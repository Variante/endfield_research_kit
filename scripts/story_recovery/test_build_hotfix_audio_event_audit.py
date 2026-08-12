import json
import tempfile
import unittest
from pathlib import Path

from scripts.story_recovery import build_hotfix_audio_event_audit as audit


class HotfixAudioEventAuditTests(unittest.TestCase):
    def test_complete_event_inventory_maps_unnamed_hashes_to_media(self) -> None:
        with tempfile.TemporaryDirectory() as raw_root:
            root = Path(raw_root)
            index_path = root / "structured/Audio/CN/index.json"
            index_path.parent.mkdir(parents=True)
            index_path.write_text(json.dumps({
                "wwiseEventInventory": [
                    {"eventHash": 0x1EFEFA3C, "mediaIds": [212418017, 281684343]},
                    {"eventHash": 0x212B3577, "mediaIds": [929875190]},
                ]
            }), encoding="utf-8")

            rows = audit.indexed_wwise_event_hashes_by_media(root)

            self.assertEqual(rows[212418017], [0x1EFEFA3C])
            self.assertEqual(rows[281684343], [0x1EFEFA3C])
            self.assertEqual(rows[929875190], [0x212B3577])


if __name__ == "__main__":
    unittest.main()
