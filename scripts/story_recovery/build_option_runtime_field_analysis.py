#!/usr/bin/env python3
"""Interpret IL2CPP body-target evidence for option active-clip selection.

The IL2CPP catalog at `reports/option_flow_body_targets_gameassembly.json`
already maps each focused dialog/option method to its GameAssembly.dll
RVA and a small window of disassembled instructions around catalog-
target calls. This script walks that JSON and extracts the *runtime
field offsets* on option objects that the disassembly proves matter:

- `+0x18` on the option object: filtered/checked by
  `TryTriggerTrunkBindingOption` before calling `SetDialogOption`. The
  active-clip gate -- when this offset reads 0, the option is skipped.
- `+0x98` on the option object: read by
  `DialogTimelineManager._SelectIndexInTimeline` and passed as the
  `optionIndex` argument into `DialogUtils.DialogChooseOption`. The
  selected option index.
- `+0x200` on the option object: written by `DialogTimelineManager.SelectIndex`
  with the current option-set index (`[rdi+0xa0]`) before calling
  `ResetDialogOption`. Persistent state for re-entry / reset flow.

The script confirms which evidence is in the catalog output and which
field semantic is locked to which call site. It then emits a digest
report (markdown + JSON) plus a one-line summary of the next decoding
target. The current target is no longer finding a `+0x18` writer: the
body-target catalog proves `DialogChooseOption` writes the selected runtime
option index to `+0x18`. The remaining recovery target is binding authored
Timeline option rows to active runtime clips strongly enough to promote branch
edges without relying on display-only overrides.

This script is **read-only** with respect to the IL2CPP tools — it
adds an interpretation layer over their existing output. No
GameAssembly.dll disassembly is performed here; the report is built
from disassembly snippets the body-target mapper already captured.

Output:

    reports/option_flow_active_clip_field_analysis.json
    reports/option_flow_active_clip_field_analysis.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

DEFAULT_BODY_TARGETS_JSON = ROOT / "reports" / "option_flow_body_targets_gameassembly.json"
DEFAULT_CATALOG_JSON = ROOT / "reports" / "option_flow_runtime_metadata_focus.json"

OFFSET_RE = re.compile(r"\[(?:r[abcdsp][xpil]|rsi|rdi|r[89]|r1[0-5])\s*\+\s*(0x[0-9a-fA-F]+|\d+)\]")


def normalize_offset(raw: str) -> int | None:
    raw = raw.strip()
    try:
        if raw.startswith("0x"):
            return int(raw, 16)
        return int(raw)
    except ValueError:
        return None


def collect_offset_uses(call: dict[str, Any]) -> list[dict[str, Any]]:
    nearby = (call.get("argumentContext") or {}).get("nearbyInstructions") or []
    out: list[dict[str, Any]] = []
    for inst in nearby:
        text = str(inst.get("text") or "")
        match = OFFSET_RE.search(text)
        if not match:
            continue
        off = normalize_offset(match.group(1))
        if off is None:
            continue
        out.append({
            "offsetHex": f"+0x{off:x}",
            "offsetInt": off,
            "instruction": text,
            "callOffset": inst.get("offset"),
            "writes": (inst.get("write") or {}).get("register"),
        })
    return out


def caller_full_name(caller: dict[str, Any]) -> str:
    return f"{caller.get('type')}.{caller.get('method')}"


def callee_full_name(call: dict[str, Any]) -> str:
    callees = call.get("callees") or []
    if not callees:
        return ""
    c = callees[0]
    return f"{c.get('type')}.{c.get('method')}"


def build_report(body_targets_path: Path) -> dict[str, Any]:
    payload = read_json(body_targets_path, {})
    if not isinstance(payload, dict):
        return {"error": f"missing or invalid {body_targets_path}"}
    direct_edges = payload.get("directCallEdges") or []
    metadata_meta = payload.get("metadata") or {}

    edge_field_uses: list[dict[str, Any]] = []
    offset_use_index: dict[int, list[dict[str, Any]]] = defaultdict(list)

    for edge in direct_edges:
        caller = caller_full_name(edge.get("caller") or {})
        callee = callee_full_name(edge)
        offset_uses = collect_offset_uses(edge)
        if not offset_uses:
            continue
        edge_field_uses.append({
            "caller": caller,
            "callee": callee,
            "callerVa": (edge.get("caller") or {}).get("methodPointerVa"),
            "callOffset": edge.get("offset"),
            "callTargetVa": edge.get("targetVa"),
            "offsetUses": offset_uses,
        })
        for use in offset_uses:
            offset_use_index[use["offsetInt"]].append({
                "caller": caller,
                "callee": callee,
                "instruction": use["instruction"],
            })

    # The runtime-field annotations the disassembly proves
    annotations = []
    for off_int, uses in sorted(offset_use_index.items()):
        callers = sorted({u["caller"] for u in uses})
        callees = sorted({u["callee"] for u in uses if u["callee"]})
        # focus on the most interesting offsets
        kind = "unknown"
        meaning = ""
        if off_int == 0x18:
            kind = "activeClipGate"
            meaning = (
                "Read inside `TryTriggerTrunkBindingOption` as "
                "`cmp [rax+0x18], 0` before calling `SetDialogOption`. "
                "Options with `[rax+0x18] == 0` are filtered out, so this is "
                "the runtime gate that keeps unresolved option-response "
                "candidate clips inactive in the current WebUI inference."
            )
        elif off_int == 0x98:
            kind = "selectedOptionIndex"
            meaning = (
                "Read inside `_SelectIndexInTimeline` as "
                "`mov ebx, [rax+0x98]; mov edx, ebx; call DialogChooseOption`. "
                "The optionIndex parameter passed to DialogChooseOption is "
                "literally `selectedOption.+0x98`."
            )
        elif off_int == 0x200:
            kind = "selectedIndexStore"
            meaning = (
                "Written inside `DialogTimelineManager.SelectIndex` as "
                "`mov [rax+0x200], ecx` (ecx <- this.+0xa0), then "
                "`ResetDialogOption()` is called. Persistent storage of "
                "the selected option index for the active dialog timeline."
            )
        elif off_int == 0xa0:
            kind = "managerCurrentIndex"
            meaning = (
                "Read inside `DialogTimelineManager.SelectIndex` as "
                "`mov ecx, [rdi+0xa0]` before storing into `[rax+0x200]`. "
                "DialogTimelineManager's current option index source."
            )
        elif off_int == 0x28:
            kind = "playableOptionsList"
            meaning = (
                "Read inside `DialogOptionPlayableAsset.GenPlayable` as "
                "`mov rdx, [rsi+0x28]` and passed to `InitDialogOptions`. "
                "The serialized `options` list on the playable asset."
            )
        annotations.append({
            "offset": f"+0x{off_int:x}",
            "offsetInt": off_int,
            "kind": kind,
            "meaning": meaning,
            "callerMethods": callers,
            "calleeMethods": callees,
            "useCount": len(uses),
        })

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sourceBodyTargets": str(body_targets_path),
        "metadata": metadata_meta,
        "summary": {
            "directCallEdgeCount": len(direct_edges),
            "edgesWithOffsetUses": len(edge_field_uses),
            "distinctOffsets": len(offset_use_index),
        },
        "runtimeFieldAnnotations": annotations,
        "edgeFieldUses": edge_field_uses,
        "nextDecodingTarget": (
            "The +0x18 writer is now identified: DialogChooseOption writes "
            "the selected optionIndex into a runtime option/playable object "
            "+0x18 field, while TryTriggerTrunkBindingOption and "
            "SetDialogOption gate active option clips on positive +0x18. "
            "Next, bind authored Timeline option rows to active runtime clips "
            "strongly enough to promote branch edges; candidate rows whose "
            "+0x18 evidence remains zero should stay diagnostic only."
        ),
    }


def markdown_report(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return f"# Option Flow Runtime Field Analysis\n\nError: {payload['error']}\n"
    s = payload["summary"]
    lines = [
        "# Option Flow Runtime Field Analysis",
        "",
        f"Generated: {payload['generated']}",
        f"Source: `{payload['sourceBodyTargets']}`",
        "",
        "## Summary",
        "",
        f"- Direct call edges: `{s['directCallEdgeCount']}`",
        f"- Edges with [reg+offset] memory uses: `{s['edgesWithOffsetUses']}`",
        f"- Distinct memory offsets seen: `{s['distinctOffsets']}`",
        "",
        "## Runtime Field Offsets",
        "",
        "| offset | kind | use count | callers | meaning |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for ann in payload["runtimeFieldAnnotations"]:
        callers = ", ".join(c.split(".")[-1] for c in ann["callerMethods"][:3])
        lines.append(
            f"| `{md_escape(ann['offset'])}` "
            f"| `{md_escape(ann['kind'])}` "
            f"| {ann['useCount']} "
            f"| `{md_escape(callers)}` "
            f"| {md_escape(ann['meaning'])} |"
        )

    lines.extend([
        "",
        "## Edge-Level Field Use Detail (top 10)",
        "",
    ])
    for edge in payload["edgeFieldUses"][:10]:
        lines.append(f"### `{md_escape(edge['caller'])}` -> `{md_escape(edge['callee'])}`")
        lines.append("")
        lines.append(
            f"caller VA: `{edge['callerVa']}`, call at +{edge['callOffset']}, "
            f"target VA: `{edge['callTargetVa']}`"
        )
        lines.append("")
        for use in edge["offsetUses"]:
            lines.append(
                f"- `{md_escape(use['offsetHex'])}` "
                f"(call+{use['callOffset']}): `{md_escape(use['instruction'])}`"
                + (f" writes `{md_escape(use['writes'])}`" if use.get("writes") else "")
            )
        lines.append("")

    lines.extend([
        "## Next Decoding Target",
        "",
        f"{payload['nextDecodingTarget']}",
        "",
        "Use this report as a working ledger of the runtime fields the WebUI",
        "needs to decode before promoting inferred option responses. None of",
        "this is yet promotable; it is the evidence the builder is waiting on.",
    ])
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--body-targets-json",
        type=Path,
        default=DEFAULT_BODY_TARGETS_JSON,
        help="Path to option_flow_body_targets_gameassembly.json",
    )
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_report(args.body_targets_json)
    out_json = args.reports_dir / "option_flow_active_clip_field_analysis.json"
    out_md = args.reports_dir / "option_flow_active_clip_field_analysis.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    if payload.get("error"):
        print(payload["error"], file=sys.stderr)
        return 1
    s = payload.get("summary") or {}
    print(
        f"Option flow runtime field analysis: "
        f"{s.get('edgesWithOffsetUses')} edges with offset uses, "
        f"{s.get('distinctOffsets')} distinct offsets."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
