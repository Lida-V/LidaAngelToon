// ============================================================================
// LidaAngelToonDepthPasses.hlsl  -  LidaAngelToon for Unity URP: ShadowCaster, DepthOnly and DepthNormals
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// Only URP ShaderLibrary functions are called (shadow bias, normal packing, rendering layers).
// Define ANGELTOON_ALPHA_CLIP before the include (transparent shader) or enable _ANGELTOON_ALPHA_CLIP (cutout)
// to clip by the base alpha.
// ============================================================================
#ifndef LIDA_ANGEL_TOON_DEPTH_PASSES_INCLUDED
#define LIDA_ANGEL_TOON_DEPTH_PASSES_INCLUDED

#include "LidaAngelToonInput.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Shadows.hlsl"

struct AngelToonDepthAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float2 uv         : TEXCOORD0;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct AngelToonDepthVaryings
{
    float4 positionCS : SV_POSITION;
    float3 normalWS   : TEXCOORD0;
    float2 uv         : TEXCOORD1;
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

void AngelToonAlphaClip(float2 uv)
{
#if defined(ANGELTOON_ALPHA_CLIP) || defined(_ANGELTOON_ALPHA_CLIP)
    clip(AngelToonSampleBase(uv).a - _Cutoff);
#endif
}

// ---------------------------------------------------------------- ShadowCaster
// URP sets these two for the light that is being rendered (names fixed by URP)
float3 _LightDirection;
float3 _LightPosition;

AngelToonDepthVaryings AngelToonShadowVertex(AngelToonDepthAttributes v)
{
    AngelToonDepthVaryings o = (AngelToonDepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    float3 positionWS = TransformObjectToWorld(v.positionOS.xyz);
    float3 normalWS = TransformObjectToWorldNormal(v.normalOS);
#if defined(_CASTING_PUNCTUAL_LIGHT_SHADOW)
    float3 toLight = normalize(_LightPosition - positionWS);
#else
    float3 toLight = _LightDirection;
#endif
    o.positionCS = ApplyShadowClamping(TransformWorldToHClip(ApplyShadowBias(positionWS, normalWS, toLight)));
    o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
    return o;
}

float4 AngelToonShadowFragment(AngelToonDepthVaryings i) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    AngelToonAlphaClip(i.uv);
    return 0;
}

// ---------------------------------------------------------------- DepthOnly / DepthNormals
AngelToonDepthVaryings AngelToonDepthVertex(AngelToonDepthAttributes v)
{
    AngelToonDepthVaryings o = (AngelToonDepthVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    o.positionCS = TransformObjectToHClip(v.positionOS.xyz);
    o.normalWS = TransformObjectToWorldNormal(v.normalOS);
    o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
    return o;
}

float AngelToonDepthFragment(AngelToonDepthVaryings i) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    AngelToonAlphaClip(i.uv);
    return i.positionCS.z;
}

float4 AngelToonPackDepthNormal(float3 normalWS)
{
    float3 n = AngelToonSafeNormalize(normalWS);
#if defined(_GBUFFER_NORMALS_OCT)
    float2 oct01 = saturate(PackNormalOctQuadEncode(n) * 0.5 + 0.5);
    return float4(PackFloat2To888(oct01), 0.0);
#else
    return float4(n, 0.0);
#endif
}

#if defined(_WRITE_RENDERING_LAYERS)
void AngelToonDepthNormalsFragment(AngelToonDepthVaryings i, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC,
                                   out float4 normalOut : SV_Target0, out uint layerOut : SV_Target1)
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    AngelToonAlphaClip(i.uv);
    float3 n = IS_FRONT_VFACE(facing, i.normalWS, -i.normalWS);
    normalOut = AngelToonPackDepthNormal(n);
    layerOut = EncodeMeshRenderingLayer();
}
#else
void AngelToonDepthNormalsFragment(AngelToonDepthVaryings i, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC,
                                   out float4 normalOut : SV_Target0)
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);
    AngelToonAlphaClip(i.uv);
    float3 n = IS_FRONT_VFACE(facing, i.normalWS, -i.normalWS);
    normalOut = AngelToonPackDepthNormal(n);
}
#endif

#endif // LIDA_ANGEL_TOON_DEPTH_PASSES_INCLUDED
