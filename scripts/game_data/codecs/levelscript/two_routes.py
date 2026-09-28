"""Exact finite LevelScript records for reviewed getter and action routes.

The selected native contract supplies the field order. This reader reuses the
maintained ActionSerializedMap primitive and Param decoders at a real cursor.
It stops at the first malformed member and makes no runtime behavior claim.
"""
from __future__ import annotations

import struct
from functools import lru_cache
from typing import Any

from scripts.game_data import levelscript_two_routes_native


@lru_cache(maxsize=1)
def _native_validation() -> dict[str, Any]:
    result = levelscript_two_routes_native.validate_current_native_contract()
    if result.get("status") != "validated":
        raise ValueError("levelscriptTwoRoutes.native:not-validated")
    return result


def decode_route_at(
    data: bytes, offset: int, family: str, tag: int, *, limit: int | None = None,
) -> tuple[dict[str, Any], int]:
    """Decode one selected union, bounded by ``limit`` when supplied."""
    _native_validation()
    route = levelscript_two_routes_native.reviewed_route(family, tag)
    hard_limit = len(data) if limit is None else limit
    if hard_limit < 0 or hard_limit > len(data) or offset < 0 or offset >= hard_limit:
        raise ValueError("levelscriptTwoRoutes.cursor:outside-input")
    # Import lazily so ActionSerializedMap may consult this module without a
    # circular import. Its Cursor owns all primitive/Param failure behavior.
    from . import action_map

    cursor = action_map._Cursor(data[:hard_limit], offset)
    tag_field = f"levelscriptTwoRoutes.{family}.tag"
    tag_width = 2 if tag > 0xFF else 1
    if tag_width == 2:
        marker = cursor.byte(f"levelscriptTwoRoutes.{family}.marker")
        if marker != 0xFA:
            raise action_map.ActionMapCodecError(
                f"levelscriptTwoRoutes.{family}:expected-wide-marker=0xfa,actual={marker:#x}"
            )
    cursor.need(tag_width, tag_field)
    physical_tag = (
        struct.unpack_from("<H", cursor.data, cursor.offset)[0]
        if tag_width == 2 else cursor.data[cursor.offset]
    )
    cursor.offset += tag_width
    if physical_tag != tag:
        raise action_map.ActionMapCodecError(
            f"levelscriptTwoRoutes.{family}:expected-tag={tag:#x},actual={physical_tag:#x}"
        )
    members = cursor.byte(f"levelscriptTwoRoutes.{family}.memberCount")
    if members != route["serializedMemberCount"]:
        raise action_map.ActionMapCodecError(
            f"levelscriptTwoRoutes.{family}:expected-members={route['serializedMemberCount']},actual={members}"
        )
    values = {
        name: cursor.value(kind, f"levelscriptTwoRoutes.{family}.{name}")
        for name, kind in route["fields"]
    }
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": tag, "memberCount": members,
        "wrapperName": route["wrapperName"], "fields": values,
        "evidenceBoundary": "exact selected native source with finite cursor",
    }, cursor.offset
