"""Authenticate selected native LevelData spline ownership and movement use."""

from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets


SCHEMA = "endfield.leveldata-spline-runtime-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "leveldata_spline_runtime_native.json"


def validate_spline_runtime_native(
    *, contract_path: Path = DEFAULT_CONTRACT, game_root: Path | None = None,
) -> dict[str, Any]:
    """Fail closed on build drift and every reviewed spline consumer anchor."""

    failures: list[dict[str, Any]] = []

    def reject(gate: str, expected: Any, actual: Any) -> None:
        failures.append({"gate": gate, "expected": expected, "actual": actual})

    try:
        raw = Path(contract_path).read_bytes()
        contract = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"status": "validation_failed", "validationFailures": [{
            "gate": "read_contract", "expected": "reviewed JSON", "actual": str(exc)[:400],
        }]}
    if contract.get("schema") != SCHEMA:
        reject("schema", SCHEMA, contract.get("schema"))
    if contract.get("status") != "validated":
        reject("contract_status", "validated", contract.get("status"))

    expected_inputs = contract.get("nativeInputs") or {}
    root = Path(game_root) if game_root is not None else None
    native = check_installed_native_inputs(
        str(expected_inputs.get("GameAssembly.dll", "")),
        str(expected_inputs.get("global-metadata.dat", "")),
        gameassembly=root.parent / "GameAssembly.dll" if root is not None else None,
        metadata=root / "il2cpp_data/Metadata/global-metadata.dat" if root is not None else None,
    )
    result: dict[str, Any] = {
        "status": native.status,
        "contractSha256": hashlib.sha256(raw).hexdigest().upper(),
        "nativeInputs": {
            "GameAssembly.dll": native.gameassembly_sha256.upper(),
            "global-metadata.dat": native.metadata_sha256.upper(),
        },
        "nativeGateDetail": native.detail,
        "evidenceBoundary": contract.get("evidenceBoundary"),
        "validationFailures": failures,
    }
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        return result

    unity_path = native.gameassembly.parent / "UnityPlayer.dll"
    unity_sha = sha256_file(unity_path).upper() if unity_path.is_file() else ""
    result["nativeInputs"]["UnityPlayer.dll"] = unity_sha
    if unity_sha != str(expected_inputs.get("UnityPlayer.dll", "")).upper():
        reject("unityplayer_sha256", expected_inputs.get("UnityPlayer.dll"), unity_sha)
    if failures:
        result["status"] = "validation_failed"
        return result

    try:
        image = NativeImage(native.gameassembly, native.metadata, label="leveldata-spline-runtime")
        methods = contract["methods"]
        for label, row in methods.items():
            if len(row) != 4:
                raise ValueError(f"method-row:{label}")
            image.validate_method_row(row)
        generic = contract["genericMethod"]
        if len(generic) != 3:
            raise ValueError("generic-method-row")
        image.validate_method_row(generic)

        windows = contract["bodyWindows"]
        if {window["startRva"] for window in windows} != {
            methods[label][3] for label in ("splineTable", "onEnter", "processVelocity")
        }:
            raise ValueError("body-window-method-starts")
        image.check_windows(windows)

        type_rows = {
            image.metadata.type_full_name(row): row for row in image.metadata.types
            if image.metadata.type_full_name(row) in contract["fieldOffsets"]
        }
        for type_name, wanted in contract["fieldOffsets"].items():
            if type_name not in type_rows:
                raise ValueError(f"field-type-missing:{type_name}")
            actual = runtime_type_field_offsets(
                image.metadata, image.pe, image.registration, type_rows[type_name].index,
            )
            for field_name, offset in wanted.items():
                if actual.get(field_name) != offset:
                    reject(f"field_offset:{type_name}.{field_name}", offset, actual.get(field_name))

        body_index: BodyIndex | None = None
        for call in contract["callSites"]:
            caller = methods[call["caller"]]
            call_va = image.pe.image_base + caller[3] + call["offset"]
            raw_call = image.pe.bytes_at_va(call_va, 5)
            if raw_call[0] != 0xE8:
                raise ValueError(f"call-opcode:{call['caller']}+{call['offset']:#x}")
            target_va = call_va + 5 + struct.unpack_from("<i", raw_call, 1)[0]
            if "target" in call:
                target_method = methods[call["target"]]
                expected_va = image.method_pointer_va(image.metadata.methods[target_method[0]])
                if target_va != expected_va:
                    reject(f"call_target:{call['caller']}+{call['offset']:#x}",
                           hex(expected_va), hex(target_va))
            else:
                expected_va = image.pe.image_base + call["targetRva"]
                if target_va != expected_va:
                    reject(f"generic_call_target:{call['caller']}+{call['offset']:#x}",
                           hex(expected_va), hex(target_va))
                else:
                    if body_index is None:
                        body_index = BodyIndex(image)
                    names = body_index.names_of(target_va)
                    if call["genericName"] not in names:
                        reject(f"generic_call_name:{call['caller']}+{call['offset']:#x}",
                               call["genericName"], names[:8])
    except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
        reject("selected_native_spline_runtime", "method bodies, fields and calls validated", str(exc)[:400])

    result["status"] = NATIVE_EVIDENCE_VALIDATED if not failures else "validation_failed"
    return result


if __name__ == "__main__":
    value = validate_spline_runtime_native()
    print(json.dumps(value, indent=2))
    raise SystemExit(0 if value["status"] == NATIVE_EVIDENCE_VALIDATED else 1)


__all__ = ["DEFAULT_CONTRACT", "validate_spline_runtime_native"]
