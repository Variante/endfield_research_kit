"""Selected-build named span receipt for BuffData SetSuperArmorAction.

The existing Buff reader already frames this action. This adapter attaches
generated wrapper field names only after rechecking its dispatcher, complete
source readers, nested generic calls, and the exact logical source bytes.

Physical tag ``0x0159`` selects the seven-member ``SetSuperArmorAction.Data``
wrapper. The checked generic calls cover the priority, impact, super-armor
and target members, and the adapter rejoins the exact action end in the
VFS-ledger-matched Buff corpus. ``TargetSettings`` remains structural, and
the stored reads do not prove when super armor is applied. The two
blackboard children are named by ``buff_super_armor_blackboard_child_receipt``.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack.buff_actions import Reader


LABEL = "buffSetSuperArmorActionReceipt"
SCHEMA = "endfield.buff-set-super-armor-action-receipt.v1"
TAG = 0x0159
SOURCE_CONTRACT = CONTRACTS_DIR / "buff_159_native.json"
CATALOG_CONTRACT = CONTRACTS_DIR / "levelscript_union_tags.json"
_NESTED_KINDS = {"scalar-flag-payload", "target-profile"}


@lru_cache(maxsize=1)
def _contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads(SOURCE_CONTRACT.read_text(encoding="utf-8"))
    catalog = json.loads(CATALOG_CONTRACT.read_text(encoding="utf-8"))
    route = catalog["families"]["AbilityActionData"][TAG]
    kinds = source["anonymousReadOrder"]["member7"]
    nested = source["nestedContexts"]
    methods = source.get("methods", [])
    window_starts = {row.get("startRva") for row in source.get("codeWindows", [])}
    if (
        source.get("schemaVersion") != 1
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("memberCount") != len(kinds)
        or any(kind not in ("byte", "scalar32", *_NESTED_KINDS) for kind in kinds)
        or len(methods) < 2
        or any(len(row) != 4 or row[3] not in window_starts for row in methods)
        or len(nested) != 1 + sum(kind in _NESTED_KINDS for kind in kinds)
    ):
        raise ValueError(f"{LABEL}:contract-shape")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Authenticate the current route, source read order, and nested types."""
    source, catalog = _contracts()
    inputs = catalog["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}:native:{gate.status}:{gate.detail}")
    routes, audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    route = routes.get(TAG)
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    kinds = source["anonymousReadOrder"]["member7"]
    contexts = source["nestedContexts"]
    if (
        audit.get("status") != "validated"
        or audit.get("nativeInputs", {}).get("GameAssembly.dll", "").upper()
        != inputs["gameAssemblySha256"]
        or audit.get("nativeInputs", {}).get("global-metadata.dat", "").upper()
        != inputs["metadataSha256"]
        or route is None
        or route.status != "resolved"
        or route.wrapper_name != reviewed["wrapperName"]
        or route.inherited_member_count != 4
        or len(route.member_order) != reviewed["memberCount"]
        or len(route.member_kinds) != len(kinds)
        or len(route.member_declared_types) != len(kinds)
        or any(
            (kind == "byte" and (actual != "bool" or width != 1))
            or (kind == "scalar32" and (actual not in ("enum", "scalar32") or width != 4))
            or (kind in _NESTED_KINDS and actual != "object")
            for kind, actual, width in zip(
                kinds, route.member_kinds, route.member_widths, strict=True
            )
        )
        or [route.member_declared_types[1], *route.member_declared_types[4:]]
        != [context["typeName"] for context in contexts]
    ):
        raise ValueError(f"{LABEL}:dispatcher-or-wrapper-drift")

    image = open_native_image(gate.gameassembly, gate.metadata)
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    for context in contexts:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        index = method_spec_usage_index(
            usage, image.registration["methodSpecsCount"],
            source=str(image.gameassembly), offset=cell,
        )
        if index != context["methodSpecIndex"]:
            raise ValueError(f"{LABEL}:method-spec-index")
        method_spec = struct.unpack(
            "<iii", image.pe.bytes_at_va(
                int(image.registration["methodSpecs"], 16) + index * 12, 12
            ),
        )
        if list(method_spec) != context["methodSpec"]:
            raise ValueError(f"{LABEL}:method-spec")
        instantiation = image.instantiations.resolve(method_spec[2])
        if (
            len(instantiation.arguments) != 1
            or instantiation.arguments[0].raw_type_record_hex
            != context["argumentRawHex"]
            or image.type_name(context["typeDefinition"]) != context["typeName"]
        ):
            raise ValueError(f"{LABEL}:method-type-argument")

    return {
        "status": "validated", "unionTag": TAG,
        "nativeInputs": {
            "GameAssembly.dll": inputs["gameAssemblySha256"],
            "global-metadata.dat": inputs["metadataSha256"],
        },
        "memberCount": len(route.member_order),
        "memberNames": list(route.member_order),
        "readKinds": list(kinds),
        "typeName": reviewed["wrappedType"],
    }


def decode_set_super_armor_action_receipt(
    data: bytes, *, source: str, logical_sha256: str, start: int, end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one bounded action while keeping its nested values structural."""
    source_contract, catalog = _contracts()
    inputs = catalog["nativeInputs"]
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs", {}).get("GameAssembly.dll")
        != inputs["gameAssemblySha256"]
        or native_validation.get("nativeInputs", {}).get("global-metadata.dat")
        != inputs["metadataSha256"]
        or native_validation.get("memberCount") != reviewed["memberCount"]
        or len(native_validation.get("memberNames", [])) != reviewed["memberCount"]
        or native_validation.get("readKinds")
        != source_contract["anonymousReadOrder"]["member7"]
        or native_validation.get("typeName") != reviewed["wrappedType"]
    ):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (
        not isinstance(logical_sha256, str)
        or len(logical_sha256) != 64
        or hashlib.sha256(data).hexdigest().upper() != logical_sha256.upper()
    ):
        raise ValueError(f"{LABEL}:logical-sha256-mismatch")
    if (
        not source or type(start) is not int or type(end) is not int
        or not 0 <= start < end <= len(data)
    ):
        raise ValueError(f"{LABEL}:invalid-action-range")

    reader = Reader(data, source, end)
    reader.pos = start
    if reader.take(3, "union-tag") != bytes((0xFA, TAG & 0xFF, TAG >> 8)):
        raise ValueError(f"{LABEL}:union-tag")
    reader.header(native_validation["memberCount"])
    callbacks = {
        "byte": lambda: reader.take(1, "anonymous-byte"),
        "scalar32": lambda: reader.take(4, "anonymous-scalar32"),
        "scalar-flag-payload": reader.scalar_flag_payload,
        "target-profile": reader.target_profile,
    }
    fields = []
    for name, kind in zip(
        native_validation["memberNames"], native_validation["readKinds"], strict=True
    ):
        field_start = reader.pos
        callbacks[kind]()
        if reader.pos <= field_start:
            raise ValueError(f"{LABEL}:field-no-progress:{name}")
        fields.append({
            "fieldName": name, "kind": kind,
            "start": field_start, "end": reader.pos,
        })
    if (
        reader.pos != end
        or fields[0]["start"] != start + 4
        or any(left["end"] != right["start"]
               for left, right in zip(fields, fields[1:]))
    ):
        raise ValueError(f"{LABEL}:action-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA, "source": source,
        "logicalSha256": logical_sha256.upper(),
        "status": "named-wrapper-exact-span", "tag": TAG,
        "typeName": native_validation["typeName"],
        "memberCount": len(fields), "start": start, "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": [
            field["fieldName"] for field in fields
            if field["kind"] in _NESTED_KINDS
        ],
        "evidenceBoundary": (
            "The selected native dispatcher and source readers name the seven "
            "SetSuperArmorAction fields at this exact authenticated span. "
            "Blackboard values, TargetSettings, parent BuffData, and runtime "
            "super-armor behavior remain unresolved."
        ),
    }
