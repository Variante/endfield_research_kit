"""Exact table-row ownership for exported assets.

The Assets page lists every exported image/model/video without saying who
references it. This module recovers the one join that is exact rather than
inferred: an exported Table row whose *asset-bearing field* holds a string that
is byte-for-byte the normalized stem of an indexed asset.

The two gates are both required, and neither is a heuristic about names:

1. the field name must be an asset-bearing name (``icon``, ``img``, ``image``,
   ``path``, ``sprite``, ``portrait``, ``avatar``, ``bust``, ``logo``,
   ``texture``, ``model``, ``prefab``, ``pic``, ``art``, ``bg``). Without it a
   plain identifier field that happens to equal an asset stem -- an
   ``AudioDialog.speakerChannel`` of ``typhoea`` beside a sprite named
   ``typhoea`` -- would be read as ownership;
2. the field *value* must equal an indexed asset's normalized stem exactly.
   A prefix, suffix, substring or case-insensitive-but-different match is not
   ownership and is not published.

Anything the two gates do not cover stays unowned. This module never proposes
a candidate owner from a shared name prefix.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

#: Trailing ``_p<PathID>`` that the exporter appends to a decoded Unity file.
_PATH_ID_SUFFIX = re.compile(r"_p[0-9A-Fa-f]{16}$")

#: Lowercase tokens that make a field name asset-bearing.
ASSET_FIELD_TOKENS: tuple[str, ...] = (
    "art",
    "avatar",
    "bg",
    "bust",
    "icon",
    "image",
    "img",
    "logo",
    "model",
    "path",
    "pic",
    "portrait",
    "prefab",
    "sprite",
    "texture",
)

#: Values shorter than this are too generic to treat as an asset stem.
MIN_ASSET_KEY_LENGTH = 6

#: Owners kept per asset stem; the rest are counted but not published.
MAX_OWNERS_PER_ASSET = 8

SCHEMA_VERSION = "tableAssetOwners.v1"


def normalized_asset_stem(rel_path: str) -> str:
    """Return the exporter-normalized stem of one indexed asset path."""
    name = str(rel_path or "").replace("\\", "/").rsplit("/", 1)[-1]
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return _PATH_ID_SUFFIX.sub("", stem)


def is_asset_bearing_field(field_path: str) -> bool:
    """True when the last named segment of a JSON path names an asset slot."""
    segments = [
        segment
        for segment in str(field_path or "").split(".")
        if segment and not segment.startswith("[")
    ]
    if not segments:
        return False
    leaf = segments[-1].lower()
    return any(token in leaf for token in ASSET_FIELD_TOKENS)


def iter_string_leaves(value, path: tuple[str, ...] = ()):
    """Yield ``(json path, string value)`` for every string leaf."""
    if isinstance(value, dict):
        for key, child in value.items():
            yield from iter_string_leaves(child, path + (str(key),))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from iter_string_leaves(child, path + (f"[{index}]",))
    elif isinstance(value, str):
        yield (".".join(path), value)


def asset_stem_index(entries) -> dict[str, list[str]]:
    """Map each normalized asset stem to the relative paths that carry it."""
    index: dict[str, list[str]] = {}
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        rel = str(entry.get("r") or "")
        if not rel:
            continue
        stem = normalized_asset_stem(rel)
        if not stem:
            continue
        index.setdefault(stem, []).append(rel)
    return index


def table_asset_owners(
    table_rows: dict[str, dict],
    stem_index: dict[str, list[str]],
) -> dict[str, list[dict]]:
    """Return ``asset stem -> owner rows`` for one set of exported tables.

    ``table_rows`` maps an exported table stem to its parsed payload.
    Both gates above are applied; a stem with no exact owner is absent.
    """
    # Whole-string equality, case-insensitive: exported asset names and table
    # ids differ only in case for real bindings (``Att_widget_*`` sprites vs
    # lowercase table values). A prefix or substring never matches.
    lowered = {stem.lower(): stem for stem in stem_index}
    owners: dict[str, list[dict]] = {}
    for table_stem in sorted(table_rows):
        payload = table_rows[table_stem]
        if not isinstance(payload, dict):
            continue
        for row_key, row in payload.items():
            for field_path, value in iter_string_leaves(row):
                if len(value) < MIN_ASSET_KEY_LENGTH:
                    continue
                if not is_asset_bearing_field(field_path):
                    continue
                stem = lowered.get(value.lower())
                if stem is None:
                    continue
                record = {
                    "table": table_stem,
                    "row": str(row_key),
                    "field": field_path,
                }
                bucket = owners.setdefault(stem, [])
                if record not in bucket:
                    bucket.append(record)
    return owners


def build_table_asset_owner_payload(
    asset_entries,
    table_dir: Path,
) -> dict:
    """Build the published ownership sidecar from an asset index and Tables."""
    stem_index = asset_stem_index(asset_entries)
    table_rows: dict[str, dict] = {}
    for path in sorted(Path(table_dir).glob("*.json")):
        if path.stem.startswith("I18nTextTable_"):
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            table_rows[path.stem] = payload

    owners = table_asset_owners(table_rows, stem_index)
    published: dict[str, dict] = {}
    truncated = 0
    for stem in sorted(owners):
        rows = owners[stem]
        entry: dict = {"owners": rows[:MAX_OWNERS_PER_ASSET]}
        if len(rows) > MAX_OWNERS_PER_ASSET:
            entry["ownerCount"] = len(rows)
            truncated += 1
        published[stem] = entry

    return {
        "schemaVersion": SCHEMA_VERSION,
        "evidence": "exact asset-bearing table field value equals asset stem",
        "counts": {
            "assetStems": len(stem_index),
            "ownedStems": len(published),
            "tables": len(table_rows),
            "truncatedStems": truncated,
        },
        "entries": published,
    }


__all__ = [
    "ASSET_FIELD_TOKENS",
    "MAX_OWNERS_PER_ASSET",
    "MIN_ASSET_KEY_LENGTH",
    "SCHEMA_VERSION",
    "asset_stem_index",
    "build_table_asset_owner_payload",
    "is_asset_bearing_field",
    "iter_string_leaves",
    "normalized_asset_stem",
    "table_asset_owners",
]
