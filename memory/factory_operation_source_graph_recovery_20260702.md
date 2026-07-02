# Factory Operation Source Graph Recovery - 2026-07-02

## Scope

Recovered semantic graph coverage for remaining compact factory operation and
domain-transfer tables:

- `FactoryItemShowingHubTable.json`
- `FactoryDomainItemTransmissionTable.json`
- `FactoryMachineCraftModeTable.json`
- `FactoryRendererTemplateTable.json`
- `FactoryFluidConsumeItemTable.json`
- `FactoryUndergroundPipeTable.json`

## Recovered Semantics

- Factory hub item visibility now exposes one domain-keyed
  `factory_hub_item_showing` node per domain and links visible factory items to
  canonical item nodes.
- Domain item transmission now exposes domain-keyed transmission nodes and
  per-level capacity nodes with route count, unlock level, lossless unlock
  level, capacity, and final-capacity markers.
- Machine craft modes now expose localized `factory_machine_craft_mode` nodes
  with name, description, sort order, and icon aliases.
- Renderer template wrapper rows now link a base renderer template to explicit
  per-level render ids.
- Fluid consume item mappings now link liquid items to allowed factory
  buildings and liquid nodes.
- Underground pipe rows now expose throughput/capacity nodes linked to existing
  factory logistic-unit and machine concepts.

## Validation

Command:

```bat
python tools\endfield_source_graph.py build --db tmp\factory_operation_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Result:

```text
Source graph: 1627886 nodes, 3055978 edges, 2234404 aliases
```

Target node counts:

```text
factory_hub_item_showing 2
factory_domain_item_transmission 2
factory_domain_transmission_level 31
factory_machine_craft_mode 2
factory_renderer_template_level 4
factory_fluid_consume_item 3
factory_underground_pipe 4
factory_logistic_unit 20
factory_fluid_machine 17
factory_renderer_template 116
```

Notable edge counts:

```text
factory_hub_shows_item 238
factory_domain_transmission_has_level 31
factory_fluid_consume_allowed_building 3
factory_underground_pipe_logistic_unit 4
factory_underground_pipe_machine_ref 4
factory_renderer_template_has_level 4
```

## Next Candidate

Remaining high-value small clusters include activity-limited formula economy
and activity rank/event metadata:

- `ActivityLimitedFormulaTable.json`
- `ActivityLimitedFormulaSettlementTable.json`
- `ActivityRankInfoTable.json`
- `ActivityShopAdditionalTable.json`
- `ActivitySubmitTextTable.json`
