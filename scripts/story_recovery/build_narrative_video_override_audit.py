#!/usr/bin/env python3
"""Validate narrative video override rules against generated Story evidence.

This audit checks `webui/overrides/narrative_videos.json` after a Story build:

- override targets exist in `webui/data/lang/<LANG>/index.json`
- attach/suppress stems exist in generated narrative video media evidence
- attach/suppress rules were reflected in generated conv payloads/reports
- `audioFrom` source keys exist and still expose cutscene audio events
- filename-only attachments and unresolved video candidates remain visible for
  follow-up review

The audit is diagnostic. It does not edit overrides or generated Story data.
"""
from __future__ import annotations

import argparse
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

_REPO_ROOT = Path(__file__).resolve().parents[2]
for _path in (_REPO_ROOT / "scripts",):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from common import (  # noqa: E402
    ROOT,
    md_escape,
    read_json,
    rel_path,
    unique_preserve,
    write_report_json,
    write_text_if_changed,
)

DEFAULT_OVERRIDE_PATH = ROOT / "webui" / "overrides" / "narrative_videos.json"
DEFAULT_CONV_ROOT = ROOT / "webui" / "data" / "lang"
DEFAULT_VIDEO_INDEX = ROOT / "webui" / "data" / "assets" / "videos.json"
DEFAULT_VIDEO_BINDINGS = ROOT / "export_full" / "recovered" / "video_bindings.json"
DEFAULT_REPORTS_DIR = ROOT / "reports" / "story" / "recovery" / "narrative_video"
DEFAULT_STORY_REPORTS_DIR = ROOT / "reports" / "story" / "build"

VIDEO_STEM_EXT_RE = re.compile(r"\.[A-Za-z0-9]{1,8}$")
GENDERED_CS_VIDEO_RE = re.compile(r"^(?:f|m|fm)_(cs_video_.+)$", flags=re.IGNORECASE)


@dataclass
class OverrideRule:
    bucket: str
    target_key: str
    stems: list[str]
    audio_from: list[str]
    note: str
    ordinal: int


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def listish_values(value: Any) -> list[Any]:
    if isinstance(value, (str, int, float)):
        return [value]
    if isinstance(value, list):
        return value
    return []


def safe_key(value: Any) -> str:
    return str(value or "").strip()


def normalize_video_stem(value: Any) -> str:
    text = safe_key(value).replace("\\", "/")
    if not text:
        return ""
    text = text.rsplit("/", 1)[-1]
    text = VIDEO_STEM_EXT_RE.sub("", text)
    return text.lower()


def strip_video_gender_prefix(stem: str) -> str:
    match = GENDERED_CS_VIDEO_RE.match(stem)
    return match.group(1).lower() if match else stem


def video_stem_aliases(value: Any) -> set[str]:
    stem = normalize_video_stem(value)
    if not stem:
        return set()
    aliases = {stem}
    aliases.add(strip_video_gender_prefix(stem))
    if stem.startswith("video_"):
        aliases.add(stem[len("video_") :])
    return {alias for alias in aliases if alias}


def standalone_video_key_for_stem(value: Any) -> str:
    stem = strip_video_gender_prefix(normalize_video_stem(value))
    stem = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_").lower()
    return f"video_{stem or 'unknown'}"


def video_ref_aliases(ref: dict[str, Any]) -> set[str]:
    aliases: set[str] = set()
    for field in ("stem", "baseStem", "name", "fmvId", "baseFmvId", "rel"):
        value = ref.get(field)
        if value:
            aliases.update(video_stem_aliases(value))
    return aliases


def normalized_rule_stems(stems: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw_stem in stems:
        stem = normalize_video_stem(raw_stem)
        if stem and stem not in seen:
            seen.add(stem)
            out.append(stem)
    return out


def normalized_story_keys(values: Iterable[Any]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        key = safe_key(value)
        lowered = key.lower()
        if key and lowered not in seen:
            seen.add(lowered)
            out.append(key)
    return out


def extract_stems_from_rule(raw_rule: Any) -> list[str]:
    raw_stems: Any = []
    if isinstance(raw_rule, dict):
        raw_stems = (
            raw_rule.get("stems")
            or raw_rule.get("videoStems")
            or raw_rule.get("stem")
            or raw_rule.get("videoStem")
            or []
        )
    elif isinstance(raw_rule, list):
        raw_stems = raw_rule
    elif raw_rule:
        raw_stems = [raw_rule]
    return normalized_rule_stems(listish_values(raw_stems))


def extract_audio_sources_from_rule(raw_rule: Any) -> list[str]:
    if not isinstance(raw_rule, dict):
        return []
    raw_sources = (
        raw_rule.get("audioFrom")
        or raw_rule.get("audioSourceKeys")
        or raw_rule.get("audioSources")
        or raw_rule.get("audioSourceKey")
        or raw_rule.get("inheritAudioFrom")
        or raw_rule.get("copyAudioFrom")
        or []
    )
    return normalized_story_keys(listish_values(raw_sources))


def parse_override_rules(payload: Any) -> list[OverrideRule]:
    if not isinstance(payload, dict):
        return []

    rules: list[OverrideRule] = []

    def add_rule(bucket: str, target_key: Any, raw_rule: Any) -> None:
        target = safe_key(target_key)
        if not target:
            return
        note = safe_key(raw_rule.get("note")) if isinstance(raw_rule, dict) else ""
        rules.append(
            OverrideRule(
                bucket=bucket,
                target_key=target,
                stems=extract_stems_from_rule(raw_rule),
                audio_from=extract_audio_sources_from_rule(raw_rule),
                note=note,
                ordinal=len(rules) + 1,
            )
        )

    def add_rules(bucket: str, raw_rules: Any) -> None:
        if isinstance(raw_rules, dict):
            for target_key, raw_rule in raw_rules.items():
                add_rule(bucket, target_key, raw_rule)
        elif isinstance(raw_rules, list):
            for raw_rule in raw_rules:
                if not isinstance(raw_rule, dict):
                    continue
                target_key = (
                    raw_rule.get("targetKey")
                    or raw_rule.get("key")
                    or raw_rule.get("resolvedKey")
                    or raw_rule.get("attachTo")
                )
                add_rule(bucket, target_key, raw_rule)

    add_rules("attachInline", payload.get("attachInline") or payload.get("attachTo"))
    add_rules("suppressInline", payload.get("suppressInline"))
    return rules


def load_story_entries(index_path: Path) -> dict[str, dict[str, Any]]:
    payload = read_json(index_path, {})
    entries = payload.get("entries") if isinstance(payload, dict) else []
    if not isinstance(entries, list):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        key = safe_key(entry.get("k"))
        if key:
            out[key] = entry
    return out


def add_catalog_ref(
    catalog: dict[str, list[dict[str, Any]]],
    aliases: Iterable[str],
    ref: dict[str, Any],
) -> None:
    compact_ref = {
        key: value
        for key, value in ref.items()
        if value not in (None, "", [], {})
    }
    for alias in aliases:
        if not alias:
            continue
        rows = catalog.setdefault(alias, [])
        if compact_ref not in rows:
            rows.append(compact_ref)


def ref_from_video_name(name: Any, *, source: str, **extra: Any) -> dict[str, Any]:
    stem = normalize_video_stem(name)
    ref = {
        "name": safe_key(name),
        "stem": stem,
        "baseStem": strip_video_gender_prefix(stem),
        "source": source,
    }
    ref.update(extra)
    return ref


def add_ref_from_name(
    catalog: dict[str, list[dict[str, Any]]],
    name: Any,
    *,
    source: str,
    **extra: Any,
) -> None:
    ref = ref_from_video_name(name, source=source, **extra)
    add_catalog_ref(catalog, video_ref_aliases(ref), ref)


def build_video_catalog(
    narrative_report: dict[str, Any],
    evidence: dict[str, Any],
    video_index: dict[str, Any],
    video_bindings: dict[str, Any],
) -> dict[str, list[dict[str, Any]]]:
    catalog: dict[str, list[dict[str, Any]]] = {}

    for section in ("attached", "standalone"):
        for row in narrative_report.get(section) or []:
            if not isinstance(row, dict):
                continue
            for name in row.get("files") or []:
                add_ref_from_name(
                    catalog,
                    name,
                    source=f"reports/story/build/narrative_videos.{section}",
                    webuiKey=safe_key(row.get("key")),
                    mission=safe_key(row.get("mission")),
                )

    for section in ("manualAttachedInline", "suppressedInline", "unresolved"):
        for row in narrative_report.get(section) or []:
            if not isinstance(row, dict):
                continue
            add_ref_from_name(
                catalog,
                row.get("name"),
                source=f"reports/story/build/narrative_videos.{section}",
                targetKey=safe_key(row.get("targetKey")),
                rel=safe_key(row.get("rel")),
                keyCandidates=list(row.get("keyCandidates") or []),
            )

    for row in evidence.get("rows") or []:
        if not isinstance(row, dict):
            continue
        video = row.get("video") if isinstance(row.get("video"), dict) else {}
        binding = row.get("binding") if isinstance(row.get("binding"), dict) else {}
        ref = {
            "name": safe_key(video.get("name")),
            "rel": safe_key(video.get("rel")),
            "stem": normalize_video_stem(binding.get("fmvId") or video.get("name")),
            "baseStem": strip_video_gender_prefix(normalize_video_stem(binding.get("fmvId") or video.get("name"))),
            "source": "webui narrative_video_evidence",
            "webuiKey": safe_key(row.get("webuiKey")),
            "bindingScene": safe_key(binding.get("scene")),
            "method": safe_key((row.get("evidence") or {}).get("method") if isinstance(row.get("evidence"), dict) else ""),
        }
        add_catalog_ref(catalog, video_ref_aliases(ref), ref)

    for entry in video_index.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        rel = safe_key(entry.get("r"))
        if "/Narrative/" not in rel.replace("\\", "/"):
            continue
        add_ref_from_name(
            catalog,
            rel,
            source="webui video index",
            rel=rel,
            size=entry.get("s"),
        )

    bindings = video_bindings.get("bindings") if isinstance(video_bindings, dict) else {}
    if isinstance(bindings, dict):
        binding_iter = bindings.items()
    elif isinstance(bindings, list):
        binding_iter = ((safe_key(row.get("fmvId")), row) for row in bindings if isinstance(row, dict))
    else:
        binding_iter = ()
    for binding_key, binding in binding_iter:
        if not isinstance(binding, dict):
            continue
        ref = {
            "fmvId": safe_key(binding.get("fmvId") or binding_key),
            "baseFmvId": safe_key(binding.get("baseFmvId")),
            "source": "export_full/recovered/video_bindings",
            "bindingScene": safe_key(binding.get("scene")),
            "mission": safe_key(binding.get("mission")),
        }
        add_catalog_ref(catalog, video_ref_aliases(ref), ref)
        for video_path in binding.get("videos") or []:
            add_ref_from_name(
                catalog,
                video_path,
                source="export_full/recovered/video_bindings",
                rel=safe_key(video_path),
                bindingScene=safe_key(binding.get("scene")),
                mission=safe_key(binding.get("mission")),
            )

    return catalog


def compact_catalog_refs(refs: list[dict[str, Any]], limit: int = 6) -> list[dict[str, Any]]:
    compact: list[dict[str, Any]] = []
    for ref in refs[:limit]:
        compact.append(
            {
                key: ref.get(key)
                for key in ("source", "name", "rel", "webuiKey", "targetKey", "bindingScene", "mission", "method")
                if ref.get(key) not in (None, "", [], {})
            }
        )
    return compact


def catalog_refs_for_stem(catalog: dict[str, list[dict[str, Any]]], stem: str) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    seen: set[tuple[tuple[str, str], ...]] = set()
    for alias in sorted(video_stem_aliases(stem)):
        for ref in catalog.get(alias) or []:
            key = tuple((name, repr(value)) for name, value in sorted(ref.items()))
            if key in seen:
                continue
            seen.add(key)
            refs.append(ref)
    return refs


def extract_ref_key_candidates(refs: Iterable[dict[str, Any]]) -> list[str]:
    candidates: list[str] = []
    for ref in refs:
        for candidate in ref.get("keyCandidates") or []:
            key = safe_key(candidate)
            if key:
                candidates.append(key)
        for field in ("webuiKey", "targetKey", "bindingScene"):
            key = safe_key(ref.get(field))
            if key:
                candidates.append(key)
    return unique_preserve(candidates)


def load_conv_payload(conv_dir: Path, key: str, cache: dict[str, Any]) -> dict[str, Any] | None:
    if key in cache:
        return cache[key]
    path = conv_dir / f"{key}.json"
    payload = read_json(path, None)
    cache[key] = payload if isinstance(payload, dict) else None
    return cache[key]


def conv_exists(conv_dir: Path, key: str, cache: dict[str, Any]) -> bool:
    return load_conv_payload(conv_dir, key, cache) is not None


def conv_video_refs(payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    refs = payload.get("narrativeVideos")
    return [ref for ref in refs if isinstance(ref, dict)] if isinstance(refs, list) else []


def conv_audio_events(payload: dict[str, Any] | None) -> list[str]:
    if not isinstance(payload, dict):
        return []
    cutscene = payload.get("cutscene") if isinstance(payload.get("cutscene"), dict) else {}
    events = list(cutscene.get("audioEvents") or [])
    out: list[str] = []
    seen: set[str] = set()
    for event in events:
        value = safe_key(event)
        lowered = value.lower()
        if value and lowered not in seen:
            seen.add(lowered)
            out.append(value)
    return out


def conv_audio_file_count(payload: dict[str, Any] | None) -> int:
    if not isinstance(payload, dict):
        return 0
    cutscene = payload.get("cutscene") if isinstance(payload.get("cutscene"), dict) else {}
    files = cutscene.get("audioFiles") or []
    return len(files) if isinstance(files, list) else 0


def refs_match_stems(refs: Iterable[dict[str, Any]], stems: Iterable[str]) -> list[dict[str, Any]]:
    wanted: set[str] = set()
    for stem in stems:
        wanted.update(video_stem_aliases(stem))
    return [ref for ref in refs if video_ref_aliases(ref) & wanted]


def debug_source(ref: dict[str, Any]) -> dict[str, Any]:
    debug = ref.get("_debug") if isinstance(ref.get("_debug"), dict) else {}
    source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
    return source


def ref_has_attachment_override(ref: dict[str, Any], target_key: str, stems: Iterable[str]) -> bool:
    source = debug_source(ref)
    override = source.get("attachmentOverride") if isinstance(source.get("attachmentOverride"), dict) else {}
    if not override:
        return False
    if safe_key(override.get("targetKey")) != target_key:
        return False
    override_stems = normalized_rule_stems(override.get("stems") or [])
    return bool(set(override_stems) & set(stems)) if override_stems else True


def standalone_reason_for_stem(conv_dir: Path, stem: str, cache: dict[str, Any]) -> str:
    payload = load_conv_payload(conv_dir, standalone_video_key_for_stem(stem), cache)
    debug = payload.get("_debug") if isinstance(payload, dict) and isinstance(payload.get("_debug"), dict) else {}
    videos = debug.get("narrativeVideos") if isinstance(debug.get("narrativeVideos"), dict) else {}
    source = videos.get("source") if isinstance(videos.get("source"), dict) else {}
    return safe_key(source.get("reason"))


def report_stem_rows(report: dict[str, Any], section: str, target_key: str, stem: str) -> list[dict[str, Any]]:
    wanted = video_stem_aliases(stem)
    out: list[dict[str, Any]] = []
    for row in report.get(section) or []:
        if not isinstance(row, dict):
            continue
        if target_key and safe_key(row.get("targetKey")) != target_key:
            continue
        row_aliases: set[str] = set()
        for row_stem in row.get("stems") or []:
            row_aliases.update(video_stem_aliases(row_stem))
        row_aliases.update(video_stem_aliases(row.get("name")))
        if row_aliases & wanted:
            out.append(row)
    return out


def authoritative_pairs(evidence: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in evidence.get("rows") or []:
        if not isinstance(row, dict):
            continue
        key = safe_key(row.get("webuiKey"))
        if not key:
            continue
        video = row.get("video") if isinstance(row.get("video"), dict) else {}
        binding = row.get("binding") if isinstance(row.get("binding"), dict) else {}
        for value in (video.get("name"), binding.get("fmvId")):
            for alias in video_stem_aliases(value):
                pairs.add((key, alias))
    return pairs


def manual_attach_pairs(report: dict[str, Any]) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in report.get("manualAttachedInline") or []:
        if not isinstance(row, dict):
            continue
        target = safe_key(row.get("targetKey"))
        if not target:
            continue
        aliases: set[str] = set()
        for stem in row.get("stems") or []:
            aliases.update(video_stem_aliases(stem))
        aliases.update(video_stem_aliases(row.get("name")))
        for alias in aliases:
            pairs.add((target, alias))
    return pairs


def collect_filename_only_attachments(
    report: dict[str, Any],
    evidence: dict[str, Any],
) -> list[dict[str, Any]]:
    authoritative = authoritative_pairs(evidence)
    manual = manual_attach_pairs(report)
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for attached in report.get("attached") or []:
        if not isinstance(attached, dict):
            continue
        key = safe_key(attached.get("key"))
        if not key:
            continue
        for name in attached.get("files") or []:
            base_stem = strip_video_gender_prefix(normalize_video_stem(name))
            if not base_stem:
                continue
            pair_key = (key, base_stem)
            if pair_key in seen:
                continue
            seen.add(pair_key)
            aliases = video_stem_aliases(name)
            if any((key, alias) in authoritative for alias in aliases):
                continue
            if any((key, alias) in manual for alias in aliases):
                continue
            rows.append(
                {
                    "targetKey": key,
                    "kind": safe_key(attached.get("kind")),
                    "mission": safe_key(attached.get("mission")),
                    "stem": base_stem,
                    "files": [
                        file_name
                        for file_name in attached.get("files") or []
                        if strip_video_gender_prefix(normalize_video_stem(file_name)) == base_stem
                    ],
                    "reason": "attached without timelinePlayable evidence or manual attach override",
                }
            )
    return rows


def collect_unresolved_candidates(
    report: dict[str, Any],
    story_entries: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for row in report.get("unresolved") or []:
        if not isinstance(row, dict):
            continue
        stem = strip_video_gender_prefix(normalize_video_stem(row.get("name")))
        if not stem:
            continue
        group = grouped.setdefault(
            stem,
            {
                "stem": stem,
                "kind": safe_key(row.get("kind")),
                "files": [],
                "rels": [],
                "keyCandidates": [],
            },
        )
        group["files"].append(safe_key(row.get("name")))
        group["rels"].append(safe_key(row.get("rel")))
        group["keyCandidates"].extend(safe_key(candidate) for candidate in row.get("keyCandidates") or [])

    out: list[dict[str, Any]] = []
    for group in grouped.values():
        candidates = unique_preserve(candidate for candidate in group["keyCandidates"] if candidate)
        existing = [candidate for candidate in candidates if candidate in story_entries]
        out.append(
            {
                "stem": group["stem"],
                "kind": group["kind"],
                "files": unique_preserve(file_name for file_name in group["files"] if file_name),
                "rels": unique_preserve(rel for rel in group["rels"] if rel)[:6],
                "keyCandidates": candidates,
                "existingCandidates": existing,
                "candidateStatus": "noGeneratedStoryTarget" if not existing else "hasGeneratedStoryTarget",
            }
        )
    return sorted(out, key=lambda row: (row["candidateStatus"], row["stem"]))


def rule_target_exists(
    rule: OverrideRule,
    story_entries: dict[str, dict[str, Any]],
    conv_dir: Path,
    conv_cache: dict[str, Any],
) -> bool:
    return rule.target_key in story_entries and conv_exists(conv_dir, rule.target_key, conv_cache)


def validate_rule(
    rule: OverrideRule,
    *,
    catalog: dict[str, list[dict[str, Any]]],
    story_entries: dict[str, dict[str, Any]],
    conv_dir: Path,
    conv_cache: dict[str, Any],
    narrative_report: dict[str, Any],
) -> dict[str, Any]:
    target_payload = load_conv_payload(conv_dir, rule.target_key, conv_cache)
    target_exists = rule_target_exists(rule, story_entries, conv_dir, conv_cache)
    target_refs = conv_video_refs(target_payload)
    target_audio = conv_audio_events(target_payload)
    target_audio_set = {event.lower() for event in target_audio}

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    stem_results: list[dict[str, Any]] = []

    if not target_exists:
        errors.append({"code": "missingTarget", "targetKey": rule.target_key})
    if not rule.stems:
        severity = errors if rule.bucket == "attachInline" else warnings
        severity.append({"code": "missingStems", "targetKey": rule.target_key})

    for stem in rule.stems:
        catalog_refs = catalog_refs_for_stem(catalog, stem)
        stem_exists = bool(catalog_refs)
        matching_target_refs = refs_match_stems(target_refs, [stem])
        override_marked_refs = [
            ref for ref in matching_target_refs if ref_has_attachment_override(ref, rule.target_key, [stem])
        ]
        standalone_reason = standalone_reason_for_stem(conv_dir, stem, conv_cache)
        manual_rows = report_stem_rows(narrative_report, "manualAttachedInline", rule.target_key, stem)
        suppress_rows = report_stem_rows(narrative_report, "suppressedInline", rule.target_key, stem)

        if not stem_exists:
            errors.append({"code": "missingStem", "targetKey": rule.target_key, "stem": stem})
        if rule.bucket == "attachInline" and stem_exists and target_exists and not matching_target_refs:
            errors.append({"code": "attachNotApplied", "targetKey": rule.target_key, "stem": stem})
        if rule.bucket == "attachInline" and matching_target_refs and not (override_marked_refs or manual_rows):
            warnings.append({"code": "attachNotMarkedManual", "targetKey": rule.target_key, "stem": stem})
        if rule.bucket == "suppressInline" and stem_exists and matching_target_refs:
            errors.append({"code": "suppressNotApplied", "targetKey": rule.target_key, "stem": stem})
        if (
            rule.bucket == "suppressInline"
            and stem_exists
            and standalone_reason != "standaloneVideoManualOverrideSuppressedInline"
            and not suppress_rows
        ):
            warnings.append(
                {
                    "code": "suppressNotVerified",
                    "targetKey": rule.target_key,
                    "stem": stem,
                    "standaloneReason": standalone_reason,
                }
            )

        stem_results.append(
            {
                "stem": stem,
                "exists": stem_exists,
                "matchedCatalogRefs": len(catalog_refs),
                "matchedExamples": compact_catalog_refs(catalog_refs),
                "keyCandidates": extract_ref_key_candidates(catalog_refs),
                "targetNarrativeVideoRefs": len(matching_target_refs),
                "manualAttachReportRows": len(manual_rows),
                "suppressedReportRows": len(suppress_rows),
                "standaloneVideoKey": standalone_video_key_for_stem(stem),
                "standaloneReason": standalone_reason,
            }
        )

    audio_results: list[dict[str, Any]] = []
    if rule.bucket != "attachInline" and rule.audio_from:
        warnings.append({"code": "audioFromOnSuppressRuleIgnored", "targetKey": rule.target_key})
    for source_key in rule.audio_from:
        source_payload = load_conv_payload(conv_dir, source_key, conv_cache)
        source_exists = source_key in story_entries and source_payload is not None
        source_events = conv_audio_events(source_payload)
        source_audio_files = conv_audio_file_count(source_payload)
        source_event_set = {event.lower() for event in source_events}
        copied_events = sorted(source_event_set & target_audio_set)
        missing_events = sorted(source_event_set - target_audio_set)
        if not source_exists:
            errors.append({"code": "missingAudioFromSource", "targetKey": rule.target_key, "sourceKey": source_key})
        elif not source_events:
            warnings.append(
                {
                    "code": "audioFromSourceHasNoEvents",
                    "targetKey": rule.target_key,
                    "sourceKey": source_key,
                    "audioFiles": source_audio_files,
                }
            )
        elif target_exists and not copied_events:
            warnings.append(
                {
                    "code": "audioFromNotApplied",
                    "targetKey": rule.target_key,
                    "sourceKey": source_key,
                    "sourceEvents": len(source_events),
                }
            )
        audio_results.append(
            {
                "sourceKey": source_key,
                "exists": source_exists,
                "audioEvents": len(source_events),
                "audioFiles": source_audio_files,
                "copiedEventsInTarget": len(copied_events),
                "missingEventsInTarget": len(missing_events),
            }
        )

    return {
        **asdict(rule),
        "targetExists": target_exists,
        "targetKind": safe_key((story_entries.get(rule.target_key) or {}).get("d")),
        "targetNarrativeVideoRefs": len(target_refs),
        "targetAudioEvents": len(target_audio),
        "stems": stem_results,
        "audioFrom": audio_results,
        "errors": errors,
        "warnings": warnings,
        "status": "error" if errors else "warning" if warnings else "ok",
    }


def summarize_rule_results(rule_results: list[dict[str, Any]]) -> dict[str, Any]:
    error_counts: dict[str, int] = defaultdict(int)
    warning_counts: dict[str, int] = defaultdict(int)
    for row in rule_results:
        for error in row.get("errors") or []:
            error_counts[safe_key(error.get("code"))] += 1
        for warning in row.get("warnings") or []:
            warning_counts[safe_key(warning.get("code"))] += 1
    return {
        "rules": len(rule_results),
        "rulesOk": sum(1 for row in rule_results if row.get("status") == "ok"),
        "rulesWithErrors": sum(1 for row in rule_results if row.get("status") == "error"),
        "rulesWithWarningsOnly": sum(1 for row in rule_results if row.get("status") == "warning"),
        "errorCounts": dict(sorted(error_counts.items())),
        "warningCounts": dict(sorted(warning_counts.items())),
    }


def collect_known_false_suppressions(report: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in report.get("suppressedInline") or []:
        if not isinstance(row, dict):
            continue
        target = safe_key(row.get("targetKey"))
        stem = strip_video_gender_prefix(normalize_video_stem(row.get("name") or next(iter(row.get("stems") or []), "")))
        key = (target, stem)
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "targetKey": target,
                "stem": stem,
                "files": unique_preserve(
                    item.get("name")
                    for item in report.get("suppressedInline") or []
                    if isinstance(item, dict)
                    and safe_key(item.get("targetKey")) == target
                    and strip_video_gender_prefix(normalize_video_stem(item.get("name"))) == stem
                ),
                "note": safe_key(row.get("note")),
            }
        )
    return rows


def build_audit(args: argparse.Namespace) -> dict[str, Any]:
    language = args.language.upper()
    lang_dir = args.conv_root / language
    conv_dir = lang_dir / "conv"
    index_path = lang_dir / "index.json"
    evidence_path = lang_dir / "narrative_video_evidence.json"
    narrative_report_path = args.story_reports_dir / f"narrative_videos_{language}.json"

    override_payload = read_json(args.override, {})
    rules = parse_override_rules(override_payload)
    story_entries = load_story_entries(index_path)
    narrative_report = read_json(narrative_report_path, {})
    evidence = read_json(evidence_path, {})
    video_index = read_json(args.video_index, {})
    video_bindings = read_json(args.video_bindings, {})

    catalog = build_video_catalog(
        narrative_report if isinstance(narrative_report, dict) else {},
        evidence if isinstance(evidence, dict) else {},
        video_index if isinstance(video_index, dict) else {},
        video_bindings if isinstance(video_bindings, dict) else {},
    )

    input_warnings: list[str] = []
    for label, path, payload in (
        ("override", args.override, override_payload),
        ("story index", index_path, story_entries),
        ("narrative video report", narrative_report_path, narrative_report),
        ("narrative video evidence", evidence_path, evidence),
        ("video index", args.video_index, video_index),
        ("video bindings", args.video_bindings, video_bindings),
    ):
        if not path.exists():
            input_warnings.append(f"missing {label}: {rel_path(path)}")
        elif payload in ({}, [], None):
            input_warnings.append(f"empty or unreadable {label}: {rel_path(path)}")

    conv_cache: dict[str, Any] = {}
    rule_results = [
        validate_rule(
            rule,
            catalog=catalog,
            story_entries=story_entries,
            conv_dir=conv_dir,
            conv_cache=conv_cache,
            narrative_report=narrative_report if isinstance(narrative_report, dict) else {},
        )
        for rule in rules
    ]
    rule_summary = summarize_rule_results(rule_results)
    known_false_suppressions = collect_known_false_suppressions(narrative_report if isinstance(narrative_report, dict) else {})
    filename_only_attachments = collect_filename_only_attachments(
        narrative_report if isinstance(narrative_report, dict) else {},
        evidence if isinstance(evidence, dict) else {},
    )
    unresolved_candidates = collect_unresolved_candidates(
        narrative_report if isinstance(narrative_report, dict) else {},
        story_entries,
    )
    likely_false_candidate_count = sum(
        1 for row in unresolved_candidates if row.get("candidateStatus") == "noGeneratedStoryTarget"
    )

    return {
        "generated": utc_now(),
        "language": language,
        "inputs": {
            "override": rel_path(args.override),
            "index": rel_path(index_path),
            "convDir": rel_path(conv_dir),
            "narrativeVideoReport": rel_path(narrative_report_path),
            "narrativeVideoEvidence": rel_path(evidence_path),
            "videoIndex": rel_path(args.video_index),
            "videoBindings": rel_path(args.video_bindings),
        },
        "inputWarnings": input_warnings,
        "summary": {
            **rule_summary,
            "overrideStems": sum(len(rule.stems) for rule in rules),
            "catalogVideoStemAliases": len(catalog),
            "knownFalseSuppressedAttachments": len(known_false_suppressions),
            "filenameOnlyAttachmentCandidates": len(filename_only_attachments),
            "unresolvedVideoCandidateGroups": len(unresolved_candidates),
            "likelyFalseUnresolvedCandidateGroups": likely_false_candidate_count,
        },
        "rules": rule_results,
        "knownFalseSuppressedAttachments": known_false_suppressions,
        "filenameOnlyAttachmentCandidates": filename_only_attachments,
        "unresolvedVideoCandidates": unresolved_candidates,
    }


def issue_lines(row: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for issue in row.get("errors") or []:
        lines.append(f"error:{issue.get('code')}")
    for issue in row.get("warnings") or []:
        lines.append(f"warn:{issue.get('code')}")
    return lines


def render_stem_list(stems: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for row in stems:
        marker = "ok" if row.get("exists") else "missing"
        refs = row.get("matchedCatalogRefs") or 0
        target_refs = row.get("targetNarrativeVideoRefs") or 0
        parts.append(f"`{md_escape(row.get('stem'))}` {marker} refs={refs} targetRefs={target_refs}")
    return "<br>".join(parts) if parts else ""


def markdown_report(payload: dict[str, Any], *, limit: int = 80) -> str:
    summary = payload["summary"]
    lines = [
        "# Narrative Video Override Audit",
        "",
        f"Generated: {payload['generated']}",
        f"Language: `{payload['language']}`",
        "",
        "## Summary",
        "",
        f"- Override rules: `{summary['rules']}` (`{summary['rulesOk']}` ok, "
        f"`{summary['rulesWithWarningsOnly']}` warning-only, `{summary['rulesWithErrors']}` with errors)",
        f"- Error counts: `{summary['errorCounts']}`",
        f"- Warning counts: `{summary['warningCounts']}`",
        f"- Override stems: `{summary['overrideStems']}`",
        f"- Known false suppressed attachments: `{summary['knownFalseSuppressedAttachments']}`",
        f"- Filename-only attachment candidates: `{summary['filenameOnlyAttachmentCandidates']}`",
        f"- Unresolved video candidate groups: `{summary['unresolvedVideoCandidateGroups']}` "
        f"(`{summary['likelyFalseUnresolvedCandidateGroups']}` with no generated target)",
        "",
    ]
    if payload.get("inputWarnings"):
        lines.extend(["## Input Warnings", ""])
        lines.extend(f"- {md_escape(warning)}" for warning in payload["inputWarnings"])
        lines.append("")

    lines.extend(
        [
            "## Override Rules",
            "",
            "| status | bucket | target | stems | audioFrom | issues |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
    )
    for row in payload["rules"]:
        audio_sources = ", ".join(
            f"`{md_escape(item.get('sourceKey'))}` events={item.get('audioEvents')} copied={item.get('copiedEventsInTarget')}"
            for item in row.get("audioFrom") or []
        )
        lines.append(
            f"| `{row.get('status')}` "
            f"| `{md_escape(row.get('bucket'))}` "
            f"| `{md_escape(row.get('target_key'))}` "
            f"| {render_stem_list(row.get('stems') or [])} "
            f"| {audio_sources or ''} "
            f"| {', '.join(issue_lines(row)) or 'none'} |"
        )
    lines.append("")

    if payload["knownFalseSuppressedAttachments"]:
        lines.extend(["## Known False Suppressions", ""])
        for row in payload["knownFalseSuppressedAttachments"][:limit]:
            files = ", ".join(f"`{md_escape(name)}`" for name in row.get("files") or [])
            lines.append(
                f"- `{md_escape(row.get('stem'))}` suppressed for `{md_escape(row.get('targetKey'))}`"
                + (f": {files}" if files else "")
            )
        lines.append("")

    if payload["filenameOnlyAttachmentCandidates"]:
        lines.extend(
            [
                "## Filename-Only Attachment Candidates",
                "",
                "These generated inline attachments have no `timelinePlayable` evidence row and no manual attach override.",
                "",
                "| target | kind | mission | stem | files |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in payload["filenameOnlyAttachmentCandidates"][:limit]:
            files = ", ".join(f"`{md_escape(name)}`" for name in row.get("files") or [])
            lines.append(
                f"| `{md_escape(row.get('targetKey'))}` "
                f"| `{md_escape(row.get('kind'))}` "
                f"| `{md_escape(row.get('mission'))}` "
                f"| `{md_escape(row.get('stem'))}` "
                f"| {files} |"
            )
        if len(payload["filenameOnlyAttachmentCandidates"]) > limit:
            lines.append(f"| ... | ... | ... | `{len(payload['filenameOnlyAttachmentCandidates']) - limit}` more | ... |")
        lines.append("")

    if payload["unresolvedVideoCandidates"]:
        lines.extend(
            [
                "## Unresolved Video Candidates",
                "",
                "| status | stem | files | generated candidates | all candidates |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in payload["unresolvedVideoCandidates"][:limit]:
            files = ", ".join(f"`{md_escape(name)}`" for name in row.get("files") or [])
            existing = ", ".join(f"`{md_escape(key)}`" for key in row.get("existingCandidates") or [])
            candidates = ", ".join(f"`{md_escape(key)}`" for key in row.get("keyCandidates") or [])
            lines.append(
                f"| `{md_escape(row.get('candidateStatus'))}` "
                f"| `{md_escape(row.get('stem'))}` "
                f"| {files} "
                f"| {existing or ''} "
                f"| {candidates or ''} |"
            )
        if len(payload["unresolvedVideoCandidates"]) > limit:
            lines.append(f"| ... | `{len(payload['unresolvedVideoCandidates']) - limit}` more | ... | ... | ... |")
        lines.append("")

    lines.extend(["## Inputs", ""])
    for label, path in payload["inputs"].items():
        lines.append(f"- {label}: `{md_escape(path)}`")
    return "\n".join(lines) + "\n"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", default="CN", help="Story language code to validate")
    parser.add_argument("--override", type=Path, default=DEFAULT_OVERRIDE_PATH)
    parser.add_argument("--conv-root", type=Path, default=DEFAULT_CONV_ROOT)
    parser.add_argument("--video-index", type=Path, default=DEFAULT_VIDEO_INDEX)
    parser.add_argument("--video-bindings", type=Path, default=DEFAULT_VIDEO_BINDINGS)
    parser.add_argument("--reports-dir", type=Path, default=DEFAULT_REPORTS_DIR)
    parser.add_argument("--story-reports-dir", type=Path, default=DEFAULT_STORY_REPORTS_DIR)
    parser.add_argument("--json", type=Path, help="output JSON path")
    parser.add_argument("--markdown", type=Path, help="output Markdown path")
    parser.add_argument("--no-write", action="store_true", help="print the summary without writing reports")
    parser.add_argument("--strict", action="store_true", help="exit non-zero when rule validation errors are present")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    args.language = args.language.upper()
    payload = build_audit(args)
    language = payload["language"]
    out_json = args.json or args.reports_dir / f"narrative_video_override_audit_{language}.json"
    out_md = args.markdown or args.reports_dir / f"narrative_video_override_audit_{language}.md"
    text = markdown_report(payload)
    if not args.no_write:
        write_report_json(out_json, payload)
        write_text_if_changed(out_md, text)
        print(f"Wrote {rel_path(out_json)}")
        print(f"Wrote {rel_path(out_md)}")
    else:
        print("No reports written (--no-write).")
    summary = payload["summary"]
    print(
        "Narrative video override audit "
        f"[{language}]: {summary['rules']} rules; "
        f"errors={summary['rulesWithErrors']}; "
        f"warnings={summary['rulesWithWarningsOnly']}; "
        f"filename-only={summary['filenameOnlyAttachmentCandidates']}; "
        f"unresolved={summary['unresolvedVideoCandidateGroups']}."
    )
    if args.strict and summary["rulesWithErrors"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
