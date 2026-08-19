"""Recover the per-character CharInfo overview camera from source prefabs.

`PhaseCharInfo._RefreshCharModelAddon` instantiates
`charDisplayData.charInfoCameraGroup`, which resolves to
`gameplay/prefabs/charinfo/cameratracks/track_chr_<template>.prefab`. Each track
is a Cinemachine rig carrying a virtual camera, look-at target and post volume
per Character Info tab. The overview state, which is what the reference captures
and the recorded roster walkthrough show, is `vcam_overview` plus
`lookat_overview`.

Do not read the camera set out of `CharacterDisplayConfig`. Its
`CharacterDisplayData` entries deserialise as SerializeReference and AnimeStudio
records them unparsed, so only best-effort string hints survive: 15 of its 33
entries yield none at all. Counting camera groups there suggests 11 characters
have one, which the asset map contradicts.

Walk both asset maps. chr_0035_liino ships in the Persistent VFS rather than
StreamingAssets, so a StreamingAssets-only scan silently yields 30 characters
instead of 31 and the missing one fails closed at framing time.

This replaces image-fitted framing with source data. It does not recover the
per-frame cursor and UIGyroscopeEffect offset, which stays unknown and is why
two captures of the same character still disagree.

Usage:
    python tools/build_charinfo_overview_camera_contract.py --extract-root <dir>
    python tools/build_charinfo_overview_camera_contract.py --check
"""

from __future__ import annotations

import argparse
import glob
import hashlib
import io
import json
import os
import re
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTRACT_PATH = os.path.join(
    PROJECT_ROOT,
    "Assets",
    "EndfieldGraphShaderLab",
    "Generated",
    "OriginalData",
    "CharInfoPresentation",
    "charinfo_overview_camera_contract.json",
)
DEFAULT_EXTRACT_ROOT = os.path.join(
    PROJECT_ROOT,
    "scratch",
    "character_recovery",
    "gameplay_reference",
    "charinfo_prefabs",
)

PATH_ID_SUFFIX = re.compile(r"_p([0-9A-Fa-f]{16})\.json$")
OVERVIEW_NODES = ("vcam_overview", "lookat_overview", "volume_overview")
SIXTEEN_BY_NINE = 1.7777778

# Independently recovered earlier from the CharInfo presentation work. The
# contract must reproduce these or the extraction has drifted.
WULFA_LOOK_AT = (0.022, 1.19, 0.0)
WULFA_VCAM_ROTATION = (-0.00036646938, 0.9991945, 0.009385596, 0.03901448)
# Field of view was hand-passed per render call before the lens was recovered.
# These two are the values the lab already used, so the extracted Cinemachine
# lens has to reproduce them.
WULFA_FOV = 20.0
ZHUANGFY_FOV = 20.007383


class CameraContractError(RuntimeError):
    """Fail-closed recovery error."""


def _path_id(filename: str) -> int | None:
    match = PATH_ID_SUFFIX.search(filename)
    if match is None:
        return None
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def _vector(value: dict | None) -> list[float] | None:
    if not value:
        return None
    return [float(value["X"]), float(value["Y"]), float(value["Z"])]


def _quaternion(value: dict | None) -> list[float] | None:
    if not value:
        return None
    return [float(value["X"]), float(value["Y"]), float(value["Z"]), float(value["W"])]


def collect(extract_root: str) -> dict:
    groups = sorted(glob.glob(os.path.join(extract_root, "out_*")))
    if not groups:
        raise CameraContractError(f"no extracted prefab groups under {extract_root}")

    tracks: dict[str, dict] = {}
    for group in groups:
        light_group = group.replace("out_", "lights_")
        transforms: dict[int, dict] = {}
        by_game_object: dict[int, int] = {}
        for path in glob.glob(os.path.join(group, "Transform", "*.json")):
            pid = _path_id(path)
            if pid is None:
                continue
            try:
                data = json.load(io.open(path, encoding="utf-8"))
            except Exception:
                continue
            owner = data.get("m_GameObject") or {}
            transforms[pid] = {
                "name": owner.get("Name") or "",
                "father": (data.get("m_Father") or {}).get("m_PathID"),
                "position": data.get("m_LocalPosition"),
                "rotation": data.get("m_LocalRotation"),
            }
            by_game_object[owner.get("m_PathID")] = pid

        def owning_track(pid: int) -> str | None:
            seen: set[int] = set()
            while pid and pid not in seen:
                seen.add(pid)
                node = transforms.get(pid)
                if node is None:
                    return None
                if node["name"].startswith("track_chr_"):
                    return node["name"]
                pid = node["father"]
            return None

        for pid, node in transforms.items():
            if node["name"] not in OVERVIEW_NODES:
                continue
            track = owning_track(pid)
            if not track:
                continue
            tracks.setdefault(track, {})[node["name"]] = {
                "localPosition": _vector(node["position"]),
                "localRotation": _quaternion(node["rotation"]),
            }

        # The Cinemachine virtual camera on vcam_overview carries the lens.
        # Field of view varies per character; near and far do not, and match
        # the values the framing code already applies.
        for path in glob.glob(os.path.join(light_group, "MonoBehaviour", "*.json")):
            try:
                data = json.load(io.open(path, encoding="utf-8"))
            except Exception:
                continue
            lens = data.get("m_Lens")
            if not isinstance(lens, dict):
                continue
            pid = by_game_object.get((data.get("m_GameObject") or {}).get("m_PathID"))
            if pid is None or transforms[pid]["name"] != "vcam_overview":
                continue
            track = owning_track(pid)
            if not track:
                continue
            tracks.setdefault(track, {})["lens"] = {
                "fieldOfView": float(lens["FieldOfView"]),
                "nearClipPlane": float(lens["NearClipPlane"]),
                "farClipPlane": float(lens["FarClipPlane"]),
                "dutch": float(lens["Dutch"]),
                "gateFit": int(lens["GateFit"]),
                "modeOverride": int(lens.get("ModeOverride", 0)),
                "sensorSize": [
                    float(lens["m_SensorSize"]["x"]),
                    float(lens["m_SensorSize"]["y"]),
                ],
                "priority": data.get("m_Priority"),
            }
    return tracks


def build(extract_root: str) -> dict:
    tracks = collect(extract_root)
    characters = {}
    for track in sorted(tracks):
        entry = tracks[track]
        vcam = entry.get("vcam_overview")
        look = entry.get("lookat_overview")
        lens = entry.get("lens")
        if not vcam or not look:
            raise CameraContractError(
                f"{track} is missing vcam_overview or lookat_overview"
            )
        if not lens:
            raise CameraContractError(
                f"{track} has no Cinemachine lens on vcam_overview"
            )
        template = track[len("track_") :]
        characters[template] = {
            "track": track,
            "actor": template.split("_", 2)[-1],
            "vcamOverview": vcam,
            "lookAtOverview": look,
            "volumeOverview": entry.get("volume_overview"),
            "lens": lens,
        }

    wulfa = characters.get("chr_0028_wulfa")
    if wulfa is None:
        raise CameraContractError("chr_0028_wulfa is absent; cannot self-check")
    look = tuple(round(v, 9) for v in wulfa["lookAtOverview"]["localPosition"])
    rot = tuple(round(v, 9) for v in wulfa["vcamOverview"]["localRotation"])
    if look != tuple(round(v, 9) for v in WULFA_LOOK_AT):
        raise CameraContractError(f"Wulfa look-at drifted: {look}")
    if rot != tuple(round(v, 9) for v in WULFA_VCAM_ROTATION):
        raise CameraContractError(f"Wulfa vcam rotation drifted: {rot}")
    if wulfa["lens"]["fieldOfView"] != WULFA_FOV:
        raise CameraContractError(
            f"Wulfa field of view drifted: {wulfa['lens']['fieldOfView']}"
        )
    zhuangfy = characters.get("chr_0030_zhuangfy")
    if zhuangfy is None:
        raise CameraContractError("chr_0030_zhuangfy is absent; cannot self-check")
    if zhuangfy["lens"]["fieldOfView"] != ZHUANGFY_FOV:
        raise CameraContractError(
            f"Zhuangfy field of view drifted: {zhuangfy['lens']['fieldOfView']}"
        )

    # Near and far are uniform and match what the framing code already applies;
    # if that ever stops being true the hard-coded clip planes are wrong.
    for template, entry in characters.items():
        lens = entry["lens"]
        if lens["nearClipPlane"] != 0.1 or lens["farClipPlane"] != 50.0:
            raise CameraContractError(
                f"{template} has non-uniform clip planes: "
                f"near {lens['nearClipPlane']}, far {lens['farClipPlane']}"
            )
        if lens["dutch"] != 0.0:
            raise CameraContractError(f"{template} has a non-zero Dutch roll")

    return {
        "schema": "endfield.charinfo.overview-camera.v1",
        "boundary": "source_closed_per_character_framing",
        "source": {
            "lua": "Lua/Data/LuaScripts/Phase/CharInfo/PhaseCharInfo.lua",
            "luaFunction": "PhaseCharInfo._RefreshCharModelAddon",
            "field": "charDisplayData.charInfoCameraGroup",
            "prefabRoot": (
                "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/cameratracks/"
            ),
            "overviewNodes": list(OVERVIEW_NODES),
        },
        "selfCheck": {
            "character": "chr_0028_wulfa",
            "note": (
                "The look-at position and vcam rotation reproduce the values the "
                "CharInfo presentation work had already recovered independently, "
                "which is what ties this prefab to that data."
            ),
            "lookAtLocalPosition": list(WULFA_LOOK_AT),
            "vcamLocalRotation": list(WULFA_VCAM_ROTATION),
            "fieldOfView": WULFA_FOV,
            "zhuangfyFieldOfView": ZHUANGFY_FOV,
            "fieldOfViewNote": (
                "Field of view used to be hand-passed per render call. The "
                "extracted Cinemachine lens reproduces both values the lab "
                "already used, which is what ties the lens to that data."
            ),
        },
        "lensNote": (
            "Field of view varies per character across five distinct values "
            "clustered just above 20 degrees, so a single constant is wrong for "
            "13 of 31. Near 0.1 and far 50.0 are uniform and match the framing "
            "code. Every ModeOverride is 0, so the physical-camera sensor size "
            "is inert; chr_0027_tangtang carries a non-16:9 sensor that has no "
            "effect and is recorded rather than applied."
        ),
        "unrecovered": (
            "The per-frame cursor and UIGyroscopeEffect offset. Framing is now "
            "source-backed, but two captures of the same character still differ "
            "by that offset, so comparison continues to need alignment."
        ),
        "vfsRootNote": (
            "chr_0035_liino ships in the Persistent VFS, not StreamingAssets. "
            "Scanning only the StreamingAssets asset map drops it silently and "
            "yields 30 characters instead of 31."
        ),
        "warning": (
            "Do not enumerate the camera set from CharacterDisplayConfig. Its "
            "CharacterDisplayData entries are SerializeReference and are recorded "
            "unparsed; 15 of 33 yield no string hints, so counting camera groups "
            "there undercounts. Use the asset map."
        ),
        "characterCount": len(characters),
        "characters": characters,
        # Flat form for Unity's JsonUtility, which cannot read dictionaries.
        "entries": [
            {
                "templateId": template,
                "actor": entry["actor"],
                "track": entry["track"],
                "vcamPosition": entry["vcamOverview"]["localPosition"],
                "vcamRotation": entry["vcamOverview"]["localRotation"],
                "lookAtPosition": entry["lookAtOverview"]["localPosition"],
                "fieldOfView": entry["lens"]["fieldOfView"],
                "nearClipPlane": entry["lens"]["nearClipPlane"],
                "farClipPlane": entry["lens"]["farClipPlane"],
            }
            for template, entry in sorted(characters.items())
        ],
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-root", default=DEFAULT_EXTRACT_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        contract = build(args.extract_root)
    except CameraContractError as error:
        print(f"camera contract failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        if not os.path.isfile(CONTRACT_PATH):
            print(f"missing contract: {CONTRACT_PATH}", file=sys.stderr)
            return 2
        existing = json.load(io.open(CONTRACT_PATH, encoding="utf-8"))
        if existing != contract:
            print("contract differs from the extracted prefabs", file=sys.stderr)
            return 1
        print(f"overview camera contract matches: {contract['characterCount']} characters")
        return 0

    os.makedirs(os.path.dirname(CONTRACT_PATH), exist_ok=True)
    with io.open(CONTRACT_PATH, "w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    print(f"wrote {os.path.relpath(CONTRACT_PATH, PROJECT_ROOT)}")
    print(f"  characters: {contract['characterCount']}")
    print(f"  self-check: Wulfa reproduces the independently recovered values")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
