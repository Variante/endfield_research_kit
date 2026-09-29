"""Join two selected SkillData cursor terminals to exact stored source reads.

The grouped receipt and two saved one-source VFS reports remain source scoped.
Pograni's 0x0152 route is injected only for this native-gated replay; the
ordinary family reader retains its closed route table.
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

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import skill_cursor_scoped_group as scoped
from scripts.game_data.memorypack import skill_timeline_shared_sequence as shared
from scripts.game_data.memorypack.corpus_gate import (
    _fingerprint, verify_current_report_inputs,
)
from scripts.game_data.memorypack.skill_cursor_wulfa_terminal import _join_ranges
from scripts.game_data.memorypack.skill_timeline_set_ignore_global_time_scale import (
    TAG as POGRANI_TAG,
    TYPE_NAME as POGRANI_TYPE,
    FIELD_NAMES as POGRANI_FIELDS,
    decode_action as decode_pograni_action,
    decode_shared_action as decode_pograni_shared_action,
    validate_current_native_contract as validate_pograni_native_contract,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.skill-cursor-lizhiyan-pograni-join.v1"
SELECTION_SCHEMA = "endfield.skill-cursor-lizhiyan-pograni-terminal-selection.v1"
SELECTION_CONTRACT = CONTRACTS_DIR / "skill_cursor_lizhiyan_pograni_terminal_selection.json"
GROUP_CONTRACT_NAME = "skill_cursor_capture_lizhiyan_pograni_group_target.json"
OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_lizhiyan_pograni_join_latest.json"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-lizhiyan-pograni-join:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_bytes())
    _require(isinstance(value, dict), f"root-shape:{path}")
    return value


def _checked_receipt(row: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    relative = row.get("path")
    _require(isinstance(relative, str) and relative.startswith(
        "scratch/reverse_engineering/endfield_capture/"), "receipt-reference-path")
    path = (REPO_ROOT / relative).resolve()
    _require(path.is_relative_to(REPO_ROOT) and path.is_file(), "receipt-outside-or-missing")
    fingerprint = _fingerprint(path)
    _require((fingerprint["length"], fingerprint["sha256"])
             == (row.get("length"), row.get("sha256")), "receipt-bytes-drift")
    return path, fingerprint


class _SelectedPograniReader(shared.SharedSequenceReader):
    def _action(self, depth: int, tag: int, width: int) -> None:
        if tag == POGRANI_TAG:
            decode_pograni_shared_action(self, depth, tag, width)
            return
        super()._action(depth, tag, width)


def _selected_pograni_timeline(source: bytes) -> dict[str, Any]:
    routes = shared._route_table()
    _require(POGRANI_TAG not in routes, "pograni-route-already-shared")
    routes = {**routes, POGRANI_TAG: {
        "tag": f"0x{POGRANI_TAG:04X}", "typeName": POGRANI_TYPE,
        "memberCount": len(POGRANI_FIELDS),
    }}
    # The saved single-source VFS reports fingerprint the shared parser. Keep
    # its bytes unchanged and confine this one extra native-gated route to the
    # synchronous selected-source replay.
    with mock.patch.object(shared, "SharedSequenceReader", _SelectedPograniReader), \
         mock.patch.object(shared, "_route_table", lambda: routes):
        return shared.decode_timeline_shared_sequence(source)


def _all_actions(profile: Mapping[str, Any]) -> list[dict[str, Any]]:
    first = profile.get("firstTimelineAction", {})
    later = profile.get("laterTimelineActions", ())
    _require(isinstance(first, Mapping) and isinstance(later, list),
             "timeline-action-shape")
    records = [first, *later]
    return [action for record in records for action in record.get("actionData", ())]


def verify_selected_sources(
    *, selection_contract_path: Path = SELECTION_CONTRACT,
    context_path: Path = scoped.DEFAULT_CONTEXT,
    binding_path: Path = scoped.DEFAULT_BINDING,
) -> dict[str, Any]:
    selection_contract_path = Path(selection_contract_path).resolve()
    _require(selection_contract_path.parent == CONTRACTS_DIR.resolve(),
             "selection-outside-reviewed-directory")
    selection = _load(selection_contract_path)
    _require(selection.get("schema") == SELECTION_SCHEMA
             and selection.get("status") == "observed-exact-sources"
             and selection.get("groupContract") == GROUP_CONTRACT_NAME,
             "selection-contract-shape")
    group_path = CONTRACTS_DIR / GROUP_CONTRACT_NAME
    group, bases, basis_paths, source_paths = scoped._selected_saved_evidence(group_path)
    for basis in bases:
        verify_current_report_inputs(basis, allow_partial=True)
    _require(selection.get("nativeInputs") == group.get("nativeInputs"),
             "native-input-selection-drift")
    selected = selection.get("targets")
    _require(isinstance(selected, list) and len(selected) == len(group["targets"]) == 2
             and [row.get("virtualPath") for row in selected]
             == [row["virtualPath"] for row in group["targets"]],
             "selection-target-scope")
    receipt_path, receipt_fingerprint = _checked_receipt(selection.get("receipt", {}))
    verified = scoped.verify_receipt(
        receipt_path, contract_path=group_path,
        context_path=context_path, binding_path=binding_path,
    )
    _require(verified.get("schema") == scoped.VERIFY_SCHEMA_V2
             and verified.get("status") == "exact-closed-scoped-group"
             and verified.get("publicationEligible") is False
             and verified.get("wholeSchemaExact") is False
             and verified.get("summary", {}).get("exactClosed") == 2
             and verified.get("summary", {}).get("failureReasons") == []
             and verified.get("targets") == group["targets"]
             and verified.get("provenance", {}).get("receipt") == receipt_fingerprint,
             "receipt-replay-drift")
    observations = {row.get("logicalPath"): row for row in verified["rows"]}
    _require(set(observations) == {row["virtualPath"] for row in selected},
             "receipt-source-scope")

    native = group["nativeInputs"]
    gate = check_installed_native_inputs(
        native["GameAssembly.dll"], native["global-metadata.dat"])
    _require(gate.status == "validated", f"native-inputs:{gate.status}:{gate.detail}")
    shared_validation = shared.validate_current_native_contract()
    _require(shared_validation.get("status") == "validated"
             and shared_validation.get("nativeInputs", {}).get("gameassemblySha256")
             == native["GameAssembly.dll"]
             and shared_validation.get("nativeInputs", {}).get("globalMetadataSha256")
             == native["global-metadata.dat"], "shared-native-validation-drift")
    pograni_validation = validate_pograni_native_contract(
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    _require(pograni_validation.get("status") == "validated"
             and pograni_validation.get("nativeInputs", {}).get("GameAssembly.dll")
             == native["GameAssembly.dll"], "pograni-native-validation-drift")

    joined: list[dict[str, Any]] = []
    for target, chosen, basis, source_path in zip(
        group["targets"], selected, bases, source_paths
    ):
        path = target["virtualPath"]
        _require((chosen.get("length"), chosen.get("logicalSha256"))
                 == (target["length"], target["logicalSha256"]),
                 f"selection-source-drift:{path}")
        source = source_path.read_bytes()
        _require((len(source), hashlib.sha256(source).hexdigest().upper())
                 == (target["length"], target["logicalSha256"]),
                 f"copied-source-drift:{path}")
        observation = observations[path]
        _require((observation.get("hardLimit"), observation.get("logicalSha256"))
                 == (target["length"], target["logicalSha256"])
                 and observation.get("boundaryClass") == "exact-closed"
                 and observation.get("parserCursor") == len(source),
                 f"executed-source-drift:{path}")
        checkpoints = observation.get("actionGroupCheckpoints")
        _require(isinstance(checkpoints, list) and len(checkpoints) == 2
                 and [row.get("childIndex") for row in checkpoints] == [0, 1]
                 and [row.get("cursorAfter") for row in checkpoints]
                 == chosen.get("actionGroupChildCursors"),
                 f"action-group-child-cursor-drift:{path}")
        terminal = chosen.get("terminal")
        candidates = observation.get("candidateAlternatives")
        _require(isinstance(terminal, Mapping) and isinstance(candidates, list)
                 and len(candidates) == 2
                 and terminal == {key: candidates[0].get(key)
                                  for key in ("candidateIndex", "encoding", "start", "end")}
                 and candidates[0].get("selected") is True
                 and candidates[1].get("selected") is False,
                 f"terminal-selection-drift:{path}")
        terminal = {**terminal, "fieldRanges": [
            {key: field[key] for key in ("fieldIndex", "fieldName", "start", "end")}
            for field in observation["runtimeFieldRanges"][43:48]
        ]}

        route = chosen.get("selectedRoute")
        if "pograni_ultimate_skill" in path:
            _require(isinstance(route, Mapping) and route.get("tag") == "0x0152",
                     "pograni-selected-route")
            action = decode_pograni_action(
                source, route.get("start"), validation=pograni_validation)
            _require(action.get("status") == "exact-stored-action-span"
                     and (action.get("start"), action.get("end"))
                     == (route.get("start"), route.get("end")),
                     "pograni-action-span-drift")
            timeline = _selected_pograni_timeline(source)
            reached = [row for row in _all_actions(timeline)
                       if row.get("tag") == POGRANI_TAG]
            _require(bool(reached)
                     and (reached[0].get("start"), reached[0].get("end"))
                     == (action["start"], action["end"]),
                     "pograni-shared-route-join")
            for reached_action in reached:
                checked = decode_pograni_action(
                    source, reached_action["start"], validation=pograni_validation)
                _require(checked.get("status") == "exact-stored-action-span"
                         and (checked.get("start"), checked.get("end"))
                         == (reached_action["start"], reached_action["end"]),
                         "pograni-later-route-span-drift")
        else:
            _require("lizhiyan_combo_skill" in path and route is None,
                     "lizhiyan-selection-route")
            action = None
            timeline = shared.decode_timeline_shared_sequence(source)
        _require(timeline.get("wholeActionGroupDataExact") is True
                 and timeline.get("wholeTimelineListExact") is True
                 and timeline.get("laterStopReason") is None
                 and timeline.get("parserCursor") == checkpoints[1]["cursorAfter"],
                 f"static-action-group-drift:{path}")
        whole = _join_ranges(
            source, observation, {"terminalSelection": terminal},
            basis["files"][0]["framing"], timeline_profile=timeline)
        _require(whole.get("wholeSchemaExact") is True
                 and whole["runtimeFieldRanges"][0]["end"]
                 == checkpoints[1]["cursorAfter"],
                 f"static-cursor-join-drift:{path}")
        joined.append({
            "virtualPath": path, "logicalSha256": target["logicalSha256"],
            "timelineActionsCount": timeline["timelineActionsCount"],
            "selectedAction": action, "actionGroupChildCursors": checkpoints,
            "selectedActionCount": len(reached) if action is not None else 0,
            "wholeActionGroupDataExact": True, "field0Through42Exact": True,
            "wholeSchemaExact": True,
            "selectedTerminal": whole["selectedTerminal"],
        })
    _require(len(joined) == 2 and all(row["wholeSchemaExact"] for row in joined),
             "whole-source-count")
    return {
        "schema": SCHEMA, "status": "two-whole-stored-sources",
        "publicationEligible": False, "wholeSchemaExact": False,
        "sourceScopedWholeStoredFileCount": 2,
        "inputSetSha256": verified["inputSetSha256"],
        "nativeValidation": {"shared": shared_validation["status"],
                             "pograniRoute": pograni_validation["status"]},
        "rows": joined,
        "provenance": {
            "selectionContract": _fingerprint(selection_contract_path),
            "groupContract": _fingerprint(group_path),
            "receipt": receipt_fingerprint,
            "context": _fingerprint(context_path),
            "bases": [_fingerprint(path) for path in basis_paths],
            "sources": [_fingerprint(path) for path in source_paths],
        },
        "evidenceBoundary": (
            "Two separately authenticated current logical SkillData sources have "
            "loss-free executed EOF cursor vectors. Native-gated stored action "
            "readers close both ActionGroups and the static fields through 42 "
            "against those cursors, then the observed terminal fields close at "
            "physical EOF. This selected-source join does not certify the whole "
            "SkillData family or action execution in gameplay."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-contract", type=Path, default=SELECTION_CONTRACT)
    parser.add_argument("--context", type=Path, default=scoped.DEFAULT_CONTEXT)
    parser.add_argument("--binding", type=Path, default=scoped.DEFAULT_BINDING)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = verify_selected_sources(
            selection_contract_path=args.selection_contract,
            context_path=args.context, binding_path=args.binding)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"],
                          "wholeStoredFileCount": result["sourceScopedWholeStoredFileCount"],
                          "publicationEligible": result["publicationEligible"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
