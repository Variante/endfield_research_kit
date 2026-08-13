from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_character_data import build_language_payload, table_roots


class BuildCharacterDataTests(unittest.TestCase):
    def test_collects_and_merges_name_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            tables = root / "structured" / "StreamingAssets" / "Table"
            tables.mkdir(parents=True)
            fixtures = {
                "TextTable.json": {
                    "npcName_chen": {"id": 10, "text": ""},
                    "npcName_f1m29d1weixidong": {"id": 13, "text": ""},
                },
                "I18nTextTable_CN.json": {
                    "10": "陈",
                    "11": "陈千语",
                    "12": "安德烈",
                    "13": "卫西东",
                    "14": "葛一朴",
                },
                "CharacterTable.json": {
                    "chr_0005_chen": {"charId": "chr_0005_chen", "name": {"id": 11}, "engName": "Chen Qianyu"},
                },
                "NpcTable.json": {
                    "andrew": {"npcId": "andrew", "dataKey": "npc_spl_andrew_01", "name": {"id": 12}},
                },
                "SNSChatTable.json": {
                    "sns_chat_heartrepair": {
                        "chatId": "sns_chat_heartrepair",
                        "name": {"text": "心脏修复同步群"},
                        "owner": "sns_npc_geyipu",
                    },
                    "sns_npc_geyipu": {
                        "chatId": "sns_npc_geyipu",
                        "name": {"id": 14},
                    },
                },
            }
            for name, payload in fixtures.items():
                (tables / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
            actors = root / "webui" / "data" / "lang" / "CN" / "actors.json"
            actors.parent.mkdir(parents=True)
            actors.write_text(json.dumps({"actorNames": {
                "chen": ["千语"],
                "sns_npc_geyipu": ["葛一朴"],
            }}, ensure_ascii=False), encoding="utf-8")
            assets = root / "webui" / "data" / "assets" / "index.json"
            assets.parent.mkdir(parents=True)
            assets.write_text(json.dumps({"entries": [
                {"k": "model", "r": "StreamingAssets/Animator/P_actor_chen_01_p0123456789ABCDEF.fbx", "pid": "0123456789ABCDEF"},
                {"k": "model", "r": "StreamingAssets/Animator/P_npc_major_andrew_01.fbx"},
                {"k": "image", "r": "StreamingAssets/Texture2D/icon_sns_npc_weixidong_01.png"},
                {"k": "image", "r": "StreamingAssets/Texture2D/icon_sns_npc_geyipu_01.png"},
            ]}), encoding="utf-8")

            payload = build_language_payload("CN", table_roots(root), "CN", actors, assets)
            by_id = {row["id"]: row for row in payload["records"]}

            self.assertEqual("character", by_id["chen"]["kind"])
            self.assertEqual({"陈", "陈千语", "Chen Qianyu", "千语"}, {item["text"] for item in by_id["chen"]["names"]})
            self.assertTrue(any(item["type"] == "actor_asset" for item in by_id["chen"]["evidence"]))
            self.assertEqual("npc", by_id["andrew"]["kind"])
            self.assertTrue(any(item["type"] == "major_npc_asset" for item in by_id["andrew"]["evidence"]))
            self.assertNotIn("weixidong", by_id)
            self.assertTrue(any(
                item["type"] == "npc_asset" and item.get("matchedIdentity") == "f1m29d1weixidong"
                for item in by_id["f1m29d1weixidong"]["evidence"]
            ))
            self.assertNotIn("geyipu", by_id)
            self.assertIn("SNSChatTable", by_id["sns_npc_geyipu"]["sourceTypes"])
            self.assertTrue(any(
                item["type"] == "npc_asset" and item.get("matchedIdentity") == "sns_npc_geyipu"
                for item in by_id["sns_npc_geyipu"]["evidence"]
            ))


if __name__ == "__main__":
    unittest.main()
