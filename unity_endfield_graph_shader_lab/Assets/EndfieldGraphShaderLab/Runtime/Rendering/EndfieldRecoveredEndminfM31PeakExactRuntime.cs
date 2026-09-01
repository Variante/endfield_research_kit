using System;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Default-off temporal admission for the exact M31 shell transport.
    /// Proven packets use two queue-3000 insertion points. The retained peak
    /// packet has a third draw after M18, but remains inadmissible until the
    /// corrected observer validates the SceneColor chronology for all three
    /// events. Unsupported or unvalidated schedules use the ordinary renderer.
    /// </summary>
    public static class EndfieldRecoveredEndminfM31PeakExactRuntime
    {
        internal const string EnvironmentVariable =
            "ENDFIELD_RECOVERED_ENDMINF_M31_PEAK_EXACT";
        private const string NativeLibrary = "OriginalDxbcSwapPlugin";
        private const string MaterialName = "M_fx_endminm_gfx_31";

        private static readonly List<ParticleSystemRenderer> Renderers =
            new List<ParticleSystemRenderer>();
        private static IntPtr renderEvent;
        private static bool prepared;
        private static bool failed;
        private static bool active;
        private static int nextEventId;
        private static int expectedEventCount;
        private static int selectedScheduleProfile;
        private static bool submissionPending;
        private static bool submittedThisFrame;
        private static bool validatedThisFrame;
        private static string failure = string.Empty;
        private static int selectedPacket = -1;
        private static int selectedPacketThisFrame = -1;
        private static uint validatedDrawCount;
        private static bool loggedActivation;
        private static bool loggedValidation;
        private static bool loggedFailure;
        private static bool loggedAdmission;
        private static bool loggedMissingRenderers;

        public static bool Requested => string.Equals(
            System.Environment.GetEnvironmentVariable(EnvironmentVariable),
            "1", StringComparison.Ordinal);

        public static string Failure => failure;
        public static bool ActiveThisFrame => active;
        public static bool SubmittedThisFrame => submittedThisFrame;
        public static bool ValidatedThisFrame => validatedThisFrame;
        public static int SelectedPacketThisFrame => selectedPacketThisFrame;
        public static int SourceFrameThisFrame =>
            selectedPacketThisFrame >= 0 &&
            EndfieldRecoveredM31PeakCaptureData.SourceFrames != null &&
            selectedPacketThisFrame <
                EndfieldRecoveredM31PeakCaptureData.SourceFrames.Length
                ? EndfieldRecoveredM31PeakCaptureData
                    .SourceFrames[selectedPacketThisFrame]
                : -1;
        internal static bool HasPendingSchedule =>
            nextEventId > 0 && nextEventId < expectedEventCount;
        public static bool HasPendingValidation => submissionPending;

        internal static bool PrepareBeforeCulling(Camera camera)
        {
            active = false;
            selectedPacket = -1;
            selectedPacketThisFrame = -1;
            nextEventId = 0;
            expectedEventCount = 0;
            selectedScheduleProfile =
                EndfieldRecoveredM31PeakCaptureData.ScheduleUnsupported;
            submittedThisFrame = false;
            validatedThisFrame = false;
            if (!Requested || failed)
            {
                RestoreRenderers();
                return false;
            }
            if (SystemInfo.graphicsDeviceType != GraphicsDeviceType.Direct3D11)
                return Fail("exact M31 peak transport requires Direct3D11");
            if (camera == null ||
                camera.GetComponent<EndfieldHGOperatorPresentation>() == null)
            {
                RestoreRenderers();
                return false;
            }
            EndfieldHGOperatorLightRig lightRig =
                camera.GetComponent<EndfieldHGOperatorLightRig>();
            if (lightRig == null || lightRig.actorRoot == null ||
                !string.Equals(lightRig.actorRoot.name, "Endminf",
                    StringComparison.OrdinalIgnoreCase))
            {
                RestoreRenderers();
                return false;
            }
            if (!prepared && !PrepareNative())
                return false;

            float seconds = ResolveOverviewSeconds(lightRig.actorRoot);
            selectedPacket = float.IsNaN(seconds) ? -1 :
                ResolveNearestPacket(seconds);
            selectedPacketThisFrame = selectedPacket;
            active = selectedPacket >= 0 && IsSupportedSchedule(
                EndfieldRecoveredM31PeakCaptureData
                    .ScheduleProfiles[selectedPacket],
                EndfieldRecoveredM31PeakCaptureData.DrawCounts[selectedPacket],
                EndfieldRecoveredM31PeakCaptureData
                    .ThirdEventAfterM18Observed[selectedPacket],
                EndfieldRecoveredM31PeakCaptureData
                    .ChronologyValidated[selectedPacket]);
            if (active)
            {
                expectedEventCount =
                    EndfieldRecoveredM31PeakCaptureData.DrawCounts[selectedPacket];
                selectedScheduleProfile =
                    EndfieldRecoveredM31PeakCaptureData
                        .ScheduleProfiles[selectedPacket];
                try
                {
                    if (Native.SetTemporalPacketIndex(
                            unchecked((uint)selectedPacket)) != 1)
                        return Fail("the native M31 temporal packet selector " +
                            "rejected split-compatible packet " +
                            selectedPacket);
                }
                catch (Exception exception)
                {
                    return Fail("the native M31 temporal packet selector " +
                        "failed: " + exception.Message);
                }
            }
            if (!loggedAdmission)
            {
                Debug.Log("Recovered exact Endminf M31 temporal admission: " +
                    "renderers=" + Renderers.Count + ", phase=" +
                    seconds.ToString("F6") + ", packet=" + selectedPacket +
                    ", schedule=" + selectedScheduleProfile +
                    ", chronologyValidated=" + active + ".");
                loggedAdmission = true;
            }
            SetRendererSuppression(active);
            return active;
        }

        private static bool PrepareNative()
        {
            Renderers.Clear();
            foreach (ParticleSystemRenderer renderer in
                     UnityEngine.Object.FindObjectsOfType<ParticleSystemRenderer>(true))
            {
                if (renderer == null || !renderer.gameObject.scene.IsValid())
                    continue;
                Material material = renderer.sharedMaterial;
                if (material != null && material.name == MaterialName)
                    Renderers.Add(renderer);
            }
            if (Renderers.Count == 0)
            {
                if (!loggedMissingRenderers)
                {
                    Debug.Log("Recovered exact Endminf M31 peak is waiting for " +
                        "runtime-spawned M_fx_endminm_gfx_31 renderers.");
                    loggedMissingRenderers = true;
                }
                return false;
            }
            float[] phases = EndfieldRecoveredM31PeakCaptureData.PhaseSeconds;
            int[] frames = EndfieldRecoveredM31PeakCaptureData.SourceFrames;
            int[] drawCounts = EndfieldRecoveredM31PeakCaptureData.DrawCounts;
            int[] firstDrawOrdinals =
                EndfieldRecoveredM31PeakCaptureData.FirstDrawOrdinals;
            int[] lastDrawOrdinals =
                EndfieldRecoveredM31PeakCaptureData.LastDrawOrdinals;
            bool[] nativeOrderCompatible =
                EndfieldRecoveredM31PeakCaptureData.NativeOrderCompatible;
            int[] scheduleProfiles =
                EndfieldRecoveredM31PeakCaptureData.ScheduleProfiles;
            bool[] chronologyValidated =
                EndfieldRecoveredM31PeakCaptureData.ChronologyValidated;
            int[] interleavedM29M30Counts =
                EndfieldRecoveredM31PeakCaptureData.InterleavedM29M30Counts;
            bool[] thirdEventAfterM18Observed =
                EndfieldRecoveredM31PeakCaptureData
                    .ThirdEventAfterM18Observed;
            string[] hashes =
                EndfieldRecoveredM31PeakCaptureData.TemporalMetadataSha256;
            int packetCount = EndfieldRecoveredM31PeakCaptureData.PacketCount;
            if (!EndfieldRecoveredM31PeakCaptureData.PayloadPrepared ||
                !EndfieldRecoveredM31PeakCaptureData.DepthContractReady ||
                phases == null || frames == null || drawCounts == null ||
                firstDrawOrdinals == null || lastDrawOrdinals == null ||
                nativeOrderCompatible == null || scheduleProfiles == null ||
                chronologyValidated == null ||
                hashes == null || packetCount < 2 ||
                interleavedM29M30Counts == null ||
                thirdEventAfterM18Observed == null ||
                phases.Length != packetCount || frames.Length != packetCount ||
                drawCounts.Length != packetCount ||
                firstDrawOrdinals.Length != packetCount ||
                lastDrawOrdinals.Length != packetCount ||
                nativeOrderCompatible.Length != packetCount ||
                scheduleProfiles.Length != packetCount ||
                chronologyValidated.Length != packetCount ||
                interleavedM29M30Counts.Length != packetCount ||
                thirdEventAfterM18Observed.Length != packetCount ||
                hashes.Length != packetCount)
            {
                return Fail("the generated M31 temporal contract is incomplete");
            }
            bool foundAnchor = false;
            for (int index = 0; index < packetCount; ++index)
            {
                if (index > 0 && (phases[index] <= phases[index - 1] ||
                                  frames[index] <= frames[index - 1]))
                    return Fail("the generated M31 temporal order is invalid");
                if (drawCounts[index] <= 0 || string.IsNullOrEmpty(hashes[index]))
                    return Fail("the generated M31 packet identity is incomplete");
                if (firstDrawOrdinals[index] > lastDrawOrdinals[index] ||
                    lastDrawOrdinals[index] - firstDrawOrdinals[index] + 1 <
                        drawCounts[index])
                    return Fail("the generated M31 owner order is invalid");
                if (nativeOrderCompatible[index] !=
                    (lastDrawOrdinals[index] - firstDrawOrdinals[index] + 1 ==
                        drawCounts[index]))
                    return Fail("the generated M31 transport-order gate drifted");
                int expectedSchedule = drawCounts[index] == 2 &&
                        interleavedM29M30Counts[index] == 2
                    ? EndfieldRecoveredM31PeakCaptureData
                        .ScheduleQueue3000Interval2
                    : drawCounts[index] == 3 &&
                        thirdEventAfterM18Observed[index]
                    ? EndfieldRecoveredM31PeakCaptureData
                        .ScheduleQueue3000ThenPostM18_3
                    : EndfieldRecoveredM31PeakCaptureData.ScheduleUnsupported;
                if (scheduleProfiles[index] != expectedSchedule)
                    return Fail("the generated M31 schedule profile drifted");
                if ((expectedSchedule == EndfieldRecoveredM31PeakCaptureData
                            .ScheduleQueue3000Interval2 &&
                        !chronologyValidated[index]) ||
                    (expectedSchedule == EndfieldRecoveredM31PeakCaptureData
                            .ScheduleUnsupported &&
                        chronologyValidated[index]))
                    return Fail("the generated M31 chronology validation gate " +
                        "drifted");
                if (interleavedM29M30Counts[index] < 0 ||
                    nativeOrderCompatible[index] &&
                    interleavedM29M30Counts[index] != 0)
                    return Fail("the generated M31/M29/M30 owner order drifted");
                bool expectedThirdEventAfterM18 = drawCounts[index] == 3;
                if (thirdEventAfterM18Observed[index] !=
                    expectedThirdEventAfterM18)
                    return Fail("the generated M31 third-event M18 boundary " +
                        "drifted");
                if (frames[index] ==
                    EndfieldRecoveredM31PeakCaptureData.AnchorFrame)
                {
                    foundAnchor = Mathf.Abs(phases[index] -
                        EndfieldRecoveredM31PeakCaptureData.AnchorPhaseSeconds) <=
                        0.000001f;
                }
            }
            if (!foundAnchor)
                return Fail("the generated M31 QPC phase anchor drifted");
            try
            {
                renderEvent = Native.GetRenderEventFunc();
                if (renderEvent == IntPtr.Zero)
                    return Fail("the native M31 peak event is unavailable");
                Native.ResetRuntimeState();
            }
            catch (Exception exception)
            {
                return Fail("the native M31 peak transport could not initialize: " +
                    exception.Message);
            }
            validatedDrawCount = 0;
            nextEventId = 0;
            expectedEventCount = 0;
            selectedScheduleProfile =
                EndfieldRecoveredM31PeakCaptureData.ScheduleUnsupported;
            submissionPending = false;
            prepared = true;
            return true;
        }

        private static int ResolveNearestPacket(float seconds)
        {
            float[] phases = EndfieldRecoveredM31PeakCaptureData.PhaseSeconds;
            float leadingHalfSpacing = (phases[1] - phases[0]) * 0.5f;
            float trailingHalfSpacing =
                (phases[phases.Length - 1] - phases[phases.Length - 2]) * 0.5f;
            if (seconds < phases[0] - leadingHalfSpacing ||
                seconds > phases[phases.Length - 1] + trailingHalfSpacing)
                return -1;

            int nearest = 0;
            float nearestDistance = Mathf.Abs(seconds - phases[0]);
            for (int index = 1; index < phases.Length; ++index)
            {
                float distance = Mathf.Abs(seconds - phases[index]);
                if (distance < nearestDistance)
                {
                    nearest = index;
                    nearestDistance = distance;
                }
            }
            return nearest;
        }

        public static bool IsCapturedPhase(float overviewSeconds)
        {
            float[] phases = EndfieldRecoveredM31PeakCaptureData.PhaseSeconds;
            int[] drawCounts = EndfieldRecoveredM31PeakCaptureData.DrawCounts;
            int[] scheduleProfiles =
                EndfieldRecoveredM31PeakCaptureData.ScheduleProfiles;
            bool[] chronologyValidated =
                EndfieldRecoveredM31PeakCaptureData.ChronologyValidated;
            bool[] thirdEventAfterM18Observed =
                EndfieldRecoveredM31PeakCaptureData
                    .ThirdEventAfterM18Observed;
            int packetCount = EndfieldRecoveredM31PeakCaptureData.PacketCount;
            if (float.IsNaN(overviewSeconds) ||
                !EndfieldRecoveredM31PeakCaptureData.PayloadPrepared ||
                !EndfieldRecoveredM31PeakCaptureData.DepthContractReady ||
                phases == null || drawCounts == null ||
                scheduleProfiles == null || chronologyValidated == null ||
                thirdEventAfterM18Observed == null || packetCount < 2 ||
                phases.Length != packetCount ||
                drawCounts.Length != packetCount ||
                scheduleProfiles.Length != packetCount ||
                chronologyValidated.Length != packetCount ||
                thirdEventAfterM18Observed.Length != packetCount)
                return false;
            int packet = ResolveNearestPacket(Mathf.Max(0.0f, overviewSeconds));
            return packet >= 0 && IsSupportedSchedule(
                scheduleProfiles[packet], drawCounts[packet],
                thirdEventAfterM18Observed[packet],
                chronologyValidated[packet]);
        }

        private static bool IsSupportedSchedule(
            int profile,
            int eventCount,
            bool thirdEventAfterM18,
            bool chronologyValidated)
        {
            if (!chronologyValidated || eventCount <= 0 ||
                eventCount > EndfieldRecoveredM31PeakCaptureData.MaxEventCount)
                return false;
            if (profile == EndfieldRecoveredM31PeakCaptureData
                    .ScheduleQueue3000Interval2)
                return eventCount == 2 && !thirdEventAfterM18;
            if (profile == EndfieldRecoveredM31PeakCaptureData
                    .ScheduleQueue3000ThenPostM18_3)
                return eventCount == 3 && thirdEventAfterM18;
            return false;
        }

        private static float ResolveOverviewSeconds(Transform actorRoot)
        {
            return EndfieldEndminfVisualCompatibilityClock
                .TryGetAuthenticatedSourceEffectElapsed(out float elapsed)
                ? elapsed
                : float.NaN;
        }

        internal static bool RenderFirst(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (nextEventId != 0)
                return Fail("the previous M31 schedule is incomplete");
            return RenderScheduledEvent(
                context, camera, sceneColor, sceneMV, sceneDepth, 0);
        }

        internal static bool RenderSecond(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (nextEventId != 1)
                return Fail("the second M31 event has no first event");
            if (!RenderScheduledEvent(
                    context, camera, sceneColor, sceneMV, sceneDepth, 1))
                return false;
            return expectedEventCount == 2
                ? CompleteScheduleSubmission()
                : true;
        }

        internal static bool RenderAfterM18BeforeQueue3001(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth)
        {
            if (selectedScheduleProfile != EndfieldRecoveredM31PeakCaptureData
                    .ScheduleQueue3000ThenPostM18_3)
                return true;
            if (nextEventId != 2 || expectedEventCount != 3)
                return Fail("the post-M18 M31 event has an incomplete " +
                    "two-event prefix");
            if (!RenderScheduledEvent(
                    context, camera, sceneColor, sceneMV, sceneDepth, 2))
                return false;
            return CompleteScheduleSubmission();
        }

        private static bool CompleteScheduleSubmission()
        {
            if (nextEventId != expectedEventCount)
                return Fail("the M31 schedule completed with a missing event");
            submissionPending = true;
            submittedThisFrame = true;
            if (!loggedActivation)
            {
                Debug.Log(
                    "Recovered exact Endminf M31 submitted " +
                    expectedEventCount + " scheduled events inside the " +
                    EndfieldRecoveredM31PeakCaptureData.PacketCount +
                    "-packet temporal envelope from capture " +
                    EndfieldRecoveredM31PeakCaptureData.TemporalSourceSession +
                    "; selected exact temporal payload frame " +
                    EndfieldRecoveredM31PeakCaptureData
                        .SourceFrames[selectedPacket] + ".");
                loggedActivation = true;
            }
            return true;
        }

        internal static void AbortPendingSchedule(string reason)
        {
            if (HasPendingSchedule)
                Fail(reason ?? "the M31 owner schedule failed");
        }

        private static bool RenderScheduledEvent(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth,
            int eventId)
        {
            if (eventId != nextEventId || eventId < 0 ||
                eventId >= expectedEventCount)
                return Fail("the M31 schedule event order drifted");
            if (!RenderSplitEvent(
                    context, camera, sceneColor, sceneMV, sceneDepth, eventId))
                return false;
            nextEventId++;
            return true;
        }

        private static bool RenderSplitEvent(
            ScriptableRenderContext context,
            Camera camera,
            EndfieldRecoveredSceneColorHandle sceneColor,
            RenderTexture sceneMV,
            RenderTexture sceneDepth,
            int eventId)
        {
            if (!Requested || failed || !prepared || !active ||
                selectedPacket < 0)
                return false;
            if (camera == null || sceneMV == null || sceneDepth == null ||
                renderEvent == IntPtr.Zero)
                return Fail("the exact M31 peak render resources are incomplete");
            IntPtr depthPointer = sceneDepth.GetNativeTexturePtr();
            if (depthPointer == IntPtr.Zero)
                return Fail("the exact M31 peak depth pointer is null");
            try
            {
                if (Native.SetDepthResource(depthPointer) != 1)
                    return Fail("the native M31 peak depth gate rejected its input");
            }
            catch (Exception exception)
            {
                return Fail("the native M31 peak depth gate failed: " +
                    exception.Message);
            }

            var command = new CommandBuffer
            {
                name = "Recovered exact Endminf M31 split SceneColor/SceneMV draw"
            };
            command.SetRenderTarget(
                new[] { sceneColor.Target, new RenderTargetIdentifier(sceneMV) },
                new RenderTargetIdentifier(BuiltinRenderTextureType.None));
            command.IssuePluginEvent(renderEvent, eventId);
            context.ExecuteCommandBuffer(command);
            command.Release();
            return true;
        }

        public static bool ValidatePendingAfterSynchronizedRender(
            out string validationFailure)
        {
            validationFailure = string.Empty;
            if (!submissionPending)
                return true;
            submissionPending = false;
            try
            {
                uint draws = Native.GetDrawCount();
                uint failures = Native.GetFailureCount();
                int result = Native.GetLastResult();
                uint submittedDraws = draws >= validatedDrawCount
                    ? draws - validatedDrawCount
                    : uint.MaxValue;
                if (submittedDraws != expectedEventCount ||
                    failures != 0 || result < 0)
                {
                    validationFailure = "native M31 peak result drifted: draws=" +
                        draws + ", failures=" + failures + ", hresult=0x" +
                        unchecked((uint)result).ToString("x8") +
                        ", previousValidatedDraws=" + validatedDrawCount +
                        ", submittedDraws=" + submittedDraws;
                    return Fail(validationFailure);
                }
                validatedDrawCount = draws;
                validatedThisFrame = true;
                if (!loggedValidation)
                {
                    Debug.Log("Recovered exact Endminf M31 peak validated: " +
                        expectedEventCount +
                        " scheduled events completed with S_OK.");
                    loggedValidation = true;
                }
                return true;
            }
            catch (Exception exception)
            {
                validationFailure = exception.Message;
                return Fail(validationFailure);
            }
        }

        private static bool Fail(string reason)
        {
            failed = true;
            active = false;
            selectedPacket = -1;
            nextEventId = 0;
            expectedEventCount = 0;
            selectedScheduleProfile =
                EndfieldRecoveredM31PeakCaptureData.ScheduleUnsupported;
            submissionPending = false;
            submittedThisFrame = false;
            validatedThisFrame = false;
            failure = reason ?? "unknown exact M31 peak failure";
            RestoreRenderers();
            if (!loggedFailure)
            {
                Debug.LogWarning("Recovered exact Endminf M31 peak failed closed: " +
                    failure + ".");
                loggedFailure = true;
            }
            return false;
        }

        private static void SetRendererSuppression(bool suppress)
        {
            foreach (ParticleSystemRenderer renderer in Renderers)
                if (renderer != null) renderer.enabled = !suppress;
        }

        private static void RestoreRenderers()
        {
            SetRendererSuppression(false);
        }

        private static class Native
        {
            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakRenderEventFunc")]
            internal static extern IntPtr GetRenderEventFunc();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM31PeakDepthResource")]
            internal static extern uint SetDepthResource(IntPtr sceneDepth);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcSetM31PeakTemporalPacketIndex")]
            internal static extern uint SetTemporalPacketIndex(uint packetIndex);

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcResetM31PeakRuntimeState")]
            internal static extern void ResetRuntimeState();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakDrawCount")]
            internal static extern uint GetDrawCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakFailureCount")]
            internal static extern uint GetFailureCount();

            [DllImport(NativeLibrary, EntryPoint =
                "EndfieldOriginalDxbcGetM31PeakLastResult")]
            internal static extern int GetLastResult();
        }
    }
}
