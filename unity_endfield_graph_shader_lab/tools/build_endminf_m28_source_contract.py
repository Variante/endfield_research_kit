#!/usr/bin/env python3
"""Build the exact source contract for Endminf's two M28 consumers."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scratch/animestudio/endminf_m28_source_contract"
PREFABS = PROBE / "prefab_json"
ASSET_MAP = (
    ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
PUBLISHED_MATERIAL = (
    ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/json_by_type/Material"
    / "M_fx_endminm_gfx_28_pBF7FEE87831B48FB.json"
)
OUTPUT = (
    ROOT
    / "reports/assets/character_recovery"
    / "endminf_m28_source_contract.json"
)

MATERIAL_ID = -4647734024635463429
MESH_ID = 9180196635748412994
SHADER_ID = 7766268189260370413
VERTEX_STREAMS = [0, 1, 3, 4, 5, 34]
VERTEX_STREAM_NAMES = ["Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"]

EXPECTED_ASSET_ROWS = (
    ("P_fxui_endminm003_overview_02", 4503240569034685938, "Animator", 373845082),
    ("MonoBehaviour", 2053995046584853056, "MonoBehaviour", 67616247),
    ("M_fx_endminm_gfx_28", MATERIAL_ID, "Material", 98801184),
    ("T_fx_mask_17_C_M", -8068815077083075652, "Texture2D", 218263346),
    ("T_fx_flow_121_M", 6970530313307194154, "Texture2D", 793448011),
    ("Sphere001", MESH_ID, "Mesh", 757901537),
)

TARGETS = (
    {
        "root": "P_fxui_endminm003_overview_02",
        "hierarchy": "all/Particle System (9)",
        "sourceOffset": 373845082,
        "gameObject": ("GameObject/Particle System (9)_pC7352270B936BDF2.json", -4092326818857173518),
        "transform": ("Transform/Transform#44_p2CD18AD818A5BDF2.json", 3229515068532440562),
        "particle": ("ParticleSystem/ParticleSystem#1_p836044E204DBBDF2.json", -8980101919441961486),
        "renderer": ("ParticleSystemRenderer/ParticleSystemRenderer#59_p4BFAE1AE5D58BDF2.json", 5474936436028915186),
        "delay": 4.4,
        "lifetime": 1.0,
        "size": 0.3,
    },
    {
        "root": "P_fxui_endminm003_overview_03",
        "hierarchy": "all/glow/Particle System (10)",
        "sourceOffset": 67616247,
        "gameObject": ("GameObject/Particle System (10)_p39D93E1DF2562240.json", 4168431228448809536),
        "transform": ("Transform/Transform#96_p17613581FBC92240.json", 1684686568004592192),
        "particle": ("ParticleSystem/ParticleSystem#101_p36BF2B48D0272240.json", 3944919390329709120),
        "renderer": ("ParticleSystemRenderer/ParticleSystemRenderer#100_p32DEA5B58EAB2240.json", 3665549345927406144),
        "delay": 2.9,
        "lifetime": 0.35,
        "size": 0.13,
    },
)

EXPECTED_ARTIFACT_SHA256 = {
    "GameObject/Particle System (9)_pC7352270B936BDF2.json": "e94743ccfa14c3486b4fc0ca916f0449701dfaa51ecb7b9f0d2e550b2885d95b",
    "Transform/Transform#44_p2CD18AD818A5BDF2.json": "0cd8a6792047f5ba8ef6079c89377358b534179eb8eb022c756ae9ab7f840eb0",
    "ParticleSystem/ParticleSystem#1_p836044E204DBBDF2.json": "11bfa897f1b72f365f6da795d48ebc5d995f924dc196b1a45e10d1269ca6112a",
    "ParticleSystemRenderer/ParticleSystemRenderer#59_p4BFAE1AE5D58BDF2.json": "b9cac14f036598977a07f5c059ecdfc9c1ed62312ca204ece65a1fbcce04a2a1",
    "GameObject/Particle System (10)_p39D93E1DF2562240.json": "be96cc9e1e491c18bb58d523e22ef27fa1dfcbb6e75783fe88e5f410837e77ab",
    "Transform/Transform#96_p17613581FBC92240.json": "a34b125c0ac20ef6735510993f165ca9d4308fb331c8750f44e20a7b0293a9d8",
    "ParticleSystem/ParticleSystem#101_p36BF2B48D0272240.json": "066436c80e9235f7bb04d370d329977df5becc829148ff67164aa0f9b5c2604a",
    "ParticleSystemRenderer/ParticleSystemRenderer#100_p32DEA5B58EAB2240.json": "a066423f860eef700cc1ee1dd2079436714f8b1511bb7d30d74e05e47fe692fa",
}
EXPECTED_MATERIAL_SHA256 = "51ae58da347abf62408380255d2abc290145642736094dedd121dc2ac8081d80"
EXPECTED_INDEX_SHA256 = "681edf2fdc3037fa8f83ab0aec4a0d4cfb9e8971178f660eedc740defa1b3cbe"
EXPECTED_PREFAB_FILTER_SHA256 = "abe83c0724f5298a51ad11a6fd41a789be560304a41f19ca8b7076ebb704b931"
EXPECTED_MATERIAL_FILTER_SHA256 = "56e6cca5c15596a3a06bbed7e7d03f7a65f3f5028e58e528022c45e705b8586c"
EXPECTED_PREFAB_STAMP_SHA256 = "1ba1ab9c975b9e0ce8a7011a0283568e990aa139fa64ad09b94de40ec65ecc5d"
EXPECTED_MATERIAL_STAMP_SHA256 = "b4cd4c02de50897d5cf94776abea47d2ca0e6b63d3889ed22817621775ca95e0"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"missing JSON input: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"JSON root is not an object: {path}")
    return value


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def pptr(value: object) -> int:
    return int(value.get("m_PathID", 0)) if isinstance(value, dict) else 0


def filename_path_id(path: Path) -> int:
    match = re.search(r"_p([0-9A-Fa-f]{16})$", path.stem)
    require(match is not None, f"artifact filename lacks PathID: {path}")
    unsigned = int(match.group(1), 16)
    return unsigned if unsigned < (1 << 63) else unsigned - (1 << 64)


def iter_asset_map_entries(path: Path):
    in_entries = False
    buffer: list[str] = []
    depth = 0
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not in_entries:
                if stripped == '"AssetEntries": [':
                    in_entries = True
                continue
            if not buffer and stripped == "]":
                return
            if not buffer:
                if stripped.startswith("{"):
                    buffer.append(line)
                    depth = line.count("{") - line.count("}")
                continue
            buffer.append(line)
            depth += line.count("{") - line.count("}")
            if depth == 0:
                yield json.loads("".join(buffer).strip().rstrip(","))
                buffer.clear()
    raise ValueError("AssetEntries did not terminate")


def exact_asset_rows() -> list[dict]:
    matches = {identity: [] for identity in EXPECTED_ASSET_ROWS}
    for row in iter_asset_map_entries(ASSET_MAP):
        identity = (
            row.get("Name"),
            int(row.get("PathID", 0)),
            row.get("Type"),
            int(row.get("Offset", -1)),
        )
        if identity in matches:
            matches[identity].append(row)
    result = []
    for identity in EXPECTED_ASSET_ROWS:
        require(len(matches[identity]) == 1, f"AssetMap identity is not unique: {identity}")
        result.append(matches[identity][0])
    return result


def validate_object_index(path: Path) -> tuple[dict, dict[int, dict]]:
    require(sha256(path) == EXPECTED_INDEX_SHA256, "M28 object-index artifact drifted")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    require(records and records[-1].get("recordType") == "summary", "object index summary is not terminal")
    summary = records[-1]
    require(summary.get("complete") is True, "object index is incomplete")
    require(summary.get("counts", {}).get("errors") == 0, "object index reports errors")
    objects = {
        int(row["object"]["pathId"]): row
        for row in records
        if row.get("recordType") == "object"
    }
    return summary, objects


def build_hierarchy_maps() -> tuple[dict[int, tuple[Path, dict]], dict[int, tuple[Path, dict]], dict[int, int]]:
    game_objects: dict[int, tuple[Path, dict]] = {}
    for path in sorted((PREFABS / "GameObject").glob("*.json")):
        row = load_json(path)
        game_id = pptr(row["m_Transform"]["m_GameObject"])
        require(game_id == filename_path_id(path), f"GameObject filename/PPtr drifted: {path}")
        require(game_id not in game_objects, f"duplicate GameObject PathID: {game_id}")
        game_objects[game_id] = (path, row)

    transforms: dict[int, tuple[Path, dict]] = {}
    transform_by_game: dict[int, int] = {}
    for path in sorted((PREFABS / "Transform").glob("*.json")):
        row = load_json(path)
        transform_id = filename_path_id(path)
        game_id = pptr(row["m_GameObject"])
        require(transform_id not in transforms, f"duplicate Transform PathID: {transform_id}")
        require(game_id not in transform_by_game, f"duplicate GameObject Transform: {game_id}")
        transforms[transform_id] = (path, row)
        transform_by_game[game_id] = transform_id
    return game_objects, transforms, transform_by_game


def hierarchy_path(
    game_id: int,
    game_objects: dict[int, tuple[Path, dict]],
    transforms: dict[int, tuple[Path, dict]],
    transform_by_game: dict[int, int],
) -> str:
    names: list[str] = []
    seen: set[int] = set()
    while game_id:
        require(game_id not in seen, "Transform hierarchy cycle")
        seen.add(game_id)
        _, game_object = game_objects[game_id]
        names.append(str(game_object["m_Name"]))
        _, transform = transforms[transform_by_game[game_id]]
        father_id = pptr(transform["m_Father"])
        game_id = pptr(transforms[father_id][1]["m_GameObject"]) if father_id else 0
    return "/".join(reversed(names))


def artifact(path: Path, expected_sha: str) -> dict:
    actual = sha256(path)
    require(actual == expected_sha, f"artifact hash drifted: {path}")
    return {"path": rel(path), "sha256": actual}


def component_metadata(row: dict, expected_id: int, expected_type: str, source_offset: int) -> dict:
    meta = row.get("$animestudio") or {}
    require(int(meta.get("pathId", 0)) == expected_id, f"{expected_type} PathID drifted")
    require(meta.get("type") == expected_type, f"{expected_type} type drifted")
    require(int(meta.get("sourceOffset", -1)) == source_offset, f"{expected_type} source offset drifted")
    return {
        "rawDataLength": int(meta["rawDataLength"]),
        "rawDataSha256": str(meta["rawDataSha256"]),
        "sourceFile": str(meta["sourceFile"]),
        "sourceOffset": int(meta["sourceOffset"]),
    }


def build_consumer(
    spec: dict,
    game_objects: dict[int, tuple[Path, dict]],
    transforms: dict[int, tuple[Path, dict]],
    transform_by_game: dict[int, int],
    index_objects: dict[int, dict],
) -> dict:
    paths = {key: PREFABS / spec[key][0] for key in ("gameObject", "transform", "particle", "renderer")}
    ids = {key: int(spec[key][1]) for key in paths}
    rows = {key: load_json(path) for key, path in paths.items()}
    for key, path in paths.items():
        require(filename_path_id(path) == ids[key], f"{key} filename PathID drifted")
        require(sha256(path) == EXPECTED_ARTIFACT_SHA256[spec[key][0]], f"{key} artifact drifted")

    expected_full_hierarchy = f"{spec['root']}/{spec['hierarchy']}"
    require(
        hierarchy_path(ids["gameObject"], game_objects, transforms, transform_by_game)
        == expected_full_hierarchy,
        f"consumer hierarchy drifted: {spec['hierarchy']}",
    )
    game_object = rows["gameObject"]
    transform = rows["transform"]
    particle = rows["particle"]
    renderer = rows["renderer"]
    require(
        [pptr(value) for value in game_object["m_Components"]]
        == [ids["transform"], ids["particle"], ids["renderer"]],
        f"component tuple drifted: {spec['hierarchy']}",
    )
    require(pptr(transform["m_GameObject"]) == ids["gameObject"], "Transform owner drifted")
    require(pptr(particle["m_GameObject"]) == ids["gameObject"], "ParticleSystem owner drifted")
    require(pptr(renderer["m_GameObject"]) == ids["gameObject"], "renderer owner drifted")
    require(renderer["m_Enabled"] is True, "source renderer is no longer enabled")
    require([pptr(value) for value in renderer["m_Materials"]] == [MATERIAL_ID], "renderer material drifted")
    require(pptr(renderer["m_Mesh"]) == MESH_ID, "renderer mesh drifted")
    require(renderer["m_VertexStreams"] == VERTEX_STREAMS, "renderer streams drifted")
    require(renderer["m_RenderMode"] == 4, "renderer mode drifted")
    require(renderer["m_EnableGPUInstancing"] is True, "GPU instancing drifted")
    require(particle["lengthInSec"] == 5.0, "particle duration drifted")
    require(particle["startDelay"]["minMaxState"] == 0, "particle delay mode drifted")
    require(particle["startDelay"]["scalar"] == spec["delay"], "particle delay drifted")
    require(particle["InitialModule"]["startLifetime"]["scalar"] == spec["lifetime"], "particle lifetime drifted")
    require(particle["InitialModule"]["startSize"]["scalar"] == spec["size"], "particle size drifted")
    require(particle["looping"] is False and particle["playOnAwake"] is True, "particle playback drifted")
    require(particle["randomSeed"] == 5834, "particle seed drifted")
    bursts = particle["EmissionModule"]["m_Bursts"]
    require(len(bursts) == 1 and bursts[0]["time"] == 0.0, "particle burst timing drifted")
    require(bursts[0]["countCurve"]["scalar"] == 1.0, "particle burst count drifted")

    particle_meta = component_metadata(particle, ids["particle"], "ParticleSystem", spec["sourceOffset"])
    renderer_meta = component_metadata(renderer, ids["renderer"], "ParticleSystemRenderer", spec["sourceOffset"])
    for key, expected_type, raw_sha in (
        ("particle", "ParticleSystem", particle_meta["rawDataSha256"]),
        ("renderer", "ParticleSystemRenderer", renderer_meta["rawDataSha256"]),
    ):
        indexed = index_objects.get(ids[key])
        require(indexed is not None and indexed.get("type") == expected_type, f"object index lacks {key}")
        require(indexed.get("decodeStatus") == "decoded", f"object index did not decode {key}")
        require(indexed.get("opaque", {}).get("rawSha256") == raw_sha, f"object index raw hash drifted: {key}")

    return {
        "root": spec["root"],
        "hierarchy": spec["hierarchy"],
        "exactFullHierarchy": expected_full_hierarchy,
        "sourceOffset": spec["sourceOffset"],
        "tuple": {
            key: {
                "pathId": ids[key],
                "pathIdHex": f"{ids[key] & ((1 << 64) - 1):016X}",
                **artifact(paths[key], EXPECTED_ARTIFACT_SHA256[spec[key][0]]),
            }
            for key in paths
        },
        "transformPayload": {
            "fatherPathId": pptr(transform["m_Father"]),
            "localPosition": transform["m_LocalPosition"],
            "localRotation": transform["m_LocalRotation"],
            "localScale": transform["m_LocalScale"],
        },
        "particleSystem": {
            **particle_meta,
            "durationSeconds": particle["lengthInSec"],
            "simulationSpeed": particle["simulationSpeed"],
            "startDelay": {"minMaxState": particle["startDelay"]["minMaxState"], "seconds": particle["startDelay"]["scalar"]},
            "looping": particle["looping"],
            "playOnAwake": particle["playOnAwake"],
            "moveWithTransform": particle["moveWithTransform"],
            "randomSeed": particle["randomSeed"],
            "startLifetimeSeconds": particle["InitialModule"]["startLifetime"]["scalar"],
            "startSpeed": particle["InitialModule"]["startSpeed"]["scalar"],
            "startSize": particle["InitialModule"]["startSize"]["scalar"],
            "burst": {
                "timeAfterDelaySeconds": bursts[0]["time"],
                "count": bursts[0]["countCurve"]["scalar"],
                "cycleCount": bursts[0]["cycleCount"],
                "repeatInterval": bursts[0]["repeatInterval"],
                "probability": bursts[0]["probability"],
            },
        },
        "renderer": {
            **renderer_meta,
            "sourceEnabled": renderer["m_Enabled"],
            "renderMode": {"serialized": renderer["m_RenderMode"], "name": "Mesh"},
            "meshDistribution": {"serialized": renderer["m_MeshDistribution"], "name": "UniformRandom"},
            "gpuInstancing": renderer["m_EnableGPUInstancing"],
            "hgGpuInstancing": renderer["m_EnableHGGPUInstancing"],
            "materialPPtr": {"fileId": renderer["m_Materials"][0]["m_FileID"], "pathId": MATERIAL_ID},
            "meshPPtr": {"fileId": renderer["m_Mesh"]["m_FileID"], "pathId": MESH_ID},
            "vertexStreams": {"serialized": renderer["m_VertexStreams"], "names": VERTEX_STREAM_NAMES},
            "motionVectors": renderer["m_MotionVectors"],
            "applyActiveColorSpace": renderer["m_ApplyActiveColorSpace"],
        },
    }


def build() -> dict:
    material_path = PROBE / "material_json/Material/M_fx_endminm_gfx_28_pBF7FEE87831B48FB.json"
    material = load_json(material_path)
    require(sha256(material_path) == EXPECTED_MATERIAL_SHA256, "targeted M28 material hash drifted")
    require(PUBLISHED_MATERIAL.is_file(), "targeted M28 material was not published to json_by_type")
    require(sha256(PUBLISHED_MATERIAL) == EXPECTED_MATERIAL_SHA256, "published M28 material hash drifted")
    require(material["m_Name"] == "M_fx_endminm_gfx_28", "material name drifted")
    require(pptr(material["m_Shader"]) == SHADER_ID, "material shader drifted")
    require(material["m_ValidKeywords"] == ["_USE_DISSOLVE"], "material keywords drifted")
    require(material["m_CustomRenderQueue"] == 3000, "material queue drifted")
    require(material["m_DisabledShaderPasses"] == ["GBuffer"], "material disabled passes drifted")
    tex_envs = material["m_SavedProperties"]["m_TexEnvs"]
    require(pptr(tex_envs["_DissolveTex"]["m_Texture"]) == -8068815077083075652, "dissolve texture drifted")
    require(pptr(tex_envs["_RefractTex"]["m_Texture"]) == 6970530313307194154, "refract texture drifted")
    require(
        all(pptr(value["m_Texture"]) == 0 for key, value in tex_envs.items() if key not in {"_DissolveTex", "_RefractTex"}),
        "unexpected non-null M28 texture binding",
    )

    index_path = PROBE / "object_index/001_98E51B76A48F5BEF8D07BDFD3E4DA7ED.jsonl"
    summary, index_objects = validate_object_index(index_path)
    prefab_stamp_path = PREFABS / ".character_import_stage.json"
    material_stamp_path = PROBE / "material_json/.character_import_stage.json"
    prefab_stamp = load_json(prefab_stamp_path)
    material_stamp = load_json(material_stamp_path)
    require(prefab_stamp["fingerprint"] == "17db6c0d1ae0f4c5b7c55be0b0c9c62677d7a5d0f5a23aa43f562b8cc57d0c61", "prefab extraction fingerprint drifted")
    require(material_stamp["fingerprint"] == "b26eb588a3b07b4285459766ddb890292d5a3b4851b96eddf5ad66cfd7d42b4d", "material extraction fingerprint drifted")
    require(prefab_stamp.get("object_index_jsonl") is True, "prefab extraction omitted object index")
    game_objects, transforms, transform_by_game = build_hierarchy_maps()
    consumers = [
        build_consumer(spec, game_objects, transforms, transform_by_game, index_objects)
        for spec in TARGETS
    ]
    require(consumers[0]["renderer"]["materialPPtr"]["fileId"] == 8, "overview_02 material FileID drifted")
    require(consumers[0]["renderer"]["meshPPtr"]["fileId"] == 9, "overview_02 mesh FileID drifted")
    require(consumers[1]["renderer"]["materialPPtr"]["fileId"] == 4, "overview_03 material FileID drifted")
    require(consumers[1]["renderer"]["meshPPtr"]["fileId"] == 5, "overview_03 mesh FileID drifted")

    floats = material["m_SavedProperties"]["m_Floats"]
    colors = material["m_SavedProperties"]["m_Colors"]
    return {
        "schema": "endfield.endminf-m28-source-contract.v1",
        "status": "exact_material_and_two_source_tuples_closed",
        "scope": [
            "P_fxui_endminm003_overview_02/all/Particle System (9)",
            "P_fxui_endminm003_overview_03/all/glow/Particle System (10)",
        ],
        "assetMap": {"path": rel(ASSET_MAP), "sha256": sha256(ASSET_MAP), "exactUniqueRows": exact_asset_rows()},
        "targetedExtraction": {
            "method": "direct AnimeStudio --filter_data export from six exact current-build AssetMap identities; no broad export",
            "prefabFilter": artifact(PROBE / "filters/m28_prefabs_001_98E51B76A48F5BEF8D07BDFD3E4DA7ED.json", EXPECTED_PREFAB_FILTER_SHA256),
            "materialFilter": artifact(PROBE / "filters/m28_material_001_FC784A3D097236EF3B3E84F44E1B28D2.json", EXPECTED_MATERIAL_FILTER_SHA256),
            "prefabStageStamp": {**artifact(prefab_stamp_path, EXPECTED_PREFAB_STAMP_SHA256), "fingerprint": prefab_stamp["fingerprint"]},
            "materialStageStamp": {**artifact(material_stamp_path, EXPECTED_MATERIAL_STAMP_SHA256), "fingerprint": material_stamp["fingerprint"]},
            "objectIndex": {"path": rel(index_path), "sha256": EXPECTED_INDEX_SHA256, "summary": summary},
        },
        "material": {
            "name": material["m_Name"],
            "pathId": MATERIAL_ID,
            "pathIdHex": "BF7FEE87831B48FB",
            "targetedArtifact": artifact(material_path, EXPECTED_MATERIAL_SHA256),
            "publishedArtifact": artifact(PUBLISHED_MATERIAL, EXPECTED_MATERIAL_SHA256),
            "shader": {"name": "HGRP/Effect/VFXRefract", "pathId": SHADER_ID},
            "validKeywords": material["m_ValidKeywords"],
            "invalidKeywords": material["m_InvalidKeywords"],
            "renderQueue": material["m_CustomRenderQueue"],
            "renderType": material["m_StringTagMap"]["RenderType"],
            "disabledPasses": material["m_DisabledShaderPasses"],
            "texturePPtrs": {
                key: {"fileId": value["m_Texture"]["m_FileID"], "pathId": pptr(value["m_Texture"])}
                for key, value in tex_envs.items()
            },
            "selectedFloats": {
                key: floats[key]
                for key in (
                    "_Intensity", "_TintColorAlpha", "_RefractIsNormal", "_DissolveUVRotate",
                    "_DissolveScheduleOffset", "_DissolveEdgeSharp", "_DisableZTest", "_ZTest",
                    "_ZWrite", "_CullMode", "_SrcBlend", "_DstBlend",
                )
            },
            "selectedVectors": {
                key: colors[key]
                for key in ("_RefractDir", "_RefractUVSpeed", "_DissolveUVSpeed")
            },
        },
        "sharedMesh": {"name": "Sphere001", "pathId": MESH_ID, "pathIdHex": "7F669C3392052E42"},
        "consumers": consumers,
        "runtimeBoundary": {
            "sourceTuples": "closed",
            "materialSource": "closed",
            "shaderProgramAnd60HzWindows": "outside this source-contract builder; admission remains fail-closed until their separate gates pass",
        },
        "protectedControls": {
            "overview_02/all/shitou (1)": "M21 exact small crystal; not modified or used as compensation",
            "overview_02/all/suikuai (1)": "admitted exact VFXRefract consumer; not modified",
            "overview_02/all/suikuai (2)": "M27 LitEffect consumer; not modified",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    report = build()
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    output = args.output if args.output.is_absolute() else ROOT / args.output
    if args.check:
        require(output.is_file(), f"missing report: {output}")
        require(output.read_text(encoding="utf-8") == rendered, "report is stale")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
    print(f"validated Endminf M28 exact source contract: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
