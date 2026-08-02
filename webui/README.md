# WebUI

`webui/` is a static browser for generated Endfield research data. It is the
primary supported user interface.

## Run

From the repository root:

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` if it is already running.

## Pages

- **Story:** recovered dialog, radio, SNS, cutscenes, options, media, and
  evidence.
- **Text Tables:** searchable localized table rows.
- **Gameplay:** curated character, weapon, ability, progression, economy, and
  world records.
- **Mission Pipeline (experimental):** quest DAG plus evidence-typed Story
  trigger chains.
- **Assets:** exported images, models, materials, video, and metadata.
- **Updates:** differences between previous and current exported game data.

Mission Pipeline, Characters, Progression, Combat & Projectiles, standalone
Combat, Factory, World, and Presentation are experimental and appear only with
`Show debug info`.

## Main files

- `index.html`: application shell.
- `style.css`: shared layout and media presentation.
- `app.js`: loading and Story rendering.
- `app_tree.js`: navigation, grouping, and filters.
- `app_labels.js`: shared labels and formatting.
- `reference.js`: Text Tables.
- `assets.js`: Assets.
- `updates.js`: Updates.

Generated payloads live under `webui/data/`; do not hand-edit them.

## Data layout

```text
data/manifest.json
data/lang/<LANG>/index.json
data/lang/<LANG>/conv/
data/lang/<LANG>/mission/
data/lang/<LANG>/reference/
data/mission_pipeline/
data/assets/
data/updates/latest.json
```

Manual runtime inputs live under `webui/overrides/`:

- `story_order.json`: complete user-managed mission order.
- `options.json`: manual option positions and responses.
- `narrative_videos.json`: explicit video attachment/suppression rules.

Rebuild Story data after editing overrides.

## Behavior contract

- Recovery issue and method filters stay visible in all modes.
- Debug panels and manual order controls are behind `Show debug info`.
- Reset returns to Story sort and preserves expanded mission groups.
- Disabling debug from a hidden page returns to a visible page and URL.
- Mission Pipeline distinguishes ownership, context, definition-only rows, and
  unresolved native playback.
- BlackBox recovery shells show the exact SubGame row, bound LevelScript,
  separate main/extra/fail task lanes, complete decoded task conditions,
  condition formulas, objective display keys, typed parent playback, and
  parents that remain definition-only. Task topology is never presented as a
  successor graph or Story order.
- Mission Pipeline opens source-bounded activation gaps in the order panel and
  shows exact ReadingPopUp/RichContent row identities for definition-only text
  files and
  lists exact recovered definition files, tables, non-owning LevelData context,
  and internal Timelines without promoting OCR or manual order to evidence.
- Quest diagnostics list the exact original-data files and decoded property or
  NPC-proxy record that bounds a non-owning co-membership; authored DialogTree
  branch context remains visible even when it cannot identify a unique trigger.
- Mission order is never inferred from registration, source-file order, or
  code addresses.
- World rows without an exported level remain unassigned.
- Identifier-only Combat ownership remains visibly inferred.

## Inline media

- `sns_emoji_*` renders as small inline emoji with no hover or modal.
- `sns_image_*`, `sns_sticker_*`, and related non-emoji media render at normal
  proportions.
- Hover and modal previews stay bounded by the viewport.

Useful fixtures:

```text
test_sns_emojicomment
test_sns_sticker
sns_topic_map02_lv005_12002
```

## Verification

After frontend changes:

1. Reuse or start the local server.
2. Confirm Story and Text Tables load.
3. Check normal and debug navigation.
4. Verify Mission Pipeline unresolved/definition-only labeling.
5. Check emoji, sticker, image, hover, and modal behavior.
6. Confirm no generated data contract changed unintentionally.

## Scope

Keep this README focused on frontend behavior. User setup belongs in the root
`README.md`, script contracts in `scripts/README.md`, and durable recovery
status in `memory/`.
