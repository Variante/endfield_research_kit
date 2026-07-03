# Settlement Economy Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added reverse lookup edges for authored settlement and economy table
relationships already emitted by the source graph:

- Shop manual refresh cost items.
- Settlement level upgrade mission refs.
- Settlement trade item refs.
- Settlement trade activity refs.

These are direct table-field inverses. They do not infer shop refresh behavior,
mission completion state, settlement production timing, or activity
availability.

## Added Edges

- `item_cost_for_manual_refresh`
- `mission_upgrades_settlement_level`
- `item_traded_by_settlement`
- `activity_uses_settlement_trade_item`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graphs:

- `tmp/economy_manual_refresh_reverse_validate.sqlite`
- `tmp/settlement_trade_reverse_validate.sqlite`

The validations seeded `ingest_economy_metadata_semantics()` and
`ingest_domain_core_semantics()` separately.

| Edge | Count |
| --- | ---: |
| `manual_refresh_costs_item` | 4 |
| `item_cost_for_manual_refresh` | 4 |
| `settlement_level_upgrade_mission` | 15 |
| `mission_upgrades_settlement_level` | 15 |
| `settlement_trade_item` | 135 |
| `item_traded_by_settlement` | 135 |
| `settlement_trade_item_activity` | 14 |
| `activity_uses_settlement_trade_item` | 14 |

Focused economy node counts:

| Node kind | Count |
| --- | ---: |
| `shop_manual_refresh_step` | 4 |
| `item` | 10 |

Focused domain-core node counts:

| Node kind | Count |
| --- | ---: |
| `settlement_level` | 19 |
| `settlement_trade_item` | 135 |
| `mission` | 15 |
| `item` | 28 |
| `activity` | 1 |
