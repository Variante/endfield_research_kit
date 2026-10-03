"""Authenticate SludgeComp.SurfTileIDs and audit current primitive-int ownership.

The selected getter identifies an inline DataGroup. The corpus audit tests its
stored span alongside RootComp and resource visibility spans, without assigning
runtime behavior to the selected tile IDs.

The selected ``FBDynamicSceneSludgeComp.get_SurfTileIDs`` fast path returns an
inline ``FBDynamicSceneDataGroup`` from the SludgeComp record
(``dynamic_sludge_surf_tile_native.json``); the main-vector contract supplies
the record vector and width and the RootComp contract the shared DataGroup
layout and ``PrimitiveInt`` type. The field and offset come from native code,
not from nearby bytes or a value pattern.

The audit checks the native inputs, VFS input set, every main dump's size and
MD5, all main-vector bounds, and each group's type, grid ID, index, count and
total. In every authenticated current grid the ``SurfTileIDs`` spans are
disjoint from the RootComp and ResourceGroup visibility spans, and the three
families tile ``PrimitiveIntList`` exactly (structural). The selected values
are nonzero stored tile IDs, not padding.

The reviewed collector returns positive, bounded grid-local primitive IDs to
a supplied UInt64 list. A selected load-check path passes those IDs to
NavMeshChunkManager.IsSurfaceLoaded; its Boolean result gates the selected
navmesh-apply call. Accessor, carrier, list insertion and caller joins are
authenticated independently. These are conditional native consumers: live
Sludge/grid selection, patch routes and actual navmesh state remain open.

Run ``python -m scripts.game_data.dynamic_sludge_surf_tile_native
--gameassembly PATH --metadata PATH --input-root DUMP_ROOT
--expected-input-set-sha256 INPUT_SET_SHA256`` over the targeted ``fb_main``
dump. It writes
``reports/animestudio/dynamic_sludge_surf_tile_native_latest.{json,md}``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_resource_comp_native import (
    _checked_span,
    _group,
    validate_native_layout as validate_resource_layout,
)
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    MAIN_NAME_RE,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import (
    _bounded_vector,
    _field_span,
    _root_layout,
    _table_layout,
    parse_dynamic_file,
)
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context import (
    generic_method_candidates, relative_branch_target, rip_qword_load_target, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import runtime_type_name
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_sludge_surf_tile_native.json"
SCHEMA = "endfield.dynamic-sludge-surf-tile-native-contract.v2"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_sludge_surf_tile_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_sludge_surf_tile_native_latest.md"


class DynamicSludgeSurfTileError(ValueError):
    """The selected getter, authenticated corpus, or stored spans differ."""


def _consumer_type_name(image: Any, index: int) -> str:
    if not 0 <= index < image.registration["typesCount"]:
        raise DynamicSludgeSurfTileError(f"consumer:signature:type-index={index}")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def _checked_consumer_window(image: Any, name: str, window: dict[str, Any]) -> bytes:
    rva, length = int(window["rva"]), int(window["length"])
    if rva < 0 or not 0 < length <= 4096:
        raise DynamicSludgeSurfTileError(f"consumer:{name}:invalid-window={rva}:{length}")
    raw = image.pe.bytes_at_va(image.pe.image_base + rva, length)
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != window["sha256"]:
        raise DynamicSludgeSurfTileError(
            f"consumer:{name}:code-window expected={window['sha256']} actual={actual} "
            f"source={getattr(image, 'gameassembly', '<selected native image>')} rva={rva:#x}")
    return raw


def _consumer_range(block: dict[str, Any], raw: dict[str, bytes], row: dict[str, Any],
                    size: int, label: str) -> bytes:
    owner = row["window"]
    offset = int(row["rva"]) - int(block["windows"][owner]["rva"])
    if not 0 <= offset <= len(raw[owner]) - size:
        raise DynamicSludgeSurfTileError(f"consumer:{label}:outside-window={owner}")
    return raw[owner][offset:offset + size]


def _checked_consumer_branch(raw: bytes, rva: int, prefix: bytes, target: int, label: str) -> None:
    if not raw.startswith(prefix) or len(raw) != len(prefix) + (1 if len(prefix) == 1 else 4):
        raise DynamicSludgeSurfTileError(f"consumer:{label}:branch-shape={raw.hex().upper()}")
    displacement = struct.unpack_from("<b" if len(prefix) == 1 else "<i", raw, len(prefix))[0]
    actual = rva + len(raw) + displacement
    if actual != target:
        raise DynamicSludgeSurfTileError(
            f"consumer:{label}:branch-target expected={target:#x} actual={actual:#x}")


def _validate_list_add_context(image: Any, block: dict[str, Any]) -> dict[str, Any]:
    """Join the supplied static Add companion independently of inline code."""
    pins = block["listAddContext"]
    cell, usage = image.nested_usage_cell(pins["usage"], label="dynamic_sludge_surf_tile")
    reg, pe, md = image.registration, image.pe, image.metadata
    records_va = int(reg["methodSpecs"], 16)
    selected = usage_method_spec(
        usage, pe.bytes_at_va(records_va, reg["methodSpecsCount"] * 12),
        len(md.methods), reg["genericInstsCount"], source=str(image.gameassembly),
        usage_offset=cell, records_offset=records_va,
    )
    for actual_key, pin_key in (("index", "methodSpecIndex"), ("rawHex", "methodSpecRawHex"),
                               ("definition", "methodDefinitionIndex"),
                               ("classInstantiationIndex", "classInstantiationIndex"),
                               ("methodInstantiationIndex", "methodInstantiationIndex")):
        if selected[actual_key] != pins[pin_key]:
            raise DynamicSludgeSurfTileError(
                f"consumer:listAdd:{actual_key}-differs expected={pins[pin_key]} actual={selected[actual_key]}")
    method = md.methods[selected["definition"]]
    if (image.type_name(method.declaring_type) != pins["type"]
            or md.string(method.name_index) != pins["method"]
            or method.parameter_count != 1
            or _consumer_type_name(image, method.return_type) != "void"):
        raise DynamicSludgeSurfTileError("consumer:listAdd:method-identity-or-signature-differs")
    instance = image.instantiations.resolve(selected["classInstantiationIndex"])
    arguments = [runtime_type_name(pe, md, row.type_pointer_va) for row in instance.arguments]
    if arguments != pins["classArguments"] or arguments != ["ulong"]:
        raise DynamicSludgeSurfTileError(
            f"consumer:listAdd:class-arguments expected={pins['classArguments']} actual={arguments[:8]} count={len(arguments)}")
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    table_va = int(reg["genericMethodTable"], 16)
    candidates = generic_method_candidates(
        pe.bytes_at_va(table_va, reg["genericMethodTableCount"] * 16),
        reg["genericMethodTableCount"], reg["methodSpecsCount"], {selected["index"]},
        code["genericMethodPointersCount"], code["invokerPointersCount"],
        source=str(image.gameassembly), offset=table_va,
    )
    targets = [pe.u64_at_va(int(code["genericMethodPointers"], 16) + row["indices"][0] * 8)
               - pe.image_base for row in candidates]
    expected = int(block["windows"][pins["targetWindow"]]["rva"])
    if len(candidates) != 1 or targets != [expected]:
        raise DynamicSludgeSurfTileError(
            f"consumer:listAdd:static-code-candidates expected={[expected]} actual={targets[:8]}")
    return {"methodSpecIndex": selected["index"], "methodDefinitionIndex": selected["definition"],
            "classArguments": arguments, "staticCandidateRva": expected,
            "boundary": "Static List<UInt64>.Add companion/candidate identity; the collector calls a separately checked inline insertion helper."}


def _validate_consumer(image: Any, block: dict[str, Any], layout: dict[str, Any],
                       root: dict[str, Any], primitive: dict[str, Any]) -> dict[str, Any]:
    """Check reviewed control/data witnesses; never infer live execution."""
    methods = block["methods"]
    required_methods = {"collect", "loaded", "tryApply", "apply", "surfaceLoaded",
                        "primitive", "primitiveLength", "groupIndex", "groupNum", "dataIndex"}
    if set(methods) != required_methods:
        raise DynamicSludgeSurfTileError("consumer:method-roster-differs")
    for name, row in methods.items():
        image.validate_method_row([int(row["index"]), row["type"], row["method"], int(row["rva"])],
                                  label="dynamic_sludge_surf_tile.consumer." + name)
        method = image.metadata.methods[int(row["index"])]
        parameters = [_consumer_type_name(image, item.type_index)
                      for item in image.metadata.parameters_for(method)]
        result = _consumer_type_name(image, method.return_type)
        if parameters != row["parameters"] or result != row["returnType"]:
            raise DynamicSludgeSurfTileError(
                f"consumer:{name}:signature expected={row['parameters']}->{row['returnType']} actual={parameters}->{result}")
    if (int(methods["primitive"]["index"]) != int(primitive["accessorMethodIndex"])
            or int(methods["groupIndex"]["index"]) != int(root["groupIndexGetterMethodIndex"])
            or int(methods["groupNum"]["index"]) != int(root["groupNumGetterMethodIndex"])
            or methods["collect"]["parameters"] != [layout["gridType"], layout["recordType"],
                                                    "System.Collections.Generic.List`1<ulong>"]
            or methods["loaded"]["parameters"] != ["System.Collections.Generic.List`1<ulong>"]
            or methods["surfaceLoaded"]["parameters"] != ["ulong"]):
        raise DynamicSludgeSurfTileError("consumer:shared-layout-or-list-binding-differs")
    raw = {name: _checked_consumer_window(image, name, row)
           for name, row in block["windows"].items()}
    for name in set(raw) & set(methods):
        if int(block["windows"][name]["rva"]) != int(methods[name]["rva"]):
            raise DynamicSludgeSurfTileError(f"consumer:{name}:window-method-binding-differs")
    witnesses = block["witnesses"]
    required = {"collectorArguments", "clearOutput", "groupCarrierInputs", "groupOffset",
                "groupCarrierBuffer", "groupCarrierOutput", "carrierPosition", "carrierOutput",
                "groupIndexOutput", "startAndGroup", "negativeGuard", "upperGuard",
                "primitiveArguments", "positiveGuard", "conversion", "iterationSkip", "loopBound",
                "originalSlot", "cloneSlot", "lengthSlot", "originalStride", "cloneStride",
                "cloneAddress", "cloneWidth", "cloneRead", "cloneReturn", "helperWidth",
                "helperRead", "helperReturn", "listStore", "loadedElement", "loadedResult",
                "loadedFalse", "loadedTrue", "applyArguments", "applyList", "applyResult",
                "emptyApply", "trueApplyArguments", "emptyApplyArguments", "registeredListStore",
                "registeredListArguments", "countGuardInitial", "countGuardLoop", "collectExit",
                "loadedIteration", "cloneBuffer", "originalBuffer", "cloneEndian", "helperEndian",
                "cloneEndianSource", "helperEndianSource", "callerInputs", "callerZero"}
    if set(witnesses) != required:
        raise DynamicSludgeSurfTileError("consumer:witness-roster-differs")
    checked = {}
    for name, row in witnesses.items():
        expected = bytes.fromhex(row["hex"])
        if not expected:
            raise DynamicSludgeSurfTileError(f"consumer:{name}:empty-witness")
        actual = _consumer_range(block, raw, row, len(expected), name)
        if actual != expected:
            raise DynamicSludgeSurfTileError(
                f"consumer:{name}:instruction-window-differs expected={expected[:48].hex().upper()} "
                f"actual={actual[:48].hex().upper()} bytes={len(expected)} rva={int(row['rva']):#x}")
        checked[name] = actual
    offset = checked["groupOffset"]
    if len(offset) != 6 or offset[:2] != b"\x81\xc2" or struct.unpack_from("<I", offset, 2)[0] != int(layout["groupOffset"]):
        raise DynamicSludgeSurfTileError("consumer:groupOffset:shared-layout-binding-differs")
    for name in ("originalSlot", "cloneSlot", "lengthSlot"):
        value = checked[name]
        if len(value) != 5 or value[0] != 0xBA or struct.unpack_from("<I", value, 1)[0] != int(primitive["vtableSlot"]):
            raise DynamicSludgeSurfTileError(f"consumer:{name}:primitive-slot-binding-differs")
    for name in ("originalStride", "cloneStride"):
        value = checked[name]
        if len(value) != 3 or value[0] != 0x8D or 1 << (value[2] >> 6) != int(primitive["elementWidth"]):
            raise DynamicSludgeSurfTileError(f"consumer:{name}:primitive-stride-binding-differs")
    for name in ("cloneWidth", "helperWidth"):
        value = checked[name]
        if len(value) != 3 or value[:1] != b"\x83" or value[2] != int(primitive["elementWidth"]):
            raise DynamicSludgeSurfTileError(f"consumer:{name}:primitive-read-width-differs")
    endian_sources = [rip_qword_load_target(checked[name], int(witnesses[name]["rva"]),
                                           source="dynamic_sludge_surf_tile")
                      for name in ("cloneEndianSource", "helperEndianSource")]
    if len(set(endian_sources)) != 1:
        raise DynamicSludgeSurfTileError("consumer:primitive-endian-source-differs")
    if checked["callerInputs"] != bytes.fromhex("458BF84C8BF24C8BE1") or checked["callerZero"] != bytes.fromhex("4533ED"):
        raise DynamicSludgeSurfTileError("consumer:caller:original-input-or-empty-list-zero-differs")
    if checked["conversion"] != bytes.fromhex("488BCE4863D0"):
        raise DynamicSludgeSurfTileError("consumer:conversion:positive-int32-to-uint64-shape-differs")
    condition_heads = {
        "negativeGuard": "85DB", "upperGuard": "3BD8", "positiveGuard": "85C0",
        "countGuardInitial": "85C0", "countGuardLoop": "85C0", "loadedResult": "84C0",
        "applyResult": "84C0", "emptyApply": "44396A18",
    }
    for name, prefix in condition_heads.items():
        if not checked[name].startswith(bytes.fromhex(prefix)):
            raise DynamicSludgeSurfTileError(f"consumer:{name}:value-condition-shape-differs")
    for name in ("listStore", "registeredListStore"):
        store = checked[name][-5:]
        if len(store) != 5 or store[0] & 0xF8 != 0x48 or store[1] != 0x89 or store[3] >> 6 != 3:
            raise DynamicSludgeSurfTileError(f"consumer:{name}:qword-insertion-stride-differs")
    branches = (
        ("negativeGuard", 2, b"\x78", "iterationSkip"),
        ("upperGuard", 2, b"\x7d", "iterationSkip"),
        ("positiveGuard", 2, b"\x7e", "iterationSkip"),
        ("countGuardInitial", 2, b"\x0f\x8e", "collectExit"),
        ("countGuardLoop", 2, b"\x7e", "collectExit"),
        ("loadedResult", 2, b"\x75", "loadedIteration"),
        ("applyResult", 2, b"\x0f\x85", "trueApplyArguments"),
        ("emptyApply", 4, b"\x0f\x84", "emptyApplyArguments"),
        ("loopBound", 18, b"\x7c", "negativeGuard"),
    )
    for name, at, prefix, target in branches:
        _checked_consumer_branch(checked[name][at:], int(witnesses[name]["rva"]) + at,
                                 prefix, int(witnesses[target]["rva"]), name)
    targets = {name: int(row["rva"]) for name, row in block["windows"].items()}
    targets.update({name: int(row["rva"]) for name, row in methods.items()})
    call_targets = {"carrier": "carrier", "numInitial": "groupNum", "groupIndex": "groupIndex",
                    "dataIndex": "dataIndex", "numLoop": "groupNum", "length": "primitiveLength",
                    "indexedClone": "indexerClone", "append": "listAdd", "numNext": "groupNum",
                    "intRead": "readInt", "surfaceLoaded": "surfaceLoaded", "collect": "collect",
                    "loaded": "loaded", "applyTrue": "apply", "applyEmpty": "apply"}
    if ({row["name"]: row["target"] for row in block["calls"]} != call_targets
            or len(block["calls"]) != len(call_targets)):
        raise DynamicSludgeSurfTileError("consumer:call-roster-or-target-binding-differs")
    for row in block["calls"]:
        instruction = _consumer_range(block, raw, row, 5, row["name"])
        if instruction[:1] != b"\xe8":
            raise DynamicSludgeSurfTileError(f"consumer:{row['name']}:call-shape-differs")
        actual = relative_branch_target(instruction, int(row["rva"]), source="dynamic_sludge_surf_tile")
        if actual != targets[row["target"]]:
            raise DynamicSludgeSurfTileError(
                f"consumer:{row['name']}:call-target expected={targets[row['target']]:#x} actual={actual:#x}")
    if ({row["role"]: len(row["calls"]) for row in block["sharedTargets"]}
            != {"tableOffset": 3, "vectorBody": 2, "listResize": 2}
            or len(block["sharedTargets"]) != 3):
        raise DynamicSludgeSurfTileError("consumer:shared-target-roster-differs")
    for group in block["sharedTargets"]:
        actual = [relative_branch_target(_consumer_range(block, raw, row, 5, group["role"]),
                                         int(row["rva"]), source="dynamic_sludge_surf_tile")
                  for row in group["calls"]]
        if len(actual) < 2 or len(set(actual)) != 1:
            raise DynamicSludgeSurfTileError(f"consumer:{group['role']}:shared-targets-differ={actual}")
    add = _validate_list_add_context(image, block)
    return {"status": "validated", "methods": {name: row["type"] + "." + row["method"]
                                               for name, row in methods.items()},
            "retainedInt32Range": {"minimum": 1, "maximum": (1 << 31) - 1},
            "listAddContext": add, "windowCount": len(raw), "witnessCount": len(checked),
            "boundary": block["boundary"]}


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[int, str], dict[str, Any]
]:
    """Authenticate the SurfTileIDs getter and its shared record/vector types."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_sludge_surf_tile", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicSludgeSurfTileError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"]:
        raise DynamicSludgeSurfTileError("installed_native_inputs:mismatched:UnityPlayer.dll missing or hash differs")
    resource, root, main, enum_by_id, resource_provenance, _ = validate_resource_layout(gameassembly, metadata)
    if resource_provenance["nativeInputs"] != inputs:
        raise DynamicSludgeSurfTileError("SurfTileIDs and resource contracts select different native inputs")
    layout = contract["layout"]
    vectors = {row["name"]: row for row in main["vectors"]}
    if (layout["gridType"] != main["gridType"] or layout["recordVector"] not in vectors
            or layout["targetVector"] not in vectors or layout["groupType"] != root["groupType"]
            or int(layout["groupWidth"]) != int(root["groupWidth"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs shared native types differ")
    record = vectors[layout["recordVector"]]
    target = vectors[layout["targetVector"]]
    name_to_id = {name: number for number, name in enum_by_id.items()}
    if (record["elementType"] != layout["recordType"]
            or int(record["fieldIndex"]) != int(layout["recordFieldIndex"])
            or int(record["elementWidth"]) != int(layout["recordWidth"])
            or target["elementType"] != "System.Int32"
            or layout["targetDataType"] not in name_to_id
            or int(root["visibleDesc"]["dataTypeValue"]) != name_to_id[layout["targetDataType"]]
            or int(target["fieldIndex"]) != int(root["visibleDesc"]["vectorFieldIndex"])
            or int(layout["groupOffset"]) < 0
            or int(layout["groupOffset"]) + int(layout["groupWidth"]) > int(layout["recordWidth"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs record or primitive-vector binding differs")
    getter = contract["getter"]
    if (getter["type"] != layout["recordType"] or getter["method"] != "get_" + layout["groupField"]
            or getter["parameters"] or getter["returnType"] != layout["groupType"]):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter declaration differs")
    image = open_native_image(gameassembly, metadata)
    image.validate_method_row(
        [int(getter["index"]), getter["type"], getter["method"], int(getter["rva"])],
        label="dynamic_sludge_surf_tile",
    )
    method = image.metadata.methods[int(getter["index"])]
    actual_parameters = [image.metadata.metadata_type_name(row.type_index)
                         for row in image.metadata.parameters_for(method)]
    if (actual_parameters != getter["parameters"]
            or image.metadata.metadata_type_name(method.return_type) != getter["returnType"]):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter signature differs")
    length = int(getter["windowLength"])
    if not 0 < length <= 4096:
        raise DynamicSludgeSurfTileError("SurfTileIDs getter window length invalid")
    body = image.pe.bytes_at_va(image.pe.image_base + int(getter["rva"]), length)
    if hashlib.sha256(body).hexdigest().upper() != getter["windowSha256"]:
        raise DynamicSludgeSurfTileError("SurfTileIDs getter code window differs")
    instruction = bytes.fromhex(getter["offsetInstructionHex"])
    if (int(getter["offsetInstructionRva"]) < int(getter["rva"])
            or int(getter["offsetInstructionRva"]) + len(instruction) > int(getter["rva"]) + length
            or image.pe.bytes_at_va(image.pe.image_base + int(getter["offsetInstructionRva"]),
                                    len(instruction)) != instruction
            or instruction[:2] != b"\x81\xc2"
            or struct.unpack_from("<I", instruction, 2)[0] != int(layout["groupOffset"])):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter DataGroup offset differs")
    carrier_offset = int(getter["carrierCallOffset"])
    if not 0 <= carrier_offset <= len(body) - 5 or body[carrier_offset] != 0xE8:
        raise DynamicSludgeSurfTileError("SurfTileIDs getter carrier call outside checked body or shape differs")
    carrier_target = relative_branch_target(body[carrier_offset:carrier_offset + 5],
                                           int(getter["rva"]) + carrier_offset,
                                           source="dynamic_sludge_surf_tile")
    if carrier_target != int(contract["consumer"]["windows"]["carrier"]["rva"]):
        raise DynamicSludgeSurfTileError("SurfTileIDs getter and collector carrier targets differ")
    try:
        consumer = _validate_consumer(image, contract["consumer"], layout, root, target)
    except ValueError as error:
        raise DynamicSludgeSurfTileError(
            f"{error}; source={Path(gameassembly)}; metadata={Path(metadata)}; contract={CONTRACT}") from error
    provenance = {
        "contractSha256": digest,
        "consumerEvidence": consumer,
        "evidenceBoundary": contract["evidenceBoundary"],
        "resourceContractSha256": resource_provenance["contractSha256"],
        "rootContractSha256": resource_provenance["rootContractSha256"],
        "nativeInputs": inputs,
    }
    return layout, resource, root, main, enum_by_id, provenance


def _checked_ownership(spans: list[tuple[int, int, str]], count: int, label: str) -> tuple[int, int]:
    """Return visible and SurfTileIDs counts, rejecting any double ownership."""
    cursor = 0
    visible = surf = 0
    for start, end, owner in sorted(spans):
        if not 0 <= start < end <= count:
            raise DynamicSludgeSurfTileError(f"{label}: invalid {owner} PrimitiveIntList span {start}:{end}/{count}")
        if start < cursor:
            raise DynamicSludgeSurfTileError(f"{label}: {owner} PrimitiveIntList span overlaps at {start}:{end}")
        cursor = end
        if owner == "SurfTileIDs":
            surf += end - start
        else:
            visible += end - start
    return visible, surf


def audit_current_main(
    layout: dict[str, Any], resource: dict[str, Any], root_layout: dict[str, Any],
    main_layout: dict[str, Any], enum_by_id: dict[int, str], *,
    outer_path: Path, ledger_path: Path, cli_path: Path, input_root: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Check all main files and partition each grid's primitive-int vector."""
    outer, current_files, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes",
    )
    widths = {int(row["fieldIndex"]): int(row["elementWidth"]) for row in main_layout["vectors"]}
    vectors = {row["name"]: row for row in main_layout["vectors"]}
    primitive_field = int(vectors[layout["targetVector"]]["fieldIndex"])
    resource_field = int(resource["resourceGroup"]["gridVectorFieldIndex"])
    root_field = int(root_layout["rootCompFieldIndex"])
    sludge_field = int(layout["recordFieldIndex"])
    root_visible_offset = int(root_layout["rootCompVisibleDescOffset"])
    resource_visible_offset = next(int(row["offset"]) for row in resource["resourceGroup"]["fields"]
                                   if row["name"] == "VisibleDesc")
    visible_offsets = (int(root_layout["visibleDesc"]["visibleStateGroupOffset"]),
                       int(root_layout["visibleDesc"]["visibleAreaGroupOffset"]))
    primitive_type = {name: number for number, name in enum_by_id.items()}[layout["targetDataType"]]
    totals: Counter[str] = Counter()
    surf_samples: list[dict[str, Any]] = []
    seen_paths: set[str] = set()
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen_paths:
            raise DynamicSludgeSurfTileError(f"duplicate current main path: {path}")
        seen_paths.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        if (len(data) != source["declaredBytes"]
                or hashlib.md5(data).hexdigest().upper() != source["fileDataMd5"]):
            raise DynamicSludgeSurfTileError(f"{path}: dump length/MD5 differs from authenticated VFS row")
        parse_dynamic_file("main", data, main_vector_widths=widths)
        root = _root_layout(data)
        grid_body, grid_count, _ = _bounded_vector(data, root, 3, 4)
        totals.update(files=1, grids=grid_count)
        for ordinal in range(grid_count):
            slot = grid_body + ordinal * 4
            table = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
            uid_address = _field_span(data, table, 0, 4)
            if uid_address is None:
                raise DynamicSludgeSurfTileError(f"{path}: grid[{ordinal}] lacks UniqueId")
            uid = struct.unpack_from("<I", data, uid_address)[0]
            primitive_body, primitive_count, _ = _bounded_vector(data, table, primitive_field, 4)
            totals["primitiveInts"] += primitive_count
            spans: list[tuple[int, int, str]] = []
            for field, width, desc_offset, owner in (
                (root_field, int(root_layout["rootCompWidth"]), root_visible_offset, "RootComp visibility"),
                (resource_field, int(resource["resourceGroup"]["width"]),
                 resource_visible_offset, "ResourceGroup visibility"),
            ):
                body, count, _ = _bounded_vector(data, table, field, width)
                for index in range(count):
                    for group_offset in visible_offsets:
                        group = _group(data, body + index * width + desc_offset + group_offset)
                        span = _checked_span(
                            group, label=f"{path}: grid[{ordinal}] {owner}[{index}]",
                            expected_type=primitive_type, expected_grid=uid, target_count=primitive_count,
                        )
                        if span is not None:
                            spans.append((*span, owner))
            sludge_body, sludge_count, _ = _bounded_vector(data, table, sludge_field, int(layout["recordWidth"]))
            totals["sludgeRecords"] += sludge_count
            for index in range(sludge_count):
                group = _group(data, sludge_body + index * int(layout["recordWidth"]) + int(layout["groupOffset"]))
                span = _checked_span(
                    group, label=f"{path}: grid[{ordinal}] SludgeComp[{index}].SurfTileIDs",
                    expected_type=primitive_type, expected_grid=uid, target_count=primitive_count,
                )
                if span is None:
                    totals["invalidSurfTileGroups"] += 1
                    continue
                spans.append((*span, "SurfTileIDs"))
                totals["validSurfTileGroups"] += 1
                for position in range(span[0], span[1]):
                    value = struct.unpack_from("<i", data, primitive_body + position * 4)[0]
                    totals["nonzeroSurfTileIds"] += value != 0
                    if len(surf_samples) < 12:
                        surf_samples.append({"source": path, "gridUniqueId": uid,
                                             "index": position, "value": value})
            visible, surf = _checked_ownership(spans, primitive_count, f"{path}: grid[{ordinal}] UniqueId={uid}")
            totals["visiblePrimitiveInts"] += visible
            totals["surfTileIds"] += surf
            totals["unownedPrimitiveInts"] += primitive_count - visible - surf
            totals["gridsWithSurfTileIds"] += surf > 0
    return {
        "format": "endfield.dynamic-sludge-surf-tile-native-audit.v2",
        "status": "validated",
        "primitiveOwnershipComplete": totals["unownedPrimitiveInts"] == 0,
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {"reportSha256": provenance["outerReportSha256"],
                  "ledgerSha256": provenance["ledgerSha256"],
                  "ledgerFileRowCount": provenance["ledgerFileRowCount"]},
        "corpus": dict(totals),
        "surfTileIdSamples": surf_samples,
        "evidenceBoundary": {
            "direct": "The selected native getter returns SludgeComp.SurfTileIDs as an inline DataGroup at its checked offset.",
            "structuralOnly": "Current authenticated main files have disjoint RootComp visibility, ResourceGroup visibility and SurfTileIDs spans into each grid's PrimitiveIntList. The corpus counts show whether these spans tile each vector.",
            "unresolved": "Live Sludge/grid selection, patch paths and actual navmesh or rendering behavior remain open.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    c = report["corpus"]
    return "\n".join([
        "# DynamicStreaming Sludge SurfTileIDs audit", "",
        f"- Status: {report['status']}; authenticated main files: {c['files']:,}; grids: {c['grids']:,}.",
        f"- Selected SurfTileIDs getter offset: {report['layout']['groupOffset']} bytes in SludgeComp.",
        f"- SludgeComp records: {c['sludgeRecords']:,}; valid SurfTileIDs groups: {c['validSurfTileGroups']:,}; invalid groups: {c.get('invalidSurfTileGroups', 0):,}.",
        f"- PrimitiveIntList entries: {c['primitiveInts']:,}; visible-group entries: {c['visiblePrimitiveInts']:,}; SurfTileIDs entries: {c['surfTileIds']:,}; still unowned: {c['unownedPrimitiveInts']:,}.",
        f"- Stored primitive ownership complete: {str(report['primitiveOwnershipComplete']).lower()}.",
        "- Conditional native consumer: positive bounded primitive IDs feed the UInt64 list and IsSurfaceLoaded result gates the selected navmesh-apply call.",
        "- Stored DataGroup ownership and selected native control flow do not establish active Sludge/grid state or live navigation effects.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        layout, resource, root, main_layout, enum_by_id, native = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_main(
            layout, resource, root, main_layout, enum_by_id,
            outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-sludge-surf-tile-native-audit: {error}", file=sys.stderr)
        return 1
    report.update(native)
    report["layout"] = {"groupField": layout["groupField"], "groupOffset": layout["groupOffset"],
                        "recordVector": layout["recordVector"], "targetVector": layout["targetVector"]}
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"DynamicStreaming SurfTileIDs audit passed: files={report['corpus']['files']} "
          f"SurfTileIDs={report['corpus']['surfTileIds']} "
          f"unowned={report['corpus']['unownedPrimitiveInts']}")
    print(f"JSON: {args.output_json}")
    print(f"Markdown: {args.output_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
