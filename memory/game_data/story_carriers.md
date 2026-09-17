# Story activation and placement carriers

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, story lane.** What a decoded LevelScript action, Timeline record, or
spatial carrier actually owns, reaches, and places -- and the exact-build native
gate and overlay rules that bound every such claim. The Story reconstruction
model these carriers feed, and everything about presenting the result, is
[`../webui/story_recovery.md`](../webui/story_recovery.md).

## LevelScript, Timeline, and native evidence

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

## Spatial carriers

Story may be placed on Map only through the exact carrier's own authored
geometry or identity. Maintained carrier families include validated trigger
volumes, constant EntityPtr targets, explicit entity lists, patrol checkpoints,
SpawnerPtr/encounter hosts, NPC proxy dialogs and envTalk, atmospheric NPC
clusters, narrative components, reading points, and exact 3D radio actions.

Each family has its own schema and uniqueness gate. These rules are shared:

- every constant or getter field is decoded in formatter order and bounded by
  exact consumption;
- dynamic blackboard values, runtime lists, nullable outputs, validation
  predicates, sibling actions, mission context, and proximity never substitute
  for the carrier identity;
- one Story may have several exact authored points; do not choose, average, or
  collapse them;
- placement does not prove activation, mission ownership, runtime actor
  position, or chronology;
- changing per-level carrier coverage belongs in generated frontier and map
  reports.

## What each carrier's identity domain is

Two carriers can address numerically equal ids in unrelated domains, so the
domain is part of the identity:

- validated local Story trigger volumes carry their own decoded Box/Sphere
  geometry at an authored X/Z position and rotation. Current-build native
  consumers confirm that these ids address the LevelScript-local
  `triggerVolumes` domain through a runtime registered-id bridge; **they are not
  WorldEntityRegistry slots.** Their Story links stay distinct from nominal
  mission context and imply neither mission ownership nor runtime firing.
- MissionArea pins have an exact MissionAreaTable Box/Sphere definition and
  remain **Story-unresolved.** Spatial proximity never supplies their Story
  files or Story order.
- NPC proxy rows use their own identity domain. A build-locked `NpcProxyGetter`
  reference can attach actions through an exact proxy-id/segment/table join; it
  **never reuses a numerically equal world-entity identity.**
- current-script slot actions resolve through a pinned native resolver
  contract: the runtime lookup is keyed by the current `LevelScriptRuntime`
  script id and slot in `EntityManager`. A unique WorldEntityRegistry
  script/slot row proves the authored map target, while **runtime registration
  and lifetime remain explicitly unproven.**
- world scenery receives a Story link when one counted `LevelInteractiveData`
  record stores both its exact `embeddedLogicId` and a NarrativeComponent
  `typeId`. e0m0's four tombs use that direct binding, **not numeric order or
  spatial proximity.**

## Registered shells and slot action bindings

- An `int_empty` shell is a registered but unresolved empty slot. It is not an
  understood interaction, and it stays in its own unresolved layer.
- A registered shell referenced by a strict constant `Param<EntityPtr>` value
  inside a validated action record becomes a script target **only when a
  build-locked native formatter contract also proves its named member
  boundary**; unresolved occurrences remain candidates. Neither form inherits
  sibling Story, cutscene, or sequence ownership.
- Script-container files, conditions, and ordering anchors are map-level
  context. They are not repeated onto every sibling slot, and a point receives
  a Story or a file **only from an exact script/slot consumer.**
- Every spatial world/script registry slot publishes an observational action
  binding status and an action array. `no_reference_observed` means only that
  current decoded LevelScript evidence contains no matching constant pointer;
  **it is not proof that the slot has no action.** Exact and unresolved
  references stay separate even when both address the same slot.
- A dynamic local-output reference becomes a slot action **only when a pinned
  producer contract proves a same-header constant alias**; validated non-alias
  outputs remain unplaced.
- The exhaustive per-slot audit -- every contracted EntityPtr field state,
  diagnostic-only dynamic `idRef`/output/variable references, and the
  non-spatial references that must not become map markers -- belongs in
  `reports/assets/map_recovery/action_binding_index.json`, not here.
