# core - the shared shading core of LidaAngelToon

| File | Content |
|---|---|
| `LidaAngelToonCore.hlsl` | the whole shading as pure functions (no texture sampling, no engine code). Pure ASCII. Unity includes it; Unreal uses the Custom-node text generated from it |
| `scripts/core_reference.py` | the same math in numpy (Python 3, numpy only). Each step carries the same tag `[S01]`..`[S24]` as the HLSL, so the two can be read side by side. `FIELDS` maps each HLSL member to the Blender node input name |
| `scripts/make_ue_custom.py` | generates `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt` and `..._OutlineWidth.txt` from the core, and `core/tests/ue_custom_check.hlsl` (the two bodies wrapped like Unreal does, for an fxc / dxc syntax check) |

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
  python -I core/scripts/make_ue_custom.py . unreal/LidaAngelToon/Source/hlsl dist/ue_custom_check.hlsl
  ```

  (run from the repository root; without the last two arguments the syntax-check file is written to
  `core/tests/`, which is not a declared file of the repository). With the core of 0.1.0 the output is
  byte-identical to the shipped files; `tests/test_repository_consistency.py` checks this.

## Notes on the header of LidaAngelToonCore.hlsl

The three copies of the core (`core/`, the Unity package, `unreal/.../Source/hlsl/`) are byte-identical
(checked by `tests/test_repository_consistency.py`). Compared with the file used in the engine tests, only comment
lines of the header changed: the license and copyright lines (SPDX `LicenseRef-Lida-Attribution-1.1`,
`Copyright (c) 2026 Lida`) and the file names it points to, which now are the paths of this repository
(`docs/SPEC.md`, `core/scripts/core_reference.py`, `core/scripts/make_ue_custom.py` and the two Unreal text files).
The code is the same. Per-material values are not part of the core: they go into the Unity material / preset or
the Unreal Material Instance.

`core_reference.py` got a license header comment and a docstring that names the paths of this repository; its code
is the same as in the engine tests. `make_ue_custom.py` reads and writes the locations of this repository instead
of the ones of the engine tests and writes header lines with the license and its own path into the Unreal text; the
generated code below those lines is the same.

## Checks done for 0.1.0

- The formula against Blender EEVEE renders (inputs read back as AOVs): mean difference 0.00013 to 0.00021, max
  0.0025 (linear), at most 1/255 in sRGB; the same HLSL on a GPU (D3D11 compute, RTX 4090 and WARP) agrees with
  Python within 0.0000015.
- Compiles with fxc (ps_5_0, vs_5_0) and dxc (ps_6_0, vs_6_0); the Unreal Custom-node text wrapped like Unreal does
  compiles with fxc and dxc.
