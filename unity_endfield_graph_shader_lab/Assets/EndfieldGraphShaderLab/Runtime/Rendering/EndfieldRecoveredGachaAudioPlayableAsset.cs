using System;
using System.Collections.Generic;
using UnityEngine;
using UnityEngine.Playables;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-closed AudioEventPlayable replacement for zhuangfy's gacha
    /// Audio helper. Paused Timeline evaluation is intentionally silent;
    /// events are posted only while the graph is playing.
    /// </summary>
    public sealed class EndfieldRecoveredGachaAudioPlayableAsset : PlayableAsset
    {
        public const long SourceTimelinePathId = 6159943924586262679L;
        public const string SourceSerializedFile =
            "CAB-8de5ae176c0a4339ac3ead156a159916";

        public const string OverviewEventName = "Au_Gcaha_zhuangfy_overview";
        public const uint OverviewEventHash = 0xee2a8301u;
        public const uint OverviewMediaId = 256896424u;
        public const double OverviewStart = 0.0;
        public const double OverviewDuration = 5.0;

        public const string RarityEventName = "Au_UI_Gacha_Chrshow_Light6";
        public const uint RarityEventHash = 0xe347da7du;
        public const uint RarityMediaId = 787269389u;
        public const double RarityStart = 7.75;
        public const double RarityDuration = 2.366666666666667;

        public AudioClip overviewClip;
        public AudioClip rarityClip;

        public override double duration => RarityStart + RarityDuration;

        public override Playable CreatePlayable(PlayableGraph graph, GameObject owner)
        {
            EndfieldRecoveredGachaAudioEmitter emitter =
                owner.GetComponent<EndfieldRecoveredGachaAudioEmitter>();
            if (emitter == null)
                emitter = owner.AddComponent<EndfieldRecoveredGachaAudioEmitter>();
            var playable = ScriptPlayable<Behaviour>.Create(graph);
            Behaviour behaviour = playable.GetBehaviour();
            behaviour.emitter = emitter;
            behaviour.overviewClip = overviewClip;
            behaviour.rarityClip = rarityClip;
            ScriptPlayableOutput output =
                ScriptPlayableOutput.Create(graph, "RecoveredGachaAudioEvents");
            output.SetSourcePlayable(playable);
            return playable;
        }

        private sealed class Behaviour : PlayableBehaviour
        {
            public EndfieldRecoveredGachaAudioEmitter emitter;
            public AudioClip overviewClip;
            public AudioClip rarityClip;
            private bool overviewPosted;
            private bool rarityPosted;
            private double previousTime = -1.0;

            public override void ProcessFrame(
                Playable playable,
                FrameData info,
                object playerData)
            {
                if (emitter == null || !emitter.PlaybackArmed)
                    return;
                double current = playable.GetTime();
                if (current + 1e-9 < previousTime)
                {
                    overviewPosted = false;
                    rarityPosted = false;
                }
                TryPost(
                    ref overviewPosted,
                    previousTime,
                    current,
                    OverviewStart,
                    OverviewDuration,
                    OverviewEventName,
                    OverviewEventHash,
                    OverviewMediaId,
                    overviewClip);
                TryPost(
                    ref rarityPosted,
                    previousTime,
                    current,
                    RarityStart,
                    RarityDuration,
                    RarityEventName,
                    RarityEventHash,
                    RarityMediaId,
                    rarityClip);
                previousTime = current;
            }

            public override void OnGraphStop(Playable playable)
            {
                if (emitter != null)
                    emitter.StopRecoveredEvents();
                overviewPosted = false;
                rarityPosted = false;
                previousTime = -1.0;
            }

            private void TryPost(
                ref bool posted,
                double previous,
                double current,
                double start,
                double clipDuration,
                string eventName,
                uint eventHash,
                uint mediaId,
                AudioClip clip)
            {
                if (posted || current + 1e-9 < start || current >= start + clipDuration)
                    return;
                if (previous >= start && previous <= current)
                    return;
                posted = true;
                emitter.PostRecoveredEvent(
                    eventName,
                    eventHash,
                    mediaId,
                    clip,
                    Math.Max(0.0, current - start));
            }
        }
    }

    [DisallowMultipleComponent]
    [AddComponentMenu("Endfield/Recovered/Gacha Audio Emitter")]
    public sealed class EndfieldRecoveredGachaAudioEmitter : MonoBehaviour
    {
        [NonSerialized] private int postCount;
        [NonSerialized] private string lastEventName;
        [NonSerialized] private uint lastEventHash;
        [NonSerialized] private uint lastMediaId;
        [NonSerialized] private int stopCount;
        private readonly List<AudioSource> activeSources = new List<AudioSource>();

        public int PostCount => postCount;
        public string LastEventName => lastEventName;
        public uint LastEventHash => lastEventHash;
        public uint LastMediaId => lastMediaId;
        public int StopCount => stopCount;
        public bool PlaybackArmed { get; set; }

        public void PostRecoveredEvent(
            string eventName,
            uint eventHash,
            uint mediaId,
            AudioClip clip,
            double seekSeconds)
        {
            postCount++;
            lastEventName = eventName;
            lastEventHash = eventHash;
            lastMediaId = mediaId;
            if (clip == null)
                return;
            AudioSource source = gameObject.AddComponent<AudioSource>();
            source.playOnAwake = false;
            source.spatialBlend = 0f;
            source.clip = clip;
            source.time = Mathf.Clamp((float)seekSeconds, 0f, clip.length);
            source.Play();
            activeSources.Add(source);
            if (Application.isPlaying)
                Destroy(source, clip.length - source.time + 0.1f);
        }

        public void StopRecoveredEvents()
        {
            bool stopped = false;
            foreach (AudioSource source in activeSources)
            {
                if (source == null)
                    continue;
                source.Stop();
                stopped = true;
                if (Application.isPlaying)
                    Destroy(source);
            }
            activeSources.Clear();
            if (stopped)
                stopCount++;
        }
    }
}
