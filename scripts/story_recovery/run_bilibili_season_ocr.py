#!/usr/bin/env python3
"""Run the existing gameplay-video OCR sampler over the new Bilibili season.

The season is downloaded into its own directory so this source can be OCRed
without mixing it with the older flat ``videos/`` intake. Its per-video OCR
reports and disposable frame cache are isolated by default as well.

Download the source first:

    python scripts/download_bilibili_video.py ^
      --season-url "https://space.bilibili.com/609095014/lists/7246850?type=season" ^
      --output-dir videos/bilibili_season_7246850

Then run a smoke test:

    python scripts/story_recovery/run_bilibili_season_ocr.py --limit 1 --limit-frames 20

For the complete source, omit both limits. Use ``--discard-frames`` when
reviewable frame images are not needed and disk usage should stay lower.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_VIDEO_ROOT = ROOT / "videos" / "bilibili_season_7246850"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "gameplay_video_ocr" / "bilibili_season_7246850"
DEFAULT_TMP_ROOT = ROOT / "tmp" / "ocr" / "bilibili_season_7246850"
OCR_SCRIPT = ROOT / "scripts" / "story_recovery" / "build_gameplay_video_ocr_audit.py"


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--video-root",
        type=Path,
        default=DEFAULT_VIDEO_ROOT,
        help=f"Downloaded season directory (default: {DEFAULT_VIDEO_ROOT})",
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_ROOT,
        help=f"Per-video OCR report directory (default: {DEFAULT_REPORT_ROOT})",
    )
    parser.add_argument("--tmp-root", type=Path, default=DEFAULT_TMP_ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--frame-step", type=int, default=10, help="OCR every Nth source frame")
    parser.add_argument(
        "--crop",
        choices=["subtitle", "lower-half", "lower-third", "full"],
        default="subtitle",
    )
    parser.add_argument(
        "--ocr-engine",
        choices=["paddleocr", "easyocr"],
        default="paddleocr",
        help="OCR engine (default: paddleocr / PP-OCRv5)",
    )
    parser.add_argument(
        "--paddleocr-variant",
        choices=["server", "mobile"],
        default="server",
        help="PP-OCRv5 model variant (default: server)",
    )
    parser.add_argument("--paddleocr-frame-batch-size", type=int, default=40)
    parser.add_argument("--limit", type=int, default=None, help="Limit videos for a smoke test")
    parser.add_argument("--limit-frames", type=int, default=None, help="Limit sampled frames per video")
    parser.add_argument("--force", action="store_true", help="Reprocess completed OCR reports")
    parser.add_argument("--easyocr-cpu", action="store_true")
    parser.add_argument("--disable-archive-box-ocr", action="store_true")
    parser.add_argument("--disable-ocr-dictionary", action="store_true")
    parser.add_argument("--keep-frames", dest="keep_frames", action="store_true", default=True)
    parser.add_argument("--discard-frames", dest="keep_frames", action="store_false")
    parser.add_argument("--no-progress", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="List pending OCR work without running OCR")
    return parser


def build_command(args: argparse.Namespace) -> list[str]:
    command = [
        sys.executable,
        str(OCR_SCRIPT),
        "--video-root",
        str(args.video_root.resolve()),
        "--report-dir",
        str(args.report_dir.resolve()),
        "--tmp-root",
        str(args.tmp_root.resolve()),
        "--frame-step",
        str(args.frame_step),
        "--crop",
        args.crop,
        "--ocr-engine",
        args.ocr_engine,
        "--paddleocr-variant",
        args.paddleocr_variant,
        "--paddleocr-frame-batch-size",
        str(args.paddleocr_frame_batch_size),
    ]
    if args.limit is not None:
        command.extend(["--limit", str(args.limit)])
    if args.limit_frames is not None:
        command.extend(["--limit-frames", str(args.limit_frames)])
    if args.force:
        command.append("--force")
    if args.easyocr_cpu:
        command.append("--easyocr-cpu")
    if args.disable_archive_box_ocr:
        command.append("--disable-archive-box-ocr")
    if args.disable_ocr_dictionary:
        command.append("--disable-ocr-dictionary")
    if not args.keep_frames:
        command.append("--discard-frames")
    if args.no_progress:
        command.append("--no-progress")
    if args.dry_run:
        command.append("--dry-run")
    return command


def main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    if args.frame_step <= 0:
        print("error: --frame-step must be greater than zero", file=sys.stderr)
        return 2
    if args.paddleocr_frame_batch_size <= 0:
        print("error: --paddleocr-frame-batch-size must be greater than zero", file=sys.stderr)
        return 2
    if args.limit is not None and args.limit <= 0:
        print("error: --limit must be greater than zero", file=sys.stderr)
        return 2
    if args.limit_frames is not None and args.limit_frames <= 0:
        print("error: --limit-frames must be greater than zero", file=sys.stderr)
        return 2
    if not args.video_root.is_dir():
        print(f"error: season video directory not found: {args.video_root}", file=sys.stderr)
        print("Run scripts/download_bilibili_video.py with --season-url first.", file=sys.stderr)
        return 2
    return subprocess.run(build_command(args), cwd=str(ROOT), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
