using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Resolves the recovered Endminf BeyondDynamicBone owner topology and
    /// runs the non-solver lifecycle probe.  This is intentionally separate
    /// from any future PlayerLoop contract/recovery helper: it does not
    /// register a PlayerLoop callback, run a solver, or alter capture fidelity.
    /// </summary>
    public static class EndfieldSecondaryDynamicsLifecycleProbeEditor
    {
        private const string ContractAssetPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_owner_recovery.json";
        private const string EndminfPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string OutputRelativePath =
            "scratch/character_recovery/secondary_dynamics_probe/endminf_lifecycle_topology.json";

        [Serializable]
        private sealed class ActorContract
        {
            public string character_id = "";
            public ClothContract[] cloths = Array.Empty<ClothContract>();
            public OverviewControllerContract overview_controller =
                new OverviewControllerContract();
        }

        [Serializable]
        private sealed class OverviewControllerContract
        {
            public string status = "";
            public float magica_cloth_weight;
        }

        [Serializable]
        private sealed class ClothContract
        {
            public string type = "";
            public string game_object_path = "";
            public int enabled;
            public RootContract[] root_bones = Array.Empty<RootContract>();
            public ColliderContract[] colliders = Array.Empty<ColliderContract>();
            public ClothParametersContract parameters = new ClothParametersContract();
        }

        [Serializable]
        private sealed class RootContract
        {
            public string path = "";
        }

        [Serializable]
        private sealed class ColliderContract
        {
            public string type = "";
            public string game_object_path = "";
        }

        [Serializable]
        private sealed class ClothParametersContract
        {
            public float simulate_weight = 1.0f;
            public float blend_weight = 1.0f;
        }

        [Serializable]
        private sealed class ProbeReport
        {
            public string schema = "endfield.charinfo.secondary-dynamics-lifecycle-probe.v1";
            public string actor = "endminf";
            public string prefab = EndminfPrefabPath;
            public string source_contract = ContractAssetPath;
            public string scope =
                "Serialized topology and lifecycle ordering only; this report is " +
                "not retail solver evidence.";
            public bool topology_resolved;
            public bool state_arrays_allocated;
            public int owner_count;
            public int root_count;
            public int collider_count;
            public int tracked_transform_count;
            public bool owner_activity_observed;
            public bool all_owners_active_self;
            public string component_binding_status =
                "serialized_contract_only_missing_beyonddynamicbone_runtime_type";
            public string[] owners = Array.Empty<string>();
            public string[] unresolved_paths = Array.Empty<string>();
            public LifecycleSummary active_scenario;
            public LifecycleSummary component_disabled_scenario;
            public LifecycleSummary global_weight_gated_scenario;
            public bool secondary_dynamics_verified = false;
            public string render_fidelity_status =
                "incomplete_missing_retail_secondary_dynamics_solver";
            public string limitation =
                "No BeyondDynamicBone/Magica/Burst solver is executed; no PlayerLoop " +
                "callback is registered; secondary_dynamics_verified remains false.";
        }

        [Serializable]
        private sealed class LifecycleSummary
        {
            public string scenario = "";
            public bool configured;
            public bool movement_disabled;
            public bool gate_open;
            public bool state_allocated;
            public bool callback_invoked;
            public bool writeback_invoked;
            public bool ordering_verified;
            public bool transforms_unchanged;
            public bool passed;
            public int tracked_transform_count;
            public int root_count;
            public int collider_count;
            public string gate_reason = "";
            public string[] events = Array.Empty<string>();
            public string limitation = "";

            public LifecycleSummary(EndfieldSecondaryDynamicsLifecycleProbe.LifecycleAudit source)
            {
                scenario = source.scenario;
                configured = source.configured;
                movement_disabled = source.movement_disabled;
                gate_open = source.gate_open;
                state_allocated = source.state_allocated;
                callback_invoked = source.callback_invoked;
                writeback_invoked = source.writeback_invoked;
                ordering_verified = source.ordering_verified;
                transforms_unchanged = source.transforms_unchanged;
                passed = source.passed;
                tracked_transform_count = source.tracked_transform_count;
                root_count = source.root_count;
                collider_count = source.collider_count;
                gate_reason = source.gate_reason;
                events = source.events ?? Array.Empty<string>();
                limitation = source.limitation;
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Probe Endminf Secondary Dynamics Topology")]
        public static void ProbeEndminf()
        {
            string outputPath = GetOutputPath();
            ProbeReport report = null;
            try
            {
                report = ProbeEndminfInternal();
                Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
                File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
                if (!report.topology_resolved ||
                    report.active_scenario == null ||
                    !report.active_scenario.passed ||
                    !report.active_scenario.gate_open ||
                    !report.active_scenario.callback_invoked ||
                    !report.active_scenario.writeback_invoked ||
                    report.component_disabled_scenario == null ||
                    !report.component_disabled_scenario.passed ||
                    report.component_disabled_scenario.gate_open ||
                    report.component_disabled_scenario.gate_reason != "component_disabled" ||
                    report.global_weight_gated_scenario == null ||
                    !report.global_weight_gated_scenario.passed ||
                    report.global_weight_gated_scenario.gate_open ||
                    report.global_weight_gated_scenario.gate_reason != "global_weight_zero")
                {
                    throw new InvalidOperationException(
                        "Secondary dynamics lifecycle probe did not pass all gates; " +
                        "see " + outputPath);
                }
                Debug.Log(
                    "Endminf secondary dynamics topology/lifecycle probe passed " +
                    "(non-solver; secondary_dynamics_verified=false): " + outputPath);
            }
            catch (Exception exception)
            {
                if (report != null)
                {
                    Directory.CreateDirectory(Path.GetDirectoryName(outputPath) ?? ".");
                    File.WriteAllText(outputPath, JsonUtility.ToJson(report, true));
                }
                Debug.LogException(exception);
                throw;
            }
        }

        /// <summary>Batch-mode wrapper used by focused validation commands.</summary>
        public static void ProbeEndminfBatch()
        {
            try
            {
                ProbeEndminf();
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Validate Secondary Dynamics Lifecycle Probe")]
        public static void ValidateSelfTest()
        {
            GameObject root = new GameObject("SecondaryDynamicsProbeTestRoot");
            GameObject child = new GameObject("Root");
            GameObject grandchild = new GameObject("MC_Ribbon2");
            child.transform.SetParent(root.transform, false);
            grandchild.transform.SetParent(child.transform, false);
            var nodes = new List<EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode>
            {
                new EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode
                {
                    path = "Root",
                    role = "root",
                    owner = "MC_Ribbon2",
                    componentType = "BeyondDynamicBone.BeyondBoneCloth",
                    transform = child.transform
                },
                new EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode
                {
                    path = "Root/MC_Ribbon2",
                    role = "collider",
                    owner = "MC_Ribbon2",
                    componentType = "BeyondDynamicBone.BeyondBoneCapsuleCollider",
                    transform = grandchild.transform
                }
            };

            try
            {
                var probe = root.AddComponent<EndfieldSecondaryDynamicsLifecycleProbe>();
                probe.Configure(nodes);
                probe.SetLifecycleGates(true, true, false,
                    EndfieldSecondaryDynamicsLifecycleProbe.EndminfSerializedOverviewWeight,
                    1.0f, 1.0f);
                EndfieldSecondaryDynamicsLifecycleProbe.LifecycleAudit active =
                    probe.RunLifecycleAudit("self_test_active");
                Require(active.passed, "active lifecycle self-test failed");
                Require(active.events.SequenceEqual(new[] { "read", "callback", "writeback" }),
                    "active lifecycle self-test ordering failed");

                probe.SetLifecycleGates(false, true, false,
                    EndfieldSecondaryDynamicsLifecycleProbe.EndminfSerializedOverviewWeight,
                    1.0f, 1.0f);
                EndfieldSecondaryDynamicsLifecycleProbe.LifecycleAudit disabled =
                    probe.RunLifecycleAudit("self_test_component_disabled");
                Require(disabled.passed, "disabled lifecycle self-test failed");
                Require(!disabled.callback_invoked && !disabled.writeback_invoked,
                    "disabled lifecycle self-test unexpectedly invoked callback/writeback");

                probe.SetLifecycleGates(true, true, false, 0.0f, 1.0f, 1.0f);
                EndfieldSecondaryDynamicsLifecycleProbe.LifecycleAudit weighted =
                    probe.RunLifecycleAudit("self_test_weight_gated");
                Require(weighted.passed, "weight lifecycle self-test failed");
                Require(weighted.gate_reason == "global_weight_zero",
                    "weight lifecycle self-test gate reason failed");
                probe.SetLifecycleGates(true, true, false, float.NaN, 1.0f, 1.0f);
                EndfieldSecondaryDynamicsLifecycleProbe.LifecycleAudit nonFinite =
                    probe.RunLifecycleAudit("self_test_non_finite_weight");
                Require(nonFinite.passed && !nonFinite.gate_open &&
                        nonFinite.gate_reason == "non_finite_weight",
                    "non-finite weight lifecycle self-test failed");
                Require(!probe.SecondaryDynamicsVerified &&
                        !EndfieldSecondaryDynamicsLifecycleProbe.IsRetailSolver,
                    "self-test attempted to claim retail solver evidence");
                Debug.Log("Secondary dynamics lifecycle self-test passed (non-solver).");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
            }
        }

        public static void ValidateSelfTestBatch()
        {
            try
            {
                ValidateSelfTest();
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static ProbeReport ProbeEndminfInternal()
        {
            TextAsset contractAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(ContractAssetPath);
            if (contractAsset == null)
                throw new FileNotFoundException("Secondary dynamics contract is missing", ContractAssetPath);

            string actorJson = ExtractNamedObject(contractAsset.text, "endminf");
            ActorContract actor = JsonUtility.FromJson<ActorContract>(actorJson);
            if (actor == null || actor.cloths == null || actor.cloths.Length == 0)
                throw new InvalidOperationException("Endminf secondary dynamics contract has no cloth entries.");

            GameObject prefabRoot = PrefabUtility.LoadPrefabContents(EndminfPrefabPath);
            if (prefabRoot == null)
                throw new InvalidOperationException("Could not load Endminf prefab contents.");

            try
            {
                return ProbePrefab(actor, prefabRoot);
            }
            finally
            {
                PrefabUtility.UnloadPrefabContents(prefabRoot);
            }
        }

        private static ProbeReport ProbePrefab(ActorContract actor, GameObject prefabRoot)
        {
            var nodes = new List<EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode>();
            var unresolved = new List<string>();
            var owners = new List<string>();
            var resolvedOwners = new List<Transform>();
            Transform actorTransform = prefabRoot.transform;

            foreach (ClothContract cloth in actor.cloths)
            {
                if (cloth == null)
                    continue;
                Transform owner = ResolveOwner(actorTransform, cloth.game_object_path);
                if (owner == null)
                {
                    unresolved.Add("owner:" + cloth.game_object_path);
                }
                else
                {
                    if (!owners.Contains(cloth.game_object_path))
                        owners.Add(cloth.game_object_path);
                    if (!resolvedOwners.Contains(owner))
                        resolvedOwners.Add(owner);
                }

                bool sourceEnabled = cloth.enabled != 0;
                foreach (RootContract root in cloth.root_bones ?? Array.Empty<RootContract>())
                {
                    if (root == null || string.IsNullOrEmpty(root.path))
                        continue;
                    Transform resolved = ResolvePath(actorTransform, root.path);
                    if (resolved == null)
                    {
                        unresolved.Add("root:" + root.path);
                        continue;
                    }
                    AddNode(nodes, root.path, "root", cloth, resolved);
                }

                foreach (ColliderContract collider in cloth.colliders ?? Array.Empty<ColliderContract>())
                {
                    if (collider == null || string.IsNullOrEmpty(collider.game_object_path))
                        continue;
                    Transform resolved = ResolvePath(actorTransform, collider.game_object_path);
                    if (resolved == null)
                    {
                        unresolved.Add("collider:" + collider.game_object_path);
                        continue;
                    }
                    AddNode(nodes, collider.game_object_path, "collider", cloth, resolved,
                        collider.type);
                }
            }

            var report = new ProbeReport
            {
                topology_resolved = unresolved.Count == 0 && owners.Count > 0 && nodes.Count > 0,
                owner_count = owners.Count,
                root_count = nodes.Count(node => node.role == "root"),
                collider_count = nodes.Count(node => node.role == "collider"),
                tracked_transform_count = nodes.Count,
                owner_activity_observed = resolvedOwners.Count == owners.Count,
                all_owners_active_self = resolvedOwners.All(owner => owner.gameObject.activeSelf),
                owners = owners.ToArray(),
                unresolved_paths = unresolved.ToArray(),
                secondary_dynamics_verified = false
            };

            if (!report.topology_resolved)
                return report;

            EndfieldSecondaryDynamicsLifecycleProbe probe =
                prefabRoot.AddComponent<EndfieldSecondaryDynamicsLifecycleProbe>();
            try
            {
                probe.Configure(nodes);
                report.state_arrays_allocated = probe.PreviousStateCount == nodes.Count &&
                                                probe.CurrentStateCount == nodes.Count;

                float globalWeight = actor.overview_controller == null
                    ? EndfieldSecondaryDynamicsLifecycleProbe.EndminfSerializedOverviewWeight
                    : actor.overview_controller.magica_cloth_weight;
                float simulateWeight = actor.cloths
                    .Where(cloth => cloth != null)
                    .Select(cloth => cloth.parameters == null ? 1.0f : cloth.parameters.simulate_weight)
                    .DefaultIfEmpty(1.0f)
                    .Min();
                float blendWeight = actor.cloths
                    .Where(cloth => cloth != null)
                    .Select(cloth => cloth.parameters == null ? 1.0f : cloth.parameters.blend_weight)
                    .DefaultIfEmpty(1.0f)
                    .Min();
                bool sourceEnabled = actor.cloths.All(cloth => cloth == null || cloth.enabled != 0);

                bool componentEnabled = sourceEnabled;
                bool ownerActive = report.owner_activity_observed && report.all_owners_active_self;
                probe.SetLifecycleGates(componentEnabled, ownerActive, false,
                    globalWeight, simulateWeight, blendWeight,
                    sourceEnabled);
                report.active_scenario = new LifecycleSummary(
                    probe.RunLifecycleAudit("endminf_enabled_weighted_movement_disabled"));

                probe.SetLifecycleGates(false, true, false, globalWeight, simulateWeight, blendWeight,
                    sourceEnabled);
                report.component_disabled_scenario = new LifecycleSummary(
                    probe.RunLifecycleAudit("endminf_component_disabled"));

                probe.SetLifecycleGates(true, true, false,
                    0.0f,
                    simulateWeight, blendWeight, sourceEnabled);
                report.global_weight_gated_scenario = new LifecycleSummary(
                    probe.RunLifecycleAudit("endminf_global_weight_gated"));
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(probe);
            }
            return report;
        }

        private static void AddNode(
            List<EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode> nodes,
            string path,
            string role,
            ClothContract cloth,
            Transform resolved,
            string componentType = "")
        {
            string key = role + "|" + path;
            if (nodes.Any(node => node.role + "|" + node.path == key))
                return;
            nodes.Add(new EndfieldSecondaryDynamicsLifecycleProbe.TopologyNode
            {
                path = path,
                role = role,
                owner = cloth.game_object_path,
                componentType = componentType.Length == 0 ? cloth.type : componentType,
                transform = resolved
            });
        }

        private static Transform ResolveOwner(Transform actorRoot, string ownerName)
        {
            if (string.IsNullOrEmpty(ownerName))
                return null;
            Transform direct = ResolvePath(actorRoot, ownerName);
            if (direct != null)
                return direct;
            Transform[] matches = actorRoot.GetComponentsInChildren<Transform>(true)
                .Where(candidate => candidate.name == ownerName)
                .ToArray();
            return matches.Length == 1 ? matches[0] : null;
        }

        private static Transform ResolvePath(Transform actorRoot, string serializedPath)
        {
            if (actorRoot == null || string.IsNullOrEmpty(serializedPath))
                return null;
            string path = serializedPath.Replace('\\', '/').Trim('/');
            string actorPrefix = actorRoot.name + "/";
            if (path.StartsWith(actorPrefix, StringComparison.Ordinal))
                path = path.Substring(actorPrefix.Length);
            return actorRoot.Find(path);
        }

        private static string ExtractNamedObject(string json, string propertyName)
        {
            string marker = "\"" + propertyName + "\"";
            int markerIndex = json.IndexOf(marker, StringComparison.Ordinal);
            if (markerIndex < 0)
                throw new InvalidOperationException(
                    "Secondary dynamics contract does not contain actor " + propertyName + ".");
            int opening = json.IndexOf('{', markerIndex + marker.Length);
            if (opening < 0)
                throw new InvalidOperationException("Actor contract object has no opening brace.");
            int closing = FindMatchingBrace(json, opening);
            return json.Substring(opening, closing - opening + 1);
        }

        private static int FindMatchingBrace(string json, int opening)
        {
            int depth = 0;
            bool escaped = false;
            bool quoted = false;
            for (int index = opening; index < json.Length; index++)
            {
                char character = json[index];
                if (quoted)
                {
                    if (escaped)
                    {
                        escaped = false;
                    }
                    else if (character == '\\')
                    {
                        escaped = true;
                    }
                    else if (character == '"')
                    {
                        quoted = false;
                    }
                    continue;
                }
                if (character == '"')
                {
                    quoted = true;
                    continue;
                }
                if (character == '{')
                    depth++;
                else if (character == '}' && --depth == 0)
                    return index;
            }
            throw new InvalidOperationException("Actor contract object has an unterminated brace.");
        }

        private static string GetOutputPath()
        {
            return Path.GetFullPath(Path.Combine(Application.dataPath, "..", OutputRelativePath));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
