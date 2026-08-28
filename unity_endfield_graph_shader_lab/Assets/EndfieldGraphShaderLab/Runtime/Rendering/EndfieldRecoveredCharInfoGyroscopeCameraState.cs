using System;
using System.Globalization;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-derived specialization of Beyond.UI.CinemachineGyroscopeEffect
    /// for the centered, zero-damping CharInfo Overview Composer. The original
    /// Finalize callback applies a camera-local world-space PositionCorrection
    /// and then recenters RawOrientation toward ReferenceLookAt. It is not a
    /// portrait offset, lens shift, or image-space translation.
    /// </summary>
    public static class EndfieldRecoveredCharInfoGyroscopeCameraState
    {
        public const string ModeEnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_MODE";
        public const string InputXEnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_X";
        public const string InputYEnvironmentVariable =
            "ENDFIELD_RECOVERED_CHARINFO_GYROSCOPE_INPUT_Y";
        public const string ModeCommandLineArgument =
            "-endfield-recovered-charinfo-gyroscope-mode";
        public const string InputXCommandLineArgument =
            "-endfield-recovered-charinfo-gyroscope-input-x";
        public const string InputYCommandLineArgument =
            "-endfield-recovered-charinfo-gyroscope-input-y";

        public const float SourceTweenDurationSeconds = 2.0f;
        public const float SourceVerticalCurveScale = 0.15f;
        public const float SourceHorizontalCurveScale = -0.25f;

        public enum RecoveryMode
        {
            Off,
            NeutralCenteredInput,
            SerializedEntry,
            RecordedInputEndpoint,
        }

        private readonly struct CurveKey
        {
            public readonly float time;
            public readonly float value;
            public readonly float inSlope;
            public readonly float outSlope;

            public CurveKey(float time, float value, float inSlope, float outSlope)
            {
                this.time = time;
                this.value = value;
                this.inSlope = inSlope;
                this.outSlope = outSlope;
            }
        }

        private static readonly CurveKey[] VerticalInputCurve =
        {
            new CurveKey(-1.0f, -1.0f, 0.30492884f, 0.30492884f),
            new CurveKey(-0.5103161f, -0.85068125f, 0.504885f, 0.504885f),
            new CurveKey(0.50977415f, 0.8643059f, 0.97900516f, 0.97900516f),
            new CurveKey(1.0f, 1.0f, 0.2767991f, 0.2767991f),
        };

        private static readonly CurveKey[] HorizontalInputCurve =
        {
            new CurveKey(-1.0f, -1.0f, 0.05619042f, 0.05619042f),
            new CurveKey(-0.3998412f, -0.9662768f, 0.129704f, 0.129704f),
            new CurveKey(0.0f, 0.005836278f, 2.6192734f, 2.6192734f),
            new CurveKey(0.3447942f, 0.9737766f, 0.12496684f, 0.12496684f),
            new CurveKey(1.0f, 1.0f, 0.04002318f, 0.04002318f),
        };

        public static bool TryApplyOverview(
            Camera camera,
            string actorName,
            Vector3 referenceLookAt)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));

            RecoveryMode mode = ResolveMode();
            if (mode == RecoveryMode.Off)
                return false;

            if (!TryResolveOffsets(mode, actorName, out Vector2 offsets))
            {
                Debug.LogWarning(
                    "Recovered CharInfo gyroscope camera state failed closed: " +
                    $"mode={mode}, actor={actorName}. Recorded-input mode requires " +
                    $"{InputXEnvironmentVariable} and {InputYEnvironmentVariable} in [-1,1].");
                return false;
            }

            Vector3 basePosition = camera.transform.position;
            Quaternion baseOrientation = camera.transform.rotation;
            Quaternion centeredOrientation = Quaternion.LookRotation(
                referenceLookAt - basePosition,
                Vector3.up);
            float centeredAngleError = Quaternion.Angle(
                baseOrientation,
                centeredOrientation);
            if (centeredAngleError > 0.01f)
            {
                Debug.LogWarning(
                    "Recovered CharInfo gyroscope camera state failed closed: " +
                    "the lab specialization requires the recovered centered Overview " +
                    $"Composer, but angular error was {centeredAngleError:0.######} degrees.");
                return false;
            }

            // Exact HasLookAt callback specialization for a centered Composer:
            // PositionCorrection += RawOrientation * (offsetX, offsetY, 0),
            // then RawOrientation is rebuilt toward ReferenceLookAt. The
            // general callback also reapplies a prior angular look offset; it
            // is exactly zero for this recovered Overview configuration.
            Vector3 correction = baseOrientation *
                new Vector3(offsets.x, offsets.y, 0.0f);
            Vector3 correctedPosition = basePosition + correction;
            Quaternion correctedOrientation = Quaternion.LookRotation(
                referenceLookAt - correctedPosition,
                Vector3.up);
            camera.transform.SetPositionAndRotation(
                correctedPosition,
                correctedOrientation);

            Debug.Log(
                "Recovered CharInfo gyroscope camera state active: " +
                $"actor={actorName}, mode={ModeName(mode)}, " +
                $"offsetX={offsets.x:R}, offsetY={offsets.y:R}, " +
                $"positionCorrection=({correction.x:R},{correction.y:R},{correction.z:R}), " +
                "stage=Finalize, hasLookAt=true, centeredComposerSpecialization=true. " +
                "Live cursor/controller state is external to static game data.");
            return true;
        }

        /// <summary>
        /// Arms the source two-second OutQuad transition for the live viewer.
        /// Static editor previews still use TryApplyOverview's exact endpoint;
        /// the runtime selection edge is the owner of temporal gyroscope state.
        /// </summary>
        public static bool TryConfigureRuntimeOverview(
            Camera camera,
            string actorName,
            Vector3 referenceLookAt)
        {
            if (camera == null)
                throw new ArgumentNullException(nameof(camera));
            RecoveryMode mode = ResolveMode();
            EndfieldRecoveredCharInfoGyroscopeTween tween =
                camera.GetComponent<EndfieldRecoveredCharInfoGyroscopeTween>();
            if (mode != RecoveryMode.RecordedInputEndpoint)
            {
                if (tween != null)
                    tween.enabled = false;
                return false;
            }
            if (!TryResolveOffsets(
                    RecoveryMode.SerializedEntry,
                    actorName,
                    out Vector2 entryOffsets) ||
                !TryResolveOffsets(mode, actorName, out Vector2 targetOffsets))
            {
                if (tween != null)
                    tween.enabled = false;
                Debug.LogWarning(
                    "Recovered CharInfo runtime gyroscope tween failed closed: " +
                    $"actor={actorName}. Recorded-input mode requires " +
                    $"{InputXEnvironmentVariable} and {InputYEnvironmentVariable} in [-1,1].");
                return false;
            }
            if (tween == null)
                tween = camera.gameObject.AddComponent<EndfieldRecoveredCharInfoGyroscopeTween>();
            tween.Configure(
                camera.transform.position,
                referenceLookAt,
                entryOffsets,
                targetOffsets,
                SourceTweenDurationSeconds);
            return true;
        }

        internal static void ApplyCenteredOverviewOffsets(
            Camera camera,
            Vector3 basePosition,
            Vector3 referenceLookAt,
            Vector2 offsets)
        {
            Quaternion baseOrientation = Quaternion.LookRotation(
                referenceLookAt - basePosition,
                Vector3.up);
            Vector3 correction = baseOrientation *
                new Vector3(offsets.x, offsets.y, 0.0f);
            Vector3 correctedPosition = basePosition + correction;
            camera.transform.SetPositionAndRotation(
                correctedPosition,
                Quaternion.LookRotation(referenceLookAt - correctedPosition, Vector3.up));
        }

        public static Vector2 EvaluateSourceMouseEndpoint(
            float normalizedMouseX,
            float normalizedMouseY)
        {
            normalizedMouseX = Mathf.Clamp(normalizedMouseX, -1.0f, 1.0f);
            normalizedMouseY = Mathf.Clamp(normalizedMouseY, -1.0f, 1.0f);

            // UIGyroscopeEffect builds target=(xCurve(mouseY)*.15,
            // yCurve(mouseX)*-.25), while its DOTween setter intentionally
            // swaps target.y -> offsetX and target.x -> offsetY.
            float offsetY = EvaluateCurve(VerticalInputCurve, normalizedMouseY) *
                SourceVerticalCurveScale;
            float offsetX = EvaluateCurve(HorizontalInputCurve, normalizedMouseX) *
                SourceHorizontalCurveScale;
            return new Vector2(offsetX, offsetY);
        }

        public static Vector2 SerializedEntryOffsets(string actorName)
        {
            if (string.Equals(actorName, "Wulfa", StringComparison.OrdinalIgnoreCase))
                return new Vector2(0.2483662f, -0.143241f);
            if (string.Equals(actorName, "Zhuangfy", StringComparison.OrdinalIgnoreCase))
                return new Vector2(-0.2489724f, 0.08848439f);
            if (string.Equals(actorName, "Endminf", StringComparison.OrdinalIgnoreCase))
                return new Vector2(0.24835543f, -0.1448596f);
            return new Vector2(float.NaN, float.NaN);
        }

        private static bool TryResolveOffsets(
            RecoveryMode mode,
            string actorName,
            out Vector2 offsets)
        {
            switch (mode)
            {
                case RecoveryMode.NeutralCenteredInput:
                    offsets = EvaluateSourceMouseEndpoint(0.0f, 0.0f);
                    return true;
                case RecoveryMode.SerializedEntry:
                    offsets = SerializedEntryOffsets(actorName);
                    return IsFinite(offsets.x) && IsFinite(offsets.y);
                case RecoveryMode.RecordedInputEndpoint:
                    if (TryReadFloatSelector(
                            InputXEnvironmentVariable,
                            InputXCommandLineArgument,
                            out float inputX) &&
                        TryReadFloatSelector(
                            InputYEnvironmentVariable,
                            InputYCommandLineArgument,
                            out float inputY) &&
                        inputX >= -1.0f && inputX <= 1.0f &&
                        inputY >= -1.0f && inputY <= 1.0f)
                    {
                        offsets = EvaluateSourceMouseEndpoint(inputX, inputY);
                        return true;
                    }
                    break;
            }

            offsets = Vector2.zero;
            return false;
        }

        private static RecoveryMode ResolveMode()
        {
            string value = Environment.GetEnvironmentVariable(
                ModeEnvironmentVariable);
            string[] arguments = Environment.GetCommandLineArgs();
            string prefix = ModeCommandLineArgument + "=";
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    value = argument.Substring(prefix.Length);
            }

            if (string.IsNullOrWhiteSpace(value))
                return RecoveryMode.Off;
            value = value.Trim();
            if (string.Equals(value, "neutral", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "neutral-centered-input", StringComparison.OrdinalIgnoreCase))
            {
                return RecoveryMode.NeutralCenteredInput;
            }
            if (string.Equals(value, "serialized-entry", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "entry", StringComparison.OrdinalIgnoreCase))
            {
                return RecoveryMode.SerializedEntry;
            }
            if (string.Equals(value, "recorded-input", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "recorded-input-endpoint", StringComparison.OrdinalIgnoreCase))
            {
                return RecoveryMode.RecordedInputEndpoint;
            }
            return RecoveryMode.Off;
        }

        private static bool TryReadFloatSelector(
            string environmentVariable,
            string commandLineArgument,
            out float value)
        {
            string text = Environment.GetEnvironmentVariable(environmentVariable);
            string prefix = commandLineArgument + "=";
            string[] arguments = Environment.GetCommandLineArgs();
            for (int i = 0; i < arguments.Length; i++)
            {
                string argument = arguments[i];
                if (argument.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
                    text = argument.Substring(prefix.Length);
            }
            return float.TryParse(
                text,
                NumberStyles.Float,
                CultureInfo.InvariantCulture,
                out value) && IsFinite(value);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static float EvaluateCurve(CurveKey[] keys, float time)
        {
            if (time <= keys[0].time)
                return keys[0].value;
            int last = keys.Length - 1;
            if (time >= keys[last].time)
                return keys[last].value;

            for (int i = 0; i < last; i++)
            {
                CurveKey left = keys[i];
                CurveKey right = keys[i + 1];
                if (time > right.time)
                    continue;

                float duration = right.time - left.time;
                float t = (time - left.time) / duration;
                float t2 = t * t;
                float t3 = t2 * t;
                float h00 = 2.0f * t3 - 3.0f * t2 + 1.0f;
                float h10 = t3 - 2.0f * t2 + t;
                float h01 = -2.0f * t3 + 3.0f * t2;
                float h11 = t3 - t2;
                return h00 * left.value +
                       h10 * duration * left.outSlope +
                       h01 * right.value +
                       h11 * duration * right.inSlope;
            }
            return keys[last].value;
        }

        private static string ModeName(RecoveryMode mode)
        {
            switch (mode)
            {
                case RecoveryMode.NeutralCenteredInput:
                    return "neutral-centered-input";
                case RecoveryMode.SerializedEntry:
                    return "serialized-entry";
                case RecoveryMode.RecordedInputEndpoint:
                    return "recorded-input-endpoint";
                default:
                    return "off";
            }
        }
    }

    [DisallowMultipleComponent]
    [RequireComponent(typeof(Camera))]
    public sealed class EndfieldRecoveredCharInfoGyroscopeTween : MonoBehaviour
    {
        private Camera viewerCamera;
        private Vector3 basePosition;
        private Vector3 referenceLookAt;
        private Vector2 entryOffsets;
        private Vector2 targetOffsets;
        private float duration;
        private float elapsed;

        public Vector2 CurrentOffsets => EvaluateCurrentOffsets();

        public void Configure(
            Vector3 sourceBasePosition,
            Vector3 sourceReferenceLookAt,
            Vector2 sourceEntryOffsets,
            Vector2 sourceTargetOffsets,
            float sourceDuration)
        {
            viewerCamera = GetComponent<Camera>();
            basePosition = sourceBasePosition;
            referenceLookAt = sourceReferenceLookAt;
            entryOffsets = sourceEntryOffsets;
            targetOffsets = sourceTargetOffsets;
            duration = Mathf.Max(0.0001f, sourceDuration);
            elapsed = 0.0f;
            enabled = true;
            ApplyCurrent();
            Debug.Log(
                "Recovered CharInfo runtime gyroscope tween active: " +
                $"entry=({entryOffsets.x:R},{entryOffsets.y:R}), " +
                $"target=({targetOffsets.x:R},{targetOffsets.y:R}), " +
                $"duration={duration:R}, ease=OutQuad.");
        }

        /// <summary>
        /// Reproduces UIGyroscopeEffect's PreLate input-change edge. DOTween
        /// starts the replacement OutQuad from the value reached by the
        /// preceding tween, rather than from the serialized actor entry.
        /// </summary>
        public bool RetargetNormalizedMouseInput(
            float normalizedMouseX,
            float normalizedMouseY)
        {
            Vector2 nextTarget =
                EndfieldRecoveredCharInfoGyroscopeCameraState
                    .EvaluateSourceMouseEndpoint(
                        normalizedMouseX,
                        normalizedMouseY);
            if ((nextTarget - targetOffsets).sqrMagnitude <= 1e-10f)
                return false;

            entryOffsets = EvaluateCurrentOffsets();
            targetOffsets = nextTarget;
            elapsed = 0.0f;
            enabled = true;
            ApplyCurrent();
            return true;
        }

        private void LateUpdate()
        {
            elapsed = Mathf.Min(duration, elapsed + Time.unscaledDeltaTime);
            ApplyCurrent();
            if (elapsed >= duration)
                enabled = false;
        }

        private void ApplyCurrent()
        {
            if (viewerCamera == null)
                return;
            Vector2 offsets = EvaluateCurrentOffsets();
            EndfieldRecoveredCharInfoGyroscopeCameraState.ApplyCenteredOverviewOffsets(
                viewerCamera,
                basePosition,
                referenceLookAt,
                offsets);
        }

        private Vector2 EvaluateCurrentOffsets()
        {
            if (duration <= 0.0f)
                return targetOffsets;
            float linear = Mathf.Clamp01(elapsed / duration);
            float outQuad = 1.0f - (1.0f - linear) * (1.0f - linear);
            return Vector2.LerpUnclamped(
                entryOffsets,
                targetOffsets,
                outQuad);
        }
    }
}
