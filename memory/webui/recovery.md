# Recovery page recovery

## Purpose

Recovery (tab `Progress` / `进度`) shows how far the installed game data is
understood: a log-scaled VFS block-volume bar, then a tree of VFS blocks whose
leaves are the declared logical-file families with their L1–L4 stages. The four
levels are defined in [`../game_data/README.md`](../game_data/README.md).

Its reason to exist is evidence honesty. Open and unassessed levels are shown
with the same prominence as closed ones, and "framed and named" stays apart
from "understood": a stage is a scoped state, never a percentage.

## Inputs and recovery flow

The builder never re-decodes bytes and never reads the installed client.

1. `reports/animestudio/vfs_payload_profile_files_latest.jsonl.gz`: one row
   per declared logical file (block, path, chunk, declared size, bytes read,
   profiler status). Block and family tallies are measured from it.
2. `scripts/webui/recovery/recovery_declarations.json`: the reviewed block
   list (checked against the C# `EndfieldVfsBlockType` enum by a focused
   test), lane per block, family path patterns, bilingual per-level stage
   statements each citing its memory topic, the stage-state vocabulary, and
   the recorded evidence limits.
3. `memory/game_data/README.md`: the four level names and questions, parsed
   from its `## The four levels` table.
4. The export's asset maps and VFS index (`meta/<Layer>/asset_map/`,
   `meta/<Layer>/vfs_index/`): objects per Unity type under the bundle family.

The measurement and fail-closed rules are in the
`scripts/webui/recovery/build_recovery.py` docstring; rendering rules are in
`webui/src/features/recovery/index.js`.

## Primary generated outputs

```text
webui/data/recovery/index.json
```

One compact v5 payload: `levels`, `stageStates`, `lanes`, `evidenceLimits`,
`sources`, and `vfs` with `totals` and `blocks[]`; each block carries its
measured tally and `families[]` with four declared stages, and the Unity
bundle family carries `objectTypes[]`.

## Evidence boundary

- **Measured**: file counts, declared/profiled bytes, container-chunk counts
  and availability. The bar describes inventory, never recovery coverage.
- **Declared**: family patterns and stages. `closed` means the stated
  boundary is closed, `partial` that only selected records or fields are, and
  `open`/`notAssessed` keep the gap visible. No family can claim L4 closed.
- A stage restates the cited memory topic's conclusion. When a topic's
  conclusion changes, update the matching stage in the declarations in the
  same change; the stage text never carries counts.
- JsonData L2 stages follow the terminal statuses of the authenticated
  JsonData registry (`scripts.game_data.jsondata_corpus`): a family whose
  every current file is `schema_decoded` has a closed L2; a family with a
  bounded-partial or format-framed residue stays partial.
- Evidence limits record a disconfirmed route or a runtime observation gap,
  not a completion queue.
- Reports under `reports/` are local-only; the page shows an explicit missing
  or schema-mismatch state when `index.json` is absent or not v5.

## Focused refresh

```bat
python -m scripts.webui.recovery.build_recovery
python -m scripts.webui.recovery.build_recovery --print-summary
python -m unittest scripts.tests.test_build_recovery
```

The page is reached at `#recovery`. It is debug-only (`data-debug-view="1"`
in `index.html`, `DEBUG_ONLY_VIEWS` in `assets.js` with a `story` fallback) and
appears once `Show debug info` is on. It is not part of `export.bat`; the
asset-map scan adds about a minute to the build.

## Highest-value remaining gaps

- No level-4 coverage measurement exists. Stage statements are scoped
  interpretations, not counts of understood bytes; a coverage measure needs
  per-family, consumer-proven evidence.
- Cross-block measurements are not shown here: JsonData coverage belongs to
  [`../game_data/serialization_memorypack.md`](../game_data/serialization_memorypack.md)
  and MonoBehaviour field/table-key evidence to
  [`../game_data/unity_assets.md`](../game_data/unity_assets.md).
- Stage texts are hand-synchronised with memory. A declaration-side check that
  the JsonData L2 states agree with the latest registry summary would stop
  them drifting after a gate run.
- The block-to-lane map must be revisited whenever the VFS enum changes; the
  builder fails closed to force that.
