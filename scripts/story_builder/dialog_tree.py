from __future__ import annotations

from .context import *
from .anime_assets import *
from .scene_graph import *
from .level_bindings import *
from .mission_flow import *

def _dialog_tree_scene_prefix(value: str) -> str | None:
    if not isinstance(value, str):
        return None
    match = re.search(r"_(\d+)$", value)
    if not match:
        return None
    prefix = value[:match.start()]
    if prefix.startswith(("dlg_", "env_", "misc_", "sns_")):
        return prefix
    return None


def _dialog_tree_option_prefix(option_id: str) -> str | None:
    if not isinstance(option_id, str) or not option_id.startswith("option_"):
        return None
    stem = option_id[len("option_") :]
    match = re.match(rf"(.+)_({SCENE_TOK})_(\d+)$", stem)
    if not match:
        return None
    prefix = match.group(1)
    if prefix.startswith(("dlg_", "env_", "misc_", "sns_")):
        return prefix
    return None


def _dialog_tree_node_position(node: dict, fallback_index: int = 0) -> tuple[float, float, int]:
    pos = node.get("_position") or {}
    try:
        x = float(pos.get("x", 0.0))
    except (TypeError, ValueError):
        x = 0.0
    try:
        y = float(pos.get("y", 0.0))
    except (TypeError, ValueError):
        y = 0.0
    return (x, y, fallback_index)


def _dialog_tree_node_line_id(node: dict) -> str:
    return _first_string_field(node, "_trunkId") or ""


def _dialog_tree_node_option_ids(node: dict) -> list[str]:
    option_ids: list[str] = []
    for entry in node.get("_normalOptions") or []:
        if not isinstance(entry, dict):
            continue
        option_id = str(entry.get("_optionId") or "").strip()
        if option_id and option_id not in option_ids:
            option_ids.append(option_id)
    return option_ids


def _dialog_tree_connection_refs(conn: dict) -> tuple[str, str]:
    if not isinstance(conn, dict):
        return ("", "")
    src = (conn.get("_sourceNode") or {}).get("$ref")
    dst = (conn.get("_targetNode") or {}).get("$ref")
    return (str(src or ""), str(dst or ""))


def _normalize_dialog_tree_line_graph(nodes: list[dict], conns: list[dict]) -> dict:
    graph_nodes: list[dict] = []
    by_id: dict[str, dict] = {}
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("$id") or "").strip()
        if not node_id:
            continue
        x, y, _ = _dialog_tree_node_position(node, idx)
        record = {
            "id": node_id,
            "type": _node_short_type(node),
            "x": round(x, 4),
            "y": round(y, 4),
        }
        if line_id := _dialog_tree_node_line_id(node):
            record["lineId"] = line_id
        if option_ids := _dialog_tree_node_option_ids(node):
            record["optionIds"] = option_ids
        graph_nodes.append(record)
        by_id[node_id] = record

    graph_edges: list[dict] = []
    edge_by_pair: dict[tuple[str, str], dict] = {}
    for conn in conns:
        src, dst = _dialog_tree_connection_refs(conn)
        if not src or not dst or src not in by_id or dst not in by_id:
            continue
        key = (src, dst)
        edge = edge_by_pair.get(key)
        if edge is None:
            edge = {
                "from": src,
                "to": dst,
            }
            if from_line := by_id[src].get("lineId"):
                edge["fromLineId"] = from_line
            if to_line := by_id[dst].get("lineId"):
                edge["toLineId"] = to_line
            edge_by_pair[key] = edge
            graph_edges.append(edge)
        else:
            edge["count"] = int(edge.get("count") or 1) + 1

    return {
        "nodes": graph_nodes,
        "edges": graph_edges,
    }


def verify_dialog_tree_reconstruction(payload: dict) -> list[dict]:
    """Check reconstructed option anchors and routes against raw graph edges."""
    if not isinstance(payload, dict):
        return [{
            "code": "invalidPayload",
            "message": "DialogTree reconstruction payload is not an object.",
        }]

    graph = payload.get("lineGraph") or {}
    if not isinstance(graph, dict):
        return [{
            "code": "missingLineGraph",
            "message": "DialogTree reconstruction payload has no lineGraph object.",
        }]

    raw_sources: list[dict] = []
    if graph.get("nodes") or graph.get("edges"):
        raw_sources.append({
            "sourceKey": payload.get("sourceKey") or payload.get("key") or "",
            "file": payload.get("file") or "",
            "nodes": graph.get("nodes") or [],
            "edges": graph.get("edges") or [],
        })
    raw_sources.extend(source for source in (graph.get("sources") or []) if isinstance(source, dict))

    def build_graph_index(source: dict, source_index: int) -> dict:
        nodes = [node for node in (source.get("nodes") or []) if isinstance(node, dict)]
        edges = [edge for edge in (source.get("edges") or []) if isinstance(edge, dict)]
        node_by_id = {str(node.get("id")): node for node in nodes if node.get("id") is not None}
        edge_pairs = {
            (str(edge.get("from") or ""), str(edge.get("to") or ""))
            for edge in edges
            if edge.get("from") is not None and edge.get("to") is not None
        }
        succs: dict[str, list[str]] = defaultdict(list)
        for left, right in edge_pairs:
            if left and right:
                succs[left].append(right)
        line_nodes: dict[str, list[str]] = defaultdict(list)
        option_nodes: dict[str, list[str]] = defaultdict(list)
        for node_id, node in node_by_id.items():
            if line_id := str(node.get("lineId") or ""):
                line_nodes[line_id].append(node_id)
            for option_id in node.get("optionIds") or []:
                if option_id:
                    option_nodes[str(option_id)].append(node_id)
        return {
            "sourceIndex": source_index,
            "sourceKey": str(source.get("sourceKey") or ""),
            "file": str(source.get("file") or ""),
            "nodeById": node_by_id,
            "edgePairs": edge_pairs,
            "succs": succs,
            "lineNodes": line_nodes,
            "optionNodes": option_nodes,
        }

    indexes = [
        index
        for idx, source in enumerate(raw_sources)
        if (index := build_graph_index(source, idx))["nodeById"] or index["edgePairs"]
    ]
    if not indexes:
        return []

    issues: list[dict] = []

    def add_issue(code: str, message: str, **extra: object) -> None:
        issue = {"code": code, "message": message}
        issue.update({key: value for key, value in extra.items() if value not in (None, "", [])})
        issues.append(issue)

    def graph_context(index: dict) -> dict:
        return {
            "graphSourceKey": index.get("sourceKey"),
            "graphFile": index.get("file"),
            "graphSourceIndex": index.get("sourceIndex"),
        }

    def anchor_path_exists(index: dict, after_line_id: str, option_node_id: str) -> bool:
        line_nodes = index["lineNodes"]
        node_by_id = index["nodeById"]
        succs = index["succs"]
        for line_node_id in line_nodes.get(after_line_id, []):
            seen = {line_node_id}
            queue = deque(succs.get(line_node_id, []))
            while queue:
                cur = queue.popleft()
                if cur in seen:
                    continue
                seen.add(cur)
                if cur == option_node_id:
                    return True
                node = node_by_id.get(cur) or {}
                if node.get("lineId") and node.get("lineId") != after_line_id:
                    continue
                queue.extend(succs.get(cur, []))
        return False

    def validate_option_anchor(
        option_id: str,
        after_line_id: str,
        *,
        mismatch_code: str,
        context: dict | None = None,
        candidate_indexes: list[dict] | None = None,
    ) -> None:
        option_id = str(option_id or "")
        after_line_id = str(after_line_id or "")
        if not option_id or not after_line_id:
            return
        candidates = candidate_indexes or indexes
        saw_option = False
        saw_line = False
        mismatch_details: list[dict] = []
        for index in candidates:
            matching_option_nodes = index["optionNodes"].get(option_id, [])
            matching_line_nodes = index["lineNodes"].get(after_line_id, [])
            saw_option = saw_option or bool(matching_option_nodes)
            saw_line = saw_line or bool(matching_line_nodes)
            if matching_option_nodes and matching_line_nodes:
                if any(anchor_path_exists(index, after_line_id, node_id) for node_id in matching_option_nodes):
                    return
                mismatch_details.append({
                    **graph_context(index),
                    "optionNodeIds": matching_option_nodes,
                    "lineNodeIds": matching_line_nodes,
                })
        if not saw_option:
            add_issue(
                "missingOptionNode",
                "Reconstructed option anchor references an option id absent from lineGraph nodes.",
                optionId=option_id,
                after=after_line_id,
                **(context or {}),
            )
            return
        if not saw_line:
            add_issue(
                "missingAnchorLineNode",
                "Reconstructed option anchor references a line id absent from lineGraph nodes.",
                optionId=option_id,
                after=after_line_id,
                **(context or {}),
            )
            return
        detail = mismatch_details[0] if mismatch_details else {}
        add_issue(
            mismatch_code,
            "Reconstructed option anchor is not reachable in lineGraph without crossing another trunk line.",
            optionId=option_id,
            after=after_line_id,
            **detail,
            **(context or {}),
        )

    def matching_indexes_for_link(link: dict) -> list[dict]:
        source_key = str(link.get("sourceKey") or "")
        file_name = str(link.get("file") or "")
        candidates = indexes
        if source_key:
            keyed = [index for index in candidates if index.get("sourceKey") == source_key]
            if keyed:
                candidates = keyed
        if file_name:
            filed = [index for index in candidates if index.get("file") == file_name]
            if filed:
                candidates = filed
        return candidates

    def pick_index_for_path(candidates: list[dict], source_node_id: str, path_node_ids: list[str]) -> dict | None:
        if source_node_id:
            containing_source = [
                index for index in candidates
                if source_node_id in index["nodeById"]
            ]
            if containing_source:
                candidates = containing_source
        if path_node_ids:
            complete = [
                index for index in candidates
                if all(node_id in index["nodeById"] for node_id in path_node_ids)
            ]
            if complete:
                return complete[0]
            partial = [
                index for index in candidates
                if any(node_id in index["nodeById"] for node_id in path_node_ids)
            ]
            if partial:
                return partial[0]
        return candidates[0] if candidates else None

    for option_id, after_line_id in (payload.get("after") or {}).items():
        validate_option_anchor(
            str(option_id or ""),
            str(after_line_id or ""),
            mismatch_code="anchorPathMismatch",
        )

    for group_index, group in enumerate(payload.get("optionGroups") or []):
        if not isinstance(group, dict):
            continue
        group_after = str(group.get("after") or "")
        if not group_after:
            continue
        for option in group.get("options") or []:
            if not isinstance(option, dict):
                continue
            validate_option_anchor(
                str(option.get("id") or option.get("optionId") or ""),
                group_after,
                mismatch_code="optionGroupAnchorPathMismatch",
                context={"group": group.get("g"), "groupIndex": group_index},
            )

    scene_links = payload.get("sceneLinks") or payload.get("sceneGraphLinks") or []
    for link_index, link in enumerate(scene_links):
        if not isinstance(link, dict):
            continue
        link_after = str(link.get("after") or "")
        candidate_indexes = matching_indexes_for_link(link)
        for option_index, option in enumerate(link.get("options") or []):
            if not isinstance(option, dict):
                continue
            option_id = str(option.get("optionId") or "")
            debug = option.get("_debug") or {}
            if not isinstance(debug, dict):
                debug = {}
            source_node_id = str(debug.get("sourceOptionNodeId") or "")
            path_node_ids = [str(node_id) for node_id in (debug.get("pathNodeIds") or []) if node_id is not None]
            index = pick_index_for_path(candidate_indexes, source_node_id, path_node_ids)
            if index is None:
                continue
            node_by_id = index["nodeById"]
            edge_pairs = index["edgePairs"]

            if source_node_id:
                source_node = node_by_id.get(source_node_id)
                if not source_node:
                    add_issue(
                        "missingSourceOptionNode",
                        "Scene link debug references a source option node absent from lineGraph.",
                        optionId=option_id,
                        sourceOptionNodeId=source_node_id,
                        linkIndex=link_index,
                        optionIndex=option_index,
                        **graph_context(index),
                    )
                elif option_id and option_id not in {str(value) for value in (source_node.get("optionIds") or [])}:
                    add_issue(
                        "sourceOptionNodeMismatch",
                        "Scene link option id is not present on its source option node.",
                        optionId=option_id,
                        sourceOptionNodeId=source_node_id,
                        nodeOptionIds=source_node.get("optionIds") or [],
                        linkIndex=link_index,
                        optionIndex=option_index,
                        **graph_context(index),
                    )

            if (
                link_after
                and source_node_id
                and source_node_id in node_by_id
                and not anchor_path_exists(index, link_after, source_node_id)
            ):
                add_issue(
                    "sceneLinkAnchorPathMismatch",
                    "Scene link anchor is not reachable in lineGraph without crossing another trunk line.",
                    optionId=option_id,
                    after=link_after,
                    sourceOptionNodeId=source_node_id,
                    linkIndex=link_index,
                    optionIndex=option_index,
                    **graph_context(index),
                )

            if source_node_id and path_node_ids and (source_node_id, path_node_ids[0]) not in edge_pairs:
                add_issue(
                    "optionStartEdgeMismatch",
                    "Scene link path does not start from the source option node edge.",
                    optionId=option_id,
                    sourceOptionNodeId=source_node_id,
                    startNodeId=path_node_ids[0],
                    linkIndex=link_index,
                    optionIndex=option_index,
                    **graph_context(index),
                )

            for left, right in zip(path_node_ids, path_node_ids[1:]):
                if (left, right) not in edge_pairs:
                    add_issue(
                        "pathEdgeMismatch",
                        "Scene link path contains adjacent nodes without a lineGraph edge.",
                        optionId=option_id,
                        fromNodeId=left,
                        toNodeId=right,
                        linkIndex=link_index,
                        optionIndex=option_index,
                        **graph_context(index),
                    )

            path_line_ids = _unique_preserve([
                str(node_by_id[node_id].get("lineId"))
                for node_id in path_node_ids
                if node_id in node_by_id and node_by_id[node_id].get("lineId")
            ])
            recorded_path_line_ids = [str(line_id) for line_id in (option.get("pathLineIds") or []) if line_id]
            if recorded_path_line_ids and recorded_path_line_ids != path_line_ids:
                add_issue(
                    "pathLineIdsMismatch",
                    "Scene link pathLineIds do not match the trunk nodes on the recorded path.",
                    optionId=option_id,
                    recordedPathLineIds=recorded_path_line_ids,
                    graphPathLineIds=path_line_ids,
                    linkIndex=link_index,
                    optionIndex=option_index,
                    **graph_context(index),
                )

            first_line_id = str(option.get("firstLineId") or "")
            if first_line_id and (not path_line_ids or first_line_id != path_line_ids[0]):
                add_issue(
                    "firstLineIdMismatch",
                    "Scene link firstLineId does not match the first trunk on the recorded path.",
                    optionId=option_id,
                    firstLineId=first_line_id,
                    graphFirstLineId=path_line_ids[0] if path_line_ids else "",
                    linkIndex=link_index,
                    optionIndex=option_index,
                    **graph_context(index),
                )

    return issues


def _ordered_dialog_tree_trunk_ids(nodes: list[dict], conns: list[dict]) -> tuple[list[str], dict]:
    by_id: dict[str, dict] = {}
    node_index: dict[str, int] = {}
    for idx, node in enumerate(nodes):
        node_id = node.get("$id")
        if node_id:
            by_id[node_id] = node
            node_index[node_id] = idx

    preds: dict[str, list[str]] = defaultdict(list)
    succs: dict[str, list[str]] = defaultdict(list)
    for conn in conns:
        src, dst = _dialog_tree_connection_refs(conn)
        if src in by_id and dst in by_id:
            if src not in preds[dst]:
                preds[dst].append(src)
            if dst not in succs[src]:
                succs[src].append(dst)

    ignored_duplicate_node_ids: set[str] = set()
    duplicate_line_nodes: dict[str, list[str]] = defaultdict(list)
    for node_id, node in by_id.items():
        trunk_id = _dialog_tree_node_line_id(node)
        if trunk_id:
            duplicate_line_nodes[trunk_id].append(node_id)
    for node_ids in duplicate_line_nodes.values():
        if len(node_ids) < 2:
            continue
        connected = {
            node_id
            for node_id in node_ids
            if preds.get(node_id) or succs.get(node_id)
        }
        if not connected:
            continue
        ignored_duplicate_node_ids.update(
            node_id
            for node_id in node_ids
            if node_id not in connected
        )
    if ignored_duplicate_node_ids:
        by_id = {
            node_id: node
            for node_id, node in by_id.items()
            if node_id not in ignored_duplicate_node_ids
        }
        node_index = {
            node_id: index
            for node_id, index in node_index.items()
            if node_id in by_id
        }

    def node_sort_key(node_id: str) -> tuple[float, float, int]:
        return _dialog_tree_node_position(by_id[node_id], node_index.get(node_id, 0))

    # Treat visual return edges as loop backs only when the graph also proves
    # they close a cycle. This keeps legitimate authored leftward edges, such
    # as long scenes wrapping to a lower canvas row, in the forward flow.
    back_edge_x_tolerance = 80.0
    row_wrap_y_tolerance = 120.0
    cycle_cache: dict[tuple[str, str], bool] = {}

    def edge_closes_cycle(src: str, dst: str) -> bool:
        cache_key = (src, dst)
        if cache_key in cycle_cache:
            return cycle_cache[cache_key]
        if src == dst:
            cycle_cache[cache_key] = True
            return True
        seen: set[str] = set()
        stack: list[str] = [dst]
        while stack:
            cur = stack.pop()
            if cur == src:
                cycle_cache[cache_key] = True
                return True
            if cur in seen:
                continue
            seen.add(cur)
            stack.extend(nxt for nxt in succs.get(cur, []) if nxt not in seen)
        cycle_cache[cache_key] = False
        return False

    def edge_is_visual_return(src: str, dst: str) -> bool:
        src_x, src_y, _ = node_sort_key(src)
        dst_x, dst_y, _ = node_sort_key(dst)
        if dst_y >= src_y + row_wrap_y_tolerance:
            return False
        return src_x > dst_x + back_edge_x_tolerance or dst_y < src_y - row_wrap_y_tolerance

    def is_forward_pred(pred: str, node_id: str) -> bool:
        if not edge_closes_cycle(pred, node_id):
            return True
        return not edge_is_visual_return(pred, node_id)

    def upstream_preds(node_id: str) -> list[str]:
        return [
            pred
            for pred in preds.get(node_id, [])
            if pred in by_id and is_forward_pred(pred, node_id)
        ]

    effective_preds = {node_id: upstream_preds(node_id) for node_id in by_id}
    roots = sorted(
        (node_id for node_id in by_id if not effective_preds.get(node_id)),
        key=node_sort_key,
    )

    ordered_line_ids: list[str] = []
    seen_line_ids: set[str] = set()
    visited: set[str] = set()
    # Use a stack, seeded in reverse, so authored connection order is preserved
    # at option splits and each branch is traversed as a readable block. Join
    # prerequisites above still prevent a merge from being visited before all
    # upstream branches have arrived.
    ready: list[str] = list(reversed(roots))
    queued: set[str] = set(roots)
    appended_node_ids: list[str] = []

    def visit(node_id: str) -> None:
        if node_id in visited:
            return
        visited.add(node_id)
        trunk_id = _dialog_tree_node_line_id(by_id[node_id])
        if trunk_id and trunk_id not in seen_line_ids:
            seen_line_ids.add(trunk_id)
            ordered_line_ids.append(trunk_id)
        next_nodes = [
            nxt
            for nxt in succs.get(node_id, [])
            if nxt not in visited and nxt not in queued
        ]
        for nxt in reversed(next_nodes):
            if nxt in visited or nxt in queued:
                continue
            if all(pred in visited for pred in effective_preds.get(nxt, [])):
                ready.append(nxt)
                queued.add(nxt)

    def drain_ready() -> None:
        while ready:
            node_id = ready.pop()
            queued.discard(node_id)
            if node_id in visited:
                continue
            if not all(pred in visited for pred in effective_preds.get(node_id, [])):
                continue
            visit(node_id)

    drain_ready()
    while len(visited) < len(by_id):
        remaining = sorted(
            (node_id for node_id in by_id if node_id not in visited),
            key=node_sort_key,
        )
        if not remaining:
            break
        node_id = remaining[0]
        appended_node_ids.append(node_id)
        queued.discard(node_id)
        visit(node_id)
        drain_ready()

    # Some trees include trunk-bearing nodes without a `$id`. They cannot
    # participate in graph traversal (connections can't reference them), but
    # their trunk IDs are still authored lines. Append by canvas position so
    # they land in the most plausible order.
    orphan_entries: list[tuple[tuple[float, float, int], str]] = []
    for idx, node in enumerate(nodes):
        if node.get("$id"):
            continue
        trunk_id = _dialog_tree_node_line_id(node)
        if not trunk_id or trunk_id in seen_line_ids:
            continue
        orphan_entries.append((_dialog_tree_node_position(node, idx), trunk_id))
    orphan_entries.sort(key=lambda item: item[0])
    orphan_trunk_ids: list[str] = []
    for _key, trunk_id in orphan_entries:
        if trunk_id in seen_line_ids:
            continue
        seen_line_ids.add(trunk_id)
        ordered_line_ids.append(trunk_id)
        orphan_trunk_ids.append(trunk_id)

    debug: dict = {
        "rootNodeIds": roots,
        "appendedNodeIds": appended_node_ids,
        "nodeCount": len(by_id),
    }
    deferred_back_edge_count = sum(
        1
        for node_id in by_id
        for pred in preds.get(node_id, [])
        if pred in by_id and pred not in effective_preds.get(node_id, [])
    )
    if deferred_back_edge_count:
        debug["deferredBackEdgeCount"] = deferred_back_edge_count
    if ignored_duplicate_node_ids:
        debug["ignoredDuplicateNodeIds"] = sorted(ignored_duplicate_node_ids, key=str)
    if orphan_trunk_ids:
        debug["orphanTrunkIds"] = orphan_trunk_ids
    return ordered_line_ids, debug


def _load_dialog_tree_extra_config(tree_key: str) -> dict | None:
    if tree_key in _DIALOG_TREE_EXTRA_CONFIG_CACHE:
        return _DIALOG_TREE_EXTRA_CONFIG_CACHE[tree_key]
    prefix = f"{tree_key}_"

    result = None
    for base in ANIME_RESOURCE_DIRS:
        path = base / f"{tree_key}_extra_config.json"
        if not path.exists():
            continue
        payload = _load_anime_resource_payload(path)
        if payload is None:
            continue

        configured_line_ids = payload.get("lineIds") if isinstance(payload, dict) else None
        if isinstance(configured_line_ids, list):
            line_ids = [
                line_id
                for line_id in configured_line_ids
                if isinstance(line_id, str) and line_id.startswith(prefix)
            ]
        elif isinstance(payload, dict):
            line_ids = [
                key
                for key in payload.keys()
                if isinstance(key, str) and key.startswith(prefix)
            ]
        else:
            line_ids = []

        if not line_ids:
            continue
        result = {
            "sourceKey": tree_key,
            "file": repo_rel(path),
            "lineIds": line_ids,
        }
    _DIALOG_TREE_EXTRA_CONFIG_CACHE[tree_key] = result
    return result


def _line_order_stems(line_id: str) -> list[str]:
    value = str(line_id or "").strip()
    if not value:
        return []
    stems: list[str] = []
    if re.search(r"_\d+$", value):
        stems.append(re.sub(r"_\d+$", "", value))
    if not value.startswith("dlg_") and re.search(r"_\d+_\d+$", value):
        stem = re.sub(r"_\d+_\d+$", "", value)
        if stem not in stems:
            stems.append(stem)
    return stems


def _option_id_scene_key(option_id: str) -> str:
    value = str(option_id or "").strip()
    if not value.startswith("option_dlg_"):
        return ""
    parts = value.rsplit("_", 2)
    if len(parts) != 3:
        return ""
    return parts[0][len("option_"):]


def _option_id_group_parts(option_id: str) -> tuple[str, int, int] | None:
    value = str(option_id or "").strip()
    match = OPTION_RE.match(value)
    if not match:
        return None
    return (f"dlg_{match.group(1)}_{match.group(2)}", int(match.group(3)), int(match.group(4)))


def _option_text_signature(text: str) -> str:
    return re.sub(r"\s+", "", str(text or "").strip())


def _timeline_stem_to_dialog_key(timeline: str) -> str:
    value = str(timeline or "")
    for prefix in ("f_dlgtl_", "m_dlgtl_", "dlgtl_"):
        if value.startswith(prefix):
            value = value[len(prefix):]
            break
    value = re.sub(r"_sub_\d+$", "", value)
    return f"dlg_{value}" if value else ""


def _normalize_line_order_ids(values) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        line_id = str(value or "").strip()
        if not line_id or line_id in seen:
            continue
        seen.add(line_id)
        out.append(line_id)
    return out


def _normalize_dialog_timeline_option_anchors(value) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict] = {}
    for raw_option_id, raw_anchor in value.items():
        option_id = str(raw_option_id or "").strip()
        if not _option_id_scene_key(option_id):
            continue
        if isinstance(raw_anchor, dict):
            after = str(raw_anchor.get("after") or "").strip()
            position = str(raw_anchor.get("position") or "").strip()
            mode = str(raw_anchor.get("mode") or "").strip()
            source = str(raw_anchor.get("sourceFile") or "").strip()
            track = str(raw_anchor.get("track") or "").strip().replace("\\", "/")
        else:
            after = str(raw_anchor or "").strip()
            position = ""
            mode = "timeline"
            source = ""
            track = ""
        anchor = {
            "mode": mode or ("timelinePreviousLine" if after else "timelinePre"),
        }
        if after:
            anchor["after"] = after
        elif position == "pre":
            anchor["position"] = "pre"
        else:
            continue
        if source:
            anchor["sourceFile"] = source
        if track:
            anchor["track"] = track
        out[option_id] = anchor
    return out


def _normalize_dialog_timeline_file(entry: dict) -> str:
    for key in ("source", "file"):
        value = str(entry.get(key) or "").strip()
        if value:
            return value.replace("\\", "/")
    roots = entry.get("sourceRoots")
    if isinstance(roots, list) and roots:
        return str(roots[0] or "").replace("\\", "/")
    return ""


def _iter_dialog_timeline_payload_entries(raw_key: str, payload):
    if not isinstance(payload, dict):
        return
    variants = payload.get("variants")
    if isinstance(variants, list) and variants:
        for variant in variants:
            if isinstance(variant, dict):
                yield variant
        return
    yield payload


def _add_dialog_timeline_alias(aliases: set[str], key: str) -> None:
    key = str(key or "").strip()
    if not key or key.startswith("_"):
        return
    aliases.add(key)
    if key.startswith("misc_"):
        aliases.add(key[len("misc_"):])


def _dialog_timeline_aliases(raw_key: str, entry: dict, line_ids: list[str], option_ids: list[str]) -> set[str]:
    aliases: set[str] = set()
    _add_dialog_timeline_alias(aliases, raw_key)
    _add_dialog_timeline_alias(aliases, str(entry.get("dialogKey") or ""))
    timeline = str(entry.get("timeline") or raw_key or "")
    if timeline:
        _add_dialog_timeline_alias(aliases, _timeline_stem_to_dialog_key(timeline))
    for line_id in line_ids:
        for stem in _line_order_stems(line_id):
            _add_dialog_timeline_alias(aliases, stem)
    for option_id in option_ids:
        _add_dialog_timeline_alias(aliases, _option_id_scene_key(option_id))
    return aliases


def _normalize_dialog_timeline_lines(value, line_ids: list[str]) -> list[dict]:
    if not isinstance(value, list):
        return []
    valid = set(line_ids)
    out: list[dict] = []
    seen: set[str] = set()
    for raw in value:
        if not isinstance(raw, dict):
            continue
        line_id = str(raw.get("id") or "").strip()
        if not line_id or line_id not in valid or line_id in seen:
            continue
        seen.add(line_id)
        try:
            start = float(raw.get("start", 0.0))
        except (TypeError, ValueError):
            start = 0.0
        try:
            duration = float(raw.get("duration", 0.0))
        except (TypeError, ValueError):
            duration = 0.0
        record = {
            "id": line_id,
            "start": round(start, 3),
            "duration": round(duration, 3),
        }
        actor = str(raw.get("actor") or "").strip()
        if actor:
            record["actor"] = actor
        for field in ("clipOptionIndex",):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, int):
                record[field] = value_for_field
        out.append(record)
    out.sort(key=lambda item: (item["start"], item["id"]))
    return out


def _normalize_dialog_timeline_option_positions(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        try:
            start = round(float(raw.get("start", 0.0)), 3)
        except (TypeError, ValueError):
            continue
        try:
            duration = round(float(raw.get("duration", 0.0)), 3)
        except (TypeError, ValueError):
            duration = 0.0
        scenes = [str(s).strip() for s in (raw.get("scenes") or []) if str(s).strip()]
        option_ids = [str(s).strip() for s in (raw.get("optionIds") or []) if str(s).strip()]
        out.append({
            "start": start,
            "duration": duration,
            "scenes": scenes,
            "optionIds": option_ids,
        })
    out.sort(key=lambda item: item["start"])
    return out


def _normalize_dialog_timeline_option_rows(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        option_id = str(raw.get("id") or "").strip()
        if not option_id:
            continue
        record: dict = {"id": option_id}
        for field in (
            "groupKey",
            "anchorMode",
            "anchorLineId",
            "track",
            "trackName",
            "sourceFile",
            "assetName",
            "assetTrack",
            "trunkId",
            "dialogId",
            "overrideOptionIconType",
        ):
            value_for_field = str(raw.get(field) or "").strip()
            if value_for_field:
                record[field] = value_for_field
        for field in (
            "index",
            "optionIndex",
            "clipOptionIndex",
            "trackPathId",
            "assetPathId",
            "logicId",
            "selectedFlag",
            "setGreyed",
            "main",
            "isChat",
            "changeFinishNum",
            "targetFinishNum",
            "useExOptionColor",
            "overrideOptionIcon",
            "conditionRid",
        ):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, int):
                record[field] = value_for_field
        for field in ("start", "duration"):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, (int, float)):
                record[field] = round(float(value_for_field), 3)
        out.append(record)
    out.sort(key=lambda item: (
        item.get("start", 0.0),
        item.get("optionIndex") if item.get("optionIndex") is not None else 10**9,
        item.get("id") or "",
        item.get("anchorMode") or "",
    ))
    return out


def _normalize_dialog_timeline_option_routes(value) -> dict[str, dict]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict] = {}
    for raw_option_id, raw in value.items():
        if not isinstance(raw, dict):
            continue
        option_id = str(raw_option_id or raw.get("id") or "").strip()
        if not option_id:
            continue
        path_line_ids = _normalize_line_order_ids(raw.get("pathLineIds"))
        skipped_line_ids = _normalize_line_order_ids(raw.get("skippedLineIds"))
        terminates_slot = bool(raw.get("terminatesSlot"))
        if not path_line_ids and not terminates_slot:
            continue
        record: dict = {
            "source": str(raw.get("source") or "runtimeJumpTrack"),
            "pathLineIds": path_line_ids,
            "skippedLineIds": skipped_line_ids,
        }
        if terminates_slot:
            record["terminatesSlot"] = True
        reverse_range_line_ids = _normalize_line_order_ids(raw.get("reverseRangeLineIds"))
        if reverse_range_line_ids:
            record["reverseRangeLineIds"] = reverse_range_line_ids
        for field in ("groupKey", "continuationGroupKey"):
            value_for_field = str(raw.get(field) or "").strip()
            if value_for_field:
                record[field] = value_for_field
        continuation_option_ids = _normalize_line_order_ids(raw.get("continuationOptionIds"))
        if continuation_option_ids:
            record["continuationOptionIds"] = continuation_option_ids
        for field in ("optionIndex",):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, int):
                record[field] = value_for_field
        for field in ("start", "end"):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, (int, float)):
                record[field] = round(float(value_for_field), 3)
        def normalize_ranges(raw_ranges) -> list[dict]:
            ranges: list[dict] = []
            for raw_range in raw_ranges or []:
                if not isinstance(raw_range, dict):
                    continue
                range_record: dict = {}
                for field in ("start", "end", "duration", "crossFadeDurationAfterJump"):
                    value_for_field = raw_range.get(field)
                    if isinstance(value_for_field, (int, float)):
                        range_record[field] = round(float(value_for_field), 3)
                for field in ("track", "trackName", "assetTrack", "displayName"):
                    value_for_field = str(raw_range.get(field) or "").strip()
                    if value_for_field:
                        range_record[field] = value_for_field
                for field in ("isReverseJump", "needChangeOptionAfterJump", "optionIndexAfterJump", "isJumpFirst"):
                    value_for_field = raw_range.get(field)
                    if isinstance(value_for_field, int):
                        range_record[field] = value_for_field
                if range_record:
                    ranges.append(range_record)
            return ranges

        skip_ranges = normalize_ranges(raw.get("skipRanges"))
        reverse_ranges = normalize_ranges(raw.get("reverseRanges"))
        if skip_ranges:
            record["skipRanges"] = skip_ranges
        if reverse_ranges:
            record["reverseRanges"] = reverse_ranges
        out[option_id] = record
    return dict(sorted(out.items()))


def _normalize_dialog_timeline_runtime_jump_clips(value) -> list[dict]:
    if not isinstance(value, list):
        return []
    out: list[dict] = []
    for raw in value:
        if not isinstance(raw, dict):
            continue
        record: dict = {}
        for field in ("start", "end", "duration", "crossFadeDurationAfterJump"):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, (int, float)):
                record[field] = round(float(value_for_field), 3)
        for field in (
            "optionIndex",
            "isReverseJump",
            "needChangeOptionAfterJump",
            "optionIndexAfterJump",
            "isJumpFirst",
        ):
            value_for_field = raw.get(field)
            if isinstance(value_for_field, int):
                record[field] = value_for_field
        for field in (
            "track",
            "trackName",
            "assetTrack",
            "displayName",
            "sourceFile",
        ):
            value_for_field = str(raw.get(field) or "").strip()
            if value_for_field:
                record[field] = value_for_field
        if record:
            out.append(record)
    out.sort(key=lambda item: (
        item.get("start", 0.0),
        item.get("optionIndex") if item.get("optionIndex") is not None else 10**9,
        item.get("track") or "",
    ))
    return out


def _index_dialog_timeline_entry(index: dict[str, list[dict]], raw_key: str, entry: dict) -> None:
    line_ids = _normalize_line_order_ids(entry.get("lineIds"))
    option_ids = _normalize_line_order_ids(entry.get("optionIds"))
    option_anchors = _normalize_dialog_timeline_option_anchors(entry.get("optionAnchors"))
    for option_id in option_anchors:
        if option_id not in option_ids:
            option_ids.append(option_id)
    if not line_ids and not option_ids:
        return
    timeline = str(entry.get("timeline") or raw_key or "")
    source_file = _normalize_dialog_timeline_file(entry)
    line_timings = _normalize_dialog_timeline_lines(entry.get("lines"), line_ids)
    timed_line_ids = [str(item.get("id") or "") for item in line_timings if item.get("id")]
    ordered_line_ids = [
        *timed_line_ids,
        *(line_id for line_id in line_ids if line_id not in timed_line_ids),
    ] if timed_line_ids else line_ids
    option_positions = _normalize_dialog_timeline_option_positions(entry.get("optionPositions"))
    option_rows = _normalize_dialog_timeline_option_rows(entry.get("options"))
    option_routes = _normalize_dialog_timeline_option_routes(entry.get("optionRoutes"))
    runtime_jump_clips = _normalize_dialog_timeline_runtime_jump_clips(
        entry.get("runtimeJumpClips")
    )
    runtime_jump_evidence_present = "runtimeJumpClips" in entry
    normalized = {
        "sourceKey": timeline or raw_key,
        "timeline": timeline,
        "file": source_file,
        "lineIds": ordered_line_ids,
        "optionIds": option_ids,
        "optionAnchors": option_anchors,
        "lineTimings": line_timings,
        "optionPositions": option_positions,
        "optionRows": option_rows,
        "optionRoutes": option_routes,
        "runtimeJumpClips": runtime_jump_clips,
        "runtimeJumpEvidencePresent": runtime_jump_evidence_present,
    }
    identity = (
        normalized["sourceKey"],
        normalized["file"],
        tuple(ordered_line_ids),
        tuple(option_ids),
        json.dumps(option_anchors, sort_keys=True, ensure_ascii=False),
        json.dumps(option_rows, sort_keys=True, ensure_ascii=False),
        json.dumps(option_routes, sort_keys=True, ensure_ascii=False),
        json.dumps(runtime_jump_clips, sort_keys=True, ensure_ascii=False),
        runtime_jump_evidence_present,
    )
    for alias in _dialog_timeline_aliases(raw_key, entry, ordered_line_ids, option_ids):
        bucket = index.setdefault(alias, [])
        if any(item.get("_identity") == identity for item in bucket):
            continue
        bucket.append({**normalized, "_identity": identity})


def _load_dialog_timeline_line_order_index() -> dict[str, list[dict]]:
    global _DIALOG_TIMELINE_LINE_ORDER_CACHE
    if _DIALOG_TIMELINE_LINE_ORDER_CACHE is not None:
        return _DIALOG_TIMELINE_LINE_ORDER_CACHE

    index: dict[str, list[dict]] = defaultdict(list)
    for path in TIMELINE_LINE_ORDER_PATHS:
        if not path.exists():
            continue
        try:
            with path.open(encoding="utf-8-sig") as f:
                payload = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(payload, dict):
            continue

        if isinstance(payload.get("lineIds"), list):
            _index_dialog_timeline_entry(index, path.stem, payload)

        by_dialog = payload.get("byDialogKey")
        if isinstance(by_dialog, dict):
            for raw_key, raw_entry in by_dialog.items():
                for entry in _iter_dialog_timeline_payload_entries(str(raw_key), raw_entry):
                    _index_dialog_timeline_entry(index, str(raw_key), entry)

        for raw_key, raw_entry in payload.items():
            if str(raw_key).startswith("_") or raw_key == "byDialogKey":
                continue
            for entry in _iter_dialog_timeline_payload_entries(str(raw_key), raw_entry):
                _index_dialog_timeline_entry(index, str(raw_key), entry)

    cleaned: dict[str, list[dict]] = {}
    for key, entries in index.items():
        public_entries: list[dict] = []
        for entry in entries:
            public = {field: entry[field] for field in ("sourceKey", "timeline", "file", "lineIds")}
            if entry.get("optionIds"):
                public["optionIds"] = entry["optionIds"]
            if entry.get("optionAnchors"):
                public["optionAnchors"] = entry["optionAnchors"]
            if entry.get("lineTimings"):
                public["lineTimings"] = entry["lineTimings"]
            if entry.get("optionPositions"):
                public["optionPositions"] = entry["optionPositions"]
            if entry.get("optionRows"):
                public["optionRows"] = entry["optionRows"]
            if entry.get("optionRoutes"):
                public["optionRoutes"] = entry["optionRoutes"]
            if entry.get("runtimeJumpEvidencePresent"):
                public["runtimeJumpClips"] = entry["runtimeJumpClips"]
            public_entries.append(public)
        public_entries.sort(key=lambda item: (-len(item["lineIds"]), item["sourceKey"], item["file"]))
        cleaned[key] = public_entries
    _DIALOG_TIMELINE_LINE_ORDER_CACHE = cleaned
    return _DIALOG_TIMELINE_LINE_ORDER_CACHE


def load_dialog_timeline_line_orders(conv_key: str) -> list[dict]:
    return list(_load_dialog_timeline_line_order_index().get(conv_key, []))


def load_dialog_timeline_option_anchors(conv_key: str) -> list[dict]:
    return [
        entry
        for entry in _load_dialog_timeline_line_order_index().get(conv_key, [])
        if entry.get("optionAnchors")
    ]


_TIMELINE_TO_DIALOG_KEYS_CACHE: dict[str, list[str]] | None = None


def _load_timeline_to_dialog_keys() -> dict[str, list[str]]:
    """Return {timeline_name: [dialog_key, ...]} reverse index across all timelines.

    Built once from the dialog-timeline index so that we can show "this scene
    shares its Unity timeline with X, Y" cross-links in the conv view.
    """
    global _TIMELINE_TO_DIALOG_KEYS_CACHE
    if _TIMELINE_TO_DIALOG_KEYS_CACHE is not None:
        return _TIMELINE_TO_DIALOG_KEYS_CACHE
    out: dict[str, set[str]] = defaultdict(set)
    for alias, entries in _load_dialog_timeline_line_order_index().items():
        if not isinstance(alias, str) or not alias.startswith("dlg_"):
            continue
        for entry in entries:
            timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
            if timeline:
                out[timeline].add(alias)
    _TIMELINE_TO_DIALOG_KEYS_CACHE = {tl: sorted(keys) for tl, keys in out.items()}
    return _TIMELINE_TO_DIALOG_KEYS_CACHE


def collect_related_scenes(conv_key: str) -> list[dict]:
    """For each timeline this scene appears in, list the OTHER dialog keys that
    also reference it. Returned dicts carry timeline name + line counts so the
    UI can show "shared timeline with X (3 lines overlap)".
    """
    if not conv_key:
        return []
    timeline_to_keys = _load_timeline_to_dialog_keys()
    own_entries = load_dialog_timeline_line_orders(conv_key)
    if not own_entries:
        return []
    own_line_ids: dict[str, set[str]] = {}
    for entry in own_entries:
        timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
        if not timeline:
            continue
        own_line_ids.setdefault(timeline, set()).update(
            str(line_id) for line_id in (entry.get("lineIds") or []) if str(line_id).startswith(f"{conv_key}_")
        )
    related: list[dict] = []
    seen_keys: set[str] = set()
    for timeline, line_set in own_line_ids.items():
        for sibling in timeline_to_keys.get(timeline, []):
            if sibling == conv_key or sibling in seen_keys:
                continue
            seen_keys.add(sibling)
            sibling_entries = load_dialog_timeline_line_orders(sibling)
            sibling_line_ids: set[str] = set()
            for entry in sibling_entries:
                if str(entry.get("timeline") or entry.get("sourceKey") or "") != timeline:
                    continue
                sibling_line_ids.update(
                    str(line_id)
                    for line_id in (entry.get("lineIds") or [])
                    if str(line_id).startswith(f"{sibling}_")
                )
            related.append({
                "key": sibling,
                "timeline": timeline,
                "ownLineCount": len(line_set),
                "siblingLineCount": len(sibling_line_ids),
            })
    related.sort(key=lambda item: (item["key"], item["timeline"]))
    return related


def collect_option_position_anchors(conv_key: str) -> list[dict]:
    """For each option clip on a timeline this conv participates in, locate the
    line in this conv (by id prefix) whose `start` is the immediate predecessor
    of the option clip's start. Returns one record per option clip in
    chronological order, so caller can map nth optionGroup to nth position.
    """
    if not conv_key:
        return []
    out: list[dict] = []
    for entry in load_dialog_timeline_line_orders(conv_key):
        positions = entry.get("optionPositions") or []
        line_timings = entry.get("lineTimings") or []
        if not positions or not line_timings:
            continue
        own_line_timings = sorted(
            (
                (float(item.get("start", 0.0)), str(item.get("id") or ""))
                for item in line_timings
                if str(item.get("id") or "").startswith(f"{conv_key}_")
            ),
            key=lambda pair: pair[0],
        )
        if not own_line_timings:
            continue
        timeline_name = str(entry.get("timeline") or entry.get("sourceKey") or "")
        for position in positions:
            try:
                pos_start = float(position.get("start", 0.0))
            except (TypeError, ValueError):
                continue
            before = ""
            for start, line_id in own_line_timings:
                if start <= pos_start + 1e-6:
                    before = line_id
                else:
                    break
            sibling_scenes = [s for s in (position.get("scenes") or []) if s and s != conv_key]
            out.append({
                "start": pos_start,
                "afterLineId": before,
                "siblingScenes": sibling_scenes,
                "timeline": timeline_name,
            })
    out.sort(key=lambda item: item["start"])
    return out


def _dialog_timeline_entry_identity(entry: dict) -> tuple:
    return (
        str(entry.get("sourceKey") or ""),
        str(entry.get("timeline") or ""),
        str(entry.get("file") or ""),
        tuple(str(line_id) for line_id in (entry.get("lineIds") or [])),
    )


def _dialog_tree_cinematic_anchor_entries(tree_file: dict | None, timeline_entries: list[dict]) -> list[dict]:
    if not tree_file or not timeline_entries:
        return []
    anchors = [
        anchor
        for anchor in (tree_file.get("cinematicTimelineAnchors") or [])
        if isinstance(anchor, dict) and anchor.get("timeline")
    ]
    if not anchors:
        return []

    timeline_by_name: dict[str, list[dict]] = defaultdict(list)
    for entry in timeline_entries:
        for name in (
            str(entry.get("timeline") or ""),
            str(entry.get("sourceKey") or ""),
        ):
            if name and entry not in timeline_by_name[name]:
                timeline_by_name[name].append(entry)

    ordered: list[dict] = []
    seen: set[tuple] = set()
    for anchor in anchors:
        timeline_name = str(anchor.get("timeline") or "")
        for entry in timeline_by_name.get(timeline_name, []):
            identity = _dialog_timeline_entry_identity(entry)
            if identity in seen:
                continue
            seen.add(identity)
            ordered.append(entry)
    return ordered


def _cinematic_timeline_line_sequence(
    conv_key: str,
    available_set: set[str],
    timeline_entries: list[dict],
    tree_file: dict | None,
) -> tuple[list[str], list[dict], list[dict]] | None:
    if not conv_key or not available_set or not tree_file:
        return None
    if tree_file.get("lineIds") and not tree_file.get("cinematicOnly"):
        return None
    ordered_entries = _dialog_tree_cinematic_anchor_entries(tree_file, timeline_entries)
    if len(ordered_entries) < 2:
        return None

    matched_by_entry: list[list[str]] = [
        [
            str(line_id)
            for line_id in (entry.get("lineIds") or [])
            if str(line_id) in available_set
        ]
        for entry in ordered_entries
    ]
    if not any(matched_by_entry):
        return None

    future_line_sets: list[set[str]] = [set() for _entry in ordered_entries]
    future: set[str] = set()
    for idx in range(len(ordered_entries) - 1, -1, -1):
        future_line_sets[idx] = set(future)
        future.update(matched_by_entry[idx])

    ordered: list[str] = []
    seen_line_ids: set[str] = set()
    sources: list[dict] = []
    anchor_debug: list[dict] = []
    anchors = [
        anchor
        for anchor in (tree_file.get("cinematicTimelineAnchors") or [])
        if isinstance(anchor, dict) and anchor.get("timeline")
    ]

    for idx, entry in enumerate(ordered_entries):
        matched = matched_by_entry[idx]
        if idx < len(ordered_entries) - 1:
            candidate_added = [
                line_id
                for line_id in matched
                if line_id not in future_line_sets[idx]
            ]
        else:
            candidate_added = list(matched)
        added = [line_id for line_id in candidate_added if line_id not in seen_line_ids]
        if added:
            seen_line_ids.update(added)
            ordered.extend(added)
            timeline_name = str(entry.get("timeline") or entry.get("sourceKey") or "")
            source = {
                "kind": "dialogTimeline",
                "sourceKey": entry.get("sourceKey") or timeline_name or conv_key,
                "timeline": timeline_name,
                "file": entry.get("file") or "",
                "coverage": len(matched),
                "matchedLineIds": matched,
                "addedLineIds": added,
            }
            sources.append(source)
            anchor = next(
                (
                    anchor
                    for anchor in anchors
                    if str(anchor.get("timeline") or "") == timeline_name
                ),
                {},
            )
            anchor_debug.append({
                "timeline": timeline_name,
                "nodeId": str(anchor.get("nodeId") or ""),
                "addedLineIds": added,
            })

    if not ordered:
        return None
    return ordered, sources, anchor_debug


def collect_line_timings(conv_key: str) -> dict[str, dict]:
    """Return {line_id: {start, duration, timeline}} for lines in this conv
    that have recovered Unity Timeline timestamps.
    """
    if not conv_key:
        return {}
    out: dict[str, dict] = {}
    timeline_entries = load_dialog_timeline_line_orders(conv_key)
    line_owner: dict[str, str] = {}
    timeline_line_ids = {
        str(line_id)
        for entry in timeline_entries
        for line_id in (entry.get("lineIds") or [])
        if str(line_id).startswith(f"{conv_key}_")
    }
    if sequence := _cinematic_timeline_line_sequence(
        conv_key,
        timeline_line_ids,
        timeline_entries,
        _load_dialog_tree_file(conv_key),
    ):
        _ordered, sources, _anchors = sequence
        for source in sources:
            owner = str(source.get("timeline") or source.get("sourceKey") or "")
            if not owner:
                continue
            for line_id in source.get("addedLineIds") or []:
                line_owner[str(line_id)] = owner

    for entry in timeline_entries:
        timeline = str(entry.get("timeline") or entry.get("sourceKey") or "")
        for record in entry.get("lineTimings") or []:
            line_id = str(record.get("id") or "")
            if not line_id.startswith(f"{conv_key}_"):
                continue
            existing = out.get(line_id)
            new_record = {
                "start": record.get("start"),
                "duration": record.get("duration"),
                "timeline": timeline,
            }
            if line_owner:
                if line_owner.get(line_id) == timeline:
                    out[line_id] = new_record
                continue
            if existing is None or (
                # Prefer the entry whose timeline this line ID actually belongs to.
                str(existing.get("timeline") or "").lower() != timeline.lower()
                and timeline.startswith(f"dlgtl_{conv_key[len('dlg_'):]}_")
            ):
                out[line_id] = new_record
    return out


def _nearest_visible_timeline_anchor(anchor_id: str, timeline_line_ids: list[str], valid_line_ids: set[str]) -> str:
    anchor_id = str(anchor_id or "").strip()
    if not anchor_id:
        return ""
    if anchor_id in valid_line_ids:
        return anchor_id
    if not timeline_line_ids:
        return ""
    try:
        anchor_index = timeline_line_ids.index(anchor_id)
    except ValueError:
        return ""
    for line_id in reversed(timeline_line_ids[: anchor_index + 1]):
        if line_id in valid_line_ids:
            return line_id
    return ""


def _load_dialog_tree_source(tree_key: str) -> dict | None:
    """Parse one AnimeStudio DialogTree file, preserving per-target slices."""
    if tree_key in _DIALOG_TREE_SOURCE_CACHE:
        return _DIALOG_TREE_SOURCE_CACHE[tree_key]
    tree_path = _find_anime_tree_path(f"{tree_key}.json")
    if not tree_path.exists():
        _DIALOG_TREE_SOURCE_CACHE[tree_key] = None
        return None
    tree = _load_anime_resource_payload(tree_path)
    if not isinstance(tree, dict):
        _DIALOG_TREE_SOURCE_CACHE[tree_key] = None
        return None
    # Anime resource payloads are shared across the read-only carrier scans.
    # Never mutate the cached source object; synthetic node ids are assigned to
    # the per-call node copies below.
    asset_name = str(tree.get("_assetName", "") or "").strip()

    nodes = [
        dict(node) if isinstance(node, dict) else node
        for node in (tree.get("nodes") or [])
    ]
    existing_node_ids = {
        str(node.get("$id"))
        for node in nodes
        if isinstance(node, dict) and node.get("$id") is not None
    }
    for idx, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("$id") is not None:
            continue
        synthetic_id = str(idx)
        if synthetic_id in existing_node_ids:
            synthetic_id = f"__idx_{idx}"
        node["$id"] = synthetic_id
        existing_node_ids.add(synthetic_id)
    conns = tree.get("connections") or []
    by_id: dict[str, dict] = {}
    for n in nodes:
        nid = n.get("$id")
        if nid:
            by_id[nid] = n

    line_graph = _normalize_dialog_tree_line_graph(nodes, conns)
    option_nodes = [
        n for n in nodes
        if _node_short_type(n) == "DialogTreeOptionNode" and n.get("$id")
    ]
    action_assets: list[dict[str, str]] = []
    seen_action_assets: set[tuple[str, str]] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        action = node.get("_actionData") or {}
        if not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        if not action_name:
            continue
        candidate_names = [action_name]
        if not action_name.startswith(("f_", "m_")):
            candidate_names.extend([f"f_{action_name}", f"m_{action_name}"])
        for candidate_name in candidate_names:
            action_path = _find_anime_tree_path(f"{candidate_name}.json")
            if not action_path.exists():
                continue
            rel_path = repo_rel(action_path)
            dedup = (action_name, rel_path)
            if dedup in seen_action_assets:
                continue
            seen_action_assets.add(dedup)
            asset = {
                "name": action_name,
                "file": rel_path,
            }
            if candidate_name != action_name:
                asset["resolvedName"] = candidate_name
            action_assets.append(asset)
    line_ids, line_order_debug = _ordered_dialog_tree_trunk_ids(nodes, conns)
    option_ids = _unique_preserve([
        entry["_optionId"]
        for node in option_nodes
        for entry in (node.get("_normalOptions") or [])
        if isinstance(entry, dict) and entry.get("_optionId")
    ])
    terminal_counts = {
        "openUi": sum(1 for n in nodes if _node_short_type(n) == "DialogTreeOpenUINode"),
        "finish": sum(1 for n in nodes if _node_short_type(n) == "DialogTreeFinishNode"),
    }

    preds: dict[str, list[str]] = defaultdict(list)
    succs: dict[str, list[str]] = defaultdict(list)
    for c in conns:
        s = (c.get("_sourceNode") or {}).get("$ref")
        t = (c.get("_targetNode") or {}).get("$ref")
        if s and t:
            preds[t].append(s)
            succs[s].append(t)

    def node_type(node_id: str) -> str:
        node = by_id.get(node_id)
        return _node_short_type(node) if node else ""

    def node_trunk_id(node_id: str) -> str | None:
        node = by_id.get(node_id)
        return _first_string_field(node, "_trunkId") if node else None

    def nearest_trunk_id(start_id: str, prefix: str | None = None) -> str | None:
        seen: set[str] = {start_id}
        stack = list(preds.get(start_id, []))
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            node = by_id.get(cur)
            if node is None:
                continue
            if _node_short_type(node) == "DialogTreeTrunkNode":
                trunk_id = _first_string_field(node, "_trunkId")
                if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                    return trunk_id
            stack.extend(preds.get(cur, []))
        return None

    def nearest_option_anchor_trunk_id(
        start_id: str,
        *,
        prefix: str | None = None,
        excluded_trunks: set[str] | None = None,
    ) -> str | None:
        """Find the nearest upstream trunk that is not one of this menu's branches.

        Option hubs often have loop-return predecessors from branch endings.
        Those are graph predecessors, but they are not the line after which the
        menu first appears. Walk predecessors in connection order and skip any
        trunk already seen on the option group's forward paths.
        """
        excluded = {str(value) for value in (excluded_trunks or set()) if str(value)}
        seen: set[str] = {start_id}
        queue = deque(preds.get(start_id, []))
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            node = by_id.get(cur)
            if node is None:
                continue
            if _node_short_type(node) == "DialogTreeTrunkNode":
                trunk_id = _first_string_field(node, "_trunkId")
                if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                    if trunk_id not in excluded:
                        return trunk_id
            queue.extend(preds.get(cur, []))
        return None

    def nearest_layout_trunk_id(start_id: str, prefix: str | None = None) -> str | None:
        node = by_id.get(start_id)
        if not isinstance(node, dict):
            return None
        pos = node.get("_position") or {}
        if not isinstance(pos, dict):
            return None
        try:
            x = float(pos.get("x"))
            y = float(pos.get("y"))
        except (TypeError, ValueError):
            return None
        candidates: list[tuple[float, float, float, str]] = []
        for candidate in by_id.values():
            if _node_short_type(candidate) != "DialogTreeTrunkNode":
                continue
            trunk_id = _first_string_field(candidate, "_trunkId")
            if not trunk_id or (prefix and _dialog_tree_scene_prefix(trunk_id) != prefix):
                continue
            candidate_pos = candidate.get("_position") or {}
            if not isinstance(candidate_pos, dict):
                continue
            try:
                cx = float(candidate_pos.get("x"))
                cy = float(candidate_pos.get("y"))
            except (TypeError, ValueError):
                continue
            candidates.append((abs(cx - x), abs(cy - y), -cx, trunk_id))
        if not candidates:
            return None
        candidates.sort()
        return candidates[0][3]

    def walk_linear_path(start_id: str | None) -> list[str]:
        if not start_id:
            return []
        out: list[str] = []
        seen: set[str] = set()
        cur = start_id
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            typ = node_type(cur)
            if typ in ("DialogTreeFinishNode", "DialogTreeOpenUINode", "DialogTreeOptionNode"):
                break
            nxts = _unique_preserve(succs.get(cur, []))
            if len(nxts) != 1:
                break
            cur = nxts[0]
        return out

    def first_common_node(paths: list[list[str]]) -> str | None:
        non_empty = [path for path in paths if path]
        if len(non_empty) < 2:
            return None
        common = set(non_empty[0])
        for path in non_empty[1:]:
            common &= set(path)
        if not common:
            return None
        for node_id in non_empty[0]:
            if node_id in common:
                return node_id
        return None

    def first_trunk_on_path(start_id: str | None, prefix: str | None = None) -> str | None:
        for node_id in walk_linear_path(start_id):
            trunk_id = node_trunk_id(node_id)
            if trunk_id and (not prefix or _dialog_tree_scene_prefix(trunk_id) == prefix):
                return trunk_id
        return None

    after_map: dict[str, str] = {}
    branch_map: dict[str, list[str]] = {}
    merge_map: dict[str, str] = {}
    converge_map: dict[str, str] = {}
    pre_option_ids: list[str] = []
    scene_line_ids_by_prefix: dict[str, list[str]] = defaultdict(list)
    for line_id in line_ids:
        if prefix := _dialog_tree_scene_prefix(line_id):
            scene_line_ids_by_prefix[prefix].append(line_id)

    fragment_builders: dict[str, dict] = {}
    scene_link_builders: dict[str, list[dict]] = defaultdict(list)

    def option_node_scene_prefixes(node_id: str) -> list[str]:
        node = by_id.get(node_id) or {}
        return _unique_preserve([
            prefix
            for prefix in (
                _dialog_tree_option_prefix(entry["_optionId"])
                for entry in (node.get("_normalOptions") or [])
                if isinstance(entry, dict) and entry.get("_optionId")
            )
            if prefix
        ])

    def option_node_option_ids(node_id: str) -> list[str]:
        node = by_id.get(node_id) or {}
        return _unique_preserve([
            str(entry["_optionId"])
            for entry in (node.get("_normalOptions") or [])
            if isinstance(entry, dict) and entry.get("_optionId")
        ])

    def node_layout_x(node_id: str) -> float | None:
        node = by_id.get(node_id)
        if not isinstance(node, dict):
            return None
        pos = node.get("_position") or {}
        if not isinstance(pos, dict):
            return None
        try:
            return float(pos.get("x"))
        except (TypeError, ValueError):
            return None

    def downstream_local_trunk_ids(
        start_ids: list[str | None],
        *,
        target_key: str,
        stop_node_id: str,
    ) -> set[str]:
        """Collect target-scene trunks reached before returning to a larger hub.

        A source option node can have loop-back predecessors from follow-up
        prompts. Those predecessor trunks are real graph predecessors, but they
        are not where the parent menu first appears. Follow through local
        same-scene option nodes so those loop returns can be excluded from menu
        anchoring, and stop at mixed-scene hubs.
        """

        out: set[str] = set()
        seen: set[str] = set()
        stop_node_x = node_layout_x(stop_node_id)
        queue = deque(str(start_id) for start_id in start_ids if start_id)
        while queue:
            cur = queue.popleft()
            if cur in seen:
                continue
            seen.add(cur)
            if cur == stop_node_id:
                continue
            typ = node_type(cur)
            trunk_id = node_trunk_id(cur)
            if trunk_id and _dialog_tree_scene_prefix(trunk_id) == target_key:
                out.add(trunk_id)
            if typ in ("DialogTreeFinishNode", "DialogTreeOpenUINode"):
                continue
            if typ == "DialogTreeOptionNode":
                prefixes = option_node_scene_prefixes(cur)
                if not prefixes or any(prefix != target_key for prefix in prefixes):
                    continue
                cur_x = node_layout_x(cur)
                # Reaching an upstream menu means this path has looped back
                # to a parent hub; do not walk that menu's other branches.
                if stop_node_x is not None and cur_x is not None and cur_x <= stop_node_x:
                    continue
            queue.extend(str(nxt) for nxt in succs.get(cur, []) if nxt)
        return out

    def summarize_option_target(start_id: str | None) -> dict:
        path = walk_linear_path(start_id)
        line_path = _unique_preserve([
            trunk_id
            for node_id in path
            if (trunk_id := node_trunk_id(node_id))
        ])
        scene_path = _unique_preserve([
            prefix
            for prefix in (_dialog_tree_scene_prefix(line_id) for line_id in line_path)
            if prefix
        ])
        summary: dict = {
            "pathLineIds": line_path,
            "sceneKeys": scene_path,
        }
        debug: dict[str, object] = {}
        if start_id:
            debug["startNodeId"] = start_id
        if path:
            debug["pathNodeIds"] = path
        if line_path:
            summary["firstLineId"] = line_path[0]
        if scene_path:
            summary["firstSceneKey"] = scene_path[0]
        if path:
            last_id = path[-1]
            last_type = node_type(last_id)
            if last_id:
                debug["endNodeId"] = last_id
            if last_type:
                debug["endNodeType"] = last_type
            if last_type == "DialogTreeOptionNode":
                submenu_scene_keys = option_node_scene_prefixes(last_id)
                if submenu_scene_keys:
                    summary["submenuSceneKeys"] = submenu_scene_keys
                return_option_ids = option_node_option_ids(last_id)
                if return_option_ids:
                    debug["returnOptionIds"] = return_option_ids
            elif last_type == "DialogTreeFinishNode":
                summary["terminal"] = "finish"
            elif last_type == "DialogTreeOpenUINode":
                summary["terminal"] = "openUi"
        elif start_id:
            start_type = node_type(start_id)
            if start_id:
                debug["endNodeId"] = start_id
            if start_type:
                debug["endNodeType"] = start_type
            if start_type == "DialogTreeOptionNode":
                submenu_scene_keys = option_node_scene_prefixes(start_id)
                if submenu_scene_keys:
                    summary["submenuSceneKeys"] = submenu_scene_keys
                return_option_ids = option_node_option_ids(start_id)
                if return_option_ids:
                    debug["returnOptionIds"] = return_option_ids
            elif start_type == "DialogTreeFinishNode":
                summary["terminal"] = "finish"
            elif start_type == "DialogTreeOpenUINode":
                summary["terminal"] = "openUi"
        if debug:
            summary["_debug"] = debug
        return summary

    source_scene_keys = sorted(scene_line_ids_by_prefix)

    cinematic_timeline_anchors: list[dict] = []
    seen_cinematic_timeline_anchors: set[tuple[str, str]] = set()
    for node in nodes:
        if not isinstance(node, dict) or _node_short_type(node) != "DialogTreeCinematicNode":
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData") or {}
        if not node_id or not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        if not action_name:
            continue
        identity = (node_id, action_name)
        if identity in seen_cinematic_timeline_anchors:
            continue
        seen_cinematic_timeline_anchors.add(identity)
        anchor: dict[str, object] = {
            "sourceKey": tree_key,
            "file": repo_rel(tree_path),
            "nodeId": node_id,
            "timeline": action_name,
        }
        target_node_ids = [
            str(target_id)
            for target_id in _unique_preserve(succs.get(node_id, []))
            if target_id
        ]
        if target_node_ids:
            anchor["targetNodeIds"] = target_node_ids
            anchor["targetCount"] = len(target_node_ids)
            if before := first_trunk_on_path(target_node_ids[0]):
                anchor["before"] = before
        if after := nearest_trunk_id(node_id):
            anchor["after"] = after
        cinematic_timeline_anchors.append(anchor)

    cinematic_finish_groups: list[dict] = []
    for node in nodes:
        if not isinstance(node, dict) or _node_short_type(node) != "DialogTreeCinematicNode":
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData") or {}
        if not node_id or not isinstance(action, dict):
            continue
        action_name = str(action.get("name") or "").strip()
        finish_nums_raw = action.get("timelineFinishNums") or []
        if (
            not action_name
            or not action.get("useTimelineFinishNumBranch")
            or not isinstance(finish_nums_raw, list)
            or len(finish_nums_raw) < 2
        ):
            continue
        finish_nums: list[object] = []
        for value in finish_nums_raw:
            if isinstance(value, bool):
                finish_nums.append(int(value))
            elif isinstance(value, int):
                finish_nums.append(value)
            elif isinstance(value, float) and value.is_integer():
                finish_nums.append(int(value))
            else:
                finish_nums.append(value)
        finish_group: dict[str, object] = {
            "sourceKey": tree_key,
            "file": repo_rel(tree_path),
            "nodeId": node_id,
            "timeline": action_name,
            "finishNums": finish_nums,
        }
        target_node_ids = [
            str(target_id)
            for target_id in _unique_preserve(succs.get(node_id, []))
            if target_id
        ]
        if target_node_ids:
            finish_group["targetNodeIds"] = target_node_ids
            finish_group["targetCount"] = len(target_node_ids)
        if after := nearest_trunk_id(node_id):
            finish_group["after"] = after
        cinematic_finish_groups.append(finish_group)

    def classify_option_target_summary(summary: dict, target_key: str, source_option_node_id: str) -> dict:
        scene_keys = _unique_preserve([
            str(scene_key)
            for scene_key in (summary.get("sceneKeys") or [])
            if scene_key
        ])
        submenu_scene_keys = _unique_preserve([
            str(scene_key)
            for scene_key in (summary.get("submenuSceneKeys") or [])
            if scene_key
        ])
        terminal = str(summary.get("terminal") or "")
        first_scene_key = str(summary.get("firstSceneKey") or "")
        debug = dict(summary.get("_debug") or {})
        end_node_id = str(debug.get("endNodeId") or "")
        end_node_type = str(debug.get("endNodeType") or "")
        same_scene_path = bool(scene_keys) and all(scene_key == target_key for scene_key in scene_keys)
        returns_to_target_menu = bool(target_key) and target_key in submenu_scene_keys
        returns_to_other_menu = any(
            scene_key != target_key
            for scene_key in submenu_scene_keys
        )
        returns_to_source_option_node = (
            end_node_type == "DialogTreeOptionNode"
            and end_node_id == source_option_node_id
        )

        outcome_kind = "unknown"
        loop: dict[str, object] | None = None

        if end_node_type == "DialogTreeOptionNode":
            if returns_to_target_menu:
                outcome_kind = "sameSceneMenuLoop"
            elif returns_to_other_menu or any(scene_key != target_key for scene_key in scene_keys):
                outcome_kind = "crossSceneMenuReturn"
            else:
                outcome_kind = "menuReturn"
            loop = {
                "kind": "sameOptionMenuReturn" if returns_to_source_option_node else "menuReturn",
                "returnsToSourceOptionNode": returns_to_source_option_node,
            }
            if submenu_scene_keys:
                loop["sceneKeys"] = submenu_scene_keys
            if len(source_scene_keys) > 1:
                loop["sourceSceneKeys"] = source_scene_keys
        elif terminal:
            if same_scene_path:
                outcome_kind = "sameSceneTerminal"
            elif scene_keys:
                outcome_kind = "crossSceneTerminal"
            else:
                outcome_kind = "terminalOnly"
        elif same_scene_path:
            outcome_kind = "sameScenePath"
        elif scene_keys:
            outcome_kind = "crossScenePath"
        elif submenu_scene_keys:
            outcome_kind = "menuReturn"

        debug["targetSceneKey"] = target_key
        debug["sourceOptionNodeId"] = source_option_node_id
        if end_node_type == "DialogTreeOptionNode":
            debug["returnsToSourceOptionNode"] = returns_to_source_option_node
        summary["outcomeKind"] = outcome_kind
        summary["_debug"] = debug
        if loop:
            summary["loop"] = loop
        return summary

    def ensure_fragment(target_key: str) -> dict:
        fragment = fragment_builders.get(target_key)
        if fragment is None:
            fragment = {
                "sourceKey": tree_key,
                "targetKey": target_key,
                "file": repo_rel(tree_path),
                "lineIds": list(scene_line_ids_by_prefix.get(target_key, [])),
                "optionGroups": [],
                "terminalCounts": {"openUi": 0, "finish": 0},
                "after": {},
                "branches": {},
                "merge": {},
                "pre": [],
                "sceneSpan": len(scene_line_ids_by_prefix) > 1,
                "sourceSceneKeys": sorted(scene_line_ids_by_prefix),
            }
            fragment_builders[target_key] = fragment
        return fragment

    for opt_node in option_nodes:
        opt_entries = [
            entry for entry in (opt_node.get("_normalOptions") or [])
            if isinstance(entry, dict) and entry.get("_optionId")
        ]
        if not opt_entries:
            continue

        targets = list(succs.get(opt_node["$id"], []))
        if len(targets) == 1 and len(opt_entries) > 1:
            targets = targets * len(opt_entries)

        paths_by_option: dict[str, list[str]] = {}
        target_node_by_option: dict[str, str | None] = {}
        first_trunk_by_option: dict[str, str | None] = {}
        terminal_kind_by_option: dict[str, str] = {}
        for idx, entry in enumerate(opt_entries):
            opt_id = entry["_optionId"]
            target = targets[idx] if idx < len(targets) else None
            target_node_by_option[opt_id] = target
            option_path = walk_linear_path(target)
            paths_by_option[opt_id] = option_path
            first_trunk_by_option[opt_id] = first_trunk_on_path(target)
            if option_path:
                last_type = node_type(option_path[-1])
                if last_type in ("DialogTreeFinishNode", "DialogTreeOpenUINode"):
                    terminal_kind_by_option[opt_id] = last_type

        unique_paths = {tuple(path) for path in paths_by_option.values()}
        local_group_details: dict[str, dict] = {}
        if len(unique_paths) < 2:
            common_node = None
            merge_trunk = None
            if len(opt_entries) >= 2 and targets:
                common_trunk = first_trunk_on_path(targets[0])
                if common_trunk:
                    for entry in opt_entries:
                        converge_map[entry["_optionId"]] = common_trunk
        else:
            common_node = first_common_node(list(paths_by_option.values()))
            merge_trunk = first_trunk_on_path(common_node) if common_node else None
            exclusive_trunks_by_option: dict[str, list[str]] = {}
            for opt_id, option_path in paths_by_option.items():
                exclusive_trunks: list[str] = []
                for node_id in option_path:
                    if common_node and node_id == common_node:
                        break
                    trunk_id = node_trunk_id(node_id)
                    if trunk_id:
                        exclusive_trunks.append(trunk_id)
                exclusive_trunks_by_option[opt_id] = exclusive_trunks
                if exclusive_trunks:
                    branch_map[opt_id] = exclusive_trunks
                    if merge_trunk:
                        merge_map[opt_id] = merge_trunk
            if merge_trunk and not any(exclusive_trunks_by_option.values()):
                for entry in opt_entries:
                    converge_map[entry["_optionId"]] = merge_trunk

        scene_option_prefixes = _unique_preserve([
            prefix
            for prefix in (_dialog_tree_option_prefix(entry["_optionId"]) for entry in opt_entries)
            if prefix
        ])

        target_prefixes = _unique_preserve([
            prefix
            for prefix in (
                _dialog_tree_scene_prefix(first_trunk_by_option.get(entry["_optionId"]) or "")
                for entry in opt_entries
            )
            if prefix
        ])

        per_target_options: dict[str, list[str]] = defaultdict(list)
        for entry in opt_entries:
            opt_id = entry["_optionId"]
            if prefix := _dialog_tree_option_prefix(opt_id):
                per_target_options[prefix].append(opt_id)

        # Precompute per-target summaries and "interesting"/"pre" flags once
        # so both the scene-link and fragment loops read the correct values.
        # The original code built `option_summaries` inside the scene-link
        # loop and the fragment loop then read the stale final-iteration
        # value 鈥?misclassifying most fragment groups.
        per_target_summaries: dict[str, list[dict]] = {}
        per_target_has_interesting: dict[str, bool] = {}
        per_target_is_pre: dict[str, bool] = {}
        per_target_after: dict[str, str | None] = {}
        for target_key, target_opt_ids in per_target_options.items():
            forward_option_ids = [
                opt_id
                for opt_id in target_opt_ids
                if _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or "") == target_key
            ]
            forward_trunk_ids = {
                trunk_id
                for opt_id in forward_option_ids
                for node_id in paths_by_option.get(opt_id, [])
                if (trunk_id := node_trunk_id(node_id))
            }
            loop_return_trunk_ids = downstream_local_trunk_ids(
                [target_node_by_option.get(opt_id) for opt_id in target_opt_ids],
                target_key=target_key,
                stop_node_id=opt_node["$id"],
            )
            backward_trunk = (
                nearest_option_anchor_trunk_id(
                    opt_node["$id"],
                    prefix=target_key,
                    excluded_trunks=forward_trunk_ids | loop_return_trunk_ids,
                )
                or nearest_layout_trunk_id(opt_node["$id"], prefix=target_key)
            )
            # Hub-loop detection: in hub-spoke trees (e.g. dlg_a1m3_10 feeding
            # a1m3_3/4/5), the option's backward predecessors include the last
            # trunk of each spoke scene via loop-return DialogTransitionNodes.
            # That trunk is NOT a semantic "after" anchor 鈥?the option
            # introduces the scene. Suppress it only when the backward trunk
            # is actually on one of this option group's own forward paths.
            group_after = backward_trunk
            if backward_trunk and backward_trunk in (forward_trunk_ids | loop_return_trunk_ids):
                group_after = None
            summaries: list[dict] = []
            has_interesting_target = False
            for idx, entry in enumerate(opt_entries):
                opt_id = entry["_optionId"]
                if opt_id not in target_opt_ids:
                    continue
                target = targets[idx] if idx < len(targets) else None
                summary = summarize_option_target(target)
                summary = classify_option_target_summary(summary, target_key, opt_node["$id"])
                option_summary = {
                    "optionId": opt_id,
                    **summary,
                }
                summaries.append(option_summary)
                if summary.get("loop"):
                    has_interesting_target = True
                if summary.get("terminal"):
                    has_interesting_target = True
                if summary.get("firstSceneKey") and summary.get("firstSceneKey") != target_key:
                    has_interesting_target = True
                if any(
                    scene_key != target_key
                    for scene_key in (summary.get("submenuSceneKeys") or [])
                ):
                    has_interesting_target = True
                if any(scene_key != target_key for scene_key in (summary.get("sceneKeys") or [])):
                    has_interesting_target = True
            group_is_pre = False
            if not group_after:
                group_is_pre = any(
                    summary.get("firstSceneKey") == target_key
                    or target_key in (summary.get("sceneKeys") or [])
                    or bool(summary.get("terminal"))
                    for summary in summaries
                )
            per_target_summaries[target_key] = summaries
            per_target_has_interesting[target_key] = has_interesting_target
            per_target_is_pre[target_key] = group_is_pre
            per_target_after[target_key] = group_after

        for target_key, target_opt_ids in per_target_options.items():
            group_after = per_target_after[target_key]
            option_summaries = per_target_summaries[target_key]
            has_interesting_target = per_target_has_interesting[target_key]
            group_is_pre = per_target_is_pre[target_key]
            if group_after:
                for opt_id in target_opt_ids:
                    after_map[opt_id] = group_after
            if group_is_pre:
                for opt_id in target_opt_ids:
                    if opt_id not in pre_option_ids:
                        pre_option_ids.append(opt_id)
            if not has_interesting_target:
                continue
            scene_link_builders[target_key].append({
                "sourceKey": tree_key,
                "sceneKey": target_key,
                "file": repo_rel(tree_path),
                "after": group_after or "",
                "options": option_summaries,
                **({"position": "pre"} if group_is_pre else {}),
                "sceneSpan": len(scene_line_ids_by_prefix) > 1,
                "sourceSceneKeys": sorted(scene_line_ids_by_prefix),
                "_debug": {
                    "sourceOptionNodeId": opt_node["$id"],
                    "groupSceneKeys": scene_option_prefixes,
                    "targetSceneKeys": target_prefixes,
                },
            })

        for target_key, target_opt_ids in per_target_options.items():
            if target_key == tree_key:
                continue
            fragment = ensure_fragment(target_key)
            relevant_targets = _unique_preserve([
                prefix
                for opt_id in target_opt_ids
                if (prefix := _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or ""))
            ])
            group_mode = "sceneLocal"
            for opt_id in target_opt_ids:
                first_scene_key = _dialog_tree_scene_prefix(first_trunk_by_option.get(opt_id) or "")
                local_branch_lines = [
                    line_id
                    for line_id in (branch_map.get(opt_id) or [])
                    if _dialog_tree_scene_prefix(line_id) == target_key
                ]
                has_local_evidence = bool(
                    local_branch_lines
                    or first_scene_key == target_key
                    or terminal_kind_by_option.get(opt_id)
                )
                has_foreign_evidence = bool(
                    first_scene_key and first_scene_key != target_key
                ) or any(
                    _dialog_tree_scene_prefix(line_id) not in (None, target_key)
                    for line_id in (branch_map.get(opt_id) or [])
                )
                if has_foreign_evidence or not has_local_evidence:
                    group_mode = "crossScene"
                    break
            group_after = per_target_after[target_key] if group_mode == "sceneLocal" else None
            option_summaries = per_target_summaries[target_key]
            group_is_pre = False
            if group_mode == "sceneLocal" and not group_after:
                group_is_pre = any(
                    summary.get("firstSceneKey") == target_key
                    or target_key in (summary.get("sceneKeys") or [])
                    or bool(summary.get("terminal"))
                    for summary in option_summaries
                )
            group = {
                "mode": group_mode,
                "optionIds": list(target_opt_ids),
                "_debug": {
                    "groupSceneKeys": scene_option_prefixes,
                    "targetSceneKeys": relevant_targets,
                    "sourceOptionNodeId": opt_node["$id"],
                },
            }
            if group_after:
                group["after"] = group_after
            elif group_is_pre:
                group["position"] = "pre"

            group_branches: dict[str, list[str]] = {}
            group_merge: dict[str, str] = {}
            for opt_id in target_opt_ids:
                local_branch_lines = [
                    line_id
                    for line_id in (branch_map.get(opt_id) or [])
                    if _dialog_tree_scene_prefix(line_id) == target_key
                ]
                if local_branch_lines:
                    group_branches[opt_id] = local_branch_lines
                    if group_mode == "sceneLocal":
                        fragment["branches"][opt_id] = local_branch_lines
                if group_mode == "sceneLocal" and group_after:
                    fragment["after"][opt_id] = group_after
                elif group_mode == "sceneLocal" and group_is_pre:
                    if opt_id not in fragment["pre"]:
                        fragment["pre"].append(opt_id)
                    if opt_id not in pre_option_ids:
                        pre_option_ids.append(opt_id)
                local_merge = merge_map.get(opt_id)
                if local_merge and _dialog_tree_scene_prefix(local_merge) == target_key:
                    group_merge[opt_id] = local_merge
                    if group_mode == "sceneLocal":
                        fragment["merge"][opt_id] = local_merge
                terminal_kind = terminal_kind_by_option.get(opt_id, "")
                if terminal_kind == "DialogTreeOpenUINode":
                    fragment["terminalCounts"]["openUi"] += 1
                elif terminal_kind == "DialogTreeFinishNode":
                    fragment["terminalCounts"]["finish"] += 1
            if group_branches:
                group["branches"] = group_branches
            if group_merge:
                group["merge"] = group_merge
            fragment["optionGroups"].append(group)

    target_fragments: list[dict] = []
    for target_key, fragment in fragment_builders.items():
        if not fragment["optionGroups"] and len(scene_line_ids_by_prefix) == 1:
            fragment["terminalCounts"] = dict(terminal_counts)
        if not fragment["lineIds"] and not fragment["optionGroups"] and not any(fragment["terminalCounts"].values()):
            continue
        target_fragments.append(fragment)
    scene_links = [
        link
        for scene_key in sorted(scene_link_builders)
        for link in scene_link_builders[scene_key]
    ]

    source = {
        "sourceKey": tree_key,
        "file": repo_rel(tree_path),
        **({"assetName": asset_name} if asset_name else {}),
        "lineIds": line_ids,
        "lineGraph": line_graph,
        "lineOrder": {
            "mode": "graphTraversal",
            **line_order_debug,
        },
        "optionIds": option_ids,
        "terminalCounts": terminal_counts,
        "after": after_map,
        "branches": branch_map,
        "merge": merge_map,
        "converge": converge_map,
        "pre": pre_option_ids,
        "actionAssets": action_assets,
        "cinematicOnly": bool(action_assets) and not line_ids,
        "cinematicTimelineAnchors": cinematic_timeline_anchors,
        "cinematicFinishGroups": cinematic_finish_groups,
        "targetFragments": target_fragments,
        "sceneLinks": scene_links,
    }
    has_signal = bool(
        line_ids
        or option_ids
        or any(terminal_counts.values())
        or cinematic_finish_groups
        or target_fragments
        or scene_links
    )
    _DIALOG_TREE_SOURCE_CACHE[tree_key] = source if has_signal else None
    return _DIALOG_TREE_SOURCE_CACHE[tree_key]


def _load_dialog_tree_file(tree_key: str) -> dict | None:
    """Return compact whole-tree metadata for one AnimeStudio DialogTree file."""
    if tree_key in _DIALOG_TREE_FILE_CACHE:
        return _DIALOG_TREE_FILE_CACHE[tree_key]
    source = _load_dialog_tree_source(tree_key)
    if not source:
        _DIALOG_TREE_FILE_CACHE[tree_key] = None
        return None
    result = {
        "sourceKey": source.get("sourceKey") or tree_key,
        "file": source.get("file") or "",
        "lineIds": source.get("lineIds") or [],
        "lineGraph": source.get("lineGraph") or {},
        "lineOrder": source.get("lineOrder") or {},
        "optionIds": source.get("optionIds") or [],
        "terminalCounts": source.get("terminalCounts") or {},
        "after": source.get("after") or {},
        "branches": source.get("branches") or {},
        "merge": source.get("merge") or {},
        "converge": source.get("converge") or {},
        "pre": source.get("pre") or [],
        "actionAssets": source.get("actionAssets") or [],
        "cinematicOnly": bool(source.get("cinematicOnly")),
        "cinematicTimelineAnchors": source.get("cinematicTimelineAnchors") or [],
        "cinematicFinishGroups": source.get("cinematicFinishGroups") or [],
    }
    _DIALOG_TREE_FILE_CACHE[tree_key] = result
    return result


def _load_related_dialog_tree_files(conv_key: str, original_line_ids: list[str] | None = None) -> list[dict]:
    cache_key = (conv_key, tuple(original_line_ids or ()))
    if cache_key in _RELATED_DIALOG_TREE_FILE_CACHE:
        return list(_RELATED_DIALOG_TREE_FILE_CACHE[cache_key])
    available_line_ids = set(original_line_ids or [])
    related: list[dict] = []
    seen_source_keys: set[str] = set()

    for path in _iter_related_dialog_tree_paths(conv_key):
        source_key = _anime_tree_logical_stem(path)
        if source_key == conv_key or source_key in seen_source_keys:
            continue
        source = _load_dialog_tree_source(source_key)
        if not source:
            continue
        line_ids = source.get("lineIds") or []
        source_scene_keys = set(source.get("sourceSceneKeys") or [])
        line_matches = [
            line_id
            for line_id in line_ids
            if line_id.startswith(f"{conv_key}_")
            or (available_line_ids and line_id in available_line_ids)
        ]
        if not line_matches and conv_key not in source_scene_keys:
            continue
        seen_source_keys.add(source_key)
        related.append({
            "sourceKey": source.get("sourceKey") or source_key,
            "file": source.get("file") or "",
            "lineIds": line_ids,
            "lineGraph": source.get("lineGraph") or {},
            "lineOrder": source.get("lineOrder") or {},
            "optionIds": source.get("optionIds") or [],
            "terminalCounts": source.get("terminalCounts") or {},
            "after": source.get("after") or {},
            "branches": source.get("branches") or {},
            "merge": source.get("merge") or {},
            "pre": source.get("pre") or [],
            "actionAssets": source.get("actionAssets") or [],
            "cinematicOnly": bool(source.get("cinematicOnly")),
            "cinematicTimelineAnchors": source.get("cinematicTimelineAnchors") or [],
            "cinematicFinishGroups": source.get("cinematicFinishGroups") or [],
        })

    _RELATED_DIALOG_TREE_FILE_CACHE[cache_key] = list(related)
    return list(related)


def load_dialog_tree_fragments(conv_key: str) -> list[dict]:
    """Return authored tree fragments that target a different base scene."""
    global _DIALOG_TREE_FRAGMENT_TARGETS_CACHE
    if _DIALOG_TREE_FRAGMENT_TARGETS_CACHE is None:
        targets: dict[str, list[dict]] = defaultdict(list)
        seen_signatures_by_target: dict[str, set[str]] = defaultdict(set)
        for path in _iter_anime_tree_files("dlg_*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            source_key = _anime_tree_logical_stem(path)
            source = _load_dialog_tree_source(source_key)
            if not source:
                continue
            for fragment in source.get("targetFragments") or []:
                target_key = fragment.get("targetKey") or ""
                source_asset_name = source.get("assetName") or ""
                if not target_key or target_key in {source_key, source_asset_name}:
                    continue
                signature = _dialog_tree_semantic_signature(fragment)
                if signature in seen_signatures_by_target[target_key]:
                    continue
                seen_signatures_by_target[target_key].add(signature)
                targets[target_key].append(fragment)
        for bucket in targets.values():
            bucket.sort(key=lambda item: item["sourceKey"])
        _DIALOG_TREE_FRAGMENT_TARGETS_CACHE = dict(targets)
    return list((_DIALOG_TREE_FRAGMENT_TARGETS_CACHE or {}).get(conv_key, []))


def load_dialog_tree_scene_links(conv_key: str) -> list[dict]:
    """Return authored outgoing scene/menu links for one scene key."""
    global _DIALOG_TREE_SCENE_LINKS_CACHE
    if _DIALOG_TREE_SCENE_LINKS_CACHE is None:
        scene_links: dict[str, list[dict]] = defaultdict(list)
        seen_signatures_by_scene: dict[str, set[str]] = defaultdict(set)
        for path in _iter_anime_tree_files("dlg_*.json"):
            if path.name.endswith("_extra_config.json"):
                continue
            source = _load_dialog_tree_source(_anime_tree_logical_stem(path))
            if not source:
                continue
            for link in source.get("sceneLinks") or []:
                scene_key = link.get("sceneKey") or ""
                if scene_key:
                    signature = _dialog_tree_semantic_signature(link)
                    if signature in seen_signatures_by_scene[scene_key]:
                        continue
                    seen_signatures_by_scene[scene_key].add(signature)
                    scene_links[scene_key].append(link)
        for bucket in scene_links.values():
            bucket.sort(key=lambda item: ((item.get("sourceKey") or ""), (item.get("after") or "")))
        _DIALOG_TREE_SCENE_LINKS_CACHE = dict(scene_links)
    return list((_DIALOG_TREE_SCENE_LINKS_CACHE or {}).get(conv_key, []))


def load_dialog_tree(conv_key: str) -> dict | None:
    """Return compact branch metadata from AnimeStudio DialogTree.

    Payload shape:
      {
        "after": {option_id: after_trunk_id},
        "branches": {option_id: [exclusive_trunk_id, ...]},
        "merge": {option_id: merge_trunk_id},
        "cinematicFinishGroups": [
          {"timeline": timeline_asset_name, "finishNums": [...], ...},
        ],
      }

    `after` answers where the option group should render.
    `branches` captures per-option exclusive trunk ids until the first merge.
    `merge` names the first shared trunk after the branch split, when one
    exists inside the current linear path.
    """
    if conv_key in _DIALOG_TREE_CACHE:
        return _DIALOG_TREE_CACHE[conv_key]
    combined = {
        "after": {},
        "afterSources": {},
        "branches": {},
        "merge": {},
        "converge": {},
        "pre": [],
        "preSources": {},
        "lineIds": [],
        "sources": [],
        "cinematicFinishGroups": [],
    }
    tree_sources: list[dict] = []
    if meta := _load_dialog_tree_file(conv_key):
        tree_sources.append(meta)
    if not tree_sources or not any(
        (meta.get("lineIds") or [])
        or (meta.get("optionIds") or [])
        or (meta.get("pre") or [])
        or (meta.get("cinematicFinishGroups") or [])
        for meta in tree_sources
    ):
        for meta in _load_related_dialog_tree_files(conv_key):
            if any(existing.get("file") == meta.get("file") for existing in tree_sources):
                continue
            tree_sources.append(meta)
    tree_sources.extend(load_dialog_tree_fragments(conv_key))
    if extra_config := _load_dialog_tree_extra_config(conv_key):
        tree_sources.append(extra_config)

    seen_line_ids: set[str] = set()
    seen_cinematic_finish_groups: set[tuple[str, str, str]] = set()
    for meta in tree_sources:
        source_key = meta.get("sourceKey") or ""
        source_label = source_key or meta.get("file") or ""
        if source_key and source_key not in combined["sources"]:
            combined["sources"].append(source_key)
        for line_id in (meta.get("lineIds") or []):
            if line_id and line_id not in seen_line_ids:
                seen_line_ids.add(line_id)
                combined["lineIds"].append(line_id)
        for opt_id, after in (meta.get("after") or {}).items():
            combined["after"].setdefault(opt_id, after)
            if source_label:
                source_bucket = combined["afterSources"].setdefault(opt_id, [])
                if source_label not in source_bucket:
                    source_bucket.append(source_label)
        for opt_id, branch_lines in (meta.get("branches") or {}).items():
            combined["branches"].setdefault(opt_id, branch_lines)
        for opt_id, merge_id in (meta.get("merge") or {}).items():
            combined["merge"].setdefault(opt_id, merge_id)
        for opt_id, converge_trunk in (meta.get("converge") or {}).items():
            combined["converge"].setdefault(opt_id, converge_trunk)
        for opt_id in (meta.get("pre") or []):
            if opt_id and opt_id not in combined["pre"]:
                combined["pre"].append(opt_id)
            if opt_id and source_label:
                source_bucket = combined["preSources"].setdefault(opt_id, [])
                if source_label not in source_bucket:
                    source_bucket.append(source_label)
        for finish_group in (meta.get("cinematicFinishGroups") or []):
            if not isinstance(finish_group, dict):
                continue
            identity = (
                str(finish_group.get("sourceKey") or source_key),
                str(finish_group.get("timeline") or ""),
                str(finish_group.get("nodeId") or ""),
            )
            if identity in seen_cinematic_finish_groups:
                continue
            seen_cinematic_finish_groups.add(identity)
            combined["cinematicFinishGroups"].append(finish_group)

    _DIALOG_TREE_CACHE[conv_key] = combined if any(
        combined[key] for key in ("after", "branches", "merge", "converge")
    ) or combined["pre"] or combined["lineIds"] or combined["cinematicFinishGroups"] else None
    return _DIALOG_TREE_CACHE[conv_key]


def resolve_scene_line_order(conv_key: str, original_line_ids: list[str]) -> tuple[list[str], dict | None]:
    available_line_ids = [line_id for line_id in original_line_ids if line_id]
    available_set = set(available_line_ids)
    if not conv_key or not available_line_ids:
        return available_line_ids, None

    candidates: list[dict] = []
    tree_file = _load_dialog_tree_file(conv_key)

    def add_candidate(kind: str, source_key: str, file: str, line_ids: list[str], priority: int) -> None:
        matched = [line_id for line_id in line_ids if line_id in available_set]
        if not matched:
            return
        candidates.append({
            "kind": kind,
            "sourceKey": source_key,
            "file": file,
            "matchedLineIds": matched,
            "coverage": len(matched),
            "priority": priority,
        })

    if tree_file:
        add_candidate(
            "dialogTree",
            tree_file.get("sourceKey") or conv_key,
            tree_file.get("file") or "",
            tree_file.get("lineIds") or [],
            0,
        )
    direct_tree_coverage = max(
        (candidate["coverage"] for candidate in candidates if candidate["kind"] == "dialogTree"),
        default=0,
    )
    if not candidates or direct_tree_coverage < len(available_set):
        seen_candidate_files = {
            (candidate["sourceKey"], candidate["file"])
            for candidate in candidates
        }
        for meta in _load_related_dialog_tree_files(conv_key, available_line_ids):
            identity = (meta.get("sourceKey") or conv_key, meta.get("file") or "")
            if identity in seen_candidate_files:
                continue
            add_candidate(
                "dialogTree",
                meta.get("sourceKey") or conv_key,
                meta.get("file") or "",
                meta.get("lineIds") or [],
                0,
            )
            seen_candidate_files.add(identity)

    timeline_entries = load_dialog_timeline_line_orders(conv_key)
    for timeline in timeline_entries:
        add_candidate(
            "dialogTimeline",
            timeline.get("sourceKey") or timeline.get("timeline") or conv_key,
            timeline.get("file") or "",
            timeline.get("lineIds") or [],
            1,
        )

    def resolve_cinematic_timeline_stitch() -> tuple[list[str], dict] | None:
        if not tree_file:
            return None
        anchors = [
            anchor
            for anchor in (tree_file.get("cinematicTimelineAnchors") or [])
            if isinstance(anchor, dict) and anchor.get("timeline")
        ]
        if not anchors or not timeline_entries:
            return None
        tree_line_ids = [
            line_id
            for line_id in (tree_file.get("lineIds") or [])
            if line_id in available_set
        ]
        if not tree_line_ids:
            return None

        timeline_by_name: dict[str, list[dict]] = defaultdict(list)
        for entry in timeline_entries:
            for name in (
                str(entry.get("timeline") or ""),
                str(entry.get("sourceKey") or ""),
            ):
                if name and entry not in timeline_by_name[name]:
                    timeline_by_name[name].append(entry)

        inserted_by_after: dict[str, list[str]] = defaultdict(list)
        contributing_sources: list[dict] = [{
            "kind": "dialogTree",
            "sourceKey": tree_file.get("sourceKey") or conv_key,
            "file": tree_file.get("file") or "",
            "coverage": len(tree_line_ids),
            "matchedLineIds": tree_line_ids,
            "addedLineIds": list(tree_line_ids),
        }]
        used_anchor_details: list[dict] = []
        seen_line_ids: set[str] = set(tree_line_ids)
        for anchor in anchors:
            timeline_name = str(anchor.get("timeline") or "")
            after_line_id = str(anchor.get("after") or "")
            if not timeline_name or after_line_id not in tree_line_ids:
                continue
            for entry in timeline_by_name.get(timeline_name, []):
                matched = [
                    line_id
                    for line_id in (entry.get("lineIds") or [])
                    if line_id in available_set
                ]
                added = [line_id for line_id in matched if line_id not in seen_line_ids]
                if not added:
                    continue
                seen_line_ids.update(added)
                inserted_by_after[after_line_id].extend(added)
                contributing_sources.append({
                    "kind": "dialogTimeline",
                    "sourceKey": entry.get("sourceKey") or entry.get("timeline") or timeline_name,
                    "file": entry.get("file") or "",
                    "coverage": len(matched),
                    "matchedLineIds": matched,
                    "addedLineIds": added,
                })
                used_anchor_details.append({
                    "timeline": timeline_name,
                    "nodeId": str(anchor.get("nodeId") or ""),
                    "after": after_line_id,
                    "before": str(anchor.get("before") or ""),
                    "addedLineIds": added,
                })

        if not used_anchor_details:
            return None
        ordered: list[str] = []
        for line_id in tree_line_ids:
            if line_id not in ordered:
                ordered.append(line_id)
            for inserted_id in inserted_by_after.get(line_id, []):
                if inserted_id not in ordered:
                    ordered.append(inserted_id)
        if set(ordered) != available_set or len(ordered) != len(available_set):
            return None
        return ordered, {
            "mode": "dialogTreeCinematicTimeline",
            "originalLineIds": available_line_ids,
            "orderedLineIds": ordered,
            "sources": contributing_sources,
            "stitch": "dialogTreeCinematicAnchors",
            "cinematicTimelineAnchors": used_anchor_details,
        }

    if cinematic_stitch := resolve_cinematic_timeline_stitch():
        return cinematic_stitch

    if cinematic_sequence := _cinematic_timeline_line_sequence(
        conv_key,
        available_set,
        timeline_entries,
        tree_file,
    ):
        ordered, sources, anchor_debug = cinematic_sequence
        if set(ordered) == available_set and len(ordered) == len(available_set):
            return ordered, {
                "mode": "dialogTreeCinematicTimeline",
                "originalLineIds": available_line_ids,
                "orderedLineIds": ordered,
                "sources": sources,
                "stitch": "dialogTreeCinematicAnchorSequence",
                "cinematicTimelineAnchors": anchor_debug,
            }

    for fragment in load_dialog_tree_fragments(conv_key):
        add_candidate(
            "dialogTreeFragment",
            fragment.get("sourceKey") or conv_key,
            fragment.get("file") or "",
            fragment.get("lineIds") or [],
            2,
        )

    # Extra config TextAssets are voice/audio sidecars. Their JSON key order is
    # not reliable execution order, so do not let them override the main
    # DialogTree, Timeline, fragments, or numeric fallback stitching.

    if not candidates:
        # Final fallback: if every line id ends in a unique numeric suffix
        # (the standard <conv_key>_<NNN> convention), use that ordering. This
        # covers cinematic scenes with no local DialogTree or Timeline asset
        # in the installed VFS, which otherwise leave the natural line order
        # undocumented.
        suffix_pairs: list[tuple[int, str]] = []
        for line_id in available_line_ids:
            match = re.search(r"_(\d+)$", line_id)
            if not match:
                suffix_pairs = []
                break
            suffix_pairs.append((int(match.group(1)), line_id))
        if suffix_pairs and len({pair[0] for pair in suffix_pairs}) == len(suffix_pairs):
            suffix_pairs.sort(key=lambda pair: pair[0])
            ordered = [line_id for _, line_id in suffix_pairs]
            return ordered, {
                "mode": "lineIdSuffix",
                "originalLineIds": available_line_ids,
                "orderedLineIds": ordered,
                "sources": [
                    {
                        "kind": "lineIdSuffix",
                        "sourceKey": conv_key,
                        "file": "",
                        "coverage": len(ordered),
                        "matchedLineIds": ordered,
                        "addedLineIds": ordered,
                    }
                ],
            }
        compound_suffix_pairs: list[tuple[int, int, str]] = []
        for line_id in available_line_ids:
            if not line_id.startswith("timeline_blackbox_"):
                compound_suffix_pairs = []
                break
            match = re.search(r"_(\d+)_(\d+)$", line_id)
            if not match:
                compound_suffix_pairs = []
                break
            compound_suffix_pairs.append((int(match.group(1)), int(match.group(2)), line_id))
        if (
            compound_suffix_pairs
            and len({(pair[0], pair[1]) for pair in compound_suffix_pairs}) == len(compound_suffix_pairs)
        ):
            compound_suffix_pairs.sort(key=lambda pair: (pair[0], pair[1], pair[2]))
            ordered = [line_id for _group, _step, line_id in compound_suffix_pairs]
            return ordered, {
                "mode": "compoundNumericSuffix",
                "originalLineIds": available_line_ids,
                "orderedLineIds": ordered,
                "sources": [
                    {
                        "kind": "compoundNumericSuffix",
                        "sourceKey": conv_key,
                        "file": "DialogTextTable.rowId",
                        "coverage": len(ordered),
                        "matchedLineIds": ordered,
                        "addedLineIds": ordered,
                    }
                ],
            }
        return available_line_ids, None

    candidates.sort(
        key=lambda item: (
            -item["coverage"],
            item["priority"],
            item["sourceKey"],
            item["file"],
        )
    )

    def line_suffix(line_id: str) -> int | None:
        match = re.search(r"_(\d+)$", line_id)
        return int(match.group(1)) if match else None

    def suffixes_are_strictly_monotonic(line_ids: list[str]) -> bool:
        suffixes = [line_suffix(line_id) for line_id in line_ids]
        if len(suffixes) < 2 or any(suffix is None for suffix in suffixes):
            return False
        numeric_suffixes = [int(suffix) for suffix in suffixes if suffix is not None]
        return len(set(numeric_suffixes)) == len(numeric_suffixes) and numeric_suffixes == sorted(numeric_suffixes)

    def all_available_line_suffixes_unique() -> bool:
        suffixes = [line_suffix(line_id) for line_id in available_line_ids]
        return (
            bool(suffixes)
            and all(suffix is not None for suffix in suffixes)
            and len(set(suffixes)) == len(suffixes)
        )

    def suffix_sorted_available_line_ids() -> list[str]:
        return [
            line_id
            for _suffix, line_id in sorted(
                ((line_suffix(line_id), line_id) for line_id in available_line_ids),
                key=lambda item: (item[0], item[1]),
            )
        ]

    def merge_uncovered_line_ids(ordered_ids: list[str], uncovered_ids: list[str]) -> list[str]:
        if not uncovered_ids:
            return ordered_ids
        suffixes = [line_suffix(line_id) for line_id in ordered_ids]
        numeric_suffixes = [suffix for suffix in suffixes if suffix is not None]
        if not numeric_suffixes:
            return [*ordered_ids, *uncovered_ids]

        min_suffix = min(numeric_suffixes)
        max_suffix = max(numeric_suffixes)
        prefix: list[tuple[int, str]] = []
        suffix: list[tuple[int, str]] = []
        unresolved: list[str] = []
        for line_id in uncovered_ids:
            suffix_num = line_suffix(line_id)
            if suffix_num is None:
                unresolved.append(line_id)
            elif suffix_num < min_suffix:
                prefix.append((suffix_num, line_id))
            elif suffix_num > max_suffix:
                suffix.append((suffix_num, line_id))
            else:
                # In-range holes are ambiguous once an authored source has
                # reordered the scene, so keep the old conservative tail
                # behavior for those.
                unresolved.append(line_id)
        prefix.sort(key=lambda item: item[0])
        suffix.sort(key=lambda item: item[0])
        return [
            *(line_id for _suffix, line_id in prefix),
            *ordered_ids,
            *unresolved,
            *(line_id for _suffix, line_id in suffix),
        ]

    ordered_line_ids: list[str] = []
    seen_line_ids: set[str] = set()
    contributing_sources: list[dict] = []
    def insert_candidate_line_id(line_id: str, candidate_line_ids: list[str], candidate_index: int) -> bool:
        if line_id in seen_line_ids:
            return False
        insert_at = len(ordered_line_ids)
        previous_anchor = next(
            (
                candidate_line_ids[index]
                for index in range(candidate_index - 1, -1, -1)
                if candidate_line_ids[index] in seen_line_ids
            ),
            "",
        )
        next_anchor = next(
            (
                candidate_line_ids[index]
                for index in range(candidate_index + 1, len(candidate_line_ids))
                if candidate_line_ids[index] in seen_line_ids
            ),
            "",
        )
        if previous_anchor and next_anchor:
            positions = {existing_id: idx for idx, existing_id in enumerate(ordered_line_ids)}
            previous_index = positions.get(previous_anchor)
            next_index = positions.get(next_anchor)
            if previous_index is not None and next_index is not None and previous_index < next_index:
                insert_at = previous_index + 1
        seen_line_ids.add(line_id)
        ordered_line_ids.insert(insert_at, line_id)
        return True

    for candidate in candidates:
        added_line_ids: list[str] = []
        candidate_line_ids = candidate["matchedLineIds"]
        for candidate_index, line_id in enumerate(candidate_line_ids):
            if insert_candidate_line_id(line_id, candidate_line_ids, candidate_index):
                added_line_ids.append(line_id)
        if added_line_ids:
            contributing_sources.append({
                **candidate,
                "addedLineIds": added_line_ids,
            })
    uncovered_line_ids = [
        line_id for line_id in available_line_ids
        if line_id not in seen_line_ids
    ]
    ordered_line_ids = merge_uncovered_line_ids(ordered_line_ids, uncovered_line_ids)
    boundary_stitch_line_ids: list[str] = []
    covered_suffixes = [
        suffix
        for suffix in (line_suffix(line_id) for line_id in seen_line_ids)
        if suffix is not None
    ]
    if covered_suffixes and all_available_line_suffixes_unique():
        min_covered_suffix = min(covered_suffixes)
        max_covered_suffix = max(covered_suffixes)
        boundary_stitch_line_ids = [
            line_id
            for line_id in uncovered_line_ids
            if (
                (suffix := line_suffix(line_id)) is not None
                and (suffix < min_covered_suffix or suffix > max_covered_suffix)
            )
        ]
        if boundary_stitch_line_ids:
            boundary_stitch_line_id_set = set(boundary_stitch_line_ids)
            ordered_boundary_stitch_line_ids = [
                line_id
                for line_id in ordered_line_ids
                if line_id in boundary_stitch_line_id_set
            ]
            contributing_sources.append({
                "kind": "numericBoundaryStitch",
                "sourceKey": conv_key,
                "file": "DialogTextTable.rowId",
                "matchedLineIds": ordered_boundary_stitch_line_ids,
                "addedLineIds": ordered_boundary_stitch_line_ids,
                "coverage": len(ordered_boundary_stitch_line_ids),
                "priority": 9,
            })
    numeric_stitch = False
    if (
        contributing_sources
        and contributing_sources[0]["kind"] == "dialogTree"
        and contributing_sources[0]["coverage"] < len(available_set)
        and suffixes_are_strictly_monotonic(contributing_sources[0]["matchedLineIds"])
        and all_available_line_suffixes_unique()
    ):
        stitched_ids = suffix_sorted_available_line_ids()
        if set(stitched_ids) == available_set:
            ordered_line_ids = stitched_ids
            numeric_stitch = True

    debug = {
        "mode": (
            "authoredNumericStitch"
            if numeric_stitch
            else ("authoredBlend" if len(contributing_sources) > 1 else contributing_sources[0]["kind"])
        ),
        "originalLineIds": available_line_ids,
        "orderedLineIds": ordered_line_ids,
        "sources": [
            {
                "kind": candidate["kind"],
                "sourceKey": candidate["sourceKey"],
                "file": candidate["file"],
                "coverage": candidate["coverage"],
                "matchedLineIds": candidate["matchedLineIds"],
                "addedLineIds": candidate["addedLineIds"],
            }
            for candidate in contributing_sources
        ],
    }
    if numeric_stitch:
        debug["stitch"] = "lineIdSuffixGaps"
    elif boundary_stitch_line_ids:
        debug["stitch"] = "numericBoundaryLines"
    return ordered_line_ids, debug


def _filter_dialog_tree_line_graph_for_scene(graph: dict, conv_key: str, available_line_ids: set[str]) -> dict:
    nodes = [node for node in (graph.get("nodes") or []) if isinstance(node, dict) and node.get("id")]
    edges = [edge for edge in (graph.get("edges") or []) if isinstance(edge, dict)]
    if not nodes:
        return {}
    by_id = {str(node.get("id")): node for node in nodes}

    def node_scene_signal(node: dict) -> bool:
        line_id = str(node.get("lineId") or "")
        if line_id and (line_id in available_line_ids or _dialog_tree_scene_prefix(line_id) == conv_key):
            return True
        for option_id in node.get("optionIds") or []:
            if _dialog_tree_option_prefix(str(option_id or "")) == conv_key:
                return True
        return False

    included = {node_id for node_id, node in by_id.items() if node_scene_signal(node)}
    if not included:
        return {
            "nodes": nodes,
            "edges": edges,
        }

    def is_connector(node_id: str) -> bool:
        node = by_id.get(node_id) or {}
        return not node.get("lineId") and not node.get("optionIds")

    changed = True
    while changed:
        changed = False
        for edge in edges:
            src = str(edge.get("from") or "")
            dst = str(edge.get("to") or "")
            if not src or not dst:
                continue
            if src in included and dst not in included and is_connector(dst):
                included.add(dst)
                changed = True
            if dst in included and src not in included and is_connector(src):
                included.add(src)
                changed = True

    return {
        "nodes": [node for node in nodes if str(node.get("id") or "") in included],
        "edges": [
            edge
            for edge in edges
            if str(edge.get("from") or "") in included and str(edge.get("to") or "") in included
        ],
    }


def build_dialog_tree_line_graph_payload(conv_key: str, original_line_ids: list[str]) -> dict | None:
    available_line_ids = {line_id for line_id in original_line_ids if line_id}
    sources: list[dict] = []
    seen_sources: set[tuple[str, str, str]] = set()
    covered_line_ids: set[str] = set()
    covered_option_ids: set[str] = set()

    def add_source(meta: dict | None, kind: str, require_new_signal: bool = False) -> bool:
        if not meta:
            return False
        graph = meta.get("lineGraph") or {}
        if not graph.get("nodes"):
            return False
        source_key = meta.get("sourceKey") or ""
        file = meta.get("file") or ""
        identity = (kind, source_key, file)
        if identity in seen_sources:
            return False
        filtered_graph = _filter_dialog_tree_line_graph_for_scene(graph, conv_key, available_line_ids)
        if not filtered_graph.get("nodes"):
            return False
        scene_line_ids = _unique_preserve([
            str(node.get("lineId") or "")
            for node in filtered_graph.get("nodes") or []
            if str(node.get("lineId") or "") in available_line_ids
            or _dialog_tree_scene_prefix(str(node.get("lineId") or "")) == conv_key
        ])
        scene_option_ids = _unique_preserve([
            str(option_id or "")
            for node in filtered_graph.get("nodes") or []
            for option_id in (node.get("optionIds") or [])
            if _dialog_tree_option_prefix(str(option_id or "")) == conv_key
        ])
        if not scene_line_ids and not scene_option_ids and source_key != conv_key:
            return False
        if require_new_signal and not (
            any(line_id not in covered_line_ids for line_id in scene_line_ids)
            or any(option_id not in covered_option_ids for option_id in scene_option_ids)
        ):
            return False
        seen_sources.add(identity)
        covered_line_ids.update(scene_line_ids)
        covered_option_ids.update(scene_option_ids)
        source_payload = {
            "kind": kind,
            "sourceKey": source_key,
            "file": file,
            "nodes": filtered_graph.get("nodes") or [],
            "edges": filtered_graph.get("edges") or [],
        }
        if scene_line_ids:
            source_payload["lineIds"] = scene_line_ids
        if scene_option_ids:
            source_payload["optionIds"] = scene_option_ids
        sources.append(source_payload)
        return True

    direct_added = add_source(_load_dialog_tree_file(conv_key), "dialogTree")
    if direct_added and (not available_line_ids or available_line_ids.issubset(covered_line_ids)):
        return {"sources": sources}
    for meta in _load_related_dialog_tree_files(conv_key, original_line_ids):
        add_source(meta, "dialogTree", require_new_signal=True)
    for fragment in load_dialog_tree_fragments(conv_key):
        source_key = fragment.get("sourceKey") or ""
        if source_key:
            add_source(_load_dialog_tree_source(source_key), "dialogTreeFragment", require_new_signal=True)

    if not sources:
        return None
    return {"sources": sources}


def build_dialog_tree_fragment_payload(conv_key: str) -> list[dict]:
    fragments = load_dialog_tree_fragments(conv_key)
    out: list[dict] = []
    for fragment in fragments:
        option_groups: list[dict] = []
        if fragment.get("optionGroups"):
            for raw_group in fragment.get("optionGroups") or []:
                group = {
                    "optionIds": raw_group.get("optionIds") or [],
                }
                if raw_group.get("after"):
                    group["after"] = raw_group["after"]
                if raw_group.get("mode"):
                    group["mode"] = raw_group["mode"]
                if raw_group.get("branches"):
                    group["branches"] = raw_group["branches"]
                if raw_group.get("merge"):
                    group["merge"] = raw_group["merge"]
                if raw_group.get("position"):
                    group["position"] = raw_group["position"]
                if raw_group.get("_debug"):
                    group["_debug"] = raw_group["_debug"]
                option_groups.append(group)
        else:
            grouped_option_ids: dict[str, list[str]] = defaultdict(list)
            for opt_id, after in (fragment.get("after") or {}).items():
                if after:
                    grouped_option_ids[after].append(opt_id)
            for after in sorted(grouped_option_ids):
                opt_ids = _unique_preserve(grouped_option_ids[after])
                group = {
                    "after": after,
                    "optionIds": opt_ids,
                }
                branch_map = {
                    opt_id: fragment["branches"][opt_id]
                    for opt_id in opt_ids
                    if opt_id in (fragment.get("branches") or {})
                }
                if branch_map:
                    group["branches"] = branch_map
                merge_map = {
                    opt_id: fragment["merge"][opt_id]
                    for opt_id in opt_ids
                    if opt_id in (fragment.get("merge") or {})
                }
                if merge_map:
                    group["merge"] = merge_map
                option_groups.append(group)

            pre_opt_ids = [
                opt_id
                for opt_id in (fragment.get("pre") or [])
                if opt_id and opt_id not in (fragment.get("after") or {})
            ]
            if pre_opt_ids:
                option_groups.append({
                    "position": "pre",
                    "optionIds": _unique_preserve(pre_opt_ids),
                })

        out.append({
            "sourceKey": fragment.get("sourceKey") or "",
            "file": fragment.get("file") or "",
            "lineIds": fragment.get("lineIds") or [],
            "optionGroups": option_groups,
            "terminalCounts": fragment.get("terminalCounts") or {},
            "sceneSpan": bool(fragment.get("sceneSpan")),
            "sourceSceneKeys": fragment.get("sourceSceneKeys") or [],
            "_debug": {
                "source": {
                    "targetKey": conv_key,
                    "sourceKey": fragment.get("sourceKey") or "",
                    "file": fragment.get("file") or "",
                },
            },
        })
    return out


def _line_ids_are_subsequence(subset: list[str], superset: list[str]) -> bool:
    if not subset or len(subset) >= len(superset):
        return False
    pos = 0
    for line_id in superset:
        if line_id == subset[pos]:
            pos += 1
            if pos == len(subset):
                return True
    return False


def _scene_link_option_dedupe_key(link: dict, option: dict) -> tuple:
    path_line_ids = [str(line_id or "") for line_id in (option.get("pathLineIds") or []) if line_id]
    first_line_id = str(option.get("firstLineId") or (path_line_ids[0] if path_line_ids else ""))
    return (
        str(link.get("after") or ""),
        str(option.get("optionId") or ""),
        first_line_id,
        str(option.get("firstSceneKey") or ""),
        bool(option.get("terminal")),
        str(option.get("outcomeKind") or ""),
        bool(option.get("loop")),
        tuple(str(scene_key or "") for scene_key in (option.get("sceneKeys") or []) if scene_key),
        tuple(str(scene_key or "") for scene_key in (option.get("submenuSceneKeys") or []) if scene_key),
    )


def _dedupe_overlapped_scene_link_paths(links: list[dict]) -> list[dict]:
    """Drop lower-coverage duplicate option paths from overlapping source files.

    DialogTree fragments can describe the same local option route from two
    extracted files. When the option identity and anchor match, and one
    pathLineIds sequence is a strict subsequence of another, the longer path has
    strictly more row coverage and should be the rendered evidence.
    """
    if not links:
        return links
    options_by_key: dict[tuple, list[tuple[int, int, list[str]]]] = defaultdict(list)
    for link_index, link in enumerate(links):
        for option_index, option in enumerate(link.get("options") or []):
            if not isinstance(option, dict):
                continue
            path_line_ids = [
                str(line_id or "")
                for line_id in (option.get("pathLineIds") or [])
                if line_id
            ]
            if not path_line_ids:
                continue
            options_by_key[_scene_link_option_dedupe_key(link, option)].append(
                (link_index, option_index, path_line_ids)
            )
    redundant: set[tuple[int, int]] = set()
    exact_paths_seen: set[tuple[tuple, tuple[str, ...]]] = set()
    for link_index, link in enumerate(links):
        for option_index, option in enumerate(link.get("options") or []):
            if not isinstance(option, dict):
                continue
            path_line_ids = tuple(
                str(line_id or "")
                for line_id in (option.get("pathLineIds") or [])
                if line_id
            )
            if not path_line_ids:
                continue
            exact_key = (_scene_link_option_dedupe_key(link, option), path_line_ids)
            if exact_key in exact_paths_seen:
                redundant.add((link_index, option_index))
            else:
                exact_paths_seen.add(exact_key)
    for entries in options_by_key.values():
        if len(entries) < 2:
            continue
        for link_index, option_index, path_line_ids in entries:
            if any(
                _line_ids_are_subsequence(path_line_ids, other_path_line_ids)
                for other_link_index, other_option_index, other_path_line_ids in entries
                if (other_link_index, other_option_index) != (link_index, option_index)
            ):
                redundant.add((link_index, option_index))
    if not redundant:
        return links
    out: list[dict] = []
    for link_index, link in enumerate(links):
        options = [
            option
            for option_index, option in enumerate(link.get("options") or [])
            if (link_index, option_index) not in redundant
        ]
        if not options:
            continue
        if len(options) == len(link.get("options") or []):
            out.append(link)
            continue
        updated = dict(link)
        updated["options"] = options
        out.append(updated)
    return out


def build_dialog_tree_scene_link_payload(conv_key: str) -> list[dict]:
    links = load_dialog_tree_scene_links(conv_key)
    out: list[dict] = []
    for link in links:
        options: list[dict] = []
        seen_option_entries: set[str] = set()
        for opt in link.get("options") or []:
            entry = {
                "optionId": opt.get("optionId") or "",
            }
            for key in ("firstLineId", "firstSceneKey", "terminal"):
                if opt.get(key):
                    entry[key] = opt[key]
            for key in ("pathLineIds", "sceneKeys", "submenuSceneKeys"):
                if opt.get(key):
                    entry[key] = opt[key]
            if opt.get("outcomeKind"):
                entry["outcomeKind"] = opt["outcomeKind"]
            if opt.get("loop"):
                entry["loop"] = opt["loop"]
            if opt.get("_debug"):
                entry["_debug"] = opt["_debug"]
            signature = json.dumps(entry, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            if signature in seen_option_entries:
                continue
            seen_option_entries.add(signature)
            options.append(entry)
        out.append({
            "sourceKey": link.get("sourceKey") or "",
            "file": link.get("file") or "",
            "after": link.get("after") or "",
            "options": options,
            "sceneSpan": bool(link.get("sceneSpan")),
            "sourceSceneKeys": link.get("sourceSceneKeys") or [],
            "_debug": {
                "source": {
                    "targetKey": conv_key,
                    "sourceKey": link.get("sourceKey") or "",
                    "file": link.get("file") or "",
                },
                "link": link.get("_debug") or {},
            },
        })
    return _dedupe_overlapped_scene_link_paths(out)


__all__ = [name for name in globals() if not name.startswith("__")]




