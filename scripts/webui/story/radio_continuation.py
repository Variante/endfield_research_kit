"""Recover authored radio-continuation edges from original LevelScript data."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .level_bindings import _load_levelscript_binding_data


StoryKeyResolver = Callable[[str], str]
LevelScriptLoader = Callable[[str], dict[str, Any]]


def build_radio_continuation_candidates(
    mission_id: str,
    level_ids: list[str],
    radio_table: dict[str, Any],
    resolve_story_key: StoryKeyResolver,
    *,
    load_levelscript: LevelScriptLoader = _load_levelscript_binding_data,
) -> list[dict[str, Any]]:
    """Return source-backed ``continueAfter*`` ordering candidates.

    A candidate requires two independent authored facts: a radio table row
    enables ``continueAfterDialog`` or ``continueAfterRadio``, and the target
    radio follows the matching predecessor in the same original LevelScript
    file's serialized string-hit order. The relation does not cross files and
    does not infer a mission owner or a branch selection.

    ``resolve_story_key`` is supplied by the language builder so only Story
    nodes actually owned by the mission can participate. ``load_levelscript``
    is injectable for focused tests; production uses the maintained
    LevelScript binding decoder directly.
    """
    candidates: list[dict[str, Any]] = []
    for level_id in dict.fromkeys(str(value) for value in level_ids if value):
        info = load_levelscript(level_id)
        for file_info in info.get("files") or []:
            last_dialog: dict[str, Any] | None = None
            last_radio: dict[str, Any] | None = None
            for hit in file_info.get("stringHits") or []:
                if not isinstance(hit, dict):
                    continue
                text = str(hit.get("text") or "").strip()
                story_key = str(resolve_story_key(text) or "").strip()
                if not story_key:
                    continue
                occurrence = {
                    "key": story_key,
                    "offset": hit.get("offset"),
                }
                if story_key.startswith(("dlg_", "misc_dlg_")):
                    last_dialog = occurrence
                if not story_key.startswith("radio_"):
                    continue
                radio_row = radio_table.get(story_key)
                if not isinstance(radio_row, dict):
                    continue
                after_dialog = bool(radio_row.get("continueAfterDialog"))
                after_radio = bool(radio_row.get("continueAfterRadio"))
                common = {
                    "mission": mission_id,
                    "levelId": level_id,
                    "file": str(file_info.get("file") or ""),
                    "radio": story_key,
                    "radioOffset": hit.get("offset"),
                    "continueAfterDialog": after_dialog,
                    "continueAfterRadio": after_radio,
                    "evidence": (
                        "authored_radio_continuation_flag_plus_same_file_"
                        "serialized_order"
                    ),
                    "missionOwnershipEvidence": False,
                    "branchSelectionEvidence": False,
                }
                if after_dialog and last_dialog is not None:
                    candidates.append({
                        **common,
                        "predecessor": last_dialog["key"],
                        "predecessorOffset": last_dialog.get("offset"),
                        "match": "after-dialog",
                    })
                if (
                    after_radio
                    and last_radio is not None
                    and last_radio["key"] != story_key
                ):
                    candidates.append({
                        **common,
                        "predecessor": last_radio["key"],
                        "predecessorOffset": last_radio.get("offset"),
                        "match": "after-radio",
                    })
                last_radio = occurrence
    return candidates
