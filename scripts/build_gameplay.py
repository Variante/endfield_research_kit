"""Build the behavior datasets behind the Gameplay WebUI page.

The page reads these four behavior/asset payloads plus the language-specific
``projectile_audio.json`` sidecar owned by ``build_audio.py``. The Gameplay
builders still run as separate stages because the export pipeline
schedules them in different dependency phases -- projectiles and the base index
need nothing, the asset sidecar needs a current Assets index, and combat
relationships need the source graph -- but the page now has one command:

    python scripts/build_gameplay.py                    # every stage
    python scripts/build_gameplay.py --stage projectiles

Behavior stage implementations live in ``scripts/gameplay_builder/``. The
asset-ref stage calls ``asset_builder.gameplay_refs`` directly so this command
remains the sole owner of its consumer-specific sidecar.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent

ROOT = SCRIPT_DIR.parent
WEBUI_DATA_ROOT = ROOT / "webui" / "data"

STAGES = ("base", "projectiles", "asset-refs", "combat")

STAGE_HELP = {
    "base": "Gameplay base index (data/lang/<LANG>/gameplay/index.json).",
    "projectiles": "Exact projectile behavior and event hashes (data/gameplay/projectiles.json).",
    "asset-refs": "Compact Gameplay-to-Assets sidecar; needs a current Assets index.",
    "combat": "Debug-only combat relationships; needs a current source graph.",
}


def build_asset_refs_stage(
    language: str,
    *,
    data_root: Path = WEBUI_DATA_ROOT,
) -> int:
    """Build the Gameplay-owned asset sidecar from explicit current inputs."""

    from asset_builder.gameplay_refs import build_from_paths

    language = str(language or "CN").upper()
    gameplay_path = data_root / "lang" / language / "gameplay" / "index.json"
    asset_index_path = data_root / "assets" / "index.json"
    output_path = data_root / "assets" / "gameplay_refs.json"
    missing = next(
        (path for path in (gameplay_path, asset_index_path) if not path.is_file()),
        None,
    )
    if missing is not None:
        print(f"{language}: Gameplay asset refs skipped (missing {missing})")
        return 0
    payload = build_from_paths(gameplay_path, asset_index_path, output_path)
    counts = payload.get("counts") or {}
    display = output_path.relative_to(ROOT) if output_path.is_relative_to(ROOT) else output_path
    print(
        f"{language}: {counts.get('matchedEntries', 0)} matched Gameplay entries; "
        f"{counts.get('withImages', 0)} with images; "
        f"{counts.get('withModels', 0)} with models -> {display}"
    )
    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--stage",
        action="append",
        choices=STAGES,
        help=(
            "Run only this stage; repeatable. Default runs every stage in "
            "dependency order. "
            + " ".join(f"`{name}`: {text}" for name, text in STAGE_HELP.items())
        ),
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["CN"],
        help="Languages for the localized stages (default: CN).",
    )
    parser.add_argument(
        "--default-language",
        default="CN",
        help="Default language for the localized stages (default: CN).",
    )
    return parser.parse_args(argv)


def run_stage(stage: str, args: argparse.Namespace) -> int:
    """Run one stage in-process and return its exit code."""
    languages = list(args.languages)
    if stage == "base":
        from gameplay_builder import base_data

        return int(
            base_data.main(
                [
                    "--languages",
                    *languages,
                    "--default-language",
                    args.default_language,
                ]
            )
            or 0
        )
    if stage == "projectiles":
        from gameplay_builder import projectiles

        return int(projectiles.main([]) or 0)
    if stage == "asset-refs":
        return build_asset_refs_stage(args.default_language)
    if stage == "combat":
        from gameplay_builder import combat_relationships

        return int(combat_relationships.main([]) or 0)
    raise ValueError(f"unknown gameplay stage: {stage}")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    # Preserve dependency order regardless of the order flags were given.
    selected = [stage for stage in STAGES if not args.stage or stage in args.stage]
    for stage in selected:
        print(f"[gameplay] stage {stage}", flush=True)
        returncode = run_stage(stage, args)
        if returncode:
            print(
                f"[gameplay] stage {stage} failed with {returncode}",
                file=sys.stderr,
                flush=True,
            )
            return returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
