# Story Page Recovery

The Story page is the main reconstructed dialog browser at
`webui/index.html#story`. It is backed by generated conversation indexes and
one lazy-loaded JSON file per recovered conversation.

## User-Facing Page

Frontend files:

- `webui/index.html`: `#story-view`, sidebar filters, conversation detail pane.
- `webui/app.js`: language loading, conversation loading, detail rendering.
- `webui/app_tree.js`: grouping, filtering, sorting, and virtualized list rows.
- `webui/app_labels.js`: UI labels and shared story formatting helpers.
- `webui/style.css`: shared layout plus story-specific presentation.

Main controls:

- language selector
- text search
- kind filter
- story-line/type filter
- recovery-issue filter
- sort selector
- raw/source display toggles
- inline tag display toggle
- gender variant toggle

## Builder

Primary command:

```bat
python scripts\webui\build_story.py --languages CN --default-language CN
```

`export.bat` runs this command after the export and Updates feed build.

For extra language bundles:

```bat
python scripts\webui\build_story.py --languages CN EN JP --default-language CN
```

## Inputs

The builder reads from `export_full/`, preferring organized current paths and
falling back to older paths where the code still supports them.

Primary structured table inputs:

```text
export_full/structured/StreamingAssets/Table/I18nTextTable_*.json
export_full/structured/StreamingAssets/Table/TextTable.json
export_full/structured/StreamingAssets/Table/DialogTextTable.json
export_full/structured/StreamingAssets/Table/SNSDialogTable.json
export_full/structured/StreamingAssets/Table/SNSDialogOptionTable.json
export_full/structured/StreamingAssets/Table/SNSChatTable.json
export_full/structured/StreamingAssets/Table/DialogOptionTable.json
export_full/structured/StreamingAssets/Table/DialogSummaryTable.json
export_full/structured/StreamingAssets/Table/MailSenderTable.json
export_full/structured/StreamingAssets/Table/RadioTable.json
export_full/structured/StreamingAssets/Table/RemoteCommonTable.json
export_full/structured/StreamingAssets/Table/EnvTalkTable.json
```

Recovered text and metadata inputs:

```text
export_full/recovered/AnimeStudio/main/TextAsset
export_full/recovered/AnimeStudio-net9-extracted
export_full/recovered/AnimeStudio-net9-json-assetmap
export_full/recovered/AnimeStudio-cli/*/json_by_type/TextAsset
export_full/recovered/AnimeStudio-cli/*/json_by_type/MonoBehaviour
```

Story order helpers imported by the builder:

```text
scripts/recover_timeline_line_orders.py
scripts/recover_mission_timelines.py
scripts/scene_order_gap_shared.py
scripts/webui/build_story_reports.py
```

## Outputs

For the default CN build:

```text
webui/data/manifest.json
webui/data/index.json
webui/data/actors.json
webui/data/lang/CN/index.json
webui/data/lang/CN/actors.json
webui/data/lang/CN/conv/<conversation-key>.json
webui/data/lang/CN/mission/<mission-id>.json
```

`index.json` and `actors.json` at the root are convenience copies for the
default language. Conversation detail payloads are intentionally lazy-loaded so
the first page load remains usable with large exports.

Generated diagnostics are outputs, not inputs:

```text
reports/mission_timeline_recovery_CN.json
reports/mission_timeline_recovery_CN.md
reports/scene_order_gap_report_CN.json
reports/scene_order_gap_report_CN.md
reports/inferred_option_anchors_CN.json
reports/inferred_option_anchors_CN.md
```

## Recovery Behavior

The current Story recovery combines several classes of data:

- authored dialog line tables for base text and speaker/actor references
- localized I18n tables for display text
- SNS tables for phone chat conversations and options
- radio, remote comm, ambient talk, black-screen, and text-table derived pages
- recovered AnimeStudio and timeline data for better authored order
- mission context files for lazy flow/context display
- source traces and warnings where recovery is partial

The page should surface recovery uncertainty instead of hiding it. When ordering
or option placement is incomplete, keep the warning/issue metadata in the
generated payload and expose it through the existing Story issue filter and
conversation warning area.

## Verification

After rebuilding:

```bat
python scripts\webui\build_story.py --languages CN --default-language CN
python serve.py
```

Check:

- `webui/data/manifest.json` includes `CN` and default language `CN`.
- `webui/data/lang/CN/index.json` exists and has conversation entries.
- `webui/data/lang/CN/conv/` contains one file per lazy-loaded conversation.
- `webui/data/lang/CN/mission/` contains mission context files.
- the Story tab loads, filters, opens a conversation, and shows raw/source
  traces when the raw toggle is enabled.
