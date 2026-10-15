// ============================================================================
// AngelToonMaterialSync.cs  -  LidaAngelToon: keep keywords, passes, blend and queue in step with the properties
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
//
// Copyright (c) 2026 Lida
// ============================================================================
using UnityEditor;
using UnityEngine;
using UnityEngine.Rendering;

namespace LidaAngelToon.Editor
{
    public static class AngelToonMaterialSync
    {
        public const string ShaderOpaque = "LidaAngelToon/Toon";
        public const string ShaderTransparent = "LidaAngelToon/Toon Transparent";
        public const string OutlineLightMode = "SRPDefaultUnlit";

        public static bool IsAngelToon(Material m)
        {
            return m != null && m.shader != null && m.shader.name.StartsWith("LidaAngelToon/");
        }

        public static bool IsTransparent(Material m)
        {
            return m != null && m.shader != null && m.shader.name == ShaderTransparent;
        }

        static float F(Material m, string n, float fallback)
        {
            return m.HasProperty(n) ? m.GetFloat(n) : fallback;
        }

        static void Keyword(Material m, string k, bool on)
        {
            if (on) m.EnableKeyword(k); else m.DisableKeyword(k);
        }

        /// <summary>
        /// Keywords from the toggles, the outline pass on / off, the blend factors of the transparent shader
        /// and the render queue (2000, 2450 for cutout, or 3000 + _QueueOffset). Call after changing a material from a script.
        /// </summary>
        public static void Sync(Material m, bool setQueue = true, bool markDirty = true)
        {
            if (!IsAngelToon(m)) return;
            Keyword(m, "_ANGELTOON_TWO_LAYER", F(m, "_TwoLayer", 0f) > 0.5f);
            Keyword(m, "_ANGELTOON_MASK_VERTEX_COLOR", F(m, "_MaskFromVertexColor", 0f) > 0.5f);
            m.SetShaderPassEnabled(OutlineLightMode, F(m, "_OutlineEnabled", 1f) > 0.5f);
            int offset = Mathf.RoundToInt(F(m, "_QueueOffset", 0f));
            if (IsTransparent(m))
            {
                bool multiply = F(m, "_MultiplyLayer", 0f) > 0.5f;
                Keyword(m, "_ANGELTOON_MULTIPLY_LAYER", multiply);
                m.SetFloat("_SrcBlend", (float)(multiply ? BlendMode.DstColor : BlendMode.SrcAlpha));
                m.SetFloat("_DstBlend", (float)(multiply ? BlendMode.Zero : BlendMode.OneMinusSrcAlpha));
                if (setQueue) m.renderQueue = (int)RenderQueue.Transparent + offset;
                m.SetOverrideTag("RenderType", "Transparent");
            }
            else
            {
                bool cutout = F(m, "_AlphaClip", 0f) > 0.5f;
                Keyword(m, "_ANGELTOON_ALPHA_CLIP", cutout);
                if (setQueue) m.renderQueue = (int)(cutout ? RenderQueue.AlphaTest : RenderQueue.Geometry) + offset;
                m.SetOverrideTag("RenderType", cutout ? "TransparentCutout" : "Opaque");
            }
            if (markDirty) EditorUtility.SetDirty(m);
        }
    }

    /// <summary>The material inspector: the default property list, then Sync().</summary>
    public class AngelToonShaderGUI : ShaderGUI
    {
        public override void OnGUI(MaterialEditor materialEditor, MaterialProperty[] properties)
        {
            EditorGUILayout.HelpBox("LidaAngelToon: colours are linear in the shader (Linear colour space). " +
                                    "The mask texture must be imported with sRGB off.", MessageType.None);
            EditorGUI.BeginChangeCheck();
            base.OnGUI(materialEditor, properties);
            if (EditorGUI.EndChangeCheck())
                foreach (Object t in materialEditor.targets)
                    AngelToonMaterialSync.Sync(t as Material);
        }

        public override void AssignNewShaderToMaterial(Material material, Shader oldShader, Shader newShader)
        {
            base.AssignNewShaderToMaterial(material, oldShader, newShader);
            AngelToonMaterialSync.Sync(material);
        }

        public override void ValidateMaterial(Material material)
        {
            AngelToonMaterialSync.Sync(material, setQueue: false, markDirty: false);
        }
    }
}
