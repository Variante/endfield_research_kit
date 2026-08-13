"""Small compatibility-free facade for source-gap orchestration.

The implementation lives in focused domain modules.  Keeping only the
operations used by :mod:`api` here makes ownership visible without recreating
the former monolithic module through hundreds of re-exports.
"""
from __future__ import annotations

from ..mission_recovery import natural_key
from ..source_story_partial_order import (
    build_report as build_partial_order_report,
    load_mission_payload_with_variants,
)
from .attachment_evidence import (
    build_general_quest_attachment_boundary_index,
    build_quest_attachment_diagnostic_index,
    load_story_trigger_manifest_evidence,
)
from .content_evidence import project_authored_story_content_keys
from .model import build_gap_report
from .offline_evidence import build_offline_exhaustion_index


__all__ = [
    "build_gap_report",
    "build_general_quest_attachment_boundary_index",
    "build_offline_exhaustion_index",
    "build_partial_order_report",
    "build_quest_attachment_diagnostic_index",
    "load_mission_payload_with_variants",
    "load_story_trigger_manifest_evidence",
    "natural_key",
    "project_authored_story_content_keys",
]
