"""Join Wulfa's executed terminal cursor to its exact stored SkillData source.

This replays the single-target receipt and current scoped source/native gates.
The output covers one reviewed logical source only and is not a family census.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import skill_cursor_capture_target
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.schemas import MEMORYPACK_FIELD_SCHEMAS
from scripts.game_data.memorypack.skill import frame_skill_exact_timeline_action_group_profile
from scripts.game_data.memorypack.skill_cursor_wulfa_scope import validate_current_scope
from scripts.game_data.memorypack.skill_timeline_shared_sequence import decode_timeline_shared_sequence
from scripts.repo_paths import REPO_ROOT


SELECTION_CONTRACT = CONTRACTS_DIR / "skill_cursor_wulfa_terminal_selection.json"
TARGET_CONTRACT = CONTRACTS_DIR / "skill_cursor_capture_wulfa_ultimate_target.json"
CORPUS_REPORT = REPO_ROOT / "tmp/audio-skilldata/try_teleport_squad_unknown_current.json"
NATIVE_CONTEXT = REPO_ROOT / "reports/animestudio/skill_cursor_native_context_wulfa_ultimate_latest.json"
VERIFICATION = REPO_ROOT / "reports/animestudio/skilldata_cursor_wulfa_ultimate_verification_latest.json"
OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_wulfa_terminal_latest.json"
SCHEMA = "endfield.skillDataWulfaTerminalSelection.v1"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-wulfa-terminal:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_bytes())
    _require(isinstance(value, dict), f"{path}:root-shape")
    return value


def _join_ranges(
    source: bytes, observation: Mapping[str, Any], selection: Mapping[str, Any],
    framing: Mapping[str, Any], *, timeline_profile: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    names = MEMORYPACK_FIELD_SCHEMAS["SkillData"]
    runtime = observation.get("runtimeFieldRanges")
    terminal = selection.get("terminalSelection")
    _require(isinstance(runtime, list) and len(runtime) == len(names)
             and isinstance(terminal, Mapping), "cursor-vector-shape")
    _require(observation.get("boundaryClass") == "exact-closed"
             and observation.get("hardLimit") == len(source)
             and observation.get("parserCursor") == len(source), "cursor-not-eof")
    _require(terminal.get("candidateIndex") == 0
             and terminal.get("encoding") == "one-member-wrapper"
             and terminal.get("end") == len(source), "selected-terminal-shape")
    candidate = observation.get("candidate")
    _require(isinstance(candidate, Mapping)
             and candidate.get("start") == terminal.get("start")
             and candidate.get("end") == terminal.get("end")
             and candidate.get("encoding") == terminal.get("encoding")
             and candidate.get("framerCandidateCount") == 2,
             "observed-candidate-drift")
    alternatives = observation.get("candidateAlternatives")
    _require(isinstance(alternatives, list) and len(alternatives) == 2
             and all(isinstance(item, Mapping) for item in alternatives)
             and alternatives[0].get("selected") is True
             and alternatives[1].get("selected") is False,
             "alternative-selection-drift")
    timeline = (decode_timeline_shared_sequence(source) if timeline_profile is None
                else timeline_profile)
    _require(timeline.get("wholeTimelineListExact") is True
             and timeline.get("wholeActionGroupDataExact") is True
             and timeline.get("laterStopReason") is None,
             "action-group-not-exact")
    static = frame_skill_exact_timeline_action_group_profile(
        source, terminal["start"], action_group_end=timeline["parserCursor"],
        timeline_count=timeline["timelineActionsCount"],
    )
    _require(static.get("status") == "exact-through-field-42"
             and len(static.get("namedFields", [])) == 43,
             "static-prefix-not-exact")
    cursor = 1
    for index, name in enumerate(names):
        row = runtime[index]
        _require(isinstance(row, Mapping) and row.get("fieldIndex") == index
                 and row.get("fieldName") == name
                 and type(row.get("start")) is int and type(row.get("end")) is int
                 and row["start"] == cursor and row["end"] > cursor,
                 f"runtime-field-{index}-drift")
        if index <= 42:
            field = static["namedFields"][index]
            _require((field.get("fieldIndex"), field.get("fieldName"),
                      field.get("start"), field.get("end"))
                     == (index, name, row["start"], row["end"]),
                     f"static-field-{index}-drift")
        cursor = row["end"]
    _require(cursor == len(source)
             and runtime[42]["end"] == terminal["start"],
             "field42-terminal-gap")
    selected_ranges = terminal.get("fieldRanges")
    _require(isinstance(selected_ranges, list) and len(selected_ranges) == 5
             and selected_ranges == [
                 {key: runtime[index][key]
                  for key in ("fieldIndex", "fieldName", "start", "end")}
                 for index in range(43, 48)
             ], "terminal-field-contract-drift")
    candidates = framing.get("candidates")
    _require(isinstance(candidates, list) and len(candidates) == 2
             and candidates[0].get("encoding") == "one-member-wrapper"
             and int(candidates[0]["startOffset"], 0) == terminal["start"]
             and int(candidates[0]["endOffset"], 0) == len(source),
             "source-candidate-drift")
    for index, member in enumerate(candidates[0]["members"], 43):
        span = member.get("range")
        _require(isinstance(span, Mapping)
                 and (span.get("start"), span.get("end"))
                 == (runtime[index]["start"], runtime[index]["end"]),
                 f"candidate-member-{index}-drift")
    return {"runtimeFieldRanges": runtime,
            "wholeActionGroupDataExact": True, "wholeSchemaExact": True,
            "selectedTerminal": {"candidateIndex": 0,
                                 "encoding": "one-member-wrapper",
                                 "start": terminal["start"], "end": len(source)}}


def verify_selected_wulfa_terminal(
    *, verification_path: Path = VERIFICATION,
    corpus_path: Path = CORPUS_REPORT,
    native_context_path: Path = NATIVE_CONTEXT,
    target_contract_path: Path = TARGET_CONTRACT,
    selection_contract_path: Path = SELECTION_CONTRACT,
) -> dict[str, Any]:
    """Return a one-source exact stored-file result after full receipt replay."""
    selection = _load(selection_contract_path)
    target_contract = _load(target_contract_path)
    verification = _load(verification_path)
    _require(selection.get("schema") == "endfield.skill-cursor-source-terminal-selection.v1"
             and selection.get("status") == "observed-exact-source",
             "selection-contract-shape")
    target = target_contract.get("target")
    _require(isinstance(target, Mapping)
             and selection.get("source") == target,
             "target-identity-drift")
    scope = validate_current_scope(corpus_path, target_contract)
    _require(scope["logicalSha256"] == target["logicalSha256"]
             and scope["sourceLength"] == target["length"],
             "current-source-drift")
    receipt_record = selection.get("receipt")
    _require(isinstance(receipt_record, Mapping), "receipt-reference-shape")
    receipt_path = (REPO_ROOT / receipt_record["path"]).resolve()
    _require(receipt_path.is_relative_to(REPO_ROOT), "receipt-outside-workspace")
    receipt_fingerprint = _fingerprint(receipt_path)
    _require(receipt_fingerprint["length"] == receipt_record.get("length")
             and receipt_fingerprint["sha256"] == receipt_record.get("sha256"),
             "receipt-bytes-drift")
    receipt = _load(receipt_path)
    replayed = skill_cursor_capture_target.verify_capture_target(
        receipt, receipt_path=receipt_path,
        receipt_sha256=receipt_fingerprint["sha256"],
        corpus_path=corpus_path, native_context_path=native_context_path,
        target_contract_path=target_contract_path, scoped_wulfa=True,
    )
    _require(replayed == verification and verification.get("status") == "complete"
             and verification.get("summary", {}).get("failureReasons") == []
             and verification.get("captureTarget", {}).get("exactObservationCount") == 1,
             "capture-verification-drift")
    native = verification.get("nativeInputs")
    _require(isinstance(native, Mapping)
             and selection.get("nativeInputs") == {
                 "GameAssembly.dll": native.get("gameAssemblySha256"),
                 "global-metadata.dat": native.get("metadataSha256").upper()
                 if isinstance(native.get("metadataSha256"), str) else None,
             }, "selection-native-drift")
    rows = verification.get("rows")
    _require(isinstance(rows, list) and len(rows) == 1
             and rows[0].get("logicalPath") == target["virtualPath"]
             and rows[0].get("logicalSha256") == target["logicalSha256"],
             "capture-source-row-drift")
    source_path = (REPO_ROOT / target_contract["scopedEvidence"]["source"]).resolve()
    source = source_path.read_bytes()
    _require(len(source) == target["length"]
             and hashlib.sha256(source).hexdigest().upper() == target["logicalSha256"],
             "source-bytes-drift")
    observed_children = rows[0].get("actionGroupCheckpoints")
    expected_children = selection.get("actionGroupChildCursors")
    _require(isinstance(observed_children, list) and isinstance(expected_children, list)
             and len(observed_children) == len(expected_children) == 2
             and all(isinstance(item, Mapping) for item in
                     [*observed_children, *expected_children])
             and [(item.get("childIndex"), item.get("cursorAfter"))
                  for item in observed_children]
             == [(item.get("childIndex"), item.get("cursorAfter"))
                 for item in expected_children],
             "action-group-child-cursor-drift")
    corpus = _load(corpus_path)
    _require(isinstance(corpus.get("files"), list) and len(corpus["files"]) == 1,
             "corpus-target-scope")
    joined = _join_ranges(source, rows[0], selection, corpus["files"][0]["framing"])
    _require(observed_children[1]["cursorAfter"]
             == joined["runtimeFieldRanges"][0]["end"],
             "action-group-final-child-drift")
    return {
        "schema": SCHEMA,
        "status": "exact-closed-one-source",
        "publicationEligible": False,
        "inputSetSha256": scope["inputSetSha256"],
        "source": target,
        "field0Through42Exact": True,
        **joined,
        "provenance": {
            "receipt": receipt_fingerprint,
            "verification": _fingerprint(verification_path),
            "selectionContract": _fingerprint(selection_contract_path),
            "targetContract": _fingerprint(target_contract_path),
            "source": _fingerprint(source_path),
        },
        "evidenceBoundary": (
            "Exact stored SkillData framing for the one authenticated Wulfa source: the "
            "executed field and ActionGroup cursor vectors match current static fields 0-42, "
            "select the earlier terminal and reach physical EOF. This does not establish "
            "other SkillData files, formatter/provider execution, or runtime ultimate behavior."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification", type=Path, default=VERIFICATION)
    parser.add_argument("--corpus-report", type=Path, default=CORPUS_REPORT)
    parser.add_argument("--native-context", type=Path, default=NATIVE_CONTEXT)
    parser.add_argument("--target-contract", type=Path, default=TARGET_CONTRACT)
    parser.add_argument("--selection-contract", type=Path, default=SELECTION_CONTRACT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = verify_selected_wulfa_terminal(
            verification_path=args.verification,
            corpus_path=args.corpus_report,
            native_context_path=args.native_context,
            target_contract_path=args.target_contract,
            selection_contract_path=args.selection_contract,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
        print(json.dumps({"status": result["status"],
                          "wholeSchemaExact": result["wholeSchemaExact"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
