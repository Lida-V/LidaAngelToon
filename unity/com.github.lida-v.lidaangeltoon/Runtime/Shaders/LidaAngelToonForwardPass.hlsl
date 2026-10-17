// ============================================================================
// LidaAngelToonForwardPass.hlsl  -  LidaAngelToon for Unity URP: the body pass (LightMode UniversalForward)
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// The engine side of the spec: it prepares AngelToonInput (normal, key light, cast shadow, textures, mask)
// and calls AngelToonShade() of LidaAngelToonCore.hlsl. URP ShaderLibrary functions are only called,
// nothing is copied from other shaders.
// ============================================================================
#ifndef LIDA_ANGEL_TOON_FORWARD_PASS_INCLUDED
#define LIDA_ANGEL_TOON_FORWARD_PASS_INCLUDED

#include "LidaAngelToonInput.hlsl"
#include "Packages/com.unity.render-pipelines.universal/ShaderLibrary/Lighting.hlsl"

struct AngelToonAttributes
{
    float4 positionOS : POSITION;
    float3 normalOS   : NORMAL;
    float2 uv         : TEXCOORD0;
    float4 color      : COLOR;
    UNITY_VERTEX_INPUT_INSTANCE_ID
};

struct AngelToonVaryings
{
    float4 positionCS : SV_POSITION;
    float3 positionWS : TEXCOORD0;
    float3 normalWS   : TEXCOORD1;
    float2 uv         : TEXCOORD2;
    float4 color      : TEXCOORD3;
    float  fogFactor  : TEXCOORD4;
#if defined(_MAIN_LIGHT_SHADOWS_SCREEN) && !defined(_SURFACE_TYPE_TRANSPARENT)
    float4 shadowCoord : TEXCOORD5;
#endif
    UNITY_VERTEX_INPUT_INSTANCE_ID
    UNITY_VERTEX_OUTPUT_STEREO
};

AngelToonVaryings AngelToonForwardVertex(AngelToonAttributes v)
{
    AngelToonVaryings o = (AngelToonVaryings)0;
    UNITY_SETUP_INSTANCE_ID(v);
    UNITY_TRANSFER_INSTANCE_ID(v, o);
    UNITY_INITIALIZE_VERTEX_OUTPUT_STEREO(o);
    VertexPositionInputs vpi = GetVertexPositionInputs(v.positionOS.xyz);
    o.positionCS = vpi.positionCS;
    o.positionWS = vpi.positionWS;
    o.normalWS = TransformObjectToWorldNormal(v.normalOS);
    o.uv = TRANSFORM_TEX(v.uv, _BaseMap);
    o.color = v.color;
    o.fogFactor = ComputeFogFactor(vpi.positionCS.z);
#if defined(_MAIN_LIGHT_SHADOWS_SCREEN) && !defined(_SURFACE_TYPE_TRANSPARENT)
    o.shadowCoord = GetShadowCoord(vpi);
#endif
    return o;
}

// Per-pixel inputs of one layer (the material decides the normal override, used for the shadow probe as in Blender)
AngelToonInput AngelToonMakeInput(float3 N, float3 L, float3 V, float3 keyColor, float shadowAtten,
                                  float3 baseColor, float3 shadeTex, float4 mask, float3 mcAdd, float3 mcMul,
                                  AngelToonMaterial m)
{
    AngelToonInput i;
    i.N = N;
    i.L = L;
    i.V = V;
    i.KeyColor = keyColor;
    float3 Ns = AngelToonSafeNormalize(AngelToonMix3(N, m.NormalOverride, m.NormalOverrideMix));
    i.ShadowedNL = AngelToonShadowedNL(dot(Ns, AngelToonSafeNormalize(L)), shadowAtten, _ShadowGain);
    i.BaseColor = baseColor;
    i.ShadeTexture = shadeTex;
    i.Occlusion = mask.r;
    i.ReceiveShadowMask = (_ReceiveShadowUseMaskA > 0.5) ? mask.a : 1.0;
    i.MatCapAdd = mcAdd;
    i.MatCapMul = mcMul;
    i.MatCapAddMask = (_MatCapAddUseMaskA > 0.5) ? mask.a : 1.0;
    return i;
}

// Optional soft contribution of additional lights (off unless _AngelToonAddLightMix > 0).
float3 AngelToonAdditionalLights(float3 positionWS, float4 positionCS, float3 N, float3 baseColor, AngelToonMaterial m)
{
    float3 sum = 0.0;
#if defined(_ADDITIONAL_LIGHTS)
    UNITY_BRANCH if (_AngelToonAddLightMix > 0.0)
    {
        InputData inputData = (InputData)0;          // the URP light loop macros read inputData
        inputData.positionWS = positionWS;
        inputData.normalWS = N;
        inputData.normalizedScreenSpaceUV = GetNormalizedScreenSpaceUV(positionCS);
        half4 shadowMask = half4(1.0, 1.0, 1.0, 1.0);
        float lo = m.ShadeShift1 - m.ShadeSoft1;
        float hi = m.ShadeShift1 + m.ShadeSoft1;
    #if USE_CLUSTER_LIGHT_LOOP
        [loop] for (uint li = 0; li < min(URP_FP_DIRECTIONAL_LIGHTS_COUNT, MAX_VISIBLE_LIGHTS); li++)
        {
            Light dl = GetAdditionalLight(li, positionWS, shadowMask);
            float t = AngelToonSmoothstep(lo, hi, dot(N, dl.direction));
            sum += baseColor * dl.color * (dl.distanceAttenuation * dl.shadowAttenuation * t);
        }
    #endif
        uint lightCount = GetAdditionalLightsCount();
        LIGHT_LOOP_BEGIN(lightCount)
            Light al = GetAdditionalLight(lightIndex, positionWS, shadowMask);
            float t2 = AngelToonSmoothstep(lo, hi, dot(N, al.direction));
            sum += baseColor * al.color * (al.distanceAttenuation * al.shadowAttenuation * t2);
        LIGHT_LOOP_END
    }
#endif
    return sum * _AngelToonAddLightMix;
}

float4 AngelToonForwardFragment(AngelToonVaryings i, FRONT_FACE_TYPE facing : FRONT_FACE_SEMANTIC) : SV_Target
{
    UNITY_SETUP_INSTANCE_ID(i);
    UNITY_SETUP_STEREO_EYE_INDEX_POST_VERTEX(i);

    float4 base = AngelToonSampleBase(i.uv);
    float4 mask = AngelToonSampleMask(i.uv, i.color);
#if defined(_ANGELTOON_ALPHA_CLIP)
    // cutout: with alpha to coverage (MSAA) the soft edge comes from the coverage, otherwise clip at _Cutoff
    clip(base.a - ((_AlphaToMask > 0.5) ? (1.0 / 255.0) : _Cutoff));
#endif

#if defined(_ANGELTOON_MULTIPLY_LAYER)
    // multiply layer: dst.rgb *= mix(1, colour, alpha)   (blend DstColor Zero)
    return float4(AngelToonMix3(float3(1.0, 1.0, 1.0), _MultiplyColor.rgb, base.a), 1.0);
#else
    float3 positionWS = i.positionWS;
    // shading normal; back faces see the normal flipped toward the viewer (spec 6)
    float3 N = AngelToonSafeNormalize(i.normalWS);
    N = IS_FRONT_VFACE(facing, N, -N);

    // key light = URP main light (direction, colour, realtime shadow); the character override replaces direction / colour
#if defined(_MAIN_LIGHT_SHADOWS_SCREEN) && !defined(_SURFACE_TYPE_TRANSPARENT)
    float4 shadowCoord = i.shadowCoord;
#else
    float4 shadowCoord = TransformWorldToShadowCoord(positionWS);
#endif
    Light mainLight = GetMainLight(shadowCoord, positionWS, half4(1.0, 1.0, 1.0, 1.0));
    float3 L = mainLight.direction;
    float3 keyColor = mainLight.color * mainLight.distanceAttenuation;
    if (_AngelToonKeyOverride > 0.5)
    {
        L = AngelToonSafeNormalize(_AngelToonKeyDirWS.xyz);
        keyColor = _AngelToonKeyColor.rgb;
    }
    float shadowAtten = mainLight.shadowAttenuation;
    float3 V = GetWorldSpaceNormalizeViewDir(positionWS);

    // MatCap: right-handed view space (+Z toward the viewer), UV origin bottom-left (spec 6)
    float2 mcUV = AngelToonMatCapUV(mul((float3x3)UNITY_MATRIX_V, N));
    float3 mcAddTex = SAMPLE_TEXTURE2D_LOD(_MatCapAddMap, sampler_LinearClamp, mcUV, 0).rgb;
    float3 mcMulTex = SAMPLE_TEXTURE2D_LOD(_MatCapMulMap, sampler_LinearClamp, mcUV, 0).rgb;
    float3 shadeTex = SAMPLE_TEXTURE2D(_ShadeMap, sampler_BaseMap, i.uv).rgb * _ShadeMapColor.rgb;

    AngelToonMaterial mA;
    ANGELTOON_FILL_MATERIAL(mA, _)
    AngelToonInput inA = AngelToonMakeInput(N, L, V, keyColor, shadowAtten, base.rgb, shadeTex, mask,
                                            mcAddTex * _MatCapAddColor.rgb, mcMulTex * _MatCapMulColor.rgb, mA);
#if defined(_ANGELTOON_TWO_LAYER)
    // two-layer material: both parameter sets are shaded and the finished colours are mixed by mask G (spec 7)
    AngelToonMaterial mB;
    ANGELTOON_FILL_MATERIAL(mB, _L2_)
    AngelToonInput inB = AngelToonMakeInput(N, L, V, keyColor, shadowAtten, base.rgb, shadeTex, mask,
                                            mcAddTex * _L2_MatCapAddColor.rgb, mcMulTex * _L2_MatCapMulColor.rgb, mB);
    float3 col = AngelToonShadeTwoLayer(inA, mA, inB, mB, mask.g);
#else
    float3 col = AngelToonShade(inA, mA);
#endif

    // optional scene terms (0 by default: the Blender reference has no ambient and one light)
    col += base.rgb * max(SampleSH(N), 0.0) * _AngelToonAmbientMix;
    col += AngelToonAdditionalLights(positionWS, i.positionCS, N, base.rgb, mA);
    col = MixFog(col, i.fogFactor);

    UNITY_BRANCH if (_AngelToonDebugMode > 0.5)
    {
        int dm = (int)(_AngelToonDebugMode + 0.5);
        col = (dm == 1) ? base.rgb
            : (dm == 2) ? N * 0.5 + 0.5
            : (dm == 3) ? mask.rgb
            : (dm == 4) ? mask.aaa
            : (dm == 5) ? float3(shadowAtten, shadowAtten, shadowAtten)
            : float3(mcUV, 0.0);
    }
#if defined(_SURFACE_TYPE_TRANSPARENT) || defined(_ANGELTOON_ALPHA_CLIP)
    return float4(col, base.a);
#else
    return float4(col, 1.0);
#endif
#endif
}

#endif // LIDA_ANGEL_TOON_FORWARD_PASS_INCLUDED
