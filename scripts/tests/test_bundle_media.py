import unittest

from scripts.story_builder.bundle_media import (
    collect_payload_media_tags,
    image_ids_from_text,
    inline_image_id_from_tag,
    media_id_is_emoji,
    media_id_is_sticker,
    media_id_looks_like_media,
    normalize_media_id,
    sns_media_text_from_params,
)
from scripts.story_builder.bundle_support import parse_mission
from scripts.story_builder.context import MISSION_STORY_TYPES


MEDIA_POLICY = {
    "parse_mission": parse_mission,
    "mission_story_types": MISSION_STORY_TYPES,
}


class BundleMediaTests(unittest.TestCase):
    def test_normalizes_and_classifies_media_ids(self) -> None:
        self.assertEqual(
            normalize_media_id(r"'SNS\Emoji\SNS_EMOJI_WAVE.PNG'"),
            "sns_emoji_wave",
        )
        self.assertTrue(media_id_is_emoji("sns_emoiji_typo"))
        self.assertTrue(media_id_is_sticker("SNS_STICKER_HELLO.PNG"))
        self.assertFalse(media_id_is_sticker("sns_sticker_emoji_mix"))
        self.assertTrue(media_id_looks_like_media("sns_image_card", **MEDIA_POLICY))
        self.assertFalse(media_id_looks_like_media("123", **MEDIA_POLICY))
        self.assertFalse(media_id_looks_like_media("e1m2", **MEDIA_POLICY))

    def test_extracts_all_supported_inline_image_forms(self) -> None:
        self.assertEqual(
            image_ids_from_text('<image="direct_a"> <image=direct_b>'),
            ["direct_a", "direct_b"],
        )
        cases = {
            "<image=id_a>": "id_a",
            "<image src='attr_b'>": "attr_b",
            "<image>body_c</image>": "body_c",
        }
        for raw_tag, expected in cases.items():
            with self.subTest(raw_tag=raw_tag):
                self.assertEqual(inline_image_id_from_tag(raw_tag), expected)

    def test_projects_gender_pair_and_generic_media_params(self) -> None:
        self.assertEqual(
            sns_media_text_from_params(
                ["sns_image_avatar_f", "sns_image_avatar_m"],
                **MEDIA_POLICY,
            ),
            '{M}<image="sns_image_avatar_m">{F}<image="sns_image_avatar_f">',
        )
        self.assertEqual(
            sns_media_text_from_params(
                ["e1m2", "sns_sticker_wave"],
                **MEDIA_POLICY,
            ),
            '<image="sns_sticker_wave">',
        )

    def test_collects_nested_payload_media_and_video_tags(self) -> None:
        payload = {
            "lines": [
                {
                    "text": '<image="SNS/Emoji/sns_emoji_wave.png">',
                    "image": "sns_image_header",
                    "images": ["e1m2", "sns_sticker_hello"],
                    "_debug": {
                        "source": {
                            "source": {
                                "contentParams": "{malformed",
                                "optionResPath": "sns_image_option",
                                "video": "cutscene_a",
                            }
                        }
                    },
                    "options": [
                        {
                            "text": '<image src="sns_image_option_text">',
                            "_debug": {
                                "source": {
                                    "contentParams": (
                                        '{"nested":[{"emojiResPath":'
                                        '"sns_emoji_nested"}]}'
                                    )
                                }
                            },
                        }
                    ],
                }
            ],
            "summary": [{"text": "<image>sns_sticker_summary</image>"}],
            "narrativeVideos": [{"id": "narrative_a"}],
            "cutscene": {"videoRefs": ["fmv_a"]},
        }

        self.assertEqual(
            collect_payload_media_tags(payload, **MEDIA_POLICY),
            {"mediaEmoji", "mediaImage", "mediaSticker", "mediaVideo"},
        )


if __name__ == "__main__":
    unittest.main()
