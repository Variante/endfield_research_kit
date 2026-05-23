#!/usr/bin/env python3
"""OCR gameplay videos as observed scene-order evidence.

The tool is intentionally incremental: completed videos are skipped on later
runs when a matching per-video report already exists. Partial download
fragments such as `.m4s` and `.lock` files are ignored by default.

This is the lower-level OCR worker. For the full OCR-to-story-order pipeline,
prefer:

    python scripts/story_recovery/build_gameplay_video_story_order.py --run-ocr

Direct OCR-only runs are still useful for diagnostics:

    python scripts/story_recovery/build_gameplay_video_ocr_audit.py
    python scripts/story_recovery/build_gameplay_video_ocr_audit.py --frame-step 45
    python scripts/story_recovery/build_gameplay_video_ocr_audit.py --dry-run
"""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import re
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT / "scripts",):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from common import (  # noqa: E402
    REPORTS_DIR,
    md_escape,
    read_json,
    rel_path,
    safe_key,
    write_report_json,
    write_text_if_changed,
)


VIDEO_ROOT = ROOT / "videos"
REPORT_DIR = REPORTS_DIR / "gameplay_video_ocr"
TMP_ROOT = ROOT / "tmp" / "gameplay_video_ocr"
FRAME_CACHE_ROOT = TMP_ROOT / "frames"
INDEX_PATH = REPORT_DIR / "gameplay_video_ocr_index.json"
INDEX_MD_PATH = REPORT_DIR / "gameplay_video_ocr_index.md"
DEFAULT_EASYOCR_MODEL_DIR = ROOT / "tools" / "easyocr"
DARK_SCREEN_ROI_TOP = 0.10
DARK_SCREEN_ROI_BOTTOM = 0.97
DARK_SCREEN_CACHE_SUBDIR = "dark_roi_10_97"
ARCHIVE_BOX_CACHE_SUBDIR = "archive_box_full"
ARCHIVE_BOX_PANEL_CACHE_SUBDIR = "archive_box_panel"

TOOL_VERSION = 6
VIDEO_EXTENSIONS = {".mp4"}
NON_CONTENT_PARAM_KEYS = {
    "easyocrGpu",
    "easyocrModelDir",
    "easyocrFrameBatchSize",
    "easyocrBatchSize",
    "ffmpegHwaccel",
    "framePrefilter",
    "keepFrames",
    "prefilterDuplicateThreshold",
    "prefilterBlankStddev",
    "prefilterBlankBrightRatio",
    "prefilterBrightThreshold",
    "prefilterFocusHeight",
}
PARTIAL_SUFFIXES = (
    ".lock",
    ".m4s",
    ".video.m4s",
    ".audio.m4s",
    ".part",
    ".tmp",
    ".download",
    ".crdownload",
)
MISSION_ID_RE = re.compile(r"(?<![A-Za-z0-9])([a-z][a-z0-9]*m[0-9]+(?:d[0-9]+)?)(?![A-Za-z0-9])", re.I)
PART_RE = re.compile(r"(?:^|[_\-\s])P(?P<part>[0-9]{1,3})(?:[_\-\s]|$)", re.I)
SAFE_STEM_RE = re.compile(r"[^A-Za-z0-9_.-]+")
WHITESPACE_RE = re.compile(r"\s+")
OCR_NOISE_RE = re.compile(r"^[\W_]+$", re.UNICODE)
UID_RE = re.compile(r"\b(?:u\s*)?id\s*[:：]?\s*[0-9]{4,}\b", re.I)
LATENCY_RE = re.compile(r"\b[0-9]{1,4}\s*ms\b", re.I)
ASCII_WORD_RE = re.compile(r"[A-Za-z]{2,}")
CJK_SPAN_RE = re.compile(r"[\u3400-\u9fff0-9，。！？、；：“”‘’（）《》…—\-\.!? ]+")
BLACKFRAME_RE = re.compile(r"\bframe:(?P<sample>[0-9]+)\s+pblack:(?P<pblack>[0-9]+)")


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def safe_report_stem(path: Path) -> str:
    stem = path.stem
    stem = SAFE_STEM_RE.sub("_", stem).strip("._")
    return stem[:160] or "video"


def run_command(args: list[str], *, cwd: Path | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if check and proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(detail or f"command failed with exit code {proc.returncode}: {' '.join(args)}")
    return proc


def resolve_executable(name: str, explicit: str | None = None) -> str | None:
    if explicit:
        path = Path(explicit)
        if path.is_file():
            return str(path)
        return explicit
    found = shutil.which(name)
    if found:
        return found
    return None


def parse_rate(value: Any) -> float | None:
    text = safe_key(value)
    if not text or text == "0/0":
        return None
    try:
        if "/" in text:
            rate = Fraction(text)
            if rate.denominator:
                return float(rate)
        return float(text)
    except (ValueError, ZeroDivisionError):
        return None


def seconds_to_clock(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return ""
    total_ms = max(0, int(round(seconds * 1000)))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    total_m = total_s // 60
    m = total_m % 60
    h = total_m // 60
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def short_duration(seconds: float | None) -> str:
    if seconds is None or not math.isfinite(seconds):
        return "?"
    seconds = max(0.0, seconds)
    if seconds < 60:
        return f"{seconds:.0f}s"
    minutes, secs = divmod(int(seconds), 60)
    if minutes < 60:
        return f"{minutes}m{secs:02d}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h{minutes:02d}m"


def one_line(text: str, *, limit: int = 180) -> str:
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if len(line) > limit:
        return line[: limit - 3] + "..."
    return line


def progress_bar(
    label: str,
    current: int,
    total: int,
    *,
    started: float,
    force: bool = False,
    width: int = 28,
) -> None:
    if total <= 0:
        return
    now = time.monotonic()
    if not force and now - getattr(progress_bar, "_last", 0.0) < 1.0:
        return
    progress_bar._last = now  # type: ignore[attr-defined]
    current = min(max(current, 0), total)
    ratio = current / total if total else 0.0
    filled = int(round(width * ratio))
    elapsed = now - started
    eta = (elapsed / current * (total - current)) if current else None
    line = (
        f"\r{label} [{('#' * filled).ljust(width, '-')}] "
        f"{current}/{total} {ratio * 100:5.1f}% "
        f"elapsed {short_duration(elapsed)} eta {short_duration(eta)}"
    )
    sys.stdout.write(line)
    if force or current >= total:
        sys.stdout.write("\n")
    sys.stdout.flush()


def release_ocr_memory(*, cuda: bool) -> None:
    gc.collect()
    if not cuda:
        return
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return
    if not torch.cuda.is_available():
        return
    torch.cuda.empty_cache()
    try:
        torch.cuda.ipc_collect()
    except Exception:
        pass


def cjk_count(text: str) -> int:
    return sum(1 for ch in text if "\u3400" <= ch <= "\u9fff")


def ascii_letter_count(text: str) -> int:
    return sum(1 for ch in text if ("A" <= ch <= "Z") or ("a" <= ch <= "z"))


def normalized_char_count(text: str) -> int:
    return sum(1 for ch in text if ch.isalnum() or ("\u3400" <= ch <= "\u9fff"))


def symbol_ratio(text: str) -> float:
    compact = "".join(ch for ch in text if not ch.isspace())
    if not compact:
        return 1.0
    useful = normalized_char_count(compact)
    return max(0.0, (len(compact) - useful) / len(compact))


def is_short_cjk_name_like(text: str, args: argparse.Namespace) -> bool:
    if args.drop_short_cjk_names:
        return False
    compact = "".join(ch for ch in text if not ch.isspace())
    cjk = cjk_count(compact)
    if cjk < args.min_cjk_chars or cjk > 4:
        return False
    return cjk == normalized_char_count(compact) and symbol_ratio(compact) <= args.max_symbol_ratio


def strip_overlay_text(text: str) -> str:
    text = UID_RE.sub(" ", text)
    text = LATENCY_RE.sub(" ", text)
    return WHITESPACE_RE.sub(" ", text).strip()


def best_cjk_span(text: str) -> str:
    if cjk_count(text) <= 0:
        return text
    candidates = [
        WHITESPACE_RE.sub(" ", match.group(0)).strip(" _-|")
        for match in CJK_SPAN_RE.finditer(text)
    ]
    candidates = [candidate for candidate in candidates if cjk_count(candidate) > 0]
    if not candidates:
        return text
    return max(candidates, key=lambda candidate: (cjk_count(candidate), normalized_char_count(candidate), len(candidate)))


def passes_ocr_quality(text: str, args: argparse.Namespace) -> bool:
    if is_short_cjk_name_like(text, args):
        return True
    if len(text) < args.min_text_length:
        return False
    if normalized_char_count(text) < args.min_normalized_chars:
        return False
    if symbol_ratio(text) > args.max_symbol_ratio:
        return False
    cjk = cjk_count(text)
    if cjk >= args.min_cjk_chars:
        return True
    if not args.keep_english_only:
        return False
    # Keep English OCR possible, but require enough word-shaped evidence.
    ascii_letters = ascii_letter_count(text)
    words = ASCII_WORD_RE.findall(text)
    return ascii_letters >= args.min_ascii_letters and len(words) >= args.min_ascii_words


def normalize_ocr_text(text: str, args: argparse.Namespace | None = None) -> str:
    text = text.replace("\ufeff", "")
    lines = []
    for raw_line in text.splitlines():
        line = WHITESPACE_RE.sub(" ", raw_line).strip()
        if args is not None and not args.keep_overlay_text:
            line = strip_overlay_text(line)
        if args is not None and not args.keep_mixed_ocr_lines:
            line = best_cjk_span(line)
        if not line:
            continue
        if OCR_NOISE_RE.match(line):
            continue
        if args is not None and not passes_ocr_quality(line, args):
            continue
        lines.append(line)
    return "\n".join(lines)


def infer_missions(path: Path) -> list[str]:
    missions: list[str] = []
    seen: set[str] = set()
    for match in MISSION_ID_RE.finditer(path.stem):
        mission = match.group(1).lower()
        if mission in seen:
            continue
        seen.add(mission)
        missions.append(mission)
    return missions


def infer_part(path: Path) -> int | None:
    match = PART_RE.search(path.stem)
    if not match:
        return None
    try:
        return int(match.group("part"))
    except ValueError:
        return None


def video_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": rel_path(path),
        "name": path.name,
        "size": stat.st_size,
        "mtimeNs": stat.st_mtime_ns,
    }


def ffprobe_video(path: Path, ffprobe: str) -> dict[str, Any]:
    args = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,r_frame_rate,nb_frames,duration:format=duration",
        "-of",
        "json",
        str(path),
    ]
    proc = run_command(args)
    payload = json.loads(proc.stdout or "{}")
    streams = payload.get("streams") or []
    stream = streams[0] if streams and isinstance(streams[0], dict) else {}
    fmt = payload.get("format") if isinstance(payload.get("format"), dict) else {}
    duration_raw = stream.get("duration") or fmt.get("duration")
    duration = None
    try:
        duration = float(duration_raw) if duration_raw is not None else None
    except (TypeError, ValueError):
        duration = None
    nb_frames = None
    try:
        nb_frames = int(stream.get("nb_frames")) if stream.get("nb_frames") else None
    except (TypeError, ValueError):
        nb_frames = None
    fps = parse_rate(stream.get("avg_frame_rate")) or parse_rate(stream.get("r_frame_rate"))
    width = int(stream.get("width") or 0)
    height = int(stream.get("height") or 0)
    if nb_frames is None and duration and fps:
        nb_frames = int(round(duration * fps))
    return {
        "width": width,
        "height": height,
        "fps": fps,
        "durationSeconds": duration,
        "duration": seconds_to_clock(duration),
        "frameCountEstimate": nb_frames,
        "raw": {
            "avgFrameRate": stream.get("avg_frame_rate"),
            "rFrameRate": stream.get("r_frame_rate"),
            "nbFrames": stream.get("nb_frames"),
            "streamDuration": stream.get("duration"),
            "formatDuration": fmt.get("duration"),
        },
    }


def ffmpeg_supports_cuda(ffmpeg: str) -> bool:
    proc = run_command([ffmpeg, "-hide_banner", "-hwaccels"], check=False)
    text = f"{proc.stdout}\n{proc.stderr}".lower()
    return proc.returncode == 0 and "cuda" in text


def ffmpeg_hwaccel_args(hwaccel: str) -> list[str]:
    if hwaccel == "cuda":
        return ["-hwaccel", "cuda"]
    return []


def run_ffmpeg_extract(args: list[str], *, fallback_args: list[str] | None, label: str) -> subprocess.CompletedProcess[str]:
    proc = run_command(args, check=False)
    if proc.returncode == 0:
        return proc
    if fallback_args is None:
        detail = (proc.stderr or proc.stdout or "").strip()
        raise RuntimeError(detail or f"ffmpeg failed with exit code {proc.returncode}")
    detail = one_line(proc.stderr or proc.stdout or "")
    print(f"{label} ffmpeg CUDA decode failed; retrying CPU decode: {detail}", file=sys.stderr)
    fallback_proc = run_command(fallback_args, check=False)
    if fallback_proc.returncode != 0:
        fallback_detail = (fallback_proc.stderr or fallback_proc.stdout or "").strip()
        raise RuntimeError(fallback_detail or f"ffmpeg CPU fallback failed with exit code {fallback_proc.returncode}")
    return fallback_proc


def params_signature(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "toolVersion": TOOL_VERSION,
        "ocrEngine": "easyocr",
        "ffmpegHwaccel": args.ffmpeg_hwaccel,
        "frameStep": args.frame_step,
        "crop": args.crop,
        "scale": args.scale,
        "ocrLang": args.ocr_lang,
        "easyocrGpu": not bool(args.easyocr_cpu),
        "easyocrModelDir": rel_path(args.easyocr_model_dir) if args.easyocr_model_dir else "",
        "easyocrFrameBatchSize": args.easyocr_frame_batch_size,
        "easyocrBatchSize": args.easyocr_batch_size,
        "easyocrMinConfidence": args.easyocr_min_confidence,
        "minTextLength": args.min_text_length,
        "minNormalizedChars": args.min_normalized_chars,
        "minCjkChars": args.min_cjk_chars,
        "minAsciiLetters": args.min_ascii_letters,
        "minAsciiWords": args.min_ascii_words,
        "maxSymbolRatio": args.max_symbol_ratio,
        "keepOverlayText": bool(args.keep_overlay_text),
        "keepMixedOcrLines": bool(args.keep_mixed_ocr_lines),
        "keepEnglishOnly": bool(args.keep_english_only),
        "keepShortCjkNames": not bool(args.drop_short_cjk_names),
        "darkFullscreenOcr": not bool(args.disable_dark_fullscreen_ocr),
        "darkFrameThreshold": args.dark_frame_threshold,
        "darkPixelThreshold": args.dark_pixel_threshold,
        "darkRoiTop": DARK_SCREEN_ROI_TOP,
        "darkRoiBottom": DARK_SCREEN_ROI_BOTTOM,
        "archiveBoxOcr": not bool(args.disable_archive_box_ocr),
        "archiveBoxLightThreshold": args.archive_box_light_threshold,
        "archiveBoxMinBrightRatio": args.archive_box_min_bright_ratio,
        "archiveBoxMinAreaRatio": args.archive_box_min_area_ratio,
        "archiveBoxMinWidthRatio": args.archive_box_min_width_ratio,
        "archiveBoxMinHeightRatio": args.archive_box_min_height_ratio,
        "archiveBoxMinFillRatio": args.archive_box_min_fill_ratio,
        "archiveBoxCropPadding": args.archive_box_crop_padding,
        "archiveBoxScale": args.archive_box_scale,
        "framePrefilter": not bool(args.disable_frame_prefilter),
        "prefilterDuplicateThreshold": args.prefilter_duplicate_threshold,
        "prefilterMaxDuplicateSkip": args.prefilter_max_duplicate_skip,
        "prefilterBlankStddev": args.prefilter_blank_stddev,
        "prefilterBlankBrightRatio": args.prefilter_blank_bright_ratio,
        "prefilterBrightThreshold": args.prefilter_bright_threshold,
        "prefilterFocusHeight": args.prefilter_focus_height,
        "limitFrames": args.limit_frames,
        "includeEmpty": bool(args.include_empty),
        "keepFrames": bool(args.keep_frames),
    }


def same_fingerprint(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return (
        safe_key(a.get("path")) == safe_key(b.get("path"))
        and a.get("size") == b.get("size")
        and a.get("mtimeNs") == b.get("mtimeNs")
    )


def comparable_params(params: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in params.items()
        if key not in NON_CONTENT_PARAM_KEYS
    }


def reusable_complete_report(payload: dict[str, Any], params: dict[str, Any]) -> bool:
    if payload.get("status") != "complete":
        return False
    report_params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    if comparable_params(report_params) != comparable_params(params):
        return False
    report_limit_frames = report_params.get("limitFrames")
    current_limit_frames = params.get("limitFrames")
    if report_limit_frames is not None:
        return report_limit_frames == current_limit_frames
    return True


def is_completed_report(path: Path, fingerprint: dict[str, Any], params: dict[str, Any]) -> bool:
    if not path.exists():
        return False
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        return False
    if not reusable_complete_report(payload, params):
        return False
    return same_fingerprint(payload.get("source") or {}, fingerprint)


def existing_report_state(path: Path, fingerprint: dict[str, Any], params: dict[str, Any]) -> tuple[str, str]:
    if not path.exists():
        return ("missing", "")
    payload = read_json(path, {})
    if not isinstance(payload, dict):
        return ("missing", "")
    status = safe_key(payload.get("status")) or "unknown"
    if not same_fingerprint(payload.get("source") or {}, fingerprint):
        return (f"stale-source:{status}", safe_key(payload.get("error")))
    if reusable_complete_report(payload, params):
        return ("complete", "")
    if status == "complete":
        return (f"stale-params:{status}", safe_key(payload.get("error")))
    report_params = payload.get("parameters")
    if not isinstance(report_params, dict) or comparable_params(report_params) != comparable_params(params):
        return (f"stale-params:{status}", safe_key(payload.get("error")))
    return (f"retry:{status}", safe_key(payload.get("error")))


def discover_videos(video_root: Path, filters: list[str]) -> list[Path]:
    if not video_root.is_dir():
        return []
    filters_lower = [item.lower() for item in filters]
    out: list[Path] = []
    for path in sorted(video_root.iterdir(), key=lambda item: item.name.lower()):
        if not path.is_file():
            continue
        name_lower = path.name.lower()
        if any(name_lower.endswith(suffix) for suffix in PARTIAL_SUFFIXES):
            continue
        if path.suffix.lower() not in VIDEO_EXTENSIONS:
            continue
        if path.stat().st_size <= 0:
            continue
        if (path.parent / f"{path.name}.lock").exists():
            continue
        if filters_lower and not any(item in name_lower for item in filters_lower):
            continue
        out.append(path)
    return out


def build_sample_select(frame_step: int, limit_frames: int | None = None) -> str:
    expr = f"not(mod(n\\,{frame_step}))"
    if limit_frames:
        expr = f"{expr}*lt(n\\,{frame_step * limit_frames})"
    return f"select='{expr}'"


def build_crop_filter(crop: str) -> str | None:
    if crop == "lower-half":
        return "crop=iw*0.74:ih/2:iw*0.13:ih*0.47"
    if crop == "lower-third":
        return "crop=iw*0.74:ih/3:iw*0.13:ih*0.63"
    if crop == "full":
        return None
    raise ValueError(f"unsupported crop: {crop}")


def build_scale_filter(scale: float) -> str | None:
    if scale and scale != 1:
        return f"scale=trunc(iw*{scale}/2)*2:trunc(ih*{scale}/2)*2"
    return None


def frame_cache_params(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "schema": "gameplayVideoFrameCache.v1",
        "cropProfile": "raised-bottom-hud-strip-dark-near-full-v3",
        "frameStep": args.frame_step,
        "crop": args.crop,
        "scale": args.scale,
        "darkFullscreenOcr": not bool(args.disable_dark_fullscreen_ocr),
        "darkFrameThreshold": args.dark_frame_threshold,
        "darkPixelThreshold": args.dark_pixel_threshold,
        # Keep the historical cache signature for normal decoded frames. The
        # blackscreen ROI has its own cache subdirectory below.
        "darkCropHeight": 0.97,
        "jpegQuality": 4,
    }


def frame_cache_signature(args: argparse.Namespace) -> str:
    data = json.dumps(frame_cache_params(args), sort_keys=True, separators=(",", ":"))
    return hashlib.sha1(data.encode("utf-8")).hexdigest()[:12]


def frame_cache_dir_for_video(path: Path, args: argparse.Namespace) -> Path:
    return FRAME_CACHE_ROOT / f"{safe_report_stem(path)}_{frame_cache_signature(args)}"


def frame_cache_manifest_path(frame_dir: Path) -> Path:
    return frame_dir / "frame_cache.json"


def read_frame_cache_manifest(frame_dir: Path) -> dict[str, Any]:
    payload = read_json(frame_cache_manifest_path(frame_dir), {})
    return payload if isinstance(payload, dict) else {}


def write_frame_cache_manifest(
    frame_dir: Path,
    *,
    source: dict[str, Any],
    params: dict[str, Any],
    full_video_complete: bool,
    black_percent_by_sample: dict[int, int],
    cached_frames: int,
) -> None:
    payload = {
        "schema": "gameplayVideoFrameCache.v1",
        "updatedAt": utc_now(),
        "source": source,
        "parameters": params,
        "fullVideoComplete": full_video_complete,
        "cachedFrames": cached_frames,
        "blackPercentBySample": {str(key): value for key, value in sorted(black_percent_by_sample.items())},
    }
    write_report_json(frame_cache_manifest_path(frame_dir), payload)


def cached_frame_path(frame_dir: Path, sample_index: int) -> Path:
    return frame_dir / f"frame_{sample_index + 1:08d}.jpg"


def cached_dark_frame_path(frame_dir: Path, sample_index: int) -> Path:
    return frame_dir / DARK_SCREEN_CACHE_SUBDIR / f"frame_{sample_index + 1:08d}.jpg"


def archive_box_cache_suffix(scale: float) -> str:
    return f"s{max(1, int(round(scale * 100))):03d}"


def archive_box_full_dir(frame_dir: Path, scale: float) -> Path:
    return frame_dir / f"{ARCHIVE_BOX_CACHE_SUBDIR}_{archive_box_cache_suffix(scale)}"


def archive_box_panel_dir(frame_dir: Path, scale: float) -> Path:
    return frame_dir / f"{ARCHIVE_BOX_PANEL_CACHE_SUBDIR}_{archive_box_cache_suffix(scale)}"


def cached_archive_full_frame_path(frame_dir: Path, sample_index: int, scale: float) -> Path:
    return archive_box_full_dir(frame_dir, scale) / f"frame_{sample_index + 1:08d}.jpg"


def cached_archive_panel_frame_path(frame_dir: Path, sample_index: int, scale: float) -> Path:
    return archive_box_panel_dir(frame_dir, scale) / f"frame_{sample_index + 1:08d}.jpg"


def contiguous_cached_frame_count(frame_dir: Path, *, limit_frames: int | None = None) -> int:
    count = 0
    while True:
        if limit_frames is not None and count >= limit_frames:
            return count
        if not cached_frame_path(frame_dir, count).is_file():
            return count
        count += 1


def cached_frame_paths(frame_dir: Path, *, limit_frames: int | None = None) -> list[Path]:
    count = contiguous_cached_frame_count(frame_dir, limit_frames=limit_frames)
    return [cached_frame_path(frame_dir, sample_index) for sample_index in range(count)]


def cache_source_size_matches(manifest: dict[str, Any], source_fingerprint: dict[str, Any]) -> bool:
    source = manifest.get("source") if isinstance(manifest.get("source"), dict) else {}
    return source.get("path") == source_fingerprint.get("path") and source.get("size") == source_fingerprint.get("size")


def parse_manifest_black_percent(manifest: dict[str, Any]) -> dict[int, int]:
    values = manifest.get("blackPercentBySample")
    if not isinstance(values, dict):
        return {}
    out: dict[int, int] = {}
    for key, value in values.items():
        try:
            out[int(key)] = int(value)
        except (TypeError, ValueError):
            continue
    return out


def build_ffmpeg_filter(
    frame_step: int,
    crop: str,
    scale: float,
    *,
    limit_frames: int | None = None,
    start_sample_index: int = 0,
    black_pixel_threshold: int | None = None,
) -> str:
    filters = [build_sample_select(frame_step, limit_frames)]
    if start_sample_index > 0:
        filters.append(f"select='gte(n\\,{start_sample_index})'")
    if black_pixel_threshold is not None:
        filters.append(f"blackframe=amount=0:threshold={black_pixel_threshold}")
    crop_filter = build_crop_filter(crop)
    if crop_filter:
        filters.append(crop_filter)
    scale_filter = build_scale_filter(scale)
    if scale_filter:
        filters.append(scale_filter)
    filters.append("format=gray")
    return ",".join(filters)


def parse_blackframe_stderr(stderr: str) -> dict[int, int]:
    values: dict[int, int] = {}
    for match in BLACKFRAME_RE.finditer(stderr or ""):
        values[int(match.group("sample"))] = int(match.group("pblack"))
    return values


def extract_frames(
    video_path: Path,
    frame_dir: Path,
    *,
    ffmpeg: str,
    ffmpeg_hwaccel: str,
    source_fingerprint: dict[str, Any],
    cache_enabled: bool,
    cache_params: dict[str, Any],
    frame_step: int,
    crop: str,
    scale: float,
    limit_frames: int | None,
    detect_black: bool,
    dark_pixel_threshold: int,
) -> tuple[list[Path], dict[int, int], dict[str, Any]]:
    if not cache_enabled and frame_dir.exists():
        shutil.rmtree(frame_dir)
    frame_dir.mkdir(parents=True, exist_ok=True)
    manifest = read_frame_cache_manifest(frame_dir) if cache_enabled else {}
    black_percent_by_sample = parse_manifest_black_percent(manifest) if cache_enabled else {}
    cached_count = contiguous_cached_frame_count(frame_dir, limit_frames=limit_frames) if cache_enabled else 0
    cache_complete = False
    if cache_enabled and cached_count > 0:
        if limit_frames is not None:
            cache_complete = cached_count >= limit_frames
        else:
            cache_complete = bool(manifest.get("fullVideoComplete")) and cache_source_size_matches(
                manifest,
                source_fingerprint,
            )
    if cache_complete:
        frame_paths = cached_frame_paths(frame_dir, limit_frames=limit_frames)
        print(f"[{video_path.name}] frame cache hit: using {len(frame_paths)} decoded frame(s) from {rel_path(frame_dir)}")
        return frame_paths, black_percent_by_sample, {
            "enabled": True,
            "dir": rel_path(frame_dir),
            "cachedFrames": len(frame_paths),
            "decodedFrames": 0,
            "reusedFrames": len(frame_paths),
        }

    start_sample_index = cached_count if cache_enabled else 0
    decode_limit = None
    if limit_frames is not None:
        decode_limit = max(0, limit_frames - start_sample_index)
        if decode_limit == 0:
            frame_paths = cached_frame_paths(frame_dir, limit_frames=limit_frames)
            print(f"[{video_path.name}] frame cache hit: using {len(frame_paths)} decoded frame(s) from {rel_path(frame_dir)}")
            return frame_paths, black_percent_by_sample, {
                "enabled": cache_enabled,
                "dir": rel_path(frame_dir) if cache_enabled else "",
                "cachedFrames": len(frame_paths),
                "decodedFrames": 0,
                "reusedFrames": len(frame_paths),
            }
    if cache_enabled and start_sample_index > 0:
        print(
            f"[{video_path.name}] frame cache partial: {start_sample_index} decoded frame(s) "
            f"exist; decoding from sample {start_sample_index}..."
        )

    output_dir = frame_dir / f"_extract_{time.time_ns()}" if cache_enabled else frame_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "frame_%08d.jpg"

    def build_args(hwaccel: str) -> list[str]:
        built = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "info" if detect_black else "error",
            "-nostats",
            "-y",
            *ffmpeg_hwaccel_args(hwaccel),
            "-i",
            str(video_path),
            "-vf",
            build_ffmpeg_filter(
                frame_step,
                crop,
                scale,
                limit_frames=limit_frames,
                start_sample_index=start_sample_index,
                black_pixel_threshold=dark_pixel_threshold if detect_black else None,
            ),
            "-vsync",
            "0",
            "-q:v",
            "4",
        ]
        if decode_limit:
            built.extend(["-frames:v", str(decode_limit)])
        built.append(str(output_pattern))
        return built

    args = build_args(ffmpeg_hwaccel)
    fallback_args = build_args("none") if ffmpeg_hwaccel == "cuda" else None
    proc = run_ffmpeg_extract(args, fallback_args=fallback_args, label=f"[{video_path.name}]")
    decoded_paths = sorted(output_dir.glob("frame_*.jpg"))
    parsed_black = parse_blackframe_stderr(proc.stderr)
    if cache_enabled:
        for offset, decoded_path in enumerate(decoded_paths):
            sample_index = start_sample_index + offset
            destination = cached_frame_path(frame_dir, sample_index)
            if destination.exists():
                try:
                    decoded_path.unlink()
                except OSError:
                    pass
                continue
            shutil.move(str(decoded_path), str(destination))
        try:
            shutil.rmtree(output_dir)
        except OSError:
            pass
        black_percent_by_sample.update({
            start_sample_index + sample_index: value
            for sample_index, value in parsed_black.items()
        })
        frame_paths = cached_frame_paths(frame_dir, limit_frames=limit_frames)
        full_video_complete = limit_frames is None
        write_frame_cache_manifest(
            frame_dir,
            source=source_fingerprint,
            params=cache_params,
            full_video_complete=full_video_complete,
            black_percent_by_sample=black_percent_by_sample,
            cached_frames=len(frame_paths),
        )
        print(
            f"[{video_path.name}] frame cache updated: decoded {len(decoded_paths)} new frame(s), "
            f"cached total={len(frame_paths)} at {rel_path(frame_dir)}"
        )
        return frame_paths, black_percent_by_sample, {
            "enabled": True,
            "dir": rel_path(frame_dir),
            "cachedFrames": len(frame_paths),
            "decodedFrames": len(decoded_paths),
            "reusedFrames": start_sample_index,
        }
    return sorted(frame_dir.glob("frame_*.jpg")), parsed_black, {
        "enabled": False,
        "dir": "",
        "cachedFrames": 0,
        "decodedFrames": len(decoded_paths),
        "reusedFrames": 0,
    }


def build_dark_fullscreen_filter(
    frame_step: int,
    scale: float,
    *,
    limit_frames: int | None,
    dark_frame_threshold: float,
    dark_pixel_threshold: int,
) -> str:
    roi_height = DARK_SCREEN_ROI_BOTTOM - DARK_SCREEN_ROI_TOP
    filters = [
        build_sample_select(frame_step, limit_frames),
        f"blackframe=amount={dark_frame_threshold:g}:threshold={dark_pixel_threshold}",
        (
            "metadata=select:key=lavfi.blackframe.pblack:"
            f"value={dark_frame_threshold:g}:function=greater"
        ),
        f"crop=iw:ih*{roi_height:g}:0:ih*{DARK_SCREEN_ROI_TOP:g}",
    ]
    scale_filter = build_scale_filter(scale)
    if scale_filter:
        filters.append(scale_filter)
    filters.append("format=gray")
    return ",".join(filters)


def extract_dark_fullscreen_frames(
    video_path: Path,
    frame_dir: Path,
    *,
    ffmpeg: str,
    ffmpeg_hwaccel: str,
    frame_step: int,
    scale: float,
    limit_frames: int | None,
    dark_frame_threshold: float,
    dark_pixel_threshold: int,
    dark_sample_indices: list[int],
    cache_enabled: bool,
) -> list[Path]:
    dark_dir = frame_dir / DARK_SCREEN_CACHE_SUBDIR
    dark_dir.mkdir(parents=True, exist_ok=True)
    cached_paths = [cached_dark_frame_path(frame_dir, sample_index) for sample_index in dark_sample_indices]
    if cache_enabled and cached_paths and all(path.is_file() for path in cached_paths):
        print(
            f"[{video_path.name}] dark-frame cache hit: using {len(cached_paths)} near-full crop(s) "
            f"from {rel_path(dark_dir)}"
        )
        return cached_paths

    output_dir = dark_dir / f"_extract_{time.time_ns()}" if cache_enabled else dark_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "frame_%08d.jpg"

    def build_args(hwaccel: str) -> list[str]:
        built = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *ffmpeg_hwaccel_args(hwaccel),
            "-i",
            str(video_path),
            "-vf",
            build_dark_fullscreen_filter(
                frame_step,
                scale,
                limit_frames=limit_frames,
                dark_frame_threshold=dark_frame_threshold,
                dark_pixel_threshold=dark_pixel_threshold,
            ),
            "-vsync",
            "0",
            "-q:v",
            "4",
        ]
        if dark_sample_indices:
            built.extend(["-frames:v", str(len(dark_sample_indices))])
        built.append(str(output_pattern))
        return built

    args = build_args(ffmpeg_hwaccel)
    fallback_args = build_args("none") if ffmpeg_hwaccel == "cuda" else None
    run_ffmpeg_extract(args, fallback_args=fallback_args, label=f"[{video_path.name}]")
    decoded_paths = sorted(output_dir.glob("frame_*.jpg"))
    if cache_enabled:
        missing_count = 0
        for sample_index, decoded_path in zip(dark_sample_indices, decoded_paths):
            destination = cached_dark_frame_path(frame_dir, sample_index)
            if destination.exists():
                try:
                    decoded_path.unlink()
                except OSError:
                    pass
                continue
            shutil.move(str(decoded_path), str(destination))
            missing_count += 1
        try:
            shutil.rmtree(output_dir)
        except OSError:
            pass
        final_paths = [cached_dark_frame_path(frame_dir, sample_index) for sample_index in dark_sample_indices]
        print(
            f"[{video_path.name}] dark-frame cache updated: decoded {missing_count} new near-full crop(s), "
            f"cached total={sum(1 for path in final_paths if path.is_file())}"
        )
        return [path for path in final_paths if path.is_file()]
    return sorted(dark_dir.glob("frame_*.jpg"))


def build_exact_sample_filter(
    sample_indices: list[int],
    frame_step: int,
    scale: float,
) -> str:
    terms = [f"eq(n\\,{sample_index * frame_step})" for sample_index in sample_indices]
    filters = [f"select='{'+'.join(terms)}'"]
    scale_filter = build_scale_filter(scale)
    if scale_filter:
        filters.append(scale_filter)
    filters.append("format=gray")
    return ",".join(filters)


def extract_archive_fullscreen_frames(
    video_path: Path,
    frame_dir: Path,
    *,
    ffmpeg: str,
    ffmpeg_hwaccel: str,
    frame_step: int,
    scale: float,
    sample_indices: list[int],
    cache_enabled: bool,
) -> list[Path]:
    if not sample_indices:
        return []
    sample_indices = sorted(set(sample_indices))
    archive_dir = archive_box_full_dir(frame_dir, scale)
    archive_dir.mkdir(parents=True, exist_ok=True)
    cached_paths = [cached_archive_full_frame_path(frame_dir, sample_index, scale) for sample_index in sample_indices]
    if cache_enabled and cached_paths and all(path.is_file() for path in cached_paths):
        print(
            f"[{video_path.name}] archive-box cache hit: using {len(cached_paths)} full-frame crop(s) "
            f"from {rel_path(archive_dir)}"
        )
        return cached_paths

    output_dir = archive_dir / f"_extract_{time.time_ns()}" if cache_enabled else archive_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    output_pattern = output_dir / "frame_%08d.jpg"

    def build_args(hwaccel: str) -> list[str]:
        built = [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            *ffmpeg_hwaccel_args(hwaccel),
            "-i",
            str(video_path),
            "-vf",
            build_exact_sample_filter(sample_indices, frame_step, scale),
            "-vsync",
            "0",
            "-q:v",
            "4",
            "-frames:v",
            str(len(sample_indices)),
            str(output_pattern),
        ]
        return built

    args = build_args(ffmpeg_hwaccel)
    fallback_args = build_args("none") if ffmpeg_hwaccel == "cuda" else None
    run_ffmpeg_extract(args, fallback_args=fallback_args, label=f"[{video_path.name}]")
    decoded_paths = sorted(output_dir.glob("frame_*.jpg"))
    if cache_enabled:
        missing_count = 0
        for sample_index, decoded_path in zip(sample_indices, decoded_paths):
            destination = cached_archive_full_frame_path(frame_dir, sample_index, scale)
            if destination.exists():
                try:
                    decoded_path.unlink()
                except OSError:
                    pass
                continue
            shutil.move(str(decoded_path), str(destination))
            missing_count += 1
        try:
            shutil.rmtree(output_dir)
        except OSError:
            pass
        final_paths = [cached_archive_full_frame_path(frame_dir, sample_index, scale) for sample_index in sample_indices]
        print(
            f"[{video_path.name}] archive-box cache updated: decoded {missing_count} new full-frame crop(s), "
            f"cached total={sum(1 for path in final_paths if path.is_file())}"
        )
        return [path for path in final_paths if path.is_file()]
    return sorted(archive_dir.glob("frame_*.jpg"))


def archive_box_features(path: Path, args: argparse.Namespace) -> dict[str, Any]:
    from PIL import Image, ImageStat

    resampling = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        probe_width = 160
        probe_height = max(1, int(round(probe_width * height / max(1, width))))
        small = gray.resize((probe_width, probe_height), resampling)
        mask = small.point(lambda pixel: 255 if pixel >= args.archive_box_light_threshold else 0)
        mask_data = list(mask.getdata())
        row_min = max(1, int(round(probe_width * 0.05)))
        col_min = max(1, int(round(probe_height * 0.05)))
        rows = [
            y
            for y in range(probe_height)
            if sum(1 for x in range(probe_width) if mask_data[y * probe_width + x]) >= row_min
        ]
        cols = [
            x
            for x in range(probe_width)
            if sum(1 for y in range(probe_height) if mask_data[y * probe_width + x]) >= col_min
        ]
        bbox = (min(cols), min(rows), max(cols) + 1, max(rows) + 1) if rows and cols else mask.getbbox()
        mask_stat = ImageStat.Stat(mask)

    total = probe_width * probe_height
    bright_ratio = float((mask_stat.sum[0] if mask_stat.sum else 0) / (255 * total)) if total else 0.0
    if bbox is None:
        return {
            "detected": False,
            "brightRatio": round(bright_ratio, 4),
            "areaRatio": 0.0,
            "widthRatio": 0.0,
            "heightRatio": 0.0,
            "fillRatio": 0.0,
            "bbox": None,
        }
    x0, y0, x1, y1 = bbox
    bbox_width = max(0, x1 - x0)
    bbox_height = max(0, y1 - y0)
    area_ratio = (bbox_width * bbox_height) / total if total else 0.0
    width_ratio = bbox_width / probe_width if probe_width else 0.0
    height_ratio = bbox_height / probe_height if probe_height else 0.0
    fill_ratio = bright_ratio / area_ratio if area_ratio else 0.0
    detected = (
        bright_ratio >= args.archive_box_min_bright_ratio
        and area_ratio >= args.archive_box_min_area_ratio
        and width_ratio >= args.archive_box_min_width_ratio
        and height_ratio >= args.archive_box_min_height_ratio
        and fill_ratio >= args.archive_box_min_fill_ratio
    )
    return {
        "detected": bool(detected),
        "brightRatio": round(bright_ratio, 4),
        "areaRatio": round(area_ratio, 4),
        "widthRatio": round(width_ratio, 4),
        "heightRatio": round(height_ratio, 4),
        "fillRatio": round(fill_ratio, 4),
        "bbox": {
            "x0": round(x0 / probe_width, 4),
            "y0": round(y0 / probe_height, 4),
            "x1": round(x1 / probe_width, 4),
            "y1": round(y1 / probe_height, 4),
        },
    }


def detect_archive_box_samples(
    frame_paths: list[Path],
    args: argparse.Namespace,
    *,
    label: str,
) -> tuple[list[int], dict[int, dict[str, Any]], dict[str, int]]:
    stats = {
        "archiveBoxScannedFrames": 0,
        "archiveBoxDetectedFrames": 0,
        "archiveBoxDetectionErrors": 0,
    }
    if args.disable_archive_box_ocr:
        return [], {}, stats

    sample_indices: list[int] = []
    features_by_sample: dict[int, dict[str, Any]] = {}
    for sample_index, image_path in enumerate(frame_paths):
        stats["archiveBoxScannedFrames"] += 1
        try:
            features = archive_box_features(image_path, args)
        except Exception:
            stats["archiveBoxDetectionErrors"] += 1
            continue
        if not features.get("detected"):
            continue
        sample_indices.append(sample_index)
        features_by_sample[sample_index] = features
    stats["archiveBoxDetectedFrames"] = len(sample_indices)
    print(
        f"{label} archive-box detector: detected={stats['archiveBoxDetectedFrames']}/"
        f"{stats['archiveBoxScannedFrames']} errors={stats['archiveBoxDetectionErrors']}"
    )
    return sample_indices, features_by_sample, stats


def crop_archive_panel_frames(
    frame_dir: Path,
    full_frame_paths: list[Path],
    sample_indices: list[int],
    args: argparse.Namespace,
    *,
    cache_enabled: bool,
) -> tuple[list[tuple[int, Path, dict[str, Any]]], dict[str, int]]:
    from PIL import Image

    stats = {
        "archiveBoxPanelFrames": 0,
        "archiveBoxPanelCropFrames": 0,
        "archiveBoxPanelFallbackFrames": 0,
        "archiveBoxPanelCropErrors": 0,
    }
    panel_dir = archive_box_panel_dir(frame_dir, args.archive_box_scale)
    panel_dir.mkdir(parents=True, exist_ok=True)
    out: list[tuple[int, Path, dict[str, Any]]] = []
    for sample_index, full_path in zip(sample_indices, full_frame_paths):
        stats["archiveBoxPanelFrames"] += 1
        panel_path = cached_archive_panel_frame_path(frame_dir, sample_index, args.archive_box_scale)
        metadata: dict[str, Any] = {
            "sampleIndex": sample_index,
            "sourceImage": rel_path(full_path),
            "cropped": False,
        }
        if cache_enabled and panel_path.is_file():
            metadata["image"] = rel_path(panel_path)
            metadata["cached"] = True
            stats["archiveBoxPanelCropFrames"] += 1
            out.append((sample_index, panel_path, metadata))
            continue
        try:
            features = archive_box_features(full_path, args)
            metadata["features"] = features
            bbox = features.get("bbox") if isinstance(features.get("bbox"), dict) else None
            if bbox:
                with Image.open(full_path) as image:
                    gray = image.convert("L")
                    width, height = gray.size
                    pad_x = int(round(width * args.archive_box_crop_padding))
                    pad_y = int(round(height * args.archive_box_crop_padding))
                    x0 = max(0, int(math.floor(float(bbox.get("x0") or 0) * width)) - pad_x)
                    y0 = max(0, int(math.floor(float(bbox.get("y0") or 0) * height)) - pad_y)
                    x1 = min(width, int(math.ceil(float(bbox.get("x1") or 1) * width)) + pad_x)
                    y1 = min(height, int(math.ceil(float(bbox.get("y1") or 1) * height)) + pad_y)
                    if x1 - x0 >= 32 and y1 - y0 >= 32:
                        crop = gray.crop((x0, y0, x1, y1))
                        crop.save(panel_path, quality=4)
                        metadata.update({
                            "image": rel_path(panel_path),
                            "cropped": True,
                            "cropBox": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                        })
                        stats["archiveBoxPanelCropFrames"] += 1
                        out.append((sample_index, panel_path, metadata))
                        continue
            stats["archiveBoxPanelFallbackFrames"] += 1
            metadata["image"] = rel_path(full_path)
            out.append((sample_index, full_path, metadata))
        except Exception as exc:
            stats["archiveBoxPanelCropErrors"] += 1
            metadata["error"] = str(exc)
            metadata["image"] = rel_path(full_path)
            out.append((sample_index, full_path, metadata))
    return out, stats


def batched(values: list[Path], size: int) -> list[list[Path]]:
    size = max(1, int(size or 1))
    return [values[index : index + size] for index in range(0, len(values), size)]


def easyocr_languages(ocr_lang: str) -> list[str]:
    mapping = {
        "chi_sim": "ch_sim",
        "chs": "ch_sim",
        "zh_sim": "ch_sim",
        "ch_sim": "ch_sim",
        "eng": "en",
        "en": "en",
    }
    langs: list[str] = []
    for part in str(ocr_lang or "").split("+"):
        key = part.strip().lower()
        if not key:
            continue
        mapped = mapping.get(key, key)
        if mapped not in langs:
            langs.append(mapped)
    return langs or ["ch_sim", "en"]


def verify_easyocr_dependency(*, gpu: bool) -> tuple[bool, str]:
    try:
        import easyocr  # type: ignore[import-not-found]  # noqa: F401
    except ImportError:
        return False, "easyocr is not installed; install it with `python -m pip install easyocr`"
    if not gpu:
        return True, "easyocr installed; GPU disabled"
    try:
        import torch  # type: ignore[import-not-found]
    except ImportError:
        return False, "easyocr GPU backend needs torch, but torch is not installed"
    if not torch.cuda.is_available():
        return False, "torch is installed, but CUDA is not available"
    name = torch.cuda.get_device_name(0)
    version = getattr(torch.version, "cuda", None) or "unknown"
    return True, f"easyocr installed; torch CUDA {version}; GPU={name}"


def create_easyocr_reader(args: argparse.Namespace) -> Any:
    import easyocr  # type: ignore[import-not-found]

    model_dir = args.easyocr_model_dir
    if model_dir:
        model_dir.mkdir(parents=True, exist_ok=True)
        network_dir = model_dir / "user_network"
        network_dir.mkdir(parents=True, exist_ok=True)
        return easyocr.Reader(
            easyocr_languages(args.ocr_lang),
            gpu=not args.easyocr_cpu,
            model_storage_directory=str(model_dir),
            user_network_directory=str(network_dir),
            download_enabled=not args.easyocr_no_download,
            verbose=False,
        )
    return easyocr.Reader(
        easyocr_languages(args.ocr_lang),
        gpu=not args.easyocr_cpu,
        download_enabled=not args.easyocr_no_download,
        verbose=False,
    )


def easyocr_rows_to_text(rows: Any, min_confidence: float) -> str:
    texts: list[str] = []
    for row in rows or []:
        if isinstance(row, str):
            texts.append(row)
            continue
        if not isinstance(row, (list, tuple)) or len(row) < 2:
            continue
        text = str(row[1] or "")
        confidence = 1.0
        if len(row) >= 3:
            try:
                confidence = float(row[2])
            except (TypeError, ValueError):
                confidence = 1.0
        if text and confidence >= min_confidence:
            texts.append(text)
    return "\n".join(texts)


def image_size(path: Path) -> tuple[int, int]:
    from PIL import Image

    with Image.open(path) as image:
        return image.size


def frame_prefilter_features(
    path: Path,
    *,
    dark_frame: bool,
    args: argparse.Namespace,
) -> dict[str, Any]:
    from PIL import Image, ImageStat

    resampling = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
    with Image.open(path) as image:
        gray = image.convert("L")
        width, height = gray.size
        if not dark_frame and args.prefilter_focus_height < 1:
            top = max(0, min(height - 1, int(height * (1 - args.prefilter_focus_height))))
            gray = gray.crop((0, top, width, height))
        small = gray.resize((64, 16), resampling)
        stat = ImageStat.Stat(small)
        bright = small.point(lambda pixel: 255 if pixel >= args.prefilter_bright_threshold else 0)
        bright_stat = ImageStat.Stat(bright)
    return {
        "mask": bright,
        "stddev": float(stat.stddev[0] if stat.stddev else 0),
        "brightRatio": float((bright_stat.sum[0] if bright_stat.sum else 0) / (255 * 64 * 16)),
    }


def mask_diff_ratio(left: Any, right: Any) -> float:
    from PIL import ImageChops, ImageStat

    diff = ImageChops.difference(left, right)
    stat = ImageStat.Stat(diff)
    total = diff.size[0] * diff.size[1]
    return float((stat.sum[0] if stat.sum else 0) / (255 * total)) if total else 1.0


def select_ocr_indexed_pairs(
    indexed_paths: list[tuple[int, Path]],
    dark_sample_index_set: set[int],
    args: argparse.Namespace,
    *,
    label: str,
) -> tuple[list[tuple[int, Path]], dict[str, int]]:
    stats = {
        "ocrCandidateFrames": len(indexed_paths),
        "prefilterSkippedBlankFrames": 0,
        "prefilterSkippedDuplicateFrames": 0,
        "prefilterForcedDuplicateFrames": 0,
        "prefilterErrors": 0,
    }
    if args.disable_frame_prefilter or args.include_empty:
        return list(indexed_paths), stats

    selected: list[tuple[int, Path]] = []
    previous_mask: Any | None = None
    duplicate_skip_run = 0
    for sample_index, image_path in indexed_paths:
        try:
            features = frame_prefilter_features(
                image_path,
                dark_frame=sample_index in dark_sample_index_set,
                args=args,
            )
        except Exception:
            stats["prefilterErrors"] += 1
            selected.append((sample_index, image_path))
            previous_mask = None
            duplicate_skip_run = 0
            continue

        is_blank = (
            features["stddev"] <= args.prefilter_blank_stddev
            and features["brightRatio"] <= args.prefilter_blank_bright_ratio
        )
        if is_blank:
            stats["prefilterSkippedBlankFrames"] += 1
            previous_mask = None
            duplicate_skip_run = 0
            continue

        if previous_mask is not None:
            diff_ratio = mask_diff_ratio(previous_mask, features["mask"])
            if diff_ratio <= args.prefilter_duplicate_threshold:
                if duplicate_skip_run < args.prefilter_max_duplicate_skip:
                    stats["prefilterSkippedDuplicateFrames"] += 1
                    duplicate_skip_run += 1
                    continue
                stats["prefilterForcedDuplicateFrames"] += 1

        selected.append((sample_index, image_path))
        previous_mask = features["mask"]
        duplicate_skip_run = 0

    stats["ocrCandidateFrames"] = len(selected)
    print(
        f"{label} prefilter: OCR candidates={stats['ocrCandidateFrames']}/{len(indexed_paths)} "
        f"blank_skip={stats['prefilterSkippedBlankFrames']} "
        f"duplicate_skip={stats['prefilterSkippedDuplicateFrames']} "
        f"forced_duplicate={stats['prefilterForcedDuplicateFrames']} "
        f"errors={stats['prefilterErrors']}"
    )
    return selected, stats


def select_ocr_frame_pairs(
    frame_paths: list[Path],
    dark_sample_index_set: set[int],
    args: argparse.Namespace,
    *,
    label: str,
) -> tuple[list[tuple[int, Path]], dict[str, int]]:
    return select_ocr_indexed_pairs(
        list(enumerate(frame_paths)),
        dark_sample_index_set,
        args,
        label=label,
    )


def run_easyocr_batch(
    reader: Any,
    image_paths: list[Path],
    args: argparse.Namespace,
    *,
    label: str,
    started: float,
) -> list[str]:
    if not image_paths:
        return []
    grouped: dict[tuple[int, int], list[tuple[int, Path]]] = {}
    for index, image_path in enumerate(image_paths):
        grouped.setdefault(image_size(image_path), []).append((index, image_path))

    out = [""] * len(image_paths)
    total_chunks = sum(
        int(math.ceil(len(indexed_paths) / args.easyocr_frame_batch_size))
        for indexed_paths in grouped.values()
    )
    completed_images = 0
    completed_chunks = 0
    group_text = ", ".join(
        f"{width}x{height}:{len(indexed_paths)}"
        for (width, height), indexed_paths in sorted(grouped.items())
    )
    print(f"{label} EasyOCR image groups: {group_text or 'none'}")
    for size, indexed_paths in sorted(grouped.items()):
        width, height = size
        chunk_count = int(math.ceil(len(indexed_paths) / args.easyocr_frame_batch_size))
        print(
            f"{label} OCR group {width}x{height}: {len(indexed_paths)} frame(s), "
            f"{chunk_count} batch(es)"
        )
        for pair_chunk in [
            indexed_paths[index : index + args.easyocr_frame_batch_size]
            for index in range(0, len(indexed_paths), args.easyocr_frame_batch_size)
        ]:
            completed_chunks += 1
            chunk_started = time.monotonic()
            chunk_indices = [index for index, _path in pair_chunk]
            chunk_paths = [path for _index, path in pair_chunk]
            rows_by_image = reader.readtext_batched(
                [str(path) for path in chunk_paths],
                detail=1,
                paragraph=False,
                batch_size=args.easyocr_batch_size,
                workers=0,
            )
            for output_index, rows in zip(chunk_indices, rows_by_image or []):
                out[output_index] = easyocr_rows_to_text(rows, args.easyocr_min_confidence)
            completed_images += len(pair_chunk)
            del rows_by_image
            print(
                f"{label} OCR batch {completed_chunks}/{total_chunks}: "
                f"{len(pair_chunk)} frame(s) in {short_duration(time.monotonic() - chunk_started)}"
            )
            if not args.no_progress:
                progress_bar(
                    f"{label} OCR",
                    completed_images,
                    len(image_paths),
                    started=started,
                    force=(completed_images == len(image_paths)),
                )
            if args.easyocr_cleanup_interval and completed_chunks % args.easyocr_cleanup_interval == 0:
                release_ocr_memory(cuda=not args.easyocr_cpu)
    return out


def observation_time(frame_index: int, fps: float | None) -> float | None:
    if not fps:
        return None
    return frame_index / fps


def collapse_segments(observations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    raw_counter: Counter[str] = Counter()
    crop_counter: Counter[str] = Counter()
    pass_counter: Counter[str] = Counter()

    def finish_current() -> None:
        nonlocal current, raw_counter, crop_counter, pass_counter
        if current is None:
            return
        current["rawTextVariants"] = [
            {"text": text, "count": count}
            for text, count in raw_counter.most_common(5)
        ]
        if crop_counter:
            current["ocrCrops"] = [
                {"crop": crop, "count": count}
                for crop, count in crop_counter.most_common()
            ]
        if pass_counter:
            current["ocrPasses"] = [
                {"pass": pass_name, "count": count}
                for pass_name, count in pass_counter.most_common()
            ]
        segments.append(current)
        current = None
        raw_counter = Counter()
        crop_counter = Counter()
        pass_counter = Counter()

    for obs in observations:
        normalized = safe_key(obs.get("text"))
        if current is None or current.get("text") != normalized:
            finish_current()
            current = {
                "text": normalized,
                "startFrame": obs.get("frame"),
                "endFrame": obs.get("frame"),
                "startSample": obs.get("sampleIndex"),
                "endSample": obs.get("sampleIndex"),
                "startTimeSeconds": obs.get("timeSeconds"),
                "endTimeSeconds": obs.get("timeSeconds"),
                "startTime": obs.get("time"),
                "endTime": obs.get("time"),
                "sampleCount": 0,
            }
        current["endFrame"] = obs.get("frame")
        current["endSample"] = obs.get("sampleIndex")
        current["endTimeSeconds"] = obs.get("timeSeconds")
        current["endTime"] = obs.get("time")
        current["sampleCount"] += 1
        raw_counter[safe_key(obs.get("rawText")) or normalized] += 1
        crop_counter[safe_key(obs.get("ocrCrop")) or "unknown"] += 1
        pass_counter[safe_key(obs.get("ocrPass")) or safe_key(obs.get("ocrCrop")) or "primary"] += 1
    finish_current()
    return segments


def md_multiline_cell(value: Any) -> str:
    text = safe_key(value)
    text = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("|", "\\|")
    )
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def write_video_markdown(report_path: Path, payload: dict[str, Any]) -> None:
    md_path = report_path.with_suffix(".md")
    lines = [
        f"# Gameplay Video OCR: `{md_escape(payload.get('source', {}).get('name'))}`",
        "",
        f"- Status: `{md_escape(payload.get('status'))}`",
        f"- Source: `{md_escape(payload.get('source', {}).get('path'))}`",
        f"- Missions from filename: `{md_escape(', '.join(payload.get('missions') or []) or 'none')}`",
        f"- Part from filename: `{md_escape(payload.get('part') if payload.get('part') is not None else 'none')}`",
    ]
    meta = payload.get("video") if isinstance(payload.get("video"), dict) else {}
    if meta:
        lines.extend([
            f"- Duration: `{md_escape(meta.get('duration') or '')}`",
            f"- Resolution: `{meta.get('width') or 0}x{meta.get('height') or 0}`",
            f"- FPS: `{meta.get('fps') or ''}`",
        ])
    params = payload.get("parameters") if isinstance(payload.get("parameters"), dict) else {}
    if params:
        dark_roi = ""
        if params.get("darkRoiTop") is not None and params.get("darkRoiBottom") is not None:
            dark_roi = f"{float(params.get('darkRoiTop')) * 100:g}%-{float(params.get('darkRoiBottom')) * 100:g}%"
        lines.extend([
            f"- Frame step: `{params.get('frameStep')}`",
            f"- Crop: `{md_escape(params.get('crop'))}`",
            f"- Dark-frame near-full OCR: `{str(params.get('darkFullscreenOcr', False)).lower()}`",
            f"- Dark-frame ROI: `{dark_roi or params.get('darkCropHeight')}`",
            f"- Archive-box OCR: `{str(params.get('archiveBoxOcr', False)).lower()}`",
            f"- Archive-box re-extract scale: `{params.get('archiveBoxScale', '')}`",
            f"- OCR language: `{md_escape(params.get('ocrLang'))}`",
        ])
    stats = payload.get("stats") if isinstance(payload.get("stats"), dict) else {}
    if stats:
        lines.extend([
            f"- Sampled frames: `{stats.get('sampledFrames', 0)}`",
            f"- Dark near-full OCR frames: `{stats.get('darkFullscreenFrames', 0)}`",
            f"- Archive-box detected frames: `{stats.get('archiveBoxDetectedFrames', 0)}`",
            f"- Archive-box OCR candidate frames: `{stats.get('archiveBoxOcrCandidateFrames', 0)}`",
            f"- Archive-box kept text frames: `{stats.get('archiveBoxNonEmptyFrames', 0)}`",
            f"- OCR candidate frames: `{stats.get('ocrCandidateFrames', stats.get('sampledFrames', 0))}`",
            f"- Prefilter skipped blank frames: `{stats.get('prefilterSkippedBlankFrames', 0)}`",
            f"- Prefilter skipped duplicate frames: `{stats.get('prefilterSkippedDuplicateFrames', 0)}`",
            f"- Prefilter forced duplicate-looking frames: `{stats.get('prefilterForcedDuplicateFrames', 0)}`",
            f"- Raw OCR frames with text: `{stats.get('rawTextFrames', stats.get('nonEmptyFrames', 0))}`",
            f"- Kept OCR frames with text: `{stats.get('nonEmptyFrames', 0)}`",
            f"- Filtered OCR frames: `{stats.get('filteredFrames', 0)}`",
            f"- Collapsed segments: `{stats.get('segments', 0)}`",
        ])
    frame_cache = payload.get("frameCache") if isinstance(payload.get("frameCache"), dict) else {}
    if frame_cache and frame_cache.get("enabled"):
        lines.extend([
            f"- Frame cache: `{md_escape(frame_cache.get('dir') or '')}`",
            f"- Frame cache reused files: `{frame_cache.get('reusedFrames', 0)}`",
            f"- Frame cache decoded files: `{frame_cache.get('decodedFrames', 0)}`",
        ])
    if payload.get("error"):
        lines.extend(["", "## Error", "", f"```text\n{payload.get('error')}\n```"])
    observations = payload.get("observations") if isinstance(payload.get("observations"), list) else []
    timeline = [
        obs
        for obs in observations
        if isinstance(obs, dict) and safe_key(obs.get("text"))
    ]
    if timeline:
        lines.extend([
            "",
            "## Filtered Timeline",
            "",
            "| sample | frame | time | crop | black | text | raw text | image |",
            "|---:|---:|---|---|---:|---|---|---|",
        ])
        for obs in timeline:
            text = md_multiline_cell(obs.get("text"))
            raw_text = md_multiline_cell(obs.get("rawText")) if safe_key(obs.get("rawText")) != safe_key(obs.get("text")) else ""
            image = md_escape(obs.get("image") or "")
            lines.append(
                f"| {obs.get('sampleIndex', '')} "
                f"| {obs.get('frame', '')} "
                f"| `{md_escape(obs.get('time') or '')}` "
                f"| `{md_escape(obs.get('ocrCrop') or '')}` "
                f"| {obs.get('blackPercent') if obs.get('blackPercent') is not None else ''} "
                f"| {text} "
                f"| {raw_text} "
                f"| `{image}` |"
            )
    segments = payload.get("segments") or []
    if segments:
        lines.extend(["", "## Collapsed Segments", "", "| start | end | samples | text |", "|---|---:|---:|---|"])
        for segment in segments:
            text = md_multiline_cell(segment.get("text") or "")
            lines.append(
                f"| `{md_escape(segment.get('startTime') or '')}` "
                f"| `{md_escape(segment.get('endTime') or '')}` "
                f"| {segment.get('sampleCount', 0)} "
                f"| {text} |"
            )
    write_text_if_changed(md_path, "\n".join(lines) + "\n")


def refresh_existing_video_markdown_reports() -> int:
    refreshed = 0
    for report_path in sorted(REPORT_DIR.glob("*_ocr.json")):
        if report_path.name == INDEX_PATH.name:
            continue
        payload = read_json(report_path, {})
        if not isinstance(payload, dict) or not isinstance(payload.get("source"), dict):
            continue
        write_video_markdown(report_path, payload)
        refreshed += 1
    return refreshed


def process_video(
    path: Path,
    *,
    args: argparse.Namespace,
    ffmpeg: str,
    ffprobe: str,
    easyocr_reader: Any | None,
    params: dict[str, Any],
) -> dict[str, Any]:
    fingerprint = video_fingerprint(path)
    report_path = REPORT_DIR / f"{safe_report_stem(path)}_ocr.json"
    started = utc_now()
    payload: dict[str, Any] = {
        "schema": "gameplayVideoOcrReport.v1",
        "status": "running",
        "generatedAt": started,
        "source": fingerprint,
        "missions": infer_missions(path),
        "part": infer_part(path),
        "parameters": params,
    }
    write_report_json(report_path, payload)

    cache_enabled = bool(args.keep_frames)
    cache_params = frame_cache_params(args)
    frame_dir = frame_cache_dir_for_video(path, args) if cache_enabled else TMP_ROOT / f"{safe_report_stem(path)}_{time.time_ns()}"
    observations: list[dict[str, Any]] = []
    raw_nonempty_frames = 0
    try:
        print(f"[{path.name}] probing video...")
        meta = ffprobe_video(path, ffprobe)
        estimated = meta.get("frameCountEstimate")
        estimated_samples = (
            int(math.ceil(float(estimated) / args.frame_step))
            if isinstance(estimated, int) and estimated > 0
            else None
        )
        print(
            f"[{path.name}] duration={meta.get('duration') or '?'} "
            f"size={meta.get('width')}x{meta.get('height')} "
            f"fps={float(meta.get('fps') or 0):.3f} "
            f"estimated_samples={estimated_samples or '?'}"
        )
        if cache_enabled:
            print(f"[{path.name}] frame cache: {rel_path(frame_dir)}")
        print(f"[{path.name}] preparing sampled {args.crop} frames with ffmpeg/cache...")
        extract_started = time.monotonic()
        detect_black = not args.disable_dark_fullscreen_ocr
        frame_paths, black_percent_by_sample, frame_cache_stats = extract_frames(
            path,
            frame_dir,
            ffmpeg=ffmpeg,
            ffmpeg_hwaccel=args.ffmpeg_hwaccel,
            source_fingerprint=fingerprint,
            cache_enabled=cache_enabled,
            cache_params=cache_params,
            frame_step=args.frame_step,
            crop=args.crop,
            scale=args.scale,
            limit_frames=args.limit_frames,
            detect_black=detect_black,
            dark_pixel_threshold=args.dark_pixel_threshold,
        )
        dark_sample_indices = [
            sample_index
            for sample_index, pblack in sorted(black_percent_by_sample.items())
            if pblack > args.dark_frame_threshold and sample_index < len(frame_paths)
        ]
        if black_percent_by_sample:
            max_black = max(black_percent_by_sample.values())
            print(
                f"[{path.name}] black-frame scan: {len(black_percent_by_sample)} sampled frame(s), "
                f"max_black={max_black}% threshold={args.dark_frame_threshold:g}%"
        )
        dark_sample_index_set = set(dark_sample_indices)
        dark_replacement_count = 0
        if dark_sample_indices:
            print(
                f"[{path.name}] {len(dark_sample_indices)} mostly-black sampled frame(s) "
                f"detected; bypassing {args.crop} crop and extracting blackscreen ROI "
                f"{DARK_SCREEN_ROI_TOP * 100:.0f}%-{DARK_SCREEN_ROI_BOTTOM * 100:.0f}%..."
            )
            dark_frame_paths = extract_dark_fullscreen_frames(
                path,
                frame_dir,
                ffmpeg=ffmpeg,
                ffmpeg_hwaccel=args.ffmpeg_hwaccel,
                frame_step=args.frame_step,
                scale=args.scale,
                limit_frames=args.limit_frames,
                dark_frame_threshold=args.dark_frame_threshold,
                dark_pixel_threshold=args.dark_pixel_threshold,
                dark_sample_indices=dark_sample_indices,
                cache_enabled=cache_enabled,
            )
            if len(dark_frame_paths) != len(dark_sample_indices):
                print(
                    f"[{path.name}] warning: expected {len(dark_sample_indices)} dark crop(s), "
                    f"got {len(dark_frame_paths)}",
                    file=sys.stderr,
                )
            for sample_index, dark_path in zip(dark_sample_indices, dark_frame_paths):
                if not args.keep_frames:
                    try:
                        frame_paths[sample_index].unlink()
                    except OSError:
                        pass
                elif cache_enabled:
                    # Keep the primary decoded frame as the actual OCR input:
                    # blackscreen samples bypass the normal subtitle crop.
                    try:
                        shutil.copy2(dark_path, frame_paths[sample_index])
                    except OSError:
                        pass
                    else:
                        dark_path = frame_paths[sample_index]
                frame_paths[sample_index] = dark_path
                dark_replacement_count += 1
        print(
            f"[{path.name}] extracted {len(frame_paths)} frame(s) "
            f"({dark_replacement_count} dark-frame near-full crop(s)) "
            f"in {short_duration(time.monotonic() - extract_started)}"
        )
        fps = meta.get("fps") if isinstance(meta.get("fps"), (int, float)) else None
        ocr_started = time.monotonic()
        if easyocr_reader is None:
            raise RuntimeError("EasyOCR reader was not initialized")
        ocr_frame_pairs, prefilter_stats = select_ocr_frame_pairs(
            frame_paths,
            dark_sample_index_set,
            args,
            label=f"[{path.name}]",
        )
        ocr_frame_paths = [image_path for _sample_index, image_path in ocr_frame_pairs]
        if frame_paths:
            print(
                f"[{path.name}] running EasyOCR "
                f"({'GPU' if not args.easyocr_cpu else 'CPU'}) on {len(ocr_frame_paths)}/{len(frame_paths)} frame(s) "
                f"(frame_batch={args.easyocr_frame_batch_size}, recognizer_batch={args.easyocr_batch_size})..."
            )
        frame_texts = run_easyocr_batch(
            easyocr_reader,
            ocr_frame_paths,
            args,
            label=f"[{path.name}]",
            started=ocr_started,
        )

        archive_stats = {
            "archiveBoxScannedFrames": 0,
            "archiveBoxDetectedFrames": 0,
            "archiveBoxDetectionErrors": 0,
            "archiveBoxFullFrames": 0,
            "archiveBoxPanelFrames": 0,
            "archiveBoxPanelCropFrames": 0,
            "archiveBoxPanelFallbackFrames": 0,
            "archiveBoxPanelCropErrors": 0,
            "archiveBoxOcrCandidateFrames": 0,
            "archiveBoxPrefilterSkippedBlankFrames": 0,
            "archiveBoxPrefilterSkippedDuplicateFrames": 0,
            "archiveBoxPrefilterForcedDuplicateFrames": 0,
            "archiveBoxPrefilterErrors": 0,
            "archiveBoxRawTextFrames": 0,
            "archiveBoxNonEmptyFrames": 0,
            "archiveBoxFilteredFrames": 0,
        }
        if not args.disable_archive_box_ocr:
            archive_sample_indices, first_pass_box_features, archive_detect_stats = detect_archive_box_samples(
                frame_paths,
                args,
                label=f"[{path.name}]",
            )
            archive_stats.update(archive_detect_stats)
            if archive_sample_indices:
                archive_full_paths = extract_archive_fullscreen_frames(
                    path,
                    frame_dir,
                    ffmpeg=ffmpeg,
                    ffmpeg_hwaccel=args.ffmpeg_hwaccel,
                    frame_step=args.frame_step,
                    scale=args.archive_box_scale,
                    sample_indices=archive_sample_indices,
                    cache_enabled=cache_enabled,
                )
                archive_stats["archiveBoxFullFrames"] = len(archive_full_paths)
                if len(archive_full_paths) != len(archive_sample_indices):
                    print(
                        f"[{path.name}] warning: expected {len(archive_sample_indices)} archive full-frame crop(s), "
                        f"got {len(archive_full_paths)}",
                        file=sys.stderr,
                    )
                archive_panel_rows, archive_panel_stats = crop_archive_panel_frames(
                    frame_dir,
                    archive_full_paths,
                    archive_sample_indices,
                    args,
                    cache_enabled=cache_enabled,
                )
                archive_stats.update(archive_panel_stats)
                archive_panel_meta_by_sample = {
                    sample_index: metadata
                    for sample_index, _panel_path, metadata in archive_panel_rows
                }
                archive_pairs, archive_prefilter_stats = select_ocr_indexed_pairs(
                    [(sample_index, panel_path) for sample_index, panel_path, _metadata in archive_panel_rows],
                    set(),
                    args,
                    label=f"[{path.name}] archive-box",
                )
                archive_stats.update({
                    "archiveBoxOcrCandidateFrames": archive_prefilter_stats.get("ocrCandidateFrames", 0),
                    "archiveBoxPrefilterSkippedBlankFrames": archive_prefilter_stats.get("prefilterSkippedBlankFrames", 0),
                    "archiveBoxPrefilterSkippedDuplicateFrames": archive_prefilter_stats.get("prefilterSkippedDuplicateFrames", 0),
                    "archiveBoxPrefilterForcedDuplicateFrames": archive_prefilter_stats.get("prefilterForcedDuplicateFrames", 0),
                    "archiveBoxPrefilterErrors": archive_prefilter_stats.get("prefilterErrors", 0),
                })
                archive_frame_texts = run_easyocr_batch(
                    easyocr_reader,
                    [image_path for _sample_index, image_path in archive_pairs],
                    args,
                    label=f"[{path.name}] archive-box",
                    started=ocr_started,
                )
                for (sample_index, image_path), raw_text in zip(archive_pairs, archive_frame_texts):
                    original_frame = sample_index * args.frame_step
                    seconds = observation_time(original_frame, fps)
                    raw_normalized = normalize_ocr_text(raw_text)
                    if raw_normalized:
                        archive_stats["archiveBoxRawTextFrames"] += 1
                    text = normalize_ocr_text(raw_text, args)
                    if text or args.include_empty:
                        archive_stats["archiveBoxNonEmptyFrames"] += 1
                        archive_box = {
                            "detector": first_pass_box_features.get(sample_index),
                            "fullFrame": archive_panel_meta_by_sample.get(sample_index) or {},
                        }
                        observations.append({
                            "sampleIndex": sample_index,
                            "frame": original_frame,
                            "timeSeconds": round(seconds, 3) if seconds is not None else None,
                            "time": seconds_to_clock(seconds),
                            "text": text,
                            "rawText": raw_normalized,
                            "ocrCrop": "archive-box",
                            "ocrPass": "archive-box",
                            "blackPercent": black_percent_by_sample.get(sample_index),
                            "image": rel_path(image_path) if args.keep_frames else None,
                            "archiveBox": archive_box,
                        })
                archive_stats["archiveBoxFilteredFrames"] = max(
                    0,
                    archive_stats["archiveBoxRawTextFrames"] - archive_stats["archiveBoxNonEmptyFrames"],
                )

        for (sample_index, image_path), raw_text in zip(ocr_frame_pairs, frame_texts):
            original_frame = sample_index * args.frame_step
            seconds = observation_time(original_frame, fps)
            raw_normalized = normalize_ocr_text(raw_text)
            if raw_normalized:
                raw_nonempty_frames += 1
            text = normalize_ocr_text(raw_text, args)
            if text or args.include_empty:
                observations.append({
                    "sampleIndex": sample_index,
                    "frame": original_frame,
                    "timeSeconds": round(seconds, 3) if seconds is not None else None,
                    "time": seconds_to_clock(seconds),
                    "text": text,
                    "rawText": raw_normalized,
                    "ocrCrop": "dark-fullscreen" if sample_index in dark_sample_index_set else args.crop,
                    "ocrPass": "primary",
                    "blackPercent": black_percent_by_sample.get(sample_index),
                    "image": rel_path(image_path) if args.keep_frames else None,
                })
            if not args.keep_frames:
                try:
                    image_path.unlink()
                except OSError:
                    pass
        observations.sort(key=lambda obs: (
            int(obs.get("sampleIndex") if obs.get("sampleIndex") is not None else -1),
            1 if safe_key(obs.get("ocrPass")) == "archive-box" else 0,
            safe_key(obs.get("text")),
        ))
        segments = collapse_segments([obs for obs in observations if safe_key(obs.get("text"))])
        primary_kept_frames = sum(
            1
            for obs in observations
            if safe_key(obs.get("text")) and safe_key(obs.get("ocrPass")) != "archive-box"
        )
        kept_frames = sum(1 for obs in observations if safe_key(obs.get("text")))
        raw_text_frames_total = raw_nonempty_frames + archive_stats["archiveBoxRawTextFrames"]
        filtered_frames = max(0, raw_text_frames_total - kept_frames)
        print(
            f"[{path.name}] OCR filter: primary_raw_text={raw_nonempty_frames}, "
            f"primary_kept={primary_kept_frames}, archive_kept={archive_stats['archiveBoxNonEmptyFrames']}, "
            f"kept={kept_frames}, filtered={filtered_frames}, "
            f"observations={len(observations)}, segments={len(segments)}"
        )
        payload.update({
            "status": "complete",
            "completedAt": utc_now(),
            "video": meta,
            "frameCache": frame_cache_stats,
            "stats": {
                "sampledFrames": len(frame_paths),
                "darkFullscreenFrames": dark_replacement_count,
                **prefilter_stats,
                **archive_stats,
                "primaryRawTextFrames": raw_nonempty_frames,
                "primaryNonEmptyFrames": primary_kept_frames,
                "rawTextFrames": raw_text_frames_total,
                "nonEmptyFrames": kept_frames,
                "filteredFrames": filtered_frames,
                "observations": len(observations),
                "segments": len(segments),
            },
            "observations": observations,
            "segments": segments,
        })
        print(
            f"[{path.name}] complete: sampled={len(frame_paths)} "
            f"ocr_candidates={prefilter_stats.get('ocrCandidateFrames', len(frame_paths))} "
            f"raw_text_frames={payload['stats']['rawTextFrames']} "
            f"kept_text_frames={payload['stats']['nonEmptyFrames']} "
            f"filtered={payload['stats']['filteredFrames']} "
            f"segments={len(segments)} report={rel_path(report_path)}"
        )
    except Exception as exc:  # noqa: BLE001 - report diagnostics for long batch runs.
        payload.update({
            "status": "error",
            "completedAt": utc_now(),
            "error": str(exc),
        })
        print(f"[{path.name}] error: {exc}", file=sys.stderr)
    finally:
        if not args.keep_frames:
            try:
                shutil.rmtree(frame_dir)
            except OSError:
                pass
        release_ocr_memory(cuda=not args.easyocr_cpu)
    write_report_json(report_path, payload)
    write_video_markdown(report_path, payload)
    return {
        "path": fingerprint["path"],
        "name": fingerprint["name"],
        "report": rel_path(report_path),
        "status": payload.get("status"),
        "missions": payload.get("missions") or [],
        "part": payload.get("part"),
        "stats": payload.get("stats") or {},
        "error": payload.get("error"),
    }


def write_blocked_video_report(
    path: Path,
    *,
    params: dict[str, Any],
    error: str,
) -> dict[str, Any]:
    fingerprint = video_fingerprint(path)
    report_path = REPORT_DIR / f"{safe_report_stem(path)}_ocr.json"
    payload = {
        "schema": "gameplayVideoOcrReport.v1",
        "status": "blocked",
        "generatedAt": utc_now(),
        "source": fingerprint,
        "missions": infer_missions(path),
        "part": infer_part(path),
        "parameters": params,
        "stats": {
            "sampledFrames": 0,
            "darkFullscreenFrames": 0,
            "rawTextFrames": 0,
            "nonEmptyFrames": 0,
            "filteredFrames": 0,
            "observations": 0,
            "segments": 0,
        },
        "observations": [],
        "segments": [],
        "error": error,
    }
    write_report_json(report_path, payload)
    write_video_markdown(report_path, payload)
    return {
        "path": fingerprint["path"],
        "name": fingerprint["name"],
        "report": rel_path(report_path),
        "status": "blocked",
        "missions": payload["missions"],
        "part": payload["part"],
        "stats": payload["stats"],
        "error": error,
    }


def write_index(entries: list[dict[str, Any]], params: dict[str, Any], *, dry_run: bool) -> None:
    payload = {
        "schema": "gameplayVideoOcrIndex.v1",
        "generatedAt": utc_now(),
        "dryRun": dry_run,
        "videoRoot": rel_path(VIDEO_ROOT),
        "reportDir": rel_path(REPORT_DIR),
        "parameters": params,
        "videos": entries,
    }
    write_report_json(INDEX_PATH, payload)

    lines = [
        "# Gameplay Video OCR Index",
        "",
        f"- Generated: `{payload['generatedAt']}`",
        f"- Video root: `{payload['videoRoot']}`",
        f"- Dry run: `{str(dry_run).lower()}`",
        "",
        "| status | part | missions | video | sampled | ocr | blank skip | duplicate skip | dark full | raw text | kept text | filtered | segments | report |",
        "|---|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for entry in entries:
        stats = entry.get("stats") if isinstance(entry.get("stats"), dict) else {}
        report = safe_key(entry.get("report"))
        report_link = f"[json]({Path(report).name})" if report else ""
        lines.append(
            f"| `{md_escape(entry.get('status'))}` "
            f"| {entry.get('part') if entry.get('part') is not None else ''} "
            f"| `{md_escape(', '.join(entry.get('missions') or []))}` "
            f"| `{md_escape(entry.get('name'))}` "
            f"| {stats.get('sampledFrames', 0)} "
            f"| {stats.get('ocrCandidateFrames', stats.get('sampledFrames', 0))} "
            f"| {stats.get('prefilterSkippedBlankFrames', 0)} "
            f"| {stats.get('prefilterSkippedDuplicateFrames', 0)} "
            f"| {stats.get('darkFullscreenFrames', 0)} "
            f"| {stats.get('rawTextFrames', stats.get('nonEmptyFrames', 0))} "
            f"| {stats.get('nonEmptyFrames', 0)} "
            f"| {stats.get('filteredFrames', 0)} "
            f"| {stats.get('segments', 0)} "
            f"| {report_link} |"
        )
    write_text_if_changed(INDEX_MD_PATH, "\n".join(lines) + "\n")


def pending_index_entry(
    path: Path,
    fingerprint: dict[str, Any],
    report_path: Path,
    *,
    status: str,
) -> dict[str, Any]:
    return {
        "path": fingerprint["path"],
        "name": fingerprint["name"],
        "report": rel_path(report_path),
        "status": status,
        "missions": infer_missions(path),
        "part": infer_part(path),
        "stats": {},
    }


def write_live_index(
    entries: list[dict[str, Any]],
    pending: list[tuple[Path, dict[str, Any], Path]],
    params: dict[str, Any],
    *,
    current_position: int | None,
) -> None:
    live_entries = list(entries)
    for index, (path, fingerprint, report_path) in enumerate(pending):
        if current_position is not None and index < current_position:
            continue
        status = "running" if current_position is not None and index == current_position else "pending"
        live_entries.append(pending_index_entry(path, fingerprint, report_path, status=status))
    write_index(live_entries, params, dry_run=False)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    advanced = argparse.SUPPRESS
    parser.add_argument("--video-root", type=Path, default=VIDEO_ROOT, help="Directory containing final video files")
    parser.add_argument("--video", action="append", default=[], help="Only process filenames containing this text")
    parser.add_argument("--frame-step", type=int, default=45, help="OCR every Nth source frame")
    parser.add_argument("--crop", choices=["lower-half", "lower-third", "full"], default="lower-half")
    parser.add_argument(
        "--scale",
        type=float,
        default=0.75,
        help=advanced,
    )
    parser.add_argument("--ocr-lang", default="chi_sim+eng", help=advanced)
    parser.add_argument("--easyocr-cpu", action="store_true", help="Run EasyOCR on CPU instead of CUDA")
    parser.add_argument(
        "--easyocr-model-dir",
        type=Path,
        default=DEFAULT_EASYOCR_MODEL_DIR,
        help=advanced,
    )
    parser.add_argument("--easyocr-no-download", action="store_true", help=advanced)
    parser.add_argument("--easyocr-frame-batch-size", type=int, default=32, help=advanced)
    parser.add_argument("--easyocr-batch-size", type=int, default=32, help=advanced)
    parser.add_argument("--easyocr-cleanup-interval", type=int, default=1, help=advanced)
    parser.add_argument("--easyocr-min-confidence", type=float, default=0.15, help=advanced)
    parser.add_argument("--low-memory", action="store_true", help="Cap EasyOCR frame and recognizer batches at 8 and clean up after every batch")
    parser.add_argument("--min-text-length", type=int, default=4, help=advanced)
    parser.add_argument("--min-normalized-chars", type=int, default=2, help=advanced)
    parser.add_argument("--min-cjk-chars", type=int, default=2, help=advanced)
    parser.add_argument("--min-ascii-letters", type=int, default=6, help=advanced)
    parser.add_argument("--min-ascii-words", type=int, default=2, help=advanced)
    parser.add_argument("--max-symbol-ratio", type=float, default=0.7, help=advanced)
    parser.add_argument("--keep-overlay-text", action="store_true", help=advanced)
    parser.add_argument("--keep-mixed-ocr-lines", action="store_true", help=advanced)
    parser.add_argument("--keep-english-only", action="store_true", help=advanced)
    parser.add_argument("--drop-short-cjk-names", action="store_true", help=advanced)
    parser.add_argument("--disable-dark-fullscreen-ocr", action="store_true", help=advanced)
    parser.add_argument("--dark-frame-threshold", type=float, default=85.0, help=advanced)
    parser.add_argument("--dark-pixel-threshold", type=int, default=32, help=advanced)
    parser.add_argument("--disable-archive-box-ocr", action="store_true", help=advanced)
    parser.add_argument("--archive-box-light-threshold", type=int, default=148, help=advanced)
    parser.add_argument("--archive-box-min-bright-ratio", type=float, default=0.12, help=advanced)
    parser.add_argument("--archive-box-min-area-ratio", type=float, default=0.18, help=advanced)
    parser.add_argument("--archive-box-min-width-ratio", type=float, default=0.35, help=advanced)
    parser.add_argument("--archive-box-min-height-ratio", type=float, default=0.20, help=advanced)
    parser.add_argument("--archive-box-min-fill-ratio", type=float, default=0.45, help=advanced)
    parser.add_argument("--archive-box-crop-padding", type=float, default=0.025, help=advanced)
    parser.add_argument("--archive-box-scale", type=float, default=1.0, help=advanced)
    parser.add_argument("--disable-frame-prefilter", action="store_true", help=advanced)
    parser.add_argument("--prefilter-duplicate-threshold", type=float, default=0.012, help=advanced)
    parser.add_argument("--prefilter-max-duplicate-skip", type=int, default=5, help=advanced)
    parser.add_argument("--prefilter-blank-stddev", type=float, default=2.5, help=advanced)
    parser.add_argument("--prefilter-blank-bright-ratio", type=float, default=0.002, help=advanced)
    parser.add_argument("--prefilter-bright-threshold", type=int, default=185, help=advanced)
    parser.add_argument("--prefilter-focus-height", type=float, default=0.72, help=advanced)
    parser.add_argument("--fast", action="store_true", help=advanced)
    parser.add_argument("--limit", type=int, default=None, help="Limit number of videos to process")
    parser.add_argument("--limit-frames", type=int, default=None, help="Limit sampled frames per video for smoke tests")
    parser.add_argument("--include-empty", action="store_true", help=advanced)
    parser.add_argument("--keep-frames", dest="keep_frames", action="store_true", default=True, help=advanced)
    parser.add_argument("--discard-frames", dest="keep_frames", action="store_false", help=advanced)
    parser.add_argument("--no-progress", action="store_true", help="Disable terminal progress bars")
    parser.add_argument("--force", action="store_true", help="Reprocess completed videos")
    parser.add_argument("--dry-run", action="store_true", help="Only list work; do not extract frames or OCR")
    parser.add_argument("--ffmpeg", default=None, help=advanced)
    parser.add_argument("--ffprobe", default=None, help=advanced)
    parser.add_argument("--ffmpeg-hwaccel", choices=["auto", "cuda", "none"], default="auto", help=advanced)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    if args.frame_step <= 0:
        parser.error("--frame-step must be greater than zero")
    if args.scale <= 0:
        parser.error("--scale must be greater than zero")
    if args.archive_box_scale <= 0:
        parser.error("--archive-box-scale must be greater than zero")
    if args.easyocr_frame_batch_size <= 0:
        parser.error("--easyocr-frame-batch-size must be greater than zero")
    if args.easyocr_batch_size <= 0:
        parser.error("--easyocr-batch-size must be greater than zero")
    if args.easyocr_cleanup_interval < 0:
        parser.error("--easyocr-cleanup-interval must be non-negative")
    if args.low_memory:
        args.easyocr_frame_batch_size = min(args.easyocr_frame_batch_size, 8)
        args.easyocr_batch_size = min(args.easyocr_batch_size, 8)
        args.easyocr_cleanup_interval = 1
    if args.fast:
        args.frame_step = max(args.frame_step, 60)
        args.scale = min(args.scale, 0.75)
        args.easyocr_cleanup_interval = max(1, args.easyocr_cleanup_interval)
    if not (0 <= args.easyocr_min_confidence <= 1):
        parser.error("--easyocr-min-confidence must be between 0 and 1")
    if args.min_text_length < 0:
        parser.error("--min-text-length must be non-negative")
    if args.min_normalized_chars < 0:
        parser.error("--min-normalized-chars must be non-negative")
    if args.min_cjk_chars < 0:
        parser.error("--min-cjk-chars must be non-negative")
    if args.min_ascii_letters < 0:
        parser.error("--min-ascii-letters must be non-negative")
    if args.min_ascii_words < 0:
        parser.error("--min-ascii-words must be non-negative")
    if not (0 <= args.max_symbol_ratio <= 1):
        parser.error("--max-symbol-ratio must be between 0 and 1")
    if not (0 <= args.dark_frame_threshold <= 100):
        parser.error("--dark-frame-threshold must be between 0 and 100")
    if not (0 <= args.dark_pixel_threshold <= 255):
        parser.error("--dark-pixel-threshold must be between 0 and 255")
    if not (0 <= args.archive_box_light_threshold <= 255):
        parser.error("--archive-box-light-threshold must be between 0 and 255")
    for option_name in (
        "archive_box_min_bright_ratio",
        "archive_box_min_area_ratio",
        "archive_box_min_width_ratio",
        "archive_box_min_height_ratio",
        "archive_box_min_fill_ratio",
        "archive_box_crop_padding",
    ):
        value = float(getattr(args, option_name))
        if not (0 <= value <= 1):
            parser.error(f"--{option_name.replace('_', '-')} must be between 0 and 1")
    if not (0 <= args.prefilter_duplicate_threshold <= 1):
        parser.error("--prefilter-duplicate-threshold must be between 0 and 1")
    if args.prefilter_max_duplicate_skip < 0:
        parser.error("--prefilter-max-duplicate-skip must be non-negative")
    if args.prefilter_blank_stddev < 0:
        parser.error("--prefilter-blank-stddev must be non-negative")
    if not (0 <= args.prefilter_blank_bright_ratio <= 1):
        parser.error("--prefilter-blank-bright-ratio must be between 0 and 1")
    if not (0 <= args.prefilter_bright_threshold <= 255):
        parser.error("--prefilter-bright-threshold must be between 0 and 255")
    if not (0.1 <= args.prefilter_focus_height <= 1):
        parser.error("--prefilter-focus-height must be between 0.1 and 1")

    global VIDEO_ROOT
    VIDEO_ROOT = args.video_root
    ffmpeg = resolve_executable("ffmpeg", args.ffmpeg)
    ffprobe = resolve_executable("ffprobe", args.ffprobe)
    if not ffmpeg:
        print("error: ffmpeg was not found on PATH; install it or pass --ffmpeg PATH", file=sys.stderr)
        return 2
    if not ffprobe:
        print("error: ffprobe was not found on PATH; install it or pass --ffprobe PATH", file=sys.stderr)
        return 2
    if args.ffmpeg_hwaccel == "auto":
        args.ffmpeg_hwaccel = "cuda" if ffmpeg_supports_cuda(ffmpeg) else "none"
    if args.ffmpeg_hwaccel == "cuda":
        print("ffmpeg decode acceleration: CUDA/NVDEC requested with CPU fallback")
    else:
        print("ffmpeg decode acceleration: CPU")
    params = params_signature(args)

    print(
        "OCR configuration: "
        f"video_root={rel_path(VIDEO_ROOT)}, frame_step={args.frame_step}, crop={args.crop}, "
        f"scale={args.scale}, easyocr_gpu={not args.easyocr_cpu}, "
        f"ffmpeg_hwaccel={args.ffmpeg_hwaccel}, "
        f"frame_batch={args.easyocr_frame_batch_size}, recognizer_batch={args.easyocr_batch_size}, "
        f"cleanup_interval={args.easyocr_cleanup_interval}, low_memory={args.low_memory}, "
        f"fast_profile={args.frame_step >= 60 and args.scale <= 0.75}, "
        f"dark_fullscreen={not args.disable_dark_fullscreen_ocr}, "
        f"archive_box_ocr={not args.disable_archive_box_ocr}, "
        f"archive_box_scale={args.archive_box_scale}, "
        f"frame_prefilter={not args.disable_frame_prefilter}, "
        f"prefilter_max_duplicate_skip={args.prefilter_max_duplicate_skip}, "
        f"frame_cache={args.keep_frames}"
    )
    print(f"OCR reports will be written under {rel_path(REPORT_DIR)}")
    refreshed_markdown = refresh_existing_video_markdown_reports()
    if refreshed_markdown:
        print(f"Refreshed {refreshed_markdown} existing per-video OCR markdown report(s)")

    videos = discover_videos(VIDEO_ROOT, args.video)
    if args.limit is not None:
        videos = videos[: args.limit]
    print(
        f"Scanning {rel_path(VIDEO_ROOT)} for final .mp4 videos"
        f"{' matching ' + ', '.join(args.video) if args.video else ''}..."
    )

    entries: list[dict[str, Any]] = []
    pending: list[tuple[Path, dict[str, Any], Path]] = []
    pending_reasons: Counter[str] = Counter()
    for path in videos:
        fingerprint = video_fingerprint(path)
        report_path = REPORT_DIR / f"{safe_report_stem(path)}_ocr.json"
        report_state, report_error = existing_report_state(report_path, fingerprint, params)
        skipped = False
        if not args.force and is_completed_report(report_path, fingerprint, params):
            existing = read_json(report_path, {})
            if isinstance(existing, dict):
                write_video_markdown(report_path, existing)
            entries.append({
                "path": fingerprint["path"],
                "name": fingerprint["name"],
                "report": rel_path(report_path),
                "status": "skipped-complete",
                "missions": existing.get("missions") or infer_missions(path),
                "part": existing.get("part") if isinstance(existing, dict) else infer_part(path),
                "stats": existing.get("stats") if isinstance(existing, dict) else {},
            })
            skipped = True
            print(f"[{path.name}] skipping existing complete OCR report")
        if not skipped:
            pending_reasons[report_state] += 1
            if report_state.startswith("retry:") and report_error:
                print(
                    f"[{path.name}] retrying previous {report_state.split(':', 1)[1]} report: "
                    f"{one_line(report_error)}"
                )
            elif report_state.startswith("stale-"):
                print(f"[{path.name}] reprocessing {report_state.replace(':', ' ')} report")
            pending.append((path, fingerprint, report_path))

    print(
        f"Discovered {len(videos)} final .mp4 video(s): "
        f"{len(entries)} skipped complete, {len(pending)} pending."
    )
    if pending_reasons:
        reason_text = ", ".join(f"{key}={value}" for key, value in sorted(pending_reasons.items()))
        print(f"Pending reasons: {reason_text}")
    if pending:
        print("Pending video order:")
        for index, (path, _fingerprint, _report_path) in enumerate(pending, start=1):
            print(f"  {index:03d}/{len(pending):03d} {path.name}")

    if args.dry_run:
        for path, fingerprint, report_path in pending:
            entries.append(pending_index_entry(path, fingerprint, report_path, status="pending"))
        write_index(entries, params, dry_run=True)
        print(f"Found {len(videos)} final video(s); {len(pending)} pending OCR run(s).")
        print(f"Wrote {rel_path(INDEX_PATH)}")
        print(f"OCR reports live under {rel_path(REPORT_DIR)}")
        return 0

    ok, detail = verify_easyocr_dependency(gpu=not args.easyocr_cpu)
    if not ok:
        for path, _fingerprint, _report_path in pending:
            entries.append(write_blocked_video_report(path, params=params, error=detail))
        write_index(entries, params, dry_run=False)
        print(f"error: {detail}", file=sys.stderr)
        print(f"Wrote {rel_path(INDEX_PATH)}", file=sys.stderr)
        print(f"OCR reports live under {rel_path(REPORT_DIR)}", file=sys.stderr)
        return 2
    print(f"Using OCR engine: {detail}")
    easyocr_reader = None
    if pending:
        print(
            "Loading EasyOCR reader "
            f"({'GPU' if not args.easyocr_cpu else 'CPU'}; languages={','.join(easyocr_languages(args.ocr_lang))})..."
        )
        easyocr_reader = create_easyocr_reader(args)

    start = time.monotonic()
    video_durations: list[float] = []
    if pending:
        write_live_index(entries, pending, params, current_position=0)
        print(f"Live OCR progress index: {rel_path(INDEX_MD_PATH)}")
        if not args.no_progress:
            progress_bar("Videos", 0, len(pending), started=start, force=True)
    for video_index, (path, _fingerprint, _report_path) in enumerate(pending, start=1):
        print(f"OCR {video_index}/{len(pending)} {rel_path(path)}")
        video_started = time.monotonic()
        entry = process_video(
            path,
            args=args,
            ffmpeg=ffmpeg,
            ffprobe=ffprobe,
            easyocr_reader=easyocr_reader,
            params=params,
        )
        video_elapsed = time.monotonic() - video_started
        video_durations.append(video_elapsed)
        entries.append(entry)
        remaining = len(pending) - video_index
        average_video_time = sum(video_durations) / len(video_durations)
        eta = average_video_time * remaining
        print(
            f"OCR {video_index}/{len(pending)} complete in {short_duration(video_elapsed)}; "
            f"remaining={remaining}; eta={short_duration(eta)}"
        )
        if not args.no_progress:
            progress_bar("Videos", video_index, len(pending), started=start, force=True)
        write_live_index(entries, pending, params, current_position=video_index)
    write_index(entries, params, dry_run=False)
    elapsed = time.monotonic() - start
    print(f"Processed {len(pending)} video(s) in {elapsed:.1f}s")
    print(f"Wrote {rel_path(INDEX_PATH)}")
    print(f"OCR reports live under {rel_path(REPORT_DIR)}")
    return 0 if not any(entry.get("status") == "error" for entry in entries) else 1


if __name__ == "__main__":
    raise SystemExit(main())
