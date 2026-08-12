#!/usr/bin/env python3
"""Audit stale numeric External Source paths against current AudioDialog paths."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
BUILD_AUDIO_PATH = ROOT / "scripts/build_audio.py"
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_JSON = ROOT / "reports/story/recovery/audio/audio_dialog_external_copy_audit.json"
DEFAULT_MD = ROOT / "reports/story/recovery/audio/audio_dialog_external_copy_audit.md"


def load_build_audio():
    spec = importlib.util.spec_from_file_location("audio_external_copy_build_audio", BUILD_AUDIO_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def load_audio_dialog_rows(export_root: Path) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for source in ("StreamingAssets", "Persistent"):
        path = export_root / f"structured/{source}/Table/AudioDialog.json"
        if not path.is_file():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            rows.update({str(key): value for key, value in payload.items() if isinstance(value, dict)})
    return rows


def build_audit(export_root: Path, language: str = "CN") -> dict[str, Any]:
    build_audio = load_build_audio()
    language = language.upper()
    language_info = build_audio.LANGUAGES[language]
    audio_root = export_root / "structured/Audio"
    language_root = audio_root / language
    dialog_rows = load_audio_dialog_rows(export_root)
    by_external_id: dict[int, tuple[str, dict[str, Any]]] = {}
    for row_key, row in dialog_rows.items():
        dialog_path = str(row.get("path") or "").strip()
        if not dialog_path:
            continue
        external_id = build_audio.audio_dialog_external_media_id(
            dialog_path, language_info["dumper"]
        )
        by_external_id[external_id] = (row_key, row)

    candidates = sorted(
        path for path in (language_root / "wwise/unknown").glob("*")
        if path.is_file()
        and path.suffix.lower() in build_audio.AUDIO_EXTENSIONS
        and path.stem.isdigit()
        and int(path.stem) > 0xFFFFFFFF
    )
    records: list[dict[str, Any]] = []
    validation_errors: list[dict[str, Any]] = []
    for path in candidates:
        external_id = int(path.stem)
        match = by_external_id.get(external_id)
        recovered_identity = (
            build_audio.RECOVERED_EXTERNAL_MEDIA_IDENTITIES.get(language) or {}
        ).get(external_id)
        record: dict[str, Any] = {
            "externalMediaId": external_id,
            "externalMediaIdHex": f"0x{external_id:016x}",
            "numericPath": path.relative_to(audio_root).as_posix(),
            "numericBytes": path.stat().st_size,
            "identityStatus": (
                "currentAudioDialogPathHash"
                if match else "boundedRecoveredAuthoredPathHash"
                if recovered_identity else "absentFromCurrentAudioDialog"
            ),
        }
        if match:
            row_key, row = match
            dialog_path = str(row.get("path") or "")
            canonical_rel = build_audio.audio_rel_for_dialog_path(dialog_path, path.suffix)
            canonical_path = language_root / Path(*Path(canonical_rel).parts)
            record.update({
                "audioDialogKey": int(row_key) if row_key.lstrip("-").isdigit() else row_key,
                "audioDialogPath": dialog_path,
                "canonicalPath": canonical_path.relative_to(audio_root).as_posix(),
                "canonicalFilePresent": canonical_path.is_file(),
                "speakerChannel": str(row.get("speakerChannel") or ""),
                "voType": row.get("voType"),
            })
            if canonical_path.is_file():
                record["canonicalBytes"] = canonical_path.stat().st_size
                record["numericSha256"] = build_audio.file_sha256(path)
                record["canonicalSha256"] = build_audio.file_sha256(canonical_path)
                record["contentStatus"] = (
                    "byteIdenticalCurrentAuthoredCopy"
                    if record["numericSha256"] == record["canonicalSha256"]
                    else "differentBytesForSameAuthoredExternalId"
                )
            else:
                record["contentStatus"] = "canonicalAuthoredFileMissing"
            if record["contentStatus"] != "byteIdenticalCurrentAuthoredCopy":
                validation_errors.append({
                    "externalMediaId": external_id,
                    "check": "exactAuthoredExternalCopy",
                    "expected": "byteIdenticalCurrentAuthoredCopy",
                    "actual": record["contentStatus"],
                    "sourcePath": record["numericPath"],
                    "audioDialogPath": dialog_path,
                })
        elif recovered_identity:
            recovered_path = str(recovered_identity["path"])
            recovered_hash = build_audio.audio_dialog_external_media_id(
                recovered_path, language_info["dumper"]
            )
            record.update({
                "recoveredAudioId": recovered_identity["audioId"],
                "recoveredAuthoredPath": recovered_path,
                "recoveredPathHash": recovered_hash,
                "identityEvidence": recovered_identity["evidence"],
                "playbackPlacementStatus": recovered_identity["playbackPlacementStatus"],
            })
            if recovered_hash != external_id:
                validation_errors.append({
                    "externalMediaId": external_id,
                    "check": "boundedRecoveredAuthoredPathHash",
                    "expected": external_id,
                    "actual": recovered_hash,
                    "sourcePath": record["numericPath"],
                    "recoveredAuthoredPath": recovered_path,
                })
        records.append(record)

    status_counts: dict[str, int] = {}
    content_counts: dict[str, int] = {}
    for row in records:
        status = str(row.get("identityStatus") or "unknown")
        content = str(row.get("contentStatus") or "notCompared")
        status_counts[status] = status_counts.get(status, 0) + 1
        content_counts[content] = content_counts.get(content, 0) + 1
    return {
        "schemaVersion": 1,
        "language": language,
        "summary": {
            "externalNumericPathCount": len(records),
            "currentAudioDialogPathHashCount": status_counts.get("currentAudioDialogPathHash", 0),
            "byteIdenticalCurrentAuthoredCopyCount": content_counts.get("byteIdenticalCurrentAuthoredCopy", 0),
            "boundedRecoveredAuthoredPathHashCount": status_counts.get("boundedRecoveredAuthoredPathHash", 0),
            "absentFromCurrentAudioDialogCount": status_counts.get("absentFromCurrentAudioDialog", 0),
            "validationErrorCount": len(validation_errors),
            "identityStatusCounts": status_counts,
            "contentStatusCounts": content_counts,
        },
        "evidenceBoundary": (
            "The 64-bit id is accepted only when it exactly equals FNV-1a-64 of "
            "voice/<language>/<AudioDialog.path lowercase>. Suppression additionally "
            "requires the current canonical file to have identical SHA-256 bytes. An "
            "identity absent from current AudioDialog is recovered only when a bounded "
            "authored-path namespace has one exact hash preimage; this does not establish "
            "a dialog row, speaker, trigger, or playback location."
        ),
        "validationErrors": validation_errors,
        "records": records,
    }


def write_markdown(payload: dict[str, Any], path: Path) -> None:
    summary = payload["summary"]
    lines = [
        "# AudioDialog External Copy Audit",
        "",
        f"- numeric External Source paths: `{summary['externalNumericPathCount']}`",
        f"- exact current AudioDialog path hashes: `{summary['currentAudioDialogPathHashCount']}`",
        f"- byte-identical canonical copies: `{summary['byteIdenticalCurrentAuthoredCopyCount']}`",
        f"- bounded recovered authored paths: `{summary['boundedRecoveredAuthoredPathHashCount']}`",
        f"- absent from current AudioDialog: `{summary['absentFromCurrentAudioDialogCount']}`",
        f"- validation errors: `{summary['validationErrorCount']}`",
        "",
        "## Evidence boundary",
        "",
        payload["evidenceBoundary"],
        "",
        "## Current-table gaps",
        "",
        "| External id | Numeric path | Bytes |",
        "| --- | --- | ---: |",
    ]
    unmatched = [row for row in payload["records"] if row["identityStatus"] != "currentAudioDialogPathHash"]
    for row in unmatched:
        lines.append(
            f"| `{row['externalMediaId']}` | `{row['numericPath']}` | `{row['numericBytes']}` |"
        )
    if not unmatched:
        lines.append("| - | - | - |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT_ROOT)
    parser.add_argument("--language", default="CN")
    parser.add_argument("--json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MD)
    args = parser.parse_args()
    payload = build_audit(args.export_root.resolve(), args.language)
    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_markdown(payload, args.markdown)
    summary = payload["summary"]
    print(
        "AudioDialog external copy audit: "
        f"paths={summary['externalNumericPathCount']}, "
        f"exactCopies={summary['byteIdenticalCurrentAuthoredCopyCount']}, "
        f"boundedIdentities={summary['boundedRecoveredAuthoredPathHashCount']}, "
        f"unmatched={summary['absentFromCurrentAudioDialogCount']}, "
        f"errors={summary['validationErrorCount']}"
    )
    return 1 if summary["validationErrorCount"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
