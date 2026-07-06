# Direct Line Reference Reverse Source-Graph Recovery - 2026-07-06

## Scope

This pass added reverse lookup edges for two direct line joins that do not use
the shared `add_line_target_edge()` helper:

- Responsive dialog response ids that match generated WebUI `line` nodes.
- AI bark text ids that match generated WebUI `line` nodes.

The edges mirror exact id joins to existing generated line nodes. They do not
infer bark trigger timing, response selection rules, speaker state, or story
ordering.

## Added Edges

- `line_used_by_responsive_response`
- `line_has_bark_text`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graph:
`tmp/direct_line_reverse_validate.sqlite`

The validation seeded `ingest_webui_story()` before
`ingest_npc_voice_bark_semantics()` so generated `line` nodes existed before
the bark/responsive table joins ran.

| Forward edge | Forward count | Reverse edge | Reverse count | Missing reverse |
| --- | ---: | --- | ---: | ---: |
| `responsive_response_line_node` | 868 | `line_used_by_responsive_response` | 868 | 0 |
| `bark_text_line_node` | 928 | `line_has_bark_text` | 928 | 0 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `line` | 39,203 |
| `responsive_response` | 4,325 |
| `bark_text` | 928 |
