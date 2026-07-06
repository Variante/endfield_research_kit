# Runtime Audit Asset Path Diagnostics - 2026-07-06

## Scope

The `dlg_c28m3_10` option-route conflict investigation found that
`reports/runtime_jump_option_route_audit_CN_nearby_promoted.json` can contain
RuntimeJumpClip `assetTrack` paths whose timeline folder no longer matches the
current recovered file layout. The basename still resolves to a current file,
but the stale path makes raw evidence review harder.

This pass adds source-graph diagnostics for runtime-audit asset paths without
changing Story recovery or option-route promotion behavior.

## Change

`tools/endfield_source_graph.py` now has
`resolve_runtime_audit_asset_path(path_text)`.

Resolution behavior:

- If the exact path exists under the repo, report:
  - `assetTrackPathStatus="exists"`
  - `assetTrackExists=true`
  - `assetTrackResolvedPath=<same path>`
- If the exact path is missing but the basename has one match under
  `export_full/recovered/AnimeStudio-cli/timeline_extract/`, report:
  - `assetTrackPathStatus="basename_resolved"`
  - `assetTrackExists=false`
  - `assetTrackResolvedPath=<current matched path>`
- If the basename has multiple matches, report:
  - `assetTrackPathStatus="basename_ambiguous"`
  - `assetTrackExists=false`
  - `assetTrackResolvedCount=<count>`
  - `assetTrackResolvedPath=<first sorted match>`
- If there is no match, report:
  - `assetTrackPathStatus="missing"`
  - `assetTrackExists=false`

`ingest_runtime_option_route_audits()` now merges this diagnostic into each
`runtime_audit_nearby_jump` edge payload.

## Validation

Direct helper checks:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/EC06385C4A4367757C11409D45CD903E/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json
```

returns:

```json
{
  "assetTrackPathStatus": "basename_resolved",
  "assetTrackExists": false,
  "assetTrackResolvedPath": "export_full/recovered/AnimeStudio-cli/timeline_extract/79C9C13CFD1A1A38E3C8279B47406BCD/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json"
}
```

The current exact path:

```text
export_full/recovered/AnimeStudio-cli/timeline_extract/79C9C13CFD1A1A38E3C8279B47406BCD/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json
```

returns `assetTrackPathStatus="exists"`.

A missing path returns `assetTrackPathStatus="missing"`.

A tiny temp SQLite graph that only called
`SourceGraphBuilder.ingest_runtime_option_route_audits()` verified that the
`dlg_c28m3_10` group-1 nearby jump edge for
`option_dlg_c28m3_10_1_001` now carries:

```json
{
  "assetTrackExists": false,
  "assetTrackPathStatus": "basename_resolved",
  "assetTrackResolvedPath": "export_full/recovered/AnimeStudio-cli/timeline_extract/79C9C13CFD1A1A38E3C8279B47406BCD/MonoBehaviour/RuntimeJumpClip_p96B55F633837CFA8.json"
}
```

## Interpretation

This diagnostic separates two cases that previously looked the same during
manual review:

- truly missing audit assets;
- stale report paths where the recovered asset still exists in the current
  timeline extraction under a different folder.

It does not prove runtime route semantics. The route caveat remains unchanged:
nearby RuntimeJumpClip edges are static timeline evidence and should stay
diagnostic until option-index mapping and jump target semantics are proven.

## Next Checks

- Rebuild the normal ignored source graph when broader story-report refresh is
  useful so `option-route-audit` output includes these fields.
- Consider adding a compact `assetPathStatusCounts` section to
  `option-route-audit` if more stale paths appear across the hotlist.
- Inspect `dlg_e6m1_10` and `dlg_e6m4_14` conflicts for the same stale-path or
  late-merge RuntimeJumpClip pattern.
