#!/usr/bin/env python3
"""Run maintained native carrier audits through one profile-based CLI."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_recovery.native_carriers import cinematic_queue, radio_forbid, scanner


ProfileRunner = Callable[[argparse.Namespace], int]
PROFILES = {
    "generic": (scanner, "Scan an installed managed value carrier."),
    "cinematic": (cinematic_queue, "Recover the cinematic queue carrier contract."),
    "radio-forbid": (radio_forbid, "Validate the retained radio-forbid negative boundary."),
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="profile", required=True)
    for name, (module, help_text) in PROFILES.items():
        profile = subparsers.add_parser(name, help=help_text, description=help_text)
        module.add_arguments(profile)
        profile.set_defaults(run_profile=module.run)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_profile: ProfileRunner = args.run_profile
    return int(run_profile(args) or 0)


if __name__ == "__main__":
    raise SystemExit(main())
