"""Validate the retained, versioned radio-forbid negative boundary."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


SCHEMA = "radioForbidNegativeBoundary.v1"
DEFAULT_CONTRACT = Path(__file__).with_name("radio_forbid_boundary.json")


class ContractError(RuntimeError):
    """Raised when the retained negative boundary is incomplete or stale-shaped."""


def load_contract(path: Path = DEFAULT_CONTRACT) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load radio-forbid boundary {path}: {exc}") from exc
    if not isinstance(payload, dict) or payload.get("schema") != SCHEMA:
        raise ContractError(f"radio-forbid boundary schema must be {SCHEMA!r}")
    if payload.get("classification") != "no_current_offline_nonempty_radio_id_producer":
        raise ContractError("radio-forbid boundary classification is missing")
    sources = payload.get("sourceFingerprints")
    observations = payload.get("observations")
    if not isinstance(sources, dict) or not isinstance(observations, dict):
        raise ContractError("radio-forbid boundary lacks sources or observations")
    for key in ("gameAssemblySha256", "globalMetadataSha256", "luaCorpusSha256", "ifixPatchSha256"):
        value = sources.get(key)
        if not isinstance(value, str) or len(value) != 64:
            raise ContractError(f"radio-forbid boundary has invalid {key}")
    if observations.get("nonEmptySerializedRadioIds") != 0:
        raise ContractError("radio-forbid boundary no longer proves an empty serialized value set")
    if observations.get("luaRadioParamConstructors") != 0:
        raise ContractError("radio-forbid boundary no longer proves absent Lua constructors")
    if observations.get("relevantActiveIfixTargets") != 0:
        raise ContractError("radio-forbid boundary no longer proves absent IFix replacements")
    return payload


def add_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)


def run(args: argparse.Namespace) -> int:
    try:
        payload = load_contract(args.contract)
    except ContractError as exc:
        print(f"radio-forbid boundary failed: {exc}")
        return 1
    print(
        f"radio-forbid boundary {payload['schema']}: "
        f"{payload['classification']} ({payload['gameBuild']})"
    )
    return 0
