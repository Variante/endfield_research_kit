using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    internal static class EndfieldSecondaryDynamicsBindingBuilder
    {
        private const string EndminfPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string SolverInputsPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_solver_inputs.json";
        private const string PayloadDecodePath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_payload_decode.json";

        internal static void Configure(
            GameObject actor,
            string actorName,
            string actorGeneratedRoot)
        {
            if (actor == null ||
                !string.Equals(actorName, "Endminf", StringComparison.OrdinalIgnoreCase))
                return;

            TextAsset solverInputs = AssetDatabase.LoadAssetAtPath<TextAsset>(SolverInputsPath);
            TextAsset payloadDecode = AssetDatabase.LoadAssetAtPath<TextAsset>(PayloadDecodePath);
            if (solverInputs == null || payloadDecode == null)
                throw new FileNotFoundException(
                    "Endminf secondary-dynamics source contracts are missing.");

            Dictionary<string, object> solverActor = ActorRow(solverInputs.text, "endminf");
            Dictionary<string, object> payloadActor = ActorRow(payloadDecode.text, "endminf");
            List<object> solverCloths = Array(solverActor, "cloths");
            List<object> payloadCloths = Array(payloadActor, "cloths");
            if (solverCloths.Count != 4 || payloadCloths.Count != 4)
                throw new InvalidDataException("Endminf must contain exactly four cloth owners.");

            var solverByOwner = solverCloths
                .Select((value, index) => Object(value, "solver cloth " + index))
                .ToDictionary(row => Text(row, "game_object_path"), StringComparer.Ordinal);
            var owners = new List<EndfieldSecondaryDynamicsData.Owner>();
            foreach (object value in payloadCloths)
            {
                Dictionary<string, object> cloth = Object(value, "payload cloth");
                string ownerPath = Text(cloth, "game_object_path");
                if (!solverByOwner.TryGetValue(ownerPath, out Dictionary<string, object> solverCloth))
                    throw new InvalidDataException("No solver-input cloth matches " + ownerPath + ".");

                Dictionary<string, object> transformArray = Object(
                    Required(cloth, "transform_array"), ownerPath + ".transform_array");
                string[] paths = Array(transformArray, "entries")
                    .Select((entry, index) => Text(
                        Object(entry, ownerPath + ".transform_array[" + index + "]"),
                        "hierarchy_path"))
                    .ToArray();
                if (paths.Length < 2 || !string.Equals(paths[paths.Length - 1], ownerPath,
                        StringComparison.Ordinal))
                    throw new InvalidDataException(
                        ownerPath + " transform array must end with its center transform.");

                Dictionary<string, object> arrays = Object(
                    Required(cloth, "proxy_mesh_arrays"), ownerPath + ".proxy_mesh_arrays");
                owners.Add(new EndfieldSecondaryDynamicsData.Owner
                {
                    ownerPath = ownerPath,
                    centerTransformPath = paths[paths.Length - 1],
                    proxyTransformPaths = paths.Take(paths.Length - 1).ToArray(),
                    selectionSampleCount = Count(Object(
                        Required(cloth, "selection_data"), ownerPath + ".selection_data")),
                    proxyVertexCount = Count(Object(
                        Required(arrays, "referenceIndices"), ownerPath + ".referenceIndices")),
                    lineCount = Count(Object(Required(arrays, "lines"), ownerPath + ".lines")),
                    baselineCount = Count(Object(
                        Required(arrays, "baseLineFlags"), ownerPath + ".baseLineFlags")),
                    centerFixedCount = Count(Object(
                        Required(arrays, "centerFixedList"), ownerPath + ".centerFixedList")),
                    colliderCount = Array(solverCloth, "collider_references").Count,
                });
            }

            int bindingCount = owners.Sum(owner => owner.proxyTransformPaths.Length);
            int uniqueCount = owners
                .SelectMany(owner => owner.proxyTransformPaths)
                .Distinct(StringComparer.Ordinal)
                .Count();
            if (bindingCount != 126 || uniqueCount != 100 || bindingCount - uniqueCount != 26)
                throw new InvalidDataException(
                    "Endminf secondary-dynamics binding overlap contract drifted.");

            string directory = actorGeneratedRoot + "/SecondaryDynamics";
            EnsureAssetFolder(directory);
            string assetPath = directory + "/EndminfSecondaryDynamicsData.asset";
            EndfieldSecondaryDynamicsData data =
                AssetDatabase.LoadAssetAtPath<EndfieldSecondaryDynamicsData>(assetPath);
            if (data == null)
            {
                data = ScriptableObject.CreateInstance<EndfieldSecondaryDynamicsData>();
                AssetDatabase.CreateAsset(data, assetPath);
            }
            data.sourceRecovered = true;
            data.actorKey = "endminf";
            data.solverInputs = solverInputs;
            data.solverInputsSha256 = Sha256(SolverInputsPath);
            data.payloadDecode = payloadDecode;
            data.payloadDecodeSha256 = Sha256(PayloadDecodePath);
            data.owners = owners.ToArray();
            data.expectedBindingCount = bindingCount;
            data.expectedUniqueBindingCount = uniqueCount;
            data.expectedOverlappingBindingCount = bindingCount - uniqueCount;
            EditorUtility.SetDirty(data);

            EndfieldSecondaryDynamicsRuntime runtime =
                actor.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            if (runtime == null)
                runtime = actor.AddComponent<EndfieldSecondaryDynamicsRuntime>();
            runtime.data = data;
            EditorUtility.SetDirty(runtime);
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Endminf Secondary Dynamics Binding")]
        public static void VerifyGeneratedEndminfBinding()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(EndminfPrefabPath);
            if (prefab == null)
                throw new FileNotFoundException("Generated Endminf prefab is missing.", EndminfPrefabPath);
            EndfieldSecondaryDynamicsRuntime runtime =
                prefab.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            if (runtime == null || runtime.data == null || runtime.SolverWritebackEnabled)
                throw new InvalidDataException(
                    "Generated Endminf secondary-dynamics coordinator is missing or not fail-closed.");
            EndfieldSecondaryDynamicsOwnerContract.BindingAudit audit =
                EndfieldSecondaryDynamicsOwnerContract.Verify(prefab, "Endminf", SolverInputsPath);
            if (!audit.owner_binding_verified ||
                audit.proxy_bindings_expected != 126 ||
                audit.unique_proxy_bindings != 100 ||
                audit.overlapping_proxy_bindings != 26 ||
                !audit.actor_runtime_coordinator_observed ||
                audit.solver_writeback_enabled)
            {
                throw new InvalidDataException(
                    "Generated Endminf secondary-dynamics binding audit differs.");
            }
            Debug.Log(
                "Verified Endminf secondary dynamics: 4 owners, 126 bindings, " +
                "100 unique transforms, 26 overlaps, solver writeback fail-closed.");
        }

        private static Dictionary<string, object> ActorRow(string json, string actorKey)
        {
            Dictionary<string, object> root = Object(
                ManifestMiniJson.Deserialize(json), "contract root");
            Dictionary<string, object> actors = Object(Required(root, "actors"), "actors");
            if (!actors.TryGetValue(actorKey, out object value))
                throw new InvalidDataException("Contract has no actor key " + actorKey + ".");
            return Object(value, "actors." + actorKey);
        }

        private static int Count(Dictionary<string, object> value) =>
            Convert.ToInt32(Required(value, "count"), CultureInfo.InvariantCulture);

        private static object Required(Dictionary<string, object> row, string key)
        {
            if (!row.TryGetValue(key, out object value) || value == null)
                throw new InvalidDataException("Secondary-dynamics contract lacks '" + key + "'.");
            return value;
        }

        private static Dictionary<string, object> Object(object value, string context) =>
            value as Dictionary<string, object> ??
            throw new InvalidDataException("Expected object at " + context + ".");

        private static List<object> Array(Dictionary<string, object> row, string key) =>
            Required(row, key) as List<object> ??
            throw new InvalidDataException("Expected array at " + key + ".");

        private static string Text(Dictionary<string, object> row, string key)
        {
            string text = Convert.ToString(Required(row, key), CultureInfo.InvariantCulture) ?? "";
            if (string.IsNullOrWhiteSpace(text))
                throw new InvalidDataException("Empty text field '" + key + "'.");
            return text;
        }

        private static string Sha256(string assetPath)
        {
            string absolute = Path.GetFullPath(Path.Combine(
                Application.dataPath, "..", assetPath));
            using (SHA256 sha = SHA256.Create())
                return string.Concat(sha.ComputeHash(File.ReadAllBytes(absolute))
                    .Select(value => value.ToString("x2")));
        }

        private static void EnsureAssetFolder(string assetPath)
        {
            string current = "Assets";
            foreach (string segment in assetPath.Split('/').Skip(1))
            {
                string next = current + "/" + segment;
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segment);
                current = next;
            }
        }
    }
}
