using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Captures a deterministic, actor-only Overview sequence from the
    /// recovered prefab. This is intentionally separate from the single-image
    /// viewer renderers: it does not alter their default backdrop or saved
    /// scene, and it never claims that an alpha readback is a verified matte.
    ///
    /// Select actors with ENDFIELD_OVERVIEW_CAPTURE_ACTOR (comma separated),
    /// choose a sampling rate with ENDFIELD_OVERVIEW_CAPTURE_FPS, and choose
    /// an output root with ENDFIELD_OVERVIEW_CAPTURE_OUTPUT. The default actor
    /// set is the current recovery priority: Endminf, Pelica, and Chen.
    /// </summary>
    public static class EndfieldOverviewCharacterSequenceCapture
    {
        private const string ViewerScenePath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/" +
            "CharacterRecoveryViewer.unity";
        private const string PlayableRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable";
        private const string DefaultOutputDirectory =
            "scratch/character_recovery/overview_capture";
        private const string ActorEnvironmentVariable =
            "ENDFIELD_OVERVIEW_CAPTURE_ACTOR";
        private const string FpsEnvironmentVariable =
            "ENDFIELD_OVERVIEW_CAPTURE_FPS";
        private const string OutputEnvironmentVariable =
            "ENDFIELD_OVERVIEW_CAPTURE_OUTPUT";
        private const int DefaultFps = 10;
        private const int DefaultWidth = 1920;
        private const int DefaultHeight = 1080;
        private const string CapturePathContract =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/" +
            "CharInfoPresentation/charinfo_overview_camera_contract.json";
        private const string SecondaryDynamicsContract =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/" +
            "CharInfoPresentation/secondary_dynamics_owner_recovery.json";

        [Serializable]
        private sealed class CaptureClip
        {
            public string name = "";
            public string role = "";
            public float duration_seconds;
            public int frame_count;
            public float sequence_start_seconds;
            public float sequence_end_seconds;
            public int loop_cycles;
        }

        [Serializable]
        private sealed class CaptureFrame
        {
            public int index;
            public string file = "";
            public string phase = "";
            public string clip = "";
            public float timestamp_seconds;
            public float clip_time_seconds;
            public float phase_seconds;
            public float phase_normalized;
            public AlphaFrameAudit alpha_audit;
        }

        [Serializable]
        private sealed class AlphaFrameAudit
        {
            public int width;
            public int height;
            public int transparent_pixels;
            public int nontransparent_pixels;
            public byte minimum_alpha;
            public byte maximum_alpha;
            public bool transparent_clear_observed;
        }

        [Serializable]
        private sealed class AlphaAudit
        {
            public bool transparent_clear_requested = true;
            public bool alpha_readback_observed;
            public bool matte_verified = false;
            public int frame_count;
            public int frames_with_transparent_pixels;
            public int frames_with_nontransparent_pixels;
            public byte minimum_alpha = 255;
            public byte maximum_alpha;
            public string verdict =
                "alpha readback is an audit only; no independent character matte " +
                "was verified";
        }

        [Serializable]
        private sealed class CameraContract
        {
            public string path = CapturePathContract;
            public string actor = "";
            public string template_id = "";
            public string track = "";
            public float[] camera_position = Array.Empty<float>();
            public float[] look_at_position = Array.Empty<float>();
            public float[] serialized_vcam_rotation = Array.Empty<float>();
            public float field_of_view;
            public float near_clip_plane;
            public float far_clip_plane;
        }

        [Serializable]
        private sealed class CaptureSidecar
        {
            public int schema_version = 1;
            public string status = "running";
            public string actor = "";
            public string prefab = "";
            public string scene = ViewerScenePath;
            public string phase = "ui_overview_start_then_ui_overview_loop";
            public string sampling_mode = "source_clip_duration_at_fixed_fps";
            public int fps;
            public int width = DefaultWidth;
            public int height = DefaultHeight;
            public string output_directory = "";
            public string sidecar = "";
            public string transition_mode = "state_weighted_crossfade_sample";
            public float controller_exit_normalized_time;
            public float controller_transition_seconds;
            public bool transparent_clear_requested = true;
            public bool transparent_pipeline_override_applied;
            public bool transparent_post_process_disabled = true;
            public bool reference_backdrop_disabled;
            public bool non_actor_renderers_disabled;
            public bool non_actor_ui_disabled;
            public bool actor_props_disabled;
            public bool matte_verified = false;
            public bool secondary_dynamics_verified = false;
            public string secondary_dynamics_contract = SecondaryDynamicsContract;
            public EndfieldSecondaryDynamicsOwnerContract.BindingAudit
                secondary_dynamics_owner_binding;
            public string render_fidelity_status =
                "incomplete_missing_retail_secondary_dynamics_solver";
            public CaptureClip[] clips = Array.Empty<CaptureClip>();
            public CameraContract camera_contract;
            public AlphaAudit alpha_audit = new AlphaAudit();
            public CaptureFrame[] frames = Array.Empty<CaptureFrame>();
            public string[] limitations = Array.Empty<string>();
            public string error = "";
        }

        private sealed class FramePlan
        {
            public string Phase = "";
            public AnimationClip Clip;
            public string ClipName = "";
            public float Timestamp;
            public float ClipTime;
            public float PhaseSeconds;
            public float PhaseNormalized;
            public float TransitionElapsed;
            public float TransitionNormalized;
        }

        private sealed class CaptureEnvironmentSnapshot
        {
            public string ActiveScenePath = "";
            public RenderPipelineAsset GraphicsPipeline;
            public RenderPipelineAsset QualityPipeline;
            public Material Skybox;
        }

        private sealed class PipelineVisualSnapshot
        {
            private readonly HGCompatRenderPipelineAsset asset;
            private readonly Color clearColor;
            private readonly bool drawSkybox;
            private readonly bool applyCharacterPostProcess;

            public PipelineVisualSnapshot(HGCompatRenderPipelineAsset asset)
            {
                this.asset = asset ?? throw new ArgumentNullException(nameof(asset));
                clearColor = asset.clearColor;
                drawSkybox = asset.drawSkybox;
                applyCharacterPostProcess = asset.applyCharacterPostProcess;
            }

            public void ApplyTransparentPass()
            {
                asset.clearColor = Color.clear;
                asset.drawSkybox = false;
                // Post processing can write an opaque color over a transparent
                // clear. The transparent beauty pass intentionally excludes it;
                // the sidecar records this limitation explicitly.
                asset.applyCharacterPostProcess = false;
            }

            public void Restore()
            {
                asset.clearColor = clearColor;
                asset.drawSkybox = drawSkybox;
                asset.applyCharacterPostProcess = applyCharacterPostProcess;
                if (asset.clearColor != clearColor ||
                    asset.drawSkybox != drawSkybox ||
                    asset.applyCharacterPostProcess != applyCharacterPostProcess)
                {
                    throw new InvalidOperationException(
                        "Could not safely restore HGCompatRenderPipelineAsset " +
                        "transparent-pass settings.");
                }
            }
        }

        [MenuItem(
            "Endfield/Character Recovery Lab/Capture Actor-Only Overview Sequence")]
        public static void CaptureActorOnlyOverviewSequence()
        {
            string outputRoot = ResolveOutputRoot();
            int fps = ResolveFps();
            string[] actorNames = ResolveActors();
            var failures = new List<string>();

            if (actorNames.Length == 0)
                throw new InvalidOperationException(
                    "No actor selected. Set " + ActorEnvironmentVariable +
                    " to one or more generated Playable actor roots.");

            // Opening the generated viewer and changing global pipeline/scene
            // state is only safe when the caller's scene can be reopened.
            // Reject an untitled or dirty scene rather than pretending it can
            // be restored after a long capture.
            CaptureEnvironmentSnapshot environment = SnapshotEnvironment();
            try
            {
                EnsureSourceSceneExists();
                EnsurePipelineAndOpenViewer();
                foreach (string actorName in actorNames)
                {
                    try
                    {
                        CaptureActor(actorName, fps, outputRoot);
                    }
                    catch (Exception exception)
                    {
                        failures.Add(actorName + ": " + exception.Message);
                        Debug.LogError(
                            "Actor-only Overview capture failed for " +
                            actorName + ": " + exception);
                    }
                }
            }
            finally
            {
                // The capture deliberately edits only the opened scene. Do not
                // save it; reopening guarantees the ordinary viewer is restored
                // after backdrop/UI isolation or a failed actor.
                try
                {
                    RestoreEnvironment(environment);
                }
                catch (Exception exception)
                {
                    failures.Add("capture environment restore failed: " + exception.Message);
                }
            }

            if (failures.Count > 0)
            {
                throw new InvalidOperationException(
                    "Actor-only Overview capture completed with failures:\n" +
                    string.Join("\n", failures.ToArray()));
            }

            Debug.Log(
                "Actor-only Overview capture completed: actors=" +
                string.Join(",", actorNames) + ", fps=" + fps + ", output=" +
                outputRoot);
        }

        private static CaptureEnvironmentSnapshot SnapshotEnvironment()
        {
            Scene activeScene = SceneManager.GetActiveScene();
            if (Application.isBatchMode &&
                (!activeScene.IsValid() || string.IsNullOrWhiteSpace(activeScene.path)))
            {
                return new CaptureEnvironmentSnapshot
                {
                    ActiveScenePath = "",
                    GraphicsPipeline = GraphicsSettings.renderPipelineAsset,
                    QualityPipeline = QualitySettings.renderPipeline,
                    Skybox = RenderSettings.skybox,
                };
            }
            if (!activeScene.IsValid() || string.IsNullOrWhiteSpace(activeScene.path))
            {
                throw new InvalidOperationException(
                    "Capture refused: the active scene is untitled or invalid; " +
                    "it cannot be safely restored after capture.");
            }
            if (activeScene.isDirty)
            {
                throw new InvalidOperationException(
                    "Capture refused: the active scene has unsaved changes; " +
                    "it cannot be safely restored without overwriting or losing them.");
            }
            string absolutePath = Path.Combine(
                Directory.GetCurrentDirectory(), activeScene.path);
            if (!File.Exists(absolutePath))
            {
                throw new FileNotFoundException(
                    "Capture refused: the active scene path cannot be reopened safely.",
                    activeScene.path);
            }
            return new CaptureEnvironmentSnapshot
            {
                ActiveScenePath = activeScene.path,
                GraphicsPipeline = GraphicsSettings.renderPipelineAsset,
                QualityPipeline = QualitySettings.renderPipeline,
                Skybox = RenderSettings.skybox,
            };
        }

        private static void RestoreEnvironment(CaptureEnvironmentSnapshot snapshot)
        {
            if (snapshot == null)
                throw new InvalidOperationException(
                    "Capture environment snapshot was missing; scene restoration is unsafe.");

            if (!string.IsNullOrWhiteSpace(snapshot.ActiveScenePath))
            {
                Scene activeScene = SceneManager.GetActiveScene();
                if (!activeScene.IsValid() ||
                    !string.Equals(activeScene.path, snapshot.ActiveScenePath,
                        StringComparison.OrdinalIgnoreCase))
                {
                    EditorSceneManager.OpenScene(
                        snapshot.ActiveScenePath,
                        OpenSceneMode.Single);
                }
            }

            GraphicsSettings.renderPipelineAsset = snapshot.GraphicsPipeline;
            QualitySettings.renderPipeline = snapshot.QualityPipeline;
            RenderSettings.skybox = snapshot.Skybox;

            Scene restoredScene = SceneManager.GetActiveScene();
            if ((!string.IsNullOrWhiteSpace(snapshot.ActiveScenePath) &&
                 !string.Equals(restoredScene.path, snapshot.ActiveScenePath,
                     StringComparison.OrdinalIgnoreCase)) ||
                GraphicsSettings.renderPipelineAsset != snapshot.GraphicsPipeline ||
                QualitySettings.renderPipeline != snapshot.QualityPipeline ||
                RenderSettings.skybox != snapshot.Skybox)
            {
                throw new InvalidOperationException(
                    "Capture environment restoration did not reproduce the saved " +
                    "active scene path, GraphicsSettings/QualitySettings pipeline, " +
                    "and RenderSettings.skybox.");
            }
        }

        private static void CaptureActor(
            string requestedActor,
            int fps,
            string outputRoot)
        {
            GameObject prefab = LoadActorPrefab(requestedActor);
            string actorName = prefab.name;
            string actorOutput = Path.Combine(outputRoot, actorName);
            string sidecarPath = Path.Combine(
                actorOutput,
                actorName + "_overview_capture.json");
            ClearPreviousFrames(actorOutput, sidecarPath);

            var sidecar = new CaptureSidecar
            {
                status = "running",
                actor = actorName,
                prefab = AssetDatabase.GetAssetPath(prefab),
                fps = fps,
                output_directory = actorOutput,
                sidecar = sidecarPath,
                limitations = CaptureLimitations(),
            };

            GameObject actor = null;
            try
            {
                Scene scene = EditorSceneManager.GetActiveScene();
                Transform charactersRoot = FindSceneObject("Characters")?.transform;
                if (charactersRoot == null)
                    throw new InvalidOperationException(
                        "CharacterRecoveryViewer has no Characters root.");

                actor = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actor == null)
                    throw new InvalidOperationException(
                        "Could not instantiate actor prefab: " +
                        AssetDatabase.GetAssetPath(prefab));
                actor.name = actorName;
                actor.transform.SetParent(charactersRoot, false);
                foreach (Transform child in charactersRoot)
                {
                    if (child != null)
                        child.gameObject.SetActive(child.gameObject == actor);
                }
                actor.transform.SetPositionAndRotation(Vector3.zero, Quaternion.identity);
                actor.transform.localScale = Vector3.one;
                actor.SetActive(true);
                Animation animation = actor.GetComponent<Animation>() ??
                    actor.GetComponentInChildren<Animation>(true);
                EndfieldOverviewPlayback playback =
                    actor.GetComponent<EndfieldOverviewPlayback>() ??
                    actor.GetComponentInChildren<EndfieldOverviewPlayback>(true);
                if (animation == null || playback == null)
                    throw new InvalidDataException(
                        "Actor has no Animation/EndfieldOverviewPlayback: " + actorName);
                sidecar.secondary_dynamics_owner_binding =
                    EndfieldSecondaryDynamicsOwnerContract.Verify(
                        actor,
                        actorName,
                        SecondaryDynamicsContract);

                AnimationClip startClip = ResolveClip(animation, playback.startClip);
                AnimationClip loopClip = ResolveClip(animation, playback.loopClip);
                if (startClip.length <= 0f || loopClip.length <= 0f)
                    throw new InvalidDataException(
                        "Overview source clip duration is non-positive for " + actorName);

                Camera camera = Camera.main ??
                    UnityEngine.Object.FindObjectOfType<Camera>(true);
                if (camera == null)
                    throw new InvalidOperationException(
                        "CharacterRecoveryViewer has no camera.");

                sidecar.camera_contract = BuildCameraContract(actorName);
                float exitSeconds = ResolveExitSeconds(
                    playback.exitNormalizedTime,
                    startClip.length);
                float transitionSeconds = ResolveTransitionSeconds(
                    playback,
                    startClip.length);
                sidecar.controller_exit_normalized_time = playback.exitNormalizedTime;
                sidecar.controller_transition_seconds = transitionSeconds;

                ConfigureActorOnlyScene(
                    scene,
                    actor,
                    camera,
                    actorName,
                    out bool backdropDisabled,
                    out bool externalRendererIsolation,
                    out bool externalUiIsolation,
                    out bool actorPropsDisabled);
                sidecar.reference_backdrop_disabled = backdropDisabled;
                sidecar.non_actor_renderers_disabled = externalRendererIsolation;
                sidecar.non_actor_ui_disabled = externalUiIsolation;
                sidecar.actor_props_disabled = actorPropsDisabled;

                playback.CancelForManualPlayback();
                playback.ApplyRecoveredParametersNow();
                animation.playAutomatically = false;
                animation.Stop();

                List<FramePlan> plan = BuildFramePlan(
                    startClip,
                    loopClip,
                    fps,
                    exitSeconds,
                    transitionSeconds,
                    playback.destinationNormalizedOffset);
                sidecar.clips = BuildClipRecords(
                    startClip,
                    loopClip,
                    fps,
                    plan,
                    exitSeconds,
                    transitionSeconds);
                var frames = new List<CaptureFrame>(plan.Count);
                var alphaSummary = new AlphaAudit
                {
                    transparent_clear_requested = true,
                    matte_verified = false,
                };
                HGCompatRenderPipelineAsset pipeline =
                    AssetDatabase.LoadAssetAtPath<HGCompatRenderPipelineAsset>(
                        "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset");
                if (pipeline == null)
                    throw new FileNotFoundException(
                        "HG compatibility render pipeline is missing for transparent capture.",
                        "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset");

                Exception frameCaptureFailure = null;
                PipelineVisualSnapshot transparentPipeline =
                    new PipelineVisualSnapshot(pipeline);
                try
                {
                    transparentPipeline.ApplyTransparentPass();
                    sidecar.transparent_pipeline_override_applied = true;
                    for (int index = 0; index < plan.Count; index++)
                    {
                        FramePlan sample = plan[index];
                        SampleFrame(
                            animation,
                            startClip,
                            loopClip,
                            playback,
                            exitSeconds,
                            sample);
                        CharacterProceduralIk poseCorrection =
                            actor.GetComponent<CharacterProceduralIk>() ??
                            actor.GetComponentInChildren<CharacterProceduralIk>(true);
                        if (poseCorrection != null)
                            poseCorrection.Evaluate();
                        // Active curves can re-enable a private widget after a
                        // sample. Re-apply this gate on every frame, not only once.
                        actorPropsDisabled = DisableActorProps(actor);

                        string fileName = "frame_" + index.ToString("D6", CultureInfo.InvariantCulture) + ".png";
                        string filePath = Path.Combine(actorOutput, fileName);
                        AlphaFrameAudit alpha = RenderTransparentFrame(
                            camera,
                            filePath,
                            DefaultWidth,
                            DefaultHeight);
                        AccumulateAlphaAudit(alphaSummary, alpha);
                        frames.Add(new CaptureFrame
                        {
                            index = index,
                            file = fileName,
                            phase = sample.Phase,
                            clip = sample.ClipName,
                            timestamp_seconds = sample.Timestamp,
                            clip_time_seconds = sample.ClipTime,
                            phase_seconds = sample.PhaseSeconds,
                            phase_normalized = sample.PhaseNormalized,
                            alpha_audit = alpha,
                        });
                        // Persist progress before the fail-closed check so a
                        // failed sidecar still explains which frame was bad.
                        sidecar.frames = frames.ToArray();
                        sidecar.alpha_audit = alphaSummary;
                        if (alpha.transparent_pixels <= 0 ||
                            alpha.nontransparent_pixels <= 0)
                        {
                            throw new InvalidDataException(
                                "Transparent capture frame " + index + " has " +
                                alpha.transparent_pixels + " transparent and " +
                                alpha.nontransparent_pixels + " non-transparent pixels; " +
                                "capture is fail-closed.");
                        }
                    }
                }
                catch (Exception exception)
                {
                    frameCaptureFailure = exception;
                }
                finally
                {
                    try
                    {
                        transparentPipeline.Restore();
                    }
                    catch (Exception exception)
                    {
                        frameCaptureFailure = frameCaptureFailure == null
                            ? exception
                            : new InvalidOperationException(
                                "Transparent pipeline capture failed and its settings " +
                                "could not be restored.",
                                new AggregateException(frameCaptureFailure, exception));
                    }
                }
                if (frameCaptureFailure != null)
                    throw frameCaptureFailure;

                sidecar.frames = frames.ToArray();
                sidecar.alpha_audit = alphaSummary;
                if (alphaSummary.frames_with_transparent_pixels != frames.Count ||
                    alphaSummary.frames_with_nontransparent_pixels != frames.Count)
                {
                    throw new InvalidDataException(
                        "Transparent capture summary does not contain both pixel classes " +
                        "for every frame; capture is fail-closed.");
                }
                sidecar.matte_verified = false;
                sidecar.status = "ok";
                File.WriteAllText(
                    sidecarPath,
                    JsonUtility.ToJson(sidecar, true) + "\n",
                    new UTF8Encoding(false));
                AssetDatabase.Refresh();
                Debug.Log(
                    "Captured actor-only Overview sequence: actor=" + actorName +
                    ", frames=" + frames.Count + ", start=" +
                    startClip.length.ToString("0.###", CultureInfo.InvariantCulture) +
                    "s, loop=" + loopClip.length.ToString("0.###", CultureInfo.InvariantCulture) +
                    "s, sidecar=" + sidecarPath);
            }
            catch (Exception exception)
            {
                sidecar.status = "failed";
                sidecar.matte_verified = false;
                sidecar.error = exception.ToString();
                try
                {
                    File.WriteAllText(
                        sidecarPath,
                        JsonUtility.ToJson(sidecar, true) + "\n",
                        new UTF8Encoding(false));
                }
                catch (Exception sidecarException)
                {
                    Debug.LogError(
                        "Could not write failed actor-only capture sidecar: " +
                        sidecarException);
                }
                throw;
            }
            finally
            {
                if (actor != null)
                    UnityEngine.Object.DestroyImmediate(actor);
            }
        }

        private static CaptureClip[] BuildClipRecords(
            AnimationClip startClip,
            AnimationClip loopClip,
            int fps,
            List<FramePlan> plan,
            float exitSeconds,
            float transitionSeconds)
        {
            int startFrameCount = plan.Count(frame => frame.Phase == "start");
            int transitionFrameCount = plan.Count(frame => frame.Phase == "transition");
            int loopFrameCount = plan.Count(frame => frame.Phase == "loop");
            float transitionBoundary = exitSeconds + transitionSeconds;
            return new[]
            {
                new CaptureClip
                {
                    name = startClip.name,
                    role = "ui_overview_start",
                    duration_seconds = startClip.length,
                    frame_count = startFrameCount,
                    sequence_start_seconds = 0f,
                    sequence_end_seconds = exitSeconds,
                    loop_cycles = 0,
                },
                new CaptureClip
                {
                    name = startClip.name + "->" + loopClip.name,
                    role = "ui_overview_transition",
                    duration_seconds = transitionSeconds,
                    frame_count = transitionFrameCount,
                    sequence_start_seconds = exitSeconds,
                    sequence_end_seconds = transitionBoundary,
                    loop_cycles = 0,
                },
                new CaptureClip
                {
                    name = loopClip.name,
                    role = "ui_overview_loop",
                    duration_seconds = loopClip.length,
                    frame_count = loopFrameCount,
                    sequence_start_seconds = transitionBoundary,
                    sequence_end_seconds = transitionBoundary + loopFrameCount / (float)fps,
                    loop_cycles = 1,
                },
            };
        }

        private static List<FramePlan> BuildFramePlan(
            AnimationClip startClip,
            AnimationClip loopClip,
            int fps,
            float exitSeconds,
            float transitionSeconds,
            float destinationNormalizedOffset)
        {
            var result = new List<FramePlan>();
            int startFrameCount = Mathf.Max(1, Mathf.CeilToInt(exitSeconds * fps));
            for (int index = 0; index < startFrameCount; index++)
            {
                float time = Mathf.Min(
                    index / (float)fps,
                    Mathf.Max(0f, exitSeconds - 1e-5f));
                result.Add(new FramePlan
                {
                    Phase = "start",
                    Clip = startClip,
                    ClipName = startClip.name,
                    Timestamp = time,
                    ClipTime = time,
                    PhaseSeconds = time,
                    PhaseNormalized = startClip.length > 0f
                        ? time / startClip.length
                    : 0f,
                });
            }

            int transitionFrameCount = transitionSeconds > 1e-5f
                ? Mathf.Max(1, Mathf.CeilToInt(transitionSeconds * fps))
                : 0;
            for (int index = 0; index < transitionFrameCount; index++)
            {
                float elapsed = Mathf.Min(
                    index / (float)fps,
                    Mathf.Max(0f, transitionSeconds - 1e-5f));
                float normalized = transitionSeconds > 0f
                    ? elapsed / transitionSeconds
                    : 1f;
                result.Add(new FramePlan
                {
                    Phase = "transition",
                    ClipName = startClip.name + "->" + loopClip.name,
                    Timestamp = exitSeconds + elapsed,
                    // For a blended state this field records transition
                    // elapsed time, while the source clip states are carried
                    // by the transition metadata.
                    ClipTime = elapsed,
                    PhaseSeconds = elapsed,
                    PhaseNormalized = normalized,
                    TransitionElapsed = elapsed,
                    TransitionNormalized = normalized,
                });
            }

            int loopFrameCount = Mathf.Max(
                1,
                Mathf.CeilToInt(loopClip.length * fps));
            for (int index = 0; index < loopFrameCount; index++)
            {
                float time = index / (float)fps;
                if (loopClip.length > 0f)
                    time = Mathf.Repeat(time, loopClip.length);
                result.Add(new FramePlan
                {
                    Phase = "loop",
                    Clip = loopClip,
                    ClipName = loopClip.name,
                    Timestamp = exitSeconds + transitionSeconds + index / (float)fps,
                    ClipTime = time,
                    PhaseSeconds = time,
                    PhaseNormalized = loopClip.length > 0f
                        ? time / loopClip.length
                        : 0f,
                });
            }
            return result;
        }

        private static float ResolveExitSeconds(float normalizedTime, float clipLength)
        {
            RequireFinite(normalizedTime, "exitNormalizedTime");
            RequireFinite(clipLength, "start clip length");
            if (clipLength <= 0f)
                throw new InvalidDataException("Start clip length must be positive.");
            return Mathf.Clamp(normalizedTime, 0f, 1f) * clipLength;
        }

        private static float ResolveTransitionSeconds(
            EndfieldOverviewPlayback playback,
            float startClipLength)
        {
            RequireFinite(
                playback.normalizedTransitionDuration,
                "normalizedTransitionDuration");
            if (playback.normalizedTransitionDuration < 0f)
                throw new InvalidDataException(
                    "normalizedTransitionDuration must not be negative.");
            float seconds = playback.transitionDurationFixed
                ? playback.normalizedTransitionDuration
                : playback.normalizedTransitionDuration * startClipLength;
            RequireFinite(seconds, "controller transition seconds");
            if (seconds < 0f)
                throw new InvalidDataException(
                    "controller transition seconds must not be negative.");
            return seconds;
        }

        private static void RequireFinite(float value, string name)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                throw new InvalidDataException(name + " must be finite.");
        }

        private static void SampleFrame(
            Animation animation,
            AnimationClip startClip,
            AnimationClip loopClip,
            EndfieldOverviewPlayback playback,
            float exitSeconds,
            FramePlan sample)
        {
            if (sample.Phase == "transition")
            {
                SampleTransition(
                    animation,
                    startClip,
                    loopClip,
                    playback.destinationNormalizedOffset,
                    exitSeconds,
                    sample.TransitionElapsed,
                    sample.TransitionNormalized);
                return;
            }
            if (sample.Clip == null)
                throw new InvalidDataException(
                    "Overview frame has no source clip: phase=" + sample.Phase);
            sample.Clip.SampleAnimation(animation.gameObject, sample.ClipTime);
        }

        private static void SampleTransition(
            Animation animation,
            AnimationClip startClip,
            AnimationClip loopClip,
            float destinationNormalizedOffset,
            float startTime,
            float elapsed,
            float normalized)
        {
            AnimationState startState = animation[startClip.name];
            AnimationState loopState = animation[loopClip.name];
            if (startState == null || loopState == null)
                throw new InvalidDataException(
                    "Overview transition source states are not registered on Animation.");

            RequireFinite(destinationNormalizedOffset, "destinationNormalizedOffset");
            RequireFinite(elapsed, "transition elapsed");
            RequireFinite(normalized, "transition normalized");
            animation.Stop();
            startState.layer = 0;
            startState.blendMode = AnimationBlendMode.Blend;
            startState.wrapMode = WrapMode.ClampForever;
            startState.speed = 0f;
            startState.enabled = true;
            startState.weight = Mathf.Clamp01(1f - normalized);
            startState.time = Mathf.Clamp(
                startTime + Mathf.Max(0f, elapsed),
                0f,
                startClip.length);

            loopState.layer = 0;
            loopState.blendMode = AnimationBlendMode.Blend;
            loopState.wrapMode = WrapMode.Loop;
            loopState.speed = 0f;
            loopState.enabled = true;
            loopState.weight = Mathf.Clamp01(normalized);
            float loopTime = Mathf.Repeat(
                Mathf.Clamp01(destinationNormalizedOffset) * loopClip.length +
                Mathf.Max(0f, elapsed),
                loopClip.length);
            loopState.time = loopTime;
            animation.Sample();
        }

        private static AnimationClip ResolveClip(Animation animation, string name)
        {
            if (string.IsNullOrWhiteSpace(name))
                throw new InvalidDataException(
                    "EndfieldOverviewPlayback has an empty source clip name.");
            AnimationState state = animation[name];
            if (state != null && state.clip != null)
                return state.clip;
            throw new FileNotFoundException(
                "Overview source clip is not registered on Animation: " + name);
        }

        private static GameObject LoadActorPrefab(string requestedActor)
        {
            string actor = requestedActor.Trim();
            if (actor.Length == 0)
                throw new ArgumentException("Actor name is empty.", nameof(requestedActor));
            string directPath = PlayableRoot + "/" + actor + "/Prefabs/" + actor + ".prefab";
            GameObject direct = AssetDatabase.LoadAssetAtPath<GameObject>(directPath);
            if (direct != null)
                return direct;

            foreach (string guid in AssetDatabase.FindAssets(
                         "t:Prefab",
                         new[] { PlayableRoot }))
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                if (!path.EndsWith("/Prefabs/" + actor + ".prefab", StringComparison.OrdinalIgnoreCase))
                    continue;
                GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(path);
                if (prefab != null)
                    return prefab;
            }
            throw new FileNotFoundException(
                "Playable actor prefab is missing: " + actor,
                directPath);
        }

        private static void EnsureSourceSceneExists()
        {
            string absolute = Path.Combine(
                Directory.GetCurrentDirectory(),
                ViewerScenePath);
            if (!File.Exists(absolute))
                throw new FileNotFoundException(
                    "Build CharacterRecoveryViewer before capturing Overview sequences.",
                    ViewerScenePath);
        }

        private static void EnsurePipelineAndOpenViewer()
        {
            GameObject pipelineAsset = AssetDatabase.LoadAssetAtPath<GameObject>(
                "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset");
            // The asset is a RenderPipelineAsset, not a GameObject. Keep this
            // check in a separate method so no capture path silently falls back
            // to Unity's default renderer.
            if (pipelineAsset != null)
                throw new InvalidOperationException(
                    "HG compatibility pipeline asset resolved as an unexpected GameObject.");
            UnityEngine.Rendering.RenderPipelineAsset pipeline =
                AssetDatabase.LoadAssetAtPath<UnityEngine.Rendering.RenderPipelineAsset>(
                    "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset");
            if (pipeline == null)
                throw new FileNotFoundException(
                    "HG compatibility render pipeline is missing.",
                    "Assets/EndfieldGraphShaderLab/Generated/HGCompatRenderPipeline.asset");
            UnityEngine.Rendering.GraphicsSettings.renderPipelineAsset = pipeline;
            QualitySettings.renderPipeline = pipeline;
            EditorSceneManager.OpenScene(ViewerScenePath, OpenSceneMode.Single);
        }

        private static void ConfigureActorOnlyScene(
            Scene scene,
            GameObject actor,
            Camera camera,
            string actorName,
            out bool backdropDisabled,
            out bool externalRendererIsolation,
            out bool externalUiIsolation,
            out bool actorPropsDisabled)
        {
            Transform lightingRoot = FindSceneObject("Lighting")?.transform;
            EndfieldManifestCharacterSetup.ConfigureOperatorReferenceLighting(
                scene,
                lightingRoot,
                camera,
                actorName,
                actor.transform);
            EndfieldManifestCharacterSetup.FrameCameraToRecoveredOperatorCamera(
                camera,
                actorName);
            camera.aspect = (float)DefaultWidth / DefaultHeight;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = new Color(0f, 0f, 0f, 0f);

            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            if (sourceSky != null)
            {
                sourceSky.operatorPhysicalHdrSource = false;
                sourceSky.enabled = false;
            }
            RenderSettings.skybox = null;

            CharacterRecoveryPresentationController presentation =
                camera.GetComponent<CharacterRecoveryPresentationController>();
            if (presentation != null)
            {
                presentation.enableRecoveredPortrait = false;
                presentation.enableRecoveredSourceEnergyCore = false;
                presentation.enableRecoveredReadyPresentationSubset = false;
                if (presentation.physicalPresentation != null)
                {
                    presentation.physicalPresentation.enableRecoveredPresentation = false;
                    presentation.physicalPresentation.enableReadySubsetDiagnostic = false;
                    presentation.physicalPresentation.RefreshSelection();
                }
            }

            foreach (Renderer renderer in UnityEngine.Object.FindObjectsOfType<Renderer>(true))
            {
                if (renderer == null || renderer.transform.IsChildOf(actor.transform))
                    continue;
                renderer.enabled = false;
            }
            // A zero count is also a successful audit: there simply was no
            // external renderer to hide in this scene variant.
            externalRendererIsolation = true;
            backdropDisabled = FindSceneObject("ReferenceBackdrop") == null ||
                !FindSceneObject("ReferenceBackdrop").GetComponentsInChildren<Renderer>(true)
                    .Any(renderer => renderer != null && renderer.enabled);

            foreach (Canvas canvas in UnityEngine.Object.FindObjectsOfType<Canvas>(true))
            {
                if (canvas == null || canvas.transform.IsChildOf(actor.transform))
                    continue;
                canvas.enabled = false;
            }
            foreach (EndfieldRecoveredCharInfoBackgroundPortrait portrait in
                     UnityEngine.Object.FindObjectsOfType<EndfieldRecoveredCharInfoBackgroundPortrait>(true))
            {
                if (portrait != null)
                    portrait.enabled = false;
            }
            // As above, absence of a Canvas is an already-isolated state.
            externalUiIsolation = true;
            actorPropsDisabled = DisableActorProps(actor);
        }

        private static bool DisableActorProps(GameObject actor)
        {
            Transform props = actor.transform.Find("RecoveredProps");
            if (props == null)
                return true;
            props.gameObject.SetActive(false);
            foreach (Renderer renderer in props.GetComponentsInChildren<Renderer>(true))
            {
                if (renderer != null)
                    renderer.enabled = false;
            }
            return true;
        }

        private static GameObject FindSceneObject(string name)
        {
            foreach (GameObject candidate in
                     Resources.FindObjectsOfTypeAll<GameObject>())
            {
                if (candidate != null && candidate.name == name &&
                    candidate.scene.IsValid())
                    return candidate;
            }
            return null;
        }

        private static CameraContract BuildCameraContract(string actorName)
        {
            EndfieldRecoveredOverviewCameraContract.Entry entry =
                EndfieldRecoveredOverviewCameraContract.Resolve(actorName);
            return new CameraContract
            {
                actor = entry.Actor,
                template_id = entry.TemplateId,
                track = entry.Track,
                camera_position = Vector3Values(entry.CameraPosition),
                look_at_position = Vector3Values(entry.LookAtPosition),
                serialized_vcam_rotation = QuaternionValues(entry.SerializedVcamRotation),
                field_of_view = entry.FieldOfView,
                near_clip_plane = entry.NearClipPlane,
                far_clip_plane = entry.FarClipPlane,
            };
        }

        private static float[] Vector3Values(Vector3 value) =>
            new[] { value.x, value.y, value.z };

        private static float[] QuaternionValues(Quaternion value) =>
            new[] { value.x, value.y, value.z, value.w };

        private static AlphaFrameAudit RenderTransparentFrame(
            Camera camera,
            string path,
            int width,
            int height)
        {
            RenderTexture previousTarget = camera.targetTexture;
            RenderTexture previousActive = RenderTexture.active;
            var renderTexture = new RenderTexture(
                width,
                height,
                24,
                RenderTextureFormat.ARGB32)
            {
                name = "Endfield Actor-Only Transparent Overview Capture",
                antiAliasing = 1,
                useMipMap = false,
                autoGenerateMips = false,
            };
            var texture = new Texture2D(
                width,
                height,
                TextureFormat.RGBA32,
                false,
                false);
            try
            {
                if (!renderTexture.Create())
                    throw new InvalidOperationException(
                        "Could not create transparent Overview capture target.");
                camera.targetTexture = renderTexture;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color(0f, 0f, 0f, 0f);
                RenderTexture.active = renderTexture;
                camera.Render();
                texture.ReadPixels(
                    new Rect(0f, 0f, width, height),
                    0,
                    0,
                    false);
                texture.Apply(false, false);
                File.WriteAllBytes(path, texture.EncodeToPNG());

                Color32[] pixels = texture.GetPixels32();
                int transparent = 0;
                int nontransparent = 0;
                byte minimum = 255;
                byte maximum = 0;
                foreach (Color32 pixel in pixels)
                {
                    minimum = Math.Min(minimum, pixel.a);
                    maximum = Math.Max(maximum, pixel.a);
                    if (pixel.a == 0)
                        transparent++;
                    else
                        nontransparent++;
                }
                return new AlphaFrameAudit
                {
                    width = width,
                    height = height,
                    transparent_pixels = transparent,
                    nontransparent_pixels = nontransparent,
                    minimum_alpha = minimum,
                    maximum_alpha = maximum,
                    transparent_clear_observed = transparent > 0,
                };
            }
            finally
            {
                camera.targetTexture = previousTarget;
                RenderTexture.active = previousActive;
                texture.Apply(false, false);
                UnityEngine.Object.DestroyImmediate(texture);
                renderTexture.Release();
                UnityEngine.Object.DestroyImmediate(renderTexture);
            }
        }

        private static void AccumulateAlphaAudit(
            AlphaAudit summary,
            AlphaFrameAudit frame)
        {
            summary.frame_count++;
            summary.alpha_readback_observed |=
                frame.transparent_pixels > 0 || frame.nontransparent_pixels > 0;
            if (frame.transparent_pixels > 0)
                summary.frames_with_transparent_pixels++;
            if (frame.nontransparent_pixels > 0)
                summary.frames_with_nontransparent_pixels++;
            summary.minimum_alpha = Math.Min(summary.minimum_alpha, frame.minimum_alpha);
            summary.maximum_alpha = Math.Max(summary.maximum_alpha, frame.maximum_alpha);
        }

        private static string[] ResolveActors()
        {
            string raw = Environment.GetEnvironmentVariable(ActorEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(raw))
                raw = "Endminf,Pelica,Chen";
            if (string.Equals(raw.Trim(), "all", StringComparison.OrdinalIgnoreCase))
            {
                var names = new List<string>();
                foreach (string guid in AssetDatabase.FindAssets(
                             "t:Prefab",
                             new[] { PlayableRoot }))
                {
                    string path = AssetDatabase.GUIDToAssetPath(guid);
                    if (!path.EndsWith(".prefab", StringComparison.OrdinalIgnoreCase) ||
                        path.IndexOf("/Prefabs/", StringComparison.OrdinalIgnoreCase) < 0)
                        continue;
                    string name = Path.GetFileNameWithoutExtension(path);
                    string parent = Path.GetFileName(Path.GetDirectoryName(path));
                    if (!string.Equals(name, parent, StringComparison.OrdinalIgnoreCase))
                        continue;
                    if (!names.Contains(name, StringComparer.OrdinalIgnoreCase))
                        names.Add(name);
                }
                names.Sort(StringComparer.OrdinalIgnoreCase);
                return names.ToArray();
            }
            return raw.Split(new[] { ',', ';' }, StringSplitOptions.RemoveEmptyEntries)
                .Select(value => value.Trim())
                .Where(value => value.Length > 0)
                .Distinct(StringComparer.OrdinalIgnoreCase)
                .ToArray();
        }

        private static int ResolveFps()
        {
            string raw = Environment.GetEnvironmentVariable(FpsEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(raw))
                return DefaultFps;
            if (!int.TryParse(raw.Trim(), NumberStyles.Integer, CultureInfo.InvariantCulture, out int fps) ||
                fps <= 0 || fps > 120)
            {
                throw new InvalidDataException(
                    FpsEnvironmentVariable + " must be an integer in [1,120], got '" + raw + "'.");
            }
            return fps;
        }

        private static string ResolveOutputRoot()
        {
            string raw = Environment.GetEnvironmentVariable(OutputEnvironmentVariable);
            if (!string.IsNullOrWhiteSpace(raw))
                return Path.GetFullPath(raw.Trim());
            return Path.GetFullPath(Path.Combine(
                Application.dataPath,
                "..",
                DefaultOutputDirectory));
        }

        private static void ClearPreviousFrames(string directory, string sidecar)
        {
            Directory.CreateDirectory(directory);
            foreach (string png in Directory.GetFiles(directory, "frame_*.png"))
                File.Delete(png);
            if (File.Exists(sidecar))
                File.Delete(sidecar);
        }

        private static string[] CaptureLimitations() => new[]
        {
            "The capture disables all Renderer and Canvas objects outside the selected actor.",
            "RecoveredProps are disabled; this is a body-only beauty capture and does not recover item/widget matte ownership.",
            "ui_overview_start ends at controller exit time; transition frames sample the start/loop AnimationState weights on the same layer, then one complete loop period is emitted without a duplicate endpoint.",
            "The transparent pass temporarily disables HGCompatRenderPipelineAsset character post processing; transparent frames therefore do not contain recovered post-process output.",
            "matteVerified=false: alpha readback is reported as an audit only; no independent character matte or UI-removal ground truth was verified.",
            "secondaryDynamicsVerified=false: the original BeyondBoneCloth owners and serialized constraints are catalogued, but the retail BeyondDynamicBone/Burst solver and its PlayerLoop scheduling are not present; cloth, hair, ribbons, and accessories can diverge from the animated body.",
            "The secondary-dynamics owner-binding audit verifies only that the declared cloth owners, root bones, and collider owners resolve on the instantiated actor; it performs no transform writes and is not solver equivalence.",
            "Recovered renderer/shader pipeline output is not a proof of retail pixel parity or of a complete source rendering pipeline.",
        };
    }
}
