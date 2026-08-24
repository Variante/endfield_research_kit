using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off selectors for the recovered physical CharInfo presentation
    /// hierarchy. The exact selector is deliberately strict: the complete
    /// original hierarchy is never shown unless every required source asset
    /// and shader semantic has been marked complete by the source-data
    /// importer. A separately named diagnostic can show only the source-owned
    /// wall, floor, and far-grid subset. That diagnostic always excludes the
    /// unresolved outside sphere and shadow receiver and is never presented as
    /// an original full-scene reconstruction.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/HGRP Compatibility/Recovered CharInfo Presentation")]
    public sealed class EndfieldRecoveredCharInfoPresentation : MonoBehaviour
    {
        public const string Keyword =
            "ENDFIELD_RECOVERED_CHARINFO_PRESENTATION";
        public const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_PRESENTATION";
        public const string CommandLineArgument =
            "-endfield-recovered-charinfo-presentation";

        public const string ReadySubsetKeyword =
            "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC";
        public const string ReadySubsetEnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_READY_SUBSET_DIAGNOSTIC";
        public const string ReadySubsetCommandLineArgument =
            "-endfield-recovered-charinfo-ready-subset-diagnostic";
        public const string EndminfBackdropVisualCompatibilityEnvironmentVariable =
            "ENDFIELD_ENDMINF_BACKDROP_VISUAL_COMPATIBILITY";

        public const string GridShaderName =
            "Endfield/Recovered/CharInfo/VFXDsWrite";
        public const string FloorShaderName =
            "Endfield/Recovered/CharInfo/VFXDistanceField";
        public const string WallShaderName =
            "Endfield/Recovered/CharInfo/VFXBaseV2Static";
        public const string ShadowReceiverShaderName =
            "Endfield/Recovered/CharInfo/CharacterNPR_ShadowReceiver";
        public const string UnavailableLitShaderName =
            "Hidden/Endfield/Recovered/CharInfo/HGRPLitUnavailable";

        [Tooltip("Requests the exact physical presentation branch. This stays " +
                 "off by default and still fails closed while source readiness " +
                 "is incomplete.")]
        public bool enableRecoveredPresentation;

        [Tooltip("Requests a partial, non-original diagnostic containing only " +
                 "the source-owned wall, floor, and far-grid passes. It stays " +
                 "off by default and explicitly excludes SphereOutside and " +
                 "ShadowPlane.")]
        public bool enableReadySubsetDiagnostic;

        [Tooltip("Importer-owned wrapper containing the exact layer-13 source hierarchy.")]
        public GameObject sourceContent;

        [Tooltip("Existing screenshot-like compatibility backdrop. It is disabled " +
                 "only after the exact source branch passes every readiness check.")]
        public Renderer compatibilityBackdropRenderer;

        [Header("Exact source renderers")]
        public Renderer sphereOutsideRenderer;
        public Renderer floorRenderer;
        public Renderer wallRenderer;
        public Renderer shadowPlaneRenderer;
        public Renderer farGridRenderer;

        [Header("Source readiness")]
        public TextAsset sourceManifest;

        [Tooltip("Source-derived endpoint samples from the original autoplay " +
                 "GridDeco and CharFloorEffect in-clips.")]
        public TextAsset settledOpenState;

        [Tooltip("Written only by the source importer after all five material/shader " +
                 "paths are semantically closed. It is intentionally false today.")]
        public bool exactSourceAssetsReady;

        [TextArea(2, 5)]
        public string readinessFailure;

        private static bool standaloneSelectionInitialized;
        private static bool? standaloneSelectionRequested;
        private static bool? standaloneReadySubsetRequested;

        private bool sourceStateApplied;
        private bool readySubsetStateApplied;
        private bool previousBackdropEnabled;
        private Renderer appliedBackdropRenderer;
        private MaterialPropertyBlock endminfBackdropProperties;
        private bool loggedReadinessFailure;
        private bool loggedReadySubsetFailure;
        private bool loggedReadySubsetActivation;

        private readonly bool[] previousRendererEnabled = new bool[5];
        private MaterialPropertyBlock previousFloorProperties;
        private MaterialPropertyBlock previousFarGridProperties;

        private static readonly int BlendTintId =
            Shader.PropertyToID("_BlendTint");
        private static readonly int TintColorId =
            Shader.PropertyToID("_TintColor");

        public bool PresentationRequested
        {
            get
            {
                InitializeStandaloneSelection();
                return enabled && gameObject.activeInHierarchy &&
                       (standaloneSelectionRequested ??
                        enableRecoveredPresentation);
            }
        }

        public bool PresentationActive =>
            sourceStateApplied && !readySubsetStateApplied;

        public bool ReadySubsetDiagnosticRequested
        {
            get
            {
                InitializeStandaloneSelection();
                return enabled && gameObject.activeInHierarchy &&
                       (standaloneReadySubsetRequested ??
                        enableReadySubsetDiagnostic);
            }
        }

        public bool ReadySubsetDiagnosticActive =>
            sourceStateApplied && readySubsetStateApplied;

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void PublishStandaloneSelection()
        {
            InitializeStandaloneSelection();
            Shader.DisableKeyword(Keyword);
            Shader.DisableKeyword(ReadySubsetKeyword);
        }

        private static void InitializeStandaloneSelection()
        {
            if (standaloneSelectionInitialized)
                return;

            standaloneSelectionInitialized = true;

            // Tri-state: an unset selector leaves the serialized scene value in
            // charge, and an explicit falsey selector forces the recovered
            // branch off even when an earlier diagnostic saved it on.
            standaloneSelectionRequested =
                EndfieldRecoveredSelector.Explicit(EnvironmentVariable);
            standaloneReadySubsetRequested =
                EndfieldRecoveredSelector.Explicit(ReadySubsetEnvironmentVariable);

            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                if (!string.Equals(
                        arguments[i],
                        CommandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                    continue;
                standaloneSelectionRequested = true;
            }

            for (int i = 0; i < arguments.Length; i++)
            {
                if (!string.Equals(
                        arguments[i],
                        ReadySubsetCommandLineArgument,
                        StringComparison.OrdinalIgnoreCase))
                    continue;
                standaloneReadySubsetRequested = true;
            }
        }

        private void OnEnable()
        {
            ApplySelection();
        }

        private void OnValidate()
        {
            ApplySelection();
        }

        private void Update()
        {
            ApplySelection();
        }

        private void OnDisable()
        {
            FailClosed();
        }

        private void OnDestroy()
        {
            FailClosed();
        }

        private void ApplySelection()
        {
            if (!PresentationRequested && !ReadySubsetDiagnosticRequested)
            {
                FailClosed();
                loggedReadinessFailure = false;
                loggedReadySubsetFailure = false;
                loggedReadySubsetActivation = false;
                return;
            }

            // A request for the complete branch always takes precedence. If
            // it is not ready, do not silently downgrade it to a partial
            // diagnostic even when both selectors were accidentally set.
            if (PresentationRequested)
            {
                ApplyExactSelection();
                return;
            }

            ApplyReadySubsetDiagnostic();
        }

        /// <summary>
        /// Re-evaluates the serialized selectors immediately. The character
        /// recovery viewer changes its recovered presentation preset while
        /// running, so waiting for the next Update would leave editor captures
        /// and same-frame actor switches one presentation state behind.
        /// </summary>
        public void RefreshSelection()
        {
            ApplySelection();
        }

        private void ApplyExactSelection()
        {

            string failure;
            if (!ValidateSourceReadiness(out failure))
            {
                FailClosed();
                if (!loggedReadinessFailure)
                {
                    Debug.LogError(
                        "Recovered CharInfo physical presentation was requested, " +
                        "but the source contract is incomplete. The branch remains " +
                        "fail-closed and ReferenceBackdrop remains authoritative. " +
                        failure,
                        this);
                    loggedReadinessFailure = true;
                }
                return;
            }

            BeginSourceState(false);

            sourceContent.SetActive(true);
            SetRendererEnabledStates(true, true, true, true, true);
            if (appliedBackdropRenderer != null)
                appliedBackdropRenderer.enabled = false;
            Shader.EnableKeyword(Keyword);
            Shader.DisableKeyword(ReadySubsetKeyword);
            loggedReadinessFailure = false;
        }

        private void ApplyReadySubsetDiagnostic()
        {
            string failure;
            ReadySubsetOpenState openState;
            if (!ValidateReadySubsetReadiness(out openState, out failure))
            {
                FailClosed();
                if (!loggedReadySubsetFailure)
                {
                    Debug.LogError(
                        "Recovered CharInfo ready-subset diagnostic was " +
                        "requested, but its bounded source contract failed. " +
                        "The branch remains off and ReferenceBackdrop remains " +
                        "authoritative. " + failure,
                        this);
                    loggedReadySubsetFailure = true;
                }
                return;
            }

            BeginSourceState(true);
            sourceContent.SetActive(true);
            ApplySettledOpenState(openState);

            if (ApplyEndminfBackdropCompatibility())
            {
                return;
            }

            // The diagnostic is intentionally an allow-list. Do not permit
            // either unresolved pass to draw even if its GameObject or source
            // renderer is enabled in the recovered prefab.
            SetRendererEnabledStates(false, true, true, false, true);
            if (appliedBackdropRenderer != null)
                appliedBackdropRenderer.enabled = false;
            Shader.DisableKeyword(Keyword);
            Shader.EnableKeyword(ReadySubsetKeyword);
            loggedReadySubsetFailure = false;

            if (!loggedReadySubsetActivation)
            {
                Debug.LogWarning(
                    "Recovered CharInfo ready-subset diagnostic active: " +
                    "partial/non-original presentation containing only " +
                    "CharFloorEffect, GeoSphere001, and GridDeco/Far. " +
                    "SphereOutside and ShadowPlane are explicitly disabled.",
                    this);
                loggedReadySubsetActivation = true;
            }
        }

        private bool ApplyEndminfBackdropCompatibility()
        {
            if (EndfieldRecoveredSelector.Explicit(
                    EndminfBackdropVisualCompatibilityEnvironmentVariable) != true)
                return false;

            // The recovered GeoSphere wall is an unresolved opaque HGRP pass:
            // admitting it covers the camera with black before its retail
            // material consumer exists. The source GridDeco/Far pass is in the
            // validated ready subset, so admit that renderer alone over the
            // bounded neutral screen plate.
            sourceContent.SetActive(true);
            if (sphereOutsideRenderer != null) sphereOutsideRenderer.enabled = false;
            if (floorRenderer != null) floorRenderer.enabled = false;
            if (wallRenderer != null) wallRenderer.enabled = false;
            // The receiver's VisibilitySH constants, dual LUTs, capsule set,
            // stencil state, and character-atlas sampling are now source-
            // closed. Admit the original plane over the compatibility wall;
            // SphereOutside remains excluded for its unresolved deferred path.
            if (shadowPlaneRenderer != null) shadowPlaneRenderer.enabled = true;
            // Far is source-complete, but its retail composition is against
            // the unresolved physical wall. Over this neutral carrier it
            // exposes the full dense perspective mesh and diverges sharply;
            // keep it fail-closed until SphereOutside's consumer is live.
            if (farGridRenderer != null) farGridRenderer.enabled = false;
            Renderer backdrop = appliedBackdropRenderer != null
                ? appliedBackdropRenderer
                : compatibilityBackdropRenderer;
            if (backdrop != null)
            {
                backdrop.enabled = true;
                if (endminfBackdropProperties == null)
                    endminfBackdropProperties = new MaterialPropertyBlock();
                backdrop.GetPropertyBlock(endminfBackdropProperties);
                // The retail CharInfo UI field is darker at the top and opens
                // toward the lower edge. Neutral-pixel medians from paired
                // frames constrain this compatibility plate; it is not a
                // SphereOutside material claim.
                endminfBackdropProperties.SetColor(
                    "_TopColor",
                    new Color(0.59f, 0.595f, 0.595f, 1.0f));
                endminfBackdropProperties.SetColor(
                    "_BottomColor",
                    new Color(0.785f, 0.79f, 0.80f, 1.0f));
                // The exact Far renderer remains admitted, but its recovered
                // transparent pass sorts behind this presentation plate in the
                // public pipeline. Retain a low-contrast carrier on the plate
                // until that queue relationship is closed.
                endminfBackdropProperties.SetColor(
                    "_GridColor",
                    new Color(0.32f, 0.325f, 0.32f, 1.0f));
                endminfBackdropProperties.SetFloat("_GridOpacity", 0.11f);
                endminfBackdropProperties.SetFloat("_DiagonalOpacity", 0.025f);
                endminfBackdropProperties.SetFloat("_GridColumns", 3.1f);
                endminfBackdropProperties.SetFloat("_GridRows", 7.25f);
                endminfBackdropProperties.SetFloat("_GridPhaseX", -0.45f);
                endminfBackdropProperties.SetFloat("_GridPhaseY", 0.25f);
                // Keep this inside the shader's serialized 0..1 contract.
                // The former 2.70 compatibility fit multiplied the bottom of
                // the plate by a negative value before tone mapping, which
                // surfaced as the non-retail cyan band at the lower edge.
                endminfBackdropProperties.SetFloat("_BottomVignette", 1.0f);
                endminfBackdropProperties.SetFloat(
                    "_BottomVignetteHeight", 0.27f);
                // This plate now really reaches the render list (the sky owner
                // no longer restores its stale disabled snapshot). Retain the
                // earlier paired-frame fit; the larger values tested while the
                // plate was accidentally absent saturate the post composite.
                endminfBackdropProperties.SetFloat("_HdrBoost", 1.30f);
                bool exactPortrait = EndfieldRecoveredSelector.Explicit(
                    EndfieldRecoveredCharInfoBackgroundPortrait.EnvironmentVariable) == true;
                endminfBackdropProperties.SetFloat(
                    "_SilhouetteOpacity",
                    exactPortrait ? 0.0f : 0.22f);
                backdrop.SetPropertyBlock(endminfBackdropProperties);
            }
            Shader.DisableKeyword(Keyword);
            Shader.DisableKeyword(ReadySubsetKeyword);
            loggedReadySubsetFailure = false;
            return true;
        }

        public bool ValidateSourceReadiness(out string failure)
        {
            if (!exactSourceAssetsReady)
            {
                failure = string.IsNullOrWhiteSpace(readinessFailure)
                    ? "The importer did not mark the five-renderer source graph complete."
                    : readinessFailure;
                return false;
            }

            if (sourceManifest == null)
            {
                failure = "The source evidence manifest is missing.";
                return false;
            }
            PresentationManifest manifest =
                JsonUtility.FromJson<PresentationManifest>(sourceManifest.text);
            if (manifest == null || !manifest.complete)
            {
                failure = "The source evidence manifest does not declare complete=true.";
                return false;
            }

            if (sourceContent == null)
            {
                failure = "The exact source hierarchy is missing.";
                return false;
            }

            if (!ValidateRenderer(
                    sphereOutsideRenderer,
                    "SphereOutside",
                    "Sphere",
                    "Endfield/Recovered/CharInfo/HGRPLit",
                    out failure) ||
                !ValidateRenderer(
                    floorRenderer,
                    "CharFloorEffect",
                    "Quad",
                    FloorShaderName,
                    out failure) ||
                !ValidateRenderer(
                    wallRenderer,
                    "GeoSphere001",
                    "GeoSphere001",
                    WallShaderName,
                    out failure) ||
                !ValidateRenderer(
                    shadowPlaneRenderer,
                    "ShadowPlane",
                    "Plane",
                    ShadowReceiverShaderName,
                    out failure) ||
                !ValidateRenderer(
                    farGridRenderer,
                    "Far",
                    "S_GridFar",
                    GridShaderName,
                    out failure))
            {
                return false;
            }

            failure = string.Empty;
            return true;
        }

        public bool ValidateReadySubsetReadiness(out string failure)
        {
            ReadySubsetOpenState ignored;
            return ValidateReadySubsetReadiness(out ignored, out failure);
        }

        private bool ValidateReadySubsetReadiness(
            out ReadySubsetOpenState openState,
            out string failure)
        {
            openState = null;
            if (sourceManifest == null)
            {
                failure = "The source evidence manifest is missing.";
                return false;
            }
            PresentationManifest manifest =
                JsonUtility.FromJson<PresentationManifest>(sourceManifest.text);
            if (manifest == null ||
                manifest.schema !=
                    "endfield.charinfo.presentation.original-data.v1")
            {
                failure = "The source evidence manifest schema is not recognized.";
                return false;
            }
            if (sourceContent == null)
            {
                failure = "The recovered source hierarchy is missing.";
                return false;
            }

            if (!ValidateRenderer(
                    floorRenderer,
                    "CharFloorEffect",
                    "Quad",
                    FloorShaderName,
                    out failure) ||
                !ValidateRenderer(
                    wallRenderer,
                    "GeoSphere001",
                    "GeoSphere001",
                    WallShaderName,
                    out failure) ||
                !ValidateRenderer(
                    farGridRenderer,
                    "Far",
                    "S_GridFar",
                    GridShaderName,
                    out failure))
            {
                return false;
            }

            if (!ValidateExcludedRenderer(
                    sphereOutsideRenderer,
                    "SphereOutside",
                    out failure) ||
                !ValidateExcludedRenderer(
                    shadowPlaneRenderer,
                    "ShadowPlane",
                    out failure))
            {
                return false;
            }

            Renderer[] renderers =
                sourceContent.GetComponentsInChildren<Renderer>(true);
            if (renderers.Length != 5)
            {
                failure =
                    $"Expected exactly five recovered source renderers; found {renderers.Length}.";
                return false;
            }
            for (int i = 0; i < renderers.Length; i++)
            {
                Renderer renderer = renderers[i];
                if (renderer != sphereOutsideRenderer &&
                    renderer != floorRenderer &&
                    renderer != wallRenderer &&
                    renderer != shadowPlaneRenderer &&
                    renderer != farGridRenderer)
                {
                    failure =
                        $"Unexpected renderer {renderer.name} exists under the source hierarchy.";
                    return false;
                }
            }

            if (settledOpenState == null)
            {
                failure = "The recovered settled/opened animation sample is missing.";
                return false;
            }
            openState =
                JsonUtility.FromJson<ReadySubsetOpenState>(
                    settledOpenState.text);
            if (openState == null ||
                openState.schema !=
                    "endfield.charinfo.presentation.ready-subset-open-state.v1" ||
                !openState.ready_subset_complete)
            {
                failure =
                    "The settled/opened animation sample is incomplete or has the wrong schema.";
                return false;
            }
            if (!IsFinite(openState.grid_far_tint) ||
                !IsFinite(openState.floor_blend_tint) ||
                !IsFinite(openState.grid_sample_time_seconds) ||
                !IsFinite(openState.floor_sample_time_seconds) ||
                openState.grid_sample_time_seconds < 0.0f ||
                openState.floor_sample_time_seconds < 0.0f)
            {
                failure = "The settled/opened animation sample contains invalid values.";
                return false;
            }

            const float endpointTolerance = 1.0e-6f;
            if (Mathf.Abs(openState.grid_sample_time_seconds - 1.0f) >
                    endpointTolerance ||
                Mathf.Abs(openState.floor_sample_time_seconds - 1.0f) >
                    endpointTolerance ||
                !MatchesSourceColor(
                    openState.grid_far_tint,
                    new Color(0.509434f, 0.509434f, 0.509434f, 0.6f),
                    endpointTolerance) ||
                !MatchesSourceColor(
                    openState.floor_blend_tint,
                    new Color(1.0f, 1.0f, 1.0f, 0.011764706f),
                    endpointTolerance))
            {
                failure =
                    "The settled/opened animation sample no longer matches " +
                    "the recovered source endpoints.";
                return false;
            }

            failure = string.Empty;
            return true;
        }

        private static bool ValidateExcludedRenderer(
            Renderer renderer,
            string expectedObjectName,
            out string failure)
        {
            if (renderer == null ||
                renderer.gameObject.name != expectedObjectName ||
                renderer.gameObject.layer != 13)
            {
                failure =
                    $"Excluded renderer {expectedObjectName} is missing or has the wrong identity.";
                return false;
            }

            failure = string.Empty;
            return true;
        }

        private static bool IsFinite(Color value)
        {
            return IsFinite(value.r) && IsFinite(value.g) &&
                   IsFinite(value.b) && IsFinite(value.a);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static bool MatchesSourceColor(
            Color value,
            Color expected,
            float tolerance)
        {
            return Mathf.Abs(value.r - expected.r) <= tolerance &&
                   Mathf.Abs(value.g - expected.g) <= tolerance &&
                   Mathf.Abs(value.b - expected.b) <= tolerance &&
                   Mathf.Abs(value.a - expected.a) <= tolerance;
        }

        private static bool ValidateRenderer(
            Renderer renderer,
            string expectedObjectName,
            string expectedMeshName,
            string expectedShaderName,
            out string failure)
        {
            if (renderer == null)
            {
                failure = $"Renderer {expectedObjectName} is missing.";
                return false;
            }
            if (renderer.gameObject.name != expectedObjectName ||
                renderer.gameObject.layer != 13)
            {
                failure = $"Renderer {expectedObjectName} has the wrong object name or layer.";
                return false;
            }

            MeshFilter filter = renderer.GetComponent<MeshFilter>();
            if (filter == null || filter.sharedMesh == null ||
                filter.sharedMesh.name != expectedMeshName)
            {
                failure = $"Renderer {expectedObjectName} is missing exact mesh {expectedMeshName}.";
                return false;
            }

            Material material = renderer.sharedMaterial;
            if (material == null || material.shader == null ||
                material.shader.name != expectedShaderName)
            {
                failure = $"Renderer {expectedObjectName} is missing exact shader {expectedShaderName}.";
                return false;
            }

            failure = string.Empty;
            return true;
        }

        private void FailClosed()
        {
            RestoreRendererState();
            if (sourceContent != null && sourceContent.activeSelf)
                sourceContent.SetActive(false);
            Shader.DisableKeyword(Keyword);
            Shader.DisableKeyword(ReadySubsetKeyword);

            if (!sourceStateApplied)
                return;
            RestoreBackdrop();
            sourceStateApplied = false;
            readySubsetStateApplied = false;
        }

        private void BeginSourceState(bool readySubset)
        {
            if (!sourceStateApplied)
            {
                appliedBackdropRenderer = compatibilityBackdropRenderer;
                previousBackdropEnabled =
                    appliedBackdropRenderer != null &&
                    appliedBackdropRenderer.enabled;
                SnapshotRendererState();
                sourceStateApplied = true;
            }
            else if (appliedBackdropRenderer != compatibilityBackdropRenderer)
            {
                RestoreBackdrop();
                appliedBackdropRenderer = compatibilityBackdropRenderer;
                previousBackdropEnabled =
                    appliedBackdropRenderer != null &&
                    appliedBackdropRenderer.enabled;
            }

            if (readySubsetStateApplied && !readySubset)
            {
                RestoreRendererState();
                SnapshotRendererState();
            }
            readySubsetStateApplied = readySubset;
        }

        private void SnapshotRendererState()
        {
            Renderer[] renderers = SourceRenderers();
            for (int i = 0; i < renderers.Length; i++)
            {
                previousRendererEnabled[i] =
                    renderers[i] != null && renderers[i].enabled;
            }

            previousFloorProperties = new MaterialPropertyBlock();
            previousFarGridProperties = new MaterialPropertyBlock();
            if (floorRenderer != null)
                floorRenderer.GetPropertyBlock(previousFloorProperties);
            if (farGridRenderer != null)
                farGridRenderer.GetPropertyBlock(previousFarGridProperties);
        }

        private void RestoreRendererState()
        {
            if (!sourceStateApplied)
                return;

            Renderer[] renderers = SourceRenderers();
            for (int i = 0; i < renderers.Length; i++)
            {
                if (renderers[i] != null)
                    renderers[i].enabled = previousRendererEnabled[i];
            }
            if (floorRenderer != null && previousFloorProperties != null)
                floorRenderer.SetPropertyBlock(previousFloorProperties);
            if (farGridRenderer != null && previousFarGridProperties != null)
                farGridRenderer.SetPropertyBlock(previousFarGridProperties);
            previousFloorProperties = null;
            previousFarGridProperties = null;
        }

        private void SetRendererEnabledStates(
            bool sphereOutside,
            bool floor,
            bool wall,
            bool shadowPlane,
            bool farGrid)
        {
            if (sphereOutsideRenderer != null)
                sphereOutsideRenderer.enabled = sphereOutside;
            if (floorRenderer != null)
                floorRenderer.enabled = floor;
            if (wallRenderer != null)
                wallRenderer.enabled = wall;
            if (shadowPlaneRenderer != null)
                shadowPlaneRenderer.enabled = shadowPlane;
            if (farGridRenderer != null)
                farGridRenderer.enabled = farGrid;
        }

        private void ApplySettledOpenState(ReadySubsetOpenState openState)
        {
            MaterialPropertyBlock floorProperties = new MaterialPropertyBlock();
            floorRenderer.GetPropertyBlock(floorProperties);
            floorProperties.SetColor(BlendTintId, openState.floor_blend_tint);
            floorRenderer.SetPropertyBlock(floorProperties);

            MaterialPropertyBlock gridProperties = new MaterialPropertyBlock();
            farGridRenderer.GetPropertyBlock(gridProperties);
            gridProperties.SetColor(TintColorId, openState.grid_far_tint);
            farGridRenderer.SetPropertyBlock(gridProperties);
        }

        private Renderer[] SourceRenderers()
        {
            return new[]
            {
                sphereOutsideRenderer,
                floorRenderer,
                wallRenderer,
                shadowPlaneRenderer,
                farGridRenderer,
            };
        }

        private void RestoreBackdrop()
        {
            if (appliedBackdropRenderer != null)
                appliedBackdropRenderer.enabled = previousBackdropEnabled;
            appliedBackdropRenderer = null;
        }

        [Serializable]
        private sealed class PresentationManifest
        {
            public string schema;
            public bool complete;
        }

        [Serializable]
        private sealed class ReadySubsetOpenState
        {
            public string schema;
            public bool ready_subset_complete;
            public float grid_sample_time_seconds;
            public Color grid_far_tint;
            public float floor_sample_time_seconds;
            public Color floor_blend_tint;
        }
    }
}
