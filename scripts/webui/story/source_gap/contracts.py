"""Stable schemas and small, versioned contracts for Story gap recovery."""
from __future__ import annotations

import hashlib
import json
import re


SCHEMA = "sourceStoryGapQueue.v132"
STORY_BINDING_COVERAGE_SCHEMA_VERSION = 19

LEVELSCRIPT_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "levelscript-interactive-narrative-config-v1"
)
LEVELDATA_INTERACTIVE_NARRATIVE_MAPPING_ID = (
    "leveldata-interactive-narrative-config-v5"
)
LEVELDATA_INTERACTIVE_HORN_MAPPING_ID = (
    "leveldata-interactive-horn-dialog-config-v1"
)
LEVELDATA_INTERACTIVE_HORN_NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-29-interactive-horn-dialog-v1"
)
LEVELDATA_INTERACTIVE_HORN_TEMPLATE_SHA256 = (
    "1200acb7208de5e4b9e861dc511cc3a3d4f1f5c56dd4b59f1dcb0ef7ab2ea33e"
)

BUCKET_ORDER = ("main", "event", "major", "character", "other")
FRONTIER_ORDER = (
    "missing-mission-runtime-bundle",
    "levelscript-control-flow",
    "source-cycle-review",
    "quest-scene-attachment",
    "dialog-option-runtime",
    "unresolved-source-node",
    "isolated-scene-source-link",
)

# Scores rank investigation value only; they never assert chronology.
SCORE_WEIGHTS = {
    "missingMissionBundle": 100,
    "sourceCycles": 20,
    "cycleScenes": 8,
    "untypedMultiSceneLevelscriptContexts": 10,
    "actionableCoreIsolatedScenes": 5,
    "actionableWeakOnlyScenes": 4,
    "unresolvedSourceNodes": 4,
    "questIdsWithoutStrictStoryAttachment": 3,
    "actionableNoExplicitOptionRouteGroups": 2,
    "actionableExcludedOptionEvidenceGroups": 2,
}

_MISSION_TYPE_RE = re.compile(r"^([a-z]+)")
_PRIORITY_MISSION_TYPES = {
    "e": "main",
    "a": "event",
    "gm": "major",
    "c": "character",
}


def priority_bucket(mission: str) -> str:
    """Return the maintained recovery bucket for a mission identifier."""
    match = _MISSION_TYPE_RE.match(str(mission or "").strip().lower())
    return _PRIORITY_MISSION_TYPES.get(match.group(1) if match else "", "")


def target_set_sha256(target_missions: dict[str, set[str]]) -> str:
    """Hash an exact Story-key/mission target set independently of scoring."""
    canonical = {
        key: sorted(target_missions[key])
        for key in sorted(target_missions)
    }
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
