using System;
using System.Collections.Generic;
using System.Linq;
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
    /// Replays the source GachaCharTLHelper two-stage Director protocol for
    /// only the helper roles whose exact PlayableAssets are recovered.
    /// Missing roles remain explicit; this class never creates identity or
    /// name-inferred Directors for Audio, Light, or Others.
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
                binding.director.Evaluate();
                binding.director.Play();
            }
        }

        public void StopAll()
        {
            foreach (EndfieldRecoveredGachaDirectorBinding binding in admitted)
                binding.director.Stop();
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
