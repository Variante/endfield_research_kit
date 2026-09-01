using System.Collections;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    [System.Serializable]
    public struct EndfieldOverviewEffectRequest
    {
        public string prefabName;
        public string mountPoint;
        public bool finishWhenExit;
        public bool finishWhenTransition;
    }

    public struct EndfieldOverviewEffectSourceClock
    {
        internal EndfieldOverviewPlayback owner;
        internal int playbackGeneration;
        internal int stateFullPathHash;
        internal float elapsedSeconds;
        internal bool valid;
    }

    [System.Serializable]
    public struct EndfieldOverviewItemWidgetBinding
    {
        public string propPath;
        public string startClip;
        public string loopClip;
        [Tooltip("Controller-proven state entered after the overview entrance when no settled loop is used.")]
        public string postTransitionClip;
        public bool hideAfterTransition;
        [Tooltip("Source evidence used to associate this widget with the overview state.")]
        public string activationEvidence;
    }

    [System.Serializable]
    public struct EndfieldOverviewTransitionCondition
    {
        public int mode;
        public string parameter;
        public float threshold;
    }

    public interface IEndfieldOverviewParameterConsumer
    {
        void ApplyOverviewParameters(
            float weaponHide,
            float magicaClothWeight,
            float staticWeaponHide);
    }

    public interface IEndfieldOverviewParameterResetConsumer
    {
        void RestoreOverviewParameters();
    }

    public interface IEndfieldOverviewEffectSpawner
    {
        void SpawnOverviewEffect(
            EndfieldOverviewEffectRequest request,
            Transform actorRoot,
            EndfieldOverviewEffectSourceClock sourceClock);
        void FinishOverviewEffect(string prefabName);
    }

    /// <summary>
    /// Reconstructs the recovered operator Overview entry -> idle transition,
    /// including source-bound private-rig item widgets, while the lab still
    /// uses legacy Animation clips. FX and Magica Cloth consumers remain
    /// separate dependencies.
    /// </summary>
    [DisallowMultipleComponent]
    [RequireComponent(typeof(Animation))]
    [DefaultExecutionOrder(-80)]
    public sealed class EndfieldOverviewPlayback : MonoBehaviour
    {
        public const int SourceOverviewStartFullPathHash = 1560421867;

        [Header("Recovered clips")]
        public Animation animationSource;
        [Tooltip("Generated source-exact Animator used by automatic Overview playback. Manual clip browsing still uses animationSource.")]
        public Animator animatorSource;
        public string startClip = "A_actor_zhuangfy_ui_overview_start_01";
        public string loopClip = "A_actor_zhuangfy_ui_overview_loop_01";
        public bool playOnEnable = true;

        [Header("Recovered Animator contract")]
        [Tooltip("Fail closed instead of falling back to Legacy Animation when the generated Animator contract is absent or stale.")]
        public bool requireAnimatorContract;
        public string animatorStartStatePath = "Base Layer.Overview.FromOveview";
        public string animatorLoopStatePath = "Base Layer.Overview.OverviewIdle";

        [Header("Recovered item widgets")]
        [Tooltip("Source-bound UI item widgets. Each widget plays on its own Animation layer.")]
        public EndfieldOverviewItemWidgetBinding[] itemWidgets =
            System.Array.Empty<EndfieldOverviewItemWidgetBinding>();

        [Header("Legacy entrance companion")]
        [Tooltip("Controller-proven private-rig clip paired only with the overview entrance.")]
        public string entranceCompanionClip;
        public string entranceCompanionPropPath;
        [Tooltip("The widget03 settled loop has no proven activation state, so the entrance prop is hidden after handoff.")]
        public bool hideEntranceCompanionAfterTransition = true;

        [Header("Recovered controller transition")]
        [Range(0f, 1f)] public float entryNormalizedOffset = 0.0058366423f;
        [Range(0f, 1.25f)] public float exitNormalizedTime = 0.97950697f;
        [Range(0f, 1f)] public float normalizedTransitionDuration = 0.05543705f;
        [Tooltip("When true, transition duration is serialized seconds; otherwise it is normalized to the source state length.")]
        public bool transitionDurationFixed;
        [Range(0f, 1f)] public float destinationNormalizedOffset;
        [Tooltip("Original Animator interruption source enum. Retained as evidence; legacy Animation has no equivalent.")]
        public int interruptionSource = 2;
        [Tooltip("Original Animator ordered-interruption flag. Retained as evidence; legacy Animation has no equivalent.")]
        public bool orderedInterruption = true;
        [Tooltip("Original Animator transition root-motion blending flag. Retained as evidence; legacy Animation has no equivalent.")]
        public bool blendRootMotion = true;
        [Tooltip("Original AnyState conditions that select the Overview entrance. The legacy lab starts the resolved clip directly instead of evaluating these parameters.")]
        public EndfieldOverviewTransitionCondition[] entryTransitionConditions =
            System.Array.Empty<EndfieldOverviewTransitionCondition>();

        [Header("Recovered FromOveview effects")]
        public EndfieldOverviewEffectRequest[] entranceEffects =
            System.Array.Empty<EndfieldOverviewEffectRequest>();

        [Header("Recovered overview audio")]
        [Tooltip("Exact media selected by the serialized Wwise event posted by the overview-start AnimationClip.")]
        public AudioClip overviewStartAudio;
        [Tooltip("Exact AnimationEvent time for PostAudioEvent(au_actor_endminf_ui_overview).")]
        public float overviewStartAudioEventTime = 0.058666665f;
        public AudioSource overviewAudioSource;

        [Header("Recovered float-curve values")]
        public float weaponHide = 1.0f;
        public float magicaClothWeight = 0.01f;
        public float staticWeaponHide = 1.0f;

        public bool IsTransitioning { get; private set; }
        public bool IsLooping { get; private set; }
        public float RecoveredTransitionSeconds { get; private set; }
        public bool AnimatorContractActive { get; private set; }
        public int CurrentAnimatorStateHash { get; private set; }
        public int NextAnimatorStateHash { get; private set; }
        public float AnimatorTransitionNormalizedTime { get; private set; }
        public int RootMotionCallbackCount { get; private set; }
        public float AppliedRootDeltaRotationDegrees { get; private set; }
        public int PlaybackGeneration => playbackGeneration;
        public bool AutomaticOverviewPlaybackActive =>
            AnimatorContractActive || waitingForExit || IsLooping;
        public Vector3 RootMotionPositionDelta =>
            transform.position - rootMotionAnchorPosition;

        public bool TryGetAutomaticOverviewStartSeconds(out float seconds)
        {
            seconds = 0f;
            Animator animator = animatorSource;
            if (!AnimatorContractActive || animator == null ||
                !animator.enabled || animator.runtimeAnimatorController == null)
                return false;

            AnimatorStateInfo current = animator.GetCurrentAnimatorStateInfo(0);
            if (Animator.StringToHash(animatorStartStatePath) !=
                    SourceOverviewStartFullPathHash ||
                current.fullPathHash != SourceOverviewStartFullPathHash ||
                current.length <= 0f || float.IsNaN(current.normalizedTime) ||
                float.IsInfinity(current.normalizedTime) || current.normalizedTime < 0f)
                return false;

            // AnimatorBehaviourPlayEffect._SyncEffectTime consumes the current
            // AnimatorStateInfo as length * normalizedTime. Do not clamp the
            // value or reject the start-to-loop transition: FromOveview remains
            // the current state during that transition, including the recovered
            // source post's late 4.4 s pulse.
            seconds = current.length * current.normalizedTime;
            return !float.IsNaN(seconds) && !float.IsInfinity(seconds) && seconds >= 0f;
        }

        private bool waitingForExit;
        private bool hasStarted;
        private int playbackGeneration;
        private bool observingManualOverviewStart;
        private float lastObservedOverviewStartTime;
        private bool animatorTransitionObserved;
        private bool animatorExitCompleted;
        private bool warnedMissingAnimatorContract;
        private Vector3 rootMotionAnchorPosition;

        private Animation AnimationSource
        {
            get
            {
                if (animationSource == null)
                    animationSource = GetComponent<Animation>();
                return animationSource;
            }
        }

        private IEnumerator Start()
        {
            hasStarted = true;
            if (!playOnEnable)
                yield break;

            // Build/setup code may assign legacy clips during OnEnable. Wait one
            // frame so original overview playback wins over playAutomatically.
            yield return null;
            RestartOverview();
        }

        private void OnEnable()
        {
            if (hasStarted && playOnEnable)
                StartCoroutine(RestartAfterEnable());
        }

        private void OnDisable()
        {
            // A transition coroutine can outlive a disabled MonoBehaviour.
            // Invalidate it so it cannot hide widgets from the next restart.
            playbackGeneration++;
            waitingForExit = false;
            IsTransitioning = false;
            IsLooping = false;
            AnimatorContractActive = false;
            CurrentAnimatorStateHash = 0;
            NextAnimatorStateHash = 0;
            AnimatorTransitionNormalizedTime = 0f;
            observingManualOverviewStart = false;
            if (animatorSource != null)
                animatorSource.enabled = false;

            // PhaseCharInfo removes the previous PhaseCharItem and clears its
            // AnimatorPlayEffectHelper before the replacement actor enters.
            // Mirror that ownership boundary when a resident lab actor is
            // disabled: no Overview parameter or spawned entrance effect may
            // leak into its next selection.
            RestoreRecoveredParameters();
            FinishAllEntranceEffects();
            StopOverviewAudio();
        }

        private IEnumerator RestartAfterEnable()
        {
            yield return null;
            RestartOverview();
        }

        private void Update()
        {
            if (AnimatorContractActive)
            {
                ObserveRecoveredAnimator();
                return;
            }

            ObserveManualOverviewStartReplay();

            if (!waitingForExit)
                return;

            Animation animation = AnimationSource;
            AnimationState startState = animation != null ? animation[startClip] : null;
            if (startState == null)
            {
                waitingForExit = false;
                return;
            }

            float exitSeconds = Mathf.Max(0f, exitNormalizedTime) * startState.length;
            if (startState.time + 1e-5f < exitSeconds)
                return;

            BeginLoopTransition(startState);
        }

        public void RestartOverview()
        {
            if (TryRestartRecoveredAnimator())
                return;
            if (requireAnimatorContract)
            {
                // Every failed automatic restart is a terminal ownership
                // boundary, including failures discovered before Rebind/state
                // entry. Revoke any prior generation and unwind its transient
                // effects instead of leaving the last successful selection
                // visible behind a disabled Animator.
                playbackGeneration++;
                AnimatorContractActive = false;
                waitingForExit = false;
                IsTransitioning = false;
                IsLooping = false;
                CurrentAnimatorStateHash = 0;
                NextAnimatorStateHash = 0;
                AnimatorTransitionNormalizedTime = 0f;
                FinishAllEntranceEffects();
                StopOverviewAudio();
                RestoreRecoveredParameters();
                Animation legacy = AnimationSource;
                if (legacy != null)
                {
                    legacy.Stop();
                    legacy.enabled = false;
                }
                if (!warnedMissingAnimatorContract)
                {
                    warnedMissingAnimatorContract = true;
                    Debug.LogError(
                        $"Recovered Overview Animator contract is missing or stale on {name}; " +
                        "automatic playback is disabled instead of using the Legacy Animation approximation.",
                        this);
                }
                return;
            }

            Animation animation = AnimationSource;
            AnimationState startState = animation != null ? animation[startClip] : null;
            AnimationState loopState = animation != null ? animation[loopClip] : null;
            if (animation == null || startState == null || loopState == null)
            {
                Debug.LogWarning(
                    $"Recovered overview playback is missing clips on {name}: " +
                    $"start={startClip} loop={loopClip}",
                    this);
                return;
            }

            playbackGeneration++;
            AnimatorContractActive = false;
            if (animatorSource != null)
                animatorSource.enabled = false;
            animation.enabled = true;
            animation.Stop();
            startState.layer = 0;
            startState.blendMode = AnimationBlendMode.Blend;
            startState.wrapMode = WrapMode.ClampForever;
            startState.speed = 1f;
            startState.weight = 1f;
            startState.enabled = true;
            startState.time = Mathf.Clamp01(entryNormalizedOffset) * startState.length;

            loopState.layer = 0;
            loopState.blendMode = AnimationBlendMode.Blend;
            loopState.wrapMode = WrapMode.Loop;
            loopState.speed = 1f;
            loopState.time = 0f;
            loopState.weight = 0f;
            loopState.enabled = false;

            animation.Play(startClip, PlayMode.StopAll);
            startState.time = Mathf.Clamp01(entryNormalizedOffset) * startState.length;
            StartItemWidgets(animation);
            PublishRecoveredParameters();
            PublishEntranceEffects();
            PlayOverviewAudio(startState.time);
            ArmOverviewStartReplayObservation(startState);
            waitingForExit = true;
            IsTransitioning = false;
            IsLooping = false;
            RecoveredTransitionSeconds = Mathf.Max(0f, normalizedTransitionDuration);
            if (!transitionDurationFixed)
                RecoveredTransitionSeconds *= startState.length;
        }

        /// <summary>
        /// Returns Overview ownership to the source-backed entrance chain when
        /// the resident viewer selects this actor again. Manual clip browsing
        /// deliberately disables this component, so selection must restore
        /// both its Update-driven handoff and its future enable lifecycle.
        /// </summary>
        public void RestartOverviewFromSelection()
        {
            playOnEnable = true;
            if (!enabled)
                enabled = true;

            // Enabling an already-started component schedules a delayed
            // restart. Selection owns the restart synchronously, so remove
            // that duplicate before resetting the entrance state.
            StopAllCoroutines();
            RestartOverview();
        }

        /// <summary>
        /// Transfers base-layer ownership to the manual clip viewer. This also
        /// cancels the one-frame delayed Start coroutine so it cannot replace a
        /// newly selected clip with the overview entrance or settled loop.
        /// </summary>
        public void CancelForManualPlayback()
        {
            playOnEnable = false;
            playbackGeneration++;
            AnimatorContractActive = false;
            if (animatorSource != null)
                animatorSource.enabled = false;
            if (AnimationSource != null)
                AnimationSource.enabled = true;
            waitingForExit = false;
            IsTransitioning = false;
            IsLooping = false;
            StopAllCoroutines();
            RestoreRecoveredParameters();
            observingManualOverviewStart = false;
        }

        private bool TryRestartRecoveredAnimator()
        {
            Animator animator = animatorSource;
            if (animator == null || animator.runtimeAnimatorController == null ||
                string.IsNullOrEmpty(animatorStartStatePath) ||
                string.IsNullOrEmpty(animatorLoopStatePath))
                return false;

            int startHash = Animator.StringToHash(animatorStartStatePath);
            int loopHash = Animator.StringToHash(animatorLoopStatePath);
            AnimationClip[] controllerClips = animator.runtimeAnimatorController.animationClips;
            bool hasStartClip = false;
            bool hasLoopClip = false;
            foreach (AnimationClip clip in controllerClips)
            {
                if (clip == null || clip.legacy)
                    continue;
                hasStartClip |= clip.name == startClip;
                hasLoopClip |= clip.name == loopClip;
            }
            if (!hasStartClip || !hasLoopClip)
                return false;

            bool hasFromIndexParameter = false;
            bool hasToIndexParameter = false;
            bool hasEnableSwitchParameter = false;
            foreach (AnimatorControllerParameter parameter in animator.parameters)
            {
                hasFromIndexParameter |= parameter.name == "FromIndex" &&
                    parameter.type == AnimatorControllerParameterType.Int;
                hasToIndexParameter |= parameter.name == "ToIndex" &&
                    parameter.type == AnimatorControllerParameterType.Int;
                hasEnableSwitchParameter |= parameter.name == "EnableSwitch" &&
                    parameter.type == AnimatorControllerParameterType.Trigger;
            }
            if (!hasFromIndexParameter || !hasToIndexParameter ||
                !hasEnableSwitchParameter)
                return false;

            Animation legacy = AnimationSource;
            if (legacy != null)
            {
                legacy.Stop();
                // The recovered body pose is owned by Animator, while the
                // source item-widget clips remain isolated on Legacy
                // Animation layers. Keep that component evaluating after
                // stopping every prior body state.
                legacy.enabled = true;
            }
            animator.enabled = true;
            animator.cullingMode = AnimatorCullingMode.AlwaysAnimate;
            animator.applyRootMotion = blendRootMotion;
            animator.Rebind();
            animator.Update(0f);
            if (!animator.HasState(0, startHash) || !animator.HasState(0, loopHash))
            {
                animator.enabled = false;
                if (legacy != null)
                    legacy.enabled = true;
                return false;
            }

            bool setFromIndex = false;
            bool setToIndex = false;
            bool setEnableSwitch = false;
            foreach (EndfieldOverviewTransitionCondition condition in
                entryTransitionConditions ?? System.Array.Empty<EndfieldOverviewTransitionCondition>())
            {
                if (condition.mode == 6 && condition.parameter == "FromIndex")
                {
                    animator.SetInteger(condition.parameter, Mathf.RoundToInt(condition.threshold));
                    setFromIndex = true;
                }
                else if (condition.mode == 6 && condition.parameter == "ToIndex")
                {
                    animator.SetInteger(condition.parameter, Mathf.RoundToInt(condition.threshold));
                    setToIndex = true;
                }
                else if (condition.mode == 1 && condition.parameter == "EnableSwitch")
                {
                    animator.ResetTrigger(condition.parameter);
                    setEnableSwitch = true;
                }
            }
            if (!setFromIndex || !setToIndex || !setEnableSwitch)
            {
                animator.enabled = false;
                if (legacy != null)
                    legacy.enabled = true;
                return false;
            }

            playbackGeneration++;
            waitingForExit = false;
            animatorTransitionObserved = false;
            animatorExitCompleted = false;
            rootMotionAnchorPosition = transform.position;
            RootMotionCallbackCount = 0;
            AppliedRootDeltaRotationDegrees = 0f;
            AnimatorContractActive = true;
            IsTransitioning = false;
            IsLooping = false;
            CurrentAnimatorStateHash = 0;
            NextAnimatorStateHash = 0;
            AnimatorTransitionNormalizedTime = 0f;
            RecoveredTransitionSeconds = Mathf.Max(0f, normalizedTransitionDuration);
            AnimationClip sourceStart = System.Array.Find(controllerClips, value =>
                value != null && value.name == startClip);
            if (!transitionDurationFixed && sourceStart != null)
                RecoveredTransitionSeconds *= sourceStart.length;

            animator.SetTrigger("EnableSwitch");
            animator.Update(0f);
            ObserveRecoveredAnimator();

            // The source StateMachineBehaviour publishes its effects from
            // OnStateEnter. The lab cannot run that game-specific behaviour,
            // so enter and authenticate the exact source state first, then
            // publish effects against its AnimatorStateInfo elapsed clock.
            if (!TryGetAutomaticOverviewStartSeconds(out float sourceElapsed))
            {
                AnimatorContractActive = false;
                animator.enabled = false;
                if (legacy != null)
                    legacy.enabled = true;
                waitingForExit = false;
                IsTransitioning = false;
                IsLooping = false;
                CurrentAnimatorStateHash = 0;
                NextAnimatorStateHash = 0;
                AnimatorTransitionNormalizedTime = 0f;
                FinishAllEntranceEffects();
                StopOverviewAudio();
                RestoreRecoveredParameters();
                return false;
            }

            StartItemWidgets(legacy);
            PublishRecoveredParameters();
            PublishEntranceEffects(new EndfieldOverviewEffectSourceClock {
                owner = this,
                playbackGeneration = playbackGeneration,
                stateFullPathHash = SourceOverviewStartFullPathHash,
                elapsedSeconds = sourceElapsed,
                valid = true,
            });
            PlayOverviewAudio(sourceElapsed);
            return true;
        }

        private void OnAnimatorMove()
        {
            if (!AnimatorContractActive || !blendRootMotion ||
                animatorSource == null || !animatorSource.enabled)
                return;

            // Pinned CharUIModelMono._OnAnimatorMove consumes deltaRotation
            // only. It never reads deltaPosition. Implementing this callback
            // prevents stock Animator root-motion translation from being
            // applied while preserving the source controller's root-motion
            // blend/callback path.
            Vector3 positionBefore = transform.position;
            Quaternion deltaRotation = animatorSource.deltaRotation;
            transform.rotation = transform.rotation * deltaRotation;
            transform.position = positionBefore;
            RootMotionCallbackCount++;
            AppliedRootDeltaRotationDegrees +=
                Quaternion.Angle(Quaternion.identity, deltaRotation);
        }

        private void ObserveRecoveredAnimator()
        {
            Animator animator = animatorSource;
            if (animator == null || !animator.enabled || animator.runtimeAnimatorController == null)
            {
                AnimatorContractActive = false;
                playbackGeneration++;
                waitingForExit = false;
                IsTransitioning = false;
                IsLooping = false;
                CurrentAnimatorStateHash = 0;
                NextAnimatorStateHash = 0;
                AnimatorTransitionNormalizedTime = 0f;
                FinishAllEntranceEffects();
                StopOverviewAudio();
                RestoreRecoveredParameters();
                return;
            }

            int startHash = Animator.StringToHash(animatorStartStatePath);
            int loopHash = Animator.StringToHash(animatorLoopStatePath);
            AnimatorStateInfo current = animator.GetCurrentAnimatorStateInfo(0);
            bool inTransition = animator.IsInTransition(0);
            AnimatorStateInfo next = inTransition
                ? animator.GetNextAnimatorStateInfo(0)
                : default;
            CurrentAnimatorStateHash = current.fullPathHash;
            NextAnimatorStateHash = inTransition ? next.fullPathHash : 0;
            AnimatorTransitionNormalizedTime = inTransition
                ? animator.GetAnimatorTransitionInfo(0).normalizedTime
                : 0f;

            bool transitioningToLoop = inTransition &&
                current.fullPathHash == startHash && next.fullPathHash == loopHash;
            if (transitioningToLoop && !animatorTransitionObserved)
            {
                animatorTransitionObserved = true;
                StopOverviewAudio();
                TransitionItemWidgets(AnimationSource, RecoveredTransitionSeconds);
            }

            if (transitioningToLoop)
            {
                IsTransitioning = true;
                IsLooping = true;
                return;
            }

            if (current.fullPathHash == loopHash)
            {
                IsTransitioning = false;
                IsLooping = true;
                if (animatorTransitionObserved && !animatorExitCompleted)
                {
                    animatorExitCompleted = true;
                    CompleteEntranceStateExit();
                }
                return;
            }

            IsTransitioning = false;
            IsLooping = false;
        }

        /// <summary>
        /// Applies the non-body composition owned by a manually selected UI
        /// clip. The viewer and automatic controller paths must publish the
        /// same Overview entrance effects every time overview_start begins.
        /// Other UI clips explicitly retire that transient entrance state.
        /// </summary>
        public void ApplyManualUiClipComposition(string clipName)
        {
            string key = (clipName ?? string.Empty).ToLowerInvariant();
            bool isUiClip = key.Contains("_ui_") || key.Contains("uiteam");
            if (!isUiClip)
                return;

            FinishAllEntranceEffects();
            StopOverviewAudio();
            if (key.Contains("_ui_overview_start"))
            {
                PublishRecoveredParameters();
                PublishEntranceEffects();
                PlayOverviewAudio(0f);
                ArmOverviewStartReplayObservation(
                    AnimationSource != null ? AnimationSource[startClip] : null);
            }
            else
            {
                observingManualOverviewStart = false;
                RestoreRecoveredParameters();
            }
        }

        private void ArmOverviewStartReplayObservation(AnimationState state)
        {
            observingManualOverviewStart = state != null && state.enabled;
            lastObservedOverviewStartTime = state != null ? state.time : 0f;
        }

        /// <summary>
        /// Manual clip browsing can loop overview_start without passing back
        /// through the viewer UI. Treat the AnimationState wrap itself as the
        /// source event so its crystals, particles, parameters, and Wwise cue
        /// are recreated on every playback cycle.
        /// </summary>
        private void ObserveManualOverviewStartReplay()
        {
            if (waitingForExit)
                return;

            Animation animation = AnimationSource;
            AnimationState state = animation != null ? animation[startClip] : null;
            bool playing = state != null && state.enabled && animation.IsPlaying(startClip);
            if (!playing)
            {
                observingManualOverviewStart = false;
                return;
            }

            if (!observingManualOverviewStart)
            {
                observingManualOverviewStart = true;
                lastObservedOverviewStartTime = state.time;
                return;
            }

            float currentTime = state.time;
            bool wrapped = currentTime + 1e-4f < lastObservedOverviewStartTime;
            if (!wrapped && state.length > 1e-5f)
            {
                int previousCycle = Mathf.FloorToInt(
                    Mathf.Max(0f, lastObservedOverviewStartTime) / state.length);
                int currentCycle = Mathf.FloorToInt(
                    Mathf.Max(0f, currentTime) / state.length);
                wrapped = currentCycle > previousCycle;
            }
            lastObservedOverviewStartTime = currentTime;
            if (!wrapped)
                return;

            FinishAllEntranceEffects();
            StopOverviewAudio();
            PublishRecoveredParameters();
            PublishEntranceEffects();
            PlayOverviewAudio(state.length > 1e-5f
                ? Mathf.Repeat(currentTime, state.length)
                : 0f);
        }

        private void PlayOverviewAudio(float clipTime)
        {
            if (overviewStartAudio == null)
                return;
            if (overviewAudioSource == null)
            {
                overviewAudioSource = GetComponent<AudioSource>();
                if (overviewAudioSource == null)
                    overviewAudioSource = gameObject.AddComponent<AudioSource>();
            }
            overviewAudioSource.playOnAwake = false;
            overviewAudioSource.loop = false;
            overviewAudioSource.spatialBlend = 0f;
            // Keep the recovered clip, event time, and playback state alive for
            // validation, but do not emit sound while iterating in the Editor
            // or a Development Build.
            overviewAudioSource.mute = Application.isEditor || Debug.isDebugBuild;
            overviewAudioSource.Stop();
            overviewAudioSource.clip = overviewStartAudio;
            overviewAudioSource.PlayDelayed(Mathf.Max(0f, overviewStartAudioEventTime - clipTime));
        }

        private void StopOverviewAudio()
        {
            if (overviewAudioSource != null)
                overviewAudioSource.Stop();
        }

        private void BeginLoopTransition(AnimationState startState)
        {
            Animation animation = AnimationSource;
            AnimationState loopState = animation != null ? animation[loopClip] : null;
            if (animation == null || loopState == null)
            {
                waitingForExit = false;
                return;
            }

            float duration = Mathf.Max(0f, normalizedTransitionDuration);
            if (!transitionDurationFixed)
                duration *= startState.length;
            loopState.time = Mathf.Clamp01(destinationNormalizedOffset) * loopState.length;
            loopState.wrapMode = WrapMode.Loop;
            animation.CrossFade(loopClip, duration, PlayMode.StopSameLayer);
            loopState.time = Mathf.Clamp01(destinationNormalizedOffset) * loopState.length;
            // The recovered loop clip has no PostAudioEvent. Its entrance cue
            // is 5.818313 s long and belongs only to the 5.866667 s start
            // state, so retire it on the controller's actual loop handoff.
            StopOverviewAudio();
            TransitionItemWidgets(animation, duration);
            StartCoroutine(FinishEntranceEffectsAfterStateExit(
                duration,
                playbackGeneration));
            waitingForExit = false;
            IsTransitioning = duration > 0f;
            IsLooping = true;
        }

        private void PublishRecoveredParameters()
        {
            foreach (MonoBehaviour behaviour in GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (behaviour == null || ReferenceEquals(behaviour, this))
                    continue;
                if (behaviour is IEndfieldOverviewParameterConsumer consumer)
                {
                    consumer.ApplyOverviewParameters(
                        weaponHide,
                        magicaClothWeight,
                        staticWeaponHide);
                }
            }
        }

        /// <summary>
        /// Applies source-backed non-animation Overview parameters after an
        /// editor or validation path samples clips directly. AnimationClip
        /// sampling does not run Start/Update, so these consumers otherwise
        /// remain unapplied in deterministic previews.
        /// </summary>
        public void ApplyRecoveredParametersNow()
        {
            PublishRecoveredParameters();
        }

        private void RestoreRecoveredParameters()
        {
            foreach (MonoBehaviour behaviour in GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (behaviour == null || ReferenceEquals(behaviour, this))
                    continue;
                if (behaviour is IEndfieldOverviewParameterResetConsumer consumer)
                    consumer.RestoreOverviewParameters();
            }
        }

        private void PublishEntranceEffects()
        {
            PublishEntranceEffects(default);
        }

        private void PublishEntranceEffects(
            EndfieldOverviewEffectSourceClock sourceClock)
        {
            if (entranceEffects == null || entranceEffects.Length == 0)
                return;
            foreach (MonoBehaviour behaviour in GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (!(behaviour is IEndfieldOverviewEffectSpawner spawner))
                    continue;
                foreach (EndfieldOverviewEffectRequest effect in entranceEffects)
                    spawner.SpawnOverviewEffect(effect, transform, sourceClock);
            }
        }

        private IEnumerator FinishEntranceEffectsAfterStateExit(
            float transitionDuration,
            int generation)
        {
            if (transitionDuration > 0f)
                yield return new WaitForSeconds(transitionDuration);

            if (generation != playbackGeneration)
                yield break;

            CompleteEntranceStateExit();
        }

        private void CompleteEntranceStateExit()
        {
            HideFinishedItemWidgets();

            if (entranceEffects != null && entranceEffects.Length > 0)
            {
                foreach (MonoBehaviour behaviour in GetComponentsInChildren<MonoBehaviour>(true))
                {
                    if (!(behaviour is IEndfieldOverviewEffectSpawner spawner))
                        continue;
                    foreach (EndfieldOverviewEffectRequest effect in entranceEffects)
                    {
                        if (effect.finishWhenExit)
                            spawner.FinishOverviewEffect(effect.prefabName);
                    }
                }
            }
            IsTransitioning = false;
        }

        private void FinishAllEntranceEffects()
        {
            if (entranceEffects == null || entranceEffects.Length == 0)
                return;

            foreach (MonoBehaviour behaviour in GetComponentsInChildren<MonoBehaviour>(true))
            {
                if (!(behaviour is IEndfieldOverviewEffectSpawner spawner))
                    continue;
                foreach (EndfieldOverviewEffectRequest effect in entranceEffects)
                    spawner.FinishOverviewEffect(effect.prefabName);
            }
        }

        private void StartItemWidgets(Animation animation)
        {
            if (animation == null)
                return;

            int widgetCount = GetItemWidgetCount();
            for (int index = 0; index < widgetCount; index++)
            {
                EndfieldOverviewItemWidgetBinding binding = GetItemWidget(index);
                int layer = index + 1;
                AnimationState startState = GetWidgetState(
                    animation,
                    binding.startClip,
                    binding.propPath,
                    "start");
                AnimationState loopState = GetWidgetState(
                    animation,
                    binding.loopClip,
                    binding.propPath,
                    "loop");
                AnimationState postTransitionState = GetWidgetState(
                    animation,
                    binding.postTransitionClip,
                    binding.propPath,
                    "post-transition");

                ConfigureWidgetState(startState, layer, WrapMode.ClampForever);
                ConfigureWidgetState(loopState, layer, WrapMode.Loop);
                ConfigureWidgetState(postTransitionState, layer, WrapMode.ClampForever);
                SetItemWidgetVisible(binding.propPath, true);

                AnimationState initialState = startState != null ? startState : loopState;
                string initialClip = startState != null ? binding.startClip : binding.loopClip;
                if (initialState == null || string.IsNullOrEmpty(initialClip))
                    continue;

                float normalizedOffset = startState != null
                    ? Mathf.Clamp01(entryNormalizedOffset)
                    : 0f;
                initialState.enabled = true;
                initialState.weight = 1f;
                initialState.time = normalizedOffset * initialState.length;
                animation.Play(initialClip, PlayMode.StopSameLayer);
                initialState.time = normalizedOffset * initialState.length;
                SetItemWidgetVisible(binding.propPath, true);
            }
        }

        private void TransitionItemWidgets(Animation animation, float duration)
        {
            int widgetCount = GetItemWidgetCount();
            for (int index = 0; index < widgetCount; index++)
            {
                EndfieldOverviewItemWidgetBinding binding = GetItemWidget(index);
                string targetClip = !string.IsNullOrEmpty(binding.loopClip)
                    ? binding.loopClip
                    : binding.postTransitionClip;
                if (string.IsNullOrEmpty(targetClip))
                    continue;

                AnimationState targetState = animation[targetClip];
                if (targetState == null)
                    continue;

                // A loop-only binding started at overview entry and should keep
                // running instead of being reset at the body handoff.
                AnimationState startState = string.IsNullOrEmpty(binding.startClip)
                    ? null
                    : animation[binding.startClip];
                if (startState == null)
                    continue;

                ConfigureWidgetState(
                    targetState,
                    index + 1,
                    !string.IsNullOrEmpty(binding.loopClip) ? WrapMode.Loop : WrapMode.ClampForever);
                targetState.time = 0f;
                animation.CrossFade(targetClip, duration, PlayMode.StopSameLayer);
                SetItemWidgetVisible(binding.propPath, true);
            }
        }

        private void HideFinishedItemWidgets()
        {
            int widgetCount = GetItemWidgetCount();
            for (int index = 0; index < widgetCount; index++)
            {
                EndfieldOverviewItemWidgetBinding binding = GetItemWidget(index);
                if (binding.hideAfterTransition)
                    SetItemWidgetVisible(binding.propPath, false);
            }
        }

        private AnimationState GetWidgetState(
            Animation animation,
            string clipName,
            string propPath,
            string role)
        {
            if (string.IsNullOrEmpty(clipName))
                return null;

            AnimationState state = animation[clipName];
            if (state == null)
            {
                Debug.LogWarning(
                    $"Recovered overview item-widget {role} clip is missing on {name}: " +
                    $"clip={clipName} prop={propPath}",
                    this);
            }
            return state;
        }

        private static void ConfigureWidgetState(
            AnimationState state,
            int layer,
            WrapMode wrapMode)
        {
            if (state == null)
                return;

            state.layer = layer;
            state.blendMode = AnimationBlendMode.Blend;
            state.wrapMode = wrapMode;
            state.speed = 1f;
            state.time = 0f;
            state.weight = 0f;
            state.enabled = false;
        }

        private int GetItemWidgetCount()
        {
            if (itemWidgets != null && itemWidgets.Length > 0)
                return itemWidgets.Length;
            return HasLegacyEntranceCompanion() ? 1 : 0;
        }

        private EndfieldOverviewItemWidgetBinding GetItemWidget(int index)
        {
            if (itemWidgets != null && itemWidgets.Length > 0)
                return itemWidgets[index];

            return new EndfieldOverviewItemWidgetBinding
            {
                propPath = entranceCompanionPropPath,
                startClip = entranceCompanionClip,
                loopClip = string.Empty,
                postTransitionClip = string.Empty,
                hideAfterTransition = hideEntranceCompanionAfterTransition,
                activationEvidence = "legacy entrance-companion serialization"
            };
        }

        private bool HasLegacyEntranceCompanion()
        {
            return !string.IsNullOrEmpty(entranceCompanionClip) ||
                   !string.IsNullOrEmpty(entranceCompanionPropPath);
        }

        private void SetItemWidgetVisible(string propPath, bool visible)
        {
            if (string.IsNullOrEmpty(propPath))
                return;
            Transform itemWidget = transform.Find(propPath);
            if (itemWidget == null)
                return;

            if (visible)
                itemWidget.gameObject.SetActive(true);
            foreach (Renderer renderer in itemWidget.GetComponentsInChildren<Renderer>(true))
            {
                if (renderer == null)
                    continue;
                if (visible)
                    renderer.gameObject.SetActive(true);
                renderer.enabled = visible;
            }
        }
    }
}
