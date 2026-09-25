"""Load the reviewed Wwise SDK enum contract instead of carrying copies of it.

``scripts/game_data/contracts/wwise_sdk_enums.json`` records the enum names and
values as compiled into Wwise 2023.1.17 -- the exact version the shipped
``AkSoundEngine.dll`` names. Every label table an audio reader derives from that
SDK belongs here, loaded once, rather than hand-copied into a reader
where it can drift away from the contract without anything noticing.

Reading a contract is not the same as proving a field carries it. The contract's
own ``evidenceBoundary`` says so: which bank byte holds which enum is settled per
field by the disassembled deserializer, and a name published here inherits that
boundary. Naming a value is not execution, selection, or audibility.
"""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Mapping

from scripts.common import sha256_file_upper
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.repo_paths import REPO_ROOT

CONTRACT_PATH = CONTRACTS_DIR / "wwise_sdk_enums.json"
CONTRACT_SCHEMA = "endfield.wwise-sdk-enums.v2"


class WwiseEnumContractError(RuntimeError):
    """The pinned SDK enum contract is absent, altered, or the wrong schema."""


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    """Return the reviewed contract, failing closed on any pin mismatch."""
    if not CONTRACT_PATH.is_file():
        raise WwiseEnumContractError(f"Wwise SDK enum contract is missing: {CONTRACT_PATH}")
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8-sig"))
    schema = str(contract.get("schema") or "")
    if schema != CONTRACT_SCHEMA:
        raise WwiseEnumContractError(
            f"Wwise SDK enum contract schema changed: expected={CONTRACT_SCHEMA} actual={schema}"
        )
    if contract.get("status") != "reviewed" or not isinstance(contract.get("enums"), dict):
        raise WwiseEnumContractError("Wwise SDK enum contract is not reviewed or has no enums")
    return contract


@lru_cache(maxsize=None)
def enum_names_by_value(enum: str) -> dict[int, tuple[str, ...]]:
    """Map one contract enum's values to the SDK identifiers that spell them.

    A value can carry several identifiers, because the SDK gives range markers
    (``AkPropID_FirstRtpc``, ``AkActionType_None``) the same value as a real
    member. Returning every spelling keeps that visible instead of letting
    dictionary order pick one.
    """
    enums = load_contract().get("enums") or {}
    if enum not in enums:
        raise WwiseEnumContractError(f"Wwise SDK enum contract has no enum named {enum!r}")
    by_value: dict[int, list[str]] = {}
    for name, value in (enums[enum] or {}).items():
        by_value.setdefault(int(value), []).append(str(name))
    return {value: tuple(names) for value, names in by_value.items()}


def enum_name(enum: str, value: int) -> str | None:
    """Return the shortest SDK identifier for one value, or None when unnamed."""
    names = enum_names_by_value(enum).get(int(value))
    if not names:
        return None
    return min(names, key=lambda name: (len(name), name))


def display_labels(
    enum: str,
    prefix: str,
    *,
    include: tuple[str, ...] = (),
    exclude: tuple[str, ...] = (),
    spellings: Mapping[str, str] | None = None,
    lower_first: bool = False,
) -> dict[int, str]:
    """Derive UI spellings from a reviewed SDK enum without duplicating values.

    ``include``, ``exclude`` and ``spellings`` refer to suffixes after ``prefix``.
    They distinguish actual members from SDK range markers and preserve older
    display spelling. A missing name, duplicate value, or malformed enum is an
    error rather than a reason to publish a guessed label.
    """
    members = load_contract()["enums"].get(enum)
    if not isinstance(members, dict) or not members:
        raise WwiseEnumContractError(f"Wwise SDK enum contract has no enum named {enum!r}")
    if not isinstance(prefix, str) or not prefix:
        raise WwiseEnumContractError(f"Wwise SDK enum {enum!r} requires a prefix")
    suffixes: dict[str, int] = {}
    for name, value in members.items():
        if not isinstance(name, str) or not name.startswith(prefix):
            raise WwiseEnumContractError(f"Wwise SDK enum {enum!r} has unexpected member {name!r}")
        suffixes[name[len(prefix):]] = int(value)
    requested = set(include) | set(exclude) | set(spellings or {})
    missing = requested - suffixes.keys()
    if missing:
        raise WwiseEnumContractError(
            f"Wwise SDK enum {enum!r} is missing requested members: {sorted(missing)}"
        )
    labels: dict[int, str] = {}
    for suffix, value in suffixes.items():
        if (include and suffix not in include) or suffix in exclude:
            continue
        label = (spellings or {}).get(suffix, suffix.replace("_", ""))
        if lower_first:
            label = label[:1].lower() + label[1:]
        if not label or value in labels:
            raise WwiseEnumContractError(
                f"Wwise SDK enum {enum!r} has an empty label or duplicate value {value}"
            )
        labels[value] = label
    return labels


def contract_provenance() -> dict[str, Any]:
    """Return the identity a report publishes so a reader can check the pin."""
    contract = load_contract()
    return {
        "path": CONTRACT_PATH.relative_to(REPO_ROOT).as_posix(),
        "sha256": sha256_file_upper(CONTRACT_PATH),
        "schema": contract.get("schema"),
        "status": contract.get("status"),
        "sdk": (contract.get("provenance") or {}).get("sdk"),
        "evidenceBoundary": contract.get("evidenceBoundary"),
    }
