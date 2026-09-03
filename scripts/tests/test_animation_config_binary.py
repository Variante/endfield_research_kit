from __future__ import annotations

import unittest

from scripts.story_builder.animation_config_binary import (
    AnimationConfigFramingError,
    FIXED_72_PREFIX,
    FIXED_72_SUFFIX,
    frame_animation_config,
)


class AnimationConfigBinaryTests(unittest.TestCase):
    RAW_VALUE = 0x0123456789ABCDEF

    @classmethod
    def _fixed_frame(cls) -> bytes:
        return (
            FIXED_72_PREFIX
            + cls.RAW_VALUE.to_bytes(8, "little", signed=False)
            + FIXED_72_SUFFIX
        )

    def test_exact_72_byte_variant_consumes_every_byte_anonymously(self) -> None:
        payload = self._fixed_frame()
        decoded = frame_animation_config(payload)

        self.assertEqual(72, len(payload))
        self.assertEqual("exact_anonymous_72_byte_frame", decoded["status"])
        self.assertEqual(72, decoded["bytesConsumed"])
        self.assertEqual([], decoded["opaqueRanges"])
        self.assertEqual(self.RAW_VALUE, decoded["ranges"][1]["rawValue"])
        self.assertEqual(255, decoded["prefix"]["rawNullTag"])

    def test_general_variant_preserves_the_remainder_as_opaque(self) -> None:
        payload = FIXED_72_PREFIX[:18] + b"unparsed"
        decoded = frame_animation_config(payload)

        self.assertEqual("exact_prefix_with_opaque_remainder", decoded["status"])
        self.assertEqual(18, decoded["opaqueRanges"][0]["startOffset"])
        self.assertEqual(len(payload), decoded["opaqueRanges"][0]["endOffset"])

    def test_truncated_prefix_fails_closed(self) -> None:
        with self.assertRaisesRegex(AnimationConfigFramingError, "truncated"):
            frame_animation_config(FIXED_72_PREFIX[:17])

    def test_member_count_and_null_tag_drift_fail_closed(self) -> None:
        payload = bytearray(self._fixed_frame())
        payload[0] = 14
        with self.assertRaisesRegex(AnimationConfigFramingError, "member count"):
            frame_animation_config(bytes(payload))

        payload = bytearray(self._fixed_frame())
        payload[1] = 0
        with self.assertRaisesRegex(AnimationConfigFramingError, "null tag"):
            frame_animation_config(bytes(payload))

    def test_zero_word_prefix_drift_fails_closed(self) -> None:
        payload = bytearray(self._fixed_frame())
        payload[8] = 1
        with self.assertRaisesRegex(AnimationConfigFramingError, "zero-word"):
            frame_animation_config(bytes(payload))

    def test_suffix_or_length_drift_cannot_retain_exact_variant_status(self) -> None:
        payload = bytearray(self._fixed_frame())
        payload[-1] ^= 1
        self.assertEqual(
            "exact_prefix_with_opaque_remainder",
            frame_animation_config(bytes(payload))["status"],
        )
        self.assertEqual(
            "exact_prefix_with_opaque_remainder",
            frame_animation_config(self._fixed_frame() + b"\x00")["status"],
        )


if __name__ == "__main__":
    unittest.main()
