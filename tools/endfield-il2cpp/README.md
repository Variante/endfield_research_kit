# Endfield IL2CPP Metadata Helper

This folder is intentionally small. The maintained path is the offline metadata
catalog:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --cache-metadata
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus
python tools\endfield-il2cpp\catalog_option_flow_metadata.py --only-focus --body-context 4
python tools\endfield-il2cpp\map_body_targets_to_gameassembly.py
python scripts\animestudio\generate_dummydll.py --dry-run
```

`catalog_option_flow_metadata.py` parses a validated `global-metadata.dat`
directly. It does not need the game running, `GameAssembly.dll`, Cpp2IL, or
Il2CppDumper.

## Exact-build core type-surface catalog

`build_catalog.py` emits a build-specific core metadata/type-surface JSON
catalog for one exact pair of native inputs. It validates the complete
CodeRegistration module set and derives
MetadataRegistration using the same registration primitives as the DummyDll
generator:

```bat
python tools\endfield-il2cpp\build_catalog.py ^
  --metadata "...\global-metadata.dat" ^
  --gameassembly "...\GameAssembly.dll" ^
  --out reports\il2cpp\catalog.json
```

Every parsed metadata type, field, method, and parameter row is retained as a
top-level row. Type rows
carry `resolved` or `malformed` status; native layouts and method pointers
carry `resolved` or `unresolved` status when registration rows are null,
out-of-range, or unavailable. The output records both source SHA-256 hashes
and registration provenance and must not be reused after either input changes.
This first schema does not yet decode events, properties, generic parameters or
containers, exported type definitions, custom attributes, method specs, or
generic method tables; those are listed explicitly in
`diagnostics.unhandledMetadataSections` rather than being presented as full
game-class coverage.
The current exact build produces a large catalog, so publication uses compact
JSON and an atomic sibling staging file. Consumers should still avoid loading
multiple copies concurrently when a streaming query or future split-table
format would suffice.

### Coverage audit against AnimeStudio

After generating the exact-build catalog, inventory the managed type
definitions that AnimeStudio can actually load from the generated DummyDLLs,
then join them to committed object-index evidence:

```bat
set ASCLI=tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe

%ASCLI% dummydll-index ^
  --input tools\DummyDll ^
  --output scratch\animestudio\dummydll_types.json

python tools\endfield-il2cpp\audit_catalog_coverage.py ^
  --catalog reports\il2cpp\catalog.json ^
  --dummydll-index scratch\animestudio\dummydll_types.json ^
  --object-index export_full\recovered\AnimeStudio-cli\Persistent\object_index ^
  --object-index export_full\recovered\AnimeStudio-cli\StreamingAssets\object_index ^
  --out-json reports\export\il2cpp_catalog_coverage_latest.json ^
  --out-md reports\export\il2cpp_catalog_coverage_latest.md
```

The audit fails closed when native hashes differ, a DummyDLL no longer matches
`generation.json`, or an object index lacks its complete terminal summary or
committed output hashes. Rejected indexes remain visible in the report but do
not contribute object rows. Catalog-to-DummyDLL gaps are Cpp2IL schema gaps,
not proof that an IL2CPP class is absent; the actionable exporter queue is the
smaller join of catalog-confirmed script identities with partial
MonoBehaviours and no usable DummyDLL type. A name-only match is not considered
usable: the generated TypeDef token must identify that same catalog type. This
detects shifted or corrupted Cpp2IL type identities that Mono.Cecil can still
read structurally.

## DummyDll Generation

AnimeStudio can optionally use IL2CPP dummy assemblies to recover a
MonoBehaviour's managed class identity and construct a script-derived TypeTree
when the generated type is usable. Regenerate the repo-local set after a game
update only when script schema recovery is needed:

```bat
python scripts\animestudio\generate_dummydll.py --dry-run
python scripts\animestudio\generate_dummydll.py --replace
```

The dry run validates the installed `GameAssembly.dll` and
`global-metadata.dat`, discovers a unique CodeRegistration from the complete
metadata image/module-name set, derives the adjacent MetadataRegistration, and
reports whether the existing `tools\DummyDll` has current provenance. Never
reuse registration addresses from an older game build.

The real run clones Cpp2IL tag `2022.0.7` into the ignored local tool cache when
needed, idempotently applies
`scripts/animestudio/cpp2il-2022.0.7-endfield.patch`, builds it, and forces the
validated registrations through environment overrides added by that patch. It
generates under `tmp/animestudio/dummydll/`, requires the output DLL names to
exactly match the metadata images, checks that each DLL is a managed PE, and
only then publishes `tools\DummyDll`. `--replace` retains the previous set as a
timestamped sibling instead of deleting it.

Successful output includes `tools\DummyDll\generation.json` with source hashes,
registration summaries, the Cpp2IL commit and patch hash, per-DLL hashes, and
bounded malformed-image/type counts parsed from Cpp2IL. DummyDlls are recovered
schema stubs, not original managed implementations. A successful generation can
still omit malformed types; confirm the target class exists before expecting a
script-derived body decode.

Use `--game-root`, `--cpp2il-source`, or `--output` for one-off paths. Explicit
`--code-registration` and `--metadata-registration` are escape hatches only
after independent validation. `--no-prepare` requires an already patched
checkout, and `--keep-work-dir` retains raw Cpp2IL output and logs.

The script contributes to recovery as evidence, not as a normal WebUI build
step:

- confirms which dialog/timeline/option/trunk fields exist after a game update;
- proves when a hoped-for branch target is not present as a serialized field;
- names the short runtime method chain worth decoding next, with nearby methods;
- links unresolved metadata type indexes back to fields and method parameters;
- maps focused method targets to `GameAssembly.dll` addresses through
  CodeRegistration and extracts simple direct-call edges;
- when `--include-generic-instantiations` is enabled, maps a null open-generic
  codegen slot to its concrete `genericMethodPointers` body only when all
  matching shipped MethodSpecs share one entry point; distinct bodies remain
  explicitly ambiguous;
- writes diff reports so metadata drift is visible between versions.

Default report outputs:

- `reports/story/recovery/options/option_flow_runtime_metadata.json`
- `reports/story/recovery/options/option_flow_runtime_metadata.md`
- `reports/story/recovery/options/option_flow_runtime_metadata_diff.json`
- `reports/story/recovery/options/option_flow_runtime_metadata_diff.md`
- `reports/story/recovery/options/option_flow_body_targets_gameassembly.json`
- `reports/story/recovery/options/option_flow_body_targets_gameassembly.md`

## What to Inspect After Updates

Read reports in this order:

1. `reports/story/recovery/options/option_flow_runtime_metadata_diff.md`
2. `reports/story/recovery/options/option_flow_runtime_metadata_focus_diff.md`
3. `reports/story/recovery/options/option_flow_body_targets_gameassembly.md`
4. `reports/story/recovery/options/option_flow_runtime_metadata_focus.md`
5. `reports/story/recovery/options/option_flow_runtime_metadata.md`

Useful signals:

- metadata version, size, and sha256 changes;
- field changes on `DialogTimelineOptionData`, `DialogOptionPlayableAsset`,
  `DialogOptionBehaviour`, `DialogTrunkBehaviour`, `DialogTimelineManager`,
  `DialogTreeOptionNode`, and `DialogTreeExOptionNode`;
- body-target method changes around `DialogManager.Next` / `SelectIndex`,
  `_SelectIndexInTimeline`,
  `TryTriggerTrunkBindingOption`, `SetDialogOption`, `ResetDialogOption`,
  `OnJumpForward`, DialogTree `GetNextIndex`, and `SelectIndex`;
- unresolved type-index usage for option-related indexes such as the shared
  option parameter/index group used by `SetDialogOption` and
  `InitDialogOptions`;
- GameAssembly VA/RVA rows and direct-call edges around the focused body
  targets;
- new names containing `target`, `next`, `branch`, `route`, `jump`, `logic`,
  `condition`, `finish`, or `select`.

Treat new serialized fields as possible recovery evidence. Treat new methods as
audit targets only; method names alone are not enough to promote a WebUI route
rule.

## Metadata Recovery

`global-metadata.dat` is expected to come from the installed Endfield Unity
IL2CPP runtime data, not from this repo's WebUI exporter. `export.bat` does not
generate it. Cache and validate the installed copy before cataloging:

```bat
python tools\endfield-il2cpp\catalog_option_flow_metadata.py ^
  --metadata "D:\Program Files\Endfield Game\Endfield_Data\il2cpp_data\Metadata\global-metadata.dat" ^
  --cache-metadata
```

The cache lands at:

```text
export_full/recovered/il2cpp/global-metadata.dat
export_full/recovered/il2cpp/global-metadata_source.json
```

Normal catalog runs prefer the recovered cache first, then the local install
path. `--cache-metadata` prefers the local install path so a game update
refreshes the cache instead of reusing the old copy. If neither exists, pass
`--metadata <path>` explicitly.

## Current Findings

The July 2026 metadata catalog confirmed that `DialogTimelineOptionData` only
has `optionIndex`, `changeFinishNum`, and `targetFinishNum`; the missing branch
target for unresolved WebUI option groups is not a hidden extra field there.
The current installed build uses CodeRegistration `0x18b9217d0` and
MetadataRegistration `0x18b921c30`.

Native mapping also establishes the Timeline route model:

- `RuntimeClip.<optionIndex>` is the active trunk-clip selector;
- `TimelinePlayable` carries current, new, and previous option indexes;
- `RuntimeJumpClip` carries jump direction and post-jump option state;
- the parent Runtime Jump Track's `m_Clips[].optionIndex`, start, duration,
  and asset PPtr supply the source option and jump interval;
- `DoJump` / `DoReverseJump` pass current, previous, and destination option
  state into `TimelineRuntimeUtils`.

The serialized Runtime Jump asset must therefore be joined to its parent track
clip. A zero-index adjacent trunk clip is shared continuation, not an
option-specific reply, unless an overlapping option-indexed Runtime Jump proves
a route. Key suffixes and line-number gaps are not runtime placement fields.

Useful mapped runtime targets include:

- `DialogManager.Next` / `SelectIndex`
- `DialogTimelineManager._SelectIndexInTimeline`
- `TryTriggerTrunkBindingOption`
- `SetDialogOption` / `ResetDialogOption`
- `DialogOptionBehaviour.InitDialogOptions`
- `DialogTrunkBehaviour.InitDialogTrunk`
- `DialogSignOptionPlayableAsset.GenPlayable`
- DialogTree `GetNextIndex` / `_TrySelectBranch` / `SelectIndex`
- `RuntimeClip.TryGetJumpClip`, `TimelinePlayable.DoJump` /
  `DoReverseJump`, and `TimelineRuntimeUtils.DoJump` / `DoReverseJump`

Old live-process dump and decompiler experiments were useful provenance, but
they are no longer the active tool path for WebUI recovery quality work.
