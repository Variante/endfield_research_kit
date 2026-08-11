#!/usr/bin/env python3
"""Download Bilibili videos into the repo-local flat videos/ folder.

This script is intentionally standalone for this repository. It does not import
the older bilibili-toolbox project; it only needs requests plus ffmpeg on PATH.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import requests


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BVIDS = ("BV1JdzMBsEUc", "BV1GczqBREHJ")
DEFAULT_COOKIE_FILE = ROOT / "cookies" / "www.bilibili.com.cookies.json"
DEFAULT_OUTPUT_DIR = ROOT / "videos"
DEFAULT_CONCURRENCY = 8
DEFAULT_STALE_LOCK_MINUTES = 30
DEFAULT_DURATION_TOLERANCE_SECONDS = 2.0
# Bilibili media mirrors sometimes terminate a bounded range just before its
# end. Keep enough fresh-URL attempts for the existing partial to advance
# without forcing a whole-season retry pass for every transient truncation.
MAX_PLAYURL_REFRESH_ATTEMPTS = 64
# Several Bilibili mirrors cap bounded responses at 512 KiB even when the
# requested range is larger. Match that cap so normal responses advance without
# consuming a fresh-play-URL attempt.
RANGE_REQUEST_BYTES = 512 * 1024

VIEW_API = "https://api.bilibili.com/x/web-interface/view"
PLAYURL_API = "https://api.bilibili.com/x/player/playurl"
SEASON_ARCHIVES_API = "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list"
SEASON_PAGE_SIZE = 100
CONTENT_RANGE_TOTAL_RE = re.compile(r"/(\d+)$")
LOCAL_BVID_RE = re.compile(r"_((?:BV)[A-Za-z0-9]+)_P\d+_")

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

MEDIA_HEADERS = {
    **BASE_HEADERS,
    "Accept": "*/*",
    "Origin": "https://www.bilibili.com",
}


class DownloadError(RuntimeError):
    pass


@dataclass(frozen=True)
class PagePlan:
    bvid: str
    cid: int
    page: int
    part_title: str
    filename: str
    target: Path
    duration_seconds: float | None = None
    width: int | None = None
    height: int | None = None


@dataclass(frozen=True)
class StreamChoice:
    url: str
    label: str
    bandwidth: int
    codecs: str = ""
    width: int | None = None
    height: int | None = None
    backup_urls: tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckFailure:
    status: str
    plan: PagePlan


def load_cookie_export(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise DownloadError(f"cookie file must be a browser-exported JSON list: {path}")
    return data


def make_session(cookie_file: Path) -> requests.Session:
    if not cookie_file.exists():
        raise DownloadError(f"cookie file not found: {cookie_file}")

    session = requests.Session()
    session.headers.update(BASE_HEADERS)

    for cookie in load_cookie_export(cookie_file):
        name = cookie.get("name")
        value = cookie.get("value")
        if not name or value is None:
            continue
        session.cookies.set(
            name,
            value,
            domain=cookie.get("domain") or ".bilibili.com",
            path=cookie.get("path") or "/",
        )

    return session


def api_get(session: requests.Session, url: str, *, params: dict, referer: str) -> dict:
    headers = {"Referer": referer}
    response = session.get(url, params=params, headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    if payload.get("code") != 0:
        message = payload.get("message") or payload.get("msg") or "unknown API error"
        raise DownloadError(f"Bilibili API error {payload.get('code')}: {message}")
    data = payload.get("data")
    if not isinstance(data, dict):
        raise DownloadError("Bilibili API response did not contain a data object")
    return data


def parse_season_url(url: str) -> tuple[str, str]:
    """Return the owner mid and season id from a Bilibili season URL."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "space.bilibili.com":
        raise DownloadError(
            "season URL must use https://space.bilibili.com/<mid>/lists/<season_id>"
        )
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) != 3 or parts[1].lower() != "lists" or not parts[0].isdigit() or not parts[2].isdigit():
        raise DownloadError(
            "season URL must use https://space.bilibili.com/<mid>/lists/<season_id>"
        )
    return parts[0], parts[2]


def fetch_season_bvids(session: requests.Session, season_url: str) -> tuple[list[str], dict]:
    """Fetch all BVIDs in a Bilibili ``type=season`` collection in display order."""
    mid, season_id = parse_season_url(season_url)
    bvids: list[str] = []
    seen: set[str] = set()
    page_num = 1
    total: int | None = None
    meta: dict = {}

    while True:
        data = api_get(
            session,
            SEASON_ARCHIVES_API,
            params={
                "mid": mid,
                "season_id": season_id,
                "page_num": page_num,
                "page_size": SEASON_PAGE_SIZE,
            },
            referer=season_url,
        )
        archives = data.get("archives")
        if not isinstance(archives, list):
            archives = []
        for archive in archives:
            if not isinstance(archive, dict):
                continue
            bvid = str(archive.get("bvid") or "").strip()
            if bvid and bvid not in seen:
                seen.add(bvid)
                bvids.append(bvid)

        page = data.get("page") if isinstance(data.get("page"), dict) else {}
        if total is None:
            total = int_value(page.get("total"))
        if isinstance(data.get("meta"), dict):
            meta = data["meta"]

        if not archives or (total is not None and len(bvids) >= total) or len(archives) < SEASON_PAGE_SIZE:
            break
        page_num += 1
        if page_num > 1000:
            raise DownloadError(f"season pagination exceeded safety limit: {season_url}")

    if total is not None and len(bvids) != total:
        raise DownloadError(
            f"season returned {len(bvids)} unique BVIDs but reported {total}: {season_url}"
        )
    if not bvids:
        raise DownloadError(f"season returned no videos: {season_url}")
    return bvids, meta


def sanitize_title(text: str) -> str:
    text = re.sub(r"[^\u4e00-\u9fffA-Za-z0-9]+", "", text or "")
    return text or "untitled"


def int_value(value: object) -> int | None:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return None


def float_value(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text.upper() == "N/A":
        return None
    if ":" in text:
        try:
            total = 0.0
            for part in text.split(":"):
                total = total * 60.0 + float(part)
            return total
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def make_filename(info: dict, page: dict) -> str:
    timestamp = info.get("pubdate") or info.get("pubtime") or info.get("created")
    if timestamp is None:
        raise DownloadError("video metadata has no pubdate/pubtime/created timestamp")
    tid = info.get("tid") or info.get("typeid")
    if tid is None:
        raise DownloadError("video metadata has no tid/typeid")
    bvid = info["bvid"]
    page_no = int(page.get("page") or 1)
    title = sanitize_title(str(page.get("part") or info.get("title") or "untitled"))
    return f"{timestamp}_T{tid}_{bvid}_P{page_no}_{title}.mp4"


def build_page_plans(info: dict, output_dir: Path) -> list[PagePlan]:
    pages = info.get("pages") or []
    if not pages:
        raise DownloadError("video metadata has no pages")

    plans = []
    bvid = info["bvid"]
    for page in pages:
        dimension = page.get("dimension") if isinstance(page.get("dimension"), dict) else {}
        filename = make_filename(info, page)
        plans.append(
            PagePlan(
                bvid=bvid,
                cid=int(page["cid"]),
                page=int(page.get("page") or len(plans) + 1),
                part_title=str(page.get("part") or info.get("title") or ""),
                filename=filename,
                target=output_dir / filename,
                duration_seconds=float_value(page.get("duration")),
                width=int_value(dimension.get("width")),
                height=int_value(dimension.get("height")),
            )
        )
    return plans


def fetch_video_info(session: requests.Session, bvid: str) -> dict:
    referer = f"https://www.bilibili.com/video/{bvid}"
    info = api_get(session, VIEW_API, params={"bvid": bvid}, referer=referer)
    if "bvid" not in info:
        info["bvid"] = bvid
    return info


def choose_video_stream(streams: list[dict], prefer_codec: str, quality: int) -> StreamChoice | None:
    candidates = [item for item in streams if stream_urls(item)]
    if not candidates:
        return None

    quality_matches = [
        item
        for item in candidates
        if int_value(item.get("id")) is not None and int_value(item.get("id")) <= quality
    ]
    if quality_matches:
        candidates = quality_matches

    if prefer_codec != "any":
        codec_prefix = "avc1" if prefer_codec == "avc" else "hev1"
        codec_matches = [
            item
            for item in candidates
            if str(item.get("codecs") or "").lower().startswith(codec_prefix)
        ]
        if codec_matches:
            candidates = codec_matches

    best = max(candidates, key=lambda item: (int(item.get("id") or 0), int(item.get("bandwidth") or 0)))
    urls = stream_urls(best)
    return StreamChoice(
        url=urls[0],
        label=f"video qn={best.get('id')} codecs={best.get('codecs')}",
        bandwidth=int(best.get("bandwidth") or 0),
        codecs=str(best.get("codecs") or ""),
        width=int_value(best.get("width")),
        height=int_value(best.get("height")),
        backup_urls=urls[1:],
    )


def stream_urls(item: dict) -> tuple[str, ...]:
    primary = str(item.get("baseUrl") or item.get("base_url") or "").strip()
    raw_backups = item.get("backupUrl") or item.get("backup_url") or []
    if isinstance(raw_backups, str):
        raw_backups = [raw_backups]
    urls: list[str] = []
    for value in [primary, *(raw_backups if isinstance(raw_backups, list) else [])]:
        url = str(value or "").strip()
        if url and url not in urls:
            urls.append(url)
    return tuple(urls)


def choose_audio_stream(streams: list[dict]) -> StreamChoice | None:
    candidates = [item for item in streams if stream_urls(item)]
    if not candidates:
        return None
    best = max(candidates, key=lambda item: int(item.get("bandwidth") or 0))
    urls = stream_urls(best)
    return StreamChoice(
        url=urls[0],
        label=f"audio id={best.get('id')}",
        bandwidth=int(best.get("bandwidth") or 0),
        codecs=str(best.get("codecs") or ""),
        backup_urls=urls[1:],
    )


def stream_url_for_attempt(choice: StreamChoice, attempt: int) -> str:
    urls = (choice.url, *choice.backup_urls)
    return urls[(attempt - 1) % len(urls)]


def fetch_playurl(
    session: requests.Session,
    plan: PagePlan,
    quality: int,
    prefer_codec: str,
    playback_mode: str = "dash",
) -> tuple[StreamChoice, StreamChoice | None]:
    referer = f"https://www.bilibili.com/video/{plan.bvid}?p={plan.page}"
    data = api_get(
        session,
        PLAYURL_API,
        params={
            "bvid": plan.bvid,
            "cid": plan.cid,
            "qn": quality,
            "fnval": 0 if playback_mode == "durl" else 16,
            "fnver": 0,
            "fourk": 1,
            "high_quality": 1,
        },
        referer=referer,
    )

    durls = data.get("durl") or []
    if playback_mode == "durl" and durls:
        if len(durls) != 1:
            raise DownloadError(
                f"legacy DURL playback returned {len(durls)} segments for {plan.filename}; "
                "multi-segment DURL playback is not supported"
            )
        durl = durls[0]
        size = int(durl.get("size") or 0)
        return StreamChoice(str(durl["url"]), f"single durl stream size={size}", size), None

    dash = data.get("dash")
    if isinstance(dash, dict):
        video_choice = choose_video_stream(dash.get("video") or [], prefer_codec, quality)
        audio_choice = choose_audio_stream(dash.get("audio") or [])
        if video_choice is None:
            raise DownloadError(f"no DASH video stream found for {plan.filename}")
        return video_choice, audio_choice

    if durls:
        if len(durls) != 1:
            raise DownloadError(
                f"legacy DURL playback returned {len(durls)} segments for {plan.filename}; "
                "multi-segment DURL playback is not supported"
            )
        best = max(durls, key=lambda item: int(item.get("size") or 0))
        size = int(best.get("size") or 0)
        return StreamChoice(str(best["url"]), f"single durl stream size={size}", size), None

    raise DownloadError(f"no playable stream found for {plan.filename}")


def content_range_total(response: requests.Response) -> int | None:
    content_range = response.headers.get("Content-Range") or ""
    match = CONTENT_RANGE_TOTAL_RE.search(content_range)
    if not match:
        return None
    return int(match.group(1))


def touch_lock(lock_path: Path | None) -> None:
    if lock_path and lock_path.exists():
        os.utime(lock_path, None)


def download_stream(
    session: requests.Session,
    url: str,
    path: Path,
    *,
    referer: str,
    lock_path: Path | None = None,
    chunk_size: int = 1024 * 1024,
    max_attempts: int = 6,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    last_error: BaseException | None = None
    range_size = max(chunk_size, RANGE_REQUEST_BYTES)
    attempt = 1
    printed_start = False

    while attempt <= max_attempts:
        downloaded = path.stat().st_size if path.exists() else 0
        range_end = downloaded + range_size - 1
        headers = {**MEDIA_HEADERS, "Referer": referer}
        # Request a ranged response even for the first chunk. Some Bilibili
        # mirrors leave an unbounded full-media response idle for a page while
        # the equivalent bounded ``bytes=0-<end>`` request streams normally.
        # A server may still ignore the range; the response handling below
        # falls back to writing a fresh file for HTTP 200.
        headers["Range"] = f"bytes={downloaded}-{range_end}"

        try:
            with session.get(url, headers=headers, stream=True, timeout=(30, 60)) as response:
                if downloaded and response.status_code == 416:
                    total = content_range_total(response)
                    if total is not None and downloaded == total:
                        print(f"    -> {path.name} already complete ({downloaded} bytes)")
                        return
                    raise DownloadError(f"resume failed with HTTP 416 for incomplete part: {path}")
                if downloaded and response.status_code == 200:
                    raise DownloadError(
                        f"server ignored Range for {path.name} at {downloaded} bytes; "
                        "refreshing the media URL"
                    )
                elif response.status_code not in (200, 206):
                    raise DownloadError(f"media download failed with HTTP {response.status_code}: {url}")

                mode = "ab" if downloaded and response.status_code == 206 else "wb"
                remote_total = content_range_total(response)
                content_length = response.headers.get("Content-Length")
                if (
                    remote_total is None
                    and response.status_code == 200
                    and content_length
                    and content_length.isdigit()
                ):
                    remote_total = downloaded + int(content_length)
                total_text = f" ({remote_total} bytes)" if remote_total is not None else ""
                resume_text = f" resume from {downloaded} bytes" if downloaded else ""
                if not printed_start or (downloaded and response.status_code == 200):
                    print(f"    -> {path.name}{resume_text}{total_text}")
                    printed_start = True

                last_touch = 0.0
                with path.open(mode) as f:
                    for chunk in response.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            now = time.monotonic()
                            if now - last_touch >= 10:
                                touch_lock(lock_path)
                                last_touch = now

            actual = path.stat().st_size
            if remote_total is not None and actual == remote_total:
                return
            if remote_total is not None and actual > remote_total:
                raise DownloadError(
                    f"media part {path.name} is larger than expected: downloaded {actual} bytes, expected {remote_total}"
                )
            if remote_total is None and response.status_code == 200:
                return
            if actual <= downloaded:
                raise DownloadError(
                    f"media part {path.name} made no progress at byte {downloaded}"
                )
            touch_lock(lock_path)
            if remote_total is not None:
                # A bounded range completed successfully but the media has
                # more bytes. Continue at the new offset without consuming a
                # retry attempt; only interrupted ranges count as retries.
                attempt = 1
                continue
            last_error = DownloadError(
                f"incomplete media part {path.name}: downloaded {actual} bytes without a remote total"
            )
        except requests.RequestException as exc:
            last_error = exc

        if attempt < max_attempts:
            print(f"    -> retry {path.name} after interrupted stream (attempt {attempt + 1}/{max_attempts})")
            touch_lock(lock_path)
            time.sleep(min(10, attempt * 2))
        attempt += 1

    raise DownloadError(f"failed to download complete media part {path.name}: {last_error}")


def mux_with_ffmpeg(video_path: Path, audio_path: Path | None, final_path: Path) -> None:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise DownloadError("ffmpeg was not found on PATH")

    legacy_tmp = final_path.with_suffix(final_path.suffix + ".tmp")
    if legacy_tmp.exists():
        legacy_tmp.unlink()

    tmp_final = final_path.with_name(f"{final_path.stem}.tmp{final_path.suffix}")
    if tmp_final.exists():
        tmp_final.unlink()

    command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(video_path)]
    if audio_path is not None:
        command.extend(["-i", str(audio_path)])
    command.extend(["-c", "copy", "-f", "mp4", str(tmp_final)])

    subprocess.run(command, check=True)
    os.replace(tmp_final, final_path)


def probe_media(path: Path) -> dict:
    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        raise DownloadError("ffprobe was not found on PATH")

    command = [
        ffprobe,
        "-v",
        "error",
        "-show_format",
        "-show_streams",
        "-print_format",
        "json",
        str(path),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip() or str(exc)
        raise DownloadError(f"ffprobe failed for {path}: {detail}") from exc

    try:
        return json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise DownloadError(f"ffprobe returned invalid JSON for {path}") from exc


def codec_matches(expected: str, actual: str) -> bool:
    expected = expected.lower()
    actual = actual.lower()
    if not expected:
        return True
    if expected.startswith("avc1"):
        return actual == "h264"
    if expected.startswith(("hev1", "hvc1")):
        return actual == "hevc"
    if expected.startswith("av01"):
        return actual == "av1"
    if expected.startswith("mp4a"):
        return actual == "aac"
    return True


def format_seconds(value: float | None) -> str:
    if value is None:
        return "?s"
    return f"{value:.1f}s"


def stream_duration(stream: dict, fallback: float | None) -> float | None:
    duration = float_value(stream.get("duration"))
    if duration is not None:
        return duration
    tags = stream.get("tags") if isinstance(stream.get("tags"), dict) else {}
    duration = float_value(tags.get("DURATION") or tags.get("duration"))
    return duration if duration is not None else fallback


def stream_summary(stream: dict, duration: float | None) -> str:
    codec = stream.get("codec_name") or "unknown"
    if stream.get("codec_type") == "video":
        width = stream.get("width") or "?"
        height = stream.get("height") or "?"
        return f"{codec} {width}x{height} {format_seconds(duration)}"
    return f"{codec} {format_seconds(duration)}"


def validate_media_tracks(
    plan: PagePlan,
    probe: dict,
    *,
    video_choice: StreamChoice,
    audio_choice: StreamChoice | None,
    duration_tolerance: float,
    strict_codec: bool,
) -> list[str]:
    problems: list[str] = []
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    format_duration = float_value(format_info.get("duration"))
    video_streams = [stream for stream in streams if stream.get("codec_type") == "video"]
    audio_streams = [stream for stream in streams if stream.get("codec_type") == "audio"]

    if len(video_streams) != 1:
        problems.append(f"expected 1 video track, found {len(video_streams)}")
    if audio_choice is not None and len(audio_streams) != 1:
        problems.append(f"expected 1 audio track, found {len(audio_streams)}")
    elif audio_choice is None and len(audio_streams) > 1:
        problems.append(f"expected at most 1 audio track, found {len(audio_streams)}")

    video_duration: float | None = None
    if video_streams:
        video = video_streams[0]
        video_duration = stream_duration(video, format_duration)
        actual_width = int_value(video.get("width"))
        actual_height = int_value(video.get("height"))
        if actual_width is None or actual_height is None:
            problems.append("video dimensions are missing")
        if strict_codec and not codec_matches(video_choice.codecs, str(video.get("codec_name") or "")):
            problems.append(
                f"video codec {video.get('codec_name') or 'unknown'} != metadata {video_choice.codecs}"
            )
        if plan.duration_seconds is not None and video_duration is not None:
            delta = abs(video_duration - plan.duration_seconds)
            if delta > duration_tolerance:
                problems.append(
                    f"video duration {format_seconds(video_duration)} != metadata "
                    f"{format_seconds(plan.duration_seconds)} (delta {delta:.1f}s)"
                )

    if audio_streams:
        audio = audio_streams[0]
        audio_duration = stream_duration(audio, format_duration)
        if (
            strict_codec
            and audio_choice is not None
            and not codec_matches(audio_choice.codecs, str(audio.get("codec_name") or ""))
        ):
            problems.append(
                f"audio codec {audio.get('codec_name') or 'unknown'} != metadata {audio_choice.codecs}"
            )
        if plan.duration_seconds is not None and audio_duration is not None:
            delta = abs(audio_duration - plan.duration_seconds)
            if delta > duration_tolerance:
                problems.append(
                    f"audio duration {format_seconds(audio_duration)} != metadata "
                    f"{format_seconds(plan.duration_seconds)} (delta {delta:.1f}s)"
                )
        if video_duration is not None and audio_duration is not None:
            delta = abs(video_duration - audio_duration)
            if delta > duration_tolerance:
                problems.append(
                    f"audio/video duration mismatch: video {format_seconds(video_duration)}, "
                    f"audio {format_seconds(audio_duration)} (delta {delta:.1f}s)"
                )

    return problems


def validate_final_media(
    plan: PagePlan,
    *,
    video_choice: StreamChoice,
    audio_choice: StreamChoice | None,
    duration_tolerance: float = DEFAULT_DURATION_TOLERANCE_SECONDS,
    strict_codec: bool = False,
) -> None:
    probe = probe_media(plan.target)
    problems = validate_media_tracks(
        plan,
        probe,
        video_choice=video_choice,
        audio_choice=audio_choice,
        duration_tolerance=duration_tolerance,
        strict_codec=strict_codec,
    )
    if problems:
        detail = "; ".join(problems)
        raise DownloadError(f"muxed file failed validation for {plan.filename}: {detail}")


def validate_downloaded_media(
    plan: PagePlan,
    *,
    video_choice: StreamChoice,
    audio_choice: StreamChoice | None,
) -> None:
    try:
        validate_final_media(plan, video_choice=video_choice, audio_choice=audio_choice)
    except DownloadError:
        cleanup_parts(
            plan.target,
            plan.target.with_suffix(plan.target.suffix + ".video.m4s"),
            plan.target.with_suffix(plan.target.suffix + ".audio.m4s"),
        )
        raise


def cleanup_parts(*paths: Path) -> None:
    for path in paths:
        if path and path.exists():
            path.unlink()


def find_existing_legacy_file(output_dir: Path, filename: str, target: Path) -> Path | None:
    if not output_dir.exists():
        return None

    matches = [
        candidate
        for candidate in output_dir.rglob(filename)
        if candidate.is_file() and candidate.resolve() != target.resolve()
    ]
    if not matches:
        return None
    return max(matches, key=lambda candidate: candidate.stat().st_size)


def acquire_lock(path: Path, stale_lock_seconds: int) -> Path:
    lock_path = path.with_suffix(path.suffix + ".lock")
    while True:
        try:
            fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            break
        except FileExistsError as exc:
            age = time.time() - lock_path.stat().st_mtime
            if stale_lock_seconds >= 0 and age >= stale_lock_seconds:
                print(f"  reclaim stale lock {lock_path}")
                lock_path.unlink()
                continue
            minutes = int(age // 60)
            raise DownloadError(
                f"lock exists, another download may be active: {lock_path} "
                f"(age {minutes}m; use --stale-lock-minutes 0 to reclaim immediately)"
            ) from exc
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
    return lock_path


def download_page(
    session: requests.Session,
    plan: PagePlan,
    *,
    output_dir: Path,
    quality: int,
    prefer_codec: str,
    playback_mode: str,
    overwrite: bool,
    dry_run: bool,
    adopt_existing: bool,
    stale_lock_seconds: int,
) -> str:
    if plan.target.exists() and not overwrite:
        print(f"  skip existing {plan.target}")
        return "skipped"

    if adopt_existing and not overwrite:
        legacy = find_existing_legacy_file(output_dir, plan.filename, plan.target)
        if legacy is not None:
            if dry_run:
                print(f"  would adopt {legacy} -> {plan.target}")
                return "planned"
            print(f"  adopt {legacy} -> {plan.target}")
            plan.target.parent.mkdir(parents=True, exist_ok=True)
            os.replace(legacy, plan.target)
            return "adopted"

    if dry_run:
        print(f"  would download {plan.target}")
        return "planned"

    lock_path = acquire_lock(plan.target, stale_lock_seconds)
    referer = f"https://www.bilibili.com/video/{plan.bvid}?p={plan.page}"
    video_part = plan.target.with_suffix(plan.target.suffix + ".video.m4s")
    audio_part = plan.target.with_suffix(plan.target.suffix + ".audio.m4s")

    try:
        for stream_attempt in range(1, MAX_PLAYURL_REFRESH_ATTEMPTS + 1):
            try:
                video_choice, audio_choice = fetch_playurl(
                    session,
                    plan,
                    quality,
                    prefer_codec,
                    playback_mode,
                )
                if stream_attempt == 1:
                    print(f"  download {plan.filename}")
                else:
                    print(
                        f"  refresh play URL for {plan.filename} "
                        f"(attempt {stream_attempt}/{MAX_PLAYURL_REFRESH_ATTEMPTS})"
                    )
                print(f"    {video_choice.label}")
                download_stream(
                    session,
                    stream_url_for_attempt(video_choice, stream_attempt),
                    video_part,
                    referer=referer,
                    lock_path=lock_path,
                    max_attempts=1,
                )

                if audio_choice is not None:
                    print(f"    {audio_choice.label}")
                    download_stream(
                        session,
                        stream_url_for_attempt(audio_choice, stream_attempt),
                        audio_part,
                        referer=referer,
                        lock_path=lock_path,
                        max_attempts=1,
                    )
                    touch_lock(lock_path)
                    mux_with_ffmpeg(video_part, audio_part, plan.target)
                    validate_downloaded_media(plan, video_choice=video_choice, audio_choice=audio_choice)
                    cleanup_parts(video_part, audio_part)
                else:
                    touch_lock(lock_path)
                    mux_with_ffmpeg(video_part, None, plan.target)
                    validate_downloaded_media(plan, video_choice=video_choice, audio_choice=None)
                    cleanup_parts(video_part)
                break
            except (requests.RequestException, DownloadError) as exc:
                if stream_attempt >= MAX_PLAYURL_REFRESH_ATTEMPTS:
                    raise
                print(f"    -> stream attempt failed; refreshing Bilibili URL: {exc}")
                touch_lock(lock_path)
                time.sleep(min(10, stream_attempt * 2))
    finally:
        if lock_path.exists():
            lock_path.unlink()

    print(f"  saved {plan.target}")
    return "downloaded"


def download_page_with_fresh_session(
    cookie_file: Path,
    plan: PagePlan,
    *,
    output_dir: Path,
    quality: int,
    prefer_codec: str,
    playback_mode: str,
    overwrite: bool,
    dry_run: bool,
    adopt_existing: bool,
    stale_lock_seconds: int,
) -> str:
    session = make_session(cookie_file)
    return download_page(
        session,
        plan,
        output_dir=output_dir,
        quality=quality,
        prefer_codec=prefer_codec,
        playback_mode=playback_mode,
        overwrite=overwrite,
        dry_run=dry_run,
        adopt_existing=adopt_existing,
        stale_lock_seconds=stale_lock_seconds,
    )


def download_plans(
    session: requests.Session,
    cookie_file: Path,
    plans: list[PagePlan],
    *,
    output_dir: Path,
    quality: int,
    prefer_codec: str,
    playback_mode: str,
    overwrite: bool,
    dry_run: bool,
    adopt_existing: bool,
    concurrency: int,
    stale_lock_seconds: int,
) -> dict[str, int]:
    stats = {"planned": 0, "downloaded": 0, "skipped": 0, "adopted": 0, "failed": 0}

    if dry_run or concurrency <= 1:
        for plan in plans:
            try:
                result = download_page(
                    session,
                    plan,
                    output_dir=output_dir,
                    quality=quality,
                    prefer_codec=prefer_codec,
                    playback_mode=playback_mode,
                    overwrite=overwrite,
                    dry_run=dry_run,
                    adopt_existing=adopt_existing,
                    stale_lock_seconds=stale_lock_seconds,
                )
                stats[result] += 1
            except (requests.RequestException, subprocess.CalledProcessError, OSError, DownloadError) as exc:
                print(f"  failed {plan.filename}: {exc}")
                stats["failed"] += 1
        return stats

    workers = min(concurrency, len(plans))
    print(f"  downloading with concurrency={workers}")
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                download_page_with_fresh_session,
                cookie_file,
                plan,
                output_dir=output_dir,
                quality=quality,
                prefer_codec=prefer_codec,
                playback_mode=playback_mode,
                overwrite=overwrite,
                dry_run=dry_run,
                adopt_existing=adopt_existing,
                stale_lock_seconds=stale_lock_seconds,
            ): plan
            for plan in plans
        }
        for future in as_completed(futures):
            plan = futures[future]
            try:
                result = future.result()
                stats[result] += 1
            except (requests.RequestException, subprocess.CalledProcessError, OSError, DownloadError) as exc:
                print(f"  failed {plan.filename}: {exc}")
                stats["failed"] += 1

    return stats


def media_track_summary(probe: dict) -> str:
    streams = probe.get("streams") if isinstance(probe.get("streams"), list) else []
    format_info = probe.get("format") if isinstance(probe.get("format"), dict) else {}
    format_duration = float_value(format_info.get("duration"))
    parts = []
    for stream_type in ("video", "audio"):
        matches = [stream for stream in streams if stream.get("codec_type") == stream_type]
        if matches:
            parts.append(f"{stream_type}={stream_summary(matches[0], stream_duration(matches[0], format_duration))}")
        else:
            parts.append(f"{stream_type}=missing")
    return ", ".join(parts)


def incomplete_parts(plan: PagePlan) -> list[Path]:
    candidates = [
        plan.target.with_suffix(plan.target.suffix + ".lock"),
        plan.target.with_suffix(plan.target.suffix + ".video.m4s"),
        plan.target.with_suffix(plan.target.suffix + ".audio.m4s"),
    ]
    return [path for path in candidates if path.exists()]


def check_existing_page(
    session: requests.Session,
    plan: PagePlan,
    *,
    quality: int,
    prefer_codec: str,
    playback_mode: str,
    duration_tolerance: float,
    strict_codec: bool,
) -> str:
    if not plan.target.exists():
        parts = incomplete_parts(plan)
        if parts:
            names = ", ".join(path.name for path in parts)
            print(f"  incomplete {plan.filename}: {names}")
            return "incomplete"
        print(f"  missing {plan.filename}")
        return "missing"

    video_choice, audio_choice = fetch_playurl(
        session,
        plan,
        quality,
        prefer_codec,
        playback_mode,
    )
    probe = probe_media(plan.target)
    problems = validate_media_tracks(
        plan,
        probe,
        video_choice=video_choice,
        audio_choice=audio_choice,
        duration_tolerance=duration_tolerance,
        strict_codec=strict_codec,
    )
    if problems:
        print(f"  mismatch {plan.filename} ({media_track_summary(probe)})")
        for problem in problems:
            print(f"    - {problem}")
        return "failed"

    print(f"  ok {plan.filename} ({media_track_summary(probe)})")
    return "ok"


def check_existing_plans(
    session: requests.Session,
    plans: list[PagePlan],
    *,
    quality: int,
    prefer_codec: str,
    playback_mode: str,
    duration_tolerance: float,
    strict_codec: bool,
) -> tuple[dict[str, int], list[CheckFailure]]:
    stats = {"ok": 0, "missing": 0, "incomplete": 0, "failed": 0}
    failures = []
    for plan in plans:
        try:
            result = check_existing_page(
                session,
                plan,
                quality=quality,
                prefer_codec=prefer_codec,
                playback_mode=playback_mode,
                duration_tolerance=duration_tolerance,
                strict_codec=strict_codec,
            )
            stats[result] += 1
            if result != "ok":
                failures.append(CheckFailure(result, plan))
        except (requests.RequestException, subprocess.CalledProcessError, OSError, DownloadError) as exc:
            print(f"  failed {plan.filename}: {exc}")
            stats["failed"] += 1
            failures.append(CheckFailure("failed", plan))
    return stats, failures


def print_failed_pages(failures: list[CheckFailure]) -> None:
    if not failures:
        print("failed videos: none")
        return

    print("failed videos:")
    for failure in failures:
        print(f"  [{failure.status}] {failure.plan.filename}")


def read_bvid_file(path: Path) -> list[str]:
    values = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.partition("#")[0].strip()
            if line:
                values.append(line)
    return values


def unique_ordered(values: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def local_bvids(output_dir: Path) -> list[str]:
    if not output_dir.exists():
        return []
    bvids = []
    for candidate in sorted(output_dir.glob("*")):
        if not candidate.is_file():
            continue
        match = LOCAL_BVID_RE.search(candidate.name)
        if match:
            bvids.append(match.group(1))
    return unique_ordered(bvids)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "bvids",
        nargs="*",
        help=f"BVIDs to download. Defaults to {', '.join(DEFAULT_BVIDS)} when no BVID or file is given.",
    )
    parser.add_argument(
        "--bvid-file",
        type=Path,
        help="Optional UTF-8 text file with one BVID per line. # comments are allowed.",
    )
    parser.add_argument(
        "--season-url",
        action="append",
        default=[],
        help=(
            "Bilibili season URL such as "
            "https://space.bilibili.com/609095014/lists/7246850?type=season. "
            "All season BVIDs are added in displayed order; may be repeated."
        ),
    )
    parser.add_argument(
        "--cookies",
        type=Path,
        default=DEFAULT_COOKIE_FILE,
        help=f"Browser-exported Bilibili cookies JSON. Default: {DEFAULT_COOKIE_FILE}",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Flat output folder. Default: {DEFAULT_OUTPUT_DIR}",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=80,
        help="Requested Bilibili quality number. 80 is 1080P; 120 is 4K when available.",
    )
    parser.add_argument(
        "--prefer-codec",
        choices=("avc", "hevc", "any"),
        default="avc",
        help="Prefer AVC/H.264 by default for easier local playback.",
    )
    parser.add_argument(
        "--playback-mode",
        choices=("dash", "durl"),
        default="dash",
        help=(
            "Bilibili playback representation to request. DASH is the default; "
            "use durl for pages whose DASH stream is shorter than the page duration."
        ),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=DEFAULT_CONCURRENCY,
        help=(
            f"Number of pages to download at the same time. Default: {DEFAULT_CONCURRENCY}. "
            "Use 1 for sequential behavior."
        ),
    )
    parser.add_argument(
        "--stale-lock-minutes",
        type=int,
        default=DEFAULT_STALE_LOCK_MINUTES,
        help=(
            "Reclaim a leftover .lock file after this many minutes. "
            f"Default: {DEFAULT_STALE_LOCK_MINUTES}; use 0 to reclaim immediately."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Re-download even when the final flat mp4 already exists.",
    )
    parser.add_argument(
        "--no-adopt-existing",
        action="store_true",
        help="Do not move exact matching legacy files from nested videos/ folders into the flat output path.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch metadata and print planned output paths without downloading media.",
    )
    parser.add_argument(
        "--check-existing",
        action="store_true",
        help=(
            "Validate existing local mp4 files against Bilibili metadata with ffprobe, "
            "without downloading media. With no BVIDs, checks BVIDs found in the output folder."
        ),
    )
    parser.add_argument(
        "--retry-failed",
        action="store_true",
        help=(
            "After checking existing files, print failed/missing/incomplete videos and "
            "re-download only those pages. Implies --check-existing."
        ),
    )
    parser.add_argument(
        "--duration-tolerance",
        type=float,
        default=DEFAULT_DURATION_TOLERANCE_SECONDS,
        help=(
            "Allowed seconds of drift when checking media track durations. "
            f"Default: {DEFAULT_DURATION_TOLERANCE_SECONDS}."
        ),
    )
    parser.add_argument(
        "--strict-codec",
        action="store_true",
        help="When checking existing files, require the local codec to match the currently selected Bilibili stream.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.retry_failed:
        args.check_existing = True

    output_dir = args.output_dir.resolve()
    cookie_file = args.cookies.resolve()
    session = make_session(cookie_file)

    bvids: list[str] = []
    for season_url in args.season_url:
        season_bvids, season_meta = fetch_season_bvids(session, season_url)
        season_name = str(season_meta.get("name") or season_meta.get("title") or "season")
        print(f"season {season_name}: {len(season_bvids)} video(s) from {season_url}")
        bvids.extend(season_bvids)
    bvids.extend(args.bvids)
    if args.bvid_file:
        bvids.extend(read_bvid_file(args.bvid_file))
    if args.check_existing and not bvids:
        bvids = local_bvids(output_dir)
    if not bvids:
        bvids = list(DEFAULT_BVIDS)
    bvids = unique_ordered(bvids)

    cookie_file = args.cookies.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    concurrency = max(1, args.concurrency)
    stale_lock_seconds = max(0, args.stale_lock_minutes) * 60

    if args.check_existing:
        stats = {"ok": 0, "missing": 0, "incomplete": 0, "failed": 0}
        failures: list[CheckFailure] = []
    else:
        stats = {"planned": 0, "downloaded": 0, "skipped": 0, "adopted": 0, "failed": 0}

    for bvid in bvids:
        print(f"{bvid}")
        info = fetch_video_info(session, bvid)
        plans = build_page_plans(info, output_dir)
        print(f"  {info.get('title', '')} ({len(plans)} page(s))")
        if args.check_existing:
            bvid_stats, bvid_failures = check_existing_plans(
                session,
                plans,
                quality=args.quality,
                prefer_codec=args.prefer_codec,
                playback_mode=args.playback_mode,
                duration_tolerance=max(0.0, args.duration_tolerance),
                strict_codec=args.strict_codec,
            )
            failures.extend(bvid_failures)
        else:
            bvid_stats = download_plans(
                session,
                cookie_file,
                plans,
                output_dir=output_dir,
                quality=args.quality,
                prefer_codec=args.prefer_codec,
                playback_mode=args.playback_mode,
                overwrite=args.overwrite,
                dry_run=args.dry_run,
                adopt_existing=not args.no_adopt_existing,
                concurrency=concurrency,
                stale_lock_seconds=stale_lock_seconds,
            )
        for key, value in bvid_stats.items():
            stats[key] += value

    if args.check_existing:
        print_failed_pages(failures)
        if args.retry_failed and failures:
            retry_plans = [failure.plan for failure in failures]
            print(f"retrying {len(retry_plans)} failed video(s)")
            retry_stats = download_plans(
                session,
                cookie_file,
                retry_plans,
                output_dir=output_dir,
                quality=args.quality,
                prefer_codec=args.prefer_codec,
                playback_mode=args.playback_mode,
                overwrite=True,
                dry_run=args.dry_run,
                adopt_existing=False,
                concurrency=concurrency,
                stale_lock_seconds=stale_lock_seconds,
            )
            print(
                "retry done: "
                + ", ".join(f"{key}={value}" for key, value in retry_stats.items() if value)
            )
            if not args.dry_run and not retry_stats["failed"]:
                stats["failed"] = 0
                stats["missing"] = 0
                stats["incomplete"] = 0
            elif retry_stats["failed"]:
                stats["failed"] = retry_stats["failed"]

    print(
        "done: "
        + ", ".join(f"{key}={value}" for key, value in stats.items() if value)
    )
    if args.check_existing:
        return 1 if stats["failed"] or stats["missing"] or stats["incomplete"] else 0
    return 1 if stats["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\ninterrupted", file=sys.stderr)
        raise SystemExit(130)
    except (requests.RequestException, subprocess.CalledProcessError, OSError, DownloadError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
