#!/usr/bin/env python3
"""Merge sparse and dense retail Endminf skinning captures into one replay.

The original 40-frame oracle covers the complete entrance-to-loop reference
window with all 74 dynamic bones.  The newer two-burst capture is denser but
retains different renderer draws in different frames.  This builder aligns the
captures from their reconstructed bone transforms, preserves every direct
observation, and fills only absent per-mesh observations by bounded transform
interpolation between retail samples.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import build_endminf_captured_secondary_dynamics_oracle as base


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
DEFAULT_BASE_ORACLE = (
    REPO_ROOT / "reports/assets/character_recovery"
    / "endminf_captured_secondary_dynamics_oracle.json"
)
DEFAULT_DENSE_DECODED = (
    REPO_ROOT / "scratch/character_recovery/endminf_skinning_20260826T231348Z"
    / "decoded_partial.json"
)
DEFAULT_REFERENCE_MATCHED_DECODED = (
    REPO_ROOT / "scratch/character_recovery/endminf_skinning_20260827T081152Z"
    / "decoded_partial.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT / "reports/assets/character_recovery"
    / "endminf_dense_captured_secondary_dynamics_oracle.json"
)
EXPECTED_BASE_SCHEMA = (
    "endfield.charinfo.endminf-captured-secondary-dynamics-oracle.v1"
)
EXPECTED_DECODED_SCHEMA = (
    "endfield.charinfo.endminf-partial-captured-skin-palette-sequence.v1"
)
OUTPUT_SCHEMA = (
    "endfield.charinfo.endminf-dense-captured-secondary-dynamics-oracle.v4"
)
BODY_CLIP_REFERENCE_SOURCE_FRAME = 115
BODY_CLIP_REFERENCE_SECONDS = 0.05090830227
ALIGNMENT_CANDIDATES = range(100, 161)
ROTATION_SCORE_METERS_PER_DEGREE = 0.002
EXPECTED_BONE_COUNT = 74
EXPECTED_DENSE_SESSION = "20260826T231348Z"
EXPECTED_REFERENCE_MATCHED_SESSION = "20260827T081152Z"
REFERENCE_MATCHED_SOURCE_FRAMES = {1845: 369, 2578: 385}


class DenseOracleError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DenseOracleError(message)


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise DenseOracleError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise DenseOracleError(f"{path} must contain one JSON object")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def quaternion_dot(left: tuple[float, ...], right: tuple[float, ...]) -> float:
    return sum(a * b for a, b in zip(left, right))


def normalize_quaternion(value: tuple[float, ...]) -> tuple[float, ...]:
    length = math.sqrt(quaternion_dot(value, value))
    require(length > 1e-10, "encountered a zero-length capture quaternion")
    return tuple(component / length for component in value)


def matrix_pose(matrix: list[list[float]]) -> tuple[tuple[float, ...], tuple[float, ...]]:
    m00, m01, m02 = matrix[0][:3]
    m10, m11, m12 = matrix[1][:3]
    m20, m21, m22 = matrix[2][:3]
    trace = m00 + m11 + m22
    if trace > 0.0:
        scale = math.sqrt(trace + 1.0) * 2.0
        quaternion = ((m21 - m12) / scale, (m02 - m20) / scale,
                      (m10 - m01) / scale, 0.25 * scale)
    elif m00 > m11 and m00 > m22:
        scale = math.sqrt(1.0 + m00 - m11 - m22) * 2.0
        quaternion = (0.25 * scale, (m01 + m10) / scale,
                      (m02 + m20) / scale, (m21 - m12) / scale)
    elif m11 > m22:
        scale = math.sqrt(1.0 + m11 - m00 - m22) * 2.0
        quaternion = ((m01 + m10) / scale, 0.25 * scale,
                      (m12 + m21) / scale, (m02 - m20) / scale)
    else:
        scale = math.sqrt(1.0 + m22 - m00 - m11) * 2.0
        quaternion = ((m02 + m20) / scale, (m12 + m21) / scale,
                      0.25 * scale, (m10 - m01) / scale)
    return (
        tuple(matrix[row][3] for row in range(3)),
        normalize_quaternion(quaternion),
    )


def pose_matrix(pose: tuple[tuple[float, ...], tuple[float, ...]]) -> list[list[float]]:
    position, quaternion = pose
    x, y, z, w = normalize_quaternion(quaternion)
    return [
        [1.0 - 2.0 * (y * y + z * z), 2.0 * (x * y - z * w),
         2.0 * (x * z + y * w), position[0]],
        [2.0 * (x * y + z * w), 1.0 - 2.0 * (x * x + z * z),
         2.0 * (y * z - x * w), position[1]],
        [2.0 * (x * z - y * w), 2.0 * (y * z + x * w),
         1.0 - 2.0 * (x * x + y * y), position[2]],
    ]


def slerp(left: tuple[float, ...], right: tuple[float, ...], blend: float) -> tuple[float, ...]:
    cosine = quaternion_dot(left, right)
    if cosine < 0.0:
        right = tuple(-value for value in right)
        cosine = -cosine
    cosine = max(-1.0, min(1.0, cosine))
    if cosine > 0.9995:
        return normalize_quaternion(tuple(
            a + (b - a) * blend for a, b in zip(left, right)
        ))
    angle = math.acos(cosine)
    sine = math.sin(angle)
    return tuple(
        a * math.sin((1.0 - blend) * angle) / sine
        + b * math.sin(blend * angle) / sine
        for a, b in zip(left, right)
    )


def interpolate(
    series: list[tuple[int, tuple[tuple[float, ...], tuple[float, ...]]]],
    frame: int,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    keys = [row[0] for row in series]
    right = bisect.bisect_left(keys, frame)
    if right < len(series) and keys[right] == frame:
        return series[right][1]
    require(right > 0 and right < len(series),
            f"frame {frame} lies outside a retail observation series")
    left = right - 1
    blend = (frame - keys[left]) / (keys[right] - keys[left])
    left_pose = series[left][1]
    right_pose = series[right][1]
    return (
        tuple(a + (b - a) * blend
              for a, b in zip(left_pose[0], right_pose[0])),
        slerp(left_pose[1], right_pose[1], blend),
    )


def pose_error(left, right) -> tuple[float, float]:
    translation = math.sqrt(sum(
        (a - b) ** 2 for a, b in zip(left[0], right[0])
    ))
    cosine = max(-1.0, min(1.0, abs(quaternion_dot(left[1], right[1]))))
    return translation, math.degrees(2.0 * math.acos(cosine))


def old_series(oracle: dict[str, Any], paths: list[str]) -> tuple[dict[str, list], list[int]]:
    alignment = oracle["referenceAlignment"]
    first_presented = int(alignment["firstCapturePresentedFrame"])
    first_reference = int(alignment["firstReferenceSourceFrame"])
    result = {path: [] for path in paths}
    source_frames = []
    for frame in oracle.get("frames", []):
        source = first_reference + int(frame["presentedFrame"]) - first_presented
        source_frames.append(source)
        rows = frame.get("ownerBoneMatrices", [])
        require([row.get("path") for row in rows] == paths,
                f"base oracle bone order drifted at {frame.get('presentedFrame')}")
        for row in rows:
            result[row["path"]].append(
                (source, matrix_pose(row["currentRootSpace3x4"]))
            )
    require(len(source_frames) >= 2, "base oracle has fewer than two frames")
    return result, source_frames


def recover_dense_observations(decoded: dict[str, Any], paths: list[str]) -> tuple[dict[int, dict], float]:
    manifest = base.load_json(base.MANIFEST)
    contracts, _ = base.mesh_contracts(manifest)
    wanted = set(paths)
    result = {}
    worst_shared = 0.0
    for frame in decoded.get("frames", []):
        recovered = {}
        for mesh_name, mesh in frame.get("meshes", {}).items():
            if mesh_name not in contracts:
                continue
            contract = contracts[mesh_name]
            matrices = mesh.get("currentMatrices3x4", [])
            require(len(contract) == len(matrices),
                    f"frame {frame.get('frame')} {mesh_name} matrix count drifted")
            for (path, inverse_bindpose), skin_rows in zip(contract, matrices):
                if path not in wanted:
                    continue
                matrix = base.multiply(base.skin_matrix(skin_rows), inverse_bindpose)
                require(base.orthonormality_error(matrix) <= base.ORTHONORMALITY_TOLERANCE,
                        f"frame {frame.get('frame')} {path} is not orthonormal")
                if path in recovered:
                    delta = base.max_delta(recovered[path], matrix)
                    worst_shared = max(worst_shared, delta)
                    require(delta <= base.SHARED_MATRIX_TOLERANCE,
                            f"frame {frame.get('frame')} shared bone differs by {delta}")
                recovered[path] = matrix
        if recovered:
            result[int(frame["frame"])] = {
                path: matrix_pose(matrix) for path, matrix in recovered.items()
            }
    require(result, "dense decoded capture has no owner-bone observations")
    return result, worst_shared


def split_bursts(frames: list[int]) -> tuple[list[int], list[int]]:
    gaps = [(right - left, index) for index, (left, right)
            in enumerate(zip(frames, frames[1:]))]
    require(gaps, "dense capture has fewer than two observed frames")
    _, boundary = max(gaps)
    first = frames[:boundary + 1]
    second = frames[boundary + 1:]
    require(len(first) >= 40 and len(second) >= 40,
            f"dense capture bursts are too short: {len(first)}/{len(second)}")
    return first, second


def align(
    old: dict[str, list], dense: dict[int, dict], first_burst: list[int]
) -> tuple[int, list[dict[str, Any]]]:
    old_min = min(next(iter(old.values())))[0]
    old_max = max(next(iter(old.values())))[0]
    first_presented = min(dense)
    scores = []
    for anchor in ALIGNMENT_CANDIDATES:
        translations = []
        rotations = []
        for presented in first_burst:
            source = anchor + presented - first_presented
            if source < old_min or source > old_max:
                continue
            for path, pose in dense[presented].items():
                translation, rotation = pose_error(
                    pose, interpolate(old[path], source)
                )
                translations.append(translation)
                rotations.append(rotation)
        require(translations, f"alignment candidate {anchor} has no overlap")
        translation = sum(translations) / len(translations)
        rotation = sum(rotations) / len(rotations)
        scores.append({
            "firstReferenceSourceFrame": anchor,
            "comparisonCount": len(translations),
            "meanTranslationMeters": translation,
            "meanRotationDegrees": rotation,
            "combinedScore": translation + ROTATION_SCORE_METERS_PER_DEGREE * rotation,
        })
    combined = min(scores, key=lambda row: row["combinedScore"])
    translation = min(scores, key=lambda row: row["meanTranslationMeters"])
    rotation = min(scores, key=lambda row: row["meanRotationDegrees"])
    require(combined is translation and combined is rotation,
            "translation and rotation alignment minima disagree")
    return int(combined["firstReferenceSourceFrame"]), scores


def build_report(
    base_path: Path,
    decoded_path: Path,
    reference_matched_path: Path,
) -> dict[str, Any]:
    oracle = load_json(base_path)
    decoded = load_json(decoded_path)
    reference_matched = load_json(reference_matched_path)
    require(oracle.get("schema") == EXPECTED_BASE_SCHEMA,
            f"base oracle schema drifted: {oracle.get('schema')}")
    require(decoded.get("schema") == EXPECTED_DECODED_SCHEMA,
            f"decoded schema drifted: {decoded.get('schema')}")
    require(Path(decoded.get("sessionRoot", "")).name == EXPECTED_DENSE_SESSION,
            f"dense capture session drifted: {decoded.get('sessionRoot')}")
    require(reference_matched.get("schema") == EXPECTED_DECODED_SCHEMA,
            "reference-matched decoded capture schema drifted: "
            f"{reference_matched.get('schema')}")
    require(Path(reference_matched.get("sessionRoot", "")).name ==
            EXPECTED_REFERENCE_MATCHED_SESSION,
            "reference-matched capture session drifted: "
            f"{reference_matched.get('sessionRoot')}")

    first_rows = oracle.get("frames", [])[0].get("ownerBoneMatrices", [])
    paths = [row.get("path") for row in first_rows]
    require(len(paths) == EXPECTED_BONE_COUNT and len(set(paths)) == len(paths),
            f"base oracle must contain {EXPECTED_BONE_COUNT} unique bones")
    sparse, sparse_source_frames = old_series(oracle, paths)
    dense, worst_shared = recover_dense_observations(decoded, paths)
    reference_matched_observations, reference_matched_worst_shared = (
        recover_dense_observations(reference_matched, paths)
    )
    require(set(reference_matched_observations) ==
            set(REFERENCE_MATCHED_SOURCE_FRAMES),
            "reference-matched capture frame set drifted: "
            f"{sorted(reference_matched_observations)}")
    dense_frames = sorted(dense)
    first_burst, second_burst = split_bursts(dense_frames)
    anchor, alignment_scores = align(sparse, dense, first_burst)
    first_dense_presented = dense_frames[0]

    dense_source_by_presented = {
        presented: anchor + presented - first_dense_presented
        for presented in dense_frames
    }
    dense_series = {path: [] for path in paths}
    for presented, rows in dense.items():
        source = dense_source_by_presented[presented]
        for path, pose in rows.items():
            dense_series[path].append((source, pose))
    for rows in dense_series.values():
        rows.sort()
    require(all(rows for rows in dense_series.values()),
            "dense capture does not cover every owner bone")

    reference_matched_by_source = {
        REFERENCE_MATCHED_SOURCE_FRAMES[presented]: rows
        for presented, rows in reference_matched_observations.items()
    }
    merged_series = {}
    direct_collisions = []
    reference_matched_collisions = []
    for path in paths:
        by_source = {source: (pose, "sparse") for source, pose in sparse[path]}
        for source, pose in dense_series[path]:
            if source in by_source:
                translation, rotation = pose_error(pose, by_source[source][0])
                direct_collisions.append((translation, rotation))
            by_source[source] = (pose, "dense")
        for source, rows in reference_matched_by_source.items():
            if path not in rows:
                continue
            pose = rows[path]
            if source in by_source:
                translation, rotation = pose_error(pose, by_source[source][0])
                reference_matched_collisions.append((translation, rotation))
            # These palettes win at their two phases because their captured
            # backbuffers independently match the clean target sequence.
            by_source[source] = (pose, "reference_matched")
        merged_series[path] = [
            (source, pose) for source, (pose, _) in sorted(by_source.items())
        ]

    source_frames = sorted(set(
        sparse_source_frames + list(dense_source_by_presented.values()) +
        list(reference_matched_by_source)
    ))
    first_source = source_frames[0]
    last_source = source_frames[-1]
    require(all(rows[0][0] <= first_source and rows[-1][0] >= last_source
                for rows in merged_series.values()),
            "one or more owner bones do not bound the merged playback interval")

    dense_direct_by_source = {
        source: dense[presented]
        for presented, source in dense_source_by_presented.items()
    }
    direct_reference_matched_by_source = reference_matched_by_source
    sparse_direct_sources = set(sparse_source_frames)
    first_presented = int(
        oracle["referenceAlignment"]["firstCapturePresentedFrame"]
    )
    frames = []
    for source in source_frames:
        direct_dense = dense_direct_by_source.get(source, {})
        direct_reference_matched = direct_reference_matched_by_source.get(
            source, {}
        )
        direct_paths = set(direct_dense) | set(direct_reference_matched)
        matrices = []
        for path in paths:
            pose = interpolate(merged_series[path], source)
            matrices.append({
                "path": path,
                "currentRootSpace3x4": pose_matrix(pose),
            })
        frames.append({
            "presentedFrame": first_presented + source - first_source,
            "playbackSourceFrame": source,
            "directDenseBoneCount": len(direct_dense),
            "directReferenceMatchedBoneCount": len(direct_reference_matched),
            "directSparseFrame": source in sparse_direct_sources,
            "interpolatedBoneCount": EXPECTED_BONE_COUNT - len(direct_paths)
                if direct_paths else 0,
            "ownerBoneMatrices": matrices,
        })

    second_sources = [dense_source_by_presented[frame] for frame in second_burst]
    selected = min(alignment_scores, key=lambda row: row["combinedScore"])
    collision_translation = [row[0] for row in direct_collisions]
    collision_rotation = [row[1] for row in direct_collisions]
    alignment = dict(oracle["referenceAlignment"])
    alignment.update({
        "lastReferenceSourceFrame": min(last_source, 883),
        "lastCapturedPlaybackSourceFrame": last_source,
        "denseFirstCapturePresentedFrame": first_dense_presented,
        "denseFirstReferenceSourceFrame": anchor,
        "denseAnchorUncertaintyFrames": 1,
        "denseMapping": (
            f"playbackSourceFrame = {anchor} + "
            f"(presentedFrame - {first_dense_presented})"
        ),
        "referenceMatchedMappings": [
            {
                "capturePresentedFrame": presented,
                "playbackSourceFrame": source,
                "cleanReferenceFrame": 257 if presented == 1845 else 273,
                "anchorUncertaintyFrames": 1,
                "evidence": (
                    "grayscale ROI edge match to the clean reference and an "
                    "independent 74-bone pose match agree within one frame"
                ),
            }
            for presented, source in sorted(
                REFERENCE_MATCHED_SOURCE_FRAMES.items()
            )
        ],
    })
    return {
        "schema": OUTPUT_SCHEMA,
        "status": (
            "owner_tagged_retail_skinning_trajectories_merged_dense_"
            "with_reference_matched_overrides"
        ),
        "scope": (
            "74 captured render-consumed owner bones; two retail palettes whose "
            "backbuffers match clean reference frames override older-run dynamics "
            "at those phases; absent draws are interpolated only between bounded "
            "retail transform observations"
        ),
        "captureSessions": [
            oracle.get("captureSession"),
            EXPECTED_DENSE_SESSION,
            EXPECTED_REFERENCE_MATCHED_SESSION,
        ],
        "frameCount": len(frames),
        "boneCount": EXPECTED_BONE_COUNT,
        "referenceAlignment": alignment,
        "playback": {
            "sourceFps": float(alignment["sourceFps"]),
            "firstPlaybackSourceFrame": first_source,
            "lastPlaybackSourceFrame": last_source,
            "entranceBodyClipAnchorSeconds": (
                BODY_CLIP_REFERENCE_SECONDS +
                (first_source - BODY_CLIP_REFERENCE_SOURCE_FRAME) /
                float(alignment["sourceFps"])
            ),
            "entranceSequenceAnchorSeconds": (
                (first_source - BODY_CLIP_REFERENCE_SOURCE_FRAME) /
                float(alignment["sourceFps"])
            ),
            "entranceAnchorEvidence": (
                "sample zero is retail source frame " + str(first_source) +
                "; deterministic Unity body phase 0.05090830227 is aligned "
                "to retail source frame 115"
            ),
            "settledLoopBurstFirstSourceFrame": min(second_sources),
            "settledLoopBurstLastSourceFrame": max(second_sources),
            "overviewLoopClipFrameCount": 125,
            "overviewLoopClipSeconds": 125.0 / float(alignment["sourceFps"]),
            "upperEndpointBehavior": "clamp_pending_periodic_shape_gate",
        },
        "sources": {
            relative(Path(__file__)): sha256(Path(__file__)),
            relative(base_path): sha256(base_path),
            relative(decoded_path): sha256(decoded_path),
            relative(reference_matched_path): sha256(reference_matched_path),
        },
        "validation": {
            "selectedDenseAnchor": selected,
            "alignmentCandidates": alignment_scores,
            "denseBurstObservationCounts": [len(first_burst), len(second_burst)],
            "denseMeshObservationCounts": decoded.get("meshObservationCounts"),
            "worstSameFrameSharedMatrixDelta": worst_shared,
            "referenceMatchedMeshObservationCounts": (
                reference_matched.get("meshObservationCounts")
            ),
            "referenceMatchedWorstSameFrameSharedMatrixDelta": (
                reference_matched_worst_shared
            ),
            "directSparseDenseCollisionCount": len(direct_collisions),
            "collisionMeanTranslationMeters": (
                sum(collision_translation) / len(collision_translation)
                if collision_translation else None
            ),
            "collisionMeanRotationDegrees": (
                sum(collision_rotation) / len(collision_rotation)
                if collision_rotation else None
            ),
            "directDenseObservationCount": sum(len(row) for row in dense.values()),
            "directReferenceMatchedObservationCount": sum(
                len(row) for row in reference_matched_observations.values()
            ),
            "referenceMatchedCollisionCount": len(
                reference_matched_collisions
            ),
            "referenceMatchedCollisionMeanTranslationMeters": (
                sum(row[0] for row in reference_matched_collisions) /
                len(reference_matched_collisions)
            ),
            "referenceMatchedCollisionMeanRotationDegrees": (
                sum(row[1] for row in reference_matched_collisions) /
                len(reference_matched_collisions)
            ),
            "mergedSampleCount": len(frames),
            "interpolationBoundary": "retail observations only; no extrapolation",
        },
        "owners": oracle.get("owners", []),
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-oracle", type=Path, default=DEFAULT_BASE_ORACLE)
    parser.add_argument("--dense-decoded", type=Path, default=DEFAULT_DENSE_DECODED)
    parser.add_argument(
        "--reference-matched-decoded",
        type=Path,
        default=DEFAULT_REFERENCE_MATCHED_DECODED,
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        report = build_report(
            args.base_oracle.resolve(),
            args.dense_decoded.resolve(),
            args.reference_matched_decoded.resolve(),
        )
    except (DenseOracleError, OSError, ValueError, KeyError, IndexError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
