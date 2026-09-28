"""Authenticate current BuffData and name reached EffectActionCfg direct members."""
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
from scripts.game_data.memorypack.buff_effect_action_receipt import (
    TAG, decode_effect_action_receipt, validate_current_native_contract as validate_parent,
)
from scripts.game_data.memorypack.buff_effect_config_child_receipt import (
    decode_effect_config_child_receipt,
    validate_current_native_contract as validate_child,
)


SCHEMA = "endfield.buff-effect-config-child-corpus.v1"
REPORTS_ROOT = ROOT / "reports"
DEFAULT_OUTPUT = REPORTS_ROOT / "animestudio/buff_effect_config_children_current_latest.json"
SOURCE_PATTERN = re.compile(r"^Data/Json/BuffData/[^/\\]+[.]json$")


def _fail(check: str, *, source: str = "", detail: str = "") -> None:
    raise ValueError(f"buffEffectConfigCorpus:{check}:source={source}; {detail}")


def build_report(
    buff: dict[str, Any], action: dict[str, Any], *,
    buff_report_path: Path, action_report_path: Path,
    export_root: Path, expected_input_set_sha256: str,
    parent_native: dict[str, Any], child_native: dict[str, Any],
) -> dict[str, Any]:
    """Recheck all current source identities and every reached EffectAction."""
    expected = expected_input_set_sha256.upper()
    files = buff.get("files")
    action_files = action.get("files")
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
        action.get("schema") != "endfield.buff-action-receipt-corpus.v7"
        or action.get("status") != "complete"
        or action.get("publicationEligible") is not True
        or action.get("wholeBuffDataExact") is not False
        or action.get("inputSetSha256") != expected
        or action.get("buffReportSha256") != buff_sha
        or action.get("sourceIdentitySetSha256") != buff["identitySetSha256"]
        or action.get("summary", {}).get("sourceFilesVerified") != len(files)
        or not isinstance(action_files, list)
    ):
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
            or any(parent_native.get("nativeInputs", {}).get(key)
                   != child_native["nativeInputs"][key]
                   for key in ("GameAssembly.dll", "global-metadata.dat"))):
        _fail("selected-native-gate")

    action_by_source = {row.get("source"): row for row in action_files}
    if len(action_by_source) != len(action_files) or None in action_by_source:
        _fail("duplicate-action-source")
    verified_sources: set[str] = set()
    rows = []
    statuses: Counter[str] = Counter()
    named_bytes = 0
    effect_bytes = 0
    named_members = 0
    files_with_effect = 0
    for file in files:
        identity = file["identity"]
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
            _fail("logical-source-bytes", source=source,
                  detail=f"expectedSha={file.get('logicalSha256')} actualSha={source_sha}; path={data_path}")
        action_file = action_by_source.pop(source, None)
        if action_file is None:
            continue
        if action_file.get("logicalSha256") != source_sha:
            _fail("action-source-hash", source=source)
        candidate = _selected_candidate(file, source)
        certified = {(row["tag"], row["start"], row["end"])
                     for row in _union_records(candidate, source, len(data))}
        seen: set[tuple[int, int, int]] = set()
        local = 0
        for action_row in action_file.get("actions", []):
            if action_row.get("tag") != TAG:
                continue
            key = (TAG, action_row.get("start"), action_row.get("end"))
            if key not in certified or key in seen:
                _fail("uncertified-or-repeated-action", source=source, detail=str(key))
            seen.add(key)
            parent = decode_effect_action_receipt(
                data, source=source, logical_sha256=source_sha,
                start=key[1], end=key[2], native_validation=parent_native,
            )
            if parent != action_row:
                _fail("parent-action-drift", source=source, detail=str(key))
            fields = [field for field in parent["namedFields"]
                      if field["fieldName"] == "effectActionCfg"]
            if len(fields) != 1:
                _fail("parent-effect-field", source=source, detail=str(key))
            field = fields[0]
            child = decode_effect_config_child_receipt(
                data, source=source, logical_sha256=source_sha,
                start=field["start"], end=field["end"],
                native_validation=child_native,
            )
            rows.append({"source": source, "logicalSha256": source_sha,
                         "actionStart": key[1], "actionEnd": key[2],
                         "effectActionCfg": child})
            local += 1
            statuses[child["status"]] += 1
            effect_bytes += child["end"] - child["start"]
            named_members += len(child["namedFields"])
            named_bytes += sum(member["end"] - member["start"]
                               for member in child["namedFields"])
        files_with_effect += local > 0
    if action_by_source:
        _fail("unmatched-action-sources", detail=f"remaining={len(action_by_source)}")
    expected_actions = action["summary"]["byTag"]["0x00A2"]["actionSpans"]
    if len(rows) != expected_actions:
        _fail("effect-action-count", detail=f"expected={expected_actions} actual={len(rows)}")
    return {
        "schema": SCHEMA, "status": "complete", "publicationEligible": True,
        "wholeBuffDataExact": False, "inputSetSha256": expected,
        "inputs": {
            "buffReport": {"path": str(buff_report_path), "sha256": buff_sha},
            "actionReport": {"path": str(action_report_path),
                             "sha256": sha256_file_upper(action_report_path)},
            "outerVfsReport": outer,
        },
        "nativeValidation": {"parentAction": parent_native, "effectConfigChild": child_native},
        "summary": {
            "sourceFilesAuthenticated": len(verified_sources),
            "filesWithEffectAction": files_with_effect,
            "effectActions": len(rows),
            "effectConfigChildStatus": dict(sorted(statuses.items())),
            "directNamedMemberSpans": named_members,
            "effectConfigChildBytes": effect_bytes,
            "directNamedMemberBytes": named_bytes,
            "wholeBuffDataPromoted": 0,
        },
        "rows": rows,
        "evidenceBoundary": (
            "Every current BuffData logical file and the parent action report are "
            "rechecked against one VFS input set, source byte hashes and the "
            "selected native build. Each EffectAction is reparsed and its "
            "EffectActionCfg child closes at the parent field boundary. The "
            "selected 85 direct source reads and destination stores name those "
            "members. Nested value meaning, live effects and whole BuffData "
            "remain unresolved."
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
        parent_native=validate_parent(), child_native=validate_child(),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
