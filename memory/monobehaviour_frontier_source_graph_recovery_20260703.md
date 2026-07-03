# MonoBehaviour Frontier Source Graph Recovery - 2026-07-03

## Scope

Added a maintained compact report path for the current MonoBehaviour decoded
frontier and made that report queryable in `tools/endfield_source_graph.py`.

The report builder reads a `scripts/build_decoded_index.py` index and writes:

```text
reports/monobehaviour_frontier_latest.json
reports/monobehaviour_frontier_latest.md
```

The report files are generated artifacts under ignored `reports/`; the durable
maintained pieces are the script, source-graph ingest, and this note.

## Current Frontier Input

Generated from the post-diagnostics index:

```bat
python scripts\build_monobehaviour_frontier_report.py --index tmp\decoded_index_mono_after_diagnostics_20260703\index.json
```

Current generated summary:

- source index: `tmp/decoded_index_mono_after_diagnostics_20260703/index.json`
- total files: `1,064,294`
- total groups: `1,478`
- decoded files: `1,063,560`
- residual files: `734`
- residual groups: `21`
- unparsed files: `0`

Top residual schemas:

| Schema | Residual files |
| --- | ---: |
| `ProjectileTemplateData` | 310 |
| `AbilityEntityTemplateData` | 162 |
| `EnemyTemplateData` | 156 |
| `LineFollower` | 48 |
| `CharacterTemplateData` | 30 |

Top residual domains:

| Domain | Residual files |
| --- | ---: |
| `camera/cinematic` | 479 |
| `gameplay/ability` | 186 |
| `managed-reference` | 61 |
| `gameplay/weapon` | 5 |
| `story/dialog` | 3 |
| `gameplay/character` | 1 |

## Graph Additions

New node kinds:

- `monobehaviour_frontier_report`
- `monobehaviour_frontier_group`
- `monobehaviour_decode_status`
- `monobehaviour_domain`
- `monobehaviour_schema`
- `monobehaviour_schema_group`
- `monobehaviour_schema_kind`
- `monobehaviour_field_set`
- `monobehaviour_registry_status`
- `monobehaviour_managed_class`
- `monobehaviour_layout`

Important edges:

- `has_monobehaviour_frontier_group`
- `monobehaviour_frontier_status_count`
- `monobehaviour_frontier_group_status`
- `monobehaviour_frontier_domain`
- `monobehaviour_frontier_schema`
- `monobehaviour_frontier_schema_group`
- `monobehaviour_frontier_schema_kind`
- `monobehaviour_frontier_field_set`
- `monobehaviour_frontier_registry_status`
- `monobehaviour_frontier_managed_class`
- `monobehaviour_frontier_layout`

## Validation

Focused temp source-graph validation created
`tmp/source_graph_monobehaviour_frontier_validation.sqlite`, called only
`ingest_monobehaviour_frontier_report()`, then removed the temp database.

Observed node counts:

| kind | count |
| --- | ---: |
| `monobehaviour_frontier_report` | 1 |
| `monobehaviour_frontier_group` | 21 |
| `monobehaviour_decode_status` | 2 |
| `monobehaviour_schema` | 17 |
| `monobehaviour_domain` | 6 |
| `monobehaviour_registry_status` | 3 |
| `monobehaviour_managed_class` | 63 |
| `monobehaviour_layout` | 53 |

Observed edge counts:

| edge | count |
| --- | ---: |
| `has_monobehaviour_frontier_group` | 21 |
| `monobehaviour_frontier_group_status` | 24 |
| `monobehaviour_frontier_schema` | 21 |
| `monobehaviour_frontier_domain` | 21 |
| `monobehaviour_frontier_registry_status` | 25 |
| `monobehaviour_frontier_managed_class` | 119 |
| `monobehaviour_frontier_layout` | 134 |

Query checks:

```bat
python tools\endfield_source_graph.py query ProjectileTemplateData --db tmp\source_graph_monobehaviour_frontier_validation.sqlite --kind monobehaviour_schema --limit 10
python tools\endfield_source_graph.py query monobehaviour_frontier_latest --db tmp\source_graph_monobehaviour_frontier_validation.sqlite --kind monobehaviour_frontier_report --limit 8
```

`ProjectileTemplateData` resolved to a `monobehaviour_schema` node with two
frontier-group edges. The report query resolved to the report node and listed
current residual groups.

## Current Interpretation

The current post-diagnostics MonoBehaviour surface has no unparsed files. The
remaining recovery work is now concentrated in 21 partial semantic groups, led
by projectile templates, ability entity templates, enemy templates, line
followers, and character templates. This makes the runtime-payload frontier
small enough to query and rank from the source graph instead of relying on
manual scans of million-file decoded indexes.
