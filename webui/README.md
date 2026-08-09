# WebUI

`webui/` is the primary supported interface: a static browser over generated
Endfield research data.

## Run

From the repository root:

```bat
.\export.bat
python serve.py
```

Reuse `http://127.0.0.1:8765/` when it is already running. Generated payloads
under `webui/data/` are builder outputs and must not be edited by hand.

## Pages

Normal navigation exposes:

- **Story:** dialog, radio, SNS, cutscenes, options, media, recovery labels,
  and evidence-aware ordering.
- **Characters:** grouped names, source evidence, aliases, and linked assets.
- **Gameplay:** characters, weapons, equipment, enemies, usable items,
  progression requirements, skills, projectiles, assets, and recovered audio.
- **Assets:** exported images, models, materials, video, and metadata.
- **Text:** searchable localized table rows.
- **Updates:** differences between previous and current exported game data.

**Mission Pipeline** is experimental and appears only with `Show debug info`.
The standalone Progression and Combat & Projectiles pages are retired. Their
useful player-facing data now appears in Gameplay; raw combat relationships,
projectile matching evidence, and unresolved ownership remain debug-only.

## Frontend map

- `index.html`: application shell and page containers.
- `style.css`: shared layout, controls, cards, and media presentation.
- `app.js`, `app_tree.js`, `app_labels.js`: Story loading, rendering, tree,
  labels, filters, and shared media behavior.
- `reference.js`, `assets.js`, `updates.js`: Text, Assets, and Updates pages.
- `src/features/characters/`: Characters page and live override editing.
- `src/features/gameplay/`: Gameplay page and integrations.
- `src/features/mission_pipeline/`: experimental mission evidence view.
- `src/features/{economy,world,presentation,projectiles,combat}/`: semantic
  payload integrations used by Gameplay or debug views.

## Data contract

Important generated roots:

```text
data/manifest.json
data/lang/<LANG>/index.json
data/lang/<LANG>/conv/
data/lang/<LANG>/mission/
data/lang/<LANG>/reference/
data/lang/<LANG>/characters/index.json
data/lang/<LANG>/gameplay/index.json
data/lang/<LANG>/gameplay/sound_effects.json
data/lang/<LANG>/{economy,world,presentation}/index.json
data/gameplay/projectiles.json
data/mission_pipeline/
data/assets/index.json
data/assets/gameplay_refs.json
data/assets/story_media.json
data/assets/videos.json
data/updates/latest.json
```

Gameplay loads its base index and optional combat, projectile, audio, and asset
sidecars independently. Missing optional sidecars must degrade to the base
record instead of breaking the page. Presentation and combat builders expose a
visible degraded reason when their source graph is absent or stale.

## Runtime overrides

Manual inputs live under `webui/overrides/`:

- `story_order.json`: complete user-managed order for each mission.
- `options.json`: manual option positions and response routes.
- `narrative_videos.json`: explicit video attachment, suppression, and audio
  inheritance rules.
- `character_merges.json`: additive identity merges and a `flagged` queue.
- `character_name_overrides.json`: replacement display names keyed by the same
  canonical character ids.

Story overrides require a Story rebuild. Character merges and display names
are edited live from the Characters page through `serve.py`; they do not
require rebuilding generated character data. Self-merges and cycles are
rejected, and merging a flagged source clears that flag.

## Behavior contract

### Shared navigation

- Recovery issue and method filters remain visible in normal and debug modes.
- Source panels, mission evidence, and Story order editing stay behind
  `Show debug info`.
- Story reset returns to Story sort while preserving expanded mission groups.
- Disabling debug while Mission Pipeline is active moves to a visible page and
  normalizes the URL.

### Story and media

- `sns_emoji_*` renders as small inline emoji with no hover or modal.
- `sns_image_*`, `sns_sticker_*`, and related non-emoji media preserve normal
  image proportions.
- Hover and modal previews remain inside their frame and the viewport.
- Definition-only rows, non-owning context, exact playback, and mission
  ownership remain visibly distinct.
- Mission or scene order is never inferred from registration, source-list
  order, file order, or code addresses.

Useful inline-media fixtures:

```text
test_sns_emojicomment
test_sns_sticker
sns_topic_map02_lv005_12002
```

### Characters and Gameplay

- Character groups use canonical ids derived from constituent table/asset ids,
  not localized display text, so overrides survive language builds.
- Filename-derived identities pass documented exclusion lists in
  `scripts/build_character_data.py`; add exclusions only after tracing the
  exact false-positive source family.
- Playable-character details keep breakthrough requirements, skill/talent
  costs, potential art, stats, and identity assets in their owning sections.
- Skill glyphs stay centered in circular controls. Normal-skill, Ultimate, and
  Combo discs use the owning character's exact `CharTypeTable.json` color:
  Cryst `#21C6D0`, Fire `#FF623D`, Natural `#9EDC23`, Physical `#888888`, and
  Pulse `#FFC000`; Normal Attack remains neutral.
- Enemy variants are a selectable difference table. Stat controls expose only
  authored points and never interpolate missing levels.
- Character skill rows show one compact linked-projectile summary and playable
  sound groups in normal mode. A skill may legitimately have no separate
  projectile template.
- Exact Wwise media candidates stay grouped when switch/random selection is
  unresolved. Direct and inferred skill/enemy ownership are labeled.
- Gameplay thumbnails and model paths link back to the matching Assets entry.

### Mission Pipeline

- Trigger cards preserve evidence type and original source boundaries.
- Native playback without a mission owner remains explicitly unassigned.
- Definition-only rows never become activation, ownership, or order evidence.
- Quest topology and client-applied state do not prove server successor
  selection.
- Manual Story order and OCR proposals are cross-reference material, not graph
  evidence.

Detailed, changing Mission Pipeline inventories belong in generated reports;
stable Story conclusions belong in `memory/game_story_recovery.md`.

## Verification

After frontend or data changes:

1. Reuse or start the default server.
2. Confirm Story, Characters, Gameplay, Assets, Text, and Updates load.
3. Toggle debug and confirm Mission Pipeline appears and hides cleanly.
4. Check Story reset/filter behavior and the inline SNS fixtures.
5. Open a playable character and an enemy; verify progression, variants,
   projectiles, sounds, and linked assets degrade cleanly when optional data is
   unavailable.
6. Check the browser console for new errors.

User setup belongs in the root `README.md`, script contracts in
`scripts/README.md`, and durable recovery status in `memory/`.
