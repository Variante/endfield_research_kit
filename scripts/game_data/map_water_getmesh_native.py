"""Validate the reviewed WaterVolume.GetMesh and initial-height call chain.

This proves the selected native branch and inputs, not a live water transform.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract


CONTRACT = CONTRACTS_DIR / "map_water_getmesh_native.json"
SCHEMA = "endfield.map-water-getmesh-native-contract.v4"
LABEL = "map_water_getmesh"


def _check_anchors_and_calls(index: BodyIndex, body: Any, code: bytes, method_row: dict[str, Any]) -> None:
    pe = index.image.pe
    for anchor in method_row["instructionAnchors"]:
        offset = anchor["offset"]
        expected_bytes = bytes.fromhex(anchor["bytesHex"])
        if code[offset:offset + len(expected_bytes)] != expected_bytes:
            raise ValueError(f"{LABEL}.native:instruction={anchor['role']}@{offset}")
    for branch in method_row.get("conditionalBranches", []):
        offset = branch["offset"]
        expected_bytes = bytes.fromhex(branch["bytesHex"])
        if (code[offset:offset + len(expected_bytes)] != expected_bytes
                or (len(expected_bytes) == 6 and not (expected_bytes[0] == 0x0F and 0x80 <= expected_bytes[1] <= 0x8F))
                or (len(expected_bytes) == 2 and not 0x70 <= expected_bytes[0] <= 0x7f)
                or len(expected_bytes) not in (2, 6)):
            raise ValueError(f"{LABEL}.native:conditional-bytes={branch['role']}@{offset}")
        displacement = struct.unpack_from("<i" if len(expected_bytes) == 6 else "<b", expected_bytes, 2 if len(expected_bytes) == 6 else 1)[0]
        if offset + len(expected_bytes) + displacement != branch["targetOffset"]:
            raise ValueError(f"{LABEL}.native:conditional-target={branch['role']}@{offset}")
    for opcode, branches in ((0xE8, method_row["directCalls"]), (0xE9, method_row.get("directBranches", []))):
        for branch in branches:
            offset = branch["offset"]
            expected_bytes = bytes.fromhex(branch["bytesHex"])
            if len(expected_bytes) != 5 or expected_bytes[0] != opcode or code[offset:offset + 5] != expected_bytes:
                raise ValueError(f"{LABEL}.native:branch-bytes={branch['method']}@{offset}")
            displacement = struct.unpack_from("<i", expected_bytes, 1)[0]
            target = body.pointer + offset + 5 + displacement
            if target != pe.image_base + branch["targetRva"]:
                raise ValueError(f"{LABEL}.native:branch-target={branch['method']}@{offset}")
            if branch["method"] not in index.names_of(target):
                raise ValueError(f"{LABEL}.native:branch-name={branch['method']}@{offset}")


def _validate_body(index: BodyIndex, method_row: dict[str, Any], *, check_hash_location: bool = False) -> dict[str, Any]:
    image = index.image
    metadata = image.metadata
    owner = method_row["typeName"]
    name = method_row["name"]
    matches = [
        method
        for type_def in metadata.types
        if metadata.type_full_name(type_def) == owner
        for method in metadata.methods_for(type_def)
        if metadata.string(method.name_index) == name
    ]
    if len(matches) != 1:
        raise ValueError(f"{LABEL}.native:method-identity={owner}.{name}:{len(matches)}")
    method = matches[0]
    if method.token != method_row["token"]:
        raise ValueError(f"{LABEL}.native:method-token={method.token}")
    if "returnType" in method_row and metadata.metadata_type_name(method.return_type) != method_row["returnType"]:
        raise ValueError(f"{LABEL}.native:return-type={owner}.{name}")
    parameters = [
        [metadata.string(param.name_index), metadata.metadata_type_name(param.type_index)]
        for param in metadata.parameters_for(method)
    ]
    expected = method_row["parameters"]
    if len(parameters) != len(expected) or any(
        actual[0] != target[0] or (target[1] is not None and actual[1] != target[1])
        for actual, target in zip(parameters, expected)
    ):
        raise ValueError(f"{LABEL}.native:parameters={parameters!r}")

    body = index.body(owner, name)
    pe = image.pe
    if body.pointer != pe.image_base + method_row["rva"] or image.method_pointer_va(method) != body.pointer:
        raise ValueError(f"{LABEL}.native:method-pointer={owner}.{name}")
    if body.size != method_row["bodySize"]:
        raise ValueError(f"{LABEL}.native:body-size={body.size}")
    code = pe.bytes_at_va(body.pointer, body.size)
    if hashlib.sha256(code).hexdigest().upper() != method_row["bodySha256"].upper():
        raise ValueError(f"{LABEL}.native:body-sha256={owner}.{name}")
    _check_anchors_and_calls(index, body, code, method_row)
    result = {
        "method": f"{owner}.{name}",
        "rva": method_row["rva"],
        "bodySize": body.size,
        "directCallCount": len(method_row["directCalls"]),
    }
    if check_hash_location:
        location = index.parameter_location(body.pointer, f"{owner}.{name}", "meshPathHash")
        if location != ("stack", method_row["meshPathHashEntryStackOffset"]):
            raise ValueError(f"{LABEL}.native:mesh-path-hash-location={location!r}")
        result["meshPathHashLocation"] = list(location)
    return result


def validate_map_water_getmesh_native_contract(contract_path: Path = CONTRACT) -> dict[str, Any]:
    """Return a fail-closed receipt for the installed build."""
    report: dict[str, Any] = {"schema": "endfield.map-water-getmesh-native-validation.v4", "status": "unresolved"}
    try:
        contract, digest = read_reviewed_contract(
            contract_path, schema=SCHEMA, label=LABEL, status="validated"
        )
        report["contractSha256"] = digest
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            inputs["gameAssemblySha256"], inputs["metadataSha256"]
        )
        report["nativeGate"] = {"status": gate.status, "detail": gate.detail}
        if gate.status != "validated":
            report["status"] = gate.status
            return report
        unity = gate.gameassembly.parent / "UnityPlayer.dll"
        if not unity.is_file():
            report.update(status="missing", diagnostic=f"{LABEL}.native:UnityPlayer.dll missing")
            return report
        actual_unity = sha256_file(unity).upper()
        if actual_unity != inputs["unityPlayerSha256"].upper():
            report.update(status="mismatched", diagnostic=f"{LABEL}.native:UnityPlayer.dll hash differs")
            return report
        image = NativeImage(gate.gameassembly, gate.metadata, label=LABEL)
        index = BodyIndex(image)
        report["method"] = _validate_body(index, contract["method"], check_hash_location=True)
        chain = contract["callerChain"]
        for field, expected_offset in chain["fieldOffsets"].items():
            actual_offset = index.field_offset(field)
            if actual_offset != expected_offset:
                raise ValueError(f"{LABEL}.native:field-offset={field}:{actual_offset}")
        report["callerChain"] = [_validate_body(index, row) for row in chain["methods"]]
        report["heightChain"] = [_validate_body(index, row) for row in contract["heightChain"]["methods"]]
        report["runtimeHeightPath"] = [_validate_body(index, row) for row in contract["runtimeHeightPath"]["methods"]]
        witness = contract["captureWitness"]
        id_field = witness["gameLevelIdField"]
        if index.field_offset(id_field["qualifiedName"]) != id_field["offset"]:
            raise ValueError(f"{LABEL}.native:game-level-id-field")
        report["captureWitness"] = {
            "gameLevelIdGetter": _validate_body(index, witness["gameLevelIdGetter"]),
            "updataMesh": _validate_body(index, witness["updataMesh"]),
        }
        for location in witness["parameterLocations"]:
            body = index.body(location["typeName"], location["name"])
            actual = index.parameter_location(
                body.pointer, f'{location["typeName"]}.{location["name"]}',
                location["parameter"]
            )
            if actual != tuple(location["location"]):
                raise ValueError(
                    f'{LABEL}.native:capture-parameter-location={location["name"]}.{location["parameter"]}:{actual!r}'
                )
        final = contract["finalTransformWitness"]
        token = final["waterVolumePtrField"]
        if (index.field_offset(token["qualifiedName"]) != token["offset"] or
                token["bytes"] != 16):
            raise ValueError(f"{LABEL}.native:surface-volume-token-field")
        report["finalTransformWitness"] = [
            _validate_body(index, row) for row in final["methods"]
        ]
        report["status"] = "validated"
    except (KeyError, TypeError, ValueError, RuntimeError, IndexError, OSError) as exc:
        report.update(status="unresolved", diagnostic=str(exc))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=CONTRACT)
    args = parser.parse_args()
    report = validate_map_water_getmesh_native_contract(args.contract)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
