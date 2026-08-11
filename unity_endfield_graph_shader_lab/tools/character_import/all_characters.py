#!/usr/bin/env python3
"""Build the source-derived catalog for every canonical character post-model.

CharacterTable identities retain the playable catalog contract.  Canonical
character-container identities absent from the current patch-aware table are
added as nonplayable source models, while NPC aliases, enemy/ability-entity
models, and variants such as Zhuangfy's ultimate prefab stay excluded.
"""

from __future__ import annotations

import copy
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from endfield_asset_map_filter import iter_asset_entries

from .catalog import (
    DEFAULT_ASSET_MAPS,
    DEFAULT_CHARACTER_TABLE,
    DEFAULT_CLIP_SCOPE,
    DEFAULT_UI_CONTROLLER_ROOTS,
    PROJECT_ROOT,
    REPO_ROOT,
    _asset_root_for_map,
    _best_unique_named_entries,
    _dedupe_entries,
    _entry_copy,
    _entry_sort_key,
    _is_actor_body_animation_entry,
    _safe_folder_name,
    _source_fingerprint,
    build_import_plan,
)


DEFAULT_ALL_CHARACTER_WORK_ROOT = REPO_ROOT / "scratch" / "character_model_import"
DEFAULT_ALL_CHARACTER_CATALOG_PATH = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Catalog"
    / "all_character_model_catalog.json"
)
DEFAULT_NPC_INFO_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "NpcInfoTable.json"
)
DEFAULT_NPC_TEMPLATE_GROUP_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "NpcTemplateGroupTable.json"
)
DEFAULT_TEXT_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "TextTable.json"
)
DEFAULT_I18N_EN_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "I18nTextTable_EN.json"
)
DEFAULT_NPC_PREFAB_INFO_ROOT = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Data"
    / "Json"
    / "NPC"
    / "PrefabInfo"
)

_CANONICAL_CHARACTER_RE = re.compile(
    r"(?:^|/)postmodels/characters/"
    r"(?P<character_id>chr_\d{4}_(?P<token>[a-z0-9]+))_postmodel\.prefab$",
    re.IGNORECASE,
)
_SOURCE_T_POSE_RE = re.compile(
    r"^A_actor_(?P<token>[^_]+)_t_pose$",
    re.IGNORECASE,
)


def _display_from_source_identifier(
    token: str,
    localized_name: str = "",
    npc_id: str = "",
) -> str:
    """Expose the original identifier without inventing a localized name."""

    source_name = localized_name or _safe_folder_name(npc_id or token)
    token_name = _safe_folder_name(token)
    if npc_id and npc_id.casefold() != token.casefold():
        return f"{source_name} ({token_name})"
    return source_name


def _npc_source_membership(
    npc_info_table: Path,
    npc_template_group_table: Path,
    text_table: Path,
    i18n_en_table: Path,
    npc_prefab_info_root: Path,
    canonical_character_ids: Iterable[str],
) -> dict[str, dict[str, Any]]:
    info = json.loads(npc_info_table.read_text(encoding="utf-8"))
    groups = json.loads(npc_template_group_table.read_text(encoding="utf-8"))
    text = json.loads(text_table.read_text(encoding="utf-8"))
    english = json.loads(i18n_en_table.read_text(encoding="utf-8"))
    if not all(isinstance(value, dict) for value in (info, groups, text, english)):
        raise ValueError("NPC source tables must contain JSON objects")
    result: dict[str, dict[str, Any]] = {}
    for character_id in canonical_character_ids:
        token = character_id.split("_", 2)[2].casefold()
        expected_template_id = f"npc_{character_id}"
        candidates: list[tuple[str, dict[str, Any]]] = []
        for key, raw_row in info.items():
            if not isinstance(raw_row, dict):
                continue
            values = {
                str(key).casefold(),
                str(raw_row.get("npcId") or "").casefold(),
                str(raw_row.get("voActor") or "").casefold(),
                str(raw_row.get("wwiseId") or "").casefold(),
            }
            template_id = str(raw_row.get("templateId") or "")
            if token in values or template_id.casefold() == expected_template_id.casefold():
                candidates.append((str(key), raw_row))
        if len(candidates) != 1:
            raise ValueError(
                f"{character_id}: expected one exact NpcInfo source join, found {len(candidates)}"
            )
        npc_key, row = candidates[0]
        group = groups.get(npc_key)
        if not isinstance(group, dict):
            raise ValueError(f"{character_id}: NpcTemplateGroup row is missing for {npc_key}")
        template_id = str(row.get("templateId") or "")
        if str(group.get("templateId") or "") != template_id:
            raise ValueError(f"{character_id}: NPC table templateId join differs")
        prefab_info_path = npc_prefab_info_root / f"{template_id}.json"
        if not prefab_info_path.is_file():
            raise FileNotFoundError(
                f"{character_id}: NPC PrefabInfo is missing: {prefab_info_path}"
            )
        prefab_info = json.loads(prefab_info_path.read_text(encoding="utf-8"))
        if not isinstance(prefab_info, dict) or str(prefab_info.get("id") or "") != template_id:
            raise ValueError(f"{character_id}: NPC PrefabInfo identity differs")
        name_key = str(group.get("name") or "")
        localized_name = ""
        localization_evidence: dict[str, Any] = {
            "name_key": name_key,
            "language": "EN",
            "status": "identifier_fallback",
        }
        if name_key:
            text_row = text.get(name_key)
            if not isinstance(text_row, dict) or "id" not in text_row:
                raise ValueError(f"{character_id}: TextTable row is missing for {name_key}")
            text_id = str(text_row["id"])
            localized_name = str(english.get(text_id) or "")
            if not localized_name:
                raise ValueError(f"{character_id}: EN localization is missing for {name_key}")
            localization_evidence = {
                "name_key": name_key,
                "text_id": text_id,
                "language": "EN",
                "status": "exact_table_join",
            }
        result[token] = {
            "npc_info_key": npc_key,
            "npc_id": str(row.get("npcId") or npc_key),
            "npc_template_id": template_id,
            "npc_name_key": name_key,
            "vo_actor": str(row.get("voActor") or group.get("voActor") or ""),
            "wwise_id": str(row.get("wwiseId") or ""),
            "localized_name_en": localized_name,
            "localization_evidence": localization_evidence,
            "npc_prefab_info_source": str(prefab_info_path.resolve()),
            "facial_morph_avatar_name": str(
                prefab_info.get("facialMorphAvatarName") or ""
            ),
            "ear_morph_avatar_name": str(prefab_info.get("earMorphAvatarName") or ""),
            "disable_blink": bool(prefab_info.get("disableBlink")),
        }
    return result


def _empty_ui_item_widgets() -> dict[str, Any]:
    return {
        "prefab_count": 0,
        "prefab_entries": [],
        "selection_rule": "no exact character UI-deco prefab was assigned",
        "clip_rule": "no UI-deco animation was assigned",
        "controller_owned_clip_families": [],
        "controller_owned_clips": [],
        "exact_controller_sources": [],
    }


def _work_paths(work_root: Path, character_id: str) -> dict[str, str]:
    actor_root = work_root / "characters" / character_id
    animation_root = actor_root / "animation_scopes" / "source-preview"
    return {
        "root": str(actor_root.resolve()),
        "hierarchy": str((actor_root / "hierarchy").resolve()),
        "meshes": str((actor_root / "meshes").resolve()),
        "materials": str((actor_root / "materials").resolve()),
        "animation_clips": str((animation_root / "animation_clips").resolve()),
        "samples": str((animation_root / "samples").resolve()),
        "widget_hierarchy": str((actor_root / "item_widgets" / "hierarchy").resolve()),
        "widget_meshes": str((actor_root / "item_widgets" / "meshes").resolve()),
        "widget_animation_clips": str(
            (animation_root / "item_widgets" / "animation_clips").resolve()
        ),
        "widget_samples": str((animation_root / "item_widgets" / "samples").resolve()),
        "filters": str((animation_root / "filters").resolve()),
        "manifest_report": str((animation_root / "manifest_report.json").resolve()),
    }


def _canonical_character_sources(
    asset_maps: Iterable[Path],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, list[dict[str, Any]]]]:
    postmodels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    t_poses: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for map_path in asset_maps:
        asset_root = _asset_root_for_map(map_path)
        for raw_entry in iter_asset_entries(map_path):
            entry_type = str(raw_entry.get("Type") or "")
            name = str(raw_entry.get("Name") or "")
            container = str(raw_entry.get("Container") or "").replace("\\", "/")
            if entry_type == "Animator":
                match = _CANONICAL_CHARACTER_RE.search(container)
                if not match:
                    continue
                character_id = match.group("character_id").casefold()
                expected_name = f"{character_id}_postmodel"
                if name.casefold() != expected_name:
                    continue
                postmodels[character_id].append(_entry_copy(raw_entry, asset_root))
                continue
            if entry_type != "AnimationClip":
                continue
            match = _SOURCE_T_POSE_RE.fullmatch(name)
            if match and _is_actor_body_animation_entry(raw_entry):
                t_poses[match.group("token").casefold()].append(
                    _entry_copy(raw_entry, asset_root)
                )
    return postmodels, t_poses


def _source_preview_animation(
    token: str,
    t_poses: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    selected = _best_unique_named_entries(t_poses.get(token, []))
    if len(selected) > 1:
        selected = [sorted(selected, key=_entry_sort_key)[0]]
    names = [str(entry.get("Name") or "") for entry in selected]
    return {
        "clip_scope": "source-preview",
        "animation_profile": "source_t_pose" if selected else "static_postmodel",
        "actor_ui_source_count": 0,
        "skeletal_body_ui_count": 0,
        "external_camera_count": 0,
        "external_ui_effect_count": 0,
        "companion_widget_count": 0,
        "selected_companion_widget_count": 0,
        "selected_count": len(selected),
        "selected_names": names,
        "preview_preference": names,
        "selected_entries": selected,
        "body_entries": selected,
        "external_camera_entries": [],
        "external_ui_effect_entries": [],
        "companion_widget_entries": [],
        "selected_companion_widget_entries": [],
        "selected_companion_widget_names": [],
        "selection_evidence": (
            "exact A_actor_<token>_t_pose AnimationClip under the original actor animation container"
            if selected
            else "no exact token-owned source preview clip"
        ),
    }


def _catalog_character(source: dict[str, Any]) -> dict[str, Any]:
    ui = source.get("ui_animation") or {}
    return {
        "character_id": source["character_id"],
        "actor_token": source["actor_token"],
        "actor_class": source.get("actor_class", "playable"),
        "source_classification": source.get(
            "source_classification",
            source.get("actor_class", "playable"),
        ),
        "source_membership": source.get("source_membership", {}),
        "capabilities": source.get("capabilities", {}),
        "display_name": source["display_name"],
        "source_display_name": source["source_display_name"],
        "root_name": source["root_name"],
        "sort_order": source["sort_order"],
        "rarity": source["rarity"],
        "import_enabled": True,
        "selected_this_run": bool(source.get("import_enabled")),
        "active": bool(source.get("active")),
        "manifest_asset_path": source["manifest_asset_path"],
        "prefab_asset_path": source["prefab_asset_path"],
        "postmodel_root": source["postmodel_root"],
        "animation_profile": ui.get("animation_profile", "playable_ui"),
        "selected_source_clips": list(ui.get("selected_names") or []),
        "preview_clip_preference": list(ui.get("preview_preference") or []),
        "source_clip_count": int(ui.get("actor_ui_source_count") or 0),
        "selected_source_clip_count": int(ui.get("selected_count") or 0),
    }


def build_all_character_plan(
    character_table: Path = DEFAULT_CHARACTER_TABLE,
    asset_maps: Iterable[Path] = DEFAULT_ASSET_MAPS,
    *,
    selected_actor_tokens: set[str] | None = None,
    work_root: Path = DEFAULT_ALL_CHARACTER_WORK_ROOT,
    controller_roots: Iterable[Path] = DEFAULT_UI_CONTROLLER_ROOTS,
    npc_info_table: Path = DEFAULT_NPC_INFO_TABLE,
    npc_template_group_table: Path = DEFAULT_NPC_TEMPLATE_GROUP_TABLE,
    text_table: Path = DEFAULT_TEXT_TABLE,
    i18n_en_table: Path = DEFAULT_I18N_EN_TABLE,
    npc_prefab_info_root: Path = DEFAULT_NPC_PREFAB_INFO_ROOT,
) -> dict[str, Any]:
    """Return the canonical character plan while preserving playable assets."""

    map_paths = tuple(Path(path).resolve() for path in asset_maps)
    for path in map_paths:
        if not path.is_file():
            raise FileNotFoundError(f"AnimeStudio asset map not found: {path}")
    npc_info_table = Path(npc_info_table).resolve()
    npc_template_group_table = Path(npc_template_group_table).resolve()
    text_table = Path(text_table).resolve()
    i18n_en_table = Path(i18n_en_table).resolve()
    npc_prefab_info_root = Path(npc_prefab_info_root).resolve()
    for path in (
        npc_info_table,
        npc_template_group_table,
        text_table,
        i18n_en_table,
    ):
        if not path.is_file():
            raise FileNotFoundError(f"NPC source table not found: {path}")
    if not npc_prefab_info_root.is_dir():
        raise FileNotFoundError(f"NPC PrefabInfo root not found: {npc_prefab_info_root}")

    playable_plan = build_import_plan(
        Path(character_table),
        map_paths,
        clip_scope=DEFAULT_CLIP_SCOPE,
        work_root=work_root / "playable_compat",
        controller_roots=controller_roots,
    )
    postmodels, t_poses = _canonical_character_sources(map_paths)
    playable_by_id = {
        str(character["character_id"]).casefold(): character
        for character in playable_plan["characters"]
    }
    nonplayable_character_ids = sorted(set(postmodels) - set(playable_by_id))
    npc_source_by_token = _npc_source_membership(
        npc_info_table,
        npc_template_group_table,
        text_table,
        i18n_en_table,
        npc_prefab_info_root,
        nonplayable_character_ids,
    )

    characters: list[dict[str, Any]] = []
    for character_id in sorted(
        postmodels,
        key=lambda value: (int(value.split("_", 2)[1]), value.casefold()),
    ):
        token = character_id.split("_", 2)[2].casefold()
        if character_id in playable_by_id:
            character = copy.deepcopy(playable_by_id[character_id])
            character["actor_class"] = "playable"
            character["source_classification"] = "playable"
            character["source_membership"] = {
                "canonical_group": "characters",
                "character_table": True,
                "npc_alias_container_expected": True,
            }
            character["capabilities"] = {
                "playable_ui_animation": True,
                "source_preview_animation": bool(
                    character.get("ui_animation", {}).get("selected_count")
                ),
                "source_charinfo_profile_available": True,
                "source_charinfo_profile_recovered": True,
            }
            character["ui_animation"]["animation_profile"] = "playable_ui"
        else:
            entries = _dedupe_entries(postmodels[character_id])
            selected_postmodel = sorted(entries, key=_entry_sort_key)[0]
            folder_name = _safe_folder_name(token)
            animation = _source_preview_animation(token, t_poses)
            npc_source = npc_source_by_token.get(token) or {}
            source_display = _display_from_source_identifier(
                token,
                str(npc_source.get("localized_name_en") or ""),
                str(npc_source.get("npc_id") or ""),
            )
            character = {
                "character_id": character_id,
                "actor_token": token,
                "actor_class": "cutscene_clone" if token == "chenpast" else "npc",
                "source_classification": (
                    "cutscene_clone" if token == "chenpast" else "npc"
                ),
                "source_membership": {
                    "canonical_group": "characters",
                    "character_table": False,
                    "npc_alias_container_expected": token in {"liino", "jsspsi"},
                    **npc_source,
                },
                "capabilities": {
                    "playable_ui_animation": False,
                    "source_preview_animation": bool(animation["selected_count"]),
                    "source_charinfo_profile_available": token == "liino",
                    "source_charinfo_profile_recovered": False,
                },
                "source_display_name": source_display,
                "display_name": source_display,
                "folder_name": folder_name,
                "root_name": folder_name,
                "sort_order": int(character_id.split("_", 2)[1]),
                "rarity": 0,
                "active": False,
                "postmodel_root": f"{character_id}_postmodel",
                "postmodel": selected_postmodel,
                "postmodel_name_candidates": sorted(entries, key=_entry_sort_key),
                "manifest_asset_path": (
                    "Assets/EndfieldGraphShaderLab/Generated/Characters/NonPlayable/"
                    f"{folder_name}/{token}_model_recovery_manifest.json"
                ),
                "prefab_asset_path": (
                    "Assets/EndfieldGraphShaderLab/Generated/Characters/NonPlayable/"
                    f"{folder_name}/Prefabs/{folder_name}.prefab"
                ),
                "work_paths": _work_paths(work_root, character_id),
                "ui_animation": animation,
                "ui_item_widgets": _empty_ui_item_widgets(),
                "source_table_row": {
                    "charId": character_id,
                    "engName": source_display,
                    "sortOrder": int(character_id.split("_", 2)[1]),
                    "rarity": 0,
                    "evidence": "canonical character postmodel; absent from current CharacterTable",
                },
            }
        characters.append(character)

    known_tokens = {str(character["actor_token"]).casefold() for character in characters}
    requested = (
        {str(token).casefold() for token in selected_actor_tokens}
        if selected_actor_tokens
        else None
    )
    unknown = sorted((requested or set()) - known_tokens)
    if unknown:
        raise ValueError(f"unknown canonical character actor token(s): {', '.join(unknown)}")

    for character in characters:
        token = str(character["actor_token"]).casefold()
        character["import_enabled"] = (
            token in requested
            if requested is not None
            else character["actor_class"] != "playable"
        )
        character["active"] = token == "wulfa"

    enabled = [character for character in characters if character["import_enabled"]]
    missing_required_clips = [
        {
            "character_id": character["character_id"],
            "actor_token": character["actor_token"],
            "selected_names": character["ui_animation"]["selected_names"],
        }
        for character in enabled
        if character["ui_animation"].get("animation_profile") == "playable_ui"
        and int(character["ui_animation"].get("selected_count") or 0) < 2
    ]
    return {
        "schema_version": 1,
        "scope": "all canonical original character post-model identities",
        "clip_scope": "playable-overview-or-exact-source-preview",
        "roster_rule": (
            "exact Animator/root/container join in postmodels/characters/"
            "chr_<four digits>_<single token>_postmodel.prefab; variants, NPC aliases, "
            "enemies, and ability entities are excluded"
        ),
        "animation_rule": (
            "CharacterTable playables retain their original overview pair; nonplayables admit "
            "only an exact token-owned A_actor_<token>_t_pose source clip, otherwise remain static"
        ),
        "character_table": _source_fingerprint(Path(character_table).resolve()),
        "asset_maps": [_source_fingerprint(path) for path in map_paths],
        "npc_info_table": _source_fingerprint(npc_info_table),
        "npc_template_group_table": _source_fingerprint(npc_template_group_table),
        "text_table": _source_fingerprint(text_table),
        "i18n_en_table": _source_fingerprint(i18n_en_table),
        "npc_prefab_info_root": str(npc_prefab_info_root),
        "playable_roster_count": len(playable_by_id),
        "nonplayable_character_count": sum(
            character["actor_class"] != "playable" for character in characters
        ),
        "roster_count": len(characters),
        "import_character_count": len(enabled),
        "missing_required_clip_sets": missing_required_clips,
        "excluded_source_groups": ["npc aliases", "enemies", "abilityentities"],
        "excluded_character_variants": ["chr_0030_zhuangfy_ult_postmodel"],
        "characters": characters,
    }


def all_character_catalog_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    characters = [_catalog_character(character) for character in plan.get("characters") or []]
    return {
        "schema_version": int(plan.get("schema_version") or 1),
        "scope": plan.get("scope", ""),
        "roster_rule": plan.get("roster_rule", ""),
        "animation_rule": plan.get("animation_rule", ""),
        "character_table": plan.get("character_table", {}),
        "asset_maps": plan.get("asset_maps", []),
        "roster_count": len(characters),
        "playable_roster_count": int(plan.get("playable_roster_count") or 0),
        "nonplayable_character_count": int(plan.get("nonplayable_character_count") or 0),
        "selected_run_character_count": int(plan.get("import_character_count") or 0),
        "characters": characters,
    }


def write_all_character_plan_outputs(
    plan: dict[str, Any],
    *,
    work_root: Path = DEFAULT_ALL_CHARACTER_WORK_ROOT,
    catalog_path: Path = DEFAULT_ALL_CHARACTER_CATALOG_PATH,
) -> tuple[Path, Path]:
    import json

    plan_path = work_root / "all_character_model_import_plan.json"
    for path, value in (
        (plan_path, plan),
        (catalog_path, all_character_catalog_from_plan(plan)),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(value, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return plan_path, catalog_path
