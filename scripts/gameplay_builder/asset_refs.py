"""Build the compact Gameplay-to-exported-asset sidecar.

Run from the repository root:

    python scripts/build_gameplay_asset_refs.py

The broad Assets index remains the source of paths; this command only writes a
small bounded lookup for Gameplay thumbnails and model links.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

SCRIPT_DIR = Path(__file__).resolve().parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from asset_builder.gameplay_refs import DEFAULT_OUTPUT, build_from_paths
from common import ASSET_DIR, LANG_DIR, ROOT


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build compact Gameplay asset references.")
    parser.add_argument(
        "--language",
        default="CN",
        help="Gameplay language payload to index (default: CN).",
    )
    parser.add_argument(
        "--asset-index",
        type=Path,
        default=ASSET_DIR / "index.json",
        help="Broad exported asset index.",
    )
    parser.add_argument(
        "--gameplay-index",
        type=Path,
        default=None,
        help="Override the Gameplay index path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output sidecar path.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    language = str(args.language or "CN").upper()
    gameplay_path = args.gameplay_index or (LANG_DIR / language / "gameplay" / "index.json")
    if not gameplay_path.is_file() or not args.asset_index.is_file():
        print(
            f"{language}: Gameplay asset refs skipped (missing "
            f"{gameplay_path if not gameplay_path.is_file() else args.asset_index})"
        )
        return 0
    payload = build_from_paths(args.gameplay_index or gameplay_path, args.asset_index, args.output)
    counts = payload.get("counts") or {}
    display = args.output.relative_to(ROOT) if args.output.is_relative_to(ROOT) else args.output
    print(
        f"{language}: {counts.get('matchedEntries', 0)} matched Gameplay entries; "
        f"{counts.get('withImages', 0)} with images; {counts.get('withModels', 0)} with models -> {display}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
