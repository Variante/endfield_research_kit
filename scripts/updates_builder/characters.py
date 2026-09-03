"""Build a fail-closed CharacterTable semantic diff for the Characters page."""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 1
TABLE_ROOTS = (
    Path("structured/StreamingAssets/Table"),
    Path("structured/Persistent/Table"),
)
I18N_NAME_RE = re.compile(r"^I18nTextTable_([^.]+)\.json$", re.IGNORECASE)


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _load_merged_table(
    export_root: Path,
    filename: str,
) -> tuple[dict[str, Any], list[str], list[str]]:
    merged: dict[str, Any] = {}
    sources: list[str] = []
    invalid_sources: list[str] = []
    for relative_root in TABLE_ROOTS:
        path = export_root / relative_root / filename
        if not path.is_file():
            continue
        relative_path = path.relative_to(export_root).as_posix()
        payload = _read_json(path)
        if not isinstance(payload, dict):
            invalid_sources.append(relative_path)
            continue
        merged.update(payload)
        sources.append(relative_path)
    return merged, sources, invalid_sources


def _available_languages(export_root: Path) -> set[str]:
    languages: set[str] = set()
    for relative_root in TABLE_ROOTS:
        root = export_root / relative_root
        if not root.is_dir():
            continue
        for path in root.glob("I18nTextTable_*.json"):
            match = I18N_NAME_RE.match(path.name)
            if match:
                languages.add(match.group(1).upper())
    return languages


def _localized_name_snapshot(
    rows: dict[str, dict[str, Any]],
    language_tables: dict[str, dict[str, Any]],
) -> dict[str, dict[str, str]]:
    names: dict[str, dict[str, str]] = {key: {} for key in rows}
    text_ids = {
        key: str(node.get("id"))
        for key, row in rows.items()
        if isinstance((node := row.get("name")), dict)
        and node.get("id") not in (None, "", 0, "0")
    }
    for language, table in sorted(language_tables.items()):
        for key, text_id in text_ids.items():
            value = table.get(text_id)
            text = str(value or "").strip()
            if text:
                names[key][language] = text
    for key, row in rows.items():
        node = row.get("name")
        direct_text = str(node.get("text") or "").strip() if isinstance(node, dict) else ""
        if direct_text:
            names[key]["SOURCE"] = direct_text
        english = str(row.get("engName") or "").strip()
        if english:
            names[key].setdefault("EN", english)
    return names


def _identity(character_key: str, row: dict[str, Any]) -> str:
    char_id = str(row.get("charId") or "").strip()
    if char_id:
        return char_id
    match = re.match(r"^chr_\d+_(.+)$", character_key, re.IGNORECASE)
    return match.group(1) if match else character_key


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_character_updates(previous_export_root: Path, export_root: Path) -> dict[str, Any]:
    """Compare CharacterTable rows and their referenced localized names.

    Missing or invalid CharacterTable input on either side produces an unavailable,
    empty payload so a partial/first baseline can never label every character added.
    """
    old_rows, old_character_sources, old_character_invalid = _load_merged_table(
        previous_export_root, "CharacterTable.json"
    )
    new_rows, new_character_sources, new_character_invalid = _load_merged_table(
        export_root, "CharacterTable.json"
    )
    old = {str(key): row for key, row in old_rows.items() if isinstance(row, dict)}
    new = {str(key): row for key, row in new_rows.items() if isinstance(row, dict)}
    base: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": "character_table_semantic_diff",
        "previousSourceRoot": str(previous_export_root),
        "sourceRoot": str(export_root),
        "sourceFiles": {
            "previous": old_character_sources,
            "current": new_character_sources,
        },
        "invalidSourceFiles": {
            "previous": old_character_invalid,
            "current": new_character_invalid,
        },
        "available": False,
        "totals": {"added": 0, "modified": 0, "deleted": 0, "changed": 0},
        "entries": [],
    }
    if (
        not old_character_sources
        or not new_character_sources
        or old_character_invalid
        or new_character_invalid
        or not old
        or not new
    ):
        diagnostics = []
        if not old_character_sources:
            diagnostics.append("previous CharacterTable.json missing or invalid")
        if not new_character_sources:
            diagnostics.append("current CharacterTable.json missing or invalid")
        if old_character_invalid:
            diagnostics.append("previous CharacterTable overlay invalid")
        if new_character_invalid:
            diagnostics.append("current CharacterTable overlay invalid")
        if old_character_sources and not old:
            diagnostics.append("previous CharacterTable has no valid object rows")
        if new_character_sources and not new:
            diagnostics.append("current CharacterTable has no valid object rows")
        base["skipReason"] = "missing_or_invalid_character_table"
        base["diagnostics"] = diagnostics
        return base

    old_languages = _available_languages(previous_export_root)
    new_languages = _available_languages(export_root)
    compared_languages: list[str] = []
    skipped_languages: list[dict[str, str]] = []
    old_language_tables: dict[str, dict[str, Any]] = {}
    new_language_tables: dict[str, dict[str, Any]] = {}
    old_i18n_sources: list[str] = []
    new_i18n_sources: list[str] = []
    for language in sorted(old_languages | new_languages):
        if language not in old_languages or language not in new_languages:
            skipped_languages.append({"language": language, "reason": "missing_on_one_side"})
            continue
        old_table, old_sources, old_invalid = _load_merged_table(
            previous_export_root, f"I18nTextTable_{language}.json"
        )
        new_table, new_sources, new_invalid = _load_merged_table(
            export_root, f"I18nTextTable_{language}.json"
        )
        if old_invalid or new_invalid or not old_sources or not new_sources or not old_table or not new_table:
            skipped_languages.append({"language": language, "reason": "invalid_on_one_or_both_sides"})
            continue
        compared_languages.append(language)
        old_language_tables[language] = old_table
        new_language_tables[language] = new_table
        old_i18n_sources.extend(old_sources)
        new_i18n_sources.extend(new_sources)
    old_names = _localized_name_snapshot(old, old_language_tables)
    new_names = _localized_name_snapshot(new, new_language_tables)
    base["sourceFiles"] = {
        "previous": old_character_sources + old_i18n_sources,
        "current": new_character_sources + new_i18n_sources,
    }
    base["localization"] = {
        "comparedLanguages": compared_languages,
        "skippedLanguages": skipped_languages,
    }

    entries: list[dict[str, Any]] = []
    for key in sorted(set(old) | set(new), key=str.casefold):
        old_row = old.get(key)
        new_row = new.get(key)
        if old_row is None:
            status = "added"
        elif new_row is None:
            status = "deleted"
        else:
            row_changed = _canonical(old_row) != _canonical(new_row)
            names_changed = old_names.get(key, {}) != new_names.get(key, {})
            if not row_changed and not names_changed:
                continue
            status = "modified"

        reference_row = new_row or old_row or {}
        entry: dict[str, Any] = {
            "status": status,
            "characterKey": key,
            "characterId": _identity(key, reference_row),
        }
        if old_row is not None:
            names = old_names.get(key, {})
            if names:
                entry["oldNames"] = names
        if new_row is not None:
            names = new_names.get(key, {})
            if names:
                entry["newNames"] = names
        if status == "modified":
            changed_fields = []
            if _canonical(old_row) != _canonical(new_row):
                changed_fields.append("characterRow")
            if entry.get("oldNames", {}) != entry.get("newNames", {}):
                changed_fields.append("localizedNames")
            entry["changedFields"] = changed_fields
        entries.append(entry)

    totals = {status: sum(entry["status"] == status for entry in entries) for status in ("added", "modified", "deleted")}
    totals["changed"] = sum(totals.values())
    base.update({"available": True, "totals": totals, "entries": entries})
    return base
