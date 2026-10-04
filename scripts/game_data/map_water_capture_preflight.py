"""Validate frozen profiles for saved Map water evidence without a capture host."""
from __future__ import annotations

from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.map_water_surface_join import CONTRACT as SURFACE_CONTRACT


NATIVE_CONTRACT = CONTRACTS_DIR / "map_water_getmesh_native.json"
DEFAULT_PROFILE = CONTRACTS_DIR / "map_water_capture_profile.json"
TRANSFORM_PROFILE = CONTRACTS_DIR / "map_water_transform_capture_profile.json"
SETUP_POSITION_PROFILE = CONTRACTS_DIR / "map_water_setup_position_capture_profile.json"


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
