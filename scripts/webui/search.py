"""Shared file-reference text for compact WebUI search projections.

Collect stored paths and basenames from nested published records, including
URL-encoded references. This is search metadata, never an ownership claim.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote

_FILE = re.compile(r"[^\s<>\"'?#=]+\.[a-z][a-z0-9]{0,11}(?=$|[\s<>\"'?#&])", re.I)
_SCALAR_FILE = re.compile(r"^[^?#]+\.[a-z][a-z0-9]{0,11}(?:[?#].*)?$", re.I)


def linked_file_search_text(*values: Any) -> str:
    """Return distinct stored/URL-decoded file paths and basenames."""
    files: dict[str, None] = {}
    seen: set[int] = set()

    def visit(value: Any) -> None:
        if isinstance(value, str):
            for text in dict.fromkeys((value, unquote(value))):
                normalized = text.replace("\\", "/")
                paths = _FILE.findall(normalized)
                if not re.search(r"[\n<>\"']", normalized) and _SCALAR_FILE.fullmatch(normalized):
                    paths.append(re.split(r"[?#]", normalized)[0])
                for path in paths:
                    files[path] = None
                    files[path.rsplit("/", 1)[-1]] = None
        elif isinstance(value, (dict, list, tuple)) and id(value) not in seen:
            seen.add(id(value))
            for child in value.values() if isinstance(value, dict) else value:
                visit(child)

    for value in values:
        visit(value)
    return "\n".join(files)
