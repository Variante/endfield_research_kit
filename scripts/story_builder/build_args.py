from __future__ import annotations

import argparse

from .context import (
    BUILD_PROFILES,
    DEFAULT_BUILD_PROFILE,
    DEFAULT_LANGUAGE,
    TIMELINE_RECOVERY_MODES,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build localized webui data bundles from exported tables."
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        help=(
            "Language codes to build. Accepts space- or comma-separated values. "
            f"Defaults to {DEFAULT_LANGUAGE} only."
        ),
    )
    parser.add_argument(
        "--default-language",
        default=DEFAULT_LANGUAGE,
        help=f"Default language for the web UI manifest (default: {DEFAULT_LANGUAGE}).",
    )
    parser.add_argument(
        "--profile",
        choices=BUILD_PROFILES,
        default=DEFAULT_BUILD_PROFILE,
        help=(
            "`lean` keeps generic table translations out of the story index and "
            "writes them to reference/ instead. `full` preserves the older "
            "story-index collection pages."
        ),
    )
    reference_group = parser.add_mutually_exclusive_group()
    reference_group.add_argument(
        "--skip-reference",
        action="store_true",
        help="Do not write the raw localized table reference bundle.",
    )
    reference_group.add_argument(
        "--reuse-reference",
        action="store_true",
        help=(
            "Preserve and validate the current localized table reference bundle "
            "instead of rebuilding it. Use only when the exported Table inputs "
            "have not changed."
        ),
    )
    parser.add_argument(
        "--timeline-recovery",
        choices=TIMELINE_RECOVERY_MODES,
        default="auto",
        help=(
            "`auto` runs Timeline line-order recovery only when the recovered "
            "index is missing or stale; `always` treats recovery failures as "
            "fatal; `never` skips the recovery step."
        ),
    )
    parser.add_argument(
        "--force-timeline-recovery",
        action="store_true",
        help="Re-extract Timeline assets even if the recovered line-order index is current.",
    )
    parser.add_argument(
        "--skip-audio-link",
        action="store_true",
        help=(
            "Do not relink existing decoded WebUI audio after building story data. "
            "By default, build.py runs build_audio.py --skip-decode for languages "
            "that already have decoded audio under export_full/structured/Audio/."
        ),
    )
    return parser.parse_args(argv)
