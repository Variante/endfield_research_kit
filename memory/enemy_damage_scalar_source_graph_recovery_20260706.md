# Enemy Damage Scalar Source Graph Recovery - 2026-07-06

## Scope

The original-data understanding report still marks numerical systems as only
moderately understood because formulas and runtime evaluators remain partial.
This pass narrows one combat-damage slice: enemy damage-taken scalar tables,
their graph representation, and the boundary between authored scalar evidence
and runtime damage-pipeline proof.

## Raw Table Evidence

Primary enemy scalar definitions:

- `export_full/structured/StreamingAssets/Table/EnemyDamageTakenLevelTable.json`
  - 5 rows.
  - Defines `damageTakenLevel` to `damageTakenScalar`.
  - Values:
    - level `1`: `0.0`
    - level `2`: `0.2`
    - level `3`: `0.5`
    - level `4`: `0.8`
    - level `5`: `1.0`
  - Row `name.text` values are empty, with localization ids present, so the
    numeric scalar values look authored/mechanical rather than localized
    display text.

Per-enemy-template damage scalar definitions:

- `export_full/structured/StreamingAssets/Table/EnemyAttributeTemplateTable.json`
  - 113 rows.
  - Every row has:
    - `physicalDmgResistScalar`
    - `fireDmgResistScalar`
    - `pulseDmgResistScalar`
    - `crystDmgResistScalar`
    - `naturalDmgResistScalar`
  - Value ranges:
    - physical: `0.4` to `1.0`
    - fire: `0.5` to `1.0`
    - pulse: `0.8` to `1.0`
    - cryst: `0.8` to `1.0`
    - natural: `0.7` to `1.0`

Representative attribute-template rows:

- `eny_0007_mimicw`: natural `0.7`, all other listed scalar fields `1.0`.
- `eny_0023_aghornb`: physical/fire/natural `0.8`.
- `eny_0027_agscorp`: physical/fire/natural `0.8`.
- `eny_0039_agcanno`: physical/fire/natural `0.8`.
- `eny_0018_lbtough`: all listed scalar fields `1.0`.

Related composite/display metadata:

- `CompositeAttributeTable.json`
  - Defines `AllDamageTakenScalar` from:
    - `PhysicalDamageTakenScalar`
    - `FireDamageTakenScalar`
    - `PulseDamageTakenScalar`
    - `CrystDamageTakenScalar`
    - `NaturalDamageTakenScalar`
    - `EtherDamageTakenScalar`
  - No literal `MagicDamageTakenScalar` row was found in this scan.
- `CompositeAttributeShowConfigTable.json`
  - `AllDamageTakenScalar` has display config using
    `valueFormat="{1-value:0.0%}"`, `showPercent=true`, and `isReduce=true`.
  - This is display formatting for scalar values, not the primary enemy scalar
    source.
- `AttributeFilterTable.json`
  - Contains a filter entry for `compositeAttr="AllDamageTakenScalar"`.

Related non-enemy equipment usage:

- `EquipTable.json`
  - 220 rows total.
  - 8 rows reference `compositeAttr="AllDamageTakenScalar"`.
  - Representative ids:
    - `item_equip_t1_suit_stragi01_body_01`
    - `item_equip_t1_suit_stragi01_edc_01`
    - `item_equip_t1_suit_stragi01_hand_01`
  - These look like authored equipment scalar modifiers using the same
    composite display family.

Related WebUI game-data group:

- `webui/data/game_data/groups/Json_BuffData.json`
  - 4,616 entries.
  - 94 entries matched `damage_taken`, `taken_damage`, or `vulnerable`.
  - Representative ids:
    - `buff_chr_0013_aglina_damage_taken_scale`
    - `buff_chr_0013_aglina_damage_taken_scale_talent0`
    - `buff_common_poise_break_damage_taken_scale`
    - `buff_dung_damage_taken_scale`
    - `buff_common_affixes_vulnerable_physical`
  - This group exposes ids, params, tags, and schema hints, but not enough here
    to prove full decoded numeric modifier payload semantics.

## Graph Validation

The normal ignored graph database currently predates the newest enemy scalar
edge families, so this pass validated against a custom temp database:

```bat
python tools\endfield_source_graph.py build --db %TEMP%\enemy_damage_scalar_validate.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The build populated the custom SQLite database but exposed a tooling bug: the
summary writer still tried to write `reports/source_graph/summary.json` even
for custom `--db` builds. This pass fixes that so custom DB builds write
`summary.json` and `summary.md` beside the custom database, while default builds
keep the existing `reports/source_graph/` summary location.

Validated temp graph node counts:

- `enemy_damage_taken_level`: 5
- `enemy_attribute_template`: 113
- `gameplay_stat_property`: 89

Validated temp graph edge counts:

- `enemy_attribute_template_sets_damage_taken_scalar`: 565
- `damage_taken_scalar_set_by_enemy_attribute_template`: 565
- `defines_enemy_attribute_template`: 113
- `uses_enemy_attribute_template`: 360

Per-stat scalar edge counts from `EnemyAttributeTemplateTable`:

| Stat key | Edges | Min | Max |
| --- | ---: | ---: | ---: |
| `physical_damage_taken_scalar` | 113 | 0.4 | 1.0 |
| `fire_damage_taken_scalar` | 113 | 0.5 | 1.0 |
| `pulse_damage_taken_scalar` | 113 | 0.8 | 1.0 |
| `cryst_damage_taken_scalar` | 113 | 0.8 | 1.0 |
| `natural_damage_taken_scalar` | 113 | 0.7 | 1.0 |

`stat-usage all_damage_taken_scalar` against the temp DB now reports:

- 5 `enemy_damage_taken_level_scales_stat_property` edges.
- 5 reverse `stat_property_scaled_by_enemy_damage_taken_level` edges.
- 8 equipment `scales_stat_property` edges from WebUI gameplay progression
  data.

`stat-usage physical_damage_taken_scalar` against the temp DB reports:

- 1 `attribute_meta_has_stat_property` edge.
- 113 `enemy_attribute_template_sets_damage_taken_scalar` edges.
- 113 reverse `damage_taken_scalar_set_by_enemy_attribute_template` edges.

## Interpretation

This slice gives strong static evidence for two related but distinct mechanics:

- `EnemyDamageTakenLevelTable` defines a five-step all-damage-taken scalar ladder
  from `0.0` through `1.0`.
- `EnemyAttributeTemplateTable` defines per-enemy-template damage resist/taken
  scalar fields for physical, fire, pulse, crystal, and natural damage families.

The naming is slightly mixed:

- Raw fields use `*DmgResistScalar`.
- Graph stat keys normalize them as `*_damage_taken_scalar` because they map
  into the same display/composite attribute family.
- Display config formats `AllDamageTakenScalar` as `1 - value`, so lower
  authored values likely display as larger reduction percentages.

This is authored table semantics, not runtime damage formula proof. It does not
establish where in the runtime damage pipeline these scalars are applied,
whether any buff/action modifies them before use, or the final modifier order
with defense, vulnerability, shields, resilience, or damage-type conversion.

## Tooling Changes

- Custom `build --db ...` source-graph runs now write `summary.json` and
  `summary.md` beside the requested custom database instead of always writing
  under `reports/source_graph/`.
- `stat-usage` output now includes caveats stating that it reports authored
  static stat/attribute evidence and does not simulate runtime formula
  evaluation, modifier order, or the damage pipeline.

## Next Checks

- Rebuild the normal ignored source graph when broader report refresh is useful
  so `reports/source_graph/endfield_source_graph.sqlite` includes the enemy
  scalar edge families.
- Follow representative BuffData entries such as
  `buff_common_affixes_vulnerable_physical` and
  `buff_common_poise_break_damage_taken_scale` into parameter/action decoding
  to see whether buff-side damage-taken modifiers can be bridged to the same
  stat keys.
- Search IL2CPP/runtime metadata for consumers of `DamageTakenScalar`,
  `DmgResistScalar`, and composite attribute display formatting to separate
  authored values from runtime evaluator order.
