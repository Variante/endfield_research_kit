"""Validate the selected Terrain LAYER record-to-resource copy chain."""

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
from scripts.game_data.terrain.tile_slots_native import validate_terrain_tile_slots
from scripts.repo_paths import REPO_ROOT


SCHEMA = "endfield.terrain-layer-slots-native-contract.v2"
DEFAULT_CONTRACT = CONTRACTS_DIR / "terrain_layer_slots_native.json"
DEFAULT_OUTPUT = REPO_ROOT / "reports/terrain/layer_slots_native.json"


def _integer(value: Any) -> int:
    return int(str(value), 0)


def _window(pe: Any, extents: dict[int, int], row: dict[str, Any], label: str) -> tuple[int, int]:
    start, end = _integer(row["startRva"]), _integer(row["endRva"])
    if end <= start:
        raise ValueError(f"{label}:invalid-window")
    pdata = [(_integer(a), _integer(b)) for a, b in row["pdata"]]
    if not pdata or pdata[0][0] != start or pdata[-1][1] != end:
        raise ValueError(f"{label}:pdata-coverage")
    for index, (a, b) in enumerate(pdata):
        if b <= a or (index and pdata[index - 1][1] != a):
            raise ValueError(f"{label}:pdata-noncontiguous")
        if extents.get(pe.image_base + a) != pe.image_base + b:
            raise ValueError(f"{label}:pdata-extent-differs-at=0x{a:X}")
    data = pe.bytes_at_va(pe.image_base + start, end - start)
    if hashlib.sha256(data).hexdigest().upper() != str(row["sha256"]).upper():
        raise ValueError(f"{label}:sha256-differs")
    return start, end


def _expect(pe: Any, rva: int, expected: bytes, label: str,
            bounds: tuple[int, int] | None = None) -> None:
    if bounds is not None and not bounds[0] <= rva <= bounds[1] - len(expected):
        raise ValueError(f"{label}:outside-window")
    actual = pe.bytes_at_va(pe.image_base + rva, len(expected))
    if actual != expected:
        raise ValueError(f"{label}:expected={expected.hex().upper()},actual={actual.hex().upper()}")


def _call(pe: Any, rva: int, target: int, label: str,
          bounds: tuple[int, int] | None = None) -> None:
    if bounds is not None and not bounds[0] <= rva <= bounds[1] - 5:
        raise ValueError(f"{label}:outside-window")
    raw = pe.bytes_at_va(pe.image_base + rva, 5)
    if raw[0] != 0xE8 or rva + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
        raise ValueError(f"{label}:direct-call-target")


def verify_layer_slot_flow(pe: Any, extents: dict[int, int], contract: dict[str, Any],
                           upstream_paths: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Check the queued layer handles, guarded copies and render-property pairs."""
    windows = {name: _window(pe, extents, row, name)
               for name, row in contract["windows"].items()}
    queue = contract["queue"]
    paths_record = upstream_paths["recordAssembly"]
    if (_integer(paths_record["appendCollectionOffset"]) + 8
            != _integer(queue["queuedStorageOffset"])
            or _integer(paths_record["appendCollectionOffset"]) + 32
            != _integer(queue["queuedCountOffset"])):
        raise ValueError("queue:upstream-layer-collection-layout")
    if _integer(queue["readyStorageOffset"]) + 16 != _integer(queue["readyCountOffset"]):
        raise ValueError("queue:ready-collection-layout")

    callback = windows["layerCallback"]
    forward = windows["layerForward"]
    consumer = windows["layerConsumer"]
    copy_dispatch = windows["copyDispatch"]
    copy_helper = windows["copyHelper"]
    getter = windows["destinationGetter"]
    _call(pe, _integer(queue["dispatchCallRva"]), callback[0], "dispatch:layer-callback")
    _expect(pe, _integer(queue["promotionQueuedCountReadRva"]),
            b"\x4c\x39\xb3" + struct.pack("<i", _integer(queue["queuedCountOffset"])),
            "promotion:queued-count")
    _expect(pe, _integer(queue["promotionQueuedStorageReadRva"]),
            b"\x48\x8b\x43" + bytes((_integer(queue["queuedStorageOffset"]),)),
            "promotion:queued-storage")
    _expect(pe, _integer(queue["promotionQueuedRecordLoadRva"]),
            b"\x48\x8b\x3c\xd0", "promotion:queued-record")
    _expect(pe, _integer(queue["promotionQueuedRecordStageRva"]),
            b"\x48\x89\x7c\x24\x50", "promotion:queued-record-stage")
    _expect(pe, _integer(queue["promotionReadyStorageReadRva"]),
            b"\x48\x8b\x8b" + struct.pack("<i", _integer(queue["readyStorageOffset"])),
            "promotion:ready-storage")
    _expect(pe, _integer(queue["promotionReadyPointerArgumentRva"]),
            b"\x4c\x8d\x44\x24\x50", "promotion:ready-pointer-argument")
    _expect(pe, _integer(queue["promotionReadyCountWriteRva"]),
            b"\x48\x89\xb3" + struct.pack("<i", _integer(queue["readyCountOffset"])),
            "promotion:ready-count")
    _expect(pe, _integer(queue["promotionReadySlotPointerRva"]),
            b"\x48\x8d\x0c\xf1", "promotion:ready-slot-pointer")
    _call(pe, _integer(queue["promotionReadyPointerCopyRva"]),
          _integer(queue["readyPointerCopyTargetRva"]), "promotion:ready-pointer-copy")
    _expect(pe, _integer(queue["callbackReadyCountReadRva"]),
            b"\x48\x39\xab" + struct.pack("<i", _integer(queue["readyCountOffset"])),
            "callback:ready-count", callback)
    _expect(pe, _integer(queue["callbackReadyStorageReadRva"]),
            b"\x48\x8b\x83" + struct.pack("<i", _integer(queue["readyStorageOffset"])),
            "callback:ready-storage", callback)
    _expect(pe, _integer(queue["callbackRecordLoadRva"]),
            b"\x48\x8b\x7c\xc8\xf8", "callback:record", callback)
    _expect(pe, _integer(queue["callbackNumericArgumentRva"]),
            b"\x8b\x17", "callback:numeric-argument", callback)
    _expect(pe, _integer(queue["callbackHandleVectorRva"]),
            b"\x4c\x8d\x44\x24\x20", "callback:handle-vector", callback)
    _call(pe, _integer(queue["callbackConsumerCallRva"]), forward[0],
          "callback:owner-forward", callback)
    _expect(pe, _integer(queue["ownerForwardRva"]),
            b"\x48\x8b\x89" + struct.pack("<i", _integer(queue["ownerPathObjectOffset"])),
            "forward:owner-subobject", forward)
    _call(pe, _integer(queue["ownerConsumerCallRva"]), consumer[0],
          "forward:layer-consumer", forward)
    _expect(pe, _integer(queue["consumerVectorStageRva"]),
            b"\x4c\x89\x44\x24\x30", "consumer:vector-stage", consumer)
    _expect(pe, _integer(queue["consumerOwnerStageRva"]),
            b"\x48\x89\x5c\x24\x38", "consumer:owner-stage", consumer)
    _expect(pe, _integer(queue["consumerCopyVectorRva"]),
            b"\x48\x8d\x4c\x24\x30", "consumer:copy-vector", consumer)
    _call(pe, _integer(queue["consumerCopyCallRva"]), copy_dispatch[0],
          "consumer:copy-dispatch", consumer)
    _expect(pe, _integer(queue["copyDispatchVectorLoadRva"]), b"\x48\x8b\x01",
            "copy-dispatch:vector-load", copy_dispatch)
    getter_spec = contract["windows"]["destinationGetter"]
    _expect(pe, _integer(getter_spec["zeroHandleRva"]), b"\x83\x39\x00",
            "destination-getter:zero-handle", getter)
    _expect(pe, _integer(getter_spec["resourcePointerRva"]), b"\x48\x8b\x42\x10",
            "destination-getter:resource-pointer", getter)
    _expect(pe, _integer(getter_spec["nullResultRva"]), b"\x33\xc0",
            "destination-getter:null-result", getter)
    _call(pe, _integer(queue["copyRoutineCallRva"]),
          _integer(queue["copyRoutineTargetRva"]), "copy-helper:lower-level-routine", copy_helper)
    for row in contract["guards"]:
        _expect(pe, _integer(row["rva"]), bytes.fromhex(row["bytesHex"]),
                f"guard:{row['meaning']}", windows[row["window"]])

    rows = contract["slotFlow"]
    if [row["family"] for row in rows] != ["D", "N", "C"]:
        raise ValueError("slotFlow:expected-D-N-C-order")
    if [row["temporaryOffset"] for row in rows] != [8, 16, 24]:
        raise ValueError("slotFlow:expected-three-adjacent-handles")
    path_offsets = {key: _integer(value) for key, value in
                    paths_record["destinationPointerOffsets"].items()}
    if {row["family"]: row["recordOffset"] for row in rows} != path_offsets:
        raise ValueError("slotFlow:upstream-record-offsets-differ")
    if len({_integer(row["destinationOffset"]) for row in rows}) != 3:
        raise ValueError("slotFlow:destination-reused")
    if [bool(row["conditional"]) for row in rows] != [False, False, True]:
        raise ValueError("slotFlow:conditional-shape")
    for index, row in enumerate(rows):
        family = row["family"]
        record = row["recordOffset"]
        temporary = row["temporaryOffset"]
        _expect(pe, _integer(row["callbackRecordRva"]),
                b"\x48\x8d\x4f" + bytes((record,)),
                f"{family}:record-slot", callback)
        _call(pe, _integer(row["callbackResolveCallRva"]),
              _integer(queue["resolverTargetRva"]), f"{family}:resolver", callback)
        _expect(pe, _integer(row["callbackStoreRva"]),
                b"\x48\x89\x44\x24" + bytes((0x20 + temporary,)),
                f"{family}:temporary-store", callback)
        if not (_integer(row["callbackRecordRva"])
                < _integer(row["callbackResolveCallRva"])
                < _integer(row["callbackStoreRva"])):
            raise ValueError(f"{family}:callback-order")
        if index < 2 and _integer(row["callbackStoreRva"]) >= _integer(rows[index + 1]["callbackResolveCallRva"]):
            raise ValueError(f"{family}:staging-overwritten-before-store")
        load_bytes = bytes.fromhex(row["copyInputLoadBytesHex"])
        if len(load_bytes) != 4 or load_bytes[-1] != temporary:
            raise ValueError(f"{family}:copy-input-offset")
        _expect(pe, _integer(row["copyInputLoadRva"]), load_bytes,
                f"{family}:copy-input", copy_dispatch)
        _expect(pe, _integer(row["destinationRva"]),
                b"\x48\x81\xc1" + struct.pack("<i", _integer(row["destinationOffset"])),
                f"{family}:destination-handle", copy_dispatch)
        _call(pe, _integer(row["getterCallRva"]),
              getter[0],
              f"{family}:destination-getter", copy_dispatch)
        _expect(pe, _integer(row["sourceArgumentRva"]),
                bytes.fromhex(row["sourceArgumentBytesHex"]),
                f"{family}:copy-source-argument", copy_dispatch)
        _call(pe, _integer(row["copyCallRva"]), copy_helper[0],
              f"{family}:copy-helper", copy_dispatch)
        if not (_integer(row["copyInputLoadRva"])
                < _integer(row["destinationRva"])
                < _integer(row["getterCallRva"])
                < _integer(row["sourceArgumentRva"])
                < _integer(row["copyCallRva"])):
            raise ValueError(f"{family}:copy-order")
        if row["conditional"]:
            _expect(pe, _integer(row["availabilityDestinationRva"]),
                    b"\x48\x81\xc1" + struct.pack("<i", _integer(row["destinationOffset"])),
                    f"{family}:availability-destination", copy_dispatch)
            _call(pe, _integer(row["availabilityCallRva"]),
                  _integer(row["availabilityTargetRva"]),
                  f"{family}:availability-check", copy_dispatch)
            if _integer(row["availabilityCallRva"]) >= _integer(row["copyCallRva"]):
                raise ValueError(f"{family}:availability-order")
    binding = contract["propertyBinding"]
    properties = contract["propertyFlow"]
    if [row["family"] for row in properties] != ["D", "N", "C"]:
        raise ValueError("propertyFlow:expected-D-N-C-order")
    if {_integer(row["destinationOffset"]) for row in properties} != {
            _integer(row["destinationOffset"]) for row in rows}:
        raise ValueError("propertyFlow:destination-set-differs")
    slot_destinations = {row["family"]: _integer(row["destinationOffset"]) for row in rows}
    property_ids = [_integer(row["propertyIdOffset"]) for row in properties]
    if len(set(property_ids)) != 3:
        raise ValueError("propertyFlow:property-id-reused")
    if len({row["property"] for row in properties}) != 3:
        raise ValueError("propertyFlow:property-name-reused")
    owner_offset = _integer(binding["ownerPathObjectOffset"])
    if owner_offset != _integer(queue["ownerPathObjectOffset"]):
        raise ValueError("propertyFlow:owner-subobject-differs")
    for row in properties:
        family = row["family"]
        destination = _integer(row["destinationOffset"])
        if destination != slot_destinations[family]:
            raise ValueError(f"{family}:property-destination-differs")
        literal_rva = _integer(row["literalRva"])
        load_rva = _integer(row["literalLoadRva"])
        literal_load = pe.bytes_at_va(pe.image_base + load_rva, 7)
        if (literal_load[:3] != b"\x48\x8d\x15"
                or load_rva + 7 + struct.unpack_from("<i", literal_load, 3)[0] != literal_rva):
            raise ValueError(f"{family}:property-literal-target")
        if pe.c_string_at_va(pe.image_base + literal_rva) != row["property"]:
            raise ValueError(f"{family}:property-literal-text")
        _call(pe, _integer(row["nameLoaderCallRva"]),
              _integer(binding["nameLoaderTargetRva"]), f"{family}:property-name-loader")
        _expect(pe, _integer(row["idResultRva"]), b"\x8b\x08",
                f"{family}:property-id-result")
        _expect(pe, _integer(row["idStoreRva"]),
                b"\x41\x89\x8e" + struct.pack("<i", _integer(row["propertyIdOffset"])),
                f"{family}:property-id-store")
        if not (load_rva < _integer(row["nameLoaderCallRva"])
                < _integer(row["idResultRva"]) < _integer(row["idStoreRva"])):
            raise ValueError(f"{family}:property-id-order")
        _expect(pe, _integer(row["bindingOwnerLoadRva"]),
                b"\x48\x8b\x8b" + struct.pack("<i", owner_offset),
                f"{family}:binding-owner-subobject")
        _expect(pe, _integer(row["bindingDestinationRva"]),
                b"\x48\x81\xc1" + struct.pack("<i", destination),
                f"{family}:binding-destination")
        _call(pe, _integer(row["bindingGetterCallRva"]), getter[0],
              f"{family}:binding-resource-getter")
        _expect(pe, _integer(row["bindingPropertyIdLoadRva"]),
                b"\x8b\x93" + struct.pack("<i", _integer(row["propertyIdOffset"])),
                f"{family}:binding-property-id")
        _expect(pe, _integer(row["bindingResourceStageRva"]), b"\x4c\x8b\xc0",
                f"{family}:binding-resource-argument")
        _expect(pe, _integer(row["bindingContextStageRva"]), b"\x48\x8b\xcf",
                f"{family}:binding-context-argument")
        _call(pe, _integer(row["bindingCallRva"]),
              _integer(binding["propertySinkTargetRva"]), f"{family}:property-sink")
        if not (_integer(row["bindingOwnerLoadRva"])
                < _integer(row["bindingDestinationRva"])
                < _integer(row["bindingGetterCallRva"])
                < _integer(row["bindingPropertyIdLoadRva"])
                < _integer(row["bindingResourceStageRva"])
                < _integer(row["bindingContextStageRva"])
                < _integer(row["bindingCallRva"])):
            raise ValueError(f"{family}:binding-order")
    third = properties[2]
    _expect(pe, _integer(binding["thirdResourceGuardOwnerLoadRva"]),
            b"\x48\x8b\x8b" + struct.pack("<i", owner_offset),
            "C:binding-guard-owner")
    _expect(pe, _integer(binding["thirdResourceGuardDestinationRva"]),
            b"\x48\x81\xc1" + struct.pack("<i", _integer(third["destinationOffset"])),
            "C:binding-guard-destination")
    _call(pe, _integer(binding["thirdResourceGuardGetterCallRva"]), getter[0],
          "C:binding-guard-getter")
    _expect(pe, _integer(binding["thirdResourceGuardTestRva"]), b"\x48\x85\xc0",
            "C:binding-guard-null-test")
    branch = _integer(binding["thirdResourceGuardBranchRva"])
    branch_bytes = pe.bytes_at_va(pe.image_base + branch, 2)
    if (branch_bytes[0] != 0x74 or branch + 2 + struct.unpack_from("<b", branch_bytes, 1)[0]
            != _integer(binding["thirdResourceGuardSkipRva"])):
        raise ValueError("C:binding-guard-skip-target")
    if not (branch < _integer(third["bindingCallRva"])
            < _integer(binding["thirdResourceGuardSkipRva"])):
        raise ValueError("C:binding-guard-order")
    slot_output = [{"family": row["family"], "recordOffset": row["recordOffset"],
                    "temporaryOffset": row["temporaryOffset"],
                    "destinationOffset": row["destinationOffset"],
                    "conditional": row["conditional"]} for row in rows]
    property_output = [{"family": row["family"], "property": row["property"],
                        "destinationOffset": row["destinationOffset"],
                        "propertyIdOffset": row["propertyIdOffset"],
                        "conditional": row["family"] == "C"} for row in properties]
    return slot_output, property_output


def validate_terrain_layer_slots(*, game_root: Path,
                                 contract_path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    """Authenticate the selected native build and withhold rows on any mismatch."""
    try:
        contract, _ = read_reviewed_contract(
            contract_path, schema=SCHEMA, status="validated", label="terrain-layer-slots"
        )
        expected = contract["nativeInputs"]
        if not isinstance(expected, dict):
            raise ValueError("nativeInputs:not-object")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as error:
        return {"status": "validation_failed", "slotFlow": [], "propertyFlow": [],
                "reason": f"contract={error}"}
    root = Path(game_root)
    gate = check_installed_native_inputs(
        str(expected.get("gameAssemblySha256") or ""),
        str(expected.get("metadataSha256") or ""),
        gameassembly=root.parent / "GameAssembly.dll",
        metadata=root / "il2cpp_data/Metadata/global-metadata.dat",
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        return {"status": gate.status, "slotFlow": [], "propertyFlow": [], "reason": gate.detail}
    unity_player = root.parent / "UnityPlayer.dll"
    try:
        actual_unity_hash = sha256_file_upper(unity_player)
    except OSError as error:
        return {"status": "missing", "slotFlow": [], "propertyFlow": [],
                "reason": f"UnityPlayer.dll={error}"}
    if actual_unity_hash != str(expected.get("unityPlayerSha256") or "").upper():
        return {"status": "mismatched", "slotFlow": [], "propertyFlow": [],
                "reason": "UnityPlayer.dll hash differs"}
    paths = validate_terrain_layer_paths(game_root=root)
    if paths["status"] != "validated" or paths.get("nativeInputs") != expected:
        return {"status": "validation_failed", "slotFlow": [], "propertyFlow": [],
                "reason": f"upstream-layer-paths={paths['status']}:{paths.get('reason', '')}"}
    tile_slots = validate_terrain_tile_slots(game_root=root)
    if tile_slots["status"] != "validated" or tile_slots.get("nativeInputs") != expected:
        return {"status": "validation_failed", "slotFlow": [], "propertyFlow": [],
                "reason": f"upstream-tile-dispatch={tile_slots['status']}:{tile_slots.get('reason', '')}"}
    try:
        mapper = load_native_mapper(NATIVE_MAPPER_PATH)
        pe = mapper.PeImage(unity_player)
        flows, property_flows = verify_layer_slot_flow(
            pe, mapper.pdata_function_extents(pe), contract, paths
        )
    except (OSError, ValueError, KeyError, TypeError, IndexError, struct.error) as error:
        return {"status": "validation_failed", "slotFlow": [], "propertyFlow": [],
                "reason": str(error)}
    return {"status": "validated", "slotFlow": flows, "propertyFlow": property_flows,
            "nativeInputs": expected,
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
    result = validate_terrain_layer_slots(game_root=args.game_root, contract_path=args.contract)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"Terrain layer slot flow: {result['status']}; {len(result['slotFlow'])} checked paths, "
          f"{len(result['propertyFlow'])} render properties")
    if result["status"] != "validated":
        print(result.get("reason", ""))
    return 0 if result["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
