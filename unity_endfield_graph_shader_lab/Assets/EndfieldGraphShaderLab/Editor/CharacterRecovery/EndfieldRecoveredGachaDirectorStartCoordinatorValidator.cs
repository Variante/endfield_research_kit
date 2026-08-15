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
            EndfieldRecoveredGachaAudioPlayableAsset audioAsset =
                ScriptableObject.CreateInstance<EndfieldRecoveredGachaAudioPlayableAsset>();
            AudioClip overviewAudio = AudioClip.Create("256896424", 9688, 1, 1000, false);
            AudioClip rarityAudio = AudioClip.Create("787269389", 5287, 1, 1000, false);
            audioAsset.overviewClip = overviewAudio;
            audioAsset.rarityClip = rarityAudio;
            EndfieldRecoveredEmptyGachaHelperPlayableAsset lightAsset =
                ScriptableObject.CreateInstance<EndfieldRecoveredEmptyGachaHelperPlayableAsset>();
            EndfieldRecoveredEmptyGachaHelperPlayableAsset othersAsset =
                ScriptableObject.CreateInstance<EndfieldRecoveredEmptyGachaHelperPlayableAsset>();
            try
            {
                PlayableDirector actor = CreateDirector(root, "Actor", actorAsset);
                PlayableDirector audio = CreateDirector(root, "Audio", audioAsset);
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
                            role = EndfieldRecoveredGachaDirectorRole.Audio,
                            sourceOrdinal = 1,
                            director = audio,
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
                            EndfieldRecoveredGachaDirectorRole.Audio,
                            EndfieldRecoveredGachaDirectorRole.Effect,
                            EndfieldRecoveredGachaDirectorRole.Light,
                            EndfieldRecoveredGachaDirectorRole.Others,
                        }),
                    "Admitted Directors are not in recovered source order.");
                Require(!coordinator.Missing.Any(),
                    "A source-closed helper role is still marked missing.");

                coordinator.SampleToBeginning();
                Require(
                    actor.time == 0.0 && audio.time == 0.0 && effect.time == 0.0 &&
                    light.time == 0.0 && others.time == 0.0,
                    "SampleToBeginning did not evaluate every admitted Director at zero.");
                EndfieldRecoveredGachaAudioEmitter sampledEmitter =
                    audio.GetComponent<EndfieldRecoveredGachaAudioEmitter>();
                Require(sampledEmitter != null && sampledEmitter.PostCount == 0,
                    "Paused Audio Timeline sampling posted a Wwise event.");
                coordinator.PlayFromStart();
                Require(
                    actor.state == PlayState.Playing && audio.state == PlayState.Playing &&
                    effect.state == PlayState.Playing &&
                    actor.time == 0.0 && effect.time == 0.0 &&
                    light.time == 0.0 && others.time == 0.0,
                    "PlayFromStart did not start every admitted Director at zero.");
                Require(
                    audioAsset.duration ==
                        EndfieldRecoveredGachaAudioPlayableAsset.RarityStart +
                        EndfieldRecoveredGachaAudioPlayableAsset.RarityDuration &&
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventName ==
                        "Au_Gcaha_zhuangfy_overview" &&
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewEventHash == 0xee2a8301u &&
                    EndfieldRecoveredGachaAudioPlayableAsset.OverviewMediaId == 256896424u &&
                    EndfieldRecoveredGachaAudioPlayableAsset.RarityEventHash == 0xe347da7du &&
                    EndfieldRecoveredGachaAudioPlayableAsset.RarityMediaId == 787269389u,
                    "Recovered Audio Timeline identity/timing contract changed.");

                PlayableGraph audioGraph = PlayableGraph.Create("RecoveredGachaAudioValidation");
                try
                {
                    Playable audioPlayable = audioAsset.CreatePlayable(audioGraph, audio.gameObject);
                    sampledEmitter.PlaybackArmed = true;
                    audioGraph.Play();
                    audioGraph.Evaluate(0f);
                    Require(sampledEmitter.PostCount == 1 &&
                        sampledEmitter.LastEventHash == 0xee2a8301u &&
                        sampledEmitter.LastMediaId == 256896424u,
                        "Forward Audio playback did not post the exact overview event.");
                    audioPlayable.SetTime(5.0);
                    audioGraph.Evaluate(0f);
                    Require(sampledEmitter.PostCount == 1 &&
                        sampledEmitter.StopCount == 0,
                        "Audio clip end incorrectly stopped a stopEventAtClipEnd=false event.");
                    audioPlayable.SetTime(7.75);
                    audioGraph.Evaluate(0f);
                    Require(sampledEmitter.PostCount == 2 &&
                        sampledEmitter.LastEventHash == 0xe347da7du &&
                        sampledEmitter.LastMediaId == 787269389u,
                        "Forward Audio playback did not post the exact rarity event.");
                    audioGraph.Stop();
                    audioGraph.Evaluate(0f);
                }
                finally
                {
                    audioGraph.Destroy();
                }
                coordinator.StopAll();
                Require(sampledEmitter.StopCount == 1,
                    "Audio graph stop did not stop its active playing IDs.");
                Require(
                    actor.state != PlayState.Playing && audio.state != PlayState.Playing &&
                    effect.state != PlayState.Playing &&
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
                EndfieldRecoveredCharLightVolumeSnapshot volumeSnapshot =
                    cameraObject.AddComponent<EndfieldRecoveredCharLightVolumeSnapshot>();
                volumeSnapshot.charMainLightMultiplier.value = 2.25f;
                volumeSnapshot.charMainLightMultiplier.overrideState = false;
                volumeSnapshot.charMainLightRangeBias.value = -0.35f;
                volumeSnapshot.charMainLightRangeBias.overrideState = true;
                lightingVolume.enabled = false;
                EndfieldRecoveredZhuangfyGachaRuntime runtime =
                    root.AddComponent<EndfieldRecoveredZhuangfyGachaRuntime>();
                EndfieldRecoveredEnvironmentPhaseSnapshot gachaEnvironment =
                    root.AddComponent<EndfieldRecoveredEnvironmentPhaseSnapshot>();
                gachaEnvironment.ConfigureGachaRoom();
                GameObject charInfoEnvironmentObject =
                    new GameObject("CharacterInfoEnvironmentContract");
                charInfoEnvironmentObject.transform.SetParent(root.transform, false);
                EndfieldRecoveredEnvironmentPhaseSnapshot charInfoEnvironment =
                    charInfoEnvironmentObject.AddComponent<
                        EndfieldRecoveredEnvironmentPhaseSnapshot>();
                charInfoEnvironment.ConfigureCharacterInfo();
                Require(
                    gachaEnvironment.IsSourceClosed &&
                    charInfoEnvironment.IsSourceClosed &&
                    gachaEnvironment.phasePathId != charInfoEnvironment.phasePathId &&
                    Mathf.Approximately(gachaEnvironment.directIntensityDividePi, 0f) &&
                    Mathf.Approximately(
                        charInfoEnvironment.directIntensityDividePi,
                        2.7475471f) &&
                    Mathf.Approximately(gachaEnvironment.indirectDiffuseFactor, 1f) &&
                    Mathf.Approximately(
                        charInfoEnvironment.indirectDiffuseFactor,
                        0.28772247f),
                    "Scene-specific priority-600 environment phases were conflated.");
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
                Require(
                    volumeSnapshot.ApplyCount == 1 &&
                    Mathf.Approximately(lightingVolume.mainLightMultiplier, 0.9f) &&
                    Mathf.Approximately(lightingVolume.mainLightRangeBias, -0.35f) &&
                    lightingVolume.overrideMainLightRangeBias &&
                    lightingVolume.ignoreSceneEnvironment,
                    "Begin did not resolve GachaRoom priority 30000 then the raw " +
                    "priority-30001 character snapshot exactly once.");
                volumeSnapshot.charMainLightMultiplier.value = 3.5f;
                runtime.AdvanceRecoveredEffectStart(10.25f);
                Require(
                    volumeSnapshot.ApplyCount == 1 &&
                    Mathf.Approximately(lightingVolume.mainLightMultiplier, 0.9f),
                    "Delayed play retained or replayed the raw Volume modifier source.");
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
                    "Actor/Audio/Effect plus exact empty Light/Others admitted in source order; " +
                    "Audio event-media timing and silent zero sample passed; " +
                    "zero sample, two-stage play, TailTick state/callback, stop, " +
                    "missing-asset rejection, one-shot 30-field Volume snapshot, and " +
                    "source-backed lighting/Volume lifecycle passed.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(actorAsset);
                UnityEngine.Object.DestroyImmediate(effectAsset);
                UnityEngine.Object.DestroyImmediate(audioAsset);
                UnityEngine.Object.DestroyImmediate(overviewAudio);
                UnityEngine.Object.DestroyImmediate(rarityAudio);
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
