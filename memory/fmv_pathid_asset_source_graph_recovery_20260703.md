# FMV PathID Asset Source Graph Recovery - 2026-07-03

## Finding

FMV video binding recovery was emitting playable asset PathID nodes with the
node key `unity_pathid:pathid:<id>`. AnimeStudio AssetMap ingest emits PathID
nodes with the canonical key `unity_pathid:<id>`, so FMV playable PathIDs could
not join through `resolves_to_unity_asset` even when the AssetMap contained the
matching `BeyondFMVPlayableAsset` MonoBehaviour.

The fix makes FMV playable PathID nodes use the same canonical numeric PathID
key as AssetMap ingest while keeping the `pathid:<id>` alias. The FMV edge now
also records the recovered source root (`StreamingAssets` or `Persistent`) from
the recovered track/source file path, and `link_fmv_pathid_unity_assets()` skips
AssetMap rows whose Unity asset source does not match that source root.

FMV asset-link edge kinds were added to the asset usage query sets so graph
asset lookups can show both:

- FMV owner -> Unity asset: `fmv_playable_pathid_resolves_unity_asset`
- Unity asset -> FMV owner: `unity_asset_used_by_fmv_playable_pathid`

Exported browser asset edges can still be zero for this slice because these
playable assets are MonoBehaviour timeline objects, not necessarily converted
WebUI asset files.

## Validation

Syntax and whitespace checks:

```bat
python -B -m py_compile tools\endfield_source_graph.py
git diff --check -- tools/endfield_source_graph.py
```

Sample AssetMap validation:

```bat
python tmp\validate_fmv_pathid_graph.py
```

Result:

- `fmv_binding_playable_pathid`: 58
- `resolves_to_unity_asset`: 5
- `fmv_playable_pathid_resolves_unity_asset`: 10
- `unity_asset_used_by_fmv_playable_pathid`: 10
- `fmv_playable_pathid_exports_asset`: 0
- `asset_export_used_by_fmv_playable_pathid`: 0

Sample resolved links included:

- `fmv_clip:cs_video_dlg_e10m1_1:0` -> `unity_asset:StreamingAssets:-7643592810396086263`
- `fmv_binding:cs_video_dlg_e10m1_1` -> `unity_asset:StreamingAssets:-7643592810396086263`

Both resolve to `BeyondFMVPlayableAsset` in
`assets/beyond/dynamicassets/gameplay/dialog/timeline/dlgtl_e10m1_1_sub_1/playable/dlgtl_e10m1_1_sub_1_actor.playable`.

A targeted source-root guard check created one fake FMV PathID with duplicate
`StreamingAssets` and `Persistent` Unity assets. With `sourceRoot` set to
`StreamingAssets`, only `unity_asset:StreamingAssets:12345` was linked.

## Review Follow-Up

Post-commit review found two hardening gaps:

- FMV PathID resolution still linked globally if `sourceRoot` was missing.
- `used-by` defaulted to `asset`, so Unity asset and raw PathID seeds did not
  reliably expose the new FMV relationships.

The resolver now requires a known `sourceRoot` before linking a video binding
PathID to an AnimeStudio AssetMap Unity asset. Unknown-root rows remain present
as `fmv_binding_playable_pathid` evidence but do not produce
`fmv_playable_pathid_resolves_unity_asset`.

`used-by` now tries `asset`, then `unity_asset`, then `unity_pathid` by default,
and reports `resolvedKind`. Direct PathID usage includes
`fmv_binding_playable_pathid` on the used-by side and `resolves_to_unity_asset`
on the uses side.

Synthetic validation used `tmp\fmv_usage_guard.sqlite` and confirmed:

- an unknown-root duplicate PathID produced no FMV Unity-asset resolution;
- a known `StreamingAssets` PathID linked only to
  `unity_asset:StreamingAssets:12345`;
- default `used-by pathid:12345` resolved as `unity_asset`;
- forced `used-by pathid:12345 --kind unity_pathid` showed the direct FMV owner
  edge plus AssetMap `resolves_to_unity_asset` dependencies.

## Follow-Up

The disposable validator under `tmp/` uses normal asset/video ingests and builds
a large SQLite file even against the sampled AssetMap. Keep it as a local probe,
but if this validation path becomes reusable, replace it with a narrower unit
harness that inserts only the minimal graph rows needed by
`link_fmv_pathid_unity_assets()`.
