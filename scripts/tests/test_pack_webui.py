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
    def test_live_router_marks_audio_debug_only_with_gameplay_fallback(self) -> None:
        project_root = SCRIPT.parents[1]
        router = (project_root / "webui" / "assets.js").read_text(encoding="utf-8")
        html = (project_root / "webui" / "index.html").read_text(encoding="utf-8")

        self.assertIn('const DEBUG_ONLY_VIEWS = new Set(["audio", "mission-pipeline"]);', router)
        self.assertIn('audio: "gameplay"', router)
        self.assertIn('id="audio-tab"', html)
        self.assertIn('data-view="audio" data-debug-view', html)
        self.assertIn('id="audio-view"', html)

    def test_packaged_router_keeps_debug_audio_and_mission_views(self) -> None:
        shim = pack_webui.ASSET_SHIM_JS

        self.assertIn('"audio"', shim)
        self.assertIn('const DEBUG_ONLY_VIEWS = new Set(["audio", "mission-pipeline"]);', shim)
        self.assertIn('audio: "gameplay"', shim)
        self.assertIn('"mission-pipeline": "gameplay"', shim)

    def test_stripping_assets_keeps_sibling_audio_view(self) -> None:
        html = """<main>
<section id="audio-view"><div id="audio-app"></div></section>
<section id="assets-view">
<div><section>nested</section></div>
</section>
<section id="updates-view"></section>
</main>"""

        stripped = pack_webui.strip_asset_view_from_index(html)

        self.assertIn('id="audio-view"', stripped)
        self.assertIn('id="updates-view"', stripped)
        self.assertNotIn('id="assets-view"', stripped)

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
