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
  registry records and emits their data as `{ "$null": true, "$inferred": true }`.

## Targeted Verification

Rebuild:

```bat
.\scripts\animestudio\rebuild.bat -Target CLI -NoRestore
```

Result: build succeeded. The final rebuild reported 14 existing warnings in
non-CLI projects and 0 errors.

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
