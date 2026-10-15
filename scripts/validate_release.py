#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
"""Validate the complete, explicitly declared source and release ZIP contents."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import sys
import zipfile

sys.dont_write_bytecode = True

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PACKAGE = "lida_angel_toon"
ADDON_PREFIX = f"blender/{PACKAGE}/"
LICENSE_PREFIX = "LICENSES/"
REQUIRED_FILES = frozenset({
    "VERSION", "README.md", "LICENSE", "NOTICE.md", "AGENTS.md",
    "requirements-dev.txt", "manifest.json", ".gitignore",
    ".github/workflows/validate.yml", "docs/INSTALL.md", "docs/SUPPORT.md",
    "blender/lida_angel_toon/__init__.py",
    "blender/lida_angel_toon/shader.py",
    "blender/lida_angel_toon/presets.py", "tools/generate_textures.py",
    "scripts/validate_release.py", "scripts/build_release.py",
    "tests/test_release_tools.py", "tests/blender_smoke.py",
    "LICENSES/GPL-3.0-or-later.txt",
    "LICENSES/Lida-Attribution-1.0.txt",
})
TEXT_SUFFIXES = {".md", ".txt", ".json", ".py", ".yml", ".yaml"}
SPECIAL_TEXT_FILES = {"VERSION", "LICENSE", ".gitignore"}
FORBIDDEN_SUFFIXES = {
    ".blend", ".blend1", ".fbx", ".vrm", ".glb", ".gltf", ".obj",
    ".mtl", ".stl", ".abc", ".usd", ".usda", ".usdc", ".usdz",
    ".unity", ".unitypackage", ".uasset", ".umap", ".dll", ".exe",
    ".zip", ".7z", ".rar", ".pem", ".key", ".pfx", ".p12",
}
LOCAL_PATH = re.compile(
    r"(?i)(?:\b[a-z]:[\\/]|file:/{2}|/(?:users|home)/[^\s<>\"']+)"
)
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{24,}\b"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{30,}\b"),
    re.compile(r"\bgithub_pat_[A-Za-z0-9_]{30,}\b"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
)


class ValidationError(ValueError):
    """A release invariant was violated. Messages never include secret values."""


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_link(path: Path) -> bool:
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def _safe_relative(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValidationError("Manifest paths must be nonempty strings")
    path = PurePosixPath(value)
    if (
        path.is_absolute() or str(path) != value
        or any(part in {".", ".."} for part in path.parts)
        or "\\" in value or ":" in value
        or any(ord(char) < 32 for char in value)
        or value.endswith("/")
    ):
        raise ValidationError("Manifest contains an unsafe relative path")
    if path.parts[0] in {".git", "dist", "__pycache__"}:
        raise ValidationError("Manifest must not declare generated or Git files")
    return value


def _load_manifest(root: Path) -> dict:
    manifest_path = root / "manifest.json"
    if manifest_path.is_symlink():
        raise ValidationError("Symbolic links are forbidden: manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValidationError("manifest.json is missing or invalid UTF-8 JSON") from exc
    if not isinstance(manifest, dict):
        raise ValidationError("manifest.json must contain an object")
    if type(manifest.get("schema_version")) is not int or manifest["schema_version"] != 1:
        raise ValidationError("Unsupported manifest schema_version")
    if manifest.get("name") != "LidaAngelToon":
        raise ValidationError("Manifest name must be LidaAngelToon")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?", version):
        raise ValidationError("Manifest version must be a semantic version")
    if not isinstance(manifest.get("files"), list) or not manifest["files"]:
        raise ValidationError("Manifest files must be a nonempty list")
    paths = [_safe_relative(value) for value in manifest["files"]]
    if len(set(value.casefold() for value in paths)) != len(paths):
        raise ValidationError("Manifest paths contain duplicates or case collisions")
    missing_required = REQUIRED_FILES - set(paths)
    if missing_required:
        raise ValidationError("Manifest omits required files: " + ", ".join(sorted(missing_required)))
    manifest["files"] = paths
    return manifest


def _source_files(root: Path) -> set[str]:
    found: set[str] = set()
    errors: list[str] = []
    for directory, dirs, files in os.walk(root, followlinks=False):
        current = Path(directory)
        retained: list[str] = []
        for name in dirs:
            path = current / name
            relative = path.relative_to(root).as_posix()
            if relative == ".git":
                continue
            if _is_link(path):
                errors.append("Symbolic links or junctions are forbidden: " + relative)
                continue
            if relative == "dist":
                continue
            retained.append(name)
        dirs[:] = retained
        for name in files:
            path = current / name
            relative = path.relative_to(root).as_posix()
            if path.is_symlink():
                errors.append("Symbolic links are forbidden: " + relative)
            elif relative == ".git":
                continue
            elif path.suffix in {".pyc", ".pyo"}:
                continue
            elif not path.is_file():
                errors.append("Nonregular files are forbidden: " + relative)
            else:
                found.add(relative)
    if errors:
        raise ValidationError("\n".join(errors))
    return found


def validate_release(root: Path | str) -> dict[str, str]:
    """Return the SHA256 of every allowed source file, or reject the tree."""
    root = Path(root)
    if _is_link(root):
        raise ValidationError("Source root must not be a symbolic link or junction")
    root = root.resolve()
    manifest = _load_manifest(root)
    declared = set(manifest["files"])
    actual = _source_files(root)
    missing, extra = declared - actual, actual - declared
    if missing or extra:
        messages = []
        if missing:
            messages.append("Missing declared files: " + ", ".join(sorted(missing)))
        if extra:
            messages.append("Undeclared files: " + ", ".join(sorted(extra)))
        raise ValidationError("\n".join(messages))
    errors: list[str] = []
    hashes: dict[str, str] = {}
    for relative in sorted(declared):
        path = root / relative
        suffix = path.suffix.lower()
        if suffix in FORBIDDEN_SUFFIXES:
            errors.append("Forbidden asset or binary type: " + relative)
            continue
        data = path.read_bytes()
        hashes[relative] = sha256(data)
        if suffix == ".png":
            if not data.startswith(PNG_SIGNATURE):
                errors.append("Invalid PNG signature: " + relative)
            continue
        if suffix not in TEXT_SUFFIXES and relative not in SPECIAL_TEXT_FILES:
            errors.append("Unsupported release file type: " + relative)
            continue
        try:
            content = data.decode("utf-8")
        except UnicodeError:
            errors.append("Text file is not valid UTF-8: " + relative)
            continue
        if "\x00" in content:
            errors.append("NUL byte in text file: " + relative)
        if LOCAL_PATH.search(content):
            errors.append("Local absolute path or file URL in: " + relative)
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            errors.append("Possible secret in: " + relative)
    try:
        version = (root / "VERSION").read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError):
        version = None
    if version != manifest["version"]:
        errors.append("VERSION does not match manifest version")
    if errors:
        raise ValidationError("\n".join(errors))
    return hashes


def expected_archive_files(root: Path | str, kind: str, hashes: dict[str, str] | None = None) -> dict[str, str]:
    root = Path(root).resolve()
    hashes = validate_release(root) if hashes is None else hashes
    manifest = _load_manifest(root)
    if kind == "source":
        prefix = f"{manifest['name']}-{manifest['version']}/"
        return {prefix + name: digest for name, digest in hashes.items()}
    if kind == "addon":
        expected = {
            f"{PACKAGE}/" + name[len(ADDON_PREFIX):]: digest
            for name, digest in hashes.items() if name.startswith(ADDON_PREFIX)
        }
        expected.update({f"{PACKAGE}/{name}": hashes[name] for name in ("LICENSE", "NOTICE.md")})
        expected.update({f"{PACKAGE}/{name}": digest for name, digest in hashes.items() if name.startswith(LICENSE_PREFIX)})
        return expected
    raise ValidationError("Archive kind must be source or addon")


def _validate_zip(archive: Path | str, expected: dict[str, str]) -> None:
    try:
        with zipfile.ZipFile(archive) as bundle:
            entries = bundle.infolist()
            names = [entry.filename for entry in entries]
            if len(names) != len(set(name.casefold() for name in names)):
                raise ValidationError("ZIP contains duplicate paths or case collisions")
            missing, extra = set(expected) - set(names), set(names) - set(expected)
            if missing or extra:
                raise ValidationError("ZIP file set differs from the declared release")
            for entry in entries:
                file_type = stat.S_IFMT(entry.external_attr >> 16)
                if entry.is_dir() or file_type not in {0, stat.S_IFREG}:
                    raise ValidationError("ZIP must contain regular files only")
                if sha256(bundle.read(entry)) != expected[entry.filename]:
                    raise ValidationError("ZIP SHA256 mismatch: " + entry.filename)
    except (OSError, zipfile.BadZipFile, RuntimeError) as exc:
        raise ValidationError("ZIP is missing, unreadable, or corrupt") from exc


def validate_archive(root: Path | str, archive: Path | str, kind: str) -> None:
    """Require exact members and source-matching bytes, including licenses."""
    _validate_zip(archive, expected_archive_files(root, kind))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--zip", type=Path, dest="archive")
    parser.add_argument("--kind", choices=("source", "addon"))
    args = parser.parse_args(argv)
    if args.archive is not None and args.kind is None:
        parser.error("--zip requires --kind")
    try:
        hashes = validate_release(args.root)
        if args.archive is not None:
            validate_archive(args.root, args.archive, args.kind)
        print(f"PASS: {len(hashes)} declared source files" + (f"; {args.kind} ZIP matches" if args.archive else ""))
        return 0
    except (ValidationError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
