# Text page recovery

## Purpose

Text exposes localized exported Table JSON as searchable rendered rows with raw
source access. It shares extraction and localization infrastructure with Story
but does not imply narrative ownership.

## Inputs and recovery flow

1. AnimeStudio's focused structured dump extracts Table blocks from the
   effective installed-data overlay.
2. Story reference discovery classifies supported tables and preserves source
   metadata.
3. `scripts.story_builder.source_links` and `scripts.story_builder.build`
   publish localized reference indexes and shards under
   `webui/data/lang/<LANG>/reference/`.
4. The frontend renders known row shapes and retains raw JSON for fields that
   have no maintained presentation.

## Evidence boundary

- A localized row proves exported table content, not that a Story, quest,
  character, or asset consumes it.
- Cross-page links require a typed source link; matching ids or text alone are
  not ownership.
- Unsupported row shapes remain raw and searchable rather than being silently
  dropped.

## Focused refresh

```bat
python -m scripts.story_builder.source_links
python -m scripts.story_builder.build --languages CN --default-language CN
```

Refresh from the installed game first only when freshness validation says the
Table extraction is stale.

## Remaining gaps

- Add maintained renderers for high-value table shapes.
- Improve typed cross-page links while preserving source provenance.
- Keep large tables responsive without truncating searchable data.
