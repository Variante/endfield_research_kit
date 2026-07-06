# Factory Utility Numeric Semantics - 2026-07-06

## Question

`memory/original_game_data_understanding_report_20260701.md` lists numerical
systems as a major remaining semantic gap: many rows and fields are decoded,
but runtime formulas and evaluators are still only partially understood. This
pass checks one bounded authored slice: factory power, miner, fuel, battery,
liquid, and sewage-treatment utility tables.

## Evidence Sources

Primary source rows:

- `export_full/structured/StreamingAssets/Table/FactoryMinerTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryFuelItemTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryBatteryItemTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryPowerStationTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryPowerPoleTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryFluidPumpInTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryFluidPumpOutTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryFluidConsumeTable.json`
- `export_full/structured/StreamingAssets/Table/FactoryFluidContainerTable.json`
- `export_full/structured/StreamingAssets/Table/FactorySewageTreatImportTable.json`
- `export_full/structured/StreamingAssets/Table/FactorySewageTreatExportTable.json`
- `export_full/structured/StreamingAssets/Table/FactorySewageTreatPlantStoreTable.json`
- `export_full/structured/StreamingAssets/Table/LiquidTable.json`
- `export_full/structured/StreamingAssets/Table/I18nTextTable_CN.json`

Current source graph evidence:

- `factory_miner`: 4 nodes
- `factory_fuel`: 6 nodes
- `factory_battery`: 5 nodes
- `factory_power_station`: 1 node
- `factory_power_pole`: 4 nodes
- `factory_hub_power`: 2 nodes
- `factory_power_data_type`: 5 nodes
- `factory_productivity_data_type`: 5 nodes
- `factory_liquid`: 11 nodes
- `factory_fluid_machine`: 17 nodes
- `factory_sewage_level`: 4 nodes
- `sewage_treat_plant`: 1 node

The `factory-flow` command reports the same boundary on representative
queries: `authored_factory_config_evidence_only` and
`not_runtime_logistics_power_or_throughput_simulation`.

## Authored Numeric Profiles

### Miners

`FactoryMinerTable` defines four miner tiers:

| Miner | Drone mode | Round ms | Transfer cooldown ms | Mineable outputs | Extra consume |
| --- | --- | ---: | ---: | --- | --- |
| `miner_1` | false | 3000 | 0 | originium ore | none |
| `miner_2` | true | 3000 | 10000 | originium ore, quartz sand | none |
| `miner_3` | true | 3000 | 10000 | originium ore, quartz sand, iron ore | none |
| `miner_4` | true | 3000 | 10000 | originium ore, quartz sand, iron ore, copper ore | 1 water per output |

Each listed `mineable` entry has `produceRate=1`. `miner_4` is the first tier
where mining consumes `item_liquid_water`, one unit per listed output. The
table therefore proves authored per-tier capability expansion and one water
gating rule, but not the full live mining scheduler.

### Fuel And Batteries

`FactoryFuelItemTable` defines fuel use for originium ore plus five processed
battery items:

| Fuel item | Fuel energy | Power provide | Progress rounds |
| --- | ---: | ---: | ---: |
| `item_originium_ore` | 48000 | 50 | 8 |
| `item_proc_battery_1` | 240000 | 220 | 40 |
| `item_proc_battery_2` | 240000 | 420 | 40 |
| `item_proc_battery_3` | 240000 | 1100 | 40 |
| `item_proc_battery_4` | 240000 | 1600 | 40 |
| `item_proc_battery_5` | 240000 | 3200 | 40 |

`FactoryBatteryItemTable` separately assigns stored battery energy:

| Battery item | Battery energy |
| --- | ---: |
| `item_proc_battery_1` | 8800 |
| `item_proc_battery_2` | 20800 |
| `item_proc_battery_3` | 54000 |
| `item_proc_battery_4` | 72000 |
| `item_proc_battery_5` | 152000 |

The source graph links these rows to item ids, but the two energy scales should
not be collapsed into one formula without runtime proof. `fuelEnergy` and
`batteryEnergy` are authored in different tables and likely serve different
systems.

### Power Generation And Network Geometry

`FactoryPowerStationTable` has one power-station profile:

```text
power_station_1: msPerRound=1000, powerProvide=150
```

`FactoryHubTable` contributes hub-level power storage/generation profiles:

| Hub | Power generate | Power storage capacity |
| --- | ---: | ---: |
| `sp_hub_1` | 200 | 100000 |
| `sp_sub_hub_1` | 0 | 100000 |

`FactoryPowerPoleTable` defines authored connection/diffusion geometry:

| Pole | Auto connect | Auto connect length | Wire start | Diffuser enabled | Range extend |
| --- | --- | ---: | --- | --- | --- |
| `power_diffuser_1` | false | 30 | false | true | 5,5,5 |
| `power_diffuser_2` | true | 30 | true | true | 5,5,5 |
| `power_pole_2` | false | 80 | true | false | 2,10,2 |
| `power_pole_3` | true | 80 | true | true | 2,10,2 |

The table proves authored power range and connection defaults. It does not
prove the runtime pathfinding, wire validation, loss model, or power-grid
simulation.

### Liquids And Fluid Machines

`LiquidTable` defines 11 liquid ids and bottle conversions. Most liquids have
six empty/full bottle pairs; `item_liquid_plant_grass_2` has seven, adding the
activity xirang enriched bottle pair.

`FactoryFluidPumpInTable`:

- `pump_1`: `msPerRound=1000`, accepts water, sewage, plant liquids, xirangite
  liquids, and copper liquids.
- `pump_2`: `msPerRound=1000`, accepts the same set plus acid.

`FactoryFluidConsumeTable`:

- `liquid_cleaner_1`: `msPerRound=2000`, consumes sewage and low/poly xirangite
  liquids.

`FactoryFluidContainerTable`:

- `liquid_storager_1`: capacity `500`
- `liquid_storager_nop_1`: capacity `10`

`FactoryFluidPumpOutTable`:

- `dumper_1` and `dumper_nop_1`: `maximumSuply=3` in the source row. The field
  name is spelled this way in the exported table.

`FactorySewageTreatImportTable`:

- `liquid_clean_gate_1`: `msPerRound=500`, accepts sewage.

`FactorySewageTreatExportTable`:

- `liquid_recycle_gate_1`: consumes `30`, produces `1`, and outputs
  `item_liquid_xiranite_poly`.

These rows recover the authored machine constants for pump/clean/storage/export
behavior. They still do not prove how the live liquid network schedules pulls,
pushes, buffering, or simultaneous machine updates.

### Sewage Treatment Store Levels

`FactorySewageTreatPlantStoreTable` defines one plant,
`liquidcleanfactory_005_1`, in `domain_2` and level `map02_lv005`.

| Level | Cost | Import level | Action | Action params | CN text meaning |
| --- | ---: | --- | ---: | --- | --- |
| 1 | 0 | true | 5114 | `map02_lv005`, `map02_lv005_liquid_clean_gate_1` | Unlock clean-water node |
| 2 | 250000 | true | 5114 | `map02_lv005`, `map02_lv005_liquid_clean_gate_2` | Increase sewage treatment capacity |
| 3 | 450000 | true | 5114 | `map02_lv005`, `map02_lv005_liquid_clean_gate_3` | Further increase sewage treatment capacity |
| 4 | 1200000 | false | 5114 | `map02_lv005`, `map02_lv005_liquid_recycle_1` | Obtain sewage treatment products |

The CN UI strings from `I18nTextTable_CN` make the level semantics stronger
than field names alone: levels 1-3 are clean-node unlock/capacity upgrades, and
level 4 unlocks treatment products.

## Current Understanding

This slice improves numerical semantics from "rows are linked" to "authored
factory utility profiles are interpretable":

- millisecond fields (`msPerRound`, `msTransferCD`) are authored cycle/cooldown
  constants;
- fuel rows combine energy, provided power, and progress-round counts;
- battery rows use a separate stored-energy scale;
- power poles encode connection defaults and range extents;
- liquid rows encode bottle conversion sets;
- sewage store levels encode unlock/capacity/product stages with explicit
  action params and UI text.

The important boundary is that these are static authored constants. This pass
does not prove the runtime equations for throughput, power load balancing,
liquid network transfer, drone mining behavior, world upgrade state, or account
progression.

## Next Checks

- Look for runtime or MonoBehaviour code that consumes `msPerRound`,
  `msTransferCD`, `fuelEnergy`, `powerProvide`, and `BatteryEnergy`.
- Compare the factory utility constants against recipe timings and machine
  power costs to see whether a consistent unit model emerges.
- Add graph edges for the nested miner `consumeItem.count` and
  `produceRate` fields if WebUI queries need direct item-count semantics.
- Consider normalizing the source typo `maximumSuply` only at a presentation
  layer; preserve the raw field spelling in source-backed evidence.
