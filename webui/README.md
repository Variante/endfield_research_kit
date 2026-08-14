# WebUI

`webui/` is a static research browser over generated Endfield data. It has no
application build step: serve the repository and open the default local URL.

## Run

```bat
python serve.py
python serve.py 9000
```

Reuse `http://127.0.0.1:8765/` when it is already running. A custom port is for
an explicitly separate server.

## Pages

| Page | Scope |
| --- | --- |
| Story | Reconstructed dialog, SNS, radio, options, cutscenes, media, and evidence-typed order |
| Characters | Identity groups, source evidence, related assets, and live overrides |
| Gameplay | Characters, equipment, enemies, items, progression, skills, projectiles, assets, and sound |
| Audio | Wwise Events/media, authored contexts, decoded playback candidates, and recovery state |
| Assets | Exported images, models, materials, video, and metadata |
| Text | Searchable localized table/reference rows |
| Updates | Exported game-data changes between two complete versions |
| Mission Pipeline | Experimental debug-only mission/Story evidence |

Factory, World, Presentation, Progression, and standalone Combat & Projectiles
pages are retired. Useful progression, projectile, and sound information lives
in Gameplay.

## Frontend map

- `index.html`: application shell and page containers.
- `style.css`: shared layout, responsive behavior, and media presentation.
- `app.js`, `app_tree.js`, `app_labels.js`: Story/Text rendering and labels.
- `reference.js`: localized Text Tables browser.
- `assets.js`, `updates.js`: Assets and Updates pages.
- `src/features/characters/`: Characters view and runtime overrides.
- `src/features/gameplay/`: Gameplay datasets and sound players.
- `src/features/audio/`: Audio evidence browser.
- `src/features/mission_pipeline/`: debug-only Mission Pipeline.

Generated data belongs in `webui/data/`; user-managed inputs belong in
`webui/overrides/`. Do not hand-edit generated JSON.

## Data layout

Core generated outputs:

```text
webui/data/manifest.json
webui/data/lang/<LANG>/index.json
webui/data/lang/<LANG>/conv/*.json
webui/data/lang/<LANG>/mission/*.json
webui/data/lang/<LANG>/reference/**
webui/data/lang/<LANG>/characters/index.json
webui/data/lang/<LANG>/gameplay/**
webui/data/lang/<LANG>/gameplay/projectile_audio.json
webui/data/lang/<LANG>/audio/{index,events,media}.json
webui/data/gameplay/projectiles.json
webui/data/mission_pipeline/index.json
webui/data/mission_pipeline/missions/*.json
webui/data/assets/{index,gameplay_refs,story_media,videos}.json
webui/data/updates/latest.json
```

Builders may add compact sidecars, but each page must tolerate an absent
optional sidecar and display an explicit degraded state when the omission
matters. Schema changes must be coordinated with their frontend consumer.

`data/gameplay/projectiles.json` owns immutable projectile behavior and authored
event hashes. The language-specific `projectile_audio.json` sidecar owns decoded
media candidates; Gameplay joins it by projectile id, sound field, and unsigned
event hash without writing audio rows back into the behavior payload.

`data/assets/gameplay_refs.json` is also Gameplay-owned: the `asset-refs` stage
joins the current Gameplay index to the Assets-owned broad index. The Assets
builder never writes this consumer-specific sidecar.

## Shared behavior

- Normal navigation exposes Story, Characters, Gameplay, Audio, Assets, Text,
  and Updates.
- Mission Pipeline appears only while `Show debug info` is enabled. Turning
  debug off while it is active returns to a visible page and normalizes the URL.
- Debug state controls raw source blocks, recovery evidence, Mission Pipeline,
  manual Story-order tools, and unresolved ownership details. Story issue and
  recovery-method filters remain visible in normal mode.
- Missing optional data is a visible unavailable/degraded state, not an empty
  success state.
- Filters, keyboard focus, modal behavior, and large result sets must remain
  usable on narrow and wide screens.

## Story and media

Story combines authored dialog structures, Timeline evidence, mission/runtime
links, localized references, and manual order. Evidence types stay visible;
weak proximity or naming matches never become exact chronology or ownership.

Stable contracts:

- Reset returns to Story sort and default filters while preserving expanded
  mission groups.
- Source/debug blocks, Timeline evidence, cutscene diagnostics, and order-edit
  controls remain debug-only.
- `sns_emoji_*` renders as ordinary inline emoji without hover or modal preview.
- Other SNS images and stickers keep their natural proportions with bounded
  hover and modal previews.
- Definitions, authored placement, runtime activation, and observed playback
  are distinct states. A media definition does not prove that it played.
- Cutscene presentation shapes remain distinct: rooted Timeline, component-only
  Timeline, LevelScript FMV, mixed carriers, and text-only candidates are not
  silently merged.
- Subtitle text is attached only through an exact authored link or a unique,
  complete ordered match. Partial or ambiguous matches fail closed.

Manual inputs:

- `overrides/story_order.json` is the active user-managed order. Export tools
  never replace it.
- `data/story_order_ocr.json` contains OCR proposals only.
- `overrides/options.json` stores manual option placement/response recovery.
- `overrides/narrative_videos.json` controls inline video attachment,
  suppression, and optional audio inheritance.

## Characters and Gameplay

Characters merges table, Story, and asset identities while retaining source
provenance. Merge/name overrides are live inputs written through `serve.py` and
do not require a rebuild. Debug-only controls must not leak into normal page
navigation.

Gameplay owns character progression, equipment, enemies, skills, projectiles,
assets, and compact sound players. Evidence labels distinguish exact authored
ownership from family-, animation-, or identifier-inferred placement.

- Enemy level selectors show only authored level points; missing levels are not
  interpolated.
- Enemy variants may share an attribute template while retaining different
  buffs, modifiers, AI, or assets.
- Projectile templates, spawned behavior, and playable-skill ownership remain
  separate relations.
- Character-skill and enemy SFX players are collapsed compactly. Inferred
  ownership is labeled; raw identity, matching, and unresolved candidates are
  debug-only.
- Shared animation Events are global Wwise graphs unless a stronger owner edge
  exists.

## Audio

Audio keeps four layers separate:

1. authored Event or media identity;
2. Wwise graph relation and possible media leaves;
3. authored consumer/trigger context;
4. observed runtime execution or selected branch.

Only the available layer is claimed. Exact HIRC traversal can prove possible
media but not switch/random selection or audibility. String literals and
same-name assets remain identity evidence until a typed consumer reaches a
playback API. Fingerprint-locked native evidence fails closed after a client
update.

When native inputs are missing or mismatched, authored Audio rows remain
visible; only build-locked callsites, mappings, and addresses disappear, with
the unavailable state shown explicitly.

Shared SFX/music and language voice stay in separate storage roots. Repeated
media IDs preserve every physical occurrence and package provenance. Direct
Story-line binding, authored context, Event-only relation, and unknown placement
are mutually exclusive generated media states.

The default purpose-priority sort and recovery filters put unknown-purpose
Events/media ahead of partial and known-purpose records. A direct Story-line
binding is a terminal known-purpose state and is not part of the investigation
queue. Candidate player cards stay expanded and materialized unless more than
20 candidates share the same playback group; larger groups start collapsed.
Responsive enemy-voice contexts may show the fingerprint-locked
`EnemyTriggerVoiceAction` voice-type-to-trigger-key mapping, while live branch
selection and audibility remain unobserved.

## Mission Pipeline

Mission Pipeline shows evidence-typed trigger chains and the gaps between
Story definitions, mission ownership, activation, and playback.

- Native registration or code-address order never implies mission order.
- Definition-only rows remain distinct from activation evidence.
- Unlinked native playback keeps an explicit ownership gap.
- Strong and weak graph edges remain visually and semantically separate.
- Manual/OCR order may guide research but does not upgrade source evidence.

## Updates

Updates displays changes produced by comparing two complete export roots. The
default feed covers WebUI-facing exported text plus image, model, video, and
decoded audio assets. It must never treat changes under `webui/`, `reports/`,
`memory/`, or `scratch/` as game-data updates.

```bat
.\build_updates.bat OLD NEW
```

## Build and verification

Use the smallest relevant root workflow:

```bat
.\export.bat
.\export.bat --mission-pipeline-only --reuse-timeline-orders --reuse-reference
.\export.bat --mission-pipeline-data-only
.\export_assets.bat
python scripts\pack_webui.py
```

Before reading an existing extraction, run
`python scripts\verify_export_freshness.py` unless freshness is already known.
If it is stale, refresh with `.\export.bat --from-game`.

After frontend or generated-data changes:

1. Load every normal page and check the browser console.
2. Toggle debug mode and verify Mission Pipeline routing in both directions.
3. Check Story reset, recovery filters, and SNS emoji/sticker fixtures.
4. Open a playable character and enemy; verify variants, progression, skills,
   projectiles, sounds, and asset links.
5. Confirm unavailable optional inputs produce a clear degraded state.

Useful Story media fixtures are `test_sns_emojicomment`, `test_sns_sticker`,
and `sns_topic_map02_lv005_12002`.
