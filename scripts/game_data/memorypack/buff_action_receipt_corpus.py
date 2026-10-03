"""Replay selected named Buff action receipts against an authenticated corpus.

This is a supplemental, fail-closed action inventory.  The input Buff corpus
still owns the outer frame and its unresolved recursive naming obligations;
neither this sweep nor a closed action span promotes whole BuffData.

The gate rechecks every completed corpus identity against the matching
exported logical bytes and the selected native inputs before using its
eight shared named action adapters. Physical Buff dispatcher tags:

- ``0x0050`` seven-member ``CompareFloat.Data``;
- ``0x0092`` 19-member ``CreateBuffActionData``;
- ``0x00A2`` 18-member ``EffectActionData``;
- ``0x00B4`` 13-member ``FinishBuffAdvanced``;
- ``0x00C9`` eight-member ``IfElseActionData``;
- ``0x00EC`` ten-member ``ModifyDynamicBlackboard.Data``;
- ``0x011F`` eight-member ``RaiseTrainLevelEvent.Data``;
- ``0x0159`` seven-member ``SetSuperArmorAction.Data``.

Generated member order and the selected readers name each reached wrapper
field and close the exact reported action span, whether the action occurs in
``abilityEventAction`` or in the supported root continuation. Adapters
additionally check generated field kinds against source read kinds and
nested declared types against the source's direct call contexts where their
modules say so. The field-five ``buffEventAction`` frontier contains many
distinct action unions, so one named wrapper does not close its recursive
schema obligation. Nested input, selector, scalar, target, blackboard and
effect-configuration profiles remain structural where their concrete
providers or values are unproved; this gate removes no recursive
action-interior blocker.

``--buff-report`` is the complete ``memorypack.buff_corpus`` report,
``--export-root`` the export root (``export_full``), ``--game-root`` the
installed ``Endfield_Data``, and ``--expected-input-set-sha256`` the VFS
audit value that report was built from. The default outputs are
``reports/animestudio/buff_action_receipts_current_latest.{json,md}``; the
JSON is the ``--action-report`` of the Buff child corpora
(``buff_shared_nested_receipt_corpus``, ``buff_create_input_child_corpus``,
``buff_effect_config_child_corpus``, ``buff_effect_vector_child_corpus``,
``buff_find_settings_child_corpus``, ``buff_super_armor_blackboard_child_receipt``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import ROOT, canonical_json_sha256
from scripts.game_data.memorypack.buff_action_receipts import (
    ACTION_DECODERS, certified_action_spans, replay_action_receipt, selected_candidate,
    validate_selected_native,
)


SCHEMA = "endfield.buff-action-receipt-corpus.v7"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT_JSON = REPORTS_ROOT / "animestudio/buff_action_receipts_current_latest.json"
DEFAULT_OUTPUT_MD = REPORTS_ROOT / "animestudio/buff_action_receipts_current_latest.md"
_SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffActionReceiptCorpus:{check}:source={source}; {detail}")


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


def _sole_target_projection(candidate: dict[str, Any], length: int) -> int | None:
    fields = (candidate["currentEventPrefix"] or {}).get("namedFields", [])
    field = next((row for row in fields if row.get("name") == "abilityEventAction"), None)
    if not field or not 0 <= field["start"] < field["end"] <= length:
        return None
    unions = [row for row in candidate["currentEventPrefix"].get("completedRecords", [])
              if row.get("kind") == "union" and field["start"] <= row.get("start", -1) < field["end"]]
    return unions[0]["tag"] if len(unions) == 1 and unions[0]["tag"] in ACTION_DECODERS else None


def build_receipt_report(
    buff_report: dict[str, Any],
    *,
    export_root: Path,
    expected_input_set_sha256: str,
    native_validations: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    """Join every report identity to exported bytes, then replay reviewed routes."""
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
    if set(native_validations) != set(ACTION_DECODERS) or any(
        native_validations[tag].get("status") != "validated"
        or native_validations[tag].get("unionTag") != tag for tag in ACTION_DECODERS
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
        candidate = selected_candidate(row, source)
        if not _has_reviewed_action_frame(candidate, source):
            no_action_frame.append(source)
            continue
        unions = certified_action_spans(candidate, source=source, length=len(data))
        receipts = []
        for union in unions:
            tag = union["tag"]
            if tag not in ACTION_DECODERS:
                continue
            receipt = replay_action_receipt(
                data, source=source, logical_sha256=digest,
                start=union["start"], end=union["end"],
                tag=tag, native_validation=native_validations[tag], certified_spans=unions,
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
        for tag in sorted(ACTION_DECODERS)
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
            for tag in sorted(ACTION_DECODERS)
        },
        "files": detail,
        "evidenceBoundary": (
            "Every source identity is rejoined to the completed authenticated Buff VFS "
            "census by path, length, MD5 and logical SHA256. Selected native contracts "
            "name only reached "
            + "/".join(f"0x{tag:04X}" for tag in sorted(ACTION_DECODERS))
            + " action wrapper fields at exact spans. "
            "Nested profiles and the complete BuffData schema remain unproved."
        ),
    }


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
        validations = validate_selected_native(args.game_root)
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
