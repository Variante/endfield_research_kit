#!/usr/bin/env python3
"""Build a validated RecoveredAclClipData JSON payload from generic ACL evidence."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import math
import struct
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def _vector(values, count: int, label: str) -> list[float]:
    if not isinstance(values, list) or len(values) != count:
        raise ValueError(f"{label} must contain {count} components")
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{label} contains a non-finite component")
    return result


def build_contract(clip_path: Path, sample_path: Path, binding_path: Path) -> dict:
    clip_bytes = clip_path.read_bytes()
    clip = json.loads(clip_bytes.decode("utf-8"))
    sample = json.loads(sample_path.read_text(encoding="utf-8"))
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    clip_name = str(clip.get("Name") or "")
    if isinstance(binding.get("clips"), list):
        matches = [row for row in binding["clips"] if row.get("name") == clip_name]
        if len(matches) != 1:
            raise ValueError("binding manifest does not contain exactly one matching clip")
        binding = matches[0]
    if not clip_name or sample.get("clip_name") != clip_name or binding.get("name") != clip_name:
        raise ValueError("clip identity disagrees across source, sample, and binding inputs")
    if sample.get("ok") is not True or sample.get("hash_ok") is not True or sample.get("validation_error") is not None:
        raise ValueError("ACL decoder did not report a validated sample")
    declared_clip_text = str(sample.get("source_json") or "")
    if not declared_clip_text:
        raise ValueError("decoded sample does not identify source_json")
    declared_clip = Path(declared_clip_text)
    if not declared_clip.is_absolute():
        declared_clip = REPO_ROOT / declared_clip
    if declared_clip.resolve() != clip_path.resolve():
        raise ValueError("decoded sample source_json differs from the supplied source clip")

    encoded = str((clip.get("m_AclCompressedBuffer") or {}).get("TransformBufferData") or "")
    try:
        acl = base64.b64decode(encoded, validate=True)
    except Exception as exc:
        raise ValueError("TransformBufferData is not valid base64") from exc
    # Endfield prefixes the ACL payload with its small transform-buffer
    # envelope; the validated ACL v2 header begins at byte 8 in current
    # exports. Keep this generic enough to accept an unwrapped ACL blob while
    # bounding the envelope rather than scanning arbitrary payload contents.
    if acl.find(struct.pack("<I", 0xAC11AC11), 0, min(len(acl), 64)) < 0:
        raise ValueError("TransformBufferData does not have bounded ACL magic")
    declared_acl = Path(str(sample.get("source_acl") or ""))
    if not declared_acl.is_absolute():
        declared_acl = REPO_ROOT / declared_acl
    if declared_acl.read_bytes() != acl:
        raise ValueError("decoded sample source_acl differs from TransformBufferData")

    track_count = int(sample.get("num_tracks") or 0)
    sample_count = int(sample.get("num_samples") or 0)
    sample_rate = float(sample.get("sample_rate") or 0.0)
    duration = float(sample.get("duration") or 0.0)
    frames = sample.get("frames")
    if track_count <= 0 or sample_count <= 0 or sample_rate <= 0 or not math.isfinite(sample_rate):
        raise ValueError("decoded sample dimensions are malformed")
    if not isinstance(frames, list) or len(frames) != sample_count:
        raise ValueError("decoded frame count disagrees with num_samples")
    expected_duration = (sample_count - 1) / sample_rate
    if not math.isfinite(duration) or abs(duration - expected_duration) > max(1e-5, expected_duration * 1e-5):
        raise ValueError("decoded duration disagrees with the uniform final sample")

    translations, rotations, scales = [], [], []
    packed = bytearray(struct.pack("<IIf", sample_count, track_count, sample_rate))
    for frame_index, frame in enumerate(frames):
        tracks = frame.get("tracks") if isinstance(frame, dict) else None
        frame_time = float(frame.get("time", math.nan)) if isinstance(frame, dict) else math.nan
        expected_time = frame_index / sample_rate
        timing_tolerance = max(1e-6, expected_time * 1e-6)
        if (frame.get("index") != frame_index or not math.isfinite(frame_time) or
                abs(frame_time - expected_time) > timing_tolerance):
            raise ValueError(f"frame {frame_index} index or uniform time is malformed")
        if not isinstance(tracks, list) or len(tracks) != track_count:
            raise ValueError(f"frame {frame_index} track count disagrees with num_tracks")
        for track_index, track in enumerate(tracks):
            prefix = f"frame {frame_index} track {track_index}"
            translation = _vector(track.get("translation"), 3, prefix + " translation")
            rotation = _vector(track.get("rotation"), 4, prefix + " rotation")
            scale = _vector(track.get("scale"), 3, prefix + " scale")
            if sum(value * value for value in rotation) <= 0.0:
                raise ValueError(prefix + " rotation is zero")
            translations.append(dict(zip("xyz", translation)))
            rotations.append(dict(zip("xyzw", rotation)))
            scales.append(dict(zip("xyz", scale)))
            packed.extend(struct.pack("<10f", *(translation + rotation + scale)))

    bindings, paths, tracks = [], set(), set()
    for row in binding.get("bones") or []:
        # Character manifests store only resolved bones; widget manifests may
        # retain unresolved rows with an explicit false marker.
        if row.get("matched") is False or row.get("track_index") is None:
            continue
        path = str(row.get("path") or "")
        track_index = int(row["track_index"])
        if not path or path in paths or track_index in tracks or not 0 <= track_index < track_count:
            raise ValueError("resolved ACL bindings contain an empty, duplicate, or invalid mapping")
        components = (
            (1 if row.get("pos_animated") is True else 0)
            | (2 if row.get("rot_animated") is True else 0)
            | (4 if row.get("scale_animated") is True else 0)
        )
        if components == 0:
            continue
        paths.add(path)
        tracks.add(track_index)
        bindings.append({
            "transformPath": path,
            "trackIndex": track_index,
            "components": components,
        })
    if not bindings:
        raise ValueError("no resolved ACL transform bindings were supplied")

    return {
        "schemaVersion": 1,
        "sourceClipName": clip_name,
        "sourceClipJsonSha256": sha256(clip_bytes),
        "sourceAclSha256": sha256(acl),
        "decodedSamplesSha256": sha256(bytes(packed)),
        "sampleRate": sample_rate,
        "duration": duration,
        "sampleCount": sample_count,
        "trackCount": track_count,
        "loopingPolicy": 1 if binding.get("loop") else 0,
        "bindings": bindings,
        "translations": translations,
        "rotations": rotations,
        "scales": scales,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clip-json", required=True, type=Path)
    parser.add_argument("--sample-json", required=True, type=Path)
    parser.add_argument("--binding-json", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    payload = build_contract(args.clip_json, args.sample_json, args.binding_json)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.output}: {payload['sampleCount']} samples x {payload['trackCount']} tracks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
