# Attribute Modifier Kind Source Graph Recovery - 2026-07-03

## Scope

Attribute display and filter tables use numeric `attributeModifier` codes as
authored display/operator metadata. Before this pass, `AttributeShowConfigTable`
also exposed those codes through `gameplay_stat_property` nodes, which made it
easy to confuse modifier/operator codes with the stat properties being shown.

The source graph now adds explicit `attribute_modifier_kind` nodes and usage
edges for display/filter contexts. This is still table evidence only: it does
not prove runtime evaluator order, final stat values, or combat formula
execution.

## Source Tables

- `AttributeShowConfigTable.json`
- `CompositeAttributeShowConfigTable.json`
- `AttributeFilterTable.json`
- `CompositeAttributeTable.json`

`CompositeAttributeTable.json` still uses `gameplay_stat_property` members
because those row values are authored stat-property names such as
`PhysicalDamageTakenScalar`, not modifier/operator codes.

## Graph Change

New node kind:

- `attribute_modifier_kind`

New edge kinds:

- `attribute_display_entry_uses_modifier_kind`
- `composite_attribute_display_entry_uses_modifier_kind`
- `attribute_filter_entry_uses_modifier_kind`
- `attribute_modifier_kind_used_by_display_entry`
- `attribute_modifier_kind_used_by_filter_entry`

Each usage edge preserves display context in data:

- `attributeModifier`
- `valueFormat`
- `showPercent`
- `isReduce`
- `inverseFormat`
- source list index
- authored display index

The older `attribute_display_entry_uses_modifier_property` edges remain for
compatibility with existing queries, but new consumers should prefer
`attribute_modifier_kind` for display/operator semantics.

## Validation

Focused temporary graph build:

```bat
tmp\attribute_modifier_semantics_validation.sqlite
```

Focused ingest:

- `ingest_attribute_dictionary()`

Edge and node counts:

- `attribute_modifier_kind`: 5 nodes for codes `5`, `6`, `7`, `8`, and `9`
- `attribute_display_entry_uses_modifier_kind`: 86
- `composite_attribute_display_entry_uses_modifier_kind`: 20
- `attribute_filter_entry_uses_modifier_kind`: 21
- `attribute_modifier_kind_used_by_display_entry`: 106
- `attribute_modifier_kind_used_by_filter_entry`: 21
- `composite_attribute_includes`: 25, unchanged for stat-property members

Code `8` has inverse-format evidence:

- `attribute:47:1`, `valueFormat` `{1-value:0.0%}`, `showPercent: true`,
  `isReduce: true`;
- `composite:AllDamageTakenScalar:1`, `valueFormat` `{1-value:0.0%}`,
  `showPercent: true`, `isReduce: true`;
- `filter:equipExtraAttr:17`, filter placement for `AllDamageTakenScalar`.

CLI smoke queries:

```bat
python tools\endfield_source_graph.py query attribute_modifier_kind:8 --db tmp\attribute_modifier_semantics_validation.sqlite --limit 12
python tools\endfield_source_graph.py query AllDamageTakenScalar --kind composite_attribute --db tmp\attribute_modifier_semantics_validation.sqlite --limit 12
python tools\endfield_source_graph.py query equipExtraAttr --kind attribute_filter --db tmp\attribute_modifier_semantics_validation.sqlite --limit 12
```

The modifier-kind query exposes direct and reverse usage edges for code `8`.
The composite query still shows the six stat-property members for
`AllDamageTakenScalar`, plus its display and filter placement.
