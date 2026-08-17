"""Streaming, fail-closed evidence extraction for DXCap ``-toXML`` output.

DXCap XML has changed shape between SDK releases.  This reader therefore uses
the operation name and named arguments as the stable boundary, while accepting
the common attribute/child spellings emitted by those releases.  It never
interprets shader bytes: the XML normally exposes only the object handle and
bytecode length.

The module is intentionally stdlib-only and can be used as a library or as a
small command-line converter::

    python dxcap_xml_evidence.py frame.xml -o frame.evidence.json
"""

from __future__ import annotations

import argparse
import io
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, TextIO


SCHEMA = "endfield.dxcap-d3d11-evidence.v1"
M23_VS_BYTECODE_LENGTH = 10720
M23_PS_BYTECODE_LENGTH = 8100
M23_IA_STRIDE = 136


class EvidenceParseError(ValueError):
    """Raised when the XML is malformed or cannot be read safely."""


class _FragmentReader:
    """Expose DXCap's rootless XML event stream as one synthetic document."""

    def __init__(self, stream: Any) -> None:
        self.stream = stream
        initial = stream.read(512)
        initial = re.sub(br"^\s*<\?xml[^>]*\?>", b"", initial, count=1)
        self.prefix = b"<Capture>" + initial
        self.suffix = b"</Capture>"
        self.finished = False

    def read(self, size: int = -1) -> bytes:
        if self.prefix:
            if size < 0 or len(self.prefix) <= size:
                value, self.prefix = self.prefix, b""
                if size < 0:
                    return value + self.stream.read() + self.suffix
                return value
            value, self.prefix = self.prefix[:size], self.prefix[size:]
            return value
        value = self.stream.read(size)
        if value:
            return value
        if not self.finished:
            self.finished = True
            value, self.suffix = self.suffix, b""
            return value
        return b""

    def close(self) -> None:
        self.stream.close()


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1].lower()


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def _text(element: ET.Element) -> str:
    return " ".join(part.strip() for part in element.itertext() if part.strip())


def _number(value: Any) -> int | float | str | None:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw or raw.lower() in {"null", "none", "n/a", "-"}:
        return None
    match = re.search(r"[-+]?0x[0-9a-f]+|[-+]?(?:\d+(?:\.\d*)?|\.\d+)", raw, re.I)
    if not match:
        return raw
    token = match.group(0)
    try:
        return int(token, 0) if not any(c in token.lower() for c in ".e") else float(token)
    except ValueError:
        return raw


def _int(value: Any) -> int | None:
    parsed = _number(value)
    return parsed if isinstance(parsed, int) else None


def _value(element: ET.Element, names: Iterable[str]) -> Any:
    wanted = {_norm(name) for name in names}
    # Prefer named attributes.  XML producers commonly use Name/value pairs.
    for key, value in element.attrib.items():
        if _norm(key) in wanted:
            return value
    for child in element.iter():
        # DXCap also emits ``<Arg name="Stride">136</Arg>``.  Treat the
        # argument name as its key, but only use its own text (not descendants)
        # so a nested argument cannot leak into a sibling lookup.
        argument_name = child.attrib.get("name") or child.attrib.get("Name")
        if argument_name is not None and _norm(argument_name) in wanted:
            for attribute in ("value", "handle"):
                if attribute in child.attrib:
                    return child.attrib[attribute]
            value = " ".join(part.strip() for part in child.itertext() if part.strip())
            if value:
                return value
        for key, value in child.attrib.items():
            if _norm(key) in wanted:
                return value
        if _norm(_local(child.tag)) in wanted:
            value = _text(child)
            if value:
                return value
    return None


def _operation(element: ET.Element) -> str:
    wanted = {"name", "function", "method", "api", "call", "operation", "op"}
    for key, value in element.attrib.items():
        if _norm(key) in wanted and value:
            return str(value)
    return _local(element.tag)


def _all_values(element: ET.Element, names: Iterable[str]) -> list[Any]:
    wanted = {_norm(name) for name in names}
    values: list[Any] = []
    for node in element.iter():
        argument_name = node.attrib.get("name") or node.attrib.get("Name")
        if argument_name is not None and _norm(argument_name) in wanted:
            if "value" in node.attrib:
                values.append(node.attrib["value"])
            elif "handle" in node.attrib:
                values.append(node.attrib["handle"])
            elif _text(node):
                values.append(_text(node))
            else:
                values.extend(
                    child.attrib[attribute]
                    for child in node.iter()
                    for attribute in ("value", "handle")
                    if child is not node and attribute in child.attrib
                )
        for key, value in node.attrib.items():
            if _norm(key) in wanted:
                values.append(value)
        if _norm(_local(node.tag)) in wanted and _text(node):
            values.append(_text(node))
    return values


def _parameters(element: ET.Element) -> dict[str, Any]:
    """Return bounded named call parameters, preserving unknown evidence."""
    out: dict[str, Any] = {}
    for node in element.iter():
        for key, value in node.attrib.items():
            if _norm(key) in {"name", "function", "method", "api", "call", "operation", "op"}:
                continue
            parsed = _number(value)
            out.setdefault(key, parsed if parsed is not None else str(value))
        if len(out) >= 96:
            break
    return out


def _handle(element: ET.Element, names: Iterable[str]) -> str | None:
    value = _value(element, names)
    if value is None:
        return None
    raw = str(value).strip()
    return raw if raw else None


def _resource_entries(element: ET.Element, kind: str) -> list[dict[str, Any]]:
    """Read slot/handle pairs from child binding records or named arrays."""
    entries: list[dict[str, Any]] = []
    parameter_tokens = {
        "buffer": ("ppvertexbuffers",),
        "constantbuffer": ("ppconstantbuffers",),
        "resource": ("ppshaderresourceviews", "pprendertargetviews"),
        "sampler": ("ppsamplers",),
    }[kind]
    for parameter in element.iter():
        if _local(parameter.tag) != "parameter":
            continue
        name = _norm(next((value for key, value in parameter.attrib.items() if _norm(key) == "name"), ""))
        if name not in parameter_tokens:
            continue
        for child in parameter.iter():
            if child is parameter or "handle" not in child.attrib:
                continue
            entries.append({"handle": child.attrib["handle"]})
    if entries:
        start_slot = _int(_value(element, ("startslot",))) or 0
        for index, row in enumerate(entries):
            row["slot"] = start_slot + index
        return entries[:64]
    child_names = {"resource", "srv", "shaderresource", "sampler", "constantbuffer", "buffer", "vertexbuffer", "binding", "view", "element"}
    for node in element.iter():
        tag = _local(node.tag)
        if node is element or tag not in child_names:
            continue
        handle = _handle(node, ("handle", "resource", "view", "buffer", "object", "id", "value"))
        slot = _int(_value(node, ("slot", "startslot", "register", "index", "bindpoint")))
        if handle is not None or slot is not None:
            row: dict[str, Any] = {}
            if slot is not None:
                row["slot"] = slot
            if handle is not None:
                row["handle"] = handle
            entries.append(row)
    # Single-call attributes are also common (pViews="...").
    if not entries:
        handles = _all_values(element, ("handle", "resource", "view", "buffer", "object"))
        for index, handle in enumerate(handles):
            entries.append({"slot": index, "handle": str(handle)})
    start_slot = _int(_value(element, ("startslot",))) or 0
    for index, row in enumerate(entries):
        row.setdefault("slot", start_slot + index)
    return entries[:64]


class _State:
    def __init__(self) -> None:
        self.shaders: dict[str, dict[str, Any]] = {}
        self.vs_handle: str | None = None
        self.ps_handle: str | None = None
        self.vertex_buffers: list[dict[str, Any]] = []
        self.index_buffer: dict[str, Any] = {}
        self.vs_constant_buffers: list[dict[str, Any]] = []
        self.ps_constant_buffers: list[dict[str, Any]] = []
        self.vs_resources: list[dict[str, Any]] = []
        self.ps_resources: list[dict[str, Any]] = []
        self.vs_samplers: list[dict[str, Any]] = []
        self.ps_samplers: list[dict[str, Any]] = []
        self.render_targets: list[dict[str, Any]] = []
        self.topology: Any = None
        self.viewport: dict[str, Any] | None = None


def _merge_slots(current: list[dict[str, Any]], updates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply a D3D11 partial slot update while preserving unaffected slots."""
    merged = {row.get("slot"): dict(row) for row in current if isinstance(row.get("slot"), int)}
    for row in updates:
        slot = row.get("slot")
        if isinstance(slot, int):
            merged[slot] = dict(row)
    return [merged[slot] for slot in sorted(merged)][:64]


def _set_entries(element: ET.Element, *, include_stride: bool = False) -> list[dict[str, Any]]:
    entries = _resource_entries(element, "buffer")
    if include_stride:
        # Child records carry the authoritative slot-local stride/offset.
        for node in element.iter():
            if _local(node.tag) not in {"buffer", "vertexbuffer", "binding"}:
                continue
            slot = _int(_value(node, ("slot", "startslot", "register", "index")))
            stride = _int(_value(node, ("stride", "strides", "bytestride")))
            offset = _int(_value(node, ("offset", "offsets", "byteoffset")))
            if slot is None and stride is None and offset is None:
                continue
            row = next((item for item in entries if item.get("slot") == slot), None)
            if row is None:
                row = {"slot": slot if slot is not None else len(entries)}
                entries.append(row)
            if stride is not None:
                row["stride"] = stride
            if offset is not None:
                row["offset"] = offset
        if not any("stride" in row for row in entries):
            strides = [_int(v) for v in _all_values(element, ("stride", "strides", "pstrides", "bytestride"))]
            offsets = [_int(v) for v in _all_values(element, ("offset", "offsets", "poffsets", "byteoffset"))]
            for i, value in enumerate(strides):
                if value is not None:
                    while len(entries) <= i:
                        entries.append({"slot": len(entries)})
                    entries[i]["stride"] = value
            for i, value in enumerate(offsets):
                if value is not None:
                    while len(entries) <= i:
                        entries.append({"slot": len(entries)})
                    entries[i]["offset"] = value
    return entries[:64]


def _draw_type(operation: str) -> str | None:
    normalized = _norm(operation)
    for name in ("DrawIndexedInstancedIndirect", "DrawInstancedIndirect", "DrawIndexedInstanced", "DrawInstanced", "DrawIndexed", "DrawAuto", "Draw"):
        if _norm(name) in normalized:
            return name
    return None


def _is_api_operation(operation: str) -> bool:
    normalized = _norm(operation)
    return any(token in normalized for token in (
        "createvertexshader", "createpixelshader", "iasetvertexbuffers",
        "iasetindexbuffer", "vssetshader", "pssetshader", "setconstantbuffers",
        "setshaderresources", "setsamplers", "omsetrendertargets",
        "iasetprimitivetopology", "rssetviewports", "draw",
    ))


def _draw_parameters(element: ET.Element) -> dict[str, Any]:
    values = _parameters(element)
    aliases = {
        "vertex_count": ("vertexcount", "vertex_count"),
        "instance_count": ("instancecount", "instance_count"),
        "start_vertex": ("startvertexlocation", "startvertex"),
        "index_count": ("indexcount",),
        "start_index": ("startindexlocation", "startindex"),
        "base_vertex": ("basevertexlocation", "basevertex"),
        "start_instance": ("startinstancelocation", "startinstance"),
    }
    for key, names in aliases.items():
        value = _value(element, names)
        if value is not None:
            values[key] = _number(value)
    return values


def _candidate(state: _State) -> dict[str, Any]:
    vs = state.shaders.get(state.vs_handle or "")
    ps = state.shaders.get(state.ps_handle or "")
    strides = sorted({row.get("stride") for row in state.vertex_buffers if isinstance(row.get("stride"), int)})
    checks = {
        "vs_handle_known": bool(vs),
        "ps_handle_known": bool(ps),
        "vs_bytecode_length": bool(vs and vs.get("bytecode_length") == M23_VS_BYTECODE_LENGTH),
        "ps_bytecode_length": bool(ps and ps.get("bytecode_length") == M23_PS_BYTECODE_LENGTH),
        "ia_stride_136": M23_IA_STRIDE in strides,
    }
    return {
        "exact_m23_candidate": all(checks.values()),
        "checks": checks,
        "reason": "all required handle/length/IA-stride evidence present" if all(checks.values()) else "insufficient evidence; no exact M23 claim",
        "byte_hashes_available": False,
    }


def _snapshot(state: _State) -> dict[str, Any]:
    return {
        "vs_handle": state.vs_handle,
        "ps_handle": state.ps_handle,
        "ia_vertex_buffers": [dict(x) for x in state.vertex_buffers],
        "index_buffer": dict(state.index_buffer),
        "vs_constant_buffers": [dict(x) for x in state.vs_constant_buffers],
        "ps_constant_buffers": [dict(x) for x in state.ps_constant_buffers],
        "vs_resources": [dict(x) for x in state.vs_resources],
        "ps_resources": [dict(x) for x in state.ps_resources],
        "vs_samplers": [dict(x) for x in state.vs_samplers],
        "ps_samplers": [dict(x) for x in state.ps_samplers],
        "render_targets": [dict(x) for x in state.render_targets],
        "topology": state.topology,
        "viewport": dict(state.viewport) if state.viewport else None,
    }


def _apply(element: ET.Element, state: _State) -> tuple[str, dict[str, Any] | None]:
    operation = _operation(element)
    normalized = _norm(operation)
    if "createvertexshader" in normalized:
        handle = _handle(element, ("vertexshader", "pvertexshader", "ppvertexshader"))
        length = _int(_value(element, ("bytecodelength", "pshaderbytecodelength")))
        if handle is not None and length is not None:
            state.shaders[handle] = {"stage": "VS", "handle": handle, "bytecode_length": length}
        return operation, None
    if "createpixelshader" in normalized:
        handle = _handle(element, ("pixelshader", "ppixelshader", "pppixelshader"))
        length = _int(_value(element, ("bytecodelength", "pshaderbytecodelength")))
        if handle is not None and length is not None:
            state.shaders[handle] = {"stage": "PS", "handle": handle, "bytecode_length": length}
        return operation, None
    if "iasetvertexbuffers" in normalized:
        state.vertex_buffers = _merge_slots(state.vertex_buffers, _set_entries(element, include_stride=True))
    elif "iasetindexbuffer" in normalized:
        state.index_buffer = {}
        for key, aliases in (("handle", ("buffer", "indexbuffer", "pindexbuffer", "handle", "resource", "object")), ("format", ("format", "dxgiformat", "indexformat")), ("offset", ("offset", "byteoffset"))):
            value = _value(element, aliases)
            if value is not None:
                state.index_buffer[key] = _number(value) if key == "offset" else str(value)
    elif "vssetshader" in normalized and "resource" not in normalized and "sampler" not in normalized:
        state.vs_handle = _handle(element, ("shader", "vertexshader", "pvertexshader", "object", "value"))
    elif "pssetshader" in normalized and "resource" not in normalized and "sampler" not in normalized:
        state.ps_handle = _handle(element, ("shader", "pixelshader", "ppixelshader", "object", "value"))
    elif "vssetconstantbuffers" in normalized:
        state.vs_constant_buffers = _merge_slots(state.vs_constant_buffers, _resource_entries(element, "constantbuffer"))
    elif "pssetconstantbuffers" in normalized:
        state.ps_constant_buffers = _merge_slots(state.ps_constant_buffers, _resource_entries(element, "constantbuffer"))
    elif "vssetshaderresources" in normalized:
        state.vs_resources = _merge_slots(state.vs_resources, _resource_entries(element, "resource"))
    elif "pssetshaderresources" in normalized:
        state.ps_resources = _merge_slots(state.ps_resources, _resource_entries(element, "resource"))
    elif "vssetsamplers" in normalized:
        state.vs_samplers = _merge_slots(state.vs_samplers, _resource_entries(element, "sampler"))
    elif "pssetsamplers" in normalized:
        state.ps_samplers = _merge_slots(state.ps_samplers, _resource_entries(element, "sampler"))
    elif "omsetrendertargets" in normalized:
        state.render_targets = _resource_entries(element, "resource")
    elif "iasetprimitivetopology" in normalized:
        state.topology = _value(element, ("topology", "primitivetopology", "value"))
    elif "rssetviewports" in normalized:
        state.viewport = {}
        for key, aliases in (("top_left_x", ("topleftx", "top_left_x", "x")), ("top_left_y", ("toplefty", "top_left_y", "y")), ("width", ("width",)), ("height", ("height",)), ("min_depth", ("mindepth", "min_depth")), ("max_depth", ("maxdepth", "max_depth"))):
            value = _value(element, aliases)
            if value is not None:
                state.viewport[key] = _number(value)
    draw_type = _draw_type(operation)
    if draw_type:
        row = {"moment": _number(_value(element, ("moment", "event", "sequence", "index", "callindex"))), "draw_type": draw_type, "parameters": _draw_parameters(element)}
        row.update(_snapshot(state))
        row["m23_candidate"] = _candidate(state)
        return operation, row
    return operation, None


def parse_dxcap(source: str | Path | TextIO) -> dict[str, Any]:
    """Parse DXCap XML incrementally and return a JSON-serializable summary."""
    if hasattr(source, "read"):
        raw = source.read()
        if isinstance(raw, bytes):
            raw = re.sub(br"^\s*<\?xml[^>]*\?>", b"", raw, count=1)
            stream = io.BytesIO(b"<Capture>" + raw + b"</Capture>")
        else:
            raw = re.sub(r"^\s*<\?xml[^>]*\?>", "", raw, count=1)
            stream = io.StringIO("<Capture>" + raw + "</Capture>")
        source_name = getattr(source, "name", "<stream>")
        close_stream = True
    else:
        stream = _FragmentReader(open(source, "rb"))
        source_name = str(source)
        close_stream = True
    state = _State()
    draws: list[dict[str, Any]] = []
    calls = 0
    operations: dict[str, int] = {}
    # Only call-like elements are retained until their end event; children are
    # not cleared while inside one, keeping the whole XML document streaming.
    call_depth: int | None = None
    depth = 0
    last_moment: int | float | str | None = None
    try:
        for event, element in ET.iterparse(stream, events=("start", "end")):
            if event == "start":
                depth += 1
                if call_depth is None and _local(element.tag) in {"call", "api", "command", "event", "function", "method"}:
                    call_depth = depth
                continue
            if call_depth is None and _local(element.tag) == "moment":
                last_moment = _number(element.attrib.get("value"))
                element.clear()
            if call_depth == depth:
                calls += 1
                if last_moment is not None:
                    element.attrib["moment"] = str(last_moment)
                operation, draw = _apply(element, state)
                operations[operation] = operations.get(operation, 0) + 1
                if draw is not None:
                    if draw["moment"] is None:
                        draw["moment"] = calls
                    draws.append(draw)
                call_depth = None
                element.clear()
            elif call_depth is None:
                element.clear()
            depth -= 1
    except (ET.ParseError, OSError, UnicodeError) as exc:
        raise EvidenceParseError(f"failed to parse DXCap XML {source_name}: {exc}") from exc
    finally:
        if close_stream:
            stream.close()
    return {"schema": SCHEMA, "source": source_name, "calls_seen": calls, "draw_calls": draws, "operations": operations, "shader_creates": list(state.shaders.values()), "byte_hashes_available": False}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Summarize D3D11 draws from DXCap -toXML output")
    parser.add_argument("xml", type=Path)
    parser.add_argument("-o", "--output", type=Path)
    args = parser.parse_args(argv)
    try:
        report = parse_dxcap(args.xml)
    except EvidenceParseError as exc:
        report = {"schema": SCHEMA, "status": "parse_failed", "error": str(exc), "draw_calls": [], "byte_hashes_available": False}
        print(json.dumps(report, indent=2), file=sys.stderr)
        return 2
    payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(payload, encoding="utf-8", newline="\n")
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
