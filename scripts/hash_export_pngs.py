"""Hash every PNG under export_full and write a path/hash CSV.

Run from the repo root:
    python scripts/hash_export_pngs.py
    python scripts/hash_export_pngs.py --workers 32
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import hashlib
import os
import sys
import time
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from common import EXPORT_ROOT, REPORTS_DIR

DEFAULT_OUTPUT = REPORTS_DIR / "export_full_png_hashes.csv"
DEFAULT_CHUNK_SIZE = 8 * 1024 * 1024
PROGRESS_EVERY = 1000
FIXED_LENGTH_ALGORITHMS = sorted(
    algorithm for algorithm in hashlib.algorithms_guaranteed if not algorithm.startswith("shake_")
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hash all PNG files under an export tree and write path,hash CSV rows.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help=f"Export tree to scan. Defaults to {EXPORT_ROOT}.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"CSV path to write. Defaults to {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--algorithm",
        default="sha256",
        choices=FIXED_LENGTH_ALGORITHMS,
        help="Hash algorithm to use. Defaults to sha256.",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=min(32, (os.cpu_count() or 4) * 4),
        help="Parallel file hashing workers. Defaults to min(32, cpu_count * 4).",
    )
    parser.add_argument(
        "--chunk-size-mib",
        type=int,
        default=DEFAULT_CHUNK_SIZE // (1024 * 1024),
        help="Per-read chunk size in MiB. Defaults to 8.",
    )
    parser.add_argument(
        "--no-sort",
        action="store_true",
        help="Write rows as workers finish instead of sorting by path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress output.",
    )
    return parser.parse_args(argv)


def iter_png_paths(root: Path):
    stack = [root]
    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_dir(follow_symlinks=False):
                            stack.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False) and entry.name.lower().endswith(".png"):
                            yield Path(entry.path)
                    except OSError as exc:
                        print(f"warning: skipping {entry.path}: {exc}", file=sys.stderr)
        except OSError as exc:
            print(f"warning: skipping {current}: {exc}", file=sys.stderr)


def hash_file(path: Path, root: Path, algorithm: str, chunk_size: int) -> tuple[str, str]:
    digest = hashlib.new(algorithm)
    with path.open("rb", buffering=0) as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            digest.update(chunk)
    return path.relative_to(root).as_posix(), digest.hexdigest()


def write_sorted_csv(
    output_path: Path,
    rows: list[tuple[str, str]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    rows.sort(key=lambda item: item[0].casefold())
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle, lineterminator="\n")
        writer.writerow(("path", "hash"))
        writer.writerows(rows)


def hash_pngs(args: argparse.Namespace) -> tuple[int, float]:
    export_root = args.export_root.resolve()
    output_path = args.output.resolve()
    chunk_size = max(1, args.chunk_size_mib) * 1024 * 1024
    workers = max(1, args.workers)

    if not export_root.is_dir():
        raise SystemExit(f"export root does not exist or is not a directory: {export_root}")

    started = time.perf_counter()
    png_paths = list(iter_png_paths(export_root))
    if not args.quiet:
        print(f"Found {len(png_paths):,} PNG files under {export_root}")

    completed = 0
    if args.no_sort:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle, lineterminator="\n")
            writer.writerow(("path", "hash"))
            with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
                futures = [
                    executor.submit(hash_file, path, export_root, args.algorithm, chunk_size)
                    for path in png_paths
                ]
                for future in concurrent.futures.as_completed(futures):
                    writer.writerow(future.result())
                    completed += 1
                    if not args.quiet and completed % PROGRESS_EVERY == 0:
                        print(f"Hashed {completed:,}/{len(png_paths):,} PNG files...", file=sys.stderr)
    else:
        rows: list[tuple[str, str]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [
                executor.submit(hash_file, path, export_root, args.algorithm, chunk_size)
                for path in png_paths
            ]
            for future in concurrent.futures.as_completed(futures):
                rows.append(future.result())
                completed += 1
                if not args.quiet and completed % PROGRESS_EVERY == 0:
                    print(f"Hashed {completed:,}/{len(png_paths):,} PNG files...", file=sys.stderr)
        write_sorted_csv(output_path, rows)

    elapsed = time.perf_counter() - started
    if not args.quiet:
        print(f"Wrote {completed:,} hashes to {output_path}")
        print(f"Elapsed: {elapsed:.2f}s")
    return completed, elapsed


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    hash_pngs(args)


if __name__ == "__main__":
    main()
