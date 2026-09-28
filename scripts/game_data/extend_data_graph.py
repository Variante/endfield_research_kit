"""Fail-closed structural reader for decoded ExtendData NodeCanvas graphs.

This validates the named JSON root, node and connection representation. Task
payloads, blackboard contents and canvas metadata remain opaque JSON; no
runtime execution or graph-owner inference follows from the stored shape.

The reviewed contract ``extend_data_graph_schema.json`` closes the named
NodeCanvas root, the observed node-type/field-set combinations, and
``BTConnection`` source/target ``$ref`` objects, and requires every edge to
reference a unique present node ID. Nodes without ``$id`` stay stored but
cannot be edge targets. A node type name does not establish execution.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Any

from scripts.game_data.contracts import CONTRACTS_DIR


SCHEMA = "endfield.extend-data-graph-shape.v1"
CONTRACT_PATH = CONTRACTS_DIR / "extend_data_graph_schema.json"
DECIMAL_ID = re.compile(r"[0-9]+\Z")


class GraphShapeError(ValueError):
    """A decoded graph differs from the reviewed structural contract."""


@lru_cache(maxsize=1)
def load_contract() -> dict[str, Any]:
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    if contract.get("schema") != SCHEMA or contract.get("status") != "reviewed-structural-only":
        raise GraphShapeError("unsupported ExtendData graph contract")
    return contract


def _require(condition: bool, label: str, detail: str) -> None:
    if not condition:
        raise GraphShapeError(f"{label}: {detail}")


def json_kind_matches(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "number":
        return (isinstance(value, int) and not isinstance(value, bool)) or (
            isinstance(value, float) and math.isfinite(value)
        )
    raise GraphShapeError(f"unsupported contract field kind {expected}")


def validate_graph(document: Any, *, label: str,
                   contract: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a structural receipt for one decoded JSON object."""
    contract = contract or load_contract()
    root = contract["root"]
    _require(isinstance(document, dict), label, "root must be an object")
    _require(set(document) == set(root["fields"]), label,
             f"root fields expected={root['fields']} actual={sorted(document)}")
    _require(document["type"] == root["type"], label,
             f"root type expected={root['type']} actual={document['type']!r}")
    for field in ("nodes", "connections", "canvasGroups", "m_allParameters"):
        _require(isinstance(document[field], list), label, f"{field} must be an array")
    derived = document["derivedData"]
    _require(isinstance(derived, dict) and set(derived) == set(root["derivedDataFields"]),
             label, "derivedData fields differ")
    _require(derived["$type"] == root["derivedDataType"] and isinstance(derived["repeat"], bool),
             label, "derivedData type/repeat differs")
    board = document["localBlackboard"]
    _require(isinstance(board, dict) and set(board) == set(root["localBlackboardFields"])
             and isinstance(board["_variables"], dict), label, "localBlackboard shape differs")

    node_contract = contract["node"]
    allowed = {row["type"]: {frozenset(fields) for fields in row["fieldSets"]}
               for row in node_contract["types"]}
    ids: set[str] = set()
    shape_counts: Counter[tuple[str, tuple[str, ...]]] = Counter()
    idless = 0
    for index, node in enumerate(document["nodes"]):
        node_label = f"{label} node[{index}]"
        _require(isinstance(node, dict), node_label, "node must be an object")
        tag = node.get("$type")
        _require(isinstance(tag, str) and tag in allowed, node_label, f"unknown node type {tag!r}")
        fields = frozenset(node)
        _require(fields in allowed[tag], node_label,
                 f"unreviewed field set for {tag}: {sorted(fields)}")
        for field, value in node.items():
            expected = node_contract["fieldKinds"].get(field)
            _require(expected is not None and json_kind_matches(value, expected), node_label,
                     f"{field} expected {expected}, actual {type(value).__name__}")
        position = node["_position"]
        _require(1 <= len(position) <= 2 and set(position) <= set(node_contract["positionFields"])
                 and all(json_kind_matches(value, "number") for value in position.values()),
                 node_label, "_position must contain finite x/y coordinates")
        for task_field in ("_action", "_condition"):
            if task_field in node:
                _require(isinstance(node[task_field].get("$type"), str), node_label,
                         f"{task_field} has no task $type")
        identifier = node.get("$id")
        if identifier is None:
            idless += 1
        else:
            _require(DECIMAL_ID.fullmatch(identifier) is not None, node_label,
                     f"nondecimal $id {identifier!r}")
            _require(identifier not in ids, node_label, f"duplicate $id {identifier}")
            ids.add(identifier)
        shape_counts[(tag, tuple(sorted(fields)))] += 1

    edge = contract["connection"]
    edge_shapes = {frozenset(fields) for fields in edge["fieldSets"]}
    disabled = 0
    for index, connection in enumerate(document["connections"]):
        edge_label = f"{label} connection[{index}]"
        _require(isinstance(connection, dict), edge_label, "connection must be an object")
        _require(frozenset(connection) in edge_shapes, edge_label,
                 f"unreviewed field set {sorted(connection)}")
        _require(connection["$type"] == edge["type"], edge_label,
                 f"unknown connection type {connection['$type']!r}")
        for field in edge["referenceFields"]:
            reference = connection[field]
            _require(isinstance(reference, dict) and set(reference) == set(edge["referenceShape"]),
                     edge_label, f"{field} must be a $ref object")
            _require(isinstance(reference["$ref"], str) and reference["$ref"] in ids,
                     edge_label, f"{field} unresolved $ref {reference['$ref']!r}")
        if edge["disabledField"] in connection:
            _require(isinstance(connection[edge["disabledField"]], bool),
                     edge_label, "_isDisabled must be boolean")
            disabled += 1
    return {"nodeCount": len(document["nodes"]), "connectionCount": len(document["connections"]),
            "idlessNodeCount": idless, "disabledConnectionCount": disabled,
            "canvasGroupCount": len(document["canvasGroups"]),
            "blackboardVariableCount": len(board["_variables"]),
            "nodeShapes": [{"type": tag, "fields": list(fields), "count": count}
                           for (tag, fields), count in sorted(shape_counts.items())]}
