# Domain POI Unlock Source-Graph Recovery - 2026-07-03

## Scope

`DomainPoiTable.unlockSystemType` is populated on domain POI type rows, but the
source graph previously kept it only in `domain_poi_type` node payloads. This
pass promotes the field into the existing `gameplay_unlock` vocabulary.

## Added Edges

- `domain_poi_type_unlock_system`
- `gameplay_unlock_controls_domain_poi_type`

## Validation

Focused temp graph:
`tmp/domain_poi_unlock_validate.sqlite`

The validation seeded `ingest_domain_depot_semantics()` only.

| Edge | Count |
| --- | ---: |
| `domain_poi_type_unlock_system` | 8 |
| `gameplay_unlock_controls_domain_poi_type` | 8 |

Unlock distribution:

| Unlock | Count |
| --- | ---: |
| `10000000` | 5 |
| `501` | 1 |
| `503` | 1 |
| `512` | 1 |

`python -m py_compile tools\endfield_source_graph.py` passed.
