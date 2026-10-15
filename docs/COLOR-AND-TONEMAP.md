# Colour spaces, tone mapping and the comparison set-up

LidaAngelToon computes everything in **linear** colour and returns a linear emission colour **before** bloom and tone
mapping. The reference look is Blender with the view transform **"Standard"** (no tone curve, sRGB display, exposure 0,
gamma 1, look None). White-clipping is handled inside the shader by Highlight Knee, not by a tone curve.

## Textures

| Texture | Colour space | Sampling |
|---|---|---|
| Base map, shade map | sRGB (decoded to linear when sampled) | UV0 |
| MatCap (add / multiply) | sRGB | clamp at the edges, bilinear, no mip maps needed; multiply map: 0.5 = no change (sRGB code 188) |
| AngelToon mask (R occlusion, G layer, B outline, A per material) | **linear** (sRGB off) | UV0; keep all four channels (no single-channel compression); 2048 or less, 512 to 1024 is usually enough |

Unreal: the mask needs alpha, so use BC7 or an uncompressed format with sRGB off. Unreal can detect a bluish colour
texture as a normal map on import (compression Normalmap, sRGB off). While the compression is Normalmap, setting sRGB
on is ignored: set the compression first, then sRGB, and check the result (`lidaangeltoon_ue_instances.import_texture_file`
does this and stops if the settings did not stick).

## Material colours

- Blender material values are linear.
- Unity: normal colour properties are shown as sRGB in the inspector and converted in linear colour space;
  `_LitTint` / `_L2_LitTint` are `[HDR]` colours and are used as they are (enter linear values; values above 1 allowed).
  The preset loader converts linear preset colours for the normal properties and writes HDR colours unchanged.
- Unreal: vector parameters are linear.

## Unity set-up that matches Blender "Standard"

- Project: Linear colour space. URP asset: HDR on.
- Post-processing: Tonemapping **None**; bloom off for comparisons (bloom is a scene choice).
- `AngelToonGlobals`: Ambient Mix 0, Additional Light Mix 0 (defaults) - the reference has one light and no ambient.
- SSAO of the renderer is not used by LidaAngelToon (occlusion comes from mask R).
- MSAA 4x was used for the tests (needed for alpha to coverage).

## Unreal set-up that matches Blender "Standard"

The materials are Unlit (emissive). In a Post Process Volume (unbound) set:

| Setting | Value |
|---|---|
| Tone Curve Amount | 0 |
| Expand Gamut | 0 |
| Blue Correction | 0 |
| Vignette Intensity | 0 |
| Bloom Intensity | 0 (for comparisons) |
| Film Grain Intensity | 0 |
| **Exposure Compensation** | **0** (the UE5 default is +1, a factor of 2) |
| Auto exposure | off (fixed exposure) |

With these settings the test scene matched Blender within about 1/255 for plain colours. In scenes that keep auto
exposure, set `ExposureLock` = 1 in `MPC_LidaAngelToon`: the emission is divided by the current exposure so the
character keeps its brightness.

Lumen: with mesh distance fields, an Unlit emissive surface lights its surroundings like an emissive light. Turn off
**Affect Dynamic Indirect Lighting** and **Affect Distance Field Lighting** on the character components (in the
test this removed about a third); the part that comes from Lumen screen traces can only be changed with scene
settings. Substrate: the Unlit materials work with Substrate on.

## Comparing with Blender

Render the same camera (position, orientation, orthographic height or vertical FOV, resolution) and the same key
light, **without bloom**, tone curve off, ambient 0, and compare 8-bit sRGB. Expected differences: anti-aliasing of
thin lines and sharp texture details (Blender's 1.5 px filter vs MSAA / TSR), cast-shadow edges (soft sun vs shadow
maps; Unreal receives no cast shadows).
