#!/usr/bin/env python3
"""Compare synchronized Unity Endminf bones with the retail skinning oracle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from pathlib import Path


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
DEFAULT_RETAIL = (
    REPO / "reports/assets/character_recovery"
    / "endminf_captured_secondary_dynamics_oracle.json"
)
DEFAULT_UNITY = (
    REPO / "scratch/character_recovery"
    / "endminf_unity_secondary_dynamics_oracle_aligned/report.json"
)
DEFAULT_OUTPUT = (
    REPO / "reports/assets/character_recovery"
    / "endminf_secondary_dynamics_trajectory_comparison.json"
)


class ComparisonError(ValueError):
    pass


def load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"{path} must contain one JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def translation_error(left: list[list[float]], right: list[list[float]]) -> float:
    return math.sqrt(sum((left[row][3] - right[row][3]) ** 2 for row in range(3)))


def rotation_error_degrees(
    left: list[list[float]], right: list[list[float]]
) -> float:
    trace = sum(
        left[row][axis] * right[row][axis]
        for row in range(3)
        for axis in range(3)
    )
    cosine = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
    return math.degrees(math.acos(cosine))


def unity_matrix(row: dict) -> list[list[float]]:
    result = []
    for index in range(3):
        vector = row.get(f"rootSpaceRow{index}")
        if not isinstance(vector, dict):
            raise ComparisonError("Unity bone row has no root-space matrix")
        result.append([float(vector[key]) for key in ("x", "y", "z", "w")])
    return result


def metrics(rows: list[dict]) -> dict:
    translations = [row["translation"] for row in rows]
    rotations = [row["rotationDegrees"] for row in rows]
    worst_translation = max(rows, key=lambda row: row["translation"])
    worst_rotation = max(rows, key=lambda row: row["rotationDegrees"])
    return {
        "sampleCount": len(rows),
        "translationMean": statistics.mean(translations),
        "translationMaximum": worst_translation["translation"],
        "translationWorst": {
            "frame": worst_translation["presentedFrame"],
            "path": worst_translation["path"],
        },
        "rotationDegreesMean": statistics.mean(rotations),
        "rotationDegreesMaximum": worst_rotation["rotationDegrees"],
        "rotationWorst": {
            "frame": worst_rotation["presentedFrame"],
            "path": worst_rotation["path"],
        },
    }


def compare(retail: dict, unity: dict) -> dict:
    if retail.get("schema") != (
        "endfield.charinfo.endminf-captured-secondary-dynamics-oracle.v1"
    ):
        raise ComparisonError("retail oracle schema differs")
    if unity.get("schema") != "endfield.endminf-viewer-playmode-sequence.v4":
        raise ComparisonError("Unity sequence schema differs")
    retail_frames = retail.get("frames", [])
    unity_frames = unity.get("frames", [])
    if len(retail_frames) != 40 or len(unity_frames) != 40:
        raise ComparisonError("comparison requires forty synchronized frames")

    owner_paths = {
        owner["owner"]: set(owner.get("capturedProxyPaths", []))
        for owner in retail.get("owners", [])
    }
    if set(owner_paths) != {"MC_Ribbon2", "MC_Hair", "MC_Ribbon", "MC_Coat"}:
        raise ComparisonError("retail owner set differs")

    owner_rows = {owner: [] for owner in owner_paths}
    frame_rows = []
    unique_paths = set()
    for index, (retail_frame, unity_frame) in enumerate(
        zip(retail_frames, unity_frames)
    ):
        expected_requested = (
            retail_frame["presentedFrame"] - 1884
        ) / 60.0
        if abs(unity_frame["requestedSeconds"] - expected_requested) > 1e-5:
            raise ComparisonError(f"Unity phase differs at frame {index}")
        retail_bones = {
            row["path"]: row["currentRootSpace3x4"]
            for row in retail_frame.get("ownerBoneMatrices", [])
        }
        unity_bones = {
            row["path"]: unity_matrix(row)
            for row in unity_frame.get("secondaryDynamicsBones", [])
        }
        common = set(retail_bones).intersection(unity_bones)
        if len(common) != 74:
            raise ComparisonError(
                f"expected 74 rendered owner paths at frame {index}, got {len(common)}"
            )
        unique_paths.update(common)
        unique_frame_metrics = []
        for path in sorted(common):
            row = {
                "presentedFrame": retail_frame["presentedFrame"],
                "path": path,
                "translation": translation_error(
                    retail_bones[path], unity_bones[path]
                ),
                "rotationDegrees": rotation_error_degrees(
                    retail_bones[path], unity_bones[path]
                ),
            }
            unique_frame_metrics.append(row)
            for owner, paths in owner_paths.items():
                if path in paths:
                    owner_rows[owner].append(row)
        frame_rows.append({
            "index": index,
            "presentedFrame": retail_frame["presentedFrame"],
            "requestedSeconds": unity_frame["requestedSeconds"],
            **metrics(unique_frame_metrics),
        })

    return {
        "schema": "endfield.endminf-secondary-dynamics-trajectory-comparison.v1",
        "status": "retail_trajectory_gap_measured",
        "scope": (
            "74 retail-rendered owner bones at 40 source-aligned checkpoints; "
            "Unity recovered solver writeback remains disabled"
        ),
        "uniqueComparedPaths": len(unique_paths),
        "ownerMetrics": {
            owner: metrics(rows) for owner, rows in owner_rows.items()
        },
        "frames": frame_rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--retail", type=Path, default=DEFAULT_RETAIL)
    parser.add_argument("--unity", type=Path, default=DEFAULT_UNITY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        retail_path = args.retail.resolve()
        unity_path = args.unity.resolve()
        report = compare(load(retail_path), load(unity_path))
        report["sources"] = {
            str(retail_path): sha256(retail_path),
            str(unity_path): sha256(unity_path),
            str(Path(__file__).resolve()): sha256(Path(__file__).resolve()),
        }
    except (ComparisonError, OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
