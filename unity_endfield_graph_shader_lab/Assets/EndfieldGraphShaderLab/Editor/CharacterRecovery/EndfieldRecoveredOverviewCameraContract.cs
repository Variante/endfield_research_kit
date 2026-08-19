using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Per-character Character Info overview camera, read from
    /// charinfo_overview_camera_contract.json.
    ///
    /// The contract is built by tools/build_charinfo_overview_camera_contract.py
    /// from the authored track_chr_&lt;template&gt;.prefab Cinemachine rigs, whose
    /// overview state is the vcam_overview and lookat_overview pair. It replaces
    /// the two hand-transcribed entries that previously lived in
    /// EndfieldManifestCharacterSetup and covers 31 characters. chr_0035_liino
    /// ships in the Persistent VFS rather than StreamingAssets, so it is only
    /// reached when both asset maps are walked.
    ///
    /// The entry also carries the Cinemachine lens. Field of view varies per
    /// character across five distinct values just above 20 degrees, so it is
    /// read from here rather than passed in by the caller.
    ///
    /// This is framing only. The per-frame cursor and UIGyroscopeEffect offset
    /// remains unrecovered, so two captures of the same character still differ
    /// and comparison continues to need alignment.
    /// </summary>
    internal static class EndfieldRecoveredOverviewCameraContract
    {
        private const string ContractPath =
            "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/" +
            "charinfo_overview_camera_contract.json";

        internal sealed class Entry
        {
            internal string TemplateId;
            internal string Actor;
            internal string Track;
            internal Vector3 CameraPosition;
            internal Vector3 LookAtPosition;
            internal Quaternion SerializedVcamRotation;
            internal float FieldOfView;
            internal float NearClipPlane;
            internal float FarClipPlane;
        }

        [Serializable]
        private sealed class SerializedEntry
        {
            public string templateId;
            public string actor;
            public string track;
            public float[] vcamPosition;
            public float[] vcamRotation;
            public float[] lookAtPosition;
            public float fieldOfView;
            public float nearClipPlane;
            public float farClipPlane;
        }

        [Serializable]
        private sealed class SerializedAlias
        {
            public string from;
            public string to;
        }

        [Serializable]
        private sealed class SerializedContract
        {
            public SerializedEntry[] entries;
            public SerializedAlias[] actorAliasEntries;
        }

        private static Dictionary<string, Entry> cache;

        internal static Entry Resolve(string actorName)
        {
            if (string.IsNullOrEmpty(actorName))
                throw new ArgumentNullException(nameof(actorName));

            Dictionary<string, Entry> entries = Load();
            if (entries.TryGetValue(actorName.ToLowerInvariant(), out Entry entry))
                return entry;

            throw new ArgumentOutOfRangeException(
                nameof(actorName),
                actorName,
                "No recovered CharInfo overview camera for this actor. The " +
                "contract covers: " + string.Join(", ", entries.Keys.OrderBy(k => k)));
        }

        internal static IReadOnlyCollection<string> Actors => Load().Keys;

        private static Dictionary<string, Entry> Load()
        {
            if (cache != null)
                return cache;

            string absolute = Path.Combine(Directory.GetCurrentDirectory(), ContractPath);
            if (!File.Exists(absolute))
                throw new FileNotFoundException(
                    "Recovered CharInfo overview camera contract is missing. Rebuild it " +
                    "with tools/build_charinfo_overview_camera_contract.py.",
                    ContractPath);

            SerializedContract parsed =
                JsonUtility.FromJson<SerializedContract>(File.ReadAllText(absolute));
            if (parsed?.entries == null || parsed.entries.Length == 0)
                throw new InvalidOperationException(
                    "Recovered CharInfo overview camera contract has no entries: " +
                    ContractPath);

            var map = new Dictionary<string, Entry>(StringComparer.OrdinalIgnoreCase);
            foreach (SerializedEntry item in parsed.entries)
            {
                if (item.vcamPosition == null || item.vcamPosition.Length != 3 ||
                    item.lookAtPosition == null || item.lookAtPosition.Length != 3 ||
                    item.vcamRotation == null || item.vcamRotation.Length != 4)
                {
                    throw new InvalidOperationException(
                        $"Recovered overview camera entry '{item.actor}' is incomplete.");
                }

                // Field of view varies per character, so a zero here means the
                // Cinemachine lens did not survive extraction rather than a
                // legitimately absent value.
                if (item.fieldOfView <= 0.0f ||
                    item.nearClipPlane <= 0.0f ||
                    item.farClipPlane <= item.nearClipPlane)
                {
                    throw new InvalidOperationException(
                        $"Recovered overview camera entry '{item.actor}' has no " +
                        "usable Cinemachine lens. Rebuild the contract with " +
                        "tools/build_charinfo_overview_camera_contract.py.");
                }

                map[item.actor.ToLowerInvariant()] = new Entry
                {
                    TemplateId = item.templateId,
                    Actor = item.actor,
                    Track = item.track,
                    CameraPosition = new Vector3(
                        item.vcamPosition[0], item.vcamPosition[1], item.vcamPosition[2]),
                    LookAtPosition = new Vector3(
                        item.lookAtPosition[0], item.lookAtPosition[1], item.lookAtPosition[2]),
                    SerializedVcamRotation = new Quaternion(
                        item.vcamRotation[0], item.vcamRotation[1],
                        item.vcamRotation[2], item.vcamRotation[3]),
                    FieldOfView = item.fieldOfView,
                    NearClipPlane = item.nearClipPlane,
                    FarClipPlane = item.farClipPlane,
                };
            }

            // The lab's actor directory name does not always match the prefab
            // template: template chr_0003_endmin is imported as Endminf. Without
            // the alias, framing that actor fails closed even though its camera
            // is present.
            if (parsed.actorAliasEntries != null)
            {
                foreach (SerializedAlias alias in parsed.actorAliasEntries)
                {
                    if (string.IsNullOrEmpty(alias.from) || string.IsNullOrEmpty(alias.to))
                        continue;
                    if (!map.TryGetValue(alias.to, out Entry target))
                    {
                        throw new InvalidOperationException(
                            $"Recovered overview camera alias '{alias.from}' points " +
                            $"at missing actor '{alias.to}'.");
                    }
                    map[alias.from.ToLowerInvariant()] = target;
                }
            }

            cache = map;
            return cache;
        }
    }
}
