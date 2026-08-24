#!/usr/bin/env python3
"""Build the pinned native AnchorWaveBright contract used by Endminf M27.

This closes the managed HGVFXManager setter/getter and the global-CB publisher.
It intentionally does not guess a CharInfo selected-frame value when no runtime
capture or serialized publisher input establishes one.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_OUTPUT = REPO_ROOT / "reports/assets/character_recovery/endminf_anchor_wave_bright_contract.json"

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
EXPECTED_CODE_REGISTRATION = 0x18B9217D0
EXPECTED_METADATA_REGISTRATION = 0x18B921C30

TYPE_NAME = "HG.Rendering.Runtime.HGVFXManager"
TYPE_INDEX = 37934
TYPE_TOKEN = 0x02000245
FIELDS = {
    "m_anchorPosition": (171293, 0x04000F4C, 0x70),
    "m_anchorRadius": (171294, 0x04000F4D, 0x78),
    "m_anchorBrightIntensity": (171295, 0x04000F4E, 0x7C),
    "m_brightInnerRadius": (171296, 0x04000F4F, 0x80),
    "m_brightOuterRadius": (171297, 0x04000F50, 0x84),
    "m_anchorBrightFlag": (171298, 0x04000F51, 0x88),
}

METHODS = {
    "SetAnchorWaveBright": {
        "index": 285884, "token": 0x06000B38,
        "va": 0x189B599E8, "end": 0x189B59AF4,
        "sha256": "252474358c40153ae9681b3b8ad6eaa001e3b9a9e0cc9bd49f91ed27f8093b8f",
    },
    "GetAnchorWaveBright": {
        "index": 285885, "token": 0x06000B39,
        "va": 0x183104670, "end": 0x183104890,
        "sha256": "829cc7835b73c9dae9f0b299604ff0498ae99e1ada5a54a1408b0e6425ec4549",
    },
    "UpdateShaderVariablesGlobalVFX": {
        "type": "HG.Rendering.Runtime.HGRenderPathBase",
        "index": 287947, "token": 0x06001347,
        "va": 0x189BDE508, "end": 0x189BDE6B0,
        "sha256": "29c6e5d227133143db585788aa1da0b84f45d9b898ffffb4920fa61a9c48593b",
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


def _hex(value: int) -> str:
    return f"0x{value:x}"


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _method_pointer(md: Any, pe: Any, native: Any, method_index: int) -> int:
    modules = native.parse_codegen_modules(pe, EXPECTED_CODE_REGISTRATION)
    ranges = native.image_method_ranges(md)
    pointers, _by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    method = md.methods[method_index]
    image = md.image_name_by_type_index[method.declaring_type]
    slot = method_index - ranges[image]["methodStart"]
    return pointers[image][slot]


def _require_bytes(body: bytes, offset: int, expected: str, label: str) -> dict[str, Any]:
    wanted = bytes.fromhex(expected)
    actual = body[offset:offset + len(wanted)]
    if actual != wanted:
        raise ContractError(f"{label} drift at 0x{offset:x}: {actual.hex()} != {wanted.hex()}")
    return {"instructionOffset": _hex(offset), "instructionBytes": actual.hex()}


def _call_target(body: bytes, method_va: int, offset: int) -> int:
    if body[offset] != 0xE8:
        raise ContractError(f"expected direct call at {_hex(method_va + offset)}")
    return method_va + offset + 5 + struct.unpack_from("<i", body, offset + 1)[0]


def build_contract(gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    gate = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if gate.status != "validated":
        raise ContractError(f"common.check_installed_native_inputs [{gate.status}]: {gate.detail}")

    catalog = _load("anchor_wave_catalog", REPO_ROOT / "tools/endfield-il2cpp/catalog_option_flow_metadata.py")
    native = _load("anchor_wave_native", REPO_ROOT / "tools/endfield-il2cpp/map_body_targets_to_gameassembly.py")
    md = catalog.Metadata(Path(gate.metadata))
    pe = native.PeImage(Path(gate.gameassembly))
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if code_registration != EXPECTED_CODE_REGISTRATION:
        raise ContractError(f"code registration drift: {_hex(code_registration)}")
    if metadata_registration != EXPECTED_METADATA_REGISTRATION:
        raise ContractError(f"metadata registration drift: {_hex(metadata_registration or 0)}")

    type_def = md.types[TYPE_INDEX]
    if md.type_full_name(type_def) != TYPE_NAME or type_def.token != TYPE_TOKEN:
        raise ContractError("HGVFXManager type identity drift")
    registration = native.metadata_registration_summary(pe, metadata_registration)
    field_offsets_pointer = pe.u64_at_va(int(registration["fieldOffsets"], 16) + TYPE_INDEX * 8)
    fields = []
    for name, (index, token, offset) in FIELDS.items():
        field = md.fields[index]
        relative = index - type_def.field_start
        actual_offset = struct.unpack(
            "<i", pe.bytes_at_va(field_offsets_pointer + relative * 4, 4)
        )[0]
        if md.string(field.name_index) != name or field.token != token or actual_offset != offset:
            raise ContractError(f"{TYPE_NAME}.{name} declaration/layout drift")
        fields.append({
            "name": name, "fieldIndex": index, "token": f"0x{token:08x}",
            "instanceOffsetBytes": _hex(offset),
        })

    verified_methods: dict[str, dict[str, Any]] = {}
    bodies: dict[str, bytes] = {}
    for name, expected in METHODS.items():
        method = md.methods[expected["index"]]
        declaring_type = md.type_full_name(md.types[method.declaring_type])
        expected_type = expected.get("type", TYPE_NAME)
        if (declaring_type != expected_type or md.string(method.name_index) != name
                or method.token != expected["token"]):
            raise ContractError(f"{expected_type}.{name} metadata identity drift")
        pointer = _method_pointer(md, pe, native, expected["index"])
        if pointer != expected["va"]:
            raise ContractError(f"{name} pointer drift: {_hex(pointer)}")
        body = pe.bytes_at_va(pointer, expected["end"] - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected["sha256"]:
            raise ContractError(f"{name} body hash drift: {digest}")
        bodies[name] = body
        verified_methods[name] = {
            "declaringType": declaring_type,
            "methodIndex": expected["index"], "token": f"0x{method.token:08x}",
            "virtualAddress": _hex(pointer), "endVirtualAddressExclusive": _hex(expected["end"]),
            "bodyBytes": len(body), "bodySha256": digest,
        }

    setter = bodies["SetAnchorWaveBright"]
    setter_sites = {
        "anchorPositionX": _require_bytes(setter, 0x81, "f30f114070", "anchorPosition.x store"),
        "anchorPositionY": _require_bytes(setter, 0x86, "f30f114874", "anchorPosition.y store"),
        "anchorRadius": _require_bytes(setter, 0x97, "f30f117878", "anchorRadius store"),
        "anchorBrightIntensity": _require_bytes(setter, 0xA8, "f30f11707c", "anchorBrightIntensity store"),
        "anchorBrightFlag": _require_bytes(setter, 0xB7, "889888000000", "anchorBrightFlag store"),
    }
    fallback_target = _call_target(setter, METHODS["SetAnchorWaveBright"]["va"], 0xEE)
    if fallback_target != 0x189CD6038:
        raise ContractError("SetAnchorWaveBright alternate implementation target drift")

    getter = bodies["GetAnchorWaveBright"]
    getter_sites = {
        "flagTest": _require_bytes(getter, 0xAA, "80b88800000000", "anchorBrightFlag test"),
        "falseValue": _require_bytes(getter, 0xB7, "33c0", "false flag value"),
        "positionX": _require_bytes(getter, 0xE6, "f30f107070", "position.x load"),
        "positionY": _require_bytes(getter, 0xFB, "f3440f105074", "position.y load"),
        "radius": _require_bytes(getter, 0x111, "f3440f104878", "radius load"),
        "intensity": _require_bytes(getter, 0x12E, "f30f10787c", "intensity load"),
        "multiplyByFlag": _require_bytes(getter, 0x147, "f3410f59f8", "intensity flag multiply"),
        "returnVector": _require_bytes(getter, 0x193, "0f1133", "Vector4 return store"),
    }
    true_branch = pe.bytes_at_va(0x184FB92AF, 10)
    if true_branch != bytes.fromhex("b801000000e970b414fe"):
        raise ContractError("GetAnchorWaveBright true-flag branch drift")

    publisher = bodies["UpdateShaderVariablesGlobalVFX"]
    publisher_call = _call_target(publisher, METHODS["UpdateShaderVariablesGlobalVFX"]["va"], 0x113)
    if publisher_call != METHODS["GetAnchorWaveBright"]["va"]:
        raise ContractError("UpdateShaderVariablesGlobalVFX getter call drift")
    publisher_store = _require_bytes(
        publisher, 0x122, "f30f7f8790060000", "ShaderVariablesGlobal c105 store"
    )

    return {
        "schema": "endfield.charinfo.endminf-anchor-wave-bright-contract.v1",
        "status": "native_contract_closed_selected_frame_value_unobserved",
        "nativeContractClosed": True,
        "selectedFrameValueClosed": False,
        "safeToInventSelectedFrameValue": False,
        "nativeGate": {
            "status": gate.status,
            "gameAssembly": {"path": _repo_path(Path(gate.gameassembly)), "sha256": gate.gameassembly_sha256},
            "globalMetadata": {"path": _repo_path(Path(gate.metadata)), "sha256": gate.metadata_sha256},
            "codeRegistrationVa": _hex(code_registration),
            "metadataRegistrationVa": _hex(metadata_registration),
        },
        "owner": {"type": TYPE_NAME, "typeIndex": TYPE_INDEX, "token": f"0x{TYPE_TOKEN:08x}"},
        "fields": fields,
        "methods": verified_methods,
        "setterContract": {
            "signature": "SetAnchorWaveBright(Vector2 anchorPosition, float anchorRadius, float anchorBrightIntensity, bool anchorBrightFlag)",
            "semantics": "the visible managed path stores the four inputs without clamping or remapping",
            "stores": setter_sites,
            "alternateImplementation": {"callOffset": "0xee", "targetVa": _hex(fallback_target),
                "boundary": "same four arguments are forwarded; callee identity is not promoted here"},
        },
        "getterContract": {
            "signature": "Vector4 GetAnchorWaveBright()",
            "value": ["m_anchorPosition.x", "m_anchorPosition.y", "m_anchorRadius",
                      "m_anchorBrightIntensity * (m_anchorBrightFlag ? 1.0 : 0.0)"],
            "sites": getter_sites,
            "trueFlagBranch": {"virtualAddress": "0x184fb92af", "instructionBytes": true_branch.hex(),
                               "value": 1},
            "falseFlagValue": 0,
        },
        "shaderVariablesGlobalPublisher": {
            "method": "HG.Rendering.Runtime.HGRenderPathBase.UpdateShaderVariablesGlobalVFX",
            "getterCallOffset": "0x113", "getterCallTargetVa": _hex(publisher_call),
            "destinationByteOffset": "0x690", "destinationRegister": "c105",
            "destinationComponents": {"z": "anchor radius", "w": "enabled-gated bright intensity"},
            "store": publisher_store,
        },
        "constructionBoundary": {
            "managedFieldsAreZeroInitialized": True,
            "defaultGetterValueBeforeAnySetter": [0.0, 0.0, 0.0, 0.0],
            "selectedCharInfoFrameInference": "not_source_proven",
            "reason": "No synchronized runtime capture or serialized CharInfo publisher input establishes whether SetAnchorWaveBright ran before the selected M27 frame.",
        },
        "m27Decision": {
            "c105LayoutAndPublisherClosed": True,
            "c105SelectedFrameValueClosed": False,
            "admissionImpact": "The recovery may bind a captured/source-proven c105 value, but must not substitute the construction default as a selected-frame fact.",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        payload = build_contract(args.gameassembly, args.metadata)
    except ContractError as exc:
        print(f"Endminf AnchorWaveBright contract failed: {exc}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Endminf AnchorWaveBright contract passed: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
