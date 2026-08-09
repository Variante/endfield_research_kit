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

## Build and serve

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` before starting another server.

Useful variants:

```bat
.\export.bat --export-from-game
.\export.bat --with-assets
.\export.bat --export-from-game --with-assets
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python scripts\pack_webui.py
```

`export.bat` freshness-checks `export_full/`. Installed-game refreshes require
`--export-from-game`; asset indexes and CN audio require `--with-assets` or
`export_assets.bat`.

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
  through `serve.py` and use stable canonical character ids.

## Stable frontend behavior

- Recovery issue/method filters remain visible in normal and debug modes.
- Story source panels and manual order controls stay behind debug mode.
- Reset restores Story sort while preserving expanded mission groups.
- Disabling debug from Mission Pipeline returns to a visible page and URL.
- `sns_emoji_*` stays small and inline without hover/modal behavior;
  non-emoji SNS media preserves normal proportions and bounded previews.
- Character groups remain stable across languages because overrides key on a
  constituent table/asset id rather than display text.
- Gameplay owns breakthrough requirements, authored enemy stat points,
  selectable enemy variants, linked assets, compact projectile behavior, and
  playable Story-style sound controls. Character and enemy audio is one final
  detail section after normal and integrated content, never embedded in skill
  cards; shared selector events expose bank, Stop, selector-node, and child-edge
  evidence before their together-listed files. Character Normal Skill,
  Ultimate, and Combo discs preserve the exact element colors authored in
  `CharTypeTable.json`; Normal Attack remains neutral.
- A skill can legitimately have no separate projectile template. Exact,
  inferred, and unresolved skill/enemy/projectile ownership stay distinct.
- Mission Pipeline distinguishes exact playback, ownership, non-owning
  context, definition-only data, and unresolved activation.
- Quest topology, native registration, source order, and code addresses never
  become mission ownership or Story chronology by themselves.

## Updates and packaging

```bat
.\build_updates.bat --init-build
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
2. Smoke-test all six normal pages and the debug-only Mission Pipeline.
3. Verify Story reset/filter behavior and inline SNS fixtures.
4. Open a playable character and enemy; check variants, progression,
   projectiles, sounds, and asset links.
5. Check console errors and keep generated reports in their topic folders.

Batch Story recovery changes; the default CN build takes minutes, and even a
Mission Pipeline data-only rebuild can be expensive on this checkout.
