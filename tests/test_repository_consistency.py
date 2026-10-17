# SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
# Copyright (c) 2026 Lida
"""Check the real repository tree: shared core copies, generated Unreal text, licenses, versions, links.

Standard library only; no Blender, Unity or Unreal Engine is started.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from validate_release import ENGINE_ARCHIVE_PREFIXES, _load_manifest, archive_members  # noqa: E402

ATTRIBUTION = "LicenseRef-Lida-Attribution-1.1"
GPL = "GPL-3.0-or-later"
KNOWN_IDS = {ATTRIBUTION, GPL}
# license text of every identifier in use (LICENSES/ holds exactly these files)
LICENSE_TEXTS = {ATTRIBUTION: "LICENSES/Lida-Attribution-1.1.txt", GPL: "LICENSES/GPL-3.0-or-later.txt"}
UNITY_PACKAGE_NAME = "com.github.lida-v.lidaangeltoon"
# Unity package names: lower case, reverse-domain style (at least three dot-separated parts)
UNITY_NAME_RULE = re.compile(r"[a-z0-9][a-z0-9_-]*(?:\.[a-z0-9][a-z0-9_-]*){2,}")
# Internal step names: a word that ends in a three-digit number (a tool or file named after a work step).
# sha256 and a URP library function are ordinary names, not step names.
STEP_NAME = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z][A-Za-z0-9_]*?[A-Za-z_]\d{3}(?![0-9A-Za-z])")
STEP_NAME_ALLOWED = re.compile(r"(?i)(?:sha256|PackFloat2To888)$")
SPDX_LINE = re.compile(r"SPDX-License-Identifier:\s*([A-Za-z0-9.+-]+)")
CORE_COPIES = (
    "core/LidaAngelToonCore.hlsl",
    f"unity/{UNITY_PACKAGE_NAME}/Runtime/Shaders/LidaAngelToonCore.hlsl",
    "unreal/LidaAngelToon/Source/hlsl/LidaAngelToonCore.hlsl",
)
UE_HLSL = "unreal/LidaAngelToon/Source/hlsl/"
UE_GENERATED = ("LidaAngelToon_UECustom_Shade.txt", "LidaAngelToon_UECustom_OutlineWidth.txt")
UE_SNIPPETS = {
    "SNIP_NORMAL": "LidaAngelToon_UESnippet_Normal.txt",
    "SNIP_MATCAP_UV": "LidaAngelToon_UESnippet_MatcapUv.txt",
    "SNIP_SHADOWED_NL": "LidaAngelToon_UESnippet_ShadowedNl.txt",
    "SNIP_OUTLINE_VIEW": "LidaAngelToon_UESnippet_OutlineView.txt",
    "SNIP_DITHER": "LidaAngelToon_UESnippet_Dither.txt",
    "SNIP_OUTLINE_MASK": "LidaAngelToon_UESnippet_OutlineMask.txt",
}
CODE_SUFFIXES = {".py", ".hlsl", ".shader", ".cs", ".txt"}
ENGINE_ASCII_SUFFIXES = CODE_SUFFIXES | {".asmdef", ".json", ".meta"}
UNITY_PACKAGE = f"unity/{UNITY_PACKAGE_NAME}/"
PACKAGE_LICENSES = (f"unity/{UNITY_PACKAGE_NAME}/LICENSE.md", "unreal/LidaAngelToon/LICENSE.md")
LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)\)")


def declared() -> list[str]:
    return list(_load_manifest(ROOT)["files"])


def is_gpl_path(name: str) -> bool:
    return (name.startswith("blender/") and name.endswith(".py")) or (
        name.startswith("tests/blender_") and name.endswith(".py"))


def link_targets(name: str, text: str):
    """Relative link targets of a Markdown file, resolved to repository paths (no URLs, no pure anchors)."""
    base = PurePosixPath(name).parent
    for target in LINK.findall(text):
        if re.match(r"[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        path = target.split("#", 1)[0]
        parts = []
        for part in (base / path).parts:
            if part == "..":
                if not parts:
                    raise AssertionError(f"{name}: link leaves the repository: {target}")
                parts.pop()
            elif part != ".":
                parts.append(part)
        yield target, "/".join(parts)


# Tool names retired in 0.2.1; only the changelog may name them.
RETIRED_STEP_NAMES_IN_HISTORY = {"core" + "338", "make_ue_custom" + "338"}  # split so this file stays clean


class RepositoryConsistencyTests(unittest.TestCase):
    def test_core_copies_are_identical(self):
        data = {name: (ROOT / name).read_bytes() for name in CORE_COPIES}
        self.assertEqual(len(set(data.values())), 1, "the three copies of LidaAngelToonCore.hlsl differ")

    def test_unreal_custom_text_regenerates_byte_identically(self):
        parent = ROOT / "dist"
        parent.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="regen-test-", dir=parent) as temporary:
            out = Path(temporary) / "hlsl"
            check = Path(temporary) / "ue_custom_check.hlsl"
            result = subprocess.run(
                [sys.executable, "-I", "-B", str(ROOT / "core/scripts/make_ue_custom.py"), str(ROOT), str(out), str(check)],
                capture_output=True, text=True, check=False)
            self.assertEqual(result.returncode, 0, result.stderr)
            for name in UE_GENERATED:
                with self.subTest(file=name):
                    self.assertEqual((out / name).read_bytes(), (ROOT / UE_HLSL / name).read_bytes())
            self.assertTrue(check.is_file())

    def test_unreal_snippet_files_match_the_build_script(self):
        tree = ast.parse((ROOT / "unreal/LidaAngelToon/Python/lidaangeltoon_ue_build.py").read_text(encoding="ascii"))
        found = {}
        for node in tree.body:
            if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
                if node.targets[0].id in UE_SNIPPETS:
                    found[node.targets[0].id] = ast.literal_eval(node.value)
        self.assertEqual(set(found), set(UE_SNIPPETS))
        for variable, file_name in UE_SNIPPETS.items():
            with self.subTest(snippet=file_name):
                text = (ROOT / UE_HLSL / file_name).read_text(encoding="ascii")
                self.assertTrue(text.endswith(found[variable]))
                header = text[: len(text) - len(found[variable])].splitlines()
                self.assertTrue(header and all(line.startswith("// ") for line in header))
                self.assertIn(f"// SPDX-License-Identifier: {ATTRIBUTION}", header)

    def test_spdx_identifiers_follow_the_license_map(self):
        for name in declared():
            path = ROOT / name
            if path.suffix == ".png":
                continue
            text = path.read_text(encoding="utf-8")
            ids = set(SPDX_LINE.findall(text))
            with self.subTest(file=name):
                self.assertTrue(ids <= KNOWN_IDS, f"unknown SPDX identifier: {ids - KNOWN_IDS}")
                if name.startswith("LICENSES/"):
                    continue
                if is_gpl_path(name):
                    self.assertIn(f"SPDX-License-Identifier: {GPL}", "\n".join(text.splitlines()[:5]))
                else:
                    self.assertNotIn(GPL, ids, "GPL identifier outside the bpy add-on and its Blender tests")
                if path.suffix in CODE_SUFFIXES and not is_gpl_path(name) and name != "requirements-dev.txt":
                    self.assertIn(f"SPDX-License-Identifier: {ATTRIBUTION}", "\n".join(text.splitlines()[:8]))

    def test_engine_code_is_ascii(self):
        for name in declared():
            if name.split("/", 1)[0] in {"core", "unity", "unreal"} and Path(name).suffix in ENGINE_ASCII_SUFFIXES:
                with self.subTest(file=name):
                    (ROOT / name).read_bytes().decode("ascii")

    def test_component_versions_match_the_code(self):
        components = _load_manifest(ROOT)["components"]
        self.assertEqual(set(components), {"blender", "unity", "unreal"})
        init = (ROOT / "blender/lida_angel_toon/__init__.py").read_text(encoding="utf-8")
        match = re.search(r'"version":\s*\((\d+),\s*(\d+),\s*(\d+)\)', init)
        self.assertIsNotNone(match)
        self.assertEqual(".".join(match.groups()), components["blender"])
        shader = (ROOT / "blender/lida_angel_toon/shader.py").read_text(encoding="utf-8")
        self.assertIn(f'VERSION = "{components["blender"]}"', shader)
        package = json.loads((ROOT / UNITY_PACKAGE / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["name"], UNITY_PACKAGE_NAME)
        self.assertEqual(package["version"], components["unity"])
        self.assertEqual(package["license"], ATTRIBUTION)
        self.assertEqual(package["author"]["name"], "Lida")

    def test_package_license_files_carry_the_full_license_and_source(self):
        full = (ROOT / LICENSE_TEXTS[ATTRIBUTION]).read_text(encoding="utf-8")
        notice = (ROOT / "NOTICE.md").read_text(encoding="utf-8")
        source = re.search(r"Source:\s*(\S+)", notice).group(1)
        for name in PACKAGE_LICENSES:
            with self.subTest(file=name):
                text = (ROOT / name).read_text(encoding="utf-8")
                match = re.search(r"\n~~~text\n(.*?)~~~\n\Z", text, re.S)
                self.assertIsNotNone(match)
                self.assertEqual(match.group(1), full)
                self.assertIn(source, text)
                self.assertIn("Author: Lida", text)

    def test_unity_package_folder_matches_the_package_name(self):
        self.assertIsNotNone(UNITY_NAME_RULE.fullmatch(UNITY_PACKAGE_NAME))
        folders = {name.split("/")[1] for name in declared() if name.startswith("unity/") and name.count("/") >= 2}
        self.assertEqual(folders, {UNITY_PACKAGE_NAME}, "unity/ must hold exactly one package folder named like the package")
        package = json.loads((ROOT / UNITY_PACKAGE / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(package["name"], UNITY_PACKAGE_NAME)
        for name in declared():
            if name.startswith(UNITY_PACKAGE) and name.endswith(".asmdef"):
                with self.subTest(asmdef=name):
                    asmdef = json.loads((ROOT / name).read_text(encoding="utf-8"))
                    self.assertTrue(asmdef["name"].startswith("LidaAngelToon."))

    def test_license_texts_match_the_identifiers_in_use(self):
        texts = {name for name in declared() if name.startswith("LICENSES/")}
        self.assertEqual(texts, set(LICENSE_TEXTS.values()))
        for identifier, name in LICENSE_TEXTS.items():
            if identifier.startswith("LicenseRef-"):
                with self.subTest(license=name):
                    head = (ROOT / name).read_text(encoding="utf-8").splitlines()[:3]
                    self.assertIn(f"SPDX-License-Identifier: {identifier}", head)

    def test_no_internal_step_names(self):
        for name in declared():
            with self.subTest(path=name):
                found = [m.group(0) for m in STEP_NAME.finditer(name) if not STEP_NAME_ALLOWED.search(m.group(0))]
                self.assertEqual(found, [], "file path carries an internal step name")
            if name.endswith(".png") or name.startswith("LICENSES/"):
                continue
            text = (ROOT / name).read_text(encoding="utf-8")
            # The changelog keeps the retired tool names of earlier releases as history.
            retired = RETIRED_STEP_NAMES_IN_HISTORY if name == "CHANGELOG.md" else set()
            with self.subTest(file=name):
                found = sorted({m.group(0) for m in STEP_NAME.finditer(text)
                                if not STEP_NAME_ALLOWED.search(m.group(0)) and m.group(0) not in retired})
                self.assertEqual(found, [], "text carries an internal step name")

    def test_unity_meta_files_are_complete(self):
        names = set(declared())
        package = [name for name in names if name.startswith(UNITY_PACKAGE)]
        guids = {}
        folders = set()
        for name in package:
            relative = PurePosixPath(name[len(UNITY_PACKAGE):])
            if any(part.endswith("~") for part in relative.parts[:-1]):
                continue
            for parent in list(relative.parents)[:-1]:
                folders.add(UNITY_PACKAGE + str(parent))
            if name.endswith(".meta"):
                asset = name[: -len(".meta")]
                with self.subTest(meta=name):
                    self.assertTrue(asset in names or asset in folders or any(n.startswith(asset + "/") for n in names))
                    guid = re.search(r"^guid: ([0-9a-f]{32})$", (ROOT / name).read_text(encoding="ascii"), re.M)
                    self.assertIsNotNone(guid)
                    self.assertNotIn(guid.group(1), guids, f"duplicate GUID in {name} and {guids.get(guid.group(1))}")
                    guids[guid.group(1)] = name
            else:
                with self.subTest(asset=name):
                    self.assertIn(name + ".meta", names)
        for folder in folders:
            with self.subTest(folder=folder):
                self.assertIn(folder + ".meta", names)

    def test_markdown_links_resolve(self):
        names = set(declared())
        folders = {str(parent) for name in names for parent in PurePosixPath(name).parents}
        for name in names:
            if name.endswith(".md"):
                for target, resolved in link_targets(name, (ROOT / name).read_text(encoding="utf-8")):
                    with self.subTest(file=name, link=target):
                        self.assertTrue(resolved in names or resolved in folders)

    def test_unity_and_unreal_archives_are_self_contained(self):
        manifest = _load_manifest(ROOT)
        for kind in ENGINE_ARCHIVE_PREFIXES:
            members = set(archive_members(manifest, declared(), kind).values())
            for name in sorted(members):
                if name.endswith(".md"):
                    for target, resolved in link_targets(name, (ROOT / name).read_text(encoding="utf-8")):
                        with self.subTest(archive=kind, file=name, link=target):
                            self.assertIn(resolved, members)

    def test_python_files_parse(self):
        for name in declared():
            if name.endswith(".py"):
                with self.subTest(file=name):
                    ast.parse((ROOT / name).read_text(encoding="utf-8"), filename=name)


if __name__ == "__main__":
    unittest.main()
