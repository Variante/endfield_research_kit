using System;
using UnityEditor;
using UnityEngine;
using Stepper = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTimeStepper;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsTimeStepperVerifier
    {
        private static readonly int[] ExpectedFirst60 =
        {
            1, 2, 1, 2, 1, 1, 2, 2, 1, 1, 2, 1, 2, 1, 2, 2, 1, 2, 1, 2,
            1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 1, 2, 1, 2, 1, 2, 1,
            2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1, 2, 1,
        };

        [MenuItem("Endfield/Character Recovery Lab/Verify Secondary Dynamics Time Stepper")]
        public static void VerifyMenu()
        {
            Verify();
            Debug.Log(
                "Verified exact pinned unpatched secondary-dynamics TimeManager/substep helper: " +
                "first-60 total 89, first-1200 total 1800, and exact non-strict 1/2 cadence.");
        }

        public static void Verify()
        {
            VerifyRetailDefaults();
            VerifyOrdinaryTrace();
            VerifyBacklogClampAndStepClock();
            VerifyDeltaSelectionAndClosedBranches();
            VerifyFailClosedBoundaries();
        }

        private static void VerifyRetailDefaults()
        {
            Stepper.TimeManagerScalars scalars = Stepper.CreateRetailDefault();
            Require(scalars.SimulationFrequency == 90, "default simulation frequency");
            Require(scalars.MaxSimulationCountPerFrame == 3, "default max count");
            RequireBits(scalars.GlobalTimeScale, 0x3f800000U, "default global scale");
            RequireBits(scalars.SimulationDeltaTime, 0x3c360b61U, "default simulation dt");
            RequireBits(scalars.MaxDeltaTime, 0x3d088889U, "default max dt");
            RequireBits(scalars.SimulationPower.X, 0x3f800000U, "default power x");
            RequireBits(scalars.SimulationPower.W, 0x3f800000U, "default power w");

            Stepper.TimeManagerScalars clamped = Stepper.CreateSupportedScalars(1, 99, -4f);
            Require(clamped.SimulationFrequency == 30, "frequency lower clamp");
            Require(clamped.MaxSimulationCountPerFrame == 5, "count upper clamp");
            RequireBits(clamped.GlobalTimeScale, 0U, "global scale lower clamp");
        }

        private static void VerifyOrdinaryTrace()
        {
            Stepper.TimeManagerScalars scalars = Stepper.CreateRetailDefault();
            Stepper.TeamFrameInput frame = NormalFrame(1f / 60f);
            Stepper.TeamState team = ZeroTeam();
            int total60 = 0;
            int total1200 = 0;
            for (int frameIndex = 0; frameIndex < 1200; frameIndex++)
            {
                int count = Stepper.AccumulateTeam(ref team, frame, scalars);
                if (frameIndex < ExpectedFirst60.Length)
                {
                    Require(count == ExpectedFirst60[frameIndex], "frame " + frameIndex + " count");
                    total60 += count;
                }

                Require(count == 1 || count == 2, "ordinary count domain");
                total1200 += count;
                for (int updateIndex = 0; updateIndex < count; updateIndex++)
                    Require(Stepper.ExecuteTeamStepClock(ref team, updateIndex, scalars.SimulationDeltaTime), "step gate");
                Require(!Stepper.ExecuteTeamStepClock(ref team, count, scalars.SimulationDeltaTime), "step return gate");

                if (frameIndex == 11)
                {
                    RequireBits(team.Time, 0x3e4ccccdU, "first-12 final time");
                    RequireBits(team.NowUpdateTime, 0x3e416c17U, "first-12 final now update time");
                }
            }

            Require(total60 == 89, "first-60 total");
            Require(total1200 == 1800, "first-1200 total");
        }

        private static void VerifyBacklogClampAndStepClock()
        {
            Stepper.TimeManagerScalars scalars = Stepper.CreateRetailDefault();
            Stepper.TeamState team = ZeroTeam();
            int count = Stepper.AccumulateTeam(ref team, NormalFrame(0.1f), scalars);
            Require(count == 3, "backlog max clamp");
            Require(team.SkipCount == 6, "backlog skip count");
            RequireBits(team.Time, 0x3d088888U, "backlog candidate trim");

            float previousNow = team.NowUpdateTime;
            Require(Stepper.ExecuteTeamStepClock(ref team, 0, scalars.SimulationDeltaTime), "first backlog step");
            RequireBits(team.NowUpdateTime, Bits(previousNow + scalars.SimulationDeltaTime), "clock binary32 add");
            Require((team.Flag & Stepper.FlagStepRunning) != 0, "running flag set");
            Require(!Stepper.ExecuteTeamStepClock(ref team, 3, scalars.SimulationDeltaTime), "out-of-prefix return");
            Require((team.Flag & Stepper.FlagStepRunning) == 0, "running flag clear");
        }

        private static void VerifyDeltaSelectionAndClosedBranches()
        {
            Stepper.TimeManagerScalars scalars = Stepper.CreateRetailDefault();

            Stepper.TeamState fixedTeam = ZeroTeam();
            Stepper.TeamFrameInput fixedFrame = new Stepper.TeamFrameInput(
                true, false, true, false, 0.5f, 1f / 60f, 0.25f);
            Require(Stepper.AccumulateTeam(ref fixedTeam, fixedFrame, scalars) == 1, "fixed delta selection");

            Stepper.TeamState unscaledTeam = ZeroTeam();
            Stepper.TeamFrameInput unscaledFrame = new Stepper.TeamFrameInput(
                true, false, false, true, 0.5f, 0.25f, 1f / 60f);
            Require(Stepper.AccumulateTeam(ref unscaledTeam, unscaledFrame, scalars) == 1, "unscaled delta selection");

            Stepper.TeamState resetTeam = ZeroTeam();
            resetTeam.ResetSimulationToAnimationPose = 1;
            Require(Stepper.AccumulateTeam(ref resetTeam, NormalFrame(1f / 60f), scalars) == 0, "reset count clear");
            Require((resetTeam.Flag & Stepper.FlagReset) != 0, "reset flag set");
            RequireBits(resetTeam.NowUpdateTime, Bits(resetTeam.Time), "reset clock snap");

            Stepper.TeamState suspended = ZeroTeam();
            suspended.Flag = Stepper.FlagSyncSuspend;
            suspended.NowUpdateTime = -0.02f;
            Require(Stepper.AccumulateTeam(ref suspended, NormalFrame(1f / 60f), scalars) == 0, "suspended pending count clear");
            float expectedPausedNow = (suspended.Time - scalars.SimulationDeltaTime) + 0.0001f;
            RequireBits(suspended.NowUpdateTime, Bits(expectedPausedNow), "suspended clock epsilon");

            Stepper.TeamState inert = ZeroTeam();
            Stepper.TeamState before = inert;
            Stepper.TeamFrameInput culled = new Stepper.TeamFrameInput(
                true, true, false, false, 1f, 1f, 1f);
            Require(Stepper.AccumulateTeam(ref inert, culled, scalars) == 0, "culled return");
            RequireBits(inert.Time, Bits(before.Time), "culled inert state");
        }

        private static void VerifyFailClosedBoundaries()
        {
            Expect<NotSupportedException>(() => Stepper.CreateRetailDefault(Stepper.ExecutionRoute.IFixPatched));
            Expect<NotSupportedException>(() => Stepper.CreateSupportedScalars(91, 3, 1f));

            Stepper.TimeManagerScalars scalars = Stepper.CreateRetailDefault();
            Stepper.TeamState team = ZeroTeam();
            Stepper.TeamState before = team;
            Expect<NotSupportedException>(() =>
                Stepper.AccumulateTeam(ref team, NormalFrame(1f / 60f), scalars, Stepper.ExecutionRoute.IFixPatched));
            RequireBits(team.Time, Bits(before.Time), "IFix rejection before mutation");

            team = ZeroTeam();
            before = team;
            Stepper.TeamFrameInput malformed = new Stepper.TeamFrameInput(
                true, false, false, false, float.NaN, 0f, 0f);
            Expect<ArgumentOutOfRangeException>(() => Stepper.AccumulateTeam(ref team, malformed, scalars));
            RequireBits(team.Time, Bits(before.Time), "malformed rejection before mutation");
        }

        private static Stepper.TeamState ZeroTeam()
        {
            return new Stepper.TeamState
            {
                TimeScale = 1f,
                FrameInterpolation = 1f,
            };
        }

        private static Stepper.TeamFrameInput NormalFrame(float deltaTime)
        {
            return new Stepper.TeamFrameInput(true, false, false, false, deltaTime, deltaTime, deltaTime);
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException("Secondary dynamics time-step verification failed: " + message);
        }

        private static void RequireBits(float actual, uint expected, string message)
        {
            uint actualBits = Bits(actual);
            if (actualBits != expected)
                throw new InvalidOperationException(
                    string.Format("Secondary dynamics time-step verification failed: {0}: {1:x8} != {2:x8}",
                        message, actualBits, expected));
        }

        private static uint Bits(float value)
        {
            return BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
        }

        private static void Expect<TException>(Action action) where TException : Exception
        {
            try
            {
                action();
            }
            catch (TException)
            {
                return;
            }

            throw new InvalidOperationException(
                "Secondary dynamics time-step verification failed: expected " + typeof(TException).Name);
        }
    }
}
