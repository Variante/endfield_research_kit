using System;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Pure managed translation of the closed transform-publication contract.
    /// It computes publication records only; it never reads or writes a Transform.
    /// Duplicate transform bindings deliberately remain separate, source-ordered records.
    /// </summary>
    public static class EndfieldSecondaryDynamicsTransformPublication
    {
        [Flags]
        public enum TransformFlags : byte
        {
            Read = 0x01,
            World = 0x02,
            Local = 0x04,
            Restore = 0x08,
            Enable = 0x10,
        }

        public enum PublicationBranch : byte
        {
            None,
            World,
            Local,
        }

        [Serializable]
        public struct Double3
        {
            public double x;
            public double y;
            public double z;

            public Double3(double x, double y, double z)
            {
                this.x = x;
                this.y = y;
                this.z = z;
            }

            public static Double3 operator -(Double3 left, Double3 right)
            {
                return new Double3(left.x - right.x, left.y - right.y, left.z - right.z);
            }
        }

        [Serializable]
        public struct Chunk
        {
            public int start;

            public Chunk(int start)
            {
                this.start = start;
            }
        }

        [Serializable]
        public struct TeamPublicationData
        {
            public Chunk proxyCommonChunk;
            public Chunk proxyBoneChunk;
            public Chunk proxyTransformChunk;
            public Quaternion negativeScaleQuaternionValue;
            public float clothSimulateWeight;
            public float clothLodFadeWeight;
        }

        public readonly struct WorldSource
        {
            public readonly int vertexIndex;
            public readonly short teamId;
            public readonly TeamPublicationData team;
            public readonly Double3 positionPostSolver;
            public readonly Quaternion rotationPostSolver;
            public readonly Quaternion vertexToTransformRotation;

            public WorldSource(
                int vertexIndex,
                short teamId,
                TeamPublicationData team,
                Double3 positionPostSolver,
                Quaternion rotationPostSolver,
                Quaternion vertexToTransformRotation)
            {
                this.vertexIndex = vertexIndex;
                this.teamId = teamId;
                this.team = team;
                this.positionPostSolver = positionPostSolver;
                this.rotationPostSolver = rotationPostSolver;
                this.vertexToTransformRotation = vertexToTransformRotation;
            }
        }

        public readonly struct WorldValue
        {
            public readonly bool publish;
            public readonly int destinationIndex;
            public readonly Double3 position;
            public readonly Quaternion rotation;

            public WorldValue(bool publish, int destinationIndex, Double3 position, Quaternion rotation)
            {
                this.publish = publish;
                this.destinationIndex = destinationIndex;
                this.position = position;
                this.rotation = rotation;
            }
        }

        public readonly struct LocalSource
        {
            public readonly int vertexIndex;
            public readonly short teamId;
            public readonly byte attributes;
            public readonly int parentIndex;
            public readonly TeamPublicationData team;

            public LocalSource(
                int vertexIndex,
                short teamId,
                byte attributes,
                int parentIndex,
                TeamPublicationData team)
            {
                this.vertexIndex = vertexIndex;
                this.teamId = teamId;
                this.attributes = attributes;
                this.parentIndex = parentIndex;
                this.team = team;
            }
        }

        public readonly struct LocalValue
        {
            public readonly bool publish;
            public readonly int childIndex;
            public readonly int parentIndex;
            public readonly Vector3 position;
            public readonly Quaternion rotation;

            public LocalValue(
                bool publish,
                int childIndex,
                int parentIndex,
                Vector3 position,
                Quaternion rotation)
            {
                this.publish = publish;
                this.childIndex = childIndex;
                this.parentIndex = parentIndex;
                this.position = position;
                this.rotation = rotation;
            }
        }

        public readonly struct FinalInput
        {
            public readonly int sourceIndex;
            public readonly int transformId;
            public readonly TransformFlags flags;
            public readonly bool cullingVisible;
            public readonly bool nativeValid;
            public readonly bool spring;
            public readonly float clothSimulateWeight;
            public readonly float clothLodFadeWeight;
            public readonly Vector3 currentWorldPosition;
            public readonly Quaternion currentWorldRotation;
            public readonly Vector3 currentLocalPosition;
            public readonly Quaternion currentLocalRotation;
            public readonly Vector3 targetWorldPosition;
            public readonly Quaternion targetWorldRotation;
            public readonly Vector3 targetLocalPosition;
            public readonly Quaternion targetLocalRotation;

            public FinalInput(
                int sourceIndex,
                int transformId,
                TransformFlags flags,
                bool cullingVisible,
                bool nativeValid,
                bool spring,
                float clothSimulateWeight,
                float clothLodFadeWeight,
                Vector3 currentWorldPosition,
                Quaternion currentWorldRotation,
                Vector3 currentLocalPosition,
                Quaternion currentLocalRotation,
                Vector3 targetWorldPosition,
                Quaternion targetWorldRotation,
                Vector3 targetLocalPosition,
                Quaternion targetLocalRotation)
            {
                this.sourceIndex = sourceIndex;
                this.transformId = transformId;
                this.flags = flags;
                this.cullingVisible = cullingVisible;
                this.nativeValid = nativeValid;
                this.spring = spring;
                this.clothSimulateWeight = clothSimulateWeight;
                this.clothLodFadeWeight = clothLodFadeWeight;
                this.currentWorldPosition = currentWorldPosition;
                this.currentWorldRotation = currentWorldRotation;
                this.currentLocalPosition = currentLocalPosition;
                this.currentLocalRotation = currentLocalRotation;
                this.targetWorldPosition = targetWorldPosition;
                this.targetWorldRotation = targetWorldRotation;
                this.targetLocalPosition = targetLocalPosition;
                this.targetLocalRotation = targetLocalRotation;
            }
        }

        public readonly struct FinalValue
        {
            public readonly int sourceIndex;
            public readonly int transformId;
            public readonly bool publish;
            public readonly PublicationBranch branch;
            public readonly float weight;
            public readonly bool writePosition;
            public readonly bool writeRotation;
            public readonly Vector3 position;
            public readonly Quaternion rotation;

            public FinalValue(
                int sourceIndex,
                int transformId,
                bool publish,
                PublicationBranch branch,
                float weight,
                bool writePosition,
                bool writeRotation,
                Vector3 position,
                Quaternion rotation)
            {
                this.sourceIndex = sourceIndex;
                this.transformId = transformId;
                this.publish = publish;
                this.branch = branch;
                this.weight = weight;
                this.writePosition = writePosition;
                this.writeRotation = writeRotation;
                this.position = position;
                this.rotation = rotation;
            }
        }

        public static WorldValue CalculateWorld(WorldSource source)
        {
            if (source.teamId == 0)
                return default;

            int local = source.vertexIndex - source.team.proxyCommonChunk.start;
            int bone = source.team.proxyBoneChunk.start + local;
            int destination = source.team.proxyTransformChunk.start + local;
            _ = bone; // The caller supplies vertexToTransformRotation at this exact bone index.

            Quaternion correction = ComponentwiseF32(
                source.team.negativeScaleQuaternionValue,
                source.vertexToTransformRotation);
            Quaternion rotation = HamiltonF32(source.rotationPostSolver, correction);
            return new WorldValue(true, destination, source.positionPostSolver, rotation);
        }

        public static LocalValue CalculateLocal(
            LocalSource source,
            IReadOnlyList<Double3> worldPositions,
            IReadOnlyList<Quaternion> worldRotations,
            IReadOnlyList<Vector3> scales)
        {
            if (source.teamId == 0 || source.parentIndex < 0 || (source.attributes & 0x02) == 0)
                return default;

            int local = source.vertexIndex - source.team.proxyCommonChunk.start;
            int child = source.team.proxyTransformChunk.start + local;
            int parent = source.team.proxyTransformChunk.start + source.parentIndex;

            Double3 deltaWorld = worldPositions[child] - worldPositions[parent];
            Quaternion parentInverse = InverseWithoutZeroGuard(worldRotations[parent]);
            Double3 localDouble = RotateDouble(parentInverse, deltaWorld);
            Vector3 parentScale = scales[parent];
            Vector3 localPosition = new Vector3(
                (float)(localDouble.x / (double)parentScale.x),
                (float)(localDouble.y / (double)parentScale.y),
                (float)(localDouble.z / (double)parentScale.z));
            Quaternion relative = HamiltonF32(parentInverse, worldRotations[child]);
            Quaternion negativeScale = source.team.negativeScaleQuaternionValue;
            Quaternion localRotation = new Quaternion(
                relative.x * negativeScale.x,
                relative.y * negativeScale.y,
                relative.z * negativeScale.z,
                relative.w * negativeScale.w);
            return new LocalValue(true, child, parent, localPosition, localRotation);
        }

        /// <summary>
        /// Resolves the final WriteTransformJob branch without touching a Transform.
        /// World targets must already include any enabled relative-transform adjustment;
        /// that adjustment's equation is not closed by the source contract.
        /// </summary>
        public static FinalValue CalculateFinal(FinalInput input)
        {
            float weight = input.clothSimulateWeight * input.clothLodFadeWeight;
            bool enabled = (input.flags & TransformFlags.Enable) != 0;
            if (!enabled || !input.cullingVisible || !input.nativeValid)
                return new FinalValue(input.sourceIndex, input.transformId, false, PublicationBranch.None,
                    weight, false, false, default, default);

            if ((input.flags & TransformFlags.World) != 0)
            {
                Quaternion rotation = Quaternion.Slerp(
                    input.currentWorldRotation,
                    input.targetWorldRotation,
                    weight);
                bool writePosition = input.spring;
                Vector3 position = input.currentWorldPosition;
                if (writePosition)
                {
                    position = weight < 1.0f
                        ? Vector3.Lerp(input.currentWorldPosition, input.targetWorldPosition, weight)
                        : input.targetWorldPosition;
                }

                return new FinalValue(input.sourceIndex, input.transformId, true, PublicationBranch.World,
                    weight, writePosition, true, position, rotation);
            }

            if ((input.flags & TransformFlags.Local) != 0)
            {
                Vector3 position;
                Quaternion rotation;
                if (weight < 1.0f)
                {
                    position = Vector3.Lerp(input.currentLocalPosition, input.targetLocalPosition, weight);
                    rotation = Quaternion.Slerp(input.currentLocalRotation, input.targetLocalRotation, weight);
                }
                else
                {
                    position = input.targetLocalPosition;
                    rotation = input.targetLocalRotation;
                }

                return new FinalValue(input.sourceIndex, input.transformId, true, PublicationBranch.Local,
                    weight, true, true, position, rotation);
            }

            return new FinalValue(input.sourceIndex, input.transformId, false, PublicationBranch.None,
                weight, false, false, default, default);
        }

        public static FinalValue[] CalculateFinalSourceOrdered(IReadOnlyList<FinalInput> inputs)
        {
            if (inputs == null)
                throw new ArgumentNullException(nameof(inputs));

            var values = new FinalValue[inputs.Count];
            for (int i = 0; i < inputs.Count; i++)
                values[i] = CalculateFinal(inputs[i]);
            return values;
        }

        private static Quaternion HamiltonF32(Quaternion left, Quaternion right)
        {
            return new Quaternion(
                ((left.w * right.x + left.x * right.w) + left.y * right.z) - left.z * right.y,
                ((left.w * right.y - left.x * right.z) + left.y * right.w) + left.z * right.x,
                ((left.w * right.z + left.x * right.y) - left.y * right.x) + left.z * right.w,
                ((left.w * right.w - left.x * right.x) - left.y * right.y) - left.z * right.z);
        }

        private static Quaternion ComponentwiseF32(Quaternion left, Quaternion right)
        {
            return new Quaternion(
                left.x * right.x,
                left.y * right.y,
                left.z * right.z,
                left.w * right.w);
        }

        private static Quaternion InverseWithoutZeroGuard(Quaternion value)
        {
            float dot = ((value.x * value.x + value.y * value.y) + value.z * value.z) + value.w * value.w;
            return new Quaternion(-value.x / dot, -value.y / dot, -value.z / dot, value.w / dot);
        }

        private static Double3 RotateDouble(Quaternion rotation, Double3 value)
        {
            // q * (v, 0) * conjugate(q), evaluated in float64 after q widened to double.
            double qx = rotation.x;
            double qy = rotation.y;
            double qz = rotation.z;
            double qw = rotation.w;
            double tx = 2.0 * (qy * value.z - qz * value.y);
            double ty = 2.0 * (qz * value.x - qx * value.z);
            double tz = 2.0 * (qx * value.y - qy * value.x);
            return new Double3(
                value.x + qw * tx + (qy * tz - qz * ty),
                value.y + qw * ty + (qz * tx - qx * tz),
                value.z + qw * tz + (qx * ty - qy * tx));
        }
    }
}
