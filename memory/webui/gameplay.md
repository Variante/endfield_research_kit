# Gameplay page recovery

## Purpose

Gameplay owns playable characters, weapons/equipment, enemies, progression,
skills, Buffs, projectiles, and semantic asset links. It is the destination for
useful data from the retired Progression and Combat & Projectiles pages. Audio
is deliberately not attached while its ownership model is under review.

The page also hosts the independently published [production catalogs](production.md)
through one shared dataset bar: Characters, Weapons, Equipment, Items, Enemies,
Recipes and Machines. Items uses the complete Production catalog and retains
Gameplay AP recovery, use effects, action blackboards and chest rewards.
Existing Story wiki links and optional asset galleries remain in item details.
Item-effect loading uses the catalog's displayed language without changing the
entity pane's selected language or pending requests. Missing item-effect data
leaves catalog details usable and shows a retry action.
Character breakthrough costs and each potential's configuration values render
expanded in the character detail, so progression data needs no disclosure click.

`webui/src/features/gameplay/tabs.js` owns dataset routing and browser history.
Legacy Production links keep their selections and filters under `#gameplay`;
legacy Gameplay item links open the combined Items tab. Builders and output
paths remain independent. `export.bat gameplay production` refreshes all tabs
from the existing export.

## Inputs and recovery flow

`python -m scripts.webui.gameplay.build_gameplay` runs every stage; the stages
are scheduled separately by the export graph
([`build_gameplay`](../../scripts/webui/gameplay/build_gameplay.py)).

1. `--stage base --stage audit` reads gameplay Tables and exact
   binary/serialized contracts, localizes entries, and publishes sharded data
   ([`base_data`](../../scripts/webui/gameplay/base_data.py)).
2. `--stage projectiles` publishes immutable projectile behavior from the
   `data_projectile_*` MonoBehaviour documents the exporter decoded through the
   bundle's own managed-reference TypeTree. Any other shape is skipped and
   counted by reason, never adapted; an empty dataset points at the export
   ([`projectiles`](../../scripts/webui/gameplay/projectiles.py)).
3. `--stage asset-refs` joins current Gameplay identities to the Assets index.
4. After the curated source graph is current, `--stage combat` publishes
   relationships or an explicit stale/degraded reason.

## Primary generated outputs

`webui/data/lang/<LANG>/gameplay/**`, `webui/data/gameplay/projectiles.json`,
`combat_relationships.json`, and `webui/data/assets/gameplay_refs.json`, whose
sole writer is the `asset-refs` stage. Audio recovery may still publish
`projectile_audio.json` and `sound_effects.json`, but this page does not load
them. Frontend rendering rules are in the header comment of
`webui/src/features/gameplay/index.js`.

List thumbnails reuse the optional asset sidecar. Characters use its horizontal
face banner (the third gallery image in the current publication), selected by
dimensions after applying the Administrator gender filter. Missing banners leave
a text row instead of falling back to full illustrations. Other kinds use their
first representative image. Rows refresh when the sidecar arrives or the gender
changes; missing or broken images leave the text usable. This adds no new
publication dependency or inferred asset owner.

Character and enemy reading views prioritize parsed mechanisms and named
attributes. `mechanics.js` turns gated DamageUnit operands, explicit projectile
callbacks and decoded Buff modifiers into concise effect summaries. It omits
disabled actions and their descendants, preserves conditional context, and
never borrows another skill's level blackboard or evaluates a runtime operand
from its stored fallback. Duplicate records do not become hit counts or an
execution order. Combat and base talents are separate; raw action parameters
and the reference navigator remain in debug information. Enemy variants use neutral
configuration numbers unless the publication supplies a distinct name. Their
selection changes the attribute template, modifiers and initial Buffs together;
it does not establish phases or difficulty order. Unnamed attributes stay
unnamed, and template combat fields remain separate from independent attributes
rather than being merged into final values. Buff effects and their recovery
status remain visible in normal view.

Game descriptions are claims to check, not implementation evidence. The
description audit distinguishes support for a named damage type or an exactly
matched Poise parameter from unverified effects. Numeric comparison requires
the same placeholder, owning skill, selected level, typed operand and native
calculation gates; ambiguous calculations remain unverified. A difference is
shown with both values for review, without calling it a confirmed gameplay bug.
Damage-type support does not validate targets, triggers, duration or cardinality.
In particular, an authored freeze/energy-return statement is not proved by a
generic CreateBuff action, and enemy reflection or stance descriptions cannot
be proved from initial Buffs alone. Missing parsed evidence is not evidence that
the implementation is absent. Unknown effect families stay explicitly unverified.

Items combine `UseItemTable`, `UsableItemChestTable` and `RecoverApItemTable`.
AP recovery is the authored `apRecoverValue`; operator supplies are the
`item_char_ap_supply_*` subset of that table. Existing entries gain AP data
without a duplicate identity. Dataset tabs separate entity kinds, with item
subtypes derived from the authored display/type fields and AP table membership.
The page registry already requires the complete `table` block for this stage.

## Evidence boundary

- Authored stats and level points are shown as authored. The Loadout view
  computes final attributes only from the validated attribute formula (see
  [`../game_data/gameplay_semantics.md`](../game_data/gameplay_semantics.md))
  over level, potential, weapon, weapon skills, equipment and set effects;
  combat Buffs, gems, team effects, IFix and display rounding stay uncomputed.
- Binary action chains publish only when typed fields consume to exact
  boundaries. Unknown unions, enums, tags, selectors, and payloads stay
  explicit.
- Character `DamageUnit` rows come only from SkillData that the selected native
  plan decodes through EOF with an identifier equal to the filename
  (`build_skill_damage_catalog`). A missing or mismatched native pair publishes
  no units. They are authored setup rows, not evaluated damage, selected
  branches, mitigation, or hits.
- Formula badges are conditional intermediate expressions, each gated by its
  own selected-native audit status in the language payload; an unavailable
  audit hides the badge and leaves the stored operands plus one note. Stored
  level blackboard numbers are never presented as observed `GetValue` results.

  | Status field | Native proof | Badge scope |
  | --- | --- | --- |
  | `skillDamageRouteEvidence` | [`damage_action_route_native`](../../scripts/game_data/memorypack/damage_action_route_native.py) | Hp units, `simpleCalculation` true, `takeAtkSnapshot` false: `atkScale × attackerAttributes[2]`; a stored `atkCalculation` subtype is bypassed on this branch; suppressed on Poise rows |
  | `skillDamageAtkScaleEvidence` | [`atk_scale_native`](../../scripts/game_data/memorypack/atk_scale_native.py) plus the route audit | Hp units with both flags false and an `AtkScaleCalculation` subtype |
  | `skillDamageBreakingAttackEvidence` | [`breaking_attack_native`](../../scripts/game_data/memorypack/breaking_attack_native.py) plus the route audit | Hp units with both flags false; hover keeps the mixed-precision order |
  | `skillDamagePoiseRouteEvidence` + `skillDamageDefiniteValueEvidence` | [`damage_action_poise_route_native`](../../scripts/game_data/memorypack/damage_action_poise_route_native.py), [`definite_value_native`](../../scripts/game_data/memorypack/definite_value_native.py) | the intermediate `PoisePackData.calcResult` input from a stored `DefiniteValueCalculation`, independent of the attack flags |

  The stored-subtype partition that makes these gates necessary is generated by
  [`route_audit`](../../scripts/webui/gameplay/route_audit.py). The separate
  [Poise result audit](../../scripts/game_data/memorypack/poise_result_native.py)
  is not published in the Gameplay index and gates nothing here; the page makes
  no applied or displayed Poise claim.
- Native enum names require the selected GameAssembly/metadata gate and
  disappear without it; authored rows remain.
- Projectile effect setup expands the exact TypeTree `EffectActionCfg` rows by
  list slot. `effectConfigEnums` names appear only when native field types, the
  selected MemoryPack member plan, and every published effect value validate.
  These fields do not prove that a runtime effect spawned or followed a target.
- Buff `TargetSettings` enum names need a selected native-field to
  serialized-plan join (`enrich_buff_target_settings_names`); they label
  authored settings, not the evaluated target, finder execution, branch
  selection, or playback.
- Projectile ownership distinguishes exact references from inferred
  candidates. Projectile fields are exact TypeTree values published as stored
  integers; no member name is inferred.
- A Buff card quotes a nonempty stored `stackingSettings.stackingKey` only when
  native evidence validates and the exact post-id tail projection supplies it;
  empty and null keys stay omitted, and no runtime stack sharing is inferred.
- Asset availability, event registration, or graph proximity does not prove
  runtime use.

## Focused refresh commands

```bat
python -m scripts.webui.gameplay.build_gameplay
python -m scripts.webui.gameplay.build_gameplay --stage projectiles
python -m scripts.webui.gameplay.build_gameplay --stage skill-refs
python -m scripts.webui.gameplay.build_gameplay --stage asset-refs --default-language CN
```

Use the canonical wrapper when cross-page Assets, Audio, source-graph, or
Story inputs changed.

## Authored skill reference navigator

`skill_refs.py` publishes `data/gameplay/skill_refs/` from the last Data page's
SkillData publication. The shared `data_inspector/publication.py` reader checks
the root, catalog and shards against the selected export's complete loose-file
signature and source identities. The consumer also authenticates the recorded
native pair against the selected installation and requires a validated wrapper
plan. Missing or stale inputs publish a visible unavailable reason; this stage
does not build Data. An alternate `--export-root` requires `--game-root` so it
cannot silently validate another installation.

Character and enemy debug details show the current entry's exact skill IDs, with an
all-skill catalog, shared search/facets, lazy per-skill records, back navigation,
and incoming skill references inside an expandable navigator. Exact group
membership supplies friendly skill names; a bounded label map translates known
action types while preserving their raw type and fields. The normal mechanism
view shares the navigator's authenticated record cache. Named action unions
must be available before their damage is summarized, so missing action context
cannot silently enable a disabled branch. Explicit enabled projectile callbacks
may load one additional skill-reference step; their values still cannot borrow
the parent's blackboard. Each node retains its nested source path, parent
context and nearest stored frame
interval, and named operands preserve their explicit selection flags. Static
CreateBuff item references require `readIdFromBlackboard` to be false; a runtime
key never promotes the stored fallback ID into a target. Explicit named fields
link static next-skill, Buff and projectile IDs; dynamic blackboard keys are
shown as parameters and never treated as target IDs. A unique SkillData ID is
a direct stored reference. Buff filename presence is source-only evidence and
does not validate the Buff's interior. Projectile definitions are available
only when their byte-complete published source identity and raw-data hash still
match the selected Unity store. Ambiguous or absent targets remain visible.

Stored frame intervals are not converted into seconds, and list order does not
claim runtime execution order. Conditional and nested contexts stay visible;
anonymous values remain structural-only. This view does not calculate damage
or attach audio. Its source links reuse the Data page's file navigation.

## Highest-value remaining gaps

- Improve exact skill-to-projectile and asset ownership.
- Revisit Gameplay audio attachment only after its ownership and runtime
  evidence boundaries are better understood.
- Recover additional action/selector schemas with exact-consumption fixtures.
- Keep runtime formula and tag semantics gated and reproducible.
- Measure Buff coverage against the provenance-matched BuffData census, not
  the export: the JsonData gate (`scripts.game_data.jsondata_corpus`) joins
  the complete `memorypack.buff_corpus` report one-to-one to the authenticated
  VFS ledger by path, length and digest, and every current file carries a
  named outer frame to EOF (the BuffData row in
  [`../game_data/extraction_payload_boundaries.md`](../game_data/extraction_payload_boundaries.md)).
  The Gameplay audit still counts exported BuffData with Persistent
  precedence instead of joining that report, and interior action and icon
  bodies outside the native-gated exact subset stay opaque, so a trigger
  missing there cannot yet be told apart from an unnamed one.
