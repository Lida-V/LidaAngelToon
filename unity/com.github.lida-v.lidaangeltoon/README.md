# LidaAngelToon for Unity (URP)

A soft two-step toon shader for the Universal Render Pipeline (URP 17, Unity 6).

- `LidaAngelToon/Toon` - opaque (optional cutout with alpha to coverage)
- `LidaAngelToon/Toon Transparent` - alpha blend (optional multiply layer)

Two soft shade steps with tint colours, a baked occlusion mask, rim light, soft specular, MatCap (add and multiply),
two-layer materials (for example cloth and skin in one material), a highlight roll-off ("Highlight Knee") and an
inverted-hull outline whose width stays between a minimum and a maximum number of screen pixels.
The shading core (`Runtime/Shaders/LidaAngelToonCore.hlsl`) is the same file as in the Unreal Engine version.

Status: 0.1.0, first version. License: Lida Attribution License 1.1 (`LicenseRef-Lida-Attribution-1.1`),
see `LICENSE.md`. Keep `LICENSE.md` when you redistribute this package or bundle it with an avatar, a model or a
game, and describe your main changes. Source: https://github.com/Lida-V/LidaAngelToon

## Name

- Shader name `LidaAngelToon` was chosen by the author (Lida).
- Package name `com.github.lida-v.lidaangeltoon` follows the Unity rule for package names (reverse-domain style,
  lower case) and is derived from the repository that publishes it (github.com/Lida-V/LidaAngelToon).
  The package folder has the same name.
- An earlier build of this version used the working name `jp.lida.angeltoon`. The code, the shader names and the
  asset GUIDs (`.meta`) are the same. If a project has the old folder, remove `Packages/jp.lida.angeltoon` before
  adding this one (two folders with the same GUIDs conflict); materials keep their shader.

## Install

Copy this folder into `Packages/` of a URP project, or add it with Package Manager > Add package from disk
(`package.json`). Requires Unity 6000.0 or later with URP 17.

## Quick start

1. Create a material with `LidaAngelToon/Toon`. Set Base Map and Base Color.
2. Optional: a mask texture (sRGB off, UV0) - R occlusion (1 = open), G layer (0 = layer A, 1 = layer B),
   B outline (1 = draw the outline here), A per material (receive shadow / MatCap add). Turn on "Use Mask Texture".
   Without a mask the shader uses R 1, G 0, B 1, A 1.
3. The outline is drawn by a second pass (LightMode `SRPDefaultUnlit`). It is on by default.
   Turn it off per material with the "Outline" toggle (the editor also disables the pass).

Character presets (all material values and textures of one character) can be loaded with
Tools > LidaAngelToon > Create Materials From Preset... (JSON format `LidaAngelToon.preset/1`).

See `Documentation~/LidaAngelToon.md` for every property and the details.
