# WebUI recovery

## Current status

The static WebUI is the primary project surface. It reliably builds Story,
Text Tables, Gameplay, Mission Pipeline, Assets, and Updates data from
`export_full/`. Generated data is reproducible; user-managed Story order stays
in `webui/overrides/story_order.json`.

Normal navigation exposes Story, Text Tables, Gameplay, Mission Pipeline,
Assets, and Updates. Experimental semantic views and source/debug panels are
behind `Show debug info`.

## Build and serve

```bat
.\export.bat
python serve.py
```

Before starting a server, reuse `http://127.0.0.1:8765/` if it is already
running.

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

`export.bat` verifies `export_full/` freshness. Installed-game refreshes require
`--export-from-game`; asset indexes and CN audio require `--with-assets` or
`export_assets.bat`.

## Data contract

Important generated roots:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/index.json
webui/data/lang/<LANG>/conv/
webui/data/lang/<LANG>/mission/
webui/data/lang/<LANG>/reference/
webui/data/mission_pipeline/
webui/data/assets/
webui/data/updates/latest.json
```

Builders must fail visibly when required evidence is stale. Presentation and
Combat degrade explicitly when their source graph is missing or older than
their inputs.

## Frontend behavior

- Story recovery issue/method filters remain visible in normal and debug mode.
- Reset returns to Story sort while preserving expanded mission groups.
- Disabling debug while a hidden page is active returns to a visible page.
- Mission Pipeline links show evidence-typed trigger chains.
- BlackBox recovery cards expose exact SubGame/bound-LevelScript context,
  separate authored task lanes, complete decoded task/condition topology,
  condition formulas, objective display keys, exact parent playback, and the
  serialized event/action graph. Ordered sequences, parallel fan-outs,
  conditional choices, loops, Story targets, runtime-shadowed duplicate-id
  records, and missing-slot normal terminals are visible,
  while definition-only parents and unordered event roots remain explicit;
  neither task definitions nor separate action roots invent Story chronology.
- Mission Story-order panels list compact original LevelScript graphs only when
  an exact native event-to-Story path relates the file to that mission. Their
  remaining actions are visibly file-local and do not imply extra order;
  active last-serialized slots stay distinct from shadowed physical records.
- Native playback without mission ownership stays explicitly unassigned.
- Definition-only rows remain distinct from playback.
- Mission or scene order is never inferred from registration or file order.

Inline media:

- `sns_emoji_*` stays small and inline with no hover or modal.
- `sns_image_*`, `sns_sticker_*`, and other non-emoji SNS media use normal
  proportions with bounded previews.

Runtime overrides:

- `webui/overrides/story_order.json`: full user-managed mission order.
- `webui/overrides/options.json`: manual option positions/responses.
- `webui/overrides/narrative_videos.json`: explicit video attachment rules.

Rebuild Story data after changing overrides.

## Updates and packaging

```bat
.\build_updates.bat --init-build
.\build_updates.bat
.\build_updates_by_patch.bat --check
.\build_updates_by_patch.bat
python scripts\pack_webui.py
```

Updates compare previous/current export roots only. Packaging produces the
static browser plus optional assets and audio archives.

## Verification

After frontend or data changes:

1. Check export freshness.
2. Run the smallest relevant builder.
3. Open Story, Mission Pipeline, Text Tables, Assets, and Updates as applicable.
4. Verify normal/debug navigation and inline SNS media.
5. Keep generated reports under their topic folders.

The default CN Story build is minutes, so batch recovery edits and use focused
tests or `--mission-pipeline-data-only` during iteration.
