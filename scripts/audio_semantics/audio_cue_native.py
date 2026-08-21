"""Build-locked AudioCue expression enum names.

The numeric values are useful evidence even when the selected native inputs do
not match.  Names are intentionally returned only after the common explicit
metadata/GameAssembly gate has validated both exact hashes.
"""

from __future__ import annotations

from typing import Any

from . import native_evidence


AUDIO_CUE_EXPRESSION_TYPES = {
    0: "EMPTY",
    1: "BINARY_EXPRESSION",
    2: "FUNCTION_CALL",
    3: "IDENTIFIER",
    4: "UNARY_EXPRESSION",
    5: "BOOL_LITERAL",
    6: "INT_LITERAL",
    7: "FLOAT_LITERAL",
    8: "STRING_LITERAL",
}
AUDIO_CUE_EXPRESSION_OP_TYPES = {
    64: "NOT_OPERATOR",
    131: "PostEventIf",
    144: "SetBoolVar",
    149: "GetBoolVar",
    153: "CleanBoolVar",
}


def exact_native_audio_cue_contract(
    native_context: native_evidence.NativeAudioEvidence | None,
) -> dict[str, Any]:
    """Return exact enum names only for the validated selected-input gate."""

    if native_context is None:
        return {
            "status": "missing",
            "reason": "native AudioCue enum gate was not selected",
            "expressionTypes": {},
            "operatorTypes": {},
        }
    if (
        not native_context.validated
        or not native_context.gate_verified
        or native_context.metadata_sha256.casefold() != native_evidence.EXPECTED_METADATA_SHA256
        or native_context.gameassembly_sha256.casefold() != native_evidence.EXPECTED_GAMEASSEMBLY_SHA256
    ):
        return {
            "status": native_context.status if native_context.status != "validated" else "unverified",
            "reason": native_context.reason or "selected native inputs did not pass the exact AudioCue enum gate",
            "expressionTypes": {},
            "operatorTypes": {},
        }
    return {
        "status": "validated",
        "reason": "exact selected global-metadata.dat and GameAssembly.dll hashes",
        "metadataSha256": native_context.metadata_sha256,
        "gameAssemblySha256": native_context.gameassembly_sha256,
        "expressionTypes": dict(AUDIO_CUE_EXPRESSION_TYPES),
        "operatorTypes": dict(AUDIO_CUE_EXPRESSION_OP_TYPES),
        "evidence": "exactCurrentBuildAudioCueEnumDefinitions",
    }


__all__ = [
    "AUDIO_CUE_EXPRESSION_TYPES",
    "AUDIO_CUE_EXPRESSION_OP_TYPES",
    "exact_native_audio_cue_contract",
]
