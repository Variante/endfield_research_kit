using System;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Camera-local selector for the recovered CharInfo operator sky. The
    /// ordinary compatibility viewer remains unchanged: this component only
    /// takes ownership of the camera clear/background state when the existing
    /// source-energy selector is enabled as well.
    /// </summary>
    [ExecuteAlways]
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    [AddComponentMenu("Endfield/HGRP Compatibility/Recovered CharInfo Sky")]
    public sealed class EndfieldRecoveredCharInfoSky : MonoBehaviour
    {
        public const string ShaderName =
            "Hidden/Endfield/HGRPCompat/Recovered CharInfo Sky";
        public const string MaterialOnlyDiagnosticEnvironmentVariable =
            "ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE_MATERIAL_ONLY_DIAGNOSTIC";

        public static readonly Color SourceTint =
            new Color(0.8207547f, 0.8207547f, 0.8207547f, 0.5f);
        public const float SourceRotationDegrees = 294.0f;
        public const float SourceExposure = 1.0f;

        [Tooltip("Marks this as an operator-reference camera. The source sky still " +
                 "requires ENDFIELD_RECOVERED_SOURCE_ENERGY_CORE.")]
        public bool operatorPhysicalHdrSource = true;

        [Tooltip("Exact T_hdri_006 128x128 BC6H source payload.")]
        public Cubemap sourceCubemap;

        [Tooltip("Recovered HGRP sky material carrying the exact tint, rotation, and " +
                 "native preExposure*brightness result.")]
        public Material sourceSkyMaterial;

        [Tooltip("UI/presentation-only neutral background. It is excluded from the " +
                 "physical HDR scene and histogram while the source path is active.")]
        public Renderer presentationBackdropRenderer;

        private Camera targetCamera;
        private bool sourceStateApplied;
        private CameraClearFlags previousClearFlags;
        private Color previousBackgroundColor;
        private Material previousRenderSettingsSkybox;
        private Renderer appliedPresentationBackdropRenderer;
        private bool previousBackdropEnabled;
        private bool loggedMissingSource;
        private bool loggedMaterialOnlyDiagnostic;

        public bool SourcePhysicalHdrRequested
        {
            get
            {
                return enabled &&
                       gameObject.activeInHierarchy &&
                       operatorPhysicalHdrSource &&
                       Shader.IsKeywordEnabled(
                           EndfieldRecoveredSourceEnergyCoreProbe.Keyword);
            }
        }

        internal static EndfieldRecoveredCharInfoSky PrepareForCamera(
            Camera camera,
            out bool drawRecoveredSky)
        {
            drawRecoveredSky = false;
            if (camera == null)
                return null;

            EndfieldRecoveredCharInfoSky sourceSky =
                camera.GetComponent<EndfieldRecoveredCharInfoSky>();
            if (sourceSky == null)
                return null;

            drawRecoveredSky = sourceSky.PrepareForRender();
            return drawRecoveredSky ? sourceSky : null;
        }

        internal static void RestoreAfterCamera(
            EndfieldRecoveredCharInfoSky preparedSourceSky)
        {
            if (preparedSourceSky != null)
                preparedSourceSky.RestoreCompatibilityState();
        }

        internal bool PrepareForRender()
        {
            if (EndfieldRecoveredSelector.Explicit(
                    EndfieldRecoveredCharInfoPresentation
                        .EndminfBackdropVisualCompatibilityEnvironmentVariable) == true)
            {
                RestoreCompatibilityState();
                // RestoreCompatibilityState returns this renderer to the
                // pre-sky snapshot (disabled in the generated scene). In the
                // Endminf compatibility branch the presentation controller,
                // not the physical sky, owns the same renderer; leaving the
                // stale snapshot in force reduces the result to the pipeline's
                // flat clear color and erases the recovered grey grid.
                if (presentationBackdropRenderer != null)
                    presentationBackdropRenderer.enabled = true;
                return false;
            }

            if (MaterialOnlyDiagnosticRequested())
            {
                RestoreCompatibilityState();
                if (Shader.IsKeywordEnabled(
                        EndfieldRecoveredSourceEnergyCoreProbe.Keyword) &&
                    !loggedMaterialOnlyDiagnostic)
                {
                    Debug.Log(
                        "Recovered source-energy material-only diagnostic: " +
                        "the material keyword remains enabled while the " +
                        "CharInfo physical-HDR sky is held off.",
                        this);
                    loggedMaterialOnlyDiagnostic = true;
                }
                return false;
            }
            loggedMaterialOnlyDiagnostic = false;

            if (!SourcePhysicalHdrRequested)
            {
                RestoreCompatibilityState();
                return false;
            }

            if (sourceCubemap == null ||
                sourceSkyMaterial == null ||
                sourceSkyMaterial.shader == null ||
                sourceSkyMaterial.shader.name != ShaderName)
            {
                RestoreCompatibilityState();
                if (!loggedMissingSource)
                {
                    Debug.LogError(
                        "Recovered CharInfo source sky was requested, but its exact " +
                        "T_hdri_006 Cubemap or recovered sky material is unavailable. " +
                        "The physical-HDR sky path remains fail-closed.",
                        this);
                    loggedMissingSource = true;
                }
                return false;
            }

            targetCamera = targetCamera != null
                ? targetCamera
                : GetComponent<Camera>();
            if (targetCamera == null)
                return false;

            if (!sourceStateApplied)
            {
                previousClearFlags = targetCamera.clearFlags;
                previousBackgroundColor = targetCamera.backgroundColor;
                previousRenderSettingsSkybox = RenderSettings.skybox;
                CachePresentationBackdropState();
                sourceStateApplied = true;
            }
            else if (presentationBackdropRenderer !=
                     appliedPresentationBackdropRenderer)
            {
                if (appliedPresentationBackdropRenderer != null)
                {
                    appliedPresentationBackdropRenderer.enabled =
                        previousBackdropEnabled;
                }
                CachePresentationBackdropState();
            }

            ApplyExactMaterialParameters();
            targetCamera.clearFlags = CameraClearFlags.Skybox;
            RenderSettings.skybox = sourceSkyMaterial;
            if (appliedPresentationBackdropRenderer != null)
                appliedPresentationBackdropRenderer.enabled = false;
            loggedMissingSource = false;
            return true;
        }

        internal static bool MaterialOnlyDiagnosticRequested()
        {
            string raw = Environment.GetEnvironmentVariable(
                MaterialOnlyDiagnosticEnvironmentVariable);
            if (string.IsNullOrWhiteSpace(raw))
                return false;

            switch (raw.Trim().ToLowerInvariant())
            {
                case "1":
                case "true":
                case "yes":
                case "on":
                    return true;
                default:
                    return false;
            }
        }

        private void ApplyExactMaterialParameters()
        {
            sourceSkyMaterial.SetTexture("_Tex", sourceCubemap);
            sourceSkyMaterial.SetColor("_Tint", SourceTint);
            sourceSkyMaterial.SetFloat("_Exposure", SourceExposure);
            sourceSkyMaterial.SetFloat("_Rotation", SourceRotationDegrees);
        }

        private void CachePresentationBackdropState()
        {
            appliedPresentationBackdropRenderer = presentationBackdropRenderer;
            previousBackdropEnabled =
                appliedPresentationBackdropRenderer != null &&
                appliedPresentationBackdropRenderer.enabled;
        }

        private void RestoreCompatibilityState()
        {
            if (!sourceStateApplied)
                return;

            if (targetCamera != null)
            {
                targetCamera.clearFlags = previousClearFlags;
                targetCamera.backgroundColor = previousBackgroundColor;
            }
            if (RenderSettings.skybox == sourceSkyMaterial)
                RenderSettings.skybox = previousRenderSettingsSkybox;
            if (appliedPresentationBackdropRenderer != null)
            {
                appliedPresentationBackdropRenderer.enabled =
                    previousBackdropEnabled;
            }
            appliedPresentationBackdropRenderer = null;
            sourceStateApplied = false;
        }

        private void OnDisable()
        {
            RestoreCompatibilityState();
        }

        private void OnDestroy()
        {
            RestoreCompatibilityState();
        }
    }
}
