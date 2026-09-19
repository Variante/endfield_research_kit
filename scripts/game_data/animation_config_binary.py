"""Anonymous, fail-closed framing for ``AnimationConfig`` payloads."""

from __future__ import annotations

from typing import Any


COMMON_PREFIX = bytes.fromhex(
    "0f ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
)
FIXED_72_PREFIX = bytes.fromhex(
    "0f ff 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00"
)
FIXED_72_SUFFIX = bytes.fromhex(
    "ff 01 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 "
    "00 00 00 00 00 00 00 00 00 00 01 00 00 00 00 01 00 00 00 00 00 00"
)


class AnimationConfigFramingError(ValueError):
    """Raised when the current-corpus prefix cannot be authenticated."""


def frame_animation_config(data: bytes) -> dict[str, Any]:
    """Frame the proven prefix and one exact anonymous 72-byte variant.

    All current files begin with a 15-member object marker, a raw null tag,
    and four zero words. Without a current formatter body these bytes are not
    assigned field names. The remainder is explicitly opaque, except for the
    current 72-byte variant whose fixed bytes and one raw u64 occupy the whole
    file and therefore consume exactly to EOF.
    """
    if not data:
        raise AnimationConfigFramingError(
            "truncated AnimationConfig: empty payload"
        )
    if data[0] != 15:
        raise AnimationConfigFramingError(
            "AnimationConfig member count mismatch: "
            f"expected=15 actual={data[0]}"
        )
    if len(data) < len(COMMON_PREFIX):
        raise AnimationConfigFramingError(
            "truncated AnimationConfig prefix: "
            f"expected={len(COMMON_PREFIX)} actual={len(data)}"
        )
    if data[1] != 0xFF:
        raise AnimationConfigFramingError(
            f"AnimationConfig raw null tag mismatch: expected=255 actual={data[1]}"
        )
    if data[2:18] != b"\x00" * 16:
        raise AnimationConfigFramingError(
            "AnimationConfig anonymous zero-word prefix mismatch at offsets 2..18"
        )

    base: dict[str, Any] = {
        "schemaStatus": "partial",
        "serializedMemberCount": 15,
        "bytesConsumed": len(data),
        "prefix": {
            "startOffset": 0,
            "endOffset": len(COMMON_PREFIX),
            "rawNullTagOffset": 1,
            "rawNullTag": data[1],
            "rawZeroWordOffsets": [2, 6, 10, 14],
            "fieldIdentityStatus": "unproven_without_formatter_body",
        },
    }

    if (
        len(data) == 72
        and data[:22] == FIXED_72_PREFIX
        and data[30:] == FIXED_72_SUFFIX
    ):
        base.update({
            "status": "exact_anonymous_72_byte_frame",
            "schemaStatus": "anonymous_exact_frame",
            "ranges": [
                {
                    "startOffset": 0,
                    "endOffset": 22,
                    "status": "fixed_current_corpus_bytes",
                },
                {
                    "startOffset": 22,
                    "endOffset": 30,
                    "status": "raw_u64",
                    "rawValue": int.from_bytes(
                        data[22:30],
                        "little",
                        signed=False,
                    ),
                },
                {
                    "startOffset": 30,
                    "endOffset": 72,
                    "status": "fixed_current_corpus_bytes",
                },
            ],
            "opaqueRanges": [],
            "evidenceBoundary": (
                "All 72 bytes are bounded and exactly consumed, but no range is "
                "assigned an authored field name or gameplay meaning."
            ),
        })
        return base

    base.update({
        "status": "exact_prefix_with_opaque_remainder",
        "ranges": [
            {
                "startOffset": 0,
                "endOffset": len(COMMON_PREFIX),
                "status": "authenticated_current_corpus_prefix",
            },
            {
                "startOffset": len(COMMON_PREFIX),
                "endOffset": len(data),
                "status": "opaque_unassigned_payload",
            },
        ],
        "opaqueRanges": [{
            "startOffset": len(COMMON_PREFIX),
            "endOffset": len(data),
            "length": len(data) - len(COMMON_PREFIX),
        }],
        "evidenceBoundary": (
            "Only the 18-byte current-corpus prefix is authenticated; all "
            "remaining bytes, including any apparent suffix, stay opaque."
        ),
    })
    return base
