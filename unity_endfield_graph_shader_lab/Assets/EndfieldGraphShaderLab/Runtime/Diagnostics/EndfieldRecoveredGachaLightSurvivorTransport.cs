using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using UnityEngine;

namespace EndfieldGraphShaderLab
{
    /// <summary>
    /// Carries the source-closed authored survivor identity/order into a
    /// runtime diagnostic boundary. It intentionally does not publish a
    /// LightData/b31 buffer: the retail LightCullResult pointer, count, and
    /// target-frame row payload still require an authorized capture.
    /// </summary>
    public static class EndfieldRecoveredGachaLightSurvivorTransport
    {
        public const string Selector =
            "ENDFIELD_RECOVERED_GACHA_LIGHT_SURVIVOR_TRANSPORT";
        public const int KnownAuthoredCount = 17;
        public const int KnownAuthoredCharacterCount = 6;
        public const int KnownAuthoredRoomCount = 11;
        public const uint SelectedAspectBits = 0x3FE38E39u;
        public const string PopulationEvidenceSha256 =
            "0441ec4817e23a69c1162643d05ae0c2c9abd1acdd02cc76d7646f0363b5ecc8";
        public const string DeferredEvidenceSha256 =
            "6675f99a85e528b4ac33631c0cd1198071cc389bf12300d6f992ba62fc401c30";
        public const string TransportContractSha256 =
            "2543b35cc356ad4a9cca2fcb20a313cd924ecf19711c9dde9753d57d28266a79";

        private static readonly string[] RoomRowsStorage =
        {
            "Spot Light (12)",
            "Spot Light (19)",
            "Linear Light (12)",
            "Linear Light (13)",
            "Linear Light (14)",
            "Spot Light (17)",
            "Linear Light (15)",
            "Spot Light (18)",
            "Spot Light (9)",
            "Spot Light (11)",
            "Spot Light (10)",
        };

        private static readonly SurvivorRow[] SelectedRowsStorage =
        {
            new SurvivorRow("SpecLight_1 (8)", "light_overview", false),
            new SurvivorRow("RimLight_2 (5)", "light_overview", false),
            new SurvivorRow("SpecLight_1 (11)", "light_overview", false),
            new SurvivorRow("Point Light_overview (2)", "light_overview", false),
            new SurvivorRow("RimLight_2 (4)", "light_overview", false),
            new SurvivorRow("FogLight_1 (2)", "light_overview", false),
            new SurvivorRow("Spot Light (12)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (19)", "SceneLight6Rarity", true),
            new SurvivorRow("Linear Light (12)", "SceneLight6Rarity", true),
            new SurvivorRow("Linear Light (13)", "SceneLight6Rarity", true),
            new SurvivorRow("Linear Light (14)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (17)", "SceneLight6Rarity", true),
            new SurvivorRow("Linear Light (15)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (18)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (9)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (11)", "SceneLight6Rarity", true),
            new SurvivorRow("Spot Light (10)", "SceneLight6Rarity", true),
        };

        private static readonly ReadOnlyCollection<string> RoomRowsView =
            Array.AsReadOnly(RoomRowsStorage);
        private static readonly ReadOnlyCollection<SurvivorRow> SelectedRowsView =
            Array.AsReadOnly(SelectedRowsStorage);

        public static bool IsRequested =>
            ReadBooleanEnvironment(Selector);

        public static IReadOnlyList<string> SelectedAspectRoomRows => RoomRowsView;

        public static IReadOnlyList<SurvivorRow> SelectedAspectRows =>
            SelectedRowsView;

        public static bool TryPrepareSelectedAspect(
            Camera camera,
            out Frame frame,
            out string failure)
        {
            frame = default;
            failure = null;
            if (!IsRequested)
            {
                failure = "explicit Gacha survivor transport selector is disabled";
                return false;
            }
            if (camera == null)
            {
                failure = "physical Gacha camera is required";
                return false;
            }

            EndfieldGachaLightAspectAdmissionOracle.AdmissionResult admission =
                EndfieldGachaLightAspectAdmissionOracle.Evaluate(camera);
            if (!admission.IsAdmitted ||
                admission.Band != EndfieldGachaLightAspectAdmissionOracle
                    .AdmissionBand.AtOrAboveSpot18Threshold)
            {
                failure =
                    "camera projection/aspect is outside the selected 16:9 authored survivor contract";
                return false;
            }
            if (FloatBits(camera.aspect) != SelectedAspectBits)
            {
                failure =
                    "camera aspect is admitted by the native threshold but is not the captured 3840x2160 sample";
                return false;
            }
            if (!SameSequence(admission.StrictRoomSubsequence, RoomRowsView))
            {
                failure = "aspect oracle room order does not match the source-backed transport";
                return false;
            }

            frame = new Frame(
                camera.aspect,
                SelectedRowsView,
                true,
                "target-frame LightCullResult pointer/count/rows remain capture-only");
            return true;
        }

        private static bool SameSequence(
            IReadOnlyList<string> left,
            IReadOnlyList<string> right)
        {
            if (left == null || right == null || left.Count != right.Count)
                return false;
            for (int index = 0; index < left.Count; index++)
            {
                if (!string.Equals(left[index], right[index], StringComparison.Ordinal))
                    return false;
            }
            return true;
        }

        private static bool ReadBooleanEnvironment(string name)
        {
            string value = Environment.GetEnvironmentVariable(name);
            return string.Equals(value, "1", StringComparison.Ordinal) ||
                string.Equals(value, "true", StringComparison.OrdinalIgnoreCase) ||
                string.Equals(value, "on", StringComparison.OrdinalIgnoreCase);
        }

        private static uint FloatBits(float value)
        {
            return unchecked((uint)BitConverter.SingleToInt32Bits(value));
        }

        public readonly struct SurvivorRow
        {
            public SurvivorRow(string name, string source, bool room)
            {
                Name = name;
                Source = source;
                IsRoom = room;
            }

            public string Name { get; }
            public string Source { get; }
            public bool IsRoom { get; }
        }

        public readonly struct Frame
        {
            internal Frame(
                float aspect,
                IReadOnlyList<SurvivorRow> rows,
                bool targetFrameCaptureRequired,
                string boundary)
            {
                Aspect = aspect;
                Rows = rows;
                TargetFrameCaptureRequired = targetFrameCaptureRequired;
                Boundary = boundary;
            }

            public float Aspect { get; }
            public IReadOnlyList<SurvivorRow> Rows { get; }
            public bool TargetFrameCaptureRequired { get; }
            public string Boundary { get; }
            public int KnownAuthoredCount => Rows != null ? Rows.Count : 0;
        }
    }

    /// <summary>
    /// Optional no-draw host for the source-backed survivor transport. It is
    /// disabled by default and never activates a room light or shader buffer.
    /// </summary>
    [AddComponentMenu(
        "Endfield/Diagnostics/Gacha Light Survivor Transport (Default Off)")]
    [DisallowMultipleComponent]
    public sealed class EndfieldRecoveredGachaLightSurvivorDiagnostic : MonoBehaviour
    {
        [SerializeField] private bool diagnosticEnabled;
        [SerializeField] private Camera targetCamera;

        public bool DiagnosticEnabled => diagnosticEnabled;

        public bool TryEvaluate(
            out EndfieldRecoveredGachaLightSurvivorTransport.Frame frame,
            out string failure)
        {
            if (!diagnosticEnabled)
            {
                frame = default;
                failure = "diagnostic component is disabled";
                return false;
            }
            Camera camera = targetCamera != null ? targetCamera : GetComponent<Camera>();
            return EndfieldRecoveredGachaLightSurvivorTransport
                .TryPrepareSelectedAspect(camera, out frame, out failure);
        }
    }
}
