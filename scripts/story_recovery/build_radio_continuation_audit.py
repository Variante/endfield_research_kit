#!/usr/bin/env python3
"""Audit radio_continueAfterDialog/Radio promotion candidates per mission.

For each `<mission>_evidence_audit.json` under `reports/mission_order/`,
walk every LevelScript file's `matchedSequence`. Whenever a
`radio_<scene>_*` key has `continueAfterDialog=true` and a `dlg_*` (or
`misc_dlg_*`) appeared earlier in the same script file, record a
(predecessor, radio) pair as a promotion candidate. Same for
`continueAfterRadio=true` paired with the prior `radio_*` entry.

The output lives under `reports/mission_order/radio_continuation_*.{json,md}`
and is purely diagnostic. The WebUI builder may choose to promote these
edges to strong evidence in a follow-up pass.

Run:

    # one mission
    python scripts/story_recovery/build_radio_continuation_audit.py --mission c17m3

    # every mission audit already on disk
    python scripts/story_recovery/build_radio_continuation_audit.py --all
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
AUDIT_DIR = ROOT / "reports" / "mission_order"
TABLE_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Table"
RADIO_TABLE_PATH = TABLE_ROOT / "RadioTable.json"


def load_radio_table() -> dict[str, Any]:
    if not RADIO_TABLE_PATH.exists():
        print(f"warning: missing {RADIO_TABLE_PATH}", file=sys.stderr)
        return {}
    return json.loads(RADIO_TABLE_PATH.read_text(encoding="utf-8"))


def family_of(key: str) -> str:
    if not key:
        return ""
    stripped = key[5:] if key.startswith("misc_") else key
    for prefix in ("dlg_", "radio_", "cutscene_", "dlgtl_", "sns_", "black_"):
        if stripped.startswith(prefix):
            return prefix.rstrip("_")
    return stripped.split("_", 1)[0]


def probe(audit_path: Path, radio_table: dict[str, Any]) -> dict[str, Any]:
    payload = json.loads(audit_path.read_text(encoding="utf-8"))
    mission = payload.get("mission") or audit_path.stem.split("_")[0]
    candidates: list[dict[str, Any]] = []
    for ls_file in payload.get("levelScriptFiles") or []:
        sequence = ls_file.get("matchedSequence") or []
        last_dialog: dict[str, Any] | None = None
        last_radio: dict[str, Any] | None = None
        for hit in sequence:
            key = hit.get("key") or ""
            family = family_of(key)
            if family == "dlg":
                last_dialog = hit
            if key.startswith("radio_") and key in radio_table:
                row = radio_table[key]
                cad = bool(row.get("continueAfterDialog"))
                car = bool(row.get("continueAfterRadio"))
                if cad and last_dialog is not None:
                    candidates.append({
                        "mission": mission,
                        "levelId": ls_file.get("levelId"),
                        "file": ls_file.get("file"),
                        "predecessor": last_dialog.get("key"),
                        "predecessorOffset": last_dialog.get("offset"),
                        "radio": key,
                        "radioOffset": hit.get("offset"),
                        "continueAfterDialog": cad,
                        "continueAfterRadio": car,
                        "match": "after-dialog",
                    })
                if car and last_radio is not None and last_radio.get("key") != key:
                    candidates.append({
                        "mission": mission,
                        "levelId": ls_file.get("levelId"),
                        "file": ls_file.get("file"),
                        "predecessor": last_radio.get("key"),
                        "predecessorOffset": last_radio.get("offset"),
                        "radio": key,
                        "radioOffset": hit.get("offset"),
                        "continueAfterDialog": cad,
                        "continueAfterRadio": car,
                        "match": "after-radio",
                    })
                last_radio = hit
    by_match = Counter(c["match"] for c in candidates)
    return {
        "mission": mission,
        "auditSource": str(audit_path.relative_to(ROOT)).replace("\\", "/"),
        "candidateCount": len(candidates),
        "byMatchKind": dict(by_match),
        "candidates": candidates,
    }


def markdown_report(results: list[dict[str, Any]]) -> str:
    total = sum(r["candidateCount"] for r in results)
    by_kind: Counter[str] = Counter()
    for result in results:
        for kind, count in result["byMatchKind"].items():
            by_kind[kind] += count
    generated = datetime.now(tz=timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    lines = [
        "# Radio Continuation Promotion Candidates",
        "",
        f"Generated: {generated}",
        "",
        "## Summary",
        "",
        f"- Mission audits inspected: {len(results)}",
        f"- Total promotion candidates: {total}",
        "- By match kind: "
        + ", ".join(f"{kind}={count}" for kind, count in by_kind.most_common()),
        "",
        "## Per-Mission Counts",
        "",
        "| mission | candidates | after-dialog | after-radio |",
        "| --- | ---: | ---: | ---: |",
    ]
    for result in sorted(results, key=lambda r: r["candidateCount"], reverse=True):
        ad = result["byMatchKind"].get("after-dialog", 0)
        ar = result["byMatchKind"].get("after-radio", 0)
        lines.append(
            f"| `{result['mission']}` | {result['candidateCount']} | {ad} | {ar} |"
        )
    lines.extend(["", "## Candidates", ""])
    for result in results:
        if not result["candidates"]:
            continue
        lines.append(f"### `{result['mission']}` ({result['candidateCount']} candidates)")
        lines.append("")
        for cand in result["candidates"]:
            file_short = (cand.get("file") or "").rsplit("/", 1)[-1]
            lines.append(
                f"- [{cand['match']}] `{cand['predecessor']}` -> `{cand['radio']}` "
                f"@ `{cand['levelId']}/{file_short}`"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mission",
        action="append",
        help="Run only for this mission id (comma-list accepted; repeatable).",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run for every _evidence_audit.json already on disk.",
    )
    parser.add_argument(
        "--audit-dir",
        type=Path,
        default=AUDIT_DIR,
        help=f"Mission-order audit directory (default: {AUDIT_DIR.relative_to(ROOT)})",
    )
    return parser.parse_args(argv)


def split_missions(values: list[str] | None) -> list[str]:
    out: list[str] = []
    for value in values or []:
        for part in str(value).split(","):
            mission = part.strip()
            if mission and mission not in out:
                out.append(mission)
    return out


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    audit_dir = args.audit_dir
    if not audit_dir.exists():
        print(f"missing audit dir: {audit_dir}", file=sys.stderr)
        return 1
    radio_table = load_radio_table()
    missions = split_missions(args.mission)
    paths: list[Path] = []
    if args.all:
        paths = sorted(audit_dir.glob("*_evidence_audit.json"))
    elif missions:
        for mission in missions:
            candidate = audit_dir / f"{mission}_evidence_audit.json"
            if not candidate.exists():
                print(f"missing audit for {mission}: {candidate}", file=sys.stderr)
                continue
            paths.append(candidate)
    else:
        paths = sorted(audit_dir.glob("*_evidence_audit.json"))
    if not paths:
        print(
            "no mission-order audits found; run build_mission_order_evidence_audit.py first",
            file=sys.stderr,
        )
        return 1
    results = [probe(path, radio_table) for path in paths]
    out_dir = audit_dir
    json_path = out_dir / "radio_continuation_CN.json"
    md_path = out_dir / "radio_continuation_CN.md"
    json_path.write_text(
        json.dumps({"results": results}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(markdown_report(results), encoding="utf-8")
    print(f"Radio continuation audit: {md_path.relative_to(ROOT)}")
    print(f"Radio continuation data:  {json_path.relative_to(ROOT)}")
    total = sum(r["candidateCount"] for r in results)
    by_kind: Counter[str] = Counter()
    for result in results:
        for kind, count in result["byMatchKind"].items():
            by_kind[kind] += count
    print(
        f"missions audited: {len(results)}; promotion candidates: {total}; "
        f"by kind: {dict(by_kind)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
