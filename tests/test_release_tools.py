# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
"""Exercise real source-tree and ZIP failure modes without requiring Blender."""

from __future__ import annotations

import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import warnings
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from validate_release import (
    ARCHIVE_KINDS, ENGINE_DOCS, PNG_SIGNATURE, REQUIRED_FILES, ValidationError, validate_archive, validate_release,
)
from build_release import build_release


class ReleaseToolsTests(unittest.TestCase):
    def setUp(self):
        fixture_parent = Path(__file__).resolve().parents[1] / "dist"
        if fixture_parent.is_symlink() or (hasattr(fixture_parent, "is_junction") and fixture_parent.is_junction()):
            raise RuntimeError("Test fixture parent must be a real directory")
        fixture_parent.mkdir(exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(prefix="release-test-", dir=fixture_parent)
        def clean_fixture():
            if Path(self.temporary.name).resolve().parent != fixture_parent.resolve():
                raise RuntimeError("Refusing cleanup outside the test fixture parent")
            self.temporary.cleanup()
        self.addCleanup(clean_fixture)
        self.root = Path(self.temporary.name)
        self.files = sorted(REQUIRED_FILES | {
            "blender/lida_angel_toon/assets/sample.png",
            "unity/jp.lida.angeltoon/Runtime/Shaders/Sample.shader",
            "unity/jp.lida.angeltoon/Runtime/Shaders/Sample.shader.meta",
            "unity/jp.lida.angeltoon/Runtime/Shaders/SampleCore.hlsl",
            "unity/jp.lida.angeltoon/Editor/Sample.cs",
            "unity/jp.lida.angeltoon/Editor/Sample.Editor.asmdef",
            "unreal/LidaAngelToon/Source/hlsl/Sample_UECustom.txt",
            "unreal/LidaAngelToon/Source/textures/sample.png",
        })
        for relative in self.files:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(PNG_SIGNATURE + b"fixture" if path.suffix == ".png" else b"Sample UTF-8 source\n")
        (self.root / "VERSION").write_text("0.1.0\n", encoding="utf-8")
        self.write_manifest()

    def write_manifest(self, **overrides):
        manifest = {"schema_version": 1, "name": "LidaAngelToon", "version": "0.1.0", "files": self.files}
        manifest.update(overrides)
        (self.root / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    def test_valid_tree_and_all_archives(self):
        self.assertEqual(set(validate_release(self.root)), set(self.files))
        report = build_release(self.root)
        self.assertEqual(set(report["archives"]), set(ARCHIVE_KINDS))
        for kind, item in report["archives"].items():
            validate_archive(self.root, self.root / "dist" / item["file"], kind)
        addon = self.root / "dist" / report["archives"]["addon"]["file"]
        self.assertTrue(addon.name.endswith("-blender-addon.zip"))
        with zipfile.ZipFile(addon) as bundle:
            self.assertIn("lida_angel_toon/__init__.py", bundle.namelist())
            self.assertIn("lida_angel_toon/LICENSE", bundle.namelist())
            self.assertIn("lida_angel_toon/NOTICE.md", bundle.namelist())
            self.assertIn("lida_angel_toon/LICENSES/GPL-3.0-or-later.txt", bundle.namelist())
            self.assertIn("lida_angel_toon/LICENSES/Lida-Attribution-1.0.txt", bundle.namelist())
            self.assertNotIn("lida_angel_toon/tests/blender_smoke.py", bundle.namelist())
            self.assertFalse(any("/unity/" in name or "/unreal/" in name for name in bundle.namelist()))
        for kind, package_file in (
            ("unity", "unity/jp.lida.angeltoon/package.json"),
            ("unreal", "unreal/LidaAngelToon/Python/lidaangeltoon_ue_build.py"),
        ):
            with self.subTest(kind=kind):
                archive = self.root / "dist" / report["archives"][kind]["file"]
                prefix = f"LidaAngelToon-0.1.0-{kind}/"
                with zipfile.ZipFile(archive) as bundle:
                    names = set(bundle.namelist())
                self.assertTrue(all(name.startswith(prefix) for name in names))
                self.assertIn(prefix + package_file, names)
                self.assertIn(prefix + f"{kind}/README.md", names)
                for name in ("LICENSE", "NOTICE.md", "LICENSES/GPL-3.0-or-later.txt",
                             "LICENSES/Lida-Attribution-1.0.txt", *ENGINE_DOCS):
                    self.assertIn(prefix + name, names)
                other = "unreal/" if kind == "unity" else "unity/"
                self.assertFalse(any(name[len(prefix):].startswith((other, "blender/", "core/", "scripts/"))
                                     for name in names))
                self.assertNotIn(prefix + "README.md", names)

    def test_unity_and_unreal_text_types_are_checked(self):
        shader = self.root / "unity/jp.lida.angeltoon/Runtime/Shaders/Sample.shader"
        shader.write_text("// shader\n" + "C" + ":/" + "Users/example/project\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "Local absolute path"):
            validate_release(self.root)
        shader.write_text("// shader\n", encoding="utf-8")
        (self.root / "unity/jp.lida.angeltoon/Editor/Sample.cs").write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(ValidationError, "valid UTF-8"):
            validate_release(self.root)

    def test_engine_assets_and_projects_rejected(self):
        for name in ("unreal/LidaAngelToon/Materials/M_Sample.uasset", "unity/jp.lida.angeltoon/Sample.mat",
                     "unity/jp.lida.angeltoon/Sample.unitypackage", "unity/Sample.asset", "unreal/Sample.uproject"):
            with self.subTest(name=name):
                path = self.root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"engine asset fixture")
                self.write_manifest(files=self.files + [name])
                with self.assertRaisesRegex(ValidationError, "Forbidden asset"):
                    validate_release(self.root)
                path.unlink()
        self.write_manifest()

    def test_invalid_components_rejected(self):
        for components in ({"godot": "0.1.0"}, {"unity": "first"}, ["blender"]):
            with self.subTest(components=components):
                self.write_manifest(components=components)
                with self.assertRaisesRegex(ValidationError, "components"):
                    validate_release(self.root)
        self.write_manifest(components={"blender": "0.1.0", "unity": "0.1.0", "unreal": "0.1.0"})
        validate_release(self.root)

    def test_missing_declared_file(self):
        (self.root / "docs/SUPPORT.md").unlink()
        with self.assertRaisesRegex(ValidationError, "Missing declared"):
            validate_release(self.root)

    def test_extra_source_file(self):
        (self.root / "leftover.py").write_text("print('unused')\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "Undeclared"):
            validate_release(self.root)

    def test_declared_model_still_rejected(self):
        self.files.append("reference.fbx")
        (self.root / "reference.fbx").write_bytes(b"model fixture")
        self.write_manifest()
        with self.assertRaisesRegex(ValidationError, "Forbidden asset"):
            validate_release(self.root)

    def test_missing_license_cannot_be_removed_from_manifest(self):
        self.files.remove("LICENSE")
        self.write_manifest()
        with self.assertRaisesRegex(ValidationError, "required files: LICENSE"):
            validate_release(self.root)

    def test_version_mismatch(self):
        (self.root / "VERSION").write_text("9.9.9\n", encoding="utf-8")
        with self.assertRaisesRegex(ValidationError, "VERSION does not match"):
            validate_release(self.root)

    def test_invalid_png_signature(self):
        (self.root / "blender/lida_angel_toon/assets/sample.png").write_bytes(b"not a PNG")
        with self.assertRaisesRegex(ValidationError, "PNG signature"):
            validate_release(self.root)

    def test_local_path_and_secret_report_does_not_echo_secret(self):
        fake_secret = "sk" + "-" + "a" * 40
        (self.root / "README.md").write_text("C" + ":/" + "Users/example/private\n" + fake_secret, encoding="utf-8")
        with self.assertRaises(ValidationError) as caught:
            validate_release(self.root)
        self.assertIn("Local absolute path", str(caught.exception))
        self.assertIn("Possible secret", str(caught.exception))
        self.assertNotIn(fake_secret, str(caught.exception))

    def test_non_utf8_text(self):
        (self.root / "NOTICE.md").write_bytes(b"\xff\xfe")
        with self.assertRaisesRegex(ValidationError, "valid UTF-8"):
            validate_release(self.root)

    def test_unsafe_and_duplicate_manifest_paths(self):
        for invalid in ("../outside.py", "/outside.py", "a\\b.py", "a//b.py", "dist/file.py"):
            with self.subTest(path=invalid):
                self.write_manifest(files=self.files + [invalid])
                with self.assertRaises(ValidationError):
                    validate_release(self.root)
        self.write_manifest(files=self.files + ["readme.md"])
        with self.assertRaisesRegex(ValidationError, "case collisions"):
            validate_release(self.root)

    def test_symbolic_link_rejected_if_available(self):
        target = self.root / "README.md"
        link = self.root / "symlink.md"
        try:
            link.symlink_to(target.name)
        except OSError:
            self.skipTest("Symlink creation is not permitted on this host")
        with self.assertRaisesRegex(ValidationError, "Symbolic links"):
            validate_release(self.root)

    def test_deterministic_bytes_despite_source_mtime_changes(self):
        first = build_release(self.root)
        initial = {path.name: path.read_bytes() for path in (self.root / "dist").iterdir()}
        for index, relative in enumerate(self.files):
            os.utime(self.root / relative, (1_600_000_000 + index, 1_600_000_000 + index))
        second = build_release(self.root)
        self.assertEqual(first, second)
        self.assertEqual(initial, {path.name: path.read_bytes() for path in (self.root / "dist").iterdir()})

    def test_zip_changed_bytes_missing_and_extra_are_rejected(self):
        report = build_release(self.root)
        original = self.root / "dist" / report["archives"]["source"]["file"]
        with zipfile.ZipFile(original) as bundle:
            entries = {name: bundle.read(name) for name in bundle.namelist()}
        for alteration in ("bytes", "missing", "extra"):
            with self.subTest(alteration=alteration):
                changed = dict(entries)
                name = next(name for name in changed if name.endswith("/README.md"))
                if alteration == "bytes":
                    changed[name] += b"tampered"
                elif alteration == "missing":
                    del changed[name]
                else:
                    changed["unwanted.fbx"] = b"model"
                archive = self.root / "dist" / "tampered.zip"
                with zipfile.ZipFile(archive, "w") as bundle:
                    for member, data in changed.items():
                        bundle.writestr(member, data)
                with self.assertRaises(ValidationError):
                    validate_archive(self.root, archive, "source")

    def test_zip_symbolic_link_rejected(self):
        report = build_release(self.root)
        archive = self.root / "dist" / report["archives"]["addon"]["file"]
        with zipfile.ZipFile(archive) as bundle:
            entries = {name: bundle.read(name) for name in bundle.namelist()}
        modified = self.root / "dist" / "linked.zip"
        with zipfile.ZipFile(modified, "w") as bundle:
            for index, (name, data) in enumerate(entries.items()):
                info = zipfile.ZipInfo(name)
                if index == 0:
                    info.create_system = 3
                    info.external_attr = 0o120777 << 16
                bundle.writestr(info, data)
        with self.assertRaisesRegex(ValidationError, "regular files only"):
            validate_archive(self.root, modified, "addon")

    def test_zip_duplicate_rejected(self):
        report = build_release(self.root)
        archive = self.root / "dist" / report["archives"]["addon"]["file"]
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            with zipfile.ZipFile(archive, "a") as bundle:
                name = "lida_angel_toon/LICENSE"
                bundle.writestr(name, bundle.read(name))
        with self.assertRaisesRegex(ValidationError, "duplicate paths"):
            validate_archive(self.root, archive, "addon")


if __name__ == "__main__":
    unittest.main()
