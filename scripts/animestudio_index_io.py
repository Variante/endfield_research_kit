"""Shared readers for published AnimeStudio object indexes.

The exporter owns index production.  Consumers use this module to make the
published merged index the first source and to keep raw json_by_type as an
explicit, diagnosable compatibility path.
"""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


class ObjectIndexUnavailable(RuntimeError):
    """The published index is absent, incomplete, or malformed."""


def object_index_dir(export_root: Path, source: str) -> Path:
    return export_root / "recovered" / "AnimeStudio-cli" / source / "object_index"


def published_object_index_path(export_root: Path, source: str) -> Path:
    directory = object_index_dir(export_root, source)
    summary_path = directory / "summary.json"
    objects_path = directory / "objects.jsonl.gz"
    if not summary_path.is_file():
        raise ObjectIndexUnavailable(f"{source}: missing published object-index summary")
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObjectIndexUnavailable(f"{source}: unreadable object-index summary: {exc}") from exc
    if not isinstance(summary, dict) or summary.get("complete") is not True:
        raise ObjectIndexUnavailable(f"{source}: published object index is incomplete")
    outputs = summary.get("outputs")
    output = outputs.get("objects") if isinstance(outputs, dict) else None
    if not isinstance(output, dict):
        raise ObjectIndexUnavailable(f"{source}: published object output is not declared")
    declared = Path(str(output.get("path") or ""))
    if declared.name != declared.as_posix() or declared.name != objects_path.name:
        raise ObjectIndexUnavailable(f"{source}: unsafe or unsupported object output path")
    if not objects_path.is_file():
        raise ObjectIndexUnavailable(f"{source}: published object output is missing")
    return objects_path


def iter_published_objects(export_root: Path, source: str) -> Iterator[dict[str, Any]]:
    """Yield object rows from the validated merged index exactly once."""

    path = published_object_index_path(export_root, source)
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ObjectIndexUnavailable(
                        f"{source}: malformed object row {line_number}: {exc}"
                    ) from exc
                if not isinstance(row, dict) or row.get("recordType") != "object":
                    continue
                yield row
    except OSError as exc:
        raise ObjectIndexUnavailable(f"{source}: cannot read object index: {exc}") from exc


def raw_json_path_for_object(export_root: Path, source: str, row: dict[str, Any]) -> Path | None:
    """Resolve the conventional raw JSON path for an indexed object."""

    identity = row.get("object") if isinstance(row.get("object"), dict) else {}
    name = str(row.get("name") or "")
    try:
        path_id = int(identity.get("pathId"))
    except (TypeError, ValueError):
        return None
    if not name:
        return None
    path = (
        export_root / "recovered" / "AnimeStudio-cli" / source
        / "json_by_type" / str(row.get("type") or "MonoBehaviour")
        / f"{name}_p{path_id & ((1 << 64) - 1):016X}.json"
    )
    return path if path.is_file() else None
