# Dialog Option And Domain Reward Reverse Source-Graph Recovery - 2026-07-03

## Scope

This pass added reverse lookup edges for two exact source-graph joins:

- `DialogOptionTable` rows that match generated WebUI `option` nodes by option
  id.
- Domain development level reward ids emitted through the shared reward helper.

Both relationships are direct inverses of existing source-graph edges. They do
not infer option routing, option display order, reward claiming rules, or domain
progression formulas.

## Added Edges

- `generated_option_has_dialog_option`
- `reward_used_by_domain_development_level`

## Validation

Commands:

```bat
python -m py_compile tools\endfield_source_graph.py
```

Focused temp graphs:

- `tmp/dialog_option_reverse_validate.sqlite`
- `tmp/domain_reward_reverse_validate.sqlite`

The dialog-option validation seeded `ingest_webui_story()` before
`ingest_dialog_support_semantics()` so generated `option` nodes existed before
the table-row join ran. The domain-reward validation seeded
`ingest_domain_core_semantics()`.

| Edge | Count |
| --- | ---: |
| `dialog_option_generated_option` | 4,208 |
| `generated_option_has_dialog_option` | 4,208 |
| `domain_development_level_reward` | 28 |
| `reward_used_by_domain_development_level` | 28 |

Focused node counts:

| Node kind | Count |
| --- | ---: |
| `dialog_option` | 4,343 |
| `option` | 4,365 |
| `domain_development_level` | 30 |
| `reward` | 28 |
