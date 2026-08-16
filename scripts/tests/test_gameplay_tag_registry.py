from __future__ import annotations

import unittest

from scripts.gameplay_builder.base_data import _derive_gameplay_tag_context_names


class GameplayTagRegistryTests(unittest.TestCase):
    def test_status_context_crc_derives_missing_immune_name(self) -> None:
        names, proofs = _derive_gameplay_tag_context_names(
            {
                "tagName2Immune": {
                    "Status/Immobilized/BlowOff": {
                        "predefinedTag": [
                            {"tagId": 663699526},
                            {"tagId": 437766570},
                        ]
                    }
                }
            }
        )

        self.assertEqual(names, {"0x1a17c9aa": ["Immune/BlowOff"]})
        self.assertEqual(
            proofs,
            [
                {
                    "id": "0x1a17c9aa",
                    "name": "Immune/BlowOff",
                    "context": "Status/Immobilized/BlowOff",
                    "evidenceStatus": "exact-context-derived",
                }
            ],
        )

    def test_context_does_not_turn_unrelated_buff_name_into_a_tag(self) -> None:
        names, proofs = _derive_gameplay_tag_context_names(
            {
                "tagName2Immune": {
                    "Status/Immobilized/BlowOff": {
                        "predefinedTag": [{"tagId": 663699526}]
                    }
                }
            }
        )

        self.assertEqual(names, {})
        self.assertEqual(proofs, [])

    def test_enemy_infliction_context_derives_element_specific_immune_path(self) -> None:
        names, proofs = _derive_gameplay_tag_context_names(
            {
                "tagName2Immune": {
                    "Skill/Enemy/Common/SpellInflictOnChar/CrystInflictOnChar": {
                        "predefinedTag": [
                            {"tagId": 2029823986},
                            {"tagId": 3408046040},
                            {"tagId": 3338849111},
                            {"tagId": 3445128550},
                        ]
                    }
                }
            }
        )

        self.assertEqual(names, {"0xcd587d66": ["Immune/SpellInflictOnChar/CrystInflictOnChar"]})
        self.assertEqual(proofs[0]["context"], "Skill/Enemy/Common/SpellInflictOnChar/CrystInflictOnChar")


if __name__ == "__main__":
    unittest.main()
