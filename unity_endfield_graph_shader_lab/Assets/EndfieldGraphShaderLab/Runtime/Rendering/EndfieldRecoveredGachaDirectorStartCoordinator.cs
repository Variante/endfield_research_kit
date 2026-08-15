using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEngine.Playables;

namespace EndfieldGraphShaderLab
{
    public enum EndfieldRecoveredGachaDirectorRole
    {
        Actor = 0,
        Audio = 1,
        Effect = 2,
        Light = 3,
        Others = 4,
    }

    [Serializable]
    public sealed class EndfieldRecoveredGachaDirectorBinding
    {
        public EndfieldRecoveredGachaDirectorRole role;
        public int sourceOrdinal;
        public PlayableDirector director;
    }

    /// <summary>
    /// Compatibility representation of a source TimelineAsset that contains
    /// no tracks, clips, or bindings. It preserves helper ownership and start
    /// ordering without inventing a visual or audio payload.
    /// </summary>
    public sealed class EndfieldRecoveredEmptyGachaHelperPlayableAsset : PlayableAsset
    {
        public EndfieldRecoveredGachaDirectorRole role;
        public long sourcePathId;
        public string sourceSerializedFile;

        public override double duration => 0.0;

        public override Playable CreatePlayable(PlayableGraph graph, GameObject owner)
        {
            return Playable.Create(graph);
        }
    }

    /// <summary>
    /// Replays the source GachaCharTLHelper two-stage Director protocol for
    /// only the helper roles whose exact PlayableAssets are recovered.
    /// Missing roles remain explicit; callers must provide a source-identified
    /// PlayableAsset and may not create name-inferred helper payloads.
    /// </summary>
    public sealed class EndfieldRecoveredGachaDirectorStartCoordinator
    {
        private static readonly EndfieldRecoveredGachaDirectorRole[] SourceOrder =
        {
            EndfieldRecoveredGachaDirectorRole.Actor,
            EndfieldRecoveredGachaDirectorRole.Audio,
            EndfieldRecoveredGachaDirectorRole.Effect,
            EndfieldRecoveredGachaDirectorRole.Light,
            EndfieldRecoveredGachaDirectorRole.Others,
        };

        private readonly EndfieldRecoveredGachaDirectorBinding[] admitted;
        private readonly EndfieldRecoveredGachaDirectorRole[] missing;

        public EndfieldRecoveredGachaDirectorStartCoordinator(
            IEnumerable<EndfieldRecoveredGachaDirectorBinding> bindings)
        {
            EndfieldRecoveredGachaDirectorBinding[] supplied =
                bindings == null
                    ? Array.Empty<EndfieldRecoveredGachaDirectorBinding>()
                    : bindings.Where(binding => binding != null).ToArray();
            Validate(supplied);
            admitted = supplied
                .OrderBy(binding => binding.sourceOrdinal)
                .ToArray();
            var admittedRoles = new HashSet<EndfieldRecoveredGachaDirectorRole>(
                admitted.Select(binding => binding.role));
            missing = SourceOrder.Where(role => !admittedRoles.Contains(role)).ToArray();
        }

        public IReadOnlyList<EndfieldRecoveredGachaDirectorBinding> Admitted => admitted;
        public IReadOnlyList<EndfieldRecoveredGachaDirectorRole> Missing => missing;

        public void SampleToBeginning()
        {
            // GachaCharTLHelper samples each helper in source order, then
            // performs a TailTick(0). TailTick ownership is not recovered and
            // deliberately remains outside this coordinator.
            foreach (EndfieldRecoveredGachaDirectorBinding binding in admitted)
            {
                SetAudioPlaybackArmed(binding, false);
                binding.director.Stop();
                binding.director.time = 0.0;
                binding.director.Evaluate();
            }
        }

        public void PlayFromStart()
        {
            // Source Lua first rebuilds every collected graph. Only after that
            // full pass does it walk Actor/Audio/Effect/Light/Others again to
            // set time zero, Evaluate, and Play each Director.
            foreach (EndfieldRecoveredGachaDirectorBinding binding in admitted)
                binding.director.RebuildGraph();
            foreach (EndfieldRecoveredGachaDirectorBinding binding in admitted)
            {
                binding.director.time = 0.0;
                SetAudioPlaybackArmed(binding, false);
                binding.director.Evaluate();
                SetAudioPlaybackArmed(binding, true);
                binding.director.Play();
            }
        }

        public void StopAll()
        {
            foreach (EndfieldRecoveredGachaDirectorBinding binding in admitted)
            {
                SetAudioPlaybackArmed(binding, false);
                if (binding.role == EndfieldRecoveredGachaDirectorRole.Audio)
                {
                    EndfieldRecoveredGachaAudioEmitter emitter =
                        binding.director.GetComponent<
                            EndfieldRecoveredGachaAudioEmitter>();
                    if (emitter != null)
                        emitter.StopRecoveredEvents();
                }
                binding.director.Stop();
            }
        }

        private static void SetAudioPlaybackArmed(
            EndfieldRecoveredGachaDirectorBinding binding,
            bool armed)
        {
            if (binding.role != EndfieldRecoveredGachaDirectorRole.Audio ||
                binding.director == null)
                return;
            EndfieldRecoveredGachaAudioEmitter emitter =
                binding.director.GetComponent<EndfieldRecoveredGachaAudioEmitter>();
            if (emitter != null)
                emitter.PlaybackArmed = armed;
        }

        private static void Validate(EndfieldRecoveredGachaDirectorBinding[] bindings)
        {
            var roles = new HashSet<EndfieldRecoveredGachaDirectorRole>();
            var ordinals = new HashSet<int>();
            foreach (EndfieldRecoveredGachaDirectorBinding binding in bindings)
            {
                int expectedOrdinal = (int)binding.role;
                if (binding.sourceOrdinal != expectedOrdinal)
                {
                    throw new ArgumentException(
                        $"Recovered gacha Director {binding.role} has source ordinal " +
                        $"{binding.sourceOrdinal}; expected {expectedOrdinal}.");
                }
                if (!roles.Add(binding.role) || !ordinals.Add(binding.sourceOrdinal))
                    throw new ArgumentException($"Duplicate recovered gacha Director role {binding.role}.");
                if (binding.director == null || binding.director.playableAsset == null)
                    throw new ArgumentException($"Recovered gacha Director {binding.role} has no exact PlayableAsset.");
                if (binding.director.playOnAwake ||
                    binding.director.timeUpdateMode != DirectorUpdateMode.GameTime)
                {
                    throw new ArgumentException(
                        $"Recovered gacha Director {binding.role} must use GameTime with playOnAwake disabled.");
                }
            }
        }
    }
}
