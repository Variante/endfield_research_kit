# WebUI recovery

## Current status

The static WebUI is the primary project surface. Normal navigation exposes
Story, Characters, Gameplay, Assets, Text, and Updates. Mission Pipeline is
experimental and appears only with `Show debug info`.

Story, localized reference data, character identities, gameplay semantics,
assets, and update comparisons build reproducibly from `export_full/`.
User-managed Story order remains outside generated data in
`webui/overrides/story_order.json`.

Standalone Progression and Combat & Projectiles views are retired. Progression
requirements and useful projectile/audio summaries live in Gameplay; raw
combat, matching, and unresolved-ownership evidence remains debug-only.
The Audio tab is a normal public semantic view (`debugOnly:false`), while raw
identities remain behind its debug toggle. Gameplay sound cards use one flat
event stream with all decoded candidates listed together; shared animation
events are labeled as global Wwise graphs rather than character-owned files.

## Build and serve

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` before starting another server.

Useful variants:

```bat
.\export.bat --from-game
.\export.bat --with-assets
.\export.bat --from-game --with-assets
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python scripts\pack_webui.py
```

`export.bat` freshness-checks `export_full/`. Installed-game refreshes require
`--from-game`; asset indexes and CN audio require `--with-assets` or
`export_assets.bat`.

After Story is current, `export.bat` runs independent semantic builders through
`scripts/build_webui_views.py`. Mission Pipeline, Gameplay, projectiles,
economy, world, and eligible Assets/Characters work overlap without crossing
their output boundaries. Joined Gameplay asset references wait for both source
indexes; the source graph waits for every producer; Presentation and Combat
then overlap. Use `--webui-jobs N` to cap concurrency. Per-task wall times and
measured overlap savings are written under `reports/export/`.
Mission-Pipeline-only runs no longer rebuild the unrelated Characters payload.
The source graph keeps its uniqueness indexes as the lookup indexes for edge
sources and aliases instead of maintaining duplicate one-column indexes; graph
rows and query behavior are unchanged.

Repeated installed-game updates should use `build_updates_by_patch.bat` after
its baseline is initialized. Its logical VFS comparison is the lossless
incremental path; full AnimeStudio extraction intentionally does not reuse the
retired weak cross-run file-count/size/mtime cache.

## Stable data contracts

Primary generated roots are:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/{index,conv,mission,reference}/
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/
webui/data/lang/<LANG>/{economy,world,presentation}/
webui/data/gameplay/projectiles.json
webui/data/mission_pipeline/
webui/data/assets/
webui/data/updates/latest.json
```

Generated payloads are never manual inputs. Gameplay loads optional combat,
projectile, audio, and asset sidecars independently and degrades to its base
record when one is missing. Presentation and combat payloads record an
explicit degraded reason when the source graph is absent or stale.

Runtime overrides:

- `story_order.json`, `options.json`, and `narrative_videos.json` require a
  Story rebuild.
- `character_merges.json` and `character_name_overrides.json` are edited live
  through `serve.py`, use stable canonical character ids, and expose their
  Characters-page editing controls only in debug mode.

## Stable frontend behavior

- Recovery issue/method filters remain visible in normal and debug modes.
- Story source panels, manual order controls, and Characters name/identity
  override controls stay behind debug mode.
- Reset restores Story sort while preserving expanded mission groups.
- Disabling debug from Mission Pipeline returns to a visible page and URL.
- `sns_emoji_*` stays small and inline without hover/modal behavior;
  non-emoji SNS media preserves normal proportions and bounded previews.
- Story and Gameplay share one persisted female/male segmented selector.
  Story gender-authored text, voice, images, video, and gender-only cutscene
  lines update together when it changes.
- Character groups remain stable across languages because overrides key on a
  constituent table/asset id rather than display text.
- Characters preserves its generated default order and can sort ascending or
  descending by alphabet, identity count, evidence groups, resource count,
  observed names, or evidence-source coverage.
- Gameplay owns breakthrough requirements, authored enemy stat points,
  selectable enemy variants, linked assets, compact projectile behavior, and
  playable Story-style sound controls. Only Events joined through the exact
  displayed Gameplay action id and its SkillData or referenced BuffData return
  to that skill row as exact Event dependencies, not generic playback claims.
  Decoded BuffData PlaySound actions add exact authored frame
  windows and stop/fade lifetime where available; activation conditions and
  Wwise selection remain unresolved. Inferred skill links, animation systems,
  profile voice, and all enemy audio stay in the final detail section. Shared
  selector events expose bank, Stop, selector-node, and child-edge evidence
  before their together-listed files. Character Normal Skill,
  Ultimate, and Combo discs preserve the exact element colors authored in
  `CharTypeTable.json`; Normal Attack remains neutral.
- Endministrator remains one canonical Gameplay character. Its persisted
  female/male switch selects concrete portraits, action rows, Story voice
  links, potential pictures, and recovered skill sounds without replacing the
  shared `chr_9000_endmin` stats, skill descriptions, talents, or potentials.
- A skill can legitimately have no separate projectile template. Exact,
  inferred, and unresolved skill/enemy/projectile ownership stay distinct.
- Mission Pipeline distinguishes exact playback, ownership, non-owning
  context, definition-only data, and unresolved activation.
- Reading-popup actions resolve their direct `_readingPopId` through
  ReadingPopUpTable. When an aligned WorldEntityRegistry script/slot and
  complete embedded interaction record raise the receiver's exact custom
  event, Mission Pipeline shows the map entity, slot, event, and coordinates;
  mission/quest ownership and order remain separate.
- Mission Pipeline spatial maps keep weak X/Z carrier proximity separate from
  exact triggers and Story order, with hover previews and a distinct
  unresolved-trigger file tray. Exact interaction anchors also show their
  nearest mission tracking point and 3D/XZ distance as explicitly non-owning,
  non-ordering spatial context. Exact native event producers with an aligned
  WorldEntityRegistry script/slot are also placed at their entity positions;
  this is a targeted runtime-map layer, not a full scene-geometry export.
- Spatial-map points are evidence-coordinate clusters, not Story instances or
  playback counts. Exact entity triggers may legitimately repeat at distinct
  authored positions. Weak LevelScript placement now separates direct carrier
  files from `levelscriptCrossFileOrder`-inherited neighbors: inherited matches
  remain auditable but are not drawn and never enter weak quest sorting. Each
  Story key draws only its nearest direct weak candidate; additional direct
  candidates are folded below the map. Exact positions suppress the same key's
  weak marker. This removes the former false visual multiplication without
  discarding the underlying diagnostic evidence.
- Quest topology, native registration, source order, and code addresses never
  become mission ownership or Story chronology by themselves.

## Updates and packaging

```bat
.\build_updates.bat --first-time
.\build_updates.bat
.\build_updates_by_patch.bat --check
.\build_updates_by_patch.bat
python scripts\pack_webui.py
```

Updates compare saved/current export roots only. Packaging includes the static
browser and optional asset/audio archives while omitting retired generated
Progression payloads.

## Highest-value gaps

- Keep optional semantic sidecars visibly degraded rather than silently stale.
- Continue improving exact Gameplay-to-asset and sound ownership.
- Preserve clear evidence labels as Mission Pipeline gains new runtime joins.
- Keep the Characters false-positive exclusions and live override data clean.
- Maintain responsive, accessible behavior across large Story, Gameplay, and
  Assets datasets.

## Verification

After frontend or data changes:

1. Check export freshness and run the smallest relevant builder.
2. Smoke-test all normal pages, the debug-only Mission Pipeline, and the
   debug-only Characters override controls.
3. Verify Story reset/filter behavior and inline SNS fixtures.
4. Open a playable character and enemy; check variants, progression,
   projectiles, sounds, and asset links.
5. Check console errors and keep generated reports in their topic folders.

Batch Story recovery changes; the default CN build takes minutes, and even a
Mission Pipeline data-only rebuild can be expensive on this checkout.
