using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;
using K = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsKernels;
using C = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCalcLineManagedEquations;
using R = EndfieldGraphShaderLab.EndfieldSecondaryDynamicsCalcLineRouteSelection;

namespace EndfieldGraphShaderLabEditor
{
    public static class EndfieldSecondaryDynamicsCalcLineManagedEquationsVerifier
    {
        private const string TopologyFixturePath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_calc_line_burst_golden_vectors.json";

        [MenuItem("Endfield/Character Recovery/Verify Secondary Dynamics CalcLine Managed Equations")]
        public static void VerifyMenu()
        {
            VerifyPackedChildIndex();
            VerifyParallelAndQuarterTurnGoldenCases();
            VerifyAntiparallelAxisSelection();
            VerifyBinary32HelperGrouping();
            VerifyParentAndChildEquations();
            VerifyPerChildDirectionAndParentSum();
            VerifyEmptyAndUndefinedBranchesFailClosed();
            VerifyDualCpuBurstEquations();
            VerifyEndminfTopologyFixture();
            VerifyLiveRouteAdmissionFailsClosed();
            Debug.Log(
                "Verified value-only secondary-dynamics CalcLine managed and dual-CPU " +
                "Burst equations; runtime route remains fail-closed until a validated trace.");
        }

        private static void VerifyPackedChildIndex()
        {
            C.ChildIndex decoded = C.DecodeChildIndex((0xabcU << 20) | 0x54321U);
            Require(decoded.count == 0xabc, "packed child count");
            Require(decoded.localStart == 0x54321, "packed child local start");
        }

        private static void VerifyParallelAndQuarterTurnGoldenCases()
        {
            Require(C.TryFromToRotation(
                D(4.0, 0.0, 0.0),
                D(7.0, 0.0, 0.0),
                0.37,
                out K.Float4 parallel), "parallel FromToRotation");
            RequireQuaternionBits(
                parallel,
                0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
                "parallel identity");

            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(0.0, 1.0, 0.0),
                1.0,
                out K.Float4 axisAngle), "ninety-degree FromToRotation");
            RequireQuaternionBits(
                axisAngle,
                0x00000000U, 0x00000000U, 0x3f3504f4U, 0x3f3504f3U,
                "pinned float-half-angle AxisAngle");

            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(0.0, 1.0, 0.0),
                0.5,
                out K.Float4 quarterTurn), "quarter-turn FromToRotation");
            RequireQuaternionBits(
                quarterTurn,
                0x00000000U, 0x00000000U, 0x3ec3ef16U, 0x3f6c835eU,
                "half interpolation of ninety degrees");
        }

        private static void VerifyAntiparallelAxisSelection()
        {
            Require(C.TryFromToRotation(
                D(1.0, 0.0, 0.0),
                D(-1.0, 0.0, 0.0),
                1.0,
                out K.Float4 positiveZ), "x antiparallel branch");
            RequireQuaternionBits(
                positiveZ,
                0x00000000U, 0x00000000U, 0x3f800000U, 0xb33bbd2eU,
                "x antiparallel deterministic axis");

            Require(C.TryFromToRotation(
                D(0.0, 1.0, 0.0),
                D(0.0, -1.0, 0.0),
                1.0,
                out K.Float4 negativeZ), "y antiparallel branch");
            RequireQuaternionBits(
                negativeZ,
                0x00000000U, 0x00000000U, 0xbf800000U, 0xb33bbd2eU,
                "y antiparallel deterministic axis");

            // For finite negative X -> positive X, the pinned comparison chooses
            // positive X as its reference. Their cross product is zero. The
            // source then normalizes that zero axis without a guard, so this
            // value model must refuse to claim a quaternion for that case.
            Require(!C.TryFromToRotation(
                D(-1.0, 0.0, 0.0),
                D(1.0, 0.0, 0.0),
                1.0,
                out _), "negative-X antiparallel zero-axis branch must fail closed");
        }

        private static void VerifyBinary32HelperGrouping()
        {
            // Exact bit inputs deliberately distinguish the pinned grouping
            // from a left-associated Hamilton expression. Pinned y/z are
            // 4100ceb8/c18426e4; reassociation gives 4100ceb7/c18426e3.
            K.Float4 hamiltonLeft = QB(
                0x3f1c497cU, 0x40930be2U, 0x404c5865U, 0xc05dcaf9U);
            K.Float4 hamiltonRight = QB(
                0xc0452e61U, 0xc0e32288U, 0x40e41e55U, 0xbf03634aU);
            K.Float4 hamilton = C.MultiplyQuaternionBinary32(
                hamiltonLeft,
                hamiltonRight);
            RequireQuaternionBits(
                hamilton,
                0x428391bcU, 0x4100ceb8U, 0xc18426e4U, 0x41583d0cU,
                "pinned Hamilton grouping");

            // These exact inputs similarly distinguish the quaternion-vector
            // grouping. Pinned x/y are c2d5a4b6/c4e22f5c; a reassociated
            // expression produces c2d5a4b8/c4e22f5b.
            K.Float4 rotateQuaternion = QB(
                0xc0acdd5dU, 0x40988ce0U, 0x40dfbac4U, 0x3fa48ce5U);
            K.Float3 rotateVector = FB(
                0x3effe6ffU, 0x40f180e6U, 0xc0f71857U);
            K.Float3 rotated = C.RotateQuaternionBinary32(
                rotateQuaternion,
                rotateVector);
            RequireFloat3Bits(
                rotated,
                0xc2d5a4b6U, 0xc4e22f5cU, 0x448f898eU,
                "pinned quaternion-vector grouping");
        }

        private static void VerifyParentAndChildEquations()
        {
            var parent = new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(-1.0f, 1.0f, -1.0f, 1.0f),
                C.FlagMove,
                0.5,
                0.25);
            var children = new[]
            {
                new C.ChildSource(
                    D(0.0, 1.0, 0.0),
                    F(1.0f, 0.0f, 0.0f),
                    Q(0.0f, 0.0f, 0.70710677f, 0.70710677f),
                    C.FlagMove),
            };
            Require(C.TryCalculateParent(parent, children, out C.ParentValue result),
                "single-child parent equation");
            Require(result.hasChildren && result.children.Length == 1, "single child result");
            RequireDouble3(result.restSum, D(1.0, 0.0, 0.0), "rest sum");
            RequireDouble3(result.directionAccumulator, D(0.0, 1.0, 0.0), "direction sum");
            RequireQuaternionBits(
                result.rotation,
                0x00000000U, 0x00000000U, 0x3ec3ef16U, 0x3f6c835eU,
                "move parent interpolation");

            // Signed local rotation is componentwise before Hamilton products.
            // local z is negated, then the +90-degree child FromTo cancels it.
            RequireQuaternionBits(
                result.children[0].rotation,
                0x00000000U, 0x00000000U, 0x33000000U, 0x3f800000U,
                "signed local and child FromTo order");
        }

        private static void VerifyPerChildDirectionAndParentSum()
        {
            var parent = new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(1.0f, 1.0f, 1.0f, 1.0f),
                0,
                0.1,
                1.0);
            var children = new[]
            {
                Child(D(3.0, 0.0, 0.0), F(1.0f, 0.0f, 0.0f), C.FlagMove),
                Child(D(99.0, 99.0, 99.0), F(0.0f, 2.0f, 0.0f), 0),
                Child(D(0.0, 0.0, 4.0), F(0.0f, 0.0f, 1.0f), C.FlagMove),
            };
            Require(C.TryCalculateParent(parent, children, out C.ParentValue result),
                "mixed move/non-move parent equation");

            // Every child uses its own direction for child FromTo. The parent
            // accumulator independently adds all three child directions.
            RequireDouble3(
                result.children[1].childDirection,
                D(0.0, 2.0, 0.0),
                "non-move child direction uses rest vector");
            RequireDouble3(
                result.directionAccumulator,
                D(3.0, 2.0, 4.0),
                "parent direction sums every child direction");
            RequireDouble3(result.restSum, D(1.0, 2.0, 1.0), "ordered rest sum");
        }

        private static void VerifyEmptyAndUndefinedBranchesFailClosed()
        {
            C.ParentSource parent = IdentityParent();
            Require(C.TryCalculateParent(parent, Array.Empty<C.ChildSource>(), out C.ParentValue empty),
                "zero-child branch");
            Require(!empty.hasChildren && empty.children.Length == 0, "zero-child no-write marker");
            RequireQuaternionBits(
                empty.rotation,
                0x00000000U, 0x00000000U, 0x00000000U, 0x3f800000U,
                "zero-child preserves parent rotation");

            Require(!C.TryFromToRotation(
                D(0.0, 0.0, 0.0), D(1.0, 0.0, 0.0), 1.0, out _),
                "zero FromTo input must fail closed");
            Require(!C.TryFromToRotation(
                D(double.NaN, 0.0, 0.0), D(1.0, 0.0, 0.0), 1.0, out _),
                "non-finite FromTo input must fail closed");

            C.ChildSource degenerate = Child(
                D(1.0, 0.0, 0.0), F(0.0f, 0.0f, 0.0f), C.FlagMove);
            Require(!C.TryCalculateParent(parent, new[] { degenerate }, out _),
                "zero authored rest vector must fail closed");

            var fixedZeroWithMovable = new[]
            {
                Child(D(1.0, 0.0, 0.0), F(1.0f, 0.0f, 0.0f), C.FlagMove),
                Child(D(0.0, 0.0, 0.0), F(0.0f, 0.0f, 0.0f), 0),
            };
            Require(C.TryCalculateParentBurst(
                    C.BurstCpuVariant.X64Sse2, parent, fixedZeroWithMovable,
                    out C.ParentValue fixedZeroResult),
                "fixed zero-offset child must skip child FromTo/write branch");
            RequireDouble3(
                fixedZeroResult.children[1].restVector,
                D(0.0, 0.0, 0.0),
                "fixed zero-offset child still contributes its rest vector");
            RequireDouble3(
                fixedZeroResult.directionAccumulator,
                D(1.0, 0.0, 0.0),
                "fixed zero-offset child preserves the finite parent accumulator");
        }

        private static void VerifyDualCpuBurstEquations()
        {
            var parent = new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(1.0f, 1.0f, 1.0f, 1.0f),
                C.FlagMove,
                0.4,
                0.9);
            var children = new[]
            {
                Child(D(0.0, 1.0, 0.0), F(1.0f, 0.0f, 0.0f), C.FlagMove),
                Child(D(0.0, 0.0, 1.0), F(0.0f, 1.0f, 0.0f), C.FlagMove),
            };

            Require(C.TryCalculateParentBurst(
                C.BurstCpuVariant.X64Sse2, parent, children, out C.ParentValue sse),
                "SSE2 CalcLine Burst equation");
            Require(C.TryCalculateParentBurst(
                C.BurstCpuVariant.Avx2, parent, children, out C.ParentValue avx),
                "AVX2 CalcLine Burst equation");
            RequireQuaternionBits(
                sse.rotation,
                0x3df5d66bU, 0xbdf5d66bU, 0x3df5d66bU, 0x3f7a67e2U,
                "SSE2 two-child parent-sum vector");
            RequireQuaternionBits(
                avx.rotation,
                0x3df5d66bU, 0xbdf5d66bU, 0x3df5d66bU, 0x3f7a67e2U,
                "AVX2 two-child parent-sum vector");
            RequireQuaternionBits(
                sse.children[0].rotation,
                0x00000000U, 0x00000000U, 0x3f3504f4U, 0x3f3504f3U,
                "SSE2 first child vector");
            RequireQuaternionBits(
                avx.children[1].rotation,
                0x3f3504f4U, 0x00000000U, 0x00000000U, 0x3f3504f3U,
                "AVX2 second child vector");

            bool rejectedUnknown = false;
            try
            {
                C.TryCalculateParentBurst(
                    (C.BurstCpuVariant)99, parent, children, out _);
            }
            catch (ArgumentOutOfRangeException)
            {
                rejectedUnknown = true;
            }
            Require(rejectedUnknown, "unknown Burst CPU variant must fail closed");
        }

        private static void VerifyEndminfTopologyFixture()
        {
            TextAsset asset = AssetDatabase.LoadAssetAtPath<TextAsset>(TopologyFixturePath);
            if (asset == null)
                throw new FileNotFoundException("CalcLine topology fixture is missing.", TopologyFixturePath);
            Dictionary<string, object> root = JsonObject(
                ManifestMiniJson.Deserialize(asset.text), "CalcLine fixture root");
            Require(JsonText(root, "schema", "CalcLine fixture root") ==
                    "endfield.charinfo.secondary-dynamics-calc-line-burst-golden-vectors.v2",
                "CalcLine topology fixture schema");
            Require(JsonText(root, "status", "CalcLine fixture root") ==
                    "dual_cpu_core_source_and_endminf_topology_exact",
                "CalcLine topology fixture status");

            Dictionary<string, object> sourceFiles = JsonObject(
                JsonRequired(root, "sourceFiles", "CalcLine fixture root"), "sourceFiles");
            Require(JsonText(JsonObject(JsonRequired(sourceFiles, "payloadDecode", "sourceFiles"),
                        "payloadDecode"), "sha256", "payloadDecode") ==
                    "6c8eed435f2acd645d3fb3560acf7c993b5ef34c8ff2336de1a9fa87a1cbff1a",
                "payload-decode fixture hash");
            Require(JsonText(JsonObject(JsonRequired(sourceFiles, "solverInputs", "sourceFiles"),
                        "solverInputs"), "sha256", "solverInputs") ==
                    "fe91726b102a1104ed223be0aeb9138a76d58887a79851cc70736fd0d4ed6251",
                "solver-input fixture hash");

            Dictionary<string, object> boundary = JsonObject(
                JsonRequired(root, "boundary", "CalcLine fixture root"), "boundary");
            Require(JsonInteger(boundary, "endminfOwnerCount", "boundary") == 4,
                "topology owner count boundary");
            Require(JsonInteger(boundary, "endminfStateCountPerOwner", "boundary") == 3,
                "topology state count boundary");
            Require(JsonInteger(boundary, "endminfTopologyCaseCount", "boundary") == 12,
                "topology case count boundary");
            Require(JsonBoolean(boundary, "fullBaselinePackedChildTraversalExecuted", "boundary"),
                "full baseline/packed-child traversal boundary");
            Require(JsonBoolean(boundary, "rotationOnlyMutationProven", "boundary"),
                "rotation-only native mutation boundary");
            Require(!JsonBoolean(boundary, "runtimeRouteSelected", "boundary"),
                "topology fixture must not select a runtime route");
            Require(!JsonBoolean(boundary, "writebackConnected", "boundary"),
                "topology fixture must remain disconnected from writeback");

            List<object> owners = JsonArray(
                JsonRequired(root, "endminfTopologyCases", "CalcLine fixture root"),
                "endminfTopologyCases");
            string[] expectedOwners = { "MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat" };
            Require(owners.Count == expectedOwners.Length, "four topology owners");
            int totalStates = 0;
            for (int ownerIndex = 0; ownerIndex < owners.Count; ownerIndex++)
            {
                Dictionary<string, object> owner = JsonObject(
                    owners[ownerIndex], "topology owner " + ownerIndex);
                string ownerPath = JsonText(owner, "ownerPath", "topology owner");
                Require(ownerPath == expectedOwners[ownerIndex],
                    "topology owner order at " + ownerIndex);
                string topologySha = JsonText(owner, "topologySha256", ownerPath);
                Require(topologySha.Length == 64, ownerPath + " topology hash");
                Dictionary<string, object> sourceArrayHashes = JsonObject(
                    JsonRequired(owner, "sourceArraySha256", ownerPath),
                    ownerPath + ".sourceArraySha256");
                Require(sourceArrayHashes.Count == 12, ownerPath + " source array hash count");
                foreach (KeyValuePair<string, object> pair in sourceArrayHashes)
                    Require(pair.Value is string value && value.Length == 64,
                        ownerPath + " source array hash " + pair.Key);

                byte[] attributes = ByteArray(owner, "attributes", ownerPath);
                int[] parentIndices = IntArray(owner, "parentIndices", ownerPath);
                uint[] childIndices = UIntArray(owner, "childIndices", ownerPath);
                ushort[] childData = UShortArray(owner, "childData", ownerPath);
                K.Float3[] localPositions = Float3Rows(owner, "localPositionBitsLe", ownerPath);
                K.Float4[] localRotations = Float4Rows(owner, "localRotationBitsLe", ownerPath);
                byte[] baselineFlags = ByteArray(owner, "baselineFlags", ownerPath);
                int[] baselineStarts = IntArray(owner, "baselineStarts", ownerPath);
                int[] baselineCounts = IntArray(owner, "baselineCounts", ownerPath);
                ushort[] baselineData = UShortArray(owner, "baselineData", ownerPath);
                int vertexCount = attributes.Length;
                Require(vertexCount > 0 && parentIndices.Length == vertexCount &&
                        childIndices.Length == vertexCount && localPositions.Length == vertexCount &&
                        localRotations.Length == vertexCount,
                    ownerPath + " topology cardinalities");
                Require(baselineFlags.Length == baselineStarts.Length &&
                        baselineFlags.Length == baselineCounts.Length,
                    ownerPath + " baseline cardinalities");

                int childCursor = 0;
                int roots = 0;
                int leaves = 0;
                int multiChildParents = 0;
                int fixedVertices = 0;
                int movableVertices = 0;
                var seenChildren = new bool[vertexCount];
                for (int parent = 0; parent < vertexCount; parent++)
                {
                    if (parentIndices[parent] < 0) roots++;
                    if ((attributes[parent] & C.FlagMove) != 0) movableVertices++;
                    else fixedVertices++;
                    C.ChildIndex childIndex = C.DecodeChildIndex(childIndices[parent]);
                    Require(childIndex.localStart == childCursor && childIndex.count >= 0 &&
                            childCursor + childIndex.count <= childData.Length,
                        ownerPath + " packed child slice " + parent);
                    if (childIndex.count == 0) leaves++;
                    if (childIndex.count > 1) multiChildParents++;
                    for (int ordinal = 0; ordinal < childIndex.count; ordinal++)
                    {
                        int child = childData[childCursor + ordinal];
                        Require(child < vertexCount && !seenChildren[child] &&
                                parentIndices[child] == parent,
                            ownerPath + " packed child membership " + parent + ":" + ordinal);
                        seenChildren[child] = true;
                    }
                    childCursor += childIndex.count;
                }
                Require(childCursor == childData.Length, ownerPath + " packed child coverage");
                int baselineVisits = 0;
                for (int baseline = 0; baseline < baselineFlags.Length; baseline++)
                {
                    int start = baselineStarts[baseline];
                    int count = baselineCounts[baseline];
                    Require(start >= 0 && count >= 0 && start + count <= baselineData.Length,
                        ownerPath + " baseline slice " + baseline);
                    baselineVisits += count;
                    for (int ordinal = 0; ordinal < count; ordinal++)
                        Require(baselineData[start + ordinal] < vertexCount,
                            ownerPath + " baseline parent range " + baseline + ":" + ordinal);
                }
                VerifyCoverage(owner, ownerPath, vertexCount, baselineFlags.Length,
                    baselineVisits, roots, leaves, multiChildParents, fixedVertices, movableVertices);

                K.Float3 negativeScaleDirection = Float3(
                    JsonArray(JsonRequired(owner, "negativeScaleDirectionBitsLe", ownerPath),
                        ownerPath + ".negativeScaleDirectionBitsLe"), ownerPath + " scale direction");
                K.Float4 negativeScaleQuaternion = Float4(
                    JsonArray(JsonRequired(owner, "negativeScaleQuaternionBitsLe", ownerPath),
                        ownerPath + ".negativeScaleQuaternionBitsLe"), ownerPath + " scale quaternion");
                double rotationalInterpolation = ParseFloatLe(
                    JsonText(owner, "rotationalInterpolationBitsLe", ownerPath));
                double rootRotation = ParseFloatLe(JsonText(owner, "rootRotationBitsLe", ownerPath));
                List<object> states = JsonArray(JsonRequired(owner, "states", ownerPath),
                    ownerPath + ".states");
                string[] expectedStates =
                    { "bind_rest", "seeded_perturbation_a", "seeded_perturbation_b" };
                Require(states.Count == expectedStates.Length, ownerPath + " state count");
                totalStates += states.Count;
                for (int stateIndex = 0; stateIndex < states.Count; stateIndex++)
                {
                    Dictionary<string, object> state = JsonObject(
                        states[stateIndex], ownerPath + ".state " + stateIndex);
                    string stateName = JsonText(state, "name", ownerPath + ".state");
                    Require(stateName == expectedStates[stateIndex],
                        ownerPath + " state order " + stateIndex);
                    K.Double3[] positions = Double3Rows(
                        state, "positionBitsLe", ownerPath + "/" + stateName);
                    K.Float4[] inputRotations = Float4Rows(
                        state, "inputRotationBitsLe", ownerPath + "/" + stateName);
                    K.Float4[] expectedRotations = Float4Rows(
                        state, "outputRotationBitsLe", ownerPath + "/" + stateName);
                    Require(positions.Length == vertexCount && inputRotations.Length == vertexCount &&
                            expectedRotations.Length == vertexCount,
                        ownerPath + "/" + stateName + " state cardinalities");
                    VerifyNativeMutationDeclaration(state, ownerPath + "/" + stateName);
                    ReplayTopology(C.BurstCpuVariant.X64Sse2, ownerPath, stateName,
                        attributes, childIndices, childData, localPositions, localRotations,
                        baselineFlags, baselineStarts, baselineCounts, baselineData,
                        negativeScaleDirection, negativeScaleQuaternion,
                        rotationalInterpolation, rootRotation,
                        positions, inputRotations, expectedRotations);
                    ReplayTopology(C.BurstCpuVariant.Avx2, ownerPath, stateName,
                        attributes, childIndices, childData, localPositions, localRotations,
                        baselineFlags, baselineStarts, baselineCounts, baselineData,
                        negativeScaleDirection, negativeScaleQuaternion,
                        rotationalInterpolation, rootRotation,
                        positions, inputRotations, expectedRotations);
                }
            }
            Require(totalStates == 12, "twelve detached Endminf topology states");
        }

        private static void ReplayTopology(
            C.BurstCpuVariant variant,
            string ownerPath,
            string stateName,
            byte[] attributes,
            uint[] childIndices,
            ushort[] childData,
            K.Float3[] localPositions,
            K.Float4[] localRotations,
            byte[] baselineFlags,
            int[] baselineStarts,
            int[] baselineCounts,
            ushort[] baselineData,
            K.Float3 negativeScaleDirection,
            K.Float4 negativeScaleQuaternion,
            double rotationalInterpolation,
            double rootRotation,
            K.Double3[] positions,
            K.Float4[] inputRotations,
            K.Float4[] expectedRotations)
        {
            var rotations = (K.Float4[])inputRotations.Clone();
            var positionSnapshot = (K.Double3[])positions.Clone();
            for (int baseline = 0; baseline < baselineFlags.Length; baseline++)
            {
                if ((baselineFlags[baseline] & 1) == 0)
                    continue;
                int start = baselineStarts[baseline];
                int count = baselineCounts[baseline];
                for (int ordinal = 0; ordinal < count; ordinal++)
                {
                    int parent = baselineData[start + ordinal];
                    C.ChildIndex childIndex = C.DecodeChildIndex(childIndices[parent]);
                    var children = new C.ChildSource[childIndex.count];
                    for (int childOrdinal = 0; childOrdinal < childIndex.count; childOrdinal++)
                    {
                        int child = childData[childIndex.localStart + childOrdinal];
                        children[childOrdinal] = new C.ChildSource(
                            positions[child], localPositions[child], localRotations[child],
                            attributes[child]);
                    }
                    var parentSource = new C.ParentSource(
                        positions[parent], rotations[parent], negativeScaleDirection,
                        negativeScaleQuaternion, attributes[parent],
                        rotationalInterpolation, rootRotation);
                    Require(C.TryCalculateParentBurst(
                            variant, parentSource, children, out C.ParentValue value),
                        ownerPath + "/" + stateName + "/" + variant +
                        " parent calculation " + parent);
                    if (!value.hasChildren)
                    {
                        Require(childIndex.count == 0,
                            ownerPath + "/" + stateName + " empty-child marker " + parent);
                        continue;
                    }
                    Require(value.children.Length == childIndex.count,
                        ownerPath + "/" + stateName + " child result count " + parent);
                    rotations[parent] = value.rotation;
                    for (int childOrdinal = 0; childOrdinal < childIndex.count; childOrdinal++)
                    {
                        int child = childData[childIndex.localStart + childOrdinal];
                        // The native child write is gated by Flag_Move. Fixed
                        // children contribute their rest direction to the parent
                        // accumulator but retain their incoming rotation lane.
                        if ((attributes[child] & C.FlagMove) != 0)
                            rotations[child] = value.children[childOrdinal].rotation;
                    }
                }
            }
            for (int vertex = 0; vertex < rotations.Length; vertex++)
            {
                RequireFloat4Bits(rotations[vertex], expectedRotations[vertex],
                    ownerPath + "/" + stateName + "/" + variant + " vertex " + vertex);
                RequireDouble3(positionSnapshot[vertex], positions[vertex],
                    ownerPath + "/" + stateName + "/" + variant +
                    " positions remain immutable " + vertex);
            }
        }

        private static void VerifyCoverage(
            Dictionary<string, object> owner,
            string ownerPath,
            int vertices,
            int baselines,
            int baselineVisits,
            int roots,
            int leaves,
            int multiChildParents,
            int fixedVertices,
            int movableVertices)
        {
            Dictionary<string, object> coverage = JsonObject(
                JsonRequired(owner, "coverage", ownerPath), ownerPath + ".coverage");
            Require(JsonInteger(coverage, "vertexCount", ownerPath + ".coverage") == vertices,
                ownerPath + " vertex coverage");
            Require(JsonInteger(coverage, "baselineCount", ownerPath + ".coverage") == baselines,
                ownerPath + " baseline coverage");
            Require(JsonInteger(coverage, "baselineParentVisitCount", ownerPath + ".coverage") ==
                    baselineVisits, ownerPath + " baseline visit coverage");
            Require(JsonInteger(coverage, "rootCount", ownerPath + ".coverage") == roots,
                ownerPath + " root coverage");
            Require(JsonInteger(coverage, "leafCount", ownerPath + ".coverage") == leaves,
                ownerPath + " leaf coverage");
            Require(JsonInteger(coverage, "multiChildParentCount", ownerPath + ".coverage") ==
                    multiChildParents, ownerPath + " multi-child coverage");
            Require(JsonInteger(coverage, "fixedVertexCount", ownerPath + ".coverage") ==
                    fixedVertices, ownerPath + " fixed coverage");
            Require(JsonInteger(coverage, "movableVertexCount", ownerPath + ".coverage") ==
                    movableVertices, ownerPath + " movable coverage");
            Require(JsonInteger(coverage, "lineCount", ownerPath + ".coverage") >= 0,
                ownerPath + " line coverage");
        }

        private static void VerifyNativeMutationDeclaration(
            Dictionary<string, object> state,
            string label)
        {
            Dictionary<string, object> variants = JsonObject(
                JsonRequired(state, "nativeMutation", label), label + ".nativeMutation");
            foreach (string variant in new[] { "x64_sse2", "avx2" })
            {
                Dictionary<string, object> mutation = JsonObject(
                    JsonRequired(variants, variant, label + ".nativeMutation"),
                    label + ".nativeMutation." + variant);
                List<object> declared = JsonArray(
                    JsonRequired(mutation, "declaredMutableBuffers", label), label + ".declared");
                List<object> changed = JsonArray(
                    JsonRequired(mutation, "changedBuffers", label), label + ".changed");
                Require(declared.Count == 1 && (string)declared[0] == "rotations",
                    label + "/" + variant + " declared mutation");
                Require(changed.Count == 1 && (string)changed[0] == "rotations",
                    label + "/" + variant + " observed mutation");
                Require(JsonText(mutation, "immutableBeforeSha256", label) ==
                        JsonText(mutation, "immutableAfterSha256", label),
                    label + "/" + variant + " immutable aggregate");
                Require(JsonText(mutation, "rotationBeforeSha256", label) !=
                        JsonText(mutation, "rotationAfterSha256", label),
                    label + "/" + variant + " rotation mutation");
            }
        }

        private static Dictionary<string, object> JsonObject(object value, string label)
        {
            if (value is Dictionary<string, object> result)
                return result;
            throw new InvalidOperationException(label + " must be an object.");
        }

        private static List<object> JsonArray(object value, string label)
        {
            if (value is List<object> result)
                return result;
            throw new InvalidOperationException(label + " must be an array.");
        }

        private static object JsonRequired(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            if (row.TryGetValue(key, out object value))
                return value;
            throw new InvalidOperationException(label + " is missing " + key + ".");
        }

        private static string JsonText(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            object value = JsonRequired(row, key, label);
            if (value is string result)
                return result;
            throw new InvalidOperationException(label + "." + key + " must be text.");
        }

        private static int JsonInteger(
            Dictionary<string, object> row,
            string key,
            string label) => JsonInteger(JsonRequired(row, key, label), label + "." + key);

        private static int JsonInteger(object value, string label)
        {
            if (value is bool)
                throw new InvalidOperationException(label + " must be an integer.");
            try
            {
                double converted = Convert.ToDouble(value, CultureInfo.InvariantCulture);
                if (double.IsNaN(converted) || double.IsInfinity(converted) ||
                    converted != Math.Truncate(converted) ||
                    converted < int.MinValue || converted > int.MaxValue)
                    throw new InvalidOperationException(label + " must be a bounded integer.");
                return checked((int)converted);
            }
            catch (Exception exception) when (!(exception is InvalidOperationException))
            {
                throw new InvalidOperationException(label + " must be an integer.", exception);
            }
        }

        private static bool JsonBoolean(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            object value = JsonRequired(row, key, label);
            if (value is bool result)
                return result;
            throw new InvalidOperationException(label + "." + key + " must be boolean.");
        }

        private static byte[] ByteArray(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new byte[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = checked((byte)JsonInteger(values[index], label + "." + key));
            return result;
        }

        private static int[] IntArray(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new int[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = JsonInteger(values[index], label + "." + key);
            return result;
        }

        private static uint[] UIntArray(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new uint[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = checked((uint)JsonInteger(values[index], label + "." + key));
            return result;
        }

        private static ushort[] UShortArray(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new ushort[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = checked((ushort)JsonInteger(values[index], label + "." + key));
            return result;
        }

        private static K.Float3[] Float3Rows(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new K.Float3[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = Float3(JsonArray(values[index], label + "." + key + "[]"), label);
            return result;
        }

        private static K.Float4[] Float4Rows(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new K.Float4[values.Count];
            for (int index = 0; index < result.Length; index++)
                result[index] = Float4(JsonArray(values[index], label + "." + key + "[]"), label);
            return result;
        }

        private static K.Double3[] Double3Rows(
            Dictionary<string, object> row,
            string key,
            string label)
        {
            List<object> values = JsonArray(JsonRequired(row, key, label), label + "." + key);
            var result = new K.Double3[values.Count];
            for (int index = 0; index < result.Length; index++)
            {
                List<object> lanes = JsonArray(values[index], label + "." + key + "[]");
                Require(lanes.Count == 3, label + "." + key + " row width");
                result[index] = D(
                    ParseDoubleLe((string)lanes[0]),
                    ParseDoubleLe((string)lanes[1]),
                    ParseDoubleLe((string)lanes[2]));
            }
            return result;
        }

        private static K.Float3 Float3(List<object> lanes, string label)
        {
            Require(lanes.Count == 3, label + " float3 width");
            return F(
                ParseFloatLe((string)lanes[0]),
                ParseFloatLe((string)lanes[1]),
                ParseFloatLe((string)lanes[2]));
        }

        private static K.Float4 Float4(List<object> lanes, string label)
        {
            Require(lanes.Count == 4, label + " float4 width");
            return Q(
                ParseFloatLe((string)lanes[0]),
                ParseFloatLe((string)lanes[1]),
                ParseFloatLe((string)lanes[2]),
                ParseFloatLe((string)lanes[3]));
        }

        private static float ParseFloatLe(string hex)
        {
            byte[] bytes = ParseLittleEndianHex(hex, 4);
            int bits = bytes[0] | bytes[1] << 8 | bytes[2] << 16 | bytes[3] << 24;
            return BitConverter.Int32BitsToSingle(bits);
        }

        private static double ParseDoubleLe(string hex)
        {
            byte[] bytes = ParseLittleEndianHex(hex, 8);
            ulong bits = 0;
            for (int index = 0; index < bytes.Length; index++)
                bits |= (ulong)bytes[index] << (index * 8);
            return BitConverter.Int64BitsToDouble(unchecked((long)bits));
        }

        private static byte[] ParseLittleEndianHex(string hex, int byteCount)
        {
            if (hex == null || hex.Length != byteCount * 2)
                throw new InvalidOperationException("Invalid little-endian scalar bit string.");
            var bytes = new byte[byteCount];
            for (int index = 0; index < byteCount; index++)
            {
                if (!byte.TryParse(hex.Substring(index * 2, 2), NumberStyles.HexNumber,
                        CultureInfo.InvariantCulture, out bytes[index]))
                    throw new InvalidOperationException("Invalid little-endian scalar bit string.");
            }
            return bytes;
        }

        private static void VerifyLiveRouteAdmissionFailsClosed()
        {
            Require(!R.TrySelect(default, out R.ExecutionRoute missing) &&
                    missing == R.ExecutionRoute.Unselected,
                "missing live observation must remain unselected");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, true, true, 1, "unknown", 0, false, null), out _),
                "unknown Burst CPU route must fail closed");
            Require(R.TrySelect(new R.Observation(
                    true, 1, true, true, 1, "x64_sse2", 0, false, null),
                    out R.ExecutionRoute sse) &&
                    sse == R.ExecutionRoute.BurstX64Sse2,
                "validated SSE2 route admission");
            Require(R.TrySelect(new R.Observation(
                    true, 1, true, true, 1, "avx2", 0, false, null),
                    out R.ExecutionRoute avx) &&
                    avx == R.ExecutionRoute.BurstAvx2,
                "validated AVX2 route admission");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, false, false, 0, null, 1, true,
                    "direct_call_fallback"), out _),
                "patched managed FromToRotation must fail closed");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, false, false, 0, null, 1, false,
                    "managed_worker"), out _),
                "unselected managed worker must fail closed");
            Require(R.TrySelect(new R.Observation(
                    true, 1, false, false, 0, null, 1, false,
                    "direct_call_fallback"), out R.ExecutionRoute managed) &&
                    managed == R.ExecutionRoute.ManagedUnpatched,
                "validated unpatched direct-call fallback admission");
            Require(!R.TrySelect(new R.Observation(
                    true, 2, true, true, 1, "x64_sse2", 0, false, null), out _),
                "conflicting Burst gate observations must fail closed");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, true, true, 2, "x64_sse2", 0, false, null), out _),
                "multiple CPU selection observations must fail closed");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, false, false, 0, null, 2, false,
                    "direct_call_fallback"), out _),
                "conflicting IFix observations must fail closed");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, true, true, 1, "x64_sse2", 1, false,
                    "direct_call_fallback"), out _),
                "simultaneous Burst and managed-route evidence must fail closed");
            Require(!R.TrySelect(new R.Observation(
                    true, 1, false, true, 1, "avx2", 1, false,
                    "direct_call_fallback"), out _),
                "managed fallback with CPU-route evidence must fail closed");

            C.ParentSource parent = IdentityParent();
            Require(!R.TryCalculateParent(
                    R.ExecutionRoute.Unselected, parent, Array.Empty<C.ChildSource>(), out _),
                "unselected route must not execute CalcLine");
        }

        private static C.ParentSource IdentityParent()
        {
            return new C.ParentSource(
                D(0.0, 0.0, 0.0),
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                F(1.0f, 1.0f, 1.0f),
                Q(1.0f, 1.0f, 1.0f, 1.0f),
                C.FlagMove,
                1.0,
                1.0);
        }

        private static C.ChildSource Child(K.Double3 position, K.Float3 local, byte attribute)
        {
            return new C.ChildSource(
                position,
                local,
                Q(0.0f, 0.0f, 0.0f, 1.0f),
                attribute);
        }

        private static K.Double3 D(double x, double y, double z) => new K.Double3(x, y, z);
        private static K.Float3 F(float x, float y, float z) => new K.Float3(x, y, z);
        private static K.Float4 Q(float x, float y, float z, float w) => new K.Float4(x, y, z, w);
        private static K.Float3 FB(uint x, uint y, uint z) =>
            new K.Float3(Single(x), Single(y), Single(z));
        private static K.Float4 QB(uint x, uint y, uint z, uint w) =>
            new K.Float4(Single(x), Single(y), Single(z), Single(w));
        private static float Single(uint bits) =>
            BitConverter.Int32BitsToSingle(unchecked((int)bits));

        private static void RequireDouble3(K.Double3 actual, K.Double3 expected, string label)
        {
            Require(BitConverter.DoubleToInt64Bits(actual.x) == BitConverter.DoubleToInt64Bits(expected.x) &&
                    BitConverter.DoubleToInt64Bits(actual.y) == BitConverter.DoubleToInt64Bits(expected.y) &&
                    BitConverter.DoubleToInt64Bits(actual.z) == BitConverter.DoubleToInt64Bits(expected.z),
                label + " expected (" + expected.x + "," + expected.y + "," + expected.z +
                ") but got (" + actual.x + "," + actual.y + "," + actual.z + ")");
        }

        private static void RequireQuaternionBits(
            K.Float4 actual,
            uint x,
            uint y,
            uint z,
            uint w,
            string label)
        {
            RequireFloatBits(actual.x, x, label + " x");
            RequireFloatBits(actual.y, y, label + " y");
            RequireFloatBits(actual.z, z, label + " z");
            RequireFloatBits(actual.w, w, label + " w");
        }

        private static void RequireFloat4Bits(K.Float4 actual, K.Float4 expected, string label)
        {
            RequireFloatBits(actual.x,
                unchecked((uint)BitConverter.SingleToInt32Bits(expected.x)), label + " x");
            RequireFloatBits(actual.y,
                unchecked((uint)BitConverter.SingleToInt32Bits(expected.y)), label + " y");
            RequireFloatBits(actual.z,
                unchecked((uint)BitConverter.SingleToInt32Bits(expected.z)), label + " z");
            RequireFloatBits(actual.w,
                unchecked((uint)BitConverter.SingleToInt32Bits(expected.w)), label + " w");
        }

        private static void RequireFloat3Bits(
            K.Float3 actual,
            uint x,
            uint y,
            uint z,
            string label)
        {
            RequireFloatBits(actual.x, x, label + " x");
            RequireFloatBits(actual.y, y, label + " y");
            RequireFloatBits(actual.z, z, label + " z");
        }

        private static void RequireFloatBits(float actual, uint expected, string label)
        {
            uint actualBits = unchecked((uint)BitConverter.SingleToInt32Bits(actual));
            Require(
                actualBits == expected,
                label + " expected 0x" + expected.ToString("x8") +
                " but got 0x" + actualBits.ToString("x8"));
        }

        private static void Require(bool condition, string message)
        {
            if (!condition)
                throw new InvalidOperationException(message);
        }
    }
}
