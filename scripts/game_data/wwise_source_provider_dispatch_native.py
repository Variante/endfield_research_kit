"""Reviewed source-based provider dispatch and storage-wrapper callsites.

The decoder-provider gate calls this validator with its already opened selected
images and storage contract. No separate scan or historical address is trusted.
"""
from __future__ import annotations

import struct
from pathlib import Path

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_decoder_provider_native as preparation
from scripts.game_data import wwise_owner_carrier_native as carrier
from scripts.game_data.wwise_source_queue_native import validate_native_group_windows, _hex, _rva

CONTRACT_PATH = CONTRACTS_DIR / "wwise_source_provider_dispatch_native.json"
SCHEMA = "endfield.wwise-source-provider-dispatch-native.v1"
LAYOUT_FIELDS = {
    "request": {"sourcePointer", "alternateDataPointer", "alternateDataWord"},
    "source": {"flagsWord", "storedWord", "dataPointer", "argumentHighWord"},
    "frame": {"descriptorPointer", "descriptorWord", "auxiliaryPointer", "directDataFlag", "argumentHighWord", "options"},
    "providerVtable": {"alternateSlot", "ordinarySlot"},
}


def load_dispatch_contract(path: Path = CONTRACT_PATH) -> dict:
    contract, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-source-provider-dispatch")
    return contract


def validate_dispatch_bytes(contract: dict, image, bodies: dict, records: dict,
                            parent: dict, storage: dict) -> None:
    fail, rows = preparation._fail, preparation._rows
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("dispatchSchema", "contract", SCHEMA, contract.get("schema"))
    if contract["nativeInputs"] != parent["nativeInputs"] or storage["nativeInputs"] != parent["nativeInputs"]:
        fail("dispatchSelectedInputs", "source/storage", parent["nativeInputs"], contract["nativeInputs"])
    groups = rows(contract["nativeGroups"], "dispatchGroups", 2)
    if len(groups) != 2 or {g["key"] for g in groups} != {"anonymousSourceProviderPreparation", "anonymousProviderStorageOpen"}:
        fail("dispatchGroupCoverage", "groups", "two reviewed groups", [g["key"] for g in groups])
    validate_native_group_windows(groups, image, bodies, records)
    witnesses = {g["key"]: carrier._witnesses(g) for g in groups}
    source = witnesses["anonymousSourceProviderPreparation"]
    required = {"retainRequest": "488bfa", "retainOutputContext": "488bd9",
                "loadRequestSource": "4c8b02", "passOrdinaryOutput": "48895c2420",
                "passAlternateOutput": "48895c2420", "callOrdinarySlot": "41ffd2"}
    for name, encoded in required.items():
        if source[name]["instructionHex"] != encoded:
            fail("dispatchArgumentTransport", name, encoded, source[name]["instructionHex"])
    layouts = contract["layouts"]
    if set(layouts) != set(LAYOUT_FIELDS):
        fail("dispatchLayoutCoverage", "layouts", sorted(LAYOUT_FIELDS), sorted(layouts))
    for name, fields in LAYOUT_FIELDS.items():
        layout = layouts[name]
        if not isinstance(layout, dict) or set(layout) != fields or any(type(v) is not int or not 0 <= v <= 4096 for v in layout.values()):
            fail("dispatchLayouts", name, sorted(fields), layout)
    bound = set()
    for binding in rows(contract["fieldBindings"], "dispatchFieldBindings", 32):
        subject = (binding["layout"], binding["field"])
        value, width = layouts[subject[0]][subject[1]], binding["displacementBytes"]
        if type(width) is not int or width not in (0, 1, 4) or (not width and value) or (width and value >= 1 << (width * 8 - 1)):
            fail("dispatchFieldWidth", ".".join(subject), "bounded signed displacement", width)
        expected = _hex(binding["prefixHex"], binding["witness"], 10) + value.to_bytes(width, "little")
        actual = bytes.fromhex(source[binding["witness"]]["instructionHex"])
        if actual != expected:
            fail("dispatchFieldBinding", ".".join(subject), expected.hex(), actual.hex())
        bound.add(subject)
    if bound != {(name, field) for name, layout in layouts.items() for field in layout}:
        fail("dispatchFieldCoverage", "fields", "each field bound to an instruction", sorted(bound))
    for name in ("source", "providerVtable"):
        if layouts[name] != parent["layouts"][name]:
            fail("dispatchDependencyLayout", name, parent["layouts"][name], layouts[name])
    frame = layouts["frame"]
    for field, storage_field in (("descriptorWord", "numericWord"), ("auxiliaryPointer", "auxiliaryPointer")):
        if frame[field] - frame["descriptorPointer"] != storage["layouts"]["descriptor"][storage_field]:
            fail("dispatchDescriptorLayout", field, storage["layouts"]["descriptor"][storage_field], frame[field] - frame["descriptorPointer"])
    if contract["constants"] != parent["constants"]:
        fail("dispatchConstants", "constants", parent["constants"], contract["constants"])
    covered = set()
    for binding in rows(contract["constantBindings"], "dispatchConstants", 4):
        name = binding["constant"]
        expected = _hex(binding["prefixHex"], name, 10) + bytes([contract["constants"][name]])
        actual = bytes.fromhex(source[binding["witness"]]["instructionHex"])
        if actual != expected: fail("dispatchConstantBinding", name, expected.hex(), actual.hex())
        covered.add(name)
    if covered != set(contract["constants"]): fail("dispatchConstantCoverage", "constants", sorted(contract["constants"]), sorted(covered))
    branches = rows(contract["branchBindings"], "dispatchBranches", 3)
    if len(branches) != 3 or {b["witness"] for b in branches} != {"branchOrdinaryKind", "branchNumericDescriptor", "jumpOrdinaryCall"}:
        fail("dispatchBranchCoverage", "branches", "three distinct branch witnesses", [b["witness"] for b in branches])
    for binding in branches:
        witness, target = source[binding["witness"]], source[binding["targetWitness"]]
        raw = bytes.fromhex(witness["instructionHex"])
        if len(raw) != 2 or raw[:1] != _hex(binding["opcodeHex"], "branch", 1) or int(witness["rva"], 16) + 2 + struct.unpack("<b", raw[1:])[0] != int(target["rva"], 16):
            fail("dispatchBranch", binding["witness"], target["rva"], raw.hex())
    singleton = {int(row["targetRva"], 16) for row in parent["globalBindings"]}
    globals_rows = rows(contract["singletonBindings"], "dispatchSingleton", 2)
    if len(globals_rows) != 2 or {b["witness"] for b in globals_rows} != {"loadOrdinarySingleton", "loadAlternateSingleton"}:
        fail("dispatchSingletonCoverage", "globals", "ordinary and alternate loads", [b["witness"] for b in globals_rows])
    for binding in globals_rows:
        witness = source[binding["witness"]]
        raw = bytes.fromhex(witness["instructionHex"])
        target = _rva(binding["targetRva"], "singleton")
        if len(raw) != 7 or raw[:3] != _hex(binding["prefixHex"], "singleton", 3) or int(witness["rva"], 16) + 7 + struct.unpack_from("<i", raw, 3)[0] != target or {target} != singleton:
            fail("dispatchSingleton", binding["witness"], sorted(singleton), raw.hex())
    targets = {g["key"]: int(g["entryRva"], 16) for g in storage["nativeGroups"]}
    for binding in rows(contract["callBindings"], "dispatchCalls", 1):
        witness = witnesses[binding["owner"]][binding["witness"]]
        raw = bytes.fromhex(witness["instructionHex"])
        target = targets[binding["targetOwner"]]
        if len(raw) != 5 or raw[0] != 0xe8 or int(witness["rva"], 16) + 5 + struct.unpack_from("<i", raw, 1)[0] != target:
            fail("dispatchCall", binding["witness"], hex(target), raw.hex())


def observer_spec(contract: dict, parent: dict, storage: dict) -> dict:
    """Derive local entry caller/address-point checks from admitted witnesses."""
    groups = {g["key"]: carrier._witnesses(g) for g in contract["nativeGroups"]}
    decoder = next(g for g in parent["nativeGroups"] if g["key"] == "anonymousDecoderProviderPreparation")
    decoder = carrier._witnesses(decoder)
    factory = next(g for g in storage["nativeGroups"] if g["key"] == "ordinaryProviderFactory")
    factory = carrier._witnesses(factory)
    source = groups["anonymousSourceProviderPreparation"]

    def after(witness: dict) -> int:
        return int(witness["rva"], 16) + len(bytes.fromhex(witness["instructionHex"]))

    points = {row["witness"]: row["targetRva"] for row in storage["addressPointBindings"]}
    return {"schema": "endfield.wwise-provider-entry-observer-spec.v1",
            "providerAddressPointRva": points["addressPrimaryTable"],
            "factoryAddressPointRva": points["addressFactoryTable"],
            "callers": {
                "anonymousOrdinaryProviderFactory": {after(source["callOrdinarySlot"]): "sourceBasedPreparation", after(decoder["callOrdinarySlot"]): "decoderPreparation"},
                "anonymousAlternateProviderFactory": {after(source["callAlternateSlot"]): "sourceBasedPreparation", after(decoder["callAlternateSlot"]): "decoderPreparation"},
                "anonymousOrdinaryProviderOpen": {after(factory["callPrimaryOpenSlot"]): "ordinaryProviderFactory"},
                "anonymousProviderDescriptorStorage": {after(factory["callPrimaryOpenSlot"]): "ordinaryProviderFactoryTailDispatch",
                    after(groups["anonymousProviderStorageOpen"]["callDescriptorStorage"]): "storageOpenWrapper"}},
            "evidenceBoundary": contract["evidenceBoundary"]}
