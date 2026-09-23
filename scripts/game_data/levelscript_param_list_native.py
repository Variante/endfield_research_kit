"""Authenticate the generated ParamListForGraph collection owner."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_param_list.json"
SCHEMA = "endfield.levelscript-template-param-list-native.v1"


@lru_cache(maxsize=4)
def load_param_list_for_graph_contract(
    *, game_root: Path | None = None, contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return the reviewed owner only for its exact installed native inputs."""
    audit: dict[str, Any] = {"status": "validation_failed"}
    try:
        raw = contract_path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        contract = json.loads(raw)
        if contract.get("schema") != SCHEMA or contract.get("status") != "exact-current-build":
            raise ValueError("contract_schema_or_status: unsupported contract")
        inputs = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            inputs["GameAssembly.dll"], inputs["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        audit.update(status=gate.status, detail=gate.detail, contractSha256=digest)
        if gate.status != "validated":
            audit["failedGate"] = "installed_native_inputs"
            return None, audit
        # Full native hashes authenticate the recorded formatter/setter windows
        # and metadata declarations together; no previous-build fallback exists.
        audit["evidenceBoundary"] = contract["evidenceBoundary"]
        return contract["layout"], audit
    except (OSError, ValueError, KeyError, TypeError) as exc:
        audit.update(failedGate="contract_validation", detail=str(exc))
        return None, audit
