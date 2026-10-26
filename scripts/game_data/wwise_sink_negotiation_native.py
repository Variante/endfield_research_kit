"""Authenticate native sink format/service negotiation on an opened voice image.

This validator does not enumerate, activate or start an audio endpoint.
"""
from __future__ import annotations

import hashlib
import struct
import uuid

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_codec_factory_native as codec
from scripts.game_data.wwise_source_queue_native import (
    _digest, _hex, _rva, validate_native_group_declarations, validate_native_group_windows,
)
from scripts.game_data.wwise_voice_pipeline_native import _instruction

CONTRACT_PATH = CONTRACTS_DIR / "wwise_sink_negotiation_native.json"
SCHEMA = "endfield.wwise-sink-negotiation-native.v2"
DEPENDENCIES = ("sinkConstructor", "sinkServiceSetup")


def load_sink_negotiation_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path, schema=SCHEMA, status="reviewedCurrentBuild", label="wwise-sink-negotiation")
    return value


def collect_groups(contract, parent):
    expected = [{"key": key, "ownerContract": "wwise_voice_pipeline_native", "ownerGroup": key} for key in DEPENDENCIES]
    if contract.get("nativeGroupDependencies") != expected:
        codec._fail("sinkNegotiationDependencies", "groups", expected, contract.get("nativeGroupDependencies"))
    if contract.get("nativeInputs") != parent.get("nativeInputs"):
        codec._fail("sinkNegotiationInputs", "voice owner", "same selected native triplet", "different declarations")
    groups = list(contract["nativeGroups"])
    for row in expected:
        group = next((g for g in parent.get("nativeGroups", []) if g.get("key") == row["ownerGroup"]), None)
        if group is None:
            codec._fail("sinkNegotiationOwnerMissing", row["key"], row["ownerGroup"], "missing owner group")
        groups.append({**group, "key": row["key"]})
    validate_native_group_declarations(groups)
    return groups


def validate_sink_negotiation_bytes(contract, image, bodies, records, parent):
    fail = codec._fail
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("sinkNegotiationSchema", "contract", SCHEMA, contract.get("schema"))
    all_groups = collect_groups(contract, parent)
    validate_native_group_windows(all_groups, image, bodies, records)
    groups = {g["key"]: g for g in all_groups}
    for row in codec._rows(contract.get("directEdges"), "sink direct edges", 16):
        raw = _instruction(image, groups, row.get("group"), row.get("rva"), 5)
        target = groups.get(row.get("targetGroup"))
        actual = int(row["rva"], 16) + 5 + struct.unpack_from("<i", raw, 1)[0]
        if raw[:1] != b"\xe8" or target is None or actual != int(target["entryRva"], 16):
            fail("sinkNegotiationEdge", str(row.get("rva")), row.get("targetGroup"), hex(actual))
    expected = [{"key": "renderClientIid", "ownerContract": "wwise_voice_pipeline_native", "ownerDataWindow": "renderClientIid"}]
    if contract.get("dataWindowDependencies") != expected:
        fail("sinkNegotiationDataDependencies", "render IID", expected, contract.get("dataWindowDependencies"))
    data = list(contract["dataWindows"])
    for row in expected:
        owner = next((w for w in parent.get("dataWindows", []) if w.get("key") == row["ownerDataWindow"]), None)
        if owner is None:
            fail("sinkNegotiationDataOwnerMissing", row["key"], row["ownerDataWindow"], "missing window")
        data.append({**owner, "key": row["key"]})
    windows = {}
    for row in codec._rows(data, "sink data", 16):
        key, length = row.get("key"), row.get("bytes")
        if not isinstance(key, str) or not key or key in windows or type(length) is not int or not 1 <= length <= 256:
            fail("sinkNegotiationDataExtent", str(key), "unique bounded window", length)
        _digest(row.get("sha256"), key)
        raw = image.bytes_at_va(image.image_base + _rva(row.get("rva"), key), length)
        if raw != _hex(row.get("hex"), key, 256) or hashlib.sha256(raw).hexdigest() != row["sha256"]:
            fail("sinkNegotiationDataBytes", key, row["sha256"], hashlib.sha256(raw).hexdigest())
        windows[key] = (row, raw)
    subtype = contract.get("formatSubtypeBinding", {})
    key = subtype.get("dataWindow")
    if key not in windows or len(windows[key][1]) != 16 or uuid.UUID(bytes_le=windows[key][1]) != uuid.UUID(subtype["uuid"]):
        fail("sinkNegotiationSubtype", str(key), "checked IEEE-float subtype", subtype)
    raw = _instruction(image, groups, subtype.get("group"), subtype.get("loadRva"), 7)
    target = int(subtype["loadRva"], 16) + 7 + struct.unpack_from("<i", raw, 3)[0]
    if raw[:3] != b"\x0f\x10\x05" or target != int(windows[key][0]["rva"], 16):
        fail("sinkNegotiationSubtypeLoad", key, windows[key][0]["rva"], hex(target))
    seen = set()
    for row in codec._rows(contract.get("interfaces"), "sink interfaces", 8):
        key = row.get("dataWindow")
        if key not in windows or key in seen or len(windows[key][1]) != 16:
            fail("sinkNegotiationInterface", str(key), "unique checked GUID", row)
        seen.add(key)
        if uuid.UUID(bytes_le=windows[key][1]) != uuid.UUID(row["uuid"]):
            fail("sinkNegotiationInterfaceGuid", key, row["uuid"], windows[key][1].hex())
        raw = _instruction(image, groups, row.get("group"), row.get("iidLoadRva"), 7)
        target = int(row["iidLoadRva"], 16) + 7 + struct.unpack_from("<i", raw, 3)[0]
        if raw[:3] != b"\x48\x8d\x15" or target != int(windows[key][0]["rva"], 16):
            fail("sinkNegotiationInterfaceLoad", key, windows[key][0]["rva"], hex(target))
    for row in codec._rows(contract.get("comCalls"), "sink COM calls", 32):
        slot, width = row.get("slot"), row.get("slotBytes")
        if type(slot) is not int or not 0 <= slot <= 256 or slot % 8 or type(width) is not int or width != (0 if slot == 0 else 1 if slot < 128 else 4):
            fail("sinkNegotiationComSlot", str(row.get("method")), "bounded aligned COM slot and encoding width", row)
        raw = _hex(row.get("prefixHex"), str(row.get("method")), 4) + slot.to_bytes(width, "little")
        actual = _instruction(image, groups, row.get("group"), row.get("rva"), len(raw))
        if actual != raw:
            fail("sinkNegotiationComCall", str(row.get("method")), raw.hex(), actual.hex())
    for row in codec._rows(contract.get("channelTables"), "sink channel tables", 4):
        key, owner = row.get("dataWindow"), groups.get(row.get("group"))
        if key not in windows or len(windows[key][1]) != 32 or owner is None:
            fail("sinkNegotiationChannelTable", str(key), "eight checked DWORD targets and owner", row)
        actual = struct.unpack("<8I", windows[key][1])
        targets = row.get("targets")
        if not isinstance(targets, list) or len(targets) != 8:
            fail("sinkNegotiationChannelTargets", key, "eight declared branch targets", targets)
        expected = tuple(_rva(r, key) for r in targets)
        if len(expected) != 8 or actual != expected or any(not any(int(w["rva"], 16) <= r < int(w["rva"], 16) + w["bodyLength"] for w in owner["windows"]) for r in actual):
            fail("sinkNegotiationChannelTargets", key, list(expected), list(actual))
        raw = _hex(row.get("instructionPrefixHex"), key, 8) + int(windows[key][0]["rva"], 16).to_bytes(4, "little")
        instruction = _instruction(image, groups, row.get("group"), row.get("loadRva"), len(raw))
        if instruction != raw:
            fail("sinkNegotiationChannelLoad", key, raw.hex(), instruction.hex())


def validate_optional_sink_negotiation(image, bodies, records, parent):
    try:
        contract = load_sink_negotiation_contract()
        validate_sink_negotiation_bytes(contract, image, bodies, records, parent)
        return {"status": "validated", "detail": "conditional native sink format/service negotiation validated",
                "selectedContractSchema": contract["schema"], "ownedNativeGroups": len(contract["nativeGroups"]),
                "nativeGroups": len(contract["nativeGroups"]) + len(contract["nativeGroupDependencies"]),
                "nativeGroupDependencies": contract["nativeGroupDependencies"], "evidenceBoundary": contract["evidenceBoundary"]}
    except codec.SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320],
                "diagnostic": {"failedCheck": "sinkNegotiation", "actual": str(error)[:160]}}
