# Updates Page Recovery

The Updates page is the original installed game-data change browser at
`webui/index.html#updates`. It must not report WebUI edits or local generated
rebuild noise as game updates.

## User-Facing Page

Frontend files:

- `webui/index.html`: `#updates-view`, filters, summary stats, detail pane.
- `webui/updates.js`: feed loading, filtering, sorting, and detail rendering.
- `webui/app_labels.js`: shared UI labels.
- `webui/style.css`: update summary and detail styling.

Main controls:

- path/extension search
- status filter
- category filter
- extension filter
- sort selector
- summary cards
- selected change detail

## Builder

Primary command:

```bat
python scripts\webui\build_updates.py
```

Reset baseline only when intentionally treating the current installed game as
the new no-change state:

```bat
python scripts\webui\build_updates.py --reset-baseline
```

`export.bat` runs `build_updates.py` before Story and Assets.

## Inputs

The default tracked source is the installed game data tree:

```text
D:\Program Files\Endfield Game\Endfield_Data
```

Tracker state:

```text
.game-data-tracker/
```

Exported asset diff source:

```text
export_full/
```

The exported asset diff is subordinate to the original game-data tracker. Asset
changes are reported only when the installed `Endfield_Data` tracker reports a
real game-data change. If no original game-data change is detected, exported
asset differences are treated as local rebuild noise and baselined silently.

Do not point this builder at:

```text
webui/
export_full/
reports/
memory/
scratch/
tmp/
```

as the primary game-data tracker root.

## Outputs

Browser feed:

```text
webui/data/updates/latest.json
```

Generated report outputs:

```text
reports/game-data-change-summary.json
reports/game-data-change-summary.md
.game-data-tracker/history/
```

On first run, when no baseline exists, the builder writes baseline summaries
inside `.game-data-tracker/` and emits an empty browser feed.

## Recovery Behavior

The Updates page is not a general repo diff viewer. It answers one question:
what changed in the original installed game data since the last tracked
baseline?

The feed includes:

- added, modified, and deleted original game-data files
- size and line deltas where meaningful
- categories and extensions for filtering
- asset-level image/model/video entries derived from `export_full/`, gated by a
  real original game-data change

This design prevents rebuild output, WebUI edits, report rewrites, or local
scratch work from appearing as game updates.

## Verification

After rebuilding:

```bat
python scripts\webui\build_updates.py
python serve.py
```

Check:

- `webui/data/updates/latest.json` exists.
- the payload's tracked root is the installed `Endfield_Data` tree.
- a first baseline run reports no existing files as new game changes.
- WebUI-only edits do not appear in the Updates tab.
- asset-level entries appear only when the game-data tracker reports real
  changes.
