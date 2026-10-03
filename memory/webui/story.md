# Story page recovery

## Purpose

Story presents localized conversations, mission grouping, options, inline
media, and typed recovery evidence. It combines sources without flattening
authored structure, Timeline placement, runtime links, manual order, or
inference into one confidence class.

## Inputs and recovery flow

1. AnimeStudio exports Table/JsonData plus broad `TextAsset`, `MonoBehaviour`,
   and `PlayableDirector` evidence from both installed roots.
2. `scripts.webui.story.refresh_evidence` refreshes source evidence and
   fail-closed native-gated reports.
3. `scripts.webui.story.source_links` joins mission/runtime references to
   Story keys.
4. `scripts.webui.story.build` localizes, groups, orders, and publishes
   conversations and references.
5. Manual inputs in `webui/overrides/story_order.json`, `options.json`, and
   `narrative_videos.json` are applied without being overwritten.
6. The page also reads `webui/data/mission_pipeline/index.json` for
   `storyCoverage.storyTriggerManifest`, published by the standalone Mission
   Pipeline workflow rather than a Story builder. Its absence is a degraded
   trigger state, not a failed build.

The page has two export modes. `export.bat story` is text only (tables,
JsonData and the Story Unity classes); the page renders text when media inputs
are absent. `export.bat story-media` adds the `story_media` task
(`build_assets --publish story-media`), which projects Story's inline, CG,
BigLogo and remote-comm images and its videos onto the exported Texture2D,
Sprite and video. Voice belongs to neither: the Audio page publishes voice
lines, event audio and dialog lifecycle hooks as
`lang/<LANG>/audio/conv/<key>.json` sidecars that the page merges when it
opens a conversation, so they appear once Audio is built and survive any later
Story rebuild.

## Primary generated outputs

`webui/data/manifest.json`, `webui/data/lang/<LANG>/index.json`, `conv/*.json`,
`mission/*.json`, and, in media mode, `webui/data/assets/story_media.json`.
Story's own `conv/*.json` never carries voice. Controls and rendering rules are
in the header comment of `webui/app.js`.

`webui/src/features/story/branches.js` renders the compact branch overview
from the selected conversation and its existing mission publication; it adds
no builder input or new recovery pass. `render(conv, options)` returns a fresh
detached details element or `null`, so switching to a conversation without
branches clears the previous overview with the conversation fragment. Local
line and content links use the same `line`/`cid` Story destinations as Character
appearances, including opening collapsed branch ancestors.

## Evidence boundary

- Case-insensitive resource matching is accepted only when unique; authored
  spelling remains visible.
- A cutscene definition is "unused" only after a complete, current carrier
  census finds no exact or uniquely folded reference. Failed, stale, missing,
  or ambiguous scans remain unresolved.
- Timeline scheduling proves authored placement, not runtime activation.
- Manual order and option placement are visibly manual and never promoted to
  source evidence.
- The branch overview distinguishes exact `sceneGraphLinks` routes, authored
  SNS `next` content references, stored option groups without a route witness,
  and manual presentation or placement. A manual label on an otherwise direct
  route retains both annotations. Local line paths, return loops and explicit
  terminal outcomes remain local; a missing destination stays unresolved.
  Mission `sourceBackedSceneEdges` are displayed with their stored evidence
  kind: authored menu availability is not execution order. Weak/fallback
  scene-order evidence and unresolved scene connections stay visible beside
  the overview. The panel never turns file order or native address order into
  a canonical playthrough; source file/node diagnostics remain behind debug.
- A `DialogOptionTable` group number filling a missing `DialogTextTable` line
  number remains a placement fallback when no DialogTree or Timeline route
  witnesses it. In `dlg_f1m15_1`, group `5` currently appears after line
  `dlg_f1m15_1_004` by this sparse-gap rule; the source graph has only row-key
  membership and the generated fallback anchor, with no branch edge. The
  conversation is absent from `DialogIdTable`, so its two options remain
  inferred rather than receiving a manual override from dialogue wording.
  Current native claims validate a Timeline option-index path in general, but
  this scene has no Timeline carrier. The available capture profiles do not
  record this scene, group, and chosen option together; a live capture is not
  ready for this gap.
- `sns_emoji_*` stays inline without a preview. Other SNS images and stickers
  keep natural proportions with bounded hover/modal previews.
- Debug mode owns raw sources, Timeline diagnostics, and order-edit tools;
  issue and recovery-method filters remain available normally.

## Focused refresh commands

```bat
python -m scripts.webui.story.refresh_evidence
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
```

When Timeline and Table inputs are unchanged, the maintained edit-loop command
may use `--timeline-recovery never --reuse-reference`. Never reuse references
after an installed-game refresh. Run the full canonical build only at the
coherent batch boundary described in `AGENTS.md`.

## Highest-value remaining gaps

- Recover more within-mission scene order from direct control-flow evidence.
- Reduce unresolved option placement without weakening manual/generated labels.
- Keep definition-only media, authored placement, and observed playback separate.

See [`story_recovery.md`](story_recovery.md) for the durable Story
reconstruction model and reports.
