"""Build a fail-closed final-catalog diff for the Characters page."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


SCHEMA_VERSION = 2
CATALOG_ROOT = Path("recovered/WebUI/characters")


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_catalogs(export_root: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    root = export_root / CATALOG_ROOT
    catalogs: dict[str, dict[str, Any]] = {}
    sources: list[str] = []
    invalid: list[str] = []
    if not root.is_dir():
        return catalogs, sources, invalid
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        relative = path.relative_to(export_root).as_posix()
        payload = _read_json(path)
        records = payload.get("records") if isinstance(payload, dict) else None
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            invalid.append(relative)
            continue
        language = str(payload.get("language") or path.stem).upper()
        catalogs[language] = payload
        sources.append(relative)
    return catalogs, sources, invalid


def _catalog_rows(catalogs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    rows: dict[str, dict[str, Any]] = {}
    for language, payload in sorted(catalogs.items()):
        for row in payload.get("records", []):
            key = str(row.get("id") or "").strip()
            if not key:
                continue
            snapshot = rows.setdefault(key, {"id": key, "languages": {}})
            snapshot["languages"][language] = row
    return rows


def _record_names(snapshot: dict[str, Any] | None) -> dict[str, str]:
    result: dict[str, str] = {}
    for language, row in (snapshot or {}).get("languages", {}).items():
        name = str(row.get("primaryName") or "").strip()
        if name:
            result[language] = name
    return result


def build_character_updates(previous_export_root: Path, export_root: Path) -> dict[str, Any]:
    """Compare the versioned final character catalogs used by the Characters page.

    Missing or invalid catalogs on either side produce an unavailable empty payload,
    so a legacy or partial export can never label every character added.
    """
    old_catalogs, old_sources, old_invalid = _load_catalogs(previous_export_root)
    new_catalogs, new_sources, new_invalid = _load_catalogs(export_root)
    old_languages = set(old_catalogs)
    new_languages = set(new_catalogs)
    common_languages = sorted(old_languages & new_languages)
    base: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": "final_character_catalog_diff",
        "previousSourceRoot": str(previous_export_root),
        "sourceRoot": str(export_root),
        "sourceFiles": {"previous": old_sources, "current": new_sources},
        "invalidSourceFiles": {"previous": old_invalid, "current": new_invalid},
        "available": False,
        "totals": {"added": 0, "modified": 0, "deleted": 0, "changed": 0},
        "entries": [],
        "localization": {
            "comparedLanguages": common_languages,
            "skippedLanguages": [
                {"language": language, "reason": "missing_on_one_side"}
                for language in sorted(old_languages ^ new_languages)
            ],
        },
    }
    if old_invalid or new_invalid or not common_languages:
        diagnostics = []
        if not old_sources:
            diagnostics.append("previous final character catalog missing")
        if not new_sources:
            diagnostics.append("current final character catalog missing")
        if old_invalid:
            diagnostics.append("previous final character catalog invalid")
        if new_invalid:
            diagnostics.append("current final character catalog invalid")
        if old_sources and new_sources and not common_languages:
            diagnostics.append("no common final character catalog language")
        base["skipReason"] = "missing_or_invalid_character_catalog"
        base["diagnostics"] = diagnostics
        return base

    old = _catalog_rows({language: old_catalogs[language] for language in common_languages})
    new = _catalog_rows({language: new_catalogs[language] for language in common_languages})
    if not old or not new:
        base["skipReason"] = "missing_or_invalid_character_catalog"
        base["diagnostics"] = ["final character catalog has no valid records on one or both sides"]
        return base

    entries: list[dict[str, Any]] = []
    for key in sorted(set(old) | set(new), key=str.casefold):
        old_row = old.get(key)
        new_row = new.get(key)
        if old_row is None:
            status = "added"
        elif new_row is None:
            status = "deleted"
        elif _canonical(old_row) != _canonical(new_row):
            status = "modified"
        else:
            continue
        entry: dict[str, Any] = {
            "status": status,
            "characterKey": key,
            "characterId": key,
        }
        old_names = _record_names(old_row)
        new_names = _record_names(new_row)
        if old_names:
            entry["oldNames"] = old_names
        if new_names:
            entry["newNames"] = new_names
        if old_row is not None:
            entry["oldRecord"] = old_row
        if new_row is not None:
            entry["newRecord"] = new_row
        if status == "modified":
            entry["changedFields"] = ["finalRecord"]
        entries.append(entry)

    totals = {status: sum(entry["status"] == status for entry in entries) for status in ("added", "modified", "deleted")}
    totals["changed"] = sum(totals.values())
    base.update({"available": True, "totals": totals, "entries": entries})
    return base
