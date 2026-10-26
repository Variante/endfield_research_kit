"""Authenticate authored Sound properties and their native PCM consumers.

The codec gate supplies one already opened, authenticated image. This module
does not load a bank, decode audio, change engine state or activate a device.

Evidence and admission boundary:

The authored-parameter frontier must keep the bank loader ABI explicit. The
existing source-queue contract now witnesses its fifth Win64 argument: a stack
byte forwarded into the node-base remainder loader. A four-argument host
invocation leaves that byte undefined and is rejected as evidence. The
source-reader/setter receipts remain source-only; a positive loader result does
not establish that the stored parameter remainder was collected. The separate
`wwise_authored_parameters_native.json` contract and its validator now
authenticate inherited Sound construction, bank remainder loading, fixed/ranged
property storage, the Sound/base collectors, the native property-to-output slot
map and the selected filter and matrix/gain consumers. Existing source-queue,
voice and routing bodies and the Sound address point remain owned by their
original contracts. The optional codec gate checks these dependencies on the
same opened selected image and withholds claims when any child or native input
fails.

Fixed properties retain key bytes followed by aligned parallel float values.
The collector requires an in-range key and its output-mask bit before adding
the float into the mapped native slot. Volume feeds the context level path;
makeup gain feeds a distinct secondary source level before route-gain
preparation. Authored low/high-pass controls reach source filter state through
the original owner refresh and frame preparation. These are consumer reads, not
meanings inferred from a property-name match.

Physical Sound records now run through the original constructor and whole
loader with the explicit remainder argument enabled, then through original
own-property collection, source preparation/decoding, frame filters, route
creation/mix/reset and the negotiated finite sink. The decoded unfiltered
samples still match the prior native source cohort; authored gain and active
low-pass filtering change the submitted PCM. Every submitted sample value,
including padded frames and terminal gain transitions, agrees with an
independent reconstruction of the selected AVX/FMA matrix/gain arithmetic from
captured native filtered PCM and native route gains. Signed-zero bit
differences are recorded separately. The filter samples are original native
kernel output; an independent filter implementation is not claimed.

Padding precedes native filter processing. A filter can therefore emit its
retained history into a final padded block, and the original ending path can
fade the route target to zero across that block. Preserve the complete
submitted block separately from logical source-frame PCM. Neither a zero input
tail nor decoder end establishes a silent rendered tail.

Preserve constructor-established filter flags when enabling authored
collection. A helper write that forces the earlier bypass state discards
initialization/transition flags and is invalid for the authored filter cohort;
exploratory output produced under that write is rejected. The admitted helper
supplies only bounded allocator/free surfaces, including null reallocation, and
opaque object/play state, registry/topology/cache/arena availability, ordered
worker dispatch and finite endpoint/COM responses. It performs no sample
arithmetic and writes neither node policy nor filter-bypass flags.

The own-Sound cohort's registry deliberately has no parent or override bus.
Successful whole Sound loading can retain its own properties while leaving its
direct parent unlinked. The bank framing reader finds ActorMixer ancestry and
an explicit output-bus override in the root ancestor, so an empty-parent result
does not establish effective game gain or complete routing. Native parent/bus
construction, exact registry admission and recursive collection now have a
separate inherited cohort below. Effective output topology and runtime
object/RTPC/state/MIDI/random-range and effects selection, general filter
widths/transitions, resampling, concurrent lifetime and real endpoint
acceptance remain open. Earlier unit-gain receipts and the historical
constructor/skip-remainder frontier retain their own conditions; they do not
inherit these authored values.
"""
from __future__ import annotations

import hashlib
import re
import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_codec_factory_native as codec
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, _selection_register, validate_native_group_declarations, validate_native_group_windows,
)
from scripts.game_data.wwise_voice_pipeline_native import _instruction

CONTRACT_PATH = CONTRACTS_DIR / "wwise_authored_parameters_native.json"
SCHEMA = "endfield.wwise-authored-parameters-native.v2"
OWNERS = ("wwise_source_queue_native", "wwise_voice_pipeline_native", "wwise_voice_routing_native")


def load_authored_parameters_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-authored-parameters")
    return value


def collect_groups(contract, owners):
    groups = list(contract["nativeGroups"])
    for row in codec._rows(contract.get("nativeGroupDependencies"), "parameter dependencies", 32):
        key, owner_key = row.get("key"), row.get("ownerContract")
        owner = owners.get(owner_key) if owner_key in OWNERS else None
        if owner is None or contract.get("nativeInputs") != owner.get("nativeInputs"):
            codec._fail("authoredParameterOwnerInputs", str(owner_key), "same selected native triplet", "missing or different owner")
        group = next((g for g in owner.get("nativeGroups", []) if g.get("key") == row.get("ownerGroup")), None)
        if group is None or key != row.get("ownerGroup"):
            codec._fail("authoredParameterOwnerGroup", str(key), row.get("ownerGroup"), "missing or aliased group")
        groups.append(group)
    validate_native_group_declarations(groups)
    return groups


def collect_data(contract, owners):
    data = list(contract["dataWindows"])
    for row in codec._rows(contract.get("dataWindowDependencies"), "parameter data dependencies", 8):
        owner_key = row.get("ownerContract")
        owner = owners.get(owner_key) if owner_key in OWNERS else None
        if owner is None or contract.get("nativeInputs") != owner.get("nativeInputs"):
            codec._fail("authoredParameterDataOwner", str(owner_key), "same selected native triplet", "missing or different owner")
        window = next((w for w in owner.get("dataWindows", []) if w.get("key") == row.get("ownerDataWindow")), None)
        if window is None or row.get("key") != row.get("ownerDataWindow"):
            codec._fail("authoredParameterDataDependency", str(row.get("key")), row.get("ownerDataWindow"), "missing or aliased data")
        data.append(window)
    return data


def _mapped_memory(prefix, opcode, register, base, index=None, scale=0):
    """Encode the bounded register/memory forms used by property-map reads."""
    rex = 0x40 | (4 if register >= 8 else 0) | (1 if base >= 8 else 0)
    if index is not None and index >= 8:
        rex |= 2
    mode = 0x40 if base & 7 == 5 else 0
    sib = index is not None or base & 7 == 4
    raw = prefix + (bytes((rex,)) if rex != 0x40 else b'') + opcode
    raw += bytes((mode | ((register & 7) << 3) | (4 if sib else base & 7),))
    if sib:
        raw += bytes(((scale << 6) | ((index & 7 if index is not None else 4) << 3) | (base & 7),))
    return raw + (b'\x00' if mode else b'')


def validate_property_map_flow(mapping, image, groups, window):
    """Distinguish the authored byte-key loop from the later controller loop."""
    fail = codec._fail
    table, index, slot, key, output = (_selection_register(mapping.get(name)) for name in
                                     ('tableRegister','indexRegister','slotRegister','keyPointerRegister','outputRegister'))
    value = mapping.get('valueRegister')
    match = re.fullmatch(r'xmm([0-9]|1[0-5])', value) if isinstance(value, str) else None
    argument = mapping.get('outputArgumentIndex')
    if match is None or type(argument) is not int or not 0 <= argument <= 3:
        fail('authoredParameterMappingRegisters', 'property map', 'XMM value and register output argument', mapping)
    value = int(match[1])
    def require(field, expected):
        raw = _instruction(image, groups, mapping['group'], mapping.get(field), len(expected))
        if raw != expected:
            fail('authoredParameterMappingFlow', field, expected.hex(), raw.hex())
    lea_prefix = bytes((0x48 | (4 if table >= 8 else 0), 0x8d, 5 | ((table & 7) << 3)))
    reloads = mapping.get('tableReloadRvas')
    if not isinstance(reloads, list) or len(reloads) > 8:
        fail('authoredParameterMappingReloads', 'property map', 'bounded reload sites', reloads)
    sites = [mapping['loadRva'], *reloads]
    if len(set(sites)) != len(sites):
        fail('authoredParameterMappingReloads', 'property map', 'distinct table loads', sites)
    for at in sites:
        expected = lea_prefix + struct.pack('<i', _rva(window['rva'], 'property map') - _rva(at, 'table load') - 7)
        raw = _instruction(image, groups, mapping['group'], at, 7)
        if raw != expected:
            fail('authoredParameterMappingLoad', str(at), expected.hex(), raw.hex())
    require('keyLoadRva', _mapped_memory(b'', b'\x0f\xb6', index, key))
    require('rangeCheckRva', bytes((0x48 | (1 if index >= 8 else 0), 0x83, 0xf8 | (index & 7), len(mapping['slots']) - 1)))
    require('indexLoadRva', _mapped_memory(b'', b'\x8b', slot, table, index, 2))
    require('ignoredSlotCompareRva', (b'\x41' if slot >= 8 else b'') + bytes((0x83, 0xf8 | (slot & 7), mapping['ignoredSlot'])))
    source = (1,2,8,9)[argument]
    require('retainOutputRva', bytes((0x48 | (4 if output >= 8 else 0) | (1 if source >= 8 else 0), 0x8b,
                                    0xc0 | ((output & 7) << 3) | (source & 7))))
    require('addRva', _mapped_memory(b'\xf3', b'\x0f\x58', value, output, slot, 2))
    require('storeRva', _mapped_memory(b'\xf3', b'\x0f\x11', value, output, slot, 2))


def validate_authored_parameters_bytes(contract, image, bodies, records, owners):
    fail = codec._fail
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("authoredParameterSchema", "contract", SCHEMA, contract.get("schema"))
    all_groups = collect_groups(contract, owners)
    validate_native_group_windows(all_groups, image, bodies, records)
    groups = {g["key"]: g for g in all_groups}
    for row in codec._rows(contract.get("directEdges"), "parameter direct edges", 96):
        raw = _instruction(image, groups, row.get("group"), row.get("rva"), 5)
        opcode = {"call": b"\xe8", "tailJump": b"\xe9"}.get(row.get("kind"))
        target = groups.get(row.get("targetGroup"))
        actual = _rva(row.get("rva"), "edge") + 5 + struct.unpack_from("<i", raw, 1)[0]
        if opcode is None or raw[:1] != opcode or target is None or actual != _rva(target["entryRva"], "target"):
            fail("authoredParameterEdge", str(row.get("rva")), row.get("targetGroup"), hex(actual))
    seen = set()
    for row in codec._rows(contract.get("instructionBindings"), "parameter instruction bindings", 64):
        pair = (row.get("group"), row.get("rva"))
        raw = _hex(row.get("instructionHex"), str(pair), 15)
        actual = _instruction(image, groups, pair[0], pair[1], len(raw))
        if pair in seen or actual != raw:
            fail("authoredParameterInstruction", str(pair), raw.hex(), actual.hex())
        seen.add(pair)
    windows = {}
    for row in codec._rows(collect_data(contract, owners), "parameter data windows", 16):
        key, length = row.get("key"), row.get("bytes")
        if not isinstance(key, str) or not key or key in windows or type(length) is not int or not 1 <= length <= 4096:
            fail("authoredParameterDataExtent", str(key), "unique bounded data window", length)
        _digest(row.get("sha256"), key)
        raw = image.bytes_at_va(image.image_base + _rva(row.get("rva"), key), length)
        digest = hashlib.sha256(raw).hexdigest()
        if digest != row["sha256"]:
            fail("authoredParameterDataBytes", key, row["sha256"], digest)
        if "hex" in row and raw != _hex(row["hex"], key, 4096):
            fail("authoredParameterDataHex", key, row["hex"], raw.hex())
        windows[key] = (row, raw)
    for row in codec._rows(contract.get("virtualBindings"), "parameter virtual bindings", 16):
        key, slot = row.get("dataWindow"), row.get("slot")
        target = groups.get(row.get("targetGroup"))
        if key not in windows or type(slot) is not int or slot < 0 or slot % 8 or slot + 8 > len(windows[key][1]) or target is None:
            fail("authoredParameterVirtualDeclaration", str(key), "bounded slot and checked target", row)
        actual_target = struct.unpack_from("<Q", windows[key][1], slot)[0] - image.image_base
        if actual_target != _rva(target["entryRva"], "virtual target"):
            fail("authoredParameterVirtualTarget", str(slot), target["entryRva"], hex(actual_target))
        raw = _hex(row.get("instructionHex"), str(slot), 15)
        register = _selection_register(row.get('callRegister'))
        expected = (b'\x41' if register >= 8 else b'') + bytes((0xff, 0x90 | (register & 7)))
        if register & 7 == 4:
            expected += b'\x24'
        expected += slot.to_bytes(4, "little")
        if raw != expected or _instruction(image, groups, row.get("group"), row.get("rva"), len(raw)) != raw:
            fail("authoredParameterVirtualCall", str(slot), expected.hex(), raw.hex())
    mapping = contract.get("propertyMapping", {})
    key = mapping.get("dataWindow")
    if key not in windows:
        fail("authoredParameterMappingWindow", str(key), "checked property map", "absent")
    raw_map = windows[key][1]
    slots = mapping.get("slots")
    if not isinstance(slots, list) or not 1 <= len(slots) <= 64 or len(raw_map) != len(slots) * 4:
        fail("authoredParameterMappingExtent", str(key), "bounded DWORD slot map", slots)
    actual_slots = list(struct.unpack("<" + str(len(slots)) + "I", raw_map))
    ignored = mapping.get("ignoredSlot")
    if type(ignored) is not int or not 1 <= ignored <= 64 or any(type(slot) is not int or not 0 <= slot <= ignored for slot in slots) or actual_slots != slots or mapping.get("outputSlotBytes") != 4:
        fail("authoredParameterMappingSlots", str(key), slots, actual_slots)
    raw = _instruction(image, groups, mapping.get("group"), mapping.get("loadRva"), 7)
    prefix = _hex(mapping.get("instructionPrefixHex"), "mapping prefix", 3)
    address = _rva(mapping.get("loadRva"), "mapping load") + 7 + struct.unpack_from("<i", raw, 3)[0]
    table = _selection_register(mapping.get('tableRegister'))
    expected_prefix = bytes((0x48 | (4 if table >= 8 else 0), 0x8d, 5 | ((table & 7) << 3)))
    if prefix != expected_prefix or raw[:3] != prefix or address != _rva(windows[key][0]["rva"], key):
        fail("authoredParameterMappingLoad", str(key), windows[key][0]["rva"], hex(address))
    validate_property_map_flow(mapping, image, groups, windows[key][0])
    seen = set()
    for row in codec._rows(mapping.get("properties"), "named parameter mappings", 32):
        prop, offset = row.get("id"), row.get("outputByteOffset")
        if type(prop) is not int or not 0 <= prop < len(slots) or prop in seen or type(offset) is not int or slots[prop] == ignored or offset != slots[prop] * 4:
            fail("authoredParameterMappingProperty", str(row.get("name")), "unique mapped native output offset", row)
        seen.add(prop)
    for row in codec._rows(contract.get("jumpTableBindings"), "parameter jump tables", 8):
        key, owner = row.get("dataWindow"), groups.get(row.get("group"))
        targets, selected = row.get("targets"), row.get("selectedIndex")
        if key not in windows or owner is None or not isinstance(targets, list) or not 1 <= len(targets) <= 32 or len(windows[key][1]) != len(targets) * 4 or type(selected) is not int or not 0 <= selected < len(targets):
            fail("authoredParameterJumpDeclaration", str(key), "bounded table and selected branch", row)
        expected = [_rva(t, key) for t in targets]
        actual = list(struct.unpack("<" + str(len(targets)) + "I", windows[key][1]))
        if actual != expected or any(not any(_rva(w["rva"], key) <= t < _rva(w["rva"], key) + w["bodyLength"] for w in owner["windows"]) for t in actual):
            fail("authoredParameterJumpTargets", key, expected, actual)
        raw = _hex(row.get("instructionPrefixHex"), key, 8) + _rva(windows[key][0]["rva"], key).to_bytes(4, "little")
        if _instruction(image, groups, row.get("group"), row.get("loadRva"), len(raw)) != raw:
            fail("authoredParameterJumpLoad", key, raw.hex(), "different operand")
        call_at = _rva(row.get("selectedCallRva"), key)
        if not expected[selected] <= call_at < expected[selected] + 32:
            fail("authoredParameterJumpSelectedBranch", key, "call inside selected short branch", hex(call_at))
        raw = _instruction(image, groups, row.get("group"), row.get("selectedCallRva"), 5)
        target = groups.get(row.get("targetGroup"))
        actual_target = call_at + 5 + struct.unpack_from("<i", raw, 1)[0]
        if raw[:1] != b"\xe8" or target is None or actual_target != _rva(target["entryRva"], key):
            fail("authoredParameterJumpSelectedCall", key, row.get("targetGroup"), hex(actual_target))


def validate_optional_authored_parameters(image, bodies, records, voice, queue, routing):
    try:
        contract = load_authored_parameters_contract()
        owners = dict(zip(OWNERS, (queue, voice, routing)))
        validate_authored_parameters_bytes(contract, image, bodies, records, owners)
        return {"status": "validated", "detail": "conditional authored Sound property collection, filter and gain consumers validated",
                "selectedContractSchema": contract["schema"], "ownedNativeGroups": len(contract["nativeGroups"]),
                "nativeGroups": len(contract["nativeGroups"]) + len(contract["nativeGroupDependencies"]),
                "nativeGroupDependencies": contract["nativeGroupDependencies"], "evidenceBoundary": contract["evidenceBoundary"]}
    except codec.SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320],
                "diagnostic": {"failedCheck": "authoredParameters", "actual": str(error)[:160]}}
