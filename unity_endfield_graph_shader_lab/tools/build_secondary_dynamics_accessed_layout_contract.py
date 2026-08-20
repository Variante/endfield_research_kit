#!/usr/bin/env python3
"""Recover direct layouts of value types touched by secondary-dynamics helpers.

The existing element contract closes the six large NativeArray element types,
but the managed Spring/Wind helpers also receive a few smaller value types.
This contract records only those types whose direct fields are actually
addressed by the fixed-client helper bodies.  It does not expand a copied
vector/quaternion into a solver, and it does not claim that the Burst range
wrapper has been joined to a native implementation.

DummyDlls are intentionally not used here.  Names and field declarations come
from the pinned metadata, while offsets and native sizes come from the same
build's MetadataRegistration tables.  The exact GameAssembly and metadata
hash gate is mandatory and fail-closed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
SOURCE_ROOT = LAB_ROOT / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
DEFAULT_OUTPUT = SOURCE_ROOT / "secondary_dynamics_accessed_layout_contract.json"
EXPECTED_GAME_ASSEMBLY_SHA256 = "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
EXPECTED_METADATA_SHA256 = "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
STATIC_CONTRACT = SOURCE_ROOT / "secondary_dynamics_solver_static_contract.json"

if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.common import check_installed_native_inputs  # noqa: E402


class ContractError(RuntimeError):
    """Raised when the fixed-client accessed-layout evidence does not close."""


def _load(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ContractError(f"unable to load helper: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _helpers() -> tuple[Any, Any]:
    root = REPO_ROOT / "tools/endfield-il2cpp"
    return (
        _load("secondary_accessed_metadata", root / "catalog_option_flow_metadata.py"),
        _load("secondary_accessed_native", root / "map_body_targets_to_gameassembly.py"),
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _file(path: Path, digest: str | None = None) -> dict[str, Any]:
    return {"path": _path(path), "size": path.stat().st_size, "sha256": digest or _sha256(path)}


def _hex_signed(value: int) -> str:
    return f"-0x{-value:x}" if value < 0 else f"0x{value:x}"


def _native_gate(game_assembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    result = check_installed_native_inputs(
        EXPECTED_GAME_ASSEMBLY_SHA256,
        EXPECTED_METADATA_SHA256,
        gameassembly=game_assembly,
        metadata=metadata,
    )
    if not result.validated:
        raise ContractError(f"common.check_installed_native_inputs [{result.status}]: {result.detail}")
    gameassembly = Path(result.gameassembly)
    global_metadata = Path(result.metadata)
    return {
        "gameAssembly": _file(gameassembly, result.gameassembly_sha256),
        "globalMetadata": _file(global_metadata, result.metadata_sha256),
    }


# These are the value types passed to the three managed helper bodies.  The
# type/field indices are assertions against the selected metadata image; the
# actual offsets are always read from MetadataRegistration.fieldOffsets.
TYPE_SPECS: tuple[dict[str, Any], ...] = (
    {
        "name": "BeyondDynamicBone.SpringConstraint+SpringConstraintParams",
        "typeIndex": 48138,
        "fieldStart": 229085,
        "fieldCount": 4,
        "fields": (
            ("springPower", 163868),
            ("limitDistance", 163868),
            ("normalLimitRatio", 163868),
            ("springNoise", 163868),
        ),
    },
    {
        "name": "BeyondDynamicBone.WindParams",
        "typeIndex": 48182,
        "fieldStart": 229230,
        "fieldCount": 7,
        "fields": (
            ("influence", 163868),
            ("frequency", 163868),
            ("turbulence", 163868),
            ("blend", 163868),
            ("synchronization", 163868),
            ("depthWeight", 163868),
            ("movingWind", 163868),
        ),
    },
    {
        "name": "BeyondDynamicBone.TeamWindInfo",
        "typeIndex": 48440,
        "fieldStart": 230551,
        "fieldCount": 4,
        "fields": (
            ("windId", 148333),
            ("time", 163868),
            ("main", 163868),
            ("direction", 171871),
        ),
    },
    {
        "name": "Unity.Mathematics.double3",
        "typeIndex": 57201,
        "fieldStart": 278555,
        "fieldCount": 4,
        "fields": (
            ("x", 137537),
            ("y", 137537),
            ("z", 137537),
            ("zero", 171828),
        ),
        "staticFields": ("zero",),
    },
    {
        "name": "Unity.Mathematics.quaternion",
        "typeIndex": 57247,
        "fieldStart": 278684,
        "fieldCount": 2,
        "fields": (
            ("value", 171886),
            ("identity", 172161),
        ),
        "staticFields": ("identity",),
    },
    {
        "name": "Unity.Mathematics.float3",
        "typeIndex": 57216,
        "fieldStart": 278598,
        "fieldCount": 4,
        "fields": (
            ("x", 163868),
            ("y", 163868),
            ("z", 163868),
            ("zero", 171874),
        ),
        "staticFields": ("zero",),
    },
)


# This is the minimal mapping needed to explain why each selected type is in
# scope.  Access offsets are byte offsets observed in the pinned managed
# helper bodies, not inferred C# field offsets.
ACCESS_EVIDENCE: tuple[dict[str, Any], ...] = (
    {
        "methodIndex": 385698,
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "method": "Spring",
        "arguments": [
            {"name": "springParams", "type": "BeyondDynamicBone.SpringConstraint+SpringConstraintParams", "accessedOffsets": ["0x0", "0x4", "0x8", "0xc"]},
            {"name": "nextPos", "type": "Unity.Mathematics.double3", "accessedOffsets": ["0x0", "0x10"]},
            {"name": "basePos", "type": "Unity.Mathematics.double3", "accessedOffsets": ["0x0", "0x10"]},
            {"name": "baseRot", "type": "Unity.Mathematics.quaternion", "accessedOffsets": ["0x0"]},
        ],
    },
    {
        "methodIndex": 385699,
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "method": "Wind",
        "arguments": [
            {"name": "windParams", "type": "BeyondDynamicBone.WindParams", "accessedOffsets": ["0x0", "0x10", "0x14", "0x18"]},
            {"name": "result", "type": "Unity.Mathematics.float3", "accessedOffsets": ["0x0", "0x8"]},
        ],
    },
    {
        "methodIndex": 385700,
        "type": "BeyondDynamicBone.SimulationManager+StartSimulationStepJob",
        "method": "WindForceBlend",
        "arguments": [
            {"name": "windInfo", "type": "BeyondDynamicBone.TeamWindInfo", "accessedOffsets": ["0x4", "0x8", "0xc", "0x14"]},
            {"name": "windParams", "type": "BeyondDynamicBone.WindParams", "accessedOffsets": ["0x8", "0xc"]},
            {"name": "windPos", "type": "Unity.Mathematics.float3", "accessedOffsets": ["0x0", "0x8"]},
            {"name": "result", "type": "Unity.Mathematics.float3", "accessedOffsets": ["0x0", "0x8"]},
        ],
    },
)


def _signed_i32(pe: Any, va: int) -> int:
    value = pe.u32_at_va(va)
    return value - (1 << 32) if value & 0x80000000 else value


def _direct_type_layout(*, md: Any, pe: Any, registration: dict[str, Any], type_pointer_index: dict[int, list[int]], spec: dict[str, Any], element_module: Any) -> dict[str, Any]:
    type_index = int(spec["typeIndex"])
    type_def = md.types[type_index]
    name = str(spec["name"])
    if md.type_full_name(type_def) != name:
        raise ContractError(f"{name} TypeDef {type_index} name drift")
    if type_def.field_start != int(spec["fieldStart"]) or type_def.field_count != int(spec["fieldCount"]):
        raise ContractError(f"{name} field range drift")
    fields = md.fields_for(type_def)
    expected_fields = tuple(spec["fields"])
    if len(fields) != len(expected_fields):
        raise ContractError(f"{name} field count drift")
    offsets_table = int(registration["fieldOffsets"], 16)
    offsets_pointer = pe.u64_at_va(offsets_table + type_index * 8)
    if not offsets_pointer:
        raise ContractError(f"{name} has no fieldOffsets entry")
    sizes_table = int(registration["typeDefinitionsSizes"], 16)
    sizes_pointer = pe.u64_at_va(sizes_table + type_index * 8)
    if not sizes_pointer:
        raise ContractError(f"{name} has no typeDefinitionsSizes entry")
    native_size = _signed_i32(pe, sizes_pointer + 4)
    instance_size = pe.u32_at_va(sizes_pointer)
    if native_size <= 0 or instance_size != native_size + 16:
        raise ContractError(f"{name} instance/native size relation drift")

    rows: list[dict[str, Any]] = []
    static_rows: list[dict[str, Any]] = []
    static_names = set(spec.get("staticFields", ()))
    previous_end = -1
    for index, (field, expected) in enumerate(zip(fields, expected_fields)):
        expected_name, expected_type = expected
        actual_name = md.string(field.name_index)
        if actual_name != expected_name or field.type_index != int(expected_type):
            raise ContractError(f"{name}.{expected_name} declaration drift: actual={actual_name}/{field.type_index}")
        boxed_offset = _signed_i32(pe, offsets_pointer + index * 4)
        native_offset = boxed_offset - 16
        metadata_type = element_module._type_record(
            md=md,
            pe=pe,
            registration=registration,
            type_pointer_index=type_pointer_index,
            metadata_type_index=field.type_index,
            label=f"{name}.{actual_name}",
        )
        row = {
            "fieldIndex": field.index,
            "name": actual_name,
            "metadataTypeIndex": field.type_index,
            "metadataTypeName": metadata_type["name"],
            "boxedFieldOffset": _hex_signed(boxed_offset),
            "nativePayloadOffset": _hex_signed(native_offset),
            "metadataType": metadata_type,
            "token": f"0x{field.token:08x}",
        }
        # Static fields have negative payload offsets in this table.  They are
        # asserted and preserved as evidence, but are not part of an instance
        # layout or any helper-access claim.
        if actual_name in static_names:
            if native_offset >= 0:
                raise ContractError(f"{name}.{actual_name} is not a static offset")
            static_rows.append(row)
            continue
        if native_offset < 0 or native_offset < previous_end:
            raise ContractError(f"{name}.{actual_name} has invalid/overlapping instance offset")
        next_offsets = [
            _signed_i32(pe, offsets_pointer + next_index * 4) - 16
            for next_index in range(index + 1, len(fields))
            if md.string(fields[next_index].name_index) not in static_names
        ]
        next_native = min(next_offsets, default=native_size)
        span = next_native - native_offset
        if span <= 0 or next_native > native_size:
            raise ContractError(f"{name}.{actual_name} has invalid slot span {span}")
        row.update({
            "slotSpanBytes": span,
            "slotEndNativePayloadOffset": f"0x{next_native:x}",
            "slotSpanEvidence": {
                "status": "closed",
                "basis": "next_instance_field_native_offset" if next_offsets else "native_size_tail",
            },
        })
        rows.append(row)
        previous_end = native_offset + span
    if not rows or previous_end != native_size:
        raise ContractError(f"{name} instance fields do not close native size")
    return {
        "name": name,
        "typeIndex": type_index,
        "fieldStart": int(spec["fieldStart"]),
        "fieldCount": int(spec["fieldCount"]),
        "fieldOffsetsPointerVa": f"0x{offsets_pointer:x}",
        "typeDefinitionsSizesPointerVa": f"0x{sizes_pointer:x}",
        "instanceSizeBytes": instance_size,
        "nativeSizeBytes": native_size,
        "directFieldsOnly": True,
        "fields": rows,
        "staticFields": static_rows,
    }


def _method_evidence(*, md: Any, pe: Any, native: Any, code_registration: int) -> list[dict[str, Any]]:
    image_names = {md.string(image.name_index) for image in md.images}
    modules = native.parse_codegen_modules(pe, code_registration)
    ranges = native.image_method_ranges(md)
    _, method_by_pointer = native.build_pointer_indexes(pe, md, modules, ranges)
    output: list[dict[str, Any]] = []
    for expected in ACCESS_EVIDENCE:
        method_index = int(expected["methodIndex"])
        candidates = [
            (pointer, signature)
            for pointer, signatures in method_by_pointer.items()
            for signature in signatures
            if int(signature.get("methodIndex", -1)) == method_index
        ]
        if len(candidates) != 1:
            raise ContractError(f"method {method_index} resolves to {len(candidates)} native bodies")
        pointer, signature = candidates[0]
        if signature.get("method") != expected["method"] or signature.get("type") != expected["type"]:
            raise ContractError(f"method {method_index} identity drift")
        static = json.loads(STATIC_CONTRACT.read_text(encoding="utf-8"))
        static_rows = [row for row in static.get("targets", []) if int(row.get("methodIndex", -1)) == method_index]
        if len(static_rows) != 1:
            raise ContractError(f"static contract lacks unique helper row {method_index}")
        row = static_rows[0]
        expected_va = int(str(row["va"]), 16)
        expected_end = int(str(row["endVaExclusive"]), 16)
        if pointer != expected_va:
            raise ContractError(f"method {method_index} pointer drift: 0x{pointer:x} != 0x{expected_va:x}")
        body = pe.bytes_at_va(pointer, expected_end - expected_va)
        digest = hashlib.sha256(body).hexdigest()
        if digest != row["bodySha256"]:
            raise ContractError(f"method {method_index} body hash drift: {digest}")
        output.append({
            "methodIndex": method_index,
            "type": expected["type"],
            "method": expected["method"],
            "va": row["va"],
            "endVaExclusive": row["endVaExclusive"],
            "spanBytes": row["spanBytes"],
            "bodySha256": row["bodySha256"],
            "accesses": expected["arguments"],
        })
    return output


def build_contract(*, game_assembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    gate = _native_gate(game_assembly, metadata)
    metadata_module, native = _helpers()
    element_module = _load("secondary_accessed_element", LAB_ROOT / "tools/build_secondary_dynamics_element_layout_contract.py")
    md = metadata_module.Metadata(Path(gate["globalMetadata"]["path"]))
    pe = native.PeImage(Path(gate["gameAssembly"]["path"]))
    image_names = {md.string(image.name_index) for image in md.images}
    code_registration = native.find_code_registration(pe, image_names)
    if code_registration != 0x18B9217D0:
        raise ContractError(f"code registration drift: 0x{code_registration:x}")
    metadata_registration = native.find_metadata_registration(pe, code_registration)
    registration = native.metadata_registration_summary(pe, metadata_registration)
    type_pointer_index = element_module._build_type_pointer_index(pe, registration)
    layouts = [
        _direct_type_layout(
            md=md,
            pe=pe,
            registration=registration,
            type_pointer_index=type_pointer_index,
            spec=spec,
            element_module=element_module,
        )
        for spec in TYPE_SPECS
    ]
    return {
        "schema": "endfield.charinfo.secondary-dynamics-accessed-layout.v1",
        "status": "accessed_nested_direct_layouts_closed",
        "accessed_layouts_recovered": True,
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
        "layouts": layouts,
        "methodEvidence": _method_evidence(md=md, pe=pe, native=native, code_registration=code_registration),
        "boundary": {
            "largeElementInputs": "TeamData, CenterData, and other NativeArray element layouts remain owned by secondary_dynamics_element_layout_contract.json.",
            "genericInputs": "No generic element field is directly addressed by Spring, Wind, or WindForceBlend; NativeArray/NativeReference remain outer job-payload boundaries.",
            "quaternionValue": "Unity.Mathematics.quaternion.value is retained as an opaque 16-byte float4 payload because the selected helpers copy the quaternion blob and do not address its component fields by name.",
            "solver": "Managed helper arithmetic and Burst range-dispatch implementation remain separate unresolved work; this report is not a solver implementation.",
        },
        "unresolved": [
            "The helper bodies' called math functions are not reimplemented here.",
            "Burst Execute/UnsafeDo range wrappers are not joined to a verified solver export.",
            "No Transform writeback or retail-equivalence claim is made.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-assembly", type=Path, default=None)
    parser.add_argument("--metadata", type=Path, default=None)
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
    except (OSError, ValueError, KeyError, IndexError, ContractError) as exc:
        print(json.dumps({"status": "unavailable", "validationFailures": [str(exc)]}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
