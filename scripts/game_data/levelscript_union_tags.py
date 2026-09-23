"""Current-build LevelScript union tags, looked up by type name.

Every LevelScript record is keyed by ``(union tag, serialized member count)``,
and a client update renumbers the tags: a tag is the type's rank among its
family's wrappers, so any inserted type shifts everything after it. Code that
names a pair as a literal therefore goes stale silently. Name the type
instead and resolve it here.

``contracts/levelscript_union_tags.json`` records, for the three LevelScript
families, every wrapper's tag (read from its native formatter switch by
``memorypack.union_dispatch``) and member count (from
``memorypack.wrapper_members``). It is regenerated, not reviewed row by row:
``--regenerate --write`` rewrites it for the installed build. When the
installed build differs, every lookup returns a unique placeholder that no
scanned record can equal, so consumers stay fail-closed rather than keyed to
another build's numbers.

Run as: python -m scripts.game_data.levelscript_union_tags --regenerate [--write]
"""
from __future__ import annotations

import argparse
import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from scripts.common import NATIVE_EVIDENCE_VALIDATED, check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA = "endfield.levelscript-union-tags.v1"
DEFAULT_CONTRACT = CONTRACTS_DIR / "levelscript_union_tags.json"
FAMILY_BASES = {
    "ActionBase": "Beyond_Gameplay_Actions_ActionBaseForMemoryPack",
    "PureGetter": "Beyond_Gameplay_Actions_PureGetterForMemoryPack",
    "ActionHeader": "Beyond_Gameplay_Actions_ActionHeaderForMemoryPack",
    # Not a LevelScript family, but BuffData and SkillData readers key their
    # ability actions the same way and go stale the same way.
    "AbilityActionData": "Beyond_Gameplay_Core_AbilityAction_AbilityActionDataForMemoryPack",
    "GameCondition": "Beyond_Gameplay_GameConditionForMemoryPack",
    "BaseComponentData": "Beyond_Gameplay_BaseComponentDataForMemoryPack",
    # The selector unions inside every TargetSettings (Buff/Skill finders,
    # validators and post-processors) renumber the same way.
    "SelectorFinder": "Beyond_Gameplay_Core_Selector_Finder_DataForMemoryPack",
    "SelectorValidator": "Beyond_Gameplay_Core_Selector_Validator_DataForMemoryPack",
    "SelectorPostProcessor": "Beyond_Gameplay_Core_Selector_PostProcessor_DataForMemoryPack",
    "LevelScriptModuleData": "Beyond_Gameplay_LevelScriptModuleDataForMemoryPack",
}
_WRAPPER_PREFIXES = ("Beyond.MemoryPack.Beyond_Gameplay_Actions_", "Beyond.MemoryPack.Beyond_Gameplay_")
_WRAPPER_SUFFIX = "ForMemoryPack"


def short_name(wrapper_name: str) -> str:
    """``...Beyond_Gameplay_Actions_IfElseActionForMemoryPack`` -> ``IfElseAction``.

    Members declared directly in ``Beyond.Gameplay`` (``ActiveRopeAnim``) lose
    that shorter prefix instead; ``regenerate`` refuses if two types collide.
    """
    for prefix in _WRAPPER_PREFIXES:
        if wrapper_name.startswith(prefix):
            wrapper_name = wrapper_name[len(prefix):]
            break
    return wrapper_name.removesuffix(_WRAPPER_SUFFIX)


@lru_cache(maxsize=1)
def _load(contract_path: Path = DEFAULT_CONTRACT) -> tuple[dict[str, dict[str, tuple[int, int]]], dict[str, Any]]:
    try:
        contract = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, {"status": "validation_failed", "detail": str(error)[:400]}
    if contract.get("schema") != SCHEMA:
        return {}, {"status": "validation_failed", "detail": f"schema={contract.get('schema')}"}
    inputs = contract.get("nativeInputs") or {}
    native = check_installed_native_inputs(
        str(inputs.get("gameAssemblySha256") or ""), str(inputs.get("metadataSha256") or ""))
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        return {}, {"status": native.status, "detail": native.detail}
    families = {
        family: {row["name"]: (row["tag"], row["memberCount"]) for row in rows}
        for family, rows in (contract.get("families") or {}).items()
    }
    return families, {"status": NATIVE_EVIDENCE_VALIDATED, "detail": ""}


def union_tags_audit() -> dict[str, Any]:
    return dict(_load()[1])


def contract_native_inputs(contract_path: Path = DEFAULT_CONTRACT) -> dict[str, str]:
    """The build the tag contract was regenerated against, uppercase."""
    try:
        inputs = json.loads(Path(contract_path).read_bytes().decode("utf-8-sig")).get("nativeInputs") or {}
    except (OSError, UnicodeError, json.JSONDecodeError):
        return {"gameAssemblySha256": "", "metadataSha256": ""}
    return {key: str(inputs.get(key) or "").upper() for key in ("gameAssemblySha256", "metadataSha256")}


def pair(family: str, name: str) -> tuple[Any, ...]:
    """The current ``(tag, member count)`` of one named type.

    An unknown name or an unvalidated build yields a placeholder tuple that is
    unique per name and can never equal a scanned integer pair, so a dict keyed
    by these stays collision-free and simply never matches.
    """
    found = _load()[0].get(family, {}).get(name)
    return found if found is not None else ("unavailable", family, name)


def action(name: str) -> tuple[Any, ...]:
    return pair("ActionBase", name)


def getter(name: str) -> tuple[Any, ...]:
    return pair("PureGetter", name)


def header(name: str) -> tuple[Any, ...]:
    return pair("ActionHeader", name)


def combined_code(family: str, name: str) -> tuple[Any, ...]:
    """The compact parser's combined ``(tag | members << 8, 0)`` form of a type."""
    found = pair(family, name)
    if isinstance(found[0], int):
        return (found[0] | (found[1] << 8), 0)
    return found


def header_code(name: str) -> tuple[Any, ...]:
    return combined_code("ActionHeader", name)


def action_code(name: str) -> tuple[Any, ...]:
    return combined_code("ActionBase", name)


def name_of(family: str, key: tuple[Any, ...]) -> str:
    """The type a current ``(tag, member count)`` names in one family, or ``""``."""
    for name, value in _load()[0].get(family, {}).items():
        if value == tuple(key):
            return name
    return ""


def wrapper_name(family: str, name: str) -> str:
    """The generated wrapper type behind one named union member, or ``""``."""
    return _wrappers().get(family, {}).get(name, "")


@lru_cache(maxsize=1)
def _wrappers() -> dict[str, dict[str, str]]:
    if _load()[1]["status"] != NATIVE_EVIDENCE_VALIDATED:
        return {}
    contract = json.loads(DEFAULT_CONTRACT.read_bytes().decode("utf-8-sig"))
    return {family: {row["name"]: row.get("wrapperName", "") for row in rows}
            for family, rows in (contract.get("families") or {}).items()}


def names(family: str) -> dict[tuple[int, int], str]:
    """Every current pair of one family, mapped to its type name."""
    return {value: name for name, value in _load()[0].get(family, {}).items()}


def formatter_name_table(family: str = "ActionBase") -> tuple[dict[int, str], dict[str, Any]]:
    """Every current tag of one family mapped to its type name, plus a source audit.

    The audit keeps the shape the Story and Mission Pipeline consumers read:
    ``status``, ``sourceFile``, ``sourceSha256`` (the contract's current bytes,
    recorded as provenance), ``nativeMappingId`` and ``validationFailures``.
    """
    import hashlib

    from scripts.common import repo_path

    audit_state = union_tags_audit()
    raw = DEFAULT_CONTRACT.read_bytes() if DEFAULT_CONTRACT.is_file() else b""
    table = {value[0]: name for value, name in names(family).items()}
    validated = audit_state["status"] == NATIVE_EVIDENCE_VALIDATED and bool(table)
    return (table if validated else {}), {
        "schema": "endfield.levelscript-union-name-table.v1",
        "status": NATIVE_EVIDENCE_VALIDATED if validated else "validation_failed",
        "sourceFile": repo_path(DEFAULT_CONTRACT),
        "sourceSha256": hashlib.sha256(raw).hexdigest().upper(),
        "nativeMappingId": f"levelscript-union-tags-{family.lower()}",
        "summary": {"recoveredTags": len(table) if validated else 0},
        "validationFailures": [] if validated else [
            {"validator": "levelscriptUnionTags", "gate": "installed_native_inputs",
             "expected": NATIVE_EVIDENCE_VALIDATED, "actual": audit_state}],
        "usesOcrOrManualOrder": False,
    }


def regenerate() -> dict[str, Any]:
    from scripts.game_data.il2cpp.native_image import NativeImage
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    from scripts.game_data.memorypack.wrapper_members import derive_from_image

    native = check_installed_native_inputs()
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        raise SystemExit(f"installed native inputs: {native.status}: {native.detail}")
    image = NativeImage(native.gameassembly, native.metadata, label="levelscriptUnionTags")
    wrappers = derive_from_image(image)
    by_name = {wrapper.name: wrapper for wrapper in wrappers.values()}
    families, switches = {}, {}
    for family, base in FAMILY_BASES.items():
        switch = read_union_switch(image, base, wrappers=wrappers)
        switches[family] = {key: switch[key] for key in ("base", "dispatcherVa", "tableVa", "entryCount")}
        families[family] = [
            {"name": short_name(entry["wrapperName"]), "wrapperName": entry["wrapperName"], "tag": entry["tag"],
             "memberCount": len(by_name[entry["wrapperName"]].members),
             "wrappedType": by_name[entry["wrapperName"]].wrapped_type}
            for entry in switch["entries"]
        ]
        seen = [row["name"] for row in families[family]]
        if len(seen) != len(set(seen)):
            raise SystemExit(f"{family}: short names are not unique")
    return {
        "schema": SCHEMA,
        "evidenceBoundary": {
            "exact": "tags from each family's native formatter jump table; member counts from generated wrapper setters",
            "unresolved": "what any record does; this is identity only",
        },
        "nativeInputs": {"gameAssemblySha256": native.gameassembly_sha256.upper(),
                         "metadataSha256": native.metadata_sha256.upper()},
        "switches": switches,
        "families": families,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    args = parser.parse_args(argv)
    if not args.regenerate:
        print(json.dumps(union_tags_audit(), indent=1))
        return 0 if union_tags_audit()["status"] == NATIVE_EVIDENCE_VALIDATED else 1
    contract = regenerate()
    encoded = (json.dumps(contract, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    print(json.dumps({family: len(rows) for family, rows in contract["families"].items()}))
    if args.write:
        args.contract.write_bytes(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
