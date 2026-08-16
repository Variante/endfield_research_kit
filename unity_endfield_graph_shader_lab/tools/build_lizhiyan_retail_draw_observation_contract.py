#!/usr/bin/env python3
"""Build a fail-closed Li Zhiyan retail draw/video observation contract.

This tool only imports files. It never launches, attaches to, or injects into
the retail client. A complete runtime trace still requires separate explicit
authorization and an independently supplied capture.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence


LAB = Path(__file__).resolve().parents[1]
REPO = LAB.parent
EVIDENCE = (
    LAB / "Assets/EndfieldGraphShaderLab/Generated/OriginalData/ShaderEvidence/"
    "LiZhiyanOverviewFinger"
)
ABI = EVIDENCE / "lizhiyan_after_dof_native_abi.json"
OUTPUT = EVIDENCE / "lizhiyan_retail_draw_observation.json"
SCHEMA = "endfield.lizhiyan-retail-draw-observation.v1"
TRACE_SCHEMA = "endfield.hgmesh-draw-observation.v1"
VIDEO_SHA256 = "2F542A3BE7CE3332295D3A841FD8613C62707E084F9E33A0F156DA8A06EBF5E7"
VIDEO_BYTES = 1_678_613_397
ABI_SHA256 = "9D1179ED33D498DDFF788CA4303FED78A46E9BEC8304560945F125A9CD26A535"
UNITY_PLAYER_SHA256 = "B47728BA10F09C46E8A107B4C7055E48CFE402D3D8C88A4529074981F9672AA2"
GAME_ASSEMBLY_SHA256 = "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
METADATA_SHA256 = "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
POSITIVE_STAGES = (
    "renderer_list_register",
    "opcode_4e_consumer",
    "survivor_record_append",
    "resource_publication",
    "opcode_2748_decode",
    "descriptor_update",
    "opcode_2731_execute",
    "descriptor_bind",
    "draw",
    "queue_submit",
    "present_pixel",
)


class ObservationContractError(RuntimeError):
    pass


def require(value: bool, check: str, expected: Any, actual: Any) -> None:
    if not value:
        raise ObservationContractError(
            f"validator=lizhiyan_retail_draw_observation; check={check}; "
            f"expected={expected}; actual={actual}"
        )


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _hex(value: Any, byte_count: int, check: str) -> str:
    text = str(value).lower()
    require(len(text) == byte_count * 2, check, byte_count * 2, len(text))
    try:
        bytes.fromhex(text)
    except ValueError as exc:
        raise ObservationContractError(
            f"validator=lizhiyan_retail_draw_observation; check={check}; "
            "expected=hex; actual=invalid"
        ) from exc
    return text


def inspect_video(video: Path, ffprobe: str) -> dict[str, Any]:
    require(video.is_file(), "video_exists", True, video)
    size = video.stat().st_size
    require(size == VIDEO_BYTES, "video_bytes", VIDEO_BYTES, size)
    digest = sha256(video)
    require(digest == VIDEO_SHA256, "video_sha256", VIDEO_SHA256, digest)
    command = [
        ffprobe, "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(video),
    ]
    completed = subprocess.run(command, check=False, capture_output=True, text=True)
    require(completed.returncode == 0, "ffprobe_exit", 0, completed.returncode)
    document = json.loads(completed.stdout)
    streams = document.get("streams", [])
    video_streams = [row for row in streams if row.get("codec_type") == "video"]
    require(len(video_streams) == 1, "video_stream_count", 1, len(video_streams))
    row = video_streams[0]
    expected = {
        "index": 0,
        "codec_name": "h264",
        "profile": "High",
        "width": 3840,
        "height": 2160,
        "pix_fmt": "yuv420p",
        "color_range": "tv",
        "color_space": "bt709",
        "time_base": "1/1000",
        "avg_frame_rate": "60/1",
        "r_frame_rate": "60/1",
    }
    for key, value in expected.items():
        require(row.get(key) == value, f"video_stream_{key}", value, row.get(key))
    duration = float(document.get("format", {}).get("duration", 0.0))
    require(abs(duration - 378.367) < 0.001, "video_duration_seconds", 378.367, duration)
    return {
        "path": video.relative_to(REPO).as_posix() if video.is_relative_to(REPO) else str(video),
        "bytes": size,
        "sha256": digest,
        "streamIndex": row["index"],
        "codec": row["codec_name"],
        "profile": row["profile"],
        "dimensions": [row["width"], row["height"]],
        "pixelFormat": row["pix_fmt"],
        "colorRange": row["color_range"],
        "colorSpace": row["color_space"],
        "timeBase": row["time_base"],
        "averageFrameRate": row["avg_frame_rate"],
        "nominalFrameRate": row["r_frame_rate"],
        "durationSeconds": duration,
        "ptsRule": "integer stream PTS in 1/1000-second units; never derive timecode as frameIndex/60",
        "oracleIntervalPts": [38000, 47000],
        "strongestFeaturePts": 40000,
        "strongestFeature": "hand-adjacent teal after-DOF layer",
    }


def _load_trace(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservationContractError(
            f"validator=lizhiyan_retail_draw_observation; check=trace_json; "
            f"source={path}; actual={exc}"
        ) from exc
    require(document.get("schema") == TRACE_SCHEMA, "trace_schema", TRACE_SCHEMA,
            document.get("schema"))
    pins = document.get("sourcePins", {})
    for key, expected in (
        ("abiContractSha256", ABI_SHA256),
        ("unityPlayerSha256", UNITY_PLAYER_SHA256),
        ("gameAssemblySha256", GAME_ASSEMBLY_SHA256),
        ("metadataSha256", METADATA_SHA256),
    ):
        require(str(pins.get(key, "")).upper() == expected,
                f"trace_pin_{key}", expected, pins.get(key))
    return document


def _validate_events(trace: Mapping[str, Any], role: str) -> dict[str, Any]:
    events = trace.get("events")
    require(isinstance(events, list) and events, f"{role}_events", "nonempty list", events)
    ids: set[str] = set()
    sequences: list[int] = []
    monotonic: list[int] = []
    by_stage: dict[str, Mapping[str, Any]] = {}
    for index, event in enumerate(events):
        require(isinstance(event, dict), f"{role}_event_{index}", "object", type(event).__name__)
        event_id = str(event.get("eventId", ""))
        require(bool(event_id) and event_id not in ids, f"{role}_event_id", "unique nonempty", event_id)
        ids.add(event_id)
        seq = event.get("seq")
        tick = event.get("monotonicNs")
        require(isinstance(seq, int), f"{role}_seq", "integer", seq)
        require(isinstance(tick, int), f"{role}_monotonic", "integer", tick)
        sequences.append(seq)
        monotonic.append(tick)
        stage = str(event.get("stage", ""))
        require(stage not in by_stage, f"{role}_stage_unique", "unique", stage)
        by_stage[stage] = event
        for key in ("threadId", "frameId", "presentIntervalId"):
            require(event.get(key) is not None, f"{role}_{stage}_{key}", "present", None)
    require(sequences == sorted(sequences) and len(set(sequences)) == len(sequences),
            f"{role}_sequence_order", "strictly increasing", sequences)
    require(monotonic == sorted(monotonic), f"{role}_monotonic_order", "nondecreasing", monotonic)
    return {"events": events, "byStage": by_stage, "sequences": sequences}


def _same(events: Sequence[Mapping[str, Any]], key: str, role: str) -> Any:
    values = {str(event.get(key, "")) for event in events}
    require(len(values) == 1 and "" not in values, f"{role}_{key}_join", "one nonempty value", sorted(values))
    return next(iter(values))


def validate_positive_trace(trace: Mapping[str, Any], video: Mapping[str, Any]) -> dict[str, Any]:
    require(trace.get("role") == "lizhiyan_positive", "positive_role", "lizhiyan_positive", trace.get("role"))
    validated = _validate_events(trace, "positive")
    by_stage = validated["byStage"]
    missing = [stage for stage in POSITIVE_STAGES if stage not in by_stage]
    if missing:
        return {"complete": False, "blockedBy": [f"missing stage: {stage}" for stage in missing]}
    chain = [by_stage[stage] for stage in POSITIVE_STAGES]
    require([event["seq"] for event in chain] == sorted(event["seq"] for event in chain),
            "positive_stage_order", list(POSITIVE_STAGES), [event["stage"] for event in chain])
    frame = _same(chain, "frameId", "positive")
    present = _same(chain, "presentIntervalId", "positive")
    session = _same(chain, "sessionId", "positive")
    resource_events = chain[0:6]
    resource_id = _same(resource_events, "resourceStableId", "positive_resource")
    recorder_events = [by_stage[name] for name in ("opcode_2748_decode", "descriptor_update", "opcode_2731_execute")]
    recorder = _same(recorder_events, "recordingEpoch", "positive")
    context = _same(recorder_events, "frontContext", "positive")
    state_hash = _same([by_stage["opcode_2748_decode"], by_stage["descriptor_update"]],
                       "derivedStateSha256", "positive")
    _hex(state_hash, 32, "positive_derived_state_sha256")
    survivor = by_stage["survivor_record_append"]
    record_hex = _hex(survivor.get("recordHex"), 64, "positive_record_hex")
    require(record_hex[64:72] != "ffffffff", "positive_record_marker", "not ffffffff", record_hex[64:72])
    descriptor = _same([by_stage["descriptor_update"], by_stage["descriptor_bind"]],
                       "descriptorSet", "positive")
    command_buffer = _same([by_stage["descriptor_bind"], by_stage["draw"], by_stage["queue_submit"]],
                           "commandBuffer", "positive")
    pixel = by_stage["present_pixel"]
    require(str(pixel.get("videoSha256", "")).upper() == VIDEO_SHA256,
            "positive_pixel_video_sha256", VIDEO_SHA256, pixel.get("videoSha256"))
    pts = pixel.get("pts")
    require(isinstance(pts, int) and video["oracleIntervalPts"][0] <= pts <= video["oracleIntervalPts"][1],
            "positive_pixel_pts", video["oracleIntervalPts"], pts)
    require(pixel.get("timeBase") == "1/1000", "positive_pixel_time_base", "1/1000", pixel.get("timeBase"))
    require(pixel.get("actorIsolation") == "lizhiyan_only", "positive_actor_isolation", "lizhiyan_only", pixel.get("actorIsolation"))
    require(pixel.get("visibleAfterDofTeal") is True, "positive_visible_teal", True, pixel.get("visibleAfterDofTeal"))
    _hex(pixel.get("decodedFrameSha256"), 32, "positive_decoded_frame_sha256")
    return {
        "complete": True,
        "blockedBy": [],
        "sessionId": session,
        "frameId": frame,
        "presentIntervalId": present,
        "resourceStableId": resource_id,
        "recordingEpoch": recorder,
        "frontContext": context,
        "derivedStateSha256": state_hash,
        "descriptorSet": descriptor,
        "commandBuffer": command_buffer,
        "drawKind": by_stage["draw"].get("drawKind"),
        "pixelPts": pts,
        "targetSignature": trace.get("targetSignature"),
    }


def validate_negative_trace(trace: Mapping[str, Any], positive: Mapping[str, Any]) -> dict[str, Any]:
    require(trace.get("role") in ("lizhiyan_absent", "wulfa"),
            "negative_role", ["lizhiyan_absent", "wulfa"], trace.get("role"))
    validated = _validate_events(trace, "negative")
    require(trace.get("captureProfile") == "same_build_camera_and_settings",
            "negative_capture_profile", "same_build_camera_and_settings", trace.get("captureProfile"))
    matching = [event for event in validated["events"] if event.get("targetSignature") == positive.get("targetSignature")]
    require(not matching, "negative_target_signature_absent", [], [event.get("eventId") for event in matching])
    return {"complete": True, "role": trace["role"], "matchingTargetEvents": 0}


def build_contract(video: Mapping[str, Any], positive_path: Path | None,
                   negative_path: Path | None) -> dict[str, Any]:
    abi_hash = sha256(ABI)
    require(abi_hash == ABI_SHA256, "abi_sha256", ABI_SHA256, abi_hash)
    blocked: list[str] = []
    positive_result: dict[str, Any] | None = None
    negative_result: dict[str, Any] | None = None
    trace_sources: list[dict[str, Any]] = []
    if positive_path is None:
        blocked.append("authorized Li Zhiyan runtime observation trace is absent")
    else:
        positive_trace = _load_trace(positive_path)
        positive_result = validate_positive_trace(positive_trace, video)
        trace_sources.append({"role": "positive", "path": str(positive_path), "sha256": sha256(positive_path)})
        blocked.extend(positive_result.get("blockedBy", []))
    if negative_path is None:
        blocked.append("same-build Li-absent or Wulfa negative-control trace is absent")
    elif positive_result is None or not positive_result.get("complete"):
        blocked.append("negative control cannot be evaluated before a complete positive chain")
    else:
        negative_trace = _load_trace(negative_path)
        negative_result = validate_negative_trace(negative_trace, positive_result)
        trace_sources.append({"role": "negative", "path": str(negative_path), "sha256": sha256(negative_path)})
    admitted = not blocked and bool(positive_result and positive_result.get("complete")) and bool(negative_result and negative_result.get("complete"))
    return {
        "schema": SCHEMA,
        "status": "proved" if admitted else "proof_pending",
        "visibleAdmission": admitted,
        "importerBoundary": {
            "offlineOnly": True,
            "launchedRetailClient": False,
            "attachedToRetailClient": False,
            "injectedIntoRetailClient": False,
            "captureRequiresSeparateExplicitAuthorization": True,
        },
        "sources": {
            "abiContract": {"path": ABI.relative_to(REPO).as_posix(), "sha256": abi_hash},
            "video": dict(video),
            "traces": trace_sources,
        },
        "positiveJoin": positive_result,
        "negativeControl": negative_result,
        "requirements": list(POSITIVE_STAGES),
        "blockedBy": blocked,
        "nonClaims": [
            "video metadata or teal pixels alone do not identify a Vulkan draw",
            "generic API-2 descriptor, indirect-draw, or submit events are not HGMesh ownership",
            "pointer equality without resource generation and stable identity is not a join",
            "timestamps do not replace event sequence, frame, recorder, command-buffer, and present identities",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, default=REPO / "videos/2026-08-15_10-32-32.mkv")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--positive-trace", type=Path)
    parser.add_argument("--negative-trace", type=Path)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    video = inspect_video(args.video.resolve(), args.ffprobe)
    contract = build_contract(video, args.positive_trace, args.negative_trace)
    rendered = json.dumps(contract, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        require(args.output.is_file(), "output_exists", True, args.output)
        require(args.output.read_text(encoding="utf-8") == rendered,
                "output_current", "generated bytes", "drifted")
        print(f"Li Zhiyan retail draw observation verified: status={contract['status']}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}: status={contract['status']}, visibleAdmission={contract['visibleAdmission']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
