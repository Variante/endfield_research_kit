# AnimeStudio P3 MonoBehaviour Pilot - 2026-07-03

## Context

P3 in `memory/improvement_plan_20260701.md` calls for a fresh decoded
MonoBehaviour index with the current AnimeStudio exporter. Before rewriting the
full million-file MonoBehaviour corpus, a targeted pilot was run against one
known Persistent chunk and the existing 78-name enemy filter.

## Command

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" tmp\p3_mono_pilot_data_eny_20260703 --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --map_op None --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll --names tmp\data_eny_probe_20260630\names_persistent_3267.txt
```

The CLI rebuild succeeded with 14 existing warnings and 0 errors.

## Result

- The pilot completed with exit code 0 and an empty warning/error log.
- Output: 78 JSON files under
  `tmp/p3_mono_pilot_data_eny_20260703/MonoBehaviour/`.
- All 78 files have `$animestudio.typeTreeSource = serializedType`.
- All 78 files retain `serializedTypeTreeError`.
- All 78 files now have `managedReferencesRegistryRecovered = true`.
- All 78 files still contain `$partial` markers.
- No file contains `managedReferencesRegistryRecoveryFailure`.

Compared to the existing stale Persistent export, all 78 matching JSON files
changed. The stale files were much smaller partial TypeTree outputs
(`2,000,327` total bytes for this sample) and did not carry the recovered
managed-reference registry fields. The fresh pilot files total `15,362,800`
bytes and include top-level `references`.

## Interpretation

The current exporter materially improves this stale enemy MonoBehaviour sample
without dropping rows or hiding partial decode status. It is therefore
reasonable to proceed to a conservative broad P3 refresh with
`--animestudio-jobs 1`, then rebuild a temporary decoded MonoBehaviour index and
bucket remaining `managedReferencesRegistryRecoveryFailure.reason` values.

This pilot does not solve the remaining partial TypeTree body decode gaps.
Those remain real parser work after the corpus is refreshed.
