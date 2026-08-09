#!/usr/bin/env python3
"""Audit the selected deferred resolver's b34 punctual ShadowData subset."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
GAME_ROOT = Path(r"D:/Program Files/Endfield Game")
SOURCES = {
    "gameAssembly": GAME_ROOT / "GameAssembly.dll",
    "globalMetadata": (
        GAME_ROOT / "Endfield_Data/il2cpp_data/Metadata/global-metadata.dat"
    ),
    "selectedFragment": (
        LAB_ROOT
        / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
        "selected_fragment.hlsl"
    ),
    "shadowLayoutAudit": (
        REPO_ROOT / "scratch/reverse_engineering/shadow_data/audit.json"
    ),
    "punctualWriterAudit": (
        REPO_ROOT
        / "scratch/reverse_engineering/punctual_shadow_data/audit.json"
    ),
    "punctualAtlasAudit": (
        REPO_ROOT
        / "scratch/reverse_engineering/punctual_shadow_data/atlas_audit.json"
    ),
    "punctualCacheAudit": (
        REPO_ROOT
        / "scratch/reverse_engineering/punctual_shadow_cache/cache_audit.json"
    ),
    "punctualRowAudit": (
        REPO_ROOT
        / "scratch/reverse_engineering/punctual_shadow_rows/row_audit.json"
    ),
    "operatorLights": (
        LAB_ROOT
        / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/"
        "RenderParameters/operator_lights.json"
    ),
}
EXPECTED_HASHES = {
    "gameAssembly": (
        "0c5573679bc6dec2d068a14335466db7ccf20af9bae2b983fb9d45677d80ffce"
    ),
    "globalMetadata": (
        "90c58e26e87c7227a85dda3fedf6ce5ed0b06dc1f76e0abbe75ab20750adf97e"
    ),
    "selectedFragment": (
        "44dc5090af87a8f65ffca870f9e02b8525c4cfe14f84cf8feaa3ea6c49e4b9db"
    ),
    "shadowLayoutAudit": (
        "26b768495bf1a54f3975ce55420d128581dd8d2937884e8c6cb1f89be049786b"
    ),
    "punctualWriterAudit": (
        "c6f0a5a104bff3d13b0bad55815dd9acccb0f16a8cfa062017fe77d59d1d8454"
    ),
    "punctualAtlasAudit": (
        "139319c151be92af75034a34f207506c8307e48d02e2a63e3acab3ab2c466861"
    ),
    "punctualCacheAudit": (
        "e6729fe5a8ca2e8c85243a161deb4310eadb53fd4da138ebf8be9a372f6b91be"
    ),
    "punctualRowAudit": (
        "a389af135a196951432d16f1a925f1a9154932b465981703dd6b1ae0fe15939f"
    ),
    "operatorLights": (
        "706f66b89aa209371df50956e9f1525026ce4a8a1f19a85210fc35d3b2c23ac8"
    ),
}
OUTPUT = LAB_ROOT / "scratch/character_recovery/deferred_shadow_data/audit.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred ShadowData audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(path)


def build_audit() -> dict[str, object]:
    hashes: dict[str, str] = {}
    for name, path in SOURCES.items():
        hashes[name] = sha256(path)
        require(f"{name}_sha256", hashes[name], EXPECTED_HASHES[name])

    shadow_layout = json.loads(
        SOURCES["shadowLayoutAudit"].read_text(encoding="utf-8")
    )
    punctual_writer = json.loads(
        SOURCES["punctualWriterAudit"].read_text(encoding="utf-8")
    )
    require("shadow_size", shadow_layout["layout"]["size_bytes"], 11440)
    require(
        "shadow_sections",
        [
            (row["name"], row["offset"], row["size"])
            for row in shadow_layout["layout"]["sections"]
        ],
        [
            ("CSM", 0, 1024),
            ("PunctualLight", 1024, 6144),
            ("Character", 7168, 2048),
            ("ASM", 9216, 2224),
        ],
    )
    require(
        "punctual_writer_rows",
        punctual_writer["manager"]["max_shadow_caster_count"],
        56,
    )

    fragment = SOURCES["selectedFragment"].read_text(encoding="utf-8")
    character_gate = "_LightDataBuffer_f_96[_773].z > 0.5f"
    continue_gate = "|| _865)\n            {"
    first_shadow_load = "mul(_33_m10[_1625]"
    require("character_gate_present", character_gate in fragment, True)
    require("early_continue_present", continue_gate in fragment, True)
    require("punctual_shadow_load_present", first_shadow_load in fragment, True)
    require(
        "consumer_control_flow_order",
        fragment.index(character_gate) < fragment.index(continue_gate)
        < fragment.index(first_shadow_load),
        True,
    )

    lights = json.loads(SOURCES["operatorLights"].read_text(encoding="utf-8"))
    fixtures: dict[str, object] = {}
    for actor, expected_count, expected_type, expected_faces in (
        ("wulfa", 8, 0, 1),
        ("zhuangfy", 6, 2, 6),
    ):
        rows = lights["actors"][actor]["lights"]
        require(f"{actor}_light_count", len(rows), expected_count)
        require(
            f"{actor}_all_character_only",
            all(row["enabled"] and row["character_only"] for row in rows),
            True,
        )
        shadowed = [row for row in rows if row["shadow_type"] != 0]
        require(f"{actor}_shadowed_count", len(shadowed), 1)
        row = shadowed[0]
        require(
            f"{actor}_shadow_identity",
            (row["index"], row["name"], row["shadow_type"], row["light_type"]),
            (4, "RimLight_2 (5)", 2, expected_type),
        )
        fixtures[actor] = {
            "lightCount": expected_count,
            "sourceRow": 4,
            "sourceName": "RimLight_2 (5)",
            "faceCount": expected_faces,
            "allRowsCharacterOnly": True,
        }

    return {
        "schema": "endfield.recovered-deferred-shadow-data-audit.v1",
        "status": "isolated_charinfo_punctual_producer_source_closed",
        "binding": {
            "canonicalName": "_ShadowData",
            "binding": 34,
            "sizeBytes": 11440,
            "vectorCount": 715,
            "d3d11BridgeName": "EndfieldCB5",
            "d3d11SelectedBytes": 6416,
            "d3d11SelectedVectors": 401,
        },
        "punctualSection": {
            "offsetBytes": 1024,
            "sizeBytes": 6144,
            "matrixVectors": [64, 287],
            "paramsVectors": [288, 343],
            "rectVectors": [344, 399],
            "texelSizeVector": 400,
            "unownedTailVectors": [401, 447],
            "dynamicSlots": [40, 47],
            "nativeAtlas": "6T x 4T for the source-closed N=8 isolated capacity",
        },
        "selectedConsumer": {
            "allFixtureRowsExitBeforeB34": True,
            "gate": "record[3].z LightCharacterOnly > 0.5",
            "boundary": (
                "b34 and _PunctualLightShadowTexV2 are not sampled by the "
                "selected SphereOutside program for these isolated rows; "
                "the recovered publication closes the matching real producer "
                "subset, not a general-scene ShadowData fixture"
            ),
        },
        "fixtures": fixtures,
        "remainingBoundary": (
            "retail whole-scene static cache rows, target-client physical "
            "atlas identity/texels, runtime IFix state, CSM/Character/ASM "
            "sections, and general-scene b34 consumption remain open"
        ),
        "sources": {
            name: {"path": relative(path), "sha256": hashes[name]}
            for name, path in SOURCES.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    rendered = json.dumps(build_audit(), indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file():
            raise AssertionError(f"missing generated audit: {OUTPUT}")
        require("generated_audit", OUTPUT.read_text(encoding="utf-8"), rendered)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Deferred ShadowData audit passed: b34=11440 bytes, "
        "punctual rows c64..c400, isolated consumer exits before b34 reads."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
