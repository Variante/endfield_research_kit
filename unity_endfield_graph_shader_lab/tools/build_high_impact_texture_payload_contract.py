#!/usr/bin/env python3
"""Build exact compressed mip payloads for close-ups and priority surfaces."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

from character_native_payload_selection import (
    EYE_SHADOW_PAYLOAD_NAMES,
    build_priority_surface_selection,
    is_baseline_face_eye_payload,
)


PROJECT = Path(__file__).resolve().parents[1]
CENSUS_ROOT = PROJECT / "scratch/character_recovery/all_character_native_texture_census"
SOURCE_REPORT = CENSUS_ROOT / "report.json"
RAW_ROOT = CENSUS_ROOT / "raw_payloads/Texture2D"
IMPORT_CONTRACT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/RenderParameters"
    / "character_texture_import_contract.json"
)
PAYLOAD_ASSET_ROOT = (
    PROJECT
    / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/TexturePayloads"
    / "CompressedMipChains"
)
CHARACTER_ROOT = (
    PROJECT / "Assets/EndfieldGraphShaderLab/Generated/Characters"
)
LEGACY_PAYLOAD_ASSET_ROOT = PAYLOAD_ASSET_ROOT.with_name("FaceAndEyes")
OUTPUT = IMPORT_CONTRACT.with_name("high_impact_texture_payload_contract.json")
GUID_RE = re.compile(r"^guid:\s*([0-9a-f]{32})\s*$", re.MULTILINE)

EXPECTED_SOURCE_BASELINE_TEXTURES = 83
EXPECTED_SOURCE_PRIORITY_TEXTURES = 110
EXPECTED_BASELINE_TEXTURES = 83
EXPECTED_BASELINE_COPIES = 175
EXPECTED_BASELINE_LOGICAL_BYTES = 62_894_928
EXPECTED_PRIORITY_TEXTURES = 110
EXPECTED_PRIORITY_COPIES = 223
EXPECTED_PRIORITY_LOGICAL_BYTES = 317_777_152


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def asset_path(path: Path) -> str:
    return path.relative_to(PROJECT).as_posix()


def read_guid(path: Path) -> str:
    meta = path.with_name(path.name + ".meta")
    if not meta.exists():
        raise RuntimeError(f"missing PNG meta/GUID: {meta}")
    match = GUID_RE.search(meta.read_text(encoding="utf-8-sig"))
    if match is None:
        raise RuntimeError(f"missing GUID field: {meta}")
    return match.group(1)


def raw_payload_path(source: dict) -> Path:
    suffix = f"p{int(source['pathId']) & ((1 << 64) - 1):016X}"
    return RAW_ROOT / f"{source['name']}_{suffix}.tex"


def current_generated_copies(file_name: str) -> list[Path]:
    """Discover current roster copies instead of trusting a stale census list.

    The source Texture2D census is object-level evidence and remains valid when
    the playable roster changes. Liino adds new generated PNG paths without
    changing those original texture objects. Keep this discovery under the
    Unity postprocessor's Playable-only authorization root. Search that root
    recursively because effect/deco textures are not confined to `Textures/`.
    """

    copies = (CHARACTER_ROOT / "Playable").rglob(file_name)
    return sorted(set(copies), key=lambda path: asset_path(path).casefold())


def main() -> None:
    census = json.loads(SOURCE_REPORT.read_text(encoding="utf-8-sig"))
    if census.get("schema") != "endfield.all-character-native-texture-census.v1":
        raise RuntimeError("unexpected source texture census schema")
    if (
        census.get("status") != "pass"
        or census.get("requestedTextureCount") != 853
        or census.get("resolvedTextureCount") != 853
        or census.get("missingDumpCount") != 0
    ):
        raise RuntimeError("source texture census is incomplete")

    import_contract = json.loads(IMPORT_CONTRACT.read_text(encoding="utf-8-sig"))
    if (
        import_contract.get("schema")
        != "endfield.character-texture-import-contract.v1"
        or import_contract.get("textureCount") != 853
    ):
        raise RuntimeError("character TextureImporter contract is incomplete")
    import_by_file = {row["fileName"]: row for row in import_contract["textures"]}

    baseline = [row for row in census["textures"] if is_baseline_face_eye_payload(row)]
    priority = build_priority_surface_selection(census["textures"])
    if len(baseline) != EXPECTED_SOURCE_BASELINE_TEXTURES:
        raise RuntimeError(
            f"expected {EXPECTED_SOURCE_BASELINE_TEXTURES} baseline textures, "
            f"found {len(baseline)}"
        )
    if len(priority) != EXPECTED_SOURCE_PRIORITY_TEXTURES:
        raise RuntimeError(
            f"expected {EXPECTED_SOURCE_PRIORITY_TEXTURES} priority textures, "
            f"found {len(priority)}"
        )
    selected = baseline + [
        row for row in census["textures"] if int(row["pathId"]) in priority
    ]
    if len({int(row["pathId"]) for row in selected}) != len(selected):
        raise RuntimeError("baseline and priority payload selections overlap")

    PAYLOAD_ASSET_ROOT.mkdir(parents=True, exist_ok=True)
    rows = []
    expected_payload_names: set[str] = set()
    copied_payload_hashes: dict[str, Path] = {}
    payload_layouts_by_hash: dict[str, tuple[int, int, int, int, int, int]] = {}
    class_totals = {
        "baseline_face_eye": Counter(),
        "priority_character_surface": Counter(),
    }
    for source in selected:
        path_suffix = f"p{int(source['pathId']) & ((1 << 64) - 1):016X}"
        file_name = f"{source['name']}_{path_suffix}.png"
        copy_paths = current_generated_copies(file_name)
        if not copy_paths:
            continue
        raw = raw_payload_path(source)
        if not raw.exists():
            raise RuntimeError(f"missing exact raw Texture2D payload: {raw}")
        expected_size = int(source["completeImageSize"])
        if raw.stat().st_size != expected_size:
            raise RuntimeError(
                f"payload size drifted for {raw}: {raw.stat().st_size} != {expected_size}"
            )

        import_row = import_by_file.get(file_name)
        if import_row is None:
            raise RuntimeError(f"missing TextureImporter source row: {file_name}")
        source_fields = (
            ("sourceObjectHash", source["sourceHash"]),
            ("sourceDescriptorSha256", source["dumpSha256"].upper()),
            ("width", int(source["width"])),
            ("height", int(source["height"])),
            ("textureFormat", int(source["format"])),
            ("mipCount", int(source["mipCount"])),
            ("completeImageSize", expected_size),
            ("sourceColorSpace", int(source["colorSpace"])),
            ("payloadOwner", "EndfieldNativeTexturePayloadPostprocessor"),
        )
        for field, expected in source_fields:
            if import_row.get(field) != expected:
                raise RuntimeError(
                    f"TextureImporter source gate drifted for {file_name}.{field}: "
                    f"{import_row.get(field)!r} != {expected!r}"
                )

        payload_sha = sha256(raw)
        payload_layout = (
            int(source["width"]),
            int(source["height"]),
            int(source["format"]),
            int(source["mipCount"]),
            int(source["colorSpace"]),
            expected_size,
        )
        target = PAYLOAD_ASSET_ROOT / f"sha256_{payload_sha}.bytes"
        if payload_sha not in copied_payload_hashes:
            shutil.copyfile(raw, target)
            copied_payload_hashes[payload_sha] = target
            payload_layouts_by_hash[payload_sha] = payload_layout
        elif sha256(copied_payload_hashes[payload_sha]) != payload_sha:
            raise RuntimeError(f"deduplicated payload hash drifted: {target}")
        elif payload_layouts_by_hash[payload_sha] != payload_layout:
            raise RuntimeError(
                "identical payload bytes crossed an incompatible texture layout: "
                f"{payload_sha} {payload_layouts_by_hash[payload_sha]} != "
                f"{payload_layout}"
            )
        expected_payload_names.add(target.name)

        copies = []
        for png in copy_paths:
            actual_png_sha = sha256(png)
            copies.append(
                {
                    "assetPath": asset_path(png),
                    "guid": read_guid(png),
                    "pngSha256": actual_png_sha,
                }
            )
        copies.sort(key=lambda row: row["assetPath"].casefold())

        path_id = int(source["pathId"])
        if path_id in priority:
            selection_class = "priority_character_surface"
            impact_rank = int(priority[path_id]["impactRank"])
            characters = priority[path_id]["characters"]
            evidence = priority[path_id]["evidence"]
        else:
            selection_class = "baseline_face_eye"
            impact_rank = 1
            characters = []
            evidence = []
        class_totals[selection_class]["textures"] += 1
        class_totals[selection_class]["copies"] += len(copies)
        class_totals[selection_class]["logicalBytes"] += expected_size

        rows.append(
            {
                "fileName": file_name,
                "name": source["name"],
                "pathId": path_id,
                "selectionClass": selection_class,
                "impactRank": impact_rank,
                "priorityCharacters": characters,
                "originalMaterialReferences": evidence,
                "sourceObjectHash": source["sourceHash"],
                "sourceDescriptorSha256": source["dumpSha256"].upper(),
                "payloadAssetPath": asset_path(target),
                "payloadSha256": payload_sha,
                "payloadSize": expected_size,
                "width": int(source["width"]),
                "height": int(source["height"]),
                "textureFormat": int(source["format"]),
                "mipCount": int(source["mipCount"]),
                "sourceColorSpace": int(source["colorSpace"]),
                "importProfile": import_row["importProfile"],
                "generatedCopies": copies,
            }
        )

    baseline_totals = class_totals["baseline_face_eye"]
    priority_totals = class_totals["priority_character_surface"]
    expected_totals = (
        (baseline_totals, EXPECTED_BASELINE_TEXTURES, EXPECTED_BASELINE_COPIES,
         EXPECTED_BASELINE_LOGICAL_BYTES, "baseline"),
        (priority_totals, EXPECTED_PRIORITY_TEXTURES, EXPECTED_PRIORITY_COPIES,
         EXPECTED_PRIORITY_LOGICAL_BYTES, "priority"),
    )
    for totals, textures, copies, logical_bytes, label in expected_totals:
        actual = (totals["textures"], totals["copies"], totals["logicalBytes"])
        expected = (textures, copies, logical_bytes)
        if actual != expected:
            raise RuntimeError(f"{label} payload totals drifted: {actual} != {expected}")

    for stale in PAYLOAD_ASSET_ROOT.glob("*.bytes"):
        if stale.name not in expected_payload_names:
            stale.unlink()
            meta = stale.with_name(stale.name + ".meta")
            if meta.exists():
                meta.unlink()
    if LEGACY_PAYLOAD_ASSET_ROOT.exists():
        for stale in LEGACY_PAYLOAD_ASSET_ROOT.glob("*.bytes"):
            stale.unlink()
            meta = stale.with_name(stale.name + ".meta")
            if meta.exists():
                meta.unlink()

    rows.sort(key=lambda row: (row["impactRank"], row["fileName"].casefold()))
    logical_payload_bytes = sum(int(row["payloadSize"]) for row in rows)
    generated_copy_count = sum(len(row["generatedCopies"]) for row in rows)
    unique_payload_bytes = sum(path.stat().st_size for path in copied_payload_hashes.values())
    rank_counts = Counter(
        row["impactRank"]
        for row in rows
        if row["selectionClass"] == "priority_character_surface"
    )
    payload = {
        "schema": "endfield.native-texture-payload-contract.v2",
        "status": "source_closed_current_build",
        "scope": (
            f"{baseline_totals['textures']} current face/iris/eye/emotion compressed "
            f"mip chains plus {priority_totals['textures']} current impact-ranked "
            "body/cloth/hair/key-accessory chains derived from original material "
            "Texture PPtrs for Li Zhiyan, Last Rite, Zhuang Fangyi, and Wulfa"
        ),
        "sourceReport": str(SOURCE_REPORT.resolve()),
        "sourceReportSha256": sha256(SOURCE_REPORT),
        "textureImportContractAssetPath": asset_path(IMPORT_CONTRACT),
        "textureImportContractSha256": sha256(IMPORT_CONTRACT),
        "baselineFaceEye": {
            "textureCount": baseline_totals["textures"],
            "generatedCopyCount": baseline_totals["copies"],
            "logicalPayloadBytes": baseline_totals["logicalBytes"],
        },
        "addedPrioritySurfaces": {
            "textureCount": priority_totals["textures"],
            "generatedCopyCount": priority_totals["copies"],
            "logicalPayloadBytes": priority_totals["logicalBytes"],
            "impactRankCounts": {str(key): rank_counts[key] for key in sorted(rank_counts)},
        },
        "textureCount": len(rows),
        "generatedCopyCount": generated_copy_count,
        "logicalPayloadBytes": logical_payload_bytes,
        "uniquePayloadCount": len(copied_payload_hashes),
        "uniquePayloadBytes": unique_payload_bytes,
        "deduplicatedPayloadBytes": logical_payload_bytes - unique_payload_bytes,
        "textures": rows,
        "boundary": (
            "Selection is gated by the 853-object census and exact manifest material "
            "PPtrs. It excludes the two separately owned eye-shadow masks, uncompressed "
            "or single-mip textures, non-priority characters' residual surfaces, and "
            "unreferenced broad-census payloads. Identical payload bytes are stored once."
        ),
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUTPUT}")
    print(
        f"textures={len(rows)} copies={generated_copy_count} "
        f"logicalBytes={logical_payload_bytes} uniquePayloads={len(copied_payload_hashes)} "
        f"uniqueBytes={unique_payload_bytes} sha256={sha256(OUTPUT)}"
    )


if __name__ == "__main__":
    main()
