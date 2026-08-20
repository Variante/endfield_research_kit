"""Build a source-closed Cinemachine overview camera-track contract.

The important edge is resolved from serialized references, not names guessed
from a roster: ``vcam_overview`` -> child ``cm`` -> the component carrying
``m_Path`` -> the referenced Cinemachine path asset.  The resulting contract
is intentionally separate from the settled-render defaults.

Usage::

    python tools/build_charinfo_camera_track_contract.py
    python tools/build_charinfo_camera_track_contract.py --check
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = PROJECT_ROOT.parent
DEFAULT_WORK_ROOT = REPO_ROOT / "scratch/charinfo_playable_profiles"
DEFAULT_OUTPUT = (
    PROJECT_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/CharInfoPresentation"
    / "charinfo_camera_track_contract.json"
)
REQUIRED_ACTORS = {"endminf", "pelica", "chen"}
PATH_ID_RE = re.compile(r"_p([0-9A-Fa-f]{16})\.json$")
EPSILON = 1e-5


class TrackContractError(RuntimeError):
    """Fail-closed source recovery error."""


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise TrackContractError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise TrackContractError(f"expected JSON object: {path}")
    return value


def path_id_from_name(path: Path) -> int:
    match = PATH_ID_RE.search(path.name)
    if match is None:
        raise TrackContractError(f"cannot recover PathID from {path}")
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def path_id(path: Path, data: dict[str, Any]) -> int:
    metadata = data.get("$animestudio") or {}
    filename_value = path_id_from_name(path)
    metadata_value = int(metadata.get("pathId", filename_value))
    if metadata_value != filename_value:
        raise TrackContractError(
            f"PathID mismatch for {path}: metadata={metadata_value}, filename={filename_value}"
        )
    return metadata_value


def pptr(value: Any) -> int:
    if not isinstance(value, dict):
        return 0
    file_id = int(value.get("m_FileID", value.get("FileID", 0)) or 0)
    if file_id != 0:
        raise TrackContractError(f"external PPtr is unsupported: FileID={file_id}")
    return int(value.get("m_PathID", value.get("PathID", 0)) or 0)


def finite_float(value: Any, field: str) -> float:
    result = float(value)
    if not math.isfinite(result):
        raise TrackContractError(f"{field} is not finite: {value!r}")
    return result


def vector(value: Any, keys: tuple[str, ...] = ("x", "y", "z")) -> list[float]:
    if not isinstance(value, dict):
        raise TrackContractError("expected serialized vector")
    result: list[float] = []
    for key in keys:
        selected = None
        for candidate in (key, key.upper(), key.capitalize()):
            if candidate in value:
                selected = value[candidate]
                break
        if selected is None:
            raise TrackContractError(f"serialized vector is missing {key}")
        result.append(finite_float(selected, f"vector.{key}"))
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class SourceIndex:
    def __init__(self, work_root: Path):
        self.root = work_root / "dependencies_json"
        if not self.root.is_dir():
            raise TrackContractError(f"missing dependency export: {self.root}")
        self.objects: dict[str, dict[int, tuple[Path, dict[str, Any]]]] = {}
        for kind in ("GameObject", "Transform", "MonoBehaviour", "Light"):
            folder = self.root / kind
            indexed: dict[int, tuple[Path, dict[str, Any]]] = {}
            for path in sorted(folder.glob("*.json")) if folder.is_dir() else ():
                data = read_json(path)
                identifier = path_id(path, data)
                if identifier in indexed:
                    raise TrackContractError(f"duplicate {kind} PathID {identifier}")
                indexed[identifier] = (path, data)
            self.objects[kind] = indexed
        self.component_owner: dict[int, int] = {}
        for game_object_id, (_, data) in self.objects["GameObject"].items():
            for component in data.get("m_Components") or []:
                identifier = pptr(component)
                if identifier:
                    previous = self.component_owner.setdefault(identifier, game_object_id)
                    if previous != game_object_id:
                        raise TrackContractError(
                            f"component {identifier} has multiple GameObject owners"
                        )

    def get(self, kind: str, identifier: int) -> tuple[Path, dict[str, Any]]:
        value = self.objects.get(kind, {}).get(identifier)
        if value is None:
            raise TrackContractError(f"unresolved {kind} PathID {identifier}")
        return value

    def component_kind(self, identifier: int) -> str:
        if identifier in self.objects["Transform"]:
            return "Transform"
        if identifier in self.objects["Light"]:
            return "Light"
        behaviour = self.objects["MonoBehaviour"].get(identifier)
        if behaviour is None:
            return "Unknown"
        data = behaviour[1]
        if "m_Path" in data:
            return "CinemachineTrackedDolly"
        if "m_Waypoints" in data and "m_Resolution" in data:
            return "CinemachinePath"
        if "m_Lens" in data:
            return "CinemachineVirtualCamera"
        if "offsetX" in data and "offsetY" in data:
            return "UIGyroscopeEffect"
        return "MonoBehaviour"

    def hierarchy_path(self, game_object_id: int) -> str:
        names: list[str] = []
        visited: set[int] = set()
        current = game_object_id
        while current and current not in visited:
            visited.add(current)
            _, game_object = self.get("GameObject", current)
            names.append(str(game_object.get("m_Name") or game_object.get("Name") or ""))
            parent_transform = pptr((game_object.get("m_Transform") or {}).get("m_Father"))
            current = self.component_owner.get(parent_transform, 0)
        if current in visited:
            raise TrackContractError(f"GameObject hierarchy cycle at {game_object_id}")
        return "/".join(reversed(names))

    def find_path(self, expected: str) -> int:
        matches = [
            identifier
            for identifier in self.objects["GameObject"]
            if self.hierarchy_path(identifier).casefold() == expected.casefold()
        ]
        if len(matches) != 1:
            raise TrackContractError(f"expected one GameObject {expected}; found {len(matches)}")
        return matches[0]


def source_record(repo_root: Path, path: Path, data: dict[str, Any]) -> dict[str, Any]:
    metadata = data.get("$animestudio") or {}
    try:
        relative = path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        relative = path.as_posix()
    return {
        "path": relative,
        "path_id": path_id(path, data),
        "sha256": sha256(path),
        "source_file": str(metadata.get("sourceFile") or ""),
        "source_original_file": Path(
            str(metadata.get("sourceOriginalPath") or "")
        ).name,
        "source_offset": int(metadata.get("sourceOffset") or 0),
        "raw_data_sha256": str(metadata.get("rawDataSha256") or ""),
    }


def qmul(left: list[float], right: list[float]) -> list[float]:
    lx, ly, lz, lw = left
    rx, ry, rz, rw = right
    return [
        lw * rx + lx * rw + ly * rz - lz * ry,
        lw * ry - lx * rz + ly * rw + lz * rx,
        lw * rz + lx * ry - ly * rx + lz * rw,
        lw * rw - lx * rx - ly * ry - lz * rz,
    ]


def qnorm(value: list[float]) -> list[float]:
    length = math.sqrt(sum(item * item for item in value))
    return [0.0, 0.0, 0.0, 1.0] if length <= 1e-12 else [item / length for item in value]


def qrotate(rotation: list[float], point: list[float]) -> list[float]:
    x, y, z, w = qnorm(rotation)
    px, py, pz = point
    tx = 2.0 * (y * pz - z * py)
    ty = 2.0 * (z * px - x * pz)
    tz = 2.0 * (x * py - y * px)
    return [
        px + w * tx + y * tz - z * ty,
        py + w * ty + z * tx - x * tz,
        pz + w * tz + x * ty - y * tx,
    ]


def add(left: list[float], right: list[float]) -> list[float]:
    return [a + b for a, b in zip(left, right)]


def mul(left: list[float], right: list[float]) -> list[float]:
    return [a * b for a, b in zip(left, right)]


def root_relative_transform(index: SourceIndex, game_object_id: int, root_id: int) -> tuple[list[float], list[float], list[float]]:
    chain: list[dict[str, Any]] = []
    current = game_object_id
    visited: set[int] = set()
    while current and current not in visited:
        visited.add(current)
        _, game_object = index.get("GameObject", current)
        chain.append(game_object.get("m_Transform") or {})
        if current == root_id:
            break
        current = index.component_owner.get(pptr(chain[-1].get("m_Father")), 0)
    if current != root_id:
        raise TrackContractError(f"GameObject {game_object_id} is not below root {root_id}")
    position, rotation, scale = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0, 1.0], [1.0, 1.0, 1.0]
    for transform in reversed(chain[:-1]):
        local_position = vector(transform.get("m_LocalPosition"))
        local_rotation = vector(transform.get("m_LocalRotation"), ("x", "y", "z", "w"))
        local_scale = vector(transform.get("m_LocalScale"))
        position = add(position, qrotate(rotation, mul(scale, local_position)))
        rotation = qnorm(qmul(rotation, local_rotation))
        scale = mul(scale, local_scale)
    return position, rotation, scale


def point_in_root(index: SourceIndex, game_object_id: int, root_id: int, point: list[float]) -> list[float]:
    position, rotation, scale = root_relative_transform(index, game_object_id, root_id)
    return add(position, qrotate(rotation, mul(scale, point)))


def max_delta(left: list[float], right: list[float]) -> float:
    values = [finite_float(abs(a - b), "endpoint delta") for a, b in zip(left, right)]
    return max(values)


def path_payload(repo_root: Path, index: SourceIndex, path_id_value: int, root_id: int, static_position: list[float]) -> dict[str, Any]:
    path_file, path_data = index.get("MonoBehaviour", path_id_value)
    if "m_Waypoints" not in path_data or "m_Resolution" not in path_data:
        raise TrackContractError(f"PathID {path_id_value} is not a Cinemachine path")
    path_game_object_id = pptr(path_data.get("m_GameObject"))
    path_game_object_file, path_game_object = index.get("GameObject", path_game_object_id)
    waypoints = []
    for waypoint in path_data.get("m_Waypoints") or []:
        waypoints.append({"position": vector(waypoint.get("position")), "roll": finite_float(waypoint.get("roll") or 0.0, "waypoint.roll")})
    if not waypoints:
        raise TrackContractError(f"path {path_file} has no waypoints")
    endpoint = point_in_root(index, path_game_object_id, root_id, waypoints[-1]["position"])
    delta = max_delta(endpoint, static_position)
    if delta > EPSILON:
        raise TrackContractError(f"path endpoint differs from static camera by {delta:g}")
    return {
        "name": str(path_game_object.get("m_Name") or path_game_object.get("Name") or ""),
        "path_id": path_id_value,
        "source": source_record(repo_root, path_file, path_data),
        "game_object": source_record(repo_root, path_game_object_file, path_game_object),
        "m_Resolution": int(path_data["m_Resolution"]),
        "m_Looped": int(path_data.get("m_Looped") or 0),
        "resolution": int(path_data["m_Resolution"]),
        "loop": bool(path_data.get("m_Looped")),
        "waypoints": waypoints,
        "endpoint": endpoint,
    }


def build_entry(repo_root: Path, index: SourceIndex, item: dict[str, Any]) -> dict[str, Any]:
    actor = str(item.get("actor_token") or "")
    track = str(item.get("camera_group") or "").replace("\\", "/").rsplit("/", 1)[-1]
    if not track:
        raise TrackContractError(f"{actor} has no camera group")
    root_id = index.find_path(track)
    vcam_path = f"{track}/DollyCart/vcam_overview"
    cm_path = f"{vcam_path}/cm"
    lookat_path = f"{track}/LookAtGroup/lookat_overview/lookat_overview_ani"
    vcam_id, cm_id, lookat_id = (index.find_path(vcam_path), index.find_path(cm_path), index.find_path(lookat_path))
    vcam_file, vcam_data = index.get("GameObject", vcam_id)
    cm_file, cm_data = index.get("GameObject", cm_id)
    lookat_file, lookat_data = index.get("GameObject", lookat_id)
    static_position = root_relative_transform(index, vcam_id, root_id)[0]
    tracked = []
    for component in cm_data.get("m_Components") or []:
        component_id = pptr(component)
        behaviour = index.objects["MonoBehaviour"].get(component_id)
        if behaviour and "m_Path" in behaviour[1]:
            tracked.append((component_id, behaviour[0], behaviour[1]))
    if len(tracked) != 1:
        raise TrackContractError(f"{actor} overview cm has {len(tracked)} TrackedDolly components")
    tracked_id, tracked_file, tracked_data = tracked[0]
    pointer = tracked_data.get("m_Path") or {}
    referenced_path_id = pptr(pointer)
    if not referenced_path_id:
        raise TrackContractError(f"{actor} TrackedDolly.m_Path is null")
    path_file, path_data = index.get("MonoBehaviour", referenced_path_id)
    path = path_payload(repo_root, index, referenced_path_id, root_id, static_position)
    position_damping = {field: finite_float(tracked_data.get(field) or 0.0, field) for field in ("m_XDamping", "m_YDamping", "m_ZDamping", "m_PitchDamping", "m_YawDamping", "m_RollDamping")}
    lookat_components = []
    for component in lookat_data.get("m_Components") or []:
        component_id = pptr(component)
        lookat_components.append({"path_id": component_id, "type": index.component_kind(component_id)})
    return {
        "actor": actor,
        "character_id": str(item.get("character_id") or ""),
        "track_root": track,
        "vcam_overview": {"path": f"{track}/DollyCart/vcam_overview", "source": source_record(repo_root, vcam_file, vcam_data), "static_position": static_position},
        "cm": {"path": cm_path, "source": source_record(repo_root, cm_file, cm_data)},
        "tracked_dolly": {"component_type": "CinemachineTrackedDolly", "path": cm_path, "source": source_record(repo_root, tracked_file, tracked_data), "m_Path": {"file_id": int(pointer.get("m_FileID") or 0), "path_id": referenced_path_id, "target_type": "MonoBehaviour", "target_name": str(path_data.get("m_Name") or path["name"]), "source": source_record(repo_root, path_file, path_data)}, "m_PathPosition": float(tracked_data.get("m_PathPosition") or 0.0), "m_PositionUnits": int(tracked_data.get("m_PositionUnits") or 0), "m_PathOffset": vector(tracked_data.get("m_PathOffset")), "m_PositionDamping": position_damping, "m_AutoDolly": dict(tracked_data.get("m_AutoDolly") or {})},
        "path": path,
        "lookat_overview_ani": {"path": lookat_path, "source": source_record(repo_root, lookat_file, lookat_data), "component_types": [entry["type"] for entry in lookat_components], "components": lookat_components},
        "endpoint_validation": {"static_camera_position": static_position, "path_endpoint": path["endpoint"], "max_abs_delta": max_delta(static_position, path["endpoint"]), "ok": True},
    }


def build_contract(work_root: Path, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    plan = read_json(work_root / "source_plan.json")
    rows = [row for row in plan.get("characters") or [] if isinstance(row, dict)]
    if not rows:
        raise TrackContractError("source plan has no characters")
    index = SourceIndex(work_root)
    entries = [build_entry(repo_root, index, row) for row in rows]
    actors = {entry["actor"] for entry in entries}
    missing = REQUIRED_ACTORS - actors
    if missing:
        raise TrackContractError("required actors absent: " + ", ".join(sorted(missing)))
    try:
        relative_work_root = work_root.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise TrackContractError(f"work root is outside repository: {work_root}") from error
    return {"schema": "endfield.charinfo.camera-track.v1", "boundary": "serialized_pptr_vcam_to_tracked_dolly_path", "source": {"work_root": relative_work_root, "source_plan": f"{relative_work_root}/source_plan.json", "edge": "vcam_overview -> cm -> TrackedDolly.m_Path"}, "required_actors": sorted(REQUIRED_ACTORS), "character_count": len(entries), "characters": entries}


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        contract = build_contract(args.work_root.resolve(), REPO_ROOT)
    except TrackContractError as error:
        print(f"camera track contract failed: {error}", file=sys.stderr)
        return 2
    if args.check:
        if not args.output.is_file():
            print(f"missing contract: {args.output}", file=sys.stderr)
            return 2
        if read_json(args.output) != contract:
            print("contract differs from serialized camera tracks", file=sys.stderr)
            return 1
        print(f"camera track contract matches: {contract['character_count']} characters")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(contract, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {args.output} ({contract['character_count']} characters)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
