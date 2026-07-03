# Texture2D Raw-Hash Collision Source Graph Recovery - 2026-07-03

## Scope

Added `reports/texture2d_raw_hash_collision_audit.json` to the optional
asset-map phase of `tools/endfield_source_graph.py`.

The report describes the remaining Texture2D output-reuse family: multiple
Unity source identities can carry different raw serialized `Hash` values while
decoding to the same exported PNG identity (`Name + PathID`). This is not a
missing-output or decode-failure condition; the audit records zero missing
outputs and zero export errors.

## Graph Additions

New node kinds:

- `texture2d_raw_hash_collision_audit`
- `texture2d_collision_source`
- `texture2d_raw_hash_collision_group`
- `texture2d_raw_map_hash`
- `texture2d_collision_sample`
- `asset_container_prefix`

Important edges:

- `has_texture2d_collision_source`
- `has_texture2d_raw_hash_collision_group`
- `texture2d_collision_decodes_to_asset`
- `asset_has_texture2d_raw_hash_collision_evidence`
- `texture2d_collision_uses_pathid`
- `texture2d_collision_resolves_unity_asset`
- `unity_asset_has_texture2d_collision_evidence`
- `texture2d_collision_has_raw_map_hash`
- `texture2d_collision_container_prefix`
- `texture2d_collision_sample_entry`
- `texture2d_collision_sample_container`
- `container_uses_texture2d_collision_output`
- `texture2d_collision_sample_raw_map_hash`

The ingest is intentionally attached after `ingest_asset_maps()` and the
material/FMV pathid link steps. That lets collision groups connect to existing
`asset`, `unity_pathid`, `unity_asset`, and `asset_container` nodes when the
full asset-map graph is being built.

## Validation

Focused temp build:

```bat
python - <<focused SourceGraphBuilder validation script>>
```

The validation database was built at
`tmp/source_graph_texture2d_collision_validation.sqlite` and then removed.

Observed counts:

| kind | count |
| --- | ---: |
| `texture2d_raw_hash_collision_audit` | 1 |
| `texture2d_collision_source` | 2 |
| `texture2d_raw_hash_collision_group` | 9 |
| `texture2d_raw_map_hash` | 362 |
| `texture2d_collision_sample` | 61 |
| `asset_container_prefix` | 13 |

Observed edge counts:

| edge | count |
| --- | ---: |
| `has_texture2d_collision_source` | 2 |
| `has_texture2d_raw_hash_collision_group` | 9 |
| `texture2d_collision_decodes_to_asset` | 9 |
| `asset_has_texture2d_raw_hash_collision_evidence` | 9 |
| `texture2d_collision_resolves_unity_asset` | 9 |
| `texture2d_collision_has_raw_map_hash` | 362 |
| `texture2d_collision_sample_entry` | 61 |

Query checks:

```bat
python tools\endfield_source_graph.py query Background_p59E0F9C8D2F90F4C --db tmp\source_graph_texture2d_collision_validation.sqlite --kind texture2d_raw_hash_collision_group --limit 8
python tools\endfield_source_graph.py used-by Persistent/convert_by_type/Texture2D/Background_p59E0F9C8D2F90F4C.png --db tmp\source_graph_texture2d_collision_validation.sqlite --limit 8
```

The first query resolved both Persistent and StreamingAssets collision-group
nodes for `Background_p59E0F9C8D2F90F4C.png` and surfaced sampled prefab
containers. The second query seeded the exported PNG `asset` node and returned
the corresponding `texture2d_raw_hash_collision_group` under `usedBy`.

## Current Interpretation

The graph can now answer why duplicated Texture2D PNG outputs are expected:
the source rows differ by raw serialized-object hash and container identity, but
the collision audit ties those rows to a single exported decoded PNG, with
PathID/Unity-asset evidence and sampled source containers.

