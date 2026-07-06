# Animation Usage Source-Graph Query - 2026-07-06

## Scope

Added `python tools/endfield_source_graph.py animation-usage` as a focused
lookup for authored animation evidence in the local source graph. The command
resolves seeds across animation configs, level-script montages, model-view state
controllers, clip references, animation clips, facial morphs, lipsync clips,
timeline clips, damage-text animations, audio, and related asset/model nodes.

## Evidence Covered

The current graph contains broad static animation coverage:

- `lipsync_clip`: 64,920 nodes, linked to audio and language records.
- `level_script_montage`: 3,512 nodes, with NPC montage category/body/action
  decomposition and level-script, level-data, character-interact, and
  atmospheric NPC consumers.
- `animation_config`: 107 nodes, linked to states, facial morphs, actor
  animation refs, cutscene refs, path refs, and referenced montages.
- `model_view_state_controller`: 399 nodes, linked to model configs, asset
  entities, animator names, clip assets, and effect references.
- `animation_clip`: 807 nodes, plus timeline line/option clips, FMV clips,
  runtime jump clips, and damage-text animation refs.

Useful examples:

```bat
python tools\endfield_source_graph.py animation-usage anim_cfg_abilityEntity_chr_0017_yvonne_combo_skill --kind animation_config
python tools\endfield_source_graph.py animation-usage Montage/NPC/Generic/agmelee/die --kind level_script_montage
python tools\endfield_source_graph.py animation-usage dyn_P_anm_common_machine+1_001_m03_postmodel --kind model_view_state_controller
python tools\endfield_source_graph.py animation-usage A_anm_base01_zmddoor+1_001_03_close_01 --kind model_view_clip_ref
python tools\endfield_source_graph.py animation-usage Chinese:au_dlg_c13m1_10_002 --kind lipsync_clip
```

## Output Shape

The command returns:

- `seedNode` and `resolvedKind` for the matched graph seed.
- `focusNodeIds` for the seed plus directly linked animation-adjacent nodes.
- `edgeCounts` for animation/montage/model-view/clip/facial/lipsync relations
  around the focus set.
- `animationSummary`, grouped into animation configs, montages, facial morphs,
  model-view evidence, lipsync, timeline clips, damage text, assets/models,
  effects, audio, and other relations.
- `relations`, preserving edge source and evidence fields for inspection.

## Caveats

This is static authored-reference evidence. It does not reconstruct runtime
animator controller execution, blend trees, masks, IK, clip timing, active
controller state, or whether a referenced montage/clip actually plays in a
specific runtime branch. It is best used to answer "where is this animation-like
thing referenced?" before deeper Unity/AnimeStudio inspection.
