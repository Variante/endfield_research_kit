"""Exact selected EntityAttachToParent cursor using the reviewed route codec.

`EntityAttachToParent` (14 members) adds, after the inherited action
fields, `child` and `parent` as `Param<EntityPtr>`, `followNodeName` as a
`Param<string>`, `localPos` and `localRot` as `Param<Vector3>`, and
`npcOffsetUseParam` as `Param<bool>`. The selected union branch resolves the
generated wrapper and its `Deserialize` body fixes the member count and
read order (`levelscript_entity_attach_native.json`). Stored attachment
values do not prove a runtime attachment.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR

from .spawner_camera import decode_route_at as _decode_contract_route_at


CONTRACT_PATH = CONTRACTS_DIR / "levelscript_entity_attach_native.json"


def decode_route_at(
    data: bytes, offset: int, family: str, tag: int, *, limit: int | None = None,
    game_root: Path | None = None, strings: Any = None,
) -> tuple[dict[str, Any], int]:
    """Decode one selected attach union at its caller-proven physical offset."""
    return _decode_contract_route_at(
        data, offset, family, tag, limit=limit, contract_path=CONTRACT_PATH,game_root=game_root,strings=strings,
    )
