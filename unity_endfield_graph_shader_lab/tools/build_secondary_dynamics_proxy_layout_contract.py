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
            "mappingEvidence": (
                "direct_serialized_element_declaration"
                if direct_share_layout else
                "exact_same_name_declaration_correspondence_serializer_body_unproven"
            ),
        }

    if len(layouts) != 35:
        raise ContractError(f"serialized layout census drifted: {len(layouts)}")
    return {
        "schema": "endfield.charinfo.secondary-dynamics-proxy-layout.v1",
        "status": "proxy_array_element_types_and_strides_closed",
        "nativeGate": gate,
        "metadataRegistration": {
            "codeRegistrationVa": f"0x{code_registration:x}",
            "metadataRegistrationVa": f"0x{metadata_registration:x}",
        },
        "declarations": {
            "virtualMesh": {"typeDefinitionIndex": VIRTUAL_MESH[1], "fieldStart": VIRTUAL_MESH[2], "fieldCount": VIRTUAL_MESH[3]},
            "shareSerializationData": {"typeDefinitionIndex": SHARE_DATA[1], "fieldStart": SHARE_DATA[2], "fieldCount": SHARE_DATA[3]},
        },
        "serializedLayouts": layouts,
        "serializedSlotCount": len(layouts),
        "secondaryDynamicsVerified": False,
        "solverImplemented": False,
        "retailEquivalent": False,
        "boundary": "Exact serialized declarations and element strides. Same-name byte[] to runtime-field correspondence is structural until ShareSerialize/ShareDeserialize bodies are pinned; no solver numerics, scheduling, Burst export mapping, or Transform writeback is claimed.",
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
