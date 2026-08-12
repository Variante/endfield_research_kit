#!/usr/bin/env python3
"""Audit AudioDialog/ResponsiveDialog voice identities against Wwise Events."""

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
from build_audio_semantics import audio_hash_generator_compute  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))




def display_path(path: Path) -> str:
    try:
        value = path.relative_to(ROOT)
    except ValueError:
        value = path
    return str(value).replace("\\", "/")


def first_table(export_root: Path, name: str) -> Path:
    for source in ("StreamingAssets", "Persistent"):
        path = export_root / "structured" / source / "Table" / name
        if path.is_file():
            return path
    raise FileNotFoundError(name)


def build_report(
    audio_index: dict[str, Any],
    *,
    export_root: Path,
    metadata_path: Path | None = None,
    gameassembly_path: Path | None = None,
) -> dict[str, Any]:
    inventory_hashes: set[int] = set()
    packages_by_hash: dict[int, set[str]] = defaultdict(set)
    for row in audio_index.get("wwiseEventInventory") or []:
        if not isinstance(row, dict) or not isinstance(row.get("eventHash"), int):
            continue
        event_hash = int(row["eventHash"]) & 0xFFFFFFFF
        inventory_hashes.add(event_hash)
        package = PurePosixPath(str(row.get("bank") or "").replace("\\", "/")).name
        if package:
            packages_by_hash[event_hash].add(package)

    aliases = [
        dict(row)
        for row in audio_index.get("audioDialogWwiseEventAliases") or []
        if isinstance(row, dict)
    ]
    errors: list[str] = []
    alias_by_hash: dict[int, dict[str, Any]] = {}
    for row in aliases:
        try:
            event_hash = int(row.get("eventHash")) & 0xFFFFFFFF
            voice_id = int(row.get("voiceId")) & 0xFFFFFFFF
        except (TypeError, ValueError):
            errors.append(f"invalid alias identity: {row!r}")
            continue
        name = str(row.get("name") or "")
        if event_hash != voice_id:
            errors.append(f"voice id mismatch for {name}: 0x{voice_id:08x} != 0x{event_hash:08x}")
        if audio_hash_generator_compute(name) != event_hash:
            errors.append(f"path hash mismatch for {name}: expected 0x{event_hash:08x}")
        if event_hash not in inventory_hashes:
            errors.append(f"Wwise Event missing for {name}: 0x{event_hash:08x}")
        previous = alias_by_hash.get(event_hash)
        if previous and str(previous.get("name") or "").casefold() != name.casefold():
            errors.append(f"alias collision for 0x{event_hash:08x}: {previous.get('name')} / {name}")
        alias_by_hash[event_hash] = row

    named_evidence_hashes = {
        int(row.get("eventHash")) & 0xFFFFFFFF
        for row in audio_index.get("eventEvidence") or []
        if isinstance(row, dict)
        and isinstance(row.get("eventHash"), int)
        and not str(row.get("eventId") or "").startswith("hashed-event:0x")
    }

    responsive_path = first_table(export_root, "ResponsiveDialog.json")
    responsive = load_json(responsive_path)
    responsive_occurrences: list[dict[str, Any]] = []
    responsive_event_hashes: set[int] = set()
    for sentence_type, sentence_row in responsive.items():
        speakers = sentence_row.get("speakers") if isinstance(sentence_row, dict) else None
        for speaker_id, speaker_row in (speakers.items() if isinstance(speakers, dict) else []):
            triggers = speaker_row.get("triggers") if isinstance(speaker_row, dict) else None
            for trigger_key, trigger_row in (triggers.items() if isinstance(triggers, dict) else []):
                if not isinstance(trigger_row, dict):
                    continue
                for response_index, raw_voice_id in enumerate(trigger_row.get("response") or []):
                    if not isinstance(raw_voice_id, int):
                        continue
                    event_hash = raw_voice_id & 0xFFFFFFFF
                    alias = alias_by_hash.get(event_hash)
                    if alias is None:
                        continue
                    responsive_event_hashes.add(event_hash)
                    responsive_occurrences.append({
                        "eventHash": event_hash,
                        "name": alias.get("name"),
                        "voiceId": raw_voice_id,
                        "sentenceType": str(sentence_type),
                        "speakerId": str(speaker_id),
                        "triggerKey": str(trigger_key),
                        "triggerTypeId": trigger_row.get("triggerTypeId"),
                        "responseIndex": response_index,
                    })

    tone_path = first_table(export_root, "AudioVoTone.json")
    tones = load_json(tone_path)
    tone_occurrences: list[dict[str, Any]] = []
    tone_event_hashes: set[int] = set()
    for raw_base_id, tone_row in tones.items():
        if not isinstance(tone_row, dict):
            continue
        for variant_index, raw_voice_id in enumerate(tone_row.get("toneList") or []):
            if not isinstance(raw_voice_id, int):
                continue
            event_hash = raw_voice_id & 0xFFFFFFFF
            alias = alias_by_hash.get(event_hash)
            if alias is None:
                continue
            tone_event_hashes.add(event_hash)
            tone_occurrences.append({
                "eventHash": event_hash,
                "name": alias.get("name"),
                "baseVoiceId": int(raw_base_id),
                "variantVoiceId": raw_voice_id,
                "variantIndex": variant_index,
            })

    package_counts = Counter(
        package
        for event_hash in alias_by_hash
        for package in packages_by_hash.get(event_hash, set())
    )
    responsive_counts = Counter(row["eventHash"] for row in responsive_occurrences)
    tone_counts = Counter(row["eventHash"] for row in tone_occurrences)
    for row in aliases:
        event_hash = int(row["eventHash"]) & 0xFFFFFFFF
        row["bankPackages"] = sorted(packages_by_hash.get(event_hash, set()))
        row["wasPreviouslyNamed"] = event_hash in named_evidence_hashes
        row["responsiveDialogOccurrenceCount"] = responsive_counts[event_hash]
        row["toneVariantOccurrenceCount"] = tone_counts[event_hash]

    provenance: dict[str, Any] = {
        "audioIndexSchemaVersion": audio_index.get("eventEvidenceSchemaVersion"),
        "responsiveDialog": display_path(responsive_path),
        "audioVoTone": display_path(tone_path),
        "runtimeMetadataReport": "reports/story/recovery/audio/voice_response_runtime_metadata.json",
        "runtimeGameAssemblyReport": "reports/story/recovery/audio/voice_response_runtime_gameassembly.json",
    }
    for label, path in (("globalMetadata", metadata_path), ("gameAssembly", gameassembly_path)):
        if path is not None and path.is_file():
            provenance[label] = {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256(path)}

    summary = {
        "wwiseEventObjectOccurrences": len(audio_index.get("wwiseEventInventory") or []),
        "wwiseEventObjectHashes": len(inventory_hashes),
        "audioDialogWwiseEventAliases": len(alias_by_hash),
        "newlyRecoveredEventNames": len(set(alias_by_hash) - named_evidence_hashes),
        "previouslyNamedAliases": len(set(alias_by_hash) & named_evidence_hashes),
        "responsiveDialogWwiseEvents": len(responsive_event_hashes),
        "responsiveDialogOccurrences": len(responsive_occurrences),
        "voiceToneVariantWwiseEvents": len(tone_event_hashes),
        "voiceToneVariantOccurrences": len(tone_occurrences),
        "bankPackages": dict(sorted(package_counts.items())),
        "validationErrors": len(errors),
    }
    return {
        "schemaVersion": 1,
        "summary": summary,
        "provenance": provenance,
        "evidenceBoundary": [
            "An alias is accepted only when AudioHashGenerator(path) equals the signed AudioDialog voice id and a current complete type-4 Wwise Event id.",
            "ResponsiveDialog response membership proves an authored possible response for that speaker/trigger family; probability, cooldown, band limit, runtime state, and the chosen response remain unobserved.",
            "AudioVoTone membership proves a possible voice-id substitution through ApplyRandomVoiceTone/TryReplaceVoiceIdWithTone, not that the variant was selected live.",
            "VoicePlayer has distinct Event and External playback paths; an AudioDialog definition alone is not treated as a playback location.",
        ],
        "validationErrors": errors,
        "aliases": aliases,
        "responsiveDialogOccurrences": responsive_occurrences,
        "voiceToneVariantOccurrences": tone_occurrences,
    }


def markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Voice response audio Event audit",
        "",
        f"- complete Wwise Event inventory: `{summary['wwiseEventObjectOccurrences']:,}` occurrences / `{summary['wwiseEventObjectHashes']:,}` unique hashes",
        f"- exact AudioDialog path/voice-id/Wwise aliases: `{summary['audioDialogWwiseEventAliases']:,}`",
        f"- newly recovered Event names: `{summary['newlyRecoveredEventNames']:,}`",
        f"- aliases already named by another source: `{summary['previouslyNamedAliases']:,}`",
        f"- aliases in ResponsiveDialog trigger families: `{summary['responsiveDialogWwiseEvents']:,}` Events / `{summary['responsiveDialogOccurrences']:,}` authored placements",
        f"- aliases in AudioVoTone: `{summary['voiceToneVariantWwiseEvents']:,}` Events / `{summary['voiceToneVariantOccurrences']:,}` variants",
        f"- validation errors: `{summary['validationErrors']}`",
        "",
        "## Bank packages",
        "",
    ]
    lines.extend(
        f"- `{name}`: `{count:,}` aliases"
        for name, count in summary["bankPackages"].items()
    )
    lines.extend(["", "## Evidence boundary", ""])
    lines.extend(f"- {value}" for value in report["evidenceBoundary"])
    lines.extend(["", "## Recovered-name samples", ""])
    for row in report["aliases"][:40]:
        lines.append(
            f"- `{row['eventHashHex']}` → `{row['name']}`; "
            f"ResponsiveDialog `{row['responsiveDialogOccurrenceCount']}`, "
            f"tone `{row['toneVariantOccurrenceCount']}`"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--language", default="CN")
    parser.add_argument("--game-root", type=Path, default=resolve_installed_game_data_root())
    parser.add_argument("--out", type=Path, default=ROOT / "reports/story/recovery/audio/voice_response_audio_event_audit.json")
    parser.add_argument("--markdown", type=Path, default=ROOT / "reports/story/recovery/audio/voice_response_audio_event_audit.md")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    index_path = args.export_root / "structured" / "Audio" / args.language.upper() / "index.json"
    report = build_report(
        load_json(index_path),
        export_root=args.export_root,
        metadata_path=args.game_root / "il2cpp_data/Metadata/global-metadata.dat",
        gameassembly_path=args.game_root.parent / "GameAssembly.dll",
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown.write_text(markdown(report), encoding="utf-8")
    summary = report["summary"]
    print(
        "Voice response audio Event audit: "
        f"aliases={summary['audioDialogWwiseEventAliases']:,}, "
        f"newNames={summary['newlyRecoveredEventNames']:,}, "
        f"responsiveEvents={summary['responsiveDialogWwiseEvents']:,}, "
        f"errors={summary['validationErrors']}"
    )
    return 1 if summary["validationErrors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
