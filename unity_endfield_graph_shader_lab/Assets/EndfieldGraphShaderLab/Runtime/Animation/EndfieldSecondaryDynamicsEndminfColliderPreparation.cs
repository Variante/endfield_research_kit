using System;
using System.Runtime.CompilerServices;
using UnityEngine;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Pure managed registration and pre-simulation preparation for Endminf's
    /// ten authored capsule colliders. Transform samples are explicit values;
    /// this helper never reads or writes a Unity Transform and has no runtime hook.
    /// </summary>
    public static class EndfieldSecondaryDynamicsEndminfColliderPreparation
    {
        public const byte Valid = 0x10;
        public const byte Enabled = 0x20;
        public const byte Reset = 0x40;
        public const byte Reverse = 0x80;
        public const int AuthoredColliderCount = 10;

        private static readonly uint[,] AuthoredCenterBits =
        {
            { 0xbd8f5c29U, 0x00000000U, 0xbde147aeU },
            { 0xbe570a3dU, 0x00000000U, 0x00000000U },
            { 0xbca3d70aU, 0x00000000U, 0xbda3d70aU },
            { 0xbdb851ecU, 0x00000000U, 0xbd99999aU },
            { 0x00000000U, 0x00000000U, 0x00000000U },
            { 0xbe570a3dU, 0x00000000U, 0x00000000U },
            { 0xbd8f5c29U, 0x00000000U, 0xbde147aeU },
            { 0xbca3d70aU, 0x00000000U, 0xbda3d70aU },
            { 0x00000000U, 0x00000000U, 0x00000000U },
            { 0xbdb851ecU, 0x00000000U, 0xbd99999aU },
        };

        private static readonly uint[,] AuthoredSizeBits =
        {
            { 0x3ddf3b64U, 0x3deb851fU, 0x3ecc49baU },
            { 0x3d9db22dU, 0x3a83126fU, 0x3efa5e35U },
            { 0x3d5d2f1bU, 0x3d8d4fdfU, 0x3e72b021U },
            { 0x3d916873U, 0x3a83126fU, 0x3ea3d70aU },
            { 0x3dd70a3dU, 0x3dd91687U, 0x3e981062U },
            { 0x3d9db22dU, 0x3a83126fU, 0x3efa5e35U },
            { 0x3de978d5U, 0x3e041893U, 0x3ecc49baU },
            { 0x3d5d2f1bU, 0x3d8d4fdfU, 0x3e72b021U },
            { 0x3dced917U, 0x3dbc6a7fU, 0x3e94fdf4U },
            { 0x3d916873U, 0x3a83126fU, 0x3ea3d70aU },
        };

        public readonly struct TransformSample
        {
            public readonly K.Double3 Position;
            public readonly K.Float4 Rotation;
            public readonly K.Float3 Scale;

            public TransformSample(K.Double3 position, K.Float4 rotation, K.Float3 scale)
            {
                Position = position;
                Rotation = rotation;
                Scale = scale;
            }
        }

        public struct RegisteredCollider
        {
            public int SourceIndex;
            public byte RegistrationFlag;
            public byte Flag;
            public K.Float3 Center;
            public K.Float3 Size;
            public K.Double3 FramePosition;
            public K.Float4 FrameRotation;
            public K.Float3 FrameScale;
            public K.Double3 OldFramePosition;
            public K.Float4 OldFrameRotation;
            public K.ColliderStartState StartState;
        }

        public readonly struct PreparedCollider
        {
            public readonly int SourceIndex;
            public readonly byte RegistrationFlag;
            public readonly byte ColliderStartFlag;
            public readonly K.Float3 Size;
            public readonly K.Double3 FramePosition;
            public readonly K.Float4 FrameRotation;
            public readonly K.Float3 FrameScale;
            public readonly K.Double3 ColliderStartOldFramePosition;
            public readonly K.Float4 ColliderStartOldFrameRotation;
            public readonly K.ColliderStartState State;

            public PreparedCollider(
                int sourceIndex,
                byte registrationFlag,
                byte colliderStartFlag,
                K.Float3 size,
                K.Double3 framePosition,
                K.Float4 frameRotation,
                K.Float3 frameScale,
                K.Double3 colliderStartOldFramePosition,
                K.Float4 colliderStartOldFrameRotation,
                K.ColliderStartState state)
            {
                SourceIndex = sourceIndex;
                RegistrationFlag = registrationFlag;
                ColliderStartFlag = colliderStartFlag;
                Size = size;
                FramePosition = framePosition;
                FrameRotation = frameRotation;
                FrameScale = frameScale;
                ColliderStartOldFramePosition = colliderStartOldFramePosition;
                ColliderStartOldFrameRotation = colliderStartOldFrameRotation;
                State = state;
            }
        }

        public static PreparedCollider[] RegisterAndPrepareAll(
            EndfieldSecondaryDynamicsData.CapsuleCollider[] colliders,
            TransformSample[] previousSamples,
            TransformSample[] currentSamples,
            bool teamReset,
            float frameInterpolation,
            float centerMoveRatio,
            float centerRotationRatio)
        {
            ValidateAuthoredArrays(colliders, previousSamples, currentSamples);
            var output = new PreparedCollider[AuthoredColliderCount];
            for (int index = 0; index < AuthoredColliderCount; index++)
            {
                RegisteredCollider state = Register(index, colliders[index], previousSamples[index]);
                output[index] = PrepareAndStart(
                    ref state, currentSamples[index], teamReset,
                    frameInterpolation, centerMoveRatio, centerRotationRatio);
            }
            return output;
        }

        public static RegisteredCollider Register(
            int sourceIndex,
            EndfieldSecondaryDynamicsData.CapsuleCollider collider,
            TransformSample sample)
        {
            ValidateAuthoredCollider(sourceIndex, collider);
            ValidateSample(sample, nameof(sample));
            int colliderType = GetEndminfColliderType(collider);
            byte registrationFlag = checked((byte)(colliderType | Valid | Enabled | Reset));
            K.Float3 center = ToFloat3(collider.center);
            K.Double3 framePosition = PublishFramePosition(sample, center);
            K.Float3 size = collider.radiusSeparation
                ? ToFloat3(collider.size)
                : new K.Float3(collider.size.x, collider.size.x, collider.size.z);
            K.Float3 position = ToFloat3(framePosition);
            return new RegisteredCollider
            {
                SourceIndex = sourceIndex,
                RegistrationFlag = registrationFlag,
                Flag = registrationFlag,
                Center = center,
                Size = size,
                FramePosition = framePosition,
                FrameRotation = sample.Rotation,
                FrameScale = sample.Scale,
                OldFramePosition = framePosition,
                OldFrameRotation = sample.Rotation,
                StartState = new K.ColliderStartState
                {
                    nowPosition = position,
                    nowRotation = sample.Rotation,
                    oldPosition = position,
                    oldRotation = sample.Rotation,
                },
            };
        }

        public static PreparedCollider PrepareAndStart(
            ref RegisteredCollider collider,
            TransformSample currentSample,
            bool teamReset,
            float frameInterpolation,
            float centerMoveRatio,
            float centerRotationRatio)
        {
            ValidateRegistered(collider);
            ValidateSample(currentSample, nameof(currentSample));
            ValidateUnitInterval(frameInterpolation, nameof(frameInterpolation));
            ValidateUnitInterval(centerMoveRatio, nameof(centerMoveRatio));
            ValidateUnitInterval(centerRotationRatio, nameof(centerRotationRatio));

            K.Double3 currentPosition = PublishFramePosition(currentSample, collider.Center);
            collider.FramePosition = currentPosition;
            collider.FrameRotation = currentSample.Rotation;
            collider.FrameScale = currentSample.Scale;

            if (teamReset || (collider.Flag & Reset) != 0)
            {
                K.Float3 resetPosition = ToFloat3(currentPosition);
                collider.OldFramePosition = currentPosition;
                collider.OldFrameRotation = currentSample.Rotation;
                collider.StartState.nowPosition = resetPosition;
                collider.StartState.nowRotation = currentSample.Rotation;
                collider.StartState.oldPosition = resetPosition;
                collider.StartState.oldRotation = currentSample.Rotation;
            }
            collider.Flag = checked((byte)(collider.Flag & ~Reset));

            K.Double3 startOldFramePosition = collider.OldFramePosition;
            K.Float4 startOldFrameRotation = collider.OldFrameRotation;
            var input = new K.ColliderStartInput
            {
                flag = collider.Flag,
                size = collider.Size,
                framePosition = ToFloat3(currentPosition),
                frameRotation = currentSample.Rotation,
                frameScale = currentSample.Scale,
                oldFramePosition = ToFloat3(startOldFramePosition),
                oldFrameRotation = startOldFrameRotation,
                frameInterpolation = frameInterpolation,
                centerMoveRatio = centerMoveRatio,
                centerRotationRatio = centerRotationRatio,
            };
            if (!K.StartCapsuleCollider(input, ref collider.StartState))
                throw new InvalidOperationException("An authored Endminf collider unexpectedly failed its active gate.");

            PreparedCollider output = new PreparedCollider(
                collider.SourceIndex, collider.RegistrationFlag, collider.Flag,
                collider.Size, currentPosition, currentSample.Rotation, currentSample.Scale,
                startOldFramePosition, startOldFrameRotation, collider.StartState);

            // Exact previous-frame publication for a subsequent explicit sample.
            collider.OldFramePosition = currentPosition;
            collider.OldFrameRotation = currentSample.Rotation;
            return output;
        }

        private static void ValidateAuthoredArrays(
            EndfieldSecondaryDynamicsData.CapsuleCollider[] colliders,
            TransformSample[] previousSamples,
            TransformSample[] currentSamples)
        {
            if (colliders == null || previousSamples == null || currentSamples == null)
                throw new ArgumentNullException("Endminf collider inputs cannot be null.");
            if (colliders.Length != AuthoredColliderCount ||
                previousSamples.Length != AuthoredColliderCount ||
                currentSamples.Length != AuthoredColliderCount)
                throw new ArgumentException("Endminf collider preparation requires exactly ten source-ordered rows and samples.");
            for (int index = 0; index < AuthoredColliderCount; index++)
                ValidateAuthoredCollider(index, colliders[index]);
        }

        private static void ValidateAuthoredCollider(
            int sourceIndex, EndfieldSecondaryDynamicsData.CapsuleCollider collider)
        {
            if (sourceIndex < 0 || sourceIndex >= AuthoredColliderCount)
                throw new ArgumentOutOfRangeException(nameof(sourceIndex));
            GetEndminfColliderType(collider);
            if (collider.reverseDirection)
                throw new NotSupportedException("Endminf's authored capsules are not reverse-direction colliders.");
            RequireBits(collider.center.x, AuthoredCenterBits[sourceIndex, 0], "center.x");
            RequireBits(collider.center.y, AuthoredCenterBits[sourceIndex, 1], "center.y");
            RequireBits(collider.center.z, AuthoredCenterBits[sourceIndex, 2], "center.z");
            RequireBits(collider.size.x, AuthoredSizeBits[sourceIndex, 0], "size.x");
            RequireBits(collider.size.y, AuthoredSizeBits[sourceIndex, 1], "size.y");
            RequireBits(collider.size.z, AuthoredSizeBits[sourceIndex, 2], "size.z");
            bool expectedRadiusSeparation = sourceIndex == 0 || sourceIndex == 2 ||
                sourceIndex == 6 || sourceIndex == 7 || sourceIndex == 8;
            int expectedDirection = sourceIndex == 4 ? 2 : 0;
            if (collider.direction != expectedDirection ||
                collider.radiusSeparation != expectedRadiusSeparation || !collider.alignedOnCenter)
                throw new NotSupportedException("Collider row does not match the pinned Endminf authored topology.");
        }

        private static int GetEndminfColliderType(EndfieldSecondaryDynamicsData.CapsuleCollider collider)
        {
            if (collider.direction == 2 && !collider.alignedOnCenter)
                throw new NotSupportedException("Capsule type 7 is not implemented by the pinned Collider Start core.");
            if (!collider.alignedOnCenter || (collider.direction != 0 && collider.direction != 2))
                throw new NotSupportedException("Only Endminf's authored centered X/Z capsules are supported.");
            return collider.direction == 0 ? 2 : 4;
        }

        private static K.Double3 PublishFramePosition(TransformSample sample, K.Float3 center)
        {
            K.Float3 scaled = new K.Float3(
                Mul(center.x, sample.Scale.x),
                Mul(center.y, sample.Scale.y),
                Mul(center.z, sample.Scale.z));
            K.Float3 offset = Rotate(sample.Rotation, scaled);
            return new K.Double3(
                sample.Position.x + (double)offset.x,
                sample.Position.y + (double)offset.y,
                sample.Position.z + (double)offset.z);
        }

        // Unity.Mathematics quaternion-vector rotation: v + q.w*t + cross(q.xyz,t),
        // where t = 2*cross(q.xyz,v), with explicit binary32 intermediates.
        private static K.Float3 Rotate(K.Float4 q, K.Float3 value)
        {
            float tx = Mul(2f, Sub(Mul(q.y, value.z), Mul(q.z, value.y)));
            float ty = Mul(2f, Sub(Mul(q.z, value.x), Mul(q.x, value.z)));
            float tz = Mul(2f, Sub(Mul(q.x, value.y), Mul(q.y, value.x)));
            float cx = Sub(Mul(q.y, tz), Mul(q.z, ty));
            float cy = Sub(Mul(q.z, tx), Mul(q.x, tz));
            float cz = Sub(Mul(q.x, ty), Mul(q.y, tx));
            return new K.Float3(
                Add(Add(value.x, Mul(q.w, tx)), cx),
                Add(Add(value.y, Mul(q.w, ty)), cy),
                Add(Add(value.z, Mul(q.w, tz)), cz));
        }

        private static void ValidateRegistered(RegisteredCollider collider)
        {
            int type = collider.Flag & 0x0f;
            if (type != 2 && type != 4)
                throw new NotSupportedException("Registered collider is outside Endminf's type-2/type-4 target.");
            if ((collider.Flag & (Valid | Enabled)) != (Valid | Enabled) ||
                (collider.Flag & Reverse) != 0)
                throw new NotSupportedException("Registered collider flags are outside Endminf's active non-reversed target.");
        }

        private static void ValidateSample(TransformSample sample, string parameter)
        {
            if (!Finite(sample.Position.x) || !Finite(sample.Position.y) || !Finite(sample.Position.z) ||
                !Finite(sample.Rotation.x) || !Finite(sample.Rotation.y) ||
                !Finite(sample.Rotation.z) || !Finite(sample.Rotation.w) ||
                !Finite(sample.Scale.x) || !Finite(sample.Scale.y) || !Finite(sample.Scale.z))
                throw new ArgumentOutOfRangeException(parameter, "Transform samples must be finite.");
        }

        private static void ValidateUnitInterval(float value, string parameter)
        {
            if (!Finite(value) || value < 0f || value > 1f)
                throw new ArgumentOutOfRangeException(parameter);
        }

        private static void RequireBits(float value, uint expected, string field)
        {
            if (Bits(value) != expected)
                throw new NotSupportedException("Collider row " + field + " differs from the pinned Endminf source value.");
        }

        private static K.Float3 ToFloat3(Vector3 value) => new K.Float3(value.x, value.y, value.z);
        private static K.Float3 ToFloat3(K.Double3 value) =>
            new K.Float3((float)value.x, (float)value.y, (float)value.z);
        private static bool Finite(float value) => !float.IsNaN(value) && !float.IsInfinity(value);
        private static bool Finite(double value) => !double.IsNaN(value) && !double.IsInfinity(value);
        private static uint Bits(float value) => BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);

        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Mul(float left, float right) => left * right;
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Add(float left, float right) => left + right;
        [MethodImpl(MethodImplOptions.NoInlining)]
        private static float Sub(float left, float right) => left - right;
    }
}
