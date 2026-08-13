"""Strict readers for published AnimeStudio object-index artifacts."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def iter_gzip_jsonl_objects(
    path: Path,
    *,
    error_type: type[Exception] = ValueError,
) -> Iterable[dict[str, Any]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise error_type(f"{path}:{line_number}: row is not an object")
                yield value
    except (OSError, json.JSONDecodeError) as exc:
        raise error_type(
            f"{path}: cannot read merged object index: {exc}"
        ) from exc
