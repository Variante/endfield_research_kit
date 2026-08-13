r"""Capture or import hash-locked runtime evidence.

Examples from the repository root::

    tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile mission
    tools\frida-runtime\venv\Scripts\python.exe -m scripts.story_recovery.runtime_trace capture --profile audio
    python -m scripts.story_recovery.runtime_trace import --profile mission capture.jsonl
    python -m scripts.story_recovery.runtime_trace import --profile audio capture.jsonl

Mission and audio keep separate hook manifests, agents, event schemas, and
evidence policies. This file is the only command-line entry point; profile
modules contain adapters and the shared core owns process/hash/JSONL safety.
"""
from __future__ import annotations

import argparse
import sys
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.story_recovery.runtime_trace"
    )

from . import runtime_trace_audio_capture as audio_capture
from . import runtime_trace_audio_import as audio_import
from . import runtime_trace_mission_capture as mission_capture
from . import runtime_trace_mission_import as mission_import


PROFILES = ("mission", "audio")
ACTIONS = ("capture", "import")


def _selected_profile(argv: Sequence[str]) -> str | None:
    for index, value in enumerate(argv):
        if value.startswith("--profile="):
            return value.partition("=")[2]
        if value == "--profile" and index + 1 < len(argv):
            return argv[index + 1]
    return None


def root_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", nargs="?", choices=ACTIONS)
    parser.add_argument("--profile", choices=PROFILES)
    return parser


def command_parser(action: str, profile: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"{action.title()} the {profile} runtime trace profile.",
        usage=f"%(prog)s {action} --profile {profile} [options]",
    )
    parser.add_argument("action", choices=[action])
    parser.add_argument("--profile", required=True, choices=[profile])
    adapter = {
        ("capture", "mission"): mission_capture,
        ("capture", "audio"): audio_capture,
        ("import", "mission"): mission_import,
        ("import", "audio"): audio_import,
    }[(action, profile)]
    adapter.add_arguments(parser)
    return parser


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values or values == ["--help"]:
        root_parser().print_help()
        raise SystemExit(0)
    action = values[0]
    if action not in ACTIONS:
        root_parser().error(f"action must be one of: {', '.join(ACTIONS)}")
    profile = _selected_profile(values)
    if profile is None:
        root_parser().error(f"{action} requires --profile mission|audio")
    if profile not in PROFILES:
        root_parser().error(f"unknown profile {profile!r}; choose mission or audio")
    return command_parser(action, profile).parse_args(values)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.action == "capture":
        return {
            "mission": mission_capture.capture,
            "audio": audio_capture.capture,
        }[args.profile](args)
    try:
        return {
            "mission": mission_import.import_trace,
            "audio": audio_import.import_trace,
        }[args.profile](args)
    except (
        mission_import.TraceValidationError,
        audio_import.AudioTraceValidationError,
        FileNotFoundError,
        OSError,
    ) as exc:
        print(f"{args.profile.title()} runtime trace import failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
