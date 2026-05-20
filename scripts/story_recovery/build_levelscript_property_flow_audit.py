#!/usr/bin/env python3
"""Audit LevelScript-property condition / setter bridge evidence.

`MissionRuntimeAsset/*.json` quests carry `CheckLevelScriptPropertyBool`
and `CheckLevelScriptPropertyInt` conditions with `(mapId, scriptId, key)`
triples. This script:

1. Walks every MRA file, extracts every property-condition triple, and
   records the checker mission, quest id, expected value, and any story
   refs on that quest.
2. Locates the target LevelScript file at
   `LevelScriptData/<mapId>/<scriptId>.json`.
3. Tests whether the property key appears as a length-prefixed UTF-8
   string inside the LS binary (the Unity serialization pattern: 4-byte
   little-endian length followed by the ASCII bytes).
4. Uses the existing `level_bindings._load_levelscript_binding_data`
   decoder to enumerate the records inside the LS file, and records
   which record(s) carry the property key as a string payload plus
   adjacent story refs (`dlg_*`, `radio_*`, `cutscene_*`, etc.).

The output records two evidence classes:

- **bridgeFound**: the key appears as a length-prefixed string in the
  target LS file. This is strong evidence the property is declared or
  read/gated inside that script. Adjacent story-keyed records in the same
  LS file are candidates for follow-up order evidence, but are not setter
  proof by themselves.
- **bridgeMissing**: the key is not in the LS binary. This is typical
  for runtime-system property names like `isFinished` and `isSucceeded`
  which the script exposes implicitly without storing the string.

Output:

    reports/mission_order/levelscript_property_flow_CN.json
    reports/mission_order/levelscript_property_flow_CN.md

Treat the bridgeFound rows as candidates for follow-up promotion to
strong scene-order edges once the setter opcode/kind is identified by
cross-referencing record adjacency with the rest of the mission audit.
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

from common import ROOT, md_escape, read_json, write_report_json, write_text_if_changed  # noqa: E402
from build_mission_order_evidence_audit import collect_mission_runtime_script_conditions  # noqa: E402

try:
    from story_builder.level_bindings import (  # noqa: E402
        _load_levelscript_binding_data,
        classify_levelscript_record,
    )
    from story_builder.levelscript_binary import decode_levelscript_record_payload  # noqa: E402
except ImportError:
    _load_levelscript_binding_data = None
    classify_levelscript_record = None
    decode_levelscript_record_payload = None

DATA_JSON_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MRA_DIR = DATA_JSON_ROOT / "MissionRuntimeAsset"
LEVELSCRIPT_DIR = DATA_JSON_ROOT / "LevelScriptData"


def safe_text(value: Any) -> str:
    return str(value or "")


def collect_quest_story_refs(quest: Any) -> list[str]:
    refs: list[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, dict):
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)
        elif isinstance(node, str):
            text = node
            for token in text.split():
                token = token.strip(",[]{}'\"")
                if (
                    token.startswith(("dlg_", "sns_", "cutscene_", "black_", "remotecomm_", "radio_"))
                    and len(token) > 4
                    and len(token) < 80
                ):
                    if token not in refs:
                        refs.append(token)

    walk(quest)
    return refs


def detect_property_key_in_ls(ls_path: Path, key: str) -> dict[str, Any]:
    if not ls_path.exists():
        return {"lsFileExists": False}
    try:
        raw = ls_path.read_bytes()
    except OSError:
        return {"lsFileExists": False}
    key_bytes = key.encode("utf-8")
    target = len(key_bytes).to_bytes(4, "little") + key_bytes
    substring_match = key_bytes in raw
    length_prefix_match = target in raw
    result = {
        "lsFileExists": True,
        "lsSizeBytes": len(raw),
        "keySubstringMatch": substring_match,
        "lengthPrefixedMatch": length_prefix_match,
    }
    if length_prefix_match:
        # find offset of first match
        result["firstLengthPrefixedOffset"] = raw.find(target)
    return result


def collect_nearby_story_refs_from_records(records: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    if not records:
        return []
    candidates: list[dict[str, Any]] = []
    for idx, record in enumerate(records):
        strings = [*(record.get("strings") or []), *(record.get("plainStrings") or [])]
        if any(s.get("text") == key for s in strings):
            # walk +/- 4 records for story-keyed strings
            window: list[dict[str, Any]] = []
            lo = max(0, idx - 4)
            hi = min(len(records), idx + 5)
            for jdx in range(lo, hi):
                neighbor = records[jdx]
                story_strings = [
                    s.get("text")
                    for s in neighbor.get("strings") or []
                    if isinstance(s, dict)
                    and isinstance(s.get("text"), str)
                    and s["text"].startswith(("dlg_", "sns_", "cutscene_", "black_", "remotecomm_", "radio_", "misc_dlg_"))
                ]
                if story_strings:
                    window.append({
                        "delta": jdx - idx,
                        "code": neighbor.get("code"),
                        "kind": neighbor.get("kind"),
                        "uid": neighbor.get("uid"),
                        "storyRefs": story_strings,
                    })
            candidates.append({
                "recordOffset": record.get("start"),
                "code": record.get("code"),
                "kind": record.get("kind"),
                "uid": record.get("uid"),
                "nextId": record.get("nextId"),
                "neighborStoryRefs": window,
            })
    return candidates


def record_texts(record: dict[str, Any]) -> list[str]:
    out: list[str] = []
    for field in ("strings", "plainStrings"):
        for hit in record.get(field) or []:
            text = hit.get("text") if isinstance(hit, dict) else hit
            if isinstance(text, str) and text and text not in out:
                out.append(text)
    return out


def format_opcode(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return ""


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


def collect_property_record_hits(
    *,
    records: list[dict[str, Any]],
    data: bytes,
    key: str,
) -> list[dict[str, Any]]:
    if not records or not data or decode_levelscript_record_payload is None:
        return []
    next_by_start = next_start_by_record_start(records, len(data))
    hits: list[dict[str, Any]] = []
    for record in records:
        texts = record_texts(record)
        if key not in texts:
            continue
        start = int(record.get("start") or 0)
        decoded = decode_levelscript_record_payload(
            data,
            record,
            next_start=next_by_start.get(start),
        )
        row = {
            "recordOffset": start,
            "recordOffsetHex": f"0x{start:x}",
            "localId": record.get("localId"),
            "nextId": record.get("nextId"),
            "opcode": format_opcode(record),
            "class": classify_levelscript_record(record) if classify_levelscript_record else "",
            "hint": decoded.get("label") or "",
            "hintConfidence": decoded.get("confidence") or "",
            "propertyRole": decoded.get("propertyRole") or "",
            "propertyEventKind": decoded.get("propertyEventKind") or "",
            "propertyKeys": decoded.get("propertyKeys") or [],
            "propertyOutputRefs": decoded.get("propertyOutputRefs") or [],
            "triggerSlotIds": decoded.get("triggerSlotIds") or [],
            "compactGate": decoded.get("compactGate") or {},
            "gateLocalRefs": decoded.get("gateLocalRefs") or [],
            "branchLocalRefs": decoded.get("branchLocalRefs") or [],
            "texts": texts[:12],
        }
        hits.append({field: value for field, value in row.items() if value not in ("", None, [], {})})
    return hits


def build_audit() -> dict[str, Any]:
    if not MRA_DIR.is_dir():
        return {"error": f"missing {MRA_DIR}"}

    triples: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    cond_total = 0
    prop_total = 0
    missions_seen: set[str] = set()
    quests_by_mission: dict[str, dict[str, Any]] = {}

    for mra_path in sorted(MRA_DIR.glob("*.json")):
        mission_id = mra_path.stem
        if mission_id.endswith("_meta"):
            continue
        try:
            mra_payload = json.loads(mra_path.read_text(encoding="utf-8"))
        except Exception:
            continue
        quests_by_mission[mission_id] = (mra_payload.get("questDic") or {})
        conds = collect_mission_runtime_script_conditions(mra_payload)
        if not conds:
            continue
        cond_total += len(conds)
        for cond in conds:
            cond_type = safe_text(cond.get("type"))
            if "Property" not in cond_type:
                continue
            map_id = safe_text(cond.get("mapId"))
            script_id = safe_text(cond.get("scriptId"))
            key = safe_text(cond.get("key"))
            if not (map_id and script_id and key):
                continue
            prop_total += 1
            triples[(map_id, script_id, key)].append({
                "mission": mission_id,
                "questId": safe_text(cond.get("questId")),
                "uniqueId": safe_text(cond.get("uniqueId")),
                "expectedValue": cond.get("value"),
                "comparer": cond.get("comparer"),
                "conditionType": cond_type,
            })
            missions_seen.add(mission_id)

    bridge_rows: list[dict[str, Any]] = []
    bridge_summary = Counter()
    property_record_opcode_counts = Counter()
    property_record_role_counts = Counter()
    record_decoder_available = _load_levelscript_binding_data is not None
    decoder_calls = 0

    for triple, checker_meta in sorted(triples.items()):
        map_id, script_id, key = triple
        ls_path = LEVELSCRIPT_DIR / map_id / f"{script_id}.json"
        detect = detect_property_key_in_ls(ls_path, key)
        bridge_status = "bridgeMissing"
        nearby_story_refs: list[dict[str, Any]] = []
        property_record_hits: list[dict[str, Any]] = []
        if detect.get("lengthPrefixedMatch"):
            bridge_status = "bridgeFound"
            if record_decoder_available and decoder_calls < 200:
                try:
                    decoded = _load_levelscript_binding_data(map_id)
                except Exception:
                    decoded = None
                decoder_calls += 1
                if isinstance(decoded, dict):
                    script_id_token = str(script_id)
                    suffix = f"{script_id_token}.json"
                    for file_entry in decoded.get("files") or []:
                        file_path = str(file_entry.get("file") or "")
                        if file_path.endswith("/" + suffix) or file_path.endswith("\\" + suffix):
                            records = file_entry.get("records") or []
                            nearby_story_refs = collect_nearby_story_refs_from_records(records, key)
                            raw_path = Path(file_path)
                            if not raw_path.is_absolute():
                                raw_path = ROOT / raw_path
                            try:
                                raw_data = raw_path.read_bytes()
                            except OSError:
                                raw_data = b""
                            property_record_hits = collect_property_record_hits(
                                records=records,
                                data=raw_data,
                                key=key,
                            )
                            for hit in property_record_hits:
                                opcode = hit.get("opcode") or "unknown"
                                property_record_opcode_counts[opcode] += 1
                                role = hit.get("propertyRole") or hit.get("hint") or "unknown"
                                property_record_role_counts[role] += 1
                            break
        elif detect.get("keySubstringMatch"):
            bridge_status = "bridgeSubstringOnly"
        bridge_summary[bridge_status] += 1

        # Collect story refs from the checker quests
        checker_story_refs: list[str] = []
        for entry in checker_meta:
            mission_id = entry.get("mission") or ""
            quest_id = entry.get("questId") or ""
            quest_dic = quests_by_mission.get(mission_id) or {}
            quest = quest_dic.get(quest_id)
            if quest:
                for ref in collect_quest_story_refs(quest):
                    if ref not in checker_story_refs:
                        checker_story_refs.append(ref)
        bridge_rows.append({
            "mapId": map_id,
            "scriptId": script_id,
            "key": key,
            "checkerCount": len(checker_meta),
            "checkers": checker_meta,
            "checkerMissions": sorted({c["mission"] for c in checker_meta}),
            "checkerStoryRefs": checker_story_refs,
            "lsDetect": detect,
            "bridgeStatus": bridge_status,
            "nearbyStoryRefs": nearby_story_refs,
            "propertyRecordHits": property_record_hits,
        })

    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": {
            "missionRuntimeAssetDir": str(MRA_DIR),
            "levelScriptDir": str(LEVELSCRIPT_DIR),
        },
        "summary": {
            "missionsWithPropertyChecks": len(missions_seen),
            "totalConditions": cond_total,
            "propertyConditions": prop_total,
            "distinctTriples": len(triples),
            "bridgeStatus": dict(bridge_summary.most_common()),
            "decodedScriptCount": decoder_calls,
            "propertyRecordOpcodeCounts": dict(property_record_opcode_counts.most_common()),
            "propertyRecordRoleCounts": dict(property_record_role_counts.most_common()),
        },
        "evidenceClassification": {
            "isOrderingSource": True,
            "isPromotable": False,
            "reason": (
                "This audit identifies which checker conditions have a real "
                "owning LS script (key visible as length-prefixed UTF-8 in the "
                "binary), establishing the bridge. The named low ActionBase "
                "setters do not exact-match these MissionRuntime check triples, "
                "so promotion requires a decoded gate/terminal walk or another "
                "independent runtime edge."
            ),
        },
        "rows": bridge_rows,
    }


def markdown_report(payload: dict[str, Any]) -> str:
    if payload.get("error"):
        return f"# LevelScript Property Flow Audit\n\nError: {payload['error']}\n"
    s = payload["summary"]
    lines = [
        "# LevelScript Property Flow Audit",
        "",
        f"Generated: {payload['generated']}",
        "",
        "## Summary",
        "",
        f"- Missions with property checks: `{s['missionsWithPropertyChecks']}`",
        f"- Total conditions: `{s['totalConditions']}` (property-typed: `{s['propertyConditions']}`)",
        f"- Distinct `(mapId, scriptId, key)` triples: `{s['distinctTriples']}`",
        f"- Bridge status: `{s['bridgeStatus']}`",
        f"- Decoded LS scripts (for nearby-story-ref enumeration): `{s['decodedScriptCount']}`",
        f"- Property record opcodes: `{s.get('propertyRecordOpcodeCounts', {})}`",
        f"- Property record roles: `{s.get('propertyRecordRoleCounts', {})}`",
        "",
        "## Evidence Classification",
        "",
        f"- `isOrderingSource`: `{payload['evidenceClassification']['isOrderingSource']}`",
        f"- `isPromotable`: `{payload['evidenceClassification']['isPromotable']}`",
        f"- Reason: {payload['evidenceClassification']['reason']}",
        "",
        "## Property Record Opcode Clusters",
        "",
        "| opcode | count |",
        "| --- | ---: |",
    ]

    opcode_counts = s.get("propertyRecordOpcodeCounts") or {}
    if opcode_counts:
        for opcode, count in opcode_counts.items():
            lines.append(f"| `{md_escape(opcode)}` | {count} |")
    else:
        lines.append("| _(none)_ | 0 |")

    lines.extend([
        "",
        "## Bridge Found Rows (sample, first 40)",
        "",
        "| mapId | scriptId | key | checker count | missions | key offset | record opcodes | nearby refs |",
        "| --- | --- | --- | ---: | --- | ---: | --- | --- |",
    ])

    bridge_rows = [row for row in payload["rows"] if row["bridgeStatus"] == "bridgeFound"]
    bridge_rows.sort(key=lambda r: (-r["checkerCount"], r["mapId"], r["scriptId"], r["key"]))
    if not bridge_rows:
        lines.append("| _(none)_ |  |  |  |  |  |  |")
    else:
        for row in bridge_rows[:40]:
            offset = row["lsDetect"].get("firstLengthPrefixedOffset")
            nearby = ", ".join(
                "+" + str(n["delta"]) + ":" + ",".join(n["storyRefs"][:2])
                for n in row.get("nearbyStoryRefs") or []
                for n in n.get("neighborStoryRefs") or []
            ) if row.get("nearbyStoryRefs") else ""
            opcodes = ", ".join(
                " ".join(
                    part
                    for part in (
                        hit.get("opcode") or "",
                        hit.get("hint") or "",
                        hit.get("propertyEventKind") or "",
                        (
                            "gateRefs="
                            + ",".join(str(ref) for ref in hit.get("gateLocalRefs")[:4])
                            if hit.get("gateLocalRefs")
                            else ""
                        ),
                        (
                            "branches="
                            + ",".join(str(ref) for ref in hit.get("branchLocalRefs")[:4])
                            if hit.get("branchLocalRefs")
                            else ""
                        ),
                    )
                    if part
                )
                for hit in row.get("propertyRecordHits") or []
                if hit.get("opcode")
            )
            missions = ", ".join(row["checkerMissions"][:3])
            lines.append(
                f"| `{md_escape(row['mapId'])}` "
                f"| `{md_escape(row['scriptId'])}` "
                f"| `{md_escape(row['key'])}` "
                f"| {row['checkerCount']} "
                f"| `{md_escape(missions)}` "
                f"| `{offset}` "
                f"| `{md_escape(opcodes[:80])}` "
                f"| `{md_escape(nearby[:120])}` |"
            )

    lines.extend([
        "",
        "## Bridge Missing Rows (system-level property names)",
        "",
        "| mapId | scriptId | key | checker count | missions |",
        "| --- | --- | --- | ---: | --- |",
    ])
    missing_rows = [row for row in payload["rows"] if row["bridgeStatus"] != "bridgeFound"]
    missing_rows.sort(key=lambda r: (-r["checkerCount"], r["mapId"], r["scriptId"], r["key"]))
    for row in missing_rows[:30]:
        missions = ", ".join(row["checkerMissions"][:3])
        lines.append(
            f"| `{md_escape(row['mapId'])}` "
            f"| `{md_escape(row['scriptId'])}` "
            f"| `{md_escape(row['key'])}` "
            f"| {row['checkerCount']} "
            f"| `{md_escape(missions)}` |"
        )
    if not missing_rows:
        lines.append("| _(none)_ |  |  |  |  |")

    lines.extend([
        "",
        "## Notes",
        "",
        "Bridge-found rows are candidates for follow-up scene-order analysis.",
        "Bridge-missing rows mostly use runtime-system property names",
        "(`isFinished`, `isSucceeded`, etc.) that the LS script exposes",
        "implicitly without storing the property name as a literal string.",
        "Use this audit as input to downstream gate/terminal decoders; do not",
        "promote anything to strong order edges directly from this report.",
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
    payload = build_audit()
    out_json = args.reports_dir / f"levelscript_property_flow_{args.language}.json"
    out_md = args.reports_dir / f"levelscript_property_flow_{args.language}.md"
    write_report_json(out_json, payload)
    write_text_if_changed(out_md, markdown_report(payload))
    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    s = payload.get("summary") or {}
    print(
        f"LevelScript property flow: "
        f"{s.get('missionsWithPropertyChecks')} missions, "
        f"{s.get('propertyConditions')} property conditions, "
        f"{s.get('distinctTriples')} triples, "
        f"bridge={s.get('bridgeStatus')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
