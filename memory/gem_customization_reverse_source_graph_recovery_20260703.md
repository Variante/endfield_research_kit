# Gem Customization Reverse Source-Graph Recovery - 2026-07-03

## Scope

`GemCustomizationBox` defines customization box items, their result gem item,
and locked gem term types. The graph already had forward edges from each
`gem_customization_box` to those targets. This pass adds reverse lookup edges so
item and term-type queries can find the customization box rows that use them.

## Added Edges

- `item_has_gem_customization_box_config`
- `item_is_gem_customization_result`
- `gem_customization_term_type_locked_by_box`

## Validation

Focused temp graph:
`tmp/gem_customization_reverse_validate.sqlite`

The validation seeded `ingest_factory_interaction_lookup_semantics()` only.

| Edge | Count |
| --- | ---: |
| `gem_customization_box_item` | 12 |
| `item_has_gem_customization_box_config` | 12 |
| `gem_customization_result_gem` | 12 |
| `item_is_gem_customization_result` | 12 |
| `gem_customization_locks_term_type` | 27 |
| `gem_customization_term_type_locked_by_box` | 27 |

Node counts in the focused graph:

| Node kind | Count |
| --- | ---: |
| `gem_customization_box` | 12 |
| `gem_customization_term_type` | 3 |
| `item` | 45 |

`python -m py_compile tools\endfield_source_graph.py` passed.
