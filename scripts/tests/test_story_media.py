import unittest
from pathlib import Path

from scripts.asset_builder import story_media

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class StoryMediaTests(unittest.TestCase):
    def test_frontend_promotes_cg_assets_to_exact_story_file_rows(self) -> None:
        project_root = PROJECT_ROOT
        app = (project_root / "webui" / "app.js").read_text(encoding="utf-8")
        labels = (project_root / "webui" / "app_labels.js").read_text(encoding="utf-8")

        self.assertIn("function storyFileImageAssetDescriptor(raw)", app)
        self.assertIn("function cgStoryFileDescriptor(assets)", app)
        self.assertIn('primary.family === "remotecomm_image_" ? "remotecomm" : "cg"', app)
        self.assertIn("imageVariants: variants", app)
        self.assertIn("if (ids.length) return ids;", app)
        self.assertIn("neutralVariant && variants.m && !variants.f", app)
        self.assertIn("ln.text || lineMediaIds(ln).length", app)
        self.assertIn("rememberBestInlineImageAsset(byStem, stemInfo.rawStem, candidate)", app)
        self.assertIn('cg: { name: "CG Image"', labels)
        self.assertIn('cg: { name: "\\u5267\\u60c5CG"', labels)
        tree = (project_root / "webui" / "app_tree.js").read_text(encoding="utf-8")
        self.assertIn('kindKeys.splice(kindKeys.indexOf("video") + 1, 0, "cg")', tree)

    def test_collects_all_cg_image_files_and_preserves_path_ids(self) -> None:
        entries = [
            {"k": "image", "r": "StreamingAssets/Sprite/cg_image_scene_1_pABC1234567890DEF.png", "pid": "ABC1234567890DEF"},
            {"k": "image", "r": "StreamingAssets/Sprite/cg_image_scene_2_f_pDEF4567890ABC123.png", "pid": "DEF4567890ABC123"},
            {"k": "image", "r": "StreamingAssets/Sprite/cg_image_scene_2_m_p789ABC1234567890.png", "pid": "789ABC1234567890"},
            {"k": "image", "r": "StreamingAssets/Sprite/sns_image_scene_1.png"},
            {"k": "model", "r": "StreamingAssets/Mesh/cg_image_scene_3.obj"},
        ]

        selected = story_media.collect_story_file_images(entries)

        self.assertEqual(
            sorted(selected),
            [
                "StreamingAssets/Sprite/cg_image_scene_1_pABC1234567890DEF.png",
                "StreamingAssets/Sprite/cg_image_scene_2_f_pDEF4567890ABC123.png",
                "StreamingAssets/Sprite/cg_image_scene_2_m_p789ABC1234567890.png",
            ],
        )
        self.assertEqual(
            selected["StreamingAssets/Sprite/cg_image_scene_1_pABC1234567890DEF.png"]["pid"],
            "ABC1234567890DEF",
        )

    def test_prefers_sprite_over_identical_texture2d_wrapper(self) -> None:
        entries = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/cg_image_scene_1_p1111111111111111.png",
                "h": "same-content",
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/cg_image_scene_1_p2222222222222222.png",
                "h": "same-content",
            },
        ]

        selected = story_media.collect_story_file_images(entries)

        self.assertEqual(
            list(selected),
            ["StreamingAssets/Sprite/cg_image_scene_1_p2222222222222222.png"],
        )

    def test_imports_biglogo_and_remotecomm_but_excludes_wrong_e2m6_cg(self) -> None:
        entries = [
            {"k": "image", "r": "StreamingAssets/Sprite/cg_image_e2m6_1_m_p1111111111111111.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/dlg_biglogo_e2m6_14_f_p2222222222222222.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/dlg_biglogo_e2m6_14_m_p3333333333333333.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/remotecomm_image_e2m6_1_p4444444444444444.png"},
        ]

        selected = story_media.collect_story_file_images(entries)
        stems = {story_media.media_resolver.media_lookup_stem(rel)[0] for rel in selected}

        self.assertNotIn("cg_image_e2m6_1_m", stems)
        self.assertEqual(
            stems,
            {
                "dlg_biglogo_e2m6_14_f",
                "dlg_biglogo_e2m6_14_m",
                "remotecomm_image_e2m6_1",
            },
        )

    def test_story_payload_deduplicates_cg_selected_by_a_reference(self) -> None:
        asset = {
            "generated": 1,
            "root": "export_full",
            "sourceRoots": {"StreamingAssets": "export_full/recovered"},
            "entries": [
                {"k": "image", "r": "StreamingAssets/Sprite/cg_image_scene_1_pABC1234567890DEF.png", "pid": "ABC1234567890DEF"},
            ],
        }
        video = {"entries": [], "sourceRoots": {}}
        original_inline = story_media.media_resolver.collect_inline_image_ids
        original_wiki_images = story_media.media_resolver.collect_wiki_media_image_ids
        original_videos = story_media.media_resolver.collect_wiki_video_refs
        try:
            story_media.media_resolver.collect_inline_image_ids = lambda _root: {"cg_image_scene_1"}
            story_media.media_resolver.collect_wiki_media_image_ids = lambda _root: set()
            story_media.media_resolver.collect_wiki_video_refs = lambda _root: set()
            payload = story_media.build_story_media_payload(asset, video)
        finally:
            story_media.media_resolver.collect_inline_image_ids = original_inline
            story_media.media_resolver.collect_wiki_media_image_ids = original_wiki_images
            story_media.media_resolver.collect_wiki_video_refs = original_videos

        self.assertEqual(payload["counts"]["image"], 1)
        self.assertEqual(payload["counts"]["cgImages"], 1)
        self.assertEqual(payload["counts"]["storyFileImages"], 1)
        self.assertEqual(len(payload["entries"]), 1)


if __name__ == "__main__":
    unittest.main()
