from __future__ import annotations

import importlib

from .context import OUT_DIR


def relink_existing_audio(target_languages: list[str]) -> None:
    try:
        audio_builder = importlib.import_module("build_audio")
    except ImportError as exc:
        print(f"Audio relink: skipped (failed to import scripts/build_audio.py: {exc})")
        return

    supported_languages = set(getattr(audio_builder, "LANGUAGES", {}))
    for language_code in target_languages:
        if language_code not in supported_languages:
            print(f"Audio relink [{language_code}]: skipped (language not supported by build_audio.py)")
            continue

        audio_root = OUT_DIR / "audio" / language_code
        has_decoded_audio = getattr(audio_builder, "has_decoded_audio", None)
        has_audio = (
            has_decoded_audio(audio_root)
            if callable(has_decoded_audio)
            else audio_root.exists()
        )
        if not has_audio:
            print(f"Audio relink [{language_code}]: skipped (no decoded audio files at {audio_root})")
            continue

        print(f"\nAudio relink [{language_code}]: using existing decoded audio")
        audio_args = audio_builder.parse_args(["--language", language_code, "--skip-decode"])
        audio_builder.build_audio(audio_args)
