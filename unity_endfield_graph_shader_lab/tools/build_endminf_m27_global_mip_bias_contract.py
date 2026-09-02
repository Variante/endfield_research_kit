#!/usr/bin/env python3
"""Build the exact-build Endminf M27 global-mip-bias source contract.

The contract closes the native producer equation and its ShaderVariablesGlobal
publication.  It deliberately does not infer the selected physical-camera or
dynamic-resolution inputs from captured c26 bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "reports/assets/character_recovery/"
    "endminf_m27_global_mip_bias_contract.json"
)

EXPECTED_GAME_ASSEMBLY_SHA256 = (
    "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
)
EXPECTED_METADATA_SHA256 = (
    "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
)
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

MIP_BIAS_INVENTORY = (
    REPO_ROOT
    / "reports/assets/character_recovery/global_mip_bias/"
    "material_mip_bias_inventory.json"
)
MIP_BIAS_INVENTORY_SHA256 = (
    "a6c5100b9b39088ff46c669ab434331f53e882bc38ecd65f962f377ef80e7fe4"
)
M27_PARTICLE_ABI = (
    REPO_ROOT
    / "reports/assets/character_recovery/endminf_m27_particle_abi.json"
)
M27_PARTICLE_ABI_SHA256 = (
    "e6d6af6d6fd55368cffc5c2451f76fa64e691cfb81685f0f3f18dd68eee7f9db"
)

TYPES = {
    "additionalCameraData": (
        38091,
        0x020002D7,
        "HG.Rendering.Runtime.HGAdditionalCameraData",
    ),
    "hgCamera": (38102, 0x020002E6, "HG.Rendering.Runtime.HGCamera"),
    "dynamicResolutionHandler": (
        56898,
        0x02000087,
        "UnityEngine.Rendering.DynamicResolutionHandler",
    ),
    "globalDynamicResolutionSettings": (
        56901,
        0x0200008C,
        "UnityEngine.Rendering.GlobalDynamicResolutionSettings",
    ),
}

FIELDS = {
    "materialMipBias": (
        "additionalCameraData", 172322, 0x04001351, "materialMipBias", 0xA0
    ),
    "taaJitter": ("hgCamera", 172398, 0x0400139D, "taaJitter", 0x68),
    "globalMipBias": (
        "hgCamera",
        172465,
        0x040013E0,
        "<globalMipBias>k__BackingField",
        0x960,
    ),
    "additionalCameraData": (
        "hgCamera", 172512, 0x0400140F, "m_AdditionalCameraData", 0xAC0
    ),
    "handlerUseMipBias": (
        "dynamicResolutionHandler", 277555, 0x04000265, "m_UseMipBias", 0x11
    ),
    "settingsUseMipBias": (
        "globalDynamicResolutionSettings", 277601, 0x04000293, "useMipBias", 0x11
    ),
}

METHODS = {
    "hgCameraUpdate": {
        "type": "hgCamera",
        "index": 286739,
        "token": 0x06000E8F,
        "name": "Update",
        "va": 0x183100120,
        "end": 0x183101A30,
        "sha256": "e99e96070212c96c1a888447c81469d3952541d12c7a2e5548f7e1b2c45c9c1f",
    },
    "updateShaderVariablesGlobalCB": {
        "type": "hgCamera",
        "index": 286748,
        "token": 0x06000E98,
        "name": "UpdateShaderVariablesGlobalCB",
        "va": 0x1832E0020,
        "end": 0x1832E0B60,
        "sha256": "31937f3310ede8f299b5387a85b35bb290973c0e049d1baa5de99356a0d17539",
    },
    "calculateMipBias": {
        "type": "dynamicResolutionHandler",
        "index": 448020,
        "token": 0x0600031E,
        "name": "CalculateMipBias",
        "va": 0x183EC96B0,
        "end": 0x183EC9780,
        "sha256": "7773e057bbfcb0ed669b8f0546ac835f9e8397f03922d19bcd23d622b46f641c",
    },
    "processSettings": {
        "type": "dynamicResolutionHandler",
        "index": 448018,
        "token": 0x0600031C,
        "name": "ProcessSettings",
        "va": 0x18B2BF104,
        "end": 0x18B2BF2CC,
        "sha256": "41a7b4f7e3d57d9711cdaafd8b3c50fa94fe869621dbd3a7f2af5bc3c929392b",
    },
}

INSTRUCTION_SITES = {
    "additionalCameraDataLoad": ("hgCameraUpdate", 0x58B, "488b86c00a0000"),
    "materialMipBiasLoad": ("hgCameraUpdate", 0x59B, "f30f1080a0000000"),
    "initialGlobalMipBiasStore": (
        "hgCameraUpdate", 0x5A5, "f30f118660090000"
    ),
    "globalMipBiasBeforeDynamicTerm": (
        "hgCameraUpdate", 0x7E8, "f30f10b660090000"
    ),
    "dynamicHandlerInstanceCall": ("hgCameraUpdate", 0x7FD, "e8ce100000"),
    "dynamicUseMipBiasBranch": (
        "hgCameraUpdate", 0x80B, "443860110f85d96d"
    ),
    "noDynamicTermAndFinalStore": (
        "hgCameraUpdate",
        0x815,
        "0f57c9f30f58cef30f118e60090000",
    ),
    "c19JitterPublication": (
        "updateShaderVariablesGlobalCB", 0x453, "0f1043680f118730010000"
    ),
    "c26XPublication": (
        "updateShaderVariablesGlobalCB", 0x45E, "8b83600900008987a0010000"
    ),
    "c26YPowPublication": (
        "updateShaderVariablesGlobalCB",
        0x4B8,
        "0f28c8f20f10054d8d6708e8c842effc",
    ),
    "c26YStore": (
        "updateShaderVariablesGlobalCB", 0x4E7, "f20f5ac0f30f1187a4010000"
    ),
    "settingsUseMipBiasCopy": (
        "processSettings", 0xA8, "488b0348c1e808884711"
    ),
}

COLD_SLICES = {
    "hgCameraUpdateDynamicMipBias": {
        "va": 0x184FB770E,
        "size": 0x47,
        "sha256": "8f6e03de2f4eb702394290bd6e10069ab85a531eec79ccc8749ac3ec4efdff0f",
        "mathLogCallOffset": 0x36,
        "mathLogTarget": 0x182F115B0,
        "baseTwoVa": 0x18B959230,
    },
    "calculateMipBiasDynamicTerm": {
        "va": 0x18521CBB4,
        "size": 0x42,
        "sha256": "f7b2204298807ba8fcef01951e8be7adfcce0a95eeba8b8ca32880dcb160cee6",
        "mathLogCallOffset": 0x34,
        "mathLogTarget": 0x182F115B0,
        "baseTwoVa": 0x18B959230,
    },
}

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    pass


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _call_target(body: bytes, method_va: int, offset: int) -> int:
    if body[offset] != 0xE8:
        raise ContractError(f"expected rel32 call at {_hex(method_va + offset)}")
    return method_va + offset + 5 + struct.unpack_from("<i", body, offset + 1)[0]


def _method_pointer(md: Any, pe: Any, native: Any, method_index: int) -> int:
    modules = native.parse_codegen_modules(pe, EXPECTED_CODE_REGISTRATION)
    ranges = native.image_method_ranges(md)
    pointers, _by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    method = md.methods[method_index]
    image = md.image_name_by_type_index[method.declaring_type]
    slot = method_index - ranges[image]["methodStart"]
    return pointers[image][slot]


def _require_file(path: Path, expected_sha256: str) -> dict[str, Any]:
    if not path.is_file():
        raise ContractError(f"missing evidence file: {path}")
    digest = _sha256(path)
    if digest != expected_sha256:
        raise ContractError(f"evidence hash drift: {path}: {digest}")
    return {"path": _repo_path(path), "sha256": digest}


def _validate_type(md: Any, key: str) -> Any:
    index, token, name = TYPES[key]
    type_def = md.types[index]
    if md.type_full_name(type_def) != name or type_def.token != token:
        raise ContractError(f"type identity drift: {name}")
    return type_def


def _validate_field(md: Any, pe: Any, registration: dict[str, Any], key: str) -> dict[str, Any]:
    type_key, index, token, name, expected_offset = FIELDS[key]
    type_def = _validate_type(md, type_key)
    field = md.fields[index]
    if md.string(field.name_index) != name or field.token != token:
        raise ContractError(f"field identity drift: {TYPES[type_key][2]}.{name}")
    field_offsets = int(registration["fieldOffsets"], 16)
    type_field_offsets = pe.u64_at_va(field_offsets + type_def.index * 8)
    relative = index - type_def.field_start
    actual_offset = struct.unpack(
        "<i", pe.bytes_at_va(type_field_offsets + relative * 4, 4)
    )[0]
    if actual_offset != expected_offset:
        raise ContractError(
            f"field offset drift: {name}: {_hex(actual_offset)} != "
            f"{_hex(expected_offset)}"
        )
    return {
        "declaringType": TYPES[type_key][2],
        "fieldIndex": index,
        "token": f"0x{token:08x}",
        "name": name,
        "instanceOffsetBytes": _hex(actual_offset),
    }


def build_contract(
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if gate.status != "validated":
        raise ContractError(
            f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}"
        )

    metadata_helper = _load(
        "m27_mip_bias_metadata",
        REPO_ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py",
    )
    native = _load(
        "m27_mip_bias_native",
        REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py",
    )
    md = metadata_helper.Metadata(Path(gate.metadata))
    pe = native.PeImage(Path(gate.gameassembly))
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError("CodeRegistration drift")
    if metadata_registration != EXPECTED_METADATA_REGISTRATION:
        raise ContractError("MetadataRegistration drift")
    registration = native.metadata_registration_summary(pe, metadata_registration)

    fields = {
        key: _validate_field(md, pe, registration, key)
        for key in FIELDS
    }

    method_rows: dict[str, Any] = {}
    bodies: dict[str, bytes] = {}
    for key, expected in METHODS.items():
        type_def = _validate_type(md, expected["type"])
        method = md.methods[expected["index"]]
        if (
            method.declaring_type != type_def.index
            or method.token != expected["token"]
            or md.string(method.name_index) != expected["name"]
        ):
            raise ContractError(f"method identity drift: {key}")
        pointer = _method_pointer(md, pe, native, expected["index"])
        if pointer != expected["va"]:
            raise ContractError(f"method pointer drift: {key}: {_hex(pointer)}")
        body = pe.bytes_at_va(pointer, expected["end"] - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected["sha256"]:
            raise ContractError(f"method body drift: {key}: {digest}")
        bodies[key] = body
        method_rows[key] = {
            "declaringType": TYPES[expected["type"]][2],
            "methodIndex": expected["index"],
            "token": f"0x{expected['token']:08x}",
            "name": expected["name"],
            "virtualAddress": _hex(pointer),
            "endVirtualAddressExclusive": _hex(expected["end"]),
            "bodyBytes": len(body),
            "bodySha256": digest,
        }

    instruction_rows: dict[str, Any] = {}
    for label, (method_key, offset, expected_hex) in INSTRUCTION_SITES.items():
        expected = bytes.fromhex(expected_hex)
        actual = bodies[method_key][offset : offset + len(expected)]
        if actual != expected:
            raise ContractError(f"instruction drift: {label}: {actual.hex()}")
        instruction_rows[label] = {
            "method": method_key,
            "instructionOffset": _hex(offset),
            "instructionBytes": actual.hex(),
        }

    cold_rows: dict[str, Any] = {}
    for key, expected in COLD_SLICES.items():
        body = pe.bytes_at_va(expected["va"], expected["size"])
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected["sha256"]:
            raise ContractError(f"cold slice drift: {key}: {digest}")
        call_target = _call_target(
            body, expected["va"], expected["mathLogCallOffset"]
        )
        if call_target != expected["mathLogTarget"]:
            raise ContractError(f"Math.Log target drift: {key}")
        base = struct.unpack("<d", pe.bytes_at_va(expected["baseTwoVa"], 8))[0]
        if base != 2.0:
            raise ContractError(f"logarithm base drift: {key}: {base}")
        cold_rows[key] = {
            "virtualAddress": _hex(expected["va"]),
            "bytes": expected["size"],
            "sha256": digest,
            "mathLogCallOffset": _hex(expected["mathLogCallOffset"]),
            "mathLogTargetVa": _hex(call_target),
            "baseTwoConstantVa": _hex(expected["baseTwoVa"]),
            "baseTwoValue": base,
        }

    inventory_source = _require_file(
        MIP_BIAS_INVENTORY, MIP_BIAS_INVENTORY_SHA256
    )
    inventory = json.loads(MIP_BIAS_INVENTORY.read_text(encoding="utf-8"))
    if (
        inventory.get("schema")
        != "endfield.authored-material-mip-bias-inventory.v1"
        or inventory.get("componentCount") != 17900
        or inventory.get("valueCounts") != {"0": 17900}
        or inventory.get("allRecoveredValuesZero") is not True
        or inventory.get("nonzeroComponents") != []
    ):
        raise ContractError("serialized material-mip-bias inventory drift")

    particle_source = _require_file(M27_PARTICLE_ABI, M27_PARTICLE_ABI_SHA256)
    particle = json.loads(M27_PARTICLE_ABI.read_text(encoding="utf-8"))
    observed = particle["liveActiveConstantRanges"][
        "globalValuesUsedByPixelProgram"
    ]["b1_c26"]
    if observed[:3] != [-1.0, 0.5, 0.0]:
        raise ContractError("validation-only M27 c26 target drift")

    # This sanity check validates the source equation only. It never selects
    # these example inputs for the reconstructed runtime.
    if math.log2(1920.0 / 3840.0) != -1.0 or 2.0 ** -1.0 != 0.5:
        raise ContractError("host floating-point source-equation sanity drift")

    return {
        "schema": "endfield.endminf-m27-global-mip-bias-contract.v1",
        "status": "source_equation_closed_selected_physical_lifecycle_unobserved",
        "sourceEquationClosed": True,
        "selectedValueSourceClosed": False,
        "safeToPopulateFromCapturedC26": False,
        "nativeGate": {
            "status": gate.status,
            "gameAssembly": {
                "path": _repo_path(Path(gate.gameassembly)),
                "sha256": gate.gameassembly_sha256,
            },
            "globalMetadata": {
                "path": _repo_path(Path(gate.metadata)),
                "sha256": gate.metadata_sha256,
            },
            "codeRegistrationVa": _hex(code_registration),
            "metadataRegistrationVa": _hex(metadata_registration),
        },
        "fields": fields,
        "methods": method_rows,
        "instructionSites": instruction_rows,
        "coldSlices": cold_rows,
        "sourceEquation": {
            "materialTerm": "HGAdditionalCameraData.materialMipBias",
            "dynamicTerm": (
                "DynamicResolutionHandler.m_UseMipBias || forceApply ? "
                "log2(inputResolution.x / outputResolution.x) : 0"
            ),
            "c26x": "materialTerm + dynamicTerm",
            "c26y": "pow(2, c26x)",
            "c19AdjacentPublication": (
                "HGCamera.taaJitter is copied independently to c19 before c26"
            ),
        },
        "serializedBoundary": {
            "source": inventory_source,
            "componentCount": inventory["componentCount"],
            "allRecoveredValuesZero": True,
            "conclusion": (
                "Serialized zero values do not identify the selected persistent "
                "physical HGAdditionalCameraData instance or its runtime mutation."
            ),
        },
        "validationOnlyTarget": {
            "source": particle_source,
            "capturedC26": observed,
            "authority": "validation_only_not_runtime_population",
            "conclusion": (
                "The final c26 pair does not partition the material and dynamic "
                "terms and therefore cannot select a source producer."
            ),
        },
        "requiredRuntimeReceipt": {
            "schema": "endfield.endminf-m27-global-mip-bias-receipt.v1",
            "sameEpochRequired": True,
            "requiredIdentities": [
                "exact build hashes",
                "physical HGCamera instance",
                "HGAdditionalCameraData instance",
                "DynamicResolutionHandler instance",
                "exact M27 renderer/shader draw",
            ],
            "requiredValues": [
                "materialMipBias float32 bits before HGCamera.Update copy",
                "m_UseMipBias and forceApply branch state",
                "inputResolution.x and outputResolution.x",
                "computed dynamic term float32 bits",
                "HGCamera.globalMipBias float32 bits after addition",
                "published c26.x and c26.y float32 bits",
            ],
            "requiredOrdering": [
                "source fields sampled before c26 publication",
                "c26 publication before the exact M27 draw",
                "no intervening camera/handler identity change",
            ],
            "failureConditions": [
                "zero or mismatched identities",
                "missing, duplicated, truncated, or lost records",
                "non-finite values or nonpositive dimensions",
                "source-equation or bit mismatch",
                "draw epoch or shader/renderer mismatch",
            ],
        },
        "decision": {
            "canSourceCloseSelectedC26WithoutRuntimeReceipt": False,
            "reason": (
                "The pinned binary closes the two-term producer equation, but "
                "static assets do not establish the selected physical camera, "
                "active DynamicResolutionHandler, branch state, or input/output "
                "extent pair at the exact M27 draw."
            ),
            "presentationAuthority": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        payload = build_contract(args.gameassembly, args.metadata)
    except (ContractError, KeyError, TypeError, ValueError) as exc:
        print(f"Endminf M27 global-mip-bias contract failed: {exc}", file=sys.stderr)
        return 1
    serialized = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.is_file():
            print(f"missing generated contract: {args.output}", file=sys.stderr)
            return 1
        if args.output.read_text(encoding="utf-8") != serialized:
            print(f"generated contract drift: {args.output}", file=sys.stderr)
            return 1
        print(f"Endminf M27 global-mip-bias contract check passed: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(serialized, encoding="utf-8")
    print(f"Endminf M27 global-mip-bias contract passed: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
