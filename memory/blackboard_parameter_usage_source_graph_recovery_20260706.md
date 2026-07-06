# Blackboard Parameter Usage Source Graph Recovery - 2026-07-06

## Summary

Added a focused `blackboard-usage` query shortcut to
`tools/endfield_source_graph.py` for reviewing gameplay blackboard keys,
decoded buff parameters, and decoded skill parameters through the source graph.
`gameplay-usage` is accepted as an alias for the same command.

This is a diagnostic source-graph improvement only. It does not change WebUI
output, game-data decoding, table exports, or gameplay formula recovery.

## Current Evidence

The current source graph has:

- 547 `gameplay_blackboard_key` nodes.
- 1,254 `buff_parameter` nodes.
- 3,323 `skill_parameter` nodes.
- 2,378 `buff` nodes.
- 2,155 `gameplay_skill` nodes.
- 4,807 `gameplay_skill_level` nodes.

Important existing edges include:

- `blackboard_key_used_by_gameplay`: 15,842
- `skill_level_uses_blackboard_key`: 14,838
- `skill_data_has_param_string`: 49,988
- `buff_data_has_param_string`: 13,373
- `level_data_has_param_string`: 13,370
- `skill_parameter_matches_blackboard_key`: 359
- `blackboard_key_matches_skill_parameter`: 359
- `buff_parameter_matches_blackboard_key`: 218
- `blackboard_key_matches_buff_parameter`: 218

The exact-name bridge edges are created by
`link_decoded_parameter_blackboard_keys()` and connect decoded parameter names
from binary config strings to blackboard keys used by authored gameplay tables.

## New Query Surface

Use:

```bat
python tools\endfield_source_graph.py blackboard-usage atk_scale --limit 5
python tools\endfield_source_graph.py blackboard-usage duration --limit 5
python tools\endfield_source_graph.py blackboard-usage tar --kind skill_parameter --limit 5
python tools\endfield_source_graph.py blackboard-usage atk_scale --kind buff_parameter --limit 5
python tools\endfield_source_graph.py gameplay-usage attack --limit 5
```

The command resolves the term as a `gameplay_blackboard_key`,
`buff_parameter`, or `skill_parameter`, then emits:

- the resolved seed node and aliases;
- adjacent parameter/blackboard edge counts;
- direct adjacent relations such as skill-level blackboard use, potential
  talent modifiers, spawner buff blackboard use, and decoded config parameter
  strings;
- exact-name bridges between blackboard keys and decoded buff/skill parameter
  nodes;
- usage relations reachable through those bridged parameter or blackboard
  nodes.

## Validation

Validated with:

```bat
python -m py_compile tools\endfield_source_graph.py
python tools\endfield_source_graph.py blackboard-usage atk_scale --limit 5
python tools\endfield_source_graph.py blackboard-usage duration --limit 5
python tools\endfield_source_graph.py blackboard-usage tar --kind skill_parameter --limit 5
```

Observed `atk_scale` resolving to `gameplay_blackboard_key:atk_scale` with
3,300 `blackboard_key_used_by_gameplay` edges, bridge edges to both
`buff_parameter:atk_scale` and `skill_parameter:atk_scale`, and bridged decoded
buff users such as `buff_cc_enemy_death_ground_area`.

Observed `duration` resolving to `gameplay_blackboard_key:duration` with
potential talent, spawner, use-effect, buff-parameter, and skill-parameter
evidence. Observed `tar` as a forced `skill_parameter` lookup with 7,083
decoded `skill_data_has_param_string` users.
