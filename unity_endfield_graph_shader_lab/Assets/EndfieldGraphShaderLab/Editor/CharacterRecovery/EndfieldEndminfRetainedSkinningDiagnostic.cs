using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Read-only retained-frame probe for Endminf hair/cape skinning. The
    /// beauty capture invokes this only after its synchronized render, so the
    /// CPU BakeMesh readback cannot become part of the submitted beauty path.
    /// </summary>
    public static class EndfieldEndminfRetainedSkinningDiagnostic
    {
        [Serializable]
        public sealed class RendererRow
        {
            public string path;
            public string status;
            public string failure;
            public bool enabled;
            public bool activeInHierarchy;
            public bool visibleAfterBeautyRender;
            public string sharedMesh;
            public int sourceVertexCount;
            public int bakedVertexCount;
            public int boneCount;
            public int bindposeCount;
            public string rootBonePath;
            public Vector3 bakedLocalBoundsCenter;
            public Vector3 bakedLocalBoundsExtents;
            public Vector3 bakedWorldBoundsCenter;
            public Vector3 bakedWorldBoundsExtents;
            public string bakedLocalVertexChecksumFnv1a64;
            public string bakedWorldVertexChecksumFnv1a64;
            public int[] sampledVertexIndices;
            public Vector3[] sampledWorldPositions;
            public string boneLocalToWorldChecksumFnv1a64;
            public string bindposeChecksumFnv1a64;
            public string rendererLocalPaletteChecksumFnv1a64;
            public string worldPaletteChecksumFnv1a64;
            public BoneRow[] bones;
        }

        [Serializable]
        public sealed class BoneRow
        {
            public int index;
            public string path;
            public bool present;
            public bool activeInHierarchy;
            public MatrixRows boneLocalToWorld;
            public MatrixRows bindpose;
            public MatrixRows rendererLocalPalette;
            public MatrixRows worldPalette;
        }

        [Serializable]
        public sealed class MatrixRows
        {
            public Vector4 row0;
            public Vector4 row1;
            public Vector4 row2;
            public Vector4 row3;
        }

        public static RendererRow[] Capture(Transform actorRoot)
        {
            if (actorRoot == null)
                throw new ArgumentNullException(nameof(actorRoot));

            return actorRoot.GetComponentsInChildren<SkinnedMeshRenderer>(true)
                .Where(IsActiveHairOrCloth)
                .OrderBy(value => RelativePath(actorRoot, value.transform),
                    StringComparer.Ordinal)
                .Select(value => CaptureRenderer(actorRoot, value))
                .ToArray();
        }

        private static bool IsActiveHairOrCloth(SkinnedMeshRenderer renderer)
        {
            if (renderer == null || !renderer.enabled ||
                !renderer.gameObject.activeInHierarchy || !renderer.isVisible)
                return false;
            string name = renderer.name ?? string.Empty;
            return name.IndexOf("_hair_", StringComparison.OrdinalIgnoreCase) >= 0 ||
                name.IndexOf("_cloth_", StringComparison.OrdinalIgnoreCase) >= 0;
        }

        private static RendererRow CaptureRenderer(
            Transform actorRoot,
            SkinnedMeshRenderer renderer)
        {
            Mesh source = renderer.sharedMesh;
            var row = new RendererRow {
                path = RelativePath(actorRoot, renderer.transform),
                status = "failed",
                failure = string.Empty,
                enabled = renderer.enabled,
                activeInHierarchy = renderer.gameObject.activeInHierarchy,
                visibleAfterBeautyRender = renderer.isVisible,
                sharedMesh = source == null ? string.Empty : source.name,
                sourceVertexCount = source == null ? 0 : source.vertexCount,
                boneCount = renderer.bones == null ? 0 : renderer.bones.Length,
                bindposeCount = source == null ? 0 : source.bindposes.Length,
                rootBonePath = RelativePath(actorRoot, renderer.rootBone),
                sampledVertexIndices = Array.Empty<int>(),
                sampledWorldPositions = Array.Empty<Vector3>(),
                bones = Array.Empty<BoneRow>()
            };
            if (source == null)
            {
                row.failure = "shared mesh is missing";
                return row;
            }

            Mesh baked = new Mesh { name = renderer.name + " Retained Diagnostic" };
            try
            {
                // false keeps vertices in renderer-local space. The explicit
                // localToWorld multiplication below makes the world checksum
                // and samples independent of BakeMesh's useScale overload.
                renderer.BakeMesh(baked, false);
                Vector3[] vertices = baked.vertices;
                row.bakedVertexCount = vertices.Length;
                row.bakedLocalBoundsCenter = baked.bounds.center;
                row.bakedLocalBoundsExtents = baked.bounds.extents;

                Matrix4x4 rendererToWorld = renderer.localToWorldMatrix;
                Vector3[] worldVertices = new Vector3[vertices.Length];
                for (int index = 0; index < vertices.Length; index++)
                    worldVertices[index] = rendererToWorld.MultiplyPoint3x4(vertices[index]);
                Bounds worldBounds = BoundsOf(worldVertices);
                row.bakedWorldBoundsCenter = worldBounds.center;
                row.bakedWorldBoundsExtents = worldBounds.extents;
                row.bakedLocalVertexChecksumFnv1a64 = Checksum(vertices);
                row.bakedWorldVertexChecksumFnv1a64 = Checksum(worldVertices);
                row.sampledVertexIndices = SampleIndices(vertices.Length);
                row.sampledWorldPositions = row.sampledVertexIndices
                    .Select(index => worldVertices[index]).ToArray();

                Transform[] bones = renderer.bones ?? Array.Empty<Transform>();
                Matrix4x4[] bindposes = source.bindposes ?? Array.Empty<Matrix4x4>();
                int paletteCount = Math.Min(bones.Length, bindposes.Length);
                var boneRows = new List<BoneRow>(paletteCount);
                var boneMatrices = new List<Matrix4x4>(paletteCount);
                var retainedBindposes = new List<Matrix4x4>(paletteCount);
                var rendererLocalPalette = new List<Matrix4x4>(paletteCount);
                var worldPalette = new List<Matrix4x4>(paletteCount);
                Matrix4x4 worldToRenderer = renderer.worldToLocalMatrix;
                for (int index = 0; index < paletteCount; index++)
                {
                    Transform bone = bones[index];
                    Matrix4x4 boneToWorld = bone == null
                        ? Matrix4x4.zero
                        : bone.localToWorldMatrix;
                    Matrix4x4 bindpose = bindposes[index];
                    Matrix4x4 worldSkin = boneToWorld * bindpose;
                    Matrix4x4 localSkin = worldToRenderer * worldSkin;
                    boneMatrices.Add(boneToWorld);
                    retainedBindposes.Add(bindpose);
                    rendererLocalPalette.Add(localSkin);
                    worldPalette.Add(worldSkin);
                    boneRows.Add(new BoneRow {
                        index = index,
                        path = RelativePath(actorRoot, bone),
                        present = bone != null,
                        activeInHierarchy = bone != null && bone.gameObject.activeInHierarchy,
                        boneLocalToWorld = Rows(boneToWorld),
                        bindpose = Rows(bindpose),
                        rendererLocalPalette = Rows(localSkin),
                        worldPalette = Rows(worldSkin)
                    });
                }
                row.bones = boneRows.ToArray();
                row.boneLocalToWorldChecksumFnv1a64 = Checksum(boneMatrices);
                row.bindposeChecksumFnv1a64 = Checksum(retainedBindposes);
                row.rendererLocalPaletteChecksumFnv1a64 =
                    Checksum(rendererLocalPalette);
                row.worldPaletteChecksumFnv1a64 = Checksum(worldPalette);

                if (vertices.Length != source.vertexCount)
                    row.failure = "BakeMesh vertex count does not match shared mesh";
                else if (bones.Length != bindposes.Length)
                    row.failure = "renderer bone count does not match mesh bindpose count";
                else if (bones.Any(value => value == null))
                    row.failure = "renderer palette contains a missing bone";
                else
                    row.status = "ok";
            }
            catch (Exception exception)
            {
                row.failure = exception.GetType().Name + ": " + exception.Message;
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(baked);
            }
            return row;
        }

        private static int[] SampleIndices(int count)
        {
            if (count <= 0)
                return Array.Empty<int>();
            return new[] { 0, count / 4, count / 2, (count * 3) / 4, count - 1 }
                .Distinct()
                .ToArray();
        }

        private static Bounds BoundsOf(Vector3[] vertices)
        {
            if (vertices == null || vertices.Length == 0)
                return new Bounds(Vector3.zero, Vector3.zero);
            Bounds bounds = new Bounds(vertices[0], Vector3.zero);
            for (int index = 1; index < vertices.Length; index++)
                bounds.Encapsulate(vertices[index]);
            return bounds;
        }

        private static MatrixRows Rows(Matrix4x4 value)
        {
            return new MatrixRows {
                row0 = value.GetRow(0),
                row1 = value.GetRow(1),
                row2 = value.GetRow(2),
                row3 = value.GetRow(3)
            };
        }

        private static string Checksum(IEnumerable<Vector3> values)
        {
            ulong hash = FnvOffset;
            foreach (Vector3 value in values)
            {
                HashFloat(ref hash, value.x);
                HashFloat(ref hash, value.y);
                HashFloat(ref hash, value.z);
            }
            return hash.ToString("x16");
        }

        private static string Checksum(IEnumerable<Matrix4x4> values)
        {
            ulong hash = FnvOffset;
            foreach (Matrix4x4 value in values)
            {
                for (int row = 0; row < 4; row++)
                for (int column = 0; column < 4; column++)
                    HashFloat(ref hash, value[row, column]);
            }
            return hash.ToString("x16");
        }

        private const ulong FnvOffset = 14695981039346656037UL;
        private const ulong FnvPrime = 1099511628211UL;

        private static void HashFloat(ref ulong hash, float value)
        {
            uint bits = unchecked((uint)BitConverter.SingleToInt32Bits(value));
            for (int shift = 0; shift < 32; shift += 8)
            {
                hash ^= (byte)(bits >> shift);
                hash *= FnvPrime;
            }
        }

        private static string RelativePath(Transform root, Transform value)
        {
            if (value == null)
                return "<missing>";
            if (value == root)
                return ".";
            var names = new Stack<string>();
            Transform current = value;
            while (current != null && current != root)
            {
                names.Push(current.name);
                current = current.parent;
            }
            return current == root
                ? string.Join("/", names.ToArray())
                : "<outside-actor>/" + value.name;
        }
    }
}
