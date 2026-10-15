# Outline rule B (spec v1): a faint outline that keeps its width in screen pixels

## Why

An inverted-hull outline with a fixed world width (for example 0.25 to 0.55 mm, as a Blender Solidify outline) is
about 0.3 px wide on a full-body 1080p frame, so it disappears; close to the face it gets thick. The goal of
LidaAngelToon is a **faint anime line that is visible at both distances** and is never black: the line colour is the
base colour under it, darkened by a tint.

## Rule

```
pixels      = clamp(gain x natural_width / pixel_world_size, min_px, max_px)       gain = 1.5
pixel_world_size = 2 x clip.w / (P[1][1] x screen_height_px)                        orthographic: clip.w = 1
```

- `natural_width`: the world width of the line of that material (the Blender reference width).
- `P[1][1]`: projection matrix element (perspective 1 / tan(vertical FOV / 2), orthographic 2 / view height).
- The hull vertex is pushed by `pixels` along the screen-projected normal (Unity: in clip space,
  `AngelToonOutlinePushClip`), or by `pixels x pixel_world_size` along the world normal (Unreal: World Position
  Offset).
- **Where**: only where mask B > 0.5 (no line inside the eyes / mouth, for example).
- **Colour**: `base colour x outline tint` (no lighting, no roll-off). In two-layer materials the tint is mixed by mask G.

Recommended limits by type of surface (the values used for the reference character):

| Surface | min px | max px |
|---|---|---|
| skin, cloth, hair (and other large parts) | 1.0 | 2.0 |
| face | 1.0 | 1.8 |
| small flowers / small decorations | 0.8 | 1.6 |
| thin metal / silver trims | 0.7 | 1.3 |

Typical result: full body at 1080p about 1 px (metal 0.7, small decorations 0.8); a close face shot (85 mm lens at
0.8 m, 800 px high) 1.4 to 2 px; the same framing at 1080p up to 2 px.

Turning the rule off (`_OutlinePixelRule` = 0 in Unity, `OutlinePixelRule` = 0 in Unreal) gives the plain world
width, for an exact comparison with a Blender Solidify outline.

## Unity

- Second pass of the same shader (LightMode `SRPDefaultUnlit`, front faces culled). Properties `_OutlineEnabled`,
  `_OutlineWidthMM`, `_OutlinePixelRule`, `_OutlineGain`, `_OutlineMinPx`, `_OutlineMaxPx`, `_OutlineTint`,
  `_OutlineTintL2`, `_OutlineUseFixedColor`, `_OutlineFixedColor`, `_OutlineNormalSource`.
- Split normals (hard edges) open gaps in the hull. Assets > LidaAngelToon > Outline Normals On Import bakes a smoothed
  normal into UV3 (tangent space; the importer must calculate tangents), then `_OutlineNormalSource` = 1.
- MSAA smooths the 1 px line.

## Unreal

- A second Skeletal Mesh Component with the same mesh, `Set Leader Pose Component` = the body, materials =
  instances of `M_LidaAngelToon_Outline` (Unlit, Masked, Two Sided; only back faces are kept). Do not let it cast
  shadows; turn off Affect Dynamic Indirect Lighting.
- Parameters `OutlineWidthMM` (Unreal works in cm: the shader uses mm x 0.1), `OutlineGain`, `OutlineMinPx`,
  `OutlineMaxPx`, `OutlinePixelRule`, `OutlineVisible`, `OutlineTint`, `L2_OutlineTint`.
- The width comes from the Custom node `LidaAngelToon_UECustom_OutlineWidth.txt`
  (generated from the core).
- The push uses the imported normals (no smoothed-normal channel in 0.1.0), so hard edges can show small gaps.

## VRM (MToon) with the same look

MToon has `outlineWidthMode = screenCoordinates`: the width is a share of the screen height. For the same faint
line: `outlineWidthFactor = target px / screen height`, for example 0.0011 (1.19 px at 1080p) for skin, cloth and
hair, 0.0010 for the face, 0.0008 for small decorations, 0.0007 for thin metal. Notes:

- UniVRM (MToon10) draws MToon outlines only when the URP renderer has `MToonOutlineRenderFeature`.
- UniVRM keeps the width constant up to about 1 / tan(vertical FOV / 2) metres and makes it thinner further away.
- MToon reads the outline width mask from the G channel, so an outline mask in B must be copied into G of a
  separate texture.
- The preview of the VRM Add-on for Blender (4.7.1) draws screenCoordinates widths as world widths (the line looks
  2 to 3 times thicker there); judge the width in the target application.
