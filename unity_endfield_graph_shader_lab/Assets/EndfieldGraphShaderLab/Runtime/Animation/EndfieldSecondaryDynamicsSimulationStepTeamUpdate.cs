using System;
using System.Runtime.CompilerServices;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Pure managed transcription of the target-active, unpatched Endminf
    /// SimulationStepTeamUpdate center-feed kernel. It owns no Unity objects and
    /// deliberately rejects routes outside the stationary-root, positive-scale,
    /// zero-wind, retail-90-Hz evidence boundary.
    /// </summary>
    public static class EndfieldSecondaryDynamicsSimulationStepTeamUpdate
    {
        public enum ExecutionRoute
        {
            Unpatched,
            IFixPatched,
        }

        public struct Parameters
        {
            public float LocalInertia;
            public float LocalMovementSpeedLimit;
            public float LocalRotationSpeedLimit;
        }

        public struct FrameInput
        {
            public float Time;
            public float FrameOldTime;
            public K.Double3 OldFrameWorldPosition;
            public K.Double3 FrameWorldPosition;
            public K.Float4 OldFrameWorldRotation;
            public K.Float4 FrameWorldRotation;
            public K.Float3 FrameScale;
            public int WindZoneCount;
            public bool NegativeScale;
            public bool StationaryActorRoot;
        }

        public struct CenterState
        {
            public float NowUpdateTime;
            public float FrameInterpolation;
            public K.Double3 NowWorldPosition;
            public K.Float4 NowWorldRotation;
            public K.Double3 OldWorldPosition;
            public K.Float4 OldWorldRotation;

            public float StepMoveInertiaRatio;
            public float StepRotationInertiaRatio;
            public K.Float3 StepVector;
            public K.Float4 StepRotation;
            public K.Float3 InertiaVector;
            public K.Float4 InertiaRotation;
            public float AngularVelocity;
            public K.Float3 RotationAxis;

            // These fields are adjacent in CenterData but are not written by
            // SimulationStepTeamUpdate. Keeping them here makes preservation
            // explicit and testable.
            public float StepMovingSpeed;
            public K.Float3 StepMovingDirection;
            public K.Float3 InitLocalGravityDirection;
        }

        public static void Execute(
            ref CenterState state,
            FrameInput frame,
            Parameters parameters,
            float simulationDeltaTime,
            ExecutionRoute route = ExecutionRoute.Unpatched)
        {
            Validate(state, frame, parameters, simulationDeltaTime, route);

            // Work on a copy so every rejected or non-finite branch is
            // fail-closed before the caller-visible state changes.
            CenterState next = state;
            next.NowUpdateTime = Add(state.NowUpdateTime, simulationDeltaTime);
            float denominator = Sub(frame.Time, frame.FrameOldTime);
            next.FrameInterpolation = denominator > 0f
                ? Clamp01(Divide(Sub(next.NowUpdateTime, frame.FrameOldTime), denominator))
                : 1f;

            K.Double3 nowPosition = Lerp(frame.OldFrameWorldPosition, frame.FrameWorldPosition,
                next.FrameInterpolation);
            K.Float4 nowRotation = next.FrameInterpolation >= 1f
                ? frame.FrameWorldRotation
                : Slerp(frame.OldFrameWorldRotation, frame.FrameWorldRotation, next.FrameInterpolation);

            K.Double3 priorNowPosition = state.NowWorldPosition;
            K.Float4 priorNowRotation = state.NowWorldRotation;
            K.Float3 stepVector = new K.Float3(
                (float)(nowPosition.x - priorNowPosition.x),
                (float)(nowPosition.y - priorNowPosition.y),
                (float)(nowPosition.z - priorNowPosition.z));
            K.Float4 stepRotation = ShortestRelativeRotation(priorNowRotation, nowRotation);

            float stepAngle = Mul(2f, Acos(Clamp(Math.Abs(stepRotation.w), 0f, 1f)));
            float angularVelocity = Divide(stepAngle, simulationDeltaTime);
            K.Float3 rotationAxis = stepAngle > 1.0e-8f
                ? RotationAxis(stepRotation, stepAngle)
                : new K.Float3(0f, 0f, 0f);

            float moveRatio = Sub(1f, parameters.LocalInertia);
            float stepLength = Sqrt(Add(Add(Mul(stepVector.x, stepVector.x), Mul(stepVector.y, stepVector.y)),
                Mul(stepVector.z, stepVector.z)));
            float movementSpeed = Divide(stepLength, simulationDeltaTime);
            if (parameters.LocalMovementSpeedLimit >= 0f && movementSpeed > parameters.LocalMovementSpeedLimit)
            {
                float t = Divide(parameters.LocalMovementSpeedLimit, movementSpeed);
                moveRatio = Lerp(1f, moveRatio, t);
            }

            float rotationSpeedDegrees = Mul(angularVelocity, 57.295780181884766f);
            float rotationRatio = Sub(1f, parameters.LocalInertia);
            float weightedRotationSpeedDegrees = Mul(parameters.LocalInertia, rotationSpeedDegrees);
            if (parameters.LocalRotationSpeedLimit >= 0f &&
                weightedRotationSpeedDegrees > parameters.LocalRotationSpeedLimit)
            {
                float t = Divide(parameters.LocalRotationSpeedLimit, weightedRotationSpeedDegrees);
                rotationRatio = Lerp(1f, rotationRatio, t);
            }

            next.StepMoveInertiaRatio = moveRatio;
            next.StepRotationInertiaRatio = rotationRatio;
            next.StepVector = stepVector;
            next.StepRotation = stepRotation;
            next.InertiaVector = moveRatio == 0f
                ? new K.Float3(0f, 0f, 0f)
                : new K.Float3(
                    Mul(stepVector.x, moveRatio),
                    Mul(stepVector.y, moveRatio),
                    Mul(stepVector.z, moveRatio));
            next.InertiaRotation = Slerp(new K.Float4(0f, 0f, 0f, 1f), stepRotation, rotationRatio);
            next.AngularVelocity = angularVelocity;
            next.RotationAxis = rotationAxis;

            next.OldWorldPosition = priorNowPosition;
            next.OldWorldRotation = priorNowRotation;
            next.NowWorldPosition = nowPosition;
            next.NowWorldRotation = nowRotation;
            ValidateFinite(next);
            state = next;
        }

        private static K.Double3 Lerp(K.Double3 a, K.Double3 b, float t)
        {
            return new K.Double3(
                a.x + (b.x - a.x) * t,
                a.y + (b.y - a.y) * t,
                a.z + (b.z - a.z) * t);
        }

        private static K.Float4 ShortestRelativeRotation(K.Float4 oldRotation, K.Float4 nowRotation)
        {
            K.Float4 inverse = Inverse(oldRotation);
            K.Float4 result = Multiply(inverse, nowRotation);
            if (result.w < 0f)
                result = new K.Float4(-result.x, -result.y, -result.z, -result.w);
            return result;
        }

        private static K.Float4 Inverse(K.Float4 value)
        {
            float lengthSquared = Dot(value, value);
            float reciprocal = Divide(1f, lengthSquared);
            return new K.Float4(
                Mul(-value.x, reciprocal), Mul(-value.y, reciprocal),
                Mul(-value.z, reciprocal), Mul(value.w, reciprocal));
        }

        private static K.Float4 Multiply(K.Float4 a, K.Float4 b)
        {
            return new K.Float4(
                Add(Add(Mul(a.w, b.x), Mul(a.x, b.w)), Sub(Mul(a.y, b.z), Mul(a.z, b.y))),
                Add(Add(Mul(a.w, b.y), Mul(a.y, b.w)), Sub(Mul(a.z, b.x), Mul(a.x, b.z))),
                Add(Add(Mul(a.w, b.z), Mul(a.z, b.w)), Sub(Mul(a.x, b.y), Mul(a.y, b.x))),
                Sub(Sub(Sub(Mul(a.w, b.w), Mul(a.x, b.x)), Mul(a.y, b.y)), Mul(a.z, b.z)));
        }

        private static K.Float3 RotationAxis(K.Float4 rotation, float angle)
        {
            float denominator = Sin(Mul(angle, 0.5f));
            if (!(denominator > 0f)) return new K.Float3(0f, 0f, 0f);
            float reciprocal = Divide(1f, denominator);
            return new K.Float3(
                Mul(rotation.x, reciprocal), Mul(rotation.y, reciprocal), Mul(rotation.z, reciprocal));
        }

        private static K.Float4 Slerp(K.Float4 a, K.Float4 b, float t)
        {
            float dot = Dot(a, b);
            if (dot < 0f)
            {
                b = new K.Float4(-b.x, -b.y, -b.z, -b.w);
                dot = -dot;
            }
            if (dot >= 0.9995f)
            {
                return Normalize(new K.Float4(
                    Add(a.x, Mul(t, Sub(b.x, a.x))),
                    Add(a.y, Mul(t, Sub(b.y, a.y))),
                    Add(a.z, Mul(t, Sub(b.z, a.z))),
                    Add(a.w, Mul(t, Sub(b.w, a.w)))));
            }

            float theta = Acos(dot);
            float inverseSin = Divide(1f, Sqrt(Sub(1f, Mul(dot, dot))));
            float weightA = Mul(inverseSin, Sin(Mul(Sub(1f, t), theta)));
            float weightB = Mul(inverseSin, Sin(Mul(t, theta)));
            return new K.Float4(
                Add(Mul(a.x, weightA), Mul(b.x, weightB)),
                Add(Mul(a.y, weightA), Mul(b.y, weightB)),
                Add(Mul(a.z, weightA), Mul(b.z, weightB)),
                Add(Mul(a.w, weightA), Mul(b.w, weightB)));
        }

        private static K.Float4 Normalize(K.Float4 value)
        {
            float inverse = Divide(1f, Sqrt(Dot(value, value)));
            return new K.Float4(
                Mul(value.x, inverse), Mul(value.y, inverse),
                Mul(value.z, inverse), Mul(value.w, inverse));
        }

        private static float Sin(float value)
        {
            if (!Finite(value) || Math.Abs(value) >= 125f)
                throw new ArgumentOutOfRangeException(nameof(value));
            float quotient = Mul(value, 0.31830987334251404f);
            int rounded = (int)Add(quotient, quotient < 0f ? -0.5f : 0.5f);
            float reduced = Add(value, Mul(rounded, -3.1414794921875f));
            reduced = Add(reduced, Mul(rounded, -0.0001131594181060791f));
            reduced = Add(reduced, Mul(rounded, -1.984187258941006e-09f));
            float signed = (rounded & 1) != 0 ? -reduced : reduced;
            float square = Mul(reduced, reduced);
            float polynomial = Add(Mul(square, 2.6083159809786594e-06f), -0.00019810690719168633f);
            polynomial = Add(Mul(square, polynomial), 0.00833307858556509f);
            polynomial = Add(Mul(square, polynomial), -0.16666659712791443f);
            return Add(signed, Mul(square, Mul(signed, polynomial)));
        }

        private static float Acos(float value)
        {
            float absolute = Math.Abs(value);
            float polynomialInput;
            float root;
            if (absolute < 0.5f)
            {
                polynomialInput = Mul(value, value);
                root = absolute;
            }
            else
            {
                polynomialInput = Mul(0.5f, Sub(1f, absolute));
                root = absolute == 1f ? 0f : Sqrt(polynomialInput);
            }
            float polynomial = Add(Mul(polynomialInput, 0.04197454825043678f), 0.024240460246801376f);
            polynomial = Add(Mul(polynomialInput, polynomial), 0.04547423869371414f);
            polynomial = Add(Mul(polynomialInput, polynomial), 0.07495029270648956f);
            polynomial = Add(Mul(polynomialInput, polynomial), 0.16666772961616516f);
            float signedRoot = value < 0f ? -root : root;
            float asin = Add(signedRoot, Mul(polynomialInput, Mul(signedRoot, polynomial)));
            if (absolute < 0.5f) return Sub(1.5707963705062866f, asin);
            float doubled = Add(root, Mul(polynomialInput, Mul(root, polynomial)));
            doubled = Add(doubled, doubled);
            return value < 0f ? Sub(3.1415927410125732f, doubled) : doubled;
        }

        private static float Dot(K.Float4 a, K.Float4 b) =>
            Add(Add(Mul(a.x, b.x), Mul(a.y, b.y)), Add(Mul(a.z, b.z), Mul(a.w, b.w)));

        private static void Validate(CenterState state, FrameInput frame, Parameters parameters,
            float simulationDeltaTime, ExecutionRoute route)
        {
            if (route != ExecutionRoute.Unpatched)
                throw new NotSupportedException("IFix/patched SimulationStepTeamUpdate is not recovered.");
            if (Bits(simulationDeltaTime) != 0x3c360b61U)
                throw new NotSupportedException("Only the pinned retail 90 Hz timestep is supported.");
            if (!frame.StationaryActorRoot)
                throw new NotSupportedException("Only the stationary Endminf overview root is supported.");
            if (frame.WindZoneCount != 0)
                throw new NotSupportedException("General wind is not recovered.");
            if (frame.NegativeScale || !(frame.FrameScale.x > 0f) || !(frame.FrameScale.y > 0f) ||
                !(frame.FrameScale.z > 0f))
                throw new NotSupportedException("Negative or zero scale is not recovered.");
            if (!Finite(parameters.LocalInertia) || parameters.LocalInertia < 0f || parameters.LocalInertia > 1f ||
                !Finite(parameters.LocalMovementSpeedLimit) || !Finite(parameters.LocalRotationSpeedLimit))
                throw new ArgumentOutOfRangeException(nameof(parameters));
            ValidateFinite(state);
            ValidateFinite(frame);
        }

        private static void ValidateFinite(CenterState value)
        {
            if (!Finite(value.NowUpdateTime) || !Finite(value.FrameInterpolation) ||
                !Finite(value.StepMoveInertiaRatio) || !Finite(value.StepRotationInertiaRatio) ||
                !Finite(value.AngularVelocity) || !Finite(value.StepMovingSpeed))
                throw new ArgumentOutOfRangeException(nameof(value));
            Validate(value.NowWorldPosition); Validate(value.OldWorldPosition);
            ValidateQuaternion(value.NowWorldRotation); ValidateQuaternion(value.OldWorldRotation);
            Validate(value.StepVector); ValidateQuaternion(value.StepRotation);
            Validate(value.InertiaVector); ValidateQuaternion(value.InertiaRotation);
            Validate(value.RotationAxis); Validate(value.StepMovingDirection);
            Validate(value.InitLocalGravityDirection);
        }

        private static void ValidateFinite(FrameInput value)
        {
            if (!Finite(value.Time) || !Finite(value.FrameOldTime))
                throw new ArgumentOutOfRangeException(nameof(value));
            Validate(value.OldFrameWorldPosition); Validate(value.FrameWorldPosition);
            ValidateQuaternion(value.OldFrameWorldRotation); ValidateQuaternion(value.FrameWorldRotation);
            Validate(value.FrameScale);
        }

        private static void Validate(K.Float3 value)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z))
                throw new ArgumentOutOfRangeException(nameof(value));
        }

        private static void Validate(K.Double3 value)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z))
                throw new ArgumentOutOfRangeException(nameof(value));
        }

        private static void ValidateQuaternion(K.Float4 value)
        {
            if (!Finite(value.x) || !Finite(value.y) || !Finite(value.z) || !Finite(value.w) ||
                !(Dot(value, value) > 0f))
                throw new ArgumentOutOfRangeException(nameof(value));
        }

        private static float Clamp01(float value) => Clamp(value, 0f, 1f);
        private static float Clamp(float value, float minimum, float maximum) =>
            value < minimum ? minimum : value > maximum ? maximum : value;
        private static float Lerp(float a, float b, float t) => Add(a, Mul(t, Sub(b, a)));
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);

        [MethodImpl(MethodImplOptions.NoInlining)] private static float Add(float a, float b) => a + b;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Sub(float a, float b) => a - b;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Mul(float a, float b) => a * b;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Divide(float a, float b) => a / b;
        [MethodImpl(MethodImplOptions.NoInlining)] private static float Sqrt(float value) => (float)Math.Sqrt(value);
    }
}
