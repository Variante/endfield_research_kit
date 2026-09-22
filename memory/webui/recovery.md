# Recovery page recovery

## Purpose

Recovery is the one page whose subject is the research itself: how far the
installed game data is understood, broken down by the four levels and the lanes
that [`../game_data/README.md`](../game_data/README.md) defines, beside how much
data sits behind each answer.

Its reason to exist is evidence honesty. Every other page shows recovered
content; this one shows the shape of what has *not* been recovered with the same
prominence, and it keeps "framed and named" strictly apart from "understood". A
100% named byte share is a level-2/3 result and the page must never let it read
as level 4.

## Inputs and recovery flow

The builder derives from generated reports and one tracked index; it never
re-decodes bytes and never reads the installed client.

1. `memory/game_data/README.md` supplies the four level definitions, the lane
   grouping, and every documented topic's level. Parsed, not copied, so the
   page follows the directory instead of drifting from it.
2. `reports/animestudio/vfs_payload_profile_files_latest.jsonl.gz` supplies the
   complete installed-corpus inventory, aggregated by `blockTypeName` into
   files, payload bytes, and the largest `pathFamily` values.
3. `reports/game_data/jsondata_schema_coverage_declared.json` supplies per-family
   named-byte coverage for the JsonData block.
4. `reports/assets/monobehaviour_field_semantics.json` supplies the class,
   object, field-path and field-classification census, the filled reference
   fields and how many of them resolve to a container, and the not-understood
   set described below.
5. `reports/assets/monobehaviour_table_keys.json` supplies the table-key join
   summary and its own evidence boundary, which is republished verbatim, plus
   the classes whose string fields join a Table's key set.
6. `scripts/webui/recovery/recovery_declarations.json` supplies what no report
   carries: the lane list, the block-type-to-lane reading, the recorded
   eliminations, and the level caveats. Each entry carries its own `_why`.

Every input is fail-closed. A missing file, an unexpected `schema` token, a
malformed profile row, a level table that is not 1..4, an unparsable topic row,
and above all a **VFS block type with no declared lane** all abort the build.
That last gate is the one that matters after a client update: a new block type
must be classified deliberately, not silently dropped out of the totals.

## Primary generated outputs

```text
webui/data/recovery/index.json
```

One compact payload. Its top-level sections are `levels`, `lanes`, `corpus`,
`jsonData`, `monoBehaviour`, `tableKeys`, `openItems`, `caveats`, and `sources`.
Every figure-bearing node carries `evidence: "measured"` or
`evidence: "declared"`; a declared node also carries the reason it cannot be
measured. The frontend renders the two differently and must keep doing so.

## Evidence boundary

- **Measured** means read out of one of the reports or the tracked lane index
  named in `sources`. Nothing is computed from installed bytes here.
- A lane's **volume** is measured. A lane's **level strip counts documented
  topic files**, not bytes. A level cell being filled means that lane has at
  least one recorded conclusion at that level -- never that the lane's data is
  understood at that level.
- **Named bytes are not understood bytes.** The JsonData section publishes
  `level: 3` and states the method verbatim. A family at 100% may still hold
  fields whose meaning is unproven.
- The MonoBehaviour **no-class-specific-signal** set -- the honest
  not-understood set -- is measured from the two MonoBehaviour reports, and is
  published as a **range, never one bound alone**. A game-specific class is in
  it when, after setting aside the four universal engine fields Unity writes on
  every object, it has no qualifying reference field, no path-shaped string
  field, and no string field whose values join an exported Table's key set. The
  two bounds differ only in what a reference has to do to qualify:
  - `floor` accepts any reference field that is ever filled;
  - `strict` accepts one only when it lands on a name -- a named target class,
    or an exported asset type rather than another anonymous MonoBehaviour.

  A filled reference is evidence that the field *is* a reference and no evidence
  about what it means, which is why the bounds are far apart; the classes
  between them, whose only signal resolves to nothing named, are published too.
  `strict` is the headline because it is what the evidence supports, and leading
  with `floor` would be the flattering half. Three further details decide the
  result and must not be relaxed: the universal fields are excluded **before**
  anything is counted, or nearly every class looks referenced; the
  public-namespace exclusion is a **prefix** list, so game namespaces such as
  `ScriptAnimation.*` stay in while `UnityEngine.*`/`Cinemachine*` drop out; and
  the one class whose script could not be named is **included**, because an
  unnamed class is game data, not engine code. The counts move as recovery
  progresses, so they live in the generated payload and the tests assert the
  predicates' components rather than literal totals.
- `corpus.levelDepth` splits the whole corpus four ways so it can be drawn as
  one segmented bar and then broken down level by level. A block type counts at
  level N when its lane has a documented conclusion at level N, plus the levels
  of any lane the index heads "all lanes" -- declared once, because the heading
  is prose. This is the **depth of the lane's documentation**, not per-byte
  understanding: one conclusion does not cover a lane's whole payload, and the
  published `basis` string plus the page's section prose say so. Each level's
  bar is drawn against the full corpus with the undocumented part visible, so a
  short bar cannot read as a small corpus.
- `openItems` are **recorded eliminations**, not a queue. What the engine's own
  HIRC parser skips, and what only a runtime consumer could answer, are not
  reachable from installed data at all; presenting them as open work would
  invite the same dead ends.
- Reports under `reports/` are local-only. The page shows each source's size and
  mtime so a stale or absent input is visible rather than implied, and it
  displays an explicit missing state when `index.json` has not been built.

## Focused refresh

```bat
python -m scripts.webui.recovery.build_recovery
python -m scripts.webui.recovery.build_recovery --print-summary
python -m unittest scripts.tests.test_build_recovery
```

The page is reached at `#recovery` (tab `Progress` / `进度`). It is not part of
`export.bat`: its inputs are focused recovery reports with their own refresh
commands, so rebuilding it after an export would publish whatever those reports
last held.

## Highest-value remaining gaps

- No level-4 measurement exists. Depth is currently shown through documented
  topics; a real per-lane "meaning proven" figure needs a report that records
  consumer-proven conclusions per family.
- Lanes with data but no topic file here (`text`, `code`, `provenance`) show a
  documentation gap, not a data gap. `IFixPatch` and `DynamicStreaming` remain
  the two blocks with no owning topic.
- The block-type-to-lane map is a declaration that must be revisited whenever
  the VFS enum changes; the builder fails closed to force that.
- Neither not-understood bound is a ceiling. Even `strict` credits a reference
  that lands on a named type without asking what the relation means, so the real
  figure is at least as high. Narrowing the range needs per-class consumer
  evidence that no report records yet.
- `corpus.levelDepth` is the coarsest honest depth measure available: it is
  per-lane, so one level-4 conclusion credits its lane's entire payload. A
  per-family depth report would replace it.
