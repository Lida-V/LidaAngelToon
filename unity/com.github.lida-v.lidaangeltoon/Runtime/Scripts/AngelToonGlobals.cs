// ============================================================================
// AngelToonGlobals.cs  -  LidaAngelToon for Unity URP: scene-wide values read by the LidaAngelToon shaders
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
//
// Copyright (c) 2026 Lida
// ============================================================================
using UnityEngine;

namespace LidaAngelToon
{
    /// <summary>
    /// Sets the global shader values of LidaAngelToon. Without this component every value is 0:
    /// the URP main light is the key light, no ambient light, no additional lights (the Blender reference look).
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [AddComponentMenu("LidaAngelToon/AngelToon Globals")]
    public class AngelToonGlobals : MonoBehaviour
    {
        public enum DebugView { Off = 0, BaseColor = 1, Normal = 2, MaskRGB = 3, MaskA = 4, MainLightShadow = 5, MatCapUV = 6 }

        [Tooltip("Use the direction of this transform (its forward = the direction the light travels) and the colour below " +
                 "instead of the URP main light for LidaAngelToon materials. Cast shadows still come from the URP main light.")]
        public bool overrideKeyLight = false;
        [Tooltip("Optional: take the override direction from this transform instead of the component's own transform.")]
        public Transform keyLightTransform;
        public Color keyColor = Color.white;
        [Min(0f)] public float keyIntensity = 1f;

        [Tooltip("Share of the ambient probe (SH) added on top of the toon shading. 0 = like the Blender reference.")]
        [Range(0f, 1f)] public float ambientMix = 0f;
        [Tooltip("Share of the additional (point / spot) lights added on top. 0 = off.")]
        [Range(0f, 1f)] public float additionalLightMix = 0f;
        [Tooltip("Show one input of the shader instead of the result (for checking).")]
        public DebugView debugView = DebugView.Off;

        static readonly int IdKeyDir = Shader.PropertyToID("_AngelToonKeyDirWS");
        static readonly int IdKeyColor = Shader.PropertyToID("_AngelToonKeyColor");
        static readonly int IdKeyOverride = Shader.PropertyToID("_AngelToonKeyOverride");
        static readonly int IdAmbient = Shader.PropertyToID("_AngelToonAmbientMix");
        static readonly int IdAddLight = Shader.PropertyToID("_AngelToonAddLightMix");
        static readonly int IdDebug = Shader.PropertyToID("_AngelToonDebugMode");

        void OnEnable() { Apply(); }
        void OnValidate() { Apply(); }
        void Update() { Apply(); }
        void OnDisable() { ResetGlobals(); }

        public void Apply()
        {
            Transform t = keyLightTransform != null ? keyLightTransform : transform;
            Vector3 toLight = -t.forward;
            Color c = keyColor.linear * keyIntensity;
            SetGlobals(overrideKeyLight, toLight, c, ambientMix, additionalLightMix, (int)debugView);
        }

        /// <summary>Set every LidaAngelToon global value (colour = linear).</summary>
        public static void SetGlobals(bool overrideKey, Vector3 directionToLightWS, Color keyColorLinear,
                                      float ambient, float additionalLights, int debugMode)
        {
            Shader.SetGlobalFloat(IdKeyOverride, overrideKey ? 1f : 0f);
            Shader.SetGlobalVector(IdKeyDir, directionToLightWS.normalized);
            Shader.SetGlobalVector(IdKeyColor, new Vector4(keyColorLinear.r, keyColorLinear.g, keyColorLinear.b, 1f));
            Shader.SetGlobalFloat(IdAmbient, ambient);
            Shader.SetGlobalFloat(IdAddLight, additionalLights);
            Shader.SetGlobalFloat(IdDebug, debugMode);
        }

        /// <summary>Back to the defaults (URP main light, no ambient, no additional lights, no debug view).</summary>
        public static void ResetGlobals()
        {
            SetGlobals(false, Vector3.up, Color.white, 0f, 0f, 0);
        }
    }
}
