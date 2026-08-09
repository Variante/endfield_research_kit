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
**Audio** is also debug-only. It exposes the current binary-validated runtime
model, Wwise HIRC object families, authored event contexts, typed possible
media leaves, and the physical decoded-media inventory without presenting the
offline graph as a live playback trace.

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
- `src/features/audio/`: lazy, virtualized debug Audio page.
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
data/lang/<LANG>/audio/{index,events,media}.json
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

The Audio overview and Event inventory load only when its debug view is opened;
the larger media inventory remains deferred until the Media mode is selected.
Both lists are virtualized, and selecting an Event fetches only its keyed detail
shard before rendering contexts, branch evidence, and players. Playable recovered audio is served from
`/export_full/structured/Audio/{shared,<LANG>}/`. The normal builder emits
lossless `.flac` files and writes those paths into Story, cutscene, projectile,
and Gameplay sound payloads; the frontend uses the same native audio control
for FLAC and WAV links. Legacy WEM files remain indexable for diagnostics but
are not a browser-playable output format. Event details list every typed
possible media leaf together and group it by Play root and Random, Sequence,
Switch/State, Layer, or direct-Sound evidence. Partial typed graphs and
byte-identical decoded content under distinct media ids remain explicit.
Skill contexts separately tag exact Gameplay-action-to-SkillData dependencies and
inferred child-skill-family ownership. Their evidence records whether the Event
was found as a complete length-prefixed reference in SkillData or through an
exact BuffData chain; the generic scan does not recover a field/callsite, and
runtime condition/timing remains explicitly unresolved for dependency-only
rows. Decoded BuffData `PlaySoundActionData` adds exact authored frame windows,
stop/fade lifetime, routing, selector hints, and time-dilation controls for the
recovered subset; `TargetSettings`, live activation, and Wwise branch selection
remain explicit gaps. Exact PlaySound actions have their own Audio Event filter
and stay visible even when no displayed skill owner is proven. All trigger tags
and source/action fields are searchable.
Interactive-object contexts keep global model/sub-template defaults separate
from per-entity `InteractiveData` component overrides. Both expose exact
lifecycle/custom state, identity, source path, and Event evidence; global audio
policy adds entity-init and enter/exit state-mask Event mappings. These are
authored state-entry requests, not live traces or Wwise SetState operations.
Projectile contexts expose each exact nonzero launch, loop, reach, hit, block,
finish, or proximity-sizzle Event field with projectile identity and source
PathID. Skill ids stored by the projectile remain template references rather
than proof that a displayed skill spawned it; lifecycle execution and Wwise
branch selection remain unresolved.
The Audio control catalog keeps cue and parameter entities separate from Wwise
Events. Only AudioCue behavior expressions with `exprType=3` become Event
contexts; `exprType=8` operands, Global `musicCue*` IDs, and RTPC names retain
their own typed records and missing-definition state.

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
- Disabling debug while Audio or Mission Pipeline is active moves to Gameplay
  and normalizes the URL.

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
- Character skill rows show one compact linked-projectile summary and only the
  playable Events proven through that displayed Gameplay action id's exact
  SkillData or BuffData dependency chain. A skill may legitimately have no
  separate projectile template.
- Typed Wwise possible-media leaves are listed together, with Play roots and
  switch/state/random/sequence/layer evidence shown separately; the UI does
  not present them as equivalent choices or observed live playback. Direct and
  inferred skill/enemy ownership are labeled.
- Character-owned animation callbacks and shared Wwise animation systems are
  separate Gameplay groups. Shared footstep/cloth/material Events show owner
  counts and global reachable leaves without presenting those leaves as the
  character's private sound library; opening one Event still lists every
  playable file together. Inferred character-skill links, animation systems,
  and profile voice remain in the final character section; enemy audio remains
  at the end of the enemy page. Compact bank, Stop, selector-node, and
  child-edge counts substantiate large Wwise fan-outs.
- Gameplay thumbnails and model paths link back to the matching Assets entry.

### Mission Pipeline

- Trigger cards preserve evidence type and original source boundaries.
- Native playback without a mission owner remains explicitly unassigned.
- Definition-only rows never become activation, ownership, or order evidence.
- Quest topology and client-applied state do not prove server successor
  selection.
- Exact DialogTree/Timeline option finish outcomes may be shown beside the
  MissionRuntime objective that consumes the same finish ID. Each row exposes
  hash-validated original files, the structural option-node/slot scope, and
  whether the finish was explicit or the binary-validated runtime-default
  `Int32 0`. Reused localization option IDs stay separated by runtime scope.
  Each row remains a dependency, not an observed player choice or
  server-selected successor.
- Exact finish consumers without a proven option route are shown separately as
  endpoint-only dependencies. The shared recovery walks typed original
  DialogTrees from the binary-proven first serialized node, validates exact
  connection identities, and admits only reachable finish nodes. These cards
  expose the prime-node path, predecessor types, value source, and hashed
  DialogTree, MissionRuntime, binary, and metadata files. They prove an authored
  endpoint-to-objective dependency, not the route or choice that reaches it.
- Original DialogTree definition cards expose normal-option route validation.
  The binary-proven `NormalOptionData.index` selects a physical outgoing edge,
  including positions around extra-option edges, and `ShowOptions` sets
  `doNext` before normal selection. Unequal option/connection counts are allowed
  when exact indexes resolve. Unreferenced definitions, linked zero-edge nodes,
  and out-of-bounds indexes remain visibly distinct and fail closed; a missing
  edge is not presented as a terminal choice. OCR and manual overrides are
  never route evidence.
- Manual Story order and OCR proposals are cross-reference material, not graph
  evidence.

Detailed, changing Mission Pipeline inventories belong in generated reports;
stable Story conclusions belong in `memory/game_story_recovery.md`.

## Verification

After frontend or data changes:

1. Reuse or start the default server.
2. Confirm Story, Characters, Gameplay, Assets, Text, and Updates load.
3. Toggle debug and confirm Audio and Mission Pipeline appear and hide cleanly.
   In Audio, confirm Events loads first, Media loads on demand, and disabling
   debug returns to Gameplay.
4. Check Story reset/filter behavior and the inline SNS fixtures.
5. Open a playable character and an enemy; verify progression, variants,
   projectiles, sounds, and linked assets degrade cleanly when optional data is
   unavailable.
6. Check the browser console for new errors.

User setup belongs in the root `README.md`, script contracts in
`scripts/README.md`, and durable recovery status in `memory/`.
