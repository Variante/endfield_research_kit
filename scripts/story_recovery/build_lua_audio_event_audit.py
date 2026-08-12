#!/usr/bin/env python3
"""Audit decrypted Lua PostEvent literals against the complete Wwise Event inventory."""
from __future__ import annotations

import argparse
import difflib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from build_audio import DEFAULT_EXPORT_ROOT, fnv1_32  # noqa: E402
from common import ROOT, md_escape, write_report_json, write_text_if_changed  # noqa: E402

DEFAULT_CACHE = DEFAULT_EXPORT_ROOT / "recovered/audio/lua_audio_references.json"
DEFAULT_INDEX = DEFAULT_EXPORT_ROOT / "structured/Audio/CN/index.json"
DEFAULT_JSON = ROOT / "reports/story/recovery/lua_audio_event_audit.json"
DEFAULT_MD = ROOT / "reports/story/recovery/lua_audio_event_audit.md"


def load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def build_payload(cache: dict[str, Any], audio_index: dict[str, Any]) -> dict[str, Any]:
    direct_rows = [
        row for row in cache.get("references") or []
        if isinstance(row, dict) and row.get("kind") == "luaPostEvent" and row.get("name")
    ]
    calls_by_name: dict[str, list[dict[str, Any]]] = defaultdict(list)
    peers_by_source: dict[str, set[str]] = defaultdict(set)
    for row in direct_rows:
        name = str(row["name"]).lower()
        calls_by_name[name].append({
            key: row[key]
            for key in ("source", "line", "expression", "method", "hash", "hashHex", "evidence")
            if row.get(key) not in (None, "")
        })
        peers_by_source[str(row.get("source") or "")].add(name)

    event_occurrences: Counter[int] = Counter()
    event_media: dict[int, set[int]] = defaultdict(set)
    for row in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(row, dict):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        event_occurrences[event_hash] += 1
        event_media[event_hash].update(
            int(value) for value in row.get("mediaIds") or []
            if isinstance(value, int)
        )

    resolved_names_by_hash: dict[int, set[str]] = defaultdict(set)
    for row in audio_index.get("eventEvidence") or []:
        if not isinstance(row, dict) or not row.get("eventId"):
            continue
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            continue
        name = str(row["eventId"]).strip()
        if name and not name.lower().startswith("hashed-event:"):
            resolved_names_by_hash[event_hash].add(name)
    resolved_names = sorted({name.lower() for names in resolved_names_by_hash.values() for name in names})

    rows = []
    for name in sorted(calls_by_name):
        event_hash = fnv1_32(name)
        found = event_hash in event_occurrences
        near = []
        if not found:
            ranked = sorted(
                (
                    difflib.SequenceMatcher(None, name, candidate).ratio(),
                    candidate,
                )
                for candidate in resolved_names
                if candidate != name
            )
            for ratio, candidate in reversed(ranked[-5:]):
                if ratio < 0.55:
                    continue
                candidate_hash = fnv1_32(candidate)
                near.append({
                    "name": candidate,
                    "hash": candidate_hash,
                    "hashHex": f"0x{candidate_hash:08x}",
                    "similarity": round(ratio, 6),
                    "eventObjectOccurrences": event_occurrences.get(candidate_hash, 0),
                    "mediaCount": len(event_media.get(candidate_hash, set())),
                    "evidenceBoundary": "nameSimilarityOnlyNotAnAlias",
                })
        sources = {str(call.get("source") or "") for call in calls_by_name[name]}
        sibling_names = sorted({
            peer
            for source in sources
            for peer in peers_by_source.get(source, set())
            if peer != name
        })
        resolved_siblings = [
            sibling for sibling in sibling_names
            if fnv1_32(sibling) in event_occurrences
        ]
        if found:
            status = "resolvedWwiseEventObject"
        elif near and float(near[0]["similarity"]) >= 0.94:
            status = "absentWithVeryCloseResolvedName"
        elif resolved_siblings:
            status = "absentWithResolvedSameFileSiblingEvents"
        else:
            status = "absentFromCompleteEventInventory"
        rows.append({
            "name": name,
            "hash": event_hash,
            "hashHex": f"0x{event_hash:08x}",
            "status": status,
            "eventObjectOccurrences": event_occurrences.get(event_hash, 0),
            "mediaCount": len(event_media.get(event_hash, set())),
            "callsites": calls_by_name[name],
            "sameFileSiblingEventNames": sibling_names,
            "resolvedSameFileSiblingEventNames": resolved_siblings,
            "nearResolvedNames": near,
        })

    status_counts = Counter(row["status"] for row in rows)
    return {
        "schemaVersion": 1,
        "summary": {
            "luaPostEventNames": len(rows),
            "luaPostEventCallsites": len(direct_rows),
            "resolvedEventNames": status_counts.get("resolvedWwiseEventObject", 0),
            "unresolvedEventNames": len(rows) - status_counts.get("resolvedWwiseEventObject", 0),
            "statusCounts": dict(sorted(status_counts.items())),
            "scannedEventObjectOccurrences": sum(event_occurrences.values()),
            "scannedUniqueEventHashes": len(event_occurrences),
        },
        "evidenceBoundary": (
            "Exact decrypted Lua PostEvent literals are hashed against every Event object in the current nine-PCK inventory. "
            "Near names and same-file siblings are review evidence only; they never create aliases, media links, or runtime execution claims."
        ),
        "events": rows,
    }


def render_markdown(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Lua Audio Event Audit",
        "",
        f"- direct PostEvent names: `{summary['luaPostEventNames']}`",
        f"- direct PostEvent callsites: `{summary['luaPostEventCallsites']}`",
        f"- resolved to current Wwise Event objects: `{summary['resolvedEventNames']}`",
        f"- unresolved: `{summary['unresolvedEventNames']}`",
        f"- scanned Event objects: `{summary['scannedEventObjectOccurrences']}` occurrences / `{summary['scannedUniqueEventHashes']}` unique hashes",
        "",
        f"> {md_escape(payload['evidenceBoundary'])}",
        "",
        "## Unresolved Requests",
        "",
        "| Lua request | hash | callsites | status | closest resolved name | resolved same-file siblings |",
        "| --- | --- | ---: | --- | --- | --- |",
    ]
    for row in payload["events"]:
        if row["status"] == "resolvedWwiseEventObject":
            continue
        closest = row.get("nearResolvedNames") or []
        closest_text = "-"
        if closest:
            closest_text = f"{closest[0]['name']} ({closest[0]['similarity']:.3f}; similarity only)"
        siblings = ", ".join(row.get("resolvedSameFileSiblingEventNames") or []) or "-"
        lines.append(
            f"| `{md_escape(row['name'])}` | `{row['hashHex']}` | {len(row['callsites'])} | "
            f"`{row['status']}` | `{md_escape(closest_text)}` | `{md_escape(siblings)}` |"
        )
        for call in row["callsites"]:
            lines.append(
                f"|  |  |  | `{md_escape(call.get('source'))}:{call.get('line')}` | "
                f"`{md_escape(call.get('expression'))}` |  |"
            )
    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--audio-index", type=Path, default=DEFAULT_INDEX)
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_payload(load_json(args.cache), load_json(args.audio_index))
    write_report_json(args.json, payload)
    write_text_if_changed(args.markdown, render_markdown(payload))
    summary = payload["summary"]
    print(
        f"Lua audio Event audit: {summary['resolvedEventNames']}/{summary['luaPostEventNames']} resolved; "
        f"{summary['unresolvedEventNames']} unresolved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
