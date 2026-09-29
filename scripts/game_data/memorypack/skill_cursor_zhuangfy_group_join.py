"""Join four executed Zhuangfy terminals to selected stored action prefixes.

The saved strict group verification is hash-pinned in a reviewed selection
contract. The two 0x0038 action spans receive an independent native-gated
static read. Earlier ActionGroup interiors remain partial in all four files.
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
from scripts.game_data.memorypack import skill_cursor_scoped_group as scoped
from scripts.game_data.memorypack import skill_timeline_shared_sequence as shared
from scripts.game_data.memorypack.corpus_gate import _fingerprint
from scripts.game_data.memorypack.skill_cursor_wulfa_terminal import _join_ranges
from scripts.game_data.memorypack.skill_timeline_check_ability_entity_cur_duration import (
    decode_action,
    validate_current_native_contract,
)
from scripts.game_data.memorypack.skill_timeline_set_ability_entity_duration import (
    decode_action as decode_set_action,
    validate_current_native_contract as validate_set_native_contract,
)
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.skill-cursor-zhuangfy-group-join.v2"
SELECTION_SCHEMA = "endfield.skill-cursor-group-terminal-selection.v2"
SELECTION_CONTRACT = CONTRACTS_DIR / "skill_cursor_zhuangfy_terminal_selection.json"
OUTPUT = REPO_ROOT / "reports/animestudio/skilldata_cursor_zhuangfy_group_join_latest.json"


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-zhuangfy-group-join:{reason}")


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(Path(path).read_bytes())
    _require(isinstance(value, dict), f"root-shape:{path}")
    return value


def _checked_reference(row: Mapping[str, Any]) -> tuple[Path, dict[str, Any]]:
    relative = row.get("path")
    _require(isinstance(relative, str) and relative, "reference-path")
    path = (REPO_ROOT / relative).resolve()
    _require(path.is_relative_to(REPO_ROOT) and path.is_file(), "reference-outside-or-missing")
    fingerprint = _fingerprint(path)
    _require((fingerprint["length"], fingerprint["sha256"])
             == (row.get("length"), row.get("sha256")),
             "reference-bytes-drift")
    return path, fingerprint


def _native_paths(basis: Mapping[str, Any]) -> tuple[Path, Path]:
    rows = basis.get("provenance", {}).get("buildFingerprints")
    _require(isinstance(rows, list), "basis-build-fingerprints")
    paths = {Path(row["path"]).name.lower(): Path(row["path"])
             for row in rows if isinstance(row, Mapping) and isinstance(row.get("path"), str)}
    _require("gameassembly.dll" in paths and "global-metadata.dat" in paths,
             "basis-native-paths")
    return paths["gameassembly.dll"], paths["global-metadata.dat"]


def _selected_timeline(source: bytes) -> dict[str, Any]:
    return shared.decode_timeline_shared_sequence(source)


def _selected_whole_file(source: bytes, observation: Mapping[str, Any],
                         terminal: Mapping[str, Any], framing: Mapping[str, Any]) -> dict[str, Any]:
    return _join_ranges(source, observation,
                        {"terminalSelection": terminal}, framing)


def verify_selected_group(
    *, selection_contract_path: Path = SELECTION_CONTRACT,
    output_path: Path | None = None,
) -> dict[str, Any]:
    selection = _load(selection_contract_path)
    _require(selection.get("schema") == SELECTION_SCHEMA
             and selection.get("status") == "observed-exact-sources",
             "selection-contract-shape")
    group_name = selection.get("groupContract")
    _require(group_name == "skill_cursor_capture_zhuangfy_group_target.json",
             "group-contract-name")
    group_path = CONTRACTS_DIR / group_name
    group, basis, basis_path, source_paths = scoped._selected_evidence(group_path)
    _require(selection.get("nativeInputs") == group.get("nativeInputs"),
             "native-contract-drift")
    verification_path, verification_fingerprint = _checked_reference(
        selection.get("verification", {}))
    receipt_path, receipt_fingerprint = _checked_reference(selection.get("receipt", {}))
    verification = _load(verification_path)
    _require(verification.get("schema") == scoped.VERIFY_SCHEMA
             and verification.get("status") == "exact-closed-scoped-group"
             and verification.get("publicationEligible") is False
             and verification.get("wholeSchemaExact") is False
             and verification.get("summary", {}).get("targetCount") == len(group["targets"])
             and verification.get("summary", {}).get("exactClosed") == len(group["targets"])
             and verification.get("summary", {}).get("failureReasons") == []
             and verification.get("targets") == group["targets"],
             "verification-scope-or-status")
    provenance = verification.get("provenance", {})
    _require(provenance.get("receipt") == receipt_fingerprint
             and provenance.get("basis") == _fingerprint(basis_path),
             "verification-provenance-drift")
    context_reference = provenance.get("context")
    _require(isinstance(context_reference, Mapping), "context-reference")
    _checked_reference(context_reference)
    _require(selection.get("targets") and isinstance(selection["targets"], list)
             and len(selection["targets"]) == len(group["targets"]),
             "selection-target-count")
    selected_by_path = {row.get("virtualPath"): row for row in selection["targets"]}
    observations = {row.get("logicalPath"): row for row in verification.get("rows", ())}
    paths = [row["virtualPath"] for row in group["targets"]]
    _require(set(selected_by_path) == set(paths)
             and set(observations) == set(paths), "selection-target-paths")

    native_game, native_metadata = _native_paths(basis)
    native_validation = validate_current_native_contract(
        gameassembly=native_game, metadata=native_metadata,
    )
    set_native_validation = validate_set_native_contract(
        gameassembly=native_game, metadata=native_metadata,
    )
    sequences = selection.get("selectedActionSequences")
    _require(isinstance(sequences, list) and len(sequences) == 2
             and len({row.get("virtualPath") for row in sequences}) == 2,
             "selected-action-scope")
    sequence_by_path = {row["virtualPath"]: row for row in sequences}
    basis_by_path = {row["virtualPath"]: row for row in basis["files"]}
    _require(set(basis_by_path) == set(paths), "basis-paths")
    joined = []
    for target, source_path in zip(group["targets"], source_paths):
        path = target["virtualPath"]
        source = source_path.read_bytes()
        _require((len(source), hashlib.sha256(source).hexdigest().upper())
                 == (target["length"], target["logicalSha256"]),
                 f"source-drift:{path}")
        chosen = selected_by_path[path]
        observation = observations[path]
        _require((chosen.get("length"), chosen.get("logicalSha256"))
                 == (target["length"], target["logicalSha256"])
                 and (observation.get("hardLimit"), observation.get("logicalSha256"))
                 == (target["length"], target["logicalSha256"])
                 and observation.get("boundaryClass") == "exact-closed"
                 and observation.get("parserCursor") == target["length"],
                 f"source-or-cursor-drift:{path}")
        selected_terminal = [row for row in observation.get("candidateAlternatives", ())
                             if row.get("selected") is True]
        terminal = chosen.get("terminal")
        _require(len(selected_terminal) == 1 and isinstance(terminal, Mapping)
                 and (selected_terminal[0].get("start"), selected_terminal[0].get("end"),
                      selected_terminal[0].get("encoding"))
                 == (terminal.get("start"), terminal.get("end"), terminal.get("encoding"))
                 and terminal.get("candidateIndex") == 0
                 and terminal.get("encoding") == "one-member-wrapper"
                 and terminal.get("end") == len(source)
                 and terminal.get("fieldRanges") == [
                     {key: field[key] for key in ("fieldIndex", "fieldName", "start", "end")}
                     for field in observation.get("runtimeFieldRanges", ())[43:48]
                 ],
                 f"terminal-selection-drift:{path}")
        child_cursors = chosen.get("actionGroupChildCursors")
        _require(isinstance(child_cursors, list)
                 and [(row.get("childIndex"), row.get("cursorAfter")) for row in child_cursors]
                 == [(row.get("childIndex"), row.get("cursorAfter"))
                     for row in observation.get("actionGroupCheckpoints", ())],
                 f"action-group-cursor-drift:{path}")
        action_results: list[dict[str, Any]] = []
        timeline = None
        whole_join = None
        if path in sequence_by_path:
            claimed = sequence_by_path[path]
            members = claimed.get("actions")
            _require(isinstance(members, list) and len(members) == 2
                     and [row.get("tag") for row in members] == ["0x0038", "0x0146"]
                     and members[0].get("end") == members[1].get("start"),
                     f"action-contract-shape:{path}")
            for row, decoder, validation in (
                (members[0], decode_action, native_validation),
                (members[1], decode_set_action, set_native_validation),
            ):
                result = decoder(source, row.get("start"), validation=validation)
                _require(result.get("status") == "exact-stored-action-span"
                         and (result.get("start"), result.get("end"))
                         == (row["start"], row["end"])
                         and result["end"] < child_cursors[1]["cursorAfter"],
                         f"action-span-drift:{path}:{row['tag']}")
                action_results.append(result)
            if claimed.get("wholeStoredFileExpected") is True:
                timeline = _selected_timeline(source)
                _require(claimed.get("nextStopTag") is None
                         and timeline.get("wholeActionGroupDataExact") is True
                         and timeline.get("laterStopReason") is None
                         and timeline.get("parserCursor") == child_cursors[1]["cursorAfter"],
                         f"action-group-not-exact:{path}")
                whole_join = _selected_whole_file(
                    source, observation, terminal, basis_by_path[path]["framing"])
                _require(whole_join.get("wholeSchemaExact") is True,
                         f"whole-file-join-failed:{path}")
            else:
                _require(claimed.get("wholeStoredFileExpected") is False
                         and claimed.get("nextStopTag") == "0x0197",
                         f"later-stop-drift:{path}")
        joined.append({
            "virtualPath": path,
            "logicalSha256": target["logicalSha256"],
            "terminal": terminal,
            "actionGroupChildCursors": child_cursors,
            "selectedActions": action_results,
            "laterStopReason": ("historical-unreplayed-route=0x0197"
                                if path in sequence_by_path and timeline is None else None),
            "wholeActionGroupExact": bool(whole_join),
            "wholeSchemaExact": bool(whole_join),
            "wholeFileJoin": whole_join,
        })
    _require(set(sequence_by_path) == {row["virtualPath"] for row in group["targets"]
                                     if "normal_skill" in row["virtualPath"]},
             "selected-action-paths")
    return {
        "schema": SCHEMA,
        "status": "one-whole-source-three-partial",
        "publicationEligible": False,
        "wholeSchemaExact": False,
        "targetCount": len(joined),
        "selectedActionCount": sum(len(row["selectedActions"]) for row in joined),
        "wholeStoredFileCount": sum(bool(row["wholeSchemaExact"]) for row in joined),
        "inputSetSha256": basis["inputSetSha256"],
        "nativeValidation": {"checkDuration": native_validation,
                             "setDuration": set_native_validation},
        "rows": joined,
        "provenance": {
            "selectionContract": _fingerprint(selection_contract_path),
            "groupContract": _fingerprint(group_path),
            "verification": verification_fingerprint,
            "receipt": receipt_fingerprint,
            "basis": _fingerprint(basis_path),
        },
        "evidenceBoundary": (
            "The live cursor selects the earlier EOF terminal in four exact copied sources. "
            "Selected native readers close actions 0x0038 and 0x0146 in the two normal-skill "
            "variants. The ultimate-mode variant's complete ActionGroup and static fields "
            "0-42 join the executed terminal and close one stored file. The ordinary variant "
            "stops later at 0x0197; perfect dodge and ultimate remain at their first stops. "
            "This selected-source result is not a complete family gate."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-contract", type=Path, default=SELECTION_CONTRACT)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        result = verify_selected_group(selection_contract_path=args.selection_contract)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8", newline="\n")
        print(json.dumps({"status": result["status"], "targetCount": result["targetCount"],
                          "selectedActionCount": result["selectedActionCount"],
                          "wholeStoredFileCount": result["wholeStoredFileCount"],
                          "output": str(args.output)}, ensure_ascii=False))
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "failed", "diagnostic": str(exc)},
                         ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
