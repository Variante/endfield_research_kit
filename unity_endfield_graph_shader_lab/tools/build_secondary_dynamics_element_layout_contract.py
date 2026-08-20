#!/usr/bin/env python3
"""Recover direct native layouts for the secondary-dynamics job elements.

The outer job contract identifies the six value types below as NativeArray
elements.  This contract resolves their *direct* fields from the pinned
IL2CPP ``MetadataRegistration.fieldOffsets`` and
``MetadataRegistration.typeDefinitionsSizes`` tables.  It intentionally does
not recurse into embedded value types, references, or generic fields: those
are recorded as type boundaries for a later, separately gated recovery.

No solver, Burst execution, or transform writeback is implied by this file.
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
DEFAULT_GAME_ASSEMBLY: Path | None = None
DEFAULT_METADATA: Path | None = None
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
DEFAULT_OUTPUT = LAB_ROOT / (
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation/"
    "secondary_dynamics_element_layout_contract.json"
)

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402

IL2CPP_TYPE_CLASS = 0x12
IL2CPP_TYPE_GENERICINST = 0x15
IL2CPP_TYPE_VALUETYPE = 0x11
IL2CPP_PRIMITIVE_TYPE_CODES = frozenset({
    0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09,
    0x0A, 0x0B, 0x0C, 0x0D, 0x18, 0x19,
})

# This is a declaration contract, not a source of offsets.  Every offset and
# native size below is read from the selected build's registration tables.
STRUCTS: tuple[tuple[str, int, int, int, tuple[tuple[str, int], ...]], ...] = (
    (
        "BeyondDynamicBone.TeamManager+TeamData", 48233, 229636, 69,
        (
            ("flag", 130498), ("originalUpdateMode", 134033), ("updateMode", 134033),
            ("frameDeltaTime", 163868), ("time", 163868), ("oldTime", 163868),
            ("nowUpdateTime", 163868), ("oldUpdateTime", 163868),
            ("frameUpdateTime", 163868), ("frameOldTime", 163868),
            ("timeScale", 163868), ("nowTimeScale", 163868),
            ("updateCount", 148333), ("skipCount", 148333),
            ("frameInterpolation", 163868), ("gravityRatio", 163868),
            ("gravityDot", 163868), ("centerTransformIndex", 148333),
            ("distanceReferenceObjectId", 148333), ("componentTransformIndex", 148333),
            ("initScale", 171871), ("scaleRatio", 163868),
            ("negativeScaleSign", 163868), ("negativeScaleDirection", 171871),
            ("negativeScaleChange", 171871), ("negativeScaleTriangleSign", 171862),
            ("negativeScaleQuaternionValue", 171886), ("componentId", 148333),
            ("useRelativeTransform", 148333), ("relativeTransformPos", 171871),
            ("relativeTransformRot", 172159), ("syncTeamId", 148333),
            ("syncParentTeamId", 34499), ("syncCenterTransformIndex", 148333),
            ("interlockingAnimatorId", 148333), ("animationPoseRatio", 163868),
            ("resetSimulationToAnimationPose", 148333), ("clothSimulateWeight", 163868),
            ("clothLodFadeWeight", 163868), ("clothLodFadeTime", 163868),
            ("velocityWeight", 163868), ("distanceWeight", 163868),
            ("blendWeight", 163868), ("forceMode", 133984), ("impactForce", 171871),
            ("proxyMeshType", 208174), ("proxyTransformChunk", 136096),
            ("proxyCommonChunk", 136096), ("proxyVertexChildDataChunk", 136096),
            ("proxyTriangleChunk", 136096), ("proxyEdgeChunk", 136096),
            ("proxyMeshChunk", 136096), ("proxyBoneChunk", 136096),
            ("proxySkinBoneChunk", 136096), ("baseLineChunk", 136096),
            ("baseLineDataChunk", 136096), ("fixedDataChunk", 136096),
            ("particleChunk", 136096), ("colliderChunk", 136096),
            ("colliderTransformChunk", 136096), ("colliderCount", 148333),
            ("distanceStartChunk", 136096), ("distanceDataChunk", 136096),
            ("bendingPairChunk", 136096), ("bendingWriteIndexChunk", 136096),
            ("bendingBufferChunk", 136096), ("selfPointChunk", 136096),
            ("selfEdgeChunk", 136096), ("selfTriangleChunk", 136096),
        ),
    ),
    (
        "BeyondDynamicBone.InertiaConstraint+CenterData", 48071, 228827, 40,
        (
            ("anchorPosition", 171827), ("anchorRotation", 172159),
            ("oldAnchorPosition", 171827), ("oldAnchorRotation", 172159),
            ("anchorComponentLocalPosition", 171871), ("centerTransformIndex", 148333),
            ("componentWorldPosition", 171827), ("componentWorldRotation", 172159),
            ("componentWorldScale", 171871), ("oldComponentWorldPosition", 171827),
            ("oldComponentWorldRotation", 172159), ("oldComponentWorldScale", 171871),
            ("frameComponentShiftVector", 171871), ("frameComponentShiftRotation", 172159),
            ("frameMovingSpeed", 163868), ("frameMovingDirection", 171871),
            ("frameWorldPosition", 171827), ("frameWorldRotation", 172159),
            ("frameWorldScale", 171871), ("frameLocalPosition", 171871),
            ("oldFrameWorldPosition", 171827), ("oldFrameWorldRotation", 172159),
            ("oldFrameWorldScale", 171871), ("nowWorldPosition", 171827),
            ("nowWorldRotation", 172159), ("oldWorldPosition", 171827),
            ("oldWorldRotation", 172159), ("stepMoveInertiaRatio", 163868),
            ("stepRotationInertiaRatio", 163868), ("stepVector", 171871),
            ("stepRotation", 172159), ("inertiaVector", 171871),
            ("inertiaRotation", 172159), ("stepMovingSpeed", 163868),
            ("stepMovingDirection", 171871), ("angularVelocity", 163868),
            ("rotationAxis", 171871), ("initLocalGravityDirection", 171871),
            ("smoothingVelocity", 171871), ("negativeScaleMatrix", 171843),
        ),
    ),
    (
        "BeyondDynamicBone.ClothParameters", 48002, 228424, 21,
        (
            ("gravity", 163868), ("worldGravityDirection", 171871),
            ("gravityFalloff", 163868), ("stablizationTimeAfterReset", 163868),
            ("blendWeight", 163868), ("dampingCurveData", 171893),
            ("radiusCurveData", 171893), ("normalAxis", 134010),
            ("rotationalInterpolation", 163868), ("rootRotation", 163868),
            ("culling", 187438), ("inertiaConstraint", 195742),
            ("tetherConstraint", 206495), ("distanceConstraint", 188470),
            ("triangleBendingConstraint", 206995), ("angleConstraint", 173401),
            ("motionConstraint", 198343), ("colliderCollisionConstraint", 186574),
            ("selfCollisionConstraint", 203734), ("wind", 170728),
            ("springConstraint", 204589),
        ),
    ),
    (
        "BeyondDynamicBone.ColliderManager+WorkData", 48373, 230209, 6,
        (
            ("aabb", 120614), ("radius", 171862), ("oldPos", 171831),
            ("nextPos", 171831), ("inverseOldRot", 172159), ("rot", 172159),
        ),
    ),
    (
        "BeyondDynamicBone.TeamWindData", 48441, 230555, 2,
        (("windZoneList", 34479), ("movingWind", 166202)),
    ),
    (
        "BeyondDynamicBone.WindManager+WindData", 48431, 230491, 12,
        (
            ("flag", 130495), ("mode", 174412), ("size", 171871),
            ("main", 163868), ("turbulence", 163868), ("zoneVolume", 163868),
            ("worldWindDirection", 171871), ("worldPositin", 171871),
            ("worldRotation", 172159), ("worldScale", 171871),
            ("worldToLocalMatrix", 171893), ("attenuation", 171893),
        ),
    ),
)


class ContractError(RuntimeError):
    """Raised when a pinned direct-field layout does not close."""


def _load(name: str, path: Path) -> Any:
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
        _load("secondary_element_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_element_native", root / "map_body_targets_to_gameassembly.py"),
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


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _repo_path(path), "size": path.stat().st_size,
            "sha256": digest or _sha256(path)}


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
        "gameAssembly": _file(Path(result.gameassembly), result.gameassembly_sha256),
        "globalMetadata": _file(Path(result.metadata), result.metadata_sha256),
    }


def _signed_i32(pe: Any, va: int) -> int:
    return struct.unpack("<i", struct.pack("<I", pe.u32_at_va(va)))[0]


def _type_definition_name(md: Any, index: int, label: str) -> str:
    if index < 0 or index >= len(md.types):
        raise ContractError(f"{label} TypeDef index {index} is outside metadata")
    return md.type_full_name(md.types[index])


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


def _type_record(
    *, md: Any, pe: Any, registration: dict[str, Any], type_pointer_index: dict[int, list[int]],
    metadata_type_index: int, label: str,
) -> dict[str, Any]:
    count = int(registration["typesCount"])
    if metadata_type_index < 0 or metadata_type_index >= count:
        raise ContractError(f"{label} metadata type index {metadata_type_index} is outside types")
    table = int(registration["types"], 16)
    pointer = pe.u64_at_va(table + metadata_type_index * 8)
    if not pointer:
        raise ContractError(f"{label} metadata type index has a null types entry")
    type_code = pe.bytes_at_va(pointer + 10, 1)[0]
    data = pe.u64_at_va(pointer)
    primitive = type_code in IL2CPP_PRIMITIVE_TYPE_CODES
    record: dict[str, Any] = {
        "metadataTypeIndex": metadata_type_index,
        "typeCode": f"0x{type_code:x}",
        "typeCodeValue": type_code,
        "typePointerVa": f"0x{pointer:x}",
        "category": "primitive" if primitive else (
            "valueType" if type_code == IL2CPP_TYPE_VALUETYPE else
            "reference" if type_code == IL2CPP_TYPE_CLASS else
            "generic" if type_code == IL2CPP_TYPE_GENERICINST else "other"
        ),
        "recursiveBoundary": "direct_field_only",
    }
    if primitive or type_code in (IL2CPP_TYPE_VALUETYPE, IL2CPP_TYPE_CLASS):
        type_definition_index = int(data)
        record["typeDefinitionIndex"] = type_definition_index
        record["name"] = _type_definition_name(md, type_definition_index, label)
        sizes_count = int(registration["typeDefinitionsSizesCount"])
        if 0 <= type_definition_index < sizes_count:
            sizes_table = int(registration["typeDefinitionsSizes"], 16)
            sizes_pointer = pe.u64_at_va(sizes_table + type_definition_index * 8)
            if sizes_pointer:
                record["typeDefinitionNativeSizeBytes"] = _signed_i32(pe, sizes_pointer + 4)
        return record
    if type_code != IL2CPP_TYPE_GENERICINST:
        record["name"] = f"<type-code:0x{type_code:x}>"
        record["genericOrReferenceBoundary"] = "unresolved_type_code"
        return record

    generic_class_pointer = data
    if not generic_class_pointer:
        raise ContractError(f"{label} generic class pointer is null")
    definition_class_pointer = pe.u64_at_va(generic_class_pointer)
    context_pointer = pe.u64_at_va(generic_class_pointer + 8)
    if not definition_class_pointer or not context_pointer:
        raise ContractError(f"{label} generic class/context pointer is null")
    definition_index = pe.u32_at_va(definition_class_pointer)
    definition_name = _type_definition_name(md, definition_index, label)
    argument_count = pe.u32_at_va(context_pointer)
    argument_vector = pe.u64_at_va(context_pointer + 8)
    if argument_count <= 0 or argument_count > 8 or not argument_vector:
        raise ContractError(f"{label} generic context has invalid argument count/vector")
    arguments: list[dict[str, Any]] = []
    argument_names: list[str] = []
    for index in range(argument_count):
        argument_pointer = pe.u64_at_va(argument_vector + index * 8)
        candidates = type_pointer_index.get(argument_pointer, [])
        if len(candidates) != 1:
            raise ContractError(
                f"{label} generic argument {index} pointer 0x{argument_pointer:x} "
                f"maps to {len(candidates)} metadata type indexes"
            )
        argument_type = _type_record(
            md=md, pe=pe, registration=registration,
            type_pointer_index=type_pointer_index,
            metadata_type_index=candidates[0], label=f"{label} generic argument {index}",
        )
        arguments.append({
            "metadataTypeIndex": candidates[0],
            "name": argument_type["name"],
            "typeCode": argument_type["typeCode"],
        })
        argument_names.append(argument_type["name"])
    record.update({
        "name": f"{definition_name}<{', '.join(argument_names)}>",
        "genericDefinitionTypeIndex": definition_index,
        "genericDefinitionName": definition_name,
        "genericContext": {
            "genericClassPointerVa": f"0x{generic_class_pointer:x}",
            "genericDefinitionClassPointerVa": f"0x{definition_class_pointer:x}",
            "genericContextPointerVa": f"0x{context_pointer:x}",
            "argumentCount": argument_count,
            "argumentVectorVa": f"0x{argument_vector:x}",
            "arguments": arguments,
        },
        "genericOrReferenceBoundary": "generic_arguments_not_recursed",
    })
    return record


def _build_struct(
    *, md: Any, pe: Any, registration: dict[str, Any], type_pointer_index: dict[int, list[int]],
    spec: tuple[str, int, int, int, tuple[tuple[str, int], ...]],
) -> dict[str, Any]:
    name, type_index, field_start, field_count, expected_fields = spec
    type_def = md.types[type_index] if 0 <= type_index < len(md.types) else None
    if type_def is None or md.type_full_name(type_def) != name:
        raise ContractError(f"element TypeDef {type_index} name drift: {name}")
    if type_def.field_start != field_start or type_def.field_count != field_count:
        raise ContractError(f"{name} field range drift")
    fields = md.fields_for(type_def)
    if len(fields) != len(expected_fields):
        raise ContractError(f"{name} metadata field count drift")
    field_table = int(registration["fieldOffsets"], 16)
    field_offsets_pointer = pe.u64_at_va(field_table + type_index * 8)
    if not field_offsets_pointer:
        raise ContractError(f"{name} has no fieldOffsets entry")
    offsets = [
        _signed_i32(pe, field_offsets_pointer + index * 4)
        for index in range(field_count)
    ]
    sizes_table = int(registration["typeDefinitionsSizes"], 16)
    sizes_pointer = pe.u64_at_va(sizes_table + type_index * 8)
    if not sizes_pointer:
        raise ContractError(f"{name} has no typeDefinitionsSizes entry")
    instance_size = pe.u32_at_va(sizes_pointer)
    native_size = _signed_i32(pe, sizes_pointer + 4)
    if native_size <= 0 or instance_size != native_size + 16:
        raise ContractError(f"{name} instance/native size relation drift")
    native_offsets = [offset - 16 for offset in offsets]
    rows: list[dict[str, Any]] = []
    previous_end = -1
    for index, (field, expected) in enumerate(zip(fields, expected_fields)):
        expected_name, expected_type_index = expected
        actual_name = md.string(field.name_index)
        if actual_name != expected_name or field.type_index != expected_type_index:
            raise ContractError(
                f"{name}.{expected_name} declaration drift: "
                f"actual={actual_name}/{field.type_index}"
            )
        boxed_offset = offsets[index]
        native_offset = native_offsets[index]
        if boxed_offset < 16 or native_offset < previous_end:
            raise ContractError(f"{name}.{actual_name} has invalid/overlapping offset")
        next_native_offset = native_offsets[index + 1] if index + 1 < len(native_offsets) else native_size
        span = next_native_offset - native_offset
        if native_offset < 0 or span <= 0 or next_native_offset > native_size:
            raise ContractError(f"{name}.{actual_name} has invalid slot span {span}")
        metadata_type = _type_record(
            md=md, pe=pe, registration=registration,
            type_pointer_index=type_pointer_index,
            metadata_type_index=field.type_index,
            label=f"{name}.{actual_name}",
        )
        row = {
            "fieldIndex": field.index,
            "name": actual_name,
            "metadataTypeIndex": field.type_index,
            "metadataTypeName": metadata_type["name"],
            "metadataType": metadata_type,
            "boxedFieldOffset": f"0x{boxed_offset:x}",
            "nativePayloadOffset": f"0x{native_offset:x}",
            "slotSpanBytes": span,
            "slotEndNativePayloadOffset": f"0x{next_native_offset:x}",
            "slotSpanEvidence": {
                "status": "closed",
                "basis": "next_field_native_offset" if index + 1 < len(native_offsets) else "native_size_tail",
                "nextField": expected_fields[index + 1][0] if index + 1 < len(expected_fields) else None,
            },
            "token": f"0x{field.token:08x}",
        }
        rows.append(row)
        previous_end = native_offset + span
    if previous_end != native_size:
        raise ContractError(f"{name} final field does not close native size")
    return {
        "name": name,
        "typeIndex": type_index,
        "fieldStart": field_start,
        "fieldCount": field_count,
        "fieldOffsetsPointerVa": f"0x{field_offsets_pointer:x}",
        "typeDefinitionsSizesPointerVa": f"0x{sizes_pointer:x}",
        "instanceSizeBytes": instance_size,
        "nativeSizeBytes": native_size,
        "directFieldsOnly": True,
        "fields": rows,
    }


def build_contract(
    *, game_assembly: Path | None = DEFAULT_GAME_ASSEMBLY,
    metadata: Path | None = DEFAULT_METADATA,
) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    catalog, native = _helpers()
    md = catalog.Metadata(Path(gate["globalMetadata"]["path"]))
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    if code_registration != 0x18B9217D0:
        raise ContractError(f"code registration drift: {code_registration!r}")
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    if metadata_registration != 0x18B921C30:
        raise ContractError(f"metadata registration drift: {metadata_registration!r}")
    registration = native.metadata_registration_summary(pe, metadata_registration)
    if int(registration["typeDefinitionsSizesCount"]) != len(md.types):
        raise ContractError("typeDefinitionsSizes count does not match metadata TypeDefs")
    max_type_index = max(spec[1] for spec in STRUCTS)
    if int(registration["fieldOffsetsCount"]) <= max_type_index:
        raise ContractError("fieldOffsets table is too short for selected elements")
    if int(registration["typeDefinitionsSizesCount"]) <= max_type_index:
        raise ContractError("typeDefinitionsSizes table is too short for selected elements")
    type_pointer_index = _build_type_pointer_index(pe, registration)
    elements = [
        _build_struct(
            md=md, pe=pe, registration=registration,
            type_pointer_index=type_pointer_index, spec=spec,
        )
        for spec in STRUCTS
    ]
    return {
        "schema": "endfield.charinfo.secondary-dynamics-element-layout.v1",
        "status": "element_struct_direct_layout_closed",
        "element_struct_layout_recovered": True,
        "direct_fields_recovered": True,
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
            "slotSpan": "next direct field native offset, or native size tail for final field",
            "recursiveBoundary": "Only direct fields are recovered; embedded value types, references, and generic arguments are not expanded.",
        },
        "elements": elements,
        "unresolved": [
            "Nested value-type layouts are retained as direct field type boundaries and are not recursively expanded.",
            "Reference and generic fields are retained as opaque direct-field boundaries; no ownership or element access is claimed.",
            "Burst Execute/UnsafeDo, solver numerics, scheduling, and transform writeback remain unrecovered.",
        ],
    }


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
    except (OSError, ValueError, KeyError, IndexError, struct.error, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
