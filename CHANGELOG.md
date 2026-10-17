# Changelog

Versions of the repository release. Each release lists the versions of its parts.

## [0.2.1] - 2026-10-17

Parts: Blender add-on 0.1.0 (unchanged), Unity package `com.github.lida-v.lidaangeltoon` 0.1.0 (renamed),
Unreal Engine files 0.1.0 (unchanged code).

- Documentation: Japanese / English answers about colour management, shadows, hair highlights, outlines,
  transparency and character consistency across shots, with an adjustment order and explicit implementation limits.
  Linked from the README and colour notes; included in the source, Unity and Unreal Engine ZIPs.
- Unity package name: `jp.lida.angeltoon` -> `com.github.lida-v.lidaangeltoon`; the package folder has the same
  name. The code, the shader names and the Unity asset GUIDs are the same; remove an old
  `Packages/jp.lida.angeltoon` folder before adding the new one.
- License: Lida Attribution License 1.1 (SPDX `LicenseRef-Lida-Attribution-1.1`) for the Unity, Unreal Engine and
  core files, the documents and the images; 1.1 names shader code explicitly in clause 1 and is otherwise the same
  as 1.0. The Python code of the Blender add-on stays GPL-3.0-or-later. Copies distributed under the Lida
  Attribution License 1.0 (v0.1.0, v0.2.0) stay under 1.0.
- Tool names: `core/scripts/core338.py` -> `core/scripts/core_reference.py`, `core/scripts/make_ue_custom338.py` ->
  `core/scripts/make_ue_custom.py`; comments that named internal steps now name the files of this repository.
  Behaviour is unchanged.
- Tests: the repository test also checks that the Unity package folder matches its package name, that `LICENSES/`
  holds only the license texts in use, and that no file or path carries an internal step name.

## [0.2.0] - 2026-10-15

Parts: Blender add-on 0.1.0 (unchanged), Unity package `jp.lida.angeltoon` 0.1.0 (new), Unreal Engine files 0.1.0 (new).

- README now shows actual full-body and face renders in Blender (development reference), Unity and Unreal Engine,
  with engine versions, capture conditions, Lida attribution and source URLs. The installable Blender add-on's
  primitive preset and control examples remain separately identified. Model data is not distributed.

- First version of LidaAngelToon for Unity (URP) and Unreal Engine 5, in the same repository as the Blender add-on.
- Shared shading core `core/LidaAngelToonCore.hlsl` (spec v1): two soft shade steps, mask texture (R occlusion,
  G second layer, B outline area, A per material), rim, soft specular, MatCap add / multiply, terminator band,
  base lift / saturation, Unlit share, Highlight Knee, two-layer materials, screen-pixel outline width
  (rule B: `clamp(1.5 x width / pixel size, min, max)`). numpy reference `core/scripts/core338.py`.
- Unity package `jp.lida.angeltoon` 0.1.0: `LidaAngelToon/Toon` (opaque, optional cut-out with alpha to coverage)
  and `LidaAngelToon/Toon Transparent` (alpha blend, optional multiply layer); passes UniversalForward,
  SRPDefaultUnlit (inverted-hull outline), ShadowCaster, DepthOnly, DepthNormals; editor tools (material sync,
  preset importer, smoothed outline normals in UV3); `AngelToonGlobals` (key light override, ambient and
  additional light shares, debug views).
- Unreal Engine: Python that builds `M_LidaAngelToon`, `M_LidaAngelToon_Translucent`, `M_LidaAngelToon_Outline`,
  `M_LidaAngelToon_MultiplyLayer`, `MPC_LidaAngelToon`, `BP_LidaAngelToonKeyLight` and default textures; Custom-node
  text generated from the core (`core/scripts/make_ue_custom338.py`); Material Instance helpers.
- Documentation: specification (English and Japanese), Blender node input mapping, outline rule B, colour and tone
  mapping notes.
- Tested: Unity 6000.6.0f1 / URP 17.6 / D3D11 / Linear / Forward+ and Unreal Engine 5.8 on Windows, against
  Blender 5.2.1 EEVEE renders of the reference node group (see README.md and docs/images/engine-models.md).
- License: the Unity, Unreal Engine and core files are under the Lida Attribution License 1.0 (SPDX
  `LicenseRef-Lida-Attribution-1.0`); the Python code of the Blender add-on stays GPL-3.0-or-later. The Unity
  package and the Unreal folder carry the license text and the source notice in their own `LICENSE.md`.
- Release ZIPs are split by platform: `-source.zip`, `-blender-addon.zip` (was `lida_angel_toon-<version>-addon.zip`),
  `-unity.zip`, `-unreal.zip`.
- Release tools: the allowlist accepts `.shader`, `.hlsl`, `.cs`, `.asmdef` and `.meta` as text; Unity scenes /
  assets / materials / prefabs, Unreal `.uasset` / `.umap` / `.uproject` and archives stay rejected. New test
  `tests/test_repository_consistency.py`.

## [0.1.0] - 2026-10-15

- First release: the Blender add-on (10 presets, six procedural textures, node group with optional AO, hair streak
  mask and inverted-hull outline), documents and release tools.
