# Mode Constant Source Graph Recovery - 2026-07-02

## Scope

Recovered first-class graph coverage for compact scalar constant tables that
were still outside the named semantic table groups:

- `AchievementConst`
- `BattleConst`
- `BlocConst`
- `FactorySocialBuildingConst`
- `GemConst`
- `KiteStationConst`
- `LoadingConst`
- `NotifyPushConst`
- `SceneConst`
- `ShopWeaponConst`
- `SnapshotConst`
- `TrackMapConst`
- `WeekRaidConst`

These tables encode cross-system numerical and mode rules rather than large
row-shaped catalogs. Examples include combat coefficient values in
`BattleConst`, gem enhancement constants in `GemConst`, week-raid timeout and
reward rules in `WeekRaidConst`, default scene/loading values, and small
feature timing thresholds.

## Graph Model

The source graph already had a `mode_const` model for similar compact mode
tables such as `FactoryConst`, `DungeonConst`, `ActivityConst`,
`BattlePassConst`, and `CashShopConst`.

The recovery extends that existing path instead of creating parallel constant
families:

- Add the remaining scalar constant tables to `MODE_CONSTANT_TABLES`.
- Derive `MODE_CONST_TABLES` from the table list so any listed `*Const` table
  flows through the same handler.
- Emit one `mode_const` node per row with `{table, key, value}` data.
- Preserve `defines_mode_const` edges from the original table row.
- Reuse `add_constant_ref_edges` for parseable references embedded in constant
  values.

## Validation

Built a focused temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\mode_constants_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1628550 nodes, 3057507 edges, 2235059 aliases
```

Focused semantic counts:

```text
NODE mode_const total 293
EDGE defines_mode_const total 293
AchievementConst                 nodes=  3 edges=  3
BattleConst                      nodes= 12 edges= 12
BlocConst                        nodes=  1 edges=  1
FactorySocialBuildingConst       nodes=  3 edges=  3
GemConst                         nodes=  3 edges=  3
KiteStationConst                 nodes=  1 edges=  1
LoadingConst                     nodes=  1 edges=  1
NotifyPushConst                  nodes=  2 edges=  2
SceneConst                       nodes=  1 edges=  1
ShopWeaponConst                  nodes=  1 edges=  1
SnapshotConst                    nodes=  2 edges=  2
TrackMapConst                    nodes=  3 edges=  3
WeekRaidConst                    nodes= 10 edges= 10
```

Sample recovered combat constants include `atkRateOfMain`,
`enemyOHKCoefficient`, `maxUltimateSp`, and
`poiseBreakDamageLevelModifier` from `BattleConst`.
