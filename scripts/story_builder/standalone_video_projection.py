from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable


def strip_video_gender_prefix(stem: str) -> tuple[str, str]:
    match = re.match(r"^(?P<gender>f|m|fm)_(?P<rest>cs_video_.+)$", stem or "", flags=re.IGNORECASE)
    if not match:
        return "", stem or ""
    return match.group("gender").lower(), match.group("rest")


def video_scene_hint(refs: list[dict]) -> str:
    for ref in refs:
        override = ref.get("_videoAttachmentAttachOverride")
        if not isinstance(override, dict):
            continue
        target = str(override.get("targetKey") or ref.get("_resolvedKey") or "").strip()
        if target:
            return strip_video_scene_prefix(target)
    for ref in refs:
        binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
        scene = str(binding.get("scene") or "").strip()
        if scene and not binding.get("isHint"):
            return strip_video_scene_prefix(scene)
    for ref in refs:
        _gender, base = strip_video_gender_prefix(str(ref.get("baseStem") or ref.get("stem") or ""))
        for prefix in ("cs_video_dlg_", "cs_video_cutscene_", "cs_video_remotecomm_", "cs_video_"):
            if base.startswith(prefix):
                return strip_video_scene_prefix(base[len(prefix):])
        if base:
            return strip_video_scene_prefix(base)
    return ""


def strip_video_scene_prefix(scene: str) -> str:
    value = str(scene or "")
    for prefix in ("dlg_", "cutscene_", "remotecomm_", "radio_", "black_"):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def video_mission_scene(refs: list[dict]) -> tuple[str, int]:
    scene_hint = video_scene_hint(refs)
    match = re.match(
        r"^(?P<mission>[a-z]+\d+m\d+(?:d\d+)?)(?:_(?P<scene>\d+).*)?$",
        scene_hint,
        flags=re.IGNORECASE,
    )
    if not match:
        return (scene_hint.split("_", 1)[0].lower() if scene_hint else "video", 0)
    return match.group("mission").lower(), int(match.group("scene") or 0)


def video_title(
    refs: list[dict],
    *,
    unique_preserve: Callable[[Iterable[str]], list[str]],
) -> str:
    base_names = unique_preserve(
        str(ref.get("baseStem") or ref.get("stem") or "")
        for ref in refs
        if ref.get("baseStem") or ref.get("stem")
    )
    if base_names:
        return base_names[0]
    names = unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
    return names[0] if names else "Narrative video"


def video_text_candidate_rows(
    video_stem: str,
    *,
    text_table: dict,
    translate: Callable[[object], str],
    source_ref: Callable[..., dict],
    pick_fields: Callable[..., dict],
    text_trace: Callable[..., dict],
) -> list[dict]:
    prefix = f"{video_stem}_"
    rows: list[tuple[tuple[int, int, str], dict]] = []
    for row_id, text_entry in text_table.items():
        row_key = str(row_id or "")
        if not row_key.startswith(prefix):
            continue
        suffix = row_key[len(prefix):]
        match = re.fullmatch(r"(?P<line>\d+)(?P<sub>d\d+)?(?:_[fm])?", suffix, flags=re.IGNORECASE)
        if not match:
            continue
        sub = match.group("sub") or ""
        sub_order = int(sub[1:]) if sub else -1
        text = translate(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
        line = {
            "id": row_key,
            "cid": f"{match.group('line')}{sub}",
            "text": text,
            "_debug": {
                **source_ref(
                    "TextTable",
                    row_key,
                    pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                    videoStem=video_stem,
                    evidence="name-matched-video-text-candidate",
                ),
                "fields": {
                    "text": text_trace("TextTable", row_key, "id", text_entry),
                },
            },
        }
        if sub:
            line["sub"] = sub
        rows.append(((int(match.group("line")), sub_order, row_key), line))
    return [line for _sort_key, line in sorted(rows, key=lambda item: item[0])]


def standalone_binding_summary(refs: list[dict]) -> tuple[str, str]:
    for ref in refs:
        override = ref.get("_videoAttachmentOverride")
        if not isinstance(override, dict):
            continue
        target = str(override.get("targetKey") or ref.get("_suppressedResolvedKey") or "")
        target_note = f" to `{target}`" if target else ""
        return (
            f"Attachment status: manual override suppresses inline attachment{target_note}; kept standalone in WebUI",
            "standaloneVideoManualOverrideSuppressedInline",
        )
    for ref in refs:
        override = ref.get("_videoAttachmentAttachOverride")
        if not isinstance(override, dict):
            continue
        target = str(override.get("targetKey") or ref.get("_resolvedKey") or "")
        if not target:
            continue
        resolved_kind = str(ref.get("_resolvedKind") or "")
        label = {
            "cutscene": "cutscene",
            "dlg": "dialog",
            "remotecomm": "remotecomm",
        }.get(resolved_kind, "story file")
        return (
            f"Attachment status: manual override attaches inline to {label} `{target}`; kept standalone in WebUI",
            "standaloneVideoManualOverrideAttachedInline",
        )
    for ref in refs:
        binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
        if not binding or binding.get("isHint"):
            continue
        scene = str(binding.get("scene") or "")
        if not scene:
            continue
        resolved_kind = str(ref.get("_resolvedKind") or "")
        resolved_key = str(ref.get("_resolvedKey") or "")
        if resolved_kind == "cutscene":
            label, target = "cutscene", resolved_key or scene
        elif resolved_kind == "dlg":
            label, target = "dialog", resolved_key or scene
        elif resolved_kind == "remotecomm":
            label, target = "remotecomm", resolved_key or scene
        elif scene.startswith("cutscene_"):
            label, target = "cutscene", scene
        elif scene.startswith("dlg_"):
            label, target = "dialog", scene
        elif scene.startswith("remotecomm_"):
            label, target = "remotecomm", scene
        else:
            label, target = "scene", scene
        attached_note = " (also embedded inline)" if resolved_kind else ""
        source_kinds = set(binding.get("sourceKinds") or [])
        if "timelinePlayable" in source_kinds:
            binding_label = "timeline-bound"
        elif "levelscriptFmvAction" in source_kinds:
            binding_label = "LevelScript FMV-action-bound"
        else:
            binding_label = "authoritatively bound"
        return (
            f"Attachment status: {binding_label} to {label} `{target}`{attached_note}; kept standalone in WebUI",
            "standaloneVideoBoundButKeptSeparate",
        )
    resolved_key = next(
        (
            str(ref.get("_resolvedKey") or "")
            for ref in refs
            if ref.get("_resolvedKey")
        ),
        "",
    )
    resolved_kind = next(
        (
            str(ref.get("_resolvedKind") or "")
            for ref in refs
            if ref.get("_resolvedKind")
        ),
        "",
    )
    if resolved_key:
        label = {
            "cutscene": "cutscene",
            "dlg": "dialog",
            "remotecomm": "remotecomm",
        }.get(resolved_kind, "story file")
        return (
            f"Attachment status: filename-mapped to {label} `{resolved_key}` (also embedded inline); kept standalone in WebUI",
            "standaloneVideoFilenameMapped",
        )
    return (
        "Attachment status: no non-name binding found for a dialog or cutscene",
        "standaloneVideoNoAuthoritativeStoryBinding",
    )


def emit_standalone_video_outputs(
    standalone_videos: dict[str, list[dict]],
    *,
    narrative_video_name_sort_key: Callable[[dict], tuple],
    compact_narrative_video_ref: Callable[[dict], dict],
    parse_mission: Callable[[str], tuple[str, int]],
    unique_preserve: Callable[[Iterable[str]], list[str]],
    mission_name_trace: Callable[[str], dict],
    write_conv_payload: Callable[[str, dict], None],
    narrative_video_index_summary: Callable[[list[dict]], dict],
    preview: Callable[[str], str],
    merge_search_text: Callable[..., str],
    mission_context_text: Callable[[str], str],
    text_table: dict,
    translate: Callable[[object], str],
    source_ref: Callable[..., dict],
    pick_fields: Callable[..., dict],
    text_trace: Callable[..., dict],
) -> list[dict]:
    entries: list[dict] = []
    for key, raw_refs in sorted(standalone_videos.items()):
        refs = sorted(raw_refs, key=narrative_video_name_sort_key)
        if not refs:
            continue
        compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
        omitted = max(0, len(refs) - len(compact_refs))
        mission, scene = video_mission_scene(refs)
        type_, act = parse_mission(mission)
        title = video_title(refs, unique_preserve=unique_preserve)
        names = unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
        source_counts = Counter(str(ref.get("source") or "") for ref in refs)
        format_counts = Counter(str(ref.get("format") or "") for ref in refs)
        attachment_text, attachment_reason = standalone_binding_summary(refs)
        attached_story_key = next(
            (
                str(ref.get("_resolvedKey") or "")
                for ref in refs
                if ref.get("_resolvedKey")
            ),
            "",
        )
        text_candidates = video_text_candidate_rows(
        title,
        text_table=text_table,
        translate=translate,
        source_ref=source_ref,
        pick_fields=pick_fields,
        text_trace=text_trace,
    )
        # `title` is the asset baseStem (e.g. cs_video_e0m0_3); the game
        # ships no localized title for FMVs. Keep it as a search hint
        # and as the lead summary label, but don't expose it as a
        # `title` field тА?that would mislead the WebUI into treating
        # the stem as a human-readable name. cutscene/dlg/radio bundles
        # also omit the field.
        #
        # We do NOT promote `cs_video_<scene>_NN` TextTable rows to
        # playable lines. They share a name with the FMV, but no
        # decoded subtitle track carries those keys. Keep them as
        # explicit candidates so the evidence level stays visible.
        summary_rows = [
            {"text": f"Standalone narrative video: {title}"},
            {"text": f"Mission: {mission}"},
            {"text": f"Files: {len(refs)} exported variant(s)"},
            {"text": attachment_text},
        ]
        definition = next(
            (
                ref.get("definition")
                for ref in refs
                if isinstance(ref.get("definition"), dict)
            ),
            None,
        )
        if isinstance(definition, dict):
            numeric_ids = [
                str(value)
                for value in (
                    definition.get("numericIds") or []
                )
            ]
            numeric_note = (
                f"; fmv_id={','.join(numeric_ids)}"
                if numeric_ids
                else ""
            )
            summary_rows.append({
                "text": (
                    "Definition status: exported FMV config exists"
                    f"{numeric_note}; definition is not playback or "
                    "mission-placement evidence."
                ),
            })
            timeline_evidence = (
                definition.get("timelineEvidence")
                if isinstance(
                    definition.get("timelineEvidence"), dict
                )
                else {}
            )
            if timeline_evidence:
                summary_rows.append({
                    "text": (
                        "Definition timeline: "
                        f"{timeline_evidence.get('trackCount', 0)} "
                        "track(s), "
                        f"{timeline_evidence.get('clipCount', 0)} "
                        "clip(s), "
                        f"{timeline_evidence.get('subtitleClipCount', 0)} "
                        "subtitle clip(s), "
                        f"{len(timeline_evidence.get('audioEventKeys') or [])} "
                        "audio event(s)."
                    ),
                })
        if text_candidates:
            candidate_preview = " / ".join(
                str(row.get("text") or "")
                for row in text_candidates[:4]
                if row.get("text")
            )
            summary_rows.append({
                "text": (
                    "Name-matched TextTable candidates: "
                    + (candidate_preview or f"{len(text_candidates)} row(s)")
                ),
            })
            summary_rows.append({
                "text": "Video text note: these rows share the FMV stem but are not tied by a decoded subtitle track.",
            })
        payload = {
            "key": key,
            "kind": "video",
            "mission": mission,
            "scene": scene,
            "lines": [],
            "summary": summary_rows,
            "narrativeVideos": compact_refs,
            "_debug": {
                "title": mission_name_trace(mission),
                "narrativeVideos": {
                    "source": {
                        "key": key,
                        "count": len(refs),
                        "shown": len(compact_refs),
                        "omitted": omitted,
                        "reason": attachment_reason,
                    },
                },
            },
        }
        if text_candidates:
            payload["videoTextCandidates"] = text_candidates[:16]
        if omitted:
            payload["narrativeVideosOmitted"] = omitted
        write_conv_payload(key, payload)
        entry = {
            "k": key,
            "d": "video",
            "m": mission,
            "s": scene,
            "t": type_ if type_ != "?" else "other",
            "a": act,
            "c": [],
            "n": 0,
            "p": preview(", ".join(names) or title),
            "tags": ["narrativeVideo"],
            "vid": narrative_video_index_summary(refs),
            "x": merge_search_text(
                " ".join([
                    key,
                    title,
                    mission,
                    " ".join(names),
                    " ".join(str(ref.get("rel") or "") for ref in refs),
                    " ".join(str(ref.get("stem") or "") for ref in refs),
                ]),
                mission_context_text(mission),
            ),
        }
        if attached_story_key:
            entry["attachTo"] = attached_story_key
        entry["videoSources"] = {
            source: source_counts[source]
            for source in sorted(source_counts)
            if source
        }
        entry["videoFormats"] = {
            fmt: format_counts[fmt]
            for fmt in sorted(format_counts)
            if fmt
        }
        if not entry["x"]:
            entry.pop("x", None)
        entries.append(entry)
    return entries
