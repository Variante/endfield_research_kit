# Domain Depot And Mission Type Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added direct reverse lookup edges for three already-recovered table
relationships:

- `MissionTypeInfoTable` mission type to mission view type.
- `DomainDepotConst` mission-id constants to mission refs.
- `DomainDepotDeliverTargetTable` delivery targets to target dialog configs.

These are table-field inverses only. They do not infer runtime mission flow or
dialog execution order.

## Added Edges

- `mission_view_type_has_mission_type`
- `mission_referenced_by_domain_depot_const`
- `domain_depot_deliver_target_dialog_for_target`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graphs:

- `tmp/domain_core_reverse_validate.sqlite`
- `tmp/domain_depot_const_dialog_reverse_validate.sqlite`

The validation seeded `ingest_domain_core_semantics()` and
`ingest_domain_depot_semantics()` separately.

| Edge | Count |
| --- | ---: |
| `mission_type_uses_view_type` | 11 |
| `mission_view_type_has_mission_type` | 11 |
| `domain_depot_const_mission` | 1 |
| `mission_referenced_by_domain_depot_const` | 1 |
| `domain_depot_target_dialog` | 22 |
| `domain_depot_deliver_target_dialog_for_target` | 22 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `mission_type_info` | 11 |
| `mission_view_type` | 5 |
| `domain_depot_const` | 8 |
| `mission` | 3 |
| `domain_depot_deliver_target` | 22 |
| `domain_depot_deliver_target_dialog` | 22 |
