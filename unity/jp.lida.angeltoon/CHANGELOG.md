# Changelog

## [0.1.0] - 2026-10-15
- First version: LidaAngelToon/Toon and LidaAngelToon/Toon Transparent for URP 17 (spec v1 of LidaAngelToon).
- Passes: UniversalForward (body), SRPDefaultUnlit (inverted-hull outline), ShadowCaster, DepthOnly, DepthNormals.
- Editor: material sync / inspector, preset importer (LidaAngelToon.preset/1 JSON), smoothed outline normals in UV3.
- Runtime: AngelToonGlobals component (character key light override, ambient share, additional light share, debug views).
- Opaque shader: optional cutout (_AlphaClip, _Cutoff) with alpha to coverage (_AlphaToMask); transparent shader: optional multiply layer.
- Mask from vertex colour (keyword), additional lights and ambient share, fixed outline colour, debug views.
- Documentation~/LidaAngelToon.md, README.md.
