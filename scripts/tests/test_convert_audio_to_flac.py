import importlib.util
import tempfile
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "convert_audio_to_flac.py"
SPEC = importlib.util.spec_from_file_location("convert_audio_to_flac", SCRIPT)
convert_audio = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(convert_audio)


class ConvertAudioTests(unittest.TestCase):
    def test_convert_one_writes_flac_atomically_and_removes_wav(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            source = root / "voice.wav"
            destination = root / "voice.flac"
            source.write_bytes(b"RIFF test")

            def fake_ffmpeg(command: list[str], check: bool) -> None:
                self.assertTrue(check)
                Path(command[-1]).write_bytes(b"fLaC test")

            with mock.patch.object(convert_audio.subprocess, "run", side_effect=fake_ffmpeg):
                status = convert_audio.convert_one(
                    root / "ffmpeg.exe",
                    source,
                    destination,
                    delete_source=True,
                )

            self.assertEqual(status, "converted")
            self.assertFalse(source.exists())
            self.assertEqual(destination.read_bytes(), b"fLaC test")

    def test_dry_run_does_not_require_ffmpeg_or_write_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            source = root / "voice.wav"
            source.write_bytes(b"RIFF test")
            stats = convert_audio.convert_audio_root(root, dry_run=True)
            self.assertEqual(stats["planned"], 1)
            self.assertFalse((root / "voice.flac").exists())


if __name__ == "__main__":
    unittest.main()
