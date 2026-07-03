# Factory Tech Hierarchy Reverse Source-Graph Recovery - 2026-07-03

## Scope

Factory tech groups, categories, layers, and tech nodes already had forward
hierarchy edges from the authored `FacSTT*` tables. This pass added reverse
structural edges so lookups from a domain, category, layer, or tech can recover
its authored factory-tech context without scanning only incoming edge names.

## Added Reverse Edges

- `domain_has_factory_tech_group`
- `factory_tech_category_in_group`
- `factory_tech_layer_in_group`
- `factory_tech_in_group`
- `factory_tech_in_category`
- `factory_tech_in_layer`
- `factory_tech_layer_required_by_layer`

## Validation

Focused temp graph:
`tmp/factory_tech_hierarchy_reverse_validate.sqlite`

Counts from `ingest_factory_tech_semantics()`:

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `factory_tech_group_domain` | 2 | `domain_has_factory_tech_group` | 2 |
| `factory_tech_group_has_category` | 22 | `factory_tech_category_in_group` | 22 |
| `factory_tech_group_has_layer` | 12 | `factory_tech_layer_in_group` | 12 |
| `factory_tech_group_has_tech` | 142 | `factory_tech_in_group` | 142 |
| `factory_tech_category_has_tech` | 142 | `factory_tech_in_category` | 142 |
| `factory_tech_layer_has_tech` | 142 | `factory_tech_in_layer` | 142 |
| `factory_tech_layer_requires_layer` | 4 | `factory_tech_layer_required_by_layer` | 4 |

CLI smoke checks:

- `python tools\endfield_source_graph.py query tech_tundra_2_connector_1 --kind factory_tech --db tmp\factory_tech_hierarchy_reverse_validate.sqlite --limit 10`
  showed the tech linked back to `tech_group_tundra` and
  `fac_team_tundra_logistics`.
- `python tools\endfield_source_graph.py query domain_2 --kind gameplay_domain --db tmp\factory_tech_hierarchy_reverse_validate.sqlite --limit 8`
  showed `domain_2` linked back to `tech_group_jinlong`.
- `python tools\endfield_source_graph.py query tech_group_jinlong_liquid --kind factory_tech_layer --db tmp\factory_tech_hierarchy_reverse_validate.sqlite --limit 12`
  showed layer membership back to `tech_group_jinlong` plus tech-to-layer
  reverse edges.

`python -m py_compile tools\endfield_source_graph.py` passed.
