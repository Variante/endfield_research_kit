#!/usr/bin/env python3
"""Fail-closed verifier for Endminf M14's exact native BC7 mip chain."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[1]
RELATIVE_ROOT = Path(
    "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads/Endminf"
)
IMPORTER = Path(
    "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery/"
    "EndfieldEndminfOverviewEffectImporter.cs"
)
STEM = "T_fx_glow_105_D_pCF334932EF9AA445.texture2d.bc7"
EXPECTED_SHA256 = "FFD3A6F707D0D0A6C92D3012BEC11A41B59AB4949E377558F426EAD4AD22D672"
EXPECTED_PATH_ID = -3516386400929143739
EXPECTED_SOURCE_FILE = "CAB-c0944558649283ebb964e4f3fb2a17a8"
EXPECTED_SOURCE_OFFSET = 847897551
EXPECTED_META = {
    STEM + ".meta": ("b3db05a7d22193f4e82016b9b3ae5940", "DefaultImporter"),
    STEM + ".manifest.json.meta": (
        "ac75303abfa3e5943abaef9cc0d52ece",
        "TextScriptImporter",
    ),
}
GUID_RE = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def expected_mips(width: int, height: int, count: int) -> list[dict[str, int]]:
    rows = []
    offset = 0
    for mip in range(count):
        mip_width = max(1, width >> mip)
        mip_height = max(1, height >> mip)
        byte_size = max(1, (mip_width + 3) // 4) * max(1, (mip_height + 3) // 4) * 16
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


def verify(project: Path = PROJECT) -> dict:
    root = project / RELATIVE_ROOT
    payload_path = root / STEM
    manifest_path = root / (STEM + ".manifest.json")
    require(payload_path.is_file(), f"missing exact M14 payload: {payload_path}")
    require(manifest_path.is_file(), f"missing exact M14 manifest: {manifest_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    descriptor = {
        "schema": "animestudio.texture2d-native-payload.v1",
        "type": "Texture2D",
        "name": "T_fx_glow_105_D",
        "pathId": EXPECTED_PATH_ID,
        "sourceFile": EXPECTED_SOURCE_FILE,
        "sourceOffset": EXPECTED_SOURCE_OFFSET,
        "width": 256,
        "height": 128,
        "completeImageSize": 43728,
        "mipsStripped": 0,
        "format": "BC7",
        "formatValue": 25,
        "mipCount": 9,
        "imageCount": 1,
        "textureDimension": 2,
        "colorSpace": 1,
    }
    for key, expected in descriptor.items():
        require(
            manifest.get(key) == expected,
            f"M14 manifest {key} drifted: {manifest.get(key)!r} != {expected!r}",
        )

    payload = manifest.get("payload")
    require(isinstance(payload, dict), "M14 manifest payload row is missing")
    require(payload.get("file") == STEM, "M14 payload filename drifted or escaped its root")
    require(payload.get("bytes") == 43728, "M14 payload byte count drifted")
    require(payload.get("sha256") == EXPECTED_SHA256, "M14 manifest SHA-256 drifted")
    require(
        payload.get("layout")
        == "unity_texture2d_resource_mip_chain_largest_to_smallest",
        "M14 payload layout identity drifted",
    )
    require(payload.get("layoutValidated") is True, "M14 payload layout is not validated")
    expected_layout = expected_mips(256, 128, 9)
    require(payload.get("mipDimensions") == expected_layout, "M14 BC7 mip layout drifted")
    require(
        expected_layout[-1]["offset"] + expected_layout[-1]["byteSize"] == 43728,
        "internal M14 BC7 layout expectation is inconsistent",
    )
    require(payload_path.stat().st_size == 43728, "M14 payload file length drifted")
    actual_sha = sha256(payload_path)
    require(actual_sha == EXPECTED_SHA256, f"M14 payload SHA-256 drifted: {actual_sha}")
    require(
        manifest.get("textureSettings")
        == {
            "filterMode": 1,
            "aniso": 1,
            "mipBias": 0.0,
            "wrapU": 0,
            "wrapV": 0,
            "wrapW": 0,
        },
        "M14 texture settings drifted",
    )
    require(
        manifest.get("streamData")
        == {
            "offset": 0,
            "size": 43728,
            "path": (
                "archive:/CAB-c0944558649283ebb964e4f3fb2a17a8/"
                "CAB-c0944558649283ebb964e4f3fb2a17a8.resS"
            ),
        },
        "M14 source stream provenance drifted",
    )

    for name, (expected_guid, importer_name) in EXPECTED_META.items():
        meta_path = root / name
        require(meta_path.is_file(), f"missing force-tracked M14 meta: {meta_path}")
        text = meta_path.read_text(encoding="utf-8-sig")
        match = GUID_RE.search(text)
        require(match is not None, f"missing Unity GUID in {meta_path}")
        require(match.group(1) == expected_guid, f"Unity GUID drifted in {meta_path}")
        require(importer_name + ":" in text, f"Unity importer drifted in {meta_path}")

    importer_path = project / IMPORTER
    require(importer_path.is_file(), f"missing M14 importer: {importer_path}")
    importer = importer_path.read_text(encoding="utf-8-sig")
    for witness in (
        "0xCF334932EF9AA445UL",
        EXPECTED_SHA256,
        "ValidateM14NativeMipLayout(payloadRow)",
        "loaded.GetRawTextureData()",
    ):
        require(witness in importer, f"M14 importer lost fail-closed witness: {witness}")

    return {
        "status": "pass",
        "pathId": EXPECTED_PATH_ID,
        "payloadSha256": actual_sha,
        "payloadBytes": payload_path.stat().st_size,
        "width": 256,
        "height": 128,
        "format": "BC7",
        "mipCount": 9,
        "forceTrack": [
            (RELATIVE_ROOT / STEM).as_posix(),
            (RELATIVE_ROOT / (STEM + ".meta")).as_posix(),
            (RELATIVE_ROOT / (STEM + ".manifest.json")).as_posix(),
            (RELATIVE_ROOT / (STEM + ".manifest.json.meta")).as_posix(),
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", type=Path, default=PROJECT)
    args = parser.parse_args()
    print(json.dumps(verify(args.project_root.resolve()), indent=2))


if __name__ == "__main__":
    main()
