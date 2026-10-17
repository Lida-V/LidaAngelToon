// ============================================================================
// LidaAngelToonInput.hlsl  -  LidaAngelToon for Unity URP: material, texture and global inputs
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// All passes of LidaAngelToon/Toon and LidaAngelToon/Toon Transparent include this file, so the
// UnityPerMaterial constant buffer has the same layout in every pass (SRP Batcher compatible).
// Colour properties are declared as Color in ShaderLab; in a Linear colour space project Unity
// delivers them here as linear values. All maths is linear (see LidaAngelToonCore.hlsl).
// ============================================================================
#ifndef LIDA_ANGEL_TOON_INPUT_INCLUDED
#define LIDA_ANGEL_TOON_INPUT_INCLUDED

#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Core.hlsl"
#include "LidaAngelToonCore.hlsl"

// The 32 per-layer values of the spec (section 3). Layer A = "_<Name>", layer B = "_L2_<Name>".
#define ANGELTOON_LAYER_CBUFFER(P) \
    float4 P##ShadeTint1; float P##ShadeShift1; float P##ShadeSoft1; \
    float4 P##ShadeTint2; float P##ShadeShift2; float P##ShadeSoft2; \
    float  P##UseShadeTexture; float P##ReceiveShadow; \
    float4 P##NormalOverride; float P##NormalOverrideMix; \
    float4 P##LitTint; \
    float4 P##RimColor; float P##RimStrength; float P##RimWidth; float P##RimSoft; float P##RimLitBias; \
    float4 P##SpecColor; float P##SpecStrength; float P##SpecSize; float P##SpecSoft; \
    float  P##MatCapAddStrength; float P##MatCapMulStrength; float P##Unlit; float P##HighlightKnee; \
    float  P##OcclusionShift; float P##OcclusionDarken; \
    float4 P##TerminatorColor; float P##TerminatorStrength; float P##TerminatorWidth; \
    float  P##BaseLift; float4 P##BaseLiftColor; float P##BaseSaturation;

#define ANGELTOON_FILL_MATERIAL(m, P) \
    m.ShadeTint1 = P##ShadeTint1.rgb; m.ShadeShift1 = P##ShadeShift1; m.ShadeSoft1 = P##ShadeSoft1; \
    m.ShadeTint2 = P##ShadeTint2.rgb; m.ShadeShift2 = P##ShadeShift2; m.ShadeSoft2 = P##ShadeSoft2; \
    m.UseShadeTexture = P##UseShadeTexture; m.ReceiveShadow = P##ReceiveShadow; \
    m.NormalOverride = P##NormalOverride.xyz; m.NormalOverrideMix = P##NormalOverrideMix; \
    m.LitTint = P##LitTint.rgb; \
    m.RimColor = P##RimColor.rgb; m.RimStrength = P##RimStrength; m.RimWidth = P##RimWidth; \
    m.RimSoft = P##RimSoft; m.RimLitBias = P##RimLitBias; \
    m.SpecColor = P##SpecColor.rgb; m.SpecStrength = P##SpecStrength; m.SpecSize = P##SpecSize; m.SpecSoft = P##SpecSoft; \
    m.MatCapAddStrength = P##MatCapAddStrength; m.MatCapMulStrength = P##MatCapMulStrength; \
    m.Unlit = P##Unlit; m.HighlightKnee = P##HighlightKnee; \
    m.OcclusionShift = P##OcclusionShift; m.OcclusionDarken = P##OcclusionDarken; \
    m.TerminatorColor = P##TerminatorColor.rgb; m.TerminatorStrength = P##TerminatorStrength; \
    m.TerminatorWidth = P##TerminatorWidth; \
    m.BaseLift = P##BaseLift; m.BaseLiftColor = P##BaseLiftColor.rgb; m.BaseSaturation = P##BaseSaturation;

CBUFFER_START(UnityPerMaterial)
    float4 _BaseMap_ST;
    float4 _BaseColor;              // multiplies _BaseMap (rgb = colour, a = alpha)
    float4 _ShadeMapColor;          // multiplies _ShadeMap (the constant shade colour when there is no map)
    float4 _MatCapAddColor;         // multiplies _MatCapAddMap (the constant when there is no map; default black = off)
    float4 _MatCapMulColor;         // multiplies _MatCapMulMap (the constant when there is no map; 0.5 = no change)
    float4 _L2_MatCapAddColor;      // layer B: multiplies the same additive MatCap map
    float4 _L2_MatCapMulColor;      // layer B: multiplies the same multiplicative MatCap map
    float  _UseAngelToonMask;       // 0 = no mask texture: (R, G, B, A) = (1, 0, 1, 1)
    float  _ReceiveShadowUseMaskA;  // 1 = cast shadows are received where mask A says so
    float  _MatCapAddUseMaskA;      // 1 = the additive MatCap applies where mask A says so
    float  _ShadowGain;             // spec v1: 1.25 (Blender reference). 1.0 = plain N.L x shadow
    ANGELTOON_LAYER_CBUFFER(_)
    ANGELTOON_LAYER_CBUFFER(_L2_)
    float  _OutlineEnabled;
    float  _OutlineWidthMM;         // natural width in millimetres (the Blender world width)
    float  _OutlinePixelRule;       // 1 = spec v1 pixel rule (default), 0 = plain world width
    float  _OutlineGain;            // spec v1: 1.5
    float  _OutlineMinPx;
    float  _OutlineMaxPx;
    float  _OutlineNormalSource;    // 0 = vertex normal, 1 = smoothed normal stored in UV3 (tangent space)
    float  _OutlineUseFixedColor;   // 1 = _OutlineFixedColor instead of base colour x tint
    float4 _OutlineTint;            // line colour = base colour x tint
    float4 _OutlineTintL2;          // two-layer materials: tint of layer B (mixed by mask G)
    float4 _OutlineFixedColor;
    float  _Cutoff;                 // alpha clip (cutout materials; transparent shader: the shadow caster)
    float  _AlphaToMask;            // cutout: 1 = alpha to coverage (MSAA) for the soft edge
    float4 _MultiplyColor;          // transparent shader, multiply layer: dst *= mix(1, colour, alpha)
CBUFFER_END

TEXTURE2D(_BaseMap);        SAMPLER(sampler_BaseMap);
TEXTURE2D(_ShadeMap);
TEXTURE2D(_MatCapAddMap);
TEXTURE2D(_MatCapMulMap);
TEXTURE2D(_AngelToonMask);  SAMPLER(sampler_AngelToonMask);

// Globals (set by the AngelToonGlobals component or Shader.SetGlobal*). Unset = 0 = off.
float4 _AngelToonKeyDirWS;      // direction TO the character key light (world)
float4 _AngelToonKeyColor;      // linear colour of the character key light
float  _AngelToonKeyOverride;   // 1 = use the two values above instead of the URP main light direction / colour
float  _AngelToonAmbientMix;    // share of the ambient probe added on top (0 = like the Blender reference)
float  _AngelToonAddLightMix;   // share of the additional (point / spot) lights added on top (0 = off)
float  _AngelToonDebugMode;     // 0 = off, 1 base, 2 normal, 3 mask rgb, 4 mask a, 5 shadow, 6 MatCap UV

float4 AngelToonSampleBase(float2 uv)
{
    return SAMPLE_TEXTURE2D(_BaseMap, sampler_BaseMap, uv) * _BaseColor;
}

// Mask: R = occlusion (1 open), G = two-layer share (1 = layer B), B = outline (> 0.5 draws), A = per material
float4 AngelToonSampleMask(float2 uv, float4 vertexColor)
{
#if defined(_ANGELTOON_MASK_VERTEX_COLOR)
    return vertexColor;
#else
    float4 m = SAMPLE_TEXTURE2D(_AngelToonMask, sampler_AngelToonMask, uv);
    return (_UseAngelToonMask > 0.5) ? m : float4(1.0, 0.0, 1.0, 1.0);
#endif
}

// Smoothed outline normal stored in UV3 in tangent space (see AngelToonOutlineNormals.cs).
float3 AngelToonOutlineNormalOS(float3 normalOS, float4 tangentOS, float3 packedTS)
{
    float3 n = normalOS;
    UNITY_BRANCH if (_OutlineNormalSource > 0.5)
    {
        float3 t = tangentOS.xyz;
        float3 b = cross(normalOS, t) * (tangentOS.w >= 0.0 ? 1.0 : -1.0);
        float3 s = t * packedTS.x + b * packedTS.y + normalOS * packedTS.z;
        float l2 = dot(s, s);
        n = (dot(t, t) > 1e-8 && l2 > 1e-8) ? s * rsqrt(l2) : normalOS;
    }
    return n;
}

#endif // LIDA_ANGEL_TOON_INPUT_INCLUDED
