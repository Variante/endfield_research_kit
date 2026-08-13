import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS_DIR))

from asset_builder import media_resolver


class MediaResolverTests(unittest.TestCase):
    def test_path_id_stem_is_normalized_and_added_to_index_entry(self) -> None:
        rel = "StreamingAssets/Sprite/sns_image_scene_pabcdef0123456789.png"
        entry = {"k": "image", "r": rel}

        stem, path_id = media_resolver.media_lookup_stem(rel)
        by_stem, _by_number = media_resolver.build_inline_image_lookup([entry])

        self.assertEqual((stem, path_id), ("sns_image_scene", "ABCDEF0123456789"))
        self.assertEqual(entry["pid"], "ABCDEF0123456789")
        self.assertEqual(by_stem["sns_image_scene"].rel, rel)

    def test_env_emoji_resolves_its_exported_prefab_layers(self) -> None:
        entries = [
            {"k": "image", "r": "StreamingAssets/Sprite/emoji_newbg_p1111111111111111.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/emoji_circle_1_p2222222222222222.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/emoji_circle_p3333333333333333.png"},
            {"k": "image", "r": "StreamingAssets/Sprite/emoji_happyeye_p4444444444444444.png"},
        ]
        by_stem, by_number = media_resolver.build_inline_image_lookup(entries)

        resolved = media_resolver.resolve_inline_image_assets(
            "EnvEmoji_Common_Normal",
            by_stem,
            by_number,
        )

        self.assertEqual(
            [candidate.stem for candidate in resolved],
            ["emoji_newbg", "emoji_circle_1", "emoji_circle", "emoji_happyeye"],
        )

    def test_video_resolution_honors_wiki_device_preference(self) -> None:
        entries = [
            {"k": "video", "r": "StreamingAssets-structured/Guide/PC/guide_demo_mb.mp4"},
            {"k": "video", "r": "StreamingAssets-structured/Guide/CT/guide_demo_mb.mp4"},
            {"k": "video", "r": "StreamingAssets-structured/Guide/Common/guide_demo_mb.mp4"},
        ]
        by_stem = media_resolver.build_video_lookup(entries)

        controller = media_resolver.resolve_exact_video_asset("guide_demo_mb", "Controller", by_stem)
        keyboard = media_resolver.resolve_exact_video_asset("guide_demo_mb", "MouseAndKeyboard", by_stem)

        self.assertIn("/Guide/CT/", controller.rel)
        self.assertIn("/Guide/PC/", keyboard.rel)

    def test_collectors_read_inline_and_wiki_debug_media(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            webui_root = Path(raw_root)
            conv_root = webui_root / "data" / "lang" / "CN" / "conv"
            mission_root = webui_root / "data" / "mission"
            conv_root.mkdir(parents=True)
            mission_root.mkdir(parents=True)
            (mission_root / "story.json").write_text(
                json.dumps({"text": "<image='SNS/Emoji/Emoji_Normal.png'>", "images": ["sns_image_demo"]}),
                encoding="utf-8",
            )
            (conv_root / "wiki_demo.json").write_text(
                json.dumps(
                    {
                        "kind": "wiki",
                        "_debug": {"source": {"source": {"refItemId": "wiki_item_42"}}},
                        "lines": [
                            {
                                "_debug": {
                                    "source": {
                                        "image": "wiki_pic_demo",
                                        "video": "guide_demo_mb",
                                        "videoDeviceType": "Controller",
                                    }
                                }
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            inline_ids = media_resolver.collect_inline_image_ids(webui_root)
            wiki_ids = media_resolver.collect_wiki_media_image_ids(webui_root)
            video_refs = media_resolver.collect_wiki_video_refs(webui_root)

        self.assertEqual(inline_ids, {"emoji_normal", "sns_image_demo", "wiki_pic_demo"})
        self.assertIn("item_42", wiki_ids)
        self.assertIn("wiki_pic_demo", wiki_ids)
        self.assertEqual(video_refs, {("guide_demo_mb", "Controller")})


if __name__ == "__main__":
    unittest.main()
