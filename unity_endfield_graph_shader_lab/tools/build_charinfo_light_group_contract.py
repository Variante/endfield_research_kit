"""Recover the per-character CharInfo additional light groups from source prefabs.

`PhaseCharInfo._RefreshCharModelAddon` instantiates
`charDisplayData.charInfoLightGroup` alongside the camera track, resolving to
`gameplay/prefabs/charinfo/additionallights/light_chr_<template>.prefab`. Each
group is a dedicated rig of 41 to 67 lights with named roles: `RimLight_*`,
`SpecLight_*`, `FogLight_*`, `FloorLight`, and `Point Light_overview`.

Every character has one, so a shading comparison against a reference capture is
only valid once the matching group is applied; the lab's default rig is not a
substitute.

Lights are organised by Character Info tab under nodes named `light_overview`,
`light_document`, `light_weapon` and so on. That parent decides the tab, not the
light's own name: a light called `Point Light_overview` can sit under
`light_document`. Every Light component serialises `m_Enabled = 1`, so the tab
node's active state is what selects them.

Usage:
    python tools/build_charinfo_light_group_contract.py --extract-root <dir>
    python tools/build_charinfo_light_group_contract.py --check
"""

from __future__ import annotations

import argparse
import collections
import glob
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
    "charinfo_light_group_contract.json",
)
DEFAULT_EXTRACT_ROOT = os.path.join(
    PROJECT_ROOT,
    "scratch",
    "character_recovery",
    "gameplay_reference",
    "charinfo_prefabs",
)
OPERATOR_LIGHTS_PATH = os.path.join(
    PROJECT_ROOT,
    "Assets",
    "EndfieldGraphShaderLab",
    "Generated",
    "OriginalData",
    "RenderParameters",
    "operator_lights.json",
)
# operator_lights.json keys chr_0003_endmin as "endminf"; same root, same lights.
OPERATOR_LIGHTS_ALIASES = {"endmin": "endminf"}
PATH_ID_SUFFIX = re.compile(r"_p([0-9A-Fa-f]{16})\.json$")


class LightContractError(RuntimeError):
    """Fail-closed recovery error."""


def _path_id(filename: str) -> int | None:
    match = PATH_ID_SUFFIX.search(filename)
    if match is None:
        return None
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def _vector(value):
    if not value:
        return None
    return [float(value["X"]), float(value["Y"]), float(value["Z"])]


def _quaternion(value):
    if not value:
        return None
    return [float(value["X"]), float(value["Y"]), float(value["Z"]), float(value["W"])]


def collect(extract_root: str) -> dict:
    groups: dict[str, list] = collections.defaultdict(list)
    index = 0
    while True:
        tgroup = os.path.join(extract_root, f"out_{index}")
        lgroup = os.path.join(extract_root, f"lights_{index}")
        if not os.path.isdir(tgroup):
            break
        index += 1
        if not os.path.isdir(lgroup):
            continue

        transforms: dict[int, dict] = {}
        by_gameobject: dict[int, int] = {}
        for path in glob.glob(os.path.join(tgroup, "Transform", "*.json")):
            pid = _path_id(path)
            if pid is None:
                continue
            data = json.load(io.open(path, encoding="utf-8"))
            owner = data.get("m_GameObject") or {}
            transforms[pid] = {
                "name": owner.get("Name") or "",
                "father": (data.get("m_Father") or {}).get("m_PathID"),
                "position": data.get("m_LocalPosition"),
                "rotation": data.get("m_LocalRotation"),
            }
            by_gameobject[owner.get("m_PathID")] = pid

        def owning_group(pid: int) -> tuple[str | None, str | None]:
            """Return (group root, tab node) for a light transform.

            Lights are organised by Character Info tab under nodes named
            light_overview, light_document, light_weapon and so on, so the tab
            is the child of the group root on the way up.
            """
            seen: set[int] = set()
            tab = None
            while pid and pid not in seen:
                seen.add(pid)
                node = transforms.get(pid)
                if node is None:
                    return None, None
                name = node["name"]
                if name.startswith("light_chr_"):
                    return name, tab
                if name.startswith("light_"):
                    tab = name
                pid = node["father"]
            return None, None

        for path in glob.glob(os.path.join(lgroup, "Light", "*.json")):
            data = json.load(io.open(path, encoding="utf-8"))
            gid = (data.get("m_GameObject") or {}).get("m_PathID")
            tpid = by_gameobject.get(gid)
            if tpid is None:
                continue
            root, tab = owning_group(tpid)
            if not root:
                continue
            node = transforms[tpid]
            colour = data.get("m_Color") or {}
            groups[root].append({
                "name": node["name"],
                "tab": tab,
                "enabled": data.get("m_Enabled"),
                "type": data.get("m_Type"),
                "shape": data.get("m_Shape"),
                "intensity": data.get("m_Intensity"),
                "range": data.get("m_Range"),
                "spotAngle": data.get("m_SpotAngle"),
                "color": [colour.get("r"), colour.get("g"), colour.get("b"), colour.get("a")],
                "cullingMask": (data.get("m_CullingMask") or {}).get("m_Bits"),
                "localPosition": _vector(node["position"]),
                "localRotation": _quaternion(node["rotation"]),
            })
    return groups


def cross_check_operator_lights(characters: dict) -> dict:
    """Verify each light_overview set against the independently recovered rig.

    RenderParameters/operator_lights.json was built from installed-game
    Light/HGAdditionalLightData JSON and is what actually applies these lights
    in the lab. If the tab grouping recovered here is right, the two must agree
    light for light, so any disagreement means one of them has drifted.
    """
    if not os.path.isfile(OPERATOR_LIGHTS_PATH):
        raise LightContractError(
            f"operator_lights.json is missing: {OPERATOR_LIGHTS_PATH}"
        )
    actors = json.load(io.open(OPERATOR_LIGHTS_PATH, encoding="utf-8"))["actors"]

    by_actor = {}
    for entry in characters.values():
        actor = entry["actor"]
        by_actor[OPERATOR_LIGHTS_ALIASES.get(actor, actor)] = entry

    def signature(light):
        return (light["name"], round(float(light["intensity"] or 0.0), 6))

    for actor in sorted(actors):
        entry = by_actor.get(actor)
        if entry is None:
            raise LightContractError(
                f"operator_lights.json has {actor} but no light group was "
                "extracted for it. If it is a Persistent-VFS character, the "
                "StreamingAssets asset map alone will not reach it."
            )
        overview = sorted(
            signature(light)
            for light in entry["lights"]
            if light["tab"] == "light_overview"
        )
        expected = sorted(signature(light) for light in actors[actor]["lights"])
        if overview != expected:
            raise LightContractError(
                f"{actor}: light_overview set ({len(overview)}) disagrees with "
                f"operator_lights.json ({len(expected)})"
            )

    return {
        "source": "Generated/OriginalData/RenderParameters/operator_lights.json",
        "actorsChecked": len(actors),
        "result": (
            "Every light_overview set reproduces the corresponding actor, which "
            "is what ties the recovered tab grouping to the rig the lab already "
            "applies."
        ),
    }


def build(extract_root: str) -> dict:
    groups = collect(extract_root)
    if not groups:
        raise LightContractError(f"no light groups found under {extract_root}")

    characters = {}
    total = 0
    enabled = 0
    overview_named = 0
    for root in sorted(groups):
        lights = sorted(
            groups[root],
            key=lambda item: (item["tab"] or "", item["name"], item["intensity"] or 0),
        )
        by_tab = collections.Counter(item["tab"] or "(none)" for item in lights)
        total += len(lights)
        enabled += sum(1 for item in lights if item["enabled"])
        overview_named += sum(1 for item in lights if "overview" in (item["name"] or "").lower())
        template = root[len("light_") :]
        characters[template] = {
            "group": root,
            "actor": template.split("_", 2)[-1],
            "lightCount": len(lights),
            "lightsByTab": dict(sorted(by_tab.items())),
            "overviewLightCount": by_tab.get("light_overview", 0),
            "lights": lights,
        }

    cross_check = cross_check_operator_lights(characters)

    return {
        "schema": "endfield.charinfo.light-group.v1",
        "boundary": "source_closed_rig_with_tab_grouping",
        "source": {
            "lua": "Lua/Data/LuaScripts/Phase/CharInfo/PhaseCharInfo.lua",
            "luaFunction": "PhaseCharInfo._RefreshCharModelAddon",
            "field": "charDisplayData.charInfoLightGroup",
            "prefabRoot": (
                "assets/beyond/dynamicassets/gameplay/prefabs/charinfo/additionallights/"
            ),
        },
        "totals": {
            "groups": len(characters),
            "lights": total,
            "componentEnabled": enabled,
            "overviewNamed": overview_named,
        },
        "groupCountNote": (
            "32 light groups against 31 camera tracks. The extra is "
            "light_chr_0024_qianneng, whose 51 lights all sit under a single "
            "light_qianneng node rather than the Character Info tab set, so it "
            "belongs to the potential screen rather than to a roster character's "
            "overview."
        ),
        "vfsRootNote": (
            "chr_0035_liino ships in the Persistent VFS, not StreamingAssets, so "
            "scanning only the StreamingAssets asset map silently drops it. Both "
            "maps have to be walked to reach the full roster."
        ),
        "operatorLightsCrossCheck": cross_check,
        "operatorLightsCrossCheckNote": (
            "Every light_overview set reproduces the corresponding actor in "
            "RenderParameters/operator_lights.json, which was recovered "
            "independently from installed-game Light/HGAdditionalLightData JSON. "
            "That file already applies these lights in the lab, so this contract "
            "documents and verifies the rig rather than supplying new wiring. "
            "operator_lights keys chr_0003_endmin as 'endminf'; same root, same "
            "12 lights."
        ),
        "tabSelection": (
            "Lights are organised by Character Info tab under nodes named "
            "light_overview, light_document, light_weapon and so on, recorded per "
            "light as 'tab'. That parent, not the light's own name, decides the "
            "tab: a light called 'Point Light_overview' can sit under "
            "light_document. Every Light component serialises m_Enabled = 1, so "
            "the tab node's active state is what selects them."
        ),
        "consequence": (
            "A shading comparison against a reference capture is only valid once "
            "the character's own group is applied. The lab's default rig is not a "
            "substitute, and any per-character delta measured without it mixes "
            "lighting error into the material result."
        ),
        "characters": characters,
    }


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--extract-root", default=DEFAULT_EXTRACT_ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        contract = build(args.extract_root)
    except LightContractError as error:
        print(f"light contract failed: {error}", file=sys.stderr)
        return 2

    if args.check:
        if not os.path.isfile(CONTRACT_PATH):
            print(f"missing contract: {CONTRACT_PATH}", file=sys.stderr)
            return 2
        existing = json.load(io.open(CONTRACT_PATH, encoding="utf-8"))
        if existing != contract:
            print("contract differs from the extracted prefabs", file=sys.stderr)
            return 1
        print(f"light group contract matches: {contract['totals']['groups']} groups")
        return 0

    os.makedirs(os.path.dirname(CONTRACT_PATH), exist_ok=True)
    with io.open(CONTRACT_PATH, "w", encoding="utf-8") as handle:
        json.dump(contract, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    totals = contract["totals"]
    print(f"wrote {os.path.relpath(CONTRACT_PATH, PROJECT_ROOT)}")
    print(f"  groups {totals['groups']}, lights {totals['lights']}, "
          f"component-enabled {totals['componentEnabled']}, "
          f"overview-named {totals['overviewNamed']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
