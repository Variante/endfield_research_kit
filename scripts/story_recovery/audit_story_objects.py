"""Build AnimeStudio Story-object evidence through one staged command."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.common import resolve_installed_game_data_root, write_report_json, write_text_if_changed  # noqa: E402
from scripts.story_builder.animestudio_story_objects import (  # noqa: E402
    CARRIER_REPORT_PATH,
    DEFAULT_ANIMESTUDIO_CLI,
    HIERARCHY_REPORT_PATH,
    REVERSE_REPORT_PATH,
    STAGES,
)
from scripts.story_builder.animestudio_story_objects import carrier, hierarchy, reverse  # noqa: E402


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=(*STAGES, "all"), default="all")
    parser.add_argument("--output-root", type=Path, default=ROOT / "export_full")
    parser.add_argument("--gap-queue", type=Path, default=carrier.DEFAULT_GAP_QUEUE)
    parser.add_argument("--story-index", type=Path, default=reverse.DEFAULT_STORY_INDEX)
    parser.add_argument("--game-root", type=Path, default=resolve_installed_game_data_root())
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument("--metadata", type=Path)
    parser.add_argument(
        "--animestudio-cli",
        type=Path,
        default=DEFAULT_ANIMESTUDIO_CLI,
    )
    parser.add_argument("--work-parent", type=Path, default=ROOT / "tmp" / "story")
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="carrier object-index source; repeat as needed",
    )
    parser.add_argument(
        "--report-root",
        type=Path,
        default=CARRIER_REPORT_PATH.parent,
    )
    return parser.parse_args(argv)


def _paths(report_root: Path, stage: str) -> tuple[Path, Path]:
    stem = {
        "carrier": CARRIER_REPORT_PATH.stem,
        "hierarchy": HIERARCHY_REPORT_PATH.stem,
        "reverse": REVERSE_REPORT_PATH.stem,
    }[stage]
    return report_root / f"{stem}.json", report_root / f"{stem}.md"


def _publish(args: argparse.Namespace, stage: str, payload: dict[str, Any], markdown: str) -> None:
    json_path, markdown_path = _paths(args.report_root, stage)
    write_report_json(json_path, payload)
    write_text_if_changed(markdown_path, markdown)
    print(f"AnimeStudio Story objects [{stage}]: {json_path.relative_to(ROOT)}")


def run_stage(args: argparse.Namespace, stage: str) -> None:
    output_root = args.output_root.resolve()
    gap_queue = args.gap_queue.resolve()
    if stage == "carrier":
        report = carrier.build_report(
            output_root,
            tuple(args.sources or carrier.DEFAULT_SOURCES),
            gap_queue,
        )
        _publish(args, stage, report, carrier.render_markdown(report))
        return
    game_root = args.game_root.resolve()
    if stage == "hierarchy":
        report = hierarchy.build_report(
            output_root=output_root,
            gap_queue=gap_queue,
            game_root=game_root,
            cli=args.animestudio_cli.resolve(),
            work_parent=args.work_parent.resolve(),
        )
        _publish(args, stage, report, hierarchy.render_markdown(report))
        return
    gameassembly = (
        args.gameassembly.resolve()
        if args.gameassembly
        else game_root.parent / "GameAssembly.dll"
    )
    metadata = (
        args.metadata.resolve()
        if args.metadata
        else game_root / "il2cpp_data" / "Metadata" / "global-metadata.dat"
    )
    report = reverse.build_report(
        output_root=output_root,
        gap_queue=gap_queue,
        story_index=args.story_index.resolve(),
        game_root=game_root,
        cli=args.animestudio_cli.resolve(),
        work_parent=args.work_parent.resolve(),
        gameassembly=gameassembly,
        metadata=metadata,
    )
    _publish(args, stage, report, reverse.render_markdown(report))


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    stages = STAGES if args.stage == "all" else (args.stage,)
    try:
        for stage in stages:
            run_stage(args, stage)
    except (carrier.AuditError, hierarchy.AuditError, reverse.AuditError) as exc:
        raise SystemExit(f"AnimeStudio Story-object audit failed at {stage}: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
