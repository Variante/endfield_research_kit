# Gameplay: Tables, MemoryPack, and the native action contracts

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, gameplay lane.** Where authored `Table` config joins exact MemoryPack
framing and selected native enum contracts to become gameplay meaning.

Per-action layouts are **not** here: each union tag has a tracked
`scripts/game_data/contracts/buff_*_native.json` or `skill_*_native.json`
contract (plus the `finder_*`, `validator_*` and `postprocessor_*` ones) with
its member order, nested profiles, null paths and pinned native inputs, and a
`memorypack/` validator that states what it proves. Gameplay joins selected
action tags to these native reader contracts; provider selection and action
semantics stay unresolved (below).

## Tables and authored joins

- Decoded Table JSON gives each authored field's name and stored value. Units,
  enum meanings and cross-table keys are proven only where a consumer has been
  checked; most tables have no consumer-proven meaning. Gameplay joins selected
  Buff/Skill tables to native contracts; Story publishes the text tables.
- Enemy variants resolve their exact attribute template before stats show.
  Authored points, cooldowns, modifiers, formulas and Buff actions stay source
  values; final values across Buffs, IFix, equipment and server state are not
  computed.
- The Table overlay is checked at the logical and decoded layers: the SparkBuffer
  dump verifies every payload and equals the export, and the previous export's
  changed set equals the changed Table identities in both VFS ledgers. With
  dictionary keys treated as IDs, tables populated in both exports gain no new
  value field paths; tables gaining or losing all rows are data-population
  changes, not a reader change.
- Character and weapon rows form a direct authored ID chain: `CharacterTable`
  and `CharGrowthTable.skillGroupMap` name skill IDs, `SkillPatchTable`
  repeats them, `WeaponBasicTable` names its potential skill, and potential and
  talent effects carry more. Exact stored strings in decoded `SkillData`/
  `BuffData` join skills to Buffs and Buffs to Buffs: authored references, not
  execution, skill ownership of every referenced Buff, or activation.

## BuffData root and union encoding

- [`memorypack/buff_actions.py`](../../scripts/game_data/memorypack/buff_actions.py)
  documents the root reader, its six cursor ranges (`abilityEventAction`
  through `buffEventAction`, pinned by the `buff_root_prefix`/`fifth`/`sixth`
  native contracts), the closed damage-processor routes, the `FA` extended-tag
  escape and the non-identifying action prefix. Generated wrapper order names
  the outer fields and storage order, not action behavior; the opaque physical
  remainder after a stop is not a decoded record.
- `buff.frame_buff_named_middle` continues through the modifier lists,
  `dispelConfig` and an opaque `iconConfig` to the accepted `id` marker; the
  suffix reader closes `id` through `waitFirstTriggerInterval` at EOF. Any
  other processor route or unsupported condition action stops at its tag.
- The selected-build `memorypack.derived_plans`/`derived_values` route decodes
  whole `BuffData`/`SkillData` records to EOF with id/filename agreement. It
  does not upgrade the bounded legacy readers, and the JsonData gate's BuffData
  `schema_decoded` state also needs a recorded root receipt (`jsondata_corpus`).
  Its PlaySound actions: [`audio_naming_coverage.md`](audio_naming_coverage.md).

## The rules every contract shares

Each was violated at least once and caught.

- **Equal member counts never select a layout.** Select from an independent
  token/module or registered-type join, never from arity, a managed name or
  byte length.
- **A shared type argument permits profile reuse, not instance merging.** Each
  repeated target or scalar context is its own instance with its own null state.
- **Structural equivalence is not shared behavior.** Tags sharing a parser
  branch keep distinct union identities and effects.
- **No legacy tag/name aliases.** Current routes contradict the legacy map, and
  exact byte consumption does not validate a legacy label.
- **Source cursor order, not destination layout.** A later object offset never
  moves a field later on the wire; setters, getters, casts, stores and cached
  constructions consume no source bytes. Enum and static type contexts pick
  the helper without adding a header or narrowing the allowed bits.
- **A normal exit may tail-jump to the write barrier**; pin the instruction and
  the separate null rejoin. Readers cross chained unwind regions, so the first
  `.pdata` end is not a record or function end.
- **Null, empty and null-wrapper are three states**; lengths below -1 fail
  closed, and a completed or null child never makes a later terminal byte or
  DWORD optional.
- **Lists reserve the remaining minimum tail before iterating**; count, null
  and loop framing stays conditional on the shared reference-list consumer, and
  a provider bridge proves neither element width nor runtime selection.
- **An unknown tag or nested union stops at its own first byte**, with no scan
  for a later marker; completed children are kept, incomplete parents are not.
- **Raw widths stay anonymous.** Several `Double`-named payloads consume four
  bytes; a vector may be three variable-width scalars rather than twelve raw
  bytes, and only the consumer's own advance decides.
- **A managed action, type or enum name is an identity.** It establishes
  nothing about behavior, units, boolean meaning, ownership, activation or
  execution order.

## What stays unresolved for every action

- **Live provider selection.** A static reader is structural evidence, not proof
  the formatter executes; IfElse paths overwrite the callsite companion in
  native thunks, and reuse reaches state-dependent dispatch. The current
  `EndfieldCapture` gameplay-semantics profile observes seven selected
  `ExecuteInternal` outcomes with bounded raw data words and opaque target
  carriers. It does not record the MemoryPack formatter provider, source-file
  identity, or action union tag at that boundary, so its receipt cannot close
  a serialized action's live provider selection. A dedicated hook needs a
  validated same-call or stable-key bridge between source identity, union tag,
  and selected provider before a capture is requested for that join.
- **Legacy suffix ownership for partial rows.** An unsupported action or
  damage-processor route leaves a physical gap in the bounded reader; the
  derived whole-record route does not convert that row into a complete one.
- **Field meaning and payload encoding** for anonymous scalars and byte spans,
  and runtime meaning even where a native enum names the stored number.

`memorypack.buff_corpus` fails on a malformed prefix even when the suffix
succeeds. `memorypack.buff_1b_corpus` joins exact-closed tag `0x1B` records to
re-streamed bytes and the `BlowOffAction_Data` reader without authenticating
root-field ownership;
[`buff_1b_action_native.json`](../../scripts/game_data/contracts/buff_1b_action_native.json)
names the thirteen `BlowOffAction.Data` fields in source order and proves a
guarded direct call from unpatched `ExecuteInternal` to
`ControlledStateComponent.ApplyBlowOff` -- a runtime consumer, not per-field
expressions, units, target choice or an observed execution.

**Recovery queue.** Close the remaining damage-processor routes from their
native union contexts, then the unsupported condition actions and
`buffEventAction` actions (until then those outer frames cannot join the named
middle); decode `iconConfig`'s 19-member body last, keeping its boundary.

## What the published Gameplay datasets establish

- Every exact `chr_NNNN_token` identity in `StrIdNumTable` is published as an
  evidence-limited record, even without a `CharacterTable` row (no playable
  claim); longer skill/Buff/projectile ids are not promoted to characters.
- Referenced BuffData ids resolve into a fail-closed lifecycle/stacking/value
  catalog. Native enum names (enemy modifier, ability event, skill type,
  cooldown operation) appear only after the native gate passes, and Buff
  action chains only where typed actions consume to the next field boundary.
- GameplayTag names come from the predefined table, the serialized
  `GameplayTagConfig` CRC32 path join, an exact `tagName2Immune` context
  (`exact-context-derived`), or validated runtime capture under the same native
  gate; derived names keep their label and unmapped ids stay raw with a
  structured reason (`load_gameplay_tag_registry` in
  [`base_data.py`](../../scripts/webui/gameplay/base_data.py)).
- The Audio builder's Gameplay sound sidecar reads derived-plan records that
  reach EOF; that does not promote the Buff child corpus to a whole named
  BuffData schema. HIRC Event identity and Skill/Buff owner links are separate
  gates, and branch activation, target choice and audibility stay unresolved.

**Action-row labels** come only from the contract's own decoding: the native
`HpRatio` type and decoded operation (incl. `Floor`/`Ceil`/`RoundToInt`),
`SimpleCalcBBAction`'s decoded operation (division is not a default), and the
decoded `CompareFloat`, `SpellInfliction` and `ConvertToTargetContext` modes.
`TargetSettings` fields are readable inside a partial action, which stays
partial. Complex-entity spawn, projectile, heal-calculation and selector
execution stay unresolved; a stored field name never establishes placement,
damage arithmetic or activation.

## Selected enum audits

Each follows derived-plan references through whole records to EOF with
id/filename agreement, joins stored members to selected native field types and
enum defaults, and fails incomplete on any gap. Current values all land on
declared members; distributions and hashes stay in the local reports.

| Audit | What it names | Boundary |
| --- | --- | --- |
| `memorypack.target_settings_corpus` | `ActionTargetType`, `DirectionType`, `TargetSource` fields | co-occurrences (Context/group key, InstantSearch/finder) have counterexamples and are not constraints |
| `memorypack.effect_config_corpus` | fifteen `EffectActionCfg` enum members; reused by projectile effects after a cross-format check | replaces the older "unresolved" reading; an option such as `FollowTarget` is authored, not executed |
| `memorypack.damage_unit_corpus` | four `DamageUnit` enums, the stored `atkCalculation`/`poiseCalculation` subtype, and parameter enums of two subtypes | a subtype names the stored body, not the arithmetic that runs; no immunity bit-mask claim |

## Damage calculation routes

Each contract is selected-build, **unpatched** and normally returning, fails
closed when the native pair or a reviewed body window changes, and gives an
**intermediate** value, never final damage. Full readings are in each
validator's docstring.

| Contract (validator in `memorypack/`) | Proven intermediate |
| --- | --- |
| [`multiply_attribute_calculation_native.json`](../../scripts/game_data/contracts/multiply_attribute_calculation_native.json) (`multiply_attribute_native`) | `GetAttribute(source, attributeType) * multiplier + addition`; `valueSource` 0 attacker, 1 defender |
| [`atk_scale_calculation_native.json`](../../scripts/game_data/contracts/atk_scale_calculation_native.json) (`atk_scale_native`) | `attack * resolved(atkScale)`; attack from override element 2 or `get_atk()` when the array is null |
| [`definite_value_calculation_native.json`](../../scripts/game_data/contracts/definite_value_calculation_native.json) (`definite_value_native`) | `base`, or `base * double(scale)` when `applyScale` |
| [`breaking_attack_calculation_native.json`](../../scripts/game_data/contracts/breaking_attack_calculation_native.json) (`breaking_attack_native`) | `Double(Single(S * M) * Single(D * A))`, attacker Atk times defender breaking-attack scalar |
| [`damage_action_normal_route_native.json`](../../scripts/game_data/contracts/damage_action_normal_route_native.json) (`damage_action_route_native`) | with `takeAtkSnapshot` false: `simpleCalculation` true gives `resolved(atkScale) * attackerAttributes[2]`; false dispatches the stored `atkCalculation`. `GetAttribute` uses a supplied override array and falls back only when it is null |
| [`damage_action_poise_route_native.json`](../../scripts/game_data/contracts/damage_action_poise_route_native.json) (`damage_action_poise_route_native`) | a nonnull `poiseCalculation` is dispatched and its value copied into `PoisePackData`, independent of `simpleCalculation` |
| [`poise_result_native.json`](../../scripts/game_data/contracts/poise_result_native.json) (`poise_result_native`) | post-calculation value times attacker/defender Poise scalars, sign-flipped into `Modifier.NewPoise`, submitted through virtual slot 87 (six candidate types; `AbilitySystemForGod` fails); base path records readback `realDelta` |

- **A stored evaluator subtype does not imply its `Evaluate` body runs**:
  `simpleCalculation` is true on some character rows that store
  `AtkScaleCalculation` or `DefiniteValueCalculation`.
  [`route_audit.py`](../../scripts/webui/gameplay/route_audit.py) records the
  branch partition; the WebUI gates each badge on the caller route and the
  evaluator contract together.
- Authored Poise input, the scaled modifier candidate and readback `realDelta`
  are different quantities; target choice, accessor overrides, guards, live
  iFix state and entity attributes block any applied or displayed amount.
- The current `IFixPatchOut` dump's declared targets
  ([`ifix_patch.json`](../../scripts/game_data/contracts/ifix_patch.json))
  name none of the two callers, four evaluators or their providers -- a
  statement about declared targets only ([`ifix_patch.md`](ifix_patch.md)).
- Open: the snapshot branch, the helper's full subtype dispatch, provider and
  attack-getter internals, override-array construction, mitigation, immunity
  and final damage.

## Character attribute formula

[`attribute_formula_native.json`](../../scripts/game_data/contracts/attribute_formula_native.json)
records how `Beyond.Gameplay.Core.Attributes` turns modifiers into a final
value (exact expressions there); `attribute_formula_native` re-proves its call
structure on the installed build.

- Three stages, each clamped to `AttributeMetaTable` bounds: base = raw +
  BaseAddition; armed applies BaseMultiplier (`max(1 + Σ, 0)`),
  BaseFinalAddition and the BaseFinalMultiplier product; final applies
  Addition, Multiplier, FinalAddition and the FinalMultiplier product.
  Same-type modifiers sum, except the two FinalMultiplier types, which multiply.
- Conversions are table data: `BattleConst` `atkRateOfMain`/`atkRateOfSub` feed
  `AtkIncreaseFactorFrom{Str,Agi,Wisd,Will}` (attributes 76-79), ATK's final
  scalar is `1 + Σ floor(X)·factor`, and MaxHp gains `floor(Str)·efficiencyOfSTR`.
  Attributes are floored before conversion.
- `modifyAttributeType` Main/Sub retarget to the owner's main/sub attribute and
  All to Str/Agi/Wisd/Will; an equipment line with `attrType` 0 is such a line.
- Sources: weapons add `(Atk, BaseAddition, baseAtk)` from the upgrade curve;
  weapon, set and passive skills carry `SkillData.cardAttributeModifier`
  (`formulaItem` is the ModifierType); equipment reads `equipAttrModifiers`.
- Call structure is `direct`; arithmetic order is a reviewed capstone reading
  (`conditional`, the stdlib decoder skips some SSE forms). Resistance, healing
  and move/cooldown hooks are unmodelled; combat buffs, gems and team effects
  are outside the inputs.

Projectile behavior is immutable authored data; skill/projectile ownership,
event hashes, decoded media and asset references keep separate provenance.
Combat/source-graph consumers reject stale inputs and publish a degraded reason
rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](../webui/gameplay.md).
