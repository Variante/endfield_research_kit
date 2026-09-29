"""Join Seraph's executed SkillData terminal to its exact stored source.

This replays one source-bound v3 receipt, selected native route, and the
current one-source VFS report. The result is diagnostic, not a family census.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from unittest import mock

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import skill_cursor_seraph_capture as capture
from scripts.game_data.memorypack import skill_timeline_shared_sequence as shared
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.skill_cursor_wulfa_terminal import _join_ranges
from scripts.game_data.memorypack.skill_timeline_dispel import (
    _contract as _dispel_contract,
    decode_action,
)
from scripts.repo_paths import REPO_ROOT


SELECTION_CONTRACT = CONTRACTS_DIR / "skill_cursor_seraph_terminal_selection.json"
TARGET_CONTRACT = CONTRACTS_DIR / "skill_cursor_capture_seraph_ultimate_target.json"
VERIFICATION = REPO_ROOT / "reports/animestudio/skilldata_cursor_seraph_ultimate_verification_latest.json"
OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_seraph_terminal_latest.json"
SCHEMA = "endfield.skillDataSeraphTerminalSelection.v1"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-seraph-terminal:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_bytes())
    _require(isinstance(value, dict), f"{path}:root-shape")
    return value


def _receipt_path(selection: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    reference = selection.get("receipt")
    _require(isinstance(reference, Mapping), "receipt-reference-shape")
    relative = reference.get("path")
    _require(isinstance(relative, str) and relative, "receipt-reference-path")
    path = (REPO_ROOT / relative).resolve()
    _require(path.is_relative_to(REPO_ROOT), "receipt-outside-workspace")
    fingerprint = _fingerprint(path)
    _require((fingerprint["length"], fingerprint["sha256"])
             == (reference.get("length"), reference.get("sha256")),
             "receipt-bytes-drift")
    return path, fingerprint


def _selected_action(
    source: bytes, selection: Mapping[str, Any],
    validation: Mapping[str, Any], route: Mapping[str, Any],
) -> dict[str, Any]:
    """Admit only the reviewed 0x009F route during this local source replay."""
    chosen = selection.get("selectedAction")
    _require(isinstance(chosen, Mapping)
             and chosen.get("tag") == "0x009F"
             and type(chosen.get("timelineIndex")) is int
             and type(chosen.get("start")) is int
             and type(chosen.get("end")) is int
             and route.get("tag") == chosen.get("tag")
             and type(route.get("memberCount")) is int
             and isinstance(route.get("typeName"), str),
             "selected-action-contract-shape")
    routes = shared._route_table()
    _require(0x9F not in routes, "shared-route-already-admitted")
    # Keep the shared parser and its existing VFS provenance untouched. Its
    # base reader already handles the Buff DispelAction framing; the source-
    # bound addition only gives the timeline walk a reviewed route label.
    with mock.patch.object(shared, "_route_table", return_value={**routes, 0x9F: route}):
        timeline = shared.decode_timeline_shared_sequence(source)
        _require(timeline.get("wholeTimelineListExact") is True
                 and timeline.get("wholeActionGroupDataExact") is True
                 and timeline.get("laterStopReason") is None,
                 "selected-timeline-not-exact")
        rows = timeline.get("laterTimelineActions")
        _require(isinstance(rows, list), "selected-timeline-rows")
        record = next((row for row in rows
                       if row.get("index") == chosen["timelineIndex"]), None)
        _require(isinstance(record, Mapping), "selected-timeline-index")
        actions = [action for action in record.get("actionData", ())
                   if isinstance(action, Mapping) and action.get("tag") == 0x9F]
        _require(len(actions) == 1
                 and (actions[0].get("start"), actions[0].get("end"))
                 == (chosen["start"], chosen["end"]),
                 "selected-action-span-drift")
        decoded = decode_action(source, chosen["start"], validation=validation)
        _require(decoded.get("status") == "exact-stored-action-span"
                 and (decoded.get("start"), decoded.get("end"))
                 == (chosen["start"], chosen["end"]),
                 "selected-action-reader-drift")
    return {"timeline": timeline, "action": decoded}


def verify_selected_seraph_terminal(
    *, verification_path: Path = VERIFICATION,
    target_contract_path: Path = TARGET_CONTRACT,
    selection_contract_path: Path = SELECTION_CONTRACT,
    context_path: Path = capture.DEFAULT_CONTEXT,
    binding_path: Path = capture.DEFAULT_BINDING,
) -> dict[str, Any]:
    """Return one exact stored-file result after current receipt replay."""
    selection = _load(selection_contract_path)
    target_contract = _load(target_contract_path)
    _require(selection.get("schema") == "endfield.skill-cursor-source-terminal-selection.v1"
             and selection.get("status") == "observed-exact-source",
             "selection-contract-shape")
    target = target_contract.get("target")
    _require(isinstance(target, Mapping) and selection.get("source") == target
             and selection.get("nativeInputs") == target_contract.get("nativeInputs"),
             "selection-target-drift")
    receipt_path, receipt_fingerprint = _receipt_path(selection)
    replayed = capture.verify_receipt(
        receipt_path, target_contract_path=target_contract_path,
        context_path=context_path, binding_path=binding_path,
    )
    verification = _load(verification_path)
    _require(replayed == verification
             and verification.get("status") == "exact-closed-one-source"
             and verification.get("publicationEligible") is False
             and verification.get("wholeSchemaExact") is False,
             "capture-verification-drift")
    observation = verification.get("row")
    _require(isinstance(observation, Mapping)
             and (observation.get("logicalPath"), observation.get("logicalSha256"))
             == (target["virtualPath"], target["logicalSha256"]),
             "capture-source-row-drift")
    child_cursors = selection.get("actionGroupChildCursors")
    observed_children = observation.get("actionGroupCheckpoints")
    _require(isinstance(child_cursors, list)
             and isinstance(observed_children, list)
             and len(child_cursors) == len(observed_children) == 2
             and [(row.get("childIndex"), row.get("cursorAfter"))
                  for row in child_cursors]
             == [(row.get("childIndex"), row.get("cursorAfter"))
                 for row in observed_children],
             "action-group-child-cursor-drift")
    scoped = target_contract.get("scopedEvidence")
    _require(isinstance(scoped, Mapping), "target-scoped-evidence")
    source_path = capture._inside_repo(scoped["source"])
    source = source_path.read_bytes()
    _require((len(source), hashlib.sha256(source).hexdigest().upper())
             == (target["length"], target["logicalSha256"]),
             "source-bytes-drift")
    basis_path = capture._inside_repo(scoped["basis"])
    basis = _load(basis_path)
    _require(len(basis.get("files", ())) == 1, "basis-target-scope")
    context = _load(context_path)
    validation = context.get("dispelNativeValidation")
    _require(isinstance(validation, Mapping)
             and validation.get("status") == "validated"
             and validation.get("unionTag") == 0x9F,
             "dispel-native-validation-drift")
    dispel = _dispel_contract()
    _require(dispel.get("selectedSource") == target
             and dispel.get("unionTag") == 0x9F
             and dispel.get("serializedMemberCount") == 9,
             "dispel-contract-source-drift")
    route = {"tag": selection["selectedAction"]["tag"],
             "typeName": dispel["actualTypeName"],
             "memberCount": dispel["serializedMemberCount"]}
    action = _selected_action(source, selection, validation, route)
    routes = shared._route_table()
    with mock.patch.object(shared, "_route_table", return_value={**routes, 0x9F: route}):
        joined = _join_ranges(
            source, observation, selection, basis["files"][0]["framing"],
        )
    _require(observed_children[1]["cursorAfter"]
             == joined["runtimeFieldRanges"][0]["end"],
             "action-group-final-child-drift")
    return {
        "schema": SCHEMA,
        "status": "exact-closed-one-source",
        "publicationEligible": False,
        "inputSetSha256": verification["inputSetSha256"],
        "source": target,
        "field0Through42Exact": True,
        **joined,
        "selectedAction": {"timelineIndex": selection["selectedAction"]["timelineIndex"],
                           "tag": "0x009F", "start": action["action"]["start"],
                           "end": action["action"]["end"]},
        "provenance": {
            "receipt": receipt_fingerprint,
            "verification": _fingerprint(verification_path),
            "selectionContract": _fingerprint(selection_contract_path),
            "targetContract": _fingerprint(target_contract_path),
            "source": _fingerprint(source_path),
        },
        "evidenceBoundary": (
            "Exact stored SkillData framing for one authenticated Seraph source: the "
            "executed field and ActionGroup cursor vectors match selected-native static "
            "action and fields 0-42, select the earlier terminal, and reach EOF. This "
            "does not establish other SkillData files or runtime dispel behavior."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verification", type=Path, default=VERIFICATION)
    parser.add_argument("--target-contract", type=Path, default=TARGET_CONTRACT)
    parser.add_argument("--selection-contract", type=Path, default=SELECTION_CONTRACT)
    parser.add_argument("--context", type=Path, default=capture.DEFAULT_CONTEXT)
    parser.add_argument("--binding", type=Path, default=capture.DEFAULT_BINDING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = verify_selected_seraph_terminal(
            verification_path=args.verification,
            target_contract_path=args.target_contract,
            selection_contract_path=args.selection_contract,
            context_path=args.context, binding_path=args.binding,
        )
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
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
