# AnimeStudio MonoBehaviour Managed-Reference Recovery

Generated 2026-06-28 while investigating `reports/20260627_215637`
`json_by_type` MonoBehaviour partial decode warnings.

## Scope

This pass only covered MonoBehaviour serialized TypeTree and managed-reference
decode behavior in `tools/AnimeStudio`. It intentionally did not address Shader
or AnimationClip conversion warnings.

## Baseline Evidence

Report logs:

- `reports/20260627_215637/StreamingAssets/StreamingAssets_animestudio_json_by_type.stdout.log`
- `reports/20260627_215637/Persistent/Persistent_animestudio_json_by_type.stdout.log`

Parsed warning shape:

| Source | Partial MonoBehaviour warnings | Main error shapes |
| --- | ---: | --- |
| `StreamingAssets` | 11,948 | 9,515 `No bytes remain while reading data:ReferencedObjectData`; 2,263 huge `ReadAlignedString`; remaining negative string lengths |
| `Persistent` | 1,486 | 1,175 `No bytes remain while reading data:ReferencedObjectData`; 252 huge `ReadAlignedString`; remaining negative string lengths |

All sampled warnings came from the serialized TypeTree path. DummyDll/script
TypeTree recovery was attempted in the targeted samples but could not resolve
the MonoScript (`scriptDerivedTypeTreeStatus: monoScriptUnresolved`), so the
fix focused on the serialized final `ManagedReferencesRegistry` tail.

## Findings

The serialized TypeTree describes `ManagedReferencesRegistry.RefIds[].data` as a
`ReferencedObjectData` node with no child schema. The generic TypeTree reader
therefore reaches the managed-reference payload boundary and either:

- tries to read another managed-reference object from payload bytes, causing
  huge or negative string lengths, or
- reaches an empty zero-length `ReferencedObjectData` tail and reports
  `No bytes remain`.

Existing CLI recovery could already parse many final managed-reference registry
tails after partial decode, but it stored the result only under
`$animestudio.recoveredManagedReferences` and still logged a warning.

The dialog option samples also exposed a valid null-like registry entry:

- referenced field value: `conditionData.rid = -2`
- registry entry: `rid = -2`, empty class/ns/asm strings, zero data bytes

The previous recovery rejected all non-positive RIDs, so those dialog option
registries stayed partial.

## Implemented Behavior

`tools/AnimeStudio/AnimeStudio.CLI/Exporter.cs` now:

- delays partial-warning emission until after final `ManagedReferencesRegistry`
  recovery has been attempted;
- when recovery succeeds, writes the recovered registry to the real payload
  field `references` instead of only metadata;
- records concise metadata under
  `$animestudio.managedReferencesRegistryRecovered` and
  `$animestudio.managedReferencesRegistryRecovery`;
- does not emit `partialTypeTreeDecode` or a warning for recovered final
  registry tails;
- still emits the old partial warning and `partialTypeTreeDecode` metadata when
  recovery fails;
- accepts negative empty-type managed-reference entries as null/sentinel
  registry records and emits their data as `{ "$null": true, "$inferred": true }`;
- lowers the managed-reference minimum header size from 24 to 20 bytes so
  zero-length null/sentinel entries are valid when scanning for later entries.

## Targeted Verification

Rebuild:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded with 0 warnings and 0 errors on the final rebuild.

Persistent positive-RID sample:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" ^
  tmp\animestudio_mb_after2_character ^
  --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType ^
  --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll ^
  --filter_data tmp\animestudio_monobehaviour_character_filter.json
```

Result: exit code 0, no warning output. The output
`CharacterDisplayConfig_p0EEC0AFE8247A15F.json` has
`managedReferencesRegistryRecovered: true`, `recoveredRidCount: 31`, no
`partialTypeTreeDecode`, and a top-level `references` payload.

StreamingAssets negative-RID dialog sample:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe ^
  "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\2FA0A1186A99B33466EF687A717704F3.chk" ^
  tmp\animestudio_mb_after2_dialog ^
  --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType ^
  --export_type JSON --types MonoBehaviour:Both --dummy_dlls tools\DummyDll ^
  --filter_data tmp\animestudio_monobehaviour_dialog_filter.json
```

Result: exit code 0, no warning output. The target
`DialogOptionPlayableAsset(Clone)(Clone)_p56DF34319DFF7FDF.json` has
`managedReferencesRegistryRecovered: true`, `recoveredRidCount: 1`, no
`partialTypeTreeDecode`, and `references.RefIds[0].rid = -2` with
`data.$null = true`.

## Remaining Risks

- This was verified with targeted filters, not a full `json_by_type` refresh.
- Some report warnings with corrupt-looking string lengths may still fail if
  their registry tail cannot be separated into plausible managed-reference
  headers.
- DummyDll script TypeTree recovery remains limited by unresolved MonoScript
  links in the sampled bundles.
- The recovery data for positive managed-reference payloads is still heuristic;
  it preserves type, RID, offsets, lengths, string hints, RID links, and known
  dialog layouts, but it is not a full field-accurate deserializer for every
  managed-reference class.

## 2026-06-28 DialogOption Recheck

No `Exporter.cs` change was made in this pass. The current CLI already recovers
the reproduced `DialogOptionPlayableAsset` registries that older generated JSON
left as `ReferencedObjectData` EOF partial decodes.

Huygens StreamingAssets sample:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\79C9C13CFD1A1A38E3C8279B47406BCD.chk" "tmp\animestudio_dialog_option_only_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^DialogOptionPlayableAsset"
```

Result: exit code 0 in 25.6 seconds. The filtered run produced 45
`DialogOptionPlayableAsset*.json` files. All showed
`managedReferencesRegistryRecovered: true` and
`managedReferencesRegistryFullyDecoded: true`; none contained `$heuristic`,
`$unparsed`, or `$partial` markers. The recovered `conditionData.rid = -2`
entries are represented as a one-entry registry with an empty type and
`data.$null = true`.

Broader same-block dialog-name check:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\StreamingAssets\VFS\7064D8E2\79C9C13CFD1A1A38E3C8279B47406BCD.chk" "tmp\animestudio_dialog_named_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^Dialog"
```

Result: exit code 0 in 16.2 seconds. The run produced 3,554 JSON files and no
literal `$heuristic`, `$unparsed`, `$partial`, or `$partialDecoded` markers.

The older generated file
`export_full/recovered/AnimeStudio-cli/Persistent/json_by_type/MonoBehaviour/DialogOptionPlayableAsset(Clone)(Clone)_p107218516523097B.json`
still contains stale `partialTypeTreeDecode` metadata:

```text
EndOfStreamException: No bytes remain while reading data:ReferencedObjectData
```

Re-running the current CLI against that Persistent source block:

```bat
.\tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe "D:\Program Files\Endfield Game\Endfield_Data\Persistent\VFS\7064D8E2\3267B09A76643181B4083C1E60B678D1.chk" "tmp\animestudio_dialog_option_persistent_current" --game ArknightsEndfield --logger_flags Warning Error --group_assets ByType --export_type JSON --types MonoBehaviour:Both --names "^DialogOptionPlayableAsset"
```

Result: exit code 0 in 9.6 seconds. The run produced 46 option files, all with
`managedReferencesRegistryRecovered: true` and
`managedReferencesRegistryFullyDecoded: true`. The matching current output
`DialogOptionPlayableAsset(Clone)(Clone)_p107218516523097B.json` contains the
top-level recovered `references` registry and no `partialTypeTreeDecode`.

A broad, aborted all-MonoBehaviour probe on the Huygens block produced 59,735
parseable JSON files before being stopped. A structured scan found 35 remaining
`$heuristic`/`$unparsed` payload records across 15 heuristic registries, but
none were dialog managed-reference classes. The sampled remaining types were
animation event handlers such as `PostAudioHandler`, `FootStepHandler`, and
`WeaponVisibleHandler` under `Beyond.Gameplay.View.Animation`.
