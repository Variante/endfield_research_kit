"""Reviewed positive Encounter opera-segment list cursor.

Decodes ``EncounterData.introPart.operaSegments`` through the generated
``OperaSegment``, ``ParamKeyValue``, ``ParamValue`` and ``ParamValueAtom``
wrappers supplied by ``levelscript_encounter_opera_segments_native.json``,
which checks all four nested layouts and their complete reader windows
against the selected build before this runs. Only reviewed positive segment
counts are accepted, with one keyed parameter holding one value atom per
segment. Any other positive shape fails closed. The nested cursor rejoins the
sequential owner, which must still reach physical EOF.  The stored opera
type, key and value do not establish when or whether an encounter operation
executes.
"""

from __future__ import annotations

import struct
from typing import Any

from .action_map import ActionMapCodecError, Declarations, _Cursor


_RECORDS = (
    "EncounterData.OperaSegment",
    "ParamKeyValue",
    "ParamValue",
    "ParamValueAtom",
)


def decode_positive_encounter_opera_segments(
    data: bytes, offset: int, field: str, contract: dict[str, Any],
) -> tuple[dict[str, Any], int]:
    """Decode only native-gated, source-reviewed positive nested lists."""
    structs = contract.get("structs") or {}
    if set(structs) != set(_RECORDS):
        raise ActionMapCodecError(f"{field}:missing-reviewed-opera-records")
    if not 0 <= offset <= len(data) - 4:
        raise ActionMapCodecError(f"{field}:truncated-count,offset={offset}")
    count = struct.unpack_from("<i", data, offset)[0]
    if count not in contract.get("supportedSegmentCounts", ()):
        raise ActionMapCodecError(f"{field}:unsupported-positive-count={count}")
    reader = _Cursor(data, offset, Declarations({}, structs, {}))
    values = reader.value("EncounterData.OperaSegment[]", field)
    if not isinstance(values, list) or len(values) != count:
        raise ActionMapCodecError(f"{field}:invalid-decoded-count")
    for segment in values:
        parameters = segment.get("parameters") if isinstance(segment, dict) else None
        if not isinstance(parameters, list) or len(parameters) != 1:
            raise ActionMapCodecError(f"{field}:unsupported-parameter-count")
        value = parameters[0].get("value") if isinstance(parameters[0], dict) else None
        atoms = value.get("valueArray") if isinstance(value, dict) else None
        if not isinstance(atoms, list) or len(atoms) != 1:
            raise ActionMapCodecError(f"{field}:unsupported-atom-count")
    return {"status": "present", "count": count, "values": values}, reader.offset
