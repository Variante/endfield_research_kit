"""Join one Zhuangfy ultimate-skill SkillData source to its saved live cursor.

Only this previously partial copied source is read. Other members of the
scoped group remain authenticated by saved reports and are not replayed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data.memorypack import skill_timeline_shared_sequence as shared
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import _fingerprint, verify_current_report_inputs
from scripts.game_data.memorypack.skill_cursor_wulfa_terminal import _join_ranges
from scripts.game_data.memorypack.skill_cursor_zhuangfy_group_join import (
    _checked_reference,
    _load,
    _native_paths,
    _require,
)
from scripts.game_data.memorypack.skill_timeline_change_specific_layer import (
    decode_action,
    validate_current_native_contract,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.skill-cursor-zhuangfy-ultimate-skill-join.v1"
SELECTION = CONTRACTS_DIR / "skill_cursor_zhuangfy_ultimate_skill_selection.json"
OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_zhuangfy_ultimate_skill_join_latest.json"


def verify_selected_ultimate_skill(*, selection_path: Path = SELECTION) -> dict[str, Any]:
    selection = _load(selection_path)
    target_path = selection.get("targetVirtualPath")
    _require(selection.get("schema") == "endfield.skill-cursor-zhuangfy-ultimate-skill-selection.v1"
             and selection.get("status") == "observed-exact-source"
             and selection.get("groupSelectionContract") ==
             "skill_cursor_zhuangfy_terminal_selection.json"
             and isinstance(target_path, str)
             and re.fullmatch(r"Data/Json/SkillData/[A-Za-z0-9_]+\.json", target_path)
             and selection.get("wholeStoredFileExpected") is True,
             "selection-shape")
    prior_path = CONTRACTS_DIR / selection["groupSelectionContract"]
    prior = _load(prior_path)
    _require(prior.get("schema") == "endfield.skill-cursor-group-terminal-selection.v2"
             and prior.get("status") == "observed-exact-sources"
             and prior.get("groupContract") == "skill_cursor_capture_zhuangfy_group_target.json",
             "prior-selection-shape")
    group_path = CONTRACTS_DIR / prior["groupContract"]
    group, _ = read_reviewed_contract(
        group_path, schema="endfield.skill-cursor-scoped-group.v1",
        status="selected-current-logical-sources", label="zhuangfy-ultimate-skill",
    )
    targets = group.get("targets")
    _require(isinstance(targets, list) and len(targets) == 4
             and len({row.get("virtualPath") for row in targets}) == 4
             and [row.get("virtualPath") for row in targets]
             == sorted(row.get("virtualPath") for row in targets)
             and prior.get("nativeInputs") == group.get("nativeInputs")
             and prior.get("targets") and len(prior["targets"]) == 4,
             "group-scope-or-native-drift")
    target = next((row for row in targets if row.get("virtualPath") == target_path), None)
    chosen = next((row for row in prior["targets"]
                   if row.get("virtualPath") == target_path), None)
    _require(isinstance(target, Mapping) and isinstance(chosen, Mapping)
             and (chosen.get("length"), chosen.get("logicalSha256"))
             == (target.get("length"), target.get("logicalSha256")),
             "selected-target-drift")
    basis_relative = group.get("scopedEvidence", {}).get("basis")
    _require(isinstance(basis_relative, str) and basis_relative,
             "basis-path-shape")
    basis_path = (REPO_ROOT / basis_relative).resolve()
    _require(basis_path.is_relative_to(REPO_ROOT) and basis_path.is_file(), "basis-missing")
    basis = _load(basis_path)
    _require(basis.get("status") == "partial"
             and basis.get("publicationEligible") is False
             and basis.get("targetedVirtualPaths") == [row["virtualPath"] for row in targets]
             and basis.get("files") and len(basis["files"]) == 4
             and [row.get("virtualPath") for row in basis["files"]]
             == basis["targetedVirtualPaths"],
             "basis-scope")
    verify_current_report_inputs(basis, allow_partial=True)
    basis_row = next(row for row in basis["files"] if row["virtualPath"] == target_path)
    _require((basis_row.get("length"), basis_row.get("logicalSha256"))
             == (target["length"], target["logicalSha256"])
             and basis_row.get("wholeSchemaExact") is False,
             "basis-selected-source-drift")
    verification_path, verification_fingerprint = _checked_reference(prior["verification"])
    receipt_path, receipt_fingerprint = _checked_reference(prior["receipt"])
    verification = _load(verification_path)
    _require(verification.get("status") == "exact-closed-scoped-group"
             and verification.get("publicationEligible") is False
             and verification.get("wholeSchemaExact") is False
             and verification.get("summary", {}).get("targetCount") == 4
             and verification.get("summary", {}).get("exactClosed") == 4
             and verification.get("summary", {}).get("failureReasons") == []
             and verification.get("targets") == targets,
             "saved-verification-scope")
    provenance = verification.get("provenance", {})
    _require(provenance.get("receipt") == receipt_fingerprint
             and provenance.get("basis") == _fingerprint(basis_path),
             "saved-verification-provenance")
    _checked_reference(provenance["context"])
    rows = verification.get("rows")
    _require(isinstance(rows, list) and len(rows) == 4
             and {row.get("logicalPath") for row in rows}
             == {row["virtualPath"] for row in targets},
             "saved-observation-scope")
    observation = next(row for row in rows if row["logicalPath"] == target_path)
    _require((observation.get("hardLimit"), observation.get("logicalSha256"))
             == (target["length"], target["logicalSha256"])
             and observation.get("boundaryClass") == "exact-closed"
             and observation.get("parserCursor") == target["length"],
             "selected-observation-drift")
    terminal = chosen.get("terminal")
    selected = [row for row in observation.get("candidateAlternatives", ())
                if row.get("selected") is True]
    _require(len(selected) == 1 and isinstance(terminal, Mapping)
             and (selected[0].get("start"), selected[0].get("end"), selected[0].get("encoding"))
             == (terminal.get("start"), terminal.get("end"), terminal.get("encoding"))
             and terminal.get("candidateIndex") == 0
             and terminal.get("encoding") == "one-member-wrapper"
             and terminal.get("end") == target["length"]
             and terminal.get("start") == selection.get("expectedTerminalStart")
             and terminal.get("fieldRanges") == [
                 {key: field[key] for key in ("fieldIndex", "fieldName", "start", "end")}
                 for field in observation.get("runtimeFieldRanges", ())[43:48]],
             "selected-terminal-drift")
    children = chosen.get("actionGroupChildCursors")
    _require(isinstance(children, list) and len(children) == 2
             and [(row.get("childIndex"), row.get("cursorAfter")) for row in children]
             == [(row.get("childIndex"), row.get("cursorAfter"))
                 for row in observation.get("actionGroupCheckpoints", ())]
             and children[1]["cursorAfter"] == selection.get("expectedActionGroupCursor"),
             "selected-child-cursor-drift")
    source_relative = target.get("source")
    _require(source_relative == "export_full/game/Json/SkillData/" + target_path.rsplit("/", 1)[1],
             "selected-source-path")
    source_path = (REPO_ROOT / source_relative).resolve()
    _require(source_path.is_relative_to(REPO_ROOT) and source_path.is_file(),
             "selected-source-missing")
    source = source_path.read_bytes()
    _require((len(source), hashlib.sha256(source).hexdigest().upper())
             == (target["length"], target["logicalSha256"]), "selected-source-bytes-drift")
    game, metadata = _native_paths(basis)
    native = validate_current_native_contract(gameassembly=game, metadata=metadata)
    _require(native["nativeInputs"]["GameAssembly.dll"]
             == group["nativeInputs"]["GameAssembly.dll"]
             and native["nativeInputs"]["global-metadata.dat"]
             == group["nativeInputs"]["global-metadata.dat"],
             "native-group-drift")
    claimed_actions = selection.get("selectedActions")
    _require(isinstance(claimed_actions, list) and len(claimed_actions) == 2
             and all(row.get("tag") == "0x002E"
                     and type(row.get("start")) is int
                     and type(row.get("end")) is int
                     and row["start"] < row["end"] < children[1]["cursorAfter"]
                     for row in claimed_actions)
             and all(a["end"] < b["start"]
                     for a, b in zip(claimed_actions, claimed_actions[1:])),
             "selected-actions-shape")
    actions = []
    for claimed in claimed_actions:
        actual = decode_action(source, claimed["start"], validation=native)
        _require(actual.get("status") == "exact-stored-action-span"
                 and (actual.get("start"), actual.get("end"))
                 == (claimed["start"], claimed["end"]),
                 "selected-action-span-drift")
        actions.append(actual)
    timeline = shared.decode_timeline_shared_sequence(source)
    _require(timeline.get("wholeActionGroupDataExact") is True
             and timeline.get("laterStopReason") is None
             and timeline.get("parserCursor") == children[1]["cursorAfter"],
             "action-group-not-exact")
    whole = _join_ranges(source, observation,
                         {"terminalSelection": terminal}, basis_row["framing"])
    _require(whole.get("wholeSchemaExact") is True,
             "whole-file-static-live-join-failed")
    return {
        "schema": SCHEMA, "status": "exact-stored-one-source-diagnostic",
        "publicationEligible": False, "wholeSchemaExact": True,
        "virtualPath": target_path, "logicalSha256": target["logicalSha256"],
        "sourceLength": len(source), "inputSetSha256": basis["inputSetSha256"],
        "nativeValidation": native, "selectedActions": actions,
        "timelineCursor": timeline["parserCursor"], "selectedTerminal": terminal,
        "wholeFileJoin": whole,
        "provenance": {
            "selectionContract": _fingerprint(selection_path),
            "priorSelectionContract": _fingerprint(prior_path),
            "groupContract": _fingerprint(group_path),
            "verification": verification_fingerprint,
            "receipt": receipt_fingerprint,
            "basis": _fingerprint(basis_path), "source": _fingerprint(source_path),
        },
        "evidenceBoundary": (
            "Only the ultimate-skill copied source is replayed. Two selected native "
            "0x002E readers close their actions; the complete ActionGroup and static "
            "fields 0-42 match the saved executed cursor, whose selected terminal "
            "reaches EOF. This diagnostic does not publish a complete SkillData family."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-contract", type=Path, default=SELECTION)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = verify_selected_ultimate_skill(selection_path=args.selection_contract)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"],
                          "virtualPath": result["virtualPath"],
                          "sourceLength": result["sourceLength"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
