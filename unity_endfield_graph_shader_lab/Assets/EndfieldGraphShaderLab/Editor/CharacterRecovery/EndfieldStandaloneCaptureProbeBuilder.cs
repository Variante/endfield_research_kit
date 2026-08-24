using System;
using System.Collections.Generic;
using System.IO;
using EndfieldGraphShaderLab;
using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.Rendering;
using UnityEngine.SceneManagement;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Builds disposable standalone-player probes from a copy of the fast scene.
    /// The authoritative fast scene and generated actor prefabs are never saved by this tool.
    /// </summary>
    public static class EndfieldStandaloneCaptureProbeBuilder
    {
        private const string FastScenePath =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Scenes/CharacterRenderStyleFast.unity";
        private const string WulfaMaterialFolder =
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Wulfa/Materials";
        private const string GeneratedProbeRoot =
            "Assets/EndfieldGraphShaderLab/Generated/Diagnostics/StandaloneCaptureProbe";
        private const string ProbeModeArgument = "-endfield-capture-probe-mode";
        private const string RendererStartArgument = "-endfield-capture-probe-renderer-start";
        private const string RendererCountArgument = "-endfield-capture-probe-renderer-count";

        [MenuItem("Endfield/Character Recovery Lab/Build Wulfa Baked Capture Probe")]
        public static void BuildWulfaBakedCaptureProbe()
        {
            Build("wulfa-baked");
        }

        [MenuItem("Endfield/Character Recovery Lab/Build Wulfa Sanitized Iris Capture Probe")]
        public static void BuildWulfaSanitizedIrisCaptureProbe()
        {
            Build("wulfa-sanitized");
        }

        /// <summary>
        /// Batch entry point. Select a probe with
        /// -endfield-capture-probe-mode
        /// environment|swatches|wulfa|wulfa-no-props|wulfa-baked|wulfa-sanitized|zhuangfy|full.
        /// </summary>
        public static void BuildProbePlayer()
        {
            Build(ReadArgument(Environment.GetCommandLineArgs(), ProbeModeArgument) ?? "wulfa-baked");
        }

        private static void Build(string requestedMode)
        {
            string mode = NormalizeMode(requestedMode);
            string[] commandLine = Environment.GetCommandLineArgs();
            int defaultRendererStart = mode == "wulfa-sanitized" ? 4 : 0;
            int defaultRendererCount = mode == "wulfa-sanitized" ? 1 : int.MaxValue;
            int rendererStart = ReadNonNegativeIntegerArgument(
                commandLine,
                RendererStartArgument,
                defaultRendererStart);
            int rendererCount = ReadNonNegativeIntegerArgument(
                commandLine,
                RendererCountArgument,
                defaultRendererCount);
            string probeLabel = (mode == "wulfa-baked" || mode == "wulfa-sanitized") &&
                (rendererStart != 0 || rendererCount != int.MaxValue)
                ? $"{mode}-r{rendererStart}-n{rendererCount}"
                : mode;
            if (!File.Exists(Path.GetFullPath(FastScenePath)))
                throw new FileNotFoundException("Build the fast render-style scene first.", FastScenePath);

            EnsureAssetFolder(GeneratedProbeRoot);
            string probeScenePath = $"{GeneratedProbeRoot}/CharacterRenderStyleProbe_{probeLabel}.unity";
            if (AssetDatabase.LoadAssetAtPath<SceneAsset>(probeScenePath) != null)
                AssetDatabase.DeleteAsset(probeScenePath);

            Scene scene = EditorSceneManager.OpenScene(FastScenePath, OpenSceneMode.Single);
            // Save under a new path before making any changes. From this point forward the
            // open scene is the disposable probe; the source scene on disk is untouched.
            if (!EditorSceneManager.SaveScene(scene, probeScenePath, false))
                throw new IOException($"Could not create standalone capture probe scene: {probeScenePath}");

            GameObject root = GameObject.Find("CharacterRecoveryViewerRoot");
            if (root == null)
                throw new InvalidOperationException("Fast scene has no CharacterRecoveryViewerRoot.");

            Transform characters = root.transform.Find("Characters");
            Transform viewerUi = root.transform.Find("ViewerUI");
            if (viewerUi != null)
                UnityEngine.Object.DestroyImmediate(viewerUi.gameObject);

            if (characters != null)
                characters = ReplaceCharactersRootWithoutCatalog(root.transform, characters);

            Transform operatorActor = null;
            string operatorActorName = null;
            switch (mode)
            {
                case "environment":
                    if (characters != null)
                        UnityEngine.Object.DestroyImmediate(characters.gameObject);
                    break;

                case "swatches":
                    if (characters != null)
                        UnityEngine.Object.DestroyImmediate(characters.gameObject);
                    BuildWulfaMaterialSwatches(root.transform);
                    break;

                case "wulfa":
                case "wulfa-no-props":
                case "wulfa-baked":
                case "wulfa-sanitized":
                    KeepOnlyActor(characters, "Wulfa");
                    Transform wulfa = characters != null ? characters.Find("Wulfa") : null;
                    if (wulfa == null)
                        throw new InvalidOperationException("Fast scene has no Wulfa actor.");
                    wulfa.gameObject.SetActive(true);
                    if (mode == "wulfa-no-props" ||
                        mode == "wulfa-baked" ||
                        mode == "wulfa-sanitized")
                    {
                        Transform props = wulfa.Find("RecoveredProps");
                        if (props != null)
                            UnityEngine.Object.DestroyImmediate(props.gameObject);
                    }
                    if (mode == "wulfa-baked")
                    {
                        List<MeshRenderer> bakedRenderers = BakeSkinnedMeshes(wulfa, probeLabel);
                        FlattenBakedActor(
                            wulfa,
                            characters,
                            bakedRenderers,
                            rendererStart,
                            rendererCount);
                    }
                    else if (mode == "wulfa-sanitized")
                    {
                        BuildSanitizedStaticActor(
                            wulfa,
                            characters,
                            rendererStart,
                            rendererCount);
                    }
                    else
                    {
                        operatorActor = wulfa;
                        operatorActorName = "Wulfa";
                    }
                    break;

                case "zhuangfy":
                    KeepOnlyActor(characters, "Zhuangfy");
                    Transform zhuangfy = characters != null ? characters.Find("Zhuangfy") : null;
                    if (zhuangfy == null)
                        throw new InvalidOperationException("Fast scene has no Zhuangfy actor.");
                    zhuangfy.gameObject.SetActive(true);
                    operatorActor = zhuangfy;
                    operatorActorName = "Zhuangfy";
                    break;

                case "full":
                    break;
            }

            if (operatorActor != null)
            {
                Camera camera = Camera.main ?? UnityEngine.Object.FindObjectOfType<Camera>(true);
                if (camera == null)
                    throw new InvalidOperationException("Standalone character probe has no camera.");
                Transform lighting = root.transform.Find("Lighting");
                EndfieldManifestCharacterSetup.ConfigureOperatorReferenceLighting(
                    scene,
                    lighting,
                    camera,
                    operatorActorName,
                    operatorActor);
                // Field of view comes from the recovered Cinemachine lens, so
                // it is no longer carried alongside the actor name here.
                EndfieldManifestCharacterSetup.FrameCameraToRecoveredOperatorCamera(
                    camera,
                    operatorActorName);
                Debug.Log(
                    $"Standalone character probe uses original-data operator lighting: " +
                    $"actor={operatorActorName}, cameraFov={camera.fieldOfView:0.######}, " +
                    "live follower bones preserved.");
            }

            // The compatibility post shader is reached through Shader.Find at runtime,
            // which is not enough to keep it in a standalone build. Every visual probe
            // (primitive or real mesh) needs the same disabled material reference so the
            // captured frame includes exposure/tonemap/bloom instead of a stripped pass.
            if (mode != "environment")
                AddPostShaderKeepalive(root.transform);

            if (!EditorSceneManager.SaveScene(scene, probeScenePath, false))
                throw new IOException($"Could not save standalone capture probe scene: {probeScenePath}");
            AssetDatabase.SaveAssets();

            string outputDirectory = Path.GetFullPath(Path.Combine(
                Directory.GetCurrentDirectory(),
                "Builds",
                "CharacterRenderStyleProbe",
                probeLabel));
            Directory.CreateDirectory(outputDirectory);
            string playerPath = Path.Combine(outputDirectory, "EndfieldCharacterRenderStyleProbe.exe");

            GraphicsDeviceType[] previousGraphicsApis =
                PlayerSettings.GetGraphicsAPIs(BuildTarget.StandaloneWindows64);
            bool previousUseDefaultGraphicsApis =
                PlayerSettings.GetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64);
            try
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(BuildTarget.StandaloneWindows64, false);
                PlayerSettings.SetGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    new[] { GraphicsDeviceType.Direct3D11 });

                var options = new BuildPlayerOptions
                {
                    scenes = new[] { probeScenePath },
                    locationPathName = playerPath,
                    target = BuildTarget.StandaloneWindows64,
                    options = BuildOptions.Development,
                };
                BuildReport report = BuildPipeline.BuildPlayer(options);
                if (report.summary.result != BuildResult.Succeeded)
                {
                    throw new InvalidOperationException(
                        $"Standalone capture probe build failed: mode={mode}, " +
                        $"result={report.summary.result}, errors={report.summary.totalErrors}, " +
                        $"warnings={report.summary.totalWarnings}.");
                }

                Debug.Log(
                    $"Standalone capture probe built: mode={probeLabel}, path={playerPath}, " +
                    $"size={report.summary.totalSize} bytes, " +
                    $"time={report.summary.totalTime.TotalSeconds:0.0}s, api=D3D11.");
            }
            finally
            {
                PlayerSettings.SetUseDefaultGraphicsAPIs(
                    BuildTarget.StandaloneWindows64,
                    previousUseDefaultGraphicsApis);
                if (!previousUseDefaultGraphicsApis &&
                    previousGraphicsApis != null &&
                    previousGraphicsApis.Length != 0)
                {
                    PlayerSettings.SetGraphicsAPIs(
                        BuildTarget.StandaloneWindows64,
                        previousGraphicsApis);
                }
            }
        }

        private static void KeepOnlyActor(Transform characters, string actorName)
        {
            if (characters == null)
                throw new InvalidOperationException("Fast scene has no Characters root.");

            for (int index = characters.childCount - 1; index >= 0; index--)
            {
                Transform child = characters.GetChild(index);
                if (!string.Equals(child.name, actorName, StringComparison.Ordinal))
                    UnityEngine.Object.DestroyImmediate(child.gameObject);
            }
        }

        private static Transform ReplaceCharactersRootWithoutCatalog(
            Transform viewerRoot,
            Transform oldCharacters)
        {
            // CharacterRecoveryActorCatalog currently shares CharacterRecoveryRig.cs.
            // Unity therefore serialized its MonoScript as a scene-local object instead of
            // a normal GUID-backed script asset. Deleting only the component leaves the
            // scene-local MonoScript orphan behind. Moving the actor children out and
            // deleting the whole root follows the known-good environment-probe path and
            // lets Unity remove both objects together during scene serialization.
            int siblingIndex = oldCharacters.GetSiblingIndex();
            Vector3 localPosition = oldCharacters.localPosition;
            Quaternion localRotation = oldCharacters.localRotation;
            Vector3 localScale = oldCharacters.localScale;
            var children = new List<Transform>(oldCharacters.childCount);
            while (oldCharacters.childCount != 0)
            {
                Transform child = oldCharacters.GetChild(0);
                children.Add(child);
                child.SetParent(viewerRoot, true);
            }
            UnityEngine.Object.DestroyImmediate(oldCharacters.gameObject);

            var replacementObject = new GameObject("Characters");
            Transform replacement = replacementObject.transform;
            replacement.SetParent(viewerRoot, false);
            replacement.SetSiblingIndex(siblingIndex);
            replacement.localPosition = localPosition;
            replacement.localRotation = localRotation;
            replacement.localScale = localScale;
            foreach (Transform child in children)
            {
                if (child != null)
                    child.SetParent(replacement, true);
            }

            Debug.Log(
                $"Replaced catalog-bearing Characters root and preserved {children.Count} actor child(ren).");
            return replacement;
        }

        private static void BuildWulfaMaterialSwatches(Transform viewerRoot)
        {
            string[] materialNames =
            {
                "M_actor_wulfa_cloth_01",
                "M_actor_wulfa_body_01",
                "M_actor_wulfa_face_01",
                "M_actor_wulfa_hair_01",
                "M_actor_wulfa_iris_01",
                "M_hairshadow_common_01",
            };

            var swatchRoot = new GameObject("WulfaMaterialSwatches");
            swatchRoot.transform.SetParent(viewerRoot, false);
            for (int index = 0; index < materialNames.Length; index++)
            {
                Material material = FindMaterial(materialNames[index]);
                if (material == null)
                    throw new FileNotFoundException($"Could not find Wulfa material '{materialNames[index]}'.");

                GameObject sphere = GameObject.CreatePrimitive(PrimitiveType.Sphere);
                sphere.name = $"Swatch_{index:D2}_{material.name}";
                sphere.transform.SetParent(swatchRoot.transform, false);
                int column = index % 3;
                int row = index / 3;
                sphere.transform.localPosition = new Vector3(
                    (column - 1) * 0.5f,
                    1.32f - row * 0.52f,
                    0.0f);
                sphere.transform.localScale = Vector3.one * 0.38f;

                Collider collider = sphere.GetComponent<Collider>();
                if (collider != null)
                    UnityEngine.Object.DestroyImmediate(collider);
                sphere.GetComponent<MeshRenderer>().sharedMaterial = material;
            }

            Camera camera = Camera.main;
            if (camera == null)
                camera = UnityEngine.Object.FindObjectOfType<Camera>();
            if (camera != null)
            {
                Vector3 target = new Vector3(0.0f, 1.05f, 0.0f);
                camera.transform.position = new Vector3(0.0f, 1.05f, 2.55f);
                camera.transform.rotation = Quaternion.LookRotation(
                    target - camera.transform.position,
                    Vector3.up);
                camera.fieldOfView = 32.0f;

                CharacterRecoveryCameraController controller =
                    camera.GetComponent<CharacterRecoveryCameraController>();
                if (controller != null)
                    controller.focusTarget = swatchRoot.transform;
            }

            Debug.Log($"Created {materialNames.Length} primitive Wulfa material swatches.");
        }

        private static Material FindMaterial(string materialName)
        {
            string[] guids = AssetDatabase.FindAssets("t:Material", new[] { WulfaMaterialFolder });
            foreach (string guid in guids)
            {
                string path = AssetDatabase.GUIDToAssetPath(guid);
                Material material = AssetDatabase.LoadAssetAtPath<Material>(path);
                if (material != null &&
                    string.Equals(material.name, materialName, StringComparison.Ordinal))
                {
                    return material;
                }
            }
            return null;
        }

        private static void AddPostShaderKeepalive(Transform viewerRoot)
        {
            string[] shaderNames =
            {
                "Hidden/Endfield/HGRPCompat/ExposureTonemap",
                "Hidden/Endfield/HGRPCompat/RecoveredCharInfoLutBuilder2D",
            };
            string[] assetNames =
            {
                "HGCompatPostShaderKeepalive",
                "RecoveredCharInfoLutBuilderKeepalive",
            };

            for (int i = 0; i < shaderNames.Length; i++)
            {
                string shaderName = shaderNames[i];
                Shader shader = Shader.Find(shaderName);
                if (shader == null)
                    throw new InvalidOperationException(
                        $"Could not find compatibility post shader '{shaderName}'.");

                string materialPath = $"{GeneratedProbeRoot}/{assetNames[i]}.mat";
                if (AssetDatabase.LoadAssetAtPath<Material>(materialPath) != null)
                    AssetDatabase.DeleteAsset(materialPath);
                var material = new Material(shader) { name = assetNames[i] };
                AssetDatabase.CreateAsset(material, materialPath);

                var keepalive = new GameObject(assetNames[i]);
                keepalive.transform.SetParent(viewerRoot, false);
                MeshRenderer renderer = keepalive.AddComponent<MeshRenderer>();
                renderer.sharedMaterial = material;
                renderer.enabled = false;
                Debug.Log($"Kept standalone compatibility post shader: {shaderName}.");
            }
        }

        private static List<MeshRenderer> BakeSkinnedMeshes(Transform actor, string mode)
        {
            string meshFolder = $"{GeneratedProbeRoot}/Meshes_{mode}";
            if (AssetDatabase.IsValidFolder(meshFolder))
                AssetDatabase.DeleteAsset(meshFolder);
            EnsureAssetFolder(meshFolder);

            SkinnedMeshRenderer[] skinnedRenderers =
                actor.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var bakedRenderers = new List<MeshRenderer>(skinnedRenderers.Length);
            int bakedCount = 0;
            foreach (SkinnedMeshRenderer source in skinnedRenderers)
            {
                if (source.sharedMesh == null)
                    continue;

                var bakedMesh = new Mesh
                {
                    name = source.sharedMesh.name + "_CaptureBaked",
                    indexFormat = source.sharedMesh.indexFormat,
                };
                source.BakeMesh(bakedMesh, true);
                bakedMesh.RecalculateBounds();

                string safeName = MakeAssetName($"{bakedCount:D3}_{source.gameObject.name}_{bakedMesh.name}");
                string meshPath = AssetDatabase.GenerateUniqueAssetPath($"{meshFolder}/{safeName}.asset");
                AssetDatabase.CreateAsset(bakedMesh, meshPath);

                MeshFilter filter = source.GetComponent<MeshFilter>();
                if (filter == null)
                    filter = source.gameObject.AddComponent<MeshFilter>();
                filter.sharedMesh = bakedMesh;

                MeshRenderer replacement = source.GetComponent<MeshRenderer>();
                if (replacement == null)
                    replacement = source.gameObject.AddComponent<MeshRenderer>();
                CopyRendererState(source, replacement);

                UnityEngine.Object.DestroyImmediate(source);
                bakedRenderers.Add(replacement);
                bakedCount++;
            }

            if (bakedCount == 0)
                throw new InvalidOperationException("Wulfa capture probe found no skinned meshes to bake.");
            Debug.Log($"Baked {bakedCount} Wulfa skinned renderers for standalone capture probe.");
            return bakedRenderers;
        }

        private static void BuildSanitizedStaticActor(
            Transform sourceActor,
            Transform characters,
            int rendererStart,
            int rendererCount)
        {
            SkinnedMeshRenderer[] allSources =
                sourceActor.GetComponentsInChildren<SkinnedMeshRenderer>(true);
            var sources = new List<SkinnedMeshRenderer>(allSources.Length);
            foreach (SkinnedMeshRenderer source in allSources)
            {
                if (source != null && source.sharedMesh != null)
                    sources.Add(source);
            }

            int rendererEnd = rendererCount == int.MaxValue
                ? int.MaxValue
                : rendererStart + rendererCount;
            var flatActor = new GameObject("WulfaCaptureSanitized");
            flatActor.transform.SetParent(characters, false);
            flatActor.transform.position = sourceActor.position;
            flatActor.transform.rotation = sourceActor.rotation;
            flatActor.transform.localScale = sourceActor.localScale;

            int keptCount = 0;
            for (int index = 0; index < sources.Count; index++)
            {
                if (index < rendererStart || index >= rendererEnd)
                    continue;

                SkinnedMeshRenderer source = sources[index];
                var bakedMesh = new Mesh
                {
                    name = source.sharedMesh.name + "_CaptureBakeTransient",
                    indexFormat = source.sharedMesh.indexFormat,
                };
                // Keep transform scale outside the baked vertex payload. This makes the
                // clean mesh's object-space contract explicit and avoids carrying any
                // renderer/bone serialization into the standalone scene.
                source.BakeMesh(bakedMesh, false);

                Mesh sanitizedMesh;
                try
                {
                    sanitizedMesh = RebuildSanitizedMesh(
                        bakedMesh,
                        source.sharedMesh.name + "_CaptureSanitized");
                }
                finally
                {
                    UnityEngine.Object.DestroyImmediate(bakedMesh);
                }

                // Deliberately do not CreateAsset() for this mesh. Saving the disposable
                // probe scene embeds it exactly like the known-good backdrop quad, avoiding
                // the original actor mesh asset's skinning/blendshape/native payload.
                var target = new GameObject(source.gameObject.name + "_Sanitized");
                target.transform.SetParent(flatActor.transform, false);
                target.transform.position = source.transform.position;
                target.transform.rotation = source.transform.rotation;
                target.transform.localScale = DivideScale(
                    source.transform.lossyScale,
                    flatActor.transform.lossyScale);

                MeshFilter filter = target.AddComponent<MeshFilter>();
                filter.sharedMesh = sanitizedMesh;
                MeshRenderer renderer = target.AddComponent<MeshRenderer>();
                CopyMinimalRendererState(source, renderer);

                Debug.Log(
                    $"Sanitized Wulfa renderer {index}: source={source.gameObject.name}, " +
                    $"mesh={source.sharedMesh.name}, vertices={sanitizedMesh.vertexCount}, " +
                    $"subMeshes={sanitizedMesh.subMeshCount}, " +
                    $"indexFormat={sanitizedMesh.indexFormat}, bounds={sanitizedMesh.bounds}.");
                keptCount++;
            }

            if (keptCount == 0)
            {
                UnityEngine.Object.DestroyImmediate(flatActor);
                throw new InvalidOperationException(
                    $"The requested sanitized Wulfa renderer range is empty " +
                    $"(available={sources.Count}, start={rendererStart}, count={rendererCount}).");
            }

            CharacterRecoveryCameraController cameraController =
                UnityEngine.Object.FindObjectOfType<CharacterRecoveryCameraController>();
            if (cameraController != null)
                cameraController.focusTarget = flatActor.transform;

            UnityEngine.Object.DestroyImmediate(sourceActor.gameObject);
            flatActor.name = "Wulfa";
            Debug.Log(
                $"Embedded {keptCount}/{sources.Count} sanitized static Wulfa renderers " +
                $"(start={rendererStart}, count={rendererCount}) in the disposable probe scene.");
        }

        private static Mesh RebuildSanitizedMesh(Mesh source, string name)
        {
            Vector3[] vertices = source.vertices;
            if (vertices == null || vertices.Length == 0)
                throw new InvalidDataException($"Mesh '{source.name}' has no readable vertices.");
            ValidateFinite(vertices, source.name, "positions");

            var sanitized = new Mesh
            {
                name = name,
                indexFormat = vertices.Length > ushort.MaxValue
                    ? IndexFormat.UInt32
                    : IndexFormat.UInt16,
            };
            sanitized.vertices = vertices;

            Vector3[] normals = source.normals;
            if (normals != null && normals.Length == vertices.Length)
            {
                ValidateFinite(normals, source.name, "normals");
                sanitized.normals = normals;
            }
            else
            {
                sanitized.RecalculateNormals();
            }

            Vector4[] tangents = source.tangents;
            if (tangents != null && tangents.Length == vertices.Length)
            {
                ValidateFinite(tangents, source.name, "tangents");
                sanitized.tangents = tangents;
            }

            Color32[] colors = source.colors32;
            if (colors != null && colors.Length == vertices.Length)
                sanitized.colors32 = colors;

            for (int channel = 0; channel < 8; channel++)
                CopyValidatedUvChannel(source, sanitized, channel, vertices.Length);

            sanitized.subMeshCount = source.subMeshCount;
            for (int subMesh = 0; subMesh < source.subMeshCount; subMesh++)
            {
                int[] indices = source.GetIndices(subMesh, true);
                foreach (int vertexIndex in indices)
                {
                    if (vertexIndex < 0 || vertexIndex >= vertices.Length)
                    {
                        throw new InvalidDataException(
                            $"Mesh '{source.name}' submesh {subMesh} index {vertexIndex} " +
                            $"is outside [0, {vertices.Length}).");
                    }
                }
                sanitized.SetIndices(
                    indices,
                    source.GetTopology(subMesh),
                    subMesh,
                    false,
                    0);
            }

            sanitized.RecalculateBounds();
            return sanitized;
        }

        private static void CopyValidatedUvChannel(
            Mesh source,
            Mesh destination,
            int channel,
            int vertexCount)
        {
            VertexAttribute attribute = (VertexAttribute)((int)VertexAttribute.TexCoord0 + channel);
            if (!source.HasVertexAttribute(attribute))
                return;

            int dimension = source.GetVertexAttributeDimension(attribute);
            switch (dimension)
            {
                case 2:
                {
                    var values = new List<Vector2>(vertexCount);
                    source.GetUVs(channel, values);
                    ValidateFinite(values, source.name, $"uv{channel}", vertexCount);
                    destination.SetUVs(channel, values);
                    break;
                }
                case 3:
                {
                    var values = new List<Vector3>(vertexCount);
                    source.GetUVs(channel, values);
                    ValidateFinite(values, source.name, $"uv{channel}", vertexCount);
                    destination.SetUVs(channel, values);
                    break;
                }
                case 4:
                {
                    var values = new List<Vector4>(vertexCount);
                    source.GetUVs(channel, values);
                    ValidateFinite(values, source.name, $"uv{channel}", vertexCount);
                    destination.SetUVs(channel, values);
                    break;
                }
                default:
                    throw new InvalidDataException(
                        $"Mesh '{source.name}' uv{channel} has unsupported dimension {dimension}.");
            }
        }

        private static void ValidateFinite(Vector3[] values, string meshName, string label)
        {
            for (int index = 0; index < values.Length; index++)
            {
                Vector3 value = values[index];
                if (!IsFinite(value.x) || !IsFinite(value.y) || !IsFinite(value.z))
                    throw new InvalidDataException(
                        $"Mesh '{meshName}' {label}[{index}] is not finite: {value}.");
            }
        }

        private static void ValidateFinite(Vector4[] values, string meshName, string label)
        {
            for (int index = 0; index < values.Length; index++)
            {
                Vector4 value = values[index];
                if (!IsFinite(value.x) || !IsFinite(value.y) ||
                    !IsFinite(value.z) || !IsFinite(value.w))
                {
                    throw new InvalidDataException(
                        $"Mesh '{meshName}' {label}[{index}] is not finite: {value}.");
                }
            }
        }

        private static void ValidateFinite(
            List<Vector2> values,
            string meshName,
            string label,
            int vertexCount)
        {
            if (values.Count != vertexCount)
                throw new InvalidDataException(
                    $"Mesh '{meshName}' {label} count {values.Count} != {vertexCount} vertices.");
            for (int index = 0; index < values.Count; index++)
            {
                Vector2 value = values[index];
                if (!IsFinite(value.x) || !IsFinite(value.y))
                    throw new InvalidDataException(
                        $"Mesh '{meshName}' {label}[{index}] is not finite: {value}.");
            }
        }

        private static void ValidateFinite(
            List<Vector3> values,
            string meshName,
            string label,
            int vertexCount)
        {
            if (values.Count != vertexCount)
                throw new InvalidDataException(
                    $"Mesh '{meshName}' {label} count {values.Count} != {vertexCount} vertices.");
            for (int index = 0; index < values.Count; index++)
            {
                Vector3 value = values[index];
                if (!IsFinite(value.x) || !IsFinite(value.y) || !IsFinite(value.z))
                    throw new InvalidDataException(
                        $"Mesh '{meshName}' {label}[{index}] is not finite: {value}.");
            }
        }

        private static void ValidateFinite(
            List<Vector4> values,
            string meshName,
            string label,
            int vertexCount)
        {
            if (values.Count != vertexCount)
                throw new InvalidDataException(
                    $"Mesh '{meshName}' {label} count {values.Count} != {vertexCount} vertices.");
            ValidateFinite(values.ToArray(), meshName, label);
        }

        private static bool IsFinite(float value)
        {
            return !float.IsNaN(value) && !float.IsInfinity(value);
        }

        private static Vector3 DivideScale(Vector3 numerator, Vector3 denominator)
        {
            return new Vector3(
                Mathf.Approximately(denominator.x, 0.0f) ? 1.0f : numerator.x / denominator.x,
                Mathf.Approximately(denominator.y, 0.0f) ? 1.0f : numerator.y / denominator.y,
                Mathf.Approximately(denominator.z, 0.0f) ? 1.0f : numerator.z / denominator.z);
        }

        private static void CopyMinimalRendererState(Renderer source, Renderer destination)
        {
            destination.enabled = source.enabled;
            destination.sharedMaterials = source.sharedMaterials;
            destination.shadowCastingMode = source.shadowCastingMode;
            destination.receiveShadows = source.receiveShadows;
            destination.renderingLayerMask = source.renderingLayerMask;
            destination.rendererPriority = source.rendererPriority;
            destination.sortingLayerID = source.sortingLayerID;
            destination.sortingOrder = source.sortingOrder;

            var propertyBlock = new MaterialPropertyBlock();
            source.GetPropertyBlock(propertyBlock);
            if (!propertyBlock.isEmpty)
                destination.SetPropertyBlock(propertyBlock);
        }

        private static void FlattenBakedActor(
            Transform sourceActor,
            Transform characters,
            List<MeshRenderer> bakedRenderers,
            int rendererStart,
            int rendererCount)
        {
            var flatActor = new GameObject("WulfaCaptureStatic");
            flatActor.transform.SetParent(characters, false);
            flatActor.transform.position = sourceActor.position;
            flatActor.transform.rotation = sourceActor.rotation;

            int rendererEnd = rendererCount == int.MaxValue
                ? int.MaxValue
                : rendererStart + rendererCount;
            int keptCount = 0;
            for (int index = 0; index < bakedRenderers.Count; index++)
            {
                MeshRenderer renderer = bakedRenderers[index];
                if (renderer == null)
                    continue;
                if (index < rendererStart || index >= rendererEnd)
                {
                    UnityEngine.Object.DestroyImmediate(renderer.gameObject);
                    continue;
                }
                renderer.transform.SetParent(flatActor.transform, true);
                keptCount++;
            }

            if (keptCount == 0)
                throw new InvalidOperationException("The requested Wulfa renderer range is empty.");

            CharacterRecoveryCameraController cameraController =
                UnityEngine.Object.FindObjectOfType<CharacterRecoveryCameraController>();
            if (cameraController != null)
                cameraController.focusTarget = flatActor.transform;

            UnityEngine.Object.DestroyImmediate(sourceActor.gameObject);
            flatActor.name = "Wulfa";
            Debug.Log(
                $"Flattened {keptCount}/{bakedRenderers.Count} baked Wulfa renderers " +
                $"(start={rendererStart}, count={rendererCount}) and removed the original " +
                "skeleton/runtime hierarchy from the static capture probe.");
        }

        private static void CopyRendererState(Renderer source, Renderer destination)
        {
            destination.enabled = source.enabled;
            destination.sharedMaterials = source.sharedMaterials;
            destination.shadowCastingMode = source.shadowCastingMode;
            destination.receiveShadows = source.receiveShadows;
            destination.lightProbeUsage = source.lightProbeUsage;
            destination.reflectionProbeUsage = source.reflectionProbeUsage;
            destination.motionVectorGenerationMode = source.motionVectorGenerationMode;
            destination.allowOcclusionWhenDynamic = source.allowOcclusionWhenDynamic;
            destination.renderingLayerMask = source.renderingLayerMask;
            destination.rendererPriority = source.rendererPriority;
            destination.sortingLayerID = source.sortingLayerID;
            destination.sortingOrder = source.sortingOrder;

            var propertyBlock = new MaterialPropertyBlock();
            source.GetPropertyBlock(propertyBlock);
            if (!propertyBlock.isEmpty)
                destination.SetPropertyBlock(propertyBlock);
        }

        private static string NormalizeMode(string mode)
        {
            string normalized = (mode ?? string.Empty).Trim().ToLowerInvariant();
            switch (normalized)
            {
                case "environment":
                case "swatches":
                case "wulfa":
                case "wulfa-no-props":
                case "wulfa-baked":
                case "wulfa-sanitized":
                case "zhuangfy":
                case "full":
                    return normalized;
                default:
                    throw new ArgumentException(
                        $"Unknown standalone capture probe mode '{mode}'. " +
                        "Use environment, swatches, wulfa, wulfa-no-props, wulfa-baked, " +
                        "wulfa-sanitized, " +
                        "zhuangfy, or full.");
            }
        }

        private static string ReadArgument(string[] arguments, string name)
        {
            for (int index = 0; index + 1 < arguments.Length; index++)
            {
                if (string.Equals(arguments[index], name, StringComparison.OrdinalIgnoreCase))
                    return arguments[index + 1];
            }
            return null;
        }

        private static int ReadNonNegativeIntegerArgument(
            string[] arguments,
            string name,
            int fallback)
        {
            string value = ReadArgument(arguments, name);
            if (!int.TryParse(value, out int parsed) || parsed < 0)
                return fallback;
            return parsed;
        }

        private static string MakeAssetName(string value)
        {
            foreach (char invalid in Path.GetInvalidFileNameChars())
                value = value.Replace(invalid, '_');
            return value.Replace(' ', '_');
        }

        private static void EnsureAssetFolder(string assetPath)
        {
            string[] segments = assetPath.Split('/');
            string current = segments[0];
            for (int index = 1; index < segments.Length; index++)
            {
                string next = current + "/" + segments[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, segments[index]);
                current = next;
            }
        }
    }
}
