# LidaAngelToon for Unreal Engine 5

Tested with **UE 5.8** on Windows. The assets are not shipped as `.uasset` files: a Python script builds them in your
project from the files of this folder.

## Contents (`LidaAngelToon/`, copy it to `Content/LidaAngelToon`)

| File | Content |
|---|---|
| `Python/lidaangeltoon_ue_build.py` | builds every generic asset (below) with the Unreal Python API (editor only) |
| `Python/lidaangeltoon_ue_instances.py` | helpers: `make_instance`, `core_values` (the 32 values with their spec names), `import_texture_file` (texture import with the right sRGB / compression / sampling) |
| `Source/hlsl/LidaAngelToon_UECustom_Shade.txt`, `..._OutlineWidth.txt` | Custom-node bodies generated from the core (`core/scripts/make_ue_custom338.py`); do not edit by hand |
| `Source/hlsl/LidaAngelToon_UESnippet_*.txt` | small Custom-node bodies used by the build (normal, MatCap UV, dither, outline mask, outline view, shadowed N.L) |
| `Source/hlsl/LidaAngelToonCore.hlsl` | a copy of `core/LidaAngelToonCore.hlsl` (reference) |
| `Source/textures/T_LidaAngelToon_*.png` | 4 x 4 default textures (white, black, grey 0.5, default mask) - the build writes them again |

## Build

1. Copy `LidaAngelToon` to `Content/LidaAngelToon` (asset paths are fixed to `/Game/LidaAngelToon/...`).
2. Enable the **Python Editor Script Plugin** (Edit > Plugins), restart the editor.
3. Run the build, as a commandlet:

   ```
   UnrealEditor-Cmd.exe <Project>.uproject -run=pythonscript -script=<Project>/Content/LidaAngelToon/Python/lidaangeltoon_ue_build.py
   ```

   or from the editor (Output Log > Python: `py "<path>/lidaangeltoon_ue_build.py"`). The first build compiles the shaders
   (a few minutes).

Optional environment variables: `LIDAANGELTOON_HLSL_DIR` (default `../Source/hlsl` next to the script),
`LIDAANGELTOON_SOURCE_DIR` (default `../Source`), `LIDAANGELTOON_REBUILD=1` (rebuild existing LidaAngelToon assets in
place; without it the script stops when an asset exists; assets are never deleted - the header comment of the script
says "delete and rebuild", the code rebuilds in place), `LIDAANGELTOON_BUILD_REPORT=<file.json>` (writes a report).

## Assets built

| Asset | Content |
|---|---|
| `Materials/M_LidaAngelToon` | Unlit, Opaque. Custom node `LidaAngelToon_Shade` (= `AngelToonShade`), a second one for two-layer materials (static switch `TwoLayer`, mixed by mask G). Textures BaseMap (x BaseColor), ShadeMap (x ShadeColor), MatCapAddMap / MatCapMulMap or their colours (`UseMatCapAddMap`, `UseMatCapMulMap`), AngelToonMask (linear). Static switch `MaskFromVertexColor`. N = vertex normal x TwoSidedSign, V = CameraVector, MatCap UV from the view-space normal with V flipped. No cast shadows. In a Masked instance: `AlphaDither` (0 = cut at `AlphaCutoff`, 1 = temporal dither resolved by TSR), `AlphaCutoff` |
| `Materials/M_LidaAngelToon_Translucent` | the same, translucent (opacity = BaseMap.a x BaseColor.a) |
| `Materials/M_LidaAngelToon_Outline` | Unlit, Masked, Two Sided inverted hull: back faces only, World Position Offset = normal x width from `LidaAngelToon_UECustom_OutlineWidth`. `OutlineWidthMM`, `OutlineGain` (1.5), `OutlineMinPx`, `OutlineMaxPx`, `OutlinePixelRule` (1 = rule B, 0 = world mm), `OutlineVisible`, `OutlineTint`, `L2_OutlineTint`, mask B > 0.5 only |
| `Materials/M_LidaAngelToon_MultiplyLayer` | Unlit, Modulate: `dst x lerp(1, LayerColor, BaseMap.a x LayerStrength)` (painted shadow layers) |
| `MPC_LidaAngelToon` | KeyDir, KeyDirOverride (direction TO the light, UE world), KeyOverride (0), KeyColor (white), ShadowGain (1.25), AmbientMix (0), AmbientColor, ExposureLock (0) |
| `Blueprints/BP_LidaAngelToonKeyLight` | writes -(forward of its KeyLight) to KeyDir on Tick and in the construction script; KeyLight empty = the first Directional Light at BeginPlay |
| `Textures/T_LidaAngelToon_*` | default textures (uncompressed, no mips) |

## Use

- **Material Instances**: parent `M_LidaAngelToon` (or `_Translucent`). Example (editor Python):

  ```python
  import unreal, lidaangeltoon_ue_instances as ati
  parent = unreal.load_asset('/Game/LidaAngelToon/Materials/M_LidaAngelToon')
  base = ati.import_texture_file('<folder>/base.png', '/Game/MyChar/Textures', 'T_Base', 'base')      # sRGB
  mask = ati.import_texture_file('<folder>/mask.png', '/Game/MyChar/Textures', 'T_Mask', 'mask_bc7')  # linear RGBA
  sc, ve = ati.core_values({...all 32 values by their spec names...})
  ati.make_instance('/Game/MyChar/Materials/MI_Cloth', parent, sc, ve,
                    {'BaseMap': base, 'AngelToonMask': mask}, {'MaskFromVertexColor': False})
  ```
  (The script folder must be on the Python path, for example `sys.path.append(<Content/LidaAngelToon/Python>)`.)
- **Key light**: put a Directional Light and `BP_LidaAngelToonKeyLight` in the level. To fix the character light, set
  MPC KeyOverride = 1 and KeyDirOverride. The light intensity is not used (KeyColor in the MPC is the colour).
- **Outline**: add a second Skeletal Mesh Component with the same mesh, outline instances per material slot,
  `Set Leader Pose Component` (the body). No shadow casting, Affect Dynamic Indirect Lighting off.
- **Cut-out parts** (for example feathers): an instance with Blend Mode override = Masked, AlphaDither 0, AlphaCutoff 0.5.
- **Post process / Lumen**: see [../docs/COLOR-AND-TONEMAP.md](../docs/COLOR-AND-TONEMAP.md) (Exposure Compensation 0,
  Tone Curve Amount 0, ...; Affect Dynamic Indirect Lighting and Affect Distance Field Lighting off on character
  components with Lumen).

## Notes from the tests

- Skeletal mesh FBX: authoring in **centimetres** worked at Actor scale 1 with or without Convert Scene Unit. A metre
  FBX came in at 1/100 with the legacy FBX import, and its small morph target deltas were dropped (blinks and mouth
  shapes broke); with the cm FBX they worked. (The cause was inferred from the Morph Threshold Position of the import.)
- UE replaces `.` in bone names with `_`. Shape keys with the same name on several meshes of one skeletal mesh become
  one morph target.
- Unreal may import a bluish colour texture as a normal map; `import_texture_file` sets the compression before sRGB
  and stops if the settings did not stick.
- Inside one skeletal mesh, translucent sections cannot be sorted per section (Translucent Sort Priority is per
  component).
- The outline pushes along the imported normals; hard edges can show small gaps (no smoothed-normal channel in 0.1.0).
- Unreal receives no cast shadows with these Unlit materials.

## License

Lida Attribution License 1.0 (the full text and the source notice are in `LidaAngelToon/LICENSE.md`; keep that
file in `Content/LidaAngelToon`). Commercial use, modification and redistribution, also inside a project, a
game or with an avatar, are allowed; keep `LICENSE.md`, the SPDX / copyright lines and the source URL, and
describe your main changes. Results made with the shader need no credit.

## Not included

- The `.uasset` files of a test project: they are UE-version-specific binaries, and the texture assets store the
  absolute source path of the machine that imported them. Run the build script instead.
- A character preset tool (it converts an unpublished character material table) and any character data.
- The default value of `LayerColor` in the multiply-layer material and the shader defaults are the values of the
  reference look; set your own values in the instances.
