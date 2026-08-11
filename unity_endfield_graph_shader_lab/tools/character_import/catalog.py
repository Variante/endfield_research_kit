#!/usr/bin/env python3
"""Build a playable-character/UI-animation catalog from exported game data.

The roster is not maintained here.  A character is considered a concrete
playable model when a ``CharacterTable`` row joins to an Animator named
``<charId>_postmodel`` in the shipped ``postmodels/characters`` container.
That join deliberately excludes selector rows such as ``chr_9000_endmin`` and
also avoids accidentally choosing the NPC copy of a playable post-model.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from endfield_asset_map_filter import iter_asset_entries


VIEWER_DISPLAY_ALIASES = {
    # CharacterTable's shipped English name is "Arcane"; retain it while
    # making the source actor identity users search for discoverable.
    "lizhiyan": "Li Zhiyan",
}


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
BASE_CHARACTER_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "StreamingAssets"
    / "Table"
    / "CharacterTable.json"
)
PATCH_CHARACTER_TABLE = (
    REPO_ROOT
    / "export_full"
    / "structured"
    / "Persistent"
    / "Table"
    / "CharacterTable.json"
)
# Persistent is the installed patch overlay.  New playable rows can arrive
# there before they exist in the StreamingAssets baseline (Liino in 1.1 is the
# first observed case), and the exported table is a complete merged payload.
DEFAULT_CHARACTER_TABLE = (
    PATCH_CHARACTER_TABLE if PATCH_CHARACTER_TABLE.is_file() else BASE_CHARACTER_TABLE
)
DEFAULT_ASSET_MAPS = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "maps"
    / "endfield_streamingassets_assets.json",
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "maps"
    / "endfield_persistent_assets.json",
)
DEFAULT_WORK_ROOT = REPO_ROOT / "scratch" / "character_ui_import"
DEFAULT_UI_CONTROLLER_ROOTS = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "AnimatorController",
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "json_by_type"
    / "AnimatorController",
)
DEFAULT_CATALOG_PATH = (
    PROJECT_ROOT
    / "Assets"
    / "EndfieldGraphShaderLab"
    / "Generated"
    / "Characters"
    / "Catalog"
    / "playable_character_ui_catalog.json"
)

DEFAULT_CLIP_SCOPE = "overview"
SUPPORTED_CLIP_SCOPES = ("overview", "overview-team", "all-ui")

_CHARACTER_ID_RE = re.compile(r"^chr_(?P<number>\d{4})_(?P<token>[a-z0-9]+)$", re.IGNORECASE)
_ACTOR_CLIP_RE = re.compile(r"^A_actor_(?P<token>[^_]+)_(?P<suffix>.+)$", re.IGNORECASE)
_ITEM_WIDGET_RE = re.compile(r"^A_item_widget_(?P<token>[^_]+)_(?P<suffix>.+)$", re.IGNORECASE)
_UI_DECO_RE = re.compile(
    r"^(?P<character_id>chr_\d{4}_[a-z0-9]+)_deco_(?P<slot>\d+)$",
    re.IGNORECASE,
)
_UI_DECO_CONTROLLER_RE = re.compile(
    r"(?:^|/)prefabs/uimodels/decoitems/"
    r"(?P<prefab>(?P<character_id>chr_\d{4}_[a-z0-9]+)_deco_(?P<slot>\d+))"
    r"_controller\.controller$",
    re.IGNORECASE,
)
_UI_DECO_CONTROLLER_ASSET_RE = re.compile(
    r"(?:^|/)prefabs/uimodels/decoitems/"
    r"(?P<prefab>(?P<character_id>chr_\d{4}_[a-z0-9]+)_deco_(?P<slot>\d+))"
    r"(?:_controller\.controller|\.prefab)$",
    re.IGNORECASE,
)
_WIDGET_CLIP_FAMILY_RE = re.compile(
    r"^(?P<family>A_(?:item_widget|widget|item_effect|npc_animal|wpn_misc)_.+?)"
    r"(?:_ui_|_uiteam_|_gacha|_relax_|_disappear|_disapper|_displayoff)",
    re.IGNORECASE,
)
_CAMERA_TOKEN_RE = re.compile(r"(?:^|_)cam(?:_|$)", re.IGNORECASE)

_WIDGET_NAME_TOKENS = (
    "item_widget",
    "widget",
    "item_effect",
    "npc_animal",
    "wpn_misc",
)
_WIDGET_UI_TOKENS = (
    "_ui_",
    "_uiteam_",
    "_gacha",
    "_relax_",
    "_disappear",
    "_disapper",
    "_displayoff",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _asset_root_for_map(path: Path) -> str:
    if path.parent.name.lower() == "maps":
        return path.parent.parent.name
    return path.stem


def _entry_copy(entry: dict[str, Any], asset_root: str) -> dict[str, Any]:
    result = dict(entry)
    result["_asset_root"] = asset_root
    return result


def _entry_identity(entry: dict[str, Any]) -> tuple[str, str, int, str, int]:
    return (
        str(entry.get("_asset_root") or ""),
        str(entry.get("Source") or ""),
        int(entry.get("PathID") or 0),
        str(entry.get("Type") or ""),
        int(entry.get("Offset") or 0),
    )


def _dedupe_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str, int, str, int]] = set()
    for entry in entries:
        identity = _entry_identity(entry)
        if identity in seen:
            continue
        seen.add(identity)
        result.append(entry)
    return result


def _entry_sort_key(entry: dict[str, Any]) -> tuple[int, int, str, str, int]:
    asset_root = str(entry.get("_asset_root") or "")
    container = str(entry.get("Container") or "").replace("\\", "/").lower()
    return (
        0 if asset_root.lower() == "streamingassets" else 1,
        0 if "/postmodels/characters/" in container else 1,
        container,
        str(entry.get("Source") or "").lower(),
        int(entry.get("Offset") or 0),
    )


def _safe_folder_name(token: str) -> str:
    parts = [part for part in re.split(r"[^A-Za-z0-9]+", token) if part]
    return "".join(part[:1].upper() + part[1:] for part in parts) or "Character"


def _character_rows(character_table: Path) -> list[dict[str, Any]]:
    raw = _load_json(character_table)
    if not isinstance(raw, dict):
        raise ValueError(f"CharacterTable root must be an object: {character_table}")

    rows: list[dict[str, Any]] = []
    for key, value in raw.items():
        if not isinstance(value, dict):
            continue
        char_id = str(value.get("charId") or key)
        match = _CHARACTER_ID_RE.fullmatch(char_id)
        if not match:
            continue
        row = dict(value)
        row["charId"] = char_id
        row["_actor_token"] = match.group("token").lower()
        rows.append(row)
    rows.sort(key=lambda row: (int(row.get("sortOrder") or 999999), str(row["charId"])))
    return rows


def _is_actor_ui_suffix(suffix: str) -> bool:
    lowered = suffix.lower()
    return lowered.startswith("ui_") or lowered.startswith("uiteam_") or lowered.startswith("gacha")


def _is_actor_body_animation_entry(entry: dict[str, Any]) -> bool:
    """Require the shipped actor-animation container, not only an actor-like name.

    Endfield also names external UI effect rigs ``A_actor_*``.  The known
    Endministrator-F example lives below ``arts/effects/commonassets`` and its
    transform CRCs do not exist in the playable post-model hierarchy.
    """

    container = str(entry.get("Container") or "").replace("\\", "/").casefold()
    return "/arts/entity/actor/" in container and "/animations/" in container


def _is_external_camera_clip(name: str) -> bool:
    match = _ACTOR_CLIP_RE.fullmatch(name)
    return bool(match and _CAMERA_TOKEN_RE.search(match.group("suffix")))


def _contains_token_segment(value: str, token: str) -> bool:
    return re.search(rf"(?:^|_){re.escape(token)}(?:_|$)", value, re.IGNORECASE) is not None


def _is_direct_widget_ui_clip(name: str, token: str) -> bool:
    """Recognize actor-named UI props without guessing shared weapon ownership.

    Endfield uses several original prefixes (``A_item_widget``, ``A_widget``,
    ``A_item_effect``, and ``A_npc_animal``).  Requiring the actor token as a
    complete underscore-delimited segment avoids the known Pograni/Wulfa
    false association.  Shared ``A_wpn_misc`` clips are intentionally left for
    later controller-graph recovery because their names carry no actor key.
    """

    lowered = name.casefold()
    return (
        _contains_token_segment(lowered, token.casefold())
        and any(marker in lowered for marker in _WIDGET_NAME_TOKENS)
        and any(marker in lowered for marker in _WIDGET_UI_TOKENS)
    )


def _widget_clip_family(name: str) -> str:
    """Return the stable source family before a widget UI-state suffix."""

    match = _WIDGET_CLIP_FAMILY_RE.match(name)
    return match.group("family").casefold() if match else ""


def _deco_controller_owner(container: str) -> tuple[str, str] | None:
    """Resolve an exact actor/deco owner from a shipped controller container."""

    normalized = container.replace("\\", "/")
    match = _UI_DECO_CONTROLLER_RE.search(normalized)
    if not match:
        return None
    return match.group("character_id").casefold(), match.group("prefab").casefold()


def _exact_deco_controller_clip_refs(
    controller_roots: Iterable[Path],
) -> list[dict[str, Any]]:
    """Read exact private-deco controller clip PPtrs from exported JSON.

    Asset-map container ownership proves some generic clip *families*, but it
    misses clips stored in their original FBX rather than embedded beside the
    controller.  The controller's exact AnimationClip PPtrs are stronger and
    also disambiguate same-shaped private hierarchies such as Mifu deco 2/3.
    """

    result: list[dict[str, Any]] = []
    for root in controller_roots:
        root = Path(root)
        if not root.is_dir():
            continue
        asset_root = root.parents[1].name if len(root.parents) > 1 else ""
        for path in sorted(root.glob("*.json")):
            # The provenance container is near the beginning. Avoid parsing
            # multi-megabyte gameplay controllers that cannot own a UI deco.
            try:
                with path.open("r", encoding="utf-8") as handle:
                    prefix = handle.read(8192)
            except OSError:
                continue
            if "prefabs/uimodels/decoitems/" not in prefix.casefold():
                continue
            data = _load_json(path)
            container = str((data.get("$animestudio") or {}).get("container") or "")
            match = _UI_DECO_CONTROLLER_ASSET_RE.search(container.replace("\\", "/"))
            if not match:
                continue
            result.append(
                {
                    "character_id": match.group("character_id").casefold(),
                    "prefab": match.group("prefab").casefold(),
                    "controller_name": str(data.get("m_Name") or path.stem),
                    "source_json": str(path.resolve()),
                    "asset_root": asset_root,
                    "clip_path_ids": sorted(
                        {
                            int((item or {}).get("m_PathID") or 0)
                            for item in data.get("m_AnimationClips") or []
                            if int((item or {}).get("m_PathID") or 0)
                        }
                    ),
                }
            )
    return result


def _widget_ui_role(name: str) -> str:
    lowered = name.casefold().replace("disapper", "disappear").replace("displayoff", "disappear")
    for marker in ("_uiteam_", "_ui_", "_gacha", "_relax_", "_disappear"):
        index = lowered.find(marker)
        if index < 0:
            continue
        role = lowered[index + 1 :]
        if role.startswith("ui_"):
            role = role[3:]
        elif role.startswith("uiteam_"):
            role = "team_" + role[7:]
        return role
    return ""


def select_widget_ui_entries(
    entries: Iterable[dict[str, Any]],
    clip_scope: str,
) -> list[dict[str, Any]]:
    candidates = _best_unique_named_entries(entries)
    if clip_scope == "all-ui":
        return candidates

    selected: list[dict[str, Any]] = []
    for entry in candidates:
        lowered = str(entry.get("Name") or "").casefold()
        if (
            "_ui_overview_start" in lowered
            or "_ui_overview_loop" in lowered
            or lowered.endswith("_ui_overview_01")
        ):
            selected.append(entry)
            continue
        if clip_scope == "overview-team" and "_uiteam_" in lowered:
            selected.append(entry)
    return selected


def _clip_category(name: str) -> str:
    match = _ACTOR_CLIP_RE.fullmatch(name)
    suffix = match.group("suffix").lower() if match else name.lower()
    if suffix.startswith("uiteam_"):
        return "team_ui"
    if suffix.startswith("gacha"):
        return "gacha_ui"
    if "ui_overview" in suffix:
        return "charinfo_overview"
    if suffix.startswith("ui_"):
        return "character_ui"
    return "unknown"


def _clip_name_key(entry: dict[str, Any]) -> str:
    return str(entry.get("Name") or "").casefold()


def _best_unique_named_entries(entries: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entry in _dedupe_entries(entries):
        grouped[_clip_name_key(entry)].append(entry)
    result = [sorted(group, key=_entry_sort_key)[0] for group in grouped.values()]
    return sorted(result, key=lambda entry: str(entry.get("Name") or "").casefold())


def _is_overview_start(name: str) -> bool:
    lowered = name.lower()
    return "_ui_overview_start" in lowered and "loop" not in lowered


def _is_overview_loop(name: str) -> bool:
    lowered = name.lower()
    return "_ui_overview_loop" in lowered or "_ui_overview_start_loop" in lowered


def _is_primary_team_idle(name: str) -> bool:
    lowered = name.lower()
    return "_uiteam_idle" in lowered and (lowered.endswith("01") or lowered.endswith("_01"))


def _prefer_overview_name(name: str, role: str) -> tuple[int, int, str]:
    lowered = name.lower()
    if role == "start":
        exact = bool(re.search(r"_ui_overview_start(?:_01)?$", lowered))
    else:
        exact = bool(re.search(r"_ui_overview_loop(?:_01)?$", lowered))
    return (0 if exact else 1, len(name), lowered)


def select_ui_entries(entries: Iterable[dict[str, Any]], clip_scope: str) -> list[dict[str, Any]]:
    """Select skeletal actor UI clips without admitting cameras or gameplay clips."""

    if clip_scope not in SUPPORTED_CLIP_SCOPES:
        raise ValueError(f"unsupported clip scope {clip_scope!r}; choose from {SUPPORTED_CLIP_SCOPES}")
    body = [entry for entry in _best_unique_named_entries(entries) if not _is_external_camera_clip(str(entry.get("Name") or ""))]
    if clip_scope == "all-ui":
        return body

    starts = [entry for entry in body if _is_overview_start(str(entry.get("Name") or ""))]
    loops = [entry for entry in body if _is_overview_loop(str(entry.get("Name") or ""))]
    selected: list[dict[str, Any]] = []
    if starts:
        selected.append(sorted(starts, key=lambda item: _prefer_overview_name(str(item.get("Name") or ""), "start"))[0])
    if loops:
        selected.append(sorted(loops, key=lambda item: _prefer_overview_name(str(item.get("Name") or ""), "loop"))[0])
    if clip_scope == "overview-team":
        team = [entry for entry in body if _is_primary_team_idle(str(entry.get("Name") or ""))]
        if team:
            selected.append(sorted(team, key=lambda item: str(item.get("Name") or "").casefold())[0])
    return _dedupe_entries(selected)


def _preview_preferences(selected: list[dict[str, Any]]) -> list[str]:
    names = [str(entry.get("Name") or "") for entry in selected]
    loops = [name for name in names if _is_overview_loop(name)]
    starts = [name for name in names if _is_overview_start(name)]
    team = [name for name in names if "_uiteam_" in name.lower()]
    remainder = [name for name in names if name not in loops and name not in starts and name not in team]
    return loops + starts + team + remainder


def _relative_to_repo(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve()).replace("\\", "/")


def _source_fingerprint(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": _relative_to_repo(path),
        "bytes": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def build_import_plan(
    character_table: Path = DEFAULT_CHARACTER_TABLE,
    asset_maps: Iterable[Path] = DEFAULT_ASSET_MAPS,
    *,
    clip_scope: str = DEFAULT_CLIP_SCOPE,
    selected_actor_tokens: set[str] | None = None,
    work_root: Path = DEFAULT_WORK_ROOT,
    controller_roots: Iterable[Path] = DEFAULT_UI_CONTROLLER_ROOTS,
) -> dict[str, Any]:
    """Join CharacterTable, playable post-models, and original UI clips."""

    character_table = character_table.resolve()
    map_paths = tuple(path.resolve() for path in asset_maps)
    if not character_table.is_file():
        raise FileNotFoundError(f"CharacterTable not found: {character_table}")
    for path in map_paths:
        if not path.is_file():
            raise FileNotFoundError(f"AnimeStudio asset map not found: {path}")
    if clip_scope not in SUPPORTED_CLIP_SCOPES:
        raise ValueError(f"unsupported clip scope: {clip_scope}")

    rows = _character_rows(character_table)
    row_by_id = {str(row["charId"]).lower(): row for row in rows}
    token_to_id = {str(row["_actor_token"]).lower(): str(row["charId"]).lower() for row in rows}
    expected_postmodels = {f"{char_id}_postmodel": char_id for char_id in row_by_id}

    postmodels: dict[str, list[dict[str, Any]]] = defaultdict(list)
    ui_deco_prefabs: dict[str, list[dict[str, Any]]] = defaultdict(list)
    actor_ui: dict[str, list[dict[str, Any]]] = defaultdict(list)
    external_actor_ui_effects: dict[str, list[dict[str, Any]]] = defaultdict(list)
    companion_ui: dict[str, list[dict[str, Any]]] = defaultdict(list)
    widget_ui_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    widget_ui_by_path_id: dict[int, list[dict[str, Any]]] = defaultdict(list)
    controller_owned_widget_families: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    controller_owned_widget_clips: dict[str, dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    exact_controller_sources: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for map_path in map_paths:
        asset_root = _asset_root_for_map(map_path)
        for raw_entry in iter_asset_entries(map_path):
            entry_type = str(raw_entry.get("Type") or "")
            name = str(raw_entry.get("Name") or "")
            lowered_name = name.lower()
            if entry_type == "Animator" and lowered_name in expected_postmodels:
                postmodels[expected_postmodels[lowered_name]].append(_entry_copy(raw_entry, asset_root))
                continue
            if entry_type == "Animator":
                deco_match = _UI_DECO_RE.fullmatch(name)
                if deco_match:
                    char_id = deco_match.group("character_id").lower()
                    expected_suffix = (
                        "/prefabs/uimodels/decoitems/" + lowered_name + ".prefab"
                    )
                    container = str(raw_entry.get("Container") or "").replace("\\", "/").lower()
                    if char_id in row_by_id and container.endswith(expected_suffix):
                        ui_deco_prefabs[char_id].append(_entry_copy(raw_entry, asset_root))
                continue
            if entry_type != "AnimationClip":
                continue

            if (
                any(marker in lowered_name for marker in _WIDGET_NAME_TOKENS)
                and any(marker in lowered_name for marker in _WIDGET_UI_TOKENS)
            ):
                widget_ui_by_path_id[int(raw_entry.get("PathID") or 0)].append(
                    _entry_copy(raw_entry, asset_root)
                )

            widget_family = _widget_clip_family(name)
            if widget_family:
                copied = _entry_copy(raw_entry, asset_root)
                widget_ui_by_family[widget_family].append(copied)
                controller_owner = _deco_controller_owner(str(raw_entry.get("Container") or ""))
                if controller_owner and controller_owner[0] in row_by_id:
                    owner_char_id, owner_prefab = controller_owner
                    controller_owned_widget_families[owner_char_id][widget_family].add(owner_prefab)

            actor_match = _ACTOR_CLIP_RE.fullmatch(name)
            if actor_match:
                token = actor_match.group("token").lower()
                if token in token_to_id and _is_actor_ui_suffix(actor_match.group("suffix")):
                    copied = _entry_copy(raw_entry, asset_root)
                    if _is_actor_body_animation_entry(raw_entry):
                        actor_ui[token_to_id[token]].append(copied)
                    else:
                        external_actor_ui_effects[token_to_id[token]].append(copied)
                continue

            widget_match = _ITEM_WIDGET_RE.fullmatch(name)
            if widget_match:
                token = widget_match.group("token").lower()
                suffix = widget_match.group("suffix").lower()
                if token in token_to_id and ("_ui_" in f"_{suffix}" or "overview" in suffix):
                    companion_ui[token_to_id[token]].append(_entry_copy(raw_entry, asset_root))
                    continue

            for token, char_id in token_to_id.items():
                if _is_direct_widget_ui_clip(name, token):
                    companion_ui[char_id].append(_entry_copy(raw_entry, asset_root))
                    break

    # Resolve private controller PPtrs after the asset maps have supplied the
    # exact AnimationClip entries. This admits shared A_wpn_misc families that
    # carry no actor token and records an exact owner before hierarchy binding
    # tie-breaking. Controllers missing from the current export stay absent;
    # the downstream audit reports that evidence boundary explicitly.
    shipped_prefabs_by_character = {
        char_id: {
            str(entry.get("Name") or "").casefold()
            for entry in entries
        }
        for char_id, entries in ui_deco_prefabs.items()
    }
    for source in _exact_deco_controller_clip_refs(controller_roots):
        char_id = str(source["character_id"])
        prefab = str(source["prefab"])
        if prefab not in shipped_prefabs_by_character.get(char_id, set()):
            continue
        exact_controller_sources[char_id].append(source)
        for path_id in source["clip_path_ids"]:
            candidates = list(widget_ui_by_path_id.get(int(path_id)) or [])
            same_root = [
                entry
                for entry in candidates
                if str(entry.get("_asset_root") or "").casefold()
                == str(source.get("asset_root") or "").casefold()
            ]
            if same_root:
                candidates = same_root
            for entry in candidates:
                clip_name = str(entry.get("Name") or "")
                if not clip_name:
                    continue
                controller_owned_widget_clips[char_id][clip_name.casefold()].add(prefab)
                family = _widget_clip_family(clip_name)
                if family:
                    controller_owned_widget_families[char_id][family].add(prefab)
                value = dict(entry)
                value["_ownership_evidence"] = "exact_private_deco_animator_controller_pptr"
                value["_owner_prefabs"] = [prefab]
                value["_controller_name"] = str(source["controller_name"])
                companion_ui[char_id].append(value)

    # Some shipped companion assets intentionally use a generic source name.
    # Wulfa's apples are the concrete example: their clips are named
    # A_item_widget_apple_*, while an AnimationClip from the same family is
    # embedded in chr_0028_wulfa_deco_{1,3}_controller.controller.  That exact
    # controller container is a source ownership edge; use it to admit the
    # other UI clips in the same family without guessing from a shared name.
    for char_id, families in controller_owned_widget_families.items():
        shipped_prefabs = {
            str(entry.get("Name") or "").casefold()
            for entry in ui_deco_prefabs.get(char_id, [])
        }
        for family, owner_prefabs in families.items():
            proven_owner_prefabs = owner_prefabs & shipped_prefabs
            if not proven_owner_prefabs:
                continue
            for entry in widget_ui_by_family.get(family, []):
                value = dict(entry)
                value["_ownership_evidence"] = "exact_actor_ui_deco_controller_family"
                value["_owner_prefabs"] = sorted(proven_owner_prefabs)
                companion_ui[char_id].append(value)
        controller_owned_widget_families[char_id] = {
            family: prefabs & shipped_prefabs
            for family, prefabs in families.items()
            if prefabs & shipped_prefabs
        }

    concrete_rows: list[dict[str, Any]] = []
    excluded_rows: list[dict[str, Any]] = []
    selected_postmodels: dict[str, dict[str, Any]] = {}
    for row in rows:
        char_id = str(row["charId"]).lower()
        expected_container_suffix = f"/postmodels/characters/{char_id}_postmodel.prefab"
        candidates = _dedupe_entries(postmodels.get(char_id, []))
        playable_candidates = [
            entry
            for entry in candidates
            if str(entry.get("Container") or "").replace("\\", "/").lower().endswith(expected_container_suffix)
        ]
        if not playable_candidates:
            excluded_rows.append(
                {
                    "character_id": char_id,
                    "actor_token": row["_actor_token"],
                    "eng_name": str(row.get("engName") or ""),
                    "reason": "no exact Animator in shipped postmodels/characters container",
                    "postmodel_name_match_count": len(candidates),
                }
            )
            continue
        concrete_rows.append(row)
        selected_postmodels[char_id] = sorted(playable_candidates, key=_entry_sort_key)[0]

    if not concrete_rows:
        raise RuntimeError("CharacterTable did not join to any concrete playable post-models")

    duplicate_display_names: dict[str, int] = defaultdict(int)
    for row in concrete_rows:
        duplicate_display_names[str(row.get("engName") or row["charId"]).casefold()] += 1

    requested_tokens = {token.lower() for token in selected_actor_tokens} if selected_actor_tokens else None
    unknown_tokens = sorted((requested_tokens or set()) - {str(row["_actor_token"]) for row in concrete_rows})
    if unknown_tokens:
        raise ValueError(f"unknown playable actor token(s): {', '.join(unknown_tokens)}")

    characters: list[dict[str, Any]] = []
    for row in concrete_rows:
        char_id = str(row["charId"]).lower()
        token = str(row["_actor_token"]).lower()
        folder_name = _safe_folder_name(token)
        source_display = str(row.get("engName") or char_id)
        display_name = source_display
        if duplicate_display_names[source_display.casefold()] > 1:
            display_name = f"{source_display} ({token})"
        viewer_alias = VIEWER_DISPLAY_ALIASES.get(token, "")
        if viewer_alias and viewer_alias.casefold() not in display_name.casefold():
            display_name = f"{display_name} ({viewer_alias})"

        all_actor_entries = _best_unique_named_entries(actor_ui.get(char_id, []))
        deferred_effect_entries = _best_unique_named_entries(
            external_actor_ui_effects.get(char_id, [])
        )
        selected_entries = select_ui_entries(all_actor_entries, clip_scope)
        external_camera_entries = [
            entry for entry in all_actor_entries if _is_external_camera_clip(str(entry.get("Name") or ""))
        ]
        body_entries = [entry for entry in all_actor_entries if entry not in external_camera_entries]
        all_widget_entries = _best_unique_named_entries(companion_ui.get(char_id, []))
        for entry in all_widget_entries:
            exact_owners = controller_owned_widget_clips.get(char_id, {}).get(
                str(entry.get("Name") or "").casefold(),
                set(),
            )
            if exact_owners:
                entry["_ownership_evidence"] = "exact_private_deco_animator_controller_pptr"
                entry["_owner_prefabs"] = sorted(exact_owners)
        selected_widget_entries = select_widget_ui_entries(all_widget_entries, clip_scope)
        deco_entries = sorted(
            _dedupe_entries(ui_deco_prefabs.get(char_id, [])),
            key=lambda entry: (
                int((_UI_DECO_RE.fullmatch(str(entry.get("Name") or "")) or {"slot": 0})["slot"]),
                _entry_sort_key(entry),
            ),
        )
        enabled = requested_tokens is None or token in requested_tokens
        actor_work_root = work_root / "characters" / char_id
        scope_work_root = actor_work_root / "animation_scopes" / clip_scope
        manifest_asset_path = (
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/"
            f"{folder_name}/{token}_ui_recovery_manifest.json"
        )
        prefab_asset_path = (
            "Assets/EndfieldGraphShaderLab/Generated/Characters/Playable/"
            f"{folder_name}/Prefabs/{folder_name}.prefab"
        )
        characters.append(
            {
                "character_id": char_id,
                "actor_token": token,
                "source_display_name": source_display,
                "display_name": display_name,
                "folder_name": folder_name,
                "root_name": folder_name,
                "sort_order": int(row.get("sortOrder") or 0),
                "rarity": int(row.get("rarity") or 0),
                "import_enabled": enabled,
                "active": False,
                "postmodel_root": f"{char_id}_postmodel",
                "postmodel": selected_postmodels[char_id],
                "postmodel_name_candidates": sorted(postmodels.get(char_id, []), key=_entry_sort_key),
                "manifest_asset_path": manifest_asset_path,
                "prefab_asset_path": prefab_asset_path,
                "work_paths": {
                    "root": str(actor_work_root.resolve()),
                    "hierarchy": str((actor_work_root / "hierarchy").resolve()),
                    "meshes": str((actor_work_root / "meshes").resolve()),
                    "animation_clips": str((scope_work_root / "animation_clips").resolve()),
                    "samples": str((scope_work_root / "samples").resolve()),
                    "widget_hierarchy": str((actor_work_root / "item_widgets" / "hierarchy").resolve()),
                    "widget_meshes": str((actor_work_root / "item_widgets" / "meshes").resolve()),
                    "widget_animation_clips": str(
                        (scope_work_root / "item_widgets" / "animation_clips").resolve()
                    ),
                    "widget_samples": str((scope_work_root / "item_widgets" / "samples").resolve()),
                    "filters": str((scope_work_root / "filters").resolve()),
                    "manifest_report": str((scope_work_root / "manifest_report.json").resolve()),
                },
                "ui_animation": {
                    "clip_scope": clip_scope,
                    "actor_ui_source_count": len(all_actor_entries),
                    "skeletal_body_ui_count": len(body_entries),
                    "external_camera_count": len(external_camera_entries),
                    "external_ui_effect_count": len(deferred_effect_entries),
                    "companion_widget_count": len(all_widget_entries),
                    "selected_companion_widget_count": len(selected_widget_entries),
                    "selected_count": len(selected_entries),
                    "selected_names": [str(entry.get("Name") or "") for entry in selected_entries],
                    "preview_preference": _preview_preferences(selected_entries),
                    "selected_entries": selected_entries,
                    "body_entries": body_entries,
                    "external_camera_entries": external_camera_entries,
                    "external_ui_effect_entries": deferred_effect_entries,
                    "companion_widget_entries": all_widget_entries,
                    "selected_companion_widget_entries": selected_widget_entries,
                    "selected_companion_widget_names": [
                        str(entry.get("Name") or "") for entry in selected_widget_entries
                    ],
                },
                "ui_item_widgets": {
                    "prefab_count": len(deco_entries),
                    "prefab_entries": deco_entries,
                    "selection_rule": (
                        "exact Animator chr_<id>_<token>_deco_<slot> in "
                        "prefabs/uimodels/decoitems/<same-name>.prefab"
                    ),
                    "clip_rule": (
                        "actor-token widget/effect/creature UI clips plus generic widget families "
                        "owned by an exact chr_<id>_<token>_deco_<slot> controller container; "
                        "shared unnamed weapon clips remain controller-graph gaps"
                    ),
                    "controller_owned_clip_families": [
                        {
                            "family": family,
                            "owner_prefabs": sorted(prefabs),
                        }
                        for family, prefabs in sorted(
                            controller_owned_widget_families.get(char_id, {}).items()
                        )
                    ],
                    "controller_owned_clips": [
                        {
                            "name": name,
                            "owner_prefabs": sorted(prefabs),
                            "evidence": "exact_private_deco_animator_controller_pptr",
                        }
                        for name, prefabs in sorted(
                            controller_owned_widget_clips.get(char_id, {}).items()
                        )
                    ],
                    "exact_controller_sources": [
                        {
                            "prefab": str(item["prefab"]),
                            "controller_name": str(item["controller_name"]),
                            "source_json": str(item["source_json"]),
                            "clip_path_id_count": len(item["clip_path_ids"]),
                        }
                        for item in sorted(
                            exact_controller_sources.get(char_id, []),
                            key=lambda value: str(value["prefab"]),
                        )
                    ],
                },
                "source_table_row": {
                    "charId": char_id,
                    "engName": source_display,
                    "sortOrder": int(row.get("sortOrder") or 0),
                    "rarity": int(row.get("rarity") or 0),
                },
            }
        )

    enabled_characters = [character for character in characters if character["import_enabled"]]
    preferred_active = next(
        (character for character in enabled_characters if character["actor_token"] == "wulfa"),
        enabled_characters[0] if enabled_characters else None,
    )
    if preferred_active is not None:
        preferred_active["active"] = True

    missing_default_clips = [
        {
            "character_id": character["character_id"],
            "actor_token": character["actor_token"],
            "selected_names": character["ui_animation"]["selected_names"],
        }
        for character in enabled_characters
        if clip_scope != "all-ui" and character["ui_animation"]["selected_count"] < 2
    ]

    return {
        "schema_version": 2,
        "scope": "playable character post-models, original UI-deco prefabs, and UI animation",
        "clip_scope": clip_scope,
        "roster_rule": (
            "CharacterTable row joined by exact name to an Animator in "
            "postmodels/characters/<charId>_postmodel.prefab"
        ),
        "animation_rule": (
            "Only A_actor_<token>_ui_*, A_actor_<token>_uiteam_*, and "
            "A_actor_<token>_gacha* source clips under arts/entity/actor/.../animations are "
            "inventoried as body clips; name-matched effects/model rigs are deferred; actor-keyed "
            "widget/effect/creature UI clips and generic widget families source-owned by exact "
            "actor deco controller containers are matched to private deco hierarchies; "
            "camera clips are never loaded as body animation"
        ),
        "character_table": _source_fingerprint(character_table),
        "asset_maps": [_source_fingerprint(path) for path in map_paths],
        "table_row_count": len(rows),
        "roster_count": len(characters),
        "import_character_count": len(enabled_characters),
        "excluded_table_rows": excluded_rows,
        "missing_default_clip_pairs": missing_default_clips,
        "characters": characters,
    }


def unity_catalog_from_plan(plan: dict[str, Any]) -> dict[str, Any]:
    characters: list[dict[str, Any]] = []
    for source in plan.get("characters") or []:
        ui = source.get("ui_animation") or {}
        characters.append(
            {
                "character_id": source["character_id"],
                "actor_token": source["actor_token"],
                "display_name": source["display_name"],
                "source_display_name": source["source_display_name"],
                "root_name": source["root_name"],
                "sort_order": source["sort_order"],
                "rarity": source["rarity"],
                # Actor filters select work for one pipeline run; they must not
                # remove the remaining recovered actors from the shared viewer.
                "import_enabled": True,
                "selected_this_run": bool(source.get("import_enabled")),
                "active": bool(source.get("active")),
                "manifest_asset_path": source["manifest_asset_path"],
                "prefab_asset_path": source["prefab_asset_path"],
                "postmodel_root": source["postmodel_root"],
                "selected_ui_clips": list(ui.get("selected_names") or []),
                "preview_clip_preference": list(ui.get("preview_preference") or []),
                "source_ui_clip_count": int(ui.get("actor_ui_source_count") or 0),
                "deferred_external_ui_effect_count": int(
                    ui.get("external_ui_effect_count") or 0
                ),
                "selected_ui_clip_count": int(ui.get("selected_count") or 0),
                "ui_item_widget_prefab_count": int(
                    (source.get("ui_item_widgets") or {}).get("prefab_count") or 0
                ),
                "source_ui_item_widget_clip_count": int(ui.get("companion_widget_count") or 0),
                "selected_ui_item_widget_clips": list(
                    ui.get("selected_companion_widget_names") or []
                ),
            }
        )
    return {
        "schema_version": plan.get("schema_version", 1),
        "scope": plan.get("scope", ""),
        "clip_scope": plan.get("clip_scope", DEFAULT_CLIP_SCOPE),
        "roster_rule": plan.get("roster_rule", ""),
        "animation_rule": plan.get("animation_rule", ""),
        "character_table": plan.get("character_table", {}),
        "roster_count": int(plan.get("roster_count") or 0),
        "import_character_count": len(characters),
        "selected_run_character_count": int(plan.get("import_character_count") or 0),
        "excluded_table_rows": plan.get("excluded_table_rows") or [],
        "characters": characters,
    }


def write_plan_outputs(
    plan: dict[str, Any],
    *,
    work_root: Path = DEFAULT_WORK_ROOT,
    catalog_path: Path = DEFAULT_CATALOG_PATH,
) -> tuple[Path, Path]:
    plan_path = work_root / "playable_character_ui_import_plan.json"
    _write_json(plan_path, plan)
    _write_json(catalog_path, unity_catalog_from_plan(plan))
    return plan_path, catalog_path
