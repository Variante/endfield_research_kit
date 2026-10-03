"""Authenticate PosRot children and their registered default Param/list grammar."""
from __future__ import annotations

import argparse
from functools import lru_cache
import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import relative_branch_target, usage_method_spec
from scripts.game_data.il2cpp.formatter_composition import validate_registered_formatter_composition
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name

SCHEMA = "endfield.levelscript-pos-rot-native-contract.v2"
LABEL = "levelscriptPosRotNative"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_pos_rot_native.json"


class PosRotNativeError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any, *,
                 native_sources: dict[str, str] | None = None, location: dict[str, Any] | None = None):
        self.check, self.expected, self.actual = check, expected, actual
        self.native_sources, self.location = native_sources or {}, location or {}
        context = (f", location={self.location}, nativeSources=" + "; ".join(f"{name}={path}" for name, path in self.native_sources.items())) if self.native_sources else ""
        super().__init__(f"{LABEL}.{check}: expected={str(expected)[:240]}, actual={str(actual)[:240]}{context}")


def _require(check: str, expected: Any, actual: Any) -> None:
    if actual != expected:
        raise PosRotNativeError(check, expected, actual)


def _signature(path: Path) -> tuple[int, int]:
    stat = path.stat()
    return stat.st_mtime_ns, stat.st_size


@lru_cache(maxsize=4)
def _read(path: Path, signature: tuple[int, int]) -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(path, schema=SCHEMA, status="exact-current-build", label=LABEL)
    _require("member-count", 2, contract.get("memberCount"))
    _require("stored-field-types", ["Vector3.Float32x3", "Vector3.Float32x3"], [row.get("wire") for row in contract["fields"]])
    _require("field-widths", [12, 12], [row.get("serializedWidth") for row in contract["fields"]])
    _require("parent-default-proof", "exact-default-stored", contract["parentEvidence"]["status"])
    return contract


def _native_sources(image: Any) -> dict[str, str]:
    return {"GameAssembly.dll": str(image.gameassembly), "global-metadata.dat": str(image.metadata_path)}


def _checked_native(image: Any, check: str, expected: Any, actual_reader: Any,
                    operation: Any, location: dict[str, Any]) -> Any:
    """Keep a native helper's failed row and bounded actual value actionable."""
    try:
        return operation()
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        try:
            actual = actual_reader()
        except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as read_error:
            actual = f"unreadable: {str(read_error)[:240]}; helper: {str(error)[:240]}"
        raise PosRotNativeError(check, expected, actual, native_sources=_native_sources(image), location=location) from error


def _method_actual(image: Any, row: list[Any]) -> list[Any]:
    method = image.metadata.methods[row[0]]
    actual = [row[0], image.type_name(method.declaring_type), image.metadata.string(method.name_index)]
    if len(row) > 3 and isinstance(row[3], int):
        actual.append(image.method_pointer_va(method) - image.pe.image_base)
    elif len(row) > 3:
        actual.append([image.metadata.metadata_type_name(parameter.type_index)
                       for parameter in image.metadata.parameters_for(method)])
    return actual


def _check_method(image: Any, row: list[Any]) -> None:
    _checked_native(image, "method-row", row, lambda: _method_actual(image, row),
                    lambda: image.validate_method_row(row, label=LABEL), {"metadataMethodIndex": row[0]})


def _check_windows(image: Any, windows: list[dict[str, Any]]) -> None:
    for window in windows:
        _checked_native(image, "code-window-sha256", window["sha256"].upper(),
                        lambda: hashlib.sha256(image.window_bytes(window)).hexdigest().upper(),
                        lambda: image.check_windows([window], label=LABEL),
                        {"startRva": window["startRva"], "endRva": window["endRva"]})


def _check_instructions(image: Any, rows: list[list[Any]]) -> None:
    for row in rows:
        rva, raw_hex = row[:2]
        _checked_native(image, "instruction-window", raw_hex.upper(),
                        lambda: image.pe.bytes_at_va(image.pe.image_base + rva, len(bytes.fromhex(raw_hex))).hex().upper(),
                        lambda: image.check_instruction_windows([row], label=LABEL), {"instructionRva": rva})


def _validate_field_stores(image: Any, row: dict[str, Any], next_read: int) -> None:
    """Tie each named Vector3 setter to its ordered inlined stores."""
    stores = row["storeInstructions"]
    _require("field-store-count", 2, len(stores))
    raw = [bytes.fromhex(item[1]) for item in stores]
    shapes = (len(raw[0]) == 5 and raw[0][:3] == b"\xf2\x0f\x11"
              and raw[0][3] & 0xf8 == 0x40
              and len(raw[1]) == 3 and raw[1][0] == 0x89
              and raw[1][1] & 0xf8 == 0x40
              and raw[0][3] & 7 == raw[1][1] & 7)
    _require("field-store-shape", True, shapes)
    offset = row["wrapperFieldOffset"]
    _require("field-store-offsets", [offset, offset + 8], [raw[0][-1], raw[1][-1]])
    _require("field-store-order", True,
             row["readCall"]["rva"] + 5 <= stores[0][0] < stores[1][0] < next_read)
    setter = image.pe.bytes_at_va(image.pe.image_base + row["setterMethod"][3], 16)
    _require("field-setter-copy-shape", "f20f10028b4208", setter[:7].hex())
    _require("field-setter-stores", bytes([0xf2, 0x0f, 0x11, 0x41, offset, 0x89, 0x41, offset + 8, 0xc3]), setter[7:])


def _validate(image: Any, contract: dict[str, Any]) -> dict[str, Any]:
    for method in contract["methods"]:
        _check_method(image, method)
    _check_windows(image, contract["codeWindows"])
    _check_instructions(image, [contract["memberCountInstruction"], *contract["rawReadWitnesses"]])
    jump_rva, jump_hex, jump_target = contract["formatterForwardingJump"]
    _check_instructions(image, [[jump_rva, jump_hex]])
    _require("formatter-forwarding-target", image.pe.image_base + jump_target,
             relative_branch_target(bytes.fromhex(jump_hex), image.pe.image_base + jump_rva, source=LABEL))
    previous = contract["memberCountInstruction"][0]
    for index, row in enumerate(contract["fields"]):
        setter = row["setterMethod"]
        _check_method(image, [*setter[:3], row["declaredSetterParameter"]])
        _require("field-setter-owner", contract["wrapperType"], setter[1])
        _require("field-setter-name", "set___" + row["name"] + "__", setter[2])
        call = row["readCall"]
        if call["rva"] <= previous:
            raise PosRotNativeError("ordered-field-reads", "strictly increasing call sites", call["rva"])
        _check_instructions(image, [[call["rva"], call["hex"]], *row["storeInstructions"]])
        _require("field-read-target", image.pe.image_base + call["targetRva"],
                 relative_branch_target(bytes.fromhex(call["hex"]), image.pe.image_base + call["rva"], source=LABEL))
        next_read = (contract["fields"][index + 1]["readCall"]["rva"]
                     if index + 1 < len(contract["fields"]) else call["rva"] + 128)
        _validate_field_stores(image, row, next_read)
        previous = call["rva"]
    context = contract["vectorReadContext"]
    _check_instructions(image, [[context["instructionRva"], context["instructionHex"]]])
    cell, usage = _checked_native(image, "vector-usage-cell", context["methodSpec"]["usageRawHex"],
        lambda: image.pe.bytes_at_va(context["methodSpec"]["usageVa"], 8).hex().upper(),
        lambda: image.nested_usage_cell(context, label=LABEL), {"instructionRva": context["instructionRva"]})
    reg, pe, md = image.registration, image.pe, image.metadata
    records = int(reg["methodSpecs"], 16)
    spec = usage_method_spec(usage, pe.bytes_at_va(records, reg["methodSpecsCount"] * 12),
                             len(md.methods), reg["genericInstsCount"], source=LABEL,
                             usage_offset=cell, records_offset=records)
    _require("vector-method-spec", context["methodSpec"], spec)
    method = md.methods[spec["definition"]]
    _require("vector-reader-owner", context["declaringType"], image.type_name(method.declaring_type))
    _require("vector-reader-method", context["methodName"], md.string(method.name_index))
    arguments = [runtime_type_name(pe, md, arg.type_pointer_va) for arg in image.instantiations.resolve(spec["methodInstantiationIndex"]).arguments]
    _require("vector-reader-argument", context["methodArguments"], arguments)
    _check_instructions(image, [[context["callRva"], context["callHex"]]])
    _require("vector-reader-core", pe.image_base + context["targetRva"],
             relative_branch_target(bytes.fromhex(context["callHex"]), pe.image_base + context["callRva"], source=LABEL))
    validate_registered_formatter_composition(image, contract["defaultComposition"], label=LABEL)
    return {"methodsChecked": len(contract["methods"]), "codeWindowsChecked": len(contract["codeWindows"]),
            "fieldOrder": [row["name"] for row in contract["fields"]], "parentProofStatus": "exact-default-stored", "runtimeProviderSelection": "unresolved"}


@lru_cache(maxsize=4)
def _authenticate(path: Path, signature: tuple[int, int], ga: Path,
                  ga_signature: tuple[int, int], metadata: Path,
                  metadata_signature: tuple[int, int]) -> dict[str, Any]:
    return _validate(open_native_image(ga, metadata), _read(path, signature))


def load_pos_rot_contract(*, game_root: Path | None = None,
                          contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(contract_path)
    audit: dict[str, Any] = {}
    try:
        signature = _signature(path)
        contract = _read(path, signature)
        expected = contract["nativeInputs"]
        root = Path(game_root) if game_root is not None else None
        native = check_installed_native_inputs(expected["GameAssembly.dll"], expected["global-metadata.dat"],
            gameassembly=root.parent / "GameAssembly.dll" if root else None,
            metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root else None)
        audit = {"validator": LABEL, "source": str(path), "nativeInputs": expected, "parentProofStatus": "unresolved",
                 "nativeSources": {"GameAssembly.dll": str(getattr(native, "gameassembly", root.parent / "GameAssembly.dll" if root else "unresolved")),
                                   "global-metadata.dat": str(getattr(native, "metadata", root / "il2cpp_data/Metadata/global-metadata.dat" if root else "unresolved"))}}
        if native.status != "validated":
            return {}, {**audit, "status": native.status, "failedCheck": "installed-native-inputs", "detail": native.detail}
        unity = native.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            return {}, {**audit, "status": "missing", "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll is absent"}
        actual_unity = sha256_file(unity)
        if actual_unity.upper() != expected["UnityPlayer.dll"].upper():
            return {}, {**audit, "status": "mismatched", "failedCheck": "UnityPlayer.dll", "detail": "selected UnityPlayer.dll hash differs", "validationFailures": [{"check": "UnityPlayer.dll", "expected": expected["UnityPlayer.dll"], "actual": actual_unity}]}
        ga_signature, metadata_signature = _signature(native.gameassembly), _signature(native.metadata)
        checked = _authenticate(path, signature, native.gameassembly, ga_signature, native.metadata, metadata_signature)
        _require("contract-unchanged", signature, _signature(path))
        _require("gameassembly-unchanged", ga_signature, _signature(native.gameassembly))
        _require("metadata-unchanged", metadata_signature, _signature(native.metadata))
        return contract, {**audit, "status": "validated", "evidenceBoundary": "exact", **checked}
    except (KeyError, IndexError, TypeError, ValueError, OSError, RuntimeError) as error:
        diagnostic = {"check": getattr(error, "check", "contract-or-native"),
                      "expected": str(getattr(error, "expected", "authenticated reviewed child"))[:500],
                      "actual": str(getattr(error, "actual", error))[:500],
                      "nativeSources": getattr(error, "native_sources", None) or audit.get("nativeSources", {}),
                      "location": getattr(error, "location", {})}
        return {}, {**audit, "status": "validation_failed", "validator": LABEL, "source": str(path),
                    "parentProofStatus": "unresolved", "failedCheck": diagnostic["check"],
                    "detail": str(error)[:500], "validationFailures": [diagnostic]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path)
    args = parser.parse_args()
    _, audit = load_pos_rot_contract(game_root=args.game_root)
    print(json.dumps(audit, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
