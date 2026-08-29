using System;
using System.IO;
using System.Text;
using UnityEditor;
using UnityEngine;

namespace EndfieldGraphShaderLabEditor
{
    /// <summary>
    /// Imports build-validated ACL runtime contracts into generated Unity
    /// assets. Jobs are external JSON so the importer is character-agnostic.
    /// </summary>
    public static class RecoveredAclClipDataImporter
    {
        [Serializable]
        private sealed class ImportItem
        {
            public string contractJson;
            public string assetPath;
        }

        [Serializable]
        private sealed class ImportJob
        {
            public ImportItem[] items = Array.Empty<ImportItem>();
        }

        public static void ImportConfigured()
        {
            string jobPath = Environment.GetEnvironmentVariable(
                "ENDFIELD_RECOVERED_ACL_IMPORT_JOB");
            if (string.IsNullOrEmpty(jobPath) || !File.Exists(jobPath))
                throw new InvalidOperationException(
                    "ENDFIELD_RECOVERED_ACL_IMPORT_JOB does not name an existing job JSON");

            ImportJob job = JsonUtility.FromJson<ImportJob>(
                File.ReadAllText(jobPath, Encoding.UTF8));
            if (job == null || job.items == null || job.items.Length == 0)
                throw new InvalidDataException("ACL import job contains no items");

            foreach (ImportItem item in job.items)
                Import(item);
            AssetDatabase.SaveAssets();
            AssetDatabase.Refresh();
            Debug.Log($"Imported {job.items.Length} validated ACL runtime contract assets.");
        }

        private static void Import(ImportItem item)
        {
            if (item == null || string.IsNullOrEmpty(item.contractJson) ||
                !File.Exists(item.contractJson))
                throw new InvalidDataException("ACL contract JSON is missing");
            if (string.IsNullOrEmpty(item.assetPath) ||
                !item.assetPath.StartsWith("Assets/", StringComparison.Ordinal) ||
                !item.assetPath.EndsWith(".asset", StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException(
                    "ACL output must be a project-relative Assets/*.asset path");

            string directory = Path.GetDirectoryName(item.assetPath)?.Replace('\\', '/');
            if (string.IsNullOrEmpty(directory))
                throw new InvalidDataException("ACL output asset directory is malformed");
            EnsureAssetFolder(directory);

            var imported = ScriptableObject.CreateInstance<
                EndfieldGraphShaderLab.RecoveredAclClipData>();
            JsonUtility.FromJsonOverwrite(
                File.ReadAllText(item.contractJson, Encoding.UTF8), imported);
            if (!imported.TryValidate(out string failure))
            {
                UnityEngine.Object.DestroyImmediate(imported);
                throw new InvalidDataException(
                    "ACL contract failed runtime validation: " + failure);
            }
            imported.name = imported.sourceClipName;

            var existing = AssetDatabase.LoadAssetAtPath<
                EndfieldGraphShaderLab.RecoveredAclClipData>(item.assetPath);
            if (existing == null)
            {
                AssetDatabase.CreateAsset(imported, item.assetPath);
            }
            else
            {
                EditorUtility.CopySerialized(imported, existing);
                existing.name = imported.name;
                EditorUtility.SetDirty(existing);
                UnityEngine.Object.DestroyImmediate(imported);
            }
        }

        private static void EnsureAssetFolder(string path)
        {
            string[] parts = path.Split('/');
            if (parts.Length == 0 || parts[0] != "Assets")
                throw new InvalidDataException("ACL asset folder must start at Assets");
            string current = "Assets";
            for (int index = 1; index < parts.Length; index++)
            {
                string next = current + "/" + parts[index];
                if (!AssetDatabase.IsValidFolder(next))
                    AssetDatabase.CreateFolder(current, parts[index]);
                current = next;
            }
        }
    }
}
