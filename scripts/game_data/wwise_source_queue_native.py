"""Authenticate descriptor queue transport and conditional source selection.

This companion gates the opt-in source-bridge observer against explicit selected
files. Its reviewed bytes close descriptor retention through the event queue and
action argument blob, then a conditional node/source/owner route. The bank loader
joins the serialized source ID to the descriptor match word, and the offline plan
preserves stored descriptor order and raw argument conversion. Static transport
also authenticates the posted Event registry key and the Play Action target
reader/setter/lookup, including a complete unwindless leaf and shared vtable slots.
It does not establish live managed request ownership or pointer lifetime; the classic
and source-consumer observer recipes remain unchanged.

Evidence and admission boundary:

The companion `wwise_source_queue_native.json` and
`wwise_source_queue_native.py` now authenticate the descriptor's earlier native
transport and a conditional selection route. The managed default body supplies
the cookie and path through checked setter order. Native copying retains the
descriptor and its text in an owned allocation, the event queue retains that
allocation, and the checked dispatch case carries it into the action's playback
argument blob. The reviewed node dispatch passes the same blob to a source
selector. Its guarded branch clones the incoming source, matches its stored
word against a descriptor, and prepares the selected source through the
observed setter route. A checked config address point then forwards the
selected pointer through the already reviewed factory and constructor before
addressing the embedded consumer. Complete code and unwind extents, transport
instructions, dispatch-table bytes and actual address-point targets gate this
route; neighboring pointers supply no ownership claim. The selector branch,
preparation success and chosen address points remain conditions, rather than
observations of a runtime instance. Bank HIRC dispatch now binds authored
Action and Event records to their native registration loaders. The Action
category factory selects the normal Play constructor, preserving the full
stored type; its target and per-class readers then populate the registered
object. A newly inserted Event reads its high-chunk-first variable count and
resolves the authored Action IDs in order against the shared Action registry.
Each successful lookup retains that Action object and appends it through its
intrusive next field to the Event head. These are the same head/next fields
later read by the queue drain.

This order correspondence requires distinct resolved Action objects and no
later link mutation. A zero Action ID or missing registry entry stops reading,
leaving the constructed prefix before failure handling. Duplicate IDs can
create a cycle or shorten the visible list; another Event using the same Action
can change its next link. Existing Event IDs reuse their current object and
skip the new authored list. Neither registry is qualified by physical bank
occurrence, so same-bank parser identity is stronger than the native global key
match. Original-byte offline checks cover these distinctions, including
complete registration loaders with explicit helper models.

The posted Event ID has a direct native identity edge before queueing. The
engine uses its unsigned remainder to choose a registry bucket, walks collision
links, and compares the full Event DWORD. It retains the matching registered
node and carries that node together with the external allocation in the same
queue record. The admitted drain case walks that node's registered Action
links. Each eligible, successfully allocated Action argument receives the same
descriptor allocation and playback serial; missing required object data or
failed allocation skips an Action and continues. The Event reference is
released after traversal. Original-byte offline checks cover these branches.
The registered-list correspondence above is conditional; neither it nor
reference counter arithmetic proves live queue allocation generations or
assigns a saved source capture to a posted Event.

The normal Play Action now has a checked target edge as well. Its bank reader
requires the constructed and stored Action types to agree, then passes the
stored target DWORD and normalized nonzero target flag through the checked
address-point setter. The setter replaces only the target registry-selection
bit. Execution calls a lookup which selects one of two registry tables, tests
the complete target key through its collision chain, retains the matching node
and returns its primary object. A missing target has no fallback to the other
namespace. The selected target supplies the existing preparation and node-play
route. Complete code/unwind extents and a separately authenticated complete
leaf setter gate this interpretation; offline checks also feed representative
physical bank Action bytes through the original reader and target lookup.
Target presence, node subtype, selected address points and preparation success
remain conditions, rather than an observation of live bank selection.

The queue companion now also authenticates the bank source-record reader and
the node's bank-loading body. On the admitted codec branch, the reader takes
the source ID from the typed bank prefix and copies it into both the lookup and
match words of its temporary info aggregate. The node loader passes this
aggregate and the separately read plug-in argument to the independently owned
`sourceSetInfo` method. That setter installs the source words in the same
node-relative source which the reviewed node-play wrapper supplies to the
selector. This closes the stored source-ID to native match-word edge. For an
External Source Sound, the ID is the descriptor cookie; it is not the key of a
packaged voice file. The loader's node-type, reader-success and no-parameter
branches remain explicit conditions, and this does not observe live bank
loading or Event selection.

The selector tests the original source argument's high word before entering
external selection. It requires an allocation, clones the source, and scans the
descriptors in stored order. A matching row is usable first by a nonzero
selection word, otherwise by a wide-text pointer, otherwise by a nonzero byte
count together with a memory pointer. A matching but unusable row is skipped;
the first usable match wins. There is no choice of a voice path from the Event
ID alone. Missing usable descriptors discard the clone; clone allocation
failure has a different local status. The contract and its offline plan keep
these outcomes separate from downstream construction and playback.

Preparation changes the source's original match word: the ordinary wide-text
and memory routes replace it with their sentinel, while the selection-word
route installs that word. Therefore a later source snapshot need not retain the
cookie which selected it. The lookup word is a separate field. The wide-text
setter resets its storage and only installs the supplied argument when that
lookup input is nonzero. It returns no status, and failed text allocation still
rejoins the selector's provisional success branch. A selected descriptor is
consequently insufficient evidence of a retained path, opened file or decoded
output.

The raw descriptor codec argument supplies the prepared source argument by
moving its low halfword into the high halfword and adding the codec-kind tag in
unsigned DWORD arithmetic. This is not a conversion through the managed enum's
labels. Current authored raw values agree with the bank's Vorbis and Opus
source arguments under this rule; saved native source chains corroborate the
Vorbis conversion. The conditional implementation factory is now checked below,
while the selected live decoder and its lifetime remain unproved. The exact
operand declarations and bank/source joins live in
`wwise_source_queue_native.json`, not in a second native catalog.
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
SCHEMA = "endfield.wwise-source-queue-native.v5"
BRIDGE_ARGUMENT_NAMES = {
    "sourceSelector": {"anonymousNodePointer", "originalSourcePointer", "playbackBlobPointer"},
    "sourceClone": {"originalSourcePointer"},
    "sourceSetWideText": {"sourceThisPointer", "sourceLookupWord", "sourceArgumentWord24", "descriptorWideTextPointer"},
    "ownerFactory": {"sourceThisPointer"},
    "ownerConstructor": {"anonymousPrimaryOwnerPointer", "sourceThisPointer"},
}
BRIDGE_RETURN_KINDS = {
    "sourceSelector": "u32", "sourceClone": "pointer", "sourceSetWideText": "void",
    "ownerFactory": "pointer", "ownerConstructor": "pointer",
}
BRIDGE_LAYOUT_NAMES = {
    "playbackBlob": {"configInterfacePointer", "externalAllocationPointer", "contextPointer", "flagsWord", "serialWord"},
    "externalAllocation": {"count", "firstDescriptor", "descriptorStride"},
    "descriptor": {"matchWord", "argumentWord", "wideTextPointer", "memoryPointer", "byteCountWord", "selectionWord"},
    "source": {"matchWord", "dataPointer", "selectionArgumentWord", "cloneBytes"},
}

# Instruction encodings, not a second build-specific address/layout catalog.
SELECTION_IMMEDIATES = {
    "sourceArgumentMask": (b"\x25", 4),
    "externalArgumentTag": (b"\x3d", 4),
    "descriptorCodecShift": (b"\xc1\xe1", 1),
    "successStatus": (None, 4),
    "emptyStatus": (None, 4),
    "cloneFailureStatus": (None, 4),
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


def _address_entries(window: dict[str, Any]) -> list[dict[str, Any]]:
    additional = window.get("additionalEntries", [])
    if not isinstance(additional, list) or len(additional) > 7:
        _fail("queueAddressPointEntries", window.get("key", "dataWindow"), "at most7 additional bindings", additional)
    entries = ([window] if "entrySlot" in window else []) + additional
    slots: set[int] = set()
    for entry in entries:
        slot = entry.get("entrySlot") if isinstance(entry, dict) else None
        if type(slot) is not int:
            _fail("queueAddressPointSlot", window.get("key", "dataWindow"), "integer target slot", entry)
        if slot in slots:
            _fail("queueAddressPointEntries", window.get("key", "dataWindow"), "distinct integer target slots", entry)
        slots.add(slot)
    return entries


def load_queue_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract, _digest_value = read_reviewed_contract(
        path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-source-queue",
    )
    return contract


def _indirect_tail_instruction(encoded: bytes) -> bool:
    """Recognize a complete register or pointer-table FF /4 near JMP.

    Memory slots stay aligned and indexed entries stay pointer-sized. This
    establishes the leaf terminal only. Its target/interface identity still
    belongs to the owning contract's table and argument-flow bindings.
    """
    cursor = 0
    if encoded and 0x40 <= encoded[0] <= 0x4f:
        if encoded[0] & 4:  # The opcode-extension field is not a GP register.
            return False
        cursor = 1
    if len(encoded) < cursor + 2 or encoded[cursor] != 0xff:
        return False
    modrm = encoded[cursor + 1]
    if (modrm >> 3) & 7 != 4:
        return False
    cursor += 2
    mode, operand = modrm >> 6, modrm & 7
    if mode == 3:
        return cursor == len(encoded)
    displacement = 1 if mode == 1 else 4 if mode == 2 or operand == 5 else 0
    if operand == 4:
        if len(encoded) <= cursor:
            return False
        sib = encoded[cursor]
        cursor += 1
        if sib >> 6 != 3:  # Selected indirect tables contain pointer entries.
            return False
        if mode == 0 and sib & 7 == 5:
            displacement = 4
    if cursor + displacement != len(encoded):
        return False
    if displacement and not (mode == 0 and operand == 5):
        slot = int.from_bytes(encoded[cursor:], 'little', signed=True)
        if slot < 0 or slot % 8:
            return False
    return True


def validate_native_group_declarations(groups: Any) -> None:
    """Bound full native groups and completely covered unwindless leaves."""
    # Shared consumers include the voice graph plus dependency-owned groups.
    if not isinstance(groups, list) or not 1 <= len(groups) <= 96:
        _fail("queueGroups", "contract", "1..96 groups", len(groups) if isinstance(groups, list) else type(groups).__name__)
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
            kind = window.get("windowKind", "fullExceptionExtent")
            if kind in ("completeLeafThroughReturn", "completeLeafThroughTailDispatch", "completeLeafThroughIndirectTailDispatch"):
                limit = 512 if kind == "completeLeafThroughReturn" else 1024
                if len(windows) != 1 or start != entry or length > limit or "unwindRva" in window or "unwindInfoHex" in window:
                    _fail("queueLeafExtent", name, f"one entry leaf of at most{limit} bytes without unwind declarations", window)
            elif kind in ("fullExceptionExtent", "dispatchTableDataWithinExceptionGroup"):
                _rva(window.get("unwindRva"), name)
                _hex(window.get("unwindInfoHex"), name, 256)
            else:
                _fail("queueWindowKind", name, "exception extent, embedded dispatch table or complete leaf", kind)
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
        leaf_kind = windows[0].get("windowKind")
        if leaf_kind in ("completeLeafThroughReturn", "completeLeafThroughTailDispatch", "completeLeafThroughIndirectTailDispatch"):
            cursor = entry
            for witness in sorted(witnesses, key=lambda row: int(row["rva"], 16)):
                if int(witness["rva"], 16) != cursor:
                    _fail("queueLeafInstructionCoverage", name, hex(cursor), witness["rva"])
                cursor += len(bytes.fromhex(witness["instructionHex"]))
            terminal = max(witnesses, key=lambda row: int(row["rva"], 16))
            encoded_terminal = bytes.fromhex(terminal["instructionHex"])
            valid_terminal = (encoded_terminal == b"\xc3" if leaf_kind == "completeLeafThroughReturn" else
                              _indirect_tail_instruction(encoded_terminal) if leaf_kind == "completeLeafThroughIndirectTailDispatch" else
                              len(encoded_terminal) == 5 and encoded_terminal[:1] == b"\xe9")
            if cursor != entry + windows[0]["bodyLength"] or not valid_terminal:
                _fail("queueLeafReturnCoverage", name, "complete contiguous instructions ending in declared RET or tail dispatch", hex(cursor))


def validate_queue_declarations(contract: dict[str, Any]) -> None:
    """Bound declarations before byte reads; require every reviewed role once."""
    groups = contract.get("nativeGroups")
    validate_native_group_declarations(groups)
    names = {group["key"] for group in groups}
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
        for entry_binding in _address_entries(window):
            slot = entry_binding["entrySlot"]
            bridge_declaration = contract.get("sourceBridgeObserver")
            functions = bridge_declaration.get("functionRoles", {}) if isinstance(bridge_declaration, dict) else {}
            source_target = functions.get(entry_binding.get("targetGroup"), {}) if isinstance(functions, dict) else {}
            source_target = source_target if isinstance(source_target, dict) else {}
            if (type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > window["bytes"]
                    or window.get("module", "akSoundEngine") != "akSoundEngine"
                    or entry_binding.get("targetGroup") not in names and source_target.get("sourceContractRole") not in ("factory", "constructor")):
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
    validate_address_point_installations(contract)
    validate_source_selection_rules(contract)
    validate_bank_registration_rules(contract)


def validate_bank_registration_rules(contract: dict[str, Any]) -> None:
    """Bind the bank registration route to reviewed calls and one registry global."""
    registration = contract.get("bankRegistration")
    if registration is None:
        return
    if not isinstance(registration, dict):
        _fail("queueBankRegistration", "bankRegistration", "object", registration)
    groups = {group["key"]: group for group in contract["nativeGroups"]}

    def witness(binding: Any) -> dict[str, Any]:
        if not isinstance(binding, dict) or not isinstance(binding.get("group"), str) or binding["group"] not in groups:
            _fail("queueBankRegistrationGroup", "bankRegistration", "named native group", binding)
        found = next((row for row in groups[binding["group"]]["instructionWitnesses"]
                      if row["role"] == binding.get("witnessRole")), None)
        if found is None:
            _fail("queueBankRegistrationWitness", binding["group"], "named instruction witness", binding)
        return found

    edges = registration.get("directEdges")
    if not isinstance(edges, list) or not 1 <= len(edges) <= 32:
        _fail("queueBankRegistrationEdges", "bankRegistration", "1..32 direct edges", edges)
    for edge in edges:
        row = witness(edge)
        target_name, kind = edge.get("targetGroup"), edge.get("kind")
        target = groups.get(target_name) if isinstance(target_name, str) else None
        encoded = bytes.fromhex(row["instructionHex"])
        opcode = {"call": b"\xe8", "tailJump": b"\xe9"}.get(kind) if isinstance(kind, str) else None
        actual = int(row["rva"], 16) + 5 + struct.unpack_from("<i", encoded, 1)[0] if len(encoded) == 5 else None
        if target is None or opcode is None or encoded[:1] != opcode or actual != int(target["entryRva"], 16):
            _fail("queueBankRegistrationEdge", row["role"], edge.get("targetGroup"), actual)
    globals_ = registration.get("sharedRegistryWitnesses")
    if not isinstance(globals_, list) or not 2 <= len(globals_) <= 8:
        _fail("queueBankRegistryWitnesses", "bankRegistration", "2..8 registry loads", globals_)
    addresses = set()
    for binding in globals_:
        row = witness(binding)
        encoded = bytes.fromhex(row["instructionHex"])
        if len(encoded) != 7 or encoded[0] not in (0x48, 0x4c) or encoded[1] != 0x8b or encoded[2] & 0xc7 != 5:
            _fail("queueBankRegistryInstruction", row["role"], "MOV register, [RIP+disp32]", row["instructionHex"])
        addresses.add(int(row["rva"], 16) + 7 + struct.unpack_from("<i", encoded, 3)[0])
    if len(addresses) != 1:
        _fail("queueBankRegistryGlobal", "bankRegistration", "one shared registry global", [hex(at) for at in sorted(addresses)])
    table = registration.get("hircDispatch")
    if not isinstance(table, dict) or not isinstance(table.get("ownerGroup"), str) or table["ownerGroup"] not in groups:
        _fail("queueBankHircDispatch", "bankRegistration", "named dispatch owner", table)
    window = next((row for row in contract.get("dataWindows", []) if row.get("key") == table.get("dataWindow")), None)
    first, count = table.get("firstType"), table.get("entryCount")
    selected = table.get("selectedTypes")
    if (window is None or type(first) is not int or not 0 <= first <= 255 or type(count) is not int
            or not 1 <= count <= 256 - first or window["bytes"] != count * 4
            or not isinstance(selected, list) or not 1 <= len(selected) <= count):
        _fail("queueBankHircDispatchExtent", "bankRegistration", "bounded typed DWORD dispatch table", table)
    owner = groups[table["ownerGroup"]]
    start = int(window["rva"], 16)
    if not any(int(row["rva"], 16) <= start and start + count * 4 <= int(row["rva"], 16) + row["bodyLength"] for row in owner["windows"]):
        _fail("queueBankHircDispatchOwner", "bankRegistration", "table inside authenticated owner", window)
    seen = set()
    for branch in selected:
        if not isinstance(branch, dict) or type(branch.get("type")) is not int or not first <= branch["type"] < first + count or branch["type"] in seen:
            _fail("queueBankHircDispatchType", "bankRegistration", "distinct in-range object type", branch)
        seen.add(branch["type"])
        target = _rva(branch.get("targetRva"), "bankHircDispatch")
        if not any(int(row["rva"], 16) <= target < int(row["rva"], 16) + row["bodyLength"] for row in owner["windows"]):
            _fail("queueBankHircDispatchTargetExtent", "bankRegistration", "target inside authenticated owner", branch)


def validate_address_point_installations(contract: dict[str, Any]) -> None:
    """Bind each selected address point to its constructor's actual publication."""
    bindings = contract.get('addressPointInstallations', [])
    windows = {row['key']: row for row in contract.get('dataWindows', []) if 'entrySlot' in row}
    groups = {row['key']: row for row in contract['nativeGroups']}
    if not isinstance(bindings, list) or len(bindings) > 16:
        _fail('queueAddressPointInstallations', 'contract', 'bounded constructor bindings', bindings)
    covered = set()
    for binding in bindings:
        if not isinstance(binding, dict):
            _fail('queueAddressPointInstallation', 'contract', 'constructor binding', binding)
        key = binding.get('dataWindow')
        group = groups.get(binding.get('group'), {})
        witnesses = {row['role']: row for row in group.get('instructionWitnesses', [])}
        load, store = witnesses.get(binding.get('loadRole'), {}), witnesses.get(binding.get('storeRole'), {})
        point = windows.get(key)
        if point is None or key in covered or point.get('module', 'akSoundEngine') != 'akSoundEngine':
            _fail('queueAddressPointInstallation', str(key), 'distinct selected native address point', binding)
        covered.add(key)
        value = _selection_register(binding.get('valueRegister'))
        owner = _selection_register(binding.get('ownerRegister'))
        offset = binding.get('offset')
        encoded = bytes.fromhex(load.get('instructionHex', ''))
        expected_prefix = bytes((0x48 | (4 if value >= 8 else 0), 0x8d, 5 | ((value & 7) << 3)))
        if (len(encoded) != 7 or encoded[:3] != expected_prefix
                or int(load['rva'], 16) + 7 + struct.unpack_from('<i', encoded, 3)[0] != int(point['rva'], 16)):
            _fail('queueAddressPointLoad', str(key), 'RIP-relative LEA of declared address point', load)
        if type(offset) is not int or not 0 <= offset <= 127:
            _fail('queueAddressPointStoreOffset', str(key), 'bounded nonnegative displacement', offset)
        mode = 0x40 if offset or owner & 7 == 5 else 0
        expected = bytes((0x48 | (4 if value >= 8 else 0) | (1 if owner >= 8 else 0), 0x89,
                          mode | ((value & 7) << 3) | (owner & 7)))
        if owner & 7 == 4:
            expected += b'\x24'
        if mode:
            expected += bytes((offset,))
        if (bytes.fromhex(store.get('instructionHex', '')) != expected
                or int(store.get('rva', '0'), 16) < int(load['rva'], 16) + 7):
            _fail('queueAddressPointStore', str(key), 'publication from the declared loaded register', store)
    if covered != set(windows):
        _fail('queueAddressPointInstallationCoverage', 'contract', sorted(windows), sorted(covered))


def _selection_register(name: str) -> int:
    registers=['rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi',*[f'r{i}' for i in range(8,16)]]
    if name not in registers or name=='rsp':
        _fail('queueSelectionRegister','status/source register','ordinary GP register other than RSP',name)
    return registers.index(name)


def _selection_mov32(destination: str, source: str) -> bytes:
    dst,src=_selection_register(destination),_selection_register(source)
    rex=0x40|(4 if dst>=8 else 0)|(1 if src>=8 else 0)
    return (bytes((rex,)) if rex!=0x40 else b'')+bytes((0x8b,0xc0|((dst&7)<<3)|(src&7)))


def _selection_immediate32(register: str, value: int) -> bytes:
    reg=_selection_register(register)
    return (b'\x41' if reg>=8 else b'')+bytes((0xb8|(reg&7),))+value.to_bytes(4,'little')


def _selection_flow(selection: dict, witnesses: dict, groups: dict) -> None:
    statuses=selection.get('statusRegisters')
    if not isinstance(statuses,dict) or set(statuses)!={'successStatus','emptyStatus','cloneFailureStatus'}:
        _fail('queueSelectionStatusRegisters','externalSourceSelection','three declared status registers',statuses)
    common=statuses['emptyStatus'];success=statuses['successStatus']
    nonvolatile={'rbx','rbp','rsi','rdi','r12','r13','r14','r15'}
    if statuses['cloneFailureStatus']!=common or common not in nonvolatile or success not in nonvolatile:
        _fail('queueSelectionStatusRegisters','externalSourceSelection','nonnull/callee-preserved common and success registers',statuses)
    def require(role, expected):
        row=witnesses.get(role,{})
        actual=bytes.fromhex(row.get('instructionHex',''))
        if actual!=expected:_fail('queueSelectionFlowInstruction',role,expected.hex(),actual.hex())
        return _rva(row.get('rva'),role),actual
    one=selection.get('successConstantWitnesses')
    if (not isinstance(one,list) or len(one)!=3 or any(not isinstance(role,str) for role in one)
            or len(set(one))!=3 or selection['immediateWitnesses']['successStatus'] not in one):
        _fail('queueSelectionSuccessConstants','externalSourceSelection','three selected success producers',one)
    for role in one:require(role,_selection_immediate32(success,selection['values']['successStatus']))
    paths=selection.get('statusPaths')
    if (not isinstance(paths,list) or len(paths)!=2 or any(not isinstance(path,dict) for path in paths)
            or {path.get('callRole') for path in paths}!={'callMemorySourceSetter','callWideTextSourceSetter'}):
        _fail('queueSelectionStatusPaths','externalSourceSelection','memory and wide setter joins',paths)
    compare_role=selection.get('statusCompareRole');reg=_selection_register(common)
    value=selection['values']['successStatus']
    if not 0<=value<=127:_fail('queueSelectionStatusValue','successStatus','bounded positive CMP immediate',value)
    compare,_=require(compare_role,(b'\x41' if reg>=8 else b'')+bytes((0x83,0xf8|(reg&7),value)))
    require(selection.get('statusReturnRole'), _selection_mov32('rax', common))
    for path in paths:
        call=witnesses.get(path.get('callRole'),{});call_bytes=bytes.fromhex(call.get('instructionHex',''))
        if len(call_bytes)!=5 or call_bytes[0]!=0xe8:_fail('queueSelectionStatusCall','status path','direct setter call',call)
        at,raw=require(path.get('storeRole'),_selection_mov32(common,success))
        jump=witnesses.get(path.get('jumpRole'),{});branch=bytes.fromhex(jump.get('instructionHex',''));site=_rva(jump.get('rva'),'status jump')
        if (at!=int(call['rva'],16)+5 or site!=at+len(raw) or not (len(branch)==2 and branch[0]==0xeb or len(branch)==5 and branch[0]==0xe9)
                or site+len(branch)+int.from_bytes(branch[1:],'little',signed=True)!=compare):
            _fail('queueSelectionStatusJoin','status path','contiguous call/store/direct jump to status comparison',path)
    join=selection.get('wideSetterJoin',{});source=join.get('sourceRegister');base=_selection_register(source)
    # EDX <- source DWORD zero, then R8D <- ECX and RCX <- source pointer.
    prefix=(b'\x41' if base>=8 else b'')+b'\x8b'
    lookup=prefix+bytes(((0x40 if base&7==5 else 0)|0x10|(base&7),))
    if base&7==4:lookup+=b'\x24'
    if base&7==5:lookup+=b'\x00'
    sequence=[(join.get('lookupRole'),lookup),(join.get('argumentRole'),_selection_mov32('r8','rcx')),
              (join.get('sourceRole'),bytes((0x48|(1 if base>=8 else 0),0x8b,0xc8|(base&7))))]
    end=None
    for role,expected in sequence:
        at,raw=require(role,expected)
        if end is not None and at!=end:_fail('queueSelectionWideJoin',role,'contiguous final setter argument setup',hex(at))
        end=at+len(raw)
    call=witnesses.get(join.get('callRole'),{});raw=bytes.fromhex(call.get('instructionHex',''));target=groups.get(join.get('targetGroup'),{})
    if (len(raw)!=5 or raw[0]!=0xe8 or int(call.get('rva','0'),16)!=end
            or end+5+int.from_bytes(raw[1:],'little',signed=True)!=int(target.get('entryRva','0'),16)):
        _fail('queueSelectionWideJoin','setter call','direct common call after the selected source/word arguments',call)


def validate_source_selection_rules(contract: dict[str, Any]) -> None:
    """Tie the optional offline selection plan to authenticated operand bytes."""
    selection = contract.get("externalSourceSelection")
    if selection is None:
        return
    if not isinstance(selection, dict):
        _fail("queueSelectionRecord", "externalSourceSelection", "object", selection)
    groups = {group["key"]: group for group in contract["nativeGroups"]}
    group = groups.get(selection.get("selectorGroup"))
    values, bindings = selection.get("values"), selection.get("immediateWitnesses")
    if (group is None or not isinstance(values, dict) or set(values) != set(SELECTION_IMMEDIATES)
            or not isinstance(bindings, dict) or set(bindings) != set(SELECTION_IMMEDIATES)):
        _fail("queueSelectionOperands", "externalSourceSelection", "named group and complete operand bindings", selection)
    witnesses = {row["role"]: row for row in group["instructionWitnesses"]}
    for name, (prefix, width) in SELECTION_IMMEDIATES.items():
        value, witness = values[name], witnesses.get(bindings[name])
        if type(value) is not int or not 0 <= value < 1 << (width * 8) or witness is None:
            _fail("queueSelectionOperand", name, f"u{width * 8} with instruction witness", value)
    _selection_flow(selection,witnesses,groups)
    for name, (prefix, width) in SELECTION_IMMEDIATES.items():
        value, witness = values[name], witnesses[bindings[name]]
        expected = (prefix + value.to_bytes(width, "little") if prefix is not None else
                    _selection_immediate32(selection["statusRegisters"][name],value))
        if bytes.fromhex(witness["instructionHex"]) != expected:
            _fail("queueSelectionInstruction", name, expected.hex(), witness["instructionHex"])
    increment = witnesses.get(selection.get("codecIncrementWitness"))
    if increment is None or increment["instructionHex"] != "ffc1":
        _fail("queueSelectionCodecIncrement", "descriptor codec", "INC ECX", increment)
    if not 0 < values["descriptorCodecShift"] < 32 or values["externalArgumentTag"] & ~values["sourceArgumentMask"]:
        _fail("queueSelectionDomain", "externalSourceSelection", "nonzero shift below32 and tag inside mask", values)
    bank = selection.get("bankSourceBinding")
    if not isinstance(bank, dict) or set(bank) != {"loaderGroup", "readerGroup", "infoSetterMethod", "infoSetterCallWitness", "readOrder"}:
        _fail("queueBankSourceBinding", "externalSourceSelection", "complete named loader/reader/source-method join", bank)
    loader, reader = groups.get(bank["loaderGroup"]), groups.get(bank["readerGroup"])
    if loader is None or reader is None or not isinstance(bank["readOrder"], str) or not bank["readOrder"]:
        _fail("queueBankSourceGroups", "externalSourceSelection", "authenticated loader and reader groups", bank)
    call = next((row for row in loader["instructionWitnesses"] if row["role"] == bank["infoSetterCallWitness"]), None)
    if (not isinstance(bank["infoSetterMethod"], str) or not bank["infoSetterMethod"] or call is None
            or len(bytes.fromhex(call["instructionHex"])) != 5 or not call["instructionHex"].startswith("e8")):
        _fail("queueBankSourceSetterCall", "externalSourceSelection", "named source method and direct call witness", bank)
    reader_call = next((row for row in loader["instructionWitnesses"] if row["role"] == "callBankSourceReader"), None)
    if reader_call is None:
        _fail("queueBankSourceReaderCall", bank["loaderGroup"], "direct source-reader call", None)
    encoded = bytes.fromhex(reader_call["instructionHex"])
    target = (int(reader_call["rva"], 16) + 5 + struct.unpack_from("<i", encoded, 1)[0]
              if len(encoded) == 5 and encoded[0] == 0xe8 else None)
    if target != int(reader["entryRva"], 16):
        _fail("queueBankSourceReaderCall", bank["loaderGroup"], reader["entryRva"], target)


def _external_descriptor_plan(selection: dict[str, Any], source_argument: int, source_cookie: int,
                              descriptors: list[dict[str, int]], *, allocation_present: bool = True,
                              clone_succeeds: bool = True) -> dict[str, Any]:
    """Offline plan for the reviewed selector fragment, never a runtime join.

    Use only declarations from a successfully authenticated queue contract.
    A row ordinal refers to this supplied allocation, not to a media package.
    A selected setter route still permits path-copy allocation failure and does
    not establish provider, codec implementation, file, decode or audibility.
    """
    values = selection["values"]
    for name, value in (("source_argument", source_argument), ("source_cookie", source_cookie)):
        if type(value) is not int or not 0 <= value <= 0xffffffff:
            raise ValueError(f"{name} must be u32")
    if type(allocation_present) is not bool or type(clone_succeeds) is not bool:
        raise ValueError("allocation/clone conditions must be Boolean")
    if not isinstance(descriptors, list) or len(descriptors) > 4096:
        raise ValueError("bounded descriptor array required")
    fields = BRIDGE_LAYOUT_NAMES["descriptor"]
    for row in descriptors:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("complete descriptor fields required")
        for name, value in row.items():
            limit = 0xffffffffffffffff if name in ("wideTextPointer", "memoryPointer") else 0xffffffff
            if type(value) is not int or not 0 <= value <= limit:
                raise ValueError(f"descriptor {name} outside unsigned field width")
    result = {"descriptorOrdinal": None, "statusWord": values["successStatus"], "mode": "originalSource"}
    if source_argument & values["sourceArgumentMask"] != values["externalArgumentTag"]:
        return result
    if allocation_present and not clone_succeeds:
        return {**result, "statusWord": values["cloneFailureStatus"], "mode": "cloneAllocationFailed"}
    for ordinal, row in enumerate(descriptors if allocation_present else []):
        if row["matchWord"] != source_cookie:
            continue
        if row["selectionWord"]:
            mode = "wordAndOptionalWideText"
        elif row["wideTextPointer"]:
            mode = "wideText"
        elif row["byteCountWord"] and row["memoryPointer"]:
            mode = "memory"
        else:
            continue
        argument = ((row["argumentWord"] << values["descriptorCodecShift"]) + 1) & 0xffffffff
        return {**result, "descriptorOrdinal": ordinal, "mode": mode, "setterArgumentWord24": argument}
    return {**result, "statusWord": values["emptyStatus"], "mode": "noUsableDescriptor"}


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
        leaf = group["windows"][0].get("windowKind") in ("completeLeafThroughReturn", "completeLeafThroughTailDispatch", "completeLeafThroughIndirectTailDispatch")
        expected_starts = {int(win["rva"], 16) for win in group["windows"]}
        actual_starts = {start for start, owner in roots.items() if owner == entry}
        if leaf:
            end = entry + group["windows"][0]["bodyLength"]
            overlaps = [row for row in records.values() if row[0] < end and entry < row[1]]
            if overlaps:
                _fail("queueLeafPdataOverlap", name, "leaf outside exception extents", overlaps[:4])
        elif roots.get(entry) != entry or expected_starts != actual_starts:
            _fail("queueUnwindGroup", name, sorted(expected_starts), sorted(actual_starts))
        selected_bodies: dict[int, bytes] = {}
        for window in group["windows"]:
            start = int(window["rva"], 16)
            raw = image.bytes_at_va(image.image_base + start, window["bodyLength"]) if leaf else bodies.get(start)
            if raw is None or len(raw) != window["bodyLength"] or not leaf and records[start][1] - start != window["bodyLength"]:
                _fail("queueBodyExtent", name, window["bodyLength"], None if raw is None else len(raw))
            selected_bodies[start] = raw
            actual = hashlib.sha256(raw).hexdigest()
            if actual != window["bodySha256"].casefold():
                _fail("queueBodySha256", name, window["bodySha256"], actual)
            if not leaf:
                uw, _parent = unwind(records[start])
                if records[start][2] != int(window["unwindRva"], 16) or uw != bytes.fromhex(window["unwindInfoHex"]):
                    _fail("queueUnwindBytes", name, f"{window['unwindRva']}/{window['unwindInfoHex']}", f"{records[start][2]:x}/{uw.hex()}")
        for witness in group["instructionWitnesses"]:
            address, encoded = int(witness["rva"], 16), bytes.fromhex(witness["instructionHex"])
            window = next(win for win in group["windows"] if int(win["rva"], 16) <= address and address + len(encoded) <= int(win["rva"], 16) + win["bodyLength"])
            offset = address - int(window["rva"], 16)
            actual = selected_bodies[int(window["rva"], 16)][offset:offset + len(encoded)]
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
        for entry_binding in _address_entries(window):
            target = next((group for group in contract["nativeGroups"] if group["key"] == entry_binding["targetGroup"]), None)
            if target is None:
                target = (source_roles or {}).get(entry_binding["targetGroup"])
            if target is None:
                _fail("queueAddressPointDependency", window["key"], "authenticated existing source endpoint", entry_binding["targetGroup"])
            expected_pointer = image.image_base + int(target["entryRva"], 16)
            pointer = struct.unpack_from("<Q", raw, entry_binding["entrySlot"])[0]
            if pointer != expected_pointer:
                _fail("queueAddressPointTarget", window["key"], hex(expected_pointer), hex(pointer))
    registration = contract.get("bankRegistration")
    if registration is not None:
        dispatch = registration["hircDispatch"]
        window = next(row for row in contract["dataWindows"] if row["key"] == dispatch["dataWindow"])
        raw = image.bytes_at_va(image.image_base + int(window["rva"], 16), window["bytes"])
        for branch in dispatch["selectedTypes"]:
            actual = struct.unpack_from("<I", raw, (branch["type"] - dispatch["firstType"]) * 4)[0]
            if actual != int(branch["targetRva"], 16):
                _fail("queueBankHircDispatchTarget", str(branch["type"]), branch["targetRva"], hex(actual))
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
        if "externalSourceSelection" in contract:
            _fail("queueSelectionSourceDependency", "externalSourceSelection", "authenticated source bridge dependencies", None)
        return {}
    source = source_native.load_source_contract()
    source_native.validate_source_contract(source)
    if source["nativeInputs"] != contract["nativeInputs"]:
        _fail("queueSourceSelectedInputs", "source roles", contract["nativeInputs"], source["nativeInputs"])
    source_native.validate_source_bodies(source, bodies)
    source_native.validate_source_consumers(source, image, records)
    source_native.validate_source_transports(source, image, bodies)
    source_native.validate_managed_bridges(source, managed)
    selection = contract.get("externalSourceSelection")
    if selection is not None:
        binding = selection["bankSourceBinding"]
        method = next((row for row in source["methods"] if row["key"] == binding["infoSetterMethod"]), None)
        loader = next(group for group in contract["nativeGroups"] if group["key"] == binding["loaderGroup"])
        call = next(row for row in loader["instructionWitnesses"] if row["role"] == binding["infoSetterCallWitness"])
        actual = int(call["rva"], 16) + 5 + struct.unpack_from("<i", bytes.fromhex(call["instructionHex"]), 1)[0]
        if method is None or actual != int(method["rva"], 16):
            _fail("queueBankSourceSetterDependency", binding["infoSetterMethod"], None if method is None else method["rva"], hex(actual))
        binding = selection.get('memorySetterBinding', {})
        method = next((row for row in source['methods'] if row['key'] == binding.get('method')), None)
        selector = next(group for group in contract['nativeGroups'] if group['key'] == selection['selectorGroup'])
        call = next((row for row in selector['instructionWitnesses'] if row['role'] == binding.get('callRole')), {})
        encoded = bytes.fromhex(call.get('instructionHex', ''))
        actual = (int(call['rva'], 16) + 5 + struct.unpack_from('<i', encoded, 1)[0]
                  if len(encoded) == 5 and encoded[0] == 0xe8 else None)
        if method is None or actual != int(method['rva'], 16):
            _fail('queueMemorySourceSetterDependency', str(binding.get('method')), None if method is None else method['rva'], actual)
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
                        "sourceSetWideText": [next_instruction("callWideTextSourceSetter")],
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
        audit.update(status="validated", detail="selected Event/Action/source transport and conditional descriptor selection validated; runtime ownership/lifetime unresolved", nativeGroups=len(contract["nativeGroups"]), managedClaims=len(rows), resolvedSourceContractRoles=source_roles, evidenceBoundary=contract["evidenceBoundary"])
        if relation_spec:
            audit["sourceBridgeRelationSpec"] = relation_spec
        if "externalSourceSelection" in contract:
            audit["externalSourceSelection"] = {
                "status": "conditionalStaticSelection", **contract["externalSourceSelection"],
                "evidenceBoundary": "Bank-source word to descriptor selection and prepared source argument only; no observed Event branch, managed queue lifetime, provider/codec implementation, file open, decode or audibility.",
            }
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
