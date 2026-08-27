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
PHASE_ANCHOR_FRAME = 2978
PHASE_ANCHOR_SECONDS = 4.433333
LEGACY_WINDOWS_QPC_FREQUENCY = 10_000_000
M29_FRAMES = (2864, 2872, 2880, 2888, 2896, 2905, 2913,
              2921, 2929, 2937, 2945, 2953, 2962)
M30_FRAMES = (2880, 2888, 2896, 2905, 2913, 2921,
              2929, 2937, 2945, 2953, 2962)
KNOWN_CAPTURES = {
    "20260826T162514Z": {
        "phaseAnchorFrame": PHASE_ANCHOR_FRAME,
        "phaseAnchorSeconds": PHASE_ANCHOR_SECONDS,
        "phaseAnchorBasis": "no-frame-generation source frame 381 peak registration",
        "expectedFrames": {"M29": M29_FRAMES, "M30": M30_FRAMES},
    },
}


class VerificationError(RuntimeError):
    pass


OWNERS = {
    "M29": {
        "vertex": 0xCE755059DEDDC2E0,
        "pixel": 0xF2AD2A14856044AC,
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


def phase_seconds(timestamp_qpc: int, anchor_timestamp_qpc: int,
                  qpc_frequency: int,
                  anchor_seconds: float = PHASE_ANCHOR_SECONDS) -> float:
    require(timestamp_qpc > 0 and anchor_timestamp_qpc > 0,
            "phase timing requires positive QPC timestamps")
    require(qpc_frequency > 0, "phase timing requires a positive QPC frequency")
    return anchor_seconds + ((timestamp_qpc - anchor_timestamp_qpc)
                             / qpc_frequency)


def capture_clock(capture: Path) -> tuple[int, str]:
    session_path = capture / "session.json"
    require(session_path.is_file(), f"capture session manifest is absent: {session_path}")
    session = json.loads(session_path.read_text(encoding="utf-8"))
    frequency = int(session.get("qpcFrequency", 0))
    if frequency > 0:
        return frequency, "session.json qpcFrequency"
    return (LEGACY_WINDOWS_QPC_FREQUENCY,
            "legacy Windows capture fallback; host QPC frequency verified as 10000000")


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


def resource_key(row: dict[str, Any]) -> tuple[int, int, int]:
    return (int(row.get("objectId", 0)), int(row.get("stage", -1)),
            int(row.get("slot", -1)))


def inspect_resource_closure(draw: dict[str, Any],
                             metadata: dict[str, Any]) -> dict[str, Any]:
    resources = [row for row in draw.get("resources", []) if isinstance(row, dict)]
    selected = [row for row in metadata.get("selectedResourceRecords", [])
                if isinstance(row, dict)]
    selected_by_key = {resource_key(row): row for row in selected}
    selected_by_object: dict[int, list[dict[str, Any]]] = {}
    for row in selected:
        selected_by_object.setdefault(int(row.get("objectId", 0)), []).append(row)
    missing = []
    unsupported = []
    for row in resources:
        key = resource_key(row)
        match = selected_by_key.get(key)
        if match is None:
            match = next((item for item in selected_by_object.get(key[0], [])
                          if item.get("completed") is True
                          and int(item.get("blobBytes", 0)) > 0), None)
        if match is not None and match.get("completed") is True and \
                int(match.get("blobBytes", 0)) > 0:
            continue
        target = {"objectId": key[0], "stage": key[1], "slot": key[2],
                  "byteSize": int(row.get("byteSize", 0))}
        if target["byteSize"] == 0:
            unsupported.append(target)
        else:
            missing.append(target)
    return {
        "ownerResourcesPresent": bool(resources),
        "complete": bool(resources) and not missing,
        "ownedResourceCount": len(resources),
        "missingPayloads": missing,
        "unsupportedZeroByteBindings": unsupported,
    }


def metadata_paths(capture: Path) -> list[Path]:
    root = capture / "graphics/frames"
    require(root.is_dir(), f"graphics frame directory is absent: {root}")
    paths = sorted(root.glob("*/metadata.json"), key=lambda path: int(path.parent.name))
    require(paths, f"capture has no graphics frame metadata: {root}")
    return paths


def collect_owner(capture: Path, owner_name: str, owner: dict[str, Any],
                  paths: list[Path], first_frame: int,
                  first_timestamp_qpc: int, qpc_frequency: int,
                  phase_anchor: tuple[int, int, float] | None,
                  expected_frames: tuple[int, ...] | None) -> list[dict[str, Any]]:
    rows = []
    observed_frames = []
    for metadata_path in paths:
        frame_id = int(metadata_path.parent.name)
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        matches = [(index, draw) for index, draw in
                   enumerate(metadata.get("drawRecords", []))
                   if isinstance(draw, dict) and is_owner(draw, owner)]
        require(len(matches) <= 1,
                f"{owner_name} frame {frame_id} owner draw count is {len(matches)}")
        if not matches:
            continue
        draw_index, draw = matches[0]
        observed_frames.append(frame_id)
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
        timestamp_qpc = int(metadata.get("timestampQpc", 0))
        require(timestamp_qpc > 0,
                f"{owner_name} frame {frame_id} has no valid timestampQpc")
        row = {
            "frame": frame_id,
            "drawIndex": draw_index,
            "frameRelativeSeconds": round((frame_id - first_frame) / 60.0, 6),
            "qpcRelativeSeconds": round(
                (timestamp_qpc - first_timestamp_qpc) / qpc_frequency, 6),
            "timestampQpc": timestamp_qpc,
            "indexCount": int(draw["count"]),
            "startIndex": int(draw["start"]),
            "baseVertex": int(draw["baseVertex"]),
            "instanceCount": int(draw["instanceCount"]),
            "psB3C1": list(vector(b3, 1)),
            "psB3C4": list(vector(b3, 4)),
            "constantSha256": constants,
            "truncatedConstantAllocations": truncated,
            "resourceClosure": inspect_resource_closure(draw, metadata),
            "metadataSha256": sha256(metadata_path),
        }
        if phase_anchor is not None:
            row["phaseSeconds"] = round(
                phase_seconds(timestamp_qpc, phase_anchor[1], qpc_frequency,
                              phase_anchor[2]), 6)
        rows.append(row)
    if expected_frames is not None:
        missing_expected = [frame for frame in expected_frames
                            if frame not in observed_frames]
        if missing_expected:
            raise VerificationError(
                f"{owner_name} frame {missing_expected[0]} owner draw count is 0")
        require(tuple(observed_frames) == tuple(expected_frames),
                f"{owner_name} frame sequence drifted: expected "
                f"{list(expected_frames)}, observed {observed_frames}")
    require(rows, f"capture contains no exact {owner_name} owner packets")
    return rows


def frame_bursts(frames: list[dict[str, Any]], qpc_frequency: int,
                 max_gap_seconds: float = 1.0
                 ) -> list[dict[str, Any]]:
    bursts: list[list[dict[str, Any]]] = []
    for row in frames:
        if not bursts or ((row["timestampQpc"] - bursts[-1][-1]["timestampQpc"])
                          / qpc_frequency) > max_gap_seconds:
            bursts.append([row])
        else:
            bursts[-1].append(row)
    return [{
        "firstFrame": burst[0]["frame"],
        "lastFrame": burst[-1]["frame"],
        "packetCount": len(burst),
        "sampledSpanSeconds": round(
            (burst[-1]["timestampQpc"] - burst[0]["timestampQpc"])
            / qpc_frequency, 6),
        "presentedFrameSpan": burst[-1]["frame"] - burst[0]["frame"],
        "frames": [row["frame"] for row in burst],
    } for burst in bursts]


def build_report(capture: Path = CAPTURE,
                 phase_anchor_frame: int | None = None,
                 phase_anchor_seconds: float | None = None) -> dict[str, Any]:
    capture = capture.resolve()
    known = KNOWN_CAPTURES.get(capture.name)
    require((phase_anchor_frame is None) == (phase_anchor_seconds is None),
            "phase anchor frame and seconds must be supplied together")
    if phase_anchor_frame is not None:
        phase_anchor = (phase_anchor_frame, float(phase_anchor_seconds))
        phase_basis = "explicit CLI/user alignment"
    elif known is not None:
        phase_anchor = (int(known["phaseAnchorFrame"]),
                        float(known["phaseAnchorSeconds"]))
        phase_basis = str(known["phaseAnchorBasis"])
    else:
        phase_anchor = None
        phase_basis = "unknown; capture-relative timing only"
    paths = metadata_paths(capture)
    qpc_frequency, qpc_frequency_basis = capture_clock(capture)
    first_frame = int(paths[0].parent.name)
    metadata_by_frame = {
        int(path.parent.name): json.loads(path.read_text(encoding="utf-8"))
        for path in paths
    }
    first_timestamp_qpc = int(metadata_by_frame[first_frame].get("timestampQpc", 0))
    require(first_timestamp_qpc > 0, f"frame {first_frame} has no valid timestampQpc")
    if phase_anchor is not None:
        anchor_metadata = metadata_by_frame.get(phase_anchor[0])
        require(anchor_metadata is not None,
                f"phase anchor frame {phase_anchor[0]} is absent from capture")
        anchor_timestamp_qpc = int(anchor_metadata.get("timestampQpc", 0))
        require(anchor_timestamp_qpc > 0,
                f"phase anchor frame {phase_anchor[0]} has no valid timestampQpc")
        phase_anchor = (phase_anchor[0], anchor_timestamp_qpc, phase_anchor[1])
    owners = {}
    for owner_name, owner in OWNERS.items():
        expected = (tuple(known["expectedFrames"][owner_name])
                    if known is not None else None)
        frames = collect_owner(capture, owner_name, owner, paths, first_frame,
                               first_timestamp_qpc, qpc_frequency,
                               phase_anchor, expected)
        complete_frames = [row["frame"] for row in frames
                           if row["resourceClosure"]["complete"]]
        bursts = frame_bursts(frames, qpc_frequency)
        primary_burst = max(bursts, key=lambda burst: burst["packetCount"])
        owners[owner_name] = {
            "shaderPair": {
                "vertex": f"0x{owner['vertex']:016X}",
                "pixel": f"0x{owner['pixel']:016X}",
            },
            "packetCount": len(frames),
            "drawCount": len(frames),
            "indexCounts": sorted({row["indexCount"] for row in frames}),
            "firstFrame": frames[0]["frame"],
            "lastFrame": frames[-1]["frame"],
            "frameBursts": bursts,
            "primaryBurst": primary_burst,
            "resourceClosedFrames": complete_frames,
            "material": parse_material(owner_name, owner),
            "frames": frames,
        }
    exact_replay_ready = all(
        bool(owner["resourceClosedFrames"]) for owner in owners.values())
    phase_contract: dict[str, Any] = {"basis": phase_basis}
    if phase_anchor is not None:
        phase_contract.update({"frame": phase_anchor[0],
                               "timestampQpc": phase_anchor[1],
                               "seconds": phase_anchor[2]})
    return {
        "schema": "endfield.endminf-m29-m30-temporal-capture.v1",
        "status": ("validated_exact_owner_temporal_and_resource_evidence"
                   if exact_replay_ready else "validated_source_assisted_only"),
        "sessionId": capture.name,
        "capture": str(capture.relative_to(REPO)).replace("\\", "/"),
        "frameCount": len(paths),
        "captureClock": {"qpcFrequency": qpc_frequency,
                         "basis": qpc_frequency_basis},
        "phaseAnchor": phase_contract,
        "owners": owners,
        "exactReplayReady": exact_replay_ready,
        "exactReplayGap": (None if exact_replay_ready else
            "No byte-complete owner-specific packet exists for one or more owners; "
            "inspect each frame's resourceClosure.missingPayloads."),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=CAPTURE)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--phase-anchor-frame", type=int)
    parser.add_argument("--phase-anchor-seconds", type=float)
    args = parser.parse_args()
    try:
        report = build_report(
            args.capture.resolve(), args.phase_anchor_frame,
            args.phase_anchor_seconds)
    except (OSError, ValueError, VerificationError) as exc:
        print(f"ERROR: {exc}")
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
