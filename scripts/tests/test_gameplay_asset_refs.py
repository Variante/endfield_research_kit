from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from asset_builder.gameplay_refs import build_gameplay_asset_refs


class GameplayAssetRefsTests(unittest.TestCase):
    def test_prefers_semantic_images_and_keeps_model_preview_links(self) -> None:
        payload = {
            "entries": [
                {"id": "chr_0004_pelica", "kind": "character"},
                {"id": "wpn_sword_0019", "kind": "weapon", "modelPath": "Gameplay/Prefabs/Weapons/wpn_sword_0019.prefab"},
            ]
        }
        assets = [
            {"k": "image", "r": "StreamingAssets/Texture2D/chr_0004_pelica_body_p1111111111111111.png", "ic": "character"},
            {"k": "image", "r": "StreamingAssets/Sprite/chr_0004_pelica_p2222222222222222.png", "ic": "chr_thumb"},
            {"k": "model", "r": "StreamingAssets/Animator/P_wpn_sword_0019_p3333333333333333.fbx", "p": "StreamingAssets/Mesh/S_wpn_sword_0019_lod0_p4444444444444444.obj"},
            {"k": "image", "r": "StreamingAssets/Sprite/wpn_sword_0019_p5555555555555555.png", "ic": "weapon"},
        ]

        result = build_gameplay_asset_refs(payload, assets)
        character = result["entries"]["character:chr_0004_pelica"]
        weapon = result["entries"]["weapon:wpn_sword_0019"]

        self.assertEqual("chr_thumb", character["images"][0]["category"])
        self.assertEqual("weapon", weapon["images"][0]["category"])
        self.assertEqual("model", weapon["models"][0]["kind"])
        self.assertIn("previewRel", weapon["models"][0])

    def test_does_not_match_partial_identifiers(self) -> None:
        payload = {"entries": [{"id": "chr_0004_pelica", "kind": "character"}]}
        assets = [{"k": "image", "r": "StreamingAssets/Sprite/chr_0004_pelica_alt_p1111111111111111.png", "ic": "chr_thumb"},
                  {"k": "image", "r": "StreamingAssets/Sprite/chr_0004_pelican_p2222222222222222.png", "ic": "chr_thumb"}]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0004_pelica"]["images"]]
        self.assertEqual(["StreamingAssets/Sprite/chr_0004_pelica_alt_p1111111111111111.png"], paths)

    def test_character_first_image_prefers_complete_illustration_size(self) -> None:
        payload = {"entries": [{"id": "chr_0004_pelica", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0004_pelica_bust_p1111111111111111.png",
                "ic": "chr_thumb",
                "s": 180000,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0004_pelica_full_p2222222222222222.png",
                "ic": "chr_thumb",
                "s": 2400000,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)

        self.assertEqual(
            "StreamingAssets/Sprite/chr_0004_pelica_full_p2222222222222222.png",
            result["entries"]["character:chr_0004_pelica"]["images"][0]["rel"],
        )

    def test_admin_wrapper_uses_concrete_gender_portraits(self) -> None:
        payload = {"entries": [{"id": "chr_9000_endmin", "kind": "character"}]}
        assets = [{
            "k": "image",
            "r": "StreamingAssets/Texture2D/chr_0002_endminm_p1111111111111111.png",
            "ic": "chr_thumb",
            "iw": 2048,
            "ih": 2048,
        }]

        result = build_gameplay_asset_refs(payload, assets)

        self.assertEqual(
            "StreamingAssets/Texture2D/chr_0002_endminm_p1111111111111111.png",
            result["entries"]["character:chr_9000_endmin"]["images"][0]["rel"],
        )

    def test_character_portraits_use_full_art_then_original_crops(self) -> None:
        payload = {
            "entries": [{"id": "chr_0017_yvonne", "kind": "character"}],
        }
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0017_yvonne_horizontal_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 854,
                "ih": 349,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0017_yvonne_full_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0017_yvonne_vertical_small_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 235,
                "ih": 1060,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0017_yvonne_vertical_p4444444444444444.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0017_yvonne_horizontal_large_p5555555555555555.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
            {
                # A "neutral" pose crop that stays below the full-portrait
                # size gate (min side < 800), so it is a genuine secondary
                # image rather than a second full portrait.
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0017_yvonne_pose_p6666666666666666.png",
                "ic": "chr_thumb",
                "iw": 686,
                "ih": 737,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p7777777777777777.png",
                "ic": "character",
                "iw": 2048,
                "ih": 1024,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0017_yvonne"]["images"]]

        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0017_yvonne_full_p2222222222222222.png",
                "StreamingAssets/Texture2D/chr_0017_yvonne_vertical_p4444444444444444.png",
                "StreamingAssets/Texture2D/chr_0017_yvonne_horizontal_large_p5555555555555555.png",
                "StreamingAssets/Sprite/chr_0017_yvonne_pose_p6666666666666666.png",
            ],
            paths,
        )

    def test_character_gallery_skips_undersized_neutral_reveal_silhouette(self) -> None:
        # Some characters export a small, roughly-square reveal/teaser
        # silhouette alongside the ground-shadow blob (no reliable name
        # marker distinguishes it from a real crop). Once a same-size or
        # larger duplicate full portrait is excluded, this silhouette can
        # become the only remaining "neutral" candidate — it must still be
        # skipped rather than filling that slot.
        payload = {"entries": [{"id": "chr_0028_wulfa", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0028_wulfa_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0028_wulfa_vert_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0028_wulfa_horiz_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
            {
                # Duplicate full-body illustration -- excluded by the
                # full-portrait dedup above, which would otherwise leave
                # this as the only "neutral" bucket candidate.
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0028_wulfa_alt_p4444444444444444.png",
                "ic": "chr_thumb",
                "iw": 2017,
                "ih": 1966,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0028_wulfa_teaser_p5555555555555555.png",
                "ic": "chr_thumb",
                "iw": 310,
                "ih": 358,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0028_wulfa"]["images"]]

        self.assertNotIn(
            "StreamingAssets/Sprite/chr_0028_wulfa_teaser_p5555555555555555.png",
            paths,
        )
        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0028_wulfa_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0028_wulfa_vert_p2222222222222222.png",
                "StreamingAssets/Texture2D/chr_0028_wulfa_horiz_p3333333333333333.png",
            ],
            paths,
        )

    def test_character_gallery_vertical_slot_skips_a_moderately_tall_duplicate(self) -> None:
        # A large (>=800px), moderately tall export (ratio ~0.59) is the same
        # full-body illustration as the square portrait, just cropped a
        # little tighter -- not the narrow ~0.17 ratio banner strip every
        # character also exports for the "vertical" role. Left unfiltered it
        # would win the vertical slot on resolution alone and shadow the
        # portrait a second time instead of showing the real banner crop.
        payload = {"entries": [{"id": "chr_0020_meurs", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0020_meurs_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                # Same illustration as the full portrait, just cropped
                # tighter -- large enough to be its own duplicate portrait.
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0020_meurs_tall_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 1182,
                "ih": 1992,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0020_meurs_banner_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0020_meurs_horiz_p4444444444444444.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0020_meurs"]["images"]]

        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0020_meurs_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0020_meurs_banner_p3333333333333333.png",
                "StreamingAssets/Texture2D/chr_0020_meurs_horiz_p4444444444444444.png",
            ],
            paths,
        )

    def test_character_gallery_keeps_only_the_higher_resolution_full_portrait(self) -> None:
        # A second, differently-cropped export of the same (or an equally
        # "full body") illustration is a duplicate portrait, not a useful
        # extra thumbnail. Only the higher-resolution one should survive;
        # the remaining slot should go to a genuine crop instead.
        payload = {"entries": [{"id": "chr_0021_whiten", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0021_whiten_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                # Same illustration, tighter vertical crop, still large
                # enough to independently read as a full portrait.
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0021_whiten_tall_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 1471,
                "ih": 1996,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0021_whiten_face_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0021_whiten"]["images"]]

        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0021_whiten_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0021_whiten_face_p3333333333333333.png",
            ],
            paths,
        )

    def test_character_gallery_fallback_does_not_double_up_a_crop_group(self) -> None:
        # No neutral-shaped candidate at all (unlike the dedup test above,
        # there isn't even a duplicate full portrait to exclude there). The
        # remaining slot must not be filled by a second, lower-resolution
        # horizontal crop when the horizontal role is already represented.
        payload = {"entries": [{"id": "chr_0009_azrila", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0009_azrila_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0009_azrila_vert_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0009_azrila_horiz_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
            {
                # Same horizontal role as the crop above, smaller and from a
                # different source directory -- a near-duplicate export, not
                # a distinct fourth image.
                "k": "image",
                "r": "StreamingAssets/Sprite/chr_0009_azrila_horiz_alt_p4444444444444444.png",
                "ic": "chr_thumb",
                "iw": 892,
                "ih": 349,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0009_azrila"]["images"]]

        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0009_azrila_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0009_azrila_vert_p2222222222222222.png",
                "StreamingAssets/Texture2D/chr_0009_azrila_horiz_p3333333333333333.png",
            ],
            paths,
        )

    def test_character_gallery_ignores_ground_shadow_sprite(self) -> None:
        # Every character has a `<id>_s_p<hash>` ground-shadow blob (a blurred
        # silhouette meant to sit under the 3D model). A single-illustration
        # character with no second pose/alt art must not have that blob fill
        # the empty "neutral" gallery slot.
        payload = {"entries": [{"id": "chr_0021_whiten", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0021_whiten_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0021_whiten_face_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0021_whiten_s_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 312,
                "ih": 312,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_0021_whiten"]["images"]]

        self.assertNotIn(
            "StreamingAssets/Texture2D/chr_0021_whiten_s_p3333333333333333.png",
            paths,
        )
        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0021_whiten_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0021_whiten_face_p2222222222222222.png",
            ],
            paths,
        )

    def test_admin_gallery_gives_each_gender_its_own_full_role_set(self) -> None:
        payload = {"entries": [{"id": "chr_9000_endmin", "kind": "character"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0002_endminm_full_p1111111111111111.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0002_endminm_vert_p2222222222222222.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0002_endminm_horiz_p3333333333333333.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0003_endminf_full_p4444444444444444.png",
                "ic": "chr_thumb",
                "iw": 2048,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0003_endminf_vert_p5555555555555555.png",
                "ic": "chr_thumb",
                "iw": 236,
                "ih": 1352,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/chr_0003_endminf_horiz_p6666666666666666.png",
                "ic": "chr_thumb",
                "iw": 900,
                "ih": 352,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        paths = [item["rel"] for item in result["entries"]["character:chr_9000_endmin"]["images"]]

        # Each gender matched full + vertical + horizontal candidates. A
        # shared, split budget would force one of those roles to be dropped
        # for one or both genders; instead every gender should keep its
        # complete set, back to back.
        self.assertEqual(
            [
                "StreamingAssets/Texture2D/chr_0002_endminm_full_p1111111111111111.png",
                "StreamingAssets/Texture2D/chr_0002_endminm_vert_p2222222222222222.png",
                "StreamingAssets/Texture2D/chr_0002_endminm_horiz_p3333333333333333.png",
                "StreamingAssets/Texture2D/chr_0003_endminf_full_p4444444444444444.png",
                "StreamingAssets/Texture2D/chr_0003_endminf_vert_p5555555555555555.png",
                "StreamingAssets/Texture2D/chr_0003_endminf_horiz_p6666666666666666.png",
            ],
            paths,
        )

    def test_weapon_images_keep_best_roles_and_ignore_material_maps(self) -> None:
        payload = {"entries": [{"id": "wpn_sword_0019", "kind": "weapon"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/T_wpn_sword_0019_01_D_p0000000000000000.png",
                "ic": "weapon",
                "mt": 1,
                "iw": 1024,
                "ih": 1024,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_sword_0019_full_p1111111111111111.png",
                "ic": "weapon",
                "iw": 1024,
                "ih": 2048,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/wpn_sword_0019_icon_p2222222222222222.png",
                "ic": "weapon",
                "iw": 254,
                "ih": 254,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_sword_0019_icon_p3333333333333333.png",
                "ic": "weapon",
                "iw": 512,
                "ih": 512,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        images = result["entries"]["weapon:wpn_sword_0019"]["images"]

        self.assertEqual(2, len(images))
        self.assertEqual(
            "StreamingAssets/Texture2D/wpn_sword_0019_icon_p3333333333333333.png",
            images[0]["rel"],
        )
        self.assertEqual((512, 512), (images[0]["width"], images[0]["height"]))
        self.assertEqual(
            "StreamingAssets/Texture2D/wpn_sword_0019_full_p1111111111111111.png",
            images[1]["rel"],
        )
        self.assertEqual((1024, 2048), (images[1]["width"], images[1]["height"]))

    def test_weapon_images_use_cropped_illustration_without_creating_aspect_slots(self) -> None:
        payload = {"entries": [{"id": "wpn_pistol_0003", "kind": "weapon"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_pistol_0003_p1111111111111111.png",
                "ic": "weapon",
                "iw": 256,
                "ih": 256,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/wpn_pistol_0003_p2222222222222222.png",
                "ic": "weapon",
                "iw": 463,
                "ih": 388,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_pistol_0003_p3333333333333333.png",
                "ic": "weapon",
                "iw": 1024,
                "ih": 2048,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        images = result["entries"]["weapon:wpn_pistol_0003"]["images"]

        self.assertEqual(2, len(images))
        self.assertEqual((256, 256), (images[0]["width"], images[0]["height"]))
        self.assertEqual((463, 388), (images[1]["width"], images[1]["height"]))
        self.assertIn("/Sprite/", images[1]["rel"])

    def test_weapon_model_alias_does_not_merge_another_weapons_images(self) -> None:
        payload = {
            "entries": [{
                "id": "wpn_funnel_0008",
                "kind": "weapon",
                "modelPath": "Gameplay/Prefabs/Weapons/wpn_funnel_0010.prefab",
            }],
        }
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_funnel_0008_p1111111111111111.png",
                "ic": "weapon",
                "iw": 256,
                "ih": 256,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/wpn_funnel_0008_p2222222222222222.png",
                "ic": "weapon",
                "iw": 472,
                "ih": 411,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/wpn_funnel_0010_p3333333333333333.png",
                "ic": "weapon",
                "iw": 256,
                "ih": 256,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/wpn_funnel_0010_p4444444444444444.png",
                "ic": "weapon",
                "iw": 426,
                "ih": 377,
            },
            {
                "k": "model",
                "r": "StreamingAssets/Animator/P_wpn_funnel_0010_p5555555555555555.fbx",
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        entry = result["entries"]["weapon:wpn_funnel_0008"]

        self.assertEqual(2, len(entry["images"]))
        self.assertTrue(all("wpn_funnel_0008" in image["rel"] for image in entry["images"]))
        self.assertTrue(any("wpn_funnel_0010" in model["rel"] for model in entry["models"]))

    def test_indexes_nested_icons_and_potential_picture_aliases(self) -> None:
        payload = {
            "entries": [{
                "id": "chr_0017_yvonne",
                "kind": "character",
                "skillGroups": [{"iconId": "icon_skill_yvonne_01"}],
                "talentGroups": [{"levels": [{"iconId": "icon_talent_yvonne_01"}]}],
                "potentials": {"levels": [{"unlockCharPictureItemList": ["item_pic_1_chr_0017_yvonne"]}]},
            }],
        }
        assets = [
            {"k": "image", "r": "StreamingAssets/Sprite/icon_skill_yvonne_01_p1111111111111111.png", "ic": "icon"},
            {"k": "image", "r": "StreamingAssets/Sprite/icon_talent_yvonne_01_p2222222222222222.png", "ic": "icon"},
            {"k": "image", "r": "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p3333333333333333.png", "ic": "character"},
        ]

        result = build_gameplay_asset_refs(payload, assets)

        self.assertIn("icon_skill_yvonne_01", result["tokens"])
        self.assertIn("icon_talent_yvonne_01", result["tokens"])
        self.assertEqual(
            "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p3333333333333333.png",
            result["tokens"]["item_pic_1_chr_0017_yvonne"]["images"][0]["rel"],
        )

    def test_potential_topic_prefers_original_theme_card_over_blur(self) -> None:
        payload = {
            "entries": [{
                "id": "chr_0017_yvonne",
                "kind": "character",
                "potentials": {
                    "levels": [{"unlockCardTopicItem": "item_topic_chr_0017_yvonne"}],
                },
            }],
        }
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/business_card_topic_chr_0017_yvonne_blur_p1111111111111111.png",
                "ic": "business_card",
                "iw": 260,
                "ih": 168,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/business_card_topic_chr_0017_yvonne_p2222222222222222.png",
                "ic": "business_card",
                "iw": 1920,
                "ih": 1080,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/item_topic_chr_0017_yvonne_p3333333333333333.png",
                "ic": "item_topic",
                "iw": 256,
                "ih": 256,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)

        self.assertEqual(
            "StreamingAssets/Sprite/business_card_topic_chr_0017_yvonne_p2222222222222222.png",
            result["tokens"]["item_topic_chr_0017_yvonne"]["images"][0]["rel"],
        )

    def test_item_picture_token_keeps_only_highest_resolution_variant(self) -> None:
        payload = {
            "entries": [{
                "id": "chr_0017_yvonne",
                "kind": "character",
                "potentials": {
                    "levels": [{"unlockCharPictureItemList": ["item_pic_1_chr_0017_yvonne"]}],
                },
            }],
        }
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p1111111111111111.png",
                "ic": "character",
                "s": 180000,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p2222222222222222.png",
                "ic": "character",
                "s": 2400000,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        images = result["tokens"]["item_pic_1_chr_0017_yvonne"]["images"]

        self.assertEqual(1, len(images))
        self.assertEqual(
            "StreamingAssets/Texture2D/pic_1_chr_0017_yvonne_p2222222222222222.png",
            images[0]["rel"],
        )

    def test_enemy_gallery_keeps_only_highest_resolution_image(self) -> None:
        payload = {"entries": [{"id": "eny_0001_test", "kind": "enemy"}]}
        assets = [
            {
                "k": "image",
                "r": "StreamingAssets/Sprite/eny_0001_test_p1111111111111111.png",
                "ic": "enemy",
                "iw": 124,
                "ih": 120,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/eny_0001_test_p2222222222222222.png",
                "ic": "enemy",
                "iw": 256,
                "ih": 256,
            },
            {
                "k": "image",
                "r": "StreamingAssets/Texture2D/eny_0001_test_p3333333333333333.png",
                "ic": "enemy",
                "iw": 128,
                "ih": 128,
            },
        ]

        result = build_gameplay_asset_refs(payload, assets)
        images = result["entries"]["enemy:eny_0001_test"]["images"]

        self.assertEqual(1, len(images))
        self.assertEqual((256, 256), (images[0]["width"], images[0]["height"]))

    def test_indexes_material_item_tokens_for_chip_icons(self) -> None:
        payload = {
            "entries": [{
                "id": "chr_0017_yvonne",
                "kind": "character",
                "talentGroups": [{"levels": [{"requiredItem": [{"id": "item_gold", "count": 1}]}]}],
            }],
        }
        assets = [{
            "k": "image",
            "r": "StreamingAssets/Sprite/item_gold_p3333333333333333.png",
            "ic": "item",
        }]

        result = build_gameplay_asset_refs(payload, assets)

        self.assertEqual(
            "StreamingAssets/Sprite/item_gold_p3333333333333333.png",
            result["tokens"]["item_gold"]["images"][0]["rel"],
        )


if __name__ == "__main__":
    unittest.main()
