---
name: endfield-option-overrides
description: Edit, review, and validate Endfield WebUI manual option recovery overrides in webui/overrides/options.json. Use for known option placement gaps, pre-scene placement, inferred option responses, stale override targets, coverage audits, and visible manual-override tagging.
---

# Endfield Option Overrides

Maintain `webui/overrides/options.json` as a WebUI-only correction layer for
known automatic recovery gaps. Treat overrides as display decisions, never as
source evidence.

## Guardrails

- Edit the JSON before considering frontend changes; change code only when the
  format or application behavior must evolve.
- Override only known `inferredOptionLayout` or `inferredOptionResponse` cases.
- Never create new option groups, option IDs, or line IDs.
- Use exact conversation keys, string group numbers, option IDs, and line IDs
  verified against `webui/data/lang/CN/conv/<key>.json`.
- Keep notes short and factual and preserve the visible manual-override tag.

## Format

```json
{
  "scenes": {
    "dlg_example_1": {
      "positions": {
        "pre": ["2"],
        "after": {
          "dlg_example_1_002": ["1"]
        }
      },
      "responses": {
        "option_dlg_example_1_1_001": ["dlg_example_1_003"]
      },
      "notes": {
        "1": "Short factual reason."
      }
    }
  }
}
```

`positions.pre` places groups before the scene. `positions.after` anchors
groups after a line. `responses` maps an option ID to exact branch line IDs.

## Workflow

1. Identify the scene, group, and generated issue. Inspect the conversation
   JSON and `reports/story/build/inferred_option_anchors_CN.json`; use
   `python tools\endfield_source_graph.py story <key> --limit-lines 12` when
   graph evidence helps.
2. For response mappings, inspect the generated warning and the relevant
   focused recovery audit. Do not promote weak adjacency or default-value hints.
3. Edit `webui/overrides/options.json` surgically.
4. Refresh the browser; runtime override edits do not require a Story rebuild.
5. Validate JSON and confirm the target scene is visibly tagged:

```bat
python -m json.tool webui\overrides\options.json
```

Run the coverage audit when adding, reviewing, or checking stale targets:

```bat
python scripts\story_recovery\build_option_override_coverage_audit.py --language CN
```

The same report includes generated response candidates and flags manual paths
whose first line conflicts with the current builder evidence. These are review
diagnostics only; a candidate or conflict never promotes inferred evidence or
changes the override file.

If frontend code changed, also run:

```bat
node --check webui\app.js
node --check webui\app_labels.js
```

Keep canonical audits under `reports/story/recovery/options/`, revisitable
probes under `scratch/story/options/<task>/`, and disposable work under
`tmp/story/options/<task-or-run>/`.

Report the affected scene, group, option and line IDs; state that the change is
WebUI-only and visibly tagged; and list the validation performed.
