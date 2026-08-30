using System;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Value-only model of the observed UseCrossFrameJob publication order.
    /// AddTransform seeds both current and last arrays from the same live
    /// transforms. Each ClothUpdate reads current transforms, publishes the
    /// completed last arrays, then schedules current simulation. Retaining that
    /// current result for the next callback is behaviorally implied by the
    /// observed array histories. The public native CopyDoubleBuffer job is a
    /// current-to-last value copy, not a pointer swap, but it has no direct caller
    /// in the statically closed target pipeline. This value model therefore does
    /// not claim that dormant method as the transport owner; that ownership
    /// remains unresolved. Reset seeding is handled separately by the owner solver.
    /// </summary>
    public sealed class EndfieldSecondaryDynamicsCrossFramePublication
    {
        public sealed class Frame
        {
            public readonly K.Double3[][] Positions;
            public readonly K.Float4[][] Rotations;
            public readonly int Generation;

            internal Frame(K.Double3[][] positions, K.Float4[][] rotations, int generation)
            {
                Positions = Clone(positions);
                Rotations = Clone(rotations);
                Generation = generation;
            }
        }

        private Frame pending;
        private bool publicationTaken;

        public bool IsSeeded => pending != null;
        public int PendingGeneration => pending == null ? -1 : pending.Generation;
        public int LastPublishedGeneration { get; private set; } = -1;

        public void SeedFromAddTransform(K.Double3[][] positions, K.Float4[][] rotations)
        {
            Validate(positions, rotations);
            pending = new Frame(positions, rotations, 0);
            publicationTaken = false;
            LastPublishedGeneration = -1;
        }

        public Frame TakeCompletedForPublication()
        {
            if (pending == null)
                throw new InvalidOperationException(
                    "Cross-frame publication was not seeded from AddTransform state.");
            if (publicationTaken)
                throw new InvalidOperationException(
                    "Cross-frame publication was taken twice without staging simulation.");
            publicationTaken = true;
            LastPublishedGeneration = pending.Generation;
            return new Frame(pending.Positions, pending.Rotations, pending.Generation);
        }

        public void StageCurrentSimulation(K.Double3[][] positions, K.Float4[][] rotations)
        {
            if (pending == null)
                throw new InvalidOperationException(
                    "Cross-frame publication was not seeded from AddTransform state.");
            if (!publicationTaken)
                throw new InvalidOperationException(
                    "Current simulation cannot replace last arrays before their publication.");
            Validate(positions, rotations);
            pending = new Frame(positions, rotations, pending.Generation + 1);
            publicationTaken = false;
        }

        private static void Validate(K.Double3[][] positions, K.Float4[][] rotations)
        {
            if (positions == null || rotations == null ||
                positions.Length != EndfieldSecondaryDynamicsFrameCoordinator.OwnerCount ||
                rotations.Length != EndfieldSecondaryDynamicsFrameCoordinator.OwnerCount)
            {
                throw new ArgumentException(
                    "Cross-frame publication requires four source-ordered owners.");
            }
            for (int owner = 0; owner < positions.Length; owner++)
            {
                if (positions[owner] == null || rotations[owner] == null ||
                    positions[owner].Length != rotations[owner].Length)
                {
                    throw new ArgumentException(
                        "Cross-frame publication owner cardinality differs at " + owner + ".");
                }
            }
        }

        private static K.Double3[][] Clone(K.Double3[][] source)
        {
            var result = new K.Double3[source.Length][];
            for (int owner = 0; owner < source.Length; owner++)
                result[owner] = (K.Double3[])source[owner].Clone();
            return result;
        }

        private static K.Float4[][] Clone(K.Float4[][] source)
        {
            var result = new K.Float4[source.Length][];
            for (int owner = 0; owner < source.Length; owner++)
                result[owner] = (K.Float4[])source[owner].Clone();
            return result;
        }
    }
}
