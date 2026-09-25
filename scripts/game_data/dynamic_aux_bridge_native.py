"""Authenticate the selected DynamicStreaming auxiliary-path native handoff.

The maintained source gate in ``dynamic_aux_pair_corpus`` separately rechecks
every paired dump against the VFS ledger's length and FileDataMd5. This module
checks the managed-to-UnityPlayer route, separate native resource requests,
the consumer's paired FlatBuffer root-slot reads, and its descriptor-major
copy builder. It does not assign semantic names to root fields or descriptors.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import relative_branch_target
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_aux_bridge_native.json"
SCHEMA = "endfield.dynamic-aux-bridge-native-contract.v4"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_aux_bridge_native_latest.json"


class DynamicAuxBridgeError(ValueError):
    """The selected build or an auxiliary-path handoff differs."""


def _call_target(pe: Any, rva: int, *, label: str) -> int:
    raw = pe.bytes_at_va(pe.image_base + rva, 5)
    if raw[0] != 0xE8:
        raise DynamicAuxBridgeError(f"{label}: expected direct call at {rva:#x}")
    return relative_branch_target(raw, pe.image_base + rva, source=label)


def _validate_descriptor_builder(pe: Any, contract: dict[str, Any], *, consumer_window: dict[str, Any]) -> dict[str, Any]:
    """Check the paired ID/descriptor/blob handoff and byte-copy loop."""
    windows = {row["role"]: row for row in contract["unityDescriptorBuilderCodeWindows"]}
    if set(windows) != {"descriptorBuilder", "byteCopy"} or len(contract["unityDescriptorBuilderCodeWindows"]) != 2:
        raise DynamicAuxBridgeError("selected descriptor-builder window set differs")
    for role, row in windows.items():
        start, end = int(row["startRva"]), int(row["endRva"])
        if not 0 < end - start <= 0x800:
            raise DynamicAuxBridgeError(f"selected descriptor-builder window bound differs: {role}")
        raw = pe.bytes_at_va(pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise DynamicAuxBridgeError(f"selected descriptor-builder code window differs: {role}")
    owner = {"consumerToDescriptorBuilder": consumer_window,
             "descriptorBuilderToByteCopy": windows["descriptorBuilder"]}
    target = {"consumerToDescriptorBuilder": "descriptorBuilder",
              "descriptorBuilderToByteCopy": "byteCopy"}
    calls = contract["unityDescriptorBuilderCalls"]
    if set(owner) != {row["role"] for row in calls} or len(calls) != 2:
        raise DynamicAuxBridgeError("selected descriptor-builder call set differs")
    for row in calls:
        role, site = row["role"], int(row["siteRva"])
        source_window = owner[role]
        expected = int(windows[target[role]]["startRva"])
        if (not int(source_window["startRva"]) <= site <= int(source_window["endRva"]) - 5
                or int(row["targetRva"]) != expected
                or _call_target(pe, site, label=role) != pe.image_base + expected):
            raise DynamicAuxBridgeError(f"selected descriptor-builder call differs: {role}")
    checks = contract["unityDescriptorBuilderInstructionChecks"]
    check_roles = {"pairedVectorHandoff", "descriptorBuilderArguments",
                   "descriptorSignedStrideAndLength", "descriptorIdAndCopy"}
    if {row["role"] for row in checks} != check_roles or len(checks) != len(check_roles):
        raise DynamicAuxBridgeError("selected descriptor-builder instruction set differs")
    for row in checks:
        role, site, raw = row["role"], int(row["rva"]), bytes.fromhex(row["hex"])
        window = consumer_window if role == "pairedVectorHandoff" else windows["descriptorBuilder"]
        if (not raw or not int(window["startRva"]) <= site
                or site + len(raw) > int(window["endRva"])
                or pe.bytes_at_va(pe.image_base + site, len(raw)) != raw):
            raise DynamicAuxBridgeError(f"selected descriptor-builder instruction differs: {role}")
    return {"windows": list(windows), "calls": [row["role"] for row in calls],
            "instructionChecks": [row["role"] for row in checks]}


def _validate_unity_worker(pe: Any, contract: dict[str, Any]) -> dict[str, Any]:
    """Check indexed path lookup, ready buffers, and both root-slot reads."""
    windows = {row["role"]: row for row in contract["unityWorkerCodeWindows"]}
    if set(windows) != {
        "initRequest", "streamingRequest", "indexedPathLookup", "resourceLookup",
        "streamConstruction", "readyStatus", "readyDataPointer", "rootResolution",
        "rootConsumer",
    }:
        raise DynamicAuxBridgeError("selected Unity worker window set differs")
    for role, row in windows.items():
        start, end = int(row["startRva"]), int(row["endRva"])
        if not 0 < end - start <= 0x800:
            raise DynamicAuxBridgeError(f"selected Unity worker window bound differs: {role}")
        raw = pe.bytes_at_va(pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise DynamicAuxBridgeError(f"selected Unity worker code window differs: {role}")

    calls = contract["unityWorkerDirectCalls"]
    if {row["role"] for row in calls} != {
        "initPathIndex", "initResourceLookup", "initStreamConstructionStub",
        "streamingPathIndex", "streamingResourceLookup",
        "streamingStreamConstructionStub", "lookupResultDispatch",
        "firstReadyStatus", "firstReadyData", "secondReadyStatus",
        "secondReadyData", "readyDataChecksStatus",
    } or len(calls) != 12:
        raise DynamicAuxBridgeError("selected Unity worker call set differs")
    target_windows = {
        "initPathIndex": "indexedPathLookup",
        "initResourceLookup": "resourceLookup",
        "streamingPathIndex": "indexedPathLookup",
        "streamingResourceLookup": "resourceLookup",
        "firstReadyStatus": "readyStatus",
        "firstReadyData": "readyDataPointer",
        "secondReadyStatus": "readyStatus",
        "secondReadyData": "readyDataPointer",
        "readyDataChecksStatus": "readyStatus",
    }
    for row in calls:
        site = int(row["siteRva"])
        if not any(int(w["startRva"]) <= site <= int(w["endRva"]) - 5
                   for w in windows.values()):
            raise DynamicAuxBridgeError(f"Unity worker call outside checked window: {row['role']}")
        if _call_target(pe, site, label=row["role"]) != pe.image_base + int(row["targetRva"]):
            raise DynamicAuxBridgeError(f"selected Unity worker call target differs: {row['role']}")
        if (row["role"] in target_windows
                and int(row["targetRva"]) != int(windows[target_windows[row["role"]]]["startRva"])):
            raise DynamicAuxBridgeError(f"selected Unity worker role target differs: {row['role']}")
    stub = contract["unityWorkerStubJump"]
    site, raw = int(stub["siteRva"]), bytes.fromhex(stub["hex"])
    if (len(raw) != 5 or raw[0] != 0xE9
            or site != next(row["targetRva"] for row in calls
                            if row["role"] == "initStreamConstructionStub")
            or site != next(row["targetRva"] for row in calls
                            if row["role"] == "streamingStreamConstructionStub")
            or int(stub["targetRva"]) != int(windows["streamConstruction"]["startRva"])
            or pe.bytes_at_va(pe.image_base + site, len(raw)) != raw
            or relative_branch_target(raw, pe.image_base + site, source="stream-constructor-stub")
            != pe.image_base + int(stub["targetRva"])):
        raise DynamicAuxBridgeError("selected Unity worker stream-constructor stub differs")

    checks = contract["unityWorkerInstructionChecks"]
    if {row["role"] for row in checks} != {
        "initPathToHandle", "streamingPathToHandle", "rootRecordSelection",
        "firstReadyBufferToRoot", "secondReadyBufferToRoot",
        "consumerSameRecordAndRoots", "secondRootField6Indexed",
        "firstRootField7Indexed",
    } or len(checks) != 8:
        raise DynamicAuxBridgeError("selected Unity worker instruction set differs")
    for row in checks:
        site, raw = int(row["rva"]), bytes.fromhex(row["hex"])
        if (not raw or not any(int(w["startRva"]) <= site
                and site + len(raw) <= int(w["endRva"]) for w in windows.values())
                or pe.bytes_at_va(pe.image_base + site, len(raw)) != raw):
            raise DynamicAuxBridgeError(f"selected Unity worker instruction differs: {row['role']}")
    builder = _validate_descriptor_builder(pe, contract, consumer_window=windows["rootConsumer"])
    return {
        "windows": list(windows),
        "calls": [row["role"] for row in calls],
        "instructionChecks": [row["role"] for row in checks],
        "descriptorBuilder": builder,
    }


def validate_native_bridge(gameassembly: Path, metadata: Path) -> dict[str, Any]:
    """Check selected managed calls, Unity registration, and native path copy."""
    contract, digest = read_reviewed_contract(
        CONTRACT, schema=SCHEMA, label="dynamic_aux_bridge", status="validated"
    )
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"],
        gameassembly=Path(gameassembly), metadata=Path(metadata),
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicAuxBridgeError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file() or sha256_file(unity).upper() != inputs["unityPlayerSha256"].upper():
        raise DynamicAuxBridgeError("installed_native_inputs:mismatched:UnityPlayer.dll missing or hash differs")

    image = open_native_image(Path(gameassembly), Path(metadata))
    managed = image.pe
    methods: dict[str, dict[str, Any]] = {}
    for row in contract["methods"]:
        role = row["role"]
        if role in methods or not 0 < int(row["windowLength"]) <= 0x800:
            raise DynamicAuxBridgeError(f"invalid selected managed method role/window: {role}")
        image.validate_method_row(
            [int(row["index"]), row["type"], row["method"], int(row["rva"])],
            label="dynamic_aux_bridge",
        )
        method = image.metadata.methods[int(row["index"])]
        parameters = [image.metadata.metadata_type_name(p.type_index)
                      for p in image.metadata.parameters_for(method)]
        if parameters != row["parameters"] or image.metadata.metadata_type_name(method.return_type) != row["returnType"]:
            raise DynamicAuxBridgeError(f"selected managed signature differs: {role}")
        body = managed.bytes_at_va(managed.image_base + int(row["rva"]), int(row["windowLength"]))
        if hashlib.sha256(body).hexdigest().upper() != row["windowSha256"].upper():
            raise DynamicAuxBridgeError(f"selected managed code window differs: {role}")
        methods[role] = row
    if set(methods) != {
        "ecsTransition", "getDataHandle", "getInitPath", "getStreamingPath",
        "allocateRuntimeChunkInjected",
    }:
        raise DynamicAuxBridgeError("selected managed method set differs")

    for row in contract["managedDirectCalls"]:
        owner = methods[row["owner"]]
        site = int(row["siteRva"])
        if not int(owner["rva"]) <= site <= int(owner["rva"]) + int(owner["windowLength"]) - 5:
            raise DynamicAuxBridgeError(f"managed call outside checked owner: {row['role']}")
        target = managed.image_base + int(methods[row["target"]]["rva"])
        if _call_target(managed, site, label=row["role"]) != target:
            raise DynamicAuxBridgeError(f"managed direct-call target differs: {row['role']}")
    if {r["role"] for r in contract["managedDirectCalls"]} != {
        "transitionToHandle", "handleToInitPath", "handleToStreamingPath",
        "handleToInjectedAllocator",
    }:
        raise DynamicAuxBridgeError("selected managed direct-call set differs")
    handoff = contract["managedArgumentHandoff"]
    handoff_rva = int(handoff["siteRva"])
    handoff_bytes = bytes.fromhex(handoff["hex"])
    allocator_call = next(r for r in contract["managedDirectCalls"]
                          if r["role"] == "handleToInjectedAllocator")
    if (handoff_rva + len(handoff_bytes) != int(allocator_call["siteRva"])
            or managed.bytes_at_va(managed.image_base + handoff_rva, len(handoff_bytes)) != handoff_bytes):
        raise DynamicAuxBridgeError("managed init/streaming argument handoff differs")

    resolver = contract["managedIcallResolver"]
    stub = methods[resolver["methodRole"]]
    load_rva, call_rva = int(resolver["literalLoadRva"]), int(resolver["resolverCallRva"])
    if (resolver["methodRole"] != "allocateRuntimeChunkInjected"
            or not int(stub["rva"]) <= load_rva
            or call_rva + 5 > int(stub["rva"]) + int(stub["windowLength"])):
        raise DynamicAuxBridgeError("managed internal-call resolver window differs")
    load = managed.bytes_at_va(managed.image_base + load_rva, 7)
    if load[:3] != b"\x48\x8d\x0d" or call_rva != load_rva + 7:
        raise DynamicAuxBridgeError("managed internal-call literal load differs")
    literal_va = managed.image_base + load_rva + 7 + struct.unpack_from("<i", load, 3)[0]
    if (managed.c_string_at_va(literal_va, limit=240) != resolver["literal"]
            or _call_target(managed, call_rva, label="managedIcallResolver")
            != managed.image_base + int(resolver["resolverTargetRva"])):
        raise DynamicAuxBridgeError("managed internal-call resolution differs")

    unity_pe = image.mapper.PeImage(unity)
    table = contract["unityInternalCallTable"]
    count, index = int(table["entryCount"]), int(table["entryIndex"])
    if not 0 < count <= 10000 or not 0 <= index < count:
        raise DynamicAuxBridgeError("Unity internal-call table bound differs")
    name_base = unity_pe.image_base + int(table["nameArrayRva"])
    function_base = unity_pe.image_base + int(table["functionArrayRva"])
    if unity_pe.u64_at_va(name_base + count * 8) != 0:
        raise DynamicAuxBridgeError("Unity internal-call name-array terminator differs")
    selected_names = [unity_pe.c_string_at_va(unity_pe.u64_at_va(name_base + i * 8), limit=240)
                      for i in range(count)]
    if (selected_names[index] != table["name"] or selected_names.count(table["name"]) != 1
            or not resolver["literal"].startswith(table["name"] + "(")
            or unity_pe.u64_at_va(function_base + index * 8)
            != unity_pe.image_base + int(table["functionRva"])):
        raise DynamicAuxBridgeError("Unity internal-call name/function registration differs")
    for i in range(count):
        pointer = unity_pe.u64_at_va(function_base + i * 8)
        offset, section, _rva = unity_pe.file_offset_for_va(pointer)
        if offset is None or section != ".text":
            raise DynamicAuxBridgeError(f"Unity internal-call function[{i}] is not raw-backed code")

    windows = {row["role"]: row for row in contract["unityCodeWindows"]}
    if set(windows) != {"allocateRuntimeChunkInjected", "runtimeChunkPathStore"}:
        raise DynamicAuxBridgeError("selected Unity code-window set differs")
    for role, row in windows.items():
        start, end = int(row["startRva"]), int(row["endRva"])
        if not 0 < end - start <= 0x800:
            raise DynamicAuxBridgeError(f"selected Unity window bound differs: {role}")
        raw = unity_pe.bytes_at_va(unity_pe.image_base + start, end - start)
        if hashlib.sha256(raw).hexdigest().upper() != row["sha256"].upper():
            raise DynamicAuxBridgeError(f"selected Unity code window differs: {role}")
    if int(windows["allocateRuntimeChunkInjected"]["startRva"]) != int(table["functionRva"]):
        raise DynamicAuxBridgeError("Unity callback/window identity differs")
    for row in contract["unityDirectCalls"]:
        site = int(row["siteRva"])
        if not any(int(w["startRva"]) <= site <= int(w["endRva"]) - 5 for w in windows.values()):
            raise DynamicAuxBridgeError(f"Unity direct call outside checked windows: {row['role']}")
        if _call_target(unity_pe, site, label=row["role"]) != unity_pe.image_base + int(row["targetRva"]):
            raise DynamicAuxBridgeError(f"Unity direct-call target differs: {row['role']}")
    if {r["role"] for r in contract["unityDirectCalls"]} != {
        "injectedToPathStore", "storeInitPath", "storeStreamingPath",
    }:
        raise DynamicAuxBridgeError("selected Unity direct-call set differs")
    for row in contract["unityInstructionChecks"]:
        site, raw = int(row["rva"]), bytes.fromhex(row["hex"])
        if (not any(int(w["startRva"]) <= site and site + len(raw) <= int(w["endRva"])
                    for w in windows.values())
                or unity_pe.bytes_at_va(unity_pe.image_base + site, len(raw)) != raw):
            raise DynamicAuxBridgeError(f"Unity path-store instruction differs: {row['role']}")
    if {r["role"] for r in contract["unityInstructionChecks"]} != {
        "helperReceivesInitPath", "helperReceivesStreamingPath", "initStringMember",
        "initStringArgument", "streamingStringMember", "streamingStringArgument",
    }:
        raise DynamicAuxBridgeError("selected Unity path-store instruction set differs")
    worker = _validate_unity_worker(unity_pe, contract)
    return {
        "format": "endfield.dynamic-aux-bridge-native-audit.v3",
        "status": "validated", "contractSha256": digest, "nativeInputs": inputs,
        "managedMethods": [{"role": row["role"], "type": row["type"], "method": row["method"]}
                           for row in contract["methods"]],
        "managedDirectCalls": [row["role"] for row in contract["managedDirectCalls"]],
        "unityInternalCall": {"name": table["name"], "functionRva": table["functionRva"]},
        "unityDirectCalls": [row["role"] for row in contract["unityDirectCalls"]],
        "unityWorker": worker,
        "evidenceBoundary": contract["evidenceBoundary"],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    args = parser.parse_args(argv)
    try:
        report = validate_native_bridge(args.gameassembly, args.metadata)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-aux-bridge-native: {error}", file=sys.stderr)
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("validated DynamicStreaming auxiliary path-to-root native route")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
