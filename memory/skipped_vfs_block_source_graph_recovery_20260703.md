# Skipped VFS Block Source Graph Recovery - 2026-07-03

## Summary

Added source-graph ingest for the skipped VFS block audit reports:

- `reports/mission_order/skipped_vfs_block_audit.json`
- `reports/mission_order/skipped_vfs_block_audit_persistent.json`

The ingest adds graph nodes for the StreamingAssets and Persistent audit roots,
their skipped block families, top directories, largest-file examples, signal
categories, and signal sample files. This makes the graph answer questions such
as which skipped VFS blocks still contain Lua, ExtendData, DynamicStreaming, IV,
or manifest data that may be worth recovering.

These reports describe blocks skipped by the lean WebUI export path, not blocks
that failed to recover. Both audits report zero missing blocks and zero missing
chunks.

Coverage from the source reports:

| Root | Blocks | Chunks | Files | Bytes | Missing blocks | Missing chunks |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| StreamingAssets | 9 | 83 | 39,738 | 3,145,356,881 | 0 | 0 |
| Persistent | 8 | 146 | 40,004 | 11,828,335,706 | 0 | 0 |

## Node And Edge Shapes

New node kinds:

- `vfs_skipped_block_audit`
- `vfs_skipped_block`
- `vfs_block_directory`
- `vfs_block_signal`

New edge kinds:

- `has_vfs_skipped_block_audit`
- `vfs_audit_has_skipped_block`
- `vfs_skipped_block_top_directory`
- `vfs_skipped_block_largest_file`
- `vfs_skipped_block_has_signal`
- `vfs_signal_sample_file`

The builder now runs this ingest immediately after WebUI asset ingest, before
story/video/table semantics, because the skipped-block audit is standalone
export evidence and does not depend on later graph slices.

## Validation

Static checks:

```bat
python -m py_compile tools\endfield_source_graph.py
git diff --check -- tools\endfield_source_graph.py
```

Focused temporary graph ingest:

```bat
@'
import sqlite3
from pathlib import Path
from tools.endfield_source_graph import SourceGraphBuilder, ROOT
path = Path('tmp/skipped_vfs_block_graph_validation_20260703.sqlite')
builder = SourceGraphBuilder(db_path=path, root=ROOT, export_root=ROOT / 'export_full')
builder.open()
builder.ingest_skipped_vfs_block_audits()
builder.commit_step('skippedVfsBlocks')
builder.close()
conn = sqlite3.connect(path)
...
'@ | python -
```

Focused ingest counts:

| Item | Count |
| --- | ---: |
| `vfs_skipped_block_audit` nodes | 2 |
| `vfs_skipped_block` nodes | 17 |
| `vfs_block_directory` nodes | 60 |
| `vfs_block_signal` nodes | 10 |
| `file` nodes | 181 |
| `dataset` nodes | 1 |
| `has_vfs_skipped_block_audit` edges | 2 |
| `vfs_audit_has_skipped_block` edges | 17 |
| `vfs_skipped_block_top_directory` edges | 60 |
| `vfs_skipped_block_largest_file` edges | 79 |
| `vfs_skipped_block_has_signal` edges | 31 |
| `vfs_signal_sample_file` edges | 258 |
| missing chunk sum across `vfs_skipped_block` nodes | 0 |
| `skipped_vfs_block_audit` file rows | 2 |

Block counts by root were `Persistent=8` and `StreamingAssets=9`.

The focused DB also confirmed skipped-block file examples such as
`Data/Bundles/Windows/manifest.hgmmap` are indexed as file nodes.

## Notes

The audit JSON stores `topDirectories` as `{value, count}` list rows and file
examples as `name`/`length` rows. The ingest accepts those shapes as well as
older dict-style `topDirectories` and `path`/`bytes` file rows.

This should not be interpreted as WebUI display data. It is queryable evidence
for the original game-data understanding caveat: substantial non-WebUI VFS
families exist and are intentionally skipped by the lean export workflow even
when their chunk coverage is complete.
