"""Export-only source-record comparisons for semantic page badges.

These are authored-source changes, not diffs of recovered page publications.
Both exports use the same projection. Linked localization participates only in
languages present on both sides. Missing primary catalogs fail closed; deleted
IDs stay in the sidecar, but are never inserted into current page datasets.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from scripts.source_paths import ExportLayout, ExportLayoutError
from scripts.webui.story.story_keys import canonical_cutscene_key
from scripts.game_data.unity_store import UnityStoreError, open_store_if_present
from scripts.webui.updates.details import source_changes
from scripts.webui.updates.production import production_source_records
from scripts.webui.updates.scanner import (
    TEXT_DIFF_MAX_BYTES, TEXT_KIND_BINARY, TEXT_KIND_DECODED_PARTIAL,
    TEXT_KIND_DECODED_WHOLE, build_text_diff, textual_form,
)


GAMEPLAY_TABLES = {
    "character": "CharacterTable", "weapon": "WeaponBasicTable",
    "equipment": "EquipTable", "enemy": "EnemyTable", "item": "UseItemTable",
}


def _story_text_key(key: str) -> str:
    if key.startswith("black_"):
        match = re.fullmatch(r"(black_.+_\d+(?:d\d+)?)_\d+", key)
    else:
        match = re.fullmatch(r"(cutscene_.+)_\d+(?:d\d+)?(?:_[fm])?", key)
    return match.group(1) if match else ""


def _story_dialog_key(key: str) -> str:
    match = re.fullmatch(r"dlg_(.+)_(\d+)_(\d+)", key)
    if match:
        return f"dlg_{match.group(1)}_{int(match.group(2))}"
    return f"misc_{re.sub(r'_\d+(_\d+)?$', '', key)}"


STORY_TABLES = {
    "DialogTextTable": _story_dialog_key,
    "TextTable": _story_text_key,
    "SNSDialogTable": lambda key: key,
    "RadioTable": lambda key: key,
    "RemoteCommonTable": lambda key: key,
    "EnvTalkTable": lambda key: f"env_{key}",
    "RichContentTable": lambda key: f"nar_{key}",
    "WikiEntryDataTable": lambda key: key,
}


def _read_object(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected an object: {path}")
    return payload


def _values(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _values(item)
    elif isinstance(value, list):
        for item in value:
            yield from _values(item)
    else:
        yield value


def _string_references(value: Any):
    if isinstance(value, dict):
        # Text handles and rendered descriptions are not table row links.
        if "id" in value and set(value) <= {"id", "text"}:
            return
        for item in value.values():
            yield from _string_references(item)
    elif isinstance(value, list):
        for item in value:
            yield from _string_references(item)
    elif isinstance(value, str) and not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", value):
        yield value


def _localized(row: Any, localization: dict[str, dict[str, Any]]) -> dict[str, Any]:
    # Only the text handles stored in this record participate, not entire
    # translation tables (which would mark unrelated entries modified).
    def text_handles(item):
        if isinstance(item, dict):
            # I18nText is an id/text wrapper. Numeric stats and coordinates
            # must never resolve to a translation by accidental equality.
            if "id" in item and set(item) <= {"id", "text"}:
                yield str(item["id"])
            for child in item.values():
                yield from text_handles(child)
        elif isinstance(item, list):
            for child in item:
                yield from text_handles(child)
    handles = set(text_handles(row))
    return {language: {key: table[key] for key in sorted(handles & table.keys())}
            for language, table in localization.items()}


def _add(records, key, source, row, localization):
    if key:
        records.setdefault(key, {})[source] = {"record": row, "text": _localized(row, localization)}


def _story(layout, tables, localization, *, include_unity=False):
    records: dict[str, Any] = {}
    for name, key_for in STORY_TABLES.items():
        for key, row in tables.get(name, {}).items():
            _add(records, key_for(key), f"{name}/{key}", row, localization)
    # Options belong to their explicitly named dialog scene. No mission-wide
    # name or proximity join is used.
    for name, pattern in (
        ("DialogOptionTable", r"option_dlg_(.+)_(\d+(?:d\d+)?)_\d+_\d+"),
        ("DialogSummaryTable", r"summary_(.+)_(\d+(?:d\d+)?)_\d+"),
    ):
        for key, row in tables.get(name, {}).items():
            match = re.fullmatch(pattern, key)
            scene = ""
            if match:
                mission, scene_token = match.group(1), match.group(2)
                scene = (f"dlg_{mission}_{int(scene_token)}" if scene_token.isdigit()
                         else f"misc_dlg_{mission}_{scene_token}")
            if scene in records:
                _add(records, scene, f"{name}/{key}", row, localization)
    for key, sources in records.items():
        for source in list(sources):
            name, row_id = source.split("/", 1)
            if name == "SNSDialogTable":
                row = tables[name][row_id]
                chat = str(row.get("chatId") or "")
                if chat in tables.get("SNSChatTable", {}):
                    _add(records, key, f"SNSChatTable/{chat}", tables["SNSChatTable"][chat], localization)
                for option in _values(row):
                    if isinstance(option, str) and option in tables.get("SNSDialogOptionTable", {}):
                        _add(records, key, f"SNSDialogOptionTable/{option}", tables["SNSDialogOptionTable"][option], localization)
    store = open_store_if_present(layout.root) if include_unity else None
    if store is not None:
        with store:
            for kind in ("MonoBehaviour", "PlayableDirector"):
                for row in store.rows(kind, "*cutscene_*.json"):
                    key = canonical_cutscene_key(row.object_name or "")
                    if key:
                        records.setdefault(key, {}).setdefault(f"{kind}/{row.object_name}", []).append(row.sha256)
        for sources in records.values():
            for value in sources.values():
                if isinstance(value, list):
                    value.sort()
    return records


def _gameplay(layout, tables, localization, *, file_families=()):
    records: dict[str, Any] = {}
    file_hashes: dict[Path, str] = {}
    # Resolve authored string row references in tables used by Gameplay. Exact
    # references capture shared skills, growth and equipment records; numeric
    # enums and array positions are never treated as row identities.
    domains = ("Item", "UseItem", "Weapon", "SkillPatch", "Character", "Char", "Equip", "Enemy", "PotentialTalent", "Reward", "RecoverAp", "UsableItem", "Spaceship")
    index: dict[str, list[tuple[str, Any]]] = {}
    for name, rows in tables.items():
        if name.startswith(domains):
            for key, row in rows.items():
                index.setdefault(key, []).append((name, row))
    for kind, name in GAMEPLAY_TABLES.items():
        for key, row in tables.get(name, {}).items():
            record_key = f"{kind}:{key}"
            pending = [key]
            seen = set()
            while pending:
                ref = pending.pop()
                if ref in seen:
                    continue
                seen.add(ref)
                for table, linked in index.get(ref, []):
                    _add(records, record_key, f"{table}/{ref}", linked, localization)
                    pending.extend(value for value in _string_references(linked)
                                   if value in index and value not in seen)
            # Serialized SkillData and BuffData remain bytes, compared by hash.
            for value in list(_values(records.get(record_key, {}))):
                if isinstance(value, str) and value.startswith("Data/Json/"):
                    if value.split("/")[2] not in file_families:
                        continue
                    path = layout.game_file(value)
                    if path.is_file():
                        if path not in file_hashes:
                            file_hashes[path] = hashlib.sha256(path.read_bytes()).hexdigest()
                        records[record_key][path.relative_to(layout.root).as_posix()] = file_hashes[path]
    return records


def _map(layout, tables, localization, *, families=()):
    records: dict[str, Any] = {}
    basic_path = layout.json_dir / "GameplayConfig" / "LevelBasicInfoTable.json"
    basic = _read_object(basic_path)
    registry_path = layout.json_dir / "GameplayConfig" / "WorldEntityRegistry.json"
    if not registry_path.is_file():
        raise ValueError(f"missing Map world registry: {registry_path}")
    from scripts.webui.map.build_map_recovery_data import _registry_by_level

    if any(not isinstance(row, dict) or "idNum" not in row for row in basic.values()):
        raise ValueError(f"missing Map level idNum: {basic_path}")
    registry = _registry_by_level(_read_object(registry_path),
                                 {key: int(row["idNum"]) for key, row in basic.items()})
    for key, row in basic.items():
        _add(records, key, f"LevelBasicInfoTable/{key}", row, localization)
        records[key]["WorldEntityRegistry"] = registry.get(key, {})
        for family in families:
            folder = layout.json_dir / family / key
            paths = sorted(folder.rglob("*")) if folder.is_dir() else [folder.with_suffix(".json")]
            for path in paths:
                if path.is_file():
                    records[key][path.relative_to(layout.root).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
    return records


def _file_comparison(source: str, status: str, roots: list[Path]) -> dict[str, Any]:
    """Use the feed's bounded maintained readers for a changed linked file."""
    result: dict[str, Any] = {"path": source, "status": status}
    texts = []
    kinds = []
    for side, root in zip(("old", "new"), roots):
        path = root / source
        if not path.is_file():
            texts.append("")
            continue
        size = path.stat().st_size
        result[f"{side}_size"] = size
        if size > TEXT_DIFF_MAX_BYTES:
            result["text_diff_note"] = "binary_too_large"
            texts.append(None)
            continue
        text, kind = textual_form(source, path.read_bytes())
        texts.append(text)
        kinds.append(kind)
    if kinds:
        result["text_kind"] = (TEXT_KIND_BINARY if TEXT_KIND_BINARY in kinds else
                               TEXT_KIND_DECODED_PARTIAL if TEXT_KIND_DECODED_PARTIAL in kinds else kinds[-1])
    diff, truncated = build_text_diff(*texts, fromfile=f"a/{source}", tofile=f"b/{source}")
    if diff:
        result.update(text_diff=diff, text_diff_truncated=truncated)
    elif "text_diff_note" not in result:
        result["text_diff_note"] = ("decoded_identical" if any(kind in
            (TEXT_KIND_DECODED_PARTIAL, TEXT_KIND_DECODED_WHOLE) for kind in kinds) else "binary_no_reader")
    return result


def _production(layout, tables, localization):
    records: dict[str, Any] = {}
    for key, sources in production_source_records(tables).items():
        for source, row in sources.items():
            _add(records, key, source, row, localization)
    return records


def build_page_updates(previous_root: Path, current_root: Path) -> dict[str, dict[str, Any]]:
    """Return independently available, uncapped page sidecars for two exports."""
    result = {}
    layouts = [ExportLayout(previous_root), ExportLayout(current_root)]
    tables = []
    diagnostics = []
    for layout in layouts:
        loaded = {}
        try:
            layout.require()
            for path in sorted(layout.table_dir.glob("*.json")):
                loaded[path.stem] = _read_object(path)
        except (OSError, ValueError, ExportLayoutError) as exc:
            diagnostics.append(str(exc))
        tables.append(loaded)
    languages = sorted({name for name in tables[0] if name.startswith("I18nTextTable_")}
                       & {name for name in tables[1] if name.startswith("I18nTextTable_")})
    localization = [{name.removeprefix("I18nTextTable_"): side[name] for name in languages} for side in tables]
    # Optional inputs must exist on both sides, just like localization. An
    # incomplete optional lane must not turn an entire family into additions.
    common_tables = tables[0].keys() & tables[1].keys()
    tables = [{name: side[name] for name in common_tables} for side in tables]
    include_unity = all(layout.unity_store_path.is_file() for layout in layouts)
    file_families = {path.name for path in layouts[0].json_dir.iterdir() if path.is_dir()} & {
        path.name for path in layouts[1].json_dir.iterdir() if path.is_dir()
    } if all(layout.json_dir.is_dir() for layout in layouts) else set()
    map_families = [name for name in ("LevelConfig", "LevelData", "LevelScriptData", "MapConfig")
                    if name in file_families]
    file_comparisons = {}
    for page, projector, required in (
        ("story", lambda layout, rows, text: _story(layout, rows, text, include_unity=include_unity), ("DialogTextTable", "TextTable")),
        ("gameplay", lambda layout, rows, text: _gameplay(layout, rows, text, file_families=file_families), tuple(GAMEPLAY_TABLES.values())),
        ("map", lambda layout, rows, text: _map(layout, rows, text, families=map_families), ()),
        ("production", _production, ("ItemTable",)),
    ):
        payload = {"schemaVersion": 3, "generated": int(time.time()),
                   "source": "export_source_record_diff", "page": page,
                   "previousSourceRoot": str(previous_root), "sourceRoot": str(current_root),
                   "comparedLanguages": [name.removeprefix("I18nTextTable_") for name in languages],
                   "available": False, "entries": [],
                   "totals": {"added": 0, "modified": 0, "deleted": 0, "changed": 0}}
        result[page] = payload
        if page == "map":
            payload["comparedFamilies"] = map_families
            payload["skippedFamilies"] = [name for name in ("LevelConfig", "LevelData", "LevelScriptData", "MapConfig")
                                          if name not in map_families]
        try:
            page_tables = tables
            if diagnostics:
                raise ValueError("; ".join(diagnostics))
            if required:
                present = [name for name in required if tables[0].get(name) and tables[1].get(name)]
                if (page == "gameplay" and not present) or (page != "gameplay" and len(present) != len(required)):
                    raise ValueError(f"missing or empty primary {page} tables")
                if page == "gameplay":
                    payload["comparedKinds"] = [kind for kind, name in GAMEPLAY_TABLES.items() if name in present]
                    payload["skippedKinds"] = [kind for kind, name in GAMEPLAY_TABLES.items() if name not in present]
                    page_tables = [{name: rows for name, rows in side.items()
                                    if name not in required or name in present} for side in tables]
            old, new = [projector(layout, side, text) for layout, side, text in zip(layouts, page_tables, localization)]
            if not old or not new:
                raise ValueError(f"empty {page} source catalog")
            for key in sorted(old.keys() | new.keys()):
                status = "added" if key not in old else "deleted" if key not in new else "modified"
                if status == "modified" and old[key] == new[key]:
                    continue
                changes = source_changes(old.get(key), new.get(key))
                for change in changes:
                    source = change["source"]
                    if source.startswith("game/") and ".." not in Path(source).parts:
                        cache_key = (source, change["status"])
                        if cache_key not in file_comparisons:
                            file_comparisons[cache_key] = _file_comparison(source, change["status"],
                                                                         [previous_root, current_root])
                        change["file"] = file_comparisons[cache_key]
                payload["entries"].append({"id": key, "status": status, "changes": changes})
                payload["totals"][status] += 1
            payload["totals"]["changed"] = len(payload["entries"])
            payload["available"] = True
        except (OSError, ValueError, sqlite3.Error, UnityStoreError) as exc:
            payload.update(skipReason="missing_or_invalid_source_catalog", diagnostics=[str(exc)])
    # Text exposes every table row, including its raw representation. Reuse
    # the collected tables and localization rather than scanning them again.
    reference = {"schemaVersion": 2, "generated": int(time.time()), "page": "reference",
                 "source": "export_source_record_diff", "previousSourceRoot": str(previous_root),
                 "sourceRoot": str(current_root), "available": not diagnostics,
                 "comparedLanguages": [name.removeprefix("I18nTextTable_") for name in languages],
                 "entries": [], "totals": {"added": 0, "modified": 0, "deleted": 0, "changed": 0}}
    if diagnostics:
        reference.update(skipReason="missing_or_invalid_source_catalog", diagnostics=diagnostics)
    else:
        for table in sorted(common_tables):
            # A language missing on either side is already excluded above.
            old, new = tables[0][table], tables[1][table]
            for key in sorted(old.keys() | new.keys()):
                source = f"{table}/{key}"
                before = {source: {"record": old[key], "text": _localized(old[key], localization[0])}} if key in old else None
                after = {source: {"record": new[key], "text": _localized(new[key], localization[1])}} if key in new else None
                if before == after:
                    continue
                status = "added" if key not in old else "deleted" if key not in new else "modified"
                reference["entries"].append({"id": source, "status": status, "changes": source_changes(before, after)})
                reference["totals"][status] += 1
        reference["totals"]["changed"] = len(reference["entries"])
    result["reference"] = reference
    return result
