"""Build compact gameplay data for the WebUI Gameplay tab.

Run from the repo root:
    python scripts/build_gameplay_data.py
    python scripts/build_gameplay_data.py --languages CN EN JP --default-language CN
"""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
import time
import zlib
from pathlib import Path
from typing import Any

if __package__ == "scripts.gameplay_builder":
    from ..common import EXPORT_ROOT, LANG_DIR, check_installed_native_inputs, rel_path, write_json
    from ..game_data.memorypack.buff import buff_gameplay_semantics
    from ..story_builder.native_protocol import il2cpp
else:
    from common import EXPORT_ROOT, LANG_DIR, check_installed_native_inputs, rel_path, write_json
    from game_data.memorypack.buff import buff_gameplay_semantics
    from story_builder.native_protocol import il2cpp


DEFAULT_TABLE_SOURCE_RELS = (
    ("StreamingAssets", Path("structured") / "StreamingAssets" / "Table"),
    ("Persistent", Path("structured") / "Persistent" / "Table"),
)
DEFAULT_GAMEPLAY_CONFIG_SOURCE_RELS = (
    (
        "StreamingAssets",
        Path("structured") / "StreamingAssets" / "Data" / "Json" / "GameplayConfig",
    ),
    (
        "Persistent",
        Path("structured") / "Persistent" / "Data" / "Json" / "GameplayConfig",
    ),
)
DEFAULT_GAMEPLAY_TAG_INDEX_RELS = (
    (
        "StreamingAssets",
        Path("recovered")
        / "AnimeStudio-cli"
        / "StreamingAssets"
        / "object_index"
        / "parts"
        / "StreamingAssets_animestudio_json_by_type_MonoBehaviour.jsonl",
    ),
    (
        "Persistent",
        Path("recovered")
        / "AnimeStudio-cli"
        / "Persistent"
        / "object_index"
        / "parts"
        / "Persistent_animestudio_json_by_type_MonoBehaviour.jsonl",
    ),
)
PLACEHOLDER_RE = re.compile(r"\{([^}:]+)(?::([^}]+))?\}")
TAG_RE = re.compile(r"</?@[^>]*>|</>|<#[^>]+>")

WEAPON_TYPE_LABELS = {
    "sword": "Sword",
    "claym": "Claymore",
    "lance": "Lance",
    "pistol": "Pistol",
    "funnel": "Funnel",
}

WEAPON_PREFIX_TYPE_IDS = {
    "sword": 1,
    "funnel": 2,
    "claym": 3,
    "lance": 5,
    "pistol": 6,
}

# These CN UseItemTable rows point at shared/stale descriptions in the
# exported I18n table. ItemTable.desc is the authored, item-specific
# activation effect and is localized per build.
ITEM_USE_DESCRIPTION_FROM_ITEM_DESC = frozenset({
    "item_cbp_voucher_pay",
    "item_cbp_voucher_originium",
    "item_resetid_1",
})

SKILL_GROUP_TYPE_LABELS = {
    0: "Normal Attack",
    1: "Skill",
    2: "Ultimate",
    3: "Combo",
}

NODE_TYPE_LABELS = {
    1: "Breakthrough",
    2: "Equipment Break",
    3: "Attribute",
    4: "Passive",
    5: "Factory",
}

TALENT_KIND_LABELS = {
    "attribute": "Attribute",
    "upgrade": "Upgrade",
    "passive": "Passive",
    "equipmentBreak": "Equipment Break",
    "factory": "Factory",
    "other": "Talent",
}

PASSIVE_NODE_RE = re.compile(r"^(?P<base>.+_passive_skill_(?P<rank>\d+))_(?P<level>\d+)$")
FACTORY_NODE_RE = re.compile(r"^fac_(?P<char>chr_.+)_(?P<rank>\d+)_(?P<level>\d+)$")
CHARACTER_NAMESPACE_RE = re.compile(r"^chr_0\d{3}_[a-z0-9]+$", re.IGNORECASE)
CHAR_BREAK_RE = re.compile(r"^charBreak(?P<level>\d+)$")
EQUIP_BREAK_RE = re.compile(r"^equipBreakT(?P<tier>\d+)$")
CURVE_SAMPLE_LEVELS = (1, 20, 40, 60, 70, 80, 90)

CHARACTER_STAT_ATTR_TYPES = (1, 2, 3, 39, 40, 41, 42)
ENEMY_STAT_ATTR_TYPES = (1, 2, 3)
ENEMY_COMBAT_SCALAR_FIELDS = (
    ("physicalDmgResistScalar", "Physical taken scalar"),
    ("fireDmgResistScalar", "Fire taken scalar"),
    ("pulseDmgResistScalar", "Pulse taken scalar"),
    ("crystDmgResistScalar", "Cold taken scalar"),
    ("naturalDmgResistScalar", "Natural taken scalar"),
    ("attackValueAgainstTower", "Tower attack value"),
)
ENEMY_RESILIENCE_FIELDS = (
    ("maxResilience", "Max resilience"),
    ("initialSuperArmor", "Initial super armor"),
    ("zeroPoiseSuperArmor", "Zero-poise super armor"),
    ("superArmorWhenResilienceZero", "Super armor at zero resilience"),
    ("breakingAttackedAtbObtain", "Break ATB gain when attacked"),
    ("resilienceDecreaseWhenHurt", "Resilience decrease when hurt"),
    ("resilienceRecover", "Resilience recovery"),
    ("resilienceRecoverInterval", "Resilience recovery interval"),
    ("resilienceFullRecoverTime", "Full recovery time"),
    ("pushedBackCoefficient", "Pushed-back coefficient"),
)
NATIVE_METADATA_HELPER = Path(__file__).resolve().parents[2] / "tools" / "endfield-il2cpp" / "catalog_option_flow_metadata.py"
NATIVE_MODIFIER_ENUM_TYPES = {
    "attributeTypes": "Beyond.GEnums.AttributeType",
    "modifierTypes": "Beyond.GEnums.ModifierType",
    "modifyAttributeTypes": "Beyond.GEnums.ModifyAttributeType",
    "abilityEvents": "Beyond.Gameplay.Core.AbilitySystem+Event",
    "skillCooldownFunctionTypes": "Beyond.Gameplay.Core.SetSkillCdAtOnce+FunctionType",
    "skillTypeMasks": "Beyond.Gameplay.SkillTypeMask",
}
STAT_ATTR_KEYS = {
    1: "hp",
    2: "atk",
    3: "def",
    4: "physical_damage_taken",
    5: "fire_damage_taken",
    6: "pulse_damage_taken",
    7: "cryst_damage_taken",
    9: "critical_rate",
    17: "normal_attack_efficiency",
    28: "ultimate_skill_efficiency",
    29: "heal_output",
    30: "heal_taken",
    31: "healing_taken_scalar",
    32: "skill_damage",
    33: "combo_skill_damage",
    34: "normal_attack_damage",
    35: "fire_burst_damage",
    36: "pulse_burst_damage",
    37: "cryst_burst_damage",
    38: "natural_burst_damage",
    39: "str",
    40: "agi",
    41: "wis",
    42: "will",
    44: "ultimate_sp_gain",
    48: "natural_damage_taken",
    50: "physical_damage",
    51: "fire_damage",
    52: "pulse_damage",
    53: "cryst_damage",
    54: "natural_damage",
    60: "ether_damage_taken",
    61: "broken_unit_damage",
    80: "physical_damage_taken_scalar",
    81: "natural_damage_taken_scalar",
    82: "cryst_damage_taken_scalar",
    83: "pulse_damage_taken_scalar",
    84: "fire_damage_taken_scalar",
    85: "ether_damage_taken_scalar",
    87: "infliction",
}
STAT_ATTR_LABELS = {
    1: "HP",
    2: "ATK",
    3: "DEF",
    4: "Physical Taken",
    5: "Fire Taken",
    6: "Pulse Taken",
    7: "Cold Taken",
    9: "Critical Rate",
    17: "Normal ATK Efficiency",
    28: "Ultimate Efficiency",
    29: "Heal Output",
    30: "Heal Taken",
    31: "Healing Taken Scalar",
    32: "Skill DMG",
    33: "Combo DMG",
    34: "Normal ATK DMG",
    35: "Fire Burst DMG",
    36: "Pulse Burst DMG",
    37: "Cold Burst DMG",
    38: "Natural Burst DMG",
    39: "STR",
    40: "AGI",
    41: "WIS",
    42: "WILL",
    44: "Ultimate SP Gain",
    48: "Natural Taken",
    50: "Physical DMG",
    51: "Fire DMG",
    52: "Pulse DMG",
    53: "Cold DMG",
    54: "Natural DMG",
    60: "Ether Taken",
    61: "Broken Target DMG",
    80: "Physical Taken Scalar",
    81: "Natural Taken Scalar",
    82: "Cold Taken Scalar",
    83: "Pulse Taken Scalar",
    84: "Fire Taken Scalar",
    85: "Ether Taken Scalar",
    87: "Infliction",
}
COMPOSITE_ATTR_KEYS = {
    "AllDamageTakenScalar": "all_damage_taken_scalar",
    "AllSkillDamageIncrease": "all_skill_damage",
    "CrystAndPulseDamageIncrease": "cryst_pulse_damage",
    "FireAndNaturalDamageIncrease": "fire_natural_damage",
    "Main": "main_attr",
    "SpellDamageIncrease": "spell_damage",
    "Sub": "sub_attr",
}
COMPOSITE_ATTR_LABELS = {
    "AllDamageTakenScalar": "All Damage Taken",
    "AllSkillDamageIncrease": "All Skill DMG",
    "CrystAndPulseDamageIncrease": "Cold / Pulse DMG",
    "FireAndNaturalDamageIncrease": "Fire / Natural DMG",
    "Main": "Main Attribute",
    "SpellDamageIncrease": "Spell DMG",
    "Sub": "Sub Attribute",
}
POTENTIAL_ATTR_BLACKBOARD_KEYS = {
    1: ("MaxHp",),
    2: ("Atk",),
    3: ("Def",),
    29: ("HealOutputIncrease",),
    32: ("NormalSkillDamageIncrease",),
    33: ("ComboSkillDamageIncrease",),
    34: ("NormalAttackDamageIncrease",),
    39: ("Str",),
    40: ("Agi",),
    41: ("Wisd",),
    42: ("Will",),
    50: ("PhysicalDamageIncrease",),
    51: ("FireDamageIncrease",),
    52: ("PulseDamageIncrease",),
    53: ("CrystDamageIncrease",),
    54: ("NaturalDamageIncrease",),
    87: ("PhysicalAndSpellInflictionEnhance",),
}
SKILL_PARAM_BLACKBOARD_KEYS = {
    1: ("costvalue", "costValue"),
    2: ("coolDown", "cooldown", "cd"),
}
EQUIPMENT_PART_LABELS = {
    0: "Body",
    1: "Hand",
    2: "Accessory",
}

HIDDEN_CHARACTER_IDS = {
    "chr_0002_endminm",
    "chr_0003_endminf",
}
CHARACTER_STORY_WIKI_KEYS = {
    "chr_9000_endmin": ["wiki_chr_0002_endminm", "wiki_chr_0003_endminf"],
}

def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build compact WebUI gameplay data from exported Endfield tables.",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=["CN"],
        help="Language codes to build. Defaults to CN.",
    )
    parser.add_argument(
        "--default-language",
        default="CN",
        help="Fallback language for unresolved text.",
    )
    parser.add_argument(
        "--export-root",
        type=Path,
        default=EXPORT_ROOT,
        help="Export root containing structured/{StreamingAssets,Persistent}/Table.",
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=LANG_DIR,
        help="WebUI language data directory.",
    )
    parser.add_argument(
        "--runtime-tag-capture",
        type=Path,
        help=(
            "Hash-gated JSONL produced by capture_runtime_tags.py; merge exact "
            "runtime GameplayTag name/id observations."
        ),
    )
    return parser.parse_args(argv)


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return default


def load_table(table_dir: Path, name: str, default: Any = None) -> Any:
    return read_json(table_dir / name, default if default is not None else {})


def table_source_roots(export_root: Path) -> list[tuple[str, Path]]:
    return [(label, export_root / rel) for label, rel in DEFAULT_TABLE_SOURCE_RELS if (export_root / rel).exists()]


def merge_table_payload(base: Any, overlay: Any) -> Any:
    if isinstance(base, dict) and isinstance(overlay, dict):
        merged = dict(base)
        merged.update(overlay)
        return merged
    if isinstance(base, list) and isinstance(overlay, list):
        return [*base, *overlay]
    return overlay


def load_merged_table(table_roots: list[tuple[str, Path]], name: str, default: Any = None) -> Any:
    found = False
    result: Any = None
    for _label, root in table_roots:
        payload = read_json(root / name, None)
        if payload is None:
            continue
        result = payload if not found else merge_table_payload(result, payload)
        found = True
    if found:
        return result
    if isinstance(default, dict):
        return dict(default)
    if isinstance(default, list):
        return list(default)
    return default if default is not None else {}


def normalize_id(value: Any) -> str:
    if value in (None, ""):
        return ""
    return str(value)


def gameplay_tag_id_hex(value: Any) -> str:
    """Normalize signed/unsigned GameplayTag ids to the WebUI hex form."""

    if value in (None, "") or isinstance(value, bool):
        return ""
    try:
        text = str(value).strip()
        parsed = int(text, 16) if text.lower().startswith("0x") else int(text, 10)
    except (TypeError, ValueError):
        return ""
    return f"0x{parsed & 0xffffffff:08x}"


def _gameplay_tag_ids(value: Any) -> list[str]:
    """Collect tag ids from a config/query tree without assigning semantics."""

    found: list[str] = []

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            if "tagId" in node:
                tag_id = gameplay_tag_id_hex(node.get("tagId"))
                if tag_id:
                    found.append(tag_id)
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return list(dict.fromkeys(found))


def _load_gameplay_tag_config_names(
    export_root: Path,
) -> tuple[
    dict[str, list[str]],
    list[dict[str, str]],
    dict[str, int],
]:
    """Read exact GameplayTagConfig paths from the generated object index.

    The serialized GameplayTag value stores only its integer id.  The Unity
    object index retains the source ``GameplayTagConfig`` string paths, while
    the current client derives ids as CRC32(UTF-8 path).  This is deliberately
    a narrow evidence join: only objects whose ``m_Script`` points at the
    current-build GameplayTagConfig script are considered.
    """

    names: dict[str, list[str]] = {}
    sources: list[dict[str, str]] = []
    evidence = {
        "matchedObjectCount": 0,
        "serializedPathCount": 0,
    }
    script_path_ids: set[str] = set()
    script_glob = (
        export_root
        / "recovered"
        / "AnimeStudio-cli"
    ).glob("*/json_by_type/MonoScript/GameplayTagConfig_p*.json")
    for script_path in script_glob:
        try:
            script_row = json.loads(script_path.read_text(encoding="utf-8"))
            path_id = script_row.get("$animestudio", {}).get("pathId")
            if path_id not in (None, ""):
                script_path_ids.add(str(path_id))
        except (OSError, TypeError, ValueError):
            continue
    if not script_path_ids:
        return names, sources, evidence
    matched_objects: set[tuple[str, str]] = set()
    for label, relative in DEFAULT_GAMEPLAY_TAG_INDEX_RELS:
        path = export_root / relative
        if not path.is_file():
            continue
        source = {"kind": label, "path": rel_path(path)}
        sources.append(source)
        try:
            handle = path.open("r", encoding="utf-8")
        except OSError:
            continue
        with handle:
            for line in handle:
                if (
                    '"recordType":"object"' not in line
                    or not any(path_id in line for path_id in script_path_ids)
                ):
                    continue
                try:
                    row = json.loads(line)
                except (TypeError, ValueError):
                    continue
                pptrs = row.get("pptrs") or []
                if not any(
                    str(pptr.get("pathId")) in script_path_ids
                    for pptr in pptrs
                    if isinstance(pptr, dict)
                ):
                    continue
                object_ref = row.get("object") or {}
                object_key = (
                    str(object_ref.get("serializedFile") or source["path"]),
                    str(object_ref.get("pathId") or ""),
                )
                if object_key not in matched_objects:
                    matched_objects.add(object_key)
                    evidence["matchedObjectCount"] += 1
                for scalar in row.get("scalars") or []:
                    if not isinstance(scalar, list) or len(scalar) < 3:
                        continue
                    field_path, value_type, value = scalar[:3]
                    if value_type != "s" or not isinstance(value, str):
                        continue
                    if not (
                        ".allTags._keyData[" in str(field_path)
                        or ".obsoletes[" in str(field_path)
                    ):
                        continue
                    evidence["serializedPathCount"] += 1
                    tag_id = f"0x{zlib.crc32(value.encode('utf-8')) & 0xffffffff:08x}"
                    rows = names.setdefault(tag_id, [])
                    if value not in rows:
                        rows.append(value)
    for values in names.values():
        values.sort()
    return names, sources, evidence


def _load_runtime_gameplay_tag_names(
    capture_path: Path | None,
) -> tuple[dict[str, list[str]], list[dict[str, str]], dict[str, Any]]:
    """Load a hash-gated runtime name/id capture without guessing semantics."""

    if capture_path is None:
        return {}, [], {}
    path = Path(capture_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"GameplayTag runtime capture not found: {path}")
    session: dict[str, Any] | None = None
    names: dict[str, list[str]] = {}
    mapping_count = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid GameplayTag runtime capture JSON at {path}:{line_number}") from exc
            if not isinstance(row, dict):
                raise ValueError(f"GameplayTag runtime capture row is not an object at {path}:{line_number}")
            if row.get("kind") == "session_start":
                if session is not None:
                    raise ValueError(f"GameplayTag runtime capture has duplicate session_start: {path}")
                session = row
                continue
            if row.get("kind") != "tag_mapping":
                continue
            tag_id = gameplay_tag_id_hex(row.get("tagIdHex") or row.get("tagId"))
            tag_name = row.get("tagName")
            if not tag_id or not isinstance(tag_name, str) or not tag_name:
                continue
            values = names.setdefault(tag_id, [])
            if tag_name not in values:
                values.append(tag_name)
                mapping_count += 1
    if not session:
        raise ValueError(f"GameplayTag runtime capture has no session_start: {path}")
    gameassembly_sha256 = str(session.get("gameAssemblySha256") or "").strip()
    metadata_sha256 = str(session.get("metadataSha256") or "").strip()
    if len(gameassembly_sha256) != 64 or len(metadata_sha256) != 64:
        raise ValueError(
            "GameplayTag runtime capture lacks the required GameAssembly/metadata hashes"
        )
    native = check_installed_native_inputs(
        expected_gameassembly_sha256=gameassembly_sha256,
        expected_metadata_sha256=metadata_sha256,
    )
    if native.status != "validated":
        raise ValueError(
            "GameplayTag runtime capture was not produced by the selected current native pair: "
            + native.detail
        )
    for values in names.values():
        values.sort()
    return (
        names,
        [{"kind": "runtime-gameplay-tag-capture", "path": rel_path(path)}],
        {
            "mappingCount": mapping_count,
            "sessionId": session.get("sessionId") or "",
            "gameBuild": session.get("gameBuild") or "",
        },
    )


def _derive_gameplay_tag_context_names(
    config: dict[str, Any],
) -> tuple[dict[str, list[str]], list[dict[str, str]]]:
    """Derive only names proven by an exact ``tagName2Immune`` context.

    ``GameplayTagPredefineTable`` stores the relationship between a status
    query and its immunity tag ids, but some immunity names are absent from
    the serialized ``GameplayTagConfig`` path list.  The current client uses
    CRC32 of the full path for GameplayTag ids.  For the explicitly observed
    context namespaces below, the corresponding immunity path is therefore a
    proof only when its CRC32 is one of the exact ids in the context.  This is
    deliberately narrower than searching arbitrary names or Buff ids and
    leaves all other ids unresolved.
    """

    names: dict[str, list[str]] = {}
    proofs: list[dict[str, str]] = []
    for context_name, value in (config.get("tagName2Immune") or {}).items():
        if not isinstance(context_name, str):
            continue
        candidate_paths: list[str] = []
        parts = context_name.split("/")
        if (
            len(parts) == 3
            and parts[0] == "Status"
            and parts[1] in {"Immobilized", "Unmovable"}
            and parts[2]
        ):
            candidate_paths.append(f"Immune/{parts[2]}")
        elif context_name.startswith("Skill/Enemy/Common/SpellInflictOnChar/"):
            suffix = context_name.removeprefix("Skill/Enemy/Common/SpellInflictOnChar/")
            if suffix and "/" not in suffix:
                candidate_paths.append(f"Immune/SpellInflictOnChar/{suffix}")
        if not candidate_paths:
            continue
        context_ids = _gameplay_tag_ids(value)
        for candidate in candidate_paths:
            candidate_id = f"0x{zlib.crc32(candidate.encode('utf-8')) & 0xffffffff:08x}"
            if candidate_id not in context_ids:
                continue
            values = names.setdefault(candidate_id, [])
            if candidate not in values:
                values.append(candidate)
            proofs.append(
                {
                    "id": candidate_id,
                    "name": candidate,
                    "context": context_name,
                    "evidenceStatus": "exact-context-derived",
                }
            )
    for values in names.values():
        values.sort()
    proofs.sort(key=lambda item: (item["id"], item["name"], item["context"]))
    return names, proofs


def load_gameplay_tag_registry(
    export_root: Path,
    runtime_capture: Path | None = None,
) -> dict[str, Any]:
    """Load exact current-build GameplayTag names and contexts."""

    config_roots = [
        (label, export_root / relative)
        for label, relative in DEFAULT_GAMEPLAY_CONFIG_SOURCE_RELS
        if (export_root / relative).is_dir()
    ]
    config = load_merged_table(config_roots, "GameplayTagPredefineTable.json", {})
    if not isinstance(config, dict):
        config = {}

    source = [
        {
            "kind": label,
            "path": rel_path(root / "GameplayTagPredefineTable.json"),
        }
        for label, root in config_roots
        if (root / "GameplayTagPredefineTable.json").is_file()
    ]
    direct: dict[str, dict[str, Any]] = {}
    for name, row in (config.get("predefinedTags") or {}).items():
        if not isinstance(row, dict):
            continue
        tag_id = gameplay_tag_id_hex(row.get("tagId"))
        if not tag_id:
            continue
        entry = direct.setdefault(
            tag_id,
            {
                "id": tag_id,
                "names": [],
                "displayNames": [],
                "rawTagIds": [],
                "evidenceStatus": "exact-predefined",
            },
        )
        if str(name) not in entry["names"]:
            entry["names"].append(str(name))
        if str(name) not in entry["displayNames"]:
            entry["displayNames"].append(str(name))
        try:
            raw_tag_id = int(row.get("tagId"))
        except (TypeError, ValueError):
            raw_tag_id = None
        if raw_tag_id is not None and raw_tag_id not in entry["rawTagIds"]:
            entry["rawTagIds"].append(raw_tag_id)

    contexts: dict[str, list[dict[str, str]]] = {}

    def add_context(kind: str, name: str, value: Any) -> None:
        for tag_id in _gameplay_tag_ids(value):
            rows = contexts.setdefault(tag_id, [])
            context = {"kind": kind, "name": str(name)}
            if context not in rows:
                rows.append(context)

    for name, value in (config.get("predefinedQuery") or {}).items():
        add_context("predefinedQuery", str(name), value)
    for name, value in (config.get("tagName2Immune") or {}).items():
        add_context("tagName2Immune", str(name), value)

    derived_names, derived_proofs = _derive_gameplay_tag_context_names(config)
    config_names, config_sources, config_evidence = _load_gameplay_tag_config_names(export_root)
    runtime_names, runtime_sources, runtime_evidence = _load_runtime_gameplay_tag_names(runtime_capture)
    source.extend(
        {
            "kind": f"{item['kind']}-gameplay-tag-config",
            "path": item["path"],
        }
        for item in config_sources
    )
    source.extend(runtime_sources)
    for tag_id, names in config_names.items():
        entry = direct.setdefault(
            tag_id,
            {
                "id": tag_id,
                "names": [],
                "displayNames": [],
                "rawTagIds": [],
                "evidenceStatus": "exact-config",
            },
        )
        for name in names:
            if name not in entry["names"]:
                entry["names"].append(name)
        # Keep the stronger, directly serialized predefined evidence when a
        # path happens to be present in both sources.
        if entry.get("evidenceStatus") != "exact-predefined":
            entry["evidenceStatus"] = "exact-config"

    for tag_id, names in derived_names.items():
        entry = direct.setdefault(
            tag_id,
            {
                "id": tag_id,
                "names": [],
                "displayNames": [],
                "rawTagIds": [],
                "evidenceStatus": "exact-context-derived",
            },
        )
        for name in names:
            if name not in entry["names"]:
                entry["names"].append(name)
        # Keep directly serialized/predefined evidence stronger than the
        # context-derived fallback when both cover the same id.
        if entry.get("evidenceStatus") not in {"exact-predefined", "exact-config"}:
            entry["evidenceStatus"] = "exact-context-derived"

    for tag_id, names in runtime_names.items():
        entry = direct.setdefault(
            tag_id,
            {
                "id": tag_id,
                "names": [],
                "displayNames": [],
                "rawTagIds": [],
                "evidenceStatus": "exact-runtime",
            },
        )
        for name in names:
            if name not in entry["names"]:
                entry["names"].append(name)
        if entry.get("evidenceStatus") not in {"exact-predefined", "exact-config"}:
            entry["evidenceStatus"] = "exact-runtime"

    for tag_id, entry in direct.items():
        entry["names"].sort()
        entry["displayNames"].sort()
        entry["name"] = " / ".join(entry["displayNames"] or entry["names"])
        entry.pop("displayNames", None)
        entry["contexts"] = sorted(
            contexts.get(tag_id, []),
            key=lambda item: (item["kind"], item["name"]),
        )

    if config_names and direct:
        status = "exact-config-and-predefined"
    elif runtime_names and direct:
        status = "exact-runtime-and-predefined"
    elif derived_names and direct:
        status = "exact-context-derived-and-predefined"
    elif direct:
        status = "exact-predefined-partial"
    else:
        status = "unavailable"
    if runtime_names:
        unresolved_reason = "not-in-current-serialized-or-runtime-gameplay-tag-registry"
    elif config_names or derived_names:
        unresolved_reason = "not-in-current-serialized-gameplay-tag-config"
    elif direct:
        unresolved_reason = "serialized-gameplay-tag-config-unavailable"
    else:
        unresolved_reason = "gameplay-tag-registry-unavailable"
    return {
        "status": status,
        "hashAlgorithm": "crc32-utf8-full-path" if (config_names or derived_names) else None,
        "unresolvedReason": unresolved_reason,
        "configEvidence": config_evidence,
        "derivedEvidence": derived_proofs,
        "runtimeEvidence": runtime_evidence,
        "source": source,
        "counts": {
            "predefinedTags": len((config.get("predefinedTags") or {})),
            "mappedTagIds": len(direct),
            "configTagNames": len(config_names),
            "derivedContextTagNames": len(derived_names),
            "configSources": len(config_sources),
            "predefinedQueries": len((config.get("predefinedQuery") or {})),
            "tagName2Immune": len((config.get("tagName2Immune") or {})),
            "contextTagIds": len(contexts),
        },
        "tags": direct,
        "contexts": contexts,
    }


def enrich_buff_gameplay_tag_details(
    record: dict[str, Any],
    gameplay_tag_registry: dict[str, Any] | None,
) -> None:
    """Attach exact registry evidence while retaining every raw tag id."""

    registry = gameplay_tag_registry or {}
    known = registry.get("tags") or {}

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            tag_ids = node.get("tagIds")
            if isinstance(tag_ids, list):
                details = []
                for raw_tag_id in tag_ids:
                    tag_id = gameplay_tag_id_hex(raw_tag_id) or str(raw_tag_id)
                    mapped = known.get(tag_id)
                    if mapped:
                        details.append({
                            "id": tag_id,
                            "name": mapped.get("name") or "",
                            "names": list(mapped.get("names") or []),
                            "contexts": list(mapped.get("contexts") or []),
                            "evidenceStatus": mapped.get("evidenceStatus")
                            or "exact-predefined",
                        })
                    else:
                        details.append({
                            "id": tag_id,
                            "name": "",
                            "names": [],
                            "contexts": list((registry.get("contexts") or {}).get(tag_id) or []),
                            "evidenceStatus": "unresolved",
                            "unresolvedReason": registry.get("unresolvedReason")
                            or "gameplay-tag-registry-unavailable",
                        })
                node["tagDetails"] = details
            for child in node.values():
                visit(child)
        elif isinstance(node, list):
            for child in node:
                visit(child)

    visit(record)


def i18n_text(i18n: dict[str, Any], node: Any, fallback_i18n: dict[str, Any] | None = None) -> str:
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, (int, float)):
        if int(node) == 0:
            return ""
        return str(i18n.get(str(int(node))) or (fallback_i18n or {}).get(str(int(node))) or "")
    if not isinstance(node, dict):
        return ""

    text = node.get("text")
    if text:
        return str(text)
    text_id = node.get("id")
    if text_id in (None, "", 0, "0"):
        return ""
    key = str(text_id)
    return str(i18n.get(key) or (fallback_i18n or {}).get(key) or "")


def text_id(node: Any) -> str:
    if isinstance(node, dict):
        return normalize_id(node.get("id"))
    if isinstance(node, (int, float)):
        return normalize_id(int(node))
    return ""


def clean_text(value: Any) -> str:
    text = TAG_RE.sub("", str(value or ""))
    return text.replace("\\n", "\n").strip()


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", [], {}):
            return value
    return None


def first_i18n_text(i18n: dict[str, Any], fallback_i18n: dict[str, Any], *nodes: Any) -> str:
    for node in nodes:
        text = i18n_text(i18n, node, fallback_i18n)
        if text:
            return text
    return ""


def format_template_value(value: Any, spec: str) -> str:
    number = float(value) if isinstance(value, (int, float)) else None
    if number is not None and spec:
        if "%" in spec:
            decimals = 0
            match = re.search(r"\.(\d+)", spec)
            if match:
                decimals = len(match.group(1))
            return f"{number * 100:.{decimals}f}%"
        if spec == "0":
            return str(int(round(number)))
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6g}"
    return str(value)


def placeholder_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return float(int(value))
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number == number else None


def lookup_placeholder_value(raw: str, values: dict[str, Any]) -> Any:
    if raw in values:
        return values[raw]
    lowered = raw.lower()
    if lowered in values:
        return values[lowered]
    return None


def evaluate_placeholder_expr(node: ast.AST, values: dict[str, Any]) -> float | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Name):
        return placeholder_number(lookup_placeholder_value(node.id, values))
    if isinstance(node, ast.UnaryOp):
        value = evaluate_placeholder_expr(node.operand, values)
        if value is None:
            return None
        if isinstance(node.op, ast.USub):
            return -value
        if isinstance(node.op, ast.UAdd):
            return value
        return None
    if isinstance(node, ast.BinOp):
        left = evaluate_placeholder_expr(node.left, values)
        right = evaluate_placeholder_expr(node.right, values)
        if left is None or right is None:
            return None
        if isinstance(node.op, ast.Add):
            return left + right
        if isinstance(node.op, ast.Sub):
            return left - right
        if isinstance(node.op, ast.Mult):
            return left * right
        if isinstance(node.op, ast.Div) and right != 0:
            return left / right
    return None


def resolve_placeholder(expr: str, values: dict[str, Any]) -> Any:
    raw = expr.strip()
    direct = lookup_placeholder_value(raw, values)
    if direct is not None:
        return direct
    if raw.startswith("1-"):
        value = placeholder_number(lookup_placeholder_value(raw[2:].strip(), values))
        if value is not None:
            return 1 - value
    if raw.startswith("-"):
        value = placeholder_number(lookup_placeholder_value(raw[1:].strip(), values))
        if value is not None:
            return -value
    try:
        parsed = ast.parse(raw, mode="eval")
    except SyntaxError:
        return None
    return evaluate_placeholder_expr(parsed.body, values)


def render_description(template: str, blackboard: list[dict[str, Any]]) -> str:
    values: dict[str, Any] = {}
    for item in blackboard:
        if not isinstance(item, dict) or not item.get("key"):
            continue
        key = str(item.get("key"))
        value = item.get("valueStr") if item.get("valueStr") not in (None, "") else item.get("value")
        values[key] = value
        values.setdefault(key.lower(), value)

    def replace(match: re.Match[str]) -> str:
        value = resolve_placeholder(match.group(1), values)
        if value is None:
            return match.group(0)
        return format_template_value(value, match.group(2) or "")

    return clean_text(PLACEHOLDER_RE.sub(replace, template))


def normalize_blackboard(items: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        key = normalize_id(item.get("key"))
        if not key:
            continue
        value = item.get("valueStr") if item.get("valueStr") not in (None, "") else item.get("value")
        out.append({"key": key, "value": value})
    return out


def skill_level_payload(
    bundle: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    fallback_name: str = "",
    fallback_desc: str = "",
) -> dict[str, Any]:
    blackboard = normalize_blackboard(bundle.get("blackboard"))
    desc_template = i18n_text(i18n, bundle.get("description"), fallback_i18n) or fallback_desc
    sub_names = bundle.get("subDescNameList") or []
    sub_values = bundle.get("subDescList") or []
    sub_desc: list[dict[str, str]] = []
    for idx, label_node in enumerate(sub_names):
        label = i18n_text(i18n, label_node, fallback_i18n)
        value = normalize_id(sub_values[idx]) if idx < len(sub_values) else ""
        if label or value:
            sub_desc.append({"label": label, "value": value})

    return {
        "level": int(bundle.get("level") or 0),
        "name": i18n_text(i18n, bundle.get("skillName"), fallback_i18n) or fallback_name,
        "description": render_description(desc_template, blackboard) if desc_template else "",
        "descriptionTemplate": clean_text(desc_template),
        "blackboard": blackboard,
        "subDesc": sub_desc,
        "coolDown": bundle.get("coolDown"),
        "costType": bundle.get("costType"),
        "costValue": bundle.get("costValue"),
        "maxChargeTime": bundle.get("maxChargeTime"),
        "tagId": normalize_id(bundle.get("tagId")),
        "iconId": normalize_id(bundle.get("iconId")),
    }


def skill_payload(
    skill_id: str,
    skill_table: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    fallback_name: str = "",
    fallback_desc: str = "",
) -> dict[str, Any]:
    row = skill_table.get(skill_id) or {}
    bundles = row.get("SkillPatchDataBundle") if isinstance(row, dict) else []
    levels = [
        skill_level_payload(bundle, i18n, fallback_i18n, fallback_name, fallback_desc)
        for bundle in bundles or []
        if isinstance(bundle, dict)
    ]
    levels.sort(key=lambda item: item.get("level") or 0)
    first = levels[0] if levels else {}
    last = levels[-1] if levels else {}
    return {
        "id": skill_id,
        "name": first.get("name") or fallback_name or skill_id,
        "description": first.get("description") or fallback_desc,
        "maxDescription": last.get("description") or "",
        "levelCount": len(levels),
        "levels": levels,
        "source": {"table": "SkillPatchTable.json", "id": skill_id},
    }


def skill_search_text(skill: dict[str, Any]) -> str:
    parts = [skill.get("id"), skill.get("name"), skill.get("description"), skill.get("maxDescription")]
    blackboard_keys: set[str] = set()
    subdesc_labels: set[str] = set()
    for level in skill.get("levels") or []:
        for item in level.get("blackboard") or []:
            key = normalize_id(item.get("key"))
            if key:
                blackboard_keys.add(key)
        for item in level.get("subDesc") or []:
            label = normalize_id(item.get("label"))
            if label:
                subdesc_labels.add(label)
    parts.extend(sorted(blackboard_keys))
    parts.extend(sorted(subdesc_labels))
    return " ".join(str(part or "") for part in parts)


def weapon_type_token_from_id(weapon_id: str) -> str:
    parts = weapon_id.split("_")
    return parts[1] if len(parts) > 1 else ""


def weapon_type_from_id(weapon_id: str) -> str:
    token = weapon_type_token_from_id(weapon_id)
    return WEAPON_TYPE_LABELS.get(token, token.title()) if token else ""


def weapon_type_id_from_weapon_id(weapon_id: str) -> int | None:
    token = weapon_type_token_from_id(weapon_id)
    return WEAPON_PREFIX_TYPE_IDS.get(token)


def weapon_type_label(type_id: Any, weapon_id: str, text_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> str:
    numeric_type: int | None = None
    try:
        numeric_type = int(type_id) if type_id not in (None, "") else None
    except (TypeError, ValueError):
        numeric_type = None
    if numeric_type is None:
        numeric_type = weapon_type_id_from_weapon_id(weapon_id)
    if numeric_type is not None:
        label = i18n_text(i18n, text_table.get(f"LUA_WEAPON_TYPE_{numeric_type}"), fallback_i18n)
        if label:
            return label
    return weapon_type_from_id(weapon_id)


def item_name(item_table: dict[str, Any], item_id: str, i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> str:
    row = item_table.get(item_id) or {}
    return i18n_text(i18n, row.get("name"), fallback_i18n) if isinstance(row, dict) else ""


def aggregate_skill_blackboard(skills: list[dict[str, Any]]) -> list[dict[str, Any]]:
    values: dict[str, Any] = {}
    for skill in skills:
        for level in skill.get("levels") or []:
            for item in level.get("blackboard") or []:
                if not isinstance(item, dict):
                    continue
                key = normalize_id(item.get("key"))
                if key and key not in values:
                    values[key] = item.get("value")
    return [{"key": key, "value": value} for key, value in values.items()]


def build_weapon_entries(
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> list[dict[str, Any]]:
    weapons = tables["WeaponBasicTable.json"]
    items = tables.get("ItemTable.json") or {}
    skill_table = tables["SkillPatchTable.json"]
    text_table = tables.get("TextTable.json") or {}
    breakthroughs = tables.get("WeaponBreakThroughTemplateTable.json") or {}
    talents = tables.get("WeaponTalentTemplateTable.json") or {}
    upgrades = tables.get("WeaponUpgradeTemplateTable.json") or {}
    upgrade_sums = tables.get("WeaponUpgradeTemplateSumTable.json") or {}
    entries = []
    for weapon_id, row in sorted(weapons.items(), key=lambda item: (item[1].get("rarity", 0), item[0])):
        if not isinstance(row, dict):
            continue
        item_row = items.get(weapon_id) or {}
        item_name = i18n_text(i18n, item_row.get("name"), fallback_i18n) if isinstance(item_row, dict) else ""
        item_desc = i18n_text(i18n, item_row.get("desc"), fallback_i18n) if isinstance(item_row, dict) else ""
        internal_name = i18n_text(i18n, row.get("engName"), fallback_i18n)
        title = item_name or internal_name or weapon_id
        desc = i18n_text(i18n, row.get("weaponDesc"), fallback_i18n)
        skill_ids = [normalize_id(value) for value in row.get("weaponSkillList") or [] if normalize_id(value)]
        skills = [skill_payload(skill_id, skill_table, i18n, fallback_i18n) for skill_id in skill_ids]
        weapon_type_id = row.get("weaponType") if row.get("weaponType") not in (None, "") else weapon_type_id_from_weapon_id(weapon_id)
        weapon_type = weapon_type_label(weapon_type_id, weapon_id, text_table, i18n, fallback_i18n)
        upgrade_payload = weapon_upgrade_payload(row.get("levelTemplateId"), upgrades, upgrade_sums)
        breakthrough_payload = weapon_breakthrough_payload(row.get("breakthroughTemplateId"), breakthroughs, items, i18n, fallback_i18n)
        stat_payload = weapon_stat_curve_payload(row.get("levelTemplateId"), upgrades, breakthrough_payload.get("rows") or [])
        talent_payload = weapon_talent_payload(row.get("talentTemplateId"), talents)
        search = " ".join([
            weapon_id,
            title,
            internal_name,
            item_desc,
            desc,
            weapon_type,
            *(skill_search_text(skill) for skill in skills),
        ])
        entries.append({
            "id": weapon_id,
            "kind": "weapon",
            "title": title,
            "subtitle": weapon_id,
            "fileName": title,
            "internalName": internal_name,
            "itemDescription": clean_text(item_desc),
            "group": f"Weapon / {weapon_type or 'Unknown'}",
            "rarity": row.get("rarity"),
            "weaponType": weapon_type_id,
            "weaponTypeKey": weapon_type_token_from_id(weapon_id),
            "weaponTypeLabel": weapon_type,
            "maxLv": row.get("maxLv"),
            "modelPath": normalize_id(row.get("modelPath")),
            "description": clean_text(desc),
            "skills": skills,
            "breakthrough": breakthrough_payload,
            "talentTemplate": talent_payload,
            "upgrade": upgrade_payload,
            "stats": stat_payload,
            "source": {"table": "WeaponBasicTable.json", "nameTable": "ItemTable.json", "id": weapon_id},
            "storyWikiKey": f"wiki_{weapon_id}",
            "search": search.lower(),
        })
    return entries


def label_lookup(table: dict[str, Any], key: Any, i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> str:
    row = table.get(str(key)) or table.get(key) or {}
    if not isinstance(row, dict):
        return ""
    return i18n_text(i18n, row.get("name"), fallback_i18n)



def row_label_lookup(
    table: dict[str, Any],
    key: Any,
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    fields: tuple[str, ...] = ("name",),
) -> str:
    row = table.get(str(key)) or table.get(key) or {}

    if not isinstance(row, dict):
        return ""
    for field in fields:
        label = i18n_text(i18n, row.get(field), fallback_i18n)
        if label:
            return label
    return ""


def equipment_part_label(item_row: dict[str, Any], showing_types: dict[str, Any], part_type: Any, i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> tuple[Any, str]:
    showing_type = item_row.get("showingType") if isinstance(item_row, dict) else None
    label = row_label_lookup(showing_types, showing_type, i18n, fallback_i18n)
    if label:
        return showing_type, label
    part_value = int_value(part_type)
    fallback = EQUIPMENT_PART_LABELS.get(part_value, f"Part {part_value}" if part_value is not None else "Equipment")
    return showing_type, fallback


def text_table_text(
    text_table: dict[str, Any],
    key: str,
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> str:
    row = text_table.get(key) or {}
    if not isinstance(row, dict):
        return ""
    return i18n_text(i18n, row, fallback_i18n)


def required_item_payload(items: Any, item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        item_id = normalize_id(item.get("id"))
        if not item_id:
            continue
        item_row = item_table.get(item_id) or {}
        name = i18n_text(i18n, item_row.get("name"), fallback_i18n) if isinstance(item_row, dict) else ""
        out.append({"id": item_id, "name": name, "count": item.get("count")})
    return out


def item_ids_counts_payload(item_ids: Any, item_counts: Any, item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for idx, item_id_raw in enumerate(item_ids or []):
        item_id = normalize_id(item_id_raw)
        if not item_id:
            continue
        count = item_counts[idx] if isinstance(item_counts, list) and idx < len(item_counts) else None
        item_row = item_table.get(item_id) or {}
        name = i18n_text(i18n, item_row.get("name"), fallback_i18n) if isinstance(item_row, dict) else ""
        out.append({"id": item_id, "name": name, "count": count})
    return out


def sampled_curve_rows(rows: list[dict[str, Any]], level_field: str, max_level: int | None = None) -> list[dict[str, Any]]:
    if not rows:
        return []
    levels = {int(value) for value in CURVE_SAMPLE_LEVELS}
    if max_level:
        levels.add(int(max_level))
    first_level = rows[0].get(level_field)
    last_level = rows[-1].get(level_field)
    if isinstance(first_level, int):
        levels.add(first_level)
    if isinstance(last_level, int):
        levels.add(last_level)
    out = [row for row in rows if isinstance(row, dict) and row.get(level_field) in levels]
    return sorted(out, key=lambda item: int(item.get(level_field) or 0))


def int_value(value: Any) -> int | None:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def attribute_values(row: dict[str, Any]) -> dict[int, Any]:
    attr_node = row.get("Attribute") if isinstance(row.get("Attribute"), dict) else row
    values: dict[int, Any] = {}
    for item in attr_node.get("attrs") or []:
        if not isinstance(item, dict):
            continue
        attr_type = int_value(item.get("attrType"))
        if attr_type is None:
            continue
        values[attr_type] = item.get("attrValue")
    return values


def stat_attr_payload(attr_type: int | str, value: Any, attr_meta: dict[str, Any] | None = None) -> dict[str, Any]:
    if isinstance(attr_type, int):
        key = STAT_ATTR_KEYS.get(attr_type, f"attr_{attr_type}")
        label = STAT_ATTR_LABELS.get(attr_type, key)
    else:
        key = str(attr_type)
        label = key
    payload: dict[str, Any] = {"type": attr_type, "key": key, "label": label, "value": value}
    if isinstance(attr_type, int) and attr_meta:
        meta = attr_meta.get(str(attr_type)) or attr_meta.get(attr_type) or {}
        if isinstance(meta, dict) and meta.get("iconName"):
            payload["iconName"] = meta.get("iconName")
    return payload


def character_stat_curve_payload(char_row: dict[str, Any], attr_meta: dict[str, Any], playable_max_level: Any = None) -> dict[str, Any]:
    stat_rows = []
    for index, row in enumerate(char_row.get("attributes") or []):
        if not isinstance(row, dict):
            continue
        values = attribute_values(row)
        level = int_value(values.get(0))
        if level is None:
            level = index + 1
        attrs = [
            stat_attr_payload(attr_type, values[attr_type], attr_meta)
            for attr_type in CHARACTER_STAT_ATTR_TYPES
            if attr_type in values
        ]
        if not attrs:
            continue
        stat_rows.append({
            "level": level,
            "breakStage": row.get("breakStage"),
            "attrs": attrs,
        })
    raw_max_level = max((int(row["level"]) for row in stat_rows if row.get("level") is not None), default=None)
    playable_cap = int_value(playable_max_level)
    display_rows = [
        row for row in stat_rows
        if playable_cap is None or int_value(row.get("level")) is None or int_value(row.get("level")) <= playable_cap
    ]
    max_level = max((int(row["level"]) for row in display_rows if row.get("level") is not None), default=None)
    return {
        "source": "CharacterTable.attributes",
        "rowCount": len(display_rows),
        "rawRowCount": len(stat_rows),
        "maxLevel": max_level,
        "rawMaxLevel": raw_max_level,
        "playableMaxLevel": playable_cap,
        "extraRowsBeyondPlayable": max(0, len(stat_rows) - len(display_rows)),
        "rows": display_rows,
        "checkpoints": sampled_curve_rows(display_rows, "level", max_level),
    }


def enemy_stat_curve_payload(attr_row: dict[str, Any], attr_meta: dict[str, Any]) -> dict[str, Any]:
    stat_rows = []
    for row in attr_row.get("levelDependentAttributes") or []:
        if not isinstance(row, dict):
            continue
        values = attribute_values(row)
        level = int_value(values.get(0))
        if level is None:
            # Enemy stat points are source rows, not a curve to reconstruct.
            # A row without its authored level coordinate cannot be displayed
            # honestly, so omit it instead of deriving a level from position.
            continue
        attrs = [
            stat_attr_payload(attr_type, values[attr_type], attr_meta)
            for attr_type in ENEMY_STAT_ATTR_TYPES
            if attr_type in values
        ]
        if not attrs:
            continue
        stat_rows.append({"level": level, "attrs": attrs})
    max_level = max((int(row["level"]) for row in stat_rows if row.get("level") is not None), default=None)
    return {
        "source": "EnemyAttributeTemplateTable.levelDependentAttributes",
        "templateId": normalize_id(attr_row.get("templateId")),
        "rowCount": len(stat_rows),
        "pointCount": len(stat_rows),
        "maxLevel": max_level,
        "interpolated": False,
        "rows": stat_rows,
    }


def enemy_attr_list_payload(node: Any, attr_meta: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(node, dict):
        return []
    values = attribute_values(node)
    return [stat_attr_payload(attr_type, values[attr_type], attr_meta) for attr_type in sorted(values)]


def enemy_modifier_payload(
    items: Any,
    attr_meta: dict[str, Any],
    native_semantics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    native_semantics = native_semantics or {}
    modifier_names = native_semantics.get("modifierTypes") or {}
    target_names = native_semantics.get("modifyAttributeTypes") or {}
    out = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        attr_type = int_value(item.get("attrType"))
        attr = stat_attr_payload(attr_type if attr_type is not None else normalize_id(item.get("attrType")), item.get("attrValue"), attr_meta)
        out.append({
            "attrType": attr_type if attr_type is not None else normalize_id(item.get("attrType")),
            "key": attr.get("key"),
            "label": attr.get("label"),
            "value": item.get("attrValue"),
            "modifierType": item.get("modifierType"),
            "modifierTypeName": modifier_names.get(str(item.get("modifierType"))),
            "modifyAttributeType": item.get("modifyAttributeType"),
            "modifyAttributeTypeName": target_names.get(str(item.get("modifyAttributeType"))),
        })
    return out


def load_native_gameplay_semantics() -> dict[str, Any]:
    """Read current enum meanings only after the selected native pair passes."""

    gate = check_installed_native_inputs()
    evidence = {
        "status": gate.status,
        "detail": gate.detail,
        "source": "selected GameAssembly.dll + global-metadata.dat",
    }
    if not gate.validated:
        return {"evidence": evidence}
    if not NATIVE_METADATA_HELPER.is_file():
        evidence.update({
            "status": "missing",
            "detail": f"metadata helper missing: {NATIVE_METADATA_HELPER}",
        })
        return {"evidence": evidence}
    try:
        helper = il2cpp.load_metadata_helper(NATIVE_METADATA_HELPER)
        metadata = helper.Metadata(gate.metadata)
        defaults = il2cpp.field_defaults(metadata)
        result: dict[str, Any] = {"evidence": evidence}
        for output_key, type_name in NATIVE_MODIFIER_ENUM_TYPES.items():
            result[output_key] = {
                str(row["id"]): str(row["name"])
                for row in il2cpp.enum_members(metadata, defaults, type_name)
            }
        evidence["coverage"] = (
            "current attribute-modifier, ability-event, skill-cooldown function, "
            "and skill-type enum constants"
        )
        return result
    except Exception as exc:
        # Native semantics are optional enrichment.  A corrupt/stale helper or
        # an unexpected metadata layout must degrade this step, never abort the
        # build-independent Gameplay datasets.  Process-control exceptions
        # (KeyboardInterrupt/SystemExit) remain outside Exception.
        evidence.update({
            "status": "parse-error",
            "detail": f"{type(exc).__name__}: {exc}",
        })
        return {"evidence": evidence}


def collect_gameplay_buff_ids(value: Any) -> list[str]:
    """Collect exact buff identifiers already referenced by Gameplay rows."""

    found: set[str] = set()

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            born_buffs = node.get("bornBuffs")
            if isinstance(born_buffs, list):
                found.update(
                    item for item in born_buffs
                    if isinstance(item, str) and re.fullmatch(r"buff_[A-Za-z0-9_]+", item)
                )
            buff_id = node.get("buffId")
            if isinstance(buff_id, str) and re.fullmatch(r"buff_[A-Za-z0-9_]+", buff_id):
                found.add(buff_id)
            effect_id = node.get("id")
            if node.get("type") == "buff" and isinstance(effect_id, str) and re.fullmatch(r"buff_[A-Za-z0-9_]+", effect_id):
                found.add(effect_id)
            for child in node.values():
                visit(child)
            return
        if isinstance(node, list):
            for child in node:
                visit(child)

    visit(value)
    return sorted(found)


def enrich_buff_native_modifier_names(
    record: dict[str, Any],
    native_semantics: dict[str, Any] | None,
) -> None:
    """Attach names only from the current, gated native enum tables."""

    native_semantics = native_semantics or {}
    attribute_names = native_semantics.get("attributeTypes") or {}
    formula_names = native_semantics.get("modifierTypes") or {}
    target_names = native_semantics.get("modifyAttributeTypes") or {}
    attribute_modifier = record.get("attributeModifier") or {}
    for item in attribute_modifier.get("attributeModifiers") or []:
        if not isinstance(item, dict):
            continue
        item["attributeTypeName"] = attribute_names.get(str(item.get("attributeType")))
        item["formulaItemName"] = formula_names.get(str(item.get("formulaItem")))
        item["modifyAttributeTypeName"] = target_names.get(
            str(item.get("modifyAttributeType"))
        )


def enrich_buff_native_action_names(
    record: dict[str, Any],
    native_semantics: dict[str, Any] | None,
) -> None:
    """Attach current-build event/cooldown enum names to exact action rows."""

    native_semantics = native_semantics or {}
    event_names = native_semantics.get("abilityEvents") or {}
    function_names = native_semantics.get("skillCooldownFunctionTypes") or {}
    skill_type_names = native_semantics.get("skillTypeMasks") or {}

    def visit_action_item(item: Any) -> None:
        if not isinstance(item, dict):
            return
        decoded = item.get("decoded") or {}
        if isinstance(decoded, dict) and decoded.get("semanticStatus") == "exact-skill-cooldown-operation":
            decoded["functionTypeName"] = function_names.get(
                str(decoded.get("functionType"))
            )
            decoded["skillTypeMaskName"] = skill_type_names.get(
                str(decoded.get("skillTypeMask"))
            )
        if not isinstance(decoded, dict):
            return
        for key in ("conditionAction", "failActions", "succeedActions"):
            sequence = decoded.get(key) or {}
            for child in sequence.get("actionDataItems") or []:
                visit_action_item(child)

    for event_map in record.get("abilityEventActions") or []:
        if not isinstance(event_map, dict):
            continue
        event_map["abilityEventName"] = event_names.get(
            str(event_map.get("abilityEvent"))
        )
        for sequence in event_map.get("actions") or []:
            if not isinstance(sequence, dict):
                continue
            for item in sequence.get("actionDataItems") or []:
                visit_action_item(item)


def build_gameplay_buff_catalog(
    export_root: Path,
    buff_ids: list[str],
    native_semantics: dict[str, Any] | None = None,
    gameplay_tag_registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve referenced BuffData with Persistent overlay precedence."""

    source_roots = (
        ("StreamingAssets", export_root / "structured" / "StreamingAssets" / "Data" / "Json" / "BuffData"),
        ("Persistent", export_root / "structured" / "Persistent" / "Data" / "Json" / "BuffData"),
    )
    catalog: dict[str, Any] = {}
    for buff_id in buff_ids:
        selected: tuple[str, Path] | None = None
        for source, root in source_roots:
            path = root / f"{buff_id}.json"
            if path.is_file():
                selected = (source, path)
        if selected is None:
            catalog[buff_id] = {
                "id": buff_id,
                "status": "missing",
                "evidenceStatus": "unresolved",
            }
            continue
        source, path = selected
        try:
            record = buff_gameplay_semantics(path)
        except OSError as exc:
            record = {
                "id": buff_id,
                "status": "read-error",
                "evidenceStatus": "unresolved",
                "error": str(exc),
            }
        enrich_buff_native_modifier_names(record, native_semantics)
        enrich_buff_native_action_names(record, native_semantics)
        enrich_buff_gameplay_tag_details(record, gameplay_tag_registry)
        record["source"] = {"kind": source, "path": rel_path(path)}
        catalog[buff_id] = record
    return catalog


def labeled_value_payload(row: dict[str, Any], fields: tuple[tuple[str, str], ...]) -> list[dict[str, Any]]:
    return [
        {"key": field, "label": label, "value": row.get(field)}
        for field, label in fields
        if row.get(field) not in (None, "")
    ]


def enemy_ability_payload(ids: Any, abilities: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for raw_id in ids or []:
        ability_id = normalize_id(raw_id)
        if not ability_id:
            continue
        row = abilities.get(ability_id) or {}
        if not isinstance(row, dict):
            row = {}
        out.append({
            "id": ability_id,
            "name": i18n_text(i18n, row.get("name"), fallback_i18n) or ability_id,
            "description": clean_text(i18n_text(i18n, row.get("description"), fallback_i18n)),
        })
    return out


def enemy_tag_payload(ids: Any, tags: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for raw_id in ids or []:
        tag_id = normalize_id(raw_id)
        if not tag_id:
            continue
        row = tags.get(tag_id) or {}
        label = i18n_text(i18n, row.get("tagText"), fallback_i18n) if isinstance(row, dict) else ""
        out.append({"id": tag_id, "label": label or tag_id})
    return out


def enemy_drop_payload(ids: Any, item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for raw_id in ids or []:
        item_id = normalize_id(raw_id)
        if not item_id:
            continue
        out.append({"id": item_id, "name": item_name(item_table, item_id, i18n, fallback_i18n)})
    return out


def weapon_break_stage_for_level(level: int | None, break_rows: list[dict[str, Any]]) -> Any:
    if level is None:
        return None
    stage = None
    for row in sorted((row for row in break_rows if isinstance(row, dict)), key=lambda item: int_value(item.get("level")) or 0):
        cap_level = int_value(row.get("level"))
        if cap_level is None or cap_level > level:
            continue
        stage = row.get("showLevel")
    return stage


def weapon_stat_curve_payload(template_id_raw: Any, upgrades: dict[str, Any], break_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    template_id = normalize_id(template_id_raw)
    rows = (upgrades.get(template_id) or {}).get("list") or []
    break_rows = break_rows or []
    stat_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = int_value(row.get("weaponLv"))
        if level is None or row.get("baseAtk") in (None, ""):
            continue
        stat_rows.append({
            "level": level,
            "breakStage": weapon_break_stage_for_level(level, break_rows),
            "attrs": [stat_attr_payload("baseAtk", row.get("baseAtk"))],
        })
    max_level = max((int(row["level"]) for row in stat_rows if row.get("level") is not None), default=None)
    return {
        "source": "WeaponUpgradeTemplateTable.baseAtk",
        "templateId": template_id,
        "rowCount": len(stat_rows),
        "maxLevel": max_level,
        "rows": stat_rows,
        "checkpoints": sampled_curve_rows(stat_rows, "level", max_level),
    }

def display_attr_payload(modifier: dict[str, Any], value: Any, attr_meta: dict[str, Any]) -> dict[str, Any]:
    attr_type = int_value(modifier.get("attrType"))
    composite = normalize_id(modifier.get("compositeAttr"))
    attr_key: int | str
    attr_key = COMPOSITE_ATTR_KEYS.get(composite, composite) if composite else (attr_type if attr_type is not None else normalize_id(modifier.get("attrType")))
    payload = stat_attr_payload(attr_key, value, attr_meta)
    if composite and composite in COMPOSITE_ATTR_LABELS:
        payload["label"] = COMPOSITE_ATTR_LABELS[composite]
    payload["attrIndex"] = modifier.get("attrIndex")
    if composite:
        payload["compositeAttr"] = composite
    if attr_type is not None:
        payload["rawAttrType"] = attr_type
    return payload

def equipment_stat_payload(equip_row: dict[str, Any], attr_meta: dict[str, Any]) -> dict[str, Any]:
    modifiers = [item for item in (equip_row.get("equipAttrModifiers") or []) if isinstance(item, dict)]
    max_len = max((len(item.get("attrValues") or []) for item in modifiers), default=0)
    rows = []
    for index in range(max_len):
        attrs = []
        for modifier in sorted(modifiers, key=lambda item: int_value(item.get("attrIndex")) or 0):
            attr_type = int_value(modifier.get("attrType"))
            values = modifier.get("attrValues") or []
            if attr_type is None or attr_type == 0 or index >= len(values):
                continue
            attrs.append(stat_attr_payload(attr_type, values[index], attr_meta))
        if attrs:
            rows.append({"level": index + 1, "attrs": attrs})

    base_modifier = equip_row.get("displayBaseAttrModifier") if isinstance(equip_row.get("displayBaseAttrModifier"), dict) else {}
    display_modifiers = [item for item in (equip_row.get("displayAttrModifiers") or []) if isinstance(item, dict)]
    all_display_modifiers = ([base_modifier] if base_modifier else []) + display_modifiers
    display_attrs = [
        display_attr_payload(item, item.get("attrValue"), attr_meta)
        for item in sorted(all_display_modifiers, key=lambda item: int_value(item.get("attrIndex")) or 0)
        if item.get("attrValue") not in (None, "")
    ]

    modifiers_by_index: dict[int, list[dict[str, Any]]] = {}
    for modifier in modifiers:
        attr_index = int_value(modifier.get("attrIndex"))
        if attr_index is None:
            continue
        modifiers_by_index.setdefault(attr_index, []).append(modifier)

    property_curves = []
    if base_modifier and base_modifier.get("attrValue") not in (None, ""):
        base_payload = display_attr_payload(base_modifier, base_modifier.get("attrValue"), attr_meta)
        property_curves.append({
            "attrIndex": int_value(base_modifier.get("attrIndex")),
            "key": base_payload.get("key"),
            "label": base_payload.get("label"),
            "iconName": base_payload.get("iconName"),
            "compositeAttr": base_payload.get("compositeAttr"),
            "rowCount": 1,
            "maxLevel": 1,
            "rows": [{"level": 1, "attrs": [base_payload]}],
        })
    for modifier in sorted(display_modifiers, key=lambda item: int_value(item.get("attrIndex")) or 0):
        if modifier.get("attrValue") in (None, ""):
            continue
        values = [modifier.get("attrValue"), *(modifier.get("enhancedAttrValues") or [])]
        attr_index = int_value(modifier.get("attrIndex"))
        matching_modifiers = sorted(modifiers_by_index.get(attr_index or -1, []), key=lambda item: int_value(item.get("attrType")) or 0)
        curve_rows = []
        for index, value in enumerate(values):
            attrs = []
            for attr_modifier in matching_modifiers:
                attr_type = int_value(attr_modifier.get("attrType"))
                attr_values = attr_modifier.get("attrValues") or []
                if attr_type is None or attr_type == 0 or index >= len(attr_values):
                    continue
                attrs.append(stat_attr_payload(attr_type, attr_values[index], attr_meta))
            if not attrs:
                attrs = [display_attr_payload(modifier, value, attr_meta)]
            curve_rows.append({"level": index + 1, "attrs": attrs})
        label_payload = display_attr_payload(modifier, modifier.get("attrValue"), attr_meta)
        property_curves.append({
            "attrIndex": attr_index,
            "key": label_payload.get("key"),
            "label": label_payload.get("label"),
            "iconName": label_payload.get("iconName"),
            "compositeAttr": label_payload.get("compositeAttr"),
            "rowCount": len(curve_rows),
            "maxLevel": curve_rows[-1]["level"] if curve_rows else None,
            "rows": curve_rows,
        })

    return {
        "source": "EquipTable.equipAttrModifiers",
        "rowCount": len(rows),
        "maxLevel": rows[-1]["level"] if rows else None,
        "rows": rows,
        "checkpoints": rows,
        "displayAttrs": display_attrs,
        "propertyCurves": property_curves,
    }


def equipment_formula_payload(
    formula: dict[str, Any],
    item_table: dict[str, Any],
    equip_packs: dict[str, Any],
    shop_channels: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> dict[str, Any]:
    if not isinstance(formula, dict) or not formula:
        return {}
    costs = item_ids_counts_payload(formula.get("costItemId"), formula.get("costItemNum"), item_table, i18n, fallback_i18n)
    gold_id = normalize_id(formula.get("costGoldId"))
    if gold_id and formula.get("costGoldNum") not in (None, "", 0):
        costs.insert(0, {
            "id": gold_id,
            "name": item_name(item_table, gold_id, i18n, fallback_i18n),
            "count": formula.get("costGoldNum"),
        })
    formula_id = normalize_id(formula.get("formulaId"))
    outcome_equip_id = normalize_id(formula.get("outcomeEquipId"))
    outcome_name = item_name(item_table, outcome_equip_id, i18n, fallback_i18n)
    pack_id = normalize_id(formula.get("packId"))
    unlock_key = normalize_id(formula.get("unlockKey"))
    return {
        "formulaId": formula_id,
        "formulaName": outcome_name or formula_id,
        "name": outcome_name or formula_id,
        "outcomeEquipId": outcome_equip_id,
        "outcomeEquipName": outcome_name,
        "packId": pack_id,
        "packName": row_label_lookup(equip_packs, pack_id, i18n, fallback_i18n),
        "unlockType": formula.get("unlockType"),
        "unlockValue": formula.get("unlockValue"),
        "unlockKey": unlock_key,
        "unlockName": row_label_lookup(shop_channels, unlock_key, i18n, fallback_i18n, ("channelName", "name")),
        "costs": costs,
    }


def equipment_domain_payload(domain_id: Any, domains: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> dict[str, Any]:
    key = normalize_id(domain_id)
    if not key:
        return {}
    return {
        "id": key,
        "name": row_label_lookup(domains, key, i18n, fallback_i18n, ("domainName", "name")) or key,
        "storageName": row_label_lookup(domains, key, i18n, fallback_i18n, ("storageName",)),
    }

def equipment_suit_lookup(
    equip_suits: dict[str, Any],
    skill_table: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for suit_id, row in equip_suits.items():
        if not isinstance(row, dict):
            continue
        effects = []
        suit_name = ""
        for effect in row.get("list") or []:
            if not isinstance(effect, dict):
                continue
            if not suit_name:
                suit_name = i18n_text(i18n, effect.get("suitName"), fallback_i18n)
            skill_id = normalize_id(effect.get("skillID"))
            effects.append({
                "equipCount": effect.get("equipCnt"),
                "skillId": skill_id,
                "skillLevel": effect.get("skillLv"),
                "suitLogoName": normalize_id(effect.get("suitLogoName")),
                "skill": skill_payload(skill_id, skill_table, i18n, fallback_i18n) if skill_id else {},
            })
        payload = {
            "id": normalize_id(suit_id),
            "name": suit_name or normalize_id(suit_id),
            "effects": effects,
        }
        for equip_id in row.get("equipList") or []:
            equip_key = normalize_id(equip_id)
            if equip_key:
                lookup[equip_key] = payload
    return lookup


def build_equipment_entries(
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> list[dict[str, Any]]:
    equips = tables.get("EquipTable.json") or {}
    items = tables.get("ItemTable.json") or {}
    formulas = tables.get("EquipFormulaTable.json") or {}
    showing_types = tables.get("ItemShowingTypeTable.json") or {}
    equip_packs = tables.get("EquipPackTable.json") or {}
    shop_channels = tables.get("ShopChannelDevelopmentTable.json") or {}
    domains = tables.get("DomainDataTable.json") or {}
    suit_lookup = equipment_suit_lookup(tables.get("EquipSuitTable.json") or {}, tables.get("SkillPatchTable.json") or {}, i18n, fallback_i18n)
    attr_meta = tables.get("AttributeMetaTable.json") or {}
    formula_by_equip = {
        normalize_id(row.get("outcomeEquipId")): row
        for row in formulas.values()
        if isinstance(row, dict) and normalize_id(row.get("outcomeEquipId"))
    }
    entries = []
    for equip_id, row in sorted(equips.items(), key=lambda item: (int_value((items.get(item[0]) or {}).get("rarity")) or 0, item[0])):
        if not isinstance(row, dict):
            continue
        item_row = items.get(equip_id) or {}
        title = i18n_text(i18n, item_row.get("name"), fallback_i18n) if isinstance(item_row, dict) else ""
        desc = i18n_text(i18n, item_row.get("desc"), fallback_i18n) if isinstance(item_row, dict) else ""
        deco_desc = i18n_text(i18n, item_row.get("decoDesc"), fallback_i18n) if isinstance(item_row, dict) else ""
        part_type = int_value(row.get("partType"))
        showing_type, part_label = equipment_part_label(item_row, showing_types, row.get("partType"), i18n, fallback_i18n)
        domain = equipment_domain_payload(row.get("domainId"), domains, i18n, fallback_i18n)
        suit = suit_lookup.get(equip_id) or ({"id": normalize_id(row.get("suitID")), "name": normalize_id(row.get("suitID")), "effects": []} if row.get("suitID") else {})
        formula = equipment_formula_payload(formula_by_equip.get(equip_id) or {}, items, equip_packs, shop_channels, i18n, fallback_i18n)
        stats = equipment_stat_payload(row, attr_meta)
        search = " ".join([
            equip_id,
            title,
            desc,
            deco_desc,
            part_label,
            domain.get("id") or "",
            domain.get("name") or "",
            domain.get("storageName") or "",
            suit.get("id") or "",
            suit.get("name") or "",
            *(effect.get("skillId") or "" for effect in suit.get("effects") or []),
            *(skill_search_text(effect.get("skill") or {}) for effect in suit.get("effects") or []),
            formula.get("formulaName") or "",
            formula.get("packName") or "",
            formula.get("unlockName") or "",
            *(item.get("name") or "" for item in formula.get("costs") or []),
        ])
        entries.append({
            "id": equip_id,
            "kind": "equipment",
            "title": title or equip_id,
            "subtitle": equip_id,
            "group": f"Equipment / {part_label}",
            "rarity": item_row.get("rarity") if isinstance(item_row, dict) else None,
            "partType": part_type,
            "partTypeLabel": part_label,
            "showingType": showing_type,
            "showingTypeLabel": part_label,
            "domainId": domain.get("id") or normalize_id(row.get("domainId")),
            "domainName": domain.get("name") or "",
            "domain": domain,
            "minWearLv": row.get("minWearLv"),
            "suitId": normalize_id(row.get("suitID")),
            "suit": suit,
            "formula": formula,
            "stats": stats,
            "iconId": normalize_id(item_row.get("iconId")) if isinstance(item_row, dict) else "",
            "description": clean_text(desc),
            "itemDescription": clean_text(deco_desc),
            "source": {"table": "EquipTable.json", "nameTable": "ItemTable.json", "id": equip_id},
            "storyWikiKey": f"wiki_{equip_id}",
            "search": search.lower(),
        })
    return entries

def weapon_upgrade_payload(template_id_raw: Any, upgrades: dict[str, Any], upgrade_sums: dict[str, Any]) -> dict[str, Any]:
    template_id = normalize_id(template_id_raw)
    rows = (upgrades.get(template_id) or {}).get("list") or []
    sum_rows = (upgrade_sums.get(template_id) or {}).get("list") or []
    sums_by_level = {row.get("weaponLv"): row for row in sum_rows if isinstance(row, dict)}
    max_row = rows[-1] if rows else {}
    max_level = int_value(max_row.get("weaponLv"))
    checkpoints = []
    for row in sampled_curve_rows([row for row in rows if isinstance(row, dict)], "weaponLv", max_row.get("weaponLv")):
        level = row.get("weaponLv")
        sum_row = sums_by_level.get(level) or {}
        checkpoints.append({
            "level": level,
            "baseAtk": row.get("baseAtk"),
            "lvUpExp": row.get("lvUpExp"),
            "lvUpGold": row.get("lvUpGold"),
            "lvUpExpSum": sum_row.get("lvUpExpSum"),
            "lvUpGoldSum": sum_row.get("lvUpGoldSum"),
        })
    per_level = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        level = row.get("weaponLv")
        sum_row = sums_by_level.get(level) or {}
        per_level.append({
            "level": level,
            "expSum": sum_row.get("lvUpExpSum"),
            "goldSum": sum_row.get("lvUpGoldSum"),
        })
    return {
        "templateId": template_id,
        "rowCount": len(rows),
        "baseAtkAtMax": max_row.get("baseAtk"),
        "maxLevel": max_row.get("weaponLv"),
        "checkpoints": checkpoints,
        "perLevel": per_level,
    }


def weapon_breakthrough_payload(template_id_raw: Any, breakthroughs: dict[str, Any], item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> dict[str, Any]:
    template_id = normalize_id(template_id_raw)
    rows = (breakthroughs.get(template_id) or {}).get("list") or []
    out_rows = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        out_rows.append({
            "level": row.get("breakthroughLv"),
            "showLevel": row.get("breakthroughShowLv"),
            "goldCost": row.get("breakthroughGold"),
            "items": required_item_payload(row.get("breakItemList"), item_table, i18n, fallback_i18n),
            "skillLevelBounds": row.get("skillLevelBounds") or [],
        })
    return {"templateId": template_id, "rowCount": len(rows), "rows": out_rows}


def weapon_talent_payload(template_id_raw: Any, talents: dict[str, Any]) -> dict[str, Any]:
    template_id = normalize_id(template_id_raw)
    rows = (talents.get(template_id) or {}).get("list") or []
    return {
        "templateId": template_id,
        "rowCount": len(rows),
        "rows": [
            {"level": row.get("talentLv"), "skillLevelExtraBounds": row.get("skillLevelExtraBounds") or []}
            for row in rows
            if isinstance(row, dict)
        ],
    }


def character_level_curve_payload(char_level_up: dict[str, Any]) -> dict[str, Any]:
    # CharLevelUpTable rows describe the cost from current level -> next level.
    # Store the cumulative cost on the reached level (level 1 is zero). The
    # final negative sentinel row is metadata, not a playable level.
    rows: list[dict[str, Any]] = [{"level": 1, "exp": 0, "gold": 0, "expSum": 0, "goldSum": 0}]
    exp_sum = 0
    gold_sum = 0
    raw_rows = char_level_up if isinstance(char_level_up, dict) else {}
    sorted_raw_rows = sorted(raw_rows.items(), key=lambda item: int_value(item[0]) if int_value(item[0]) is not None else 999999)
    for start_raw, raw_row in sorted_raw_rows:
        if not isinstance(raw_row, dict):
            continue
        start = int_value(start_raw)
        exp = int_value(raw_row.get("exp"))
        gold = int_value(raw_row.get("gold"))
        if start is None or exp is None or gold is None or exp < 0 or gold < 0:
            continue
        exp_sum += exp
        gold_sum += gold
        rows.append({
            "level": start + 1,
            "exp": exp,
            "gold": gold,
            "expSum": exp_sum,
            "goldSum": gold_sum,
        })
    max_level = rows[-1]["level"] if rows else None
    per_level = [{"level": row["level"], "expSum": row["expSum"], "goldSum": row["goldSum"]} for row in rows]
    return {
        "table": "CharLevelUpTable.json",
        "source": "CharLevelUpTable.json",
        "rowCount": len(raw_rows),
        "maxLevel": max_level,
        "checkpoints": sampled_curve_rows(rows, "level", max_level),
        "perLevel": per_level,
    }


def character_break_stage_payload(tables: dict[str, Any], item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    break_table = tables.get("CharBreakTable.json") or {}
    stage_table = tables.get("CharBreakStageTable.json") or {}
    rows = []
    for key, stage in sorted(stage_table.items(), key=lambda item: int(item[0]) if str(item[0]).isdigit() else 999):
        if not isinstance(stage, dict):
            continue
        break_row = break_table.get(str(key)) or break_table.get(key) or {}
        rows.append({
            "stage": stage.get("breakStage", key),
            "levelRange": [stage.get("minCharLevel"), stage.get("maxCharLevel")],
            "skillCaps": {
                "normalAttack": stage.get("normalAttackSkillLevel"),
                "normalSkill": stage.get("normalSkillLevel"),
                "ultimate": stage.get("ultimateSkillLevel"),
                "combo": stage.get("comboSkillLevel"),
            },
            "breakStatus": break_row.get("breakStatus") if isinstance(break_row, dict) else None,
            "goldCost": break_row.get("goldCost") if isinstance(break_row, dict) else None,
            "availableExpItems": required_item_payload([{"id": item_id, "count": None} for item_id in (break_row.get("availableExpItems") or [])] if isinstance(break_row, dict) else [], item_table, i18n, fallback_i18n),
        })
    return rows


def character_breakthrough_payload(growth_row: dict[str, Any], item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for node_id, row in (growth_row.get("charBreakCostMap") or {}).items():
        if not isinstance(row, dict) or int(row.get("nodeType") or 0) != 1:
            continue
        rows.append({
            "id": normalize_id(node_id),
            "stage": row.get("breakStage"),
            "level": int(re.search(r"(\d+)$", normalize_id(node_id)).group(1)) if re.search(r"(\d+)$", normalize_id(node_id)) else None,
            "equipTierLimit": row.get("equipTierLimit"),
            "name": i18n_text(i18n, row.get("name"), fallback_i18n),
            "description": clean_text(i18n_text(i18n, row.get("description"), fallback_i18n)),
            "requiredItem": required_item_payload(row.get("requiredItem"), item_table, i18n, fallback_i18n),
        })
    rows.sort(key=lambda item: (int(item.get("stage") or 0), int(item.get("level") or 0), str(item.get("id") or "")))
    return rows


def potential_picture_payload(item_id: Any, item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> dict[str, Any] | None:
    # A potential-unlock picture item carries two authored strings beyond its
    # name: `desc` is generic backpack boilerplate ("unlocks the operator's
    # keepsake photo ..."), while `decoDesc` is the actual flavor line/quote
    # shown alongside the photo in-game. Surface `decoDesc` as the sentence.
    normalized_id = normalize_id(item_id)
    if not normalized_id:
        return None
    item = item_table.get(normalized_id)
    if not isinstance(item, dict):
        return {"id": normalized_id, "name": "", "sentence": ""}
    return {
        "id": normalized_id,
        "name": clean_text(i18n_text(i18n, item.get("name"), fallback_i18n)),
        "sentence": clean_text(i18n_text(i18n, item.get("decoDesc"), fallback_i18n)),
    }


def character_potential_payload(char_id: str, tables: dict[str, Any], item_table: dict[str, Any], i18n: dict[str, Any], fallback_i18n: dict[str, Any]) -> dict[str, Any]:
    potentials = tables.get("CharacterPotentialTable.json") or {}
    effects = tables.get("PotentialTalentEffectTable.json") or {}
    row = potentials.get(char_id) or {}
    levels = []
    for item in row.get("potentialUnlockBundle") or []:
        if not isinstance(item, dict):
            continue
        effect_id = normalize_id(item.get("potentialEffectId"))
        effect = effects.get(effect_id) or {}
        desc_template = i18n_text(i18n, effect.get("desc"), fallback_i18n) if isinstance(effect, dict) else ""
        blackboard = potential_effect_blackboard(effect if isinstance(effect, dict) else {})
        pictures = [
            picture for picture in (
                potential_picture_payload(picture_id, item_table, i18n, fallback_i18n)
                for picture_id in item.get("unlockCharPictureItemList") or []
            ) if picture
        ]
        levels.append({
            "level": item.get("level"),
            "name": i18n_text(i18n, item.get("name"), fallback_i18n),
            "potentialEffectId": effect_id,
            "description": render_description(desc_template, blackboard) if desc_template else "",
            "descriptionTemplate": clean_text(desc_template),
            "blackboard": blackboard,
            "requiredItem": item_ids_counts_payload(item.get("itemIds"), item.get("itemCnts"), item_table, i18n, fallback_i18n),
            "unlockCardTopicItem": normalize_id(item.get("unlockCardTopicItem")),
            "unlockCharPictureItemList": [normalize_id(value) for value in item.get("unlockCharPictureItemList") or [] if normalize_id(value)],
            "pictures": pictures,
            "effectRefs": potential_effect_refs(effect if isinstance(effect, dict) else {}),
        })
    return {
        "firstItemId": normalize_id(row.get("firstItemId")),
        "firstItem": required_item_payload([{"id": row.get("firstItemId"), "count": 1}] if row.get("firstItemId") else [], item_table, i18n, fallback_i18n),
        "levels": sorted(levels, key=lambda item: int(item.get("level") or 0)),
    }


def potential_effect_blackboard(effect: dict[str, Any]) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    seen: set[str] = set()

    def append_value(key_raw: Any, value: Any) -> None:
        key = normalize_id(key_raw)
        if key and key not in seen:
            seen.add(key)
            values.append({"key": key, "value": value})

    def add_items(items: Any) -> None:
        for item in normalize_blackboard(items):
            append_value(item.get("key"), item.get("value"))

    for row in effect.get("dataList") or []:
        if not isinstance(row, dict):
            continue
        attach_skill = row.get("attachSkill") if isinstance(row.get("attachSkill"), dict) else {}
        attach_buff = row.get("attachBuff") if isinstance(row.get("attachBuff"), dict) else {}
        add_items(attach_skill.get("blackboard"))
        add_items(attach_buff.get("blackboard"))

        bb_mod = row.get("skillBbModifier") if isinstance(row.get("skillBbModifier"), dict) else {}
        key = normalize_id(bb_mod.get("bbKey"))
        if key:
            value = bb_mod.get("stringValue") if bb_mod.get("stringValue") not in (None, "") else bb_mod.get("floatValue")
            append_value(key, value)

        attr_mod = row.get("attrModifier") if isinstance(row.get("attrModifier"), dict) else {}
        attr_type = int_value(attr_mod.get("attrType"))
        if attr_type is not None:
            attr_value = attr_mod.get("attrValue")
            append_value(f"attr_{attr_type}", attr_value)
            append_value(f"{attr_type},0", attr_value)
            for attr_key in POTENTIAL_ATTR_BLACKBOARD_KEYS.get(attr_type, ()):
                append_value(attr_key, attr_value)

        skill_param = row.get("skillParamModifier") if isinstance(row.get("skillParamModifier"), dict) else {}
        param_type = int_value(skill_param.get("paramType"))
        if param_type is not None:
            param_value = skill_param.get("paramValue")
            append_value(f"param_{param_type}", param_value)
            for param_key in SKILL_PARAM_BLACKBOARD_KEYS.get(param_type, ()):
                append_value(param_key, param_value)
    return values

def potential_effect_refs(effect: dict[str, Any]) -> list[dict[str, str]]:
    refs: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for row in effect.get("dataList") or []:
        if not isinstance(row, dict):
            continue
        attach_skill = row.get("attachSkill") if isinstance(row.get("attachSkill"), dict) else {}
        skill_id = normalize_id(attach_skill.get("skillId"))
        if skill_id and ("skill", skill_id) not in seen:
            seen.add(("skill", skill_id))
            refs.append({"type": "skill", "id": skill_id})
        attach_buff = row.get("attachBuff") if isinstance(row.get("attachBuff"), dict) else {}
        buff_id = normalize_id(attach_buff.get("buffId"))
        if buff_id and ("buff", buff_id) not in seen:
            seen.add(("buff", buff_id))
            refs.append({"type": "buff", "id": buff_id})
    return refs


def spaceship_skill_for_factory_node(
    char_id: str,
    node: dict[str, Any],
    spaceship_char_skills: dict[str, Any],
    spaceship_skills: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    factory = node.get("factorySkillNodeInfo") if isinstance(node.get("factorySkillNodeInfo"), dict) else {}
    index = int(factory.get("index") or 0)
    level = int(factory.get("level") or 0)
    row = spaceship_char_skills.get(char_id) or {}
    expected_suffix = f"_{index + 1}_{level}"
    for item in row.get("skillList") or []:
        if not isinstance(item, dict):
            continue
        skill_id = normalize_id(item.get("skillId"))
        skill = spaceship_skills.get(skill_id) or {}
        skill_level = int(skill.get("level") or 0) if isinstance(skill, dict) else 0
        if int(item.get("skillIndex") or 0) == index and skill_level == level:
            return item, skill if isinstance(skill, dict) else {}
        if skill_id.endswith(expected_suffix):
            return item, skill if isinstance(skill, dict) else {}
    return {}, {}


def build_talent_level_payload(
    char_id: str,
    node_id: str,
    node: dict[str, Any],
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> dict[str, Any]:
    potential_effects = tables.get("PotentialTalentEffectTable.json") or {}
    item_table = tables.get("ItemTable.json") or {}
    char_break_nodes = tables.get("CharBreakNodeTable.json") or {}
    text_table = tables.get("TextTable.json") or {}
    spaceship_char_skills = tables.get("SpaceshipCharSkillTable.json") or {}
    spaceship_skills = tables.get("SpaceshipSkillTable.json") or {}

    node_type = int(node.get("nodeType") or 0)
    passive = node.get("passiveSkillNodeInfo") if isinstance(node.get("passiveSkillNodeInfo"), dict) else {}
    attr = node.get("attributeNodeInfo") if isinstance(node.get("attributeNodeInfo"), dict) else {}
    factory = node.get("factorySkillNodeInfo") if isinstance(node.get("factorySkillNodeInfo"), dict) else {}
    required_items = required_item_payload(node.get("requiredItem"), item_table, i18n, fallback_i18n)

    base_payload: dict[str, Any] = {
        "id": node_id,
        "nodeType": node_type,
        "typeLabel": NODE_TYPE_LABELS.get(node_type, f"Node {node_type}" if node_type else ""),
        "requiredItem": required_items,
        "source": {"table": "CharGrowthTable.json", "id": node_id},
    }

    char_break_match = CHAR_BREAK_RE.match(node_id)
    if char_break_match or node_type == 1:
        break_node = char_break_nodes.get(node_id) or {}
        level_limit = int(char_break_match.group("level")) if char_break_match else 0
        break_stage = int(break_node.get("breakStage") or 0) if isinstance(break_node, dict) else 0
        equip_tier = break_node.get("equipTierLimit") if isinstance(break_node, dict) else None
        break_label = text_table_text(text_table, "LUA_CHAR_BREAK", i18n, fallback_i18n) or "Breakthrough"
        equip_label = text_table_text(text_table, "LUA_CHAR_INFO_TITLE_EQUIP", i18n, fallback_i18n) or "Equipment"
        title = f"{break_label} {level_limit}" if level_limit else f"{break_label} {break_stage}".strip()
        group_title = f"{break_label} / {equip_label}{break_label}" if equip_label else break_label
        base_payload.update({
            "kind": "upgrade",
            "upgradeKind": "characterBreak",
            "kindLabel": break_label,
            "groupTitle": group_title,
            "rank": break_stage,
            "rankIndex": break_stage,
            "level": level_limit or break_stage,
            "sortIndex": level_limit or (break_stage * 20),
            "title": title,
            "description": "",
            "breakStage": break_stage,
            "equipTierLimit": equip_tier,
            "characterLevelLimit": level_limit,
            "source": {"table": "CharBreakNodeTable.json", "id": node_id},
        })
        return base_payload
    passive_match = PASSIVE_NODE_RE.match(node_id)
    if passive_match or node_type == 4:
        effect_id = normalize_id(passive.get("talentEffectId"))
        effect = potential_effects.get(effect_id) or {}
        desc_template = i18n_text(i18n, effect.get("desc"), fallback_i18n)
        blackboard = potential_effect_blackboard(effect if isinstance(effect, dict) else {})
        rank_index = int(passive.get("index") if passive.get("index") is not None else passive_match.group("rank") if passive_match else 0)
        level = int(passive.get("level") or (passive_match.group("level") if passive_match else 0) or 0)
        title = i18n_text(i18n, passive.get("name"), fallback_i18n) or node_id
        base_payload.update({
            "kind": "passive",
            "kindLabel": TALENT_KIND_LABELS["passive"],
            "rank": rank_index + 1,
            "rankIndex": rank_index,
            "level": level,
            "title": title,
            "description": render_description(desc_template, blackboard) if desc_template else "",
            "descriptionTemplate": clean_text(desc_template),
            "blackboard": blackboard,
            "breakStage": passive.get("breakStage"),
            "iconId": normalize_id(passive.get("iconId")),
            "talentEffectId": effect_id,
            "effectRefs": potential_effect_refs(effect if isinstance(effect, dict) else {}),
        })
        return base_payload

    factory_match = FACTORY_NODE_RE.match(node_id)
    if factory_match or node_type == 5:
        skill_ref, skill = spaceship_skill_for_factory_node(char_id, node, spaceship_char_skills, spaceship_skills)
        rank_index = int(factory.get("index") if factory.get("index") is not None else factory_match.group("rank") if factory_match else 0)
        level = int(factory.get("level") or (factory_match.group("level") if factory_match else 0) or skill.get("level") or 0)
        title = i18n_text(i18n, skill.get("talentName"), fallback_i18n) or i18n_text(i18n, skill.get("name"), fallback_i18n) or node_id
        name = i18n_text(i18n, skill.get("name"), fallback_i18n) or title
        desc = i18n_text(i18n, skill.get("desc"), fallback_i18n)
        base_payload.update({
            "kind": "factory",
            "kindLabel": TALENT_KIND_LABELS["factory"],
            "rank": rank_index + 1,
            "rankIndex": rank_index,
            "level": level,
            "title": title,
            "name": name,
            "description": clean_text(desc),
            "breakStage": factory.get("breakStage"),
            "unlockHint": clean_text(i18n_text(i18n, skill_ref.get("unlockHint"), fallback_i18n)),
            "skillId": normalize_id(skill.get("id") or skill_ref.get("skillId")),
            "iconId": normalize_id(skill.get("icon")),
            "roomType": skill.get("roomType"),
            "effectType": skill.get("effectType"),
            "parameters": skill.get("parameters") or [],
            "source": {"table": "SpaceshipSkillTable.json", "id": normalize_id(skill.get("id") or skill_ref.get("skillId")) or node_id},
        })
        return base_payload

    equip_match = EQUIP_BREAK_RE.match(node_id)
    if equip_match or node_type == 2:
        break_node = char_break_nodes.get(node_id) or {}
        tier = int(equip_match.group("tier")) if equip_match else int(break_node.get("equipTierLimit") or 0)
        equip_label = text_table_text(text_table, "LUA_CHAR_INFO_TITLE_EQUIP", i18n, fallback_i18n) or "Equipment"
        break_label = text_table_text(text_table, "LUA_CHAR_BREAK", i18n, fallback_i18n) or "Breakthrough"
        title = f"{equip_label}{break_label} T{tier}" if equip_label or break_label else node_id
        desc = text_table_text(text_table, "LUA_CHAR_INFO_EQUIP_JUMP_TALENT", i18n, fallback_i18n)
        base_payload.update({
            "kind": "upgrade",
            "upgradeKind": "equipmentBreak",
            "kindLabel": TALENT_KIND_LABELS["equipmentBreak"],
            "groupTitle": f"{break_label} / {equip_label}{break_label}" if equip_label else TALENT_KIND_LABELS["upgrade"],
            "rank": tier,
            "rankIndex": tier - 1 if tier else 0,
            "level": tier,
            "sortIndex": (int(break_node.get("breakStage") or tier or 0) * 20) + 5,
            "title": title,
            "description": clean_text(desc),
            "breakStage": break_node.get("breakStage"),
            "equipTierLimit": break_node.get("equipTierLimit"),
            "source": {"table": "CharBreakNodeTable.json", "id": node_id},
        })
        return base_payload

    if node_type == 3:
        attr_mod = (attr.get("attributeModifier") or {}) if isinstance(attr, dict) else {}
        base_payload.update({
            "kind": "attribute",
            "kindLabel": TALENT_KIND_LABELS["attribute"],
            "rank": int(attr.get("breakStage") or 0),
            "rankIndex": int(attr.get("breakStage") or 0),
            "level": int(attr.get("breakStage") or 0),
            "sortIndex": int(attr.get("breakStage") or 0),
            "title": i18n_text(i18n, attr.get("title"), fallback_i18n) or node_id,
            "description": clean_text(i18n_text(i18n, attr.get("desc"), fallback_i18n)),
            "breakStage": attr.get("breakStage"),
            "favorability": attr.get("favorability"),
            "attributeModifier": attr_mod,
        })
        return base_payload

    base_payload.update({
        "kind": "other",
        "kindLabel": TALENT_KIND_LABELS["other"],
        "rank": 0,
        "rankIndex": 0,
        "level": 0,
        "title": node_id,
        "description": "",
    })
    return base_payload


def build_talent_groups(
    char_id: str,
    talent_node_map: dict[str, Any],
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    flat_levels: list[dict[str, Any]] = []
    grouped: dict[str, dict[str, Any]] = {}

    for node_id, node in talent_node_map.items():
        node_id = normalize_id(node_id)
        if not isinstance(node, dict):
            continue
        level = build_talent_level_payload(char_id, node_id, node, tables, i18n, fallback_i18n)
        flat_levels.append(level)
        kind = normalize_id(level.get("kind")) or "other"
        if kind in {"passive", "factory"}:
            group_id = f"{kind}:{char_id}:{level.get('rankIndex', 0)}"
        elif kind in {"attribute", "upgrade"}:
            group_id = f"{kind}:{char_id}"
        else:
            group_id = f"{kind}:{node_id}"

        group = grouped.get(group_id)
        if not group:
            group = {
                "id": group_id,
                "kind": kind,
                "kindLabel": level.get("kindLabel") or TALENT_KIND_LABELS.get(kind, kind),
                "rank": level.get("rank"),
                "rankIndex": level.get("rankIndex"),
                "title": level.get("groupTitle") or TALENT_KIND_LABELS.get(kind, kind) or level.get("title") or node_id,
                "levels": [],
            }
            grouped[group_id] = group
        if kind in {"passive", "factory"} and level.get("title"):
            group["title"] = level.get("title")
        elif kind in {"attribute", "upgrade"} and level.get("groupTitle"):
            group["title"] = level.get("groupTitle")
        group["levels"].append(level)

    for group in grouped.values():
        group["levels"].sort(key=lambda item: (int(item.get("sortIndex") if item.get("sortIndex") is not None else item.get("level") or 0), str(item.get("id") or "")))
        if group["levels"]:
            first = group["levels"][0]
            group.setdefault("title", first.get("title") or first.get("id"))
            if group.get("kind") == "factory":
                group["title"] = first.get("title") or group.get("title")

    order = {"upgrade": 0, "attribute": 1, "passive": 2, "factory": 3, "other": 9}
    groups = sorted(
        grouped.values(),
        key=lambda item: (
            order.get(str(item.get("kind") or "other"), 9),
            int(item.get("rankIndex") or 0),
            int(item.get("rank") or 0),
            str(item.get("id") or ""),
        ),
    )
    return groups, flat_levels

def character_sort_key(char_id: str, row: Any) -> tuple[int, str]:
    if isinstance(row, dict):
        value = row.get("sortOrder")
        try:
            return int(value), char_id
        except (TypeError, ValueError):
            pass
    return 1_000_000, char_id


def game_object_payload(
    object_id_raw: Any,
    count: Any,
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> dict[str, Any]:
    object_id = normalize_id(object_id_raw)
    item_table = tables.get("ItemTable.json") or {}
    char_table = tables.get("CharacterTable.json") or {}
    kind = "item"
    name = ""
    if object_id.startswith("chr_"):
        kind = "character"
        row = char_table.get(object_id) if isinstance(char_table.get(object_id), dict) else {}
        name = i18n_text(i18n, row.get("name"), fallback_i18n) if row else ""
    elif object_id.startswith("wpn_"):
        kind = "weapon"
        row = item_table.get(object_id) if isinstance(item_table.get(object_id), dict) else {}
        name = i18n_text(i18n, row.get("name"), fallback_i18n) if row else ""
    elif object_id.startswith("item_equip_"):
        kind = "equipment"
        row = item_table.get(object_id) if isinstance(item_table.get(object_id), dict) else {}
        name = i18n_text(i18n, row.get("name"), fallback_i18n) if row else ""
    elif object_id in item_table and isinstance(item_table.get(object_id), dict):
        name = i18n_text(i18n, item_table[object_id].get("name"), fallback_i18n)
    return {"id": object_id, "name": name, "count": count, "kind": kind}


def description_reward_quantity_overrides(
    description: str,
    item_table: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> dict[str, list[int]]:
    """Recover authored quantity variants from an item's use description.

    A few usable reward items intentionally leave RewardTable.count at zero
    because the actual quantity is presented as a list in the item text (for
    example, the three fortune-ticket outcomes).  Preserve those authored
    values in the compact Gameplay payload instead of exposing a misleading
    zero quantity.
    """
    names = {
        item_name(item_table, item_id, i18n, fallback_i18n): item_id
        for item_id in item_table
        if item_name(item_table, item_id, i18n, fallback_i18n)
    }
    overrides: dict[str, list[int]] = {}
    for raw_line in clean_text(description).splitlines():
        line = raw_line.strip()
        match = re.match(r"^-?\s*(.+?)\s*[\u00d7x]\s*(\d+(?:\.\d+)?)\s*$", line, re.IGNORECASE)
        if not match:
            continue
        item_id = names.get(match.group(1).strip())
        if not item_id:
            continue
        count = float(match.group(2))
        if count.is_integer() and count > 0:
            overrides.setdefault(item_id, []).append(int(count))
    return overrides


def reward_bundle_payload(
    bundles: Any,
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    quantity_overrides: dict[str, list[int]] | None = None,
) -> list[dict[str, Any]]:
    out = []
    for bundle in bundles or []:
        if not isinstance(bundle, dict):
            continue
        object_id = normalize_id(bundle.get("id"))
        if not object_id:
            continue
        override_counts = (quantity_overrides or {}).get(object_id) or []
        if override_counts:
            out.extend(game_object_payload(object_id, count, tables, i18n, fallback_i18n) for count in override_counts)
            continue
        raw_count = bundle.get("count")
        count = None if raw_count in (0, 0.0, "0") else raw_count
        out.append(game_object_payload(object_id, count, tables, i18n, fallback_i18n))
    return out


def reward_quantities_unavailable(
    bundles: Any,
    quantity_overrides: dict[str, list[int]] | None = None,
) -> bool:
    """Report missing quantities without filling them from external guesses."""
    found_bundle = False
    for bundle in bundles or []:
        if not isinstance(bundle, dict):
            continue
        object_id = normalize_id(bundle.get("id"))
        if not object_id:
            continue
        found_bundle = True
        if (quantity_overrides or {}).get(object_id):
            return False
        raw_count = bundle.get("count")
        if raw_count not in (None, "", 0, 0.0, "0"):
            return False
    return found_bundle


def reward_payload(
    reward_id_raw: Any,
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    quantity_overrides: dict[str, list[int]] | None = None,
) -> dict[str, Any]:
    reward_id = normalize_id(reward_id_raw)
    rewards = tables.get("RewardTable.json") or {}
    row = rewards.get(reward_id) if isinstance(rewards.get(reward_id), dict) else {}
    item_bundles = row.get("itemBundles") if isinstance(row, dict) else []
    probable_bundles = row.get("probItemBundles") if isinstance(row, dict) else []
    return {
        "id": reward_id,
        "quantityDataUnavailable": reward_quantities_unavailable(
            [*(item_bundles or []), *(probable_bundles or [])], quantity_overrides
        ),
        "items": reward_bundle_payload(item_bundles, tables, i18n, fallback_i18n, quantity_overrides),
        "probableItems": reward_bundle_payload(probable_bundles, tables, i18n, fallback_i18n, quantity_overrides),
    }


def prefixed_blackboard(prefix: str, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not prefix:
        return []
    return [
        {"key": f"{prefix}\\{item.get('key')}", "value": item.get("value")}
        for item in items or []
        if item.get("key")
    ]


def item_use_action_payload(action: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    buff_data = action.get("buffBBData") if isinstance(action.get("buffBBData"), dict) else {}
    skill_data = action.get("skillBBData") if isinstance(action.get("skillBBData"), dict) else {}
    buff_id = normalize_id(buff_data.get("buffId"))
    skill_id = normalize_id(skill_data.get("skillId"))
    buff_blackboard = normalize_blackboard(buff_data.get("blackboard"))
    skill_blackboard = normalize_blackboard(skill_data.get("blackboard"))
    desc_blackboard = [
        *buff_blackboard,
        *skill_blackboard,
        *prefixed_blackboard(buff_id, buff_blackboard),
        *prefixed_blackboard(skill_id, skill_blackboard),
    ]
    return {
        "useType": action.get("useType"),
        "buffId": buff_id,
        "skillId": skill_id,
        "skillPath": normalize_id(skill_data.get("skillPath")),
        "buffBlackboard": buff_blackboard,
        "skillBlackboard": skill_blackboard,
    }, desc_blackboard


def common_item_payload(
    item_id: str,
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    story_wiki_titles: dict[str, str] | None = None,
) -> dict[str, Any]:
    item_table = tables.get("ItemTable.json") or {}
    item_types = tables.get("ItemTypeTable.json") or {}
    showing_types = tables.get("ItemShowingTypeTable.json") or {}
    story_wiki_titles = story_wiki_titles or {}
    row = item_table.get(item_id) if isinstance(item_table.get(item_id), dict) else {}
    item_type = row.get("type") if isinstance(row, dict) else None
    showing_type = row.get("showingType") if isinstance(row, dict) else None
    item_type_label = row_label_lookup(item_types, item_type, i18n, fallback_i18n)
    showing_type_label = row_label_lookup(showing_types, showing_type, i18n, fallback_i18n)
    title = i18n_text(i18n, row.get("name"), fallback_i18n) if isinstance(row, dict) else ""
    title = title or story_wiki_titles.get(f"wiki_{item_id}", "") or item_id
    return {
        "id": item_id,
        "title": title,
        "subtitle": item_id,
        "fileName": title if title != item_id else "",
        "itemType": item_type,
        "itemTypeLabel": item_type_label,
        "showingType": showing_type,
        "showingTypeLabel": showing_type_label,
        "rarity": row.get("rarity") if isinstance(row, dict) else None,
        "iconId": normalize_id(row.get("iconId")) if isinstance(row, dict) else "",
        "iconCompositeId": normalize_id(row.get("iconCompositeId")) if isinstance(row, dict) else "",
        "modelKey": normalize_id(row.get("modelKey")) if isinstance(row, dict) else "",
        "maxStackCount": row.get("maxStackCount") if isinstance(row, dict) else None,
        "maxBackpackStackCount": row.get("maxBackpackStackCount") if isinstance(row, dict) else None,
        "backpackCanDiscard": row.get("backpackCanDiscard") if isinstance(row, dict) else None,
        "description": clean_text(i18n_text(i18n, row.get("desc"), fallback_i18n)) if isinstance(row, dict) else "",
        "decoDescription": clean_text(i18n_text(i18n, row.get("decoDesc"), fallback_i18n)) if isinstance(row, dict) else "",
        "storyWikiKey": f"wiki_{item_id}",
    }


def build_usable_item_entries(
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    story_wiki_titles: dict[str, str] | None = None,
) -> list[dict[str, Any]]:
    use_items = tables.get("UseItemTable.json") or {}
    chest_items = tables.get("UsableItemChestTable.json") or {}
    entries = []

    for item_id, row in sorted(use_items.items()):
        if not isinstance(row, dict):
            continue
        item_id = normalize_id(row.get("itemId")) or normalize_id(item_id)
        base = common_item_payload(item_id, tables, i18n, fallback_i18n, story_wiki_titles)
        actions = []
        desc_blackboard: list[dict[str, Any]] = []
        for action in row.get("useActions") or []:
            if not isinstance(action, dict):
                continue
            action_payload, action_desc_blackboard = item_use_action_payload(action)
            actions.append(action_payload)
            desc_blackboard.extend(action_desc_blackboard)
        desc_template = i18n_text(i18n, row.get("itemUseDesc"), fallback_i18n)
        use_description = render_description(desc_template, desc_blackboard) if desc_template else ""
        effective_description_template = clean_text(desc_template)
        if item_id in ITEM_USE_DESCRIPTION_FROM_ITEM_DESC and base.get("description"):
            use_description = base.get("description") or use_description
            effective_description_template = base.get("description") or effective_description_template
        search = " ".join([
            item_id,
            base.get("title") or "",
            base.get("itemTypeLabel") or "",
            base.get("showingTypeLabel") or "",
            base.get("description") or "",
            use_description,
            *(action.get("buffId") or "" for action in actions),
            *(action.get("skillId") or "" for action in actions),
            *(bb.get("key") or "" for action in actions for bb in (action.get("buffBlackboard") or [])),
            *(bb.get("key") or "" for action in actions for bb in (action.get("skillBlackboard") or [])),
        ])
        entries.append({
            **base,
            "kind": "item",
            "group": f"Item / {base.get('showingTypeLabel') or base.get('itemTypeLabel') or 'Usable'}",
            "useCategory": "use",
            "useData": {
                "duration": row.get("duration"),
                "effectType": row.get("effectType"),
                "isPersistentBuff": row.get("isPersistentBuff"),
                "isValuableDepot": row.get("isValuableDepot"),
                "stackingKey": normalize_id(row.get("stackingKey")),
                "targetNumType": row.get("targetNumType"),
                "uiType": row.get("uiType"),
                "description": use_description,
                "descriptionTemplate": effective_description_template,
                "actions": actions,
            },
            "source": {"table": "UseItemTable.json", "nameTable": "ItemTable.json", "id": item_id},
            "search": search.lower(),
        })

    for item_id, row in sorted(chest_items.items()):
        if not isinstance(row, dict):
            continue
        item_id = normalize_id(row.get("id")) or normalize_id(item_id)
        base = common_item_payload(item_id, tables, i18n, fallback_i18n, story_wiki_titles)
        random_items = item_ids_counts_payload(row.get("randomChestItemIds"), row.get("randomChestItemCounts"), tables.get("ItemTable.json") or {}, i18n, fallback_i18n)
        quantity_overrides = description_reward_quantity_overrides(
            base.get("description") or "",
            tables.get("ItemTable.json") or {},
            i18n,
            fallback_i18n,
        )
        rewards = []
        for reward_id_raw in row.get("rewardIdList") or []:
            reward_id = normalize_id(reward_id_raw)
            if not reward_id:
                continue
            rewards.append(reward_payload(
                reward_id,
                tables,
                i18n,
                fallback_i18n,
                quantity_overrides,
            ))
        search = " ".join([
            item_id,
            base.get("title") or "",
            base.get("itemTypeLabel") or "",
            base.get("showingTypeLabel") or "",
            base.get("description") or "",
            *(item.get("name") or item.get("id") or "" for item in random_items),
            *(reward.get("id") or "" for reward in rewards),
            *(item.get("name") or item.get("id") or "" for reward in rewards for item in (reward.get("items") or [])),
            *(item.get("name") or item.get("id") or "" for reward in rewards for item in (reward.get("probableItems") or [])),
        ])
        entries.append({
            **base,
            "kind": "item",
            "group": f"Item / {base.get('itemTypeLabel') or base.get('showingTypeLabel') or 'Chest'}",
            "useCategory": "chest",
            "chestData": {
                "type": row.get("type"),
                "selectedCount": row.get("selectedCount"),
                "randomItems": random_items,
                "rewards": rewards,
            },
            "source": {"table": "UsableItemChestTable.json", "nameTable": "ItemTable.json", "id": item_id},
            "search": search.lower(),
        })
    return entries

def build_enemy_entries(
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
    story_wiki_titles: dict[str, str] | None = None,
    native_semantics: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    enemies = tables.get("EnemyTable.json") or {}
    attr_templates = tables.get("EnemyAttributeTemplateTable.json") or {}
    display_infos = tables.get("EnemyDisplayInfoTable.json") or {}
    template_display_infos = tables.get("EnemyTemplateDisplayInfoTable.json") or {}
    display_types = tables.get("DisplayEnemyTypeTable.json") or {}
    ability_descs = tables.get("EnemyAbilityDescTable.json") or {}
    enemy_tags = tables.get("EnemyTagTable.json") or {}
    drop_table = tables.get("WikiEnemyDropTable.json") or {}
    item_table = tables.get("ItemTable.json") or {}
    attr_meta = tables.get("AttributeMetaTable.json") or {}
    story_wiki_titles = story_wiki_titles or {}

    def dedupe_values(values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            key = normalize_id(value)
            if not key or key in seen:
                continue
            seen.add(key)
            result.append(key)
        return result

    def dedupe_payloads(values: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen = set()
        result = []
        for value in values:
            key = json.dumps(value, sort_keys=True, ensure_ascii=False)
            if key in seen:
                continue
            seen.add(key)
            result.append(value)
        return result

    grouped: dict[str, list[tuple[str, dict[str, Any]]]] = {}
    for enemy_id, row in sorted(enemies.items()):
        if not isinstance(row, dict):
            continue
        template_id = normalize_id(row.get("templateId")) or enemy_id
        grouped.setdefault(template_id, []).append((enemy_id, row))

    entries = []
    for template_id, variant_rows in sorted(grouped.items()):
        primary_id, primary_row = next(((enemy_id, row) for enemy_id, row in variant_rows if enemy_id == template_id), variant_rows[0])
        display = display_infos.get(primary_id) if isinstance(display_infos.get(primary_id), dict) else {}
        template_display = template_display_infos.get(template_id) if isinstance(template_display_infos.get(template_id), dict) else {}
        wiki_title = story_wiki_titles.get(f"wiki_{template_id}", "")
        display_name = first_i18n_text(i18n, fallback_i18n, display.get("name"))
        template_name = first_i18n_text(i18n, fallback_i18n, template_display.get("name")) or wiki_title or template_id
        title = display_name or wiki_title or template_name or template_id
        nickname = first_i18n_text(i18n, fallback_i18n, display.get("nickname"), template_display.get("nickname"))
        description = clean_text(first_i18n_text(i18n, fallback_i18n, display.get("description"), template_display.get("description")))
        display_type = first_non_empty(display.get("displayType"), template_display.get("displayType"))
        display_type_label = row_label_lookup(display_types, display_type, i18n, fallback_i18n) or (f"Type {display_type}" if display_type not in (None, "") else "")
        ability_ids = first_non_empty(display.get("abilityDescIds"), template_display.get("abilityDescIds"), []) or []
        abilities = enemy_ability_payload(ability_ids, ability_descs, i18n, fallback_i18n)
        tags = enemy_tag_payload(template_display.get("tags") or [], enemy_tags, i18n, fallback_i18n)
        drop_row = drop_table.get(template_id) or {}
        drops = enemy_drop_payload(drop_row.get("dropItemIds") if isinstance(drop_row, dict) else [], item_table, i18n, fallback_i18n)
        attr_template_id = normalize_id(primary_row.get("attrTemplateId")) or template_id
        attr_row = attr_templates.get(attr_template_id) if isinstance(attr_templates.get(attr_template_id), dict) else {}
        distribution_ids = [normalize_id(value) for value in template_display.get("distributionIds") or [] if normalize_id(value)]

        variants = []
        variant_ids = []
        story_wiki_keys = [f"wiki_{template_id}"]
        variant_attr_template_ids = []
        born_buffs: list[str] = []
        attr_modifiers: list[dict[str, Any]] = []
        for variant_id, variant_row in variant_rows:
            variant_display = display_infos.get(variant_id) if isinstance(display_infos.get(variant_id), dict) else {}
            variant_name = first_i18n_text(i18n, fallback_i18n, variant_display.get("name")) or story_wiki_titles.get(f"wiki_{variant_id}", "")
            variant_attr_template_id = normalize_id(variant_row.get("attrTemplateId")) or attr_template_id
            variant_display_type = first_non_empty(variant_display.get("displayType"), display_type)
            variant_display_type_label = row_label_lookup(display_types, variant_display_type, i18n, fallback_i18n) or display_type_label
            variant_buffs = [normalize_id(value) for value in variant_row.get("bornBuffs") or [] if normalize_id(value)]
            variant_modifiers = enemy_modifier_payload(
                variant_row.get("attrModifiers") or [],
                attr_meta,
                native_semantics,
            )
            born_buffs.extend(variant_buffs)
            attr_modifiers.extend(variant_modifiers)
            variant_ids.append(variant_id)
            variant_attr_template_ids.append(variant_attr_template_id)
            variants.append({
                "id": variant_id,
                "name": variant_name,
                "templateId": template_id,
                "attrTemplateId": variant_attr_template_id,
                "modelId": normalize_id(variant_row.get("modelId")),
                "aiTemplateId": normalize_id(variant_row.get("aiTemplateId")),
                "displayType": variant_display_type,
                "displayTypeLabel": variant_display_type_label,
                "isDangerous": variant_row.get("isDangerous"),
                "showBigEffect": variant_row.get("showBigEffect"),
                "showBigHeadbar": variant_row.get("showBigHeadbar"),
                "autoLockCancelType": variant_row.get("autoLockCancelType"),
                "autoLockCancelTime": variant_row.get("autoLockCancelTime"),
                "serverDeathCheck": variant_row.get("serverDeathCheck"),
                "bornBuffs": variant_buffs,
                "attrModifiers": variant_modifiers,
                "source": {"table": "EnemyTable.json", "id": variant_id},
            })

        story_wiki_keys = dedupe_values(story_wiki_keys)
        attribute_templates = {}
        for variant_attr_template_id in dedupe_values(variant_attr_template_ids):
            variant_attr_row = attr_templates.get(variant_attr_template_id) if isinstance(attr_templates.get(variant_attr_template_id), dict) else {}
            attribute_templates[variant_attr_template_id] = {
                "id": variant_attr_template_id,
                "source": {"table": "EnemyAttributeTemplateTable.json", "id": variant_attr_template_id},
                "stats": enemy_stat_curve_payload(variant_attr_row, attr_meta),
                "independentAttributes": enemy_attr_list_payload(variant_attr_row.get("levelIndependentAttributes"), attr_meta),
                "damageScalars": labeled_value_payload(variant_attr_row, ENEMY_COMBAT_SCALAR_FIELDS),
                "resilience": labeled_value_payload(variant_attr_row, ENEMY_RESILIENCE_FIELDS),
            }
        primary_attributes = attribute_templates.get(attr_template_id) or {
            "stats": enemy_stat_curve_payload(attr_row, attr_meta),
            "independentAttributes": enemy_attr_list_payload(attr_row.get("levelIndependentAttributes"), attr_meta),
            "damageScalars": labeled_value_payload(attr_row, ENEMY_COMBAT_SCALAR_FIELDS),
            "resilience": labeled_value_payload(attr_row, ENEMY_RESILIENCE_FIELDS),
        }
        born_buffs = dedupe_values(born_buffs)
        attr_modifiers = dedupe_payloads(attr_modifiers)
        model_id = normalize_id(primary_row.get("modelId"))
        ai_template_id = normalize_id(primary_row.get("aiTemplateId"))
        display_source = {"table": "EnemyTemplateDisplayInfoTable.json", "id": template_id} if template_display else ({"table": "EnemyDisplayInfoTable.json", "id": primary_id} if display else {})
        search = " ".join([
            template_id,
            primary_id,
            attr_template_id,
            model_id,
            ai_template_id,
            title,
            template_name,
            nickname,
            description,
            display_type_label,
            *(variant_ids),
            *(variant.get("name") or "" for variant in variants),
            *(ability.get("name") or "" for ability in abilities),
            *(ability.get("description") or "" for ability in abilities),
            *(tag.get("label") or "" for tag in tags),
            *distribution_ids,
            *born_buffs,
            *(drop.get("name") or drop.get("id") or "" for drop in drops),
        ])
        entries.append({
            "id": template_id,
            "kind": "enemy",
            "title": title,
            "subtitle": template_id,
            "fileName": title if title != template_id else "",
            "group": f"Enemy / {display_type_label or (template_name if template_name != template_id else template_id)}",
            "templateId": template_id,
            "templateName": template_name,
            "attrTemplateId": attr_template_id,
            "modelId": model_id,
            "aiTemplateId": ai_template_id,
            "displayType": display_type,
            "displayTypeLabel": display_type_label,
            "nickname": nickname,
            "description": description,
            "isDangerous": any(bool(row.get("isDangerous")) for _enemy_id, row in variant_rows),
            "showBigEffect": primary_row.get("showBigEffect"),
            "showBigHeadbar": primary_row.get("showBigHeadbar"),
            "autoLockCancelType": primary_row.get("autoLockCancelType"),
            "autoLockCancelTime": primary_row.get("autoLockCancelTime"),
            "serverDeathCheck": primary_row.get("serverDeathCheck"),
            "abilities": abilities,
            "tags": tags,
            "distributionIds": distribution_ids,
            "dropItems": drops,
            "bornBuffs": born_buffs,
            "attrModifiers": attr_modifiers,
            "independentAttributes": primary_attributes.get("independentAttributes") or [],
            "damageScalars": primary_attributes.get("damageScalars") or [],
            "resilience": primary_attributes.get("resilience") or [],
            "stats": primary_attributes.get("stats") or {},
            "attributeTemplates": attribute_templates,
            "variants": variants,
            "variantCount": len(variants),
            "variantIds": variant_ids,
            "source": {"table": "EnemyTable.json", "id": primary_id, "templateId": template_id},
            "displaySource": display_source,
            "storyWikiKey": story_wiki_keys[0] if story_wiki_keys else f"wiki_{template_id}",
            "storyWikiKeys": story_wiki_keys,
            "search": search.lower(),
        })
    return entries

def discover_character_namespace_ids(value: Any) -> set[str]:
    """Collect exact character namespace ids without promoting child skill ids."""

    found: set[str] = set()

    def visit(current: Any) -> None:
        if isinstance(current, dict):
            for key, child in current.items():
                normalized = normalize_id(key)
                if CHARACTER_NAMESPACE_RE.fullmatch(normalized):
                    found.add(normalized)
                visit(child)
        elif isinstance(current, list):
            for child in current:
                visit(child)
        elif isinstance(current, str):
            normalized = normalize_id(current)
            if CHARACTER_NAMESPACE_RE.fullmatch(normalized):
                found.add(normalized)

    visit(value)
    return found


def build_character_entries(
    tables: dict[str, Any],
    i18n: dict[str, Any],
    fallback_i18n: dict[str, Any],
) -> list[dict[str, Any]]:
    chars = tables["CharacterTable.json"]
    growth = tables["CharGrowthTable.json"]
    skill_table = tables["SkillPatchTable.json"]
    item_table = tables.get("ItemTable.json") or {}
    text_table = tables.get("TextTable.json") or {}
    professions = tables.get("CharProfessionTable.json") or {}
    char_types = tables.get("CharTypeTable.json") or {}
    level_curve = character_level_curve_payload(tables.get("CharLevelUpTable.json") or {})
    attr_meta = tables.get("AttributeMetaTable.json") or {}
    break_stages = character_break_stage_payload(tables, item_table, i18n, fallback_i18n)
    namespace_ids = discover_character_namespace_ids(tables.get("StrIdNumTable.json") or {})
    character_rows = {
        char_id: row
        for char_id, row in chars.items()
        if isinstance(char_id, str)
    }
    for char_id in namespace_ids:
        character_rows.setdefault(char_id, {})
    entries = []
    for char_id, row in sorted(character_rows.items(), key=lambda item: character_sort_key(item[0], item[1])):
        if char_id in HIDDEN_CHARACTER_IDS:
            continue
        if not isinstance(row, dict):
            continue
        growth_row = growth.get(char_id) or {}
        namespace_only = char_id not in chars
        actor_token = CHARACTER_NAMESPACE_RE.fullmatch(char_id)
        npc_name_key = f"npcName_{actor_token.group(0).split('_', 2)[2]}" if actor_token else ""
        name = (
            i18n_text(i18n, row.get("name"), fallback_i18n)
            or i18n_text(i18n, text_table.get(npc_name_key), fallback_i18n)
            or normalize_id(row.get("engName"))
            or char_id
        )
        profession_label = label_lookup(professions, row.get("profession"), i18n, fallback_i18n)
        type_row = char_types.get(normalize_id(row.get("charTypeId"))) or {}
        element_label = i18n_text(i18n, type_row.get("name"), fallback_i18n) or normalize_id(row.get("charTypeId"))
        skill_groups = []
        for group_id, group in sorted((growth_row.get("skillGroupMap") or {}).items(), key=lambda item: int((item[1] or {}).get("skillGroupType") or 0)):
            if not isinstance(group, dict):
                continue
            group_name = i18n_text(i18n, group.get("name"), fallback_i18n) or group_id
            group_desc_template = i18n_text(i18n, group.get("desc"), fallback_i18n)
            skill_ids = [normalize_id(skill_id) for skill_id in group.get("skillIdList") or [] if normalize_id(skill_id)]
            skills = [
                skill_payload(skill_id, skill_table, i18n, fallback_i18n)
                for skill_id in skill_ids
            ]
            group_blackboard = aggregate_skill_blackboard(skills)
            group_desc = render_description(group_desc_template, group_blackboard) if group_desc_template else ""
            level_up_rows = []
            for level_row in growth_row.get("skillLevelUp") or []:
                if not isinstance(level_row, dict) or normalize_id(level_row.get("skillGroupId")) != group_id:
                    continue
                level_up_rows.append({
                    "skillGroupId": normalize_id(level_row.get("skillGroupId")),
                    "level": level_row.get("level"),
                    "goldCost": level_row.get("goldCost"),
                    "itemBundle": required_item_payload(level_row.get("itemBundle"), item_table, i18n, fallback_i18n),
                })
            skill_groups.append({
                "id": group_id,
                "type": group.get("skillGroupType"),
                "typeLabel": SKILL_GROUP_TYPE_LABELS.get(int(group.get("skillGroupType") or 0), f"Group {group.get('skillGroupType')}"),
                "name": group_name,
                "description": clean_text(group_desc),
                "descriptionTemplate": clean_text(group_desc_template),
                "blackboard": group_blackboard,
                "iconId": normalize_id(group.get("icon")),
                "actionSkillIds": skill_ids,
                "levelUp": level_up_rows,
                "skills": skills,
            })
        talent_groups, talents = build_talent_groups(
            char_id,
            growth_row.get("talentNodeMap") or {},
            tables,
            i18n,
            fallback_i18n,
        )
        breakthroughs = character_breakthrough_payload(growth_row, item_table, i18n, fallback_i18n)
        potentials = character_potential_payload(char_id, tables, item_table, i18n, fallback_i18n)
        stats = character_stat_curve_payload(row, attr_meta, level_curve.get("maxLevel"))
        default_weapon_id = normalize_id(row.get("defaultWeaponId"))
        default_weapon_name = item_name(item_table, default_weapon_id, i18n, fallback_i18n)
        weapon_type_name = weapon_type_label(row.get("weaponType"), default_weapon_id, text_table, i18n, fallback_i18n)
        search = " ".join([
            char_id,
            name,
            normalize_id(row.get("engName")),
            profession_label,
            element_label,
            weapon_type_name,
            default_weapon_name,
            default_weapon_id,
            *(group.get("name") or "" for group in skill_groups),
            *(group.get("description") or "" for group in skill_groups),
            *(skill_search_text(skill) for group in skill_groups for skill in group.get("skills") or []),
            *(group.get("title") or "" for group in talent_groups),
            *(level.get("title") or "" for group in talent_groups for level in group.get("levels") or []),
            *(level.get("description") or "" for group in talent_groups for level in group.get("levels") or []),
            *(item.get("name") or "" for row in breakthroughs for item in row.get("requiredItem") or []),
            *(level.get("name") or "" for level in (potentials.get("levels") or [])),
            *(level.get("description") or "" for level in (potentials.get("levels") or [])),
            *(item.get("name") or "" for level in (potentials.get("levels") or []) for item in level.get("requiredItem") or []),
        ])
        story_wiki_keys = CHARACTER_STORY_WIKI_KEYS.get(char_id) or [f"wiki_{char_id}"]
        entries.append({
            "id": char_id,
            "kind": "character",
            "title": name,
            "subtitle": char_id,
            "group": f"Character / {element_label or 'Unknown'}",
            "engName": normalize_id(row.get("engName")),
            "rarity": row.get("rarity"),
            "profession": row.get("profession"),
            "professionLabel": profession_label,
            "element": normalize_id(row.get("charTypeId")),
            "elementLabel": element_label,
            "weaponType": row.get("weaponType"),
            "weaponTypeKey": weapon_type_token_from_id(default_weapon_id),
            "weaponTypeLabel": weapon_type_name,
            "defaultWeaponId": default_weapon_id,
            "defaultWeaponName": default_weapon_name,
            "mainAttrType": row.get("mainAttrType"),
            "subAttrType": row.get("subAttrType"),
            "skillGroups": skill_groups,
            "talentGroups": talent_groups,
            "talents": talents,
            "levelCurve": level_curve,
            "breakStages": break_stages,
            "breakthroughs": breakthroughs,
            "potentials": potentials,
            "stats": stats,
            "source": {
                "table": "StrIdNumTable.json" if namespace_only else "CharacterTable.json",
                "id": char_id,
            },
            "characterTablePresent": not namespace_only,
            "identityStatus": "character_namespace_only" if namespace_only else "character_table_row",
            "evidenceBoundary": (
                "The exact chr_0NNN_token namespace is registered, but CharacterTable has no row; "
                "availability, progression, runtime use, and playable status remain unproven."
                if namespace_only else None
            ),
            "storyWikiKey": story_wiki_keys[0],
            "storyWikiKeys": story_wiki_keys,
            "search": search.lower(),
        })
    return entries


def load_story_wiki_titles(out_dir: Path, language: str) -> dict[str, str]:
    payload = read_json(out_dir / language / "index.json", {})
    if not isinstance(payload, dict):
        return {}
    titles: dict[str, str] = {}
    for entry in payload.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        key = normalize_id(entry.get("k"))
        if not key.startswith("wiki_"):
            continue
        titles[key] = clean_text(entry.get("title")) or key
    return titles


def apply_story_wiki_keys(entries: list[dict[str, Any]], story_wiki_keys: set[str]) -> int:
    count = 0
    for entry in entries:
        raw_keys: list[Any] = []
        alias_keys = entry.get("storyWikiKeys")
        if isinstance(alias_keys, list):
            raw_keys.extend(alias_keys)
        elif alias_keys:
            raw_keys.append(alias_keys)
        raw_keys.append(entry.get("storyWikiKey") or (f"wiki_{entry.get('id')}" if entry.get("id") else ""))
        valid_keys = []
        seen = set()
        for raw_key in raw_keys:
            key = normalize_id(raw_key)
            if not key or key in seen or key not in story_wiki_keys:
                continue
            seen.add(key)
            valid_keys.append(key)
        if valid_keys:
            entry["storyWikiKey"] = valid_keys[0]
            if len(valid_keys) > 1:
                entry["storyWikiKeys"] = valid_keys
            else:
                entry.pop("storyWikiKeys", None)
            count += len(valid_keys)
        else:
            entry.pop("storyWikiKey", None)
            entry.pop("storyWikiKeys", None)
    return count

def build_language_payload(
    language: str,
    table_roots: list[tuple[str, Path]],
    fallback_language: str,
    story_wiki_keys: set[str] | None = None,
    story_wiki_titles: dict[str, str] | None = None,
    export_root: Path | None = None,
    native_semantics: dict[str, Any] | None = None,
    runtime_tag_capture: Path | None = None,
) -> dict[str, Any]:
    fallback_i18n = load_merged_table(table_roots, f"I18nTextTable_{fallback_language}.json", {})
    i18n = fallback_i18n if language == fallback_language else load_merged_table(table_roots, f"I18nTextTable_{language}.json", fallback_i18n)
    table_names = [
        "GlobalConst.json",
        "ItemTable.json",
        "ItemTypeTable.json",
        "UseItemTable.json",
        "UsableItemChestTable.json",
        "RewardTable.json",
        "WeaponBasicTable.json",
        "WeaponBreakThroughTemplateTable.json",
        "WeaponTalentTemplateTable.json",
        "WeaponUpgradeTemplateTable.json",
        "WeaponUpgradeTemplateSumTable.json",
        "SkillPatchTable.json",
        "StrIdNumTable.json",
        "CharacterTable.json",
        "CharGrowthTable.json",
        "CharLevelUpTable.json",
        "CharBreakTable.json",
        "CharBreakStageTable.json",
        "CharacterPotentialTable.json",
        "CharProfessionTable.json",
        "CharTypeTable.json",
        "AttributeMetaTable.json",
        "EquipTable.json",
        "EquipItemTable.json",
        "EquipSuitTable.json",
        "EquipFormulaTable.json",
        "EquipEnhanceCostTable.json",
        "ItemShowingTypeTable.json",
        "EquipPackTable.json",
        "ShopChannelDevelopmentTable.json",
        "DomainDataTable.json",
        "CharBreakNodeTable.json",
        "PotentialTalentEffectTable.json",
        "SpaceshipCharSkillTable.json",
        "SpaceshipSkillTable.json",
        "EnemyTable.json",
        "EnemyAttributeTemplateTable.json",
        "EnemyDisplayInfoTable.json",
        "EnemyTemplateDisplayInfoTable.json",
        "DisplayEnemyTypeTable.json",
        "EnemyAbilityDescTable.json",
        "EnemyTagTable.json",
        "WikiEnemyDropTable.json",
        "TextTable.json",
    ]
    tables = {name: load_merged_table(table_roots, name, {}) for name in table_names}
    global_const = tables.get("GlobalConst.json") or {}
    gold_item_id = normalize_id(global_const.get("goldItemId")) if isinstance(global_const, dict) else ""
    currency_items = {}
    if gold_item_id:
        gold_item = game_object_payload(gold_item_id, None, tables, i18n, fallback_i18n)
        gold_item["source"] = {"table": "GlobalConst.json", "field": "goldItemId", "itemId": gold_item_id}
        currency_items["gold"] = gold_item
    weapons = build_weapon_entries(tables, i18n, fallback_i18n)
    equipment = build_equipment_entries(tables, i18n, fallback_i18n)
    characters = build_character_entries(tables, i18n, fallback_i18n)
    enemies = build_enemy_entries(
        tables,
        i18n,
        fallback_i18n,
        story_wiki_titles,
        native_semantics,
    )
    usable_items = build_usable_item_entries(tables, i18n, fallback_i18n, story_wiki_titles)
    entries = sorted(
        [*weapons, *equipment, *characters, *enemies, *usable_items],
        key=lambda item: ({"weapon": 0, "equipment": 1, "character": 2, "enemy": 3, "item": 4}.get(str(item.get("kind") or ""), 9), str(item.get("group") or ""), str(item.get("title") or "")),
    )
    gameplay_buff_ids = collect_gameplay_buff_ids(entries)
    resolved_export_root = export_root or table_roots[0][1].parents[2]
    gameplay_tag_registry = load_gameplay_tag_registry(
        resolved_export_root,
        runtime_tag_capture,
    )
    buffs = build_gameplay_buff_catalog(
        resolved_export_root,
        gameplay_buff_ids,
        native_semantics,
        gameplay_tag_registry,
    )
    story_wiki_link_count = apply_story_wiki_keys(entries, story_wiki_keys or set())
    enemy_stat_templates = {
        normalize_id(item.get("attrTemplateId")): (item.get("stats") or {}).get("rowCount") or 0
        for item in enemies
        if normalize_id(item.get("attrTemplateId"))
    }
    return {
        "generated": int(time.time()),
        "language": language,
        "sourceRoot": ", ".join(rel_path(root) for _label, root in table_roots),
        "sourceRoots": [{"source": label, "root": rel_path(root)} for label, root in table_roots],
        "tables": table_names,
        "gameplayTagRegistry": gameplay_tag_registry,
        "currencyItems": currency_items,
        "buffs": buffs,
        "buffEvidence": {
            "status": "partial-memorypack-semantics",
            "coverage": (
                "Referenced BuffData ids, exact post-id lifecycle/stacking/trigger tail, "
                "exact empty-ability-event prefix tags/attribute modifiers, exact "
                "predefined GameplayTag names where the current registry covers them, "
                "and keyed pre-id BlackboardDouble candidates"
            ),
            "boundary": (
                "Non-empty pre-id ability-event action bodies remain unresolved; "
                "a duration is shown only when one unique authored duration key is present; "
                "GameplayTag ids absent from the predefined registry remain raw."
            ),
        },
        "nativeEvidence": (native_semantics or {}).get("evidence") or {
            "status": "not-requested",
            "detail": "native modifier enum meanings were not loaded",
        },
        "counts": {
            "entries": len(entries),
            "weapons": len(weapons),
            "characters": len(characters),
            "equipment": len(equipment),
            "enemies": len(enemies),
            "usableItems": len(usable_items),
            "characterSkillGroups": sum(len(item.get("skillGroups") or []) for item in characters),
            "weaponSkills": sum(len(item.get("skills") or []) for item in weapons),
            "equipmentSuitEffects": sum(len(((item.get("suit") or {}).get("effects") or [])) for item in equipment),
            "equipmentStatRows": sum(len((item.get("stats") or {}).get("rows") or []) for item in equipment),
            "equipmentPropertyCurves": sum(len((item.get("stats") or {}).get("propertyCurves") or []) for item in equipment),
            "characterTalentGroups": sum(len(item.get("talentGroups") or []) for item in characters),
            "characterBreakthroughRows": sum(len(item.get("breakthroughs") or []) for item in characters),
            "characterPotentialLevels": sum(len((item.get("potentials") or {}).get("levels") or []) for item in characters),
            "weaponUpgradeCheckpoints": sum(len((item.get("upgrade") or {}).get("checkpoints") or []) for item in weapons),
            "weaponStatRows": sum(len((item.get("stats") or {}).get("rows") or []) for item in weapons),
            "characterStatRows": sum(len((item.get("stats") or {}).get("rows") or []) for item in characters),
            "characterRawStatRows": sum(int((item.get("stats") or {}).get("rawRowCount") or 0) for item in characters),
            "enemyStatRows": sum(int(value or 0) for value in enemy_stat_templates.values()),
            "enemyEntryStatRows": sum(int((item.get("stats") or {}).get("rowCount") or 0) for item in enemies),
            "enemyAbilities": sum(len(item.get("abilities") or []) for item in enemies),
            "enemyVariants": sum(len(item.get("variants") or []) for item in enemies),
            "enemyBornBuffs": sum(len(item.get("bornBuffs") or []) for item in enemies),
            "gameplayBuffs": len(gameplay_buff_ids),
            "resolvedGameplayBuffs": sum(
                1 for record in buffs.values()
                if record.get("evidenceStatus") != "unresolved"
            ),
            "gameplayBuffAttributeModifiers": sum(
                len(((record.get("attributeModifier") or {}).get("attributeModifiers") or []))
                for record in buffs.values()
            ),
            "usableItemActions": sum(len(((item.get("useData") or {}).get("actions") or [])) for item in usable_items),
            "usableItemRewards": sum(len(((item.get("chestData") or {}).get("rewards") or [])) for item in usable_items),
            "weaponBreakthroughRows": sum(len((item.get("breakthrough") or {}).get("rows") or []) for item in weapons),
            "storyWikiLinks": story_wiki_link_count,
        },
        "entries": entries,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    table_roots = table_source_roots(args.export_root)
    if not table_roots:
        print(f"Missing table directories under: {args.export_root / 'structured'}", file=sys.stderr)
        return 2

    native_semantics = load_native_gameplay_semantics()
    if (native_semantics.get("evidence") or {}).get("status") != "validated":
        print(
            "Gameplay native modifier semantics skipped: "
            + str((native_semantics.get("evidence") or {}).get("detail") or "native gate unavailable"),
            file=sys.stderr,
        )
    outputs = []
    for language in args.languages:
        code = str(language).strip().upper()
        if not code:
            continue
        story_wiki_titles = load_story_wiki_titles(args.out_dir, code)
        story_wiki_keys = set(story_wiki_titles)
        payload = build_language_payload(
            code,
            table_roots,
            str(args.default_language).strip().upper(),
            story_wiki_keys,
            story_wiki_titles,
            args.export_root,
            native_semantics,
            args.runtime_tag_capture,
        )
        out_path = args.out_dir / code / "gameplay" / "index.json"
        write_json(out_path, payload)
        outputs.append((code, out_path, payload["counts"]))

    for code, path, counts in outputs:
        print(
            f"{code}: wrote {rel_path(path)} "
            f"({counts['weapons']} weapons, {counts['equipment']} equipment, "
            f"{counts['characters']} characters, {counts['enemies']} enemies, "
            f"{counts['usableItems']} usable items)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
