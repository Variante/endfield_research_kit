# Story page recovery

## Purpose

Story presents localized conversations, mission grouping, options, inline
media, and typed recovery evidence. It combines sources without flattening
authored structure, Timeline placement, runtime links, manual order, or
inference into one confidence class.

## Inputs and recovery flow

1. AnimeStudio exports Table/JsonData plus broad `TextAsset`, `MonoBehaviour`,
   and `PlayableDirector` evidence from both installed roots.
2. `scripts.story_builder.refresh_evidence` refreshes source evidence and
   fail-closed native-gated reports.
3. `scripts.story_builder.source_links` joins mission/runtime references to
   Story keys.
4. `scripts.story_builder.build` localizes, groups, orders, and publishes
   conversations and references.
5. Manual inputs in `webui/overrides/story_order.json`, `options.json`, and
   `narrative_videos.json` are applied without being overwritten.

Primary outputs are `webui/data/manifest.json`,
`webui/data/lang/<LANG>/index.json`, `conv/*.json`, `mission/*.json`, and
`webui/data/assets/story_media.json`.

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
python -m scripts.story_builder.refresh_evidence
python -m scripts.story_builder.source_links
python -m scripts.story_builder.build --languages CN --default-language CN
```

When Timeline and Table inputs are unchanged, the maintained edit-loop command
may use `--timeline-recovery never --reuse-reference`. Never reuse references
after an installed-game refresh. Run the full canonical build only at the
coherent batch boundary described in `AGENTS.md`.

## Remaining gaps

- Recover more within-mission scene order from direct control-flow evidence.
- Reduce unresolved option placement without weakening manual/generated labels.
- Keep definition-only media, authored placement, and observed playback separate.

See [`../game_story_recovery.md`](../game_story_recovery.md) for the durable
Story reconstruction model and reports.
