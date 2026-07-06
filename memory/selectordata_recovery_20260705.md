# SelectorData / FindTargetAction Full Recovery - 2026-07-05

## Result

`Beyond.Gameplay.Core.Selector+SelectorData` (and the `TargetSettings` /
`DirectionSettings` variants around it) **is self-delimiting** under the layout
proven below. `scripts/build_data_index.py` now has a full byte-proven forward
parser for `FindTargetAction` (tag `0x009f`) and `ContinuousFindTargetAction`
(tag `0x007c`), registered both for single-item exact decode and for
multi-action chain consumption. Every FindTargetAction occurrence in the
current BuffData corpus decodes `exact`; no selector-related ambiguity remains.

BuffData decode scan (per root, StreamingAssets == Persistent), before -> after:

| metric | before | after |
|---|---|---|
| typed-chain-items records | 14 | 20 |
| ambiguous-union-tag-boundaries records | 54 | 48 |
| single-item records | 263 | 263 |
| empty records | 7 | 7 |
| item exact | 17 | 61 |
| item partial | 185+6=191 | 185 |
| item opaque | 95 | 93 |
| typed decoder failures | 0 | 0 |
| FindTargetAction items | 20 partial + opaque | 31 exact + 2 Continuous exact, 0 partial/opaque |

All 48 remaining ambiguous records are blocked by OTHER action families
(FinishBuffAdvanced, CheckBuffStackNumAdvanced, HitStopAction, SpawnEnemyAction,
LockCameraAim, TimeDilation, unknown first-tags 0x0056/0x0062/0x0075/0x007a/
0x0086/0x0097/0x00d3, createBuff reservedU32, effectAction tail-u32) — zero are
blocked by SelectorData anymore.

## Proven layout (the actual discovery)

The local MemoryPack dialect for these types:

1. **Object** = 1-byte member-count header (must equal the serialized member
   count) or `0xFF` null. **List** = u32 count (`0xFFFFFFFF` null) + elements.
   **String** = u32 byte length (`0xFFFFFFFF` null) + UTF-8.
2. **Member order = base-class members first, each class level sorted
   alphabetically (ordinal) by member name.** This matches the generated
   `*ForMemoryPack` wrapper member sets and the GameAssembly `Deserialize`
   setter call order (which is alphabetical in every audited body). It is NOT
   IL2CPP field-token order.
3. **Union member** = `0xFF` null, else 1-byte tag (selector formatter cctor
   tables in `reports/mission_order/selector_formatter_tag_audit.json`), then
   the payload object with its own member-count header. Payload header must
   equal the subtype's total serialized member count including base classes
   (e.g. `HitBoxFinder+Data` = 8: 5 inherited from `TargetFinder+Data` + 3 own).
4. Key composite types (all byte-proven):
   - `FindTargetActionData` (item member count 18 = 4 prefix + 14 body):
     prefix `isEnable,priorityLevel,priorityOffset,serverActionIndex`; body
     `advancedSelectorDirection(DirectionSettings), center(i32),
     centerContextKey(str), centerMountPoint(i32), centerToGround(bool),
     contextKey(str), selectorData, selectorDirection(i32), selectorOwner(i32),
     selectorOwnerContextKey(str), target(i32), targetGroupKey(str),
     useAdvancedDirectionSetting(bool), useCenterEntityMountPoint(bool)`.
     `ContinuousFindTargetAction.Data` appends `findInterval(f32)` (19 members).
   - `SelectorData` (3): `finderData` union, `postProcessorData`
     List<union>, `validatorData` List<union> — in that (alphabetical) order.
   - `TargetSettings` (13): `advancedDirection, centerContextKey,
     centerToGround, centerType, enableAdvancedDirection, ownerContextKey,
     selectorData, selectorDirection, selectorOwner, target, targetContextKey,
     targetGroupKey, targetSource` (static `Default` not serialized).
   - `DirectionSettings` (8): `clampToXZ, customSourceAndTarget,
     directionType(i32), invertDirection, source(TargetSettings),
     sourceMountPoint(i32), target(TargetSettings), targetMountPoint(i32)`.
     NOTE: the pre-existing partial decoder's "directionType raw 1" was really
     `clampToXZ=1, customSourceAndTarget=0, dirType bytes 0-1`; mount points are
     4-byte enums (setter stores are 4-byte, byte-proven).
   - `BlackboardParam<T>` (metadata `Beyond.Blackboard+BlackboardParamBase\`2`,
     type-pool 175183 float / 175186 int) (3): `blackboardKey(str),
     useBlackboardKey(bool), value(4B)`. `BlackboardVector3` (175196) (3):
     x/y/z each a BlackboardParam<float>.
   - `HitBoxFinder+ShapeData` (18, alphabetical): `angle(bbp),
     castDirection(i32), centerOffset(bbv3), dirRefMountPoint(i32),
     directionRef(i32), enablePreview(bool), eulerAngle(bbv3), height(bbp),
     hitEffectTowardsType(i32), limitAngle(bool), limitHeight(bool),
     maxHeight(bbp), posRefMP(i32), positionRef(i32), radius(bbp),
     shapeType(i32), size(bbv3), useDirection(bool)`. `shapeList`/`boxShape`
     (pool 65441) = List<ShapeData>.
   - `GameplayTag` (2): `tagId(i32 hash), tagName(str)`; `GameplayTagQuery`
     (pool 135488) (2): `queryType(i32), tags(List<GameplayTag>)` — used by
     `TagValidator.query` and `OwnerPartsFinder.partQuery`.
   - `BuffFindSettings` (3): `buffIdList(List<i32>), checkType(i32),
     tagQuery(GameplayTagQuery)`; `SmartTargetSelectSetting` (4):
     `smartTargetBuffFindSettings(BuffFindSettings), smartTargetBuffIds(List<i32>),
     smartTargetSelectStrategy(i32), smartTargetTagQuery(GameplayTagQuery)`.
5. Type-pool index equivalences resolved via cross-type field usage in
   metadata: 155804=float, 130467=double, 161412=Vector3(12B),
   150805=Quaternion(16B), 142445=LayerMask(4B), 157146=string, 123940=bool.

Selector subtype schemas live in `BUFF_SELECTOR_FINDER_SUBTYPES` /
`BUFF_SELECTOR_VALIDATOR_SUBTYPES` / `BUFF_SELECTOR_POSTPROCESSOR_SUBTYPES` in
`scripts/build_data_index.py`. Subtypes byte-validated in real data:
CharacterTeamFinder, HitBoxFinder(+TargetFinder base), OwnerSpawnedEntityFinder,
OwnerPartsFinder, RandomPointFinder, SmartTargetFinder, MainCharacterValidator,
TagValidator, DistanceValidator. The rest are registered from wrapper member
sets + resolved field widths and are guarded by the member-count header check.

## Fail-closed guards

- Unknown selector union tag, wide tag (0xFA), or a subtype marked
  layout-unproven raises (`BuffSelectorSubtypeUnproven`), so chain walkers keep
  records `ambiguous` and single items fall back to the previous partial
  decoder — no warning is ever suppressed without a full parse.
- Single-item exact decode additionally requires landing exactly on the proven
  item end; otherwise the old partial output is preserved unchanged.
- Object headers must equal expected serialized member counts; bools must be
  0/1; strings strict UTF-8/no control chars; lists capped at 256; selector
  recursion capped at depth 8.

## Still-unproven subtype layouts (intentionally fail-closed)

- `ShapeFinder+Data` (finder 0x0e): `shapeData` field is pool 127178 ("battle
  shape data", shared with AuraAction/CreateAdditionalBattleShape/
  DynamicTriggerInput). Never observed in decodable BuffData.
- `PriorityFilter+Data` (postProcessor 0x06): `buffFilterSettings` pool 124100
  — probably `List<BuffFindSettings>` (single BuffFindSettings = 124103/124104
  cluster) but no sample exists to discriminate. Never observed.
- These are the ONLY remaining selector gaps; both raise cleanly if a future
  game update starts using them.

## Eliminated hypotheses (do not retry)

- IL2CPP field-token order as serialization order: disproven byte-exactly
  (token order puts `targetGroupKey` first; bodies start with
  `advancedSelectorDirection` header 0x08).
- `read_buff_target_settings_envelope_partial` (67-byte envelope) inside
  FindTargetAction middles: 0 candidates (already known; confirmed obsolete —
  the real TargetSettings here is the full 13-member object, and all sampled
  `DirectionSettings.source/target` are null `0xFF`).
- `GameplayTagQuery.tags` as List<string>: disproven (element u32s all ended in
  low byte 0x02 = GameplayTag object header).
- SelectorData members as three single unions, or declaration order
  finder/validator/postProcessor: disproven (validator/postProcessor are lists;
  alphabetical finder/postProcessor/validator is the only order where subtype
  member-count headers validate, e.g. `main` sample validator tag 0x07 =
  MainCharacterValidator with 0 members).

## Evidence trail

- `scratch/selectordata_20260705/replay_selectordata.py` — standalone replay
  parser; 24/24 boundary-audit samples consume to their exact proven ends with
  independent tail-field cross-checks (selectorOwner/target/targetGroupKey).
- `scratch/selectordata_20260705/dryrun_patched_scan.py`,
  `probe_remaining_ambiguous.py`, `probe_smarttarget.py` — chain-level
  validation and per-record blocker attribution; scan outputs in the same dir
  (`scan_baseline_20260705.txt`, `scan_promoted_20260705.txt`).
- `scratch/selectordata_20260705/dump_selector_type_fields.py`,
  `dump_wrappers.py`, `dump_shapedata_provider.py`, `dump_tagquery.py` — IL2CPP
  metadata field lists, wrapper member sets, and type-pool index resolution.
- Semantic sanity checks: `findInterval=0.1` on Continuous items; RandomPoint
  blackboard keys `ballNum`/`minRadius`/`maxRadius` bind alphabetically to
  `pointNum`/`minRadius`/`radius`; SmartTargetFinder decodes tag
  `Skill/Character/chr_0030_zhuangfy/SwordTar` with strategy 3 = SelectByTag
  and a DistanceValidator(<=12).

## Validation

- `python -m py_compile scripts\build_data_index.py` passed.
- Full Json build `tmp\game_data_index_selectordata_validate_20260705`
  (see summary below in this note's Validation follow-up).
- Direct BuffData decode scan before/after as tabled above; zero typed decoder
  failures in both.

## Remaining Frontier

- BuffData chains: the 48 ambiguous records per root need consumers for other
  action families (top: FinishBuffAdvanced 6, CheckBuffStackNumAdvanced 6,
  unknown-tag 0x0056 x7, HitStopAction 3, SpawnEnemyAction 3, 0x00d3 x3).
  FindTargetAction/SelectorData is no longer the blocker anywhere.
- `reports/mission_order/findtarget_selector_boundary_audit.*` is now stale by
  design (it measured the pre-promotion opaque middles); regenerate only if a
  fresh gate measurement is needed — decoded items no longer expose
  `bodyMiddleOpaque`.
- MonoBehaviour TypeTree side (74 partial SelectorData/TargetSettings refs in
  CharacterTemplateData groups) was NOT touched: the TypeTree serializer is a
  different format from MemoryPack; the byte proof here does not transfer
  directly. The subtype member lists/orders recovered here are still the right
  schema input if that work is attempted.
