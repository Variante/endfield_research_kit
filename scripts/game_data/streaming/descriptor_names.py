"""Read InitChunkData descriptor-21 name prefixes and compare storage layouts.

The CLI accepts AnimeStudio.CLI ``stream --verify-md5 --block-type streaming``
JSONL for a bounded reproduction. ``descriptor_name_corpus`` applies the same
reader to every authenticated Init logical file. Neither route assigns a
native component name or runtime behavior to the descriptor ID.
"""

from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.streaming.framing import (
    _bounded_vector,
    _decode_compressed,
    _field_address,
    _root_layout,
    _table_layout,
    parse_streaming_file,
)
from scripts.game_data.streaming.corpus import RAW_DATA_EXCEPTIONS


SCHEMA = "endfield.streaming-descriptor-name-join.v3"
NAME_DESCRIPTOR_ID = 21
NAME_WIDTH = 64


def _u32(data: bytes, address: int) -> int:
    return struct.unpack_from("<I", data, address)[0]


def _table_vector(data: bytes, table: dict[str, Any], field: int, label: str) -> list[dict[str, Any]]:
    start, count, _end = _bounded_vector(data, table, field, 4, label)
    result = []
    for index in range(count):
        slot = start + 4 + index * 4
        relative = _u32(data, slot)
        if not relative or slot + relative <= slot:
            raise ValueError(f"{label} row {index}: expected forward table offset")
        result.append(_table_layout(data, slot + relative))
    return result


def _root_pairs(data: bytes, root: dict[str, Any]) -> Counter[tuple[int, bytes]]:
    ids_start, count, _ = _bounded_vector(data, root, 3, 4, "root field 3 ids")
    rows = _table_vector(data, root, 5, "root field 5 rows")
    if len(rows) != count:
        raise ValueError(f"root parallel count: expected {count}, actual {len(rows)}")
    pairs: Counter[tuple[int, bytes]] = Counter()
    for index, row in enumerate(rows):
        name_slot = _field_address(row, 0)
        if name_slot is None:
            raise ValueError(f"root field 5 row {index}: missing field 0")
        target = name_slot + _u32(data, name_slot)
        if target <= name_slot or target + 4 > len(data):
            raise ValueError(f"root field 5 row {index}: invalid name target {target}")
        length = _u32(data, target)
        end = target + 4 + length
        if end >= len(data) or data[end] != 0:
            raise ValueError(f"root field 5 row {index}: invalid string boundary {end}")
        key = _u32(data, ids_start + 4 + index * 4)
        pairs[(key, data[target + 4 : end])] += 1
    return pairs


def _name_slot(value: bytes) -> bytes | None:
    """Return printable text from one NUL-terminated, 64-byte name slot."""
    if len(value) != NAME_WIDTH or b"\0" not in value:
        return None
    name, tail = value.split(b"\0", 1)
    if not name or any(tail):
        return None
    if any(byte < 0x20 or byte >= 0x7F for byte in name):
        return None
    return name


def audit_packed_init(packed: bytes, *, virtual_path: str) -> dict[str, Any]:
    """Compare both byte layouts with same-file root (ID, full name/prefix)."""
    if not virtual_path.rsplit("/", 1)[-1].startswith("InitChunkData_"):
        raise ValueError(f"{virtual_path}: expected InitChunkData filename")
    parsed = parse_streaming_file(
        "init", packed, allow_raw=virtual_path in RAW_DATA_EXCEPTIONS
    )
    if parsed["encoding"] == "inverted_lz4":
        clear = _decode_compressed(packed)
    elif parsed["encoding"] == "raw_flatbuffer" and virtual_path in RAW_DATA_EXCEPTIONS:
        clear = packed
    else:
        raise ValueError(f"{virtual_path}: unsupported Init envelope {parsed['encoding']}")
    root = _root_layout(clear)
    root["tableOffset"] = root["rootOffset"]
    reference_pairs = _root_pairs(clear, root)
    id_wrappers = _table_vector(clear, root, 6, "root field 6 wrappers")
    groups = _table_vector(clear, root, 7, "root field 7 groups")
    if len(id_wrappers) != len(groups):
        raise ValueError(f"{virtual_path}: group count mismatch {len(id_wrappers)}/{len(groups)}")

    reference_prefix_pairs: Counter[tuple[int, bytes]] = Counter()
    for (key, name), count in reference_pairs.items():
        reference_prefix_pairs[(key, name[:NAME_WIDTH - 1])] += count
    descriptor_pairs: Counter[tuple[int, bytes]] = Counter()
    row_pairs: Counter[tuple[int, bytes]] = Counter()
    name_groups = name_slots = descriptor_valid = row_valid = 0
    invalid_name_samples: list[dict[str, Any]] = []
    for group_index, (wrapper, group) in enumerate(zip(id_wrappers, groups)):
        ids_start, count, _ = _bounded_vector(clear, wrapper, 0, 4, "group ids")
        group_count_slot = _field_address(group, 1)
        if group_count_slot is None or _u32(clear, group_count_slot) != count:
            raise ValueError(f"{virtual_path}: group {group_index} ID/count mismatch")
        ids = [_u32(clear, ids_start + 4 + index * 4) for index in range(count)]
        descriptor_start, descriptor_count, _ = _bounded_vector(
            clear, group, 3, 8, "group descriptors"
        )
        descriptors = [
            struct.unpack_from("<HHI", clear, descriptor_start + 4 + index * 8)
            for index in range(descriptor_count)
        ]
        blob_slot = _field_address(group, 4)
        if blob_slot is None:
            raise ValueError(f"{virtual_path}: group {group_index} missing blob wrapper")
        blob_wrapper = _table_layout(clear, blob_slot + _u32(clear, blob_slot))
        blob_start, blob_length, blob_end = _bounded_vector(
            clear, blob_wrapper, 0, 1, "group blob"
        )
        blob = clear[blob_start + 4 : blob_end]
        if blob_length != count * sum(stride for _id, stride, _reserved in descriptors):
            raise ValueError(f"{virtual_path}: group {group_index} descriptor/blob length mismatch")
        if sum(did == NAME_DESCRIPTOR_ID for did, _stride, _reserved in descriptors) != 1:
            raise ValueError(f"{virtual_path}: group {group_index} expected one descriptor 21")
        cursor = 0
        row_offset = 0
        row_width = sum(stride for _id, stride, _reserved in descriptors)
        for descriptor_id, stride, reserved in descriptors:
            if reserved:
                raise ValueError(f"{virtual_path}: group {group_index} nonzero descriptor reserved word")
            segment = blob[cursor : cursor + count * stride]
            if descriptor_id == NAME_DESCRIPTOR_ID:
                if stride != NAME_WIDTH:
                    raise ValueError(f"{virtual_path}: group {group_index} descriptor 21 width {stride}")
                name_groups += 1
                for index, key in enumerate(ids):
                    name_slots += 1
                    descriptor_name = _name_slot(segment[index * stride : (index + 1) * stride])
                    row_name = _name_slot(
                        blob[index * row_width + row_offset : index * row_width + row_offset + stride]
                    )
                    if descriptor_name is not None:
                        descriptor_valid += 1
                        descriptor_pairs[(key, descriptor_name)] += 1
                    elif len(invalid_name_samples) < 12:
                        invalid_name_samples.append({
                            "groupIndex": group_index,
                            "rowIndex": index,
                            "id": key,
                            "rawHex": segment[index * stride : (index + 1) * stride].hex(),
                        })
                    if row_name is not None:
                        row_valid += 1
                        row_pairs[(key, row_name)] += 1
            cursor += count * stride
            row_offset += stride
        if cursor != blob_length:
            raise ValueError(f"{virtual_path}: group {group_index} unconsumed blob bytes")

    descriptor_full_matches = sum((descriptor_pairs & reference_pairs).values())
    descriptor_prefix_matches = sum((descriptor_pairs & reference_prefix_pairs).values())
    row_full_matches = sum((row_pairs & reference_pairs).values())
    row_prefix_matches = sum((row_pairs & reference_prefix_pairs).values())
    descriptor_only = descriptor_pairs - reference_prefix_pairs
    root_only = reference_prefix_pairs - descriptor_pairs
    def samples(pairs: Counter[tuple[int, bytes]]) -> list[dict[str, Any]]:
        return [
            {"id": key, "name": name.decode("utf-8", errors="replace"), "count": count}
            for (key, name), count in sorted(pairs.items())[:12]
        ]
    return {
        "virtualPath": virtual_path,
        "packedMd5": hashlib.md5(packed).hexdigest().upper(),
        "decodedSha256": hashlib.sha256(clear).hexdigest().upper(),
        "decodedBytes": len(clear),
        "groupCount": len(groups),
        "descriptor21Groups": name_groups,
        "descriptor21Slots": name_slots,
        "descriptorMajorValidNameSlots": descriptor_valid,
        "descriptorMajorExactRootPairs": descriptor_full_matches,
        "descriptorMajorExactRootPrefixPairs": descriptor_prefix_matches,
        "truncatedRootNamePairs": sum(
            count for (_key, name), count in reference_pairs.items() if len(name) >= NAME_WIDTH
        ),
        "descriptorPairsOutsideRootPrefix": sum(descriptor_only.values()),
        "rootPrefixPairsOutsideDescriptor": sum(root_only.values()),
        "descriptorPairsOutsideRootPrefixSamples": samples(descriptor_only),
        "rootPrefixPairsOutsideDescriptorSamples": samples(root_only),
        "invalidNameSamples": invalid_name_samples,
        "rowMajorValidNameSlots": row_valid,
        "rowMajorExactRootPairs": row_full_matches,
        "rowMajorExactRootPrefixPairs": row_prefix_matches,
        "rootPairs": sum(reference_pairs.values()),
        "evidenceBoundary": "Same-file decoded-byte full-name and 63-byte prefix comparisons; the slot does not preserve omitted suffix bytes. No runtime ownership is inferred.",
    }


def audit_stream_jsonl(input_path: Path, *, expected_report: Path | None = None) -> dict[str, Any]:
    expected = None
    if expected_report is not None:
        report = json.loads(expected_report.read_text(encoding="utf-8-sig"))
        expected = {row["virtualPath"]: row for row in report["files"]}
    rows = []
    seen: set[str] = set()
    with input_path.open("r", encoding="utf-8-sig") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            record = json.loads(line)
            path = record["fileName"]
            if path in seen:
                raise ValueError(f"line {line_number}: duplicate path {path}")
            seen.add(path)
            packed = base64.b64decode(record["dataBase64"], validate=True)
            if len(packed) != record["length"]:
                raise ValueError(f"line {line_number}: packed length mismatch for {path}")
            row = audit_packed_init(packed, virtual_path=path)
            if expected is not None:
                known = expected.get(path)
                if known is None:
                    raise ValueError(f"line {line_number}: source path absent from expected report: {path}")
                for key in ("packedMd5", "decodedSha256"):
                    if row[key] != known[key]:
                        raise ValueError(f"line {line_number}: {path} {key} mismatch: {row[key]} / {known[key]}")
            rows.append(row)
    if not rows:
        raise ValueError(f"{input_path}: no streamed files")
    keys = (
        "groupCount", "descriptor21Groups", "descriptor21Slots",
        "descriptorMajorValidNameSlots", "descriptorMajorExactRootPairs",
        "descriptorMajorExactRootPrefixPairs", "truncatedRootNamePairs",
        "descriptorPairsOutsideRootPrefix", "rootPrefixPairsOutsideDescriptor",
        "rowMajorValidNameSlots", "rowMajorExactRootPairs",
        "rowMajorExactRootPrefixPairs", "rootPairs",
    )
    totals = {key: sum(row[key] for row in rows) for key in keys}
    complete = (
        totals["groupCount"] == totals["descriptor21Groups"]
        and totals["descriptor21Slots"] == totals["descriptorMajorValidNameSlots"]
        == totals["descriptorMajorExactRootPrefixPairs"]
    )
    return {
        "schema": SCHEMA,
        "status": "complete-bounded-direct-prefix-join" if complete else "bounded-counterexample",
        "fileCount": len(rows),
        "sourceHashCheck": "matched-expected-report" if expected is not None else "stream-hashes-observed",
        "totals": totals,
        "files": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-jsonl", type=Path, required=True)
    parser.add_argument("--expected-report", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit_stream_jsonl(args.input_jsonl, expected_report=args.expected_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(result["status"], result["fileCount"], result["totals"])
    return 0 if result["status"] == "complete-bounded-direct-prefix-join" else 1


if __name__ == "__main__":
    raise SystemExit(main())
