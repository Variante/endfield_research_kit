using System;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsCrossFramePublicationVerifier
    {
        [MenuItem("Endfield/Character Recovery Lab/Verify Secondary Dynamics Cross-Frame Publication")]
        public static void Verify()
        {
            var buffer = new EndfieldSecondaryDynamicsCrossFramePublication();
            K.Double3[][] seedPositions = Positions(1.0);
            K.Float4[][] seedRotations = Rotations(1.0f);
            buffer.SeedFromAddTransform(seedPositions, seedRotations);

            // The seed must be isolated from caller mutation, like native
            // current/last NativeArrays rather than shared managed aliases.
            seedPositions[0][0].x = 99.0;
            EndfieldSecondaryDynamicsCrossFramePublication.Frame first =
                buffer.TakeCompletedForPublication();
            Require(first.Generation == 0 && first.Positions[0][0].x == 1.0,
                "AddTransform-equivalent seed was not isolated");

            K.Double3[][] nextPositions = Positions(2.0);
            K.Float4[][] nextRotations = Rotations(2.0f);
            buffer.StageCurrentSimulation(nextPositions, nextRotations);
            nextPositions[0][0].x = 88.0;
            EndfieldSecondaryDynamicsCrossFramePublication.Frame second =
                buffer.TakeCompletedForPublication();
            Require(second.Generation == 1 && second.Positions[0][0].x == 2.0,
                "current simulation was not deferred to the next publication");
            Require(buffer.LastPublishedGeneration == 1,
                "published generation telemetry differs");

            bool rejected = false;
            try
            {
                buffer.TakeCompletedForPublication();
            }
            catch (InvalidOperationException)
            {
                rejected = true;
            }
            Require(rejected, "double publication did not fail closed");
            Debug.Log("Secondary dynamics cross-frame publication verified.");
        }

        private static K.Double3[][] Positions(double value)
        {
            var result = new K.Double3[
                EndfieldSecondaryDynamicsFrameCoordinator.OwnerCount][];
            for (int owner = 0; owner < result.Length; owner++)
                result[owner] = new[] { new K.Double3(value + owner, 0.0, 0.0) };
            return result;
        }

        private static K.Float4[][] Rotations(float value)
        {
            var result = new K.Float4[
                EndfieldSecondaryDynamicsFrameCoordinator.OwnerCount][];
            for (int owner = 0; owner < result.Length; owner++)
                result[owner] = new[] { new K.Float4(0f, 0f, 0f, value) };
            return result;
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
