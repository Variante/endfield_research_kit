#!/usr/bin/env python3
"""Validate one EndfieldCapture session for Endminf VFX and cloth recovery.

The report deliberately keeps two independent gates visible:

* exact M29/M30 draw-resource closure; and
* render-boundary skin-palette coverage for the character meshes.

Individual meshes are not necessarily retained in every graphics frame.  The
palette gate therefore measures unambiguous per-mesh observations across both
capture bursts instead of requiring every mesh in every frame.
"""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

import decode_endminf_endfield_capture_skinning as skinning
import verify_endminf_m29_m30_capture_completeness as effects


REPO = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_combined_graphics_capture_latest.json"
)

MINIMUM_TOTAL = {
    "body": 8,
    "cloth_01": 40,
    "cloth_02": 8,
    "cloth_04": 24,
    "hair": 40,
}
MINIMUM_PER_SEQUENCE = {
    "cloth_01": 8,
    "cloth_02": 4,
    "cloth_04": 4,
    "hair": 8,
}
MINIMUM_SEQUENCE_FRAMES = 48


class VerificationError(RuntimeError):
    pass


def frame_paths(capture: Path) -> list[Path]:
    root = capture / "graphics/frames"
    paths = sorted(root.glob("*/metadata.json"), key=lambda path: int(path.parent.name))
    if not paths:
        raise VerificationError(f"capture has no graphics metadata under {root}")
    return paths


def split_sequences(frames: list[int]) -> list[list[int]]:
    if not frames:
        return []
    positive = [right - left for left, right in zip(frames, frames[1:]) if right > left]
    cadence = statistics.median(positive) if positive else 1
    threshold = max(32, int(cadence * 4))
    result = [[frames[0]]]
    for left, right in zip(frames, frames[1:]):
        if right - left > threshold:
            result.append([])
        result[-1].append(right)
    return result


def palette_resource(metadata: dict[str, Any], resources_path: Path) -> str | None:
    rows = [
        row for row in metadata.get("selectedResourceRecords", [])
        if isinstance(row, dict)
        and row.get("completed") is True
        and int(row.get("byteSize", -1)) == skinning.PALETTE_BYTES
        and int(row.get("blobBytes", -1)) == skinning.PALETTE_BYTES
    ]
    if len(rows) != 1:
        return f"expected one completed palette resource, found {len(rows)}"
    row = rows[0]
    try:
        file_size = resources_path.stat().st_size
    except OSError as exc:
        return f"cannot stat resources file: {exc}"
    start = int(row.get("blobOffset", -1))
    end = start + int(row.get("blobBytes", -1))
    if start < 0 or end > file_size:
        return f"palette blob range [{start}, {end}) exceeds {file_size} bytes"
    return None


def audit_palettes(capture: Path) -> dict[str, Any]:
    paths = frame_paths(capture)
    frame_ids = [int(path.parent.name) for path in paths]
    sequences = split_sequences(frame_ids)
    sequence_by_frame = {
        frame: index for index, sequence in enumerate(sequences) for frame in sequence
    }
    meshes = tuple(MINIMUM_TOTAL)
    observations: dict[str, list[dict[str, Any]]] = {mesh: [] for mesh in meshes}
    palette_errors: list[dict[str, Any]] = []
    ambiguous: list[dict[str, Any]] = []

    for path in paths:
        metadata = skinning.load_json(path)
        frame = int(metadata.get("frame", path.parent.name))
        resource_name = str(metadata.get("resourcesFile", "resources.bin"))
        resource_error = palette_resource(metadata, path.parent / resource_name)
        if resource_error:
            palette_errors.append({"frame": frame, "error": resource_error})
            continue
        for mesh in meshes:
            try:
                draw = skinning.unique_mesh_draw(metadata, mesh)
            except skinning.CaptureError as exc:
                message = str(exc)
                if "ambiguous" in message or "metadata snapshot" in message:
                    ambiguous.append({"frame": frame, "mesh": mesh, "error": message})
                continue
            observations[mesh].append({
                "frame": frame,
                "sequence": sequence_by_frame[frame],
                "currentBaseRaw": draw["currentBaseRaw"],
                "previousBaseRaw": draw["previousBaseRaw"],
                "matchingDrawRecords": draw["matchingDrawRecords"],
            })

    errors = []
    if len(sequences) != 2:
        errors.append(f"expected two graphics bursts, found {len(sequences)}")
    for index, sequence in enumerate(sequences):
        if len(sequence) < MINIMUM_SEQUENCE_FRAMES:
            errors.append(
                f"sequence {index} has {len(sequence)} frames; need {MINIMUM_SEQUENCE_FRAMES}"
            )
    if ambiguous:
        errors.append(f"{len(ambiguous)} mesh observations have ambiguous/invalid b2 metadata")

    mesh_reports: dict[str, Any] = {}
    for mesh, rows in observations.items():
        per_sequence = [sum(row["sequence"] == index for row in rows)
                        for index in range(len(sequences))]
        required_total = MINIMUM_TOTAL[mesh]
        if len(rows) < required_total:
            errors.append(f"{mesh} has {len(rows)} observations; need {required_total}")
        required_per_sequence = MINIMUM_PER_SEQUENCE.get(mesh)
        if required_per_sequence is not None:
            for index, count in enumerate(per_sequence):
                if count < required_per_sequence:
                    errors.append(
                        f"{mesh} sequence {index} has {count} observations; "
                        f"need {required_per_sequence}"
                    )
        mesh_reports[mesh] = {
            "observationCount": len(rows),
            "minimumRequired": required_total,
            "perSequence": per_sequence,
            "firstFrame": rows[0]["frame"] if rows else None,
            "lastFrame": rows[-1]["frame"] if rows else None,
            "observations": rows,
        }

    return {
        "status": "validated_render_boundary_palette_coverage" if not errors else "rejected",
        "frameCount": len(paths),
        "sequences": [
            {"index": index, "frameCount": len(sequence),
             "firstFrame": sequence[0], "lastFrame": sequence[-1]}
            for index, sequence in enumerate(sequences)
        ],
        "paletteResourceErrorCount": len(palette_errors),
        "paletteResourceErrors": palette_errors,
        "ambiguousObservationCount": len(ambiguous),
        "ambiguousObservations": ambiguous,
        "meshes": mesh_reports,
        "errors": errors,
    }


def build_report(capture: Path) -> dict[str, Any]:
    palette = audit_palettes(capture)
    effect_report = None
    effect_error = None
    try:
        effect_report = effects.build_report(capture)
    except (OSError, ValueError, effects.VerificationError) as exc:
        effect_error = str(exc)
    errors = list(palette["errors"])
    if effect_error:
        errors.append(f"M29/M30: {effect_error}")
    return {
        "schema": "endfield.endminf-combined-graphics-capture.v1",
        "status": "validated" if not errors else "rejected",
        "capture": str(capture.resolve()),
        "effects": effect_report if effect_report is not None else {
            "status": "rejected", "error": effect_error,
        },
        "skinning": palette,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(args.capture.resolve())
    except (OSError, ValueError, VerificationError, skinning.CaptureError) as exc:
        print(f"ERROR: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    if report["status"] != "validated":
        for error in report["errors"]:
            print(f"ERROR: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
