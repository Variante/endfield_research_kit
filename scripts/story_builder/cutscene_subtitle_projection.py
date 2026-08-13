from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable


def subtitle_locale_tokens(code: str) -> tuple[str, ...]:
    return {
        "CN": ("CHI", "CN"),
        "EN": ("ENG", "EN"),
        "JP": ("JP",),
        "KR": ("KR", "KO"),
        "TC": ("CHT", "TC"),
        "MX": ("MX", "ES"),
        "BR": ("BR", "PT"),
    }.get(str(code or "").upper(), (str(code or "").upper(),))


def subtitle_track_language_score(track: dict, *, language_code: str) -> int:
    name = str(track.get("parentName") or "").upper()
    desired = subtitle_locale_tokens(language_code)

    def first_desired_index(tokens: list[str]) -> int | None:
        matches = [desired.index(token) for token in tokens if token in desired]
        return min(matches) if matches else None

    env_tokens = re.findall(r"_ENV_([A-Z]+)", name)
    audio_tokens = re.findall(r"_AU_([A-Z]+)", name)
    if env_tokens:
        env_index = first_desired_index(env_tokens)
        if env_index is None:
            return 100
        audio_index = first_desired_index(audio_tokens)
        return env_index if audio_index is not None else 10 + env_index
    if audio_tokens:
        audio_index = first_desired_index(audio_tokens)
        return 20 + audio_index if audio_index is not None else 80
    return 50


def subtitle_tracks_for_language(
    cutscene_key: str,
    tracks: list[dict],
    *,
    language_code: str,
    parent_overrides: dict[str, dict[str, set[str]]],
) -> list[dict]:
    parent_override = (
        parent_overrides.get(str(language_code or "").upper(), {}).get(cutscene_key)
    )
    if parent_override:
        selected = [
            track
            for track in tracks
            if str(track.get("parentName") or "") in parent_override
        ]
        if selected:
            return selected
    scored = [
        (subtitle_track_language_score(track, language_code=language_code), track)
        for track in tracks
        if isinstance(track, dict)
    ]
    if not scored:
        return []
    best_score = min(score for score, _track in scored)
    return [track for score, track in scored if score == best_score]


def build_cutscene_texttable_line(
    row_key: str,
    text_entry: object,
    match: re.Match[str],
    cutscene_key: str,
    raw_group: str,
    *,
    translate: Callable[[object], str],
    source_ref: Callable[..., dict],
    pick_fields: Callable[..., dict],
    text_trace: Callable[..., dict],
) -> dict:
    line_num = int(match.group("line"))
    sub = match.group("sub") or ""
    gender = (match.group("gender") or "").strip("_").upper()
    cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
    text = translate(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
    line = {
        "id": row_key,
        "cid": cid,
        "text": text,
        "_debug": {
            **source_ref(
                "TextTable",
                row_key,
                (
                    pick_fields(text_entry, "id", "text")
                    if isinstance(text_entry, dict)
                    else {"value": text_entry}
                ),
                cutsceneKey=cutscene_key,
                textGroup=raw_group,
                line=line_num,
            ),
            "fields": {
                "text": text_trace("TextTable", row_key, "id", text_entry),
            },
        },
    }
    if raw_group != cutscene_key:
        line["textGroup"] = raw_group
    if sub:
        line["sub"] = sub
        line["_debug"]["source"]["sub"] = sub
    if gender:
        line["gender"] = gender
        line["_debug"]["source"]["gender"] = gender
    return line


def subtitle_start_key(value: object) -> float:
    return round(float(value), 6) if isinstance(value, (int, float)) else 0.0


def subtitle_slot_key(ref: dict, timing_index: int) -> tuple[float, float, int]:
    duration = ref.get("duration")
    return (
        subtitle_start_key(ref.get("start")),
        round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
        timing_index,
    )


def subtitle_clip_debug(track: dict, ref: dict) -> dict:
    debug = {
        "source": "animeSubtitleTrack",
        "file": track.get("file"),
        "parent": track.get("parentName"),
        "parentFile": track.get("parentFile"),
        "textId": ref.get("textId"),
        "start": ref.get("start"),
        "duration": ref.get("duration"),
        "clipIndex": ref.get("clipIndex"),
        "assetPathId": ref.get("assetPathId"),
    }
    if ref.get("displayName"):
        debug["displayName"] = ref.get("displayName")
    if track.get("gender"):
        debug["assetGender"] = track["gender"]
    if track.get("pathId") not in (None, ""):
        debug["trackPathId"] = track["pathId"]
    if track.get("parentPathId") not in (None, ""):
        debug["parentPathId"] = track["parentPathId"]
    return debug


def line_matches_cutscene_key(line: dict, cutscene_key: str) -> bool:
    row_id = str(line.get("id") or "")
    if row_id.startswith(f"{cutscene_key}_"):
        return True
    if str(line.get("textGroup") or "") == cutscene_key:
        return True
    debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
    if str(debug.get("cutsceneKey") or "") == cutscene_key:
        return True
    source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
    return str(source.get("textGroup") or "") == cutscene_key


def subtitle_gender_rank(gender: str) -> int:
    return {"": 0, "F": 1, "M": 2}.get(str(gender or "").upper(), 3)


def line_has_explicit_gender_switch(line: dict) -> bool:
    text = str(line.get("text") or "")
    return "{F}" in text or "{M}" in text


def normalize_subtitle_variant_text(text: object) -> str:
    source = str(text or "")
    source = re.sub(r"\{[FM]\}", "", source)
    return "".join(
        ch.casefold()
        for ch in source
        if not ch.isspace() and not unicodedata.category(ch).startswith("P")
    )


def subtitle_candidate_rank(
    cutscene_key: str,
    candidate: dict,
) -> tuple[int, int, int, int, str]:
    line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
    return (
        0 if line_has_explicit_gender_switch(line) else 1,
        0 if line_matches_cutscene_key(line, cutscene_key) else 1,
        subtitle_gender_rank(candidate.get("gender") or ""),
        int(candidate.get("clipIndex") or 0),
        str(candidate.get("rowKey") or ""),
    )


def subtitle_alternate_line_debug(candidate: dict) -> dict:
    line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
    out = {
        "id": line.get("id"),
        "cid": line.get("cid"),
        "text": line.get("text"),
        "track": candidate.get("trackDebug"),
    }
    if line.get("textGroup"):
        out["textGroup"] = line.get("textGroup")
    if candidate.get("gender"):
        out["assetGender"] = candidate.get("gender")
    return out


def build_fallback_track_line(
    cutscene_key: str,
    row_key: str,
    ref: dict,
    *,
    text_table: dict,
    cutscene_text_row_re: re.Pattern[str],
    translate: Callable[[object], str],
    source_ref: Callable[..., dict],
    text_trace: Callable[..., dict],
) -> dict:
    match = cutscene_text_row_re.match(row_key)
    text_entry = text_table.get(row_key)
    text = (
        translate(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
        if text_entry
        else ""
    )
    source = source_ref(
        "AnimeStudioSubtitleTrack",
        row_key,
        {"textId": row_key},
        cutsceneKey=cutscene_key,
    )
    if match:
        raw_group = match.group("group")
        line_num = int(match.group("line"))
        sub = match.group("sub") or ""
        gender = (match.group("gender") or "").strip("_").upper()
        source["source"]["textGroup"] = raw_group
        source["source"]["line"] = line_num
        if sub:
            source["source"]["sub"] = sub
        if gender:
            source["source"]["gender"] = gender
        cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
    else:
        cid = str(ref.get("clipIndex") or "")
    return {
        "id": row_key,
        "cid": cid,
        "text": text,
        "_debug": {
            **source,
            "fields": {
                "text": (
                    text_trace("TextTable", row_key, "id", text_entry)
                    if text_entry
                    else {
                        "table": "TextTable",
                        "rowId": row_key,
                        "field": "id",
                        "raw": None,
                        "lookup": [],
                        "text": "",
                    }
                ),
            },
        },
    }


__all__ = [
    "build_cutscene_texttable_line",
    "build_fallback_track_line",
    "line_has_explicit_gender_switch",
    "line_matches_cutscene_key",
    "normalize_subtitle_variant_text",
    "subtitle_alternate_line_debug",
    "subtitle_candidate_rank",
    "subtitle_clip_debug",
    "subtitle_gender_rank",
    "subtitle_locale_tokens",
    "subtitle_slot_key",
    "subtitle_start_key",
    "subtitle_track_language_score",
    "subtitle_tracks_for_language",
]
