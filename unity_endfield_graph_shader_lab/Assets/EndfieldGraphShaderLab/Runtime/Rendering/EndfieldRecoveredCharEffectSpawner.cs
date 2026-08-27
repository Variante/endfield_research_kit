using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Shared Overview entrance-effect adapter for generated, source-closed
    /// particle or static-mesh prefabs. The component is intentionally data-driven:
    /// no prefab-name fallback, EffectSetting emulation, or HGRP shader
    /// approximation is performed here.
    /// </summary>
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Character Recovery/Char Effect Spawner")]
    public sealed class EndfieldRecoveredCharEffectSpawner : MonoBehaviour,
        IEndfieldOverviewEffectSpawner
    {
        public const string ExpectedContractSchema =
            "endfield.zhuangfy-gacha-particle-inventory.v1";
        public const string CharInfoContractSchema =
            "endfield.charinfo-char-effect-particle.v1";
        public const string EndminfOverviewContractSchema =
            "endfield.endminf-overview-particle-stage.v1";
        private const string EndminfCompositeRockClipName =
            "A_fx_endminf_ui_overview_03_04";
        private const float EndminfCompositeRockClipDelaySeconds = 2.7666667f;
        private const float EndminfSmoke20PresentationAdvanceSeconds = 2f / 60f;
        private const string EndminfSmoke20MaterialName = "M_fx_endminm_gfx_20";

        public enum BindingKind
        {
            Particle = 0,
            StaticMesh = 1,
        }

        public static bool IsSupportedContractSchema(string schema)
        {
            return string.Equals(schema, ExpectedContractSchema, StringComparison.Ordinal) ||
                string.Equals(schema, CharInfoContractSchema, StringComparison.Ordinal) ||
                string.Equals(schema, EndminfOverviewContractSchema, StringComparison.Ordinal);
        }

        [Serializable]
        public sealed class Binding
        {
            [Tooltip("Serialized effect representation. Existing bindings default to Particle.")]
            public BindingKind bindingKind;

            [Tooltip("Exact EndfieldOverviewEffectRequest.prefabName.")]
            public string requestPrefabName;

            [Tooltip("Generated prefab with an EndfieldRecoveredParticleEffectSource marker.")]
            public GameObject prefab;

            [Tooltip("Exact existing actor-relative object path when the effect is already reconstructed as an animated item-widget object instead of a particle prefab.")]
            public string existingActorObjectPath;

            [Tooltip("Optional exact mount path below the actor root. Empty means actor root.")]
            public string requiredMountPoint;

            [Tooltip("Explicit source scene mount. Required for external mounts such as singleEffects/effect<height>.")]
            public Transform explicitMount;

            [Tooltip("Source owner path from the serialized contract; evidence only, never resolved by name.")]
            public string sourceMountOwner;

            public long sourceMountGameObjectPathId;
            public long sourceMountTransformPathId;

            [Tooltip("Optional marker effectRoot assertion. Empty means use the marker value.")]
            public string expectedEffectRoot;

            [Min(0f)]
            public float expectedDelay;

            [Min(0f)]
            public float expectedDuration;

            [Tooltip("Exact AnimatorBehaviourPlayEffect EffectItem.isStationaryPosition.")]
            public bool stationaryPosition;
            public bool shouldFollowScale;
            public bool shouldFollowRotation;
            public bool shouldFollowMainObjRotation;
        }

        [SerializeField]
        private Binding[] bindings = Array.Empty<Binding>();

        [SerializeField]
        private bool rejectUnboundRequests = true;

        private readonly Dictionary<string, GameObject> activeEffects =
            new Dictionary<string, GameObject>(StringComparer.Ordinal);
        private readonly Dictionary<string, Coroutine> pendingEffects =
            new Dictionary<string, Coroutine>(StringComparer.Ordinal);
        private readonly Dictionary<string, Coroutine> lifetimeEffects =
            new Dictionary<string, Coroutine>(StringComparer.Ordinal);

        public Binding[] Bindings => bindings;

        public void ReplaceBindings(Binding[] value)
        {
            bindings = value ?? Array.Empty<Binding>();
        }

        public bool RejectUnboundRequests
        {
            get => rejectUnboundRequests;
            set => rejectUnboundRequests = value;
        }

        public void SpawnOverviewEffect(
            EndfieldOverviewEffectRequest request,
            Transform actorRoot)
        {
            if (string.IsNullOrEmpty(request.prefabName))
                return;

            Binding binding = FindBinding(request.prefabName);
            if (binding == null)
            {
                FailClosed(
                    "unbound_effect_request",
                    request.prefabName,
                    "No exact CharEffect binding exists.");
                return;
            }

            if (!string.IsNullOrEmpty(binding.existingActorObjectPath))
            {
                if (binding.prefab != null)
                {
                    FailClosed(
                        "invalid_existing_effect_binding",
                        request.prefabName,
                        "Existing-object binding also supplied a prefab.");
                    return;
                }
                Transform existing = actorRoot == null
                    ? null
                    : actorRoot.Find(binding.existingActorObjectPath);
                if (existing == null)
                {
                    FailClosed(
                        "missing_existing_effect_object",
                        request.prefabName,
                        "Exact actor-relative item-widget object was not found.");
                }
                return;
            }

            if (!TryValidateBinding(binding, request, out string reason))
            {
                FailClosed("invalid_effect_binding", request.prefabName, reason);
                return;
            }

            Transform mount = ResolveMount(binding, request, actorRoot, out reason);
            if (mount == null)
            {
                FailClosed("missing_effect_mount", request.prefabName, reason);
                return;
            }

            FinishOverviewEffect(request.prefabName);

            if (binding.expectedDelay > 0f)
            {
                pendingEffects[request.prefabName] = StartCoroutine(
                    SpawnAfterDelay(binding, request, mount));
                return;
            }

            CreateEffect(binding, request, mount);
        }

        private IEnumerator SpawnAfterDelay(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            Transform mount)
        {
            yield return new WaitForSeconds(binding.expectedDelay);
            pendingEffects.Remove(request.prefabName);
            if (mount == null || !isActiveAndEnabled)
                yield break;
            CreateEffect(binding, request, mount);
        }

        private void CreateEffect(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            Transform mount)
        {

            GameObject instance;
            if (binding.stationaryPosition)
            {
                instance = Instantiate(binding.prefab);
                instance.transform.position = mount.position;
                instance.transform.rotation = binding.shouldFollowRotation
                    ? mount.rotation : binding.prefab.transform.rotation;
                instance.transform.localScale = binding.shouldFollowScale
                    ? mount.localScale : Vector3.one;
            }
            else
            {
                instance = Instantiate(binding.prefab, mount, false);
            }
            instance.name = binding.prefab.name + "__OverviewRuntime";
            ApplyEndminfBillboardClampCompatibility(instance);
            if (string.Equals(binding.prefab.name,
                    "P_fxui_endminm003_overview_02",
                    StringComparison.Ordinal))
                EndfieldEndminfVisualCompatibilityClock.MarkOverview02Start(
                    instance.transform);
            instance.SetActive(false);

            ParticleSystem[] systems = binding.bindingKind == BindingKind.Particle
                ? instance.GetComponentsInChildren<ParticleSystem>(true)
                : Array.Empty<ParticleSystem>();
            foreach (ParticleSystem system in systems)
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);

            activeEffects[request.prefabName] = instance;
            instance.SetActive(true);
            StartRecoveredLegacyAnimations(instance);
            PlayRecoveredParticleSystems(instance, systems);

            if (binding.expectedDuration > 0f)
            {
                lifetimeEffects[request.prefabName] = StartCoroutine(
                    FinishAfterDuration(
                        request.prefabName,
                        instance,
                        binding.expectedDuration));
            }
        }

        private void StartRecoveredLegacyAnimations(GameObject instance)
        {
            // Instantiate activates an enabled prefab before this spawner can
            // clear and stage its ParticleSystems. Deactivating that instance
            // again stops playAutomatically legacy Animation components, and
            // the following activation does not reliably restart them. Replay
            // only clips explicitly marked automatic in the recovered prefab.
            foreach (Animation animation in
                instance.GetComponentsInChildren<Animation>(true))
            {
                if (!animation.playAutomatically || animation.clip == null)
                    continue;
                animation.Stop();
                animation.Rewind(animation.clip.name);
                if (string.Equals(
                        animation.clip.name,
                        EndminfCompositeRockClipName,
                        StringComparison.Ordinal))
                {
                    // Retail's last nonzero/first-zero sampled packets are at
                    // 4.1667/4.30 s. The exact 1.50 s source active curve and
                    // its 30-fps ticks fix the trigger at tick 83 (2.7667 s).
                    StartCoroutine(PlayRecoveredLegacyAnimationAfterDelay(
                        instance,
                        animation,
                        EndminfCompositeRockClipDelaySeconds));
                    continue;
                }
                PlayRecoveredLegacyAnimation(animation);
            }
        }

        private static void PlayRecoveredLegacyAnimation(Animation animation)
        {
            if (!animation.Play(animation.clip.name))
            {
                Debug.LogError(
                    "Recovered CharEffect legacy animation failed closed: " +
                    animation.clip.name,
                    animation);
            }
        }

        private static IEnumerator PlayRecoveredLegacyAnimationAfterDelay(
            GameObject instance,
            Animation animation,
            float delaySeconds)
        {
            yield return new WaitForSeconds(delaySeconds);
            if (instance == null || animation == null ||
                !instance.activeInHierarchy)
                yield break;
            PlayRecoveredLegacyAnimation(animation);
        }

        private static void PlayRecoveredParticleSystems(
            GameObject instance,
            ParticleSystem[] systems)
        {
            // The overview_02 post owner predates the first visible body by
            // nine retail ticks, but the phase-paired no-frame-generation
            // sequence does not put that age on its ParticleSystems. Applying
            // the post offset here makes M13 visible at source frame 367,
            // where retail has no ring, and removes its peak from frame 382.
            // Keep particle delays on the selection/body timeline; only the
            // separately recovered compatibility post clock carries pre-roll.
            foreach (ParticleSystem system in systems)
            {
                system.Play(true);
                if (IsEndminfSmoke20(instance, system))
                {
                    // The retained 4.46 s source delay is correct, but Unity's
                    // public ParticleSystem publishes this six-particle plume
                    // two render ticks after the matched retail frame. Advance
                    // only the source-identified smoke owner; global particle
                    // pre-roll shifts crystals, stones, rays and their seeds.
                    system.Simulate(
                        EndminfSmoke20PresentationAdvanceSeconds,
                        false,
                        false,
                        true);
                    // Simulate leaves a public-Unity ParticleSystem paused;
                    // resume this owner without recursively restarting peers.
                    system.Play(false);
                }
            }
        }

        private static bool IsEndminfSmoke20(
            GameObject instance,
            ParticleSystem system)
        {
            if (!EndfieldEndminfVisualCompatibilityClock.Requested ||
                instance == null || system == null ||
                instance.name.IndexOf(
                    "P_fxui_endminm003_overview_02",
                    StringComparison.Ordinal) < 0 ||
                !string.Equals(system.name, "smoke (2)", StringComparison.Ordinal) ||
                system.transform.parent == null ||
                !string.Equals(system.transform.parent.name, "all", StringComparison.Ordinal))
            {
                return false;
            }

            ParticleSystemRenderer renderer = system.GetComponent<ParticleSystemRenderer>();
            if (renderer == null)
                return false;
            foreach (Material material in renderer.sharedMaterials)
            {
                if (material != null && string.Equals(
                        material.name,
                        EndminfSmoke20MaterialName,
                        StringComparison.Ordinal))
                    return true;
            }
            return false;
        }

        private static void ApplyEndminfBillboardClampCompatibility(GameObject instance)
        {
            if (!EndfieldEndminfVisualCompatibilityClock.Requested || instance == null ||
                instance.name.IndexOf("P_fxui_endminm003_overview_",
                    StringComparison.Ordinal) < 0)
                return;

            // The source ParticleSystemRenderer payload frequently carries
            // maxParticleSize=0.5. Unity's built-in particle path interprets
            // that as a hard half-screen billboard clamp, visibly slicing the
            // authored flare. Retail HGRP owns a different VFX draw path. Keep
            // the serialized prefab untouched and remove only that runtime
            // compatibility clamp for billboard/stretch billboards.
            foreach (ParticleSystemRenderer renderer in
                instance.GetComponentsInChildren<ParticleSystemRenderer>(true))
            {
                // Do not broaden this to Stretch. Endminf's M22 jianshe ray
                // producer is an authored stretch renderer whose 0.5 cap is
                // visible in the retail frame. Removing that cap turned its
                // short radial rays into screen-spanning shard streaks.
                if (renderer.renderMode != ParticleSystemRenderMode.Billboard)
                    continue;
                if (renderer.maxParticleSize <= 0.5001f)
                    renderer.maxParticleSize = 10f;
            }
        }

        private IEnumerator FinishAfterDuration(
            string prefabName,
            GameObject expectedInstance,
            float duration)
        {
            yield return new WaitForSeconds(duration);
            lifetimeEffects.Remove(prefabName);
            if (activeEffects.TryGetValue(prefabName, out GameObject instance) &&
                instance == expectedInstance)
            {
                activeEffects.Remove(prefabName);
                DestroyEffectInstance(instance);
            }
        }

        public void FinishOverviewEffect(string prefabName)
        {
            if (string.IsNullOrEmpty(prefabName))
                return;

            if (pendingEffects.TryGetValue(prefabName, out Coroutine pending))
            {
                pendingEffects.Remove(prefabName);
                if (pending != null)
                    StopCoroutine(pending);
            }
            if (lifetimeEffects.TryGetValue(prefabName, out Coroutine lifetime))
            {
                lifetimeEffects.Remove(prefabName);
                if (lifetime != null)
                    StopCoroutine(lifetime);
            }

            if (!activeEffects.TryGetValue(prefabName, out GameObject instance))
                return;

            activeEffects.Remove(prefabName);
            DestroyEffectInstance(instance);
        }

        private static void DestroyEffectInstance(GameObject instance)
        {
            if (instance == null)
                return;

            EndfieldEndminfVisualCompatibilityClock.ClearOverview02(
                instance.transform);

            foreach (ParticleSystem system in
                instance.GetComponentsInChildren<ParticleSystem>(true))
            {
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
            }
            Destroy(instance);
        }

        private void OnDisable()
        {
            FinishAllEffects();
        }

        private void OnDestroy()
        {
            FinishAllEffects();
        }

        private void FinishAllEffects()
        {
            string[] names = new string[activeEffects.Count];
            activeEffects.Keys.CopyTo(names, 0);
            foreach (string name in names)
                FinishOverviewEffect(name);
        }

        private Binding FindBinding(string requestPrefabName)
        {
            if (bindings == null)
                return null;
            foreach (Binding binding in bindings)
            {
                if (binding != null &&
                    string.Equals(
                        binding.requestPrefabName,
                        requestPrefabName,
                        StringComparison.Ordinal))
                    return binding;
            }
            return null;
        }

        private static Transform ResolveMount(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            Transform actorRoot,
            out string reason)
        {
            reason = string.Empty;
            if (actorRoot == null)
            {
                reason = "Actor root is null.";
                return null;
            }

            string required = binding.requiredMountPoint ?? string.Empty;
            string requested = request.mountPoint ?? string.Empty;
            if (!string.Equals(required, requested, StringComparison.Ordinal))
            {
                reason =
                    "Requested mount point does not match the binding: '" +
                    requested + "' versus '" + required + "'.";
                return null;
            }

            if (binding.explicitMount != null)
                return binding.explicitMount;

            if (required.StartsWith("sceneObject.", StringComparison.Ordinal))
            {
                reason = "External source mount requires an explicit Transform binding.";
                return null;
            }

            if (requested.Length == 0)
                return actorRoot;

            if (requested.IndexOf('/') >= 0)
            {
                Transform pathMount = actorRoot.Find(requested);
                if (pathMount == null)
                    reason = "Exact mount path was not found below the actor root.";
                return pathMount;
            }

            Transform uniqueMount = null;
            foreach (Transform candidate in actorRoot.GetComponentsInChildren<Transform>(true))
            {
                if (!string.Equals(candidate.name, requested, StringComparison.Ordinal))
                    continue;
                if (uniqueMount != null)
                {
                    reason = "Mount name is not unique below the actor root.";
                    return null;
                }
                uniqueMount = candidate;
            }
            if (uniqueMount == null)
                reason = "Exact mount name was not found below the actor root.";
            return uniqueMount;
        }

        private static bool TryValidateBinding(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            out string reason)
        {
            reason = string.Empty;
            if (binding.prefab == null)
            {
                reason = "Binding prefab is null.";
                return false;
            }

            if (!string.Equals(
                binding.requestPrefabName,
                request.prefabName,
                StringComparison.Ordinal))
            {
                reason = "Binding request name is not exact.";
                return false;
            }

            if (binding.bindingKind == BindingKind.StaticMesh)
                return TryValidateStaticMeshBinding(binding, out reason);
            if (binding.bindingKind != BindingKind.Particle)
            {
                reason = "Unsupported effect binding kind.";
                return false;
            }

            EndfieldRecoveredParticleEffectSource marker =
                binding.prefab.GetComponent<EndfieldRecoveredParticleEffectSource>();
            if (marker == null)
            {
                reason = "Prefab has no source particle contract marker.";
                return false;
            }
            if (!IsSupportedContractSchema(marker.contractSchema))
            {
                reason = "Unsupported or unknown particle contract schema.";
                return false;
            }
            if (string.IsNullOrEmpty(marker.effectRoot))
            {
                reason = "Source marker has no effectRoot.";
                return false;
            }
            if (!string.IsNullOrEmpty(binding.expectedEffectRoot) &&
                marker.effectRoot != binding.expectedEffectRoot)
            {
                reason = "Source effectRoot does not match the explicit binding.";
                return false;
            }
            if (binding.expectedDuration > 0f &&
                !Mathf.Approximately(binding.expectedDuration, marker.sourceEffectDuration))
            {
                reason = "Source effect duration does not match the explicit binding.";
                return false;
            }
            if (marker.particleNodes == null || marker.particleNodes.Length == 0)
            {
                reason = "Source marker has no particle nodes.";
                return false;
            }

            ParticleSystem[] systems =
                binding.prefab.GetComponentsInChildren<ParticleSystem>(true);
            ParticleSystemRenderer[] renderers =
                binding.prefab.GetComponentsInChildren<ParticleSystemRenderer>(true);
            if (systems.Length != marker.particleNodes.Length ||
                renderers.Length != marker.particleNodes.Length)
            {
                reason = "Generated particle/renderer counts drifted from the source marker.";
                return false;
            }

            foreach (EndfieldRecoveredParticleNodeSource node in marker.particleNodes)
            {
                if (node == null ||
                    !node.nativeParticlePayloadApplied ||
                    !node.nativeRendererPayloadApplied ||
                    (node.rendererFailClosedForUnrecoveredShader &&
                     !string.Equals(marker.contractSchema,
                         EndminfOverviewContractSchema, StringComparison.Ordinal)))
                {
                    reason =
                        "At least one particle node is incomplete or fail-closed for an " +
                        "unrecovered shader.";
                    return false;
                }
            }

            for (int index = 0; index < renderers.Length; index++)
            {
                ParticleSystemRenderer renderer = renderers[index];
                EndfieldRecoveredParticleNodeSource node = marker.particleNodes[index];
                if (renderer == null)
                {
                    reason = "Particle renderer is missing.";
                    return false;
                }
                if (!node.sourceRendererEnabled)
                {
                    if (renderer.enabled)
                    {
                        reason = "Disabled source renderer became enabled.";
                        return false;
                    }
                    continue;
                }
                if (node.rendererFailClosedForUnrecoveredShader &&
                    string.Equals(marker.contractSchema,
                        EndminfOverviewContractSchema, StringComparison.Ordinal))
                {
                    if (renderer.enabled)
                    {
                        reason = "Fail-closed Endminf renderer became enabled.";
                        return false;
                    }
                    continue;
                }
                if (renderer.sharedMaterials == null || renderer.sharedMaterials.Length == 0)
                {
                    reason = "Enabled particle renderer has no source material.";
                    return false;
                }
                foreach (Material material in renderer.sharedMaterials)
                {
                    if (material == null || material.shader == null ||
                        material.shader.name.IndexOf(
                            "Unavailable",
                            StringComparison.OrdinalIgnoreCase) >= 0 ||
                        material.shader.name.IndexOf(
                            "FailClosed",
                            StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        reason =
                            "Particle material/shader is unresolved or explicitly " +
                            "fail-closed.";
                        return false;
                    }
                }
            }
            return true;
        }

        public static bool TryValidateBindingForRecoveryAudit(
            Binding binding,
            EndfieldOverviewEffectRequest request,
            out string reason)
        {
            return TryValidateBinding(binding, request, out reason);
        }

        private static bool TryValidateStaticMeshBinding(Binding binding, out string reason)
        {
            reason = string.Empty;
            EndfieldRecoveredStaticMeshEffectSource marker =
                binding.prefab.GetComponent<EndfieldRecoveredStaticMeshEffectSource>();
            if (marker == null)
            {
                reason = "Prefab has no source static-mesh contract marker.";
                return false;
            }
            if (!string.Equals(
                marker.contractSchema,
                EndfieldRecoveredStaticMeshEffectSource.LiZhiyanStart01ContractSchema,
                StringComparison.Ordinal))
            {
                reason = "Unsupported or unknown static-mesh contract schema.";
                return false;
            }
            if (!string.Equals(
                    marker.effectRoot,
                    "P_fxui_lizhiyan_overview_start_01",
                    StringComparison.Ordinal) ||
                (!string.IsNullOrEmpty(binding.expectedEffectRoot) &&
                    marker.effectRoot != binding.expectedEffectRoot))
            {
                reason = "Static-mesh source effectRoot is absent or mismatched.";
                return false;
            }
            if (!marker.sourcePayloadApplied || !marker.visibleAdmission ||
                marker.blockedBy == null || marker.blockedBy.Length != 0 ||
                string.IsNullOrEmpty(marker.sourceAggregateSha256))
            {
                reason = "Static-mesh source contract has not admitted runtime visibility.";
                return false;
            }
            if (!Mathf.Approximately(binding.expectedDuration, marker.sourceEffectDuration) ||
                !Mathf.Approximately(binding.expectedDelay, marker.sourceEffectDelay))
            {
                reason = "Static-mesh source timing does not match the explicit binding.";
                return false;
            }
            if (!marker.sourceEffectSettingPayloadApplied ||
                !marker.sourceAnimationPayloadApplied || marker.sourceStartAnimationClipPathId == 0 ||
                marker.sourceStartAnimationClip == null ||
                marker.sourceStartAnimationClipName != "A_fxui__lizhiyan_overview_start_01" ||
                !Mathf.Approximately(marker.sourceStartAnimationSampleRate, 30.0f) ||
                !Mathf.Approximately(marker.sourceStartAnimationStopTime, 6.366667f) ||
                marker.sourceAnimationTargetPathHashes == null ||
                marker.sourceAnimationTargetPathHashes.Length != 10 ||
                marker.sourceAnimationTargetPaths == null ||
                marker.sourceAnimationTargetPaths.Length != 10 ||
                marker.sourceAnimationMaterialPropertyHashes == null ||
                marker.sourceAnimationMaterialPropertyHashes.Length != 7 ||
                marker.sourceAnimationMaterialProperties == null ||
                marker.sourceAnimationMaterialProperties.Length != 7 ||
                !marker.sourceAnimationBindingsResolved)
            {
                reason = "Static-mesh EffectSetting or animation payload is not applied.";
                return false;
            }
            var expectedAnimationPaths = new HashSet<string>(new[] {
                "S_fx_shoutiaodai_01", "S_fx_lzy_fenweiqiliu_02",
                "S_fx_lzy_tiaodaifenwei_01 (4)", "S_fx_shoutiaodai_01 (1)",
                "S_fx_lzy_tiaodaifenwei_01 (5)", "S_fx_lzy_tiaodaifenwei_01 (7)",
                "S_fx_lzy_tiaodaifenwei_01 (6)", "S_fx_lzy_fenweiqiliu_02 (1)",
                "S_fx_tuoweidisan_01", "S_fx_lzy_fenweiqiliu_02 (3)" });
            var expectedAnimationProperties = new HashSet<string>(new[] {
                "_MainTex_ST.x", "_MainTex_ST.y", "_MainTex_ST.z", "_MainTex_ST.w",
                "_DisturbUIntensity1", "_TintColorAlpha", "_DissolveScheduleOffset" });
            if (!expectedAnimationPaths.SetEquals(marker.sourceAnimationTargetPaths) ||
                !expectedAnimationProperties.SetEquals(marker.sourceAnimationMaterialProperties))
            {
                reason = "Static-mesh animation path or material-property mapping drifted.";
                return false;
            }
            if (marker.sourceGameObjectPathId != 1314393592276219621L ||
                marker.sourceTransformPathId != 4995983695754262245L ||
                marker.sourceEffectSettingPathId != 2305038813790631653L ||
                marker.sourceAnimatorPathId != -7686199192497981723L ||
                marker.sourceAnimationHelperPathId != -8633596874860955931L ||
                marker.sourceStartAnimationClipPathId != 7360398354216100382L)
            {
                reason = "Li Zhiyan start_01 source component identities drifted.";
                return false;
            }
            if (marker.staticMeshNodes == null || marker.staticMeshNodes.Length == 0)
            {
                reason = "Source marker has no static-mesh nodes.";
                return false;
            }
            if (marker.staticMeshNodes.Length != 4)
            {
                reason = "Li Zhiyan start_01 must contain exactly four static-mesh nodes.";
                return false;
            }
            var expectedFilterIds = new HashSet<long> {
                8907211204029478629L, -3027743468593580315L,
                3101834544805148389L, -9078621906017421595L };
            var expectedRendererIds = new HashSet<long> {
                -1741348596941359387L, 4708942470875150053L,
                8270785745755535077L, -6436609233402104091L };
            var observedFilterIds = new HashSet<long>();
            var observedRendererIds = new HashSet<long>();
            var observedMaterialIds = new HashSet<long>();
            MeshFilter[] filters = binding.prefab.GetComponentsInChildren<MeshFilter>(true);
            MeshRenderer[] renderers = binding.prefab.GetComponentsInChildren<MeshRenderer>(true);
            if (binding.prefab.GetComponentsInChildren<ParticleSystem>(true).Length != 0)
            {
                reason = "Static-mesh source unexpectedly contains ParticleSystems.";
                return false;
            }
            if (filters.Length != marker.staticMeshNodes.Length ||
                renderers.Length != marker.staticMeshNodes.Length)
            {
                reason = "Generated static mesh/renderer counts drifted from the source marker.";
                return false;
            }
            foreach (EndfieldRecoveredStaticMeshNodeSource node in marker.staticMeshNodes)
            {
                if (node == null || node.generatedMeshFilter == null ||
                    node.generatedMeshRenderer == null || node.meshPathId == 0 ||
                    node.materialPathIds == null || node.materialPathIds.Length == 0 ||
                    !node.nativeMeshPayloadApplied || !node.nativeRendererPayloadApplied ||
                    !node.nativeTexturePayloadsApplied || !node.exactShaderVariantsApplied ||
                    node.rendererFailClosedForUnrecoveredShader)
                {
                    reason = "At least one static-mesh node is incomplete or fail-closed.";
                    return false;
                }
                if (node.meshPathId != -6840663686705882004L ||
                    !observedFilterIds.Add(node.meshFilterPathId) ||
                    !observedRendererIds.Add(node.meshRendererPathId))
                {
                    reason = "Static-mesh source identity is duplicated or mismatched.";
                    return false;
                }
                foreach (long materialPathId in node.materialPathIds)
                    observedMaterialIds.Add(materialPathId);
                if (node.generatedMeshFilter.sharedMesh == null ||
                    node.generatedMeshRenderer.enabled != node.sourceRendererEnabled ||
                    node.generatedMeshRenderer.sharedMaterials == null ||
                    node.generatedMeshRenderer.sharedMaterials.Length != node.materialPathIds.Length)
                {
                    reason = "Static mesh, renderer state, or material count drifted.";
                    return false;
                }
                foreach (Material material in node.generatedMeshRenderer.sharedMaterials)
                {
                    if (material == null || material.shader == null ||
                        material.shader.name.IndexOf("Unavailable", StringComparison.OrdinalIgnoreCase) >= 0 ||
                        material.shader.name.IndexOf("FailClosed", StringComparison.OrdinalIgnoreCase) >= 0)
                    {
                        reason = "Static-mesh material/shader is unresolved or fail-closed.";
                        return false;
                    }
                }
            }
            if (!observedFilterIds.SetEquals(expectedFilterIds) ||
                !observedRendererIds.SetEquals(expectedRendererIds) ||
                !observedMaterialIds.SetEquals(new long[] {
                    -6912999194325832649L,
                    2993445828574428557L,
                    3282333668994552481L }))
            {
                reason = "Li Zhiyan start_01 renderer/filter identity set drifted.";
                return false;
            }
            return true;
        }

        private void FailClosed(string code, string effectName, string reason)
        {
            if (rejectUnboundRequests || code != "unbound_effect_request")
            {
                Debug.LogWarning(
                    "[Endfield CharEffect] " + code + " for '" + effectName + "': " +
                    reason,
                    this);
            }
        }
    }
}
