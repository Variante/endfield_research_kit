using System;
using System.Linq;
using UnityEditor;
using UnityEngine;
using UnityEngine.Playables;
using EndfieldGraphShaderLab;

namespace EndfieldGraphShaderLabEditor
{
    public sealed class EndfieldGachaDirectorValidationPlayableAsset : PlayableAsset
    {
        public override double duration => 1.0;

        public override Playable CreatePlayable(PlayableGraph graph, GameObject owner)
        {
            return Playable.Create(graph);
        }
    }

    public static class EndfieldRecoveredGachaDirectorStartCoordinatorValidator
    {
        [MenuItem("Endfield/Character Recovery Lab/Validate Gacha Director Start Coordinator")]
        public static void ValidateMenu()
        {
            ValidateCommandLine();
        }

        public static void ValidateCommandLine()
        {
            GameObject root = new GameObject("RecoveredGachaDirectorCoordinatorValidation");
            EndfieldGachaDirectorValidationPlayableAsset actorAsset =
                ScriptableObject.CreateInstance<EndfieldGachaDirectorValidationPlayableAsset>();
            EndfieldGachaDirectorValidationPlayableAsset effectAsset =
                ScriptableObject.CreateInstance<EndfieldGachaDirectorValidationPlayableAsset>();
            EndfieldRecoveredEmptyGachaHelperPlayableAsset lightAsset =
                ScriptableObject.CreateInstance<EndfieldRecoveredEmptyGachaHelperPlayableAsset>();
            EndfieldRecoveredEmptyGachaHelperPlayableAsset othersAsset =
                ScriptableObject.CreateInstance<EndfieldRecoveredEmptyGachaHelperPlayableAsset>();
            try
            {
                PlayableDirector actor = CreateDirector(root, "Actor", actorAsset);
                PlayableDirector effect = CreateDirector(root, "Effect", effectAsset);
                PlayableDirector light = CreateDirector(root, "Light", lightAsset);
                PlayableDirector others = CreateDirector(root, "Others", othersAsset);
                var coordinator = new EndfieldRecoveredGachaDirectorStartCoordinator(
                    new[]
                    {
                        new EndfieldRecoveredGachaDirectorBinding
                        {
                            role = EndfieldRecoveredGachaDirectorRole.Effect,
                            sourceOrdinal = 2,
                            director = effect,
                        },
                        new EndfieldRecoveredGachaDirectorBinding
                        {
                            role = EndfieldRecoveredGachaDirectorRole.Actor,
                            sourceOrdinal = 0,
                            director = actor,
                        },
                        new EndfieldRecoveredGachaDirectorBinding
                        {
                            role = EndfieldRecoveredGachaDirectorRole.Light,
                            sourceOrdinal = 3,
                            director = light,
                        },
                        new EndfieldRecoveredGachaDirectorBinding
                        {
                            role = EndfieldRecoveredGachaDirectorRole.Others,
                            sourceOrdinal = 4,
                            director = others,
                        },
                    });

                Require(
                    coordinator.Admitted.Select(binding => binding.role).SequenceEqual(
                        new[]
                        {
                            EndfieldRecoveredGachaDirectorRole.Actor,
                            EndfieldRecoveredGachaDirectorRole.Effect,
                            EndfieldRecoveredGachaDirectorRole.Light,
                            EndfieldRecoveredGachaDirectorRole.Others,
                        }),
                    "Admitted Directors are not in recovered source order.");
                Require(
                    coordinator.Missing.SequenceEqual(new[]
                    {
                        EndfieldRecoveredGachaDirectorRole.Audio,
                    }),
                    "Missing helper roles are not preserved fail closed.");

                coordinator.SampleToBeginning();
                Require(
                    actor.time == 0.0 && effect.time == 0.0 &&
                    light.time == 0.0 && others.time == 0.0,
                    "SampleToBeginning did not evaluate every admitted Director at zero.");
                coordinator.PlayFromStart();
                Require(
                    actor.state == PlayState.Playing && effect.state == PlayState.Playing &&
                    actor.time == 0.0 && effect.time == 0.0 &&
                    light.time == 0.0 && others.time == 0.0,
                    "PlayFromStart did not start every admitted Director at zero.");
                coordinator.StopAll();
                Require(
                    actor.state != PlayState.Playing && effect.state != PlayState.Playing &&
                    light.state != PlayState.Playing && others.state != PlayState.Playing,
                    "StopAll left an admitted Director playing.");

                bool rejectedIdentityDirector = false;
                try
                {
                    _ = new EndfieldRecoveredGachaDirectorStartCoordinator(
                        new[]
                        {
                            new EndfieldRecoveredGachaDirectorBinding
                            {
                                role = EndfieldRecoveredGachaDirectorRole.Audio,
                                sourceOrdinal = 1,
                                director = null,
                            },
                        });
                }
                catch (ArgumentException)
                {
                    rejectedIdentityDirector = true;
                }
                Require(rejectedIdentityDirector,
                    "A missing Audio PlayableAsset did not fail closed.");

                int unityLightCountBefore =
                    root.GetComponentsInChildren<Light>(true).Length;
                GameObject cameraObject = new GameObject("PresentationCamera");
                cameraObject.transform.SetParent(root.transform, false);
                cameraObject.AddComponent<Camera>();
                EndfieldHGOperatorLightRig lightRig =
                    cameraObject.AddComponent<EndfieldHGOperatorLightRig>();
                lightRig.actorRoot = root.transform;
                lightRig.normalLightCompatibilityScale = 0f;
                lightRig.rimLightCompatibilityScale = 0f;
                EndfieldHGRPCharacterLightingVolume lightingVolume =
                    cameraObject.AddComponent<EndfieldHGRPCharacterLightingVolume>();
                EndfieldRecoveredZhuangfyGachaRuntime runtime =
                    root.AddComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
                runtime.autoStartRecoveredEffect = false;
                runtime.actorCameraDirector = actor;
                runtime.director = effect;
                runtime.BindSourceBackedPresentation(lightRig, lightingVolume);
                Vector4 exposureBefore = Shader.GetGlobalVector("_ExposureParams");
                Require(
                    !lightingVolume.enabled &&
                    !lightRig.sourceBackedClusteredNprLightLoop &&
                    !lightRig.sourceBackedLightBinningMembership &&
                    !lightRig.sourceBackedIsolatedPunctualSoftShadowProducer,
                    "Binding did not close the recovered presentation lifecycle.");
                Require(runtime.BeginRecoveredEffectStart(10f),
                    "Recovered presentation lifecycle rejected exact direct references.");
                Require(
                    lightingVolume.enabled &&
                    lightRig.sourceBackedClusteredNprLightLoop &&
                    lightRig.sourceBackedLightBinningMembership &&
                    !lightRig.sourceBackedIsolatedPunctualSoftShadowProducer,
                    "Begin did not open the exact clustered/binning presentation subset.");
                runtime.actorLoopStartTime = 0.5;
                int loopTransitions = 0;
                int triggerCount = 0;
                runtime.LoopTrackChanged += _ => loopTransitions++;
                runtime.SetRecoveredTriggerOnce(0.25, () => triggerCount++);
                actor.time = 0.6;
                runtime.TailTickRecoveredState();
                runtime.TailTickRecoveredState();
                Require(
                    runtime.InLoopTrack && loopTransitions == 1 && triggerCount == 1,
                    "Recovered TailTick did not enter loop and fire its callback exactly once.");
                actor.time = 0.0;
                runtime.TailTickRecoveredState();
                Require(!runtime.InLoopTrack && loopTransitions == 2 && triggerCount == 1,
                    "Recovered TailTick did not leave loop without repeating the callback.");
                runtime.EndRecoveredEffect();
                Require(
                    !lightingVolume.enabled &&
                    !lightRig.sourceBackedClusteredNprLightLoop &&
                    !lightRig.sourceBackedLightBinningMembership &&
                    !lightRig.sourceBackedIsolatedPunctualSoftShadowProducer &&
                    Shader.GetGlobalInt("_EndfieldOperatorLightCount") == 0 &&
                    Shader.GetGlobalFloat("_EndfieldRecoveredClusteredNprLightLoop") == 0f &&
                    Shader.GetGlobalFloat("_EndfieldRecoveredLightBinningAvailable") == 0f,
                    "End did not close all recovered presentation publication paths.");
                Require(
                    root.GetComponentsInChildren<Light>(true).Length == unityLightCountBefore,
                    "Recovered presentation lifecycle created a duplicate Unity Light.");
                Require(Shader.GetGlobalVector("_ExposureParams") == exposureBefore,
                    "Recovered presentation lifecycle reset exposure history.");

                Debug.Log(
                    "Recovered gacha Director start coordinator validation passed: " +
                    "Actor/Effect plus exact empty Light/Others admitted in source order; " +
                    "Audio missing; " +
                    "zero sample, two-stage play, TailTick state/callback, stop, " +
                    "missing-asset rejection, and " +
                    "source-backed lighting/Volume lifecycle passed.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(actorAsset);
                UnityEngine.Object.DestroyImmediate(effectAsset);
                UnityEngine.Object.DestroyImmediate(lightAsset);
                UnityEngine.Object.DestroyImmediate(othersAsset);
            }
        }

        private static PlayableDirector CreateDirector(
            GameObject root,
            string name,
            PlayableAsset asset)
        {
            GameObject owner = new GameObject(name);
            owner.transform.SetParent(root.transform, false);
            PlayableDirector director = owner.AddComponent<PlayableDirector>();
            director.playOnAwake = false;
            director.timeUpdateMode = DirectorUpdateMode.GameTime;
            director.playableAsset = asset;
            return director;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
