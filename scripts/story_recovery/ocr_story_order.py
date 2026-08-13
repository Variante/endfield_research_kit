r"""Maintain gameplay-video OCR Story-order evidence with one command.

Commands::

    python scripts\story_recovery\ocr_story_order.py sample [OCR options]
    python scripts\story_recovery\ocr_story_order.py match [matching options]
    python scripts\story_recovery\ocr_story_order.py publish [proposal options]
    python scripts\story_recovery\ocr_story_order.py compare [comparison options]

Use ``compare --detailed`` to rematch selected OCR reports and render the
diagnostic video/override window comparison. No command edits the active Story
order override.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Callable, Sequence


ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.story_recovery.ocr import _detailed_compare, compare, extract, match, proposal  # noqa: E402


COMMANDS: dict[str, tuple[str, Callable[[list[str] | None], int]]] = {
    "sample": ("extract/cache sampled frames and OCR observations", extract.main),
    "match": ("match completed OCR reports and build an OCR-only proposal", match.main),
    "publish": ("distill the proposal for the WebUI debug comparison", proposal.main),
    "compare": ("compare OCR-observed and active manual Story order", compare.main),
}


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(description=__doc__)
    value.add_argument("command", nargs="?", choices=COMMANDS)
    return value


def main(argv: Sequence[str] | None = None) -> int:
    values = list(sys.argv[1:] if argv is None else argv)
    if not values or values == ["--help"]:
        root = parser()
        root.print_help()
        print("\ncommands:")
        for name, (description, _handler) in COMMANDS.items():
            print(f"  {name:<8} {description}")
        return 0
    command = values.pop(0)
    if command not in COMMANDS:
        parser().error(f"unknown command {command!r}")
    if command == "compare" and "--detailed" in values:
        values.remove("--detailed")
        return _detailed_compare.main(values)
    return COMMANDS[command][1](values)


if __name__ == "__main__":
    raise SystemExit(main())
