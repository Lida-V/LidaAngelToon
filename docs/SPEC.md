# LidaAngelToon specification v1

The rules that make the Unity and Unreal versions of **LidaAngelToon** look like the Blender reference (node group
`LidaSoftToon`). Japanese original: [SPEC.ja.md](SPEC.ja.md). Character-specific material names, per-material values,
textures and paths are not part of this specification; they belong to the materials (Unity materials / presets,
Unreal Material Instances).

Names: Unity `LidaAngelToon/Toon`, `LidaAngelToon/Toon Transparent`; Unreal `M_LidaAngelToon`,
`M_LidaAngelToon_Translucent`, `M_LidaAngelToon_Outline`, `M_LidaAngelToon_MultiplyLayer`, `MPC_LidaAngelToon`.
The Blender node group keeps its name `LidaSoftToon`; its math is the math below.

## 1. Files

| File | Content |
|---|---|
| `core/LidaAngelToonCore.hlsl` | the shared formula as pure functions (Unity includes it; Unreal uses generated Custom-node text). ASCII only |
| `core/scripts/core_reference.py` | the same formula in numpy, step tags `[S01]`..`[S24]` shared with the HLSL |
| `core/scripts/make_ue_custom.py` | generates the Unreal Custom-node text from the core |
| `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_Shade.txt` | Custom-node body that returns the colour (do not edit by hand) |
| `unreal/LidaAngelToon/Source/hlsl/LidaAngelToon_UECustom_OutlineWidth.txt` | Custom-node body that returns the outline push length (cm) |

## 2. Shading, step by step

All colours are **linear**. sRGB textures are decoded when sampled. The result is a linear emission colour before
bloom and tone mapping.

1. **Directions**: N (surface normal), L (to the key light), V (to the camera). N.L in -1..1.
2. **Cast shadow**: lower N.L only inside shadows: `NLs = min(N.L, shadowed N.L)`, then
   `Ls0 = mix(N.L, NLs, ReceiveShadow)`. The engines compute the shadowed N.L as `saturate(N.L) x shadow x 1.25`
   (`AngelToonShadowedNL`); 1.25 is measured from Blender (section 5).
3. **Baked occlusion** (mask R, 1 = open): `occ = smoothstep(0.05, 0.9, 1 - AO)`, `Ls = Ls0 - occ x OcclusionShift`.
4. **Two soft steps**: `t1 = smoothstep(Shift1 - Soft1, Shift1 + Soft1, Ls)` (lit <-> shade 1),
   `t2 = smoothstep(Shift2 - Soft2, Shift2 + Soft2, Ls)` (shade 1 <-> shade 2).
5. **Base colour**: lift `mix(Base, BaseLiftColor, BaseLift)`, then saturation `mix(luma, colour, BaseSaturation)`
   (Rec.709 luma 0.2126729, 0.7151522, 0.0721750).
6. **Shade colours**: `shade1 = (UseShadeTexture ? shade texture : base) x ShadeTint1`, `shade2 = shade1 x ShadeTint2`,
   `lit = base x LitTint x key colour`.
7. **Mix**: `C = mix(mix(shade2, shade1, t2), lit, t1)`.
8. **Terminator band**: a hat-shaped band of half width TerminatorWidth around Shift1 mixes `C x TerminatorColor`
   in by TerminatorStrength (for example a faint warm band on skin).
9. **Occlusion tint**: `mix(C, C x ShadeTint2, occ x OcclusionDarken)`. Rim, specular and MatCap below are
   multiplied by `open = 1 - occ`.
10. **Rim**: `smoothstep(1 - W - S, 1 - W + S, 1 - max(N.V, 0)) x mix(1, t1, RimLitBias) x RimStrength x open`, added
    with RimColor.
11. **Specular**: `H = normalize(L + V)`, `smoothstep(Size - Soft, Size + Soft, max(N.H, 0)) x t1 x SpecStrength x open`,
    added with SpecColor.
12. **MatCap**: multiply `mix(C, C x MatCapMul x 2, MatCapMulStrength)` (0.5 = no change), then add
    `C + MatCapAdd x (MatCapAddStrength x mask x open)`.
13. **Unlit share**: `mix(C, base, Unlit)` (eyes, mouth, gems).
14. **Highlight Knee**: if the brightest channel m is above k = HighlightKnee, it is mapped to
    `k + (1 - k)(1 - exp(-(m - k)/(1 - k)))` and all channels are scaled by the same factor (keeps the hue).
15. Blend factors are clamped to 0..1 where Blender's Mix node clamps them. `smoothstep` returns 0 when the two edges
    are equal (Blender Map Range).

The code: `AngelToonShade()` in `core/LidaAngelToonCore.hlsl`.

## 3. Inputs

32 per-material values and 12 per-pixel inputs. Names in Blender, HLSL, Unity and Unreal:
[BLENDER-NODE-MAPPING.md](BLENDER-NODE-MAPPING.md). Colour inputs use RGB only. LitTint may be above 1.

Textures:

| Content | Unity | Unreal |
|---|---|---|
| base map (UV0, sRGB) | `_BaseMap` (x `_BaseColor`) | BaseMap (x BaseColor) |
| shade map (UV0, sRGB) | `_ShadeMap` (x `_ShadeMapColor`) | ShadeMap (x ShadeColor) |
| MatCap add (sRGB, clamp, bilinear) | `_MatCapAddMap` / `_MatCapAddColor` | MatCapAddMap or MatCapAddColor (`UseMatCapAddMap`) |
| MatCap multiply | `_MatCapMulMap` / `_MatCapMulColor` (0.5 = no change) | MatCapMulMap or MatCapMulColor (`UseMatCapMulMap`) |
| mask (section 4) | `_AngelToonMask` (+ "Use Mask Texture") | AngelToonMask |
| what mask A is used for | `_ReceiveShadowUseMaskA`, `_MatCapAddUseMaskA` | ReceiveShadowUseMaskA, MatCapAddUseMaskA |
| two-layer material | `_TwoLayer` and the `_L2_` set | static switch TwoLayer and the `L2_` set |

No MatCap texture is shipped; the MatCap colours alone also work.

## 4. Mask texture `_AngelToonMask`

RGBA, 8-bit, **linear (sRGB off)**, UV0 (the UV of the base map), 2048 or less (512 to 1024 is usually enough).

| Channel | Meaning | Without a mask |
|---|---|---|
| R | baked occlusion, 1 = open | 1 |
| G | weight of the second layer (1 = layer B, 0 = layer A) | 0 |
| B | where the outline is drawn (above 0.5 only; for example 0 inside the eyes and mouth) | 1 |
| A | per material: the area that receives cast shadows (for example only the neck under a face) or the area of the additive MatCap (for example a hair highlight band); unused otherwise | 1 |

Per-material colour work that sits before "Base Color" in Blender (blush, hair root-to-tip colour, ...) is baked into
the base map, not done in the shader. Per-vertex values made in Blender (for example baked AO) are baked into the mask.

## 5. Key light, cast shadows, ambient, bloom, display

- **Key light**: one directional light; its direction and colour are used. In Blender the light energy only enters the
  shadow calibration, not the colour. The reference scene lights the character from its right, front and above
  (right 0.669, front 0.526, up 0.526); for the reference images the light turned with the camera (always from the upper
  left front of the frame).
  - The engines use the scene's main light and offer an override for a character light (Unity `_AngelToonKeyDirWS`,
    `_AngelToonKeyColor`, `_AngelToonKeyOverride`; Unreal `MPC_LidaAngelToon` KeyDir, KeyDirOverride, KeyOverride, KeyColor).
- **Cast shadows**: Unity receives them (mask A can limit where); Unreal does not (Unlit). **Gain 1.25**
  (`_ShadowGain`, Unreal MPC ShadowGain). The Blender group measures cast shadows as "diffuse brightness / 0.25464";
  in Blender 5.2.1 EEVEE an unshadowed point gives N.L x 1/pi / 0.25464 = **1.25 x N.L**, so shading only changes where
  the shadow is darker than 0.8 (the outer penumbra is a little narrower). Multiply by 1.25 in the engines to match;
  use 1.0 for a plain N.L x shadow.
- **Ambient**: 0 in Blender. The engines have an optional share (`_AngelToonAmbientMix`, Unreal AmbientMix); use 0 to compare.
- **Bloom**: a scene choice. Compare without bloom.
- **Display**: Blender "Standard" (no tone curve, sRGB display, exposure 0, gamma 1). Unity: Linear + Tonemapping None.
  Unreal: the post-process set in [COLOR-AND-TONEMAP.md](COLOR-AND-TONEMAP.md).
- Screen-space AO is not used.

## 6. Orientation (watch left / right, up / down)

- **N**: Blender flips N toward the viewer on back faces (a plate whose front faces away, seen from the front, is lit
  with a normal toward the viewer). Double-sided materials (feathers, thin cloth) must do the same in the engines
  (Unity `VFACE` / `SV_IsFrontFace`, Unreal TwoSidedSign). In Blender N is the custom split normal.
- **L, V**: from the shaded point to the light / camera. Orthographic V = the camera back axis.
- **MatCap**: normalised view-space normal, `uv = n.xy x 0.5 + 0.5`. Blender and Unity view space are right-handed
  (+X right, +Y up, +Z toward the viewer) and UV (0,0) is the bottom left. Unity:
  `AngelToonMatCapUV(mul((float3x3)UNITY_MATRIX_V, N))`. **Unreal view space is left-handed (+Z away) and V = 0 is the top
  row**: use `AngelToonMatCapUV_UE()` (V flipped). Check with a test MatCap (red grows to the right, green upward, a white
  dot at the upper right): on a sphere the red must grow toward screen right, green upward, the dot at the upper right.
- **Coordinates** (common FBX settings, character facing forward; always check with the marks above): Blender (x, y, z)
  -> Unity (-x, z, -y) (the character faces +Z). In Unreal it depends on the import orientation; set the light by its
  direction relative to the character.
- Checks: (1) the key light comes from the upper left front of the frame (on a front view the face's cheek on the left
  of the image is lit); (2) the MatCap test colours; (3) a back-facing plate is lit; (4) the shadow of a sphere falls in
  the middle of the plate below it.

## 7. Two-layer materials

Blender shades layer A and layer B **separately to the end** (including the roll-off) and mixes the finished colours
by mask G (Mix Shader). HLSL: `AngelToonShadeTwoLayer`. Mixing the values first and shading once is not the same
(the formula is not linear). The outline tint is mixed by G as well.

## 8. Transparency and order

Opaque, cut-out and translucent are chosen per material. Translucent (blend) uses `LidaAngelToon/Toon Transparent`
(depth write selectable, `_QueueOffset`). Alpha = base map alpha. Fine cut-outs such as feathers worked best as
Alpha Clip + Alpha To Coverage (Unity, MSAA required) and Masked with cut-off 0.5 (Unreal); as translucent they sorted
wrong where they overlap.

## 9. Outline

Inverted hull, colour = base colour x tint, only where mask B > 0.5, width by rule B:
`pixels = clamp(1.5 x natural width / pixel world size, min px, max px)`. Details, limits by surface type, Unity and
Unreal set-up and the MToon equivalent: [OUTLINE-RULE-B.md](OUTLINE-RULE-B.md). Push along the welded (smoothed) vertex
normal where possible; split normals open gaps.

## 10. Multiply layer (painted shadow layer)

A layer that only multiplies what is below: `dst.rgb *= mix(1, layer colour, texture alpha)`. Drawn after the surface
it darkens, no depth write, no outline. Unity: `_MultiplyLayer` of `LidaAngelToon/Toon Transparent`. Unreal:
`M_LidaAngelToon_MultiplyLayer` (LayerColor, LayerStrength).

## 11. Test scene and reference images (not included)

Blender test scene: 13 spheres (radius 0.1 m, smooth UV sphere 128 x 64: one per kind of material, one two-layer, one
MatCap orientation test), 2 plates (cast shadow, back face) and a character face. Sphere AO: 1 on the upper half, down
to 0.1 at the bottom. Masks: 0 at the left edge to 1 at the right edge. Two orthographic cameras (1300 x 850 at 1 mm per
pixel; 800 x 800 for the face). Reference renders: 64 samples, filter 1.5 px, with and without bloom, PNG and linear
EXR; character views: full body front and oblique, face front and oblique, hair from behind, back, full body 1080p.
Compare the same camera and light without bloom. Suggested pass marks for the spheres and plates: mean 2/255 or less,
max 8/255 or less (shadow-edge and outline pixels excluded); the character by eye.

## 12. How close it is

The test scene rendered with 1 sample and no filter, all inputs of the group read back as AOVs, the colour recomputed
for the same pixels:

| | pixels | Python vs Blender (linear) | GPU HLSL vs Blender | GPU vs Python |
|---|---|---|---|---|
| spheres and plates, 15 materials | 488,460 | mean 0.00013, max 0.0025, sRGB max 1/255 | same (RTX 4090 and WARP) | max 0.0000015 |
| face (3 materials of a character face) | 340,292 | mean 0.00021, max 0.0011, max 1/255 | same | max 0.0000003 |

Also: luma weights within 0.0005, MatCap UV within 0.0006 (AOV precision), back-face N flipped toward the viewer,
MatCap orientation (red right, green up), shadow gain 1.2497 (median). Compiles with fxc (ps_5_0, vs_5_0) and dxc
(ps_6_0, vs_6_0); the Unreal Custom-node text wrapped like Unreal compiles with fxc and dxc.

In the engines (8-bit sRGB against Blender without bloom): Unity spheres and plates mean 0.10/255, face 0.33;
Unreal spheres and plates mean 0.43/255, face 0.64 to 0.80; a full character in 7 views Unity mean 2.4 to 2.7,
Unreal mean 1.9 to 3.2 (Unreal receives no cast shadows).

## 13. Pitfalls

- **Keep shader source ASCII.** DXC stopped with 0x80070459 on Japanese comments (Unreal's DXC is expected to do the
  same). Explanations live in the documents.
- Unreal pastes a Custom node inside a function, so the core's functions are members of a local struct in the
  generated text. Regenerate after any change of the core: `python -I core/scripts/make_ue_custom.py <repository root>`.
- Unreal works in cm: mm values x 0.1.
- Base, shade and MatCap textures are sRGB; the mask and other data textures are linear. MatCap clamps at the edges.
- Two-layer materials: shade twice and mix (do not mix the values).
- Shadow gain 1.25, ambient 0 (when comparing), no tone curve, no bloom when comparing.
- Unity URP 17.6 Forward+: body in `UniversalForward`, outline as a second pass `SRPDefaultUnlit` (front faces culled),
  plus `ShadowCaster`, `DepthOnly`, `DepthNormals`. Pixel rule on by default.

## 14. Known differences

- Blender's cast shadows are soft (sun angle 6 degrees, jitter); engine shadow maps have other edges. The use of the
  shadow value is the same.
- The 1/pi diffuse probe value was measured in Blender 5.2.1 EEVEE; 0.25464 is the calibration inside the group. The
  spec follows what Blender shows (1.25).
- The Blender sample of the outline rule used one width per object (at the object's centre depth); the engines compute
  it per vertex, so objects with a large depth range (skirts) differ a little.
