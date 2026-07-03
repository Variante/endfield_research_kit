# Factory Tech Action Reverse Source-Graph Recovery - 2026-07-03

## Scope

Factory tech actions in `FacSTTNodeTable` already emitted forward references
from a `factory_tech` node to string parameters interpreted as items, gameplay
domains, or factory machines. This pass added the reverse lookup edges so a
referenced gameplay object can answer which factory tech action uses it.

## Graph Semantics

- `item_used_by_factory_tech_action`
- `domain_used_by_factory_tech_action`
- `factory_machine_used_by_factory_tech_action`

These mirror the existing forward action edges:

- `factory_tech_action_references_item`
- `factory_tech_action_references_domain`
- `factory_tech_action_references_machine`

Evidence remains the source parameter slot, for example
`action.parameters[0].valueStringList[0]`.

## Validation

Focused temp graph:
`tmp/factory_tech_action_reverse_validate.sqlite`

Counts from `ingest_factory_tech_semantics()`:

| Edge kind | Count |
| --- | ---: |
| `factory_tech_action_references_item` | 52 |
| `item_used_by_factory_tech_action` | 52 |
| `factory_tech_action_references_domain` | 3 |
| `domain_used_by_factory_tech_action` | 3 |
| `factory_tech_action_references_machine` | 20 |
| `factory_machine_used_by_factory_tech_action` | 20 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query FacBridge --kind factory_machine --db tmp\factory_tech_action_reverse_validate.sqlite --limit 8`
  showed `factory_machine:FacBridge` linked back to
  `factory_tech:tech_tundra_2_connector_1`.
- `python tools\endfield_source_graph.py query domain_2 --kind gameplay_domain --db tmp\factory_tech_action_reverse_validate.sqlite --limit 8`
  showed `domain_2` linked back to the three xiranite oven amount techs.
- `python tools\endfield_source_graph.py query item_bp_battle_cannon_1 --kind item --db tmp\factory_tech_action_reverse_validate.sqlite --limit 8`
  showed the blueprint item linked back to
  `factory_tech:tech_tundra_2_battle_cannon_1`.

`python -m py_compile tools\endfield_source_graph.py` passed.
