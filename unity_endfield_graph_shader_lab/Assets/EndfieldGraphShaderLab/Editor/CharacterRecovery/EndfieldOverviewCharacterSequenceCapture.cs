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
            public string transition_mode = "direct_clip_boundary";
            public float controller_exit_normalized_time;
            public float controller_transition_seconds;
            public bool transparent_clear_requested = true;
            public bool reference_backdrop_disabled;
            public bool non_actor_renderers_disabled;
            public bool non_actor_ui_disabled;
            public bool actor_props_disabled;
            public bool matte_verified = false;
            public CaptureClip[] clips = Array.Empty<CaptureClip>();
            public CameraContract camera_contract;
            public AlphaAudit alpha_audit = new AlphaAudit();
            public CaptureFrame[] frames = Array.Empty<CaptureFrame>();
            public string[] limitations = Array.Empty<string>();
            public string error = "";
        }

        private sealed class FramePlan
        {
            public string Phase;
            public AnimationClip Clip;
            public float Timestamp;
            public float ClipTime;
            public float PhaseSeconds;
            public float PhaseNormalized;
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
                    if (File.Exists(Path.Combine(
                            Directory.GetCurrentDirectory(), ViewerScenePath)))
                    {
                        EditorSceneManager.OpenScene(
                            ViewerScenePath,
                            OpenSceneMode.Single);
                    }
                }
                catch (Exception exception)
                {
                    failures.Add("viewer restore: " + exception.Message);
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

                ClearActorRoots(charactersRoot);
                actor = PrefabUtility.InstantiatePrefab(prefab, scene) as GameObject;
                if (actor == null)
                    throw new InvalidOperationException(
                        "Could not instantiate actor prefab: " +
                        AssetDatabase.GetAssetPath(prefab));
                actor.name = actorName;
                actor.transform.SetParent(charactersRoot, false);
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
                sidecar.controller_exit_normalized_time = playback.exitNormalizedTime;
                sidecar.controller_transition_seconds = playback.transitionDurationFixed
                    ? playback.normalizedTransitionDuration
                    : playback.normalizedTransitionDuration * startClip.length;
                sidecar.clips = BuildClipRecords(startClip, loopClip, fps);

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

                List<FramePlan> plan = BuildFramePlan(startClip, loopClip, fps);
                var frames = new List<CaptureFrame>(plan.Count);
                var alphaSummary = new AlphaAudit
                {
                    transparent_clear_requested = true,
                    matte_verified = false,
                };
                for (int index = 0; index < plan.Count; index++)
                {
                    FramePlan sample = plan[index];
                    sample.Clip.SampleAnimation(animation.gameObject, sample.ClipTime);
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
                        clip = sample.Clip.name,
                        timestamp_seconds = sample.Timestamp,
                        clip_time_seconds = sample.ClipTime,
                        phase_seconds = sample.PhaseSeconds,
                        phase_normalized = sample.PhaseNormalized,
                        alpha_audit = alpha,
                    });
                }

                sidecar.frames = frames.ToArray();
                sidecar.alpha_audit = alphaSummary;
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
            int fps)
        {
            int startFrameCount = Mathf.Max(
                1,
                Mathf.CeilToInt(startClip.length * fps) + 1);
            int loopFrameCount = Mathf.Max(
                1,
                Mathf.CeilToInt(loopClip.length * fps));
            float sequenceBoundary = startClip.length;
            return new[]
            {
                new CaptureClip
                {
                    name = startClip.name,
                    role = "ui_overview_start",
                    duration_seconds = startClip.length,
                    frame_count = startFrameCount,
                    sequence_start_seconds = 0f,
                    sequence_end_seconds = sequenceBoundary,
                    loop_cycles = 0,
                },
                new CaptureClip
                {
                    name = loopClip.name,
                    role = "ui_overview_loop",
                    duration_seconds = loopClip.length,
                    frame_count = loopFrameCount,
                    sequence_start_seconds = sequenceBoundary,
                    sequence_end_seconds = sequenceBoundary + loopFrameCount / (float)fps,
                    loop_cycles = 1,
                },
            };
        }

        private static List<FramePlan> BuildFramePlan(
            AnimationClip startClip,
            AnimationClip loopClip,
            int fps)
        {
            var result = new List<FramePlan>();
            int startFrameCount = Mathf.Max(
                1,
                Mathf.CeilToInt(startClip.length * fps));
            for (int index = 0; index <= startFrameCount; index++)
            {
                float time = Mathf.Min(index / (float)fps, startClip.length);
                result.Add(new FramePlan
                {
                    Phase = "start",
                    Clip = startClip,
                    Timestamp = time,
                    ClipTime = time,
                    PhaseSeconds = time,
                    PhaseNormalized = startClip.length > 0f
                        ? time / startClip.length
                        : 0f,
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
                    Timestamp = startClip.length + index / (float)fps,
                    ClipTime = time,
                    PhaseSeconds = time,
                    PhaseNormalized = loopClip.length > 0f
                        ? time / loopClip.length
                        : 0f,
                });
            }
            return result;
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
            UnityEngine.Rendering.QualitySettings.renderPipeline = pipeline;
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

        private static void ClearActorRoots(Transform charactersRoot)
        {
            for (int index = charactersRoot.childCount - 1; index >= 0; index--)
            {
                Transform child = charactersRoot.GetChild(index);
                if (child != null)
                    UnityEngine.Object.DestroyImmediate(child.gameObject);
            }
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
            "ui_overview_start and ui_overview_loop are sampled at a direct clip boundary; the runtime Animator crossfade is recorded but not simulated.",
            "matteVerified=false: alpha readback is reported as an audit only; no independent character matte or UI-removal ground truth was verified.",
            "Recovered renderer/shader pipeline output is not a proof of retail pixel parity or of a complete source rendering pipeline.",
        };
    }
}
