from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    webui_script_dir = Path(__file__).resolve().parents[1]
    if str(webui_script_dir) not in sys.path:
        sys.path.insert(0, str(webui_script_dir))
    from story_builder.bundle_support import (
        discover_languages,
        language_info,
        normalize_language_selection,
    )
    from story_builder.context import (
        BUILD_PROFILES,
        DEFAULT_BUILD_PROFILE,
        DEFAULT_LANGUAGE,
        LANG_DIR,
        OUT_DIR,
        write_json,
    )
    from story_builder.language_bundle import (
        build_language_bundle,
        load_reused_reference_stats,
    )
    from story_builder.timeline_action_evidence import build_timeline_action_evidence_for_build
    from story_builder.timeline_recovery import (
        TIMELINE_RECOVERY_MODES,
        ensure_timeline_orders_current,
    )
else:
    from .bundle_support import discover_languages, language_info, normalize_language_selection
    from .context import (
        BUILD_PROFILES,
        DEFAULT_BUILD_PROFILE,
        DEFAULT_LANGUAGE,
        LANG_DIR,
        OUT_DIR,
        write_json,
    )
    from .language_bundle import build_language_bundle, load_reused_reference_stats
    from .timeline_action_evidence import build_timeline_action_evidence_for_build
    from .timeline_recovery import TIMELINE_RECOVERY_MODES, ensure_timeline_orders_current


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
            "writes them to reference/. `full` includes those legacy collections."
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
            "instead of rebuilding it. Use only when exported Table inputs are unchanged."
        ),
    )
    parser.add_argument(
        "--timeline-recovery",
        choices=TIMELINE_RECOVERY_MODES,
        default="auto",
        help=(
            "`auto` refreshes missing or stale Timeline line order; `always` also "
            "makes recovery failures fatal; `never` skips recovery."
        ),
    )
    parser.add_argument(
        "--force-timeline-recovery",
        action="store_true",
        help="Re-extract Timeline assets even when the recovered line-order index is current.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    ensure_timeline_orders_current(args.timeline_recovery, args.force_timeline_recovery)
    build_timeline_action_evidence_for_build()

    available_languages = discover_languages()
    if not available_languages:
        raise SystemExit(
            "No I18nTextTable_*.json files found in export_full/structured/StreamingAssets/Table "
            "from the current WebUI export."
        )

    target_languages = normalize_language_selection(args.languages, available_languages)
    default_language = args.default_language.strip().upper() if args.default_language else DEFAULT_LANGUAGE
    if default_language not in target_languages:
        raise SystemExit(
            f"Default language {default_language!r} is not in the selected build set: "
            + ", ".join(target_languages)
        )

    if args.reuse_reference:
        for language_code in target_languages:
            load_reused_reference_stats(
                LANG_DIR / language_code / "reference",
                language_code,
            )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LANG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(OUT_DIR / "conv", ignore_errors=True)
    for stale_file in ("manifest.json", "index.json", "actors.json"):
        (OUT_DIR / stale_file).unlink(missing_ok=True)

    print("Building localized web UI bundles...")
    print("Languages:", ", ".join(target_languages))
    print("Default language:", default_language)
    print("Profile:", args.profile)
    if args.skip_reference:
        print("Reference bundle: disabled")
    elif args.reuse_reference:
        print("Reference bundle: reusing validated generated data")

    stats = [
        build_language_bundle(
            language_code,
            LANG_DIR / language_code,
            profile=args.profile,
            write_reference=not args.skip_reference,
            reuse_reference=args.reuse_reference,
        )
        for language_code in target_languages
    ]

    for language_dir in LANG_DIR.iterdir():
        if language_dir.is_dir() and language_dir.name not in target_languages:
            shutil.rmtree(language_dir, ignore_errors=True)

    write_json(
        OUT_DIR / "manifest.json",
        {
            "generated": int(time.time()),
            "defaultLanguage": default_language,
            "profile": args.profile,
            "reference": not args.skip_reference,
            "referenceReused": bool(args.reuse_reference),
            "languages": [language_info(code) for code in target_languages],
            "stats": stats,
        },
        indent=2,
        compact=False,
    )

    print("\nManifest written to", OUT_DIR / "manifest.json")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(1)
