// ============================================================================
// LidaAngelToonOutlinePass.hlsl  -  LidaAngelToon for Unity URP: inverted-hull outline (LightMode SRPDefaultUnlit)
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// The hull is the same mesh pushed along its (smoothed) normal; the pass culls front faces so only the
// back of the hull shows around the silhouette. Width (spec v1 section 9):
//   _OutlinePixelRule = 1: px = clamp(gain x width / (world size of one pixel), min px, max px), pushed on screen
//   _OutlinePixelRule = 0: the plain world width (millimetres), like the Blender Solidify reference
// Colour = base colour x tint (unlit), or a fixed colour. Drawn only where mask B > 0.5.
// ============================================================================
#ifndef LIDA_ANGEL_TOON_OUTLINE_PASS_INCLUDED
#define LIDA_ANGEL_TOON_OUTLINE_PASS_INCLUDED

#include "LidaAngelToonInput.hlsl"

struct AngelToonOutlineAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float4 tangentOS  : TANGENT;
    float2 uv         : TEXCOORD0;
    float3 outlineTS  : TEXCOORD3;      // smoothed normal in tangent space (optional)
    float4 color      : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct AngelToonOutlineVaryings
{
    float4 positionCS : SV_POSITION;
    float2 uv         : TEXCOORD0;
    float4 color      : TEXCOORD1;
    float  fogFactor  : TEXCOORD2;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

AngelToonOutlineVaryings AngelToonOutlineVertex(AngelToonOutlineAttributes v)
{
    AngelToonOutlineVaryings o = (AngelToonOutlineVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);

    float3 nOS = AngelToonOutlineNormalOS(v.normalOS, v.tangentOS, v.outlineTS);
    float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
    float3 nWS = AngelToonSafeNormalize(TransformObjectToWorldNormal(nOS));
    float widthWorld = _OutlineWidthMM * 0.001;
    float4 positionCS;
    UNITY_BRANCH if (_OutlinePixelRule > 0.5)
    {
        positionCS = TransformWorldToHClip(positionWS);
        float3 nVS = TransformWorldToViewDir(nWS, false);
        float2 nCS = mul((float3x3)UNITY_MATRIX_P, nVS).xy;
        // projection [1][1] can be negative when the target is flipped; the size of a pixel uses its magnitude
        float pixelWorld = AngelToonPixelWorldSize(positionCS.w, abs(UNITY_MATRIX_P[1][1]), _ScreenParams.y);
        float px = AngelToonOutlinePixels(widthWorld, pixelWorld, _OutlineGain, _OutlineMinPx, _OutlineMaxPx);
        positionCS = AngelToonOutlinePushClip(positionCS, nCS, px, _ScreenParams.xy);
    }
    else
    {
        positionCS = TransformWorldToHClip(positionWS + nWS * widthWorld);
    }
    // disabled outline: put the vertex outside the clip volume
    positionCS = (_OutlineEnabled > 0.5) ? positionCS : float4(2.0, 2.0, 2.0, 1.0);
    o.positionCS = positionCS;
    o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
    o.color = v.color;
    o.fogFactor = ComputeFogFactor(positionCS.z);
    return o;
}

float4 AngelToonOutlineFragment(AngelToonOutlineVaryings i) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    float4 base = AngelToonSampleBase(i.uv);
    float4 mask = AngelToonSampleMask(i.uv, i.color);
    clip(AngelToonOutlineVisible(mask.b) - 0.5);
#if defined(_ANGELTOON_ALPHA_CLIP)
    clip(base.a - _Cutoff);
#endif
    float3 tint = _OutlineTint.rgb;
#if defined(_ANGELTOON_TWO_LAYER)
    tint = AngelToonMix3(_OutlineTint.rgb, _OutlineTintL2.rgb, mask.g);
#endif
    float3 col = (_OutlineUseFixedColor > 0.5) ? _OutlineFixedColor.rgb : AngelToonOutlineColor(base.rgb, tint);
    col = MixFog(col, i.fogFactor);
#if defined(_SURFACE_TYPE_TRANSPARENT)
    return float4(col, base.a);
#else
    return float4(col, 1.0);
#endif
}

#endif // LIDA_ANGEL_TOON_OUTLINE_PASS_INCLUDED
