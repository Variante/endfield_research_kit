"""Strict parsing and build-time validation for narrative video overrides."""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BUCKETS = ("attachInline", "suppressInline")
RULE_FIELDS = frozenset({"stems", "audioFrom", "note"})
ROOT = Path(__file__).resolve().parents[2]


def _source_label(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except (OSError, ValueError):
        return path.as_posix()


def normalize_video_override_stem(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    return re.sub(r"\.[^.]+$", "", text.rsplit("/", 1)[-1]).lower()


@dataclass(frozen=True)
class NarrativeVideoOverrides:
    source: Path
    source_hash: str
    buckets: dict[str, dict[str, list[dict[str, Any]]]]

    def rules_for(self, bucket: str) -> dict[str, list[dict[str, Any]]]:
        return self.buckets[bucket]

    def iter_rules(self) -> Iterable[tuple[str, str, dict[str, Any]]]:
        for bucket in BUCKETS:
            for target_key, rules in self.buckets[bucket].items():
                for rule in rules:
                    yield bucket, target_key, rule


class NarrativeVideoOverrideValidationError(ValueError):
    def __init__(
        self,
        *,
        source: Path,
        source_hash: str,
        stage: str,
        issues: list[dict[str, Any]],
    ) -> None:
        self.source = source
        self.source_hash = source_hash
        self.stage = stage
        self.issues = issues[:20]
        first = self.issues[0] if self.issues else {"code": "unknown"}
        location = "/".join(
            str(first.get(field) or "")
            for field in ("bucket", "targetKey", "stem", "sourceKey")
            if first.get(field)
        )
        detail = f" at {location}" if location else ""
        super().__init__(
            "narrative video override validation failed "
            f"during {stage}: {first.get('code', 'unknown')}{detail} "
            f"[{source}]"
        )

    def report(self, *, language: str) -> dict[str, Any]:
        return {
            "language": language,
            "summary": {
                "status": "error",
                "validationStage": self.stage,
                "validationErrors": len(self.issues),
            },
            "overrideValidation": {
                "status": "error",
                "stage": self.stage,
                "source": _source_label(self.source),
                "sourceSha256": self.source_hash,
                "issues": self.issues,
            },
        }


def _issue(
    code: str,
    *,
    bucket: str = "",
    target_key: str = "",
    stem: str = "",
    source_key: str = "",
    expected: object = None,
    actual: object = None,
) -> dict[str, Any]:
    return {
        key: value
        for key, value in {
            "code": code,
            "bucket": bucket,
            "targetKey": target_key,
            "stem": stem,
            "sourceKey": source_key,
            "expected": expected,
            "actual": actual,
        }.items()
        if value not in (None, "")
    }


def _raise(
    *,
    source: Path,
    source_hash: str,
    stage: str,
    issues: list[dict[str, Any]],
) -> None:
    if issues:
        raise NarrativeVideoOverrideValidationError(
            source=source,
            source_hash=source_hash,
            stage=stage,
            issues=issues,
        )


def load_narrative_video_overrides(path: Path) -> NarrativeVideoOverrides:
    """Load the single maintained override schema, rejecting silent fallback."""
    source_hash = ""
    try:
        raw = path.read_bytes()
        source_hash = hashlib.sha256(raw).hexdigest()
        payload = json.loads(raw.decode("utf-8-sig"))
    except FileNotFoundError:
        _raise(
            source=path,
            source_hash=source_hash,
            stage="schema",
            issues=[_issue("missing_override_file", expected="readable JSON object")],
        )
        raise AssertionError("unreachable")
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _raise(
            source=path,
            source_hash=source_hash,
            stage="schema",
            issues=[
                _issue(
                    "invalid_override_json",
                    expected="UTF-8 JSON object",
                    actual=str(exc),
                )
            ],
        )
        raise AssertionError("unreachable")

    issues: list[dict[str, Any]] = []
    if not isinstance(payload, dict):
        issues.append(
            _issue(
                "invalid_root_type",
                expected="object",
                actual=type(payload).__name__,
            )
        )
        payload = {}
    unknown_root_fields = sorted(
        key for key in payload if key not in {*BUCKETS, "_note"}
    )
    if unknown_root_fields:
        issues.append(
            _issue(
                "unknown_root_fields",
                expected=["_note", *BUCKETS],
                actual=unknown_root_fields,
            )
        )

    buckets: dict[str, dict[str, list[dict[str, Any]]]] = {
        bucket: {} for bucket in BUCKETS
    }
    attachment_owners: dict[str, str] = {}
    for bucket in BUCKETS:
        raw_rules = payload.get(bucket, {})
        if not isinstance(raw_rules, dict):
            issues.append(
                _issue(
                    "invalid_bucket_type",
                    bucket=bucket,
                    expected="object keyed by target Story key",
                    actual=type(raw_rules).__name__,
                )
            )
            continue
        for raw_target, raw_rule in raw_rules.items():
            target_key = str(raw_target or "").strip()
            if not target_key:
                issues.append(_issue("missing_target_key", bucket=bucket))
                continue
            if not isinstance(raw_rule, dict):
                issues.append(
                    _issue(
                        "invalid_rule_type",
                        bucket=bucket,
                        target_key=target_key,
                        expected="object",
                        actual=type(raw_rule).__name__,
                    )
                )
                continue
            unknown_fields = sorted(set(raw_rule) - RULE_FIELDS)
            if unknown_fields:
                issues.append(
                    _issue(
                        "unknown_rule_fields",
                        bucket=bucket,
                        target_key=target_key,
                        expected=sorted(RULE_FIELDS),
                        actual=unknown_fields,
                    )
                )
            raw_stems = raw_rule.get("stems")
            if not isinstance(raw_stems, list):
                issues.append(
                    _issue(
                        "invalid_stems_type",
                        bucket=bucket,
                        target_key=target_key,
                        expected="non-empty string array",
                        actual=type(raw_stems).__name__,
                    )
                )
                raw_stems = []
            stems: list[str] = []
            for raw_stem in raw_stems:
                stem = (
                    normalize_video_override_stem(raw_stem)
                    if isinstance(raw_stem, str)
                    else ""
                )
                if not stem:
                    issues.append(
                        _issue(
                            "invalid_stem",
                            bucket=bucket,
                            target_key=target_key,
                            expected="non-empty string",
                            actual=raw_stem,
                        )
                    )
                elif stem in stems:
                    issues.append(
                        _issue(
                            "duplicate_stem",
                            bucket=bucket,
                            target_key=target_key,
                            stem=stem,
                        )
                    )
                else:
                    stems.append(stem)
            if not stems:
                issues.append(
                    _issue(
                        "missing_stems",
                        bucket=bucket,
                        target_key=target_key,
                        expected="at least one video stem",
                        actual=0,
                    )
                )

            raw_audio_from = raw_rule.get("audioFrom", [])
            if not isinstance(raw_audio_from, list):
                issues.append(
                    _issue(
                        "invalid_audio_from_type",
                        bucket=bucket,
                        target_key=target_key,
                        expected="string array",
                        actual=type(raw_audio_from).__name__,
                    )
                )
                raw_audio_from = []
            audio_from: list[str] = []
            for raw_source in raw_audio_from:
                source_key = raw_source.strip() if isinstance(raw_source, str) else ""
                if not source_key:
                    issues.append(
                        _issue(
                            "invalid_audio_source",
                            bucket=bucket,
                            target_key=target_key,
                            expected="non-empty Story key",
                            actual=raw_source,
                        )
                    )
                elif source_key in audio_from:
                    issues.append(
                        _issue(
                            "duplicate_audio_source",
                            bucket=bucket,
                            target_key=target_key,
                            source_key=source_key,
                        )
                    )
                else:
                    audio_from.append(source_key)
            if bucket == "suppressInline" and audio_from:
                issues.append(
                    _issue(
                        "audio_source_on_suppress_rule",
                        bucket=bucket,
                        target_key=target_key,
                        actual=audio_from,
                    )
                )

            note = raw_rule.get("note", "")
            if not isinstance(note, str):
                issues.append(
                    _issue(
                        "invalid_note_type",
                        bucket=bucket,
                        target_key=target_key,
                        expected="string",
                        actual=type(note).__name__,
                    )
                )
                note = ""
            for stem in stems:
                if bucket == "attachInline":
                    previous_target = attachment_owners.setdefault(stem, target_key)
                    if previous_target != target_key:
                        issues.append(
                            _issue(
                                "ambiguous_attachment_stem",
                                bucket=bucket,
                                target_key=target_key,
                                stem=stem,
                                expected=previous_target,
                                actual=target_key,
                            )
                        )
            buckets[bucket].setdefault(target_key, []).append(
                {
                    "targetKey": target_key,
                    "stems": stems,
                    "audioFrom": audio_from,
                    "note": note,
                    "source": path,
                }
            )

    _raise(
        source=path,
        source_hash=source_hash,
        stage="schema",
        issues=issues,
    )
    return NarrativeVideoOverrides(path, source_hash, buckets)


def validate_narrative_video_override_inputs(
    overrides: NarrativeVideoOverrides,
    *,
    story_keys: Iterable[str],
    video_refs: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Require every rule target and video stem to exist in current inputs."""
    current_story_keys = {str(key) for key in story_keys if key}
    current_stems = {
        stem
        for ref in video_refs
        for stem in (
            normalize_video_override_stem(ref.get("stem")),
            normalize_video_override_stem(ref.get("baseStem")),
            normalize_video_override_stem(ref.get("name")),
        )
        if stem
    }
    issues: list[dict[str, Any]] = []
    rule_count = 0
    stem_count = 0
    audio_source_count = 0
    for bucket, target_key, rule in overrides.iter_rules():
        rule_count += 1
        stems = list(rule.get("stems") or [])
        stem_count += len(stems)
        if target_key not in current_story_keys:
            issues.append(
                _issue(
                    "stale_target_key",
                    bucket=bucket,
                    target_key=target_key,
                    expected="current generated Story key",
                    actual="missing",
                )
            )
        for stem in stems:
            if stem not in current_stems:
                issues.append(
                    _issue(
                        "stale_video_stem",
                        bucket=bucket,
                        target_key=target_key,
                        stem=stem,
                        expected="current narrative video asset",
                        actual="missing",
                    )
                )
        for source_key in rule.get("audioFrom") or []:
            audio_source_count += 1
            if source_key not in current_story_keys:
                issues.append(
                    _issue(
                        "stale_audio_source_key",
                        bucket=bucket,
                        target_key=target_key,
                        source_key=source_key,
                        expected="current generated Story key",
                        actual="missing",
                    )
                )
    _raise(
        source=overrides.source,
        source_hash=overrides.source_hash,
        stage="inputs",
        issues=issues,
    )
    return {
        "status": "ok",
        "stage": "inputs",
        "source": _source_label(overrides.source),
        "sourceSha256": overrides.source_hash,
        "rules": rule_count,
        "stems": stem_count,
        "audioSources": audio_source_count,
        "storyKeys": len(current_story_keys),
        "videoStems": len(current_stems),
    }


def validate_narrative_video_override_application(
    overrides: NarrativeVideoOverrides,
    *,
    applied_attach: Iterable[tuple[str, str]],
    applied_suppress: Iterable[tuple[str, str]],
    input_validation: dict[str, Any],
) -> dict[str, Any]:
    """Require each current rule stem to affect the intended build result."""
    applied = {
        "attachInline": set(applied_attach),
        "suppressInline": set(applied_suppress),
    }
    issues: list[dict[str, Any]] = []
    for bucket, target_key, rule in overrides.iter_rules():
        for stem in rule.get("stems") or []:
            if (target_key, stem) not in applied[bucket]:
                issues.append(
                    _issue(
                        "override_not_applied",
                        bucket=bucket,
                        target_key=target_key,
                        stem=stem,
                        expected="matching built video reference",
                        actual="none",
                    )
                )
    _raise(
        source=overrides.source,
        source_hash=overrides.source_hash,
        stage="application",
        issues=issues,
    )
    return {
        **input_validation,
        "stage": "application",
        "appliedAttachPairs": len(applied["attachInline"]),
        "appliedSuppressPairs": len(applied["suppressInline"]),
    }


__all__ = [
    "NarrativeVideoOverrideValidationError",
    "NarrativeVideoOverrides",
    "load_narrative_video_overrides",
    "normalize_video_override_stem",
    "validate_narrative_video_override_application",
    "validate_narrative_video_override_inputs",
]
