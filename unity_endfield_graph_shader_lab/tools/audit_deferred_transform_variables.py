#!/usr/bin/env python3
"""Audit the selected deferred resolver's source-backed b30 camera reads."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
METADATA = (
    LAB_ROOT
    / "scratch/reverse_engineering/sphereoutside_deferred_variant/"
    "original_shader_export/Shader/"
    "HGRP_DeferredLighting_p5F10B115E8D3AFDE.shader.bytecode/"
    "0097_endfield_dxbc_1.dxbc.metadata.json"
)
CAMERA_REPORT = (
    REPO_ROOT
    / "scratch/reverse_engineering/"
    "zhuangfy_specific_lightning901_gacha_camera_frame/"
    "gacha_camera_frame_report.json"
)
OUTPUT = (
    LAB_ROOT
    / "scratch/character_recovery/deferred_transform_variables/audit.json"
)
EXPECTED_METADATA_SHA256 = (
    "07b16f92bce820666837e624777b4160d89bb5faf9a57e8eafe48c6041501cff"
)
EXPECTED_CAMERA_REPORT_SHA256 = (
    "65a49f19e727787e2c34466968dbcb53df890f6ecf79efb0bbcb469dccd138d8"
)
EXPECTED_FIELDS = {
    "_ViewMatrix": {"byteOffset": 0, "register": 0, "rows": 4, "columns": 4},
    "_InvViewMatrix": {
        "byteOffset": 64,
        "register": 4,
        "rows": 4,
        "columns": 4,
    },
    "_InvViewProjMatrix": {
        "byteOffset": 384,
        "register": 24,
        "rows": 4,
        "columns": 4,
    },
    "_WorldSpaceCameraPos_Internal": {
        "byteOffset": 704,
        "register": 44,
        "rows": 4,
        "columns": 1,
    },
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return path.resolve().relative_to(REPO_ROOT).as_posix()


def require(check: str, actual: object, expected: object) -> None:
    if actual != expected:
        raise AssertionError(
            "Deferred TransformVariables audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def build_audit() -> dict[str, object]:
    metadata_hash = sha256(METADATA)
    camera_hash = sha256(CAMERA_REPORT)
    require("metadata_sha256", metadata_hash, EXPECTED_METADATA_SHA256)
    require("camera_report_sha256", camera_hash, EXPECTED_CAMERA_REPORT_SHA256)

    metadata = json.loads(METADATA.read_text(encoding="utf-8"))
    transform = next(
        row
        for row in metadata["ConstantBufferParameters"]
        if row["Name"] == "_TransformVariables"
    )
    require("buffer_size", transform["Size"], 1312)
    require("partial_consumer_metadata", transform["IsPartialCB"], True)

    fields: dict[str, dict[str, int]] = {}
    for group in ("MatrixParameters", "VectorParameters"):
        for row in transform[group]:
            fields[row["Name"]] = {
                "byteOffset": int(row["Index"]),
                "register": int(row["Index"]) // 16,
                "rows": int(row["RowCount"]),
                "columns": int(row["ColumnCount"]),
            }
    require("selected_used_fields", fields, EXPECTED_FIELDS)

    camera = json.loads(CAMERA_REPORT.read_text(encoding="utf-8"))
    matrix_fixture = camera["d3d12DiagnosticMatrixFixture"]
    require(
        "matrix_construction",
        matrix_fixture["matrixConstruction"],
        "GL.GetGPUProjectionMatrix(nonJitteredProjection,true) * "
        "worldToCameraWithIndices12To14ZeroAnd15One",
    )
    require(
        "d3d_register_packing",
        matrix_fixture["d3dRegisterPacking"],
        "four physical column registers; VS computes "
        "x*c32+y*c33+z*c34+1*c35",
    )

    return {
        "schema": "endfield.deferred-transform-variables-audit.v1",
        "status": "selected_consumer_used_ranges_source_closed",
        "constantBuffer": {
            "name": "_TransformVariables",
            "binding": 30,
            "sizeBytes": 1312,
            "vectorCount": 82,
            "partialConsumerMetadata": True,
        },
        "selectedUsedFields": fields,
        "producerFormula": {
            "view": "HGCamera input world-to-camera matrix",
            "inverseView": "inverse of the HGCamera input view matrix",
            "inverseViewProjection": (
                "inverse(GL.GetGPUProjectionMatrix(projection,true) * view)"
            ),
            "worldSpaceCameraPosition": "physical Camera transform position xyz",
            "matrixPacking": matrix_fixture["d3dRegisterPacking"],
        },
        "boundary": (
            "Only the four fields present in the selected original pass-0 "
            "partial constant-buffer metadata are closed. The other 69 "
            "float4 registers remain history/jitter/stereo producer work and "
            "must stay zero in the default-off lab transport."
        ),
        "sources": {
            "selectedDxbcMetadata": {
                "path": relative(METADATA),
                "sha256": metadata_hash,
            },
            "installedCameraMatrixAudit": {
                "path": relative(CAMERA_REPORT),
                "sha256": camera_hash,
            },
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    audit = build_audit()
    rendered = json.dumps(audit, indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file():
            raise AssertionError(f"missing generated audit: {OUTPUT}")
        require("generated_audit", OUTPUT.read_text(encoding="utf-8"), rendered)
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(rendered, encoding="utf-8")
    print(
        "Deferred TransformVariables audit passed: b30=1312 bytes, "
        "selected fields=4, unknown registers remain fail-closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
