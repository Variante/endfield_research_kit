# Gameplay: Tables, MemoryPack, and the native action contracts

Part of [`../game_data_recovery.md`](../game_data_recovery.md). See
[`README.md`](README.md) for the level and lane map.

**Level 4, gameplay lane.** Where authored `Table` config joins exact MemoryPack
framing and selected native enum contracts to become gameplay meaning.

The per-action layouts are **not** in this file. They live in the 213 tracked
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
- **whole-`BuffData` EOF and suffix ownership for partial rows** -- an
  unsupported action or damage-processor route still leaves a physical gap;
  only the contiguous named middle plus accepted suffix closes the outer frame;
- **field meaning, payload encoding, and gameplay semantics** for every
  anonymous scalar, byte span and enum.

`buff_corpus` publishes a separate prefix success/failure/unsupported/ambiguity
denominator and fails its gate on malformed prefixes even when the suffix
reader succeeds. `memorypack.buff_1b_corpus` joins exact-closed root-continuation
tag `0x1B` records to re-streamed current logical bytes and the selected
`BlowOffAction_Data` reader contract; the continuation profile does not
authenticate root-field ownership. Changing coverage belongs in
`reports/animestudio/buff_1b_current_latest.{json,md}` and the matching
`buff_corpus` report, not here.

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
- complex-entity spawn, projectile, heal-calculation,
  `DamageUnit`/`EffectActionCfg` and unresolved selector payloads **stay
  unresolved**; a neighbouring decoded field does not name them.

## Tags, projectiles, and consumer freshness

- Gameplay tag names come from exact predefined/config registries or validated
  runtime capture under the same native gate. CRC/context-derived names retain
  their derivation label; raw unmapped ids remain visible.
- Projectile behavior is immutable authored data. Skill/projectile ownership,
  event hashes, decoded media, and asset references keep separate provenance.
- Combat/source-graph consumers reject stale inputs and publish a degraded
  reason rather than accepting old edges.

Page publication belongs in [`webui/gameplay.md`](../webui/gameplay.md).
