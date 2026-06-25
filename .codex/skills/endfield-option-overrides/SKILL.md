---
name: endfield-option-overrides
description: Edit and validate Endfield WebUI-only manual option recovery overrides. Use when Codex needs to add, update, review, or verify entries in webui/overrides/options.json for known option placement gaps, unknown option positions, inferred option responses, or manual override tags in the Story WebUI.
---

# Endfield Option Overrides

Use this skill to maintain the local override file that covers known WebUI
option recovery gaps without changing the automatic recovery rules.

## Files

- Override data: `webui/overrides/options.json`
- Runtime application point: `webui/app.js`
- Story rendering tags: `webui/app.js`, `webui/app_labels.js`, `webui/style.css`
- Generated validation targets: `webui/data/lang/CN/conv/<key>.json`,
  `reports/inferred_option_anchors_CN.json`

## Rules

- Treat overrides as WebUI-only display corrections, not source evidence.
- Edit the JSON file first. Change frontend code only when the override
  format itself must evolve.
- Apply overrides only to known generated issue cases:
  `inferredOptionLayout` / unknown option position, or
  `inferredOptionResponse` / inferred following-line response.
- Do not use overrides to create new option groups, options, or line ids.
- Prefer exact stable ids: conversation key, group number, option id, and line id.
- Preserve the visible manual override tag; users must be able to see when a row
  was manually overridden.

## Override Format

Placement override:

```json
{
  "scenes": {
    "dlg_example_1": {
      "positions": {
        "after": {
          "dlg_example_1_002": ["1"]
        }
      },
      "notes": {
        "1": "Why this manual placement is accepted."
      }
    }
  }
}
```

Pre-scene placement:

```json
"positions": { "pre": ["1"] }
```

Inferred response override:

```json
"responses": {
  "option_dlg_example_1_1_001": ["dlg_example_1_003"]
}
```

## Workflow

1. Identify the target scene and group.
   - Use existing WebUI JSON, `reports/inferred_option_anchors_CN.json`, or:
     `python tools\endfield_source_graph.py story <key> --limit-lines 12`
   - For inferred responses, inspect the generated warning or run the relevant
     `scripts/story_recovery/` audit before adding a manual mapping.

2. Edit `webui/overrides/options.json`.
   - Keep notes short and factual.
   - Use string values for group numbers.
   - Validate option ids and line ids against the generated conv JSON.

3. Refresh the browser. No story rebuild is needed for runtime override edits.

4. Verify results.
   - `python -m json.tool webui\overrides\options.json`
   - Confirm the target Story scene shows the manual override tag.
   - Confirm unresolved inferred-anchor counts are expected:
     `reports/inferred_option_anchors_CN.json`
   - Run syntax checks after frontend edits:
     `node --check webui\app.js`
     `node --check webui\app_labels.js`

## Reporting Back

Mention:

- Which scene/group/option ids were overridden.
- Which line ids or placement were pinned.
- That the override is WebUI-only and visibly tagged.
- Which validation commands were run.
