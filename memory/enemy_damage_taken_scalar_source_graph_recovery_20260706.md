# Enemy Damage-Taken Scalar Source Graph Recovery - 2026-07-06

## Scope

This is a P7 damage-path improvement for authored enemy damage-taken scalar
evidence. It does not recover the runtime damage formula, `DamageAction`
`DamageUnit` internals, modifier order, or IL2CPP evaluator execution.

## Change

`tools/endfield_source_graph.py` now links two enemy damage-scalar sources into
the existing stat/composite attribute vocabulary.

`EnemyDamageTakenLevelTable` rows now emit:

- `enemy_damage_taken_level_scales_stat_property`
- `stat_property_scaled_by_enemy_damage_taken_level`
- `enemy_damage_taken_level_scales_composite_attribute`
- `composite_attribute_scaled_by_enemy_damage_taken_level`

Those edges connect the five authored `damageTakenScalar` tiers to
`gameplay_stat_property:all_damage_taken_scalar` and
`composite_attribute:AllDamageTakenScalar`.

`EnemyAttributeTemplateTable` rows now emit:

- `enemy_attribute_template_sets_damage_taken_scalar`
- `damage_taken_scalar_set_by_enemy_attribute_template`

The field-to-stat mapping is:

- `physicalDmgResistScalar` -> `physical_damage_taken_scalar`
- `naturalDmgResistScalar` -> `natural_damage_taken_scalar`
- `fireDmgResistScalar` -> `fire_damage_taken_scalar`
- `crystDmgResistScalar` -> `cryst_damage_taken_scalar`
- `pulseDmgResistScalar` -> `pulse_damage_taken_scalar`

## Validation

Validated with an enemy-only temp source graph smoke build:

```bat
python - <<SMOKE
from pathlib import Path
from tools.endfield_source_graph import SourceGraphBuilder
b = SourceGraphBuilder(db_path=Path('tmp/enemy_damage_taken_scalar_smoke.sqlite'), include_gameplay=False, include_asset_maps=False, include_reference_rows=False, emit_followups=False)
b.open()
b.ingest_enemy_semantics()
b.close()
SMOKE
```

Counts from `tmp/enemy_damage_taken_scalar_smoke.sqlite`:

- `enemy_damage_taken_level_scales_stat_property`: 5
- `stat_property_scaled_by_enemy_damage_taken_level`: 5
- `enemy_damage_taken_level_scales_composite_attribute`: 5
- `composite_attribute_scaled_by_enemy_damage_taken_level`: 5
- `enemy_attribute_template_sets_damage_taken_scalar`: 565
- `damage_taken_scalar_set_by_enemy_attribute_template`: 565

Sample tier edge payload:

```json
{
  "damageTakenLevel": 1,
  "damageTakenScalar": 0.0
}
```

Sample enemy attribute-template edge payload:

```json
{
  "field": "crystDmgResistScalar",
  "statKey": "cryst_damage_taken_scalar",
  "value": 1.0
}
```

## Boundary

This makes authored enemy damage-taken scalar data queryable by stat property
and composite attribute. It is static table evidence only. The graph still does
not prove which runtime evaluator consumes these scalars, how they compose with
buffs/equipment/potential modifiers, or how final damage is calculated.
