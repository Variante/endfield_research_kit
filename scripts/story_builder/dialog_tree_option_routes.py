"""Recover DialogTree normal-option routes from serialized runtime indexes.

The installed client does not require one outgoing connection per normal
option.  ``NormalOptionData.index`` is the physical index passed through the
normal-option handler to ``DialogTree.Continue``; an omitted managed ``Int32``
is zero under the validated FullSerializer contract.  Extra-option nodes are
ordinary entries in the outgoing connection list, so authored normal-option
indexes already account for their position.

Keep this module data-driven.  It deliberately has no dialog-id exceptions,
filename heuristics, layout-coordinate fallbacks, OCR input, or manual
overrides.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Iterable


DIALOG_TREE_RUNTIME_DEFAULTS: dict[str, Any] = {
    "status": "validated",
    "scope": "FullSerializer reflected fields omitted from authored JSON",
    "managedValueTypeDefaults": {
        "System.Int32": 0,
        "System.Boolean": False,
    },
}


def short_type(value: Any) -> str:
    text = str(value or "").split(",", 1)[0]
    return text.rsplit(".", 1)[-1]


def resolve_serialized_field(
    record: dict[str, Any],
    field_name: str,
    managed_type: str,
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> tuple[Any | None, str]:
    """Resolve one reflected field without inventing object-specific values."""
    if field_name in record:
        value = record[field_name]
        if managed_type == "System.Int32" and type(value) is int:
            return value, "serialized_explicit"
        if managed_type == "System.Boolean" and type(value) is bool:
            return value, "serialized_explicit"
        return None, "invalid_serialized_value"
    defaults = runtime_defaults or {}
    values = defaults.get("managedValueTypeDefaults") or {}
    if defaults.get("status") == "validated" and managed_type in values:
        value = values[managed_type]
        if managed_type == "System.Int32" and type(value) is int:
            return value, "runtime_default"
        if managed_type == "System.Boolean" and type(value) is bool:
            return value, "runtime_default"
    return None, "missing_without_validated_default"


def _unrecoverable_option_routes(
    option_rows: Any,
    *,
    node_id: str,
    node_ordinal: int,
    issue: dict[str, Any],
) -> list[dict[str, Any]]:
    """Retain every option under a node whose graph identity is unusable."""
    if not isinstance(option_rows, list):
        return []
    routes: list[dict[str, Any]] = []
    for option_ordinal, option in enumerate(option_rows):
        option_id = (
            str(option.get("_optionId") or "").strip()
            if isinstance(option, dict)
            else ""
        )
        routes.append(
            {
                "nodeId": node_id or None,
                "nodeOrdinal": node_ordinal,
                "optionOrdinal": option_ordinal,
                "optionId": option_id,
                "status": "rejected",
                "evidenceKind": "normal_option_serialized_connection_index",
                "issue": {
                    **issue,
                    "optionOrdinal": option_ordinal,
                    "optionId": option_id,
                },
            }
        )
    return routes


def recover_dialog_tree_option_routes(
    nodes: Iterable[Any],
    connections: Iterable[Any],
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map every normal option to its exact serialized connection index.

    Results retain invalid authored options as bounded diagnostics.  A valid
    option route is never inferred from option-list order, connection count,
    duplicate targets, node coordinates, or nearby graph structure.
    """
    defaults = runtime_defaults or {}
    node_by_id: dict[str, dict[str, Any]] = {}
    issues: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    unrecoverable_node_rows: list[dict[str, Any]] = []
    for ordinal, node in enumerate(nodes):
        if not isinstance(node, dict):
            issues.append(
                {
                    "gate": "nodeShape",
                    "nodeOrdinal": ordinal,
                    "actual": type(node).__name__,
                }
            )
            continue
        is_option_node = short_type(node.get("$type")) == "DialogTreeOptionNode"
        option_rows = node.get("_normalOptions")
        if is_option_node:
            counts["authoredOptionNodes"] += 1
            if isinstance(option_rows, list):
                counts["authoredNormalOptions"] += len(option_rows)
        node_id = str(node.get("$id") or "")
        if not node_id:
            issue = {"gate": "nodeIdentity", "nodeOrdinal": ordinal}
            issues.append(issue)
            if is_option_node:
                routes = _unrecoverable_option_routes(
                    option_rows,
                    node_id=node_id,
                    node_ordinal=ordinal,
                    issue=issue,
                )
                counts["unrecoverableOptionNodes"] += 1
                counts["rejectedNormalOptionRoutes"] += len(routes)
                counts["unrecoverableNormalOptionRoutes"] += len(routes)
                unrecoverable_node_rows.append(
                    {
                        "nodeId": None,
                        "nodeOrdinal": ordinal,
                        "normalOptionCount": (
                            len(option_rows) if isinstance(option_rows, list) else 0
                        ),
                        "outgoingConnectionCount": None,
                        "routes": routes,
                        "issues": [issue],
                    }
                )
            continue
        if node_id in node_by_id:
            issue = {
                "gate": "uniqueNodeId",
                "nodeId": node_id,
                "nodeOrdinal": ordinal,
            }
            issues.append(issue)
            if is_option_node:
                routes = _unrecoverable_option_routes(
                    option_rows,
                    node_id=node_id,
                    node_ordinal=ordinal,
                    issue=issue,
                )
                counts["unrecoverableOptionNodes"] += 1
                counts["rejectedNormalOptionRoutes"] += len(routes)
                counts["unrecoverableNormalOptionRoutes"] += len(routes)
                unrecoverable_node_rows.append(
                    {
                        "nodeId": node_id,
                        "nodeOrdinal": ordinal,
                        "normalOptionCount": (
                            len(option_rows) if isinstance(option_rows, list) else 0
                        ),
                        "outgoingConnectionCount": None,
                        "routes": routes,
                        "issues": [issue],
                    }
                )
            continue
        node_by_id[node_id] = node

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    for ordinal, connection in enumerate(connections):
        if not isinstance(connection, dict):
            issues.append(
                {
                    "gate": "connectionShape",
                    "connectionOrdinal": ordinal,
                    "actual": type(connection).__name__,
                }
            )
            continue
        source_id = str(((connection.get("_sourceNode") or {}).get("$ref")) or "")
        target_id = str(((connection.get("_targetNode") or {}).get("$ref")) or "")
        if source_id not in node_by_id or target_id not in node_by_id:
            issues.append(
                {
                    "gate": "connectionReference",
                    "connectionOrdinal": ordinal,
                    "sourceNodeId": source_id,
                    "targetNodeId": target_id,
                }
            )
            continue
        targets_by_source[source_id].append(target_id)

    node_rows: list[dict[str, Any]] = list(unrecoverable_node_rows)
    routes_by_node_id: dict[str, list[dict[str, Any]]] = {}
    for node_id, node in node_by_id.items():
        if short_type(node.get("$type")) != "DialogTreeOptionNode":
            continue
        counts["optionNodes"] += 1
        option_rows = node.get("_normalOptions")
        if not isinstance(option_rows, list):
            issue = {
                "gate": "normalOptionList",
                "nodeId": node_id,
                "actual": type(option_rows).__name__,
            }
            issues.append(issue)
            node_rows.append({"nodeId": node_id, "routes": [], "issues": [issue]})
            routes_by_node_id[node_id] = []
            continue

        outgoing = list(targets_by_source.get(node_id, []))
        extra_indices = [
            index
            for index, target_id in enumerate(outgoing)
            if short_type((node_by_id.get(target_id) or {}).get("$type"))
            == "DialogTreeExOptionNode"
        ]
        has_extra, has_extra_source = resolve_serialized_field(
            node,
            "_hasExOption",
            "System.Boolean",
            runtime_defaults=defaults,
        )
        node_issues: list[dict[str, Any]] = []
        if has_extra_source in {
            "invalid_serialized_value",
            "missing_without_validated_default",
        }:
            node_issues.append(
                {
                    "gate": "hasExtraOptionValue",
                    "nodeId": node_id,
                    "actual": has_extra_source,
                }
            )
        elif bool(has_extra) != bool(extra_indices):
            node_issues.append(
                {
                    "gate": "extraOptionFlagAgreement",
                    "nodeId": node_id,
                    "expected": bool(has_extra),
                    "actual": bool(extra_indices),
                    "extraOptionConnectionIndices": extra_indices,
                }
            )
        if len(extra_indices) > 1:
            node_issues.append(
                {
                    "gate": "extraOptionConnectionMultiplicity",
                    "nodeId": node_id,
                    "expected": "at most one",
                    "actual": len(extra_indices),
                    "extraOptionConnectionIndices": extra_indices,
                }
            )

        routes: list[dict[str, Any]] = []
        referenced_indices: set[int] = set()
        for option_ordinal, option in enumerate(option_rows):
            counts["normalOptions"] += 1
            route: dict[str, Any] = {
                "nodeId": node_id,
                "optionOrdinal": option_ordinal,
                "status": "rejected",
                "evidenceKind": "normal_option_serialized_connection_index",
            }
            if not isinstance(option, dict):
                issue = {
                    "gate": "normalOptionShape",
                    "nodeId": node_id,
                    "optionOrdinal": option_ordinal,
                    "actual": type(option).__name__,
                }
                route["issue"] = issue
                node_issues.append(issue)
                routes.append(route)
                counts["rejectedNormalOptionRoutes"] += 1
                continue
            option_id = str(option.get("_optionId") or "").strip()
            route["optionId"] = option_id
            if not option_id:
                issue = {
                    "gate": "normalOptionIdentity",
                    "nodeId": node_id,
                    "optionOrdinal": option_ordinal,
                }
                route["issue"] = issue
                node_issues.append(issue)
                routes.append(route)
                counts["rejectedNormalOptionRoutes"] += 1
                continue
            connection_index, index_source = resolve_serialized_field(
                option,
                "index",
                "System.Int32",
                runtime_defaults=defaults,
            )
            route["connectionIndex"] = connection_index
            route["connectionIndexSource"] = index_source
            if index_source in {
                "invalid_serialized_value",
                "missing_without_validated_default",
            }:
                issue = {
                    "gate": "normalOptionConnectionIndexValue",
                    "nodeId": node_id,
                    "optionOrdinal": option_ordinal,
                    "optionId": option_id,
                    "actual": index_source,
                }
                route["issue"] = issue
                node_issues.append(issue)
                routes.append(route)
                counts["rejectedNormalOptionRoutes"] += 1
                continue
            if connection_index < 0 or connection_index >= len(outgoing):
                issue = {
                    "gate": "normalOptionConnectionIndexBounds",
                    "nodeId": node_id,
                    "optionOrdinal": option_ordinal,
                    "optionId": option_id,
                    "expected": {
                        "minimum": 0,
                        "maximumExclusive": len(outgoing),
                    },
                    "actual": connection_index,
                }
                route["issue"] = issue
                node_issues.append(issue)
                routes.append(route)
                counts["rejectedNormalOptionRoutes"] += 1
                continue
            target_id = outgoing[connection_index]
            target_type = short_type((node_by_id.get(target_id) or {}).get("$type"))
            route.update(
                {
                    "status": "validated",
                    "targetNodeId": target_id,
                    "targetNodeType": target_type,
                }
            )
            if connection_index in extra_indices:
                route["warning"] = "normal_option_targets_extra_option_node"
                counts["normalOptionRoutesToExtraOption"] += 1
            referenced_indices.add(connection_index)
            routes.append(route)
            counts["validatedNormalOptionRoutes"] += 1
            if index_source == "runtime_default":
                counts["runtimeDefaultConnectionIndexes"] += 1
            else:
                counts["explicitConnectionIndexes"] += 1

        issues.extend(node_issues)
        routes_by_node_id[node_id] = routes
        unmapped_indices = sorted(set(range(len(outgoing))) - referenced_indices)
        node_rows.append(
            {
                "nodeId": node_id,
                "normalOptionCount": len(option_rows),
                "outgoingConnectionCount": len(outgoing),
                "hasExtraOption": has_extra,
                "hasExtraOptionSource": has_extra_source,
                "extraOptionConnectionIndices": extra_indices,
                "unmappedConnectionIndices": unmapped_indices,
                "routes": routes,
                "issues": node_issues,
            }
        )
        if len(option_rows) != len(outgoing):
            counts["connectionCountMismatchNodes"] += 1
        if extra_indices:
            counts["extraOptionNodes"] += 1
        if node_issues:
            counts["nodesWithRouteIssues"] += 1

    return {
        "schemaVersion": "dialogTreeNormalOptionRoutes.v1",
        "evidencePolicy": (
            "NormalOptionData.index selects the physical outgoing connection. "
            "Missing managed Int32 fields use zero only under the validated "
            "FullSerializer default contract. OCR, overrides, names, suffixes, "
            "coordinates, and connection-count guesses are not read."
        ),
        "counts": dict(sorted(counts.items())),
        "nodes": node_rows,
        "routesByNodeId": routes_by_node_id,
        "issues": issues,
    }
