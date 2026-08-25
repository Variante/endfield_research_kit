using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Verifies that the tracked BeyondBoneCloth owner evidence still binds to
    /// the generated actor hierarchy. This is deliberately Editor-only and
    /// performs no simulation, scheduling, or transform writes.
    /// </summary>
    internal static class EndfieldSecondaryDynamicsOwnerContract
    {
        [Serializable]
        internal sealed class BindingAudit
        {
            public string status = "not_checked";
            public string actor_key = "";
            public string contract_sha256 = "";
            public int cloth_owners_expected;
            public int cloth_owners_resolved;
            public int collider_owners_expected;
            public int collider_owners_resolved;
            public int root_bones_expected;
            public int root_bones_resolved;
            public int proxy_bindings_expected;
            public int proxy_bindings_resolved;
            public int unique_proxy_bindings;
            public int overlapping_proxy_bindings;
            public bool actor_runtime_coordinator_observed;
            public bool solver_writeback_enabled;
            public bool owner_binding_verified;
            public bool runtime_solver_observed;
            public string[] runtime_solver_components = Array.Empty<string>();
            public string evidence_boundary =
                "owner hierarchy presence only; no solver or retail-equivalent motion verified";
        }

        internal static BindingAudit Verify(
            GameObject actor,
            string actorName,
            string contractAssetPath)
        {
            if (actor == null)
                throw new ArgumentNullException(nameof(actor));
            if (string.IsNullOrWhiteSpace(actorName))
                throw new InvalidDataException("Secondary-dynamics actor name is empty.");
            if (string.IsNullOrWhiteSpace(contractAssetPath))
                throw new InvalidDataException("Secondary-dynamics contract path is empty.");

            string projectRoot = Path.GetFullPath(Path.Combine(Application.dataPath, ".."));
            string absolutePath = Path.GetFullPath(Path.Combine(projectRoot, contractAssetPath));
            if (!File.Exists(absolutePath))
                throw new FileNotFoundException(
                    "Secondary-dynamics owner contract is missing.", absolutePath);

            byte[] bytes = File.ReadAllBytes(absolutePath);
            Dictionary<string, object> root = Dict(
                ManifestMiniJson.Deserialize(Encoding.UTF8.GetString(bytes)),
                "contract root");
            Dictionary<string, object> actors = Dict(Required(root, "actors"), "actors");
            string actorKey = actorName.Trim().ToLowerInvariant();
            if (!actors.TryGetValue(actorKey, out object actorValue))
            {
                throw new InvalidDataException(
                    "Secondary-dynamics contract has no actor key '" + actorKey + "'.");
            }

            Dictionary<string, object> actorRow = Dict(actorValue, "actors." + actorKey);
            List<object> cloths = List(Required(actorRow, "cloths"), actorKey + ".cloths");
            List<object> colliders = List(
                Required(actorRow, "colliders"), actorKey + ".colliders");
            var audit = new BindingAudit
            {
                actor_key = actorKey,
                contract_sha256 = Sha256(bytes),
                cloth_owners_expected = cloths.Count,
                collider_owners_expected = colliders.Count,
            };
            var proxyPaths = new List<string>();

            for (int index = 0; index < cloths.Count; index++)
            {
                Dictionary<string, object> cloth = Dict(
                    cloths[index], actorKey + ".cloths[" + index + "]");
                ResolveRequiredPath(
                    actor.transform,
                    String(cloth, "game_object_path"),
                    "cloth owner");
                audit.cloth_owners_resolved++;

                List<object> roots = List(
                    Required(cloth, "root_bones"),
                    actorKey + ".cloths[" + index + "].root_bones");
                audit.root_bones_expected += roots.Count;
                for (int rootIndex = 0; rootIndex < roots.Count; rootIndex++)
                {
                    Dictionary<string, object> rootBone = Dict(
                        roots[rootIndex],
                        actorKey + ".cloths[" + index + "].root_bones[" + rootIndex + "]");
                    ResolveRequiredPath(
                        actor.transform,
                        String(rootBone, "path"),
                        "cloth root bone");
                    audit.root_bones_resolved++;
                }

                string ownerPath = String(cloth, "game_object_path");
                List<object> proxyBindings = List(
                    Required(cloth, "proxy_transform_bindings"),
                    actorKey + ".cloths[" + index + "].proxy_transform_bindings");
                for (int bindingIndex = 0; bindingIndex < proxyBindings.Count; bindingIndex++)
                {
                    Dictionary<string, object> binding = Dict(
                        proxyBindings[bindingIndex],
                        actorKey + ".cloths[" + index + "].proxy_transform_bindings[" +
                        bindingIndex + "]");
                    int arrayIndex = Convert.ToInt32(
                        Required(binding, "array_index"), CultureInfo.InvariantCulture);
                    if (arrayIndex != bindingIndex)
                        throw new InvalidDataException(
                            "Secondary-dynamics proxy binding order drifted for " + ownerPath + ".");
                    string path = String(binding, "path");
                    if (string.Equals(path, ownerPath, StringComparison.Ordinal))
                        continue;
                    audit.proxy_bindings_expected++;
                    ResolveRequiredPath(actor.transform, path, "proxy transform");
                    audit.proxy_bindings_resolved++;
                    proxyPaths.Add(path);
                }
            }

            for (int index = 0; index < colliders.Count; index++)
            {
                Dictionary<string, object> collider = Dict(
                    colliders[index], actorKey + ".colliders[" + index + "]");
                ResolveRequiredPath(
                    actor.transform,
                    String(collider, "game_object_path"),
                    "collider owner");
                audit.collider_owners_resolved++;
            }

            audit.runtime_solver_components = actor
                .GetComponentsInChildren<MonoBehaviour>(true)
                .Where(component => component != null)
                .Select(component => component.GetType().FullName ?? component.GetType().Name)
                .Where(typeName =>
                    typeName.IndexOf("BeyondDynamicBone", StringComparison.OrdinalIgnoreCase) >= 0 ||
                    typeName.IndexOf("MagicaCloth", StringComparison.OrdinalIgnoreCase) >= 0)
                .Distinct(StringComparer.Ordinal)
                .OrderBy(value => value, StringComparer.Ordinal)
                .ToArray();
            audit.runtime_solver_observed = audit.runtime_solver_components.Length > 0;
            audit.unique_proxy_bindings = proxyPaths.Distinct(StringComparer.Ordinal).Count();
            audit.overlapping_proxy_bindings =
                audit.proxy_bindings_expected - audit.unique_proxy_bindings;
            EndfieldSecondaryDynamicsRuntime coordinator =
                actor.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            audit.actor_runtime_coordinator_observed = coordinator != null;
            audit.solver_writeback_enabled =
                coordinator != null && coordinator.SolverWritebackEnabled;
            if (actorKey == "endminf" &&
                (audit.proxy_bindings_expected != 126 ||
                 audit.unique_proxy_bindings != 100 ||
                 audit.overlapping_proxy_bindings != 26))
            {
                throw new InvalidDataException(
                    "Endminf secondary-dynamics proxy overlap contract drifted.");
            }
            audit.owner_binding_verified =
                audit.cloth_owners_resolved == audit.cloth_owners_expected &&
                audit.collider_owners_resolved == audit.collider_owners_expected &&
                audit.root_bones_resolved == audit.root_bones_expected &&
                audit.proxy_bindings_resolved == audit.proxy_bindings_expected;
            if (!audit.owner_binding_verified)
                throw new InvalidDataException("Secondary-dynamics owner binding is incomplete.");
            audit.status = audit.solver_writeback_enabled
                ? "owner_and_proxy_hierarchy_verified_solver_writeback_unverified"
                : audit.actor_runtime_coordinator_observed
                    ? "owner_and_proxy_hierarchy_verified_coordinator_fail_closed"
                    : audit.runtime_solver_observed
                        ? "owner_and_proxy_hierarchy_verified_runtime_solver_component_observed_unverified"
                        : "owner_and_proxy_hierarchy_verified_solver_absent";
            audit.evidence_boundary = audit.solver_writeback_enabled
                ? "owner/proxy hierarchy verified; solver writeback present but retail equivalence unverified"
                : "owner/proxy hierarchy and overlap verified; no solver transform writeback enabled";
            return audit;
        }

        private static Transform ResolveRequiredPath(
            Transform actorRoot,
            string relativePath,
            string role)
        {
            if (string.IsNullOrWhiteSpace(relativePath))
                throw new InvalidDataException("Secondary-dynamics " + role + " path is empty.");
            Transform resolved = actorRoot.Find(relativePath);
            if (resolved == null)
            {
                throw new InvalidDataException(
                    "Secondary-dynamics " + role + " path does not resolve under actor '" +
                    actorRoot.name + "': " + relativePath);
            }
            return resolved;
        }

        private static object Required(Dictionary<string, object> row, string key)
        {
            if (!row.TryGetValue(key, out object value) || value == null)
                throw new InvalidDataException("Secondary-dynamics contract lacks '" + key + "'.");
            return value;
        }

        private static Dictionary<string, object> Dict(object value, string context) =>
            value as Dictionary<string, object> ??
            throw new InvalidDataException(
                "Secondary-dynamics contract expected an object at " + context + ".");

        private static List<object> List(object value, string context) =>
            value as List<object> ??
            throw new InvalidDataException(
                "Secondary-dynamics contract expected an array at " + context + ".");

        private static string String(Dictionary<string, object> row, string key)
        {
            object value = Required(row, key);
            string text = Convert.ToString(value, CultureInfo.InvariantCulture) ?? "";
            if (string.IsNullOrWhiteSpace(text))
                throw new InvalidDataException(
                    "Secondary-dynamics contract field '" + key + "' is empty.");
            return text;
        }

        private static string Sha256(byte[] bytes)
        {
            using (SHA256 sha = SHA256.Create())
            {
                return string.Concat(sha.ComputeHash(bytes).Select(value => value.ToString("x2")));
            }
        }
    }
}
