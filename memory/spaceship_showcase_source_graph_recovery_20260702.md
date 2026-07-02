# Spaceship Showcase Source Graph Recovery - 2026-07-02

## Scope

Extended the existing spaceship semantic graph pass to cover remaining small
spaceship/social lookup tables:

- `SpaceshipGrowCabinBoxIdToUnlockLevelTable.json`
- `SpaceshipShowcaseItemTable.json`
- `SpaceshipShowcaseTable.json`
- `SpaceshipShowcaseBySortIdTable.json`
- `SpaceshipBuildTypeTable.json`
- `SpaceshipGrowCabinFormulaShowingTypeTable.json`
- `SpaceshipCreditTable.json`
- `SpaceshipClueGoodsPriceConvertDataTable.json`
- `SpaceshipCharRelationNeedMap.json`
- `SpaceshipCharRelationLevelTable.json`
- `SpaceshipCharGiftGainRatio.json`

## Recovered Semantics

- Grow-cabin box ids now link to spaceship room level unlock nodes.
- Showcase item rows now link exhibit items to item nodes, asset stems, and tag
  taxonomy nodes.
- Showcase category rows now expose named showcase nodes and sort-id lookup
  nodes.
- Spaceship build type groups now expose their contained build type ids.
- Grow-cabin formula showing types now expose localized names and icon asset
  aliases.
- Credit conversion tiers now expose total price and credit reward counts for
  both credit tables.
- Character relation thresholds now expose required favorability and relation
  level description text.
- Gift gain-ratio rows now expose gain ratio and per-tier maximum limit
  metadata.

## Validation

Command:

```bat
python tools\endfield_source_graph.py build --db tmp\spaceship_showcase_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1627305 nodes, 3054624 edges, 2233343 aliases
```

Target node counts:

```text
spaceship_showcase_item 8
spaceship_showcase 7
spaceship_showcase_sort 7
spaceship_build_type_group 5
spaceship_build_type 5
spaceship_grow_cabin_box_unlock 9
spaceship_formula_showing_type 4
spaceship_credit_tier 4
spaceship_relation_need 3
spaceship_relation_level 3
spaceship_gift_gain_ratio 3
```

Notable edge counts:

```text
defines_spaceship_credit_tier 8
defines_spaceship_showcase 14
spaceship_showcase_item_tag 17
spaceship_grow_cabin_box_unlock_level 9
spaceship_showcase_sort_refs_showcase 7
uses_i18n_text 42
```

## Next Candidate

The sidecar explorer and local coverage scan both point to domain/settlement
core tables as the next high-value gap:

- `DomainDataTable.json`
- `SettlementBasicDataTable.json`
- `DomainDegreeSourceTable.json`
- possibly `MissionTypeInfoTable.json`

These connect domains, maps/levels, settlements, shops, factory tech packages,
trade items, and settlement progression.
