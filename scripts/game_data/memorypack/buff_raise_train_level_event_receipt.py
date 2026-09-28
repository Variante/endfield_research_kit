"""Selected-build named wrapper receipt for Buff RaiseTrainLevelEvent (011F).

The reviewed Buff source window owns the eight read kinds; the current native
action route supplies generated wrapper names and nested declared types. The
paired and scalar Blackboard payloads remain structurally framed here.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.context import method_spec_usage_index
from scripts.game_data.il2cpp.native_image import open_native_image
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import load_action_routes


LABEL = "buffRaiseTrainLevelEventReceipt"
SCHEMA = "endfield.buff-raise-train-level-event-receipt.v1"
TAG = 0x011F
SOURCE_PATH = CONTRACTS_DIR / "buff_11f_native.json"
CATALOG_PATH = CONTRACTS_DIR / "levelscript_union_tags.json"
_KIND_COMPATIBILITY = {
    "byte": {"bool"},
    "scalar32": {"enum", "scalar32"},
    "paired-payload": {"object"},
    "scalar-payload": {"object"},
}


@lru_cache(maxsize=1)
def _contracts() -> tuple[dict[str, Any], dict[str, Any]]:
    source = json.loads(SOURCE_PATH.read_bytes())
    catalog = json.loads(CATALOG_PATH.read_bytes())
    routes = catalog["families"]["AbilityActionData"]
    route = routes[TAG]
    kinds = source.get("anonymousReadOrder", {}).get("member8")
    nested_contexts = source.get("nestedContexts")
    if (
        source.get("schemaVersion") != 1
        or not isinstance(source.get("methods"), list)
        or not isinstance(source.get("codeWindows"), list)
        or not isinstance(nested_contexts, list)
        or not isinstance(kinds, list)
        or not kinds
        or any(kind not in _KIND_COMPATIBILITY for kind in kinds)
        or sum(kind in ("paired-payload", "scalar-payload") for kind in kinds)
        != len(nested_contexts)
        or catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or route.get("tag") != TAG
        or route.get("memberCount") != len(kinds)
        or not isinstance(route.get("wrapperName"), str)
        or not isinstance(route.get("wrappedType"), str)
        or catalog["switches"]["AbilityActionData"]["entryCount"] != len(routes)
    ):
        raise ValueError(f"{LABEL}.contract:dependency-shape")
    return source, catalog


def validate_current_native_contract() -> dict[str, Any]:
    """Prove route, source bytes, three nested contexts, and field order."""
    source, catalog = _contracts()
    inputs = catalog["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssemblySha256"], inputs["metadataSha256"]
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"{LABEL}.native:{gate.status}:{gate.detail}")
    routes, route_audit = load_action_routes(
        gameassembly=gate.gameassembly, metadata=gate.metadata
    )
    route = routes.get(TAG)
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    kinds = source["anonymousReadOrder"]["member8"]
    if (
        route_audit.get("status") != "validated"
        or route_audit.get("nativeInputs", {}).get("GameAssembly.dll", "").upper()
        != inputs["gameAssemblySha256"]
        or route_audit.get("nativeInputs", {}).get("global-metadata.dat", "").upper()
        != inputs["metadataSha256"]
        or route is None or route.status != "resolved"
        or route.wrapper_name != reviewed["wrapperName"]
        or len(route.member_order) != reviewed["memberCount"]
        or route.inherited_member_count != 4
        or len(route.member_kinds) != len(kinds)
        or len(route.member_declared_types) != len(kinds)
        or len(route.member_widths) != len(kinds)
        or any(
            member_kind not in _KIND_COMPATIBILITY[read_kind]
            or (read_kind == "byte" and width != 1)
            or (read_kind == "scalar32" and width != 4)
            for read_kind, member_kind, width in zip(
                kinds, route.member_kinds, route.member_widths, strict=True
            )
        )
        or [
            declared for kind, declared in zip(kinds, route.member_declared_types, strict=True)
            if kind in ("paired-payload", "scalar-payload")
        ] != [context["typeName"] for context in source["nestedContexts"]]
    ):
        raise ValueError(f"{LABEL}.native:route-or-wrapper-drift")
    image = open_native_image(gate.gameassembly, gate.metadata)
    for method in source["methods"]:
        image.validate_method_row(method, label=LABEL)
    image.check_windows(source["codeWindows"], label=LABEL)
    for context in source["nestedContexts"]:
        cell, usage = image.nested_usage_cell(context, label=LABEL)
        spec_index = context["methodSpecIndex"]
        if (
            method_spec_usage_index(
                usage, image.registration["methodSpecsCount"],
                source=str(gate.gameassembly), offset=cell,
            ) != spec_index
            or not 0 <= spec_index < image.registration["methodSpecsCount"]
        ):
            raise ValueError(f"{LABEL}.native:nested-method-spec-index")
        raw = image.pe.bytes_at_va(
            int(image.registration["methodSpecs"], 16) + spec_index * 12, 12
        )
        if list(struct.unpack("<iii", raw)) != context["methodSpec"]:
            raise ValueError(f"{LABEL}.native:nested-method-spec")
        instantiation = image.instantiations.resolve(context["methodSpec"][2])
        if (
            image.type_name(context["typeDefinition"]) != context["typeName"]
            or len(instantiation.arguments) != 1
            or instantiation.arguments[0].raw_type_record_hex.upper()
            != context["argumentRawHex"].upper()
        ):
            raise ValueError(f"{LABEL}.native:nested-type")
    return {
        "status": "validated",
        "unionTag": TAG,
        "nativeInputs": {
            "GameAssembly.dll": inputs["gameAssemblySha256"],
            "global-metadata.dat": inputs["metadataSha256"],
        },
        "memberCount": len(route.member_order),
        "memberNames": list(route.member_order),
        "readKinds": list(kinds),
        "typeName": reviewed["wrappedType"],
    }


def decode_raise_train_level_event_receipt(
    data: bytes,
    *,
    source: str,
    logical_sha256: str,
    start: int,
    end: int,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Name one authenticated extended-tag wrapper and exact physical span."""
    source_contract, catalog = _contracts()
    inputs = catalog["nativeInputs"]
    reviewed = catalog["families"]["AbilityActionData"][TAG]
    if (
        native_validation.get("status") != "validated"
        or native_validation.get("unionTag") != TAG
        or native_validation.get("nativeInputs") != {
            "GameAssembly.dll": inputs["gameAssemblySha256"],
            "global-metadata.dat": inputs["metadataSha256"],
        }
        or native_validation.get("memberCount") != reviewed["memberCount"]
        or len(native_validation.get("memberNames", [])) != reviewed["memberCount"]
        or native_validation.get("readKinds")
        != source_contract["anonymousReadOrder"]["member8"]
        or native_validation.get("typeName") != reviewed["wrappedType"]
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
    tag_bytes = reader.take(3, "union-tag")
    if tag_bytes != b"\xFA" + struct.pack("<H", TAG):
        raise ValueError(f"{LABEL}:union-tag")
    reader.header(native_validation["memberCount"])
    callbacks = {
        "byte": lambda: reader.take(1, "anonymous-byte"),
        "scalar32": lambda: reader.take(4, "anonymous-scalar32"),
        "paired-payload": reader.paired_payload,
        "scalar-payload": reader.scalar_payload,
    }
    fields: list[dict[str, Any]] = []
    for name, kind in zip(
        native_validation["memberNames"], native_validation["readKinds"], strict=True
    ):
        field_start = reader.pos
        value = callbacks[kind]()
        if kind == "byte" and value[0] not in (0, 1):
            raise ValueError(f"{LABEL}:invalid-boolean={field_start}")
        if reader.pos <= field_start:
            raise ValueError(f"{LABEL}:field-no-progress:{name}")
        fields.append({"fieldName": name, "kind": kind,
                       "start": field_start, "end": reader.pos})
    if reader.pos != end or fields[0]["start"] != start + 4 or any(
        left["end"] != right["start"] for left, right in zip(fields, fields[1:])
    ):
        raise ValueError(f"{LABEL}:action-end={reader.pos}; expected={end}")
    return {
        "schema": SCHEMA,
        "source": source,
        "logicalSha256": logical_sha256.upper(),
        "status": "named-wrapper-exact-span",
        "tag": TAG,
        "typeName": reviewed["wrappedType"],
        "memberCount": len(fields),
        "start": start,
        "end": end,
        "namedFields": fields,
        "wholeActionByteSpanExact": True,
        "recursiveNamedSchemaExact": False,
        "wholeBuffDataExact": False,
        "nestedStructuralFields": [
            name for name, kind in zip(
                native_validation["memberNames"], native_validation["readKinds"], strict=True
            ) if kind in ("paired-payload", "scalar-payload")
        ],
        "evidenceBoundary": (
            "The selected native route and generated wrapper name eight source "
            "ordered members. Current logical bytes close this physical action "
            "span. BlackboardString and BlackboardDouble payloads remain "
            "structurally framed; this does not prove string values, evaluation, "
            "runtime event dispatch, or enclosing BuffData ownership."
        ),
    }
