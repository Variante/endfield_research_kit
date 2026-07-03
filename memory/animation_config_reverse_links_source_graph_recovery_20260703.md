# Animation Config Reverse Links Source Graph Recovery - 2026-07-03

## Scope

The source graph now adds target-side reverse links for decoded
`AnimationConfig` references. Animation configs already exposed state names,
facial morph paths, montage paths, actor animation refs, cutscene refs, and one
generic path ref. Only montage targets had reverse edges before this pass.

This improves target-first animation questions such as "which character config
uses this actor animation ref?" or "which configs reference this cutscene-like
animation token?" without changing the underlying bounded AnimationConfig
decoder.

## Graph Additions

New reverse edges:

- `animation_state_used_by_animation_config`
- `facial_morph_used_by_animation_config`
- `actor_animation_ref_used_by_animation_config`
- `animation_cutscene_ref_used_by_animation_config`
- `animation_path_ref_used_by_animation_config`

Existing `level_script_montage_used_by_animation_config` remains the montage
reverse edge.

## Validation

Static check:

```bat
python -B -m py_compile tools\endfield_source_graph.py
```

Focused temp graph using only `ingest_decoded_config_semantics()`:

- `animation_config_references_state`: 1,886
- `animation_state_used_by_animation_config`: 1,886
- `animation_config_references_facial_morph`: 339
- `facial_morph_used_by_animation_config`: 339
- `animation_config_references_actor_animation`: 364
- `actor_animation_ref_used_by_animation_config`: 364
- `animation_config_references_cutscene`: 14
- `animation_cutscene_ref_used_by_animation_config`: 14
- `animation_config_references_path`: 1
- `animation_path_ref_used_by_animation_config`: 1
- `animation_config_references_montage`: 34
- `level_script_montage_used_by_animation_config`: 34

Query checks:

- `A_actor_aglina_battle_walk_stop_l --kind actor_animation_ref` resolves back
  to `anim_cfg_chr_0013_aglina` through
  `actor_animation_ref_used_by_animation_config`.
- `cutscene_e1m1_2 --kind animation_cutscene_ref` resolves to the character
  animation configs that reference the cutscene-like token.
- `FacialMorph --kind facial_morph` still shows existing atmospheric NPC
  references, and specific morph paths now also have reverse animation-config
  evidence when they are present in decoded AnimationConfig rows.

## Interpretation

This is an explainability improvement for character and animation recovery. It
does not decode nested montage or curve bodies, and it does not assign runtime
meaning to state names. It makes the recovered AnimationConfig reference
surface navigable from the referenced animation assets and tokens.
