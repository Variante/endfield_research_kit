# AnimeStudio MonoBehaviour Probe - 2026-07-02

## Context

Older story export logs under `reports/20260627_161728/` reported 13,434
partial MonoBehaviour warnings. The sampled warnings stopped at
`data:ReferencedObjectData` while reading the final
`ManagedReferencesRegistry` field, with zero metadata-only JSON fallbacks.

## Probe

Ran a targeted current AnimeStudio CLI probe against the installed Persistent
VFS data with:

- `--dummy_dlls D:\fluffy-dump\tools\DummyDll`
- `--mono_behaviour_type_tree_priority ScriptFirst`
- `--map_op CABMap,Load`
- `--map_name endfield_persistent_assets`
- one-row `--filter_data` for the old `MonoBehaviour#392` warning sample

The first name-filter attempt exported nothing because `MonoBehaviour#392` is a
runtime display label, not an asset-map `Name`. The successful filter used the
asset-map row for:

- source:
  `D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\0CE8FA57\FCF21734CEDE10386D06530C787F510D.chk`
- offset: `13771353`
- pathID: `-8483177569919634855`
- original exported payload:
  `export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour/MonoBehaviour#392_p8A45B2F22A60F259.json`

The filtered run still exported the containing bundle's MonoBehaviours rather
than only one object, so results were read by `pathId` and `rawDataSha256`.

## Results

For the exact old sample (`rawDataSha256`
`725b7d81eb4b77d8d451c93301287bf946d2a338ad01dc34b37d053301b1cee2`):

- current probe output by raw hash:
  `tmp/mb_probe_script_first_filter/MonoBehaviour/MonoBehaviour#86_p8A45B2F22A60F259.json`
- duplicate script-resolved output:
  `tmp/mb_probe_script_first_filter/MonoBehaviour/UIButton_p8A45B2F22A60F259.json`
- `managedReferencesRegistryRecovered`: `true`
- `managedReferencesRegistryFullyDecoded`: `true`
- recovered registry: version `2`, count `1`, rid `-2`, zero-length inferred
  null data at offset `748`
- no hard metadata-only fallback

This means the old warning for this sample is stale for the current CLI: the
current exporter recovers the final managed-reference tail and suppresses the
partial warning when `recoveredManagedReferencesTail` is true.

ScriptFirst did not improve schema decoding:

- probe JSON files: `1281`
- `typeTreeSource`: all `serializedType`
- script-derived status counts:
  - `typeDefinitionNotFound`: `630`
  - `monoScriptUnresolved`: `640`
  - `resolved`: `10`
  - `typeTreeConversionFailed`: `1`
- script-derived usable TypeTrees: `0`

Even when MonoScript resolves, the current DummyDlls often produce only the
12-node base MonoBehaviour TypeTree. For the duplicate `UIButton` output,
`scriptAssemblyName` was `UI.Beyond.dll` and `scriptFullName` was
`Beyond.UI.UIButton`, but `scriptDerivedTypeTreeStatus` was
`typeDefinitionNotFound`. `tools/DummyDll/UI.Beyond.dll` exists but is only
4 KB, so it is not rich enough for this recovery path.

## Interpretation

The short-term MonoBehaviour recovery path should focus on current serialized
partial recovery and managed-reference classification. Broad ScriptFirst runs
with the current DummyDll set are not expected to reduce warnings because the
script-derived TypeTrees are not usable.

## Next Steps

1. Prefer rerunning a current focused story JSON export before spending time on
   the stale June 27 partial warning counts.
2. If ScriptFirst recovery is still desired, generate richer DummyDll/script
   schemas first; simply loading CABMap dependencies is not enough.
3. Keep the export summary distinction between real partial failures and
   recovered `ManagedReferencesRegistry` tails so future warning counts do not
   overstate lost data.
