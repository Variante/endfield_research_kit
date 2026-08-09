import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "pack_webui.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("pack_webui", SCRIPT)
pack_webui = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = pack_webui
SPEC.loader.exec_module(pack_webui)


class PackWebuiAudioTests(unittest.TestCase):
    def test_audio_package_scans_only_flac(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            export_root = Path(raw_root)
            audio_root = export_root / "structured" / "Audio" / "CN"
            audio_root.mkdir(parents=True)
            (audio_root / "old.wav").write_bytes(b"wav")
            (audio_root / "old.wem").write_bytes(b"wem")
            (audio_root / "current.flac").write_bytes(b"flac")

            files = list(pack_webui.iter_exported_audio_files(export_root))

            self.assertEqual([path.name for path in files], ["current.flac"])


if __name__ == "__main__":
    unittest.main()
