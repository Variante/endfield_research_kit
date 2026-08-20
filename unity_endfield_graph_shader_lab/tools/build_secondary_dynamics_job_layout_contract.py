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
            ("jobColliderIndexList", 83201, "NativeArray", 50690, 16),
            ("teamDataArray", 83381, "NativeArray", 50690, 16),
            ("centerDataArray", 83349, "NativeArray", 50690, 16),
            ("teamIdArray", 83197, "NativeArray", 50690, 16),
            ("flagArray", 83139, "NativeArray", 50690, 16),
            ("sizeArray", 83304, "NativeArray", 50690, 16),
            ("framePositions", 83298, "NativeArray", 50690, 16),
            ("frameRotations", 83315, "NativeArray", 50690, 16),
            ("frameScales", 83304, "NativeArray", 50690, 16),
            ("oldFramePositions", 83298, "NativeArray", 50690, 16),
            ("oldFrameRotations", 83315, "NativeArray", 50690, 16),
            ("nowPositions", 83298, "NativeArray", 50690, 16),
            ("nowRotations", 83315, "NativeArray", 50690, 16),
            ("oldPositions", 83298, "NativeArray", 50690, 16),
            ("oldRotations", 83315, "NativeArray", 50690, 16),
            ("workDataArray", 83340, "NativeArray", 50690, 16),
            ("_indexCount", 83620, "NativeReference", 60806, 16),
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
            ("jobColliderIndexList", 83201, "NativeArray", 50690, 16),
            ("nowPositions", 83298, "NativeArray", 50690, 16),
            ("nowRotations", 83315, "NativeArray", 50690, 16),
            ("oldPositions", 83298, "NativeArray", 50690, 16),
            ("oldRotations", 83315, "NativeArray", 50690, 16),
            ("_indexCount", 83620, "NativeReference", 60806, 16),
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
            ("stepParticleIndexArray", 83201, "NativeArray", 50690, 16),
            ("attributes", 83290, "NativeArray", 50690, 16),
            ("depthArray", 83240, "NativeArray", 50690, 16),
            ("positions", 83298, "NativeArray", 50690, 16),
            ("rotations", 83315, "NativeArray", 50690, 16),
            ("vertexRootIndices", 83201, "NativeArray", 50690, 16),
            ("teamDataArray", 83381, "NativeArray", 50690, 16),
            ("parameterArray", 83108, "NativeArray", 50690, 16),
            ("centerDataArray", 83349, "NativeArray", 50690, 16),
            ("teamWindArray", 83253, "NativeArray", 50690, 16),
            ("windDataArray", 83391, "NativeArray", 50690, 16),
            ("teamIdArray", 83197, "NativeArray", 50690, 16),
            ("oldPosArray", 83298, "NativeArray", 50690, 16),
            ("nextPosArray", 83298, "NativeArray", 50690, 16),
            ("basePosArray", 83298, "NativeArray", 50690, 16),
            ("velocityArray", 83304, "NativeArray", 50690, 16),
            ("baseRotArray", 83315, "NativeArray", 50690, 16),
            ("oldPositionArray", 83298, "NativeArray", 50690, 16),
            ("oldRotationArray", 83315, "NativeArray", 50690, 16),
            ("velocityPosArray", 83298, "NativeArray", 50690, 16),
            ("frictionArray", 83240, "NativeArray", 50690, 16),
            ("stepBasicPositionArray", 83298, "NativeArray", 50690, 16),
            ("stepBasicRotationArray", 83315, "NativeArray", 50690, 16),
            ("_indexCount", 83620, "NativeReference", 60806, 16),
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
            ("stepParticleIndexArray", 83201, "NativeArray", 50690, 16),
            ("teamDataArray", 83381, "NativeArray", 50690, 16),
            ("parameterArray", 83108, "NativeArray", 50690, 16),
            ("centerDataArray", 83349, "NativeArray", 50690, 16),
            ("attributes", 83290, "NativeArray", 50690, 16),
            ("vertexDepths", 83240, "NativeArray", 50690, 16),
            ("teamIdArray", 83197, "NativeArray", 50690, 16),
            ("nextPosArray", 83298, "NativeArray", 50690, 16),
            ("oldPosArray", 83298, "NativeArray", 50690, 16),
            ("velocityPosArray", 83298, "NativeArray", 50690, 16),
            ("velocityArray", 83304, "NativeArray", 50690, 16),
            ("realVelocityArray", 83304, "NativeArray", 50690, 16),
            ("frictionArray", 83240, "NativeArray", 50690, 16),
            ("staticFrictionArray", 83240, "NativeArray", 50690, 16),
            ("collisionNormalArray", 83304, "NativeArray", 50690, 16),
            ("_indexCount", 83620, "NativeReference", 60806, 16),
        ),
    },
)


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


def _build_job(md: Any, native: Any, pe: Any, registration: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
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
    previous_end = -1
    for index, (field, expected, boxed_offset) in enumerate(zip(expected_fields, fields, offsets)):
        name, type_index, kind, _declared_definition, width = field
        actual_name = md.string(expected.name_index)
        if actual_name != name or expected.type_index != type_index:
            raise ContractError(f"{spec['type']} field {index} declaration drift")
        offset = boxed_offset - 16
        if boxed_offset < 16:
            raise ContractError(f"{spec['type']} field {name} has invalid boxed/native relation")
        if offset < previous_end:
            raise ContractError(f"{spec['type']} fields overlap at {name}")
        previous_end = offset + width
        rows.append({
            "fieldIndex": expected.index,
            "name": name,
            "metadataTypeIndex": type_index,
            "kind": kind,
            "boxedFieldOffset": f"0x{boxed_offset:x}",
            "nativePayloadOffset": f"0x{offset:x}",
            "slotWidthBytes": width,
            "token": f"0x{expected.token:08x}",
        })
    if native_size < previous_end:
        raise ContractError(f"{spec['type']} native size does not contain its final field")
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
    if int(registration["typeDefinitionsSizesCount"]) < max_type_index + 1:
        raise ContractError("typeDefinitionsSizes table is too short")
    jobs = [_build_job(md, native, pe, registration, spec) for spec in JOBS]
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
            "typeDefinitionsSizes": registration["typeDefinitionsSizes"],
            "typeDefinitionsSizesCount": registration["typeDefinitionsSizesCount"],
        },
        "layoutBasis": {
            "il2cppObjectHeaderBytes": 16,
            "boxedFieldOffsets": "MetadataRegistration.fieldOffsets",
            "nativePayloadOffsets": "boxedFieldOffset - 0x10",
            "nativeSize": "MetadataRegistration.typeDefinitionsSizes.native_size",
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
