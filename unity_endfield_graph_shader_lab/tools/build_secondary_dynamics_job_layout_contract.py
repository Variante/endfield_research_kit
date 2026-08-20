#!/usr/bin/env python3
"""Recover the pinned IL2CPP outer job payload layouts.

This contract intentionally stops at the job value itself.  It records the
materialized field offsets of the four Magica/secondary-dynamics jobs, but it
does not invent the layout of the open generic ``NativeArray<T>`` or
``NativeReference<T>`` internals, nor does it claim Burst ``Execute`` bodies.
Every native fact is recomputed from the selected metadata registration and
the selected GameAssembly after the common installed-client gate succeeds.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import struct
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_job_layout_contract.json"
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None

# The selected GameAssembly is PE32+ x64 (PeImage rejects any other image).
# This is the alignment boundary used for the materialized native job value;
# it is not a claim about the size or alignment of an open generic definition.
NATIVE_ABI_ALIGNMENT_BYTES = 8
GENERIC_FIELD_KINDS = frozenset({"NativeArray", "NativeReference"})
IL2CPP_TYPE_GENERICINST = 0x15
IL2CPP_TYPE_VALUETYPE = 0x11
IL2CPP_PRIMITIVE_TYPE_CODES = frozenset(range(0x1, 0x0f))

EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when a pinned field-layout evidence gate does not close."""


def _load_tool_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load IL2CPP helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (
        _load_tool_module("endfield_layout_metadata", root / "catalog_option_flow_metadata.py"),
        _load_tool_module("endfield_layout_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _repo_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file_record(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {
        "path": _repo_path(path),
        "size": path.stat().st_size,
        "sha256": digest or _sha256(path),
    }


# Metadata field type indexes are retained as an assertion, not as a source of
# offsets.  The offsets below always come from MetadataRegistration.fieldOffsets.
# The declaration type indexes below are classification assertions only; they
# do not claim any inner NativeArray/NativeReference layout.
def _native_array_field(name: str, type_index: int) -> tuple[str, int, str, int]:
    return name, type_index, "NativeArray", 50690


def _native_reference_field(name: str, type_index: int) -> tuple[str, int, str, int]:
    return name, type_index, "NativeReference", 60806


JOBS: tuple[dict[str, Any], ...] = (
    {
        "typeIndex": 48376,
        "type": "BeyondDynamicBone.ColliderManager+StartSimulationStepJob",
        "fieldStart": 230238,
        "fieldCount": 17,
        "setterMethod": "SetIndexCount",
        "setterMethodIndex": 385449,
        "nativeReferenceTypeIndex": 83620,
        "nativeReferenceDefinitionIndex": 60806,
        "fields": (
            _native_array_field("jobColliderIndexList", 83201),
            _native_array_field("teamDataArray", 83381),
            _native_array_field("centerDataArray", 83349),
            _native_array_field("teamIdArray", 83197),
            _native_array_field("flagArray", 83139),
            _native_array_field("sizeArray", 83304),
            _native_array_field("framePositions", 83298),
            _native_array_field("frameRotations", 83315),
            _native_array_field("frameScales", 83304),
            _native_array_field("oldFramePositions", 83298),
            _native_array_field("oldFrameRotations", 83315),
            _native_array_field("nowPositions", 83298),
            _native_array_field("nowRotations", 83315),
            _native_array_field("oldPositions", 83298),
            _native_array_field("oldRotations", 83315),
            _native_array_field("workDataArray", 83340),
            _native_reference_field("_indexCount", 83620),
        ),
    },
    {
        "typeIndex": 48377,
        "type": "BeyondDynamicBone.ColliderManager+EndSimulationStepJob",
        "fieldStart": 230255,
        "fieldCount": 6,
        "setterMethod": "SetIndexCount",
        "setterMethodIndex": 385453,
        "nativeReferenceTypeIndex": 83620,
        "nativeReferenceDefinitionIndex": 60806,
        "fields": (
            _native_array_field("jobColliderIndexList", 83201),
            _native_array_field("nowPositions", 83298),
            _native_array_field("nowRotations", 83315),
            _native_array_field("oldPositions", 83298),
            _native_array_field("oldRotations", 83315),
            _native_reference_field("_indexCount", 83620),
        ),
    },
    {
        "typeIndex": 48422,
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "fieldStart": 230393,
        "fieldCount": 26,
        "setterMethod": "SetIndexCount",
        "setterMethodIndex": 385695,
        "nativeReferenceTypeIndex": 83620,
        "nativeReferenceDefinitionIndex": 60806,
        "fields": (
            ("simulationPower", 171886, "float4", 57221, 16),
            ("simulationDeltaTime", 163868, "Single", 42141, 4),
            _native_array_field("stepParticleIndexArray", 83201),
            _native_array_field("attributes", 83290),
            _native_array_field("depthArray", 83240),
            _native_array_field("positions", 83298),
            _native_array_field("rotations", 83315),
            _native_array_field("vertexRootIndices", 83201),
            _native_array_field("teamDataArray", 83381),
            _native_array_field("parameterArray", 83108),
            _native_array_field("centerDataArray", 83349),
            _native_array_field("teamWindArray", 83253),
            _native_array_field("windDataArray", 83391),
            _native_array_field("teamIdArray", 83197),
            _native_array_field("oldPosArray", 83298),
            _native_array_field("nextPosArray", 83298),
            _native_array_field("basePosArray", 83298),
            _native_array_field("velocityArray", 83304),
            _native_array_field("baseRotArray", 83315),
            _native_array_field("oldPositionArray", 83298),
            _native_array_field("oldRotationArray", 83315),
            _native_array_field("velocityPosArray", 83298),
            _native_array_field("frictionArray", 83240),
            _native_array_field("stepBasicPositionArray", 83298),
            _native_array_field("stepBasicRotationArray", 83315),
            _native_reference_field("_indexCount", 83620),
        ),
    },
    {
        "typeIndex": 48424,
        "type": "BeyondDynamicBone.SimulationManager+EndSimulationStepJob",
        "fieldStart": 230433,
        "fieldCount": 17,
        "setterMethod": "SetIndexCount",
        "setterMethodIndex": 385706,
        "nativeReferenceTypeIndex": 83620,
        "nativeReferenceDefinitionIndex": 60806,
        "fields": (
            ("simulationDeltaTime", 163868, "Single", 42141, 4),
            _native_array_field("stepParticleIndexArray", 83201),
            _native_array_field("teamDataArray", 83381),
            _native_array_field("parameterArray", 83108),
            _native_array_field("centerDataArray", 83349),
            _native_array_field("attributes", 83290),
            _native_array_field("vertexDepths", 83240),
            _native_array_field("teamIdArray", 83197),
            _native_array_field("nextPosArray", 83298),
            _native_array_field("oldPosArray", 83298),
            _native_array_field("velocityPosArray", 83298),
            _native_array_field("velocityArray", 83304),
            _native_array_field("realVelocityArray", 83304),
            _native_array_field("frictionArray", 83240),
            _native_array_field("staticFrictionArray", 83240),
            _native_array_field("collisionNormalArray", 83304),
            _native_reference_field("_indexCount", 83620),
        ),
    },
)

EXPECTED_PADDING_GAPS: dict[str, tuple[int, int, str, str]] = {
    "BeyondDynamicBone.SimulationManager+StartSimulationStepJob": (
        0x14, 0x18, "simulationDeltaTime", "stepParticleIndexArray"
    ),
    "BeyondDynamicBone.SimulationManager+EndSimulationStepJob": (
        0x4, 0x8, "simulationDeltaTime", "stepParticleIndexArray"
    ),
}


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(
            f"common.check_installed_native_inputs [{result.status}]: {result.detail}"
        )
    return {
        "gameAssembly": _file_record(Path(result.gameassembly), result.gameassembly_sha256),
        "globalMetadata": _file_record(Path(result.metadata), result.metadata_sha256),
    }


def _signed_i32(pe: Any, va: int) -> int:
    return struct.unpack("<i", struct.pack("<I", pe.u32_at_va(va)))[0]


def _type_definition_for_byval_index(md: Any, metadata_type_index: int, field_name: str) -> Any:
    """Resolve one canonical TypeDef without confusing a byref alias for it."""
    matches = [
        type_def for type_def in md.types
        if type_def.byval_type_index == metadata_type_index
    ]
    if len(matches) != 1:
        raise ContractError(
            f"{field_name} element metadata type index {metadata_type_index} "
            f"maps to {len(matches)} by-value TypeDefs"
        )
    return matches[0]


def _build_type_pointer_index(pe: Any, registration: dict[str, Any]) -> dict[int, list[int]]:
    count = int(registration["typesCount"])
    pointer = int(registration["types"], 16)
    if count <= 0 or not pointer:
        raise ContractError("MetadataRegistration.types has no usable count/pointer")
    result: dict[int, list[int]] = {}
    for index in range(count):
        type_pointer = pe.u64_at_va(pointer + index * 8)
        if type_pointer:
            result.setdefault(type_pointer, []).append(index)
    return result


def _element_type_evidence(
    *,
    md: Any,
    pe: Any,
    registration: dict[str, Any],
    type_pointer_index: dict[int, list[int]],
    field_name: str,
    metadata_type_index: int,
    expected_kind: str,
    expected_definition_index: int,
) -> dict[str, Any]:
    """Resolve one closed NativeArray/NativeReference argument fail-closed."""
    type_count = int(registration["typesCount"])
    if metadata_type_index < 0 or metadata_type_index >= type_count:
        raise ContractError(
            f"{field_name} generic metadata type index {metadata_type_index} "
            f"is outside MetadataRegistration.types count {type_count}"
        )
    type_table = int(registration["types"], 16)
    type_pointer = pe.u64_at_va(type_table + metadata_type_index * 8)
    if not type_pointer:
        raise ContractError(f"{field_name} generic metadata type index has a null types entry")
    type_code = pe.bytes_at_va(type_pointer + 10, 1)[0]
    if type_code != IL2CPP_TYPE_GENERICINST:
        raise ContractError(
            f"{field_name} metadata type index {metadata_type_index} has type code "
            f"0x{type_code:x}, expected GENERICINST 0x{IL2CPP_TYPE_GENERICINST:x}"
        )

    generic_class_pointer = pe.u64_at_va(type_pointer)
    if not generic_class_pointer:
        raise ContractError(f"{field_name} generic type has a null generic-class context")
    generic_definition_class_pointer = pe.u64_at_va(generic_class_pointer)
    if not generic_definition_class_pointer:
        raise ContractError(f"{field_name} generic class has a null definition-class pointer")
    generic_definition_index = pe.u32_at_va(generic_definition_class_pointer)
    if generic_definition_index != expected_definition_index:
        raise ContractError(
            f"{field_name} generic definition index {generic_definition_index} "
            f"does not match {expected_kind} definition {expected_definition_index}"
        )
    if generic_definition_index >= len(md.types):
        raise ContractError(f"{field_name} generic definition index is outside metadata TypeDefs")
    generic_definition_name = md.type_full_name(md.types[generic_definition_index])
    expected_definition_name = {
        50690: "Unity.Collections.NativeArray`1",
        60806: "Unity.Collections.NativeReference`1",
    }.get(expected_definition_index)
    if generic_definition_name != expected_definition_name:
        raise ContractError(
            f"{field_name} generic definition {generic_definition_index} name drift: "
            f"{generic_definition_name!r}"
        )

    context_pointer = pe.u64_at_va(generic_class_pointer + 8)
    if not context_pointer:
        raise ContractError(f"{field_name} generic class has a null generic context")
    argument_count = pe.u32_at_va(context_pointer)
    argument_vector = pe.u64_at_va(context_pointer + 8)
    if argument_count != 1 or not argument_vector:
        raise ContractError(
            f"{field_name} generic context has argumentCount={argument_count} "
            f"and argumentVector=0x{argument_vector:x}; expected one argument"
        )
    argument_pointer = pe.u64_at_va(argument_vector)
    candidates = type_pointer_index.get(argument_pointer, [])
    if len(candidates) != 1:
        raise ContractError(
            f"{field_name} generic argument pointer 0x{argument_pointer:x} "
            f"maps to {len(candidates)} metadata type indexes"
        )
    element_metadata_type_index = candidates[0]
    element_type_code = pe.bytes_at_va(argument_pointer + 10, 1)[0]
    if element_type_code == IL2CPP_TYPE_VALUETYPE:
        element_category = "valueType"
    elif element_type_code in IL2CPP_PRIMITIVE_TYPE_CODES:
        element_category = "primitive"
    else:
        raise ContractError(
            f"{field_name} element metadata type index {element_metadata_type_index} "
            f"has unsupported type code 0x{element_type_code:x}"
        )
    element_type_def = _type_definition_for_byval_index(
        md, element_metadata_type_index, field_name
    )
    sizes_count = int(registration["typeDefinitionsSizesCount"])
    if sizes_count != len(md.types):
        raise ContractError(
            f"{field_name} typeDefinitionsSizes count {sizes_count} "
            f"does not equal metadata TypeDef count {len(md.types)}"
        )
    if element_type_def.index < 0 or element_type_def.index >= sizes_count:
        raise ContractError(
            f"{field_name} element TypeDef index {element_type_def.index} "
            f"is outside typeDefinitionsSizes count {sizes_count}"
        )
    sizes_table = int(registration["typeDefinitionsSizes"], 16)
    sizes_pointer = pe.u64_at_va(sizes_table + element_type_def.index * 8)
    if not sizes_pointer:
        raise ContractError(
            f"{field_name} element TypeDef index {element_type_def.index} "
            "has a null typeDefinitionsSizes entry"
        )
    instance_size = pe.u32_at_va(sizes_pointer)
    native_size = _signed_i32(pe, sizes_pointer + 4)
    if native_size <= 0 or instance_size != native_size + 16:
        raise ContractError(
            f"{field_name} element {md.type_full_name(element_type_def)} "
            f"has invalid typeDefinitionsSizes instance={instance_size} native={native_size}"
        )
    return {
        "genericContext": {
            "genericDefinitionTypeIndex": generic_definition_index,
            "genericDefinitionName": generic_definition_name,
            "genericClassPointerVa": f"0x{generic_class_pointer:x}",
            "genericDefinitionClassPointerVa": f"0x{generic_definition_class_pointer:x}",
            "genericContextPointerVa": f"0x{context_pointer:x}",
            "argumentCount": argument_count,
            "argumentVectorVa": f"0x{argument_vector:x}",
            "elementTypePointerVa": f"0x{argument_pointer:x}",
        },
        "elementType": {
            "name": md.type_full_name(element_type_def),
            "metadataTypeIndex": element_metadata_type_index,
            "typeDefinitionIndex": element_type_def.index,
            "typeCode": element_type_code,
            "category": element_category,
            "typeDefinitionsSizesPointerVa": f"0x{sizes_pointer:x}",
            "instanceSizeBytes": instance_size,
            "nativeSizeBytes": native_size,
        },
    }


def _method_pointer(md: Any, native: Any, pe: Any, method_index: int) -> int:
    modules = native.parse_codegen_modules(pe, 0x18B9217D0)
    ranges = native.image_method_ranges(md)
    _by_image, by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    pointers = [pointer for pointer, rows in by_pointer.items() if any(row.get("methodIndex") == method_index for row in rows)]
    if len(pointers) != 1:
        raise ContractError(f"method index {method_index} does not resolve to one native pointer")
    return pointers[0]


def _setter_evidence(pe: Any, pointer: int, expected_offset: int) -> dict[str, Any]:
    file_offset, section, _rva = pe.file_offset_for_va(pointer)
    if file_offset is None:
        raise ContractError(f"setter VA 0x{pointer:x} is outside GameAssembly")
    probe = pe.bytes_at_va(pointer, 256)
    prologue_offset = probe.find(b"\x48\x8b\xf9")
    if prologue_offset < 0 or probe[prologue_offset + 3:prologue_offset + 6] != b"\x48\x8b\xda":
        raise ContractError(
            f"setter 0x{pointer:x} lacks the exact this/argument prologue "
            "48 8b f9 followed by 48 8b da"
        )
    pattern = re.compile(
        rb"\x0f\x10\x03\x0f\x11(?:\x87(?P<disp32>.{4})|\x47(?P<disp8>.))",
        re.DOTALL,
    )
    first_ret = probe.find(b"\xc3")
    matches = [match for match in pattern.finditer(probe) if first_ret < 0 or match.start() < first_ret]
    if len(matches) != 1:
        raise ContractError(f"setter 0x{pointer:x} has {len(matches)} exact 16-byte stores")
    match = matches[0]
    if match.group("disp32") is not None:
        displacement = struct.unpack("<i", match.group("disp32"))[0]
    else:
        displacement = struct.unpack("<b", match.group("disp8"))[0]
    if displacement != expected_offset:
        raise ContractError(
            f"setter 0x{pointer:x} stores this+0x{displacement:x}, expected 0x{expected_offset:x}"
        )
    ret = probe.find(b"\xc3", match.end())
    if ret < 0:
        raise ContractError(f"setter 0x{pointer:x} has no return after its store")
    body = probe[: ret + 1]
    return {
        "methodPointerVa": f"0x{pointer:x}",
        "fileOffset": f"0x{file_offset:x}",
        "section": section,
        "bodyBytes": len(body),
        "bodySha256": hashlib.sha256(body).hexdigest(),
        "store": {
            "instruction": "movups xmm0,[rbx]; movups [rdi+disp32],xmm0",
            "thisRegister": "rdi",
            "argumentRegister": "rbx",
            "prologue": {
                "this": "48 8b f9",
                "argument": "48 8b da",
                "thisRegister": "rdi",
                "argumentRegister": "rbx",
                "relation": "argument move immediately follows this move",
            },
            "payloadOffset": f"0x{displacement:x}",
            "widthBytes": 16,
            "matches": "_indexCount",
        },
    }


def _validate_setter_metadata(md: Any, spec: dict[str, Any]) -> Any:
    method = md.methods[spec["setterMethodIndex"]]
    if md.string(method.name_index) != spec["setterMethod"] or method.declaring_type != spec["typeIndex"]:
        raise ContractError(f"{spec['type']} setter metadata drift")
    parameters = md.parameters_for(method)
    if method.parameter_count != 1 or len(parameters) != 1 or parameters[0].type_index != 83617:
        raise ContractError(
            f"{spec['type']} SetIndexCount parameter metadata drift: "
            f"count={method.parameter_count}, types={[row.type_index for row in parameters]}"
        )
    return method


def _field_slot_evidence(
    *,
    name: str,
    kind: str,
    native_offset: int,
    next_native_offset: int,
    native_size: int,
    declared_width: int,
    next_field_name: str | None,
) -> tuple[int, dict[str, Any]]:
    """Derive a materialized field slot from the next native boundary.

    For a NativeArray/NativeReference field, the concrete closed-instance slot
    is the distance to the next field (or the native-size tail for the final
    field).  The generic definition's own size is deliberately not consulted:
    the inner contract only has lower bounds for those open definitions.
    Scalar/vector rows retain their independently classified field width while
    still recording the inter-field ABI span.
    """
    if native_offset < 0 or native_size < 0:
        raise ContractError(f"{name} has a negative native layout boundary")
    if native_offset % NATIVE_ABI_ALIGNMENT_BYTES:
        raise ContractError(
            f"{name} native offset 0x{native_offset:x} violates "
            f"{NATIVE_ABI_ALIGNMENT_BYTES}-byte ABI alignment"
        )
    if native_size % NATIVE_ABI_ALIGNMENT_BYTES:
        raise ContractError(
            f"native size 0x{native_size:x} violates "
            f"{NATIVE_ABI_ALIGNMENT_BYTES}-byte ABI alignment"
        )
    span = next_native_offset - native_offset
    if span <= 0:
        raise ContractError(
            f"{name} has non-positive native slot span {span} "
            f"(offset=0x{native_offset:x}, boundary=0x{next_native_offset:x})"
        )
    if next_native_offset > native_size:
        raise ContractError(
            f"{name} native slot boundary 0x{next_native_offset:x} exceeds "
            f"native size 0x{native_size:x}"
        )
    if span % NATIVE_ABI_ALIGNMENT_BYTES:
        raise ContractError(
            f"{name} native slot span {span} violates "
            f"{NATIVE_ABI_ALIGNMENT_BYTES}-byte ABI alignment"
        )

    if kind in GENERIC_FIELD_KINDS:
        # This is the concrete *outer* slot.  Do not use declared_width here:
        # that tuple value is retained only as a historical classification
        # assertion and must never become a generic type-size claim.
        width = span
        basis = "next_field_native_offset" if next_field_name else "native_size_tail"
    else:
        if declared_width <= 0 or declared_width > span:
            raise ContractError(
                f"{name} classified width {declared_width} does not fit "
                f"native slot span {span}"
            )
        width = declared_width
        basis = "classified_field_width_with_next_field_span"

    evidence = {
        "status": "closed",
        "basis": basis,
        "nativePayloadOffset": f"0x{native_offset:x}",
        "nextNativePayloadOffset": f"0x{next_native_offset:x}",
        "nextField": next_field_name,
        "slotSpanBytes": span,
        "abiAlignmentBytes": NATIVE_ABI_ALIGNMENT_BYTES,
        "abiAligned": True,
    }
    if kind in GENERIC_FIELD_KINDS:
        evidence["genericTypeSizeClaimed"] = False
    return width, evidence


def _build_job(
    md: Any,
    native: Any,
    pe: Any,
    registration: dict[str, Any],
    type_pointer_index: dict[int, list[int]],
    spec: dict[str, Any],
) -> dict[str, Any]:
    type_def = md.types[spec["typeIndex"]]
    if md.type_full_name(type_def) != spec["type"]:
        raise ContractError(f"type {spec['typeIndex']} name drift")
    if type_def.field_start != spec["fieldStart"] or type_def.field_count != spec["fieldCount"]:
        raise ContractError(f"{spec['type']} field range drift")
    fields = md.fields_for(type_def)
    field_table = int(registration["fieldOffsets"], 16)
    field_offsets_pointer = pe.u64_at_va(field_table + spec["typeIndex"] * 8)
    if not field_offsets_pointer:
        raise ContractError(f"{spec['type']} has no fieldOffsets entry")
    offsets = [_signed_i32(pe, field_offsets_pointer + index * 4) for index in range(spec["fieldCount"])]
    sizes_table = int(registration["typeDefinitionsSizes"], 16)
    sizes_pointer = pe.u64_at_va(sizes_table + spec["typeIndex"] * 8)
    if not sizes_pointer:
        raise ContractError(f"{spec['type']} has no typeDefinitionsSizes entry")
    instance_size = pe.u32_at_va(sizes_pointer)
    native_size = _signed_i32(pe, sizes_pointer + 4)
    if instance_size != native_size + 16:
        raise ContractError(f"{spec['type']} instance/native size header relation drift")
    expected_fields = spec["fields"]
    if len(fields) != len(expected_fields):
        raise ContractError(f"{spec['type']} metadata field count drift")
    rows: list[dict[str, Any]] = []
    padding_gaps: list[dict[str, Any]] = []
    previous_end = -1
    native_offsets = [boxed_offset - 16 for boxed_offset in offsets]
    if native_size % NATIVE_ABI_ALIGNMENT_BYTES:
        raise ContractError(
            f"{spec['type']} native size 0x{native_size:x} violates "
            f"{NATIVE_ABI_ALIGNMENT_BYTES}-byte ABI alignment"
        )
    for index, (field, expected, boxed_offset) in enumerate(zip(expected_fields, fields, offsets)):
        name, type_index, kind, _declared_definition, *width_values = field
        declared_width = width_values[0] if width_values else None
        actual_name = md.string(expected.name_index)
        if actual_name != name or expected.type_index != type_index:
            raise ContractError(f"{spec['type']} field {index} declaration drift")
        offset = boxed_offset - 16
        if boxed_offset < 16:
            raise ContractError(f"{spec['type']} field {name} has invalid boxed/native relation")
        if offset != native_offsets[index] or offset < previous_end:
            raise ContractError(f"{spec['type']} fields overlap at {name}")
        next_offset = native_offsets[index + 1] if index + 1 < len(native_offsets) else native_size
        next_name = expected_fields[index + 1][0] if index + 1 < len(expected_fields) else None
        slot_width, slot_evidence = _field_slot_evidence(
            name=name,
            kind=kind,
            native_offset=offset,
            next_native_offset=next_offset,
            native_size=native_size,
            declared_width=declared_width or 0,
            next_field_name=next_name,
        )
        previous_end = offset + slot_width
        row = {
            "fieldIndex": expected.index,
            "name": name,
            "metadataTypeIndex": type_index,
            "kind": kind,
            "boxedFieldOffset": f"0x{boxed_offset:x}",
            "nativePayloadOffset": f"0x{offset:x}",
            "slotWidthBytes": slot_width,
            "slotWidthEvidence": slot_evidence,
            "token": f"0x{expected.token:08x}",
        }
        if kind in GENERIC_FIELD_KINDS:
            generic_evidence = _element_type_evidence(
                md=md,
                pe=pe,
                registration=registration,
                type_pointer_index=type_pointer_index,
                field_name=f"{spec['type']}.{name}",
                metadata_type_index=type_index,
                expected_kind=kind,
                expected_definition_index=field[3],
            )
            row.update(generic_evidence)
        rows.append(row)
        field_end = offset + slot_width
        if next_offset > field_end:
            padding_gaps.append({
                "nativePayloadOffset": f"0x{field_end:x}",
                "endNativePayloadOffset": f"0x{next_offset:x}",
                "sizeBytes": next_offset - field_end,
                "afterField": name,
                "beforeField": next_name,
                "basis": "declared_field_width_to_next_native_offset",
            })
    if native_size < previous_end:
        raise ContractError(f"{spec['type']} native size does not contain its final field")
    expected_gap = EXPECTED_PADDING_GAPS.get(spec["type"])
    if expected_gap is not None:
        actual_gap = padding_gaps
        if len(actual_gap) != 1:
            raise ContractError(
                f"{spec['type']} expected one explicit padding/gap record, "
                f"found {len(actual_gap)}"
            )
        gap_start, gap_end, after_field, before_field = expected_gap
        observed_gap = actual_gap[0]
        if (
            observed_gap["nativePayloadOffset"] != f"0x{gap_start:x}"
            or observed_gap["endNativePayloadOffset"] != f"0x{gap_end:x}"
            or observed_gap["afterField"] != after_field
            or observed_gap["beforeField"] != before_field
        ):
            raise ContractError(f"{spec['type']} explicit padding/gap boundary drift")
    elif padding_gaps:
        raise ContractError(f"{spec['type']} has unexpected padding/gap records")
    method = _validate_setter_metadata(md, spec)
    pointer = _method_pointer(md, native, pe, spec["setterMethodIndex"])
    index_offset = offsets[-1] - 16
    setter = _setter_evidence(pe, pointer, index_offset)
    return {
        "type": spec["type"],
        "typeIndex": spec["typeIndex"],
        "token": f"0x{type_def.token:08x}",
        "fieldStart": spec["fieldStart"],
        "fieldCount": spec["fieldCount"],
        "fieldOffsetsPointerVa": f"0x{field_offsets_pointer:x}",
        "typeDefinitionsSizesPointerVa": f"0x{sizes_pointer:x}",
        "instanceSizeBytes": instance_size,
        "nativeSizeBytes": native_size,
        "fields": rows,
        "paddingGaps": padding_gaps,
        "setIndexCount": {
            "methodIndex": spec["setterMethodIndex"],
            "token": f"0x{method.token:08x}",
            "parameter": {
                "parameterCount": method.parameter_count,
                "metadataTypeIndex": 83617,
                "kind": "NativeReference",
            },
            **setter,
        },
    }


def build_contract(*, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY, metadata: Path | None = DEFAULT_METADATA) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    game_path = Path(gate["gameAssembly"]["path"])
    metadata_path = Path(gate["globalMetadata"]["path"])
    catalog, native = _helpers()
    md = catalog.Metadata(metadata_path)
    pe = native.PeImage(game_path)
    declaration_names = {
        50690: "Unity.Collections.NativeArray`1",
        60806: "Unity.Collections.NativeReference`1",
        57221: "Unity.Mathematics.float4",
        42141: "System.Single",
    }
    for definition_index, expected_name in declaration_names.items():
        if md.type_full_name(md.types[definition_index]) != expected_name:
            raise ContractError(f"declaration type {definition_index} name drift")
    code_registration = native.find_code_registration(pe, {catalog_md_name for catalog_md_name in (md.string(image.name_index) for image in md.images)})
    if code_registration != 0x18B9217D0:
        raise ContractError(f"code registration drift: {code_registration!r}")
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if metadata_registration != 0x18B921C30:
        raise ContractError(f"metadata registration drift: {metadata_registration!r}")
    registration = native.metadata_registration_summary(pe, metadata_registration)
    max_type_index = max(spec["typeIndex"] for spec in JOBS)
    if int(registration["fieldOffsetsCount"]) < max_type_index + 1:
        raise ContractError("fieldOffsets table is too short")
    if int(registration["typeDefinitionsSizesCount"]) != len(md.types):
        raise ContractError(
            "typeDefinitionsSizes count does not match metadata TypeDef count: "
            f"{registration['typeDefinitionsSizesCount']} != {len(md.types)}"
        )
    if int(registration["typeDefinitionsSizesCount"]) < max_type_index + 1:
        raise ContractError("typeDefinitionsSizes table is too short")
    type_pointer_index = _build_type_pointer_index(pe, registration)
    jobs = [
        _build_job(md, native, pe, registration, type_pointer_index, spec)
        for spec in JOBS
    ]
    return {
        "schema": "endfield.charinfo.secondary-dynamics-job-layout.v1",
        "status": "outer_job_layout_closed",
        "outer_job_layout_recovered": True,
        "job_payload_layout_recovered": False,
        "secondary_dynamics_verified": False,
        "solver_implemented": False,
        "retail_equivalent": False,
        "native_gate": gate,
        "metadataRegistration": {
            "codeRegistrationVa": f"0x{code_registration:x}",
            "metadataRegistrationVa": f"0x{metadata_registration:x}",
            "fieldOffsets": registration["fieldOffsets"],
            "fieldOffsetsCount": registration["fieldOffsetsCount"],
            "types": registration["types"],
            "typesCount": registration["typesCount"],
            "typeDefinitionsSizes": registration["typeDefinitionsSizes"],
            "typeDefinitionsSizesCount": registration["typeDefinitionsSizesCount"],
        },
        "layoutBasis": {
            "il2cppObjectHeaderBytes": 16,
            "boxedFieldOffsets": "MetadataRegistration.fieldOffsets",
            "nativePayloadOffsets": "boxedFieldOffset - 0x10",
            "nativeSize": "MetadataRegistration.typeDefinitionsSizes.native_size",
            "concreteGenericSlotWidths": {
                "status": "closed_from_adjacent_offsets_and_native_size_tail",
                "source": "MetadataRegistration.fieldOffsets plus typeDefinitionsSizes.native_size",
                "abiAlignmentBytes": NATIVE_ABI_ALIGNMENT_BYTES,
                "genericTypeSizeClaimed": False,
                "boundary": "Each NativeArray/NativeReference width is the concrete closed job slot span; it is not the open generic type's total size.",
            },
            "declarationClassificationBoundary": "field kind labels classify the pinned metadata type indexes for readability only; they are not inner generic layout claims",
            "genericBoundary": {
                "NativeArray": {
                    "definitionIndex": 50690,
                    "innerLayoutRecovered": False,
                    "classificationBoundary": "declaration classification only; not an inner generic layout claim",
                },
                "NativeReference": {
                    "definitionIndex": 60806,
                    "innerLayoutRecovered": False,
                    "classificationBoundary": "declaration classification only; not an inner generic layout claim",
                },
            },
        },
        "jobs": jobs,
        "unresolved": [
            "NativeArray<T> inner m_Buffer/m_Length/m_AllocatorLabel offsets are not claimed.",
            "NativeReference<T> inner m_Data/m_AllocatorLabel offsets are not claimed.",
            "Execute/UnsafeDo and Burst constraint numerics are not recovered.",
        ],
    }


def verify_contract(path: Path = DEFAULT_OUTPUT) -> tuple[bool, str]:
    expected = json.dumps(build_contract(), indent=2, ensure_ascii=False) + "\n"
    if not path.is_file():
        return False, f"missing contract: {path}"
    actual = path.read_text(encoding="utf-8")
    if actual != expected:
        return False, "generated contract differs from a fresh native/metadata reconstruction"
    return True, "validated"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=DEFAULT_GAME_ASSEMBLY)
    parser.add_argument("--metadata", type=Path, default=DEFAULT_METADATA)
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
    except (OSError, ValueError, KeyError, struct.error, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
