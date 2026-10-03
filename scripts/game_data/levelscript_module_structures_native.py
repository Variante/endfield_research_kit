"""Authenticate reusable RollingStone and Rune module stored structures."""
from __future__ import annotations

from functools import lru_cache
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition

CONTRACT_PATH = CONTRACTS_DIR / "levelscript_module_structures_native.json"
SCHEMA = "endfield.levelscript-module-structures-native.v1"




LABEL = "levelscriptModuleStructuresNative"


class ModuleNativeError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any):
        self.check, self.expected, self.actual = check, expected, actual
        super().__init__(f"{LABEL}.{check}: expected={str(expected)[:240]},actual={str(actual)[:240]}")


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


def _require(check: str, expected: Any, actual: Any) -> None:
    if expected != actual:
        raise ModuleNativeError(check, expected, actual)


def _read(path: Path) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    _require("contract-schema", SCHEMA, contract.get("schema"))
    _require("contract-status", "exact-current-build", contract.get("status"))
    return contract


@lru_cache(maxsize=4)
def _authenticate(path: Path, signature: tuple[int, int], gameassembly: Path,
                  ga_signature: tuple[int, int], metadata: Path,
                  metadata_signature: tuple[int, int]) -> dict[str, Any]:
    contract = _read(path)
    image = open_native_image(gameassembly, metadata)
    validate_registered_formatter_composition(image, contract["defaultComposition"], label="moduleStructures")
    for structure in contract["structures"]:
        wrapper = structure["wrapper"]
        names = [row["name"] for row in structure["readOrder"]]
        if names != wrapper["memberOrder"] or len(names) != wrapper["serializedMemberCount"]:
            raise ValueError("moduleStructures.contract:field-order")
        count = structure["memberCountInstruction"]
        raw = bytes.fromhex(count["bytes"])
        image.check_instruction_windows([[int(count["va"], 16) - image.pe.image_base, raw.hex()]], label="moduleStructures")
        if raw[-1] != len(names):
            raise ValueError("moduleStructures.native:member-count")
        previous = int(count["va"], 16) - image.pe.image_base
        for row in structure["readOrder"]:
            read, setter = row["precedingReadCall"], row["setterCall"]
            if not previous < read["instructionRva"] < setter["instructionRva"] or setter["targetRva"] != row["setterMethod"][3]:
                raise ValueError("moduleStructures.native:read-setter-order=" + row["name"])
            for call in (read, setter):
                image.check_instruction_windows([[call["instructionRva"], call["instructionHex"]]], label="moduleStructures")
                target = relative_branch_target(bytes.fromhex(call["instructionHex"]), image.pe.image_base + call["instructionRva"], source="moduleStructures") - image.pe.image_base
                if target != call["targetRva"]:
                    raise ValueError("moduleStructures.native:call-target=" + row["name"])
            previous = setter["instructionRva"]
    return {"moduleTypes": [row["wrapper"]["wrappedType"].rsplit(".", 1)[-1] for row in contract["structures"]],
            "evidenceBoundary": contract["evidenceBoundary"]}


def validate(*, game_root: Path | None = None, contract_path: Path = CONTRACT_PATH) -> dict[str, Any]:
    """Recheck selected sources on every call; cache only authenticated bodies."""
    path = Path(contract_path)
    audit: dict[str, Any] = {"validator": LABEL, "source": str(path), "moduleTypes": []}
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
        failure = {"check": check, "expected": str(getattr(error, "expected", "authenticated reviewed default module grammar"))[:500],
                   "actual": str(getattr(error, "actual", error))[:500],
                   "nativeSources": audit.get("nativeSources", {}), "nativeInputs": audit.get("nativeInputs", {})}
        return {**audit, "status": "validation_failed", "failedCheck": check,
                "detail": str(error)[:500], "validationFailures": [failure]}
