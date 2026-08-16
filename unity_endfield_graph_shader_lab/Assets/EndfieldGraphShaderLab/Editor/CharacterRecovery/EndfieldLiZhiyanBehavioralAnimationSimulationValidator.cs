using System;
using UnityEditor;
using UnityEngine;
using EndfieldGraphShaderLab;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Focused construction/lifecycle validator for the stock behavioural
    /// simulation.  It deliberately verifies the fail-closed labels instead
    /// of treating a valid Unity graph as proof of retail native equivalence.
    /// </summary>
    public static class EndfieldLiZhiyanBehavioralAnimationSimulationValidator
    {
        [MenuItem(
            "Endfield/Character Recovery Lab/Validate Li Zhiyan Behavioral Animation Simulation")]
        public static void ValidateMenu()
        {
            ValidateCommandLine();
        }

        public static void ValidateCommandLine()
        {
            GameObject root = new GameObject(
                "LiZhiyanBehavioralAnimationSimulationValidation");
            AnimationClip clip = new AnimationClip
            {
                name = "A_fxui__lizhiyan_overview_start_01.Validation",
                legacy = false,
            };
            try
            {
                root.AddComponent<Animator>();
                GameObject rendererObject = new GameObject("S_fx_lzy_validation");
                rendererObject.transform.SetParent(root.transform, false);
                MeshRenderer renderer = rendererObject.AddComponent<MeshRenderer>();
                EndfieldLiZhiyanBehavioralAnimationSimulation simulation =
                    root.AddComponent<EndfieldLiZhiyanBehavioralAnimationSimulation>();
                simulation.ConfigureSourceIdentity(
                    "P_fxui_lizhiyan_overview_start_01",
                    2305038813790631653L,
                    7360398354216100382L,
                    clip,
                    0.25f);
                simulation.ConfigureRendererProbeBindings(new[]
                {
                    new EndfieldLiZhiyanBehavioralAnimationSimulation.RendererProbeBinding(
                        -1741348596941359387L,
                        "S_fx_lzy_validation",
                        renderer),
                });

                Require(
                    simulation.TryConstructSimulation(out string constructionReason),
                    "Simulation construction failed: " + constructionReason);
                Require(simulation.Mode ==
                    EndfieldLiZhiyanBehavioralAnimationSimulation.SimulationMode,
                    "Simulation mode label drifted.");
                Require(simulation.Backend ==
                    EndfieldLiZhiyanBehavioralAnimationSimulation.BackendDescription,
                    "Simulation backend label drifted.");
                Require(simulation.SourceEffectSettingPathId ==
                    2305038813790631653L &&
                    simulation.SourceStartAnimationClipPathId ==
                    7360398354216100382L,
                    "Source EffectSetting/AnimationClip PathIDs drifted.");
                Require(simulation.UsesGameTime,
                    "Simulation graph is not explicitly configured for GameTime.");
                Require(simulation.GraphIsValid && simulation.GraphWasPlayed,
                    "Simulation graph was not constructed and played.");
                Require(simulation.GraphInputCount == 3,
                    "Simulation mixer does not have exactly three inputs.");
                Require(simulation.ConnectedInputCount == 1,
                    "Simulation connected an input other than slot 0.");
                Require(Mathf.Approximately(simulation.InputWeight0, 1f) &&
                    Mathf.Approximately(simulation.InputWeight1, 0f) &&
                    Mathf.Approximately(simulation.InputWeight2, 0f),
                    "Simulation mixer weights are not [1, 0, 0].");
                Require(Math.Abs(simulation.MixerSpeed - 1.0) < 1e-6 &&
                    Math.Abs(simulation.MixerTime) < 1e-6,
                    "Simulation mixer did not start at speed 1 and time 0.");

                Require(!simulation.RetailAbiEquivalent &&
                    !simulation.VisibleAdmission &&
                    !simulation.NativeRendererMappingClaimed,
                    "Simulation exposed an unsupported native or visible claim.");
                Require(!simulation.TryAdmitRetailAbi(out string retailReason) &&
                    retailReason ==
                    EndfieldLiZhiyanBehavioralAnimationSimulation.RetailAbiRefusal,
                    "Retail ABI refusal is not fail-closed.");
                Require(!simulation.TryAdmitVisibleRendering(out string visibleReason) &&
                    visibleReason == EndfieldLiZhiyanBehavioralAnimationSimulation
                        .VisibleAdmissionRefusal,
                    "Visible-admission refusal is not fail-closed.");
                Require(!simulation.TryMapRendererToNativeRecord(
                        renderer.GetInstanceID(),
                        out string nativeReason) &&
                    nativeReason == EndfieldLiZhiyanBehavioralAnimationSimulation
                        .NativeMappingRefusal,
                    "Native renderer mapping refusal is not fail-closed.");

                Require(simulation.RendererIdentityProbes.Count == 1,
                    "Renderer identity probe did not capture exactly one renderer.");
                EndfieldLiZhiyanBehavioralAnimationSimulation.RendererIdentityProbeRecord
                    record = simulation.RendererIdentityProbes[0];
                Require(record.SourceRendererPathId == -1741348596941359387L &&
                    record.Hierarchy == "S_fx_lzy_validation" &&
                    record.UnityRendererInstanceId == renderer.GetInstanceID() &&
                    record.Frame >= 0 && !record.NativeMappingClaimed,
                    "Renderer identity probe record is incomplete or claims native mapping.");

                Require(simulation.AdvanceLifetimeForValidation(0.24f),
                    "Simulation expired before its configured EffectSetting lifetime.");
                Require(simulation.GraphIsValid,
                    "Simulation graph was destroyed before the configured lifetime.");
                Require(!simulation.AdvanceLifetimeForValidation(0.02f) &&
                    simulation.LifetimeExpired && !simulation.GraphIsValid,
                    "Simulation graph was not destroyed at the configured lifetime.");

                Debug.Log(
                    "[Endfield Li Zhiyan] behavioral animation simulation validation " +
                    "passed: GameTime, three inputs, slot-0-only [1,0,0], Play/SetTime(0), " +
                    "speed 1, lifetime destruction, source IDs, renderer probe, and " +
                    "retail/native/visible fail-closed labels.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(root);
                UnityEngine.Object.DestroyImmediate(clip);
            }
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
