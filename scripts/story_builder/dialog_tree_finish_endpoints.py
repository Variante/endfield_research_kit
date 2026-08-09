"""Recover prime-reachable DialogTree finish endpoints from serialized graphs.

The installed client starts a fresh DialogTree at ``Graph.primeNode`` (the
first serialized node) and ``DialogTreeFinishNode.DoExecute`` forwards its
serialized ``finishId`` to ``DialogManager.FinishDialog``.  This module keeps
that recovery structural and reusable: it never reads dialog names, filename
suffixes, editor coordinates, OCR, or manual overrides.
"""
from __future__ import annotations

from collections import Counter, defaultdict, deque
from typing import Any, Iterable

from .dialog_tree_option_routes import resolve_serialized_field, short_type


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
    node_ordinal_by_id: dict[str, int] = {}
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
        node_ordinal_by_id[node_id] = ordinal

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
        if not isinstance(node, dict) or short_type(node.get("$type")) != "DialogTreeFinishNode":
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

    issues.extend(
        endpoint["issue"]
        for endpoint in endpoints
        if endpoint.get("issue")
    )
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
