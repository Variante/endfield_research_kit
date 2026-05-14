# Reference Page Recovery

The Reference page is the raw localized table browser at
`webui/index.html#reference`. It is deliberately separate from Story so users
can inspect localized table rows without depending on story reconstruction.

## User-Facing Page

Frontend files:

- `webui/index.html`: `#reference-view`, table list, detail pane.
- `webui/reference.js`: manifest loading, table catalog loading, table detail
  loading, search, and source filtering.
- `webui/app_labels.js`: shared UI labels.
- `webui/style.css`: shared split-pane layout and reference styling.

Main controls:

- table/text search
- source selector
- table list
- detail rows for the selected table

## Builder

The Reference data is built by the same story builder:

```bat
python scripts\story_builder\build.py --languages CN --default-language CN
```

Reference output is regenerated with Story output so localized text and
conversation reconstruction stay in sync.

## Inputs

Primary localized inputs:

```text
export_full/structured/StreamingAssets/Table/I18nTextTable_*.json
export_full/structured/StreamingAssets/Table/TextTable.json
```

The builder also reads other structured table files under:

```text
export_full/structured/StreamingAssets/Table/
export_full/structured/Persistent/
```

when those rows can be represented as localized reference data.

## Outputs

For the default CN build:

```text
webui/data/lang/CN/reference/index.json
webui/data/lang/CN/reference/<source>/<table>.json
```

`reference/index.json` is the catalog used by `reference.js`. Individual table
JSON files are loaded on demand when a table is selected.

## Recovery Behavior

Reference recovery keeps rows close to the exported source tables. It should
avoid story-specific interpretation except for resolving localized display text
where possible. This makes Reference useful for checking:

- raw table coverage
- untranslated or missing localized rows
- row ids and text ids used by Story
- source/table provenance for a displayed string

If a table belongs in Reference but should not create a Story conversation, keep
it in `reference/` only. The lean Story profile depends on this separation.

## Verification

After rebuilding:

```bat
python scripts\story_builder\build.py --languages CN --default-language CN
python serve.py
```

Check:

- `webui/data/lang/CN/reference/index.json` exists.
- `webui/data/lang/CN/reference/` has per-source table JSON files.
- the Reference tab loads the table count.
- selecting a table lazy-loads rows.
- search can find both table names and row text.
