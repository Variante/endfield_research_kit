"""Authenticate the reviewed DamageText GPUI serialization field layouts.

The contract ``gpu_ui_damage_text_native.json`` pins the current native
inputs, the generated reader order, the original field types and offsets,
and the selected reader windows for the six-field
``PrefabGroupSerializeData`` and its nested records. Missing or mismatched
native inputs withhold the exact schema, and the DamageText reader in
``scripts.game_data.gpu_ui_binary`` then fails closed on drift instead of
guessing a layout.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "gpu_ui_damage_text_native.json"
SCHEMA = "endfield.gpui-damage-text-native-contract.v2"


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
        selected_root=gate.metadata.parent.parent.parent
        unity=selected_root.parent/'UnityPlayer.dll'
        if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper()!=native['UnityPlayer.dll']:
            raise ValueError('selected UnityPlayer.dll missing or mismatched: '+str(unity))
        from scripts.game_data.il2cpp.native_image import open_native_image
        from scripts.game_data.memorypack.generated_action_sources import _source_preparation_scope
        from scripts.game_data.memorypack.gpu_damage_text_sources import derive,declaration
        from scripts.game_data.levelscript_reader_inputs import snapshot_complete_reader_inputs
        before=snapshot_complete_reader_inputs()
        image=open_native_image(gate.gameassembly,gate.metadata)
        with _source_preparation_scope(image,native):fresh=declaration(derive(image,native))
        if fresh!=contract['nativePrograms'] or fresh['records']!=contract['records']:
            raise ValueError('current complete DamageText graph differs from reviewed native declaration')
        if Path(contract_path).read_bytes()!=raw or before!=snapshot_complete_reader_inputs():
            raise ValueError('DamageText contract or reader sources changed during proof')
        audit.update(status="validated", validatedCodeWindows=len(fresh['codeWindows']),
                     completeNativeReaderCount=len(fresh['readers']),
                     evidenceBoundary=contract["evidenceBoundary"])
        return contract, audit
    except (OSError, ValueError, KeyError, TypeError) as error:
        failures.append({"gate": "contract_validation", "detail": str(error)[:500]})
        return None, audit
