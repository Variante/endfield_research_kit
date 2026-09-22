"""Exact current-wrapper codec for LevelData ``predefinedParams``."""

from __future__ import annotations

from typing import Any

from .blackbox import (
    LevelDataBlackboxCodecError,
    decode_predefined_param_at,
)
from .memorypack import read_count, read_string


def decode_level_factory_predefined_param_list(
    data: bytes, offset: int,
) -> dict[str, Any] | None:
    """Decode ``List<LevelFactoryPredefinedParamData>`` exactly.

    The generated two-member owner reads ``instKey`` and then the nullable
    20-member ``PredefinedParam``. Nested component codecs are shared with the
    same wrapper used by ``LevelDataBlackbox.predefinedTemplates``.
    """
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any] | None] = []
    component_counts: dict[str, int] = {}
    try:
        for index in range(max(0, count)):
            row_start = cursor
            if cursor >= len(data):
                return None
            if data[cursor] == 0xFF:
                rows.append(None)
                cursor += 1
                continue
            if data[cursor] != 2:
                return None
            cursor += 1
            key_decoded = read_string(data, cursor, max_length=16_384)
            if key_decoded is None:
                return None
            inst_key, cursor = key_decoded
            if cursor >= len(data):
                return None
            if data[cursor] == 0xFF:
                param = None
                cursor += 1
            else:
                if data[cursor] != 20:
                    return None
                param, cursor = decode_predefined_param_at(
                    data, cursor + 1, f"predefinedParams[{index}].param"
                )
                for name, value in param.items():
                    if name != "memberCount" and value is not None:
                        component_counts[name] = component_counts.get(name, 0) + 1
            rows.append({
                "indexInCollection": index,
                "startOffset": row_start,
                "endOffset": cursor,
                "memberCount": 2,
                "instKey": inst_key,
                "param": param,
            })
    except LevelDataBlackboxCodecError:
        return None
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "componentCounts": dict(sorted(component_counts.items())),
        "itemFieldOrder": ["instKey", "param"],
        "paramFieldOrder": [
            "cache", "common", "envGenWithActivator", "fluidContainer",
            "fluidReaction", "gridBox", "hub", "miner", "powerDiffuser",
            "powerGate", "powerPole", "powerPort", "producer", "selector",
            "sewageTreatPlantExport", "sewageTreatPlantImport", "sign",
            "travelPole", "udPipe", "valve",
        ],
        "fieldOrderSource": (
            "current generated LevelFactoryPredefinedParamDataForMemoryPack "
            "and PredefinedParamForMemoryPack wrappers"
        ),
    }
