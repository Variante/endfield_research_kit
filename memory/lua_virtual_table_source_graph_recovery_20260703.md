# Lua Virtual Table Source Graph Recovery - 2026-07-03

## Context

The Lua consumer audit intentionally left several `Tables.*` names unmatched
when they are runtime virtual dictionaries or aliases rather than direct
exported JSON table filenames. Four of those names are now useful enough to
resolve explicitly in the source graph.

## Change

`tools/endfield_source_graph.py` now creates `lua_virtual_table` nodes for:

- `formulaIdToStr`
- `formulaIdToNum`
- `i18nTextTable`
- `factoryProcessorCraftTable`

The graph links unmatched Lua table references and Lua modules to the virtual
node, then links the virtual node to the best recovered target:

- `formulaIdToStr` -> `id_dictionary:NumIdStrTable:formula_id`
- `formulaIdToNum` -> `id_dictionary:StrIdNumTable:formula_id`
- `i18nTextTable` -> `table:I18nTextTable_CN`
- `factoryProcessorCraftTable` -> `table:FactoryHubCraftTable`

Each edge records a confidence label and reason.

## Validation

```bat
python -B -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py build --db tmp\lua_virtual_table_validation_20260703.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

Temporary graph result:

```text
Source graph: 1691594 nodes, 3821237 edges, 2289650 aliases
```

SQLite counts:

| Kind | Count |
|---|---:|
| `lua_virtual_table` nodes | 4 |
| `lua_unmatched_table_has_virtual_resolution` edges | 4 |
| `lua_module_references_virtual_table` edges | 5 |
| `lua_virtual_table_resolves_to_id_dictionary` edges | 2 |
| `lua_virtual_table_resolves_to_table` edges | 2 |
