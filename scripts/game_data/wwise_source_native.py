"""Authenticate bounded Wwise source observer ABI on explicitly selected files.

The reviewed contract owns registers, structure spans and code witnesses. This
reader proves them before any observer profile is emitted; it never chooses a
game root or treats a historical SDK label as a current type-layout proof.
"""
from __future__ import annotations

import hashlib
import struct
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import NativeImage, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import runtime_type_name


CONTRACT_PATH = CONTRACTS_DIR / "wwise_source_native.json"
SCHEMA = "endfield.wwise-source-native.v4"
FIELD_WIDTHS = {"pointer": 8, "u32": 4}


class SourceContractError(ValueError):
    """A bounded expected-versus-actual native diagnostic."""

    def __init__(self, check: str, subject: str, expected: Any, actual: Any):
        self.diagnostic = {
            "failedCheck": check,
            "subject": subject,
            "expected": str(expected)[:160],
            "actual": str(actual)[:160],
        }
        super().__init__(f"{check} {subject}: expected {expected}; actual {actual}")


def load_source_contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    value, _digest = read_reviewed_contract(
        path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-source",
    )
    return value


def validate_source_contract(contract: dict[str, Any]) -> None:
    """Refuse malformed memory spans and ABI recipes before rendering an agent."""
    structures = contract.get("structures", {})
    if not isinstance(structures, dict) or not structures:
        raise SourceContractError("structures", "contract", "nonempty object", structures)
    for key, layout in structures.items():
        if not isinstance(layout, dict):
            raise SourceContractError("structureRecord", key, "object", type(layout).__name__)
        span = layout.get("captureBytes")
        fields = layout.get("fields")
        if type(span) is not int or not 0 < span <= 64 or not isinstance(fields, list) or not fields:
            raise SourceContractError("structureSpan", key, "1..64 bytes and fields", span)
        names: set[str] = set()
        occupied: set[int] = set()
        for field in fields:
            if not isinstance(field, dict):
                raise SourceContractError("fieldRecord", key, "object", type(field).__name__)
            name, offset, kind = field.get("name"), field.get("offset"), field.get("kind")
            width = FIELD_WIDTHS.get(kind, 0)
            if not isinstance(name, str) or not name or name in names:
                raise SourceContractError("fieldName", key, "unique nonempty name", name)
            if type(offset) is not int or offset < 0 or not width or offset + width > span:
                raise SourceContractError("fieldExtent", f"{key}.{name}", f"inside {span}", f"{offset}+{width}")
            extent = set(range(offset, offset + width))
            if occupied & extent:
                raise SourceContractError("fieldOverlap", f"{key}.{name}", "disjoint bytes", offset)
            occupied.update(extent)
            names.add(name)
        if occupied != set(range(span)):
            raise SourceContractError("structureCoverage", key, f"all {span} bytes", len(occupied))
    keys: set[str] = set()
    methods = contract.get("methods")
    if not isinstance(methods, list) or not methods:
        raise SourceContractError("methods", "contract", "nonempty list", type(methods).__name__)
    for method in methods:
        if not isinstance(method, dict):
            raise SourceContractError("methodRecord", "methods", "object", type(method).__name__)
        key = method.get("key")
        if not isinstance(key, str) or not key or key in keys:
            raise SourceContractError("methodKey", "methods", "unique nonempty key", key)
        keys.add(key)
        args = method.get("args", {})
        if not isinstance(args, dict) or not args or method.get("returnKind") != "void":
            raise SourceContractError("sourceAbi", key, "arguments and void result", method.get("returnKind"))
        indexes: set[int] = set()
        for name, arg in args.items():
            if not isinstance(arg, dict):
                raise SourceContractError("argumentRecord", f"{key}.{name}", "object", type(arg).__name__)
            index, kind = arg.get("index"), arg.get("kind")
            if type(index) is not int or not 0 <= index <= 3 or index in indexes or kind not in FIELD_WIDTHS:
                raise SourceContractError("argument", f"{key}.{name}", "unique register index 0..3 / pointer or u32", arg)
            indexes.add(index)
        if indexes != set(range(len(args))):
            raise SourceContractError("argumentCoverage", key, "contiguous argument indexes", sorted(indexes))
        observations = method.get("observe")
        if not isinstance(observations, list) or not observations:
            raise SourceContractError("observations", key, "nonempty list", type(observations).__name__)
        for observation in observations:
            if not isinstance(observation, dict):
                raise SourceContractError("observationRecord", key, "object", type(observation).__name__)
            index = observation.get("argIndex")
            if observation.get("structure") not in structures or not any(
                arg["index"] == index and arg["kind"] == "pointer" for arg in args.values()
            ):
                raise SourceContractError("observationBase", key, "known layout and pointer argument", observation)
    if not keys:
        raise SourceContractError("methods", "contract", "nonempty methods", 0)
    _validate_consumer_contract(contract)
    _validate_owner_transports(contract)
    _validate_managed_contract(contract)


def _validate_managed_contract(contract: dict[str, Any]) -> None:
    methods = contract.get("managedMethods")
    if not isinstance(methods, list) or not 1 <= len(methods) <= 8:
        raise SourceContractError("managedMethods", "contract", "1..8 full managed signatures", methods)
    for row in methods:
        if not isinstance(row, dict):
            raise SourceContractError("managedMethod", "contract", "object", row)
        parameters = row.get("parameters")
        if not isinstance(parameters, list) or not 1 <= len(parameters) <= 16:
            raise SourceContractError("managedSignature", row.get("name"), "1..16 complete parameters", parameters)
        names = set()
        for parameter in parameters:
            if (not isinstance(parameter, dict) or not isinstance(parameter.get("name"), str)
                    or not parameter["name"] or parameter["name"] in names
                    or not isinstance(parameter.get("type"), str) or not parameter["type"]):
                raise SourceContractError("managedParameterRecord", row.get("name"), "unique name and runtime type", parameter)
            names.add(parameter["name"])
        if type(row.get("static")) is not bool or not isinstance(row.get("returnType"), str):
            raise SourceContractError("managedSignature", row.get("name"), "staticness and runtime return type", row)
    enums = contract.get("managedEnumStorage")
    if not isinstance(enums, list) or not 1 <= len(enums) <= 8:
        raise SourceContractError("managedEnumStorage", "contract", "1..8 enum storage proofs", enums)
    names = set()
    for row in enums:
        if (not isinstance(row, dict) or type(row.get("typeDefinitionIndex")) is not int
                or row["typeDefinitionIndex"] < 0 or not isinstance(row.get("typeName"), str)
                or not row["typeName"] or row["typeName"] in names or row.get("parentType") != "System.Enum"
                or row.get("valueField") != "value__" or row.get("underlyingType") not in ("int", "uint")):
            raise SourceContractError("managedEnumStorageRecord", "contract", "unique enum with int/uint value__ storage", row)
        names.add(row["typeName"])


def _validate_consumer_contract(contract: dict[str, Any]) -> None:
    consumers = contract.get("consumers")
    if not isinstance(consumers, list) or len(consumers) > 8:
        raise SourceContractError("consumers", "contract", "list of at most 8", type(consumers).__name__)
    methods = {row["key"]: row for row in contract["methods"]}
    keys: set[str] = set()
    for row in consumers:
        if not isinstance(row, dict) or not isinstance(row.get("key"), str) or not row["key"] or row["key"] in keys:
            raise SourceContractError("consumerRecord", "consumers", "unique named object", row)
        key = row["key"]
        keys.add(key)
        callee = methods.get(row.get("calleeKey"))
        if callee is None:
            raise SourceContractError("consumerCallee", key, "reviewed source method", row.get("calleeKey"))
        if row.get("ownerArgument") != {"name": "anonymousCallerOwnerPointer", "index": 0, "kind": "pointer"}:
            raise SourceContractError("consumerOwnerArgument", key, "anonymous pointer in RCX", row.get("ownerArgument"))
        source, output = row.get("sourcePointerField", {}), row.get("outputReference", {})
        for field, index in ((source, 0), (output, 1)):
            if (not isinstance(field, dict) or type(field.get("offset")) is not int
                    or not 0 <= field["offset"] <= 0xffff or callee["args"].get(field.get("name")) != {"index": index, "kind": "pointer"}):
                raise SourceContractError("consumerField", key, "bounded field naming callee pointer argument", field)
        if output.get("structure") not in contract["structures"]:
            raise SourceContractError("consumerOutputLayout", key, "reviewed output structure", output.get("structure"))
        windows = row.get("windows")
        if not isinstance(windows, list) or not 1 <= len(windows) <= 16:
            raise SourceContractError("consumerWindows", key, "1..16 full exception extents", windows)
        starts: set[int] = set()
        extents: list[tuple[int, int]] = []
        total = 0
        roles: dict[str, tuple[int, bytes]] = {}
        for window in windows:
            if not isinstance(window, dict):
                raise SourceContractError("consumerWindow", key, "object", window)
            start, length = _consumer_rva(window.get("rva"), key, "windowRva"), window.get("bodyLength")
            if start in starts or type(length) is not int or not 0 < length <= 8192:
                raise SourceContractError("consumerWindowExtent", key, "unique start and 1..8192 bytes", f"{start}/{length}")
            if any(start < end and begin < start + length for begin, end in extents):
                raise SourceContractError("consumerWindowOverlap", key, "disjoint full extents", hex(start))
            starts.add(start)
            extents.append((start, start + length))
            total += length
            _consumer_rva(window.get("unwindRva"), key, "unwindRva")
            digest = window.get("bodySha256")
            if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                raise SourceContractError("consumerBodyHash", key, "SHA256 hex", digest)
            unwind = _consumer_hex(window.get("unwindInfoHex"), key, "consumerUnwindHex", 256)
            if not 4 <= len(unwind) <= 256:
                raise SourceContractError("consumerUnwindExtent", key, "4..256 bytes", len(unwind))
            witnesses = window.get("instructionWitnesses", [])
            if not isinstance(witnesses, list) or len(witnesses) > 4:
                raise SourceContractError("consumerWitnesses", key, "list of at most 4", witnesses)
            for witness in witnesses:
                if not isinstance(witness, dict):
                    raise SourceContractError("consumerWitness", key, "object", witness)
                role = witness.get("role")
                if not isinstance(role, str) or not role or role in roles:
                    raise SourceContractError("consumerWitnessRole", key, "unique role", role)
                offset = witness.get("bodyOffset")
                encoded = _consumer_hex(witness.get("instructionHex"), key, "consumerInstructionHex", 15)
                if type(offset) is not int or offset < 0 or not encoded or offset + len(encoded) > length:
                    raise SourceContractError("consumerInstructionExtent", key, f"inside {length}", f"{offset}+{len(encoded)}")
                roles[role] = (start + offset, encoded)
        entry = _consumer_rva(row.get("entryRva"), key, "entryRva")
        if total > 65536 or entry not in starts:
            raise SourceContractError("consumerExtent", key, "bounded group containing entry", total)
        call_rva = _consumer_rva(row.get("callRva"), key, "callRva")
        return_rva = _consumer_rva(row.get("returnRva"), key, "returnRva")
        target = _consumer_rva(callee.get("rva"), key, "calleeRva")
        if not -(1 << 31) <= target - return_rva < (1 << 31):
            raise SourceContractError("consumerCallDisplacement", key, "signed 32-bit direct call", target - return_rva)
        expected = {
            "entryOwnerRegister": (entry + 6, bytes.fromhex("488bf9")),
            "loadSourceArgument": (call_rva - 14, bytes.fromhex("488b8f") + struct.pack("<I", source["offset"])),
            "addressOutputArgument": (call_rva - 7, bytes.fromhex("488d97") + struct.pack("<I", output["offset"])),
            "callSourceLock": (call_rva, b"\xe8" + struct.pack("<i", target - return_rva)),
        }
        if return_rva != call_rva + 5 or roles != expected:
            raise SourceContractError("consumerDataFlowWitnesses", key, "entry owner/source load/output address/direct call", roles)


def _consumer_rva(value: Any, key: str, field: str) -> int:
    if (not isinstance(value, str) or not 3 <= len(value) <= 10 or not value.startswith("0x")
            or any(c not in "0123456789abcdefABCDEF" for c in value[2:])):
        raise SourceContractError("consumerRva", f"{key}.{field}", "bounded hexadecimal RVA", value)
    result = int(value, 16)
    if not 0 < result <= 0xffffffff:
        raise SourceContractError("consumerRva", f"{key}.{field}", "positive 32-bit RVA", value)
    return result


def _consumer_hex(value: Any, key: str, check: str, maximum: int) -> bytes:
    if (not isinstance(value, str) or len(value) > maximum * 2 or len(value) % 2
            or any(c not in "0123456789abcdefABCDEF" for c in value)):
        raise SourceContractError(check, key, f"at most {maximum} bytes as hex", value)
    return bytes.fromhex(value)


def _transport_roles(group: dict[str, Any], key: str) -> dict[str, tuple[int, bytes]]:
    if not isinstance(group.get("key"), str) or not group["key"]:
        raise SourceContractError("transportGroupKey", key, "nonempty group key", group.get("key"))
    windows = group.get("windows")
    if not isinstance(windows, list) or not 1 <= len(windows) <= 16:
        raise SourceContractError("transportWindows", key, "1..16 full exception extents", windows)
    starts: set[int] = set()
    roles: dict[str, tuple[int, bytes]] = {}
    extents: list[tuple[int, int]] = []
    for window in windows:
        if not isinstance(window, dict):
            raise SourceContractError("transportWindow", key, "object", window)
        start = _consumer_rva(window.get("rva"), key, "windowRva")
        length = window.get("bodyLength")
        if (type(length) is not int or not 0 < length <= 8192 or start in starts
                or any(start < end and begin < start + length for begin, end in extents)):
            raise SourceContractError("transportWindowExtent", key, "unique disjoint 1..8192 bytes", length)
        starts.add(start); extents.append((start, start + length))
        _consumer_rva(window.get("unwindRva"), key, "unwindRva")
        unwind = _consumer_hex(window.get("unwindInfoHex"), key, "transportUnwindHex", 256)
        digest = window.get("bodySha256")
        if len(unwind) < 4 or not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
            raise SourceContractError("transportWindowIdentity", key, "unwind record and SHA256", digest)
        witnesses = window.get("instructionWitnesses", [])
        if not isinstance(witnesses, list) or len(witnesses) > 12:
            raise SourceContractError("transportWitnesses", key, "at most 12 witnesses", witnesses)
        for witness in witnesses:
            if not isinstance(witness, dict):
                raise SourceContractError("transportWitness", key, "object", witness)
            role, offset = witness.get("role"), witness.get("bodyOffset")
            encoded = _consumer_hex(witness.get("instructionHex"), key, "transportInstructionHex", 15)
            if (not isinstance(role, str) or not role or role in roles or type(offset) is not int
                    or offset < 0 or not encoded or offset + len(encoded) > length):
                raise SourceContractError("transportWitnessExtent", key, "unique role inside full extent", witness)
            roles[role] = (start + offset, encoded)
    entry = _consumer_rva(group.get("entryRva"), key, "entryRva")
    if entry not in starts or sum(end - begin for begin, end in extents) > 65536:
        raise SourceContractError("transportGroupExtent", key, "bounded group containing entry", entry)
    return roles


def _relative32(target: int, next_instruction: int, key: str) -> bytes:
    displacement = target - next_instruction
    if not -(1 << 31) <= displacement < (1 << 31):
        raise SourceContractError("transportDisplacement", key, "signed 32-bit displacement", displacement)
    return struct.pack("<i", displacement)


def _validate_owner_transports(contract: dict[str, Any]) -> None:
    transports = contract.get("ownerTransports")
    if not isinstance(transports, list) or len(transports) > 8:
        raise SourceContractError("ownerTransports", "contract", "list of at most 8", transports)
    consumers = {row["key"]: row for row in contract["consumers"]}
    keys: set[str] = set()
    for row in transports:
        if not isinstance(row, dict) or not isinstance(row.get("key"), str) or not row["key"] or row["key"] in keys:
            raise SourceContractError("ownerTransportRecord", "contract", "unique named object", row)
        key = row["key"]; keys.add(key)
        consumer = consumers.get(row.get("consumerKey"))
        constructor, factory = row.get("constructor"), row.get("factory")
        if consumer is None or not isinstance(constructor, dict) or not isinstance(factory, dict):
            raise SourceContractError("transportEndpoints", key, "known consumer and constructor/factory", row.get("consumerKey"))
        if (constructor.get("ownerArgument") != {"name": "anonymousPrimaryOwnerPointer", "index": 0, "kind": "pointer"}
                or constructor.get("sourceArgument") != {"name": "sourceThisPointer", "index": 3, "kind": "pointer"}
                or factory.get("sourceArgument") != {"name": "sourceThisPointer", "index": 2, "kind": "pointer"}):
            raise SourceContractError("transportAbi", key, "constructor RCX owner/R9 source, factory R8 source", constructor.get("sourceArgument"))
        adjustment, stored = row.get("consumerOwnerOffset"), row.get("primarySourcePointerOffset")
        if (type(adjustment) is not int or not 0 < adjustment < 128 or type(stored) is not int
                or stored != adjustment + consumer["sourcePointerField"]["offset"] or stored > 0xffff):
            raise SourceContractError("transportOwnerAdjustment", key, "primary source member = consumer member + positive subobject offset", f"{adjustment}/{stored}")
        table = row.get("addressPointWindow")
        if not isinstance(table, dict):
            raise SourceContractError("transportDataWindow", key, "bounded address-point window", table)
        table_rva = _consumer_rva(table.get("rva"), key, "addressPointRva")
        size, slot, digest = table.get("bytes"), table.get("consumerEntrySlot"), table.get("sha256")
        if (type(size) is not int or not 8 <= size <= 4096 or type(slot) is not int or slot < 0
                or slot % 8 or slot + 8 > size or not isinstance(digest, str) or len(digest) != 64
                or any(c not in "0123456789abcdefABCDEF" for c in digest)):
            raise SourceContractError("transportDataExtent", key, "bounded aligned pointer slot and SHA256", f"{size}/{slot}/{digest}")
        roles = _transport_roles(constructor, key)
        expected = {
            "retainConstructorSource": bytes.fromhex("498be9"),
            "retainConstructorOwner": bytes.fromhex("488bf9"),
            "addressConsumerOwner": bytes.fromhex("4883c1") + bytes([adjustment]),
            "loadConsumerAddressPoint": bytes.fromhex("488d05") + _relative32(table_rva, roles.get("loadConsumerAddressPoint", (0, b""))[0] + 7, key),
            "storeConsumerAddressPoint": bytes.fromhex("488947") + bytes([adjustment]),
            "storeConstructorSource": bytes.fromhex("4889af") + struct.pack("<I", stored),
            "returnPrimaryOwner": bytes.fromhex("488bc7"),
        }
        if {name: encoded for name, (_rva, encoded) in roles.items()} != expected:
            raise SourceContractError("constructorTransportWitnesses", key, "owner/source retention, adjustment, address point, source store and return", roles)
        order = [roles[name][0] for name in expected]
        if order != sorted(order):
            raise SourceContractError("constructorTransportOrder", key, "retention before member writes before return", order)
        witness = row.get("consumerAdjustmentWitness", {})
        if not isinstance(witness, dict):
            raise SourceContractError("consumerAdjustmentWitness", key, "object", witness)
        witness_rva = _consumer_rva(witness.get("rva"), key, "consumerAdjustmentRva")
        encoded = _consumer_hex(witness.get("instructionHex"), key, "consumerAdjustmentHex", 15)
        if (encoded != bytes.fromhex("4c8d47") + struct.pack("<b", -adjustment)
                or not any(int(w["rva"], 16) <= witness_rva and witness_rva + len(encoded) <= int(w["rva"], 16) + w["bodyLength"] for w in consumer["windows"])):
            raise SourceContractError("consumerAdjustmentFlow", key, "authenticated consumer derives primary owner using same adjustment", witness)
        roles = _transport_roles(factory, key)
        constructor_rva = int(constructor["entryRva"], 16)
        expected = {"retainFactorySource": bytes.fromhex("498bf8"), "testStorageResult": bytes.fromhex("4885c0"),
                    "forwardFactorySource": bytes.fromhex("4c8bcf"), "passConstructorOwner": bytes.fromhex("488bc8"),
                    "callConstructor": b"\xe8" + _relative32(constructor_rva, roles.get("callConstructor", (0, b""))[0] + 5, key)}
        if {name: encoded for name, (_rva, encoded) in roles.items()} != expected:
            raise SourceContractError("factoryTransportWitnesses", key, "entry R8 retained/forwarded to R9 and storage result passed to constructor RCX", roles)
        order = [roles[name][0] for name in expected]
        if order != sorted(order):
            raise SourceContractError("factoryTransportOrder", key, "source retention/test/arguments/direct constructor call", order)


def _source_groups(contract: dict[str, Any]) -> list[dict[str, Any]]:
    return [*contract["consumers"], *(group for row in contract["ownerTransports"] for group in (row["constructor"], row["factory"]))]


def validate_source_bodies(contract: dict[str, Any], bodies: dict[int, bytes]) -> None:
    """Bind every source and support window to its exact PE exception extent."""
    for window in [*contract["methods"], *contract.get("supportWindows", []),
                   *(window for row in _source_groups(contract) for window in row["windows"])]:
        rva = int(window["rva"], 16)
        label = window.get("key", window["rva"])
        body = bodies.get(rva)
        if body is None or len(body) != window["bodyLength"]:
            raise SourceContractError("pdataExtent", label, window["bodyLength"], None if body is None else len(body))
        actual_hash = hashlib.sha256(body).hexdigest()
        if actual_hash.casefold() != window["bodySha256"].casefold():
            raise SourceContractError("bodySha256", label, window["bodySha256"], actual_hash)
        for witness in window.get("instructionWitnesses", []):
            offset = witness["bodyOffset"]
            encoded = bytes.fromhex(witness["instructionHex"])
            if type(offset) is not int or offset < 0 or not encoded or offset + len(encoded) > len(body):
                raise SourceContractError("instructionExtent", label, f"inside {len(body)}", f"{offset}+{len(encoded)}")
            actual = body[offset:offset + len(encoded)]
            if actual != encoded:
                raise SourceContractError("instructionBytes", label, encoded.hex(), actual.hex())


def _collect_source_image(path: Path, mapper: Any) -> tuple[Any, dict[int, bytes], dict[int, tuple[int, int, int]]]:
    """One selected PE supplies code extents, hashes and unwind identities."""
    image = mapper.PeImage(path)
    sections = [row for row in image.sections if row["name"] == ".pdata" and row["rawSize"]]
    if len(sections) != 1:
        raise SourceContractError("exceptionDirectory", path.name, "one stored .pdata", len(sections))
    section = sections[0]
    size = min(section["virtualSize"] or section["rawSize"], section["rawSize"])
    if not 12 <= size <= 4 * 1024 * 1024:
        raise SourceContractError("exceptionDirectoryExtent", path.name, "12..4194304 bytes", size)
    records: dict[int, tuple[int, int, int]] = {}
    for offset in range(0, size - 11, 12):
        row = struct.unpack_from("<III", image.buf, section["rawPointer"] + offset)
        if not row[0] or row[1] <= row[0]:
            continue
        if row[0] in records:
            raise SourceContractError("duplicateExceptionExtent", path.name, "unique start RVA", row[0])
        records[row[0]] = row
    bodies = {start: image.bytes_at_va(image.image_base + start, row[1] - start) for start, row in records.items()}
    return image, bodies, records


def _unwind_record(image: Any, row: tuple[int, int, int]) -> tuple[bytes, tuple[int, int, int] | None]:
    header = image.bytes_at_va(image.image_base + row[2], 4)
    version, flags, count = header[0] & 7, header[0] >> 3, header[2]
    if version not in (1, 2) or count > 64 or flags > 7 or (flags & 4 and flags & 3):
        raise SourceContractError("unwindHeader", hex(row[0]), "bounded x64 unwind header", header.hex())
    prefix_size = 4 + ((count + 1) // 2) * 4
    tail = 12 if flags & 4 else (4 if flags & 3 else 0)
    raw = image.bytes_at_va(image.image_base + row[2], prefix_size + tail)
    return raw, struct.unpack_from("<III", raw, prefix_size) if flags & 4 else None


def validate_source_consumers(contract: dict[str, Any], image: Any, records: dict[int, tuple[int, int, int]]) -> None:
    """Authenticate complete chained groups, never treating an interior segment as entry."""
    if not _source_groups(contract):
        return
    cache: dict[int, tuple[bytes, tuple[int, int, int] | None]] = {}

    def unwind(row: tuple[int, int, int]):
        if row[0] not in cache:
            cache[row[0]] = _unwind_record(image, row)
        return cache[row[0]]

    def root(row: tuple[int, int, int]) -> int:
        seen: set[int] = set()
        for _ in range(16):
            if row[0] in seen:
                raise SourceContractError("unwindChainCycle", hex(row[0]), "acyclic chain", sorted(seen))
            seen.add(row[0])
            _raw, parent = unwind(row)
            if parent is None:
                return row[0]
            if records.get(parent[0]) != parent:
                raise SourceContractError("unwindChainParent", hex(row[0]), "actual .pdata parent record", parent)
            row = parent
        raise SourceContractError("unwindChainDepth", hex(row[0]), "at most 16", 17)

    roots = {start: root(row) for start, row in records.items()}
    for consumer in _source_groups(contract):
        key, entry = consumer["key"], int(consumer["entryRva"], 16)
        declared = {int(row["rva"], 16) for row in consumer["windows"]}
        actual = {start for start, owner in roots.items() if owner == entry}
        if declared != actual or roots.get(entry) != entry:
            raise SourceContractError("consumerUnwindGroup", key, sorted(declared), sorted(actual))
        for window in consumer["windows"]:
            start = int(window["rva"], 16)
            record = records[start]
            if record[2] != int(window["unwindRva"], 16):
                raise SourceContractError("consumerUnwindRva", key, window["unwindRva"], hex(record[2]))
            raw, parent = unwind(record)
            if raw != bytes.fromhex(window["unwindInfoHex"]):
                raise SourceContractError("consumerUnwindBytes", key, window["unwindInfoHex"], raw.hex())
    for consumer in contract["consumers"]:
        key = consumer["key"]
        declared = {int(row["rva"], 16) for row in consumer["windows"]}
        call_rva, return_rva = int(consumer["callRva"], 16), int(consumer["returnRva"], 16)
        if not any(start <= call_rva and return_rva < records[start][1] for start in declared):
            raise SourceContractError("consumerCallExtent", key, "call and return inside authenticated extent", hex(call_rva))


def validate_source_transports(contract: dict[str, Any], image: Any, bodies: dict[int, bytes]) -> None:
    """Bind the anonymous address point and reverse this-adjustment to selected bytes."""
    consumers = {row["key"]: row for row in contract["consumers"]}
    for row in contract["ownerTransports"]:
        key, window = row["key"], row["addressPointWindow"]
        raw = image.bytes_at_va(image.image_base + int(window["rva"], 16), window["bytes"])
        if len(raw) != window["bytes"]:
            raise SourceContractError("transportDataReadExtent", key, window["bytes"], len(raw))
        digest = hashlib.sha256(raw).hexdigest()
        if digest != window["sha256"].casefold():
            raise SourceContractError("transportDataSha256", key, window["sha256"], digest)
        slot = window["consumerEntrySlot"]
        pointer = struct.unpack_from("<Q", raw, slot)[0]
        target = image.image_base + int(consumers[row["consumerKey"]]["entryRva"], 16)
        if pointer != target:
            raise SourceContractError("transportConsumerEntry", key, hex(target), hex(pointer))
        witness = row["consumerAdjustmentWitness"]
        rva, expected = int(witness["rva"], 16), bytes.fromhex(witness["instructionHex"])
        for extent in consumers[row["consumerKey"]]["windows"]:
            start = int(extent["rva"], 16)
            body = bodies[start]
            if start <= rva and rva + len(expected) <= start + len(body):
                actual = body[rva - start:rva - start + len(expected)]
                if actual != expected:
                    raise SourceContractError("consumerAdjustmentBytes", key, expected.hex(), actual.hex())
                break
        else:
            raise SourceContractError("consumerAdjustmentExtent", key, "inside reviewed consumer body", hex(rva))


def validate_managed_bridges(contract: dict[str, Any], image: NativeImage) -> None:
    """Prove full registered signatures, enum storage and selected native windows.

    Registered Il2CppType pointers supply the runtime names even when metadata's
    convenience name map has only an unresolved type-index placeholder.
    """
    type_cache: dict[int, tuple[str, int]] = {}

    def registered_type(index: int, subject: str) -> tuple[str, int]:
        if type(index) is not int or not 0 <= index < image.registration["typesCount"]:
            raise SourceContractError("managedRuntimeTypeIndex", subject,
                                      f"0..{image.registration['typesCount'] - 1}", index)
        if index not in type_cache:
            pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
            type_cache[index] = (runtime_type_name(image.pe, image.metadata, pointer), pointer)
        return type_cache[index]

    for row in contract["managedMethods"]:
        index = image.validate_method_row([
            row["methodIndex"], row["typeName"], row["methodName"], int(row["rva"], 16),
        ])
        method = image.metadata.methods[index]
        actual_static = bool(method.flags & 0x10)
        if actual_static != row["static"]:
            raise SourceContractError("managedStatic", row["name"], row["static"], actual_static)
        parameters = image.metadata.parameters_for(method)
        expected_count = len(row["parameters"])
        if method.parameter_count != expected_count or len(parameters) != expected_count:
            raise SourceContractError("managedParameterCount", row["name"], expected_count,
                                      f"declared={method.parameter_count}, framed={len(parameters)}")
        for ordinal, (expected, parameter) in enumerate(zip(row["parameters"], parameters)):
            actual = {"name": image.metadata.string(parameter.name_index),
                      "type": registered_type(parameter.type_index, row["name"])[0]}
            if actual != expected:
                raise SourceContractError("managedParameters", f"{row['name']}[{ordinal}]", expected, actual)
        actual_return = registered_type(method.return_type, row["name"])[0]
        if actual_return != row["returnType"]:
            raise SourceContractError("managedReturn", row["name"], row["returnType"], actual_return)
        image.check_windows([{
            "startRva": int(row["rva"], 16),
            "endRva": int(row["rva"], 16) + row["bodyLength"],
            "sha256": row["bodySha256"],
        }], gate="managed-bridge-window")
    for row in contract["managedEnumStorage"]:
        index = row["typeDefinitionIndex"]
        if not 0 <= index < len(image.metadata.types):
            raise SourceContractError("managedEnumTypeIndex", row["typeName"], "metadata definition in bounds", index)
        definition = image.metadata.types[index]
        actual_name = image.metadata.type_full_name(definition)
        if actual_name != row["typeName"]:
            raise SourceContractError("managedEnumIdentity", row["typeName"], row["typeName"], actual_name)
        if not definition.bitfield & 2:
            raise SourceContractError("managedEnumClassification", row["typeName"], "enum type-definition flag", definition.bitfield)
        parent = registered_type(definition.parent_index, row["typeName"])[0]
        if parent != row["parentType"]:
            raise SourceContractError("managedEnumParent", row["typeName"], row["parentType"], parent)
        fields = [field for field in image.metadata.fields_for(definition)
                  if image.metadata.string(field.name_index) == row["valueField"]]
        if len(fields) != 1:
            raise SourceContractError("managedEnumValueField", row["typeName"], "one value__ instance field", len(fields))
        actual_type, pointer = registered_type(fields[0].type_index, row["typeName"])
        attributes = struct.unpack("<H", image.pe.bytes_at_va(pointer + 8, 2))[0]
        if attributes & 0x10 or actual_type != row["underlyingType"]:
            raise SourceContractError("managedEnumBacking", row["typeName"],
                                      f"nonstatic {row['underlyingType']} value__", f"type={actual_type}, attrs={attributes:#x}")


def load_validated_source_contract(
    *, gameassembly: Path, metadata: Path, ak_sound_engine: Path,
    contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return no usable rows for absent, drifted or malformed selected inputs."""
    audit: dict[str, Any] = {"status": "missing", "contractPath": str(contract_path), "detail": ""}
    if any(path is None for path in (gameassembly, metadata, ak_sound_engine)):
        audit.update(detail="explicit selected GameAssembly.dll, metadata and AkSoundEngine.dll paths are required",
                     diagnostic={"failedCheck": "selectedInputs", "expected": "three explicit paths", "actual": "missing path"})
        return None, audit
    try:
        contract = load_source_contract(contract_path)
        validate_source_contract(contract)
        inputs = contract["nativeInputs"]
        gate = check_installed_native_inputs(
            inputs["gameAssemblySha256"], inputs["globalMetadataSha256"],
            gameassembly=gameassembly, metadata=metadata, require_metadata=True,
        )
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != "validated":
            return None, audit
        if not ak_sound_engine.is_file():
            audit.update(status="missing", detail=f"selected AkSoundEngine.dll not found: {ak_sound_engine}")
            return None, audit
        actual_size, actual_hash = ak_sound_engine.stat().st_size, sha256_file(ak_sound_engine)
        if actual_size != inputs["akSoundEngineFileSize"] or actual_hash.casefold() != inputs["akSoundEngineSha256"].casefold():
            raise SourceContractError("akSoundEngineInput", str(ak_sound_engine),
                                      f"{inputs['akSoundEngineFileSize']}/{inputs['akSoundEngineSha256']}",
                                      f"{actual_size}/{actual_hash}")
        image = NativeImage(gameassembly, metadata, label="wwise-source")
        source_image, bodies, records = _collect_source_image(ak_sound_engine, image.mapper)
        opened_hash = hashlib.sha256(source_image.buf).hexdigest()
        if opened_hash.casefold() != inputs["akSoundEngineSha256"].casefold():
            raise SourceContractError("openedAkSoundEngineInput", str(ak_sound_engine), inputs["akSoundEngineSha256"], opened_hash)
        validate_source_bodies(contract, bodies)
        validate_source_consumers(contract, source_image, records)
        validate_source_transports(contract, source_image, bodies)
        validate_managed_bridges(contract, image)
        audit.update(status="validated", detail="selected native source ABI and managed bridges validated",
                     sourceMethods=len(contract["methods"]), supportWindows=len(contract.get("supportWindows", [])),
                     sourceConsumers=len(contract["consumers"]), ownerTransports=len(contract["ownerTransports"]),
                     managedFullSignatures=len(contract["managedMethods"]), managedEnumStorage=len(contract["managedEnumStorage"]))
        return contract, audit
    except SourceContractError as exc:
        audit.update(status="mismatched", detail=str(exc), diagnostic=exc.diagnostic)
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        audit.update(status="mismatched", detail=str(exc)[:320], diagnostic={"failedCheck": "sourceContract", "actual": str(exc)[:320]})
    return None, audit
