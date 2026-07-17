import argparse
import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "build_audio.py"
SPEC = importlib.util.spec_from_file_location("build_audio", SCRIPT)
build_audio = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(build_audio)


class AudioCategoryTests(unittest.TestCase):
    def test_voice_categories_keep_useful_story_detail(self) -> None:
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/story/main_episodes/line.wav"),
            ("story_voice", "main_episodes"),
        )
        self.assertEqual(
            build_audio.audio_category_for_rel("voice/characters/avywen/line.wav"),
            ("character_voice", "avywen"),
        )

    def test_event_category_handles_voice_alias(self) -> None:
        self.assertEqual(build_audio.event_audio_category("au_voice_test"), "au_vo")
        self.assertEqual(
            build_audio.audio_category_for_rel("wwise/unknown/1.wav", "au_music"),
            ("music", ""),
        )

    def test_combined_decode_retains_shared_bank_provenance(self) -> None:
        self.assertEqual(
            build_audio.combined_decode_source_block(
                "shared", "CN", "unmapped/initial/123.wav"
            ),
            "initial-audio",
        )
        self.assertEqual(
            build_audio.combined_decode_source_block("CN", "CN", "voice/line.wav"),
            "voice",
        )


class AudioDumperTests(unittest.TestCase):
    def test_all_mode_runs_once_per_vfs_source(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            executable = root / "AnimeStudio.CLI.exe"
            streaming = root / "StreamingAssets"
            persistent = root / "Persistent"
            audio_root = root / "Audio"
            executable.touch()
            streaming.mkdir()
            persistent.mkdir()
            args = argparse.Namespace(
                skip_decode=False,
                audio_dumper=executable,
                streaming_assets=streaming,
                fallback_assets=persistent,
                audio_root=audio_root,
                block="all",
                format="wav",
            )

            with mock.patch.object(build_audio.subprocess, "run") as run:
                build_audio.run_audio_dumper(args, "CN", build_audio.LANGUAGES["CN"])

            self.assertEqual(run.call_count, 1)
            for call in run.call_args_list:
                command = call.args[0]
                self.assertEqual(command[1:3], ["audio", "--streaming-assets"])
                self.assertIn("--block", command)
                self.assertEqual(command[command.index("--block") + 1], "all")
                self.assertIn("--shared-output", command)


if __name__ == "__main__":
    unittest.main()
