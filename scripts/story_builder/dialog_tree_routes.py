"""Recover DialogTree routes from serialized runtime graphs.

The installed client does not require one outgoing connection per normal
option.  ``NormalOptionData.index`` is the physical index passed through the
normal-option handler to ``DialogTree.Continue``; an omitted managed ``Int32``
is zero under the validated FullSerializer contract.  Extra-option nodes are
ordinary entries in the outgoing connection list, so authored normal-option
indexes already account for their position.

Finish endpoints use the same node identities, physical connections, and
managed-value defaults as normal options.  Keeping both algorithms here makes
that shared serialized routing contract explicit without coupling it to file
paths, report generation, or other I/O.

This module deliberately has no dialog-id exceptions, filename heuristics,
layout-coordinate fallbacks, OCR input, or manual overrides.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
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
    failure_class: str,
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
                "failureClass": failure_class,
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
    node_ordinal_by_id: dict[str, int] = {}
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
                    failure_class="unreferenced_option_definition",
                )
                counts["unrecoverableOptionNodes"] += 1
                counts["unreferencedOptionDefinitionNodes"] += 1
                counts["rejectedNormalOptionRoutes"] += len(routes)
                counts["unrecoverableNormalOptionRoutes"] += len(routes)
                counts["unreferencedOptionDefinitionRoutes"] += len(routes)
                unrecoverable_node_rows.append(
                    {
                        "nodeId": None,
                        "nodeOrdinal": ordinal,
                        "routingClass": "unreferenced_option_definition",
                        "serializedReferenceIdentity": False,
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
                    failure_class="ambiguous_node_identity",
                )
                counts["unrecoverableOptionNodes"] += 1
                counts["rejectedNormalOptionRoutes"] += len(routes)
                counts["unrecoverableNormalOptionRoutes"] += len(routes)
                unrecoverable_node_rows.append(
                    {
                        "nodeId": node_id,
                        "nodeOrdinal": ordinal,
                        "routingClass": "ambiguous_node_identity",
                        "serializedReferenceIdentity": True,
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
        node_ordinal_by_id[node_id] = ordinal

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    incoming_by_target: Counter[str] = Counter()
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
        incoming_by_target[target_id] += 1

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
        incoming_count = incoming_by_target.get(node_id, 0)
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
                route["failureClass"] = "invalid_normal_option_shape"
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
                route["failureClass"] = "missing_normal_option_identity"
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
                route["failureClass"] = "invalid_serialized_connection_index"
                node_issues.append(issue)
                routes.append(route)
                counts["rejectedNormalOptionRoutes"] += 1
                continue
            if connection_index < 0 or connection_index >= len(outgoing):
                failure_class = (
                    "linked_option_node_without_outgoing_connections"
                    if not outgoing
                    else "serialized_connection_index_out_of_bounds"
                )
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
                route["failureClass"] = failure_class
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
        rejected_route_count = sum(
            route.get("status") != "validated" for route in routes
        )
        out_of_bounds_route_count = sum(
            route.get("failureClass")
            == "serialized_connection_index_out_of_bounds"
            for route in routes
        )
        if not outgoing and option_rows:
            routing_class = "linked_option_node_without_outgoing_connections"
            counts["linkedOptionNodesWithoutOutgoingConnections"] += 1
            counts["linkedNormalOptionsWithoutOutgoingConnections"] += len(
                option_rows
            )
        elif rejected_route_count:
            routing_class = "linked_option_node_with_partial_index_coverage"
            counts["linkedOptionNodesWithPartialIndexCoverage"] += 1
            counts["serializedConnectionIndexesOutOfBounds"] += (
                out_of_bounds_route_count
            )
        elif len(option_rows) != len(outgoing):
            routing_class = "unequal_count_node_with_exact_index_coverage"
        else:
            routing_class = "exact_index_coverage"
        node_rows.append(
            {
                "nodeId": node_id,
                "nodeOrdinal": node_ordinal_by_id[node_id],
                "routingClass": routing_class,
                "serializedReferenceIdentity": True,
                "incomingConnectionCount": incoming_count,
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


def recover_dialog_tree_finish_endpoints(
    nodes: Iterable[Any],
    connections: Iterable[Any],
    *,
    runtime_defaults: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return every exact finish node with a validated prime-node path.

    Invalid or detached finish definitions remain in ``endpoints`` as rejected
    diagnostics.  A caller may publish an endpoint only when its status is
    ``validated``; an incoming edge, node-array position, or matching finish
    number alone is deliberately insufficient.
    """
    node_rows = list(nodes)
    connection_rows = list(connections)
    issues: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    node_by_id: dict[str, dict[str, Any]] = {}
    duplicate_node_ids: set[str] = set()

    for ordinal, node in enumerate(node_rows):
        if not isinstance(node, dict):
            issues.append(
                {
                    "gate": "nodeShape",
                    "nodeOrdinal": ordinal,
                    "expected": "object",
                    "actual": type(node).__name__,
                }
            )
            continue
        node_id = str(node.get("$id") or "")
        if not node_id:
            continue
        if node_id in node_by_id:
            duplicate_node_ids.add(node_id)
            issues.append(
                {
                    "gate": "uniqueNodeId",
                    "nodeId": node_id,
                    "expected": "one serialized node",
                    "actual": "duplicate",
                }
            )
            continue
        node_by_id[node_id] = node

    prime_node_id = ""
    if node_rows and isinstance(node_rows[0], dict):
        prime_node_id = str(node_rows[0].get("$id") or "")
    if not prime_node_id or prime_node_id not in node_by_id:
        issues.append(
            {
                "gate": "primeNodeIdentity",
                "nodeOrdinal": 0 if node_rows else None,
                "expected": "nodes[0] with unique serialized $id",
                "actual": prime_node_id or "missing",
            }
        )

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    sources_by_target: dict[str, list[str]] = defaultdict(list)
    edge_by_pair: dict[tuple[str, str], dict[str, Any]] = {}
    connection_graph_valid = True
    for ordinal, connection in enumerate(connection_rows):
        if (
            not isinstance(connection, dict)
            or short_type(connection.get("$type")) != "DialogTreeConnection"
        ):
            connection_graph_valid = False
            issues.append(
                {
                    "gate": "connectionShape",
                    "connectionOrdinal": ordinal,
                    "expected": "DialogTreeConnection object",
                    "actual": type(connection).__name__,
                }
            )
            continue
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = (
            str(source.get("$ref") or "") if isinstance(source, dict) else ""
        )
        target_id = (
            str(target.get("$ref") or "") if isinstance(target, dict) else ""
        )
        if (
            not source_id
            or not target_id
            or source_id not in node_by_id
            or target_id not in node_by_id
            or source_id in duplicate_node_ids
            or target_id in duplicate_node_ids
        ):
            connection_graph_valid = False
            issues.append(
                {
                    "gate": "connectionReference",
                    "connectionOrdinal": ordinal,
                    "expected": "two unique serialized node identities",
                    "actual": {"sourceNodeId": source_id, "targetNodeId": target_id},
                }
            )
            continue
        targets_by_source[source_id].append(target_id)
        sources_by_target[target_id].append(source_id)
        edge_by_pair.setdefault(
            (source_id, target_id),
            {
                "connectionOrdinal": ordinal,
                "sourceNodeId": source_id,
                "targetNodeId": target_id,
            },
        )

    prime_paths: dict[str, list[str]] = {}
    if prime_node_id and connection_graph_valid:
        prime_paths[prime_node_id] = [prime_node_id]
        pending = deque([prime_node_id])
        while pending:
            source_id = pending.popleft()
            for target_id in targets_by_source.get(source_id, []):
                if target_id in prime_paths:
                    continue
                prime_paths[target_id] = [*prime_paths[source_id], target_id]
                pending.append(target_id)

    endpoints: list[dict[str, Any]] = []
    for ordinal, node in enumerate(node_rows):
        if (
            not isinstance(node, dict)
            or short_type(node.get("$type")) != "DialogTreeFinishNode"
        ):
            continue
        counts["authoredFinishNodes"] += 1
        node_id = str(node.get("$id") or "")
        endpoint: dict[str, Any] = {
            "nodeId": node_id or None,
            "nodeOrdinal": ordinal,
            "status": "rejected",
            "evidenceKind": "prime_reachable_serialized_finish_endpoint",
        }
        if not node_id:
            endpoint["failureClass"] = "unreferenced_finish_definition"
            endpoint["issue"] = {
                "gate": "finishNodeIdentity",
                "nodeOrdinal": ordinal,
                "expected": "serialized $id",
                "actual": "missing",
            }
            counts["unreferencedFinishDefinitions"] += 1
            counts["rejectedFinishEndpoints"] += 1
            endpoints.append(endpoint)
            continue
        if node_id in duplicate_node_ids:
            endpoint["failureClass"] = "ambiguous_finish_node_identity"
            endpoint["issue"] = {
                "gate": "finishNodeIdentity",
                "nodeId": node_id,
                "expected": "unique serialized $id",
                "actual": "duplicate",
            }
            counts["ambiguousFinishNodeIdentities"] += 1
            counts["rejectedFinishEndpoints"] += 1
            endpoints.append(endpoint)
            continue

        finish_id, finish_id_source = resolve_serialized_field(
            node,
            "finishId",
            "System.Int32",
            runtime_defaults=runtime_defaults,
        )
        endpoint.update(
            {
                "finishId": finish_id,
                "finishIdSource": finish_id_source,
                "primeNodeId": prime_node_id or None,
                "incomingConnectionCount": len(sources_by_target.get(node_id, [])),
                "predecessorNodeIds": list(sources_by_target.get(node_id, [])),
                "predecessorNodeTypes": [
                    short_type(node_by_id[source_id].get("$type"))
                    for source_id in sources_by_target.get(node_id, [])
                ],
            }
        )
        if finish_id_source in {
            "invalid_serialized_value",
            "missing_without_validated_default",
        }:
            endpoint["failureClass"] = "invalid_serialized_finish_id"
            endpoint["issue"] = {
                "gate": "serializedFinishId",
                "nodeId": node_id,
                "expected": "authored Int32 or validated managed default",
                "actual": finish_id_source,
            }
            counts["invalidFinishIds"] += 1
            counts["rejectedFinishEndpoints"] += 1
            endpoints.append(endpoint)
            continue
        if not connection_graph_valid or not prime_node_id:
            endpoint["failureClass"] = "invalid_finish_connection_graph"
            endpoint["issue"] = {
                "gate": "finishPrimeReachability",
                "nodeId": node_id,
                "expected": "valid serialized graph with prime node",
                "actual": "invalid_graph",
            }
            counts["rejectedFinishEndpoints"] += 1
            endpoints.append(endpoint)
            continue

        node_path = prime_paths.get(node_id, [])
        if not node_path:
            endpoint["failureClass"] = "finish_node_not_reachable_from_prime"
            endpoint["issue"] = {
                "gate": "finishPrimeReachability",
                "nodeId": node_id,
                "expected": {"primeNodeId": prime_node_id, "reachable": True},
                "actual": {"reachable": False},
            }
            counts["unreachableFinishNodes"] += 1
            counts["rejectedFinishEndpoints"] += 1
            endpoints.append(endpoint)
            continue

        endpoint.update(
            {
                "status": "validated",
                "reachableFromPrimeNode": True,
                "nodePath": node_path,
                "connectionPath": [
                    edge_by_pair[(source_id, target_id)]
                    for source_id, target_id in zip(node_path, node_path[1:])
                ],
            }
        )
        counts["validatedFinishEndpoints"] += 1
        if finish_id_source == "serialized_explicit":
            counts["explicitFinishIds"] += 1
        elif finish_id_source == "runtime_default":
            counts["runtimeDefaultFinishIds"] += 1
        endpoints.append(endpoint)

    issues.extend(endpoint["issue"] for endpoint in endpoints if endpoint.get("issue"))
    return {
        "schemaVersion": "dialogTreeFinishEndpoints.v1",
        "evidencePolicy": (
            "Only finish nodes reachable from serialized nodes[0] through exact "
            "DialogTreeConnection references are accepted. finishId uses an "
            "authored Int32 or the validated managed-value default; filenames, "
            "node layout, OCR, and overrides are not read."
        ),
        "primeNodeId": prime_node_id or None,
        "counts": dict(sorted(counts.items())),
        "endpoints": endpoints,
        "issues": issues,
    }
