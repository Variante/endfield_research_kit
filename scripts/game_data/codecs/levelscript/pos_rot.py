"""Exact PosRot children and bounded default stored lists."""
from __future__ import annotations

import math
from pathlib import Path
import struct
from typing import Any

from scripts.game_data.levelscript_pos_rot_native import load_pos_rot_contract


class PosRotDecodeError(ValueError):
    pass


def decode_pos_rot(data: bytes, offset: int, *, game_root: Path | None = None) -> tuple[dict[str, Any], int]:
    """Read one authenticated mc2 child without claiming any parent-list join."""
    contract, native = load_pos_rot_contract(game_root=game_root)
    if native["status"] != "validated":
        raise PosRotDecodeError(f"PosRot.{native['failedCheck']}: expected=validated,actual={native['status']},detail={native['detail']}")
    width = 1 + sum(row["serializedWidth"] for row in contract["fields"])
    if offset < 0 or offset + width > len(data):
        raise PosRotDecodeError(f"PosRot.bounded-record: offset={offset},expected={width},actual={max(0,len(data)-offset)}")
    if data[offset] != contract["memberCount"]:
        raise PosRotDecodeError(f"PosRot.member-count: offset={offset},expected={contract['memberCount']},actual={data[offset]}")
    values = struct.unpack_from("<6f", data, offset + 1)
    if not all(math.isfinite(value) for value in values):
        raise PosRotDecodeError(f"PosRot.finite-vector-profile: offset={offset},actual=non-finite")
    result = {row["name"]: dict(zip(("x", "y", "z"), values[index*3:index*3+3]))
              for index,row in enumerate(contract["fields"])}
    return result, offset + width


def decode_pos_rot_list(data: bytes, offset: int, *, game_root: Path | None = None) -> tuple[list[dict[str, Any]] | None, int]:
    """Read a bounded registered default list, retaining child object framing."""
    _, audit = load_pos_rot_contract(game_root=game_root)
    if audit.get("status") != "validated" or audit.get("parentProofStatus") != "exact-default-stored":
        raise PosRotDecodeError(f"PosRot.list-default-join: expected=exact-default-stored,actual={audit.get('status')}/{audit.get('parentProofStatus')}")
    if offset < 0 or offset + 4 > len(data):
        raise PosRotDecodeError(f"PosRot.list-count-bounds: offset={offset}")
    count = struct.unpack_from("<i", data, offset)[0]
    if not -1 <= count <= 4096:
        raise PosRotDecodeError(f"PosRot.list-count: expected=-1..4096,actual={count}")
    cursor = offset + 4
    values = None if count == -1 else []
    for _ in range(max(0, count)):
        value, cursor = decode_pos_rot(data, cursor, game_root=game_root)
        values.append(value)
    return values, cursor
