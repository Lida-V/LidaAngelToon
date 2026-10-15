// ============================================================================
// AngelToonPreset.cs  -  LidaAngelToon: create materials from a preset JSON ("LidaAngelToon.preset/1")
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.0
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// Preset format (all colours LINEAR; the tool converts them for Unity's Color properties):
// {
//   "format": "LidaAngelToon.preset/1",
//   "materials": [
//     { "name": "Cloth", "shader": "LidaAngelToon/Toon",
//       "floats": { "_ShadeShift1": 0.05 },
//       "colors_linear": { "_ShadeTint1": [0.7, 0.72, 0.89, 1] },
//       "vectors": { "_NormalOverride": [0, 0, 0, 0] },
//       "textures": { "_BaseMap": { "path": "Assets/.../Cloth.png", "srgb": true, "wrap": "repeat",
//                                   "mipmaps": true, "compression": "default" } },
//       "keywords": [], "disabled_passes": [], "render_queue": -1 }
//   ],
//   "assignments": [ { "object": "Body", "slot": 0, "material": "Cloth" } ]
// }
// "render_queue" -1 = from the shader / _QueueOffset. Texture import settings are applied when "apply_import" is true.
// ============================================================================
using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;

namespace LidaAngelToon.Editor
{
    public static class AngelToonPreset
    {
        public const string Format = "LidaAngelToon.preset/1";

        public class Result
        {
            public readonly Dictionary<string, Material> materials = new Dictionary<string, Material>();
            public readonly List<string> warnings = new List<string>();
            public int texturesImported;
        }

        public static Dictionary<string, object> Load(string presetPath)
        {
            var root = AngelToonJson.Parse(File.ReadAllText(presetPath)) as Dictionary<string, object>;
            if (root == null) throw new FormatException("preset: the top level must be an object");
            object f;
            if (!root.TryGetValue("format", out f) || (f as string) != Format)
                throw new FormatException("preset: format must be " + Format);
            return root;
        }

        static Dictionary<string, object> Obj(Dictionary<string, object> d, string key)
        {
            object v;
            return d.TryGetValue(key, out v) ? v as Dictionary<string, object> : null;
        }

        static List<object> Arr(Dictionary<string, object> d, string key)
        {
            object v;
            return d.TryGetValue(key, out v) ? v as List<object> : null;
        }

        static T Get<T>(Dictionary<string, object> d, string key, T fallback)
        {
            object v;
            if (d == null || !d.TryGetValue(key, out v) || v == null) return fallback;
            if (typeof(T) == typeof(float)) return (T)(object)Convert.ToSingle(v);
            if (typeof(T) == typeof(int)) return (T)(object)Convert.ToInt32(v);
            return v is T ? (T)v : fallback;
        }

        static Vector4 Vec(object v, float w = 1f)
        {
            var l = v as List<object>;
            float[] a = { 0f, 0f, 0f, w };
            for (int i = 0; i < Mathf.Min(4, l.Count); i++) a[i] = Convert.ToSingle(l[i]);
            return new Vector4(a[0], a[1], a[2], a[3]);
        }

        /// <summary>
        /// Set a Color property from a LINEAR colour. In a Linear colour space project Unity converts plain Color
        /// properties from gamma to linear on upload, but passes [HDR] Color properties unchanged, so plain ones are
        /// stored as .gamma and HDR ones as they are.
        /// </summary>
        public static void SetColorLinear(Material m, string property, Vector4 linear)
        {
            var c = new Color(linear.x, linear.y, linear.z, linear.w);
            int idx = m.shader.FindPropertyIndex(property);
            bool hdr = idx >= 0 && (m.shader.GetPropertyFlags(idx) & UnityEngine.Rendering.ShaderPropertyFlags.HDR) != 0;
            bool linearSpace = QualitySettings.activeColorSpace == ColorSpace.Linear;
            m.SetColor(property, (hdr || !linearSpace) ? c : c.gamma);
        }

        /// <summary>Texture import settings from the preset (sRGB, wrap, mipmaps, compression).</summary>
        public static Texture2D ImportTexture(Dictionary<string, object> t, Result res)
        {
            string path = Get<string>(t, "path", null);
            var importer = AssetImporter.GetAtPath(path) as TextureImporter;
            if (importer == null)
            {
                res.warnings.Add("texture not found: " + path);
                return null;
            }
            bool changed = false;
            bool srgb = Get(t, "srgb", true);
            if (importer.sRGBTexture != srgb) { importer.sRGBTexture = srgb; changed = true; }
            string wrap = Get<string>(t, "wrap", "repeat");
            var wm = wrap == "clamp" ? TextureWrapMode.Clamp : TextureWrapMode.Repeat;
            if (importer.wrapMode != wm) { importer.wrapMode = wm; changed = true; }
            bool mips = Get(t, "mipmaps", true);
            if (importer.mipmapEnabled != mips) { importer.mipmapEnabled = mips; changed = true; }
            string comp = Get<string>(t, "compression", "default");
            var tc = comp == "none" ? TextureImporterCompression.Uncompressed : TextureImporterCompression.Compressed;
            if (importer.textureCompression != tc) { importer.textureCompression = tc; changed = true; }
            int aniso = Get(t, "aniso", -1);
            if (aniso >= 0 && importer.anisoLevel != aniso) { importer.anisoLevel = aniso; changed = true; }
            if (importer.filterMode != FilterMode.Trilinear && mips) { importer.filterMode = FilterMode.Trilinear; changed = true; }
            if (importer.textureType != TextureImporterType.Default) { importer.textureType = TextureImporterType.Default; changed = true; }
            if (changed)
            {
                importer.SaveAndReimport();
                res.texturesImported++;
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        /// <summary>
        /// Create (or update) one material asset per preset entry in outputFolder ("Assets/...").
        /// </summary>
        public static Result CreateMaterials(Dictionary<string, object> preset, string outputFolder, bool applyTextureImport = true)
        {
            var res = new Result();
            if (!AssetDatabase.IsValidFolder(outputFolder))
            {
                string parent = Path.GetDirectoryName(outputFolder).Replace('\\', '/');
                AssetDatabase.CreateFolder(parent, Path.GetFileName(outputFolder));
            }
            foreach (object o in Arr(preset, "materials") ?? new List<object>())
            {
                var e = o as Dictionary<string, object>;
                string name = Get<string>(e, "name", null);
                string shaderName = Get<string>(e, "shader", AngelToonMaterialSync.ShaderOpaque);
                Shader sh = Shader.Find(shaderName);
                if (sh == null) { res.warnings.Add("shader not found: " + shaderName); continue; }
                string path = outputFolder + "/" + SafeName(name) + ".mat";
                Material m = AssetDatabase.LoadAssetAtPath<Material>(path);
                bool isNew = m == null;
                if (isNew) m = new Material(sh) { name = SafeName(name) };
                else m.shader = sh;
                var floats = Obj(e, "floats");
                if (floats != null)
                    foreach (var kv in floats)
                        if (m.HasProperty(kv.Key)) m.SetFloat(kv.Key, Convert.ToSingle(kv.Value));
                        else res.warnings.Add(name + ": no float " + kv.Key);
                var cols = Obj(e, "colors_linear");
                if (cols != null)
                    foreach (var kv in cols)
                        if (m.HasProperty(kv.Key)) SetColorLinear(m, kv.Key, Vec(kv.Value));
                        else res.warnings.Add(name + ": no colour " + kv.Key);
                var vecs = Obj(e, "vectors");
                if (vecs != null)
                    foreach (var kv in vecs)
                        if (m.HasProperty(kv.Key)) m.SetVector(kv.Key, Vec(kv.Value, 0f));
                        else res.warnings.Add(name + ": no vector " + kv.Key);
                var texs = Obj(e, "textures");
                if (texs != null)
                    foreach (var kv in texs)
                    {
                        var td = kv.Value as Dictionary<string, object>;
                        Texture2D tex = applyTextureImport ? ImportTexture(td, res)
                                                           : AssetDatabase.LoadAssetAtPath<Texture2D>(Get<string>(td, "path", ""));
                        if (tex == null) { res.warnings.Add(name + ": texture missing for " + kv.Key); continue; }
                        if (m.HasProperty(kv.Key)) m.SetTexture(kv.Key, tex);
                        else res.warnings.Add(name + ": no texture slot " + kv.Key);
                    }
                AngelToonMaterialSync.Sync(m, setQueue: true, markDirty: false);
                foreach (object k in Arr(e, "keywords") ?? new List<object>()) m.EnableKeyword((string)k);
                foreach (object pn in Arr(e, "disabled_passes") ?? new List<object>()) m.SetShaderPassEnabled((string)pn, false);
                int rq = Get(e, "render_queue", -1);
                if (rq >= 0) m.renderQueue = rq;
                if (isNew) AssetDatabase.CreateAsset(m, path);
                else EditorUtility.SetDirty(m);
                res.materials[name] = m;
            }
            AssetDatabase.SaveAssets();
            return res;
        }

        /// <summary>Put the preset materials on the renderers below root (by object name and slot).</summary>
        public static int Assign(Dictionary<string, object> preset, GameObject root, Dictionary<string, Material> materials, List<string> warnings)
        {
            int n = 0;
            var renderers = new Dictionary<string, Renderer>(StringComparer.Ordinal);
            foreach (Renderer rr in root.GetComponentsInChildren<Renderer>(true))
                if (!renderers.ContainsKey(rr.gameObject.name)) renderers[rr.gameObject.name] = rr;
                else warnings.Add("two renderers named " + rr.gameObject.name + " (the first one is used)");
            foreach (object o in Arr(preset, "assignments") ?? new List<object>())
            {
                var a = o as Dictionary<string, object>;
                string on = Get<string>(a, "object", null);
                int slot = Get(a, "slot", 0);
                string mn = Get<string>(a, "material", null);
                Renderer r;
                Material m;
                if (!renderers.TryGetValue(on, out r)) { warnings.Add("object not found: " + on); continue; }
                if (!materials.TryGetValue(mn, out m)) { warnings.Add("material not in preset: " + mn); continue; }
                var mats = r.sharedMaterials;
                if (slot < 0 || slot >= mats.Length) { warnings.Add(on + ": no slot " + slot); continue; }
                mats[slot] = m;
                r.sharedMaterials = mats;
                n++;
            }
            return n;
        }

        static string SafeName(string s)
        {
            foreach (char c in Path.GetInvalidFileNameChars()) s = s.Replace(c, '_');
            return s;
        }

        [MenuItem("Tools/LidaAngelToon/Create Materials From Preset...")]
        static void MenuCreate()
        {
            string p = EditorUtility.OpenFilePanel("LidaAngelToon preset", Application.dataPath, "json");
            if (string.IsNullOrEmpty(p)) return;
            string folder = EditorUtility.SaveFolderPanel("Output folder (inside Assets)", Application.dataPath, "LidaAngelToonMaterials");
            if (string.IsNullOrEmpty(folder)) return;
            folder = folder.Replace('\\', '/');
            string data = Application.dataPath.Replace('\\', '/');
            if (!folder.StartsWith(data)) { Debug.LogError("LidaAngelToon: the output folder must be inside Assets"); return; }
            folder = "Assets" + folder.Substring(data.Length);
            var preset = Load(p);
            var res = CreateMaterials(preset, folder);
            if (Selection.activeGameObject != null && Arr(preset, "assignments") != null)
                Assign(preset, Selection.activeGameObject, res.materials, res.warnings);
            foreach (string w in res.warnings) Debug.LogWarning("LidaAngelToon preset: " + w);
            Debug.Log("LidaAngelToon preset: " + res.materials.Count + " materials in " + folder);
        }
    }
}
