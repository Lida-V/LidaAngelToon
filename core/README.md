# core - the shared shading core of LidaAngelToon

| File | Content |
|---|---|
| `LidaAngelToonCore.hlsl` | the whole shading as pure functions (no texture sampling, no engine code). Pure ASCII. Unity includes it; Unreal uses the Custom-node text generated from it |
| `scripts/core338.py` | the same math in numpy (Python 3, numpy only). Each step carries the same tag `[S01]`..`[S24]` as the HLSL, so the two can be read side by side. `FIELDS` maps each HLSL member to the Blender node input name |
| `scripts/make_ue_custom338.py` | generates `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt` and `..._OutlineWidth.txt` from the core, and `core/tests/ue_custom_check.hlsl` (the two bodies wrapped like Unreal does, for an fxc / dxc syntax check) |

## Functions

| Function | Use |
|---|---|
| `AngelToonShade(AngelToonInput i, AngelToonMaterial m)` | the shaded colour (linear emission, before bloom / tone mapping) |
| `AngelToonShadeTwoLayer(iA, mA, iB, mB, maskB)` | shades both parameter sets and mixes the finished colours by mask G (`maskB`) |
| `AngelToonShadowedNL(NL, shadowAtten, gain)` | `saturate(NL) x shadow x gain` for `AngelToonInput.ShadowedNL` (the shade function then uses `min(N.L, ShadowedNL)`); gain 1.25 matches the Blender reference |
| `AngelToonMatCapUV(normalVS)` / `AngelToonMatCapUV_UE(normalViewUE)` | MatCap UV from a view-space normal (Unity: right-handed view space, V = 0 at the bottom; Unreal: left-handed, V = 0 at the top) |
| `AngelToonHighlightKnee(c, k)` | soft roll-off of the brightest channel above `k`, hue kept |
| `AngelToonPixelWorldSize`, `AngelToonOutlinePixels`, `AngelToonOutlinePushClip`, `AngelToonOutlineColor`, `AngelToonOutlineVisible` | outline width in screen pixels (rule B), push of the hull in clip space, outline colour and mask |

`AngelToonMaterial` holds the 32 per-material values, `AngelToonInput` the 12 per-pixel inputs. Their meaning and the
Blender / Unity / Unreal names are in [../docs/BLENDER-NODE-MAPPING.md](../docs/BLENDER-NODE-MAPPING.md); the order of the
steps in [../docs/SPEC.md](../docs/SPEC.md).

## Rules

- All colours are linear. Sample sRGB textures with sRGB decoding before passing them; the mask is linear.
- N, L, V in the same world space. Flip N toward the viewer on back faces. L = direction TO the light, V = direction
  TO the camera (orthographic: the camera's back axis).
- Keep the file ASCII: DXC (and Unreal's shader compiler) stop on non-ASCII text, even in comments.
- After changing the core, regenerate the Unreal text:

  ```
  python -I core/scripts/make_ue_custom338.py . unreal/LidaAngelToon/Source/hlsl dist/ue_custom_check.hlsl
  ```

  (run from the repository root; without the last two arguments the syntax-check file is written to
  `core/tests/`, which is not a declared file of the repository). With the core of 0.1.0 the output is
  byte-identical to the shipped files; `tests/test_repository_consistency.py` checks this.

## Notes on the header of LidaAngelToonCore.hlsl

The three copies of the core (`core/`, the Unity package, `unreal/.../Source/hlsl/`) are byte-identical
(checked by `tests/test_repository_consistency.py`). Compared with the file used in the engine tests, only the two
comment lines of the header changed (license and copyright: SPDX `LicenseRef-Lida-Attribution-1.0`,
`Copyright (c) 2026 Lida`); the code is the same. The header still names the files of the place where it was
written:

| Header says | In this package |
|---|---|
| `spec v1 (toonspec338)` | spec v1 = [../docs/SPEC.md](../docs/SPEC.md) (toonspec338 is the internal name of the step that wrote it) |
| `scripts/core338.py` | `core/scripts/core338.py` |
| `data/material_table338.json` (the per-material values) | not included (character data). Per-material values go into the Unity material / preset or the Unreal Material Instance |
| `hlsl/LidaAngelToon_UECustom.txt`, `scripts/make_ue_custom338.py` | `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt` and `_OutlineWidth.txt`, `core/scripts/make_ue_custom338.py` |

`core338.py` got a license header comment in front (the code is unchanged; its Python syntax tree is identical).
Its docstring mentions a comparison script of the original workspace that is not part of this repository.
`make_ue_custom338.py` reads and writes the package locations instead of the original ones; the generated text is
the same.

## Checks done for 0.1.0

- The formula against Blender EEVEE renders (inputs read back as AOVs): mean difference 0.00013 to 0.00021, max
  0.0025 (linear), at most 1/255 in sRGB; the same HLSL on a GPU (D3D11 compute, RTX 4090 and WARP) agrees with
  Python within 0.0000015.
- Compiles with fxc (ps_5_0, vs_5_0) and dxc (ps_6_0, vs_6_0); the Unreal Custom-node text wrapped like Unreal does
  compiles with fxc and dxc.
