"""Authenticate reviewed LevelScript task-condition union rows."""
from __future__ import annotations

import hashlib
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.animation_curve_native import _pe_file_offset


CONTRACT_PATH = Path(__file__).with_suffix(".json")
CONTRACT_SHA256 = "f1a98f4168db74db2fb7be4a84fff0ca2a8640ab5f6718dc083491df7ddfed5f"
SCHEMA = "endfield.levelscript-task-condition-native.v1"


@lru_cache(maxsize=4)
def load_levelscript_task_condition_rows(
    *, game_root: Path | None = None, contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    """Return authenticated ``(tag, memberCount)`` rows or an empty mapping."""
    failures: list[dict[str, Any]] = []
    audit: dict[str, Any] = {"status": "validation_failed", "validationFailures": failures}
    try:
        raw = contract_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        if digest != CONTRACT_SHA256:
            raise ValueError(
                f"contract_sha256: expected {CONTRACT_SHA256}, actual {digest}"
            )
        contract = json.loads(raw)
        if contract.get("schema") != SCHEMA or contract.get("status") != "validated":
            raise ValueError("contract_schema_or_status: unsupported contract")
        inputs = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            inputs["GameAssembly.dll"],
            inputs["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        audit.update(nativeGate={"status": gate.status, "detail": gate.detail}, contractSha256=digest)
        if gate.status != "validated":
            failures.append({
                "gate": "installed_native_inputs", "expected": "validated",
                "actual": gate.status, "detail": gate.detail,
            })
            audit["status"] = gate.status
            return {}, audit
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        unity_digest = hashlib.sha256(unity.read_bytes()).hexdigest()
        if unity_digest != inputs["UnityPlayer.dll"]:
            failures.append({
                "gate": "UnityPlayer.dll_sha256", "expected": inputs["UnityPlayer.dll"],
                "actual": unity_digest,
            })
            return {}, audit
        image = gate.gameassembly.read_bytes()
        for window in contract["codeWindows"]:
            size = int(window["length"])
            offset = _pe_file_offset(image, int(window["rva"], 0), size)
            actual = hashlib.sha256(image[offset:offset + size]).hexdigest()
            if actual != window["sha256"]:
                failures.append({
                    "gate": "code_window_sha256", "owner": window["name"],
                    "expected": window["sha256"], "actual": actual,
                })
        if failures:
            return {}, audit
        rows = {
            (int(row["tag"], 0), int(row["memberCount"])): row
            for row in contract["rows"]
        }
        audit.update(
            status="validated", evidenceBoundary=contract["evidenceBoundary"],
            validatedCodeWindows=len(contract["codeWindows"]), validatedRows=len(rows),
        )
        return rows, audit
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append({"gate": "contract_validation", "detail": str(error)})
        return {}, audit
