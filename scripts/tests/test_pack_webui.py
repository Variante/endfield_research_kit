import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "pack_webui.py"
sys.path.insert(0, str(SCRIPT.parent))
SPEC = importlib.util.spec_from_file_location("pack_webui", SCRIPT)
pack_webui = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = pack_webui
SPEC.loader.exec_module(pack_webui)


class PackWebuiAudioTests(unittest.TestCase):
    def test_single_value_audio_format_flag_is_removed(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pack_webui.parse_args(["--audio-format", "flac"])

    def test_staged_package_failure_preserves_published_files(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            outputs = [root / "story.zip", root / "assets.zip"]
            for output in outputs:
                output.write_bytes(b"published")

            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                with pack_webui.staged_package_outputs(outputs) as staged:
                    for path in staged.values():
                        path.write_bytes(b"replacement")
                    raise RuntimeError("fixture failure")

            self.assertEqual([path.read_bytes() for path in outputs], [b"published"] * 2)
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_staged_packages_replace_outputs_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            outputs = [root / "story.zip", root / "assets.zip"]
            for output in outputs:
                output.write_bytes(b"published")

            with pack_webui.staged_package_outputs(outputs) as staged:
                for path in staged.values():
                    path.write_bytes(b"replacement")

            self.assertEqual([path.read_bytes() for path in outputs], [b"replacement"] * 2)
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_live_router_keeps_audio_normal_and_debug_mission_views(self) -> None:
        project_root = SCRIPT.parents[1]
        router = (project_root / "webui" / "assets.js").read_text(encoding="utf-8")
        html = (project_root / "webui" / "index.html").read_text(encoding="utf-8")

        self.assertIn('const DEBUG_ONLY_VIEWS = new Set(["mission-pipeline"]);', router)
        self.assertIn('audio: "gameplay"', router)
        self.assertIn('id="audio-tab"', html)
        self.assertIn('data-view="audio" data-i18n="audioTab"', html)
        self.assertIn('id="audio-view"', html)

    def test_packaged_router_keeps_audio_and_debug_mission_views(self) -> None:
        shim = pack_webui.ASSET_SHIM_JS

        self.assertIn('"audio"', shim)
        self.assertIn('const DEBUG_ONLY_VIEWS = new Set(["mission-pipeline"]);', shim)
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

    def test_gameplay_exact_skill_audio_is_inline_and_other_audio_trails(self) -> None:
        project_root = SCRIPT.parents[1]
        source = (project_root / "webui" / "src" / "features" / "gameplay" / "index.js").read_text(encoding="utf-8")
        skill_row = source[source.index("function renderActiveSkillRow"):source.index("function renderWeaponDetail")]
        character_detail = source[source.index("function renderCharacterDetail"):source.index("function renderEquipmentSuit")]
        detail_renderer = source[source.index("function renderDetail(entry)"):source.index("function renderListNote")]

        self.assertIn("renderActiveSkillSoundEffects(group, character)", skill_row)
        self.assertIn(".filter(gameplaySoundHasExactSkillTrigger)", source)
        self.assertIn(".filter((event) => !gameplaySoundHasExactSkillTrigger(event))", source)
        self.assertIn('buffPlaySoundAction: "soundTriggerPlaySoundAction"', source)
        self.assertIn('text("soundPlaySoundFrame")', source)
        self.assertIn('event?.actionDispatchEvidence || []', source)
        self.assertIn('soundDispatchNoExplicitDelay', source)
        self.assertIn('soundActionProbability', source)
        # All recovered candidates are listed together; there is no hidden
        # candidate selector/player layer on the Gameplay page.
        self.assertIn('<audio controls preload="none" src="${escapeHtml(candidate.src)}"', source)
        self.assertNotIn('[data-gameplay-sfx-src]:not([data-gameplay-sfx-bound])', source)
        self.assertNotIn('data-gameplay-sfx-player', source)
        self.assertIn("[1, 2, 3, 4].includes(payload.schemaVersion)", source)
        self.assertNotIn('section(text("characterActionAudio")', character_detail)
        self.assertIn('entry.kind === "character"', detail_renderer)
        self.assertIn('section(text("relatedSoundEffects"), renderCharacterSoundEffects', detail_renderer)
        self.assertGreater(detail_renderer.index("trailingAudio"), detail_renderer.index("renderIntegratedSections"))

    def test_audio_page_surfaces_typed_music_branch_evidence(self) -> None:
        project_root = SCRIPT.parents[1]
        source = (project_root / "webui" / "src" / "features" / "audio" / "index.js").read_text(encoding="utf-8")

        self.assertIn('musicSwitchCandidate: "relationMusicSwitch"', source)
        self.assertIn('musicPlaylistCandidate: "relationMusicPlaylist"', source)
        self.assertIn('musicTrackSource: "relationMusicSource"', source)
        self.assertIn('asArray(evidence?.musicNodeEvidence)', source)
        self.assertIn('asArray(node?.selectionTypeLabels)', source)
        self.assertIn('evidence?.actionDispatchEvidence', source)
        self.assertIn('coDispatchWithAuthoredDelayDifference', (project_root / "scripts" / "build_audio.py").read_text(encoding="utf-8"))
        self.assertIn('action?.probability?.baseValuesPercent', source)

    def test_audio_page_labels_single_complete_topology_leaf(self) -> None:
        project_root = SCRIPT.parents[1]
        source = (project_root / "webui" / "src" / "features" / "audio" / "index.js").read_text(encoding="utf-8")
        self.assertIn('relationSingleTopology:', source)
        self.assertIn('singleTopology: "relationSingleTopology"', source)
        self.assertIn('record?.traversalStatus === "complete"', source)
        self.assertIn('Number(record?.unresolvedNodeCount || 0) === 0', source)


if __name__ == "__main__":
    unittest.main()
