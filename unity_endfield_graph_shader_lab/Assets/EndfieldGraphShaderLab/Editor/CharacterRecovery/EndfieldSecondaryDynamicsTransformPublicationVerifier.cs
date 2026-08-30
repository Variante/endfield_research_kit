using System;
using System.Collections.Generic;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsTransformPublicationVerifier
    {
        [MenuItem("Endfield/Character Recovery/Verify Secondary Dynamics Transform Publication")]
        public static void VerifyMenu()
        {
            VerifyWorldEquation();
            VerifyLocalEquationAndGuards();
            VerifyPositiveScaleQuaternionSignMask();
            VerifyFinalWorldAndFixedBranches();
            VerifyFinalLocalAndWeightBranches();
            VerifyEntryGatesAndPrecedence();
            VerifyDuplicatePreservation();
            Debug.Log("Verified secondary-dynamics transform publication world/local equations, flags, weight branches, fixed behavior, and source-ordered duplicates.");
        }

        private static void VerifyWorldEquation()
        {
            const float qz90 = 0.70710677f;
            var team = Team(
                10,
                30,
                50,
                EndfieldSecondaryDynamicsTransformPublicationAdapter.PositiveScaleQuaternionSignMask,
                1.0f,
                1.0f);
            var value = EndfieldSecondaryDynamicsTransformPublication.CalculateWorld(
                new EndfieldSecondaryDynamicsTransformPublication.WorldSource(
                    12, 1, team,
                    new EndfieldSecondaryDynamicsTransformPublication.Double3(1.25, -2.5, 3.75),
                    Quaternion.identity,
                    new Quaternion(0.0f, 0.0f, qz90, qz90)));
            Require(value.publish, "world row was rejected");
            Require(value.destinationIndex == 52, "world destination equation");
            Require(value.position.x == 1.25 && value.position.y == -2.5 && value.position.z == 3.75,
                "world position publication");
            RequireFloatBits(value.rotation.x, 0.0f, "world componentwise sign-mask x");
            RequireFloatBits(value.rotation.y, 0.0f, "world componentwise sign-mask y");
            RequireFloatBits(value.rotation.z, qz90, "world componentwise sign-mask z");
            RequireFloatBits(value.rotation.w, qz90, "world componentwise sign-mask w");

            var skipped = EndfieldSecondaryDynamicsTransformPublication.CalculateWorld(
                new EndfieldSecondaryDynamicsTransformPublication.WorldSource(
                    12, 0, team, default, Quaternion.identity, Quaternion.identity));
            Require(!skipped.publish, "team zero world guard");
        }

        private static void VerifyLocalEquationAndGuards()
        {
            var team = Team(10, 30, 50, new Quaternion(2.0f, 3.0f, 4.0f, 5.0f), 1.0f, 1.0f);
            var positions = FilledDouble3(64);
            var rotations = FilledQuaternion(64, Quaternion.identity);
            var scales = FilledVector3(64, Vector3.one);
            positions[52] = new EndfieldSecondaryDynamicsTransformPublication.Double3(5.0, 7.0, 9.0);
            positions[51] = new EndfieldSecondaryDynamicsTransformPublication.Double3(1.0, 2.0, 3.0);
            scales[51] = new Vector3(2.0f, 5.0f, 3.0f);

            var value = EndfieldSecondaryDynamicsTransformPublication.CalculateLocal(
                new EndfieldSecondaryDynamicsTransformPublication.LocalSource(12, 1, 0x02, 1, team),
                positions, rotations, scales);
            Require(value.publish && value.childIndex == 52 && value.parentIndex == 51, "local indices");
            RequireVector(value.position, new Vector3(2.0f, 1.0f, 2.0f), "local double position equation");
            RequireQuaternionExact(value.rotation, new Quaternion(0.0f, 0.0f, 0.0f, 5.0f),
                "local componentwise negative-scale rotation equation");

            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateLocal(
                new EndfieldSecondaryDynamicsTransformPublication.LocalSource(12, 0, 0x02, 1, team),
                positions, rotations, scales).publish, "local team guard");
            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateLocal(
                new EndfieldSecondaryDynamicsTransformPublication.LocalSource(12, 1, 0x02, -1, team),
                positions, rotations, scales).publish, "local parent guard");
            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateLocal(
                new EndfieldSecondaryDynamicsTransformPublication.LocalSource(12, 1, 0x01, 1, team),
                positions, rotations, scales).publish, "local attribute guard");
        }

        private static void VerifyPositiveScaleQuaternionSignMask()
        {
            const float qz90 = 0.70710677f;
            var team = Team(
                0,
                0,
                0,
                EndfieldSecondaryDynamicsTransformPublicationAdapter
                    .PositiveScaleQuaternionSignMask,
                1f,
                1f);
            var positions = FilledDouble3(2);
            var rotations = FilledQuaternion(2, Quaternion.identity);
            rotations[1] = new Quaternion(0f, 0f, qz90, qz90);
            var scales = FilledVector3(2, Vector3.one);
            EndfieldSecondaryDynamicsTransformPublication.LocalValue value =
                EndfieldSecondaryDynamicsTransformPublication.CalculateLocal(
                    new EndfieldSecondaryDynamicsTransformPublication.LocalSource(
                        1,
                        1,
                        0x02,
                        0,
                        team),
                    positions,
                    rotations,
                    scales);
            Require(value.publish, "positive-scale local publication");
            RequireFloatBits(value.rotation.x, 0f,
                "positive-scale local rotation x");
            RequireFloatBits(value.rotation.y, 0f,
                "positive-scale local rotation y");
            RequireFloatBits(value.rotation.z, qz90,
                "positive-scale local rotation z");
            RequireFloatBits(value.rotation.w, qz90,
                "positive-scale local rotation w");
        }

        private static void VerifyFinalWorldAndFixedBranches()
        {
            var spring = Final(
                0, 100,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                true, 0.5f, 1.0f);
            var springValue = EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(spring);
            Require(springValue.publish && springValue.branch == EndfieldSecondaryDynamicsTransformPublication.PublicationBranch.World,
                "world branch");
            Require(springValue.writePosition && springValue.writeRotation, "spring writes");
            RequireVector(springValue.position, new Vector3(5.0f, 10.0f, 15.0f), "spring weighted world position");
            RequireQuaternion(springValue.rotation,
                new Quaternion(0.0f, 0.38268343f, 0.0f, 0.9238795f),
                "spring shortest-path world rotation");

            var fixedInput = Final(
                1, 101,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                false, 1.0f, 1.0f);
            var fixedValue = EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(fixedInput);
            Require(!fixedValue.writePosition && fixedValue.writeRotation, "fixed world write mask");
            RequireVector(fixedValue.position, fixedInput.currentWorldPosition, "fixed preserves world position");
        }

        private static void VerifyFinalLocalAndWeightBranches()
        {
            var weighted = Final(
                2, 102,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                true, 0.5f, 0.5f);
            var weightedValue = EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(weighted);
            Require(weightedValue.weight == 0.25f, "binary32 weight product");
            RequireVector(weightedValue.position, new Vector3(1.0f, 2.0f, 3.0f), "weighted local position");
            RequireQuaternion(weightedValue.rotation,
                new Quaternion(0.19509032f, 0.0f, 0.0f, 0.98078525f),
                "weighted shortest-path local rotation");

            var saturated = Final(
                3, 103,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                true, 2.0f, 0.75f);
            var saturatedValue = EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(saturated);
            Require(saturatedValue.weight == 1.5f, "unclamped weight value");
            RequireVector(saturatedValue.position, saturated.targetLocalPosition, "weight >= 1 direct local assignment");
            RequireQuaternionExact(saturatedValue.rotation, saturated.targetLocalRotation, "weight >= 1 direct local rotation");

            var negative = Final(
                4, 104,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                true, -1.0f, 0.5f);
            var negativeValue = EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(negative);
            RequireVector(negativeValue.position, negative.currentLocalPosition, "saturated negative lerp");
            RequireQuaternion(negativeValue.rotation, negative.currentLocalRotation, "saturated negative slerp");
        }

        private static void VerifyEntryGatesAndPrecedence()
        {
            var both = Final(
                5, 105,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                true, 1.0f, 1.0f);
            Require(EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(both).branch ==
                    EndfieldSecondaryDynamicsTransformPublication.PublicationBranch.World,
                "world precedence");

            var disabled = Final(6, 106, EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                true, 1.0f, 1.0f);
            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(disabled).publish, "enable gate");

            var culled = Final(7, 107,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                true, 1.0f, 1.0f, cullingVisible: false);
            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(culled).publish, "culling gate");

            var invalid = Final(8, 108,
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                true, 1.0f, 1.0f, nativeValid: false);
            Require(!EndfieldSecondaryDynamicsTransformPublication.CalculateFinal(invalid).publish, "native validity gate");
        }

        private static void VerifyDuplicatePreservation()
        {
            const int duplicateTransform = 777;
            var inputs = new[]
            {
                Final(20, duplicateTransform,
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.World,
                    true, 1.0f, 1.0f),
                Final(21, 888,
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                    true, 1.0f, 1.0f),
                Final(22, duplicateTransform,
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Enable |
                    EndfieldSecondaryDynamicsTransformPublication.TransformFlags.Local,
                    true, 1.0f, 1.0f),
            };
            var values = EndfieldSecondaryDynamicsTransformPublication.CalculateFinalSourceOrdered(inputs);
            Require(values.Length == 3, "duplicate output cardinality");
            Require(values[0].sourceIndex == 20 && values[1].sourceIndex == 21 && values[2].sourceIndex == 22,
                "source order preservation");
            Require(values[0].transformId == duplicateTransform && values[2].transformId == duplicateTransform,
                "duplicate transform preservation");
            Require(values[0].branch == EndfieldSecondaryDynamicsTransformPublication.PublicationBranch.World &&
                    values[2].branch == EndfieldSecondaryDynamicsTransformPublication.PublicationBranch.Local,
                "no duplicate winner arbitration");
        }

        private static EndfieldSecondaryDynamicsTransformPublication.TeamPublicationData Team(
            int commonStart, int boneStart, int transformStart, Quaternion negativeScale,
            float simulateWeight, float lodWeight)
        {
            return new EndfieldSecondaryDynamicsTransformPublication.TeamPublicationData
            {
                proxyCommonChunk = new EndfieldSecondaryDynamicsTransformPublication.Chunk(commonStart),
                proxyBoneChunk = new EndfieldSecondaryDynamicsTransformPublication.Chunk(boneStart),
                proxyTransformChunk = new EndfieldSecondaryDynamicsTransformPublication.Chunk(transformStart),
                negativeScaleQuaternionValue = negativeScale,
                clothSimulateWeight = simulateWeight,
                clothLodFadeWeight = lodWeight,
            };
        }

        private static EndfieldSecondaryDynamicsTransformPublication.FinalInput Final(
            int sourceIndex,
            int transformId,
            EndfieldSecondaryDynamicsTransformPublication.TransformFlags flags,
            bool spring,
            float simulateWeight,
            float lodWeight,
            bool cullingVisible = true,
            bool nativeValid = true)
        {
            return new EndfieldSecondaryDynamicsTransformPublication.FinalInput(
                sourceIndex, transformId, flags, cullingVisible, nativeValid, spring,
                simulateWeight, lodWeight,
                Vector3.zero, Quaternion.identity,
                Vector3.zero, Quaternion.identity,
                new Vector3(10.0f, 20.0f, 30.0f), Quaternion.AngleAxis(90.0f, Vector3.up),
                new Vector3(4.0f, 8.0f, 12.0f), Quaternion.AngleAxis(90.0f, Vector3.right));
        }

        private static List<EndfieldSecondaryDynamicsTransformPublication.Double3> FilledDouble3(int count)
        {
            var values = new List<EndfieldSecondaryDynamicsTransformPublication.Double3>(count);
            for (int i = 0; i < count; i++)
                values.Add(default);
            return values;
        }

        private static List<Quaternion> FilledQuaternion(int count, Quaternion value)
        {
            var values = new List<Quaternion>(count);
            for (int i = 0; i < count; i++)
                values.Add(value);
            return values;
        }

        private static List<Vector3> FilledVector3(int count, Vector3 value)
        {
            var values = new List<Vector3>(count);
            for (int i = 0; i < count; i++)
                values.Add(value);
            return values;
        }

        private static void RequireVector(Vector3 actual, Vector3 expected, string label)
        {
            Require(actual == expected, label + ": expected " + expected + ", got " + actual);
        }

        private static void RequireQuaternion(Quaternion actual, Quaternion expected, string label)
        {
            Require(Mathf.Abs(actual.x - expected.x) <= 1.0e-6f &&
                    Mathf.Abs(actual.y - expected.y) <= 1.0e-6f &&
                    Mathf.Abs(actual.z - expected.z) <= 1.0e-6f &&
                    Mathf.Abs(actual.w - expected.w) <= 1.0e-6f,
                label + ": expected " + expected + ", got " + actual);
        }

        private static void RequireQuaternionExact(Quaternion actual, Quaternion expected, string label)
        {
            Require(actual.x == expected.x && actual.y == expected.y && actual.z == expected.z && actual.w == expected.w,
                label + ": expected exact " + expected + ", got " + actual);
        }

        private static void RequireFloatBits(float actual, float expected, string label)
        {
            Require(
                BitConverter.SingleToInt32Bits(actual) ==
                BitConverter.SingleToInt32Bits(expected),
                label + ": expected exact bits " +
                BitConverter.SingleToInt32Bits(expected).ToString("x8") +
                ", got " + BitConverter.SingleToInt32Bits(actual).ToString("x8"));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException("Secondary dynamics transform publication verification failed: " + message);
        }
    }
}
