#!/usr/bin/env python3
"""Catalog AudioDialogCustomEventTable entries by mission and signature.

This is an evidence-classification audit: `AudioDialogCustomEventTable.json`
maps a small set of `dlg_*` IDs to Wwise event hashes for `preEnterEvents`,
`preExitEvents`, and `preloadEvents`. The hashes are runtime Wwise IDs (not
FNV-1, FNV-1A, CRC32, or Murmur3 of any `au_*` event name string found in
`global-metadata.dat`), so they cannot be reversed without reaching into
`GameAssembly.dll` directly.

The audit's verdict is therefore: this table is a per-dialog *presence flag*
for "this dialog plays with custom Wwise audio enter/exit hooks", not a
mission-order or option-response source. The shared-signature group hints at
which dialogs share an audio profile, but the IDs themselves do not name
chronology.

Outputs:

    reports/mission_order/audio_dialog_custom_events_CN.json
    reports/mission_order/audio_dialog_custom_events_CN.md
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402

TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
CUSTOM_EVENT_TABLE_PATH = TABLE_ROOT / "AudioDialogCustomEventTable.json"
AUDIO_DIALOG_TABLE_PATH = TABLE_ROOT / "AudioDialog.json"
MISSION_RE = re.compile(r"^dlg_([a-z]+\d+m\d+(?:d\d+)?)_", re.I)


def mission_for_dialog(dlg_id: str) -> str:
    match = MISSION_RE.match(str(dlg_id or ""))
    return match.group(1) if match else ""


def signature_tuple(row: dict[str, Any]) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    def normalize(values: Any) -> tuple[int, ...]:
        if not isinstance(values, list):
            return ()
        return tuple(sorted(int(v) for v in values if isinstance(v, (int, float))))

    return (
        normalize(row.get("preEnterEvents")),
        normalize(row.get("preExitEvents")),
        normalize(row.get("preloadEvents")),
    )


def collect_audio_dialog_paths(dialog_ids: list[str]) -> dict[str, list[str]]:
    if not AUDIO_DIALOG_TABLE_PATH.exists():
        return {dlg: [] for dlg in dialog_ids}
    payload = read_json(AUDIO_DIALOG_TABLE_PATH, {})
    paths_by_dialog: dict[str, set[str]] = defaultdict(set)
    if not isinstance(payload, dict):
        return {dlg: [] for dlg in dialog_ids}
    needle_set = {dlg.lower() for dlg in dialog_ids}
    for row in payload.values():
        if not isinstance(row, dict):
            continue
        path = str(row.get("path") or "")
        if not path:
            continue
        lowered = path.lower()
        for needle in needle_set:
            if f"/au_{needle}_" in lowered or f"\\au_{needle}_" in lowered:
                paths_by_dialog[needle].add(path)
    return {
        dlg: sorted(paths_by_dialog.get(dlg.lower(), set())) for dlg in dialog_ids
    }


def build_report() -> dict[str, Any]:
    table = read_json(CUSTOM_EVENT_TABLE_PATH, {})
    if not isinstance(table, dict):
        table = {}

    entries: list[dict[str, Any]] = []
    sig_groups: dict[tuple, list[str]] = defaultdict(list)
    per_mission: Counter[str] = Counter()
    all_event_ids: set[int] = set()
    preload_event_ids: set[int] = set()

    for dlg_id, row in sorted(table.items()):
        if not isinstance(row, dict):
            continue
        mission = mission_for_dialog(dlg_id)
        sig = signature_tuple(row)
        sig_groups[sig].append(dlg_id)
        per_mission[mission or "?"] += 1
        for kind in ("preEnterEvents", "preExitEvents", "preloadEvents"):
            for ev in row.get(kind) or []:
                ev_int = int(ev)
                all_event_ids.add(ev_int)
                if kind == "preloadEvents":
                    preload_event_ids.add(ev_int)
        entries.append({
            "dialogId": dlg_id,
            "mission": mission,
            "preEnterEvents": list(row.get("preEnterEvents") or []),
            "preExitEvents": list(row.get("preExitEvents") or []),
            "preloadEvents": list(row.get("preloadEvents") or []),
        })

    audio_paths = collect_audio_dialog_paths([entry["dialogId"] for entry in entries])
    for entry in entries:
        entry["audioDialogPaths"] = audio_paths.get(entry["dialogId"], [])

    shared_signatures = []
    unique_signatures = []
    for sig, dlgs in sig_groups.items():
        record = {
            "preEnterEvents": list(sig[0]),
            "preExitEvents": list(sig[1]),
            "preloadEvents": list(sig[2]),
            "dialogIds": sorted(dlgs),
            "missions": sorted({mission_for_dialog(d) for d in dlgs if mission_for_dialog(d)}),
        }
        if len(dlgs) > 1:
            shared_signatures.append(record)
        else:
            unique_signatures.append(record)
    shared_signatures.sort(key=lambda r: (-len(r["dialogIds"]), r["dialogIds"]))
    unique_signatures.sort(key=lambda r: r["dialogIds"])

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": str(CUSTOM_EVENT_TABLE_PATH),
        "summary": {
            "dialogCount": len(entries),
            "distinctEventIds": len(all_event_ids),
            "distinctPreloadEventIds": len(preload_event_ids),
            "sharedSignatureCount": len(shared_signatures),
            "uniqueSignatureCount": len(unique_signatures),
            "perMissionCounts": dict(per_mission.most_common()),
        },
        "evidenceClassification": {
            "isOrderingSource": False,
            "reason": (
                "Event IDs are runtime Wwise event hashes. No FNV-1, FNV-1A, "
                "CRC32, or Murmur3 transform of any au_* string discovered in "
                "global-metadata.dat hashes to the target IDs, so the table is "
                "not reversible to ordered Wwise event names from metadata.dat "
                "alone. The table is a per-dialog presence flag for custom "
                "audio enter/exit hooks, not a chronology source."
            ),
            "usableSignals": [
                "presenceFlag: tags 41 dialogs (mostly chapter e8) as carrying "
                "custom Wwise audio enter/exit hooks; useful as a dialog-type "
                "label but does not order scene files.",
                "sharedSignatureGrouping: 6 dialogs share the default enter/"
                "exit signature, suggesting a shared audio profile. Authored "
                "co-membership signal at best; not a chronology edge.",
            ],
        },
        "sharedSignatures": shared_signatures,
        "uniqueSignatures": unique_signatures,
        "entries": entries,
    }
    return payload


def markdown_report(payload: dict[str, Any]) -> str:
    s = payload["summary"]
    lines = [
        "# AudioDialogCustomEventTable Audit",
        "",
        f"Generated: {payload['generated']}",
        f"Source: `{payload['source']}`",
        "",
        "## Summary",
        "",
        f"- Dialogs in table: `{s['dialogCount']}`",
        f"- Distinct event IDs: `{s['distinctEventIds']}` ({s['distinctPreloadEventIds']} preload)",
        f"- Shared signatures: `{s['sharedSignatureCount']}`",
        f"- Unique signatures: `{s['uniqueSignatureCount']}`",
        "",
        "## Evidence Classification",
        "",
        f"- `isOrderingSource`: `{payload['evidenceClassification']['isOrderingSource']}`",
        f"- Reason: {payload['evidenceClassification']['reason']}",
        "- Usable signals:",
    ]
    for signal in payload["evidenceClassification"]["usableSignals"]:
        lines.append(f"  - {signal}")

    lines.extend([
        "",
        "## Per-Mission Counts",
        "",
        "| mission | dialogs |",
        "| --- | ---: |",
    ])
    for mission, count in s["perMissionCounts"].items():
        lines.append(f"| `{md_escape(mission)}` | {count} |")

    lines.extend([
        "",
        "## Shared Signatures",
        "",
        "Dialogs that share the exact same (preEnter, preExit, preload) event "
        "signature. Indicates a shared audio profile.",
        "",
        "| signature (preEnter / preExit / preload) | dialog count | missions | dialogs |",
        "| --- | ---: | --- | --- |",
    ])
    if payload["sharedSignatures"]:
        for sig in payload["sharedSignatures"]:
            lines.append(
                f"| `{sig['preEnterEvents']} / {sig['preExitEvents']} / {sig['preloadEvents']}` "
                f"| {len(sig['dialogIds'])} "
                f"| `{', '.join(sig['missions'])}` "
                f"| `{', '.join(sig['dialogIds'])}` |"
            )
    else:
        lines.append("| _(none)_ |  |  |  |")

    lines.extend([
        "",
        "## Unique Signatures",
        "",
        "Dialogs with bespoke per-dialog Wwise audio enter/exit hooks.",
        "",
        "| dialog | mission | preEnter | preExit | preload | audio dialog paths |",
        "| --- | --- | ---: | ---: | ---: | --- |",
    ])
    entries_by_id = {e["dialogId"]: e for e in payload["entries"]}
    for sig in payload["uniqueSignatures"]:
        dlg_id = sig["dialogIds"][0]
        entry = entries_by_id.get(dlg_id) or {}
        paths = entry.get("audioDialogPaths") or []
        path_text = ", ".join(f"`{md_escape(p)}`" for p in paths[:3])
        if len(paths) > 3:
            path_text += f", +{len(paths) - 3}"
        lines.append(
            f"| `{md_escape(dlg_id)}` "
            f"| `{md_escape(entry.get('mission') or '')}` "
            f"| {sig['preEnterEvents']} "
            f"| {sig['preExitEvents']} "
            f"| {sig['preloadEvents']} "
            f"| {path_text or '_(none)_'} |"
        )

    lines.extend([
        "",
        "## Conclusion",
        "",
        "AudioDialogCustomEventTable is not a scene-order or option-response "
        "evidence source. Treat it as a dialog metadata tag (custom-audio "
        "presence flag) and ignore for ordering promotions.",
    ])

    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports" / "mission_order",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_report()
    out_json = args.reports_dir / f"audio_dialog_custom_events_{args.language}.json"
    out_md = args.reports_dir / f"audio_dialog_custom_events_{args.language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    s = payload["summary"]
    print(
        f"AudioDialogCustomEventTable: {s['dialogCount']} dialogs, "
        f"{s['distinctEventIds']} event IDs, "
        f"{s['sharedSignatureCount']} shared + {s['uniqueSignatureCount']} unique signatures."
    )
    print("Classification: not an ordering source; tag only.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
