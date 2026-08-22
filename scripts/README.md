# Scripts

This directory contains the maintained exporters and builders for the static
WebUI. Use the root wrappers for normal work; call Python entry points only for
focused development or validation.

## Root workflows

| Goal | Command |
| --- | --- |
| First-time Story/Text setup | `.\setup_first_time.bat` |
| Rebuild from the current export | `.\export.bat` |
| Refresh Story from the game | `.\export.bat --from-game` |
| Refresh Story and assets together | `.\export.bat --from-game --with-assets` |
| Story/Mission recovery loop | `.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference` |
| Mission Pipeline JSON only | `.\export.bat --mission-pipeline-data-only` |
| Reindex assets and CN audio | `.\export_assets.bat` |
| Refresh assets and CN audio | `.\export_assets.bat --from-game` |
| Compare exports for Updates | `.\build_updates.bat OLD NEW` |
| Serve or package | `python serve.py` / `python scripts\pack_webui.py` |

The wrappers load `endfield_paths.bat`, then apply explicit path flags. Run any
wrapper with `--help` for its supported options.

## Export rules

`export.bat` is the canonical Story, Text, Characters, Gameplay, and generated
WebUI rebuild. It reads the current `export_full/` by default and runs
`verify_export_freshness.py` before downstream builders. Use `--from-game` only
when the extraction must be refreshed from the installed client.

Useful shared flags:

- `--with-assets` adds asset indexes and CN audio relinking.
- `--focused-assets`, `--default-assets`, and `--debug-assets` select asset
  scope from narrowest to broadest.
- `--asset-jobs N` caps AnimeStudio workers; `--webui-jobs N` caps independent
  post-Story builders.
- `--game-root PATH` overrides the configured client for one run.
- `--story-only`, `--mission-pipeline-only`, and
  `--mission-pipeline-data-only` stop after their named scope.
- `--full-source-graph` adds exhaustive Unity-object/PathID graph work. The
  default graph contains only source rows consumed by WebUI edges.

Installed-game-only flags fail with an explanation when `--from-game` is
absent. Keep wrapper files CRLF; LF-only batch files can break backward `goto`
argument loops under `cmd.exe`.

Every export records build-step timings and a process-tree benchmark under
`reports/export/`. The Combat builder rejects stale graph inputs and publishes
a degraded reason instead of using them as direct evidence.

## Main builders

| Area | Entry point | Main output |
| --- | --- | --- |
| Extraction | `export_full_from_game.py` | `export_full/` |
| Export freshness | `verify_export_freshness.py` | validation result |
| WebUI orchestration | `build_webui_views.py` | semantic page data |
| Story evidence | `story_builder/refresh_evidence.py` | `reports/story/` evidence |
| Story links | `story_builder/source_links.py` | localized reference data |
| Story | `story_builder/build.py` | `webui/data/lang/<LANG>/` |
| Mission Pipeline | `build_mission_pipeline_data.py` | `webui/data/mission_pipeline/` |
| Lua consumer index | `story_builder/lua_consumer_references.py` | fingerprinted Mission Pipeline evidence |
| Characters | `build_character_data.py` | character indexes |
| Gameplay | `build_gameplay.py` | Gameplay datasets |
| Assets | `build_assets.py` | asset indexes and media lookup |
| Audio | `build_audio.py` | decoded/relinked audio data |
| Audio semantics | `build_audio_semantics.py` | compact Audio page evidence and shards |
| Updates | `build_updates.py` | `webui/data/updates/latest.json` |
| Packaging | `pack_webui.py` | distributable static package |

`build_gameplay.py` owns every Gameplay dataset. Behavior-focused stages live
in `gameplay_builder/`; its `asset-refs` stage calls the public
`asset_builder.gameplay_refs` API with the current Gameplay and Assets indexes
and is the sole writer of `webui/data/assets/gameplay_refs.json`.
The base stage also resolves every BuffData id referenced by active Gameplay
rows into a compact, fail-closed lifecycle/stacking/value catalog. Native enemy
modifier, ability-event, skill-type, and cooldown-operation enum names are
emitted only after the selected GameAssembly/metadata pair passes the
installed-native gate. Non-empty Buff action chains use the current formatter's
union ids/member counts and publish only chains whose typed actions consume to
the exact next field boundary. The base stage also joins the current
`GameplayTagPredefineTable.json` by signed-Int32/unsigned-hex ID, then joins
the build's serialized `GameplayTagConfig` object-index paths using the
validated CRC32(UTF-8 full path) rule. It publishes exact predefined/config
names and preserves unmapped applied tags as raw IDs. A missing immunity path
is named only when an exact `tagName2Immune` status context independently
contains the CRC32 of `Immune/<suffix>`; these rows are labeled
`exact-context-derived` and retain the proof context. The registry records the
matched config-object/path counts and marks IDs absent from that serialized
registry with a structured unresolved reason; it does not infer names from
Buff ids.
When the serialized registry is incomplete, capture the live current-build
registry before rebuilding the base stage. Start the capture first so it can
attach during client startup, then load the title/menu or a gameplay scene:

```bat
tools\frida-runtime\venv\Scripts\python.exe -m scripts.gameplay_builder.capture_runtime_tags --duration 600 --output scratch\reverse_engineering\gameplay_tag_runtime\capture.jsonl
python scripts\build_gameplay.py --stage base --languages CN --default-language CN --runtime-tag-capture scratch\reverse_engineering\gameplay_tag_runtime\capture.jsonl
```

The capture is read-only and refuses to attach unless the selected
`GameAssembly.dll` and `global-metadata.dat` match the pinned current-build
hashes. Runtime rows are merged only when that same native-input gate is
validated; otherwise the static export remains unchanged. Use `--check-only`
to verify the hook manifest without attaching.
`build_assets.py` writes only Assets-owned indexes and media lookup. The legacy
economy, world, presentation, and broad data index helpers are diagnostic only
and do not feed active pages.

Typical focused commands:

```bat
python scripts\verify_export_freshness.py
python -m scripts.story_builder.refresh_evidence
python -m scripts.story_builder.source_links
python -m scripts.story_builder.build --languages CN --default-language CN
python scripts\build_character_data.py --languages CN --default-language CN
python scripts\build_mission_pipeline_data.py
python scripts\build_gameplay.py
python scripts\build_assets.py
python scripts\build_audio.py
python scripts\build_audio.py --skip-decode --refresh-hirc
python scripts\pack_webui.py
```

Direct Story builds take several minutes. Allow at least 15 minutes for the
shell command, especially for multiple languages or forced Timeline recovery.

## Story recovery

Production parsing, validation, attachment, and generated schemas live in
`story_builder/`. Audit and candidate-generation tools live in
`story_recovery/`; they may import stable builder primitives, but production
builders must not import or execute recovery modules.

Mission Pipeline reads the canonical shipped-Lua consumer index through
`story_builder.lua_consumer_references`; it does not consume a recovery-script
artifact. Cinematic-handle classification and typed action-producer joins come
from the reviewed, installed-build-gated
`story_builder/native_contracts/cinematic_queue.json`; the full native carrier
report is not a production input. Standard WebUI extraction intentionally
omits Lua, so refresh this tracked index only from an explicit complete
plaintext-Lua extraction. To refresh it and optionally render Markdown, run:

```bat
python -m scripts.story_builder.lua_consumer_references --markdown
```

To refresh and reconcile the optional full cinematic native audit against the
compact contract, run
`python -m scripts.story_recovery.audit_native_carriers cinematic`. Use
`--skip-contract-reconciliation` only while reviewing a new installed build
before intentionally updating the versioned contract.

`story_builder/source_gap/` owns the canonical source-only Story gap queue.
Mission Pipeline refreshes it through the in-process builder API; it is not a
recovery-script subprocess.

Work in small validated batches:

1. Use focused unit tests, parser probes, or
   `--mission-pipeline-data-only` while generated Story inputs are current.
2. After at least three independent changes, or at the end of a coherent
   30–60 minute batch, run the canonical `--mission-pipeline-only` rebuild.
3. Rebuild earlier only for changed installed inputs, stale generated data, or
   a cross-cutting schema change that focused tests cannot validate.

Reuse Timeline order and localized references only when their inputs are
unchanged. `--reuse-reference` is incompatible with `--from-game`.

Validators fail closed. A failure must name the validator, gate, affected
mission or Story key, source path, bounded expected/actual values, and relevant
hashes in both structured output and the CLI summary.

Review manual option coverage, stale targets, and current generated response
candidate conflicts with the single maintained option audit:

```bat
python -m scripts.story_recovery.build_option_override_coverage_audit --language CN
```

Manual Story order is user-managed in `webui/overrides/story_order.json`.
OCR writes proposals to `webui/data/story_order_ocr.json`; exports never replace
the active override.

Gameplay-video OCR uses one command surface. `sample` extracts OCR evidence,
`match` builds an OCR-only order proposal, `publish` refreshes the compact
WebUI reference, and `compare` reports differences without editing the active
override:

```bat
python -m scripts.story_recovery.ocr_story_order sample --dry-run
python -m scripts.story_recovery.ocr_story_order match
python -m scripts.story_recovery.ocr_story_order publish
python -m scripts.story_recovery.ocr_story_order compare
```

AnimeStudio Story-object recovery uses one staged audit. `reverse` publishes
the fail-closed playback-alias evidence consumed by builders; `carrier` and
`hierarchy` remain optional candidate diagnostics, and `all` runs the three in
dependency order:

```bat
python -m scripts.story_recovery.audit_story_objects --stage reverse
```

Native value-carrier work also uses one profile command. `generic` is the
importable type/field-driven scanner, `cinematic` retains the structural queue
contract and its existing report paths, and `radio-forbid` validates the small
versioned negative boundary recorded for the pinned build:

```bat
python -m scripts.story_recovery.audit_native_carriers generic --carrier-type TYPE --focus-field FIELD
python -m scripts.story_recovery.audit_native_carriers cinematic
python -m scripts.story_recovery.audit_native_carriers radio-forbid
```

Reusable implementations and the radio boundary live under
`story_recovery/native_carriers/`; tests live under `scripts/tests/` rather
than beside recovery tools.

Mission and audio runtime traces share one fail-closed CLI while retaining
separate hook manifests, Frida agents, schemas, and evidence boundaries:

```bat
tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile mission
tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile audio
python -m scripts.story_recovery.runtime_trace import --profile mission CAPTURE.jsonl
python -m scripts.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl
```

The reviewed LevelScript task paths are builder-owned in
`story_builder/native_contracts/mission_task_paths.json`. The protocol registry
reads that contract directly; the mission runtime hook manifest references and
validates the same contract before rendering its Frida agent, so task RVAs,
message IDs, and field offsets have one mutable source of truth.

## Assets and audio

Prefer `export.bat --from-game --with-assets` when both Story and assets need a
fresh extraction. Use `export_assets.bat --from-game` when Story is already
current, or plain `export_assets.bat` to rebuild indexes and relink existing
decoded assets.

`build_audio.py` writes shared SFX/music once under
`export_full/structured/Audio/shared/` and language voice under
`export_full/structured/Audio/<LANG>/`. AnimeStudio streams decoded PCM into
lossless FLAC without intermediate WAV files or `ffmpeg`. The maintained decode
and WebUI output are FLAC-only. Existing WAV/WEM files remain readable when an
index-only maintenance run encounters them, but the builder no longer produces
or converts those formats. Projectile behavior and authored event hashes stay
immutable in `webui/data/gameplay/projectiles.json`; Audio publishes playable
HIRC candidates separately in
`webui/data/lang/<LANG>/gameplay/projectile_audio.json`.
Use `--skip-decode --refresh-hirc` when parser/schema work needs a fresh HIRC
bank pass while decoded audio files are already current; plain `--skip-decode`
reuses the existing event-media/HIRC cache.
Its v150 HIRC parser also publishes exact NodeBase effect slots and output-bus
IDs. Effect definitions retain physical PCK/bank scope, built-in plug-in class
identity, and parameter hashes. Fingerprinted shipped `SetParamsBlock` layouts
decode exact authored base settings for Gain, Delay, Compressor, Expander,
three-band Parametric EQ, Meter, Matrix Reverb, Pitch Shifter, Harmonizer, and
Stereo Delay. Guitar Distortion exposes three pre-EQ and three post-EQ bands
plus distortion type, drive, tone, rectification, output gain, and wet/dry mix.
The v150 FX-slot bit vectors are also decoded: direct NodeBase slots expose
authored bypass, ShareSet, and rendered bits, while Audio/Aux Bus slots expose
the bypass/ShareSet subset. These flags are not runtime DSP/audibility proof
and remain separate from node-level `bypassAll` and dynamic BypassFX controls.
RoomVerb exposes all 37 public authoring controls and all 31 ER pattern names;
its 11 additional private algorithm-tuning IDs retain exact values with
native-use roles: five feed early-reflection tap-pattern synthesis (endpoint
pairs plus seeded per-tap variation, then ER-grid normalization), one feeds
six-channel coefficient derivation, two feed a seeded secondary
reflection-pattern generator, and three remain name/read-unresolved in the
audited native path.
Convolution Reverb exposes its 13 public runtime controls plus exact
impulse-response plug-in media IDs. Its two private rows retain exact native
forwarding evidence: SetParam 34 reaches wrapper +0x4c and both convolution
processing paths, while serialized byte 56 reaches wrapper +0x50 and runtime
state (including runtime state +0x8c for the byte). The current CPU consumer does
not expose a read of the forwarded scalar,
so public names and final DSP roles remain fail-closed; IR IDs are not emitted
as playable WEM leaves.
Mastering Suite exposes its four output-device modules: six EQ bands, four
multiband-compressor bands with crossover/link controls, overall plus 12
serialized channel gains, and limiter mode/threshold/timing/output/link values.
Its SetParam IDs 100 and 200 remain exact unnamed codes. Binary evidence pins
them to native storage +0x18/+0x88, but no direct read is observed in the
audited runtime region; the UI labels them storage-only and keeps those
definitions visibly partial rather than inferring processing-order or profile
semantics. The 12 channel gains map exactly from serialized offsets 235..279 to
native +0x118..+0x144 (stride 4), while speaker names remain unresolved.
Type-8/type-18 HIRC objects also publish
the complete 279-bus parent hierarchy (276 parent edges and three roots).
Typed v150 ``CAkBus`` parsing consumes the property, positioning, Aux, duck,
and bus-state fields before InitialFX and proves the serialized effect count on
all 279 buses: 128 have an explicit zero-count list (including the 50 Audio Bus
and 11 Auxiliary Bus rows previously recovered by sibling correlation), while
151 have 247 decoded non-empty slots. The same v150 NodeBase tail parser
recovers the authored AuxParams bitvector, four conditional User-Defined Aux
Bus slots, and Early Reflections Bus ID with field-level fail-closed
diagnostics. The current unique-payload audit passes 188,964/188,964 nodes,
finds 7,492 populated User slots to 25 Aux Buses, 30,162 Game-Defined Use bits,
and no populated Early Reflections target. Game-Defined Bus IDs/listeners/send
levels are runtime API inputs and remain unresolved rather than projected as
static routes. The Bus parser now continues through the v150 suffix in its
actual order—InitialRTPC before StateChunk—and parses all 279 Bus payloads
exactly: 92 curves/265 points, 15 State groups, 32 States, and 34 authored
State values. Parameter labels use the current RTPC table; out-of-range IDs such
as `0x1802`/`0x1804` remain explicit custom/internal numerics rather than
guessed DSP names. The NodeBase parser continues through AdvSettings, StateChunk,
and InitialRTPC: an independent audit matches production offsets and row counts on
188,964/188,964 unique node payloads, recovering 1,278 State Group occurrences,
5,709 RTPC curves, and 15,599 points. The generated summary now carries a
hash-pinned IL2CPP cross-match for six
game-side GameParameter symbols: `AU_RTPC_CINE_CTRL_VOL_AMB` (`0x6b7dc358`,
3 node/4 Bus curves), `...VOL_MU` (`0x590f4cd1`, 2 Bus curves), `...VOL_SFX`
(`0x52aabb05`, 11 Bus curves), `...IS_MUTE_BY_SDK_WEBVIEW` (`0xba4a40b7`,
1 Bus curve), `...IS_SURROUND_CHANNELS` (`0x7ec2f9aa`, 2 Bus curves), and
`...GLOBAL_VOL_MASTER_IOS_WORKAROUND` (`0x3794392f`, 1 Bus curve). This is
symbol-to-ID evidence only; `0x1802`/`0x1804` remain custom/internal Wwise
property IDs with no guessed DSP names or live-value claims. Event/media RTPC
and Bus-control rows reuse the same exact-name catalog; unmatched IDs remain
numeric/custom. Generated event evidence preserves State
property values and complete RTPC points/accumulation/scaling with known control
hashes named only by exact FNV/native evidence. The semantic media shard also
projects each possible media leaf onto its exact serialized Event output-bus
paths and keeps effect/unresolved bus IDs as references into that catalog;
runtime branch selection and effective DSP are not inferred. The same build publishes
serialized trigger-context summaries on each media row (semantic kinds, roles,
owners, situations, and selection/activation statuses) through an exact
`mediaRefs` join; these remain authored requests rather than observed playback.
LevelScript `PlayVoice`/`PlayVoiceNarrative` rows are kept as a separate
direct path-stem contract: their constant `_voId` selects an `AudioDialog`
path and deliberately has `wwiseEventStatus=notApplicable`; they are not
rewritten into Wwise Event identities.
The same semantic build scans current IL2CPP string fields for 25 unique
`AU_*` symbols whose AudioHashGenerator hashes match current Wwise Event IDs.
It publishes each declaring type, field token, metadata hash, and exact
symbol-to-ID evidence, then uses the existing name-prefix taxonomy only for a
conservative broad category. This static field identity does not recover the
runtime setter, caller, trigger, selected branch, execution, or audibility.
The same build now adds 18 exact native `SwitchAudioCustomState` contexts across
rotate-platform, crane, electric-fence, ForgeIron, LifterButton, and
MovingPlatform Event rows. The trigger catalog exposes the decoded custom-state
name, current-build method/callsite evidence, and metadata usage word only
after an authored `InteractiveData` custom-state join. RotateNormalStart and
RotateOverStart remain separate branch-specific states at one native callsite;
branch execution, object ownership, and audible output remain unobserved.
The same fingerprint-locked catalog also places the pause/resume control Events
`au_gameplay_pause_spidle` and `au_gameplay_resume_spidle` at their exact
`SnapshotSystem` `PostEvent` callsites; the selected action entity and runtime
execution branch remain unobserved.
Complete final-media leaf-set equivalence also recovers a uniform broad output
category for 85 hash-only Events (56 SFX, 21 UI, 6 voice, 2 control), without
upgrading their caller, trigger, branch, or runtime-purpose status.
The projection also retains weak category-name evidence for 954 named Events
from enemy, actor/UI, LevelSequence, and Gameplay-SFX families; exact voice
contexts override the weak enemy-name category on 602 rows.
Media paths that remain under `wwise/unknown` now receive a separate semantic
category from exact evidence: 40,421 rows (34,458 SFX, 5,645 voice, 188 UI, 66
ambience, 48 control, 13 music, 3 cue). This includes 40,217 uniform related-
Event joins, four trigger-context Event categories, and 200 MonoBehaviour
audio-field roles. The raw physical category is preserved; 276 mixed
known-category joins remain unclassified.
Media whose typed NodeBase evidence has `outputBusNodeCount=0` now receive an
explicit `noExplicitOutputBusSerialized` status; this is not treated as a
default route, silence, or proof of an effect-free path.
Media rows also carry bounded exact direct NodeBase effect slots from Event
`postProcessSummary.effectNodes`, separate from output-Bus effects. Each
summary preserves the effect ID/plugin, node and slot, authored parameter
summary, and slot flags without claiming live DSP execution or audibility.
They also carry exact serialized Wwise media-edge types and selection paths
(`directSound`, `layerChild`, `randomAlternative`, `switchCandidate`,
sequence/music edges) plus root Action IDs. The current CN projection has
59,109 media rows with graph evidence and 39,619 selection-path summaries;
these are authored candidate relations, not runtime branch or caller traces.
Media rows also receive a separate Event-level context summary for the
possible media set: 44,442 rows and 367,317 context occurrences currently
carry compact consumer kinds, roles, owners, and situations. This is broader
than exact `mediaRefs` and remains explicitly non-selected/runtime-unobserved.
The current CN build exposes these on 1,879 media rows with 471,281 slot
occurrences; each row keeps at most 32 distinct summaries and reports when
the list was truncated. Media rows also publish a compact serialized effect
chain that combines direct-node slots with each leaf-to-root Bus path: 32,044
rows and 573,360 authored chain stages in CN, capped at 64 stages per row.
Direct-node slots are shown before Bus slots, and Bus slots preserve serialized
path/slot order. This is an authored binary join, not observed runtime DSP
ordering, inherited values, branch choice, or audibility.
The same media rows keep compact references to serialized Bus controls: 31,523
rows, 135,375 controlled-Bus occurrences, 332,954 RTPC curve occurrences, and
5,616 State values in CN. Full points and plug-in parameters remain in the
unique Bus catalog and are resolved by Bus ID instead of duplicated per leaf.
Serialized Bus ducking is also projected compactly: 1,909 CN media rows reach
2,249 ducking Bus definitions with 4,453 authored duck slots, preserving target
Bus, attenuation, fade, and target-property fields. Runtime duck activation and
audibility are not inferred.
Exact User-Defined Aux slots are projected compactly as well: 20,588 CN media
rows expose 27,592 unique Aux Bus/slot targets and 698,886 underlying send
occurrences. Source-node types, flags, root Actions, and target Bus IDs remain
visible; Game-Defined IDs and live send levels are runtime-only.
Each target also retains its exact serialized Aux Bus parent path and effect-Bus
IDs, linking the possible send route into the typed Bus/DSP catalog.
NodeBase authored property values and ranges are also summarized per possible
media path: 53,882 CN rows expose 715,175 distinct property signatures across
18,436,139 occurrences, and 21,526 rows expose 48,721 range signatures across
113,639 occurrences. Raw U32 forms and full node provenance remain in Event
evidence.
The same media projection publishes bounded exact StateChunk overrides and
InitialRTPC response shapes from possible Event paths: the current CN output
has 4,300 media rows with 20,254 RTPC control summaries and 1,292 rows with
2,339 State-value overrides. Each RTPC summary keeps at most eight points and
marks truncation. These joins describe authored serialized controls, not live
setter values, selected branches, effective inheritance, platform DSP, or
audibility.
The same build publishes exact initial AkPropID v150 bundles: 90,639 traversed nodes contain 165,161 authored
values and 1,650 min/max ranges, with raw U32 and finite-float forms preserved;
typed ID/integer unions retain integer labels rather than fake tiny floats.
Initial BypassFX/BypassAllFX property IDs do not occur in the current banks;
direct NodeBase bypass flags remain a separate exact field and dynamic bypass
is still unresolved. Effective inheritance, live State/RTPC/modulator values,
platform DSP, and audibility remain gaps.

The same v150 HIRC pass now decodes non-playback Action tails directly from the
bank bytes. SetState (3,455), SetSwitch (304), Set/ResetGameParameter (158),
Stop/Pause/Resume (1,627), Seek (122), value/filter actions (1,020), and FX
slot actions (32) are all `typedExactV150` in the current named-event
evidence (0 failed control tails); the parser also preserves typed Event→Action
object paths/type labels, action ordinals, FNV IDs, value ranges,
fade curves, active-action bit vectors, exception buses, and FX slot indices.
The semantic projection now joins 1,601 State/Switch Action group references
and 1,042 exact value references. It covers the three native-backed selector
roles (voice identity, surface material, and local/remote routing), plus ten
exact current-metadata music State groups. Typed type-6 selector packages use
the same 15-row catalog; unmatched IDs remain numeric.
Within the same Event evidence, 12 Set/ResetGameParameter rows share an exact
ID with an InitialRTPC curve target (2 unique IDs); these are exposed as
`sameEventInitialRtpcId` authored curve-target joins, while the GameParameter
name and live value remain unresolved.
Five unique InitialRTPC IDs are also joined to exact metadata `au_rtpc_*`
literals (14 curve occurrences across six Event occurrences). The catalog keeps
the exact authored Event/context, controlled AkProp targets, response-point
count, and interpolation mix; it does not claim a live RTPC update or audible
result.
The schema-117 semantic payload additionally publishes
`controlCatalog.staticRtpcAlignment`. Its six-name canonical `AU_RTPC_*`
contract (mapping owned by `audio_semantics/rtpc_contract.py`) aligns exact
numeric HIRC IDs with serialized InitialRTPC curve/property evidence and
same-event Set/ResetGameParameter controls. `rtpc_alignment.py` publishes this
as `authoredStatic` evidence only. The explicit selected
`global-metadata.dat` + `GameAssembly.dll` hash gate is required; a missing or
mismatched selected/source hash, malformed or incomplete contract, or stale
serialized evidence fails closed and withholds static names/rows. Runtime
parameter values, setter execution, target objects, selected branches, DSP,
and audibility remain runtime-only. Existing page data changes only after a
formal semantic rebuild (normally `export.bat`, or the targeted
`python scripts\build_audio_semantics.py --language CN` run).
These are authored trigger parameters, not evaluated runtime state, effective
inheritance, selected branch, DSP execution, or audibility. Any unsupported or
truncated tail is published as `failedClosed` with an offset and reason.

`build_audio_semantics.py` publishes the authored v150 Type-6 selector subset
only on lazy Event-detail records as `selectorBranches` with
`selectorBranchSchemaVersion=1`; compact Event summaries omit this payload.
Package child IDs join decoded media only through exact same-bank
`soundObjectIds` evidence. Malformed or cross-bank structures stay unresolved
and fail closed, while runtime selector choice and audibility remain unresolved.

The same semantic build publishes LevelScript audio lifecycle evidence with the
serialized action ordinal and validated static topology. Producer/consumer
links are admitted only for an exact same-LevelScript source-root and source-
path identity, with one active final serialized slot and one unique output
path. `story_builder.level_bindings` resolves `ParamSource=200` dynamic string
properties only through the strict `LevelScriptBriefData` property formatter;
`ParamSource=100` and unknown/runtime sources remain runtime-unresolved and
cannot become handles. Full lifecycle identities and raw paths are lazy
Event-detail data under `levelScriptAudioLifecycle` schema version 1; compact
rows retain only bounded summaries. This is authored serialized topology, not
runtime handle state, action execution, branch selection, or audibility.

RemoteCommon lifecycle fields use an exact Persistent-over-Streaming row
overlay: non-empty `startAudioEvent`/`endAudioEvent` values become separate
authored trigger contexts, while `voiceId` remains a dialogue identity. The
current CN contract has four lifecycle rows; all resolve to Wwise music Events,
none has a playable media leaf, and runtime execution remains unobserved.

`build_audio_semantics.py` is the thin orchestration/publishing surface for
the Audio evidence page. Maintained domain code lives under
`audio_semantics/`: `native_evidence.py` owns the installed-build gate,
`external_source.py` owns static External Source voice-route/path joins, and
`model_view_projection.py` owns authored ModelView normal/positioned branch
projection;
`identifiers.py` owns Wwise hashes and managed string identities,
`managed_literals.py`, `responsive_voice.py`, and `voice_requests.py`
own their respective consumer evidence, `interactive_components.py` and
`authored_components.py` own serialized component recovery,
`table_contexts.py` owns authored table/config scanning and the validated,
bounded AudioCue expression AST. The projection retains the complete validated
tree with cue/handler scope, expression side, source path, parent/depth,
`exprType`, four serialized scalar fields, child paths, node class, and
bounded diagnostics without evaluating serialized expressions. Non-empty
behavior `exprType=3` leaves are authored Event requests; non-empty
`exprType=8` leaves are `runtimeCueVariable` evidence; non-empty child lists
are `compositeOpaque`, and all other nodes remain opaque. `childrenLimit`
rejects the parent before child projection. `audio_cue_native.py` owns the
selected `global-metadata.dat` / `GameAssembly.dll` gate: enum/operator names
are published only for a validated exact contract, while missing or mismatched
native inputs keep those names absent.

MonoBehaviour `monoBehaviourAudioIdField` contexts are projected by
`audio_semantics.managed_literals.project_mono_behaviour_audio_field`. The
serialized path remains the evidence; the narrow `component*` role is an
authored static field label, while `componentLayout`, raw field/path values,
and exact GameObject placement stay separately searchable. Component or
callback execution, Event posting, Wwise selection, and audibility remain
unobserved. Role/layout coverage is emitted in generated Audio stats and Event
summaries rather than fixed in this document.

`scene_backgrounds.py` owns the scene-background catalog. It consumes the real
AnimeStudio AssetMap object root in one bounded streaming pass, using exact
AssetMap `Source` + `PathID` identities. Prefab-local and scene-asset
containment candidates remain separate; only an authoritative scene ID with
unique scene containment promotes scene ownership. Missing, malformed, or
unreadable maps fail closed rather than falling back to names or paths. It
resolves `AudioMapData` and scene emitters by script type, and joins exact
`AudioLevel` rows plus `MissionRuntimeAsset.acceptMode.levelId`. The semantic
publisher writes `webui/data/lang/<LANG>/audio/scene_backgrounds.json` with
authored Event requests and possible Wwise media leaves. Scene activation,
State/RTPC values, selector branches, listener state, playback, and audibility
remain runtime evidence; source prefab definitions do not prove level-instance
placement. `recover_map_streaming_instances.py` also publishes the validated
InitChunkData entity/name/transform and raw ECS columns with a versioned prefab
identity contract. The current validated columns expose no known prefab
Source+PathID/hash field in the observed schema, so no instance is promoted by
basename, entity name, position, Mesh, or similarity. If a future sidecar has
an exact numeric identity, it may resolve through one unique full AssetMap
container path (or an explicit component identity) before the Audio page
attaches a level; ambiguous and missing relations stay unresolved.
If explicit component identity and exact prefab-path identity routes disagree,
reconciliation fails closed with `conflictingPrefabInstanceIdentityJoins`;
current sidecars still do not produce the required prefab Source+PathID.
`media_ownership.py` projects those scene roles plus exact Event-context and
external-path evidence into coarse decoded-media ownership such as scene
environment, animation, authored component, interaction, or mission narration.
It may fill an otherwise unknown semantic category only for unambiguous roles
such as outdoor room tone or an authored ambient emitter; ownership never
upgrades runtime playback or audibility status.
Scene-emitter Event rows also publish compact containment and prefab-identity
status sets. The current valid negative contract is prefab-local/static-authored
emitter with unresolved scene and unavailable prefab identity; only exact
SceneAsset/Level containment or an exact prefab Source+PathID evidence row
joined to one level may publish sceneEmitterSceneIds. Candidate paths, sidecar
levelId, names, positions, and mixed exact attributions fail closed. The next
recovery step is exporter/sidecar production of exact prefab identity, not more
filename or path inference.
Scene-global Event rows also receive a compact attribution only after the
already merged `scene_backgrounds.py` catalog validates every direct context:
the complete scene-id and original semantic-role sets are retained, while
malformed, partial, non-direct, truncated, or out-of-catalog contexts remain
unavailable with bounded diagnostics. This is authored definition evidence;
`foundInWwise`, category, runtime activation, branch choice, playback, and
audibility are unchanged.
The same module owns the CharacterTable/EnemyTable/EnemyTemplateTable animation
identity overlay catalog. Persistent rows are authoritative; a malformed Persistent
layer suppresses that table's identity surface instead of silently falling back
to a stale base. Each supported serialized AnimationClip callback keeps
per-Clip resolved entity IDs separate from candidate IDs: exact Character,
Enemy, or EnemyTemplate matches may resolve, while unique-token and multi-match
possibilities remain candidate/ambiguous. Shared callback owners remain shared,
and missing, malformed, or unsupported evidence stays unresolved/fail-closed;
candidate IDs never become resolved ownership.
The same domain loads current `CharacterTable` keys and assigns authored
`chr_*`/`au_chr_*` Event namespaces, plus Event-leading internal character
tokens such as `lastrite_*`, to a character only through a delimited full key,
a unique four-digit character-id prefix, or a uniquely owned exact token. It
propagates that owner set to possible media, retaining every owner when a Wwise
leaf is shared.
Generic character templates, display-name similarity, actions, runtime
requests, selected leaves, and playback positions are not inferred.
Every supported serialized AnimationClip `PostAudioEvent` context is also
projected as an explicit Event/media callback link with its clip, owner,
function, reachability, and AnimatorController names when available. This
callback link does not require the Event and clip names to match and does not
promote an unknown category.
The same domain recognizes an AnimationClip action name and Wwise Event id
only when their normalized names match exactly inside an existing
`PostAudioEvent` callback context. This promotes the Event and its possible
media to action SFX while retaining the clip, actor, callback, and runtime-
selection boundary; name similarity without the callback never creates a
trigger or ownership edge.
`table_contexts.py` and `event_projection.py` / `event_summary.py` own WebUI
row projection. Full AudioCue ASTs are lazy Event-detail data under
`audioCueExpressionSchemaVersion=1`; compact rows publish bounded summaries
only. The AST is a static request/operand projection, never condition truth,
variable value, branch execution, or playback evidence.
`build_audio.py` imports shared primitives from those owners instead of
treating the semantics entry point as a utility module.
The semantic index also publishes the bounded
`externalSourceEventIdentityAudit`: External Source Event ids are compared
separately with typed voice-table routing aliases and the narrower AudioDialog
path-hash aliases, preserving the Event-route versus per-request
`externalSourceKey` boundary.
When the structured AudioDialog tables are available, the same audit adds a
typed `overrideWwiseEvent -> AudioDialog.path` candidate join: the current CN
export produces bounded route/path candidate sets. Shared route Events remain
candidate sets, not selected runtime rows; changing counts are kept in
`reports/story/recovery/audio/external_source_override_path_audit.*`.
Typed `AudioDialogChannel` narrating/radio fields add a broader candidate join
for channel-selection candidates; this is explicitly lower-confidence evidence
and is reported separately in
`reports/story/recovery/audio/external_source_channel_path_audit.*`.
The selected-build native I/O chain also carries a read-only pointer-table
census for the registered device, default file-I/O object, provider, and pump;
the generated `reports/story/recovery/audio/native_io_vtable_pointer_census.*`
is static dispatch evidence, not a runtime playback trace.

The VoicePlayer resolver's static arguments are also closed on the selected
build: it reads `VoiceI18n.s_languagePrefix` and calls the shared formatter as
`("{0}/{1}/{2}", "Voice", languagePrefix, VoiceData.path)`, yielding the native
key shape `Voice/<language>/<VoiceData.path>` before `PostEventExternal`.
`_PostEventWithExternalSource` passes that same managed string directly to
`AkExternalSourceInfo.szFile` before native descriptor copying, so the direct
VoicePlayer key-to-descriptor-path identity is statically closed. The remaining
runtime gap is source-state/sourceInfo instance selection and opened-handle
identity.
The managed codec argument is a separate closed boundary: current metadata
defines `Beyond.Audio.AudioCodec` as `PCM=-1`, `ADPCM=1`, `VORBIS=2`,
`ATRAC9=6`, and `OPUS_WEM=10`, and the selected `_PostEventWithExternalSource`
body forwards its eighth stack argument unchanged into
  `AkExternalSourceInfo.set_idCodec`. Its resolved AkSoundEngine export
`CSharp_ada48f7e7181c770` (`AkSoundEngine.dll+0x335c0`) jumps to
`0x180006050`, which stores the value directly at descriptor `+0x04`; there is
no setter-side conversion. Current public `AKCODECID_*` constants use
different values (`PCM=1`, `VORBIS=4`, `ATRAC9=12`, `AKOPUS_WEM=20`), so the
  raw Beyond enum domain is now closed at the descriptor while its downstream
  native consumer semantics remain unresolved. The installed runtime type
  table resolves both `RuntimeVoiceData.codec` and the adapter's codec
  parameter to `Beyond.Audio.AudioCodec`; the remaining gap is native
  descriptor consumption. Do not equate the Beyond enum with the public
  `AKCODECID_*` constants.
  The same selected GameAssembly also closes the serialized voice-codec side:
  `RuntimeVoiceData.FromSparkBuffer` and `VoiceData.get_codec` both read serialized
  `VoiceData.codec` at offset `0x14` through the shared SparkBuffer integer
  reader and copy the returned `Int32` unchanged into `RuntimeVoiceData.codec`.
  Thus the serialized `VoiceData.codec -> RuntimeVoiceData.codec` edge is raw
  propagation. The AudioDialog field name/schema agrees with that serialized
  field, but this does not claim a separate table-loader trace. Runtime type
  resolution closes the managed handoff into the adapter's
  `Beyond.Audio.AudioCodec` parameter; only native interpretation remains
  open.
The nearby sourceInfo/provider branch is not that consumer: its non-flag-9
`sourceInfo +0x04` fallback becomes provider state `+0xb8`, which the selected
stream helpers use as a byte-position/stream bound. The managed external
`idCodec` is preserved in the copied external record payload and has no
static edge to that provider field or a decoder branch yet.

Native Audio claims always receive both the selected
`global-metadata.dat` and the matching `GameAssembly.dll` through
`--game-root`. Missing or mismatched binaries retain authored evidence but
omit build-locked callsites, mappings, and runtime addresses. Do not restore
module-global default game paths, duplicate native catalogs, compatibility
re-exports, or broad `ImportError` import fallbacks.

For the remaining live source-state/sourceInfo-to-open-handle, optional
decoder-callback, and unobserved-codec-descriptor joins,
the read-only runtime probe is prepared with the repo-local Frida environment:

```bat
tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile audio --check-only
tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile audio
python -m scripts.story_recovery.runtime_trace import --profile audio CAPTURE.jsonl
```

The audio hook manifest also verifies `AkSoundEngine.dll` and attaches optional
native lookup, source-manager key-join (`0xe2cd0`), key-to-decoder registry
(`0x13f440`), source/provider preparation (`0x1af7a0`), post-call descriptor, callback-queue, Wwise open, and
asynchronous-read probes, plus the managed external-post/callback boundaries.
It also has an optional current-build `VoicePlayer.ExternalSourcePreparation`
hook at `GameAssembly.dll+0x3abef40`; its ABI records the formatted
`externalSourceKey` together with the Event, audio-object argument, and voice
handle immediately before the external-post helper, and samples its fifth
stack argument (`codec` at entry `+0x28`) as `voicePreparationCodecs`. This
narrows the managed
path-resolution boundary, but does not by itself prove native lookup, file
open, decode, or audibility.
The key-join probe records the requested key and source-state `+0x268`; the
registry probe records the same key argument and active decoder pointer. These
hooks are prepared evidence only until an authorized capture observes a match.
The provider-preparation hook follows decoder `+0x18` to owner `+0x288` and
records the descriptor `+0x10` UTF-16 candidate without assuming that its
flags select the path; the importer reports only exact path-string overlap with
the default-I/O open hook. The descriptor-copy hook also records the copied
allocation pointer and the manager-constructor hook records its `descriptorInfo
+0` pointer; the importer publishes `sharedDescriptorAllocationBases` when a
same-session pointer match is observed, without promoting it to a sourceInfo,
file-handle, or PCM join.
The importer publishes these observations under `nativePairing.keyLifecycle`,
including bounded key intersections, explicit
`registrationManagerJoinRequestedKeys` /
`registrationManagerJoinStateKeys268` comparisons, descriptor paths, and
file-open paths. Those registration-to-join intersections directly test the
currently unresolved generated-serial versus source-state-key equality, but
remain same-session evidence unless pointer or managed call-chain data narrows
them to one request; they are still not proof of one handle, codec stream, or
PCM buffer.
The Frida agent also resolves the exact external-source manager hash-table node
by serial at constructor return and at join/lookup entry. The importer exposes
`registrationManagerEntryPointers`, `managerJoinEntryPointers`, and
`sharedRegistrationJoinEntryPointers` (plus the lookup equivalent). A shared
pointer proves that the observed values reached one native manager entry in
that capture; it still does not prove the descriptor selected a file handle,
decoder stream, or PCM buffer.
`managerEntryDescriptorInfoPointers` and
`sharedManagerDescriptorAllocationBases` separately compare manager entry
`+0x38` with the descriptor-copy allocation, proving retention of the same
descriptor allocation when they intersect; this remains ownership evidence,
not a sourceInfo/path/file/PCM join.
Each native hook event also carries `nativeParentCaptureId` when another
attached native hook is active synchronously on the same thread. The importer
publishes exact resolved pairs under
`nativePairing.nativeCallRelations` as
`synchronousNativeHookNesting`; missing or merely adjacent IDs are omitted, so
this relation does not infer asynchronous ownership, file, decoder, or PCM.
It also publishes `nativePairing.managedExternalPathLifecycle`: the optional
VoicePlayer preparation path is joined to the Adapter external-post path only
through the Frida parent-capture chain, then compared with descriptor/provider/
open path strings in the same session. Exact parent/path matches narrow the
managed-to-native boundary, but are still not a native handle, decoder, branch,
or PCM correlation. Native events also carry the same-thread managed hook stack
when a synchronous bridge is active; the importer emits bounded
`managedNativeContextCorrelations` and exact descriptor/provider/open path
matches for that direct stack relation. This is stronger than a same-session
string overlap, but it still does not join a later asynchronous sourceInfo,
handle, decoder stream, or audible PCM result.
The importer also publishes `nativePairing.callbackLifecycle`: when the native
resolver/queue descriptor pointer equals the managed
`_OnExternalSourceEventCallback` cookie, it records bounded callback-context
transport evidence. This pointer is the temporary callback mapping object, not
the Wwise external-source cookie, and the match still does not prove file,
decoder, PCM, or audibility.
When the managed parent-capture chain includes `AkCallbackManager.PostCallbacks`
and `_ProcessEventCallback`, `callbackLifecycle` also emits bounded
`managedExternalCallbackChains` and raw callback-type values. That proves the
managed Wwise callback-delivery chain for the capture only; it does not join the
native resolver descriptor, file, decoder, or PCM.
The source-manager constructor hook decodes its stack ABI explicitly: `args[5]`
is the resolver function stored at manager `+0x50`, `args[6]` is the mapping
pointer stored at `+0x58`, and `args[7]` is operation flags at `+0x60`.
The Wwise default-I/O path is hooked at its real `0x5030` entry (the manifest
decodes the UTF-16 file-path argument); do not treat the interior `0x5080`
branch as an independent function. The profile also observes the embedded
codec stream callback at `0x1c9fa0`, including its indirect callback/context
pointers and bounded buffer state, plus the selected Opus memory-source copier
at `0x1c44d0`. The codec state path at `0x1801c8d11` calls that reader, and
packet wrapper `0x1801c8b60` reaches `0x1801cc1b0` at `0x1801c8bda`; every
direct parser caller supplies a known callback in the callee-frame `+0xf0`
slot: `0x1801c6490`/`0x1801c6bf2` pass `0x1801c6f90`, and wrapper
`0x1801cc1e1` passes `0x1801cbff0`. Both are integer-array transforms invoked
at `0x1801cc4ce/0x1801cc532/0x1801cc57e`, not PCM sinks. The selected Opus
descriptor and the header-recognized generic memory descriptor are both
resolved: `0x1801c4650 -> 0x1801ca9a0 -> 0x1801cfe80` constructs a descriptor
whose `+0/+8/+0x10/+0x18` entries are `0x1801cfd80/0x1801cfe00/0x18010ad90/
0x1801cfd70` (copy/advance, seek, data-pointer, and free). The selected decoder
output path is also statically closed: `0x1801c4650` calls `0x1801c7ec0` at
`0x1801c4770`, then loads returned float samples at `0x1801c481a`, scales and
converts them, and writes signed PCM16 samples to the caller buffer at
`0x1801c483c`. A selected-build direct-call scan finds only two calls to stream
setup `0x1801ca710`: `0x1801c7e3e` from the Opus wrapper
(`0x1801c5255 -> 0x1801c7df0`, descriptor `0x1802b09d8`) and `0x1801caa1c`
from the generic memory wrapper (`0x1801c46f9 -> 0x1801ca9a0 -> 0x1801cfe80`,
the four-entry descriptor `0x1801cfd80/0x1801cfe00/0x18010ad90/0x1801cfd70`).
No additional direct setup callsite or direct descriptor literal is present;
an address-taken indirect caller would remain outside this scan. A raw scan also
finds no absolute pointer literal or RIP-relative memory operand resolving to
`0x1801ca710` or `0x1801c9fa0`, excluding an in-image static setup reference
while leaving runtime-computed or external pointers open. The optional decoder callback context `+0x2a08` is read at
`0x1801c8b64` but has no direct store in the current AkSoundEngine function
table. A direct/overlap-aware audit of selected `.text` operands covering
`+0x29f0..+0x2a10` finds writes at `+0x29f8`/`+0x29fc` and a qword at
`+0x2a00` ending at `+0x2a07`, with no write reaching `+0x2a08`; this is a
bounded negative result, not proof that indirect initialization never occurs.
An exhaustive direct-call census separately finds ten valid readers of
`0x1801c9fa0`: `0x1801c83fd`, `0x1801c8d11`,
`0x1801c96bf/0x1801c985a/0x1801c9909`, `0x1801c9adb`, `0x1801c9cca`,
`0x1801ca1eb`, and `0x1801cb8ee/0x1801cbd1b`, grouped in containing functions
`0x1801c8160`, `0x1801c8c60`, `0x1801c9670`, `0x1801c9a00`, `0x1801c9c80`,
`0x1801ca110`, and `0x1801cb270`. This closes the direct read-consumer census
but does not identify additional setup descriptors or indirect callback targets.
The matching direct-call census finds three valid callers of decoder
`0x1801c7ec0`: `0x1801c477b` in `0x1801c4729`, plus
`0x1801c49bc` and `0x1801c4a3e` in `0x1801c499c`. The first call's returned
float samples flow through the known signed-PCM16 writes; the latter two are
the initial attempt and the retry after provider refill `0x1801af960`, with
return codes driving decoder state and consumption. No other direct decoder
call exists in the selected `.text`; this expands decode-consumer coverage
without proving an indirect decoder target or a new PCM sink.
The runtime manifest now hooks the exact decoder entry ABI at
`0x1801c7ec0`: `(decoder, float-output slot, frame-count slot)`. It samples
decoder owner `+0x18 -> +0x268` (the source-state key), provider interface
`+0x58`, the returned float-buffer pointer, produced frame count, and the
native return address before and after the call. Return address `0x1801c4780`
identifies the direct caller whose static body writes PCM16;
`0x1801c49c1`/`0x1801c4a43` are the refill/retry callers. The importer reports
key-registry/decoder-call,
source-provider/decoder-call, and source-state/decoder-call intersections as
bounded continuity evidence. It also compares provider-preparation
`sourceOwner` (`decoder+0x18`) with decoder-entry `decoderOwner`, giving a
same-owner check for the sourceInfo/provider instance; no verified capture has
produced those rows yet.
The optional sourceInfo-selector hook also samples the post-call selected table
entry key (`outputDescriptor +0 -> +8`), candidate descriptor pointer
(`outputDescriptor +0x10`), and candidate auxiliary field (`outputDescriptor
+0x18`). The source-info consumer and provider-preparation hooks sample the
source object's copied descriptor pointer at `+0x338` (owner `+0x18 -> +0x338`)
after the consumer returns. Matching these pointers is a bounded selector ->
source-owner continuity check; it still does not identify the external file,
handle, or decoded PCM.
The optional source-state initializer hook at `0x1800d1f90` samples the
destination source-state object, `sourceConfig +0x34`, incoming `sourceInfo`,
and post-write `sourceState +0x268/+0x288`. The importer intersects those
objects and keys with manager joins, provider owners, decoder owners, and
sourceInfo pointers. These are initialization-continuity checks, not proof
that the managed external key selected that instance.
The native manager-constructor hook also decodes its `u32` status return:
`1` is the successful registration path and `0x34` is the allocation-failure
path in this build. The importer records `registrationStatuses` so a future
capture can distinguish a missing join from a registration that never
completed; status alone does not prove source-state, file, or PCM identity.
The remaining address-taken codec callback/initialization targets, callback
ownership, runtime external source-state/sourceInfo identity, and live
invocation remain unresolved. The
direct VoicePlayer external key-to-copied-descriptor path is statically closed.
Static analysis now joins the file/key provider secondary interface's `+0x78`
GetBuffer-shaped queue (`0x1800b85c0`) to the registered device and the
device `+0x428` default file-I/O request slots used by `PerformStreamMgrIO`;
the provider `+0x80` slot (`0x1800b9a00`) is release/advance-shaped. The
sourceInfo file/key descriptor path is statically bounded through the concrete
factory `0x1800b5e30`, whose constructor `0x1800bb160` installs secondary
vtable `0x180293260` at allocation `+0x90`; its descriptor-copy path carries
descriptor `+0` as a UTF-16 path into provider-owned storage. The copied
descriptor allocation is retained through event record `+0x14` into source
manager `+0x38`; in the voice/render path `0x1801443e0` loads context `+0x268`
into a temporary dword at local `+0x10` and passes its address as stack argument
5 to `0x18018a5a0`. The `0x18018a5a0 -> 0x1801898c0` path preserves that pointer
in `r8`, and `0x180189a59` passes it as `rcx` to source/media lookup, so this
callsite reads context `+0x268` as source-state key `+0`. The other lookup
callers are `0x180189826`, `0x180189e18`, and `0x18018a2a8`.
The retention edge is now exact for the shared external PostEvent path:
`0x1800c38b0` receives the copied allocation from `0x1800c08d0`, stores it in
the local carrier `[rsp+0x50]`, and passes a pointer to that carrier to
`0x1800c3990`. The latter copies the carrier's 0x14-byte descriptor payload to
registration record `+0x14/+0x24`; `0x1800e12e0` forwards record `+0x14`, and
`0x1800e1320` stores its first qword at manager `+0x38`. Thus manager `+0x38`
is the copied external-descriptor allocation pointer in this path, not a raw
UTF-16 string. This still does not join that allocation to sourceInfo `+0x10`
or to the source-state key at runtime. The unrelated
local integer from temporary state/input `+0x10` (build constant `0x200`) and
context `+0x2a4` is not that key. Initializer `0x1800d1f90` copies the context
field from config `+0x34`; one concrete producer at `0x180034e4f` fills that
field from an upstream record `+0x14` before `0x1800365f0` calls the
initializer. Other constructors `0x1800fc9e0` and `0x18018dba0` receive their
config pointers through separate callers.
The retention lifetime is bounded too: exact-key detach callers
`0x1800e2a5e`/`0x1800e2a8e` enter `0x1800e1770`, which reads manager `+0x38`
only to pass the allocation to refcount release `0x1800c5f60` before unlinking
the entry. It does not dereference that field as a path or feed the provider or
codec, so `+0x38` is an ownership-retention field rather than a direct
sourceInfo/provider input.
The provider input boundary is separate: `0x1801af7a0` loads owner `+0x18`
and sourceInfo from `+0x288`; its file/key branch chooses sourceInfo `+0x10`
for the local descriptor when flag bit 9 is set, then passes that descriptor
through the singleton provider vtable `+0x28` to provider-owned UTF-16 storage.
That call boundary carries no explicit manager entry, manager `+0x38`, or
source-state key value, so it closes sourceInfo-to-provider provenance while
leaving identity with the copied external descriptor unresolved. The selected
factory's provider slot copies descriptor `+0` into provider-owned UTF-16
storage and retains descriptor `+0x08/+0x14` metadata. Exact build addresses
and the branch table are kept in the generated native-provider audit report;
this is still static path transport, not a live key/handle/PCM correlation.
The provider-to-file boundary is now explicit too: open wrapper `0x180024630`
passes the registered-device descriptor and returned path pointer through
`0x180004a20`/`0x180004b40`; the default I/O table dispatches slot 0 to
`0x180005030`, whose `CreateFileW`/`GetFileSize` pair stores the handle/size.
`0x180004b40` chooses the incoming path or device base path and normalizes it
through `0x180005150`. This closes provider-request to native-open transport,
but the boundary still carries no external key, source-state key, or manager
`+0x38` value.
The audio runtime trace now also reads the default-open routine's stack
argument-5 provider context after the call: the selected build stores the
`CreateFileW` handle at provider-context `+0x10` and file size at `+0`.
The async batch descriptor's provider object is sampled at `+0x10` as well,
so `runtime_trace_audio_import.py` reports an exact `openHandle` /
`descriptorProviderHandle` intersection when one capture shows the same
native handle crossing open into `ReadFileEx`. This is stronger than a path
string overlap, but it still does not prove source-key ownership, decoder
selection, PCM delivery, or audibility; stack-memory capture is only enabled
for this verified native hook contract.
The selected native `.text` has one direct source-config entry,
`0x18003def1 -> 0x180034db0`: stack argument 6 comes from the record returned
by `0x180040350` (`[object +0x10] -> [+0x68] +0x18`). Because that result is
parent `B +0x18`, `0x180034e4f` reads parent `B +0x2c` into config `+0x34`
before `0x1800365f0` constructs the source state. Sibling accessor
`0x1800404f0` reads the same `B +0x2c`; callsites `0x18003e35b` and
`0x18003e486` pass it into source vtable `+0x138`, proving local field reuse.
This closes direct producer/callsite and local-field-alias coverage, but parent
`B` is not statically aliased to the external registration record or its serial.
The source-state metadata pointer is bounded separately: initializer
`0x1800d1f90` copies incoming `r9` to `+0x288` and config `+0x34` to `+0x268`;
the primary `0x18003def1 -> 0x180034db0 -> 0x1800365f0` chain supplies that
`r9` from the record returned by `0x180046580` (via the callee's incoming
`r8`), while alternate initializer callers `0x1800fca27` and `0x18018dbc5`
have separate metadata inputs. The external manager's descriptor allocation
is instead retained at manager `+0x38` by `0x1800e1320`; no direct selected-build
edge joins it to the `0x180046580` record or source-state `+0x288`.
The source-state helper `0x1800d2ed0` separately feeds sourceInfo `+0` and
`((+0xc >> 2) & 0x1f)` into selector `0x1800f5030` through global slot
`0x180344a20`; that selector walks its own `+0x88`/`+0x90` table and compares
entry `+8` to sourceInfo `+0`. This slot is distinct from the external-manager
hash slot `0x1803449f8` and decoder registry slot `0x1803449d0`, so sourceInfo
`+0` is bounded as an internal selection key rather than a proven registration
serial. The selector's `0x1800f9780` helper fills a 0x20-byte descriptor
(`+0` matched entry, `+8` optional type-2 context, `+0x10` candidate `+8`,
`+0x18` candidate `+0x10`); the caller checks those fields against source
`+0x328`, passes the candidate through `0x180143de0`, then applies sourceInfo
through `0x180104720` before copying the descriptor into the source object.
This joins the internal key to source/provider setup, but runtime values,
path/handle choice, and PCM delivery remain unobserved.
External manager `+0x4c` is
populated from a separate `0x1800c3990` lock-xadd serial through
`0x1800e1320` (the `0x1800c3990` record `+0xc`, global lock-xadd result `+1`).
Direct-call coverage finds both constructor wrappers: `0x1800e12e0 ->
0x1800e1320` at `0x1800e130b` with callers
`0x1800c3516/0x1800c3b31/0x1800c3e7e`, and `0x1800e1490 -> 0x1800e1320`
at `0x1800e14d2` with callers `0x1800c41cc/0x1800c4472`. Each prepares a
native registration record before the constructor stores its `+8` dword at
object `+0x4c`; this closes wrapper coverage but not equality with source-state
key.
The lookup compares the complete numeric source-state key to that serial. The
source-construction path now has an explicit static join: `0x1800350d7` passes
the same parent `B +0x2c` into `0x1800e2cd0`, whose bucket walk compares it
directly with manager entry `+0x4c` (the `0x1800c3990` registration serial),
with no hash transform. A successful runtime match and the later file/PCM
handoff remain unobserved.
Within the child-source branch, `0x180034640` carries one source record through
`0x180037740`: constructor write `0x18003779e` copies record `+0x14` to the
child object's `+0x2c`, and `0x180034733` uses that same record field as the
`0x1800e2cd0` key. This proves local same-record value identity, but not an
alias to the separately generated registration serial.
An exhaustive direct-call census finds four join callsites: `0x180034762` and
`0x1800350d7` in the primary source/voice construction paths, plus
`0x1800d35a8` and `0x1800e06ea` in broader manager state transitions. Only the
two `0x034xxx` callers carry the parent-B/source-state key explanation; the
other two expand native join coverage but do not establish external-source
media selection, path opening, or PCM delivery.
Registration-key provenance is independently bounded: the `0x1800c3990`
families generate manager keys from lock-xadd serial slot `0x180344988` and
store serial+1 at registration record `+0xc` before the constructor retains it
at manager entry `+0x4c`, while the two primary source joins load their key
from parent-B/source-state `+0x14`. The complete source-state `+0x268` writer
audit finds no store sourced from that serial slot. Thus exact comparison is
closed, but equality is still a runtime-value question; path/handle and PCM
handoff remain unobserved.
An exact selected-build direct-call audit finds only two calls to
`0x1800c3990` (`0x1800c394e` and `0x1800c3c47`), both in registration or
external-post bridges; the primary source setup at `0x1800350d7` calls only
the exact-key join `0x1800e2cd0`. This is negative direct-call evidence, not
proof that indirect/shared-record aliasing cannot occur. The detailed census
is kept in `reports/story/recovery/audio/native_registration_serial_audit.*`.
The exact join body at `0x1800e2cd0` is narrower than a media lookup: a hit
appends the source-state pointer to manager entry `+0x10`, updates count and
capacity (`+0x18`/`+0x1c`), and optionally retains auxiliary state at `+0x30`.
It does not read manager `+0x38`/`+0x40` or the copied UTF-16 record, so this
edge is lifecycle/state registration only; the runtime key match and the
separate provider-to-path/handle/PCM handoff remain open.
The joined source-state pointer is retained only as manager-entry attachment
state: `0x1800e2cd0` appends it to entry `+0x10` (count `+0x18`, capacity
`+0x1c`), while `0x1800e29d0` removes a matching pointer, decrements the
count, and invokes `0x1800e1770`; manager reset `0x1800e2e20` frees these
arrays. Those consumers are lifecycle cleanup, not path/byte reads or codec
input, so the e2cd0 hit does not itself select a media file.
The shared helper `0x18018a5a0` receives a pointer to the key slot as stack
argument 5 and forwards it through `0x1801898c0`. Voice/render caller
`0x1801451ea` passes a local copy of `[r12+0x268]`; alternate caller
`0x180144c1f` passes `r12+0x18` under its flag, and `0x18017da06` can pass a
local zero slot. These are exact key-slot callsites, but they do not prove
equality with the manager serial. A complete selected-build `AkSoundEngine.dll`
direct-offset/overlap audit found one source-state `+0x268` writer:
`0x1800d2055` copies config `+0x34` into the source-state object. Exact-offset
stores at `0x18008668c` and `0x1800ac3bf` copy larger structures,
`0x1800ae238` clears an `e38`-sized container, and `0x18012d0fe` initializes a
separate `0x310`-byte object; overlapping 16-byte zero stores at
`0x18022ad9c`, `0x18022b3f5`, and `0x18022b83a` begin at `+0x264` inside
separately allocated `0x320`-byte auxiliary objects. The other hits are stack
locals or atomic refcount-like fields, so no second direct source-state key
setter was found. The separate `0x1800350d7 -> 0x1800e2cd0` call closes the
static key-to-manager-entry comparison path; runtime match success remains
unobserved.
The serial storage resolves to global `0x180344988`; its only RIP-relative
references in the selected native `.text` are lock-xadd writers at
`0x1800c3414`, `0x1800c3af2`, `0x1800c3e48`, `0x1800c418e`, and `0x1800c443d`,
with no direct RIP-relative read at the source-state constructors. The
source-state value is therefore not statically shown to load from the serial
global.
After provider/decoder preparation, `0x1801b0160` reads the owner `+0x268`
key and registers the active decoder through `0x18013f440` using global slot
`0x1803449d0`, distinct from the source-manager hash slot `0x1803449f8` used
by `0x1800e2cd0`. Its `+0x10` table uses 0x18-byte key/decoder/status
records; teardown `0x180189041 -> 0x18013f290` removes a key+decoder pair.
This joins the source-state key to an active decoder lifetime, not to the
UTF-16 path, `ReadFileEx` request, or PCM buffer.
The source-manager callback branches are also explicit: `0x1800e2820` requires
object flags `+0x60` bit `0x10`, writes cookie/context/key/aux at the resolver
descriptor `+0/+8/+0x10/+0x14`, and invokes `0x1800e19a0` with op `0x10`;
`0x1800e28d0` requires bit `0x20`, builds the stack descriptor at
`+0x20/+0x28/+0x30/+0x34`, invokes the callback with op `0x20`, and stores the
return at manager `+0x48`. The fixed bridge maps op `0x10` to its no-op path
and op `0x20` to the queued callback record. This is callback descriptor
transport only; managed path, opened handle, and PCM ownership remain open.
The adjacent exact-key branches are now bounded too: `0x1800e25f0` requires
entry `+0x60` bit `0x80`, sends entry cookie/context/key/aux to the stored
callback with op `0x80`, and is reached at `0x1800347af`, `0x1800356bf`, and
`0x18003578f`; `0x1800e26f0` requires bit `0x2000`, copies the caller's
0x20-byte-plus-tail payload and invokes op `0x2000` from range-matched caller
`0x18004388b`. The fixed bridge maps op `0x80` to the common queued record and
op `0x2000` to its string-or-generic queued-record builder. These remain
state/notification transports, not file selection, handle opening, or PCM
handoff.
registered-device pump `0x1800bc1e0`
selects the provider through `0x1800ba0e0` and assembles each `0x18`-byte
request descriptor before dispatching the registered-device subobject at
`0x1800bc4a5`. The provider constructed by `0x1800bb160` has primary vtable
`0x1802932e8`, whose active `+0x20` is `0x1800bc660`; the ordinary provider
path can create a chunk/request through `0x1800bb970 -> 0x1800bb8e0`. Its
secondary address point `0x180293260 + 0x20 = 0x1800b8820` is only a provider
field serializer and does not populate the pump's candidate-context or flag
slots. On the accepted ordinary branch, the pump forms descriptor `+0x10` as
the address of `candidate + 0x8` (`lea`, not a dereferenced `[local + 0x8] + 8`);
the carrier's branch-dependent provenance remains unresolved. The
subobject `+0x28/+0x30/+0x38` calls resolve to `0x180024630`,
`0x1800248e4 -> 0x1800248f0`, and `0x180024190` (open/setup/release), not
the later batch-read slots. The same device vtable separately exposes
`+0x58 = 0x180024200`, `+0x60 = 0x180024270` (`ReadFileEx`), and `+0x68 =
0x1800243e0` (`WriteFileEx`) on the primary address point. The active
composite address point retained at stream-manager `+0x428` is `0x18028c020`;
its `+0x28/+0x30/+0x38` slots resolve to `0x180005430` (provider/state
dispatch), `0x180024270` (direct `ReadFileEx`), and `0x1800243e0`
(`WriteFileEx`). The pump therefore makes a static provider-preparation ->
ReadFileEx join. Each batch-read writes only its internal helper at request
`+0x28`; it does not initialize request `+0x18`, so callback ownership remains
upstream. The pump's provider virtual `+0x20` call at `0x1800bc369` passes an
explicit descriptor output slot (`rdx`), candidate context slot (`r8`), and
flag slot (`r9`). The active `0x1800bc660` implementation initializes those
outputs and may call `0x1800bb970 -> 0x1800bb8e0`; the alternate serializer
`0x1800b8820` only writes provider descriptor fields. The state-2 helper
`0x1800b97e0` instead enters the default-I/O filter/deferred callback path and
does not initialize the pump-local context slot. Thus the candidate-carrier
source is a conditional provider-to-request edge, not a closed provider-result
proof.
The same plugin exposes an alternate provider-batch wrapper at `0x180005430`:
it filters provider pointers through `0x180005870` and calls the device
dispatch helper (`0x180024200`). Inside `0x180024270`, the descriptor ABI is
exact: 0x18-byte stride, descriptor `+0` provider object whose `+0x10` is the
`ReadFileEx` handle carrier, and descriptor `+0x10` is the ordinary carrier at
request base `+0x8`. For request base `R`, carrier `+0` is `R+0x8`, carrier
`+0x8` is the byte count at `R+0x10`, carrier `+0x10` is the caller-supplied
buffer/source at `R+0x18`, carrier `+0x18` is the fixed callback
`R+0x20 = 0x1800bf190`, and carrier `+0x28` is the read ring helper at
`R+0x30`. The provider-dispatch-to-active-pump address point calls
`0x180024270` directly after filtering; this closes the active
provider-to-ReadFileEx-to-request-recycle transport without claiming a live
key-to-file or PCM mapping.
Static dataflow now identifies that provider object: `0x1800b9530` allocates
the 0x70-byte state record, and `0x1800b9647` stores `0x1800b92c0` at its
`+0x18` and the owning source object at `+0x20`. Thus `0x180024200`'s provider
callback resolves to `0x1800b92c0 -> 0x1800b8b00`, a queue/state transition,
not the codec stream object's indirect `+0` callback. The source-manager
constructor `0x1800bb160` installs primary vtable `0x1802932e8` at the
0x110-byte allocation base and secondary vtable `0x180293260` at base `+0x90`;
the decoder receives the secondary interface while the request retains the
primary base at `+0x48`. Together with the pump's direct `+0x30 ->
0x180024270` call on address point `0x18028c020`, this closes
provider-to-ReadFileEx-to-request-recycle into the same codec provider
allocation. The selected decoder's caller converts its returned floats to
signed PCM16 in the caller-owned output buffer. The selected Opus descriptor
and the header-recognized generic memory descriptor have resolved `+0` stream
callbacks; remaining edges are any address-taken indirect codec setup, optional
callback initialization, source-state-to-provider path correlation, and live
invocation; fixed-callback provider identity is closed. The direct VoicePlayer
external key-to-copied-descriptor path is statically closed.
Request constructor `0x1800bb8e0` takes a free-list object from stream-manager
`+0x458`, writes request `+0x10/+0x14`, stores caller `r8` at request `+0x18`
as buffer/source, installs fixed callback `0x1800bf190` at `+0x20`, self at
`+0x28`, and the primary provider base at `+0x48`. The pump passes candidate
`+0x8`, so completion `0x1800245b0` loads carrier `+0x18` and tail-jumps to
`0x1800bf190` with `rcx=carrier`; that completion therefore sees the same
provider allocation whose secondary interface at base `+0x90` supplies the
codec queue. Callers `0x1800bbad3` and `0x1800bca20` still supply
branch-specific source/offset inputs to the segment allocator; neither adds a
new stream descriptor beyond the two codec paths resolved above.
The provider-to-decoder handoff is exact for the concrete decoder class:
`0x1801af960` calls provider `+0x78`, then decoder `+0x130`; decoder address
point `0x18029cde8` resolves that slot to `0x1801afc80`, which stores the
provider buffer at decoder `+0x60` and updates `+0x68/+0x6c/+0x70`.
Refill `0x1801afb20 -> 0x1801aebf0` and reset `0x1801af740` release through
provider `+0x80`. This closes buffer ownership into the decoder and joins
ReadFileEx completion/request recycle to the same provider allocation and
queue. The selected decoder's caller converts its returned floats to signed
PCM16 in the caller-owned output buffer. The two statically reached stream
descriptors have resolved callbacks; this section does not identify any
remaining address-taken codec callback/initialization, native key-to-provider
path invocation, or live playback.
Native rows
are execution evidence only; the importer does not claim the native
key-to-provider path or decode mapping until one capture correlates the external
descriptor and opened path with the selected stream callback and resulting
decoded data flow.

The default AnimeStudio type-job mode is `auto`: map-filtered conversion stays
sharded, while broad Story JSON runs in isolated sequential processes. Do not
add a JSON type to map filtering until broad and filtered exports are
byte-diffed. Do not shard JSON export without new measurements; current results
show disk contention rather than a speedup.

Optional DummyDll regeneration is build-specific:

```bat
python -m scripts.animestudio.generate_dummydll --dry-run
python -m scripts.animestudio.generate_dummydll --replace
```

Missing or stale DummyDlls warn and fall back to serialized schemas. Never
reuse native registration addresses across game builds.

## Updates

Updates compare two complete export folders. Pass `OLD NEW`, or configure
`ENDFIELD_PREVIOUS_EXPORT_ROOT` and `ENDFIELD_EXPORT_ROOT` in
`endfield_paths.bat`. A named `OLD` refreshes the cached baseline.
`build_updates.py` calls the reusable `updates_builder/scanner.py` API in
process; the scanner is an internal component rather than a second CLI.

```bat
.\build_updates.bat OLD NEW
.\build_updates.bat OLD NEW --text-only
.\build_updates.bat OLD NEW --no-audio
.\build_updates.bat OLD NEW --exact
python scripts\build_updates.py --refresh-previous-export-baseline
```

The default scan covers WebUI-facing exported text plus image, model, video,
and decoded audio assets. `--text-only` omits all assets, `--no-audio` keeps
other assets, `--exact` hashes contents, and `--full-export-scan` is for broad
audits only.

Pruning is destructive. Preview byte-identical files in the previous export
with `.\build_updates.bat --prune-old --dry-run`; run without `--dry-run` only
when intentionally cleaning that saved previous export. The guard rejects the
current export and repository root.

## Native evidence and source graph

Steps that read `GameAssembly.dll` or `global-metadata.dat` validate the exact
installed build first. Missing or mismatched inputs skip only that step and
leave its published report untouched. Set
`ENDFIELD_REQUIRE_NATIVE_EVIDENCE=1` when an audit must fail hard.

The source graph is rebuilt after semantic views:

```bat
python tools\endfield_source_graph.py build
python tools\endfield_source_graph.py query ID_OR_NAME
python tools\endfield_source_graph.py story STORY_KEY
python tools\endfield_source_graph.py issues --limit 20
```

## Output hygiene

- Generated reports belong in topic directories under `reports/`.
- Reusable conclusions belong in the six topic files under `memory/`.
- Revisitable experiments belong in `scratch/<topic>/<task>/`.
- Disposable intermediates belong in `tmp/<topic>/<run>/` and should be
  removed after validation.
- New maintained scripts must support the WebUI or the Unity character lab;
  otherwise keep them in `scratch/` or `tmp/`.
The same catalog also admits an NPC owner only when one valid `NpcInfoTable`
row has matching non-empty `voActor`/`wwiseId` fields and its
`NpcTemplateGroupTable` `npcNameId`/`templateId` row agrees. Exact actor tokens
must also have one exact current `AudioDialogChannel` key whose typed narrating
and radio Event suffixes agree with that token; then they publish `ownerKind=npc`,
the `npcId`, template id, and actor token. Rows
with duplicate tokens, overlay conflicts, malformed layers, or template
mismatches remain unresolved; generic archetypes are never promoted by name.
Mixed Events retain that identity only on their callback occurrence/Clip rows,
not as a single Event owner. This does not prove CharacterTable identity,
Animator execution, playback, or audibility.
