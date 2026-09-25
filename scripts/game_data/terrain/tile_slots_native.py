"""Validate the selected native Terrain tile-result-to-copy chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NATIVE_MAPPER_PATH, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import load_native_mapper
from scripts.game_data.terrain.layer_paths_native import validate_terrain_layer_paths
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-tile-slots-native-contract.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_tile_slots_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/tile_slots_native.json"


def _integer(value: Any) -> int:
    return int(str(value), 0)


def _window(pe: Any, extents: dict[int, int], row: dict[str, Any], label: str) -> tuple[int, int]:
    start, end = _integer(row["startRva"]), _integer(row["endRva"])
    if end <= start or (row.get("pdata", True)
                        and extents.get(pe.image_base + start) != pe.image_base + end):
        raise ValueError(f"{label}:pdata-extent-differs")
    data = pe.bytes_at_va(pe.image_base + start, end - start)
    if hashlib.sha256(data).hexdigest().upper() != str(row["sha256"]).upper():
        raise ValueError(f"{label}:sha256-differs")
    return start, end


def _expect(pe: Any, rva: int, expected: bytes, label: str, bounds: tuple[int, int]) -> None:
    start, end = bounds
    if not start <= rva <= end - len(expected):
        raise ValueError(f"{label}:outside-window")
    actual = pe.bytes_at_va(pe.image_base + rva, len(expected))
    if actual != expected:
        raise ValueError(f"{label}:expected={expected.hex().upper()},actual={actual.hex().upper()}")


def _direct_call(pe: Any, rva: int, target: int, label: str, bounds: tuple[int, int]) -> None:
    start, end = bounds
    if not start <= rva <= end - 5:
        raise ValueError(f"{label}:outside-window")
    raw = pe.bytes_at_va(pe.image_base + rva, 5)
    actual = rva + 5 + struct.unpack_from("<i", raw, 1)[0]
    if raw[0] != 0xE8 or actual != target:
        raise ValueError(f"{label}:direct-call-target")


def _literal_load(
    pe: Any, rva: int, literal_rva: int, literal: str, label: str,
    bounds: tuple[int, int],
) -> None:
    start, end = bounds
    if not start <= rva <= end - 7:
        raise ValueError(f"{label}:outside-window")
    raw = pe.bytes_at_va(pe.image_base + rva, 7)
    target = rva + 7 + struct.unpack_from("<i", raw, 3)[0]
    if raw[:3] != b"\x48\x8d\x15" or target != literal_rva:
        raise ValueError(f"{label}:literal-target")
    actual = pe.c_string_at_va(pe.image_base + literal_rva)
    if actual != literal:
        raise ValueError(f"{label}:literal:expected={literal!r},actual={actual!r}")


def verify_tile_slot_flow(pe: Any, contract: dict[str, Any], extents: dict[int, int]) -> list[dict[str, Any]]:
    """Check six queued record slots through handle staging and conditional copy calls."""
    windows = {
        name: _window(pe, extents, row, name)
        for name, row in contract["windows"].items()
    }
    dispatch = contract["dispatch"]
    consumer = contract["tileConsumer"]
    d, p, q, t = (windows[name] for name in
                  ("dispatch", "queuePromotion", "queueCallback", "tileConsumer"))
    copy_entry, copy_body = windows["copyEntry"], windows["copyBody"]
    if copy_entry[1] != copy_body[0] or copy_body[1] != windows["copyExit"][0]:
        raise ValueError("copy:noncontiguous-windows")
    binding_windows = [windows[name] for name in
                       ("bindingEntry", "bindingPrelude", "bindingMiddle", "bindingTail")]
    if any(left[1] != right[0] for left, right in zip(binding_windows, binding_windows[1:])):
        raise ValueError("binding:noncontiguous-windows")
    owner_offset = _integer(dispatch["ownerPathObjectOffset"])
    stage_offset = _integer(dispatch["ownerPointerStageStackOffset"])
    vector_offset = _integer(dispatch["callbackVectorStackOffset"])
    if not 0 <= stage_offset <= 0x7F or not 0 <= vector_offset <= 0x7F:
        raise ValueError("dispatch:stack-offset-range")
    queued_count = _integer(dispatch["queuedCountOffset"])
    queued_storage = _integer(dispatch["queuedStorageOffset"])
    ready_count = _integer(dispatch["readyCountOffset"])
    ready_storage = _integer(dispatch["readyStorageOffset"])
    _direct_call(pe, _integer(dispatch["promotionCallRva"]), p[0], "dispatch:queue-promotion", d)
    _expect(pe, _integer(dispatch["queuedCountReadRva"]),
            b"\x4c\x39\xb3" + struct.pack("<i", queued_count), "promotion:queued-count", p)
    _expect(pe, _integer(dispatch["queuedStorageReadRva"]),
            b"\x48\x8b\x83" + struct.pack("<i", queued_storage),
            "promotion:queued-storage", p)
    _expect(pe, _integer(dispatch["queuedRecordLoadRva"]),
            b"\x48\x8b\x3c\xd0", "promotion:record-pointer", p)
    _expect(pe, _integer(dispatch["queuedRecordStageRva"]),
            b"\x48\x89\x7c\x24" + bytes((stage_offset,)), "promotion:stage-record", p)
    _expect(pe, _integer(dispatch["readyStorageReadRva"]),
            b"\x48\x8b\x8b" + struct.pack("<i", ready_storage),
            "promotion:ready-storage", p)
    _expect(pe, _integer(dispatch["readyCountWriteRva"]),
            b"\x48\x89\xb3" + struct.pack("<i", ready_count),
            "promotion:ready-count", p)
    _expect(pe, _integer(dispatch["readyPointerArgumentRva"]),
            b"\x4c\x8d\x44\x24" + bytes((stage_offset,)),
            "promotion:ready-pointer-argument", p)
    _direct_call(pe, _integer(dispatch["readyPointerCopyCallRva"]),
                 windows["queuePointerCopy"][0], "promotion:ready-pointer-copy", p)
    _expect(pe, windows["queuePointerCopy"][0],
            bytes.fromhex(dispatch["readyPointerCopyBytesHex"]),
            "promotion:pointer-copy-body", windows["queuePointerCopy"])
    _expect(pe, _integer(dispatch["ownerPathObjectLoadRva"]),
            b"\x48\x8b\x8e" + struct.pack("<i", owner_offset), "dispatch:path-object", d)
    _expect(pe, _integer(dispatch["ownerPointerStageRva"]),
            b"\x48\x89\x74\x24" + bytes((stage_offset,)), "dispatch:owner-pointer", d)
    _direct_call(pe, _integer(dispatch["queueCallbackCallRva"]), q[0], "dispatch:queue-callback", d)
    _expect(pe, _integer(dispatch["callbackReadyCountReadRva"]),
            b"\x4c\x39\xb3" + struct.pack("<i", ready_count),
            "queue:ready-count", q)
    _expect(pe, _integer(dispatch["callbackReadyStorageReadRva"]),
            b"\x48\x8b\x83" + struct.pack("<i", ready_storage),
            "queue:ready-storage", q)
    _expect(pe, _integer(dispatch["callbackRecordLoadRva"]),
            bytes.fromhex(dispatch["callbackRecordLoadBytesHex"]), "queue:record-load", q)
    _expect(pe, _integer(dispatch["callbackPackedIdLoadRva"]),
            b"\x8b\x17", "queue:packed-id", q)
    _expect(pe, _integer(dispatch["callbackHandleVectorRva"]),
            b"\x4c\x8d\x44\x24" + bytes((vector_offset,)), "queue:handle-vector", q)
    _expect(pe, _integer(dispatch["callbackOwnerLoadRva"]),
            b"\x48\x8b\x0e", "queue:owner-load", q)
    _direct_call(pe, _integer(dispatch["callbackConsumerCallRva"]),
                 _integer(dispatch["tileConsumerTargetRva"]), "queue:tile-consumer", q)
    _expect(pe, _integer(consumer["ownerDataGuardRva"]),
            b"\x48\x83\x79" + bytes((_integer(consumer["ownerDataOffset"]), 0)),
            "consumer:owner-data-guard", t)
    _direct_call(pe, _integer(consumer["tileAvailabilityCallRva"]),
                 _integer(consumer["tileAvailabilityTargetRva"]), "consumer:availability", t)
    _expect(pe, _integer(consumer["copyPreconditionRva"]),
            b"\x48\x85\xf6", "copy:source-null-guard", copy_entry)
    _direct_call(pe, _integer(consumer["copyCallRva"]),
                 _integer(consumer["copyPrimitiveTargetRva"]), "copy:primitive", copy_body)
    binding = contract["propertyBinding"]
    initializer = windows["ownerInitializer"]
    render_binding = windows["propertyBinding"]
    owner_path_offset = _integer(binding["ownerPathObjectOffset"])
    if owner_path_offset != owner_offset:
        raise ValueError("binding:owner-path-object-offset")
    _expect(pe, _integer(binding["ownerPathObjectStoreRva"]),
            b"\x49\x89\x86" + struct.pack("<i", owner_path_offset),
            "binding:owner-path-object-store", initializer)
    _expect(pe, _integer(binding["bindingEntryOwnerCaptureRva"]),
            b"\x48\x8b\xf9", "binding:owner-capture", windows["bindingEntry"])
    _expect(pe, _integer(binding["bindingEntryPathObjectReadRva"]),
            b"\x48\x8b\x8f" + struct.pack("<i", owner_path_offset),
            "binding:owner-path-object-read", windows["bindingPrelude"])
    _expect(pe, _integer(binding["bindingTailOwnerArgumentRva"]),
            b"\x48\x8b\xcf", "binding:owner-argument", windows["bindingTail"])
    _direct_call(pe, _integer(binding["bindingTailCallRva"]), render_binding[0],
                 "binding:property-function", windows["bindingTail"])
    _direct_call(pe, _integer(binding["nameLoaderBodyCallRva"]),
                 _integer(binding["nameLoaderBodyTargetRva"]),
                 "binding:name-loader-body", windows["propertyNameLoader"])
    sink = windows["propertySink"]
    _expect(pe, _integer(binding["sinkResourceCaptureRva"]),
            b"\x49\x8b\xe8", "binding:sink-resource-capture", sink)
    _expect(pe, _integer(binding["sinkPropertyIdCaptureRva"]),
            b"\x8b\xda", "binding:sink-property-id-capture", sink)
    _expect(pe, _integer(binding["sinkResourceForwardRva"]),
            b"\x4c\x8b\xc5", "binding:sink-resource-forward", sink)
    _expect(pe, _integer(binding["sinkPropertyIdForwardRva"]),
            b"\x8b\xd3", "binding:sink-property-id-forward", sink)
    _direct_call(pe, _integer(binding["sinkApplyCallRva"]),
                 _integer(binding["sinkApplyTargetRva"]), "binding:sink-apply", sink)

    rows = contract["slotFlow"]
    families = {"Terrain_H", "Terrain_N", "Terrain_T", "Terrain_A", "Terrain_S", "Terrain_C"}
    if (not isinstance(rows, list) or len(rows) != 6
            or {row.get("family") for row in rows if isinstance(row, dict)} != families):
        raise ValueError("slotFlow:expected-six-tile-families")
    if [row["recordOffset"] for row in rows] != [8, 16, 24, 32, 40, 48]:
        raise ValueError("slotFlow:record-layout")
    if {row["temporaryOffset"] for row in rows} != {8, 16, 24, 32, 40, 48}:
        raise ValueError("slotFlow:temporary-layout")
    if len({_integer(row["destinationOffset"]) for row in rows}) != 6:
        raise ValueError("slotFlow:destination-uniqueness")
    if len({_integer(row["propertyIdOffset"]) for row in rows}) != 6:
        raise ValueError("slotFlow:property-id-uniqueness")
    result = []
    for row in rows:
        family = row["family"]
        record = row["recordOffset"]
        temporary = row["temporaryOffset"]
        destination = _integer(row["destinationOffset"])
        _expect(pe, _integer(row["resolveArgumentRva"]),
                b"\x48\x8d\x4f" + bytes((record,)), f"{family}:record-slot", q)
        _direct_call(pe, _integer(row["resolveCallRva"]),
                     _integer(dispatch["resolveHandleTargetRva"]), f"{family}:resolve", q)
        _expect(pe, _integer(row["temporaryStoreRva"]),
                b"\x48\x89\x44\x24" + bytes((vector_offset + temporary,)),
                f"{family}:temporary-store", q)
        _expect(pe, _integer(row["consumerLoadRva"]),
                b"\x49\x8b\x4c\x24" + bytes((temporary,)), f"{family}:consumer-load", t)
        _expect(pe, _integer(row["destinationRva"]),
                b"\x48\x8d\x96" + struct.pack("<i", destination),
                f"{family}:owner-destination", t)
        _direct_call(pe, _integer(row["copyCallRva"]),
                     _integer(dispatch["copyTargetRva"]), f"{family}:copy-helper", t)
        property_id = _integer(row["propertyIdOffset"])
        if not (_integer(row["propertyLiteralLoadRva"])
                < _integer(row["nameLoaderCallRva"])
                < _integer(row["propertyIdStoreRva"])):
            raise ValueError(f"{family}:property-id-flow-order")
        _literal_load(pe, _integer(row["propertyLiteralLoadRva"]),
                      _integer(row["propertyLiteralRva"]), row["property"],
                      f"{family}:property-name", initializer)
        _direct_call(pe, _integer(row["nameLoaderCallRva"]),
                     _integer(binding["nameLoaderCallTargetRva"]),
                     f"{family}:property-id-loader", initializer)
        store = _integer(row["propertyIdStoreRva"])
        _expect(pe, store - 2, b"\x8b\x08", f"{family}:property-id-result", initializer)
        _expect(pe, store, b"\x41\x89\x8e" + struct.pack("<i", property_id),
                f"{family}:property-id-store", initializer)
        _expect(pe, _integer(row["bindingDestinationRva"]),
                b"\x48\x8d\x8b" + struct.pack("<i", destination),
                f"{family}:binding-destination", render_binding)
        _direct_call(pe, _integer(row["bindingResourceGetterCallRva"]),
                     _integer(binding["destinationResourceGetterTargetRva"]),
                     f"{family}:binding-resource-getter", render_binding)
        _expect(pe, _integer(row["bindingPropertyIdLoadRva"]),
                b"\x8b\x93" + struct.pack("<i", property_id),
                f"{family}:binding-property-id", render_binding)
        _expect(pe, _integer(row["bindingResourceArgumentRva"]),
                b"\x4c\x8b\xc0", f"{family}:binding-resource-argument", render_binding)
        _expect(pe, _integer(row["bindingContextArgumentRva"]),
                b"\x48\x8b\xcf", f"{family}:binding-context-argument", render_binding)
        if not (_integer(row["bindingDestinationRva"])
                < _integer(row["bindingResourceGetterCallRva"])
                < _integer(row["bindingPropertyIdLoadRva"])
                < _integer(row["bindingResourceArgumentRva"])
                < _integer(row["bindingContextArgumentRva"])
                < _integer(row["bindingCallRva"])):
            raise ValueError(f"{family}:binding-order")
        _direct_call(pe, _integer(row["bindingCallRva"]),
                     _integer(binding["propertySinkTargetRva"]),
                     f"{family}:property-binding", render_binding)
        result.append({"family": family, "recordOffset": record,
                       "temporaryOffset": temporary, "destinationOffset": row["destinationOffset"],
                       "property": row["property"]})
    return result


def validate_terrain_tile_slots(*, game_root: Path, contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Fail closed when the selected build or upstream path record proof differs."""
    try:
        contract, _ = read_reviewed_contract(
            contract_path, schema=SCHEMA, status="validated", label="terrain-tile-slots"
        )
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict):
            raise ValueError("nativeInputs:not-object")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "validation_failed", "slotFlow": [], "reason": f"contract={error}"}
    root = Path(game_root)
    gate = check_installed_native_inputs(
        str(expected.get("gameAssemblySha256") or ""),
        str(expected.get("metadataSha256") or ""),
        gameassembly=root.parent / "GameAssembly.dll",
        metadata=root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "slotFlow": [], "reason": gate.detail}
    unity_player = root.parent / "UnityPlayer.dll"
    try:
        actual_unity_hash = sha256_file_upper(unity_player)
    except OSError as error:
        return {"status": "missing", "slotFlow": [], "reason": f"UnityPlayer.dll={error}"}
    if actual_unity_hash != str(expected.get("unityPlayerSha256") or "").upper():
        return {"status": "mismatched", "slotFlow": [], "reason": "UnityPlayer.dll hash differs"}
    upstream = validate_terrain_layer_paths(game_root=root)
    if upstream["status"] != "validated" or upstream.get("nativeInputs") != expected:
        return {"status": "validation_failed", "slotFlow": [],
                "reason": f"upstream-layer-paths={upstream['status']}:{upstream.get('reason', '')}"}
    source_offsets = {row["family"]: _integer(row["destinationPointerOffset"])
                      for row in upstream["terrainPaths"]}
    try:
        if source_offsets != {row["family"]: row["recordOffset"]
                              for row in contract["slotFlow"]}:
            raise ValueError("upstream-layer-paths:record-slot-mismatch")
        mapper = load_native_mapper(NATIVE_MAPPER_PATH)
        pe = mapper.PeImage(unity_player)
        flows = verify_tile_slot_flow(pe, contract, mapper.pdata_function_extents(pe))
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as error:
        return {"status": "validation_failed", "slotFlow": [], "reason": str(error)}
    return {"status": "validated", "slotFlow": flows, "nativeInputs": expected,
            "evidenceBoundary": contract["evidenceBoundary"]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-root", type=Path, required=True,
                        help="Explicit selected Endfield_Data root")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    if (REPO_ROOT / "reports").resolve() not in output.parents:
        parser.error("--output must be under reports/")
    result = validate_terrain_tile_slots(game_root=args.game_root, contract_path=args.contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Terrain tile slot flow: {result['status']}; {len(result['slotFlow'])} checked paths")
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
