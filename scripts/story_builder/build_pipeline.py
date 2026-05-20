from __future__ import annotations

import shutil
import time

from .audio_relink import relink_existing_audio
from .build_args import parse_args
from .bundle_support import discover_languages, language_info, normalize_language_selection
from .context import DEFAULT_LANGUAGE, LANG_DIR, OUT_DIR, write_json
from .language_bundle import build_language_bundle
from .timeline_orders import recover_timeline_orders_for_build


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
        (OUT_DIR / stale_file).unlink(missing_ok=True)

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

    write_json(
        OUT_DIR / "manifest.json",
        {
            "generated": int(time.time()),
            "defaultLanguage": default_language,
            "profile": args.profile,
            "reference": not args.skip_reference,
            "languages": [language_info(code) for code in target_languages],
            "stats": stats,
        },
        indent=2,
        compact=False,
    )

    print("\nManifest written to", OUT_DIR / "manifest.json")
    if args.skip_audio_link:
        print("Audio relink: skipped by --skip-audio-link")
    else:
        relink_existing_audio(target_languages)
