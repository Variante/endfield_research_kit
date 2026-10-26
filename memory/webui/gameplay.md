# Gameplay page recovery

Enemy distribution navigation uses the authored `DistributionInfoTable.jumpId`
join to `SystemJumpTable` (`phaseId=Map`, JSON `phaseArgs.levelId`). The localized
area name labels the link. Generic distribution categories without a map jump
remain text; this join identifies a map, not an enemy spawn position.

## Purpose

Gameplay owns playable characters, weapons/equipment, enemies, progression,
skills, Buffs, projectiles, and semantic asset links. It is the destination for
useful data from the retired Progression and Combat & Projectiles pages. Audio
is deliberately not attached while its ownership model is under review.

Weapon and equipment sidebar entries share two lines: name, then metadata
and effect/attribute labels, with overflow truncated on the second line.

The page also hosts the Gameplay-owned item, building and recipe catalogs
through one shared dataset bar: Characters, Weapons, Essences, Equipment,
Items, Enemies, Combat stages and Activities. Activities reads the last
Story/Text reference and Assets media publications through
`webui/src/features/gameplay/activities/`; the shared tabs controller owns its
routing and lifecycle. See [Activities](activities.md) for its evidence boundary. Items uses the complete Gameplay catalog and retains
Gameplay AP recovery, use effects, action blackboards and chest rewards.
Role-specific equipment supplies absent from UsableItemChestTable use the exact
ActivityCharTrial.showRewardId → RewardTable.itemBundles inclusion to link
the supply item to the trial equipRewardId. Details show that shared equipment
reward with quantities and navigation, explicitly retaining the unresolved
alpha/beta box allocation; the trial reward is not asserted as single-box contents.
Existing Story wiki links and optional asset galleries remain in item details.
Item details link back to an existing Story wiki entry in the displayed language
independently of item-effect availability; Story item links select Gameplay's
Items catalog through the shared navigation URL.
Machine details also show the linked building items' `decoDesc` flavor text
after the machine description, reusing The Gameplay item catalog’s published item records.
Exact item/building links share distinct descriptions, item crafting and use
connections, building recipes, and Story navigation across both catalog views.
For exact one-to-one item/building pairs, both catalog selections render the
same combined detail: item identity and flavor, crafting/use connections, item
properties, then building recipes and placement/power properties. The header
lists both IDs and sources are merged. Linked detail shards reuse the catalog's
language and cache; ambiguous or multi-record links retain separate views.
Combined details use one tag row, one item/building switch row, and paired
item/building configuration disclosures to avoid repeated section headings.
Crafting-source and ingredient-use cards reuse The Gameplay item catalog’s recipe summaries
to display the full ingredient/output formula, including hub-crafted building
items; no processing time is inferred for untimed manual/hub recipes.
Item-effect loading uses the catalog's displayed language without changing the
entity pane's selected language or pending requests. Missing item-effect data
leaves catalog details usable and shows a retry action.
Character breakthrough costs and each potential's configuration values render
expanded in the character detail, so progression data needs no disclosure click.
Character and enemy header facts use the same compact gray label=value line as
other Gameplay details. Character Data / Loadout controls follow the character
name in the title row and wrap on narrow screens; source IDs remain debug-only.
Character, Weapon, Essence and Equipment sidebar rows omit the redundant kind
badge because each dataset has its own tab.
The Items catalog automatically selects the first filtered
record when opened without an explicit ID. Formula item groups use centered flex
rows so operators align with item chips; both within-group and cross-group operands
use plus signs. Item and building recipe rows share one renderer and reserve one fixed activity-label column
("活动限定") followed by the formula, with per-cycle counts and per-minute rates.
The device column is omitted and gas conditions remain above their recipe group. Catalog and entity sections share heading
styles and omit horizontal separators. Building records retain their authored IDs and publication paths within Items.

Recipes have no standalone Gameplay tab. Current recipe links open
an output item's page, selecting the first published output for multi-output recipes.
Items load complete recipe shards for their source/use rows; inputs, outputs, cycle
rates, variants, formula items and stored conditions remain available there.
`itemRecipe` preserves the requested recipe for scrolling within the item detail.
Recipe publications and the shared crafting renderer remain in use.

Gameplay's entity, item and stage datasets share `src/features/gameplay/detail.js` for the image/title
shell, plain metadata, section markup, and attribute cards. Entity, catalog and
combat-stage renderers retain their data joins and interactions. Published images
supply the title thumbnail when present; missing images leave a text header.
Character/weapon level attributes and Equipment attributes use the same
card renderer, while crafting input/output rows share the catalog recipe renderer.

Building details within Items retain the catalog's image and large title.
Building dimensions, power requirement and electricity consumption appear in the
header metadata for exact one-to-one item/building joins. Other linked buildings
retain their separate attribute sections inside the item detail.
Configured output references come from the linked ItemTable row's `outcomeItemIds`,
not from the building recipe index; they do not establish a complete production list.
Its former tag row uses plain gray metadata for type, rarity and category;
dimensions, power requirement and consumption join that metadata line.
Crafting sources use the same card surface with recipe input → output rows.
Section typography and the Assets strip are shared; the main icon also appears
in the deduplicated strip. Exact building/item pairs display their combined content in one item detail.
Stored configuration
disclosures and the catalog evidence note stay behind Show debug info for this
tab. Untimed crafting rows with no device/environment omit empty layout columns.
Weapon sections share character heading typography, omit horizontal section
dividers, and reuse the character asset strip for images and model links.
Weapon base attack uses the same plain effect text as skill values. Breakthrough
and cumulative upgrade costs share one wrapping item row per group; currency
chips link to their published Items entry and use “折金票” / “累计折金票” in CN.
Essence details show term pools in three columns under one Essence terms heading,
using the same individual card and title styles as character potentials,
then compatible weapons and image assets. World-level costs remain in the
published data but have no visible detail section. Image previews
group identical icon names across Texture/Sprite crop and resolution variants,
choosing the largest display representation; source asset identities stay distinct.
Weapon, Essence and Equipment image/model sections are titled Assets (“素材”).
All Gameplay asset image cards show the complete filename, including extension
and object identity suffix, beneath the image and in the enlarged preview.
Captions wrap within the card instead of being truncated.
Thumbnail filename captions are plain text; the thumbnail remains an enlargement
button, and only its popup caption links to the exact Assets path. Authored binary-table image fields
have priority for every item: `iconId` supplies the portrait and exact media-table
references supply supplemental images. Filename-based quest/variant associations
and manual image selections cannot replace an authored icon, even when that
icon's asset is missing. Generic icons remain visible when directly authored.
The former treasure-to-goods manual image correction is removed;
`item_e1m1_treasure` uses its stored `item_radio_01`, and
`item_quest_e2m6_battery2` uses its stored `item_proc_battery_3`.
Quest filename matching is conditional and applies only without an authored icon;
reading artwork stays supplemental instead of replacing that icon.
`item_mission_f1m29d2_flower1` directly stores
`iconId = item_mission_sm2l7m1_flute` in the verified ItemTable decode; the
different item and image stems do not establish an incorrect association.
The permission card `item_e2m2_ID` directly stores
`iconId = item_mission_sm1l3m3_elevatorcard` in ItemTable. A focused installed
TableCfg decode with MD5 verification reproduced the published table exactly.
This is a stored icon reference, not a name-based display guess or proof that
the permission card and elevator-card item are identical; live UI consumption
is a separate evidence boundary.
Equipment shares Weapon's section headings, spacing without horizontal dividers,
plain highlighted attribute values and thumbnail/model strip. Manufacturing
material links keep their existing item lookup and icons.
For Wuling City's Energy Alluvium, `WorldEnergyPointGroupTable` directly names
`eny_0091_wgshoal` as its icon. Gameplay asset matching uses the full entity/icon
tokens, while exported candidate models use the `monster_elite_wgshoal` naming
family. The current `EnemyTable`/`EnemyTemplateTable` rows provide no model ID
bridge; `AIConfig/EnemyTemplateDataSummary` only names the enemy data asset.
The user-selected `P_monster_elite_wgshoal_01` model is recorded in
`webui/overrides/gameplay_assets.json`. The asset-ref stage resolves its exact
base name to one exported representative and marks it `manualOverride`;
missing selected models fail with the entity key and stem. This manual display
selection does not prove the enemy-data-to-prefab ownership link.

`webui/src/features/gameplay/tabs.js` owns dataset routing and browser history.
Only current Gameplay routes are supported; retired Gameplay items, Building and
Recipe routes, hash redirects and selection parameter aliases are removed. Builders and output
paths remain independent. `export.bat gameplay` refreshes all tabs
from the existing export.

## Inputs and recovery flow

### Combat stage catalog

Gameplay's Combat stages tab is published by the `battle-stages` stage in
`scripts.webui.gameplay.build_gameplay`, implemented in `battle_stages.py`.
It reads exported Tables and the last published Data/Assets/Gameplay sidecars,
and writes `lang/<LANG>/gameplay/battle_stages.json` (schemaVersion 3). Spawner configurations
are published once under `spawners` and entries reference them by
`battle.spawnerIds`, so shared scenes are not duplicated.
Spawner hosts are selected by an explicit current-dungeon-ID branch, else by
SubGameInstanceDataTable.bindScriptId matching the host's level script
(`boundScript`); only remaining hosts are shown as shared-scene configuration.
`battle_links.py` adds `links.maps` (stage scene and associated area maps that the Map
page published) and `links.missions` (GameMechanicConditionTable unlock/quest
conditions and dungeonMissionId), each an identity join, not a progression claim.
The Gameplay task declares Table inputs and optional JsonData; publication
consumers add no cross-page build dependency. Supported categories are explicitly
listed in the projector; sharing DungeonTable does not make puzzle, factory or
racing records combat stages.
Combat stage update identities are `stage:<DungeonTable key>` in
`updates/gameplay.json`. Lists and detail titles show badges, details expose
source-field changes, and Version changes combines with the stage facets.
Comparisons follow the exact stage and selected shared definitions, with
sibling configurations excluded; recovered/runtime wave parity is not inferred
from an authored-source badge.

DungeonTable's category and series ID own grouping, and an exact inclusion in
DungeonSeriesTable.includeDungeonIds owns member ordering. DungeonRaidTable's
stored isRaid/RelatedLevel fields own normal/hard classification and paired-mode
navigation; a suffix or localized name never substitutes for that table.
Enemy IDs retain their parallel configured levels, including missing-level gaps.
RewardTable fixed item bundles retain each authored reward field and quantity;
random bundles are marked separately and no complete reward-pool claim is made.
Explicit ActivityDungeonTable.gameMap.gameId joins link supporting activities.
These are stored configurations, not current unlock/availability or observed
runtime behavior. Exact enemy variant IDs, source dumps and internal
script/config identities remain behind debug.

`battle_evidence.py` consumes Data's named LevelData, LevelScriptData and
SpawnerConfig publications. A stored sceneId owns scene membership, LevelData's
script and host pointers own script/config joins, and a named GetCurDungeonId →
SwitchString case → literal explicit-script event receiver owns conditional
dungeon selection. Other hosts remain labelled shared-scene configuration.
Library keys resolve exact enemy variants. SpawnMonsterFromTemplateV2 counts,
local timestamps and intervals retain their stored values, alongside repeat flags,
group backup counts and concurrent limits. Counts describe configured spawn
actions for one execution, not observed population or a stage total. Timestamps
are local offsets; tied times, wave IDs and dictionary order never establish
runtime wave order. Unknown transitions retain an explicit recovery gap.

Publication freshness and usable decoded Spawner records are separate checks.
If a current Data publication contains no complete named SpawnerConfig records,
Gameplay exposes it as unavailable with bounded decoder diagnostics and status
counts. A fresh manifest must not hide a whole-family reader refusal. The
indexed-string root and nested-layout migration remains owned by the raw reader;
LevelScript native drift likewise keeps script-backed stage selection unavailable.

Literal named Buff-application actions retain their trigger entries and target
scope when linked through named getters/repeat-list pointers. Born Buffs remain
separate from variant Buffs. Identifiers and blackboard parameters do not establish
effect semantics. SeasonTowerDungeonTable's exact dungeon key supplies authored
special-Buff prose; only same-row DungeonTable.paramList numeric keys substitute
its placeholders. Missing or duplicate keys remain unresolved placeholders.
The stage builds its own Buff catalog with `base_data.build_gameplay_buff_catalog`
for exactly the referenced IDs (Gameplay's published catalog omits many spawn and
script Buffs). Recovered Buffs render through Gameplay's `buffSummary(record,
values)`: the applier's blackboard values fill the keyed modifier/duration fields,
and a key without a supplied value is shown as set by that key rather than the
serialized placeholder. Unresolved Buffs show their literal reference and
parameters.

`battle_presentation.py` resolves authored dungeon image tokens against whole
normalized asset stems, preferring full textures for stage art. Reward icons
use exact ItemTable.iconId. Enemy artwork belongs to the linked published
template; it is not claimed as a variant-specific appearance. Shared Gameplay
reading cards, overview facts, row thumbnails and image previews supply the UI.
Stage descriptions, objectives and special rules share one detail section;
background artwork is shown only in the final shared Assets strip.
`battle_activities.py` owns stored activity navigation: ActivityDungeon and
ActivityCharTrial direct joins, activity/stage-checked completion-condition
dungeon references, and unselected SeasonTowerMainHud destinations followed
through season week groups and star game IDs. Literal completion references
do not prove ownership or condition execution; mode destinations do not select
a live season. Both Activities and combat-stage details preserve these relation
labels and reuse one Gameplay publication.
Map link roles follow the stored field: sceneId is a scene target, while
levelId is an associated area rather than an assumed entrance. Trial dungeons
can carry only levelId and still link to the published simulated training area.
Enemy links select the precise variant in the existing enemy detail.
Attribute modifiers retain EnemyTable's raw modifier type and value; a stored
Multiplier amount is not displayed as a computed final multiplier.

`--stage battle-stages --battle-stages-from-reference` provides a preview from
the last published localized Text rawRows and Data/Assets/Gameplay data.
It never reads the export, accepts no export/native override or additional stage,
records missing tables and labels the result `referencePreview`. Missing raid
publication leaves mode classification unspecified, even when a title mentions
hard mode. This keeps a usable preview while an export's completeness gate refuses
the normal builder; it does not mark that export complete or current. Data
snapshot framing/catalog/counts are validated, and native-backed projections
still authenticate the selected installed binaries. The normal path keeps Data's
export signature/source gates; missing, stale or native-mismatched evidence
empties only that projection and records its diagnostic. An alternate export
requires an explicit game root for native evidence. Full builds retain the export
completeness gate and replace the preview after a usable export is available.

The frontend supports search, shared category/mode/recommended-level facets,
sorting, continuous virtual scrolling, collapsible series, deep links and enemy/item navigation.
Reset keeps the selected dataset; empty results keep the selected detail available.
Interface language and data language remain independent.

### Entity and behavior stages

Equipment manufacturing uses the exact EquipFormulaTable.level →
EquipFormulaChainTable key join. Each chain retains its own currency and
component quantities; the formula row alone does not contain those costs.
The frontend shows component and currency quantities with thumbnails from
The Gameplay item catalog’s published item/icon lookup, within the Gameplay build. Component production costs and time are not displayed.
Manufacturing presents the formula link inside one card, with each alternative
method in its own bordered recipe row. It reuses the Recipes renderer for
material inputs joined by plus signs, an arrow and the equipment output.
Pack membership and undecoded unlock values/types stay in published
data but are hidden from details; numeric unlock types are not user conditions.

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
   Its implementations, `gameplay_refs.py` and `factory_models.py`, live under
   `scripts/webui/gameplay/`; the existing asset-sidecar path is a publication
   contract, not Assets builder ownership.
4. After the curated source graph is current, `--stage combat` publishes
   relationships or an explicit stale/degraded reason.

## Primary generated outputs

`webui/data/lang/<LANG>/gameplay/**`, `webui/data/gameplay/projectiles.json`,
`combat_relationships.json`, and `webui/data/assets/gameplay_refs.json`, whose
sole writer is the `asset-refs` stage. The page also reads Audio's
`projectile_audio.json` and (in the background) `sound_effects.json` as
playback links; Audio owns their binding evidence, including each event's
authored Wwise `selectionTree` (layers play together; random/sequence/switch
pools are alternatives, and which branch a trigger takes stays unresolved). Frontend rendering rules are in the header comment of
`webui/src/features/gameplay/index.js`.

List thumbnails reuse the optional asset sidecar. Characters use its horizontal
face banner (the third gallery image in the current publication), selected by
dimensions after applying the Administrator gender filter. Missing banners leave
a text row instead of falling back to full illustrations. Other kinds use their
first representative image. Rows refresh when the sidecar arrives or the gender
changes; missing or broken images leave the text usable. This adds no new
publication dependency or inferred asset owner.
Weapon list labels and their three skill facets come from the published
skills, not a separate weapon-name mapping. Essences (Energy Alluvium groups)
is projected by [gems.py](../../scripts/webui/gameplay/gems.py); its
weapon-compatibility and region joins are authored-pool candidates, not drop
probabilities (see [gameplay_semantics](../game_data/gameplay_semantics.md));
UI behavior is in [`webui/README.md`](../../webui/README.md#gameplay).

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
it does not establish phases or difficulty order. Exact variant IDs and update
badges are visible on selectors and comparison rows. Change panels separate each
affected configuration, preserving its own previous/current source values. An
added configuration is a new record relative to the previous export, not proof
of release or runtime availability. Unnamed attributes stay
unnamed, and template combat fields remain separate from independent attributes
rather than being merged into final values. Buff effects and their recovery
status remain visible in normal view.

SkillData and BuffData value readers receive the selected export's indexed
string pool explicitly. Buff lifecycle and stacking names come from selected
native enum fields with matching serialized widths. A Buff is counted as decoded
only after physical EOF and filename/id agreement; the published evidence label
remains `derived-plan-whole-record`. Raw action fields and additional effect
families remain pending semantic recovery, including when a known duration or
attribute modifier can already be displayed. A decoded Buff does not establish
that its actions ran.

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

Equipment suit groups use published suit IDs; matching names alone do not
establish suit membership.

- Authored stats and level points are shown as authored. The Loadout view
  computes final attributes only from the validated attribute formula (see
  [`../game_data/gameplay_semantics.md`](../game_data/gameplay_semantics.md))
  over level, potential, weapon, weapon skills, equipment and set effects;
  combat Buffs, gems, team effects, IFix and display rounding stay uncomputed.
  Reviewed element-specific damage-taken scalars include their corresponding
  reduction factors. Weapon/set bonuses retain whole-record, identifier-matched
  SkillData decoding with the selected export's StringPool when present.
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
- Tighten Gameplay audio links to exact runtime owners; they show Audio's
  current candidate bindings, not proven playback.
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

The Items catalog accepts only its current publication format. Item and recipe
references carry explicit catalog/group joins; retired recipe URLs and browser
alias conversion are removed. Singleton types share Other. Media for all catalog
items uses the current Gameplay asset sidecar, including authored picture, card
theme, sticker and avatar bindings from the Gameplay item catalog and model-key candidates.
Items and entity details share the same Story wiki button renderer.


## Item, building and recipe catalog

Gameplay items is the table-backed item, recipe and building publication displayed
inside Gameplay. Its builder keeps its own publication and does not rebuild or
depend on Gameplay, Assets or Data. Gameplay adds optional use effects and
rewards to item details from the publication in the same displayed language.
Its source links reuse the Data page's file viewer; the catalog and details
remain usable in a static package without that viewer's local server API.
Item bundles share one linked item-chip renderer across exchanges and recipes,
using Gameplay's chip CSS and exact item catalog links. Shop listings and
currency-use entries expose configured `cnDiscount` price variants explicitly.
Currency purchase records show base prices, configured discounts and discounted prices, including an explicit no-discount label. Older publications missing discount fields show a refresh notice.
Item shop listings default to a collapsed section. Deduplication ignores goods
and reward record IDs, retains all source links, and compares the complete
configuration, including shop identity, reward contents, base prices, limits and
conditions. Matching purchases with different discounts render together with
every distinct discount and discounted price; currency-use references share
this grouping. Distinct base prices or availability remain separate, and all
source links are retained.
These are configured variants, not live discounts: the credit-shop Lua consumer
multiplies the base price by the server goods record's `discount` value.
The shared `CashShopUtils.GetDisplayPrice` consumer rounds that rate to a whole
percentage, then floors the discounted price. The frontend applies this display
rule to configured variants too; it does not treat the table rate as live server
state. Refresh Gameplay items publication after adding discount fields to currency
references, since older shards omit them even when the source table has them.

## Recipe navigation

Gameplay exposes one Items catalog including buildings, with no standalone
Building or Recipe tab. Exact `FactoryBuildingItemTable` joins suppress a
separate building row when its published item is present. Buildings without a
published item remain selectable entries; matching names never merge records.
Building category and power/recipe relationship facets share the Items sidebar
with item type, medal category and version filters. All linked building
attributes and recipes stay in item details, including non-bijective joins.
The `endfield.gameplay-items.v1` index carries item `buildingIds` and machine `items`
references to perform this join without fetching detail shards. Older schemas
are rejected. Recipes are rendered inline using explicit current `groupId`
references; item bundles use `catalogId`, retaining source IDs as evidence. Retired production/building/recipe routes,
hash redirects and selection/filter parameter adaptations are removed.
Items load full recipe shards for source and ingredient-use rows, retaining
variants, quantities, processing rates, building references, formula items and
stored conditions. Recipe publications and shared crafting rendering remain
available to Items and Equipment.
Recipe rows omit the redundant View recipe link; item and building links remain.

## Inputs and publication

`scripts/webui/gameplay/items/build.py` reads exported tables through
`ExportLayout`. Its `TABLE_NAMES` declaration is the exact table inventory;
the page registry declares the `table` structured input for extraction and
freshness checks. It reads no installed binary or other page's publication.
Existing Sprite crop documents and Texture2D images are optional reused inputs,
declared with the registry's `uses`; a Gameplay items refresh does not extract them.
The compact icon lookup uses authored `iconId` values and shared exact image-stem
resolution. Within exact-name candidates it shares Gameplay's item-icon shape
preference, then selects the highest resolution; Sprite wins an equal-size tie.
Same-name variants can include full art, small art and a solid silhouette, so a
Sprite-first filename sort is unsuitable for item thumbnails. This is a display
preference, not proof of the runtime asset selection. Missing icons stay
absent, with their identifiers recorded in `iconStatus`; no prefix match is used.

The builder publishes `webui/data/gameplay/items/manifest.json`, the available
languages and default language, plus `webui/data/lang/<LANG>/gameplay/items/index.json`
and item/recipe/building detail shards. Every source table has a SHA256 receipt
in the index. Missing or malformed required tables fail before publication.
An untranslated page uses the declared default language and displays that
fallback. The direct command is:

```bat
python -m scripts.webui.gameplay.build_gameplay --stage items --languages CN --default-language CN
```

`export.bat gameplay` performs the page registry's normal freshness check and
build. Refreshing from the installed game remains an explicit separate choice.

## Recovered relationships

Item detail shards also carry `wikiDescriptions` from exact
`WikiEntryDataTable.refItemId` joins, with entry IDs and localized `desc` text.
Gameplay displays this explanation after primary and decorative descriptions,
including in the shared building/item detail. It uses the existing rich-text
renderer and deduplicates identical wiki explanations. This reads The Gameplay item catalog’s
own exported tables, without a Story publication dependency.
The publication's `labels` resolves `ui_wiki_building_usable_formula` and
`ui_wiki_building_usable_func` through `TextTable` into the selected language's
I18n table. Gameplay uses their translated text for building recipe and wiki
explanation headings; keys are not displayed or translated via UI locale.
The same label map supplies item participating-recipe and activity-limited
recipe text from their corresponding wiki keys.
Recipe index summaries retain activity and gas-environment metadata and compact
original variants. Item recipe references select the variant by original ID,
never render a grouped union as one craft, and preserve condition badges in both
participating-recipe and production-source lists.
Item and building identity tags share the header row with the Story Wiki link.
Recipe rows keep formula, processing time and detail navigation in separate grid
columns; the building link lives inside the formula column so it cannot push the
detail link onto another row.

Item and building descriptions are separate authored fields:
`ItemTable.desc` and `FactoryBuildingTable.desc`. Their wording can differ even
for an exact building-item join (the multi-port underground pipe uses cargo
wording in the building record and liquids/gases in the item record). This does
not prove which field a runtime screen selects or that either field is obsolete.
`ItemTable.decoDesc` is item decorative text, not a second building description;
decorative buildings can repeat it in `FactoryBuildingTable.desc`. Details label
record/field sources only when linked descriptions differ (and decorative sources
only when linked decorative texts differ), group identical text into one display,
and retain distinct text separately. Descriptions have no headings; differing
sources use inline labels. Decorative text appears last, one font size smaller. This also covers
items whose own `desc` and `decoDesc` match. Per-publication inventories belong
under `reports/gameplay/items/`, not in the durable recovery state.

- `ItemTable` supplies the complete catalog, localized item types, descriptions,
  rarity and stack fields; `FactoryItemTable` marks production-specific entries.
- Machine, hub and manual craft tables supply ingredients and outcomes. The
  item detail exposes reverse produced-by and used-in-recipe links. Machine
  recipe groups retain their stored nesting, including groups with multiple
  outputs. An explicit `machineId` matches a building by exact table key;
  `FactoryBuildingItemTable` maps building items to building identifiers.
- Recipe filters retain machine / infrastructure equipment / manual methods.
  Output categories collect every positive outcome's item type, showing type
  and exact building encyclopedia category, merging identical localized labels.
  The hub-craft method is displayed as 基建设备.
- `medals.py` groups achievement medals by matching authored name and completion
  text handles to each item's name and decorative description. Ambiguous pairs
  also require the achievement/level item identifier; plated variants require
  `canBePlated`. Conflicting owners remain separate. Every tier keeps its full
  item row, conditions and source references. `AchievementTypeTable` supplies
  category/group labels. Original item identifiers remain searchable aliases
  to the achievement group; localized names alone never create a group.
- `limited_items.py` groups duplicate limited-item records through the exact
  `LTItemTable.itemId` mapping, using its target as the display identity. Rows
  must match apart from their identifier and internal type. Missing targets,
  differing configuration and cyclic links stay separate; chains are not
  followed. Original records and types remain in `itemVariants`, source receipts
  and relationship lists are combined, and both identifiers remain searchable
  and navigable. This does not equate their runtime item types or expiration rules.
- Building categories follow the encyclopedia's `WikiGroupTable` building groups
  through exact `WikiEntryDataTable.refItemId` and building-item joins. Multiple
  categories are retained; buildings without a matching entry remain uncategorized.
  Visible depth, height and width come directly from `FactoryBuildingTable.range`,
  also attached to the corresponding building items, without inventing a unit.
- `ShopGoodsTable.rewardId` joins `RewardTable.itemBundles` by exact identifier.
  Listings retain their authored currency, price, limits and unlock conditions
  from the goods, shop and shop group. Probabilistic reward bundles are never
  promoted to fixed item sources. Shop rows without a reward identifier remain
  explicit coverage gaps.
- Weapon breakthrough materials follow `WeaponBasicTable`'s explicit template
  reference into `WeaponBreakThroughTemplateTable`. Zero costs do not create
  material-use links. Weapon experience items, equipment enhancement costs,
  manual-upgrade mappings, recipe formula items and shop currencies form the
  remaining supported reverse uses. Their original source rows remain attached.

## Evidence boundary and remaining work

These joins prove stored configuration and identifier references, not current
availability, runtime unlocks, complete acquisition coverage or actual production
rates. Configured machine duration follows the exported UI's
`FactoryUtils.getCraftNeedTime` in `Common/Utils/FactoryUtils.lua`:
`progressRound * msPerRound / 1000` seconds. `totalProgress` remains a raw progress
field. Missing rounds or craft-group milliseconds leave duration unspecified;
hub and manual recipes do not acquire an invented duration. Recipe groups do not
imply alternatives. A missing source link means
the supported tables do not supply one; it does not mean an item is unobtainable.
Manual-upgrade rows are shown as mappings, without inventing an unstated consumed
quantity. There is no guessed join by label, naming convention or address order.

Character upgrade costs, gathering locations, task rewards, live shop state and
resolved unlock-condition explanations remain outside this publication. Building
renderer-template metadata is retained without inferring additional recipe
ownership. The page does not calculate production chains or effective rates.
The catalog index retains building wiki category order for device list grouping.
Group headers use the exact published category joins, with uncategorized devices
last; filtering still counts device records, not the continuous list’s group headings.
Items and recipes group by their first domain filter, with combined crafting
methods kept together. Recipe source/use references retain each original method's
gas environment rather than borrowing one requirement from a grouped recipe.
Building detail recipe lists group rows by the exact gas-environment ID and
display the requirement once per group. Recipes without a requirement remain
in a separate group; activity restrictions and formulas stay on each recipe.
Activity-only formula tags use exact craft-ID membership in
`LimitedFormulaCraftIdReverseTable`; matching activity `timeLimitFormula` lists
provide the forward join. The exported `FactoryUtils.isTimeLimitedFormula`
consumer checks this reverse table, and `FormulaCtrl` uses it for the limited-time
marker. This establishes stored classification and a direct Lua UI consumer,
not native-body validation or current runtime availability. Activity membership
is retained per method; a combined recipe's tag means it contains an activity
method, not that every method is activity-limited.
Recipes and machine recipe rows display nominal quantities per minute as
`count * 60 / durationSeconds`, preserving stored groups and method boundaries;
unknown or nonpositive durations do not produce rates. Required `gasEnv` values
join `FactoryEnvDisplayTable` exactly, retaining the numeric requirement and its
environment icon token. The frontend names those authored display tokens and
shows the corresponding exported `icon_gas_env_*` presentation icon; known
requirements display only the icon and name, while unknown requirements stay
visible by ID. This icon selection does not claim runtime asset ownership.

## Frontend contract

`webui/src/features/gameplay/items.js` mounts inside `#gameplay-catalog-app` under
`#gameplay-view`; `gameplay/tabs.js` owns shared dataset navigation. It uses
shared facets, regular-expression search,
category/direction sorting, continuous virtual scrolling, filter collapsing and Data file links.
There is one Items catalog including linked and unlinked buildings. Selection
uses `gameplayKind=item` with `gameplay=items:<id>` or `machines:<id>` and
`#gameplay`; search and repeated type/medal-category/building-category/relationship
filters use `item*` parameters. Retired routes and parameter aliases are not read.
Search determines membership; the chosen name/rarity order applies even with
multiple search terms. Catalog and relationship navigation resets filters and
sorting to match the destination URL; browser history restores the prior state.
Replacing the catalog clears its detail state and invalidates pending detail
requests, including failures. Display-setting events cannot revive an old
selection, and a pending copy action only updates its original button.
Source tables and the coverage audit follow the global Show debug info switch.
Normal views retain item relationships and meaningful availability limitations.
Item-type filters merge identical localized labels while retaining each original
type in the data. Building filters show encyclopedia groups and their available
icons. Item, recipe-output and building icons share the same compact lookup.
Character avatar items follow `UserAvatarTable.itemId` and its explicit icon
reference, selecting a square image for character heads. Filled bottle and gas
jar icons overlay the exact `FullBottleTable.liquidId` or `FullGasJarTable.gasId`
item icon at the center, matching the exported `UI/Widgets/ItemIcon.lua` layout
(content side length `80/180` of the container). Achievement tiers retain the
stored ItemTable icon; achievement-ID/level filename construction cannot override
that direct reference. A single authored tier displays Level 1 while retaining
its original `sourceLevel` for evidence; multiple tiers keep their authored levels.
Recipes with the same complete set of positive output item IDs share an entry.
`recipeVariants` preserve each source recipe's nested groups, counts, machine,
conditions and configured duration; differing co-products stay separate.
The builder writes the current recipe `groupId` on each reverse reference and
the current item `catalogId` on every item bundle. Alias maps remain internal
to authored grouping and Updates source comparison; they are not published or
used for browser selection conversion.
Every method shows production time and expanded conditions/configuration in two
columns, stacking on narrow screens. These display groups do not imply one
combined craft or establish that methods are interchangeable at runtime.
Machines display `powerConsume` as electricity consumption and dimensions as
depth × width × height. Their recipe rows include each source method's full
ingredient/output groups and quantities plus processing time, with a link to
the output item's recipe. The builder embeds these method summaries before recipe
grouping, so a machine row never borrows another method's time or quantities.
Descriptions render expanded through Story's safe rich-text renderer, including
bold and named emphasis tags, and follow the shared raw-tag display setting.
Empty relationship sections are omitted.

The shared update badges read `updates/gameplay.json`. The Updates builder
compares the same catalog joins over both exports' authored source rows and
common localized text. Item, recipe, machine and grouped medal identities use
`<kind>:<id>` keys. Limited-item groups retain both raw item rows and their
`LTItemTable` mapping in the same comparison identity. UI changes and icon
display preferences create no game update.
Usage receipts retain their declared source fields; a weapon's unrelated
statistics do not become material changes. Ingredient labels and linked machine
footprints are terminal views, so recipe comparisons do not traverse each
ingredient's own production and usage network. Entity comparisons use explicit
field-to-table ownership joins, with shared skills retained for each actual owner.
Loadout picker option lists are excluded from shared resource-update collection
and decoration. Only their selected summary previews participate, so unselected
equipment does not become character resource changes.

Fixture tests in the local `scripts/tests/test_build_production.py` cover exact
joins, nested groups, zero-cost rejection, probabilistic shop boundaries,
unresolved identifiers, input failures and shard/index publication consistency.
They also cover localized type merging, exact encyclopedia joins, dimensions,
full-size icon selection, Sprite-only fallback and rejection of similar names.
`test_production_categories.py` covers output categories, medal ownership and
plating, old identifiers, and the scope and field details of Gameplay items updates.
`test_production_limited_items.py` covers explicit mapping, divergent and missing
targets, relationship preservation, aliases and grouped update provenance.
`scripts/tests/gameplay_item_filters.cjs` checks selection retention, filtered-out selection, empty results, reset and URL writes against the real filter function. Browser smoke checks cover combined type/relationship tags, switching datasets, recipes and linked media.

Item recipe references resolve the original source ID within `recipeVariants`
before rendering a grouped recipe. Each source retains its own machine, groups,
time and environment; a grouped catalog entry is not a combined formula.
Shop cards group identical published configuration fields, excluding goods ID
and source links, and label the number of matching configurations. All goods
IDs and source links remain available; this grouping does not prove runtime
availability or merge the underlying goods. Raw goods can differ in sorting
even when the published display fields match.

Item and recipe pages share the compact method row: activity tag, machine,
gas environment, formula and processing time. Item/machine rows link to the
recipe page; recipe rows omit that self-link and retain supplemental formula
items, conditions and stored configuration below the row. Empty metadata
columns retain their width so formulas align across source methods.

Item media follows exact PictureItemTable → PictureTable.imgId,
BusinessCardTopicTable.itemId → id, SnapshotStickerTable.itemId → icon and
UserAvatarTable.itemId → icon bindings. These tokens and ItemTable.modelKey
are published in summaries and details with source receipts. The asset sidecar
selects one exported representation per complete media basename separately
from inventory icons; it does not claim runtime asset ownership from a name
match. Focused AnimeStudio Table dumps with VFS MD5 verification established
byte equality between the installed ItemTable and these five media tables and
their published decoded exports. This proves the stored fields and exact table
joins, rather than runtime UI consumption. Avatar icons use the explicit
UserAvatarTable reference; grouped medals retain their source ItemTable icons.
Singleton displayed types share the Other facet and list group while
the original type remains visible in details. Story wiki links use the shared
Gameplay button component.


物品目录由 Gameplay 的 `items` 阶段发布，图片关联在随后 `asset-refs` 阶段读取该目录；所有更新标记使用 Gameplay sidecar。筛选变更保留仍匹配的选中项，否则选择第一个匹配项；空结果清空选中项和详情，URL 同步当前筛选与选中项。

Item pictures, themes, stickers and inventory icons share the bottom Assets section and Gameplay’s existing section heading/image-model strip. The strip and image thumbnails reuse the weapon/Essence rounded borders and gray backgrounds; no separate illustration is inserted above the description.

Medal list/header/tier portraits use the achievement's source level artwork
token (`<achievement>_lvNN`, with `_plating` for plated tiers) as an explicit
presentation choice. The authored generic inventory icon is retained unchanged
and remains in the Assets strip alongside the displayed medal artwork. Missing
medal artwork leaves the portrait empty, without a generic-icon fallback.

Item storage limits appear in header metadata only for finite values greater than one. Equal storage/backpack limits share one label; different limits retain explicit storage/backpack labels. Building buffer limits remain separately labeled. Sentinel/default values are omitted without claiming unlimited storage. Raw item/building/recipe configuration remains available behind Show debug info; source identifiers, booleans and anonymous enums are not normal-view metadata.

Weapon and equipment records link both ways between Gameplay’s Items and their respective datasets using exact matching IDs in the displayed language. Header buttons appear only when the target exists in the current publication, share the Story Wiki button style, and sit beside it in one wrapping row using shared dataset routing.

Record item headers link to the Audio page's full-track and sample Event records
through the exact SpaceshipMusicTable item key and musicEvent/musicEventSample
fields. A focused VFS-MD5-verified binary decode reproduced that published table
byte-for-byte. The links prove stored configuration, not resolved media or runtime
playback. Empty fields and items without a music row expose no inferred links.
Audio publishes `lang/<LANG>/audio/record_media.json` from exact SpaceshipMusicTable
event contexts and its current decoded media candidates. Gameplay reads that
optional publication and adds audio controls below images in the same Assets
section. It publishes only its own table references and never rewrites Audio
data. Missing media yields no player; multiple leaves remain candidate audio.

Spaceship exhibit model links follow the exact item key in
SpaceshipShowcaseItemTable and its resPath prefab basename. A VFS-MD5-verified
binary table decode reproduced the published table. Assets keeps Animator/Mesh
container memberships keyed by Unity type and PathID, retaining all memberships
for shared objects. Gameplay joins only the complete prefab basename, selects
an Animator when available or a highest-detail Mesh otherwise, and records
`showcase-prefab-pathid` direct evidence. This identifies a stored prefab member,
not runtime placement, and does not infer a model from an item's icon or name.
The remaining `item_spaceship_exhibits_tundra_4` (生机盆景, the CN ItemTable.name
localization; its description identifies a source-stone sapling model) gap is its
`spaceship_showcase_item002` prefab: AssetMap lists the SpaceshipShowcaseItem
component, whose indexed fields describe camera offsets and whose PPtrs join
the prefab root and script, but supplies no direct Mesh/Animator membership.
This does not prove that the rendered exhibit lacks geometry; its model join
remains unresolved. At the user's request, gameplay_assets.json supplies the
temporary S_crystal_tree+1_001_01 LOD0 display model, labeled as a temporary
manual selection with conditional evidence. This does not close the prefab
ownership gap; a direct prefab model join takes priority if one is recovered.

Quest items (authored ItemTable type 13) also include exported `reading_`/`read_` illustrations when the complete suffix matches their item ID or icon ID after removing the item/mission/quest prefix. This is a conditional display association, recorded as `quest-reading-name`, rather than proof of a runtime reading or mission join. Full basename matching rejects partial and numeric-prefix collisions. The largest original is preferred over cropped Sprite representations. Quest portraits prioritize the directly authored icon, including generic document icons. Reading artwork stays in the bottom Assets strip as supplemental conditional evidence. Filename matching and manual selections cannot replace an authored icon; a missing matching icon asset leaves the portrait empty.

Factory device and decoration models use the default FactoryBuildingTable
renderer template; logistics first joins FactoryItem2LogisticIdTable to its
typed connector/router/valve table. The asset-ref stage reads the effective
published object index and exact AssetMap membership of FactoryUnitConfigAsset.
Only lodSettings renderer m_mesh PPtrs can supply model links, resolved to a
unique published Mesh PathID at the highest stored detail. Composite configs
follow resolved subAssets PPtrs by serialized-file/PathID identity, recording
the complete config chain before reading each part's renderer mesh. Collider meshes,
materials and ItemTable's generic int_drop_building are excluded. Missing or
ambiguous targets produce no model. Exact render-resource/config joins are
direct; segmented config names under a resource prefix remain conditional
owner candidates even though their Mesh PPtrs are explicit. The evidence is
stored configuration, not a claim about runtime assembly or placement.

Character attribute talent nodes store their modifiers directly in
`attributeNodeInfo.attributeModifiers`, not a nested `attributeModifier` object.
The base builder publishes these under each talent level's
`attributeModifier.attributeModifiers`. Loadout affinity-talent selection sums
unlocked nodes through the chosen stage, bounded by the selected breakthrough;
the default selects every available stage. Affinity requirements and modifier
sources remain visible. Concrete authored targets are retained rather than
replaced with an assumed main-ability target or parsed from localized prose.
