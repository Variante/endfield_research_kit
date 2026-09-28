"""Exact finite readers for selected spawner-event and camera getter unions.

The reviewed native contract supplies tag, member count and field order. This
module reuses ActionSerializedMap's primitive and Param cursors at a caller's
actual offset and never searches for a later record boundary.
"""

from __future__ import annotations

from functools import lru_cache
import json
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_spawner_camera_native.json"
SCHEMA = "endfield.levelscript-route-deserialize-native.v1"


@lru_cache(maxsize=4)
def _contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if contract.get("schema") != SCHEMA:
        raise ValueError("levelscriptSpawnerCamera.contract:unsupported-schema")
    return contract


def decode_route_at(
    data: bytes, offset: int, family: str, tag: int, *,
    limit: int | None = None, contract_path: Path = CONTRACT_PATH,
) -> tuple[dict[str, Any], int]:
    """Decode one reviewed union at its exact cursor, bounded by ``limit``."""
    contract = _contract(contract_path)
    inputs = contract["nativeInputs"]
    gate = check_installed_native_inputs(
        inputs["gameAssembly"]["sha256"], inputs["metadata"]["sha256"],
    )
    if gate.status != "validated":
        raise ValueError(f"levelscriptSpawnerCamera.native:actual={gate.status},detail={gate.detail}")
    routes = [row for row in contract["routes"] if (row["family"], row["tag"]) == (family, tag)]
    if len(routes) != 1:
        raise ValueError(f"levelscriptSpawnerCamera.contract:unsupported-route={family}/{tag:#x}")
    route = routes[0]
    end_limit = len(data) if limit is None else limit
    if not 0 <= offset < end_limit <= len(data):
        raise ValueError("levelscriptSpawnerCamera.cursor:outside-input")

    from . import action_map  # The shared cursor, imported here to avoid a cycle.

    cursor = action_map._Cursor(data[:end_limit], offset)
    physical_tag = cursor.byte(f"levelscriptSpawnerCamera.{family}.tag")
    if physical_tag == 0xFA:
        cursor.need(2, f"levelscriptSpawnerCamera.{family}.wideTag")
        physical_tag = cursor.data[cursor.offset] | cursor.data[cursor.offset + 1] << 8
        cursor.offset += 2
    if physical_tag != tag:
        raise action_map.ActionMapCodecError(
            f"levelscriptSpawnerCamera.{family}:expected-tag={tag:#x},actual={physical_tag:#x}"
        )
    members = cursor.byte(f"levelscriptSpawnerCamera.{family}.memberCount")
    if members != route["memberCount"]:
        raise action_map.ActionMapCodecError(
            f"levelscriptSpawnerCamera.{family}:expected-members={route['memberCount']},actual={members}"
        )
    values = {
        name: cursor.value(kind, f"levelscriptSpawnerCamera.{family}.{name}")
        for name, kind in route["fields"]
    }
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": tag, "memberCount": members,
        "wrapperName": route["wrapperName"], "fields": values,
    }, cursor.offset
