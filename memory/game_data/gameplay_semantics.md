# Gameplay: Tables, MemoryPack, and the native action contracts

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, gameplay lane.** Where authored `Table` config joins exact MemoryPack
framing and selected native enum contracts to become gameplay meaning.

The per-action layouts are **not** in this file. They live in the tracked
`scripts/game_data/contracts/buff_*_native.json` contracts, one per union tag, plus the
`finder_*`, `validator_*` and `postprocessor_*` contracts beside them. Each
records its own member order, nested profiles, null paths and pinned native
inputs, and each is reviewable and diffable in git. For a specific tag, read its
contract. What is durable here and nowhere else is the root framing, the reading
rules every contract shares, and what stays unresolved for all of them.

## What gameplay recovery joins

Gameplay recovery joins authored Tables, exact binary/serialized structures,
selected native enum contracts, Assets, Audio, and the curated graph.

- Enemy variants resolve their exact attribute template before stats are shown.
- Authored level points, cooldowns, modifiers, formulas, and Buff actions are
  preserved as source values. Final runtime values across other Buffs, IFix,
  equipment, and server state remain uncomputed.
- Action/condition unions publish only the typed prefix or body that consumes
  exactly. Unknown selectors, enums, tags, blackboard operations, and nested
  payloads stay unresolved.

## BuffData's root, and the union encoding

The root is framed forward from byte zero; the per-action bodies hang off it.

- `memorypack.buff_actions` frames `abilityEventAction` forward from
  byte zero under each retained filename-anchor candidate's hard limit. It
  supports the current IfElse/Sequence grammar, the selected member-five child
  profile, nulls and bounded counts, records completed nested spans, and stops
  at the first unsupported union. Atomic spans plus an explicit physical-file
  remainder tile the bytes; **that remainder is opaque, not a decoded record.**
- `buff_root_prefix_native.json` pins root members 2-4 after that first
  collection: scalar payload, directly counted raw DWORD array, then a
  member-two collection profile. The array helper copies four bytes per entry
  with no element header, and the `GameplayTag` type name does not select the
  separate tag-list wrapper grammar. Only a non-null collection has the
  terminal byte.
- `buff_root_fifth_native.json` pins the next root collection to a
  `List<DataPair>` context: member-four elements read a byte, a signed nullable
  byte payload, eight raw bytes, then another nullable payload. The eight-byte
  load is independently pinned -- do not reuse the scalar profile's four-byte
  value, and do not read the leading byte as a union tag.
- `buff_root_sixth_native.json` pins the following `List<BuffActionMap>`: FF or
  member two, a nullable Sequence array, then a required inline DWORD. This
  **reverses** the first collection's scalar/array order, so equal member counts
  do not make the maps interchangeable.
- Generated current wrapper order assigns those six cursor ranges to
  `abilityEventAction`, `addingCooldown`, `applyTags`, `attributeModifier`,
  `blackboard`, and `buffEventAction`. This names storage order; it does not
  assign action behavior.
- The selected-build `memorypack.derived_plans`/`derived_values` route now
  decodes each current `BuffData` and `SkillData` whole record to EOF. That is
  a separate, stronger route than the bounded legacy action and middle/suffix
  readers below. It exposes nested typed PlaySound actions inside the full
  authored tree; their trigger-slot and Audio boundary is described in
  [`audio_naming_coverage.md`](audio_naming_coverage.md).
- `frame_buff_named_middle` reads positive damage and heal modifier lists in
  current generated wrapper order. Damage items read condition, processor list,
  then enable-side storage; heal items read condition, enable-side storage,
  then processor list. Damage processor routes 0 and 9 and both heal routes
  present in the current corpus have exact bounded profiles. Other damage
  processor tags and unsupported condition actions stop at their first tag.
  The reader consumes the exact raw-eight `dispelConfig` representation and
  leaves the 19-member `iconConfig` body as one named opaque range at the
  accepted `id` marker.
- When that middle cursor reaches the unique accepted marker, the existing
  sequential suffix reader names `id` through `waitFirstTriggerInterval` and
  closes at EOF. Nested icon, modifier, and action bodies retain their own
  weaker evidence even though the outer 30-field frame is closed.
- **Extended unions consume `FA` followed by a little-endian unsigned tag**, and
  reports retain the decoded tag rather than the escape byte. Supporting a
  decoded tag does not admit its reserved single-byte physical encoding: those
  stay unsupported until separately authenticated.
- The recurring action prefix is one byte plus three scalar32 values. It is a
  shared shape, not an identifier: it cannot select which reader applies.

## The rules every contract shares

These are why the catalog was worth keeping as rules rather than as prose. Each
one has been violated at least once and caught.

**On selecting a reader.**

- **Equal member counts never select a layout.** Two tags with the same header
  count routinely have different member orders. Select from an independent
  token/module or registered-type join, never from arity, a managed name, or
  byte length alone.
- **A shared type argument permits profile reuse, not instance merging.**
  Repeated target or scalar contexts are separate serialized instances, each
  with its own bounded profile and null state.
- **Structural equivalence is not shared behavior.** Two tags may share one
  parser branch while keeping distinct union identities and unrelated gameplay
  effects.
- **Do not import legacy tag/name aliases to improve coverage.** Current-build
  routes contradict the legacy reader's tag/name map, and exact byte consumption
  alone does not validate a legacy label.

**On reading order.**

- **Source cursor order, not destination layout.** A field's later object offset
  never moves it later on the wire. Output-side setters, getters, casts, stores
  and cached constructions consume no source bytes and add no members; an
  output-store inventory misses serialized members.
- **Enum and static type contexts identify which helper consumes a scalar.**
  They add no nested header and do not narrow the allowed bits.
- **A normal exit may tail-jump to the write barrier.** Pin the whole
  instruction and the separate null rejoin rather than assuming a `RET`.
  Readers also cross chained unwind regions -- the first `.pdata` end is not a
  record or function end.

**On bounds and null states.**

- **Null, empty, and null-wrapper are three distinct states.** Negative lengths
  below -1 fail closed, and no standard MemoryPack UTF-16 or negative-length
  variant is guessed.
- **A completed child never makes a later required field optional.** Terminal
  bytes and DWORDs stay required even when every preceding profile is null.
- **Lists reserve the remaining minimum tail before iterating**, and count,
  null and loop framing stays conditional on the shared reference-list consumer.
  A provider bridge alone proves neither element width nor runtime selection.
- **An unknown tag or nested union stops in place**, at its own first byte,
  without scanning for a later marker. Unwind depth on failure, retain completed
  children, and leave incomplete parents unrecorded.
- **Raw widths stay anonymous.** A four-byte read keeps four bytes whatever its
  managed name says -- several `Double`-named payloads consume exactly four. A
  vector may be three variable-width scalar payloads rather than twelve raw
  bytes, and only the consumer's own advance decides which.

**On what a name proves.**

- **A managed action, type or enum name establishes nothing** about gameplay
  behavior, numeric units, boolean meaning, ownership, activation roles, or
  runtime execution order. A registered name is an identity, not a semantic.

## What stays unresolved for every action

Recorded once here rather than repeated per tag, because it applies to all of
them:

- **live provider selection** -- a concrete static reader is structural
  evidence, not proof that the formatter executes; selected IfElse paths
  overwrite the callsite companion in native thunks, and reuse reaches
  state-dependent provider dispatch with the same reader and output;
- **legacy bounded-reader suffix ownership for partial rows** -- an
  unsupported action or damage-processor route still leaves a physical gap in
  that reader; only its contiguous named middle plus accepted suffix closes
  that route's outer frame. The selected-build derived whole-record route above
  is independently exact and does not convert a partial legacy row into a
  complete one;
- **field meaning and payload encoding** for anonymous scalars and byte spans,
  and runtime gameplay meaning even when a selected native enum names the
  stored number.

`buff_corpus` publishes a separate prefix success/failure/unsupported/ambiguity
denominator and fails its gate on malformed prefixes even when the suffix
reader succeeds. `memorypack.buff_1b_corpus` joins exact-closed root-continuation
tag `0x1B` records to re-streamed current logical bytes and the selected
`BlowOffAction_Data` reader contract; the continuation profile does not
authenticate root-field ownership. Changing coverage belongs in
`reports/animestudio/buff_1b_current_latest.{json,md}` and the matching
`buff_corpus` report, not here.

The selected-build
[`buff_1b_action_native.json`](../../scripts/game_data/contracts/buff_1b_action_native.json)
contract goes beyond the
anonymous tag layout. Its reader assigns the thirteen `BlowOffAction.Data`
fields after the inherited enable/priority/index prefix in this **source
order**: `attackerTargetSettings`, `blowOffDistance`, `blowOffHeight`,
`deadOption`, `directionAngleOffset`, `directionSettings`,
`distanceRandomRange`, `forceMoveColliderToGround`,
`modelHeightRecoverTime`, `overwriteHeight`, `targetSettings`,
`teammateBigStagger`, `totalTime`. The audit joins each source position to a
direct named setter call and the destination field's selected metadata type
and offset. Six are `BlackboardDouble` profiles and two are `TargetSettings`
profiles; neither managed `Double` names nor destination offsets change their
independently proven source widths. On the selected unpatched
`BlowOffAction.ExecuteInternal` body, a guarded branch directly calls
`ControlledStateComponent.ApplyBlowOff`; the same body also contains target,
state, direction and blackboard processing. This establishes a runtime consumer for the named action,
but not the expression for each field, units, direction convention, target
choice, patch state, live formatter choice or an observed execution. The
native audit fails closed on a different installed pair; its changing result
belongs in `reports/game_data/buff_1b_action_native.json`.

**Recovery queue.** Resolve the remaining damage-processor routes from their
current native union contexts, then close the unsupported condition actions and
the actions reached inside `buffEventAction`; until those close, the remaining
outer frames cannot join the named middle. Decode `iconConfig`'s 19-member body
after those higher-coverage gaps without weakening its current opaque boundary.

## What the published Gameplay datasets establish

The page builder's own evidence limits, which travel with the data rather than
with the command:

The base stage publishes every exact `chr_NNNN_token` identity registered in
`StrIdNumTable`, even when `CharacterTable` has no row. Such namespace-only
records remain visibly evidence-limited and do not claim availability,
progression, runtime use, or playable status; longer skill/Buff/projectile ids
are not promoted to characters.
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

The Audio builder publishes a separate Gameplay sound sidecar from exact
whole-record SkillData/BuffData PlaySound unions. It keeps each raw sound
literal, action path, enclosing frame or Buff/Ability trigger, typed target
settings, and source hash. Selected HIRC Event identity and authored
Skill/Buff/born-Buff owner links are separate gates. A missing native decode,
incomplete family, or invalid HIRC inventory withholds this exact enrichment;
runtime branch activation, target choice, and audibility remain unresolved.

### What a decoded action row may be labelled

A label is allowed only where the contract's own decoding supplies it, and the
refusals below are the ones that were each once assumed instead of read:

- a blackboard calculation row carries the native `HpRatio` type and the
  operation the contract decoded, including `Floor`, `Ceil` and `RoundToInt`.
- `SimpleCalcBBAction` shows its **decoded** operation. Division is not the
  default and was not assumed.
- `CompareFloat` shows the exact blackboard comparison; `SpellInfliction`
  carries its elemental type; a complex-entity `ConvertToTargetContext` row
  carries the decoded target-conversion and translation-rotation modes.
- common `TargetSettings` fields -- target/group, context, owner, source and
  selector values -- are readable even when the enclosing action is partial,
  and a partial enclosing action stays partial.
- complex-entity spawn, projectile, heal-calculation, and selector execution
  **stay unresolved**; a neighbouring decoded field does not name their
  runtime behavior. `DamageUnit` and `EffectActionCfg` have exact stored
  member boundaries in the selected whole-record route, even where the older
  bounded action reader still stops at a nested child. The stored field name
  does not establish effect placement, damage arithmetic, or activation.

### TargetSettings enum evidence

`memorypack.target_settings_corpus` follows the selected derived-plan object
references through exact whole-record `SkillData` and `BuffData`, including
nested action unions. It requires EOF and agreement between each decoded record
id and filename, then joins the generated `TargetSettings` member plan to the
selected runtime field types and native enum defaults. The three fields
`centerType`, `selectorOwner` and `target` carry `ActionTargetType` values;
`selectorDirection` carries `DirectionType`; `targetSource` carries
`TargetSource`. Current stored values all land on declared enum members. The
selected pair, full enum names, changing counts and source-set hash are in the
local report, not pinned in prose. A missing native pair, field that no longer
resolves to a selected enum, unknown numeric value, or incomplete record leaves
the audit incomplete.

The current corpus strongly associates `targetSource=Context` with a nonempty
`targetGroupKey` and `targetSource=InstantSearch` with a nested finder, but each
association has an authored counterexample. The report retains those exact
source paths. These are observed co-occurrences, not schema constraints or
proof that a runtime consumer chose that target, evaluated the finder, or
executed the enclosing branch.

### EffectActionCfg enum evidence

`memorypack.effect_config_corpus` follows the same selected derived-plan
references into `EffectActionCfg` wherever it appears in exact whole-record
`SkillData` and `BuffData`. It requires EOF and agreement between each record's
decoded id and filename. Fifteen stored scalar members then join to their
declaring native field types and enum defaults in the explicitly selected
`GameAssembly.dll`/`global-metadata.dat` pair. All values observed in the
current installed corpus are declared members. The audit includes the effect,
movement, position, rotation, camera, visibility, and mount-point fields;
their exact member names, selected enum names, source-set hash, changing counts,
and examples stay in the local report.

This corrects the older blanket description of `EffectActionCfg` as
unresolved: its stored enum fields and full serialized boundaries are exact
for this selected build. A declared name such as `FollowTarget` is still an
authored option, not evidence that the game followed a target in a particular
execution. Runtime spawn, branch selection, overrides, units, and renderer
binding remain unresolved. Missing or mismatched native inputs, an unresolved
field type, an unknown numeric value, or a non-EOF record makes the audit
incomplete rather than publishing a plausible enum label.

The same managed `EffectActionCfg` type is also decoded through exact
managed-reference TypeTrees in projectile MonoBehaviour exports. The Gameplay
projectile builder reuses the selected field-to-enum join only after checking
every published projectile effect value, including its stored alert config.
That cross-format agreement supports the enum labels on authored projectile
effects; it does not establish which projectile effects activate at runtime.

### DamageUnit enum evidence

`memorypack.damage_unit_corpus` follows plan references to
`DamageAction+DamageUnit` inside exact whole-record `SkillData` and `BuffData`.
Each record must reach EOF and its decoded id must match its filename. The
selected native field types and enum defaults name the four stored members
`damageAttributeType`, `damageType`, `damageVisualImportance`, and
`ignoreDamageImmuneLevel`. Every value in the current installed corpus is a
declared member; the source-set hash, distribution, examples, and changing
counts stay in the generated report. The observed immunity-field integers
coincide with declared individual members; the audit makes no bit-mask claim.
The same exact plan identifies the concrete union subtype, or null, in each
`atkCalculation` and `poiseCalculation` slot. Current authored records use five
attack-calculation subtypes and two poise-calculation subtypes; their changing
distributions and examples remain in the report. A subtype name establishes
which body is stored, not the arithmetic that the game eventually applies.
For the two calculation subtypes with stored enum parameters,
`MultiplyAttributeCalculation` and `PrimaryAttrCalculation`, the audit also
joins `attributeType`/`type` and `valueSource` to their selected native field
types and declared members. The current values all resolve. These labels are
authored choices; the separate native contract below proves their use only
for one calculation subtype's unpatched evaluator.

The selected-build
[`MultiplyAttributeCalculation.Evaluate` contract](../../scripts/game_data/contracts/multiply_attribute_calculation_native.json)
gates the exact method pointer, runtime field types and offsets, enum members,
direct call and branch targets, and reviewed body bytes against the explicit
`GameAssembly.dll`/`global-metadata.dat` pair. In its **unpatched** path,
`valueSource == AttackerOrHealer (0)` keeps the attacker as the attribute
source; `Target (1)` selects the defender. The selected source, matching
override-attribute array, and stored `attributeType` reach
`CalculationBase.GetAttribute`. The stored `multiplier` and `addition`
`BlackboardDouble` fields each reach `ActionBlackboardExtensions.GetValue`
with the action blackboard. The evaluator converts those resolved scalar
values to double and computes **`GetAttribute(...) * multiplier + addition`**
as its intermediate result.
This is a direct stored-field-to-intermediate-arithmetic relation for this
subtype, including both authored source choices in the exact corpus.

The selected-build
[`AtkScaleCalculation.Evaluate` contract](../../scripts/game_data/contracts/atk_scale_calculation_native.json)
separately proves the normally returning **unpatched** path. Its signature
names the `attacker` and optional `attackerOverrideAttributes: double[]`
operands. With a nonnull override array of length greater than two, the body
reads element 2, which is the selected `AttributeType.Atk` index. With a null
override array, it calls `attacker.get_atk()`; a present shorter array takes a
failure path rather than falling back. The stored `atkScale: BlackboardDouble`
reaches `ActionBlackboardExtensions.GetValue` with the action blackboard. Its
`Single` result is converted to `Double` and multiplied by the selected attack
value into the numeric `CalcResult.value`. The optional server debug-args path
rejoins the same multiplication. This proves an intermediate **`attack *
resolved(atkScale)`** expression for a subtype present in character skills,
not a final damage number.

The selected-build
[`DefiniteValueCalculation.Evaluate` contract](../../scripts/game_data/contracts/definite_value_calculation_native.json)
proves a different piecewise result for its normally returning **unpatched**
path. The stored `value: BlackboardDouble` reaches
`ActionBlackboardExtensions.GetDoubleValue` with the action blackboard. With
`applyScale == false`, that returned `Double` becomes numeric
`CalcResult.value` unchanged. With `applyScale == true`, the stored
`valueScale: BlackboardDouble` reaches `ActionBlackboardExtensions.GetValue`;
its `Single` return is converted to `Double` and multiplied by the resolved
`value`. Thus the direct intermediate expression is **`base`** or
**`base * double(scale)`**, selected by `applyScale`. The optional server
debug-args branch rejoins the same numeric return. If the evaluator's iFix
check is patched, the body calls `GetPatch` and an iFix wrapper, then skips
the ordinary numeric return; the expression is not asserted for that path.

The selected-build
[`BreakingAttackCalculation.Evaluate` contract](../../scripts/game_data/contracts/breaking_attack_calculation_native.json)
proves another normally returning **unpatched** path. It passes attacker
`AttributeType.Atk (2)` and defender
`AttributeType.BreakingAttackDamageTakenScalar (27)` to
`CalculationBase.GetAttribute`, each with the corresponding override-attribute
array. It passes the stored `multiplier` and `atkScale` `BlackboardDouble`
fields to `ActionBlackboardExtensions.GetValue` with the action blackboard.
The two attribute returns are `Double`; the two resolved scale returns are
`Single`. The body multiplies the attributes in `Double`, multiplies the
scales in `Single`, converts the attribute product to `Single`, multiplies
those two `Single` results, then converts to `Double` as `CalcResult.value`.
In operation order, with `A` = attacker Atk, `D` = defender breaking-attack
scalar, `M` = resolved multiplier, and `S` = resolved atkScale, the intermediate
result is **`Double(Single(S * M) * Single(D * A))`**, where each multiplication
uses its operands' stated precision. An optional server debug-args path
rejoins that arithmetic. The evaluator's patched iFix path instead obtains a
wrapper result and skips the ordinary arithmetic.

The separately authenticated
[`DamageAction._CalculateDamageResultForNormalEntity` route contract](../../scripts/game_data/contracts/damage_action_normal_route_native.json)
checks how a stored attack calculation is selected. On its normally returning
unpatched path, the caller tests `takeAtkSnapshot` first. When it is false,
`simpleCalculation == true` resolves the **DamageUnit's own** `atkScale` through
`GetValue`, converts that Single result to Double, and multiplies it by
`DamagePackData.attackerAttributes[2]`. The byref pack's unboxed array field
and index-two length check are part of the selected native proof. When
`simpleCalculation == false`, the caller requires a nonnull stored
`atkCalculation` and passes it to a calculation-object dispatch helper; the
simple scalar branch is skipped. The helper's complete subtype dispatch and
later damage pipeline remain open. A true `takeAtkSnapshot` takes a separate
branch whose calculation semantics this contract does not assign.

The separately authenticated
[`DamageAction._ProcessDamage` Poise route contract](../../scripts/game_data/contracts/damage_action_poise_route_native.json)
closes the stored calculation's immediate consumer on the selected build. The
caller indexes `DamageActionData.damageUnits`, saves that `DamageUnit`, then
tests its `poiseCalculation` field for null. On the normally returning
unpatched branch with a nonnull field, it constructs `PoisePackData`, calls
`ApplyPoiseModifier(BeforeCalculation)`, passes the stored calculation pointer
to the calculation-object helper, and copies the returned
`CalcResult.value` into the unboxed `PoisePackData.calcResult.value` slot when
the intervening post-evaluator guard allows continuation. The
reviewed method, field and enum identities, stack-slot join, direct calls,
branches, full helper return, and method-body windows fail closed against the
explicit selected native pair. This Poise input route does not use the
`simpleCalculation` attack selector. It does not prove which virtual subtype
target ran, what the blackboard resolved, or what Poise was applied or shown.
The exact current character SkillData partition of stored Poise calculation
subtypes, `applyScale` flags, and damage attributes stays in the generated
`character_damage_routes.json` report. Where it stores
`DefiniteValueCalculation`, and if the virtual dispatch selects that stored
evaluator, its separately authenticated contract gives a conditional
intermediate input expression: `GetDoubleValue(value)`
when `applyScale` is false, or that Double multiplied by
`Double(GetValue(valueScale))` when true. These are calculation results entering
`PoisePackData`, not final Poise amounts.

This corrects an earlier presentation assumption: a **stored evaluator subtype
does not imply its `Evaluate` body is selected**. In the exact current
character SkillData set, `simpleCalculation` is true even for some rows that
store `AtkScaleCalculation` or `DefiniteValueCalculation`. The maintained
[`route audit`](../../scripts/webui/gameplay/route_audit.py) records the
changing per-branch counts and examples under `reports/game_data/`, after the
CN Gameplay build; that report requires both the selected native route and
whole-record character SkillData evidence. The WebUI consequently gates the
simple-path badge on the caller contract, and attack evaluator badges on both
the caller route and their own evaluator contracts. Those attack badges are
limited to authored Hp units. A separate Poise input badge requires both the
Poise caller route and `DefiniteValueCalculation.Evaluate` contracts; it names
the intermediate calculation, never a displayed Poise amount.

The separately gated
[`Poise result contract`](../../scripts/game_data/contracts/poise_result_native.json)
extends the selected unpatched native path beyond that intermediate. On its
normally returning branch, `PoisePackData.GetFinalHealValue` invokes
`ApplyPoiseModifier(AfterCalculation)` and reads the resulting Double
`calcResult.value`. `_ProcessDamage` multiplies that value by the attacker
`PoiseDamageOutputScalar` and defender `PoiseDamageTakenScalar` entries in the
PoisePackData attribute arrays, in that order. It flips the scaled Double's
sign before calling the `Modifier.NewPoise` overload that takes the pack and
three stored DamageUnit flags: break time dilation, hidden Poise UI effect,
and ignore Poise immunity. The normal non-extra-target branch calls
`Modifier.get_target`, guards a null result, then submits the modifier
through the returned target's virtual slot 87. The selected metadata closes
the declared `AbilitySystem` descendant set at six types. Base
`AbilitySystem`, enemy part, Int, IntResource and NPC retain the base
`ApplyModifier` slot; `AbilitySystemForGod` overrides it. The God override's
unpatched branch returns `ApplyResult.Failed` without entering the base
application body. This is a candidate set from the selected native metadata,
not an observation of the target class for any executed DamageAction. The
extra-target branch has another factor and uses a transferred modifier path,
which this contract does not interpret as the normal path.

The called `NewPoise` overload forwards the signed Double to its common
constructor path. That path stores the magnitude as a Double and its sign as
`DeltaType.Add` or `DeltaType.Minus`, with `TargetType.Poise`. When the target
selects the base `AbilitySystem.ApplyModifier` path, that body calls
`_DoApplyModifier`; its Poise target
branch calls `PoiseController.ModifyPoise` when the target has a controller.
For Poise damage, the branch tests Poise immunity and the modifier's ignore
flag before that call. The controller checks `hasPoise` and, for an enemy
part, `useMainBodyPoise`. On its active path it gets a signed Double
`finalDelta`, converts it to Single, adds the current Single Poise, invokes
the virtual `set_poise` slot, reads the virtual `get_poise` slot back, and
stores their Single difference converted to Double in `Modifier.realDelta`.
The base `set_poise` body passes the proposed Single, zero and `maxPoise` to
its bound helper, then writes `AbilitySystem.m_poise` only when the returned
value differs enough from the prior field value. Thus the authored input,
post-calculation scaled modifier candidate, and stored readback `realDelta` are
different quantities. Runtime target choice, the virtual Poise accessor
overrides, other guards, live iFix state and entity attributes still prevent a
character-specific applied or displayed Poise amount from being reported.

The current MD5-verified `IFixPatchOut` dump agrees with the reviewed
[`Gameplay patch contract`](../../scripts/game_data/contracts/ifix_patch.json).
Its declared fix targets name neither the two checked DamageAction callers nor the four
checked calculation evaluators or their blackboard/attribute providers. This
is an exact statement about those installed patch files' declared targets;
it does not prove that no other runtime hook, later patch write, or indirect
effect changes a live calculation. The file-currentness and activation
boundaries are detailed in [`ifix_patch.md`](ifix_patch.md).

This establishes authored damage category, attribute target, visual importance,
and one stored immunity option for the selected build. It does not compute
final damage, establish that any authored action executes, or prove mitigation
and immunity behavior. The selected `GetAttribute` body directly uses a
supplied override array at the requested attribute index, and falls back to
the source entity's `attributes.GetValue` only when that array is null; a
present short array fails its bounds check. Blackboard provider internals,
the attack getter's internals, live iFix state, and override-array construction
remain open. The exact code-body
gates fail closed when the selected native pair or any reviewed method/body
witness changes. The authored corpus audit separately fails closed on a
missing or changed native pair, an unresolved field type or value, or an
incomplete record.

## Character attribute formula

`contracts/attribute_formula_native.json` records how
`Beyond.Gameplay.Core.Attributes` turns modifiers into a final value, and
`attribute_formula_native.py` re-proves its call structure on the installed
build. Conclusions (details and exact expressions live in the contract):

- Three stages, each clamped to `AttributeMetaTable` bounds: base = raw +
  BaseAddition; armed applies BaseMultiplier (as `max(1 + Σ, 0)`),
  BaseFinalAddition and the BaseFinalMultiplier product; final applies
  Addition, Multiplier, FinalAddition and the FinalMultiplier product. Same-type
  modifiers sum, except the two FinalMultiplier types, which multiply.
- The conversions are table data, not code constants: `BattleConst`
  `atkRateOfMain`/`atkRateOfSub` feed `AtkIncreaseFactorFrom{Str,Agi,Wisd,Will}`
  (attributes 76-79), ATK's final scalar is `1 + Σ floor(X)·factor`, and MaxHp
  gains `floor(Str)·efficiencyOfSTR`. Attributes are floored before conversion.
- `modifyAttributeType` Main/Sub retarget to the owner's main/sub attribute and
  All to Str/Agi/Wisd/Will; an equipment line with `attrType` 0 is such a line.
- Sources: weapons contribute `(Atk, BaseAddition, baseAtk)` from the upgrade
  curve; weapon, set and passive skills carry `SkillData.cardAttributeModifier`
  (`formulaItem` is the ModifierType); equipment reads `equipAttrModifiers`.
- The call structure is `direct`; the arithmetic order is a reviewed capstone
  reading (`conditional`) because the stdlib decoder skips some SSE forms.
  Hooks for resistances, healing and move/cooldown scalars are unmodelled, and
  combat buffs, gems and team effects are outside the formula's inputs.

## Tags, projectiles, and consumer freshness

- Gameplay tag names come from exact predefined/config registries or validated
  runtime capture under the same native gate. CRC/context-derived names retain
  their derivation label; raw unmapped ids remain visible.
- Projectile behavior is immutable authored data. Skill/projectile ownership,
  event hashes, decoded media, and asset references keep separate provenance.
- Combat/source-graph consumers reject stale inputs and publish a degraded
  reason rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](../webui/gameplay.md).
