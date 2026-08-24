#!/usr/bin/env python3
"""Build the exact source contract for Endminf overview_02/suikuai (2)."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scratch/animestudio/endminf_m27_source_contract"
REFERENCE = (
    ROOT
    / "scratch/character_recovery/endminf_m27_source_contract"
    / "no_framegen_4p49_window"
)
ASSET_MAP = (
    ROOT
    / "export_full/recovered/AnimeStudio-cli/StreamingAssets/maps"
    / "endfield_streamingassets_assets.json"
)
OUTPUT = (
    ROOT
    / "reports/assets/character_recovery"
    / "endminf_m27_suikuai_source_contract.json"
)

EXPECTED_FILTER_IDENTITIES = (
    ("P_fxui_endminm003_overview_02", 4503240569034685938, "Animator", 373845082),
    ("M_fx_endminm_gfx_27", -6543263480174539080, "Material", 540787460),
    ("T_fx_sourcerocks+2_D", 5406992154111209049, "Texture2D", 81202418),
    ("T_fx_sourcerocks+3_N", 5597062348073817015, "Texture2D", 355691189),
    ("T_fx_sourcerocks+1_N", -8583694459516385401, "Texture2D", 613212742),
    ("T_fx_flow_04_02_M", -2770956563882859728, "Texture2D", 448727288),
    ("S_rock_small_1_017_02_lod2", -8157825361227167527, "Mesh", 247138057),
)

TEXTURES = (
    (
        "_BaseColorMap",
        "T_fx_sourcerocks+2_D",
        5406992154111209049,
        "967_convert/Texture2D/"
        "T_fx_sourcerocks+2_D_p4B097EB7791F6E59.texture2d.bc7.manifest.json",
        "967_convert/Texture2D/T_fx_sourcerocks+2_D_p4B097EB7791F6E59.png",
    ),
    (
        "_MROMap",
        "T_fx_sourcerocks+3_N",
        5597062348073817015,
        "ce_convert/Texture2D/"
        "T_fx_sourcerocks+3_N_p4DACC28D12A753B7.texture2d.raw.manifest.json",
        "ce_convert/Texture2D/T_fx_sourcerocks+3_N_p4DACC28D12A753B7.png",
    ),
    (
        "_NormalMap",
        "T_fx_sourcerocks+1_N",
        -8583694459516385401,
        "967_convert/Texture2D/"
        "T_fx_sourcerocks+1_N_p88E0975E10098787.texture2d.raw.manifest.json",
        "967_convert/Texture2D/T_fx_sourcerocks+1_N_p88E0975E10098787.png",
    ),
    (
        "_ParallaxMap",
        "T_fx_flow_04_02_M",
        -2770956563882859728,
        "fc_convert/Texture2D/"
        "T_fx_flow_04_02_M_pD98B95AFB1B9A330.texture2d.bc7.manifest.json",
        "fc_convert/Texture2D/T_fx_flow_04_02_M_pD98B95AFB1B9A330.png",
    ),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path):
    require(path.is_file(), f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


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
                text = "".join(buffer).strip().rstrip(",")
                yield json.loads(text)
                buffer.clear()
    raise ValueError("AssetEntries did not terminate")


def validate_asset_map(filter_rows: list[dict]) -> list[dict]:
    requested = {
        (row["Name"], int(row["PathID"]), row["Type"], int(row["Offset"]))
        for row in filter_rows
    }
    require(requested == set(EXPECTED_FILTER_IDENTITIES), "filter identity set drifted")
    matches: dict[tuple, list[dict]] = {key: [] for key in requested}
    for entry in iter_asset_map_entries(ASSET_MAP):
        key = (
            entry.get("Name"),
            int(entry.get("PathID", 0)),
            entry.get("Type"),
            int(entry.get("Offset", -1)),
        )
        if key in matches:
            matches[key].append(entry)
    for key, rows in matches.items():
        require(len(rows) == 1, f"AssetMap identity is not unique: {key}: {len(rows)}")
        filter_source = next(
            row["Source"]
            for row in filter_rows
            if (row["Name"], int(row["PathID"]), row["Type"], int(row["Offset"])) == key
        )
        require(
            Path(filter_source).name.lower() == Path(rows[0]["Source"]).name.lower(),
            f"filter source drifted: {key}",
        )
    return [matches[key][0] for key in EXPECTED_FILTER_IDENTITIES]


def validate_object_index(path: Path) -> dict:
    require(path.is_file(), f"missing object index: {path}")
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    summaries = [row for row in records if row.get("recordType") == "summary"]
    require(len(summaries) == 1, "object index must contain one terminal summary")
    require(records[-1] == summaries[0], "object index summary is not terminal")
    summary = summaries[0]
    require(summary.get("complete") is True, "object index is incomplete")
    require(summary["counts"]["errors"] == 0, "object index reports errors")
    return {"path": rel(path), "sha256": sha256(path), "summary": summary}


def curve_range(curve: dict) -> list[float]:
    require(curve["minMaxState"] == 3, "expected random-between-two-constants curve")
    return [curve["minScalar"], curve["scalar"]]


def independent_block_layout(manifest: dict) -> dict:
    require(manifest["format"] in {"BC5", "BC7"}, "unexpected texture format")
    offset = 0
    rows = []
    width = int(manifest["width"])
    height = int(manifest["height"])
    for mip in range(int(manifest["mipCount"])):
        mip_width = max(1, width >> mip)
        mip_height = max(1, height >> mip)
        byte_size = math.ceil(mip_width / 4) * math.ceil(mip_height / 4) * 16
        rows.append(
            {
                "mip": mip,
                "width": mip_width,
                "height": mip_height,
                "offset": offset,
                "byteSize": byte_size,
            }
        )
        offset += byte_size
    require(offset == manifest["completeImageSize"], "block mip chain size mismatch")
    return {
        "method": "independent 4x4 block-compressed mip chain, 16 bytes per block",
        "validated": True,
        "bytes": offset,
        "mips": rows,
    }


def build() -> dict:
    filter_path = PROBE / "filter_data.json"
    filter_rows = load_json(filter_path)
    asset_rows = validate_asset_map(filter_rows)

    material_path = (
        PROBE / "fc_json/Material/M_fx_endminm_gfx_27_pA531A88850690EB8.json"
    )
    particle_path = (
        PROBE
        / "prefab_json/ParticleSystem/ParticleSystem#19_pD0F8EAE40ECBBDF2.json"
    )
    renderer_path = (
        PROBE
        / "prefab_json/ParticleSystemRenderer/"
        / "ParticleSystemRenderer#29_p00D29E9B23BDBDF2.json"
    )
    game_object_path = (
        PROBE / "prefab_json/GameObject/suikuai (2)_p7E28A79DF3C2BDF2.json"
    )
    mesh_json_path = (
        PROBE / "fc_json/Mesh/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.json"
    )
    mesh_obj_path = (
        PROBE / "fc_convert/Mesh/S_rock_small_1_017_02_lod2_p8EC9950E5461C8D9.obj"
    )

    material = load_json(material_path)
    particle = load_json(particle_path)
    renderer = load_json(renderer_path)
    game_object = load_json(game_object_path)
    mesh = load_json(mesh_json_path)

    require(material["m_Name"] == "M_fx_endminm_gfx_27", "material name drifted")
    require(material["m_Shader"]["m_PathID"] == 6428594484694422749, "shader drifted")
    require(material["m_ValidKeywords"] == ["_PARALLAX_MAP"], "keywords drifted")
    require(material["m_CustomRenderQueue"] == 2000, "render queue drifted")
    require(
        material["m_DisabledShaderPasses"]
        == ["ForwardOnly", "DepthOnly", "ForwardReflection"],
        "disabled pass set drifted",
    )

    texture_rows = []
    tex_envs = material["m_SavedProperties"]["m_TexEnvs"]
    for prop, name, path_id, manifest_rel, png_rel in TEXTURES:
        require(tex_envs[prop]["m_Texture"]["m_PathID"] == path_id, f"{prop} drifted")
        manifest_path = PROBE / manifest_rel
        manifest = load_json(manifest_path)
        require(manifest["name"] == name and manifest["pathId"] == path_id, f"{prop} identity drifted")
        payload_path = manifest_path.parent / manifest["payload"]["file"]
        require(payload_path.stat().st_size == manifest["payload"]["bytes"], f"{prop} size drifted")
        require(sha256(payload_path).upper() == manifest["payload"]["sha256"], f"{prop} hash drifted")
        png_path = PROBE / png_rel
        texture_rows.append(
            {
                "property": prop,
                "name": name,
                "pathId": path_id,
                "pathIdHex": f"{path_id & ((1 << 64) - 1):016X}",
                "format": manifest["format"],
                "width": manifest["width"],
                "height": manifest["height"],
                "mipCount": manifest["mipCount"],
                "colorSpace": manifest["colorSpace"],
                "payload": {
                    "path": rel(payload_path),
                    "bytes": payload_path.stat().st_size,
                    "sha256": sha256(payload_path),
                },
                "decodedPng": {"path": rel(png_path), "sha256": sha256(png_path)},
                "exporterLayoutValidated": manifest["payload"]["layoutValidated"],
                "independentLayout": independent_block_layout(manifest),
            }
        )

    meta = particle["$animestudio"]
    renderer_meta = renderer["$animestudio"]
    require(meta["pathId"] == -3388700454374621710, "particle PathID drifted")
    require(renderer_meta["pathId"] == 59284134265994738, "renderer PathID drifted")
    require(renderer["m_Enabled"] is True, "source renderer is no longer enabled")
    require(
        [row["m_PathID"] for row in renderer["m_Materials"]] == [-6543263480174539080],
        "renderer material drifted",
    )
    require(renderer["m_Mesh"]["m_PathID"] == -8157825361227167527, "mesh PPtr drifted")
    require(renderer["m_VertexStreams"] == [0, 1, 3, 4, 5, 34], "vertex streams drifted")

    burst = particle["EmissionModule"]["m_Bursts"]
    require(len(burst) == 1 and burst[0]["countCurve"]["minMaxState"] == 0, "burst drifted")
    require(burst[0]["countCurve"]["scalar"] == 15.0, "burst count drifted")
    require(mesh["m_Name"] == "S_rock_small_1_017_02_lod2", "mesh name drifted")
    require(mesh["m_VertexCount"] == 29, "mesh vertex count drifted")
    require(mesh["m_SubMeshes"][0]["indexCount"] == 72, "mesh index count drifted")

    reference_frames = []
    for source_frame in range(382, 391):
        image = REFERENCE / f"source_382_to_390_{source_frame - 381:02d}.png"
        require(image.is_file(), f"missing reference frame {source_frame}")
        reference_frames.append(
            {"sourceFrameOneBased": source_frame, "path": rel(image), "sha256": sha256(image)}
        )

    video = ROOT / "videos/2026-08-24_06-37-22.mkv"
    report = {
        "schema": "endfield.endminf-m27-suikuai-source-contract.v1",
        "status": "source_closed_visual_ownership_unresolved",
        "scope": "P_fxui_endminm003_overview_02/all/suikuai (2) only",
        "assetMap": {
            "path": rel(ASSET_MAP),
            "sha256": sha256(ASSET_MAP),
            "exactUniqueRows": asset_rows,
        },
        "targetedExtraction": {
            "filter": {"path": rel(filter_path), "sha256": sha256(filter_path)},
            "selectedIdentityCount": 7,
            "prefabExportedObjects": 7,
            "assetExportedObjects": {
                "material": 1,
                "textures": 4,
                "meshes": 1,
            },
            "objectIndex": validate_object_index(PROBE / "prefab_objects.jsonl"),
            "evidenceBoundary": "direct AnimeStudio --filter_data exports from exact AssetMap source/offset rows; no broad source scan or name-only ownership",
        },
        "particleSystem": {
            "path": rel(particle_path),
            "artifactSha256": sha256(particle_path),
            "pathId": meta["pathId"],
            "rawDataLength": meta["rawDataLength"],
            "rawDataSha256": meta["rawDataSha256"],
            "sourceFile": meta["sourceFile"],
            "sourceOffset": meta["sourceOffset"],
            "durationSeconds": particle["lengthInSec"],
            "simulationSpeed": particle["simulationSpeed"],
            "simulationSpace": "World",
            "moveWithTransformSerialized": particle["moveWithTransform"],
            "looping": particle["looping"],
            "playOnAwake": particle["playOnAwake"],
            "startDelaySeconds": particle["startDelay"]["scalar"],
            "randomSeed": particle["randomSeed"],
            "lifetimeSeconds": curve_range(particle["InitialModule"]["startLifetime"]),
            "speed": curve_range(particle["InitialModule"]["startSpeed"]),
            "size": curve_range(particle["InitialModule"]["startSize"]),
            "startColor": particle["InitialModule"]["startColor"],
            "burst": {
                "timeAfterDelaySeconds": burst[0]["time"],
                "count": burst[0]["countCurve"]["scalar"],
                "cycleCount": burst[0]["cycleCount"],
                "repeatInterval": burst[0]["repeatInterval"],
                "probability": burst[0]["probability"],
            },
            "customData": {
                "enabled": particle["CustomDataModule"]["enabled"],
                "mode0": particle["CustomDataModule"]["mode0"],
                "componentCount": particle["CustomDataModule"]["vectorComponentCount0"],
                "xRange": curve_range(particle["CustomDataModule"]["vector0_0"]),
                "yzw": [
                    particle["CustomDataModule"]["vector0_1"]["scalar"],
                    particle["CustomDataModule"]["vector0_2"]["scalar"],
                    particle["CustomDataModule"]["vector0_3"]["scalar"],
                ],
            },
        },
        "renderer": {
            "path": rel(renderer_path),
            "artifactSha256": sha256(renderer_path),
            "pathId": renderer_meta["pathId"],
            "rawDataLength": renderer_meta["rawDataLength"],
            "rawDataSha256": renderer_meta["rawDataSha256"],
            "sourceEnabled": renderer["m_Enabled"],
            "renderMode": {"serialized": renderer["m_RenderMode"], "name": "Mesh"},
            "meshDistribution": {"serialized": renderer["m_MeshDistribution"], "name": "UniformRandom"},
            "customVertexStreams": {
                "serialized": renderer["m_VertexStreams"],
                "names": ["Position", "Normal", "Color", "UV", "UV2", "Custom1XYZW"],
            },
            "materialPathId": renderer["m_Materials"][0]["m_PathID"],
            "meshPathId": renderer["m_Mesh"]["m_PathID"],
            "meshWeights": [
                renderer["m_MeshWeighting"],
                renderer["m_MeshWeighting1"],
                renderer["m_MeshWeighting2"],
                renderer["m_MeshWeighting3"],
            ],
            "localTransform": game_object["m_Transform"],
        },
        "material": {
            "path": rel(material_path),
            "artifactSha256": sha256(material_path),
            "name": material["m_Name"],
            "pathId": -6543263480174539080,
            "pathIdHex": "A531A88850690EB8",
            "shader": {"name": "HGRP/LitEffect", "pathId": material["m_Shader"]["m_PathID"]},
            "validKeywords": material["m_ValidKeywords"],
            "disabledPasses": material["m_DisabledShaderPasses"],
            "renderQueue": material["m_CustomRenderQueue"],
            "selectedProperties": {
                "_EmissiveColor": material["m_SavedProperties"]["m_Colors"]["_EmissiveColor"],
                "_ParallaxColor": material["m_SavedProperties"]["m_Colors"]["_ParallaxColor"],
                "_ParallaxColorDark": material["m_SavedProperties"]["m_Colors"]["_ParallaxColorDark"],
                "_ParallaxStrength": material["m_SavedProperties"]["m_Floats"]["_ParallaxStrength"],
                "_ParallaxTilling": material["m_SavedProperties"]["m_Floats"]["_ParallaxTilling"],
                "_ParallaxMarchNum": material["m_SavedProperties"]["m_Floats"]["_ParallaxMarchNum"],
                "_ParallaxAnimRandom": material["m_SavedProperties"]["m_Floats"]["_ParallaxAnimRandom"],
                "_ParallaxIgnorePostExposure": material["m_SavedProperties"]["m_Floats"]["_ParallaxIgnorePostExposure"],
            },
            "textures": texture_rows,
        },
        "mesh": {
            "json": {"path": rel(mesh_json_path), "sha256": sha256(mesh_json_path)},
            "obj": {"path": rel(mesh_obj_path), "sha256": sha256(mesh_obj_path)},
            "name": mesh["m_Name"],
            "pathId": -8157825361227167527,
            "pathIdHex": "8EC9950E5461C8D9",
            "vertexCount": mesh["m_VertexCount"],
            "indexCount": mesh["m_SubMeshes"][0]["indexCount"],
            "localAabb": mesh["m_SubMeshes"][0]["localAABB"],
        },
        "noFramegen60HzComparison": {
            "recording": {"path": rel(video), "sha256": sha256(video)},
            "mapping": "sourceFrame = 115 + round(sequenceSeconds * 60), with +/-1 source-frame anchor uncertainty",
            "authoredDelaySeconds": 4.49,
            "nominalBoundary": {
                "lastPreBurstSequenceSeconds": 269 / 60,
                "lastPreBurstSourceFrame": 384,
                "firstPostBurstSequenceSeconds": 270 / 60,
                "firstPostBurstSourceFrame": 385,
                "uncertaintySourceFrames": [383, 386],
            },
            "reviewedFrames": reference_frames,
            "observation": "Small amber faceted fragments are visible throughout source frames 382-390, including before the nominal M27 burst boundary. The window is physically compatible with an additional 15-fragment M27 burst, but it has no clean visual onset that separates M27 from the earlier actor-owned rock/crystal complex.",
            "ownershipConclusion": "source role closed; retail pixel ownership unresolved",
        },
        "runtimeBoundary": {
            "sourceRole": "authored-enabled late World-space physical-rock burst using the same small-rock mesh and four-texture family as the earlier LitEffect rocks",
            "managedStreamConstruction": "serialized ParticleSystem CustomData plus renderer vertex streams are sufficient for Unity to construct Position/Normal/Color/UV/UV2/Custom1XYZW",
            "remainingConsumer": "exact LitEffect HGBuffer/GBuffer five-MRT consumer, ParserBindChannels, and live per-frame/per-draw inputs",
            "admission": "fail_closed",
        },
        "protectedCrystalBoundary": {
            "path": "overview_02/all/shitou (1)",
            "material": "M_fx_endminm_gfx_21",
            "policy": "not modified and not used as a substitute for M27",
        },
    }
    return report


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
    print(f"validated Endminf M27 suikuai source contract: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
