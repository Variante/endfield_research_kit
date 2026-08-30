using System;
using UnityEngine;
using UnityEngine.Rendering;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Source-closed publication rule for the retail terrain subsurface
    /// manager. The selected CharInfo lifecycle/value is intentionally an
    /// external evidence input: an empty local registry is not proof that the
    /// retail selected frame also published zero.
    /// </summary>
    internal static class EndfieldRecoveredTerrainSubsurfaceConstants
    {
        internal const string NativeContractSchema =
            "endfield.endminf-m27-terrain-profile-native-contract.v1";
        internal const string RequiredSelectedFrameProvenanceSchema =
            "endfield.endminf-m27-terrain-profile-selected-frame.v1";

        private static readonly int TerrainSubsurfaceProfileIntId =
            Shader.PropertyToID("_TerrainSubsurfaceProfileInt");

        internal static bool TryPublish(
            CommandBuffer command,
            bool selectedFrameLifecycleValidated,
            bool reservedTerrainKeyRegistered,
            int registeredProfileIndex,
            string selectedFrameProvenanceSchema,
            string selectedFrameProvenance,
            out PublisherState state,
            out string failure)
        {
            state = default;
            failure = string.Empty;
            if (command == null)
            {
                failure = "the terrain subsurface publisher requires a command buffer";
                return false;
            }
            if (!selectedFrameLifecycleValidated ||
                !string.Equals(
                    selectedFrameProvenanceSchema,
                    RequiredSelectedFrameProvenanceSchema,
                    StringComparison.Ordinal) ||
                string.IsNullOrWhiteSpace(selectedFrameProvenance))
            {
                failure =
                    "fresh selected-frame terrain lifecycle/value provenance " +
                    "is required; incomplete captures and an empty lab registry " +
                    "do not authorize zero";
                return false;
            }
            if (reservedTerrainKeyRegistered)
            {
                if (registeredProfileIndex < 0 ||
                    registeredProfileIndex >= 16777215)
                {
                    failure =
                        "the validated terrain profile index cannot be encoded " +
                        "exactly as the retail global float";
                    return false;
                }
            }
            else if (registeredProfileIndex != -1)
            {
                failure =
                    "an absent reserved terrain key requires the retail -1 sentinel";
                return false;
            }

            uint publishedValue = reservedTerrainKeyRegistered
                ? checked((uint)registeredProfileIndex + 1u)
                : 0u;
            command.SetGlobalFloat(
                TerrainSubsurfaceProfileIntId,
                publishedValue);
            state = new PublisherState(
                publishedValue,
                selectedFrameProvenanceSchema,
                selectedFrameProvenance);
            return true;
        }

        internal readonly struct PublisherState
        {
            internal readonly bool ready;
            internal readonly uint publishedValue;
            internal readonly string nativeContractSchema;
            internal readonly string selectedFrameProvenanceSchema;
            internal readonly string selectedFrameProvenance;

            internal PublisherState(
                uint publishedValue,
                string selectedFrameProvenanceSchema,
                string selectedFrameProvenance)
            {
                ready = true;
                this.publishedValue = publishedValue;
                nativeContractSchema = NativeContractSchema;
                this.selectedFrameProvenanceSchema =
                    selectedFrameProvenanceSchema;
                this.selectedFrameProvenance = selectedFrameProvenance;
            }
        }
    }
}
