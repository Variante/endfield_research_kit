"""Bounded squad-USP header composition through reviewed default formatters."""
from __future__ import annotations

from pathlib import Path
import struct
from typing import Any

from scripts.game_data.levelscript_on_squad_member_usp_native import (
    LABEL, load_on_squad_member_usp_contract,
)


class SquadUspDecodeError(ValueError):
    def __init__(self, check: str, expected: Any, actual: Any, *, field: str, offset: int,
                 decoded_prefix: dict[str, Any] | None = None):
        self.diagnostics = {"validator": LABEL, "check": check, "field": field, "offset": offset,
                            "expected": str(expected)[:240], "actual": str(actual)[:240]}
        self.decoded_prefix = decoded_prefix or {}
        super().__init__(f"{field}: validator={LABEL},check={check},offset={offset},expected={expected},actual={actual}")


class _Reader:
    def __init__(self, data: bytes, offset: int):
        if offset < 0 or offset > len(data):
            raise SquadUspDecodeError("bounded-offset", f"0..{len(data)}", offset, field="record", offset=offset)
        self.data, self.offset = data, offset

    def raw(self, size: int, field: str) -> bytes:
        if size < 0 or size > len(self.data) - self.offset:
            raise SquadUspDecodeError("bounded-source-read", size, max(0, len(self.data) - self.offset), field=field, offset=self.offset)
        result = self.data[self.offset:self.offset + size]
        self.offset += size
        return result

    def value(self, kind: str, field: str) -> Any:
        if kind == "bool":
            return bool(self.raw(1, field)[0])
        if kind == "int32":
            return struct.unpack("<i", self.raw(4, field))[0]
        if kind == "string":
            start = self.offset
            size = struct.unpack("<i", self.raw(4, field + ".byteLength"))[0]
            if size == -1:
                return None
            if size < -1:
                raise SquadUspDecodeError("utf8-length-profile", "-1 or bounded nonnegative byte length", size, field=field, offset=start)
            try:
                return self.raw(size, field).decode("utf-8")
            except UnicodeDecodeError as error:
                raise SquadUspDecodeError("utf8-profile", "valid UTF-8 bytes", str(error)[:120], field=field, offset=start) from error
        raise SquadUspDecodeError("isolated-wire-kind", "bool/int32/string", kind, field=field, offset=self.offset)


def _authenticated(game_root: Path | None, gameassembly: Path | None, metadata: Path | None) -> dict[str, Any]:
    contract, audit = load_on_squad_member_usp_contract(game_root=game_root, gameassembly=gameassembly, metadata=metadata)
    if audit["status"] != "validated":
        raise SquadUspDecodeError(audit["failedCheck"], "validated selected native inputs", audit["status"] + ":" + audit["detail"], field="native", offset=0)
    return contract


def _decode_child_wire(data: bytes, offset: int, child: dict[str, Any]) -> tuple[dict[str, Any], int]:
    cursor = _Reader(data, offset)
    header = cursor.raw(1, child["kind"] + ".memberCount")[0]
    if header == 0xFF:
        return {"null": True, "fields": None, "sourceOffset": offset, "endOffset": cursor.offset,
                "evidenceBoundary": "exact", "scope": "isolated-generated-child", "parentProviderJoin": "unresolved"}, cursor.offset
    if header != child["memberCount"]:
        raise SquadUspDecodeError("member-count", child["memberCount"], header, field=child["kind"], offset=offset)
    fields, spans = {}, {}
    for name, kind in child["fields"]:
        start = cursor.offset
        fields[name] = cursor.value(kind, child["kind"] + "." + name)
        spans[name] = [start, cursor.offset]
    return {"null": False, "fields": fields, "fieldSpans": spans, "sourceOffset": offset,
            "endOffset": cursor.offset, "evidenceBoundary": "exact", "scope": "isolated-generated-child",
            "parentProviderJoin": "unresolved"}, cursor.offset


def decode_isolated_squad_usp_child(data: bytes, offset: int, kind: str, *,
        game_root: Path | None = None, gameassembly: Path | None = None,
        metadata: Path | None = None) -> tuple[dict[str, Any], int]:
    """Decode one authenticated child, retaining its unresolved parent join."""
    contract = _authenticated(game_root, gameassembly, metadata)
    children = {row["kind"]: row for row in contract["children"]}
    if kind not in children:
        raise SquadUspDecodeError("isolated-child-type", list(children), kind, field="child", offset=offset)
    return _decode_child_wire(data, offset, children[kind])


def decode_on_squad_member_usp_header(data: bytes, offset: int, *,
        game_root: Path | None = None, gameassembly: Path | None = None,
        metadata: Path | None = None) -> tuple[dict[str, Any], int]:
    """Decode the exact default stored header; make no live provider claim."""
    contract = _authenticated(game_root, gameassembly, metadata)
    route = contract["route"]
    cursor = _Reader(data, offset)
    tag = cursor.raw(1, "squadUspHeader.unionTag")[0]
    if tag == 0xFA:
        tag = struct.unpack("<H", cursor.raw(2, "squadUspHeader.wideUnionTag"))[0]
    if tag != route["tag"]:
        raise SquadUspDecodeError("union-tag", route["tag"], tag, field="squadUspHeader", offset=offset)
    members = cursor.raw(1, "squadUspHeader.memberCount")[0]
    if members == 0xFF:
        return {"sourceOffset": offset, "endOffset": cursor.offset, "unionTag": tag,
                "memberCount": None, "wrapperNull": True, "fields": None,
                "evidenceBoundary": "exact", "scope": "direct-outer-wrapper-null"}, cursor.offset
    if members != route["serializedMemberCount"]:
        raise SquadUspDecodeError("member-count", route["serializedMemberCount"], members, field="squadUspHeader", offset=cursor.offset - 1)
    fields, spans = {}, {}
    for name, kind in route["fields"]:
        start = cursor.offset
        if kind.startswith("Param"):
            child = next(row for row in contract["children"] if row["kind"] == kind)
            if child["parentProviderJoin"] != "exact-default-stored":
                raise SquadUspDecodeError("default-stored-join", "exact-default-stored", child["parentProviderJoin"], field=name, offset=start)
            fields[name], cursor.offset = _decode_child_wire(data, cursor.offset, child)
            fields[name].update(scope="default-stored-child", parentProviderJoin="exact-default-stored", runtimeProviderSelection="unresolved")
        else:
            fields[name] = cursor.value(kind, "squadUspHeader." + name)
        spans[name] = [start, cursor.offset]
    return {"sourceOffset": offset, "endOffset": cursor.offset, "unionTag": tag,
            "memberCount": members, "wrapperNull": False, "fields": fields, "fieldSpans": spans,
            "evidenceBoundary": "exact", "scope": "default-stored-header",
            "runtimeProviderSelection": "unresolved"}, cursor.offset
