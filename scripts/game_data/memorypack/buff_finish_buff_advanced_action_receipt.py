"""Selected-build named wrapper receipt for BuffData FinishBuffAdvanced actions.

The existing Buff parser closes the physical 0x00B4 action anonymously. This
adapter names only the thirteen wrapper slots after authenticating the selected
native route, setter order, source readers, logical file hash and action end.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR


LABEL = "buffFinishBuffAdvancedActionReceipt"
CONTRACT_PATH = CONTRACTS_DIR / "buff_finish_buff_advanced_action_receipt_native.json"
SCHEMA = "endfield.buff-finish-buff-advanced-action-receipt.v1"
TAG = 0x00B4


@lru_cache(maxsize=1)
def _contract() -> dict[str, Any]:
    contract, _digest = read_reviewed_contract(
        CONTRACT_PATH,
        schema="endfield.buff-finish-buff-advanced-action-receipt-native-contract.v1",
        label=LABEL,
        status="exact-current-build",
    )
    return contract


@lru_cache(maxsize=1)
def _dependencies() -> tuple[dict[str, Any], dict[str, Any]]:
    contract = _contract()
    source = json.loads((CONTRACTS_DIR / contract["sourceContract"]).read_bytes())
    catalog = json.loads((CONTRACTS_DIR / contract["catalogContract"]).read_bytes())
    routes = catalog["families"]["AbilityActionData"]
    route = routes[TAG]
    wrapper = contract["wrapper"]
    if (
        source.get("schemaVersion") != 1
        or tuple(source.get("anonymousReadOrder", {}).get("member13", ()))
        != tuple(contract["orderedReadKinds"])
        or len(contract["orderedReadKinds"]) != wrapper["serializedMemberCount"]
        or len(wrapper["inheritedSetterMethods"]) + len(wrapper["setterMethods"])
        != wrapper["serializedMemberCount"]
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or catalog["nativeInputs"]["gameAssemblySha256"]
        != contract["nativeInputs"]["GameAssembly.dll"]
        or catalog["nativeInputs"]["metadataSha256"]
        != contract["nativeInputs"]["global-metadata.dat"]
        or route["tag"] != TAG
        or route["wrapperName"] != wrapper["typeName"]
        or route["wrappedType"] != contract["wrappedType"]
        or route["memberCount"] != wrapper["serializedMemberCount"]
        or catalog["switches"]["AbilityActionData"]["entryCount"] != len(routes)
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the selected route, generated setters, and source profile."""
    contract = _contract()
    source, _catalog = _dependencies()
    expected = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    unityplayer = gate.gameassembly.parent / "UnityPlayer.dll"
    if (
        not unityplayer.is_file()
        or hashlib.sha256(unityplayer.read_bytes()).hexdigest().upper()
        != expected["UnityPlayer.dll"]
    ):
        raise ValueError(f"{LABEL}.native:UnityPlayer.dll:missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    image.validate_dispatcher(contract["dispatcher"], label=LABEL)
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows([*source["codeWindows"], *source["dataWindows"]], label=LABEL)
    for context in source["nestedContexts"]:
        instruction = image.pe.bytes_at_va(
            image.pe.image_base + context["instructionRva"], 7
        )
        if (
            instruction.hex().upper() != context["instructionHex"].upper()
            or instruction[:2] != b"\x48\x8b"
            or instruction[2] not in (0x15, 0x35)
        ):
            raise ValueError(f"{LABEL}.native:nested-instruction")
        cell = (
            image.pe.image_base + context["instructionRva"] + 7
            + struct.unpack_from("<i", instruction, 3)[0]
        )
        if (
            cell != context["cellVa"]
            or image.pe.bytes_at_va(cell, 8).hex().upper()
            != context["usageRawHex"].upper()
        ):
            raise ValueError(f"{LABEL}.native:nested-usage")
    wrapper = contract["wrapper"]
    owner = image.check_wrapper_inheritance(wrapper, label=LABEL)
    parent = image.metadata.types[wrapper["parentTypeDefinition"]]
    if (
        image.setter_methods(parent, parameter="typeName", label=LABEL)
        != wrapper["inheritedSetterMethods"]
        or image.setter_methods(owner, parameter="typeName", label=LABEL)
        != wrapper["setterMethods"]
    ):
        raise ValueError(f"{LABEL}.native:setter-order")
    return {
        "status": "validated",
        "unionTag": TAG,
        "nativeInputs": expected,
        "memberCount": wrapper["serializedMemberCount"],
    }


def _field_name(setter: list[Any]) -> str:
    name = setter[1]
    if not name.startswith("set___") or not name.endswith("__"):
        raise ValueError(f"{LABEL}.contract:setter-name={name}")
    return name.removeprefix("set___").removesuffix("__")


def decode_finish_buff_advanced_action_receipt(
    data: bytes,
    *,
    source: str,
    logical_sha256: str,
    start: int,
    end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name exactly one authenticated, bounded physical action span."""
    contract = _contract()
    _dependencies()
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs") != contract["nativeInputs"]
        or native_validation.get("memberCount")
        != contract["wrapper"]["serializedMemberCount"]
    ):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (
        not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}:logical-sha256-mismatch")
    if not source or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data):
        raise ValueError(f"{LABEL}:invalid-action-range")

    reader = Reader(data, source, end)
    reader.pos = start
    if reader.take(1, "union-tag")[0] != TAG:
        raise ValueError(f"{LABEL}:union-tag")
    reader.header(contract["wrapper"]["serializedMemberCount"])
    fields: list[dict[str, Any]] = []
    setters = (
        contract["wrapper"]["inheritedSetterMethods"]
        + contract["wrapper"]["setterMethods"]
    )
    callbacks = {
        "byte": lambda: reader.take(1, "anonymous-byte"),
        "scalar32": lambda: reader.take(4, "anonymous-scalar32"),
        "target-profile": reader.target_profile,
        "finder-profile": reader.finder_profile,
        "scalar-payload": reader.scalar_payload,
    }
    for setter, kind in zip(setters, contract["orderedReadKinds"], strict=True):
        field_start = reader.pos
        callbacks[kind]()
        if reader.pos <= field_start:
            raise ValueError(f"{LABEL}:field-no-progress")
        fields.append({
            "fieldName": _field_name(setter),
            "kind": kind,
            "start": field_start,
            "end": reader.pos,
        })
    if reader.pos != end or fields[0]["start"] != start + 2 or any(
        left["end"] != right["start"] for left, right in zip(fields, fields[1:])
    ):
        raise ValueError(f"{LABEL}:action-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA,
        "source": source,
        "logicalSha256": logical_sha256.upper(),
        "status": "named-wrapper-exact-span",
        "tag": TAG,
        "typeName": contract["wrappedType"],
        "memberCount": len(fields),
        "start": start,
        "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": [
            "buffOwner", "buffSettings", "buffSource", "finishLayerCnt", "finishSource"
        ],
        "evidenceBoundary": (
            "The selected native route and generated setters name thirteen "
            "FinishBuffAdvanced wrapper members, and authenticated logical bytes "
            "close this one physical action span. Nested profiles remain structural "
            "only; other actions, enclosing BuffData ownership, and runtime finish "
            "behavior remain unresolved."
        ),
    }
