from __future__ import annotations

import struct
import unittest
from unittest.mock import patch

from scripts.story_builder.native_contracts.spawnerptr_getter import (
    NATIVE_MAPPING_ID,
    decode_spawnerptr_getter_member,
)


class SpawnerPtrGetterContractTests(unittest.TestCase):
    def test_true_member_boundary_decodes_constant_and_source200(self) -> None:
        fixtures = (
            (26200040020, -1, 0, None, "constant"),
            (0, -1, 200, "newSpawner", "source200_property"),
        )
        with patch(
            "scripts.story_builder.native_contracts.spawnerptr_getter.load_spawnerptr_getter_contract",
            return_value=({"unionTag": 420}, {"status": "validated"}),
        ):
            for spawner_id, id_ref, source, path, expected_kind in fixtures:
                encoded_path = path.encode() if path else b""
                path_size = len(encoded_path) if path else -1
                member = b"\x04" + struct.pack(
                    "<Qiii", spawner_id, id_ref, source, path_size
                ) + encoded_path
                data = b"ABCD" + member
                decoded = decode_spawnerptr_getter_member(
                    data,
                    payload_start=8,
                    record_end=len(data),
                )
                self.assertEqual(spawner_id, decoded["spawnerId"])
                self.assertEqual(path, decoded["path"])
                self.assertEqual(expected_kind, decoded["bindingKind"])
                self.assertEqual(NATIVE_MAPPING_ID, decoded["nativeMappingId"])

    def test_wrong_overlap_marker_fails_closed(self) -> None:
        with patch(
            "scripts.story_builder.native_contracts.spawnerptr_getter.load_spawnerptr_getter_contract",
            return_value=({"unionTag": 420}, {"status": "validated"}),
        ):
            self.assertEqual({}, decode_spawnerptr_getter_member(
                b"ABCD\x03" + bytes(20), payload_start=8, record_end=25
            ))


if __name__ == "__main__":
    unittest.main()
