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

6. The Story page additionally reads `webui/data/mission_pipeline/index.json`
   for `storyCoverage.storyTriggerManifest`, which is published by the
   standalone Mission Pipeline workflow rather than by a Story builder. Its
   absence is a degraded trigger state, not a failed build.

Primary outputs are `webui/data/manifest.json`,
`webui/data/lang/<LANG>/index.json`, `conv/*.json` and `mission/*.json`.

The page has two export modes. `export.bat story` is text only: tables,
JsonData and the Story Unity classes, with no image, video or audio extracted
or built, and the page renders text when the media inputs are absent.
`export.bat story-media` adds the media: the `story_media` task
(`build_assets --publish story-media`) projects Story's inline, CG, BigLogo and
remote-comm images and its videos onto the exported Texture2D, Sprite and video
as `webui/data/assets/story_media.json`, and the Audio build attaches voice
lines to `conv/*.json`. That rebuilds the Audio page too, because the voice
links come from its one builder. A text-only Story rebuild drops those links
until Audio runs again.

## Evidence boundary

- Case-insensitive resource matching is accepted only when unique; authored
  spelling remains visible.
- A cutscene definition is “unused” only after a complete, current carrier
  census finds no exact or uniquely folded reference. Failed, stale, missing,
  or ambiguous scans remain unresolved.
- Timeline scheduling proves authored placement, not runtime activation.
- Manual order and option placement are visibly manual and never promoted to
  source evidence.
- `sns_emoji_*` stays inline without a preview. Other SNS images and stickers
  keep natural proportions with bounded hover/modal previews.
- Debug mode owns raw sources, Timeline diagnostics, and order-edit tools;
  issue and recovery-method filters remain available normally.

## Focused refresh

```bat
python -m scripts.webui.story.refresh_evidence
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
```

When Timeline and Table inputs are unchanged, the maintained edit-loop command
may use `--timeline-recovery never --reuse-reference`. Never reuse references
after an installed-game refresh. Run the full canonical build only at the
coherent batch boundary described in `AGENTS.md`.

## Remaining gaps

- Recover more within-mission scene order from direct control-flow evidence.
- Reduce unresolved option placement without weakening manual/generated labels.
- Keep definition-only media, authored placement, and observed playback separate.

See [`story_recovery.md`](story_recovery.md) for the durable
Story reconstruction model and reports.
