# Scripts

Active scripts in this directory support the WebUI export/package workflow.

## Active Wrappers

From the repo root:

```bat
notepad endfield_paths.bat
.\setup_first_time.bat
.\export.bat
.\export.bat --mission-pipeline-only
.\export.bat --mission-pipeline-only --reuse-timeline-orders
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export.bat --with-assets
.\export.bat --full-source-graph
.\export.bat --export-from-game
.\build_updates.bat
.\export_assets.bat
.\pack_webui.bat
```

For a fresh checkout, edit `endfield_paths.bat` first, then prefer the root
`setup_first_time.bat` wrapper. It initializes and builds the required external
tools, runs the installed-game Story/Gameplay/Text Tables export, prints optional
Assets/media and Updates follow-up commands, and starts or reuses the default
WebUI server. Pass `--no-serve` if the setup should stop after the build/export
steps.

The root wrappers load `endfield_paths.bat` before parsing arguments. It sets
`ENDFIELD_GAME_ROOT`, `ENDFIELD_PREVIOUS_EXPORT_ROOT`, and
`ENDFIELD_EXPORT_ROOT` for repeated local runs. Explicit flags such as
`--game-root`, `--previous-export-root`, and `--export-root` still take
precedence for one-off commands.

`export.bat` is the normal Story, Gameplay, and Text Tables WebUI rebuild path from an existing
`export_full/`. It runs:

- `scripts/verify_export_freshness.py`
- `scripts/story_builder/refresh_evidence.py`
- `scripts/story_builder/build.py --languages CN --default-language CN --skip-audio-link`
- `scripts/build_character_data.py --languages CN --default-language CN`
- `scripts/build_mission_pipeline_data.py`
- `scripts/build_gameplay_data.py --languages CN --default-language CN`
- `scripts/build_progression_data.py --languages CN --default-language CN`
- `scripts/build_projectile_data.py`
- `scripts/build_economy_data.py --languages CN --default-language CN`
- `scripts/build_world_data.py --languages CN --default-language CN`
- optional asset/audio refresh when requested
- `tools/endfield_source_graph.py build --language CN --relevant-asset-maps --skip-reference-rows --skip-followups`
- `scripts/build_presentation_data.py --languages CN`
- `scripts/build_combat_relationships.py --languages CN`

Presentation and Combat check source-graph freshness against their generated
inputs. Presentation emits a stable empty degraded payload instead of reading
missing or stale graph evidence. Combat checks its generated Gameplay, manifest,
asset-index, AbilityEntity, and CharacterTemplate inputs. A stale graph is not
opened; the payload records the reason and falls back to authored Gameplay plus
exact AnimeStudio evidence. The wrapper rebuild order keeps the normal output
graph-backed without allowing stale edges to retain direct confidence.

The default source graph still reads original AnimeStudio AssetMaps, but inserts
only source/PathID rows consumed by material, shader, texture, and FMV WebUI
edges. On the current export this retains 1,140 relevant identities instead of
indexing roughly 1.81 million generic Unity identities; Presentation and Combat
payloads were byte-for-byte equivalent to those built from the exhaustive
graph. Pass `--full-source-graph` for broad Unity-object/PathID queries and the
investigative follow-up reports. Pass `--mission-pipeline-only` for the recovery
edit loop: it refreshes Story evidence, CN Story/Text Tables, and Mission
Pipeline, then skips unrelated semantic views and the graph. If Story outputs
are already current, run `export.bat --mission-pipeline-data-only` or
`python scripts\build_mission_pipeline_data.py` directly; both skip Story,
evidence, semantic-view, and source-graph rebuilds, and currently complete in a
few seconds. When Story relations changed but `export_full/` and the recovered
Timeline inputs did not, add `--reuse-timeline-orders`; this passes
`--timeline-recovery never` to the Story builder and avoids a redundant
installed-VFS preflight. The wrapper rejects this flag with `--export-from-game`
and with the already Story-free data-only mode so a real game-data refresh
cannot silently reuse an old order index.

The graph also consumes Mission Pipeline `envTalkContext` rows. It preserves the
exact mission/quest-state -> atmospheric switcher group -> cluster -> envTalk ->
Story chain through explicit context nodes. Every edge is marked non-owning
context with playback and order evidence disabled; no direct mission-to-Story
edge is emitted.

The same graph build indexes Mission Pipeline's exact unowned native runtime
receivers. Each receiver must retain one unique level/script/header identity,
the current-build MemoryPack mapping, and a Story source path agreeing with that
identity. Receiver -> Story means exact playback control flow; it deliberately
emits no mission or quest edge. The current frontier has 158 receivers and 182
placements covering 153 Story files across 25 event families and 23 levels.

When the exported Table inputs are also unchanged, add `--reuse-reference` to
validate and preserve the current localized Text Tables reference index and all
of its indexed files. The wrapper rejects this mode with `--export-from-game`
and with the Story-free data-only mode.

The 2026-07-21 performance pass keeps all evidence predicates exact. It fixes
an accidental recursive scan below an already exact `MonoBehaviour` root,
uses upper bounds before expensive `SequenceMatcher.ratio()` calls, resolves
Timeline parent PathIDs lazily, and validates every selected CHK before a
filtered extraction directory can be replaced. The final current CN Story
rebuild with pinned Timeline order and audio relinking disabled completed in
132.973 seconds. Exact scene-key resolution is now build-cached by payload,
mission, and resolver identity; immutable binary inputs below `export_full/`
are read once per process. With pinned Timeline order, validated reference
reuse, and audio relinking disabled, the same CN Story build completed in
124.441 seconds. The AnimeStudio filename resolver now fully indexes the small
TextAsset roots and only the authored dialog/timeline/cutscene families in the
million-file MonoBehaviour roots, with exact lazy lookup for other stems. The
large machine-readable mission-timeline report is compact JSON (52.4 MB versus
93.3 MB pretty-printed); its paired Markdown remains readable. The current
Mission-Pipeline-only JSON pass completed in 2.202 seconds on the final run. If the disposable
filtered Timeline extraction is missing, the
Story pass now spends about 15 seconds recovering the same containment from
the current full typed MonoBehaviour export instead of dropping evidence.
After adding the fail-closed NPC patrol mission-context join, the same fast CN
command completed in 128.264 seconds and its direct Mission Pipeline rebuild in
2.141 seconds. The relation checks only exact patrol receiver occurrences and
one relevant LevelData scene; it does not change the fast-path contract.
The subsequent expanded-recovery profile removed repeated Win32 binding setup,
Path-object provenance normalization, and duplicate validated LevelData
member-22 decodes. The same current fast command completed in 106.275 seconds,
down from 129.055 seconds, while aggregate hashes for all conversation,
mission, and reused-reference payloads remained byte-identical. Its direct
Mission Pipeline rebuild completed in 2.202 seconds.
The next pass prepares each LevelScript's typed action/control context once and
reuses it for every Story-bearing action in that file. The isolated native
playback index fell from about 13.3 to 9.2 seconds while retaining the same
duplicate-id validation, branch traversal, ordering, and fail-closed rules. A
full fast CN Story run including the newer BattleSignal producer and task-map
dependency evidence completed in 106.847 seconds; its direct Mission Pipeline
pass completed in 2.094 seconds. The inferred-option-anchor report is now
accumulated while conversation payloads are written instead of reopening all
10,887 generated JSON files at the end; an equivalence test retains the old
directory scan and proves identical JSON and Markdown report output. A warm
repeat measured 108.784 seconds overall (106.3 seconds inside CN Story), so
this removes redundant I/O but does not claim a material end-to-end wall-time
improvement on this checkout. The final direct Mission Pipeline pass measured
2.013 seconds. The following optimization groups exact entity-tracking targets
by authored scene and parses each byte-verified LevelData source/mirror pair
once. Its isolated real-data stage fell from 8.216 to 0.871 seconds while
emitting the identical one-row SHA-256 result; the latest warm full command
completed in 90.572 seconds overall (88.1 seconds inside CN Story). Ordinary
filesystem-cache variation accounts for part of the full-run difference, so
only the isolated roughly 7.3-second saving is attributed to this change. The
final direct Mission Pipeline pass measured 1.993 seconds. The data-only
wrapper now runs the inexpensive freshness guard before reusing Story
sidecars, so stale installed-game inputs fail before a fast graph rebuild
instead of silently presenting old evidence.
The next mechanical pass retains filename-pattern results for the whole Story
process, pre-partitions sibling option-template candidates by their already
required option count, and compares unchanged generated text as platform-native
encoded bytes. It skips no evidence predicate. All 10,887 conversation files
remained byte-identical; normalized hashes for all 702 mission files, the Story
index, mission-timeline report, and binding coverage also remained identical,
and the full script suite passed 290 tests. Because the measured full run
overlapped independent binary audits, no end-to-end wall-time saving is claimed
from that noisy sample.

The freshness verifier uses a fast non-empty check for required generated output
folders by default; pass `--full-output-counts` directly to
`verify_export_freshness.py` only when exact file counts are needed for an
audit. `refresh_evidence.py` runs the DialogIdTable registry, narrative video
bindings, and story source-link refresh in parallel before the Story builder
loads those generated files. Selective AnimeStudio filename scans use the
native Windows find API instead of walking million-file type directories for
each prefix; this does not change the accepted original-data evidence rows.

Pass `--export-from-game` when you explicitly want to refresh `export_full/`
from installed game data before rebuilding Story/Gameplay/Text Tables data. Pass
`--with-assets` to also run the asset index builder and CN audio relinker after
Story is rebuilt. When `--export-from-game` and `--with-assets` are combined,
the wrapper runs one AnimeStudio Story+asset export so the source scan, maps
stage, and VFS index work are not repeated by a second wrapper invocation.
Set `ENDFIELD_GAME_ROOT` in `endfield_paths.bat` when the installed game is not
under the default `D:\Program Files\Endfield Game\Endfield_Data`. The path must
be the installed `Endfield_Data` directory. For one-off runs, pass
`--game-root PATH`; an explicit argument takes precedence over the config file.
Fresh clones must initialize and build the AnimeStudio submodule before this
installed-game refresh path can run:

```bat
git submodule update --init tools/AnimeStudio
.\scripts\animestudio\setup_dotnet9.bat
.\scripts\animestudio\rebuild.bat -Target CLI
```

The exporter expects
`tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe`.

`build_updates.bat` writes `webui/data/updates/latest.json` from the saved
previous export and current `export_full/`. Use `.\build_updates.bat
--init-build` for initial or baseline-only update feeds. By default it compares
the exported text JSON that feeds Story and Text Tables plus exported image/model/video
assets and decoded audio using fast size fingerprints; pass
`--hash-asset-updates` for slower same-size binary modification detection,
`--skip-audio-updates` to omit decoded audio while keeping other asset entries,
or `--skip-asset-updates` for a text-only feed. The wrapper reads
`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` from
`endfield_paths.bat`; pass `--previous-export-root PATH` and
`--export-root PATH` only for one-off comparisons. Most runs do not need
`--game-root`; pass it only for optional decoded-impact mapping from a
non-default installed
`Endfield_Data` root. It does not choose the export trees.

For an explicit one-off comparison between two already extracted versions, use:

```bat
.\build_updates.bat --previous-export-root "D:\exports\Endfield_old" --export-root "D:\exports\Endfield_new" --refresh-previous-export-baseline
```

The old extraction supplies the cached comparison baseline; the new extraction
is scanned against it. `--refresh-previous-export-baseline` is required after
replacing the contents at a previously used old-export path and is safe to use
for an intentional one-off comparison. The command writes the WebUI feed plus
`reports/updates/game-data-change-summary.json/.md`. Use `--full-export-scan`
only for a broad audit of every file in the two export roots; the default
focused scope is the correct mode for the Updates page.

`build_updates_by_patch.bat --check` compares the installed client's original
VFS snapshot without changing published state. The wrapper's default `--apply`
mode uses that result to stage changed extraction work and invokes
`build_updates.bat` itself after archive/current publication.

`export_assets.bat` runs `scripts/build_assets.py` for the compact WebUI media
indexes, then runs `scripts/build_audio.py --skip-decode` to relink existing
decoded CN audio into generated conversations. Pass `--export-from-game` to run
the full WebUI-facing AnimeStudio image/model export plus `Material` JSON after
first writing a lightweight AnimeStudio `vfs-index` bundle metadata snapshot,
and decode CN audio first. Pass `--webui-assets` when only WebUI-referenced
Texture2D media is needed, or `--debug-assets` for exhaustive AnimeStudio
conversion/JSON diagnostics. When Story also needs an installed-game refresh,
prefer `export.bat --export-from-game --with-assets` so one exporter invocation
covers Story and assets. It accepts the same `endfield_paths.bat`
`ENDFIELD_GAME_ROOT` fallback and `--game-root PATH` override when refreshing
decoded assets/audio from a non-default install root.

Both installed-game wrappers pass `--animestudio-jobs N` through to
`export_full_from_game.py`. The default is now `8`; AnimeStudio subprocess
tasks for a source go through a shared worker pool, and asset shards are queued
round-robin by type so one large type does not monopolize workers. Use a lower
value such as `1`, `2`, or `4` for low-RAM or first-time runs.
Non-sharded JSON type exports use `--animestudio-type-job-mode auto` by default,
which merges matching JSON types into one AnimeStudio process instead of loading
the same source files once per type. Pass `--animestudio-type-job-mode parallel`
for the older one-process-per-type behavior, or `merged` to combine every
non-sharded type set. Earlier testing on the 64 GiB workstation found
`--animestudio-jobs 2` improved the pre-merge Story JSON slice by about 21%,
while the old full asset refresh peaked at about 27 GiB observed process-tree
working set. Full-mode `AnimationClip` and `Texture2D` workers dominate both
memory and wall time.

Both wrappers can pass `--animestudio-dummy-dlls PATH` through when
`--export-from-game` is present. Use this only for optional IL2CPP DummyDll
folders that improve AnimeStudio MonoBehaviour schema recovery during Story JSON
export. If the flag is omitted, `export_full_from_game.py` checks
`ANIMESTUDIO_DUMMY_DLLS`, then known local locations such as `tools\DummyDll`;
it only adds AnimeStudio's `--dummy_dlls` option when the selected directory
exists and contains `.dll` files. Missing or stale DummyDll paths warn and
continue without DummyDlls instead of failing the export.

For targeted MonoBehaviour recovery experiments, pass
`--animestudio-mono-behaviour-type-tree-priority script-first` to make
AnimeStudio try a DummyDll script-derived TypeTree before the embedded
serialized TypeTree. The default `serialized-first` preserves the normal export
order and only uses script-derived trees as a fallback after serialized decode
failure. Script-first only improves body decoding when the relevant external
`MonoScript` bundle is loaded and the DummyDll set contains a usable script
type with real field nodes. Without DummyDlls, or when the script type is absent
or only resolves to a base-only tree, AnimeStudio records the script-derived
status when applicable and keeps the serialized/partial decode result.

For binary-first Unity-object investigations, AnimeStudio also accepts
`--object_index_jsonl FILE`. This opt-in CLI sidecar streams compact `object`,
`schema`, `monoScript`, and terminal `summary` JSONL rows while the selected
objects and dependency context are resident. It preserves source CAB/path/
offset/PathID identities, identifier-like decoded scalars, and non-null PPtrs;
it does not infer an edge from names or PathID alone. `MonoScript` rows and
exported MonoScript JSON include exact class/namespace/assembly plus
`$animestudio` source provenance even when no usable DummyDll type definition
exists. Use a unique output file per AnimeStudio process. The installed-game
Python wrapper can opt into the maintained multi-process merge with
`--animestudio-object-index` for Story/all scopes. Each relevant
MonoBehaviour/PlayableDirector worker writes one exact part under
`<source>/object_index/parts/`; `scripts/animestudio_object_index.py` then
publishes deterministic `objects.jsonl.gz` and `schemas.jsonl.gz`, followed by
`summary.json` as the commit marker. The merge rejects incomplete parts,
conflicting physical identities, and non-unique external CAB-filename/PathID
targets. The summary is accepted only when its output hashes, stage-signature
hash, current source fingerprint, CLI apphost, first-party managed assemblies,
and optional DummyDll content hashes validate. Story/all carrier refreshes
invalidate an older commit marker before workers start. The option is disabled
for asset-only and `--skip-animestudio` runs and remains opt-in because the
complete carrier index can be large.

After an explicitly requested installed-game Story/all export has published
that index, run:

```bat
python scripts\story_recovery\build_animestudio_story_carrier_audit.py
python scripts\story_recovery\build_animestudio_story_gameobject_audit.py
python scripts\story_recovery\build_animestudio_story_reverse_pptr_audit.py
python scripts\story_recovery\build_cutscene_timeline_event_surface_audit.py
python scripts\story_recovery\build_animestudio_story_guide_consumer_audit.py
```

The carrier audit reads the current source-gap queue and reports only exact
core-isolated Story values that occur in typed Story-id fields on the same
completely decoded object as typed mission/quest or scene/script identifiers.
Exact Timeline roots whose serialized names begin with `f_`, `m_`, or `fm_`
are matched to the canonical `cutscene_*` Story key while preserving the
physical source value and normalization in the report. This normalization is
limited to the complete gender-prefixed root name: component suffixes,
locale/hash suffixes, substrings, and fuzzy variants remain rejected.
The stable `coreIsolatedSceneKeys` target prevents queue-only classification
changes from invalidating the audit that helps classify that queue. The report
records the complete target key-to-mission map plus a deterministic target-set
digest, and the gap builder accepts a negative result only when that digest
still matches its freshly derived core-isolated target set. It validates the
merged summary, stage signature, and output hashes first.
Partial/truncated
objects, unresolved MonoScript identity, substrings, names, neighboring
objects, PathID proximity, OCR, and manual overrides are rejected. Output goes
to `reports/story/recovery/animestudio_story_carrier_audit.{json,md}`. Rows are
candidate carriers only: native consumer semantics must independently establish
ownership or playback, and the audit never creates an order edge.
`--output-root` is the `export_full` root, not its nested
`recovered/AnimeStudio-cli` directory; the default already uses the repository
`export_full`.

The GameObject audit consumes the same validated index but follows only exact,
resolved `m_GameObject` PPtrs from actionable Story-bearing objects. It maps
their physical chunk offsets through the current VFS index, extracts only the
original logical AssetBundles, exports their GameObjects in a temporary
`tmp/story/` work directory, and resolves exact sibling component PathIDs plus
the complete recursive Transform child hierarchy back through the typed object
index. Child traversal is accepted only when each parent `m_Children` relation
agrees with the child's `m_Father`; unresolved or inconsistent hierarchies fail
closed. Targeted bundle dumps are split into batches of at most 64 logical
names so the exact scan remains below Windows command-line length limits.
Output goes to
`reports/story/recovery/animestudio_story_gameobject_audit.{json,md}`.
GameObject co-membership and Transform ancestry are exact serialized evidence,
but a typed mission/runtime sibling or descendant is still only a candidate
until native consumer semantics prove playback or ownership; neither supplies
order by itself.
Pass `--game-root PATH` or set `ENDFIELD_GAME_ROOT` when the installed
`Endfield_Data` root is not at the repository default.

The reverse-PPtr audit scans the complete validated object index a second time
for exact resolved references into the current actionable Story-bearing
objects. It separates same-file Timeline composition from cross-file
`PlayableDirector.m_PlayableAsset` bindings, then exports only the director
host bundles and resolves their exact Transform ancestry, descendants, typed
components, and `CutsceneRootComponent._timelineName` values. It uses the same
strict complete-name gender-root normalization as the forward audits; component
or fuzzy aliases are not admitted. Output goes to
`reports/story/recovery/animestudio_story_reverse_pptr_audit.{json,md}`.
The current hash-gated native mapping additionally promotes a cross-Story row
to a root playback alias only when that exact CutsceneRoot's resolved
`_director` PPtr lands on the same PlayableDirector:
`TimelineHandle.get_director` resolves the root's `topDirector`,
`CutsceneRootComponent.get_topDirector` returns `_director`, and
`TimelineHandle.Play` invokes it. A root playback alias proves which
TimelineAsset that loaded root plays; it still must not be converted into
mission ownership or relative Story order.
Mission Pipeline consumes the compact alias rows only when the report schema,
native mapping and binary hashes, object-index stage signature, and latest
export source fingerprints all remain current. It publishes the exact
CutsceneRoot-to-native-action-to-Story chain as an ownership-unresolved debug
route and corpus count. A second, narrower composition is admitted only when
an independently connected owner route already terminates at that exact root
and contains a native playback action. That composition extends owner context
to the played TimelineAsset without creating Story chronology. On the current
export this recovers only `cutscene_gm02m4_1`; condition/dependency routes and
the other three aliases remain non-owning.

The cutscene Timeline event-surface audit consumes those exact root playback
aliases and scans the complete CAB identity of every played TimelineAsset in
the published object indexes. It validates the exact target object as a fully
decoded typed `UnityEngine.Timeline.TimelineAsset`, inventories every script
class in the CAB, and reports any event/signal/marker/mission/quest/level/global
track or scalar surface for manual semantic review. Output goes to
`reports/story/recovery/cutscene_timeline_event_surface_audit.{json,md}`.
A clean negative closes only Timeline-emitted event context for those exact
played assets; it does not prove that a root is unused or definition-only and
does not create mission ownership, activation, or Story order.

The guide-consumer audit scans the same current, source-fingerprint-validated
merged index for exact typed `GuideRuntimeAsset` managed references. It accepts
only `FacSetInteractLockedState` actions that serialize `radioId` and a factory
instance key in the same action, live in a `guide_blackbox_*` asset, and
co-carry no mission, quest, scene, or script owner. The current native
`Execute` mapping is hash-gated and proves that the locked branch passes
`instKey` and `radioId` to `RemoteFactoryInteract.LockBuildingInteract`.
Its compact report feeds the source-gap queue and Mission Pipeline only while
the report, object-index stage signature, latest export source fingerprint,
and native mapping all agree. `export.bat --export-from-game
--animestudio-object-index` refreshes this audit automatically. The
classification removes known factory tutorial content from mission recovery;
it never adds mission ownership or Story order.

When MonoBehaviour TypeTree decoding fails inside a managed-reference registry,
AnimeStudio now emits partial JSON instead of collapsing to metadata-only JSON
when safe fields were already read. The partial output keeps decoded fields such
as `m_Name` and `actionsData`, then recovers
`$animestudio.recoveredManagedReferences.RefIds` headers (`rid`, managed type,
raw payload offset, raw payload length, and validated inferred
`DialogMainFlowData` `leadRid`/`linkedRids` when that layout matches exactly) so
downstream tools can still join decoded `rid` references to their runtime
managed types. It also names validated string fields for common dialog action
payloads, including `lineId`, `animationPath`, `facialMorphPath`, and
`poseControlNames`, records inferred transform-like fields for validated
`DialogTeleportEntityActionData` payloads, names small validated empty-tail and
flag/index-like dialog actions, records validated motion/camera/post-process
scalar blocks for action payloads such as `DialogMoveToActData`,
`DialogLookAtActData`, `DialogTurnToActData`, `DialogCamDOFActionData`,
`DialogMaskActionData`, `DialogCamPPActionData`, and the common
`DialogCamActData` layout, and records a conservative `inferredActionTimingPrefix`
for dialog action payloads (`value0Seconds`, `value1Seconds`, and `actionCode`).
Still-unparsed payloads may include
`heuristicStringHints` and `heuristicRidLinks`; those fields are advisory
clues, not a typed managed-reference schema decode.

`export_full_from_game.py` writes detailed stage logs and summaries under
`../reports/export/`. Nonzero AnimeStudio subprocesses now make the wrapper return
nonzero after the summary is written, so `export.bat` and `export_assets.bat`
stop on partial type-sliced failure. Metadata-only MonoBehaviour JSON is a
bounded fallback for objects with impossible schema fields. Per-asset
`Export ... error` log entries are skipped converted assets and should be
reviewed separately from wrapper-level failures.

`scripts/build_audio.py` can still be run directly for non-CN languages or
audio-only maintenance. It indexes shared files under
`export_full/structured/Audio/shared/` plus language voice files under
`export_full/structured/Audio/<LANG>/`, adds playable `audioSrc` links to
generated conversation JSON when a line's `audio` id matches a decoded file,
streams Wwise bank HIRC metadata from VFS `*banks.pck` payloads via AnimeStudio
`stream`, and links cutscene audio events such as `au_sfx_*`/`au_vo_*` when
the event graph reaches decoded media. The default decode uses one fallback-aware
AnimeStudio `audio --block all` process; `--shared-output` keeps common
SFX/music separate from language voice without reloading the VFS once per audio
block or decoding the same PCKs again with reversed source roots. The CLI reads
one PCK at a time and limits concurrent converters. Generated indexes categorize voice by story/character/enemy use and
resolved Wwise media by SFX, voice-event, music, cue, ambience, or UI event.
Pass `--block hotfix-audio` for an
explicit HotfixAudio decode; it is treated as shared audio storage but is not
part of `--block all`.

`pack_webui.bat` runs `scripts/pack_webui.py` and creates split
shareable zips. The main story zip contains `serve.py`, `webui/`, generated
story and text-table data, WebUI code, and emoji images. The companion assets
zip contains larger displayed image/video media resolved from `export_full/`,
and the standalone audio zip contains decoded story audio from `export_full/`.
Extract the story zip first, then extract the assets and audio zips into the
same directory when media or audio is wanted. Packaging excludes 3D/model
payloads and does not include
`scratch/`, `reports/`, or `tmp/`.
Pass `--skip-audio` when only the story and companion assets zips are needed.
When the Assets browser is excluded, the packaged `assets.js` navigation shim
must preserve the source WebUI's debug-only view gating, safe hash fallbacks,
and keyboard exclusion for hidden tabs.

## Folder Contract

The active WebUI export/package workflow should not require inputs from
`../scratch/`, `../reports/`, or `../tmp/`.

Expected active inputs and outputs:

- `../webui/`: static browser app plus generated WebUI data under
  `webui/data/`.
- `../export_full/`: generated export data used by Story, Text Tables, Assets,
  and package media resolution.
- `../.game-data-tracker/`: persistent state for exported WebUI text JSON and
  asset update tracking.
- `../reports/`: generated reports grouped by topic. Most are outputs, but a
  small number of recovery reports are explicit inputs to later audit or Story
  build stages; scripts keep those paths within their topic directories. Reports
  are never package inputs and should not contain
  agent investigation conclusions.
  Routine outputs use `reports/export/`, `reports/story/build/`,
  `reports/updates/`, and `reports/assets/`; manual Story recovery evidence
  uses `reports/story/recovery/`. The source graph, mission-order audits, and
  gameplay OCR corpus keep their established topic roots under `reports/`.
- `../videos/`: local gameplay video inputs used by the optional OCR/audio
  story-order recovery tools. Completed `.mp4` files are inputs to
  `story_recovery/build_gameplay_video_ocr_audit.py`; downloader `.m4s` parts
  and `.lock` files are ignored as incomplete work.
- `../memory/`: observations, conclusions, older exploration notes, status
  snapshots, and archived scripts.
- `../scratch/`: topic-grouped probes, prototypes, and previews that may be
  revisited. Use `scratch/<topic>/<task>/`; do not add loose root files.
- `../tmp/`: topic-grouped disposable intermediates and run output. Use
  `tmp/<topic>/<task-or-run>/`, and remove completed runs after validation.
- `../tools/`: the tracked source-graph helper, tracked IL2CPP diagnostics
  used by optional recovery audits, and ignored local vendor/tool caches. If a
  workflow needs reusable helper data such as AnimeStudio DummyDlls, place it
  here or pass it explicitly rather than relying on `scratch/` or `tmp`. New
  promoted tools need intentional tracking and documentation because this
  directory is ignored by default.

## WebUI

- `export_full_from_game.py`: export data from the installed Endfield client.
  The normal WebUI wrapper is `..\export.bat`, which skips raw VFS, source
  inventory, raw asset bundles, audio PCK/media files, world-streaming bytes,
  irradiance volumes, extend-data bins, patch bytes, Lua, and heavy
  2D/3D/animation asset conversion unless `--with-assets` is passed. The
  structured dump defaults to `--structured-dump-mode webui`, and
  `scripts\build_audio.py` streams Wwise bank metadata directly from VFS for
  event relinking. Structured dump and VFS-index commands configure
  `StreamingAssets` and `Persistent` as sibling fallbacks so AnimeStudio can
  resolve authoritative `.blc` metadata and `.chk` payloads from either root.
  `--structured-dump-mode full` keeps the same production skip
  rules, and `--structured-dump-mode debug` is the broad VFS diagnostic mode.
  Pass repeatable `--world-scene-chunk MAP:X:Z` selectors to additionally dump
  the matching static `InitChunkData` and `StreamingChunkData` files from the
  `streaming` block. Chunk coordinates are `floor(world X / 128)` and
  `floor(world Z / 128)`; for example, the map02 cell containing
  `(305.328, -1609.578)` is `map02:2:-13`. Targeted scene chunks are exported
  only from `StreamingAssets` and cannot be combined with `--skip-structured`.
  `..\export_assets.bat` runs those heavier asset passes separately. Summaries
  are written under `..\reports\`, but the workflow does not require `reports`,
  `scratch`, or `tmp` as active inputs.
- `verify_export_freshness.py`: compares the latest export summary with
  the current installed `Endfield_Data` source fingerprints and verifies the
  WebUI-required export folders are present. `export.bat` runs it immediately
  after `export_full_from_game.py` so game updates do not silently reuse stale
  `export_full/` data. Persistent runtime-only roots `HGDownload`, `Logs`, and
  `Temp` are excluded from the source fingerprint: launcher/runtime churn
  there is not an exported WebUI source and must not invalidate otherwise
  byte-current VFS output.
- `track_export_changes.py`: generic file-tree scanner used by the WebUI
  Updates builder.
- `track_game_data_updates.py`: streams AnimeStudio `vfs-index --jsonl` records
  for `StreamingAssets` and `Persistent` into a compact SQLite source snapshot.
  Both scans use the other installed source as fallback because a catalog may
  reference a chunk physically stored in the other root. The snapshot requests
  only the block families the transactional WebUI patch workflow can publish,
  including CN voice; optional uninstalled `AuditAudio` and non-CN language
  packages are outside this baseline rather than being treated as missing
  required data.
  It compares logical VFS files by source/block/path plus data MD5 and length,
  reports chunk-only repacks separately, rejects truncated scans, missing
  chunks, duplicate identities, and newly missing blocks, and never promotes a
  candidate implicitly. `baseline-current` seeds from only the installed
  current version; `check` writes a candidate/change plan without changing the
  baseline. Candidate promotion is owned by the transactional patch workflow
  and occurs only after staged export validation, publication, WebUI rebuild,
  and Updates-feed generation succeed.
- `game_data_update_workflow.py`: transactional patch orchestration behind
  `..\build_updates_by_patch.bat`. `--init-baseline` verifies that the existing
  export matches the installed sources, then atomically attaches the source
  snapshot under `export_full/recovered/AnimeStudio-cli/`. `--check` remains
  read-only. Default `--apply` clones the complete current export into sibling
  staging, selectively dumps changed direct VFS files, refreshes broader
  AnimeStudio/audio scopes only when affected, verifies the installed logical
  snapshot again, archives the previous export, publishes the staged current
  export, rebuilds WebUI data, invokes the Updates feed comparison, and advances
  the baseline only after success. It journals folder rotation and restores the
  previous export/WebUI data on handled post-rotation failures.
- `build_updates.py`: writes `webui/data/updates/latest.json` by comparing
  WebUI-facing text JSON roots and exported asset roots in a previous exported
  game-data tree, default `..\export_1d2\`, with the current `..\export_full\`.
  Scanner cache lives under `..\.game-data-tracker\`;
  generated summary reports live under `..\reports\`, and non-empty feed
  snapshots are written as `..\.game-data-tracker\history\update-feed-*.json`.
  The root `..\build_updates.bat` wrapper runs this standalone update step.
  Pass `--previous-export-root PATH` to compare a different saved export,
  `--export-root PATH` to compare a different current export,
  `--game-root PATH` only for optional decoded-impact mapping,
  `--refresh-previous-export-baseline` after replacing the saved previous
  export, `--baseline-only` to write an empty feed, `--skip-audio-updates` to
  omit decoded audio while keeping image/model/video asset entries, or
  `--skip-asset-updates` to skip the full exported asset diff. Asset
  modifications use fast size fingerprints by default; pass
  `--hash-asset-updates` for slower
  content-hash detection of same-size binary changes. Pass
  `--full-export-scan` only for an intentional all-files audit of the export
  roots. Pass
  `--dry-run-prune-previous-export-untracked` to preview previous-export files
  that already exist byte-identically at the same relative paths in the current
  export, and `--prune-previous-export-untracked` to delete those old duplicate
  copies after confirming the preview. Cached tracker and asset baselines keep
  later comparisons from treating those pruned files as newly added.
- `story_builder/build.py`: builds CN Story/Text Tables data by default,
  with optional extra languages. The builder reads from `..\export_full\`, stamps dialog convs
  with DialogIdTable runtime registry evidence, links narrative
  Cutscene/RemoteComm video files to matching story entries, promotes
  mission-shaped ReadingPopUp/RichContent `text_*` rows into story text
  conversations, and writes generated WebUI data plus durable reports.
  The static frontend currently
  treats SNS emoji ids such as `sns_emoji_*` as inline emoji, while non-emoji
  SNS media such as `sns_image_*` and `sns_sticker_*` render as normal images.
  The command entry stays small: `build_args.py` owns CLI flags,
  `timeline_orders.py` owns the pre-build Timeline recovery check,
  `timeline_action_evidence.py` owns the pre-build managed-reference action
  evidence pass, `build_pipeline.py` owns bundle orchestration and manifest writing, and
  `audio_relink.py` owns the post-build decoded-audio relink pass.
- `build_assets.py`: builds the compact WebUI Story/Wiki media index by
  default, or the broad Assets browser index and optional demo bundle zips with
  `--mode full`. It is run by `..\export_assets.bat` and by
  `..\export.bat --with-assets`, not the story-only `..\export.bat`.
- `build_gameplay_data.py`: builds the compact Gameplay tab payload under
  `webui/data/lang/<LANG>/gameplay/index.json` from structured tables such as
  `WeaponBasicTable`, `WeaponUpgradeTemplate*`, `WeaponBreakThroughTemplateTable`,
  `WeaponTalentTemplateTable`, `ItemTable`, `EquipTable`, `EquipFormulaTable`,
  `EquipSuitTable`, `CharacterTable`, `CharGrowthTable`, `CharLevelUpTable`,
  `CharBreak*`, `CharacterPotentialTable`, `SkillPatchTable`, `EnemyTable`,
  `EnemyAttributeTemplateTable`, `EnemyAbilityDescTable`, `UseItemTable`,
  `UsableItemChestTable`, `RewardTable`, and talent/profession/type lookup
  tables. It resolves localized display names,
  default weapon links, skill blackboard values, level-up costs, weapon upgrade
  checkpoints, weapon base-ATK stat checkpoints, breakthrough material costs,
  equipment display/property stat curves, domain/formula/suit context,
  character break-stage caps, capped character stat checkpoints from
  `CharacterTable.attributes`, character breakthrough costs, potential unlock
  effects, enemy variants/stat curves/abilities/combat scalars/buffs/drops,
  usable-item actions and chest rewards, and Story wiki cross-links when a
  matching `wiki_*` Story page exists.
  It is run by `..\export.bat` after the Story builder and can be run
  directly for extra languages with `--languages CN EN JP --default-language CN`.
- `build_character_data.py`: builds
  `webui/data/lang/<LANG>/characters/index.json` for the normal `人物` page.
  It merges localized `TextTable.json` `npcName_*` keys, playable
  `CharacterTable` names, `NpcTable` names and identifiers, generated Story
  actor names, and grouped `_actor_` / `_npc_` / major-NPC evidence from the
  exported asset index. Asset matches retain counts and representative paths;
  filename tokens remain identifiers unless another source supplies a
  localized name.
- `build_mission_pipeline_data.py`: builds the language-neutral, lazy
  `webui/data/mission_pipeline/index.json` and per-mission graph payloads from
  exported `MissionRuntimeAsset`. It preserves predecessor and condition-state
  edges as authored evidence, annotates the client/server protocol proven in
  the current native binary, retains exact dialog finish `0`, and never treats
  `flowIndex` as an exclusive branch selector. The default input is selected
  as one coherent corpus: Persistent wins only when it contains every
  StreamingAssets mission filename, otherwise the builder falls back wholly
  to StreamingAssets instead of creating a partial hybrid. The index records
  the selected root, completeness decision, and exact changed common
  filenames; an explicit `--mission-root` is labeled separately. The current
  980/980 Persistent override changes five files and yields 490
  missions, 4,462 quests, 155 mission-state edges, and the additional strong
  `dlg_f1m32_1 -> dlg_f1m32_2` Story edge. Schema 18 also preserves 3,496
  authored tracking rows on 3,241 objectives, including exact positions,
  entity/script operands, and normalized tracking filters, plus 217 initial
  mission-property rows across 71 missions. These fields are debug context and
  never create graph edges without an independent consumer/writer proof.
  The current native property audit identifies 204 tracking rows across 46
  missions / 110 mission-variable identities whose visibility conditions read
  `MissionData.propertyDict` through `TryGetSaveProperty -> DoCompare`.
  `SC_UPDATE_MISSION_PROPERTY (124)` resolves numeric property ids, converts
  `DYNAMIC_PARAMETER`, updates that dictionary, and sends the condition-change
  event. The server producer/timing rule remains unavailable, so this is a
  synchronized marker-visibility contract rather than quest or Story causality.
  Maintained offline recovery audits that scan MissionRuntime use the same
  complete-Persistent-or-whole-Streaming selector. `export.bat` runs it after Story
  so the experimental page can merge names and objective text from
  the selected language's existing mission sidecars. Story bundle generation
  also localizes base/quest-override mission descriptions and emits per-quest
  typed `storyConnections` plus the compatibility `storyFiles` list. Conditions
  are `Story -> Quest`, native client-action slots are `Quest -> Story`, and
  bounded LevelData/LevelScript/variant-runtime/NPC recovery remains contextual;
  mission co-membership and spatial proximity are not promoted. Per-mission
  connections and the unlinked Story remainder are also normalized into
  `storyCoverage.storyTriggerManifest`. Its evidence-typed routes distinguish
  playback, condition, dependency, context, unresolved playback ownership, and
  definition-only records, while retaining compact exact native event/action
  control paths from every maintained occurrence carrier (`levelScriptOccurrences`,
  `nativeOccurrences`, native black actions, parent-dialog occurrences, and
  preload occurrences). This projection explains existing evidence; it does not infer
  mission ownership or Story order from binary address order.
  Per-mission
  payloads also retain typed `SubGameInstanceData` rows that carry both
  `dungeonMissionId` and `bindScriptId` as mission-shell runtime evidence. They
  are counted separately and never create a quest or Story attachment. The
  generated cards retain the exact GameMechanics `gameId` request/push identity
  and the current-build lifecycle proof: `WorldChallengeGame.SendQuit` reads
  `bindScriptId` at typed-row offset `+0x50`, manually ends the resolved
  LevelScript when required, and then sends the stop request. Audited start
  paths do not consume that field, so it is not labeled as a proven activation
  edge. OCR/manual/gameplay evidence may cross-reference the recovery queue but
  cannot promote a binding.
  Typed `ActivityDungeonFightingStageTable` and
  `ActivitySnapShotStageTable` rows also enrich exact quest-level context. They
  currently contribute 25 `questId -> levelId` rows and explicitly add zero
  Story attachments. Exact `OnQuestStateChanged -> StartDialogAction`
  (`0x049e/0x0f`) chains whose
  original DialogTree is action-only are emitted separately as non-Story
  runtime actions; in particular the a1m4/a1m13 Open UI assets keep their raw
  `dlg_*` identities, panel/activity parameters, and are never rewritten to a
  `misc_dlg_*` Story alias.
  The coverage pass also joins missionless SubGame `bindScriptId` values to the
  exact script ids on unlinked native-playback occurrences. These become
  explicit missionless runtime nodes, not mission-owned Story connections; the
  current corpus has ten nodes, nine unique Story files, and fourteen
  SubGame-to-Story placements. Exact `GameMechanicConditionTable`,
  `ActivityConditionalMultiStageTable`, and `DungeonTable` cross-references are
  retained as non-owning prerequisite/association/scene-host evidence. Blank
  `rankRelatedId` values and name similarity do not create edges.
  `QuestStateEqual` (18) and `MissionStateEqual` (19) identify only the quest
  or mission state that gates SubGame availability; `CheckPassGameMechanicsId`
  (5031) identifies a preceding challenge. None makes the gated SubGame's
  Story playback mission-owned.
  A separate exact-runtime-receiver inventory organizes unlinked playback under
  current-build serialized event selectors without changing mission ownership.
  The current CN payload has 182 nodes, 182 unique Story files, and 210
  receiver-to-Story placements. The fail-closed local chain
  `OnSpawnerEntitySpawn -> ListAddValueEntityPtr -> OnEntityHpChanged` for
  `radio_gm02m20_9/_18`, where the unique same-level SpawnerConfig names
  `gm02m20`, remains mission context rather than quest context.
  Language sidecars cover every exported MissionRuntime mission, direct refs normalize
  against the full language Story corpus, and client actions retain the full
  authored `_nextID` chain. Native addresses describe the installed build's
  fallback path because IFix dispatch can replace it at runtime. Server
  placeholders are counted as condition instances (and separately as quests
  and missions), expose their composite `(questId, conditionId)` identity, and
  explicitly show that the installed native fallback sends no condition-level
  client request. Their return lane is the exact
  `SC_QUEST_OBJECTIVES_UPDATE { questId, questObjectives[{ conditionId,
  extraDetails, values, isComplete, descriptionIndex }] }` payload;
  `conditionId` alone is not treated as globally unique or as a Story bridge.
  The generated Story-binding coverage report also groups every residual exact
  playback by its decoded native event family and retains the complete key list,
  so recovery priorities come from current binary identities rather than Story
  filenames. A compact coverage summary is embedded back into the pipeline
  index for the WebUI header. Placeholder identity reuse counts and the current
  installed IFix-patch audit are likewise build-scoped rather than assumed
  constants.
  Mission-named LevelData scope now requires a fully decoded member-22
  `Dictionary<ulong, LevelScriptBriefData>` entry: the eight-member value must
  end with `scriptId == key`, all values must form one contiguous chain, and
  the preceding dictionary count must match. This is labeled asset-shell
  context, not logical mission/quest ownership; explicit MissionRuntime script
  conditions may legitimately point at a script hosted by another shell.
  Broad LevelData shells can also receive exact mission-area context without
  filename inference: typed `MissionAreaTrackingInfo.missionAreaId` resolves
  through `MissionAreaTable.subDataParentId` to an identical root key in the
  same validated member-22 dictionary. Every authored root/file hit must agree
  on one MissionRuntime; shared roots remain unresolved. This is still
  asset-shell context, not quest chronology.
  Typed `EntityTrackingInfo` is retained with `trackScriptEntity`, local
  `scriptId`, `entitySlotId`, and `entityLogicId`. The builder applies the
  current native `GameUtil.ToGlobalId` mapping, requires one exact aligned
  `WorldEntityRegistry` script/slot row and same-scene LevelScript file, and
  then admits only two narrow context relations: an exact tracked interactive
  `type_id` property, or a typed actionList Story record with an exact
  event-to-action control path in that script. Neither relation is playback or
  chronology; mismatched tracked/event slots remain explicit, raw file-wide
  strings and cross-script getters are rejected, and the UI labels these rows
  as client navigation context with no server exchange.
  The exact InteractiveTable object-to-template map is required before a
  tracked `properties[type_id]` value is accepted, and only template
  `int_narrative_mission` is supported. One stricter native bridge is also
  emitted when the tracked slot is the exact `ScriptEntityPtr` in an
  `EntityCompare` IfElse condition, its true branch raises one custom event,
  and a unique same-level listener plays Story. The current `e0m0_q#2` route
  reaches `cutscene_e0m0_1stZipline`; its server-placeholder completion remains
  opaque.
  For `trackScriptEntity=false`, the builder instead requires the local logic-id
  suffix to resolve to exactly one current
  `WorldEntityRegistry.worldEntityBriefInfos` global id. It may add a third,
  property-specific context relation only when an exact same-scene
  `EntityEvent_OnSavePropertyChanged` constant target matches that global id
  and its serialized path reaches one Story action. This relation is local
  tracked-entity context, not a quest completion or server response.
  A fourth non-script bridge requires a unique MissionRuntime tracking row,
  the unique local/global WorldEntityRegistry identity, byte-identical
  LevelData/InteractiveTable/template mirrors, a counted 25-member
  LevelInteractiveData record, and component 94's exact three-key
  `{FX_CHANGE_MISSION_ID, TYPE, TYPE_ID}` map with `TYPE=Dialog(1)`. Current
  data places `dlg_sm1l1m1_17` in `sm1l1m1_q#6` as navigation/configuration
  context; the exact reachable child `dlg_sm1l1m1_16` inherits that one quest
  as a possible authored DialogTree route. Neither row claims ownership,
  quest playback/completion, chronology, or a server exchange.
  Current Leader trigger-volume bodies are decoded from union tag `1`, member
  count `8`, with strict shape/slot/range checks and EOF-bounded framing.
  Matching MissionArea geometry is level-scoped through
  `LevelBasicInfoTable.idNum` and remains local context. Exact
  `PosTrackingInfo` coordinates may also match one selected Leader trigger
  center when the level, event slot, shape center, and candidate mission are
  all unique; this does not claim full area-shape equality. A validated LevelData
  member-22 shell can additionally scope sibling playback scripts only when all
  exact MRA/MissionArea/asset anchors in the container agree on one mission.
  Mission-level `missionStoryConnections` preserve native NPC accept dialogs
  and explicit `NpcProxyEx.missionId` context without forcing either onto a
  quest. Exact authored SNS mission ids, serialized black-screen playable to
  Timeline-root containment, uniquely MissionRuntime-scoped LevelScript action
  payloads, and FocusMode `radioIdInteractLocked` fields add mission-shell
  context without inventing quest placement. Exact quest-state LevelScript
  gates emit directional `Quest -> Story` actions only when the event, typed
  condition, `_nextID` chain, and native playback action all resolve without
  ambiguity; immediate authored DialogTree and LevelScript scene neighbors
  remain scoped context. Native playback rows whose mission/quest trigger is
  not decoded stay visible as unresolved evidence. `flow.unlinked` is the
  globally unconnected same-owner mission-scene remainder used by the WebUI's
  collapsed `Unassigned Story` section.
  A separate fail-closed NPC segment identity may add weak mission-shell
  context only when typed `NpcProxyTrackingInfo.proxyId`, every nonempty
  `NpcProxyEx.missionId`, the `WorldEntityRegistry.npcProxyBriefInfos` key and
  positive `segmentIdGlobal`, and the same-scene Story-playing LevelScript
  global id all agree on one mission. Every raw playback occurrence normalized
  to the output must reach that same owner. The current census yields nine
  direct Story outputs plus two exact DialogTree black-action children. This is
  not an activation edge: the recovered native tracking path reads proxy AOI
  position and never consumes `segmentIdGlobal` to start a LevelScript, so the
  UI labels the relation `derived_exact_shell` with no server exchange.
  `NpcProxyTable.lazyDestroyOverrideDialogId` is handled separately: a row must
  have `lazyDestroy=true`, an exact scene, one resolvable Story key, and exactly
  one typed same-scene proxy consumer. The accepted relation is non-owning
  quest navigation/configuration context. Native `NpcProxy.OnDeActive ->
  NpcProxyMgr.ApplyLazyDestroyData -> NpcManager.AddOverrideInteractDialogId`
  proves the field is executable, but does not prove quest-caused deactivation
  or playback; upstream server proxy state has no client request or expected
  reply on this edge.
  Exact `MissionEvent_OnClientGlobalVarChanged` paths may join their literal
  key to one MissionRuntime's `CheckClientGlobalVar` consumers, and typed
  `WaitForNpcProxyReady` path steps may join an exact tracked proxy to one
  mission. Shared quest candidates remain mission-shell context; neither rule
  invents a decoded server request/response. Native control traversal accepts
  duplicate local ids only when every typed record, text operand, `nextId`, and
  branch target is semantically identical, retaining all equivalent offsets.
  It also follows the exact current-build `SwitchInt` case/default layout while
  preserving its `-1` and `0` sentinels as non-edges. Exact `Play3DRadio`
  records may join `radioId` to a same-scene tracked NPC proxy only when the
  12-field payload consumes to EOF, `useNpcProxy` is true, and every typed
  consumer agrees on one mission. A complete TravelPole/entity-compare/custom-
  event producer/listener route may similarly inherit one authoritative
  validated LevelData shell; both are mission context, not quest triggers.
  Exact `ManuallyStartGuideGroup` (`0x0304/0x09`) literals may join an exact
  `OnGuideGroupComplete` Story listener only when the group has one producer,
  one Story target, and the producer has one mission-named validated LevelData
  host. The current native manual-guide branch is client-only and skips
  `CS_COMPLETE_GUIDE_GROUP`; ambiguous or unhosted groups remain unlinked and
  never gain a server exchange card.
  MissionRuntime `CheckGuideGroupComplete` nodes retain their exact
  `_guideGroupId` and `_completeType` facts. The native contract distinguishes
  server-backed `CS_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClose }` /
  `SC_COMPLETE_GUIDE_GROUP { GuideGroupId, IsClosed }` from the manual
  client-only bypass; neither packet supplies a mission/quest identity.
  An exact `OnSpawnerComplete` constant id may add mission-shell context when
  one same-level original SpawnerConfig has that id and its authored identifiers
  contain exactly one delimited current MissionRuntime id. The originating
  completion remains a server push and does not select a quest.
  A fail-closed WorldEntity foreign-key rule may attach exact Leader-trigger,
  Script-stage-changed, or entity-interactive-state playback as quest context
  when a canonical MissionRuntime condition supplies
  a complete typed entity group, every entity belongs to only that mission and
  quest, every same-level `LevelScriptBriefData.refWorldEntityIdList` occurrence
  resolves the group to the same script, and an exact current-build control path
  reaches the Story action. Current accepted shapes are a complete
  `CheckMonsterKilled._enemyIds` set and a direct all-`InteractiveCheckInt`
  `CombineCondition`. Singleton, mixed, slot-backed, cross-level, shared-owner,
  and ambiguous-script groups fail closed. The emitted relation is shared
  authored context only and explicitly denies a proven quest/server activation
  or paired response. Every Story action occurrence must use the same resolved
  script and a whitelisted exact receiver; the only auxiliary exception is an
  exact current-build same-script `PreloadCutsceneAction`, which is retained
  separately and never counted as playback. Stage rows expose the one-way
  `SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE {sceneNumId, scriptId, stage}` push and
  expected return `none`; entity-state rows remain local with no packet join.
  The mission summary's native-boundary cards additionally expose the proven
  asynchronous global-variable, spawner, and trigger-volume request/response/
  push field contracts.
  System-owned Story carriers follow the same original-data rule. DomainDepot
  dialogs require the exact configured mission id, dialog-row key/npcProxyId,
  and delivery-target targetId join; only residual dialogs in the target Story
  group are promoted. SkipChapter requires one same-row missionId/bindDlgId/
  skipChapterConfigId relation. Their native cards show the exact DomainDepot
  and SkipChapter requests, responses, fields, handlers, and effects.
  FactoryBuildingPanelLock radio rows are emitted only as non-owning exact
  quest-state dependencies; the native lock check reads the synchronized local
  quest cache and sends no direct packet.
  Previously unattached typed DialogTree If/Branch gates are likewise emitted
  only under `missionStateStoryDependencies`. They require exact sequential
  DialogIdTable record registration, exact DialogTreeConnection reachability to
  a same-root numeric trunk, and typed CheckQuestState fields. Native condition
  and branch consumers read the synchronized local cache and send no request or
  expected reply; these rows explain route selection, not dialog ownership.
  The runtime contract also exposes the independent NpcProxy server-push path:
  SC_NPC_ENTER_MAP_RESYNC / SC_NPC_ACTIVE_CHANGE_NTF carries
  proxyNumId/metaKvs/activeCondIndex, which selects an exDatas row and its
  dialogId. The selector does not read the adjacent missionId; that field is a
  separate paused-mission deactivation guard and cannot bind blank-mission rows.
  They are marked boundary-only and never attached to quest nodes without an
  independently typed Story ownership bridge.
  The pipeline build also writes
  `reports/story/build/mission_pipeline_story_binding_coverage_<LANG>.{json,md}`
  with unique-file, cross-mission-placement, evidence-row, per-kind, and full
  unlinked counts. This report counts only generated original-data connections;
  OCR, manual overrides, and gameplay observations cannot improve coverage.
  Story rows whose nominal owner is not one of the pipeline missions enter the
  denominator only after an accepted generated edge connects them. The report
  publishes their count and keys separately so valid level-owned cutscenes are
  not silently omitted and unrelated external-owner rows do not inflate the
  unlinked queue.
  Definition-only black-screen rows are also split by exact `TextVoIdTable`
  evidence into non-empty audio-metadata-only definitions, explicit empty
  audio mappings that are likely legacy, and missing audio metadata. These are
  negative current-build consumer classifications only: every row remains
  unbound and the audio table never creates mission or quest ownership.
  Exact PureGetter mission-state branches are decoded from the installed
  binary's `GetMissionState` (`0x013a/8`) and `CompareMissionState`
  (`0x001f/10`) registrations. The current native enums are `Equal=0`,
  `NotEqual=1` and `MissionState.Completed=3`; the selected true/false IfElse
  edge is retained for every mission whose state directly determines a Story
  action under `missionStateStoryDependencies`. These are dependency edges,
  not Story ownership and do not improve attachment coverage. Only the exact
  single-mission `Equal(Processing)` true branch is also admitted as narrow
  mission-shell playback context; broad `!= Completed`, post-completion, and
  multi-mission branches are not promoted.
  `GetMissionState.GetResult` reads the player's synchronized local
  `MissionSystem` cache, so the gate sends no client request and expects no
  direct server response. `SC_SYNC_ALL_MISSION` and
  `SC_MISSION_STATE_UPDATE` are independent upstream pushes that populate the
  cache, not replies paired to the Story action.
  LevelData member 17 contributes a second, exact mission-state dependency
  family. The decoder accepts only one-item `specificDatas` lists whose
  `FunctionAreaSpecificData` tag is `9`, whose `RadioTriggerZoneData` member
  count is `7`, and whose bounded fields resolve to current Story and
  MissionRuntime ids. It emits each exact `hideBeforeMissionId`,
  `hideAfterMissionId`, or `hideCompleteMissionId` role as both a non-owning
  state dependency and radio playback context. The native
  `RadioTriggerZoneHandler.OnEnter -> _GetRadioTriggerMissionState ->
  MissionSystem.GetMissionState -> GameAction.PlayRadio` chain proves the
  context, but not quest ownership. The local state read sends no client
  request and expects no paired reply; upstream mission synchronization remains
  independent.
  A third exact dependency family comes from LevelData member 20. The decoder
  admits only counted 25-member `LevelInteractiveData` records with a typed
  next-record boundary and a fully decoded ParamValue map that co-carries the
  canonical `FX_CHANGE_MISSION_ID` and `TYPE_ID` PropertyKeys. It then requires
  exact original-data joins through `ReadingPopUpTable.contentId`, the
  byte-identical InteractiveTable mirror, and the narrative template whose
  BaseComponentData tag `0x00b3` is registered as
  `Core_NarrativeComponentData`. Current data connects `radio_c16m4_50` and
  `_51` to the `c16m4d5` state dependency. Native NarrativeComponent bodies
  prove the state-query and playback lanes; because the exact interaction
  packet/reply is not recovered, the UI separately notes the optional
  `_RequestInteract` path instead of manufacturing a server exchange.
  The same exact final-record framing now admits one separately validated
  `int_horn.properties.dialog_id` consumer. It requires component keys
  `[0,132]`, the exact seven-property Horn shape, byte-identical authored
  template mirrors pinned by SHA-256, and the current native
  `RegisterInteractOptions` / `ReqInteractHorn(finishId)` flow. The one current
  row binds registered definition `dlg_sm1l1m9_11` to the exact q13
  `CheckTalkOptionFinish` consumer and retains q16 Completed as a separate
  availability lock. Because the definition has no emitted text conversation,
  Mission Pipeline publishes a definition-only context route outside Story
  coverage and does not alias the `...11d5` conversation.
  Typed DialogTree narrative links additionally report direct, direct-mission,
  `derived_exact_quest`, and `derived_exact_shell` evidence tiers. Every exact
  parent use is retained: `unresolvedDialogTreeNarrativeActions` includes both
  wholly unlinked and partially connected files, while
  `unlinkedDialogTreeNarrativeActions` remains the no-connected-parent subset.
  Narrative actions on DialogTree nodes without a managed-reference `$id` are
  excluded as unreachable authoring leftovers. A nested black action may
  inherit only a mission shell from its exact parent dialog when typed parent
  playback, a complete validated LevelData member-22 host, and every independent
  typed MissionArea/position parent context union to one mission. Authored
  `dlg_*` playback ids and emitted `misc_dlg_*` Story aliases are normalized as
  the same exact parent occurrence. A conflicting union vetoes the attachment;
  this route never creates a quest gate or server exchange.
  Registered DialogTree cross-Story playback uses the separate
  `dialog_tree_reachable_story_playback` relation. The extractor accepts only
  typed `DialogTreeTrunkNode..._trunkId` or `DialogTreeDialogNode._dialogId`
  fields on a directed ancestor/descendant path from a current-parent numeric
  trunk. Missing-id authoring remnants are ignored, while every serialized
  connection endpoint must resolve. Weak-component/unique-root siblings,
  subtitle text, finish checks, and generic strings never attach Story files.
  Parent placement is frozen before this pass, so inheritance is one-hop and
  non-transitive. One unique parent quest may receive the child; multiple
  agreeing parent quests select only their shared mission shell. Exact but
  unscoped rows remain under `unresolvedDialogTreeStoryPlaybackCarriers` and
  are counted by the Mission Pipeline coverage report without being promoted.
  Authored trunk ids are labeled reachable because runtime replacement can
  override them; the recovered playback path is client-local with
  `serverExchange: false`.
- `story_recovery/build_protocol_registry_audit.py`: decodes the complete
  current-build `Proto.CSMessageID` and `Proto.SCMessageID` enums plus selected
  Story-facing protobuf field schemas from `global-metadata.dat`. It writes
  `reports/story/recovery/protocol_registry_audit.{json,md}`. The report keeps
  schema presence below runtime proof. The LevelScript task family exposes
  exact `(sceneNumId, scriptId, taskId)` identity but no mission/quest
  co-carrier; its separately proven current-build sender/handlers are recorded
  in `mission_runtime_trace_hooks.json`.
  The audit also records the corrected native message-125 path.
  `SC_SCENE_TRIGGER_CLIENT_MISSION_EVENT` reaches
  `MissionSystem.Handle_ClientMissionEvent`, interns the exact
  `(missionId, eventName)` pair through `KeyGenerator<T1,T2>` /
  `CombineKeyManager`, and publishes the resulting runtime key through
  `EventManager.SendGlobal`; it does not dispatch to the serialized
  `MissionEvent_OnCustomEventForMission` family. The report now decodes the
  IL2CPP generic method-spec table as well: message 125 uses
  `SendGlobal<Beyond.Gameplay.EventData>`, but zero of 51 current
  `BindGlobal` specializations has the required
  `Beyond.EventData<Beyond.Gameplay.EventData>` subscriber shape. That closes
  compiled managed typed consumers even when their final call form is
  indirect; native memory manipulation, runtime reflection, future IFix, and
  future builds remain outside the bound. The report also records that message 57
  preserves a non-empty `ctxToken` in `EventParams` before
  `RaiseScriptEvent`; the opaque token is event context, not mission/quest
  identity. Messages 126/316/317 remain present schemas but have no installed
  fallback handler/sender and are not inferred to be request/response pairs.
  `SC_MISSION_STATE_UPDATE.succeedId` is documented as a completion outcome
  selector rather than a successor mission. Rebuild with:

  ```bat
  python scripts\story_recovery\build_protocol_registry_audit.py
  ```

- `story_recovery/build_mission_option_carrier_audit.py`: verifies the
  hash-pinned `MissionOptionData` and `MissionOptionHandler` native bodies,
  scans the complete exported MonoBehaviour indexes, decoded TextAsset
  scripts, structured JsonData roots, and installed VFS Lua corpus, and writes
  `reports/story/recovery/mission_option_carrier_audit.{json,md}`. The current
  `_DoAction` fallback gives `callDialogId` priority and jumps to the end after
  playback; it calls `AcceptMission(missionId)` only when `callDialogId` is
  empty. The two fields are alternate actions, not a mission-to-dialog edge.
  The audit fails closed if the installed binary/metadata hashes change, an
  authored instance appears, or current IFix starts replacing the path.

  ```bat
  python scripts\story_recovery\build_mission_option_carrier_audit.py
  ```

- `story_recovery/build_mission_property_scriptptr_audit.py`: closes the
  nested `MissionRuntimeAsset.propertyDic -> ParamVariable.m_scriptPtr`
  candidate without treating shared managed types as foreign keys. It counts
  current authored `properties` rows, verifies the hash-pinned mission sync
  and LevelScript subscription bodies, performs a whole-GameAssembly direct
  caller census for `ToVariable` and the four entity/script subscription
  setters, checks the current IFix target list, and writes
  `reports/story/recovery/mission_property_scriptptr_audit.{json,md}`. The
  current result counts 217 authored rows across 71 missions, verifies the 204
  tracking-property filters and their native evaluator/update path, and keeps
  authored/server mission values in
  `MissionData.propertyDict` separate from the `m_scriptPtr` attached by local
  LevelScript event registration and adds zero Story bindings.

  ```bat
  python scripts\story_recovery\build_mission_property_scriptptr_audit.py
  ```

- `story_recovery/build_param_source_mission_context_audit.py`: verifies the
  installed `ParamSource.CURRENT_MISSION_ID = 1004` enum contract, scans every
  structured MissionRuntime action/condition and every raw LevelScript UID
  record, and checks the current IFix target list. It writes
  `reports/story/recovery/param_source_mission_context_audit.{json,md}` and
  fails closed on binary, metadata, corpus, action-type, or patch drift. The
  current result finds 18 MissionRuntime self-property checks across six
  missions and zero LevelScript uses, Story operands, bindings, or order
  edges.

  ```bat
  python scripts\story_recovery\build_param_source_mission_context_audit.py
  ```

- `story_recovery/build_managed_identity_carrier_census.py`: scans all current
  managed types for direct mission/quest identity beside LevelScript/scene or
  Story playback identity, validates the exact authored FocusMode,
  NpcProxyEx, SubGame, and MissionOption counts, and checks the installed IFix
  target list. It writes
  `reports/story/recovery/managed_identity_carrier_census.{json,md}` and fails
  closed on binary, metadata, authored-count, candidate-set, or patch drift.
  The current result classifies all ten direct candidate types with zero
  unreviewed rows. Its new native closure proves that
  `CommonTrackingPointInfoBase` and `TrackingInfoBase` use mission/scene
  identity only for HUD/map tracking, not Story playback or mission order.

  ```bat
  python scripts\story_recovery\build_managed_identity_carrier_census.py
  ```

- `story_recovery/build_nested_managed_identity_carrier_census.py`: resolves
  the installed MetadataRegistration runtime type table, including generic
  collection arguments, and follows custom managed fields to depth three. It
  writes
  `reports/story/recovery/nested_managed_identity_carrier_census.{json,md}`
  and fails closed on binary, metadata, IFix, candidate-set, or native caller
  drift. The current result classifies all 25 typed candidates, including 14
  that depend on a nested path, with zero unreviewed rows. The last newly
  audited path is
  `DialogManager.m_pendingItemSubmitter -> InventoryItemSubmitter.questId`:
  dialog finish can forward that object. Native direct callers of the
  constructor and `RegisterPendingSubmission` remain zero, but the audit now
  target-dumps the shipped `SubmitItemCtrl.lua` and proves its XLua
  constructor/registration call. It also checks all typed DialogTree OpenUI
  terminals: 13 are SubmitItem actions, three use the stock placeholder params,
  ten have empty params, and none exports a concrete quest id. The audit also
  target-dumps and hash-pins `PhaseDialog.lua`, proving that the current native/
  Lua OpenUI fallback forwards and JSON-decodes the authored parameter without
  a mission/quest lookup. Finally it scans all MissionRuntime objectives and
  `SubmitItem.json`: three exact quest submission checks resolve to item/count
  requirements, two have a same-AND dialog-finish co-gate, and those dialog ids
  overlap no SubmitItem OpenUI terminal. The report therefore records an active
  producer plus exact quest-to-submission context, but adds no quest-to-OpenUI,
  Story ownership, or order edge.

  ```bat
  python scripts\story_recovery\build_nested_managed_identity_carrier_census.py
  ```

- `story_recovery/import_mission_runtime_trace.py`: validates hook-produced
  JSONL and builds a `missionRuntimeTrace.v1` observational bundle. The input
  fails closed: every session needs one `session_start`, sequence numbers must
  increase, mission/quest state rows must carry an explicit `active` boolean,
  and every Story playback must carry either its propagated `chainId` or an
  explicit JSON `null`. A route is classified exact only when one chain contains
  the LevelScript event, entered action, and final Story playback. Active
  missions/quests are copied as temporal context and never promoted to authored
  ownership; per-session playback transitions remain separate from
  `sourceStoryPartialOrder`.

  The minimum useful hook surface for the current build is:

  - `Beyond.Gameplay.Core.LevelScriptRuntime._RaiseOnScriptEvent`
    (token `0x060121a3`, method index `74146`; current audited RVA
    `0x34b90c0`) to allocate a unique dispatch `chainId` and record level,
    script, event, and resolved ActionHeader identity;
  - `ActionHeader.Process` (`0x06007f17`, index `32534`, RVA `0x3d3c9b0`),
    `ActionHeader.DoProcess` (`0x06007f18`, index `32535`, RVA `0x31754f0`),
    and `ActionMapAsset.RunAction(startNodeID, ...)` (`0x06007f2a`, index
    `32553`, RVA `0x75f42fc`) to retain `headerLocalId`, `actionLocalId`, and
    concrete action type on that chain;
  - the final Story entry points (`StartDialogAction`, `PlayRadio`,
    `PlayRadioAndWait`, `PlayRemoteComm`, cutscene/black/SNS playback) to record
    the actual Story key, including an explicit null chain when work escaped the
    synchronous dispatch context;
  - MissionSystem state application, including `StartMission` (`0x0600524f`),
    `StartQuest` (`0x06005247`), `SucceedQuest` (`0x0600524b`), `FailQuest`
    (`0x0600524c`), and `FailMission` (`0x06005254`), to maintain the complete
    active snapshot before playback. A separate one-shot
    `MissionSystem.Tick` probe (`0x0600522b`, index `21034`, current RVA
    `0x34e3890`) initializes that state when the recorder attaches after
    mission startup. Hook symbols/tokens should be resolved again per game
    build; do not hard-code the listed RVAs across updates.
  - LevelScript task condition and network boundaries:
    `TaskCondition._OnConditionResultChanged` (`0x060121fe`, RVA
    `0x6fb0f9c`) carries exact scene/script/task/condition identity;
    `SendLevelScriptUpdateTaskProgress` (`0x06004d91`, RVA `0x73825c8`)
    carries the actual message-105 progress send; decoded server handlers for
    messages 813/815/816/823 are hooked at RVAs
    `0x3bd6fa0`/`0x42ba410`/`0x45e7f50`/`0x7386060`;
    `TaskCondition.InvokeOnIsCompleteChangeAction` (`0x06012207`, RVA
    `0x42bad00`) recovers the post-application condition-completed byte only
    while message 815 is active and the condition identity matches its parent.

  Current mapped string-param playback probes include
  `FlushAndPlayRadio.Execute` (`0x06008dfb`, index `36346`, RVA
  `0x7672390`), `StartContinuousDialog.Execute` (`0x06008d39`, index `36152`,
  RVA `0x766dbb4`), `PlayCutsceneAction.Execute`
  (`0x06008e19`, RVA `0x7675ea4`), `PlayCutsceneIgnoreCinematicQueue.Execute`
  (`0x06008e23`, RVA `0x7676618`), `PlayLevelSequenceAction.Execute`
  (`0x06008e2e`, RVA `0x767713c`),
  `PlayLevelSequenceAndControlSceneObjectsAction.PlayCinematic`
  (`0x06008e3d`, RVA `0x7677b24`),
  `PlayLevelSequenceAndHideSceneObjectsAction.PlayCinematic`
  (`0x06008e4c`, index `36427`, RVA `0x76781bc`),
  `Play3DRadio.Execute` (`0x06008e0a`, RVA
  `0x7675670`), `Play3DRadioAndWait.Execute` (`0x06008e0f`, RVA
  `0x767514c`), `PlayRadio.Execute` (`0x06008e5a`, RVA `0x76787ec`),
  `PlayRadioAndWait.Execute` (`0x06008e5d`, RVA `0x76783f4`),
  `PlayRemoteComm.Execute` (`0x06008e64`, RVA `0x7678a84`),
  `PlayDialogAndHideSceneObjectAction.PlayCinematic` (`0x06008cf2`, RVA
  `0x7669a84`),
  `StartCutsceneAndControlSceneObjectAction.PlayCinematic` (`0x06008e8b`, RVA
  `0x767cff4`), `StartCutsceneAndHideSceneObjectAction.PlayCinematic`
  (`0x06008ea7`, RVA `0x767dd14`),
  `StartCutsceneAndTeleportAction.Execute` (`0x06008ec7`, RVA `0x767e1ec`),
  `StartDialogAction.Execute` (`0x06008ed7`, RVA `0x767e920`),
  `StartDialogAndTeleportAction.Execute` (`0x06008ede`, RVA `0x767f6b0`), and
  `StartRemoteCommAndTeleport.Execute` (`0x06008eed`, RVA `0x768008c`). Their
  current bodies reach the proved `Param<string>.GetValue` resolver while the
  concrete action boundary is active. Hide/control cutscenes use their separate
  concrete `PlayCinematic` overrides rather than an inherited `Execute`;
  current metadata and bodies prove the classes, method identities, and
  `_cutsceneId` resolution independently.

  The same current-binary coverage pass rejects similarly named non-probes.
  `PlayVoiceNarrative.Execute` resolves an `au_*` voice id rather than a Story
  key; `FacPlayInteractLockedRadio.Execute` resolves factory instance/building
  ids rather than a radio id; and `TravelPoleHandoverToCutscene.Execute` calls
  `CutsceneManager.TryGetCutsceneHandle` and hands an existing handle to
  `TravelPoleBrain.HandoverToCutscene` without resolving its nominal
  `_cutsceneId`. Preload, stop, pause, override, and custom-event actions are
  likewise not final Story playback. Names and formatter registration alone
  never qualify a hook.

  FMV uses an explicit current-build map rather than a prefix transform. Current
  `PlayFmvAction.Execute` (`0x06008e2b`, RVA `0x7676be4`) and
  `StartFmvAndTeleportAction.Execute` (`0x06008ee5`, RVA `0x767fbe8`) reach
  the same resolver, but return original FMV ids rather than final Story keys.
  All 37 typed current LevelScript FMV records decode exactly, covering 30
  plain `cs_video_*` ids and one gender-prefixed id. Only 22 plain ids have an
  exact matching current `cutscene_*` Story file, so only those 22 pairs are
  listed in `playbackKeyMaps.fmv`. The other eight plain ids and
  `f_cs_video_e9m3_1` remain diagnostics; prefix resemblance does not create a
  Story edge.

  The offline video index also inventories exported FMV config definitions as
  a separate evidence class. The current export has `72` definitions. Forty-six
  female/male definitions resolve through an already-authoritative canonical
  base binding, leaving `13` without an authoritative Timeline,
  MissionRuntime, or LevelScript binding. Definition records retain exact
  config/source PathIDs and
  `NumIdStrTable.fmv_id` values, but always set
  `placementEvidence=false`; they do not populate the scene/mission binding
  indexes. For the 13 true definition-only rows, the builder follows exact
  default-playable, track, clip, and clip-asset PathIDs and records authored
  subtitle text ids and audio event keys in `timelineEvidence`. It does not
  synthesize missing localization or media. Standalone video cards, the
  generated report, and the source graph may display this provenance without
  turning it into playback, ownership, or order.

  SNS uses a distinct field-backed final boundary:
  `MainCharForceSNSBrain._StartSNSUI` (`0x06014493`, index `83090`, RVA
  `0x70ef8b4`) reads the exact `SNSDialogTable` dialog key from
  `m_dialogId` at `this+0x128`; `m_chatId` is at `+0x130`. Hooking this method
  avoids treating a rejected `_StartForceSNS(chatId, dialogId)` request as
  playback. `SnsTrackingInfo.Execute` is not a playback substitute: its
  `snsDialogId` belongs to mission-HUD tracking.

  The recorder preserves an exact dispatch chain across the asynchronous SNS
  queue when one exists. Current `GameAction.StartForceSNS` (`0x06008049`,
  index `32840`, RVA `0x75ed938`) allocates and initializes one
  `ForceSNSQueueItemData`; its direct `GameAction.AddCinematicItem2Queue` call
  (`0x0600804b`, index `32842`, RVA `0x75dcf58`) receives that object pointer.
  The successful `MainCharForceSNSBrain.StartForceSNS` consumer
  (`0x060144a7`, index `83110`, RVA `0x70ed65c`) retrieves the same pointer
  from its handle at `+0x18` and copies the dialog/chat ids into the brain
  before `_StartSNSUI`. The object pointer is the propagation key; chat id,
  dialog id, and `showToast` are fail-closed integrity checks. A rejected
  request/consumer, a missing or repeated queue boundary, or any copied-field
  mismatch discards the chain. If the accepted queue request itself has no
  live dispatch chain, final SNS playback still emits an explicit null chain;
  id equality or timing is never used to synthesize one.

  Three queued dialog action probes now defer their `story_playback` event to
  an accepted native boundary:
  `PlayDialogAndHideSceneObjectAction.PlayCinematic`, `StartDialogAction`, and
  `StartDialogAndTeleportAction`. Their current bodies resolve the dialog
  parameter and call `GameAction.StartDialog` (`0x06008038`, index `32823`,
  RVA `0x75ed524`). That method writes the dialog id to
  `DialogQueueItemData+0x18`, passes the object to
  `AddCinematicItem2Queue`, and returns true only after enqueueing it.
  `DialogManager.PlayDialogByHandle` (`0x0600f777`, index `63350`, RVA
  `0x6e15e40`) later retrieves the same pointer from its handle at `+0x18`.
  The recorder emits only when the nested `PlayDialogByJsonId` path reaches
  `DialogManager._PlayDialogInternal` (`0x0600f84e`, index `63565`, RVA
  `0x6e28040`) after `_CheckCanPlayDialog` succeeds. The action parameter,
  request argument, queue-item field, consumer value, and accepted-boundary
  value must all agree. `StartContinuousDialog` uses a different non-queue
  route and remains independently classified; do not force it through this
  handoff.

  Black-screen capture now retains the concrete action entry and resolves the
  key only at the final synchronous mask boundary. The current binary maps
  `ComplexNarrativeBlackScreenAction.Execute` (`0x06008ca9`, index `36008`,
  RVA `0x7660bf0`), `NarrativeBlackScreenAction.Execute` (`0x06008ce9`, index
  `36072`, RVA `0x7668c84`), and
  `StartNarrativeBlackScreenAndTeleport.Execute` (`0x06008d45`, index `36164`,
  RVA `0x766e494`); all three bodies call
  `GameAction.ShowNarrativeBlackScreen(UICommonMaskData)` (`0x0600802b`, index
  `32810`, RVA `0x75ec4b0`) directly. Current `GameAssembly.dll` layout
  recovery places `UICommonMaskData.textDataList` at `+0x70`, the
  `List<CommonMaskTextData>` items/size at `+0x10`/`+0x18`, array data at
  `+0x20`, and each embedded `LangKey.key` at item `+0x10`.

  The exported original `TextTable.json` contains 249 native
  `black_*_NNN` line ids. Every one reduces unambiguously to one of 215 exact
  generated Story keys, and every resulting key has its matching Story file.
  The only extra black lines in generated data are the three WebUI-authored
  `black_webui_secret_notice` lines; they are absent from the original table
  and cannot occur in the native mask probe. The hook fails closed unless an
  active black action owns the same-thread call, the native list has 1-64
  readable items, every item contains a correctly shaped original-style line
  id, and every line resolves to the same `black_*` key. It does not consult
  OCR, overrides, filenames, or display order; invalid or ownership-free calls
  remain diagnostics rather than edges.

  Late-attach MissionSystem initialization is also current-binary-only. The
  compiled `GetMissionIdByQuestId`, `GetMissionData`, and `GetQuestData`
  bodies place the quest-to-mission map, mission dictionary, and current-quest
  dictionary at `MissionSystem+0x70/+0xd8/+0xe0`. The exact current generic
  dictionary enumerator reads entries at `+0x18`, used count at `+0x20`,
  version at `+0x2c`, array data at `+0x20`, and 24-byte entries with
  hash/key/value at `+0/+8/+0x10`. `MissionData` and `QuestData` both carry
  their exact id at `+0x10` and state at `+0x18`; metadata default constants
  prove mission states `0..5` and quest states `0,2,3,4,5`, with
  `Processing=2` in both.

  The Tick hook retries a bounded read until all three dictionaries are
  structurally stable. It validates capacity, used count, version, every live
  hash/key/value entry, each dictionary key against the embedded data id, every
  enum value, and every current quest's exact quest-to-mission mapping before
  publishing anything. It then seeds the quest map and emits only currently
  processing mission/quest rows as the initial active context. A mismatch,
  unknown state, missing identity, concurrent version change, or exhausted
  retry budget produces diagnostics and no partial snapshot. This path does not
  consult OCR, WebUI overrides, filename shape, or prior recovered order.

  `story_recovery/capture_mission_runtime_trace.py` is the maintained launcher
  for this first hook set. It verifies the exact sizes and SHA-256 hashes of
  `Endfield.exe`, `GameAssembly.dll`, and `global-metadata.dat` against
  `story_recovery/mission_runtime_trace_hooks.json` before loading
  `mission_runtime_trace_agent.js`; an update fails closed instead of reusing
  stale RVAs. Install Frida only in the ignored repo-local environment and arm
  the capture before starting the game:

  ```bat
  python -m venv tools\frida-runtime\venv
  tools\frida-runtime\venv\Scripts\python.exe -m pip install frida-tools
  tools\frida-runtime\venv\Scripts\python.exe scripts\story_recovery\capture_mission_runtime_trace.py
  ```

  On the current protected client, `ACE-BASE.sys` denies Frida target writes
  and allocation even from an elevated launcher (`WriteProcessMemory` or
  `VirtualAllocEx`, Windows error 5). Treat live injection as unavailable while
  that protection is active; do not weaken or bypass the anti-cheat. The
  launcher and importer remain useful for a future supported capture
  environment.

  `story_recovery/build_local_runtime_artifact_audit.py` is the supported
  injection-free follow-up for artifacts produced by normal play. It scans
  only `Player*.log` and `ClientData/**/*.json` under Unity persistent data,
  matches exact keys from the generated Story index, and accepts a typed JSON
  candidate only when one object co-carries a typed Story field with a typed
  mission/quest or scene/script field. Reports go to
  `reports/story/recovery/local_runtime_artifact_audit.{json,md}`. They retain
  relative redacted filenames, game identifiers, counts, and line numbers,
  but no arbitrary log text, account directory ids, or absolute user paths.
  This is observational evidence only and never creates authored ownership,
  playback, branch, completion, or order edges.

  ```bat
  python scripts\story_recovery\build_local_runtime_artifact_audit.py
  ```

  Captures default to `scratch/story/runtime_trace/`; hook errors and missing
  playback-key probes are written to a sibling diagnostics JSONL. The current
  live `_RaiseOnScriptEvent` probe resolves the exact level/script pair but not
  the serialized `ActionHeader.localId`, so it emits an explicit null header id
  instead of inventing one. `ActionMapAsset.RunAction` still supplies exact
  action-local ids. Action-backed playback hooks recover final Story keys
  through the current-build `Param<string>` resolver, while the SNS probe reads
  the final UI object's exact dialog field. Treat the hook as read-only
  research instrumentation: it does not patch game files or gameplay state,
  but runtime injection into a live-service client can still be detected by
  client protections.

  Task hooks emit `levelscript_task` rows for local condition changes, actual
  client progress sends, and decoded server task state/progress/lifecycle
  messages. Message 815 additionally emits one
  `condition_completion_applied` row for each synchronously notified condition,
  carrying the exact condition id and applied completion boolean. When a server
  task handler synchronously raises a LevelScript event, the hook copies exact
  task context into that event's selector and the importer retains it through
  the action/playback route. The task packet family still supplies no mission or
  quest foreign key, so this context is never promoted to ownership.

  A compact capture looks like:

  ```jsonl
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":0,"monotonicMs":0,"kind":"session_start","gameBuild":"CURRENT","captureTool":"runtime-hook"}
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":1,"monotonicMs":10,"kind":"mission_state","missionId":"e11m1","state":"Processing","active":true}
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":2,"monotonicMs":11,"kind":"quest_state","missionId":"e11m1","questId":"e11m1_q1","state":"Processing","active":true}
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":3,"monotonicMs":20,"kind":"levelscript_event","chainId":"dispatch-1","levelId":"map_test","scriptId":"7001","headerLocalId":4,"eventName":"LevelEvent_OnBattleSignal","selector":{"signalId":"story_start"}}
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":4,"monotonicMs":21,"kind":"action_enter","chainId":"dispatch-1","levelId":"map_test","scriptId":"7001","headerLocalId":4,"actionLocalId":5,"actionType":"PlayRadio"}
  {"schema":"missionRuntimeTrace.event.v1","sessionId":"e11m1-run-1","seq":5,"monotonicMs":22,"kind":"story_playback","chainId":"dispatch-1","storyKey":"radio_e11m1_1","playbackType":"radio"}
  ```

  Import and publish the overlay with:

  ```bat
  python scripts\story_recovery\import_mission_runtime_trace.py scratch\story\runtime_trace\capture.jsonl
  python scripts\build_mission_pipeline_data.py --runtime-trace-bundle reports\story\recovery\mission_runtime_trace.json
  ```

  The builder adds observed rows to exact quest nodes when an active quest id
  matches, otherwise it retains mission-only context. It sets both
  `ownershipPromotion` and `orderPromotion` to `false` and adds no authored
  graph edge.
- `build_projectile_data.py`: curates exact AnimeStudio projectile
  MonoBehaviour payloads into `webui/data/gameplay/projectiles.json`. It keeps
  byte-completeness and semantic confidence separate; use `--require-exact` for
  a strict audit run.
- `build_progression_data.py`: builds
  `webui/data/lang/<LANG>/progression/index.json` as an endpoint-valid graph of
  authored character/weapon/equipment progression, item costs/use/obtain paths,
  rewards, probable bundle entries, drop pools, and wiki enemy drops. Every
  relation keeps direct table/row/path evidence; the payload explicitly excludes
  live account state, availability, probabilities, and optimization claims.
- `build_combat_relationships.py`: builds
  `webui/data/lang/<LANG>/gameplay/combat_relationships.json` from curated
  Gameplay data, the exact inherited AbilityEntity prefix/component RID list,
  the guarded/mirrored opening through `useFrameTick`, the exact 92-byte
  `surroundingConfig`, and the source graph when available. It preserves direct
  versus inferred evidence, qualifies metadata-order/enum/hash meanings,
  excludes bytes from `followMountPointConfig` onward, and adds exact-consumed Character TargetSettings only when their owner
  RIDs are reachable from the template component graph. It degrades to
  authored Gameplay plus available AnimeStudio prefix evidence when the
  optional graph is absent.
- `build_economy_data.py`: builds the language-scoped Factory view from
  authored recipe, machine, technology, logistics, utility, shop, reward, and
  activity tables. The output preserves raw ids/values and does not infer live
  simulation or account state.
- `build_world_data.py`: builds `webui/data/lang/<LANG>/world/index.json` from
  authored map/level tables, decoded WorldEntityRegistry/NPC proxy data,
  exact-prefix spawner configs, enemy/model/audio tables, and level-script
  filenames. It deduplicates mirrored roots while preserving source provenance
  and labels inferred level-prefix map links.
- `build_presentation_data.py`: builds
  `webui/data/lang/<LANG>/presentation/index.json` from the current local source
  graph. It selects authored model/controller/material/animation/effect roots,
  follows a curated set of direct and inferred presentation edges, caps
  high-degree asset relationships, rejects generic Unity asset/path-id nodes,
  and records omissions plus the static/runtime evidence boundary. A missing or
  stale graph produces a deterministic empty degraded payload.
- `build_data_index.py`: builds a legacy local decoded-config index from final
  decoded config files under `export_full/structured/StreamingAssets/Data/Json`
  and `export_full/structured/Persistent/Data/Json` by default. It writes
  lazy-loaded shards under `webui/data/game_data/`, splits
  JSON entries by clear directory structure before falling back to filename
  prefixes, parses real text JSON, identifies known MemoryPack binary `.json`
  families with IL2CPP-recovered top-level field names, and decodes stable
  `LipSync` and `LevelScriptData` preview facts. Raw `.ab` bundles, packed
  audio, video/media, streaming, irradiance, and extend-data payloads are
  intentionally excluded; the Assets/export tooling owns richer media and asset
  browsing. The current WebUI no longer loads this as a tab.
- `build_decoded_index.py`: builds a legacy local AnimeStudio decoded JSON index from
  AnimeStudio JSON outputs under
  `export_full/recovered/AnimeStudio-cli/<source>/json_by_type/`. It defaults to
  MonoBehaviour, writes lazy-loaded shards under `webui/data/decoded/`, groups
  entries by semantic domain and schema signal, splits only oversized
  semantic/schema groups into balanced lazy-loaded parts, records `$animestudio`
  metadata, decode status markers, managed-reference classes/layouts, semantic
  meaning/tags, schema/field-set IDs, and links raw previews back to
  `export_full/` without copying decoded files. The current WebUI no longer loads this as a tab.
- `build_monobehaviour_frontier_report.py`: summarizes a decoded
  `build_decoded_index.py` index into the current MonoBehaviour recovery
  frontier. It reports residual partial/unparsed groups, top schema/domain/
  registry buckets, and compact group records to
  `reports/assets/diagnostics/monobehaviour_frontier_latest.json/.md` by default.
- `build_audio.py`: decodes audio via AnimeStudio CLI, stores shared
  SFX/music once under `export_full/structured/Audio/shared/`, indexes
  language voice files under `export_full/structured/Audio/<LANG>/`, parses Wwise bank
  event-to-media links, and post-processes generated conversation JSON so
  dialog/cutscene lines and recoverable cutscene audio events can render native
  browser audio controls. It accepts scalar or list-valued audio path fields
  (`audioPath`, `audioPaths`, `audioDialogPath`, `audioDialogPaths`) from Story
  payloads and their `_debug.source` blocks.
- `hash_export_pngs.py`: hashes every `.png` file under `..\export_full\` with
  parallel readers and writes `path,hash` CSV rows to
  `..\reports\assets\export_full_png_hashes.csv` by default.
- `find_duplicate_dialog_lines.py`: scans generated
  `webui/data/lang/<LANG>/conv/*.json` files for exact repeated spoken line
  text across different missions, reporting the speaker, mission, scene, and
  line ids. It defaults to `dlg` conversations and can emit text, JSON, or CSV.
- `asset_builder/`: shared asset-browser indexing, story-media selection, and
  demo bundle helpers used by `build_assets.py` and the Updates builder.
- `pack_webui.py`: packages split shareable WebUI zips from
  `serve.py`, `..\webui\`, and displayed media files under `..\export_full\`.
  The primary zip is story/gameplay/reference code/data plus emoji, including
  the full `envEmoji_common_*` prefab layer sprite set; the companion assets zip
  carries larger images and videos; the standalone audio zip carries decoded
  story audio. Legacy local index folders are excluded by default because
  they point back to the local export tree.
- `download_bilibili_video.py`: optional gameplay-video intake helper for the
  OCR/audio story-order workflow. It downloads Bilibili pages into the flat
  `..\videos\` folder using browser-exported cookies, resumable `.m4s` parts,
  per-file `.lock` guards, and `ffmpeg` stream muxing. It intentionally uses
  the external `requests` package and is not part of the stdlib-only export
  path or any normal `export.bat` run.
- `common.py`: small shared constants and JSON/path helpers for the
  WebUI builders.
- `recover_envemoji_prefabs.py`: regenerates the `envEmoji_common_*` prefab
  registry consumed by the Story builder's EnvTalk emoji rows. Merges the
  AnimeStudio JSON pass (RectTransform layer geometry, colors, enter
  animation curves) with the Dump pass (GameObject PathID active state) so
  duplicate child names inside emoji bundles do not collide. Not part of
  `export.bat`; run it after Endfield updates that touch emoji prefab data.
- AnimeStudio CLI file exports are expected to use
  `{name}_p<PathID>` names. The export wrapper includes this naming contract in
  its cache signature and clears refreshed type folders before rerunning them,
  so stale files from older naming contracts are removed by a forced refresh of
  the affected stage/type. AnimeStudio-derived WebUI inputs that do not carry
  the PathID suffix are ignored.
## WebUI Story Helpers

These are kept because the WebUI story builders import or use them:

- `story_builder/timeline_recovery.py`: parses `dlgtl_*` Timeline MonoBehaviour
  data into authored line orders. It prefers the full AnimeStudio
  `json_by_type/MonoBehaviour` export and only falls back to filtered
  `timeline_extract` CLI exports for focused diagnostics or when the full
  export has no recoverable Timeline tracks; pass
  `--extract-timeline-assets` to force the old extraction path. Backs the
  `dialogTimeline` recovery mode, which corresponds to the runtime path
  `Beyond.Gameplay.Core.DialogTimelineManager.PlayDialogTimeline`.
- `story_builder/timeline_action_evidence.py`: scans AnimeStudio
  MonoBehaviour JSON for recovered managed-reference action payloads, follows
  `DialogMainFlowData` RID links to trunk line actions, compares the recovered
  action-flow line sequence against `timeline_line_orders.json`, and writes
  `export_full/recovered/AnimeStudio-cli/timeline_action_evidence.json`.
  The Story builder attaches compact results under
  `conv._debug.timelineActions` for WebUI `Show debug info`; it is evidence
  only and does not reorder Story rows by itself. Rich output requires a
  refreshed AnimeStudio Story JSON export that includes
  `$animestudio.recoveredManagedReferences.RefIds`.
- `story_builder/mission_recovery.py`: reconstructs mission-level quest/scene
  ordering evidence from `MissionRuntimeAsset`.
- `story_builder/dialog_registry.py`: extracts
  `Beyond.Gameplay.DialogIdTable` (the runtime's authoritative dialog
  registry) printable identifier vocabulary into a sceneKey index used by
  `scene_order_gap_shared.py` for evidence-grounded "registered vs cut
  content" classification. It sequentially decodes every key in the complete
  first 2,633-entry DialogBriefInfo MemoryPack map and labels those rows with
  `memoryPackRecordKey` / `memorypack_record_key` evidence. Printable root/line
  tokens remain separately labeled vocabulary evidence. `option_dlg_*` rows are kept as option vocabulary
  and never counted as dialog roots or trunk lines. It sequentially decodes the
  current nine-member `DialogBriefInfo`, including the authoritative
  `usedDialogTimelineIds` list (and valid `f_dlgtl_*` values), while retaining
  the schema boundary that there is no branch or option-placement field.
  Trunk/line decomposition is token-shape classification only. Runs as part of
  `export.bat` between the main export step and the build steps.
- `story_builder/source_links.py`: scans `MissionRuntimeAsset`,
  `LevelScriptData`, and `LevelScriptTemplateData` for `dlg_*`, `radio_*`,
  `sns_*`, `cutscene_*`, `remotecomm_*`, and reading-popup references. It
  writes `export_full/recovered/story_source_links.json`; the Story builder
  stamps matching conv files and index entries with source evidence and
  writes per-language coverage/orphan reports.
- `story_builder/level_bindings.py`: among the fail-closed LevelData joins,
  decodes the current 27-member top-level `LevelScriptData.interactives` map.
  Each accepted value is a completely consumed 25-member
  `LevelInteractiveData` record with an exact narrative template and component
  `94` `type_id`. Direct Story ids and exact
  `ReadingPopUpTable.contentId` joins become
  `levelscript_interactive_narrative_config` Mission Pipeline context. These
  rows bind source configuration only; script activation, player interaction,
  quest causality, ownership, and Story order remain unresolved.
  It also decodes the counted `LevelData` interactive list using exact
  StreamingAssets/Persistent byte mirrors. Non-final 25-member values use the
  next typed record as their boundary. A final value is admitted only when it
  ends at top-level member 21 and either the adjacent complete nonempty
  member-22 LevelScriptBriefData dictionary independently validates or the
  exact environment-only members 21-43 empty-script suffix validates through
  EOF. That suffix checks every current-build field, including the containing
  level's scene id, zero-valued safe-zone data, null level-specific data, and
  all empty collections. The interactive record accepts
  a null progress lock or exact current-build mission/quest-state leaf and
  recursively nested combined condition forms. Raw compare/combined operators
  are restricted to observed values `0..1`; unknown tags, member counts,
  operators, targets, depth/count overflow, or trailing bytes fail closed.
  Narrative component `94`, InteractiveTable template identity,
  and direct Story or ReadingPopUp content-id resolution produce
  `leveldata_interactive_narrative_config` context. A decoded lock proves an
  interactive availability constraint, but its state owner is not Story
  ownership; object instantiation, playback causality, and order remain
  unresolved.
- `story_builder/levelscript_binary.py`: shared raw LevelScriptData helpers.
  It verifies serialized script ids against file names and decodes the
  current 27-member top-level MemoryPack tail fields that are stable, including
  `startType` when the adjacent `startShapeList` can be skipped safely. It
  also decodes the three serialized `ActionSerializedMap` UID-list boundaries
  in the GameAssembly/MetadataRegistration-backed order (`actionList`,
  `getterList`, `headerList`) and diagnostic action payload hints, including
  `0x0bed/0x00` terminal-branch tail refs as local LevelScript action ids and
  compact `ActionHeader.nextId` prefixes on header/event rows. Both LevelScript
  UID parsers expose the normalized MemoryPack `unionTag`, concrete
  `serializedMemberCount`, common `dontLog` bool, and one-byte versus
  `FA + u16` tag encoding; old combined `code/kind` fields remain compatibility
  diagnostics, not literal opcodes for compact tags. The shared payload decoder
  also exposes exact `Split._idList` and `IfElseAction` false/true local action
  ids for fail-closed control traversal.
  On headerList rows, the fixed signed field at record `+26` is retained as
  `ActionHeader.filterLevel`; the derived payload decodes `filterMask` at `+0`
  and the event-to-action `ActionHeader.nextID` at `+5`. A guarded current
  single-entity `LevelEvent_OnEntityHpChanged` shape exposes direction, entity
  slot, and HP ratio only when its full 84-byte Param layout matches.
  The exact dynamic-list HP variant retains its LevelScript property path and
  can be joined to one matching `ListAddValueEntityPtr` writer and one constant
  `OnSpawnerEntitySpawn` producer in the same script. Exact
  `OnNpcPatrolCheckpointReach` rows expose dynamic NPC property path, patrol id,
  checkpoint index, NPC-position output, and local/no-server transport.
  ActionBase tag/member-count `0x031e/0x0c` is decoded as exact-EOF
  `NpcPatrolStart(startFromBeginning, patrolId, forceIdle, targetNpc)`. The
  mission-context matcher additionally requires a case-sensitive type-13
  BriefData property, same-entry world-entity reference, current registry row,
  same-script producer, fully consumed `NpcPatrolData/9` point list, in-range
  checkpoint, and one MissionRuntime union across matching same-scene
  `EntityTrackingInfo` rows. Multiple candidate quests remain non-owning.
  The inherited ScriptEvent header is replayed after the variable-length
  `_validate: Param<bool>` object, so validation-node `idRef` values are not
  mislabeled as script ids. Exact `OnScriptActive` and
  `OnScriptStageChanged` rows expose SELF/SPECIFY_SCRIPT scope, optional target
  script parameters, stage filter/output parameters, and the proven local
  runtime/no-server boundary. Exact EOF-bounded `OnSpawnerGroupBegin` and
  `OnSpawnerWaveBegin` shapes expose constant group/wave keys and
  `SpawnerPtr.id` values while rejecting dynamic outputs or extra bytes.
  Exact `OnSpawnerComplete` exposes its constant id and server-push contract;
  exact `EntityEvent_OnSavePropertyChanged` exposes a constant target entity,
  property key, outputs, and local/no-server boundary. Bounded detail decoders
  also retain teleport-finish, squad-fight, entity-skill, entity-death,
  encounter-battle, and skip-popup fields without promoting ownership.
  ActionBase tag/member-count `0x0304/0x09` is decoded as
  `ManuallyStartGuideGroup`, including its exact `guideId` literal for the
  fail-closed producer/completion matcher.
  When a two-block action map has an omitted/empty getter block followed by a
  header-shaped final block, it labels that final block as `headerList`.
- `story_builder/spawner_binary.py`: fail-closed current-build MemoryPack
  reader for the final `SpawnerConfig.waveMap`. It requires one complete parse
  to physical EOF, decodes the exact eleven-field wave and twelve-field group
  rows, and leaves nested action maps opaque. Dictionary indices, member
  counts, field bounds, named group uniqueness, and wave/group keys are
  validated before the source-only order audit may use PartKilled
  dependencies.
- `story_builder/timeline_recovery.py`: in addition to dialog line and option
  recovery, resolves black-screen text playables through their owning Timeline
  track and serialized parent PPtrs to the Actor root, then joins the Timeline
  through exact `DialogBriefInfo.usedDialogTimelineIds` membership (with the
  existing root mapping retained as a fail-closed fallback). A black id reaches
  mission-shell context only when the parent dialog also has typed playback and
  a validated LevelData BriefData host, or when the exact parent dialog has one
  unique direct original-data mission context. Parent dialogs attached to
  multiple quests stop at the mission shell; unresolved Actor roots remain
  diagnostic. If the disposable per-CHK `timeline_extract` directory is
  absent, the attachment pass may use the current full typed MonoBehaviour
  export only after an exact Actor-root filename from the current line-order
  index selects the source. SourceFile and PathID checks still guard every
  playable, track, and parent hop. The current fallback recovers 17 exact rows
  across 13 black Story keys and labels the source mode in generated evidence.
- `story_builder/anime_assets.py` also decodes the base64 `m_Script` of
  installed-game `dlg_*.json` TextAssets and extracts only exact
  `DialogNarrativeMaskActionData.texts[].key` or
  `DialogComplexNarrativeMaskActionData.textDataList[].langKey.key` values from
  typed DialogTree node action containers that have a managed-reference `$id`.
  Literal stage directions, custom text, and ID-less unreachable editor nodes
  never create links. A resolved black Story file can inherit one unique
  direct parent-dialog quest/mission placement; exact LevelScript/LevelData
  host chains remain the weaker `derived_exact_shell` mission tier, and
  multiple parent dialogs fail closed. The separate typed
  `DialogLeftSubtitleActionData.text1..text4` extractor keeps the same parent
  scoping but emits a distinct local-presentation relation. Current data binds
  the two `black_e0m2_1` LangKeys through `dlg_e0m2_4` to the `e0m2` mission
  shell; it is not black-screen playback, audio, quest placement, or a network
  exchange.
- `story_builder/video_bindings.py` builds the narrative video binding evidence used
  by the Story builder. It scans dialog `timeline_extract` outputs plus the
  full story-scoped AnimeStudio `json_by_type/MonoBehaviour` exports, so
  gameplay cutscene playables such as `*_cutscene_*_actor.playable` can bind
  `BeyondFMVPlayableAsset.fmvId` back to a cutscene entry. It also consumes
  typed LevelScript `PlayFmvAction` occurrences when the exact decoded native
  `_moviePath` / `_fmvId` field and native schema mapping agree with the
  normalized `cutscene_*` Story key. Timeline- and LevelScript-backed links are
  preserved into
  `webui/data/lang/<LANG>/narrative_video_evidence.json` so a WebUI video can
  be traced to the exact playable or native LevelScript source instead of
  relying on filename matching. An exact LevelScript FMV action can materialize
  a missing `cutscene_*` Story card, which in turn lets existing LevelScript
  control-path evidence participate in the Mission Pipeline. Gender-prefixed
  video variants inherit only the exact canonical base-FMV binding. Narrative
  videos that only match by name are emitted as standalone `video` story files
  grouped by mission, while resolved mappings attach to the dialog, cutscene,
  remotecomm, or other story file and keep the standalone row adjacent in
  Story sort. Timeline / playable evidence supplies authored inline placement
  when available. Manual attach and suppression rules in
  `webui/overrides/narrative_videos.json` cover known filename mismatches and
  known false attachments while keeping standalone video rows. An attach rule
  can also set `audioFrom` to copy source cutscene audio events into the
  attached target during the audio relink step. The source graph resolves an
  FMV edge to the exact scene when that generated Story node exists, otherwise
  retains the established fallback Story hint, and keeps typed LevelScript
  source-file edges alongside playable-asset sources.
- `story_builder/` also scans narrative video folders under
  `Data/Video/PC/Narrative/Cutscene` and `RemoteComm`, attaches matching
  `narrativeVideos` to dialog/cutscene/remotecomm conv JSON, and writes
  `reports/story/build/narrative_videos_<LANG>.json` / `.md`.
- `story_recovery/build_narrative_video_override_audit.py` validates
  `webui/overrides/narrative_videos.json` against the generated Story video
  report, `narrative_video_evidence.json`, video indexes, and conv payloads.
  It reports missing override stems/targets, missing `audioFrom` source keys,
  stale attach/suppress rules, filename-only attachment candidates, and
  unresolved video candidate keys.
- `story_recovery/build_option_override_coverage_audit.py` validates
  current `inferredOptionLayout` and `inferredOptionResponse` warning records
  against `webui/overrides/options.json`. It writes
  `reports/story/recovery/options/option_override_coverage_<LANG>.json` / `.md` and distinguishes
  raw recovery uncertainty from manual WebUI display coverage.
- `webui/overrides/options.json` is a runtime WebUI-only manual
  override file for known option recovery gaps. It can pin option groups with
  `positions.after.<lineId>: ["<group>"]` or `positions.pre`, and can map
  inferred option replies with `responses.<optionId>: ["<lineId>"]`. Edit it
  and refresh the browser; no Story rebuild is needed. Overrides do not promote
  new automatic evidence, and overridden rows are tagged in the Story view.
  Generated Story index entries with option issues include compact
  `optionIssueTargets` metadata. The frontend uses those stable targets to
  remove an issue counter only when the runtime override covers every affected
  group/option; partial coverage remains in the outstanding queue.

## Story Recovery Tools

These tools are not part of `export.bat`. Most live under
`scripts/story_recovery/` so the root export/package commands stay easy to
scan; the root-level Bilibili downloader is listed here because it feeds the
gameplay-video OCR/audio workflow.

- `story_recovery/build_mission_dependency_graph.py`: recovers the
  inter-mission graph from authored cross-mission state conditions
  (`CheckMissionState`/`CheckQuestState` and their `SimpleCondition*`
  counterparts), including nested `CombineCondition.subConditions`. Emits
  `reports/mission_graph/mission_dependency_graph.{json,md}`. Relations are
  kept distinct rather than collapsed: only `requiresCompleted` is precedence,
  while `requiresProcessing` is a co-active window and `abortsOnCompleted`
  (a `failedCondition` reference) is mutual exclusion; an unpinned
  comparer/state pair stays `unclassified` instead of being guessed. The
  builder also constructs the quest-granularity graph from `prevQuestIdList`
  plus cross-mission quest precedence, and only calls a mission-level cycle an
  `interleaving` when that quest graph is acyclic -- otherwise it is reported
  as an unexplained cycle. Mission unlock order is server-authored, so a
  missing edge never means two missions are unordered. It uses the same
  complete-Persistent-or-Streaming fallback selector as Mission Pipeline; the
  current corpus has 524 state rows, 197 cross-mission rows, and 155 edges
  across 154 missions (141 precedence). Mission Pipeline embeds
  the per-mission entry as `missionGraph`.
- `story_recovery/build_envtalk_attachment.py`: maps ambient `env_*` Story
  files to their authored consumers. `EnvTalkTable` is definition-only and has
  a verified 1:1 bijection with the `env_<envTalkId>.json` conversation corpus.
  Consumers are read by exact field name from `NpcProxyTable` (including
  nested `lazyDestroyEnvTalkData`), `NpcProxyExDataTable`,
  `AtmosphericNpcClusterDataTable`, and `NpcTable`. Two exact non-owning
  context joins are retained: a typed `NpcProxyTrackingInfo.npcProxyId` whose
  proxy carries `envTalkIds`, and a same-level atmospheric cluster whose full,
  non-empty NPC set is contained by exactly one active switcher group. The
  latter reads only exact mission/quest fields under that group's condition
  plus `bindMissionId`; partial, cross-level, ambiguous, and config-identity
  mismatches fail closed. These relations describe navigation or NPC-group
  availability, never playback, ownership, chronology, completion, or a
  server exchange. Consumer references absent from `EnvTalkTable` are reported
  with a whitespace flag and never repaired by trimming. Emits
  `reports/mission_graph/envtalk_attachment.{json,md}`; Mission Pipeline embeds
  `envTalkContext` per mission and a separate `envTalkTriggerManifest` that is
  deliberately kept out of the Story coverage denominator.
- `story_recovery/build_node_attachment_coverage.py`: measures whether Story
  files reach a *quest node* rather than only a mission shell, which is the
  unit the pipeline graph draws. Splits the corpus into quest-attached,
  mission-shell-only, and unlinked, then reports which shell-only rows already
  name a candidate quest, broken down by relation and candidate count. Rows
  whose relation is policy-blocked (currently
  `pos_tracking_trigger_center_story_context`, spatial proximity) are counted
  separately and never presented as placeable. It also runs one independent
  exact join: a shell-only row whose hosting LevelScript is named by exactly
  one quest objective condition (typed `_scriptId`), globally unique and in the
  row's own mission, is reported as a quest-level *scope* placement — the
  objective may read a different property of that script than the one that
  plays the Story, so this is never playback ownership. When several objectives
  name the same script, the audit admits one additional discriminator only: an
  `exact_unique_getter` naming one of those quests must occur on that exact
  Story playback path in the same script. Script-wide strings and unrelated
  paths never select a quest. Mission Pipeline publishes admitted rows as
  `nodes[*].storyScopeContexts` with explicit `playbackOwnership: false` and
  `orderEvidence: false`; the source graph mirrors the same non-owning
  quest/LevelScript/Story relation. Rejected rows are retained in
  `scriptScopedQuestAmbiguities` with same-mission versus foreign-owner
  classification. Emits
  `reports/mission_graph/node_attachment_coverage.{json,md}`.
- `story_recovery/build_source_story_partial_order.py`: builds a strict,
  source-only per-mission partial-order and branch audit from the generated
  Story index, mission bundles, and conversation payloads. It does not read
  `webui/overrides/story_order.json`, OCR proposals, numeric scene suffixes,
  generated UI rank, or `sceneOrderInfo.questOrder`. Strong source edges are
  augmented by exact serialized LevelScript event-to-action path-prefix edges:
  if the complete local-id path to one Story action is a strict prefix of the
  path to another action under the same event header, the former precedes the
  latter. Equal paths, divergent paths, conflicting reverse evidence, native
  registration order, and byte offsets never create this edge. Mission Pipeline
  invokes this audit and embeds its per-mission graph in lazy mission payloads.
  Filename ownership is not allowed to hide such a chain: an external Story
  key is admitted to one mission audit only when its exact native path is
  prefix-comparable with an index-backed scene under the same event header.
  Generic mission host context, equal/divergent paths, file order, and
  scene-graph clues do not expand the candidate set. Current CN data admits 21
  such context placements across 14 missions and exposes 31 additional strong
  edges.
  A second, weaker cross-owner candidate rule requires three exact inputs:
  an already indexed Story card, a typed final-playback occurrence, and a
  `levelscriptSceneChain` edge carrying the same source file. These nodes are
  labeled `exactLevelScriptPlaybackContext`; they remain supported/weak
  context and never become authored mission ownership or strict chronology.
  Current CN data adds 11 such cutscene placements and leaves the stronger 21
  native-control-path placements unchanged. Per-endpoint action classes remain
  on generic scene-chain edges. A missing endpoint that is only
  `preload_cutscene` is reported separately under
  `definitionOnlySourceNodes`, unless another exact final-playback occurrence
  for that Story key exists anywhere in the installed corpus. Current schema
  `sourceStoryPartialOrder.v19` has zero unresolved source nodes and preserves
  two `e9m2` preload-only definitions.
  When a base mission bundle explicitly lists
  `flow.sceneGraphVariantMissions`, the audit also loads those exact generated
  variant bundles and merges only the route/quest evidence collections it
  consumes. Undeclared, missing, or identity-mismatched files fail closed.
  This restores e10m4d5's exact route evidence to the base e10m4 graph,
  including three native path-prefix edges that had appeared only as weak file
  order. A cross-Story DialogTree trunk continuation is additionally strong
  only when one exact registered carrier chain covers every child line and its
  current-parent closure covers every parent line; the first recovered edge is
  `dlg_e10m4_3 -> dlg_e10m4_14`.
  Source-graph ingestion preserves the same boundary through explicit
  `mission_story_context` nodes for exact playback context and
  `mission_story_definition` nodes for preload-only references. It never emits
  a direct mission-to-Story ownership edge for either class, and it does not
  create an indexed Story card for a preload-only identifier. A generic
  source-reference placeholder may still exist because the LevelScript
  literally contains that id.
  Native `Branch` (`0x002d/0x09`) is distinct from conditional fan-out. Its
  runtime fields are `_idList` and `m_index`; the installed
  `GameAssembly.dll` `Branch.Execute` body reads the indexed list entry, uses
  `ActionBase.SetResultReservedID` between non-final entries, calls
  `SetResultNextID`, increments the index, and resets it after the list ends.
  The exact full-length MemoryPack list is therefore followed as ordered
  continuation and exposed as `Branch.sequence[n]`, never as a `Split` arm.
  Current CN recovery gains 43 distinct exact owner paths across 14 Story keys:
  13 formerly actionable weak-only keys become exact-native closed, and the
  comparable c28m1 path adds
  `radio_c28m1_9 -> radio_c28m1_15`. The e10m4 cutscene path is restored under
  custom event `start_p2`, but remains unordered against
  `radio_e10m4_69` because those paths diverge at a preceding typed `Split`.
  Exact divergent `Split.actions[n]`, `IfElseAction.true/falseAction`, and
  `SwitchInt.case[n]` paths are retained as native fan-out/branch arms without
  ordering siblings. A native convergence is emitted only when every observed
  arm route contains the same later local ID. Branch rows also retain the exact
  serialized event selector and condition evidence: typed PureGetter identity,
  decoded comparer/path/value operands where supported, or an exact inline
  Param. Current CN data has event details for all 73 native branch groups;
  source-100/null-path outputs remain parameters rather than invented local
  refs, and outer ActionMap bytes do not hide zero-field ScriptComplete events.
  Class-only predicates remain visibly distinct from unresolved ones. The
  original-data `questSequence`, `questFailGuard`, `authoredMenu`, and generic
  `levelscriptSceneChain` relations remain visible as supported topology but
  do not order scenes:
  `questSequence` is assembled from heterogeneous quest-local reference
  collections, failed-condition references are branch guards, and menu/submenu
  reachability can be cyclic. The installed `QuestInfo.prevQuestIdList` /
  `MissionRuntimeAsset.BuildConnectionBetweenLayers` contract supports
  `questPrev` as the inter-quest order relation; it does not give the first
  three
  relations a playback-order contract. If projecting distinct quest instances
  onto reusable Story file nodes produces reciprocal `questPrev` edges, both
  file-level edges are demoted to supported topology with
  `demotionReason=reciprocalQuestProjection`; the quest DAG remains valid, but
  it does not select one global order for the reused files.
  The installed ActionBase formatter table likewise proves that the generic
  LevelScript chain can connect Story-looking payloads on
  `PreloadDialogAction`, `PreloadCutsceneAction`, `RemoveNPCDialog`,
  `OverrideNPCDialog`, and stop actions. It can also cross separate physical
  `ActionSerializedMap` list roots. Those references prove source topology,
  not playback. Strict LevelScript order therefore comes from typed playback
  actions on exact serialized event/control paths or from the decoded
  `LevelEvent_OnDialogExit` relation.
  Exact `LevelEvent_OnQuestStateChanged` paths are also retained with their
  source file, complete local-id path, and each typed playback position;
  consecutive positions on one identical path emit
  `levelscriptQuestStateActionPath`.
  A second narrow source-only rule joins exact typed
  `LevelEvent_OnSpawnerWaveBegin` playback to a uniquely decoded original
  `SpawnerConfig` wave/group map. Only mode-2 `PartKilled` rows with an explicit
  `waveModeTargetKey` emit `spawnerWavePartKilled`; the installed runtime
  resolves that target key to `previousWaveBlock` and checks its killed count
  before the dependent wave starts. The decoder also consumes exact
  twelve-field `SpawnerGroupData` rows while leaving their action maps opaque.
  `spawnerWaveGroupPartKilled` is emitted only when installed
  `InitWave`/`OnInit`/`AllowToStart` semantics prove that one named parent
  group dominates every possible spawn in its wave, or when a parent
  wave-begin callback precedes a group callback in the dependent wave. A
  group/wave callback may reach Story playback through an exact same-script
  `RaiseCustomScriptEvent` relay only when the generated native evidence
  preserves the producer control path, exact current-script receiver, exact
  listener key, and exact listener-to-playback route.
  Multiple Story listeners on one group event remain unordered. Parallel or
  Sequence layouts without a complete domination chain, unrelated group
  events, and HP thresholds remain non-ordering.
  The strong graph is condensed
  into an SCC DAG and transitively reduced; weak file/order clues,
  cycles, isolated scenes, rejected option evidence, and option groups with no
  explicit route remain visible instead of being forced into a total order.
  Intra-dialog option routes are promoted from direct
  DialogTree/DialogTreeFragment paths, the exact decoded Runtime Jump Track
  signature, or complete distinct positive Timeline clip `optionIndex`
  coverage. The latter fails closed unless every branch clip matches its
  authored option index and every in-window Runtime Jump occurs after that
  option's last response clip and converges forward to the shared continuation.
  Runtime Jump paths are reduced to their option-exclusive prefixes;
  a choice that skips directly to the shared continuation is represented
  explicitly instead of requiring a fabricated response line, including
  option slots before the first local dialog line. Zero-index Timeline trunk
  clips remain shared even when fewer local lines than options remain.
  Distinct zero-index Timeline slots are sequential prompts, a slot after the
  last local line has no local line route, and same-text local table options
  are definition-only when the exact cinematic consumes a complete foreign
  option-id/finish-number set. When a generated same-prefix table group is
  only partly present in every recovered DialogTree, scene-link, and Timeline
  consumer, the absent ids remain visible as definition-only rows instead of
  being counted as missing authored branches. Complete authored menu, UI,
  loop, and terminal outcomes are likewise retained as closed non-line
  outcomes rather than missing line routes. An option target that reaches an
  exact `DialogTreeIfNode` retains every serialized conditional outcome (line
  path, OpenUI, or Finish); a following option/submenu node is explicitly not
  classified as a conditional branch. Same-prefix ids serialized on distinct
  DialogTree option nodes are closed as separate conditional prompts, while
  ids on one disconnected option node with no outgoing connection are closed
  as orphan definitions. Neither layout is promoted into a fabricated choice
  fork. Source-less option rows on a scene absent from the runtime
  `DialogIdTable` are also closed only after the complete collector finds no
  authored route or outcome consumer. Run
  `python scripts\story_recovery\build_source_story_partial_order.py`; it
  writes `reports/mission_order/source_story_partial_order_<LANG>.json` / `.md`.
- `story_recovery/build_source_story_order_cross_reference.py`: compares only
  strict direct edges from the source partial-order report against
  `webui/overrides/story_order.json` and `webui/data/story_order_ocr.json`.
  The two lists are fallible comparison inputs: agreement never promotes an
  edge, disagreement never removes one, and supported/weak relations are
  ignored. It reports agree/disagree/uncovered counts plus cases where OCR and
  the manual list contradict each other on the same strict edge. Run
  `python scripts\story_recovery\build_source_story_order_cross_reference.py
  --language CN`; it writes
  `reports/mission_order/source_story_order_cross_reference_<LANG>.json` /
  `.md`.
- `story_recovery/build_source_story_gap_queue.py`: reuses the strict partial
  order in memory and ranks the remaining source-recovery work by mission and
  evidence frontier. The score is triage only, never chronology. It separates
  core Story isolation from ambient `env`/standalone-video rows, and scores a
  quest attachment gap only when diagnostic Story evidence exists but no
  strict attachment does. Exact current-build playback under either
  `unlinkedNativePlayback` or the binary-derived native playback index counts
  as typed control flow even when a weaker pre-existing quest-context row
  caused the bundle to omit the redundant native row. The index join requires
  the exact source file, action-list membership, playback class, Story
  identity, and GameAssembly mapping; it supplies no ownership or chronology.
  The complete action occurrence census also separates actionable missing
  playback types from exact binary-negative contexts. Current-build
  `PreloadDialogAction`, `PreloadCutsceneAction`, `OverrideNPCDialog`,
  `RemoveNPCDialog`, and `StopRadio` references, plus Story strings outside
  `ActionSerializedMap.actionList`, remain visible under
  `closedNonPlaybackLevelscriptContexts` but do not contribute to the
  actionable LevelScript-gap score. Unknown action tags still fail closed and
  remain actionable.
  Weak-only rows are scored as control-flow work only when a physical
  action-list record still lacks the exact native route. Complete typed
  event-to-playback paths with no prefix-comparable second Story action are
  reported as exact-native closed; file/order or quest topology without an
  action record remains visible but non-actionable. Isolated exact-native
  playback is likewise a closed partial-order limit, not a missing source
  link. The same exact-native bucket also closes a nested narrative-mask file
  only when every authored use has complete mission scope and the typed
  DialogTree `connections` graph gives one unique adjacent parent trunk on
  each side, with the action reached from the binary-defined prime node through
  that predecessor. The report preserves those before/after line ids, but adds no
  scene-file edge because the parent file contains content on both sides.
  Node-array order, editor position, filename suffixes, OCR, and manual order
  remain inadmissible for that closure.
  An isolated dialog with exact mission-level
  `npc_proxy_ex_mission_context` is separately reported as
  `closed_exact_runtime_config_no_relative_order` only when it retains the
  current native mapping/hash and the proved one-based
  `exDatas[activeCondIndex - 1].dialogId` selector boundary. This establishes
  selectable mission-scoped configuration, not a quest trigger or relative
  order, and adds no edge. A proxy may live in another mission bundle only when
  its exact `storyOwnerMission` names the Story file's nominal mission and its
  `npcProxyMissionId` equals that context bundle; this is recorded as an exact
  cross-mission runtime context and does not move the Story file into the
  context mission chronology. Current-build `black_*` rows carrying the full
  `original_text_definition_without_consumer` classification are also excluded
  from actionable isolation after the bounded LevelScript, DialogTree, and
  Timeline consumer search.
  An exact `CheckTalkOptionFinish._dialogId` objective condition is likewise
  closed as a Story-to-quest completion dependency, including when the
  consuming mission has no Story partial-order row of its own. The condition
  proves that the quest reads the dialog's synchronized finish state; it does
  not identify the dialog activator, transfer Story ownership, or add a
  Story-to-Story chronology edge.
  Exact typed MissionRuntime `client_action_start`, `_succeed`, and `_failed`
  rows likewise count as strict quest attachment when their lifecycle slot,
  phase, action id/type, and serialized Story-id source all agree. An isolated
  Story file reached by such an action is closed as exact quest-lifecycle
  playback context, not relative Story order.
  A narrower current-build-only deferral class removes a row from scoring only
  when every named offline evidence gate remains exact.
  `sourceStoryGapQueue.v40` evaluates 172 residual radio definitions, 25 root
  cutscene carriers, 25 registered dialog definitions, five exact
  DialogTextTable-only/no-registry groups, ten exact
  ReadingPopUp/RichContent definitions, two text-only cutscenes, and two
  TextTable-only black narrative definitions across
  `e0m0`, `e1m3`, `e2m4`, `e3m3`, `e6m3`, `e6m4`, `e7m2`, `e7m3`, `e9m2`, `e10m3`, `e10m4`,
  `e11m1`, `e11m2`, `e11m4`, `e11m5`, `e11m6`, and `e11m8`. It defers 169 radio definitions;
  two close through strict exact native mission context, and one through
  strict exact runtime configuration. This includes seven bounded `e1m3`
  radio definitions, its canonical misc-dialog definition and one-host
  Timeline root; `radio_e1m3_13` instead closes through an exact mission-state
  radio-trigger-zone carrier, and `radio_e1m3_32` through an exact local
  leader-trigger playback path joined to e1m3 MissionRuntime world-entity
  tracking. Neither context supplies relative Story order. It also includes
  all five e7m2 radios, two registered dialogs, two ReadingPopUp/RichContent
  definitions, and the one-host registry-id-406 designer cutscene; all eight
  e3m3 radios plus two registered dialogs, preserving the 18-line/four-option
  `dlg_e3m3_12` definition without inventing an option route; three e0m0
  radios, four registered Timeline roots, one explicit unregistered
  root/PlayableDirector carrier, and one ReadingPopUp/RichContent definition.
  The remaining e0m0 quest gap stays active because same-script scope is not a
  strict quest attachment. e10m3 adds two registered dialogs (including one
  exact 19-line/two-track Timeline) and three ReadingPopUp/RichContent
  definitions; its interact-locked radio instead closes through exact
  FocusModeInstanceTable runtime context. The three DialogTextTable-only e10m3
  groups use a separate fail-closed schema requiring exact line/audio sets,
  absent AudioDialog membership, absent DialogId registration, absent
  DialogTree assets and Timeline rows, and the carrier-audit negative.
  e6m4 adds seven audio-complete radios and two one-host, registry/hash-locked
  Timeline roots.
  e7m3 adds two radios, two readings, and three registered dialogs while
  retaining their option groups without treating option presence as a route.
  e11m8 adds one radio, one registered owned-Timeline dialog, and two
  no-registry one-line dialogs with exact present AudioDialog membership.
  Its two bare black files use the generic TextTable-only absence gates; a
  third black file closes as an exact parent DialogTree action disconnected
  from the prime-node path, without asserting playback or order.
  e2m4 adds seven radios and one registered five-line/two-option dialog.
  The class also includes all five bounded
  `e6m3` radios, its three dialogs, two text
  definitions, and 14-row text-only cutscene; all eight residual `e9m2` radios and five
  root cutscenes, all 23 residual `e11m1` radios, all nine residual `e11m2`
  radios, all seven residual `e11m5` radios and seven dialogs, and all 22
  residual `e11m6` radios. It requires the
  expected
  `GameAssembly.dll`,
  RadioTable, AudioDialog, TextTable, NumIdStrTable, and cutscene-definition
  hashes; the complete provenance-valid carrier audit and current core-target
  digest; exact RadioTable schema and AudioDialog membership; exact Timeline
  registry ids and every physical root definition variant, or the complete
  text-only definition group; and current
  GameObject plus reverse-PPtr audit negatives. Timeline roots additionally
  require exact forward GameObject row counts and exact `PlayableDirector` host
  counts. The two e11m2 `liexi` cross-Story root/playable-asset aliases are
  retained as exact composition evidence but explicitly remain non-chronology,
  non-ownership relations. Dialog deferrals additionally require exact
  MemoryPack DialogId source/index hashes and registration rows, complete
  DialogTree hashes, exact DialogTextTable row schemas, AudioDialog membership,
  and no recovered route. The e11m6 dialog also requires its exact six-line
  insertion inside the shared e11m5 Timeline; that containment remains context,
  not activation or whole-file order. The owning `dlg_e11m5_9` dialog
  independently requires the exact registered Timeline id, full 17-line mixed
  e11m5/e11m6 clip sequence, source file, track PathID, and terminal option ids.
  A hash-locked definition may defer an isolated scene even when the Story
  builder omits it from the narrower `unlinked` denominator, but only while
  the complete carrier audit remains negative and no accepted mission/quest,
  native, or definition route exists. The owned Timeline remains composition
  rather than activation or whole-file chronology.
  Declared missing AudioDialog ids are also fail-closed per dialog rather than
  treated as present membership. A text-only group
  is admitted only when its complete TextTable rows remain exact and no
  Timeline registry row, GameObject target, reverse relation, director host, or
  route exists. Deferred rows remain visible as
  `deferred_current_build_offline_surface_exhausted`, add no graph edge, and
  automatically become actionable again if a hash, target set, mission
  assignment, route, or audit gate changes.
  Exact Timeline-contained black-screen playback is separately closed as
  native context only when every clip, parent dialog, registered Timeline,
  variant LevelData host, and parent event-to-dialog path agrees. It adds no
  scene edge when the parent dialog has content on both sides. Unique
  `levelscript_mission_context` rows whose every occurrence names one exact
  MissionRuntime objective-script owner also count as strict quest attachment,
  without implying relative Story order.
  Authored non-mission isolation is also closed without an edge. Speaker radio
  continuation and character SNS topics come only from their keyed tables.
  `radio_blackbox_common_1` comes from the separately freshness-checked
  GuideRuntime audit: 13 exact `FacSetInteractLockedState` actions across 10
  factory tutorial assets, with current native `Execute` semantics and no
  mission/quest owner. Filename shapes never admit this class, and guide action
  ids or `nextId` values never become mission order.
  Run
  `python scripts\story_recovery\build_source_story_gap_queue.py --language CN`;
  it writes `reports/mission_order/source_story_gap_queue_<LANG>.json` / `.md`.
- `story_recovery/build_mission_order_evidence_audit.py`: expands one mission's
  current Story candidates into an evidence inventory without changing the
  partial order. Reading/PRTS rows count as links only through an exact
  `contentId`; same-number or transformed-suffix candidates are emitted
  separately as fallible cross-references and never as ownership, playback,
  or chronology evidence.
- `story_recovery/build_runtime_jump_option_route_audit.py`: audits remaining
  live `inferredOptionResponse` warning groups against nearby Runtime Jump
  Track clips, including forward skip ranges, reverse/directional ranges, and
  `needChangeOptionAfterJump` markers. It writes
  `reports/story/recovery/options/runtime_jump_option_route_audit_<LANG>.json` / `.md`. Use it
  before promoting any new automatic option-route rule. Pass
  `--include-promoted-risk-groups` only when you intentionally want to inspect
  already anchored diagnostic `optionBranchRisk` rows.
- `story_recovery/build_option_route_evidence_controls.py`: summarizes
  positive Runtime Jump route controls from `timeline_line_orders.json` beside
  the current negative-control `runtime_jump_option_route_audit` queue. It
  writes `reports/story/recovery/options/option_route_evidence_controls_<LANG>_priority.json` / `.md`
  and documents the evidence bar for promoting inferred option responses.
- `story_recovery/build_priority_story_order_audit.py`: summarizes the current
  main-story, event, major-mission, and character-story recovery surface from
  the built WebUI data. It writes `reports/story/recovery/order/priority_story_order_<LANG>.json` /
  `.md`, including ordered/unknown totals, remaining inferred responses,
  non-runtime option-layout rows, uncovered line warnings, and top unknown
  missions.
- `download_bilibili_video.py`: optional downloader for collecting gameplay
  videos before OCR. It accepts BVIDs directly or from `--bvid-file`, defaults
  to the repo-local cookie export at
  `cookies/www.bilibili.com.cookies.json`, writes flat `.mp4` outputs under
  `videos/`, prefers AVC for local playback, adopts matching legacy nested
  video files unless `--no-adopt-existing` is passed, and skips completed files
  unless `--overwrite` is used. Use `--dry-run` to inspect planned filenames
  without downloading. It requires network access, `requests`, valid Bilibili
  cookies, and `ffmpeg`; keep partial `.m4s` and `.lock` files out of the OCR
  corpus until the muxed `.mp4` is complete.
- `story_recovery/build_gameplay_video_ocr_audit.py`: lower-level OCR worker
  used by the full gameplay video story-order pipeline. It samples final
  gameplay videos from `videos/`, crops the subtitle/options band of every 10th
  frame by default (`13%-100%` width, `50%-97%` height) at source resolution,
  and runs OCR on that crop. The default engine is **PaddleOCR PP-OCRv5**
  (`--ocr-engine paddleocr`, `server` variant), which is markedly more accurate
  on Chinese subtitle text and, on a CUDA build, far faster (~0.13 s/frame on an
  RTX 5080) than the legacy **EasyOCR** engine (`--ocr-engine easyocr`). EasyOCR
  uses a Story-derived character dictionary by default, built from CN
  conversation text, speaker labels, summaries, and options; pass
  `--disable-ocr-dictionary` for unconstrained recognition (the dictionary
  allowlist applies to EasyOCR only - PaddleOCR's recognizer has a fixed
  dictionary and relies on downstream Story matching to filter). It writes
  per-video reports plus an aggregate index under
  `reports/gameplay_video_ocr/`. The runner skips `.lock`, `.m4s`, zero-byte,
  and other partial downloads, and it skips already completed videos when a
  complete per-video OCR report already exists for the same source file. Use
  `--frame-step 10` for the current default cadence, `--dry-run` to inspect
  pending videos, `--limit-frames` for smoke tests, and `--force` only when
  intentionally reprocessing completed videos. Decoded sampled-frame JPEGs are
  kept by default under `tmp/ocr/gameplay_video_ocr/frames/`; reruns reuse existing
  frame files and append only missing sampled frames. Pass `--discard-frames`
  only for a disposable run. The default OCR language is Simplified Chinese
  (`chi_sim`; for EasyOCR mapped to `ch_sim`). PP-OCRv5 weights are cached under
  `~/.paddlex/official_models/`; EasyOCR weights live under `tools/easyocr/`.
  Both recognizers also support ASCII letters, digits, and common punctuation.
  OCR output
  is filtered before it becomes a segment: UID/latency overlays are stripped,
  Chinese-rich spans are extracted from mixed junk lines, short lines are
  dropped unless they look like short Chinese speaker names, and mostly-symbol
  lines are rejected. The default recognition and line filters are
  intentionally permissive so short subtitle fragments, speaker names, and
  lower-confidence OCR boxes are kept for matching. Mostly-black sampled
  frames bypass the normal subtitle crop and are replaced in the decoded-frame
  cache by a near-full-frame OCR crop (`10%-97%` height) that avoids the top
  HUD and bottom UID strip. Archive-box frames and detected SNS interface
  prompts, such as the first-frame P11 SNS option panel, get a second exact
  source-frame OCR pass using the same near-full ROI and are recorded as
  `archive-box` or `sns-interface` observations. The script logs OCR
  configuration, report output location, pending/skip reasons, pending video
  order, ffprobe metadata, black-frame scan stats, frame extraction status,
  EasyOCR image groups, OCR dictionary size/hash, per-batch OCR timing,
  kept/filtered frame counts, dark-frame/archive/SNS near-full crop counts,
  the full filtered per-frame timeline in each per-video markdown
  report, per-video elapsed/remaining/ETA lines, an overall video progress bar,
  and a live status index at
  `reports/gameplay_video_ocr/gameplay_video_ocr_index.md`. It orchestrates
  external `ffmpeg`/`ffprobe` plus the OCR engine (PaddleOCR/Paddle on CUDA, or
  EasyOCR/PyTorch). ffmpeg tries CUDA/NVDEC decode automatically when the local
  ffmpeg build supports it, with CPU fallback if hardware decode fails. Both OCR
  engines use CUDA when available unless `--easyocr-cpu` (the shared force-CPU
  switch) is passed. The PaddleOCR GPU path uses a locally built
  `paddlepaddle-gpu` wheel with Blackwell `sm_120` support; it imports `torch`
  first so paddle reuses torch's bundled CUDA 12.8 / cuDNN 9 runtime DLLs (see
  `memory/` notes / `scratch/ocr/paddle_build/`). The PP-OCRv5 server default
  `--paddleocr-frame-batch-size 40` was benchmarked on cached P10 gameplay
  crops on an RTX 5080; batch 56 was effectively tied, while 64+ regressed.
- `story_recovery/build_gameplay_video_story_order.py`: full OCR/audio-to-order
  promotion pipeline. It can run the OCR sampler first with `--run-ocr`, then
  matches completed OCR segments against current CN Story text rows, summaries,
  and option text, and matches decoded Story audio templates against each
  gameplay video's audio track. Story file titles are excluded from OCR segment
  matching so mission-title overlays do not place SNS, archive, or other story
  files by title alone.
  Audio matching uses ffmpeg to build cached mono speech-band RMS/delta
  fingerprints under `tmp/ocr/gameplay_video_ocr/audio/`. A sparse landmark
  prefilter keeps the expensive normalized correlation pass to the strongest
  candidate offsets instead of scanning every video window for every template.
  `au_music*` templates are skipped by default so gameplay BGM is treated as
  background, and accepted audio-template hits are preferred over OCR spans
  when both place the same Story key. Pass `--disable-audio-match` for an
  OCR-only run or `--audio-include-music` only when music-event matching is
  intentional. The
  matcher reads the current user-managed order in
  `webui/overrides/story_order.json`,
  uses missions marked `locked: true` as controls for an OCR threshold sweep,
  then rebuilds final observed sequences with the selected effective threshold.
  Each gameplay video's search scope includes its inferred mission plus the
  inferred missions for adjacent parts in the same video series, so a `P10`
  report can also match Story files from `P9` and `P11`.
  By default it only moves recognized Story files to the front of each mission
  order and does not infer order from numeric file indexes; pass
  `--infer-index-gaps` only when indexed gap insertion is intentional. Pass
  `--old-videos-only` to limit both OCR sampling and loaded OCR reports to the
  original gameplay BVIDs. Synthetic archive-to-map-dialog companion matches
  are disabled by default because they are not direct gameplay observations.
  The terminal output and markdown report include locked-order mismatch counts
  per mission. Each matching run refreshes both
  `reports/gameplay_video_ocr/story_order_ocr_matches.json` and `.md` with a
  shared generated timestamp. It emits
  a proposed full-list story order at
  `reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json`.
  It also writes a WebUI debug reference at
  `webui/data/story_order_ocr.json` via `build_webui_ocr_order.py`, so debug
  mode can compare the OCR order with static recovery and the current override.
  A full all-video OCR/order refresh is
  `python scripts\story_recovery\build_gameplay_video_story_order.py --run-ocr`;
  it always leaves `webui/overrides/story_order.json` untouched while refreshing
  the standalone reports and WebUI OCR reference. Users review OCR, static
  recovery, and manual evidence before saving the final active order through the
  WebUI or by editing the override. Mission locks are preserved in the proposed
  OCR output. Smoke OCR reports made with `--limit-frames` are
  ignored unless `--include-smoke` is passed. The matcher logs corpus/index
  loading, OCR report scan skip/load counts, report match order, and per-video
  OCR-segment matching progress. It ignores stale OCR reports from older filter
  versions unless `--include-stale-ocr` is passed. The wrapper intentionally
  exposes only the practical OCR controls:
  `--ocr-engine` (default `paddleocr`), `--frame-step`, `--ocr-crop`,
  `--ocr-limit`, `--ocr-limit-frames`, `--paddleocr-frame-batch-size`,
  `--easyocr-cpu`, `--disable-ocr-dictionary`, and `--force-ocr`.
- `story_recovery/build_webui_ocr_order.py`: distills
  `reports/gameplay_video_ocr/story_order_ocr_proposed_story_order.json` into
  the small WebUI-served reference `webui/data/story_order_ocr.json`. Run it
  directly when the proposed OCR order already exists and only the debug compare
  reference needs to be refreshed.
- `story_recovery/show_gameplay_video_order_comparison.py`: focused review
  helper for selected OCR reports. It defaults to current P10 OCR outputs,
  reruns the text-only Story matcher for those reports, and writes a
  side-by-side comparison of matched mission order against
  `webui/overrides/story_order.json` to
  `reports/gameplay_video_ocr/p10_story_order_comparison.json` / `.md`.
  Pass `--include-stale-ocr` to include older P10 reports that the current
  matcher normally skips.
- `story_recovery/build_levelscript_opcode_shape_audit.py`: scans all
  decoded `LevelScriptData` action records and groups opcode/kind pairs by
  payload shape, actionMap role, strings, property keys, trigger slots,
  compact script pointers, decoded compact gate/terminal local refs, and
  ManualStart-like `levelId+scriptId` payloads.
  It writes `reports/mission_order/levelscript_opcode_shape_audit.json` /
  `.md` and is the first stop before naming new setter/start opcodes. It
  reports serialized-map membership separately for `actionList`, `getterList`,
  and `headerList`, with only residual UID records treated as outside the
  serialized map.
- `story_recovery/build_levelscript_action_map_list_audit.py`: audits the
  three physical `ActionSerializedMap` UID-list blocks against GameAssembly
  setter dispatch, MetadataRegistration type resolution, and observed opcode
  content. It writes
  `reports/mission_order/levelscript_action_map_list_audit.json` / `.md` and
  documents omitted-getter/header-only two-block cases; current recovery moves
  derived `ScriptEventHeader`-band rows into `headerList` rather than
  `getterList`.
- `story_recovery/build_levelscript_manual_control_audit.py`: follows the
  current-build ActionBase manual control records (`0x0308/0x0a`
  `ManualStartLevelScript`, `0x0302/0x0a` `ManualEndLevelScript`), checks for
  literal target operands, and records the common adjacent trigger-event
  pattern. It writes
  `reports/mission_order/levelscript_manual_control_audit.json` / `.md`;
  current recovery finds `150` manual control rows and `140` exact
  ActionHeader `_nextID` event-to-control pairs. Only `4` rows carry literal
  script-id operands, all self-targets, so there are `0` literal cross-script
  targets.
- `story_recovery/build_native_receiver_activation_frontier.py`: collapses the
  Mission Pipeline's exact unresolved runtime receivers to their hosting
  LevelScripts, decodes each top-level start policy and validated LevelData
  member-22 container, and intersects them with literal manual-control targets,
  typed MissionRuntime objective operands, original-data SubGame
  `bindScriptId` rows, and exact `DungeonTable.sceneId` hosts. It writes
  `reports/story/recovery/native_receiver_activation_frontier.json` / `.md`;
  the normal Mission Pipeline builder also refreshes this report and publishes
  compact fail-closed annotations on all receiver nodes for the debug UI.
  Current recovery covers `161` receiver nodes / `185` Story placements on
  `95` scripts and `155` Story keys: `10` have an exact SubGame activation
  scope, `55` are Manual with no decoded static shape/task/parent carrier, and
  none has an incoming literal cross-script manual-control row. One receiver
  script is read by a typed MissionRuntime objective. The compact debug
  annotation publishes its exact mission, quest, objective index, and
  condition types with explicit false ownership, activation, and Story-playback
  flags. That condition observes its `isFinished` property and does not
  activate or own its playback.
  All `12`
  non-SubGame scripts with non-empty authored start shapes have zero complete
  exact shape matches in the same-level MissionArea table. Of `25` receiver
  scripts with task maps, all `25` now decode completely as `32` tasks and
  `55` conditions across `11` concrete root `GameCondition` types. None is
  `CheckMissionState`; the exact entity, spawner, dialog, area, property,
  stage, monster, and combine operands are published as dependency/completion
  evidence, not activation or ownership. A complete typed operand pass resolves
  `46` conditions to `53` exact authored sources: `26` current-script entity
  slots, `15` WorldEntity logic ids, `5` same-level LevelScripts, `3`
  same-receiver Story keys, `3` same-level MissionArea rows, and `1`
  same-level SpawnerConfig. Exact MissionRuntime indexes for those operand
  families find `0` typed consumers, so the source annotations add no owner.
  The report also indexes exact
  `CheckLevelScriptTaskFinished(scene, script, task)` consumers. The current
  MissionRuntime corpus has two such conditions globally, but neither matches
  any of the `32` receiver tasks, so the report publishes `0` typed task
  consumers. It also finds `18` receiver scripts and `14` Story keys
  on `6` exact Dungeon/SubGame scenes, producing `40` scene-context
  placements (`7` bound-script and `33` sibling-script placements) and `31`
  availability-prerequisite annotations. Same-scene placement is loading
  context only. In particular, `dung02_bdg002/41100000004` plays
  `cutscene_e9m3_2` while its first boss-rush SubGame is unlocked by
  `e9m4_q#1`, proving that a scene's unlock identity cannot be promoted to
  Story ownership or activation. Nine receiver scripts / ten Story keys also
  share a scene with a typed `DungeonSubGameData.dungeonMissionId`. All nine
  are sibling scripts, not the mission shell's bound script. The mismatches
  `c6m3` shell vs. `c6m1` Story and `c13m2d5` shell vs. `c13m2` Story prove
  that this mission id is non-owning scene/runtime context rather than a
  playback attachment.
  The v8 nominal-host comparison now checks every filename/index-derived
  mission candidate against the complete same-level mission-named LevelData
  dictionary. It finds `49` receiver scripts whose candidate mission host is
  present and validated but excludes that receiver. For the five unresolved
  exact-playback black keys, three are on excluded generic hosts
  (`black_e9m2_1`, `black_sm2l6m1_4`, and `black_e11m1_2`); the other two
  (`black_a1m6d3_1` and `black_a1m6d4_1`) have exact
  `activity_qingxi_qiangti_3/_4` SubGame bind carriers and no same-level
  nominal-mission host. This closes the current static nominal-owner route for
  all five without turning filename identity into ownership evidence.
  Exact level/script/task joins add
  display/tracking metadata for `13` tasks and SubGame main-task bindings for
  `10`; all ten SubGame rows have null `dungeonMissionId`. The `82` distinct
  task/condition ids have zero MissionRuntimeAsset occurrence. Only the already
  SubGame-scoped
  `map02_lv002/22800950006` contains exact serialized MissionRuntime-id string
  tokens (`a1m6d6`, `a1m6d7`); all `85` non-SubGame receiver scripts contain
  none. These
  classifications narrow the producer queue and create no mission, quest,
  playback, or order edge.
- `story_recovery/build_levelscript_property_setter_candidate_audit.py`:
  follows the MissionRuntime property-check bridges into the target
  `LevelScriptData` files, keeps exact key-bearing UID records separate from
  offset-only/top-level property data, and ranks local setter/gate/listener
  opcode candidates by chain position and decoded payload hints. It writes
  `reports/mission_order/levelscript_property_setter_candidates_<LANG>.json`
  / `.md`; the output is diagnostic and not direct order-promotion evidence.
- `story_recovery/build_levelscript_gate_audit.py`: follows `0x0a03/0x00`
  compact condition/gate records. The shared binary decoder now exposes the
  stable shape as a property key, type code, post-key flag, and optional tail
  local action ref. The audit walks that local ref separately from ordinary
  `nextId`, then cross-checks MissionRuntime property bridges. It writes
  `reports/mission_order/levelscript_gate_audit_<LANG>.json` / `.md`;
  current CN recovery finds `219` gate rows, `171` decoded property-key rows,
  `41` rows with tail local refs, and `10` MissionRuntime-bridged rows.
- `story_recovery/build_levelscript_terminal_branch_audit.py`: follows
  `0x0bed/0x00` terminal-branch records through their decoded tail local-id
  refs, then walks `nextId`, split-list refs, and nested terminal refs to
  expose the story/play records reachable after a compact property terminal.
  It writes
  `reports/mission_order/levelscript_terminal_branch_audit_<LANG>.json` /
  `.md`; current CN recovery finds `1,529` terminal rows, `6` MissionRuntime
  property-bridged rows, `156` rows with story-key targets, and `154` rows
  with play-action targets.
- `story_recovery/build_levelscript_setter_overlap_audit.py`: compares
  MissionRuntime `CheckLevelScriptProperty*` triples against named ActionBase
  setters (`0x03da/0x0a` `SetBool`, `0x0410/0x0a` `SetInt`,
  `0x0413/0x0a` `SetIntIncrease`). It writes
  `reports/mission_order/levelscript_setter_overlap_<LANG>.json` / `.md`;
  current CN recovery finds `1,725` decoded setter-key rows but `0` exact
  `(mapId, scriptId, key)` matches to MissionRuntime property checks.
- `story_recovery/build_levelscript_action_metadata_audit.py`: extracts a
  focused IL2CPP metadata view for LevelScript action/event classes, including
  ManualStart/ManualEnd, property getter, property-change listener, and
  trigger-volume event shapes, plus the generic `Set<T>` / `SetList<T>` and
  ParamBlackboard/ParamVariable property-storage surfaces. It also retains the
  `Branch` runtime `_idList`/`m_index` shape and its MemoryPack `_idList`
  setter, and keeps the `ActionMapAssetRaw -> ActionSerializedMap` layer
  visible. Runtime fields are
  `headerList`, `actionList`, and `getterList`; the body audit shows setter
  dispatch in `actionList`, `getterList`, `headerList` order, and the list
  audit checks that against binary content signatures. This is the current
  best lead for unnamed compact records such as `0x0a03/0x00` and
  `0x0bed/0x00`. It writes
  `reports/mission_order/levelscript_action_runtime_metadata.json` / `.md`
  and is used to reject property-key records that only match read/gate/listener
  families while keeping the generic setter family visible.
- `story_recovery/build_levelscript_action_map_type_audit.py`: resolves the
  ActionSerializedMap and ActionMapRuntime type indexes that the metadata-only
  catalog leaves as `<type-index:N>`. It reads GameAssembly
  `Il2CppMetadataRegistration` and writes
  `reports/mission_order/levelscript_action_map_type_indices.json` / `.md`;
  current recovery resolves `actionList` to `List<ActionBase>`, `getterList`
  to `List<PureGetter>`, `headerList` to `List<ActionHeader>`, and the runtime
  arrays to `ActionBase[]`, `PureGetter[]`, and `ActionHeader[]`.
- `story_recovery/build_levelscript_action_body_audit.py`: maps the focused
  LevelScript action/runtime metadata targets to `GameAssembly.dll` and writes
  a compact body report at
  `reports/mission_order/levelscript_action_body_targets_gameassembly.json`
  / `.md`. It confirms manual start/end calls, property getter reads,
  property-change listener registration, and the runtime
  `UpdateRuntimeState -> ModuleResetUpdateProperty` path. It also checks the
  generic setter follow-up: concrete MemoryPack wrappers deserialize
  `set____key__` before `set____value__`, and their generic wrapper setters
  store key/value at the real instance offsets `+0xd0`/`+0xd8`. It also maps
  `ActionSerializedMapForMemoryPack.Deserialize`, confirming calls to
  `set___actionList__`, `set___getterList__`, and `set___headerList__` in
  that order; the setters write ActionSerializedMap fields at `+0x18`,
  `+0x20`, and `+0x10`. It also tracks `ActionHeaderForMemoryPack` setter
  bodies, including `set____nextID__` at runtime field `+0x60`, which backs
  the compact payload `ActionHeader.nextId` decode used by the header-chain
  audit. The focused body report also maps `Branch.Execute`: `_idList` is at
  `+0xd0`, `m_index` at `+0xd8`, and resolved calls to
  `SetResultReservedID`/`SetResultNextID` prove sequential continuation.
  Use the ActionBase formatter tag audit below for the opcode-to-class bridge.
- `story_recovery/build_levelscript_actionbase_tag_audit.py`: extracts the
  generated `ActionBaseForMemoryPackFormatter..cctor` union tag table from
  `GameAssembly.dll`, also checks the tiny `FinalActionBase` formatter, and
  decodes runtime-metadata type slots back through `global-metadata.dat`. It writes
  `reports/mission_order/levelscript_actionbase_formatter_tags.json` / `.md`
  and cross-references `levelscript_opcode_shape_audit`: current recovery finds
  1,313 contiguous ActionBase tags `0x0000..0x0520` from the installed
  CodeRegistration `0x18b9217d0`. Common playback records include
  `0x0363/0x0d` `PlayRadio`, `0x0364/0x0d` `PlayRadioAndWait`,
  `0x0357/0x14` `PlayCutsceneAction`, and `0x049e/0x0f`
  `StartDialogAction`. Manual control opcodes are `0x0308/0x0a`
  `ManualStartLevelScript` and `0x0302/0x0a` `ManualEndLevelScript`; setter
  examples are `0x03da/0x0a` `SetBool`, `0x0410/0x0a` `SetInt`, and
  `0x0413/0x0a` `SetIntIncrease`. Compact-u8 records must first be normalized
  from the legacy combined `(memberCount << 8) | tag` code: for example,
  raw `0x09b9/0x00` is tag `0x00b9` with nine members and maps exactly to
  `ExitLevelCustomPerformance`, not to an unknown high opcode. Other exact
  presentation-chain mappings include `0x04ca/0x09`
  `ToggleClearScreenButRadio`, `0x02fe/0x0a` `MainCharMoveTo`, and compact
  `0x0e34/0x00` -> tag `0x0034`/14 members `CallServer`. The current typed
  CallServer corpus serializes each hash-shaped event name as `#` plus its own
  eight-hex-digit action UID. Builders retain these as
  `levelscriptCallServerSelfUidCallback` diagnostics but exclude them from
  Story nodes, order edges, and mission ownership. The two current typed
  `PlayDialogAndHideSceneObjectAction` (`0x035a/0x0f`) punctuation-only
  payloads, `#` beside `dlg_sm2l5m1_7` and `%` beside `dlg_sm2l5m1_8`, are
  likewise retained as `levelscriptNonNodeScalarPayload` diagnostics rather
  than emitted as graph identifiers. This recognizer requires exact
  action-list membership and a co-record dialog id. The same fail-closed graph
  hygiene recognizes the four current one-character parameters beside real
  cutscene ids in typed `StartCutsceneAndControlSceneObjectAction` and
  `StartCutsceneAndHideSceneObjectAction` records. It retains `P`, `Y`, `e`,
  and `A` as non-node diagnostics and emits no graph edge for them. Remaining
  generic-symbol edges retain their weak topology. Physical
  `ActionSerializedMap` membership—not overlapping union tags—controls their
  annotations: action-list boundaries carry exact formatter-derived
  `sourceActions`, while header-list boundaries carry `sourceEvents`, for
  WebUI debug chips/tooltips. The localized build joins these fields onto the
  exact matching `timelineRecovery.sourceBackedSceneEdges` copy by
  source/target/kind. Knowing that a symbol belongs to camera, audio, guide,
  level-sequence, or custom-event action context does not promote order or
  mission ownership. High
  event/gate/terminal records such as `0x0a03/0x00`, `0x0bed/0x00`, current
  trigger events `0x12be/0x00` and `0x12c0/0x00`, dialog exit
  `0x1355/0x00`, and quest-state change `0x1385/0x00` are outside that
  ActionBase tag range.
- `story_recovery/build_memorypack_union_tag_audit.py`: scans all generated
  MemoryPack formatter `.cctor` union registrations and writes
  `reports/story/recovery/memorypack_union_formatter_tag_audit.json` / `.md`.
  The current installed audit reaches raw ActionBase union tag `0x0520` and
  fully recovers the exact `ActionHeader` formatter table as 230 contiguous
  tags `0x0000..0x00e5`. The root `Beyond.Gameplay.GameCondition` formatter
  has 308 registrations; use `--full-tag-limit 400` when its complete tag rows
  are required, and do not mix its tag meanings with the overlapping
  `GameConditionServer` or `GameConditionClient` tables. Story consumers use
  the complete header table only for
  proved `headerList` records because the ActionBase/PureGetter/Header tag
  spaces overlap. The x64 helper preserves successfully decoded registrations
  when the final cctor instruction is a bounded/truncated tail, so the complete
  table no longer depends on shortening the scan by one byte. `0x0a03/0x00` is
  now
  structurally decoded as a compact condition/gate record with a type code,
  post flag, and optional tail local action ref; `0x0bed/0x00` is now decoded
  as a compact terminal branch carrier with local action refs, though both
  runtime class families are still unnamed.
- `story_recovery/build_selector_formatter_tag_audit.py`: extracts selector
  Finder/Validator/PostProcessor MemoryPack formatter evidence from
  `GameAssembly.dll`. It writes
  `reports/mission_order/selector_formatter_tag_audit.json` / `.md`; current
  recovery resolves Finder tags `0x0000..0x0013`, Validator tags
  `0x0000..0x000a`, and PostProcessor tags `0x0000..0x0008` to concrete
  selector formatter names.
- `story_recovery/build_selector_targetsettings_body_audit.py`: regenerates the
  focused selector/TargetSettings IL2CPP metadata catalog, maps it to
  `GameAssembly.dll`, preserves the raw body report, and writes
  `reports/mission_order/selector_targetsettings_chain_summary.json` / `.md`.
  The compact summary records FindTargetAction/SelectorData/TargetSettings
  setter call order, setter store offsets, aliasing warnings, selector tag-map
  evidence, and the current "parser still missing" gate before FindTargetAction
  chain consumption can be enabled.
- `story_recovery/build_findtarget_selector_boundary_audit.py`: scans exported
  BuffData through the existing WebUI data decoder and writes
  `reports/mission_order/findtarget_selector_boundary_audit.json` / `.md`. It
  groups real FindTargetAction body-middle byte shapes, checks whether the
  current TargetSettings envelope parser accepts any middle-byte candidates,
  stores complete body-middle hex for parser replay in JSON, lists ambiguous
  first-FindTarget records, and keeps selector tag byte hits as non-proof
  prioritization hints.
- `story_recovery/build_findtarget_selector_replay_audit.py`: replays the saved
  FindTargetAction body-middle byte shapes against the current TargetSettings
  envelope helper and selector formatter tag maps. It writes
  `reports/mission_order/findtarget_selector_replay_audit.json` / `.md`, keeps
  selector matches as tag-only hints, consumes only locally proven empty-payload
  selector prefixes, and reports exact boundary proof and chain-safe FindTarget
  counters separately from noisy union-tag candidates.
- `story_recovery/build_findtarget_selector_payload_priority_audit.py`: ranks
  nonzero FindTarget selector tag hints and actual `0x0000` selector formatter
  tags against MemoryPack metadata setter complexity. It writes
  `reports/mission_order/findtarget_selector_payload_priority_audit.json` /
  `.md` and identifies empty-payload selector targets for bounded byte-probe
  follow-up work.
- `story_recovery/build_lua_consumer_reference_audit.py`: scans extracted Lua
  roots and writes `reports/mission_order/lua_consumer_reference_audit.json` /
  `.md`. It deduplicates Persistent/StreamingAssets modules by relative Lua
  path, extracts `Tables.*`, `GEnums.*`, `CS.Beyond.*`, `contentParam`,
  dialog/RemoteComm ids, sprite/video/audio helper references, checks
  `Tables.*` names against exported Table JSON roots, emits graph-ready
  Lua module-to-table edge candidates, and summarizes focus areas such as
  SNS, RemoteComm, Dialog, map marks, and mission UI. It also enumerates every
  direct `GameAction.*` call, classifies the bounded Story-playback API set,
  resolves only direct or simple string-constant first arguments, validates
  exact registry casing, and reports nearby table names as triage rather than
  data-flow proof. Table-fed ids, handles, concatenation, and parameters remain
  unresolved instead of being guessed.
- `story_recovery/build_cutscene_case_resolution_audit.py`: follows the exact
  current-build `GameAction.PlayCutsceneAndGetHandle -> CutsceneManager ->
  GetGenderedCutsceneId -> TryGetCinematicData -> CachedPathAssetLoader ->
  StringPathHash` chain for the Lua literal `Cutscene_e0m0_1`. It validates the
  Lua and IFix audits, maps null open-generic slots through concrete IL2CPP
  MethodSpecs, and writes
  `reports/story/recovery/cutscene_case_resolution_audit.{json,md}`. The current
  result proves case-sensitive resource lookup and permanently rejects that
  spelling as playback evidence for lowercase `cutscene_e0m0_1` on the reviewed
  build. Binary, metadata, or IFix fingerprint drift fails closed.
- `story_recovery/build_string_path_hash_story_audit.py`: validates the skipped
  main `StringPathHash.bin` and initial `InitStringPathHash.bin` registries
  with the same layout: an 8-byte bucket table, a
  `hash:int64 + stringPoolOffset:uint64` entry table, and a length-prefixed
  UTF-16 path pool. It reports target paths by registry, recovers every
  resource path/hash containing the three unresolved CutsceneRoot selector
  keys, then searches the complete structured export, both AnimeStudio object
  indexes, an optional adjacent `CompressData.bin` dump, and the current
  `GameAssembly.dll` for exact binary/text consumers. Repeat
  `--native-binary PATH` to replace the default native-binary input. It writes
  `reports/story/recovery/string_path_hash_story_audit.{json,md}` and treats
  hash registration as resource availability only: the reverse lookup does not
  prove playback, chronology, or mission/quest ownership. The normal WebUI
  export intentionally skips ExtendData, so prepare the bounded offline inputs
  first:

  ```bat
  call endfield_paths.bat
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --streaming-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\root_selector_string_path_hash --block-type initial-extend-data --block-type extend-data --file-regex "(?i)StringPathHash"
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --streaming-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\root_selector_compress_data --block-type initial-extend-data --block-type extend-data --file-regex "(?i)CompressData"
  python scripts\story_recovery\build_string_path_hash_story_audit.py
  ```

  The current 7.24 GB structured/object census plus the 280 MB native scan
  takes about nine minutes on this checkout and is not part of `export.bat`.
- `story_recovery/build_world_streaming_story_selector_audit.py`: closes the
  skipped binary-scene variant for the three unresolved CutsceneRoot selectors.
  It first validates both complete AnimeStudio object-index publications and
  searches resolved script/type identities plus distinctive nested
  Encounter/BattlerStage fields. It then uses AnimeStudio `stream` to scan the
  current `Streaming` and `DynamicStreaming` VFS blocks in place, including the
  effective Persistent overlay with StreamingAssets fallback. Exact patterns
  cover each root and all 34 registered resource paths as UTF-8/ASCII and
  UTF-16LE, plus both byte orders of every registered `StringPathHash`.
  Results and corpus fingerprints go to
  `reports/story/recovery/world_streaming_story_selector_audit.{json,md}`:

  ```bat
  python scripts\story_recovery\build_world_streaming_story_selector_audit.py
  ```

  This standalone audit takes about four minutes on the current checkout and
  is not part of `export.bat`. A zero result closes exact selectors only; it
  does not rule out transformed nested identities, runtime/server construction,
  or future data, and never creates ownership or order from world-file
  co-location.
- `story_recovery/build_dynamic_scene_mission_control_audit.py`: streams the
  current effective `DynamicStreaming` `fb_main` files and decodes the typed
  `RootComp -> IdComp / MissionControlComp -> MissionCondition` spine. It joins
  an exact numeric `IdComp.logicId` to exported LevelScript file ids and lists
  matching Story playback occurrences, but classifies the result as a
  cross-system candidate rather than a runtime owner: native DynamicScene and
  LevelScript lookups use separate registries, and no direct bridge has been
  recovered. Results go to
  `reports/story/recovery/dynamic_scene_mission_control_audit.{json,md}`:

  ```bat
  python scripts\story_recovery\build_dynamic_scene_mission_control_audit.py
  ```

  The audit is deliberately standalone and never adds mission ownership or
  Story order. Use `--input` only to replay a prepared AnimeStudio stream
  JSONL; the default reads the installed Persistent overlay with
  StreamingAssets fallback. It also fingerprints current IL2CPP metadata and
  closes the adjacent `FBDynamicSceneScriptControlComp` lead: that struct has
  only `DefaultLoad:int32`, and zero current mission-controlled root co-carries
  it.
- `story_recovery/build_dynamic_scene_levelscript_action_bridge_audit.py`:
  follows the identity candidates into current effective LevelScripts and
  admits only fully consumed constant `ShowSceneDecorationNew` /
  `ShowSceneDecorationWithHandle` action rows. The typed
  `DynamicSceneEntityPtr` target is a direct LevelScript-to-DynamicScene
  identity edge; the audit also compares the exact serialized header/action
  paths for the target action and Story playback. Results go to
  `reports/story/recovery/dynamic_scene_levelscript_action_bridge_audit.{json,md}`:

  ```bat
  python scripts\story_recovery\build_dynamic_scene_levelscript_action_bridge_audit.py
  ```

  The current build has one exact self-target bridge:
  `map02_lv001/10100282001` runs `dlg_c27m3_6` and then
  `ShowSceneDecorationNew(10100282001, false)` on the same
  `ScriptEvent_OnLeaderEnterTriggerVolume` slot-80001 chain. This proves shared
  local LevelScript control context, not that the DynamicScene mission
  condition starts that trigger header. The audit therefore keeps
  `missionGraphAction=none`. The follow-up component census also closes the
  tempting slot bridge: all 387 mission-controlled roots carry only IdComp,
  MissionControlComp, ResourceComp, and BlightMiasmaComp, with zero
  TriggerComp. The TriggerComp schema contains geometry and a position-list
  group but no trigger-slot or LevelScript identity. The audit also resolves
  the event's slot `80001` to the owning LevelScript's exact embedded Leader
  trigger-volume row. Its fully decoded eight-member schema contains only
  local flags, slot/count, exit index, and shape geometry; current metadata
  gives the Leader subtype zero additional fields. With no DynamicScene,
  mission, quest, or foreign entity identity, this route remains
  `missionGraphAction=none` and coordinate proximity is not promoted.
- `story_recovery/build_compress_data_story_audit.py`: replaces the raw-byte
  `CompressData.bin` probe with a full logical decode. It hash-gates the current
  `DataCompressManager` native mapping, validates the count/absolute-offset
  table and each
  `compressedLength + originalLength + Brotli payload` record, parses every
  result as UTF-16LE NodeCanvas JSON, and joins all pool indexes back to exact
  typed BehaviourTree assets through `_enableGraphStringCompress` and
  `_serializedGraphStringIndex`. It writes
  `reports/story/recovery/compress_data_story_audit.{json,md}`. This standalone
  audit requires the Python `brotli` module; normal export/build tooling remains
  stdlib-only. After preparing `CompressData.bin` with the targeted dump above,
  run:

  ```bat
  python scripts\story_recovery\build_compress_data_story_audit.py
  ```

  Shared indexes are valid deduplication, not duplicate-owner evidence. The
  audit fails closed on missing pool indexes, malformed records, decode/length
  mismatch, non-BehaviourTree logical roots, incomplete typed objects, or
  native binary/metadata hash drift.
- `story_recovery/build_facbone_trs_story_audit.py`: validates the final
  current ExtendData-family file as a serialized unit-guid hash table followed
  by bone-name-hash records and contiguous 64-byte frame matrices. It
  hash-gates the file plus current `GameAssembly.dll`/metadata, validates every
  bucket and the gap-free unit/bone/matrix partitions, and records the native
  `FacBoneTRSBinary.TryGetBoneTRS` and `STATICVATDATA.GetBoneTRS` reader path.
  The report at
  `reports/story/recovery/facbone_trs_story_audit.{json,md}` closes the file as
  factory VAT animation data with no mission-graph action. Prepare and run the
  bounded audit with:

  ```bat
  call endfield_paths.bat
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --streaming-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\extend_data_inventory\current.json --block-type initial-extend-data --block-type extend-data
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --streaming-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\facbone_trs --block-type extend-data --file-regex "(?i)FacBoneTRS\.bin$"
  python scripts\story_recovery\build_facbone_trs_story_audit.py
  ```

- `story_recovery/build_bundle_manifest_story_audit.py`: inventories both
  installed BundleManifest copies, selects the newer effective Persistent
  version, Brotli-decompresses `manifest.hgmmap`, and validates its magic/build
  strings, asset and bundle hash-table partitions, equal-count bundle array,
  and framed shared data pool. The native schema restricts its records to
  asset-path routing and bundle dependency metadata, so the report at
  `reports/story/recovery/bundle_manifest_story_audit.{json,md}` treats bundle
  membership as resource availability rather than Story ownership. This
  standalone audit requires Python `brotli`. Prepare the bounded inputs with:

  ```bat
  call endfield_paths.bat
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --streaming-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\bundle_manifest_probe\streaming.json --block-type bundle-manifest
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe vfs-index --streaming-assets "%ENDFIELD_GAME_ROOT%\Persistent" --fallback-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\bundle_manifest_probe\persistent.json --block-type bundle-manifest
  tools\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe dump --streaming-assets "%ENDFIELD_GAME_ROOT%\Persistent" --fallback-assets "%ENDFIELD_GAME_ROOT%\StreamingAssets" --output tmp\story\bundle_manifest_probe\persistent_dump --block-type bundle-manifest
  python scripts\story_recovery\build_bundle_manifest_story_audit.py
  ```

- `story_recovery/build_skipped_vfs_block_audit.py`: summarizes an
  AnimeStudio/fluffy-dumper `vfs-index` JSON for WebUI-skipped VFS blocks such
  as Lua, ExtendData, Streaming, DynamicStreaming, and BundleManifest. It
  writes `reports/mission_order/skipped_vfs_block_audit.json` / `.md` with
  counts, sizes, top directories, largest files, and story/SNS/UI signal
  samples so broad raw dumps can be prioritized.
- `story_recovery/build_hotfix_audio_event_audit.py`: streams
  `hotfix-audio` PCK payloads directly from VFS, parses embedded Wwise bank
  HIRC metadata, and writes
  `reports/mission_order/hotfix_audio_event_audit.json` / `.md` with
  HotfixAudio media ids mapped to event hashes and any known event names.
- `story_recovery/build_levelscript_header_chain_audit.py`: uses the compact
  `ActionHeader.nextId` payload field on `headerList` rows to walk from
  event/listener records into `actionList` chains. It writes
  `reports/mission_order/levelscript_header_chain_audit.json` / `.md`. The
  report overlays the complete current-build ActionHeader formatter identities
  from the Story-recovery audit instead of reviving the disproven historical
  high-code `base + tag` inference. Header names are applied only after
  `headerList` membership is proved.
  Story builder also decodes the current-build `0x1355/0x00`
  `LevelEvent_OnDialogExit` opcode (historical exports used `0x1250/0x00`):
  when the header names exactly one Story scene and each linked action record
  resolves to at most one Story scene, it emits the action-chain sequence as
  strong `levelscriptDialogExit` partial-order edges with file, level, script,
  local-id, and chain-position provenance. Ambiguous and self-only chains are
  retained by the audit but not promoted.
- `story_recovery/build_option_playable_semantics_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded
  `DialogOptionPlayableAsset` fields such as `logicId`, `trunkId`,
  `dialogId`, `conditionRid`, `changeFinishNum`, and `targetFinishNum`. Use
  `--only-interesting` to focus on groups where `logicId` is the only
  non-default semantic clue, or `--story <key> --group <n>` for a targeted
  scene check.
- `story_recovery/build_option_logic_id_audit.py`: follows up on the `logicId` queue by
  scanning structured tables, `MissionRuntimeAsset`, `LevelScriptData`,
  `LevelScriptTemplateData`, gameplay config, and Lua consumer terms for exact
  references to option `logicId` values. Same-mission mission/level-script
  matches would be high-value evidence; table/config-only matches are
  diagnostic unless another source links them to the dialog.
- `story_recovery/build_dialog_tree_option_route_audit.py`: audits remaining
  `inferredOptionResponse` groups against decoded AnimeStudio DialogTree
  routes, related scene links, target fragments, and cinematic wrappers. Use it
  after the option-playable and `logicId` audits to separate cases where
  the Story builder could promote authored tree evidence from the larger queue
  that needs deeper Timeline/runtime option-target decoding.
- `story_recovery/build_timeline_option_flow_audit.py`: audits remaining
  `inferredOptionResponse` groups against raw Timeline trunk clips. It reports
  whether candidate response clips carry useful non-default `optionIndex`
  values, resolves `misc_dlg_*` WebUI aliases to underlying `dlg_*` Timeline
  entries, and separates promotable `trunkClipOptionIndexRoute` cases from
  default `optionIndex=0` adjacent layouts. Current native control flow proves
  zero-index trunk clips are shared continuation unless an overlapping raw
  Runtime Jump window supplies option-indexed route evidence.
- `story_recovery/build_timeline_binding_audit.py`: checks whether unresolved
  option responses separate cleanly by Timeline track, track binding, actor
  binding, or option-clip placement.
- `scene_order_gap_shared.py`: classifies each scene's line-order and
  option-layout recovery quality. Consumes the DialogIdTable registry above
  to upgrade `lineIdSuffix`-mode scenes to one of:
  - `unregisteredScene`: sceneKey is absent from `DialogIdTable`, so the
    runtime cannot load this scene at all (cut/dead content; the only order
    that exists is `DialogTextTable` layout).
  - `dialogTrunkRowIteration`: sceneKey IS registered but no Timeline or
    dialogTree source matched; `DialogTrunkBehaviour` would iterate
    `DialogTextTable` rows by sceneKey prefix, which produces the same
    sequence we already emit.
  Option-key suffix and sparse line-gap placements on unregistered scenes are
  surfaced separately as table-only display recovery; they are not treated as
  recoverable live-runtime option positions.
- `story_recovery/annotate_conv_with_registry.py`: standalone refresher for stamping each
  dialog conv JSON's `_debug` block with a `runtimeRegistry` evidence record
  (registered-root flag and option-id vocabulary from `DialogIdTable`; the
  current table has no per-trunk line tokens).
  The Story builder does this during normal exports; the refresher is useful
  when updating existing conv files without a full rebuild. Pure evidence
  surfacing; no inference.
- `story_recovery/rewrite_scene_order_warnings.py`: one-shot warning rebuild for conv
  JSONs without re-running the Story builder. Useful after tightening
  `scene_order_gap_shared.py` criteria.

### IL2CPP-derived evidence (out-of-band)

The C# class hierarchy backing the recovery modes was confirmed by scanning
`global-metadata.dat` from the game's IL2CPP runtime. The maintained helpers
under `tools/endfield-il2cpp/` validate/cache the metadata artifact, catalog
option-flow fields and method targets, and map focused body targets to
`GameAssembly.dll` addresses. They write drift/evidence reports outside the
normal WebUI build.
Relevant runtime types:

- `Beyond.Gameplay.Core.DialogManager` (partial across `.DialogTree.cs`,
  `.Level.cs`, `.LifeCycle.cs`, `.Timeline.cs`) -- routes every dialog load
- `Beyond.Gameplay.Core.DialogTrunkBehaviour` -- per-trunk playback driver
- `Beyond.Gameplay.Core.DialogTimelineManager` -- Timeline-driven path
- `Beyond.Gameplay.Core.DialogTreeController` -- tree/branch navigation
- `Beyond.Gameplay.Core.DialogOptionBehaviour` -- option/choice nodes
- `Beyond.Gameplay.DialogIdTable` -- runtime dialog registry (extracted by
  `story_builder/dialog_registry.py`)

There is **no** separate document / letter / memo / consent-form UI loader
class anywhere in the runtime. Every dialog scene -- including the "letter"
and "consent form" content -- goes through `DialogTrunkBehaviour
._TryInitDialogText`, with `DialogTimelineManager` and `DialogTreeController`
overlaid when applicable.

## Archived

The old archived-script bucket has been retired. UE5 pose-demo helpers live
with the UE project under `../ue5_zhuangfy_pose_demo 5.3/Scripts/`.
Put new experiments in `../scratch/<topic>/<task>/` and disposable runs in
`../tmp/<topic>/<task-or-run>/`. Move observations or conclusions to
`../memory/` when they need to be kept, and keep both work-directory roots
free of loose entries.
