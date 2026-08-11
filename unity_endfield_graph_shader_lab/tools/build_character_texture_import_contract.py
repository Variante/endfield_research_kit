#!/usr/bin/env python3
"""Build exact TextureImporter profiles from installed character Texture2D dumps."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from character_native_payload_selection import (
    EYE_SHADOW_PAYLOAD_NAMES,
    build_priority_surface_selection,
    is_baseline_face_eye_payload,
)


PROJECT = Path(__file__).resolve().parents[1]
SOURCE_REPORT = (
    PROJECT
    / "scratch/character_recovery/all_character_native_texture_census/report.json"
)
OUTPUT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
    / "character_texture_import_contract.json"
)

def payload_owner(item: dict, priority_surface_path_ids: set[int]) -> str:
    name = str(item["name"])
    if name in EYE_SHADOW_PAYLOAD_NAMES:
        return "EndfieldEyeShadowBc7PayloadPostprocessor"
    if (
        is_baseline_face_eye_payload(item)
        or int(item["pathId"]) in priority_surface_path_ids
    ):
        return "EndfieldNativeTexturePayloadPostprocessor"
    return "descriptor_only_png_top_level"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def main() -> None:
    source = json.loads(SOURCE_REPORT.read_text(encoding="utf-8-sig"))
    if source.get("schema") != "endfield.all-character-native-texture-census.v1":
        raise RuntimeError("unexpected source texture census schema")
    if (
        source.get("status") != "pass"
        or source.get("requestedTextureCount") != 853
        or source.get("resolvedTextureCount") != 853
        or source.get("missingDumpCount") != 0
    ):
        raise RuntimeError("source texture census is incomplete")

    priority_surface_selection = build_priority_surface_selection(source["textures"])
    if len(priority_surface_selection) != 110:
        raise RuntimeError(
            "priority-character material-PPtr selection drifted: expected 110 "
            f"objects, found {len(priority_surface_selection)}"
        )
    priority_surface_path_ids = set(priority_surface_selection)

    rows = []
    for item in source["textures"]:
        dump = Path(item["dumpPath"])
        if not dump.exists():
            raise RuntimeError(f"missing source descriptor dump: {dump}")
        if sha256(dump) != item["dumpSha256"].upper():
            raise RuntimeError(f"source descriptor dump hash drifted: {dump}")
        suffix = f"p{int(item['pathId']) & ((1 << 64) - 1):016X}"
        rows.append(
            {
                "fileName": f"{item['name']}_{suffix}.png",
                "name": item["name"],
                "pathId": int(item["pathId"]),
                "source": item["source"],
                "sourceOffset": int(item["offset"]),
                "sourceObjectHash": item["sourceHash"],
                "sourceDescriptorDump": str(dump),
                "sourceDescriptorSha256": item["dumpSha256"].upper(),
                "width": int(item["width"]),
                "height": int(item["height"]),
                "textureFormat": int(item["format"]),
                "mipCount": int(item["mipCount"]),
                "completeImageSize": int(item["completeImageSize"]),
                "sourceColorSpace": int(item["colorSpace"]),
                "importProfile": {
                    # UnityEngine.TextureColorSpace is serialized as
                    # Linear=0, sRGB=1 in the stock 2021.3.34f1 runtime that
                    # the current Endfield fork derives from.  This is the
                    # Texture2D object enum, not PlayerSettings ColorSpace
                    # (Gamma=0, Linear=1).
                    "sRGBTexture": item["colorSpace"] == 1,
                    "mipmapEnabled": item["mipCount"] > 1,
                    "streamingMipmaps": bool(item["streamingMipmaps"]),
                    "streamingMipmapsPriority": int(item["streamingPriority"]),
                    "filterMode": int(item["filterMode"]),
                    "anisoLevel": int(item["aniso"]),
                    "mipMapBias": float(item["mipBias"]),
                    "wrapU": int(item["wrapU"]),
                    "wrapV": int(item["wrapV"]),
                    "wrapW": int(item["wrapW"]),
                },
                "generatedCopyCount": len(item["generatedCopies"]),
                "payloadOwner": payload_owner(item, priority_surface_path_ids),
            }
        )
    rows.sort(key=lambda row: row["fileName"].casefold())

    payload = {
        "schema": "endfield.character-texture-import-contract.v1",
        "status": "source_closed_current_build",
        "scope": (
            "853 exact installed Texture2D objects referenced by all encoded PNG "
            "filenames in the current 31-character generated roster"
        ),
        "sourceReport": str(SOURCE_REPORT.resolve()),
        "sourceReportSha256": sha256(SOURCE_REPORT),
        "textureCount": len(rows),
        "textures": rows,
        "boundary": (
            "All importer descriptor fields come from installed Texture2D type trees. "
            "The close-up face/iris/emotion subset, 110 original-material-PPtr-ranked "
            "priority-character surface objects, and two separately owned eye-shadow "
            "masks preserve exact installed payloads. Other PNG assets retain decoded "
            "top-level pixels and Unity still regenerates their lower mip texels."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(f"sha256={sha256(OUTPUT)}")


if __name__ == "__main__":
    main()
