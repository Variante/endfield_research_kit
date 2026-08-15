using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;
using EndfieldGraphShaderLab;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldRosterAnimationSwitchValidator
    {
        private const string PlayableRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable";
        private const float PositionTolerance = 0.00001f;
        private const float RotationToleranceDegrees = 0.01f;
        private const float ScaleTolerance = 0.00001f;

        [MenuItem("Endfield/Character Recovery Lab/Validate Roster Animation Switching")]
        public static void ValidateMenu()
        {
            Validate();
        }

        public static void ValidateCommandLine()
        {
            Validate();
        }

        private static void Validate()
        {
            string projectRoot = Directory.GetParent(Application.dataPath).FullName;
            string manifestRoot = Path.Combine(projectRoot, PlayableRoot.Replace('/', Path.DirectorySeparatorChar));
            string[] manifestPaths = Directory.GetFiles(
                manifestRoot,
                "*_ui_recovery_manifest.json",
                SearchOption.AllDirectories);
            Array.Sort(manifestPaths, StringComparer.OrdinalIgnoreCase);
            if (manifestPaths.Length == 0)
                throw new InvalidOperationException("No playable manifests were found for roster validation.");

            int actorCount = 0;
            int clipCount = 0;
            int contaminatedTransitionCount = 0;
            int staleTransformCount = 0;
            int overviewOwnershipCount = 0;
            int overviewSelectionRestartCount = 0;
            int overviewHandoffCount = 0;
            foreach (string manifestPath in manifestPaths)
            {
                Manifest manifest = JsonUtility.FromJson<Manifest>(File.ReadAllText(manifestPath));
                if (manifest == null || manifest.clips == null)
                    throw new InvalidOperationException($"Could not parse animation clips: {manifestPath}");
                string actor = new DirectoryInfo(Path.GetDirectoryName(manifestPath)).Name;
                string prefabPath = $"{PlayableRoot}/{actor}/Prefabs/{actor}.prefab";
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(prefabPath);
                if (prefab == null)
                    throw new InvalidOperationException($"Missing generated prefab: {prefabPath}");

                GameObject instance = PrefabUtility.InstantiatePrefab(prefab) as GameObject;
                if (instance == null)
                    throw new InvalidOperationException($"Could not instantiate generated prefab: {prefabPath}");
                try
                {
                    Animation animation = instance.GetComponent<Animation>();
                    CharacterAnimationReferencePose provider =
                        instance.GetComponent<CharacterAnimationReferencePose>();
                    if (animation == null || provider == null)
                    {
                        throw new InvalidOperationException(
                            $"{actor}: regenerated prefab lacks Animation or Awake-time reference-pose provider.");
                    }

                    EndfieldOverviewPlayback overview = instance.GetComponent<EndfieldOverviewPlayback>();
                    if (overview != null)
                    {
                        if (!overview.enabled || !overview.playOnEnable)
                            throw new InvalidOperationException($"{actor}: initial Overview ownership is disabled.");
                        overview.CancelForManualPlayback();
                        if (overview.enabled || overview.playOnEnable || overview.IsTransitioning || overview.IsLooping)
                            throw new InvalidOperationException($"{actor}: manual Overview cancellation is incomplete.");

                        overview.RestartOverviewFromSelection();
                        AnimationState selectedStartState = animation[overview.startClip];
                        if (!overview.enabled || !overview.playOnEnable || selectedStartState == null)
                        {
                            throw new InvalidOperationException(
                                $"{actor}: selection did not restore Overview entrance ownership.");
                        }
                        float expectedStartTime =
                            Mathf.Clamp01(overview.entryNormalizedOffset) * selectedStartState.length;
                        if (Mathf.Abs(selectedStartState.time - expectedStartTime) > 0.00001f)
                        {
                            throw new InvalidOperationException(
                                $"{actor}: selection restarted {overview.startClip} at " +
                                $"{selectedStartState.time:R}, expected {expectedStartTime:R}.");
                        }
                        overviewSelectionRestartCount++;
                        overview.CancelForManualPlayback();
                        overviewOwnershipCount++;
                    }

                    List<ManifestClip> bodyClips = manifest.clips
                        .Where(clip => clip != null && string.IsNullOrEmpty(clip.widget_prefab))
                        .OrderByDescending(ChannelCount)
                        .ThenBy(clip => clip.name, StringComparer.Ordinal)
                        .ToList();
                    if (bodyClips.Count == 0)
                        throw new InvalidOperationException($"{actor}: manifest has no body clips.");
                    foreach (ManifestClip clip in bodyClips)
                    {
                        if (animation[clip.name] == null)
                            throw new InvalidOperationException($"{actor}: prefab is missing body clip {clip.name}.");
                    }

                    CharacterLocalPoseSnapshot referencePose = provider.Snapshot;
                    int transformCount = instance.GetComponentsInChildren<Transform>(true).Length;
                    if (referencePose.Count != transformCount)
                    {
                        throw new InvalidOperationException(
                            $"{actor}: reference pose captured {referencePose.Count}/{transformCount} transforms.");
                    }
                    foreach (ManifestClip target in bodyClips)
                    {
                        HashSet<string> targetChannels = ChannelSet(target);
                        ManifestClip source = bodyClips
                            .Where(candidate => candidate != target)
                            .OrderByDescending(candidate =>
                            {
                                HashSet<string> sourceChannels = ChannelSet(candidate);
                                sourceChannels.ExceptWith(targetChannels);
                                return sourceChannels.Count;
                            })
                            .ThenBy(candidate => candidate.name, StringComparer.Ordinal)
                            .FirstOrDefault();
                        if (source == null)
                            throw new InvalidOperationException($"{actor}: cannot select a contamination clip.");
                        AnimationState sourceState = animation[source.name];
                        AnimationState targetState = animation[target.name];
                        float sourceTime = sourceState.length * 0.83f;
                        float targetTime = targetState.length * 0.47f;

                        referencePose.Restore();
                        SampleSingle(animation, targetState, targetTime);
                        Dictionary<string, LocalPose> fresh = CapturePose(instance.transform);

                        referencePose.Restore();
                        SampleSingle(animation, sourceState, sourceTime);
                        SampleSingle(animation, targetState, targetTime);
                        Dictionary<string, LocalPose> leaked = CapturePose(instance.transform);
                        int leakedTransforms = CountMismatches(fresh, leaked);
                        if (leakedTransforms > 0)
                        {
                            contaminatedTransitionCount++;
                            staleTransformCount += leakedTransforms;
                        }

                        referencePose.Restore();
                        SampleSingle(animation, targetState, targetTime);
                        Dictionary<string, LocalPose> reset = CapturePose(instance.transform);
                        int resetMismatches = CountMismatches(fresh, reset);
                        if (resetMismatches != 0)
                        {
                            throw new InvalidOperationException(
                                $"{actor}/{target.name}: reset sample differs from fresh sample on " +
                                $"{resetMismatches} transforms.");
                        }
                        clipCount++;
                    }

                    var allClipsByName = manifest.clips
                        .Where(clip => clip != null && !string.IsNullOrEmpty(clip.name))
                        .ToDictionary(clip => clip.name, StringComparer.Ordinal);
                    foreach (ManifestClip loopClip in manifest.clips)
                    {
                        if (loopClip == null || string.IsNullOrEmpty(loopClip.name))
                            continue;
                        string startName = OverviewStartName(loopClip.name);
                        if (string.IsNullOrEmpty(startName))
                            continue;
                        if (!allClipsByName.ContainsKey(startName))
                            continue;
                        AnimationState startState = animation[startName];
                        AnimationState loopState = animation[loopClip.name];
                        if (startState == null || loopState == null)
                        {
                            throw new InvalidOperationException(
                                $"{actor}: generated Overview handoff clips are missing: {startName} -> {loopClip.name}.");
                        }

                        referencePose.Restore();
                        SampleSingle(animation, loopState, loopState.length * 0.47f);
                        Dictionary<string, LocalPose> freshLoop = CapturePose(instance.transform);
                        referencePose.Restore();
                        SampleSingle(animation, startState, startState.length);
                        SampleSingle(animation, loopState, loopState.length * 0.47f);
                        Dictionary<string, LocalPose> handedOffLoop = CapturePose(instance.transform);
                        int handoffMismatches = CountMismatches(freshLoop, handedOffLoop);
                        if (handoffMismatches != 0)
                        {
                            throw new InvalidOperationException(
                                $"{actor}: Overview handoff {startName} -> {loopClip.name} retains " +
                                $"{handoffMismatches} start-only transforms.");
                        }
                        overviewHandoffCount++;
                    }
                    actorCount++;
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(instance);
                }
            }

            if (actorCount != manifestPaths.Length || clipCount == 0)
                throw new InvalidOperationException($"Incomplete roster validation: actors={actorCount}, clips={clipCount}.");
            Debug.Log(
                $"Roster animation switch validation passed: actors={actorCount}, body clips={clipCount}, " +
                $"contaminated source->target probes={contaminatedTransitionCount}, " +
                $"stale transforms prevented={staleTransformCount}, " +
                $"post-reset mismatches=0, Overview ownership checks={overviewOwnershipCount}, " +
                $"selection restarts={overviewSelectionRestartCount}, " +
                $"start->loop handoffs={overviewHandoffCount}.");
        }

        private static int ChannelCount(ManifestClip clip)
        {
            if (clip == null || clip.bones == null)
                return 0;
            int count = 0;
            foreach (ManifestBone bone in clip.bones)
            {
                if (bone == null)
                    continue;
                count += bone.pos_animated ? 1 : 0;
                count += bone.rot_animated ? 1 : 0;
                count += bone.scale_animated ? 1 : 0;
            }
            return count;
        }

        private static HashSet<string> ChannelSet(ManifestClip clip)
        {
            var result = new HashSet<string>(StringComparer.Ordinal);
            if (clip == null || clip.bones == null)
                return result;
            foreach (ManifestBone bone in clip.bones)
            {
                if (bone == null || string.IsNullOrEmpty(bone.path))
                    continue;
                if (bone.pos_animated) result.Add(bone.path + "|p");
                if (bone.rot_animated) result.Add(bone.path + "|r");
                if (bone.scale_animated) result.Add(bone.path + "|s");
            }
            return result;
        }

        private static string OverviewStartName(string loopName)
        {
            const string LoopToken = "_overview_loop_";
            const string TerminalLoopToken = "_overview_loop";
            int tokenIndex = loopName.IndexOf(LoopToken, StringComparison.OrdinalIgnoreCase);
            if (tokenIndex >= 0)
            {
                return loopName.Substring(0, tokenIndex) +
                    "_overview_start_" +
                    loopName.Substring(tokenIndex + LoopToken.Length);
            }
            if (loopName.EndsWith(TerminalLoopToken, StringComparison.OrdinalIgnoreCase))
            {
                return loopName.Substring(0, loopName.Length - TerminalLoopToken.Length) +
                    "_overview_start";
            }
            return string.Empty;
        }

        private static void SampleSingle(Animation animation, AnimationState state, float time)
        {
            animation.Stop();
            state.layer = 0;
            state.blendMode = AnimationBlendMode.Blend;
            state.weight = 1f;
            state.wrapMode = WrapMode.Once;
            state.speed = 0f;
            state.time = Mathf.Clamp(time, 0f, state.length);
            state.enabled = true;
            animation.Sample();
        }

        private static Dictionary<string, LocalPose> CapturePose(Transform root)
        {
            var result = new Dictionary<string, LocalPose>(StringComparer.Ordinal);
            foreach (Transform current in root.GetComponentsInChildren<Transform>(true))
            {
                string path = current == root
                    ? "<root>"
                    : AnimationUtility.CalculateTransformPath(current, root);
                result[path] = new LocalPose
                {
                    position = current.localPosition,
                    rotation = current.localRotation,
                    scale = current.localScale,
                    activeSelf = current.gameObject.activeSelf,
                };
            }
            return result;
        }

        private static int CountMismatches(
            Dictionary<string, LocalPose> expected,
            Dictionary<string, LocalPose> actual)
        {
            int count = 0;
            foreach (KeyValuePair<string, LocalPose> pair in expected)
            {
                if (!actual.TryGetValue(pair.Key, out LocalPose value) ||
                    Vector3.Distance(pair.Value.position, value.position) > PositionTolerance ||
                    Quaternion.Angle(pair.Value.rotation, value.rotation) > RotationToleranceDegrees ||
                    Vector3.Distance(pair.Value.scale, value.scale) > ScaleTolerance ||
                    pair.Value.activeSelf != value.activeSelf)
                {
                    count++;
                }
            }
            return count;
        }

        [Serializable]
        private sealed class Manifest
        {
            public ManifestClip[] clips;
        }

        [Serializable]
        private sealed class ManifestClip
        {
            public string name;
            public string widget_prefab;
            public ManifestBone[] bones;
        }

        [Serializable]
        private sealed class ManifestBone
        {
            public bool pos_animated;
            public bool rot_animated;
            public bool scale_animated;
            public string path;
        }

        private struct LocalPose
        {
            public Vector3 position;
            public Quaternion rotation;
            public Vector3 scale;
            public bool activeSelf;
        }
    }
}
