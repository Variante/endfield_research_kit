using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static partial class EndfieldManifestCharacterSetup
    {
        private static readonly string SkeletalMorphNpcPrefabInfoRoot = Path.GetFullPath(
            Path.Combine(
                Directory.GetCurrentDirectory(),
                "..",
                "export_full",
                "structured",
                "StreamingAssets",
                "Data",
                "Json",
                "NPC",
                "PrefabInfo"));

        private static readonly string SkeletalMorphAvatarJsonRoot = Path.GetFullPath(
            Path.Combine(
                Directory.GetCurrentDirectory(),
                "..",
                "export_full",
                "recovered",
                "AnimeStudio-cli",
                "Persistent",
                "json_by_type",
                "MonoBehaviour"));

        private static readonly string SkeletalMorphStreamingAvatarJsonRoot = Path.GetFullPath(
            Path.Combine(
                Directory.GetCurrentDirectory(),
                "..",
                "export_full",
                "recovered",
                "AnimeStudio-cli",
                "StreamingAssets",
                "json_by_type",
                "MonoBehaviour"));

        [MenuItem("Endfield/Character Recovery Lab/Refresh Playable Skeletal Morph Base Poses")]
        public static void RefreshPlayableSkeletalMorphBasePoses()
        {
            int refreshed = 0;
            foreach (ManifestCharacterSpec character in PlayableCatalogCharacters())
            {
                string manifestPath = Path.Combine(
                    Directory.GetCurrentDirectory(),
                    character.ManifestAssetPath);
                if (!File.Exists(manifestPath))
                    throw new FileNotFoundException(
                        $"Playable character manifest is missing: {character.RootName}",
                        manifestPath);
                if (AssetDatabase.LoadAssetAtPath<GameObject>(character.PrefabAssetPath) == null)
                    throw new FileNotFoundException(
                        $"Playable character prefab is missing: {character.RootName}",
                        character.PrefabAssetPath);

                Dictionary<string, object> manifest = Dict(
                    ManifestMiniJson.Deserialize(File.ReadAllText(manifestPath, Encoding.UTF8)));
                GameObject prefabRoot = PrefabUtility.LoadPrefabContents(character.PrefabAssetPath);
                try
                {
                    ConfigureRecoveredSkeletalMorphBasePose(prefabRoot, manifest);
                    PrefabUtility.SaveAsPrefabAsset(prefabRoot, character.PrefabAssetPath);
                    refreshed++;
                }
                finally
                {
                    PrefabUtility.UnloadPrefabContents(prefabRoot);
                }
            }

            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"Refreshed retail skeletal-morph neutral base poses: actors={refreshed}.");
        }

        private static void ConfigureRecoveredSkeletalMorphBasePose(
            GameObject root,
            Dictionary<string, object> manifest)
        {
            string characterId = Str(
                manifest.TryGetValue("character_id", out object characterIdObj)
                    ? characterIdObj
                    : null);
            if (characterId.Length == 0)
                return;

            Dictionary<string, object> sourceMembership = Dict(
                manifest.TryGetValue(
                    "source_membership",
                    out object sourceMembershipObj)
                    ? sourceMembershipObj
                    : null);
            string npcTemplateId = Str(
                manifest.TryGetValue(
                    "npc_template_id",
                    out object directNpcTemplateIdObj)
                    ? directNpcTemplateIdObj
                    : null);
            if (npcTemplateId.Length == 0)
                npcTemplateId = Str(
                sourceMembership.TryGetValue(
                    "npc_template_id",
                    out object npcTemplateIdObj)
                    ? npcTemplateIdObj
                    : null);
            if (npcTemplateId.IndexOfAny(Path.GetInvalidFileNameChars()) >= 0 ||
                npcTemplateId.Contains("/") || npcTemplateId.Contains("\\"))
            {
                throw new InvalidDataException(
                    $"NPC PrefabInfo identity is not a filename-safe source ID: {npcTemplateId}");
            }
            string npcFileName = npcTemplateId.Length > 0
                ? npcTemplateId + ".json"
                : $"npc_{characterId}.json";
            string npcPath = Path.Combine(
                SkeletalMorphNpcPrefabInfoRoot,
                npcFileName);
            if (!File.Exists(npcPath))
                throw new FileNotFoundException(
                    $"Installed NPC PrefabInfo is missing for {characterId} " +
                    $"(source template {npcFileName}).",
                    npcPath);

            Dictionary<string, object> npc = Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(npcPath, Encoding.UTF8)));
            string npcSourceId = Str(
                npc.TryGetValue("id", out object npcIdObj) ? npcIdObj : null);
            string expectedNpcSourceId = npcTemplateId.Length > 0
                ? npcTemplateId
                : $"npc_{characterId}";
            if (!string.Equals(
                    npcSourceId,
                    expectedNpcSourceId,
                    StringComparison.Ordinal))
            {
                throw new InvalidDataException(
                    $"NPC PrefabInfo identity differs for {characterId}: " +
                    $"expected={expectedNpcSourceId}, actual={npcSourceId}.");
            }
            string faceAddress = Str(
                npc.TryGetValue("facialMorphAvatarName", out object faceObj)
                    ? faceObj
                    : null);
            string earAddress = Str(
                npc.TryGetValue("earMorphAvatarName", out object earObj)
                    ? earObj
                    : null);
            bool npcDisableBlink = Bool(
                npc.TryGetValue("disableBlink", out object disableBlinkObj)
                    ? disableBlinkObj
                    : null);
            if (faceAddress.Length == 0)
                throw new InvalidOperationException(
                    $"Character NPC {characterId} has no facialMorphAvatarName.");

            // Resolve only the primary postmodel skeleton described by the
            // manifest. Generated model-variant subtrees intentionally repeat
            // the same bone names and must not receive the active avatar pose.
            IList transformManifest = manifest.TryGetValue(
                    "transforms", out object transformsObj)
                ? List(transformsObj)
                : manifest.TryGetValue("bones", out object bonesObj)
                    ? List(bonesObj)
                    : List(manifest.TryGetValue(
                            "scene_transforms", out object sceneTransformsObj)
                        ? sceneTransformsObj
                        : null);
            transformManifest = HighestQualityTransformManifest(transformManifest);
            var transformsByName = new Dictionary<string, List<Transform>>(StringComparer.Ordinal);
            foreach (object transformObj in transformManifest)
            {
                Dictionary<string, object> transformRow = Dict(transformObj);
                string path = Str(
                    transformRow.TryGetValue("path", out object pathObj)
                        ? pathObj
                        : null);
                Transform transform = path.Length == 0
                    ? root.transform
                    : root.transform.Find(path);
                if (transform == null)
                    continue;
                string name = Str(
                    transformRow.TryGetValue("name", out object nameObj)
                        ? nameObj
                        : null,
                    transform.name);
                if (!transformsByName.TryGetValue(name, out List<Transform> matches))
                {
                    matches = new List<Transform>();
                    transformsByName.Add(name, matches);
                }
                matches.Add(transform);
            }

            var bindings = new List<EndfieldRecoveredSkeletalMorphBoneBinding>();
            bool faceAvatarDisableBlink = AddRecoveredSkeletalMorphAvatarBindings(
                faceAddress,
                expectedDataType: 0,
                transformsByName,
                bindings);
            if (earAddress.Length > 0)
            {
                AddRecoveredSkeletalMorphAvatarBindings(
                    earAddress,
                    expectedDataType: 1,
                    transformsByName,
                    bindings);
            }

            EndfieldRecoveredSkeletalMorphBasePose component =
                root.GetComponent<EndfieldRecoveredSkeletalMorphBasePose>();
            if (component == null)
                component = root.AddComponent<EndfieldRecoveredSkeletalMorphBasePose>();
            component.characterId = characterId;
            component.npcDisableBlink = npcDisableBlink;
            component.automaticBlinkEligible = !npcDisableBlink && !faceAvatarDisableBlink;
            component.avatarAddresses = earAddress.Length > 0
                ? new[] { faceAddress, earAddress }
                : new[] { faceAddress };
            component.applyNeutralBasePoseEachFrame = true;
            component.bindings = bindings.ToArray();
            component.ApplyNeutralBasePose();
            EditorUtility.SetDirty(component);
            ConfigureRecoveredNamedFacialAnimation(root, characterId);
            ConfigureRecoveredAutomaticFacialBlink(root, characterId);
        }

        private static bool AddRecoveredSkeletalMorphAvatarBindings(
            string address,
            int expectedDataType,
            Dictionary<string, List<Transform>> transformsByName,
            List<EndfieldRecoveredSkeletalMorphBoneBinding> destination)
        {
            string[] addressParts = address.Replace('\\', '/').Split('/');
            if (addressParts.Length < 4)
                throw new InvalidOperationException(
                    $"Unexpected skeletal-morph avatar address: {address}");
            string prefix = expectedDataType == 0
                ? "data_facemorph_avatar_"
                : "data_earmorph_avatar_";
            string logicalName = prefix + addressParts[addressParts.Length - 1];
            string[] candidates = Directory.GetFiles(
                SkeletalMorphAvatarJsonRoot,
                logicalName + "_p*.json",
                SearchOption.TopDirectoryOnly);
            if (candidates.Length == 0)
            {
                candidates = Directory.GetFiles(
                    SkeletalMorphStreamingAvatarJsonRoot,
                    logicalName + "_p*.json",
                    SearchOption.TopDirectoryOnly);
            }
            if (candidates.Length != 1)
                throw new InvalidOperationException(
                    $"Expected exactly one installed avatar JSON for {address}; " +
                    $"found {candidates.Length} under the preferred Persistent root " +
                    $"{SkeletalMorphAvatarJsonRoot} or current StreamingAssets fallback " +
                    $"{SkeletalMorphStreamingAvatarJsonRoot}.");

            Dictionary<string, object> avatar = Dict(
                ManifestMiniJson.Deserialize(File.ReadAllText(candidates[0], Encoding.UTF8)));
            int dataType = Int(
                avatar.TryGetValue("dataType", out object dataTypeObj)
                    ? dataTypeObj
                    : null,
                -1);
            if (dataType != expectedDataType)
                throw new InvalidOperationException(
                    $"Avatar {address} dataType is {dataType}; expected {expectedDataType}.");

            Dictionary<string, object> data = Dict(
                avatar.TryGetValue("data", out object dataObj) ? dataObj : null);
            IList names = List(
                data.TryGetValue("allBoneNames", out object namesObj) ? namesObj : null);
            IList poses = List(
                data.TryGetValue("basePoseConfig", out object posesObj) ? posesObj : null);
            if (names.Count == 0 || names.Count != poses.Count)
                throw new InvalidOperationException(
                    $"Avatar {address} has invalid base pose arrays: " +
                    $"names={names.Count}, poses={poses.Count}.");

            for (int index = 0; index < names.Count; index++)
            {
                string boneName = Str(names[index]);
                if (!transformsByName.TryGetValue(
                        boneName,
                        out List<Transform> matches) ||
                    matches.Count != 1)
                {
                    throw new InvalidOperationException(
                        $"Avatar {address} bone '{boneName}' resolves to " +
                        $"{(matches == null ? 0 : matches.Count)} transforms on the imported rig.");
                }

                Dictionary<string, object> pose = Dict(poses[index]);
                destination.Add(new EndfieldRecoveredSkeletalMorphBoneBinding
                {
                    avatarAddress = address,
                    dataType = dataType,
                    boneId = Int(
                        pose.TryGetValue("boneID", out object boneIdObj)
                            ? boneIdObj
                            : null,
                        -1),
                    boneName = boneName,
                    target = matches[0],
                    localPosition = SkeletalMorphVector3(
                        Dict(pose.TryGetValue("position", out object positionObj)
                            ? positionObj
                            : null)),
                    localRotation = SkeletalMorphFromMaya(
                        SkeletalMorphVector3(
                            Dict(pose.TryGetValue("rotation", out object rotationObj)
                                ? rotationObj
                                : null))),
                    mayaEulerRotation = SkeletalMorphVector3(
                        Dict(pose.TryGetValue("rotation", out object mayaRotationObj)
                            ? mayaRotationObj
                            : null)),
                    localScale = SkeletalMorphVector3(
                        Dict(pose.TryGetValue("scale", out object scaleObj)
                            ? scaleObj
                            : null)),
                });
            }

            return Bool(
                avatar.TryGetValue("disableBlink", out object disableBlinkObj)
                    ? disableBlinkObj
                    : null);
        }

        private static Vector3 SkeletalMorphVector3(Dictionary<string, object> value)
        {
            return new Vector3(
                Float(value.TryGetValue("x", out object xObj) ? xObj : null),
                Float(value.TryGetValue("y", out object yObj) ? yObj : null),
                Float(value.TryGetValue("z", out object zObj) ? zObj : null));
        }

        private static Quaternion SkeletalMorphFromMaya(Vector3 eulerAngle)
        {
            // Retail Beyond.Gameplay.Core.SkeletalMorphUtils.FromMaya,
            // GameAssembly VA 0x187098dbc.
            Quaternion z = Quaternion.AngleAxis(-eulerAngle.z, Vector3.forward);
            Quaternion y = Quaternion.AngleAxis(-eulerAngle.y, Vector3.up);
            Quaternion x = Quaternion.AngleAxis(eulerAngle.x, Vector3.right);
            return z * y * x;
        }
    }
}
