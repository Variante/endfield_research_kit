#!/usr/bin/env python3
"""Verify exact installed payloads and the bounded priority-surface extension."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from character_native_payload_selection import (
    EYE_SHADOW_PAYLOAD_NAMES,
    build_priority_surface_selection,
    is_baseline_face_eye_payload,
)


PROJECT = Path(__file__).resolve().parents[1]
CENSUS_ROOT = PROJECT / "scratch/character_recovery/all_character_native_texture_census"
CENSUS = CENSUS_ROOT / "report.json"
FULL_RAW = CENSUS_ROOT / "raw_payloads/Texture2D"
IMPORT_CONTRACT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
    / "character_texture_import_contract.json"
)
PAYLOAD_CONTRACT = IMPORT_CONTRACT.with_name("high_impact_texture_payload_contract.json")
PAYLOAD_ROOT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads"
    / "CompressedMipChains"
)
CHARACTER_ROOT = (
    PROJECT / "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable"
)
LEGACY_PAYLOAD_ROOT = PAYLOAD_ROOT.with_name("FaceAndEyes")
POSTPROCESSOR = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Editor/CharacterRecovery"
    / "EndfieldNativeTexturePayloadPostprocessor.cs"
)
REPORT = (
    PROJECT
    / "scratch/character_recovery/priority_native_surface_payload/payload_audit_report.json"
)
REPORT_MD = REPORT.with_suffix(".md")

GUID_RE = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)
FORMAT_NAMES = {4: "RGBA32", 10: "DXT1", 25: "BC7", 27: "BC5"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def raw_name(row: dict) -> str:
    suffix = f"p{int(row['pathId']) & ((1 << 64) - 1):016X}"
    return f"{row['name']}_{suffix}.tex"


def read_guid(png: Path) -> str:
    text = png.with_name(png.name + ".meta").read_text(encoding="utf-8-sig")
    match = GUID_RE.search(text)
    assert match is not None, png
    return match.group(1)


def current_playable_copies(file_name: str) -> list[Path]:
    return sorted(
        CHARACTER_ROOT.rglob(file_name),
        key=lambda path: path.as_posix().casefold(),
    )


def main() -> None:
    census = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    assert census["schema"] == "endfield.all-character-native-texture-census.v1"
    assert census["status"] == "pass"
    census_count = int(census["resolvedTextureCount"])
    assert census["requestedTextureCount"] == census_count
    assert census_count == len(census["textures"])
    assert census["missingDumpCount"] == 0
    assert census["descriptorDriftCount"] == 0

    census_rows = census["textures"]
    census_by_path_id = {int(row["pathId"]): row for row in census_rows}

    requested_payload_bytes = sum(row["completeImageSize"] for row in census_rows)
    format_counts = Counter(int(row["format"]) for row in census_rows)

    # The current census also sees newly exported Liino and Jsspsi face/iris
    # descriptors. They are not part of the prior 83-row baseline subset;
    # Liino's two exact rows are accounted for by the explicit extension below.
    baseline_rows = [
        row
        for row in census_rows
        if is_baseline_face_eye_payload(row)
        and not str(row["name"]).startswith(("T_actor_liino_", "T_actor_jsspsi_"))
    ]
    assert len(baseline_rows) == 83
    assert sum(row["completeImageSize"] for row in baseline_rows) == 62_894_928
    priority = build_priority_surface_selection(census_rows)
    assert len(priority) == 110
    assert sum(census_by_path_id[path_id]["completeImageSize"] for path_id in priority) == 317_777_152
    assert not ({int(row["pathId"]) for row in baseline_rows} & set(priority))

    import_contract = json.loads(IMPORT_CONTRACT.read_text(encoding="utf-8-sig"))
    assert import_contract["schema"] == "endfield.character-texture-import-contract.v1"
    assert import_contract["textureCount"] == census_count
    import_by_file = {row["fileName"]: row for row in import_contract["textures"]}
    owners = Counter(row["payloadOwner"] for row in import_contract["textures"])
    assert owners == {
        "EndfieldNativeTexturePayloadPostprocessor": 215,
        "EndfieldEyeShadowBc7PayloadPostprocessor": 2,
        "descriptor_only_png_top_level": census_count - 217,
    }

    contract = json.loads(PAYLOAD_CONTRACT.read_text(encoding="utf-8-sig"))
    assert contract["schema"] == "endfield.native-texture-payload-contract.v2"
    assert contract["status"] == "source_closed_current_build"
    assert contract["textureImportContractSha256"] == sha256(IMPORT_CONTRACT)
    assert contract["baselineFaceEye"] == {
        "textureCount": 83,
        "generatedCopyCount": 175,
        "logicalPayloadBytes": 62_894_928,
    }
    assert contract["addedPrioritySurfaces"]["textureCount"] == 110
    assert contract["addedPrioritySurfaces"]["generatedCopyCount"] == 223
    assert contract["addedPrioritySurfaces"]["logicalPayloadBytes"] == 317_777_152
    assert contract["newCharacterSurfaces"] == {
        "character": "Liino",
        "textureCount": 22,
        "generatedCopyCount": 22,
        "logicalPayloadBytes": 63_963_776,
        "selectionClass": "liino_character_surface",
    }
    assert contract["textureCount"] == 215 == len(contract["textures"])
    assert contract["generatedCopyCount"] == 420
    assert contract["logicalPayloadBytes"] == 444_635_856
    assert contract["uniquePayloadCount"] == 213
    assert contract["uniquePayloadBytes"] == 442_888_176
    assert contract["deduplicatedPayloadBytes"] == 1_747_680

    contract_path_ids = {int(row["pathId"]) for row in contract["textures"]}
    expected_baseline_path_ids = {
        int(row["pathId"])
        for row in baseline_rows
        if current_playable_copies(raw_name(row).replace(".tex", ".png"))
    }
    expected_priority_path_ids = {
        path_id
        for path_id in priority
        if current_playable_copies(
            raw_name(census_by_path_id[path_id]).replace(".tex", ".png")
        )
    }
    expected_liino_path_ids = {
        int(row["pathId"])
        for row in census_rows
        if str(row["name"]).startswith("T_actor_liino_")
        or str(row["name"]).startswith("T_item_widget_liino_")
    }
    expected_path_ids = (
        expected_baseline_path_ids | expected_priority_path_ids | expected_liino_path_ids
    )
    assert contract_path_ids == expected_path_ids
    priority_contract_rows = [
        row
        for row in contract["textures"]
        if row["selectionClass"] == "priority_character_surface"
    ]
    assert {
        int(row["pathId"]) for row in priority_contract_rows
    } == expected_priority_path_ids
    liino_contract_rows = [
        row for row in contract["textures"]
        if row["selectionClass"] == "liino_character_surface"
    ]
    assert {int(row["pathId"]) for row in liino_contract_rows} == expected_liino_path_ids

    copy_count = 0
    payload_paths_by_hash: dict[str, set[str]] = defaultdict(set)
    payload_layouts_by_hash: dict[str, set[tuple[int, int, int, int, int, int]]] = (
        defaultdict(set)
    )
    character_path_ids: dict[str, set[int]] = defaultdict(set)
    for row in contract["textures"]:
        source = import_by_file[row["fileName"]]
        assert source["payloadOwner"] == "EndfieldNativeTexturePayloadPostprocessor"
        for field in (
            "pathId",
            "sourceObjectHash",
            "sourceDescriptorSha256",
            "width",
            "height",
            "textureFormat",
            "mipCount",
            "sourceColorSpace",
            "importProfile",
        ):
            assert row[field] == source[field], (row["fileName"], field)
        assert row["payloadSize"] == source["completeImageSize"]

        raw = FULL_RAW / raw_name(census_by_path_id[int(row["pathId"])])
        assert raw.exists(), raw
        payload = PROJECT / row["payloadAssetPath"]
        assert payload.exists()
        assert payload.parent == PAYLOAD_ROOT
        assert payload.name == f"sha256_{row['payloadSha256']}.bytes"
        assert payload.stat().st_size == row["payloadSize"]
        assert sha256(raw) == row["payloadSha256"]
        assert sha256(payload) == row["payloadSha256"]
        payload_paths_by_hash[row["payloadSha256"]].add(row["payloadAssetPath"])
        payload_layouts_by_hash[row["payloadSha256"]].add(
            (
                int(row["width"]),
                int(row["height"]),
                int(row["textureFormat"]),
                int(row["mipCount"]),
                int(row["sourceColorSpace"]),
                int(row["payloadSize"]),
            )
        )

        if row["selectionClass"] == "priority_character_surface":
            evidence = priority[int(row["pathId"])]
            assert row["impactRank"] == evidence["impactRank"]
            assert row["priorityCharacters"] == evidence["characters"]
            assert row["originalMaterialReferences"] == evidence["evidence"]
            for character in row["priorityCharacters"]:
                character_path_ids[character].add(int(row["pathId"]))
        elif row["selectionClass"] == "liino_character_surface":
            assert row["impactRank"] == 1
            assert row["priorityCharacters"] == ["Liino"]
            assert not row["originalMaterialReferences"]
            character_path_ids["Liino"].add(int(row["pathId"]))
        else:
            assert row["selectionClass"] == "baseline_face_eye"
            assert not row["priorityCharacters"]
            assert not row["originalMaterialReferences"]

        expected_copy_paths = {
            path.relative_to(PROJECT).as_posix()
            for path in current_playable_copies(row["fileName"])
        }
        assert {copy["assetPath"] for copy in row["generatedCopies"]} == expected_copy_paths
        for copy in row["generatedCopies"]:
            png = PROJECT / copy["assetPath"]
            assert png.exists()
            assert png.name.casefold() == row["fileName"].casefold()
            assert sha256(png) == copy["pngSha256"]
            assert read_guid(png) == copy["guid"]
            copy_count += 1
    assert copy_count == contract["generatedCopyCount"]
    assert all(len(paths) == 1 for paths in payload_paths_by_hash.values())
    assert all(len(layouts) == 1 for layouts in payload_layouts_by_hash.values())
    assert len(payload_paths_by_hash) == contract["uniquePayloadCount"]

    physical_files = {path.resolve() for path in PAYLOAD_ROOT.glob("*.bytes")}
    contract_files = {
        (PROJECT / paths.copy().pop()).resolve()
        for paths in payload_paths_by_hash.values()
    }
    assert physical_files == contract_files
    assert sum(path.stat().st_size for path in physical_files) == contract["uniquePayloadBytes"]
    assert not list(LEGACY_PAYLOAD_ROOT.glob("*.bytes"))

    source = POSTPROCESSOR.read_text(encoding="utf-8-sig")
    for fragment in (
        "EndfieldNativeTexturePayloadPostprocessor",
        "endfield.native-texture-payload-contract.v2",
        "sourceObjectHash",
        "sourceDescriptorSha256",
        "pngSha256",
        "AssetDatabase.AssetPathToGUID",
        "LoadRawTextureData(payload.Bytes)",
        "texture.Apply(false, false)",
        "TextureImporterCompression.Uncompressed",
        "EndfieldNativeTexturePayloadValidator",
    ):
        assert fragment in source
    assert "FromBase64String" not in source

    character_summary = {}
    for character in sorted(character_path_ids, key=str.casefold):
        path_ids = character_path_ids[character]
        character_summary[character] = {
            "textureObjectCount": len(path_ids),
            "logicalPayloadBytes": sum(
                int(census_by_path_id[path_id]["completeImageSize"])
                for path_id in path_ids
            ),
        }
    audit = {
        "schema": "endfield.priority-native-surface-payload-audit.v1",
        "status": "pass",
        "fullRawExport": {
            "requestedTextureCount": len(census_rows),
            "requestedPayloadBytes": requested_payload_bytes,
            "formatCounts": {
                FORMAT_NAMES[key]: format_counts[key] for key in sorted(format_counts)
            },
        },
        "priorExactSubset": {
            "faceEyeTextureCount": 83,
            "faceEyeGeneratedCopyCount": 175,
            "faceEyeLogicalPayloadBytes": 62_894_928,
            "separateEyeMaskTextureCount": len(EYE_SHADOW_PAYLOAD_NAMES),
        },
        "addedPrioritySurfaces": {
            **contract["addedPrioritySurfaces"],
            "characters": character_summary,
            "identities": [
                {
                    "impactRank": row["impactRank"],
                    "name": row["name"],
                    "pathId": row["pathId"],
                    "textureFormat": row["textureFormat"],
                    "mipCount": row["mipCount"],
                    "payloadBytes": row["payloadSize"],
                    "characters": row["priorityCharacters"],
                    "materialReferenceCount": len(row["originalMaterialReferences"]),
                }
                for row in priority_contract_rows
            ],
        },
        "newCharacterSurfaces": contract["newCharacterSurfaces"],
        "combinedNativePayloadContract": {
            "textureObjectCount": contract["textureCount"],
            "generatedCopyCount": contract["generatedCopyCount"],
            "logicalPayloadBytes": contract["logicalPayloadBytes"],
            "uniquePayloadCount": contract["uniquePayloadCount"],
            "uniquePayloadBytes": contract["uniquePayloadBytes"],
            "deduplicatedPayloadBytes": contract["deduplicatedPayloadBytes"],
            "contractSha256": sha256(PAYLOAD_CONTRACT),
            "textureImportContractSha256": sha256(IMPORT_CONTRACT),
        },
        "boundary": contract["boundary"],
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(audit, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Priority Native Surface Payload Audit",
        "",
        "- Status: pass",
        f"- Added: 110 Texture2D objects / 223 PNG GUID owners / {317_777_152:,} logical bytes",
        "- Source: exact material Texture PPtrs for Li Zhiyan, Last Rite, Zhuang Fangyi, and Wulfa",
        f"- New Liino exact payloads: 22 objects / 22 PNG GUID owners / {63_963_776:,} logical bytes",
        f"- Combined: 215 objects / 420 PNG GUID owners / {444_635_856:,} logical bytes",
        f"- Deduplicated storage: 213 payload files / {442_888_176:,} bytes",
        "- Existing separate eye masks retained: 2 objects / 49 PNG copies",
        "",
    ]
    REPORT_MD.write_text("\n".join(lines), encoding="utf-8")
    print(
        "PASS: source-gated native payloads preserve 83 current face/eye objects, "
        "110 impact-ranked priority-character surfaces, and 22 exact Liino "
        "surfaces as 213 unique compressed mip-chain files."
    )


if __name__ == "__main__":
    main()
