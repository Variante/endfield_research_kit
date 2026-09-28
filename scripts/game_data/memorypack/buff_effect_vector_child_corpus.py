"""Authenticate reached Buff EffectActionCfg vector and scalar children."""
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
from scripts.game_data.memorypack import buff_effect_action_receipt as action
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vector


SCHEMA = "endfield.buff-effect-vector-child-corpus.v1"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT = REPORTS_ROOT / "animestudio/buff_effect_vector_children_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffEffectVectorCorpus:{check}:source={source}; {detail}")


def build_report(
    buff: dict[str, Any], actions: dict[str, Any], *,
    buff_report_path: Path, action_report_path: Path,
    export_root: Path, expected_input_set_sha256: str,
    action_native: dict[str, Any], vector_native: dict[str, Any],
) -> dict[str, Any]:
    """Recheck the current VFS set, source bytes and every selected action."""
    expected = expected_input_set_sha256.upper()
    files = buff.get("files")
    action_files = actions.get("files")
    if not re.fullmatch(r"[0-9A-F]{64}", expected):
        _fail("expected-input-set-format")
    if (
        buff.get("format") != "animestudio-buffdata-current-vfs-corpus"
        or buff.get("status") != "complete"
        or buff.get("publicationEligible") is not True
        or buff.get("wholeSchemaExact") is not False
        or buff.get("inputSetSha256") != expected
        or not isinstance(files, list)
        or buff.get("summary", {}).get("filesSelected") != len(files)
        or buff["summary"].get("filesUnique") != len(files)
        or buff["summary"].get("filesFailed") != 0
        or buff["summary"].get("filesAmbiguous") != 0
        or canonical_json_sha256([
            {"identity": row.get("identity"), "logicalSha256": row.get("logicalSha256")}
            for row in files
        ]) != buff.get("identitySetSha256")
    ):
        _fail("buff-report-identity-or-status")
    buff_sha = sha256_file_upper(buff_report_path)
    if (
        actions.get("schema") != "endfield.buff-action-receipt-corpus.v7"
        or actions.get("status") != "complete"
        or actions.get("publicationEligible") is not True
        or actions.get("wholeBuffDataExact") is not False
        or actions.get("inputSetSha256") != expected
        or actions.get("buffReportSha256") != buff_sha
        or actions.get("sourceIdentitySetSha256") != buff["identitySetSha256"]
        or actions.get("summary", {}).get("sourceFilesVerified") != len(files)
        or not isinstance(action_files, list)
    ):
        _fail("action-report-identity-or-status")
    outer = buff["provenance"]["outer"]
    outer_path = Path(outer["path"])
    if (
        sha256_file_upper(outer_path) != outer["sha256"]
        or json.loads(outer_path.read_text(encoding="utf-8")).get("inputSetSha256")
        != expected
    ):
        _fail("outer-vfs-source-drift", detail=str(outer_path))
    if (
        action_native.get("status") != "validated"
        or action_native.get("unionTag") != action.TAG
        or vector_native.get("status") != "validated"
        or any(action_native.get("nativeInputs", {}).get(key)
               != vector_native["nativeInputs"][key]
               for key in ("GameAssembly.dll", "global-metadata.dat"))
    ):
        _fail("selected-native-gate")

    action_by_source = {row.get("source"): row for row in action_files}
    if len(action_by_source) != len(action_files) or None in action_by_source:
        _fail("duplicate-action-source")
    verified: set[str] = set()
    rows = []
    states: Counter[str] = Counter()
    scalar_states: Counter[str] = Counter()
    vector_states: Counter[str] = Counter()
    files_with_effect: set[str] = set()
    for file in files:
        identity = file["identity"]
        source = identity.get("fileName")
        if (
            not isinstance(source, str) or not SOURCE_PATTERN.fullmatch(source)
            or source in verified or identity.get("virtualPath") != source
            or identity.get("status") != "verified"
            or identity.get("boundaryStatus") != "boundary_verified"
            or identity.get("inputSetSha256") != expected
        ):
            _fail("source-identity", source=str(source))
        verified.add(source)
        data_path = export_root / "game" / source.removeprefix("Data/")
        data = data_path.read_bytes()
        source_sha = hashlib.sha256(data).hexdigest().upper()
        source_md5 = hashlib.md5(data).hexdigest().upper()
        if (
            len(data) != identity.get("length")
            or len(data) != identity.get("actualBytesRead")
            or source_sha != file.get("logicalSha256")
            or source_md5 != identity.get("recomputedFileDataMd5", "").upper()
        ):
            _fail("logical-source-bytes", source=source, detail=str(data_path))
        action_file = action_by_source.pop(source, None)
        if action_file is None:
            continue
        if action_file.get("logicalSha256") != source_sha:
            _fail("action-source-hash", source=source)
        candidate = _selected_candidate(file, source)
        certified = {(row["tag"], row["start"], row["end"])
                     for row in _union_records(candidate, source, len(data))}
        seen: set[tuple[int, int, int]] = set()
        for parent in action_file.get("actions", []):
            if parent.get("tag") != action.TAG:
                continue
            key = (action.TAG, parent.get("start"), parent.get("end"))
            if key not in certified or key in seen:
                _fail("uncertified-or-repeated-action", source=source, detail=str(key))
            seen.add(key)
            receipt = vector.decode_effect_vector_child_receipt(
                data, source=source, logical_sha256=source_sha,
                start=key[1], end=key[2],
                native_validation=vector_native, action_native=action_native,
            )
            if (
                parent.get("schema") != action.SCHEMA
                or parent.get("start") != key[1]
                or parent.get("end") != key[2]
                or parent.get("logicalSha256") != source_sha
            ):
                _fail("parent-action-receipt", source=source)
            rows.append(receipt)
            files_with_effect.add(source)
            states[receipt["status"]] += 1
            scalar_states.update(row["child"]["status"]
                                 for row in receipt["scalarChildren"])
            vector_states.update(row["status"] for row in receipt["vectorChildren"])
            scalar_states.update(member["child"]["status"]
                                 for row in receipt["vectorChildren"]
                                 for member in row["namedMembers"])
    if action_by_source:
        _fail("unmatched-action-sources", detail=str(len(action_by_source)))
    expected_effect = actions["summary"]["byTag"]["0x00A2"]
    if (
        len(rows) != expected_effect["actionSpans"]
        or len(files_with_effect) != expected_effect["files"]
        or len(rows) != sum(states.values())
        or sum(vector_states.values()) != 3 * len(rows)
        or sum(scalar_states.values()) != 11 * len(rows)
    ):
        _fail("effect-action-coverage")
    return {
        "schema": SCHEMA, "status": "complete",
        "publicationEligible": True, "wholeBuffDataExact": False,
        "inputSetSha256": expected,
        "inputs": {
            "buffReport": {"path": str(buff_report_path), "sha256": buff_sha},
            "actionReport": {"path": str(action_report_path),
                             "sha256": sha256_file_upper(action_report_path)},
            "outerVfsReport": outer,
        },
        "nativeValidation": {
            "action": action_native,
            "vector": {key: value for key, value in vector_native.items()
                       if key not in ("effectConfigNative", "scalarNative")},
        },
        "summary": {
            "sourceFilesAuthenticated": len(verified),
            "filesWithEffectAction": len(files_with_effect),
            "effectActions": len(rows),
            "vectorChildren": sum(vector_states.values()),
            "blackboardScalarChildren": sum(scalar_states.values()),
            "effectStatus": dict(sorted(states.items())),
            "vectorStatus": dict(sorted(vector_states.items())),
            "scalarStatus": dict(sorted(scalar_states.items())),
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Every current BuffData identity, logical source byte stream and "
            "selected EffectAction span is rechecked. The native vector reader "
            "and generated setters name x/y/z, and selected scalar child "
            "readers name their stored members at exact parent field extents. "
            "Live providers, effect execution and whole BuffData remain open."
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
    report = build_report(
        json.loads(buff_path.read_text(encoding="utf-8")),
        json.loads(action_path.read_text(encoding="utf-8")),
        buff_report_path=buff_path, action_report_path=action_path,
        export_root=args.export_root.resolve(),
        expected_input_set_sha256=args.expected_input_set_sha256,
        action_native=action.validate_current_native_contract(),
        vector_native=vector.validate_current_native_contract(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
