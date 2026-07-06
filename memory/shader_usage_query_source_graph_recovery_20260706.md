# Shader Usage Source Graph Query Recovery - 2026-07-06

## Context

The original-data understanding report still lists shader recovery as partial:
shader payloads and snippets are extracted, but HLSL decompilation, resource
binding normalization, material assignment, and renderer fidelity remain open
work. The graph already contains useful shader evidence, but generic `query`
only shows the first few neighbors of a shader program.

## Change

`tools/endfield_source_graph.py` now supports:

```bat
python tools\endfield_source_graph.py shader-usage TERM
```

The command resolves these seed kinds before falling back to generic lookup:

- `shader_program`
- `shader`
- `shader_family`
- `shader_bytecode_backend`
- `shader_snippet`
- `unity_pathid`
- `material`

For a shader program it returns:

- shader export membership
- shader family
- bytecode backends such as `DXBC` and `SMOL-V`
- snippet nodes
- shader PathID
- materials that reference the shader PathID
- asset entities using those material JSON assets, when material asset links
  are present

## Validation Examples

Named shader lookup:

```bat
python tools\endfield_source_graph.py shader-usage HGRP/CharacterNPR_Skin --limit 8
```

Expected evidence includes `shader_program_family`, two
`shader_program_has_backend` rows, snippet rows, and `shader_program_pathid`.

PathID lookup:

```bat
python tools\endfield_source_graph.py shader-usage 4484747192473637154 --limit 8
```

Expected evidence resolves to the `HGRP/CharacterNPR_Skin` shader program and
shows material references through `uses_shader_pathid`. For this shader, the
query also surfaces actor asset entities such as `actor_aglina_body_01` through
the material JSON asset bridge.

Material-driven lookup:

```bat
python tools\endfield_source_graph.py shader-usage M_actor_endminf_body_01 --kind material --limit 8
```

Expected evidence includes `uses_shader_pathid` to
`pathid:4484747192473637154`, matching the material-chain evidence surfaced by
`entity-assets StreamingAssets/actor_endminf_body_01`.

## Boundary

This command summarizes extracted shader payload and material-reference
evidence. It does not decompile DXBC to HLSL, normalize all resource bindings,
prove original material assignment in Unity, or validate runtime renderer
fidelity.
