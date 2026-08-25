import io
import re
import tempfile
import unittest
import zipfile
from contextlib import redirect_stderr
from pathlib import Path

from scripts import pack_webui

SCRIPT = Path(pack_webui.__file__).resolve()


class PackWebuiAudioTests(unittest.TestCase):
    def test_page_reference_scope_covers_normal_media_pages(self) -> None:
        page_data = {
            "data/assets/gameplay_refs.json",
            "data/assets/story_media.json",
            "data/gameplay/projectiles.json",
            "data/map_recovery/index.json",
            "data/mission_pipeline/index.json",
            "data/lang/CN/conv/example.json",
            "data/lang/CN/mission/example.json",
            "data/lang/CN/characters/index.json",
            "data/lang/CN/gameplay/index.json",
        }
        for rel in page_data:
            self.assertTrue(pack_webui.is_page_reference_path(rel), rel)
        for rel in ("data/audio/index.json", "data/assets/index.json", "data/updates/latest.json"):
            self.assertFalse(pack_webui.is_page_reference_path(rel), rel)

    def test_page_local_media_scope_owns_map_character_and_gameplay_files(self) -> None:
        companion = {
            "src/features/map_recovery/index.js",
            "data/map_recovery/index.json",
            "src/features/characters/index.js",
            "data/lang/CN/characters/index.json",
            "src/features/gameplay/index.js",
            "data/lang/CN/gameplay/index.json",
            "data/gameplay/projectiles.json",
            "data/assets/gameplay_refs.json",
        }
        for rel in companion:
            self.assertTrue(pack_webui.is_companion_feature_path(rel), rel)
        for rel in ("app.js", "data/lang/CN/index.json", "src/features/audio/index.js"):
            self.assertFalse(pack_webui.is_companion_feature_path(rel), rel)

    def test_collect_page_media_references_accepts_only_known_exact_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            payload_path = root / "page.json"
            payload_path.write_text(
                '{"image":"StreamingAssets/Texture2D/used.png",'
                '"audio":"../../export_full/structured/Audio/CN/used.flac",'
                '"unknown":"StreamingAssets/Texture2D/not-indexed.png"}',
                encoding="utf-8",
            )

            assets, audio = pack_webui.collect_page_media_references(
                [payload_path],
                known_asset_rels={"StreamingAssets/Texture2D/used.png"},
                known_audio_rels={"structured/Audio/CN/used.flac"},
            )

            self.assertEqual(assets, {"StreamingAssets/Texture2D/used.png"})
            self.assertEqual(audio, {"structured/Audio/CN/used.flac"})

    def test_merged_media_index_excludes_models_and_deduplicates_media(self) -> None:
        full = {
            "root": "export_full",
            "sourceRoots": {"StreamingAssets": "source-a"},
            "entries": [
                {"r": "StreamingAssets/Texture2D/a.png", "k": "image"},
                {"r": "StreamingAssets/Mesh/a.obj", "k": "model"},
            ],
        }
        story = {
            "sourceRoots": {"Persistent": "source-b"},
            "entries": [
                {"r": "StreamingAssets/Texture2D/a.png", "k": "image", "label": "story"},
                {"r": "Persistent/Video/b.mp4", "k": "video"},
            ],
        }

        merged = pack_webui.merged_media_asset_payload(full, story)

        self.assertEqual(
            [entry["r"] for entry in merged["entries"]],
            ["Persistent/Video/b.mp4", "StreamingAssets/Texture2D/a.png"],
        )
        self.assertEqual(merged["counts"]["model"], 0)
        self.assertEqual(merged["sourceRoots"], {"Persistent": "source-b", "StreamingAssets": "source-a"})

    def test_chinese_usage_note_describes_all_three_packages(self) -> None:
        note = pack_webui.CHINESE_USAGE_README
        self.assertIn("主程序包", note)
        self.assertIn("常用图片和视频包", note)
        self.assertIn("常用语音包", note)
        self.assertIn("可选完整资源包", note)
        self.assertIn("主程序包 → 常用图片和视频包 → 常用语音包 → 可选完整资源包", note)

    def test_all_companion_zips_include_readable_chinese_usage_notes(self) -> None:
        empty_plan = pack_webui.PackagePlan(
            curated_asset_payload={"entries": []},
            complete_asset_payload={"entries": []},
            curated_images=[],
            curated_videos=[],
            resource_assets=[],
            curated_audio_files=[],
            resource_audio_files=[],
            audio_indexes=[],
        )
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            audio_index_source = root / "source-audio-index.json"
            audio_index_source.write_text('{"entries":[]}', encoding="utf-8")
            model_source = root / "mesh.obj"
            model_source.write_text("v 0 0 0\n", encoding="utf-8")
            empty_plan.complete_asset_payload = {
                "entries": [{"r": "StreamingAssets/Mesh/mesh.obj", "k": "model"}]
            }
            resource_asset = pack_webui.ExportedImage(
                rel="StreamingAssets/Mesh/mesh.obj",
                source_path=model_source,
                archive_path="export_full/StreamingAssets/Mesh/mesh.obj",
            )
            empty_plan.audio_indexes = [
                pack_webui.ExportedImage(
                    rel="structured/Audio/CN/index.json",
                    source_path=audio_index_source,
                    archive_path="export_full/structured/Audio/CN/index.json",
                )
            ]
            media_zip = root / "media.zip"
            audio_zip = root / "audio.zip"
            resources_zip = root / "resources.zip"
            pack_webui._write_media_package(
                media_zip,
                webui_root=root,
                plan=empty_plan,
                page_local_media_files=[],
                curated_images=[],
                curated_videos=[],
            )
            pack_webui._write_page_audio_package(audio_zip, curated_audio=[])
            pack_webui._write_resources_package(
                resources_zip,
                webui_root=root,
                plan=empty_plan,
                resource_data_files=[],
                resource_assets=[resource_asset],
                resource_audio=[],
            )

            for output in (media_zip, audio_zip, resources_zip):
                with zipfile.ZipFile(output) as zipf:
                    note = zipf.read("README-中文说明.txt").decode("utf-8")
                    self.assertIn("推荐解压顺序", note)
            with zipfile.ZipFile(resources_zip) as zipf:
                self.assertEqual(
                    zipf.read("export_full/structured/Audio/CN/index.json"),
                    b'{"entries":[]}',
                )
                self.assertEqual(
                    zipf.read("export_full/StreamingAssets/Mesh/mesh.obj"),
                    model_source.read_bytes(),
                )

    def test_default_package_selection_builds_all_four(self) -> None:
        self.assertEqual(
            pack_webui.parse_args([]).packages,
            ("story", "media", "audio", "resource"),
        )

    def test_package_selection_preserves_requested_order(self) -> None:
        self.assertEqual(
            pack_webui.parse_args(["story,audio,media,resource"]).packages,
            ("story", "audio", "media", "resource"),
        )
        self.assertEqual(pack_webui.parse_args(["resource"]).packages, ("resource",))

    def test_invalid_and_duplicate_package_selections_are_rejected(self) -> None:
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pack_webui.parse_args(["story,story"])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            pack_webui.parse_args(["assets"])

    def test_staged_package_failure_preserves_published_file(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            output = root / "story.zip"
            output.write_bytes(b"published")

            with self.assertRaisesRegex(RuntimeError, "fixture failure"):
                with pack_webui.staged_package_output(output) as staged:
                    staged.write_bytes(b"replacement")
                    raise RuntimeError("fixture failure")

            self.assertEqual(output.read_bytes(), b"published")
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_staged_package_replaces_output_after_success(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            output = root / "story.zip"
            output.write_bytes(b"published")

            with pack_webui.staged_package_output(output) as staged:
                staged.write_bytes(b"replacement")

            self.assertEqual(output.read_bytes(), b"replacement")
            self.assertEqual(list(root.glob("*.tmp")), [])

    def test_live_router_keeps_audio_normal_and_debug_mission_views(self) -> None:
        project_root = SCRIPT.parents[1]
        router = (project_root / "webui" / "assets.js").read_text(encoding="utf-8")
        html = (project_root / "webui" / "index.html").read_text(encoding="utf-8")

        # Mission Pipeline remains debug-only, while Audio and Map are
        # normal views that must stay directly addressable with debug disabled.
        debug_only = re.search(r"const DEBUG_ONLY_VIEWS = new Set\(\[(.*?)\]\);", router)
        self.assertIsNotNone(debug_only)
        self.assertIn('"mission-pipeline"', debug_only.group(1))
        self.assertNotIn('"audio"', debug_only.group(1))
        self.assertNotIn('"map-recovery"', debug_only.group(1))
        self.assertIn('audio: "gameplay"', router)
        self.assertIn('id="audio-tab"', html)
        self.assertIn('data-view="audio" data-i18n="audioTab"', html)
        self.assertIn('id="audio-view"', html)

        story_tab = html.index('id="story-tab"')
        map_tab = html.index('id="map-recovery-tab"')
        characters_tab = html.index('id="characters-tab"')
        self.assertLess(story_tab, map_tab)
        self.assertLess(map_tab, characters_tab)
        map_button = re.search(r'<button id="map-recovery-tab"[^>]*>', html)
        self.assertIsNotNone(map_button)
        self.assertNotIn("data-debug-view", map_button.group(0))

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

    def test_already_compressed_media_is_stored_without_recompression(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            source = root / "voice.flac"
            output = root / "media.zip"
            source.write_bytes(b"already-compressed-fixture")
            with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zipf:
                pack_webui.zip_write_file(zipf, set(), source, "voice.flac")

            with zipfile.ZipFile(output) as zipf:
                self.assertEqual(zipf.getinfo("voice.flac").compress_type, zipfile.ZIP_STORED)

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
        self.assertIn("[1, 2, 3, 4, 5, 6, 7, 8, 9, 10].includes(payload.schemaVersion)", source)
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
