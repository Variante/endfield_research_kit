#!/usr/bin/env python3
"""Validate typed voice-table strings promoted to current Wwise Event names."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from common import (  # noqa: E402
    resolve_installed_game_data_root,
    sha256_file as sha256,
)
from build_audio import VOICE_TABLE_WWISE_EVENT_FIELDS  # noqa: E402
from build_audio_semantics import audio_hash_generator_compute  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))




def build_report(
    audio_index: dict[str, Any],
    *,
    metadata_path: Path | None = None,
    gameassembly_path: Path | None = None,
) -> dict[str, Any]:
    inventory_by_hash: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in audio_index.get("wwiseEventInventory") or []:
        if isinstance(row, dict) and isinstance(row.get("eventHash"), int):
            inventory_by_hash[int(row["eventHash"]) & 0xFFFFFFFF].append(row)
    previously_named = {
        int(row["eventHash"]) & 0xFFFFFFFF
        for row in audio_index.get("eventEvidence") or []
        if isinstance(row, dict)
        and isinstance(row.get("eventHash"), int)
        and not str(row.get("eventId") or "").startswith("hashed-event:0x")
    }
    allowed = {
        (table, field): spec[0]
        for table, fields in VOICE_TABLE_WWISE_EVENT_FIELDS.items()
        for field, spec in fields.items()
    }
    errors: list[str] = []
    seen: dict[int, str] = {}
    aliases: list[dict[str, Any]] = []
    route_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    package_counts: Counter[str] = Counter()
    media_relation_counts: Counter[str] = Counter()
    for raw in audio_index.get("voiceTableWwiseEventAliases") or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            errors.append(f"invalid alias identity: {row!r}")
            continue
        name = str(row.get("name") or "").strip()
        if audio_hash_generator_compute(name) != event_hash:
            errors.append(f"name hash mismatch for {name}: expected 0x{event_hash:08x}")
        if event_hash not in inventory_by_hash:
            errors.append(f"Wwise Event missing for {name}: 0x{event_hash:08x}")
        if event_hash in seen and seen[event_hash].casefold() != name.casefold():
            errors.append(f"alias collision for 0x{event_hash:08x}: {seen[event_hash]} / {name}")
        seen[event_hash] = name
        for usage in row.get("usages") or []:
            if not isinstance(usage, dict):
                continue
            key = (str(usage.get("table") or ""), str(usage.get("field") or ""))
            route = str(usage.get("routeKind") or "")
            if key not in allowed:
                errors.append(f"unapproved typed field for {name}: {key[0]}.{key[1]}")
            elif allowed[key] != route:
                errors.append(f"route mismatch for {name}: {route} != {allowed[key]}")
            route_counts[route] += 1
            field_counts[f"{key[0]}.{key[1]}"] += int(usage.get("occurrenceCount") or 0)
        inventory = inventory_by_hash.get(event_hash, [])
        packages = sorted({
            PurePosixPath(str(item.get("bank") or "").replace("\\", "/")).name
            for item in inventory if item.get("bank")
        })
        has_media = any(item.get("mediaIds") for item in inventory)
        has_external = any(
            any(str(source.get("sourceKind") or "").startswith("externalSource") for source in item.get("nonMediaSourceEvidence") or [])
            for item in inventory
        )
        relation = "decodedMedia" if has_media else "externalSource" if has_external else "noRecoveredSource"
        media_relation_counts[relation] += 1
        for package in packages:
            package_counts[package] += 1
        row["bankPackages"] = packages
        row["wasPreviouslyNamed"] = event_hash in previously_named
        row["audioLibraryRelation"] = relation
        aliases.append(row)

    provenance: dict[str, Any] = {
        "audioIndexSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
        "metadataEvidence": "scratch/reverse_engineering/audio_event_string_hash_scan/voice_exact_metadata.md",
        "nativeEvidence": "scratch/reverse_engineering/audio_event_string_hash_scan/voice_select_gameassembly.md",
    }
    for label, path in (("globalMetadata", metadata_path), ("gameAssembly", gameassembly_path)):
        if path is not None and path.is_file():
            provenance[label] = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}
    summary = {
        "wwiseEventObjectOccurrences": sum(len(rows) for rows in inventory_by_hash.values()),
        "wwiseEventObjectHashes": len(inventory_by_hash),
        "voiceTableWwiseEventAliases": len(aliases),
        "newlyRecoveredEventNames": sum(not row["wasPreviouslyNamed"] for row in aliases),
        "previouslyNamedAliases": sum(bool(row["wasPreviouslyNamed"]) for row in aliases),
        "routeKinds": dict(sorted(route_counts.items())),
        "fieldOccurrences": dict(sorted(field_counts.items())),
        "bankPackages": dict(sorted(package_counts.items())),
        "audioLibraryRelations": dict(sorted(media_relation_counts.items())),
        "validationErrors": len(errors),
    }
    return {
        "schemaVersion": 1,
        "summary": summary,
        "provenance": provenance,
        "evidenceBoundary": [
            "Only whitelisted fields whose current metadata getters declare Wwise Event, override, or template semantics are admitted.",
            "Each admitted string must hash exactly to a type-4 Event id in the current complete Wwise bank inventory; conflicting names fail closed.",
            "VoiceManager/VoiceUtilsInternal/VoicePlayer prove the selection and playback route, but no live branch choice or audible playback is observed.",
            "ResponsiveTriggers.eventTemplate is an authored possible response template, not proof that a response occurred.",
        ],
        "validationErrors": errors,
        "aliases": aliases,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Typed voice-table Wwise Event audit", "",
        f"- complete Wwise Event inventory: `{summary['wwiseEventObjectOccurrences']:,}` occurrences / `{summary['wwiseEventObjectHashes']:,}` unique hashes",
        f"- exact typed voice-table aliases: `{summary['voiceTableWwiseEventAliases']:,}`",
        f"- newly recovered Event names: `{summary['newlyRecoveredEventNames']:,}`",
        f"- aliases already named by another source: `{summary['previouslyNamedAliases']:,}`",
        f"- validation errors: `{summary['validationErrors']}`", "",
        "## Authored fields", "",
    ]
    lines.extend(f"- `{name}`: `{count:,}` occurrences" for name, count in summary["fieldOccurrences"].items())
    lines.extend(["", "## Audio-library relations", ""])
    lines.extend(f"- `{name}`: `{count:,}` Events" for name, count in summary["audioLibraryRelations"].items())
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {value}" for value in report["evidenceBoundary"])
    lines.extend(["", "## Recovered-name samples", ""])
    for row in report["aliases"][:40]:
        lines.append(f"- `{row['eventHashHex']}` -> `{row['name']}`; `{row['audioLibraryRelation']}`")
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--game-root", type=Path, default=resolve_installed_game_data_root())
    parser.add_argument("--out", type=Path, default=ROOT / "reports/story/recovery/audio/voice_table_audio_event_audit.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports/story/recovery/audio/voice_table_audio_event_audit.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = build_report(
        load_json(args.export_root / "structured" / "Audio" / args.language.upper() / "index.json"),
        metadata_path=args.game_root / "il2cpp_data/Metadata/global-metadata.dat",
        gameassembly_path=args.game_root.parent / "GameAssembly.dll",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    summary = report["summary"]
    print(f"Typed voice-table Event audit: aliases={summary['voiceTableWwiseEventAliases']:,}, newNames={summary['newlyRecoveredEventNames']:,}, errors={summary['validationErrors']}")
    return 1 if summary["validationErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
