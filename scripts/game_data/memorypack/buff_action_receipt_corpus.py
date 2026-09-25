"""Replay selected named Buff action receipts against an authenticated corpus.

This is a supplemental, fail-closed action inventory.  The input Buff corpus
still owns the outer frame and its unresolved recursive naming obligations;
neither this sweep nor a closed action span promotes whole BuffData.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from scripts.common import (
    GLOBAL_METADATA_REL, ROOT, canonical_json_sha256,
    resolve_installed_native_inputs, sha256_file_upper,
)
from scripts.game_data.memorypack import (
    buff_create_buff_action_receipt as create_buff,
    buff_finish_buff_advanced_action_receipt as finish_buff,
)


SCHEMA = "endfield.buff-action-receipt-corpus.v1"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT_JSON = REPORTS_ROOT / "animestudio/buff_action_receipts_current_latest.json"
DEFAULT_OUTPUT_MD = REPORTS_ROOT / "animestudio/buff_action_receipts_current_latest.md"
_SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
_ROUTES = {
    create_buff.TAG: create_buff.decode_create_buff_action_receipt,
    finish_buff.TAG: finish_buff.decode_finish_buff_advanced_action_receipt,
}


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffActionReceiptCorpus:{check}:source={source}; {detail}")


def _selected_candidate(row: dict[str, Any], source: str) -> dict[str, Any]:
    candidates = row.get("candidates")
    selected = [c for c in candidates or [] if c.get("readerAcceptedThroughEof") is True]
    if row.get("candidateCount") != 1 or len(selected) != 1:
        _fail("candidate-identity", source=source, detail="requires one accepted EOF candidate")
    return selected[0]


def _has_reviewed_action_frame(candidate: dict[str, Any], source: str) -> bool:
    event = candidate.get("currentEventPrefix")
    root = candidate.get("currentRootContinuation")
    receipt = candidate.get("namedSchemaReceipt")
    if event is None and root is None and receipt is None:
        return False
    if (
        not isinstance(event, dict) or event.get("status") != "supported-prefix"
        or not isinstance(root, dict) or root.get("status") != "supported-prefix"
        or not isinstance(receipt, dict)
    ):
        _fail("candidate-action-frame", source=source,
              detail="partial or unsupported action profile")
    return True


def _union_records(candidate: dict[str, Any], source: str, length: int) -> list[dict[str, int]]:
    records: list[dict[str, int]] = []
    seen: set[tuple[int, int, int]] = set()
    for profile_name in ("currentEventPrefix", "currentRootContinuation"):
        profile = candidate[profile_name]
        for row in profile.get("completedRecords", []):
            if row.get("kind") != "union":
                continue
            start, end, tag = row.get("start"), row.get("end"), row.get("tag")
            if (
                type(start) is not int or type(end) is not int or type(tag) is not int
                or not 0 <= start < end <= length
            ):
                _fail("union-range", source=source, detail=str((start, end, tag)))
            identity = (start, end, tag)
            if identity in seen:
                _fail("duplicate-union", source=source, detail=str(identity))
            seen.add(identity)
            records.append({"start": start, "end": end, "tag": tag})
    return sorted(records, key=lambda row: (row["start"], row["end"], row["tag"]))


def _sole_target_projection(candidate: dict[str, Any], length: int) -> int | None:
    fields = (candidate["currentEventPrefix"] or {}).get("namedFields", [])
    field = next((row for row in fields if row.get("name") == "abilityEventAction"), None)
    if not field or not 0 <= field["start"] < field["end"] <= length:
        return None
    unions = [row for row in candidate["currentEventPrefix"].get("completedRecords", [])
              if row.get("kind") == "union" and field["start"] <= row.get("start", -1) < field["end"]]
    return unions[0]["tag"] if len(unions) == 1 and unions[0]["tag"] in _ROUTES else None


def build_receipt_report(
    buff_report: dict[str, Any],
    *,
    export_root: Path,
    expected_input_set_sha256: str,
    native_validations: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Join every report identity to exported bytes, then replay both routes."""
    summary = buff_report.get("summary") or {}
    rows = buff_report.get("files")
    if (
        buff_report.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or buff_report.get("status") != "complete"
        or buff_report.get("publicationEligible") is not True
        or buff_report.get("wholeSchemaExact") is not False
        or not isinstance(rows, list)
        or summary.get("filesSelected") != len(rows)
        or summary.get("filesUnique") != len(rows)
        or summary.get("filesFailed") != 0
        or summary.get("filesAmbiguous") != 0
    ):
        _fail("report-not-complete", detail="requires a complete unique Buff VFS census")
    if (
        not isinstance(expected_input_set_sha256, str)
        or not re.fullmatch(r"[0-9A-Fa-f]{64}", expected_input_set_sha256)
        or buff_report.get("inputSetSha256", "").upper() != expected_input_set_sha256.upper()
    ):
        _fail("input-set-mismatch")
    if canonical_json_sha256([
        {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
        for row in rows
    ]) != buff_report.get("identitySetSha256"):
        _fail("identity-set-mismatch")
    if set(native_validations) != set(_ROUTES) or any(
        native_validations[tag].get("status") != "validated"
        or native_validations[tag].get("unionTag") != tag for tag in _ROUTES
    ):
        _fail("native-gate")

    export_root = Path(export_root).resolve()
    detail: list[dict[str, Any]] = []
    counts: Counter[int] = Counter()
    file_counts: Counter[int] = Counter()
    bytes_by_tag: Counter[int] = Counter()
    sole_counts: Counter[int] = Counter()
    no_action_frame: list[str] = []
    source_names: set[str] = set()
    for row in rows:
        identity = row.get("identity") or {}
        source = identity.get("fileName", "")
        if (
            not isinstance(source, str) or not _SOURCE_PATTERN.fullmatch(source)
            or identity.get("virtualPath") != source
            or identity.get("inputSetSha256", "").upper() != expected_input_set_sha256.upper()
            or identity.get("status") != "verified"
            or identity.get("boundaryStatus") != "boundary_verified"
            or source in source_names
        ):
            _fail("source-identity", source=str(source))
        source_names.add(source)
        path = export_root / "game" / source.removeprefix("Data/")
        try:
            data = path.read_bytes()
        except OSError as exc:
            _fail("source-unreadable", source=source, detail=str(exc))
        digest = hashlib.sha256(data).hexdigest().upper()
        if (
            type(identity.get("length")) is not int
            or len(data) != identity["length"]
            or identity.get("actualBytesRead") != len(data)
            or digest != row.get("logicalSha256")
            or hashlib.md5(data).hexdigest().upper()
            != identity.get("recomputedFileDataMd5", "").upper()
        ):
            _fail("source-hash-or-length", source=source)
        candidate = _selected_candidate(row, source)
        if not _has_reviewed_action_frame(candidate, source):
            no_action_frame.append(source)
            continue
        unions = _union_records(candidate, source, len(data))
        receipts = []
        for union in unions:
            tag = union["tag"]
            if tag not in _ROUTES:
                continue
            receipt = _ROUTES[tag](
                data, source=source, logical_sha256=digest,
                start=union["start"], end=union["end"],
                native_validation=native_validations[tag],
            )
            if (
                receipt.get("wholeActionByteSpanExact") is not True
                or receipt.get("recursiveNamedSchemaExact") is not False
                or receipt.get("wholeBuffDataExact") is not False
            ):
                _fail("receipt-boundary", source=source, detail=f"tag=0x{tag:04X}")
            receipts.append(receipt)
            counts[tag] += 1
            bytes_by_tag[tag] += union["end"] - union["start"]
        for tag in {receipt["tag"] for receipt in receipts}:
            file_counts[tag] += 1
        sole = _sole_target_projection(candidate, len(data))
        if sole is not None:
            sole_counts[sole] += 1
        if receipts:
            detail.append({"source": source, "logicalSha256": digest,
                           "actions": receipts})

    per_tag = {
        f"0x{tag:04X}": {
            "actionSpans": counts[tag],
            "files": file_counts[tag],
            "actionBytes": bytes_by_tag[tag],
            "soleAbilityEventActionFiles": sole_counts[tag],
        }
        for tag in sorted(_ROUTES)
    }
    return {
        "schema": SCHEMA,
        "status": "complete",
        "publicationEligible": True,
        "wholeBuffDataExact": False,
        "inputSetSha256": expected_input_set_sha256.upper(),
        "sourceIdentitySetSha256": buff_report["identitySetSha256"],
        "exportRoot": str(export_root),
        "summary": {
            "sourceFilesVerified": len(rows),
            "rowsWithoutReviewedActionFrame": len(no_action_frame),
            "noActionFrameExamples": no_action_frame[:8],
            "filesWithNamedActionReceipts": len(detail),
            "byTag": per_tag,
        },
        "nativeInputsByTag": {
            f"0x{tag:04X}": native_validations[tag]["nativeInputs"]
            for tag in sorted(_ROUTES)
        },
        "files": detail,
        "evidenceBoundary": (
            "Every source identity is rejoined to the completed authenticated Buff VFS "
            "census by path, length, MD5 and logical SHA256. Selected native contracts "
            "name only reached 0x0092/0x00B4 action wrapper fields at exact spans. "
            "Nested profiles and the complete BuffData schema remain unproved."
        ),
    }


@contextmanager
def _selected_game_root(game_root: Path):
    root = Path(game_root).resolve()
    assembly = root.parent / "GameAssembly.dll"
    metadata = root / GLOBAL_METADATA_REL
    unityplayer = root.parent / "UnityPlayer.dll"
    if not all(path.is_file() for path in (assembly, metadata, unityplayer)):
        _fail("selected-native-input-missing", detail=str(root))
    old = os.environ.get("ENDFIELD_GAME_ROOT")
    os.environ["ENDFIELD_GAME_ROOT"] = str(root)
    try:
        actual_assembly, actual_metadata = resolve_installed_native_inputs()
        if actual_assembly.resolve() != assembly or actual_metadata.resolve() != metadata:
            _fail("selected-native-path-drift", detail=str(root))
        yield {"GameAssembly.dll": assembly, "global-metadata.dat": metadata,
               "UnityPlayer.dll": unityplayer}
    finally:
        if old is None:
            os.environ.pop("ENDFIELD_GAME_ROOT", None)
        else:
            os.environ["ENDFIELD_GAME_ROOT"] = old


def _validate_selected_native(game_root: Path) -> dict[int, dict[str, Any]]:
    with _selected_game_root(game_root) as paths:
        validations = {
            create_buff.TAG: create_buff.validate_current_native_contract(),
            finish_buff.TAG: finish_buff.validate_current_native_contract(),
        }
        for tag, validation in validations.items():
            if validation.get("status") != "validated" or validation.get("unionTag") != tag:
                _fail("native-gate", detail=f"tag=0x{tag:04X}")
            for name, path in paths.items():
                if sha256_file_upper(path) != validation["nativeInputs"][name]:
                    _fail("selected-native-hash-drift", detail=f"tag=0x{tag:04X} {name}")
        return validations


def _reports_path(path: Path) -> Path:
    resolved = Path(path).resolve()
    if not resolved.is_relative_to(REPORTS_ROOT.resolve()):
        _fail("output-outside-reports", detail=str(resolved))
    return resolved


def _atomic_text(path: Path, value: str) -> None:
    path = _reports_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", newline="\n",
                                         dir=path.parent, suffix=".tmp", delete=False) as stream:
            stream.write(value)
            temporary = Path(stream.name)
        os.replace(temporary, path)
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Selected installed Endfield_Data directory")
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_OUTPUT_MD)
    args = parser.parse_args(argv)
    try:
        output_json, output_md = _reports_path(args.output_json), _reports_path(args.output_md)
        raw = args.buff_report.read_bytes()
        source_report = json.loads(raw)
        validations = _validate_selected_native(args.game_root)
        report = build_receipt_report(
            source_report, export_root=args.export_root,
            expected_input_set_sha256=args.expected_input_set_sha256,
            native_validations=validations,
        )
        report["buffReportSha256"] = hashlib.sha256(raw).hexdigest().upper()
        report["buffReportPath"] = str(args.buff_report.resolve())
        _atomic_text(output_json, json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        lines = ["# BuffData named action receipts", "",
                 f"Input set: `{report['inputSetSha256']}`", "",
                 f"Verified source files: {report['summary']['sourceFilesVerified']}",
                 f"Files with receipts: {report['summary']['filesWithNamedActionReceipts']}", ""]
        for tag, count in report["summary"]["byTag"].items():
            lines.append(f"- {tag}: {count['actionSpans']} action spans in {count['files']} files; "
                         f"{count['soleAbilityEventActionFiles']} files have this as their sole "
                         "abilityEventAction union")
        lines.extend(["", report["evidenceBoundary"], ""])
        _atomic_text(output_md, "\n".join(lines))
        print(json.dumps({"status": "complete", "summary": report["summary"]}))
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
