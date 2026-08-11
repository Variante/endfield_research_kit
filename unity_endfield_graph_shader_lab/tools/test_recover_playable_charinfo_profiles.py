import struct
import unittest

from recover_playable_charinfo_profiles import recover_display_record, source_layer


def unity_string(value: str) -> bytes:
    encoded = value.encode("ascii")
    result = struct.pack("<I", len(encoded)) + encoded
    return result + b"\0" * ((-len(result)) & 3)


class RawCharacterDisplayRecoveryTests(unittest.TestCase):
    def test_recognizes_streaming_and_persistent_source_layers(self) -> None:
        self.assertEqual(
            source_layer({"Source": r"D:\Game\Endfield_Data\StreamingAssets\VFS\a.chk"}),
            "StreamingAssets",
        )
        self.assertEqual(
            source_layer({"Source": r"D:\Game\Endfield_Data\Persistent\VFS\b.chk"}),
            "Persistent",
        )

    def test_recovers_serialized_height_groups_and_overview_offset(self) -> None:
        character_id = "chr_0032_lizhiyan"
        record = bytearray()
        record += struct.pack("<3I", 0, 0, 0)
        record += struct.pack("<I", 2)
        record += struct.pack("<I", 0)
        record += unity_string("CameraTracks/track_chr_0032_lizhiyan")
        record += unity_string("AdditionalLights/light_chr_0032_lizhiyan")
        record += struct.pack("<7f", 0, 0, 0, 1, 1, 1, 1)
        record += struct.pack("<3f", 0.1, -0.2, 0.3)
        record += unity_string(character_id)

        recovered = recover_display_record(character_id, bytes(record), 0, len(record))

        self.assertEqual(recovered["height"], {"name": "Female", "value": 2})
        self.assertEqual(
            recovered["charInfoCameraGroup"],
            "CameraTracks/track_chr_0032_lizhiyan",
        )
        self.assertEqual(
            recovered["charInfoLightGroup"],
            "AdditionalLights/light_chr_0032_lizhiyan",
        )
        self.assertAlmostEqual(recovered["overviewImgOffset"]["x"], 0.1)
        self.assertAlmostEqual(recovered["overviewImgOffset"]["y"], -0.2)
        self.assertAlmostEqual(recovered["overviewImgOffset"]["z"], 0.3)


if __name__ == "__main__":
    unittest.main()
