"""Build a fail-closed final-catalog diff for the Characters page."""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

from scripts.common import ROOT, WEBUI_BUILD_DIR, rel_path
from scripts.source_paths import ExportLayout
from scripts.webui.characters.build_character_data import CONVERTED_MEDIA_TYPES


SCHEMA_VERSION = 3
CHARACTER_BUILDER_MODULE = "scripts.webui.characters.build_character_data"
CHARACTER_BUILDER_SOURCE = ROOT / "scripts" / "webui" / "characters" / "build_character_data.py"


def comparison_character_catalog_dir(export_root: Path, state_dir: Path) -> Path:
    """Build one export's Characters catalog for the Updates diff, cached.

    Both sides of the diff are built here by the same builder from the same
    kinds of input: that export's tables and its own converted media (no
    shared asset index), and no Story actor registry, which exists only for
    the export the WebUI was built from. A builder change or a Story-only
    input therefore never shows up as a game update. The cache key covers the
    builder source, the tables, and the media folders the builder scans.
    """
    layout = ExportLayout(export_root)
    digest = hashlib.sha256()
    digest.update(CHARACTER_BUILDER_SOURCE.read_bytes())
    digest.update(str(layout.root.resolve()).encode("utf-8"))
    for path in sorted(layout.table_dir.glob("*.json")):
        stat = path.stat()
        digest.update(f"{path.name}|{stat.st_size}|{stat.st_mtime_ns};".encode("utf-8"))
    for type_name in CONVERTED_MEDIA_TYPES:
        type_dir = layout.unity_type_dir(type_name)
        # A folder's mtime changes when a file is added, removed, or renamed.
        stamp = type_dir.stat().st_mtime_ns if type_dir.is_dir() else 0
        digest.update(f"{type_name}|{stamp};".encode("utf-8"))
    cache_dir = state_dir / "characters" / digest.hexdigest()[:16]
    catalog_dir = cache_dir / "catalog"
    if catalog_dir.is_dir() and any(catalog_dir.glob("*.json")):
        return catalog_dir
    languages = sorted(path.stem.upper() for path in (WEBUI_BUILD_DIR / "characters").glob("*.json")) or ["CN"]
    command = [
        sys.executable, "-m", CHARACTER_BUILDER_MODULE,
        "--export-root", str(export_root),
        "--out-dir", str(cache_dir / "lang"),
        "--snapshot-dir", str(catalog_dir),
        # No index file: the builder scans this export's own converted media.
        "--asset-index", str(cache_dir / "no-asset-index.json"),
        "--languages", *languages,
    ]
    result = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        # An unavailable catalog makes the diff unavailable, never "all added".
        print(
            f"[build_updates] character catalog build for {export_root} failed ({result.returncode}): "
            f"{result.stderr.strip()[-400:]}",
            file=sys.stderr,
        )
    return catalog_dir


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _load_catalogs(root: Path) -> tuple[dict[str, dict[str, Any]], list[str], list[str]]:
    catalogs: dict[str, dict[str, Any]] = {}
    sources: list[str] = []
    invalid: list[str] = []
    if not root.is_dir():
        return catalogs, sources, invalid
    for path in sorted(root.glob("*.json"), key=lambda item: item.name.casefold()):
        relative = rel_path(path)
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


def build_character_updates(
    previous_catalog_dir: Path,
    catalog_dir: Path,
    *,
    previous_source_root: Path,
    source_root: Path,
) -> dict[str, Any]:
    """Compare the versioned final character catalogs used by the Characters page.

    Missing or invalid catalogs on either side produce an unavailable empty payload,
    so a legacy or partial export can never label every character added.
    """
    old_catalogs, old_sources, old_invalid = _load_catalogs(previous_catalog_dir)
    new_catalogs, new_sources, new_invalid = _load_catalogs(catalog_dir)
    old_languages = set(old_catalogs)
    new_languages = set(new_catalogs)
    common_languages = sorted(old_languages & new_languages)
    base: dict[str, Any] = {
        "schemaVersion": SCHEMA_VERSION,
        "generated": int(time.time()),
        "source": "final_character_catalog_diff",
        "previousSourceRoot": str(previous_source_root),
        "sourceRoot": str(source_root),
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
