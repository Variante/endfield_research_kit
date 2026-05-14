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

Inline image behavior:

- SNS emoji images such as `sns_emoji_*` are treated as regular inline emoji.
  They do not open hover popovers or the full-screen modal.
- EnvTalk emoji-only rows such as `envEmoji_common_adaptationwork` and
  `envEmoji_common_dislike` render their line-level `emoji` fields from
  the Unity emoji prefab aliases and recovered RectTransform layer data in
  `story_media.json`. The WebUI also plays recovered `AnimationClip` enter
  curves for the background alpha flicker and body squash/stretch when the
  row scrolls into view, with hover/focus replay for verification.
- Non-emoji SNS media such as `sns_image_*`, `sns_sticker_*`,
  `deco_sns_tweet_decorate_*`, `bg_sns_tweet_decorate_*`, and related
  `cg_image_*` assets render with normal image proportions instead of the
  compact emoji treatment.
- Hover popovers and the modal preview should stay inside their visible border
  and within the viewport.

EnvTalk emoji runtime evidence:

- `HeadLabelCtrl.ShowEnvTalk` loads `UIConst.EMOJI_PREFAB_PATH` for
  `envTalkSingleData.emojiId`; IL2CPP supplies the head-label host types, but
  the visible emoji composition comes from
  `Assets/Beyond/DynamicAssets/Gameplay/UI/Prefabs/Emoji/%s.prefab`.
- The extracted clips for `emoji_adaptationwork`, `emoji_newdislike`, and
  `emoji_newworkhard` include matching `*in` / `*out` animations. Static Story
  rows use the `*in` curves and hold the final frame; `*out` is reserved for a
  future UI hide/removal event.

Narrative video behavior:

- The Story page selects the best playable active-gender/source variant for
  each distinct narrative video. Hidden duplicate files such as alternate
  sources, raw `.usm` exports, or inactive gender variants should not be
  counted as additional user-facing videos.

## Builder

Primary command:

```bat
python scripts\webui\build_story.py --languages CN --default-language CN
```

`export.bat` runs this command after export freshness verification,
DialogIdTable recovery, story source-link rebuilding, and the Updates feed.

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
scripts/recover_dialog_id_registry.py
scripts/recover_timeline_line_orders.py
scripts/recover_mission_timelines.py
scripts/scene_order_gap_shared.py
scripts/webui/build_story_reports.py
```

Prebuilt evidence inputs used by the builder:

```text
export_full/recovered/dialog_id_table_index.json
export_full/recovered/story_source_links.json
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

Rendered inline media is resolved from the asset index at browser time. The
frontend classifies SNS emoji separately from non-emoji SNS media so phone chat
emoji stays inline while SNS stickers/photos keep their normal image shape.

The page should surface recovery uncertainty instead of hiding it. When ordering
or option placement is incomplete, keep the warning/issue metadata in the
generated payload and expose it through the existing Story issue filter and
conversation warning area.

For Timeline-inferred option responses, the builder can use raw trunk
`clipOptionIndex` values only when every candidate response clip has a distinct
value that exactly matches the group's option indices. The first recovered case
is `dlg_c28m3_10` group 1; most remaining adjacent response layouts still carry
only default `0` values and stay marked as inferred.

The 2026-05-14 final sweep confirms only three scenes in the CN export carry
any non-zero `clipOptionIndex` on trunk lines (`dlg_c28m1_2` 2/16, `dlg_c28m3_10`
4/25, `dlg_c28m3_23` 2/11), and none cover all responses in a group, so the
exact-match rule already captures every source-backed case. The remaining 14
`inferredOptionResponse` scenes (`dlg_c13m2_20`, `dlg_c17m2_1`, `dlg_c17m3_17`,
`dlg_c27m5_4`, `dlg_c28m3_23`, `dlg_e1m10_5`, `dlg_e1m10_7`, `dlg_e2m5_2`,
`dlg_e4m1_4`, `dlg_e4m1d5_6`, `dlg_e6m1_10`, `dlg_e6m3_14`, `dlg_e6m4_14`,
`dlg_e9m2_14`) all have zero Runtime Jump clips, blank `trunkId`/`dialogId` on
their DialogOptionPlayableAsset entries, and only a runtime `logicId` hook with
no matching lookup table in the export — the per-option response branch is not
in the source data. Of the 19 `inferredOptionLayout` `noTreeReference` scenes,
18 have no dialog timeline data at all and the lone exception (`dlg_e2m6_11`)
hosts a cross-scene option clip pointing at `dlg_e2m6_19`'s option ids, which
the builder already labels with `position=pre`. No further source signals are
available; do not promote any of these to source-backed.

The `inferred_option_anchors_CN.md` report lists ~97 scenes where no
DialogTree / scene-link / dialog Timeline source names the option group's
anchor and the builder falls back to `lineNumber` / `sparseGap` / `lastLine`
ordinal heuristics. These remain genuinely inferred — do NOT promote them
to source-backed. Empirical cross-check against tree-authored scenes shows
the `option_<scene>_<g>_<n>` key encoding is closer to a trunk index than a
flat DialogTextTable line index, and 73% of registered tree-authored
option groups disagree with the `g = flat line index` rule (e.g.
`dlg_a1m10_1` tree anchors group 2 at `_003`, group 3 at `_007`, not
`_002` and `_003`). The runtime trunk → flat mapping that converts the
registry's per-trunk line ids to flat DialogTextTable rows is not in the
exported source data; recovering the correct anchor for these unregistered
or no-tree scenes would require additional runtime evidence. The 97
inferred scenes also have zero matching `au_dlg_<scene>_*.wem` paths in
`AudioDialog.json`, which is itself a signal that the runtime may never
present them through the standard dialog loader.

LevelScript story/hash singleton cases are exposed as diagnostics, not scene
ordering. Current source-backed hash-terminal evidence uses terminal records
with `code=0x0e34`, `kind=0x00`, and `nextId=-1`; examples include
`dlg_e2m6_11 -> #e2e0953a`, `dlg_c17m2_1 -> #e2e0953a`, and
`dlg_e2m5_2 -> #43792b8d`. Treat these as terminal trigger/event-argument
nodes unless a separate source later links the hash to another story scene.
The 2026-05-13 CN mission timeline catalog has `855` such terminals across
`582` unique hashes, all matching `story->hash plain 0x0e34 0x00 nextId=-1`;
`#e2e0953a` is the broad shared sentinel (`259` scenes across `88` missions).

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
- `test_sns_emojicomment` keeps `sns_emoji_*` inline with no popup/modal.
- `test_sns_sticker` renders `sns_sticker_*` with normal image proportions.
- `sns_topic_map02_lv005_12002` renders `sns_image_*` as bounded previews and
  keeps the preview/modal image inside its frame.
