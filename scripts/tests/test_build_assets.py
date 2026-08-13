import tempfile
import unittest
from pathlib import Path

from scripts import build_assets
from scripts.asset_builder.index import AssetScanResult, scan_exported_media_assets

class BuildAssetsTests(unittest.TestCase):
    def scan_fixture(self, root: Path) -> tuple[Path, AssetScanResult]:
        export_root = root / "export_full"
        source_root = export_root / "structured" / "StreamingAssets"
        fixtures = {
            "Sprite/sns_image_fixture_p1111111111111111.png": b"fixture-image",
            "Guide/PC/guide_fixture_p2222222222222222.mp4": b"fixture-video",
            "Mesh/fixture_p3333333333333333.obj": b"o fixture\n",
        }
        for rel, content in fixtures.items():
            path = source_root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        return export_root, scan_exported_media_assets(root=root, export_root=export_root)

    def with_story_fixture(self, scan: AssetScanResult):
        original = build_assets.build_story_media_payload
        image = next(entry for entry in scan.asset_entries if entry.get("k") == "image")
        video = next(entry for entry in scan.video_entries if entry.get("k") == "video")

        def build_story(asset_payload: dict, _video_payload: dict) -> dict:
            entries = [dict(image), dict(video)]
            return {
                "generated": asset_payload["generated"],
                "root": asset_payload["root"],
                "sourceRoots": asset_payload["sourceRoots"],
                "counts": {"total": 2, "image": 1, "video": 1},
                "entries": entries,
            }

        build_assets.build_story_media_payload = build_story
        self.addCleanup(setattr, build_assets, "build_story_media_payload", original)

    def test_scan_returns_public_result_and_one_pair_of_payloads(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root, scan = self.scan_fixture(root)
            asset_payload, video_payload = scan.payloads(root=root, export_root=export_root)

        self.assertIsInstance(scan, AssetScanResult)
        self.assertEqual(scan.counts, {"total": 3, "image": 1, "model": 1, "video": 1, "json": 0})
        self.assertEqual(scan.video_counts, {"total": 1, "video": 1})
        self.assertEqual(asset_payload["generated"], video_payload["generated"])
        self.assertEqual(asset_payload["counts"], scan.counts)
        image = next(entry for entry in asset_payload["entries"] if entry.get("k") == "image")
        self.assertEqual(image["pid"], "1111111111111111")

    def test_focused_payload_publishes_only_story_media_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root, scan = self.scan_fixture(root)
            self.with_story_fixture(scan)

            asset_payload, video_payload, story_payload = build_assets.build_output_payloads(
                scan,
                mode="focused",
                root=root,
                export_root=export_root,
            )

        self.assertEqual(asset_payload["mode"], "webui")
        self.assertEqual(asset_payload["counts"], {"total": 2, "image": 1, "model": 0, "video": 1, "json": 0})
        self.assertEqual(asset_payload["entries"], story_payload["entries"])
        self.assertEqual(video_payload["entries"], [story_payload["entries"][1]])

    def test_default_and_debug_publish_the_same_full_scan_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            export_root, scan = self.scan_fixture(root)
            self.with_story_fixture(scan)

            default_asset, default_video, _story = build_assets.build_output_payloads(
                scan,
                mode="default",
                root=root,
                export_root=export_root,
            )
            debug_asset, debug_video, _story = build_assets.build_output_payloads(
                scan,
                mode="debug",
                root=root,
                export_root=export_root,
            )

        self.assertNotIn("mode", default_asset)
        self.assertEqual(default_asset["counts"], scan.counts)
        self.assertEqual(default_asset["entries"], scan.asset_entries)
        self.assertEqual(default_video["entries"], scan.video_entries)
        self.assertEqual(default_asset, debug_asset)
        self.assertEqual(default_video, debug_video)


if __name__ == "__main__":
    unittest.main()
