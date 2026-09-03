# WebUI recovery

This file is the maintenance entry point for the static WebUI. Page-specific
recovery contracts live under [`webui/`](webui/README.md); frontend-only layout
and behavior contracts remain in [`../webui/README.md`](../webui/README.md).

## Active pages

| Page | Recovery guide | Primary builder |
| --- | --- | --- |
| Story | [`webui/story.md`](webui/story.md) | `scripts.story_builder` |
| Map | [`webui/map.md`](webui/map.md) | `scripts.build_map_recovery_data` |
| Characters | [`webui/characters.md`](webui/characters.md) | `scripts.build_character_data` |
| Gameplay | [`webui/gameplay.md`](webui/gameplay.md) | `scripts.build_gameplay` |
| Audio | [`webui/audio.md`](webui/audio.md) | `scripts.build_audio` and `scripts.build_audio_semantics` |
| Assets | [`webui/assets.md`](webui/assets.md) | `scripts.build_assets` |
| Text | [`webui/text.md`](webui/text.md) | `scripts.story_builder` |
| Updates | [`webui/updates.md`](webui/updates.md) | `scripts.build_updates` |

Mission Pipeline is a standalone recovery workflow, not a WebUI page or normal
export stage. Retired Progression and Combat & Projectiles pages stay retired;
their useful data belongs to Gameplay.

## Export flow

Choose the smallest workflow that owns the changed input:

| Situation | Command |
| --- | --- |
| First setup | `.\setup.bat` |
| Rebuild all generated views from current `export_full/` | `.\export.bat` |
| Refresh installed-game Story/Table data, then rebuild | `.\export.bat --from-game` |
| Refresh Story and assets in one extraction, then rebuild | `.\export.bat --from-game --with-assets` |
| Apply changed installed VFS files locally, then rebuild every normal view | `.\export.bat --changed-only` |
| Story is current; rebuild downstream views/assets/audio | `.\export_assets.bat` |
| Story is current; refresh installed-game assets/audio first | `.\export_assets.bat --from-game` |
| Compare two complete exports for Updates | `.\build_updates.bat OLD NEW` |
| Serve / package | `python serve.py` / `python scripts\pack_webui.py` |

Without `--from-game`, wrappers read the configured `export_full/` and first
run `python scripts\verify_export_freshness.py`. Do not use `--from-game` for a
data-only rebuild. When both Story and assets need extraction, prefer one
`--from-game --with-assets` run over two AnimeStudio passes.

The canonical full flow is:

1. Resolve paths from `endfield_paths.bat`, overridden by explicit flags.
2. If requested, use AnimeStudio to refresh structured Story/Table inputs and
   optionally asset/audio outputs.
3. Refresh Story evidence and build localized Story and Text data.
4. Run post-Story builders in dependency-safe phases: Map, Characters,
   Gameplay/projectiles, optional Assets/audio, joined sidecars, curated source
   graph, then graph consumers.
5. Write step timings and process-tree memory benchmarks under
   `reports/export/`.

`--webui-jobs N` limits post-Story concurrency; `--asset-jobs N` limits
AnimeStudio workers. `--focused-assets`, `--default-assets`, and
`--debug-assets` select increasing extraction scope. Use
`--full-source-graph` only for exhaustive Unity object/PathID investigation.

`--changed-only` is a local refresh, not an Updates comparison. It runs the
same complete Story, semantic-view, asset, audio, graph, and graph-consumer
publication path as a full installed-game asset refresh, but it neither calls
the Updates builder nor advances any previous-export/Updates baseline. Its
private VFS snapshot commits only after all publication stages succeed.

## Shared contracts

- Generated data belongs in `webui/data/`; never hand-edit it. User-maintained
  inputs belong in `webui/overrides/`.
- A schema change updates producer and consumer together. Missing optional
  sidecars render as unavailable or degraded, never as a silent empty success.
- Normal navigation contains only the eight pages above. Debug state may reveal
  raw sources and recovery evidence, but Story issue/method filters stay visible.
- Story order and manual option overrides are user data and are not replaced by
  export runs.
- Evidence types remain distinct: authored reference, recovered relation,
  inferred ownership, runtime observation, and user annotation are not
  interchangeable.
- Reuse an existing `http://127.0.0.1:8765/` server before starting another.

## Verification

After a focused edit, run the owning builder and its focused tests. At a
publication boundary, run the canonical wrapper, inspect
`reports/export/webui_build_steps_latest.md` and
`reports/export/export_full_summary.md`, then smoke-test every active page for
console errors, deep links, filters, media playback, and explicit degraded
states. Use the serve/package workflow only when browser or archive validation
is required.

Changing counts and per-build inventories belong in `reports/`; page guides
record only stable recovery logic, evidence boundaries, and the highest-value
gaps.
