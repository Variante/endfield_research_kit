"""Authenticate current Buff files and replay CreateBuff input/assignment children."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import ROOT, canonical_json_sha256, sha256_file_upper
from scripts.game_data.memorypack.buff_action_receipt_corpus import (
    _selected_candidate, _union_records,
)
from scripts.game_data.memorypack.buff_create_buff_action_receipt import (
    decode_create_buff_action_receipt,
    validate_current_native_contract as validate_parent_native,
)
from scripts.game_data.memorypack.buff_create_input_child_receipt import (
    decode_create_buff_input_list,
    validate_current_native_contract as validate_child_native,
)


SCHEMA = "endfield.buff-create-input-child-corpus.v1"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT = REPORTS_ROOT / "animestudio/buff_create_input_children_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")
TAG = 0x0092


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffCreateInputCorpus:{check}:source={source}; {detail}")


def build_report(
    buff: dict[str, Any], action: dict[str, Any], *, buff_report_path: Path,
    action_report_path: Path, export_root: Path, expected_input_set_sha256: str,
    parent_native: dict[str, Any], child_native: dict[str, Any],
) -> dict[str, Any]:
    """Verify every current Buff identity and every reached parent field."""
    expected = expected_input_set_sha256.upper()
    files = buff.get("files")
    action_files = action.get("files")
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        _fail("expected-input-set-format")
    if (buff.get("format") != "animestudio-buffdata-current-vfs-corpus"
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
            ]) != buff.get("identitySetSha256")):
        _fail("buff-report-identity-or-status")
    buff_sha = sha256_file_upper(buff_report_path)
    if (action.get("schema") != "endfield.buff-action-receipt-corpus.v7"
            or action.get("status") != "complete"
            or action.get("publicationEligible") is not True
            or action.get("wholeBuffDataExact") is not False
            or action.get("inputSetSha256") != expected
            or action.get("buffReportSha256") != buff_sha
            or action.get("sourceIdentitySetSha256") != buff["identitySetSha256"]
            or action.get("summary", {}).get("sourceFilesVerified") != len(files)
            or not isinstance(action_files, list)):
        _fail("action-report-identity-or-status")
    outer = buff["provenance"]["outer"]
    outer_path = Path(outer["path"])
    if (sha256_file_upper(outer_path) != outer["sha256"]
            or json.loads(outer_path.read_text(encoding="utf-8")).get("inputSetSha256")
            != expected):
        _fail("outer-vfs-source-drift", detail=str(outer_path))
    if (parent_native.get("status") != "validated"
            or parent_native.get("unionTag") != TAG
            or child_native.get("status") != "validated"
            or parent_native.get("nativeInputs") != child_native.get("nativeInputs")):
        _fail("selected-native-gate")

    action_by_source = {row.get("source"): row for row in action_files}
    if len(action_by_source) != len(action_files) or None in action_by_source:
        _fail("duplicate-action-source")
    verified_sources: set[str] = set()
    rows: list[dict[str, Any]] = []
    input_count = pair_count = positive_pair_lists = 0
    input_states: Counter[str] = Counter()
    pair_states: Counter[str] = Counter()
    list_counts: Counter[str] = Counter()
    for file in files:
        identity = file["identity"]
        source = identity.get("fileName")
        if (not isinstance(source, str) or not SOURCE_PATTERN.fullmatch(source)
                or source in verified_sources or identity.get("virtualPath") != source
                or identity.get("status") != "verified"
                or identity.get("boundaryStatus") != "boundary_verified"
                or identity.get("inputSetSha256") != expected):
            _fail("source-identity", source=str(source))
        verified_sources.add(source)
        data_path = export_root / "game" / source.removeprefix("Data/")
        data = data_path.read_bytes()
        digest = hashlib.sha256(data).hexdigest().upper()
        if (len(data) != identity.get("length")
                or len(data) != identity.get("actualBytesRead")
                or digest != file.get("logicalSha256")
                or hashlib.md5(data).hexdigest().upper()
                != identity.get("recomputedFileDataMd5", "").upper()):
            _fail("logical-source-bytes", source=source,
                  detail=f"expectedSha={file.get('logicalSha256')} actualSha={digest}; path={data_path}")
        action_file = action_by_source.pop(source, None)
        certified = {(record["tag"], record["start"], record["end"])
                     for record in _union_records(_selected_candidate(file, source), source, len(data))}
        if action_file is None:
            continue
        if action_file.get("logicalSha256") != digest:
            _fail("action-source-hash", source=source)
        seen: set[tuple[int, int, int]] = set()
        for parent in action_file.get("actions", []):
            if parent.get("tag") != TAG:
                continue
            key = (TAG, parent.get("start"), parent.get("end"))
            if key not in certified or key in seen:
                _fail("uncertified-or-repeated-parent", source=source, detail=str(key))
            seen.add(key)
            replay = decode_create_buff_action_receipt(
                data, source=source, logical_sha256=digest, start=key[1], end=key[2],
                native_validation=parent_native,
            )
            if replay["namedFields"] != parent.get("namedFields"):
                _fail("parent-field-drift", source=source, detail=str(key))
            fields = [row for row in replay["namedFields"] if row["fieldName"] == "buffs"]
            if len(fields) != 1 or fields[0]["kind"] != "List<CreateBuffActionInput>":
                _fail("parent-buffs-field", source=source)
            child = decode_create_buff_input_list(
                data, source=source, logical_sha256=digest,
                start=fields[0]["start"], end=fields[0]["end"],
                native_validation=child_native,
            )
            rows.append({"source": source, "logicalSha256": digest,
                         "parentAction": {"tag": TAG, "start": key[1], "end": key[2]},
                         "buffs": child})
            list_counts[str(child["count"])] += 1
            for item in child["inputs"]:
                input_count += 1
                input_states[item["status"]] += 1
                if item["status"] != "named-five-member-exact-span":
                    continue
                assignments = item["namedFields"][1]
                if assignments["count"] > 0:
                    positive_pair_lists += 1
                for pair in assignments["elements"]:
                    pair_count += 1
                    pair_states[pair["status"]] += 1
    if action_by_source:
        _fail("unmatched-action-sources", detail=f"remaining={len(action_by_source)}")
    expected_actions = action["summary"]["byTag"]["0x0092"]["actionSpans"]
    if len(rows) != expected_actions:
        _fail("parent-action-count", detail=f"expected={expected_actions} actual={len(rows)}")
    return {
        "schema": SCHEMA, "status": "complete", "publicationEligible": True,
        "wholeBuffDataExact": False, "inputSetSha256": expected,
        "inputs": {
            "buffReport": {"path": str(buff_report_path), "sha256": buff_sha},
            "actionReport": {"path": str(action_report_path),
                             "sha256": sha256_file_upper(action_report_path)},
            "outerVfsReport": outer,
        },
        "nativeValidation": {"parentAction": parent_native, "inputChildren": child_native},
        "summary": {
            "sourceFilesAuthenticated": len(verified_sources),
            "createBuffActions": len(rows),
            "filesWithCreateBuffActions": len({row["source"] for row in rows}),
            "inputListCounts": dict(sorted(list_counts.items())),
            "createBuffInputElements": input_count,
            "inputElementStates": dict(sorted(input_states.items())),
            "positiveAssignmentLists": positive_pair_lists,
            "assignPairElements": pair_count,
            "assignPairStates": dict(sorted(pair_states.items())),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Every current BuffData logical file and the parent action report are "
            "rechecked against the same VFS input set, source byte hashes and "
            "selected native build. Each CreateBuffAction parent is reparsed and "
            "its buffs field closes at the report's certified byte boundary. "
            "Nested CreateBuffActionInput and AssignPair direct fields are named "
            "in selected source order; string bytes and numeric bits stay raw. "
            "Live assignment behavior and whole BuffData remain unresolved."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--buff-report", type=Path, required=True)
    parser.add_argument("--action-report", type=Path, required=True)
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if REPORTS_ROOT.resolve() not in output.parents:
        parser.error(f"output must be under {REPORTS_ROOT}")
    buff_path = args.buff_report.resolve()
    action_path = args.action_report.resolve()
    buff = json.loads(buff_path.read_text(encoding="utf-8"))
    action = json.loads(action_path.read_text(encoding="utf-8"))
    report = build_report(
        buff, action, buff_report_path=buff_path, action_report_path=action_path,
        export_root=args.export_root.resolve(),
        expected_input_set_sha256=args.expected_input_set_sha256,
        parent_native=validate_parent_native(), child_native=validate_child_native(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
