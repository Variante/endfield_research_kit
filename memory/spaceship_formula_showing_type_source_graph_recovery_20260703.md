# Spaceship Formula Showing-Type Source-Graph Recovery - 2026-07-03

## Scope

Grow-cabin formula rows and seed-formula rows store a `type` value that matches
`SpaceshipGrowCabinFormulaShowingTypeTable`, but the source graph previously
kept this value only in formula node data. This pass promotes that relationship
into graph edges.

## Added Edges

- `spaceship_formula_has_showing_type`
- `spaceship_formula_showing_type_has_formula`

## Validation

Focused temp graph:
`tmp/spaceship_formula_type_validate.sqlite`

The validation seeded item economy and spaceship semantics.

| Edge | Count |
| --- | ---: |
| `spaceship_formula_has_showing_type` | 30 |
| `spaceship_formula_showing_type_has_formula` | 30 |
| `defines_spaceship_formula_showing_type` | 4 |

Formula edge split:

| Source table | Count |
| --- | ---: |
| `SpaceshipGrowCabinFormulaTable` | 15 |
| `SpaceshipGrowCabinSeedFormulaTable` | 15 |

Used showing-type nodes are `1`, `2`, and `3`; lookup type `0` remains the
catchall display row and is not referenced by formula rows.

`python -m py_compile tools\endfield_source_graph.py` passed.
