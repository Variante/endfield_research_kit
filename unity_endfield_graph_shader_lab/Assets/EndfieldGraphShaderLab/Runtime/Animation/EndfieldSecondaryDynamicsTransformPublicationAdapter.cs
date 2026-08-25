using System;
using UnityEngine;
using F = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsFrameCoordinator;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using T = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsTransformPublication;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Certified TransformAccess publication boundary for Endminf. It preserves
    /// all 126 source lanes, including duplicates, and applies them in source order.
    /// </summary>
    public sealed class EndfieldSecondaryDynamicsTransformPublicationAdapter
    {
        private readonly EndfieldSecondaryDynamicsData _data;
        private readonly Transform[][] _transforms;
        private readonly Vector3[][] _initialLocalPositions;
        private readonly Quaternion[][] _initialLocalRotations;

        public EndfieldSecondaryDynamicsTransformPublicationAdapter(
            Transform actorRoot,
            EndfieldSecondaryDynamicsData data)
        {
            if (actorRoot == null) throw new ArgumentNullException(nameof(actorRoot));
            if (data == null || data.owners == null || data.owners.Length != F.OwnerCount)
                throw new ArgumentException("Exactly four Endminf owners are required.", nameof(data));
            _data = data;
            _transforms = new Transform[F.OwnerCount][];
            _initialLocalPositions = new Vector3[F.OwnerCount][];
            _initialLocalRotations = new Quaternion[F.OwnerCount][];
            for (int owner = 0; owner < F.OwnerCount; owner++)
            {
                EndfieldSecondaryDynamicsData.Owner source = data.owners[owner];
                if (source.proxyTransformPaths == null ||
                    source.proxyTransformPaths.Length != source.proxyVertexCount)
                    throw new ArgumentException("Owner publication topology differs at " + owner + ".");
                _transforms[owner] = new Transform[source.proxyVertexCount];
                _initialLocalPositions[owner] = new Vector3[source.proxyVertexCount];
                _initialLocalRotations[owner] = new Quaternion[source.proxyVertexCount];
                for (int vertex = 0; vertex < source.proxyVertexCount; vertex++)
                {
                    Transform target = actorRoot.Find(source.proxyTransformPaths[vertex]);
                    if (target == null)
                        throw new ArgumentException("Publication transform does not resolve: " +
                            source.proxyTransformPaths[vertex]);
                    _transforms[owner][vertex] = target;
                    _initialLocalPositions[owner][vertex] = target.localPosition;
                    _initialLocalRotations[owner][vertex] = target.localRotation;
                }
            }
        }

        public void RestoreInitialLocals()
        {
            for (int owner = 0; owner < F.OwnerCount; owner++)
            {
                EndfieldSecondaryDynamicsData.Owner source = _data.owners[owner];
                for (int vertex = 0; vertex < source.proxyVertexCount; vertex++)
                {
                    if ((Flags(source.attributes[vertex]) & T.TransformFlags.Restore) == 0)
                        continue;
                    Transform target = _transforms[owner][vertex];
                    target.localPosition = _initialLocalPositions[owner][vertex];
                    target.localRotation = _initialLocalRotations[owner][vertex];
                }
            }
        }

        public T.FinalValue[] Publish(
            K.Double3[][] positions,
            K.Float4[][] rotations,
            float clothSimulateWeight,
            bool applyWrites)
        {
            ValidatePublication(positions, rotations);
            int total = 0;
            for (int owner = 0; owner < F.OwnerCount; owner++)
                total += _data.owners[owner].proxyVertexCount;
            var values = new T.FinalValue[total];
            int sourceIndex = 0;

            for (int owner = 0; owner < F.OwnerCount; owner++)
            {
                EndfieldSecondaryDynamicsData.Owner source = _data.owners[owner];
                Transform[] bindings = _transforms[owner];
                int count = source.proxyVertexCount;
                var worldPositions = new T.Double3[count];
                var worldRotations = new Quaternion[count];
                var scales = new Vector3[count];
                var team = new T.TeamPublicationData
                {
                    proxyCommonChunk = new T.Chunk(0),
                    proxyBoneChunk = new T.Chunk(0),
                    proxyTransformChunk = new T.Chunk(0),
                    negativeScaleQuaternionValue = Quaternion.identity,
                    clothSimulateWeight = clothSimulateWeight,
                    clothLodFadeWeight = 1f,
                };

                for (int vertex = 0; vertex < count; vertex++)
                {
                    K.Double3 p = positions[owner][vertex];
                    K.Float4 r = rotations[owner][vertex];
                    T.WorldValue world = T.CalculateWorld(new T.WorldSource(
                        vertex, 1, team, new T.Double3(p.x, p.y, p.z),
                        new Quaternion(r.x, r.y, r.z, r.w),
                        source.vertexToTransformRotations[vertex]));
                    if (!world.publish || world.destinationIndex != vertex)
                        throw new InvalidOperationException("Endminf world publication index differs.");
                    worldPositions[vertex] = world.position;
                    worldRotations[vertex] = world.rotation;
                    scales[vertex] = bindings[vertex].lossyScale;
                }

                for (int vertex = 0; vertex < count; vertex++, sourceIndex++)
                {
                    Transform target = bindings[vertex];
                    T.LocalValue local = T.CalculateLocal(new T.LocalSource(
                        vertex, 1, source.attributes[vertex],
                        source.vertexParentIndices[vertex], team),
                        worldPositions, worldRotations, scales);
                    T.TransformFlags flags = Flags(source.attributes[vertex]);
                    T.FinalValue value = T.CalculateFinal(new T.FinalInput(
                        sourceIndex,
                        target.GetInstanceID(),
                        flags,
                        true,
                        target != null,
                        source.solverInputs.springEnabled,
                        team.clothSimulateWeight,
                        team.clothLodFadeWeight,
                        target.position,
                        target.rotation,
                        target.localPosition,
                        target.localRotation,
                        ToVector3(worldPositions[vertex]),
                        worldRotations[vertex],
                        local.publish ? local.position : target.localPosition,
                        local.publish ? local.rotation : target.localRotation));
                    values[sourceIndex] = value;
                    if (applyWrites)
                        Apply(target, value);
                }
            }
            return values;
        }

        private void ValidatePublication(K.Double3[][] positions, K.Float4[][] rotations)
        {
            if (positions == null || rotations == null ||
                positions.Length != F.OwnerCount || rotations.Length != F.OwnerCount)
                throw new ArgumentException("Four owner publication arrays are required.");
            for (int owner = 0; owner < F.OwnerCount; owner++)
            {
                int count = _data.owners[owner].proxyVertexCount;
                if (positions[owner] == null || rotations[owner] == null ||
                    positions[owner].Length != count || rotations[owner].Length != count)
                    throw new ArgumentException("Owner publication cardinality differs at " + owner + ".");
            }
        }

        private static T.TransformFlags Flags(byte attribute)
        {
            switch (attribute)
            {
                case 0: return T.TransformFlags.Read | T.TransformFlags.Enable;
                case 1: return T.TransformFlags.Read | T.TransformFlags.World |
                               T.TransformFlags.Restore | T.TransformFlags.Enable;
                case 2: return T.TransformFlags.Read | T.TransformFlags.Local |
                               T.TransformFlags.Restore | T.TransformFlags.Enable;
                default: throw new NotSupportedException(
                    "Endminf publication attribute is outside the recovered 0-2 domain.");
            }
        }

        private static void Apply(Transform target, T.FinalValue value)
        {
            if (!value.publish)
                return;
            if (value.branch == T.PublicationBranch.World)
            {
                if (value.writePosition) target.position = value.position;
                if (value.writeRotation) target.rotation = value.rotation;
            }
            else if (value.branch == T.PublicationBranch.Local)
            {
                if (value.writePosition) target.localPosition = value.position;
                if (value.writeRotation) target.localRotation = value.rotation;
            }
        }

        private static Vector3 ToVector3(T.Double3 value) =>
            new Vector3((float)value.x, (float)value.y, (float)value.z);
    }
}
