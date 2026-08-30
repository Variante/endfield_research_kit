using System;
using System.Runtime.CompilerServices;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Pure managed transcription of the pinned, unpatched Endfield secondary-dynamics
    /// TimeManager scalar setup and per-team substep clock. It has no runtime hook and
    /// deliberately rejects the unaudited IFix route and scalar-power inputs above 90 Hz.
    /// </summary>
    public static class EndfieldSecondaryDynamicsTimeStepper
    {
        public const int DefaultSimulationFrequency = 90;
        public const int DefaultMaxSimulationCountPerFrame = 3;
        public const float DefaultGlobalTimeScale = 1f;
        public const ulong FlagValid = 0x1UL;
        public const ulong FlagReset = 0x4UL;
        public const ulong FlagTimeReset = 0x8UL;
        public const ulong FlagSyncSuspend = 0x10UL;
        public const ulong FlagStepRunning = 0x80UL;

        private const float PausedClockEpsilon = 0.0001f;

        public enum ExecutionRoute
        {
            Unpatched = 0,
            IFixPatched = 1,
        }

        public readonly struct TimeManagerScalars
        {
            public readonly int SimulationFrequency;
            public readonly int MaxSimulationCountPerFrame;
            public readonly float GlobalTimeScale;
            public readonly float SimulationDeltaTime;
            public readonly float MaxDeltaTime;
            public readonly Float4 SimulationPower;

            internal TimeManagerScalars(
                int simulationFrequency,
                int maxSimulationCountPerFrame,
                float globalTimeScale,
                float simulationDeltaTime,
                float maxDeltaTime,
                Float4 simulationPower)
            {
                SimulationFrequency = simulationFrequency;
                MaxSimulationCountPerFrame = maxSimulationCountPerFrame;
                GlobalTimeScale = globalTimeScale;
                SimulationDeltaTime = simulationDeltaTime;
                MaxDeltaTime = maxDeltaTime;
                SimulationPower = simulationPower;
            }
        }

        public readonly struct Float4
        {
            public readonly float X;
            public readonly float Y;
            public readonly float Z;
            public readonly float W;

            public Float4(float x, float y, float z, float w)
            {
                X = x;
                Y = y;
                Z = z;
                W = w;
            }
        }

        public struct TeamState
        {
            public ulong Flag;
            public float Time;
            public float OldTime;
            public float NowUpdateTime;
            public float OldUpdateTime;
            public float FrameUpdateTime;
            public float FrameOldTime;
            public float TimeScale;
            public int UpdateCount;
            public int SkipCount;
            public float FrameInterpolation;
            public int ResetSimulationToAnimationPose;
        }

        public readonly struct TeamFrameInput
        {
            public readonly bool IsEnabled;
            public readonly bool IsCullingInvisible;
            public readonly bool IsFixedUpdate;
            public readonly bool IsUnscaled;
            public readonly float UnityFrameDeltaTime;
            public readonly float UnityFrameFixedDeltaTime;
            public readonly float UnityFrameUnscaledDeltaTime;

            public TeamFrameInput(
                bool isEnabled,
                bool isCullingInvisible,
                bool isFixedUpdate,
                bool isUnscaled,
                float unityFrameDeltaTime,
                float unityFrameFixedDeltaTime,
                float unityFrameUnscaledDeltaTime)
            {
                IsEnabled = isEnabled;
                IsCullingInvisible = isCullingInvisible;
                IsFixedUpdate = isFixedUpdate;
                IsUnscaled = isUnscaled;
                UnityFrameDeltaTime = unityFrameDeltaTime;
                UnityFrameFixedDeltaTime = unityFrameFixedDeltaTime;
                UnityFrameUnscaledDeltaTime = unityFrameUnscaledDeltaTime;
            }
        }

        public static TimeManagerScalars CreateRetailDefault(
            ExecutionRoute route = ExecutionRoute.Unpatched)
        {
            return CreateSupportedScalars(
                DefaultSimulationFrequency,
                DefaultMaxSimulationCountPerFrame,
                DefaultGlobalTimeScale,
                route);
        }

        public static TimeManagerScalars CreateSupportedScalars(
            int simulationFrequency,
            int maxSimulationCountPerFrame,
            float globalTimeScale,
            ExecutionRoute route = ExecutionRoute.Unpatched)
        {
            RequireUnpatched(route);
            RequireFinite(globalTimeScale, nameof(globalTimeScale));

            int frequency = Clamp(simulationFrequency, 30, 150);
            int maxCount = Clamp(maxSimulationCountPerFrame, 1, 5);
            float clampedGlobalScale = Clamp(globalTimeScale, 0f, 1f);
            float simulationDeltaTime = Divide(1f, (float)frequency);
            float maxDeltaTime = Multiply((float)maxCount, simulationDeltaTime);
            float basePower = Divide(90f, (float)frequency);
            basePower = basePower < 1f ? basePower : 1f;

            // The pinned scalar helper is closed only for (basePower=1, exponent=1.8).
            // Reject before returning a partially usable configuration.
            if (SingleToUInt32Bits(basePower) != SingleToUInt32Bits(1f))
                throw new NotSupportedException(
                    "The nondefault Endfield scalar-power helper is not recovered; frequencies above 90 Hz fail closed.");

            return new TimeManagerScalars(
                frequency,
                maxCount,
                clampedGlobalScale,
                simulationDeltaTime,
                maxDeltaTime,
                new Float4(basePower, basePower, basePower, 1f));
        }

        /// <summary>
        /// Executes AlwaysTeamUpdatePostJob's closed accumulator path for one already
        /// selected team. Ineligible and culling-invisible teams are intentionally inert.
        /// Returns the team's resulting update count for max-count reduction.
        /// </summary>
        public static int AccumulateTeam(
            ref TeamState team,
            TeamFrameInput frame,
            TimeManagerScalars timeManager,
            ExecutionRoute route = ExecutionRoute.Unpatched)
        {
            RequireUnpatched(route);
            ValidateTimeManager(timeManager);
            ValidateFrame(frame);
            ValidateTeam(team);

            if (!frame.IsEnabled || frame.IsCullingInvisible)
                return 0;

            float selectedDelta = frame.IsFixedUpdate
                ? frame.UnityFrameFixedDeltaTime
                : (frame.IsUnscaled ? frame.UnityFrameUnscaledDeltaTime : frame.UnityFrameDeltaTime);
            float effectiveScale = frame.IsUnscaled
                ? team.TimeScale
                : Multiply(team.TimeScale, timeManager.GlobalTimeScale);
            if ((team.Flag & FlagSyncSuspend) != 0)
                effectiveScale = 0f;

            float scaledDelta = Multiply(effectiveScale, selectedDelta);
            float candidateTime = Add(team.Time, scaledDelta);
            float elapsed = Subtract(candidateTime, team.NowUpdateTime);
            float ratio = Divide(elapsed, timeManager.SimulationDeltaTime);
            int rawCount = TruncateToInt32(ratio);
            int updateCount = rawCount >= timeManager.MaxSimulationCountPerFrame
                ? timeManager.MaxSimulationCountPerFrame
                : rawCount;
            int skipCount = rawCount - updateCount;
            if (skipCount > 0)
            {
                float skippedDuration = Multiply((float)skipCount, timeManager.SimulationDeltaTime);
                candidateTime = Subtract(candidateTime, skippedDuration);
            }

            team.OldTime = team.Time;
            team.Time = candidateTime;
            team.UpdateCount = updateCount;
            team.SkipCount = skipCount;

            if (team.ResetSimulationToAnimationPose != 0)
            {
                team.NowUpdateTime = candidateTime;
                team.UpdateCount = 0;
                team.SkipCount = 0;
                team.Flag |= FlagReset;
            }
            else if (updateCount > 0 && effectiveScale == 0f)
            {
                team.NowUpdateTime = Add(Subtract(candidateTime, timeManager.SimulationDeltaTime), PausedClockEpsilon);
                team.UpdateCount = 0;
                team.SkipCount = 0;
            }
            else if (updateCount > 0)
            {
                team.OldUpdateTime = team.NowUpdateTime;
                team.FrameOldTime = team.FrameUpdateTime;
                team.FrameUpdateTime = candidateTime;
            }

            return team.UpdateCount > 0 ? team.UpdateCount : 0;
        }

        public static int ReduceMaximumUpdateCount(int currentMaximum, int teamUpdateCount)
        {
            return teamUpdateCount > currentMaximum ? teamUpdateCount : currentMaximum;
        }

        /// <summary>
        /// Executes the closed clock portion of SimulationStepTeamUpdate. The caller owns
        /// the solver body; false means this team returns before solver work.
        /// </summary>
        public static bool ExecuteTeamStepClock(
            ref TeamState team,
            int updateIndex,
            float simulationDeltaTime,
            ExecutionRoute route = ExecutionRoute.Unpatched)
        {
            RequireUnpatched(route);
            if (updateIndex < 0)
                throw new ArgumentOutOfRangeException(nameof(updateIndex));
            RequirePositiveFinite(simulationDeltaTime, nameof(simulationDeltaTime));
            ValidateTeam(team);

            bool runs = updateIndex < team.UpdateCount;
            if (!runs)
            {
                team.Flag &= ~FlagStepRunning;
                return false;
            }

            team.Flag |= FlagStepRunning;
            team.NowUpdateTime = Add(team.NowUpdateTime, simulationDeltaTime);
            float denominator = Subtract(team.Time, team.FrameOldTime);
            if (denominator > 0f)
            {
                float numerator = Subtract(team.NowUpdateTime, team.FrameOldTime);
                float interpolation = Divide(numerator, denominator);
                team.FrameInterpolation = Clamp(interpolation, 0f, 1f);
            }
            else
            {
                team.FrameInterpolation = 1f;
            }

            return true;
        }

        private static void ValidateTimeManager(TimeManagerScalars value)
        {
            if (value.SimulationFrequency < 30 || value.SimulationFrequency > 90 ||
                value.MaxSimulationCountPerFrame < 1 || value.MaxSimulationCountPerFrame > 5)
                throw new ArgumentException("TimeManager scalars were not produced by the supported pinned route.", nameof(value));
            RequirePositiveFinite(value.SimulationDeltaTime, nameof(value.SimulationDeltaTime));
            RequirePositiveFinite(value.MaxDeltaTime, nameof(value.MaxDeltaTime));
            RequireFinite(value.GlobalTimeScale, nameof(value.GlobalTimeScale));
            if (SingleToUInt32Bits(value.SimulationPower.W) != SingleToUInt32Bits(1f))
                throw new NotSupportedException("A nondefault scalar-power value is unsupported.");
        }

        private static void ValidateFrame(TeamFrameInput frame)
        {
            RequireFinite(frame.UnityFrameDeltaTime, nameof(frame.UnityFrameDeltaTime));
            RequireFinite(frame.UnityFrameFixedDeltaTime, nameof(frame.UnityFrameFixedDeltaTime));
            RequireFinite(frame.UnityFrameUnscaledDeltaTime, nameof(frame.UnityFrameUnscaledDeltaTime));
        }

        private static void ValidateTeam(TeamState team)
        {
            RequireFinite(team.Time, nameof(team.Time));
            RequireFinite(team.OldTime, nameof(team.OldTime));
            RequireFinite(team.NowUpdateTime, nameof(team.NowUpdateTime));
            RequireFinite(team.OldUpdateTime, nameof(team.OldUpdateTime));
            RequireFinite(team.FrameUpdateTime, nameof(team.FrameUpdateTime));
            RequireFinite(team.FrameOldTime, nameof(team.FrameOldTime));
            RequireFinite(team.TimeScale, nameof(team.TimeScale));
            RequireFinite(team.FrameInterpolation, nameof(team.FrameInterpolation));
        }

        private static void RequireUnpatched(ExecutionRoute route)
        {
            if (route != ExecutionRoute.Unpatched)
                throw new NotSupportedException("The IFix-patched secondary-dynamics route is not recovered.");
        }

        private static void RequireFinite(float value, string name)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
                throw new ArgumentOutOfRangeException(name, "A finite binary32 value is required.");
        }

        private static void RequirePositiveFinite(float value, string name)
        {
            RequireFinite(value, name);
            if (!(value > 0f))
                throw new ArgumentOutOfRangeException(name, "A positive binary32 value is required.");
        }

        private static int TruncateToInt32(float value)
        {
            RequireFinite(value, nameof(value));
            if (value < int.MinValue || value >= 2147483648f)
                throw new OverflowException("The native cvttss2si input is outside the supported finite Int32 range.");
            return (int)value;
        }

        private static int Clamp(int value, int minimum, int maximum)
        {
            return value < minimum ? minimum : (value > maximum ? maximum : value);
        }

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Add(float left, float right) => left + right;

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Subtract(float left, float right) => left - right;

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Multiply(float left, float right) => left * right;

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Divide(float left, float right) => left / right;

        private static float Clamp(float value, float minimum, float maximum)
        {
            return value < minimum ? minimum : (value > maximum ? maximum : value);
        }

        private static uint SingleToUInt32Bits(float value)
        {
            byte[] bytes = BitConverter.GetBytes(value);
            return BitConverter.ToUInt32(bytes, 0);
        }
    }
}
