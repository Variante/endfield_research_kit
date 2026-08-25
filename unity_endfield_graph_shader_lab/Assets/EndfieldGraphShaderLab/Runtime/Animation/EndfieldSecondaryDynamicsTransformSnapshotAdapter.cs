using System;
using UnityEngine;
using F = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsFrameCoordinator;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using P = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsEndminfColliderPreparation;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Exact source-ordered Unity Transform read boundary for the inert Endminf
    /// frame coordinator. It snapshots values only and has no writeback path.
    /// </summary>
    public sealed class EndfieldSecondaryDynamicsTransformSnapshotAdapter
    {
        public sealed class SnapshotFrame
        {
            public F.OwnerTransformSnapshot[] Owners;
            public P.TransformSample[] PreviousColliderSamples;
            public P.TransformSample[] CurrentColliderSamples;
            public K.Float3 ActorScale;
            public bool ActorRootStationary;
            public bool NegativeScale;
        }

        private readonly Transform _actorRoot;
        private readonly Transform[][] _ownerTransforms;
        private readonly Transform[] _colliderTransforms;
        private F.OwnerTransformSnapshot[] _owners;
        private P.TransformSample[] _colliders;
        private Vector3 _rootPosition;
        private Quaternion _rootRotation;
        private bool _initialized;

        public EndfieldSecondaryDynamicsTransformSnapshotAdapter(
            Transform actorRoot,
            EndfieldSecondaryDynamicsData data)
        {
            if (actorRoot == null) throw new ArgumentNullException(nameof(actorRoot));
            if (data == null) throw new ArgumentNullException(nameof(data));
            if (data.owners == null || data.owners.Length != F.OwnerCount)
                throw new ArgumentException("Exactly four Endminf owners are required.", nameof(data));
            if (data.colliders == null ||
                data.colliders.Length != P.AuthoredColliderCount)
                throw new ArgumentException("Exactly ten Endminf colliders are required.", nameof(data));

            _actorRoot = actorRoot;
            _ownerTransforms = new Transform[F.OwnerCount][];
            for (int owner = 0; owner < F.OwnerCount; owner++)
            {
                var source = data.owners[owner];
                if (source.proxyTransformPaths == null ||
                    source.proxyTransformPaths.Length != source.proxyVertexCount)
                    throw new ArgumentException("Owner transform topology differs at index " + owner + ".");
                _ownerTransforms[owner] = new Transform[source.proxyVertexCount];
                for (int vertex = 0; vertex < source.proxyVertexCount; vertex++)
                    _ownerTransforms[owner][vertex] = Resolve(
                        actorRoot, source.proxyTransformPaths[vertex],
                        "owner " + owner + " vertex " + vertex);
            }

            _colliderTransforms = new Transform[P.AuthoredColliderCount];
            for (int collider = 0; collider < _colliderTransforms.Length; collider++)
                _colliderTransforms[collider] = Resolve(
                    actorRoot, data.colliders[collider].transformPath,
                    "collider " + collider);
        }

        public SnapshotFrame Capture()
        {
            F.OwnerTransformSnapshot[] currentOwners = ReadOwners();
            P.TransformSample[] currentColliders = ReadColliders();
            Vector3 currentRootPosition = _actorRoot.position;
            Quaternion currentRootRotation = _actorRoot.rotation;
            Vector3 scale = _actorRoot.lossyScale;

            if (!_initialized)
            {
                _owners = CloneAsInitial(currentOwners);
                _colliders = (P.TransformSample[])currentColliders.Clone();
                _rootPosition = currentRootPosition;
                _rootRotation = currentRootRotation;
                _initialized = true;
            }

            var result = new SnapshotFrame
            {
                Owners = MergePreviousAndCurrent(_owners, currentOwners),
                PreviousColliderSamples = (P.TransformSample[])_colliders.Clone(),
                CurrentColliderSamples = (P.TransformSample[])currentColliders.Clone(),
                ActorScale = F3(scale),
                ActorRootStationary = Same(_rootPosition, currentRootPosition) &&
                                      Same(_rootRotation, currentRootRotation),
                NegativeScale = scale.x * scale.y * scale.z < 0f,
            };

            _owners = CloneAsInitial(currentOwners);
            _colliders = (P.TransformSample[])currentColliders.Clone();
            _rootPosition = currentRootPosition;
            _rootRotation = currentRootRotation;
            return result;
        }

        private F.OwnerTransformSnapshot[] ReadOwners()
        {
            var result = new F.OwnerTransformSnapshot[F.OwnerCount];
            for (int owner = 0; owner < result.Length; owner++)
            {
                Transform[] bindings = _ownerTransforms[owner];
                var positions = new K.Double3[bindings.Length];
                var rotations = new K.Float4[bindings.Length];
                for (int vertex = 0; vertex < bindings.Length; vertex++)
                {
                    Transform transform = bindings[vertex];
                    Vector3 position = transform.position;
                    Quaternion rotation = transform.rotation;
                    positions[vertex] = new K.Double3(position.x, position.y, position.z);
                    rotations[vertex] = new K.Float4(
                        rotation.x, rotation.y, rotation.z, rotation.w);
                }
                result[owner] = new F.OwnerTransformSnapshot
                {
                    CurrentWorldPositions = positions,
                    CurrentWorldRotations = rotations,
                    PreviousWorldPositions = (K.Double3[])positions.Clone(),
                    PreviousWorldRotations = (K.Float4[])rotations.Clone(),
                };
            }
            return result;
        }

        private P.TransformSample[] ReadColliders()
        {
            var result = new P.TransformSample[_colliderTransforms.Length];
            for (int index = 0; index < result.Length; index++)
            {
                Transform transform = _colliderTransforms[index];
                Vector3 position = transform.position;
                Quaternion rotation = transform.rotation;
                Vector3 scale = transform.lossyScale;
                result[index] = new P.TransformSample(
                    new K.Double3(position.x, position.y, position.z),
                    new K.Float4(rotation.x, rotation.y, rotation.z, rotation.w),
                    F3(scale));
            }
            return result;
        }

        private static F.OwnerTransformSnapshot[] MergePreviousAndCurrent(
            F.OwnerTransformSnapshot[] previous,
            F.OwnerTransformSnapshot[] current)
        {
            var result = new F.OwnerTransformSnapshot[F.OwnerCount];
            for (int owner = 0; owner < result.Length; owner++)
                result[owner] = new F.OwnerTransformSnapshot
                {
                    PreviousWorldPositions =
                        (K.Double3[])previous[owner].CurrentWorldPositions.Clone(),
                    PreviousWorldRotations =
                        (K.Float4[])previous[owner].CurrentWorldRotations.Clone(),
                    CurrentWorldPositions =
                        (K.Double3[])current[owner].CurrentWorldPositions.Clone(),
                    CurrentWorldRotations =
                        (K.Float4[])current[owner].CurrentWorldRotations.Clone(),
                };
            return result;
        }

        private static F.OwnerTransformSnapshot[] CloneAsInitial(
            F.OwnerTransformSnapshot[] source)
        {
            var result = new F.OwnerTransformSnapshot[F.OwnerCount];
            for (int owner = 0; owner < result.Length; owner++)
                result[owner] = new F.OwnerTransformSnapshot
                {
                    CurrentWorldPositions =
                        (K.Double3[])source[owner].CurrentWorldPositions.Clone(),
                    CurrentWorldRotations =
                        (K.Float4[])source[owner].CurrentWorldRotations.Clone(),
                    PreviousWorldPositions =
                        (K.Double3[])source[owner].CurrentWorldPositions.Clone(),
                    PreviousWorldRotations =
                        (K.Float4[])source[owner].CurrentWorldRotations.Clone(),
                };
            return result;
        }

        private static Transform Resolve(Transform root, string path, string label)
        {
            if (string.IsNullOrEmpty(path))
                throw new ArgumentException("Empty transform path for " + label + ".");
            Transform result = root.Find(path);
            if (result == null)
                throw new ArgumentException("Transform path does not resolve for " +
                    label + ": " + path);
            return result;
        }

        private static K.Float3 F3(Vector3 value) =>
            new K.Float3(value.x, value.y, value.z);

        private static bool Same(Vector3 left, Vector3 right) =>
            Bits(left.x) == Bits(right.x) && Bits(left.y) == Bits(right.y) &&
            Bits(left.z) == Bits(right.z);

        private static bool Same(Quaternion left, Quaternion right) =>
            Bits(left.x) == Bits(right.x) && Bits(left.y) == Bits(right.y) &&
            Bits(left.z) == Bits(right.z) && Bits(left.w) == Bits(right.w);

        private static uint Bits(float value) =>
            BitConverter.ToUInt32(BitConverter.GetBytes(value), 0);
    }
}
