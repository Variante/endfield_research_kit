"""Re-prove reviewed shared mission connections on explicitly selected binaries.

Only validated groups expose native method rows. Native default-body proofs do
not establish live IFix selection, server rules, activation or causal ownership.
"""
from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import Body, BodyIndex, ClaimError, evaluate
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.repo_paths import REPO_ROOT

CONTRACT_SCHEMA = "endfield.mission-shared-native-claims.v1"
REPORT_SCHEMA = "endfield.mission-shared-native-evaluation.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "mission_shared_native.json"


class OwnedBodyIndex(BodyIndex):
    """Constrain each claim to its .pdata body and unwind-owned fragments.

    Unnamed jump targets are separate helpers, not implicit body membership.
    Explicit callsAnonymousHelper claims retain the shared evaluator's bounds.
    """

    def _extent(self, pointer: int) -> int:
        end = self.extents.get(pointer)
        if end is None or not 0 < end - pointer <= 1024 * 1024:
            raise ClaimError(f"mission_shared.body: missing or oversized .pdata extent at 0x{pointer:x}")
        return end - pointer

    def body_with_fragments(self, body: Body) -> list[dict[str, Any]]:
        rows = list(body.rows)
        for pointer, size in sorted(self.chained_fragments.get(body.pointer, ())):
            if body.pointer <= pointer < body.pointer + body.size:
                continue
            if not 0 < size <= 1024 * 1024:
                raise ClaimError(f"mission_shared.fragment: invalid extent at 0x{pointer:x}")
            rows.extend(self._decode(pointer, size))
        return rows

    def callees(self, rows: Iterable[dict[str, Any]]) -> list[tuple[int, str]]:
        """Name only decoded direct targets; never byte-scan unnamed helpers."""
        result: list[tuple[int, str]] = []
        for row in rows:
            match = re.fullmatch(r"(?:call|jmp) 0x([0-9a-f]+)", str(row.get("text") or ""))
            if match:
                result.extend((int(row.get("offset") or 0), name)
                              for name in self.names_of(int(match[1], 16)))
        return result


def _gate_row(gate: Any) -> dict[str, Any]:
    return {"status": gate.status, "detail": gate.detail,
            "gameAssembly": {"path": str(gate.gameassembly), "sha256": gate.gameassembly_sha256},
            "metadata": {"path": str(gate.metadata), "sha256": gate.metadata_sha256}}


def evaluate_types(index: BodyIndex, claims: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check declared inheritance and override absence from selected metadata."""
    rows, failures = [], []
    for name, spec in claims.items():
        row = index.types.get(name)
        if row is None or row.parent_index < 0:
            failures.append({"symbol": name, "claim": "parent", "reason": "selected type or parent is missing"})
            continue
        pointer = index.pe.u64_at_va(int(index.image.registration["types"], 16) + row.parent_index * 8)
        parent = runtime_type_name(index.pe, index.metadata, pointer)
        declared = {index.metadata.string(method.name_index)
                    for method in index.metadata.methods[row.method_start:row.method_start + row.method_count]}
        rows.append({"type": name, "parent": parent, "declaredMethods": sorted(declared)})
        if parent != spec["parent"]:
            failures.append({"symbol": name, "claim": "parent", "reason": f"expected {spec['parent']}; actual {parent}"})
        present = sorted(declared.intersection(spec.get("absentDeclaredMethods", [])))
        if present:
            failures.append({"symbol": name, "claim": "absentDeclaredMethods", "reason": f"unexpected overrides {present}"})
    return rows, failures


def validate_group_shape(name: str, group: Any) -> None:
    if not isinstance(group, dict) or not isinstance(group.get("methods"), dict) or not group["methods"]:
        raise ValueError(f"mission_shared.contract: group {name} needs named methods")
    for symbol, spec in group["methods"].items():
        if not isinstance(spec, dict) or not all(isinstance(spec.get(key), str) and spec[key] for key in ("type", "method")) or not isinstance(spec.get("claims"), list) or not spec["claims"]:
            raise ValueError(f"mission_shared.contract: {name}/{symbol} needs an identity and nonempty claims")
        for position, claim in enumerate(spec["claims"]):
            if not isinstance(claim, dict) or len(set(claim) - {"ordered"}) != 1 or ("ordered" in claim and ("calls" not in claim or not isinstance(claim["ordered"], bool))):
                raise ValueError(f"mission_shared.contract: {name}/{symbol} claim[{position}] needs exactly one operator (calls may have ordered)")
    types = group.get("types", {})
    if not isinstance(types, dict):
        raise ValueError(f"mission_shared.contract: {name}/types must be a map")
    for type_name, spec in types.items():
        absent = spec.get("absentDeclaredMethods", []) if isinstance(spec, dict) else None
        if not isinstance(type_name, str) or not isinstance(spec, dict) or not isinstance(spec.get("parent"), str) or not spec["parent"] or not isinstance(absent, list) or not all(isinstance(method, str) for method in absent):
            raise ValueError(f"mission_shared.contract: {name}/types/{type_name} needs a parent and a list of absent method names")


def evaluate_connections(
    gameassembly: Path, metadata: Path, *, contract_path: Path = DEFAULT_CONTRACT,
) -> dict[str, Any]:
    """Fail closed on missing inputs, group claim failure or input mutation."""
    before = check_installed_native_inputs(gameassembly=gameassembly, metadata=metadata)
    report: dict[str, Any] = {"schema": REPORT_SCHEMA, "status": before.status,
        "nativeGate": _gate_row(before), "groups": {},
        "bodyPolicy": "decoded named call targets in exact .pdata bodies and unwind-owned fragments; anonymous helpers require an explicit bounded claim",
        "evidenceBoundary": "native default-body primitive claims; field predicates match offsets and alone do not prove read/write direction, typed receivers or control flow. Contract prose is reviewed interpretation, not a complete machine proof. Live IFix selection, activation, returns, server policy and asynchronous ownership remain unresolved"}
    if before.status != "validated":
        return report
    try:
        contract, digest = read_reviewed_contract(contract_path, schema=CONTRACT_SCHEMA,
                                                  status="reviewed", label="mission_shared")
        groups = contract.get("groups")
        if not isinstance(groups, dict) or not groups:
            raise ValueError("mission_shared.contract: nonempty groups required")
        report["contract"] = {"path": str(contract_path), "sha256": digest}
        for name, group in groups.items():
            validate_group_shape(name, group)
        index = OwnedBodyIndex(NativeImage(gameassembly, metadata, label="mission_shared"))
        for name, group in groups.items():
            methods, failures = evaluate(index, group["methods"])
            types, type_failures = evaluate_types(index, group.get("types", {}))
            failures.extend(type_failures)
            status = "validation_failed" if failures else "pendingReview" if group.get("pendingReview") else "validated"
            report["groups"][name] = {"status": status, "methods": methods if status == "validated" else [],
                "types": types if status == "validated" else [], "evaluatedMethods": methods,
                "evaluatedTypes": types, "failures": failures}
        report["status"] = "validated" if all(g["status"] == "validated" for g in report["groups"].values()) else "validation_failed"
    except (OSError, RuntimeError, ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        report["status"] = "validation_failed"
        report["detail"] = f"mission_shared.evaluate: {exc}"
        for group in report["groups"].values():
            group["status"] = "validation_failed"
            group["methods"] = []
            group["types"] = []
    after = check_installed_native_inputs(before.gameassembly_sha256, before.metadata_sha256,
                                         gameassembly=gameassembly, metadata=metadata)
    report["nativeGateAfter"] = _gate_row(after)
    if after.status != "validated":
        report["status"] = after.status
        for group in report["groups"].values():
            group["status"] = after.status
            group["methods"] = []
            group["types"] = []
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, default=REPO_ROOT / "reports/runtime_capture/mission-shared-native.json")
    args = parser.parse_args(argv)
    output = args.report.resolve()
    if not any(output.is_relative_to(REPO_ROOT / root) for root in ("reports", "scratch", "tmp")):
        parser.error("generated report must be within reports/, scratch/ or tmp/")
    report = evaluate_connections(args.gameassembly, args.metadata)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[mission_shared_native] {report['status']}: {output}")
    if report["status"] != "validated":
        detail = report.get("detail") or report["nativeGate"].get("detail") or report.get("nativeGateAfter", {}).get("detail")
        if detail:
            print(f"[mission_shared_native] failed gate: {detail}")
        for name, group in report["groups"].items():
            if group["status"] != "validated" and not group["failures"]:
                print(f"[mission_shared_native] {name}: {group['status']}; see reviewed contract and native gates")
            for failure in group["failures"]:
                print(f"[mission_shared_native] {name}/{failure['symbol']}: {failure['claim']} => {failure['reason']}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
