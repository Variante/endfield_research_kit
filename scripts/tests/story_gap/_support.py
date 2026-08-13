from __future__ import annotations

import base64
import copy
import json
import tempfile
import unittest
from functools import cache
from pathlib import Path
from unittest.mock import patch


from scripts.story_builder.source_gap import contracts as _contracts
from scripts.story_builder.source_gap import attachment_evidence as _attachment_evidence
from scripts.story_builder.source_gap import content_evidence as _content_evidence
from scripts.story_builder.source_gap import core as _core
from scripts.story_builder.source_gap import data as _data
from scripts.story_builder.source_gap import foundation as _foundation
from scripts.story_builder.source_gap import model as _model
from scripts.story_builder.source_gap import offline_evidence as _offline_evidence
from scripts.story_builder.source_gap import providers as _providers
from scripts.story_builder.level_bindings import (
    build_levelscript_action_story_occurrences,
    build_levelscript_native_story_playback_index,
)
from scripts.story_builder.anime_assets import (
    recover_dialog_tree_definition_evidence,
)


class _GapQueueTestFacade:
    """Keep legacy white-box patches aligned with their new domain owner."""

    _modules = (
        _core,
        _model,
        _offline_evidence,
        _content_evidence,
        _attachment_evidence,
        _providers,
        _data,
        _foundation,
        _contracts,
    )

    def __init__(self) -> None:
        object.__setattr__(self, "_restore", {})

    def __getattr__(self, name: str):
        for module in self._modules:
            if hasattr(module, name):
                return getattr(module, name)
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        owners = [module for module in self._modules if hasattr(module, name)]
        if not owners:
            raise AttributeError(name)
        self._restore.setdefault(name, []).append(
            [(module, getattr(module, name)) for module in owners]
        )
        for module in owners:
            setattr(module, name, value)

    def __delattr__(self, name: str) -> None:
        stack = self._restore.get(name) or []
        if not stack:
            raise AttributeError(name)
        for module, value in stack.pop():
            setattr(module, name, value)


gap_queue = _GapQueueTestFacade()


@cache
def current_npc_proxy_consumer_contexts(story_key: str) -> tuple[dict, ...]:
    """Project the current general NpcProxy scan into the legacy test shape."""
    npc_proxy_ex = gap_queue.read_json(
        gap_queue.ROOT
        / "export_full/structured/Persistent/Data/Json/GameplayConfig/"
        "NpcProxyExDataTable.json",
        {},
    )
    facts, failure = gap_queue._generic_missionless_npc_proxy_dialog_facts(
        story_key,
        npc_proxy_ex,
        gap_queue.read_json(
            gap_queue.ROOT
            / "export_full/structured/StreamingAssets/Data/Json/GameplayConfig/"
            "NpcProxyTable.json",
            {},
        ),
        gap_queue.read_json(
            gap_queue.ROOT / "export_full/recovered/dialog_id_table_index.json",
            {},
        ),
    )
    if failure is not None:
        raise AssertionError(failure)
    rows = []
    for consumer in (facts or {}).get("npcProxyConsumers") or []:
        proxy_id = consumer["npcProxyId"]
        entry_index = consumer["activeRowIndex"]
        rows.append({
            "proxyId": proxy_id,
            "entryIndex": entry_index,
            "entry": npc_proxy_ex["data"][proxy_id][entry_index],
        })
    return tuple(rows)


def partial_mission(
    mission: str,
    *,
    scenes: list[str],
    isolated: list[str] | None = None,
    weak_only: list[str] | None = None,
    cycles: list[list[str]] | None = None,
    edges: list[dict] | None = None,
    no_route_groups: int = 0,
    excluded_groups: int = 0,
) -> dict:
    cycle_rows = [
        {"id": f"p{index}", "sceneKeys": values, "cyclic": True}
        for index, values in enumerate(cycles or [], start=1)
    ]
    return {
        "mission": mission,
        "summary": {
            "sceneCount": len(scenes),
            "strongEdgeCount": sum(edge.get("tier") == "strong" for edge in edges or []),
            "reducedComponentEdgeCount": 0,
            "comparableScenePairs": 0,
            "totalScenePairs": len(scenes) * (len(scenes) - 1) // 2,
            "isolatedSceneCount": len(isolated or []),
            "weakOnlySceneCount": len(weak_only or []),
            "cycleCount": len(cycle_rows),
            "questForkCount": 0,
            "questMergeCount": 0,
            "dialogLineOptionGroupCount": 0,
            "noExplicitRouteGroupCount": no_route_groups,
            "excludedDialogLineOptionGroupCount": excluded_groups,
        },
        "nodes": [
            {
                "key": key,
                "kind": "dlg",
                "relationStatus": "isolated" if key in (isolated or []) else "source-ordered",
            }
            for key in scenes
        ],
        "directEdges": edges or [],
        "cycles": cycle_rows,
        "isolatedSceneKeys": isolated or [],
        "weakOnlySceneKeys": weak_only or [],
        "unresolvedSourceNodes": [],
    }


def mission_payload(
    *,
    quest_ids: list[str] | None = None,
    contexts: list[dict] | None = None,
    sequences: list[dict] | None = None,
    connections: list[dict] | None = None,
    placements: dict | None = None,
) -> dict:
    return {
        "flow": {
            "missionStoryConnections": connections or [],
        },
        "timelineRecovery": {
            "quests": [{"questId": quest_id} for quest_id in quest_ids or []],
            "sourceBackedStoryCallContexts": contexts or [],
            "sourceBackedSceneSequences": sequences or [],
            "scenePlacement": placements or {},
            "unresolved": [],
        }
    }



class SourceGapTestCase(unittest.TestCase):
    @staticmethod
    def typed_selector_connection(story_key: str) -> dict:
        alternatives = [
            {"role": "first", "key": "dlg_a"},
            {"role": "repeat", "key": "dlg_b"},
        ]
        return {
            "missionId": "m1",
            "key": story_key,
            "relation": "opaque_system_selector",
            "selectorKind": "typed_table_story_selector",
            "selectorGroupId": "target_opaque",
            "selectorRole": next(
                item["role"] for item in alternatives if item["key"] == story_key
            ),
            "selectorAlternatives": alternatives,
            "graphEffect": "none",
            "sourceFiles": ["TypedTable.json"],
            "nativeMappingId": "mapping-v1",
            "nativeConsumers": [{"method": "Select"}],
            "orderBoundary": "no relative order",
        }

__all__ = [
    "SourceGapTestCase",
    "Path",
    "base64",
    "build_levelscript_action_story_occurrences",
    "build_levelscript_native_story_playback_index",
    "copy",
    "current_npc_proxy_consumer_contexts",
    "gap_queue",
    "json",
    "mission_payload",
    "partial_mission",
    "patch",
    "recover_dialog_tree_definition_evidence",
    "tempfile",
    "unittest",
]
