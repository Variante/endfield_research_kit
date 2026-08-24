#!/usr/bin/env python3
"""Recover native element layouts for serialized secondary-dynamics proxy arrays.

The payload decoder historically retained these arrays as raw bytes because
their serialized records do not carry a stride.  This builder closes that
boundary from the pinned IL2CPP ``VirtualMesh`` and ``TransformData`` field
declarations.  It publishes element identities and strides only; it does not
instantiate a solver, schedule Burst jobs, or write Transforms.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

import build_secondary_dynamics_element_layout_contract as element_layout


LAB_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_proxy_layout_contract.json"
)

VIRTUAL_MESH = ("BeyondDynamicBone.VirtualMesh", 48620, 230909, 62)
SHARE_DATA = ("BeyondDynamicBone.VirtualMesh+ShareSerializationData", 48610, 231259, 55)
TRANSFORM_DATA = ("BeyondDynamicBone.TransformData", 48446, 230557, 16)
TRANSFORM_SHARE_DATA = ("BeyondDynamicBone.TransformData+ShareSerializationData", 48444, 230584, 3)

SERIALIZER_METHODS = {
    "serialize": {
        "methodIndex": 386635, "method": "ShareSerialize", "token": "0x06000c14",
        "va": 0x1866BE154, "endVa": 0x1866BEB44,
        "bodySha256": "fb553ce505afefa75eb06817016c5f1c244d1af4eb9d4fde8ef7d041f67fd166",
        "ifixPatchId": 0x555, "ifixCallOffset": 371,
    },
    "deserialize": {
        "methodIndex": 386636, "method": "ShareDeserialize", "token": "0x06000c15",
        "va": 0x183E8FE60, "endVa": 0x183E90A00,
        "bodySha256": "283daa75da452fdda631e2608af23a7b1e1f143c9eadb128ae30257ebfa8eeae",
        "ifixPatchId": 0x60, "ifixCallOffset": 55,
    },
}

TRANSFORM_SERIALIZER_METHODS = {
    "serialize": {
        "methodIndex": 385816, "method": "ShareSerialize", "token": "0x060008e1",
        "va": 0x186789E9C, "endVa": 0x18678A050,
        "bodySha256": "08698043ad28ccba1fedfae3b4019a8c4bbbf0d1a4d34484c0c6e5a80ed5f259",
        "ifixPatchId": 0x49A, "ifixCallOffset": 86,
    },
    "deserialize": {
        "methodIndex": 385817, "method": "ShareDeserialize", "token": "0x060008e2",
        "va": 0x183E8FA80, "endVa": 0x183E8FE60,
        "bodySha256": "3032c4024914e56830fb4b1be6250e15cd858cd9c491b24dc9fec44d693ab287",
        "ifixPatchId": 0x61, "ifixCallOffset": 36,
    },
}

TRANSFORM_LAYOUT_SPECS = (
    ("transformData.flagArray", "flagArray", 33190, "uint8", 88930, 0x18, 0x10),
    ("transformData.initLocalPositionArray", "initLocalPositionArray", 33196, "float3", 88935, 0x20, 0x18),
    ("transformData.initLocalRotationArray", "initLocalRotationArray", 33201, "float4", 88939, 0x28, 0x20),
)

# The offsets are boxed managed-object field offsets.  They are repeated here
# only as fail-closed expectations; the observed values are read from
# MetadataRegistration.fieldOffsets on every build.
ASSIGNMENT_OFFSETS = {
    "referenceIndices": (0x30, 0x20), "attributes": (0x38, 0x28),
    "localPositions": (0x40, 0x30), "localNormals": (0x48, 0x38),
    "localTangents": (0x50, 0x40), "uv": (0x58, 0x48),
    "boneWeights": (0x60, 0x50), "triangles": (0x68, 0x58),
    "lines": (0x70, 0x60), "skinBoneTransformIndices": (0x130, 0x120),
    "skinBoneBindPoses": (0x138, 0x128), "vertexToTriangles": (0x190, 0x170),
    "vertexToVertexIndexArray": (0x1A0, 0x178),
    "vertexToVertexDataArray": (0x1B0, 0x180), "edges": (0x1C0, 0x188),
    "edgeFlags": (0x1D0, 0x190),
    "edgeToTrianglesKeys": (0x1E0, 0x198),
    "edgeToTrianglesValues": (0x1E0, 0x1A0),
    "vertexBindPosePositions": (0x1F0, 0x1A8),
    "vertexBindPoseRotations": (0x200, 0x1B0),
    "vertexToTransformRotations": (0x210, 0x1B8),
    "vertexDepths": (0x220, 0x1C0), "vertexRootIndices": (0x230, 0x1C8),
    "vertexParentIndices": (0x240, 0x1D0),
    "vertexChildIndexArray": (0x250, 0x1D8),
    "vertexChildDataArray": (0x260, 0x1E0),
    "vertexLocalPositions": (0x270, 0x1E8),
    "vertexLocalRotations": (0x280, 0x1F0),
    "normalAdjustmentRotations": (0x290, 0x1F8),
    "baseLineFlags": (0x2A0, 0x200),
    "baseLineStartDataIndices": (0x2B0, 0x208),
    "baseLineDataCounts": (0x2C0, 0x210), "baseLineData": (0x2D0, 0x218),
    "customSkinningBoneIndices": (0x2E0, 0x220),
    "centerFixedList": (0x2E8, 0x228),
}

# serialized field, corresponding runtime field, runtime metadata type index,
# selected runtime generic argument (None for SZARRAY, 0 for one-argument
# containers, 0/1 for the hash-map split), decoder kind.
LAYOUT_SPECS = (
    ("referenceIndices", "referenceIndices", 33192, 0, "int32"),
    ("attributes", "attributes", 33193, 0, "uint8"),
    ("localPositions", "localPositions", 33197, 0, "float3"),
    ("localNormals", "localNormals", 33197, 0, "float3"),
    ("localTangents", "localTangents", 33197, 0, "float3"),
    ("uv", "uv", 33195, 0, "float2"),
    ("boneWeights", "boneWeights", 33194, 0, "opaque"),
    ("triangles", "triangles", 33200, 0, "int3"),
    ("lines", "lines", 33199, 0, "int2"),
    ("skinBoneTransformIndices", "skinBoneTransformIndices", 33192, 0, "int32"),
    ("skinBoneBindPoses", "skinBoneBindPoses", 33198, 0, "float16"),
    ("vertexToTriangles", "vertexToTriangles", 83078, 0, "opaque"),
    ("vertexToVertexIndexArray", "vertexToVertexIndexArray", 83269, 0, "uint32"),
    ("vertexToVertexDataArray", "vertexToVertexDataArray", 83266, 0, "uint16"),
    ("edges", "edges", 83311, 0, "int2"),
    ("edgeFlags", "edgeFlags", 83139, 0, "uint8"),
    ("edgeToTrianglesKeys", "edgeToTriangles", 83598, 0, "int2"),
    ("edgeToTrianglesValues", "edgeToTriangles", 83598, 1, "uint16"),
    ("vertexBindPosePositions", "vertexBindPosePositions", 83304, 0, "float3"),
    ("vertexBindPoseRotations", "vertexBindPoseRotations", 83315, 0, "float4"),
    ("vertexToTransformRotations", "vertexToTransformRotations", 83315, 0, "float4"),
    ("vertexDepths", "vertexDepths", 83240, 0, "float32"),
    ("vertexRootIndices", "vertexRootIndices", 83201, 0, "int32"),
    ("vertexParentIndices", "vertexParentIndices", 83201, 0, "int32"),
    ("vertexChildIndexArray", "vertexChildIndexArray", 83269, 0, "uint32"),
    ("vertexChildDataArray", "vertexChildDataArray", 83266, 0, "uint16"),
    ("vertexLocalPositions", "vertexLocalPositions", 83304, 0, "float3"),
    ("vertexLocalRotations", "vertexLocalRotations", 83315, 0, "float4"),
    ("normalAdjustmentRotations", "normalAdjustmentRotations", 83315, 0, "float4"),
    ("baseLineFlags", "baseLineFlags", 83139, 0, "uint8"),
    ("baseLineStartDataIndices", "baseLineStartDataIndices", 83266, 0, "uint16"),
    ("baseLineDataCounts", "baseLineDataCounts", 83266, 0, "uint16"),
    ("baseLineData", "baseLineData", 83266, 0, "uint16"),
    ("customSkinningBoneIndices", "customSkinningBoneIndices", 118931, None, "int32"),
    ("centerFixedList", "centerFixedList", 119545, None, "uint16"),
)

SHARE_FIELD_TYPE_INDICES = {
    "referenceIndices": 88931, "attributes": 88932,
    "localPositions": 88935, "localNormals": 88935, "localTangents": 88935,
    "uv": 88934, "boneWeights": 88933, "triangles": 88938, "lines": 88937,
    "skinBoneTransformIndices": 88931, "skinBoneBindPoses": 88936,
    **{name: 118327 for name in (
        "vertexToTriangles", "vertexToVertexIndexArray", "vertexToVertexDataArray",
        "edges", "edgeFlags", "vertexBindPosePositions", "vertexBindPoseRotations",
        "vertexToTransformRotations", "vertexDepths", "vertexRootIndices",
        "vertexParentIndices", "vertexChildIndexArray", "vertexChildDataArray",
        "vertexLocalPositions", "vertexLocalRotations", "normalAdjustmentRotations",
        "baseLineFlags", "baseLineStartDataIndices", "baseLineDataCounts", "baseLineData",
    )},
    "edgeToTrianglesKeys": 119742, "edgeToTrianglesValues": 119545,
    "customSkinningBoneIndices": 118931, "centerFixedList": 119545,
}

DECODER_FORMATS = {
    "uint8": (1, "<B"), "uint16": (2, "<H"), "uint32": (4, "<I"),
    "int32": (4, "<i"), "float32": (4, "<f"), "float2": (8, "<2f"),
    "float3": (12, "<3f"), "float4": (16, "<4f"),
    "int2": (8, "<2i"), "int3": (12, "<3i"), "float16": (64, "<16f"),
}


class ContractError(RuntimeError):
    pass


def _resolve_type(md: Any, pe: Any, registration: dict[str, Any],
                  pointer_index: dict[int, list[int]], index: int, label: str) -> dict[str, Any]:
    record = element_layout._type_record(
        md=md, pe=pe, registration=registration, type_pointer_index=pointer_index,
        metadata_type_index=index, label=label,
    )
    if record["typeCodeValue"] == 0x1D:
        element_pointer = pe.u64_at_va(int(record["typePointerVa"], 16))
        candidates = pointer_index.get(element_pointer, [])
        if len(candidates) != 1:
            raise ContractError(f"{label} SZARRAY element maps to {len(candidates)} types")
        element = _resolve_type(md, pe, registration, pointer_index, candidates[0], label + " element")
        record.update({
            "category": "szarray",
            "name": element["name"] + "[]",
            "element": element,
        })
    elif record["category"] == "generic":
        arguments = []
        for argument in record["genericContext"]["arguments"]:
            arguments.append(_resolve_type(
                md, pe, registration, pointer_index,
                int(argument["metadataTypeIndex"]), label + " generic argument",
            ))
        record["resolvedGenericArguments"] = arguments
    return record


def _element_size(record: dict[str, Any], *, md: Any, pe: Any,
                  registration: dict[str, Any], pointer_index: dict[int, list[int]],
                  label: str) -> tuple[int, dict[str, Any]]:
    size = record.get("typeDefinitionNativeSizeBytes")
    if isinstance(size, int) and size > 0:
        return size, {
            "basis": "MetadataRegistration.typeDefinitionsSizes",
            "typeDefinitionIndex": record["typeDefinitionIndex"],
            "nativeSizeBytes": size,
        }
    match = re.fullmatch(r"Unity\.Collections\.FixedList(\d+)Bytes`1<.+>", record["name"])
    if match:
        expected = int(match.group(1))
        definition_index = record.get("genericDefinitionTypeIndex")
        if not isinstance(definition_index, int):
            raise ContractError(f"{label}: fixed-list generic definition is missing")
        type_def = md.types[definition_index]
        fields = md.fields_for(type_def)
        declarations = [(md.string(field.name_index), field.type_index) for field in fields]
        if declarations != [("length", 168224), ("buffer", 141638)]:
            raise ContractError(f"{label}: fixed-list field declaration drift: {declarations}")
        length_type = _resolve_type(
            md, pe, registration, pointer_index, 168224, label + ".length")
        buffer_type = _resolve_type(
            md, pe, registration, pointer_index, 141638, label + ".buffer")
        length_size = length_type.get("typeDefinitionNativeSizeBytes")
        buffer_size = buffer_type.get("typeDefinitionNativeSizeBytes")
        if length_size != 2 or buffer_size != 30 or length_size + buffer_size != expected:
            raise ContractError(f"{label}: fixed-list structural size drift")
        return expected, {
            "basis": "fixed_list_structural_fields",
            "genericDefinitionTypeIndex": definition_index,
            "fields": [
                {"name": "length", "type": length_type["name"], "nativeSizeBytes": length_size},
                {"name": "buffer", "type": buffer_type["name"], "nativeSizeBytes": buffer_size},
            ],
            "nativeSizeBytes": expected,
        }
    raise ContractError(f"no native element size for {record['name']}")


def _type_definition(md: Any, spec: tuple[str, int, int, int]) -> tuple[Any, dict[str, Any]]:
    name, index, field_start, field_count = spec
    type_def = md.types[index]
    if (md.type_full_name(type_def) != name or type_def.field_start != field_start or
            type_def.field_count != field_count):
        raise ContractError(f"{name} declaration drift")
    return type_def, {md.string(field.name_index): field for field in md.fields_for(type_def)}


def _field_offsets(pe: Any, registration: dict[str, Any], type_index: int,
                   fields: dict[str, Any]) -> dict[str, int]:
    table = int(registration["fieldOffsets"], 16)
    pointer = pe.u64_at_va(table + type_index * 8)
    if not pointer:
        raise ContractError(f"TypeDef {type_index} has no fieldOffsets entry")
    first = min(field.index for field in fields.values())
    return {
        name: pe.u32_at_va(pointer + (field.index - first) * 4)
        for name, field in fields.items()
    }


def _serializer_methods(native: Any, md: Any, pe: Any, *,
                        specs: dict[str, dict[str, Any]] = SERIALIZER_METHODS,
                        declaring_type: str = VIRTUAL_MESH[0]) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    _, by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    pointers = sorted(pointer for pointer in by_pointer if pointer)
    records: dict[str, Any] = {}
    instructions: dict[str, list[dict[str, Any]]] = {}
    for direction, expected in specs.items():
        candidates = [
            (pointer, signature)
            for pointer, signatures in by_pointer.items()
            for signature in signatures
            if int(signature.get("methodIndex", -1)) == expected["methodIndex"]
        ]
        if len(candidates) != 1:
            raise ContractError(f"{expected['method']} resolves to {len(candidates)} pointers")
        pointer, signature = candidates[0]
        position = bisect.bisect_right(pointers, pointer)
        end = pointers[position] if position < len(pointers) else 0
        if (pointer != expected["va"] or end != expected["endVa"] or
                signature.get("type") != declaring_type or
                signature.get("method") != expected["method"] or
                str(signature.get("token", "")).lower() != expected["token"]):
            raise ContractError(f"{expected['method']} identity or authoritative span drift")
        body = pe.bytes_at_va(pointer, end - pointer)
        digest = hashlib.sha256(body).hexdigest()
        if digest != expected["bodySha256"]:
            raise ContractError(f"{expected['method']} body hash drift: {digest}")
        decoded = native.decode_x64_subset(body, pointer, stop_offset=len(body))
        patch_value = f"0x{expected['ifixPatchId']:x}"
        patch_rows = [
            row for row in decoded
            if (row.get("write") or {}).get("value") == patch_value
            and str(row.get("text", "")).startswith("mov ")
        ]
        if len(patch_rows) != 1:
            raise ContractError(f"{expected['method']} IFix patch gate drift")
        calls, _ = native.scan_direct_calls(
            pe, pointer, end - pointer, by_pointer, set(),
            include_unresolved=True, arg_context_window=0,
        )
        patch_calls = [
            row for row in calls
            if row.get("offset") == expected["ifixCallOffset"]
            and any(
                target.get("type") == "IFix.WrappersManagerImpl" and
                target.get("method") == "IsPatched"
                for target in row.get("resolved", [])
            )
        ]
        if len(patch_calls) != 1:
            raise ContractError(f"{expected['method']} IFix IsPatched call drift")
        records[direction] = {
            "methodIndex": expected["methodIndex"], "declaringType": signature["type"],
            "method": signature["method"], "token": signature["token"],
            "va": f"0x{pointer:x}", "endVa": f"0x{end:x}", "spanBytes": end - pointer,
            "bodySha256": digest,
            "ifixBoundary": {
                "patchId": f"0x{expected['ifixPatchId']:x}",
                "patchIdLoadInstructionOffset": patch_rows[0]["offset"],
                "isPatchedCallInstructionOffset": expected["ifixCallOffset"],
                "status": "patch_activity_and_target_unproven",
            },
        }
        instructions[direction] = decoded
    return records, instructions


def _transform_assignment_evidence(name: str, runtime_offset: int, share_offset: int,
                                   instructions: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    return {
        "classification": "exact_unpatched_native_assignment",
        "operation": "ExSimpleNativeArray.Serialize/Deserialize",
        "serializeInstructionOffsets": {
            "runtimeSource": _one_instruction(
                instructions["serialize"], f"mov rcx, [rdi+0x{runtime_offset:x}]",
                name + " serialize source"),
            "serializedTarget": _one_instruction(
                instructions["serialize"], f"mov [rbx+0x{share_offset:x}], rax",
                name + " serialize target"),
        },
        "deserializeInstructionOffsets": {
            "serializedSource": _one_instruction(
                instructions["deserialize"], f"mov r14, [rdi+0x{share_offset:x}]"
                if share_offset != 0x20 else f"mov rsi, [rdi+0x{share_offset:x}]",
                name + " deserialize source"),
            "runtimeTarget": _one_instruction(
                instructions["deserialize"],
                f"mov [rbx+0x{runtime_offset:x}], " + ("rsi" if runtime_offset != 0x28 else "rdi"),
                name + " deserialize target"),
        },
    }


def _one_instruction(instructions: list[dict[str, Any]], text: str, label: str) -> int:
    matches = [row for row in instructions if row.get("text") == text]
    if len(matches) != 1:
        raise ContractError(f"{label} expected one instruction {text!r}, found {len(matches)}")
    return int(matches[0]["offset"])


def _assignment_evidence(name: str, runtime_offset: int, share_offset: int,
                         instructions: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    s = instructions["serialize"]
    d = instructions["deserialize"]
    if name in {row[0] for row in LAYOUT_SPECS[:11]}:
        kind = "ExSimpleNativeArray.Serialize/Deserialize"
        serialize_source = _one_instruction(s, f"mov rcx, [rdi+0x{runtime_offset:x}]", name + " serialize source")
        serialize_target = _one_instruction(s, f"mov [rbx+0x{share_offset:x}], rax", name + " serialize target")
        deserialize_source = _one_instruction(d, f"mov rdx, [rdi+0x{share_offset:x}]", name + " deserialize source")
        deserialize_target = _one_instruction(d, f"mov rcx, [rbx+0x{runtime_offset:x}]", name + " deserialize target")
    elif name.startswith("edgeToTriangles"):
        kind = "NativeMultiHashMapExtensions.MC2Serialize/MC2Deserialize"
        serialize_source = _one_instruction(s, f"lea rdx, [rdi+0x{runtime_offset:x}]", name + " serialize source")
        serialize_target = _one_instruction(
            s,
            f"mov [rbx+0x{share_offset:x}], " + ("rax" if name.endswith("Keys") else "r9"),
            name + " serialize target",
        )
        deserialize_source = _one_instruction(
            d,
            ("mov rdx" if name.endswith("Keys") else "mov r8") + f", [rdi+0x{share_offset:x}]",
            name + " deserialize source",
        )
        deserialize_target = _one_instruction(d, f"movaps [rbx+0x{runtime_offset:x}], xmm0", name + " deserialize target")
    elif name in {"customSkinningBoneIndices", "centerFixedList"}:
        kind = "DataUtility.ArrayCopy"
        serialize_source = _one_instruction(s, f"mov rcx, [rdi+0x{runtime_offset:x}]", name + " serialize source")
        serialize_target = _one_instruction(s, f"lea rdx, [rbx+0x{share_offset:x}]", name + " serialize target")
        deserialize_source = _one_instruction(d, f"mov rcx, [rdi+0x{share_offset:x}]", name + " deserialize source")
        deserialize_target = _one_instruction(d, f"lea rdx, [rbx+0x{runtime_offset:x}]", name + " deserialize target")
    else:
        kind = "NativeArrayExtensions.MC2ToRawBytes/MC2FromRawBytes"
        serialize_source = _one_instruction(s, f"lea rcx, [rdi+0x{runtime_offset:x}]", name + " serialize source")
        serialize_target = _one_instruction(s, f"mov [rbx+0x{share_offset:x}], rax", name + " serialize target")
        deserialize_source = _one_instruction(d, f"mov rdx, [rdi+0x{share_offset:x}]", name + " deserialize source")
        deserialize_target = _one_instruction(d, f"movaps [rbx+0x{runtime_offset:x}], xmm0", name + " deserialize target")
    return {
        "classification": "exact_unpatched_native_assignment", "operation": kind,
        "serializeInstructionOffsets": {"runtimeSource": serialize_source, "serializedTarget": serialize_target},
        "deserializeInstructionOffsets": {"serializedSource": deserialize_source, "runtimeTarget": deserialize_target},
    }


def build_contract(*, game_assembly: Path | None = None,
                   metadata: Path | None = None) -> dict[str, Any]:
    gate = element_layout._native_gate(game_assembly, metadata)
    catalog, native = element_layout._helpers()
    md = catalog.Metadata(Path(gate["globalMetadata"]["path"]))
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if code_registration != 0x18B9217D0 or metadata_registration != 0x18B921C30:
        raise ContractError("pinned registration addresses drifted")
    registration = native.metadata_registration_summary(pe, metadata_registration)
    pointer_index = element_layout._build_type_pointer_index(pe, registration)
    _, virtual_fields = _type_definition(md, VIRTUAL_MESH)
    _, share_fields = _type_definition(md, SHARE_DATA)
    _, transform_fields = _type_definition(md, TRANSFORM_DATA)
    _, transform_share_fields = _type_definition(md, TRANSFORM_SHARE_DATA)
    virtual_offsets = _field_offsets(pe, registration, VIRTUAL_MESH[1], virtual_fields)
    share_offsets = _field_offsets(pe, registration, SHARE_DATA[1], share_fields)
    serializer_methods, serializer_instructions = _serializer_methods(native, md, pe)
    transform_offsets = _field_offsets(pe, registration, TRANSFORM_DATA[1], transform_fields)
    transform_share_offsets = _field_offsets(
        pe, registration, TRANSFORM_SHARE_DATA[1], transform_share_fields)
    transform_serializer_methods, transform_serializer_instructions = _serializer_methods(
        native, md, pe, specs=TRANSFORM_SERIALIZER_METHODS,
        declaring_type=TRANSFORM_DATA[0],
    )

    layouts: dict[str, Any] = {}
    for path, runtime_name, runtime_index, argument_index, decode_kind in LAYOUT_SPECS:
        share_field = share_fields.get(path)
        expected_share_index = SHARE_FIELD_TYPE_INDICES[path]
        if share_field is None or share_field.type_index != expected_share_index:
            actual = None if share_field is None else share_field.type_index
            raise ContractError(f"ShareSerializationData.{path} type drift: {actual} != {expected_share_index}")
        runtime_field = virtual_fields.get(runtime_name)
        if runtime_field is None or runtime_field.type_index != runtime_index:
            actual = None if runtime_field is None else runtime_field.type_index
            raise ContractError(f"VirtualMesh.{runtime_name} type drift: {actual} != {runtime_index}")
        expected_runtime_offset, expected_share_offset = ASSIGNMENT_OFFSETS[path]
        if (virtual_offsets[runtime_name] != expected_runtime_offset or
                share_offsets[path] != expected_share_offset):
            raise ContractError(
                f"{path} field offset drift: runtime=0x{virtual_offsets[runtime_name]:x} "
                f"share=0x{share_offsets[path]:x}"
            )
        share_container = _resolve_type(
            md, pe, registration, pointer_index, share_field.type_index,
            f"BeyondDynamicBone.VirtualMesh+ShareSerializationData.{path}",
        )
        direct_share_layout = share_field.type_index != 118327
        container = share_container if direct_share_layout else _resolve_type(
            md, pe, registration, pointer_index, runtime_field.type_index,
            f"BeyondDynamicBone.VirtualMesh.{runtime_name}",
        )
        if direct_share_layout and container["category"] == "szarray":
            element = container["element"]
        elif argument_index is None:
            if container["category"] != "szarray":
                raise ContractError(f"{path} is no longer an SZARRAY")
            element = container["element"]
        else:
            arguments = container.get("resolvedGenericArguments") or []
            if argument_index >= len(arguments):
                raise ContractError(f"{path} generic argument {argument_index} is missing")
            element = arguments[argument_index]
        stride, stride_evidence = _element_size(
            element, md=md, pe=pe, registration=registration,
            pointer_index=pointer_index, label=path,
        )
        expected_stride, fmt = DECODER_FORMATS.get(decode_kind, (stride, None))
        if stride != expected_stride:
            raise ContractError(f"{path} stride drift: {stride} != {expected_stride}")
        layouts[path] = {
            "declaringType": SHARE_DATA[0],
            "field": path,
            "fieldIndex": share_field.index,
            "metadataTypeIndex": share_field.type_index,
            "serializedContainerType": share_container["name"],
            "runtimeField": runtime_name,
            "runtimeFieldIndex": runtime_field.index,
            "runtimeMetadataTypeIndex": runtime_field.type_index,
            "runtimeFieldOffset": f"0x{expected_runtime_offset:x}",
            "serializedFieldOffset": f"0x{expected_share_offset:x}",
            "containerType": container["name"],
            "elementType": element["name"],
            "strideBytes": stride,
            "strideEvidence": stride_evidence,
            "decodeKind": decode_kind,
            "structFormat": fmt,
            "serializedEncoding": (
                "element_value_list"
                if share_container["category"] == "szarray" and
                   share_container["element"]["name"] != "System.Byte"
                else "raw_byte_list"
                if share_container["category"] == "szarray"
                else "serialization_data"
            ),
            "mappingEvidence": _assignment_evidence(
                path, expected_runtime_offset, expected_share_offset,
                serializer_instructions,
            ),
        }

    if len(layouts) != 35:
        raise ContractError(f"serialized layout census drifted: {len(layouts)}")

    transform_layouts: dict[str, Any] = {}
    for path, field_name, runtime_type_index, decode_kind, share_type_index, runtime_offset, share_offset in TRANSFORM_LAYOUT_SPECS:
        runtime_field = transform_fields.get(field_name)
        share_field = transform_share_fields.get(field_name)
        if (runtime_field is None or runtime_field.type_index != runtime_type_index or
                share_field is None or share_field.type_index != share_type_index):
            raise ContractError(f"{path} declaration drift")
        if (transform_offsets[field_name] != runtime_offset or
                transform_share_offsets[field_name] != share_offset):
            raise ContractError(f"{path} field offset drift")
        container = _resolve_type(
            md, pe, registration, pointer_index, share_field.type_index,
            f"{TRANSFORM_SHARE_DATA[0]}.{field_name}",
        )
        arguments = container.get("resolvedGenericArguments") or []
        if container.get("category") != "generic" or len(arguments) != 1:
            raise ContractError(f"{path} serialized field is no longer one-argument SerializationData")
        element = arguments[0]
        stride, stride_evidence = _element_size(
            element, md=md, pe=pe, registration=registration,
            pointer_index=pointer_index, label=path,
        )
        expected_stride, fmt = DECODER_FORMATS[decode_kind]
        if stride != expected_stride:
            raise ContractError(f"{path} stride drift: {stride} != {expected_stride}")
        transform_layouts[path] = {
            "declaringType": TRANSFORM_SHARE_DATA[0], "field": field_name,
            "fieldIndex": share_field.index, "metadataTypeIndex": share_field.type_index,
            "serializedContainerType": container["name"],
            "runtimeField": field_name, "runtimeFieldIndex": runtime_field.index,
            "runtimeMetadataTypeIndex": runtime_field.type_index,
            "runtimeFieldOffset": f"0x{runtime_offset:x}",
            "serializedFieldOffset": f"0x{share_offset:x}",
            "elementType": element["name"], "strideBytes": stride,
            "strideEvidence": stride_evidence, "decodeKind": decode_kind,
            "structFormat": fmt, "serializedEncoding": "serialization_data",
            "mappingEvidence": _transform_assignment_evidence(
                path, runtime_offset, share_offset, transform_serializer_instructions),
        }
    return {
        "schema": "endfield.charinfo.secondary-dynamics-proxy-layout.v3",
        "status": "proxy_and_transform_array_layout_assignments_closed_unpatched",
        "nativeGate": gate,
        "metadataRegistration": {
            "codeRegistrationVa": f"0x{code_registration:x}",
            "metadataRegistrationVa": f"0x{metadata_registration:x}",
        },
        "declarations": {
            "virtualMesh": {"typeDefinitionIndex": VIRTUAL_MESH[1], "fieldStart": VIRTUAL_MESH[2], "fieldCount": VIRTUAL_MESH[3]},
            "shareSerializationData": {"typeDefinitionIndex": SHARE_DATA[1], "fieldStart": SHARE_DATA[2], "fieldCount": SHARE_DATA[3]},
            "transformData": {"typeDefinitionIndex": TRANSFORM_DATA[1], "fieldStart": TRANSFORM_DATA[2], "fieldCount": TRANSFORM_DATA[3]},
            "transformShareSerializationData": {"typeDefinitionIndex": TRANSFORM_SHARE_DATA[1], "fieldStart": TRANSFORM_SHARE_DATA[2], "fieldCount": TRANSFORM_SHARE_DATA[3]},
        },
        "serializerMethods": serializer_methods,
        "transformSerializerMethods": transform_serializer_methods,
        "serializedLayouts": layouts,
        "serializedSlotCount": len(layouts),
        "nestedTransformLayouts": transform_layouts,
        "nestedTransformSlotCount": len(transform_layouts),
        "secondaryDynamicsVerified": False,
        "solverImplemented": False,
        "retailEquivalent": False,
        "boundary": "Exact declarations, element strides, object field offsets, and bidirectional assignments for 35 VirtualMesh proxy slots and three nested TransformData arrays in their hash-pinned unpatched ShareSerialize/ShareDeserialize bodies. IFix patch activity and targets have not been proven, so unconditional runtime equivalence is not claimed. No solver numerics, scheduling, Burst export mapping, or Transform writeback is claimed.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        result = build_contract(game_assembly=args.game_assembly, metadata=args.metadata)
        serialized = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
        if args.check:
            matches = args.output.is_file() and args.output.read_text(encoding="utf-8") == serialized
            print(json.dumps({"status": result["status"], "matches": matches, "output": str(args.output)}))
            return 0 if matches else 1
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
        print(json.dumps({"status": result["status"], "output": str(args.output)}))
        return 0
    except (OSError, ValueError, KeyError, IndexError, struct.error, ContractError,
            element_layout.ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
