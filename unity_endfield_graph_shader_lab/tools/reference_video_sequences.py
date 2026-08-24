"""Extract configured retail-video intervals as reproducible frame sequences."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "reference_video_sequences.json"
SAFE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]*$")
FRAME_NAME = re.compile(r"^frame_(\d{6})\.png$")


class PipelineError(RuntimeError):
    pass


def sha256_file(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(4 << 20), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def load_config(path: Path) -> dict:
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PipelineError(f"cannot read config {path}: {error}") from error
    if config.get("schema") != "endfield.character-reference-video.v1":
        raise PipelineError("unsupported or missing config schema")
    if not isinstance(config.get("recordings"), list) or not config["recordings"]:
        raise PipelineError("config must contain recordings")
    return config


def probe(path: Path) -> dict:
    command = [
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "format=duration:stream=width,height,avg_frame_rate",
        "-of", "json", str(path),
    ]
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
        payload = json.loads(result.stdout)
        stream = payload["streams"][0]
        numerator, denominator = stream["avg_frame_rate"].split("/", 1)
        return {
            "width": int(stream["width"]),
            "height": int(stream["height"]),
            "fps": float(numerator) / float(denominator),
            "duration": float(payload["format"]["duration"]),
        }
    except FileNotFoundError as error:
        raise PipelineError("ffprobe is not on PATH") from error
    except (subprocess.CalledProcessError, KeyError, ValueError, json.JSONDecodeError) as error:
        raise PipelineError(f"ffprobe failed for {path}: {error}") from error


def _identifier(value: object, label: str) -> str:
    result = str(value or "").lower()
    if not SAFE_ID.fullmatch(result):
        raise PipelineError(f"invalid {label}: {value!r}")
    return result


def expand_segments(recording: dict, duration: float) -> list[dict]:
    explicit = recording.get("segments")
    markers = recording.get("markers")
    if bool(explicit) == bool(markers):
        raise PipelineError(f"{recording.get('id')}: provide exactly one of segments or markers")
    rows = []
    if explicit:
        rows = [dict(row) for row in explicit]
    else:
        for index, marker in enumerate(markers):
            row = dict(marker)
            row["id"] = row.get("id") or f"{row.get('character')}_overview_{index + 1:02d}"
            row["behavior"] = row.get("behavior") or "observed_character_info_interval"
            row["startSeconds"] = marker.get("atSeconds")
            row["endSeconds"] = (
                markers[index + 1].get("atSeconds") if index + 1 < len(markers) else duration
            )
            rows.append(row)
    previous_end = -1.0
    for row in rows:
        row["id"] = _identifier(row.get("id"), "segment id")
        row["character"] = _identifier(row.get("character"), "character")
        try:
            start = float(row["startSeconds"])
            end = float(row["endSeconds"])
        except (KeyError, TypeError, ValueError) as error:
            raise PipelineError(f"{row['id']}: invalid start/end seconds") from error
        if start < 0 or end <= start or end > duration + 0.05:
            raise PipelineError(f"{row['id']}: interval {start}..{end} outside 0..{duration}")
        if start < previous_end - 0.0001:
            raise PipelineError(f"{row['id']}: segments overlap or are out of order")
        row["startSeconds"], row["endSeconds"] = start, min(end, duration)
        if row.get("startFrame") is not None:
            try:
                row["startFrame"] = int(row["startFrame"])
            except (TypeError, ValueError) as error:
                raise PipelineError(f"{row['id']}: invalid one-based startFrame") from error
            if row["startFrame"] < 1:
                raise PipelineError(f"{row['id']}: startFrame must be one-based and positive")
        previous_end = end
    return rows


def planned_sequences(config_path: Path, config: dict, args) -> list[dict]:
    output_root = (PROJECT_ROOT / config.get("outputRoot", "scratch/character_recovery/reference_sequences")).resolve()
    if PROJECT_ROOT not in output_root.parents:
        raise PipelineError("outputRoot must stay inside the Unity project")
    defaults = config.get("defaults") or {}
    fps = float(args.fps or defaults.get("fps", 60))
    if fps <= 0 or fps > 240:
        raise PipelineError("fps must be greater than 0 and at most 240")
    plans = []
    seen_recordings = set()
    for recording in config["recordings"]:
        recording_id = _identifier(recording.get("id"), "recording id")
        if recording_id in seen_recordings:
            raise PipelineError(f"duplicate recording id: {recording_id}")
        seen_recordings.add(recording_id)
        if args.recording and recording_id != args.recording:
            continue
        source = (PROJECT_ROOT / str(recording.get("source", ""))).resolve()
        if not source.is_file():
            raise PipelineError(f"{recording_id}: source video not found: {source}")
        metadata = probe(source)
        expected = recording.get("resolution")
        if expected and list(expected) != [metadata["width"], metadata["height"]]:
            raise PipelineError(
                f"{recording_id}: resolution {metadata['width']}x{metadata['height']} "
                f"does not match configured {expected[0]}x{expected[1]}"
            )
        for segment in expand_segments(recording, metadata["duration"]):
            if args.character and segment["character"] != args.character:
                continue
            if args.segment and segment["id"] != args.segment:
                continue
            destination = output_root / recording_id / segment["character"] / segment["id"]
            plans.append({
                "recordingId": recording_id,
                "source": source,
                "sourceMetadata": metadata,
                "segment": segment,
                "destination": destination,
                "fps": fps,
                "scale": args.scale,
                "pixelFormat": defaults.get("pixelFormat", "rgb24"),
                "videoDecoder": None if args.software_decode else (args.decoder or defaults.get("videoDecoder")),
            })
    if (args.recording or args.character or args.segment) and not plans:
        raise PipelineError("filters matched no configured sequences")
    return plans


def ffmpeg_command(plan: dict, partial: Path) -> list[str]:
    segment = plan["segment"]
    if segment.get("startFrame") is not None:
        filters = [
            f"trim=start_frame={segment['startFrame'] - 1}:end={segment['endSeconds']:.12g}",
            "setpts=PTS-STARTPTS",
            f"fps={plan['fps']:.12g}",
        ]
        input_window = ["-i", str(plan["source"])]
    else:
        filters = [f"fps={plan['fps']:.12g}"]
        input_window = [
            "-ss", f"{segment['startSeconds']:.6f}", "-i", str(plan["source"]),
            "-t", f"{segment['endSeconds'] - segment['startSeconds']:.6f}",
        ]
    if plan["scale"]:
        filters.append(f"scale={plan['scale']}")
    return [
        "ffmpeg", "-hide_banner", "-loglevel", "warning", "-nostdin", "-y",
        *(["-c:v", plan["videoDecoder"]] if plan["videoDecoder"] else []),
        *input_window,
        "-an", "-vf", ",".join(filters), "-pix_fmt", plan["pixelFormat"],
        "-start_number", "1", str(partial / "frame_%06d.png"),
    ]


def plan_contract(plan: dict) -> dict:
    partial = plan["destination"].with_name(plan["destination"].name + ".partial")
    return {
        "recordingId": plan["recordingId"],
        "character": plan["segment"]["character"],
        "segment": plan["segment"],
        "source": {
            "path": str(plan["source"].relative_to(PROJECT_ROOT.parent)).replace("\\", "/"),
            **plan["sourceMetadata"],
        },
        "output": {
            "fps": plan["fps"],
            "scale": plan["scale"],
            "pixelFormat": plan["pixelFormat"],
            "videoDecoder": plan["videoDecoder"] or "ffmpeg_software_default",
        },
        "ffmpegCommand": ffmpeg_command(plan, partial),
    }


def validate_sidecar_contract(plan: dict, sidecar: dict) -> None:
    expected = plan_contract(plan)
    for label in ("recordingId", "character", "segment", "ffmpegCommand"):
        if sidecar.get(label) != expected[label]:
            raise PipelineError(f"sidecar {label} does not match current plan: {plan['destination']}")
    for section in ("source", "output"):
        actual_section = sidecar.get(section) or {}
        for key, value in expected[section].items():
            if actual_section.get(key) != value:
                raise PipelineError(
                    f"sidecar {section}.{key} does not match current plan: {plan['destination']}"
                )


def frame_files(destination: Path) -> list[Path]:
    files = sorted(destination.glob("frame_*.png"))
    for index, path in enumerate(files, 1):
        match = FRAME_NAME.fullmatch(path.name)
        if match is None or int(match.group(1)) != index:
            raise PipelineError(f"non-contiguous frame sequence in {destination}")
    return files


def extract(plan: dict, force: bool, resume: bool, dry_run: bool) -> None:
    destination = plan["destination"]
    partial = destination.with_name(destination.name + ".partial")
    command = ffmpeg_command(plan, partial)
    if dry_run:
        print(subprocess.list2cmdline(command))
        return
    if destination.exists() and resume:
        check(plan)
        print(f"skip completed {destination.relative_to(PROJECT_ROOT)}")
        return
    if destination.exists() and not force:
        raise PipelineError(f"output exists (use --resume or --force): {destination}")
    for target in (partial, destination if force else None):
        if target and target.exists():
            if PROJECT_ROOT not in target.resolve().parents:
                raise PipelineError(f"refusing to remove path outside project: {target}")
            shutil.rmtree(target)
    partial.mkdir(parents=True)
    try:
        subprocess.run(command, check=True)
    except FileNotFoundError as error:
        raise PipelineError("ffmpeg is not on PATH") from error
    except subprocess.CalledProcessError as error:
        raise PipelineError(f"ffmpeg failed with exit code {error.returncode}") from error
    files = frame_files(partial)
    expected = round((plan["segment"]["endSeconds"] - plan["segment"]["startSeconds"]) * plan["fps"])
    if not files or abs(len(files) - expected) > 1:
        raise PipelineError(f"unexpected frame count for {destination}: {len(files)} vs about {expected}")
    source_size, source_hash = plan["sourcePin"]
    contract = plan_contract(plan)
    sidecar = {
        "schema": "endfield.character-reference-sequence.v1",
        "boundary": "recorded_retail_video_measurement",
        "recordingId": contract["recordingId"],
        "character": contract["character"],
        "segment": contract["segment"],
        "source": {
            **contract["source"],
            "bytes": source_size,
            "sha256": source_hash,
        },
        "output": {
            **contract["output"],
            "frameCount": len(files),
            "firstFrameSourceSeconds": plan["segment"]["startSeconds"],
            "firstSourceFrame": plan["segment"].get("startFrame"),
            "timestampRule": "sourceSeconds = startSeconds + (frameNumber - 1) / fps; firstSourceFrame is exact when present",
        },
        "ffmpegCommand": contract["ffmpegCommand"],
    }
    (partial / "sequence.json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
    partial.replace(destination)
    print(f"wrote {destination.relative_to(PROJECT_ROOT)} ({len(files)} frames)")


def check(plan: dict) -> None:
    destination = plan["destination"]
    sidecar_path = destination / "sequence.json"
    if not sidecar_path.is_file():
        raise PipelineError(f"missing sidecar: {sidecar_path}")
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    if sidecar.get("schema") != "endfield.character-reference-sequence.v1":
        raise PipelineError(f"invalid sidecar schema: {sidecar_path}")
    validate_sidecar_contract(plan, sidecar)
    size, digest = plan["sourcePin"]
    source = sidecar.get("source") or {}
    if source.get("bytes") != size or source.get("sha256") != digest:
        raise PipelineError(f"source pin changed: {plan['source']}")
    files = frame_files(destination)
    recorded = (sidecar.get("output") or {}).get("frameCount")
    if recorded != len(files):
        raise PipelineError(f"frame count changed: {destination} ({len(files)} != {recorded})")
    expected = round((plan["segment"]["endSeconds"] - plan["segment"]["startSeconds"]) * plan["fps"])
    if abs(len(files) - expected) > 1:
        raise PipelineError(f"unexpected frame count: {destination} ({len(files)} vs about {expected})")
    print(f"ok {destination.relative_to(PROJECT_ROOT)} ({len(files)} frames)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--recording")
    parser.add_argument("--character")
    parser.add_argument("--segment")
    parser.add_argument("--fps", type=float)
    parser.add_argument("--scale", help="FFmpeg scale WIDTH:HEIGHT, for example 1920:-2")
    decoder = parser.add_mutually_exclusive_group()
    decoder.add_argument("--decoder", help="FFmpeg video decoder name, overriding config")
    decoder.add_argument("--software-decode", action="store_true", help="disable the configured GPU decoder")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    try:
        config_path = args.config.resolve()
        config = load_config(config_path)
        plans = planned_sequences(config_path, config, args)
        if not args.list and not args.dry_run:
            source_pins = {}
            for plan in plans:
                if plan["source"] not in source_pins:
                    source_pins[plan["source"]] = sha256_file(plan["source"])
                plan["sourcePin"] = source_pins[plan["source"]]
        if args.list:
            for plan in plans:
                segment = plan["segment"]
                print(f"{plan['recordingId']}: {segment['character']}/{segment['id']} "
                      f"{segment['startSeconds']:.4f}..{segment['endSeconds']:.4f}s "
                      f"({segment.get('behavior', 'unlabeled')})")
        elif args.check:
            for plan in plans:
                check(plan)
        else:
            for plan in plans:
                extract(plan, args.force, args.resume, args.dry_run)
    except (PipelineError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
