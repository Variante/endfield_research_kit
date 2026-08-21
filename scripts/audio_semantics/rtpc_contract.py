"""Build-locked static GameParameter/RTPC identity contract.

The builder records the source evidence rows; semantic projections validate
against this one shared identity contract so a stale or fabricated
``AU_RTPC_*`` name cannot become a second native catalog.
"""

from __future__ import annotations


CANONICAL_RTPC_IDS = {
    "AU_RTPC_CINE_CTRL_VOL_AMB": 0x6B7DC358,
    "AU_RTPC_CINE_CTRL_VOL_MU": 0x590F4CD1,
    "AU_RTPC_CINE_CTRL_VOL_SFX": 0x52AABB05,
    "AU_RTPC_IS_MUTE_BY_SDK_WEBVIEW": 0xBA4A40B7,
    "AU_RTPC_IS_SURROUND_CHANNELS": 0x7EC2F9AA,
    "AU_RTPC_GLOBAL_VOL_MASTER_IOS_WORKAROUND": 0x3794392F,
}
CANONICAL_RTPC_HEX = {
    name: f"0x{parameter_id:08x}"
    for name, parameter_id in CANONICAL_RTPC_IDS.items()
}
CANONICAL_METADATA_PREFIX = (
    "Beyond.Gameplay.Audio.AudioGameplayConstants+GameParameters."
)
CANONICAL_RTPC_ENTRIES = tuple(
    {
        "parameterId": parameter_id,
        "parameterIdHex": CANONICAL_RTPC_HEX[name],
        "metadataField": CANONICAL_METADATA_PREFIX + name,
    }
    for name, parameter_id in CANONICAL_RTPC_IDS.items()
)


__all__ = [
    "CANONICAL_METADATA_PREFIX",
    "CANONICAL_RTPC_ENTRIES",
    "CANONICAL_RTPC_HEX",
    "CANONICAL_RTPC_IDS",
]
