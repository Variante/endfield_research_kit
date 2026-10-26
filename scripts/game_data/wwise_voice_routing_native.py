"""Authenticate source-route creation, bus admission, native mix and frame reset.

The voice pipeline supplies its authenticated contract and already opened image.
This module does not construct routes, decode PCM or initialize an audio device.
"""
from __future__ import annotations

import struct

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import read_reviewed_contract
from scripts.game_data import wwise_codec_factory_native as codec
from scripts.game_data.wwise_source_queue_native import (
    _hex, validate_native_group_declarations, validate_native_group_windows,
)
from scripts.game_data.wwise_voice_pipeline_native import _instruction

CONTRACT_PATH = CONTRACTS_DIR / "wwise_voice_routing_native.json"
SCHEMA = "endfield.wwise-voice-routing-native.v1"
DEPENDENCIES = ("contextFramePreparation", "routingPublication", "masterBusOutput")


def load_voice_routing_contract(path=CONTRACT_PATH):
    value, _ = read_reviewed_contract(path, schema=SCHEMA,
                                     status="reviewedCurrentBuild", label="wwise-voice-routing")
    return value


def collect_groups(contract, parent):
    expected = [{"key": key, "ownerContract": "wwise_voice_pipeline_native", "ownerGroup": key}
                for key in DEPENDENCIES]
    if contract.get("nativeGroupDependencies") != expected:
        codec._fail("voiceRoutingDependencies", "groups", expected, contract.get("nativeGroupDependencies"))
    if contract.get("nativeInputs") != parent.get("nativeInputs"):
        codec._fail("voiceRoutingInputs", "voice owner", "same selected native triplet", "different declarations")
    groups = list(contract["nativeGroups"])
    for row in expected:
        group = next((g for g in parent.get("nativeGroups", []) if g.get("key") == row["ownerGroup"]), None)
        if group is None:
            codec._fail("voiceRoutingOwnerMissing", row["key"], row["ownerGroup"], "missing owner group")
        groups.append({**group, "key": row["key"]})
    validate_native_group_declarations(groups)
    return groups


def validate_voice_routing_bytes(contract, image, bodies, records, parent):
    fail = codec._fail
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewedCurrentBuild":
        fail("voiceRoutingSchema", "contract", SCHEMA, contract.get("schema"))
    all_groups = collect_groups(contract, parent)
    validate_native_group_windows(all_groups, image, bodies, records)
    groups = {g["key"]: g for g in all_groups}
    for row in codec._rows(contract.get("directEdges"), "routing direct edges", 64):
        witness = codec._witness(groups, row.get("group"), row.get("witnessRole"))
        raw = bytes.fromhex(witness["instructionHex"])
        target = groups.get(row.get("targetGroup"))
        opcode = {"call": b"\xe8", "tailJump": b"\xe9"}.get(row.get("kind"))
        actual = int(witness["rva"], 16) + 5 + struct.unpack_from("<i", raw, 1)[0] if len(raw) == 5 else None
        if target is None or opcode is None or raw[:1] != opcode or actual != int(target["entryRva"], 16):
            fail("voiceRoutingEdge", witness["role"], row.get("targetGroup"), actual)
    layout = contract.get("layout")
    if not isinstance(layout, dict) or not layout or len(layout) > 64:
        fail("voiceRoutingLayout", "layout", "bounded named fields", layout)
    seen = set()
    for row in codec._rows(contract.get("fieldBindings"), "routing fields", 64):
        name, width = row.get("field"), row.get("displacementBytes")
        offset = layout.get(name) if isinstance(name, str) else None
        if type(width) is not int or width not in (1, 4) or type(offset) is not int or not 0 <= offset < 1 << (width * 8):
            fail("voiceRoutingFieldDeclaration", str(name), "bounded displacement", row)
        if name in seen:
            fail("voiceRoutingFieldDuplicate", name, "one field binding", name)
        seen.add(name)
        raw = _hex(row.get("prefixHex"), name, 10) + offset.to_bytes(width, "little")
        if row.get("suffixHex") != "":
            raw += _hex(row.get("suffixHex"), name, 10)
        actual = _instruction(image, groups, row.get("group"), row.get("rva"), len(raw))
        if actual != raw:
            fail("voiceRoutingField", name, raw.hex(), actual.hex())
    if seen != set(layout):
        fail("voiceRoutingFieldCoverage", "layout", sorted(layout), sorted(seen))


def validate_optional_voice_routing(image, bodies, records, parent):
    try:
        contract = load_voice_routing_contract()
        validate_voice_routing_bytes(contract, image, bodies, records, parent)
        return {"status": "validated", "detail": "conditional native route creation, bus admission/mix and frame reset validated",
                "selectedContractSchema": contract["schema"], "ownedNativeGroups": len(contract["nativeGroups"]),
                "nativeGroups": len(contract["nativeGroups"]) + len(contract["nativeGroupDependencies"]),
                "nativeGroupDependencies": contract["nativeGroupDependencies"], "evidenceBoundary": contract["evidenceBoundary"]}
    except codec.SourceContractError as error:
        return {"status": "mismatched", "detail": str(error)[:320], "diagnostic": error.diagnostic}
    except FileNotFoundError as error:
        return {"status": "missing", "detail": str(error)[:320]}
    except (OSError, ValueError, KeyError, TypeError, IndexError, AttributeError, OverflowError, StopIteration) as error:
        return {"status": "mismatched", "detail": str(error)[:320],
                "diagnostic": {"failedCheck": "voiceRouting", "actual": str(error)[:160]}}
