"""Exact current-build ``SetEnablePlayerAction`` field decoder."""

from __future__ import annotations

from typing import Any

from scripts.game_data.codecs.levelscript.params import (
    decode_bool_param,
    decode_i32_param,
)


class SetEnablePlayerActionDecodeError(ValueError):
    """Raised when the selected action no longer matches its exact layout."""


def decode_fields(
    data: bytes,
    cursor: int,
) -> tuple[dict[str, Any], int]:
    """Decode the three generated fields after ``ActionBase``."""

    start = cursor
    fields: dict[str, Any] = {}
    for name, decoder in (
        ("actionMask", decode_i32_param),
        ("advanced", decode_bool_param),
        ("enablePlayerInput", decode_bool_param),
    ):
        decoded = decoder(data, cursor)
        if decoded is None:
            raise SetEnablePlayerActionDecodeError(
                f"SetEnablePlayerAction.{name} did not decode at offset={cursor}"
            )
        fields[name], cursor = decoded
    fields["consumedBytes"] = cursor - start
    return fields, cursor
