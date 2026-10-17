// ============================================================================
// AngelToonOutlineNormals.cs  -  LidaAngelToon: smoothed outline normals stored in UV3 (tangent space)
//
// SPDX-License-Identifier: LicenseRef-Lida-Attribution-1.1
//
// Copyright (c) 2026 Lida
// ============================================================================
//
// A mesh is split where UVs or normals differ, so pushing the outline hull along the vertex normals opens
// gaps at those seams. The smoothed normal is the corner-angle weighted average of the face normals of all
// vertices at the same position (like the vertex normals of a welded mesh in Blender). It is stored in UV3
// relative to the vertex frame (tangent, bitangent, normal), so it follows skinning and blend shapes; the
// shader rebuilds it with _OutlineNormalSource = 1.
// Import hook: models whose importer userData contains "LidaAngelToon.OutlineNormals" get it on import
// (menu Assets > LidaAngelToon > Outline Normals On Import).
// ============================================================================
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace LidaAngelToon.Editor
{
    public static class AngelToonOutlineNormals
    {
        public const int UVChannel = 3;
        public const string ImportTag = "LidaAngelToon.OutlineNormals";

        /// <summary>Corner-angle weighted face normals summed over all vertices that share a position (object space).</summary>
        public static Vector3[] ComputeSmoothNormals(Mesh mesh, float weldDistance = 1e-6f)
        {
            Vector3[] p = mesh.vertices;
            Vector3[] vn = mesh.normals;
            int n = p.Length;
            var group = new int[n];
            var keyToGroup = new Dictionary<Vector3Int, int>();
            float inv = 1f / Mathf.Max(weldDistance, 1e-9f);
            int groups = 0;
            for (int i = 0; i < n; i++)
            {
                var k = new Vector3Int(Mathf.RoundToInt(p[i].x * inv), Mathf.RoundToInt(p[i].y * inv), Mathf.RoundToInt(p[i].z * inv));
                int g;
                if (!keyToGroup.TryGetValue(k, out g)) { g = groups++; keyToGroup[k] = g; }
                group[i] = g;
            }
            var sum = new Vector3[groups];
            var refN = new Vector3[groups];
            for (int i = 0; i < n; i++) if (vn != null && vn.Length == n) refN[group[i]] += vn[i];
            for (int s = 0; s < mesh.subMeshCount; s++)
            {
                if (mesh.GetTopology(s) != MeshTopology.Triangles) continue;
                int[] t = mesh.GetTriangles(s);
                for (int i = 0; i + 2 < t.Length; i += 3)
                {
                    int a = t[i], b = t[i + 1], c = t[i + 2];
                    Vector3 fn = Vector3.Cross(p[b] - p[a], p[c] - p[a]);
                    if (fn.sqrMagnitude < 1e-30f) continue;
                    fn.Normalize();
                    sum[group[a]] += fn * Angle(p[b] - p[a], p[c] - p[a]);
                    sum[group[b]] += fn * Angle(p[c] - p[b], p[a] - p[b]);
                    sum[group[c]] += fn * Angle(p[a] - p[c], p[b] - p[c]);
                }
            }
            var outN = new Vector3[n];
            for (int g = 0; g < groups; g++)
            {
                // keep the side of the imported normals (the winding convention does not matter)
                if (Vector3.Dot(sum[g], refN[g]) < 0f) sum[g] = -sum[g];
                sum[g] = sum[g].sqrMagnitude > 1e-30f ? sum[g].normalized : refN[g].normalized;
            }
            for (int i = 0; i < n; i++) outN[i] = sum[group[i]];
            return outN;
        }

        static float Angle(Vector3 u, Vector3 v)
        {
            float d = u.magnitude * v.magnitude;
            if (d < 1e-30f) return 0f;
            return Mathf.Acos(Mathf.Clamp(Vector3.Dot(u, v) / d, -1f, 1f));
        }

        /// <summary>Store object-space normals in UV3 relative to (tangent, bitangent, normal). Creates tangents if missing.</summary>
        public static void WriteTangentSpace(Mesh mesh, Vector3[] smoothOS)
        {
            if (mesh.tangents == null || mesh.tangents.Length != mesh.vertexCount) mesh.RecalculateTangents();
            Vector3[] nrm = mesh.normals;
            Vector4[] tan = mesh.tangents;
            var uv = new List<Vector3>(mesh.vertexCount);
            for (int i = 0; i < mesh.vertexCount; i++)
            {
                Vector3 nn = nrm[i];
                Vector3 t = new Vector3(tan[i].x, tan[i].y, tan[i].z);
                Vector3 b = Vector3.Cross(nn, t) * (tan[i].w >= 0f ? 1f : -1f);
                Vector3 s = smoothOS[i];
                uv.Add(new Vector3(Vector3.Dot(s, t), Vector3.Dot(s, b), Vector3.Dot(s, nn)));
            }
            mesh.SetUVs(UVChannel, uv);
        }

        /// <summary>Compute and store the smoothed outline normals of one mesh.</summary>
        public static void Bake(Mesh mesh)
        {
            WriteTangentSpace(mesh, ComputeSmoothNormals(mesh));
        }

        [MenuItem("Assets/LidaAngelToon/Outline Normals On Import (toggle)")]
        static void MenuToggle()
        {
            foreach (Object o in Selection.objects)
            {
                string path = AssetDatabase.GetAssetPath(o);
                var mi = AssetImporter.GetAtPath(path) as ModelImporter;
                if (mi == null) continue;
                string ud = mi.userData ?? "";
                mi.userData = ud.Contains(ImportTag) ? ud.Replace(ImportTag, "").Trim() : (ud + " " + ImportTag).Trim();
                mi.SaveAndReimport();
                Debug.Log("LidaAngelToon: outline normals on import " + (mi.userData.Contains(ImportTag) ? "ON" : "OFF") + " for " + path);
            }
        }
    }

    class AngelToonOutlineNormalsPostprocessor : AssetPostprocessor
    {
        void OnPostprocessModel(GameObject root)
        {
            var mi = assetImporter as ModelImporter;
            if (mi == null || mi.userData == null || !mi.userData.Contains(AngelToonOutlineNormals.ImportTag)) return;
            var done = new HashSet<Mesh>();
            foreach (var mf in root.GetComponentsInChildren<MeshFilter>(true))
                if (mf.sharedMesh != null && done.Add(mf.sharedMesh)) AngelToonOutlineNormals.Bake(mf.sharedMesh);
            foreach (var sr in root.GetComponentsInChildren<SkinnedMeshRenderer>(true))
                if (sr.sharedMesh != null && done.Add(sr.sharedMesh)) AngelToonOutlineNormals.Bake(sr.sharedMesh);
        }
    }
}
