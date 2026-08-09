#!/usr/bin/env python3
"""Audit the installed Zhuangfy gacha authored-light population boundary."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
GAME_ASSEMBLY = GAME_ROOT / "GameAssembly.dll"
GLOBAL_METADATA = GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
ROOM_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/7064D8E2/"
    "8B805A424FFA2FC7F4DE0BC016C09009.chk"
)
CHARINFO_CHUNK = (
    GAME_ROOT
    / "Endfield_Data/StreamingAssets/VFS/7064D8E2/"
    "62EB15DCD74A3348E244B9B068AB9694.chk"
)
LUA_SOURCE = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/lua_dump/Lua/Data/LuaScripts/"
    "UI/Panels/GachaChar/GachaCharCtrl.lua"
)
CHARACTER_TABLE = (
    REPO_ROOT / "export_full/structured/StreamingAssets/Table/CharacterTable.json"
)
GACHA_CHAR_TABLE = (
    REPO_ROOT / "export_full/structured/StreamingAssets/Table/GachaCharInfoTable.json"
)
ROOM_HIERARCHY = (
    REPO_ROOT
    / "scratch/animestudio/zhuangfy_gacha_room_lights/room_light_hierarchy.json"
)
ROOM_LIGHT_ROOT = (
    REPO_ROOT / "scratch/animestudio/zhuangfy_gacha_room_lights/json/Light"
)
CHAR_JSON_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/character_light_json"
)
CHAR_DUMP_ROOT = (
    REPO_ROOT
    / "scratch/animestudio/gacha_light_population/character_light_dump"
)
OPERATOR_LIGHTS = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "RenderParameters/operator_lights.json"
)
NATIVE_CULL_REPORT = (
    REPO_ROOT
    / "scratch/reverse_engineering/clustered_light_native_culling/report.json"
)
GACHA_CULL_VIEW_AUDIT = (
    REPO_ROOT / "scratch/reverse_engineering/gacha_light_cull_view/audit.json"
)
GACHA_SELECTED_LIST_AUDIT = (
    REPO_ROOT / "scratch/reverse_engineering/gacha_light_selected_list/audit.json"
)
OUTPUT = (
    LAB_ROOT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
    "CharInfoPresentation/gacha_light_population_recovery.json"
)

EXPECTED_HASHES = {
    "gameAssembly": "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce",
    "globalMetadata": "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e",
    "roomChunk": "4b4ae868dc333fd5b22fc30e667d3156675178bfffd57b93e0e4b625c89f0b26",
    "charInfoChunk": "db94219ee4f522a824c32ec979c2dc5bfd7b1013b4e45c18b77fb3ae4809694e",
    "gachaLua": "94815321515ebf7d4067f60f2f6e2a1d25611bc2e40f712e22cd40a6d159ae19",
    "characterTable": "50392af8d8c93854b99e5342b4b70c049b68d2da306e366325d749ba77bf4779",
    "gachaCharTable": "05c1b414bab1f3fbb7a9a983c7193c40ccf0884d6cb50edf7469d8ee05dd50fb",
    "roomHierarchy": "bf26b44919a7563bd6c7ee137346d7f8880bb1a32911a8972c586b2bb0c87db9",
    "operatorLights": "706f66b89aa209371df50956e9f1525026ce4a8a1f19a85210fc35d3b2c23ac8",
    "nativeCullReport": "f7b6e9b6407bb26555491c13f9895b712a9219218c19ac07efd56d7c947d7d7e",
    "gachaCullViewAudit": "4717ddd564f0eee2e1742024660e233e09865b4a301a4b7566aaca6844011dc4",
    "gachaSelectedListAudit": "7b3624526a77102fb075cdc1ad98277eb6746b5a1853faa1fd2ad2032951e1b3",
}

ROOM_SURVIVOR_SUBSEQUENCE = [
    "Spot Light (12)",
    "Spot Light (19)",
    "Linear Light (12)",
    "Linear Light (13)",
    "Linear Light (14)",
    "Spot Light (17)",
    "Linear Light (15)",
    "Spot Light (18)",
    "Spot Light (9)",
    "Spot Light (11)",
    "Spot Light (10)",
]

NATIVE_METHODS = {
    "CharUIModelMono.InitLightFollower": {
        "methodIndex": 49713,
        "virtualAddress": "0x186C25FA0",
        "fileOffset": 0x6C245A0,
        "sizeBytes": 220,
        "sha256": "9259bd577548c38e5eb44b1c6b02d5379a448048d888ff646a866a398d7cb4a1",
    },
    "CharUIModelMono._GetFollowableNode": {
        "methodIndex": 49714,
        "virtualAddress": "0x186C29FD0",
        "fileOffset": 0x6C285D0,
        "sizeBytes": 116,
        "sha256": "c0f00babeb5c1f6d717788a099c5cfc6d824a0e633149b1805f16e7e15ef817f",
    },
    "CharInfoLightFollower.InitCharLightFollower": {
        "methodIndex": 16388,
        "virtualAddress": "0x1872ECF0C",
        "fileOffset": 0x72EB50C,
        "sizeBytes": 220,
        "sha256": "fd263394528933a30655f5a52b42c790dbce0f91ed2475619a01ccff25f80379",
    },
    "CharInfoLightFollower.LateTick": {
        "methodIndex": 16387,
        "virtualAddress": "0x1872ECFE8",
        "fileOffset": 0x72EB5E8,
        "sizeBytes": 188,
        "sha256": "d274f9b13d6f0275e4791bee11ba6a34980fc30391dfcfbe6f12369e57707bd8",
    },
    "CharInfoLightFollower._FollowWithFixedOffset": {
        "methodIndex": 16389,
        "virtualAddress": "0x1872ED108",
        "fileOffset": 0x72EB708,
        "sizeBytes": 264,
        "sha256": "0eaa0ce1b9c6aa70feb71d85175be340ab7598bbfa1d4ba05644b252297cbc12",
    },
    "CharInfoLightFollower._FollowWithParent": {
        "methodIndex": 16390,
        "virtualAddress": "0x1872ED210",
        "fileOffset": 0x72EB810,
        "sizeBytes": 504,
        "sha256": "27fdafe4771dd013713e4ae37a2132e102e949a47f0047843d48d6092c01821d",
    },
}

EXPECTED_GROUPS = {
    "light_document": (114660774365865291, True, 6, 4, 6, {"0": 2, "2": 4}),
    "light_equip": (-4122620703443081909, False, 6, 1, 6, {"0": 2, "2": 4}),
    "light_overview": (-1840922393885432501, False, 6, 4, 6, {"0": 2, "2": 4}),
    "light_skill": (-736313027726760629, False, 8, 0, 7, {"0": 3, "2": 5}),
    "light_upgrade": (7162434402683692363, False, 7, 5, 7, {"0": 2, "2": 5}),
    "light_weapon": (-2373901316435892917, False, 11, 0, 11, {"0": 1, "2": 10}),
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object, source: Path | str) -> None:
    if actual != expected:
        raise AssertionError(
            "Gacha light-population audit failed: "
            f"validator=gacha_light_population; check={check}; source={source}; "
            f"expected={expected!r}; actual={actual!r}"
        )


def verified_hash(name: str, path: Path) -> dict[str, object]:
    require(f"{name}_exists", path.is_file(), True, path)
    actual = sha256(path)
    require(f"{name}_sha256", actual, EXPECTED_HASHES[name], path)
    return {"sizeBytes": path.stat().st_size, "sha256": actual}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validate_lua_contract(text: str, source: Path | str) -> dict[str, object]:
    compact = re.sub(r"\s+", " ", text)
    checks = {
        "characterLightPath": (
            r'LoadGameObject\(string\.format\("Assets/Beyond/DynamicAssets/Gameplay/'
            r'Prefabs/CharInfo/AdditionalLights/light_%s\.prefab", charId\)\)'
        ),
        "overviewSelector": r'local isTarget = childTrans\.name == "light_overview"',
        "childActivation": r"childTrans\.gameObject:SetActive\(isTarget\)",
        "followerInitialization": r"uiModelMono:InitLightFollower\(childTrans\)",
        "rarity6": r"sceneLight6Rarity\.gameObject:SetActive\(rarity >= 6\)",
        "rarity5": r"sceneLight5Rarity\.gameObject:SetActive\(rarity == 5\)",
        "rarity4": r"sceneLight4Rarity\.gameObject:SetActive\(rarity <= 4\)",
    }
    for name, pattern in checks.items():
        require(f"lua_{name}", bool(re.search(pattern, compact)), True, source)
    selector_block = re.search(
        r'local isTarget = childTrans\.name == "light_overview" '
        r"childTrans\.gameObject:SetActive\(isTarget\) if isTarget then "
        r"uiModelMono:InitLightFollower\(childTrans\) end",
        compact,
    )
    require("lua_selector_block_order", bool(selector_block), True, source)
    return {
        "characterLightPrefabEquation": (
            "Assets/Beyond/DynamicAssets/Gameplay/Prefabs/CharInfo/"
            "AdditionalLights/light_<charId>.prefab"
        ),
        "selectedChild": "light_overview",
        "otherDirectChildrenActive": False,
        "selectedChildActive": True,
        "initLightFollowerOnSelectedChild": True,
        "roomRarityRules": {
            "SceneLight6Rarity": "rarity >= 6",
            "SceneLight5Rarity": "rarity == 5",
            "SceneLight4Rarity": "rarity <= 4",
        },
    }


def path_id_from_name(path: Path) -> int:
    match = re.search(r"_p([0-9A-Fa-f]{16})\.", path.name)
    if not match:
        raise AssertionError(
            "Gacha light-population audit failed: "
            f"validator=gacha_light_population; check=path_id_suffix; source={path}; "
            "expected='16 hexadecimal digits'; actual='missing'"
        )
    value = int(match.group(1), 16)
    return value - (1 << 64) if value >= (1 << 63) else value


def load_folder(root: Path, name: str) -> dict[int, tuple[Path, dict[str, Any]]]:
    result = {}
    for path in sorted((root / name).glob("*.json")):
        result[path_id_from_name(path)] = (path, load_json(path))
    return result


def read_active_self(path: Path) -> bool:
    match = re.search(
        r"^\s*bool m_IsActive = (True|False)\s*$",
        path.read_text(encoding="utf-8-sig"),
        re.M,
    )
    require("game_object_active_self_present", bool(match), True, path)
    return match.group(1) == "True" if match else False


def analyze_character_prefab(
    json_root: Path, dump_root: Path
) -> tuple[dict[str, object], list[dict[str, object]]]:
    game_objects = load_folder(json_root, "GameObject")
    transforms = load_folder(json_root, "Transform")
    lights = load_folder(json_root, "Light")
    behaviours = load_folder(json_root, "MonoBehaviour")
    require("character_game_object_count", len(game_objects), 51, json_root)
    require("character_transform_count", len(transforms), 51, json_root)
    require("character_light_count", len(lights), 44, json_root)
    require("character_behaviour_count", len(behaviours), 65, json_root)

    go_by_transform = {
        transform_id: int(data["m_GameObject"]["m_PathID"])
        for transform_id, (_, data) in transforms.items()
    }
    parent_by_go = {}
    for transform_id, (_, data) in transforms.items():
        go_id = go_by_transform[transform_id]
        parent_by_go[go_id] = go_by_transform.get(int(data["m_Father"]["m_PathID"]))
    name_by_go = {go_id: data["m_Name"] for go_id, (_, data) in game_objects.items()}
    active_by_go = {}
    for go_id, (path, _) in game_objects.items():
        active_by_go[go_id] = read_active_self(
            dump_root / "GameObject" / path.with_suffix(".txt").name
        )

    def lineage(go_id: int) -> list[int]:
        result = []
        seen = set()
        while go_id is not None:
            require("character_transform_cycle", go_id in seen, False, json_root)
            seen.add(go_id)
            result.append(go_id)
            go_id = parent_by_go.get(go_id)
        return result

    def group_for(go_id: int) -> str:
        for ancestor in lineage(go_id):
            name = name_by_go[ancestor]
            if name.startswith("light_") and name != "light_chr_0030_zhuangfy":
                return name
        return "<root>"

    behaviour_by_go: dict[int, list[dict[str, Any]]] = defaultdict(list)
    behaviour_counts = Counter()
    for _, (_, data) in behaviours.items():
        fields = data["$animestudio"]["typeTreeFieldPaths"]
        if "followType:int" in fields:
            kind = "CharInfoLightFollower"
        elif "m_LightCharacterOnly:UInt8" in fields:
            kind = "HGLightExtension"
        else:
            kind = "other"
        behaviour_counts[kind] += 1
        behaviour_by_go[int(data["m_GameObject"]["m_PathID"])].append(
            {"kind": kind, "data": data}
        )
    require(
        "character_behaviour_kinds",
        dict(behaviour_counts),
        {"CharInfoLightFollower": 14, "HGLightExtension": 44, "other": 7},
        json_root,
    )

    group_counts: dict[str, Counter] = defaultdict(Counter)
    rows = []
    for light_id, (path, data) in lights.items():
        go_id = int(data["m_GameObject"]["m_PathID"])
        group = group_for(go_id)
        followers = [x for x in behaviour_by_go[go_id] if x["kind"] == "CharInfoLightFollower"]
        extensions = [x for x in behaviour_by_go[go_id] if x["kind"] == "HGLightExtension"]
        require("single_light_extension", len(extensions), 1, path)
        character_only = bool(extensions[0]["data"]["m_LightCharacterOnly"])
        row = {
            "pathId": light_id,
            "name": name_by_go[go_id],
            "group": group,
            "type": int(data["m_Type"]),
            "enabled": bool(data["m_Enabled"]),
            "cookiePathId": int(data["m_Cookie"]["m_PathID"]),
            "priority": int(data["m_LightPriority"]),
            "characterOnly": character_only,
            "hasFollower": bool(followers),
        }
        rows.append(row)
        counts = group_counts[group]
        counts["lights"] += 1
        counts["enabled"] += row["enabled"]
        counts["followers"] += row["hasFollower"]
        counts["characterOnly"] += character_only
        counts[f"type_{row['type']}"] += 1

    groups = []
    for name, expected in EXPECTED_GROUPS.items():
        group_ids = [go_id for go_id, go_name in name_by_go.items() if go_name == name]
        require(f"{name}_unique", len(group_ids), 1, json_root)
        group_id = group_ids[0]
        counts = group_counts[name]
        actual = (
            group_id,
            active_by_go[group_id],
            counts["lights"],
            counts["followers"],
            counts["characterOnly"],
            {key.removeprefix("type_"): value for key, value in counts.items() if key.startswith("type_")},
        )
        require(f"{name}_contract", actual, expected, json_root)
        require(f"{name}_enabled", counts["enabled"], counts["lights"], json_root)
        groups.append(
            {
                "name": name,
                "pathId": group_id,
                "serializedActiveSelf": active_by_go[group_id],
                "lightCount": counts["lights"],
                "followerCount": counts["followers"],
                "characterOnlyCount": counts["characterOnly"],
                "typeCounts": actual[-1],
            }
        )
    require("character_groups_only", set(group_counts), set(EXPECTED_GROUPS), json_root)
    selected = sorted(
        (row for row in rows if row["group"] == "light_overview"),
        key=lambda row: row["pathId"],
    )
    return {
        "root": "light_chr_0030_zhuangfy",
        "totalLightCount": len(lights),
        "groups": groups,
    }, selected


def validate_room_population(
    hierarchy: dict[str, Any], light_root: Path
) -> list[dict[str, object]]:
    require("room_light_count", int(hierarchy["lightCount"]), 34, ROOM_HIERARCHY)
    require(
        "room_rarity_counts",
        hierarchy["rarityCounts"],
        {"SceneLight4Rarity": 11, "SceneLight5Rarity": 11, "SceneLight6Rarity": 12},
        ROOM_HIERARCHY,
    )
    selected = [row for row in hierarchy["lights"] if row["rarityGroup"] == "SceneLight6Rarity"]
    require("room_selected_count", len(selected), 12, ROOM_HIERARCHY)
    rows = []
    for row in selected:
        path_id = int(row["lightPathId"])
        path_hex = f"{path_id & ((1 << 64) - 1):016X}"
        matches = list(light_root.glob(f"*p{path_hex}.json"))
        require(f"room_light_{path_hex}_file_count", len(matches), 1, light_root)
        path = matches[0]
        data = load_json(path)
        require(f"room_light_{path_hex}_enabled", bool(data["m_Enabled"]), True, path)
        require(f"room_light_{path_hex}_layer", int(data["m_RenderingLayerMask"]), 1, path)
        require(f"room_light_{path_hex}_cookie", int(data["m_Cookie"]["m_PathID"]), 0, path)
        require(
            f"room_light_{path_hex}_shadow",
            int(data["m_Shadows"]["m_PlatformSpecificType"]["defaultParam"]),
            0,
            path,
        )
        rows.append(
            {
                "pathId": path_id,
                "name": row["name"],
                "type": int(data["m_Type"]),
                "priority": int(data["m_LightPriority"]),
                "enabled": True,
                "renderingLayerMask": 1,
                "cookiePathId": 0,
                "shadowType": 0,
                "sourceRawSha256": data["$animestudio"]["rawDataSha256"],
            }
        )
    require("room_selected_type_counts", Counter(row["type"] for row in rows), Counter({2: 11, 0: 1}), light_root)
    return sorted(rows, key=lambda row: row["pathId"])


def validate_operator_population(
    payload: dict[str, Any], prefab_rows: list[dict[str, object]]
) -> list[dict[str, object]]:
    actor = payload["actors"]["zhuangfy"]
    require("operator_group", actor["group_name"], "light_overview", OPERATOR_LIGHTS)
    require("operator_root", actor["root_name"], "light_chr_0030_zhuangfy", OPERATOR_LIGHTS)
    require("operator_light_count", int(actor["count"]), 6, OPERATOR_LIGHTS)
    rows = []
    for row in actor["lights"]:
        rows.append(
            {
                "pathId": int(row["light_path_id"]),
                "name": row["name"],
                "type": int(row["light_type"]),
                "priority": int(row["priority"]),
                "enabled": bool(row["enabled"]),
                "cookiePathId": int(row["cookie_path_id"]),
                "shadowType": int(row["shadow_type"]),
                "characterOnly": bool(row["character_only"]),
                "hasFollower": row["follower"] is not None,
            }
        )
    require("operator_all_enabled", all(row["enabled"] for row in rows), True, OPERATOR_LIGHTS)
    require("operator_all_character_only", all(row["characterOnly"] for row in rows), True, OPERATOR_LIGHTS)
    require("operator_cookie_count", sum(bool(row["cookiePathId"]) for row in rows), 0, OPERATOR_LIGHTS)
    require("operator_shadow_count", sum(bool(row["shadowType"]) for row in rows), 1, OPERATOR_LIGHTS)
    require("operator_follower_count", sum(row["hasFollower"] for row in rows), 4, OPERATOR_LIGHTS)
    prefab_membership = [(row["pathId"], row["name"], row["type"]) for row in prefab_rows]
    operator_membership = sorted((row["pathId"], row["name"], row["type"]) for row in rows)
    require("operator_prefab_membership", operator_membership, prefab_membership, OPERATOR_LIGHTS)
    return rows


def validate_native_methods(game_assembly: Path) -> list[dict[str, object]]:
    data = game_assembly.read_bytes()
    rows = []
    for name, spec in NATIVE_METHODS.items():
        offset = int(spec["fileOffset"])
        size = int(spec["sizeBytes"])
        actual = hashlib.sha256(data[offset : offset + size]).hexdigest()
        require(f"native_{name}_sha256", actual, spec["sha256"], game_assembly)
        rows.append({"method": name, **spec})
    return rows


def validate_native_cull_boundary(
    native: dict[str, Any],
    view: dict[str, Any],
    selected: dict[str, Any],
    room_rows: list[dict[str, object]],
) -> dict[str, object]:
    require(
        "native_cull_status",
        native["status"],
        "native candidate producer substantially source-closed; scheduled generic cull-view internals remain bounded open",
        NATIVE_CULL_REPORT,
    )
    require(
        "normal_path_fallback",
        view["nativeProof"]["fallbackMode"][
            "useFallbackLightCullingOnSourceClosedShippedRoute"
        ],
        False,
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "gacha_occlusion_dimensions",
        view["nativeProof"]["occlusion"]["addCullViewDimensions"],
        [0, 0],
        GACHA_CULL_VIEW_AUDIT,
    )
    strongest = view["strongestExactOutput"]
    require(
        "room_native_maximum",
        int(strongest["authoredRoomMaximumContributionCount"]),
        11,
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "room_exact_exclusion",
        strongest["excludedAuthoredRoomRows"],
        ["Spot Light (20)"],
        GACHA_CULL_VIEW_AUDIT,
    )
    require(
        "room_survivor_subsequence",
        strongest["remainingAuthoredRoomOrderIsExactSubsequenceOf"],
        ROOM_SURVIVOR_SUBSEQUENCE,
        GACHA_CULL_VIEW_AUDIT,
    )
    selected_output = selected["strongestExactOutput"]
    require(
        "selected_generic_gate",
        selected_output["genericFlagMaskGateClosedForAll12"],
        True,
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "selected_exact_exclusion",
        selected_output["guaranteedAbsent"],
        ["Spot Light (20)"],
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "selected_survivor_subsequence",
        selected_output["remainingStrictRelativeOrderIfAdmitted"],
        ROOM_SURVIVOR_SUBSEQUENCE,
        GACHA_SELECTED_LIST_AUDIT,
    )
    require(
        "room_excluded_row_membership",
        "Spot Light (20)" in {row["name"] for row in room_rows},
        True,
        ROOM_HIERARCHY,
    )
    for source, audit in (
        (GACHA_CULL_VIEW_AUDIT, view),
        (GACHA_SELECTED_LIST_AUDIT, selected),
    ):
        require(
            f"{source.parent.name}_offline_only",
            set(audit["noRuntimeLaunches"].values()),
            {False},
            source,
        )
    return {
        "shippedCandidateCore": "normal; useFallbackLightCulling=false",
        "gachaOcclusionDimensions": [0, 0],
        "gachaOcclusionActive": False,
        "genericFlagMaskGateClosedForAll12RoomLights": True,
        "guaranteedAbsentRoomLights": ["Spot Light (20)"],
        "authoredRoomMaximumContributionCount": 11,
        "knownAuthoredSurvivorUpperBound": 17,
        "remainingRoomOrderIfAdmitted": ROOM_SURVIVOR_SUBSEQUENCE,
        "nativeOutputOrder": (
            "accepted non-directionals sort by ascending camera distance squared; "
            "SetupState then sorts types 0/2 by priority descending and distance ascending"
        ),
        "firstOpenRoomBoundary": (
            "the synchronous AABB/plane result for the other eleven room rows depends "
            "on live horizontal planes derived from final render-target aspect"
        ),
    }


def build_report(*, verify_hashes: bool = True) -> dict[str, object]:
    source_paths = {
        "gameAssembly": GAME_ASSEMBLY,
        "globalMetadata": GLOBAL_METADATA,
        "roomChunk": ROOM_CHUNK,
        "charInfoChunk": CHARINFO_CHUNK,
        "gachaLua": LUA_SOURCE,
        "characterTable": CHARACTER_TABLE,
        "gachaCharTable": GACHA_CHAR_TABLE,
        "roomHierarchy": ROOM_HIERARCHY,
        "operatorLights": OPERATOR_LIGHTS,
        "nativeCullReport": NATIVE_CULL_REPORT,
        "gachaCullViewAudit": GACHA_CULL_VIEW_AUDIT,
        "gachaSelectedListAudit": GACHA_SELECTED_LIST_AUDIT,
    }
    source_hashes = (
        {name: verified_hash(name, path) for name, path in source_paths.items()}
        if verify_hashes
        else {}
    )
    lua_contract = validate_lua_contract(
        LUA_SOURCE.read_text(encoding="utf-8-sig"), LUA_SOURCE
    )
    character_table = load_json(CHARACTER_TABLE)
    gacha_table = load_json(GACHA_CHAR_TABLE)
    character_row = character_table["chr_0030_zhuangfy"]
    gacha_row = gacha_table["chr_0030_zhuangfy"]
    require("zhuangfy_rarity", int(character_row["rarity"]), 6, CHARACTER_TABLE)
    require("zhuangfy_timeline", gacha_row["timelineAssetName"], "gacha_char_zhuangfy", GACHA_CHAR_TABLE)

    prefab, prefab_rows = analyze_character_prefab(CHAR_JSON_ROOT, CHAR_DUMP_ROOT)
    operator_rows = validate_operator_population(load_json(OPERATOR_LIGHTS), prefab_rows)
    room_rows = validate_room_population(load_json(ROOM_HIERARCHY), ROOM_LIGHT_ROOT)
    native_rows = validate_native_methods(GAME_ASSEMBLY)
    native_cull_boundary = validate_native_cull_boundary(
        load_json(NATIVE_CULL_REPORT),
        load_json(GACHA_CULL_VIEW_AUDIT),
        load_json(GACHA_SELECTED_LIST_AUDIT),
        room_rows,
    )
    union = room_rows + operator_rows
    type_counts = Counter(row["type"] for row in union)
    require("authored_union_count", len(union), 18, "room + character overview")
    require("authored_union_types", type_counts, Counter({2: 15, 0: 3}), "room + character overview")
    require("authored_union_cookie_count", sum(bool(row["cookiePathId"]) for row in union), 0, "room + character overview")

    return {
        "schema": "endfield.gacha-light-population-recovery.v2",
        "status": "zhuangfy_gacha_authored_population_and_first_native_exclusion_source_closed",
        "runtimeReady": False,
        "outcome": (
            "Installed Lua selects only light_overview from light_chr_0030_zhuangfy, "
            "initializes its four CharInfoLightFollower components, and selects the "
            "12-light SceneLight6Rarity room group for rarity 6. The resulting known "
            "serialized Unity-Light candidate union is exactly 18 enabled lights: "
            "3 type 0 and 15 type 2, with no authored cookies and one character-light "
            "shadow request. The shipped normal native path disables fallback and Gacha "
            "occlusion; Spot Light (20) is aspect-independently rejected, tightening the "
            "known authored survivor upper bound to 17. This still does not close the "
            "target-frame LightCullResult, dynamic/custom lights, final order, or lightCount."
        ),
        "installedInputs": source_hashes,
        "selection": {
            "characterId": "chr_0030_zhuangfy",
            "rarity": 6,
            "timelineAssetName": "gacha_char_zhuangfy",
            **lua_contract,
            "activeRoomGroup": "SceneLight6Rarity",
        },
        "serializedCharacterPrefab": prefab,
        "knownActiveAuthoredCandidates": {
            "count": 18,
            "typeCounts": {str(key): value for key, value in sorted(type_counts.items())},
            "cookieCount": 0,
            "shadowRequestCount": 1,
            "room": {"group": "SceneLight6Rarity", "count": 12, "lights": room_rows},
            "character": {"group": "light_overview", "count": 6, "lights": operator_rows},
        },
        "nativeFollowerContract": {
            "methods": native_rows,
            "enumeration": (
                "InitLightFollower calls GetComponentsInChildren<CharInfoLightFollower>(true), "
                "maps followableNodeType 0 to Bip001 and 1 to Head_Local, then initializes "
                "each component with that transform."
            ),
            "lateTickModes": {
                "0": "fixed world position offset",
                "1": "parent-space position and rotation",
            },
            "selectedFollowerCount": 4,
        },
        "nativeCullBoundary": native_cull_boundary,
        "evidenceBoundary": {
            "closed": [
                "installed Lua prefab path and direct-child activation rule",
                "rarity-6 GachaRoom group selection",
                "all 44 serialized character-prefab Unity Lights and six page groups",
                "six selected light_overview rows and four follower records",
                "twelve selected SceneLight6Rarity room rows",
                "known 18-row authored type/cookie/shadow census",
                "installed native follower traversal, node selection, and transform modes",
                "shipped normal candidate core with fallback and Gacha occlusion disabled",
                "generic room layer/mask gate for all twelve room rows",
                "aspect-independent rejection of Spot Light (20) and 17-row authored upper bound",
            ],
            "open": [
                "target-frame HGCullingSystem.CullLights pointer/count and survivors",
                "aspect-dependent AABB outcomes for the other eleven room rows",
                "character-light cull outcomes and evaluated follower transforms",
                "persistent/global carry-in or runtime-created custom lights",
                "final priority/distance order, LightDataBuffer rows, and lightCount",
            ],
            "decision": (
                "Use 18 as the exact known serialized input population and 17 only as its "
                "current native survivor upper bound. Do not publish either as the retail "
                "survivor array or enable deferred pass 0 until the target-frame result is "
                "captured or otherwise source-closed."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate that the committed generated contract is current without rewriting it.",
    )
    parser.add_argument("--skip-hash-pins", action="store_true")
    args = parser.parse_args()
    report = build_report(verify_hashes=not args.skip_hash_pins)
    serialized = json.dumps(report, indent=2) + "\n"
    if args.check:
        require(
            "generatedOutputExists",
            args.output.exists(),
            True,
            args.output,
        )
        actual = args.output.read_text(encoding="utf-8")
        require(
            "generatedOutputCurrent",
            hashlib.sha256(actual.encode("utf-8")).hexdigest(),
            hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
            args.output,
        )
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(report["outcome"])
    print(f"{'checked' if args.check else 'wrote'} {args.output}")


if __name__ == "__main__":
    main()
