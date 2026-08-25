#!/usr/bin/env python3
"""Build owner-tagged Endminf bone trajectories from captured skin palettes."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
MANIFEST = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf"
    / "endminf_ui_recovery_manifest.json"
)
MESH_ROOT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf/Meshes"
)
SOLVER_INPUTS = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "secondary_dynamics_solver_inputs.json"
)
DEFAULT_OUTPUT = (
    REPO_ROOT
    / "reports/assets/character_recovery"
    / "endminf_captured_secondary_dynamics_oracle.json"
)
MESH_NAMES = {
    "body": "S_actor_endminf_body_01_lod0",
    "cloth_01": "S_actor_endminf_cloth_01_lod0",
    "cloth_04": "S_actor_endminf_cloth_04_lod0",
    "hair": "S_actor_endminf_hair_01_lod0",
}
SHARED_MATRIX_TOLERANCE = 1e-5
ORTHONORMALITY_TOLERANCE = 5e-5


class OracleError(ValueError):
    pass


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OracleError(f"cannot read {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise OracleError(f"{path} must contain one JSON object")
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


def multiply(left: list[list[float]], right: list[list[float]]) -> list[list[float]]:
    return [
        [
            sum(left[row][inner] * right[inner][column] for inner in range(4))
            for column in range(4)
        ]
        for row in range(4)
    ]


def inverse(matrix: list[list[float]]) -> list[list[float]]:
    work = [
        row[:] + [1.0 if row_index == column else 0.0 for column in range(4)]
        for row_index, row in enumerate(matrix)
    ]
    for column in range(4):
        pivot = max(range(column, 4), key=lambda row: abs(work[row][column]))
        if abs(work[pivot][column]) < 1e-10:
            raise OracleError("encountered a singular bind-pose matrix")
        work[column], work[pivot] = work[pivot], work[column]
        scale = work[column][column]
        work[column] = [value / scale for value in work[column]]
        for row in range(4):
            if row == column:
                continue
            scale = work[row][column]
            work[row] = [
                value - scale * pivot_value
                for value, pivot_value in zip(work[row], work[column])
            ]
    return [row[4:] for row in work]


def parse_bindposes(path: Path) -> list[list[list[float]]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise OracleError(f"cannot read mesh asset {path}: {exc}") from exc
    try:
        section = text.split("  m_BindPose:\n", 1)[1].split(
            "  m_BoneNameHashes:", 1
        )[0]
    except IndexError as exc:
        raise OracleError(f"mesh asset {path} has no bounded bind-pose section") from exc
    rows: list[dict[str, float]] = []
    current: dict[str, float] | None = None
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- e00:"):
            current = {"e00": float(stripped.split(":", 1)[1])}
            rows.append(current)
        elif current is not None and stripped.startswith("e") and ":" in stripped:
            key, value = stripped.split(":", 1)
            current[key] = float(value)
    matrices = []
    for index, row in enumerate(rows):
        keys = [f"e{r}{c}" for r in range(4) for c in range(4)]
        if any(key not in row for key in keys):
            raise OracleError(f"bind pose {index} in {path} is incomplete")
        matrices.append([[row[f"e{r}{c}"] for c in range(4)] for r in range(4)])
    if not matrices:
        raise OracleError(f"mesh asset {path} has no bind poses")
    return matrices


def skin_matrix(rows: list[list[float]]) -> list[list[float]]:
    if len(rows) != 3 or any(len(row) != 4 for row in rows):
        raise OracleError("captured skin matrix must contain three float4 rows")
    return [list(row) for row in rows] + [[0.0, 0.0, 0.0, 1.0]]


def max_delta(left: list[list[float]], right: list[list[float]]) -> float:
    return max(
        abs(a - b)
        for left_row, right_row in zip(left, right)
        for a, b in zip(left_row, right_row)
    )


def orthonormality_error(matrix: list[list[float]]) -> float:
    basis = [row[:3] for row in matrix[:3]]
    return max(
        abs(
            sum(basis[left][axis] * basis[right][axis] for axis in range(3))
            - (1.0 if left == right else 0.0)
        )
        for left in range(3)
        for right in range(3)
    )


def motion_delta(current: list[list[float]], previous: list[list[float]]) -> tuple[float, float]:
    translation = math.sqrt(sum(
        (current[row][3] - previous[row][3]) ** 2 for row in range(3)
    ))
    trace = sum(
        current[row][axis] * previous[row][axis]
        for row in range(3)
        for axis in range(3)
    )
    cosine = max(-1.0, min(1.0, (trace - 1.0) * 0.5))
    return translation, math.degrees(math.acos(cosine))


def mesh_contracts(manifest: dict) -> tuple[dict, dict[str, str]]:
    manifest_meshes = {row["name"]: row for row in manifest.get("meshes", [])}
    contracts = {}
    hashes = {}
    for token, name in MESH_NAMES.items():
        if name not in manifest_meshes:
            raise OracleError(f"manifest has no mesh {name}")
        source = manifest_meshes[name]
        mesh_path = MESH_ROOT / f"{name}.asset"
        bindposes = parse_bindposes(mesh_path)
        paths = source.get("bone_paths", [])
        if len(paths) != len(bindposes):
            raise OracleError(
                f"{name} has {len(paths)} bone paths but {len(bindposes)} bind poses"
            )
        contracts[token] = list(zip(paths, [inverse(row) for row in bindposes]))
        hashes[relative(mesh_path)] = sha256(mesh_path)
    return contracts, hashes


def recover_frame(frame: dict, contracts: dict) -> tuple[dict, dict, dict]:
    current: dict[str, tuple[str, list[list[float]]]] = {}
    previous: dict[str, tuple[str, list[list[float]]]] = {}
    validation = {"sharedComparisons": 0, "worstSharedDelta": 0.0,
                  "worstShared": None, "worstOrthonormalityError": 0.0,
                  "worstOrthonormalBone": None}
    for token, rows in contracts.items():
        mesh = frame.get("meshes", {}).get(token)
        if not mesh:
            raise OracleError(f"frame {frame.get('frame')} has no decoded {token} mesh")
        current_rows = mesh.get("currentMatrices3x4", [])
        previous_rows = mesh.get("previousMatrices3x4", [])
        if len(rows) != len(current_rows) or len(rows) != len(previous_rows):
            raise OracleError(f"frame {frame.get('frame')} {token} matrix count drift")
        for (path, inverse_bindpose), current_skin, previous_skin in zip(
            rows, current_rows, previous_rows
        ):
            current_bone = multiply(skin_matrix(current_skin), inverse_bindpose)
            previous_bone = multiply(skin_matrix(previous_skin), inverse_bindpose)
            error = max(
                orthonormality_error(current_bone),
                orthonormality_error(previous_bone),
            )
            if error > validation["worstOrthonormalityError"]:
                validation["worstOrthonormalityError"] = error
                validation["worstOrthonormalBone"] = [token, path]
            if path in current:
                delta = max(
                    max_delta(current[path][1], current_bone),
                    max_delta(previous[path][1], previous_bone),
                )
                validation["sharedComparisons"] += 1
                if delta > validation["worstSharedDelta"]:
                    validation["worstSharedDelta"] = delta
                    validation["worstShared"] = [current[path][0], token, path]
            else:
                current[path] = (token, current_bone)
                previous[path] = (token, previous_bone)
    return current, previous, validation


def build_oracle(decoded_path: Path) -> dict:
    decoded = load_json(decoded_path)
    manifest = load_json(MANIFEST)
    solver = load_json(SOLVER_INPUTS)
    contracts, mesh_hashes = mesh_contracts(manifest)
    owner_sources = solver.get("actors", {}).get("endminf", {}).get("cloths", [])
    if len(owner_sources) != 4:
        raise OracleError(f"expected four Endminf cloth owners, found {len(owner_sources)}")

    owner_rows = []
    owner_paths = set()
    for owner in owner_sources:
        authored = [row["path"] for row in owner.get("proxy_transform_bindings", [])]
        row = {
            "owner": owner["game_object_path"],
            "authoredProxyCount": len(authored),
            "authoredRootPaths": [item["path"] for item in owner.get("root_bones", [])],
            "_authoredProxyPaths": authored,
        }
        owner_rows.append(row)
        owner_paths.update(authored)

    frames = []
    aggregate = {"sharedComparisons": 0, "worstSharedDelta": 0.0,
                 "worstShared": None, "worstOrthonormalityError": 0.0,
                 "worstOrthonormalBone": None}
    captured_owner_paths = set()
    motion = {}
    for frame in decoded.get("frames", []):
        current, previous, validation = recover_frame(frame, contracts)
        aggregate["sharedComparisons"] += validation["sharedComparisons"]
        if validation["worstSharedDelta"] > aggregate["worstSharedDelta"]:
            aggregate["worstSharedDelta"] = validation["worstSharedDelta"]
            aggregate["worstShared"] = [frame["frame"], *validation["worstShared"]]
        if validation["worstOrthonormalityError"] > aggregate["worstOrthonormalityError"]:
            aggregate["worstOrthonormalityError"] = validation["worstOrthonormalityError"]
            aggregate["worstOrthonormalBone"] = [
                frame["frame"], *validation["worstOrthonormalBone"]
            ]
        paths = sorted(owner_paths.intersection(current))
        captured_owner_paths.update(paths)
        matrices = []
        for path in paths:
            translation, rotation = motion_delta(current[path][1], previous[path][1])
            row = motion.setdefault(path, {"maxTranslation": 0.0, "maxRotationDegrees": 0.0})
            row["maxTranslation"] = max(row["maxTranslation"], translation)
            row["maxRotationDegrees"] = max(row["maxRotationDegrees"], rotation)
            matrices.append({
                "path": path,
                "currentRootSpace3x4": current[path][1][:3],
                "previousRootSpace3x4": previous[path][1][:3],
            })
        frames.append({"presentedFrame": frame["frame"], "ownerBoneMatrices": matrices})

    if not frames:
        raise OracleError("decoded capture contains no frames")
    if aggregate["worstSharedDelta"] > SHARED_MATRIX_TOLERANCE:
        raise OracleError(
            f"shared renderer bones disagree by {aggregate['worstSharedDelta']}"
        )
    if aggregate["worstOrthonormalityError"] > ORTHONORMALITY_TOLERANCE:
        raise OracleError(
            "reconstructed bone matrices are not orthonormal: "
            f"{aggregate['worstOrthonormalityError']}"
        )

    for row in owner_rows:
        authored = row.pop("_authoredProxyPaths")
        captured = [path for path in authored if path in captured_owner_paths]
        row["capturedProxyCount"] = len(captured)
        row["capturedProxyPaths"] = captured
        row["missingProxyPaths"] = [
            path for path in authored if path not in captured_owner_paths
        ]
        row["motionMaxima"] = {
            path: motion[path] for path in captured if path in motion
        }

    session_root = Path(decoded.get("sessionRoot", ""))
    return {
        "schema": "endfield.charinfo.endminf-captured-secondary-dynamics-oracle.v1",
        "status": "owner_tagged_retail_skinning_trajectories_recovered",
        "captureSession": session_root.name,
        "scope": "captured skinned bones only; not a complete solver-state capture",
        "frameCount": len(frames),
        "presentedFrameInterval": {
            "minimum": min(
                right["presentedFrame"] - left["presentedFrame"]
                for left, right in zip(frames, frames[1:])
            ),
            "maximum": max(
                right["presentedFrame"] - left["presentedFrame"]
                for left, right in zip(frames, frames[1:])
            ),
        },
        "sources": {
            relative(Path(__file__)): sha256(Path(__file__)),
            relative(decoded_path): sha256(decoded_path),
            relative(MANIFEST): sha256(MANIFEST),
            relative(SOLVER_INPUTS): sha256(SOLVER_INPUTS),
            **mesh_hashes,
        },
        "validation": aggregate,
        "owners": owner_rows,
        "frames": frames,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("decoded_capture", type=Path)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = build_oracle(args.decoded_capture.resolve())
    except (OracleError, OSError, ValueError) as exc:
        print(f"error: {exc}")
        return 2
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
