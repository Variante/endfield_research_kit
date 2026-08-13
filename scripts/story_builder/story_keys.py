"""Pure normalization of Story line and Timeline identifiers."""

from __future__ import annotations

import re


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


__all__ = ["line_stem", "timeline_stem_to_dialog_key"]
