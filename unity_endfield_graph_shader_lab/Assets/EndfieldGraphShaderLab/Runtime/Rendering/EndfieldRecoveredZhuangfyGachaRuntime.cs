using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Playables;
using UnityEngine.Rendering;
using UnityEngine.Timeline;

namespace EndfieldGraphShaderLab
{
    public enum EndfieldRecoveredEntityVFXKind
    {
        AdditiveMaterial = 0,
        Dissolve = 1,
    }

    [Serializable]
    public sealed class EndfieldRecoveredEntityVFXDefinition
    {
        public string assetName;
        public EndfieldRecoveredEntityVFXKind kind;
        public int rendererMask = -1;
        public bool useScaledTime;
        public bool loop;
        public float duration;
        public bool evaluateAtInitialZero;

        public Material additiveMaterial;
        public bool enableVertexColorIfMeshHasVFXVertexColor;
        public bool useStartCurve;
        public AnimationCurve startOpacityCurve = new AnimationCurve();

        public bool allowSimultaneous;
        public int dissolveUvSet;
        public bool useCutoffPositionY;
        public float cutoffUseDissolve;
        public bool stopShadowCasting;
        public bool stopRayTracingMeanTime;
        public float stopShadowCastingDelay;
        public float revertShadowCastingDelay;
        public Texture2D dissolveTexture;
        public Vector4 dissolveTextureST = new Vector4(1f, 1f, 0f, 0f);
        public float dissolveEdgeSharp;
        public Color dissolveEmissiveColor = Color.white;
        public float dissolveEmissiveEdge;
        public bool useLocalScreenUV;
        public AnimationCurve startDissolveCurve = new AnimationCurve();
        public bool useLoopCurve;
        public float loopDuration;
        public bool useEndCurve;
        public float endDuration;
    }

    /// <summary>
    /// Zhuang-only implementation of the native Timeline/EntityVFX branches
    /// that are closed by the two serialized contracts and retail IL2CPP CFG.
    /// It is intentionally not a reusable EntityVFX approximation.
    /// </summary>
    [DisallowMultipleComponent]
    public sealed class EndfieldRecoveredZhuangfyGachaRuntime : MonoBehaviour
    {
        // The native binary stores bytes 6f 12 83 3a and uses a strict SETA.
        public const float NativePlayableMinWeight = 0.0010000000474974513f;
        public const int NativeMaxAddedMaterialRecords = 4;
        public const string NativeCharacterDissolveKeyword = "VFX_CHARACTER_DISSOLVE";

        private static readonly int TintColorAlpha = Shader.PropertyToID("_TintColorAlpha");
        private static readonly int UseDissolve = Shader.PropertyToID("_UseDissolve");
        private static readonly int DissolveScheduleOffset = Shader.PropertyToID("_DissolveScheduleOffset");
        private static readonly int DissolveTex = Shader.PropertyToID("_DissolveTex");
        private static readonly int DissolveTexST = Shader.PropertyToID("_DissolveTex_ST");
        private static readonly int DissolveEdgeSharp = Shader.PropertyToID("_DissolveEdgeSharp");
        private static readonly int DissolveEmissiveColor = Shader.PropertyToID("_DissolveEmissiveColor");
        private static readonly int DissolveEmissiveEdge = Shader.PropertyToID("_DissolveEmissiveEdge");
        private static readonly int DissolveUseViewUV = Shader.PropertyToID("_DissolveUseViewUV");
        private static readonly int DissolveUVSet = Shader.PropertyToID("_DissolveUVSet");

        [Serializable]
        private sealed class AddedMaterialInstance
        {
            public Renderer renderer;
            public Material material;
        }

        [Serializable]
        private sealed class ReplacementMaterialInstance
        {
            public Renderer renderer;
            public Material[] materials = Array.Empty<Material>();
        }

        private sealed class RuntimeState
        {
            public EndfieldRecoveredEntityVFXDefinition definition;
            public readonly List<AddedMaterialInstance> addedMaterials = new List<AddedMaterialInstance>();
            public readonly List<ReplacementMaterialInstance> replacementMaterials =
                new List<ReplacementMaterialInstance>();
            public readonly Dictionary<Renderer, ShadowCastingMode> originalShadowModes =
                new Dictionary<Renderer, ShadowCastingMode>();
            public bool playing;
            public bool dissolveInitialized;
            public bool dissolveVisualFailClosed;
            public bool shadowStopped;
            public double lastEvaluationTime = double.NaN;
            public float selectedWeight;
        }

        public PlayableDirector director;
        public PlayableDirector actorCameraDirector;
        public bool autoStartRecoveredEffect = true;
        public float scaledPlayDelaySeconds = 0.25f;
        public double actorLoopStartTime = 10.7;
        public Transform exactRendererScopeRoot;
        public Renderer[] exactEligibleRenderers = Array.Empty<Renderer>();
        public EndfieldRecoveredEntityVFXDefinition[] definitions =
            Array.Empty<EndfieldRecoveredEntityVFXDefinition>();
        [TextArea] public string nativeOpenBoundary =
            "Runtime IFix patch payload and ray-tracing mean-time mutation remain source-open.";

        private readonly Dictionary<string, RuntimeState> states =
            new Dictionary<string, RuntimeState>(StringComparer.Ordinal);
        private readonly Dictionary<Renderer, Material[]> originalRendererMaterials =
            new Dictionary<Renderer, Material[]>();
        private readonly List<RuntimeState> activeAddedMaterialStates =
            new List<RuntimeState>();
        private RuntimeState activeDissolveState;
        private bool delayedPlayPending;
        private float delayedPlayDeadline;
        private EndfieldRecoveredGachaDirectorStartCoordinator directorStartCoordinator;
        private PlayableDirector lightStructuralDirector;
        private PlayableDirector othersStructuralDirector;
        private EndfieldRecoveredEmptyGachaHelperPlayableAsset lightStructuralAsset;
        private EndfieldRecoveredEmptyGachaHelperPlayableAsset othersStructuralAsset;
        private EndfieldHGOperatorLightRig sourceBackedOperatorLightRig;
        private EndfieldHGRPCharacterLightingVolume sourceBackedCharacterLightingVolume;
        private EndfieldRecoveredCharLightVolumeSnapshot sourceBackedVolumeSnapshot;
        private bool gateSourceBackedPresentation;
        private bool presentationLifecycleActive;
        private bool boundCharacterLightingEnabled;
        private bool inLoopTrack;
        private double triggerOnceTime = -1.0;
        private Action triggerOnceCallback;

        public event Action<bool> LoopTrackChanged;

        public bool InLoopTrack => inLoopTrack;

        public static bool IsNativeSampleActive(float weight)
        {
            return weight > NativePlayableMinWeight;
        }

        public int ActiveAddedMaterialInstanceCount
        {
            get { return states.Values.Sum(state => state.addedMaterials.Count); }
        }

        public int ActiveAddedMaterialRecordCount
        {
            get { return activeAddedMaterialStates.Count; }
        }

        public int AppliedAddedMaterialRecordCount
        {
            get { return Math.Min(NativeMaxAddedMaterialRecords, activeAddedMaterialStates.Count); }
        }

        public int ActiveDissolveReplacementMaterialCount
        {
            get
            {
                return activeDissolveState == null
                    ? 0
                    : activeDissolveState.replacementMaterials.Sum(item => item.materials.Length);
            }
        }

        public bool DelayedPlayPending
        {
            get { return delayedPlayPending; }
        }

        public float DelayedPlayDeadline
        {
            get { return delayedPlayDeadline; }
        }

        public bool IsShadowStopped(string assetName)
        {
            return states.TryGetValue(assetName, out RuntimeState state) && state.shadowStopped;
        }

        public bool IsDissolveVisualFailClosed(string assetName)
        {
            return states.TryGetValue(assetName, out RuntimeState state) && state.dissolveVisualFailClosed;
        }

        private void Awake()
        {
            EnsureStates();
        }

        private void Start()
        {
            if (autoStartRecoveredEffect)
                BeginRecoveredEffectStart(Time.time);
        }

        private void Update()
        {
            AdvanceRecoveredEffectStart(Time.time);
            TailTickRecoveredState();
        }

        private void OnDisable()
        {
            EndRecoveredEffect();
        }

        private void OnDestroy()
        {
            EndRecoveredEffect();
            if (lightStructuralAsset != null)
                Destroy(lightStructuralAsset);
            if (othersStructuralAsset != null)
                Destroy(othersStructuralAsset);
        }

        public bool BeginRecoveredEffectStart(float scaledTime)
        {
            delayedPlayPending = false;
            if (director == null || director.playableAsset == null ||
                actorCameraDirector == null ||
                actorCameraDirector.playableAsset == null ||
                scaledPlayDelaySeconds < 0f)
                return false;
            if (gateSourceBackedPresentation &&
                (sourceBackedOperatorLightRig == null ||
                 sourceBackedCharacterLightingVolume == null ||
                 sourceBackedVolumeSnapshot == null ||
                 sourceBackedOperatorLightRig.actorRoot == null ||
                 sourceBackedOperatorLightRig.normalLightCompatibilityScale != 0f ||
                 sourceBackedOperatorLightRig.rimLightCompatibilityScale != 0f))
            {
                CloseSourceBackedPresentation();
                return false;
            }
            try
            {
                OpenSourceBackedPresentation();
                if (!sourceBackedVolumeSnapshot.ApplyOnceTo(
                        sourceBackedCharacterLightingVolume))
                    throw new InvalidOperationException(
                        "Recovered CharLightVolumeData snapshot could not be copied.");
                EnsureDirectorStartCoordinator();
                inLoopTrack = false;
                directorStartCoordinator.SampleToBeginning();
                TailTickRecoveredState();
            }
            catch
            {
                CloseSourceBackedPresentation();
                throw;
            }
            // Public Unity 2022 does not invoke custom EntityVFX ProcessFrame
            // here after Stop, while the retail helper enters SampleToBeginning
            // with its child graph already constructed. Dispatch only the exact
            // source clips whose joined Timeline start is zero.
            DispatchSourceZeroStartEntityVFX();
            delayedPlayDeadline = scaledTime + scaledPlayDelaySeconds;
            delayedPlayPending = true;
            return true;
        }

        public void BindSourceBackedPresentation(
            EndfieldHGOperatorLightRig operatorLightRig,
            EndfieldHGRPCharacterLightingVolume characterLightingVolume)
        {
            sourceBackedOperatorLightRig = operatorLightRig;
            sourceBackedCharacterLightingVolume = characterLightingVolume;
            sourceBackedVolumeSnapshot = characterLightingVolume != null
                ? characterLightingVolume.GetComponent<EndfieldRecoveredCharLightVolumeSnapshot>()
                : null;
            boundCharacterLightingEnabled = characterLightingVolume != null &&
                characterLightingVolume.enabled;
            gateSourceBackedPresentation = true;
            presentationLifecycleActive = false;
            if (sourceBackedOperatorLightRig != null)
            {
                sourceBackedOperatorLightRig.SetRecoveredGachaPublicationState(
                    false,
                    false,
                    false);
            }
            if (sourceBackedCharacterLightingVolume != null)
                sourceBackedCharacterLightingVolume.enabled = false;
        }

        public void EndRecoveredEffect()
        {
            delayedPlayPending = false;
            directorStartCoordinator?.StopAll();
            ResetAllEntityVFX();
            CloseSourceBackedPresentation();
            triggerOnceTime = -1.0;
            triggerOnceCallback = null;
        }

        private void OpenSourceBackedPresentation()
        {
            if (!gateSourceBackedPresentation || presentationLifecycleActive)
                return;
            sourceBackedCharacterLightingVolume.enabled = true;
            sourceBackedOperatorLightRig.SetRecoveredGachaPublicationState(
                true,
                true,
                false);
            presentationLifecycleActive = true;
        }

        private void CloseSourceBackedPresentation()
        {
            presentationLifecycleActive = false;
            if (sourceBackedOperatorLightRig != null)
            {
                sourceBackedOperatorLightRig.SetRecoveredGachaPublicationState(
                    false,
                    false,
                    false);
            }
            if (sourceBackedCharacterLightingVolume != null)
                sourceBackedCharacterLightingVolume.enabled = boundCharacterLightingEnabled;
        }

        public bool AdvanceRecoveredEffectStart(float scaledTime)
        {
            if (!delayedPlayPending || scaledTime < delayedPlayDeadline)
                return false;
            delayedPlayPending = false;
            if (director == null || director.playableAsset == null ||
                actorCameraDirector == null ||
                actorCameraDirector.playableAsset == null)
                return false;
            EnsureDirectorStartCoordinator();
            inLoopTrack = false;
            directorStartCoordinator.PlayFromStart();
            DispatchSourceZeroStartEntityVFX();
            TailTickRecoveredState();
            return true;
        }

        public void SetRecoveredTriggerOnce(double time, Action callback)
        {
            triggerOnceTime = time;
            triggerOnceCallback = callback;
        }

        public void TailTickRecoveredState()
        {
            if (actorCameraDirector == null)
                return;
            double actorTime = actorCameraDirector.time;
            bool nextLoopState = actorTime >= actorLoopStartTime;
            if (nextLoopState != inLoopTrack)
            {
                inLoopTrack = nextLoopState;
                LoopTrackChanged?.Invoke(inLoopTrack);
            }
            if (triggerOnceCallback != null && actorTime >= triggerOnceTime)
            {
                Action callback = triggerOnceCallback;
                triggerOnceTime = -1.0;
                triggerOnceCallback = null;
                callback();
            }
        }

        private void EnsureDirectorStartCoordinator()
        {
            if (directorStartCoordinator != null)
                return;
            lightStructuralDirector = EnsureStructuralEmptyDirector(
                EndfieldRecoveredGachaDirectorRole.Light,
                "Light",
                -5654231416230730172L,
                "CAB-2e7efde638026cbecddde6018788eae0",
                ref lightStructuralAsset);
            othersStructuralDirector = EnsureStructuralEmptyDirector(
                EndfieldRecoveredGachaDirectorRole.Others,
                "Others",
                3821394883651479761L,
                "CAB-758541911c26bfe46db18814d7af3f90",
                ref othersStructuralAsset);
            directorStartCoordinator = new EndfieldRecoveredGachaDirectorStartCoordinator(
                new[]
                {
                    new EndfieldRecoveredGachaDirectorBinding
                    {
                        role = EndfieldRecoveredGachaDirectorRole.Actor,
                        sourceOrdinal = 0,
                        director = actorCameraDirector,
                    },
                    new EndfieldRecoveredGachaDirectorBinding
                    {
                        role = EndfieldRecoveredGachaDirectorRole.Effect,
                        sourceOrdinal = 2,
                        director = director,
                    },
                    new EndfieldRecoveredGachaDirectorBinding
                    {
                        role = EndfieldRecoveredGachaDirectorRole.Light,
                        sourceOrdinal = 3,
                        director = lightStructuralDirector,
                    },
                    new EndfieldRecoveredGachaDirectorBinding
                    {
                        role = EndfieldRecoveredGachaDirectorRole.Others,
                        sourceOrdinal = 4,
                        director = othersStructuralDirector,
                    },
                });
        }

        private PlayableDirector EnsureStructuralEmptyDirector(
            EndfieldRecoveredGachaDirectorRole role,
            string ownerName,
            long sourcePathId,
            string sourceSerializedFile,
            ref EndfieldRecoveredEmptyGachaHelperPlayableAsset asset)
        {
            Transform owner = transform.Find(ownerName);
            if (owner == null)
            {
                var ownerObject = new GameObject(ownerName);
                ownerObject.transform.SetParent(transform, false);
                owner = ownerObject.transform;
            }
            PlayableDirector helper = owner.GetComponent<PlayableDirector>();
            if (helper == null)
                helper = owner.gameObject.AddComponent<PlayableDirector>();
            if (helper.playableAsset != null &&
                !(helper.playableAsset is EndfieldRecoveredEmptyGachaHelperPlayableAsset))
            {
                throw new InvalidOperationException(
                    $"Recovered empty {role} helper already owns an unvalidated PlayableAsset.");
            }
            if (asset == null)
            {
                asset = ScriptableObject.CreateInstance<
                    EndfieldRecoveredEmptyGachaHelperPlayableAsset>();
                asset.name = $"gacha_char_zhuangfy_{ownerName}";
                asset.role = role;
                asset.sourcePathId = sourcePathId;
                asset.sourceSerializedFile = sourceSerializedFile;
            }
            helper.playOnAwake = false;
            helper.timeUpdateMode = DirectorUpdateMode.GameTime;
            helper.extrapolationMode = DirectorWrapMode.None;
            helper.playableAsset = asset;
            return helper;
        }

        private void DispatchSourceZeroStartEntityVFX()
        {
            EnsureStates();
            foreach (EndfieldRecoveredEntityVFXDefinition definition in definitions)
            {
                if (definition == null || !definition.evaluateAtInitialZero)
                    continue;
                // The original tracks begin exactly at zero with no blend and
                // therefore enter SampleVFX at full effective weight. The
                // strict same-evaluation weight gate makes this idempotent if
                // the public Timeline implementation already processed them.
                SampleEntityVFX(definition.assetName, 0f, false, 1f, 0f);
            }
        }

        private void EnsureStates()
        {
            if (states.Count > 0)
                return;
            foreach (EndfieldRecoveredEntityVFXDefinition definition in definitions)
            {
                if (definition == null || string.IsNullOrEmpty(definition.assetName) ||
                    states.ContainsKey(definition.assetName))
                    continue;
                states.Add(definition.assetName, new RuntimeState { definition = definition });
            }
        }

        public void SampleEntityVFX(
            string assetName,
            float time,
            bool ending,
            float weight,
            float clipStartTime)
        {
            EnsureStates();
            if (!states.TryGetValue(assetName, out RuntimeState state))
                return; // Unknown assets fail closed.
            if (!IsNativeSampleActive(weight))
            {
                // Native _SampleVFX dispatches Stop(force=true) when the
                // strict gate becomes inactive and the controller is playing.
                if (state.playing)
                    FinalStop(state);
                return;
            }

            double evaluationTime = director != null ? director.time : Time.frameCount;
            if (!DoubleEquals(state.lastEvaluationTime, evaluationTime))
            {
                state.lastEvaluationTime = evaluationTime;
                state.selectedWeight = -1f;
            }
            // Native SampleVFX replaces only for a strictly greater weight.
            if (!(weight > state.selectedWeight))
                return;
            state.selectedWeight = weight;

            if (!state.playing)
                Play(state);
            if (!state.playing)
                return;

            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            if (ending)
            {
                // All five exact Zhuang assets disable their end curves.
                if (definition.useEndCurve && definition.endDuration > 0f)
                    FailClosedState(state);
                return;
            }

            if (definition.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial)
                SampleAdditiveStart(state, time);
            else if (definition.kind == EndfieldRecoveredEntityVFXKind.Dissolve)
                SampleDissolve(state, time);
        }

        public void ResetEntityVFX(string assetName)
        {
            EnsureStates();
            if (states.TryGetValue(assetName, out RuntimeState state))
                FinalStop(state);
        }

        public void ResetAllEntityVFX()
        {
            EnsureStates();
            foreach (RuntimeState state in states.Values)
                FinalStop(state);
        }

        private void Play(RuntimeState state)
        {
            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            if (definition.rendererMask != -1 || exactRendererScopeRoot == null ||
                exactEligibleRenderers == null || exactEligibleRenderers.Length == 0 ||
                exactEligibleRenderers.Any(renderer =>
                    renderer == null || !renderer.transform.IsChildOf(exactRendererScopeRoot)))
            {
                FailClosedState(state);
                return;
            }

            state.playing = true;
            state.dissolveInitialized = false;
            state.dissolveVisualFailClosed = false;
            if (definition.kind == EndfieldRecoveredEntityVFXKind.AdditiveMaterial)
            {
                if (definition.additiveMaterial == null || !definition.useStartCurve ||
                    definition.startOpacityCurve == null || definition.startOpacityCurve.length == 0 ||
                    !definition.enableVertexColorIfMeshHasVFXVertexColor)
                {
                    FailClosedState(state);
                    return;
                }
                if (!CaptureOriginalRendererMaterials())
                {
                    FailClosedState(state);
                    return;
                }
                foreach (Renderer renderer in exactEligibleRenderers)
                {
                    // Retail Play clones for the start-curve path, retains the
                    // AddMaterial handle, gathers inserted customized instances,
                    // and mutates those instances rather than the shared source.
                    Material clone = new Material(definition.additiveMaterial)
                    {
                        name = definition.additiveMaterial.name + " (Recovered EntityVFX Instance)"
                    };
                    if (!clone.HasProperty(TintColorAlpha))
                    {
                        DestroyMaterial(clone);
                        foreach (AddedMaterialInstance created in state.addedMaterials)
                            DestroyMaterial(created.material);
                        state.addedMaterials.Clear();
                        FailClosedState(state);
                        return;
                    }
                    state.addedMaterials.Add(new AddedMaterialInstance
                    {
                        renderer = renderer,
                        material = clone,
                    });
                }
                activeAddedMaterialStates.Add(state);
                RebuildSharedMaterialArrays();
            }
        }

        private bool CaptureOriginalRendererMaterials()
        {
            foreach (Renderer renderer in exactEligibleRenderers)
            {
                if (renderer == null)
                    return false;
                if (originalRendererMaterials.ContainsKey(renderer))
                    continue;
                Material[] originals = renderer.sharedMaterials;
                if (originals == null || originals.Length == 0 || originals.Any(material => material == null))
                    return false;
                originalRendererMaterials.Add(renderer, (Material[])originals.Clone());
            }
            return true;
        }

        private void RebuildSharedMaterialArrays()
        {
            foreach (Renderer renderer in exactEligibleRenderers)
            {
                if (renderer == null || !originalRendererMaterials.TryGetValue(renderer, out Material[] originals))
                    continue;

                var rebuilt = new List<Material>();
                int accepted = 0;
                for (int stateIndex = activeAddedMaterialStates.Count - 1;
                    stateIndex >= 0 && accepted < NativeMaxAddedMaterialRecords;
                    stateIndex--)
                {
                    RuntimeState active = activeAddedMaterialStates[stateIndex];
                    AddedMaterialInstance instance = active.addedMaterials.FirstOrDefault(item =>
                        item.renderer == renderer && item.material != null);
                    if (instance == null)
                        continue;

                    // Native ApplySharedMaterialArray emits accepted records
                    // newest-first, once per source material/submesh slot, then
                    // appends the complete original shared-material array.
                    for (int slot = 0; slot < originals.Length; slot++)
                        rebuilt.Add(instance.material);
                    accepted++;
                }
                rebuilt.AddRange(originals);
                if (activeDissolveState != null)
                {
                    ReplacementMaterialInstance replacement =
                        activeDissolveState.replacementMaterials.FirstOrDefault(item =>
                            item.renderer == renderer);
                    if (replacement != null && replacement.materials.Length == originals.Length)
                    {
                        rebuilt.RemoveRange(rebuilt.Count - originals.Length, originals.Length);
                        rebuilt.AddRange(replacement.materials);
                    }
                }
                renderer.sharedMaterials = rebuilt.ToArray();
            }
        }

        private static void SampleAdditiveStart(RuntimeState state, float passTime)
        {
            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            // Exact specialization: loop=false and only start opacity is enabled.
            if (definition.loop || !definition.useStartCurve || definition.duration <= 0f)
            {
                FailClosedState(state);
                return;
            }
            float normalized = Mathf.Clamp01(passTime / definition.duration);
            float opacity = definition.startOpacityCurve.Evaluate(normalized);
            foreach (AddedMaterialInstance instance in state.addedMaterials)
            {
                if (instance.material != null)
                    instance.material.SetFloat(TintColorAlpha, opacity);
            }
        }

        private void SampleDissolve(RuntimeState state, float passTime)
        {
            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            if (!definition.loop || definition.duration <= 0f || definition.useCutoffPositionY ||
                definition.useLoopCurve || definition.useEndCurve ||
                definition.startDissolveCurve == null || definition.startDissolveCurve.length == 0)
            {
                FailClosedState(state);
                return;
            }

            // Native OnSample uses Start only before duration.  With loop=true,
            // useLoopCurve=false, and useCutOffPosY=false, Loop writes nothing.
            if (passTime < definition.duration)
            {
                UpdateShadowCasting(state, passTime);
                float normalized = Mathf.Clamp01(passTime / definition.duration);
                float schedule = definition.startDissolveCurve.Evaluate(normalized);
                ApplyDissolve(state, schedule, !state.dissolveInitialized);
                state.dissolveInitialized = true;
            }
        }

        private void UpdateShadowCasting(RuntimeState state, float passTime)
        {
            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            if (!definition.stopShadowCasting)
                return;
            if (!state.shadowStopped && passTime >= definition.stopShadowCastingDelay &&
                passTime < definition.revertShadowCastingDelay)
            {
                foreach (Renderer renderer in exactEligibleRenderers)
                {
                    state.originalShadowModes[renderer] = renderer.shadowCastingMode;
                    renderer.shadowCastingMode = ShadowCastingMode.Off;
                }
                state.shadowStopped = true;
                // stopRayTracingMeanTime is preserved in the definition but the
                // retail helper's mean-time mutation is not guessed here.
            }
            else if (state.shadowStopped && passTime > definition.revertShadowCastingDelay)
            {
                RestoreShadow(state);
            }
        }

        private void ApplyDissolve(RuntimeState state, float schedule, bool initialize)
        {
            EndfieldRecoveredEntityVFXDefinition definition = state.definition;
            if (initialize && !EnsureDissolveReplacementMaterials(state))
                return;
            if (!ReferenceEquals(activeDissolveState, state))
                return;

            foreach (ReplacementMaterialInstance replacement in state.replacementMaterials)
            {
                foreach (Material material in replacement.materials)
                {
                    SetFloatIfSupported(material, DissolveScheduleOffset, schedule);
                    if (initialize)
                    {
                        // The installed normal EntityRenderHelper chain reaches
                        // MeshMaterialController._TryEnsureReplaceMaterial and
                        // then Material EnableKeyword/Set* calls. It does not
                        // use Renderer.SetPropertyBlock or custom-per-draw data.
                        material.EnableKeyword(NativeCharacterDissolveKeyword);
                        SetFloatIfSupported(material, UseDissolve, 1f);
                        SetTextureIfSupported(material, DissolveTex, definition.dissolveTexture);
                        SetVectorIfSupported(material, DissolveTexST, definition.dissolveTextureST);
                        SetFloatIfSupported(
                            material,
                            DissolveEdgeSharp,
                            definition.dissolveEdgeSharp);
                        SetColorIfSupported(
                            material,
                            DissolveEmissiveColor,
                            definition.dissolveEmissiveColor);
                        SetFloatIfSupported(
                            material,
                            DissolveEmissiveEdge,
                            definition.dissolveEmissiveEdge);
                        SetFloatIfSupported(
                            material,
                            DissolveUseViewUV,
                            definition.useLocalScreenUV ? 1f : 0f);
                        SetFloatIfSupported(material, DissolveUVSet, definition.dissolveUvSet);
                    }
                }
            }
        }

        private bool EnsureDissolveReplacementMaterials(RuntimeState state)
        {
            if (ReferenceEquals(activeDissolveState, state))
                return true;
            if (activeDissolveState != null || state.replacementMaterials.Count > 0 ||
                !CaptureOriginalRendererMaterials())
            {
                state.dissolveVisualFailClosed = true;
                return false;
            }

            bool fullySupported = originalRendererMaterials.Values.All(materials =>
                materials.Length > 0 && materials.All(IsDissolveMaterialSupported));
            if (!fullySupported)
                state.dissolveVisualFailClosed = true;

            foreach (Renderer renderer in exactEligibleRenderers)
            {
                Material[] originals = originalRendererMaterials[renderer];
                var replacements = new Material[originals.Length];
                for (int index = 0; index < originals.Length; index++)
                {
                    replacements[index] = new Material(originals[index])
                    {
                        name = originals[index].name +
                            " (Recovered EntityVFX Replacement)"
                    };
                }
                state.replacementMaterials.Add(new ReplacementMaterialInstance
                {
                    renderer = renderer,
                    materials = replacements,
                });
            }

            activeDissolveState = state;
            RebuildSharedMaterialArrays();
            return true;
        }

        private static bool IsDissolveMaterialSupported(Material material)
        {
            return material != null &&
                material.HasProperty(UseDissolve) &&
                material.HasProperty(DissolveScheduleOffset) &&
                material.HasProperty(DissolveTex) &&
                material.HasProperty(DissolveTexST) &&
                material.HasProperty(DissolveEdgeSharp) &&
                material.HasProperty(DissolveEmissiveColor) &&
                material.HasProperty(DissolveEmissiveEdge) &&
                material.HasProperty(DissolveUseViewUV) &&
                material.HasProperty(DissolveUVSet);
        }

        private static void ResetDissolveMaterialValues(RuntimeState state)
        {
            foreach (ReplacementMaterialInstance replacement in state.replacementMaterials)
            {
                foreach (Material material in replacement.materials)
                {
                    if (material == null)
                        continue;
                    material.DisableKeyword(NativeCharacterDissolveKeyword);
                    SetFloatIfSupported(material, DissolveScheduleOffset, 0f);
                    SetTextureIfSupported(material, DissolveTex, null);
                    SetVectorIfSupported(
                        material,
                        DissolveTexST,
                        new Vector4(1f, 1f, 0f, 0f));
                    SetFloatIfSupported(material, DissolveEdgeSharp, 0f);
                    SetColorIfSupported(material, DissolveEmissiveColor, Color.white);
                    SetFloatIfSupported(material, DissolveEmissiveEdge, 0f);
                    SetFloatIfSupported(material, DissolveUseViewUV, 0f);
                }
            }
        }

        private static void SetFloatIfSupported(Material material, int property, float value)
        {
            if (material.HasProperty(property))
                material.SetFloat(property, value);
        }

        private static void SetTextureIfSupported(Material material, int property, Texture value)
        {
            if (material.HasProperty(property))
                material.SetTexture(property, value);
        }

        private static void SetVectorIfSupported(Material material, int property, Vector4 value)
        {
            if (material.HasProperty(property))
                material.SetVector(property, value);
        }

        private static void SetColorIfSupported(Material material, int property, Color value)
        {
            if (material.HasProperty(property))
                material.SetColor(property, value);
        }

        private static void FailClosedState(RuntimeState state)
        {
            state.playing = false;
        }

        private void FinalStop(RuntimeState state)
        {
            bool wasAddedMaterial = activeAddedMaterialStates.Remove(state);
            bool wasDissolve = ReferenceEquals(activeDissolveState, state);
            if (wasDissolve)
            {
                ResetDissolveMaterialValues(state);
                activeDissolveState = null;
            }
            if (wasAddedMaterial || wasDissolve)
                RebuildSharedMaterialArrays();
            foreach (AddedMaterialInstance instance in state.addedMaterials)
            {
                DestroyMaterial(instance.material);
            }
            state.addedMaterials.Clear();
            foreach (ReplacementMaterialInstance replacement in state.replacementMaterials)
            {
                foreach (Material material in replacement.materials)
                    DestroyMaterial(material);
            }
            state.replacementMaterials.Clear();
            ReleaseOriginalRendererMaterialsIfUnused();
            RestoreShadow(state);
            state.playing = false;
            state.dissolveInitialized = false;
            state.dissolveVisualFailClosed = false;
            state.lastEvaluationTime = double.NaN;
            state.selectedWeight = -1f;
        }

        private void ReleaseOriginalRendererMaterialsIfUnused()
        {
            if (activeAddedMaterialStates.Count == 0 && activeDissolveState == null)
                originalRendererMaterials.Clear();
        }

        private static void RestoreShadow(RuntimeState state)
        {
            foreach (KeyValuePair<Renderer, ShadowCastingMode> pair in state.originalShadowModes)
            {
                if (pair.Key != null)
                    pair.Key.shadowCastingMode = pair.Value;
            }
            state.originalShadowModes.Clear();
            state.shadowStopped = false;
        }

        private static void DestroyMaterial(Material material)
        {
            if (material == null)
                return;
            if (Application.isPlaying)
                UnityEngine.Object.Destroy(material);
            else
                UnityEngine.Object.DestroyImmediate(material);
        }

        private static bool DoubleEquals(double a, double b)
        {
            return Math.Abs(a - b) <= 1.0e-9;
        }
    }

}
