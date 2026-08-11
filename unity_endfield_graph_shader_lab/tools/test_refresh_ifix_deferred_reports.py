import importlib.util
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).with_name("refresh_ifix_deferred_reports.py")
SPEC = importlib.util.spec_from_file_location("refresh_ifix_deferred_reports", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RefreshIfixDeferredReportsTests(unittest.TestCase):
    def summary(self) -> dict[str, object]:
        return {
            "index_repo_path": "scratch/character_recovery/ifix/index.json",
            "index_sha256": "b" * 64,
            "block_version": 23167343,
            "file_count": 1,
            "chunk_count": 1,
            "byte_count": 86926,
            "target_count": 32,
            "state_repo_path": "state.json",
            "state_size": 123,
            "state_sha256": "c" * 64,
            "patch_sha256": "d" * 64,
        }

    def test_updates_only_ifix_projection_fields(self) -> None:
        payload = {
            "support": {
                "installed_ifix_patch_index": {
                    "repo_path": "old.json",
                    "sha256": "a" * 64,
                    "block_version": 22764515,
                    "byte_count": 82021,
                    "target_count": 30,
                    "state_report": {},
                }
            },
            "native": {
                "settings": {
                    "persistent_ifix_patch_overlay": {
                        "block_version": 22764515,
                        "byte_count": 82021,
                        "target_count": 30,
                    }
                }
            },
            "text": "active 30-target Gameplay.Beyond patch",
            "unrelated": {"target_count": 30, "byte_count": 82021},
        }
        result = MODULE.refresh_payload(payload, self.summary())
        self.assertEqual(
            result["support"]["installed_ifix_patch_index"]["target_count"], 32
        )
        self.assertEqual(
            result["native"]["settings"]["persistent_ifix_patch_overlay"]["block_version"],
            23167343,
        )
        self.assertEqual(result["text"], "active 32-target Gameplay.Beyond patch")
        self.assertEqual(result["unrelated"]["target_count"], 30)

    def test_render_preserves_report_formatting(self) -> None:
        original = '{\n  "installed_ifix_target_count": 30,\n  "unrelated": 30\n}\n'
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text(original, encoding="utf-8")
            rendered = MODULE.render(path, self.summary())
        self.assertEqual(
            rendered,
            '{\n  "installed_ifix_target_count": 32,\n  "unrelated": 30\n}\n',
        )


if __name__ == "__main__":
    unittest.main()
