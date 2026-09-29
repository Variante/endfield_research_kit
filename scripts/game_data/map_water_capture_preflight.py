"""Non-launching selected Map water capture preflight.

It binds the EndfieldCapture profile to the reviewed native and one authored
LevelData/StringPathHash/Mesh join, then runs the host's exact-file/runtime
``check`` command. It never arms or launches the game.
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.map_water_surface_join import (
    CONTRACT as SURFACE_CONTRACT,
    validate_map_water_surface_join,
)


NATIVE_CONTRACT = CONTRACTS_DIR / "map_water_getmesh_native.json"
DEFAULT_PROFILE = Path("tools/EndfieldCapture/config/map_water_volume_2026-08-25.json")
TRANSFORM_PROFILE = Path("tools/EndfieldCapture/config/map_water_volume_transform_2026-08-25.json")
SETUP_POSITION_PROFILE = Path("tools/EndfieldCapture/config/map_water_volume_setup_position_2026-08-25.json")


def _method_pin(profile: dict[str, Any], native: dict[str, Any], label: str) -> None:
    if (profile["rva"], profile["bodyBytes"], profile["sha256"].upper()) != (
        native["rva"], native["bodySize"], native["bodySha256"].upper()
    ):
        raise ValueError(f"map_water_capture:method-pin:{label}")


def _bind_profile(profile: dict[str, Any], native: dict[str, Any],
                  surface: dict[str, Any]) -> None:
    if (profile["schema"] not in (
            "endfieldCapture.mapWaterVolumeBuild.v1",
            "endfieldCapture.mapWaterVolumeBuild.v2",
            "endfieldCapture.mapWaterVolumeBuild.v3") or
            profile["profile"] != "map-water-volume"):
        raise ValueError("map_water_capture:profile-schema")
    capture = profile["capture"]
    source = surface["selectedSource"]
    mesh = surface["mesh"]
    if (capture["sceneId"], capture["waterVolumeId"],
            capture["meshPathHash"]) != (
                source["levelId"], int(source["waterVolumeId"]),
                mesh["meshPathHash"]):
        raise ValueError("map_water_capture:selected-source-identity")
    inputs = native["nativeInputs"]
    files = profile["files"]
    for key, expected in (("gameAssembly", inputs["gameAssemblySha256"]),
                          ("metadata", inputs["metadataSha256"]),
                          ("unityPlayer", inputs["unityPlayerSha256"])):
        if files[key]["sha256"].upper() != expected.upper():
            raise ValueError(f"map_water_capture:native-file-pin:{key}")
    fields = native["callerChain"]["fieldOffsets"]
    witness = native["captureWitness"]
    expected_fields = {
        "gameLevelIdFieldOffset": witness["gameLevelIdField"]["offset"],
        "levelWaterVolumeIdFieldOffset": fields["Beyond.Gameplay.LevelWaterVolumeData::id"],
        "waterVolumeIdFieldOffset": fields["Beyond.Gameplay.Core.WaterVolumeManager+WaterVolume::waterVolumeId"],
        "waterVolumeMeshPathHashFieldOffset": fields["Beyond.Gameplay.Core.WaterVolumeManager+WaterVolume::meshPathHash"],
        "waterVolumeSurfaceMeshMonoFieldOffset": fields["Beyond.Gameplay.Core.WaterVolumeManager+WaterVolume::surfaceMeshMono"],
    }
    for key, expected in expected_fields.items():
        if capture[key] != expected:
            raise ValueError(f"map_water_capture:field-offset:{key}")
    _method_pin(capture["setup"], native["callerChain"]["methods"][0], "Setup")
    _method_pin(capture["getMesh"], native["method"], "GetMesh")
    _method_pin(capture["updataMesh"], witness["updataMesh"], "UpdataMesh")
    if profile["schema"].endswith((".v2", ".v3")):
        final = native["finalTransformWitness"]
        if capture["surfaceMonoWaterVolumePtrFieldOffset"] != (
                final["waterVolumePtrField"]["offset"]):
            raise ValueError("map_water_capture:surface-volume-token-offset")
        methods = {row["name"]: row for row in final["methods"]}
        for key, name in (("tick", "Tick"), ("getPosition", "get_position"),
                          ("onRecycle", "OnRecycle")):
            _method_pin(capture[key], methods[name], name)
        if profile["schema"].endswith(".v3"):
            _method_pin(capture["setPosition"], methods["set_position"], "set_position")


def validate_map_water_capture_preflight(
    *, profile_path: Path, host_exe: Path, runtime_dll: Path,
    game_dir: Path, export_root: Path | None = None,
) -> dict[str, Any]:
    report: dict[str, Any] = {
        "schema": "endfield.map-water-capture-preflight.v1",
        "status": "unresolved",
    }
    try:
        profile = json.loads(profile_path.read_text(encoding="utf-8"))
        native = json.loads(NATIVE_CONTRACT.read_text(encoding="utf-8"))
        surface = json.loads(SURFACE_CONTRACT.read_text(encoding="utf-8"))
        _bind_profile(profile, native, surface)
        join = (validate_map_water_surface_join(export_root=export_root)
                if export_root is not None else validate_map_water_surface_join())
        report["selectedJoinStatus"] = join["status"]
        if join["status"] != "validated":
            report.update(status=join["status"], diagnostic=join.get("diagnostic"))
            return report
        command = [str(host_exe.resolve()), "check", "--map-water-volume",
                   "--manifest", str(profile_path.resolve()),
                   "--game-dir", str(game_dir.resolve()),
                   "--runtime", str(runtime_dll.resolve())]
        completed = subprocess.run(command, check=False, capture_output=True,
                                   text=True, timeout=120)
        if completed.returncode != 0:
            raise ValueError("map_water_capture:host-check:" +
                             (completed.stderr.strip() or str(completed.returncode)))
        host = json.loads(completed.stdout)
        if (host.get("command"), host.get("providers"), host.get("status"),
                host.get("gameBuild")) != (
                    "check", "map-water-volume", "validated",
                    profile["gameBuild"]):
            raise ValueError("map_water_capture:host-check-receipt")
        report.update(
            status="validated", sceneId=profile["capture"]["sceneId"],
            waterVolumeId=profile["capture"]["waterVolumeId"],
            meshPathHash=profile["capture"]["meshPathHash"],
            hostRuntimeSha256=host["runtimeSha256"],
            evidenceBoundary="installed-build and authored-input preflight only; no live water observation",
        )
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        report["diagnostic"] = str(exc)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--host-exe", type=Path, required=True)
    parser.add_argument("--runtime-dll", type=Path, required=True)
    parser.add_argument("--game-dir", type=Path, required=True)
    parser.add_argument("--export-root", type=Path)
    args = parser.parse_args()
    receipt = validate_map_water_capture_preflight(
        profile_path=args.profile, host_exe=args.host_exe,
        runtime_dll=args.runtime_dll, game_dir=args.game_dir,
        export_root=args.export_root,
    )
    print(json.dumps(receipt, indent=2))
    return 0 if receipt["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
