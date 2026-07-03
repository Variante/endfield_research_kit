# Domain Depot Location Reverse Source-Graph Recovery - 2026-07-03

## Scope

Domain depot rows, buyer rows, and delivery target rows already linked outward
to their authored domain and level ids. This pass adds the reverse edges so
queries starting from a domain or level can discover depot locations, buyers,
and delivery targets anchored there.

## Added Reverse Edges

- `domain_has_domain_depot`
- `domain_has_domain_depot_buyer`
- `domain_has_domain_depot_target`
- `level_has_domain_depot`
- `level_has_domain_depot_buyer`
- `level_has_domain_depot_target`

## Validation

Focused temp graph:
`tmp/domain_depot_location_reverse_validate.sqlite`

The validation seeded `ingest_domain_depot_semantics()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `domain_depot_in_domain` | 5 | `domain_has_domain_depot` | 5 |
| `domain_depot_buyer_in_domain` | 55 | `domain_has_domain_depot_buyer` | 55 |
| `domain_depot_target_in_domain` | 22 | `domain_has_domain_depot_target` | 22 |
| `domain_depot_in_level` | 5 | `level_has_domain_depot` | 5 |
| `domain_depot_buyer_in_level` | 55 | `level_has_domain_depot_buyer` | 55 |
| `domain_depot_target_in_level` | 22 | `level_has_domain_depot_target` | 22 |

`python -m py_compile tools\endfield_source_graph.py` passed.
