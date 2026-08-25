using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Linq;
using System.Security.Cryptography;
using System.Text;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    internal static class EndfieldSecondaryDynamicsBindingBuilder
    {
        private const string EndminfPrefabPath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Prefabs/Endminf.prefab";
        private const string SolverInputsPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_solver_inputs.json";
        private const string PayloadDecodePath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "secondary_dynamics_payload_decode.json";

        internal static void Configure(
            GameObject actor,
            string actorName,
            string actorGeneratedRoot,
            bool persist = true)
        {
            if (actor == null ||
                !string.Equals(actorName, "Endminf", StringComparison.OrdinalIgnoreCase))
                return;

            TextAsset solverInputs = AssetDatabase.LoadAssetAtPath<TextAsset>(SolverInputsPath);
            TextAsset payloadDecode = AssetDatabase.LoadAssetAtPath<TextAsset>(PayloadDecodePath);
            if (solverInputs == null || payloadDecode == null)
                throw new FileNotFoundException(
                    "Endminf secondary-dynamics source contracts are missing.");

            Dictionary<string, object> solverActor = ActorRow(solverInputs.text, "endminf");
            Dictionary<string, object> payloadActor = ActorRow(payloadDecode.text, "endminf");
            List<object> solverCloths = Array(solverActor, "cloths");
            List<object> payloadCloths = Array(payloadActor, "cloths");
            if (solverCloths.Count != 4 || payloadCloths.Count != 4)
                throw new InvalidDataException("Endminf must contain exactly four cloth owners.");

            var solverByOwner = solverCloths
                .Select((value, index) => Object(value, "solver cloth " + index))
                .ToDictionary(row => Text(row, "game_object_path"), StringComparer.Ordinal);
            var owners = new List<EndfieldSecondaryDynamicsData.Owner>();
            foreach (object value in payloadCloths)
            {
                Dictionary<string, object> cloth = Object(value, "payload cloth");
                string ownerPath = Text(cloth, "game_object_path");
                if (!solverByOwner.TryGetValue(ownerPath, out Dictionary<string, object> solverCloth))
                    throw new InvalidDataException("No solver-input cloth matches " + ownerPath + ".");

                Dictionary<string, object> transformArray = Object(
                    Required(cloth, "transform_array"), ownerPath + ".transform_array");
                string[] paths = Array(transformArray, "entries")
                    .Select((entry, index) => Text(
                        Object(entry, ownerPath + ".transform_array[" + index + "]"),
                        "hierarchy_path"))
                    .ToArray();
                if (paths.Length < 2 || !string.Equals(paths[paths.Length - 1], ownerPath,
                        StringComparison.Ordinal))
                    throw new InvalidDataException(
                        ownerPath + " transform array must end with its center transform.");

                Dictionary<string, object> arrays = Object(
                    Required(cloth, "proxy_mesh_arrays"), ownerPath + ".proxy_mesh_arrays");
                int vertexCount = Count(Object(
                    Required(arrays, "referenceIndices"), ownerPath + ".referenceIndices"));
                int[] referenceIndices = IntArray(arrays, "referenceIndices", ownerPath);
                byte[] attributes = ByteArray(arrays, "attributes", ownerPath);
                float[] vertexDepths = FloatArray(arrays, "vertexDepths", ownerPath);
                int[] rootIndices = IntArray(arrays, "vertexRootIndices", ownerPath);
                int[] parentIndices = IntArray(arrays, "vertexParentIndices", ownerPath);
                Vector3[] localPositions = Vector3Array(arrays, "vertexLocalPositions", ownerPath);
                Quaternion[] localRotations = QuaternionArray(
                    arrays, "vertexLocalRotations", ownerPath);
                Quaternion[] vertexToTransformRotations = QuaternionArray(
                    arrays, "vertexToTransformRotations", ownerPath);
                byte[] baseLineFlags = ByteArray(arrays, "baseLineFlags", ownerPath);
                ushort[] baseLineStarts = UShortArray(
                    arrays, "baseLineStartDataIndices", ownerPath);
                ushort[] baseLineCounts = UShortArray(arrays, "baseLineDataCounts", ownerPath);
                ushort[] baseLineData = UShortArray(arrays, "baseLineData", ownerPath);
                ushort[] centerFixedList = UShortArray(arrays, "centerFixedList", ownerPath);

                ValidateVertexArrays(
                    ownerPath,
                    vertexCount,
                    paths.Length - 1,
                    referenceIndices,
                    attributes,
                    vertexDepths,
                    rootIndices,
                    parentIndices,
                    localPositions,
                    localRotations,
                    vertexToTransformRotations);
                ValidateBaselines(
                    ownerPath,
                    vertexCount,
                    baseLineFlags,
                    baseLineStarts,
                    baseLineCounts,
                    baseLineData,
                    centerFixedList);

                Dictionary<string, object> solverInput = Object(
                    Required(solverCloth, "solver_input"), ownerPath + ".solver_input");
                Dictionary<string, object> prebuildData = Object(
                    Required(solverInput, "prebuild_data"), ownerPath + ".prebuild_data");
                Dictionary<string, object> preBuildData = Object(
                    Required(prebuildData, "preBuildData"), ownerPath + ".preBuildData");
                Dictionary<string, object> distanceData = Object(
                    Required(preBuildData, "distanceConstraintData"),
                    ownerPath + ".distanceConstraintData");
                int[] distanceIndices = DirectIntArray(
                    distanceData, "indexArray", ownerPath + ".distanceConstraintData");
                ushort[] distanceParticles = DirectUShortArray(
                    distanceData, "dataArray", ownerPath + ".distanceConstraintData");
                float[] distanceRestLengths = DirectFloatArray(
                    distanceData, "distanceArray", ownerPath + ".distanceConstraintData");
                ValidateDistanceConstraints(
                    ownerPath,
                    vertexCount,
                    distanceIndices,
                    distanceParticles,
                    distanceRestLengths);

                owners.Add(new EndfieldSecondaryDynamicsData.Owner
                {
                    ownerPath = ownerPath,
                    centerTransformPath = paths[paths.Length - 1],
                    proxyTransformPaths = paths.Take(paths.Length - 1).ToArray(),
                    selectionSampleCount = Count(Object(
                        Required(cloth, "selection_data"), ownerPath + ".selection_data")),
                    proxyVertexCount = vertexCount,
                    lineCount = Count(Object(Required(arrays, "lines"), ownerPath + ".lines")),
                    baselineCount = Count(Object(
                        Required(arrays, "baseLineFlags"), ownerPath + ".baseLineFlags")),
                    centerFixedCount = Count(Object(
                        Required(arrays, "centerFixedList"), ownerPath + ".centerFixedList")),
                    colliderCount = Array(solverCloth, "collider_references").Count,
                    referenceIndices = referenceIndices,
                    attributes = attributes,
                    vertexDepths = vertexDepths,
                    vertexRootIndices = rootIndices,
                    vertexParentIndices = parentIndices,
                    vertexLocalPositions = localPositions,
                    vertexLocalRotations = localRotations,
                    vertexToTransformRotations = vertexToTransformRotations,
                    baseLineFlags = baseLineFlags,
                    baseLineStartDataIndices = baseLineStarts,
                    baseLineDataCounts = baseLineCounts,
                    baseLineData = baseLineData,
                    centerFixedList = centerFixedList,
                    distanceConstraintIndexArray = distanceIndices,
                    distanceConstraintDataArray = distanceParticles,
                    distanceConstraintRestLengths = distanceRestLengths,
                    solverInputs = DecodeSolverInputs(solverInput, ownerPath),
                });
            }

            int bindingCount = owners.Sum(owner => owner.proxyTransformPaths.Length);
            int uniqueCount = owners
                .SelectMany(owner => owner.proxyTransformPaths)
                .Distinct(StringComparer.Ordinal)
                .Count();
            if (bindingCount != 126 || uniqueCount != 100 || bindingCount - uniqueCount != 26)
                throw new InvalidDataException(
                    "Endminf secondary-dynamics binding overlap contract drifted.");
            if (!persist)
                return;

            string directory = actorGeneratedRoot + "/SecondaryDynamics";
            EnsureAssetFolder(directory);
            string assetPath = directory + "/EndminfSecondaryDynamicsData.asset";
            EndfieldSecondaryDynamicsData data =
                AssetDatabase.LoadAssetAtPath<EndfieldSecondaryDynamicsData>(assetPath);
            if (data == null)
            {
                data = ScriptableObject.CreateInstance<EndfieldSecondaryDynamicsData>();
                AssetDatabase.CreateAsset(data, assetPath);
            }
            data.sourceRecovered = true;
            data.actorKey = "endminf";
            data.solverInputs = solverInputs;
            data.solverInputsSha256 = Sha256(SolverInputsPath);
            data.payloadDecode = payloadDecode;
            data.payloadDecodeSha256 = Sha256(PayloadDecodePath);
            data.owners = owners.ToArray();
            data.expectedBindingCount = bindingCount;
            data.expectedUniqueBindingCount = uniqueCount;
            data.expectedOverlappingBindingCount = bindingCount - uniqueCount;
            EditorUtility.SetDirty(data);

            EndfieldSecondaryDynamicsRuntime runtime =
                actor.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            if (runtime == null)
                runtime = actor.AddComponent<EndfieldSecondaryDynamicsRuntime>();
            runtime.data = data;
            EditorUtility.SetDirty(runtime);
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Endminf Secondary Dynamics Source Data")]
        public static void VerifyEndminfSourceDataLayer()
        {
            GameObject probe = new GameObject("EndminfSecondaryDynamicsSourceProbe");
            try
            {
                Configure(probe, "Endminf", string.Empty, false);
                Debug.Log(
                    "Verified Endminf secondary-dynamics source data: exact topology, " +
                    "distance constraints, and authored solver scalars are well-formed; " +
                    "no asset or runtime writeback was created.");
            }
            finally
            {
                UnityEngine.Object.DestroyImmediate(probe);
            }
        }

        [MenuItem("Endfield/Character Recovery Lab/Verify Endminf Secondary Dynamics Binding")]
        public static void VerifyGeneratedEndminfBinding()
        {
            GameObject prefab = AssetDatabase.LoadAssetAtPath<GameObject>(EndminfPrefabPath);
            if (prefab == null)
                throw new FileNotFoundException("Generated Endminf prefab is missing.", EndminfPrefabPath);
            EndfieldSecondaryDynamicsRuntime runtime =
                prefab.GetComponent<EndfieldSecondaryDynamicsRuntime>();
            if (runtime == null || runtime.data == null || runtime.SolverWritebackEnabled)
                throw new InvalidDataException(
                    "Generated Endminf secondary-dynamics coordinator is missing or not fail-closed.");
            EndfieldSecondaryDynamicsOwnerContract.BindingAudit audit =
                EndfieldSecondaryDynamicsOwnerContract.Verify(prefab, "Endminf", SolverInputsPath);
            if (!audit.owner_binding_verified ||
                audit.proxy_bindings_expected != 126 ||
                audit.unique_proxy_bindings != 100 ||
                audit.overlapping_proxy_bindings != 26 ||
                !audit.actor_runtime_coordinator_observed ||
                audit.solver_writeback_enabled)
            {
                throw new InvalidDataException(
                    "Generated Endminf secondary-dynamics binding audit differs.");
            }
            Debug.Log(
                "Verified Endminf secondary dynamics: 4 owners, 126 bindings, " +
                "100 unique transforms, 26 overlaps, solver writeback fail-closed.");
        }

        private static Dictionary<string, object> ActorRow(string json, string actorKey)
        {
            Dictionary<string, object> root = Object(
                ManifestMiniJson.Deserialize(json), "contract root");
            Dictionary<string, object> actors = Object(Required(root, "actors"), "actors");
            if (!actors.TryGetValue(actorKey, out object value))
                throw new InvalidDataException("Contract has no actor key " + actorKey + ".");
            return Object(value, "actors." + actorKey);
        }

        private static int Count(Dictionary<string, object> value) =>
            Convert.ToInt32(Required(value, "count"), CultureInfo.InvariantCulture);

        private static object Required(Dictionary<string, object> row, string key)
        {
            if (!row.TryGetValue(key, out object value) || value == null)
                throw new InvalidDataException("Secondary-dynamics contract lacks '" + key + "'.");
            return value;
        }

        private static Dictionary<string, object> Object(object value, string context) =>
            value as Dictionary<string, object> ??
            throw new InvalidDataException("Expected object at " + context + ".");

        private static List<object> Array(Dictionary<string, object> row, string key) =>
            Required(row, key) as List<object> ??
            throw new InvalidDataException("Expected array at " + key + ".");

        private static string Text(Dictionary<string, object> row, string key)
        {
            string text = Convert.ToString(Required(row, key), CultureInfo.InvariantCulture) ?? "";
            if (string.IsNullOrWhiteSpace(text))
                throw new InvalidDataException("Empty text field '" + key + "'.");
            return text;
        }

        private static EndfieldSecondaryDynamicsData.SolverInputs DecodeSolverInputs(
            Dictionary<string, object> solverInput,
            string ownerPath)
        {
            Dictionary<string, object> parameters = Object(
                Required(solverInput, "parameters"), ownerPath + ".parameters");
            Dictionary<string, object> constraints = Object(
                Required(solverInput, "constraints"), ownerPath + ".constraints");
            Dictionary<string, object> damping = Child(constraints, "damping", ownerPath);
            Dictionary<string, object> radius = Child(constraints, "radius", ownerPath);
            Dictionary<string, object> inertia = Child(
                constraints, "inertiaConstraint", ownerPath);
            Dictionary<string, object> particleSpeed = Child(
                inertia, "particleSpeedLimit", ownerPath + ".inertiaConstraint");
            Dictionary<string, object> tether = Child(
                constraints, "tetherConstraint", ownerPath);
            Dictionary<string, object> distance = Child(
                constraints, "distanceConstraint", ownerPath);
            Dictionary<string, object> distanceStiffness = Child(
                distance, "stiffness", ownerPath + ".distanceConstraint");
            Dictionary<string, object> restoration = Child(
                constraints, "angleRestorationConstraint", ownerPath);
            Dictionary<string, object> restorationStiffness = Child(
                restoration, "stiffness", ownerPath + ".angleRestorationConstraint");
            Dictionary<string, object> limit = Child(
                constraints, "angleLimitConstraint", ownerPath);
            Dictionary<string, object> limitAngle = Child(
                limit, "limitAngle", ownerPath + ".angleLimitConstraint");
            Dictionary<string, object> collision = Child(
                constraints, "colliderCollisionConstraint", ownerPath);
            Dictionary<string, object> spring = Child(
                constraints, "springConstraint", ownerPath);

            return new EndfieldSecondaryDynamicsData.SolverInputs
            {
                authoredScalarsRecovered = true,
                compiledCurveSamplesRecovered = false,
                compiledCurveSamplesBoundary =
                    "The source contracts preserve authored value/useCurve/keyframes, but do " +
                    "not contain the compiled ClothParameters 16-float curve buffers.",
                normalAxis = Integer(parameters, "normalAxis", ownerPath),
                gravity = Float(parameters, "gravity", ownerPath),
                gravityDirection = Vector3Value(
                    Child(parameters, "gravityDirection", ownerPath),
                    ownerPath + ".gravityDirection"),
                gravityFalloff = Float(parameters, "gravityFalloff", ownerPath),
                animationPoseRatio = Float(parameters, "animationPoseRatio", ownerPath),
                dampingValue = Float(damping, "value", ownerPath),
                dampingUsesCurve = Toggle(damping, "useCurve", ownerPath),
                radiusValue = Float(radius, "value", ownerPath),
                radiusUsesCurve = Toggle(radius, "useCurve", ownerPath),
                inertiaDepth = Float(inertia, "depthInertia", ownerPath),
                particleSpeedLimitEnabled = Toggle(particleSpeed, "use", ownerPath),
                particleSpeedLimit = Float(particleSpeed, "value", ownerPath),
                centrifugalAcceleration = Float(
                    inertia, "centrifualAcceleration", ownerPath),
                tetherDistanceCompression = Float(
                    tether, "distanceCompression", ownerPath),
                distanceStiffnessValue = Float(
                    distanceStiffness, "value", ownerPath),
                distanceStiffnessUsesCurve = Toggle(
                    distanceStiffness, "useCurve", ownerPath),
                angleRestorationEnabled = Toggle(
                    restoration, "useAngleRestoration", ownerPath),
                angleRestorationStiffnessValue = Float(
                    restorationStiffness, "value", ownerPath),
                angleRestorationStiffnessUsesCurve = Toggle(
                    restorationStiffness, "useCurve", ownerPath),
                angleRestorationVelocityAttenuation = Float(
                    restoration, "velocityAttenuation", ownerPath),
                angleRestorationGravityFalloff = Float(
                    restoration, "gravityFalloff", ownerPath),
                angleLimitEnabled = Toggle(limit, "useAngleLimit", ownerPath),
                angleLimitValue = Float(limitAngle, "value", ownerPath),
                angleLimitUsesCurve = Toggle(limitAngle, "useCurve", ownerPath),
                angleLimitStiffness = Float(limit, "stiffness", ownerPath),
                colliderDynamicFriction = Float(collision, "friction", ownerPath),
                springEnabled = Toggle(spring, "useSpring", ownerPath),
                springPower = Float(spring, "springPower", ownerPath),
                springLimitDistance = Float(spring, "limitDistance", ownerPath),
                springNormalLimitRatio = Float(spring, "normalLimitRatio", ownerPath),
                springNoise = Float(spring, "springNoise", ownerPath),
            };
        }

        private static void ValidateVertexArrays(
            string ownerPath,
            int vertexCount,
            int proxyTransformCount,
            int[] referenceIndices,
            byte[] attributes,
            float[] depths,
            int[] rootIndices,
            int[] parentIndices,
            Vector3[] localPositions,
            Quaternion[] localRotations,
            Quaternion[] vertexToTransformRotations)
        {
            var cardinalities = new Dictionary<string, int>
            {
                { "referenceIndices", referenceIndices.Length },
                { "attributes", attributes.Length },
                { "vertexDepths", depths.Length },
                { "vertexRootIndices", rootIndices.Length },
                { "vertexParentIndices", parentIndices.Length },
                { "vertexLocalPositions", localPositions.Length },
                { "vertexLocalRotations", localRotations.Length },
                { "vertexToTransformRotations", vertexToTransformRotations.Length },
            };
            foreach (KeyValuePair<string, int> pair in cardinalities)
            {
                if (pair.Value != vertexCount)
                    throw new InvalidDataException(
                        ownerPath + "." + pair.Key + " count " + pair.Value +
                        " differs from proxy vertex count " + vertexCount + ".");
            }
            for (int index = 0; index < vertexCount; index++)
            {
                if (referenceIndices[index] < 0 || referenceIndices[index] >= proxyTransformCount)
                    throw new InvalidDataException(
                        ownerPath + ".referenceIndices[" + index + "] is out of range.");
                ValidateOptionalVertexIndex(ownerPath, "vertexRootIndices", index,
                    rootIndices[index], vertexCount);
                ValidateOptionalVertexIndex(ownerPath, "vertexParentIndices", index,
                    parentIndices[index], vertexCount);
                if (float.IsNaN(depths[index]) || float.IsInfinity(depths[index]))
                    throw new InvalidDataException(
                        ownerPath + ".vertexDepths[" + index + "] is not finite.");
            }
        }

        private static void ValidateOptionalVertexIndex(
            string ownerPath,
            string field,
            int element,
            int value,
            int vertexCount)
        {
            if (value < -1 || value >= vertexCount)
                throw new InvalidDataException(
                    ownerPath + "." + field + "[" + element + "] is out of range.");
        }

        private static void ValidateBaselines(
            string ownerPath,
            int vertexCount,
            byte[] flags,
            ushort[] starts,
            ushort[] counts,
            ushort[] data,
            ushort[] centerFixed)
        {
            if (flags.Length != starts.Length || flags.Length != counts.Length)
                throw new InvalidDataException(
                    ownerPath + " baseline flag/start/count cardinalities differ.");
            for (int baseline = 0; baseline < flags.Length; baseline++)
            {
                int end = starts[baseline] + counts[baseline];
                if (end > data.Length)
                    throw new InvalidDataException(
                        ownerPath + ".baseLineData slice " + baseline + " exceeds data.");
            }
            ValidateVertexList(ownerPath, "baseLineData", data, vertexCount);
            ValidateVertexList(ownerPath, "centerFixedList", centerFixed, vertexCount);
        }

        private static void ValidateDistanceConstraints(
            string ownerPath,
            int vertexCount,
            int[] packedIndices,
            ushort[] particles,
            float[] restLengths)
        {
            if (packedIndices.Length != vertexCount)
                throw new InvalidDataException(
                    ownerPath + " distance index count differs from proxy vertex count.");
            if (particles.Length != restLengths.Length)
                throw new InvalidDataException(
                    ownerPath + " distance particle/rest-length cardinalities differ.");
            for (int vertex = 0; vertex < packedIndices.Length; vertex++)
            {
                int start = packedIndices[vertex] & 0x000fffff;
                int count = (int)((uint)packedIndices[vertex] >> 20);
                if (start + count > particles.Length)
                    throw new InvalidDataException(
                        ownerPath + ".distanceConstraintIndexArray[" + vertex +
                        "] exceeds flattened data.");
            }
            ValidateVertexList(ownerPath, "distanceConstraintDataArray", particles, vertexCount);
            for (int index = 0; index < restLengths.Length; index++)
            {
                if (float.IsNaN(restLengths[index]) || float.IsInfinity(restLengths[index]) ||
                    restLengths[index] < 0.0f)
                    throw new InvalidDataException(
                        ownerPath + ".distanceConstraintRestLengths[" + index +
                        "] is malformed.");
            }
        }

        private static void ValidateVertexList(
            string ownerPath,
            string field,
            ushort[] values,
            int vertexCount)
        {
            for (int index = 0; index < values.Length; index++)
            {
                if (values[index] >= vertexCount)
                    throw new InvalidDataException(
                        ownerPath + "." + field + "[" + index + "] is out of range.");
            }
        }

        private static int[] IntArray(
            Dictionary<string, object> arrays, string key, string ownerPath) =>
            DirectIntArray(ArrayRecord(arrays, key, ownerPath), "values", ownerPath + "." + key,
                Count(ArrayRecord(arrays, key, ownerPath)));

        private static byte[] ByteArray(
            Dictionary<string, object> arrays, string key, string ownerPath)
        {
            int[] values = IntArray(arrays, key, ownerPath);
            return values.Select((value, index) =>
            {
                if (value < byte.MinValue || value > byte.MaxValue)
                    throw new InvalidDataException(
                        ownerPath + "." + key + "[" + index + "] is not a byte.");
                return (byte)value;
            }).ToArray();
        }

        private static ushort[] UShortArray(
            Dictionary<string, object> arrays, string key, string ownerPath)
        {
            int[] values = IntArray(arrays, key, ownerPath);
            return ToUShort(values, ownerPath + "." + key);
        }

        private static float[] FloatArray(
            Dictionary<string, object> arrays, string key, string ownerPath)
        {
            Dictionary<string, object> record = ArrayRecord(arrays, key, ownerPath);
            return DirectFloatArray(record, "values", ownerPath + "." + key, Count(record));
        }

        private static Vector3[] Vector3Array(
            Dictionary<string, object> arrays, string key, string ownerPath)
        {
            Dictionary<string, object> record = ArrayRecord(arrays, key, ownerPath);
            List<object> values = DirectArray(record, "values", ownerPath + "." + key);
            RequireCount(values.Count, Count(record), ownerPath + "." + key);
            return values.Select((value, index) => Vector3Value(
                value, ownerPath + "." + key + "[" + index + "]")).ToArray();
        }

        private static Quaternion[] QuaternionArray(
            Dictionary<string, object> arrays, string key, string ownerPath)
        {
            Dictionary<string, object> record = ArrayRecord(arrays, key, ownerPath);
            List<object> values = DirectArray(record, "values", ownerPath + "." + key);
            RequireCount(values.Count, Count(record), ownerPath + "." + key);
            return values.Select((value, index) => QuaternionValue(
                value, ownerPath + "." + key + "[" + index + "]")).ToArray();
        }

        private static Dictionary<string, object> ArrayRecord(
            Dictionary<string, object> arrays, string key, string ownerPath) =>
            Object(Required(arrays, key), ownerPath + "." + key);

        private static Vector3 Vector3Value(Dictionary<string, object> record, string context)
        {
            if (record.TryGetValue("value", out object packed))
            {
                List<object> values = packed as List<object> ??
                    throw new InvalidDataException("Expected vector array at " + context + ".");
                RequireCount(values.Count, 3, context);
                return new Vector3(Number(values[0], context), Number(values[1], context),
                    Number(values[2], context));
            }
            return new Vector3(Float(record, "x", context), Float(record, "y", context),
                Float(record, "z", context));
        }

        private static Vector3 Vector3Value(object value, string context)
        {
            if (value is Dictionary<string, object> record)
                return Vector3Value(record, context);
            List<object> values = value as List<object> ??
                throw new InvalidDataException("Expected vector array at " + context + ".");
            RequireCount(values.Count, 3, context);
            return new Vector3(Number(values[0], context), Number(values[1], context),
                Number(values[2], context));
        }

        private static Quaternion QuaternionValue(object value, string context)
        {
            List<object> values;
            if (value is Dictionary<string, object> record)
            {
                values = Required(record, "value") as List<object> ??
                    throw new InvalidDataException("Expected quaternion array at " + context + ".");
            }
            else
            {
                values = value as List<object> ??
                    throw new InvalidDataException("Expected quaternion array at " + context + ".");
            }
            RequireCount(values.Count, 4, context);
            return new Quaternion(Number(values[0], context), Number(values[1], context),
                Number(values[2], context), Number(values[3], context));
        }

        private static int[] DirectIntArray(
            Dictionary<string, object> row,
            string key,
            string context,
            int expectedCount = -1)
        {
            List<object> values = DirectArray(row, key, context);
            if (expectedCount >= 0)
                RequireCount(values.Count, expectedCount, context);
            return values.Select((value, index) => CheckedInteger(
                value, context + "[" + index + "]")).ToArray();
        }

        private static ushort[] DirectUShortArray(
            Dictionary<string, object> row, string key, string context) =>
            ToUShort(DirectIntArray(row, key, context), context + "." + key);

        private static float[] DirectFloatArray(
            Dictionary<string, object> row,
            string key,
            string context,
            int expectedCount = -1)
        {
            List<object> values = DirectArray(row, key, context);
            if (expectedCount >= 0)
                RequireCount(values.Count, expectedCount, context);
            return values.Select((value, index) => Number(
                value, context + "[" + index + "]")).ToArray();
        }

        private static ushort[] ToUShort(int[] values, string context) =>
            values.Select((value, index) =>
            {
                if (value < ushort.MinValue || value > ushort.MaxValue)
                    throw new InvalidDataException(
                        context + "[" + index + "] is not an unsigned 16-bit value.");
                return (ushort)value;
            }).ToArray();

        private static List<object> DirectArray(
            Dictionary<string, object> row, string key, string context) =>
            Required(row, key) as List<object> ??
            throw new InvalidDataException("Expected array at " + context + "." + key + ".");

        private static Dictionary<string, object> Child(
            Dictionary<string, object> row, string key, string context) =>
            Object(Required(row, key), context + "." + key);

        private static bool Toggle(Dictionary<string, object> row, string key, string context)
        {
            int value = Integer(row, key, context);
            if (value != 0 && value != 1)
                throw new InvalidDataException(context + "." + key + " is not a toggle.");
            return value != 0;
        }

        private static int Integer(Dictionary<string, object> row, string key, string context) =>
            CheckedInteger(Required(row, key), context + "." + key);

        private static int CheckedInteger(object value, string context)
        {
            double number = Convert.ToDouble(value, CultureInfo.InvariantCulture);
            if (double.IsNaN(number) || double.IsInfinity(number) || number != Math.Truncate(number) ||
                number < int.MinValue || number > int.MaxValue)
                throw new InvalidDataException("Expected 32-bit integer at " + context + ".");
            return (int)number;
        }

        private static float Float(Dictionary<string, object> row, string key, string context) =>
            Number(Required(row, key), context + "." + key);

        private static float Number(object value, string context)
        {
            float number = Convert.ToSingle(value, CultureInfo.InvariantCulture);
            if (float.IsNaN(number) || float.IsInfinity(number))
                throw new InvalidDataException("Expected finite float at " + context + ".");
            return number;
        }

        private static void RequireCount(int actual, int expected, string context)
        {
            if (actual != expected)
                throw new InvalidDataException(
                    context + " count " + actual + " differs from declared count " + expected + ".");
        }

        private static string Sha256(string assetPath)
        {
            string absolute = Path.GetFullPath(Path.Combine(
                Application.dataPath, "..", assetPath));
            using (SHA256 sha = SHA256.Create())
                return string.Concat(sha.ComputeHash(File.ReadAllBytes(absolute))
                    .Select(value => value.ToString("x2")));
        }

        private static void EnsureAssetFolder(string assetPath)
        {
            string current = "Assets";
            foreach (string segment in assetPath.Split('/').Skip(1))
            {
                string next = current + "/" + segment;
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segment);
                current = next;
            }
        }
    }
}
