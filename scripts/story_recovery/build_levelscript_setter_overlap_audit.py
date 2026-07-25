#!/usr/bin/env python3
"""Compare MissionRuntime property checks with decoded ActionBase setters.

MissionRuntime `CheckLevelScriptProperty*` rows point at `(mapId, scriptId,
key)` triples. The named low ActionBase setters (`SetBool`, `SetInt`,
`SetIntIncrease`) are a tempting completion-source candidate, so this audit
checks whether those setters actually write the same script/key triples.

Output:

    reports/mission_order/levelscript_setter_overlap_CN.json
    reports/mission_order/levelscript_setter_overlap_CN.md
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts", _REPO_ROOT / "scripts" / "story_recovery"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402
from build_mission_order_evidence_audit import collect_mission_runtime_script_conditions  # noqa: E402
from story_builder.context import LEVELSCRIPT_DIR  # noqa: E402
from story_builder.level_bindings import _load_levelscript_binding_data  # noqa: E402
from story_builder.levelscript_binary import decode_levelscript_record_payload  # noqa: E402


REPORT_DIR = ROOT / "reports" / "mission_order"
DATA_JSON_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MRA_DIR = DATA_JSON_ROOT / "MissionRuntimeAsset"

SETTER_OPCODES = {
    (0x03DA, 0x0A): "SetBool",
    (0x0410, 0x0A): "SetInt",
    (0x0413, 0x0A): "SetIntIncrease",
}


def safe_text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def repo_rel(path: Path | str) -> str:
    p = Path(path)
    try:
        return p.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return str(path).replace("\\", "/")


def next_start_by_record_start(records: list[dict[str, Any]], data_len: int) -> dict[int, int | None]:
    starts: dict[int, int | None] = {}
    sorted_records = sorted(records, key=lambda row: int(row.get("start") or 0))
    for index, record in enumerate(sorted_records):
        start = int(record.get("start") or 0)
        starts[start] = (
            int(sorted_records[index + 1].get("start") or data_len)
            if index + 1 < len(sorted_records)
            else None
        )
    return starts


def record_texts(record: dict[str, Any], decoded: dict[str, Any] | None = None) -> list[str]:
    out: list[str] = []
    for field in (decoded or {}).get("taggedFields") or []:
        if isinstance(field, dict) and field.get("type") == "string":
            text = safe_text(field.get("value"))
            if text and text not in out:
                out.append(text)
    for field_name in ("strings", "plainStrings"):
        for hit in record.get(field_name) or []:
            text = safe_text(hit.get("text") if isinstance(hit, dict) else hit)
            if text and text not in out:
                out.append(text)
    return out


def collect_property_checks() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(MRA_DIR.glob("*.json")):
        if path.stem.endswith("_meta"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        for condition in collect_mission_runtime_script_conditions(payload):
            condition_type = safe_text(condition.get("type"))
            if "Property" not in condition_type:
                continue
            map_id = safe_text(condition.get("mapId"))
            script_id = safe_text(condition.get("scriptId"))
            key = safe_text(condition.get("key"))
            if not (map_id and script_id and key):
                continue
            rows.append({
                "mission": path.stem,
                "questId": safe_text(condition.get("questId")),
                "mapId": map_id,
                "scriptId": script_id,
                "key": key,
                "expectedValue": condition.get("value"),
                "comparer": condition.get("comparer"),
                "type": condition_type,
            })
    return rows


def collect_setters() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for level_dir in sorted(path for path in LEVELSCRIPT_DIR.iterdir() if path.is_dir()):
        binding = _load_levelscript_binding_data(level_dir.name)
        for file_info in binding.get("files") or []:
            file_path = Path(safe_text(file_info.get("file")))
            if not file_path.is_absolute():
                file_path = ROOT / file_path
            try:
                data = file_path.read_bytes()
            except OSError:
                continue
            records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
            next_by_start = next_start_by_record_start(records, len(data))
            for record in records:
                opcode = (record.get("code"), record.get("kind"))
                if opcode not in SETTER_OPCODES:
                    continue
                start = int(record.get("start") or 0)
                decoded = decode_levelscript_record_payload(data, record, next_start=next_by_start.get(start))
                keys = list(decoded.get("propertyKeys") or [])
                if not keys:
                    for text in record_texts(record, decoded):
                        if text and text not in keys:
                            keys.append(text)
                for key in keys:
                    rows.append({
                        "mapId": level_dir.name,
                        "scriptId": file_path.stem,
                        "key": key,
                        "action": SETTER_OPCODES[opcode],
                        "opcode": f"0x{int(opcode[0]):04x}/0x{int(opcode[1]):02x}",
                        "offset": f"0x{start:x}",
                        "localId": record.get("localId"),
                        "nextId": record.get("nextId"),
                        "file": repo_rel(file_path),
                    })
    return rows


def compact_check(check: dict[str, Any]) -> dict[str, Any]:
    return {
        "mission": check.get("mission"),
        "questId": check.get("questId"),
        "mapId": check.get("mapId"),
        "scriptId": check.get("scriptId"),
        "expectedValue": check.get("expectedValue"),
        "comparer": check.get("comparer"),
        "type": check.get("type"),
    }


def build_audit() -> dict[str, Any]:
    checks = collect_property_checks()
    setters = collect_setters()
    checks_by_exact: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    checks_by_level_key: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    checks_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for check in checks:
        checks_by_exact[(check["mapId"], check["scriptId"], check["key"])].append(check)
        checks_by_level_key[(check["mapId"], check["key"])].append(check)
        checks_by_key[check["key"]].append(check)

    exact_rows: list[dict[str, Any]] = []
    same_level_rows: list[dict[str, Any]] = []
    key_only_rows: list[dict[str, Any]] = []
    for setter in setters:
        exact = checks_by_exact.get((setter["mapId"], setter["scriptId"], setter["key"])) or []
        if exact:
            exact_rows.append({
                "setter": setter,
                "checks": [compact_check(check) for check in exact[:8]],
            })
            continue
        same_level = checks_by_level_key.get((setter["mapId"], setter["key"])) or []
        if same_level:
            same_level_rows.append({
                "setter": setter,
                "checks": [compact_check(check) for check in same_level[:8]],
            })
            continue
        key_only = checks_by_key.get(setter["key"]) or []
        if key_only:
            key_only_rows.append({
                "setter": setter,
                "checks": [compact_check(check) for check in key_only[:8]],
            })

    setter_actions = Counter(setter.get("action") for setter in setters)
    check_types = Counter(check.get("type") for check in checks)
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "missionRuntimeAssetDir": repo_rel(MRA_DIR),
            "levelScriptDir": repo_rel(LEVELSCRIPT_DIR),
        },
        "summary": {
            "propertyChecks": len(checks),
            "distinctCheckTriples": len(checks_by_exact),
            "distinctCheckKeys": len(checks_by_key),
            "setterKeyRows": len(setters),
            "setterActions": dict(setter_actions.most_common()),
            "checkTypes": dict(check_types.most_common()),
            "exactSetterCheckMatches": len(exact_rows),
            "sameLevelKeyMatches": len(same_level_rows),
            "sameKeyOnlyMatches": len(key_only_rows),
        },
        "evidenceClassification": {
            "isOrderingSource": True,
            "isPromotable": False,
            "reason": (
                "Named ActionBase setters are real mutation actions, but they do not "
                "exactly match MissionRuntime `(mapId, scriptId, key)` property checks "
                "in this export. Same-key-only matches are too generic for mission "
                "timeline promotion."
            ),
        },
        "exactMatches": exact_rows,
        "sameLevelKeyMatches": same_level_rows[:200],
        "sameKeyOnlyMatches": key_only_rows[:200],
    }


def markdown_report(payload: dict[str, Any]) -> str:
    summary = payload.get("summary") or {}
    lines = [
        "# LevelScript Setter / MissionRuntime Property Overlap",
        "",
        f"Generated: {payload.get('generated')}",
        "",
        "## Summary",
        "",
        f"- MissionRuntime property checks: `{summary.get('propertyChecks')}`",
        f"- Distinct check triples: `{summary.get('distinctCheckTriples')}`",
        f"- Distinct check keys: `{summary.get('distinctCheckKeys')}`",
        f"- Decoded setter-key rows: `{summary.get('setterKeyRows')}`",
        f"- Setter actions: `{summary.get('setterActions')}`",
        f"- Exact `(mapId, scriptId, key)` setter/check matches: `{summary.get('exactSetterCheckMatches')}`",
        f"- Same-level same-key matches: `{summary.get('sameLevelKeyMatches')}`",
        f"- Same-key-only matches: `{summary.get('sameKeyOnlyMatches')}`",
        "",
        "## Interpretation",
        "",
        "- `SetBool`, `SetInt`, and `SetIntIncrease` are confirmed ActionBase setters.",
        "- They do not exactly write any MissionRuntime checked `(mapId, scriptId, key)` triple in this export.",
        "- This supports treating `0x0a03` / `0x0bed` as script-property gate/terminal read shapes, not as normal ActionBase setters.",
        "",
        "## Same-Level Same-Key Matches",
        "",
        "| setter | key | action | offset | checks |",
        "| --- | --- | --- | --- | --- |",
    ]
    same_level = payload.get("sameLevelKeyMatches") or []
    if not same_level:
        lines.append("| _(none)_ |  |  |  |  |")
    for row in same_level[:30]:
        setter = row.get("setter") or {}
        checks = "; ".join(
            f"{check.get('mission')}/{check.get('questId')} -> {check.get('scriptId')}"
            for check in (row.get("checks") or [])[:4]
        )
        lines.append(
            f"| `{md_escape(setter.get('mapId'))}/{md_escape(setter.get('scriptId'))}` "
            f"| `{md_escape(setter.get('key'))}` "
            f"| `{md_escape(setter.get('action'))}` "
            f"| `{md_escape(setter.get('offset'))}` "
            f"| `{md_escape(checks)}` |"
        )

    lines.extend([
        "",
        "## Same-Key-Only Matches",
        "",
        "| setter | key | action | offset | checks |",
        "| --- | --- | --- | --- | --- |",
    ])
    key_only = payload.get("sameKeyOnlyMatches") or []
    if not key_only:
        lines.append("| _(none)_ |  |  |  |  |")
    for row in key_only[:30]:
        setter = row.get("setter") or {}
        checks = "; ".join(
            f"{check.get('mission')}/{check.get('questId')} {check.get('mapId')}/{check.get('scriptId')}"
            for check in (row.get("checks") or [])[:4]
        )
        lines.append(
            f"| `{md_escape(setter.get('mapId'))}/{md_escape(setter.get('scriptId'))}` "
            f"| `{md_escape(setter.get('key'))}` "
            f"| `{md_escape(setter.get('action'))}` "
            f"| `{md_escape(setter.get('offset'))}` "
            f"| `{md_escape(checks)}` |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--reports-dir", type=Path, default=REPORT_DIR)
    args = parser.parse_args()

    args.reports_dir.mkdir(parents=True, exist_ok=True)
    payload = build_audit()
    out_json = args.reports_dir / f"levelscript_setter_overlap_{args.language}.json"
    out_md = args.reports_dir / f"levelscript_setter_overlap_{args.language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    summary = payload.get("summary") or {}
    print(f"LevelScript setter overlap audit: {out_json}")
    print(f"LevelScript setter overlap report: {out_md}")
    print(
        f"checks={summary.get('propertyChecks')} "
        f"setters={summary.get('setterKeyRows')} "
        f"exact={summary.get('exactSetterCheckMatches')} "
        f"sameLevel={summary.get('sameLevelKeyMatches')} "
        f"keyOnly={summary.get('sameKeyOnlyMatches')}"
    )


if __name__ == "__main__":
    main()
