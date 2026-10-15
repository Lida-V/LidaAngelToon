#!/usr/bin/env python3
# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
"""Build deterministic, validated source and Blender install ZIPs in dist/."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import zipfile

sys.dont_write_bytecode = True
from validate_release import (  # noqa: E402
    ADDON_PREFIX, LICENSE_PREFIX, PACKAGE, ValidationError, _is_link, _load_manifest, _validate_zip,
    expected_archive_files, sha256, validate_release,
)

FIXED_TIMESTAMP = (1980, 1, 1, 0, 0, 0)


def _write_zip(destination: Path, entries: dict[str, bytes]) -> None:
    """Set all ZIP metadata explicitly; no source times or host paths leak."""
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for name, data in sorted(entries.items()):
            entry = zipfile.ZipInfo(name, FIXED_TIMESTAMP)
            entry.create_system = 3
            entry.external_attr = (stat.S_IFREG | 0o644) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            bundle.writestr(entry, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def _atomic_write(destination: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=".release-", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(data)
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def build_release(root: Path | str) -> dict:
    root = Path(root)
    if _is_link(root):
        raise ValidationError("Source root must not be a symbolic link or junction")
    root = root.resolve()
    hashes = validate_release(root)
    manifest = _load_manifest(root)
    contents = {name: (root / name).read_bytes() for name in hashes}
    if any(sha256(contents[name]) != digest for name, digest in hashes.items()):
        raise ValidationError("Sources changed during validation; run the build again")
    output = root / "dist"
    if output.is_symlink() or (hasattr(output, "is_junction") and output.is_junction()):
        raise ValidationError("dist must not be a symbolic link or junction")
    if output.exists() and not output.is_dir():
        raise ValidationError("dist must be a directory")
    output.mkdir(exist_ok=True)
    if output.resolve().parent != root:
        raise ValidationError("dist must resolve inside the source root")
    prefix = f"{manifest['name']}-{manifest['version']}/"
    source_entries = {prefix + name: data for name, data in contents.items()}
    addon_entries = {
        f"{PACKAGE}/" + name[len(ADDON_PREFIX):]: data
        for name, data in contents.items() if name.startswith(ADDON_PREFIX)
    }
    addon_entries.update({f"{PACKAGE}/{name}": contents[name] for name in ("LICENSE", "NOTICE.md")})
    addon_entries.update({f"{PACKAGE}/{name}": data for name, data in contents.items() if name.startswith(LICENSE_PREFIX)})
    names = {
        "source": f"LidaAngelToon-{manifest['version']}-source.zip",
        "addon": f"lida_angel_toon-{manifest['version']}-addon.zip",
    }
    report = {
        "schema_version": 1, "name": manifest["name"], "version": manifest["version"],
        "archives": {}, "source_files": dict(sorted(hashes.items())),
    }
    for kind, entries in (("source", source_entries), ("addon", addon_entries)):
        destination = output / names[kind]
        with tempfile.NamedTemporaryFile(dir=output, prefix=".release-", suffix=".zip", delete=False) as handle:
            temporary = Path(handle.name)
        try:
            _write_zip(temporary, entries)
            _validate_zip(temporary, expected_archive_files(root, kind, hashes))
            archive_data = temporary.read_bytes()
            report["archives"][kind] = {
                "file": names[kind], "sha256": sha256(archive_data),
                "size_bytes": len(archive_data), "file_count": len(entries),
            }
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
    if validate_release(root) != hashes:
        raise ValidationError("Sources changed during the build; run the build again")
    _atomic_write(output / "release-manifest.json", (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    checksum_lines = [f"{item['sha256']}  {item['file']}" for item in sorted(report["archives"].values(), key=lambda item: item["file"])]
    _atomic_write(output / "SHA256SUMS.txt", ("\n".join(checksum_lines) + "\n").encode("utf-8"))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    try:
        report = build_release(args.root)
        for kind, archive in report["archives"].items():
            print(f"PASS: dist/{archive['file']} ({kind}, {archive['file_count']} files, SHA256 {archive['sha256']})")
        return 0
    except (ValidationError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
