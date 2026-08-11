using System;
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLab.Editor
{
    public static class EndfieldHandIkRecoveryVerifier
    {
        private const string CatalogPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/playable_character_ik_evidence.json";
        private const string FootScalarCatalogPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Catalog/playable_character_foot_ik_scalar_curves.json";
        private static readonly string[] HandTargetSuffixes =
            { "/IK_Hand_L_001", "/IK_Hand_R_001" };
        private static readonly string[] DeformingHandSuffixes =
            { "/Bip001_L_Hand", "/Bip001_R_Hand" };
        private static readonly string[] FootTargetSuffixes =
            { "/IK_Foot_L_001", "/IK_Foot_R_001" };
        private static readonly string[] KneeTargetSuffixes =
            { "/IK_Knee_L_001", "/IK_Knee_R_001" };
        private static readonly string[] WeaponTargetSuffixes =
            { "/IK_Weapon_L_001", "/IK_Weapon_R_001" };

        private sealed class ActorSpec
        {
            public string CharacterId = "";
            public string ActorToken = "";
            public string RootName = "";
            public string PrefabPath = "";
            public string ManifestPath = "";
            public Dictionary<string, object> ClipBindingSummary = new Dictionary<string, object>();
            public Dictionary<string, object> RuntimeSolver = new Dictionary<string, object>();
        }

        private sealed class EvidenceCounts
        {
            public int Clips;
            public int BilateralHandTargets;
            public int BilateralDeformingHands;
            public int BilateralFootTargets;
            public int BilateralKneeTargets;
            public int BilateralWeaponTargets;
            public int PartialHandTargets;
            public int PartialDeformingHands;
            public int PartialFootTargets;
            public int PartialKneeTargets;
            public int PartialWeaponTargets;

            public void Add(EvidenceCounts other)
            {
                Clips += other.Clips;
                BilateralHandTargets += other.BilateralHandTargets;
                BilateralDeformingHands += other.BilateralDeformingHands;
                BilateralFootTargets += other.BilateralFootTargets;
                BilateralKneeTargets += other.BilateralKneeTargets;
                BilateralWeaponTargets += other.BilateralWeaponTargets;
                PartialHandTargets += other.PartialHandTargets;
                PartialDeformingHands += other.PartialDeformingHands;
                PartialFootTargets += other.PartialFootTargets;
                PartialKneeTargets += other.PartialKneeTargets;
                PartialWeaponTargets += other.PartialWeaponTargets;
            }
        }

        public static void VerifyBatch()
        {
            try
            {
                List<ActorSpec> actors = LoadPlayableRoster();
                Require(actors.Count > 0, "Playable IK evidence catalog is empty");
                int catalogFootScalarCurves = VerifyFootScalarCatalog();

                var totals = new EvidenceCounts();
                int consumersUnproven = 0;
                int weightsUnproven = 0;
                int actorFootScalarCurves = 0;
                foreach (ActorSpec actor in actors)
                {
                    EvidenceCounts actorCounts = VerifyActor(
                        actor,
                        out bool consumerProven,
                        out bool weightsProven,
                        out int footScalarCurves);
                    totals.Add(actorCounts);
                    actorFootScalarCurves += footScalarCurves;
                    if (!consumerProven)
                        consumersUnproven++;
                    if (!weightsProven)
                        weightsUnproven++;
                }

                Require(consumersUnproven == actors.Count, "A runtime IK consumer became marked proven without verifier support");
                Require(weightsUnproven == actors.Count, "Runtime IK weights became marked proven without verifier support");
                Require(
                    actorFootScalarCurves == catalogFootScalarCurves,
                    $"Actor scalar rows total {actorFootScalarCurves}; catalog has {catalogFootScalarCurves}");
                Debug.Log(
                    "PLAYABLE_IK_RECOVERY_VERIFY_OK "
                    + $"actors={actors.Count} clips={totals.Clips} "
                    + $"bilateral_hand_targets={totals.BilateralHandTargets} "
                    + $"bilateral_deforming_hands={totals.BilateralDeformingHands} "
                    + $"bilateral_foot_targets={totals.BilateralFootTargets} "
                    + $"bilateral_knee_targets={totals.BilateralKneeTargets} "
                    + $"bilateral_weapon_targets={totals.BilateralWeaponTargets} "
                    + $"partial_hand_targets={totals.PartialHandTargets} "
                    + $"partial_deforming_hands={totals.PartialDeformingHands} "
                    + $"partial_foot_targets={totals.PartialFootTargets} "
                    + $"partial_knee_targets={totals.PartialKneeTargets} "
                    + $"partial_weapon_targets={totals.PartialWeaponTargets} "
                    + $"runtime_consumers_unproven={consumersUnproven} "
                    + $"runtime_weights_unproven={weightsUnproven} "
                    + $"retail_foot_binding_source_postmodels={actors.Count} "
                    + $"exact_foot_ik_weight_curves={catalogFootScalarCurves} "
                    + "foot_ik_foot_weight_bindings=0 foot_ik_adsorb_weight_bindings=0 "
                    + "foot_weight_source_proven=1 absent_key_fallback_proven=1 "
                    + "final_pelvis_recurrence_proven=1 active_ik_layer_mask=0x00300000 "
                    + "grounder_callback_order_proven=0 "
                    + "complete_grounder_weight_outputs_proven=0 "
                    + $"retail_hand_target_source=external_exdata "
                    + $"lab_solver_default_enabled=0 fail_closed_pose_checks={actors.Count}");
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static List<ActorSpec> LoadPlayableRoster()
        {
            TextAsset catalogAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(CatalogPath);
            Require(catalogAsset != null, $"Missing playable catalog: {CatalogPath}");
            Dictionary<string, object> catalog = Dict(
                global::EndfieldGraphShaderLabEditor.ManifestMiniJson.Deserialize(catalogAsset.text));
            int declaredRosterCount = Int(catalog.TryGetValue("roster_count", out object rosterObj) ? rosterObj : null);
            Require(declaredRosterCount > 0, "Catalog roster_count must be positive");

            var actors = new List<ActorSpec>();
            foreach (object item in List(catalog.TryGetValue("characters", out object charactersObj) ? charactersObj : null))
            {
                Dictionary<string, object> character = Dict(item);
                actors.Add(
                    new ActorSpec
                    {
                        CharacterId = Str(character.TryGetValue("character_id", out object idObj) ? idObj : null),
                        ActorToken = Str(character.TryGetValue("actor_token", out object tokenObj) ? tokenObj : null),
                        RootName = Str(character.TryGetValue("root_name", out object rootObj) ? rootObj : null),
                        PrefabPath = Str(character.TryGetValue("prefab_asset_path", out object prefabObj) ? prefabObj : null),
                        ManifestPath = Str(character.TryGetValue("manifest_asset_path", out object manifestObj) ? manifestObj : null),
                        ClipBindingSummary = Dict(
                            character.TryGetValue("clip_binding_summary", out object summaryObj)
                                ? summaryObj
                                : null),
                        RuntimeSolver = Dict(
                            character.TryGetValue("runtime_solver", out object runtimeObj)
                                ? runtimeObj
                                : null),
                    });
            }
            Require(
                actors.Count == declaredRosterCount,
                $"Playable catalog count is {actors.Count}; declared {declaredRosterCount}");
            return actors;
        }

        private static EvidenceCounts VerifyActor(
            ActorSpec actor,
            out bool consumerProven,
            out bool weightsProven,
            out int footScalarCurveCount)
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(actor.PrefabPath);
            Require(prefab != null, $"{actor.CharacterId}: missing prefab {actor.PrefabPath}");

            CharacterProceduralIk prefabSolver = prefab.GetComponent<CharacterProceduralIk>();
            Require(prefabSolver != null, $"{actor.CharacterId}: CharacterProceduralIk is missing");
            Require(
                !prefabSolver.enableLabSolver,
                $"{actor.CharacterId}: diagnostic lab solver must deserialize disabled");

            consumerProven = Bool(
                actor.RuntimeSolver.TryGetValue("consumer_proven", out object consumerObj)
                    ? consumerObj
                    : null);
            weightsProven = Bool(
                actor.RuntimeSolver.TryGetValue("weights_proven", out object weightsObj)
                    ? weightsObj
                    : null);
            Require(!consumerProven, $"{actor.CharacterId}: runtime consumer is not source-proven");
            Require(!weightsProven, $"{actor.CharacterId}: runtime weights are not source-proven");
            Require(
                Bool(Value(actor.RuntimeSolver, "foot_binding_proven")),
                $"{actor.CharacterId}: original Grounder foot binding evidence is missing");
            Require(
                Bool(Value(actor.RuntimeSolver, "foot_weight_flow_proven")),
                $"{actor.CharacterId}: original animation-blackboard foot weight flow is missing");
            Require(
                Bool(Value(actor.RuntimeSolver, "foot_weight_source_proven")),
                $"{actor.CharacterId}: three-key foot source semantics are missing");
            Dictionary<string, object> footWeightSource = Dict(
                Value(actor.RuntimeSolver, "foot_weight_source"));
            Require(
                Str(Value(footWeightSource, "status"))
                    == "three_key_lookup_and_final_pelvis_recurrence_recovered_live_inputs_and_callback_order_incomplete",
                $"{actor.CharacterId}: foot scalar evidence status changed");
            Require(
                Bool(Value(footWeightSource, "do_not_synthesize_absent_values")),
                $"{actor.CharacterId}: absent foot values may not be synthesized");
            Require(
                !Bool(Value(footWeightSource, "complete_three_value_source_recovered"))
                && Bool(Value(footWeightSource, "three_requested_key_lookup_semantics_recovered"))
                && Bool(Value(footWeightSource, "absent_key_fallback_recovered"))
                && Bool(Value(footWeightSource, "final_pelvis_weight_recurrence_recovered"))
                && !Bool(Value(footWeightSource, "complete_grounder_weight_outputs_recovered")),
                $"{actor.CharacterId}: foot lookup/fallback/final-output boundary changed");
            Dictionary<string, object> pelvisWeightRuntime = Dict(
                Value(footWeightSource, "final_pelvis_weight_runtime"));
            Dictionary<string, object> airWeightRuntime = Dict(
                Value(pelvisWeightRuntime, "air"));
            Dictionary<string, object> downstreamWeightRuntime = Dict(
                Value(pelvisWeightRuntime, "downstream_grounder_update"));
            Require(
                Mathf.Abs(Float(Value(airWeightRuntime, "rate")) - 360.0f) <= 1e-6f
                && !Bool(Value(downstreamWeightRuntime, "callback_order_recovered")),
                $"{actor.CharacterId}: exact air rate or callback-order boundary changed");
            Dictionary<string, object> ordinaryGrounding = Dict(
                Value(actor.RuntimeSolver, "ordinary_grounding"));
            Dictionary<string, object> groundingQueries = Dict(
                Value(ordinaryGrounding, "queries"));
            Require(
                Bool(Value(groundingQueries, "active_movement_setting_ik_layers_recovered"))
                && Int(Value(groundingQueries, "active_movement_setting_ik_layers_decimal"))
                    == 0x00300000,
                $"{actor.CharacterId}: installed MovementSetting Terrain|IK mask changed");
            Require(
                !Bool(Value(groundingQueries, "serialized_grounder_layer_mask_runtime_authoritative"))
                && !Bool(Value(groundingQueries, "source_compatible_terrain_query_provider_recovered")),
                $"{actor.CharacterId}: layer authority/provider evidence boundary changed");
            VerifyRequestedFootValues(actor.CharacterId, List(Value(footWeightSource, "requested_values")));
            footScalarCurveCount = Int(Value(
                footWeightSource,
                "current_actor_exact_foot_ik_weight_curve_count"));
            List<object> actorScalarRows = List(Value(
                footWeightSource,
                "current_actor_exact_foot_ik_weight_curves"));
            Require(
                actorScalarRows.Count == footScalarCurveCount,
                $"{actor.CharacterId}: compact scalar row count changed");
            foreach (object rowObj in actorScalarRows)
            {
                Dictionary<string, object> row = Dict(rowObj);
                Require(
                    Int(Value(row, "scalar_track_index")) == 15,
                    $"{actor.CharacterId}: FootIKWeight moved from scalar track 15");
                Require(
                    Mathf.Abs(Float(Value(row, "sample_rate")) - 60.0f) <= 1e-6f,
                    $"{actor.CharacterId}: FootIKWeight sample rate changed");
                Require(
                    Mathf.Abs(Float(Value(row, "constant_value")) - 1.0f) <= 1e-6f,
                    $"{actor.CharacterId}: FootIKWeight is no longer exact constant one");
            }
            Dictionary<string, object> perTarget = Dict(Value(actor.RuntimeSolver, "per_target_binding"));
            Require(
                Str(Value(Dict(Value(perTarget, "foot")), "status"))
                    == "proven_grounding_reference_in_all_current_original_postmodels",
                $"{actor.CharacterId}: foot binding evidence boundary changed");
            Require(
                Int(Value(Dict(Value(perTarget, "foot")), "source_roster_audit_count")) == 31,
                $"{actor.CharacterId}: exact Grounder foot-binding roster count changed");
            Require(
                !Bool(Value(Dict(Value(perTarget, "foot")), "bipedik_limb_target")),
                $"{actor.CharacterId}: authored foot reference was incorrectly promoted to a BipedIK limb target");
            Require(
                Str(Value(Dict(Value(perTarget, "hand")), "status"))
                    == "external_interaction_target_not_baked_marker",
                $"{actor.CharacterId}: hand target source changed");

            EvidenceCounts counts = CountsFromSummary(actor.ClipBindingSummary);
            string representativeClip = FindRepresentativeClip(actor);
            Require(counts.Clips > 0, $"{actor.CharacterId}: manifest has no clips");
            Require(!string.IsNullOrEmpty(representativeClip), $"{actor.CharacterId}: no authored overview loop clip found");
            VerifyRepresentativeClip(actor, prefab, representativeClip);

            Debug.Log(
                $"PLAYABLE_IK_RECOVERY_ACTOR_OK character={actor.CharacterId} token={actor.ActorToken} "
                + $"clips={counts.Clips} bilateral_hand_targets={counts.BilateralHandTargets} "
                + $"bilateral_deforming_hands={counts.BilateralDeformingHands} "
                + $"bilateral_foot_targets={counts.BilateralFootTargets} "
                + $"bilateral_knee_targets={counts.BilateralKneeTargets} "
                + $"bilateral_weapon_targets={counts.BilateralWeaponTargets} "
                + $"retail_foot_binding_family_proven=true exact_foot_ik_weight_curves={footScalarCurveCount} "
                + "foot_weight_source_proven=true absent_key_fallback_proven=true "
                + "final_pelvis_recurrence_proven=true active_ik_layer_mask=0x00300000 "
                + "grounder_callback_order_proven=false "
                + "complete_grounder_weight_outputs_proven=false "
                + "retail_hand_target_source=external_exdata "
                + "runtime_consumer_proven=false runtime_weights_proven=false lab_solver_default_enabled=false");
            return counts;
        }

        private static int VerifyFootScalarCatalog()
        {
            TextAsset catalogAsset = AssetDatabase.LoadAssetAtPath<TextAsset>(FootScalarCatalogPath);
            Require(catalogAsset != null, $"Missing foot scalar catalog: {FootScalarCatalogPath}");
            Dictionary<string, object> catalog = Dict(
                global::EndfieldGraphShaderLabEditor.ManifestMiniJson.Deserialize(catalogAsset.text));
            Dictionary<string, object> scope = Dict(Value(catalog, "scope"));
            Require(
                Int(Value(scope, "unique_current_all_ui_clip_count")) == 779,
                "Foot scalar catalog UI clip scope changed");
            Require(
                Int(Value(scope, "nonempty_float_buffer_clip_count")) == 754,
                "Foot scalar catalog FloatBufferData scope changed");
            VerifyRequestedFootValues("catalog", List(Value(catalog, "requested_values")));

            List<object> rows = List(Value(catalog, "authored_curves"));
            Require(rows.Count == 24, $"Expected 24 exact FootIKWeight rows; found {rows.Count}");
            var actors = new HashSet<string>(StringComparer.Ordinal);
            foreach (object rowObj in rows)
            {
                Dictionary<string, object> row = Dict(rowObj);
                actors.Add(Str(Value(row, "character_id")));
                Require(
                    Int(Value(row, "float_curve_count"))
                        == Int(Value(row, "animator_binding_count")),
                    $"{Str(Value(row, "clip_name"))}: scalar binding count proof changed");
                List<object> curves = List(Value(row, "curves"));
                Require(curves.Count == 1, "Each authored scalar row must contain one exact curve");
                Dictionary<string, object> curve = Dict(curves[0]);
                Require(
                    Str(Value(curve, "runtime_name")) == "FootIKWeight"
                    && Int(Value(curve, "attribute_hash_u32")) == unchecked((int)0x2B797234)
                    && Int(Value(curve, "scalar_track_index")) == 15,
                    $"{Str(Value(row, "clip_name"))}: FootIKWeight binding changed");
                Require(
                    Mathf.Abs(Float(Value(curve, "sample_rate")) - 60.0f) <= 1e-6f
                    && Mathf.Abs(Float(Value(curve, "minimum")) - 1.0f) <= 1e-6f
                    && Mathf.Abs(Float(Value(curve, "maximum")) - 1.0f) <= 1e-6f,
                    $"{Str(Value(row, "clip_name"))}: FootIKWeight values changed");
                List<object> samples = List(Value(curve, "samples"));
                Require(
                    samples.Count == Int(Value(curve, "sample_count")),
                    $"{Str(Value(row, "clip_name"))}: FootIKWeight sample count changed");
                foreach (object sample in samples)
                {
                    Require(
                        Mathf.Abs(Float(sample) - 1.0f) <= 1e-6f,
                        $"{Str(Value(row, "clip_name"))}: non-one FootIKWeight sample found");
                }
            }
            Require(actors.Count == 9, $"Expected nine actors with FootIKWeight curves; found {actors.Count}");
            Dictionary<string, object> runtime = Dict(Value(catalog, "runtime"));
            Require(
                !Bool(Value(runtime, "complete_three_value_source_recovered"))
                && Bool(Value(runtime, "three_requested_key_lookup_semantics_recovered"))
                && Bool(Value(runtime, "absent_key_fallback_recovered"))
                && Bool(Value(runtime, "final_pelvis_weight_recurrence_recovered"))
                && !Bool(Value(runtime, "complete_grounder_weight_outputs_recovered"))
                && !Bool(Value(runtime, "default_enabled")),
                "Recovered foot lookup semantics must keep incomplete final outputs fail-closed");
            return rows.Count;
        }

        private static void VerifyRequestedFootValues(string owner, List<object> values)
        {
            Require(values.Count == 3, $"{owner}: expected three requested foot values");
            var counts = new Dictionary<string, int>(StringComparer.Ordinal);
            foreach (object valueObj in values)
            {
                Dictionary<string, object> value = Dict(valueObj);
                counts[Str(Value(value, "runtime_name"))] = Int(
                    Value(value, "ui_clip_binding_count"));
            }
            Require(
                counts.TryGetValue("FootIKWeight", out int weightCount) && weightCount == 24,
                $"{owner}: FootIKWeight binding count changed");
            Require(
                counts.TryGetValue("FootIKFootWeight", out int footCount) && footCount == 0,
                $"{owner}: FootIKFootWeight must remain absent from UI clips");
            Require(
                counts.TryGetValue("FootIKAdsorbWeight", out int adsorbCount) && adsorbCount == 0,
                $"{owner}: FootIKAdsorbWeight must remain absent from UI clips");
        }

        private static EvidenceCounts CountsFromSummary(Dictionary<string, object> summary)
        {
            return new EvidenceCounts
            {
                Clips = Int(Value(summary, "clip_count")),
                BilateralHandTargets = Int(Value(summary, "bilateral_hand_targets_clip_count")),
                BilateralDeformingHands = Int(Value(summary, "bilateral_deforming_hands_clip_count")),
                BilateralFootTargets = Int(Value(summary, "bilateral_foot_targets_clip_count")),
                BilateralKneeTargets = Int(Value(summary, "bilateral_knee_targets_clip_count")),
                BilateralWeaponTargets = Int(Value(summary, "bilateral_weapon_targets_clip_count")),
                PartialHandTargets = Int(Value(summary, "partial_hand_targets_clip_count")),
                PartialDeformingHands = Int(Value(summary, "partial_deforming_hands_clip_count")),
                PartialFootTargets = Int(Value(summary, "partial_foot_targets_clip_count")),
                PartialKneeTargets = Int(Value(summary, "partial_knee_targets_clip_count")),
                PartialWeaponTargets = Int(Value(summary, "partial_weapon_targets_clip_count")),
            };
        }

        private static string FindRepresentativeClip(ActorSpec actor)
        {
            foreach (object item in List(Value(
                actor.ClipBindingSummary,
                "clips_with_bilateral_hand_targets")))
            {
                string clipName = Str(item);
                if (clipName.StartsWith($"A_actor_{actor.ActorToken}_", StringComparison.OrdinalIgnoreCase)
                    && clipName.IndexOf("ui_overview", StringComparison.OrdinalIgnoreCase) >= 0
                    && clipName.IndexOf("loop", StringComparison.OrdinalIgnoreCase) >= 0)
                {
                    return clipName;
                }
            }
            return "";
        }

        private static void VerifyRepresentativeClip(
            ActorSpec actor,
            GameObject prefab,
            string clipName)
        {
            string clipPath = $"{actor.ManifestPath.Substring(0, actor.ManifestPath.LastIndexOf('/'))}/Animations/{clipName}.anim";
            AnimationClip clip = AssetDatabase.LoadAssetAtPath<AnimationClip>(clipPath);
            Require(clip != null, $"{actor.CharacterId}: missing representative clip {clipPath}");

            var curvePaths = new HashSet<string>(StringComparer.Ordinal);
            foreach (EditorCurveBinding binding in AnimationUtility.GetCurveBindings(clip))
            {
                if (binding.type == typeof(Transform))
                    curvePaths.Add(binding.path);
            }
            Require(HasBilateral(curvePaths, HandTargetSuffixes), $"{actor.CharacterId}: bilateral hand targets are missing from Unity clip");
            Require(HasBilateral(curvePaths, DeformingHandSuffixes), $"{actor.CharacterId}: bilateral deforming hands are missing from Unity clip");
            Require(HasBilateral(curvePaths, FootTargetSuffixes), $"{actor.CharacterId}: bilateral foot targets are missing from Unity clip");
            Require(HasBilateral(curvePaths, KneeTargetSuffixes), $"{actor.CharacterId}: bilateral knee targets are missing from Unity clip");
            Require(HasBilateral(curvePaths, WeaponTargetSuffixes), $"{actor.CharacterId}: bilateral weapon targets are missing from Unity clip");

            GameObject instance = UnityEngine.Object.Instantiate(prefab);
            try
            {
                instance.hideFlags = HideFlags.HideAndDontSave;
                CharacterProceduralIk solver = instance.GetComponent<CharacterProceduralIk>();
                Require(!solver.enableLabSolver, $"{actor.CharacterId}: instance unexpectedly enabled lab solver");
                clip.SampleAnimation(instance, Mathf.Min(clip.length * 0.5f, clip.length));
                var before = CaptureArmPose(solver);
                solver.Evaluate();
                var after = CaptureArmPose(solver);
                Require(before.Count == after.Count, $"{actor.CharacterId}: arm pose capture mismatch");
                for (int index = 0; index < before.Count; index++)
                {
                    Require(
                        Vector3.SqrMagnitude(before[index].position - after[index].position) <= 1e-12f
                        && Quaternion.Angle(before[index].rotation, after[index].rotation) <= 1e-5f,
                        $"{actor.CharacterId}: disabled lab solver changed authored pose at index {index}");
                }
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(instance);
            }
        }

        private static bool HasBilateral(HashSet<string> paths, string[] suffixes) =>
            CountSuffixes(paths, suffixes) == suffixes.Length;

        private static int CountSuffixes(HashSet<string> paths, string[] suffixes)
        {
            int count = 0;
            foreach (string suffix in suffixes)
            {
                foreach (string path in paths)
                {
                    if (!path.EndsWith(suffix, StringComparison.Ordinal))
                        continue;
                    count++;
                    break;
                }
            }
            return count;
        }

        private static List<(Vector3 position, Quaternion rotation)> CaptureArmPose(
            CharacterProceduralIk solver)
        {
            var pose = new List<(Vector3, Quaternion)>();
            AddPose(pose, solver.leftUpper);
            AddPose(pose, solver.leftForearm);
            AddPose(pose, solver.leftHand);
            AddPose(pose, solver.rightUpper);
            AddPose(pose, solver.rightForearm);
            AddPose(pose, solver.rightHand);
            return pose;
        }

        private static void AddPose(
            List<(Vector3 position, Quaternion rotation)> pose,
            Transform transform)
        {
            Require(transform != null, "Configured arm transform is missing");
            pose.Add((transform.position, transform.rotation));
        }

        private static Dictionary<string, object> Dict(object value) =>
            value as Dictionary<string, object> ?? new Dictionary<string, object>();

        private static object Value(Dictionary<string, object> dictionary, string key) =>
            dictionary.TryGetValue(key, out object value) ? value : null;

        private static List<object> List(object value) =>
            value as List<object> ?? new List<object>();

        private static string Str(object value) => value?.ToString() ?? "";

        private static bool Bool(object value) =>
            value is bool boolean
                ? boolean
                : Str(value).Equals("true", StringComparison.OrdinalIgnoreCase);

        private static int Int(object value)
        {
            if (value is long longValue)
                return (int)longValue;
            if (value is double doubleValue)
                return (int)doubleValue;
            return int.TryParse(Str(value), out int parsed) ? parsed : 0;
        }

        private static float Float(object value)
        {
            if (value is double doubleValue)
                return (float)doubleValue;
            if (value is long longValue)
                return longValue;
            return float.TryParse(Str(value), out float parsed) ? parsed : 0.0f;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
