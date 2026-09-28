"""Selected-build named wrapper receipt for BuffData ModifyDynamicBlackboard spans.

The existing reader frames physical tag 0x00EC. Its reviewed native source
contract supplies the ten-member read order; the action dispatcher supplies
generated field names and declared member types. Nested target and blackboard
values remain structural, as does the enclosing BuffData.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "buffModifyDynamicBlackboardActionReceipt"
TAG = 0x00EC
SCHEMA = "endfield.buff-modify-dynamic-blackboard-action-receipt.v1"
SOURCE_CONTRACT = CONTRACTS_DIR / "buff_ec_native.json"
CATALOG_CONTRACT = CONTRACTS_DIR / "levelscript_union_tags.json"

_KIND_COMPATIBILITY = {
    "byte": {"bool"},
    "scalar32": {"enum", "scalar32"},
    "byte-payload": {"string"},
    "member13": {"object"},
    "scalar-payload": {"object"},
}
_NESTED_PROFILE_KINDS = {"member13", "scalar-payload"}


@lru_cache(maxsize=1)
def _contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_CONTRACT.read_text(encoding="utf-8"))
    route = catalog["families"]["AbilityActionData"][TAG]
    kinds = source["anonymousReadOrder"]["member10"]
    if (
        source.get("schemaVersion") != 1
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("memberCount") != len(kinds)
        or not source.get("methods")
        or not source.get("codeWindows")
        or len(source.get("nestedContexts", [])) < 2
    ):
        raise ValueError(f"{LABEL}:contract-shape")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Recheck the selected dispatcher, source bytes and generated member order."""
    source, catalog = _contracts()
    inputs = catalog["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}:native:{gate.status}:{gate.detail}")
    routes, route_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    route = routes.get(TAG)
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    read_kinds = source["anonymousReadOrder"]["member10"]
    if (
        route_audit.get("status") != "validated"
        or route_audit.get("nativeInputs", {}).get("GameAssembly.dll", "").upper()
        != inputs["gameAssemblySha256"]
        or route_audit.get("nativeInputs", {}).get("global-metadata.dat", "").upper()
        != inputs["metadataSha256"]
        or route is None
        or route.status != "resolved"
        or route.wrapper_name != reviewed["wrapperName"]
        or len(route.member_order) != reviewed["memberCount"]
        or route.inherited_member_count != 4
        or len(route.member_kinds) != len(read_kinds)
        or len(route.member_declared_types) != len(read_kinds)
        or any(
            kind not in _KIND_COMPATIBILITY.get(read_kind, set())
            or (read_kind == "byte" and width != 1)
            or (read_kind == "scalar32" and width != 4)
            for read_kind, kind, width in zip(
                read_kinds, route.member_kinds, route.member_widths, strict=True
            )
        )
        or [
            declared_type
            for read_kind, declared_type in zip(
                read_kinds, route.member_declared_types, strict=True
            ) if read_kind in _NESTED_PROFILE_KINDS
        ] != [context["typeName"] for context in source["nestedContexts"][:2]]
    ):
        raise ValueError(f"{LABEL}:dispatcher-or-wrapper-drift")

    image = open_native_image(gate.gameassembly, gate.metadata)
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    for context in source["nestedContexts"]:
        instruction = image.pe.bytes_at_va(
            image.pe.image_base + context["instructionRva"], 7
        )
        if (
            instruction.hex().upper() != context["instructionHex"].upper()
            or instruction[:2] != b"\x48\x8b"
            or instruction[2] not in (0x15, 0x35)
        ):
            raise ValueError(f"{LABEL}:nested-instruction")
        cell = (
            image.pe.image_base + context["instructionRva"] + 7
            + struct.unpack_from("<i", instruction, 3)[0]
        )
        if (
            cell != context["cellVa"]
            or image.pe.bytes_at_va(cell, 8).hex().upper()
            != context["usageRawHex"].upper()
        ):
            raise ValueError(f"{LABEL}:nested-usage")

    return {
        "status": "validated",
        "unionTag": TAG,
        "nativeInputs": {
            "GameAssembly.dll": inputs["gameAssemblySha256"],
            "global-metadata.dat": inputs["metadataSha256"],
        },
        "memberCount": len(route.member_order),
        "memberNames": list(route.member_order),
        "readKinds": list(read_kinds),
        "typeName": reviewed["wrappedType"],
    }


def decode_modify_dynamic_blackboard_action_receipt(
    data: bytes,
    *,
    source: str,
    logical_sha256: str,
    start: int,
    end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one authenticated, bounded ModifyDynamicBlackboard wrapper."""
    source_contract, catalog = _contracts()
    native_inputs = catalog["nativeInputs"]
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs", {}).get("GameAssembly.dll")
        != native_inputs["gameAssemblySha256"]
        or native_validation.get("nativeInputs", {}).get("global-metadata.dat")
        != native_inputs["metadataSha256"]
        or native_validation.get("memberCount") != reviewed["memberCount"]
        or len(native_validation.get("memberNames", [])) != reviewed["memberCount"]
        or native_validation.get("readKinds")
        != source_contract["anonymousReadOrder"]["member10"]
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
    reader.header(native_validation["memberCount"])
    callbacks = {
        "byte": lambda: reader.take(1, "anonymous-byte"),
        "scalar32": lambda: reader.take(4, "anonymous-scalar32"),
        "byte-payload": reader.byte_payload,
        "member13": reader.target_profile,
        "scalar-payload": reader.scalar_payload,
    }
    fields: list[dict[str, Any]] = []
    for name, kind in zip(
        native_validation["memberNames"], native_validation["readKinds"], strict=True
    ):
        field_start = reader.pos
        callbacks[kind]()
        if reader.pos <= field_start:
            raise ValueError(f"{LABEL}:field-no-progress:{name}")
        fields.append({
            "fieldName": name,
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
        "typeName": native_validation["typeName"],
        "memberCount": len(fields),
        "start": start,
        "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": [
            field["fieldName"] for field in fields
            if field["kind"] in _NESTED_PROFILE_KINDS
        ],
        "evidenceBoundary": (
            "The selected native dispatcher and source contract name the ten "
            "ModifyDynamicBlackboard wrapper fields at this exact authenticated span. "
            "Nested target and blackboard values and the enclosing BuffData remain "
            "structural; runtime blackboard modification is not witnessed."
        ),
    }
