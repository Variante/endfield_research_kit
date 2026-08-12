#!/usr/bin/env python3
"""Audit identity-only Wwise Event names recovered from the skill-id map."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import sha256_file as file_sha256  # noqa: E402

SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from build_audio_semantics import audio_hash_generator_compute  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))




def scan_serialized_hashes(
    export_root: Path,
    event_hashes: set[int],
) -> tuple[dict[int, list[dict[str, Any]]], dict[str, int]]:
    needles = {event_hash: struct.pack("<I", event_hash) for event_hash in event_hashes}
    hits: dict[int, list[dict[str, Any]]] = defaultdict(list)
    file_count = 0
    byte_count = 0
    for source_root in ("StreamingAssets", "Persistent"):
        for family in ("SkillData", "BuffData"):
            root = export_root / "structured" / source_root / "Data" / "Json" / family
            for path in sorted(root.glob("*.json")):
                data = path.read_bytes()
                file_count += 1
                byte_count += len(data)
                for event_hash, needle in needles.items():
                    offsets: list[int] = []
                    offset = data.find(needle)
                    while offset >= 0 and len(offsets) < 20:
                        offsets.append(offset)
                        offset = data.find(needle, offset + 1)
                    if offsets:
                        hits[event_hash].append({
                            "source": path.relative_to(export_root).as_posix(),
                            "offsets": offsets,
                        })
    return dict(hits), {"files": file_count, "bytes": byte_count}


def build_report(audio_index: dict[str, Any], export_root: Path) -> dict[str, Any]:
    aliases = [
        dict(row) for row in audio_index.get("skillIdDictionaryWwiseEventAliases") or []
        if isinstance(row, dict)
    ]
    inventory: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in audio_index.get("wwiseEventInventory") or []:
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int):
            inventory[int(row["eventHash"]) & 0xFFFFFFFF].append(row)
    event_hashes = {
        int(row["eventHash"]) & 0xFFFFFFFF
        for row in aliases if isinstance(row.get("eventHash"), int)
    }
    serialized_hits, scan = scan_serialized_hashes(export_root, event_hashes)
    errors: list[str] = []
    output_rows: list[dict[str, Any]] = []
    relation_counts: Counter[str] = Counter()
    operation_counts: Counter[str] = Counter()
    for row in aliases:
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            errors.append(f"invalid alias: {row!r}")
            continue
        name = str(row.get("name") or "").strip()
        if audio_hash_generator_compute(name) != event_hash:
            errors.append(f"name hash mismatch: {name}: 0x{event_hash:08x}")
        if row.get("dictionaryKind") != "skill_id":
            errors.append(f"unexpected dictionary kind: {name}: {row.get('dictionaryKind')}")
        if row.get("playbackPlacementStatus") != "identityOnlyNoAudioConsumer":
            errors.append(f"unsafe placement status: {name}: {row.get('playbackPlacementStatus')}")
        event_rows = inventory.get(event_hash, [])
        if not event_rows:
            errors.append(f"Wwise Event missing: {name}: 0x{event_hash:08x}")
        dictionary_sources: list[str] = []
        skill_sources: list[str] = []
        numeric_ids: set[str] = set()
        for source_root in ("StreamingAssets", "Persistent"):
            table_path = export_root / "structured" / source_root / "Table" / "NumIdStrTable.json"
            payload = load_json(table_path)
            skill_map = ((payload.get("skill_id") or {}).get("dic") or {})
            matched_ids = {str(key) for key, value in skill_map.items() if value == name}
            if not matched_ids:
                errors.append(f"skill-id dictionary row missing: {source_root}: {name}")
            else:
                numeric_ids.update(matched_ids)
                dictionary_sources.append(table_path.relative_to(export_root).as_posix())
            skill_path = export_root / "structured" / source_root / "Data" / "Json" / "SkillData" / f"{name}.json"
            if not skill_path.is_file():
                errors.append(f"SkillData file missing: {source_root}: {name}")
            else:
                skill_sources.append(skill_path.relative_to(export_root).as_posix())
        raw_hits = serialized_hits.get(event_hash, [])
        if raw_hits:
            errors.append(f"identity-only boundary stale; serialized uint32 hash found: {name}: {raw_hits[:3]}")
        media_ids = sorted({
            int(media_id)
            for event_row in event_rows
            for media_id in event_row.get("mediaIds") or []
            if isinstance(media_id, int)
        })
        operations = sorted({
            str(action.get("operation") or "")
            for event_row in event_rows
            for action in event_row.get("actionEvidence") or []
            if isinstance(action, dict) and action.get("operation")
        })
        relation = "decodedMedia" if media_ids else "playbackActionWithoutDecodedMedia" if "play" in operations or "playEvent" in operations else "noPlaybackAction"
        relation_counts[relation] += 1
        operation_counts.update(operations)
        output_rows.append({
            **row,
            "numericSkillIdsValidated": sorted(numeric_ids, key=int),
            "dictionarySourcesValidated": dictionary_sources,
            "skillDataSourcesValidated": skill_sources,
            "serializedUint32EventHashHits": raw_hits,
            "wwiseBankPackages": sorted({
                PurePosixPath(str(event_row.get("bank") or "").replace("\\", "/")).name
                for event_row in event_rows if event_row.get("bank")
            }),
            "wwiseActionOperations": operations,
            "decodedMediaIds": media_ids,
            "audioLibraryRelation": relation,
        })
    return {
        "schemaVersion": 1,
        "summary": {
            "aliases": len(output_rows),
            "wwiseEventObjectOccurrences": sum(len(inventory.get(int(row["eventHash"]) & 0xFFFFFFFF, [])) for row in aliases),
            "audioLibraryRelations": dict(sorted(relation_counts.items())),
            "actionOperations": dict(sorted(operation_counts.items())),
            "serializedPayloadScan": scan,
            "serializedUint32EventHashHits": sum(len(rows) for rows in serialized_hits.values()),
            "validationErrors": len(errors),
        },
        "sourceFingerprint": {
            "audioIndexSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
            "audioIndexGenerated": audio_index.get("generated"),
            "persistentNumIdStrTableSha256": file_sha256(
                export_root / "structured/Persistent/Table/NumIdStrTable.json"
            ),
        },
        "evidenceBoundary": [
            "Exact skill_id dictionary strings and same-name SkillData files recover authored Event identity only when the game hash equals a current type-4 Wwise Event id.",
            "Typed Wwise Actions and media leaves prove audio-library playback topology, not which gameplay system posts the Event.",
            "The complete current SkillData/BuffData payload scan found no serialized uint32 Event hash for these aliases; filename, skill-id membership, and name equality are not promoted into a skill playback trigger.",
        ],
        "validationErrors": errors,
        "aliases": sorted(output_rows, key=lambda row: str(row.get("name") or "").casefold()),
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Skill-id Wwise Event identity audit", "",
        f"- exact identity-only aliases: `{summary['aliases']:,}`",
        f"- scanned SkillData/BuffData: `{summary['serializedPayloadScan']['files']:,}` files / `{summary['serializedPayloadScan']['bytes']:,}` bytes",
        f"- serialized uint32 Event-hash hits: `{summary['serializedUint32EventHashHits']:,}`",
        f"- validation errors: `{summary['validationErrors']:,}`", "",
        "## Audio-library relations", "",
    ]
    lines.extend(f"- `{key}`: `{value:,}`" for key, value in summary["audioLibraryRelations"].items())
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {line}" for line in report["evidenceBoundary"])
    lines.extend(["", "## Aliases", ""])
    for row in report["aliases"]:
        lines.append(
            f"- `{row['eventHashHex']}` -> `{row['name']}`; skill id "
            f"`{' / '.join(row['numericSkillIdsValidated'])}`; relation "
            f"`{row['audioLibraryRelation']}`; decoded media `{len(row['decodedMediaIds'])}`"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--json-out", type=Path, default=ROOT / "reports/story/recovery/audio/skill_id_audio_event_audit.json")
    parser.add_argument("--markdown-out", type=Path, default=ROOT / "reports/story/recovery/audio/skill_id_audio_event_audit.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index_path = args.export_root / "structured/Audio" / args.language.upper() / "index.json"
    report = build_report(load_json(index_path), args.export_root.resolve())
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_out.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_out.write_text(markdown(report), encoding="utf-8")
    print(
        f"Skill-id audio Event audit: aliases={report['summary']['aliases']:,}, "
        f"hashHits={report['summary']['serializedUint32EventHashHits']:,}, "
        f"errors={report['summary']['validationErrors']:,}"
    )
    return 1 if report["summary"]["validationErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
