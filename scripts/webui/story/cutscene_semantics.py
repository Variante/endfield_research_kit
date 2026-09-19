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


def validated_lua_cutscene_playback_keys(report: Any) -> tuple[list[str], list[dict[str, Any]]]:
    """Return authored Lua cutscene ids only from the complete census.

    Recovery association is case-insensitive, so a reviewed case-mismatch row
    is still positive playback evidence.  The caller's definition-identity
    gate remains responsible for rejecting folded-name collisions.
    """
    if not isinstance(report, dict) or report.get("schemaVersion") != "luaConsumerReferenceAudit.v5":
        return [], [{
            "gate": "validated_lua_consumer_reference_audit_schema",
            "expected": "luaConsumerReferenceAudit.v5",
            "actual": report.get("schemaVersion") if isinstance(report, dict) else type(report).__name__,
        }]
    read_errors = report.get("readErrors")
    if read_errors not in (None, []):
        return [], [{
            "gate": "complete_lua_consumer_reference_census",
            "expected": [],
            "actual": read_errors,
        }]
    game_action = report.get("gameActionAudit")
    rows = game_action.get("authoredStoryPlaybackCalls") if isinstance(game_action, dict) else None
    if not isinstance(rows, list):
        return [], [{
            "gate": "authored_lua_story_playback_calls_present",
            "expected": "list",
            "actual": type(rows).__name__,
        }]
    keys = sorted({
        str(row.get("canonicalStoryKey") or row.get("resolvedLiteral") or "").strip()
        for row in rows
        if isinstance(row, dict)
        and row.get("playbackKind") == "cutscene"
        and str(row.get("canonicalStoryKey") or row.get("resolvedLiteral") or "").strip()
    })
    return keys, []


def classify_cutscene_playback_use(
    cutscene_key: str,
    *,
    definition_keys: list[str],
    playback_story_keys: list[str],
    scan_status: str,
    validation_failures: list[dict] | None = None,
) -> dict[str, Any]:
    """Classify unused only from a complete uniquely-folded carrier census."""
    folded = str(cutscene_key or "").casefold()
    definition_matches = sorted({
        key for key in definition_keys if str(key).casefold() == folded
    })
    if len(definition_matches) != 1:
        return {
            "status": "unresolved_definition_identity",
            "automaticUnused": False,
            "caseInsensitiveDefinitionMatches": definition_matches,
            "failureGate": "unique_case_insensitive_definition_identity",
        }
    if scan_status != "validated_complete" or validation_failures:
        return {
            "status": "unresolved_playback_scan",
            "automaticUnused": False,
            "failureGate": "complete_non_degraded_playback_carrier_scan",
            "scanStatus": scan_status,
            "validationFailureCount": len(validation_failures or []),
        }
    playback_matches = sorted({
        key for key in playback_story_keys if str(key).casefold() == folded
    })
    if playback_matches:
        return {
            "status": "playback_observed",
            "automaticUnused": False,
            "caseInsensitivePlaybackMatches": playback_matches,
        }
    return {
        "status": "conclusive_no_playback_observed",
        "automaticUnused": True,
        "caseInsensitivePlaybackMatches": [],
        "boundary": (
            "A complete non-degraded playback-carrier census found no exact or uniquely "
            "case-insensitive reference to this authored cutscene definition."
        ),
    }


def apply_cutscene_playback_use_postpass(
    payloads_by_key: dict[str, dict[str, Any]],
    index_entries: list[dict[str, Any]],
    *,
    playback_story_keys: list[str],
    scan_status: str,
    validation_failures: list[dict] | None = None,
) -> dict[str, int]:
    """Publish playback-use diagnostics after every carrier index is complete."""
    definition_keys = sorted(payloads_by_key)
    index_by_key = {
        str(entry.get("k") or ""): entry
        for entry in index_entries
        if isinstance(entry, dict)
    }
    counts = {"definitions": 0, "playbackObserved": 0, "automaticUnused": 0,
              "unresolved": 0}
    for key in definition_keys:
        payload = payloads_by_key[key]
        if payload.get("kind") != "cutscene" or not isinstance(payload.get("cutscene"), dict):
            continue
        result = classify_cutscene_playback_use(
            key,
            definition_keys=definition_keys,
            playback_story_keys=playback_story_keys,
            scan_status=scan_status,
            validation_failures=validation_failures,
        )
        payload["cutscene"]["playbackUse"] = result
        payload["automaticUnused"] = bool(result.get("automaticUnused"))
        entry = index_by_key.get(key)
        if entry is not None:
            entry["playbackUse"] = {
                "status": result.get("status"),
                "automaticUnused": bool(result.get("automaticUnused")),
            }
            entry["automaticUnused"] = bool(result.get("automaticUnused"))
        counts["definitions"] += 1
        if result.get("status") == "playback_observed":
            counts["playbackObserved"] += 1
        elif result.get("automaticUnused"):
            counts["automaticUnused"] += 1
        else:
            counts["unresolved"] += 1
    return counts


def exact_levelscript_fmv_bindings(
    cutscene: dict[str, Any],
) -> list[dict[str, Any]]:
    """Return authored FMV bindings only when their source is exact."""
    bindings = [
        row for row in (cutscene.get("levelscriptFmvBindings") or [])
        if isinstance(row, dict)
    ]
    for index, binding in enumerate(bindings):
        sources = [
            row for row in (binding.get("sources") or [])
            if isinstance(row, dict)
        ]
        exact_sources = [
            row for row in sources
            if row.get("kind") == "levelscriptFmvAction"
            and row.get("sourceFile")
            and row.get("actionName")
            and row.get("nativeMappingId")
        ]
        if not binding.get("fmvId") or not exact_sources:
            raise ValueError(
                f"FMV binding {index} lacks an exact "
                "levelscriptFmvAction source"
            )
    return bindings


def cutscene_semantic_shape(cutscene: dict[str, Any]) -> str:
    """Classify one generated cutscene without implying runtime execution."""
    variants = [
        row for row in (cutscene.get("variants") or [])
        if isinstance(row, dict)
    ]
    has_components = bool(variants)
    has_root = any(row.get("part") == "root" for row in variants)
    has_levelscript_fmv = bool(exact_levelscript_fmv_bindings(cutscene))
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


def _line_id_list_equal(left: object, right: object) -> bool:
    if not isinstance(left, list) or not isinstance(right, list):
        return False
    return [str(value or "") for value in left] == [str(value or "") for value in right]

def normalize_cutscene_text_group(group: str) -> str:
    match = re.match(r"^(.*_)(0+)(\d+)$", group)
    if not match:
        return group
    return f"{match.group(1)}{int(match.group(3))}"

def merge_duplicate_cutscene_rows(rows: list[tuple[tuple[int, int, int, str, str], dict]]) -> list[dict]:
    merged: list[dict] = []
    seen: dict[tuple[str, str, str], dict] = {}
    for _sort_key, line in sorted(rows, key=lambda item: item[0]):
        dedupe_key = (
            str(line.get("cid") or ""),
            str(line.get("gender") or ""),
            str(line.get("text") or ""),
        )
        existing = seen.get(dedupe_key)
        if existing is None:
            seen[dedupe_key] = line
            merged.append(line)
            continue

        duplicate = {"id": line.get("id") or ""}
        if line.get("textGroup"):
            duplicate["textGroup"] = line["textGroup"]
        if line.get("sub"):
            duplicate["sub"] = line["sub"]
        if line.get("gender"):
            duplicate["gender"] = line["gender"]
        existing.setdefault("mergedDuplicateRows", []).append(duplicate)
        existing_debug = existing.setdefault("_debug", {})
        existing_debug.setdefault("mergedDuplicateRows", []).append(duplicate)
        existing_source = existing_debug.setdefault("source", {})
        merged_row_ids = existing_source.setdefault("mergedDuplicateRowIds", [])
        if duplicate["id"] and duplicate["id"] not in merged_row_ids:
            merged_row_ids.append(duplicate["id"])
        if duplicate.get("textGroup"):
            merged_groups = existing_source.setdefault("mergedDuplicateTextGroups", [])
            if duplicate["textGroup"] not in merged_groups:
                merged_groups.append(duplicate["textGroup"])
    return merged

def cutscene_line_text_groups(cutscene_key: str, lines: list[dict]) -> list[str]:
    groups: list[str] = []
    for line in lines:
        for group in [
            str(line.get("textGroup") or cutscene_key),
            *[
                str(duplicate.get("textGroup") or "")
                for duplicate in (line.get("mergedDuplicateRows") or [])
                if isinstance(duplicate, dict)
            ],
        ]:
            if group and group not in groups:
                groups.append(group)
    return groups

def cutscene_pair_normalize(text: str) -> str:
    """Strip whitespace, punctuation, and symbols so that F and M variants
    differing only in cosmetic markers (leading space, halfwidth/fullwidth
    punctuation, smart quotes) compare equal. Letters and digits survive."""
    if not text:
        return ""
    out = []
    for ch in str(text):
        cat = unicodedata.category(ch)
        if cat and cat[0] in ("L", "N"):
            out.append(ch)
    return "".join(out)
