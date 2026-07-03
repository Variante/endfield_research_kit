# Domain Depot Inferred Reverse Source-Graph Recovery - 2026-07-03

## Scope

Domain depot buyer and delivery-target rows are inferred to belong to depots by
matching their authored `level` with depot `refLevelId`. The source graph
already emitted owner-to-depot inferred edges. This pass adds the reverse edges
so queries starting from a depot can discover the inferred buyers and delivery
targets attached to that depot.

## Added Reverse Edges

- `domain_depot_has_buyer`
- `domain_depot_has_target`

Both reverse edges carry the same evidence and payload as the existing inferred
forward edge:

- evidence: `level/refLevelId`
- data: `{"inference":"shared level/refLevelId"}`

## Validation

Focused temp graph:
`tmp/domain_depot_inferred_reverse_validate.sqlite`

The validation seeded `ingest_domain_depot_semantics()` only.

| Forward edge | Count | Reverse edge | Count |
| --- | ---: | --- | ---: |
| `domain_depot_buyer_for_depot` | 55 | `domain_depot_has_buyer` | 55 |
| `domain_depot_target_for_depot` | 22 | `domain_depot_has_target` | 22 |

`python -m py_compile tools\endfield_source_graph.py` passed.
