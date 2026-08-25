#!/usr/bin/env python3
"""Decode a selectively captured Endfield GPU skin-matrix palette.

The recovered CharacterNPR Skin PreGBuffer vertex shader treats ``vs-t0`` as
a ByteAddressBuffer of float4 records.  Its per-instance metadata supplies two
base record indices; the shader adds three records and then addresses each bone
as three consecutive float4 rows.  The x base drives the current vertex
position, while the y base supplies previous-frame motion-vector positions.

This tool deliberately requires the effective (post ``+ 3``) base row.  The
captured constant-buffer range needed to recover that value is not available
in the older descriptor-only FrameAnalysis captures, so guessing it would turn
unrelated records into plausible-looking matrices.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import struct
import sys
from pathlib import Path
from typing import Iterable


EXPECTED_RESOURCE_HASH = "554904b3"
EXPECTED_BYTE_WIDTH = 8_413_184
EXPECTED_STRIDE = 16
ROWS_PER_MATRIX = 3
EXPECTED_CONSTANT_BUFFER_HASH = "a517561d"
EXPECTED_CONSTANT_BUFFER_BYTE_WIDTH = 4_194_304


class CaptureError(ValueError):
    """Raised when capture evidence is absent, ambiguous, or inconsistent."""


def parse_descriptor(path: Path) -> dict[str, object]:
    try:
        text = path.read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise CaptureError(f"cannot read descriptor {path}: {exc}") from exc
    fields = re.findall(r'(\w+)=(?:"([^"]*)"|(\S+))', text)
    parsed = {key: quoted or bare for key, quoted, bare in fields}
    for required in ("type", "byte_width", "stride"):
        if required not in parsed:
            raise CaptureError(f"descriptor {path} lacks {required}")
    try:
        parsed["byte_width"] = int(str(parsed["byte_width"]), 10)
        parsed["stride"] = int(str(parsed["stride"]), 10)
    except ValueError as exc:
        raise CaptureError(f"descriptor {path} has a non-integer size or stride") from exc
    return parsed


def select_resource(capture_dir: Path, draw: int) -> tuple[Path, Path]:
    if not capture_dir.is_dir():
        raise CaptureError(f"capture directory does not exist: {capture_dir}")
    prefix = f"{draw:06d}-vs-t0={EXPECTED_RESOURCE_HASH}-"
    descriptors = sorted(
        path for path in capture_dir.glob(f"{prefix}*.dsc") if path.is_file()
    )
    if len(descriptors) != 1:
        raise CaptureError(
            f"expected exactly one draw {draw:06d} vs-t0={EXPECTED_RESOURCE_HASH} "
            f"descriptor in {capture_dir}, found {len(descriptors)}"
        )
    descriptor = descriptors[0]
    payload = descriptor.with_suffix(".buf")
    if not payload.is_file():
        raise CaptureError(
            f"binary payload is missing for {descriptor.name}; recapture with the "
            "3DMigoto 'buf' analysis option"
        )
    return descriptor, payload


def select_constant_buffer(capture_dir: Path, draw: int, slot: int = 2) -> tuple[Path, Path]:
    prefix = f"{draw:06d}-vs-cb{slot}={EXPECTED_CONSTANT_BUFFER_HASH}-"
    descriptors = sorted(
        path for path in capture_dir.glob(f"{prefix}*.dsc") if path.is_file()
    )
    if len(descriptors) != 1:
        raise CaptureError(
            f"expected exactly one draw {draw:06d} vs-cb{slot}="
            f"{EXPECTED_CONSTANT_BUFFER_HASH} descriptor in {capture_dir}, "
            f"found {len(descriptors)}"
        )
    descriptor = descriptors[0]
    payload = descriptor.with_suffix(".buf")
    if not payload.is_file():
        raise CaptureError(
            f"binary constant-buffer payload is missing for {descriptor.name}; "
            "recapture with the 3DMigoto 'buf' analysis option"
        )
    return descriptor, payload


def parse_constant_buffer_range(log_path: Path, draw: int, slot: int = 2) -> tuple[int, int]:
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise CaptureError(f"cannot read frame-analysis log {log_path}: {exc}") from exc
    call_pattern = re.compile(
        rf"^{draw:06d} VSSetConstantBuffers1\(StartSlot:{slot}, NumBuffers:(\d+),"
    )
    value_pattern = re.compile(
        rf"^\s+{slot}: first_constant=(\d+) num_constants=(\d+)\s*$"
    )
    matches: list[tuple[int, int]] = []
    for index, line in enumerate(lines):
        call = call_pattern.match(line)
        if call is None:
            continue
        if int(call.group(1), 10) != 1:
            raise CaptureError(
                f"draw {draw:06d} slot {slot} range logger reported an unexpected "
                f"NumBuffers={call.group(1)}"
            )
        if index + 1 >= len(lines):
            raise CaptureError(f"draw {draw:06d} slot {slot} range log is truncated")
        value = value_pattern.match(lines[index + 1])
        if value is None:
            raise CaptureError(
                f"draw {draw:06d} slot {slot} lacks numeric first_constant/"
                "num_constants evidence; use the observer-only range-logging build"
            )
        matches.append((int(value.group(1), 10), int(value.group(2), 10)))
    if len(matches) != 1:
        raise CaptureError(
            f"expected exactly one draw {draw:06d} VS slot {slot} range in "
            f"{log_path}, found {len(matches)}"
        )
    return matches[0]


def derive_palette_bases(
    capture_dir: Path, draw: int, relative_instance: int = 0
) -> dict[str, int | str]:
    if relative_instance < 0:
        raise CaptureError("relative instance must be non-negative")
    first_constant, num_constants = parse_constant_buffer_range(
        capture_dir / "log.txt", draw, 2
    )
    instance_row = relative_instance * 16
    metadata_row = instance_row + 5
    if metadata_row >= num_constants:
        raise CaptureError(
            f"instance metadata row {metadata_row} exceeds bound b2 range of "
            f"{num_constants} constants"
        )
    descriptor, payload = select_constant_buffer(capture_dir, draw, 2)
    metadata = parse_descriptor(descriptor)
    if metadata["type"] != "Buffer":
        raise CaptureError(f"{descriptor} is not a Buffer descriptor")
    if metadata["byte_width"] != EXPECTED_CONSTANT_BUFFER_BYTE_WIDTH:
        raise CaptureError(
            f"unexpected b2 byte_width {metadata['byte_width']} in {descriptor}; "
            f"expected {EXPECTED_CONSTANT_BUFFER_BYTE_WIDTH}"
        )
    if metadata["stride"] != 0:
        raise CaptureError(f"unexpected b2 stride {metadata['stride']} in {descriptor}")
    data = payload.read_bytes()
    if len(data) != metadata["byte_width"]:
        raise CaptureError(
            f"b2 payload size {len(data)} does not match descriptor byte_width "
            f"{metadata['byte_width']}"
        )
    absolute_row = first_constant + metadata_row
    byte_offset = absolute_row * 16
    if byte_offset + 16 > len(data):
        raise CaptureError(
            f"b2 metadata row {absolute_row} exceeds the captured ring buffer"
        )
    current_raw, previous_raw, reserved_z, reserved_w = struct.unpack_from(
        "<4I", data, byte_offset
    )
    current_effective = current_raw + 3
    previous_effective = previous_raw + 3
    record_count = EXPECTED_BYTE_WIDTH // EXPECTED_STRIDE
    if current_effective >= record_count or previous_effective >= record_count:
        raise CaptureError(
            "derived skin-palette base exceeds the vs-t0 float4 record count: "
            f"current={current_effective}, previous={previous_effective}, "
            f"records={record_count}"
        )
    return {
        "constant_buffer_descriptor": descriptor.name,
        "constant_buffer_payload": payload.name,
        "first_constant": first_constant,
        "num_constants": num_constants,
        "relative_instance": relative_instance,
        "instance_metadata_relative_row": metadata_row,
        "instance_metadata_absolute_row": absolute_row,
        "current_base_raw": current_raw,
        "previous_base_raw": previous_raw,
        "reserved_z": reserved_z,
        "reserved_w": reserved_w,
        "current_effective_base_row": current_effective,
        "previous_effective_base_row": previous_effective,
    }


def load_float4_records(descriptor: Path, payload: Path) -> tuple[list[tuple[float, ...]], dict[str, object]]:
    metadata = parse_descriptor(descriptor)
    if metadata["type"] != "Buffer":
        raise CaptureError(f"{descriptor} is not a Buffer descriptor")
    if metadata["byte_width"] != EXPECTED_BYTE_WIDTH:
        raise CaptureError(
            f"unexpected byte_width {metadata['byte_width']} in {descriptor}; "
            f"expected {EXPECTED_BYTE_WIDTH} for {EXPECTED_RESOURCE_HASH}"
        )
    if metadata["stride"] != EXPECTED_STRIDE:
        raise CaptureError(
            f"unexpected stride {metadata['stride']} in {descriptor}; expected {EXPECTED_STRIDE}"
        )
    data = payload.read_bytes()
    if len(data) != metadata["byte_width"]:
        raise CaptureError(
            f"payload size {len(data)} does not match descriptor byte_width "
            f"{metadata['byte_width']} for {payload}"
        )
    records = list(struct.iter_unpack("<4f", data))
    return records, metadata


def extract_matrices(
    records: list[tuple[float, ...]], base_row: int, matrix_count: int
) -> list[list[list[float]]]:
    if base_row < 0:
        raise CaptureError("base row must be non-negative")
    if matrix_count <= 0:
        raise CaptureError("matrix count must be positive")
    end_row = base_row + matrix_count * ROWS_PER_MATRIX
    if end_row > len(records):
        raise CaptureError(
            f"matrix range [{base_row}, {end_row}) exceeds {len(records)} float4 records"
        )
    selected = records[base_row:end_row]
    for relative_row, row in enumerate(selected):
        if not all(math.isfinite(value) for value in row):
            raise CaptureError(
                f"non-finite float at absolute row {base_row + relative_row}"
            )
    return [
        [list(row) for row in selected[index : index + ROWS_PER_MATRIX]]
        for index in range(0, len(selected), ROWS_PER_MATRIX)
    ]


def changed_matrix_ranges(
    left: list[list[list[float]]],
    right: list[list[list[float]]],
    tolerance: float,
) -> tuple[list[dict[str, int]], float]:
    if len(left) != len(right):
        raise CaptureError("matrix comparisons require equal matrix counts")
    changed: list[int] = []
    maximum = 0.0
    for index, (left_matrix, right_matrix) in enumerate(zip(left, right)):
        delta = max(
            abs(a - b)
            for left_row, right_row in zip(left_matrix, right_matrix)
            for a, b in zip(left_row, right_row)
        )
        maximum = max(maximum, delta)
        if delta > tolerance:
            changed.append(index)
    ranges: list[dict[str, int]] = []
    for index in changed:
        if ranges and index == ranges[-1]["end_matrix_exclusive"]:
            ranges[-1]["end_matrix_exclusive"] += 1
        else:
            ranges.append({"start_matrix": index, "end_matrix_exclusive": index + 1})
    return ranges, maximum


def decode_capture(
    capture_dir: Path,
    draw: int,
    base_row: int | None,
    matrix_count: int,
    previous_base_row: int | None = None,
    relative_instance: int = 0,
) -> dict[str, object]:
    descriptor, payload = select_resource(capture_dir, draw)
    records, metadata = load_float4_records(descriptor, payload)
    derived = None
    if base_row is None:
        derived = derive_palette_bases(capture_dir, draw, relative_instance)
        base_row = int(derived["current_effective_base_row"])
        if previous_base_row is None:
            previous_base_row = int(derived["previous_effective_base_row"])
    matrices = extract_matrices(records, base_row, matrix_count)
    result = {
        "capture_dir": str(capture_dir.resolve()),
        "draw": draw,
        "resource_hash": EXPECTED_RESOURCE_HASH,
        "descriptor": descriptor.name,
        "payload": payload.name,
        "descriptor_fields": metadata,
        "effective_base_row": base_row,
        "matrix_count": matrix_count,
        "rows_per_matrix": ROWS_PER_MATRIX,
        "matrices_3x4": matrices,
    }
    if derived is not None:
        result["derived_binding"] = derived
    if previous_base_row is not None:
        result["previous_effective_base_row"] = previous_base_row
        result["previous_matrices_3x4"] = extract_matrices(
            records, previous_base_row, matrix_count
        )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture_dir", type=Path)
    parser.add_argument("--draw", type=int, required=True)
    parser.add_argument(
        "--current-base-row",
        type=int,
        help="effective float4 row index after the shader's +3 adjustment",
    )
    parser.add_argument("--matrix-count", type=int, required=True)
    parser.add_argument(
        "--relative-instance",
        type=int,
        default=0,
        help="instance index relative to BaseInstance (default: 0)",
    )
    parser.add_argument(
        "--previous-base-row",
        type=int,
        help="optional effective previous-frame float4 row index (b2 instance word 5.y + 3)",
    )
    parser.add_argument("--compare-capture-dir", type=Path)
    parser.add_argument("--compare-draw", type=int)
    parser.add_argument("--compare-current-base-row", type=int)
    parser.add_argument("--tolerance", type=float, default=1e-6)
    parser.add_argument("--output", type=Path)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.tolerance < 0 or not math.isfinite(args.tolerance):
            raise CaptureError("tolerance must be finite and non-negative")
        result = decode_capture(
            args.capture_dir,
            args.draw,
            args.current_base_row,
            args.matrix_count,
            args.previous_base_row,
            args.relative_instance,
        )
        if args.compare_capture_dir is not None:
            compare = decode_capture(
                args.compare_capture_dir,
                args.compare_draw if args.compare_draw is not None else args.draw,
                args.compare_current_base_row
                if args.compare_current_base_row is not None
                else args.current_base_row,
                args.matrix_count,
                relative_instance=args.relative_instance,
            )
            ranges, maximum = changed_matrix_ranges(
                result["matrices_3x4"], compare["matrices_3x4"], args.tolerance
            )
            result["comparison"] = {
                "capture_dir": compare["capture_dir"],
                "draw": compare["draw"],
                "effective_base_row": compare["effective_base_row"],
                "tolerance": args.tolerance,
                "maximum_absolute_component_delta": maximum,
                "changed_matrix_ranges": ranges,
            }
        encoded = json.dumps(result, indent=2, sort_keys=True) + "\n"
        if args.output is None:
            sys.stdout.write(encoded)
        else:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(encoded, encoding="utf-8")
    except (CaptureError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
