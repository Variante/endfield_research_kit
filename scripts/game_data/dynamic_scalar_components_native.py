"""Authenticate and census scalar inline components in current fb_main files.

The reviewed native contract names generated accessors, builders and a selected
MissionCondition string consumer. Field offsets, return types, record widths
and alignments close stored layouts; integer-valued flags and anonymous gaps
retain their representation. Authored string slots are separate from runtime
keys, condition evaluation, other control-ID targets and live activation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterator

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs, sha256_file
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.dynamic_main_native import _checked_dump_path, validate_native_layout as validate_main_layout
from scripts.game_data.dynamic_stream_area_corpus import DEFAULT_CLI, DEFAULT_LEDGER, DEFAULT_OUTER, MAIN_NAME_RE, load_current_inputs
from scripts.game_data.dynamic_streaming import _bounded_vector, _field_span, _root_layout, _table_layout, _validate_string_vector, parse_dynamic_file
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT


CONTRACT = CONTRACTS_DIR / "dynamic_scalar_components_native.json"
SCHEMA = "endfield.dynamic-scalar-components-native-contract.v3"
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_scalar_components_native_latest.json"
DEFAULT_MARKDOWN = REPO_ROOT / "reports/animestudio/dynamic_scalar_components_native_latest.md"
FIELD_FORMATS = {
    "System.Boolean": "<B", "System.Int32": "<i", "System.UInt32": "<I",
    "System.Int64": "<q", "System.UInt64": "<Q", "System.Single": "<f",
}


class DynamicScalarComponentsError(ValueError):
    """A native gate, scalar layout or authenticated payload differs."""


def _unique_immediate(raw: bytes, prefix: bytes, label: str) -> int:
    hits = list(re.finditer(re.escape(prefix) + b"(.)", raw, re.DOTALL))
    if len(hits) != 1:
        raise DynamicScalarComponentsError(f"{label}: expected one selected instruction, actual={len(hits)}")
    return hits[0][1][0]


def _getter_offset(raw: bytes, label: str) -> int:
    if raw.count(b"\x8b\x1b") != 1:  # mov ebx,[rbx]: inline carrier's position
        raise DynamicScalarComponentsError(f"{label}: inline base read differs")
    if b"\x8d\x53" in raw:  # lea edx,[rbx+field offset]
        return _unique_immediate(raw, b"\x8d\x53", label)
    if b"\x8b\xd3" not in raw:  # mov edx,ebx: field at base; patched fallback may also move rdx
        raise DynamicScalarComponentsError(f"{label}: zero-offset read differs")
    return 0


def _field_width(field: dict[str, Any], inline_types: dict[str, dict[str, Any]]) -> int:
    if field["type"] in inline_types:
        return int(inline_types[field["type"]]["width"])
    try:
        return struct.calcsize(FIELD_FORMATS[field["type"]])
    except KeyError as exc:
        raise DynamicScalarComponentsError(f"{field['name']}: unsupported stored type {field['type']}") from exc


def _flat_fields(record: dict[str, Any], inline_types: dict[str, dict[str, Any]], *, prefix: str = "", base: int = 0) -> Iterator[dict[str, Any]]:
    for field in record["fields"]:
        name = prefix + field["name"]
        offset = base + int(field["offset"])
        if field["type"] in inline_types:
            yield from _flat_fields(inline_types[field["type"]], inline_types, prefix=name + ".", base=offset)
        else:
            yield {**field, "name": name, "offset": offset}


def _flat_values(values: dict[str, Any], *, prefix: str = "") -> Iterator[tuple[str, Any]]:
    for name, value in values.items():
        if isinstance(value, dict):
            yield from _flat_values(value, prefix=prefix + name + ".")
        else:
            yield prefix + name, value


def _gaps(record: dict[str, Any], *, inline_types: dict[str, dict[str, Any]] | None = None) -> list[tuple[int, int]]:
    inline_types = inline_types or {}
    cursor, gaps = 0, []
    for field in sorted(record["fields"], key=lambda row: int(row["offset"])):
        start = int(field["offset"])
        width = _field_width(field, inline_types)
        if start < cursor or start + width > int(record["width"]):
            raise DynamicScalarComponentsError(f"{record['name']}.{field['name']}: overlapping or out-of-record field {start}+{width}")
        if start > cursor:
            gaps.append((cursor, start))
        cursor = start + width
    if cursor < int(record["width"]):
        gaps.append((cursor, int(record["width"])))
    return gaps


def _float32_getter_offset(raw: bytes, label: str) -> int:
    for witness in (b"\x0f\x10\x73\x08", b"\x48\x63\x3b", b"\x66\x48\x0f\x7e\xf3"):
        if raw.count(witness) != 1:
            raise DynamicScalarComponentsError(f"{label}: float32 carrier base witness differs")
    zero, later = b"\xf3\x0f\x10\x04\x1f", b"\xf3\x0f\x10\x44\x1f"
    if raw.count(zero) == 1 and later not in raw:
        return 0
    if zero in raw:
        raise DynamicScalarComponentsError(f"{label}: ambiguous float32 read")
    return _unique_immediate(raw, later, label)


def _nested_getter_offset(raw: bytes, label: str, helper: str) -> int:
    base, increment = ((b"\x8b\x17", b"\x83\xc2") if helper == "initialize" else (b"\x44\x8b\x07", b"\x41\x83\xc0"))
    if raw.count(base) != 1:
        raise DynamicScalarComponentsError(f"{label}: nested carrier base witness differs")
    return _unique_immediate(raw, increment, label) if increment in raw else 0


def _builder_struct_declarations(raw: bytes) -> list[tuple[int, int, int]]:
    """Recover the selected struct argument pair, including retained alignment."""
    direct = [(hit.start(), hit[1][0], hit[2][0]) for hit in re.finditer(b"\x41\x8d\x51(.)\x45\x8d\x41(.)", raw, re.DOTALL)]
    retained = [(hit.start(), hit[1][0], hit[2][0]) for hit in re.finditer(b"\x41\x8d\x69(.)\x8b\xd5\x45\x8d\x41(.)", raw, re.DOTALL)]
    return sorted(direct + retained)


def _validate_record(record: dict[str, Any], methods: dict[int, dict[str, Any]], raw: dict[int, bytes], *, inline_types: dict[str, dict[str, Any]] | None = None, carriers: dict[str, dict[str, Any]] | None = None) -> None:
    inline_types, carriers = inline_types or {}, carriers or {}
    fields = record["fields"]
    if not fields or len({f["name"] for f in fields}) != len(fields):
        raise DynamicScalarComponentsError(f"{record['name']}: empty or duplicate fields")
    _gaps(record, inline_types=inline_types)
    for field in fields:
        index = int(field["getterMethodIndex"])
        row = methods[index]
        if (row["type"] != record["type"] or row["method"] != "get_" + field["name"]
                or row["parameters"] or row["returnType"] != field["type"]):
            raise DynamicScalarComponentsError(f"{record['name']}.{field['name']}: selected getter identity/type differs")
        label = f"{record['name']}.{field['name']}"
        if field["type"] in inline_types:
            helper = field["carrierHelper"]
            target = _relative_call_target(raw[index], int(row["rva"]), int(field["carrierCallOffset"]), label)
            if target != int(carriers[helper]["rva"]):
                raise DynamicScalarComponentsError(f"{label}: selected carrier initializer call differs")
            actual = _nested_getter_offset(raw[index], label, helper)
        elif record.get("getterKind") == "inlineFloat32":
            if field["type"] != "System.Single":
                raise DynamicScalarComponentsError(f"{label}: inline float32 getter type differs")
            actual = _float32_getter_offset(raw[index], label)
        else:
            actual = _getter_offset(raw[index], label)
        if actual != int(field["offset"]):
            raise DynamicScalarComponentsError(f"{record['name']}.{field['name']}: offset expected={field['offset']} actual={actual}")
    index = int(record["builderMethodIndex"])
    builder = methods[index]
    flattened = list(_flat_fields(record, inline_types))
    expected = ["Google.FlatBuffers.FlatBufferBuilder", *(field["type"] for field in flattened)]
    if (builder["type"] != record["type"] or builder["method"] != "Create" + record["type"].rsplit(".", 1)[-1]
            or builder["parameters"] != expected
            or [name.casefold() for name in builder["parameterNames"][1:]] != [field["name"].replace(".", "_").casefold() for field in flattened]):
        raise DynamicScalarComponentsError(f"{record['name']}: builder identity/field parameters differ")
    if "builderStructInstructionOffset" in record:
        at = int(record["builderStructInstructionOffset"])
        declarations = _builder_struct_declarations(raw[index])
        if not declarations or at != declarations[0][0]:
            raise DynamicScalarComponentsError(f"{record['name']}: first builder struct declaration differs")
        _, alignment, width = declarations[0]
    else:
        alignment = _unique_immediate(raw[index], b"\x41\x8d\x51", record["name"] + " alignment")
        width = _unique_immediate(raw[index], b"\x45\x8d\x41", record["name"] + " width")
    if (alignment, width) != (int(record["alignment"]), int(record["width"])):
        raise DynamicScalarComponentsError(f"{record['name']}: width/alignment expected={record['width']}/{record['alignment']} actual={width}/{alignment}")


def _relative_call_target(raw: bytes, rva: int, offset: int, label: str) -> int:
    if offset < 0 or offset + 5 > len(raw) or raw[offset] != 0xE8:
        raise DynamicScalarComponentsError(f"{label}: expected direct call at offset={offset}")
    return rva + offset + 5 + struct.unpack_from("<i", raw, offset + 1)[0]


def _validate_string_consumers(layout: dict[str, Any], main: dict[str, Any], methods: dict[int, dict[str, Any]], raw: dict[int, bytes]) -> set[int]:
    selected, seen = set(), set()
    records = {record["name"]: record for record in layout["records"]}
    for join in layout.get("stringIndexConsumers", []):
        label = join["record"] + "." + join["field"]
        if label in seen:
            raise DynamicScalarComponentsError(f"{label}: duplicate string consumer")
        seen.add(label)
        field = next((field for field in records[join["record"]]["fields"] if field["name"] == join["field"]), None)
        if field is None or field["type"] != "System.Int32":
            raise DynamicScalarComponentsError(f"{label}: string source is not a selected Int32 getter")
        consumer_index, span_index, key_index = (int(join[key]) for key in ("consumerMethodIndex", "stringSpanMethodIndex", "runtimeKeyMethodIndex"))
        consumer, span, key = (methods[index] for index in (consumer_index, span_index, key_index))
        if (span["parameters"] != [main["rootType"], "System.Int32"] or span["method"] != "GetStrSpan"
                or consumer["method"] != "RegisterEntityCaredCondition" or key["method"] != "GetStrKey"):
            raise DynamicScalarComponentsError(f"{label}: typed string consumer identity differs")
        for offset_key, target_index in (("getterCallOffset", int(field["getterMethodIndex"])), ("spanCallOffset", span_index), ("runtimeKeyCallOffset", key_index)):
            actual = _relative_call_target(raw[consumer_index], int(consumer["rva"]), int(join[offset_key]), label)
            if actual != int(methods[target_index]["rva"]):
                raise DynamicScalarComponentsError(f"{label}: {offset_key} target expected={methods[target_index]['rva']} actual={actual}")
        at = int(join["getterResultArgumentOffset"])
        if raw[consumer_index][at:at + 3] != b"\x44\x8b\xc0":  # mov r8d,eax
            raise DynamicScalarComponentsError(f"{label}: getter return is not the string index argument")
        at = int(join["rootFieldInstructionOffset"])
        if at < 0 or at + 5 > len(raw[span_index]) or raw[span_index][at] != 0xBA:
            raise DynamicScalarComponentsError(f"{label}: selected root field instruction differs")
        slot = struct.unpack_from("<I", raw[span_index], at + 1)[0]
        field_index = int(join["rootStringsFieldIndex"])
        if field_index != int(main["rootStringsFieldIndex"]) or slot != 4 + field_index * 2:
            raise DynamicScalarComponentsError(f"{label}: root string vtable slot expected={4 + int(main['rootStringsFieldIndex']) * 2} actual={slot}")
        for probe in join["probes"]:
            index, at = int(probe["methodIndex"]), int(probe["offset"])
            expected = bytes.fromhex(probe["bytes"])
            if at < 0 or not expected or raw[index][at:at + len(expected)] != expected:
                raise DynamicScalarComponentsError(f"{label}: native argument/lookup witness differs method={index} offset={at} claim={probe['claim']}")
        selected.update((consumer_index, span_index, key_index))
    return selected


def _validate_carriers(layout: dict[str, Any], image: Any) -> dict[str, dict[str, Any]]:
    helpers, bodies = {}, {}
    for helper in layout.get("carrierHelpers", []):
        name, length = helper["name"], int(helper["bodyExtent"])
        if name in helpers or not 0 < length <= 256:
            raise DynamicScalarComponentsError(f"{name}: duplicate or invalid carrier helper")
        body = image.pe.bytes_at_va(image.pe.image_base + int(helper["rva"]), length)
        if hashlib.sha256(body).hexdigest().upper() != helper["bodySha256"].upper():
            raise DynamicScalarComponentsError(f"{name}: selected carrier helper hash differs")
        for probe in helper["probes"]:
            at, expected = int(probe["offset"]), bytes.fromhex(probe["bytes"])
            if at < 0 or not expected or body[at:at + len(expected)] != expected:
                raise DynamicScalarComponentsError(f"{name}: carrier witness differs offset={at} claim={probe['claim']}")
        helpers[name], bodies[name] = helper, body
    if helpers:
        if set(helpers) != {"initialize", "forward"}:
            raise DynamicScalarComponentsError("selected carrier helper roles differ")
        target = _relative_call_target(bodies["forward"], int(helpers["forward"]["rva"]), int(helpers["forward"]["initializerCallOffset"]), "forward")
        if target != int(helpers["initialize"]["rva"]):
            raise DynamicScalarComponentsError("forward carrier initializer target differs")
    return helpers


def validate_native_layout(gameassembly: Path, metadata: Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, str], dict[str, str]]:
    """Authenticate all selected accessors against the explicitly selected build."""
    contract, digest = read_reviewed_contract(CONTRACT, schema=SCHEMA, label="dynamic_scalar_components", status="validated")
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(inputs["gameAssemblySha256"], inputs["metadataSha256"], gameassembly=gameassembly, metadata=metadata)
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise DynamicScalarComponentsError(f"installed_native_inputs:{gate.status}:{gate.detail}")
    unity = Path(gameassembly).parent / "UnityPlayer.dll"
    if not unity.is_file():
        raise DynamicScalarComponentsError(f"installed_native_inputs:missing:{unity}")
    receipt = {"gameAssemblySha256": gate.gameassembly_sha256.upper(), "metadataSha256": gate.metadata_sha256.upper(), "unityPlayerSha256": sha256_file(unity).upper()}
    if receipt != inputs:
        raise DynamicScalarComponentsError("installed_native_inputs:mismatched:UnityPlayer.dll hash differs")
    main, main_digest, main_receipt = validate_main_layout(gameassembly, metadata)
    if main_receipt != receipt:
        raise DynamicScalarComponentsError("scalar and main native contracts select different builds")
    layout = contract["layout"]
    if layout["gridType"] != main["gridType"]:
        raise DynamicScalarComponentsError("scalar grid type differs from main layout")
    image = open_native_image(gameassembly, metadata)
    methods, raw = {}, {}
    for row in contract["methods"]:
        index = int(row["index"])
        if index in methods:
            raise DynamicScalarComponentsError(f"duplicate selected method index {index}")
        image.validate_method_row([index, row["type"], row["method"], int(row["rva"])], label="dynamic_scalar_components")
        method = image.metadata.methods[index]
        parameters = image.metadata.parameters_for(method)
        if ([image.metadata.metadata_type_name(p.type_index) for p in parameters] != row["parameters"]
                or [image.metadata.string(p.name_index) for p in parameters] != row["parameterNames"]
                or image.metadata.metadata_type_name(method.return_type) != row["returnType"]):
            raise DynamicScalarComponentsError(f"{row['type']}.{row['method']}: selected metadata signature differs")
        length = int(row["bodyExtent"])
        if not 0 < length <= 4096:
            raise DynamicScalarComponentsError(f"{row['type']}.{row['method']}: invalid body extent {length}")
        body = image.pe.bytes_at_va(image.pe.image_base + int(row["rva"]), length)
        if hashlib.sha256(body).hexdigest().upper() != row["bodySha256"].upper():
            raise DynamicScalarComponentsError(f"{row['type']}.{row['method']}: selected body hash differs")
        methods[index], raw[index] = row, body
    vectors = {int(v["fieldIndex"]): v for v in main["vectors"]}
    inline_names = layout.get("inlineTypes", [])
    inline_types = {record["type"]: record for record in layout["records"] if record["type"] in inline_names}
    if len(inline_names) != len(set(inline_names)) or set(inline_types) != set(inline_names):
        raise DynamicScalarComponentsError("absent or duplicate selected inline types")
    if any(field["type"] in inline_types for record in inline_types.values() for field in record["fields"]):
        raise DynamicScalarComponentsError("recursive selected inline types are unsupported")
    carriers = _validate_carriers(layout, image)
    names, selected = set(), set()
    for record in layout["records"]:
        vector = vectors[int(record["gridFieldIndex"])]
        if (record["name"] in names or vector["name"] != record["name"]
                or int(vector["elementWidth"]) != int(record["width"])):
            raise DynamicScalarComponentsError(f"{record['name']}: duplicate or mismatched main vector")
        names.add(record["name"])
        _validate_record(record, methods, raw, inline_types=inline_types, carriers=carriers)
        selected.update(int(f["getterMethodIndex"]) for f in record["fields"])
        selected.add(int(record["builderMethodIndex"]))
    selected.update(_validate_string_consumers(layout, main, methods, raw))
    if selected != set(methods):
        raise DynamicScalarComponentsError("unused or absent selected scalar method")
    return layout, main, {"scalarComponentsContractSha256": digest, "mainVectorContractSha256": main_digest}, receipt


def _decode_record(data: bytes, start: int, record: dict[str, Any], source: str, *, inline_types: dict[str, dict[str, Any]] | None = None) -> tuple[dict[str, Any], bool]:
    inline_types = inline_types or {}
    if start < 0 or start + int(record["width"]) > len(data):
        raise DynamicScalarComponentsError(f"{source}: {record['name']} record exceeds payload {start}+{record['width']}/{len(data)}")
    gaps = _gaps(record, inline_types=inline_types)
    values = {}
    nested_gap = False
    for field in record["fields"]:
        if field["type"] in inline_types:
            values[field["name"]], child_gap = _decode_record(data, start + int(field["offset"]), inline_types[field["type"]], source + ": " + field["name"], inline_types=inline_types)
            nested_gap |= child_gap
            continue
        value = struct.unpack_from(FIELD_FORMATS[field["type"]], data, start + int(field["offset"]))[0]
        if field["type"] == "System.Boolean" and value not in (0, 1):
            raise DynamicScalarComponentsError(f"{source}: {record['name']}.{field['name']} Boolean expected=0|1 actual={value}")
        values[field["name"]] = value
    return values, nested_gap or any(any(data[start + a:start + b]) for a, b in gaps)


def _resolve_string_index(strings: list[str], index: int) -> dict[str, Any]:
    """Mirror the selected GetStrSpan bound, including its empty fallback."""
    if not 0 <= index < len(strings):
        return {"index": index, "status": "out_of_range_empty_span", "text": ""}
    return {"index": index, "status": "resolved", "text": strings[index]}


def _payload_records(data: bytes, *, layout: dict[str, Any], widths: dict[int, int], source: str) -> Iterator[dict[str, Any]]:
    parse_dynamic_file("main", data, main_vector_widths=widths)
    root = _root_layout(data)
    joins = layout.get("stringIndexConsumers", [])
    inline_types = {record["type"]: record for record in layout["records"] if record["type"] in layout.get("inlineTypes", [])}
    strings = []
    if joins:
        string_body, string_count, _ = _bounded_vector(data, root, int(joins[0]["rootStringsFieldIndex"]), 4)
        spans = _validate_string_vector(data, string_body, string_count)
        strings = [data[start + 4:end - 1].decode("utf-8", errors="strict") for start, end, _ in spans]
    body, count, _ = _bounded_vector(data, root, 3, 4)
    for grid in range(count):
        slot = body + grid * 4
        table = _table_layout(data, slot + struct.unpack_from("<I", data, slot)[0])
        uid = _field_span(data, table, 0, 4)
        if uid is None:
            raise DynamicScalarComponentsError(f"{source}: grid[{grid}] has no UniqueId")
        unique_id = struct.unpack_from("<I", data, uid)[0]
        for record in layout["records"]:
            vector_body, vector_count, _ = _bounded_vector(data, table, int(record["gridFieldIndex"]), int(record["width"]))
            for ordinal in range(vector_count):
                label = f"{source}: grid[{grid}] UniqueId={unique_id} {record['name']}[{ordinal}]"
                values, nonzero_gap = _decode_record(data, vector_body + ordinal * int(record["width"]), record, label, inline_types=inline_types)
                references = {join["field"]: _resolve_string_index(strings, int(values[join["field"]])) for join in joins if join["record"] == record["name"]}
                yield {"name": record["name"], "gridOrdinal": grid, "uniqueId": unique_id, "ordinal": ordinal, "values": values, "stringReferences": references, "nonzeroGap": nonzero_gap}


def decode_authenticated_main(data: bytes, *, layout: dict[str, Any], main: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    """Decode existing bytes using a native layout and current VFS receipt.

    ``layout`` and ``main`` must come from :func:`validate_native_layout`;
    ``source`` must be a selected main row from ``load_current_inputs``.
    Callers may cache both gates for one batch and read exported raw bytes.
    This function performs no extraction and does not trust report samples.
    """
    path = source["path"]
    md5 = hashlib.md5(data).hexdigest().upper()
    expected_md5 = source["fileDataMd5"].upper()
    if len(data) != int(source["declaredBytes"]) or md5 != expected_md5:
        raise DynamicScalarComponentsError(f"{path}: authenticated byte join failed length={len(data)}/{source['declaredBytes']} md5={md5}/{expected_md5}")
    widths = {int(v["fieldIndex"]): int(v["elementWidth"]) for v in main["vectors"]}
    try:
        return list(_payload_records(data, layout=layout, widths=widths, source=path))
    except (ValueError, OverflowError) as exc:
        raise DynamicScalarComponentsError(f"{path}: sourceMd5={md5}: scalar framing failed: {exc}") from exc


def audit_current_main(layout: dict[str, Any], main: dict[str, Any], *, outer_path: Path, ledger_path: Path, cli_path: Path, input_root: Path, expected_input_set_sha256: str) -> dict[str, Any]:
    outer, current_files, provenance = load_current_inputs(outer_path, ledger_path, cli_path, expected_input_set_sha256, file_name_re=MAIN_NAME_RE, selection_label="fb_main_*.bytes")
    totals, counts, gap_counts = Counter(), Counter(), Counter()
    field_values, grids, samples = defaultdict(Counter), defaultdict(set), defaultdict(list)
    string_values, string_statuses = defaultdict(Counter), defaultdict(Counter)
    file_receipts = []
    seen = set()
    inline_types = {record["type"]: record for record in layout["records"] if record["type"] in layout.get("inlineTypes", [])}
    for source in current_files:
        path = source["path"]
        identity = path.replace("\\", "/").casefold()
        if identity in seen:
            raise DynamicScalarComponentsError(f"duplicate current main path: {path}")
        seen.add(identity)
        data = _checked_dump_path(input_root, path).read_bytes()
        md5 = hashlib.md5(data).hexdigest().upper()
        decoded = decode_authenticated_main(data, layout=layout, main=main, source=source)
        file_receipts.append({"path": path, "declaredBytes": len(data), "fileDataMd5": md5, "sha256": hashlib.sha256(data).hexdigest().upper(), "decodedRecords": len(decoded)})
        for record in decoded:
            name = record["name"]
            counts[name] += 1
            grids[name].add((identity, record["gridOrdinal"]))
            gap_counts[name] += record["nonzeroGap"]
            flattened_values = dict(_flat_values(record["values"]))
            for field, value in flattened_values.items():
                if isinstance(value, float) and not math.isfinite(value):
                    value = repr(value)
                field_values[name, field][value] += 1
            for field, reference in record["stringReferences"].items():
                string_values[name, field][reference["text"]] += 1
                string_statuses[name, field][reference["status"]] += 1
            if len(samples[name]) < 8:
                samples[name].append({"source": path, "sourceMd5": md5, "gridOrdinal": record["gridOrdinal"], "uniqueId": record["uniqueId"], "ordinal": record["ordinal"], "values": {k: repr(v) if isinstance(v, float) and not math.isfinite(v) else v for k, v in flattened_values.items()}, "stringReferences": record["stringReferences"]})
        totals.update({"files": 1, "bytes": len(data)})
    rows = []
    for record in layout["records"]:
        name = record["name"]
        fields = []
        for field in _flat_fields(record, inline_types):
            observed = field_values[name, field["name"]]
            numeric = [v for v in observed if isinstance(v, (int, float))]
            fields.append({"name": field["name"], "type": field["type"], "offset": field["offset"], "distinctValues": len(observed), "minimum": min(numeric) if numeric else None, "maximum": max(numeric) if numeric else None, "commonValues": [{"value": value, "count": count} for value, count in sorted(observed.items(), key=lambda item: (-item[1], repr(item[0])))[:12]]})
        references = []
        for join in layout.get("stringIndexConsumers", []):
            if join["record"] != name:
                continue
            field = join["field"]
            observed = string_values[name, field]
            references.append({"field": field, "rootStringsFieldIndex": join["rootStringsFieldIndex"], "statuses": dict(string_statuses[name, field]), "distinctStrings": len(observed), "commonStrings": [{"text": value, "count": count} for value, count in sorted(observed.items(), key=lambda item: (-item[1], item[0]))[:12]], "evidenceBoundary": join["evidenceBoundary"]})
        rows.append({"name": name, "gridFieldIndex": record["gridFieldIndex"], "width": record["width"], "alignment": record["alignment"], "recordCount": counts[name], "populatedGrids": len(grids[name]), "unassignedByteSpans": [list(span) for span in _gaps(record, inline_types=inline_types)], "recordsWithNonzeroUnassignedBytes": gap_counts[name], "fields": fields, "stringIndexFields": references, "samples": samples[name]})
    totals["records"] = sum(counts.values())
    return {"format": "endfield.dynamic-scalar-components-native-audit.v3", "status": "validated", "inputSetSha256": outer["inputSetSha256"], "outer": {"reportSha256": provenance["outerReportSha256"], "ledgerSha256": provenance["ledgerSha256"]}, "corpus": dict(totals), "files": file_receipts, "records": rows, "evidenceBoundary": "Generated getter names, return types and offsets authenticate stored fields; builder parameters, width and alignment authenticate each inline record. Selected Vector3 float32 reads and nested carrier initializers establish stored X/Y/Z fields without world-space or rotation-unit claims. Main allocation framing and current VFS byte joins precede decoding. A selected direct MissionCondition.Id consumer establishes its root TotalStr index; its authored text is separate from the allocated runtime key. Integer flags remain integers; other targets, enum meanings, live evaluations and activation remain unresolved."}


def _markdown(report: dict[str, Any]) -> str:
    lines = ["# DynamicStreaming scalar component audit", "", f"- Status: `{report['status']}`; files: {report['corpus']['files']:,}; records: {report['corpus']['records']:,}.", "- " + report["evidenceBoundary"], "", "| Component | Width | Records | Populated grids | Unassigned bytes | Nonzero gap records |", "|---|---:|---:|---:|---|---:|"]
    for row in report["records"]:
        lines.append(f"| `{row['name']}` | {row['width']} | {row['recordCount']:,} | {row['populatedGrids']:,} | {row['unassignedByteSpans']} | {row['recordsWithNonzeroUnassignedBytes']:,} |")
    for row in report["records"]:
        lines.extend(["", "## " + row["name"], "", "| Field | Native type | Offset | Distinct values | Range |", "|---|---|---:|---:|---|"])
        for field in row["fields"]:
            lines.append(f"| `{field['name']}` | `{field['type']}` | {field['offset']} | {field['distinctValues']:,} | {field['minimum']}..{field['maximum']} |")
        for reference in row["stringIndexFields"]:
            lines.extend(["", f"`{reference['field']}` → root TotalStr[{reference['rootStringsFieldIndex']}], statuses: {reference['statuses']}; distinct text: {reference['distinctStrings']:,}.", "", reference["evidenceBoundary"], "", "| Authored text | Records |", "|---|---:|"])
            for observed in reference["commonStrings"]:
                escaped = observed["text"].replace("|", "\\|").replace("\n", "\\n").replace("\r", "\\r")
                lines.append(f"| `{escaped}` | {observed['count']:,} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gameassembly", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args(argv)
    try:
        layout, main_layout, digests, receipt = validate_native_layout(args.gameassembly, args.metadata)
        report = audit_current_main(layout, main_layout, outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli, input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256)
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-scalar-components-native-audit: {error}", file=sys.stderr)
        return 1
    report.update({"contracts": digests, "nativeInputs": receipt})
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"DynamicStreaming scalar component audit passed: files={report['corpus']['files']} records={report['corpus']['records']} layouts={len(report['records'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
