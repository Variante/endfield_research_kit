"""Replay selected single-CreateBuff BuffData roots against authenticated VFS bytes.

This supplementary gate does not change the canonical Buff or JsonData census.
It emits proposals only for roots whose sole remaining nested blocker is the
CreateBuff action and whose original bytes pass the thirty-field forward read.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from scripts.common import ROOT, canonical_json_sha256, sha256_file_upper
from scripts.game_data.memorypack.buff_create_action_root_receipt import (
    decode_single_create_action_root, validate_current_native_contract,
)
from scripts.game_data.memorypack.buff_root_no_positive_native import _contract as _root_contract


SCHEMA = "endfield.buff-root-single-create-action-corpus.v1"
DEFAULT_REPORT = ROOT / "reports/animestudio/buffdata_current_latest.json"
DEFAULT_EXPORT = ROOT / "export_full"
DEFAULT_OUTPUT = ROOT / "reports/animestudio/buff_create_action_root_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
ROOT_BLOCKER = {"field": "root", "category": "recursive-name-authentication-incomplete",
                "start": None, "end": None}


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffCreateActionRootCorpus:{check}:source={source}; {detail}")


def _selected_create_candidate(file: dict[str, Any], *, length: int) -> tuple[bool, bool]:
    """Return (sole CreateBuff, root-only-action-blocker) from one unique row."""
    candidates = file.get("candidates") or []
    if (file.get("coverageStatus") != "unique"
            or file.get("candidateCount") != 1 or len(candidates) != 1
            or file.get("eventPrefixStatus") != "success"
            or file.get("rootContinuationStatus") != "success"
            or file.get("namedOuterFrameStatus")
            not in ("named_exact_frame", "named_exact_full")):
        return False, False
    candidate = candidates[0]
    event = candidate.get("currentEventPrefix") or {}
    fields = event.get("namedFields") or []
    action_field = next((row for row in fields
                         if row.get("name") == "abilityEventAction"), None)
    if action_field is None:
        return False, False
    action_unions = [row for row in event.get("completedRecords", [])
                     if row.get("kind") == "union"
                     and action_field["start"] <= row.get("start", -1)
                     < action_field["end"]]
    if len(action_unions) != 1 or action_unions[0].get("tag") != 0x0092:
        return False, False
    named = candidate.get("namedSchemaReceipt") or {}
    blockers = named.get("blockers")
    exact_candidate = (
        candidate.get("readerAcceptedThroughEof") is True
        and candidate.get("currentNamedSuffix", {}).get("status")
        == "named-exact-to-eof"
        and candidate.get("currentNamedSuffix", {}).get("endOffset") == length
        and named.get("physicalEof") == length
        and named.get("actionUnionCount") == 1
        and named.get("hasConservativeSuffixFrontier") is False
        and named.get("composedOpaqueBytes") == 0
        and isinstance(blockers, list) and len(blockers) == 2
        and blockers[0].get("field") == "abilityEventAction"
        and blockers[0].get("category") == "anonymous-action-interior"
        and blockers[1] == ROOT_BLOCKER
    )
    return True, exact_candidate


def build_report(
    buff: dict[str, Any], *, buff_report_path: Path, export_root: Path,
    expected_input_set_sha256: str, native_validation: dict[str, Any],
) -> dict[str, Any]:
    expected = expected_input_set_sha256.upper()
    files = buff.get("files")
    if (
        not re.fullmatch(r"[0-9A-F]{64}", expected)
        or buff.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or buff.get("status") != "complete"
        or buff.get("publicationEligible") is not True
        or buff.get("wholeSchemaExact") is not False
        or buff.get("inputSetSha256") != expected
        or not isinstance(files, list)
        or buff.get("summary", {}).get("filesSelected") != len(files)
        or buff.get("summary", {}).get("filesUnique") != len(files)
        or buff.get("summary", {}).get("filesFailed") != 0
        or buff.get("summary", {}).get("filesAmbiguous") != 0
        or canonical_json_sha256([
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in files
        ]) != buff.get("identitySetSha256")
    ):
        _fail("buff-report-identity-or-status")
    outer = buff["provenance"]["outer"]
    outer_path = Path(outer["path"])
    if (
        sha256_file_upper(outer_path) != outer["sha256"]
        or json.loads(outer_path.read_text(encoding="utf-8")).get("inputSetSha256")
        != expected
    ):
        _fail("outer-vfs-source-drift", detail=str(outer_path))
    if native_validation.get("status") != "validated":
        _fail("selected-native-gate")
    verified_sources: set[str] = set()
    rows: list[dict[str, Any]] = []
    sole_count = 0
    other_blockers: list[str] = []
    for file in files:
        identity = file.get("identity") or {}
        source = identity.get("fileName")
        if (
            not isinstance(source, str) or not SOURCE_PATTERN.fullmatch(source)
            or source in verified_sources or identity.get("virtualPath") != source
            or identity.get("status") != "verified"
            or identity.get("boundaryStatus") != "boundary_verified"
            or identity.get("inputSetSha256") != expected
        ):
            _fail("source-identity", source=str(source))
        verified_sources.add(source)
        path = export_root / "game" / source.removeprefix("Data/")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if (
            len(data) != identity.get("length")
            or len(data) != identity.get("actualBytesRead")
            or digest != file.get("logicalSha256")
            or hashlib.md5(data).hexdigest().upper()
            != identity.get("recomputedFileDataMd5", "").upper()
        ):
            _fail("logical-source-bytes", source=source)
        sole, eligible = _selected_create_candidate(file, length=len(data))
        if not sole:
            continue
        sole_count += 1
        if not eligible:
            other_blockers.append(source)
            continue
        receipt = decode_single_create_action_root(
            data, source=source, expected_sha256=digest,
            native_validation=native_validation,
        )
        if (
            receipt.get("wholeSchemaExact") is not True
            or receipt.get("rootMemberCount") != 30
            or receipt.get("bytesConsumed") != len(data)
            or receipt.get("physicalEof") != len(data)
            or [row.get("name") for row in receipt.get("fields", [])]
            != [row["name"] for row in _root_contract()["fields"]]
        ):
            _fail("root-receipt-boundary", source=source)
        rows.append(receipt)
    if len(verified_sources) != len(files):
        _fail("source-census-incomplete")
    return {
        "schema": SCHEMA, "status": "complete", "publicationEligible": False,
        "wholeBuffDataCorpusExact": False,
        "inputSetSha256": expected,
        "sourceIdentitySetSha256": buff["identitySetSha256"],
        "inputs": {
            "buffReport": {"path": str(buff_report_path),
                           "sha256": sha256_file_upper(buff_report_path)},
            "outerVfsReport": outer,
        },
        "nativeInputs": native_validation["nativeInputs"],
        "summary": {"sourceFilesAuthenticated": len(verified_sources),
                    "soleCreateActionFiles": sole_count,
                    "eligibleSingleCreateActionRoots": len(rows),
                    "exactOriginalByteRootProposals": len(rows),
                    "otherBlockerFiles": len(other_blockers)},
        "otherBlockerSources": other_blockers,
        "rows": rows,
        "evidenceBoundary": (
            "Every current BuffData source is rejoined to the authenticated VFS "
            "identity and logical bytes. Selected native readers and original "
            "source bytes close the eligible thirty-member roots through EOF; "
            "canonical Buff and JsonData corpora remain unchanged."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--export-root", type=Path, default=DEFAULT_EXPORT)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (ROOT / "reports").resolve() not in output.parents:
        parser.error("output must be under reports/")
    buff_path = args.buff_report.resolve()
    report = build_report(
        json.loads(buff_path.read_text(encoding="utf-8")),
        buff_report_path=buff_path, export_root=args.export_root.resolve(),
        expected_input_set_sha256=args.expected_input_set_sha256,
        native_validation=validate_current_native_contract(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
