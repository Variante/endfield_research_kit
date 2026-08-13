"""Focused command-line entry point for the source Story gap builder."""
from __future__ import annotations

import argparse
from pathlib import Path

from .api import ROOT, build_source_gap_queue


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the source-only Story recovery gap queue."
    )
    parser.add_argument("--language", default="CN")
    parser.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports" / "mission_order",
    )
    parser.add_argument("--table-root", type=Path)
    parser.add_argument("--game-assembly", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = build_source_gap_queue(
        args.language,
        reports_dir=args.reports_dir,
        table_root=args.table_root,
        game_assembly=args.game_assembly,
    )
    print(
        "Source-only Story gap queue: "
        f"{result.paths.markdown.resolve().relative_to(ROOT)}"
    )
    print(
        "Source-only Story gap data: "
        f"{result.paths.json.resolve().relative_to(ROOT)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
