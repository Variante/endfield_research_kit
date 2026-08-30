#!/usr/bin/env python3
"""Audit exact M27 b0 reads and the source-derived temporal publisher."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


LAB_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = LAB_ROOT.parent
BYTECODE_ROOT = LAB_ROOT / "tools/original_dxbc_exact/bytecode"
VERTEX_DXBC = BYTECODE_ROOT / "endminf_m27_hgbuffer_vs.dxbc"
PIXEL_DXBC = BYTECODE_ROOT / "endminf_m27_hgbuffer_ps.dxbc"
FRAME = (
    REPO_ROOT
    / "scratch/reverse_engineering/endfield_capture/20260829T224523Z/"
    "graphics/frames/2344/metadata.json"
)
CONTRACT = (
    LAB_ROOT / "Assets/EndfieldGraphShaderLab/Runtime/Rendering/"
    "EndfieldRecoveredDeferredTransformVariablesContract.cs"
)
OWNER = CONTRACT.with_name("EndfieldRecoveredDeferredTransformVariables.cs")
PIPELINE = CONTRACT.with_name("HGCompatRenderPipeline.cs")
OUTPUT = (
    REPO_ROOT / "reports/assets/character_recovery/"
    "endminf_m27_b0_source_contract.json"
)

EXPECTED_DXBC = {
    "vertex": "c0266e7fac0046c18ef9ce4ca229873284198d3b2202af0e2db86d073dd57c3c",
    "pixel": "92d80a93add9c714daeb265a66d3fe6e841c32825728d6af4268cede13c0c44e",
}
EXPECTED_IDENTITIES = {
    "vertex": "0xC0266E7FAC0046C1",
    "pixel": "0x92D80A93ADD9C714",
}
EXPECTED_READS = {
    "vertex": {
        32: "xyzw", 33: "xyzw", 34: "xyzw", 35: "xyzw",
        44: "xyz",
        57: "xyw", 58: "xyw", 59: "xyw", 60: "xyw",
        81: "xyz",
    },
    "pixel": {
        0: "z", 1: "z", 2: "z",
        24: "xyzw", 25: "xyzw", 26: "xyzw", 27: "xyzw",
        44: "xyz",
    },
}
EXPECTED_PIXEL_B3_READS = {
    0: "xzw", 1: "xw", 2: "w", 3: "xyw", 4: "xyz", 7: "xz",
    8: "xyzw", 11: "xyzw", 12: "xyzw", 22: "x", 24: "xyzw",
    25: "xyzw", 26: "xyzw", 27: "xyz", 28: "yw", 29: "xyz",
    30: "xyz",
}
LANE_INDEX = {lane: index for index, lane in enumerate("xyzw")}


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
            "M27 b0 source audit failed: "
            f"check={check}; expected={expected!r}; actual={actual!r}"
        )


def find_fxc() -> Path:
    kits = Path(r"C:\Program Files (x86)\Windows Kits\10\bin")
    candidates = sorted(kits.glob("*/x64/fxc.exe"), reverse=True)
    if not candidates:
        raise AssertionError("M27 b0 source audit failed: fxc.exe is unavailable")
    return candidates[0]


def read_inventory(
        fxc: Path,
        path: Path,
        buffer_slot: int) -> dict[int, str]:
    result = subprocess.run(
        [str(fxc), "/dumpbin", "/nologo", str(path)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    lanes: dict[int, set[str]] = {}
    pattern = rf"cb{buffer_slot}\[(\d+)\]\.([xyzw]+)"
    for match in re.finditer(pattern, result.stdout):
        lanes.setdefault(int(match.group(1)), set()).update(match.group(2))
    return {
        register: "".join(lane for lane in "xyzw" if lane in values)
        for register, values in lanes.items()
    }


def find_row(rows: list[dict[str, object]], **wanted: object) -> dict[str, object]:
    for row in rows:
        if all(row.get(key) == value for key, value in wanted.items()):
            return row
    raise AssertionError(f"M27 b0 source audit failed: missing row {wanted}")


def cb_words(row: dict[str, object]) -> list[int]:
    payload = bytes.fromhex(str(row.get("dataHex", "")))
    count = int(row.get("capturedConstants", 0))
    require("captured_b0_bytes", len(payload), count * 16)
    return list(struct.unpack(f"<{len(payload) // 4}I", payload))


def selected_words(words: list[int], register: int, lanes: str) -> list[int]:
    return [words[register * 4 + LANE_INDEX[lane]] for lane in lanes]


def normalize_signed_zero(word: int) -> int:
    return 0 if word & 0x7FFFFFFF == 0 else word


def build_audit() -> dict[str, object]:
    fxc = find_fxc()
    for stage, path in (("vertex", VERTEX_DXBC), ("pixel", PIXEL_DXBC)):
        require(f"{stage}_dxbc_sha256", sha256(path), EXPECTED_DXBC[stage])
        require(f"{stage}_b0_reads", read_inventory(fxc, path, 0),
                EXPECTED_READS[stage])
    require("pixel_b3_reads", read_inventory(fxc, PIXEL_DXBC, 3),
            EXPECTED_PIXEL_B3_READS)

    frame = json.loads(FRAME.read_text(encoding="utf-8"))
    require("frame_capture_incomplete", frame.get("captureIncomplete"), False)
    require("frame_capture_failed", frame.get("captureFailed"), False)
    require("frame_dropped_events", frame.get("droppedEvents"), 0)
    draw = find_row(
        frame.get("drawRecords", []),
        priorityShaderPair=True,
        priorityM27Geometry=True,
    )
    require("draw_ordinal", draw.get("drawOrdinal"), 38)
    require("draw_count", draw.get("count"), 1080)
    require("draw_instance_count", draw.get("instanceCount"), 1)
    shaders = draw.get("shaders", [])
    require(
        "draw_vertex_identity",
        find_row(shaders, stage=0).get("identityHash"),
        int(EXPECTED_IDENTITIES["vertex"], 16),
    )
    require(
        "draw_pixel_identity",
        find_row(shaders, stage=4).get("identityHash"),
        int(EXPECTED_IDENTITIES["pixel"], 16),
    )
    buffers = draw.get("constantBuffers", [])
    vertex_b0 = find_row(buffers, stage=0, slot=0)
    pixel_b0 = find_row(buffers, stage=4, slot=0)
    for stage, row, needed in (
            ("vertex", vertex_b0, 82), ("pixel", pixel_b0, 28)):
        require(f"{stage}_b0_range_valid", row.get("rangeValid"), True)
        require(f"{stage}_b0_metadata_valid", row.get("metadataValid"), True)
        require(f"{stage}_b0_captured_constants",
                int(row.get("capturedConstants", 0)) >= needed, True)
    require("shared_b0_buffer",
            (vertex_b0.get("bufferId"), vertex_b0.get("firstConstant")),
            (pixel_b0.get("bufferId"), pixel_b0.get("firstConstant")))
    vertex_words = cb_words(vertex_b0)
    pixel_words = cb_words(pixel_b0)
    current_matrix_words = vertex_words[32 * 4:36 * 4]
    previous_matrix_words = vertex_words[57 * 4:61 * 4]
    require(
        "retail_reset_previous_matrix_numeric",
        [normalize_signed_zero(word) for word in previous_matrix_words],
        [normalize_signed_zero(word) for word in current_matrix_words],
    )
    matrix_signed_zero_differences = sum(
        current != previous and normalize_signed_zero(current) ==
        normalize_signed_zero(previous)
        for current, previous in zip(current_matrix_words,
                                     previous_matrix_words)
    )
    require(
        "retail_reset_previous_camera_xyz",
        selected_words(vertex_words, 81, "xyz"),
        selected_words(vertex_words, 44, "xyz"),
    )
    for register, lanes in EXPECTED_READS["pixel"].items():
        if register >= 28:
            continue
        require(
            f"shared_stage_b0_c{register}_{lanes}",
            selected_words(pixel_words, register, lanes),
            selected_words(vertex_words, register, lanes),
        )

    contract_text = CONTRACT.read_text(encoding="utf-8")
    owner_text = OWNER.read_text(encoding="utf-8")
    pipeline_text = PIPELINE.read_text(encoding="utf-8")
    for marker in (
        "public static readonly int[] M27ReadVectors",
        "nonJitteredGpuProjection * viewNoTranslation",
        "viewProjection.inverse",
        "previousFrameHistoryReady",
        "previousProjection",
        "previousPosition",
    ):
        require(f"contract_marker:{marker}", marker in contract_text, True)
    for marker in (
        "Dictionary<int,",
        ".CameraHistoryState>",
        ".TryEvaluateHistory(",
        "Time.frameCount",
        "CommitHistory(",
        "currentM27SourceReady = true",
        "currentM27SourceReady = false",
    ):
        require(f"owner_marker:{marker}", marker in owner_text, True)
    start = pipeline_text.find(
        "if (EndfieldRecoveredDeferredTransformVariables.IsRequested)")
    owner_gate = pipeline_text.find(
        "if (recoveredEndminfLitEffectOwnerActive", start)
    require("continuous_camera_history_publication",
            start >= 0 and owner_gate > start and
            "PrepareAndPublish" in pipeline_text[start:owner_gate], True)

    return {
        "schema": "endfield.endminf-m27-b0-source-contract.v1",
        "status": "source_closed_runtime_values_not_captured",
        "exactProgram": {
            "subProgramIndex": 113,
            "vertex": {
                "path": relative(VERTEX_DXBC),
                "sha256": EXPECTED_DXBC["vertex"],
                "identity": EXPECTED_IDENTITIES["vertex"],
                "b0Reads": {str(key): value
                            for key, value in EXPECTED_READS["vertex"].items()},
            },
            "pixel": {
                "path": relative(PIXEL_DXBC),
                "sha256": EXPECTED_DXBC["pixel"],
                "identity": EXPECTED_IDENTITIES["pixel"],
                "b0Reads": {str(key): value
                            for key, value in EXPECTED_READS["pixel"].items()},
                "b3Reads": {
                    str(key): value
                    for key, value in EXPECTED_PIXEL_B3_READS.items()
                },
            },
        },
        "sourceProducer": {
            "currentView": "camera.worldToCameraMatrix",
            "inverseViewProjection": (
                "inverse(GL.GetGPUProjectionMatrix(camera.projectionMatrix, "
                "renderIntoTexture) * camera.worldToCameraMatrix)"
            ),
            "currentNonJitteredViewNoTranslationProjection": (
                "GL.GetGPUProjectionMatrix(camera.nonJitteredProjectionMatrix, "
                "renderIntoTexture) * viewWithoutTranslation"
            ),
            "cameraPosition": "camera.transform.position",
            "previousFrame": (
                "per-camera immediately preceding source-built matrix and "
                "position when frame/extent/render-target continuity holds"
            ),
            "historyReset": (
                "current matrix and position, matching retail HGCamera reset"
            ),
        },
        "selectedDrawValidation": {
            "source": {"path": relative(FRAME), "sha256": sha256(FRAME)},
            "frame": 2344,
            "drawOrdinal": 38,
            "actualM27Geometry": True,
            "currentPreviousMatrixNumericallyExactOnReset": True,
            "currentPreviousMatrixSignedZeroDifferences":
                matrix_signed_zero_differences,
            "currentPreviousCameraXyzBitExactOnReset": True,
            "sharedStageB0WordsBitExact": True,
            "capturedPayloadUsedAtRuntime": False,
        },
        "sources": {
            "contract": {"path": relative(CONTRACT), "sha256": sha256(CONTRACT)},
            "owner": {"path": relative(OWNER), "sha256": sha256(OWNER)},
            "pipeline": {"path": relative(PIPELINE), "sha256": sha256(PIPELINE)},
        },
        "boundary": (
            "Captured b0 values validate names, packing, and retail reset "
            "semantics only. Runtime values are rebuilt from the live camera "
            "and per-camera temporal history; no captured matrix, position, "
            "constant-buffer array, or fitted curve is published."
        ),
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
        "M27 b0 source audit passed: exact DXBC reads, actual draw reset, "
        "and source-derived temporal publisher are closed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
