from __future__ import annotations

import unittest

from scripts.gameplay_builder.base_data import discover_character_namespace_ids


class GameplayCharacterNamespaceTests(unittest.TestCase):
    def test_discovers_exact_character_ids_without_promoting_skill_children(self) -> None:
        registry = {
            "characters": {
                "chr_0038_purrche": 52,
                "chr_0038_purrche_attack1": 2928,
                "buff_chr_0038_purrche_block": 2672,
            },
            "reverse": ["chr_9001_girl", "projectile_chr_0038_purrche_normal"],
        }

        self.assertEqual(
            {"chr_0038_purrche"},
            discover_character_namespace_ids(registry),
        )


if __name__ == "__main__":
    unittest.main()
