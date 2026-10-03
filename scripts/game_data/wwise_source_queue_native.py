"""Authenticate descriptor queue transport and conditional source selection.

This companion gates the opt-in source-bridge observer against explicit selected
files. Its reviewed bytes close descriptor retention through the event queue and
action argument blob, then a conditional node/source/owner route. Static transport
does not establish live managed request ownership or pointer lifetime; the classic
and source-consumer observer recipes remain unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex, ClaimError, evaluate
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data import wwise_source_native as source_native
from scripts.game_data.wwise_source_native import SourceContractError, _collect_source_image, _unwind_record


CONTRACT_PATH = CONTRACTS_DIR / "wwise_source_queue_native.json"
SCHEMA = "endfield.wwise-source-queue-native.v1"
BRIDGE_ARGUMENT_NAMES = {
    "sourceSelector": {"anonymousNodePointer", "originalSourcePointer", "playbackBlobPointer"},
    "sourceClone": {"originalSourcePointer"},
    "sourceSetWideText": {"sourceThisPointer", "sourceLookupWord", "sourceArgumentWord24", "descriptorWideTextPointer"},
    "ownerFactory": {"sourceThisPointer"},
    "ownerConstructor": {"anonymousPrimaryOwnerPointer", "sourceThisPointer"},
}
BRIDGE_RETURN_KINDS = {
    "sourceSelector": "void", "sourceClone": "pointer", "sourceSetWideText": "void",
    "ownerFactory": "pointer", "ownerConstructor": "pointer",
}
BRIDGE_LAYOUT_NAMES = {
    "playbackBlob": {"configInterfacePointer", "externalAllocationPointer", "contextPointer", "flagsWord", "serialWord"},
    "externalAllocation": {"count", "firstDescriptor", "descriptorStride"},
    "descriptor": {"matchWord", "argumentWord", "wideTextPointer", "memoryPointer", "byteCountWord", "selectionWord"},
    "source": {"matchWord", "dataPointer", "selectionArgumentWord", "cloneBytes"},
}


def _fail(check: str, subject: str, expected: Any, actual: Any) -> None:
    raise SourceContractError(check, subject, expected, actual)


def _rva(value: Any, subject: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-fA-F]{1,8}", value) is None:
        _fail("queueRva", subject, "bounded hexadecimal RVA", value)
    return int(value, 16)


def _hex(value: Any, subject: str, limit: int) -> bytes:
    if not isinstance(value, str) or not value or len(value) % 2 or len(value) > limit * 2:
        _fail("queueHex", subject, f"1..{limit} bytes", str(value)[:80])
    try:
        return bytes.fromhex(value)
    except ValueError:
        _fail("queueHex", subject, "hexadecimal bytes", str(value)[:80])


def _digest(value: Any, subject: str) -> None:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-fA-F]{64}", value) is None:
        _fail("queueDigest", subject, "SHA256", value)


def load_queue_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _digest_value = read_reviewed_contract(
        path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-source-queue",
    )
    return contract


def validate_queue_declarations(contract: dict[str, Any]) -> None:
    """Bound declarations before byte reads; require every reviewed role once."""
    groups = contract.get("nativeGroups")
    if not isinstance(groups, list) or not 1 <= len(groups) <= 24:
        _fail("queueGroups", "contract", "1..24 groups", type(groups).__name__)
    names: set[str] = set()
    for group in groups:
        if not isinstance(group, dict):
            _fail("queueGroupRecord", "contract", "object", type(group).__name__)
        name = group.get("key")
        if not isinstance(name, str) or not name or name in names:
            _fail("queueGroupKey", "contract", "unique nonempty key", name)
        names.add(name)
        entry = _rva(group.get("entryRva"), name)
        windows = group.get("windows")
        if not isinstance(windows, list) or not 1 <= len(windows) <= 16:
            _fail("queueWindows", name, "1..16 full extents", type(windows).__name__)
        starts: set[int] = set()
        for window in windows:
            if not isinstance(window, dict):
                _fail("queueWindowRecord", name, "object", type(window).__name__)
            start = _rva(window.get("rva"), name)
            length = window.get("bodyLength")
            if start in starts or type(length) is not int or not 1 <= length <= 16384:
                _fail("queueWindowExtent", name, "unique start and 1..16384 bytes", f"{start}/{length}")
            starts.add(start)
            _digest(window.get("bodySha256"), name)
            _rva(window.get("unwindRva"), name)
            _hex(window.get("unwindInfoHex"), name, 256)
        if entry not in starts:
            _fail("queueEntryExtent", name, "entry is a declared start", group.get("entryRva"))
        witnesses = group.get("instructionWitnesses")
        required = group.get("requiredRoles")
        if (not isinstance(witnesses, list) or not 1 <= len(witnesses) <= 128
                or not isinstance(required, list) or not required or len(required) > 128
                or any(not isinstance(role, str) or not role or len(role) > 96 for role in required)
                or len(set(required)) != len(required)):
            _fail("queueTransportRoles", name, "bounded witnesses and unique required roles", required)
        roles: set[str] = set()
        for witness in witnesses:
            if not isinstance(witness, dict):
                _fail("queueWitnessRecord", name, "object", type(witness).__name__)
            role = witness.get("role")
            if not isinstance(role, str) or not role or role in roles:
                _fail("queueWitnessRole", name, "unique nonempty role", role)
            roles.add(role)
            address = _rva(witness.get("rva"), role)
            encoded = _hex(witness.get("instructionHex"), role, 15)
            if not any(int(win["rva"], 16) <= address and address + len(encoded) <= int(win["rva"], 16) + win["bodyLength"] for win in windows):
                _fail("queueWitnessExtent", role, "inside declared full extent", witness["rva"])
        if roles != set(required):
            _fail("queueTransportRoles", name, sorted(required), sorted(roles))
    table = contract.get("dispatchTable", {})
    if not isinstance(table, dict):
        _fail("queueDispatchRecord", "dispatchTable", "object", type(table).__name__)
    _rva(table.get("rva"), "dispatchTable")
    count, selected = table.get("entryCount"), table.get("selectedTag")
    if type(count) is not int or not 1 <= count <= 256 or type(selected) is not int or not 0 <= selected < count:
        _fail("queueDispatchExtent", "dispatchTable", "1..256 entries and in-range selected tag", f"{count}/{selected}")
    _digest(table.get("sha256"), "dispatchTable")
    _rva(table.get("targetRva"), "dispatchTable")
    owner = next((g for g in groups if g["key"] == table.get("ownerGroup")), None)
    if owner is None or not any(int(win["rva"], 16) <= int(table["rva"], 16) and int(table["rva"], 16) + count * 4 <= int(win["rva"], 16) + win["bodyLength"] for win in owner["windows"]):
        _fail("queueDispatchOwner", "dispatchTable", "table inside authenticated group extent", table.get("ownerGroup"))
    data_windows = contract.get("dataWindows", [])
    if not isinstance(data_windows, list) or len(data_windows) > 32:
        _fail("queueDataWindows", "contract", "list of at most32", type(data_windows).__name__)
    for window in data_windows:
        if not isinstance(window, dict):
            _fail("queueDataRecord", "dataWindow", "object", type(window).__name__)
        _rva(window.get("rva"), "dataWindow")
        if type(window.get("bytes")) is not int or not 1 <= window["bytes"] <= 4096:
            _fail("queueDataExtent", "dataWindow", "1..4096 bytes", window.get("bytes"))
        _digest(window.get("sha256"), "dataWindow")
        if window.get("module", "akSoundEngine") not in ("gameAssembly", "akSoundEngine"):
            _fail("queueDataModule", "dataWindow", "declared selected native module", window.get("module"))
        if "entrySlot" in window:
            slot = window["entrySlot"]
            bridge_declaration = contract.get("sourceBridgeObserver")
            functions = bridge_declaration.get("functionRoles", {}) if isinstance(bridge_declaration, dict) else {}
            source_target = functions.get(window.get("targetGroup"), {}) if isinstance(functions, dict) else {}
            source_target = source_target if isinstance(source_target, dict) else {}
            if (type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > window["bytes"]
                    or window.get("module", "akSoundEngine") != "akSoundEngine"
                    or window.get("targetGroup") not in names and source_target.get("sourceContractRole") not in ("factory", "constructor")):
                _fail("queueAddressPointSlot", "dataWindow", "aligned bounded slot targeting named group", window)
    managed_windows = contract.get("managedWindows", [])
    if not isinstance(managed_windows, list) or len(managed_windows) > 32:
        _fail("queueManagedWindows", "contract", "list of at most32", type(managed_windows).__name__)
    for window in managed_windows:
        if not isinstance(window, dict) or type(window.get("startRva")) is not int or type(window.get("endRva")) is not int or not 0 <= window["startRva"] < window["endRva"] <= 0xffffffff or window["endRva"] - window["startRva"] > 16384:
            _fail("queueManagedExtent", "managedWindow", "bounded selected window", window)
        _digest(window.get("sha256"), "managedWindow")
    if not isinstance(contract.get("managedClaims"), dict) or not contract["managedClaims"]:
        _fail("queueManagedClaims", "contract", "nonempty named claims", contract.get("managedClaims"))
    bridge = contract.get("sourceBridgeObserver")
    if bridge is not None:
        if not isinstance(bridge, dict) or bridge.get("maxDescriptorRows") != 1 or type(bridge.get("maxDescriptorRows")) is not int:
            _fail("queueBridgeScope", "sourceBridgeObserver", "one sampled descriptor row", bridge)
        layouts = bridge.get("bridgeLayouts")
        if not isinstance(layouts, dict) or set(layouts) != set(BRIDGE_LAYOUT_NAMES):
            _fail("queueBridgeLayouts", "sourceBridgeObserver", "declared bridge layout families", type(layouts).__name__)
        for key, layout in layouts.items():
            if not isinstance(key, str) or not isinstance(layout, dict) or not layout or len(layout) > 32 or any(not isinstance(name, str) or type(value) is not int or not 0 <= value <= 4096 for name, value in layout.items()):
                _fail("queueBridgeLayout", key, "bounded named integer field roles", layout)
            if set(layout) != BRIDGE_LAYOUT_NAMES[key]:
                _fail("queueBridgeLayoutFields", key, sorted(BRIDGE_LAYOUT_NAMES[key]), sorted(layout))
        functions = bridge.get("functionRoles")
        if not isinstance(functions, dict) or set(functions) != set(BRIDGE_ARGUMENT_NAMES):
            _fail("queueBridgeFunctions", "sourceBridgeObserver", "five named bridge functions", type(functions).__name__)
        for name, function in functions.items():
            if not isinstance(name, str) or not isinstance(function, dict):
                _fail("queueBridgeFunction", str(name), "named object", type(function).__name__)
            if ("groupKey" in function) == ("sourceContractRole" in function):
                _fail("queueBridgeFunctionOwner", name, "one native group or existing source role", function)
            expected_source_role = {"ownerFactory": "factory", "ownerConstructor": "constructor"}.get(name)
            if expected_source_role is not None and function.get("sourceContractRole") != expected_source_role:
                _fail("queueBridgeSourceRole", name, expected_source_role, function.get("sourceContractRole"))
            if expected_source_role is None and "groupKey" not in function:
                _fail("queueBridgeFunctionGroup", name, "authenticated native group", function)
            if "groupKey" in function and function["groupKey"] not in names:
                _fail("queueBridgeFunctionGroup", name, "authenticated native group", function["groupKey"])
            if "sourceContractRole" in function and function["sourceContractRole"] not in ("factory", "constructor"):
                _fail("queueBridgeSourceRole", name, "factory or constructor", function["sourceContractRole"])
            args = function.get("args")
            if not isinstance(args, dict) or not args or len(args) > 4:
                _fail("queueBridgeArgs", name, "1..4 register arguments", args)
            if set(args) != BRIDGE_ARGUMENT_NAMES[name]:
                _fail("queueBridgeArgumentNames", name, sorted(BRIDGE_ARGUMENT_NAMES[name]), sorted(args))
            indices: set[int] = set()
            for arg_name, arg in args.items():
                if not isinstance(arg_name, str) or not isinstance(arg, dict) or type(arg.get("index")) is not int or not 0 <= arg["index"] <= 3 or arg["index"] in indices or arg.get("kind") not in ("pointer", "u32"):
                    _fail("queueBridgeArg", name, "unique typed register argument", arg)
                if "allowNull" in arg and (type(arg["allowNull"]) is not bool or arg["kind"] != "pointer"):
                    _fail("queueBridgeNullableArgument", arg_name, "boolean on pointer argument only", arg)
                indices.add(arg["index"])
            if function.get("returnKind") != BRIDGE_RETURN_KINDS[name]:
                _fail("queueBridgeReturn", name, BRIDGE_RETURN_KINDS[name], function.get("returnKind"))
            memory = function.get("memory", [])
            if not isinstance(memory, list) or len(memory) > 32:
                _fail("queueBridgeMemory", name, "list of at most32 fixed reads", type(memory).__name__)
            memory_names: set[str] = set()
            for read in memory:
                if not isinstance(read, dict) or not isinstance(read.get("name"), str) or not read["name"] or read["name"] in memory_names:
                    _fail("queueBridgeMemoryName", name, "unique named read", read)
                memory_names.add(read["name"])
                chain = read.get("pointerOffsets", [])
                if type(read.get("argIndex")) is not int or read["argIndex"] not in indices or type(read.get("offset")) is not int or not 0 <= read["offset"] <= 4096 or read.get("kind") not in ("pointer", "u32", "utf16", "utf16Direct") or not isinstance(chain, list) or len(chain) > 2 or any(type(offset) is not int or not 0 <= offset <= 4096 for offset in chain):
                    _fail("queueBridgeMemoryRecipe", read["name"], "bounded fixed pointer chain/field", read)
                if "samplePhase" in read and read["samplePhase"] not in ("entry", "result"):
                    _fail("queueBridgeSamplePhase", read["name"], "entry or result", read["samplePhase"])
        witnesses_by_group = {group["key"]: {w["role"]: w for w in group["instructionWitnesses"]} for group in groups}
        abi = bridge.get("abiWitnesses", [])
        if not isinstance(abi, list) or len(abi) > 32:
            _fail("queueBridgeAbiWitnesses", "sourceBridgeObserver", "bounded list", abi)
        register_indices = {"rax": 0, "rcx": 1, "rdx": 2, "rbx": 3, "rsp": 4, "rbp": 5, "rsi": 6, "rdi": 7, **{f"r{i}": i for i in range(8, 16)}}
        argument_registers = (1, 2, 8, 9)
        abi_coverage: set[tuple[str, str]] = set()
        for binding in abi:
            if not isinstance(binding, dict) or binding.get("functionRole") not in functions:
                _fail("queueBridgeAbiWitness", "sourceBridgeObserver", "named function argument binding", binding)
            function = functions[binding["functionRole"]]
            arg = function["args"].get(binding.get("argument"))
            destination = register_indices.get(binding.get("retainedRegister"))
            witness = witnesses_by_group.get(function.get("groupKey"), {}).get(binding.get("witnessRole"))
            pair = (binding["functionRole"], binding.get("argument"))
            if not arg or destination is None or witness is None or pair in abi_coverage:
                _fail("queueBridgeAbiBinding", binding["functionRole"], "unique argument with retained-register witness", binding)
            abi_coverage.add(pair)
            register = argument_registers[arg["index"]]
            rex = (0x48 if arg["kind"] == "pointer" else 0x40) | (4 if destination >= 8 else 0) | (1 if register >= 8 else 0)
            encoded = (bytes((rex,)) if rex != 0x40 else b"") + bytes((0x8b, 0xc0 | (destination & 7) << 3 | register & 7))
            if bytes.fromhex(witness["instructionHex"]) != encoded:
                _fail("queueBridgeAbiInstruction", binding["argument"], encoded.hex(), witness["instructionHex"])
        required_abi = {(name, arg) for name, function in functions.items() if "groupKey" in function for arg in function["args"]}
        if abi_coverage != required_abi:
            _fail("queueBridgeAbiCoverage", "sourceBridgeObserver", sorted(required_abi), sorted(abi_coverage))
        bindings = bridge.get("layoutWitnesses", [])
        if not isinstance(bindings, list) or len(bindings) > 64:
            _fail("queueBridgeLayoutWitnesses", "sourceBridgeObserver", "bounded list", bindings)
        layout_coverage: set[tuple[str, str]] = set()
        for binding in bindings:
            if not isinstance(binding, dict):
                _fail("queueBridgeLayoutWitness", "sourceBridgeObserver", "object", type(binding).__name__)
            layout = layouts.get(binding.get("layout"), {})
            value = layout.get(binding.get("field"))
            witness = witnesses_by_group.get(binding.get("groupKey"), {}).get(binding.get("witnessRole"))
            width = binding.get("displacementBytes")
            base = binding.get("baseOffset", 0)
            pair = (binding.get("layout"), binding.get("field"))
            if type(value) is not int or witness is None or type(width) is not int or width not in (0, 1, 4) or type(base) is not int or not 0 <= base <= 4096 or width == 1 and value + base > 127 or width == 0 and value + base != 0 or pair in layout_coverage:
                _fail("queueBridgeLayoutBinding", str(binding.get("field")), "bounded field and actual transport witness", binding)
            layout_coverage.add(pair)
            prefix = _hex(binding.get("prefixHex"), str(binding.get("field")), 14)
            encoded = prefix + (struct.pack("<b" if width == 1 else "<i", value + base) if width else b"")
            if bytes.fromhex(witness["instructionHex"]) != encoded:
                _fail("queueBridgeLayoutInstruction", binding["field"], encoded.hex(), witness["instructionHex"])
        required_layout = {(name, field) for name, layout in layouts.items() for field in layout}
        if layout_coverage != required_layout:
            _fail("queueBridgeLayoutCoverage", "sourceBridgeObserver", sorted(required_layout), sorted(layout_coverage))


def validate_queue_bodies(contract: dict[str, Any], image: Any, bodies: dict[int, bytes], records: dict[int, tuple[int, int, int]], *, source_roles: dict[str, Any] | None = None) -> None:
    """Validate complete unwind groups, role bytes and the actual dispatch case."""
    validate_queue_declarations(contract)
    validate_native_group_windows(contract["nativeGroups"], image, bodies, records)
    validate_queue_data_windows(contract, image, source_roles=source_roles)


def validate_native_group_windows(groups: list[dict[str, Any]], image: Any, bodies: dict[int, bytes], records: dict[int, tuple[int, int, int]]) -> None:
    """Validate declared full unwind groups on one already opened source image.

    Callers own their bounded declaration shape before invoking this shared
    native-family byte checker.
    """
    cache: dict[int, tuple[bytes, tuple[int, int, int] | None]] = {}

    def unwind(row: tuple[int, int, int]):
        if row[0] not in cache:
            cache[row[0]] = _unwind_record(image, row)
        return cache[row[0]]

    def root(row: tuple[int, int, int]) -> int:
        seen: set[int] = set()
        for _ in range(16):
            if row[0] in seen:
                _fail("queueUnwindCycle", hex(row[0]), "acyclic group", sorted(seen))
            seen.add(row[0])
            _raw, parent = unwind(row)
            if parent is None:
                return row[0]
            if records.get(parent[0]) != parent:
                _fail("queueUnwindParent", hex(row[0]), "actual parent record", parent)
            row = parent
        _fail("queueUnwindDepth", hex(row[0]), "at most16", 17)

    roots = {start: root(row) for start, row in records.items()}
    for group in groups:
        name, entry = group["key"], int(group["entryRva"], 16)
        expected_starts = {int(win["rva"], 16) for win in group["windows"]}
        actual_starts = {start for start, owner in roots.items() if owner == entry}
        if roots.get(entry) != entry or expected_starts != actual_starts:
            _fail("queueUnwindGroup", name, sorted(expected_starts), sorted(actual_starts))
        for window in group["windows"]:
            start = int(window["rva"], 16)
            raw = bodies.get(start)
            if raw is None or len(raw) != window["bodyLength"] or records[start][1] - start != window["bodyLength"]:
                _fail("queueBodyExtent", name, window["bodyLength"], None if raw is None else len(raw))
            actual = hashlib.sha256(raw).hexdigest()
            if actual != window["bodySha256"].casefold():
                _fail("queueBodySha256", name, window["bodySha256"], actual)
            uw, _parent = unwind(records[start])
            if records[start][2] != int(window["unwindRva"], 16) or uw != bytes.fromhex(window["unwindInfoHex"]):
                _fail("queueUnwindBytes", name, f"{window['unwindRva']}/{window['unwindInfoHex']}", f"{records[start][2]:x}/{uw.hex()}")
        for witness in group["instructionWitnesses"]:
            address, encoded = int(witness["rva"], 16), bytes.fromhex(witness["instructionHex"])
            window = next(win for win in group["windows"] if int(win["rva"], 16) <= address and address + len(encoded) <= int(win["rva"], 16) + win["bodyLength"])
            offset = address - int(window["rva"], 16)
            actual = bodies[int(window["rva"], 16)][offset:offset + len(encoded)]
            if actual != encoded:
                _fail("queueTransportWitness", witness["role"], encoded.hex(), actual.hex())


def validate_queue_data_windows(contract: dict[str, Any], image: Any, *, source_roles: dict[str, Any] | None = None) -> None:
    """Validate selected data/address-point windows and queue dispatch table."""
    for window in contract.get("dataWindows", []):
        if window.get("module", "akSoundEngine") != "akSoundEngine":
            continue
        raw = image.bytes_at_va(image.image_base + int(window["rva"], 16), window["bytes"])
        actual = hashlib.sha256(raw).hexdigest()
        if len(raw) != window["bytes"] or actual != window["sha256"].casefold():
            _fail("queueDataSha256", window.get("key", "dataWindow"), window["sha256"], actual)
        if "entrySlot" in window:
            target = next((group for group in contract["nativeGroups"] if group["key"] == window["targetGroup"]), None)
            if target is None:
                target = (source_roles or {}).get(window["targetGroup"])
            if target is None:
                _fail("queueAddressPointDependency", window["key"], "authenticated existing source endpoint", window["targetGroup"])
            expected_pointer = image.image_base + int(target["entryRva"], 16)
            pointer = struct.unpack_from("<Q", raw, window["entrySlot"])[0]
            if pointer != expected_pointer:
                _fail("queueAddressPointTarget", window["key"], hex(expected_pointer), hex(pointer))
    table = contract["dispatchTable"]
    raw = image.bytes_at_va(image.image_base + int(table["rva"], 16), table["entryCount"] * 4)
    actual = hashlib.sha256(raw).hexdigest()
    if len(raw) != table["entryCount"] * 4 or actual != table["sha256"].casefold():
        _fail("queueDispatchSha256", "dispatchTable", table["sha256"], actual)
    target = struct.unpack_from("<I", raw, table["selectedTag"] * 4)[0]
    if target != int(table["targetRva"], 16):
        _fail("queueDispatchTarget", "dispatchTable", table["targetRva"], hex(target))
    owner = next(g for g in contract["nativeGroups"] if g["key"] == table["ownerGroup"])
    if not any(int(win["rva"], 16) <= target < int(win["rva"], 16) + win["bodyLength"] for win in owner["windows"]):
        _fail("queueDispatchTargetExtent", "dispatchTable", "inside owning function group", hex(target))


def validate_managed_queue_claims(contract: dict[str, Any], image: NativeImage) -> list[dict[str, Any]]:
    rows, failures = evaluate(BodyIndex(image), contract["managedClaims"])
    if failures:
        _fail("queueManagedClaim", failures[0].get("symbol", "method"), "reviewed named claim", failures[0])
    image.check_windows(contract.get("managedWindows", []), gate="wwise-source-queue-managed")
    for window in contract.get("dataWindows", []):
        if window.get("module") != "gameAssembly":
            continue
        raw = image.pe.bytes_at_va(image.pe.image_base + int(window["rva"], 16), window["bytes"])
        actual = hashlib.sha256(raw).hexdigest()
        if len(raw) != window["bytes"] or actual != window["sha256"].casefold():
            _fail("queueManagedDataSha256", window.get("key", "dataWindow"), window["sha256"], actual)
    return rows


def validate_source_role_dependencies(contract: dict[str, Any], managed: NativeImage, image: Any, bodies: dict[int, bytes], records: dict[int, tuple[int, int, int]], *, relation_spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """Reuse the source owner's contract on the same opened selected images."""
    bridge = contract.get("sourceBridgeObserver")
    if bridge is None:
        return {}
    source = source_native.load_source_contract()
    source_native.validate_source_contract(source)
    if source["nativeInputs"] != contract["nativeInputs"]:
        _fail("queueSourceSelectedInputs", "source roles", contract["nativeInputs"], source["nativeInputs"])
    source_native.validate_source_bodies(source, bodies)
    source_native.validate_source_consumers(source, image, records)
    source_native.validate_source_transports(source, image, bodies)
    source_native.validate_managed_bridges(source, managed)
    transports = source["ownerTransports"]
    if len(transports) != 1:
        _fail("queueSourceOwnerSelection", "source roles", "one reviewed owner transport", len(transports))
    result: dict[str, Any] = {}
    for name, role in bridge["functionRoles"].items():
        if "sourceContractRole" not in role:
            continue
        expected_endpoint = {"ownerFactory": "factory", "ownerConstructor": "constructor"}.get(name)
        if role["sourceContractRole"] != expected_endpoint:
            _fail("queueSourceEndpoint", name, expected_endpoint, role["sourceContractRole"])
        endpoint = transports[0][role["sourceContractRole"]]
        source_arg = endpoint["sourceArgument"]
        arg = role["args"].get(source_arg["name"])
        if arg != {"index": source_arg["index"], "kind": source_arg["kind"]}:
            _fail("queueSourceArgument", name, source_arg, arg)
        owner_arg = endpoint.get("ownerArgument")
        if owner_arg is not None and role["args"].get(owner_arg["name"]) != {"index": owner_arg["index"], "kind": owner_arg["kind"]}:
            _fail("queueSourceOwnerArgument", name, owner_arg, role["args"].get(owner_arg["name"]))
        result[name] = {"entryRva": endpoint["entryRva"], "key": endpoint["key"], "sourceArgument": source_arg}
    if relation_spec is not None:
        relation_spec.update(build_source_bridge_relation_spec(contract, source, result))
    return result


def build_source_bridge_relation_spec(contract: dict[str, Any], source: dict[str, Any], source_roles: dict[str, Any]) -> dict[str, Any]:
    """Project minimal relation roles only after their owning gates authenticate."""
    bridge = contract["sourceBridgeObserver"]
    groups = {group["key"]: group for group in contract["nativeGroups"]}
    functions = bridge["functionRoles"]
    transport = source["ownerTransports"][0]
    consumer = next(row for row in source["consumers"] if row["key"] == transport["consumerKey"])
    roles = {}
    for name, function in functions.items():
        endpoint = groups.get(function.get("groupKey")) or source_roles[name]
        roles[name] = {"sourceKind": endpoint["key"], "entryRva": endpoint["entryRva"], "args": function["args"]}
    roles["ownerConsumer"] = {"sourceKind": consumer["key"], "entryRva": consumer["entryRva"],
                              "args": {consumer["ownerArgument"]["name"]: {key: consumer["ownerArgument"][key] for key in ("index", "kind")}}}
    lock = next(row for row in source["methods"] if row["key"] == consumer["calleeKey"])
    roles["sourceLock"] = {"sourceKind": lock["key"], "entryRva": lock["rva"], "args": lock["args"]}
    selector = groups[functions["sourceSelector"]["groupKey"]]
    witnesses = {row["role"]: row for row in selector["instructionWitnesses"]}

    def next_instruction(name: str) -> str:
        row = witnesses[name]
        return hex(int(row["rva"], 16) + len(bytes.fromhex(row["instructionHex"])))

    factory = transport["factory"]
    ctor_call = next((window, witness) for window in factory["windows"] for witness in window["instructionWitnesses"] if witness["role"] == "callConstructor")
    ctor_return = int(ctor_call[0]["rva"], 16) + ctor_call[1]["bodyOffset"] + len(bytes.fromhex(ctor_call[1]["instructionHex"]))
    config_call = bytes.fromhex(witnesses["callConfigInterfaceSlot32"]["instructionHex"])
    if len(config_call) != 3 or config_call[:2] != bytes.fromhex("ff50"):
        _fail("queueBridgeDispatchInstruction", "config dispatch", "bounded indirect register call with byte slot", config_call.hex())
    config_slot = config_call[-1]
    dispatch = []
    for window in contract["dataWindows"]:
        if window.get("entrySlot") != config_slot or window.get("module", "akSoundEngine") != "akSoundEngine":
            continue
        endpoint = groups.get(window["targetGroup"]) or source_roles[window["targetGroup"]]
        dispatch.append({"addressPointRva": window["rva"], "entrySlot": config_slot,
                         "targetRva": endpoint["entryRva"],
                         "dispatchKind": "directFactory" if window["targetGroup"] == "ownerFactory" else "conditionalFactoryWrapper"})
    return {"schema": "endfield.wwise-source-bridge-relations.v1",
            "moduleName": Path(source["captureFiles"]["akSoundEngine"]["relativePath"]).name,
            "roles": roles, "bridgeLayouts": bridge["bridgeLayouts"],
            "sourceFields": source["structures"]["source"]["fields"],
            "outputFields": source["structures"][consumer["outputReference"]["structure"]]["fields"],
            "ownerLayout": {"consumerOwnerOffset": transport["consumerOwnerOffset"],
                            "primarySourcePointerOffset": transport["primarySourcePointerOffset"],
                            "consumerSourcePointerOffset": consumer["sourcePointerField"]["offset"],
                            "consumerOutputOffset": consumer["outputReference"]["offset"]},
            "consumerAddressPointRva": transport["addressPointWindow"]["rva"],
            "callers": {"sourceClone": [next_instruction("cloneOriginalSource")],
                        "sourceSetWideText": [next_instruction("callWideTextSourceSetterPointerBranch"), next_instruction("callWideTextSourceSetterWord28Branch")],
                        "ownerFactory": [next_instruction("callConfigInterfaceSlot32")],
                        "ownerConstructor": [hex(ctor_return)],
                        "ownerConsumer": [next_instruction("callEmbeddedOwnerSlot80")],
                        "sourceLock": [consumer["returnRva"]]},
            "configDispatchRows": dispatch}


def validate_opened_managed_inputs(contract: dict[str, Any], image: NativeImage) -> None:
    """Bind hashes to the opened bytes reused by every claim and source role."""
    for key, raw in (("gameAssemblySha256", image.pe.buf), ("globalMetadataSha256", image.metadata.buf)):
        actual = hashlib.sha256(raw).hexdigest()
        expected = contract["nativeInputs"][key].casefold()
        if actual != expected:
            _fail("queueOpenedManagedInput", key, expected, actual)


def load_validated_queue_contract(*, gameassembly: Path, metadata: Path, ak_sound_engine: Path, contract_path: Path = CONTRACT_PATH) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Fail closed without choosing a default native path or publishing a capture."""
    audit: dict[str, Any] = {"status": "missing", "contractPath": str(contract_path), "detail": ""}
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        audit.update(detail="three explicit selected native paths are required", diagnostic={"failedCheck": "selectedInputs", "expected": "three explicit paths", "actual": "missing path"})
        return None, audit
    try:
        contract = load_queue_contract(contract_path)
        validate_queue_declarations(contract)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["globalMetadataSha256"], gameassembly=gameassembly, metadata=metadata, require_metadata=True)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != "validated":
            return None, audit
        if not ak_sound_engine.is_file():
            audit.update(status="missing", detail=f"selected AkSoundEngine.dll not found: {ak_sound_engine}")
            return None, audit
        actual_size, actual_hash = ak_sound_engine.stat().st_size, sha256_file(ak_sound_engine)
        if actual_size != inputs["akSoundEngineFileSize"] or actual_hash.casefold() != inputs["akSoundEngineSha256"].casefold():
            _fail("queueAkSoundEngineInput", str(ak_sound_engine), f"{inputs['akSoundEngineFileSize']}/{inputs['akSoundEngineSha256']}", f"{actual_size}/{actual_hash}")
        managed = NativeImage(gameassembly, metadata, label="wwise-source-queue")
        validate_opened_managed_inputs(contract, managed)
        source, bodies, records = _collect_source_image(ak_sound_engine, managed.mapper)
        opened_hash = hashlib.sha256(source.buf).hexdigest()
        if opened_hash != inputs["akSoundEngineSha256"].casefold():
            _fail("queueOpenedInput", str(ak_sound_engine), inputs["akSoundEngineSha256"], opened_hash)
        relation_spec: dict[str, Any] = {}
        source_roles = validate_source_role_dependencies(contract, managed, source, bodies, records, relation_spec=relation_spec)
        validate_queue_bodies(contract, source, bodies, records, source_roles=source_roles)
        rows = validate_managed_queue_claims(contract, managed)
        contract = {**contract, "resolvedSourceContractRoles": source_roles}
        audit.update(status="validated", detail="selected static descriptor/queue/action and conditional source selection validated; runtime ownership/lifetime unresolved", nativeGroups=len(contract["nativeGroups"]), managedClaims=len(rows), resolvedSourceContractRoles=source_roles, evidenceBoundary=contract["evidenceBoundary"])
        if relation_spec:
            audit["sourceBridgeRelationSpec"] = relation_spec
        return contract, audit
    except SourceContractError as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic=error.diagnostic)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, ClaimError) as error:
        audit.update(status="mismatched", detail=str(error)[:320], diagnostic={"failedCheck": "queueContract", "actual": str(error)[:160]})
    return None, audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", required=True, type=Path)
    parser.add_argument("--metadata", required=True, type=Path)
    parser.add_argument("--ak-sound-engine", required=True, type=Path)
    args = parser.parse_args()
    _contract, audit = load_validated_queue_contract(gameassembly=args.gameassembly, metadata=args.metadata, ak_sound_engine=args.ak_sound_engine)
    print(json.dumps(audit, ensure_ascii=False, indent=2))
    return 0 if audit["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
