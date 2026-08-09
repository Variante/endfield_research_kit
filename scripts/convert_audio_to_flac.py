#!/usr/bin/env python3
"""Convert decoded WAV audio into lossless FLAC files for the WebUI."""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Iterable


FLAC_SUFFIX = ".flac"
WAV_SUFFIX = ".wav"
DEFAULT_JOBS = max(1, min(4, os.cpu_count() or 1))


def resolve_ffmpeg(value: str | Path | None = None) -> Path:
    """Resolve an explicit ffmpeg path or the executable available on PATH."""
    if value:
        path = Path(value).expanduser()
        if path.is_file():
            return path.resolve()
        raise FileNotFoundError(f"ffmpeg executable not found: {path}")
    discovered = shutil.which("ffmpeg")
    if not discovered:
        raise FileNotFoundError(
            "ffmpeg was not found on PATH; install ffmpeg or pass --ffmpeg PATH"
        )
    return Path(discovered).resolve()


def iter_wav_files(audio_root: Path) -> Iterable[Path]:
    """Yield decoded WAV files below an audio root in stable order."""
    if not audio_root.exists():
        return
    yield from sorted(
        path
        for path in audio_root.rglob("*")
        if path.is_file() and path.suffix.lower() == WAV_SUFFIX
    )


def flac_path_for(source: Path) -> Path:
    return source.with_suffix(FLAC_SUFFIX)


def should_convert(source: Path, destination: Path, *, force: bool = False) -> bool:
    if force or not destination.exists():
        return True
    if destination.stat().st_size <= 0:
        return True
    return source.stat().st_mtime_ns > destination.stat().st_mtime_ns


def convert_one(
    ffmpeg: Path,
    source: Path,
    destination: Path,
    *,
    delete_source: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> str:
    """Convert one WAV atomically and optionally remove the source WAV."""
    if not should_convert(source, destination, force=force):
        if delete_source and destination.exists() and destination.stat().st_size > 0:
            source.unlink()
        return "skipped"
    if dry_run:
        return "planned"

    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temporary = tempfile.mkstemp(
        prefix=f".{destination.stem}.",
        suffix=FLAC_SUFFIX,
        dir=destination.parent,
    )
    os.close(descriptor)
    temporary = Path(raw_temporary)
    try:
        command = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-i",
            str(source),
            "-map",
            "0:a:0",
            "-map_metadata",
            "-1",
            "-c:a",
            "flac",
            str(temporary),
        ]
        subprocess.run(command, check=True)
        if not temporary.exists() or temporary.stat().st_size <= 0:
            raise RuntimeError(f"ffmpeg produced no FLAC output for {source}")
        os.replace(temporary, destination)
        if delete_source:
            source.unlink()
        return "converted"
    finally:
        temporary.unlink(missing_ok=True)


def convert_audio_root(
    audio_root: Path,
    *,
    ffmpeg: str | Path | None = None,
    jobs: int = DEFAULT_JOBS,
    delete_source: bool = False,
    force: bool = False,
    dry_run: bool = False,
) -> dict[str, int]:
    """Convert every WAV below ``audio_root`` and return bounded counters."""
    sources = list(iter_wav_files(audio_root))
    stats = {"scanned": len(sources), "converted": 0, "skipped": 0, "planned": 0, "failed": 0}
    if not sources:
        return stats
    encoder = resolve_ffmpeg(ffmpeg) if not dry_run else None
    worker_count = max(1, int(jobs or 1))

    def convert(source: Path) -> str:
        return convert_one(
            encoder,  # type: ignore[arg-type]
            source,
            flac_path_for(source),
            delete_source=delete_source,
            force=force,
            dry_run=dry_run,
        )

    failures: list[tuple[Path, Exception]] = []
    completed = 0
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(convert, source): source for source in sources}
        for future in as_completed(futures):
            source = futures[future]
            try:
                stats[future.result()] += 1
                completed += 1
                if not dry_run and (completed % 1000 == 0 or completed == len(sources)):
                    print(
                        f"FLAC audio conversion: {completed:,}/{len(sources):,} complete",
                        flush=True,
                    )
            except Exception as exc:  # pragma: no cover - exercised by CLI failures
                stats["failed"] += 1
                if len(failures) < 8:
                    failures.append((source, exc))

    if failures:
        details = "; ".join(f"{source}: {error}" for source, error in failures)
        if stats["failed"] > len(failures):
            details += f"; and {stats['failed'] - len(failures):,} more failure(s)"
        raise RuntimeError(f"FLAC conversion failed: {details}")
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--audio-root",
        type=Path,
        default=Path("export_full/structured/Audio"),
        help="Root containing decoded WAV files.",
    )
    parser.add_argument("--ffmpeg", type=Path, default=None, help="Path to ffmpeg.")
    parser.add_argument("--jobs", type=int, default=DEFAULT_JOBS)
    parser.add_argument(
        "--delete-source",
        action="store_true",
        help="Delete each WAV only after its FLAC replacement is complete.",
    )
    parser.add_argument("--force", action="store_true", help="Re-encode even when FLAC is newer.")
    parser.add_argument("--dry-run", action="store_true", help="Report planned conversions without writing files.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stats = convert_audio_root(
        args.audio_root.resolve(),
        ffmpeg=args.ffmpeg,
        jobs=args.jobs,
        delete_source=args.delete_source,
        force=args.force,
        dry_run=args.dry_run,
    )
    print(
        "FLAC audio conversion: "
        f"{stats['scanned']:,} scanned, "
        f"{stats['converted']:,} converted, "
        f"{stats['skipped']:,} skipped, "
        f"{stats['planned']:,} planned"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
