from __future__ import annotations

import copy
import re
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class CutsceneTextInputs:
    text_table: dict
    language_code: str
    subtitle_parent_overrides: dict
    cutscene_text_row_re: re.Pattern[str]


@dataclass(frozen=True)
class CutsceneTextCallbacks:
    split_parent_key: Callable[[str], str]
    split_child_sort_key: Callable[[str], object]
    resolve_text_group: Callable[[str, set[str], set[str]], str]
    translate: Callable[..., str]
    remember_texttable_row_usage: Callable[[object], None]
    source_ref: Callable[..., dict]
    pick_fields: Callable[..., dict]
    text_trace: Callable[..., dict]
    build_texttable_line: Callable[..., dict]
    select_display_text_group: Callable[[dict, list[dict]], str]
    select_tracks_for_language: Callable[..., list[dict]]
    subtitle_start_key: Callable[[object], float]
    subtitle_slot_key: Callable[[dict, int], tuple[float, float, int]]
    subtitle_clip_debug: Callable[[dict, dict], dict]
    build_fallback_track_line: Callable[..., dict]
    subtitle_candidate_rank: Callable[[str, dict], tuple]
    line_has_explicit_gender_switch: Callable[[dict], bool]
    subtitle_alternate_line_debug: Callable[[dict], dict]
    normalize_subtitle_variant_text: Callable[[object], str]
    merge_duplicate_rows: Callable[[list], list[dict]]
    pair_normalize: Callable[[str], str]

def project_cutscene_text_lines(
    asset_keys: set[str],
    subtitle_tracks_by_key: dict[str, list[dict]],
    *,
    inputs: CutsceneTextInputs,
    callbacks: CutsceneTextCallbacks,
) -> dict[str, list[dict]]:
    split_asset_children_by_parent: dict[str, list[str]] = defaultdict(list)
    for asset_key in asset_keys:
        parent_key = callbacks.split_parent_key(asset_key)
        if parent_key and parent_key not in asset_keys:
            split_asset_children_by_parent[parent_key].append(asset_key)
    for children in split_asset_children_by_parent.values():
        children.sort(key=callbacks.split_child_sort_key)
    raw_groups: set[str] = set()
    matched_rows: list[tuple[str, dict, re.Match[str]]] = []
    for row_id, text_entry in inputs.text_table.items():
        row_key = str(row_id or "")
        if not row_key.startswith("cutscene_"):
            continue
        match = inputs.cutscene_text_row_re.match(row_key)
        if not match:
            continue
        raw_groups.add(match.group("group"))
        matched_rows.append((row_key, text_entry, match))
    grouped: dict[str, list[tuple[tuple[int, int, int, str, str], dict]]] = defaultdict(list)
    lines_by_row_id: dict[str, dict] = {}
    def remember_cutscene_line_usage(line: dict) -> None:
        callbacks.remember_texttable_row_usage(line.get("id"))
        for duplicate in line.get("mergedDuplicateRows") or []:
            if isinstance(duplicate, dict):
                callbacks.remember_texttable_row_usage(duplicate.get("id"))
    for row_key, text_entry, match in matched_rows:
        raw_group = match.group("group")
        cutscene_key = callbacks.resolve_text_group(raw_group, asset_keys, raw_groups)
        line_num = int(match.group("line"))
        sub = match.group("sub") or ""
        gender = (match.group("gender") or "").strip("_").upper()
        line = callbacks.build_texttable_line(
            row_key,
            text_entry,
            match,
            cutscene_key,
            raw_group,
            translate=callbacks.translate,
            source_ref=callbacks.source_ref,
            pick_fields=callbacks.pick_fields,
            text_trace=callbacks.text_trace,
        )
        lines_by_row_id[row_key] = line
        sub_order = int(sub[1:]) if sub else -1
        alias_order = 1 if raw_group != cutscene_key else 0
        grouped[cutscene_key].append(((line_num, sub_order, alias_order, gender, row_key), line))
    merged_by_key: dict[str, list[dict]] = {}
    for cutscene_key, subtitle_tracks in subtitle_tracks_by_key.items():
        subtitle_tracks = callbacks.select_tracks_for_language(
            cutscene_key,
            subtitle_tracks,
            language_code=inputs.language_code,
            parent_overrides=inputs.subtitle_parent_overrides,
        )
        if subtitle_tracks and not any(
            str(ref.get("textId") or "").strip()
            for track in subtitle_tracks
            for ref in (track.get("lines") or [])
            if isinstance(ref, dict)
        ):
            candidate_groups: dict[str, list[dict]] = defaultdict(list)
            for _sort_key, line in grouped.get(cutscene_key) or []:
                if not isinstance(line, dict):
                    continue
                raw_group = str(line.get("textGroup") or cutscene_key)
                candidate_groups[raw_group].append(line)
            selected_group = callbacks.select_display_text_group(
                candidate_groups,
                subtitle_tracks,
            )
            if selected_group:
                selected_lines = [
                    copy.deepcopy(line)
                    for line in candidate_groups[selected_group]
                ]
                unselected_groups = sorted(
                    group for group in candidate_groups
                    if group != selected_group
                )
                track_rows = [
                    {
                        "file": track.get("file"),
                        "parent": track.get("parentName"),
                        "gender": track.get("gender"),
                        "clipCount": len(track.get("lines") or []),
                    }
                    for track in subtitle_tracks
                ]
                for line in selected_lines:
                    line.setdefault("_debug", {})[
                        "subtitleTrackDisplayFallback"
                    ] = {
                        "source": "animeSubtitleTrackDisplayAlignment",
                        "reason": "SubtitlePlayableAsset text IDs unavailable",
                        "selectedTextGroup": selected_group,
                        "unselectedTextGroups": unselected_groups,
                        "tracks": track_rows,
                    }
                    remember_cutscene_line_usage(line)
                merged_by_key[cutscene_key] = selected_lines
                continue
        slot_candidates: dict[tuple[float, float, int], list[dict]] = defaultdict(list)
        for track in subtitle_tracks:
            timing_counts: dict[tuple[float, float], int] = defaultdict(int)
            for ref in track.get("lines") or []:
                row_key = str(ref.get("textId") or "").strip()
                if not row_key:
                    continue
                start = callbacks.subtitle_start_key(ref.get("start"))
                duration = ref.get("duration")
                timing_key = (
                    start,
                    round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
                )
                timing_index = timing_counts[timing_key]
                timing_counts[timing_key] += 1
                slot_key = callbacks.subtitle_slot_key(ref, timing_index)
                track_debug = callbacks.subtitle_clip_debug(track, ref)
                line = copy.deepcopy(lines_by_row_id.get(row_key))
                if line is None:
                    line = callbacks.build_fallback_track_line(
                        cutscene_key,
                        row_key,
                        ref,
                        text_table=inputs.text_table,
                        cutscene_text_row_re=inputs.cutscene_text_row_re,
                        translate=callbacks.translate,
                        source_ref=callbacks.source_ref,
                        text_trace=callbacks.text_trace,
                    )
                line_debug = line.setdefault("_debug", {})
                line_debug["subtitleTrack"] = track_debug
                line_debug.setdefault("subtitleTracks", []).append(track_debug)
                line_debug.setdefault("source", {})["subtitleTrackFile"] = track.get("file")
                if track.get("gender"):
                    line_debug["source"]["subtitleAssetGender"] = track["gender"]
                remember_cutscene_line_usage(line)
                slot_candidates[slot_key].append({
                    "rowKey": row_key,
                    "slotKey": slot_key,
                    "gender": str(track.get("gender") or "").upper(),
                    "clipIndex": int(ref.get("clipIndex") or 0),
                    "sortKey": (slot_key[0], timing_index, int(ref.get("clipIndex") or 0), row_key),
                    "line": line,
                    "trackDebug": track_debug,
                })
        ordered_lines: list[tuple[tuple[float, int, int, str], dict]] = []
        for slot_key, candidates in slot_candidates.items():
            genders = {candidate["gender"] for candidate in candidates if candidate.get("gender")}
            if len(genders) > 1 and all(candidate.get("gender") for candidate in candidates):
                ranked = sorted(
                    candidates,
                    key=lambda candidate: callbacks.subtitle_candidate_rank(cutscene_key, candidate),
                )
                chosen = ranked[0]
                chosen_line = chosen["line"]
                chosen_debug = chosen_line.setdefault("_debug", {})
                chosen_tracks = chosen_debug.setdefault("subtitleTracks", [])
                alternates: list[dict] = []
                by_gender: dict[str, dict] = {}
                chosen_text = chosen_line.get("text")
                chosen_id = chosen_line.get("id")
                explicit_switch = callbacks.line_has_explicit_gender_switch(chosen_line)
                if chosen.get("gender"):
                    by_gender.setdefault(chosen["gender"], chosen)
                for candidate in ranked[1:]:
                    if candidate.get("gender"):
                        by_gender.setdefault(candidate["gender"], candidate)
                    candidate_track = candidate.get("trackDebug")
                    if candidate_track:
                        chosen_tracks.append(candidate_track)
                    candidate_line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
                    if candidate_line.get("id") != chosen_id or candidate_line.get("text") != chosen_text:
                        alternates.append(callbacks.subtitle_alternate_line_debug(candidate))
                if not explicit_switch and "F" in by_gender and "M" in by_gender:
                    f_line = by_gender["F"].get("line") if isinstance(by_gender["F"].get("line"), dict) else {}
                    m_line = by_gender["M"].get("line") if isinstance(by_gender["M"].get("line"), dict) else {}
                    f_text = str(f_line.get("text") or "")
                    m_text = str(m_line.get("text") or "")
                    if (
                        f_text != m_text
                        and callbacks.normalize_subtitle_variant_text(f_text)
                        != callbacks.normalize_subtitle_variant_text(m_text)
                    ):
                        chosen_line["text"] = f"{{F}}{f_text}{{M}}{m_text}"
                        chosen_debug["subtitleGenderSwitch"] = {
                            "source": "animeSubtitleTrackAlignment",
                            "F": {"id": f_line.get("id"), "text": f_text},
                            "M": {"id": m_line.get("id"), "text": m_text},
                        }
                if alternates:
                    chosen_debug["subtitleAlternateLines"] = alternates
                ordered_lines.append((chosen["sortKey"], chosen_line))
                continue
            by_row_key: dict[str, dict] = {}
            for candidate in sorted(candidates, key=lambda c: (c["sortKey"], c["rowKey"])):
                existing = by_row_key.get(candidate["rowKey"])
                if existing is not None:
                    existing_line = existing["line"]
                    existing_debug = existing_line.setdefault("_debug", {})
                    candidate_track = candidate.get("trackDebug")
                    if candidate_track:
                        existing_debug.setdefault("subtitleTracks", []).append(candidate_track)
                    continue
                by_row_key[candidate["rowKey"]] = candidate
                ordered_lines.append((candidate["sortKey"], candidate["line"]))
        if ordered_lines:
            subtitle_lines = [
                line for _sort_key, line in sorted(ordered_lines, key=lambda item: item[0])
            ]
            text_rows = grouped.get(cutscene_key) or []
            text_rows_have_text = any(
                str(line.get("text") or "").strip()
                for _sort_key, line in text_rows
                if isinstance(line, dict)
            )
            subtitle_lines_have_text = any(
                str(line.get("text") or "").strip()
                for line in subtitle_lines
                if isinstance(line, dict)
            )
            if text_rows_have_text and not subtitle_lines_have_text:
                subtitle_lines = callbacks.merge_duplicate_rows(text_rows)
                track_ids = [
                    str(line.get("id") or "")
                    for line in (
                        candidate.get("line")
                        for candidates in slot_candidates.values()
                        for candidate in candidates
                    )
                    if isinstance(line, dict) and line.get("id")
                ]
                for line in subtitle_lines:
                    line_debug = line.setdefault("_debug", {})
                    line_debug["subtitleTrackTextTableFallback"] = {
                        "source": "animeSubtitleTrack",
                        "reason": "subtitle track textIds did not resolve to localized TextTable text",
                        "trackTextIds": sorted(set(track_ids)),
                    }
                    remember_cutscene_line_usage(line)
            merged_by_key[cutscene_key] = subtitle_lines
    def lines_for_cutscene_key(cutscene_key: str) -> list[dict]:
        if cutscene_key in merged_by_key:
            return merged_by_key[cutscene_key]
        return [
            line
            for _sort_key, line in grouped.get(cutscene_key, [])
            if isinstance(line, dict)
        ]
    def matching_split_child_line(parent_key: str, parent_line: dict) -> dict | None:
        cid = str(parent_line.get("cid") or "")
        normalized_text = callbacks.pair_normalize(str(parent_line.get("text") or ""))
        if not cid or not normalized_text:
            return None
        for child_key in split_asset_children_by_parent.get(parent_key) or []:
            for child_line in lines_for_cutscene_key(child_key):
                if str(child_line.get("cid") or "") != cid:
                    continue
                child_text = callbacks.pair_normalize(str(child_line.get("text") or ""))
                if child_text and child_text == normalized_text:
                    return child_line
        return None
    def attach_text_only_parent_duplicate(parent_key: str, parent_line: dict, child_line: dict) -> None:
        duplicate = {
            "id": parent_line.get("id") or "",
            "textGroup": parent_key,
        }
        if parent_line.get("text"):
            duplicate["text"] = parent_line["text"]
        if parent_line.get("sub"):
            duplicate["sub"] = parent_line["sub"]
        if parent_line.get("gender"):
            duplicate["gender"] = parent_line["gender"]
        child_line.setdefault("mergedDuplicateRows", []).append(duplicate)
        child_debug = child_line.setdefault("_debug", {})
        child_debug.setdefault("mergedDuplicateRows", []).append(duplicate)
        child_source = child_debug.setdefault("source", {})
        row_ids = child_source.setdefault("mergedDuplicateRowIds", [])
        if duplicate["id"] and duplicate["id"] not in row_ids:
            row_ids.append(duplicate["id"])
        groups = child_source.setdefault("mergedDuplicateTextGroups", [])
        if parent_key and parent_key not in groups:
            groups.append(parent_key)
        suppressed = child_source.setdefault("suppressedTextOnlyParentGroups", [])
        if parent_key and parent_key not in suppressed:
            suppressed.append(parent_key)
        remember_cutscene_line_usage(child_line)
    def suppress_text_only_split_parent(cutscene_key: str, rows: list[tuple[tuple[int, int, int, str, str], dict]]) -> bool:
        if cutscene_key in asset_keys:
            return False
        if not split_asset_children_by_parent.get(cutscene_key):
            return False
        matches: list[tuple[dict, dict]] = []
        for _sort_key, line in rows:
            if not isinstance(line, dict):
                return False
            child_line = matching_split_child_line(cutscene_key, line)
            if child_line is None:
                return False
            matches.append((line, child_line))
        for parent_line, child_line in matches:
            attach_text_only_parent_duplicate(cutscene_key, parent_line, child_line)
        return bool(matches)
    for cutscene_key, rows in grouped.items():
        if cutscene_key in merged_by_key:
            continue
        if suppress_text_only_split_parent(cutscene_key, rows):
            continue
        lines = callbacks.merge_duplicate_rows(rows)
        for line in lines:
            remember_cutscene_line_usage(line)
        merged_by_key[cutscene_key] = lines
    return merged_by_key

__all__ = [
    "CutsceneTextCallbacks",
    "CutsceneTextInputs",
    "project_cutscene_text_lines",
]
