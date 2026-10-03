"""Authenticate the shared EnvTalk Param/list/child default stored grammar.

The reviewed contract joins each concrete original type to its generated
wrapper and default adapter, the typed parent/list contexts, formatter and
conversion vtable slots, and the child's string/int32 reader. The native
16-byte conversion result is not a serialized element width. Runtime cache
replacement and action execution remain outside this stored-format claim.
"""
from __future__ import annotations

from functools import lru_cache
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition

CONTRACT_PATH = CONTRACTS_DIR / "levelscript_envtalk_native.json"
SCHEMA = "endfield.levelscript-envtalk-native.v1"




LABEL = "levelscriptEnvTalkNative"


class EnvTalkNativeError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any):
        self.check, self.expected, self.actual = check, expected, actual
        super().__init__(f"{LABEL}.{check}: expected={str(expected)[:240]},actual={str(actual)[:240]}")


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _require(check: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise EnvTalkNativeError(check, expected, actual)


def _read(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    _require("contract-schema", SCHEMA, contract.get("schema"))
    _require("contract-status", "exact-default-stored-grammar", contract.get("status"))
    return contract


@lru_cache(maxsize=4)
def _authenticate(path: Path, signature: tuple[int, int], gameassembly: Path,
                  ga_signature: tuple[int, int], metadata: Path,
                  metadata_signature: tuple[int, int]) -> dict[str, Any]:
    contract = _read(path)
    image = open_native_image(gameassembly, metadata)
    validate_registered_formatter_composition(image, contract, label="envTalk")
    return {"codecKinds": contract["codecKinds"], "evidenceBoundary": contract["evidenceBoundary"]}


def validate(*, game_root: Path | None = None, contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Recheck selected sources on every call; cache only authenticated bodies."""
    path = Path(contract_path)
    audit: dict[str, Any] = {"validator": LABEL, "source": str(path), "codecKinds": []}
    try:
        signature = _signature(path)
        contract = _read(path)
        inputs = contract["nativeInputs"]
        audit["nativeInputs"] = inputs
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(inputs["gameAssembly"]["sha256"], inputs["metadata"]["sha256"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None)
        audit["nativeSources"] = {"GameAssembly.dll": str(getattr(gate, "gameassembly", "unresolved")),
                                  "global-metadata.dat": str(getattr(gate, "metadata", "unresolved"))}
        if gate.status != "validated":
            failure = {"check": "installed-native-inputs", "expected": inputs,
                       "actual": {"status": gate.status, "detail": str(gate.detail)[:500],
                                  "gameAssemblySha256": getattr(gate, "gameassembly_sha256", None),
                                  "metadataSha256": getattr(gate, "metadata_sha256", None)}}
            return {**audit, "status": gate.status, "failedCheck": failure["check"],
                    "detail": str(gate.detail)[:500], "validationFailures": [failure]}
        ga_signature, md_signature = _signature(gate.gameassembly), _signature(gate.metadata)
        checked = _authenticate(path, signature, gate.gameassembly, ga_signature, gate.metadata, md_signature)
        for label, target, before in (("contract-unchanged", path, signature), ("gameassembly-unchanged", gate.gameassembly, ga_signature), ("metadata-unchanged", gate.metadata, md_signature)):
            _require(label, before, _signature(target))
        return {**audit, **checked, "status": "validated"}
    except (OSError, ValueError, KeyError, IndexError, TypeError, struct.error) as error:
        check = getattr(error, "check", str(error).split("=", 1)[0].split(":", 1)[-1][:160] or "contract-or-native")
        failure = {"check": check, "expected": str(getattr(error, "expected", "authenticated reviewed default EnvTalk grammar"))[:500],
                   "actual": str(getattr(error, "actual", error))[:500],
                   "nativeSources": audit.get("nativeSources", {}), "nativeInputs": audit.get("nativeInputs", {})}
        return {**audit, "status": "validation_failed", "failedCheck": check,
                "detail": str(error)[:500], "validationFailures": [failure]}
