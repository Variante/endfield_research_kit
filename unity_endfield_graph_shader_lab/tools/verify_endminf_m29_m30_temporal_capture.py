#!/usr/bin/env python3
"""Verify retained Endminf M29/M30 temporal draw evidence fail-closed."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any


REPO = Path(__file__).resolve().parents[2]
CAPTURE = REPO / "scratch/reverse_engineering/endfield_capture/20260826T162514Z"
OUTPUT = (REPO / "reports/assets/character_recovery"
          / "endminf_m29_m30_temporal_capture_latest.json")
MATERIAL_ROOT = (REPO / "unity_endfield_graph_shader_lab/Assets/EndfieldGraphShaderLab"
                 / "Generated/Characters/Playable/Endminf/Effects/Overview/Materials")
SESSION = "20260826T162514Z"
PHASE_ANCHOR_FRAME = 2978
PHASE_ANCHOR_SECONDS = 4.433333
M29_FRAMES = (2864, 2872, 2880, 2888, 2896, 2905, 2913,
              2921, 2929, 2937, 2945, 2953, 2962)
M30_FRAMES = (2880, 2888, 2896, 2905, 2913, 2921,
              2929, 2937, 2945, 2953, 2962)


class VerificationError(RuntimeError):
    pass


OWNERS = {
    "M29": {
        "vertex": 0xCE755059DEDDC2E0,
        "pixel": 0xF2AD2A14856044AC,
        "frames": M29_FRAMES,
        "counts": {1386},
        "c1": (1.0, 0.0, 15.0, 1.3),
        "c4": (0.26225068, 0.15781066, 0.08437622, 1.0),
        "authoredTint": (0.54901963, 0.43381283, 0.32156864, 1.0),
        "material": "M_fx_endminm_gfx_29_p7BCC4552203800A8.mat",
        "materialPathId": "0x7BCC4552203800A8",
    },
    "M30": {
        "vertex": 0x62A5CE6C09171DE9,
        "pixel": 0x5558DEDDB1EE6188,
        "frames": M30_FRAMES,
        "counts": {6, 12},
        "c1": (1.0, 0.0, 3.0, 0.5),
        "c4": (0.93269453, 0.52442606, 0.09170079, 1.0),
        "authoredTint": (0.96981126, 0.75122124, 0.3348593, 1.0),
        "material": "M_fx_endminm_gfx_30_p5FE318FDDD817ADA.mat",
        "materialPathId": "0x5FE318FDDD817ADA",
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def phase_seconds(frame: int) -> float:
    return PHASE_ANCHOR_SECONDS + (frame - PHASE_ANCHOR_FRAME) / 60.0


def shaders(draw: dict[str, Any]) -> dict[int, int]:
    return {int(row["stage"]): int(row["identityHash"])
            for row in draw.get("shaders", [])}


def constant(draw: dict[str, Any], stage: int, slot: int) -> bytes:
    rows = [row for row in draw.get("constantBuffers", [])
            if row.get("stage") == stage and row.get("slot") == slot]
    require(len(rows) == 1, f"stage {stage} b{slot} is not unique")
    row = rows[0]
    require(row.get("rangeValid") is True and row.get("metadataValid") is True,
            f"stage {stage} b{slot} is invalid")
    payload = bytes.fromhex(row.get("dataHex", ""))
    require(payload and len(payload) % 16 == 0,
            f"stage {stage} b{slot} is not float4 aligned")
    return payload


def vector(payload: bytes, index: int) -> tuple[float, float, float, float]:
    offset = index * 16
    require(offset + 16 <= len(payload), f"constant c{index} is absent")
    return struct.unpack_from("<4f", payload, offset)


def close(actual: tuple[float, ...], expected: tuple[float, ...]) -> bool:
    return all(math.isclose(a, e, rel_tol=0.0, abs_tol=2e-6)
               for a, e in zip(actual, expected))


def is_owner(draw: dict[str, Any], owner: dict[str, Any]) -> bool:
    pair = shaders(draw)
    if pair.get(0) != owner["vertex"] or pair.get(4) != owner["pixel"]:
        return False
    try:
        b3 = constant(draw, 4, 3)
    except VerificationError:
        return False
    return close(vector(b3, 1), owner["c1"]) and close(vector(b3, 4), owner["c4"])


def linear_channel(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def parse_material(owner_name: str, owner: dict[str, Any]) -> dict[str, Any]:
    path = MATERIAL_ROOT / owner["material"]
    require(path.is_file(), f"{owner_name} generated material is absent")
    text = path.read_text(encoding="utf-8")
    tint_match = re.search(
        r"^\s*- _TintColor: \{r: ([^,]+), g: ([^,]+), b: ([^,]+), a: ([^}]+)\}$",
        text, re.MULTILINE)
    intensity_match = re.search(r"^\s*- _TintColorIntensity: ([^\r\n]+)$", text, re.MULTILINE)
    alpha_match = re.search(r"^\s*- _TintColorAlpha: ([^\r\n]+)$", text, re.MULTILINE)
    require(tint_match is not None and intensity_match is not None and alpha_match is not None,
            f"{owner_name} generated material lost tint properties")
    authored = tuple(float(tint_match.group(i)) for i in range(1, 5))
    require(close(authored, owner["authoredTint"]),
            f"{owner_name} authored tint drifted")
    require(math.isclose(float(intensity_match.group(1)), owner["c1"][2], abs_tol=1e-6),
            f"{owner_name} tint intensity drifted")
    require(math.isclose(float(alpha_match.group(1)), owner["c1"][3], abs_tol=1e-6),
            f"{owner_name} tint alpha drifted")
    linear = tuple(linear_channel(value) for value in authored[:3]) + (authored[3],)
    require(close(linear, owner["c4"]),
            f"{owner_name} authored tint no longer maps to captured PS b3 c4")
    return {
        "path": str(path.relative_to(REPO)).replace("\\", "/"),
        "sha256": sha256(path),
        "materialPathId": owner["materialPathId"],
        "authoredTint": list(authored),
        "linearTint": list(linear),
        "intensity": float(intensity_match.group(1)),
        "alpha": float(alpha_match.group(1)),
    }


def collect_owner(capture: Path, owner_name: str,
                  owner: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for frame_id in owner["frames"]:
        metadata_path = capture / "graphics/frames" / str(frame_id) / "metadata.json"
        require(metadata_path.is_file(), f"{owner_name} frame {frame_id} metadata is absent")
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        matches = [draw for draw in metadata.get("drawRecords", [])
                   if isinstance(draw, dict) and is_owner(draw, owner)]
        require(len(matches) == 1,
                f"{owner_name} frame {frame_id} owner draw count is {len(matches)}")
        draw = matches[0]
        require(int(draw.get("count", -1)) in owner["counts"],
                f"{owner_name} frame {frame_id} index count drifted")
        require(int(draw.get("instanceCount", -1)) == 1,
                f"{owner_name} frame {frame_id} instance count drifted")
        constants = {}
        truncated = []
        for stage, slots in ((0, range(5)), (4, range(4))):
            for slot in slots:
                payload = constant(draw, stage, slot)
                key = f"{'vs' if stage == 0 else 'ps'}B{slot}"
                constants[key] = hashlib.sha256(payload).hexdigest()
                source = next(row for row in draw["constantBuffers"]
                              if row["stage"] == stage and row["slot"] == slot)
                if source.get("truncated") is True:
                    truncated.append(key)
        b3 = constant(draw, 4, 3)
        rows.append({
            "frame": frame_id,
            "phaseSeconds": round(phase_seconds(frame_id), 6),
            "indexCount": int(draw["count"]),
            "startIndex": int(draw["start"]),
            "baseVertex": int(draw["baseVertex"]),
            "instanceCount": int(draw["instanceCount"]),
            "psB3C1": list(vector(b3, 1)),
            "psB3C4": list(vector(b3, 4)),
            "constantSha256": constants,
            "truncatedConstantAllocations": truncated,
            "metadataSha256": sha256(metadata_path),
        })
    return rows


def build_report(capture: Path = CAPTURE) -> dict[str, Any]:
    require(capture.name == SESSION, "M29/M30 capture session drifted")
    owners = {}
    for owner_name, owner in OWNERS.items():
        frames = collect_owner(capture, owner_name, owner)
        owners[owner_name] = {
            "shaderPair": {
                "vertex": f"0x{owner['vertex']:016X}",
                "pixel": f"0x{owner['pixel']:016X}",
            },
            "packetCount": len(frames),
            "drawCount": len(frames),
            "indexCounts": sorted({row["indexCount"] for row in frames}),
            "material": parse_material(owner_name, owner),
            "frames": frames,
        }
    return {
        "schema": "endfield.endminf-m29-m30-temporal-capture.v1",
        "status": "validated_source_assisted_only",
        "sessionId": SESSION,
        "capture": str(capture.relative_to(REPO)).replace("\\", "/"),
        "phaseAnchor": {
            "frame": PHASE_ANCHOR_FRAME,
            "seconds": PHASE_ANCHOR_SECONDS,
            "basis": "no-frame-generation source frame 381 peak registration",
        },
        "owners": owners,
        "exactReplayReady": False,
        "exactReplayGap": (
            "This pre-patch session retains draw identity and bounded constant prefixes, "
            "but not owner-specific M29/M30 IA and PS t0-t5 resources."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    report = build_report(args.capture.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
