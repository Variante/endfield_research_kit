"""Authenticate stored camera fields and the shared CameraBlendCurveKey reader.

The reviewed contract supplies layout and native provenance. The selected
method identities, code windows and typed ReadValue registration are checked
before either camera codec admits fields. No runtime camera behavior is proved.
"""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import (
    relative_branch_target, generic_method_candidates, usage_method_spec,
)
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_name

SCHEMA = "endfield.levelscript-camera-look-at.v2"
LABEL = "levelscriptCameraLookAtNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_camera_look_at_native.json"


class CameraNativeValidationError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any) -> None:
        self.check, self.expected, self.actual = check, expected, actual
        super().__init__(f"{LABEL}.{check}: expected={expected!s:.240}, actual={actual!s:.240}")


def _require(check: str, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise CameraNativeValidationError(check, expected, actual)


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=4)
def _read(path: Path, signature: tuple[int, int]) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    _require("contract-schema", SCHEMA, contract.get("schema"))
    _require("contract-status", "exact-current-build", contract.get("status"))
    _require("contract-evidence", "exact", contract.get("evidenceBoundary"))
    _require("curve-managed-type", "Beyond.CameraBlendCurveKey", contract["curveKey"]["managedType"])
    for name in ("GameAssembly.dll", "global-metadata.dat"):
        digest = contract["nativeInputs"][name]
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise CameraNativeValidationError("native-input-hash", "64 hexadecimal characters", name)
    fields = contract["fields"]
    if not isinstance(fields, list) or len(fields) != len({row[0] for row in fields}):
        raise CameraNativeValidationError("field-layout", "unique ordered field declarations", fields)
    return contract


def read_camera_look_at_contract(contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Read reviewed declarations; callers must authenticate before decoding."""
    path = Path(contract_path)
    return _read(path, _signature(path))


def _validate_native(image: Any, contract: dict[str, Any]) -> dict[str, int]:
    for row in contract["methods"]:
        image.validate_method_row(row, label=LABEL)
    for window in contract["codeWindows"]:
        raw = image.pe.bytes_at_va(int(window["va"], 16), window["length"])
        _require("code-window:" + window["name"], window["sha256"].upper(), hashlib.sha256(raw).hexdigest().upper())
    terminal = contract["curveKey"]["keySetterTerminal"]
    terminal_raw = bytes.fromhex(terminal["hex"])
    _require("key-setter-terminal-bytes", terminal_raw, image.pe.bytes_at_va(image.pe.image_base + terminal["rva"], len(terminal_raw)))
    _require("key-setter-terminal-jmp", 0xE9, terminal_raw[-5])

    context = contract["curveKey"]["typedReadValue"]
    image.check_instruction_windows([
        [context["instructionRva"], context["instructionHex"]],
        [context["callRva"], context["callHex"]],
    ], label=LABEL)
    cell, usage = image.nested_usage_cell(context, label=LABEL)
    registration, pe, metadata = image.registration, image.pe, image.metadata
    records = int(registration["methodSpecs"], 16)
    spec = usage_method_spec(
        usage, pe.bytes_at_va(records, registration["methodSpecsCount"] * 12),
        len(metadata.methods), registration["genericInstsCount"],
        source=str(image.gameassembly), usage_offset=cell, records_offset=records,
    )
    _require("typed-readvalue-method-spec", context["methodSpec"], spec)
    method = metadata.methods[spec["definition"]]
    _require("typed-readvalue-owner", context["declaringType"], image.type_name(method.declaring_type))
    _require("typed-readvalue-name", context["methodName"], metadata.string(method.name_index))
    _require("typed-readvalue-class-instantiation", -1, spec["classInstantiationIndex"])
    instance = image.instantiations.resolve(spec["methodInstantiationIndex"])
    arguments = [runtime_type_name(pe, metadata, argument.type_pointer_va) for argument in instance.arguments]
    _require("typed-readvalue-arguments", context["methodArguments"], arguments)
    _require("typed-readvalue-key-argument", [contract["curveKey"]["managedType"]], arguments)
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    table = int(registration["genericMethodTable"], 16)
    candidates = generic_method_candidates(
        pe.bytes_at_va(table, registration["genericMethodTableCount"] * 16),
        registration["genericMethodTableCount"], registration["methodSpecsCount"],
        {spec["index"]}, code["genericMethodPointersCount"], code["invokerPointersCount"],
        source=str(image.gameassembly), offset=table,
    )
    resolved = [{"row": row, "rva": pe.u64_at_va(int(code["genericMethodPointers"], 16) + row["indices"][0] * 8) - pe.image_base} for row in candidates]
    _require("typed-readvalue-candidates", context["genericCandidates"], resolved)
    _require("typed-readvalue-candidate-count", 1, len(resolved))
    target = relative_branch_target(
        bytes.fromhex(context["callHex"]), pe.image_base + context["callRva"], source=LABEL,
    )
    _require("typed-readvalue-direct-call", pe.image_base + resolved[0]["rva"], target)
    return {"methodsChecked": len(contract["methods"]), "codeWindowsChecked": len(contract["codeWindows"]), "typedReaderCandidatesChecked": len(resolved)}


@lru_cache(maxsize=4)
def _authenticate(contract_path: Path, contract_signature: tuple[int, int], gameassembly: Path,
                  ga_signature: tuple[int, int], metadata: Path,
                  metadata_signature: tuple[int, int]) -> dict[str, int]:
    contract = _read(contract_path, contract_signature)
    image = open_native_image(gameassembly, metadata)
    return _validate_native(image, contract)


def load_camera_look_at_contract(*, game_root: Path | None = None,
                                contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Return no declarations on missing inputs, drift or a failed native check."""
    path = Path(contract_path)
    try:
        contract_signature = _signature(path)
        contract = _read(path, contract_signature)
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        gate = check_installed_native_inputs(
            expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None,
        )
        audit = {"validator": LABEL, "source": str(path), "nativeInputs": expected,
                 "observedNativeInputs": {"GameAssembly.dll": str(getattr(gate, "gameassembly_sha256", "")),
                                          "global-metadata.dat": str(getattr(gate, "metadata_sha256", ""))}}
        _require("contract-unchanged", contract_signature, _signature(path))
        if gate.status != "validated":
            return {}, {**audit, "status": gate.status, "failedCheck": "installed_native_inputs", "detail": gate.detail,
                        "validationFailures": [{"check": "installed_native_inputs", "expected": "validated", "actual": gate.status, "detail": gate.detail[:500]}]}
        ga_signature, metadata_signature = _signature(gate.gameassembly), _signature(gate.metadata)
        checked = _authenticate(path, contract_signature, gate.gameassembly, ga_signature, gate.metadata, metadata_signature)
        _require("contract-unchanged", contract_signature, _signature(path))
        _require("gameassembly-unchanged", ga_signature, _signature(gate.gameassembly))
        _require("metadata-unchanged", metadata_signature, _signature(gate.metadata))
        return contract, {**audit, "status": "validated", "evidenceBoundary": "exact", **checked}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        failure = {"check": getattr(error, "check", "contract-or-native"),
                   "expected": str(getattr(error, "expected", "authenticated reviewed contract"))[:500],
                   "actual": str(getattr(error, "actual", error))[:500]}
        return {}, {"status": "validation_failed", "validator": LABEL, "source": str(path),
                    "failedCheck": failure["check"], "detail": str(error)[:500], "validationFailures": [failure]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    _, audit = load_camera_look_at_contract(game_root=args.game_root)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
