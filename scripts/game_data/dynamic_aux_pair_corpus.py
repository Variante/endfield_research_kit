"""Authenticate and compare paired DynamicStreaming fb_init/fb_streaming roots.

The selected native bridge separately proves consumption of paired root rows.
This gate reports stored FlatBuffer framing, paired byte/count relations, and
the ID/descriptor/blob structure. It also compares descriptor 21's bytes with
the same file's root ID/name-string rows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.game_data.dynamic_main_native import _checked_dump_path
from scripts.game_data.dynamic_stream_area_corpus import (
    DEFAULT_CLI,
    DEFAULT_LEDGER,
    DEFAULT_OUTER,
    load_current_inputs,
)
from scripts.game_data.dynamic_streaming import (
    _bounded_vector,
    _field_span,
    _root_layout,
    _table_layout,
    _u32,
    decode_dynamic_payload,
    iter_dynamic_aux_field5_table_views,
    parse_dynamic_aux_reference_shapes,
    parse_dynamic_file,
)
from scripts.repo_paths import REPO_ROOT


FILE_RE = re.compile(r"(?:^|/)fb_(?:init|streaming)_[^/]+\.bytes$", re.IGNORECASE)
NAME_RE = re.compile(r"^(?P<parent>.*)/fb_(?P<kind>init|streaming)_(?P<suffix>[^/]+)\.bytes$", re.IGNORECASE)
DEFAULT_JSON = REPO_ROOT / "reports/animestudio/dynamic_aux_pair_latest.json"
DEFAULT_MD = REPO_ROOT / "reports/animestudio/dynamic_aux_pair_latest.md"


class DynamicAuxPairError(ValueError):
    """A source, framing, or paired-current-corpus relation differs."""


def _table_vector_rows(data: bytes, field: int) -> list[dict[str, Any]]:
    root = _root_layout(data)
    body, count, _end = _bounded_vector(data, root, field, 4)
    rows = []
    for index in range(count):
        slot = body + index * 4
        relative = _u32(data, slot)
        if not relative or slot + relative <= slot:
            raise DynamicAuxPairError(f"field {field}[{index}]: invalid table offset")
        rows.append(_table_layout(data, slot + relative))
    return rows


def _root_id_name_pairs(data: bytes) -> Counter[tuple[int, bytes]]:
    """Read parallel root field-3 IDs and field-5 field-0 FlatBuffer strings."""
    root = _root_layout(data)
    ids_body, ids_count, _ = _bounded_vector(data, root, 3, 4)
    rows = _table_vector_rows(data, 5)
    if len(rows) != ids_count:
        raise DynamicAuxPairError("root ID/name row counts differ")
    pairs: Counter[tuple[int, bytes]] = Counter()
    for index, row in enumerate(rows):
        slot = _field_span(data, row, 0, 4)
        if slot is None:
            raise DynamicAuxPairError(f"root name row {index} lacks field zero")
        relative = _u32(data, slot)
        target = slot + relative
        if not relative or target <= slot or target + 4 > len(data):
            raise DynamicAuxPairError(f"root name row {index} has invalid string offset")
        length = _u32(data, target)
        end = target + 4 + length
        if not length or end >= len(data) or data[end] != 0:
            raise DynamicAuxPairError(f"root name row {index} has invalid string extent")
        pairs[(_u32(data, ids_body + 4 * index), data[target + 4:end])] += 1
    return pairs


def _padded_name_slot(value: bytes) -> bytes | None:
    """A bounded 64-byte slot can equal a FlatBuffer string only with zero padding."""
    if len(value) != 64 or b"\0" not in value:
        return None
    name, padding = value.split(b"\0", 1)
    return name if name and not any(padding) else None


def _check_consumer_groups(key: str, init: bytes, streaming: bytes) -> Counter[str]:
    """Check stored ID/descriptor/blob structure seen by the native consumer."""
    first_rows = _table_vector_rows(init, 7)
    second_rows = _table_vector_rows(streaming, 6)
    if len(first_rows) != len(second_rows):
        raise DynamicAuxPairError(f"{key}: paired consumer group counts differ")
    root = _root_layout(streaming)
    root_body, root_count, _ = _bounded_vector(streaming, root, 3, 4)
    root_ids = Counter(_u32(streaming, root_body + 4 * i) for i in range(root_count))
    group_ids: Counter[int] = Counter()
    root_names = _root_id_name_pairs(init)
    projected_names: Counter[tuple[int, bytes]] = Counter()
    for (item_id, name), count in root_names.items():
        projected_names[(item_id, name[:63])] += count
    descriptor_names: Counter[tuple[int, bytes]] = Counter()
    totals: Counter[str] = Counter()
    for ordinal, (first, second) in enumerate(zip(first_rows, second_rows, strict=True)):
        id_body, id_count, _ = _bounded_vector(streaming, second, 0, 4)
        descriptor_body, descriptor_count, _ = _bounded_vector(init, first, 3, 8)
        wrapper_slot = _field_span(init, first, 4, 4)
        if wrapper_slot is None or not _u32(init, wrapper_slot):
            raise DynamicAuxPairError(f"{key}: group {ordinal} lacks byte-blob wrapper")
        wrapper = _table_layout(init, wrapper_slot + _u32(init, wrapper_slot))
        blob_body, blob_count, _ = _bounded_vector(init, wrapper, 0, 1)
        group_ids.update(_u32(streaming, id_body + 4 * i) for i in range(id_count))
        expected_bytes = 0
        descriptor21_count = 0
        for index in range(descriptor_count):
            descriptor_id, stride, reserved = struct.unpack_from(
                "<hhI", init, descriptor_body + 8 * index
            )
            if stride <= 0 or reserved:
                raise DynamicAuxPairError(
                    f"{key}: group {ordinal} descriptor {index} has invalid stride/reserved word"
                )
            expected_bytes += id_count * stride
            totals["descriptors"] += 1
            if descriptor_id == 21 and stride == 64:
                totals["descriptor21Width64Rows"] += 1
                descriptor21_count += 1
                segment = init[blob_body + expected_bytes - id_count * stride:
                               blob_body + expected_bytes]
                for item in range(id_count):
                    name = _padded_name_slot(segment[item * stride:(item + 1) * stride])
                    if name is None:
                        raise DynamicAuxPairError(
                            f"{key}: group {ordinal} descriptor 21 name slot {item} is not zero-padded"
                        )
                    descriptor_names[(_u32(streaming, id_body + 4 * item), name)] += 1
                    totals["descriptor21NameSlots"] += 1
        if descriptor21_count != 1:
            raise DynamicAuxPairError(f"{key}: group {ordinal} expected one descriptor 21 name column")
        if expected_bytes != blob_count:
            raise DynamicAuxPairError(
                f"{key}: group {ordinal} descriptor-major bytes {expected_bytes} differ from blob {blob_count}"
            )
        totals["groups"] += 1
        totals["groupIds"] += id_count
        totals["blobBytes"] += blob_count
    if group_ids != root_ids:
        raise DynamicAuxPairError(f"{key}: grouped IDs do not partition root field 3")
    if descriptor_names != projected_names:
        missing = list((projected_names - descriptor_names).items())[:3]
        extra = list((descriptor_names - projected_names).items())[:3]
        raise DynamicAuxPairError(
            f"{key}: descriptor 21 ID/name pairs differ from root field 3/5 strings clipped to 63 bytes: "
            f"missing={missing} extra={extra}"
        )
    totals["rootIdPartitionPairs"] += 1
    totals["descriptor21RootNamePrefixPairs"] += 1
    totals["descriptor21ExactRootNames"] += sum(count for (_id, name), count in root_names.items() if len(name) <= 63)
    totals["descriptor21TruncatedRootNames"] += sum(count for (_id, name), count in root_names.items() if len(name) > 63)
    return totals


def pair_identity(virtual_path: str) -> tuple[str, str]:
    """Return normalized pair key and kind from an authenticated VFS path."""
    name = virtual_path.replace("\\", "/")
    match = NAME_RE.fullmatch(name)
    if not match:
        raise DynamicAuxPairError(f"unexpected auxiliary VFS path: {virtual_path}")
    return (match["parent"] + "/" + match["suffix"]).casefold(), match["kind"].casefold()


def _vector_bytes(decoded: bytes, vector: dict[str, Any]) -> bytes:
    start = int(vector["bodyOffset"])
    end = int(vector["endOffset"])
    if start < 0 or end < start or end > len(decoded):
        raise DynamicAuxPairError(f"auxiliary vector span {start}:{end} outside decoded payload")
    if end - start != int(vector["count"]) * int(vector["elementWidth"]):
        raise DynamicAuxPairError("auxiliary vector count/width does not match its span")
    return decoded[start:end]


def _check_pair(key: str, init: dict[str, Any], streaming: dict[str, Any]) -> Counter[str]:
    """Check only the cross-file equalities observed in the current corpus."""
    a, b = init["parsed"], streaming["parsed"]
    if a["ScalarFieldValues"] != b["ScalarFieldValues"]:
        raise DynamicAuxPairError(f"{key}: root scalar fields differ across pair")
    av, bv = a["Vectors"], b["Vectors"]
    if len(av) != 6 or len(bv) != 6 or any(v["fieldIndex"] != i for i, v in enumerate(av, 2)) or any(v["fieldIndex"] != i for i, v in enumerate(bv, 2)):
        raise DynamicAuxPairError(f"{key}: auxiliary vector field set differs")
    for member_name, member, vectors in (("init", init, av), ("streaming", streaming, bv)):
        # Field 3's four-byte stride exactly meets field 2's count word.
        if int(vectors[1]["endOffset"]) != int(vectors[0]["bodyOffset"]) - 4:
            raise DynamicAuxPairError(f"{key}: {member_name} field 3 does not meet field 2 count word")
        # Field 4 has only a one-byte lower bound. Its checked count-byte
        # prefix is followed by at most three zero bytes before the next
        # independently located count word. Those bytes could be padding or
        # part of wider elements, so they are not called a full vector body.
        end = int(vectors[2]["endOffset"])
        next_count_word = int(vectors[3]["bodyOffset"]) - 4
        gap = next_count_word - end
        if (gap not in (0, 1, 2, 3) or next_count_word % 4
                or any(member["decoded"][end:next_count_word])):
            raise DynamicAuxPairError(f"{key}: {member_name} field 4 prefix has an unexpected aligned tail")
    for field in (2, 3, 4):
        if _vector_bytes(init["decoded"], av[field - 2]) != _vector_bytes(streaming["decoded"], bv[field - 2]):
            part = "prefix" if field == 4 else "body"
            raise DynamicAuxPairError(f"{key}: vector field {field} checked {part} bytes differ across pair")
    if int(av[3]["count"]) != int(bv[3]["count"]):
        raise DynamicAuxPairError(f"{key}: vector field 5 counts differ across pair")
    if int(av[5]["count"]) != int(bv[4]["count"]):
        raise DynamicAuxPairError(f"{key}: init field 7 and streaming field 6 counts differ")
    if any(int(v["count"]) != 0 for v in (av[0], av[4], bv[0], bv[5])):
        raise DynamicAuxPairError(f"{key}: current empty auxiliary vector position differs")
    totals: Counter[str] = Counter()
    init_tables = iter_dynamic_aux_field5_table_views(init["decoded"], a)
    streaming_tables = iter_dynamic_aux_field5_table_views(streaming["decoded"], b)
    for first, second in zip(init_tables, streaming_tables, strict=True):
        index = first["index"]
        if index != second["index"] or first["presentFields"] != second["presentFields"]:
            raise DynamicAuxPairError(f"{key}: field 5 table {index} vtable mask differs across pair")
        totals["matchingField5TableMasks"] += 1
        for field in (1, 2):
            left, right = first["slots"][field], second["slots"][field]
            if left != right:
                raise DynamicAuxPairError(f"{key}: field 5 table {index} slot {field} raw bytes differ")
            if left is not None:
                totals[f"matchingField5Slot{field}FourByteValues"] += 1
        for field in (3, 4, 5):
            left, right = first["slots"][field], second["slots"][field]
            if left is not None and right is not None and left != right:
                totals[f"differingField5Slot{field}FourByteValues"] += 1
    totals.update(_check_consumer_groups(key, init["decoded"], streaming["decoded"]))
    return totals


def audit_current_pairs(
    *, outer_path: Path, ledger_path: Path, cli_path: Path, input_root: Path,
    expected_input_set_sha256: str,
) -> dict[str, Any]:
    """Join every pair to the current VFS ledger and check bounded framing."""
    outer, sources, provenance = load_current_inputs(
        outer_path, ledger_path, cli_path, expected_input_set_sha256,
        file_name_re=FILE_RE, selection_label="fb_init/fb_streaming",
    )
    by_key: dict[str, dict[str, dict[str, Any]]] = {}
    totals: Counter[str] = Counter()
    scalar_values: dict[int, Counter[int]] = {0: Counter(), 1: Counter()}
    vector_totals: dict[tuple[str, int], Counter[str]] = {
        (kind, field): Counter() for kind in ("init", "streaming") for field in range(2, 8)
    }
    nested_shapes: dict[tuple[str, int, int, int, tuple[int, ...]], int] = Counter()
    for source in sources:
        virtual_path = str(source["path"])
        key, kind = pair_identity(virtual_path)
        pair = by_key.setdefault(key, {})
        if kind in pair:
            raise DynamicAuxPairError(f"duplicate current auxiliary pair member: {virtual_path}")
        packed = _checked_dump_path(input_root, virtual_path).read_bytes()
        if len(packed) != int(source["declaredBytes"]) or hashlib.md5(packed).hexdigest().upper() != source["fileDataMd5"]:
            raise DynamicAuxPairError(f"{virtual_path}: dump length/MD5 differs from authenticated VFS row")
        parsed = parse_dynamic_file(kind, packed)
        decoded = decode_dynamic_payload(kind, packed)
        if parsed["decodedBytes"] != len(decoded):
            raise DynamicAuxPairError(f"{virtual_path}: decoded byte count differs")
        pair[kind] = {"path": virtual_path, "parsed": parsed, "decoded": decoded}
        totals[f"{kind}Files"] += 1
        totals[f"{kind}PackedBytes"] += len(packed)
        totals[f"{kind}DecodedBytes"] += len(decoded)
        for field, value in enumerate(parsed["ScalarFieldValues"]):
            scalar_values[field][int(value)] += 1
        for vector in parsed["Vectors"]:
            field = int(vector["fieldIndex"])
            _vector_bytes(decoded, vector)
            counts = vector_totals[(kind, field)]
            counts["files"] += 1
            counts["elements"] += int(vector["count"])
            counts["bodyBytes"] += int(vector["bodyBytes"])
            counts["nonemptyFiles"] += int(vector["count"] > 0)
        for table_vector in parse_dynamic_aux_reference_shapes(decoded, parsed):
            field = int(table_vector["fieldIndex"])
            for shape in table_vector["shapes"]:
                nested_shapes[(kind, field, int(shape["fieldCount"]),
                               int(shape["objectSize"]), tuple(shape["presentFields"]))] += int(shape["tables"])
    for key, pair in by_key.items():
        if set(pair) != {"init", "streaming"}:
            raise DynamicAuxPairError(f"{key}: missing auxiliary pair member; found {sorted(pair)}")
        totals.update(_check_pair(key, pair["init"], pair["streaming"]))
        totals["validatedPairs"] += 1
    return {
        "format": "endfield.dynamic-aux-pair-corpus.v3",
        "status": "validated",
        "inputSetSha256": outer["inputSetSha256"],
        "outer": {"reportSha256": provenance["outerReportSha256"],
                  "ledgerSha256": provenance["ledgerSha256"],
                  "ledgerFileRowCount": provenance["ledgerFileRowCount"]},
        "corpus": dict(totals),
        "scalarValues": [{"fieldIndex": field,
                          "values": [{"value": value, "files": count} for value, count in sorted(values.items())]}
                         for field, values in scalar_values.items()],
        "vectors": [{"kind": kind, "fieldIndex": field, **dict(vector_totals[(kind, field)])}
                    for kind in ("init", "streaming") for field in range(2, 8)],
        "nestedTableShapes": [
            {"kind": kind, "fieldIndex": field, "fieldCount": field_count,
             "objectSize": object_size, "presentFields": list(present), "tables": count}
            for (kind, field, field_count, object_size, present), count in sorted(nested_shapes.items())
        ],
        "pairRelation": {
            "exactEqualScalarFields": [0, 1],
            "exactEqualVectorBodies": [2, 3],
            "equalCountBytePrefixesWithZeroAlignedTail": [4],
            "equalCountVectorFields": [[5, 5], [7, 6]],
            "emptyVectorFields": {"init": [2, 6], "streaming": [2, 7]},
            "field5SameIndexTables": {
                "presentFieldMasks": "equal",
                "rawFourByteSlotsEqualWhenPresent": [1, 2],
                "otherRawFourByteSlots": "censused, not required to differ",
            },
            "consumerGroupStructure": "init field 7 row field 3 has eight-byte descriptor rows and row field 4 has a nested field-0 byte blob; paired streaming field 6 row field 0 has UInt32 IDs. The grouped ID multiset equals root field 3; descriptor stride times group ID count exactly partitions each blob. Every group has one descriptor 21 with 64-byte zero-padded name slots, and their (ID, name) multiset equals init root field-3 IDs paired by ordinal with field-5 row field-0 FlatBuffer strings after clipping each string to 63 bytes.",
        },
        "evidenceBoundary": {
            "exact": "All selected dumps match current authenticated VFS ledger length and FileDataMd5; every pair passes observed root framing and the recorded cross-file byte/count equalities. Same-index field-5 table vtable masks and present slot-1/2 first-four bytes agree. Field 4 equality covers its checked count-byte prefix, not an independently typed full vector body. The paired consumer group rows have bounded ID, descriptor and blob vectors; grouped IDs partition root field 3, and descriptor-count times stride exactly partitions each blob. Descriptor 21 is one 64-byte zero-padded name column per group; its (ID, name) pairs equal the init root ID/name-string rows after names longer than 63 bytes are clipped. The report separates exact names from clipped names.",
            "structuralOnly": "The separate selected native bridge contract proves direct consumption of the paired group vectors and descriptor-major byte copy. The stored name identity does not establish a named runtime component or downstream ownership.",
            "unresolved": "Semantic names for descriptor IDs other than 21, remaining nested element schemas, meanings of other root fields, and live file selection remain open.",
        },
    }


def _markdown(report: dict[str, Any]) -> str:
    c = report["corpus"]
    return "\n".join([
        "# DynamicStreaming auxiliary pair corpus", "",
        f"- Status: {report['status']}; authenticated pairs: {c['validatedPairs']:,}; init files: {c['initFiles']:,}; streaming files: {c['streamingFiles']:,}.",
        "- Root scalar fields 0 and 1 and vector bodies 2 and 3 match within every pair; field 4's checked count-byte prefix matches with a zero aligned tail; field 5 table masks and present slot-1/2 four-byte spans agree by index; init field 7 and streaming field 6 counts match.",
        f"- The paired consumer rows cover {c['groups']:,} groups and {c['groupIds']:,} IDs: streaming group IDs partition root field 3 within every pair, and each init descriptor-major blob has exact count × stride length.",
        f"- Descriptor 21 provides {c['descriptor21NameSlots']:,} zero-padded name slots in {c['descriptor21RootNamePrefixPairs']:,} pairs: {c['descriptor21ExactRootNames']:,} equal the root names exactly, and {c['descriptor21TruncatedRootNames']:,} equal their first 63 bytes.",
        "- This is authenticated stored identity. The selected native bridge proves the conditional copy; named runtime component ownership and live selection remain open.", "",
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--expected-input-set-sha256", required=True)
    parser.add_argument("--outer-report", type=Path, default=DEFAULT_OUTER)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--cli", type=Path, default=DEFAULT_CLI)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    args = parser.parse_args(argv)
    try:
        report = audit_current_pairs(
            outer_path=args.outer_report, ledger_path=args.ledger, cli_path=args.cli,
            input_root=args.input_root, expected_input_set_sha256=args.expected_input_set_sha256,
        )
    except (OSError, ValueError, KeyError, IndexError, RuntimeError) as error:
        print(f"dynamic-aux-pair-corpus: {error}", file=sys.stderr)
        return 1
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.output_md.write_text(_markdown(report), encoding="utf-8")
    print(f"validated {report['corpus']['validatedPairs']} DynamicStreaming auxiliary pairs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
