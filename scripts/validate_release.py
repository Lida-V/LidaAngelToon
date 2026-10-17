#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
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
NOTICE_FILES = ("LICENSE", "NOTICE.md")
# Unity / Unreal Engine release ZIPs: the platform folder, the shared engine documents and the license files,
# at the same relative paths as in the repository (so the relative links of the documents keep working).
ENGINE_ARCHIVE_PREFIXES = {"unity": "unity/", "unreal": "unreal/"}
ENGINE_DOCS = (
    "docs/SPEC.md", "docs/SPEC.ja.md", "docs/BLENDER-NODE-MAPPING.md",
    "docs/OUTLINE-RULE-B.md", "docs/COLOR-AND-TONEMAP.md", "docs/CROSS-ENGINE-LOOK.md",
)
ARCHIVE_KINDS = ("source", "addon", "unity", "unreal")
ARCHIVE_FILE_NAMES = {
    "source": "{name}-{version}-source.zip",
    "addon": "{name}-{version}-blender-addon.zip",
    "unity": "{name}-{version}-unity.zip",
    "unreal": "{name}-{version}-unreal.zip",
}
COMPONENTS = frozenset({"blender", "unity", "unreal"})
REQUIRED_FILES = frozenset({
    "VERSION", "README.md", "LICENSE", "NOTICE.md", "AGENTS.md", "CHANGELOG.md",
    "requirements-dev.txt", "manifest.json", ".gitignore",
    ".github/workflows/validate.yml", "docs/INSTALL.md", "docs/SUPPORT.md",
    "blender/lida_angel_toon/__init__.py",
    "blender/lida_angel_toon/shader.py",
    "blender/lida_angel_toon/presets.py", "tools/generate_textures.py",
    "scripts/validate_release.py", "scripts/build_release.py",
    "tests/test_release_tools.py", "tests/test_repository_consistency.py",
    "tests/blender_smoke.py",
    "LICENSES/GPL-3.0-or-later.txt",
    "LICENSES/Lida-Attribution-1.1.txt",
    "core/LidaAngelToonCore.hlsl",
    "unity/README.md", "unity/com.github.lida-v.lidaangeltoon/package.json",
    "unity/com.github.lida-v.lidaangeltoon/LICENSE.md",
    "unreal/README.md", "unreal/LidaAngelToon/LICENSE.md",
    "unreal/LidaAngelToon/Python/lidaangeltoon_ue_build.py",
    *ENGINE_DOCS,
})
TEXT_SUFFIXES = {
    ".md", ".txt", ".json", ".py", ".yml", ".yaml",
    ".shader", ".hlsl", ".cs", ".asmdef", ".meta",
}
SPECIAL_TEXT_FILES = {"VERSION", "LICENSE", ".gitignore"}
FORBIDDEN_SUFFIXES = {
    ".blend", ".blend1", ".fbx", ".vrm", ".glb", ".gltf", ".obj",
    ".mtl", ".stl", ".abc", ".usd", ".usda", ".usdc", ".usdz",
    ".unity", ".unitypackage", ".uasset", ".umap", ".uproject", ".dll", ".exe",
    ".asset", ".mat", ".prefab", ".anim", ".controller",
    ".zip", ".7z", ".rar", ".tgz", ".tar", ".gz", ".pem", ".key", ".pfx", ".p12",
}
SEMVER = re.compile(r"\d+\.\d+\.\d+(?:-[A-Za-z0-9.-]+)?")
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
    if not isinstance(version, str) or not SEMVER.fullmatch(version):
        raise ValidationError("Manifest version must be a semantic version")
    components = manifest.get("components", {})
    if (
        not isinstance(components, dict) or not set(components) <= COMPONENTS
        or not all(isinstance(value, str) and SEMVER.fullmatch(value) for value in components.values())
    ):
        raise ValidationError("Manifest components must map blender/unity/unreal to semantic versions")
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


def archive_file_name(manifest: dict, kind: str) -> str:
    if kind not in ARCHIVE_FILE_NAMES:
        raise ValidationError("Archive kind must be one of: " + ", ".join(ARCHIVE_KINDS))
    return ARCHIVE_FILE_NAMES[kind].format(name=manifest["name"], version=manifest["version"])


def archive_members(manifest: dict, names, kind: str) -> dict[str, str]:
    """Map each archive member path to the declared source file it is copied from."""
    names = sorted(names)
    notices = [name for name in names if name in NOTICE_FILES or name.startswith(LICENSE_PREFIX)]
    if kind == "source":
        prefix = f"{manifest['name']}-{manifest['version']}/"
        return {prefix + name: name for name in names}
    if kind == "addon":
        members = {f"{PACKAGE}/" + name[len(ADDON_PREFIX):]: name for name in names if name.startswith(ADDON_PREFIX)}
        members.update({f"{PACKAGE}/{name}": name for name in notices})
        return members
    if kind in ENGINE_ARCHIVE_PREFIXES:
        platform = [name for name in names if name.startswith(ENGINE_ARCHIVE_PREFIXES[kind])]
        if not platform:
            raise ValidationError(f"No {kind} files to package")
        prefix = f"{manifest['name']}-{manifest['version']}-{kind}/"
        selected = platform + [name for name in names if name in ENGINE_DOCS] + notices
        return {prefix + name: name for name in selected}
    raise ValidationError("Archive kind must be one of: " + ", ".join(ARCHIVE_KINDS))


def expected_archive_files(root: Path | str, kind: str, hashes: dict[str, str] | None = None) -> dict[str, str]:
    root = Path(root).resolve()
    hashes = validate_release(root) if hashes is None else hashes
    manifest = _load_manifest(root)
    return {member: hashes[source] for member, source in archive_members(manifest, hashes, kind).items()}


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
    parser.add_argument("--kind", choices=ARCHIVE_KINDS)
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
