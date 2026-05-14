from __future__ import annotations

from .context import *
from .bundle_support import *
from .language_bundle import build_language_bundle

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
    parser.add_argument(
        "--skip-reference",
        action="store_true",
        help="Do not write the raw localized table reference bundle.",
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
    return parser.parse_args(argv)

def recover_timeline_orders_for_build(mode: str, force: bool = False) -> None:
    global _DIALOG_TIMELINE_LINE_ORDER_CACHE, _TIMELINE_TO_DIALOG_KEYS_CACHE
    if mode == "never":
        print("Timeline line-order recovery: skipped")
        return

    maps = discover_timeline_asset_maps(EXPORT_ROOT)
    order_out = timeline_recovery_order_out(EXPORT_ROOT)
    if not force and timeline_order_is_current(order_out, maps):
        print(f"Timeline line-order recovery: using {order_out}")
        return

    if mode == "auto" and not maps:
        print("Timeline line-order recovery: skipped (no AnimeStudio CLI AssetMaps found)")
        return

    print("Timeline line-order recovery: extracting and parsing Timeline assets...")
    try:
        recover_timeline_line_orders(
            TimelineRecoveryConfig(
                export_root=EXPORT_ROOT,
                maps=maps,
                order_out=order_out,
            )
        )
    except Exception as exc:
        if mode == "always":
            raise
        print(f"Timeline line-order recovery: skipped ({exc})")
        return

    from . import dialog_tree as _dialog_tree

    _dialog_tree._DIALOG_TIMELINE_LINE_ORDER_CACHE = None
    _dialog_tree._TIMELINE_TO_DIALOG_KEYS_CACHE = None


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    recover_timeline_orders_for_build(args.timeline_recovery, args.force_timeline_recovery)

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

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    LANG_DIR.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(OUT_DIR / "conv", ignore_errors=True)
    for stale_file in ("manifest.json", "index.json", "actors.json"):
        stale_path = OUT_DIR / stale_file
        if stale_path.exists():
            stale_path.unlink()

    print("Building localized web UI bundles...")
    print("Languages:", ", ".join(target_languages))
    print("Default language:", default_language)
    print("Profile:", args.profile)
    if args.skip_reference:
        print("Reference bundle: disabled")

    stats: list[dict] = []
    for language_code in target_languages:
        stats.append(
            build_language_bundle(
                language_code,
                LANG_DIR / language_code,
                profile=args.profile,
                write_reference=not args.skip_reference,
            )
        )
    for language_dir in LANG_DIR.iterdir():
        if language_dir.is_dir() and language_dir.name not in target_languages:
            shutil.rmtree(language_dir, ignore_errors=True)

    manifest = {
        "generated": int(time.time()),
        "defaultLanguage": default_language,
        "profile": args.profile,
        "reference": not args.skip_reference,
        "languages": [language_info(code) for code in target_languages],
        "stats": stats,
    }
    write_json(OUT_DIR / "manifest.json", manifest, indent=2, compact=False)

    print("\nManifest written to", OUT_DIR / "manifest.json")


__all__ = [name for name in globals() if not name.startswith("__")]
