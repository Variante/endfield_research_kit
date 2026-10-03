"""Current third-binary gate shared by LevelScript Data adapters and receipts.

Reachable action/task children require UnityPlayer as well as the selected
GameAssembly and metadata. Reuse their owning reviewed contract's pins; this
module authenticates inputs only and does not infer any child layout.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any

from scripts.common import resolve_installed_native_inputs, sha256_file
from scripts.game_data.levelscript_task_condition_native import CONTRACT_PATH, SCHEMA


def selected_child_native_signature(
    native_inputs: dict[str, str] | None, *, gameassembly: Path | None = None,
) -> dict[str, Any]:
    """Return a bounded audit; every caller must require ``validated``."""
    audit: dict[str, Any] = {
        "status": "unavailable", "validator": "levelscript-child-native-inputs",
        "source": str(CONTRACT_PATH), "failedCheck": "contract",
    }
    try:
        contract = json.loads(CONTRACT_PATH.read_bytes())
        if not isinstance(contract, dict) or contract.get("schema") != SCHEMA or contract.get("status") != "validated":
            raise ValueError("task-condition native contract schema/status unavailable")
        names = ("GameAssembly.dll", "global-metadata.dat", "UnityPlayer.dll")
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict) or any(re.fullmatch(r"[0-9a-fA-F]{64}", str(expected.get(name) or "")) is None for name in names):
            raise ValueError("task-condition native contract pins unavailable")
        audit["expected"] = {name: expected[name].upper() for name in names}
        if gameassembly is None or native_inputs is None:
            selected_assembly, selected_metadata = resolve_installed_native_inputs()
            if gameassembly is None:
                gameassembly = selected_assembly
            if native_inputs is None:
                native_inputs = {}
                audit["actual"] = native_inputs
                for name, path in (("GameAssembly.dll", selected_assembly), ("global-metadata.dat", selected_metadata)):
                    audit.update(source=str(path), failedCheck="selected-native-inputs")
                    native_inputs[name] = sha256_file(path).upper()
        unity = gameassembly.parent / "UnityPlayer.dll"
        audit.update(source=str(unity), failedCheck="selected-native-inputs")
        actual = {
            "GameAssembly.dll": native_inputs["GameAssembly.dll"].upper(),
            "global-metadata.dat": native_inputs["global-metadata.dat"].upper(),
            "UnityPlayer.dll": sha256_file(unity).upper(),
        }
        audit["actual"] = actual
        mismatched = [name for name in names if expected[name].upper() != actual[name]]
        if mismatched:
            audit.update(status="mismatched", detail="native hash mismatch: " + ", ".join(mismatched))
        else:
            audit.update(status="validated", failedCheck=None, detail="")
    except (OSError, ValueError, KeyError, TypeError, RuntimeError) as exc:
        audit.update(status="missing" if isinstance(exc, FileNotFoundError) else "unavailable",
                     detail=str(exc)[:500])
    return audit
