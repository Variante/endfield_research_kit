"""Reviewed shallow task envelopes inside decoded ExtendData behavior graphs.

All currently reached task names and immediate fields are framed here. Nested
object/list contents remain opaque except for the two typed list wrappers and
one behavior-tag wrapper. Stored fields do not imply execution, blackboard
values, or a graph-owner relationship.
"""

from __future__ import annotations

import json
from collections import Counter
from functools import lru_cache
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.extend_data_graph import json_kind_matches


SCHEMA = "endfield.extend-data-task-envelopes.v2"
CONTRACT_PATH = CONTRACTS_DIR / "extend_data_task_envelopes.json"


class TaskShapeError(ValueError):
    """A reached task type or shallow field shape differs from the review."""


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if (contract.get("schema") != SCHEMA or contract.get("status") != "reviewed-structural-only"
            or contract.get("requireKnownTaskTypes") is not True):
        raise TaskShapeError("unsupported ExtendData task contract")
    names = [row["type"] for row in contract["profiles"]]
    if len(names) != len(set(names)):
        raise TaskShapeError("duplicate reviewed task profile")
    return contract


def validate_tasks(document: dict[str, Any], *, label: str,
                   contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Traverse typed task lists and validate every reviewed field envelope."""
    contract = contract or load_contract()
    profiles = {row["type"]: row for row in contract["profiles"]}
    counts: Counter[str] = Counter()
    selected = 0
    typed_children = 0
    max_depth = 0
    behavior_tags: Counter[int] = Counter()

    def visit(task: Any, path: str, depth: int) -> None:
        nonlocal selected, typed_children, max_depth
        if depth > 128:
            raise TaskShapeError(f"{path}: nested task depth exceeds 128")
        if not isinstance(task, dict) or not isinstance(task.get("$type"), str):
            raise TaskShapeError(f"{path}: expected typed task object")
        tag = task["$type"]
        counts[tag] += 1
        max_depth = max(max_depth, depth)
        profile = profiles.get(tag)
        child_field = None
        if profile is None and contract["requireKnownTaskTypes"]:
            raise TaskShapeError(f"{path}: unreviewed task type {tag}")
        if profile is not None:
            fields = frozenset(task)
            allowed = {frozenset(shape) for shape in profile["fieldSets"]}
            if fields not in allowed:
                raise TaskShapeError(f"{path}: unreviewed {tag} field set {sorted(fields)}")
            for field, value in task.items():
                expected = profile["fieldKinds"].get(field)
                if expected is None or not json_kind_matches(value, expected):
                    raise TaskShapeError(f"{path}: {tag}.{field} expected {expected}, actual {type(value).__name__}")
            selected += 1
            child_field = profile.get("taskListField")
            if child_field is not None and child_field not in task:
                raise TaskShapeError(f"{path}: reviewed task list field {child_field} absent")
            if "nestedBehaviorTag" in profile:
                wrapper = profile["nestedBehaviorTag"]
                behavior = task["behavior"]
                if set(behavior) != set(wrapper["behaviorFields"]):
                    raise TaskShapeError(f"{path}: behavior wrapper fields differ")
                tag_row = behavior["tag"]
                if not isinstance(tag_row, dict) or set(tag_row) != set(wrapper["tagFields"]):
                    raise TaskShapeError(f"{path}: behavior.tag fields differ")
                tag_id = tag_row["tagId"]
                if not json_kind_matches(tag_id, wrapper["tagIdKind"]):
                    raise TaskShapeError(f"{path}: behavior.tag.tagId expected integer")
                behavior_tags[tag_id] += 1
        for field, value in task.items():
            if not isinstance(value, list):
                continue
            typed = [isinstance(item, dict) and "$type" in item for item in value]
            if field == child_field:
                if not all(typed):
                    raise TaskShapeError(f"{path}: {field} contains a non-task child")
                typed_children += len(value)
                for index, item in enumerate(value):
                    visit(item, f"{path}.{field}[{index}]", depth + 1)
            elif any(typed):
                raise TaskShapeError(f"{path}: unreviewed typed child array {field}")

    for index, node in enumerate(document["nodes"]):
        for field in ("_action", "_condition"):
            if field in node:
                visit(node[field], f"{label} node[{index}].{field}", 0)
    return {"taskCount": sum(counts.values()), "selectedTaskCount": selected,
            "unreviewedTaskCount": sum(counts.values()) - selected,
            "typedChildCount": typed_children, "maxDepth": max_depth,
            "typeCounts": dict(sorted(counts.items())),
            "behaviorTagIds": dict(sorted(behavior_tags.items()))}
