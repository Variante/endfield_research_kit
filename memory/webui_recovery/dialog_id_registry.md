# DialogIdTable Registry Recovery

This document records the May 2026 work that added the runtime
`DialogIdTable` registry as a first-class evidence source for the WebUI's
line-order recovery. It captures the motivation, the IL2CPP investigation
that grounded the work, the resulting scripts and data flow, and the
operational notes future maintainers need (the game does **not** need to
be running; game updates flow through automatically; here are the bounded
ways the recovery can break).

## TL;DR

- The WebUI's line-order recovery now consults Endfield's authoritative
  runtime dialog registry: `Beyond.Gameplay.DialogIdTable`. A `dlg_*` scene
  that is absent from this table cannot be loaded by the runtime.
- Two evidence-grounded reason codes replace the old `lineIdSuffix`
  fallback warning:
  - `unregisteredScene` — sceneKey absent from `DialogIdTable`; the runtime
    has no entry point for it; presented order is the table layout that
    `DialogTextTable` happens to use.
  - `dialogTrunkRowIteration` — sceneKey present in `DialogIdTable` but no
    Timeline / dialogTree source recovered; `DialogTrunkBehaviour` walks
    `DialogTextTable` rows by sceneKey prefix in table order, which equals
    suffix order when no row has moved.
- Every conv JSON now carries a `_debug.runtimeRegistry` evidence block that
  the WebUI (or any downstream tool) can show directly.
- Game does **not** need to be running for this recovery. It runs offline
  against the disk-side `DialogIdTable.json` produced by
  `export_full_from_game.py`.
- Game updates flow through automatically: rerun `export.bat`. The registry
  rebuilds itself from the freshly-extracted `DialogIdTable.json` and all
  downstream conv JSONs / warnings refresh.
- The IL2CPP class hierarchy that justifies the reasoning was confirmed
  by a one-shot scan of `global-metadata.dat`. That scan does not need to
  be repeated unless the game version bumps in a way that changes class
  names.

## Background: why we did this

The presenting problem: the WebUI showed "no line-order data found" warnings
for five `dlg_e10m3_*` / `dlg_e10m4_*` scenes that contained document-style
content (consent forms, handover documents, letters, broken-recorder memos).
The recovery had fallen back to `lineIdSuffix` mode — sort by the `_NNN`
suffix on each line id — and was honestly reporting that no authored source
matched.

Two layers of investigation followed:

1. **Asset-side audit.** `dlg_e10m3_10/11/12, dlg_e10m4_16/17` have no
   `dlgtl_*_sub_1` Timeline asset (confirmed by AnimeStudio CLI AssetMap),
   no LevelScript chain reference (confirmed by mission graph), and zero
   matches in the AnimeStudio asset map across 1.35 M asset entries. The
   only references anywhere in the structured tree are in `DialogTextTable`
   itself (and `AudioDialog` for `dlg_e10m4_16` only).
2. **Runtime-side audit.** We pursued IL2CPP decompilation to confirm the
   C# code path. Static decompilation is blocked because Endfield's anti-
   tamper layer (`HGP.dll`) obfuscates `MetadataRegistration`. A runtime
   dump succeeded via pe-sieve + a custom PowerShell wrapper around
   `RtlCreateProcessReflection`, plus a `procdump -ma` full memory snapshot
   when pe-sieve alone wasn't enough. After all that, we found `Metadata
   Registration` is in fact in process memory but in HGP-relocated memory
   that neither Cpp2IL nor Il2CppDumper can decode.

   **At that point we realised metadata.dat alone — without `Metadata
   Registration` — is enough**: class and method names live in plaintext
   inside `global-metadata.dat`'s string section. A grep of metadata.dat
   gave us the complete vocabulary of Endfield's dialog system without
   needing the actual runtime binary to be decompiled. That's the evidence
   base for everything below.

Key findings from the metadata.dat scan:

- There is exactly **one** dialog-loading class hierarchy in the runtime.
  `Beyond.Gameplay.Core.DialogManager` (split across `.DialogTree.cs`,
  `.Level.cs`, `.LifeCycle.cs`, `.Timeline.cs`), `DialogTrunkBehaviour`,
  `DialogTimelineManager`, `DialogTreeController`, and
  `DialogOptionBehaviour`. There is **no** separate `Mingbaopu*`,
  `Letter*Panel`, `Memo*Controller`, `BulletinBoard*`, `DocumentController`,
  `Jiaojieshu*`, or `Tongyishu*` class anywhere. Every dialog scene goes
  through the same loader; the document-style scenes are not a separate
  flavor of UI.
- `Beyond.Gameplay.DialogIdTable` exists as the runtime dialog registry,
  with a per-record type `DialogBriefInfo`. This is the authoritative
  source for "what dialogs can the runtime load."

Once we knew the runtime registry was on disk, the answer to the original
question fell out for free: the five orphan scenes aren't in
`DialogIdTable`. The runtime has no entry point for them. They are
unreachable content, and the suffix order we were calling "fallback" is
the only sequence those `DialogTextTable` rows can ever appear in.

## What's on disk

```
export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json
export_full/structured/Persistent/Data/Json/GameplayConfig/DialogIdTable.json
```

Both files are extracted from the game install by `export_full_from_game.py`
as part of the existing structured-asset export. They are MemoryPack-encoded
binary records, not JSON despite the extension — each record is a
`DialogBriefInfo` keyed by a dialog ID string. We do **not** fully parse
the binary; we just extract the ASCII identifiers, which is enough to
build the registry. ID format observed:

- Scene-root keys: `dlg_<sceneKey>` (e.g. `dlg_e10m3_1`)
  - Some scene roots use a non-numeric suffix instead of a number — e.g.
    `dlg_a1m4_OpenUI`, `dlg_a1m4_NewSeries`. Those still count as scene
    roots.
- Per-line keys: `dlg_<sceneKey>_<trunkIdx>_<lineDigits>` where trunkIdx
  is a small positive int and lineDigits is 3-5 digits (e.g.
  `dlg_e10m3_1_1_001`, `dlg_e10m3_1_2_001`, ...).
- Option keys: `option_dlg_<sceneKey>_<groupIdx>_<optionDigits>` where
  optionDigits is three digits (e.g. `option_dlg_e2m5_3_1_001`). These are
  runtime option registrations, not route targets by themselves.
- Some scenes appear only through per-line keys with no explicit scene-
  root token. We still count those as registered.

Note: the per-line keys in `DialogIdTable` use a different numbering scheme
than `DialogTextTable`. `DialogTextTable` has `dlg_e10m3_1_001` ...
`dlg_e10m3_1_005` (flat per-scene); `DialogIdTable` has
`dlg_e10m3_1_1_001` (scene 1, trunk 1, position 001). The runtime maps
between the two via the trunk decomposition we don't fully parse.

## Scripts

### `scripts/recover_dialog_id_registry.py`

Extracts `DialogIdTable.json` into a fast-lookup JSON registry.

Usage (already in `export.bat`):

```
python scripts/recover_dialog_id_registry.py --quiet
```

Input: `export_full/structured/StreamingAssets/Data/Json/GameplayConfig/DialogIdTable.json`

Output: `export_full/recovered/dialog_id_table_index.json` — a dict keyed
by sceneKey:

As of the 2026-05-12 extractor pass, the current installed data yields:

- `4,496` registered scenes.
- `1,058` scenes with trunk/line decomposition.
- `1,185` scenes with option registrations.
- `3,725` extracted option IDs.

```json
"dlg_e10m3_1": {
  "registered": true,
  "hasRootKey": true,
  "trunkCount": 3,
  "trunkIndices": [1, 2, 3],
  "lineCount": 4,
  "linesByTrunk": {
    "1": ["dlg_e10m3_1_1_001", "dlg_e10m3_1_1_002"],
    "2": ["dlg_e10m3_1_2_001"],
    "3": ["dlg_e10m3_1_3_001"]
  },
  "optionGroupCount": 1,
  "optionCount": 2,
  "optionsByGroup": {
    "1": ["option_dlg_e10m3_1_1_001", "option_dlg_e10m3_1_1_002"]
  }
}
```

Observed registry size on the current dump: 4 496 scenes (1 058 with per-
trunk decomposition, 3 438 root-key-only).

### `scripts/scene_order_gap_shared.py` (changed)

Module-level helpers added:

- `load_dialog_id_registry(path=None)` — returns the registry dict from
  the default location; cached.
- `analyze_line_order(conv, *, dialog_id_registry=None)` — optional kwarg.
- `build_scene_order_disorder_warning(conv, *, dialog_id_registry=None)` —
  same.

The `lineIdSuffix` branch was rewritten. When suffix order equals raw
table order (`moved_line_ids` empty), it now decides between:

- `unregisteredScene` — registry has no entry for this sceneKey. The
  runtime has no entry point, so there is no "real" runtime order to
  reconcile with. Status: `direct`, no warning.
- `dialogTrunkRowIteration` — registry has the sceneKey but no Timeline
  or dialogTree source matched. `DialogTrunkBehaviour` would iterate
  `DialogTextTable` rows by sceneKey prefix; suffix order is what that
  iteration produces. Status: `direct`, no warning.

If neither path applies (suffix sort did move lines), the old
`lineIdSuffix` fallback status is kept and a warning is emitted as before.

### `scripts/annotate_conv_with_registry.py`

Stamps each conv JSON's `_debug` block with a `runtimeRegistry` evidence
record. This is pure surfacing — the WebUI can render the evidence
directly without re-deriving it. The block looks like:

```json
"runtimeRegistry": {
  "registered": true,
  "trunkCount": 3,
  "trunkIndices": [1, 2, 3],
  "lineCount": 4,
  "lineCountWebui": 5,
  "hasRootKey": true,
  "optionsByGroup": {
    "1": ["option_dlg_e2m5_3_1_001", "option_dlg_e2m5_3_1_002"]
  },
  "reason": "sceneKey is registered in Beyond.Gameplay.DialogIdTable",
  "lineCountDelta": 1,
  "note": "webui has 5 line(s) but DialogIdTable's per-trunk line entries total 4; the extra webui line(s) may be summary/hint rows that the runtime doesn't address by trunk id"
}
```

The soft `lineCountDelta` / `note` fields fire whenever the registry's
per-trunk line total disagrees with the webui line count. Many scenes have
extra webui lines (summary text, hints) that don't show up in the runtime's
trunk-indexed registry. This is informational, not a bug indicator — but
it surfaces inconsistencies for inspection.

### `scripts/rewrite_scene_order_warnings.py`

One-shot warning rebuild for conv JSONs. Updated to pass the registry to
`build_scene_order_disorder_warning`. Run this after editing
`scene_order_gap_shared.py` to refresh warnings without a full
`build_story.py` rerun.

## Wiring

`export.bat` now runs the registry recovery after the main export and
before `build_updates.py`:

```
python .\scripts\export_full_from_game.py --skip-raw-vfs --skip-source-inventory %*
python .\scripts\recover_dialog_id_registry.py --quiet
python .\scripts\webui\build_updates.py
python .\scripts\webui\build_story.py --languages CN --default-language CN
python .\scripts\webui\build_assets.py
```

`build_story.py` loads the registry once, stamps each dialog conv with
`_debug.runtimeRegistry`, and passes the same registry into
`shared_build_scene_order_disorder_warning(payload)`.

For pre-existing builds, `scripts/annotate_conv_with_registry.py` and
`scripts/rewrite_scene_order_warnings.py` are stand-alone refreshers; you
can run them without rerunning the full pipeline.

## Operational answers

### Does this need the game running in the background?

No. Everything in `export.bat` reads from the **installed game files on
disk** (`D:\Program Files\Endfield Game\Endfield_Data\`). The game can stay
closed; on most updates we only need the files.

The IL2CPP runtime-dump work (pe-sieve, procdump, custom PowerShell P/Invoke
wrappers around `RtlCreateProcessReflection`) **did** need the game running
because they had to read the in-memory state. That work was a one-shot
investigation to confirm the C# class hierarchy. The findings were captured
in code comments and in this document; the runtime dumps themselves are no
longer needed. Future maintainers should not rerun them.

Those runtime-dump scripts and outputs were disposable scratch artifacts and
may be absent after tool cleanup. The maintained path is the offline metadata
helper under `tools/endfield-il2cpp/`.

### What happens if they upgrade the game data?

Rerun `export.bat`. The pipeline picks up the new game data automatically:

1. `export_full_from_game.py` re-extracts everything from the install,
   including the new `DialogIdTable.json`.
2. `verify_export_freshness.py` confirms the new `export_full/` matches the
   installed source fingerprints before the long WebUI builders run.
3. `recover_dialog_id_registry.py` rebuilds
   `export_full/recovered/dialog_id_table_index.json`. Scenes added in the
   update appear; scenes removed disappear. Trunk counts update.
4. `build_story_source_links.py` rebuilds mission, level-script, cutscene,
   remotecomm, SNS, radio, and reading-popup source evidence.
5. `build_story.py` rebuilds all conv JSONs and stamps
   `_debug.runtimeRegistry` from the new registry.
6. `annotate_conv_with_registry.py` remains available as a stand-alone
   refresher for existing conv files, but normal `export.bat` runs do not
   need it because `build_story.py` now writes `_debug.runtimeRegistry`
   directly.

### Known fragility points (read before debugging a quiet failure)

1. **Binary format change.** `recover_dialog_id_registry.py` extracts
   ASCII tokens with the regex `(dlg_[A-Za-z0-9_]{2,80}|radio_[A-Za-z0-9_]{2,80})`.
   If a future game version starts encrypting `DialogIdTable.json` at rest,
   the extractor returns an empty dict and every scene becomes
   `unregistered`. **Detection**: `recover_dialog_id_registry.py` reports
   the total registered-scene count when run without `--quiet`; a drop
   from ~4 500 to ~0 is the smoking gun. **Fix**: investigate the new
   binary format; the in-memory representation is still
   MemoryPack-encoded `DialogBriefInfo` records.
2. **New dialog loader class added in the game.** If a future patch adds
   a new dialog-loading C# class (e.g. a specialized `MingbaopuController`
   that bypasses `DialogManager`), our `dialogTrunkRowIteration` rationale
   becomes incomplete. The recovery would still classify those scenes as
   `unregisteredScene` (correctly, if the new class doesn't register them
   in `DialogIdTable`) or fall back to `lineIdSuffix` (if the order
   becomes ambiguous). **Detection**: run the offline metadata catalog under
   `tools/endfield-il2cpp/` against the new `global-metadata.dat` and inspect
   the dialog/option focus reports for new loader classes or methods. If a
   new one appears, this document needs updating.
3. **Per-line ID schema change.** Our trunk-decomposition regex expects
   `dlg_<scene>_<trunkInt>_<lineDigits>`. A different format (e.g. mixed-
   case trunk tags, more nested segments) would silently drop the trunk
   decomposition. The recovery's binary "registered or not" status keeps
   working; only the `trunkCount` / `linesByTrunk` fields degrade.
   **Detection**: spot-check the registry index after an update against a
   known multi-trunk scene like `dlg_e10m3_1`.
4. **C# class renames.** Comments and human-readable reason strings in
   `scene_order_gap_shared.py` mention `DialogTrunkBehaviour`,
   `DialogManager`, etc. The recovery logic does **not** depend on these
   names matching the runtime — only on `DialogIdTable` being the right
   table. If the game renames classes, the docs become stale but the
   recovery still works correctly.

### What I deliberately did *not* automate

These were considered and rejected for the "solid evidence" bar:

- **Radio scene registry**: `radio_*` IDs are absent from `DialogIdTable`
  — they live in `RadioTable.json` (separate table). Extending the
  registry recovery to radio scenes is a clean follow-up but I didn't do
  it here.
- **Auto-resolving the line-count delta**: the `lineCountDelta` /
  `note` fields surface inconsistencies but don't reorder lines.
  Resolving the delta requires understanding what the "extra" webui lines
  are (summary text, hint text, conditional alternates?), and that needs
  per-table parsing work we haven't done.
- **Option panel positions from IL2CPP**: metadata.dat has `panelId`,
  `popUpPanelId`, `centerPanelId`, `ApplyPanelId` field names that suggest
  the runtime has explicit position categories for dialog options. The
  existing option-layout recovery doesn't surface these. Wiring them in
  needs a concrete data source (the asset that stores per-scene panel id
  per option). I didn't trace that path.
- **Trunk-count auto-validation**: we could programmatically detect when
  our `dialogTree`-mode recovery emits a trunk count that disagrees with
  `DialogIdTable`. That's a real bug-finder but needs the recovery to
  expose its trunk decomposition (it currently emits only a flat
  `orderedLineIds`). Useful follow-up.

## Where the IL2CPP-side evidence lives

The maintained evidence path is now:

- `tools/endfield-il2cpp/catalog_option_flow_metadata.py`: validates/caches
  `global-metadata.dat`, catalogs dialog/timeline/trunk/option fields and
  method targets, and writes drift reports.
- `tools/endfield-il2cpp/map_body_targets_to_gameassembly.py`: maps focused
  metadata method targets to `GameAssembly.dll` addresses and simple direct
  call edges.
- `reports/option_flow_runtime_metadata*.json` / `.md` and
  `reports/option_flow_body_targets_gameassembly.*`: generated evidence
  reports.

Historical live-process dump artifacts were scratch-only provenance and are
not part of the active workflow. Do not restore or rerun the pe-sieve,
procdump, Cpp2IL, or Il2CppDumper path unless a concrete future investigation
requires it.

## Quick command reference

Fresh build from scratch (game closed, install present on disk):

```
.\export.bat
```

Refresh just the registry + warnings without re-export:

```
python .\scripts\recover_dialog_id_registry.py
python .\scripts\rewrite_scene_order_warnings.py
python .\scripts\annotate_conv_with_registry.py   # optional, refresh existing _debug blocks
```

Verify a specific scene's classification:

```
python -c "import json,sys; sys.path.insert(0,'scripts'); \
from scene_order_gap_shared import analyze_line_order, load_dialog_id_registry; \
conv = json.load(open('webui/data/lang/CN/conv/dlg_e10m3_10.json',encoding='utf-8')); \
print(analyze_line_order(conv, dialog_id_registry=load_dialog_id_registry()))"
```

Confirm metadata.dat class hierarchy hasn't drifted after a game update:

```
python .\scratch\il2cpp_runtime_dump\scan_metadata_strings.py
```

Expected: hits for `DialogTrunkBehaviour`, `DialogManager`,
`DialogTimelineManager`, `DialogTreeController`, `DialogOptionBehaviour`;
zero hits for `Mingbao*`, `Letter*Panel`, `Memo*Panel`, `BulletinBoard`,
`DocumentController`. If new dialog-loader classes appear, update this
document.
