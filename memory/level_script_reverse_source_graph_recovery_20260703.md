# Level Script Reverse Source Graph Recovery - 2026-07-03

## Context

Decoded level script and level script template refs already connected script
nodes to referenced story keys, missions, gameplay effects, buffs, templates,
and montages. Audio refs had reverse edges, but narrative and gameplay refs were
still forward-only, which made story-centered recovery queries miss the runtime
script/template data that mentioned a story or mission id.

## Change

`tools/endfield_source_graph.py` now emits reverse edges from referenced nodes
back to the level script or level script template owner:

- `story_used_by_level_script`
- `mission_used_by_level_script`
- `gameplay_effect_used_by_level_script`
- `buff_used_by_level_script`
- `level_script_template_used_by_level_script`
- `level_script_montage_used_by_level_script`
- `story_used_by_level_script_template`
- `mission_used_by_level_script_template`
- `gameplay_effect_used_by_level_script_template`
- `buff_used_by_level_script_template`
- `level_script_template_used_by_level_script_template`
- `level_script_montage_used_by_level_script_template`

The reverse edges preserve the same source, evidence, and extracted string-ref
payload as the existing forward edges.

## Validation

Syntax and diff checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Temporary graph:

```bat
python tools\endfield_source_graph.py build --db tmp\level_script_reverse_source_graph.sqlite --skip-asset-maps --skip-reference-rows --skip-followups
```

The graph built successfully with 1,691,485 nodes and 3,814,281 edges.
Forward/reverse counts matched:

- `level_script_references_story`: 4,416 / `story_used_by_level_script`: 4,416
- `level_script_references_mission`: 722 / `mission_used_by_level_script`: 722
- `level_script_references_effect`: 941 / `gameplay_effect_used_by_level_script`: 941
- `level_script_references_buff`: 873 / `buff_used_by_level_script`: 873
- `level_script_references_template`: 374 / `level_script_template_used_by_level_script`: 374
- `level_script_references_montage`: 228 / `level_script_montage_used_by_level_script`: 228
- `level_script_template_references_story`: 45 / `story_used_by_level_script_template`: 45
- `level_script_template_references_mission`: 0 / `mission_used_by_level_script_template`: 0
- `level_script_template_references_effect`: 16 / `gameplay_effect_used_by_level_script_template`: 16
- `level_script_template_references_buff`: 5 / `buff_used_by_level_script_template`: 5
- `level_script_template_references_template`: 0 / `level_script_template_used_by_level_script_template`: 0
- `level_script_template_references_montage`: 31 / `level_script_montage_used_by_level_script_template`: 31
