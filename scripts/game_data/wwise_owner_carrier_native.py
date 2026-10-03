"""Authenticate the primary-owner command queue and carrier-control boundary.

The selected source owner dependency and complete native groups share one opened
image. The optional observer projection is entry-only: command-4 control may
release a decoder, so its return never licenses a second pointer dereference.
Queue batching/recycling is structural and does not prove object generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data import wwise_source_native as source_native
from scripts.game_data.wwise_source_native import SourceContractError, _collect_source_image
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_windows, validate_opened_managed_inputs,
)


CONTRACT_PATH = CONTRACTS_DIR / "wwise_owner_carrier_native.json"
SCHEMA = "endfield.wwise-owner-carrier-native.v1"
ROLE_ARGUMENTS = {
    "ownerCommand4": {"primaryOwnerPointer"},
    "ownerCommandEnqueue": {"commandWord", "primaryOwnerPointer"},
    "ownerCarrierLookup": {"commandPayloadPointer"},
    "carrierCommand4": {"carrierPointer", "primaryOwnerPointer"},
}
RETURN_KINDS = {"ownerCommand4": "u32", "ownerCommandEnqueue": "u32", "ownerCarrierLookup": "pointer", "carrierCommand4": "void"}
LAYOUT_FIELDS = {
    "primaryOwner": {"addressPoint": "pointer", "carrierPointer": "pointer", "command4StateWord": "u16"},
    "queueNode": {"nextPointer": "pointer", "primaryOwnerPointer": "pointer", "batchSerialWord": "u32", "commandStatusWord": "u32"},
    "commandPayload": {"primaryOwnerPointer": "pointer", "batchSerialWord": "u32", "commandStatusWord": "u32"},
    "carrier": {"currentDecoderPointer": "pointer", "pendingDecoderPointer": "pointer", "controlStateWord": "u32", "controlReasonWord": "u32"},
    "decoder": {"primaryOwnerPointer": "pointer", "flagsByte": "u8"},
}
CONSTANT_NAMES = {"queueNodeBytes", "payloadOffset", "selectedCommand", "readyBit", "enqueueSuccessStatus", "allocationFailureStatus"}
REGISTERS = {name: index for index, name in enumerate(("rax", "rcx", "rdx", "rbx", "rsp", "rbp", "rsi", "rdi", "r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15"))}
ARGUMENT_REGISTERS = (1, 2, 8, 9)


def _fail(check: str, subject: str, expected: Any, actual: Any) -> None:
    raise SourceContractError(check, subject, expected, actual)


def load_owner_carrier_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-owner-carrier")
    return contract


def _records(value: Any, subject: str, maximum: int) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not 1 <= len(value) <= maximum or any(not isinstance(row, dict) for row in value):
        _fail("carrierDeclarationRows", subject, f"1..{maximum} objects", type(value).__name__)
    return value


def _witnesses(owner: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = _records(owner.get("instructionWitnesses"), owner["key"], 128)
    required = owner.get("requiredRoles")
    if not isinstance(required, list) or not required or len(required) > 128 or any(not isinstance(name, str) or not 1 <= len(name) <= 96 for name in required) or len(set(required)) != len(required):
        _fail("carrierRequiredRoles", owner["key"], "bounded unique role names", required)
    result = {}
    for row in rows:
        role = row.get("role")
        if not isinstance(role, str) or not 1 <= len(role) <= 96 or role in result:
            _fail("carrierWitnessRole", owner["key"], "unique bounded name", role)
        _rva(row.get("rva"), role)
        _hex(row.get("instructionHex"), role, 15)
        result[role] = row
    if set(result) != set(required):
        _fail("carrierWitnessCoverage", owner["key"], required, sorted(result))
    return result


def validate_owner_carrier_declarations(contract: dict[str, Any]) -> None:
    """Bind ABI/fields/constants to reviewed instruction bytes before reads."""
    owners: dict[str, dict[str, Any]] = {}
    for leaf, rows in ((False, _records(contract.get("nativeGroups"), "nativeGroups", 8)), (True, _records(contract.get("leafWindows"), "leafWindows", 8))):
        for owner in rows:
            key = owner.get("key")
            if not isinstance(key, str) or not 1 <= len(key) <= 96 or key in owners:
                _fail("carrierNativeKey", "native", "unique bounded key", key)
            owners[key] = owner
            entry = _rva(owner.get("entryRva"), key)
            windows = [dict(owner, rva=owner["entryRva"])] if leaf else _records(owner.get("windows"), key, 16)
            starts = set()
            for window in windows:
                start = _rva(window.get("rva"), key)
                length = window.get("bodyLength")
                if type(length) is not int or not 1 <= length <= 16384 or start in starts:
                    _fail("carrierWindowExtent", key, "unique bounded full extent", length)
                starts.add(start)
                _digest(window.get("bodySha256"), key)
                if not leaf:
                    _rva(window.get("unwindRva"), key)
                    _hex(window.get("unwindInfoHex"), key, 256)
            if entry not in starts:
                _fail("carrierEntryExtent", key, "true entry in full group", entry)
            if leaf:
                if _rva(owner.get("boundaryRva"), key) != entry + owner["bodyLength"] or _hex(owner.get("boundaryHex"), key, 16) != b"\xcc" * len(bytes.fromhex(owner["boundaryHex"])):
                    _fail("carrierLeafBoundary", key, "following interrupt padding", owner.get("boundaryHex"))
            for row in _witnesses(owner).values():
                address, encoded = int(row["rva"], 16), bytes.fromhex(row["instructionHex"])
                if not any(int(win["rva"], 16) <= address and address + len(encoded) <= int(win["rva"], 16) + win["bodyLength"] for win in windows):
                    _fail("carrierWitnessExtent", row["role"], "inside full extent", row["rva"])
    dependency = contract.get("sourceOwnerDependency")
    if not isinstance(dependency, dict) or dependency.get("sourceContractRole") != "constructor":
        _fail("carrierSourceOwnerRole", "dependency", "existing constructor endpoint", dependency)
    dep_rows = _records(dependency.get("instructionWitnesses"), "sourceConstructor", 8)
    if {row.get("role") for row in dep_rows} != {"loadPrimaryAddressPoint", "storePrimaryAddressPoint"}:
        _fail("carrierPrimaryPointWitnesses", "dependency", "load and store", dep_rows)
    dependency = {**dependency, "key": "sourceConstructor", "requiredRoles": [row["role"] for row in dep_rows]}
    owners["sourceConstructor"] = dependency
    witnesses = {key: _witnesses(row) for key, row in owners.items()}
    layouts, constants, functions = contract.get("layouts"), contract.get("constants"), contract.get("functionRoles")
    if not isinstance(layouts, dict) or set(layouts) != set(LAYOUT_FIELDS):
        _fail("carrierLayouts", "layouts", sorted(LAYOUT_FIELDS), layouts)
    for name, fields in layouts.items():
        if not isinstance(fields, dict) or set(fields) != set(LAYOUT_FIELDS[name]):
            _fail("carrierLayoutFields", name, sorted(LAYOUT_FIELDS[name]), fields)
        for field, value in fields.items():
            if not isinstance(value, dict) or type(value.get("offset")) is not int or not 0 <= value["offset"] <= 4096 or value.get("kind") != LAYOUT_FIELDS[name][field]:
                _fail("carrierField", f"{name}.{field}", "bounded offset and reviewed type", value)
    if not isinstance(constants, dict) or set(constants) != CONSTANT_NAMES or any(type(value) is not int or not 0 <= value <= 0xffffffff for value in constants.values()):
        _fail("carrierConstants", "constants", sorted(CONSTANT_NAMES), constants)
    if not isinstance(functions, dict) or set(functions) != set(ROLE_ARGUMENTS):
        _fail("carrierFunctions", "functionRoles", sorted(ROLE_ARGUMENTS), functions)
    for name, function in functions.items():
        if not isinstance(function, dict) or ("groupKey" in function) == ("leafKey" in function) or function.get("groupKey", function.get("leafKey")) not in owners or function.get("returnKind") != RETURN_KINDS[name]:
            _fail("carrierFunctionPolicy", name, "one authenticated endpoint and reviewed return policy", function)
        args = function.get("args")
        if not isinstance(args, dict) or set(args) != ROLE_ARGUMENTS[name]:
            _fail("carrierArguments", name, sorted(ROLE_ARGUMENTS[name]), args)
        for arg, value in args.items():
            kind = "u32" if arg == "commandWord" else "pointer"
            if not isinstance(value, dict) or type(value.get("index")) is not int or not 0 <= value["index"] <= 3 or value.get("kind") != kind:
                _fail("carrierArgument", f"{name}.{arg}", "reviewed first-four register argument", value)

    def witness(binding: dict[str, Any], key: str = "ownerKey") -> bytes:
        row = witnesses.get(binding.get(key), {}).get(binding.get("witnessRole"))
        if row is None:
            _fail("carrierBindingWitness", "binding", "owned witness", binding)
        return bytes.fromhex(row["instructionHex"])

    def coverage(rows: list[dict[str, Any]], key, expected: set):
        actual = [key(row) for row in rows]
        if len(set(actual)) != len(actual) or set(actual) != expected:
            _fail("carrierBindingCoverage", "binding", sorted(expected), actual)

    abi = _records(contract.get("abiBindings"), "abiBindings", 16)
    coverage(abi, lambda row: (row.get("functionRole"), row.get("argument")), {(name, arg) for name, function in functions.items() for arg in function["args"]})
    for binding in abi:
        function = functions[binding["functionRole"]]
        arg = function["args"][binding["argument"]]
        register = ARGUMENT_REGISTERS[arg["index"]]
        owner = function.get("groupKey", function.get("leafKey"))
        encoded = witness({**binding, "ownerKey": owner})
        if binding.get("bindingKind") == "comparePointerField":
            base = REGISTERS.get(binding.get("baseRegister"))
            field = layouts.get(binding.get("layout"), {}).get(binding.get("field"), {})
            offset = field.get("offset")
            if base is None or base & 7 == 4 or type(offset) is not int or not 0 <= offset <= 127 or arg["kind"] != "pointer":
                _fail("carrierAbiCompare", binding["argument"], "bounded pointer comparison", binding)
            rex = 0x48 | (4 if register >= 8 else 0) | (1 if base >= 8 else 0)
            expected = bytes((rex, 0x3b, 0x40 | (register & 7) << 3 | base & 7, offset))
        else:
            destination = REGISTERS.get(binding.get("retainedRegister"))
            if destination is None or binding.get("bindingKind") not in (None, "registerMove"):
                _fail("carrierAbiMove", binding["argument"], "retained register move", binding)
            rex = (0x48 if arg["kind"] == "pointer" else 0x40) | (4 if destination >= 8 else 0) | (1 if register >= 8 else 0)
            expected = (bytes((rex,)) if rex != 0x40 else b"") + bytes((0x8b, 0xc0 | (destination & 7) << 3 | register & 7))
        if encoded != expected:
            _fail("carrierAbiInstruction", binding["argument"], expected.hex(), encoded.hex())
    fields = _records(contract.get("layoutBindings"), "layoutBindings", 32)
    coverage(fields, lambda row: (row.get("layout"), row.get("field")), {(name, field) for name, layout in layouts.items() for field in layout})
    for binding in fields:
        offset = layouts[binding["layout"]][binding["field"]]["offset"]
        width = binding.get("displacementBytes")
        if type(width) is not int or width not in (0, 1, 4) or width == 0 and offset != 0 or width == 1 and offset > 127:
            _fail("carrierFieldDisplacement", binding["field"], "actual bounded displacement", width)
        expected = _hex(binding.get("prefixHex"), binding["field"], 15) + (struct.pack("<b" if width == 1 else "<i", offset) if width else b"") + bytes.fromhex(binding.get("suffixHex", ""))
        encoded = witness(binding)
        if expected != encoded:
            _fail("carrierLayoutInstruction", binding["field"], expected.hex(), encoded.hex())
    values = _records(contract.get("constantBindings"), "constantBindings", 16)
    coverage(values, lambda row: row.get("constant"), CONSTANT_NAMES)
    for binding in values:
        value, width = constants[binding["constant"]], binding.get("immediateBytes")
        if type(width) is not int or width not in (1, 4) or binding.get("transform") not in ("identity", "complement32"):
            _fail("carrierConstantEncoding", binding["constant"], "bounded immediate", binding)
        value = value if binding["transform"] == "identity" else (~value & 0xffffffff)
        expected = _hex(binding.get("prefixHex"), binding["constant"], 15) + value.to_bytes(width, "little")
        encoded = witness(binding)
        if expected != encoded:
            _fail("carrierConstantInstruction", binding["constant"], expected.hex(), encoded.hex())
    calls = _records(contract.get("callBindings"), "callBindings", 8)
    coverage(calls, lambda row: row.get("targetRole"), {"ownerCommandEnqueue", "ownerCarrierLookup", "carrierCommand4"})
    for binding in calls:
        target = functions[binding["targetRole"]]
        target_entry = int(owners[target.get("groupKey", target.get("leafKey"))]["entryRva"], 16)
        row = witnesses[binding["ownerKey"]][binding["witnessRole"]]
        opcode = _hex(binding.get("opcodeHex"), "call", 1)
        if opcode not in (b"\xe8", b"\xe9"):
            _fail("carrierCallOpcode", "call", "direct call or tail jump", binding)
        expected = opcode + struct.pack("<i", target_entry - int(row["rva"], 16) - 5)
        if bytes.fromhex(row["instructionHex"]) != expected:
            _fail("carrierCallTarget", binding["targetRole"], expected.hex(), row["instructionHex"])
    table, point = contract.get("dispatchTable"), contract.get("addressPoint")
    if not isinstance(table, dict) or not isinstance(point, dict):
        _fail("carrierDataDeclarations", "data", "dispatch and address point", [table, point])
    for row in (table, point):
        _rva(row.get("rva"), "data")
        _digest(row.get("sha256"), "data")
    count, selected = table.get("entryCount"), table.get("selectedTag")
    if type(count) is not int or not 1 <= count <= 256 or type(selected) is not int or not 0 <= selected < count or selected != constants["selectedCommand"]:
        _fail("carrierCommandTable", "dispatchTable", "bounded selected command", table)
    owner = owners.get(table.get("ownerGroup"), {})
    target = _rva(table.get("targetRva"), "dispatchTable")
    if not any(int(win["rva"], 16) <= int(table["rva"], 16) and int(table["rva"], 16) + count * 4 <= int(win["rva"], 16) + win["bodyLength"] and int(win["rva"], 16) <= target < int(win["rva"], 16) + win["bodyLength"] for win in owner.get("windows", [])):
        _fail("carrierCommandTableOwner", "dispatchTable", "table and target in full drain extent", table)
    size, slot = point.get("bytes"), point.get("entrySlot")
    if type(size) is not int or not 8 <= size <= 4096 or type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > size or point.get("targetLeaf") != functions["ownerCommand4"].get("leafKey"):
        _fail("carrierAddressPoint", "addressPoint", "bounded slot selecting owner command4 leaf", point)
    drain_witnesses = witnesses[table["ownerGroup"]]
    table_load = bytes.fromhex(drain_witnesses["loadCommandDispatchTable"]["instructionHex"])
    expected_table_load = bytes.fromhex("418b8c84") + struct.pack("<I", int(table["rva"], 16))
    if table_load != expected_table_load:
        _fail("carrierDispatchTableAddress", "dispatchTable", expected_table_load.hex(), table_load.hex())
    ready_bit = constants["readyBit"]
    if not ready_bit or ready_bit & (ready_bit - 1):
        _fail("carrierReadyBit", "readyBit", "single u32 bit", ready_bit)
    expected_test = bytes.fromhex("0fbae0") + bytes((ready_bit.bit_length() - 1,))
    actual_test = bytes.fromhex(drain_witnesses["testDispatchReadyBit"]["instructionHex"])
    if actual_test != expected_test:
        _fail("carrierDispatchReadyBit", "readyBit", expected_test.hex(), actual_test.hex())
    node, payload = layouts["queueNode"], layouts["commandPayload"]
    for field in payload:
        if node[field]["offset"] != constants["payloadOffset"] + payload[field]["offset"]:
            _fail("carrierPayloadLayout", field, constants["payloadOffset"] + payload[field]["offset"], node[field]["offset"])
    if node["commandStatusWord"]["offset"] + 4 != constants["queueNodeBytes"]:
        _fail("carrierNodeExtent", "queueNodeBytes", node["commandStatusWord"]["offset"] + 4, constants["queueNodeBytes"])


def validate_owner_carrier_bytes(contract: dict[str, Any], image: Any, bodies: dict[int, bytes], records: dict[int, tuple[int, int, int]], source: dict[str, Any]) -> None:
    validate_owner_carrier_declarations(contract)
    validate_native_group_windows(contract["nativeGroups"], image, bodies, records)
    for leaf in contract["leafWindows"]:
        entry, length = int(leaf["entryRva"], 16), leaf["bodyLength"]
        if any(start < entry + length and row[1] > entry for start, row in records.items()):
            _fail("carrierLeafUnwindOverlap", leaf["key"], "unwindless leaf", hex(entry))
        raw = image.bytes_at_va(image.image_base + entry, length)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != leaf["bodySha256"].casefold():
            _fail("carrierLeafBytes", leaf["key"], leaf["bodySha256"], hashlib.sha256(raw).hexdigest())
        boundary = image.bytes_at_va(image.image_base + int(leaf["boundaryRva"], 16), len(bytes.fromhex(leaf["boundaryHex"])))
        if boundary != bytes.fromhex(leaf["boundaryHex"]):
            _fail("carrierLeafPadding", leaf["key"], leaf["boundaryHex"], boundary.hex())
        for witness in leaf["instructionWitnesses"]:
            start = int(witness["rva"], 16) - entry
            encoded = bytes.fromhex(witness["instructionHex"])
            if raw[start:start + len(encoded)] != encoded:
                _fail("carrierLeafWitness", witness["role"], encoded.hex(), raw[start:start + len(encoded)].hex())
    point, table = contract["addressPoint"], contract["dispatchTable"]
    for row, length in ((point, point["bytes"]), (table, table["entryCount"] * 4)):
        raw = image.bytes_at_va(image.image_base + int(row["rva"], 16), length)
        if len(raw) != length or hashlib.sha256(raw).hexdigest() != row["sha256"].casefold():
            _fail("carrierDataBytes", row["rva"], row["sha256"], hashlib.sha256(raw).hexdigest())
        if row is point:
            leaf = next(item for item in contract["leafWindows"] if item["key"] == point["targetLeaf"])
            target = struct.unpack_from("<Q", raw, point["entrySlot"])[0] - image.image_base
            expected = int(leaf["entryRva"], 16)
        else:
            target = struct.unpack_from("<I", raw, table["selectedTag"] * 4)[0]
            expected = int(table["targetRva"], 16)
        if target != expected:
            _fail("carrierDataTarget", row["rva"], hex(expected), hex(target))
    if source["nativeInputs"] != contract["nativeInputs"] or len(source["ownerTransports"]) != 1:
        _fail("carrierSourceSelectedInputs", "source dependency", contract["nativeInputs"], source["nativeInputs"])
    constructor = source["ownerTransports"][0]["constructor"]
    for witness in contract["sourceOwnerDependency"]["instructionWitnesses"]:
        address, encoded = int(witness["rva"], 16), bytes.fromhex(witness["instructionHex"])
        window = next((win for win in constructor["windows"] if int(win["rva"], 16) <= address and address + len(encoded) <= int(win["rva"], 16) + win["bodyLength"]), None)
        if window is None:
            _fail("carrierConstructorWitnessExtent", witness["role"], "inside admitted existing constructor", witness["rva"])
        offset = address - int(window["rva"], 16)
        actual = bodies[int(window["rva"], 16)][offset:offset + len(encoded)]
        if actual != encoded:
            _fail("carrierConstructorWitness", witness["role"], encoded.hex(), actual.hex())
        if witness["role"] == "loadPrimaryAddressPoint":
            if len(encoded) != 7 or encoded[:3] != b"\x48\x8d\x05" or address + 7 + struct.unpack_from("<i", encoded, 3)[0] != int(point["rva"], 16):
                _fail("carrierConstructorAddressPoint", witness["role"], point["rva"], encoded.hex())


def build_owner_carrier_observer_spec(contract: dict[str, Any], source: dict[str, Any]) -> dict[str, Any]:
    """Project typed entry-only fields after the selected native gate passes."""
    owners = {row["key"]: row for row in contract["nativeGroups"] + contract["leafWindows"]}
    roles = {}
    for name, function in contract["functionRoles"].items():
        owner = owners[function.get("groupKey", function.get("leafKey"))]
        roles[name] = {"sourceKind": owner["key"], "entryRva": owner["entryRva"], "args": function["args"], "returnKind": function["returnKind"]}
    drain = next(row for row in contract["nativeGroups"] if row["key"] == contract["dispatchTable"]["ownerGroup"])
    witnesses = {row["role"]: row for row in drain["instructionWitnesses"]}
    callers = {name: [hex(int(witnesses[witness]["rva"], 16) + len(bytes.fromhex(witnesses[witness]["instructionHex"])))] for name, witness in (("ownerCarrierLookup", "callCarrierLookup"), ("carrierCommand4", "callCarrierCommand4Control"))}
    return {"schema": "endfield.wwise-owner-carrier-observer.v1", "moduleName": Path(source["captureFiles"]["akSoundEngine"]["relativePath"]).name,
            "roles": roles, "layouts": contract["layouts"], "constants": contract["constants"], "primaryAddressPointRva": contract["addressPoint"]["rva"],
            "callers": callers, "sourcePointerOffset": source["ownerTransports"][0]["primarySourcePointerOffset"],
            "sourceFields": source["structures"]["source"]["fields"], "memorySamplePhase": "entry", "evidenceBoundary": contract["evidenceBoundary"]}


def load_validated_owner_carrier_contract(*, gameassembly: Path, metadata: Path, ak_sound_engine: Path, contract_path: Path = CONTRACT_PATH) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    audit: dict[str, Any] = {"status": "missing", "contractPath": str(contract_path), "detail": ""}
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        audit.update(detail="three explicit selected native paths are required", diagnostic={"failedCheck": "selectedInputs", "actual": "missing path"})
        return None, audit
    try:
        contract = load_owner_carrier_contract(contract_path)
        validate_owner_carrier_declarations(contract)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["globalMetadataSha256"], gameassembly=gameassembly, metadata=metadata, require_metadata=True)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != "validated":
            return None, audit
        if not ak_sound_engine.is_file():
            audit.update(status="missing", detail=f"selected AkSoundEngine.dll not found: {ak_sound_engine}")
            return None, audit
        size, digest = ak_sound_engine.stat().st_size, sha256_file(ak_sound_engine)
        if size != inputs["akSoundEngineFileSize"] or digest.casefold() != inputs["akSoundEngineSha256"].casefold():
            _fail("carrierAkSoundEngineInput", str(ak_sound_engine), f"{inputs['akSoundEngineFileSize']}/{inputs['akSoundEngineSha256']}", f"{size}/{digest}")
        managed = NativeImage(gameassembly, metadata, label="wwise-owner-carrier")
        validate_opened_managed_inputs(contract, managed)
        image, bodies, records = _collect_source_image(ak_sound_engine, managed.mapper)
        digest = hashlib.sha256(image.buf).hexdigest()
        if digest != inputs["akSoundEngineSha256"].casefold():
            _fail("carrierOpenedInput", str(ak_sound_engine), inputs["akSoundEngineSha256"], digest)
        source = source_native.load_source_contract()
        source_native.validate_source_contract(source)
        source_native.validate_source_bodies(source, bodies)
        source_native.validate_source_consumers(source, image, records)
        source_native.validate_source_transports(source, image, bodies)
        validate_owner_carrier_bytes(contract, image, bodies, records, source)
        audit.update(status="validated", detail="selected owner command queue and conditional carrier-control transport validated; generation/provider unresolved",
                     evidenceBoundary=contract["evidenceBoundary"], ownerCarrierObserverSpec=build_owner_carrier_observer_spec(contract, source))
        return contract, audit
    except SourceContractError as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic=error.diagnostic)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError) as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic={"failedCheck": "ownerCarrierContract", "actual": str(error)[:160]})
    return None, audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--ak-sound-engine", required=True, type=Path)
    args = parser.parse_args()
    _contract, audit = load_validated_owner_carrier_contract(gameassembly=args.gameassembly, metadata=args.metadata, ak_sound_engine=args.ak_sound_engine)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
