"""Exact finite readers for selected spawner-event and camera getter unions.

The reviewed native contract supplies tag, member count and field order. This
module reuses ActionSerializedMap's primitive and Param cursors at a caller's
actual offset and never searches for a later record boundary.

Routes in `levelscript_spawner_camera_native.json`: the
`LevelEvent_OnSpawnerComplete` header adds a `Param<SpawnerPtr>` filter and a
separately framed `ParamOutput<SpawnerPtr>` after the inherited event
fields; the `GetMainLevelCameraController` getter has only its seven
inherited node fields. `codecs.levelscript.entity_attach` reuses this
cursor with its own contract. The same rows are also reviewed layouts in
`action_map_layouts.json`. Stored values do not prove gameplay effects.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.levelscript_route_deserialize_native import validate


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_spawner_camera_native.json"
SCHEMA = "endfield.levelscript-route-deserialize-native.v2"


def _contract(path: Path = CONTRACT_PATH) -> dict[str, Any]:
    contract = json.loads(path.read_bytes())
    if (contract.get("schema"), contract.get("status")) != (SCHEMA, "exact-current-build"):
        raise ValueError("levelscriptSpawnerCamera.contract:unsupported-schema")
    return contract


def decode_route_at(
    data: bytes, offset: int, family: str, tag: int, *,
    limit: int | None = None, contract_path: Path = CONTRACT_PATH,
    game_root: Path | None = None, strings: Any = None,
) -> tuple[dict[str, Any], int]:
    """Decode one reviewed union at its exact cursor, bounded by ``limit``."""
    contract = _contract(contract_path)
    root = Path(game_root) if game_root is not None else None
    audit = validate(contract_path=contract_path,
        gameassembly=root.parent/'GameAssembly.dll' if root else None,
        metadata=root/'il2cpp_data/Metadata/global-metadata.dat' if root else None)
    if audit.get('status') != 'validated':
        raise ValueError(f"levelscriptSpawnerCamera.native:actual={audit.get('status')},detail={audit.get('detail',audit.get('nativeGate'))}")
    routes = [row for row in contract["routes"] if (row["family"], row["tag"]) == (family, tag)]
    if len(routes) != 1:
        raise ValueError(f"levelscriptSpawnerCamera.contract:unsupported-route={family}/{tag:#x}")
    route = routes[0]
    if not any(all(row.get(k) == route[k] for k in ('family','tag','wrapperName','memberCount','fields'))
               for row in audit.get('validatedRows',[])):
        raise ValueError('levelscriptSpawnerCamera.native:route-identity')
    end_limit = len(data) if limit is None else limit
    if not 0 <= offset < end_limit <= len(data):
        raise ValueError("levelscriptSpawnerCamera.cursor:outside-input")

    from . import action_map  # The shared cursor, imported here to avoid a cycle.

    cursor = action_map._Cursor(data[:end_limit], offset, game_root=root, strings=strings)
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
    from .node_strings import decode_node_string
    layout = dict(route,nativeGate=contract_path.stem)
    values = {}
    for name,kind in route['fields']:
        if kind == 'string':
            values[name],cursor.offset = decode_node_string(cursor.data,cursor.offset,layout,
                ((contract_path.name,SCHEMA,contract_path.stem),),field=name,game_root=root,strings=strings)
        else:values[name] = cursor.value(kind,f'levelscriptSpawnerCamera.{family}.{name}')
    return {
        "sourceOffset": offset, "endOffset": cursor.offset,
        "unionTag": tag, "memberCount": members,
        "wrapperName": route["wrapperName"], "fields": values,
    }, cursor.offset
