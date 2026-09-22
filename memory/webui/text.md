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
3. `scripts.webui.story.source_links` and `scripts.webui.story.build`
   publish localized reference indexes and shards under
   `webui/data/lang/<LANG>/reference/`.
4. `scripts.webui.story.reference_structured_fields` declares the maintained
   renderers: one rule set per exported table stem, naming each field's display
   label and the table its value points at. The bundle builder resolves those
   references by exact row lookup and attaches the result to the row as
   `fields`.
5. The frontend renders known row shapes plus `fields`, and retains raw JSON
   for fields that have no maintained presentation.

## Evidence boundary

- A localized row proves exported table content, not that a Story, quest,
  character, or asset consumes it.
- Cross-page links require a typed source link; matching ids or text alone are
  not ownership.
- A maintained `fields` reference is resolved only when the named table (or
  `MissionRuntimeAsset`/`Level` pseudo-source) actually contains that row key.
  An absent row is published as unresolved, never dropped and never
  substituted by a similar id. A quest id resolves to a mission only through
  the literal `<mission>_q#<n>` form.
- Reference navigation is inside the Text page: a resolved reference selects
  the owning table and row. There is no deep-link contract to Story,
  Characters, or Gameplay, so a maintained field never claims one.
- Unsupported row shapes remain raw and searchable rather than being silently
  dropped. A table with structured fields but no localized text is published
  on its fields alone.

## Focused refresh

```bat
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
```

Refresh from the installed game first only when freshness validation says the
Table extraction is stale.

## Remaining gaps

- Maintained renderers currently cover the Typhoea archery/shooting-range,
  Parkour, and Foresight families. Extend them to the remaining high-value
  configuration tables; the generic renderer stays the fallback.
- The page has no cross-page deep-link target, so a maintained field cannot
  open a mission on Story or an item on Gameplay. Either add a receiving
  contract to those pages or keep such references as named provenance.
- Keep large tables responsive without truncating searchable data.
