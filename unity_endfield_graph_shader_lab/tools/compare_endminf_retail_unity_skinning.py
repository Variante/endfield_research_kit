#!/usr/bin/env python3
"""Fail-closed comparison of retained Endminf retail and Unity skin palettes.

The retail capture stores a large source palette plus draw-time indices copied
through VS constant buffer b2.  This tool brackets each Unity timestamp in
retail presented-frame space, recovers root-space bone transforms with the
Unity mesh bindposes, rigidly interpolates them, reconstructs skin matrices,
and compares those matrices with Unity's retained CPU-side palette report.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import sys
from pathlib import Path


PALETTE_BYTES = 8_413_184
PALETTE_STRIDE = 16
ROWS_PER_MATRIX = 3
CB2_BYTES = 4_194_304
CB2_CONSTANTS = 4_096
QPC_FALLBACK_FREQUENCY = 10_000_000
DEFAULT_TIMES = (3.0, 5.0)

MESHES = {
    "cloth_01": {
        "indexCount": 101_994,
        "matrixCount": 156,
        "rendererSuffix": "S_actor_endminf_cloth_01_lod0",
        "vertexShaders": {
            (13_754_588_598_049_366_955, 6044),
            (13_479_119_685_698_484_394, 8296),
            (6_381_089_381_834_541_132, 7404),
            (10_167_811_038_498_854_955, 9400),
        },
    },
    "cloth_04": {
        "indexCount": 20_577,
        "matrixCount": 14,
        "rendererSuffix": "S_actor_endminf_cloth_04_lod0",
        "vertexShaders": {
            (13_754_588_598_049_366_955, 6044),
            (13_479_119_685_698_484_394, 8296),
            (6_381_089_381_834_541_132, 7404),
            (10_167_811_038_498_854_955, 9400),
        },
    },
    "cloth_02": {
        "indexCount": 2_286,
        "matrixCount": 29,
        "rendererSuffix": "S_actor_endminf_cloth_02_lod0",
        "vertexShaders": {
            (13_479_119_685_698_484_394, 8296),
        },
    },
    "hair": {
        "indexCount": 27_615,
        "matrixCount": 28,
        "rendererSuffix": "S_actor_endminf_hair_01_lod0",
        "vertexShaders": {
            (13_754_588_598_049_366_955, 6044),
            (6_381_089_381_834_541_132, 7404),
            (1_918_334_518_211_676_586, 9380),
            (5_717_532_255_460_097_973, 9548),
        },
    },
}


class ComparisonError(ValueError):
    """Evidence or mathematical gate failed."""


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ComparisonError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ComparisonError(f"{path} must contain one JSON object")
    return value


def finite_number(value: object, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ComparisonError(f"{label} is not numeric") from exc
    if not math.isfinite(result):
        raise ComparisonError(f"{label} is not finite")
    return result


def report_matrix(value: object, label: str) -> list[list[float]]:
    if not isinstance(value, dict):
        raise ComparisonError(f"{label} is not a matrix object")
    rows = []
    for row_index in range(4):
        row = value.get(f"row{row_index}")
        if not isinstance(row, dict):
            raise ComparisonError(f"{label}.row{row_index} is missing")
        rows.append([
            finite_number(row.get(component), f"{label}.row{row_index}.{component}")
            for component in "xyzw"
        ])
    return rows


def mat_mul(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[sum(a[r][k] * b[k][c] for k in range(4)) for c in range(4)] for r in range(4)]


def mat_inverse(value: list[list[float]], label: str) -> list[list[float]]:
    work = [row[:] + [1.0 if r == c else 0.0 for c in range(4)] for r, row in enumerate(value)]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-10:
            raise ComparisonError(f"{label} is singular")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [item / scale for item in work[column]]
        for row in range(4):
            if row == column:
                continue
            scale = work[row][column]
            work[row] = [work[row][i] - scale * work[column][i] for i in range(8)]
    result = [row[4:] for row in work]
    if not all(math.isfinite(item) for row in result for item in row):
        raise ComparisonError(f"{label} inverse is not finite")
    return result


def rigid_parts(matrix: list[list[float]], label: str) -> tuple[list[float], tuple[float, float, float, float]]:
    if max(abs(matrix[3][i] - (1.0 if i == 3 else 0.0)) for i in range(4)) > 2e-3:
        raise ComparisonError(f"{label} is not affine")
    columns = [[matrix[r][c] for r in range(3)] for c in range(3)]
    lengths = [math.sqrt(sum(item * item for item in column)) for column in columns]
    if max(abs(length - 1.0) for length in lengths) > 5e-3:
        raise ComparisonError(f"{label} has non-unit scale {lengths}")
    dots = [sum(columns[a][i] * columns[b][i] for i in range(3)) for a, b in ((0, 1), (0, 2), (1, 2))]
    if max(abs(value) for value in dots) > 5e-3:
        raise ComparisonError(f"{label} has shear/non-orthogonal axes {dots}")
    determinant = (
        matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
        - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
        + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0])
    )
    if abs(determinant - 1.0) > 8e-3:
        raise ComparisonError(f"{label} has non-rigid determinant {determinant}")
    return [matrix[0][3], matrix[1][3], matrix[2][3]], quat_from_matrix(matrix)


def quat_from_matrix(m: list[list[float]]) -> tuple[float, float, float, float]:
    trace = m[0][0] + m[1][1] + m[2][2]
    if trace > 0.0:
        s = math.sqrt(trace + 1.0) * 2.0
        q = ((m[2][1] - m[1][2]) / s, (m[0][2] - m[2][0]) / s, (m[1][0] - m[0][1]) / s, 0.25 * s)
    elif m[0][0] > m[1][1] and m[0][0] > m[2][2]:
        s = math.sqrt(1.0 + m[0][0] - m[1][1] - m[2][2]) * 2.0
        q = (0.25 * s, (m[0][1] + m[1][0]) / s, (m[0][2] + m[2][0]) / s, (m[2][1] - m[1][2]) / s)
    elif m[1][1] > m[2][2]:
        s = math.sqrt(1.0 + m[1][1] - m[0][0] - m[2][2]) * 2.0
        q = ((m[0][1] + m[1][0]) / s, 0.25 * s, (m[1][2] + m[2][1]) / s, (m[0][2] - m[2][0]) / s)
    else:
        s = math.sqrt(1.0 + m[2][2] - m[0][0] - m[1][1]) * 2.0
        q = ((m[0][2] + m[2][0]) / s, (m[1][2] + m[2][1]) / s, 0.25 * s, (m[1][0] - m[0][1]) / s)
    norm = math.sqrt(sum(item * item for item in q))
    if norm < 1e-10 or not math.isfinite(norm):
        raise ComparisonError("cannot normalize rotation quaternion")
    return tuple(item / norm for item in q)


def quat_slerp(a: tuple[float, ...], b: tuple[float, ...], t: float) -> tuple[float, float, float, float]:
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0.0:
        b = tuple(-item for item in b)
        dot = -dot
    dot = max(-1.0, min(1.0, dot))
    if dot > 0.9995:
        q = tuple(a[i] + t * (b[i] - a[i]) for i in range(4))
        norm = math.sqrt(sum(item * item for item in q))
        return tuple(item / norm for item in q)
    theta = math.acos(dot)
    scale = math.sin(theta)
    return tuple((math.sin((1.0 - t) * theta) * a[i] + math.sin(t * theta) * b[i]) / scale for i in range(4))


def matrix_from_parts(translation: list[float], q: tuple[float, ...]) -> list[list[float]]:
    x, y, z, w = q
    return [
        [1 - 2 * (y*y + z*z), 2 * (x*y - z*w), 2 * (x*z + y*w), translation[0]],
        [2 * (x*y + z*w), 1 - 2 * (x*x + z*z), 2 * (y*z - x*w), translation[1]],
        [2 * (x*z - y*w), 2 * (y*z + x*w), 1 - 2 * (x*x + y*y), translation[2]],
        [0.0, 0.0, 0.0, 1.0],
    ]


def rotation_error_degrees(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    dot = min(1.0, abs(sum(x * y for x, y in zip(a, b))))
    return math.degrees(2.0 * math.acos(dot))


def select_draw(metadata: dict, mesh_name: str) -> dict:
    contract = MESHES[mesh_name]
    candidates = []
    for row in metadata.get("drawRecords", []):
        shaders = row.get("shaders")
        vs = [
            (int(item.get("identityHash", 0)), int(item.get("bytecodeSize", 0)))
            for item in shaders if item.get("stage") == 0
        ] if isinstance(shaders, list) else []
        if (
            row.get("indexedInstanced") is True
            and int(row.get("count", -1)) == contract["indexCount"]
            and row.get("vsCb2RangeValid") is True
            and row.get("vsCb2MetadataValid") is True
            and int(row.get("vsCb2NumConstants", -1)) == CB2_CONSTANTS
            and len(vs) == 1
            and vs[0] in contract["vertexShaders"]
        ):
            candidates.append(row)
    if not candidates:
        raise ComparisonError(f"frame {metadata.get('frame')} has no gated {mesh_name} draw")
    palette_keys = {(int(row["vsCb2CurrentPaletteRaw"]), int(row["vsCb2PreviousPaletteRaw"])) for row in candidates}
    if len(palette_keys) != 1:
        raise ComparisonError(f"frame {metadata.get('frame')} has ambiguous {mesh_name} palette indices")
    cb2_ids = {int(row.get("vsCb2BufferId", 0)) for row in candidates}
    if len(cb2_ids) != 1 or 0 in cb2_ids:
        raise ComparisonError(f"frame {metadata.get('frame')} has ambiguous/zero {mesh_name} vsCb2BufferId")
    for row in candidates:
        shaders = row.get("shaders")
        if not isinstance(shaders, list):
            raise ComparisonError(f"frame {metadata.get('frame')} {mesh_name} has no shader metadata")
        vs = [(int(item.get("identityHash", 0)), int(item.get("bytecodeSize", 0))) for item in shaders if item.get("stage") == 0]
        ps = [(int(item.get("identityHash", 0)), int(item.get("bytecodeSize", 0))) for item in shaders if item.get("stage") == 4]
        if len(vs) != 1 or vs[0] not in contract["vertexShaders"] or len(ps) != 1 or min(ps[0]) <= 0:
            raise ComparisonError(f"frame {metadata.get('frame')} {mesh_name} shader identity is missing or unexpected")
    current, previous = next(iter(palette_keys))
    return {"currentRaw": current, "previousRaw": previous, "cb2ObjectId": next(iter(cb2_ids)), "drawCount": len(candidates)}


def select_resources(metadata: dict, cb2_object_ids: set[int], require_palette_srv_alias: bool = True) -> dict:
    records = metadata.get("selectedResourceRecords", [])
    palettes = [row for row in records if row.get("completed") is True and int(row.get("captureKind", -1)) == 5 and int(row.get("byteSize", -1)) == PALETTE_BYTES and int(row.get("blobBytes", -1)) == PALETTE_BYTES]
    if len(palettes) != 1:
        raise ComparisonError(f"frame {metadata.get('frame')} expected one completed source palette, found {len(palettes)}")
    palette = palettes[0]
    palette_id = int(palette.get("objectId", 0))
    aliases = [row for row in records if int(row.get("objectId", 0)) == palette_id and int(row.get("captureKind", -1)) == 3]
    if palette_id == 0 or (require_palette_srv_alias and not aliases):
        raise ComparisonError(f"frame {metadata.get('frame')} source palette lacks its draw-visible SRV object alias")
    cb2_records = [
        row for row in records
        if row.get("completed") is True
        and int(row.get("captureKind", -1)) == 2
        and int(row.get("byteSize", -1)) == CB2_BYTES
        and int(row.get("blobBytes", -1)) == CB2_BYTES
    ]
    completed_ids = {int(row.get("objectId", 0)) for row in cb2_records}
    if not cb2_object_ids.issubset(completed_ids):
        raise ComparisonError(f"frame {metadata.get('frame')} draw vsCb2BufferId {sorted(cb2_object_ids)} does not match completed b2 object IDs {sorted(completed_ids)}")
    return {
        "palette": palette,
        "paletteObjectId": palette_id,
        "sourcePaletteSrvAliasProven": bool(aliases),
        "matchedDrawCb2ObjectIds": sorted(cb2_object_ids),
        "otherCompletedConstantBufferObjectIds": sorted(completed_ids - cb2_object_ids),
    }


def blob_slice(blob: bytes, record: dict, label: str) -> bytes:
    start, size = int(record.get("blobOffset", -1)), int(record.get("blobBytes", -1))
    if start < 0 or size < 0 or start + size > len(blob):
        raise ComparisonError(f"{label} blob range is invalid")
    return blob[start:start + size]


def decode_frame(frame_dir: Path, mesh_names: tuple[str, ...], require_palette_srv_alias: bool = True) -> dict:
    metadata = load_json(frame_dir / "metadata.json")
    if metadata.get("captureIncomplete") or metadata.get("captureFailed"):
        raise ComparisonError(f"frame {metadata.get('frame')} is incomplete or failed")
    draws = {name: select_draw(metadata, name) for name in mesh_names}
    resources = select_resources(
        metadata,
        {draw["cb2ObjectId"] for draw in draws.values()},
        require_palette_srv_alias=require_palette_srv_alias,
    )
    try:
        blob = (frame_dir / metadata.get("resourcesFile", "resources.bin")).read_bytes()
    except OSError as exc:
        raise ComparisonError(f"cannot read frame {metadata.get('frame')} resources: {exc}") from exc
    palette = blob_slice(blob, resources["palette"], "source palette")
    matrices = {}
    row_count = len(palette) // PALETTE_STRIDE
    for name, draw in draws.items():
        count = MESHES[name]["matrixCount"]
        base = draw["currentRaw"] + 3
        if base < 0 or base + count * ROWS_PER_MATRIX > row_count:
            raise ComparisonError(f"frame {metadata.get('frame')} {name} source palette range is out of bounds")
        decoded = []
        for matrix_index in range(count):
            rows = []
            for row_index in range(ROWS_PER_MATRIX):
                offset = (base + matrix_index * ROWS_PER_MATRIX + row_index) * PALETTE_STRIDE
                row = list(struct.unpack_from("<4f", palette, offset))
                if not all(math.isfinite(item) for item in row):
                    raise ComparisonError(f"frame {metadata.get('frame')} {name} matrix {matrix_index} is non-finite")
                rows.append(row)
            rows.append([0.0, 0.0, 0.0, 1.0])
            decoded.append(rows)
        matrices[name] = decoded
    return {
        "frame": int(metadata["frame"]),
        "timestampQpc": int(metadata["timestampQpc"]),
        "draws": draws,
        "resources": resources,
        "matrices": matrices,
    }


def load_unity(report_path: Path, times: tuple[float, ...], mesh_names: tuple[str, ...]) -> dict[float, dict]:
    report = load_json(report_path)
    if report.get("status") != "targeted_ok" or report.get("retainedSkinningDiagnostic") is not True:
        raise ComparisonError("Unity report is not a successful retained-skinning diagnostic")
    result = {}
    for target in times:
        frames = [row for row in report.get("frames", []) if abs(finite_number(row.get("requestedSeconds"), "requestedSeconds") - target) < 1e-4]
        if len(frames) != 1:
            raise ComparisonError(f"Unity report expected one sample at t={target}, found {len(frames)}")
        frame = frames[0]
        renderers = frame.get("retainedSkinningRenderers")
        if not isinstance(renderers, list):
            raise ComparisonError(f"Unity t={target} has no retained renderer rows")
        sample = {}
        for name in mesh_names:
            contract = MESHES[name]
            matches = [row for row in renderers if str(row.get("path", "")).endswith(contract["rendererSuffix"])]
            if len(matches) != 1:
                raise ComparisonError(f"Unity t={target} expected one {name} renderer, found {len(matches)}")
            row = matches[0]
            bones = row.get("bones")
            if row.get("status") != "ok" or not isinstance(bones, list):
                raise ComparisonError(f"Unity t={target} {name} renderer is not valid")
            expected = contract["matrixCount"]
            if int(row.get("boneCount", -1)) != expected or int(row.get("bindposeCount", -1)) != expected or len(bones) != expected:
                raise ComparisonError(f"Unity t={target} {name} matrix/bindpose count does not equal {expected}")
            parsed = []
            for index, bone in enumerate(bones):
                bindpose = report_matrix(bone.get("bindpose"), f"Unity t={target} {name}[{index}].bindpose")
                skin = report_matrix(bone.get("rendererLocalPalette"), f"Unity t={target} {name}[{index}].rendererLocalPalette")
                root = mat_mul(skin, mat_inverse(bindpose, f"Unity t={target} {name}[{index}].bindpose"))
                rigid_parts(root, f"Unity t={target} {name}[{index}] recovered root")
                parsed.append({"bindpose": bindpose, "skin": skin, "root": root, "path": bone.get("path", "")})
            sample[name] = parsed
        result[target] = {"requestedSeconds": target, "actualSeconds": finite_number(frame.get("actualSeconds"), "actualSeconds"), "meshes": sample}
    return result


def frame_catalog(session_root: Path) -> list[tuple[int, int, Path]]:
    root = session_root / "graphics" / "frames"
    rows = []
    if not root.is_dir():
        raise ComparisonError(f"no graphics frame directory at {root}")
    for path in root.iterdir():
        if not path.is_dir() or not path.name.isdigit() or not (path / "metadata.json").is_file():
            continue
        metadata = load_json(path / "metadata.json")
        rows.append((int(metadata.get("frame", -1)), int(metadata.get("timestampQpc", 0)), path))
    rows.sort()
    if len(rows) < 2 or any(frame < 0 or qpc <= 0 for frame, qpc, _ in rows):
        raise ComparisonError("retail frame catalog lacks valid frame/QPC metadata")
    if any(rows[index][0] >= rows[index + 1][0] or rows[index][1] >= rows[index + 1][1] for index in range(len(rows) - 1)):
        raise ComparisonError("retail frame/QPC catalog is not strictly increasing")
    return rows


def bracket(catalog: list[tuple[int, int, Path]], target: float, uncertainty: float) -> tuple[tuple[int, int, Path], tuple[int, int, Path]]:
    lower = [row for row in catalog if row[0] <= target - uncertainty]
    upper = [row for row in catalog if row[0] >= target + uncertainty]
    if not lower or not upper:
        raise ComparisonError(f"retail captures do not bracket target frame {target} with ±{uncertainty} frame boundary")
    low, high = lower[-1], upper[0]
    if low[0] >= high[0]:
        raise ComparisonError(f"invalid retail bracket for target frame {target}")
    return low, high


def mesh_catalog(catalog: list[tuple[int, int, Path]], mesh_name: str) -> list[tuple[int, int, Path]]:
    """Return frames with complete metadata gates for one sparse mesh draw."""
    result = []
    for frame, qpc, path in catalog:
        metadata = load_json(path / "metadata.json")
        try:
            draw = select_draw(metadata, mesh_name)
            select_resources(metadata, {draw["cb2ObjectId"]})
        except ComparisonError:
            continue
        result.append((frame, qpc, path))
    if len(result) < 2:
        raise ComparisonError(f"retail session has fewer than two fully gated {mesh_name} observations")
    return result


def metric_summary(values: list[float]) -> dict:
    if not values or not all(math.isfinite(item) for item in values):
        raise ComparisonError("cannot summarize empty/non-finite errors")
    return {"mean": sum(values) / len(values), "max": max(values)}


def compare_mesh(name: str, unity_bones: list[dict], low_matrices: list, high_matrices: list, alpha: float) -> dict:
    element_errors, translation_errors, rotation_errors = [], [], []
    for index, unity in enumerate(unity_bones):
        inverse_bindpose = mat_inverse(unity["bindpose"], f"{name}[{index}] bindpose")
        low_root = mat_mul(low_matrices[index], inverse_bindpose)
        high_root = mat_mul(high_matrices[index], inverse_bindpose)
        low_translation, low_rotation = rigid_parts(low_root, f"retail low {name}[{index}] root")
        high_translation, high_rotation = rigid_parts(high_root, f"retail high {name}[{index}] root")
        translation = [low_translation[i] + alpha * (high_translation[i] - low_translation[i]) for i in range(3)]
        rotation = quat_slerp(low_rotation, high_rotation, alpha)
        retail_root = matrix_from_parts(translation, rotation)
        retail_skin = mat_mul(retail_root, unity["bindpose"])
        element_errors.extend(abs(retail_skin[r][c] - unity["skin"][r][c]) for r in range(4) for c in range(4))
        unity_translation, unity_rotation = rigid_parts(unity["root"], f"Unity {name}[{index}] root")
        translation_errors.append(math.sqrt(sum((translation[i] - unity_translation[i]) ** 2 for i in range(3))))
        rotation_errors.append(rotation_error_degrees(rotation, unity_rotation))
    return {
        "matrixCount": len(unity_bones),
        "elementAbsoluteError": metric_summary(element_errors),
        "rootTranslationError": metric_summary(translation_errors),
        "rootRotationErrorDegrees": metric_summary(rotation_errors),
    }


def compare(session_root: Path, unity_report: Path, times: tuple[float, ...] = DEFAULT_TIMES) -> dict:
    mesh_names = tuple(MESHES)
    session = load_json(session_root / "session.json")
    if session.get("gameBuild") != "endfield-2026-07-11-gameassembly-0c557367":
        raise ComparisonError("retail session is not the pinned Endfield build")
    catalog = frame_catalog(session_root)
    unity = load_unity(unity_report, times, mesh_names)
    samples = []
    decoded_cache = {}
    catalogs_by_mesh = {name: mesh_catalog(catalog, name) for name in mesh_names}
    for target_time in times:
        target_source = 114.0 + target_time * 60.0
        target_presented = 2833.0 + (target_source - 129.0)
        mesh_results = {}
        for name in mesh_names:
            low_row, high_row = bracket(catalogs_by_mesh[name], target_presented, 1.0)
            low_key, high_key = (low_row[0], name), (high_row[0], name)
            if low_key not in decoded_cache:
                decoded_cache[low_key] = decode_frame(low_row[2], (name,))
            if high_key not in decoded_cache:
                decoded_cache[high_key] = decode_frame(high_row[2], (name,))
            low, high = decoded_cache[low_key], decoded_cache[high_key]
            alpha = (target_presented - low["frame"]) / (high["frame"] - low["frame"])
            if not 0.0 <= alpha <= 1.0:
                raise ComparisonError(f"t={target_time} {name} interpolation alpha is outside [0,1]")
            target_qpc = low["timestampQpc"] + alpha * (high["timestampQpc"] - low["timestampQpc"])
            seconds_per_presented_frame = (high["timestampQpc"] - low["timestampQpc"]) / QPC_FALLBACK_FREQUENCY / (high["frame"] - low["frame"])
            if not (1.0 / 75.0 <= seconds_per_presented_frame <= 1.0 / 45.0):
                raise ComparisonError(f"t={target_time} {name} bracket has implausible QPC cadence {seconds_per_presented_frame}")
            mesh_results[name] = {
                "timing": {
                    "bracketFrames": [low["frame"], high["frame"]],
                    "interpolationAlpha": alpha,
                    "bracketQpc": [low["timestampQpc"], high["timestampQpc"]],
                    "interpolatedTargetQpc": target_qpc,
                    "secondsPerPresentedFrame": seconds_per_presented_frame,
                },
                "resourceBinding": {
                    "low": low["resources"],
                    "high": high["resources"],
                    "contract": "source palette object is SRV-visible; selected mesh draw b2 ID equals a completed constant-buffer object ID",
                },
                **compare_mesh(name, unity[target_time]["meshes"][name], low["matrices"][name], high["matrices"][name], alpha),
            }
        samples.append({
            "unityRequestedSeconds": target_time,
            "unityActualSeconds": unity[target_time]["actualSeconds"],
            "timing": {
                "mapping": "retailSourceFrame = 129 + (presentedFrame - 2833); Unity source frame = 114 + 60*t",
                "targetRetailSourceFrame": target_source,
                "targetPresentedFrame": target_presented,
                "explicitUncertaintyFrames": 1.0,
                "requiredBoundary": [target_presented - 1.0, target_presented + 1.0],
                "qpcFrequency": QPC_FALLBACK_FREQUENCY,
                "qpcFrequencySource": "validated legacy-session fallback",
            },
            "meshes": mesh_results,
        })
    return {
        "schema": "endfield.endminf-retail-unity-retained-skinning-comparison.v1",
        "status": "compared_with_documented_limitations",
        "retailSession": str(session_root.resolve()),
        "unityReport": str(unity_report.resolve()),
        "samples": samples,
        "limitations": [
            "Unity palettes are CPU-computed after beauty rendering, not GPU readbacks of submitted VS constants.",
            "The retained Unity pose is driven by the recovered retail replay oracle, so this validates reconstruction/plumbing but is not an independent solver-quality test.",
            "The 8.4 MiB source palette and 4 MiB draw-time VS b2 constant buffer are distinct D3D11 objects; the capture proves source SRV visibility and exact b2 draw binding, not a direct object-ID equality between them.",
            "The legacy retail session omits qpcFrequency; the validated 10 MHz fallback is used and timing retains an explicit ±1 presented-frame boundary.",
            "The legacy capture is sparse and draw retention differs by mesh, so each mesh uses its nearest independently gated bracket; wide brackets are reported and can reduce interpolation fidelity.",
            "Retail roots are recovered with Unity bindposes and rejected unless affine, unit-scale, orthogonal, and right-handed before translation lerp/quaternion slerp.",
            "Only cloth_01, cloth_04, and hair are covered by exact retail index/palette contracts.",
        ],
    }


def compare_exact_frame(session_root: Path, unity_report: Path, target_time: float, retail_frame: int) -> dict:
    """Compare one Unity pose directly with one fully retained retail frame."""
    mesh_names = tuple(MESHES)
    session = load_json(session_root / "session.json")
    if session.get("gameBuild") != "endfield-2026-07-11-gameassembly-0c557367":
        raise ComparisonError("retail session is not the pinned Endfield build")
    if retail_frame < 0:
        raise ComparisonError("retail frame must be non-negative")
    unity = load_unity(unity_report, (target_time,), mesh_names)[target_time]
    frame_dir = session_root / "graphics" / "frames" / str(retail_frame)
    # The 20260828 peak frame retained the complete source palette and exact
    # draw-visible b2 object but omitted the older capture's duplicate SRV
    # alias row. Preserve that limitation explicitly instead of discarding the
    # otherwise complete direct-palette diagnostic.
    retail = decode_frame(frame_dir, mesh_names, require_palette_srv_alias=False)
    if retail["frame"] != retail_frame:
        raise ComparisonError(f"retail frame directory {retail_frame} contains frame {retail['frame']}")
    meshes = {}
    for name in mesh_names:
        meshes[name] = {
            "timing": {
                "retailFrame": retail_frame,
                "retailTimestampQpc": retail["timestampQpc"],
                "interpolationAlpha": 0.0,
            },
            "resourceBinding": retail["resources"],
            **compare_mesh(
                name,
                unity["meshes"][name],
                retail["matrices"][name],
                retail["matrices"][name],
                0.0,
            ),
        }
    return {
        "schema": "endfield.endminf-retail-unity-retained-skinning-comparison.v1",
        "status": "exact_frame_comparison",
        "retailSession": str(session_root.resolve()),
        "unityReport": str(unity_report.resolve()),
        "samples": [{
            "unityRequestedSeconds": target_time,
            "unityActualSeconds": unity["actualSeconds"],
            "timing": {
                "mapping": "explicit user-selected retail frame; no interpolation",
                "targetPresentedFrame": retail_frame,
                "explicitUncertaintyFrames": 0.0,
            },
            "meshes": meshes,
        }],
        "limitations": [
            "Unity palettes are CPU-computed after beauty rendering, not GPU readbacks of submitted VS constants.",
            "The retained Unity pose is driven by the recovered retail replay oracle, so this validates reconstruction/plumbing but is not an independent solver-quality test.",
            "Retail roots are recovered with Unity bindposes; exact-frame comparison assumes the selected retail and Unity samples describe the same animation phase.",
            "Baked-vertex checksums are retained separately but are not directly comparable because the retail capture does not contain a matching CPU-baked vertex stream.",
            "This peak capture omitted a duplicate draw-visible SRV alias row for the source palette; the complete palette and exact draw b2 object are retained, and sourcePaletteSrvAliasProven reports false.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("retail_session", type=Path)
    parser.add_argument("unity_report", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--retail-frame", type=int, help="compare directly against this retained retail frame")
    parser.add_argument("--time", type=float, help="Unity requestedSeconds paired with --retail-frame")
    args = parser.parse_args(argv)
    try:
        if (args.retail_frame is None) != (args.time is None):
            raise ComparisonError("--retail-frame and --time must be supplied together")
        if args.retail_frame is not None:
            result = compare_exact_frame(
                args.retail_session.resolve(), args.unity_report.resolve(), args.time, args.retail_frame
            )
        else:
            result = compare(args.retail_session.resolve(), args.unity_report.resolve())
    except (ComparisonError, OSError, ValueError, KeyError, struct.error) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    encoded = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(encoded, encoding="utf-8")
        print(f"wrote {args.output}")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
