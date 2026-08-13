from __future__ import annotations

import re
import unicodedata
from typing import Any


CUTSCENE_SEMANTIC_SHAPES = frozenset({
    "unityTimeline",
    "unityTimelineWithIndependentFmv",
    "timelineComponentsWithoutRoot",
    "levelscriptFmv",
    "textOnlyUnconfirmed",
})


def cutscene_semantic_shape(cutscene: dict[str, Any]) -> str:
    """Classify one generated cutscene without implying runtime execution."""
    variants = [
        row for row in (cutscene.get("variants") or [])
        if isinstance(row, dict)
    ]
    has_components = bool(variants)
    has_root = any(row.get("part") == "root" for row in variants)
    has_levelscript_fmv = bool(cutscene.get("levelscriptFmvBindings"))
    text_only = bool(cutscene.get("textOnlyUnconfirmed"))

    if text_only and (has_components or has_levelscript_fmv):
        raise ValueError(
            "textOnlyUnconfirmed conflicts with authored cutscene evidence"
        )
    if has_root and has_levelscript_fmv:
        return "unityTimelineWithIndependentFmv"
    if has_root:
        return "unityTimeline"
    if has_components:
        return "timelineComponentsWithoutRoot"
    if has_levelscript_fmv:
        return "levelscriptFmv"
    if text_only:
        return "textOnlyUnconfirmed"
    raise ValueError("cutscene has no classifiable authored evidence")


def cutscene_subtitle_evidence(
    cutscene: dict[str, Any],
    lines: list[dict[str, Any]],
) -> str:
    if cutscene.get("hasSubtitleTrack"):
        return "authoredTrack"
    if lines:
        return "localizedTextWithoutTrack"
    return "none"


def normalize_subtitle_display_text(value: object) -> str:
    source = re.sub(r"\{[FM]\}", "", str(value or ""))
    return "".join(
        char.casefold()
        for char in source
        if not char.isspace()
        and not unicodedata.category(char).startswith("P")
    )


def select_subtitle_text_group_from_display_names(
    text_groups: dict[str, list[dict[str, Any]]],
    tracks: list[dict[str, Any]],
) -> str:
    """Select one TextTable group only when every track uniquely agrees.

    This is a fail-closed fallback for exports where authored subtitle tracks
    retain clip timing/display names but their SubtitlePlayableAsset `_textId`
    objects are unavailable. It never merges partially matching groups.
    """
    normalized_groups: dict[str, tuple[str, ...]] = {}
    for group, lines in text_groups.items():
        values = tuple(
            normalize_subtitle_display_text(line.get("text"))
            for line in lines
            if isinstance(line, dict)
        )
        if values and all(values):
            normalized_groups[str(group)] = values

    agreed_groups: set[str] | None = None
    usable_tracks = 0
    for track in tracks:
        refs = [
            ref for ref in (track.get("lines") or [])
            if isinstance(ref, dict)
        ]
        displays = tuple(
            normalize_subtitle_display_text(ref.get("displayName"))
            for ref in refs
        )
        if not displays or not all(displays):
            return ""
        usable_tracks += 1
        matches = {
            group for group, values in normalized_groups.items()
            if values == displays
        }
        if len(matches) != 1:
            return ""
        agreed_groups = matches if agreed_groups is None else agreed_groups & matches
        if len(agreed_groups) != 1:
            return ""

    if usable_tracks and agreed_groups and len(agreed_groups) == 1:
        return next(iter(agreed_groups))
    return ""
