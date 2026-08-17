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
        // BakeMesh and the source-side Matrix4x4.TRS candidate both execute
        // through Unity's binary32 transform path.  These are deliberately
        // tight absolute vector tolerances: a loose pixel-space tolerance
        // would allow a wrong particle ordering or rotation convention to
        // pass unnoticed.
        private const float PositionTransformTolerance = 0.00001f;
        private const float NormalTransformTolerance = 0.00001f;
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

            public static Float4Record From(Quaternion value)
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
            public string indicesSha256;
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
            public string indicesSha256;
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
            public Float3Record axisOfRotation;
            public ColorRecord color;
            public Float4Record custom1;
            public bool uses3DRotation;
            public float rotationDegrees;
            public int sourceVertexOffset;
            public int sourceVertexCount;
            public int bakedVertexOffset;
            public int bakedVertexCount;
            public int sourceIndexCount;
            public int bakedIndexOffset;
            public int bakedIndexCount;
            public bool bakedIndexRangeValid;
            // Range-only validation is insufficient: a renderer can keep all
            // indices inside the particle's vertex window while reordering
            // triangles.  Keep the exact source-submesh sequence and the
            // first bounded mismatch in the report so a future ABI bridge
            // cannot silently accept a different index topology.
            public bool bakedIndexSequenceValid;
            public string sourceIndexSequenceSha256;
            public string expectedIndexSequenceSha256;
            public string bakedIndexSequenceSha256;
            public int bakedIndexMismatchCount;
            public int bakedIndexFirstMismatchSubmesh = -1;
            public int bakedIndexFirstMismatchOffset = -1;
            public int bakedIndexFirstExpected = -1;
            public int bakedIndexFirstActual = -1;
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
        private sealed class TransformValidationEvidence
        {
            public string candidate =
                "Matrix4x4.TRS(particle.position, particle rotation, " +
                "particle.GetCurrentSize3D(system)), then system.localToWorld";
            public string rotationContract =
                "startRotation3D=true: Quaternion.Euler(rotation3D degrees); " +
                "false: Quaternion.AngleAxis(rotation degrees, axisOfRotation)";
            public float positionTolerance;
            public float normalTolerance;
            public int positionSampleCount;
            public int positionFailureCount;
            public float positionMaxError;
            public float positionMeanError;
            public int positionFirstFailureParticle = -1;
            public int positionFirstFailureVertex = -1;
            public Float3Record positionFirstExpected;
            public Float3Record positionFirstActual;
            public int normalSampleCount;
            public int normalFailureCount;
            public float normalMaxError;
            public float normalMeanError;
            public int normalFirstFailureParticle = -1;
            public int normalFirstFailureVertex = -1;
            public Float3Record normalFirstExpected;
            public Float3Record normalFirstActual;
            public Float3Record[] firstParticleSourceProbe;
            public Float3Record[] firstParticleBakedProbe;
            public bool localTrsClosed;
            public bool inverseTransposeNormalClosed;
        }

        [Serializable]
        private sealed class CaptureEvidence
        {
            public string label;
            public Float3Record cameraPosition;
            public Float4Record cameraRotation;
            public uint serializedRandomSeed;
            public int particleCount;
            public string beforeParticleStateSha256;
            public string afterParticleStateSha256;
            public string beforeCustom1Sha256;
            public string afterCustom1Sha256;
            public bool fixedSeedClosed;
            public bool bakeMeshMutationClosed;
            public BakedMeshEvidence bakedMesh;
        }

        // The managed arrays are intentionally kept outside CaptureEvidence:
        // they are inputs to the transform oracle, not part of the JSON schema.
        private sealed class CaptureSample
        {
            public CaptureEvidence evidence;
            public ParticleSystem.Particle[] particles;
            public List<Vector4> customRows;
            public Mesh bakedMesh;
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
            public bool indexSequenceClosed;
            public bool localTrsClosed;
            public bool inverseTransposeNormalClosed;
            public bool stateResetClosed;
            public bool bakeMeshMutationClosed;
            public bool repeatClosed;
            public bool cameraInvarianceAuthoredGateClosed;
            public bool cameraInvarianceExpected;
            public bool cameraInvarianceClosed;
            public string cameraInvarianceDiagnostic;
            public CaptureEvidence cameraA;
            public CaptureEvidence cameraB;
            public CaptureEvidence cameraARepeat;
            public int particleCount;
            public int bakedVertexCount;
            public int bakedIndexCount;
            public string particleStateSha256;
            public string custom1Sha256;
            public SourceMeshEvidence[] sourceMeshes;
            public BakedMeshEvidence bakedMesh;
            public TransformValidationEvidence transformValidation;
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
            public bool fixedTimeStep;
            public string simulationContract;
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
                fixedTimeStep = false,
                simulationContract =
                    "Simulate(effectLocalSeconds, withChildren:false, " +
                    "restart:true, fixedTimeStep:false), then Play(false)",
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
                        row.segmentMappingClosed && row.localTrsClosed &&
                        row.inverseTransposeNormalClosed && row.stateResetClosed &&
                        row.bakeMeshMutationClosed && row.repeatClosed &&
                        row.cameraInvarianceAuthoredGateClosed &&
                        (!row.cameraInvarianceExpected || row.cameraInvarianceClosed)),
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
            // randomSeed is serialized on the authored ParticleSystem.  Every
            // sample below resets to this exact value before exact-time
            // simulation; reusing a live system would hide random-stream or
            // BakeMesh mutation.
            uint serializedRandomSeed = system.randomSeed;
            CaptureSample cameraA = null;
            CaptureSample cameraB = null;
            CaptureSample cameraARepeat = null;
            try
            {
                ConfigureCamera(camera, new Vector3(0.0f, 0.0f, -10.0f),
                    Quaternion.identity);
                cameraA = CaptureRendererSample(
                    system, renderer, camera, effectLocalSeconds,
                    serializedRandomSeed, "cameraA", spec.hierarchy);
                ConfigureCamera(camera, new Vector3(3.25f, 1.75f, -7.5f),
                    Quaternion.Euler(17.0f, -21.0f, 8.0f));
                cameraB = CaptureRendererSample(
                    system, renderer, camera, effectLocalSeconds,
                    serializedRandomSeed, "cameraB", spec.hierarchy);
                ConfigureCamera(camera, new Vector3(0.0f, 0.0f, -10.0f),
                    Quaternion.identity);
                cameraARepeat = CaptureRendererSample(
                    system, renderer, camera, effectLocalSeconds,
                    serializedRandomSeed, "cameraARepeat", spec.hierarchy);

                SourceMeshEvidence source = DescribeSourceMesh(meshes[0], spec.meshPathId);
                int expectedVertices = 0;
                int expectedIndices = 0;
                foreach (ParticleSystem.Particle particle in cameraA.particles)
                {
                    int meshIndex = particle.GetMeshIndex(system);
                    Require(meshIndex >= 0 && meshIndex < meshes.Length &&
                        meshes[meshIndex] != null,
                        "M23 particle selected an invalid source mesh index: " +
                        meshIndex + " at " + spec.hierarchy);
                    expectedVertices += meshes[meshIndex].vertexCount;
                    expectedIndices += CountIndices(meshes[meshIndex]);
                }
                Require(cameraA.bakedMesh.subMeshCount == meshes[0].subMeshCount,
                    "M23 BakeMesh submesh count drifted at " + spec.hierarchy);
                Require(cameraA.bakedMesh.vertexCount == expectedVertices &&
                    CountIndices(cameraA.bakedMesh) == expectedIndices,
                    "M23 BakeMesh geometry count mismatch at " + spec.hierarchy +
                    ": actual=" + cameraA.bakedMesh.vertexCount + "/" + CountIndices(cameraA.bakedMesh) +
                    ", expected=" + expectedVertices + "/" + expectedIndices);
                bool stateResetClosed =
                    cameraA.evidence.beforeParticleStateSha256 ==
                        cameraB.evidence.beforeParticleStateSha256 &&
                    cameraA.evidence.beforeParticleStateSha256 ==
                        cameraARepeat.evidence.beforeParticleStateSha256 &&
                    cameraA.evidence.beforeCustom1Sha256 ==
                        cameraB.evidence.beforeCustom1Sha256 &&
                    cameraA.evidence.beforeCustom1Sha256 ==
                        cameraARepeat.evidence.beforeCustom1Sha256;
                bool bakeMeshMutationClosed =
                    cameraA.evidence.bakeMeshMutationClosed &&
                    cameraB.evidence.bakeMeshMutationClosed &&
                    cameraARepeat.evidence.bakeMeshMutationClosed;
                bool repeatClosed =
                    MeshDigestEqual(cameraA.evidence.bakedMesh,
                        cameraARepeat.evidence.bakedMesh) &&
                    stateResetClosed;
                bool cameraInvarianceClosed = MeshDigestEqual(
                    cameraA.evidence.bakedMesh, cameraB.evidence.bakedMesh);
                bool cameraInvarianceAuthoredGateClosed =
                    renderer.renderMode == ParticleSystemRenderMode.Mesh &&
                    renderer.alignment == ParticleSystemRenderSpace.Local &&
                    renderer.sortMode == ParticleSystemSortMode.None &&
                    renderer.cameraVelocityScale == 0.0f &&
                    renderer.velocityScale == 0.0f;
                bool cameraInvarianceExpected = cameraInvarianceAuthoredGateClosed;
                string cameraInvarianceDiagnostic = cameraInvarianceClosed
                    ? "cameraA and cameraB baked mesh digests are identical"
                    : "cameraA and cameraB baked mesh digests differ";
                Require(stateResetClosed,
                    "M23 exact-time reset state mismatch at " + spec.hierarchy);
                Require(bakeMeshMutationClosed,
                    "M23 BakeMesh mutated particle or Custom1 state at " + spec.hierarchy);
                Require(repeatClosed,
                    "M23 camera A repeat is not deterministic at " + spec.hierarchy);
                Require(cameraInvarianceAuthoredGateClosed,
                    "M23 camera-invariance authored gate drifted at " + spec.hierarchy +
                    ": renderMode=" + renderer.renderMode +
                    ", alignment=" + renderer.alignment +
                    ", sortMode=" + renderer.sortMode +
                    ", cameraVelocityScale=" + renderer.cameraVelocityScale +
                    ", velocityScale=" + renderer.velocityScale);
                Require(cameraInvarianceClosed,
                    "M23 authored mesh/local/unsorted BakeMesh is camera-dependent at " +
                    spec.hierarchy);
                TransformValidationEvidence transformValidation;
                ParticleEvidence[] particlesEvidence = BuildParticleEvidence(
                    system, meshes, cameraA.bakedMesh, cameraA.particles,
                    cameraA.customRows, cameraA.particles.Length,
                    main.startRotation3D, out transformValidation);
                var evidence = new RendererEvidence
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
                    particleStateClosed = stateResetClosed && bakeMeshMutationClosed,
                    custom1Closed = stateResetClosed && bakeMeshMutationClosed,
                    segmentMappingClosed = particlesEvidence.All(value =>
                        value.bakedIndexRangeValid && value.bakedIndexSequenceValid),
                    indexSequenceClosed = particlesEvidence.All(value =>
                        value.bakedIndexSequenceValid),
                    localTrsClosed = transformValidation.localTrsClosed,
                    inverseTransposeNormalClosed =
                        transformValidation.inverseTransposeNormalClosed,
                    stateResetClosed = stateResetClosed,
                    bakeMeshMutationClosed = bakeMeshMutationClosed,
                    repeatClosed = repeatClosed,
                    cameraInvarianceAuthoredGateClosed =
                        cameraInvarianceAuthoredGateClosed,
                    cameraInvarianceExpected = cameraInvarianceExpected,
                    cameraInvarianceClosed = cameraInvarianceClosed,
                    cameraInvarianceDiagnostic = cameraInvarianceDiagnostic,
                    cameraA = cameraA.evidence,
                    cameraB = cameraB.evidence,
                    cameraARepeat = cameraARepeat.evidence,
                    particleCount = cameraA.particles.Length,
                    bakedVertexCount = cameraA.bakedMesh.vertexCount,
                    bakedIndexCount = CountIndices(cameraA.bakedMesh),
                    particleStateSha256 = cameraA.evidence.beforeParticleStateSha256,
                    custom1Sha256 = cameraA.evidence.beforeCustom1Sha256,
                    sourceMeshes = new[] { source },
                    bakedMesh = cameraA.evidence.bakedMesh,
                    transformValidation = transformValidation,
                    particles = particlesEvidence,
                };
                Require(evidence.segmentMappingClosed,
                    "M23 baked index segment/range or exact sequence validation failed");
                return evidence;
            }
            finally
            {
                if (cameraA != null && cameraA.bakedMesh != null)
                    UnityEngine.Object.DestroyImmediate(cameraA.bakedMesh);
                if (cameraB != null && cameraB.bakedMesh != null)
                    UnityEngine.Object.DestroyImmediate(cameraB.bakedMesh);
                if (cameraARepeat != null && cameraARepeat.bakedMesh != null)
                    UnityEngine.Object.DestroyImmediate(cameraARepeat.bakedMesh);
            }
        }

        private sealed class ParticleStateSnapshot
        {
            public ParticleSystem.Particle[] particles;
            public List<Vector4> customRows;
            public string particleStateSha256;
            public string custom1Sha256;
        }

        private static CaptureSample CaptureRendererSample(
            ParticleSystem system,
            ParticleSystemRenderer renderer,
            Camera camera,
            float effectLocalSeconds,
            uint serializedRandomSeed,
            string label,
            string hierarchy)
        {
            ResetAndSimulate(system, effectLocalSeconds, serializedRandomSeed, hierarchy);
            ParticleStateSnapshot before = ReadParticleState(system, hierarchy);
            Mesh baked = new Mesh { name = "LiZhiyan_M23_SourceMesh_Oracle_" + label };
            try
            {
                renderer.BakeMesh(baked, camera,
                    ParticleSystemBakeMeshOptions.BakePosition |
                    ParticleSystemBakeMeshOptions.BakeRotationAndScale);
                ParticleStateSnapshot after = ReadParticleState(system, hierarchy);
                bool fixedSeedClosed = system.randomSeed == serializedRandomSeed;
                bool bakeMeshMutationClosed =
                    before.particleStateSha256 == after.particleStateSha256 &&
                    before.custom1Sha256 == after.custom1Sha256 &&
                    before.particles.Length == after.particles.Length &&
                    before.customRows.Count == after.customRows.Count;
                var evidence = new CaptureEvidence
                {
                    label = label,
                    cameraPosition = Float3Record.From(camera.transform.position),
                    cameraRotation = Float4Record.From(camera.transform.rotation),
                    serializedRandomSeed = serializedRandomSeed,
                    particleCount = before.particles.Length,
                    beforeParticleStateSha256 = before.particleStateSha256,
                    afterParticleStateSha256 = after.particleStateSha256,
                    beforeCustom1Sha256 = before.custom1Sha256,
                    afterCustom1Sha256 = after.custom1Sha256,
                    fixedSeedClosed = fixedSeedClosed,
                    bakeMeshMutationClosed = bakeMeshMutationClosed,
                    bakedMesh = DescribeBakedMesh(baked),
                };
                Require(fixedSeedClosed,
                    "M23 ParticleSystem randomSeed mutated during " + label +
                    " at " + hierarchy);
                Require(bakeMeshMutationClosed,
                    "M23 BakeMesh mutated particle or Custom1 state during " +
                    label + " at " + hierarchy);
                return new CaptureSample
                {
                    evidence = evidence,
                    particles = before.particles,
                    customRows = before.customRows,
                    bakedMesh = baked,
                };
            }
            catch
            {
                UnityEngine.Object.DestroyImmediate(baked);
                throw;
            }
        }

        private static void ResetAndSimulate(
            ParticleSystem system,
            float effectLocalSeconds,
            uint serializedRandomSeed,
            string hierarchy)
        {
            system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            system.Clear(true);
            system.randomSeed = serializedRandomSeed;
            Require(system.randomSeed == serializedRandomSeed,
                "M23 could not restore serialized randomSeed at " + hierarchy);
            system.Simulate(effectLocalSeconds, false, true, false);
            // Match the maintained actor-capture submission boundary: Play
            // publishes the simulated state to the renderer without advancing
            // time in this batchmode call.
            system.Play(false);
        }

        private static ParticleStateSnapshot ReadParticleState(
            ParticleSystem system,
            string hierarchy)
        {
            ParticleSystem.MainModule main = system.main;
            var particles = new ParticleSystem.Particle[
                Mathf.Max(system.particleCount, main.maxParticles)];
            int particleCount = system.GetParticles(particles);
            Array.Resize(ref particles, particleCount);
            var customRows = new List<Vector4>(particleCount);
            int customCount = system.GetCustomParticleData(
                customRows, ParticleSystemCustomData.Custom1);
            Require(customCount == particleCount && customRows.Count == particleCount,
                "M23 Custom1 count does not match particle count at " + hierarchy);
            return new ParticleStateSnapshot
            {
                particles = particles,
                customRows = customRows,
                particleStateSha256 = HashParticleState(particles, system),
                custom1Sha256 = HashVector4(customRows.ToArray()),
            };
        }

        private static void ConfigureCamera(
            Camera camera,
            Vector3 position,
            Quaternion rotation)
        {
            camera.transform.SetPositionAndRotation(position, rotation);
            camera.enabled = false;
        }

        private static bool MeshDigestEqual(
            BakedMeshEvidence left,
            BakedMeshEvidence right)
        {
            if (left == null || right == null ||
                left.vertexCount != right.vertexCount ||
                left.subMeshCount != right.subMeshCount ||
                left.indexCount != right.indexCount ||
                !SequenceEqual(left.subMeshIndexCounts, right.subMeshIndexCounts) ||
                left.indicesSha256 != right.indicesSha256 ||
                left.boundsSha256 != right.boundsSha256)
                return false;
            return ChannelDigestEqual(left.positions, right.positions) &&
                ChannelDigestEqual(left.normals, right.normals) &&
                ChannelDigestEqual(left.tangents, right.tangents) &&
                ChannelDigestEqual(left.colors, right.colors) &&
                ChannelDigestEqual(left.uv0, right.uv0) &&
                ChannelDigestEqual(left.uv1, right.uv1) &&
                ChannelDigestEqual(left.uv2, right.uv2) &&
                ChannelDigestEqual(left.uv3, right.uv3) &&
                ChannelDigestEqual(left.uv4, right.uv4) &&
                ChannelDigestEqual(left.uv5, right.uv5) &&
                ChannelDigestEqual(left.uv6, right.uv6) &&
                ChannelDigestEqual(left.uv7, right.uv7);
        }

        private static bool ChannelDigestEqual(
            ChannelEvidence left,
            ChannelEvidence right)
        {
            return left != null && right != null &&
                left.semantic == right.semantic &&
                left.present == right.present &&
                left.count == right.count &&
                left.sha256 == right.sha256;
        }

        private static bool SequenceEqual(int[] left, int[] right)
        {
            if (left == null || right == null || left.Length != right.Length)
                return left == right;
            for (int index = 0; index < left.Length; ++index)
                if (left[index] != right[index])
                    return false;
            return true;
        }

        private static ParticleEvidence[] BuildParticleEvidence(
            ParticleSystem system,
            Mesh[] sourceMeshes,
            Mesh baked,
            ParticleSystem.Particle[] particles,
            List<Vector4> customRows,
            int particleCount,
            bool startRotation3D,
            out TransformValidationEvidence transformValidation)
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
            Require(bakedNormals != null && bakedNormals.Length == baked.vertexCount,
                "M23 baked Normal channel is incomplete");
            var validation = new TransformValidationEvidence
            {
                positionTolerance = PositionTransformTolerance,
                normalTolerance = NormalTransformTolerance,
                firstParticleBakedProbe = bakedPositions.Take(8)
                    .Select(Float3Record.From).ToArray(),
            };
            double positionErrorSum = 0.0;
            double normalErrorSum = 0.0;
            var result = new ParticleEvidence[particleCount];
            int vertexOffset = 0;
            int sourceIndexOffset = 0;
            for (int particleIndex = 0; particleIndex < particleCount; ++particleIndex)
            {
                int meshIndex = particles[particleIndex].GetMeshIndex(system);
                Require(meshIndex >= 0 && meshIndex < sourceMeshes.Length &&
                    sourceMeshes[meshIndex] != null,
                    "M23 particle selected an invalid source mesh index: " +
                    meshIndex + " at particle " + particleIndex);
                Mesh source = sourceMeshes[meshIndex];
                Require(source.subMeshCount == baked.subMeshCount,
                    "M23 selected source mesh submesh count drifted at particle " +
                    particleIndex);
                Vector3[] sourcePositions = source.vertices;
                Vector3[] sourceNormals = source.normals;
                Require(sourcePositions != null && sourcePositions.Length == source.vertexCount,
                    "M23 source Position channel is incomplete at mesh " + meshIndex);
                Require(sourceNormals != null && sourceNormals.Length == source.vertexCount,
                    "M23 source Normal channel is incomplete at mesh " + meshIndex);
                if (particleIndex == 0)
                    validation.firstParticleSourceProbe = sourcePositions.Take(8)
                        .Select(Float3Record.From).ToArray();
                int vertexCount = source.vertexCount;
                int sourceIndexCount = CountIndices(source);
                ParticleSystem.Particle particle = particles[particleIndex];
                Vector3 particleSize = particle.GetCurrentSize3D(system);
                Quaternion particleRotation = BuildParticleRotation(
                    particle, startRotation3D);
                Matrix4x4 particleTrs = Matrix4x4.TRS(
                    particle.position, particleRotation, particleSize);
                Matrix4x4 sourceToBaked =
                    system.transform.localToWorldMatrix * particleTrs;
                Matrix4x4 inverseTranspose = sourceToBaked.inverse.transpose;
                var row = new ParticleEvidence
                {
                    particleIndex = particleIndex,
                    meshIndex = meshIndex,
                    randomSeed = particles[particleIndex].randomSeed,
                    position = Float3Record.From(particle.position),
                    rotation3D = Float3Record.From(particle.rotation3D),
                    size3D = Float3Record.From(particleSize),
                    velocity = Float3Record.From(particle.velocity),
                    axisOfRotation = Float3Record.From(particle.axisOfRotation),
                    color = ColorRecord.From(particle.GetCurrentColor(system)),
                    custom1 = Float4Record.From(customRows[particleIndex]),
                    uses3DRotation = startRotation3D,
                    rotationDegrees = startRotation3D ? 0.0f : particle.rotation,
                    sourceVertexOffset = 0,
                    sourceVertexCount = vertexCount,
                    bakedVertexOffset = vertexOffset,
                    bakedVertexCount = vertexCount,
                    sourceIndexCount = sourceIndexCount,
                    bakedIndexOffset = sourceIndexOffset,
                    bakedIndexCount = sourceIndexCount,
                    bakedIndexRangeValid = true,
                    bakedIndexSequenceValid = false,
                    sourcePositionSha256 = HashVector3(source.vertices),
                    bakedPositionSegmentSha256 = HashVector3(Slice(bakedPositions, vertexOffset, vertexCount)),
                    bakedNormalSegmentSha256 = HashVector3(SliceRequired(bakedNormals, vertexOffset, vertexCount, "normal")),
                    bakedColorSegmentSha256 = HashColor32(SliceRequired(bakedColors, vertexOffset, vertexCount, "color")),
                    bakedUv0SegmentSha256 = HashVector4(SliceRequired(bakedUv[0], vertexOffset, vertexCount, "uv0")),
                    bakedUv1SegmentSha256 = HashVector4(SliceRequired(bakedUv[1], vertexOffset, vertexCount, "uv1")),
                };
                for (int vertex = 0; vertex < vertexCount; ++vertex)
                {
                    Vector3 expectedPosition = sourceToBaked.MultiplyPoint3x4(
                        sourcePositions[vertex]);
                    Vector3 actualPosition = bakedPositions[vertexOffset + vertex];
                    float positionError = Vector3.Distance(
                        expectedPosition, actualPosition);
                    validation.positionSampleCount++;
                    positionErrorSum += positionError;
                    validation.positionMaxError = Mathf.Max(
                        validation.positionMaxError, positionError);
                    if (positionError > PositionTransformTolerance)
                    {
                        validation.positionFailureCount++;
                        if (validation.positionFirstFailureParticle < 0)
                        {
                            validation.positionFirstFailureParticle = particleIndex;
                            validation.positionFirstFailureVertex = vertex;
                            validation.positionFirstExpected =
                                Float3Record.From(expectedPosition);
                            validation.positionFirstActual =
                                Float3Record.From(actualPosition);
                        }
                    }

                    Vector3 sourceNormal = sourceNormals[vertex];
                    Require(sourceNormal.sqrMagnitude > 0.0f,
                        "M23 source Normal contains a zero vector at vertex " + vertex);
                    Vector3 expectedNormal = inverseTranspose.MultiplyVector(
                        sourceNormal).normalized;
                    Vector3 actualNormal = bakedNormals[vertexOffset + vertex];
                    Require(actualNormal.sqrMagnitude > 0.0f,
                        "M23 baked Normal contains a zero vector at particle " +
                        particleIndex + ", vertex " + vertex);
                    actualNormal.Normalize();
                    float normalError = Vector3.Distance(expectedNormal, actualNormal);
                    validation.normalSampleCount++;
                    normalErrorSum += normalError;
                    validation.normalMaxError = Mathf.Max(
                        validation.normalMaxError, normalError);
                    if (normalError > NormalTransformTolerance)
                    {
                        validation.normalFailureCount++;
                        if (validation.normalFirstFailureParticle < 0)
                        {
                            validation.normalFirstFailureParticle = particleIndex;
                            validation.normalFirstFailureVertex = vertex;
                            validation.normalFirstExpected =
                                Float3Record.From(expectedNormal);
                            validation.normalFirstActual =
                                Float3Record.From(actualNormal);
                        }
                    }
                }
                for (int channel = 0; channel < bakedUv.Length; ++channel)
                {
                    int mask = MatchReplicatedCustom1(
                        bakedUv[channel], vertexOffset, vertexCount, customRows[particleIndex]);
                    SetCustomMask(row, channel, mask);
                }
                ValidateParticleIndexSequence(
                    source, baked, bakedIndexOffsets, vertexOffset, row);
                Require(row.bakedIndexRangeValid && row.bakedIndexSequenceValid,
                    "M23 baked index segment escaped range or exact source sequence");
                result[particleIndex] = row;
                vertexOffset += vertexCount;
                sourceIndexOffset += sourceIndexCount;
            }
            for (int submesh = 0; submesh < baked.subMeshCount; ++submesh)
                Require(bakedIndexOffsets[submesh] == (int)baked.GetIndexCount(submesh),
                    "M23 baked index stream contains an unassigned trailing segment at submesh " +
                    submesh);
            validation.positionMeanError = validation.positionSampleCount == 0
                ? 0.0f
                : (float)(positionErrorSum / validation.positionSampleCount);
            validation.normalMeanError = validation.normalSampleCount == 0
                ? 0.0f
                : (float)(normalErrorSum / validation.normalSampleCount);
            validation.localTrsClosed = validation.positionFailureCount == 0;
            validation.inverseTransposeNormalClosed =
                validation.normalFailureCount == 0;
            transformValidation = validation;
            return result;
        }

        private static void ValidateParticleIndexSequence(
            Mesh source,
            Mesh baked,
            int[] bakedIndexOffsets,
            int bakedVertexOffset,
            ParticleEvidence row)
        {
            var sourceSegments = new List<int[]>(source.subMeshCount);
            var expectedSegments = new List<int[]>(source.subMeshCount);
            var actualSegments = new List<int[]>(source.subMeshCount);
            int mismatchCount = 0;
            int firstMismatchSubmesh = -1;
            int firstMismatchOffset = -1;
            int firstExpected = -1;
            int firstActual = -1;
            bool rangeValid = true;
            bool sequenceValid = true;

            for (int submesh = 0; submesh < source.subMeshCount; ++submesh)
            {
                int[] sourceIndices = source.GetIndices(submesh);
                int[] bakedIndices = baked.GetIndices(submesh);
                int bakedStart = bakedIndexOffsets[submesh];
                sourceSegments.Add(sourceIndices);

                var expected = new int[sourceIndices.Length];
                var actual = new List<int>(sourceIndices.Length);
                bool complete = bakedStart >= 0 &&
                    bakedStart + sourceIndices.Length <= bakedIndices.Length;
                if (!complete)
                {
                    sequenceValid = false;
                    rangeValid = false;
                }

                for (int offset = 0; offset < sourceIndices.Length; ++offset)
                {
                    int expectedIndex = sourceIndices[offset] + bakedVertexOffset;
                    expected[offset] = expectedIndex;
                    int absoluteIndex = bakedStart + offset;
                    int actualIndex = complete ? bakedIndices[absoluteIndex] : -1;
                    actual.Add(actualIndex);
                    if (actualIndex < bakedVertexOffset ||
                        actualIndex >= bakedVertexOffset + row.bakedVertexCount)
                        rangeValid = false;
                    if (!complete || actualIndex != expectedIndex)
                    {
                        sequenceValid = false;
                        mismatchCount++;
                        if (firstMismatchSubmesh < 0)
                        {
                            firstMismatchSubmesh = submesh;
                            firstMismatchOffset = offset;
                            firstExpected = expectedIndex;
                            firstActual = actualIndex;
                        }
                    }
                }
                expectedSegments.Add(expected);
                actualSegments.Add(actual.ToArray());
                bakedIndexOffsets[submesh] += sourceIndices.Length;
            }

            row.bakedIndexRangeValid = rangeValid;
            row.bakedIndexSequenceValid = sequenceValid && mismatchCount == 0;
            row.sourceIndexSequenceSha256 = HashIndexSubmeshes(sourceSegments);
            row.expectedIndexSequenceSha256 = HashIndexSubmeshes(expectedSegments);
            row.bakedIndexSequenceSha256 = HashIndexSubmeshes(actualSegments);
            row.bakedIndexMismatchCount = mismatchCount;
            row.bakedIndexFirstMismatchSubmesh = firstMismatchSubmesh;
            row.bakedIndexFirstMismatchOffset = firstMismatchOffset;
            row.bakedIndexFirstExpected = firstExpected;
            row.bakedIndexFirstActual = firstActual;
        }

        private static Quaternion BuildParticleRotation(
            ParticleSystem.Particle particle,
            bool startRotation3D)
        {
            if (startRotation3D)
                return Quaternion.Euler(particle.rotation3D);
            Require(particle.axisOfRotation.sqrMagnitude > 0.0f,
                "M23 scalar particle rotation has no axisOfRotation");
            // Particle.rotation is exposed in degrees by Unity 2022.3, as is
            // rotation3D. Quaternion.AngleAxis uses the same unit.
            return Quaternion.AngleAxis(
                particle.rotation, particle.axisOfRotation.normalized);
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
                indicesSha256 = HashIndices(mesh),
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
                indicesSha256 = HashIndices(mesh),
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
                    writer.Write(value.rotation);
                    Write(writer, value.axisOfRotation);
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
                writer.Write(system.main.startRotation3D);
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

        private static string HashIndexSubmeshes(IList<int[]> segments)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(segments == null ? 0 : segments.Count);
                if (segments != null)
                {
                    foreach (int[] segment in segments)
                    {
                        int[] values = segment ?? Array.Empty<int>();
                        writer.Write(values.Length);
                        foreach (int value in values)
                            writer.Write(value);
                    }
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

        private static string HashIndices(Mesh mesh)
        {
            using (var bytes = new MemoryStream())
            using (var writer = new BinaryWriter(bytes))
            {
                writer.Write(mesh.subMeshCount);
                for (int submesh = 0; submesh < mesh.subMeshCount; ++submesh)
                {
                    int[] indices = mesh.GetIndices(submesh);
                    writer.Write(indices.Length);
                    foreach (int value in indices)
                        writer.Write(value);
                }
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
