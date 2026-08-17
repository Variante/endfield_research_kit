// Standalone Li Zhiyan M23 source-mesh/particle-segment oracle.
//
// This is deliberately independent from the actor visual capture harness.  It
// only samples the source-closed start_04_2 particle prefab at the retail
// anchor PTS 40000, records public Unity ParticleSystem/BakeMesh state, and
// fails closed when a segment cannot be mapped without inventing an input.

using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldLiZhiyanM23SourceMeshOracle
    {
        private const string PrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Lizhiyan/" +
            "Effects/OverviewPeakParticles/" +
            "P_fxui_lizhiyan_overview_start_04_2.prefab";
        private const string ExpectedSchema =
            "endfield.lizhiyan-overview-peak-particle-effects.v1";
        private const string ExpectedRoot =
            "P_fxui_lizhiyan_overview_start_04_2";
        private const int RetailPts = 40000;
        private const int RetailClockOriginPts = 37967;
        private const int RetailClockUnitsPerSecond = 1000;
        private const float ExpectedEffectDelay = 1.833333f;
        private const string OutputRelativePath =
            "scratch/character_recovery/lizhiyan_m23_source_mesh_oracle/" +
            "pts_40000.json";

        private static readonly int[] ExpectedStreams = { 0, 1, 3, 4, 5, 34 };

        private sealed class RendererSpec
        {
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public long meshPathId;
            public long materialPathId;
        }

        private static readonly RendererSpec[] RendererSpecs =
        {
            new RendererSpec
            {
                hierarchy = ExpectedRoot + "/xuanzhuan03",
                particleSystemPathId = 2171212438583907872L,
                particleRendererPathId = 37981486576571936L,
                meshPathId = 5776537116290261507L,
                materialPathId = -430604955415889784L,
            },
            new RendererSpec
            {
                hierarchy = ExpectedRoot + "/xuanzhuan03_02",
                particleSystemPathId = 8324091109314139680L,
                particleRendererPathId = 5944045158489396768L,
                meshPathId = 987594971817297645L,
                materialPathId = -430604955415889784L,
            },
            new RendererSpec
            {
                hierarchy = ExpectedRoot + "/xuanzhuan04",
                particleSystemPathId = 8348750931752523296L,
                particleRendererPathId = 6551385765768926752L,
                meshPathId = 5776537116290261507L,
                materialPathId = -430604955415889784L,
            },
            new RendererSpec
            {
                hierarchy = ExpectedRoot + "/xuanzhuan04_02",
                particleSystemPathId = 4395430579353425440L,
                particleRendererPathId = -9496592748243424L,
                meshPathId = 987594971817297645L,
                materialPathId = -430604955415889784L,
            },
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
                    x = value.x,
                    y = value.y,
                    z = value.z,
                    w = value.w,
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
        }

        [Serializable]
        private sealed class ChannelEvidence
        {
            public string semantic;
            public bool present;
            public int count;
            public string sha256;
        }

        [Serializable]
        private sealed class SourceMeshEvidence
        {
            public string name;
            public long meshPathId;
            public int vertexCount;
            public int subMeshCount;
            public int indexCount;
            public int[] subMeshIndexCounts;
            public ChannelEvidence positions;
            public ChannelEvidence normals;
            public ChannelEvidence tangents;
            public ChannelEvidence colors;
            public ChannelEvidence uv0;
            public ChannelEvidence uv1;
            public ChannelEvidence uv2;
            public ChannelEvidence uv3;
            public ChannelEvidence uv4;
            public ChannelEvidence uv5;
            public ChannelEvidence uv6;
            public ChannelEvidence uv7;
            public string sourceBoundsSha256;
        }

        [Serializable]
        private sealed class BakedMeshEvidence
        {
            public int vertexCount;
            public int subMeshCount;
            public int indexCount;
            public int[] subMeshIndexCounts;
            public ChannelEvidence positions;
            public ChannelEvidence normals;
            public ChannelEvidence tangents;
            public ChannelEvidence colors;
            public ChannelEvidence uv0;
            public ChannelEvidence uv1;
            public ChannelEvidence uv2;
            public ChannelEvidence uv3;
            public ChannelEvidence uv4;
            public ChannelEvidence uv5;
            public ChannelEvidence uv6;
            public ChannelEvidence uv7;
            public string boundsSha256;
        }

        [Serializable]
        private sealed class ParticleEvidence
        {
            public int particleIndex;
            public int meshIndex;
            public uint randomSeed;
            public Float3Record position;
            public Float3Record rotation3D;
            public Float3Record size3D;
            public Float3Record velocity;
            public ColorRecord color;
            public Float4Record custom1;
            public int sourceVertexOffset;
            public int sourceVertexCount;
            public int bakedVertexOffset;
            public int bakedVertexCount;
            public int sourceIndexCount;
            public int bakedIndexOffset;
            public int bakedIndexCount;
            public bool bakedIndexRangeValid;
            public string sourcePositionSha256;
            public string bakedPositionSegmentSha256;
            public string bakedNormalSegmentSha256;
            public string bakedColorSegmentSha256;
            public string bakedUv0SegmentSha256;
            public string bakedUv1SegmentSha256;
            public int custom1Uv0ReplicationMask;
            public int custom1Uv1ReplicationMask;
            public int custom1Uv2ReplicationMask;
            public int custom1Uv3ReplicationMask;
            public int custom1Uv4ReplicationMask;
            public int custom1Uv5ReplicationMask;
            public int custom1Uv6ReplicationMask;
            public int custom1Uv7ReplicationMask;
        }

        [Serializable]
        private sealed class RendererEvidence
        {
            public string hierarchy;
            public long particleSystemPathId;
            public long particleRendererPathId;
            public long materialPathId;
            public long[] meshPathIds;
            public int[] authoredStreamIds;
            public string[] authoredStreams;
            public bool sourceRendererEnabled;
            public bool sourceGeometryClosed;
            public bool particleStateClosed;
            public bool custom1Closed;
            public bool segmentMappingClosed;
            public int particleCount;
            public int bakedVertexCount;
            public int bakedIndexCount;
            public string particleStateSha256;
            public string custom1Sha256;
            public SourceMeshEvidence[] sourceMeshes;
            public BakedMeshEvidence bakedMesh;
            public ParticleEvidence[] particles;
        }

        [Serializable]
        private sealed class OracleReport
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
            public bool sourceContractPassed;
            public bool noDefaultsUsed;
            public bool visualAdmission;
            public RendererEvidence[] renderers;
        }

        [MenuItem("Endfield/Character Recovery Lab/Render Diagnostics/" +
            "Li Zhiyan M23 Source Mesh Oracle PTS 40000")]
        public static void RunAndWriteEvidence()
        {
            string outputPath = ProjectAbsolute(OutputRelativePath);
            Directory.CreateDirectory(Path.GetDirectoryName(outputPath));
            OracleReport report = new OracleReport
            {
                schema = "endfield.lizhiyan-m23-source-mesh-oracle.v1",
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
                visualAdmission = false,
                noDefaultsUsed = true,
            };
            Scene scene = default(Scene);
            GameObject instance = null;
            GameObject cameraObject = null;
            try
            {
                Require(SystemInfo.graphicsDeviceType != GraphicsDeviceType.Null,
                    "M23 source oracle requires a real graphics backend; do not use -nographics");
                // Reuse the maintained source-closed peak importer validator;
                // this oracle never reconstructs meshes/materials or silently
                // substitutes missing serialized dependencies.
                EndfieldLiZhiyanOverviewPeakParticleEffectImporter.ValidateBatch();
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(PrefabPath);
                Require(prefab != null, "Missing generated M23 prefab: " + PrefabPath);
                scene = EditorSceneManager.NewScene(
                    NewSceneSetup.EmptyScene, NewSceneMode.Single);
                instance = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                Require(instance != null, "Could not instantiate generated M23 prefab");
                instance.name = ExpectedRoot;
                instance.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                instance.transform.localScale = Vector3.one;
                Require(instance.name == ExpectedRoot,
                    "Generated M23 prefab root identity drifted");

                EndfieldRecoveredParticleEffectSource marker =
                    instance.GetComponent<EndfieldRecoveredParticleEffectSource>();
                Require(marker != null && marker.contractSchema == ExpectedSchema &&
                    marker.effectRoot == ExpectedRoot && marker.particleNodes.Length == 6,
                    "Generated M23 source marker contract drifted");
                report.sourceEffectDelay = marker.sourceEffectDelay;
                Require(Mathf.Abs(marker.sourceEffectDelay - ExpectedEffectDelay) < 0.00001f,
                    "M23 source effect delay drifted: " + marker.sourceEffectDelay);
                report.effectLocalSeconds = report.localSeconds - marker.sourceEffectDelay;
                Require(report.effectLocalSeconds >= 0.0f,
                    "PTS 40000 precedes M23 source effect start");

                cameraObject = new GameObject("LiZhiyan_M23_SourceMesh_Oracle_Camera");
                SceneManager.MoveGameObjectToScene(cameraObject, scene);
                Camera camera = cameraObject.AddComponent<Camera>();
                camera.enabled = false;
                camera.transform.SetPositionAndRotation(
                    new Vector3(0.0f, 0.0f, -10.0f), Quaternion.identity);

                var rows = new List<RendererEvidence>();
                foreach (RendererSpec spec in RendererSpecs)
                    rows.Add(ProbeRenderer(instance, marker, camera, spec, report.effectLocalSeconds));
                report.renderers = rows.ToArray();
                report.sourceContractPassed = true;
                report.status = "passed";
                report.failure = string.Empty;
                Require(report.renderers.Length == RendererSpecs.Length &&
                    report.renderers.All(row => row.sourceGeometryClosed &&
                        row.particleStateClosed && row.custom1Closed &&
                        row.segmentMappingClosed),
                    "M23 source mesh/particle segment evidence did not close");
            }
            catch (Exception exception)
            {
                report.status = "failed";
                report.failure = exception.GetType().Name + ": " + exception.Message;
                report.sourceContractPassed = false;
                Debug.LogError("Li Zhiyan M23 source mesh oracle failed closed: " + report.failure);
                throw;
            }
            finally
            {
                if (cameraObject != null)
                    UnityEngine.Object.DestroyImmediate(cameraObject);
                if (instance != null)
                    UnityEngine.Object.DestroyImmediate(instance);
                if (scene.IsValid() && scene.isLoaded && SceneManager.sceneCount > 1)
                    EditorSceneManager.CloseScene(scene, true);
                File.WriteAllText(outputPath, JsonUtility.ToJson(report, true) + "\n",
                    new UTF8Encoding(false));
            }
            Debug.Log("PASS Li Zhiyan M23 source mesh oracle: report=" + outputPath);
        }

        private static RendererEvidence ProbeRenderer(
            GameObject instance,
            EndfieldRecoveredParticleEffectSource marker,
            Camera camera,
            RendererSpec spec,
            float effectLocalSeconds)
        {
            EndfieldRecoveredParticleNodeSource node = marker.particleNodes.SingleOrDefault(
                value => value.particleRendererPathId == spec.particleRendererPathId);
            Require(node != null, "M23 renderer marker missing: " + spec.hierarchy);
            Require(node.hierarchy == spec.hierarchy &&
                node.particleSystemPathId == spec.particleSystemPathId &&
                node.materialPathIds.Length == 1 && node.materialPathIds[0] == spec.materialPathId &&
                node.meshPathIds.Length == 1 && node.meshPathIds[0] == spec.meshPathId,
                "M23 source identity drifted: " + spec.hierarchy);
            Transform host = FindHierarchy(instance.transform, node.hierarchy);
            Require(host != null, "M23 renderer hierarchy missing: " + spec.hierarchy);
            ParticleSystem system = host.GetComponent<ParticleSystem>();
            ParticleSystemRenderer renderer = host.GetComponent<ParticleSystemRenderer>();
            Require(system != null && renderer != null,
                "M23 ParticleSystem/Renderer component missing: " + spec.hierarchy);
            Require(renderer.sharedMaterials.Length == 1 && renderer.sharedMaterials[0] != null,
                "M23 renderer material binding incomplete: " + spec.hierarchy);
            Require(renderer.renderMode == ParticleSystemRenderMode.Mesh,
                "M23 renderer is not mesh mode: " + spec.hierarchy);
            var streams = new List<ParticleSystemVertexStream>();
            renderer.GetActiveVertexStreams(streams);
            int[] streamIds = streams.Select(value => (int)value).ToArray();
            Require(streamIds.SequenceEqual(ExpectedStreams),
                "M23 authored vertex stream tuple drifted: " + spec.hierarchy);

            Mesh[] meshes = new Mesh[renderer.meshCount];
            float[] weights = new float[renderer.meshCount];
            Require(renderer.GetMeshes(meshes) == meshes.Length && meshes.Length == 1 &&
                renderer.GetMeshWeightings(weights) == weights.Length &&
                meshes[0] != null && Mathf.Abs(weights[0] - 1.0f) < 0.000001f,
                "M23 source mesh slots are incomplete: " + spec.hierarchy);
            Require(renderer.mesh == meshes[0], "M23 primary mesh identity drifted: " + spec.hierarchy);

            ParticleSystem.MainModule main = system.main;
            Require(!system.useAutoRandomSeed,
                "M23 system uses automatic random seed: " + spec.hierarchy);
            system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            system.Clear(true);
            system.Simulate(effectLocalSeconds, true, true, true);
            var particles = new ParticleSystem.Particle[Mathf.Max(system.particleCount, main.maxParticles)];
            int particleCount = system.GetParticles(particles);
            Array.Resize(ref particles, particleCount);
            var customRows = new List<Vector4>(particleCount);
            int customCount = system.GetCustomParticleData(customRows, ParticleSystemCustomData.Custom1);
            Require(customCount == particleCount && customRows.Count == particleCount,
                "M23 Custom1 count does not match particle count: " + spec.hierarchy);

            Mesh baked = new Mesh { name = "LiZhiyan_M23_SourceMesh_Oracle_Baked" };
            try
            {
                renderer.BakeMesh(baked, camera,
                    ParticleSystemBakeMeshOptions.BakePosition |
                    ParticleSystemBakeMeshOptions.BakeRotationAndScale);
                SourceMeshEvidence source = DescribeSourceMesh(meshes[0], spec.meshPathId);
                BakedMeshEvidence bakedEvidence = DescribeBakedMesh(baked);
                int expectedVertices = particleCount * meshes[0].vertexCount;
                int expectedIndices = particleCount * CountIndices(meshes[0]);
                Require(baked.subMeshCount == meshes[0].subMeshCount,
                    "M23 BakeMesh submesh count drifted at " + spec.hierarchy);
                Require(baked.vertexCount == expectedVertices && CountIndices(baked) == expectedIndices,
                    "M23 BakeMesh geometry count mismatch at " + spec.hierarchy +
                    ": actual=" + baked.vertexCount + "/" + CountIndices(baked) +
                    ", expected=" + expectedVertices + "/" + expectedIndices);
                ParticleEvidence[] particlesEvidence = BuildParticleEvidence(
                    system, meshes[0], baked, particles, customRows, particleCount);
                return new RendererEvidence
                {
                    hierarchy = spec.hierarchy,
                    particleSystemPathId = spec.particleSystemPathId,
                    particleRendererPathId = spec.particleRendererPathId,
                    materialPathId = spec.materialPathId,
                    meshPathIds = new[] { spec.meshPathId },
                    authoredStreamIds = streamIds,
                    authoredStreams = streams.Select(value => value.ToString()).ToArray(),
                    sourceRendererEnabled = renderer.enabled,
                    sourceGeometryClosed = true,
                    particleStateClosed = true,
                    custom1Closed = true,
                    segmentMappingClosed = particlesEvidence.All(value =>
                        value.bakedIndexRangeValid),
                    particleCount = particleCount,
                    bakedVertexCount = baked.vertexCount,
                    bakedIndexCount = CountIndices(baked),
                    particleStateSha256 = HashParticleState(particles, system),
                    custom1Sha256 = HashVector4(customRows.ToArray()),
                    sourceMeshes = new[] { source },
                    bakedMesh = bakedEvidence,
                    particles = particlesEvidence,
                };
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(baked);
            }
        }

        private static ParticleEvidence[] BuildParticleEvidence(
            ParticleSystem system,
            Mesh source,
            Mesh baked,
            ParticleSystem.Particle[] particles,
            List<Vector4> customRows,
            int particleCount)
        {
            Vector3[] bakedPositions = baked.vertices;
            Vector3[] bakedNormals = baked.normals;
            Color32[] bakedColors = baked.colors32;
            var bakedUv = new List<Vector4>[8];
            for (int channel = 0; channel < bakedUv.Length; ++channel)
            {
                bakedUv[channel] = new List<Vector4>();
                baked.GetUVs(channel, bakedUv[channel]);
            }
            int[] bakedIndexOffsets = new int[baked.subMeshCount];
            var result = new ParticleEvidence[particleCount];
            int vertexOffset = 0;
            int sourceIndexOffset = 0;
            for (int particleIndex = 0; particleIndex < particleCount; ++particleIndex)
            {
                int vertexCount = source.vertexCount;
                int sourceIndexCount = CountIndices(source);
                int meshIndex = particles[particleIndex].GetMeshIndex(system);
                // The generated M23 renderer has one source mesh.  Asking the
                // particle for its mesh index still records Unity's public
                // selection rather than silently assuming it.
                Require(meshIndex == 0, "M23 particle selected an unexpected mesh index");
                var row = new ParticleEvidence
                {
                    particleIndex = particleIndex,
                    meshIndex = meshIndex,
                    randomSeed = particles[particleIndex].randomSeed,
                    position = Float3Record.From(particles[particleIndex].position),
                    rotation3D = Float3Record.From(particles[particleIndex].rotation3D),
                    size3D = Float3Record.From(particles[particleIndex].GetCurrentSize3D(system)),
                    velocity = Float3Record.From(particles[particleIndex].velocity),
                    color = ColorRecord.From(particles[particleIndex].GetCurrentColor(system)),
                    custom1 = Float4Record.From(customRows[particleIndex]),
                    sourceVertexOffset = 0,
                    sourceVertexCount = vertexCount,
                    bakedVertexOffset = vertexOffset,
                    bakedVertexCount = vertexCount,
                    sourceIndexCount = sourceIndexCount,
                    bakedIndexOffset = sourceIndexOffset,
                    bakedIndexCount = sourceIndexCount,
                    bakedIndexRangeValid = true,
                    sourcePositionSha256 = HashVector3(source.vertices),
                    bakedPositionSegmentSha256 = HashVector3(Slice(bakedPositions, vertexOffset, vertexCount)),
                    bakedNormalSegmentSha256 = HashVector3(SliceRequired(bakedNormals, vertexOffset, vertexCount, "normal")),
                    bakedColorSegmentSha256 = HashColor32(SliceRequired(bakedColors, vertexOffset, vertexCount, "color")),
                    bakedUv0SegmentSha256 = HashVector4(SliceRequired(bakedUv[0], vertexOffset, vertexCount, "uv0")),
                    bakedUv1SegmentSha256 = HashVector4(SliceRequired(bakedUv[1], vertexOffset, vertexCount, "uv1")),
                };
                for (int channel = 0; channel < bakedUv.Length; ++channel)
                {
                    int mask = MatchReplicatedCustom1(
                        bakedUv[channel], vertexOffset, vertexCount, customRows[particleIndex]);
                    SetCustomMask(row, channel, mask);
                }
                for (int submesh = 0; submesh < baked.subMeshCount; ++submesh)
                {
                    int[] indices = baked.GetIndices(submesh);
                    int count = (int)source.GetIndexCount(submesh);
                    int expectedStart = bakedIndexOffsets[submesh];
                    int expectedEnd = expectedStart + count;
                    for (int index = expectedStart; index < expectedEnd; ++index)
                    {
                        Require(index < indices.Length,
                            "M23 baked index segment is truncated");
                        int value = indices[index];
                        if (value < vertexOffset || value >= vertexOffset + vertexCount)
                            row.bakedIndexRangeValid = false;
                    }
                    bakedIndexOffsets[submesh] += count;
                }
                Require(row.bakedIndexRangeValid,
                    "M23 baked index segment escaped its particle vertex range");
                result[particleIndex] = row;
                vertexOffset += vertexCount;
                sourceIndexOffset += sourceIndexCount;
            }
            return result;
        }

        private static void SetCustomMask(ParticleEvidence row, int channel, int mask)
        {
            switch (channel)
            {
                case 0: row.custom1Uv0ReplicationMask = mask; break;
                case 1: row.custom1Uv1ReplicationMask = mask; break;
                case 2: row.custom1Uv2ReplicationMask = mask; break;
                case 3: row.custom1Uv3ReplicationMask = mask; break;
                case 4: row.custom1Uv4ReplicationMask = mask; break;
                case 5: row.custom1Uv5ReplicationMask = mask; break;
                case 6: row.custom1Uv6ReplicationMask = mask; break;
                case 7: row.custom1Uv7ReplicationMask = mask; break;
            }
        }

        private static int MatchReplicatedCustom1(
            List<Vector4> values, int offset, int count, Vector4 expected)
        {
            if (values == null || values.Count < offset + count)
                return -1;
            int mask = 15;
            for (int index = offset; index < offset + count; ++index)
            {
                Vector4 actual = values[index];
                if (!BitEqual(actual.x, expected.x)) mask &= ~1;
                if (!BitEqual(actual.y, expected.y)) mask &= ~2;
                if (!BitEqual(actual.z, expected.z)) mask &= ~4;
                if (!BitEqual(actual.w, expected.w)) mask &= ~8;
            }
            return mask;
        }

        private static SourceMeshEvidence DescribeSourceMesh(Mesh mesh, long meshPathId)
        {
            Require(mesh != null && mesh.vertexCount > 0,
                "M23 source mesh is empty");
            return new SourceMeshEvidence
            {
                name = mesh.name,
                meshPathId = meshPathId,
                vertexCount = mesh.vertexCount,
                subMeshCount = mesh.subMeshCount,
                indexCount = CountIndices(mesh),
                subMeshIndexCounts = Enumerable.Range(0, mesh.subMeshCount)
                    .Select(index => (int)mesh.GetIndexCount(index)).ToArray(),
                positions = Digest("Position", mesh.vertices),
                normals = Digest("Normal", mesh.normals),
                tangents = Digest("Tangent", mesh.tangents),
                colors = Digest("Color", mesh.colors32),
                uv0 = DigestUv(mesh, 0),
                uv1 = DigestUv(mesh, 1),
                uv2 = DigestUv(mesh, 2),
                uv3 = DigestUv(mesh, 3),
                uv4 = DigestUv(mesh, 4),
                uv5 = DigestUv(mesh, 5),
                uv6 = DigestUv(mesh, 6),
                uv7 = DigestUv(mesh, 7),
                sourceBoundsSha256 = HashBounds(mesh.bounds),
            };
        }

        private static BakedMeshEvidence DescribeBakedMesh(Mesh mesh)
        {
            return new BakedMeshEvidence
            {
                vertexCount = mesh.vertexCount,
                subMeshCount = mesh.subMeshCount,
                indexCount = CountIndices(mesh),
                subMeshIndexCounts = Enumerable.Range(0, mesh.subMeshCount)
                    .Select(index => (int)mesh.GetIndexCount(index)).ToArray(),
                positions = Digest("Position", mesh.vertices),
                normals = Digest("Normal", mesh.normals),
                tangents = Digest("Tangent", mesh.tangents),
                colors = Digest("Color", mesh.colors32),
                uv0 = DigestUv(mesh, 0),
                uv1 = DigestUv(mesh, 1),
                uv2 = DigestUv(mesh, 2),
                uv3 = DigestUv(mesh, 3),
                uv4 = DigestUv(mesh, 4),
                uv5 = DigestUv(mesh, 5),
                uv6 = DigestUv(mesh, 6),
                uv7 = DigestUv(mesh, 7),
                boundsSha256 = HashBounds(mesh.bounds),
            };
        }

        private static ChannelEvidence Digest(string semantic, Vector3[] values)
        {
            return new ChannelEvidence
            {
                semantic = semantic,
                present = values != null && values.Length > 0,
                count = values == null ? 0 : values.Length,
                sha256 = HashVector3(values ?? Array.Empty<Vector3>()),
            };
        }

        private static ChannelEvidence Digest(string semantic, Vector4[] values)
        {
            return new ChannelEvidence
            {
                semantic = semantic,
                present = values != null && values.Length > 0,
                count = values == null ? 0 : values.Length,
                sha256 = HashVector4(values ?? Array.Empty<Vector4>()),
            };
        }

        private static ChannelEvidence Digest(string semantic, Color32[] values)
        {
            return new ChannelEvidence
            {
                semantic = semantic,
                present = values != null && values.Length > 0,
                count = values == null ? 0 : values.Length,
                sha256 = HashColor32(values ?? Array.Empty<Color32>()),
            };
        }

        private static ChannelEvidence DigestUv(Mesh mesh, int channel)
        {
            var values = new List<Vector4>();
            mesh.GetUVs(channel, values);
            return Digest("TEXCOORD" + channel, values.ToArray());
        }

        private static string HashParticleState(ParticleSystem.Particle[] values, ParticleSystem system)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(values.Length);
                foreach (ParticleSystem.Particle value in values)
                {
                    Write(writer, value.position);
                    Write(writer, value.rotation3D);
                    Write(writer, value.GetCurrentSize3D(system));
                    Write(writer, value.velocity);
                    writer.Write(value.randomSeed);
                    writer.Write(value.remainingLifetime);
                    writer.Write(value.startLifetime);
                    Color32 color = value.GetCurrentColor(system);
                    writer.Write(color.r); writer.Write(color.g);
                    writer.Write(color.b); writer.Write(color.a);
                    writer.Write(value.GetMeshIndex(system));
                }
                writer.Flush();
                return Hash(bytes.ToArray());
            }
        }

        private static string HashVector3(Vector3[] values)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(values.Length);
                foreach (Vector3 value in values) Write(writer, value);
                writer.Flush();
                return Hash(bytes.ToArray());
            }
        }

        private static string HashVector4(Vector4[] values)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(values.Length);
                foreach (Vector4 value in values) Write(writer, value);
                writer.Flush();
                return Hash(bytes.ToArray());
            }
        }

        private static string HashColor32(Color32[] values)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(values.Length);
                foreach (Color32 value in values)
                {
                    writer.Write(value.r); writer.Write(value.g);
                    writer.Write(value.b); writer.Write(value.a);
                }
                writer.Flush();
                return Hash(bytes.ToArray());
            }
        }

        private static string HashBounds(Bounds bounds)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                Write(writer, bounds.center); Write(writer, bounds.size);
                Write(writer, bounds.min); Write(writer, bounds.max);
                writer.Flush();
                return Hash(bytes.ToArray());
            }
        }

        private static Vector3[] SliceRequired(Vector3[] values, int offset, int count, string name)
        {
            Require(values != null && values.Length >= offset + count,
                "M23 baked " + name + " channel is incomplete");
            return Slice(values, offset, count);
        }

        private static Color32[] SliceRequired(Color32[] values, int offset, int count, string name)
        {
            Require(values != null && values.Length >= offset + count,
                "M23 baked " + name + " channel is incomplete");
            return values.Skip(offset).Take(count).ToArray();
        }

        private static Vector4[] SliceRequired(List<Vector4> values, int offset, int count, string name)
        {
            Require(values != null && values.Count >= offset + count,
                "M23 baked " + name + " channel is incomplete");
            return values.Skip(offset).Take(count).ToArray();
        }

        private static Vector3[] Slice(Vector3[] values, int offset, int count)
        {
            return values.Skip(offset).Take(count).ToArray();
        }

        private static int CountIndices(Mesh mesh)
        {
            int total = 0;
            for (int index = 0; index < mesh.subMeshCount; ++index)
                total += (int)mesh.GetIndexCount(index);
            return total;
        }

        private static Transform FindHierarchy(Transform root, string hierarchy)
        {
            string[] parts = hierarchy.Split('/');
            Require(parts.Length > 0 && parts[0] == root.name,
                "M23 hierarchy root drifted: " + hierarchy);
            Transform cursor = root;
            for (int index = 1; index < parts.Length && cursor != null; ++index)
                cursor = cursor.Find(parts[index]);
            return cursor;
        }

        private static bool BitEqual(float left, float right)
        {
            return BitConverter.SingleToInt32Bits(left) == BitConverter.SingleToInt32Bits(right);
        }

        private static void Write(BinaryWriter writer, Vector3 value)
        {
            writer.Write(value.x); writer.Write(value.y); writer.Write(value.z);
        }

        private static void Write(BinaryWriter writer, Vector4 value)
        {
            writer.Write(value.x); writer.Write(value.y);
            writer.Write(value.z); writer.Write(value.w);
        }

        private static string Hash(byte[] bytes)
        {
            using (SHA256 sha = SHA256.Create())
                return BitConverter.ToString(sha.ComputeHash(bytes)).Replace("-", string.Empty);
        }

        private static string ProjectAbsolute(string relative)
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..",
                relative.Replace('/', Path.DirectorySeparatorChar)));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
