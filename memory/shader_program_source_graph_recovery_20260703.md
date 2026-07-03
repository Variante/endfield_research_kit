# Shader Program Source Graph Recovery - 2026-07-03

## Scope

Converted AnimeStudio shader exports are now source-graph evidence. The graph
scans exported `.shader` files under:

- `export_full/recovered/AnimeStudio-cli/StreamingAssets/convert_by_type/Shader/`
- `export_full/recovered/AnimeStudio-cli/Persistent/convert_by_type/Shader/`

This closes part of the original-game understanding gap where material shader
PathIDs could resolve to Unity shader assets, but the exported shader programs
and Endfield bytecode snippet inventory were not queryable.

## Evidence Shape

Shader export status manifests use:

- `schema_version`
- `generated_at_epoch`
- `summary`
- `output_path_collision_samples`
- `source_groups`

Current status summaries:

- StreamingAssets: 271 matched entries, 248 source groups, 220 actual output
  files, 0 missing outputs, 0 unmapped export errors.
- Persistent: 222 matched entries, 220 source groups, 218 actual output files,
  0 missing outputs, 0 unmapped export errors.

All current converted shader files follow:

```text
export_full/recovered/AnimeStudio-cli/<root>/convert_by_type/Shader/<shader name with / as _>_p<16 hex PathID>.shader
```

The hex suffix is the unsigned 64-bit representation of the Unity PathID. The
source graph reuses the existing `asset_pid_signed_path_id()` conversion so
`_pA59A1508935AED46` becomes `-6513870784461869754`, matching AssetMap
`PathID` values.

## Graph Additions

New node kinds:

- `shader_export`
- `shader_program`
- `shader_snippet`
- `shader_family`
- `shader_bytecode_backend`
- `shader_sidecar_format`

New edges:

- `shader_export_has_program`
- `shader_program_pathid`
- `shader_program_named_shader`
- `shader_program_family`
- `shader_program_has_backend`
- `shader_program_has_snippet`
- `shader_snippet_backend`
- `shader_program_has_sidecar_format`
- `shader_program_resolves_unity_asset`
- `unity_asset_exports_shader_program`
- `material_uses_shader_program`
- `shader_program_used_by_material`

The full-build resolver joins shader programs to same-root Unity shader assets
through existing `unity_pathid -> unity_asset` map edges. It then connects
materials to shader programs through existing `shader_used_by_material_slot`
edges.

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused shader-program temp graph:

- `shader_export`: 2
- `shader_program`: 438
- `shader_snippet`: 131,524
- `shader_family`: 9
- `shader_bytecode_backend`: 2
- `shader_sidecar_format`: 0
- `shader_export_has_program`: 438
- `shader_program_has_snippet`: 131,524
- `shader_program_has_backend`: 872
- `shader_program_pathid`: 438
- `shader_program_named_shader`: 438
- `shader_program_family`: 438

Backend declared snippet totals:

- DXBC: 63,398 snippets, 846,238,212 declared bytes.
- SMOL-V: 68,126 snippets, 559,392,583 declared bytes.

Resolver fixture:

- `shader_program_resolves_unity_asset`: 1
- `unity_asset_exports_shader_program`: 1
- `material_uses_shader_program`: 1
- `shader_program_used_by_material`: 1
- Cross-root bad joins: 0

Query checks:

- `HGRP/CharacterNPR_Eye` resolves to StreamingAssets and Persistent
  `shader_program` nodes, then to backend and snippet evidence.
- `SMOL-V --kind shader_bytecode_backend` shows shader programs with SMOL-V
  snippet markers.
- `StreamingAssets:-1706220712117210762 --kind shader_program` resolves to the
  exact `HGRP/CharacterNPR_Eye` program.

## Notes

Normal exports currently have no `.shader.bytecode` sidecar directories in the
two main roots, so sidecar format nodes are ready but count 0. The opt-in
sidecar exporter remains documented in
`memory/animestudio_shader_bytecode_sidecars_20260703.md`.

The attempted full-map validation loaded a multi-GB temporary SQLite database
and was abandoned in favor of a focused source-root resolver fixture. The full
build should still resolve all 438 converted shader programs once asset maps are
included; a read-only subagent confirmed all 220 StreamingAssets and 218
Persistent shader files map to same-root `Type=Shader` AssetMap entries.
