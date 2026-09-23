"""Authenticate the reviewed DamageText GPUI serialization field layouts."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.animation_curve_native import _pe_file_offset


CONTRACT_PATH = CONTRACTS_DIR / "gpu_ui_damage_text_native.json"
SCHEMA = "endfield.gpui-damage-text-native-contract.v1"


def load_damage_text_schema(
    *, game_root: Path | None = None, contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return no schema when its contract, native inputs or reader windows drift."""
    failures: list[dict[str, Any]] = []
    audit: dict[str, Any] = {
        "status": "validation_failed", "validationFailures": failures,
    }
    try:
        raw = Path(contract_path).read_bytes()
        digest = hashlib.sha256(raw).hexdigest().upper()
        audit["contractSha256"] = digest
        contract = json.loads(raw)
        if contract.get("schema") != SCHEMA or contract.get("status") != "validated":
            raise ValueError("unsupported contract schema or status")
        native = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            native["GameAssembly.dll"], native["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        audit["nativeGate"] = {"status": gate.status, "detail": gate.detail}
        if gate.status != "validated":
            audit["status"] = gate.status
            failures.append({"gate": "installed_native_inputs", "expected": "validated",
                             "actual": gate.status, "detail": gate.detail})
            return None, audit
        image = gate.gameassembly.read_bytes()
        for window in contract["codeWindows"]:
            size = window["length"]
            offset = _pe_file_offset(image, int(window["rva"], 0), size)
            actual = hashlib.sha256(image[offset:offset + size]).hexdigest().upper()
            if actual != window["sha256"]:
                failures.append({"gate": "reader_window_sha256", "owner": window["name"],
                                 "expected": window["sha256"], "actual": actual})
        if failures:
            return None, audit
        audit.update(status="validated", validatedCodeWindows=len(contract["codeWindows"]),
                     evidenceBoundary=contract["evidenceBoundary"])
        return contract, audit
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append({"gate": "contract_validation", "detail": str(error)[:500]})
        return None, audit
