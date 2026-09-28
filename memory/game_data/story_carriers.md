# Story activation and placement carriers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, story lane.** What a decoded LevelScript action, Timeline record, or
spatial carrier actually owns, reaches, and places -- and the exact-build native
gate and overlay rules that bound every such claim. The Story reconstruction
model these carriers feed, and everything about presenting the result, is
[`../webui/story_recovery.md`](../webui/story_recovery.md).

## LevelScript, Timeline, and native evidence

Selected LevelScript actions prove Story links under explicit gates. That
covers the carriers Story reads, not the whole LevelScript family.

- LevelScript actions, headers, UIDs, callbacks, lists, and target carriers are
  accepted only through versioned parsers and bounded validation.
- Active evidence uses one logical-path overlay. Persistent replaces the
  complete StreamingAssets file; changed shadow data is decoded from active
  bytes or rejected.
- A direct playback carrier requires one typed header-to-action path. Preload,
  load, stop, sibling actions, foreign headers, unresolved graph shapes, and
  raw numeric hits remain diagnostics.
- CallServer ordering requires one complete linear Story-to-callback-to-Story
  closure with no branch, merge, loop, truncation, or ambiguous target. A
  one-sided path adds no cross-Story edge.
- Timeline track/clip ownership proves authored scheduling, not Director
  activation, selected option, or Wwise playback.
- Native evidence is locked to exact `GameAssembly.dll` and metadata hashes.
  Registration order and code addresses never imply Story order.

## Native claims across a client update

- A contract records its build in its own `nativeInputs`/`sources`; no module
  repeats that hash. On another build it reports `mismatched` until the claim
  is proved again, and only names carry over: addresses, tokens, offsets,
  registers and enum values are re-derived, and code registration is located
  from the metadata image names, never pinned.
- Claims that re-prove from the binary have a regenerator (CallServer callback,
  cutscene case resolution, iFix patch, cinematic queue, TeleportParam). Census
  conclusions (identity-carrier negative boundaries, cross-system consumers)
  have none and stay `mismatched` until reviewed again.
- Instruction-shape analyses must survive codegen churn. The current build
  wraps many methods in an iFix patch-flag test, moves rare paths into
  separate `.pdata` fragments, calls unnamed helpers (struct-argument shims,
  inlined copies of named methods), reallocates saved registers, and widens
  short jumps to rel32 `jcc`. A body is the function plus every fragment
  chained to it by `UNW_FLAG_CHAININFO` (`BodyIndex.chained_fragments` in
  `scripts/game_data/il2cpp/body_claims.py`), however reached; a jump-target
  walk misses fragment-to-fragment edges. Follow one level into an unnamed
  helper, name a jump from its opcode, accept any save/restore register pair,
  and label a helper-reached callee as such. Compiler-generated names
  (`<M>d__N`, `<>c__DisplayClassN_M`, `b__N_M`) renumber between builds; match
  them with the ordinal normalized, and only when unique.
- An iFix wrapper may test its patch id after a class-init prologue, so an
  opening-window miss does not prove it absent. The inlined
  `TaskCondition.InvokeOnIsCompleteChangeAction` escapes a hook on the named
  method (`scripts/game_data/mission_task_paths_native.py`).
- `withinActiveArea` is hysteresis, proved from `_CalcWithinAreaHysteresis`:
  `!rangeSensitive || hit(enterShapes) || (prevWithin &&
  !IsNullOrEmpty(exitShapes) && hit(exitShapes))`. The outside list is a hold
  zone, not an exclusion zone ("outside hit clears" was the previous build).
  The inlined call site is tied to it `conditional`ly (`protocol_registry.py`).
- Consumer meanings the Story builders cite are claims about named bodies
  proved on the installed build (`contracts/story_native_consumers.json`,
  `contracts/dialog_finish_native.json`), not pinned tokens. The current
  DialogTreeIfNode, Timeline option-index (a wider current-or-previous gate)
  and `Branch.Execute` order readings are in
  [`story_native_consumers_native.py`](../../scripts/game_data/story_native_consumers_native.py).
- A generated artifact made on one build is current only when its recorded
  native hashes equal the installed build's. The reverse-PPtr audit (Story
  root playback aliases) and `webui/story/dynamic_scene.json` were made on the
  previous build and publish nothing until regenerated. The reverse audit
  regenerates through `scripts.webui.story_recovery.audit_story_objects` after
  an export published with `--animestudio-object-index`; `dynamic_scene.json`
  has no generator (see `scripts/webui/story/dynamic_scene.py`).
- Mission Pipeline `RUNTIME_CONTRACT` rows are re-verified by name each run
  (`scripts/webui/mission_pipeline/runtime_contract_native.py`); a row whose
  chain no longer holds is `link_failed` and needs a fresh reading, not a pin.

## Current mission JsonData carrier boundary

The selected VFS ledger and exported `game/Json` bytes agree for the active
LevelScriptData, LevelData, LevelConfig, SpawnerConfig and MissionRuntimeAsset
families; that direct comparison is needed because the export lacks
per-output provenance, so `verify_export_freshness` alone cannot authenticate
every file's content.

- Changed LevelScriptData, LevelData and SpawnerConfig files close at physical
  EOF with `levelscript_binary.frame_levelscript_declared_root` and declarations
  derived from the matching installed native build: the byte boundary is
  complete, member names stay `direct`. Changed LevelConfig files close under
  `decode_level_config`. Both MissionRuntimeAsset main and meta sets pass their
  named schema readers (`scripts/game_data/schemas/mission_runtime_main.py`);
  the main contract's `currentCorpus` header still identifies the older
  reviewed baseline and is not a current-corpus gate.
- The source path chain is LevelConfig's signed `levelDataPaths` int64 -> the
  authenticated `StringPathHash.bin` bucket/path-offset pair -> active LevelData
  logical path. LevelData `levelScriptBriefDataDict` stores a `dataPath.hash`;
  a unique catalog path plus equality of its dictionary key, embedded
  `scriptId` and LevelScriptData filename stem proves that script reference.
  `spawners[].configId` matches the SpawnerConfig root `configId` and path.
  These are JsonData source-path and typed-id joins; Unity CAB/PathID identity
  applies only when crossing into serialized Unity objects, and a filename
  resemblance alone is insufficient.
- Mission name and description keys resolve directly in the byte-verified
  `TextTable`; matching Dialog prefixes are candidates until a typed
  mission-to-dialog field connects them. A level field, a mission name in a
  LevelData filename, script brief, condition, or `mainPathQuests` array proves
  authored definition or reference, **not** client activation, a server quest
  branch, or a played Story. Producer-to-mission ownership and activation
  order stay unresolved until an exact consumer trace or observed runtime event
  joins them; the source joins never become a Story edge or order on their own.

## LevelScript FMV path to installed Video

`PlayFmvAction._moviePath` is a stored constant `Param<string>`. Each
authenticated `cs_video_*` value resolves to exact Video logical paths under
`Data/Video/PC/Narrative/Cutscene/` -- a base `<id>.usm` or a complete `f_`/`m_`
pair -- through
[`levelscript_fmv_video_corpus.py`](../../scripts/game_data/levelscript_fmv_video_corpus.py)
and the reviewed `levelscript_fmv_video_native.json` consumer route
(`GameAction.PlayFmv` -> `GetGenderedFMVId` -> `Narrative/Cutscene/{0}` ->
VFS lookup). This is **conditional** name resolution: gender, iFix state,
activation, playback, mission ownership and order are not proved. The
per-source join is `reports/story/recovery/current_levelscript_fmv_video_join.json`.

## Spatial carriers

Story is placed on Map only through the exact carrier's own authored geometry
or identity: trigger volumes, constant EntityPtr targets, entity lists, patrol
checkpoints, SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk,
atmospheric NPC clusters, narrative components, reading points, and 3D radio
actions. Each has its own schema and uniqueness gate, under shared rules:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology; per-level coverage belongs in the generated frontier
  and map reports.

## What each carrier's identity domain is

Numerically equal ids in unrelated domains are different identities:

- validated local Story trigger volumes carry their own decoded Box/Sphere
  geometry at an authored X/Z position and rotation. Current-build native
  consumers confirm these ids address the LevelScript-local `triggerVolumes`
  domain through a runtime registered-id bridge; **they are not
  WorldEntityRegistry slots.** Their Story links stay distinct from nominal
  mission context and imply neither mission ownership nor runtime firing.
- MissionArea pins have an exact MissionAreaTable Box/Sphere definition and
  remain **Story-unresolved**; proximity never supplies their Story or order.
- NPC proxy rows use their own domain. A build-locked `NpcProxyGetter` reference
  attaches actions through an exact proxy-id/segment/table join and **never
  reuses a numerically equal world-entity identity.** The unreviewed
  `jumpToCampFireGlobalId` tracking field (by name an optional campfire jump
  target) is accepted only at 0 (`npc_proxy_tracking_fields_are_exact` in
  `scripts/webui/story/source_gap/data.py`); any other value or new field fails
  closed until reviewed.
- current-script slot actions resolve through the pinned
  [`entityptr_script_slot_native.py`](../../scripts/game_data/entityptr_script_slot_native.py)
  contract: the lookup is keyed by the current `LevelScriptRuntime` script id
  and slot in `EntityManager`. A unique WorldEntityRegistry script/slot row
  proves the authored map target; **runtime registration and lifetime stay
  unproven.**
- world scenery receives a Story link when one counted `LevelInteractiveData`
  record stores both its exact `embeddedLogicId` and a NarrativeComponent
  `typeId`. e0m0's four tombs use that direct binding, **not numeric order or
  spatial proximity.**

## Registered shells and slot action bindings

- An `int_empty` shell is a registered, unresolved empty slot in its own layer.
- A registered shell referenced by a strict constant `Param<EntityPtr>` inside
  a validated action record becomes a script target **only when a build-locked
  native formatter contract also proves its named member boundary**
  ([`action_entity_fields_native.py`](../../scripts/game_data/action_entity_fields_native.py));
  unresolved occurrences stay candidates. Neither form inherits sibling Story,
  cutscene, or sequence ownership.
- Script-container files, conditions, and ordering anchors are map-level
  context, not repeated onto sibling slots; a point receives a Story or a file
  **only from an exact script/slot consumer.**
- Every spatial world/script registry slot publishes an observational action
  binding status and action array. `no_reference_observed` means only that
  current decoded LevelScript evidence has no matching constant pointer --
  **not that the slot has no action.** Exact and unresolved references stay
  separate even when both address the same slot.
- A dynamic local-output reference becomes a slot action **only when a pinned
  producer contract proves a same-header constant alias**
  ([`entityptr_output_alias_native.py`](../../scripts/game_data/entityptr_output_alias_native.py));
  validated non-alias outputs remain unplaced.
- The exhaustive per-slot audit -- contracted EntityPtr field states,
  diagnostic-only dynamic `idRef`/output/variable references, and non-spatial
  references that must not become map markers -- belongs in
  `reports/assets/map_recovery/action_binding_index.json`.
