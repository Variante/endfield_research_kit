# Lua Virtual Table Source Graph Recovery - 2026-07-03

## Context

The Lua consumer-reference audit found 494 matched exported table names and 8
unmatched `Tables.*` or `CS.Beyond.Cfg.Tables.*` references. Several unmatched
names are not exported table filenames, but they do have source-backed meanings:
runtime dictionary aliases or current-language table aliases. Without a graph
bridge they stayed as opaque `lua_table_reference` nodes.

## Change

`tools/endfield_source_graph.py` now adds `lua_virtual_table` nodes for the
unmatched Lua references that have conservative source-backed targets:

- `formulaIdToStr` -> `NumIdStrTable:formula_id`
- `formulaIdToNum` -> `StrIdNumTable:formula_id`
- `i18nTextTable` -> `I18nTextTable_CN`
- `factoryProcessorCraftTable` -> `FactoryHubCraftTable`

The first two are exact `CS.Beyond.Cfg.Tables` id-dictionary uses. The i18n
mapping is tagged `current_language` because `LuaCfg` uses the active runtime
language table, and CN is the current WebUI default language. The factory
processor mapping is tagged `field_match`: the Lua consumer reads
`usableLevel`, and `FactoryHubCraftTable` is the exported factory craft table
with that field.

The still-unresolved Lua table names remain diagnostic `lua_table_reference`
nodes:

- `blocShopItemTable`
- `equipTierLevelTable`
- `settlementOrderDataTable`
- `skillLockTable`

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\lua_virtual_table_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,594 nodes and 3,821,237 edges.
Validated counts:

- `lua_module_references_unmatched_table`: 9
- `lua_unmatched_table_has_virtual_resolution`: 4
- `lua_module_references_virtual_table`: 5
- `lua_virtual_table_resolves_to_id_dictionary`: 2
- `lua_virtual_table_resolves_to_table`: 2
- `lua_virtual_table` nodes: 4

Validated targets:

- `lua_virtual_table:factoryProcessorCraftTable` -> `table:FactoryHubCraftTable`
- `lua_virtual_table:formulaIdToNum` -> `id_dictionary:StrIdNumTable:formula_id`
- `lua_virtual_table:formulaIdToStr` -> `id_dictionary:NumIdStrTable:formula_id`
- `lua_virtual_table:i18nTextTable` -> `table:I18nTextTable_CN`

The five module-level virtual references are from
`FacTechTreePopUpCtrl.lua`, `FacSaveBlueprintCtrl.lua`, `FactoryUtils.lua`,
`BlueprintCell.lua`, and `LuaCfg.lua`.
