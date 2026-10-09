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
   publish localized reference indexes and shards.
4. [`reference_structured_fields`](../../scripts/webui/story/reference_structured_fields.py)
   declares the maintained renderers: one rule set per exported table stem,
   naming each field's display label and the table its value points at. The
   bundle builder resolves those references by exact row lookup and attaches
   the result to the row as `fields`.
5. The frontend renders known row shapes plus `fields`, and retains raw JSON
   for fields that have no maintained presentation.
6. [`reference_activity_guides`](../../scripts/webui/story/reference_activity_guides.py)
   projects achievement tiers and plating requirements, activity prerequisites,
   authored stages/tasks/milestones, dungeon references and fixed reward items
   into `guide.sections`. The reference bundle publishes these rows even when
   they contain no localized text. The same row navigation, search and shared
   pagination cover guides and generic rows.

## Primary generated outputs

`webui/data/lang/<LANG>/reference/**`. Row rendering and in-page reference
navigation are in the header comment of
`webui/src/features/reference/index.js`.

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
- Reference navigation stays inside the Text page. There is no deep-link
  contract to Story, Characters, or Gameplay, so a maintained field never
  claims one.
- Unsupported row shapes remain raw and searchable rather than being silently
  dropped. A table with structured fields but no localized text is published
  on its fields alone.
- Guides describe stored configuration, not live unlocks, current event
  availability, condition execution, or player progress. Achievement tiers and
  each nested activity stage keep their source paths and record boundaries;
  display order is not a prerequisite chain.
- Reward expansion follows the exact `RewardTable` key and its `itemBundles`
  item IDs. It shows quantities and absent item rows explicitly. A nonempty
  `probItemBundles` is a separately labeled random-reward count, never a fixed
  item grant. Reward rows have their own guide, making reward links navigable
  even without localized text.
- Stage condition sidecars link only when their exact row key and each stored
  `stageId` agree. A task's explicit completion condition IDs link to the
  completion-condition table; unlock IDs with no proved target remain labeled
  unresolved. Condition type/comparison codes and typed parameter views are
  available in a compact disclosure, without inventing predicate meanings.
- Authored time ranges remain their stored strings and indexed ranges. No
  timezone, regional selection, current availability or scheduling semantics
  are inferred from them.
- The shared pager bounds rendered rows while all loaded guide fields and
  localized text remain searchable. Following a field reference selects the
  target's page and keeps the requested row visible under the existing search.
- The raw pane reads a bounded prefix, never parses incomplete JSON, and offers
  the complete original file as a download. Large/deep previews keep source
  formatting; row and within-row text pagination bound DOM work without dropping
  loaded search results. Size guards and bounded caches live in
  `webui/src/features/reference/files.js`; these are browser limits, not evidence
  of missing source rows.

## Focused refresh commands

```bat
python -m scripts.webui.story.source_links
python -m scripts.webui.story.build --languages CN --default-language CN
```

Refresh from the installed game first only when freshness validation says the
Table extraction is stale.

## Highest-value remaining gaps

- Extend maintained renderers (currently the families declared in
  `reference_structured_fields`) to the remaining high-value configuration
  tables; the generic renderer stays the fallback.
- The page has no cross-page deep-link target, so a maintained field cannot
  open a mission on Story or an item on Gameplay. Either add a receiving
  contract to those pages or keep such references as named provenance.
- Complete condition semantics and activity families outside the maintained
  guide registry still require explicit source-backed rules; generic text and
  raw-file access remain available for those tables.
