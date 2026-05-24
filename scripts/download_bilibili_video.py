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

import requests


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BVIDS = ("BV1JdzMBsEUc", "BV1GczqBREHJ")
DEFAULT_COOKIE_FILE = ROOT / "cookies" / "www.bilibili.com.cookies.json"
DEFAULT_OUTPUT_DIR = ROOT / "videos"
DEFAULT_CONCURRENCY = 8
DEFAULT_STALE_LOCK_MINUTES = 30

VIEW_API = "https://api.bilibili.com/x/web-interface/view"
PLAYURL_API = "https://api.bilibili.com/x/player/playurl"
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


def choose_video_stream(streams: list[dict], prefer_codec: str) -> StreamChoice | None:
    candidates = [item for item in streams if item.get("baseUrl") or item.get("base_url")]
    if not candidates:
        return None

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
    return StreamChoice(
        url=str(best.get("baseUrl") or best.get("base_url")),
        label=f"video qn={best.get('id')} codecs={best.get('codecs')}",
        bandwidth=int(best.get("bandwidth") or 0),
        codecs=str(best.get("codecs") or ""),
        width=int_value(best.get("width")),
        height=int_value(best.get("height")),
    )


def choose_audio_stream(streams: list[dict]) -> StreamChoice | None:
    candidates = [item for item in streams if item.get("baseUrl") or item.get("base_url")]
    if not candidates:
        return None
    best = max(candidates, key=lambda item: int(item.get("bandwidth") or 0))
    return StreamChoice(
        url=str(best.get("baseUrl") or best.get("base_url")),
        label=f"audio id={best.get('id')}",
        bandwidth=int(best.get("bandwidth") or 0),
        codecs=str(best.get("codecs") or ""),
    )


def fetch_playurl(session: requests.Session, plan: PagePlan, quality: int, prefer_codec: str) -> tuple[StreamChoice, StreamChoice | None]:
    referer = f"https://www.bilibili.com/video/{plan.bvid}?p={plan.page}"
    data = api_get(
        session,
        PLAYURL_API,
        params={
            "bvid": plan.bvid,
            "cid": plan.cid,
            "qn": quality,
            "fnval": 16,
            "fnver": 0,
            "fourk": 1,
            "high_quality": 1,
        },
        referer=referer,
    )

    dash = data.get("dash")
    if isinstance(dash, dict):
        video_choice = choose_video_stream(dash.get("video") or [], prefer_codec)
        audio_choice = choose_audio_stream(dash.get("audio") or [])
        if video_choice is None:
            raise DownloadError(f"no DASH video stream found for {plan.filename}")
        return video_choice, audio_choice

    durls = data.get("durl") or []
    if durls:
        best = max(durls, key=lambda item: int(item.get("size") or 0))
        return StreamChoice(str(best["url"]), "single durl stream", int(best.get("size") or 0)), None

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
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    downloaded = path.stat().st_size if path.exists() else 0

    headers = {**MEDIA_HEADERS, "Referer": referer}
    if downloaded:
        headers["Range"] = f"bytes={downloaded}-"

    with session.get(url, headers=headers, stream=True, timeout=(30, 60)) as response:
        if downloaded and response.status_code == 416:
            total = content_range_total(response)
            if total is not None and downloaded == total:
                print(f"    -> {path.name} already complete ({downloaded} bytes)")
                return
            raise DownloadError(f"resume failed with HTTP 416 for incomplete part: {path}")
        if downloaded and response.status_code == 200:
            print(f"    -> {path.name} restarting; server ignored Range for {downloaded} bytes")
            downloaded = 0
        elif response.status_code not in (200, 206):
            raise DownloadError(f"media download failed with HTTP {response.status_code}: {url}")

        mode = "ab" if downloaded and response.status_code == 206 else "wb"
        remote_total = content_range_total(response)
        content_length = response.headers.get("Content-Length")
        if remote_total is None and content_length and content_length.isdigit():
            remote_total = downloaded + int(content_length)
        total_text = f" ({remote_total} bytes)" if remote_total is not None else ""
        resume_text = f" resume from {downloaded} bytes" if downloaded else ""
        print(f"    -> {path.name}{resume_text}{total_text}")

        last_touch = 0.0
        with path.open(mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    now = time.monotonic()
                    if now - last_touch >= 10:
                        touch_lock(lock_path)
                        last_touch = now


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
        video_choice, audio_choice = fetch_playurl(session, plan, quality, prefer_codec)
        print(f"  download {plan.filename}")
        print(f"    {video_choice.label}")
        download_stream(session, video_choice.url, video_part, referer=referer, lock_path=lock_path)

        if audio_choice is not None:
            print(f"    {audio_choice.label}")
            download_stream(session, audio_choice.url, audio_part, referer=referer, lock_path=lock_path)
            touch_lock(lock_path)
            mux_with_ffmpeg(video_part, audio_part, plan.target)
            cleanup_parts(video_part, audio_part)
        else:
            touch_lock(lock_path)
            mux_with_ffmpeg(video_part, None, plan.target)
            cleanup_parts(video_part)
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
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    bvids = list(args.bvids)
    if args.bvid_file:
        bvids.extend(read_bvid_file(args.bvid_file))
    if not bvids:
        bvids = list(DEFAULT_BVIDS)
    bvids = unique_ordered(bvids)

    cookie_file = args.cookies.resolve()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    concurrency = max(1, args.concurrency)
    stale_lock_seconds = max(0, args.stale_lock_minutes) * 60

    session = make_session(cookie_file)
    stats = {"planned": 0, "downloaded": 0, "skipped": 0, "adopted": 0, "failed": 0}

    for bvid in bvids:
        print(f"{bvid}")
        info = fetch_video_info(session, bvid)
        plans = build_page_plans(info, output_dir)
        print(f"  {info.get('title', '')} ({len(plans)} page(s))")
        bvid_stats = download_plans(
            session,
            cookie_file,
            plans,
            output_dir=output_dir,
            quality=args.quality,
            prefer_codec=args.prefer_codec,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            adopt_existing=not args.no_adopt_existing,
            concurrency=concurrency,
            stale_lock_seconds=stale_lock_seconds,
        )
        for key, value in bvid_stats.items():
            stats[key] += value

    print(
        "done: "
        + ", ".join(f"{key}={value}" for key, value in stats.items() if value)
    )
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
