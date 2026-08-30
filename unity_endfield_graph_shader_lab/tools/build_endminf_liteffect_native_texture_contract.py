#!/usr/bin/env python3
"""Publish Endminf LitEffect textures as exact native compressed mip chains."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PROJECT = Path(__file__).resolve().parents[1]
SOURCE_CONTRACT = (
    ROOT
    / "reports/assets/character_recovery/endminf_m27_suikuai_source_contract.json"
)
TEXTURE_ROOT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/Endminf"
    / "Effects/Overview/Textures"
)
MATERIAL_ROOT = TEXTURE_ROOT.with_name("Materials")
PAYLOAD_ROOT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads"
    / "EndminfLitEffect"
)
CONTRACT_ROOT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
)
IMPORT_CONTRACT = CONTRACT_ROOT / "endminf_liteffect_texture_import_contract.json"
PAYLOAD_CONTRACT = CONTRACT_ROOT / "endminf_liteffect_native_texture_payload_contract.json"

GUID_RE = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)
FORMAT_IDS = {"BC7": 25, "BC5": 27}
DXGI_FORMATS = {"BC7": 99, "BC5": 83}
EXPECTED_PROPERTIES = ["_BaseColorMap", "_MROMap", "_NormalMap", "_ParallaxMap"]
EXPECTED_MATERIALS = {
    "M_fx_endminm_gfx_01_p5A6341E8A834E421.mat",
    "M_fx_endminm_gfx_27_pA531A88850690EB8.mat",
    "M_fx_endminm_gfx_38_pAFCE491DD7BC5724.mat",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def load_json(path: Path) -> dict:
    require(path.is_file(), f"missing JSON input: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def project_asset_path(path: Path) -> str:
    return path.relative_to(PROJECT).as_posix()


def root_relative_path(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def read_guid(png: Path) -> str:
    meta = png.with_name(png.name + ".meta")
    require(meta.is_file(), f"missing stable texture GUID: {meta}")
    match = GUID_RE.search(meta.read_text(encoding="utf-8-sig"))
    require(match is not None, f"missing GUID field: {meta}")
    return match.group(1)


def mip_layout(width: int, height: int, mip_count: int) -> list[dict]:
    offset = 0
    rows = []
    for mip in range(mip_count):
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
    return rows


def descriptor_path(name: str, path_id_hex: str) -> Path:
    matches = [
        path
        for path in (ROOT / "scratch/animestudio/endminf_m27_source_contract").rglob(
            f"{name}_p{path_id_hex}.json"
        )
        if not path.name.endswith(".manifest.json")
    ]
    require(len(matches) == 1, f"descriptor identity is not unique for {name}: {matches}")
    return matches[0]


def generated_png(name: str, path_id_hex: str) -> Path:
    matches = list(TEXTURE_ROOT.glob(f"Compatibility_{name}_p{path_id_hex}.png"))
    require(len(matches) == 1, f"generated texture identity is not unique: {name}")
    return matches[0]


def source_hashes_by_path_id(source: dict) -> dict[int, str]:
    rows = source["assetMap"]["exactUniqueRows"]
    hashes = {
        int(row["PathID"]): str(row["Hash"])
        for row in rows
        if row["Type"] == "Texture2D"
    }
    require(len(hashes) == 4, "source AssetMap texture identity set drifted")
    return hashes


def import_profile(prop: str, texture: dict, descriptor: dict) -> dict:
    settings = descriptor["m_TextureSettings"]
    require(int(settings["m_FilterMode"]) == 1, f"{prop} filter mode drifted")
    require(int(settings["m_Aniso"]) == 1, f"{prop} anisotropy drifted")
    require(float(settings["m_MipBias"]) == 0.0, f"{prop} mip bias drifted")
    require(int(settings["m_WrapMode"]) == 0, f"{prop} wrap mode drifted")
    return {
        "textureType": 1 if prop == "_NormalMap" else 0,
        "sRGBTexture": int(texture["colorSpace"]) == 1,
        "mipmapEnabled": int(texture["mipCount"]) > 1,
        "streamingMipmaps": False,
        "streamingMipmapsPriority": 0,
        "filterMode": int(settings["m_FilterMode"]),
        "anisoLevel": int(settings["m_Aniso"]),
        "mipMapBias": float(settings["m_MipBias"]),
        "wrapU": int(settings["m_WrapMode"]),
        "wrapV": int(settings["m_WrapMode"]),
        "wrapW": int(settings["m_WrapMode"]),
    }


def material_bindings(rows: list[dict]) -> list[dict]:
    expected_by_property = {
        row["property"]: row["generatedCopies"][0]["guid"] for row in rows
    }
    bindings = []
    for path in sorted(MATERIAL_ROOT.glob("M_fx_endminm_gfx_*.mat")):
        text = path.read_text(encoding="utf-8-sig")
        found = {
            prop: guid
            for prop, guid in expected_by_property.items()
            if guid in text
        }
        if not found:
            continue
        require(found == expected_by_property,
                f"partial LitEffect texture family in {path.name}")
        texture_bindings = []
        for prop in EXPECTED_PROPERTIES:
            match = re.search(
                rf"-\s+{re.escape(prop)}:\s*\n"
                rf"\s*m_Texture:\s*\{{fileID:\s*(\d+),\s*"
                rf"guid:\s*([0-9a-f]{{32}}),\s*type:\s*(\d+)\}}",
                text,
                re.IGNORECASE,
            )
            require(match is not None,
                    f"material binding is missing for {path.name}:{prop}")
            require(int(match.group(1)) == 2_800_000,
                    f"material local file ID drifted for {path.name}:{prop}")
            require(match.group(2).lower() == expected_by_property[prop].lower(),
                    f"material GUID drifted for {path.name}:{prop}")
            require(int(match.group(3)) == 3,
                    f"material texture type drifted for {path.name}:{prop}")
            texture_bindings.append(
                {
                    "property": prop,
                    "guid": match.group(2),
                    "localFileId": int(match.group(1)),
                }
            )
        bindings.append(
            {
                "assetPath": project_asset_path(path),
                "sha256": sha256(path),
                "textureBindings": texture_bindings,
            }
        )
    require({Path(row["assetPath"]).name for row in bindings} == EXPECTED_MATERIALS,
            "LitEffect material binding set drifted")
    return bindings


def build(write: bool) -> tuple[dict, dict, dict[str, bytes]]:
    source = load_json(SOURCE_CONTRACT)
    require(
        source.get("schema") == "endfield.endminf-m27-suikuai-source-contract.v1",
        "unexpected M27 source contract schema",
    )
    require(
        source.get("status") == "source_closed_visual_ownership_unresolved",
        "M27 source contract is not source-closed",
    )
    textures = source["material"]["textures"]
    require([row["property"] for row in textures] == EXPECTED_PROPERTIES,
            "LitEffect source register order drifted")
    hashes_by_path_id = source_hashes_by_path_id(source)

    import_rows = []
    payload_rows = []
    payloads: dict[str, bytes] = {}
    for texture in textures:
        prop = texture["property"]
        name = texture["name"]
        path_id = int(texture["pathId"])
        path_id_hex = texture["pathIdHex"]
        descriptor_file = descriptor_path(name, path_id_hex)
        descriptor = load_json(descriptor_file)
        require(descriptor["m_Name"] == name, f"{prop} descriptor name drifted")
        require(int(descriptor["m_Width"]) == int(texture["width"]), f"{prop} width drifted")
        require(int(descriptor["m_Height"]) == int(texture["height"]), f"{prop} height drifted")
        require(int(descriptor["m_MipCount"]) == int(texture["mipCount"]), f"{prop} mips drifted")
        require(descriptor["m_TextureFormat"] == texture["format"], f"{prop} format drifted")
        require(int(descriptor["m_CompleteImageSize"]) == int(texture["payload"]["bytes"]),
                f"{prop} complete image size drifted")
        require(int(descriptor["m_MipsStripped"]) == 0,
                f"{prop} stripped mip count drifted")
        require(int(descriptor["m_ImageCount"]) == 1,
                f"{prop} image count drifted")
        require(int(descriptor["m_TextureDimension"]) == 2,
                f"{prop} texture dimension drifted")
        require(int(descriptor["m_StreamData"]["offset"]) == 0,
                f"{prop} stream offset drifted")
        require(int(descriptor["m_StreamData"]["size"]) == int(texture["payload"]["bytes"]),
                f"{prop} stream size drifted")

        payload_file = ROOT / texture["payload"]["path"]
        payload = payload_file.read_bytes()
        require(len(payload) == int(texture["payload"]["bytes"]), f"{prop} size drifted")
        require(sha256_bytes(payload).lower() == texture["payload"]["sha256"].lower(),
                f"{prop} payload hash drifted")
        layout = mip_layout(int(texture["width"]), int(texture["height"]), int(texture["mipCount"]))
        require(sum(row["byteSize"] for row in layout) == len(payload), f"{prop} mip layout drifted")

        png = generated_png(name, path_id_hex)
        guid = read_guid(png)
        file_name = png.name
        profile = import_profile(prop, texture, descriptor)
        source_object_hash = hashes_by_path_id[path_id]
        descriptor_sha = sha256(descriptor_file)
        import_row = {
            "fileName": file_name,
            "pathId": path_id,
            "sourceObjectHash": source_object_hash,
            "sourceDescriptorSha256": descriptor_sha,
            "width": int(texture["width"]),
            "height": int(texture["height"]),
            "textureFormat": FORMAT_IDS[texture["format"]],
            "mipCount": int(texture["mipCount"]),
            "completeImageSize": len(payload),
            "sourceColorSpace": int(texture["colorSpace"]),
            "importProfile": profile,
            "payloadOwner": "EndfieldNativeTexturePayloadPostprocessor",
        }
        import_rows.append(import_row)
        target = PAYLOAD_ROOT / f"sha256_{sha256_bytes(payload)}.bytes"
        payloads[project_asset_path(target)] = payload
        payload_rows.append(
            {
                "fileName": file_name,
                "name": name,
                "property": prop,
                "pathId": path_id,
                "sourceObjectHash": source_object_hash,
                "sourceDescriptorSha256": descriptor_sha,
                "payloadAssetPath": project_asset_path(target),
                "payloadSha256": sha256_bytes(payload),
                "payloadSize": len(payload),
                "width": int(texture["width"]),
                "height": int(texture["height"]),
                "textureFormat": FORMAT_IDS[texture["format"]],
                "dxgiFormat": DXGI_FORMATS[texture["format"]],
                "mipCount": int(texture["mipCount"]),
                "sourceColorSpace": int(texture["colorSpace"]),
                "importProfile": profile,
                "mipLayout": layout,
                "generatedCopies": [
                    {
                        "assetPath": project_asset_path(png),
                        "guid": guid,
                        "pngSha256": sha256(png),
                    }
                ],
            }
        )

    import_contract = {
        "schema": "endfield.character-texture-import-contract.v1",
        "status": "source_closed_current_build",
        "scope": "Endminf LitEffect M01/M27/M38 four-texture family",
        "sourceContract": root_relative_path(SOURCE_CONTRACT),
        "sourceContractSha256": sha256(SOURCE_CONTRACT),
        "textureCount": len(import_rows),
        "textures": import_rows,
    }
    import_rendered = json.dumps(import_contract, indent=2) + "\n"
    import_bytes = import_rendered.encode("utf-8")
    bindings = material_bindings(payload_rows)
    logical_bytes = sum(row["payloadSize"] for row in payload_rows)
    unique_bytes = sum(len(data) for data in payloads.values())
    payload_contract = {
        "schema": "endfield.native-texture-payload-contract.v2",
        "status": "source_closed_current_build",
        "scope": "Endminf LitEffect M01/M27/M38 exact BC5/BC7 compressed mip transport",
        "sourceContract": root_relative_path(SOURCE_CONTRACT),
        "sourceContractSha256": sha256(SOURCE_CONTRACT),
        "textureImportContractAssetPath": project_asset_path(IMPORT_CONTRACT),
        "textureImportContractSha256": sha256_bytes(import_bytes),
        "textureCount": len(payload_rows),
        "generatedCopyCount": sum(len(row["generatedCopies"]) for row in payload_rows),
        "logicalPayloadBytes": logical_bytes,
        "uniquePayloadCount": len(payloads),
        "uniquePayloadBytes": unique_bytes,
        "deduplicatedPayloadBytes": logical_bytes - unique_bytes,
        "materialBindings": bindings,
        "textures": payload_rows,
        "boundary": (
            "The exact installed compressed mip chains replace only the PNG-derived bytes "
            "at existing texture asset paths. Existing GUIDs, local file IDs, material PPtrs, "
            "particle transforms, authored curves, and runtime placement remain unchanged. "
            "This transport is source-contract and material-PPtr driven and has no live-capture "
            "dependency."
        ),
    }
    payload_bytes = (json.dumps(payload_contract, indent=2) + "\n").encode("utf-8")

    if write:
        PAYLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        expected = set()
        for asset_path, data in payloads.items():
            target = PROJECT / asset_path
            if not target.is_file() or target.read_bytes() != data:
                source_path = ROOT / next(
                    row["payload"]["path"]
                    for row in textures
                    if sha256_bytes(data).lower() == row["payload"]["sha256"].lower()
                )
                shutil.copyfile(source_path, target)
            expected.add(target.resolve())
        for stale in PAYLOAD_ROOT.glob("*.bytes"):
            if stale.resolve() not in expected:
                stale.unlink()
                meta = stale.with_name(stale.name + ".meta")
                if meta.exists():
                    meta.unlink()
        CONTRACT_ROOT.mkdir(parents=True, exist_ok=True)
        IMPORT_CONTRACT.write_bytes(import_bytes)
        PAYLOAD_CONTRACT.write_bytes(payload_bytes)
    return import_contract, payload_contract, payloads


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    import_contract, payload_contract, payloads = build(write=not args.check)
    if args.check:
        expected_import = (json.dumps(import_contract, indent=2) + "\n").encode("utf-8")
        expected_payload = (json.dumps(payload_contract, indent=2) + "\n").encode("utf-8")
        require(IMPORT_CONTRACT.is_file(), f"missing output: {IMPORT_CONTRACT}")
        require(PAYLOAD_CONTRACT.is_file(), f"missing output: {PAYLOAD_CONTRACT}")
        require(IMPORT_CONTRACT.read_bytes() == expected_import,
                "published import contract drifted")
        require(PAYLOAD_CONTRACT.read_bytes() == expected_payload,
                "published payload contract drifted")
        for asset_path, data in payloads.items():
            target = PROJECT / asset_path
            require(target.is_file() and target.read_bytes() == data,
                    f"published payload drifted: {target}")
    print(
        f"textures={payload_contract['textureCount']} "
        f"bytes={payload_contract['logicalPayloadBytes']} "
        f"properties={','.join(row['property'] for row in payload_contract['textures'])} "
        f"check={args.check}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
