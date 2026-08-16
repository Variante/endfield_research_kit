using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Animations;
using UnityEngine.Playables;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// A deliberately non-retail animation preview for the serialized Li
    /// Zhiyan EffectSetting entrance clip.
    ///
    /// The installed client creates an AdvancedAnimationMixerPlayable and has
    /// an unresolved native stage-table path.  This component therefore uses
    /// Unity's stock AnimationMixerPlayable only as a behavioural simulation:
    /// it preserves the proven three-input/slot-zero control shape, but never
    /// presents that shape as the retail ABI, a native renderer bridge, or a
    /// visible-admission decision.
    /// </summary>
    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Character Recovery/Li Zhiyan Behavioral Animation Simulation")]
    public sealed class EndfieldLiZhiyanBehavioralAnimationSimulation : MonoBehaviour
    {
        public const string SimulationMode = "behavioral_simulation";
        public const string BackendDescription = "stock AnimationMixerPlayable";
        public const string RetailAbiRefusal =
            "Stock AnimationMixerPlayable is not the retail AdvancedAnimationMixerPlayable ABI.";
        public const string VisibleAdmissionRefusal =
            "Behavioral simulation never admits retail-visible native rendering.";
        public const string NativeMappingRefusal =
            "Renderer instance identity is diagnostic only; no native HGTree mapping is claimed.";

        [Header("Serialized source identity")]
        [SerializeField]
        private string sourceEffectRoot = "P_fxui_lizhiyan_overview_start_01";

        [SerializeField]
        private long sourceEffectSettingPathId = 2305038813790631653L;

        [SerializeField]
        private long sourceStartAnimationClipPathId = 7360398354216100382L;

        [SerializeField]
        private AnimationClip sourceStartAnimationClip;

        [SerializeField]
        [Min(0.0001f)]
        private float effectSettingLifetime = 2.2f;

        [SerializeField]
        private bool playOnEnable = true;

        [Header("Optional source contract for renderer diagnostics")]
        [SerializeField]
        private EndfieldRecoveredStaticMeshEffectSource sourceContract;

        [SerializeField]
        private RendererProbeBinding[] rendererProbeBindings =
            Array.Empty<RendererProbeBinding>();

        private PlayableGraph graph;
        private AnimationMixerPlayable mixer;
        private AnimationClipPlayable clipPlayable;
        private AnimationPlayableOutput output;
        private bool graphWasPlayed;
        private bool lifetimeExpired;
        private float elapsedLifetime;
        private readonly List<RendererIdentityProbeRecord> rendererIdentityProbeRecords =
            new List<RendererIdentityProbeRecord>();

        /// <summary>
        /// Explicitly labels this component's only supported execution mode.
        /// </summary>
        public string Mode => SimulationMode;

        public string Backend => BackendDescription;

        public string SourceEffectRoot => sourceEffectRoot;

        public long SourceEffectSettingPathId => sourceEffectSettingPathId;

        public long SourceStartAnimationClipPathId => sourceStartAnimationClipPathId;

        public AnimationClip SourceStartAnimationClip => sourceStartAnimationClip;

        public float EffectSettingLifetime => effectSettingLifetime;

        public bool UsesGameTime => true;

        public bool RetailAbiEquivalent => false;

        public bool VisibleAdmission => false;

        public bool NativeRendererMappingClaimed => false;

        public bool GraphWasPlayed => graphWasPlayed;

        public bool LifetimeExpired => lifetimeExpired;

        public float ElapsedLifetime => elapsedLifetime;

        public bool GraphIsValid => graph.IsValid();

        public int GraphInputCount => GraphIsValid ? mixer.GetInputCount() : 0;

        public int ConnectedInputCount
        {
            get
            {
                if (!GraphIsValid)
                    return 0;

                int connected = 0;
                for (int index = 0; index < mixer.GetInputCount(); index++)
                {
                    if (mixer.GetInput(index).IsValid())
                        connected++;
                }
                return connected;
            }
        }

        public float InputWeight0 => GetInputWeight(0);

        public float InputWeight1 => GetInputWeight(1);

        public float InputWeight2 => GetInputWeight(2);

        public double MixerTime => GraphIsValid ? mixer.GetTime() : -1.0;

        public double MixerSpeed => GraphIsValid ? mixer.GetSpeed() : -1.0;

        /// <summary>
        /// The records are read-only to callers.  The integer is Unity's
        /// managed instance ID only; it is intentionally not an HGTree or
        /// renderer-list identity.
        /// </summary>
        public IReadOnlyList<RendererIdentityProbeRecord> RendererIdentityProbes =>
            rendererIdentityProbeRecords;

        public IReadOnlyList<RendererProbeBinding> RendererProbeBindings =>
            rendererProbeBindings;

        private void OnEnable()
        {
            if (playOnEnable)
                TryConstructSimulation(out _);
        }

        private void Update()
        {
            AdvanceLifetime(Time.deltaTime);
        }

        private void OnDisable()
        {
            DestroySimulationGraph();
        }

        private void OnDestroy()
        {
            DestroySimulationGraph();
        }

        /// <summary>
        /// Builds the intentionally limited stock graph.  Exactly three
        /// inputs are created, only slot 0 is connected, and all weights are
        /// set explicitly to [1, 0, 0].
        /// </summary>
        public bool TryConstructSimulation(out string reason)
        {
            reason = string.Empty;
            DestroySimulationGraph();
            graphWasPlayed = false;
            lifetimeExpired = false;
            elapsedLifetime = 0f;

            if (string.IsNullOrEmpty(sourceEffectRoot))
            {
                reason = "source effect root is empty";
                return false;
            }
            if (sourceEffectSettingPathId == 0L)
            {
                reason = "source EffectSetting PathID is missing";
                return false;
            }
            if (sourceStartAnimationClipPathId == 0L)
            {
                reason = "source animation clip PathID is missing";
                return false;
            }
            if (sourceStartAnimationClip == null)
            {
                reason = "source animation clip is not assigned";
                return false;
            }
            if (sourceStartAnimationClip.legacy)
            {
                reason = "legacy AnimationClip cannot drive the Animator Playables output";
                return false;
            }
            if (effectSettingLifetime <= 0f || float.IsNaN(effectSettingLifetime) ||
                float.IsInfinity(effectSettingLifetime))
            {
                reason = "EffectSetting lifetime must be finite and greater than zero";
                return false;
            }

            Animator animator = GetComponent<Animator>();
            if (animator == null)
            {
                reason = "an Animator is required for the AnimationPlayableOutput";
                return false;
            }

            graph = PlayableGraph.Create(
                "LiZhiyan." + sourceEffectRoot + "." + SimulationMode);
            graph.SetTimeUpdateMode(DirectorUpdateMode.GameTime);

            mixer = AnimationMixerPlayable.Create(graph, 3);
            clipPlayable = AnimationClipPlayable.Create(graph, sourceStartAnimationClip);
            output = AnimationPlayableOutput.Create(
                graph,
                "Li Zhiyan behavioral simulation",
                animator);

            // The native source proves a three-slot mixer shape, but does not
            // prove the custom stage table.  Keep only the source-backed start
            // clip connected; slots 1 and 2 remain intentionally unconnected.
            graph.Connect(clipPlayable, 0, mixer, 0);
            mixer.SetInputWeight(0, 1f);
            mixer.SetInputWeight(1, 0f);
            mixer.SetInputWeight(2, 0f);
            mixer.SetSpeed(1.0);
            clipPlayable.SetSpeed(1.0);
            output.SetSourcePlayable(mixer);

            // Match the proven managed control sequence: Play followed by a
            // zero-time start.  This is still only stock graph behaviour.
            graph.Play();
            graphWasPlayed = true;
            clipPlayable.SetTime(0.0);
            mixer.SetTime(0.0);

            CaptureRendererIdentityProbe();
            return true;
        }

        /// <summary>
        /// Refuses any caller that attempts to promote this graph to the
        /// unresolved retail ABI.
        /// </summary>
        public bool TryAdmitRetailAbi(out string reason)
        {
            reason = RetailAbiRefusal;
            return false;
        }

        /// <summary>
        /// Refuses visible/native admission even when the behavioural graph is
        /// successfully constructed.
        /// </summary>
        public bool TryAdmitVisibleRendering(out string reason)
        {
            reason = VisibleAdmissionRefusal;
            return false;
        }

        /// <summary>
        /// Refuses an inferred renderer-to-HGTree/native-list mapping.  The
        /// probe records remain useful for a future runtime capture only.
        /// </summary>
        public bool TryMapRendererToNativeRecord(
            int unityRendererInstanceId,
            out string reason)
        {
            reason = NativeMappingRefusal;
            return false;
        }

        /// <summary>
        /// Captures the current managed renderer identity without exporting it
        /// as a native renderer/entity identity.  Repeated calls replace the
        /// read-only snapshot and stamp the current Unity frame.
        /// </summary>
        public void CaptureRendererIdentityProbe()
        {
            rendererIdentityProbeRecords.Clear();
            int frame = Time.frameCount;

            if (rendererProbeBindings != null && rendererProbeBindings.Length > 0)
            {
                foreach (RendererProbeBinding binding in rendererProbeBindings)
                {
                    if (binding == null || binding.Renderer == null)
                        continue;
                    rendererIdentityProbeRecords.Add(
                        new RendererIdentityProbeRecord(
                            binding.SourceRendererPathId,
                            binding.Hierarchy,
                            binding.Renderer.GetInstanceID(),
                            frame));
                }
                return;
            }

            if (sourceContract == null || sourceContract.staticMeshNodes == null)
                return;

            foreach (EndfieldRecoveredStaticMeshNodeSource node in
                sourceContract.staticMeshNodes)
            {
                if (node == null || node.generatedMeshRenderer == null)
                    continue;
                rendererIdentityProbeRecords.Add(
                    new RendererIdentityProbeRecord(
                        node.meshRendererPathId,
                        node.hierarchy,
                        node.generatedMeshRenderer.GetInstanceID(),
                        frame));
            }
        }

        /// <summary>
        /// Advances only the EffectSetting lifetime gate.  It is public so an
        /// Editor validator can test destruction deterministically without
        /// pretending that an Editor update is a retail frame.
        /// </summary>
        public bool AdvanceLifetimeForValidation(float deltaTime)
        {
            return AdvanceLifetime(deltaTime);
        }

        public void ConfigureSourceIdentity(
            string effectRoot,
            long effectSettingPathId,
            long animationClipPathId,
            AnimationClip animationClip,
            float lifetime)
        {
            sourceEffectRoot = effectRoot;
            sourceEffectSettingPathId = effectSettingPathId;
            sourceStartAnimationClipPathId = animationClipPathId;
            sourceStartAnimationClip = animationClip;
            effectSettingLifetime = lifetime;
        }

        public void ConfigureRendererProbeBindings(
            RendererProbeBinding[] bindings)
        {
            rendererProbeBindings = bindings ?? Array.Empty<RendererProbeBinding>();
        }

        private float GetInputWeight(int index)
        {
            return GraphIsValid && index >= 0 && index < mixer.GetInputCount()
                ? mixer.GetInputWeight(index)
                : -1f;
        }

        private bool AdvanceLifetime(float deltaTime)
        {
            if (!GraphIsValid || lifetimeExpired)
                return false;

            if (deltaTime < 0f || float.IsNaN(deltaTime) || float.IsInfinity(deltaTime))
                return false;

            elapsedLifetime += deltaTime;
            if (elapsedLifetime + 1e-6f < effectSettingLifetime)
                return true;

            lifetimeExpired = true;
            DestroySimulationGraph();
            return false;
        }

        private void DestroySimulationGraph()
        {
            if (!graph.IsValid())
                return;

            graph.Stop();
            graph.Destroy();
            graphWasPlayed = false;
        }

        [Serializable]
        public sealed class RendererProbeBinding
        {
            [SerializeField]
            private long sourceRendererPathId;

            [SerializeField]
            private string hierarchy;

            [SerializeField]
            private Renderer renderer;

            public RendererProbeBinding() { }

            public RendererProbeBinding(
                long sourceRendererPathId,
                string hierarchy,
                Renderer renderer)
            {
                this.sourceRendererPathId = sourceRendererPathId;
                this.hierarchy = hierarchy;
                this.renderer = renderer;
            }

            public long SourceRendererPathId => sourceRendererPathId;

            public string Hierarchy => hierarchy;

            public Renderer Renderer => renderer;
        }

        [Serializable]
        public sealed class RendererIdentityProbeRecord
        {
            [SerializeField]
            private long sourceRendererPathId;

            [SerializeField]
            private string hierarchy;

            [SerializeField]
            private int unityRendererInstanceId;

            [SerializeField]
            private int frame;

            internal RendererIdentityProbeRecord(
                long sourceRendererPathId,
                string hierarchy,
                int unityRendererInstanceId,
                int frame)
            {
                this.sourceRendererPathId = sourceRendererPathId;
                this.hierarchy = hierarchy;
                this.unityRendererInstanceId = unityRendererInstanceId;
                this.frame = frame;
            }

            public long SourceRendererPathId => sourceRendererPathId;

            public string Hierarchy => hierarchy;

            public int UnityRendererInstanceId => unityRendererInstanceId;

            public int Frame => frame;

            public bool NativeMappingClaimed => false;
        }
    }
}
