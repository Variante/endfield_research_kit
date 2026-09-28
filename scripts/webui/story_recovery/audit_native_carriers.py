#!/usr/bin/env python3
"""Run maintained native carrier audits through one profile-based CLI.

Profiles: ``generic`` is the importable type/field-driven scanner
(``--carrier-type TYPE --focus-field FIELD``); ``cinematic`` retains the
structural queue contract and its report paths and reconciles the full native
audit against the compact ``contracts/cinematic_queue.json`` that production
reads (``--write-contract`` regenerates that contract from a validating audit
after a client update, ``--skip-contract-reconciliation`` only writes the
audit); ``radio-forbid`` validates the small versioned negative boundary
recorded for the pinned build. Reusable scanner and profile code lives in
``native_carriers/``. The full audit is never a production input.
"""
from __future__ import annotations

import argparse
from collections.abc import Callable

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this maintained entry point as: "
        "python -m scripts.webui.story_recovery.audit_native_carriers"
    )

from scripts.webui.story_recovery.native_carriers import cinematic_queue, radio_forbid, scanner


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
