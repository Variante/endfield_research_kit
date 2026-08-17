// Managed public-input census for the Li Zhiyan M23 mesh-particle draw.
//
// This file intentionally stops at Unity's public ParticleSystem/Mesh API.
// It records the values which a future 136-byte input-stream bridge must
// consume, but never serializes a guessed packed row and never grants exact
// DXBC or visual admission.  The separate sidecar is useful even when the
// native renderer-packing path is unavailable.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldLiZhiyanM23ManagedParticlePacketCensus
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Effects/OverviewPeakParticles/" +
            "P_fxui_lizhiyan_overview_start_04_2.prefab";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-peak-particle-effects.v1";
        private const string ExpectedRoot = "P_fxui_lizhiyan_overview_start_04_2";
        private const int RetailPts = 40000;
        private const int RetailClockOriginPts = 37967;
        private const int RetailClockUnitsPerSecond = 1000;
        private const float ExpectedEffectDelay = 1.833333f;
        private const int ExpectedPacketStrideBytes = 136;
        private const string OutputRelativePath =
            "scratch/character_recovery/lizhiyan_m23_packet_census/pts_40000.json";
        private static readonly int[] ExpectedStreams = { 0, 1, 3, 4, 5, 34 };
        private static readonly string[] ExpectedStreamNames =
        {
            "Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW",
        };

        [Serializable]
        private sealed class Float3Record
        {
            public float x;
            public float y;
            public float z;

            public static Float3Record From(Vector3 value)
            {
                return new Float3Record { x = value.x, y = value.y, z = value.z };
            }
        }

        [Serializable]
        private sealed class Float4Record
        {
            public float x;
            public float y;
            public float z;
            public float w;

            public static Float4Record From(Vector4 value)
            {
                return new Float4Record
                {
                    x = value.x, y = value.y, z = value.z, w = value.w,
                };
            }

            public static Float4Record From(Quaternion value)
            {
                return new Float4Record
                {
                    x = value.x, y = value.y, z = value.z, w = value.w,
                };
            }
        }

        [Serializable]
        private sealed class ColorRecord
        {
            public byte r;
            public byte g;
            public byte b;
            public byte a;

            public static ColorRecord From(Color32 value)
            {
                return new ColorRecord { r = value.r, g = value.g, b = value.b, a = value.a };
            }

            public static ColorRecord From(Color value)
            {
                return From((Color32)value);
            }
        }

        [Serializable]
        private sealed class BoneWeightRecord
        {
            public float weight0;
            public float weight1;
            public float weight2;
            public float weight3;
            public int boneIndex0;
            public int boneIndex1;
            public int boneIndex2;
            public int boneIndex3;

            public static BoneWeightRecord From(BoneWeight value)
            {
                return new BoneWeightRecord
                {
                    weight0 = value.weight0, weight1 = value.weight1,
                    weight2 = value.weight2, weight3 = value.weight3,
                    boneIndex0 = value.boneIndex0, boneIndex1 = value.boneIndex1,
                    boneIndex2 = value.boneIndex2, boneIndex3 = value.boneIndex3,
                };
            }
        }

        [Serializable]
        private sealed class MatrixRecord
        {
            // Unity's Matrix4x4.ToString is locale-dependent.  Keep the
            // binary32 column-major values explicit for later packet work.
            public float[] columnMajor;

            public static MatrixRecord From(Matrix4x4 value)
            {
                var result = new float[16];
                for (int column = 0; column < 4; ++column)
                    for (int row = 0; row < 4; ++row)
                        result[column * 4 + row] = value[row, column];
                return new MatrixRecord { columnMajor = result };
            }
        }

        [Serializable]
        private sealed class SubmeshRecord
        {
            public int submesh;
            public int[] indices;
        }

        [Serializable]
        private sealed class ChannelRecord
        {
            public string semantic;
            public bool present;
            public int count;
            public string provenance;
            public string note;
        }

        [Serializable]
        private sealed class SourceMeshRecord
        {
            public string name;
            public long meshPathId;
            public int vertexCount;
            public int subMeshCount;
            public int[] subMeshIndexCounts;
            public SubmeshRecord[] subMeshes;
            public Float3Record[] positions;
            public Float3Record[] normals;
            public Float4Record[] tangents;
            public ColorRecord[] colors;
            public Float4Record[] uv0;
            public Float4Record[] uv1;
            public Float4Record[] uv2;
            public Float4Record[] uv3;
            public Float4Record[] uv4;
            public Float4Record[] uv5;
            public Float4Record[] uv6;
            public Float4Record[] uv7;
            public BoneWeightRecord[] boneWeights;
            public MatrixRecord[] bindPoses;
            public ChannelRecord[] channels;
        }

        [Serializable]
        private sealed class ParticleRecord
        {
            public int particleIndex;
            public int meshIndex;
            public uint randomSeed;
            public Float3Record position;
            public Float3Record velocity;
            public Float3Record animatedVelocity;
            public Float3Record axisOfRotation;
            public float rotation;
            public Float3Record rotation3D;
            public float angularVelocity;
            public Float3Record angularVelocity3D;
            public float startSize;
            public Float3Record startSize3D;
            public ColorRecord startColor;
            public ColorRecord currentColor;
            public float remainingLifetime;
            public float startLifetime;
            public Float4Record custom1;
            public Float3Record currentSize3D;
            public QuaternionRecord rotationQuaternion;
            public MatrixRecord particleLocalMatrix;
            public MatrixRecord particleWorldMatrix;
            public MatrixRecord particleNormalMatrix;
            public string publicInputProvenance;
            public PacketVertexRecord[] vertices;
        }

        [Serializable]
        private sealed class QuaternionRecord
        {
            public float x;
            public float y;
            public float z;
            public float w;

            public static QuaternionRecord From(Quaternion value)
            {
                return new QuaternionRecord { x = value.x, y = value.y, z = value.z, w = value.w };
            }
        }

        [Serializable]
        private sealed class PacketVertexRecord
        {
            public int sourceVertexIndex;
            public Float3Record sourcePosition;
            public Float3Record sourceNormal;
            public Float4Record sourceTangent;
            public ColorRecord sourceColor;
            public Float4Record sourceUv0;
            public Float4Record sourceUv1;
            public Float4Record sourceUv4;
            public BoneWeightRecord sourceBoneWeight;
            public Float3Record candidatePosition;
            public Float3Record candidateNormal;
            public Float4Record candidateTangent;
            public ColorRecord publicCurrentColorNotPackedColor;
            public Float4Record candidateTexcoord4;
            public string candidateContract;
        }

        [Serializable]
        private sealed class PacketFieldContract
        {
            public string semantic;
            public int offsetBytes;
            public int componentCount;
            public string provenance;
            public string source;
            public string note;
        }

        [Serializable]
        private sealed class RendererRecord
        {
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public long materialPathId;
            public long[] meshPathIds;
            public string materialName;
            public string materialShaderName;
            public bool sourceRendererEnabled;
            public string renderMode;
            public string alignment;
            public string sortMode;
            public float velocityScale;
            public float cameraVelocityScale;
            public bool enableGPUInstancing;
            public string[] activeVertexStreams;
            public int[] activeVertexStreamIds;
            public float[] sourceMeshWeights;
            public MatrixRecord systemLocalToWorld;
            public int particleCount;
            public int totalSourceVertices;
            public int totalSourceIndices;
            public bool publicParticleInputsClosed;
            public bool sourceMeshInputsClosed;
            public bool candidateRowsBuilt;
            public bool exactPackedRowsAvailable;
            public bool drawTimeCb3Available;
            public SourceMeshRecord[] sourceMeshes;
            public ParticleRecord[] particles;
            public string[] unresolvedInputs;
        }

        [Serializable]
        private sealed class CensusReport
        {
            public string schema;
            public string status;
            public string failure;
            public string unityVersion;
            public string graphicsDeviceType;
            public string prefab;
            public string effectRoot;
            public int retailPts;
            public int retailClockOriginPts;
            public float localSeconds;
            public float effectLocalSeconds;
            public float sourceEffectDelay;
            public int packetStrideBytes;
            public string packetAbiProvenance;
            public bool sourceRendererSubmissionPath;
            public bool publicInputCensusClosed;
            public bool candidatePacketAdmission;
            public bool exactPackedRowParity;
            public bool drawTimeCb3Available;
            public bool visualAdmission;
            public bool nativePackedColorProducerProven;
            public string nativePackedColorContract;
            public string[] unresolvedInputs;
            public PacketFieldContract[] packetFields;
            public RendererRecord[] renderers;
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Li Zhiyan M23 Managed Particle Packet Census PTS 40000")]
        public static void RunAndWriteEvidence()
        {
            string outputPath = ProjectAbsolute(OutputRelativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            var report = new CensusReport
            {
                schema = "endfield.lizhiyan-m23-managed-particle-packet-census.v1",
                status = "failed",
                failure = "not_started",
                unityVersion = Application.unityVersion,
                graphicsDeviceType = SystemInfo.graphicsDeviceType.ToString(),
                prefab = PrefabPath,
                effectRoot = ExpectedRoot,
                retailPts = RetailPts,
                retailClockOriginPts = RetailClockOriginPts,
                localSeconds = (RetailPts - RetailClockOriginPts) /
                    (float)RetailClockUnitsPerSecond,
                packetStrideBytes = ExpectedPacketStrideBytes,
                packetAbiProvenance =
                    "exact 136-byte IA field offsets are recovered from the M23 " +
                    "DXBC/ISGN contract; public Unity APIs do not expose the packed rows",
                sourceRendererSubmissionPath = false,
                candidatePacketAdmission = false,
                exactPackedRowParity = false,
                drawTimeCb3Available = false,
                visualAdmission = false,
                nativePackedColorProducerProven = true,
                nativePackedColorContract =
                    "pinned DrawMeshParticles<4> reads one RGBA8 row per particle, " +
                    "divides by 255, and writes cb3[13]=1-packedRGBA; BakeMesh.colors32 " +
                    "is the exact observed COLOR0 lane, not GetCurrentColor",
                unresolvedInputs = UnresolvedInputs(),
                packetFields = PacketFields(),
            };
            Scene scene = default(Scene);
            GameObject instance = null;
            try
            {
                Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                    "M23 packet census requires a real graphics backend; do not use -nographics");
                EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ValidateBatch();
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
                Require(prefab != null, "Missing generated M23 prefab: " + PrefabPath);
                scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                instance = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                Require(instance != null, "Could not instantiate generated M23 prefab");
                instance.name = ExpectedRoot;
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                instance.transform.localScale = Vector3.one;
                var marker = instance.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(marker != null && marker.contractSchema == ExpectedSchema &&
                    marker.effectRoot == ExpectedRoot && marker.particleNodes != null &&
                    marker.particleNodes.Length == 6,
                    "Generated M23 source marker contract drifted");
                report.sourceEffectDelay = marker.sourceEffectDelay;
                Require(Mathf.Abs(marker.sourceEffectDelay - ExpectedEffectDelay) < 0.00001f,
                    "M23 source effect delay drifted: " + marker.sourceEffectDelay);
                report.effectLocalSeconds = report.localSeconds - marker.sourceEffectDelay;
                Require(report.effectLocalSeconds >= 0.0f,
                    "PTS 40000 precedes M23 source effect start");

                var rows = new List<RendererRecord>();
                foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
                {
                    if (node == null || !node.hierarchy.Contains("/xuanzhuan"))
                        continue;
                    rows.Add(ProbeRenderer(instance, node, report.effectLocalSeconds));
                }
                Require(rows.Count == 4, "M23 packet census renderer count drifted: " + rows.Count);
                report.renderers = rows.ToArray();
                report.publicInputCensusClosed = report.renderers.All(row =>
                    row.publicParticleInputsClosed && row.sourceMeshInputsClosed &&
                    row.candidateRowsBuilt);
                report.status = report.publicInputCensusClosed ? "incomplete" : "failed";
                report.failure = report.publicInputCensusClosed
                    ? "public source census closed; exact 136-byte packed rows, " +
                      "internal renderer packing, and draw-time cb3 remain unresolved"
                    : "one or more public source inputs could not be captured";
                Require(report.publicInputCensusClosed,
                    "M23 public source-input census did not close");
                Debug.LogWarning("M23 managed packet census is intentionally non-admitting: " +
                    outputPath);
            }
            catch (Exception exception)
            {
                report.status = "failed";
                report.failure = exception.GetType().Name + ": " + exception.Message;
                report.publicInputCensusClosed = false;
                Debug.LogError("Li Zhiyan M23 managed packet census failed closed: " + report.failure);
            }
            finally
            {
                if (instance != null)
                    UnityEngine.Object.DestroyImmediate(instance);
                if (scene.IsValid() && scene.isLoaded && SceneManager.sceneCount > 1)
                    EditorSceneManager.CloseScene(scene, true);
                File.WriteAllText(outputPath, JsonUtility.ToJson(report, true) + "\n",
                    new UTF8Encoding(false));
            }
            if (report.status == "failed")
                throw new InvalidOperationException(report.failure);
        }

        private static RendererRecord ProbeRenderer(
            GameObject instance,
            EndfieldRecoveredParticleNodeSource node,
            float effectLocalSeconds)
        {
            Transform host = FindHierarchy(instance.transform, node.hierarchy);
            Require(host != null, "M23 renderer hierarchy missing: " + node.hierarchy);
            ParticleSystem system = host.GetComponent<ParticleSystem>();
            ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
            Require(system != null && renderer != null,
                "M23 ParticleSystem/Renderer component missing: " + node.hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            int[] streamIds = streams.Select(value => (int)value).ToArray();
            Require(streamIds.SequenceEqual(ExpectedStreams),
                "M23 authored stream tuple drifted: " + node.hierarchy);
            Require(renderer.renderMode == ParticleSystemRenderMode.Mesh,
                "M23 renderer is not mesh mode: " + node.hierarchy);
            Require(node.meshPathIds != null && node.materialPathIds != null,
                "M23 source identity arrays are missing: " + node.hierarchy);
            Mesh[] meshes = new Mesh[renderer.meshCount];
            float[] weights = new float[renderer.meshCount];
            Require(renderer.GetMeshes(meshes) == meshes.Length && meshes.Length > 0 &&
                renderer.GetMeshWeightings(weights) == weights.Length,
                "M23 source mesh slots are incomplete: " + node.hierarchy);
            Require(renderer.sharedMaterials.Length == 1 && renderer.sharedMaterials[0] != null,
                "M23 source material binding is incomplete: " + node.hierarchy);
            ParticleSystem.MainModule main = system.main;
            Require(!system.useAutoRandomSeed,
                "M23 source system uses automatic random seed: " + node.hierarchy);
            uint seed = system.randomSeed;
            ResetAndSimulate(system, effectLocalSeconds, seed, node.hierarchy);
            var particles = new ParticleSystem.Particle[Mathf.Max(system.particleCount, main.maxParticles)];
            int particleCount = system.GetParticles(particles);
            Array.Resize(ref particles, particleCount);
            var custom = new List<Vector4>(particleCount);
            int customCount = system.GetCustomParticleData(custom, ParticleSystemCustomData.Custom1);
            Require(customCount == particleCount && custom.Count == particleCount,
                "M23 Custom1 count does not match particles: " + node.hierarchy);

            var uniqueMeshes = new List<SourceMeshRecord>();
            var meshIndexById = new Dictionary<int, int>();
            for (int index = 0; index < meshes.Length; ++index)
            {
                Require(meshes[index] != null, "M23 source mesh is null at slot " + index);
                meshIndexById[index] = uniqueMeshes.Count;
                uniqueMeshes.Add(DescribeMesh(meshes[index],
                    index < node.meshPathIds.Length ? node.meshPathIds[index] : 0L));
            }

            var particleRows = new ParticleRecord[particleCount];
            int totalVertices = 0;
            int totalIndices = 0;
            for (int index = 0; index < particleCount; ++index)
            {
                ParticleSystem.Particle particle = particles[index];
                int meshIndex = particle.GetMeshIndex(system);
                Require(meshIndex >= 0 && meshIndex < meshes.Length && meshes[meshIndex] != null,
                    "M23 particle selected invalid mesh index " + meshIndex + " at " + node.hierarchy);
                SourceMeshRecord source = uniqueMeshes[meshIndexById[meshIndex]];
                particleRows[index] = DescribeParticle(
                    system, source, meshes[meshIndex], particle, custom[index], index);
                totalVertices += meshes[meshIndex].vertexCount;
                totalIndices += CountIndices(meshes[meshIndex]);
            }
            return new RendererRecord
            {
                hierarchy = node.hierarchy,
                particleSystemPathId = node.particleSystemPathId,
                particleRendererPathId = node.particleRendererPathId,
                materialPathId = node.materialPathIds.Length == 1 ? node.materialPathIds[0] : 0L,
                meshPathIds = node.meshPathIds,
                materialName = renderer.sharedMaterials[0].name,
                materialShaderName = renderer.sharedMaterials[0].shader == null
                    ? string.Empty : renderer.sharedMaterials[0].shader.name,
                sourceRendererEnabled = node.sourceRendererEnabled && renderer.enabled,
                renderMode = renderer.renderMode.ToString(),
                alignment = renderer.alignment.ToString(),
                sortMode = renderer.sortMode.ToString(),
                velocityScale = renderer.velocityScale,
                cameraVelocityScale = renderer.cameraVelocityScale,
                enableGPUInstancing = renderer.enableGPUInstancing,
                activeVertexStreams = streams.Select(value => value.ToString()).ToArray(),
                activeVertexStreamIds = streamIds,
                sourceMeshWeights = weights,
                systemLocalToWorld = MatrixRecord.From(system.transform.localToWorldMatrix),
                particleCount = particleCount,
                totalSourceVertices = totalVertices,
                totalSourceIndices = totalIndices,
                publicParticleInputsClosed = true,
                sourceMeshInputsClosed = uniqueMeshes.All(IsCompleteMesh),
                candidateRowsBuilt = true,
                exactPackedRowsAvailable = false,
                drawTimeCb3Available = false,
                sourceMeshes = uniqueMeshes.ToArray(),
                particles = particleRows,
                unresolvedInputs = UnresolvedInputs(),
            };
        }

        private static SourceMeshRecord DescribeMesh(Mesh mesh, long meshPathId)
        {
            var uv = new Float4Record[8][];
            for (int channel = 0; channel < uv.Length; ++channel)
            {
                var values = new List<Vector4>();
                mesh.GetUVs(channel, values);
                uv[channel] = values.Select(Float4Record.From).ToArray();
            }
            BoneWeight[] weights = mesh.boneWeights ?? Array.Empty<BoneWeight>();
            Matrix4x4[] bindPoses = mesh.bindposes ?? Array.Empty<Matrix4x4>();
            var subMeshes = new SubmeshRecord[mesh.subMeshCount];
            var submeshCounts = new int[mesh.subMeshCount];
            for (int submesh = 0; submesh < mesh.subMeshCount; ++submesh)
            {
                int[] indices = mesh.GetIndices(submesh);
                submeshCounts[submesh] = indices.Length;
                subMeshes[submesh] = new SubmeshRecord { submesh = submesh, indices = indices };
            }
            Vector3[] positions = mesh.vertices ?? Array.Empty<Vector3>();
            Vector3[] normals = mesh.normals ?? Array.Empty<Vector3>();
            Vector4[] tangents = mesh.tangents ?? Array.Empty<Vector4>();
            Color32[] colors = mesh.colors32 ?? Array.Empty<Color32>();
            return new SourceMeshRecord
            {
                name = mesh.name,
                meshPathId = meshPathId,
                vertexCount = mesh.vertexCount,
                subMeshCount = mesh.subMeshCount,
                subMeshIndexCounts = submeshCounts,
                subMeshes = subMeshes,
                positions = positions.Select(Float3Record.From).ToArray(),
                normals = normals.Select(Float3Record.From).ToArray(),
                tangents = tangents.Select(Float4Record.From).ToArray(),
                colors = colors.Select(ColorRecord.From).ToArray(),
                uv0 = uv[0], uv1 = uv[1], uv2 = uv[2], uv3 = uv[3],
                uv4 = uv[4], uv5 = uv[5], uv6 = uv[6], uv7 = uv[7],
                boneWeights = weights.Select(BoneWeightRecord.From).ToArray(),
                bindPoses = bindPoses.Select(MatrixRecord.From).ToArray(),
                channels = new[]
                {
                    Channel("POSITION", positions.Length == mesh.vertexCount, positions.Length,
                        "proven", "Mesh.vertices"),
                    Channel("NORMAL", normals.Length == mesh.vertexCount, normals.Length,
                        "proven", "Mesh.normals"),
                    Channel("TANGENT", tangents.Length == mesh.vertexCount, tangents.Length,
                        "proven", "Mesh.tangents; packed-row placement remains unresolved"),
                    Channel("COLOR0", colors.Length == mesh.vertexCount, colors.Length,
                        colors.Length == mesh.vertexCount ? "proven" : "unresolved",
                        colors.Length == mesh.vertexCount ? "Mesh.colors32" : "source mesh has no COLOR0"),
                    Channel("TEXCOORD0", uv[0].Length == mesh.vertexCount, uv[0].Length,
                        "proven", "Mesh.GetUVs(0)"),
                    Channel("TEXCOORD1", uv[1].Length == mesh.vertexCount, uv[1].Length,
                        "proven", "Mesh.GetUVs(1)"),
                    Channel("TEXCOORD4", uv[4].Length == mesh.vertexCount, uv[4].Length,
                        uv[4].Length == mesh.vertexCount ? "proven" : "unresolved",
                        "Mesh.GetUVs(4); Custom1 replication is a separate public input"),
                    Channel("BLENDWEIGHTS", weights.Length == mesh.vertexCount, weights.Length,
                        weights.Length == mesh.vertexCount ? "proven" : "unresolved",
                        "Mesh.boneWeights; renderer ABI use is unresolved"),
                    Channel("BLENDINDICES", weights.Length == mesh.vertexCount, weights.Length,
                        weights.Length == mesh.vertexCount ? "proven" : "unresolved",
                        "Mesh.boneWeights; renderer ABI use is unresolved"),
                },
            };
        }

        private static ParticleRecord DescribeParticle(
            ParticleSystem system,
            SourceMeshRecord source,
            Mesh mesh,
            ParticleSystem.Particle particle,
            Vector4 custom1,
            int particleIndex)
        {
            Vector3 size = particle.GetCurrentSize3D(system);
            Quaternion rotation = system.main.startRotation3D
                ? Quaternion.Euler(particle.rotation3D)
                : Quaternion.AngleAxis(particle.rotation, particle.axisOfRotation);
            Matrix4x4 local = Matrix4x4.TRS(particle.position, rotation, size);
            Matrix4x4 world = system.transform.localToWorldMatrix * local;
            Matrix4x4 normalMatrix = world.inverse.transpose;
            Vector3[] positions = mesh.vertices ?? Array.Empty<Vector3>();
            Vector3[] normals = mesh.normals ?? Array.Empty<Vector3>();
            Vector4[] tangents = mesh.tangents ?? Array.Empty<Vector4>();
            Color32[] colors = mesh.colors32 ?? Array.Empty<Color32>();
            Vector4[][] uvs = new Vector4[8][];
            for (int channel = 0; channel < uvs.Length; ++channel)
            {
                var values = new List<Vector4>();
                mesh.GetUVs(channel, values);
                uvs[channel] = values.ToArray();
            }
            BoneWeight[] weights = mesh.boneWeights ?? Array.Empty<BoneWeight>();
            var vertices = new PacketVertexRecord[mesh.vertexCount];
            for (int vertex = 0; vertex < mesh.vertexCount; ++vertex)
            {
                Vector3 sourcePosition = positions[vertex];
                Vector3 sourceNormal = normals.Length == mesh.vertexCount
                    ? normals[vertex] : Vector3.zero;
                Vector3 transformedNormal = normalMatrix.MultiplyVector(sourceNormal).normalized;
                Vector4 sourceTangent = tangents.Length == mesh.vertexCount
                    ? tangents[vertex] : Vector4.zero;
                Vector3 transformedTangent = world.MultiplyVector(
                    new Vector3(sourceTangent.x, sourceTangent.y, sourceTangent.z)).normalized;
                Vector4 candidateTangent = new Vector4(
                    transformedTangent.x, transformedTangent.y, transformedTangent.z, sourceTangent.w);
                vertices[vertex] = new PacketVertexRecord
                {
                    sourceVertexIndex = vertex,
                    sourcePosition = Float3Record.From(sourcePosition),
                    sourceNormal = Float3Record.From(sourceNormal),
                    sourceTangent = tangents.Length == mesh.vertexCount
                        ? Float4Record.From(sourceTangent) : null,
                    sourceColor = colors.Length == mesh.vertexCount
                        ? ColorRecord.From(colors[vertex]) : null,
                    sourceUv0 = uvs[0].Length == mesh.vertexCount
                        ? Float4Record.From(uvs[0][vertex]) : null,
                    sourceUv1 = uvs[1].Length == mesh.vertexCount
                        ? Float4Record.From(uvs[1][vertex]) : null,
                    sourceUv4 = uvs[4].Length == mesh.vertexCount
                        ? Float4Record.From(uvs[4][vertex]) : null,
                    sourceBoneWeight = weights.Length == mesh.vertexCount
                        ? BoneWeightRecord.From(weights[vertex]) : null,
                    candidatePosition = Float3Record.From(world.MultiplyPoint3x4(sourcePosition)),
                    candidateNormal = Float3Record.From(transformedNormal),
                    candidateTangent = tangents.Length == mesh.vertexCount
                        ? Float4Record.From(candidateTangent) : null,
                    publicCurrentColorNotPackedColor =
                        ColorRecord.From(particle.GetCurrentColor(system)),
                    candidateTexcoord4 = Float4Record.From(custom1),
                    candidateContract =
                        "candidate only: source channel plus public particle transform/Custom1; " +
                        "not Unity internal packed-row parity",
                };
            }
            Color32 startColor = particle.startColor;
            return new ParticleRecord
            {
                particleIndex = particleIndex,
                meshIndex = particle.GetMeshIndex(system),
                randomSeed = particle.randomSeed,
                position = Float3Record.From(particle.position),
                velocity = Float3Record.From(particle.velocity),
                animatedVelocity = Float3Record.From(particle.animatedVelocity),
                axisOfRotation = Float3Record.From(particle.axisOfRotation),
                rotation = particle.rotation,
                rotation3D = Float3Record.From(particle.rotation3D),
                angularVelocity = particle.angularVelocity,
                angularVelocity3D = Float3Record.From(particle.angularVelocity3D),
                startSize = particle.startSize,
                startSize3D = Float3Record.From(particle.startSize3D),
                startColor = ColorRecord.From(startColor),
                currentColor = ColorRecord.From(particle.GetCurrentColor(system)),
                remainingLifetime = particle.remainingLifetime,
                startLifetime = particle.startLifetime,
                custom1 = Float4Record.From(custom1),
                currentSize3D = Float3Record.From(size),
                rotationQuaternion = QuaternionRecord.From(rotation),
                particleLocalMatrix = MatrixRecord.From(local),
                particleWorldMatrix = MatrixRecord.From(world),
                particleNormalMatrix = MatrixRecord.From(normalMatrix),
                publicInputProvenance =
                    "proven from ParticleSystem.GetParticles + GetCustomParticleData(Custom1); " +
                    "derived size/color/rotation are Unity public API values",
                vertices = vertices,
            };
        }

        private static bool IsCompleteMesh(SourceMeshRecord mesh)
        {
            if (mesh == null || mesh.positions == null || mesh.normals == null ||
                mesh.positions.Length != mesh.vertexCount || mesh.normals.Length != mesh.vertexCount)
                return false;
            // These are the only channels whose values are required to build
            // the managed census rows.  Missing channels remain represented as
            // unresolved rather than silently zero-filled in a packet.
            return mesh.channels != null && mesh.channels.Any(value =>
                value.semantic == "POSITION" && value.present) &&
                mesh.channels.Any(value => value.semantic == "NORMAL" && value.present);
        }

        private static PacketFieldContract[] PacketFields()
        {
            return new[]
            {
                Field("POSITION", 0, 3, "inferred", "source position + public particle TRS",
                    "136-byte destination is known; Unity internal packing is not exposed"),
                Field("NORMAL", 12, 3, "inferred", "source normal + public inverse-transpose candidate",
                    "candidate agrees with BakeMesh oracle, not packed-row parity"),
                Field("TANGENT", 24, 4, "inferred", "Mesh.tangents + public particle transform",
                    "destination placement known from ISGN; renderer packing unresolved"),
                Field("COLOR0", 40, 4, "producer_proven_value_unresolved",
                    "renderer packed RGBA8 / BakeMesh.colors32",
                    "source COLOR0 is absent; GetCurrentColor is census-only and differs by one alpha quantum for particle 1"),
                Field("TEXCOORD0", 56, 4, "inferred", "Mesh.GetUVs(0)",
                    "source value captured; internal stream-to-slot packing unresolved"),
                Field("TEXCOORD1", 72, 4, "inferred", "Mesh.GetUVs(1)",
                    "source value captured; internal stream-to-slot packing unresolved"),
                Field("TEXCOORD4", 88, 4, "unresolved", "Mesh.GetUVs(4) and Custom1",
                    "Custom1 stream 34 is public, but its TEXCOORD4 expansion is not proven"),
                Field("BLENDWEIGHTS", 104, 4, "unresolved", "Mesh.boneWeights",
                    "shader skin branch and renderer default fill are not proven"),
                Field("BLENDINDICES", 120, 4, "unresolved", "Mesh.boneWeights",
                    "shader skin branch and renderer default fill are not proven"),
            };
        }

        private static PacketFieldContract Field(
            string semantic, int offset, int components, string provenance,
            string source, string note)
        {
            return new PacketFieldContract
            {
                semantic = semantic, offsetBytes = offset, componentCount = components,
                provenance = provenance, source = source, note = note,
            };
        }

        private static ChannelRecord Channel(
            string semantic, bool present, int count, string provenance, string note)
        {
            return new ChannelRecord
            {
                semantic = semantic, present = present, count = count,
                provenance = provenance, note = note,
            };
        }

        private static string[] UnresolvedInputs()
        {
            return new[]
            {
                "Unity internal ParticleSystemRenderer expansion into the 136-byte IA row",
                "exact per-row COLOR0 bytes without invoking the separate BakeMesh oracle",
                "exact Custom1-to-TEXCOORD4 expansion and any padding/default values",
                "exact BLENDWEIGHTS/BLENDINDICES renderer fill; native cb3[4].w=0 proves the lanes are behaviorally unused here",
                "draw-time VS cb3[14] bytes and producer timing",
                "runtime texture/SRV identity at the real particle draw",
            };
        }

        private static void ResetAndSimulate(
            ParticleSystem system, float seconds, uint seed, string hierarchy)
        {
            system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            system.Clear(true);
            system.randomSeed = seed;
            Require(system.randomSeed == seed, "M23 could not restore randomSeed at " + hierarchy);
            system.Simulate(seconds, false, true, false);
            system.Play(false);
        }

        private static Transform FindHierarchy(Transform root, string path)
        {
            string[] pieces = path.Split('/');
            int start = pieces.Length > 0 && root.name == pieces[0] ? 1 : 0;
            Transform current = root;
            for (int index = start; index < pieces.Length; ++index)
            {
                current = current.Find(pieces[index]);
                if (current == null) return null;
            }
            return current;
        }

        private static int CountIndices(Mesh mesh)
        {
            int total = 0;
            for (int submesh = 0; submesh < mesh.subMeshCount; ++submesh)
                total += (int)mesh.GetIndexCount(submesh);
            return total;
        }

        private static string ProjectAbsolute(string relative)
        {
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            return Path.Combine(projectRoot, relative.Replace('/', Path.DirectorySeparatorChar));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
