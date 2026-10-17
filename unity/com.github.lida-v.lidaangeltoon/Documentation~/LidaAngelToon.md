# LidaAngelToon (Unity URP) - manual

Version 0.1.0. URP 17 (Unity 6000.0 or later), Forward / Forward+ renderers. Tested with Unity 6000.6.0f1,
URP 17.6, Direct3D 11, linear colour space.

## 1. Shaders and passes

| Shader | Passes | Use |
|---|---|---|
| `LidaAngelToon/Toon` | UniversalForward, SRPDefaultUnlit (outline), ShadowCaster, DepthOnly, DepthNormals | opaque and cutout |
| `LidaAngelToon/Toon Transparent` | UniversalForward, SRPDefaultUnlit (outline), ShadowCaster | alpha blend, multiply layer |

Both shaders share one `UnityPerMaterial` constant buffer layout, so they are SRP Batcher compatible.
Keywords (material, local): `_ANGELTOON_MASK_VERTEX_COLOR`, `_ANGELTOON_TWO_LAYER`, `_ANGELTOON_ALPHA_CLIP`
(opaque shader), `_ANGELTOON_MULTIPLY_LAYER` (transparent shader). URP keywords: main light shadows (incl. screen
shadows and cascades), soft shadows, additional lights and their shadows, Forward+ cluster light loop, fog.

## 2. Shading (spec v1)

```
N      = normalize(lerp(normal, Normal Override, Normal Override Mix)); NL = dot(N, L) (main light)
NLs    = min(NL, saturate(NL) x shadow attenuation x Shadow Gain)
Ls     = lerp(NL, NLs, Receive Shadow x (mask A when "Receive Shadow x Mask A", else 1))
occ    = smoothstep(0.05, 0.9, 1 - mask R);  Ls -= occ x Occlusion Shift
t1, t2 = smoothstep(Shift - Soft, Shift + Soft, Ls) for step 1 and step 2
base   = saturation(lerp(base colour, Base Lift Color, Base Lift), Base Saturation)
shade1 = (base or Shade Map) x Shade Tint 1;  shade2 = shade1 x Shade Tint 2;  lit = base x Lit Tint x light colour
c      = lerp(lerp(shade2, shade1, t2), lit, t1)
then the terminator band around Shift 1, Shade Tint 2 again in occluded areas (Occlusion Darken),
rim, soft specular, MatCap add / multiply, Unlit share and Highlight Knee (the brightest channel above the knee
rolls off softly toward 1.0, keeping the hue).
```
The full order is written step by step ([S01]...) in `LidaAngelToonCore.hlsl`.

Back faces use the flipped normal. With "Two Layer" on, mask G blends between the layer A values and the `_L2_`
values (all shading values have an L2 copy).

## 3. Properties

| Group | Properties |
|---|---|
| Base | `_BaseMap` (sRGB, UV0), `_BaseColor`, `_ShadeMap` + `_ShadeMapColor` (used when Use Shade Map = 1) |
| MatCap | `_MatCapAddMap` / `_MatCapAddColor` / `_MatCapAddStrength`, `_MatCapMulMap` / `_MatCapMulColor` / `_MatCapMulStrength` (0.5 = no change). View-space normal, clamp sampling. |
| Mask | `_UseAngelToonMask`, `_AngelToonMask` (linear), `_MaskFromVertexColor` (use the vertex colour as the mask), `_ReceiveShadowUseMaskA`, `_MatCapAddUseMaskA`, `_ShadowGain` (1.25) |
| Shade | `_ShadeTint1/2`, `_ShadeShift1/2`, `_ShadeSoft1/2`, `_UseShadeTexture`, `_ReceiveShadow`, `_NormalOverride`, `_NormalOverrideMix` |
| Light | `_LitTint` (HDR colour: the value is used as it is, no gamma conversion) |
| Rim | `_RimColor`, `_RimStrength`, `_RimWidth`, `_RimSoft`, `_RimLitBias` |
| Specular | `_SpecColor`, `_SpecStrength`, `_SpecSize`, `_SpecSoft` |
| Tone | `_Unlit`, `_HighlightKnee` |
| Occlusion (mask R) | `_OcclusionShift`, `_OcclusionDarken` |
| Terminator band | `_TerminatorColor`, `_TerminatorStrength`, `_TerminatorWidth` |
| Base colour | `_BaseLift`, `_BaseLiftColor`, `_BaseSaturation` |
| Two layer | `_TwoLayer` and the `_L2_` copies |
| Outline | `_OutlineEnabled`, `_OutlineWidthMM`, `_OutlinePixelRule`, `_OutlineGain`, `_OutlineMinPx`, `_OutlineMaxPx`, `_OutlineNormalSource`, `_OutlineTint`, `_OutlineTintL2`, `_OutlineUseFixedColor`, `_OutlineFixedColor` |
| Render state | `_Cull`, `_QueueOffset`, `_AlphaClip`, `_Cutoff`, `_AlphaToMask` (opaque); `_ZWrite`, `_MultiplyLayer`, `_MultiplyColor` (transparent) |

Colours are entered as sRGB colours in the inspector (Unity converts them to linear in linear colour space),
except `_LitTint` / `_L2_LitTint`, which are HDR colours and are used unchanged. Presets store linear values;
the preset loader converts them for the normal colours and writes the HDR colours as they are.

## 4. Outline

Inverted hull: the mesh is drawn again, pushed along its normal, with front faces culled.

- Pixel rule (default, `_OutlinePixelRule` = 1, spec v1 rule B):
  `pixels = clamp(Gain x Width / (world size of one pixel at that depth), Min px, Max px)`.
  The line stays visible far away (Min) and does not get thick close up (Max). Default Gain 1.5, Min 1, Max 2.
- World rule (`_OutlinePixelRule` = 0): the plain width in millimetres, like a Blender Solidify outline.
- Where: mask B > 0.5. Colour: base colour x `_OutlineTint` (lerp to `_OutlineTintL2` by mask G in two-layer
  materials), or a fixed colour.
- Normal: the vertex normal, or a smoothed normal stored in UV3 (tangent space). Split normals (hard edges)
  open gaps in the hull; the smoothed normal closes them. To bake it on import, select the model and use
  Assets > LidaAngelToon > Outline Normals On Import (toggle); the importer must calculate tangents.
  Then set `_OutlineNormalSource` = 1.

## 5. Cutout and transparency

- Opaque shader with `_AlphaClip` on: clip at `_Cutoff`; with `_AlphaToMask` on (MSAA needed) the edge is soft
  (alpha to coverage) and overlapping cutout layers sort themselves. Queue 2450 (AlphaTest).
- Transparent shader: alpha blend, `_ZWrite` selectable, shadow caster clips at `_Cutoff`.
  `_MultiplyLayer` makes it a multiply layer (DstColor Zero) that darkens what is below by `lerp(1, _MultiplyColor, alpha)`
  (for painted shadow layers); it does not cast shadows.

## 6. Scene settings (AngelToonGlobals)

Add `AngelToonGlobals` to any object in the scene (works in edit mode):

| Field | Meaning |
|---|---|
| Override Key Light, Key Light Transform, Key Color, Key Intensity | use this direction and colour instead of the URP main light for the toon shading (keeps the character lighting fixed while the scene light changes) |
| Ambient Mix | share of the ambient light (spherical harmonics) added to the base colour (0 = off) |
| Additional Light Mix | share of point / spot lights (0 = off) |
| Debug View | 1 base, 2 normal, 3 mask RGB, 4 mask A, 5 shadow, 6 MatCap UV |

Globals: `_AngelToonKeyDirWS`, `_AngelToonKeyColor`, `_AngelToonKeyOverride`, `_AngelToonAmbientMix`,
`_AngelToonAddLightMix`, `_AngelToonDebugMode`. They can also be set from code with `AngelToonGlobals.SetGlobals(...)`.

## 7. Presets

`Tools > LidaAngelToon > Create Materials From Preset...` reads a JSON file of format `LidaAngelToon.preset/1`:
`materials` (name, shader, floats, colours in linear, textures with import settings, keywords),
`assignments` (object, slot material name, material) and `copy_files`. Character data stays in the preset,
not in the shader.

## 8. Notes

- The shader keeps the same results as the Blender reference of spec v1 when bloom and tone mapping are off.
- Antialiasing: MSAA (4x tested) smooths the outline and is needed for alpha to coverage.
- License: Lida Attribution License 1.1 (`LICENSE.md` of the package). Author: Lida.
  Source: https://github.com/Lida-V/LidaAngelToon
