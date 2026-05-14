from __future__ import annotations

from .context import *
from .anime_assets import *

def _node_short_type(node: dict) -> str:
    t = node.get("$type", "")
    return t.split(",", 1)[0].rsplit(".", 1)[-1]


def _scene_graph_runtime_payload_key(
    payload_text: str,
    mission_id: str,
    dialog_key_resolver,
) -> str:
    if not payload_text:
        return ""
    if scene_key := _resolve_payload_scene_key(payload_text, mission_id, dialog_key_resolver):
        return scene_key
    if payload_text.startswith(f"remotecomm_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"radio_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"black_{mission_id}_"):
        return payload_text
    if payload_text.startswith(f"cutscene_{mission_id}_"):
        return payload_text
    if canonical_cutscene := _canonical_cutscene_key(payload_text):
        if f"_{mission_id}_" in f"_{canonical_cutscene}_":
            return canonical_cutscene
    if payload_text.startswith((f"dlg_{mission_id}_", f"sns_{mission_id}_", f"misc_dlg_{mission_id}_")):
        return payload_text
    if re.match(r"^[A-Za-z0-9]+_q#.+$", payload_text):
        return payload_text
    if payload_text.startswith("TpForLs_"):
        return payload_text
    if payload_text.startswith("cs_video_"):
        return payload_text
    if re.match(r"^#[0-9a-fA-F]{8}$", payload_text):
        return payload_text
    if re.match(r"^(?:map|dung|indie|main)[0-9A-Za-z_]*$", payload_text):
        return payload_text
    if (
        payload_text.endswith("_default")
        or "_map" in payload_text
        or "_dung" in payload_text
        or "_indie" in payload_text
        or "_main" in payload_text
    ):
        return payload_text
    return payload_text


def _scene_graph_node_kind(node_key: str, available_keys: set[str] | None = None) -> str:
    available_keys = available_keys or set()
    if node_key.startswith("ui:"):
        return "ui"
    if node_key.startswith("remotecomm_"):
        return "remotecomm"
    if node_key.startswith("radio_"):
        return "radio"
    if node_key.startswith("black_"):
        return "black"
    if node_key.startswith("cutscene_") or _canonical_cutscene_key(node_key):
        return "cutscene"
    if node_key.startswith("sns_"):
        return "sns"
    if node_key.startswith("misc_"):
        return "misc"
    if node_key.startswith("dlg_"):
        return "dlg" if node_key in available_keys else "runtimeDialog"
    if re.match(r"^[A-Za-z0-9]+_q#.+$", node_key):
        return "levelscriptQuest"
    if node_key.startswith("TpForLs_"):
        return "levelscriptTeleport"
    if node_key.startswith("cs_video_"):
        return "levelscriptVideo"
    if re.match(r"^#[0-9a-fA-F]{8}$", node_key):
        return "levelscriptHash"
    if re.match(r"^(?:map|dung|indie|main)[0-9A-Za-z_]*$", node_key):
        return "levelscriptLevel"
    if (
        node_key.endswith("_default")
        or "_map" in node_key
        or "_dung" in node_key
        or "_indie" in node_key
        or "_main" in node_key
    ):
        return "levelscriptProxy"
    if node_key:
        return "levelscriptSymbol"
    return "runtime"


def _is_story_scene_graph_kind(kind: str) -> bool:
    return kind in MISSION_SCENE_ENTRY_KINDS


def _is_story_scene_graph_key(node_key: str, available_keys: set[str] | None = None) -> bool:
    return _is_story_scene_graph_kind(_scene_graph_node_kind(node_key, available_keys))


def _compact_scene_graph_sequence(
    sequence: list[str],
    available_keys: set[str] | None = None,
) -> list[str]:
    out: list[str] = []
    for node_key in sequence:
        if not _is_story_scene_graph_key(node_key, available_keys):
            continue
        if not out or out[-1] != node_key:
            out.append(node_key)
    return out


def _refine_scene_graph_order(
    node_keys: set[str],
    edges: list[dict],
    base_order_map: dict[str, int],
    available_keys: set[str] | None = None,
) -> dict[str, int]:
    available_keys = available_keys or set()
    succs: dict[str, list[str]] = defaultdict(list)
    edge_specs: list[tuple[str, str, str]] = []
    for edge in edges:
        src = edge.get("from") or ""
        dst = edge.get("to") or ""
        kind = edge.get("kind") or ""
        if not src or not dst or src == dst:
            continue
        if src not in node_keys or dst not in node_keys:
            continue
        succs[src].append(dst)
        edge_specs.append((src, dst, kind))
    for key in node_keys:
        succs.setdefault(key, [])

    tight_edge_kinds = {
        "questSequence",
        "questFailGuard",
        "authoredDirect",
        "authoredMenu",
        "levelscriptSceneChain",
    }
    order_hints: dict[str, float] = {
        key: float(order)
        for key, order in base_order_map.items()
        if key in node_keys
    }
    for _ in range(max(1, len(node_keys))):
        changed = False
        for src, dst, kind in edge_specs:
            is_tight = kind in tight_edge_kinds
            if src in order_hints and (is_tight or dst not in base_order_map):
                candidate = order_hints[src] + 0.25
                current = order_hints.get(dst)
                if current is None or candidate < current:
                    order_hints[dst] = candidate
                    changed = True
            if dst in order_hints and (is_tight or src not in base_order_map):
                candidate = order_hints[dst] - 0.25
                current = order_hints.get(src)
                if current is None or candidate < current:
                    order_hints[src] = candidate
                    changed = True
        if not changed:
            break

    def base_sort_key(key: str) -> tuple:
        return (
            order_hints.get(key, 10**9),
            _scene_graph_node_kind(key, available_keys),
            key,
        )

    index_counter = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[list[str]] = []

    def strongconnect(node_key: str) -> None:
        nonlocal index_counter
        indices[node_key] = index_counter
        lowlinks[node_key] = index_counter
        index_counter += 1
        stack.append(node_key)
        on_stack.add(node_key)

        for next_key in succs.get(node_key, []):
            if next_key not in indices:
                strongconnect(next_key)
                lowlinks[node_key] = min(lowlinks[node_key], lowlinks[next_key])
            elif next_key in on_stack:
                lowlinks[node_key] = min(lowlinks[node_key], indices[next_key])

        if lowlinks[node_key] != indices[node_key]:
            return

        component: list[str] = []
        while stack:
            cur = stack.pop()
            on_stack.remove(cur)
            component.append(cur)
            if cur == node_key:
                break
        component.sort(key=base_sort_key)
        components.append(component)

    for key in sorted(node_keys, key=base_sort_key):
        if key not in indices:
            strongconnect(key)

    component_index_by_key: dict[str, int] = {}
    for idx, component in enumerate(components):
        for key in component:
            component_index_by_key[key] = idx

    comp_succs: dict[int, set[int]] = defaultdict(set)
    indegree: dict[int, int] = {idx: 0 for idx in range(len(components))}
    for src, dsts in succs.items():
        src_idx = component_index_by_key[src]
        for dst in dsts:
            dst_idx = component_index_by_key[dst]
            if src_idx == dst_idx or dst_idx in comp_succs[src_idx]:
                continue
            comp_succs[src_idx].add(dst_idx)
            indegree[dst_idx] += 1

    ready = sorted(
        (idx for idx, degree in indegree.items() if degree == 0),
        key=lambda idx: tuple(base_sort_key(key) for key in components[idx]),
    )
    ordered: list[str] = []
    while ready:
        comp_idx = ready.pop(0)
        ordered.extend(components[comp_idx])
        for next_idx in sorted(comp_succs.get(comp_idx, set())):
            indegree[next_idx] -= 1
            if indegree[next_idx] == 0:
                ready.append(next_idx)
        ready.sort(key=lambda idx: tuple(base_sort_key(key) for key in components[idx]))

    if len(ordered) < len(node_keys):
        emitted = set(ordered)
        for component in sorted(components, key=lambda comp: tuple(base_sort_key(key) for key in comp)):
            for key in component:
                if key not in emitted:
                    emitted.add(key)
                    ordered.append(key)

    return {
        key: order
        for order, key in enumerate(ordered)
    }


def _detect_scene_graph_entries(
    nodes: list[dict],
    edges: list[dict],
    quest_scene_meta: dict[str, dict],
    chain_start_meta: dict[str, dict],
    order_map: dict[str, int],
    graph_order_map: dict[str, int],
    available_keys: set[str] | None = None,
) -> dict | None:
    available_keys = available_keys or set()
    scene_nodes = [
        node for node in nodes
        if _is_story_scene_graph_kind(str(node.get("kind") or ""))
    ]
    if not scene_nodes:
        return None

    entry_edge_kinds = {
        "questSequence",
        "questPrev",
        "questFailGuard",
        "authoredDirect",
        "authoredMenu",
        "levelscriptSceneChain",
    }
    incoming_kinds: dict[str, set[str]] = defaultdict(set)
    outgoing_kinds: dict[str, set[str]] = defaultdict(set)
    incoming_count: Counter = Counter()
    outgoing_count: Counter = Counter()
    for edge in edges:
        src = edge.get("from") or ""
        dst = edge.get("to") or ""
        kind = edge.get("kind") or ""
        if kind not in entry_edge_kinds:
            continue
        if not _is_story_scene_graph_key(src, available_keys):
            continue
        if not _is_story_scene_graph_key(dst, available_keys):
            continue
        incoming_count[dst] += 1
        outgoing_count[src] += 1
        incoming_kinds[dst].add(kind)
        outgoing_kinds[src].add(kind)

    scene_node_keys = [
        str(node.get("key") or "")
        for node in scene_nodes
        if str(node.get("key") or "")
    ]
    connected_scene_keys = [
        key
        for key in scene_node_keys
        if incoming_count.get(key, 0) or outgoing_count.get(key, 0)
    ]
    graph_order_first_key = (
        min(
            connected_scene_keys,
            key=lambda key: (
                graph_order_map.get(key, 10**9),
                order_map.get(key, 10**9),
                key,
            ),
        )
        if connected_scene_keys
        else ""
    )

    candidates: list[dict] = []
    for node in scene_nodes:
        key = str(node.get("key") or "")
        if not key:
            continue
        quest_meta = quest_scene_meta.get(key) or {}
        chain_meta = chain_start_meta.get(key) or {}
        root_quest_ids = list(quest_meta.get("rootQuestIds") or [])
        quest_ids = list(quest_meta.get("questIds") or [])
        flow_indices = sorted({
            int(idx)
            for idx in (quest_meta.get("flowIndices") or [])
            if isinstance(idx, int | float) or (isinstance(idx, str) and idx.isdigit())
        })
        chain_files = list(chain_meta.get("sourceFiles") or [])
        chain_levels = list(chain_meta.get("levelIds") or [])
        chain_positions = sorted({
            int(pos)
            for pos in (chain_meta.get("positions") or [])
            if isinstance(pos, int | float) or (isinstance(pos, str) and str(pos).isdigit())
        })
        zero_incoming = incoming_count.get(key, 0) == 0
        reasons: list[str] = []
        if root_quest_ids:
            reasons.append("rootQuest")
        if quest_ids and not reasons:
            reasons.append("questStart")
        if key == graph_order_first_key:
            reasons.append("graphOrderFirst")
        if chain_files:
            reasons.append("levelscriptStart")
        if zero_incoming:
            reasons.append("zeroIncoming")
        if not reasons:
            continue

        if root_quest_ids:
            confidence = "high"
        elif quest_ids or (chain_files and zero_incoming):
            confidence = "medium"
        elif key == graph_order_first_key and (
            incoming_kinds.get(key) or outgoing_kinds.get(key)
        ):
            confidence = "medium"
        else:
            confidence = "low"

        candidates.append({
            "key": key,
            "kind": node.get("kind") or _scene_graph_node_kind(key, available_keys),
            "confidence": confidence,
            "reasons": reasons,
            "rootQuestIds": root_quest_ids,
            "questIds": quest_ids,
            "flowIndices": flow_indices,
            "sourceFiles": chain_files,
            "levelIds": chain_levels,
            "incomingKinds": sorted(incoming_kinds.get(key, set())),
            "outgoingKinds": sorted(outgoing_kinds.get(key, set())),
            "zeroIncoming": zero_incoming,
            "_rank": (
                0 if root_quest_ids else 1,
                flow_indices[0] if flow_indices else 10**9,
                0 if quest_ids else 1,
                0 if key == graph_order_first_key else 1,
                0 if zero_incoming else 1,
                0 if chain_files else 1,
                chain_positions[0] if chain_positions else 10**9,
                graph_order_map.get(key, 10**9),
                order_map.get(key, 10**9),
                key,
            ),
        })

    if not candidates:
        fallback = min(
            scene_nodes,
            key=lambda node: (
                graph_order_map.get(str(node.get("key") or ""), 10**9),
                order_map.get(str(node.get("key") or ""), 10**9),
                str(node.get("key") or ""),
            ),
        )
        fallback_key = str(fallback.get("key") or "")
        if not fallback_key:
            return None
        return {
            "primaryEntryKey": fallback_key,
            "entryNodes": [{
                "key": fallback_key,
                "kind": fallback.get("kind") or _scene_graph_node_kind(fallback_key, available_keys),
                "confidence": "low",
                "reasons": ["graphOrderFallback"],
                "incomingKinds": sorted(incoming_kinds.get(fallback_key, set())),
                "outgoingKinds": sorted(outgoing_kinds.get(fallback_key, set())),
                "zeroIncoming": incoming_count.get(fallback_key, 0) == 0,
            }],
        }

    candidates.sort(key=lambda item: item["_rank"])
    entry_nodes = []
    for rank, item in enumerate(candidates):
        payload = {k: v for k, v in item.items() if not k.startswith("_")}
        payload["rank"] = rank
        entry_nodes.append(payload)
    return {
        "primaryEntryKey": entry_nodes[0]["key"],
        "entryNodes": entry_nodes,
    }


__all__ = [name for name in globals() if not name.startswith("__")]
