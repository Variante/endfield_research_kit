"""Authenticate reviewed native programs, identities and linked witnesses.

Contracts own every build-specific declaration. Hashes authenticate reviewed
instructions; they do not discover arithmetic or claim that a live path ran.
Callers must gate the selected native pair before invoking this validator.
"""
from __future__ import annotations

import re
import struct
from typing import Any

from scripts.game_data.il2cpp import protocol


def rva(value: str) -> int:
    if not isinstance(value, str) or re.fullmatch(r"0x[0-9a-f]+", value) is None:
        raise ValueError(f"contract-rva={value!r}")
    return int(value, 16)


def relative_target(image, site: int, opcode: bytes, width: int = 4) -> int:
    if width not in (1, 4):
        raise ValueError(f"invalid-relative-width={width}")
    raw = image.pe.bytes_at_va(image.pe.image_base + site, len(opcode) + width)
    if raw[:len(opcode)] != opcode:
        raise ValueError(f"native-opcode={site:#x}:expected={opcode.hex()}:actual={raw.hex()}")
    return site + len(raw) + int.from_bytes(raw[len(opcode):], "little", signed=True)


def runtime_type(image, index: int) -> str:
    if not 0 <= index < int(image.registration["typesCount"]):
        raise ValueError(f"native-type-index={index}")
    pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    if not pointer:
        raise ValueError(f"native-type-pointer={index}")
    return protocol.runtime_type_name(image.pe, image.metadata, pointer)


def validate(image, contract: dict[str, Any], *, label: str) -> dict[str, Any]:
    if contract.get("programVersion") != 1:
        raise ValueError(f"{label}.contract:program-version")
    methods = contract["methods"]
    if not methods or set(methods) != set(contract["signatures"]):
        raise ValueError(f"{label}.contract:method-signature-set")
    resolved = {}
    for role, row in methods.items():
        image.validate_method_row([*row[:3], rva(row[3])], label=label)
        resolved[role] = rva(row[3])
        method = image.metadata.methods[row[0]]
        signature = {"parameters": [[image.metadata.string(p.name_index), runtime_type(image, p.type_index)]
                                    for p in image.metadata.parameters_for(method)],
                     "returnType": runtime_type(image, method.return_type),
                     "static": bool(method.flags & 0x10),
                     "byrefParameters": [image.metadata.string(p.name_index)
                         for p in image.metadata.parameters_for(method)
                         if image.pe.bytes_at_va(image.pe.u64_at_va(
                             int(image.registration["types"], 16) + p.type_index * 8), 16)[11] & 0x20]}
        if signature != contract["signatures"][role]:
            raise ValueError(f"{label}.native:signature={role}:expected={contract['signatures'][role]!r}:actual={signature!r}")
    owners = {image.metadata.type_full_name(t): t for t in image.metadata.types}
    for owner_name, name, type_name, offset, token in contract["fields"]:
        owner = owners[owner_name]
        fields = [f for f in image.metadata.fields_for(owner) if image.metadata.string(f.name_index) == name]
        if len(fields) != 1:
            raise ValueError(f"{label}.native:field-count={owner_name}.{name}:{len(fields)}")
        field = fields[0]
        offsets = protocol.runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
        actual = [runtime_type(image, field.type_index), offsets.get(name), f"0x{field.token:08x}"]
        if actual != [type_name, offset, token]:
            raise ValueError(f"{label}.native:field={owner_name}.{name}:expected={[type_name, offset, token]!r}:actual={actual!r}")
    defaults = protocol.field_defaults(image.metadata)
    for type_name, name, value, token in contract["enumMembers"]:
        members = protocol.native_enum_members(image.metadata, defaults, image.pe, image.registration, type_name)
        matches = [m for m in members if m["name"] == name]
        if len(matches) != 1 or [matches[0]["id"], matches[0]["token"]] != [value, token]:
            raise ValueError(f"{label}.native:enum={type_name}.{name}:expected={[value, token]!r}:actual={matches!r}")
    windows = [{**w, "startRva": rva(w["startRva"]), "endRva": rva(w["endRva"])}
               for w in contract["codeWindows"]]
    if not windows or any(w["startRva"] >= w["endRva"] for w in windows):
        raise ValueError(f"{label}.contract:code-windows")
    image.check_windows(windows, label=label)

    def covered(site: int, count: int) -> None:
        if not any(w["startRva"] <= site < site + count <= w["endRva"] for w in windows):
            raise ValueError(f"{label}.contract:witness-outside-reviewed-windows={site:#x}+{count}")

    for role in contract["entryRoles"]:
        if not any(w["startRva"] == resolved[role] for w in windows):
            raise ValueError(f"{label}.contract:missing-reviewed-entry={role}")
    for row in contract["instructionWindows"]:
        covered(rva(row[0]), len(bytes.fromhex(row[1])))
    image.check_instruction_windows([[rva(row[0]), row[1], row[2]] for row in contract["instructionWindows"]], label=label)
    for call in contract["calls"]:
        site = rva(call["siteRva"])
        opcode = bytes.fromhex(call.get("opcode", "e8"))
        covered(site, len(opcode) + 4)
        expected = resolved[call["method"]]
        actual = relative_target(image, site, opcode)
        if actual != expected:
            raise ValueError(f"{label}.native:call-target={site:#x}:expected={expected:#x}:actual={actual:#x}")
    for branch in contract["branches"]:
        site = rva(branch["siteRva"])
        opcode = bytes.fromhex(branch["opcode"])
        width = branch["displacementBytes"]
        covered(site, len(opcode) + width)
        actual = relative_target(image, site, opcode, width)
        if actual != rva(branch["targetRva"]):
            raise ValueError(f"{label}.native:branch-target={site:#x}:expected={branch['targetRva']}:actual={actual:#x}")
    for address in contract["addressTargets"]:
        site = rva(address["siteRva"])
        raw = bytes.fromhex(address["instructionBytes"])
        covered(site, len(raw))
        actual = image.pe.bytes_at_va(image.pe.image_base + site, len(raw))
        if actual != raw:
            raise ValueError(f"{label}.native:address-instruction={site:#x}")
        target = site + len(raw) + struct.unpack_from("<i", raw, len(raw) - 4)[0]
        if target != resolved[address["method"]]:
            raise ValueError(f"{label}.native:address-target={site:#x}")
    for literal in contract["literals"]:
        site = rva(literal["siteRva"])
        raw = bytes.fromhex(literal["instructionBytes"])
        covered(site, len(raw))
        actual = image.pe.bytes_at_va(image.pe.image_base + site, len(raw))
        if actual != raw:
            raise ValueError(f"{label}.native:literal-instruction={site:#x}")
        target = site + len(raw) + struct.unpack_from("<i", raw, literal["displacementOffset"])[0]
        if target != rva(literal["targetRva"]):
            raise ValueError(f"{label}.native:literal-target={site:#x}")
        fmt = {"float32": "<f", "float64": "<d"}[literal["type"]]
        actual = struct.unpack(fmt, image.pe.bytes_at_va(image.pe.image_base + target, struct.calcsize(fmt)))[0]
        if actual != literal["value"]:
            raise ValueError(f"{label}.native:literal-value={site:#x}:expected={literal['value']}:actual={actual}")
    return {"methods": methods, "fields": contract["fields"], "codeWindows": contract["codeWindows"],
            "callSites": len(contract["calls"]), "branchSites": len(contract["branches"]),
            "instructionWitnesses": len(contract["instructionWindows"])}
