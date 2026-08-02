from __future__ import annotations

import hashlib
from functools import lru_cache

from .context import *


_DIALOG_TREE_TYPE = "Beyond.Gameplay.DialogTree"
_DIALOG_NARRATIVE_MASK_ACTION_TYPE = (
    "Beyond.Gameplay.DialogNarrativeMaskActionData"
)
_DIALOG_COMPLEX_NARRATIVE_MASK_ACTION_TYPE = (
    "Beyond.Gameplay.DialogComplexNarrativeMaskActionData"
)
_DIALOG_LEFT_SUBTITLE_ACTION_TYPE = (
    "Beyond.Gameplay.DialogLeftSubtitleActionData"
)
_DIALOG_TREE_OPEN_UI_NODE_TYPE = "Beyond.Gameplay.DialogTreeOpenUINode"
_DIALOG_TREE_FINISH_NODE_TYPE = "Beyond.Gameplay.DialogTreeFinishNode"
_DIALOG_OPEN_UI_ACTION_TYPE = "Beyond.Gameplay.DialogOpenUIAction"
_DIALOG_TREE_IF_NODE_TYPE = "Beyond.Gameplay.DialogTreeIfNode"
_DIALOG_TREE_BRANCH_NODE_TYPE = "Beyond.Gameplay.DialogTreeBranchNode"
_DIALOG_TREE_TRUNK_NODE_TYPE = "Beyond.Gameplay.DialogTreeTrunkNode"
_DIALOG_TREE_DIALOG_NODE_TYPE = "Beyond.Gameplay.DialogTreeDialogNode"
_DIALOG_TREE_CONNECTION_TYPE = "Beyond.Gameplay.DialogTreeConnection"
_CHECK_QUEST_STATE_TYPE = "Beyond.Gameplay.CheckQuestState"
_DIALOG_TREE_TRUNK_LINE_RE = re.compile(r"^(?P<story>.+)_(?P<line>[0-9]+)$")
_ANIME_TREE_MONO_INDEX_PATTERNS = (
    "dlg_*.json",
    "env_*.json",
    "misc_*.json",
    "sns_*.json",
    "black_*.json",
    "radio_*.json",
    "remotecomm_*.json",
    "dlgtl_*.json",
    "f_dlgtl_*.json",
    "m_dlgtl_*.json",
    "cs_*.json",
    "f_cs_*.json",
    "m_cs_*.json",
    "cutscene_*.json",
    "f_cutscene_*.json",
    "m_cutscene_*.json",
)
_ANIME_TREE_COMPLETE_MONO_PREFIXES = tuple(
    pattern[:-6]
    for pattern in _ANIME_TREE_MONO_INDEX_PATTERNS
)
_ANIME_TREE_PATH_INDEX: dict[str, Path] | None = None
_ANIME_TREE_SORTED_STEMS: list[str] | None = None


def _anime_tree_logical_stem(path: Path) -> str:
    return path_id_export_base_stem(path.stem)


def _find_anime_tree_path(filename: str) -> Path:
    requested = Path(filename).stem
    path_index = _get_anime_tree_path_index()
    path = path_index.get(requested)
    if path is None and not requested.startswith(_ANIME_TREE_COMPLETE_MONO_PREFIXES):
        # PathID-preserving exports append ``_p<hex>`` to the authored stem.
        # A prefix-constrained Win32 lookup lets NTFS find that exact asset in
        # the million-file MonoBehaviour directory without rebuilding a full
        # directory index. Filter by logical stem so prefix siblings cannot be
        # selected accidentally.
        for candidate in _iter_anime_tree_files(f"{requested}*.json"):
            if (
                candidate.name.endswith("_extra_config.json")
                or _anime_tree_logical_stem(candidate) != requested
            ):
                continue
            path = candidate
            path_index[requested] = candidate
            if _ANIME_TREE_SORTED_STEMS is not None:
                insert_at = bisect_left(_ANIME_TREE_SORTED_STEMS, requested)
                if (
                    insert_at == len(_ANIME_TREE_SORTED_STEMS)
                    or _ANIME_TREE_SORTED_STEMS[insert_at] != requested
                ):
                    _ANIME_TREE_SORTED_STEMS.insert(insert_at, requested)
            break
    if path is not None:
        return path
    fallback = (
        ANIME_RESOURCE_DIRS[0]
        if ANIME_RESOURCE_DIRS
        else EXPORT_ROOT / "recovered" / "AnimeStudio-cli" / "__missing_resource_dir__"
    )
    return fallback / "__missing_path_id_export__" / filename


@lru_cache(maxsize=None)
def _anime_tree_files(pattern: str) -> tuple[Path, ...]:
    # A Story build asks for hundreds of exact authored object names in
    # addition to the broad dialog/Timeline families.  A small LRU repeatedly
    # evicted those broad results and forced NTFS to search million-object
    # MonoBehaviour folders again.  Export inputs are immutable for the life
    # of one builder process, so retaining the compact path tuples is safe.
    seen: set[str] = set()
    files: list[Path] = []
    for base in ANIME_RESOURCE_DIRS:
        if not base.exists():
            continue
        for path in fast_glob_files(base, pattern):
            if not _anime_tree_logical_stem(path):
                continue
            if path.name in seen:
                continue
            seen.add(path.name)
            files.append(path)
    return tuple(files)


def _iter_anime_tree_files(pattern: str):
    yield from _anime_tree_files(pattern)


def _get_anime_tree_path_index() -> dict[str, Path]:
    global _ANIME_TREE_PATH_INDEX, _ANIME_TREE_SORTED_STEMS
    if _ANIME_TREE_PATH_INDEX is None:
        index: dict[str, Path] = {}
        seen: set[str] = set()
        for base in ANIME_RESOURCE_DIRS:
            if not base.exists():
                continue
            # Dialog trees and their referenced TextAssets use arbitrary
            # authored names, so keep the complete (small) TextAsset index.
            # A current full MonoBehaviour export contains more than a million
            # files; only dialog roots need prefix discovery there. Other
            # MonoBehaviour assets are resolved lazily by exact authored name
            # in ``_find_anime_tree_path`` below.
            patterns = (
                ("*.json",)
                if base.name.casefold() == "textasset"
                else _ANIME_TREE_MONO_INDEX_PATTERNS
            )
            for pattern in patterns:
                for path in fast_glob_files(base, pattern):
                    if path.name in seen:
                        continue
                    seen.add(path.name)
                    if path.name.endswith("_extra_config.json"):
                        continue
                    logical_stem = _anime_tree_logical_stem(path)
                    if logical_stem:
                        index.setdefault(logical_stem, path)
        _ANIME_TREE_PATH_INDEX = index
        _ANIME_TREE_SORTED_STEMS = sorted(index.keys())
    return _ANIME_TREE_PATH_INDEX


def _iter_sorted_stems_with_prefix(sorted_stems: list[str], prefix: str):
    index = bisect_left(sorted_stems, prefix)
    while index < len(sorted_stems):
        stem = sorted_stems[index]
        if not stem.startswith(prefix):
            break
        yield stem
        index += 1


def _iter_related_dialog_tree_paths(conv_key: str):
    seen: set[str] = set()
    exact_stems = [conv_key]
    prefix_stems = [conv_key]
    if conv_key.startswith("dlg_"):
        bare = conv_key[4:]
        if bare not in exact_stems:
            exact_stems.append(bare)
        if bare not in prefix_stems:
            prefix_stems.append(bare)
        if bare.startswith("blackbox_"):
            gpl = f"dlg_gpl_{bare}"
            if gpl not in exact_stems:
                exact_stems.append(gpl)
            if gpl not in prefix_stems:
                prefix_stems.append(gpl)

    path_index = _get_anime_tree_path_index()
    for stem in exact_stems:
        path = path_index.get(stem)
        if path is None:
            continue
        key = str(path).lower()
        if key in seen:
            continue
        seen.add(key)
        yield path
    all_stems = _ANIME_TREE_SORTED_STEMS or sorted(path_index.keys())
    for stem in prefix_stems:
        prefix = f"{stem}_"
        for candidate_stem in _iter_sorted_stems_with_prefix(all_stems, prefix):
            path = path_index[candidate_stem]
            key = str(path).lower()
            if key in seen:
                continue
            seen.add(key)
            yield path


@lru_cache(maxsize=8192)
def _load_anime_resource_payload(path: Path):
    try:
        with path.open(encoding="utf-8-sig") as f:
            payload = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None

    if not isinstance(payload, dict):
        return payload

    script = payload.get("m_Script")
    if not isinstance(script, str) or not script:
        return payload

    try:
        decoded = base64.b64decode(script)
        decoded_text = decoded.decode("utf-8-sig")
        decoded_payload = json.loads(decoded_text)
    except (ValueError, binascii.Error, UnicodeDecodeError, json.JSONDecodeError):
        return payload

    if isinstance(decoded_payload, dict):
        asset_name = str(payload.get("Name") or payload.get("m_Name") or "").strip()
        if asset_name:
            decoded_payload = dict(decoded_payload)
            decoded_payload["_assetName"] = asset_name

    return decoded_payload


def extract_dialog_tree_definition_evidence(
    payload: dict,
    dialog_key: str,
) -> dict | None:
    """Return exact typed definition facts for one authored DialogTree root.

    This is definition and internal-graph evidence only.  It does not prove
    which mission action starts the dialog, but it is sufficient to distinguish
    a real DialogTree objective from a genuinely missing Timeline/DialogTree
    carrier.
    """
    dialog_key = str(dialog_key or "").strip()
    if (
        not dialog_key
        or not isinstance(payload, dict)
        or payload.get("type") != _DIALOG_TREE_TYPE
        or str(payload.get("_assetName") or "").strip() != dialog_key
    ):
        return None
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return None

    node_type_counts: dict[str, int] = {}
    line_ids: list[str] = []
    line_id_by_node_id: dict[str, str] = {}
    node_type_by_id: dict[str, str] = {}
    option_ids: list[str] = []
    runtime_option_types: list[str] = []
    option_group_count = 0
    branching_option_group_count = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = str(node.get("$type") or "").strip()
        node_id = str(node.get("$id") or "").strip()
        if node_id and node_type:
            node_type_by_id[node_id] = node_type
        if node_type:
            short_type = node_type.rsplit(".", 1)[-1]
            node_type_counts[short_type] = node_type_counts.get(short_type, 0) + 1
        if node_type == _DIALOG_TREE_TRUNK_NODE_TYPE:
            actor_data = node.get("_actorNodeData")
            trunk_data = (
                actor_data.get("mfTrunkActionData")
                if isinstance(actor_data, dict)
                else None
            )
            line_id = str(
                (trunk_data.get("_trunkId") or "")
                if isinstance(trunk_data, dict)
                else ""
            ).strip()
            if line_id and line_id not in line_ids:
                line_ids.append(line_id)
            if node_id and line_id:
                line_id_by_node_id[node_id] = line_id
        if node_type == "Beyond.Gameplay.DialogTreeOptionNode":
            for option in node.get("_normalOptions") or []:
                if not isinstance(option, dict):
                    continue
                option_type = str(option.get("$type") or "").strip()
                if option_type and option_type not in runtime_option_types:
                    runtime_option_types.append(option_type)
            authored_options = [
                str(row.get("_optionId") or "").strip()
                for row in (node.get("_normalOptions") or [])
                if isinstance(row, dict) and str(row.get("_optionId") or "").strip()
            ]
            if authored_options:
                option_group_count += 1
                if len(authored_options) > 1:
                    branching_option_group_count += 1
            for option_id in authored_options:
                if option_id not in option_ids:
                    option_ids.append(option_id)

    typed_connections: list[tuple[str, str]] = []
    for row in connections:
        if (
            not isinstance(row, dict)
            or row.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
            or not isinstance(row.get("_sourceNode"), dict)
            or not isinstance(row.get("_targetNode"), dict)
            or row["_sourceNode"].get("$ref") is None
            or row["_targetNode"].get("$ref") is None
        ):
            continue
        typed_connections.append((
            str(row["_sourceNode"]["$ref"]),
            str(row["_targetNode"]["$ref"]),
        ))
    incoming_node_ids = {target for _source, target in typed_connections}
    line_connections = [
        {
            "fromLineId": line_id_by_node_id[source],
            "toLineId": line_id_by_node_id[target],
            "sourceNodeId": source,
            "targetNodeId": target,
        }
        for source, target in typed_connections
        if source in line_id_by_node_id and target in line_id_by_node_id
    ]
    entry_line_ids = [
        line_id_by_node_id[node_id]
        for node_id in line_id_by_node_id
        if node_id not in incoming_node_ids
    ]
    terminal_line_ids = [
        line_id_by_node_id[source]
        for source, target in typed_connections
        if (
            source in line_id_by_node_id
            and node_type_by_id.get(target, "").endswith(
                ".DialogTreeFinishNode"
            )
        )
    ]
    return {
        "sceneKey": dialog_key,
        "assetName": dialog_key,
        "assetType": _DIALOG_TREE_TYPE,
        "lineIds": line_ids,
        "optionIds": option_ids,
        "runtimeOptionTypes": runtime_option_types,
        "nodeCount": sum(node_type_counts.values()),
        "nodeTypeCounts": dict(sorted(node_type_counts.items())),
        "connectionCount": len(typed_connections),
        "lineConnections": line_connections,
        "entryLineIds": entry_line_ids,
        "terminalLineIds": terminal_line_ids,
        "nonLineConnectionCount": (
            len(typed_connections) - len(line_connections)
        ),
        "optionGroupCount": option_group_count,
        "branchingOptionGroupCount": branching_option_group_count,
        "evidenceKind": "exact_dialog_tree_definition",
        "activationBoundary": (
            "the MissionRuntime condition observes this DialogTree root; the "
            "definition does not identify the client action that starts it"
        ),
        "orderBoundary": (
            "DialogTree node/connection order is internal to this dialog and "
            "does not create a cross-file mission chronology edge"
        ),
    }


@lru_cache(maxsize=8192)
def _recover_dialog_tree_definition_evidence(dialog_key: str) -> dict | None:
    path = _find_anime_tree_path(f"{dialog_key}.json")
    if not path.is_file():
        return None
    payload = _load_anime_resource_payload(path)
    evidence = extract_dialog_tree_definition_evidence(payload, dialog_key)
    if evidence is None:
        return None
    return {
        **evidence,
        "sourceFile": repo_rel(path),
        "sourcePathId": path_id_export_path_id(path.stem),
        "sourceSha256": hashlib.sha256(path.read_bytes()).hexdigest().upper(),
        "sourceType": "AnimeStudio TextAsset/DialogTree",
    }


def recover_dialog_tree_definition_evidence(dialog_key: str) -> dict | None:
    """Load one exact current-game DialogTree definition with provenance."""
    evidence = _recover_dialog_tree_definition_evidence(str(dialog_key or "").strip())
    return dict(evidence) if isinstance(evidence, dict) else None


def _iter_dialog_tree_action_slots(payload: dict):
    """Yield only the authored DialogTree action containers proved by native types."""

    if payload.get("type") != _DIALOG_TREE_TYPE:
        return
    nodes = payload.get("nodes")
    if not isinstance(nodes, list):
        return

    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        # DialogTreeConnection references nodes by their managed-reference
        # `$id`. Nodes without one are unreachable authoring leftovers and
        # cannot be treated as runtime containment evidence.
        node_id = str(node.get("$id") or "").strip()
        if not node_id:
            continue
        actor_data = node.get("_actorNodeData")
        if isinstance(actor_data, dict):
            actor_actions = actor_data.get("actions")
            if isinstance(actor_actions, list):
                for action_index, action in enumerate(actor_actions):
                    if isinstance(action, dict):
                        yield (
                            f"nodes[{node_index}]._actorNodeData.actions[{action_index}]",
                            action,
                            node_id,
                        )
            actor_groups = actor_data.get("actionGroups")
            if isinstance(actor_groups, list):
                for group_index, action_group in enumerate(actor_groups):
                    if not isinstance(action_group, dict):
                        continue
                    grouped_actions = action_group.get("actions")
                    if not isinstance(grouped_actions, list):
                        continue
                    for action_index, action in enumerate(grouped_actions):
                        if isinstance(action, dict):
                            yield (
                                "nodes[{}]._actorNodeData.actionGroups[{}].actions[{}]".format(
                                    node_index,
                                    group_index,
                                    action_index,
                                ),
                                action,
                                node_id,
                            )

        transition_data = node.get("_transitionData")
        if not isinstance(transition_data, dict):
            continue

        actions = transition_data.get("actions")
        if isinstance(actions, list):
            for action_index, action in enumerate(actions):
                if isinstance(action, dict):
                    yield (
                        f"nodes[{node_index}]._transitionData.actions[{action_index}]",
                        action,
                        node_id,
                    )

        action_groups = transition_data.get("_actionGroups")
        if not isinstance(action_groups, list):
            continue
        for group_index, action_group in enumerate(action_groups):
            if not isinstance(action_group, dict):
                continue
            grouped_actions = action_group.get("actions")
            if not isinstance(grouped_actions, list):
                continue
            for action_index, action in enumerate(grouped_actions):
                if isinstance(action, dict):
                        yield (
                            "nodes[{}]._transitionData._actionGroups[{}].actions[{}]".format(
                                node_index,
                                group_index,
                                action_index,
                            ),
                            action,
                            node_id,
                        )


def _dialog_tree_immediate_trunk_contexts(payload: dict) -> dict[str, dict]:
    """Return exact one-edge trunk neighbors for addressable DialogTree nodes.

    The serialized ``connections`` graph is authoritative here. Node array
    order and editor positions are deliberately ignored. A placement is exact
    only when the action node has one incoming and one outgoing typed
    connection and both adjacent nodes are typed trunk nodes with nonempty
    ``_trunkId`` values.
    """
    if payload.get("type") != _DIALOG_TREE_TYPE:
        return {}
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return {}

    node_by_id: dict[str, dict] = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("$id") in (None, ""):
            continue
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return {}
        node_by_id[node_id] = node
    if not node_by_id:
        return {}
    prime_node = nodes[0] if nodes else None
    prime_node_id = (
        str(prime_node.get("$id"))
        if isinstance(prime_node, dict)
        and prime_node.get("$id") not in (None, "")
        else ""
    )
    if not prime_node_id or prime_node_id not in node_by_id:
        return {}

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    sources_by_target: dict[str, list[str]] = defaultdict(list)
    edge_rows: list[dict] = []
    for connection_index, connection in enumerate(connections):
        if (
            not isinstance(connection, dict)
            or connection.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
        ):
            return {}
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = (
            str(source.get("$ref") or "")
            if isinstance(source, dict)
            else ""
        )
        target_id = (
            str(target.get("$ref") or "")
            if isinstance(target, dict)
            else ""
        )
        if source_id not in node_by_id or target_id not in node_by_id:
            return {}
        targets_by_source[source_id].append(target_id)
        sources_by_target[target_id].append(source_id)
        edge_rows.append({
            "index": connection_index,
            "sourceNodeId": source_id,
            "targetNodeId": target_id,
            "type": _DIALOG_TREE_CONNECTION_TYPE,
        })

    edge_by_pair = {
        (row["sourceNodeId"], row["targetNodeId"]): row
        for row in edge_rows
    }

    def shortest_prime_path(target_id: str) -> list[str]:
        paths: dict[str, list[str]] = {
            prime_node_id: [prime_node_id],
        }
        pending = deque([prime_node_id])
        while pending:
            source_id = pending.popleft()
            if source_id == target_id:
                return paths[source_id]
            for next_id in targets_by_source.get(source_id) or []:
                if next_id in paths:
                    continue
                paths[next_id] = [*paths[source_id], next_id]
                pending.append(next_id)
        return []

    def trunk_id(node_id: str) -> str:
        node = node_by_id.get(node_id)
        if not isinstance(node, dict) or node.get("$type") != _DIALOG_TREE_TRUNK_NODE_TYPE:
            return ""
        actor_data = node.get("_actorNodeData")
        trunk_data = (
            actor_data.get("mfTrunkActionData")
            if isinstance(actor_data, dict)
            else None
        )
        return (
            str(trunk_data.get("_trunkId") or "").strip()
            if isinstance(trunk_data, dict)
            else ""
        )

    out: dict[str, dict] = {}
    for node_id in node_by_id:
        incoming_ids = sources_by_target.get(node_id) or []
        outgoing_ids = targets_by_source.get(node_id) or []
        preceding_trunks = [
            value
            for adjacent_id in incoming_ids
            if (value := trunk_id(adjacent_id))
        ]
        following_trunks = [
            value
            for adjacent_id in outgoing_ids
            if (value := trunk_id(adjacent_id))
        ]
        node_path = shortest_prime_path(node_id)
        predecessor_is_entry_path_tail = (
            len(incoming_ids) == 1
            and len(node_path) >= 2
            and node_path[-2] == incoming_ids[0]
        )
        exact = (
            len(incoming_ids) == 1
            and len(outgoing_ids) == 1
            and len(preceding_trunks) == 1
            and len(following_trunks) == 1
            and predecessor_is_entry_path_tail
        )
        out[node_id] = {
            "dialogTreeConnectionPlacementStatus": (
                "exact_unique_adjacent_trunks"
                if exact
                else "not_exact_unique_adjacent_trunks"
            ),
            "incomingNodeIds": list(incoming_ids),
            "outgoingNodeIds": list(outgoing_ids),
            "primeNodeId": prime_node_id,
            "reachableFromPrimeNode": bool(node_path),
            "primeToActionNodePath": node_path,
            "primeToActionConnectionPath": [
                edge_by_pair[(source_id, target_id)]
                for source_id, target_id in zip(
                    node_path,
                    node_path[1:],
                )
            ],
            "immediatelyPrecedingTrunkIds": preceding_trunks,
            "immediatelyFollowingTrunkIds": following_trunks,
            "adjacentConnectionRows": [
                row
                for row in edge_rows
                if (
                    row["sourceNodeId"] == node_id
                    or row["targetNodeId"] == node_id
                )
            ],
        }
    return out


def _extract_dialog_tree_narrative_mask_actions(payload: dict) -> list[dict]:
    """Extract exact LangKey references from typed narrative-mask actions.

    This deliberately does not recursively search JSON.  Only the action
    containers, concrete action types, and fields recovered from the current
    native binary are accepted as attachment evidence.
    """

    out: list[dict] = []
    trunk_contexts = _dialog_tree_immediate_trunk_contexts(payload)
    for action_path, action, node_id in _iter_dialog_tree_action_slots(payload):
        action_type = str(action.get("$type") or "")
        if action_type == _DIALOG_NARRATIVE_MASK_ACTION_TYPE:
            text_rows = action.get("texts")
            action_kind = "narrative"
        elif action_type == _DIALOG_COMPLEX_NARRATIVE_MASK_ACTION_TYPE:
            text_rows = action.get("textDataList")
            action_kind = "complex_narrative"
        else:
            continue
        if not isinstance(text_rows, list):
            continue

        for text_index, text_row in enumerate(text_rows):
            if not isinstance(text_row, dict):
                continue
            if action_kind == "narrative":
                text_id = str(text_row.get("key") or "").strip()
            else:
                lang_key = text_row.get("langKey")
                text_id = (
                    str(lang_key.get("key") or "").strip()
                    if isinstance(lang_key, dict)
                    else ""
                )
            if not text_id:
                continue

            record = {
                "textId": text_id,
                "actionType": action_type,
                "actionKind": action_kind,
                "actionPath": action_path,
                "nodeId": node_id,
                "textIndex": text_index,
                **(
                    trunk_contexts.get(node_id)
                    or {
                        "dialogTreeConnectionPlacementStatus":
                            "connection_graph_unavailable"
                    }
                ),
            }
            for timing_field in (
                "duration",
                "textBeforeTime",
                "textAfterTime",
                "isMainAction",
            ):
                if action.get(timing_field) is not None:
                    record[timing_field] = action[timing_field]
            if action_kind == "complex_narrative":
                custom_text = str(text_row.get("customText") or "").strip()
                if custom_text:
                    record["customText"] = custom_text
                if text_row.get("textBeforeTime") is not None:
                    record["textBeforeTime"] = text_row["textBeforeTime"]
            out.append(record)
    return out


def _extract_dialog_tree_left_subtitle_actions(payload: dict) -> list[dict]:
    """Extract exact LangKeys from the native left-subtitle action payload.

    The current binary exposes four fixed ``LangKey`` fields.  This is local
    dialog UI presentation, not NarrativeBlackScreen/trunk/audio playback, so
    callers must retain the distinct relation when adding mission context.
    """
    out: list[dict] = []
    for action_path, action, node_id in _iter_dialog_tree_action_slots(payload):
        if str(action.get("$type") or "") != _DIALOG_LEFT_SUBTITLE_ACTION_TYPE:
            continue
        for text_index, field_name in enumerate(("text1", "text2", "text3", "text4")):
            lang_key = action.get(field_name)
            if not isinstance(lang_key, dict):
                continue
            text_id = str(lang_key.get("key") or "").strip()
            if not text_id:
                continue
            record = {
                "textId": text_id,
                "actionType": _DIALOG_LEFT_SUBTITLE_ACTION_TYPE,
                "actionKind": "left_subtitle",
                "actionPath": action_path,
                "nodeId": node_id,
                "textIndex": text_index,
                "textField": field_name,
            }
            for timing_field in ("textStayTime", "duration"):
                if action.get(timing_field) is not None:
                    record[timing_field] = action[timing_field]
            out.append(record)
    return out


def _extract_dialog_tree_open_ui_actions(payload: dict) -> list[dict]:
    """Extract exact action-only Open UI terminals from a typed DialogTree."""
    if payload.get("type") != _DIALOG_TREE_TYPE:
        return []
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return []
    node_by_id = {
        str(node.get("$id")): node
        for node in nodes
        if isinstance(node, dict) and node.get("$id") not in (None, "")
    }
    targets_by_source: dict[str, list[str]] = defaultdict(list)
    for connection in connections:
        if not isinstance(connection, dict):
            continue
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = str(source.get("$ref") or "") if isinstance(source, dict) else ""
        target_id = str(target.get("$ref") or "") if isinstance(target, dict) else ""
        if source_id and target_id:
            targets_by_source[source_id].append(target_id)

    out: list[dict] = []
    for node_index, node in enumerate(nodes):
        if (
            not isinstance(node, dict)
            or node.get("$type") != _DIALOG_TREE_OPEN_UI_NODE_TYPE
        ):
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData")
        if (
            not node_id
            or not isinstance(action, dict)
            or action.get("$type") != _DIALOG_OPEN_UI_ACTION_TYPE
        ):
            continue
        target_ids = targets_by_source.get(node_id) or []
        if not target_ids or any(
            (node_by_id.get(target_id) or {}).get("$type")
            != _DIALOG_TREE_FINISH_NODE_TYPE
            for target_id in target_ids
        ):
            continue
        raw_param = str(action.get("param") or "").strip()
        parsed_param: dict = {}
        if raw_param:
            try:
                candidate = json.loads(raw_param)
            except json.JSONDecodeError:
                candidate = None
            if isinstance(candidate, dict):
                parsed_param = candidate
        finish_ids = sorted({
            int((node_by_id[target_id]).get("finishId") or 0)
            for target_id in target_ids
            if isinstance((node_by_id.get(target_id) or {}).get("finishId", 0), int)
        })
        out.append({
            "nodeId": node_id,
            "nodeIndex": node_index,
            "nodeType": _DIALOG_TREE_OPEN_UI_NODE_TYPE,
            "actionType": _DIALOG_OPEN_UI_ACTION_TYPE,
            "actionEnum": action.get("actionEnum"),
            "panelType": action.get("panelType"),
            "param": raw_param,
            "paramData": parsed_param,
            "finishIds": finish_ids,
            "terminalKind": "open_ui",
        })
    return out


def _extract_dialog_tree_open_ui_content_actions(payload: dict) -> list[dict]:
    """Extract typed OpenUI content consumers with exact graph boundaries.

    Unlike ``_extract_dialog_tree_open_ui_actions``, this includes inline
    OpenUI nodes.  It does not infer a Story target from the parameter string;
    the caller must resolve the exact popup id through its typed source table.
    """
    if payload.get("type") != _DIALOG_TREE_TYPE:
        return []
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return []

    node_by_id: dict[str, dict] = {}
    for node in nodes:
        if not isinstance(node, dict) or node.get("$id") in (None, ""):
            return []
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return []
        node_by_id[node_id] = node
    if not node_by_id:
        return []
    prime_node_id = str(nodes[0].get("$id") or "")
    if not prime_node_id:
        return []

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    sources_by_target: dict[str, list[str]] = defaultdict(list)
    for connection in connections:
        if (
            not isinstance(connection, dict)
            or connection.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
        ):
            return []
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = str(source.get("$ref") or "") if isinstance(source, dict) else ""
        target_id = str(target.get("$ref") or "") if isinstance(target, dict) else ""
        if source_id not in node_by_id or target_id not in node_by_id:
            return []
        targets_by_source[source_id].append(target_id)
        sources_by_target[target_id].append(source_id)

    reachable: set[str] = set()
    pending = deque([prime_node_id])
    while pending:
        node_id = pending.popleft()
        if node_id in reachable:
            continue
        reachable.add(node_id)
        pending.extend(targets_by_source.get(node_id) or [])

    def trunk_id(node_id: str) -> str:
        node = node_by_id.get(node_id) or {}
        if node.get("$type") != _DIALOG_TREE_TRUNK_NODE_TYPE:
            return ""
        actor_data = node.get("_actorNodeData")
        trunk_data = (
            actor_data.get("mfTrunkActionData")
            if isinstance(actor_data, dict) else None
        )
        return (
            str(trunk_data.get("_trunkId") or "").strip()
            if isinstance(trunk_data, dict) else ""
        )

    def unique_forward_trunk(start_ids: list[str]) -> str:
        if len(start_ids) != 1:
            return ""
        node_id = start_ids[0]
        seen: set[str] = set()
        while node_id and node_id not in seen:
            seen.add(node_id)
            line_id = trunk_id(node_id)
            if line_id:
                return line_id
            targets = targets_by_source.get(node_id) or []
            if len(targets) != 1:
                return ""
            node_id = targets[0]
        return ""

    out: list[dict] = []
    for node_index, node in enumerate(nodes):
        if node.get("$type") != _DIALOG_TREE_OPEN_UI_NODE_TYPE:
            continue
        node_id = str(node.get("$id") or "")
        action = node.get("_actionData")
        if (
            not node_id
            or not isinstance(action, dict)
            or action.get("$type") != _DIALOG_OPEN_UI_ACTION_TYPE
        ):
            continue
        raw_param = str(action.get("param") or "").strip()
        try:
            parsed_param = json.loads(raw_param) if raw_param else None
        except json.JSONDecodeError:
            parsed_param = None
        if not isinstance(parsed_param, dict):
            parsed_param = {}

        incoming_ids = sources_by_target.get(node_id) or []
        outgoing_ids = targets_by_source.get(node_id) or []
        after_ids = [
            line_id for adjacent_id in incoming_ids
            if (line_id := trunk_id(adjacent_id))
        ]
        before_ids = [
            line_id for adjacent_id in outgoing_ids
            if (line_id := trunk_id(adjacent_id))
        ]
        placement_status = "not_exact_story_boundary"
        if (
            node_id in reachable
            and len(incoming_ids) == len(outgoing_ids) == 1
            and len(after_ids) == len(before_ids) == 1
        ):
            placement_status = "exact_between_adjacent_parent_trunks"
        elif (
            node_id in reachable
            and len(incoming_ids) == len(outgoing_ids) == 1
            and len(after_ids) == 1
            and not before_ids
            and (node_by_id.get(outgoing_ids[0]) or {}).get("$type")
            == _DIALOG_TREE_FINISH_NODE_TYPE
        ):
            placement_status = "exact_after_parent_trunk_at_finish"
        elif (
            node_id == prime_node_id
            and not incoming_ids
            and len(outgoing_ids) == 1
        ):
            first_line_id = unique_forward_trunk(outgoing_ids)
            if first_line_id:
                before_ids = [first_line_id]
                placement_status = "exact_prime_entry_before_parent_trunk"

        out.append({
            "nodeId": node_id,
            "nodeIndex": node_index,
            "nodeType": _DIALOG_TREE_OPEN_UI_NODE_TYPE,
            "actionType": _DIALOG_OPEN_UI_ACTION_TYPE,
            "actionEnum": action.get("actionEnum"),
            "panelType": action.get("panelType"),
            "param": raw_param,
            "paramData": parsed_param,
            "readingPopupId": str(parsed_param.get("id") or "").strip(),
            "incomingNodeIds": list(incoming_ids),
            "outgoingNodeIds": list(outgoing_ids),
            "reachableFromPrimeNode": node_id in reachable,
            "embeddedAfterLineIds": after_ids,
            "embeddedBeforeLineIds": before_ids,
            "dialogTreeConnectionPlacementStatus": placement_status,
            "nativeMappingId":
                "dialog-tree-open-ui-reading-popup-connection-native-v1",
        })
    return out


def _extract_dialog_tree_quest_state_dependencies(
    payload: dict,
    dialog_key: str,
) -> list[dict]:
    """Extract typed active-component CheckQuestState dialog dependencies.

    A same-asset quest string is not sufficient.  The condition node must be
    connected through authored DialogTreeConnection edges to a trunk whose
    exact ``_trunkId`` belongs to the current registered dialog root.  This
    rejects isolated authoring leftovers such as dlg_e1m7_5's alternate root.
    """
    if payload.get("type") != _DIALOG_TREE_TYPE or not dialog_key:
        return []
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return []
    node_by_id: dict[str, tuple[int, dict]] = {}
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            return []
        if node.get("$id") in (None, ""):
            # Current authored assets contain isolated editor remnants without
            # an addressable id. They cannot participate in a serialized edge
            # or this condition-to-current-trunk reachability proof.
            continue
        node_id = str(node.get("$id"))
        if node_id in node_by_id:
            return []
        node_by_id[node_id] = (node_index, node)
    targets_by_source: dict[str, set[str]] = defaultdict(set)
    sources_by_target: dict[str, set[str]] = defaultdict(set)
    connection_rows: list[dict] = []
    for connection_index, connection in enumerate(connections):
        if (
            not isinstance(connection, dict)
            or connection.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
        ):
            return []
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = str(source.get("$ref") or "") if isinstance(source, dict) else ""
        target_id = str(target.get("$ref") or "") if isinstance(target, dict) else ""
        if source_id not in node_by_id or target_id not in node_by_id:
            return []
        targets_by_source[source_id].add(target_id)
        sources_by_target[target_id].add(source_id)
        connection_rows.append({
            "index": connection_index,
            "sourceNodeId": source_id,
            "targetNodeId": target_id,
            "type": str(connection.get("$type") or ""),
        })

    current_trunks: dict[str, str] = {}
    for node_id, (_node_index, node) in node_by_id.items():
        if node.get("$type") != _DIALOG_TREE_TRUNK_NODE_TYPE:
            continue
        actor_data = node.get("_actorNodeData")
        trunk_action = (
            actor_data.get("mfTrunkActionData")
            if isinstance(actor_data, dict)
            else None
        )
        trunk_id = (
            str(trunk_action.get("_trunkId") or "").strip()
            if isinstance(trunk_action, dict)
            else ""
        )
        if re.fullmatch(rf"{re.escape(dialog_key)}_\d+", trunk_id):
            current_trunks[node_id] = trunk_id
    if not current_trunks:
        return []

    def reachable(start: str, graph: dict[str, set[str]]) -> set[str]:
        seen: set[str] = set()
        pending = list(graph.get(start) or [])
        while pending:
            node_id = pending.pop()
            if node_id in seen:
                continue
            seen.add(node_id)
            pending.extend(graph.get(node_id) or [])
        return seen

    out: list[dict] = []
    for node_id, (node_index, node) in sorted(
        node_by_id.items(),
        key=lambda item: item[1][0],
    ):
        node_type = str(node.get("$type") or "")
        condition_rows: list[tuple[int, dict, str]] = []
        if node_type == _DIALOG_TREE_IF_NODE_TYPE:
            condition_container = node.get("_dialogIfData")
            condition = (
                condition_container.get("condition")
                if isinstance(condition_container, dict)
                else None
            )
            if isinstance(condition, dict):
                condition_rows.append((
                    0,
                    condition,
                    f"nodes[{node_index}]._dialogIfData.condition",
                ))
        elif node_type == _DIALOG_TREE_BRANCH_NODE_TYPE:
            condition_container = node.get("_dialogBranchData")
            conditions = (
                condition_container.get("conditions")
                if isinstance(condition_container, dict)
                else None
            )
            if isinstance(conditions, list):
                condition_rows.extend(
                    (
                        condition_index,
                        condition,
                        (
                            f"nodes[{node_index}]._dialogBranchData.conditions"
                            f"[{condition_index}]"
                        ),
                    )
                    for condition_index, condition in enumerate(conditions)
                    if isinstance(condition, dict)
                )
        else:
            continue

        descendant_ids = reachable(node_id, targets_by_source)
        ancestor_ids = reachable(node_id, sources_by_target)
        descendant_trunks = {
            trunk_node_id: current_trunks[trunk_node_id]
            for trunk_node_id in sorted(descendant_ids & set(current_trunks))
        }
        ancestor_trunks = {
            trunk_node_id: current_trunks[trunk_node_id]
            for trunk_node_id in sorted(ancestor_ids & set(current_trunks))
        }
        if not descendant_trunks and not ancestor_trunks:
            continue
        if not targets_by_source.get(node_id):
            continue

        conditions_by_quest: dict[str, list[dict]] = defaultdict(list)
        for condition_index, condition, condition_path in condition_rows:
            if condition.get("$type") != _CHECK_QUEST_STATE_TYPE:
                continue
            quest_ref = condition.get("_questId")
            target_state_ref = condition.get("_targetQuestState")
            comparer_ref = condition.get("_comparer")
            quest_id = (
                str(quest_ref.get("constValue") or "").strip()
                if isinstance(quest_ref, dict)
                else ""
            )
            target_state = (
                target_state_ref.get("constValue")
                if isinstance(target_state_ref, dict)
                else None
            )
            if not quest_id or isinstance(target_state, bool) or not isinstance(target_state, int):
                continue
            if not isinstance(comparer_ref, dict):
                continue
            if not comparer_ref:
                comparer = 0
                comparer_source = "omitted_serialized_default"
            else:
                if "constValue" not in comparer_ref:
                    continue
                comparer = comparer_ref.get("constValue")
                if isinstance(comparer, bool) or not isinstance(comparer, int):
                    continue
                comparer_source = "serialized_const_value"
            conditions_by_quest[quest_id].append({
                "conditionIndex": condition_index,
                "conditionPath": condition_path,
                "conditionType": _CHECK_QUEST_STATE_TYPE,
                "targetQuestState": target_state,
                "comparer": comparer,
                "comparerSource": comparer_source,
            })

        for quest_id, quest_conditions in sorted(conditions_by_quest.items()):
            out.append({
                "dialogKey": dialog_key,
                "questId": quest_id,
                "nodeId": node_id,
                "nodeIndex": node_index,
                "nodeType": node_type,
                "conditions": quest_conditions,
                "targetQuestStates": sorted({
                    int(row["targetQuestState"])
                    for row in quest_conditions
                }),
                "comparerValues": sorted({
                    int(row["comparer"])
                    for row in quest_conditions
                }),
                "incomingNodeIds": sorted(sources_by_target.get(node_id) or []),
                "outgoingNodeIds": sorted(targets_by_source.get(node_id) or []),
                "ancestorCurrentStoryTrunks": ancestor_trunks,
                "descendantCurrentStoryTrunks": descendant_trunks,
                "currentStoryTrunkNodeIds": sorted(current_trunks),
                "connectionRows": [
                    row
                    for row in connection_rows
                    if (
                        row["sourceNodeId"] == node_id
                        or row["targetNodeId"] == node_id
                    )
                ],
            })
    return out


def _extract_all_leaf_quest_state_condition(
    condition: object,
    condition_path: str,
) -> dict:
    """Decode one quest-state-only condition tree or fail closed.

    ``CombineCondition`` is useful as a cross-Story carrier scope only when
    every recursive leaf is an exact constant ``CheckQuestState``.  A mixed or
    dynamic condition could select the authored branch for reasons unrelated
    to the named quests, so callers must not keep a favorable subset.
    """
    if not isinstance(condition, dict):
        return {}
    condition_type = str(condition.get("$type") or "")
    if condition_type == _CHECK_QUEST_STATE_TYPE:
        quest_ref = condition.get("_questId")
        comparer_ref = condition.get("_comparer")
        state_ref = condition.get("_targetQuestState")
        quest_id = (
            str(quest_ref.get("constValue") or "").strip()
            if isinstance(quest_ref, dict)
            else ""
        )
        target_state = (
            state_ref.get("constValue")
            if isinstance(state_ref, dict)
            else None
        )
        if (
            not quest_id
            or not isinstance(comparer_ref, dict)
            or isinstance(target_state, bool)
            or not isinstance(target_state, int)
        ):
            return {}
        if not comparer_ref:
            comparer = 0
            comparer_source = "omitted_serialized_default"
        else:
            comparer = comparer_ref.get("constValue")
            if isinstance(comparer, bool) or not isinstance(comparer, int):
                return {}
            comparer_source = "serialized_const_value"
        return {
            "conditionType": condition_type,
            "conditionPath": condition_path,
            "questIds": [quest_id],
            "conditions": [{
                "conditionPath": condition_path,
                "conditionType": condition_type,
                "questId": quest_id,
                "comparer": comparer,
                "comparerSource": comparer_source,
                "targetQuestState": target_state,
            }],
            "combineConditions": [],
        }
    if condition_type != "Beyond.Gameplay.CombineCondition":
        return {}
    subconditions = condition.get("subConditions")
    eval_string = condition.get("conditionEvalString")
    if (
        not isinstance(subconditions, list)
        or not subconditions
        or not isinstance(eval_string, str)
        or not eval_string.strip()
    ):
        return {}
    decoded_children: list[dict] = []
    for index, child in enumerate(subconditions):
        decoded = _extract_all_leaf_quest_state_condition(
            child,
            f"{condition_path}.subConditions[{index}]",
        )
        if not decoded:
            return {}
        decoded_children.append(decoded)
    quest_ids = sorted({
        str(quest_id or "")
        for decoded in decoded_children
        for quest_id in decoded.get("questIds") or []
        if quest_id
    })
    if not quest_ids:
        return {}
    return {
        "conditionType": condition_type,
        "conditionPath": condition_path,
        "conditionEvalString": eval_string,
        "questIds": quest_ids,
        "conditions": [
            row
            for decoded in decoded_children
            for row in decoded.get("conditions") or []
        ],
        "combineConditions": [{
            "conditionPath": condition_path,
            "conditionEvalString": eval_string,
            "subConditionCount": len(subconditions),
        }, *[
            row
            for decoded in decoded_children
            for row in decoded.get("combineConditions") or []
        ]],
    }


def _dialog_tree_carrier_quest_state_contexts(
    node_by_id: dict[str, tuple[int, dict]],
    targets_by_source: dict[str, list[str]],
    sources_by_target: dict[str, list[str]],
    carrier_node_id: str,
) -> list[dict]:
    """Return quest-state-only If nodes that dominate one carrier.

    A condition is retained only when the carrier is reachable from a
    serialized graph root and removing that condition makes the carrier
    unreachable from every such root.  This is the explicit no-bypass proof;
    merely sharing a weak component or one favorable path is insufficient.
    """
    roots = sorted(set(node_by_id) - set(sources_by_target))
    if not roots or carrier_node_id not in node_by_id:
        return []

    def can_reach(start_ids: list[str], target_id: str, blocked: str = "") -> bool:
        pending = [node_id for node_id in start_ids if node_id != blocked]
        seen: set[str] = set()
        while pending:
            node_id = pending.pop()
            if node_id == target_id:
                return True
            if node_id in seen or node_id == blocked:
                continue
            seen.add(node_id)
            pending.extend(
                next_id
                for next_id in targets_by_source.get(node_id) or []
                if next_id not in seen and next_id != blocked
            )
        return False

    reaching_roots = [
        root_id
        for root_id in roots
        if can_reach([root_id], carrier_node_id)
    ]
    if not reaching_roots:
        return []
    contexts: list[dict] = []
    for node_id, (node_index, node) in sorted(
        node_by_id.items(),
        key=lambda item: item[1][0],
    ):
        if node.get("$type") != _DIALOG_TREE_IF_NODE_TYPE:
            continue
        # The If node must be on a root-to-carrier path and dominate every
        # root that can reach the carrier. A second root/path around it is a
        # hard veto.
        if not can_reach(reaching_roots, node_id):
            continue
        if can_reach(reaching_roots, carrier_node_id, blocked=node_id):
            continue
        container = node.get("_dialogIfData")
        condition = (
            container.get("condition")
            if isinstance(container, dict)
            else None
        )
        decoded = _extract_all_leaf_quest_state_condition(
            condition,
            f"nodes[{node_index}]._dialogIfData.condition",
        )
        if not decoded:
            continue
        contexts.append({
            **decoded,
            "nodeId": node_id,
            "nodeIndex": node_index,
            "nodeType": _DIALOG_TREE_IF_NODE_TYPE,
            "carrierNodeId": carrier_node_id,
            "entryRootNodeIds": reaching_roots,
            "incomingNodeIds": sorted(sources_by_target.get(node_id) or []),
            "outgoingNodeIds": sorted(targets_by_source.get(node_id) or []),
            "noBypass": True,
            "scopeBoundary": (
                "quest-state branch dependency only; not dialog ownership or "
                "a unique quest playback trigger"
            ),
        })
    return contexts


def _extract_dialog_tree_story_playback_carriers(
    payload: dict,
    dialog_key: str,
    story_keys: set[str],
) -> list[dict]:
    """Extract cross-Story playback carriers anchored to the current dialog.

    The current binary consumes ``DTTrunkNodeData._trunkId`` through
    ``DialogTreeTrunkNode._DoPlayTrunk`` and ``DialogManager.PlayTrunkNode``.
    It separately consumes ``DialogTreeDialogNode._dialogId`` through
    ``DialogTreeDialogNode.DoExecute`` and ``DialogManager.PlayNextDialog``.
    Only directed ancestors or descendants of an exact current-dialog trunk
    anchor are accepted.  Weak-component siblings, generic strings, subtitle
    LangKeys, finish conditions, synthetic ids, and filename similarity are
    not playback evidence.
    """
    if payload.get("type") != _DIALOG_TREE_TYPE or not dialog_key:
        return []
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, list):
        return []

    node_by_id: dict[str, tuple[int, dict]] = {}
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            return []
        if node.get("$id") in (None, ""):
            # Missing-id nodes are inert authoring remnants: no serialized
            # edge can address them, so they cannot be anchors or carriers.
            continue
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return []
        node_by_id[node_id] = (node_index, node)
    if not node_by_id:
        return []

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    sources_by_target: dict[str, list[str]] = defaultdict(list)
    connection_rows: list[dict] = []
    for connection_index, connection in enumerate(connections):
        if (
            not isinstance(connection, dict)
            or connection.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
        ):
            return []
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = str(source.get("$ref") or "") if isinstance(source, dict) else ""
        target_id = str(target.get("$ref") or "") if isinstance(target, dict) else ""
        if source_id not in node_by_id or target_id not in node_by_id:
            return []
        targets_by_source[source_id].append(target_id)
        sources_by_target[target_id].append(source_id)
        connection_rows.append({
            "index": connection_index,
            "sourceNodeId": source_id,
            "targetNodeId": target_id,
            "type": _DIALOG_TREE_CONNECTION_TYPE,
        })

    def shortest_path(
        start_id: str,
        target_id: str,
        neighbors: dict[str, list[str]],
    ) -> list[str]:
        paths: dict[str, list[str]] = {start_id: [start_id]}
        pending = deque([start_id])
        while pending:
            source_id = pending.popleft()
            if source_id == target_id:
                return paths[source_id]
            for next_id in neighbors.get(source_id) or []:
                if next_id in paths:
                    continue
                paths[next_id] = [*paths[source_id], next_id]
                pending.append(next_id)
        return []

    current_parent_trunks: dict[str, str] = {}
    for node_id, (_node_index, node) in node_by_id.items():
        if node.get("$type") != _DIALOG_TREE_TRUNK_NODE_TYPE:
            continue
        actor_data = node.get("_actorNodeData")
        trunk_data = (
            actor_data.get("mfTrunkActionData")
            if isinstance(actor_data, dict)
            else None
        )
        trunk_id = (
            str(trunk_data.get("_trunkId") or "").strip()
            if isinstance(trunk_data, dict)
            else ""
        )
        match = _DIALOG_TREE_TRUNK_LINE_RE.fullmatch(trunk_id)
        if match and match.group("story") == dialog_key:
            current_parent_trunks[node_id] = trunk_id
    if not current_parent_trunks:
        return []

    edge_by_pair: dict[tuple[str, str], dict] = {}
    for row in connection_rows:
        edge_by_pair.setdefault(
            (row["sourceNodeId"], row["targetNodeId"]),
            row,
        )

    accepted_story_keys = set(story_keys)
    out: list[dict] = []
    for node_id, (node_index, node) in sorted(
        node_by_id.items(),
        key=lambda item: item[1][0],
    ):
        node_type = str(node.get("$type") or "")
        trunk_id = ""
        dialog_id = ""
        line_index = None
        if node_type == _DIALOG_TREE_TRUNK_NODE_TYPE:
            actor_data = node.get("_actorNodeData")
            trunk_data = (
                actor_data.get("mfTrunkActionData")
                if isinstance(actor_data, dict)
                else None
            )
            trunk_id = (
                str(trunk_data.get("_trunkId") or "").strip()
                if isinstance(trunk_data, dict)
                else ""
            )
            match = _DIALOG_TREE_TRUNK_LINE_RE.fullmatch(trunk_id)
            if not match:
                continue
            story_key = match.group("story")
            line_index = int(match.group("line"))
            carrier_kind = "trunk"
            carrier_field = "_actorNodeData.mfTrunkActionData._trunkId"
            carrier_value = trunk_id
        elif node_type == _DIALOG_TREE_DIALOG_NODE_TYPE:
            dialog_id = str(node.get("_dialogId") or "").strip()
            if not dialog_id:
                continue
            story_key = dialog_id
            carrier_kind = "dialog"
            carrier_field = "_dialogId"
            carrier_value = dialog_id
        else:
            continue
        if story_key == dialog_key or story_key not in accepted_story_keys:
            continue
        candidate_paths: list[tuple[int, str, str, list[str]]] = []
        for parent_node_id in current_parent_trunks:
            descendant_path = shortest_path(
                parent_node_id,
                node_id,
                targets_by_source,
            )
            if descendant_path:
                candidate_paths.append((
                    len(descendant_path),
                    "parent_to_child",
                    parent_node_id,
                    descendant_path,
                ))
            reverse_ancestor_path = shortest_path(
                parent_node_id,
                node_id,
                sources_by_target,
            )
            ancestor_path = list(reversed(reverse_ancestor_path))
            if ancestor_path:
                candidate_paths.append((
                    len(ancestor_path),
                    "child_to_parent",
                    parent_node_id,
                    ancestor_path,
                ))
        if not candidate_paths:
            continue
        _path_length, reach_direction, parent_node_id, node_path = min(
            candidate_paths,
            key=lambda row: (row[0], row[1], row[2], row[3]),
        )
        out.append({
            "dialogKey": dialog_key,
            "storyKey": story_key,
            "carrierKind": carrier_kind,
            "carrierValue": carrier_value,
            "trunkId": trunk_id,
            "dialogId": dialog_id,
            "lineIndex": line_index,
            "nodeId": node_id,
            "nodeIndex": node_index,
            "nodeType": node_type,
            "carrierField": carrier_field,
            "parentTrunkNodeId": parent_node_id,
            "parentTrunkId": current_parent_trunks.get(parent_node_id, ""),
            "currentParentTrunkNodeIds": sorted(current_parent_trunks),
            "currentParentTrunkIds": sorted(current_parent_trunks.values()),
            "reachDirection": reach_direction,
            "reachableFromCurrentParentTrunk": True,
            "entryProof": "exact_registered_dialog_tree_current_parent_anchor",
            "nodePath": node_path,
            "connectionPath": [
                edge_by_pair[(source_id, target_id)]
                for source_id, target_id in zip(node_path, node_path[1:])
            ],
            "questStateBranchContexts": (
                _dialog_tree_carrier_quest_state_contexts(
                    node_by_id,
                    targets_by_source,
                    sources_by_target,
                    node_id,
                )
            ),
        })
    return out


def _extract_dialog_tree_story_trunk_carriers(
    payload: dict,
    dialog_key: str,
    story_keys: set[str],
) -> list[dict]:
    """Compatibility view containing only typed trunk playback carriers."""
    return [
        row
        for row in _extract_dialog_tree_story_playback_carriers(
            payload,
            dialog_key,
            story_keys,
        )
        if row.get("carrierKind") == "trunk"
    ]


def _extract_dialog_tree_prime_reachable_story_playback_carriers(
    payload: dict,
    dialog_key: str,
    story_keys: set[str],
    authored_text_ids: set[str],
    registered_dialog_keys: set[str],
) -> list[dict]:
    """Return typed Story carriers reachable from serialized ``nodes[0]``.

    Current native ``Graph.get_primeNode`` returns ``allNodes[0]`` and a fresh
    ``DialogTree.OnGraphStarted`` enters that node when no current node is
    already set. This is possible authored playback containment only. It does
    not prove that a MissionRuntime completion condition starts the parent
    dialog, nor does it establish Story ownership or visit order.
    """
    if payload.get("type") != _DIALOG_TREE_TYPE or not dialog_key:
        return []
    nodes = payload.get("nodes")
    connections = payload.get("connections")
    if not isinstance(nodes, list) or not nodes or not isinstance(connections, list):
        return []
    prime_node = nodes[0]
    if not isinstance(prime_node, dict) or prime_node.get("$id") in (None, ""):
        return []
    prime_node_id = str(prime_node["$id"])

    node_by_id: dict[str, tuple[int, dict]] = {}
    for node_index, node in enumerate(nodes):
        if not isinstance(node, dict):
            return []
        if node.get("$id") in (None, ""):
            continue
        node_id = str(node["$id"])
        if node_id in node_by_id:
            return []
        node_by_id[node_id] = (node_index, node)
    if prime_node_id not in node_by_id:
        return []

    targets_by_source: dict[str, list[str]] = defaultdict(list)
    connection_rows: list[dict] = []
    for connection_index, connection in enumerate(connections):
        if (
            not isinstance(connection, dict)
            or connection.get("$type") != _DIALOG_TREE_CONNECTION_TYPE
        ):
            return []
        source = connection.get("_sourceNode")
        target = connection.get("_targetNode")
        source_id = str(source.get("$ref") or "") if isinstance(source, dict) else ""
        target_id = str(target.get("$ref") or "") if isinstance(target, dict) else ""
        if source_id not in node_by_id or target_id not in node_by_id:
            return []
        targets_by_source[source_id].append(target_id)
        connection_rows.append({
            "index": connection_index,
            "sourceNodeId": source_id,
            "targetNodeId": target_id,
            "type": _DIALOG_TREE_CONNECTION_TYPE,
        })

    edge_by_pair: dict[tuple[str, str], dict] = {}
    for row in connection_rows:
        edge_by_pair.setdefault(
            (row["sourceNodeId"], row["targetNodeId"]),
            row,
        )

    def shortest_prime_path(target_id: str) -> list[str]:
        paths: dict[str, list[str]] = {prime_node_id: [prime_node_id]}
        pending = deque([prime_node_id])
        while pending:
            source_id = pending.popleft()
            if source_id == target_id:
                return paths[source_id]
            for next_id in targets_by_source.get(source_id) or []:
                if next_id in paths:
                    continue
                paths[next_id] = [*paths[source_id], next_id]
                pending.append(next_id)
        return []

    accepted_story_keys = set(story_keys)
    out: list[dict] = []
    for node_id, (node_index, node) in sorted(
        node_by_id.items(),
        key=lambda item: item[1][0],
    ):
        node_type = str(node.get("$type") or "")
        trunk_id = ""
        dialog_id = ""
        line_index = None
        if node_type == _DIALOG_TREE_TRUNK_NODE_TYPE:
            actor_data = node.get("_actorNodeData")
            trunk_data = (
                actor_data.get("mfTrunkActionData")
                if isinstance(actor_data, dict)
                else None
            )
            trunk_id = (
                str(trunk_data.get("_trunkId") or "").strip()
                if isinstance(trunk_data, dict)
                else ""
            )
            match = _DIALOG_TREE_TRUNK_LINE_RE.fullmatch(trunk_id)
            if not match or trunk_id not in authored_text_ids:
                continue
            story_key = match.group("story")
            line_index = int(match.group("line"))
            carrier_kind = "trunk"
            carrier_field = "_actorNodeData.mfTrunkActionData._trunkId"
            carrier_value = trunk_id
        elif node_type == _DIALOG_TREE_DIALOG_NODE_TYPE:
            dialog_id = str(node.get("_dialogId") or "").strip()
            if not dialog_id or dialog_id not in registered_dialog_keys:
                continue
            story_key = dialog_id
            carrier_kind = "dialog"
            carrier_field = "_dialogId"
            carrier_value = dialog_id
        else:
            continue
        if story_key == dialog_key or story_key not in accepted_story_keys:
            continue
        node_path = shortest_prime_path(node_id)
        if not node_path:
            continue
        out.append({
            "dialogKey": dialog_key,
            "storyKey": story_key,
            "carrierKind": carrier_kind,
            "carrierValue": carrier_value,
            "trunkId": trunk_id,
            "dialogId": dialog_id,
            "lineIndex": line_index,
            "nodeId": node_id,
            "nodeIndex": node_index,
            "nodeType": node_type,
            "carrierField": carrier_field,
            "reachDirection": "prime_to_carrier",
            "primeNodeIndex": 0,
            "primeNodeId": prime_node_id,
            "reachableFromPrimeNode": True,
            "entryProof": "exact_registered_dialog_tree_prime_node_reachability",
            "nodePath": node_path,
            "connectionPath": [
                edge_by_pair[(source_id, target_id)]
                for source_id, target_id in zip(node_path, node_path[1:])
            ],
        })
    return out


def recover_dialog_tree_narrative_mask_actions() -> list[dict]:
    """Return native-schema narrative LangKey occurrences from dialog TextAssets."""

    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        if not dialog_key.startswith("dlg_"):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        for record in _extract_dialog_tree_narrative_mask_actions(payload):
            preceding_trunks = [
                str(value)
                for value in record.get("immediatelyPrecedingTrunkIds") or []
                if value
            ]
            following_trunks = [
                str(value)
                for value in record.get("immediatelyFollowingTrunkIds") or []
                if value
            ]
            exact_parent_neighbors = (
                record.get("dialogTreeConnectionPlacementStatus")
                == "exact_unique_adjacent_trunks"
                and len(preceding_trunks) == 1
                and len(following_trunks) == 1
                and all(
                    (
                        match := _DIALOG_TREE_TRUNK_LINE_RE.fullmatch(trunk_id)
                    )
                    and match.group("story") == dialog_key
                    for trunk_id in (*preceding_trunks, *following_trunks)
                )
            )
            placement = {
                "dialogTreeConnectionPlacementStatus": (
                    "exact_unique_adjacent_parent_trunks"
                    if exact_parent_neighbors
                    else "no_exact_unique_adjacent_parent_trunks"
                ),
                "nativeMappingId":
                    "dialog-tree-narrative-mask-connection-native-v1",
                "orderBoundary": (
                    "line-level placement inside the parent DialogTree only; "
                    "the parent Story file contains content on both sides, so "
                    "this does not establish a Story-file edge"
                ),
            }
            if exact_parent_neighbors:
                placement["embeddedAfterLineIds"] = preceding_trunks
                placement["embeddedBeforeLineIds"] = following_trunks
            out.append({
                **record,
                **placement,
                "dialogKey": dialog_key,
                "assetName": asset_name or dialog_key,
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })

    out.sort(key=lambda row: (
        str(row.get("dialogKey") or ""),
        str(row.get("actionPath") or ""),
        int(row.get("textIndex") or 0),
        str(row.get("textId") or ""),
    ))
    return out


def recover_dialog_tree_left_subtitle_actions() -> list[dict]:
    """Return exact native-schema left-subtitle LangKey occurrences."""
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        if not dialog_key.startswith("dlg_"):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        for record in _extract_dialog_tree_left_subtitle_actions(payload):
            out.append({
                **record,
                "dialogKey": dialog_key,
                "assetName": asset_name,
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("dialogKey") or ""),
        str(row.get("actionPath") or ""),
        int(row.get("textIndex") or 0),
        str(row.get("textId") or ""),
    ))
    return out


def recover_dialog_tree_open_ui_actions() -> list[dict]:
    """Return typed Open UI terminals from original DialogTree TextAssets."""
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        if not dialog_key.startswith("dlg_"):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        for record in _extract_dialog_tree_open_ui_actions(payload):
            out.append({
                **record,
                "dialogKey": dialog_key,
                "assetName": asset_name,
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("dialogKey") or ""),
        int(row.get("nodeIndex") or 0),
    ))
    return out


def recover_dialog_tree_open_ui_content_actions() -> list[dict]:
    """Return typed inline and terminal OpenUI consumers from DialogTrees."""
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        if not dialog_key.startswith("dlg_"):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        source_sha256 = hashlib.sha256(path.read_bytes()).hexdigest().upper()
        for record in _extract_dialog_tree_open_ui_content_actions(payload):
            out.append({
                **record,
                "dialogKey": dialog_key,
                "assetName": asset_name,
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceSha256": source_sha256,
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("dialogKey") or ""),
        int(row.get("nodeIndex") or 0),
    ))
    return out


def recover_dialog_tree_quest_state_dependencies(
    dialog_id_registry: dict[str, dict],
) -> list[dict]:
    """Return active registered DialogTree quest-state dependencies."""
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        registry_row = dialog_id_registry.get(dialog_key)
        if (
            not dialog_key.startswith("dlg_")
            or not isinstance(registry_row, dict)
            or registry_row.get("registered") is not True
            or registry_row.get("memoryPackRecordKey") is not True
            or "memorypack_record_key"
            not in (registry_row.get("registrationEvidence") or [])
        ):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        for record in _extract_dialog_tree_quest_state_dependencies(
            payload,
            dialog_key,
        ):
            out.append({
                **record,
                "assetName": asset_name,
                "registeredDialogRoot": True,
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("dialogKey") or ""),
        str(row.get("questId") or ""),
        int(row.get("nodeIndex") or 0),
        str(row.get("sourceFile") or ""),
    ))
    return out


def recover_dialog_tree_story_playback_carriers(
    dialog_id_registry: dict[str, dict],
    story_keys: set[str],
) -> list[dict]:
    """Return exact anchored Story playback carriers from registered DialogTrees."""
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        registry_row = dialog_id_registry.get(dialog_key)
        if (
            not dialog_key.startswith("dlg_")
            or not isinstance(registry_row, dict)
            or registry_row.get("registered") is not True
            or registry_row.get("memoryPackRecordKey") is not True
            or "memorypack_record_key"
            not in (registry_row.get("registrationEvidence") or [])
        ):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        for record in _extract_dialog_tree_story_playback_carriers(
            payload,
            dialog_key,
            story_keys,
        ):
            out.append({
                **record,
                "assetName": asset_name,
                "registeredDialogRoot": True,
                "registrationEvidence": ["memorypack_record_key"],
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("storyKey") or ""),
        str(row.get("dialogKey") or ""),
        int(row.get("nodeIndex") or 0),
        str(row.get("sourceFile") or ""),
    ))
    return out


def recover_dialog_tree_prime_reachable_story_playback_carriers(
    dialog_id_registry: dict[str, dict],
    story_keys: set[str],
    authored_text_ids: set[str],
    eligible_parent_keys: set[str] | None = None,
) -> list[dict]:
    """Return exact prime-reachable carriers from registered DialogTrees."""
    eligible = (
        None if eligible_parent_keys is None else set(eligible_parent_keys)
    )
    out: list[dict] = []
    for path in _iter_anime_tree_files("dlg_*.json"):
        dialog_key = _anime_tree_logical_stem(path)
        if eligible is not None and dialog_key not in eligible:
            continue
        registry_row = dialog_id_registry.get(dialog_key)
        if (
            not dialog_key.startswith("dlg_")
            or not isinstance(registry_row, dict)
            or registry_row.get("registered") is not True
            or registry_row.get("memoryPackRecordKey") is not True
            or "memorypack_record_key"
            not in (registry_row.get("registrationEvidence") or [])
        ):
            continue
        payload = _load_anime_resource_payload(path)
        if not isinstance(payload, dict):
            continue
        asset_name = str(payload.get("_assetName") or "").strip()
        if asset_name != dialog_key:
            continue
        for record in _extract_dialog_tree_prime_reachable_story_playback_carriers(
            payload,
            dialog_key,
            story_keys,
            authored_text_ids,
            set(dialog_id_registry),
        ):
            out.append({
                **record,
                "assetName": asset_name,
                "registeredDialogRoot": True,
                "registrationEvidence": ["memorypack_record_key"],
                "sourceFile": repo_rel(path),
                "sourcePathId": path_id_export_path_id(path.stem),
                "sourceType": "AnimeStudio TextAsset/DialogTree",
            })
    out.sort(key=lambda row: (
        str(row.get("storyKey") or ""),
        str(row.get("dialogKey") or ""),
        int(row.get("nodeIndex") or 0),
        str(row.get("sourceFile") or ""),
    ))
    return out


def recover_dialog_tree_story_trunk_carriers(
    dialog_id_registry: dict[str, dict],
    story_keys: set[str],
) -> list[dict]:
    """Compatibility view containing only typed trunk playback carriers."""
    return [
        row
        for row in recover_dialog_tree_story_playback_carriers(
            dialog_id_registry,
            story_keys,
        )
        if row.get("carrierKind") == "trunk"
    ]


def _dialog_tree_semantic_signature(record: dict) -> str:
    """Return a stable signature for DialogTree evidence, ignoring asset aliases."""

    ignored_keys = {"assetName", "file", "sourceKey"}

    def scrub(value):
        if isinstance(value, dict):
            return {
                key: scrub(value[key])
                for key in sorted(value)
                if key not in ignored_keys
            }
        if isinstance(value, list):
            return [scrub(item) for item in value]
        return value

    return json.dumps(
        scrub(record),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )


def _extract_ref_strings(node, field_names: tuple[str, ...]) -> list[str]:
    return unique_strings(
        value
        for field_name in field_names
        for value in _walk_const_values(node, field_name)
    )


_EMBEDDED_STORY_REF_RE = re.compile(
    r"(?:dlg|sns|cutscene|black|remotecomm|radio)_[A-Za-z0-9_]+"
)
_LEVELDATA_STORY_REF_RE = re.compile(
    rb"\b(?:dlg|sns|cutscene|black|remotecomm|radio)_[A-Za-z0-9_]{2,120}"
)
_LEVELDATA_QUEST_ID_RE = re.compile(
    rb"\b[A-Za-z0-9][A-Za-z0-9_]*_q#[A-Za-z0-9_]+\b"
)
_LEVELDATA_ASCII_RE = re.compile(rb"[ -~]{3,}")
_LEVELDATA_STORY_MISSION_RE = re.compile(r"^([a-z]+\d+m\d+(?:d\d+)?)(?:_|$)", re.I)
_LEVELDATA_PRIORITY_STORY_TYPES = {"e", "a", "gm", "c"}


def _extract_embedded_story_refs(text: str) -> list[str]:
    value = str(text or "")
    if not value:
        return []
    return _unique_preserve(match.group(0) for match in _EMBEDDED_STORY_REF_RE.finditer(value))


def _mission_from_story_ref(ref: str) -> str:
    value = str(ref or "").strip()
    if value.startswith("misc_"):
        value = value[5:]
    for prefix in ("dlg_", "sns_", "cutscene_", "black_", "remotecomm_", "radio_"):
        if not value.startswith(prefix):
            continue
        rest = value[len(prefix):]
        if match := _LEVELDATA_STORY_MISSION_RE.match(rest):
            return match.group(1)
    return ""


def _mission_parent_id(mission_id: str) -> str:
    return re.sub(r"d\d+$", "", str(mission_id or ""))


def _mission_story_type(mission_id: str) -> str:
    match = re.match(r"^([a-z]+)", str(mission_id or "").lower())
    return match.group(1) if match else ""


def _quest_id_mission(quest_id: str) -> str:
    value = str(quest_id or "")
    return value.split("_q#", 1)[0] if "_q#" in value else ""


def _leveldata_story_ref_matches_quest(story_ref: str, quest_id: str) -> bool:
    story_mission = _mission_from_story_ref(story_ref)
    quest_mission = _quest_id_mission(quest_id)
    if not story_mission or not quest_mission:
        return False
    if (
        _mission_story_type(story_mission) not in _LEVELDATA_PRIORITY_STORY_TYPES
        and _mission_story_type(quest_mission) not in _LEVELDATA_PRIORITY_STORY_TYPES
    ):
        return False
    return (
        story_mission == quest_mission
        or story_mission == _mission_parent_id(quest_mission)
        or _mission_parent_id(story_mission) == _mission_parent_id(quest_mission)
    )


def _leveldata_hit_distance(story_start: int, story_end: int, quest_start: int, quest_end: int) -> int:
    if quest_start <= story_start <= quest_end:
        return 0
    return min(abs(quest_start - story_start), abs(quest_end - story_end))


def _leveldata_context_strings(raw: bytes, start: int, end: int) -> list[str]:
    context = raw[max(0, start - 220) : min(len(raw), end + 220)]
    return [
        match.group().decode("ascii", "ignore").strip()
        for match in _LEVELDATA_ASCII_RE.finditer(context)
    ]


def _leveldata_quest_story_refs_by_mission() -> dict[str, dict[str, list[dict]]]:
    global _LEVELDATA_QUEST_STORY_REF_CACHE
    if _LEVELDATA_QUEST_STORY_REF_CACHE is not None:
        return _LEVELDATA_QUEST_STORY_REF_CACHE

    by_mission: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    seen: set[tuple[str, str, str, str]] = set()
    if not LEVELDATA_DIR.is_dir():
        _LEVELDATA_QUEST_STORY_REF_CACHE = {}
        return _LEVELDATA_QUEST_STORY_REF_CACHE

    source_fields = {
        "require_quest",
        "radio_await_start",
        "radio_escape_start",
        "use_level_event_click",
        "level_event_id_click",
        "click_option_name_list",
        "lang_int_trigger_dialog_option",
        "isFinished",
    }

    for path in sorted(LEVELDATA_DIR.rglob("*.json")):
        try:
            raw = read_bytes_cached(path)
        except OSError:
            continue
        story_hits = [
            (match.start(), match.end(), match.group().decode("ascii", "ignore"))
            for match in _LEVELDATA_STORY_REF_RE.finditer(raw)
        ]
        if not story_hits:
            continue
        quest_hits = [
            (match.start(), match.end(), match.group().decode("ascii", "ignore"))
            for match in _LEVELDATA_QUEST_ID_RE.finditer(raw)
        ]
        if not quest_hits:
            continue
        file_ref = repo_rel(path)
        for story_start, story_end, story_ref in story_hits:
            context_start = max(0, story_start - 220)
            context_end = min(len(raw), story_end + 220)
            candidates = [
                (quest_start, quest_end, quest_id)
                for quest_start, quest_end, quest_id in quest_hits
                if context_start <= quest_start < context_end
                and _leveldata_story_ref_matches_quest(story_ref, quest_id)
            ]
            if not candidates:
                continue
            quest_start, quest_end, quest_id = candidates[-1]
            quest_mission = _quest_id_mission(quest_id)
            if not quest_mission:
                continue
            signature = (quest_mission, quest_id, story_ref, file_ref)
            if signature in seen:
                continue
            seen.add(signature)

            strings = _leveldata_context_strings(raw, min(story_start, quest_start), max(story_end, quest_end))
            fields = _unique_preserve(
                text
                for text in strings
                if (
                    text in source_fields
                    or text.startswith((
                        "dlg_",
                        "sns_",
                        "cutscene_",
                        "black_",
                        "remotecomm_",
                        "radio_",
                    ))
                )
            )
            entity = next((text for text in reversed(strings) if text.startswith("int_")), "")
            row = {
                "storyRef": story_ref,
                "questId": quest_id,
                "levelId": path.parent.name,
                "file": file_ref,
                "distance": _leveldata_hit_distance(
                    story_start,
                    story_end,
                    quest_start,
                    quest_end,
                ),
                "storyOffset": story_start,
                "questOffset": quest_start,
                "source": "LevelData quest/story byte-string context",
            }
            if entity:
                row["entity"] = entity
            if fields:
                row["fields"] = fields[:12]
            by_mission[quest_mission][quest_id].append(row)

    _LEVELDATA_QUEST_STORY_REF_CACHE = {
        mission: {
            quest_id: sorted(
                rows,
                key=lambda row: (
                    int(row.get("storyOffset") or 0),
                    str(row.get("storyRef") or ""),
                ),
            )
            for quest_id, rows in sorted(quests.items())
        }
        for mission, quests in sorted(by_mission.items())
    }
    return _LEVELDATA_QUEST_STORY_REF_CACHE


def _leveldata_quest_story_refs_for_mission(mission_id: str) -> dict[str, list[dict]]:
    return _leveldata_quest_story_refs_by_mission().get(str(mission_id or ""), {})


def _quest_area_story_refs(quest: dict) -> list[str]:
    refs: list[str] = []
    for anchor in quest.get("objectiveAnchors") or []:
        for ref in anchor.get("areaStoryRefs") or []:
            if ref and ref not in refs:
                refs.append(ref)
        for leaf in anchor.get("conditionLeaves") or []:
            for ref in leaf.get("areaStoryRefs") or []:
                if ref and ref not in refs:
                    refs.append(ref)
    return refs


def _extract_client_action_refs(raw: dict, field_names: tuple[str, ...]) -> dict[str, list[str]]:
    action_list = (((raw.get("actionMapRaw") or {}).get("dataMap") or {}).get("actionList") or [])
    actions_by_id: dict[int, dict] = {}
    for action in action_list:
        action_id = action.get("_ID")
        if not isinstance(action_id, int):
            continue
        actions_by_id[action_id] = action

    def action_chain_refs(action_id: int) -> list[str]:
        refs: list[str] = []
        seen: set[int] = set()
        current = action_id
        while isinstance(current, int) and current in actions_by_id and current not in seen:
            seen.add(current)
            action = actions_by_id[current]
            for ref in _extract_ref_strings(action, field_names):
                if ref not in refs:
                    refs.append(ref)
            next_id = action.get("_nextID")
            if not isinstance(next_id, int) or next_id < 0:
                break
            current = next_id
        return refs

    out: dict[str, list[str]] = {}
    for key_row, action_id in zip(raw.get("clientActionMapKey") or [], raw.get("clientActionMapValue") or []):
        if not isinstance(key_row, dict) or not isinstance(action_id, int):
            continue
        quest_id = key_row.get("questId")
        if not isinstance(quest_id, str) or not quest_id:
            continue
        refs = action_chain_refs(action_id)
        if not refs:
            continue
        bucket = out.setdefault(quest_id, [])
        for ref in refs:
            if ref not in bucket:
                bucket.append(ref)
    return out


def _condition_short_type(full_type: str) -> str:
    # "Beyond.Gameplay.CheckMissionIntProperty, Gameplay.Beyond" -> "CheckMissionIntProperty"
    head = full_type.split(",", 1)[0]
    return head.rsplit(".", 1)[-1] if head else ""


def _extract_branch_flags(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    out: list[dict] = []
    t = cond.get("$type", "")
    short = _condition_short_type(t)
    if short == "CombineCondition":
        for sub in cond.get("subConditions", []) or []:
            out.extend(_extract_branch_flags(sub))
        return out
    if short == "CheckMissionIntProperty":
        out.append({
            "type": short,
            "key": (cond.get("_key") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_compareValue") or {}).get("constValue"),
        })
        return out
    if short == "CheckQuestState":
        out.append({
            "type": short,
            "key": (cond.get("_questId") or {}).get("constValue"),
            "cmp": (cond.get("_comparer") or {}).get("constValue"),
            "val": (cond.get("_targetQuestState") or {}).get("constValue"),
        })
        return out
    if short:
        # Unknown leaf — surface the type so the UI can still hint at it.
        out.append({"type": short})
    return out


def _combine_eval_string(cond) -> str:
    if not isinstance(cond, dict):
        return ""
    if _condition_short_type(cond.get("$type", "")) == "CombineCondition":
        return cond.get("conditionEvalString", "") or ""
    return ""


def _natural_key(value: str) -> tuple:
    parts = re.findall(r"\d+|\D+", value or "")
    out = []
    for part in parts:
        if part.isdigit():
            out.append((0, int(part)))
        else:
            out.append((1, part))
    return tuple(out)


def _quest_sort_key(q: dict) -> tuple:
    tail = (q.get("id") or "").split("#")[-1]
    return (q.get("flowIndex", 10**9), _natural_key(tail), q.get("id") or "")


def _extract_tracking_hints(quest) -> list[dict]:
    out: list[dict] = []
    seen: set[tuple] = set()
    for objective_index, obj in enumerate(quest.get("objectiveList") or []):
        tracking_rows = [
            (tracking_index, info, {})
            for tracking_index, info in enumerate(obj.get("trackingInfoList") or [])
        ]
        # Objective.GetRuntimeTrackingList selects these authored wrappers when
        # mapTrackingToMultiDesc is true.  Only the exact script-entity shape is
        # promoted into the maintained tracking join; other nested navigation
        # rows stay inert here so they cannot create new Story associations.
        if obj.get("mapTrackingToMultiDesc") is True:
            for multi_description_index, wrapper in enumerate(
                obj.get("multiDescTrackingInfoList") or []
            ):
                if not isinstance(wrapper, dict):
                    continue
                actual_list = wrapper.get("actualList")
                if not isinstance(actual_list, list):
                    continue
                for actual_list_index, info in enumerate(actual_list):
                    if (
                        not isinstance(info, dict)
                        or _condition_short_type(info.get("$type", ""))
                        != "EntityTrackingInfo"
                        or info.get("trackScriptEntity") is not True
                    ):
                        continue
                    tracking_rows.append((
                        actual_list_index,
                        info,
                        {
                            "trackingListSource": (
                                "multiDescTrackingInfoList.actualList"
                            ),
                            "multiDescriptionIndex": multi_description_index,
                            "actualListIndex": actual_list_index,
                        },
                    ))

        for tracking_index, info, provenance in tracking_rows:
            if not isinstance(info, dict):
                continue
            hint: dict = {}
            typ = _condition_short_type(info.get("$type", ""))
            if typ:
                hint["type"] = typ
            scene_id = info.get("sceneId")
            if isinstance(scene_id, str) and scene_id:
                hint["scene"] = scene_id
            npc_proxy_id = info.get("npcProxyId")
            if isinstance(npc_proxy_id, str) and npc_proxy_id:
                hint["npcProxyId"] = npc_proxy_id
            if "useFilterCondition" in info:
                hint["useFilterCondition"] = info.get("useFilterCondition") is True
            filter_condition = info.get("filterCondition")
            if info.get("useFilterCondition") is True and isinstance(
                filter_condition,
                dict,
            ):
                # This condition controls whether the navigation marker is
                # displayed. It is retained verbatim for evidence, but must
                # never be reinterpreted as activation of the tracked proxy or
                # playback of an adjacent dialog.
                hint["trackingVisibilityFilter"] = {
                    "role": "tracking_marker_visibility_only",
                    "conditionType": _condition_short_type(
                        filter_condition.get("$type", "")
                    ),
                    "serializedCondition": copy.deepcopy(filter_condition),
                }
            mission_area_id = info.get("missionAreaId")
            if isinstance(mission_area_id, str) and mission_area_id:
                hint["missionAreaId"] = mission_area_id
                area_story_refs = _extract_embedded_story_refs(mission_area_id)
                if area_story_refs:
                    hint["areaStoryRefs"] = area_story_refs
            jump_id = info.get("jumpId")
            if isinstance(jump_id, str) and jump_id:
                hint["jumpId"] = jump_id
            sns_dialog_id = info.get("snsDialogId")
            if isinstance(sns_dialog_id, str) and sns_dialog_id:
                # SnsTrackingInfo is authored quest-marker context. Preserve
                # its exact Story id for a typed quest attachment, while
                # keeping it distinct from SNS playback evidence.
                hint["snsDialogId"] = sns_dialog_id
            # EntityTrackingInfo is a native navigation target. Preserve the
            # exact serialized fields so the mission builder can resolve the
            # local script/slot pair through WorldEntityRegistry. This is
            # context evidence only: it does not say the quest invokes every
            # action or Story id stored in that LevelScript.
            if isinstance(info.get("trackScriptEntity"), bool):
                hint["trackScriptEntity"] = info["trackScriptEntity"]
            for field_name in ("entityLogicId", "scriptId", "entitySlotId"):
                value = info.get(field_name)
                if isinstance(value, int) and not isinstance(value, bool):
                    hint[field_name] = value
            hint["objectiveIndex"] = objective_index + 1
            hint["trackingIndex"] = tracking_index
            hint.update(provenance)
            tracking_pos = info.get("trackingPos")
            if isinstance(tracking_pos, dict):
                try:
                    hint["trackingPos"] = {
                        "x": float(tracking_pos.get("x", 0.0)),
                        "y": float(tracking_pos.get("y", 0.0)),
                        "z": float(tracking_pos.get("z", 0.0)),
                    }
                except (TypeError, ValueError):
                    pass
            if not hint:
                continue
            key = (
                hint.get("type", ""),
                hint.get("scene", ""),
                hint.get("npcProxyId", ""),
                hint.get("missionAreaId", ""),
                hint.get("jumpId", ""),
                hint.get("snsDialogId", ""),
                hint.get("trackScriptEntity"),
                hint.get("entityLogicId"),
                hint.get("scriptId"),
                hint.get("entitySlotId"),
                hint.get("trackingListSource", ""),
                hint.get("objectiveIndex") if hint.get("trackingListSource") else None,
                hint.get("multiDescriptionIndex"),
                hint.get("actualListIndex"),
                tuple(
                    round(float(hint["trackingPos"][axis]), 3)
                    for axis in ("x", "y", "z")
                ) if hint.get("trackingPos") else (),
            )
            if key in seen:
                continue
            seen.add(key)
            out.append(hint)
    return out


def _extract_objective_tracking_hints(obj: dict) -> list[dict]:
    quest_like = {"objectiveList": [obj]}
    return _extract_tracking_hints(quest_like)


def _extract_condition_anchor_leaves(cond) -> list[dict]:
    if not isinstance(cond, dict):
        return []
    short = _condition_short_type(cond.get("$type", ""))
    if short == "CombineCondition":
        out: list[dict] = []
        for sub in cond.get("subConditions") or []:
            out.extend(_extract_condition_anchor_leaves(sub))
        return out

    leaf: dict = {"type": short or "Unknown"}
    story_refs = _extract_ref_strings(
        cond,
        (*_DIALOG_REF_FIELDS, *_CUTSCENE_REF_FIELDS, *_REMOTECOMM_REF_FIELDS, *_RADIO_REF_FIELDS),
    )
    if story_refs:
        leaf["storyRefs"] = story_refs

    area_story_refs = _unique_preserve(
        ref
        for field_name in ("_areaId", "areaId", "missionAreaId")
        for value in _walk_field_values(cond, field_name)
        if isinstance(value, str)
        for ref in _extract_embedded_story_refs(value)
    )
    if area_story_refs:
        leaf["areaStoryRefs"] = area_story_refs

    level_ids = unique_strings(
        value
        for field_name in ("_sceneId", "sceneId", "_levelId", "levelId", "_mapId", "mapId")
        for value in _walk_field_values(cond, field_name)
    )
    if level_ids:
        leaf["sceneIds"] = level_ids

    script_ids: list[int] = []
    for field_name in ("_scriptId", "scriptId"):
        for value in _walk_field_values(cond, field_name):
            script_id = None
            if isinstance(value, dict):
                script_id = value.get("scriptId")
            elif isinstance(value, int):
                script_id = value
            if isinstance(script_id, int) and script_id > 0 and script_id not in script_ids:
                script_ids.append(script_id)
    if script_ids:
        leaf["scriptIds"] = script_ids

    logic_ids: list[int] = []
    for value in _walk_field_values(cond, "_entityId"):
        if isinstance(value, dict):
            logic_id = value.get("logicId")
            if isinstance(logic_id, int) and logic_id not in logic_ids:
                logic_ids.append(logic_id)
    if logic_ids:
        leaf["logicIds"] = logic_ids

    quest_refs: list[dict] = []
    quest_ids = unique_strings(_walk_field_values(cond, "_questId"))
    target_states = list(_walk_field_values(cond, "_targetQuestState"))
    target_state = target_states[0] if target_states else None
    for quest_id in quest_ids:
        quest_ref = {"questId": quest_id}
        if isinstance(target_state, (int, float, str)):
            quest_ref["targetState"] = target_state
        quest_refs.append(quest_ref)
    if quest_refs:
        leaf["questStateRefs"] = quest_refs

    compare_keys = unique_strings(_walk_field_values(cond, "_key"))
    if compare_keys:
        leaf["keys"] = compare_keys
    compare_values = list(_walk_field_values(cond, "_compareValue"))
    if compare_values:
        leaf["compareValues"] = _unique_preserve(compare_values)
    finish_ids = list(_walk_field_values(cond, "_finishId"))
    if finish_ids:
        leaf["finishIds"] = _unique_preserve(finish_ids)
    trigger_slot_ids = list(_walk_field_values(cond, "_triggerSlotIdOutput"))
    if trigger_slot_ids:
        leaf["triggerSlotIds"] = _unique_preserve(trigger_slot_ids)
    succeed_ids = list(_walk_field_values(cond, "_succeedId"))
    if succeed_ids:
        leaf["succeedIds"] = _unique_preserve(succeed_ids)
    new_states = list(_walk_field_values(cond, "_newState"))
    if new_states:
        leaf["newStates"] = _unique_preserve(new_states)
    old_states = list(_walk_field_values(cond, "_oldState"))
    if old_states:
        leaf["oldStates"] = _unique_preserve(old_states)
    event_trigger_ids = list(_walk_field_values(cond, "level_event_id_trigger"))
    if event_trigger_ids:
        leaf["eventTriggerIds"] = _unique_preserve(event_trigger_ids)

    return [leaf]


def _extract_objective_anchors(quest: dict) -> list[dict]:
    out: list[dict] = []
    for index, obj in enumerate(quest.get("objectiveList") or [], start=1):
        if not isinstance(obj, dict):
            continue
        tracking = [_resolve_tracking_hint(hint) for hint in _extract_objective_tracking_hints(obj)]
        leaves = _extract_condition_anchor_leaves(obj.get("condition"))

        anchor: dict = {
            "index": index,
            "tracking": tracking,
            "conditionLeaves": leaves,
        }
        description = obj.get("description")
        if isinstance(description, dict) and description.get("key"):
            anchor["descriptionKey"] = str(description["key"])
        multiple_description = [
            str(item.get("key"))
            for item in (obj.get("multipleDescription") or [])
            if isinstance(item, dict) and item.get("key")
        ]
        if multiple_description:
            anchor["multipleDescriptionKeys"] = _unique_preserve(multiple_description)
        if obj.get("muteTrack"):
            anchor["muteTrack"] = True
        if obj.get("isBlockObjective"):
            anchor["isBlockObjective"] = True

        condition_types = _unique_preserve([
            str(leaf.get("type") or "")
            for leaf in leaves
            if leaf.get("type")
        ])
        if condition_types:
            anchor["conditionTypes"] = condition_types

        tracking_types = _unique_preserve([
            str(hint.get("type") or "")
            for hint in tracking
            if hint.get("type")
        ])
        if tracking_types:
            anchor["trackingTypes"] = tracking_types

        story_refs = _unique_preserve([
            str(ref)
            for leaf in leaves
            for ref in (leaf.get("storyRefs") or [])
            if ref
        ])
        if story_refs:
            anchor["storyRefs"] = story_refs

        area_story_refs = _unique_preserve([
            str(ref)
            for ref in (
                [ref for leaf in leaves for ref in (leaf.get("areaStoryRefs") or [])]
                + [ref for hint in tracking for ref in (hint.get("areaStoryRefs") or [])]
            )
            if ref
        ])
        if area_story_refs:
            anchor["areaStoryRefs"] = area_story_refs

        scene_ids = _unique_preserve([
            str(scene_id)
            for value in (
                [scene_id for leaf in leaves for scene_id in (leaf.get("sceneIds") or [])]
                + [hint.get("scene") for hint in tracking if hint.get("scene")]
            )
            if value
            for scene_id in [value]
        ])
        if scene_ids:
            anchor["sceneIds"] = scene_ids

        mission_area_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("missionAreaId") for hint in tracking if hint.get("missionAreaId")])
            if value
        ])
        if mission_area_ids:
            anchor["missionAreaIds"] = mission_area_ids

        npc_proxy_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("npcProxyId") for hint in tracking if hint.get("npcProxyId")])
            if value
        ])
        if npc_proxy_ids:
            anchor["npcProxyIds"] = npc_proxy_ids

        jump_ids = _unique_preserve([
            str(value)
            for value in ([hint.get("jumpId") for hint in tracking if hint.get("jumpId")])
            if value
        ])
        if jump_ids:
            anchor["jumpIds"] = jump_ids

        script_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("scriptIds") or [])
            if isinstance(value, int)
        ])
        if script_ids:
            anchor["scriptIds"] = script_ids

        logic_ids = _unique_preserve([
            int(value)
            for leaf in leaves
            for value in (leaf.get("logicIds") or [])
            if isinstance(value, int)
        ])
        if logic_ids:
            anchor["logicIds"] = logic_ids

        quest_state_refs = []
        seen_quest_state_refs: set[tuple[str, str]] = set()
        for leaf in leaves:
            for row in (leaf.get("questStateRefs") or []):
                quest_id = str(row.get("questId") or "")
                if not quest_id:
                    continue
                state_value = row.get("targetState")
                dedup = (quest_id, str(state_value))
                if dedup in seen_quest_state_refs:
                    continue
                seen_quest_state_refs.add(dedup)
                quest_ref = {"questId": quest_id}
                if state_value is not None:
                    quest_ref["targetState"] = state_value
                quest_state_refs.append(quest_ref)
        if quest_state_refs:
            anchor["questStateRefs"] = quest_state_refs

        if (
            anchor.get("tracking")
            or anchor.get("conditionTypes")
            or anchor.get("storyRefs")
            or anchor.get("areaStoryRefs")
            or anchor.get("sceneIds")
            or anchor.get("missionAreaIds")
            or anchor.get("npcProxyIds")
            or anchor.get("jumpIds")
            or anchor.get("scriptIds")
            or anchor.get("logicIds")
            or anchor.get("questStateRefs")
        ):
            out.append(anchor)
    return out


def _build_mission_area_index(
    table_raw: object,
    level_basic_raw: object,
) -> dict[tuple[str, str], dict]:
    """Index MissionArea rows by their authored level and area id.

    ``MissionAreaTable.m_areas`` is keyed by ``LevelBasicInfoTable.idNum``.
    Area ids are not globally unique (``c13_001`` is one current example), so
    selecting the first matching id silently assigns the wrong position and
    sub-data parent.  A level-less fallback is retained only for ids that
    occur in exactly one authored level bucket.
    """
    if not isinstance(table_raw, dict) or not isinstance(level_basic_raw, dict):
        return {}
    level_ids_by_num: dict[str, list[str]] = defaultdict(list)
    for raw_level_id, row in level_basic_raw.items():
        if not isinstance(row, dict):
            continue
        level_id = str(row.get("id") or raw_level_id or "").strip()
        raw_id_num = row.get("idNum")
        if not level_id or isinstance(raw_id_num, bool):
            continue
        try:
            id_num = str(int(raw_id_num))
        except (TypeError, ValueError):
            continue
        if level_id not in level_ids_by_num[id_num]:
            level_ids_by_num[id_num].append(level_id)

    rows_by_area_id: dict[str, list[tuple[str, dict]]] = defaultdict(list)
    out: dict[tuple[str, str], dict] = {}
    area_buckets = table_raw.get("m_areas")
    if not isinstance(area_buckets, dict):
        return out
    for raw_level_num, bucket in area_buckets.items():
        if not isinstance(bucket, dict):
            continue
        level_num = str(raw_level_num).strip()
        level_ids = level_ids_by_num.get(level_num) or []
        for raw_area_id, row in bucket.items():
            if not isinstance(row, dict):
                continue
            mission_area_id = str(
                row.get("missionAreaId") or raw_area_id or ""
            ).strip()
            if not mission_area_id:
                continue
            enriched = dict(row)
            enriched["levelNum"] = level_num
            rows_by_area_id[mission_area_id].append((level_num, enriched))
            for level_id in level_ids:
                out[(level_id, mission_area_id)] = enriched

    for mission_area_id, rows in rows_by_area_id.items():
        if len(rows) == 1:
            out[("", mission_area_id)] = rows[0][1]
    return out


def _load_mission_areas() -> dict[tuple[str, str], dict]:
    global _MISSION_AREA_CACHE
    if _MISSION_AREA_CACHE is not None:
        return _MISSION_AREA_CACHE
    out: dict[tuple[str, str], dict] = {}
    path = GAMEPLAY_CONFIG_DIR / "MissionAreaTable.json"
    level_basic_path = GAMEPLAY_CONFIG_DIR / "LevelBasicInfoTable.json"
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
        with level_basic_path.open(encoding="utf-8") as f:
            level_basic_raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _MISSION_AREA_CACHE = out
        return out
    out = _build_mission_area_index(raw, level_basic_raw)
    _MISSION_AREA_CACHE = out
    return out


def _load_npc_proxy_table() -> dict[str, dict]:
    global _NPC_PROXY_TABLE_CACHE
    if _NPC_PROXY_TABLE_CACHE is not None:
        return _NPC_PROXY_TABLE_CACHE
    path = NPC_PROXY_TABLE_PATH
    try:
        with path.open(encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, json.JSONDecodeError):
        _NPC_PROXY_TABLE_CACHE = {}
        return {}
    table = raw.get("dataTable") if isinstance(raw, dict) else None
    _NPC_PROXY_TABLE_CACHE = table if isinstance(table, dict) else {}
    return _NPC_PROXY_TABLE_CACHE


@lru_cache(maxsize=65_536)
def _canonical_cutscene_key(name: str) -> str:
    return mission_canonical_cutscene_key(name)


@lru_cache(maxsize=65_536)
def _scene_ref_alias_candidates(name: str) -> tuple[str, ...]:
    value = str(name or "").strip()
    if not value:
        return ()

    aliases: list[str] = []

    def add(candidate: str) -> None:
        if candidate and candidate != value and candidate not in aliases:
            aliases.append(candidate)

    bases = [value]
    if match := re.match(r"^(?:f|m|fm)_(.+)$", value, re.IGNORECASE):
        bases.append(match.group(1))

    for base in bases:
        if base.startswith("dlg_"):
            add(f"misc_{base}")
        elif base.startswith("misc_dlg_"):
            add(base[len("misc_"):])

        if base.startswith("cs_video_"):
            add(f"cutscene_{base[len('cs_video_'):]}")

        if not base.startswith((
            "dlg_",
            "sns_",
            "misc_dlg_",
            "cutscene_",
            "black_",
            "remotecomm_",
            "radio_",
        )):
            continue

        parent = base
        while parent.count("_") >= 3:
            stem, suffix = parent.rsplit("_", 1)
            if not suffix.isdigit():
                break
            add(stem)
            parent = stem

    return tuple(aliases)


def _scene_key_matches_mission(scene_key: str, mission_id: str) -> bool:
    return not mission_id or f"_{mission_id}_" in f"_{scene_key}_"


@lru_cache(maxsize=131_072)
def _resolve_payload_scene_key(payload_text: str, mission_id: str, dialog_key_resolver) -> str:
    candidates = _unique_preserve([
        str(payload_text or "").strip(),
        *_scene_ref_alias_candidates(payload_text),
    ])
    for candidate in candidates:
        if not candidate:
            continue
        scene_key = dialog_key_resolver(candidate) or ""
        if scene_key and _scene_key_matches_mission(scene_key, mission_id):
            return scene_key
        canonical_cutscene = _canonical_cutscene_key(candidate) or ""
        if canonical_cutscene and _scene_key_matches_mission(canonical_cutscene, mission_id):
            scene_key = dialog_key_resolver(canonical_cutscene) or canonical_cutscene
            if _scene_key_matches_mission(scene_key, mission_id):
                return scene_key
    return ""


def _cutscene_asset_name_without_prefix(name: str) -> str:
    value = str(name or "").strip()
    if match := re.match(r"^(?:f|m|fm)_(cutscene_.+)$", value, re.IGNORECASE):
        return match.group(1)
    return value


def _cutscene_variant_part(name: str, canonical_key: str) -> str:
    value = _cutscene_asset_name_without_prefix(name)
    value = re.sub(r"_p[0-9A-Fa-f]{8,16}$", "", value)
    if canonical_key and value.startswith(canonical_key):
        remainder = value[len(canonical_key):].strip("_")
    else:
        remainder = ""
    if not remainder:
        return "root"
    first = remainder.split("_", 1)[0]
    if first in {"Actor", "Audio", "Effect", "Light", "Others"}:
        return first
    if first in {"CHI", "CN", "EN", "ENG", "JP", "KO", "KR", "ENV"}:
        return f"locale:{first}"
    return "variant"


def _decode_anime_text_asset_payload(raw: dict) -> dict:
    script = raw.get("m_Script") if isinstance(raw, dict) else None
    if not isinstance(script, str) or not script.strip():
        return {}
    try:
        decoded = base64.b64decode(script, validate=True).decode("utf-8-sig")
        payload = json.loads(decoded)
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _subtitle_playable_text_ids(raw: dict) -> list[str]:
    text_id = str(raw.get("_textId") or "").strip()
    if text_id:
        return [text_id]

    numbered: list[tuple[int, str]] = []
    for key, value in raw.items():
        match = re.fullmatch(r"_textId_(\d+)", str(key or ""))
        if not match:
            continue
        text = str(value or "").strip()
        if text:
            numbered.append((int(match.group(1)), text))
    return [text for _index, text in sorted(numbered)]


def _cutscene_variant_gender(name: str) -> str:
    if re.match(r"^f_", str(name or ""), re.IGNORECASE):
        return "F"
    if re.match(r"^m_", str(name or ""), re.IGNORECASE):
        return "M"
    return ""


def _load_cutscene_subtitle_tracks() -> dict[str, list[dict]]:
    """Return AnimeStudio subtitle clip text IDs grouped by canonical cutscene.

    TextTable rows can contain loose aliases and unused leftovers. When a
    decoded cutscene has a real Timeline subtitle track, the clip asset
    references are the stronger source for which text IDs are actually used.
    """
    global _CUTSCENE_SUBTITLE_TRACK_CACHE
    if _CUTSCENE_SUBTITLE_TRACK_CACHE is not None:
        return _CUTSCENE_SUBTITLE_TRACK_CACHE

    parent_assets: dict[int, dict] = {}
    for path in _iter_anime_tree_files("*cutscene*.json"):
        logical_stem = _anime_tree_logical_stem(path)
        canonical_key = _canonical_cutscene_key(logical_stem)
        if not canonical_key:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        info = raw.get("$animestudio") if isinstance(raw, dict) else None
        path_id = info.get("pathId") if isinstance(info, dict) else None
        if not isinstance(path_id, int):
            continue
        parent_assets[path_id] = {
            "cutsceneKey": canonical_key,
            "name": logical_stem,
            "gender": _cutscene_variant_gender(logical_stem),
            "file": repo_rel(path),
        }

    playable_text_ids: dict[int, list[str]] = {}
    for path in _iter_anime_tree_files("*SubtitlePlayableAsset*.json"):
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        info = raw.get("$animestudio") if isinstance(raw.get("$animestudio"), dict) else {}
        path_id = info.get("pathId")
        if not isinstance(path_id, int):
            continue
        text_ids = _subtitle_playable_text_ids(raw)
        if text_ids:
            playable_text_ids[path_id] = text_ids

    out: dict[str, list[dict]] = defaultdict(list)
    for path in itertools.chain(
        _iter_anime_tree_files("*Subtitle Track*.json"),
        _iter_anime_tree_files("*Left Subtitle Track*.json"),
    ):
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(raw, dict):
            continue
        clips = raw.get("m_Clips")
        if not isinstance(clips, list) or not clips:
            continue

        parent = raw.get("m_Parent") if isinstance(raw.get("m_Parent"), dict) else {}
        parent_id = parent.get("m_PathID")
        parent_asset = parent_assets.get(parent_id)
        if not parent_asset:
            continue

        track_info = raw.get("$animestudio") if isinstance(raw.get("$animestudio"), dict) else {}
        lines: list[dict] = []
        for clip_index, clip in enumerate(clips):
            if not isinstance(clip, dict):
                continue
            asset_ref = clip.get("m_Asset") if isinstance(clip.get("m_Asset"), dict) else {}
            asset_id = asset_ref.get("m_PathID")
            for text_id in playable_text_ids.get(asset_id, []):
                lines.append({
                    "textId": text_id,
                    "start": clip.get("m_Start"),
                    "duration": clip.get("m_Duration"),
                    "displayName": str(clip.get("m_DisplayName") or ""),
                    "clipIndex": clip_index,
                    "assetPathId": asset_id,
                })
        if not lines:
            continue

        lines.sort(key=lambda line: (
            float(line["start"]) if isinstance(line.get("start"), (int, float)) else 0.0,
            int(line.get("clipIndex") or 0),
            str(line.get("textId") or ""),
        ))
        out[parent_asset["cutsceneKey"]].append({
            "file": repo_rel(path),
            "pathId": track_info.get("pathId"),
            "parentPathId": parent_id,
            "parentName": parent_asset["name"],
            "parentFile": parent_asset["file"],
            "gender": parent_asset.get("gender") or "",
            "lines": lines,
        })

    for tracks in out.values():
        tracks.sort(key=lambda track: (
            str(track.get("parentName") or ""),
            str(track.get("file") or ""),
            str(track.get("pathId") or ""),
        ))

    _CUTSCENE_SUBTITLE_TRACK_CACHE = dict(out)
    return _CUTSCENE_SUBTITLE_TRACK_CACHE


def _infer_cutscene_mission_and_scene(
    canonical_key: str,
    known_missions: list[str],
) -> tuple[str, str]:
    prefix = "cutscene_"
    rest = canonical_key[len(prefix):] if canonical_key.startswith(prefix) else canonical_key
    mission = ""
    for candidate in known_missions:
        start = 0
        while True:
            idx = rest.find(candidate, start)
            if idx < 0:
                break
            end = idx + len(candidate)
            before_ok = idx == 0 or rest[idx - 1] == "_"
            after_ok = end == len(rest) or rest[end] == "_"
            if before_ok and after_ok:
                mission = candidate
                break
            start = idx + 1
        if mission:
            break

    if mission:
        idx = rest.find(mission)
        before = rest[:idx].strip("_")
        after = rest[idx + len(mission):].strip("_")
        scene = "_".join(part for part in (before, after) if part) or "0"
        return mission, scene

    parts = [part for part in rest.split("_") if part]
    if len(parts) >= 2 and parts[0].startswith("map") and parts[1].startswith("lv"):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if len(parts) >= 2 and parts[0].startswith(("dung", "indie", "blackbox")):
        mission = "_".join(parts[:2])
        return mission, "_".join(parts[2:]) or "0"
    if parts:
        mission = parts[0]
        return mission, "_".join(parts[1:]) or "0"
    return canonical_key, "0"


def _relative_asset_ref(label: str, source_root: Path, path: Path) -> str:
    try:
        rel_suffix = path.relative_to(source_root).as_posix()
    except ValueError:
        rel_suffix = path.name
    return f"{label}/{rel_suffix}" if rel_suffix else label


def _iter_narrative_video_roots(kind_dir: str):
    structured_roots = (
        ("StreamingAssets-structured", STREAMING_ASSETS_DIR),
        ("Persistent-structured", PERSISTENT_ASSETS_DIR),
    )
    for label, source_root in structured_roots:
        video_dir = source_root / "Data" / "Video" / "PC" / "Narrative" / kind_dir
        if video_dir.exists():
            yield label, source_root, video_dir

    raw_vfs_root = EXPORT_ROOT / "raw_vfs"
    for source in ("StreamingAssets", "Persistent"):
        files_root = raw_vfs_root / source / "files"
        if not files_root.exists():
            continue
        for bucket_dir in sorted(files_root.iterdir()):
            if not bucket_dir.is_dir():
                continue
            video_dir = bucket_dir / "Data" / "Video" / "PC" / "Narrative" / kind_dir
            if video_dir.exists():
                yield "raw_vfs", raw_vfs_root, video_dir


def _strip_gender_video_prefix(stem: str) -> tuple[str, str]:
    value = str(stem or "").strip()
    if match := re.match(r"^(?P<gender>f|m)_(?P<rest>.+)$", value, re.IGNORECASE):
        return match.group("gender").lower(), match.group("rest")
    return "", value


def _narrative_video_key_candidates(kind: str, stem: str) -> list[str]:
    _, base = _strip_gender_video_prefix(stem)
    candidates: list[str] = []

    def add(candidate: str) -> None:
        candidate = str(candidate or "").strip()
        if candidate and candidate not in candidates:
            candidates.append(candidate)

    def letter_suffix_alias(value: str) -> str:
        match = re.match(r"^(.+_\d+)[a-z]+$", str(value or ""), re.IGNORECASE)
        return match.group(1) if match else ""

    if kind == "cutscene":
        raw = base
        if raw.startswith("cs_video_"):
            raw = raw[len("cs_video_"):]
        raw_alias = letter_suffix_alias(raw)
        if raw.startswith("dlg_"):
            add(raw)
            add(raw_alias)
            add(f"misc_{raw}")
            if raw_alias:
                add(f"misc_{raw_alias}")
        if raw.startswith("cutscene_"):
            add(_canonical_cutscene_key(raw) or raw)
            if raw_alias:
                add(_canonical_cutscene_key(raw_alias) or raw_alias)
        else:
            add(_canonical_cutscene_key(f"cutscene_{raw}") or f"cutscene_{raw}")
            if raw_alias:
                add(_canonical_cutscene_key(f"cutscene_{raw_alias}") or f"cutscene_{raw_alias}")
            if not raw.startswith("dlg_"):
                add(f"dlg_{raw}")
                if raw_alias:
                    add(f"dlg_{raw_alias}")
        add(raw)
        add(raw_alias)
    elif kind == "remotecomm":
        add(base)
        if not base.startswith("remotecomm_"):
            add(f"remotecomm_{base}")
    return candidates


def _load_video_bindings_index() -> dict[str, dict]:
    """Read recovered/video_bindings.json keyed by fmvId.

    Empty dict if the recovery output is missing or unreadable; downstream code
    must treat any missing entry as "no authoritative binding, fall back to
    name heuristics".
    """
    global _VIDEO_BINDINGS_CACHE
    if _VIDEO_BINDINGS_CACHE is not None:
        return _VIDEO_BINDINGS_CACHE
    try:
        payload = json.loads(VIDEO_BINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _VIDEO_BINDINGS_CACHE = {}
        return _VIDEO_BINDINGS_CACHE
    bindings = payload.get("bindings") if isinstance(payload, dict) else None
    _VIDEO_BINDINGS_CACHE = bindings if isinstance(bindings, dict) else {}
    return _VIDEO_BINDINGS_CACHE


def _video_binding_for_stem(stem: str) -> dict | None:
    bindings = _load_video_bindings_index()
    if not bindings:
        return None
    direct = bindings.get(stem)
    if isinstance(direct, dict):
        return direct
    _gender, base_stem = _strip_gender_video_prefix(stem)
    if base_stem != stem:
        base_binding = bindings.get(base_stem)
        if isinstance(base_binding, dict):
            return base_binding
    return None


def _load_video_definitions_index() -> dict[str, dict]:
    """Read definition-only FMV provenance without promoting it to a binding."""
    global _VIDEO_DEFINITIONS_CACHE
    if _VIDEO_DEFINITIONS_CACHE is not None:
        return _VIDEO_DEFINITIONS_CACHE
    try:
        payload = json.loads(VIDEO_BINDINGS_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _VIDEO_DEFINITIONS_CACHE = {}
        return _VIDEO_DEFINITIONS_CACHE
    definitions = payload.get("definitions") if isinstance(payload, dict) else None
    _VIDEO_DEFINITIONS_CACHE = (
        definitions if isinstance(definitions, dict) else {}
    )
    return _VIDEO_DEFINITIONS_CACHE


def _video_definition_for_stem(stem: str) -> dict | None:
    definitions = _load_video_definitions_index()
    direct = definitions.get(stem)
    if isinstance(direct, dict):
        return direct
    _gender, base_stem = _strip_gender_video_prefix(stem)
    base_definition = definitions.get(base_stem)
    return base_definition if isinstance(base_definition, dict) else None


def _authoritative_scene_keys(kind: str, binding: dict) -> list[str]:
    """Convert a binding record into scene-key candidates suitable for index lookup.

    A timeline-resolved scene id like `e6m2_7` becomes the dialog key
    `dlg_e6m2_7`. For non-dialog scenes the raw id is also returned. Bindings
    that only carry a hint (no timeline asset) are skipped so the heuristic
    fallback stays in charge.
    """
    if not isinstance(binding, dict):
        return []
    if binding.get("sceneIsHint"):
        return []
    scene = str(binding.get("scene") or "").strip()
    if not scene:
        return []
    keys: list[str] = []
    if scene.startswith("dlg_"):
        keys.append(scene)
    else:
        keys.append(f"dlg_{scene}")
        if kind == "remotecomm" and not scene.startswith("remotecomm_"):
            keys.append(f"remotecomm_{scene}")
    if scene not in keys:
        keys.append(scene)
    return keys


def _load_narrative_video_assets() -> list[dict]:
    global _NARRATIVE_VIDEO_CACHE
    if _NARRATIVE_VIDEO_CACHE is not None:
        return _NARRATIVE_VIDEO_CACHE

    out: list[dict] = []
    for kind, kind_dir in (("cutscene", "Cutscene"), ("remotecomm", "RemoteComm")):
        for label, source_root, video_dir in _iter_narrative_video_roots(kind_dir):
            for path in sorted(video_dir.iterdir()):
                if not path.is_file() or path.suffix.lower() not in NARRATIVE_VIDEO_EXTENSIONS:
                    continue
                gender, base_stem = _strip_gender_video_prefix(path.stem)
                heuristic_candidates = _narrative_video_key_candidates(kind, path.stem)
                binding = _video_binding_for_stem(path.stem)
                definition = _video_definition_for_stem(path.stem)
                authoritative_keys = _authoritative_scene_keys(kind, binding or {})

                candidates: list[str] = []
                seen: set[str] = set()
                for value in (*authoritative_keys, *heuristic_candidates):
                    if value and value not in seen:
                        candidates.append(value)
                        seen.add(value)
                if not candidates:
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    size = 0
                ref = {
                    "kind": kind,
                    "name": path.name,
                    "stem": path.stem,
                    "baseStem": base_stem,
                    "gender": gender,
                    "format": path.suffix.lower().lstrip("."),
                    "size": size,
                    "source": label,
                    "rel": _relative_asset_ref(label, source_root, path),
                    "keyCandidates": candidates,
                }
                if binding:
                    binding_sources = [
                        {
                            key: source.get(key)
                            for key in (
                                "kind",
                                "asset",
                                "container",
                                "pathId",
                                "duration",
                                "missions",
                                "levelId",
                                "scriptId",
                                "sourceFile",
                                "actionMapRole",
                                "recordOffset",
                                "localId",
                                "actionName",
                                "nativeMappingId",
                                "fmvAction",
                            )
                            if key in source
                        }
                        for source in (binding.get("sources") or [])
                        if isinstance(source, dict)
                    ]
                    ref["binding"] = {
                        "fmvId": str(binding.get("fmvId") or path.stem),
                        "scene": str(binding.get("scene") or ""),
                        "mission": str(binding.get("mission") or ""),
                        "missions": list(binding.get("missions") or []),
                        "isHint": bool(binding.get("sceneIsHint")),
                        "sourceKinds": sorted({
                            str(s.get("kind") or "")
                            for s in (binding.get("sources") or [])
                            if isinstance(s, dict) and s.get("kind")
                        }),
                        "clips": [
                            {
                                "scene": c.get("scene"),
                                "start": c.get("start"),
                                "duration": c.get("duration"),
                                "optionIndex": c.get("optionIndex"),
                            }
                            for c in (binding.get("clips") or [])
                            if isinstance(c, dict)
                        ][:8],
                    }
                    if binding_sources:
                        ref["binding"]["evidence"] = binding_sources[:8]
                if definition:
                    ref["definition"] = {
                        "fmvId": str(
                            definition.get("fmvId") or path.stem
                        ),
                        "numericIds": [
                            int(value)
                            for value in (
                                definition.get("numericIds") or []
                            )
                            if isinstance(value, int)
                        ],
                        "placementEvidence": False,
                        "timelineEvidence": (
                            definition.get("timelineEvidence")
                            if isinstance(
                                definition.get("timelineEvidence"),
                                dict,
                            )
                            else {}
                        ),
                        "evidence": [
                            source
                            for source in (
                                definition.get("sources") or []
                            )
                            if isinstance(source, dict)
                        ][:8],
                    }
                if authoritative_keys:
                    ref["authoritativeKeys"] = list(authoritative_keys)
                out.append(ref)

    out.sort(key=lambda ref: (
        str(ref.get("kind") or ""),
        str((ref.get("keyCandidates") or [""])[0]),
        str(ref.get("baseStem") or ""),
        str(ref.get("gender") or ""),
        str(ref.get("source") or ""),
        str(ref.get("name") or ""),
    ))
    _NARRATIVE_VIDEO_CACHE = out
    return out


def _load_cutscene_assets() -> dict[str, dict]:
    global _CUTSCENE_ASSET_CACHE
    if _CUTSCENE_ASSET_CACHE is not None:
        return _CUTSCENE_ASSET_CACHE

    out: dict[str, dict] = {}
    for path in _iter_anime_tree_files("*cutscene*.json"):
        logical_stem = _anime_tree_logical_stem(path)
        canonical_key = _canonical_cutscene_key(logical_stem)
        if not canonical_key:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            continue

        entry = out.setdefault(
            canonical_key,
            {
                "variants": [],
                "componentCounts": Counter(),
                "levels": set(),
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": defaultdict(list),
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
            },
        )
        payload = _decode_anime_text_asset_payload(raw) or raw
        part = _cutscene_variant_part(logical_stem, canonical_key)
        entry["componentCounts"][part] += 1
        entry["variants"].append({
            "name": logical_stem,
            "part": part,
            "file": repo_rel(path),
            "path": str(payload.get("path") or ""),
            "version": str(payload.get("version") or raw.get("m_Version") or ""),
        })
        if payload.get("path"):
            entry["paths"].append(str(payload["path"]))
        if payload.get("version"):
            entry["versions"].append(str(payload["version"]))
        elif raw.get("m_Version") not in (None, ""):
            entry["versions"].append(str(raw["m_Version"]))
        audio_events = payload.get("audioEvents") or []
        if isinstance(audio_events, list):
            entry["audioEvents"].extend(str(event) for event in audio_events if event)
        tag_group = payload.get("tagGroup") if isinstance(payload, dict) else None
        if isinstance(tag_group, dict):
            tags = tag_group.get("tags") or []
            if isinstance(tags, list):
                entry["tags"].extend(str(tag) for tag in tags if tag)
            if tag_group.get("narrativeTypeTag") not in (None, ""):
                entry["metadata"]["narrativeTypeTag"].append(tag_group["narrativeTypeTag"])
        for meta_key in (
            "targetFrameRate",
            "skipType",
            "hideSquad",
            "useBlackScreen",
            "isTransition",
            "disableKeepCameras",
            "farCameraPosition",
            "noUIDispatch",
            "npcVisibleRuleType",
        ):
            if meta_key in payload and is_present(payload.get(meta_key)):
                entry["metadata"][meta_key].append(payload[meta_key])
        keep_camera_path = str(payload.get("keepCameraPath") or "")
        if keep_camera_path:
            entry["keepCameraPaths"].append(keep_camera_path)
        entry["useBlackScreen"] = entry["useBlackScreen"] or bool(payload.get("useBlackScreen"))
        path_text = str(payload.get("path") or "")
        entry["isTransition"] = entry["isTransition"] or bool(payload.get("isTransition")) or ("CutsceneTransition/" in path_text)

        for track in payload.get("trackData") or []:
            for sub_track in track.get("subTracks") or []:
                if "SubtitleTrackData" in str(sub_track.get("$type") or ""):
                    entry["hasSubtitleTrack"] = True

        for actor in payload.get("actors") or []:
            descriptor = actor.get("descriptor") or {}
            level_id = str(descriptor.get("levelId") or "")
            if level_id:
                entry["levels"].add(level_id)
            label = (
                str(descriptor.get("entityId") or "")
                or str(descriptor.get("interactiveTemplateId") or "")
                or str(descriptor.get("name") or "")
            ).strip()
            if label and label not in entry["actorLabels"]:
                entry["actorLabels"].append(label)

    for entry in out.values():
        entry["variants"].sort(key=lambda item: item["name"])
        entry["paths"] = _unique_preserve(entry["paths"])
        entry["versions"] = _unique_preserve(entry["versions"])
        entry["audioEvents"] = _unique_preserve(entry["audioEvents"])
        entry["tags"] = _unique_preserve(entry["tags"])
        entry["metadata"] = {
            key: _unique_preserve(values)
            for key, values in sorted(entry["metadata"].items())
            if values
        }
        entry["keepCameraPaths"] = _unique_preserve(entry["keepCameraPaths"])
        entry["componentCounts"] = {
            key: entry["componentCounts"][key]
            for key in sorted(entry["componentCounts"], key=lambda item: (item != "root", item))
        }
        entry["levels"] = sorted(entry["levels"])
    _CUTSCENE_ASSET_CACHE = out
    return out


def _cutscene_component_summary(cutscene: dict, *, limit: int = 8) -> str:
    counts = cutscene.get("componentCounts") or {}
    if not isinstance(counts, dict) or not counts:
        variant_count = len(cutscene.get("variants") or [])
        return f"{variant_count} file{'s' if variant_count != 1 else ''}" if variant_count else ""
    parts = [
        f"{key} {count}"
        for key, count in counts.items()
        if count
    ]
    if len(parts) > limit:
        hidden = len(parts) - limit
        parts = [*parts[:limit], f"+{hidden} more"]
    return ", ".join(parts)


def _resolve_tracking_hint(hint: dict) -> dict:
    resolved = dict(hint)
    tracking_pos = hint.get("trackingPos")
    if isinstance(tracking_pos, dict):
        resolved["position"] = tracking_pos
        resolved["sourceType"] = "trackingPos"
        return resolved

    mission_area_id = str(hint.get("missionAreaId") or "")
    if mission_area_id:
        scene_id = str(hint.get("scene") or hint.get("sceneId") or "")
        areas = _load_mission_areas()
        area = (
            areas.get((scene_id, mission_area_id))
            or areas.get(("", mission_area_id))
            or {}
        )
        shape = area.get("shape") or {}
        position = shape.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "missionArea"
            resolved["shapeType"] = shape.get("type")
            resolved["radius"] = shape.get("radius")
            size = shape.get("size")
            if isinstance(size, dict):
                resolved["size"] = {
                    axis: float(size.get(axis, 0.0)) for axis in ("x", "y", "z")
                }
            euler_angles = shape.get("eulerAngles")
            if isinstance(euler_angles, dict):
                resolved["rotation"] = {
                    axis: float(euler_angles.get(axis, 0.0))
                    for axis in ("x", "y", "z")
                }
            if area.get("levelNum") not in (None, ""):
                resolved["levelNum"] = str(area.get("levelNum"))
            sub_data_parent_id = area.get("subDataParentId")
            if sub_data_parent_id not in (None, "", [], {}):
                resolved["subDataParentId"] = sub_data_parent_id
                resolved["levelDataParentId"] = sub_data_parent_id
            if area.get("activeOnTravelLine") not in (None, "", [], {}):
                resolved["activeOnTravelLine"] = area.get("activeOnTravelLine")
            if area.get("needTrackingRoute") not in (None, "", [], {}):
                resolved["needTrackingRoute"] = area.get("needTrackingRoute")
            route_points = (((area.get("trackingRouteInfo") or {}).get("points")) or [])
            if route_points:
                resolved["routePointCount"] = len(route_points)
            return resolved

    npc_proxy_id = str(hint.get("npcProxyId") or "")
    if npc_proxy_id:
        proxy = _load_npc_proxy_table().get(npc_proxy_id) or {}
        position = proxy.get("position")
        if isinstance(position, dict):
            resolved["position"] = {
                "x": float(position.get("x", 0.0)),
                "y": float(position.get("y", 0.0)),
                "z": float(position.get("z", 0.0)),
            }
            resolved["sourceType"] = "npcProxy"
            rotation = proxy.get("rotation")
            if isinstance(rotation, dict):
                resolved["rotation"] = {
                    "x": float(rotation.get("x", 0.0)),
                    "y": float(rotation.get("y", 0.0)),
                    "z": float(rotation.get("z", 0.0)),
                }
            return resolved

    return resolved


def _tracking_hint_pin(hint: dict) -> dict | None:
    position = hint.get("position")
    if not isinstance(position, dict):
        return None
    return {
        "scene": str(hint.get("scene") or ""),
        "trackingType": str(hint.get("type") or ""),
        "sourceType": str(hint.get("sourceType") or ""),
        "position": {
            "x": float(position.get("x", 0.0)),
            "y": float(position.get("y", 0.0)),
            "z": float(position.get("z", 0.0)),
        },
        **({"missionAreaId": hint["missionAreaId"]} if hint.get("missionAreaId") else {}),
        **({"npcProxyId": hint["npcProxyId"]} if hint.get("npcProxyId") else {}),
        **({"radius": hint["radius"]} if hint.get("radius") is not None else {}),
        **({"subDataParentId": hint["subDataParentId"]} if hint.get("subDataParentId") is not None else {}),
        **({"levelDataParentId": hint["levelDataParentId"]} if hint.get("levelDataParentId") is not None else {}),
        **({"activeOnTravelLine": hint["activeOnTravelLine"]} if hint.get("activeOnTravelLine") is not None else {}),
        **({"needTrackingRoute": hint["needTrackingRoute"]} if hint.get("needTrackingRoute") is not None else {}),
        **({"routePointCount": hint["routePointCount"]} if hint.get("routePointCount") is not None else {}),
    }


__all__ = [name for name in globals() if not name.startswith("__")]
