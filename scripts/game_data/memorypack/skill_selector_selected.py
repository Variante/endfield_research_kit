"""Selected-build join for newly reached nested Skill selector routes.

The reviewed selector switch tables are pinned by sibling contracts. For a
requested slot this resolves the selected native branch's type-usage load to
the generated wrapper, then checks its plan. A catalog name alone cannot
admit a child: both the native route and the finite plan must agree.
"""
from __future__ import annotations

import hashlib
import json
import struct
from functools import lru_cache
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.derived_schema import resolve_routes


CATALOG_PATH = CONTRACTS_DIR / "levelscript_union_tags.json"
BASE_CONTRACTS = {
    "SelectorFinder": (
        "skill_selector_finder_typhoea_native.json",
        "endfield.skill-selector-finder-typhoea-native-contract.v1",
    ),
    "SelectorValidator": (
        "skill_selector_validator_in_screen_native.json",
        "endfield.skill-selector-validator-in-screen-native-contract.v1",
    ),
}


@lru_cache(maxsize=1)
def _selected_resolver():
    routes, resolver, audit = resolve_routes()
    if audit.get("status") != "validated" or resolver is None:
        raise ValueError(f"skillSelectorSelected.plan:{audit.get('status')}")
    return resolver, audit


@lru_cache(maxsize=8)
def validate_selected_selector_route(
    family: str, tag: int, *, wrapper_name: str, wrapped_type: str,
    member_name: str, child_type: str,
) -> dict[str, Any]:
    """Prove one nested tag/one-member child without inferring live behavior."""
    validation = validate_selected_selector_route_plan(
        family, tag, wrapper_name=wrapper_name, wrapped_type=wrapped_type,
        members=((member_name, child_type),),
    )
    return {**validation, "memberName": member_name, "childType": child_type}


@lru_cache(maxsize=16)
def validate_selected_selector_route_plan(
    family: str, tag: int, *, wrapper_name: str, wrapped_type: str,
    members: tuple[tuple[str, str], ...],
) -> dict[str, Any]:
    """Prove a selected nested tag and each serialized object member in order."""
    if family not in BASE_CONTRACTS or type(tag) is not int or tag < 0:
        raise ValueError("skillSelectorSelected.family-or-tag")
    if not members or any(
        not isinstance(row, tuple) or len(row) != 2
        or not all(isinstance(value, str) and value for value in row)
        for row in members
    ):
        raise ValueError("skillSelectorSelected.members")
    base_name, base_schema = BASE_CONTRACTS[family]
    base, _ = read_reviewed_contract(
        CONTRACTS_DIR / base_name, schema=base_schema,
        status="exact-current-build", label="skillSelectorSelected",
    )
    catalog = json.loads(CATALOG_PATH.read_bytes())
    rows = catalog.get("families", {}).get(family)
    switch = catalog.get("switches", {}).get(family, {})
    if (
        catalog.get("schema") != "endfield.levelscript-union-tags.v1"
        or not isinstance(rows, list)
        or tag >= len(rows)
        or switch.get("entryCount") != len(rows)
        or switch.get("base") is None
        or catalog.get("nativeInputs", {}).get("gameAssemblySha256")
        != base["nativeInputs"]["GameAssembly.dll"]
        or catalog.get("nativeInputs", {}).get("metadataSha256")
        != base["nativeInputs"]["global-metadata.dat"]
        or rows[tag] != {
            "name": rows[tag].get("name"), "wrapperName": wrapper_name,
            "tag": tag, "memberCount": len(members), "wrappedType": wrapped_type,
        }
    ):
        raise ValueError(f"skillSelectorSelected.catalog:{family}:{tag:#x}")
    expected = base["nativeInputs"]
    gate = check_installed_native_inputs(
        expected["GameAssembly.dll"], expected["global-metadata.dat"],
    )
    if gate.status != NATIVE_EVIDENCE_VALIDATED:
        raise ValueError(f"skillSelectorSelected.native:{gate.status}:{gate.detail}")
    unity = gate.gameassembly.parent / "UnityPlayer.dll"
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected["UnityPlayer.dll"]:
        raise ValueError("skillSelectorSelected.native:UnityPlayer.dll-missing-or-mismatched")
    image = open_native_image(gate.gameassembly, gate.metadata)
    pinned = base["dispatcher"]
    if (
        int(switch["tableVa"], 16) != image.pe.image_base + pinned["switchTableRva"]
        or switch["entryCount"] != pinned["switchEntryCount"]
    ):
        raise ValueError(f"skillSelectorSelected.native:switch-identity:{family}")
    table = image.pe.bytes_at_va(image.pe.image_base + pinned["switchTableRva"], len(rows) * 4)
    if hashlib.sha256(table).hexdigest().upper() != pinned["switchTableSha256"]:
        raise ValueError(f"skillSelectorSelected.native:switch-table-drift:{family}")
    targets = struct.unpack("<" + "I" * len(rows), table)
    target = targets[tag]
    next_target = min((value for value in targets if value > target), default=target + 96)
    branch_length = min(next_target - target, 96)
    if branch_length < 35:
        raise ValueError(f"skillSelectorSelected.native:branch-too-short:{family}:{tag:#x}")
    branch = image.pe.bytes_at_va(image.pe.image_base + target, branch_length)
    # The selected branch checks the existing object and loads the wrapper's
    # type usage before its type check. The later 4C 8B 05 carries a method
    # usage and must not be mistaken for this wrapper identity.
    if branch[:3] not in (b"\x48\x8B\x0E", b"\x48\x8B\x0F") or branch[3:6] != b"\x48\x85\xC9":
        raise ValueError(f"skillSelectorSelected.native:branch-shape:{family}:{tag:#x}")
    instruction = 8
    if branch[instruction:instruction + 3] != b"\x48\x8B\x15":
        raise ValueError(f"skillSelectorSelected.native:type-load-shape:{family}:{tag:#x}")
    cell = image.pe.image_base + target + instruction + 7 + struct.unpack_from("<i", branch, instruction + 3)[0]
    usage = image.pe.bytes_at_va(cell, 8)
    index = unresolved_usage_index(
        usage, image.registration["typesCount"], tag=1,
        source=str(image.gameassembly), offset=cell,
    )
    type_pointer = image.pe.u64_at_va(int(image.registration["types"], 16) + index * 8)
    definition = struct.unpack_from("<Q", image.pe.bytes_at_va(type_pointer, 16))[0]
    if image.type_name(definition) != wrapper_name:
        raise ValueError(f"skillSelectorSelected.native:wrapper-join:{family}:{tag:#x}")

    resolver, audit = _selected_resolver()
    wrapper = resolver.wrappers.get(definition)
    plan = resolver.plans.get(definition)
    if (
        wrapper is None or wrapper.name != wrapper_name
        or wrapper.wrapped_type != wrapped_type
        or not isinstance(plan, tuple) or len(plan) != len(members)
        or any(
            member.name != expected_name or member.kind != "object"
            or member.ref not in resolver.wrappers
            or resolver.wrappers[member.ref].wrapped_type != expected_type
            for member, (expected_name, expected_type) in zip(plan, members)
        )
    ):
        raise ValueError(f"skillSelectorSelected.plan:wrapper-or-child-drift:{family}:{tag:#x}")
    return {
        "status": "validated", "evidenceBoundary": "direct-route-structural-child",
        "family": family, "tag": tag, "wrapperName": wrapper_name,
        "wrappedType": wrapped_type, "memberCount": len(members),
        "members": [
            {"name": name, "childType": child_type} for name, child_type in members
        ],
        "nativeInputs": audit.get("nativeInputs"),
        "switchTableContract": base_name, "catalogContract": CATALOG_PATH.name,
    }
