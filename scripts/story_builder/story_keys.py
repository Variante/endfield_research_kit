"""Pure normalization of Story line and Timeline identifiers."""

from __future__ import annotations

import re
from typing import Any


_CUTSCENE_HASH_SUFFIX_RE = re.compile(r"_p[0-9A-Fa-f]{8,16}$")
_CUTSCENE_COMPONENT_SUFFIX_RE = re.compile(
    r"_(?:Actor|Audio|Effect|Light|Others)(?:_(?:cam_\d+|AU|CHI|CN|EN|ENG|JP|KO|KR|ENV))*$",
    re.IGNORECASE,
)
_CUTSCENE_LOCALE_SUFFIX_RE = re.compile(
    r"_(?:CHI|CN|EN|ENG|JP|KO|KR|ENV)$",
    re.IGNORECASE,
)


def canonical_cutscene_key(value: str) -> str:
    if not isinstance(value, str):
        return ""
    key = value.strip()
    if key.startswith("cutscene_"):
        pass
    elif match := re.match(r"^(?:f|m|fm)_(cutscene_.+)$", key, re.IGNORECASE):
        key = match.group(1)
    else:
        return ""
    key = "cutscene_" + key[len("cutscene_") :]
    key = _CUTSCENE_HASH_SUFFIX_RE.sub("", key)
    key = _CUTSCENE_COMPONENT_SUFFIX_RE.sub("", key)
    key = _CUTSCENE_LOCALE_SUFFIX_RE.sub("", key)
    return key if key != "cutscene" else ""


def line_stem(line_id: str) -> str:
    value = str(line_id or "")
    if value.startswith("dlg_"):
        return re.sub(r"_\d+$", "", value)
    if re.search(r"_\d+_\d+$", value):
        return re.sub(r"_\d+_\d+$", "", value)
    return re.sub(r"_\d+$", "", value) if re.search(r"_\d+$", value) else ""


def timeline_stem_to_dialog_key(timeline: str) -> str:
    value = str(timeline or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def string_list(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    for value in values:
        text = str(value if value is not None else "").strip()
        if text and text not in out:
            out.append(text)
    return out


__all__ = [
    "canonical_cutscene_key",
    "line_stem",
    "string_list",
    "timeline_stem_to_dialog_key",
]
