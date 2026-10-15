# Blender node inputs and the Unity / Unreal names

The reference look was made in Blender with a node group named **`LidaSoftToon`** (the group keeps its Blender
name; it is not part of this repository). `core/LidaAngelToonCore.hlsl` reproduces it. Each value has the same name in
HLSL and Unreal, and `_<Name>` in Unity. The second layer of a two-layer material uses `_L2_<Name>` (Unity) and
`L2_<Name>` (Unreal).

The Blender add-on of this repository (`blender/lida_angel_toon`, GPL-3.0-or-later) builds a node group with the
**same 38 input names** (32 material values + 6 per-pixel inputs below). This was checked by name only; its default values differ, and its numbers were not
compared with this core in this release.

## Per-material values (`AngelToonMaterial`, 32)

| Blender input | HLSL / Unreal | Type | Unity | Meaning |
|---|---|---|---|---|
| Shade Tint 1 | ShadeTint1 | float3 | `_ShadeTint1` | 1st shade tint (multiplies the base colour) |
| Shade Shift 1 | ShadeShift1 | float | `_ShadeShift1` | position of the 1st border on N.L (bigger = wider shade) |
| Shade Soft 1 | ShadeSoft1 | float | `_ShadeSoft1` | half width of the 1st soft step |
| Shade Tint 2 | ShadeTint2 | float3 | `_ShadeTint2` | 2nd shade tint (multiplies the 1st shade) |
| Shade Shift 2 | ShadeShift2 | float | `_ShadeShift2` | position of the 2nd border |
| Shade Soft 2 | ShadeSoft2 | float | `_ShadeSoft2` | half width of the 2nd soft step |
| Use Shade Texture | UseShadeTexture | float | `_UseShadeTexture` ("Use Shade Map") | 1 = shade colour from the shade texture, 0 = from the base colour |
| Receive Shadow | ReceiveShadow | float | `_ReceiveShadow` | cast-shadow strength (0 = ignore cast shadows) |
| Normal Override | NormalOverride | float3 | `_NormalOverride` | optional normal override |
| Normal Override Mix | NormalOverrideMix | float | `_NormalOverrideMix` | share of the override (0 = off) |
| Lit Tint | LitTint | float3 | `_LitTint` (HDR colour, linear, used as it is) | tint of the lit side; values above 1 are allowed |
| Rim Color | RimColor | float3 | `_RimColor` | rim light colour (added) |
| Rim Strength | RimStrength | float | `_RimStrength` | rim strength |
| Rim Width | RimWidth | float | `_RimWidth` | rim width on 1 - N.V |
| Rim Soft | RimSoft | float | `_RimSoft` | rim softness |
| Rim Lit Bias | RimLitBias | float | `_RimLitBias` | 0 = rim all around, 1 = rim only on the lit side |
| Spec Color | SpecColor | float3 | `_SpecColor` | soft specular colour (added) |
| Spec Strength | SpecStrength | float | `_SpecStrength` | specular strength |
| Spec Size | SpecSize | float | `_SpecSize` | N.H threshold (closer to 1 = smaller) |
| Spec Soft | SpecSoft | float | `_SpecSoft` | specular edge softness |
| MatCap Add Strength | MatCapAddStrength | float | `_MatCapAddStrength` | strength of the additive MatCap |
| MatCap Mul Strength | MatCapMulStrength | float | `_MatCapMulStrength` | strength of the multiplicative MatCap (0.5 in the texture = no change) |
| Unlit | Unlit | float | `_Unlit` | share of the plain base colour, independent of light (eyes, gems) |
| Highlight Knee | HighlightKnee | float | `_HighlightKnee` | the brightest channel above this rolls off toward 1.0 (1 = off) |
| Occlusion Shift | OcclusionShift | float | `_OcclusionShift` | how far baked occlusion pushes N.L down |
| Occlusion Darken | OcclusionDarken | float | `_OcclusionDarken` | extra 2nd-shade tint in occluded areas |
| Terminator Color | TerminatorColor | float3 | `_TerminatorColor` | colour of the thin band at the light / shade border (multiply) |
| Terminator Strength | TerminatorStrength | float | `_TerminatorStrength` | band strength |
| Terminator Width | TerminatorWidth | float | `_TerminatorWidth` | band width on N.L |
| Base Lift | BaseLift | float | `_BaseLift` | pull the base colour toward Base Lift Color |
| Base Lift Color | BaseLiftColor | float3 | `_BaseLiftColor` | target of the lift |
| Base Saturation | BaseSaturation | float | `_BaseSaturation` | saturation of the base colour (1 = unchanged) |

Colours: Blender colours are RGBA, only RGB is used. The values in a Blender material are linear. Unity shows normal
colours as sRGB in the inspector and converts them (linear colour space); `_LitTint` / `_L2_LitTint` are HDR colours and
are used unchanged. Unreal vector parameters are linear.

## Per-pixel inputs (`AngelToonInput`, 12)

| HLSL / Custom-node pin | Blender | Unity | Unreal |
|---|---|---|---|
| N | the shading normal inside the group (custom split normals), flipped toward the viewer on back faces | world normal, flipped on back faces | vertex normal x TwoSidedSign |
| L | direction to the key light (a sun) | URP main light direction, or `_AngelToonKeyDirWS` when `_AngelToonKeyOverride` = 1 | `MPC_LidaAngelToon` KeyDir, or KeyDirOverride when KeyOverride = 1 |
| V | direction to the camera | view direction (orthographic: the camera back axis) | CameraVector |
| KeyColor | key light colour (white) | URP main light colour, or `_AngelToonKeyColor` | MPC KeyColor |
| ShadowedNL | from the group's shadow probe (1.25 x N.L when unshadowed, see SPEC 5) | `saturate(N.L) x main light shadow x _ShadowGain` | `saturate(N.L) x 1 x ShadowGain` (no cast shadows) |
| BaseColor | group input **Base Color** | `_BaseMap` x `_BaseColor` | BaseMap x BaseColor |
| ShadeTexture | group input **Shade Texture** | `_ShadeMap` x `_ShadeMapColor` | ShadeMap x ShadeColor |
| Occlusion | group input **Occlusion** | mask R | mask R |
| ReceiveShadowMask | (part of the receive strength of the material) | mask A when `_ReceiveShadowUseMaskA` = 1, else 1 | mask A when ReceiveShadowUseMaskA = 1, else 1 |
| MatCapAdd | group input **MatCap Add** | `_MatCapAddMap` x `_MatCapAddColor` | MatCapAddMap, or MatCapAddColor |
| MatCapMul | group input **MatCap Mul** | `_MatCapMulMap` x `_MatCapMulColor` | MatCapMulMap, or MatCapMulColor |
| MatCapAddMask | group input **MatCap Add Mask** | mask A when `_MatCapAddUseMaskA` = 1, else 1 | mask A when MatCapAddUseMaskA = 1, else 1 |

MatCap textures are sRGB, sampled with clamp at the edges; the UV comes from the view-space normal
(`AngelToonMatCapUV` in Unity, `AngelToonMatCapUV_UE` in Unreal, where V is flipped).
