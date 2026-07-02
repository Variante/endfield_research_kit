# Domain Core Source Graph Recovery - 2026-07-02

## Scope

Added a `DOMAIN_CORE_TABLES` source graph pass for the central domain and
settlement progression spine:

- `DomainDataTable.json`
- `SettlementBasicDataTable.json`
- `DomainDegreeSourceTable.json`
- `MissionTypeInfoTable.json`

## Recovered Semantics

- Domain rows now update canonical `gameplay_domain` nodes with names and core
  metadata, then link to domain map, shop group, factory tech package, domain
  money item, POI types, machine-mode types, kite stations, asset aliases, and
  domain UI audio events.
- Domain development levels now expose `domain_development_level` nodes with
  level-up EXP, money cap, reward, and version metadata.
- Per-map domain development effects now expose `domain_level_effect` nodes
  linked to the affected level with bandwidth, battle-building limit,
  travel-pole limit, and mine-output metadata.
- Settlement rows now expose `settlement` nodes linked to their domain, level,
  settlement POI, localized name, and wanted tag group.
- Settlement levels now expose progression nodes with EXP, money, production
  period, bandwidth, battle-building limits, travel-pole limits, picture asset,
  recommended item, and upgrade mission refs.
- Settlement trade item maps now expose one `settlement_trade_item` node per
  settlement-level item, linked to item and optional activity refs with money
  and settlement-EXP yields.
- Domain degree sources now expose localized source-type nodes.
- Mission type metadata now exposes mission type and mission view type nodes.

## Validation

Command:

```bat
python tools\endfield_source_graph.py build --db tmp\domain_core_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1627803 nodes, 3055638 edges, 2233975 aliases
```

Target node counts:

```text
domain_development_level 30
domain_level_effect 180
domain_machine_mode_type 2
domain_degree_source 11
mission_type_info 11
mission_view_type 5
settlement 5
settlement_level 19
settlement_trade_item 135
settlement_poi 5
shop_group 20
```

Notable edge counts:

```text
domain_has_development_level 30
domain_development_level_has_effect 180
domain_level_effect_applies_to_level 180
domain_development_level_reward 28
domain_has_level 12
domain_has_settlement 5
settlement_has_level 19
settlement_level_has_trade_item 135
settlement_trade_item 135
settlement_trade_item_activity 14
settlement_level_upgrade_mission 15
domain_degree_source_name_text 11
mission_type_uses_view_type 11
```

## Next Candidate

The next high-value uncovered cluster is remaining factory domain/transfer
operation metadata:

- `FactoryItemShowingHubTable.json`
- `FactoryDomainItemTransmissionTable.json`
- `FactoryMachineCraftModeTable.json`
- `FactoryFluidConsumeItemTable.json`
- `FactoryUndergroundPipeTable.json`

That would connect domain hub item visibility, inter-domain transfer capacity,
machine mode labels, fluids, and underground pipe throughput to the factory
graph.
