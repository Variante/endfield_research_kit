# MemoryPack: framing status, and how the native formatter is resolved

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 2, cross-lane.** The serialization framework under the gameplay and
level payloads: where each JsonData family's framing stands, how LevelScript,
SkillData and BuffData routes are promoted, and the IL2CPP chain that
identifies which formatter a payload resolves to -- static identity
throughout, never observed execution. Current denominators are in the
generated JsonData, SkillData and BuffData corpus reports; each reader,
validator and gate documents its own layout, evidence tier and non-proofs in
its module docstring, with per-build facts in `scripts/game_data/contracts/`.
Derived-plan EOF closure never substitutes for an independently named
whole-file schema.

## The JsonData registry gate

`python -m scripts.game_data.jsondata_corpus` joins each current JsonData
identity to its export file by path, length and logical MD5 and assigns one
terminal state (vocabulary in its docstring). The last complete gate
authenticated every current file with no unsupported or unclassified
identity: only LevelScriptData, LevelScriptTemplateData and SkillData keep
named partials, BuffData outside its exact cohort has named outer frames, and
every other family is schema decoded. A state is a structural lane, not field
coverage; family gates own cursor, native and semantic claims. A type with a
registered `MemoryPackFormatter` (`SerializeFieldDictionary` and siblings) is
read from that formatter, never from its field list; see
[`codecs/levelscript/action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py).

## JSON-schema and compact-table families

Each reader checks stored order, types and cross-index relations and fails
closed on drift; none proves runtime selection or consumption. Textual JSON
lives in the `scripts/game_data/schemas/` package (GameplayConfig compact and
`$type` tables, text tables, LevelMountPoint, NPC catalogs and PrefabInfo,
GoldCoin, UILevelMapLoadConfig, MissionRuntimeAsset, MapConfig). Binary
tables use `gameplay_compact_binary` (MissionArea, SubGame,
WorldEntityRegistry), `memorypack.tables` (DialogIdTable,
BambooRaftTaskTable), `interactive_binary`, the LevelConfig, NavMesh,
TeleportValidation, AetherEnergyLock and MatrixShockWave `*_binary` readers,
`atmospheric_npc_binary` and `gpu_ui_binary`/`gpu_ui_corpus`. Map marks
([`map_mark_relations.py`](../../scripts/game_data/map_mark_relations.py)):
a registry link needs an exact `markInstId` and equal position, a scene link
also a unique `LevelShortIdTable` scene, and it assigns only that marker.

## LevelData, Interactive, AbilitySystem and AnimationConfig

All are exact stored schemas in the last gate. LevelData's sequential
43-field reader (`leveldata_binary.py`, `codecs/leveldata/`) shares value
codecs with LevelScript and the 14+77+27 NPC row; its fallbacks are named
frames, never full schemas. SpawnerConfig and CharInteractPerform close every
owner. Interactive templates (`memorypack/interactive.py`) take component
tags from the native `BaseComponentData` dispatcher; the 38-member
`Core_AbilitySystemForIntData` refuses positive nested domains rather than
inherit a schema from field names. AnimationConfig and NPC MontageNew resolve
path hashes only through an authenticated `StringPathHash` catalog; the
shader-publication proof is conditional on runtime actor and IFix selection.

## LevelScriptData owner cursor

One generated-order walk (`codecs/levelscript/sequential_owner.py`) reads
members 2..27 after an exact action-map boundary: null (`0xff`), the 20-byte
empty `ActionMapAssetRaw`, or a positive map whose three lists and
`ParamListForGraph` close (`current_action_sequence.py`, then the reviewed
`action_map_layouts.json` nodes). `top_level_prefix` delegates positive
`enemies`, `interactiveLocks`, `interactives`, `modules` and `npcs` to exact
codecs and stops before an unowned positive count. `task_conditions.py`
decodes `taskMap`; a file is exact only when every entry and `triggerVolumes`
end at physical EOF, and a failed entry keeps its first bounded diagnostic.
GameCondition and module tags renumber per build and resolve by type name.
The unique-suffix and first-record lanes stay partial. Rank first stops by
whole files unlocked after every list and the owner tail close, not by raw
union counts, and rerank after each complete gate.

## LevelScript action-map unions

`ActionMapAssetRaw` is the three-list `ActionSerializedMap` (action, getter,
header) plus a one-member `ParamListForGraph`; empty, it closes at root byte
20 (the map alone at byte 15). Templates and Interactive files reuse the same
reader ([template reader](../../scripts/game_data/levelscript_template_binary.py)).
Elements are unions keyed by `(tag, memberCount)` in four separate dispatcher
domains (ActionBase, PureGetter, ActionHeader, nested GameCondition). Tags are
per-build family ranks: name types via `scripts.game_data.levelscript_union_tags`.
`python -m scripts.game_data.levelscript_union_layouts` derives every layout
from setter order at the `direct` tier and returns nothing if a reviewed row
disagrees. Production reads only the reviewed (`exact`) rows of
`codecs/levelscript/action_map_layouts.json` through
[`action_map.py`](../../scripts/game_data/codecs/levelscript/action_map.py),
whose docstring owns wire shape, gate mechanics and non-obvious Param shapes.

One proof pattern covers every route: switch jump and registered wrapper fix
identity; the complete reader and forwarding formatter fix member count,
ordered reads and setters; typed `Param<T>` contexts fix parameter, element
and enum types; ledger-joined source spans replay exactly. That proves stored
fields only, never an action run, event fired, getter value or resolved ID.
Per route: `contracts/levelscript_<route>_native.json`, validator
`python -m scripts.game_data.levelscript_<route>_native` (its docstring holds
stored fields, reached authored forms and non-proofs), sometimes a
`codecs/levelscript/` codec, and an `action_map._required_native_gates` entry.
Promotion: (1) isolated contract, validator, tests; (2) layout row, gate
entry, production replay, clean derivation; (3) whole-owner closure, decided
only by the full JsonData gate (`scripts.game_data.jsondata_corpus`) at
physical EOF. Projections between (2) and (3) are provisional.

## LevelScript route status

- Integrated: every layout row and `_required_native_gates` contract; the
  code is the inventory.
- Step 2, awaiting the next combined gate (the last one predates them):
  ActionBase `0x00DB` FacSetInteractLockedState, `0x04DF`
  ToggleClearScreenButRadioV2, `0x0395` RemoveNPCDialog; ActionHeader
  `0x00DC` OnMapVarChanged and `0x0065` OnEnemyInFight, whose corrected
  projection closes 8 reached owners at EOF and leaves 11 at later unions.
- Step 1 only (no layout row): ActionBase `0x0366` PlayEffectOnNpc (not the
  integrated `0x0367` PlayEffectOnNpcProxy), `0x002B` BlockBattleMusic,
  `0x002A` BlockAutoMusicChangeCancel.
- `SetAudioCueVar.Execute`: build-independent claims contract
  `levelscript_audio_cue_execute_claims.json` (validator
  `levelscript_audio_cue_execute_native`) proves ordered call sites only.

## LevelScript route-specific conclusions

- A path/ID-sourced Param's constant slot is a placeholder: often
  `BoolCompare`'s first operand, and every reached `EventArgsAssignFloat`
  `EventArgsPtr`.
- `PlayFmvAction.beforeMask` is `Param<bool>`; names never decide wire types.
  `SendLuaEvent1` reads a seven-member inner value, bypassing its setter.
- Widths vary (`AudioBlackScreenBehaviour` enums byte-backed, most Int32);
  action `Param<GameplayTag>` is a raw int32; short `LevelScriptPtr` IDs
  frame exactly like long ones.

## BuffData

The 30-member root readers (`memorypack/buff.py`, `buff_actions.py`,
`buff_residual_actions.py`, `buff_icon_config.py`, and the top-level
`buff_frontiers_native.py`) give every file a named outer frame, but `memorypack/buff_named_schema.py`
keeps nested action, positive `stackEffects` and timeline bodies opaque. A
whole schema needs a forward receipt from byte 0 through all 30 fields, `id`
equal to the source stem and physical EOF: `buff_root_no_positive`
(empty-list, narrow blackboard/globalModifier, and positive-damage roots whose
conditions and processors each have a selected receipt) or
`buff_create_action_root_receipt` (a sole `CreateBuffAction`); JsonData
replays it. The isolated gradual positive-damage work leaves the canonical
exact set unchanged. Child receipts name direct members only; strings, flags
and value bits stay raw. Tag meanings are local to the Buff dispatcher.

## SkillData

SkillData is one 48-member object: field 0 `ActionGroupData`, fields 1-42
read by a sequential reader derived from the generated wrapper types, and a
five-member terminal (fields 43-47). A gated immediate-registration site joins
the Core `ReadValue<T>` key to `GenericMemoryPackFormatter`. That is static
adapter identity, not executed registration or active dispatch
(`scripts/game_data/il2cpp/context_audit_skilldata.py`). Promotion climbs from
exact action to exact timeline record, whole ActionGroup, then whole file
(fields 1-42 plus the selected terminal at physical EOF). A lower rung never
counts as a higher one.

Per-tag layouts live in code, one reader per route:
`scripts/game_data/memorypack/skill_timeline_*.py` for actions,
`skill_selector_*.py` for nested selectors (their own switch tables), and
`skill_timeline_shared_sequence.py`, whose composite contract also admits
routes reused from reviewed Buff readers. Each route's contract pins the
dispatcher, reader body, source calls and generic contexts. Readers check
every reached union tag and member-count byte. Nested children
(`skill_selector_postprocessor_convert_to_slot`, `skill_selector_zero_member`
-- where `FF` is not a zero header -- `skill_damage_unit_gameplay_tag_list`,
`skill_timeline_two_*`) are admitted only where reached. All of it is stored
framing only. Gate: `python -m scripts.game_data.memorypack.skill_corpus`.

**Static limit.** Rows with no content-bound prior receipt (files added by the
newer VFS overlay) have two terminal framings that both parse exactly to EOF.
The native field-43 bool and field-44 `GameplayTagList` header favor the
earlier one only conditionally on the ordinary formatter/provider route, and
static evidence cannot observe provider choice or the executed cursor. The
subset rebind carries a prior live selection only to logically identical rows,
so new rows stayed `ambiguous` until the live target-set capture. The capture
is gated by `il2cpp.skill_cursor_native_context` and
`il2cpp.skill_cursor_target_set_context`, verified by
`skill_cursor_capture_target_set` and promoted by
`skill_cursor_target_set_overlay`. Those docstrings own the provenance chain,
the rebuild order after a reader change, and the capture procedure.

Historical export-backed censuses do not establish current VFS coverage;
`memorypack.skill_corpus` starts from the authenticated ledger and stream
bytes, and a unique EOF candidate is unique only within its grammar.

## SkillData live cursor evidence

The live SkillData capture (session `20260928T005315Z`) is complete and
loss-free. The strict target-set verifier confirms every requested target
plus the positive control, so that set needs no further capture. Every
witnessed source reads the earlier one-member terminal: field 43
`switchToCenterBeforeCast` through field 47 `useAIExclusiveFrame` at EOF. The
full sweep promoted every formerly ambiguous target-set source to whole-schema
exact. A live cursor selects stored cursor positions for one exact source:
terminal candidate, field vector and ActionGroup child checkpoints
(`skill_cursor_receipt`). It does not name a populated ActionGroup interior,
choose a provider, show a gameplay branch, or give any action semantics.
Purrche's parent `IfElseAction` puts the base combo ability-range source in
the fail branch of `potential_3 >= 1`. The below-Potential-3 branch was
unavailable on the user's save: its stored source and native logic are
recovered, but its execution is unobserved.

## Resolving the native formatter

Each step is `direct` static evidence, never the live formatter, cache, cursor
or EOF; `il2cpp.context_audit` checks it, and each report `boundary` says what.

1. Registration is a pointer array of 16-byte records; `GetFormatter<T>`'s
   parameter belongs to `ReadValue<T>` (`il2cpp.context`).
2. The MVAR leaf ordinal indexes the method-inst vector; modules join by
   unique image name; usage cells resolve via the lazy MethodSpec resolver.
3. The cache is seeded from the registration and compares only the tag plus
   one flag bit. RGCTX slots are not module entries. Never put shared
   object/object arguments into the companion's class context.
4. Setter order is the wire order: generated setters, inherited first, never
   `fields_for` (`memorypack.wrapper_members`).
5. `memorypack.action_dispatcher` walks every AbilityActionData tag;
   `memorypack.union_subtypes` orders nested unions (`structuralOnly`).
6. A body is tag, member-count header, members. The opt-in `derived_*`
   modules fail closed; a plan-only tag is self-consistent, not proven.

## Wire rules every reader relies on

Owners: `memorypack.derived_schema`, `memorypack.wrapper_members`,
`il2cpp.context_audit_memorypack`.

- `List<T>` elements carry a header or `FF`; unmanaged `T[]` is packed raw.
- A struct is its aligned size; a union base is abstract without `Deserialize`.
- Maps are a count plus pairs, padded only when both sides are unmanaged.
- The wrapper reader takes one header byte; `ListFormatter` compares its
  signed count with the remaining bytes, unscaled.
- The `FF` peek consumes one byte; other elements convert through
  `IMemoryPackDeSerializeWrapper<T0>`, so output width is not consumption.
- The provider takes a companion, not the reader; its caches are stateful.
- Cursor state is never an EOF test; no caller compares consumption.
- The formatter-check carrier's last 16 bytes are opaque.

## Recovery acceleration

- `native_union_atlas` checks every union contract in one native context
  with family-qualified tags; publication still needs full corpus gates.
- A Skill replay cache keyed by `dependency_snapshot` reproduces warm and miss
  rows faster, but it is a prototype: changed bytes need a fresh stream, and
  admitting a route can change old bounded rows.

## Eliminated readings

Each line is a reading that was tested and refused; the owning module's
docstring keeps the refuting test.

**JsonData families and tables**

- `SerializeFieldDictionary` header as map count; `MapMarkTempTable` key
  always equal to `markInfoId`; marker group key as scene or level.
- UID-shaped bytes or an audio-map scan as extents; TriggerZone owning a
  later audio-key map; one tag number reused across union families.
- Buff: one-byte `FF` as `0x00FF`; anonymous first `globalModifier` member;
  compact-stacking EOF as ownership; shifted `tagsAfterTriggerExtendBuffAction`.
- Quest state `1`; `0x04B1` as `StopLevelSeqLoopSegment`; `AirWallPtr` as
  `EntityPtr`; `StartLevelCustomPerformance` bool as always present.
- `posList` as three floats; `preWarnEffectFixedRotation` as four floats;
  AnimationConfig offset 62 as `montages`; bulk `FKeyframe` in wrapper order;
  `npcMontages` tags as 64-bit; MontageNew 20-byte vectors; `renderNodes`
  count equal to `nodeCount`; a corpus enum subset for component keys.

**LevelScript unions**

- Byte-7 action-map framing (first list count only); a terminal template ID
  making earlier bytes exact; a child layout guessed from member count or
  position; an outer `WaitForCondition` licensing a nested-condition parse;
  merging dispatcher domains on identical scalar layouts.
- All-EOF `0x00DC`/`0x0065` projections: a scratch counter bug.

**SkillData**

- A one-byte-later terminal (refused by the native field-43 bool and every
  live cursor); EOF validity or another source's witness as a terminal
  selector; promotion by derived-plan EOF, a same-tag layout, or a tag only
  the Buff reader admits.
- A diagnostic integer as a physical tag without a failed union-tag check;
  `FA FF 00` (`0x00FF`) as null; `BoneAttachAction` `0x0000` as a sentinel;
  `CheckSuperArmor` tail anomalies as offset errors (later bytes select other
  routes).
- SkillAIMove `markerInfo` as a wrapper call (it is an eight-byte unmanaged
  copy); `TeleportPosSelectAction` as an alias of `TeleportAction`; Buff's
  compact selector-tag or handwritten tag/member-count tables applied to Skill.
- A PlayAnimation prefix outranking a complete shared-sequence profile; broad
  catches that dropped later refusals; per-build RVAs or method indexes in
  Python as identity; file bytes for virtual-only PE globals.

**Formatter identity and wire framing**

- Identity: the `GetFormatter<T>` counterexample (a probe indirection bug);
  `table + i*16` as a record address; byte equality with `System.Object`
  selecting a shared body; all switch-table pins as one union; reviewed rows
  joined by tag across unions instead of by type name.
- Types: declaration order as wire order; nested-union tags in ordinal order;
  a subclass making a type a union; a memberless wrapper as unresolvable; an
  enum's base as `System.ValueType` or every enum as four bytes; a struct as
  the sum of its member widths; a four-byte output slot as a serialized width.
- Framing: one framing for list and array elements; a counted map with a
  managed side as unreadable; a short `ForceSyncAnimData` header (cursor
  drift); a depth limit of 24 or an empty (falsy) `PlanRegistry` as a
  schema signal; the reference census counting more than nested `skillId`;
  `MissionRuntimeAsset` payloads as MemoryPack (they are JSON).

## Remaining gaps

The ordered queue across families is in
[`../game_data_recovery.md`](../game_data_recovery.md); these are the open
items this topic owns.

- **LevelScript.** The gate rerun, first-stop leaders and route integration
  order are item 1 of the queue;
  [`levelscript_first_stop_census.py`](../../scripts/game_data/levelscript_first_stop_census.py)
  reruns the owner over the JsonData receipt's partial files and ranks first
  stops by whole files. Unsupported values: positive
  `PosRot`/`GameplayTag`/`BuffPtr`
  list elements, non-null `CameraControllerBase` and target-script values,
  non-constant patrol `EntityPtr`, positive dynamic AI blackboards, camera
  poses and curve keys; `SendLuaEvent2` is unobserved; partial templates stop
  at unreviewed unions.
- **BuffData.** The gradual positive-damage branch (queue item 2); the
  remaining sword root; positive `attributeModifier`; timeline, `stackEffects` and
  `buffEventAction` interiors; string parity.
- **SkillData.** The bounded-partial residue stops at mostly distinct action
  tags with one or two files each, so LevelScript routes have better
  immediate yield. Open grammars: FindTarget nested tags `0x02`/`0x03`, the
  85-member `EffectActionCfg` body, DamageAction variants and `DamageUnit`
  member 33, CameraImpulse's nested actions. No cursor receipt names a
  populated ActionGroup interior; a terminal proof cannot fill an earlier
  child.
- **Formatter and runtime.** Registration history and the outer
  provider/cache path are unjoined; provider selection, live formatter/cache
  contents and substitution are unobserved; the DamageUnit tag-list and
  `CheckSkillType` list providers stay conditional. Nested-union tags stay
  `structuralOnly` until their tables are walked, and each plan-only tag needs
  a whole-corpus adoption run. `Dictionary<string, object>` has no plan.
- **Tooling.** Dependency-scoped Skill replay needs a route registry and
  mutation tests before it leaves prototype. CharInteractPerform's
  `FAnimationCurve` now shares AnimationConfig's proven bulk-key reader; no
  current custom curve has positive keys to exercise it in that family.
