"""Reviewed conditional provider construction and descriptor storage bytes.

The selected native gate is owned by wwise_decoder_provider_native, whose
include-storage mode calls this validator on the same opened images. No SDK
name or historical report admits a slot, field, copy or live-object claim.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data import wwise_decoder_provider_native as preparation
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows, _digest, _hex, _rva

CONTRACT_PATH = CONTRACTS_DIR / "wwise_provider_storage_native.json"
SCHEMA = "endfield.wwise-provider-storage-native.v1"
GROUP_NAMES = {"singletonInitializer", "ordinaryProviderFactory", "ordinaryProviderConstructor", "providerDescriptorStorage", "wideTextCopy", "secureWideTextCopy", "alternateProviderFactory"}
LEAF_NAMES = {"ordinaryProviderOpen", "alternateProviderConstructor", "wideTextLength"}
LAYOUT_FIELDS = {
    "factory": {"ordinarySlot", "alternateSlot"},
    "provider": {"primaryTable", "secondaryTable", "descriptorAllocation", "openSlot"},
    "descriptor": {"textPointer", "numericWord", "auxiliaryPointer", "modeWord", "ownedAuxiliary"},
    "alternateProvider": {"dataPointer", "dataWord"},
}


def load_storage_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-provider-storage")
    return contract


def validate_storage_declarations(contract: dict[str, Any]) -> None:
    fail, rows = preparation._fail, preparation._rows
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("storageSchema", "contract", SCHEMA, contract.get("schema"))
    for name in ("gameAssemblySha256", "globalMetadataSha256", "akSoundEngineSha256"):
        _digest(contract["nativeInputs"][name], name)
    size = contract["nativeInputs"]["akSoundEngineFileSize"]
    if type(size) is not int or not 0 < size <= 256 * 1024 * 1024:
        fail("storageInputSize", "akSoundEngineFileSize", "bounded positive integer", size)
    owners, witnesses = {}, {}
    for leaf, declarations, names in (
        (False, rows(contract.get("nativeGroups"), "nativeGroups", 7), GROUP_NAMES),
        (True, rows(contract.get("leafWindows"), "leafWindows", 3), LEAF_NAMES),
    ):
        if len(declarations) != len(names) or {r.get("key") for r in declarations} != names:
            fail("storageOwnerCoverage", "leaf" if leaf else "group", sorted(names), [r.get("key") for r in declarations])
        for owner in declarations:
            name, start = owner["key"], _rva(owner["entryRva"], owner["key"])
            owners[name] = owner
            windows = [owner] if leaf else rows(owner.get("windows"), name, 16)
            starts = set()
            for window in windows:
                address = start if leaf else _rva(window["rva"], name)
                length = window["bodyLength"]
                if address in starts or type(length) is not int or not 1 <= length <= 65536:
                    fail("storageWindowExtent", name, "bounded unique code window", window)
                starts.add(address); _digest(window["bodySha256"], name)
                if leaf:
                    if _rva(window["boundaryRva"], name) != address + length:
                        fail("storageLeafBoundary", name, hex(address+length), window["boundaryRva"])
                    boundary = _hex(window["boundaryHex"], name, 16)
                    if any(value != 0xcc for value in boundary):
                        fail("storageLeafPadding", name, "INT3 padding", boundary.hex())
                else:
                    _rva(window["unwindRva"], name); _hex(window["unwindInfoHex"], name, 256)
            if start not in starts:
                fail("storageEntryExtent", name, "entry at window start", owner["entryRva"])
            witnesses[name] = carrier._witnesses(owner)
            for role, witness in witnesses[name].items():
                at, encoded = int(witness["rva"],16), bytes.fromhex(witness["instructionHex"])
                if not any((start if leaf else int(w["rva"],16)) <= at and at+len(encoded) <= (start if leaf else int(w["rva"],16))+w["bodyLength"] for w in windows):
                    fail("storageWitnessExtent", name+"."+role, "inside complete code window", witness["rva"])
    layouts = contract["layouts"]
    if set(layouts) != set(LAYOUT_FIELDS):
        fail("storageLayoutCoverage", "layouts", sorted(LAYOUT_FIELDS), sorted(layouts))
    for name, fields in LAYOUT_FIELDS.items():
        if set(layouts[name]) != fields:
            fail("storageFieldCoverage", name, sorted(fields), sorted(layouts[name]))
        for field, offset in layouts[name].items():
            if type(offset) is not int or not 0 <= offset <= 4096:
                fail("storageFieldOffset", name+"."+field, "bounded nonnegative integer", offset)
    bound = set()
    for binding in rows(contract["fieldBindings"], "fieldBindings", 48):
        name, field = binding["layout"], binding["field"]
        value, width = layouts[name][field], binding["displacementBytes"]
        if type(width) is not int or width not in (0, 1, 4) or (width == 0 and value != 0) or (width and value >= 1 << (width*8-1)):
            fail("storageDisplacementWidth", name+"."+field, "bounded signed displacement or base field", width)
        expected = _hex(binding["prefixHex"], field, 10) + value.to_bytes(width, "little")
        actual = bytes.fromhex(witnesses[binding["owner"]][binding["witness"]]["instructionHex"])
        if expected != actual:
            fail("storageFieldBinding", name+"."+field, expected.hex(), actual.hex())
        bound.add((name,field))
    expected_fields = {(n,f) for n,fields in LAYOUT_FIELDS.items() if n != "factory" for f in fields}
    if bound != expected_fields:
        fail("storageFieldBindingCoverage", "fieldBindings", sorted(expected_fields), sorted(bound))
    call_targets = set()
    for binding in rows(contract["callBindings"], "callBindings", 16):
        witness = witnesses[binding["owner"]][binding["witness"]]
        encoded = bytes.fromhex(witness["instructionHex"])
        opcode = _hex(binding["opcodeHex"], binding["witness"], 1)
        target = int(owners[binding["targetOwner"]]["entryRva"],16)
        if opcode not in (b"\xe8",b"\xe9") or len(encoded) != 5 or encoded[:1] != opcode or int(witness["rva"],16)+5+struct.unpack_from("<i",encoded,1)[0] != target:
            fail("storageCallTarget", binding["witness"], hex(target), encoded.hex())
        call_targets.add(binding["targetOwner"])
    required_targets = {"ordinaryProviderConstructor", "providerDescriptorStorage", "wideTextLength", "wideTextCopy", "secureWideTextCopy", "alternateProviderConstructor"}
    if call_targets != required_targets:
        fail("storageCallCoverage", "callBindings", sorted(required_targets), sorted(call_targets))
    points = {}
    for bindings in (rows(contract["addressPointBindings"], "addressPointBindings", 4), rows(contract["singletonBindings"], "singletonBindings", 2)):
        for binding in bindings:
            witness = witnesses[binding["owner"]][binding["witness"]]
            encoded = bytes.fromhex(witness["instructionHex"])
            prefix = _hex(binding["prefixHex"], binding["witness"], 3)
            target = _rva(binding["targetRva"], binding["witness"])
            if len(encoded) != 7 or encoded[:3] != prefix or int(witness["rva"],16)+7+struct.unpack_from("<i",encoded,3)[0] != target:
                fail("storageRipTarget", binding["witness"], binding["targetRva"], encoded.hex())
            points[binding["witness"]] = target
    if set(points) != {"addressFactoryTable", "addressPrimaryTable", "addressSecondaryTable", "addressAlternateTable", "loadSingleton", "storeSingleton"} or points["loadSingleton"] != points["storeSingleton"]:
        fail("storageAddressPointCoverage", "address points", "four address points and one consistent singleton", points)
    slots = rows(contract["tableSlots"], "tableSlots", 3)
    if len(slots) != 3 or {s.get("key") for s in slots} != {"factoryOrdinarySlot", "factoryAlternateSlot", "providerOpenSlot"}:
        fail("storageSlotCoverage", "tableSlots", "three reviewed slots", slots)
    for slot in slots:
        _rva(slot["addressPointRva"], slot["key"]); _digest(slot["sha256"], slot["key"])
        if type(slot["slot"]) is not int or not 0 <= slot["slot"] <= 256 or slot["slot"] % 8 or slot["targetOwner"] not in owners:
            fail("storageSlotOffset", slot["key"], "bounded pointer slot and admitted target", slot)
    allocations = contract["allocationBytes"]
    if set(allocations) != {"singleton", "ordinaryProvider", "descriptor", "alternateProvider"} or any(type(v) is not int or not 1 <= v <= 65536 for v in allocations.values()):
        fail("storageAllocationCoverage", "allocationBytes", "four bounded byte requests", allocations)
    covered = set()
    for binding in rows(contract["allocationBindings"], "allocationBindings", 4):
        name = binding["allocation"]
        expected = _hex(binding["prefixHex"], name, 1)+struct.pack("<I",allocations[name])
        actual = bytes.fromhex(witnesses[binding["owner"]][binding["witness"]]["instructionHex"])
        if actual != expected:
            fail("storageAllocationBinding", name, expected.hex(), actual.hex())
        covered.add(name)
    if covered != set(allocations):
        fail("storageAllocationBindingCoverage", "allocationBindings", sorted(allocations), sorted(covered))


def validate_storage_bytes(contract: dict[str, Any], image: Any, bodies: dict[int, bytes], records: dict[int, tuple[int, int, int]], parent: dict[str, Any]) -> None:
    validate_storage_declarations(contract)
    fail = preparation._fail
    if contract["nativeInputs"] != parent["nativeInputs"]:
        fail("storageSelectedDependency", "preparation", parent["nativeInputs"], contract["nativeInputs"])
    points = {r["witness"]:int(r["targetRva"],16) for r in contract["addressPointBindings"]+contract["singletonBindings"]}
    parent_global = {int(r["targetRva"],16) for r in parent["globalBindings"]}
    if parent_global != {points["storeSingleton"]}:
        fail("storagePreparationSingleton", "singleton", sorted(parent_global), points["storeSingleton"])
    for name in ("ordinarySlot","alternateSlot"):
        if contract["layouts"]["factory"][name] != parent["layouts"]["providerVtable"][name]:
            fail("storagePreparationSlot", name, parent["layouts"]["providerVtable"][name], contract["layouts"]["factory"][name])
    for name, parent_name in (("textPointer","descriptorPointer"),("numericWord","descriptorWord"),("auxiliaryPointer","flagsDescriptorPointer")):
        expected = parent["layouts"]["frame"][parent_name] - parent["layouts"]["frame"]["descriptorPointer"]
        if contract["layouts"]["descriptor"][name] != expected:
            fail("storagePreparationDescriptor", name, expected, contract["layouts"]["descriptor"][name])
    owners = {g["key"]:g for g in contract["nativeGroups"]+contract["leafWindows"]}
    validate_native_group_windows(contract["nativeGroups"],image,bodies,records)
    for leaf in contract["leafWindows"]:
        start,length = int(leaf["entryRva"],16),leaf["bodyLength"]
        if any(row[0] < start+length and row[1] > start for row in records.values()):
            fail("storageLeafUnwindOverlap",leaf["key"],"unwindless leaf",hex(start))
        raw=image.bytes_at_va(image.image_base+start,length)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != leaf["bodySha256"].casefold():
            fail("storageLeafBytes",leaf["key"],leaf["bodySha256"],hashlib.sha256(raw).hexdigest())
        boundary=image.bytes_at_va(image.image_base+start+length,len(bytes.fromhex(leaf["boundaryHex"])))
        if boundary != bytes.fromhex(leaf["boundaryHex"]):
            fail("storageLeafPaddingBytes",leaf["key"],leaf["boundaryHex"],boundary.hex())
        for witness in leaf["instructionWitnesses"]:
            offset=int(witness["rva"],16)-start; encoded=bytes.fromhex(witness["instructionHex"])
            if raw[offset:offset+len(encoded)] != encoded:
                fail("storageLeafWitness",witness["role"],encoded.hex(),raw[offset:offset+len(encoded)].hex())
    slot_expectations = {
        "factoryOrdinarySlot": (points["addressFactoryTable"],contract["layouts"]["factory"]["ordinarySlot"],"ordinaryProviderFactory"),
        "factoryAlternateSlot": (points["addressFactoryTable"],contract["layouts"]["factory"]["alternateSlot"],"alternateProviderFactory"),
        "providerOpenSlot": (points["addressPrimaryTable"],contract["layouts"]["provider"]["openSlot"],"ordinaryProviderOpen"),
    }
    for slot in contract["tableSlots"]:
        expected = slot_expectations[slot["key"]]
        actual = (int(slot["addressPointRva"],16),slot["slot"],slot["targetOwner"])
        if actual != expected:
            fail("storageTableRelation",slot["key"],expected,actual)
        raw=image.bytes_at_va(image.image_base+actual[0]+actual[1],8)
        target=image.image_base+int(owners[actual[2]]["entryRva"],16)
        if len(raw) != 8 or hashlib.sha256(raw).hexdigest() != slot["sha256"].casefold() or struct.unpack("<Q",raw)[0] != target:
            fail("storageTableBytes",slot["key"],f"{slot['sha256']}/{hex(target)}",raw.hex())
