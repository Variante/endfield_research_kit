"""Recheck a saved one-source Wulfa basis for a direct cursor capture.

This scoped diagnostic preserves the original partial VFS report bytes.  An
exact additive shared-parser proof permits an in-memory provenance rebind;
the normal current VFS gate then checks the original source, chunks, exporter,
native inputs and controls.  No selected terminal or family coverage follows.
"""
from __future__ import annotations

import ast
import copy
import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from scripts.game_data.memorypack.corpus_gate import _fingerprint, verify_current_report_inputs
from scripts.game_data.memorypack.skill import frame_skill_exact_timeline_action_group_profile
from scripts.game_data.memorypack.skill_sparse_corpus_compose import (
    SHARED_CONTRACT, SHARED_SOURCE, _controls_unreached_routes,
    _fingerprint_map, _parser_map, _unique_named,
    prove_ten_route_with_anim_scale_addition,
)
from scripts.game_data.memorypack.skill_timeline_shared_sequence import decode_timeline_shared_sequence
from scripts.repo_paths import REPO_ROOT


VIRTUAL_PATH = "Data/Json/SkillData/chr_0028_wulfa_ultimate_skill.json"
NEW_PARSER_MODULES = (
    "skill_timeline_anim_event_receiver.py",
    "skill_timeline_continuous_anim_time_scale.py",
)
DOWNSTREAM_VERIFIERS = {
    "skill_cursor_capture_target.py": (
        "oldCaptureTargetVerifier", {"verify_capture_target", "main"},
    ),
    "skill_cursor_receipt.py": (
        "oldCursorReceiptVerifier",
        {"_validate_report_gates", "preflight_skilldata_corpus",
         "verify_skilldata_cursor_capture"},
    ),
}


def _require(condition: bool, reason: str) -> None:
    if not condition:
        raise ValueError(f"skill-cursor-wulfa-scope:{reason}")


def _path(evidence: Mapping[str, Any], name: str) -> Path:
    value = evidence.get(name)
    _require(isinstance(value, str) and value != "", f"{name}-path-missing")
    path = (REPO_ROOT / value).resolve()
    _require(path.is_file() and path.is_relative_to(REPO_ROOT), f"{name}-outside-workspace-or-missing")
    return path


def _downstream_verifier_only_drift(old: bytes, current: bytes,
                                    changed_functions: set[str]) -> bool:
    def normalized(data: bytes) -> str:
        tree = ast.parse(data.decode("utf-8"))
        found: set[str] = set()
        for index, node in enumerate(tree.body):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                    and node.name in changed_functions:
                found.add(node.name)
                tree.body[index] = ast.Pass()
        _require(found == changed_functions, "downstream-verifier-function-set")
        return ast.dump(tree, include_attributes=False)
    return normalized(old) == normalized(current)


def validate_current_scope(
    basis_path: Path, contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Authenticate only Wulfa, with prior controls reused byte for byte."""
    target = contract.get("target")
    evidence = contract.get("scopedEvidence")
    _require(isinstance(target, Mapping) and isinstance(evidence, Mapping), "contract-shape")
    _require(target.get("virtualPath") == VIRTUAL_PATH, "target-path")
    basis_path = Path(basis_path).resolve()
    _require(basis_path == _path(evidence, "basis"), "basis-path")
    controls_path = _path(evidence, "controls")
    source_path = _path(evidence, "source")
    old_parser = _path(evidence, "oldSharedParser")
    old_contract = _path(evidence, "oldSharedContract")
    basis = json.loads(basis_path.read_bytes())
    controls = json.loads(controls_path.read_bytes())
    _require(basis.get("status") == "partial" and basis.get("publicationEligible") is False
             and basis.get("targetedVirtualPaths") == [VIRTUAL_PATH]
             and len(basis.get("files", [])) == 1
             and basis["files"][0].get("virtualPath") == VIRTUAL_PATH,
             "basis-scope")
    _require(controls.get("status") == "partial" and controls.get("publicationEligible") is False
             and len(controls.get("files", [])) == 3
             and controls.get("inputSetSha256") == basis.get("inputSetSha256"),
             "control-scope")
    current_parser = REPO_ROOT / "scripts/game_data/memorypack/skill_timeline_shared_sequence.py"
    current_contract = REPO_ROOT / "scripts/game_data/contracts/skill_timeline_shared_sequence_native.json"
    old_parser_ref = _unique_named(_parser_map(controls), SHARED_SOURCE)[1]
    old_contract_ref = _unique_named(
        _fingerprint_map(controls, "timelinePlayAnimationContracts"), SHARED_CONTRACT,
    )[1]
    route_proof = prove_ten_route_with_anim_scale_addition(
        old_parser.read_bytes(), current_parser.read_bytes(),
        old_parser_ref, _fingerprint(current_parser),
        old_contract.read_bytes(), current_contract.read_bytes(),
        old_contract_ref, _fingerprint(current_contract),
    )
    _controls_unreached_routes(controls["files"], {0x0012, 0x008B})
    parser_rows = [
        _fingerprint(current_parser) if Path(row["path"]).name == SHARED_SOURCE else row
        for row in basis["provenance"]["parser"]
    ]
    _require(sum(Path(row["path"]).name == SHARED_SOURCE for row in parser_rows) == 1,
             "shared-parser-fingerprint")
    basis_parser = _parser_map(basis)
    for name, (old_key, changed_functions) in DOWNSTREAM_VERIFIERS.items():
        current_path = REPO_ROOT / "scripts/game_data/memorypack" / name
        old_path = _path(evidence, old_key)
        old_ref = _unique_named(basis_parser, name)[1]
        _require(_fingerprint(old_path)["length"] == old_ref["length"]
                 and _fingerprint(old_path)["sha256"] == old_ref["sha256"]
                 and _downstream_verifier_only_drift(
                     old_path.read_bytes(), current_path.read_bytes(), changed_functions,
                 ), "downstream-verifier-drift")
        parser_rows = [
            _fingerprint(current_path) if Path(row["path"]).name == name else row
            for row in parser_rows
        ]
    for name in NEW_PARSER_MODULES:
        _require(all(Path(row["path"]).name != name for row in parser_rows),
                 "new-parser-already-present")
        parser_rows.append(_fingerprint(REPO_ROOT / "scripts/game_data/memorypack" / name))
    for report in (basis, controls):
        checked = copy.deepcopy(report)
        checked["provenance"]["parser"] = parser_rows
        verify_current_report_inputs(checked, allow_partial=True)
    for path, reference in _fingerprint_map(basis, "timelinePlayAnimationContracts").items():
        if Path(path).name != SHARED_CONTRACT:
            _require(_fingerprint(Path(path))["sha256"] == reference["sha256"],
                     "dependency-contract-drift")
    row = basis["files"][0]
    source = source_path.read_bytes()
    _require(len(source) == row.get("length") == target.get("length")
             and hashlib.md5(source).hexdigest().upper() == row.get("logicalMd5")
             and hashlib.sha256(source).hexdigest().upper()
             == row.get("logicalSha256") == target.get("logicalSha256"),
             "source-identity")
    candidates = row.get("framing", {}).get("candidates", [])
    _require(len(candidates) == 2
             and all(candidate.get("boundaryClass") == "ambiguous"
                     and candidate.get("exactToEof") is True for candidate in candidates),
             "terminal-candidate-shape")
    timeline = decode_timeline_shared_sequence(source)
    _require(timeline.get("wholeTimelineListExact") is True
             and timeline.get("wholeActionGroupDataExact") is True
             and timeline.get("laterStopReason") is None,
             "action-group-not-exact")
    terminal_start = int(candidates[0]["startOffset"], 0)
    prefix = frame_skill_exact_timeline_action_group_profile(
        source, terminal_start, action_group_end=timeline["parserCursor"],
        timeline_count=timeline["timelineActionsCount"],
    )
    _require(prefix.get("status") == "exact-through-field-42"
             and prefix["namedFields"][-1]["fieldIndex"] == 42
             and prefix["namedFields"][-1]["end"] == terminal_start
             and int(candidates[0]["endOffset"], 0) == len(source),
             "field42-terminal-join")
    return {
        "status": "scoped-wulfa-unselected",
        "inputSetSha256": basis["inputSetSha256"],
        "virtualPath": VIRTUAL_PATH,
        "sourceLength": len(source),
        "logicalSha256": row["logicalSha256"],
        "routeProof": route_proof,
        "basisReference": _fingerprint(basis_path),
        "controlsReference": _fingerprint(controls_path),
        "sourceReference": _fingerprint(source_path),
        "field42End": terminal_start,
        "wholeActionGroupDataExact": True,
        "terminalSelected": False,
    }
