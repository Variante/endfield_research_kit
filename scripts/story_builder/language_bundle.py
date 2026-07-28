from __future__ import annotations
import json as _radio_cont_json
import hashlib as _reference_hashlib
import re as _radio_cont_re
from functools import lru_cache as _radio_cont_lru_cache
from pathlib import Path as _RadioContPath
from .context import *
from .anime_assets import *
from .scene_graph import *
from .level_bindings import *
from .mission_flow import *
from .dialog_tree import *
from .bundle_support import *
from .language_helpers import *
from .timeline_action_evidence import build_conversation_action_debug
from .ability_binary import (
    build_battle_signal_producer_index,
    match_battle_signal_story_producers,
)
from .mission_recovery import (
    decode_mission_interactive_script_entity_conditions,
    decode_mission_script_conditions,
    decode_mission_world_entity_condition_groups,
    decode_mission_world_entity_condition_refs,
    is_call_server_self_uid_callback,
)

_RADIO_CONTINUATION_REPORT_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "reports" / "mission_order" / "radio_continuation_CN.json"
)
_FMV_CLIP_BY_KEY_REPORT_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "reports" / "playable_director" / "fmv_clip_by_webui_key.json"
)
_NARRATIVE_VIDEO_OVERRIDES_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "webui" / "overrides" / "narrative_videos.json"
)
_STORY_ORDER_OVERRIDES_PATH = (
    _RadioContPath(__file__).resolve().parents[2]
    / "webui" / "overrides" / "story_order.json"
)


@_radio_cont_lru_cache(maxsize=65536)
def _sequence_similarity_at_least(left: str, right: str, threshold: float) -> bool:
    """Return the exact SequenceMatcher threshold result with safe upper bounds.

    Story option recovery compares many unrelated text pairs.  The length and
    character-multiset bounds can reject most of them without running the much
    more expensive matching-block search.  ``quick_ratio`` is guaranteed to be
    an upper bound, so this changes cost only, never the accepted set.
    """
    if left == right:
        return 1.0 >= threshold
    total_length = len(left) + len(right)
    if not total_length:
        return True
    if (2.0 * min(len(left), len(right)) / total_length) < threshold:
        return False
    matcher = SequenceMatcher(None, left, right)
    if matcher.quick_ratio() < threshold:
        return False
    return matcher.ratio() >= threshold


def match_play3d_npc_tracking_context(
    story_key: str,
    occurrence: dict,
    consumers_by_proxy: dict[str, list[dict]],
) -> dict:
    """Match one exact Play3DRadio target to typed same-scene tracking.

    All matching consumers must agree on one MissionRuntime.  Repeated quest
    rows inside that mission are retained as evidence; cross-mission proxy ids
    fail closed.
    """
    play3d = occurrence.get("play3DRadio") or {}
    proxy_id = str(play3d.get("npcProxyId") or "").strip()
    level_id = str(occurrence.get("levelId") or "")
    if not (
        story_key
        and occurrence.get("actionName") == "Play3DRadio"
        and play3d.get("payloadShape")
        == "play3d-radio-native-12-field-exact-eof"
        and play3d.get("radioId") == story_key
        and play3d.get("useNpcProxy") is True
        and proxy_id
        and level_id
    ):
        return {}
    consumers = [
        row
        for row in consumers_by_proxy.get(proxy_id) or []
        if str(row.get("scene") or "") == level_id
    ]
    missions = {
        str(row.get("missionId") or "")
        for row in consumers
        if row.get("missionId")
    }
    if not consumers or len(missions) != 1:
        return {}
    return {
        "missionId": next(iter(missions)),
        "npcProxyId": proxy_id,
        "consumers": consumers,
    }


def classify_leveldata_mission_shell_occurrences(
    occurrences: list[dict],
    leveldata_script_hosts: dict[tuple[str, str], dict],
    available_missions: set[str],
) -> tuple[dict[str, list[dict]], list[dict]]:
    """Classify playback occurrences by exact validated LevelData shell.

    The join is deliberately limited to a complete member-22 BriefData entry
    whose host index independently resolves to one MissionRuntime id.  Shared
    shells remain visible to callers but are never promoted.
    """
    scoped: dict[str, list[dict]] = defaultdict(list)
    shared: list[dict] = []
    for occurrence in occurrences:
        pair = (
            str(occurrence.get("levelId") or ""),
            str(occurrence.get("scriptId") or ""),
        )
        host_evidence = leveldata_script_hosts.get(pair)
        if not host_evidence:
            continue
        if host_evidence.get("status") != "unique":
            shared.append(host_evidence)
            continue
        host_missions = list(host_evidence.get("hostMissionIds") or [])
        if len(host_missions) != 1:
            continue
        target_mission = str(host_missions[0] or "")
        if target_mission not in available_missions:
            continue
        enriched = dict(occurrence)
        enriched["levelDataHosts"] = list(host_evidence.get("hosts") or [])
        enriched["scopeEvidenceKinds"] = [
            "mission_leveldata_member22_contains_validated_levelscript_brief"
        ]
        scoped[target_mission].append(enriched)
    return scoped, shared


def collect_native_story_occurrences(
    native_story_playback_index: dict[str, list[dict]],
    *story_keys: str,
) -> list[dict]:
    """Collect exact native occurrences across authored/emitted Story aliases."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for story_key in dict.fromkeys(story_keys):
        for occurrence in native_story_playback_index.get(story_key) or []:
            signature = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
                str(occurrence.get("sourceFile") or ""),
                occurrence.get("recordOffset"),
                str(occurrence.get("actionName") or ""),
            )
            if signature in seen:
                continue
            seen.add(signature)
            out.append(occurrence)
    return out


def filter_native_story_playback_index(
    native_story_playback_index: dict[str, list[dict]],
    emitted_story_keys: set[str],
    suppressed_fmv_pairs: set[tuple[str, str]] | None = None,
) -> dict[str, list[dict]]:
    """Keep native playback identities that have an emitted Story page.

    Native FMV ids normalize mechanically from ``cs_video_X`` to
    ``cutscene_X``. Manual video overrides can intentionally expose a video
    under a different Story key, so an absent canonical page must not become a
    ghost runtime node or an implicit override relation.
    """
    suppressed = suppressed_fmv_pairs or set()
    out: dict[str, list[dict]] = {}
    for story_key, rows in native_story_playback_index.items():
        if story_key not in emitted_story_keys:
            continue
        retained = [
            row
            for row in rows
            if (
                story_key,
                str((row.get("fmvAction") or {}).get("fmvId") or "").lower(),
            )
            not in suppressed
        ]
        if retained:
            out[story_key] = retained
    return out


def filter_non_fmv_story_playback_index(
    native_story_playback_index: dict[str, list[dict]],
) -> dict[str, list[dict]]:
    """Remove FMV rows from generic mission-context promotion paths.

    FMV placement is intentionally centralized in the exact LevelData shell
    joins below, where every serialized occurrence must resolve to the same
    mission. Other native Story actions may still use their specialized event,
    entity, property, or mission-state context recovery.
    """
    return {
        story_key: retained
        for story_key, rows in native_story_playback_index.items()
        if (
            retained := [
                row for row in rows if row.get("recordClass") != "play_fmv"
            ]
        )
    }


def native_fmv_scope_is_complete(
    occurrences: list[dict],
    scoped_by_mission: dict[str, list[dict]],
    shared_hosts: list[dict],
) -> bool:
    """Require every exact FMV occurrence to agree on one mission shell.

    A cutscene can be invoked by several authored LevelScripts. Selecting the
    convenient hosted subset would conceal an unowned or conflicting route,
    so FMV ownership stays unresolved unless the complete occurrence set is
    scoped and unanimous. Other long-standing playback families retain their
    existing partial-shell diagnostics.
    """
    if not any(row.get("recordClass") == "play_fmv" for row in occurrences):
        return True
    return bool(
        occurrences
        and not shared_hosts
        and len(scoped_by_mission) == 1
        and sum(len(rows) for rows in scoped_by_mission.values())
        == len(occurrences)
    )


def collect_dialog_tree_completion_parent_quests(
    raw_mission_flows: dict[str, dict],
    eligible_parent_keys: set[str],
) -> dict[str, dict[tuple[str, str], list[dict]]]:
    """Index exact MissionRuntime completion observers for DialogTree roots.

    Some registered controller roots emit no Story page and are therefore
    removed by normal localized Story filtering. Preserve only their original
    ``CheckTalkOptionFinish._dialogId`` rows here; observing completion is
    dependency context and never proof that the quest launches playback.
    """
    out: dict[str, dict[tuple[str, str], list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for mission_id, flow in raw_mission_flows.items():
        if not isinstance(flow, dict):
            continue
        for quest in flow.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            quest_id = str(quest.get("id") or "")
            if not quest_id:
                continue
            for row in quest.get("storyConnections") or []:
                if not isinstance(row, dict):
                    continue
                parent_key = str(row.get("key") or "")
                source = str(row.get("source") or "")
                if (
                    parent_key not in eligible_parent_keys
                    or row.get("relation") != "objective_condition"
                    or row.get("conditionType") != "CheckTalkOptionFinish"
                    or row.get("confidence") != "direct"
                    or not source.endswith(".condition._dialogId")
                ):
                    continue
                out[parent_key][(str(mission_id), quest_id)].append({
                    **row,
                    "missionId": str(mission_id),
                    "questId": quest_id,
                })
    return {
        parent_key: dict(rows_by_target)
        for parent_key, rows_by_target in out.items()
    }


def unique_dialog_tree_prime_parent_groups(
    groups: dict[tuple[str, str], list[dict]],
) -> dict[str, tuple[str, list[dict]]]:
    """Keep Story targets that have exactly one prime-reachable parent root.

    A child reachable from multiple registered parents must not inherit the
    lexically first parent's mission. Even agreeing parent scopes stay
    unresolved until the runtime relationship between those roots is proved.
    """
    by_story: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    for (story_key, dialog_key), rows in groups.items():
        if story_key and dialog_key and rows:
            by_story[story_key].append((dialog_key, rows))
    return {
        story_key: candidates[0]
        for story_key, candidates in by_story.items()
        if len(candidates) == 1
    }


def collect_globally_attached_story_keys(
    mission_flows_payload: dict[str, dict],
    preexisting_by_mission: dict[str, set[str]],
) -> set[str]:
    """Collect every Story key attached anywhere in the accumulated flows.

    The auxiliary preexisting index is intentionally not treated as complete:
    some older connection families are materialized directly in mission or
    quest payloads.  A new fallback shell relation must inspect both surfaces
    or it can duplicate hundreds of already-proven bindings.
    """
    attached = {
        str(story_key)
        for story_keys in preexisting_by_mission.values()
        for story_key in story_keys
        if story_key
    }
    for flow_payload in mission_flows_payload.values():
        if not isinstance(flow_payload, dict):
            continue
        attached.update(
            str(row.get("key") or "")
            for row in flow_payload.get("missionStoryConnections") or []
            if isinstance(row, dict) and row.get("key")
        )
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            attached.update(
                str(row.get("key") or "")
                for row in quest.get("storyConnections") or []
                if isinstance(row, dict) and row.get("key")
            )
    attached.discard("")
    return attached


def select_dialog_tree_story_carrier_scope(
    direct_quests: dict[tuple[str, str], list[dict]],
    derived_quests: dict[tuple[str, str], list[dict]],
    mission_contexts: dict[str, list[dict]],
) -> dict:
    """Select one non-transitive parent scope for a DialogTree carrier.

    Direct quest lifecycle evidence takes priority over derived exact context.
    Independently authored mission context remains an agreement/veto signal in
    both cases.  Multiple quests may still prove one mission shell, but never
    one favorable quest.
    """
    selected_quests = direct_quests if direct_quests else derived_quests
    quest_evidence = "direct" if direct_quests else "derived" if derived_quests else "none"
    candidate_missions = {
        str(mission_id)
        for mission_id, _quest_id in selected_quests
        if mission_id
    }
    candidate_missions.update(
        str(mission_id)
        for mission_id, rows in mission_contexts.items()
        if mission_id and rows
    )
    if not candidate_missions:
        return {"status": "missing_parent_scope"}
    if len(candidate_missions) != 1:
        return {
            "status": "conflicting_parent_missions",
            "candidateMissionIds": sorted(candidate_missions),
        }
    mission_id = next(iter(candidate_missions))
    matching_quests = {
        target: rows
        for target, rows in selected_quests.items()
        if target[0] == mission_id and rows
    }
    if len(matching_quests) == 1:
        mission, quest_id = next(iter(matching_quests))
        return {
            "status": "accepted_unique_parent_quest",
            "scopeKind": "quest",
            "missionId": mission,
            "questId": quest_id,
            "questEvidence": quest_evidence,
            "questRows": matching_quests[(mission, quest_id)],
            "missionContextRows": list(mission_contexts.get(mission) or []),
        }
    return {
        "status": "accepted_unique_parent_mission",
        "scopeKind": "mission",
        "missionId": mission_id,
        "questEvidence": quest_evidence,
        "candidateQuestIds": sorted({
            quest_id
            for quest_mission, quest_id in matching_quests
            if quest_mission == mission_id and quest_id
        }),
        "questRows": [
            row
            for rows in matching_quests.values()
            for row in rows
        ],
        "missionContextRows": list(mission_contexts.get(mission_id) or []),
    }


def select_cross_story_quest_state_carrier_scope(
    occurrence_rows: list[dict],
    quest_targets: dict[str, tuple[str, dict]],
) -> dict:
    """Resolve child-specific DialogTree gates to one mission, never one quest.

    Every occurrence must carry an all-leaf quest-state condition with an
    explicit no-bypass proof. Every serialized quest id must resolve to a
    recovered MissionRuntime quest, and all must agree on one mission. This
    context is intentionally stronger than a conflicting parent-dialog shell,
    but remains dependency/playback-route context rather than ownership.
    """
    if not occurrence_rows:
        return {}
    contexts: list[dict] = []
    quest_ids: set[str] = set()
    for occurrence in occurrence_rows:
        occurrence_contexts = [
            row
            for row in occurrence.get("questStateBranchContexts") or []
            if isinstance(row, dict)
            and row.get("noBypass") is True
            and row.get("conditions")
        ]
        if not occurrence_contexts:
            return {}
        contexts.extend(occurrence_contexts)
        for context in occurrence_contexts:
            context_quest_ids = {
                str(quest_id or "").strip()
                for quest_id in context.get("questIds") or []
                if str(quest_id or "").strip()
            }
            if not context_quest_ids:
                return {}
            quest_ids.update(context_quest_ids)
    resolved_targets = {
        quest_id: quest_targets.get(quest_id)
        for quest_id in sorted(quest_ids)
    }
    if any(not target for target in resolved_targets.values()):
        return {}
    missions = {
        str(target[0] or "")
        for target in resolved_targets.values()
        if target
    }
    missions.discard("")
    if len(missions) != 1:
        return {}
    mission_id = next(iter(missions))
    context_row = {
        "relation": "dialog_tree_quest_state_carrier_context",
        "missionId": mission_id,
        "candidateQuestIds": sorted(quest_ids),
        "questStateBranchContexts": contexts,
        "storyBinding": True,
        "ownership": False,
        "dependencyOnly": True,
        "possibleAuthoredRoute": True,
    }
    return {
        "status": "accepted_cross_story_quest_state_carrier_context",
        "scopeKind": "mission",
        "missionId": mission_id,
        "questEvidence": "derived",
        "candidateQuestIds": sorted(quest_ids),
        "questRows": [],
        "missionContextRows": [context_row],
        "carrierQuestStateContext": context_row,
    }


def build_npc_proxy_tracking_dialog_navigation_contexts(
    npc_tracking_consumers: dict[str, list[dict]],
    npc_proxy_rows: dict,
    npc_proxy_ex: dict,
    world_entity_registry: dict,
    dialog_id_registry: dict[str, dict],
    dialog_tree_story_playback_groups: dict[tuple[str, str], list[dict]],
) -> list[dict]:
    """Join one tracked proxy to one registered parent and typed child route.

    This is a navigation/configuration relation. ``NpcProxyTrackingInfo`` only
    resolves AOI position, while the server-selected active condition chooses
    the interaction row independently. Ambiguous consumers, scenes, registry
    identities, nonempty mission-owner rows, parent dialogs, or child carrier
    types therefore fail closed.
    """
    ex_rows_by_proxy = (npc_proxy_ex or {}).get("data") or {}
    registry_rows_by_proxy: dict[str, list[dict]] = defaultdict(list)
    for raw_key, raw_row in (
        (world_entity_registry or {}).get("npcProxyBriefInfos") or {}
    ).items():
        if not isinstance(raw_row, dict):
            continue
        proxy_id = str(raw_row.get("proxyId") or "").strip()
        segment_id = raw_row.get("segmentIdGlobal")
        try:
            dictionary_id = int(raw_key)
        except (TypeError, ValueError):
            continue
        if (
            not proxy_id
            or isinstance(segment_id, bool)
            or not isinstance(segment_id, int)
            or segment_id <= 0
            or dictionary_id != segment_id
        ):
            continue
        registry_rows_by_proxy[proxy_id].append({
            "dictionaryKey": str(raw_key),
            "segmentIdGlobal": segment_id,
            "proxyId": proxy_id,
            "position": raw_row.get("position"),
        })

    child_routes_by_parent: dict[str, list[dict]] = defaultdict(list)
    for (child_story_key, parent_story_key), occurrences in sorted(
        dialog_tree_story_playback_groups.items()
    ):
        typed_occurrences = [
            row
            for row in occurrences
            if isinstance(row, dict)
            and row.get("carrierKind") == "dialog"
            and str(row.get("dialogId") or "") == child_story_key
            and str(row.get("dialogKey") or "") == parent_story_key
        ]
        if not typed_occurrences or len(typed_occurrences) != len(occurrences):
            continue
        child_routes_by_parent[parent_story_key].append({
            "childStoryKey": child_story_key,
            "occurrences": typed_occurrences,
        })

    def positions_match(left: object, right: object) -> bool:
        if not isinstance(left, dict) or not isinstance(right, dict):
            return False
        try:
            return all(
                abs(float(left[axis]) - float(right[axis])) <= 0.000001
                for axis in ("x", "y", "z")
            )
        except (KeyError, TypeError, ValueError):
            return False

    out: list[dict] = []
    for proxy_id, consumers in sorted(npc_tracking_consumers.items()):
        if len(consumers) != 1:
            continue
        consumer = consumers[0]
        mission_id = str(consumer.get("missionId") or "").strip()
        quest_id = str(consumer.get("questId") or "").strip()
        scene_id = str(consumer.get("scene") or "").strip()
        proxy_row = (npc_proxy_rows or {}).get(proxy_id)
        registry_rows = registry_rows_by_proxy.get(proxy_id) or []
        ex_rows = (ex_rows_by_proxy or {}).get(proxy_id) or []
        if (
            not mission_id
            or not quest_id
            or not scene_id
            or not isinstance(proxy_row, dict)
            or str(proxy_row.get("proxyId") or "") != proxy_id
            or str(proxy_row.get("levelId") or "") != scene_id
            or len(registry_rows) != 1
            or not isinstance(ex_rows, list)
            or not ex_rows
            or not positions_match(
                proxy_row.get("position"),
                registry_rows[0].get("position"),
            )
        ):
            continue
        valid_ex_rows = [row for row in ex_rows if isinstance(row, dict)]
        if len(valid_ex_rows) != len(ex_rows):
            continue
        # Any authored mission owner belongs to the stricter existing same-row
        # ownership path. This fallback is only for missionless interaction
        # rows and must not select around a conflicting owner.
        if any(str(row.get("missionId") or "").strip() for row in valid_ex_rows):
            continue
        parent_dialogs = sorted({
            str(row.get("dialogId") or "").strip()
            for row in valid_ex_rows
            if str(row.get("dialogId") or "").strip()
        })
        if len(parent_dialogs) != 1:
            continue
        parent_story_key = parent_dialogs[0]
        registration = dialog_id_registry.get(parent_story_key)
        child_routes = child_routes_by_parent.get(parent_story_key) or []
        if (
            not isinstance(registration, dict)
            or registration.get("registered") is not True
            or registration.get("memoryPackRecordKey") is not True
            or "memorypack_record_key"
            not in (registration.get("registrationEvidence") or [])
            or not child_routes
        ):
            continue
        out.append({
            "missionId": mission_id,
            "questId": quest_id,
            "npcProxyId": proxy_id,
            "levelId": scene_id,
            "parentStoryKey": parent_story_key,
            "childStoryKeys": sorted({
                str(route.get("childStoryKey") or "")
                for route in child_routes
                if route.get("childStoryKey")
            }),
            "trackingConsumer": consumer,
            "trackingVisibilityFilter": consumer.get(
                "trackingVisibilityFilter"
            ),
            "npcProxyTableRow": {
                "proxyId": proxy_id,
                "levelId": scene_id,
                "subDataParentId": proxy_row.get("subDataParentId"),
                "position": proxy_row.get("position"),
            },
            "npcProxyRegistryRow": registry_rows[0],
            "npcProxyExRows": valid_ex_rows,
            "dialogTreeChildRoutes": child_routes,
            "relation": "npc_proxy_tracking_dialog_navigation_context",
            "storyBinding": True,
            "ownership": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "serverExchange": False,
        })
    return out


def build_npc_proxy_lazy_destroy_dialog_contexts(
    npc_tracking_consumers: dict[str, list[dict]],
    npc_proxy_rows: dict,
    available_story_keys: set[str],
) -> list[dict]:
    """Bind a tracked NPC proxy to its authored lazy-destroy dialog override.

    The installed runtime stores ``lazyDestroyOverrideDialogId`` on
    ``NpcRuntimeProxyData`` and, during ``NpcProxy.OnDeActive``, passes it to
    ``NpcProxyMgr.ApplyLazyDestroyData``.  That method calls
    ``NpcManager.AddOverrideInteractDialogId`` for the same NPC.  This proves
    that the table field is an executable dialog carrier.  It still does not
    prove that the tracking quest deactivates the proxy, so the accepted edge
    remains navigation/configuration context only.

    Require one exact same-scene typed tracking consumer.  Reused proxies,
    disabled lazy destruction, missing Story definitions, aliases that resolve
    more than once, and row/proxy identity mismatches all fail closed.
    """
    out: list[dict] = []
    for proxy_id, raw_row in sorted((npc_proxy_rows or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        dialog_id = str(
            raw_row.get("lazyDestroyOverrideDialogId") or ""
        ).strip()
        resolved_story_keys = [
            candidate
            for candidate in (dialog_id, f"misc_{dialog_id}")
            if candidate and candidate in available_story_keys
        ]
        consumers = list((npc_tracking_consumers or {}).get(proxy_id) or [])
        if (
            not proxy_id
            or str(raw_row.get("proxyId") or "").strip() != proxy_id
            or raw_row.get("lazyDestroy") is not True
            or not dialog_id
            or len(resolved_story_keys) != 1
            or len(consumers) != 1
            or not isinstance(consumers[0], dict)
        ):
            continue
        consumer = consumers[0]
        mission_id = str(consumer.get("missionId") or "").strip()
        quest_id = str(consumer.get("questId") or "").strip()
        scene_id = str(consumer.get("scene") or "").strip()
        if (
            not mission_id
            or not quest_id
            or not scene_id
            or str(raw_row.get("levelId") or "").strip() != scene_id
        ):
            continue
        out.append({
            "missionId": mission_id,
            "questId": quest_id,
            "npcProxyId": proxy_id,
            "levelId": scene_id,
            "dialogId": dialog_id,
            "storyKey": resolved_story_keys[0],
            "trackingConsumer": consumer,
            "npcProxyTableRow": {
                "proxyId": proxy_id,
                "levelId": scene_id,
                "subDataParentId": raw_row.get("subDataParentId"),
                "lazyDestroy": True,
                "lazyDestroyOverrideDialogId": dialog_id,
            },
            "relation": "npc_proxy_lazy_destroy_dialog_context",
            "storyBinding": True,
            "ownership": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "serverExchange": True,
            "clientRequest": False,
            "expectedClientReply": False,
        })
    return out


def attach_unconnected_mission_shell_fallbacks(
    mission_flows_payload: dict[str, dict],
    preexisting_by_mission: dict[str, set[str]],
    pending: list[tuple[str, str, dict]],
) -> list[tuple[str, str]]:
    """Append fallback shell edges only after stronger flows are complete."""
    attached = collect_globally_attached_story_keys(
        mission_flows_payload,
        preexisting_by_mission,
    )
    emitted: list[tuple[str, str]] = []
    for target_mission, story_key, connection in pending:
        if not target_mission or not story_key or story_key in attached:
            continue
        flow_payload = mission_flows_payload.get(target_mission)
        if not isinstance(flow_payload, dict):
            continue
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_by_mission.setdefault(target_mission, set()).add(story_key)
        attached.add(story_key)
        emitted.append((target_mission, story_key))
    return emitted


def build_domain_depot_story_connections(
    domain_const: dict,
    dialog_rows: dict,
    target_rows: dict,
    available_missions: set[str],
) -> list[dict]:
    """Join depot delivery dialogs to the exact configured mission shell.

    The join is deliberately table-typed: ``DomainDepotConst`` supplies the
    MissionRuntime id, the dialog-table key must equal its ``npcProxyId``, and
    at least one delivery-target row must carry that same ``targetId``.  Story
    names and filename prefixes are never consulted.
    """
    mission_id = str((domain_const or {}).get("depotDeliverMissionId") or "").strip()
    if mission_id not in available_missions:
        return []
    targets_by_id: dict[str, list[dict]] = defaultdict(list)
    for row_key, raw_row in sorted((target_rows or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        target_id = str(raw_row.get("targetId") or "").strip()
        if not target_id:
            continue
        targets_by_id[target_id].append({
            "rowKey": str(row_key),
            "deliverTargetId": str(raw_row.get("deliverTargetId") or ""),
            "targetId": target_id,
            "domainId": str(raw_row.get("domainId") or ""),
            "levelId": str(raw_row.get("level") or ""),
            "entityType": raw_row.get("entityType"),
        })
    out: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for row_key, raw_row in sorted((dialog_rows or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        npc_proxy_id = str(raw_row.get("npcProxyId") or "").strip()
        if not npc_proxy_id or str(row_key) != npc_proxy_id:
            continue
        target_matches = targets_by_id.get(npc_proxy_id) or []
        if not target_matches:
            continue
        for dialog_field, dialog_phase in (
            ("initialDialogId", "initial_delivery_dialog"),
            ("repeatDialogId", "repeat_delivery_dialog"),
        ):
            story_key = str(raw_row.get(dialog_field) or "").strip()
            signature = (mission_id, story_key, dialog_field)
            if not story_key or signature in seen:
                continue
            seen.add(signature)
            out.append({
                "missionId": mission_id,
                "key": story_key,
                "npcProxyId": npc_proxy_id,
                "dialogTableKey": str(row_key),
                "dialogField": dialog_field,
                "dialogPhase": dialog_phase,
                "deliverTargets": target_matches,
                "sourceTables": [
                    "DomainDepotConst.json",
                    "DomainDepotDeliverTargetDialogTable.json",
                    "DomainDepotDeliverTargetTable.json",
                ],
            })
    return out


def build_skip_chapter_story_connections(
    skip_rows: dict,
    available_missions: set[str],
) -> list[dict]:
    """Return exact same-row SkipChapter mission/dialog foreign keys."""
    out: list[dict] = []
    for row_key, raw_row in sorted((skip_rows or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        config_id = str(raw_row.get("skipChapterConfigId") or "").strip()
        mission_id = str(raw_row.get("missionId") or "").strip()
        story_key = str(raw_row.get("bindDlgId") or "").strip()
        if (
            not config_id
            or str(row_key) != config_id
            or mission_id not in available_missions
            or not story_key
        ):
            continue
        out.append({
            "missionId": mission_id,
            "key": story_key,
            "skipChapterConfigId": config_id,
            "bindActivityId": str(raw_row.get("bindActivityId") or ""),
            "sourceTables": ["SkipChapterTable.json"],
        })
    return out


def build_factory_lock_story_dependencies(
    lock_rows: dict,
    quest_targets: dict[str, tuple[str, dict]],
) -> list[dict]:
    """Resolve factory-panel radio gates through exact authored quest ids.

    These rows describe a local quest-state consumer, not a Story owner.  A
    dependency is emitted only for a quest id already present in a recovered
    MissionRuntime; no mission id is parsed from the radio or quest string.
    """
    out: list[dict] = []
    for row_key, raw_row in sorted((lock_rows or {}).items()):
        if not isinstance(raw_row, dict):
            continue
        for condition_index, condition in enumerate(raw_row.get("list") or []):
            if not isinstance(condition, dict):
                continue
            story_key = str(condition.get("radioId") or "").strip()
            if not story_key:
                continue
            roles_by_mission: dict[str, list[dict]] = defaultdict(list)
            for quest_field in ("startQuestId", "endQuestId"):
                quest_id = str(condition.get(quest_field) or "").strip()
                quest_target = quest_targets.get(quest_id)
                if not quest_id or not quest_target:
                    continue
                mission_id = str(quest_target[0] or "").strip()
                if mission_id:
                    roles_by_mission[mission_id].append({
                        "field": quest_field,
                        "questId": quest_id,
                    })
            for mission_id, quest_roles in sorted(roles_by_mission.items()):
                out.append({
                    "missionId": mission_id,
                    "key": story_key,
                    "factoryBuildingId": str(row_key),
                    "conditionIndex": condition_index,
                    "lockType": condition.get("lockType"),
                    "priority": condition.get("priority"),
                    "args": list(condition.get("args") or []),
                    "startQuestId": str(condition.get("startQuestId") or ""),
                    "endQuestId": str(condition.get("endQuestId") or ""),
                    "questGateRoles": quest_roles,
                    "sourceTables": ["FactoryBuildingPanelLock.json"],
                })
    return out


def is_exact_processing_mission_state_story_context(
    route: dict,
    target_mission: str,
) -> bool:
    """Admit only a single exact ``mission == Processing`` true branch.

    Other exact mission-state gates remain valuable dependencies, but
    ``!= Completed`` spans five states, completed branches are post-mission,
    and multi-mission paths do not prove one active mission shell.
    """
    gates = [
        gate
        for gate_path in route.get("gatePaths") or []
        for gate in gate_path.get("missionStateGates") or []
        if isinstance(gate, dict)
    ]
    return bool(
        target_mission
        and list(route.get("gateMissionIds") or []) == [target_mission]
        and len(gates) == 1
        and gates[0].get("missionId") == target_mission
        and gates[0].get("comparerName") == "Equal"
        and gates[0].get("expectedStateName") == "Processing"
        and gates[0].get("selectedBranch") == "true"
    )


def is_typed_dialog_tree_runtime_action_connection(
    connection: dict,
    available_story_keys: set[str],
    open_ui_actions_by_dialog: dict[str, list[dict]],
) -> bool:
    dialog_key = str(connection.get("key") or "").strip()
    return bool(
        dialog_key
        and dialog_key not in available_story_keys
        and dialog_key in open_ui_actions_by_dialog
        and connection.get("event") == "LevelEvent_OnQuestStateChanged"
        and connection.get("actionName") == "StartDialogAction"
        and connection.get("relation") in {
            "levelscript_quest_processing_action",
            "levelscript_quest_completed_action",
        }
    )


def quest_attached_dialog_tree_runtime_actions(
    quest: dict,
    available_story_keys: set[str],
    open_ui_actions_by_dialog: dict[str, list[dict]],
) -> list[dict]:
    """Separate typed action-only DialogTrees from Story-file attachments."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for connection in quest.get("storyConnections") or []:
        if not isinstance(connection, dict):
            continue
        dialog_key = str(connection.get("key") or "").strip()
        if not is_typed_dialog_tree_runtime_action_connection(
            connection,
            available_story_keys,
            open_ui_actions_by_dialog,
        ):
            continue
        for action in open_ui_actions_by_dialog.get(dialog_key) or []:
            signature = (
                dialog_key,
                connection.get("levelId"),
                connection.get("scriptId"),
                connection.get("headerLocalId"),
                connection.get("actionLocalId"),
                action.get("sourceFile"),
                action.get("nodeId"),
            )
            if signature in seen:
                continue
            seen.add(signature)
            out.append({
                "kind": "dialog_tree_action",
                "terminalKind": "open_ui",
                "dialogKey": dialog_key,
                "relation": "levelscript_quest_dialog_tree_action",
                "direction": "quest_to_runtime_action",
                "phase": connection.get("phase") or "unknown",
                "confidence": "native_typed_direct",
                "storyBinding": False,
                "panelType": action.get("panelType"),
                "actionEnum": action.get("actionEnum"),
                "param": action.get("param") or "",
                "paramData": dict(action.get("paramData") or {}),
                "finishIds": list(action.get("finishIds") or []),
                "levelId": connection.get("levelId") or "",
                "scriptId": connection.get("scriptId") or "",
                "headerLocalId": connection.get("headerLocalId"),
                "actionLocalId": connection.get("actionLocalId"),
                "questState": connection.get("questState"),
                "questStateName": connection.get("questStateName") or "",
                "source": connection.get("source") or "",
                "dialogTreeSource": action.get("sourceFile") or "",
                "dialogTreeNodeId": action.get("nodeId") or "",
                "sourceType": action.get("sourceType") or "",
            })
    return out


def select_unique_original_parent_mission(
    scoped_occurrences: dict[str, list[dict]],
    shared_shells: list[dict],
    occurrence_count: int,
    parent_contexts: dict[str, list[dict]],
) -> str:
    """Return one mission only when every original-data parent scope agrees."""
    if (
        occurrence_count <= 0
        or shared_shells
        or sum(len(rows) for rows in scoped_occurrences.values())
        != occurrence_count
    ):
        return ""
    candidates = set(scoped_occurrences)
    candidates.update(parent_contexts)
    return next(iter(candidates)) if len(candidates) == 1 else ""


def select_unique_typed_mission_area_parent_mission(
    scoped_occurrences: dict[str, list[dict]],
    shared_shells: list[dict],
    occurrence_count: int,
    parent_contexts: dict[str, list[dict]],
) -> tuple[str, dict[str, list[dict]]]:
    """Prefer typed MissionArea ownership over LevelData filename parsing.

    ``MissionAreaTrackingInfo.missionAreaId`` joined through the exact
    ``MissionAreaTable.subDataParentId`` and an identical validated LevelData
    member-22 root is serialized ownership evidence. A mission token parsed
    from the LevelData filename is not, so it cannot veto that typed join.
    Other exact parent contexts still participate and must agree.
    """
    admissible_contexts: dict[str, list[dict]] = {}
    for mission_id, rows in parent_contexts.items():
        retained = [
            row
            for row in rows
            if str(row.get("relation") or "")
            != "leveldata_levelscript_mission_context"
        ]
        if retained:
            admissible_contexts[mission_id] = retained
    return (
        select_unique_original_parent_mission(
            scoped_occurrences,
            shared_shells,
            occurrence_count,
            admissible_contexts,
        ),
        admissible_contexts,
    )

@_radio_cont_lru_cache(maxsize=2)
def _load_story_order_overrides(path_str: str) -> dict[str, list[str]]:
    """Load {missionId: [orderedSceneKey, ...]} from the story-order override.
    Used only to widen the additive sceneOrderInfo candidate set so it matches
    the order-compare report's keyInfo coverage (override-only scene keys).
    """
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    payload = _radio_cont_json.loads(path.read_text(encoding="utf-8-sig"))
    missions = payload.get("missions") if isinstance(payload, dict) else {}
    out: dict[str, list[str]] = {}
    if isinstance(missions, dict):
        for mission_id, row in missions.items():
            order = (row or {}).get("order") if isinstance(row, dict) else None
            if isinstance(order, list):
                out[str(mission_id)] = [str(key) for key in order if key]
    return out

def _normalize_video_override_stem(value: object) -> str:
    text = str(value or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.rsplit("/", 1)[-1]
    return _radio_cont_re.sub(r"\.[^.]+$", "", text, flags=_radio_cont_re.IGNORECASE).lower()

@_radio_cont_lru_cache(maxsize=2)
def _load_narrative_video_overrides(path_str: str) -> dict[str, dict[str, list[dict]]]:
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {"suppressInline": {}, "attachInline": {}}
    try:
        payload = _radio_cont_json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, _radio_cont_json.JSONDecodeError):
        return {"suppressInline": {}, "attachInline": {}}
    if not isinstance(payload, dict):
        return {"suppressInline": {}, "attachInline": {}}
    out: dict[str, dict[str, list[dict]]] = {
        "suppressInline": {},
        "attachInline": {},
    }
    def add_rule(bucket: dict[str, list[dict]], target_key: object, raw_rule: object) -> None:
        key = str(target_key or "").strip()
        if not key:
            return
        note = ""
        raw_stems: object = []
        if isinstance(raw_rule, dict):
            note = str(raw_rule.get("note") or "")
            raw_stems = (
                raw_rule.get("stems")
                or raw_rule.get("videoStems")
                or raw_rule.get("stem")
                or raw_rule.get("videoStem")
                or []
            )
        elif isinstance(raw_rule, list):
            raw_stems = raw_rule
        elif raw_rule:
            raw_stems = [raw_rule]
        if isinstance(raw_stems, (str, int, float)):
            raw_stems = [raw_stems]
        stems = sorted({
            normalized
            for normalized in (_normalize_video_override_stem(value) for value in (raw_stems or []))
            if normalized
        })
        bucket.setdefault(key, []).append({
            "targetKey": key,
            "stems": stems,
            "note": note,
            "source": path,
        })
    def add_rules(bucket_name: str, raw_rules: object) -> None:
        bucket = out[bucket_name]
        if isinstance(raw_rules, dict):
            for target_key, raw_rule in raw_rules.items():
                add_rule(bucket, target_key, raw_rule)
        elif isinstance(raw_rules, list):
            for raw_rule in raw_rules:
                if not isinstance(raw_rule, dict):
                    continue
                target_key = (
                    raw_rule.get("targetKey")
                    or raw_rule.get("key")
                    or raw_rule.get("resolvedKey")
                    or raw_rule.get("attachTo")
                )
                add_rule(bucket, target_key, raw_rule)
    add_rules("suppressInline", payload.get("suppressInline"))
    add_rules("attachInline", payload.get("attachInline") or payload.get("attachTo"))
    return out

def _manual_option_group_override(conv_key: str, group_id: int) -> dict:
    # Runtime WebUI overrides now live in webui/overrides/options.json
    # and are applied by webui/app.js so users can edit them without rebuilding
    # generated conversation JSON.
    return {}

@_radio_cont_lru_cache(maxsize=2)
def _load_radio_continuation_candidates_by_mission(
    path_str: str,
) -> dict[str, list[dict]]:
    """Load the radio-continuation audit report keyed by mission id.
    Each value is a list of `(predecessor, radio, match, levelId, file)` dicts.
    Returns an empty dict when the report has not been generated yet, so the
    builder degrades to its prior behavior cleanly.
    """
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    try:
        payload = _radio_cont_json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, _radio_cont_json.JSONDecodeError):
        return {}
    out: dict[str, list[dict]] = {}
    for result in payload.get("results") or []:
        mission = result.get("mission") or ""
        if not mission:
            continue
        out.setdefault(mission, []).extend(result.get("candidates") or [])
    return out

@_radio_cont_lru_cache(maxsize=2)
def _load_fmv_clips_by_webui_key(path_str: str) -> dict[str, list[dict]]:
    """Load `reports/playable_director/fmv_clip_by_webui_key.json`.
    Returns `{webui_key: [{fmvId, clipStart, clipDuration, ...}, ...]}` or
    an empty dict when the report has not been generated yet. The builder
    surfaces these as per-conv `fmvClips` meta so the WebUI can display
    authored FMV timing for cutscene/dialog stories that bind to a
    `BeyondFMVPlayableAsset` clip.
    """
    path = _RadioContPath(path_str)
    if not path.is_file():
        return {}
    try:
        payload = _radio_cont_json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, _radio_cont_json.JSONDecodeError):
        return {}
    mappings = payload.get("mappings")
    return mappings if isinstance(mappings, dict) else {}

def load_reused_reference_stats(reference_dir: Path, language_code: str) -> dict:
    """Validate an existing localized reference bundle before preserving it."""
    index_path = reference_dir / "index.json"
    try:
        payload = _radio_cont_json.loads(index_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, _radio_cont_json.JSONDecodeError):
        payload = None
    if not isinstance(payload, dict):
        raise RuntimeError(
            f"cannot reuse reference bundle: missing or invalid {index_path}"
        )
    if str(payload.get("language") or "").upper() != language_code.upper():
        raise RuntimeError(
            f"cannot reuse reference bundle: {index_path} belongs to "
            f"{payload.get('language')!r}, not {language_code!r}"
        )
    tables = payload.get("tables")
    stats = payload.get("stats")
    if not isinstance(tables, list) or not isinstance(stats, dict):
        raise RuntimeError(
            f"cannot reuse reference bundle: {index_path} lacks tables/stats"
        )
    try:
        table_count = int(stats.get("tables"))
        row_count = int(stats.get("rows"))
        text_count = int(stats.get("texts"))
        byte_count = int(stats.get("bytes"))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(
            f"cannot reuse reference bundle: {index_path} has invalid stats"
        ) from exc
    if table_count != len(tables) or min(
        table_count,
        row_count,
        text_count,
        byte_count,
    ) < 0:
        raise RuntimeError(
            f"cannot reuse reference bundle: {index_path} stats do not match its table index"
        )

    reference_root = reference_dir.resolve()
    checked_files: set[Path] = set()
    for table in tables:
        if not isinstance(table, dict):
            raise RuntimeError(
                f"cannot reuse reference bundle: {index_path} has a malformed table row"
            )
        for field in ("file", "baseFile"):
            raw_rel = str(table.get(field) or "").strip().replace("\\", "/")
            if not raw_rel:
                continue
            rel_path = Path(raw_rel)
            if rel_path.is_absolute() or ".." in rel_path.parts:
                raise RuntimeError(
                    f"cannot reuse reference bundle: unsafe {field} path {raw_rel!r}"
                )
            candidate = (reference_dir / rel_path).resolve()
            if not candidate.is_relative_to(reference_root):
                raise RuntimeError(
                    f"cannot reuse reference bundle: unsafe {field} path {raw_rel!r}"
                )
            if candidate in checked_files:
                continue
            checked_files.add(candidate)
            if not candidate.is_file():
                raise RuntimeError(
                    f"cannot reuse reference bundle: indexed file is missing: {candidate}"
                )
    return {
        "tables": table_count,
        "rows": row_count,
        "texts": text_count,
        "bytes": byte_count,
    }


def build_language_bundle(
    language_code: str,
    out_dir: Path,
    *,
    profile: str = DEFAULT_BUILD_PROFILE,
    write_reference: bool = True,
    reuse_reference: bool = False,
) -> dict:
    if profile not in BUILD_PROFILES:
        raise ValueError(f"unknown build profile: {profile}")
    include_reference_in_story_index = profile == "full"
    i18n_table_name = f"I18nTextTable_{language_code}.json"
    i18n_table_key = i18n_table_name.removesuffix(".json")
    t0 = time.time()
    conv_dir = out_dir / "conv"
    reference_dir = out_dir / "reference"
    mission_dir = out_dir / "mission"
    out_dir.mkdir(parents=True, exist_ok=True)
    conv_dir.mkdir(parents=True, exist_ok=True)
    if reuse_reference and not write_reference:
        raise ValueError("reuse_reference requires write_reference=True")
    if write_reference and not reuse_reference:
        reference_dir.mkdir(parents=True, exist_ok=True)
    elif not reuse_reference:
        shutil.rmtree(reference_dir, ignore_errors=True)
    dialog_id_registry = shared_load_dialog_id_registry()
    story_source_links = load_story_source_links()
    dialog_tree_open_ui_actions_by_key: dict[str, list[dict]] = defaultdict(list)
    for row in recover_dialog_tree_open_ui_actions():
        dialog_key = str(row.get("dialogKey") or "").strip()
        if dialog_key:
            dialog_tree_open_ui_actions_by_key[dialog_key].append(row)
    narrative_video_assets = _load_narrative_video_assets()
    narrative_video_overrides = _load_narrative_video_overrides(str(_NARRATIVE_VIDEO_OVERRIDES_PATH))
    narrative_video_suppress_overrides = narrative_video_overrides.get("suppressInline") or {}
    narrative_video_attach_overrides = narrative_video_overrides.get("attachInline") or {}
    fmv_clips_by_key = _load_fmv_clips_by_webui_key(str(_FMV_CLIP_BY_KEY_REPORT_PATH))
    written_conv_paths: set[str] = set()
    written_reference_paths: set[str] = set()
    written_mission_paths: set[str] = set()
    conv_media_tags_by_key: dict[str, set[str]] = defaultdict(set)
    conv_hint_search_text_by_key: dict[str, str] = {}
    scene_order_analysis_by_payload_id: dict[int, dict] = {}
    scene_order_gap_sources: dict[str, tuple[Path, dict, dict | None]] = {}
    inferred_option_anchor_rows_by_key: dict[str, dict] = {}
    inline_image_tag_re = re.compile(
        r"<image\b(?!\s*=)[^>]*>[\s\S]*?</image>"
        r"|<image\s*=[^>]+>"
        r"|<image\b(?=[^>]*(?:src|source|path|name|id)\s*=)[^>]*>",
        flags=re.IGNORECASE,
    )

    def normalize_media_id(value: object) -> str:
        trimmed = clean_media_id_value(value).replace("\\", "/")
        if not trimmed:
            return ""
        without_prefix = re.sub(r"^SNS/Emoji/", "", trimmed, flags=re.IGNORECASE)
        last_segment = without_prefix.split("/")[-1] or without_prefix
        return re.sub(r"\.[^.]+$", "", last_segment, flags=re.IGNORECASE).lower()
    def inline_image_id_from_tag(raw_tag: str) -> str:
        raw = str(raw_tag or "").strip()
        if not raw:
            return ""
        body_match = re.match(r"^<image\b(?!\s*=)[^>]*>([\s\S]*?)</image>$", raw, flags=re.IGNORECASE)
        if body_match:
            return clean_media_id_value(body_match.group(1))
        quoted_direct = re.match(r"""^<image\s*=\s*(["'])([\s\S]*?)\1""", raw, flags=re.IGNORECASE)
        if quoted_direct:
            return clean_media_id_value(quoted_direct.group(2))
        loose_direct = re.match(r"^<image\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
        if loose_direct:
            return clean_media_id_value(loose_direct.group(1))
        quoted_attr = re.search(
            r"""\b(?:src|source|path|name|id)\s*=\s*(["'])([\s\S]*?)\1""",
            raw,
            flags=re.IGNORECASE,
        )
        if quoted_attr:
            return clean_media_id_value(quoted_attr.group(2))
        loose_attr = re.search(r"\b(?:src|source|path|name|id)\s*=\s*([^>\s]+)", raw, flags=re.IGNORECASE)
        return clean_media_id_value(loose_attr.group(1)) if loose_attr else ""
    def image_ids_from_text(text: object) -> list[str]:
        source = str(text or "")
        if "<image" not in source.lower():
            return []
        return [
            image_id
            for image_id in (inline_image_id_from_tag(match.group(0)) for match in inline_image_tag_re.finditer(source))
            if image_id
        ]
    def media_id_is_emoji(value: object) -> bool:
        normalized = normalize_media_id(value)
        return "emoji" in normalized or "emoiji" in normalized
    def media_id_is_sticker(value: object) -> bool:
        normalized = normalize_media_id(value)
        if not normalized or media_id_is_emoji(normalized):
            return False
        return normalized.startswith("sns_sticker_") or "sticker" in normalized
    def media_id_looks_like_media(value: object) -> bool:
        normalized = normalize_media_id(value)
        if not normalized:
            return False
        if normalized.isdigit():
            return False
        mission_type, _mission_act = parse_mission(normalized)
        if mission_type in MISSION_STORY_TYPES:
            return False
        return True

    def collect_payload_media_tags(payload: dict) -> set[str]:
        tags: set[str] = set()
        def add_media_id(value: object) -> None:
            if not media_id_looks_like_media(value):
                return
            normalized = normalize_media_id(value)
            if media_id_is_emoji(normalized):
                tags.add("mediaEmoji")
                return
            tags.add("mediaSticker" if media_id_is_sticker(normalized) else "mediaImage")
        def add_text_images(value: object) -> None:
            for image_id in image_ids_from_text(value):
                add_media_id(image_id)
        def source_from_debug(debug: object) -> dict:
            if not isinstance(debug, dict):
                return {}
            source = debug.get("source") or {}
            if isinstance(source, dict) and isinstance(source.get("source"), dict):
                return source["source"]
            return source if isinstance(source, dict) else {}
        def add_media_from_source(source: dict) -> None:
            if not isinstance(source, dict):
                return
            for field in ("image", "emoji", "emojiResPath", "optionResPath"):
                add_media_id(source.get(field))
            for image_id in source.get("contentParam") or []:
                add_media_id(image_id)
            raw_content_params = source.get("contentParams")
            if not isinstance(raw_content_params, str) or not raw_content_params.strip():
                return
            try:
                content_params = json.loads(raw_content_params)
            except json.JSONDecodeError:
                return
            def visit_content_param(node: object) -> None:
                if isinstance(node, dict):
                    for key, value in node.items():
                        if key in {"image", "imageResPath", "emoji", "emojiResPath", "optionResPath"}:
                            add_media_id(value)
                        elif isinstance(value, (dict, list)):
                            visit_content_param(value)
                elif isinstance(node, list):
                    for item in node:
                        visit_content_param(item)
            visit_content_param(content_params)
        def visit_line(line: object) -> None:
            if not isinstance(line, dict):
                return
            add_text_images(line.get("text"))
            add_media_id(line.get("image"))
            add_media_id(line.get("emoji"))
            for image_id in line.get("images") or []:
                add_media_id(image_id)
            source = source_from_debug(line.get("_debug"))
            add_media_from_source(source)
            if source.get("video"):
                tags.add("mediaVideo")
            for option in line.get("options") or []:
                if not isinstance(option, dict):
                    continue
                add_text_images(option.get("text"))
                add_media_id(option.get("image"))
                add_media_id(option.get("emoji"))
                add_media_from_source(source_from_debug(option.get("_debug")))
        for line in payload.get("lines") or []:
            visit_line(line)
        for row in payload.get("summary") or []:
            if isinstance(row, dict):
                add_text_images(row.get("text"))
        if payload.get("narrativeVideos"):
            tags.add("mediaVideo")
        cutscene = payload.get("cutscene")
        if isinstance(cutscene, dict) and cutscene.get("videoRefs"):
            tags.add("mediaVideo")
        return tags

    def remember_written(path: Path, bucket: set[str]) -> Path:
        bucket.add(written_path_key(path))
        return path
    def write_conv_payload(out_key: str, payload: dict) -> Path:
        path = conv_dir / f"{out_key}.json"
        write_json(path, payload)
        inferred_anchor_row = shared_inferred_option_anchor_row(payload, out_key)
        if inferred_anchor_row is None:
            inferred_option_anchor_rows_by_key.pop(out_key, None)
        else:
            inferred_option_anchor_rows_by_key[out_key] = inferred_anchor_row
        hint_text = line_haystack(payload.get("lines") or [], "hint")
        if hint_text:
            conv_hint_search_text_by_key[out_key] = hint_text
        else:
            conv_hint_search_text_by_key.pop(out_key, None)
        if path.stem.startswith("dlg_"):
            scene_order_gap_sources[written_path_key(path)] = (
                path,
                payload,
                scene_order_analysis_by_payload_id.get(id(payload)),
            )
        media_tags = collect_payload_media_tags(payload)
        if media_tags:
            conv_media_tags_by_key[out_key].update(media_tags)
        return remember_written(path, written_conv_paths)
    def write_reference_payload(rel_file: str, payload: dict) -> Path:
        path = reference_dir / rel_file
        write_json(path, payload)
        return remember_written(path, written_reference_paths)
    def write_mission_payload(rel_file: str, payload: dict) -> Path:
        path = out_dir / rel_file
        write_json(path, payload)
        return remember_written(path, written_mission_paths)
    def cleanup_stale_json(root: Path, written_paths: set[str]) -> None:
        if not root.exists():
            return
        for path in sorted(root.rglob("*.json")):
            if written_path_key(path) not in written_paths:
                path.unlink()
        for path in sorted(root.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir():
                try:
                    path.rmdir()
                except OSError:
                    pass
    print(f"\n[{language_code}] Loading tables...")
    i18n_by_source = {
        "streaming": load(i18n_table_name),
        "persistent": load_optional_table_json(
            PERSISTENT_TABLE_DIR,
            i18n_table_name,
            f"Persistent/{i18n_table_name}",
        ),
    }
    default_text_source = "persistent" if i18n_by_source.get("persistent") else "streaming"
    def apply_i18n_hotfixes() -> dict[str, dict[str, int]]:
        hotfix_type = I18N_HOTFIX_LANGUAGE_TYPES.get(language_code)
        stats: dict[str, dict[str, int]] = {}
        if hotfix_type is None:
            return stats
        for source_name, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            target = i18n_by_source.get(source_name)
            if not isinstance(target, dict):
                continue
            hotfix_rows = load_optional_table_json(
                table_dir,
                I18N_HOTFIX_TABLE,
                f"{source_name}/{I18N_HOTFIX_TABLE}",
            )
            patched = 0
            added = 0
            for row_id, row in hotfix_rows.items():
                if not isinstance(row, dict):
                    continue
                for item in row.get("list") or []:
                    if not isinstance(item, dict):
                        continue
                    if item.get("type") != hotfix_type:
                        continue
                    text = item.get("text")
                    if text is None:
                        continue
                    text_id = str(item.get("id") or row_id)
                    if not text_id:
                        continue
                    if text_id not in target:
                        added += 1
                    target[text_id] = str(text)
                    patched += 1
            if patched or added:
                stats[source_name] = {"patched": patched, "added": added}
        return stats
    hotfix_stats = apply_i18n_hotfixes()
    if hotfix_stats:
        summary = ", ".join(
            f"{source}: {row['patched']} patched ({row['added']} new)"
            for source, row in sorted(hotfix_stats.items())
        )
        print(f"  applied {I18N_HOTFIX_TABLE}: {summary}")
    def load_effective_table(name: str) -> dict:
        streaming_payload = load(name)
        persistent_payload = load_optional_table_json(
            PERSISTENT_TABLE_DIR,
            name,
            f"Persistent/{name}",
        )
        if not persistent_payload:
            return streaming_payload
        if not streaming_payload:
            print(f"  using Persistent/{name}: {len(persistent_payload)} row(s)")
            return persistent_payload
        streaming_keys = set(streaming_payload)
        persistent_keys = set(persistent_payload)
        only_persistent = len(persistent_keys - streaming_keys)
        only_streaming = len(streaming_keys - persistent_keys)
        if len(persistent_payload) >= int(len(streaming_payload) * 0.8):
            if only_persistent or only_streaming:
                print(
                    f"  using Persistent/{name}: +{only_persistent} row(s), "
                    f"-{only_streaming} row(s) versus StreamingAssets"
                )
            return persistent_payload
        merged = dict(streaming_payload)
        merged.update(persistent_payload)
        print(
            f"  merged Persistent/{name}: {only_persistent} added/updated row(s), "
            f"{len(merged)} effective row(s)"
        )
        return merged
    text_table = load_effective_table("TextTable.json")
    dialogs = load_effective_table("DialogTextTable.json")
    sns = load_effective_table("SNSDialogTable.json")
    sns_chats = load_effective_table("SNSChatTable.json")
    sns_opts = load_effective_table("SNSDialogOptionTable.json")
    sns_topics = load_effective_table("SNSDialogTopicTable.json")
    dlg_opts = load_effective_table("DialogOptionTable.json")
    summaries = load_effective_table("DialogSummaryTable.json")
    mission_extra_info = load_effective_table("MissionExtraInfoTable.json")
    dungeons = load_effective_table("DungeonTable.json")
    skill_patches = load_effective_table("SkillPatchTable.json")
    char_growth = load_effective_table("CharGrowthTable.json")
    game_mechanics = load_effective_table("GameMechanicTable.json")
    loading_tips = load_effective_table("LoadingTipsTable.json")
    error_codes = load_effective_table("ErrorCodeTable.json")
    achievements = load_effective_table("AchievementTable.json")
    achievement_types = load_effective_table("AchievementTypeTable.json")
    mail_senders = load_effective_table("MailSenderTable.json")
    mail_templates = load_effective_table("MailTemplateTable.json")
    domain_depot_const = load_effective_table("DomainDepotConst.json")
    domain_depot_dialogs = load_effective_table(
        "DomainDepotDeliverTargetDialogTable.json"
    )
    domain_depot_targets = load_effective_table(
        "DomainDepotDeliverTargetTable.json"
    )
    skip_chapter_rows = load_effective_table("SkipChapterTable.json")
    factory_building_panel_locks = load_effective_table(
        "FactoryBuildingPanelLock.json"
    )
    character_rows = load_effective_table("CharacterTable.json")
    item_rows = load_effective_table("ItemTable.json")
    weapon_basic = load_effective_table("WeaponBasicTable.json")
    enemy_display_info = load_effective_table("EnemyDisplayInfoTable.json")
    enemy_template_display = load_effective_table("EnemyTemplateDisplayInfoTable.json")
    enemy_ability_desc = load_effective_table("EnemyAbilityDescTable.json")
    npc_rows = load_effective_table("NpcTable.json")
    npc_templates = load_effective_table("NpcTemplateGroupTable.json")
    npc_proxy_rows = load_json_path(NPC_PROXY_TABLE_PATH, "NpcProxyTable.json").get("dataTable") or {}
    npc_proxy_ex = _load_npc_proxy_ex()
    npc_proxy_info = npc_proxy_ex.get("proxyInfoData") or {}
    npc_proxy_info = npc_proxy_info if isinstance(npc_proxy_info, dict) else {}
    atmos_cluster_rows = load_json_path(
        ATMOS_CLUSTER_TABLE_PATH, "AtmosphericNpcClusterDataTable.json"
    ).get("dataTable") or {}
    radios = load_effective_table("RadioTable.json")
    remote_common = load_effective_table("RemoteCommonTable.json")
    env_talks = load_effective_table("EnvTalkTable.json")
    ai_bark_text = load_effective_table("AIBarkText.json")
    audio_dialog = load_effective_table("AudioDialog.json")
    responsive_dialog = load_effective_table("ResponsiveDialog.json")
    rich_content = load_effective_table("RichContentTable.json")
    reading_popups = load_effective_table("ReadingPopUpTable.json")
    rich_content_persistent = load_optional_table_json(
        PERSISTENT_TABLE_DIR,
        "RichContentTable.json",
        "Persistent/RichContentTable.json",
    )
    reading_popups_persistent = load_optional_table_json(
        PERSISTENT_TABLE_DIR,
        "ReadingPopUpTable.json",
        "Persistent/ReadingPopUpTable.json",
    )
    prts_all_items = load_effective_table("PrtsAllItem.json")
    prts_first_lv = load_effective_table("PrtsFirstLv.json")
    prts_page = load_effective_table("PrtsPage.json")
    prts_notes = load_effective_table("PrtsNote.json")
    prts_categories = load_effective_table("PrtsCategory.json")
    prts_investigate_categories = load_effective_table("PrtsInvestigateCategory.json")
    wiki_categories = load_effective_table("WikiCategoryTable.json")
    wiki_groups = load_effective_table("WikiGroupTable.json")
    wiki_entry_data = load_effective_table("WikiEntryDataTable.json")
    wiki_tutorial_pages = load_effective_table("WikiTutorialPageTable.json")
    wiki_tutorial_pages_by_entry = load_effective_table("WikiTutorialPageByEntryTable.json")
    wiki_craft_jump = load_effective_table("WikiCraftJumpTable.json")
    wiki_default_craft = load_effective_table("WikiDefaultCraftTable.json")

    def t(id_value, preferred_source: str | None = None) -> str:
        s = norm_id(id_value)
        if not s:
            return ""
        primary_source = preferred_source or default_text_source
        lookup_order = [primary_source]
        for source_name in ("streaming", "persistent"):
            if source_name not in lookup_order:
                lookup_order.append(source_name)
        for source_name in lookup_order:
            text = (i18n_by_source.get(source_name) or {}).get(s, "")
            if text:
                return text
        return ""

    referenced_texttable_row_ids: set[str] = set()
    def remember_texttable_row_usage(row_id) -> None:
        row_key = str(row_id or "").strip()
        if row_key:
            referenced_texttable_row_ids.add(row_key)
    def text_trace(
        table: str,
        row_id: str,
        field: str,
        raw_value,
        *,
        preferred_source: str | None = None,
        transform: str = "",
    ) -> dict:
        i18n_id = norm_id(raw_value.get("id") if isinstance(raw_value, dict) else raw_value)
        primary_source = preferred_source or default_text_source
        resolved = t(i18n_id, preferred_source=primary_source)
        trace = {
            "table": table,
            "rowId": row_id,
            "field": field,
            "raw": raw_value,
            "lookup": [],
            "text": resolved,
        }
        if primary_source != "streaming":
            trace["preferredSource"] = primary_source
        if i18n_id:
            trace["lookup"].append({
                "from": f"{table}[{row_id}].{field}",
                "value": i18n_id,
            })
            trace["lookup"].append({
                "from": f"{i18n_table_key}[{i18n_id}]",
                "value": resolved,
            })
        if transform:
            trace["transform"] = transform
        return trace
    def named_text_trace(table: str, row_id: str, field: str, raw_value) -> dict:
        trace = text_trace(table, row_id, field, raw_value)
        trace["braceText"] = brace_text(trace["text"])
        if trace["text"]:
            trace["lookup"].append({
                "from": f"brace_text({field})",
                "value": trace["braceText"],
            })
        return trace

    def rich_content_trace(row_id: str, field: str, raw_value) -> dict:
        return text_trace("RichContentTable", row_id, field, raw_value)
    def rich_content_title_text(content_id: str) -> str:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return ""
        return t((row.get("title") or {}).get("id"))
    def rich_content_lines(content_id: str) -> list[dict]:
        row = rich_content.get(content_id)
        if not isinstance(row, dict):
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            content = (item or {}).get("content") or {}
            text = t(content.get("id"))
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        content_id,
                        pick_fields(item, "content"),
                        nodeId=idx,
                    ),
                    "fields": {
                        "text": rich_content_trace(content_id, "content", content),
                    },
                },
            })
        return out

    def sns_media_text_from_params(params) -> str:
        image_ids = [
            str(value or "").strip()
            for value in (params or [])
            if media_id_looks_like_media(value)
        ]
        if not image_ids:
            return ""
        if len(image_ids) == 2:
            by_gender: dict[str, str] = {}
            for image_id in image_ids:
                lower = image_id.lower()
                if lower.endswith("_m"):
                    by_gender["M"] = image_id
                elif lower.endswith("_f"):
                    by_gender["F"] = image_id
            if by_gender.get("M") and by_gender.get("F"):
                return (
                    f'{{M}}{inline_image_tag(by_gender["M"])}'
                    f'{{F}}{inline_image_tag(by_gender["F"])}'
                )
        return " ".join(inline_image_tag(image_id) for image_id in image_ids)
    def sns_content_text(node: dict) -> str:
        text = t(node.get("content", {}).get("id"))
        if text:
            return text
        if node.get("contentType") == 2:
            return sns_media_text_from_params(node.get("contentParam"))
        return ""
    def sns_option_display_text(opt: dict) -> str:
        text = t(opt.get("optionDesc", {}).get("id"))
        if text:
            return text
        res_path = str(opt.get("optionResPath") or "").strip()
        if res_path:
            return inline_image_tag(res_path)
        return ""


    mission_name_cache: dict[str, str] = {}
    chat_name_cache: dict[str, str] = {}
    topic_name_cache: dict[str, str] = {}
    topic_id_cache: dict[str, str] = {}
    blackbox_title_cache: dict[str, str] = {}
    topic_base_index: dict[str, list[str]] = defaultdict(list)
    blackbox_base_titles: dict[str, list[dict]] = defaultdict(list)
    blackbox_exact_titles: dict[str, dict] = {}
    for topic_key in sns_topics:
        base_key = re.sub(r"_\d+$", "", topic_key)
        topic_base_index[base_key].append(topic_key)
    for topic_ids in topic_base_index.values():
        topic_ids.sort(key=lambda key: [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", key)])

    for dungeon_id, row in dungeons.items():
        scene_id = normalize_blackbox_id(str(row.get("sceneId") or ""))
        if not scene_id.startswith("blackbox_"):
            continue
        title = brace_text(t((row.get("dungeonName") or {}).get("id")))
        if not title:
            continue
        info = {
            "dungeonId": dungeon_id,
            "sceneId": scene_id,
            "title": title,
            "row": row,
        }
        blackbox_exact_titles[scene_id] = info
        blackbox_base_titles[re.sub(r"_\d+$", "", scene_id)].append(info)
    def mission_name(mission_id: str) -> str:
        """Resolve a mission id like `a1m6d3` to a localized display name."""
        if not mission_id:
            return ""
        if mission_id in mission_name_cache:
            return mission_name_cache[mission_id]
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                name = chat_name(chat_id)
                mission_name_cache[mission_id] = name
                return name
        row = text_table.get(f"{mission_id}_name")
        if row:
            remember_texttable_row_usage(f"{mission_id}_name")
            name = brace_text(t(row.get("id")))
            mission_name_cache[mission_id] = name
            return name
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if normalized_blackbox_id.startswith("blackbox_"):
            if normalized_blackbox_id in blackbox_title_cache:
                name = blackbox_title_cache[normalized_blackbox_id]
                mission_name_cache[mission_id] = name
                return name
            if exact := blackbox_exact_titles.get(normalized_blackbox_id):
                name = exact["title"]
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
            titles = [info["title"] for info in blackbox_base_titles.get(normalized_blackbox_id, [])]
            if titles:
                name = " / ".join(dict.fromkeys(titles))
                blackbox_title_cache[normalized_blackbox_id] = name
                mission_name_cache[mission_id] = name
                return name
        mission_name_cache[mission_id] = ""
        return ""
    def mission_name_trace(mission_id: str) -> dict | None:
        if not mission_id:
            return None
        if mission_id.startswith("topic_"):
            chat_id = mission_chat_id(mission_id)
            if chat_id:
                trace = chat_name_trace(chat_id)
                if trace:
                    trace = dict(trace)
                    trace["source"] = dict(trace.get("source") or {})
                    trace["source"]["derivedMissionId"] = mission_id
                    return trace
        row_id = f"{mission_id}_name"
        row = text_table.get(row_id)
        if row:
            remember_texttable_row_usage(row_id)
            return {
                **source_ref("TextTable", row_id, pick_fields(row, "id")),
                "value": brace_text(t(row.get("id"))),
                "trace": named_text_trace("TextTable", row_id, "id", row.get("id")),
            }
        normalized_blackbox_id = normalize_blackbox_id(mission_id)
        if not normalized_blackbox_id.startswith("blackbox_"):
            return None
        if exact := blackbox_exact_titles.get(normalized_blackbox_id):
            return {
                **source_ref(
                    "DungeonTable",
                    exact["dungeonId"],
                    pick_fields(exact["row"], "sceneId", "dungeonName"),
                    normalizedMissionId=normalized_blackbox_id,
                ),
                "value": exact["title"],
                "trace": named_text_trace(
                    "DungeonTable",
                    exact["dungeonId"],
                    "dungeonName",
                    (exact["row"].get("dungeonName") or {}),
                ),
            }
        infos = blackbox_base_titles.get(normalized_blackbox_id, [])
        if not infos:
            return None
        titles = [info["title"] for info in infos]
        return {
            "table": "DungeonTable",
            "rowId": normalized_blackbox_id,
            "source": {
                "normalizedMissionId": normalized_blackbox_id,
                "variants": [
                    {
                        "dungeonId": info["dungeonId"],
                        "sceneId": info["sceneId"],
                        "title": info["title"],
                    }
                    for info in infos
                ],
            },
            "value": " / ".join(dict.fromkeys(titles)),
            "trace": {
                "raw": titles,
                "lookup": [
                    {
                        "from": f"DungeonTable[{info['dungeonId']}].dungeonName",
                        "value": info["title"],
                    }
                    for info in infos
                ],
            },
        }
    def resolve_topic_id(topic_id: str) -> str:
        """Resolve base SNS topic ids like `topic_chr_0004_pelica` to a table row."""
        if not topic_id:
            return ""
        if topic_id in topic_id_cache:
            return topic_id_cache[topic_id]
        if topic_id in sns_topics:
            topic_id_cache[topic_id] = topic_id
            return topic_id
        matches = topic_base_index.get(topic_id, [])
        resolved = matches[0] if matches else ""
        topic_id_cache[topic_id] = resolved
        return resolved
    def mission_chat_id(mission_id: str) -> str:
        if not mission_id.startswith("topic_"):
            return ""
        chat_id = mission_id.removeprefix("topic_")
        if not chat_id:
            return ""
        if chat_id in sns_chats:
            return chat_id
        prefixed = f"sns_{chat_id}"
        return prefixed if prefixed in sns_chats else ""
    def chat_name(chat_id: str) -> str:
        if not chat_id:
            return ""
        if chat_id in chat_name_cache:
            return chat_name_cache[chat_id]
        row = sns_chats.get(chat_id)
        if not row:
            chat_name_cache[chat_id] = ""
            return ""
        name = brace_text(t((row.get("name") or {}).get("id")))
        chat_name_cache[chat_id] = name
        return name
    def chat_name_trace(chat_id: str) -> dict | None:
        if not chat_id:
            return None
        row = sns_chats.get(chat_id)
        if not row:
            return None
        return {
            **source_ref("SNSChatTable", chat_id, pick_fields(row, "chatId", "name", "owner", "chatType")),
            "value": brace_text(t((row.get("name") or {}).get("id"))),
            "trace": named_text_trace("SNSChatTable", chat_id, "name", row.get("name")),
        }
    def chat_type(chat_id: str) -> int:
        if not chat_id:
            return 0
        row = sns_chats.get(chat_id)
        if not isinstance(row, dict):
            return 0
        try:
            return int(row.get("chatType") or 0)
        except (TypeError, ValueError):
            return 0
    def topic_name(topic_id: str) -> str:
        """Resolve an SNS topic id like `topic_chr_0004_pelica` to its localized title."""
        if not topic_id:
            return ""
        if topic_id in topic_name_cache:
            return topic_name_cache[topic_id]
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            topic_name_cache[topic_id] = ""
            return ""
        name = brace_text(t(row.get("topicName", {}).get("id")))
        topic_name_cache[topic_id] = name
        return name
    def topic_name_trace(topic_id: str) -> dict | None:
        if not topic_id:
            return None
        resolved_topic_id = resolve_topic_id(topic_id)
        row = sns_topics.get(resolved_topic_id)
        if not row:
            return None
        return {
            **source_ref(
                "SNSDialogTopicTable", resolved_topic_id, pick_fields(row, "topicName")
            ),
            "value": brace_text(t(row.get("topicName", {}).get("id"))),
            "trace": named_text_trace(
                "SNSDialogTopicTable", resolved_topic_id, "topicName", row.get("topicName")
            ),
        }
    def named_text(name_key: str) -> str:
        if not name_key:
            return ""
        row = text_table.get(name_key)
        if not row:
            return ""
        remember_texttable_row_usage(name_key)
        return t(row.get("id"))
    def named_text_key_trace(name_key: str) -> dict | None:
        if not name_key:
            return None
        row = text_table.get(name_key)
        if not row:
            return None
        return {
            **source_ref("TextTable", name_key, pick_fields(row, "id")),
            "value": named_text(name_key),
            "trace": text_trace("TextTable", name_key, "id", row.get("id")),
        }

    def localized_objective_instruction(key: object) -> dict | None:
        text_key = str(key or "").strip()
        if not text_key:
            return None
        return {
            "key": text_key,
            "text": named_text(text_key),
        }
    def objective_instruction_keys(anchor: dict) -> list[str]:
        keys: list[str] = []
        if anchor.get("descriptionKey"):
            keys.append(str(anchor.get("descriptionKey") or ""))
        keys.extend(str(key) for key in (anchor.get("multipleDescriptionKeys") or []))
        return _unique_preserve(key for key in keys if key)
    def localize_mission_flow(flow: dict | None) -> dict | None:
        if not isinstance(flow, dict):
            return flow
        localized = copy.deepcopy(flow)
        mission_description_key = str(localized.get("missionDescriptionKey") or "").strip()
        if mission_description_key:
            localized["missionDescription"] = localized_objective_instruction(mission_description_key)
        for quest in localized.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            description_key = mission_description_key
            description_source = "mission"
            if quest.get("overrideMissionDescription") and quest.get("descriptionOverrideKey"):
                description_key = str(quest.get("descriptionOverrideKey") or "").strip()
                description_source = "quest_override"
            if description_key:
                description = localized_objective_instruction(description_key)
                if description:
                    description["source"] = description_source
                    quest["missionDescription"] = description
            quest_instructions: list[dict] = []
            for anchor in quest.get("objectiveAnchors") or []:
                if not isinstance(anchor, dict):
                    continue
                instructions = [
                    entry
                    for key in objective_instruction_keys(anchor)
                    if (entry := localized_objective_instruction(key))
                ]
                if not instructions:
                    continue
                anchor["objectiveInstructions"] = instructions
                index = anchor.get("index")
                for entry in instructions:
                    row = dict(entry)
                    if index not in (None, ""):
                        row["objectiveIndex"] = index
                    quest_instructions.append(row)
            if quest_instructions:
                quest["objectiveInstructions"] = quest_instructions
        return localized

    def quest_attached_story_connections(quest: dict, available: set[str]) -> list[dict]:
        rows: list[dict] = []
        seen: set[tuple] = set()

        def add(row: dict) -> None:
            raw_key = str(row.get("key") or "").strip()
            if is_typed_dialog_tree_runtime_action_connection(
                row,
                available,
                dialog_tree_open_ui_actions_by_key,
            ):
                # This is a typed action-only DialogTree resource, not a Story
                # conversation. Do not rewrite it to a misc_dlg_* alias.
                return
            story_key = resolve_scene_ref_out_key(raw_key, available) if raw_key else ""
            if not story_key:
                return
            normalized = dict(row)
            normalized["key"] = story_key
            signature = (
                story_key,
                normalized.get("relation"),
                normalized.get("phase"),
                normalized.get("actionSlot"),
                normalized.get("actionId"),
                normalized.get("objectiveIndex"),
                normalized.get("mapId"),
                normalized.get("scriptId"),
                normalized.get("conditionKey"),
                normalized.get("variantMission"),
                normalized.get("attachmentKind"),
                normalized.get("npcProxyId"),
                normalized.get("source"),
            )
            if signature in seen:
                return
            seen.add(signature)
            rows.append(normalized)

        for row in quest.get("storyConnections") or []:
            if isinstance(row, dict):
                add(row)

        # Compatibility for older/partial mission-flow rows. These are direct
        # references, but their runtime direction was not retained.
        typed_keys = {str(row.get("key") or "") for row in rows}
        for field, kind in (
            ("dialogs", "dialog"),
            ("cutscenes", "cutscene"),
            ("remotecomms", "remotecomm"),
            ("radios", "radio"),
        ):
            for key in quest.get(field) or []:
                resolved = resolve_scene_ref_out_key(str(key or ""), available)
                if not resolved or resolved in typed_keys:
                    continue
                add({
                    "key": resolved,
                    "kind": kind,
                    "relation": "runtime_reference",
                    "direction": "context",
                    "phase": "unknown",
                    "confidence": "direct_untyped",
                    "source": f"MissionRuntimeAsset.{field}",
                })
        return rows

    def quest_attached_story_files(
        quest: dict,
        available: set[str],
        connections: list[dict] | None = None,
    ) -> list[dict]:
        rows: list[dict] = []
        seen: set[str] = set()

        def add(key: object, kind: str, evidence: str) -> None:
            story_key = str(key or "").strip()
            if not story_key or story_key not in available or story_key in seen:
                return
            seen.add(story_key)
            rows.append({"key": story_key, "kind": kind, "evidence": evidence})

        for connection in connections or quest_attached_story_connections(quest, available):
            add(
                connection.get("key"),
                str(connection.get("kind") or "story"),
                str(connection.get("source") or connection.get("relation") or "quest Story connection"),
            )
        return rows

    npc_templates_by_template_id: dict[str, list[str]] = defaultdict(list)
    for template_row_id, row in npc_templates.items():
        template_id = str(row.get("templateId") or "")
        for candidate in {template_row_id, template_id, norm_template_id(template_id)}:
            if candidate:
                npc_templates_by_template_id[candidate].append(template_row_id)
    npc_data_key_by_id: dict[str, str] = {}
    npc_data_keys_by_group: dict[str, list[str]] = defaultdict(list)
    for npc_row_id, row in npc_rows.items():
        if not isinstance(row, dict):
            continue
        data_key = str(row.get("dataKey") or "").strip()
        if not data_key:
            continue
        for key in (
            str(npc_row_id or "").strip(),
            str(row.get("npcId") or "").strip(),
            str(row.get("normalCfg") or "").strip(),
        ):
            if key and key not in npc_data_key_by_id:
                npc_data_key_by_id[key] = data_key
        group_id = str(row.get("npcGroupId") or "").strip()
        if group_id and data_key not in npc_data_keys_by_group[group_id]:
            npc_data_keys_by_group[group_id].append(data_key)
    def npc_template_row_id_for_candidate(value: str) -> str:
        raw = str(value or "").strip()
        if not raw:
            return ""
        candidates = _unique_preserve([raw, norm_template_id(raw)])
        for candidate in candidates:
            if candidate in npc_templates:
                return candidate
            template_row_ids = npc_templates_by_template_id.get(candidate) or []
            if template_row_ids:
                return template_row_ids[0]
        return ""
    def resolve_npc_template_row(row_id: str, row: dict) -> tuple[str, dict | None]:
        candidates: list[str] = []
        def add_candidate(value: str) -> None:
            if not value or value in candidates:
                return
            candidates.append(value)
            norm = norm_template_id(value)
            if norm and norm not in candidates:
                candidates.append(norm)
        add_candidate(row_id)
        for key in ("npcId", "dataKey", "npcGroupId", "normalCfg"):
            value = str(row.get(key) or "")
            add_candidate(value)
            group_base = re.sub(r"_g\d+$", "", value)
            add_candidate(group_base)
        for candidate in candidates:
            if candidate in npc_templates:
                return (candidate, npc_templates[candidate])
            if candidate in npc_templates_by_template_id:
                template_row_id = npc_templates_by_template_id[candidate][0]
                return (template_row_id, npc_templates[template_row_id])
        return ("", None)
    env_npc_meta: dict[str, dict] = {}
    for npc_row_id, row in npc_rows.items():
        env_ids = row.get("envTalkIds") or []
        if not env_ids:
            continue
        template_row_id, template_row = resolve_npc_template_row(npc_row_id, row)
        template_name_key = str((template_row or {}).get("name") or "")
        template_title_key = str((template_row or {}).get("title") or "")
        direct_name = t((row.get("name") or {}).get("id")) if isinstance(row.get("name"), dict) else ""
        direct_title = t((row.get("title") or {}).get("id")) if isinstance(row.get("title"), dict) else ""
        name = direct_name or named_text(template_name_key)
        title = direct_title or named_text(template_title_key)
        meta = {
            "npcId": row.get("npcId") or npc_row_id,
            "npcGroupId": row.get("npcGroupId") or "",
            "dataKey": row.get("dataKey") or "",
            "name": name,
            "title": title,
            "dialogSelector": row.get("dialogSelector") or "",
            "_debug": {
                **source_ref(
                    "NpcTable",
                    npc_row_id,
                    pick_fields(
                        row,
                        "npcId",
                        "npcGroupId",
                        "dataKey",
                        "dialogSelector",
                        "envTalkIds",
                        "name",
                        "title",
                    ),
                ),
                "fields": {
                    "name": text_trace("NpcTable", npc_row_id, "name", row.get("name")),
                    "title": text_trace("NpcTable", npc_row_id, "title", row.get("title")),
                },
            },
        }
        if template_row:
            meta["_debug"]["template"] = source_ref(
                "NpcTemplateGroupTable",
                template_row_id,
                pick_fields(template_row, "npcNameId", "templateId", "name", "title"),
            )
            if template_name_key:
                meta["_debug"]["fields"]["templateName"] = named_text_key_trace(template_name_key)
            if template_title_key:
                meta["_debug"]["fields"]["templateTitle"] = named_text_key_trace(template_title_key)
        for env_id in env_ids:
            env_npc_meta.setdefault(env_id, meta)
    env_story_binding_hints: dict[str, dict[str, set[str] | list[dict]]] = defaultdict(
        lambda: {"levels": set(), "proxies": set(), "sources": []}
    )
    def add_env_story_binding_hint(
        env_id: str,
        *,
        level_id: str = "",
        proxy_id: str = "",
        source: dict | None = None,
    ) -> None:
        env_id = (env_id or "").strip()
        if not env_id:
            return
        hints = env_story_binding_hints[env_id]
        if level_id:
            hints["levels"].add(level_id)
        if proxy_id:
            hints["proxies"].add(proxy_id)
        if source:
            hints["sources"].append(source)
    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("proxyId") or row_id or "")
        for env_id in row.get("envTalkIds") or []:
            add_env_story_binding_hint(
                env_id,
                level_id=level_id,
                proxy_id=proxy_id,
                source={
                    "table": "NpcProxyTable",
                    "rowId": row_id,
                    "proxyId": proxy_id,
                    "levelId": level_id,
                },
            )
    for row_id, row in atmos_cluster_rows.items():
        if not isinstance(row, dict):
            continue
        env_id = str(row.get("envTalkId") or "").strip()
        if not env_id:
            continue
        level_id = str(row.get("levelId") or "")
        proxy_id = str(row.get("clusterId") or row_id or "")
        add_env_story_binding_hint(
            env_id,
            level_id=level_id,
            proxy_id=proxy_id,
            source={
                "table": "AtmosphericNpcClusterDataTable",
                "rowId": row_id,
                "clusterId": proxy_id,
                "levelId": level_id,
            },
        )
    # ---------- Story dialog groups ----------
    groups: dict[str, list[tuple[int, str, dict]]] = defaultdict(list)
    misc: list[tuple[str, dict]] = []
    for dlg_id, entry in dialogs.items():
        m = DLG_RE.match(dlg_id)
        if not m:
            misc.append((dlg_id, entry))
            continue
        mission, scene, line = m.group(1), int(m.group(2)), int(m.group(3))
        groups[f"dlg__{mission}__{scene}"].append((line, dlg_id, entry))
    # Build actor display name table.
    # Each actorNameId may have multiple variant names across the game
    # (alias, masked persona, "鍓嶇紑{鐪熷悕}", etc.). Keep all distinct ones,
    # but drop the "锛燂紵锛? / "???" placeholder used for unrevealed identities.
    PLACEHOLDER_NAMES = {"锛燂紵锛?", "???"}
    actor_name_sets: dict[str, set[str]] = defaultdict(set)
    def add_actor_text(aid: str, name: str) -> None:
        if not aid or not name or name in PLACEHOLDER_NAMES:
            return
        actor_name_sets[aid].add(name)
    def add_actor_name(aid: str, name_id) -> None:
        if not aid:
            return
        add_actor_text(aid, t(name_id))
    def scoped_actor_base_candidates(actor_id: str) -> list[str]:
        """Return canonical actor-id candidates from map/base-scoped ids.
        EnvTalk actor ids sometimes encode the speaker as a scoped proxy such
        as `chen_map01_e2m5`. The prefix is still the real speaker id, while
        the suffix only tells us which map/mission proxy emitted the bark.
        Some ids instead use NPC template/group ids, such as
        `npc_spl_andrew_01_g01_map01_lv001_e1m3_001`; resolve those through
        NpcTable and NpcTemplateGroupTable so the browser can show the real
        display name.
        """
        raw = str(actor_id or "").strip()
        if not raw:
            return []
        out: list[str] = []
        def add_candidate(value: str) -> None:
            value = str(value or "").strip()
            if value and value not in out:
                out.append(value)
        add_candidate(raw)
        for marker in ("_map", "_base", "_dung", "_data_sub"):
            idx = raw.find(marker)
            if idx > 0:
                add_candidate(raw[:idx])
        index = 0
        while index < len(out):
            current = out[index]
            index += 1
            if current.startswith("npc_tpl_"):
                add_candidate(norm_template_id(current))
            data_key = npc_data_key_by_id.get(current)
            if data_key:
                add_candidate(data_key)
            for data_key in npc_data_keys_by_group.get(current, []):
                add_candidate(data_key)
            group_base = re.sub(r"_g\d+$", "", current)
            if group_base != current:
                add_candidate(group_base)
            template_row_id = npc_template_row_id_for_candidate(current)
            if template_row_id:
                add_candidate(template_row_id)
                template_row = npc_templates.get(template_row_id) or {}
                add_candidate(str(template_row.get("npcNameId") or ""))
        return out
    def npc_proxy_actor_candidates(proxy_id: str) -> list[str]:
        raw = str(proxy_id or "").strip()
        if not raw:
            return []
        out: list[str] = []
        info = npc_proxy_info.get(raw)
        if isinstance(info, dict):
            for field in ("npcNameId", "npcId"):
                value = str(info.get(field) or "").strip()
                if not value:
                    continue
                out.append(value)
                out.extend(scoped_actor_base_candidates(value))
        out.extend(scoped_actor_base_candidates(raw))
        return _unique_preserve(out)
    def add_actor_template_name(aid: str) -> None:
        if not aid:
            return
        template_row_id = npc_template_row_id_for_candidate(aid)
        row = npc_templates.get(template_row_id) if template_row_id else None
        if not isinstance(row, dict):
            return
        canonical_aid = str(row.get("npcNameId") or "").strip()
        for target_aid in _unique_preserve([aid, canonical_aid]):
            add_actor_text(target_aid, named_text(str(row.get("name") or "")))
            add_actor_text(target_aid, named_text(str(row.get("title") or "")))
        if canonical_aid and actor_name_sets.get(canonical_aid):
            actor_name_sets[aid].update(actor_name_sets[canonical_aid])
    for entry in dialogs.values():
        add_actor_name(entry.get("actorNameId") or "", entry.get("actorName", {}).get("id"))
    for radio in radios.values():
        for item in radio.get("radioSingleDataList", []) or []:
            aid = item.get("actorNameId") or ""
            add_actor_name(aid, item.get("actorName", {}).get("id"))
            add_actor_name(aid, item.get("infoActorName", {}).get("id"))
    # Mail senders cover characters that only surface in inbox/SNS data, so
    # seed the canonical actor table from them before expanding SNS aliases.
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sender_id, row.get("senderName", {}).get("id"))
    # SNS chat rows provide the visible display name for synthetic ids like
    # `sns_chat_daniel` and a small number of non-`sns_` chat owners that do
    # not correspond to a regular story actor id.
    for sns_id, row in sns_chats.items():
        if not isinstance(row, dict):
            continue
        add_actor_name(sns_id, row.get("name", {}).get("id"))

    # Reuse exported icon metadata instead of guessing SNS aliases from the raw
    # chat id alone. Mail sender data already maps icon asset -> canonical
    # actor key like `pelica` / `andrew`, and SNS chat rows reuse those icons.
    sns_related_ids: dict[str, list[str]] = {}
    icon_to_actor_id: dict[str, str] = {}
    for sender_id, row in mail_senders.items():
        if not isinstance(row, dict):
            continue
        icon = icon_basename(str(row.get("senderIcon") or ""))
        if icon and sender_id:
            icon_to_actor_id.setdefault(icon, sender_id)
    for sns_id, row in sns_chats.items():
        if not sns_id.startswith("sns_") or not isinstance(row, dict):
            continue
        related: list[str] = []
        for icon_field in ("icon", "listIcon"):
            icon = icon_basename(str(row.get(icon_field) or ""))
            mapped = icon_to_actor_id.get(icon)
            if mapped and mapped not in related:
                related.append(mapped)
        core = sns_id[len("sns_"):]
        if core.startswith("chr_"):
            parts = core.split("_")
            if parts and parts[-1] not in related:
                related.append(parts[-1])
        elif core.startswith("npc_"):
            npc_name = core[len("npc_"):]
            if npc_name and npc_name not in related:
                related.append(npc_name)
        elif core and core not in related:
            related.append(core)
        if related:
            sns_related_ids[sns_id] = related
    for sns_id, related_ids in sns_related_ids.items():
        for related_id in related_ids:
            names = actor_name_sets.get(related_id)
            if names:
                actor_name_sets[sns_id].update(names)
                break
    # The generic player/admin id and the female presentation id should share
    # the same resolved display name in the browser data.
    if actor_name_sets.get("endminf"):
        actor_name_sets["endmin"].update(actor_name_sets["endminf"])
    npc_proxy_rows_by_proxy_id: dict[str, tuple[str, dict]] = {}
    env_talk_proxy_ids_by_env: dict[str, list[str]] = defaultdict(list)
    for row_id, row in npc_proxy_rows.items():
        if not isinstance(row, dict):
            continue
        proxy_id = str(row.get("proxyId") or row_id or "").strip()
        if not proxy_id:
            continue
        npc_proxy_rows_by_proxy_id[proxy_id] = (str(row_id), row)
        env_ids = [
            str(env_id).strip()
            for env_id in (row.get("envTalkIds") or [])
            if env_id is not None and str(env_id).strip()
        ]
        if not env_ids:
            continue
        override_name_key = str(((row.get("overrideNpcNameId") or {}).get("key")) or "")
        if row.get("ifOverrideNpcName") and override_name_key:
            add_actor_text(proxy_id, named_text(override_name_key))
        for base_actor_id in npc_proxy_actor_candidates(proxy_id):
            add_actor_template_name(base_actor_id)
            if actor_name_sets.get(base_actor_id):
                actor_name_sets[proxy_id].update(actor_name_sets[base_actor_id])
                break
        for env_id in env_ids:
            env_talk_proxy_ids_by_env[env_id].append(proxy_id)
    for entry in env_talks.values():
        for item in entry.get("envTalkDataList", []) or []:
            scoped_actor_id = str(item.get("actorId") or "")
            for base_actor_id in npc_proxy_actor_candidates(scoped_actor_id):
                add_actor_template_name(base_actor_id)
                if actor_name_sets.get(base_actor_id):
                    actor_name_sets[scoped_actor_id].update(actor_name_sets[base_actor_id])
                    break
    actor_names: dict[str, list[str]] = {
        aid: sorted(names) for aid, names in actor_name_sets.items()
    }
    def speaker_display_name(speaker_id: str) -> str:
        """Best-effort display name for dialog/SNS speaker ids."""
        if not speaker_id:
            return ""
        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])
        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_")
            if parts:
                candidates.append(parts[-1])
        elif "_" in core:
            candidates.append(core.split("_")[-1])
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            names = actor_names.get(candidate)
            if names:
                return names[0]
        return ""
    def speaker_actor_id(speaker_id: str) -> str:
        """Resolve a speaker/channel id back to the browser's actor id when possible."""
        if not speaker_id:
            return ""
        candidates: list[str] = [speaker_id]
        if speaker_id.startswith("sns_"):
            candidates.append(speaker_id[len("sns_"):])
        core = candidates[-1]
        candidates.extend(npc_proxy_actor_candidates(core))
        if core.startswith("npc_"):
            candidates.append(core[len("npc_"):])
        if core.startswith("chr_"):
            candidates.append(core)
            parts = core.split("_", 2)
            if len(parts) >= 3:
                candidates.append(parts[2])
        elif "_" in core:
            candidates.append(core.split("_")[-1])
        seen: set[str] = set()
        for candidate in candidates:
            if not candidate or candidate in seen:
                continue
            seen.add(candidate)
            if candidate in actor_names or re.fullmatch(r"endmin[fm]?", candidate):
                return candidate
        return ""

    def env_index_slot(env_id: str) -> tuple[str, str, str, list[str]]:
        """Return browser slot info for an env-talk entry.
        Most env talks are browsed with the open-world text bucket, while
        operator greeting lines (`greetEnvTalk*`) stay alongside other
        operator-interaction content.
        """
        if env_id.startswith("greetEnvTalk"):
            return ("misc", "greet", "sim", ["envTalk"])
        mission = env_group(env_id)
        return ("env", mission, "worldtext", ["envTalk"])


    def indexed_line_haystack(lines: list[dict], *fields: str) -> str:
        return " ".join(
            part
            for part in (
                line_identity_haystack(lines),
                line_haystack(lines, *fields),
                line_option_haystack(lines),
            )
            if part
        )
    # ---------- SNS dialogs ----------
    sns_groups: dict[str, dict] = {}
    for sns_id, entry in sns.items():
        sns_groups[sns_id] = entry
    # ---------- Extras: summary / options + standalone radio ----------
    # Each attaches to a conversation out_key. Regular dialog scenes emit as
    # `dlg_<mission>_<scene>` (scene is int). Sub-scene dialogs like
    # `dlg_c16m1_4d5_001` end up in misc bucket `misc_dlg_<mission>_<scene>`.
    # We build both possible target keys so extras route correctly.
    dlg_out_keys: set[str] = set()
    for key in groups:
        _, mission, scene_str = key.split("__")
        dlg_out_keys.add(f"dlg_{mission}_{int(scene_str)}")
    sns_out_keys: set[str] = set(sns_groups)
    radio_out_keys: set[str] = set()
    black_out_keys: set[str] = set()
    remotecomm_out_keys: set[str] = set()
    cutscene_out_keys: set[str] = set()
    misc_bucket_keys: set[str] = set()
    for did, _ in misc:
        bkey = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
        misc_bucket_keys.add(f"misc_{bkey}")
    known_missions: set[str] = {key.split("__")[1] for key in groups}
    known_missions.update(m.group(1) for sid in sns_groups if (m := SNS_RE.match(sid)))
    for did, _ in misc:
        type_, _act, mission, _scene = slot_misc(re.sub(r"_\d+(_\d+)?$", "", did) or "_misc")
        if type_ != "x" and mission:
            known_missions.add(mission)
    for radio_id in radios:
        if m := RADIO_RE.match(radio_id):
            known_missions.add(m.group(1))
    for remote_id in remote_common:
        if m := REMOTECOMM_RE.match(remote_id):
            known_missions.add(m.group(1))
    env_story_missions: dict[str, str] = {}
    for env_id in env_talks:
        if story_mission := env_story_mission(env_id, known_missions):
            env_story_missions[env_id] = story_mission
    mission_note_by_mission: dict[str, list[dict]] = defaultdict(list)
    for mission_id, row in mission_extra_info.items():
        text = t((row.get("extraInfoDesc") or {}).get("id"))
        if not text:
            continue
        mission_note_by_mission[mission_id].append({
            "missionId": mission_id,
            "type": row.get("extraInfoType", 0),
            "text": text,
            "_debug": {
                **source_ref(
                    "MissionExtraInfoTable",
                    mission_id,
                    pick_fields(row, "missionId", "extraInfoType", "extraInfoDesc"),
                ),
                "fields": {
                    "text": text_trace(
                        "MissionExtraInfoTable",
                        mission_id,
                        "extraInfoDesc",
                        row.get("extraInfoDesc"),
                    ),
                },
            },
        })

    mission_level_refs: dict[str, list[dict]] = defaultdict(list)
    mission_leveldata_host_refs: dict[str, list[dict]] = defaultdict(list)
    seen_leveldata_host_refs: set[tuple[str, str, str, str]] = set()
    def add_leveldata_host_ref(mission_id: str, ref_meta: dict, path: Path, relation: str) -> None:
        if mission_id not in known_missions:
            return
        file_ref = repo_rel(path)
        level_id = ref_meta["level"]
        seen_key = (mission_id, level_id, file_ref, relation)
        if seen_key in seen_leveldata_host_refs:
            return
        seen_leveldata_host_refs.add(seen_key)
        mission_leveldata_host_refs[mission_id].append({
            "levelId": level_id,
            "hostType": level_host_type(level_id),
            "kind": ref_meta["kind"],
            "file": file_ref,
            "token": ref_meta["token"],
            "relation": relation,
        })
    if LEVELDATA_DIR.is_dir():
        for path in LEVELDATA_DIR.rglob("*.json"):
            ref_meta = parse_level_ref_name(path.name)
            if not ref_meta:
                continue
            mission_id = ref_meta["token"]
            add_leveldata_host_ref(mission_id, ref_meta, path, "exact")
            parent_mission_id = re.sub(r"d\d+$", "", mission_id)
            if parent_mission_id != mission_id:
                add_leveldata_host_ref(parent_mission_id, ref_meta, path, "parentVariant")
            if mission_id in known_missions:
                level_id = ref_meta["level"]
                mission_level_refs[mission_id].append({
                    "levelId": level_id,
                    "hostType": level_host_type(level_id),
                    "kind": ref_meta["kind"],
                    "file": repo_rel(path),
                    "_debug": {
                        "source": {
                            "file": repo_rel(path),
                            "levelId": level_id,
                            "kind": ref_meta["kind"],
                            "missionId": mission_id,
                        },
                    },
                })
    for refs in mission_level_refs.values():
        refs.sort(key=lambda ref: (ref["hostType"], ref["levelId"], ref["kind"], ref["file"]))
    for refs in mission_leveldata_host_refs.values():
        refs.sort(key=lambda ref: (ref["hostType"], ref["levelId"], ref["relation"], ref["kind"], ref["file"]))
    def mission_context_text(mission_id: str) -> str:
        if not mission_id:
            return ""
        parts: list[str] = []
        for note in mission_note_by_mission.get(mission_id, []):
            if note.get("text"):
                parts.append(note["text"])
        for ref in mission_level_refs.get(mission_id, []):
            if ref.get("levelId"):
                parts.append(ref["levelId"])
        return " ".join(parts)

    extra_mission_names: dict[str, str] = {}
    def entry_tags(out_key: str, mission: str = "") -> list[str]:
        tags: list[str] = []
        if out_key in summary_by_key:
            tags.append("summary")
        return tags
    def attach_target(mission: str, scene: str, *, allow_sns: bool = False) -> str | None:
        """Pick the out_key that owns (mission, scene), or None if orphan."""
        if re.fullmatch(r"\d+", scene):
            cand = f"dlg_{mission}_{int(scene)}"
            if cand in dlg_out_keys:
                return cand
            if allow_sns:
                cand = f"sns_{mission}_{int(scene)}"
                if cand in sns_out_keys:
                    return cand
        cand = f"misc_dlg_{mission}_{scene}"
        if cand in misc_bucket_keys:
            return cand
        return None
    def dialog_scene_out_key(dialog_id: str) -> str | None:
        if dialog_id in sns_out_keys:
            return dialog_id
        if dialog_id in radio_out_keys:
            return dialog_id
        if dialog_id in black_out_keys or dialog_id in remotecomm_out_keys:
            return dialog_id
        if canonical_cutscene := _canonical_cutscene_key(dialog_id):
            if canonical_cutscene in cutscene_out_keys:
                return canonical_cutscene
        m = re.match(rf"^dlg_(.+)_({SCENE_TOK})$", dialog_id)
        if not m:
            if dialog_id.startswith("dlg_"):
                payload = dialog_id[4:]
                if "_" in payload:
                    mission, scene = payload.split("_", 1)
                    return attach_target(mission, scene)
            return None
        return attach_target(m.group(1), m.group(2))
    summary_by_key: dict[str, list[dict]] = defaultdict(list)
    summary_orphans = 0
    for sid, entry in summaries.items():
        m = SUMMARY_RE.match(sid)
        if not m:
            summary_orphans += 1
            continue
        mission, scene, _idx = m.group(1), m.group(2), m.group(3)
        target = attach_target(mission, scene)
        text = t(entry.get("id"))
        if not text:
            continue
        if target is None:
            summary_orphans += 1
            continue
        summary_by_key[target].append({
            "text": text,
            "_debug": {
                **source_ref("DialogSummaryTable", sid, pick_fields(entry, "id")),
                "fields": {
                    "text": text_trace("DialogSummaryTable", sid, "id", entry.get("id")),
                },
            },
        })
    options_by_key: dict[str, dict[int, list[dict]]] = defaultdict(lambda: defaultdict(list))
    dialog_option_text_by_id: dict[str, str] = {}
    dialog_option_signature_by_id: dict[str, tuple[str, str]] = {}
    dialog_option_payload_by_id: dict[str, dict] = {}
    dialog_option_ids_by_scene_group: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
    option_orphans = 0
    for raw_oid, entry in dlg_opts.items():
        oid = DIALOG_OPTION_ID_CORRECTIONS.get(raw_oid, raw_oid)
        m = OPTION_RE.match(oid)
        if not m:
            # `dlg_spaceship_*` UI options have no scene; skip.
            continue
        mission, scene, grp, idx = m.group(1), m.group(2), int(m.group(3)), int(m.group(4))
        option_text = t(entry.get("optionText", {}).get("id"))
        option_icon = entry.get("iconType", "") or ""
        option_scene_key = f"dlg_{mission}_{scene}"
        dialog_option_text_by_id[oid] = option_text
        dialog_option_signature_by_id[oid] = (_option_text_signature(option_text), option_icon)
        if oid != raw_oid:
            dialog_option_text_by_id[raw_oid] = option_text
            dialog_option_signature_by_id[raw_oid] = (_option_text_signature(option_text), option_icon)
        dialog_option_ids_by_scene_group[(option_scene_key, grp)].append((idx, oid))
        target = attach_target(mission, scene)
        if target is None:
            option_orphans += 1
            continue
        option_debug = {
            **source_ref(
                "DialogOptionTable",
                raw_oid,
                pick_fields(entry, "optionText", "iconType"),
            ),
            "fields": {
                "text": text_trace(
                    "DialogOptionTable", raw_oid, "optionText", entry.get("optionText")
                ),
            },
        }
        if oid != raw_oid:
            option_debug["idCorrection"] = {
                "from": raw_oid,
                "to": oid,
                "reason": "DialogOptionTable group number disagrees with recovered env_12 menu order.",
            }
        option_entry = {
            "id": oid,
            "i": idx,
            "text": option_text,
            "icon": option_icon,
            "_debug": option_debug,
        }
        options_by_key[target][grp].append(option_entry)
        dialog_option_payload_by_id[oid] = option_entry
    dialog_option_group_ids_by_key: dict[tuple[str, int], list[str]] = {
        key: [oid for _idx, oid in sorted(entries)]
        for key, entries in dialog_option_ids_by_scene_group.items()
    }
    dialog_option_group_keys_by_group: dict[int, list[tuple[str, int]]] = defaultdict(list)
    for group_key in dialog_option_group_ids_by_key:
        dialog_option_group_keys_by_group[group_key[1]].append(group_key)
    for group_keys in dialog_option_group_keys_by_group.values():
        group_keys.sort(key=lambda key: key[0])
    dialog_option_group_keys_by_group_and_count: dict[
        tuple[int, int], list[tuple[str, int]]
    ] = defaultdict(list)
    for group_id, group_keys in dialog_option_group_keys_by_group.items():
        for group_key in group_keys:
            dialog_option_group_keys_by_group_and_count[
                (group_id, len(dialog_option_group_ids_by_key[group_key]))
            ].append(group_key)
    radio_rows: list[dict] = []
    radio_orphans = 0
    radio_targets_seen: set[str] = set()
    for rid, entry in radios.items():
        m = RADIO_RE.match(rid)
        if not m:
            radio_orphans += 1
            continue
        mission, scene = m.group(1), m.group(2)
        target = attach_target(mission, scene, allow_sns=True)
        if target is None:
            radio_orphans += 1
        items = []
        actors: set[str] = set()
        prev_text = ""
        for item in entry.get("radioSingleDataList", []) or []:
            actor_id = item.get("actorNameId", "") or ""
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("radioText", {}).get("id"))
            if actor_id:
                actors.add(actor_id)
            if not prev_text and text:
                prev_text = text
            items.append({
                "id": item.get("id", "") or "",
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": item.get("audioOverride", "") or "",
                "emo": item.get("emotionType", 0),
                "_debug": {
                    **source_ref(
                        "RadioTable.radioSingleDataList",
                        item.get("id", "") or "",
                        pick_fields(
                            item,
                            "id",
                            "actorNameId",
                            "actorName",
                            "infoActorName",
                            "radioText",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RadioTable.radioSingleDataList",
                            item.get("id", "") or "",
                            "radioText",
                            item.get("radioText"),
                        ),
                    },
                },
            })
        if target:
            radio_targets_seen.add(target)
        type_, act = parse_mission(mission)
        radio_rows.append({
            "k": rid,
            "m": mission,
            "scene": scene,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": sorted(actors),
            "p": preview(prev_text),
            "lines": items,
            "radioType": entry.get("radioType", 0),
            "target": target or "",
            "_debug": source_ref(
                "RadioTable",
                rid,
                pick_fields(entry, "radioType"),
            ),
        })
    def pack_options(
        groups_map: dict[int, list[dict]],
        lines: list[dict] | None = None,
        conv_key: str | None = None,
    ) -> dict:
        """Return option groups sorted by group number, each annotated with an
        `after` field naming the line id after which it should render.
        Primary signal (when available): the AnimeStudio DialogTree graph at
        `exported/AnimeStudio/main/TextAsset/<conv_key>.json`, which stores
        the authoritative option鈫抰runk wiring. Falls back to a gap heuristic:
        DialogTextTable lines are numbered sparsely 鈥?slots are reserved for
        player-response audio that isn't stored as dialog text 鈥?so a line
        sequence like `_001..006, _008..013, _016..025, _030..041` has three
        gaps where choices happen, and option groups `g=1`, `g=2`, `g=3`
        attach to those gaps in order.
        """
        tree_meta: dict = {}
        tree_after: dict[str, str] = {}
        tree_after_sources: dict[str, list[str]] = {}
        tree_branches: dict[str, list[str]] = {}
        tree_merge: dict[str, str] = {}
        tree_converge: dict[str, str] = {}
        tree_pre: set[str] = set()
        tree_pre_sources: dict[str, list[str]] = {}
        scene_link_after: dict[str, str] = {}
        scene_link_authored_option_ids: set[str] = set()
        scene_link_sources: set[str] = set()
        cinematic_finish_groups: list[dict] = []
        cinematic_after_by_group: dict[int, str] = {}
        cinematic_sources_by_group: dict[int, list[str]] = {}
        cinematic_authored_option_ids: set[str] = set()
        cinematic_sources: set[str] = set()
        text_alias_after_by_group: dict[int, str] = {}
        text_alias_pre_by_group: set[int] = set()
        text_alias_sources_by_group: dict[int, list[str]] = {}
        text_alias_foreign_option_ids_by_group: dict[int, list[str]] = {}
        text_alias_authored_option_ids: set[str] = set()
        text_alias_sources: set[str] = set()
        timeline_entries: list[dict] = []
        timeline_after: dict[str, str] = {}
        timeline_after_line_ids: dict[str, list[str]] = {}
        timeline_after_line_timings: dict[str, dict[str, dict]] = {}
        timeline_after_runtime_jump_clips: dict[str, list[dict] | None] = {}
        timeline_option_rows: dict[str, list[dict]] = defaultdict(list)
        timeline_option_routes: dict[str, list[dict]] = defaultdict(list)
        timeline_pre: set[str] = set()
        timeline_authored_option_ids: set[str] = set()
        timeline_sources: set[str] = set()
        if conv_key:
            tree_meta = load_dialog_tree(conv_key) or {}
            tree_after = tree_meta.get("after", {}) or {}
            tree_after_sources = tree_meta.get("afterSources", {}) or {}
            tree_branches = tree_meta.get("branches", {}) or {}
            tree_merge = tree_meta.get("merge", {}) or {}
            tree_converge = tree_meta.get("converge", {}) or {}
            tree_pre_sources = tree_meta.get("preSources", {}) or {}
            cinematic_finish_groups = [
                group
                for group in (tree_meta.get("cinematicFinishGroups") or [])
                if isinstance(group, dict)
            ]
            tree_pre = {
                opt_id
                for opt_id in (tree_meta.get("pre") or [])
                if isinstance(opt_id, str) and opt_id
            }
            for link in load_dialog_tree_scene_links(conv_key) or []:
                source_key = link.get("sourceKey") or ""
                if source_key:
                    scene_link_sources.add(source_key)
                group_after = link.get("after") or ""
                for opt in link.get("options") or []:
                    opt_id = opt.get("optionId") or ""
                    if not opt_id:
                        continue
                    if group_after:
                        scene_link_authored_option_ids.add(opt_id)
                        if opt_id not in scene_link_after:
                            scene_link_after[opt_id] = group_after
            timeline_entries = load_dialog_timeline_line_orders(conv_key)
            for timeline in timeline_entries:
                if not timeline.get("optionAnchors"):
                    continue
                source_key = timeline.get("sourceKey") or timeline.get("timeline") or ""
                file_path = timeline.get("file") or ""
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                timeline_line_timing_by_id = {
                    str(row.get("id") or ""): row
                    for row in (timeline.get("lineTimings") or [])
                    if isinstance(row, dict) and str(row.get("id") or "").strip()
                }
                if source_key:
                    timeline_sources.add(source_key)
                if file_path:
                    timeline_sources.add(file_path)
                for row in timeline.get("optionRows") or []:
                    if not isinstance(row, dict):
                        continue
                    opt_id = str(row.get("id") or "")
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    timeline_option_rows[opt_id].append(row)
                for opt_id, route in (timeline.get("optionRoutes") or {}).items():
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    if isinstance(route, dict):
                        timeline_option_routes[opt_id].append(route)
                for opt_id, anchor in (timeline.get("optionAnchors") or {}).items():
                    if _dialog_tree_option_prefix(opt_id) != conv_key:
                        continue
                    if not isinstance(anchor, dict):
                        continue
                    after_id = str(anchor.get("after") or "")
                    if after_id:
                        timeline_authored_option_ids.add(opt_id)
                        timeline_after.setdefault(opt_id, after_id)
                        if timeline_line_ids and opt_id not in timeline_after_line_ids:
                            timeline_after_line_ids[opt_id] = timeline_line_ids
                            timeline_after_line_timings[opt_id] = timeline_line_timing_by_id
                            timeline_after_runtime_jump_clips[opt_id] = (
                                list(timeline.get("runtimeJumpClips") or [])
                                if "runtimeJumpClips" in timeline
                                else None
                            )
                    elif anchor.get("position") == "pre":
                        timeline_authored_option_ids.add(opt_id)
                        timeline_pre.add(opt_id)
        line_idxs: list[tuple[int, str]] = []
        valid_line_ids: set[str] = set()
        if lines:
            for ln in lines:
                lid = ln.get("id") or ""
                if lid:
                    valid_line_ids.add(lid)
                m = re.search(r"_(\d+)$", lid)
                if m:
                    line_idxs.append((int(m.group(1)), lid))
        line_idxs.sort()
        # Fallback anchors when DialogTree/timeline data leaves option groups
        # unanchored. Four signals, in priority order:
        #   1. sparse-gap boundaries 鈥?between two contiguous numbering runs,
        #      the player choice plays during the missing slot.
        #   2. timeline option-clip positions 鈥?when this conv shares a Unity
        #      Timeline with another scene (e.g. dlg_e2m6_11 + dlg_e2m6_19),
        #      the option clip's start time tells us which of THIS conv's
        #      lines plays just before the choice. We surface that even when
        #      the recorded `_optionId` belongs to the sibling scene.
        #   3. exact group/line number 鈥?in contiguous table-only scenes,
        #      option group g=1 follows line _001 by key convention. This is
        #      promoted to a source-keyed anchor rather than a warning-only
        #      fallback because both sides carry the same authored group index.
        #   4. dialog last line 鈥?for cinematic-finish patterns where one
        #      option clip drives end-of-arc finish-num branches.
        # All four write to optionGroups[].after; `inferredAnchorMode` in the
        # warning's groupDetails records which signal won.
        fallback_after_ids: list[str] = []
        fallback_group_line_ids: dict[int, str] = {}
        last_line_fallback_id = ""
        if line_idxs:
            fallback_group_line_ids = {
                idx: line_id
                for idx, line_id in line_idxs
            }
            runs: list[list[tuple[int, str]]] = [[line_idxs[0]]]
            for prev, nxt in zip(line_idxs, line_idxs[1:]):
                if nxt[0] == prev[0] + 1:
                    runs[-1].append(nxt)
                else:
                    runs.append([nxt])
            gap_after_ids: list[str] = []
            for run_idx, run in enumerate(runs):
                if run_idx > 0:
                    prev_run = runs[run_idx - 1]
                    if prev_run:
                        gap_after_ids.append(prev_run[-1][1])
            fallback_after_ids.extend(gap_after_ids)
            last_line_fallback_id = line_idxs[-1][1]
        sibling_position_anchors = collect_option_position_anchors(conv_key) if conv_key else []
        group_option_ids_by_group: dict[int, list[str]] = {
            group_id: [
                opt.get("id") or ""
                for opt in sorted(group_opts, key=lambda o: o.get("i", 0))
                if isinstance(opt, dict) and opt.get("id")
            ]
            for group_id, group_opts in groups_map.items()
        }
        option_count_hist = Counter(
            len(group_opt_ids)
            for group_opt_ids in group_option_ids_by_group.values()
            if group_opt_ids
        )
        def cinematic_finish_anchor(finish_group: dict, option_count: int) -> tuple[str, list[str]]:
            finish_nums = finish_group.get("finishNums") or []
            if not isinstance(finish_nums, list) or len(finish_nums) != option_count:
                return "", []
            target_count = finish_group.get("targetCount")
            if isinstance(target_count, int) and target_count and target_count != option_count:
                return "", []
            timeline_name = str(finish_group.get("timeline") or "").strip()
            if not timeline_name:
                return "", []
            source_bits = [
                str(value)
                for value in (
                    finish_group.get("sourceKey"),
                    finish_group.get("file"),
                    timeline_name,
                )
                if str(value or "").strip()
            ]
            for timeline in timeline_entries:
                entry_names = {
                    str(timeline.get("sourceKey") or "").strip(),
                    str(timeline.get("timeline") or "").strip(),
                }
                if timeline_name not in entry_names:
                    continue
                timeline_line_ids = [
                    str(line_id)
                    for line_id in (timeline.get("lineIds") or [])
                    if str(line_id).strip()
                ]
                for line_id in reversed(timeline_line_ids):
                    if line_id in valid_line_ids:
                        if file_path := str(timeline.get("file") or "").strip():
                            source_bits.append(file_path)
                        return line_id, _unique_preserve(source_bits)
            after_id = str(finish_group.get("after") or "").strip()
            if after_id in valid_line_ids:
                return after_id, _unique_preserve(source_bits)
            return "", []
        # Cinematic finish-number branches describe timeline outcomes, not
        # explicit option UI placement. Keep them out of authored option
        # anchoring unless an extracted option clip/node names the current
        # option ids directly.
        def option_signature_sequence(option_ids: list[str]) -> list[tuple[str, str]]:
            signatures: list[tuple[str, str]] = []
            for opt_id in option_ids:
                signature = dialog_option_signature_by_id.get(opt_id)
                if not signature or not signature[0]:
                    return []
                signatures.append(signature)
            return signatures
        def option_signatures_compatible(left_ids: list[str], right_ids: list[str]) -> bool:
            if len(left_ids) != len(right_ids) or not left_ids:
                return False
            for left_id, right_id in zip(left_ids, right_ids):
                left_text, left_icon = dialog_option_signature_by_id.get(left_id, ("", ""))
                right_text, right_icon = dialog_option_signature_by_id.get(right_id, ("", ""))
                if not left_text or not right_text:
                    return False
                if left_icon and right_icon and left_icon != right_icon:
                    return False
                if left_text == right_text:
                    continue
                if left_text in right_text or right_text in left_text:
                    continue
                if not _sequence_similarity_at_least(left_text, right_text, 0.92):
                    return False
            return True
        def dialog_line_text_signature(line_id: str) -> str:
            row = dialogs.get(line_id)
            if not isinstance(row, dict):
                return ""
            text_value = t((row.get("dialogText") or {}).get("id"))
            return _option_text_signature(text_value)
        def sibling_scene_text_branch_for_group(
            group_opt_ids: list[str],
            after_id: str,
            sibling_anchor_record: dict | None,
            group_id: int,
        ) -> dict:
            if (
                not group_opt_ids
                or len(group_opt_ids) < 2
                or not after_id
                or not sibling_anchor_record
            ):
                return {}
            sibling_scenes = [
                str(scene_key)
                for scene_key in (sibling_anchor_record.get("siblingScenes") or [])
                if str(scene_key or "").strip() and str(scene_key) != conv_key
            ]
            if not sibling_scenes:
                return {}
            local_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
            if after_id in local_line_ids:
                local_candidate_line_ids = local_line_ids[local_line_ids.index(after_id) + 1:]
            else:
                local_candidate_line_ids = local_line_ids
            if not local_candidate_line_ids:
                return {}
            local_signature_by_line_id = {
                line_id: _option_text_signature(str(line.get("text") or ""))
                for line in (lines or [])
                if (line_id := str(line.get("id") or "")) in valid_line_ids
            }
            if not local_signature_by_line_id:
                return {}
            for sibling_scene in sibling_scenes:
                sibling_opt_ids = dialog_option_group_ids_by_key.get((sibling_scene, group_id)) or []
                if not option_signatures_compatible(group_opt_ids, sibling_opt_ids):
                    continue
                sibling_tree = load_dialog_tree(sibling_scene) or {}
                sibling_branches = sibling_tree.get("branches") or {}
                branch_line_ids_by_option: dict[str, list[str]] = {}
                sibling_line_ids_by_option: dict[str, list[str]] = {}
                used_local_line_ids: set[str] = set()
                for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids):
                    sibling_branch_line_ids = [
                        str(line_id)
                        for line_id in (sibling_branches.get(sibling_opt_id) or [])
                        if str(line_id or "").strip()
                    ]
                    if not sibling_branch_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    mapped_line_ids: list[str] = []
                    for sibling_line_id in sibling_branch_line_ids:
                        sibling_signature = dialog_line_text_signature(sibling_line_id)
                        if not sibling_signature:
                            mapped_line_ids = []
                            break
                        matches = [
                            local_line_id
                            for local_line_id in local_candidate_line_ids
                            if local_line_id not in used_local_line_ids
                            and local_signature_by_line_id.get(local_line_id) == sibling_signature
                        ]
                        if len(matches) != 1:
                            mapped_line_ids = []
                            break
                        mapped_line_id = matches[0]
                        used_local_line_ids.add(mapped_line_id)
                        mapped_line_ids.append(mapped_line_id)
                    if not mapped_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    branch_line_ids_by_option[local_opt_id] = mapped_line_ids
                    sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                if len(branch_line_ids_by_option) != len(group_opt_ids):
                    continue
                if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
                    continue
                sibling_option_ids_by_option = {
                    local_opt_id: sibling_opt_id
                    for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids)
                }
                source_bits = _unique_preserve([
                    str(value)
                    for value in (
                        sibling_scene,
                        sibling_tree.get("sourceKey") or "",
                        sibling_tree.get("file") or "",
                        sibling_anchor_record.get("timeline") or "",
                    )
                    if str(value or "").strip()
                ])
                return {
                    "code": "siblingSceneTextBranches",
                    "reason": "siblingSceneTextMatch",
                    "detail": (
                        "A sibling scene on the same dialog Timeline has authored "
                        "SceneGraph option branches whose branch texts exactly "
                        "match local lines after this fallback option anchor."
                    ),
                    "after": after_id,
                    "optionIds": group_opt_ids,
                    "branchLineIdsByOption": branch_line_ids_by_option,
                    "siblingScene": sibling_scene,
                    "siblingOptionIdsByOption": sibling_option_ids_by_option,
                    "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
                    "source": "siblingSceneGraphText",
                    "sources": source_bits,
                }
            return {}
        def sibling_scene_template_branch_for_group(
            group_opt_ids: list[str],
            after_id: str,
            group_id: int,
        ) -> dict:
            if not group_opt_ids or len(group_opt_ids) < 2:
                return {}
            local_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
            if len(local_line_ids) < 3:
                return {}
            local_signature_by_line_id = {
                line_id: _option_text_signature(str(line.get("text") or ""))
                for line in (lines or [])
                if (line_id := str(line.get("id") or "")) in valid_line_ids
            }
            if not local_signature_by_line_id:
                return {}
            local_option_signatures = option_signature_sequence(group_opt_ids)
            if not local_option_signatures:
                return {}
            sibling_group_keys = [
                key
                for key in dialog_option_group_keys_by_group_and_count.get(
                    (group_id, len(group_opt_ids)),
                    [],
                )
                if key[0] != conv_key
            ]
            for sibling_scene, _sibling_group_id in sibling_group_keys:
                sibling_opt_ids = dialog_option_group_ids_by_key.get((sibling_scene, group_id)) or []
                sibling_signatures = option_signature_sequence(sibling_opt_ids)
                if not sibling_signatures:
                    continue
                compatible_positions = 0
                icons_compatible = True
                for (local_text, local_icon), (sibling_text, sibling_icon) in zip(local_option_signatures, sibling_signatures):
                    if local_icon and sibling_icon and local_icon != sibling_icon:
                        icons_compatible = False
                        break
                    if local_text == sibling_text or local_text in sibling_text or sibling_text in local_text:
                        compatible_positions += 1
                    elif _sequence_similarity_at_least(local_text, sibling_text, 0.92):
                        compatible_positions += 1
                if not icons_compatible or compatible_positions < max(2, len(group_opt_ids) - 1):
                    continue
                sibling_tree = load_dialog_tree(sibling_scene) or {}
                sibling_branches = sibling_tree.get("branches") or {}
                sibling_after = sibling_tree.get("after") or {}
                if not sibling_branches:
                    continue
                sibling_after_ids = [
                    str(sibling_after.get(opt_id) or "")
                    for opt_id in sibling_opt_ids
                    if str(sibling_after.get(opt_id) or "").strip()
                ]
                if len(set(sibling_after_ids)) != 1:
                    continue
                sibling_after_id = sibling_after_ids[0]
                sibling_after_text = dialog_line_text_signature(sibling_after_id)
                if not sibling_after_text:
                    continue
                local_after_candidates = [
                    local_line_id
                    for local_line_id in local_line_ids
                    if (
                        local_signature_by_line_id.get(local_line_id) == sibling_after_text
                        or _sequence_similarity_at_least(
                            local_signature_by_line_id.get(local_line_id) or "",
                            sibling_after_text,
                            0.80,
                        )
                    )
                ]
                if not local_after_candidates:
                    continue
                branch_line_ids_by_option: dict[str, list[str]] = {}
                sibling_line_ids_by_option: dict[str, list[str]] = {}
                used_local_line_ids: set[str] = set()
                missing_options: list[tuple[str, str, list[str]]] = []
                for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids):
                    sibling_branch_line_ids = [
                        str(line_id)
                        for line_id in (sibling_branches.get(sibling_opt_id) or [])
                        if str(line_id or "").strip()
                    ]
                    if not sibling_branch_line_ids:
                        branch_line_ids_by_option = {}
                        break
                    mapped_line_ids: list[str] = []
                    for sibling_line_id in sibling_branch_line_ids:
                        sibling_signature = dialog_line_text_signature(sibling_line_id)
                        if not sibling_signature:
                            mapped_line_ids = []
                            break
                        matches = [
                            local_line_id
                            for local_line_id in local_line_ids
                            if local_line_id not in used_local_line_ids
                            and local_signature_by_line_id.get(local_line_id) == sibling_signature
                        ]
                        if len(matches) != 1:
                            mapped_line_ids = []
                            break
                        mapped_line_id = matches[0]
                        used_local_line_ids.add(mapped_line_id)
                        mapped_line_ids.append(mapped_line_id)
                    if mapped_line_ids:
                        branch_line_ids_by_option[local_opt_id] = mapped_line_ids
                        sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                    else:
                        missing_options.append((local_opt_id, sibling_opt_id, sibling_branch_line_ids))
                if not branch_line_ids_by_option or len(missing_options) > 1:
                    continue
                mapped_indices = [
                    local_line_ids.index(line_id)
                    for mapped_lines in branch_line_ids_by_option.values()
                    for line_id in mapped_lines
                    if line_id in local_line_ids
                ]
                if not mapped_indices:
                    continue
                earliest_mapped_index = min(mapped_indices)
                local_after_id = ""
                for candidate in reversed(local_after_candidates):
                    candidate_index = local_line_ids.index(candidate)
                    if candidate_index < earliest_mapped_index:
                        local_after_id = candidate
                        break
                if not local_after_id:
                    continue
                after_index = local_line_ids.index(local_after_id)
                if after_id and after_id in local_line_ids and local_line_ids.index(after_id) > after_index:
                    continue
                if missing_options:
                    local_opt_id, sibling_opt_id, sibling_branch_line_ids = missing_options[0]
                    inferred_lines = [
                        line_id
                        for line_id in local_line_ids[after_index + 1:earliest_mapped_index]
                        if line_id not in used_local_line_ids
                    ]
                    if not inferred_lines:
                        continue
                    branch_line_ids_by_option[local_opt_id] = inferred_lines
                    sibling_line_ids_by_option[local_opt_id] = sibling_branch_line_ids
                if len(branch_line_ids_by_option) != len(group_opt_ids):
                    continue
                if len({tuple(line_ids) for line_ids in branch_line_ids_by_option.values()}) < 2:
                    continue
                sibling_option_ids_by_option = {
                    local_opt_id: sibling_opt_id
                    for local_opt_id, sibling_opt_id in zip(group_opt_ids, sibling_opt_ids)
                }
                source_bits = _unique_preserve([
                    str(value)
                    for value in (
                        sibling_scene,
                        sibling_tree.get("sourceKey") or "",
                        sibling_tree.get("file") or "",
                    )
                    if str(value or "").strip()
                ])
                return {
                    "code": "siblingSceneTextBranches",
                    "reason": "siblingSceneTemplate",
                    "detail": (
                        "A sibling scene has authored SceneGraph option branches "
                        "with matching option layout and repeated local branch text; "
                        "unmatched local lines between the sibling-matched anchor and "
                        "the first matched branch are assigned to the remaining option."
                    ),
                    "after": local_after_id,
                    "previousAfter": after_id,
                    "optionIds": group_opt_ids,
                    "branchLineIdsByOption": branch_line_ids_by_option,
                    "siblingScene": sibling_scene,
                    "siblingOptionIdsByOption": sibling_option_ids_by_option,
                    "siblingBranchLineIdsByOption": sibling_line_ids_by_option,
                    "source": "siblingSceneGraphText",
                    "sources": source_bits,
                }
            return {}
        def source_bits_for_options(option_ids: list[str], source_map: dict[str, object]) -> list[str]:
            source_bits: list[str] = []
            for opt_id in option_ids:
                raw_sources = source_map.get(opt_id) if isinstance(source_map, dict) else None
                if isinstance(raw_sources, list):
                    source_bits.extend(str(source) for source in raw_sources if str(source or "").strip())
                elif raw_sources:
                    source_bits.append(str(raw_sources))
            return _unique_preserve(source_bits)
        def complete_foreign_option_group(
            group_key: tuple[str, int],
            raw_entries: list[tuple[int, str]],
        ) -> list[str]:
            foreign_ids = [
                opt_id
                for _idx, opt_id in sorted(raw_entries, key=lambda item: item[0])
                if opt_id
            ]
            if not foreign_ids or len(set(foreign_ids)) != len(foreign_ids):
                return []
            full_foreign_ids = dialog_option_group_ids_by_key.get(group_key) or []
            if not full_foreign_ids or foreign_ids != full_foreign_ids:
                return []
            return foreign_ids
        foreign_after_groups: dict[tuple[str, int], list[tuple[int, str, str]]] = defaultdict(list)
        for foreign_opt_id, raw_after in tree_after.items():
            parts = _option_id_group_parts(foreign_opt_id)
            candidate_after = str(raw_after or "")
            if not parts or not candidate_after or candidate_after not in valid_line_ids:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_after_groups[(scene_key, foreign_group_id)].append(
                (foreign_index, foreign_opt_id, candidate_after)
            )
        foreign_pre_groups: dict[tuple[str, int], list[tuple[int, str]]] = defaultdict(list)
        for foreign_opt_id in tree_pre:
            parts = _option_id_group_parts(foreign_opt_id)
            if not parts:
                continue
            scene_key, foreign_group_id, foreign_index = parts
            if scene_key == conv_key:
                continue
            foreign_pre_groups[(scene_key, foreign_group_id)].append((foreign_index, foreign_opt_id))
        for group_id, group_opt_ids in group_option_ids_by_group.items():
            local_signature = option_signature_sequence(group_opt_ids)
            if not local_signature:
                continue
            after_matches: list[tuple[str, list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_after_groups.items():
                ordered_entries = sorted(raw_entries, key=lambda item: item[0])
                foreign_ids = complete_foreign_option_group(
                    foreign_group_key,
                    [(idx, opt_id) for idx, opt_id, _after in ordered_entries],
                )
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                anchors = {after for _idx, _opt_id, after in ordered_entries}
                if len(anchors) != 1:
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_after_sources)
                after_matches.append((next(iter(anchors)), foreign_ids, source_bits))
            # Exact text/icon aliases are useful investigation hints, but they
            # are not firm authored placement for the current option ids.
            # Only direct extracted references may anchor options.
            if len(after_matches) == 1:
                continue
            pre_matches: list[tuple[list[str], list[str]]] = []
            for foreign_group_key, raw_entries in foreign_pre_groups.items():
                foreign_ids = complete_foreign_option_group(foreign_group_key, raw_entries)
                if len(foreign_ids) != len(group_opt_ids):
                    continue
                if option_signature_sequence(foreign_ids) != local_signature:
                    continue
                source_bits = source_bits_for_options(foreign_ids, tree_pre_sources)
                pre_matches.append((foreign_ids, source_bits))
            if len(pre_matches) == 1:
                continue
        out: list[dict] = []
        authored_option_ids = (
            set(tree_after)
            | set(tree_branches)
            | set(tree_merge)
            | tree_pre
            | scene_link_authored_option_ids
            | timeline_authored_option_ids
        )
        authored_group_count = 0
        pre_group_count = 0
        keyed_group_count = 0
        sibling_text_group_count = 0
        fallback_group_count = 0
        unanchored_group_count = 0
        fallback_group_labels: list[str] = []
        group_details: list[dict] = []
        option_response_risks: list[dict] = []
        manual_option_response_overrides: list[dict] = []
        def preferred_timeline_option_row(opt_id: str) -> dict:
            rows = timeline_option_rows.get(opt_id) or []
            if not rows:
                return {}
            return min(
                rows,
                key=lambda row: (
                    0 if row.get("anchorMode") == "trunkBinding" else 1,
                    float(row.get("start") or 0.0),
                    row.get("optionIndex") if row.get("optionIndex") is not None else 10**9,
                    row.get("assetTrack") or "",
                ),
            )
        def preferred_timeline_option_route(opt_id: str) -> dict:
            routes = timeline_option_routes.get(opt_id) or []
            if not routes:
                return {}
            return max(
                routes,
                key=lambda route: (
                    len(route.get("pathLineIds") or []),
                    -float(route.get("start") or 0.0),
                    str(route.get("source") or ""),
                ),
            )
        def timeline_route_branch_for_group(group_opt_ids: list[str], after_id: str) -> dict:
            if len(group_opt_ids) < 2 or not after_id:
                return {}
            if any(tree_branches.get(opt_id) for opt_id in group_opt_ids):
                return {}
            anchors = [timeline_after.get(opt_id) or "" for opt_id in group_opt_ids]
            if not all(anchor == after_id for anchor in anchors):
                return {}
            routes = [preferred_timeline_option_route(opt_id) for opt_id in group_opt_ids]
            # A route is acceptable when either it lists per-option lines OR it
            # flags `terminatesSlot` 鈥?the latter means the option's Runtime
            # Jump skip range covers the whole post-anchor window so no in-slot
            # lines play.
            if not all(
                route.get("pathLineIds") or route.get("terminatesSlot")
                for route in routes
            ):
                return {}
            branch_line_ids_by_option: dict[str, list[str]] = {}
            skipped_line_ids_by_option: dict[str, list[str]] = {}
            reverse_range_line_ids_by_option: dict[str, list[str]] = {}
            terminating_option_ids: list[str] = []
            for opt_id, route in zip(group_opt_ids, routes):
                path_line_ids = [
                    str(line_id)
                    for line_id in (route.get("pathLineIds") or [])
                    if line_id in valid_line_ids
                ]
                terminates_slot = bool(route.get("terminatesSlot"))
                if terminates_slot and not path_line_ids:
                    terminating_option_ids.append(opt_id)
                elif not path_line_ids:
                    return {}
                branch_line_ids_by_option[opt_id] = path_line_ids
                skipped_line_ids_by_option[opt_id] = [
                    str(line_id)
                    for line_id in (route.get("skippedLineIds") or [])
                    if line_id in valid_line_ids
                ]
                reverse_range_line_ids_by_option[opt_id] = [
                    str(line_id)
                    for line_id in (route.get("reverseRangeLineIds") or [])
                    if line_id in valid_line_ids
                ]
            distinct_branch_signatures = {
                ("__terminatesSlot__",) if opt_id in terminating_option_ids else tuple(value)
                for opt_id, value in branch_line_ids_by_option.items()
            }
            if len(distinct_branch_signatures) < 2:
                return {}
            continuation_option_ids = _unique_preserve([
                str(option_id)
                for route in routes
                for option_id in (route.get("continuationOptionIds") or [])
                if str(option_id or "").strip()
            ])
            payload = {
                "code": "timelineRouteBranches",
                "reason": "runtimeJumpTrack",
                "detail": (
                    "Runtime Jump Track clips in the dialog Timeline mark "
                    "which time ranges each selected optionIndex skips or "
                    "re-enters; branch lines are recovered from those "
                    "directional route windows."
                ),
                "after": after_id,
                "optionIds": group_opt_ids,
                "branchLineIdsByOption": branch_line_ids_by_option,
                "skippedLineIdsByOption": skipped_line_ids_by_option,
                "reverseRangeLineIdsByOption": {
                    opt_id: line_ids
                    for opt_id, line_ids in reverse_range_line_ids_by_option.items()
                    if line_ids
                },
                "continuationOptionIds": continuation_option_ids,
                "source": "dialogTimeline",
                "optionIndex": [
                    route.get("optionIndex")
                    for route in routes
                ],
                "assetTracks": _unique_preserve([
                    str(raw_range.get("track") or raw_range.get("assetTrack") or "")
                    for route in routes
                    for raw_range in ((route.get("skipRanges") or []) + (route.get("reverseRanges") or []))
                    if str(raw_range.get("track") or raw_range.get("assetTrack") or "").strip()
                ]),
            }
            if terminating_option_ids:
                payload["terminatingOptionIds"] = terminating_option_ids
            return payload
        def following_line_risk_for_group(group_opt_ids: list[str], after_id: str) -> dict:
            if len(group_opt_ids) < 2 or not after_id:
                return {}
            if any(tree_branches.get(opt_id) for opt_id in group_opt_ids):
                return {}
            anchors = [timeline_after.get(opt_id) or "" for opt_id in group_opt_ids]
            if not all(anchor == after_id for anchor in anchors):
                return {}
            # Dialog tree shows all options converge to the same response trunk.
            # Only emit cosmeticChoice when Timeline anchors already matched (so this
            # is a group that would otherwise have become inferredFollowingLines).
            if all(opt_id in tree_converge for opt_id in group_opt_ids):
                trunk_ids = {tree_converge[opt_id] for opt_id in group_opt_ids}
                if len(trunk_ids) == 1:
                    common_trunk = next(iter(trunk_ids))
                    if common_trunk in valid_line_ids:
                        return {
                            "code": "cosmeticChoice",
                            "reason": "treeSourcedConvergence",
                            "detail": (
                                "Dialog tree shows all options in this group lead to the "
                                "same response trunk; the choice affects only the player's "
                                "displayed text, not which line plays next."
                            ),
                            "after": after_id,
                            "optionIds": group_opt_ids,
                            "candidateLineIds": [],
                            "commonContinuationLineId": common_trunk,
                            "source": "dialogTree",
                        }
            timeline_line_ids: list[str] = []
            timeline_line_timing_by_id: dict[str, dict] = {}
            for opt_id in group_opt_ids:
                candidate_order = timeline_after_line_ids.get(opt_id) or []
                if after_id in candidate_order:
                    timeline_line_ids = candidate_order
                    timeline_line_timing_by_id = timeline_after_line_timings.get(opt_id) or {}
                    break
            if not timeline_line_ids or after_id not in timeline_line_ids:
                return {}
            after_index = timeline_line_ids.index(after_id)
            candidate_line_ids = [
                line_id
                for line_id in timeline_line_ids[after_index + 1 : after_index + 1 + len(group_opt_ids)]
                if line_id in valid_line_ids
            ]
            if len(candidate_line_ids) != len(group_opt_ids):
                return {}
            common_continuation_id = ""
            for line_id in timeline_line_ids[after_index + 1 + len(group_opt_ids) :]:
                if line_id in valid_line_ids:
                    common_continuation_id = line_id
                    break
            preferred_rows = [preferred_timeline_option_row(opt_id) for opt_id in group_opt_ids]
            option_indices = [
                row.get("optionIndex") if isinstance(row.get("optionIndex"), int) else None
                for row in preferred_rows
            ]
            candidate_clip_indices = [
                (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                for line_id in candidate_line_ids
            ]
            candidate_timing_rows = [
                timeline_line_timing_by_id.get(line_id) or {}
                for line_id in candidate_line_ids
            ]
            candidate_starts = [
                float(row.get("start"))
                for row in candidate_timing_rows
                if isinstance(row.get("start"), (int, float))
            ]
            candidate_ends = [
                float(row.get("start")) + float(row.get("duration") or 0.0)
                for row in candidate_timing_rows
                if isinstance(row.get("start"), (int, float))
            ]
            runtime_jump_clips = (
                timeline_after_runtime_jump_clips.get(group_opt_ids[0])
                if group_opt_ids
                else None
            )
            continuation_classification = classify_zero_index_timeline_continuation(
                option_indices,
                candidate_clip_indices,
                candidate_window_start=min(candidate_starts) if candidate_starts else None,
                candidate_window_end=max(candidate_ends) if candidate_ends else None,
                runtime_jump_clips=runtime_jump_clips,
            )
            if continuation_classification.get("status") == "shared":
                reason = str(
                    continuation_classification.get("reason")
                    or "defaultTrunkClipContinuation"
                )
                detail = (
                    "The current game runtime only activates option-bound trunk "
                    "clips whose runtime option field is positive. Every adjacent "
                    "candidate trunk clip carries clipOptionIndex 0, and no raw "
                    "Runtime Jump overlaps this window, so these lines are a shared "
                    "Timeline continuation rather than per-option replies."
                )
                if reason == "rawOptionIndexConverges":
                    detail = (
                        "Both the UI option rows and adjacent trunk clips resolve to "
                        "raw optionIndex 0. The current game runtime treats this as "
                        "shared Timeline continuation rather than option-specific "
                        "branch replies."
                    )
                if reason == "defaultTrunkClipContinuationWithRuntimeJump":
                    detail = (
                        "Every adjacent candidate trunk clip carries "
                        "clipOptionIndex 0, so the window is shared immediate "
                        "continuation rather than one reply per option. Raw "
                        "Runtime Jump clips overlap the window but do not form "
                        "a complete per-option route; they remain attached as "
                        "later-route uncertainty instead of being converted "
                        "into adjacent reply targets."
                    )
                result = {
                    "code": "sharedTimelineContinuation",
                    "reason": reason,
                    "detail": detail,
                    "after": after_id,
                    "optionIds": group_opt_ids,
                    "candidateLineIds": [],
                    "candidateWindowLineIds": candidate_line_ids,
                    "commonContinuationLineId": candidate_line_ids[0],
                    "source": "dialogTimeline",
                    "optionIndex": option_indices,
                    "candidateLineClipOptionIndex": candidate_clip_indices,
                    "optionIndexPattern": continuation_classification.get("optionIndexPattern"),
                    "candidateLineClipOptionIndexPattern": continuation_classification.get(
                        "candidateLineClipOptionIndexPattern"
                    ),
                }
                if continuation_classification.get("runtimeJumpRouteStatus"):
                    result["runtimeJumpRouteStatus"] = continuation_classification[
                        "runtimeJumpRouteStatus"
                    ]
                if continuation_classification.get("overlappingRuntimeJumpClips"):
                    result["overlappingRuntimeJumpClips"] = continuation_classification[
                        "overlappingRuntimeJumpClips"
                    ]
                return result
            candidate_mapping = ""
            branch_line_ids_by_option: dict[str, list[str]] = {}
            branch_clip_indices_by_option: dict[str, list[int]] = {}
            if (
                len(candidate_clip_indices) == len(candidate_line_ids) == len(option_indices)
                and all(isinstance(value, int) for value in candidate_clip_indices)
                and all(isinstance(value, int) for value in option_indices)
                and len(set(candidate_clip_indices)) == len(candidate_clip_indices)
                and set(candidate_clip_indices) == set(option_indices)
            ):
                line_id_by_clip_index = {
                    clip_index: line_id
                    for line_id, clip_index in zip(candidate_line_ids, candidate_clip_indices)
                }
                reordered_candidate_line_ids = [
                    line_id_by_clip_index.get(option_index)
                    for option_index in option_indices
                ]
                if (
                    len(reordered_candidate_line_ids) == len(candidate_line_ids)
                    and all(line_id in valid_line_ids for line_id in reordered_candidate_line_ids)
                ):
                    candidate_line_ids = [str(line_id) for line_id in reordered_candidate_line_ids]
                    candidate_mapping = "trunkClipOptionIndex"
                    candidate_clip_indices = [
                        (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                        for line_id in candidate_line_ids
                    ]
                    option_index_set = {value for value in option_indices if isinstance(value, int) and value != 0}
                    branch_line_ids_by_index: dict[int, list[str]] = {value: [] for value in option_index_set}
                    branch_clip_indices_by_index: dict[int, list[int]] = {value: [] for value in option_index_set}
                    branch_window_end_index = after_index + len(candidate_line_ids)
                    for index, line_id in enumerate(timeline_line_ids[after_index + 1 :], start=after_index + 1):
                        if line_id not in valid_line_ids:
                            continue
                        clip_index = (timeline_line_timing_by_id.get(line_id) or {}).get("clipOptionIndex")
                        if isinstance(clip_index, int) and clip_index in option_index_set:
                            branch_line_ids_by_index.setdefault(clip_index, []).append(line_id)
                            branch_clip_indices_by_index.setdefault(clip_index, []).append(clip_index)
                            branch_window_end_index = index
                            continue
                        break
                    for opt_id, option_index in zip(group_opt_ids, option_indices):
                        if not isinstance(option_index, int):
                            continue
                        branch_lines = [
                            line_id
                            for line_id in (branch_line_ids_by_index.get(option_index) or [])
                            if line_id in valid_line_ids
                        ]
                        if not branch_lines:
                            branch_lines = [
                                line_id
                                for line_id in [line_id_by_clip_index.get(option_index)]
                                if line_id in valid_line_ids
                            ]
                        if branch_lines:
                            branch_line_ids_by_option[opt_id] = branch_lines
                            branch_clip_indices_by_option[opt_id] = [
                                int(value)
                                for value in (branch_clip_indices_by_index.get(option_index) or [option_index])
                                if isinstance(value, int)
                            ]
                    for line_id in timeline_line_ids[branch_window_end_index + 1 :]:
                        if line_id in valid_line_ids:
                            common_continuation_id = line_id
                            break
            detail = (
                "Timeline option metadata anchors this group to a trunk line, "
                "but the option entries do not name explicit target trunk ids; "
                "the following line candidates are inferred from Timeline order."
            )
            if candidate_mapping:
                detail = (
                    "Timeline option metadata anchors this group to a trunk line, "
                    "but the option entries do not name explicit target trunk ids; "
                    "candidate response lines and same-index branch continuations "
                    "are matched to options by the raw trunk clip optionIndex values."
                )
            risk = {
                "code": "inferredFollowingLines",
                "reason": "optionTargetsMissing",
                "detail": detail,
                "after": after_id,
                "optionIds": group_opt_ids,
                "candidateLineIds": candidate_line_ids,
                "commonContinuationLineId": common_continuation_id,
                "source": "dialogTimeline",
                "optionIndex": [
                    row.get("optionIndex")
                    for row in preferred_rows
                ],
                "assetTracks": _unique_preserve([
                    str(row.get("assetTrack") or "")
                    for row in preferred_rows
                    if row.get("assetTrack")
                ]),
            }
            if continuation_classification.get("status") in {"blocked", "unverified"}:
                risk["runtimeContinuationClassification"] = continuation_classification
            if candidate_mapping:
                risk["candidateMapping"] = candidate_mapping
                risk["candidateLineIdsByOption"] = {
                    opt_id: branch_line_ids_by_option.get(opt_id) or [line_id]
                    for opt_id, line_id in zip(group_opt_ids, candidate_line_ids)
                }
                risk["candidateLineClipOptionIndex"] = candidate_clip_indices
                if branch_line_ids_by_option:
                    risk["branchLineIdsByOption"] = branch_line_ids_by_option
                if branch_clip_indices_by_option:
                    risk["branchLineClipOptionIndexByOption"] = branch_clip_indices_by_option
            return risk
        def option_risk_line_ids(following_line_risk: dict, option_count: int) -> list[str]:
            option_ids = [
                str(option_id)
                for option_id in (following_line_risk.get("optionIds") or [])
                if str(option_id or "").strip()
            ]
            candidate_lines_by_option = following_line_risk.get("candidateLineIdsByOption")
            if isinstance(candidate_lines_by_option, dict) and len(option_ids) == option_count:
                mapped_line_ids: list[str] = []
                for option_id in option_ids:
                    mapped_value = candidate_lines_by_option.get(option_id)
                    if isinstance(mapped_value, list):
                        line_id = next(
                            (
                                str(value)
                                for value in mapped_value
                                if str(value or "") in valid_line_ids
                            ),
                            "",
                        )
                    else:
                        line_id = str(mapped_value or "")
                    if line_id not in valid_line_ids:
                        break
                    mapped_line_ids.append(line_id)
                if len(mapped_line_ids) == option_count:
                    return mapped_line_ids
            candidate_line_ids = [
                str(line_id)
                for line_id in (following_line_risk.get("candidateLineIds") or [])
                if line_id in valid_line_ids
            ]
            if len(candidate_line_ids) == option_count:
                return candidate_line_ids
            common_line_id = str(following_line_risk.get("commonContinuationLineId") or "")
            if common_line_id in valid_line_ids:
                return [common_line_id for _ in range(option_count)]
            return []
        def all_option_response_risk_line_ids(following_line_risk: dict) -> list[str]:
            out: list[str] = []
            def push(line_id: object) -> None:
                value = str(line_id or "")
                if value and value in valid_line_ids and value not in out:
                    out.append(value)
            for line_id in following_line_risk.get("candidateLineIds") or []:
                push(line_id)
            branch_lines_by_option = following_line_risk.get("branchLineIdsByOption")
            if isinstance(branch_lines_by_option, dict):
                for line_ids in branch_lines_by_option.values():
                    if isinstance(line_ids, list):
                        for line_id in line_ids:
                            push(line_id)
                    else:
                        push(line_ids)
            return out
        sorted_group_ids = sorted(groups_map)
        sorted_group_index = {group_id: idx for idx, group_id in enumerate(sorted_group_ids)}
        local_ordered_line_ids = [line_id for _idx, line_id in line_idxs if line_id in valid_line_ids]
        local_line_order_index = {
            line_id: idx for idx, line_id in enumerate(local_ordered_line_ids)
        }
        rendered_ordered_line_ids = [
            str(line.get("id") or "")
            for line in (lines or [])
            if str(line.get("id") or "") in valid_line_ids
        ]
        rendered_line_order_index = {
            line_id: idx for idx, line_id in enumerate(rendered_ordered_line_ids)
        }
        local_scene_link_options_by_after: dict[str, list[dict]] = defaultdict(list)
        seen_local_scene_link_options: set[tuple[str, str, tuple[str, ...]]] = set()
        for link in build_dialog_tree_scene_link_payload(conv_key) or []:
            after_id = str(link.get("after") or "")
            if after_id not in valid_line_ids:
                continue
            for option in link.get("options") or []:
                if not isinstance(option, dict):
                    continue
                path_line_ids = tuple(
                    str(line_id)
                    for line_id in (option.get("pathLineIds") or [])
                    if str(line_id or "") in valid_line_ids
                )
                if not path_line_ids:
                    continue
                option_id = str(option.get("optionId") or "")
                identity = (after_id, option_id, path_line_ids)
                if identity in seen_local_scene_link_options:
                    continue
                seen_local_scene_link_options.add(identity)
                local_scene_link_options_by_after[after_id].append(option)
        def option_has_visible_table_text(option_id: str) -> bool:
            text_value, _icon_value = dialog_option_signature_by_id.get(option_id, ("", ""))
            return bool(text_value)
        def hidden_single_option_path_after(after_id: str) -> tuple[str, list[str]]:
            options_after = [
                option
                for option in local_scene_link_options_by_after.get(after_id, [])
                if _dialog_tree_option_prefix(str(option.get("optionId") or "")) == conv_key
            ]
            if len(options_after) != 1:
                return "", []
            option = options_after[0]
            option_id = str(option.get("optionId") or "")
            if not option_id or option_has_visible_table_text(option_id):
                return "", []
            path_line_ids = [
                str(line_id)
                for line_id in (option.get("pathLineIds") or [])
                if str(line_id or "") in valid_line_ids
            ]
            return option_id, path_line_ids
        def expand_transparent_single_option_branch(branch_lines: list[str]) -> list[str]:
            expanded: list[str] = []
            expanded_after_ids: set[str] = set()
            def append_line(line_id: str) -> None:
                if line_id in valid_line_ids and line_id not in expanded:
                    expanded.append(line_id)
            for line_id in branch_lines:
                append_line(line_id)
            while expanded:
                after_id = expanded[-1]
                if after_id in expanded_after_ids:
                    break
                expanded_after_ids.add(after_id)
                _option_id, next_path = hidden_single_option_path_after(after_id)
                if not next_path:
                    break
                first_next = next_path[0]
                start_index = rendered_line_order_index.get(after_id)
                end_index = rendered_line_order_index.get(first_next)
                if start_index is not None and end_index is not None and start_index < end_index:
                    for line_id in rendered_ordered_line_ids[start_index + 1:end_index]:
                        append_line(line_id)
                before_count = len(expanded)
                for line_id in next_path:
                    append_line(line_id)
                if len(expanded) == before_count:
                    break
            return expanded
        def normalize_group_branch_convergence(group: dict, opts: list[dict], group_opt_ids: list[str]) -> dict:
            if len(opts) < 2 or len(group_opt_ids) != len(opts):
                return {}
            paths: list[list[str]] = []
            for opt in opts:
                branch_lines = [
                    str(line_id)
                    for line_id in (opt.get("branchLines") or [])
                    if str(line_id or "") in valid_line_ids
                ]
                if not branch_lines:
                    return {}
                paths.append(branch_lines)
            min_length = min(len(path) for path in paths)
            suffix_length = 0
            while suffix_length < min_length:
                candidate = paths[0][len(paths[0]) - suffix_length - 1]
                if not all(path[len(path) - suffix_length - 1] == candidate for path in paths):
                    break
                suffix_length += 1
            if suffix_length <= 0:
                return {}
            if any(len(path) <= suffix_length for path in paths):
                return {}
            common_suffix = paths[0][len(paths[0]) - suffix_length:]
            branch_line_ids_by_option: dict[str, list[str]] = {}
            for opt, opt_id, path in zip(opts, group_opt_ids, paths):
                branch_specific_lines = path[:len(path) - suffix_length]
                if not branch_specific_lines:
                    return {}
                opt["branchLines"] = branch_specific_lines
                branch_line_ids_by_option[opt_id] = branch_specific_lines
                opt.setdefault("_debug", {})["branchConvergence"] = {
                    "mode": "commonSuffix",
                    "commonLineIds": common_suffix,
                }
            return {
                "code": "dialogTreeBranchConvergence",
                "reason": "commonBranchSuffix",
                "detail": (
                    "Authored same-scene branch paths share a trailing line sequence; "
                    "branchLines are trimmed to branch-specific lines and rendered as "
                    "converging at the shared continuation."
                ),
                "after": group.get("after") or "",
                "optionIds": group_opt_ids,
                "branchLineIdsByOption": branch_line_ids_by_option,
                "commonContinuationLineId": common_suffix[0],
                "commonContinuationLineIds": common_suffix,
                "source": "dialogTree",
            }
        trusted_group_after_cache: dict[int, tuple[str, dict]] = {}
        recovered_single_option_line_ids: set[str] = set()
        def previous_visible_line_id(line_id: str) -> str:
            idx = local_line_order_index.get(line_id)
            if idx is None or idx <= 0:
                return ""
            return local_ordered_line_ids[idx - 1]
        def trusted_recovered_group_after(group_id: int) -> tuple[str, dict]:
            if group_id in trusted_group_after_cache:
                return trusted_group_after_cache[group_id]
            group_ids = group_option_ids_by_group.get(group_id, [])
            result: tuple[str, dict] = ("", {})
            if len(group_ids) >= 2:
                candidate = sibling_scene_template_branch_for_group(
                    group_ids,
                    fallback_group_line_ids.get(group_id, ""),
                    group_id,
                )
                candidate_after = str(candidate.get("after") or "")
                if candidate_after in valid_line_ids:
                    result = (candidate_after, candidate)
            elif len(group_ids) == 1:
                group_pos = sorted_group_index.get(group_id)
                if group_pos is not None:
                    for later_group_id in sorted_group_ids[group_pos + 1:]:
                        later_after, later_risk = trusted_recovered_group_after(later_group_id)
                        if later_after not in valid_line_ids:
                            continue
                        inferred_after = previous_visible_line_id(later_after)
                        if inferred_after in valid_line_ids:
                            result = (
                                inferred_after,
                                {
                                    "code": "siblingSceneTextBranches",
                                    "reason": "singleOptionSpanBeforeRecoveredAnchor",
                                    "detail": (
                                        "A later option group is recovered from sibling SceneGraph "
                                        "branch evidence; this single-option group occupies the "
                                        "contiguous line span immediately before that recovered anchor."
                                    ),
                                    "after": inferred_after,
                                    "nextRecoveredGroup": later_group_id,
                                    "nextRecoveredAfter": later_after,
                                    "nextRecoveredReason": later_risk.get("reason") or "",
                                    "source": later_risk.get("source") or "siblingSceneGraphText",
                                    "sources": later_risk.get("sources") or [],
                                },
                            )
                        break
            trusted_group_after_cache[group_id] = result
            return result
        def single_option_span_before_recovered_anchor(
            group_id: int,
            group_opt_ids: list[str],
            after_id: str,
        ) -> dict:
            if len(group_opt_ids) != 1 or after_id not in valid_line_ids:
                return {}
            group_pos = sorted_group_index.get(group_id)
            if group_pos is None:
                return {}
            next_after = ""
            next_group_id = 0
            next_risk: dict = {}
            for later_group_id in sorted_group_ids[group_pos + 1:]:
                candidate_after, candidate_risk = trusted_recovered_group_after(later_group_id)
                if candidate_after in valid_line_ids:
                    next_after = candidate_after
                    next_group_id = later_group_id
                    next_risk = candidate_risk
                    break
            if next_after not in valid_line_ids:
                return {}
            start_index = local_line_order_index.get(after_id)
            end_index = local_line_order_index.get(next_after)
            if start_index is None or end_index is None or end_index <= start_index:
                return {}
            candidate_lines = [
                line_id
                for line_id in local_ordered_line_ids[start_index + 1:end_index + 1]
                if line_id not in recovered_single_option_line_ids
            ]
            if not candidate_lines:
                return {}
            inferred_after = previous_visible_line_id(candidate_lines[0])
            if inferred_after not in valid_line_ids:
                return {}
            return {
                "code": "siblingSceneTextBranches",
                "reason": "singleOptionSpanBeforeRecoveredAnchor",
                "detail": (
                    "A later option group is recovered from sibling SceneGraph "
                    "branch evidence; this single-option group consumes the "
                    "remaining contiguous line span before that recovered anchor."
                ),
                "after": inferred_after,
                "previousAfter": after_id,
                "optionIds": group_opt_ids,
                "branchLineIdsByOption": {group_opt_ids[0]: candidate_lines},
                "nextRecoveredGroup": next_group_id,
                "nextRecoveredAfter": next_after,
                "nextRecoveredReason": next_risk.get("reason") or "",
                "source": next_risk.get("source") or "siblingSceneGraphText",
                "sources": next_risk.get("sources") or [],
            }
        for order, g in enumerate(sorted(groups_map), start=1):
            opts = sorted(groups_map[g], key=lambda o: o["i"])
            group_opt_ids = group_option_ids_by_group.get(g, [])
            placement_override = DIALOG_OPTION_GROUP_POSITION_OVERRIDES.get((conv_key or "", g), "")
            manual_override = _manual_option_group_override(conv_key or "", g)
            cinematic_after_candidate = cinematic_after_by_group.get(g, "")
            cinematic_group_sources = cinematic_sources_by_group.get(g, [])
            text_alias_after_candidate = text_alias_after_by_group.get(g, "")
            text_alias_group_sources = text_alias_sources_by_group.get(g, [])
            text_alias_foreign_option_ids = text_alias_foreign_option_ids_by_group.get(g, [])
            group = {"g": g, "options": opts}
            after = None
            tree_after_option_ids: list[str] = []
            scene_link_after_option_ids: list[str] = []
            timeline_after_option_ids: list[str] = []
            cinematic_after_option_ids: list[str] = []
            text_alias_after_option_ids: list[str] = []
            for opt in opts:
                opt_id = opt.get("id") or ""
                tree_after_candidate = tree_after.get(opt_id) or ""
                scene_link_after_candidate = scene_link_after.get(opt_id) or ""
                timeline_after_candidate = timeline_after.get(opt_id) or ""
                if timeline_after_candidate and timeline_after_candidate not in valid_line_ids:
                    timeline_after_candidate = _nearest_visible_timeline_anchor(
                        timeline_after_candidate,
                        timeline_after_line_ids.get(opt_id) or [],
                        valid_line_ids,
                    )
                if tree_after_candidate and tree_after_candidate in valid_line_ids:
                    tree_after_option_ids.append(opt_id)
                if scene_link_after_candidate and scene_link_after_candidate in valid_line_ids:
                    scene_link_after_option_ids.append(opt_id)
                if timeline_after_candidate and timeline_after_candidate in valid_line_ids:
                    timeline_after_option_ids.append(opt_id)
                if cinematic_after_candidate and cinematic_after_candidate in valid_line_ids:
                    cinematic_after_option_ids.append(opt_id)
                if text_alias_after_candidate and text_alias_after_candidate in valid_line_ids:
                    text_alias_after_option_ids.append(opt_id)
                authored_after_candidates = [
                    tree_after_candidate,
                    scene_link_after_candidate,
                    timeline_after_candidate,
                ]
                after = next(
                    (
                        candidate_after
                        for candidate_after in authored_after_candidates
                        if candidate_after and candidate_after in valid_line_ids
                    ),
                    None,
                )
                if after:
                    break
            if (
                after == cinematic_after_candidate
                and cinematic_after_candidate
                and cinematic_after_candidate in valid_line_ids
            ):
                cinematic_after_option_ids = list(group_opt_ids)
            if (
                after == text_alias_after_candidate
                and text_alias_after_candidate
                and text_alias_after_candidate in valid_line_ids
            ):
                text_alias_after_option_ids = list(group_opt_ids)
            after_is_authored = bool(after)
            for opt in opts:
                opt_id = opt.get("id") or ""
                branch_lines = [
                    lid for lid in (tree_branches.get(opt_id) or [])
                    if lid in valid_line_ids
                ]
                if branch_lines:
                    opt["branchLines"] = expand_transparent_single_option_branch(branch_lines)
            pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in tree_pre]
            timeline_pre_option_ids = [opt_id for opt_id in group_opt_ids if opt_id in timeline_pre]
            text_alias_pre_option_ids = list(group_opt_ids) if g in text_alias_pre_by_group else []
            authored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id in authored_option_ids
            ]
            unauthored_group_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id and opt_id not in authored_option_ids
            ]
            direct_pre_option_ids = [
                opt_id for opt_id in group_opt_ids if opt_id in tree_pre or opt_id in timeline_pre
            ]
            group_is_authored_pre = bool(group_opt_ids) and all(
                opt_id in tree_pre or opt_id in timeline_pre
                for opt_id in group_opt_ids
            )
            used_group_fallback = False
            used_group_keyed = False
            group_status = "unanchored"
            fallback_anchor_id = ""
            inferred_anchor_mode = ""
            sibling_anchor_record: dict | None = None
            if after_is_authored:
                authored_group_count += 1
                group_status = "authoredAfter"
            elif group_is_authored_pre:
                group["position"] = "pre"
                pre_group_count += 1
                group_status = "authoredPre"
            elif placement_override == "pre" and direct_pre_option_ids:
                group["position"] = "pre"
                pre_group_count += 1
                group_status = "correctedPre"
            elif order - 1 < len(fallback_after_ids):
                fallback_anchor_id = fallback_after_ids[order - 1]
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "sparseGap"
            elif (
                order - 1 < len(sibling_position_anchors)
                and sibling_position_anchors[order - 1].get("afterLineId") in valid_line_ids
            ):
                sibling_anchor_record = sibling_position_anchors[order - 1]
                fallback_anchor_id = sibling_anchor_record["afterLineId"]
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "siblingTimelinePosition"
            elif g in fallback_group_line_ids:
                fallback_anchor_id = fallback_group_line_ids[g]
                used_group_keyed = True
                keyed_group_count += 1
                group_status = "keyedAfter"
                inferred_anchor_mode = "lineNumber"
            elif last_line_fallback_id:
                fallback_anchor_id = last_line_fallback_id
                used_group_fallback = True
                fallback_group_count += 1
                fallback_group_labels.append(f"g{g}")
                group_status = "fallbackAfter"
                inferred_anchor_mode = "lastLine"
            else:
                unanchored_group_count += 1
            if after_is_authored and after:
                group["after"] = after
            elif used_group_keyed and fallback_anchor_id:
                group["after"] = fallback_anchor_id
            elif used_group_fallback and fallback_anchor_id:
                group["after"] = fallback_anchor_id
            layout_override = (
                manual_override.get("layout")
                if isinstance(manual_override.get("layout"), dict)
                else {}
            )
            manual_layout_applied = False
            if layout_override:
                override_after = str(layout_override.get("after") or "").strip()
                override_position = str(layout_override.get("position") or "").strip()
                can_apply_layout_override = (
                    (after_is_authored or group_status in {"fallbackAfter", "keyedAfter", "unanchored"})
                    and (
                        override_position == "pre"
                        or (override_after and override_after in valid_line_ids)
                    )
                )
                if can_apply_layout_override:
                    if override_position == "pre":
                        group.pop("after", None)
                        group["position"] = "pre"
                    else:
                        group.pop("position", None)
                        group["after"] = override_after
                        fallback_anchor_id = override_after
                    manual_layout_applied = True
                    group["manualOverride"] = {
                        "kind": "optionLayout",
                        "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                        "note": str(manual_override.get("note") or layout_override.get("note") or ""),
                    }
            timeline_route_branch = timeline_route_branch_for_group(group_opt_ids, group.get("after") or "")
            route_branch_lines_by_option = timeline_route_branch.get("branchLineIdsByOption") or {}
            sibling_text_branch = {}
            if timeline_route_branch.get("continuationOptionIds"):
                group["continuationOptionIds"] = timeline_route_branch["continuationOptionIds"]
            for opt in opts:
                opt_id = opt.get("id") or ""
                if opt.get("branchLines"):
                    continue
                route_branch_lines = [
                    line_id
                    for line_id in (route_branch_lines_by_option.get(opt_id) or [])
                    if line_id in valid_line_ids
                ]
                if route_branch_lines:
                    opt["branchLines"] = route_branch_lines
            if not any(opt.get("branchLines") for opt in opts):
                sibling_text_branch = sibling_scene_text_branch_for_group(
                    group_opt_ids,
                    group.get("after") or "",
                    sibling_anchor_record
                    if not manual_layout_applied and inferred_anchor_mode == "siblingTimelinePosition"
                    else None,
                    g,
                )
                if not sibling_text_branch:
                    sibling_text_branch = sibling_scene_template_branch_for_group(
                        group_opt_ids,
                        group.get("after") or "",
                        g,
                    )
                if not sibling_text_branch:
                    sibling_text_branch = single_option_span_before_recovered_anchor(
                        g,
                        group_opt_ids,
                        group.get("after") or "",
                    )
                sibling_branch_lines_by_option = sibling_text_branch.get("branchLineIdsByOption") or {}
                sibling_after = str(sibling_text_branch.get("after") or "")
                if sibling_after in valid_line_ids:
                    group["after"] = sibling_after
                    fallback_anchor_id = sibling_after
                for opt in opts:
                    opt_id = opt.get("id") or ""
                    branch_lines = [
                        line_id
                        for line_id in (sibling_branch_lines_by_option.get(opt_id) or [])
                        if line_id in valid_line_ids
                    ]
                    if branch_lines:
                        opt["branchLines"] = branch_lines
                        if sibling_text_branch.get("reason") == "singleOptionSpanBeforeRecoveredAnchor":
                            recovered_single_option_line_ids.update(branch_lines)
            if placement_override == "pre":
                corrected_opts_without_branch = [
                    opt
                    for opt in opts
                    if opt.get("id") in CORRECTED_DIALOG_OPTION_IDS and not opt.get("branchLines")
                ]
                if len(corrected_opts_without_branch) == 1:
                    covered_line_ids = {
                        line_id
                        for opt in opts
                        for line_id in (opt.get("branchLines") or [])
                        if line_id in valid_line_ids
                    }
                    remaining_line_ids = [
                        line_id
                        for _idx, line_id in line_idxs
                        if line_id in valid_line_ids and line_id not in covered_line_ids
                    ]
                    if remaining_line_ids:
                        corrected_opt = corrected_opts_without_branch[0]
                        corrected_opt["branchLines"] = remaining_line_ids
                        corrected_opt.setdefault("_debug", {})["branchLineCorrection"] = {
                            "mode": "remainingLinesForCorrectedPreGroup",
                            "reason": "The corrected pre-scene option uses the only line span not covered by authored DialogTree branches.",
                            "lineIds": remaining_line_ids,
                        }
            branch_convergence_risk = normalize_group_branch_convergence(group, opts, group_opt_ids)
            following_line_risk = (
                timeline_route_branch
                or sibling_text_branch
                or branch_convergence_risk
                or following_line_risk_for_group(group_opt_ids, group.get("after") or "")
            )
            original_following_line_risk = dict(following_line_risk) if following_line_risk else {}
            response_override = (
                manual_override.get("responses")
                if isinstance(manual_override.get("responses"), dict)
                else {}
            )
            manual_response_applied = False
            if response_override:
                option_set = {opt_id for opt_id in group_opt_ids if opt_id}
                branch_line_ids_by_option: dict[str, list[str]] = {}
                for raw_opt_id, raw_response in response_override.items():
                    opt_id = str(raw_opt_id or "")
                    if opt_id not in option_set or not isinstance(raw_response, dict):
                        continue
                    raw_lines = raw_response.get("branchLines")
                    if raw_lines is None:
                        raw_lines = raw_response.get("lineIds")
                    if raw_lines is None:
                        raw_lines = [raw_response.get("lineId")]
                    if not isinstance(raw_lines, list):
                        raw_lines = [raw_lines]
                    line_ids = [
                        str(line_id)
                        for line_id in raw_lines
                        if str(line_id or "") in valid_line_ids
                    ]
                    if line_ids:
                        branch_line_ids_by_option[opt_id] = _unique_preserve(line_ids)
                if branch_line_ids_by_option:
                    override_detail = (
                        "Manual WebUI-only override supplies option response "
                        "line mapping for this group."
                    )
                    if following_line_risk.get("code") == "inferredFollowingLines":
                        override_detail = (
                            "Manual WebUI-only override supplies option response "
                            "line mapping for a group that otherwise used inferred "
                            "Timeline-order candidates."
                        )
                    following_line_risk = {
                        **following_line_risk,
                        "code": "manualOptionResponseOverride",
                        "reason": "manualOverride",
                        "detail": override_detail,
                        "branchLineIdsByOption": branch_line_ids_by_option,
                        "candidateLineIdsByOption": branch_line_ids_by_option,
                        "manualOverride": {
                            "kind": "optionResponse",
                            "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                            "note": str(manual_override.get("note") or ""),
                        },
                    }
                    if original_following_line_risk:
                        following_line_risk["overriddenRisk"] = original_following_line_risk
                    for opt in opts:
                        opt_id = opt.get("id") or ""
                        if opt_id in branch_line_ids_by_option:
                            opt["branchLines"] = branch_line_ids_by_option[opt_id]
                    manual_response_applied = True
            if following_line_risk.get("code") == "siblingSceneTextBranches":
                if used_group_fallback:
                    used_group_fallback = False
                    if fallback_group_count > 0:
                        fallback_group_count -= 1
                    fallback_group_labels = [
                        label for label in fallback_group_labels if label != f"g{g}"
                    ]
                if used_group_keyed:
                    used_group_keyed = False
                    if keyed_group_count > 0:
                        keyed_group_count -= 1
                group_status = "siblingSceneText"
                sibling_text_group_count += 1
            if following_line_risk:
                group["optionBranchRisk"] = following_line_risk
                if following_line_risk.get("code") == "inferredFollowingLines":
                    strong_raw_index_mapping = (
                        following_line_risk.get("candidateMapping") == "trunkClipOptionIndex"
                        and bool(following_line_risk.get("branchLineIdsByOption"))
                    )
                    if not strong_raw_index_mapping:
                        option_response_risks.append({
                            "group": g,
                            **following_line_risk,
                        })
                    tag_code = "rawOptionIndexMatchedLine" if strong_raw_index_mapping else "inferredFollowingLine"
                    for opt, line_id in zip(opts, option_risk_line_ids(following_line_risk, len(opts))):
                        tag = {
                            "code": tag_code,
                            "lineId": line_id,
                            "reason": following_line_risk["reason"],
                            "branchRiskCode": following_line_risk.get("code") or "",
                            "source": following_line_risk.get("source") or "",
                        }
                        if strong_raw_index_mapping:
                            tag["candidateMapping"] = following_line_risk.get("candidateMapping") or ""
                        opt.setdefault("riskTags", []).append(tag)
                elif following_line_risk.get("code") == "manualOptionResponseOverride":
                    manual_option_response_overrides.append({
                        "group": g,
                        **following_line_risk,
                    })
                    if original_following_line_risk.get("code") == "inferredFollowingLines":
                        strong_raw_index_mapping = (
                            original_following_line_risk.get("candidateMapping") == "trunkClipOptionIndex"
                            and bool(original_following_line_risk.get("branchLineIdsByOption"))
                        )
                        if not strong_raw_index_mapping:
                            option_response_risks.append({
                                "group": g,
                                **original_following_line_risk,
                            })
                        tag_code = "rawOptionIndexMatchedLine" if strong_raw_index_mapping else "inferredFollowingLine"
                        for opt, line_id in zip(opts, option_risk_line_ids(original_following_line_risk, len(opts))):
                            tag = {
                                "code": tag_code,
                                "lineId": line_id,
                                "reason": original_following_line_risk["reason"],
                                "branchRiskCode": original_following_line_risk.get("code") or "",
                                "source": original_following_line_risk.get("source") or "",
                            }
                            if strong_raw_index_mapping:
                                tag["candidateMapping"] = original_following_line_risk.get("candidateMapping") or ""
                            opt.setdefault("riskTags", []).append(tag)
                    for opt in opts:
                        opt_id = opt.get("id") or ""
                        line_ids = (following_line_risk.get("branchLineIdsByOption") or {}).get(opt_id) or []
                        if not line_ids:
                            continue
                        opt.setdefault("riskTags", []).append({
                            "code": "manualOptionResponseOverride",
                            "lineId": line_ids[0],
                            "reason": "manualOverride",
                            "branchRiskCode": following_line_risk.get("code") or "",
                            "source": repo_rel(_MANUAL_OPTION_OVERRIDES_PATH),
                        })
            if sibling_anchor_record and sibling_anchor_record.get("siblingScenes"):
                group["branchHint"] = {
                    "scenes": sibling_anchor_record["siblingScenes"],
                    "timeline": sibling_anchor_record.get("timeline") or "",
                }
            group_detail = {
                "group": g,
                "status": group_status,
                "after": after or fallback_anchor_id or "",
                "position": group.get("position") or "",
                "inferredAnchorMode": inferred_anchor_mode,
                "optionIds": group_opt_ids,
                "authoredOptionIds": authored_group_option_ids,
                "unauthoredOptionIds": unauthored_group_option_ids,
                "treeAfterOptionIds": tree_after_option_ids,
                "sceneLinkAfterOptionIds": scene_link_after_option_ids,
                "timelineAfterOptionIds": timeline_after_option_ids,
                "cinematicAfterOptionIds": cinematic_after_option_ids,
                "textAliasAfterOptionIds": text_alias_after_option_ids,
                "textAliasPreOptionIds": text_alias_pre_option_ids,
                "textAliasSourceOptionIds": text_alias_foreign_option_ids,
                "preOptionIds": pre_option_ids,
                "timelinePreOptionIds": timeline_pre_option_ids,
                "fallbackAnchorId": fallback_anchor_id,
                "positionOverride": placement_override,
                "cinematicSources": cinematic_group_sources,
                "textAliasSources": text_alias_group_sources,
            }
            group_manual_override = group.get("manualOverride") or (
                following_line_risk.get("manualOverride") if manual_response_applied else {}
            )
            if group_manual_override:
                group_detail["manualOverride"] = group_manual_override
            if manual_layout_applied:
                group_detail["manualLayoutOverride"] = True
            if manual_response_applied:
                group_detail["manualResponseOverride"] = True
            group_details.append(group_detail)
            out.append(group)
        has_meaningful_option_text = any(
            str(opt.get("text") or "").strip()
            for group in out
            for opt in (group.get("options") or [])
            if isinstance(opt, dict)
        )
        has_layout_warning_groups = (
            keyed_group_count > 0
            or fallback_group_count > 0
            or unanchored_group_count > 0
        )
        warnings: list[dict] = []
        if has_meaningful_option_text and has_layout_warning_groups:
            total_groups = len(out)
            if not authored_option_ids:
                reason_short = "noTreeReference"
                reason_text = (
                    "no AnimeStudio tree references any option for this scene; "
                    "positions are recovered from original DialogOption/DialogText key "
                    "structure where possible, with any line-gap or end-of-scene "
                    "fallback identified separately"
                )
            elif authored_group_count + pre_group_count == 0:
                reason_short = "noAuthoredGroupAnchor"
                reason_text = (
                    "tree data exists for this scene's options but no group "
                    "received an authored anchor; fallback candidates are "
                    "diagnostic only"
                )
            else:
                reason_short = "partialAuthoredCoverage"
                reason_text = (
                    f"{authored_group_count + pre_group_count} of {total_groups} option "
                    f"groups anchored from tree data; {fallback_group_count} only have "
                    f"diagnostic fallback candidates ({', '.join(fallback_group_labels)})"
                )
            warnings.append({
                "code": "inferredOptionLayout",
                "reason": reason_short,
                "detail": reason_text,
                "groupBreakdown": {
                    "total": total_groups,
                    "authoredAfter": authored_group_count,
                    "authoredPre": pre_group_count,
                    "keyedAfter": keyed_group_count,
                    "siblingSceneText": sibling_text_group_count,
                    "fallbackAfter": fallback_group_count,
                    "unanchored": unanchored_group_count,
                },
                "fallbackGroups": fallback_group_labels,
                "fallbackAnchorIds": fallback_after_ids,
                "groupDetails": group_details,
                "treeSources": tree_meta.get("sources") or [],
                "sceneLinkSources": sorted(scene_link_sources),
                "timelineSources": sorted(timeline_sources),
                "cinematicSources": sorted(cinematic_sources),
                "textAliasSources": sorted(text_alias_sources),
                "authoredOptionCount": len(authored_option_ids),
            })
        if option_response_risks:
            warnings.append({
                "code": "inferredOptionResponse",
                "reason": "optionTargetsMissing",
                "detail": (
                    "one or more option responses are inferred from Timeline order "
                    "because the option metadata does not name explicit target trunk ids"
                ),
                "groups": option_response_risks,
                "optionIds": _unique_preserve([
                    option_id
                    for risk in option_response_risks
                    for option_id in (risk.get("optionIds") or [])
                    if option_id
                ]),
                "lineIds": _unique_preserve([
                    line_id
                    for risk in option_response_risks
                    for line_id in all_option_response_risk_line_ids(risk)
                    if line_id
                ]),
            })
        if manual_option_response_overrides:
            warnings.append({
                "code": "manualOptionResponseOverride",
                "reason": "manualOverride",
                "detail": (
                    "manual WebUI-only overrides supply option response line "
                    "mappings for these groups"
                ),
                "groups": manual_option_response_overrides,
                "optionIds": _unique_preserve([
                    option_id
                    for risk in manual_option_response_overrides
                    for option_id in (risk.get("optionIds") or [])
                    if option_id
                ]),
                "lineIds": _unique_preserve([
                    line_id
                    for risk in manual_option_response_overrides
                    for line_id in all_option_response_risk_line_ids(risk)
                    if line_id
                ]),
            })
        return {
            "groups": out,
            "warnings": warnings,
        }
    def attach_runtime_registry_debug(payload: dict) -> None:
        debug = payload.setdefault("_debug", {})
        if not isinstance(debug, dict):
            debug = {}
            payload["_debug"] = debug
        block = shared_build_runtime_registry_debug(
            payload, dialog_id_registry=dialog_id_registry
        )
        if block is None:
            debug.pop("runtimeRegistry", None)
            return
        debug["runtimeRegistry"] = block
    def attach_scene_order_warning(payload: dict) -> None:
        analysis = shared_analyze_scene_order_disorder(
            payload, dialog_id_registry=dialog_id_registry
        )
        scene_order_analysis_by_payload_id[id(payload)] = analysis
        warning = analysis.get("warning")
        if warning is None:
            return
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "sceneOrderDisorder"
        ]
        payload["warnings"] = [warning, *existing_warnings]

    def build_duplicate_timestamp_warning(payload: dict) -> dict | None:
        buckets: dict[tuple[str, str], list[dict]] = defaultdict(list)
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            ts = line.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
            timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
            buckets[(timeline, format_webui_timeline_seconds(ts))].append(line)
        groups: list[dict] = []
        for (timeline, label), lines_for_ts in sorted(
            buckets.items(),
            key=lambda item: min(float(line.get("ts") or 0.0) for line in item[1]),
        ):
            if len(lines_for_ts) < 2:
                continue
            group = {
                "timestamp": label,
                "lineIds": [str(line.get("id") or "") for line in lines_for_ts if line.get("id")],
                "lines": [
                    {
                        "id": str(line.get("id") or ""),
                        "actor": str(line.get("actor") or line.get("aid") or ""),
                        "ts": line.get("ts"),
                        "dur": line.get("dur"),
                    }
                    for line in lines_for_ts
                    if line.get("id")
                ],
            }
            if timeline:
                group["timeline"] = timeline
            groups.append(group)
        if not groups:
            return None
        line_ids: list[str] = []
        for group in groups:
            for line_id in group["lineIds"]:
                if line_id not in line_ids:
                    line_ids.append(line_id)
        return {
            "code": "duplicateTimestamps",
            "reason": "duplicateDisplayTimestamp",
            "detail": "two or more lines share the same WebUI timeline timestamp label within one timeline segment",
            "groups": groups,
            "lineIds": line_ids,
        }
    def attach_duplicate_timestamp_warning(payload: dict) -> None:
        warning = build_duplicate_timestamp_warning(payload)
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "duplicateTimestamps"
        ]
        if warning is None:
            if existing_warnings:
                payload["warnings"] = existing_warnings
            else:
                payload.pop("warnings", None)
            return
        payload["warnings"] = [*existing_warnings, warning]

    def build_timeline_timestamp_regression_warning(payload: dict) -> dict | None:
        timed_lines: list[dict] = []
        for idx, line in enumerate(payload.get("lines") or []):
            if not isinstance(line, dict):
                continue
            ts = line.get("ts")
            if not isinstance(ts, (int, float)):
                continue
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            timing_debug = debug.get("timelineTiming") if isinstance(debug, dict) else {}
            timeline = str(timing_debug.get("timeline") or "") if isinstance(timing_debug, dict) else ""
            timed_lines.append({
                "index": idx,
                "id": str(line.get("id") or ""),
                "ts": float(ts),
                "timeline": timeline,
            })
        regressions: list[dict] = []
        for prev, cur in zip(timed_lines, timed_lines[1:]):
            if cur["ts"] + 1e-6 >= prev["ts"]:
                continue
            regressions.append({
                "prevLineId": prev["id"],
                "prevTimestamp": format_webui_timeline_seconds(prev["ts"]),
                "prevTimeline": prev["timeline"],
                "lineId": cur["id"],
                "timestamp": format_webui_timeline_seconds(cur["ts"]),
                "timeline": cur["timeline"],
            })
        if not regressions:
            return None
        line_ids: list[str] = []
        for row in regressions:
            for line_id in (row.get("prevLineId"), row.get("lineId")):
                if line_id and line_id not in line_ids:
                    line_ids.append(line_id)
        timelines = sorted({row["timeline"] for row in timed_lines if row.get("timeline")})
        return {
            "code": "timelineTimestampRegression",
            "reason": "timelineTimestampsMoveBackward",
            "detail": "recovered Timeline timestamps move backward in rendered line order; secondary timelines may be local stitch evidence rather than absolute scene time",
            "lineIds": line_ids,
            "regressions": regressions,
            "timelines": timelines,
        }

    def attach_timeline_timestamp_regression_warning(payload: dict) -> None:
        warning = build_timeline_timestamp_regression_warning(payload)
        existing_warnings = [
            existing
            for existing in (payload.get("warnings") or [])
            if isinstance(existing, dict) and existing.get("code") != "timelineTimestampRegression"
        ]
        if warning is None:
            if existing_warnings:
                payload["warnings"] = existing_warnings
            else:
                payload.pop("warnings", None)
            return
        payload["warnings"] = [*existing_warnings, warning]
    def attach_timeline_action_evidence(
        payload: dict,
        evidence_key: str,
        original_line_ids: list[str],
        current_line_ids: list[str],
    ) -> None:
        action_debug = build_conversation_action_debug(
            evidence_key,
            original_line_ids,
            current_line_ids,
        )
        if not action_debug:
            return
        debug = payload.setdefault("_debug", {})
        if not isinstance(debug, dict):
            debug = {}
            payload["_debug"] = debug
        debug["timelineActions"] = action_debug
        line_actions_by_id = {
            str(row.get("lineId") or ""): row
            for row in (action_debug.get("lineActions") or [])
            if isinstance(row, dict) and row.get("lineId")
        }
        if not line_actions_by_id:
            return
        for line in payload.get("lines") or []:
            if not isinstance(line, dict):
                continue
            line_id = str(line.get("id") or "")
            line_actions = line_actions_by_id.get(line_id)
            if not line_actions:
                continue
            line.setdefault("_debug", {})["timelineActions"] = line_actions
    def extras_text(out_key: str) -> str:
        """Concatenate all extras text for an out_key so the index entry's
        search haystack covers summaries / dialog options."""
        parts: list[str] = []
        if out_key in summary_by_key:
            parts.extend(s["text"] for s in summary_by_key[out_key] if s.get("text"))
        if out_key in options_by_key:
            for opts in options_by_key[out_key].values():
                for o in opts:
                    for id_field in ("id", "optionId"):
                        if o.get(id_field):
                            parts.append(str(o[id_field]))
                    if o["text"]:
                        parts.append(o["text"])
        return " ".join(parts)

    def attach_submenu_targets(links: list[dict]) -> None:
        for link in links or []:
            for opt in link.get("options") or []:
                if not isinstance(opt, dict):
                    continue
                submenu_scene_keys = [
                    str(scene_key)
                    for scene_key in (opt.get("submenuSceneKeys") or [])
                    if str(scene_key).strip()
                ]
                if not submenu_scene_keys:
                    continue
                debug = opt.get("_debug") if isinstance(opt.get("_debug"), dict) else {}
                return_option_ids = [
                    str(option_id)
                    for option_id in (debug.get("returnOptionIds") or [])
                    if str(option_id).strip()
                ]
                targets: list[dict] = []
                seen_targets: set[tuple[str, str]] = set()
                for idx, option_id in enumerate(return_option_ids):
                    scene_key = _dialog_tree_option_prefix(option_id) or ""
                    if not scene_key and idx < len(submenu_scene_keys):
                        scene_key = submenu_scene_keys[idx]
                    if not scene_key:
                        continue
                    key = (scene_key, option_id)
                    if key in seen_targets:
                        continue
                    seen_targets.add(key)
                    target = {
                        "sceneKey": scene_key,
                        "optionId": option_id,
                    }
                    if text := dialog_option_text_by_id.get(option_id):
                        target["text"] = text
                    targets.append(target)
                for scene_key in submenu_scene_keys:
                    if any(target.get("sceneKey") == scene_key for target in targets):
                        continue
                    target = {"sceneKey": scene_key}
                    targets.append(target)
                if targets:
                    opt["submenuTargets"] = targets
    def clone_dialog_option_for_hub(option_id: str, hub_index: int, target_scene_key: str = "") -> dict | None:
        option_id = str(option_id or "").strip()
        if not option_id:
            return None
        base = dialog_option_payload_by_id.get(option_id)
        if base:
            option = copy.deepcopy(base)
        else:
            text, icon = dialog_option_signature_by_id.get(option_id, ("", ""))
            option = {
                "id": option_id,
                "i": hub_index,
                "text": text,
                "icon": icon or "",
                "_debug": {
                    "table": "DialogOptionTable",
                    "rowId": option_id,
                    "source": {},
                    "hubOnly": True,
                },
            }
        option["i"] = hub_index
        if target_scene_key:
            option["targetSceneKey"] = target_scene_key
            option.setdefault("_debug", {})["hubTargetSceneKey"] = target_scene_key
        return option

    def source_hub_option_groups(conv_key: str, valid_line_ids: set[str]) -> tuple[list[dict], list[dict]]:
        source = _load_dialog_tree_source(conv_key)
        if not source:
            return [], []
        raw_links = [
            link
            for link in (source.get("sceneLinks") or [])
            if isinstance(link, dict)
            and (link.get("sourceKey") or "") == conv_key
        ]
        if not raw_links:
            return [], []
        nodes_by_id = {
            str(node.get("id") or ""): node
            for node in ((source.get("lineGraph") or {}).get("nodes") or [])
            if isinstance(node, dict) and node.get("id") is not None
        }
        by_source_node: dict[str, list[dict]] = defaultdict(list)
        for link in raw_links:
            link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
            source_node_id = str(link_debug.get("sourceOptionNodeId") or "").strip()
            group_scene_keys = [
                str(scene_key)
                for scene_key in (link_debug.get("groupSceneKeys") or [])
                if str(scene_key or "").strip()
            ]
            if source_node_id and conv_key in group_scene_keys and len(set(group_scene_keys)) > 1:
                by_source_node[source_node_id].append(link)
        hub_groups: list[dict] = []
        hub_scene_links: list[dict] = []
        for source_node_id, links in sorted(by_source_node.items()):
            local_after = next(
                (
                    str(link.get("after") or "")
                    for link in links
                    if (link.get("sceneKey") or "") == conv_key
                    and str(link.get("after") or "") in valid_line_ids
                ),
                "",
            )
            if not local_after:
                continue
            node_option_ids = [
                str(option_id)
                for option_id in (nodes_by_id.get(source_node_id, {}).get("optionIds") or [])
                if str(option_id or "").strip()
            ]
            if len(node_option_ids) < 2:
                continue
            raw_option_by_id: dict[str, dict] = {}
            target_scene_by_option: dict[str, str] = {}
            group_scene_keys: list[str] = []
            target_scene_keys: list[str] = []
            for link in links:
                link_debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
                group_scene_keys.extend(
                    str(scene_key)
                    for scene_key in (link_debug.get("groupSceneKeys") or [])
                    if str(scene_key or "").strip()
                )
                target_scene_keys.extend(
                    str(scene_key)
                    for scene_key in (link_debug.get("targetSceneKeys") or [])
                    if str(scene_key or "").strip()
                )
                scene_key = str(link.get("sceneKey") or "")
                for raw_option in link.get("options") or []:
                    if not isinstance(raw_option, dict):
                        continue
                    option_id = str(raw_option.get("optionId") or "").strip()
                    if not option_id:
                        continue
                    raw_option_by_id.setdefault(option_id, raw_option)
                    if scene_key:
                        target_scene_by_option.setdefault(option_id, scene_key)
            ordered_option_ids = [
                option_id
                for option_id in node_option_ids
                if option_id in raw_option_by_id or option_id in dialog_option_payload_by_id
            ]
            if len(ordered_option_ids) < 2:
                continue
            group_ids = [
                parts[1]
                for option_id in ordered_option_ids
                if (parts := _option_id_group_parts(option_id))
            ]
            group_id = group_ids[0] if group_ids else 1
            options = [
                option
                for option in (
                    clone_dialog_option_for_hub(
                        option_id,
                        hub_index,
                        target_scene_by_option.get(option_id, ""),
                    )
                    for hub_index, option_id in enumerate(ordered_option_ids, start=1)
                )
                if option is not None
            ]
            if len(options) < 2:
                continue
            hub_groups.append({
                "g": group_id,
                "after": local_after,
                "options": options,
                "hubMenu": {
                    "sourceKey": conv_key,
                    "sourceOptionNodeId": source_node_id,
                    "sourceFile": source.get("file") or "",
                    "sceneKeys": _unique_preserve(group_scene_keys),
                },
            })
            hub_scene_links.append({
                "sourceKey": conv_key,
                "file": source.get("file") or "",
                "after": local_after,
                "options": [
                    scene_link_option_payload(raw_option_by_id[option_id])
                    for option_id in ordered_option_ids
                    if option_id in raw_option_by_id
                ],
                "sceneSpan": True,
                "sourceSceneKeys": source.get("sourceSceneKeys") or sorted(set(group_scene_keys)),
                "_debug": {
                    "source": {
                        "targetKey": conv_key,
                        "sourceKey": conv_key,
                        "file": source.get("file") or "",
                    },
                    "link": {
                        "sourceOptionNodeId": source_node_id,
                        "groupSceneKeys": _unique_preserve(group_scene_keys),
                        "targetSceneKeys": _unique_preserve(target_scene_keys),
                        "sourceHubMenu": True,
                    },
                },
            })
        return hub_groups, hub_scene_links
    def apply_source_hub_option_groups(payload: dict, scene_graph_links: list[dict]) -> list[dict]:
        def group_after_suffix(group: dict) -> int:
            match = re.search(r"_(\d+)$", str(group.get("after") or ""))
            return int(match.group(1)) if match else -1
        def link_source_node_id(link: dict) -> str:
            debug = link.get("_debug") if isinstance(link.get("_debug"), dict) else {}
            link_debug = debug.get("link") if isinstance(debug.get("link"), dict) else {}
            return str(link_debug.get("sourceOptionNodeId") or "")
        def link_option_ids(link: dict) -> set[str]:
            return {
                str(option.get("optionId") or "")
                for option in (link.get("options") or [])
                if isinstance(option, dict) and str(option.get("optionId") or "")
            }
        conv_key = str(payload.get("key") or "")
        valid_line_ids = {
            str(line.get("id") or "")
            for line in (payload.get("lines") or [])
            if isinstance(line, dict) and str(line.get("id") or "")
        }
        hub_groups, hub_links = source_hub_option_groups(conv_key, valid_line_ids)
        if not hub_groups:
            return scene_graph_links
        groups = [
            group
            for group in (payload.get("optionGroups") or [])
            if isinstance(group, dict)
        ]
        for hub_group in hub_groups:
            hub_g = hub_group.get("g")
            replaced = False
            for idx, existing_group in enumerate(groups):
                if existing_group.get("g") == hub_g and existing_group.get("after") == hub_group.get("after"):
                    groups[idx] = hub_group
                    replaced = True
                    break
            if not replaced:
                groups.append(hub_group)
        groups.sort(key=lambda group: (group_after_suffix(group), group.get("g") or 0))
        payload["optionGroups"] = groups
        for hub_link in hub_links:
            if hub_link.get("options"):
                hub_debug = hub_link.get("_debug") if isinstance(hub_link.get("_debug"), dict) else {}
                hub_link_debug = hub_debug.get("link") if isinstance(hub_debug.get("link"), dict) else {}
                hub_source_node_id = str(hub_link_debug.get("sourceOptionNodeId") or "")
                hub_after = str(hub_link.get("after") or "")
                hub_option_ids = link_option_ids(hub_link)
                scene_graph_links[:] = [
                    existing
                    for existing in scene_graph_links
                    if not (
                        str(existing.get("after") or "") == hub_after
                        and link_source_node_id(existing) == hub_source_node_id
                        and link_option_ids(existing).issubset(hub_option_ids)
                    )
                ]
                scene_graph_links.append(hub_link)
        return scene_graph_links

    def dialog_recovery_methods(payload: dict) -> list[str]:
        methods: list[str] = []
        def add(method: str) -> None:
            if method and method not in methods:
                methods.append(method)
        debug = payload.get("_debug") if isinstance(payload.get("_debug"), dict) else {}
        runtime_registry = (
            debug.get("runtimeRegistry")
            if isinstance(debug.get("runtimeRegistry"), dict)
            else {}
        )
        line_order = debug.get("lineOrder") if isinstance(debug.get("lineOrder"), dict) else {}
        line_order_mode = str(line_order.get("mode") or "")
        if line_order_mode == "lineIdSuffix":
            registry = debug.get("runtimeRegistry") if isinstance(debug.get("runtimeRegistry"), dict) else {}
            original_line_ids = line_order.get("originalLineIds") or []
            ordered_line_ids = line_order.get("orderedLineIds") or []
            if registry.get("registered") is True and _line_id_list_equal(original_line_ids, ordered_line_ids):
                add("lineOrder:runtimeRowIteration")
            elif registry.get("registered") is False:
                add("lineOrder:unregisteredScene")
            else:
                add("lineOrder:lineIdSuffix")
        elif line_order_mode:
            add(f"lineOrder:{line_order_mode}")
        elif len(payload.get("lines") or []) > 1:
            add("lineOrder:missing")
        option_groups = [
            group
            for group in (payload.get("optionGroups") or [])
            if isinstance(group, dict)
        ]
        warnings = [
            warning
            for warning in (payload.get("warnings") or [])
            if isinstance(warning, dict)
        ]
        layout_warning = next(
            (warning for warning in warnings if warning.get("code") == "inferredOptionLayout"),
            None,
        )
        if layout_warning:
            reason = str(layout_warning.get("reason") or "")
            group_details = [
                detail
                for detail in (layout_warning.get("groupDetails") or [])
                if isinstance(detail, dict) and not detail.get("manualLayoutOverride")
            ]
            modes = {
                str(detail.get("inferredAnchorMode") or "")
                for detail in group_details
            }
            statuses = {str(detail.get("status") or "") for detail in group_details}
            if runtime_registry.get("registered") is False:
                add("optionLayout:tableOnlyCutContent")
            else:
                if "lineNumber" in modes:
                    add("optionLayout:keyMatched")
                if "sparseGap" in modes:
                    add("optionLayout:sparseGap")
                if "siblingTimelinePosition" in modes:
                    add("optionLayout:siblingTimelinePosition")
                if "lastLine" in modes:
                    add("optionLayout:lastLine")
                if "unanchored" in statuses:
                    add("optionLayout:unanchored")
            if not group_details:
                if reason == "partialAuthoredCoverage":
                    add("optionLayout:partialAuthoredCoverage")
                elif reason == "noAuthoredGroupAnchor":
                    add("optionLayout:noAuthoredGroupAnchor")
                else:
                    add("optionLayout:fallback")
        elif option_groups:
            add("optionLayout:authored")
        if payload.get("sceneGraphLinks"):
            add("optionBranch:sceneGraph")
        if payload.get("graphFragments"):
            add("optionBranch:dialogTreeFragment")
        for group in option_groups:
            if group.get("continuationOptionIds"):
                add("optionBranch:continuationOption")
            if group.get("branchHint"):
                add("optionBranch:siblingSceneHint")
            risk = group.get("optionBranchRisk") if isinstance(group.get("optionBranchRisk"), dict) else {}
            if not risk:
                continue
            def add_option_branch_methods(branch_risk: dict) -> None:
                if branch_risk.get("code") == "timelineRouteBranches":
                    add("optionBranch:runtimeJump")
                elif branch_risk.get("code") == "siblingSceneTextBranches":
                    add("optionBranch:siblingSceneText")
                elif branch_risk.get("candidateMapping") == "trunkClipOptionIndex":
                    add("optionBranch:rawIndexMatched")
                elif branch_risk.get("code") == "inferredFollowingLines":
                    add("optionBranch:timelineAdjacent")
                elif branch_risk.get("code") == "manualOptionResponseOverride":
                    add("optionBranch:manualOverride")
                elif branch_risk.get("code") == "sharedTimelineContinuation":
                    add("optionBranch:commonContinuation")
                if branch_risk.get("commonContinuationLineId"):
                    add("optionBranch:commonContinuation")
                if branch_risk.get("continuationOptionIds"):
                    add("optionBranch:continuationOption")
            overridden_risk = (
                risk.get("overriddenRisk")
                if isinstance(risk.get("overriddenRisk"), dict)
                else {}
            )
            if overridden_risk:
                add_option_branch_methods(overridden_risk)
            add_option_branch_methods(risk)
        return methods
    print(
        f"Extras: summary={len(summary_by_key)} scenes ({summary_orphans} orphans), "
        f"options={len(options_by_key)} scenes ({option_orphans} orphans), "
        f"radioTargets={len(radio_targets_seen)} scenes, "
        f"radioStandalone={len(radio_rows)} conversations ({radio_orphans} orphans)"
    )
    index_entries: list[dict] = []
    story_env_entries_by_mission: dict[str, list[dict]] = defaultdict(list)
    scene_graph_links_by_key: dict[str, list[dict]] = {}
    # Emit dialog conversations
    print(f"Writing {len(groups)} dialog conversations...")
    for key, items in groups.items():
        items.sort(key=lambda x: x[0])
        _, mission, scene_str = key.split("__")
        scene = int(scene_str)
        type_, act = parse_mission(mission)
        lines = []
        actors: set[str] = set()
        for _line, dlg_id, e in items:
            actor_id = e.get("actorNameId") or ""
            actor = t(e.get("actorName", {}).get("id"))
            text = t(e.get("dialogText", {}).get("id"))
            hint = t(e.get("hint", {}).get("id"))
            audio = e.get("audioOverride") or ""
            emo = e.get("emotionType", 0)
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": dlg_id,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": audio,
                "emo": emo,
                "_debug": {
                    **source_ref(
                        "DialogTextTable",
                        dlg_id,
                        pick_fields(
                            e,
                            "actorNameId",
                            "actorName",
                            "dialogText",
                            "hint",
                            "audioOverride",
                            "emotionType",
                        ),
                    ),
                    "fields": {
                        "actor": text_trace("DialogTextTable", dlg_id, "actorName", e.get("actorName")),
                        "text": text_trace("DialogTextTable", dlg_id, "dialogText", e.get("dialogText")),
                        "hint": text_trace("DialogTextTable", dlg_id, "hint", e.get("hint")),
                    },
                },
            })
        out_key = f"dlg_{mission}_{scene}"
        original_line_ids = [line.get("id") or "" for line in lines]
        ordered_line_ids, line_order_debug = resolve_scene_line_order(
            out_key,
            original_line_ids,
        )
        if ordered_line_ids:
            line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
            lines = [
                line
                for _idx, line in sorted(
                    enumerate(lines),
                    key=lambda item: (
                        line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                        item[0],
                    ),
                )
            ]
        prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
        payload = {
            "key": out_key,
            "kind": "dlg",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        if line_order_debug:
            payload["_debug"]["lineOrder"] = line_order_debug
        # Attach Unity Timeline timing per line so the conv view can render a
        # 00:54-style gutter alongside each line. Only sets "ts" / "dur" when
        # the recovery JSON actually has a timestamp for the line.
        line_timings = collect_line_timings(out_key)
        if line_timings:
            for line in lines:
                timing = line_timings.get(line.get("id") or "")
                if not timing:
                    continue
                if isinstance(timing.get("start"), (int, float)):
                    line["ts"] = timing["start"]
                if isinstance(timing.get("duration"), (int, float)):
                    line["dur"] = timing["duration"]
                timing_debug = {
                    key: timing[key]
                    for key in ("timeline", "start", "duration")
                    if timing.get(key) not in (None, "")
                }
                if timing_debug:
                    line.setdefault("_debug", {})["timelineTiming"] = timing_debug
        # Cross-link with other dialog scenes that share this scene's Unity
        # Timeline. Surfaces cases like dlg_e2m6_11 + dlg_e2m6_19 where a single
        # cinematic recording is split into two DialogTextTable scenes.
        related = collect_related_scenes(out_key)
        if related:
            payload["relatedScenes"] = related
        if out_key in summary_by_key:
            payload["summary"] = summary_by_key[out_key]
        if out_key in options_by_key:
            packed_options = pack_options(options_by_key[out_key], lines, out_key)
            payload["optionGroups"] = packed_options["groups"]
            if packed_options["warnings"]:
                payload["warnings"] = packed_options["warnings"]
        line_graph = build_dialog_tree_line_graph_payload(
            out_key,
            [line.get("id") or "" for line in lines],
        )
        if line_graph:
            payload["lineGraph"] = line_graph
        graph_fragments = build_dialog_tree_fragment_payload(out_key)
        if graph_fragments:
            payload["graphFragments"] = graph_fragments
        scene_graph_links = build_dialog_tree_scene_link_payload(out_key)
        scene_graph_links = apply_source_hub_option_groups(payload, scene_graph_links)
        if scene_graph_links:
            attach_submenu_targets(scene_graph_links)
            payload["sceneGraphLinks"] = scene_graph_links
            scene_graph_links_by_key[out_key] = scene_graph_links
        attach_runtime_registry_debug(payload)
        attach_timeline_action_evidence(
            payload,
            out_key,
            original_line_ids,
            [line.get("id") or "" for line in lines],
        )
        attach_scene_order_warning(payload)
        attach_duplicate_timestamp_warning(payload)
        attach_timeline_timestamp_regression_warning(payload)
        story_issue_codes = dialog_story_issue_codes(payload)
        option_issue_targets = dialog_option_issue_targets(payload)
        recovery_methods = dialog_recovery_methods(payload)
        if fmv_clips_by_key.get(out_key):
            payload["fmvClips"] = fmv_clips_by_key[out_key]
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,                # key
            "d": "dlg",                  # kind
            "m": mission,                # mission id
            "s": scene,                  # scene number
            "t": type_,                  # type prefix (a/c/e/f/m)
            "a": act,                    # act number
            "c": sorted(actors),         # actor ids
            "n": len(lines),             # line count
            "p": preview(prev_text),     # text preview
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        entry["x"] = merge_search_text(
            indexed_line_haystack(lines, "text", "actor", "aid", "hint"),
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
        entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
        if graph_fragments:
            tags = entry.setdefault("tags", [])
            if "graphFragment" not in tags:
                tags.append("graphFragment")
        if scene_graph_links:
            tags = entry.setdefault("tags", [])
            if "sceneGraph" not in tags:
                tags.append("sceneGraph")
        if story_issue_codes:
            entry["storyIssues"] = story_issue_codes
        if option_issue_targets:
            entry["optionIssueTargets"] = option_issue_targets
        if recovery_methods:
            entry["recoveryMethods"] = recovery_methods
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    # Emit SNS conversations
    print(f"Writing {len(sns_groups)} SNS conversations...")
    for sns_id, entry in sns_groups.items():
        m = SNS_RE.match(sns_id)
        mission = m.group(1) if m else sns_id
        scene = int(m.group(2)) if m else 0
        chat_id = str(entry.get("chatId") or "")
        is_topic_chat = sns_id.startswith("sns_topic_") and bool(chat_id)
        if is_topic_chat:
            mission = f"topic_{chat_id}"
        type_, act = parse_mission(mission)
        # Reconstruct order by following nextContentId from -1's preContentId backwards,
        # then forwards from the first node whose preContentId == 0.
        cdata = entry.get("dialogContentData", {})
        # The "-1" sentinel marks the end; its preContentId is the last real node.
        # Find the start: the node whose preContentId == 0 (or 1 if absent).
        start = None
        for cid, node in cdata.items():
            if node.get("preContentId") == 0 and cid != "-1":
                start = cid
                break
        ordered = []
        seen = set()
        cur = start or "1"
        while cur and cur in cdata and cur not in seen:
            seen.add(cur)
            node = cdata[cur]
            if str(node.get("contentId")) == "-1":
                break
            ordered.append((cur, node))
            nxt = node.get("nextContentId")
            cur = str(nxt) if nxt not in (None, 0, -1) else None
        # Fallback: if traversal looks incomplete, append remaining numeric nodes by id.
        if len(ordered) < sum(1 for cid in cdata if cid not in ("-1",)):
            for cid in sorted((c for c in cdata if c not in ("-1",)), key=lambda x: int(x)):
                if cid not in seen:
                    seen.add(cid)
                    ordered.append((cid, cdata[cid]))
        lines = []
        speakers: list[str] = []
        seen_speakers: set[str] = set()
        prev_text = ""
        for order_idx, (cid, node) in enumerate(ordered, start=1):
            speaker = node.get("speaker") or ""
            text = sns_content_text(node)
            options = []
            for opt_id in node.get("dialogOptionIds", []) or []:
                opt = sns_opts.get(opt_id)
                if not opt:
                    continue
                option_text = sns_option_display_text(opt)
                option_res_path = str(opt.get("optionResPath") or "").strip()
                option_entry = {
                    "id": opt_id,
                    "text": option_text,
                    "next": opt.get("optionNextContentId"),
                    "_debug": {
                        **source_ref(
                            "SNSDialogOptionTable",
                            opt_id,
                            pick_fields(
                                opt,
                                "optionDesc",
                                "optionNextContentId",
                                "optionResPath",
                            ),
                        ),
                        "fields": {
                            "text": text_trace(
                                "SNSDialogOptionTable", opt_id, "optionDesc", opt.get("optionDesc")
                            ),
                        },
                    },
                }
                if option_res_path:
                    option_entry["image"] = option_res_path
                    option_entry["emoji"] = option_res_path
                    option_entry["_debug"]["fields"]["image"] = {
                        "table": "SNSDialogOptionTable",
                        "rowId": opt_id,
                        "field": "optionResPath",
                        "raw": option_res_path,
                        "lookup": [
                            {
                                "from": f"SNSDialogOptionTable[{opt_id}].optionResPath",
                                "value": option_res_path,
                            }
                        ],
                        "text": option_text,
                    }
                options.append(option_entry)
            if speaker and speaker not in seen_speakers:
                seen_speakers.add(speaker)
                speakers.append(speaker)
            line_entry = {
                "cid": int(cid),
                "speaker": speaker,
                "text": text,
                "type": node.get("contentType", 1),
                "options": options,
                "linkMission": node.get("linkMissionId") or "",
                "_debug": {
                    **source_ref(
                        "SNSDialogTable.dialogContentData",
                        sns_id,
                        pick_fields(
                            node,
                            "contentId",
                            "preContentId",
                            "nextContentId",
                            "speaker",
                            "content",
                            "contentParam",
                            "contentParams",
                            "contentType",
                            "dialogOptionIds",
                            "linkMissionId",
                            "optionType",
                        ),
                        nodeId=cid,
                        order=order_idx,
                    ),
                    "fields": {
                        "text": text_trace(
                            "SNSDialogTable.dialogContentData", sns_id, "content", node.get("content")
                        ),
                    },
                },
            }
            if node.get("contentType") == 2:
                image_ids = [
                    str(value or "").strip()
                    for value in (node.get("contentParam") or [])
                    if media_id_looks_like_media(value)
                ]
                if image_ids:
                    line_entry["images"] = image_ids
                    line_entry["_debug"]["fields"]["images"] = {
                        "table": "SNSDialogTable.dialogContentData",
                        "rowId": sns_id,
                        "field": "contentParam",
                        "raw": node.get("contentParam"),
                        "lookup": [
                            {
                                "from": f"SNSDialogTable.dialogContentData[{sns_id}].contentParam",
                                "value": image_ids,
                            }
                        ],
                        "text": text,
                    }
            lines.append(line_entry)
            if not prev_text and text:
                prev_text = text
        # Keep each SNS conversation keyed by its original table row id so
        # topic chats can share a chat-based mission bucket without colliding
        # in the index or overwriting each other's conv JSON files.
        out_key = sns_id
        title_topic_id = entry.get("topicId") or mission.removeprefix("topic_")
        topic_title_trace = topic_name_trace(title_topic_id)
        chat_title_trace = chat_name_trace(chat_id)
        mission_title_trace = mission_name_trace(mission)
        chat_title = chat_name(chat_id)
        chat_type_value = chat_type(chat_id)
        mission_title = mission_name(mission)
        topic_title = topic_name(title_topic_id)
        title_choices: list[tuple[str, dict | None]] = []
        if is_topic_chat:
            title_choices.extend([
                (topic_title, topic_title_trace),
                (chat_title, chat_title_trace),
            ])
        else:
            title_choices.append((topic_title, topic_title_trace))
        title_choices.extend([
            (mission_title, mission_title_trace),
            (chat_title, chat_title_trace),
            (sns_raw_title(out_key), {"source": sns_raw_title(out_key)}),
        ])
        display_title = ""
        display_title_debug: dict | None = None
        for title_value, title_debug in title_choices:
            if title_value:
                display_title = title_value
                display_title_debug = title_debug or {"source": title_value}
                break
        if not display_title:
            display_title = sns_raw_title(out_key)
            display_title_debug = {"source": display_title}
        def is_admin_sns_speaker(speaker_id: str) -> bool:
            return (speaker_actor_id(speaker_id) or speaker_id).lower() in ADMIN_ACTOR_IDS
        primary_speaker = speakers[0] if speakers else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = speakers[1] if len(speakers) > 1 else ""
        if primary_speaker and is_admin_sns_speaker(primary_speaker):
            primary_speaker = next(
                (speaker for speaker in speakers if not is_admin_sns_speaker(speaker)),
                "",
            )
        if not primary_speaker and chat_id and not is_admin_sns_speaker(chat_id):
            primary_speaker = chat_id
        index_speakers = (
            [primary_speaker] + [speaker for speaker in speakers if speaker != primary_speaker]
            if primary_speaker else speakers
        )
        sns_payload = {
            "key": out_key,
            "kind": "sns",
            "mission": mission,
            "scene": scene,
            "title": display_title,
            "chatId": chat_id,
            "chatTitle": chat_title,
            "chatType": chat_type_value,
            "chatGroupSpeaker": primary_speaker,
            "relatedMissionId": entry.get("relatedMissionId", ""),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "SNSDialogTable",
                    sns_id,
                    pick_fields(entry, "chatId", "relatedMissionId", "topicId", "dialogContentData"),
                ),
                "title": display_title_debug,
                "chat": chat_title_trace,
            },
        }
        write_conv_payload(out_key, sns_payload)
        entry = {
            "k": out_key,
            "d": "sns",
            "m": mission,
            "s": scene,
            "t": type_,
            "a": act,
            "title": display_title,
            "chatId": chat_id,
            "chatTitle": chat_title,
            "chatType": chat_type_value,
            "chatGroupSpeaker": primary_speaker,
            "c": index_speakers,
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (tags := entry_tags(out_key, mission)):
            entry["tags"] = tags
        sns_line_text = indexed_line_haystack(lines, "text", "speaker", "linkMission")
        entry["x"] = display_title
        for title_text in (chat_title, topic_title, mission_title):
            if title_text and title_text != display_title:
                entry["x"] = merge_search_text(entry["x"], title_text)
        entry["x"] = merge_search_text(entry["x"], sns_line_text)
        entry["x"] = merge_search_text(
            entry["x"],
            extras_text(out_key),
        )
        entry["x"] = merge_search_text(
            entry["x"],
            mission_context_text(mission),
        )
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    # Emit radio conversations as standalone entries. Radio is no longer
    # embedded into dlg/sns/misc pages; the browser should navigate to the
    # explicit radio scene instead.
    print(f"Writing {len(radio_rows)} radio conversations...")
    for radio in sorted(
        radio_rows,
        key=lambda item: (item["t"], item["a"], item["m"], item["s"], item["k"]),
    ):
        out_key = radio["k"]
        payload = {
            "key": out_key,
            "kind": "radio",
            "mission": radio["m"],
            "scene": radio["scene"],
            "radioType": radio["radioType"],
            "lines": radio["lines"],
            "_debug": {
                "source": radio["_debug"],
                "title": mission_name_trace(radio["m"]),
            },
        }
        if radio["target"]:
            payload["_debug"]["attachedTo"] = {
                "source": {
                    "key": radio["target"],
                }
            }
        write_conv_payload(out_key, payload)
        radio_out_keys.add(out_key)
        entry = {
            "k": out_key,
            "d": "radio",
            "m": radio["m"],
            "s": radio["s"],
            "t": radio["t"],
            "a": radio["a"],
            "c": radio["c"],
            "n": len(radio["lines"]),
            "p": radio["p"],
            "tags": ["radio"],
        }
        if (xt := indexed_line_haystack(radio["lines"], "text", "actor", "aid")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(radio["m"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    radio_row_lookup = {row["k"]: row for row in radio_rows}
    black_groups: dict[str, dict] = {}
    for text_id, text_entry in text_table.items():
        m = BLACK_RE.match(text_id)
        if not m:
            continue
        mission, scene, line_str = m.group(1), m.group(2), m.group(3)
        out_key = f"black_{mission}_{scene}"
        bucket = black_groups.setdefault(
            out_key,
            {
                "mission": mission,
                "scene": scene,
                "items": [],
            },
        )
        bucket["items"].append((int(line_str), text_id, text_entry))
    print(f"Writing {len(black_groups)} black-screen conversations...")
    for out_key, bucket in sorted(
        black_groups.items(),
        key=lambda item: (
            parse_mission(item[1]["mission"])[0],
            parse_mission(item[1]["mission"])[1],
            item[1]["mission"],
            scene_sort_value(item[1]["scene"]),
            item[0],
        ),
    ):
        mission = bucket["mission"]
        scene = bucket["scene"]
        type_, act = parse_mission(mission)
        lines = []
        prev_text = ""
        for _order, text_id, text_entry in sorted(bucket["items"], key=lambda item: (item[0], item[1])):
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            lines.append({
                "id": text_id,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        text_id,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                    ),
                    "fields": {
                        "text": text_trace("TextTable", text_id, "id", text_entry),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text
        payload = {
            "key": out_key,
            "kind": "black",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "_debug": {
                "title": mission_name_trace(mission),
            },
        }
        write_conv_payload(out_key, payload)
        black_out_keys.add(out_key)
        entry = {
            "k": out_key,
            "d": "black",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(prev_text),
        }
        if (xt := indexed_line_haystack(lines, "text")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    story_text_key_re = re.compile(
        r"^text_(?P<mission>(?:gm|sm|db|dm|[acefm])\d+(?:[a-z]\d+)*(?:d\d+)?)(?:_(?P<scene>.+))?$",
        re.IGNORECASE,
    )
    def story_text_key_parts(text_key: str) -> tuple[str, str] | None:
        match = story_text_key_re.match(str(text_key or ""))
        if not match:
            return None
        return match.group("mission"), match.group("scene") or "0"
    def reading_popup_story_content_key(row_id: str, row: dict | None) -> str:
        if not isinstance(row, dict):
            return ""
        candidates = [
            str(row.get("contentId") or "").strip(),
            str(row_id or "").strip(),
        ]
        for candidate in candidates:
            if candidate.startswith("text_") and story_text_key_parts(candidate):
                return candidate
        return ""
    def rich_content_story_row(content_key: str, preferred_source: str) -> tuple[str, dict]:
        sources = [preferred_source, "streaming", "persistent"]
        seen_sources: set[str] = set()
        for source_name in sources:
            if source_name in seen_sources:
                continue
            seen_sources.add(source_name)
            payload = rich_content_persistent if source_name == "persistent" else rich_content
            row = payload.get(content_key) if isinstance(payload, dict) else None
            if isinstance(row, dict):
                return source_name, row
        return preferred_source or "streaming", {}
    popup_rows_by_content: dict[str, list[tuple[str, str, dict]]] = defaultdict(list)
    for source_name, popup_table in (
        ("streaming", reading_popups),
        ("persistent", reading_popups_persistent),
    ):
        if not isinstance(popup_table, dict):
            continue
        for row_id, row in popup_table.items():
            content_key = reading_popup_story_content_key(str(row_id), row if isinstance(row, dict) else None)
            if not content_key:
                continue
            popup_rows_by_content[content_key].append((source_name, str(row_id), row))
    print(f"Writing {len(popup_rows_by_content)} reading-popup text conversations...")
    for content_key, popup_rows in sorted(popup_rows_by_content.items()):
        parts = story_text_key_parts(content_key)
        if not parts:
            continue
        popup_rows.sort(key=lambda item: (0 if item[0] == "streaming" else 1, item[1]))
        primary_source, primary_row_id, primary_row = popup_rows[0]
        mission, scene = parts
        type_, act = parse_mission(mission)
        rich_source, rich_row = rich_content_story_row(content_key, primary_source)
        rich_title = t((rich_row.get("title") or {}).get("id"), preferred_source=rich_source) if rich_row else ""
        popup_title = t((primary_row.get("title") or {}).get("id"), preferred_source=primary_source)
        title = brace_text(rich_title or popup_title) or content_key
        lines: list[dict] = []
        prev_text = ""
        for idx, item in enumerate((rich_row.get("contentList") or []) if rich_row else [], start=1):
            if not isinstance(item, dict):
                continue
            content = item.get("content") or {}
            text = t(content.get("id"), preferred_source=rich_source)
            if text and not prev_text:
                prev_text = text
            lines.append({
                "id": f"{content_key}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        content_key,
                        pick_fields(item, "content"),
                        nodeId=idx,
                        tableSource=rich_source,
                    ),
                    "fields": {
                        "text": text_trace(
                            "RichContentTable",
                            content_key,
                            "content",
                            content,
                            preferred_source=rich_source,
                        ),
                    },
                },
            })
        if not lines and not title:
            continue
        popup_sources = [
            source_ref(
                "ReadingPopUpTable",
                row_id,
                pick_fields(row, "bgType", "contentId", "iconType", "id", "title"),
                tableSource=source_name,
            )
            for source_name, row_id, row in popup_rows
        ]
        payload = {
            "key": content_key,
            "kind": "text",
            "mission": mission,
            "scene": scene,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": popup_sources[0],
                "readingPopupRows": popup_sources,
            },
        }
        if rich_row:
            payload["_debug"]["richContent"] = source_ref(
                "RichContentTable",
                content_key,
                pick_fields(rich_row, "title", "contentList"),
                tableSource=rich_source,
            )
        if len(popup_rows) > 1:
            payload["summary"] = [{
                "text": f"Reading popup source rows: {len(popup_rows)}",
            }]
        write_conv_payload(content_key, payload)
        entry = {
            "k": content_key,
            "d": "text",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(prev_text or title),
            "tags": ["readingPopup", "text"],
        }
        search_text = " ".join(part for part in [
            content_key,
            primary_row_id,
            title,
            indexed_line_haystack(lines, "text"),
            mission_context_text(mission),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    remotecomm_video_owner_by_stem: dict[str, str] = {}
    remotecomm_expected_video_stems_by_key: dict[str, list[str]] = {}
    remotecomm_video_timeline_by_key: dict[str, list[dict]] = {}
    remotecomm_available_video_stems = {
        str(ref.get("baseStem") or ref.get("stem") or "").strip().lower()
        for ref in narrative_video_assets
        if ref.get("kind") == "remotecomm" and (ref.get("baseStem") or ref.get("stem"))
    }
    audio_dialog_duration_by_stem: dict[str, dict] = {}
    for audio_row in audio_dialog.values():
        if not isinstance(audio_row, dict):
            continue
        audio_path = str(audio_row.get("path") or "").replace("\\", "/")
        if not audio_path:
            continue
        audio_stem = re.sub(r"\.[^.]+$", "", audio_path.rsplit("/", 1)[-1], flags=re.IGNORECASE).lower()
        if audio_stem:
            audio_dialog_duration_by_stem[audio_stem] = audio_row
    def remotecomm_video_stem_from_middle_id(middle_id: object) -> str:
        value = str(middle_id or "").strip().replace("\\", "/")
        if not value:
            return ""
        stem = value.rsplit("/", 1)[-1].lower()
        if stem in remotecomm_available_video_stems:
            return stem
        return ""
    def remotecomm_voice_duration(voice_id: object) -> float | None:
        row = audio_dialog_duration_by_stem.get(str(voice_id or "").strip().lower())
        if not row:
            return None
        duration_keys: list[str] = []
        if language_code and language_code != "CN":
            duration_keys.append(f"wavDuration{language_code}")
        duration_keys.append("wavDuration")
        if language_code:
            duration_keys.append(f"wavDuration{language_code}")
        for key in _unique_preserve(duration_keys):
            value = row.get(key)
            if isinstance(value, (int, float)) and value >= 0:
                return float(value)
        return None
    remote_rows: list[dict] = []
    for remote_id, remote_entry in remote_common.items():
        m = REMOTECOMM_RE.match(remote_id)
        if not m:
            continue
        mission = m.group(1)
        scene = m.group(2) or "0"
        type_, act = parse_mission(mission)
        lines = []
        actors: set[str] = set()
        audio_events: list[str] = []
        expected_video_stems: list[str] = []
        line_video_timing: list[dict] = []
        elapsed_time: float | None = 0.0
        prev_text = ""
        def add_audio_event(value: object) -> None:
            event_id = str(value or "").strip()
            if not event_id:
                return
            if event_id not in audio_events:
                audio_events.append(event_id)
        def add_expected_video_stem(video_stem: str) -> None:
            if not video_stem:
                return
            if video_stem not in expected_video_stems:
                expected_video_stems.append(video_stem)
            remotecomm_video_owner_by_stem.setdefault(video_stem, remote_id)
        for item in sorted(
            remote_entry.get("remoteCommSingleDataList", []) or [],
            key=lambda row: row.get("index", 0),
        ):
            actor_list = [str(actor_id) for actor_id in (item.get("actorList") or []) if actor_id]
            actor_id = str(item.get("middleId") or (actor_list[0] if actor_list else ""))
            actor = t(item.get("actorName", {}).get("id"))
            text = t(item.get("remoteCommText", {}).get("id"))
            hint = t(item.get("hint", {}).get("id"))
            audio_id = str(item.get("audioId") or "").strip()
            music_id = str(item.get("musicId") or "").strip()
            voice_id = str(item.get("voiceId") or "").strip()
            video_stem = remotecomm_video_stem_from_middle_id(actor_id)
            add_expected_video_stem(video_stem)
            add_audio_event(audio_id)
            add_audio_event(music_id)
            voice_duration = remotecomm_voice_duration(voice_id)
            line_start = elapsed_time
            line_duration = (voice_duration + 1.0) if voice_duration is not None else None
            line_end = (
                line_start + line_duration
                if line_start is not None and line_duration is not None
                else None
            )
            line_video_timing.append({
                "lineId": str(item.get("singleId") or remote_id),
                "index": item.get("index"),
                "middleId": actor_id,
                "videoStem": video_stem,
                "audioEvent": audio_id,
                "voiceId": voice_id,
                "voiceDuration": voice_duration,
                "lineStart": line_start,
                "lineEnd": line_end,
                "isVideoLoop": bool(item.get("isVideoLoop")),
            })
            elapsed_time = line_end
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("singleId") or remote_id,
                "cid": item.get("index"),
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "hint": hint,
                "audio": audio_id,
                "voice": voice_id,
                "_debug": {
                    **source_ref(
                        "RemoteCommonTable.remoteCommSingleDataList",
                        item.get("singleId") or remote_id,
                        pick_fields(
                            item,
                            "actorList",
                            "actorName",
                            "audioId",
                            "hint",
                            "imageList",
                            "index",
                            "isVideoLoop",
                            "middleId",
                            "musicId",
                            "remoteCommText",
                            "singleId",
                            "voiceId",
                        ),
                        rowId=remote_id,
                    ),
                    "fields": {
                        "actor": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "actorName",
                            item.get("actorName"),
                        ),
                        "text": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "remoteCommText",
                            item.get("remoteCommText"),
                        ),
                        "hint": text_trace(
                            "RemoteCommonTable.remoteCommSingleDataList",
                            item.get("singleId") or remote_id,
                            "hint",
                            item.get("hint"),
                        ),
                    },
                },
            })
            if not prev_text and text:
                prev_text = text
        add_audio_event(remote_entry.get("startAudioEvent"))
        add_audio_event(remote_entry.get("endAudioEvent"))
        if expected_video_stems:
            remotecomm_expected_video_stems_by_key[remote_id] = expected_video_stems
        video_segments: list[dict] = []
        current_segment: dict | None = None
        for timing in line_video_timing:
            video_stem = str(timing.get("videoStem") or "")
            if not video_stem:
                if current_segment is not None:
                    video_segments.append(current_segment)
                    current_segment = None
                continue
            if current_segment is None or current_segment.get("videoStem") != video_stem:
                if current_segment is not None:
                    video_segments.append(current_segment)
                current_segment = {
                    "videoStem": video_stem,
                    "middleId": str(timing.get("middleId") or ""),
                    "startLine": str(timing.get("lineId") or ""),
                    "endLine": str(timing.get("lineId") or ""),
                    "startIndex": timing.get("index"),
                    "endIndex": timing.get("index"),
                    "startTime": timing.get("lineStart"),
                    "endTime": timing.get("lineEnd"),
                    "lineIds": [],
                    "audioEvents": [],
                    "isVideoLoop": bool(timing.get("isVideoLoop")),
                    "timingBasis": "RemoteComm auto advance uses voice wavDuration + 1s per line",
                }
            current_segment["endLine"] = str(timing.get("lineId") or "")
            current_segment["endIndex"] = timing.get("index")
            current_segment["endTime"] = timing.get("lineEnd")
            current_segment["lineIds"].append(str(timing.get("lineId") or ""))
            if timing.get("audioEvent") and timing.get("audioEvent") not in current_segment["audioEvents"]:
                current_segment["audioEvents"].append(str(timing["audioEvent"]))
            if timing.get("lineStart") is not None and current_segment.get("startTime") is None:
                current_segment["startTime"] = timing.get("lineStart")
            if timing.get("lineEnd") is not None:
                current_segment["endTime"] = timing.get("lineEnd")
        if current_segment is not None:
            video_segments.append(current_segment)
        for segment in video_segments:
            if isinstance(segment.get("startTime"), (int, float)):
                segment["startTime"] = round(float(segment["startTime"]), 6)
            if isinstance(segment.get("endTime"), (int, float)):
                segment["endTime"] = round(float(segment["endTime"]), 6)
            if isinstance(segment.get("startTime"), (int, float)) and isinstance(segment.get("endTime"), (int, float)):
                segment["duration"] = round(float(segment["endTime"]) - float(segment["startTime"]), 6)
        if video_segments:
            remotecomm_video_timeline_by_key[remote_id] = video_segments
        remote_rows.append({
            "key": remote_id,
            "mission": mission,
            "scene": scene,
            "type": type_,
            "act": act,
            "actors": sorted(actors),
            "lines": lines,
            "audioEvents": audio_events,
            "expectedVideoStems": expected_video_stems,
            "videoTimeline": video_segments,
            "preview": prev_text,
            "source": remote_entry,
        })
    print(f"Writing {len(remote_rows)} remote communication conversations...")
    for remote in sorted(
        remote_rows,
        key=lambda item: (
            item["type"],
            item["act"],
            item["mission"],
            scene_sort_value(item["scene"]),
            item["key"],
        ),
    ):
        payload = {
            "key": remote["key"],
            "kind": "remotecomm",
            "mission": remote["mission"],
            "scene": remote["scene"],
            "lines": remote["lines"],
            "_debug": {
                "source": source_ref(
                    "RemoteCommonTable",
                    remote["key"],
                    pick_fields(remote["source"], "autoPlay", "startAudioEvent", "endAudioEvent", "remoteCommSingleDataList"),
                ),
                "title": mission_name_trace(remote["mission"]),
            },
        }
        if remote["audioEvents"]:
            payload["audioEvents"] = list(remote["audioEvents"])
            payload["_debug"]["audioEvents"] = {
                "source": {
                    "table": "RemoteCommonTable",
                    "rowId": remote["key"],
                    "fields": ["startAudioEvent", "endAudioEvent", "remoteCommSingleDataList.audioId", "remoteCommSingleDataList.musicId"],
                    "values": list(remote["audioEvents"]),
                },
            }
        if remote["expectedVideoStems"]:
            payload["_debug"]["remotecommVideos"] = {
                "source": {
                    "table": "RemoteCommonTable.remoteCommSingleDataList",
                    "rowId": remote["key"],
                    "evidence": "middleId video lookup: Narrative/RemoteComm/{middleId}",
                    "expectedVideoStems": list(remote["expectedVideoStems"]),
                },
            }
        if remote["videoTimeline"]:
            payload["remotecommVideoTimeline"] = list(remote["videoTimeline"])
            payload["_debug"].setdefault("remotecommVideos", {
                "source": {
                    "table": "RemoteCommonTable.remoteCommSingleDataList",
                    "rowId": remote["key"],
                    "evidence": "middleId video lookup: Narrative/RemoteComm/{middleId}",
                    "expectedVideoStems": list(remote["expectedVideoStems"]),
                },
            })
            payload["_debug"]["remotecommVideos"]["source"]["timeline"] = list(remote["videoTimeline"])
        write_conv_payload(remote["key"], payload)
        remotecomm_out_keys.add(remote["key"])
        entry = {
            "k": remote["key"],
            "d": "remotecomm",
            "m": remote["mission"],
            "s": scene_sort_value(remote["scene"]),
            "t": remote["type"],
            "a": remote["act"],
            "c": remote["actors"],
            "n": len(remote["lines"]),
            "p": preview(remote["preview"]),
        }
        if (xt := indexed_line_haystack(remote["lines"], "text", "actor", "aid", "hint")):
            entry["x"] = xt
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(remote["mission"]))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    known_cutscene_missions = sorted(
        {
            path.stem
            for path in MRA_DIR.glob("*.json")
            if path.stem and not path.stem.endswith("_meta")
        }
        | {
            entry["m"]
            for entry in index_entries
            if entry.get("m")
        },
        key=lambda mission: (-len(mission), mission),
    )

    def split_cutscene_parent_key(key: str) -> str:
        match = re.match(r"^(cutscene_.+_\d+)_(\d+)$", str(key or ""))
        return match.group(1) if match else ""
    def split_cutscene_child_sort_key(key: str) -> tuple[int, str]:
        match = re.match(r"^cutscene_.+_\d+_(\d+)$", str(key or ""))
        return (int(match.group(1)) if match else 999999, str(key or ""))
    def resolve_cutscene_text_group(group: str, asset_keys: set[str], raw_groups: set[str]) -> str:
        if group in asset_keys:
            return group
        normalized = normalize_cutscene_text_group(group)
        if normalized != group:
            if normalized in asset_keys:
                return normalized
            if normalized in raw_groups:
                return group
        if normalized in asset_keys:
            return normalized
        for candidate in sorted(asset_keys, key=lambda key: (-len(key), key)):
            if not group.startswith(candidate):
                continue
            rest = group[len(candidate):]
            if rest and re.fullmatch(r"d\d+(?:_.*)?", rest):
                return candidate
        return normalized
    def subtitle_locale_tokens(code: str) -> tuple[str, ...]:
        return {
            "CN": ("CHI", "CN"),
            "EN": ("ENG", "EN"),
            "JP": ("JP",),
            "KR": ("KR", "KO"),
            "TC": ("CHT", "TC"),
            "MX": ("MX", "ES"),
            "BR": ("BR", "PT"),
        }.get(str(code or "").upper(), (str(code or "").upper(),))
    def subtitle_track_language_score(track: dict) -> int:
        name = str(track.get("parentName") or "").upper()
        desired = subtitle_locale_tokens(language_code)
        def first_desired_index(tokens: list[str]) -> int | None:
            matches = [
                desired.index(token)
                for token in tokens
                if token in desired
            ]
            return min(matches) if matches else None
        env_tokens = re.findall(r"_ENV_([A-Z]+)", name)
        audio_tokens = re.findall(r"_AU_([A-Z]+)", name)
        if env_tokens:
            env_index = first_desired_index(env_tokens)
            if env_index is None:
                return 100
            audio_index = first_desired_index(audio_tokens)
            return env_index if audio_index is not None else 10 + env_index
        if audio_tokens:
            audio_index = first_desired_index(audio_tokens)
            return 20 + audio_index if audio_index is not None else 80
        return 50
    # The CN e0m0_2 playable has two Chinese-looking subtitle families. The
    # untagged F/M tracks match observed playback; the AU_CHI_ENV_CHI tracks are
    # a different localized/audio variant with incompatible mid-scene lines.
    cutscene_subtitle_parent_overrides = {
        "CN": {
            "cutscene_e0m0_2": {
                "f_cutscene_e0m0_2_Others",
                "m_cutscene_e0m0_2_Others",
            },
        },
    }
    def subtitle_tracks_for_language(cutscene_key: str, tracks: list[dict]) -> list[dict]:
        parent_override = (
            cutscene_subtitle_parent_overrides
            .get(str(language_code or "").upper(), {})
            .get(cutscene_key)
        )
        if parent_override:
            selected = [
                track for track in tracks
                if str(track.get("parentName") or "") in parent_override
            ]
            if selected:
                return selected
        scored = [
            (subtitle_track_language_score(track), track)
            for track in tracks
            if isinstance(track, dict)
        ]
        if not scored:
            return []
        best_score = min(score for score, _track in scored)
        return [
            track for score, track in scored
            if score == best_score
        ]
    def cutscene_text_lines(
        asset_keys: set[str],
        subtitle_tracks_by_key: dict[str, list[dict]],
    ) -> dict[str, list[dict]]:
        split_asset_children_by_parent: dict[str, list[str]] = defaultdict(list)
        for asset_key in asset_keys:
            parent_key = split_cutscene_parent_key(asset_key)
            if parent_key and parent_key not in asset_keys:
                split_asset_children_by_parent[parent_key].append(asset_key)
        for children in split_asset_children_by_parent.values():
            children.sort(key=split_cutscene_child_sort_key)
        raw_groups: set[str] = set()
        matched_rows: list[tuple[str, dict, re.Match[str]]] = []
        for row_id, text_entry in text_table.items():
            row_key = str(row_id or "")
            if not row_key.startswith("cutscene_"):
                continue
            match = CUTSCENE_TEXT_ROW_RE.match(row_key)
            if not match:
                continue
            raw_groups.add(match.group("group"))
            matched_rows.append((row_key, text_entry, match))
        grouped: dict[str, list[tuple[tuple[int, int, int, str, str], dict]]] = defaultdict(list)
        lines_by_row_id: dict[str, dict] = {}
        def build_cutscene_texttable_line(
            row_key: str,
            text_entry,
            match: re.Match[str],
            cutscene_key: str,
            raw_group: str,
        ) -> dict:
            line_num = int(match.group("line"))
            sub = match.group("sub") or ""
            gender = (match.group("gender") or "").strip("_").upper()
            cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
            line = {
                "id": row_key,
                "cid": cid,
                "text": text,
                "_debug": {
                    **source_ref(
                        "TextTable",
                        row_key,
                        pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                        cutsceneKey=cutscene_key,
                        textGroup=raw_group,
                        line=line_num,
                    ),
                    "fields": {
                        "text": text_trace("TextTable", row_key, "id", text_entry),
                    },
                },
            }
            if raw_group != cutscene_key:
                line["textGroup"] = raw_group
            if sub:
                line["sub"] = sub
                line["_debug"]["source"]["sub"] = sub
            if gender:
                line["gender"] = gender
                line["_debug"]["source"]["gender"] = gender
            return line
        def remember_cutscene_line_usage(line: dict) -> None:
            remember_texttable_row_usage(line.get("id"))
            for duplicate in line.get("mergedDuplicateRows") or []:
                if isinstance(duplicate, dict):
                    remember_texttable_row_usage(duplicate.get("id"))
        def subtitle_start_key(value) -> float:
            return round(float(value), 6) if isinstance(value, (int, float)) else 0.0
        def subtitle_slot_key(ref: dict, timing_index: int) -> tuple[float, float, int]:
            duration = ref.get("duration")
            return (
                subtitle_start_key(ref.get("start")),
                round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
                timing_index,
            )
        def subtitle_clip_debug(track: dict, ref: dict) -> dict:
            debug = {
                "source": "animeSubtitleTrack",
                "file": track.get("file"),
                "parent": track.get("parentName"),
                "parentFile": track.get("parentFile"),
                "textId": ref.get("textId"),
                "start": ref.get("start"),
                "duration": ref.get("duration"),
                "clipIndex": ref.get("clipIndex"),
                "assetPathId": ref.get("assetPathId"),
            }
            if ref.get("displayName"):
                debug["displayName"] = ref.get("displayName")
            if track.get("gender"):
                debug["assetGender"] = track["gender"]
            if track.get("pathId") not in (None, ""):
                debug["trackPathId"] = track["pathId"]
            if track.get("parentPathId") not in (None, ""):
                debug["parentPathId"] = track["parentPathId"]
            return debug
        def line_matches_cutscene_key(line: dict, cutscene_key: str) -> bool:
            row_id = str(line.get("id") or "")
            if row_id.startswith(f"{cutscene_key}_"):
                return True
            if str(line.get("textGroup") or "") == cutscene_key:
                return True
            debug = line.get("_debug") if isinstance(line.get("_debug"), dict) else {}
            if str(debug.get("cutsceneKey") or "") == cutscene_key:
                return True
            source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
            return str(source.get("textGroup") or "") == cutscene_key
        def subtitle_gender_rank(gender: str) -> int:
            return {"": 0, "F": 1, "M": 2}.get(str(gender or "").upper(), 3)
        def line_has_explicit_gender_switch(line: dict) -> bool:
            text = str(line.get("text") or "")
            return "{F}" in text or "{M}" in text
        def normalize_subtitle_variant_text(text: object) -> str:
            source = str(text or "")
            source = re.sub(r"\{[FM]\}", "", source)
            return "".join(
                ch.casefold()
                for ch in source
                if not ch.isspace() and not unicodedata.category(ch).startswith("P")
            )
        def subtitle_candidate_rank(cutscene_key: str, candidate: dict) -> tuple[int, int, int, int, str]:
            line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
            return (
                0 if line_has_explicit_gender_switch(line) else 1,
                0 if line_matches_cutscene_key(line, cutscene_key) else 1,
                subtitle_gender_rank(candidate.get("gender") or ""),
                int(candidate.get("clipIndex") or 0),
                str(candidate.get("rowKey") or ""),
            )
        def subtitle_alternate_line_debug(candidate: dict) -> dict:
            line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
            out = {
                "id": line.get("id"),
                "cid": line.get("cid"),
                "text": line.get("text"),
                "track": candidate.get("trackDebug"),
            }
            if line.get("textGroup"):
                out["textGroup"] = line.get("textGroup")
            if candidate.get("gender"):
                out["assetGender"] = candidate.get("gender")
            return out
        def build_fallback_track_line(cutscene_key: str, row_key: str, ref: dict) -> dict:
            match = CUTSCENE_TEXT_ROW_RE.match(row_key)
            text_entry = text_table.get(row_key)
            text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry) if text_entry else ""
            source = source_ref(
                "AnimeStudioSubtitleTrack",
                row_key,
                {"textId": row_key},
                cutsceneKey=cutscene_key,
            )
            if match:
                raw_group = match.group("group")
                line_num = int(match.group("line"))
                sub = match.group("sub") or ""
                gender = (match.group("gender") or "").strip("_").upper()
                source["source"]["textGroup"] = raw_group
                source["source"]["line"] = line_num
                if sub:
                    source["source"]["sub"] = sub
                if gender:
                    source["source"]["gender"] = gender
                cid = f"{match.group('line')}{sub}{('_' + gender.lower()) if gender else ''}"
            else:
                cid = str(ref.get("clipIndex") or "")
            return {
                "id": row_key,
                "cid": cid,
                "text": text,
                "_debug": {
                    **source,
                    "fields": {
                        "text": text_trace("TextTable", row_key, "id", text_entry) if text_entry else {
                            "table": "TextTable",
                            "rowId": row_key,
                            "field": "id",
                            "raw": None,
                            "lookup": [],
                            "text": "",
                        },
                    },
                },
            }
        for row_key, text_entry, match in matched_rows:
            raw_group = match.group("group")
            cutscene_key = resolve_cutscene_text_group(raw_group, asset_keys, raw_groups)
            line_num = int(match.group("line"))
            sub = match.group("sub") or ""
            gender = (match.group("gender") or "").strip("_").upper()
            line = build_cutscene_texttable_line(row_key, text_entry, match, cutscene_key, raw_group)
            lines_by_row_id[row_key] = line
            sub_order = int(sub[1:]) if sub else -1
            alias_order = 1 if raw_group != cutscene_key else 0
            grouped[cutscene_key].append(((line_num, sub_order, alias_order, gender, row_key), line))
        merged_by_key: dict[str, list[dict]] = {}
        for cutscene_key, subtitle_tracks in subtitle_tracks_by_key.items():
            subtitle_tracks = subtitle_tracks_for_language(cutscene_key, subtitle_tracks)
            slot_candidates: dict[tuple[float, float, int], list[dict]] = defaultdict(list)
            for track in subtitle_tracks:
                timing_counts: dict[tuple[float, float], int] = defaultdict(int)
                for ref in track.get("lines") or []:
                    row_key = str(ref.get("textId") or "").strip()
                    if not row_key:
                        continue
                    start = subtitle_start_key(ref.get("start"))
                    duration = ref.get("duration")
                    timing_key = (
                        start,
                        round(float(duration), 6) if isinstance(duration, (int, float)) else 0.0,
                    )
                    timing_index = timing_counts[timing_key]
                    timing_counts[timing_key] += 1
                    slot_key = subtitle_slot_key(ref, timing_index)
                    track_debug = subtitle_clip_debug(track, ref)
                    line = copy.deepcopy(lines_by_row_id.get(row_key))
                    if line is None:
                        line = build_fallback_track_line(cutscene_key, row_key, ref)
                    line_debug = line.setdefault("_debug", {})
                    line_debug["subtitleTrack"] = track_debug
                    line_debug.setdefault("subtitleTracks", []).append(track_debug)
                    line_debug.setdefault("source", {})["subtitleTrackFile"] = track.get("file")
                    if track.get("gender"):
                        line_debug["source"]["subtitleAssetGender"] = track["gender"]
                    remember_cutscene_line_usage(line)
                    slot_candidates[slot_key].append({
                        "rowKey": row_key,
                        "slotKey": slot_key,
                        "gender": str(track.get("gender") or "").upper(),
                        "clipIndex": int(ref.get("clipIndex") or 0),
                        "sortKey": (slot_key[0], timing_index, int(ref.get("clipIndex") or 0), row_key),
                        "line": line,
                        "trackDebug": track_debug,
                    })
            ordered_lines: list[tuple[tuple[float, int, int, str], dict]] = []
            for slot_key, candidates in slot_candidates.items():
                genders = {candidate["gender"] for candidate in candidates if candidate.get("gender")}
                if len(genders) > 1 and all(candidate.get("gender") for candidate in candidates):
                    ranked = sorted(
                        candidates,
                        key=lambda candidate: subtitle_candidate_rank(cutscene_key, candidate),
                    )
                    chosen = ranked[0]
                    chosen_line = chosen["line"]
                    chosen_debug = chosen_line.setdefault("_debug", {})
                    chosen_tracks = chosen_debug.setdefault("subtitleTracks", [])
                    alternates: list[dict] = []
                    by_gender: dict[str, dict] = {}
                    chosen_text = chosen_line.get("text")
                    chosen_id = chosen_line.get("id")
                    explicit_switch = line_has_explicit_gender_switch(chosen_line)
                    if chosen.get("gender"):
                        by_gender.setdefault(chosen["gender"], chosen)
                    for candidate in ranked[1:]:
                        if candidate.get("gender"):
                            by_gender.setdefault(candidate["gender"], candidate)
                        candidate_track = candidate.get("trackDebug")
                        if candidate_track:
                            chosen_tracks.append(candidate_track)
                        candidate_line = candidate.get("line") if isinstance(candidate.get("line"), dict) else {}
                        if candidate_line.get("id") != chosen_id or candidate_line.get("text") != chosen_text:
                            alternates.append(subtitle_alternate_line_debug(candidate))
                    if not explicit_switch and "F" in by_gender and "M" in by_gender:
                        f_line = by_gender["F"].get("line") if isinstance(by_gender["F"].get("line"), dict) else {}
                        m_line = by_gender["M"].get("line") if isinstance(by_gender["M"].get("line"), dict) else {}
                        f_text = str(f_line.get("text") or "")
                        m_text = str(m_line.get("text") or "")
                        if (
                            f_text != m_text
                            and normalize_subtitle_variant_text(f_text)
                            != normalize_subtitle_variant_text(m_text)
                        ):
                            chosen_line["text"] = f"{{F}}{f_text}{{M}}{m_text}"
                            chosen_debug["subtitleGenderSwitch"] = {
                                "source": "animeSubtitleTrackAlignment",
                                "F": {"id": f_line.get("id"), "text": f_text},
                                "M": {"id": m_line.get("id"), "text": m_text},
                            }
                    if alternates:
                        chosen_debug["subtitleAlternateLines"] = alternates
                    ordered_lines.append((chosen["sortKey"], chosen_line))
                    continue
                by_row_key: dict[str, dict] = {}
                for candidate in sorted(candidates, key=lambda c: (c["sortKey"], c["rowKey"])):
                    existing = by_row_key.get(candidate["rowKey"])
                    if existing is not None:
                        existing_line = existing["line"]
                        existing_debug = existing_line.setdefault("_debug", {})
                        candidate_track = candidate.get("trackDebug")
                        if candidate_track:
                            existing_debug.setdefault("subtitleTracks", []).append(candidate_track)
                        continue
                    by_row_key[candidate["rowKey"]] = candidate
                    ordered_lines.append((candidate["sortKey"], candidate["line"]))
            if ordered_lines:
                subtitle_lines = [
                    line for _sort_key, line in sorted(ordered_lines, key=lambda item: item[0])
                ]
                text_rows = grouped.get(cutscene_key) or []
                text_rows_have_text = any(
                    str(line.get("text") or "").strip()
                    for _sort_key, line in text_rows
                    if isinstance(line, dict)
                )
                subtitle_lines_have_text = any(
                    str(line.get("text") or "").strip()
                    for line in subtitle_lines
                    if isinstance(line, dict)
                )
                if text_rows_have_text and not subtitle_lines_have_text:
                    subtitle_lines = merge_duplicate_cutscene_rows(text_rows)
                    track_ids = [
                        str(line.get("id") or "")
                        for line in (
                            candidate.get("line")
                            for candidates in slot_candidates.values()
                            for candidate in candidates
                        )
                        if isinstance(line, dict) and line.get("id")
                    ]
                    for line in subtitle_lines:
                        line_debug = line.setdefault("_debug", {})
                        line_debug["subtitleTrackTextTableFallback"] = {
                            "source": "animeSubtitleTrack",
                            "reason": "subtitle track textIds did not resolve to localized TextTable text",
                            "trackTextIds": sorted(set(track_ids)),
                        }
                        remember_cutscene_line_usage(line)
                merged_by_key[cutscene_key] = subtitle_lines
        def lines_for_cutscene_key(cutscene_key: str) -> list[dict]:
            if cutscene_key in merged_by_key:
                return merged_by_key[cutscene_key]
            return [
                line
                for _sort_key, line in grouped.get(cutscene_key, [])
                if isinstance(line, dict)
            ]
        def matching_split_child_line(parent_key: str, parent_line: dict) -> dict | None:
            cid = str(parent_line.get("cid") or "")
            normalized_text = cutscene_pair_normalize(str(parent_line.get("text") or ""))
            if not cid or not normalized_text:
                return None
            for child_key in split_asset_children_by_parent.get(parent_key) or []:
                for child_line in lines_for_cutscene_key(child_key):
                    if str(child_line.get("cid") or "") != cid:
                        continue
                    child_text = cutscene_pair_normalize(str(child_line.get("text") or ""))
                    if child_text and child_text == normalized_text:
                        return child_line
            return None
        def attach_text_only_parent_duplicate(parent_key: str, parent_line: dict, child_line: dict) -> None:
            duplicate = {
                "id": parent_line.get("id") or "",
                "textGroup": parent_key,
            }
            if parent_line.get("text"):
                duplicate["text"] = parent_line["text"]
            if parent_line.get("sub"):
                duplicate["sub"] = parent_line["sub"]
            if parent_line.get("gender"):
                duplicate["gender"] = parent_line["gender"]
            child_line.setdefault("mergedDuplicateRows", []).append(duplicate)
            child_debug = child_line.setdefault("_debug", {})
            child_debug.setdefault("mergedDuplicateRows", []).append(duplicate)
            child_source = child_debug.setdefault("source", {})
            row_ids = child_source.setdefault("mergedDuplicateRowIds", [])
            if duplicate["id"] and duplicate["id"] not in row_ids:
                row_ids.append(duplicate["id"])
            groups = child_source.setdefault("mergedDuplicateTextGroups", [])
            if parent_key and parent_key not in groups:
                groups.append(parent_key)
            suppressed = child_source.setdefault("suppressedTextOnlyParentGroups", [])
            if parent_key and parent_key not in suppressed:
                suppressed.append(parent_key)
            remember_cutscene_line_usage(child_line)
        def suppress_text_only_split_parent(cutscene_key: str, rows: list[tuple[tuple[int, int, int, str, str], dict]]) -> bool:
            if cutscene_key in asset_keys:
                return False
            if not split_asset_children_by_parent.get(cutscene_key):
                return False
            matches: list[tuple[dict, dict]] = []
            for _sort_key, line in rows:
                if not isinstance(line, dict):
                    return False
                child_line = matching_split_child_line(cutscene_key, line)
                if child_line is None:
                    return False
                matches.append((line, child_line))
            for parent_line, child_line in matches:
                attach_text_only_parent_duplicate(cutscene_key, parent_line, child_line)
            return bool(matches)
        for cutscene_key, rows in grouped.items():
            if cutscene_key in merged_by_key:
                continue
            if suppress_text_only_split_parent(cutscene_key, rows):
                continue
            lines = merge_duplicate_cutscene_rows(rows)
            for line in lines:
                remember_cutscene_line_usage(line)
            merged_by_key[cutscene_key] = lines
        return merged_by_key
    def ensure_cutscene_asset(cutscene_key: str) -> dict:
        return cutscene_assets.setdefault(
            cutscene_key,
            {
                "variants": [],
                "componentCounts": {},
                "levels": [],
                "actorLabels": [],
                "paths": [],
                "versions": [],
                "audioEvents": [],
                "tags": [],
                "metadata": {},
                "keepCameraPaths": [],
                "useBlackScreen": False,
                "isTransition": False,
                "hasSubtitleTrack": False,
                "textOnly": True,
            },
        )
    def story_source_backed_cutscene_keys() -> set[str]:
        backed: set[str] = set()
        for raw_key in story_source_links:
            key = str(raw_key or "").strip()
            if not key:
                continue
            candidates = [key]
            if key.endswith("_start"):
                candidates.append(key.removesuffix("_start"))
            for candidate in candidates:
                canonical = _canonical_cutscene_key(candidate)
                if canonical:
                    backed.add(canonical)
        return backed
    def narrative_video_backed_cutscene_keys() -> set[str]:
        """Return cutscene keys whose text-only file has video evidence.
        Dialog-bound FMVs often carry names such as `cs_video_dlg_e0m2_5`.
        Those should attach to the dialog, not promote a sibling
        `cutscene_e0m2_5` TextTable group. Keep a text-only cutscene only when
        the video does not already resolve to a previously written story key.
        """
        existing_story_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }
        backed: set[str] = set()
        for ref in narrative_video_assets:
            if ref.get("kind") != "cutscene":
                continue
            authoritative_keys = [
                str(candidate or "").strip()
                for candidate in (ref.get("authoritativeKeys") or [])
                if str(candidate or "").strip()
            ]
            if authoritative_keys:
                if any(candidate in existing_story_keys for candidate in authoritative_keys):
                    continue
                candidates = authoritative_keys
            else:
                candidates = [
                    str(candidate or "").strip()
                    for candidate in (ref.get("keyCandidates") or [])
                    if str(candidate or "").strip()
                ]
            for candidate in candidates:
                canonical = _canonical_cutscene_key(candidate)
                if canonical:
                    backed.add(canonical)
        return backed
    def cutscene_text_fingerprint(lines: list[dict]) -> tuple[str, ...]:
        return tuple(
            text
            for line in lines
            if isinstance(line, dict)
            for text in [cutscene_pair_normalize(str(line.get("text") or ""))]
            if text
        )
    def cutscene_text_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
        if not left or not right:
            return 0.0
        if left == right:
            return 1.0
        return SequenceMatcher(None, "\n".join(left), "\n".join(right)).ratio()
    def find_suppressed_cutscene_duplicate(
        cutscene_key: str,
        lines: list[dict],
        kept_lines_by_key: dict[str, list[dict]],
    ) -> dict:
        fingerprint = cutscene_text_fingerprint(lines)
        if not fingerprint:
            return {}
        mission, _scene = _infer_cutscene_mission_and_scene(cutscene_key, known_cutscene_missions)
        best: tuple[float, str, int] = (0.0, "", 0)
        for target_key, target_lines in kept_lines_by_key.items():
            if target_key == cutscene_key:
                continue
            target_mission, _target_scene = _infer_cutscene_mission_and_scene(target_key, known_cutscene_missions)
            if mission and target_mission and mission != target_mission:
                continue
            target_fingerprint = cutscene_text_fingerprint(target_lines)
            score = cutscene_text_similarity(fingerprint, target_fingerprint)
            if score > best[0]:
                best = (score, target_key, len(target_fingerprint))
        if best[0] < 0.98:
            return {}
        return {
            "key": best[1],
            "similarity": round(best[0], 4),
            "lineCount": best[2],
        }
    def write_suppressed_cutscene_text_report(rows: list[dict]) -> dict:
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "summary": {
                "textOnlyCandidates": len(rows),
                "emittedTextOnlyCandidates": sum(1 for row in rows if row.get("emitted")),
                "suppressedTextOnlyCutscenes": sum(1 for row in rows if not row.get("emitted")),
                "duplicateTextGroups": sum(1 for row in rows if row.get("duplicateOf")),
            },
            "rows": rows,
        }
        report_json = REPORTS_DIR / f"cutscene_text_candidates_{language_code}.json"
        if not rows:
            report_json.unlink(missing_ok=True)
            return report
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(report_json, report, indent=2, compact=False)
        report["report"] = {
            "json": repo_rel(report_json),
        }
        return report
    cutscene_assets = _load_cutscene_assets()
    cutscene_text_by_key = cutscene_text_lines(set(cutscene_assets), _load_cutscene_subtitle_tracks())
    source_backed_cutscene_keys = story_source_backed_cutscene_keys()
    video_backed_cutscene_keys = narrative_video_backed_cutscene_keys()
    retained_text_only_cutscene_keys = source_backed_cutscene_keys | video_backed_cutscene_keys
    unconfirmed_text_by_key: dict[str, list[dict]] = {
        cutscene_key: lines
        for cutscene_key, lines in cutscene_text_by_key.items()
        if cutscene_key not in cutscene_assets
        and cutscene_key not in retained_text_only_cutscene_keys
    }
    suppressed_text_by_key: dict[str, list[dict]] = {}
    suppressed_duplicate_groups_by_target: dict[str, list[dict]] = defaultdict(list)
    kept_cutscene_lines = {
        key: lines
        for key, lines in cutscene_text_by_key.items()
        if key in cutscene_assets or key in retained_text_only_cutscene_keys
    }
    suppressed_report_rows: list[dict] = []
    for cutscene_key, lines in sorted(unconfirmed_text_by_key.items()):
        duplicate_of = find_suppressed_cutscene_duplicate(cutscene_key, lines, kept_cutscene_lines)
        row = {
            "key": cutscene_key,
            "lineCount": len(lines),
            "lineIds": [
                str(line.get("id") or "")
                for line in lines
                if isinstance(line, dict) and line.get("id")
            ],
            "reason": "textOnlyWithoutAssetSourceOrVideo",
            "emitted": True,
        }
        if duplicate_of:
            suppressed_text_by_key[cutscene_key] = cutscene_text_by_key.pop(cutscene_key)
            row["emitted"] = False
            row["duplicateOf"] = duplicate_of
            suppressed_duplicate_groups_by_target[duplicate_of["key"]].append({
                "key": cutscene_key,
                "lineCount": len(lines),
                "similarity": duplicate_of["similarity"],
            })
        suppressed_report_rows.append(row)
    write_suppressed_cutscene_text_report(suppressed_report_rows)
    for cutscene_key in cutscene_text_by_key:
        cutscene = ensure_cutscene_asset(cutscene_key)
        if cutscene_key in unconfirmed_text_by_key and cutscene_key not in suppressed_text_by_key:
            cutscene["textOnlyUnconfirmed"] = True
    for target_key, groups in suppressed_duplicate_groups_by_target.items():
        if target_key in cutscene_assets:
            existing = cutscene_assets[target_key].setdefault("suppressedTextOnlyGroups", [])
            existing.extend(groups)
    timeline_bound_cutscene_video_keys: set[str] = set()
    for ref in narrative_video_assets:
        if ref.get("kind") != "cutscene":
            continue
        binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
        if not binding or binding.get("isHint"):
            continue
        if "timelinePlayable" not in set(binding.get("sourceKinds") or []):
            continue
        for candidate in ref.get("authoritativeKeys") or ref.get("keyCandidates") or []:
            candidate_key = str(candidate or "")
            if candidate_key in cutscene_assets:
                timeline_bound_cutscene_video_keys.add(candidate_key)
    print(f"Writing {len(cutscene_assets)} cutscene conversations...")
    for cutscene_key, cutscene in sorted(cutscene_assets.items()):
        mission, scene = _infer_cutscene_mission_and_scene(cutscene_key, known_cutscene_missions)
        type_, act = parse_mission(mission)
        if type_ not in MISSION_STORY_TYPES:
            type_, act = "x", 0
        lines = cutscene_text_by_key.get(cutscene_key, [])
        text_groups = cutscene_line_text_groups(cutscene_key, lines)
        summary_rows: list[dict] = []
        if cutscene.get("paths"):
            summary_rows.append({"text": f"AnimeStudio path: {cutscene['paths'][0]}"})
        if cutscene.get("levels"):
            summary_rows.append({"text": f"Levels: {', '.join(cutscene['levels'])}"})
        if cutscene.get("audioEvents"):
            summary_rows.append({"text": "Audio events: " + ", ".join(cutscene["audioEvents"][:8])})
        if cutscene.get("tags"):
            summary_rows.append({"text": "Tags: " + ", ".join(cutscene["tags"][:8])})
        metadata = cutscene.get("metadata") or {}
        if isinstance(metadata, dict) and metadata:
            metadata_parts = []
            for meta_key, values in list(metadata.items())[:8]:
                if isinstance(values, list):
                    metadata_parts.append(f"{meta_key}={', '.join(str(value) for value in values[:3])}")
                else:
                    metadata_parts.append(f"{meta_key}={values}")
            if metadata_parts:
                summary_rows.append({"text": "Metadata: " + "; ".join(metadata_parts)})
        component_summary = _cutscene_component_summary(cutscene)
        if component_summary:
            summary_rows.append({"text": f"Components: {component_summary}"})
        if cutscene.get("variants"):
            summary_rows.append({"text": f"Files: {len(cutscene['variants'])} exported asset(s)"})
        if cutscene.get("suppressedTextOnlyGroups"):
            names = ", ".join(
                str(group.get("key") or "")
                for group in (cutscene.get("suppressedTextOnlyGroups") or [])[:8]
                if group.get("key")
            )
            if names:
                summary_rows.append({"text": f"Suppressed duplicate text groups: {names}"})
        if cutscene.get("textOnlyUnconfirmed"):
            summary_rows.append({
                "text": "Text-only candidate: no matching AnimeStudio cutscene asset, source link, or narrative video was found.",
            })
        if cutscene.get("actorLabels"):
            summary_rows.append({
                "text": "Actors: " + ", ".join(cutscene["actorLabels"]),
            })
        flags: list[str] = []
        if cutscene.get("isTransition"):
            flags.append("transition")
        if cutscene.get("useBlackScreen"):
            flags.append("black-screen")
        if cutscene.get("hasSubtitleTrack"):
            flags.append("subtitle-track")
        if cutscene.get("keepCameraPaths"):
            flags.append("keep-camera")
        if flags:
            summary_rows.append({"text": "Flags: " + ", ".join(flags)})
        if (
            lines
            and not cutscene.get("hasSubtitleTrack")
            and (
                cutscene_key in timeline_bound_cutscene_video_keys
                or fmv_clips_by_key.get(cutscene_key)
            )
        ):
            summary_rows.append({
                "text": "Text rows: TextTable name matches only; no decoded subtitle track ties these rows to the FMV timeline.",
            })
        if lines:
            summary_rows.append({"text": f"TextTable rows: {len(lines)} localized cutscene text row(s)"})
        if len(text_groups) > 1:
            summary_rows.append({"text": "Text groups: " + ", ".join(text_groups[:8])})
        payload = {
            "key": cutscene_key,
            "kind": "cutscene",
            "mission": mission,
            "scene": scene,
            "lines": lines,
            "summary": summary_rows,
            "cutscene": {
                "variants": cutscene.get("variants") or [],
                "levels": cutscene.get("levels") or [],
                "actorLabels": cutscene.get("actorLabels") or [],
                "paths": cutscene.get("paths") or [],
                "versions": cutscene.get("versions") or [],
                "audioEvents": cutscene.get("audioEvents") or [],
                "tags": cutscene.get("tags") or [],
                "textGroups": text_groups,
                "metadata": cutscene.get("metadata") or {},
                "componentCounts": cutscene.get("componentCounts") or {},
                "variantCount": len(cutscene.get("variants") or []),
                "keepCameraPaths": cutscene.get("keepCameraPaths") or [],
                "useBlackScreen": bool(cutscene.get("useBlackScreen")),
                "isTransition": bool(cutscene.get("isTransition")),
                "hasSubtitleTrack": bool(cutscene.get("hasSubtitleTrack")),
                "suppressedTextOnlyGroups": cutscene.get("suppressedTextOnlyGroups") or [],
                "textOnlyUnconfirmed": bool(cutscene.get("textOnlyUnconfirmed")),
            },
            "_debug": {
                "title": mission_name_trace(mission),
                "source": {
                    "canonicalKey": cutscene_key,
                    "variants": cutscene.get("variants") or [],
                },
            },
        }
        if fmv_clips_by_key.get(cutscene_key):
            payload["fmvClips"] = fmv_clips_by_key[cutscene_key]
        write_conv_payload(cutscene_key, payload)
        cutscene_out_keys.add(cutscene_key)
        search_text = " ".join(part for part in [
            cutscene_key,
            mission,
            scene,
            " ".join(cutscene.get("levels") or []),
            " ".join(cutscene.get("actorLabels") or []),
            " ".join(cutscene.get("paths") or []),
            " ".join(cutscene.get("audioEvents") or []),
            " ".join(cutscene.get("tags") or []),
            " ".join(text_groups),
            indexed_line_haystack(lines, "text"),
            component_summary,
            " ".join(variant["name"] for variant in (cutscene.get("variants") or [])),
            " ".join(cutscene.get("keepCameraPaths") or []),
            " ".join(
                str(group.get("key") or "")
                for group in (cutscene.get("suppressedTextOnlyGroups") or [])
            ),
        ] if part)
        line_preview = next((line.get("text") or "" for line in lines if line.get("text")), "")
        entry = {
            "k": cutscene_key,
            "d": "cutscene",
            "m": mission,
            "s": scene_sort_value(scene),
            "t": type_,
            "a": act,
            "c": [],
            "n": len(lines),
            "p": preview(line_preview or " | ".join(part for part in (
                component_summary,
                (cutscene.get("paths") or [""])[0] if cutscene.get("paths") else "",
                (", ".join(cutscene.get("levels") or []) if cutscene.get("levels") else ""),
                (", ".join(cutscene.get("actorLabels")[:3]) if cutscene.get("actorLabels") else ""),
            ) if part)),
            "tags": [
                "cutscene",
                *(["cutsceneText"] if lines else []),
                *(["cutsceneTextCandidate"] if cutscene.get("textOnlyUnconfirmed") else []),
            ],
        }
        if search_text:
            entry["x"] = search_text
        entry["x"] = merge_search_text(entry.get("x", ""), mission_context_text(mission))
        if not entry["x"]:
            entry.pop("x")
        index_entries.append(entry)
    env_talk_speaker_hints_by_env: dict[str, list[dict]] = defaultdict(list)
    for env_id, proxy_ids in env_talk_proxy_ids_by_env.items():
        seen_hint_keys: set[tuple[str, str]] = set()
        for proxy_id in proxy_ids:
            row_id, proxy_row = npc_proxy_rows_by_proxy_id.get(proxy_id, ("", {}))
            proxy_info = npc_proxy_info.get(proxy_id) if isinstance(npc_proxy_info, dict) else None
            candidates = [*npc_proxy_actor_candidates(proxy_id), proxy_id]
            actor_id = ""
            speaker_name = ""
            for candidate in _unique_preserve(candidates):
                actor_id = speaker_actor_id(candidate) or (candidate if candidate in actor_names else "")
                speaker_name = speaker_display_name(candidate)
                if speaker_name:
                    break
            if not speaker_name and isinstance(proxy_row, dict):
                override_name_key = str(((proxy_row.get("overrideNpcNameId") or {}).get("key")) or "")
                if proxy_row.get("ifOverrideNpcName") and override_name_key:
                    speaker_name = named_text(override_name_key)
                    actor_id = actor_id or proxy_id
            if not speaker_name:
                continue
            hint_key = (actor_id or proxy_id, speaker_name)
            if hint_key in seen_hint_keys:
                continue
            seen_hint_keys.add(hint_key)
            env_talk_speaker_hints_by_env[env_id].append({
                "actorId": actor_id or proxy_id,
                "speakerName": speaker_name,
                "proxyId": proxy_id,
                "source": {
                    "table": "NpcProxyTable",
                    "rowId": row_id or proxy_id,
                    "fields": pick_fields(
                        proxy_row if isinstance(proxy_row, dict) else {},
                        "proxyId",
                        "levelId",
                        "envTalkIds",
                        "ifOverrideNpcName",
                        "overrideNpcNameId",
                    ),
                    "proxyInfoData": pick_fields(
                        proxy_info if isinstance(proxy_info, dict) else {},
                        "npcId",
                        "npcNameId",
                        "mapId",
                        "npcProxyType",
                    ),
                },
            })
    # Emit environment conversations
    print(f"Writing {len(env_talks)} environment conversations...")
    for env_id in sorted(env_talks):
        entry = env_talks[env_id]
        env_npc = env_npc_meta.get(env_id)
        env_speaker_hints = env_talk_speaker_hints_by_env.get(env_id) or []
        lines = []
        actors: set[str] = set()
        prev_text = ""
        for item in sorted(entry.get("envTalkDataList", []) or [], key=lambda x: x.get("index", 0)):
            raw_actor_id = str(item.get("actorId") or "").strip()
            raw_actor_name = speaker_display_name(raw_actor_id)
            speaker_hint = env_speaker_hints[0] if env_speaker_hints and not raw_actor_name else None
            actor_id = (
                (raw_actor_id if raw_actor_name or not speaker_hint else "")
                or ((speaker_hint or {}).get("actorId") if speaker_hint else "")
                or raw_actor_id
                or (env_npc.get("npcId") if env_npc else "")
                or ""
            )
            actor = (
                raw_actor_name
                or ((speaker_hint or {}).get("speakerName") if speaker_hint else "")
                or speaker_display_name(actor_id)
                or (env_npc.get("name") if env_npc else "")
                or (env_npc.get("title") if env_npc else "")
            )
            text = t(item.get("text", {}).get("id"))
            audio = item.get("audio") or ""
            emoji = item.get("emojiId") or ""
            duration = item.get("duration")
            slot = item.get("slotId")
            index = item.get("index")
            if actor_id:
                actors.add(actor_id)
            lines.append({
                "id": item.get("envTalkId") or env_id,
                "cid": index,
                "aid": actor_id,
                "actor": actor,
                "text": text,
                "audio": audio,
                "emoji": emoji,
                "duration": duration,
                "slot": slot,
                "_debug": {
                    **source_ref(
                        "EnvTalkTable.envTalkDataList",
                        item.get("envTalkId") or env_id,
                        pick_fields(
                            item,
                            "actorId",
                            "audio",
                            "duration",
                            "emojiId",
                            "envTalkId",
                            "index",
                            "slotId",
                            "text",
                        ),
                        nodeId=index,
                    ),
                    "fields": {
                        "text": text_trace(
                            "EnvTalkTable.envTalkDataList",
                            item.get("envTalkId") or env_id,
                            "text",
                            item.get("text"),
                        ),
                    },
                },
            })
            if speaker_hint:
                lines[-1]["_debug"]["speakerHint"] = speaker_hint
            if not prev_text and text:
                prev_text = text
        out_key = f"env_{env_id}"
        kind, mission, mission_type, index_tags = env_index_slot(env_id)
        env_payload = {
            "key": out_key,
            "kind": kind,
            "mission": mission,
            "title": env_id,
            "cooldown": entry.get("envTalkCd"),
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "EnvTalkTable",
                    env_id,
                    pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                ),
            },
        }
        if env_speaker_hints:
            env_payload["_debug"]["speakerHints"] = env_speaker_hints
        if env_npc:
            env_payload["npc"] = env_npc
            env_payload["_debug"]["npc"] = env_npc["_debug"]
        write_conv_payload(out_key, env_payload)
        index_entry = {
            "k": out_key,
            "d": kind,
            "m": mission,
            "s": 0,
            "t": mission_type,
            "a": 0,
            "title": env_id,
            "c": sorted(actors),
            "n": len(lines),
            "p": preview(prev_text),
            "tags": index_tags,
        }
        if (xt := indexed_line_haystack(lines, "text", "actor", "aid", "emoji")):
            index_entry["x"] = xt
        index_entry["x"] = merge_search_text(index_entry.get("x", ""), mission_context_text(mission))
        if not index_entry["x"]:
            index_entry.pop("x")
        index_entries.append(index_entry)
        if story_mission := env_story_missions.get(env_id):
            env_entry = {
                "key": out_key,
                "id": env_id,
                "cooldown": entry.get("envTalkCd"),
                "lines": lines,
                "_debug": {
                    "source": source_ref(
                        "EnvTalkTable",
                        env_id,
                        pick_fields(entry, "envTalkCd", "envTalkDataList", "envTalkId"),
                    ),
                },
            }
            if env_speaker_hints:
                env_entry["_debug"]["speakerHints"] = env_speaker_hints
            if env_npc:
                env_entry["npc"] = env_npc
                env_entry["_debug"]["npc"] = env_npc["_debug"]
            if hints := env_story_binding_hints.get(env_id):
                levels = sorted(hints["levels"])
                proxies = sorted(hints["proxies"])
                if levels or proxies:
                    env_entry["_attachHints"] = {
                        "levels": levels,
                        "proxies": proxies,
                    }
                    env_entry["_debug"]["bindingHints"] = {
                        "source": {
                            "levels": levels,
                            "proxyIds": proxies,
                            "refs": hints["sources"],
                        }
                    }
            story_env_entries_by_mission[story_mission].append(env_entry)
    wiki_category_names: dict[str, str] = {}
    wiki_group_names: dict[str, str] = {}
    wiki_group_to_category: dict[str, str] = {}
    for category_id, category_row in sorted(
        wiki_categories.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        wiki_category_names[category_id] = category_name
        extra_mission_names.setdefault(category_id, category_name)
        group_rows = ((wiki_groups.get(category_id) or {}).get("list") or [])
        for group_row in group_rows:
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or group_id
            wiki_group_names[group_id] = group_name
            wiki_group_to_category[group_id] = category_id
            extra_mission_names.setdefault(group_id, group_name)
    def wiki_category_id(row_id: str, row: dict) -> str:
        group_id = str(row.get("groupId") or "")
        if group_id in wiki_group_to_category:
            return wiki_group_to_category[group_id]
        if row_id.startswith("wiki_tut_"):
            return "wiki_type_tutorial"
        if str(row.get("refMonsterTemplateId") or ""):
            return "wiki_type_monster"
        ref_item_id = str(row.get("refItemId") or "")
        if ref_item_id.startswith("wpn_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_building_"):
            return "wiki_type_building"
        if group_id.startswith("wiki_group_weapon_"):
            return "wiki_type_weapon"
        if group_id.startswith("wiki_group_monster_"):
            return "wiki_type_monster"
        if group_id.startswith("wiki_group_tutorial_"):
            return "wiki_type_tutorial"
        if group_id.startswith("wiki_group_equip_") or group_id.startswith("suit_") or group_id.startswith("domain_"):
            return "wiki_type_equip"
        return "wiki_type_item"
    wiki_text_fingerprints: set[tuple[str, ...]] = set()
    print(f"Writing {len(wiki_entry_data)} wiki entries...")
    for row_id, row in sorted(
        wiki_entry_data.items(),
        key=lambda item: (
            wiki_category_id(item[0], item[1] if isinstance(item[1], dict) else {}),
            str((item[1] or {}).get("groupId") or ""),
            int((item[1] or {}).get("order") or 0),
            item[0],
        ),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "")
        category_id = wiki_category_id(row_id, row)
        category_name = wiki_category_names.get(category_id, category_id)
        group_name = wiki_group_names.get(group_id, group_id or category_name)
        mission_id = group_id or category_id
        if mission_id:
            extra_mission_names.setdefault(mission_id, group_name if group_id else category_name)
        row_desc = t((row.get("desc") or {}).get("id"))
        ref_item_id = str(row.get("refItemId") or "")
        ref_monster_id = str(row.get("refMonsterTemplateId") or "")
        prts_id = str(row.get("prtsId") or "")
        item_row = item_rows.get(ref_item_id) if isinstance(item_rows.get(ref_item_id), dict) else {}
        weapon_row = weapon_basic.get(ref_item_id) if isinstance(weapon_basic.get(ref_item_id), dict) else {}
        enemy_row = (
            enemy_template_display.get(ref_monster_id)
            if isinstance(enemy_template_display.get(ref_monster_id), dict)
            else enemy_display_info.get(ref_monster_id)
            if isinstance(enemy_display_info.get(ref_monster_id), dict)
            else {}
        )
        title = row_id
        lines: list[dict] = []
        summary_rows: list[dict] = []
        seen_texts: set[tuple[str, str]] = set()
        def add_line(line_id: str, text: str, *, hint: str = "", debug: dict | None = None) -> None:
            normalized = (text or "").strip()
            if not normalized:
                return
            key = (hint, normalized)
            if key in seen_texts:
                return
            seen_texts.add(key)
            line = {"id": line_id, "text": normalized}
            if hint:
                line["hint"] = hint
            if debug:
                line["_debug"] = debug
            lines.append(line)
        if category_id in {"wiki_type_item", "wiki_type_equip", "wiki_type_building", "wiki_type_weapon"}:
            title = brace_text(t((item_row.get("name") or {}).get("id"))) or title
            item_desc = t((item_row.get("desc") or {}).get("id"))
            deco_desc = t((item_row.get("decoDesc") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                item_desc,
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name", "obtainWayIds", "rarity", "type")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "desc", item_row.get("desc")),
                    },
                } if item_row else None,
            )
            add_line(
                f"{row_id}_deco",
                deco_desc,
                hint="Flavor",
                debug={
                    **source_ref("ItemTable", ref_item_id, pick_fields(item_row, "desc", "decoDesc", "id", "name")),
                    "fields": {
                        "text": text_trace("ItemTable", ref_item_id, "decoDesc", item_row.get("decoDesc")),
                    },
                } if item_row else None,
            )
            if category_id == "wiki_type_weapon":
                weapon_desc = t((weapon_row.get("weaponDesc") or {}).get("id"))
                add_line(
                    f"{row_id}_weapon",
                    weapon_desc,
                    hint="Weapon",
                    debug={
                        **source_ref("WeaponBasicTable", ref_item_id, pick_fields(weapon_row, "rarity", "weaponDesc", "weaponId", "weaponSkillList", "weaponType")),
                        "fields": {
                            "text": text_trace("WeaponBasicTable", ref_item_id, "weaponDesc", weapon_row.get("weaponDesc")),
                        },
                    } if weapon_row else None,
                )
                if weapon_row.get("weaponSkillList"):
                    summary_rows.append({"text": "Skills: " + ", ".join(str(skill_id) for skill_id in weapon_row.get("weaponSkillList") or [])})
            if item_row.get("rarity") is not None:
                summary_rows.append({"text": f"Rarity: {item_row['rarity']}"})
            if craft_row := (wiki_craft_jump.get(ref_item_id) if isinstance(wiki_craft_jump.get(ref_item_id), dict) else {}):
                if craft_row.get("blueprintId"):
                    summary_rows.append({"text": f"Blueprint: {craft_row['blueprintId']}"})
                if craft_row.get("blackboxId"):
                    summary_rows.append({"text": f"Blackbox: {craft_row['blackboxId']}"})
            if default_craft := str(wiki_default_craft.get(ref_item_id) or ""):
                summary_rows.append({"text": f"Default craft: {default_craft}"})
        elif category_id == "wiki_type_monster":
            title = (
                brace_text(t((enemy_row.get("name") or {}).get("id")))
                or brace_text(t((enemy_row.get("nickname") or {}).get("id")))
                or title
            )
            enemy_desc = t((enemy_row.get("description") or {}).get("id"))
            add_line(
                f"{row_id}_desc",
                enemy_desc,
                debug={
                    **source_ref(
                        "EnemyTemplateDisplayInfoTable",
                        ref_monster_id,
                        pick_fields(enemy_row, "abilityDescIds", "description", "name", "nickname", "templateId"),
                    ),
                    "fields": {
                        "text": text_trace("EnemyTemplateDisplayInfoTable", ref_monster_id, "description", enemy_row.get("description")),
                    },
                } if enemy_row else None,
            )
            nickname = brace_text(t((enemy_row.get("nickname") or {}).get("id")))
            if nickname and nickname != title:
                summary_rows.append({"text": f"Alias: {nickname}"})
            for ability_id in enemy_row.get("abilityDescIds") or []:
                ability_row = enemy_ability_desc.get(ability_id) if isinstance(enemy_ability_desc.get(ability_id), dict) else {}
                ability_name = brace_text(t((ability_row.get("name") or {}).get("id"))) or str(ability_id)
                ability_text = t((ability_row.get("description") or {}).get("id"))
                summary_rows.append({
                    "text": f"Ability: {ability_name}" + (f" - {ability_text}" if ability_text else ""),
                    "_debug": source_ref(
                        "EnemyAbilityDescTable",
                        str(ability_id),
                        pick_fields(ability_row, "abilityId", "description", "name"),
                    ) if ability_row else None,
                })
        elif category_id == "wiki_type_tutorial":
            page_ids = []
            page_ref_row = (
                wiki_tutorial_pages_by_entry.get(row_id)
                if isinstance(wiki_tutorial_pages_by_entry.get(row_id), dict)
                else {}
            )
            page_ids = [str(page_id) for page_id in (page_ref_row.get("pageIds") or []) if str(page_id)]
            page_title_candidates: list[str] = []
            for page_id in page_ids:
                page_row = wiki_tutorial_pages.get(page_id) if isinstance(wiki_tutorial_pages.get(page_id), dict) else {}
                page_title = brace_text(t((page_row.get("title") or {}).get("id")))
                page_text = t((page_row.get("content") or {}).get("id"))
                if page_title:
                    page_title_candidates.append(page_title)
                add_line(
                    page_id,
                    page_text,
                    hint=page_title,
                    debug={
                        **source_ref(
                            "WikiTutorialPageTable",
                            page_id,
                            pick_fields(page_row, "content", "id", "image", "order", "refWikiEntryIds", "title", "tutorialId", "video", "videoDeviceType"),
                        ),
                        "fields": {
                            "title": text_trace("WikiTutorialPageTable", page_id, "title", page_row.get("title")),
                            "text": text_trace("WikiTutorialPageTable", page_id, "content", page_row.get("content")),
                        },
                    } if page_row else None,
                )
                media_bits = []
                if page_row.get("image"):
                    media_bits.append(f"image={page_row['image']}")
                if page_row.get("video"):
                    media_bits.append(f"video={page_row['video']}")
                if media_bits:
                    summary_rows.append({"text": f"{page_title or page_id}: " + ", ".join(media_bits)})
            title = next((candidate for candidate in page_title_candidates if candidate), row_id)
        if row_desc:
            add_line(
                f"{row_id}_wiki",
                row_desc,
                hint="Wiki",
                debug={
                    **source_ref("WikiEntryDataTable", row_id, pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId")),
                    "fields": {
                        "text": text_trace("WikiEntryDataTable", row_id, "desc", row.get("desc")),
                    },
                },
            )
        summary_rows.insert(0, {"text": f"Category: {category_name}"})
        if group_name and group_name != category_name:
            summary_rows.insert(1, {"text": f"Group: {group_name}"})
        if prts_id:
            summary_rows.append({"text": f"PRTS: {prts_id}"})
        if ref_item_id:
            summary_rows.append({"text": f"Ref item: {ref_item_id}"})
        if ref_monster_id:
            summary_rows.append({"text": f"Ref enemy: {ref_monster_id}"})
        wiki_fp = text_sequence_fingerprint(lines)
        if wiki_fp:
            wiki_text_fingerprints.add(wiki_fp)
        payload = {
            "key": row_id,
            "kind": "wiki",
            "mission": mission_id,
            "scene": int(row.get("order") or 0),
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "WikiEntryDataTable",
                    row_id,
                    pick_fields(row, "desc", "groupId", "id", "order", "prtsId", "refItemId", "refMonsterTemplateId"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if group_id:
            payload["_debug"]["group"] = {
                "categoryId": category_id,
                "categoryName": category_name,
                "groupId": group_id,
                "groupName": group_name,
            }
        write_conv_payload(row_id, payload)
        entry = {
            "k": row_id,
            "d": "wiki",
            "m": mission_id,
            "s": int(row.get("order") or 0),
            "t": "wiki",
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", category_id, group_id or category_id],
        }
        search_text = " ".join(
            part
            for part in [
                row_id,
                category_id,
                category_name,
                group_id,
                group_name,
                title,
                row_desc,
                ref_item_id,
                ref_monster_id,
                prts_id,
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    operator_archive_rows = [row for row in character_rows.values() if isinstance(row, dict) and ((row.get("profileRecord") or []) or (row.get("profileVoice") or []))]
    print(f"Writing {len(operator_archive_rows)} operator archive pages...")
    for char_id, row in sorted(
        ((char_id, row) for char_id, row in character_rows.items() if isinstance(row, dict)),
        key=lambda item: (int((item[1] or {}).get("sortOrder") or 0), item[0]),
    ):
        profile_records = [item for item in (row.get("profileRecord") or []) if isinstance(item, dict)]
        profile_voice = [item for item in (row.get("profileVoice") or []) if isinstance(item, dict)]
        if not profile_records and not profile_voice:
            continue
        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        char_name = (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )
        extra_mission_names[char_id] = char_name
        title = char_name
        summary_rows: list[dict] = []
        summary_rows.append({"text": f"Profile sections: {len(profile_records)}"})
        summary_rows.append({"text": f"Voice entries: {len(profile_voice)}"})
        if department := str(row.get("department") or ""):
            summary_rows.append({"text": f"Department: {department}"})
        if cv_name := brace_text(t((((row.get("cvName") or {}).get("ChiCVName") or {}).get("id")))):
            summary_rows.append({"text": f"CV: {cv_name}"})
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if char_type := str(row.get("charTypeId") or ""):
            summary_rows.append({"text": f"Type: {char_type}"})
        if weapon_type := row.get("weaponType"):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            weapon_item_row = item_rows.get(default_weapon_id) if isinstance(item_rows.get(default_weapon_id), dict) else {}
            weapon_name = brace_text(t((weapon_item_row.get("name") or {}).get("id"))) or default_weapon_id
            summary_rows.append({"text": f"Default weapon: {weapon_name}"})
        lines: list[dict] = []
        for record in sorted(profile_records, key=lambda item: (int(item.get("recordIndex") or 0), str(item.get("id") or ""))):
            record_text = t((record.get("recordDesc") or {}).get("id"))
            if not record_text:
                continue
            record_title = brace_text(t((record.get("recordTitle") or {}).get("id"))) or str(record.get("recordID") or record.get("id") or "")
            lines.append({
                "id": str(record.get("id") or record.get("recordID") or f"{char_id}_record"),
                "text": record_text,
                "hint": record_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileRecord",
                        char_id,
                        pick_fields(record, "charId", "id", "recordDesc", "recordID", "recordIndex", "recordTitle", "unlockType", "unlockValue"),
                        nodeId=record.get("recordIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordTitle", record.get("recordTitle")),
                        "text": text_trace("CharacterTable.profileRecord", str(record.get("id") or char_id), "recordDesc", record.get("recordDesc")),
                    },
                },
            })
        for voice in sorted(profile_voice, key=lambda item: (int(item.get("voiceIndex") or 0), str(item.get("id") or ""))):
            voice_id = str(voice.get("voId") or "").strip()
            voice_text = t((voice.get("voiceDesc") or {}).get("id"))
            if not voice_text and not voice_id:
                continue
            voice_title = brace_text(t((voice.get("voiceTitle") or {}).get("id"))) or str(voice_id or voice.get("id") or "")
            line = {
                "id": str(voice.get("id") or voice.get("voId") or f"{char_id}_voice"),
                "aid": actor_id,
                "actor": char_name,
                "text": voice_text,
                "hint": voice_title,
                "_debug": {
                    **source_ref(
                        "CharacterTable.profileVoice",
                        char_id,
                        pick_fields(voice, "charId", "id", "unlockType", "unlockValue", "voId", "voiceDesc", "voiceIndex", "voiceTitle"),
                        nodeId=voice.get("voiceIndex"),
                    ),
                    "fields": {
                        "title": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceTitle", voice.get("voiceTitle")),
                        "text": text_trace("CharacterTable.profileVoice", str(voice.get("id") or char_id), "voiceDesc", voice.get("voiceDesc")),
                    },
                },
            }
            if voice_id:
                line["voice"] = voice_id
            lines.append(line)
        if not lines:
            continue
        out_key = f"wiki_{char_id}"
        payload = {
            "key": out_key,
            "kind": "table_charactertable",
            "mission": char_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "CharacterTable",
                    char_id,
                    pick_fields(row, "charId", "cvName", "defaultWeaponId", "department", "name", "profileRecord", "profileVoice", "rarity", "sortOrder"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "table_charactertable",
            "m": char_id,
            "s": 0,
            "t": "table_charactertable",
            "a": 0,
            "title": title,
            "c": [actor_id] if actor_id else [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": ["wiki", "character", "archive", "table_charactertable"],
        }
        search_text = " ".join(
            part
            for part in [
                char_id,
                actor_id,
                char_name,
                str(row.get("department") or ""),
                str(row.get("charTypeId") or ""),
                str(row.get("defaultWeaponId") or ""),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)

    story_reference_only_tags = {
        "achievement",
        "enemyAbility",
        "errorCode",
        "gameMechanic",
        "growth",
        "skillPatch",
        "snsChat",
        "tip",
    }

    def write_reference_page(
        out_key: str,
        mission_id: str,
        scene: int,
        title: str,
        lines: list[dict],
        *,
        kind: str | None = None,
        type_key: str | None = None,
        source_debug: dict | None = None,
        summary_rows: list[dict] | None = None,
        tags: list[str] | None = None,
        search_parts: list[str] | None = None,
        actors: list[str] | None = None,
        preview_text: str | None = None,
        debug_extra: dict | None = None,
    ) -> None:
        if not title and not lines and not summary_rows:
            return
        raw_tags = [str(tag or "") for tag in (tags or ["wiki"]) if str(tag or "")]
        if (
            not include_reference_in_story_index
            and story_reference_only_tags & set(raw_tags)
        ):
            return
        entry_tags = normalized_reference_tags(raw_tags, mission_id)
        ref_kind = str(kind or reference_kind_from_tags(tags))
        ref_type = str(type_key or ref_kind)
        payload = {
            "key": out_key,
            "kind": ref_kind,
            "mission": mission_id,
            "scene": scene,
            "title": title or out_key,
            "lines": lines,
            "_debug": {},
        }
        if source_debug:
            payload["_debug"]["source"] = source_debug
        if summary_rows:
            payload["summary"] = summary_rows
        if debug_extra:
            payload["_debug"].update(debug_extra)
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": ref_kind,
            "m": mission_id,
            "s": scene,
            "t": ref_type,
            "a": 0,
            "title": title or out_key,
            "c": list(actors or []),
            "n": len(lines),
            "p": preview(
                preview_text
                or next((line.get("text") or "" for line in lines if line.get("text")), title or out_key)
            ),
            "tags": entry_tags,
        }
        search_text = " ".join(
            part
            for part in [
                *(search_parts or []),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("actor") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
                " ".join(row.get("text") or "" for row in (summary_rows or [])),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    def character_page_title(char_id: str) -> str:
        row = character_rows.get(char_id) if isinstance(character_rows.get(char_id), dict) else {}
        actor_id = char_id.split("_", 2)[-1] if char_id.startswith("chr_") else char_id
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or speaker_display_name(actor_id)
            or speaker_display_name(char_id)
            or char_id
        )

    def collection_hint_from_path(path: str) -> str:
        tokens: list[str] = []
        raw = str(path or "")
        if raw.startswith("$."):
            raw = raw[2:]
        elif raw == "$":
            raw = ""
        for piece in [part for part in raw.split(".") if part]:
            base = re.sub(r"\[\d+\]", "", piece)
            idx_matches = [int(match) + 1 for match in re.findall(r"\[(\d+)\]", piece)]
            label = collection_display_name(base)
            if idx_matches:
                label = f"{label} {idx_matches[-1]}"
            if label:
                tokens.append(label)
        return " / ".join(tokens[-2:])

    def collection_bucket(table_name: str, row_id: str, row: dict | None) -> str:
        if table_name == "CommonDeathTips.json":
            return "common_death_tips"
        if table_name == "DisplayEnemyTypeTable.json":
            return "display_enemy_type"
        if table_name == "TextTable.json":
            return collection_bucket_from_key(row_id)
        if isinstance(row, dict):
            for field in (
                "groupId",
                "categoryId",
                "formulaGroupId",
                "gameCategory",
                "machineId",
                "owner",
                "charId",
                "charTypeId",
                "profession",
                "weaponType",
                "roomType",
                "pageType",
                "tagType",
                "type",
            ):
                value = row.get(field)
                if isinstance(value, str) and value and len(value) <= 48:
                    return value
                if isinstance(value, int | float) and field in {"roomType", "pageType", "tagType"}:
                    return f"{field}_{int(value)}"
        return collection_bucket_from_key(row_id)
    def collection_reading_story_ref(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> tuple[str, int, str] | None:
        if table_name not in {"PrtsReading.json", "ReadingPopUpTable.json", "RichContentTable.json"}:
            return None
        candidates: list[str] = []
        if table_name == "PrtsReading.json" and isinstance(row, dict):
            items = row.get("list") or {}
            if isinstance(items, dict):
                sorted_items = sorted(
                    ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                    key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
                )
                for _node_id, node in sorted_items:
                    content_id = str(node.get("contentId") or "").strip()
                    if content_id:
                        candidates.append(content_id)
        elif table_name == "ReadingPopUpTable.json" and isinstance(row, dict):
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                candidates.append(content_id)
        elif table_name == "RichContentTable.json" and isinstance(row, dict):
            title_text = rich_content_title_text(str(row_id or ""))
            if title_text:
                candidates.append(title_text)
        candidates.append(str(row_id or ""))
        return (
            collection_story_ref_from_identifiers(*candidates)
            or collection_map_ref_from_identifiers(*candidates)
        )
    collection_story_mission_pattern = re.compile(
        r"(?<![a-z0-9])((?:gm|sm|db|dm|[acefm])\d+(?:[a-z]\d+)*(?:d\d+)?)(?![a-z0-9])",
        re.IGNORECASE,
    )
    collection_map_pattern = re.compile(r"map\d+_lv\d+", re.IGNORECASE)

    def collection_story_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if lowered.startswith("topic_"):
                return (value, 0, "topic")
            if lowered.startswith("sr_"):
                return (value, 0, "f")
            if match := collection_story_mission_pattern.findall(lowered):
                mission_id = match[-1]
                type_key, _act = parse_mission(mission_id)
                if type_key in MISSION_STORY_TYPES:
                    return (mission_id, collection_scene_suffix(value), type_key)
        return None
    def collection_map_ref_from_identifiers(*values: str) -> tuple[str, int, str] | None:
        for raw_value in values:
            value = str(raw_value or "").strip()
            if not value:
                continue
            lowered = value.lower()
            if match := collection_map_pattern.findall(lowered):
                return (match[-1], collection_scene_suffix(value), "map")
        return None
    def collection_story_ref_from_bucket(bucket: str) -> tuple[str, int, str] | None:
        candidates: set[str] = set()
        for match in collection_story_mission_pattern.finditer(str(bucket or "").lower()):
            mission_id = match.group(1)
            type_key, _act = parse_mission(mission_id)
            if type_key in MISSION_STORY_TYPES:
                candidates.add(mission_id)
        if len(candidates) != 1:
            return None
        mission_id = next(iter(candidates))
        type_key, _act = parse_mission(mission_id)
        return (mission_id, 0, type_key)
    def collection_bucket_token(bucket: str) -> str:
        slug = collection_slug(bucket)
        checksum = sum((idx + 1) * ord(ch) for idx, ch in enumerate(str(bucket or ""))) % 104729
        return f"{slug}_{checksum:x}" if checksum else slug


    prts_archive_categories = ("collection", "digital", "document", "media", "paper", "report")
    def prts_archive_category_from_identifier(value) -> str:
        raw = re.sub(r"[^0-9A-Za-z]+", "_", str(value or "")).strip("_").lower()
        if not raw:
            return ""
        if raw.startswith("nar_"):
            raw = raw[4:]
        if raw.startswith("multi_media"):
            return "media"
        for category_key in prts_archive_categories:
            if raw == category_key or raw.startswith(f"{category_key}_"):
                return category_key
        return ""
    def prts_archive_category_from_collection_ids(collection_ids) -> str:
        counts: dict[str, int] = {}
        first_seen: dict[str, int] = {}
        for idx, raw_id in enumerate(collection_ids or []):
            category_key = prts_archive_category_from_identifier(raw_id)
            if not category_key:
                continue
            counts[category_key] = counts.get(category_key, 0) + 1
            first_seen.setdefault(category_key, idx)
        if not counts:
            return ""
        return min(
            counts,
            key=lambda category_key: (-counts[category_key], first_seen.get(category_key, 0), category_key),
        )
    def prts_archive_category_from_row(
        table_name: str,
        row_id: str,
        row: dict | None,
    ) -> str:
        if table_name == "PrtsCategory.json":
            if isinstance(row, dict):
                return prts_archive_category_from_identifier(row.get("categoryId"))
            return prts_archive_category_from_identifier(row_id)
        if isinstance(row, dict):
            for field in ("categoryId", "firstLvId", "id", "type"):
                category_key = prts_archive_category_from_identifier(row.get(field))
                if category_key:
                    return category_key
            if table_name in {"PrtsInvestigate.json", "PrtsInvestigateCategory.json"}:
                collection_ids: list[str] = []
                for field in ("collectionIdList",):
                    values = row.get(field) or []
                    if isinstance(values, list):
                        collection_ids.extend(str(value) for value in values if str(value))
                for field in ("categoryDataList", "list"):
                    groups = row.get(field) or []
                    if not isinstance(groups, list):
                        continue
                    for group_row in groups:
                        if not isinstance(group_row, dict):
                            continue
                        values = group_row.get("collectionIdList") or []
                        if isinstance(values, list):
                            collection_ids.extend(str(value) for value in values if str(value))
                category_key = prts_archive_category_from_collection_ids(collection_ids)
                if category_key:
                    return category_key
        return prts_archive_category_from_identifier(row_id)
    def prts_category_display_name(category_key: str) -> str:
        row = prts_categories.get(category_key) if isinstance(prts_categories.get(category_key), dict) else {}
        return (
            brace_text(t((row.get("name") or {}).get("id")))
            or str(category_key or "").replace("_", " ").strip().title()
        )
    prts_note_metadata: dict[str, dict] = {}
    for research_id, research_row in sorted(prts_investigate_categories.items()):
        if not isinstance(research_row, dict):
            continue
        for list_index, list_row in enumerate(research_row.get("list") or [], start=1):
            if not isinstance(list_row, dict):
                continue
            note_title = brace_text(t((list_row.get("name") or {}).get("id")))
            category_key = prts_archive_category_from_collection_ids(list_row.get("collectionIdList") or [])
            collection_ids = [
                str(value)
                for value in (list_row.get("collectionIdList") or [])
                if str(value)
            ]
            for note_id in (list_row.get("noteIdList") or []):
                note_key = str(note_id or "").strip()
                if not note_key:
                    continue
                meta = prts_note_metadata.setdefault(note_key, {})
                if note_title and not meta.get("title"):
                    meta["title"] = note_title
                if category_key and not meta.get("category"):
                    meta["category"] = category_key
                meta.setdefault("researchId", str(research_id))
                meta.setdefault("index", int(list_row.get("index") or list_index))
                if collection_ids and not meta.get("collectionIds"):
                    meta["collectionIds"] = list(collection_ids)
    prts_content_ids = {
        str((row or {}).get("contentId") or "")
        for row in prts_all_items.values()
        if isinstance(row, dict) and str((row or {}).get("contentId") or "")
    }
    prts_investigate_metadata_by_unlock_prts: dict[str, list[dict]] = defaultdict(list)
    for research_id, research_row in sorted(load("PrtsInvestigate.json").items()):
        if not isinstance(research_row, dict):
            continue
        unlock_prts = str(research_row.get("unlockPrts") or "").strip()
        if not unlock_prts:
            continue
        research_name = brace_text(t((research_row.get("name") or {}).get("id")))
        research_desc = t((research_row.get("desc") or {}).get("id"))
        if not research_name and not research_desc:
            continue
        prts_investigate_metadata_by_unlock_prts[unlock_prts].append({
            "researchId": str(research_id),
            "title": research_name,
            "desc": research_desc,
        })
    def collection_tags(
        table_name: str,
        row_id: str,
        bucket: str,
        row: dict | None = None,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[str]:
        stem = table_name.removesuffix(".json")
        tags = [
            "wiki",
            "collection",
            f"table_{collection_slug(stem)}",
            f"source_{collection_slug(table_source)}",
        ]
        lower = stem.lower()
        for needle, tag in (
            ("activity", "activity"),
            ("achievement", "achievement"),
            ("battlepass", "battlePass"),
            ("char", "character"),
            ("dungeon", "dungeon"),
            ("enemy", "enemy"),
            ("factory", "factory"),
            ("item", "item"),
            ("jump", "systemJump"),
            ("mail", "mail"),
            ("money", "money"),
            ("picture", "picture"),
            ("radio", "radio"),
            ("skill", "skill"),
            ("system", "system"),
            ("task", "other"),
            ("tip", "other"),
            ("weapon", "weapon"),
        ):
            if tag == "system" and lower.startswith("systemjump"):
                continue
            if needle in lower and tag not in tags:
                tags.append(tag)
        if variant:
            tags.append("variant")
        bucket_slug = collection_slug(bucket)
        if bucket_slug and bucket_slug != "misc":
            tags.append(f"group_{bucket_slug}")
        if isinstance(row, dict):
            if isinstance(row.get("groupId"), str) and row.get("groupId"):
                tags.append(f"group_{collection_slug(row['groupId'])}")
            if isinstance(row.get("categoryId"), str) and row.get("categoryId"):
                tags.append(f"category_{collection_slug(row['categoryId'])}")
        prts_category_key = prts_archive_category_from_row(table_name, row_id, row)
        if prts_category_key:
            tags.append(f"category_{collection_slug(prts_category_key)}")
        deduped: list[str] = []
        for tag in tags:
            if tag not in deduped:
                deduped.append(tag)
        return deduped
    def collect_reference_text_nodes(
        table_name: str,
        row_id: str,
        raw_value,
        *,
        preferred_source: str = "streaming",
        path: str = "$",
        out: list[dict] | None = None,
    ) -> list[dict]:
        if out is None:
            out = []
        if isinstance(raw_value, dict):
            if "id" in raw_value and "text" in raw_value:
                text = t(raw_value.get("id"), preferred_source=preferred_source)
                if text:
                    field_name = re.sub(r"\[\d+\]", "", path.rsplit(".", 1)[-1] if "." in path else path)
                    out.append({
                        "field": field_name or "text",
                        "hint": collection_hint_from_path(path),
                        "path": path,
                        "raw": raw_value,
                        "text": text,
                    })
            for key, value in raw_value.items():
                child_path = f"{path}.{key}" if path != "$" else f"$.{key}"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
            return out
        if isinstance(raw_value, list):
            for idx, value in enumerate(raw_value):
                child_path = f"{path}[{idx}]"
                collect_reference_text_nodes(
                    table_name,
                    row_id,
                    value,
                    preferred_source=preferred_source,
                    path=child_path,
                    out=out,
                )
        return out
    def collection_row_title(
        table_name: str,
        row_id: str,
        text_nodes: list[dict],
        *,
        preferred_source: str = "streaming",
    ) -> str:
        preferred_fields = {
            "name",
            "title",
            "talentName",
            "gameName",
            "dungeonName",
            "tipsTitle",
            "topicName",
            "recordTitle",
            "voiceTitle",
            "iconDesc",
            "effectTitle",
        }
        for node in text_nodes:
            if node.get("field") in preferred_fields:
                return brace_text(node.get("text") or "") or (node.get("text") or "")
        if table_name == "TextTable.json":
            return row_id
        return row_id
    def collection_summary_rows(
        table_name: str,
        row_id: str,
        row: dict | None,
        bucket: str,
        *,
        table_source: str = "streaming",
        variant: bool = False,
    ) -> list[dict]:
        rows = [
            {"text": f"Table: {collection_display_name(table_name.removesuffix('.json'))}"},
            {"text": f"Row: {row_id}"},
        ]
        if table_source != "streaming":
            rows.append({"text": f"Source: {collection_source_label(table_source)}"})
        if variant:
            rows.append({"text": "Variant: differs from StreamingAssets row"})
        bucket_label = collection_display_name(bucket)
        if bucket_label and bucket_label != "Misc":
            rows.append({"text": f"Group: {bucket_label}"})
        if isinstance(row, dict):
            for field in ("groupId", "categoryId", "type", "gameCategory", "profession", "weaponType", "machineId", "roomType", "unlockMissionId"):
                value = row.get(field)
                if value in (None, "", [], {}):
                    continue
                if isinstance(value, list):
                    preview_value = ", ".join(str(item) for item in value[:4])
                    if len(value) > 4:
                        preview_value += ", ..."
                else:
                    preview_value = str(value)
                rows.append({"text": f"{collection_display_name(field)}: {preview_value}"})
                if len(rows) >= 6:
                    break
        return rows
    def collect_exported_texttable_row_ids() -> set[str]:
        referenced = set(referenced_texttable_row_ids)
        def visit(value) -> None:
            if isinstance(value, dict):
                if value.get("table") == "TextTable" and value.get("rowId"):
                    remember_texttable_row_usage(value.get("rowId"))
                    referenced.add(str(value.get("rowId")))
                for nested in value.values():
                    visit(nested)
                return
            if isinstance(value, list):
                for nested in value:
                    visit(nested)
        for conv_path in sorted(written_conv_paths):
            if conv_path.stem.startswith("wiki_collection_texttable_"):
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            visit(payload)
        return referenced
    def write_texttable_collection_pages(excluded_row_ids: set[str] | None = None) -> None:
        excluded = {str(row_id) for row_id in (excluded_row_ids or set()) if str(row_id or "").strip()}
        chunks_by_bucket: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for row_id, row in sorted(text_table.items()):
            if not isinstance(row, dict):
                continue
            if row_id in excluded:
                continue
            text = t(row.get("id"))
            if not text:
                continue
            chunks_by_bucket[collection_bucket("TextTable.json", row_id, row)].append((row_id, row))
        total_pages = 0
        total_rows = 0
        chunk_size = 200
        for bucket, entries in sorted(chunks_by_bucket.items()):
            total_rows += len(entries)
            bucket_token = collection_bucket_token(bucket)
            story_ref = collection_story_ref_from_bucket(bucket)
            if story_ref:
                mission_id, _forced_scene_value, forced_type_key = story_ref
                extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
            else:
                mission_id = f"wiki_collection_texttable_{bucket_token}"
                forced_type_key = None
            for chunk_index, start in enumerate(range(0, len(entries), chunk_size), start=1):
                chunk = entries[start:start + chunk_size]
                lines: list[dict] = []
                for row_id, row in chunk:
                    text = t(row.get("id"))
                    if not text:
                        continue
                    lines.append({
                        "id": row_id,
                        "text": text,
                        "hint": row_id,
                        "_debug": {
                            **source_ref("TextTable", row_id, pick_fields(row, "id")),
                            "fields": {
                                "text": text_trace("TextTable", row_id, "id", row.get("id")),
                            },
                        },
                    })
                if not lines:
                    continue
                total_pages += 1
                title = f"TextTable / {collection_display_name(bucket)}"
                if len(entries) > chunk_size:
                    title += f" ({chunk_index})"
                out_key = f"wiki_collection_texttable_{bucket_token}_{chunk_index}"
                summary_rows = [
                    {"text": "Table: TextTable"},
                    {"text": f"Group: {collection_display_name(bucket)}"},
                    {"text": f"Entries: {len(lines)}"},
                ]
                write_reference_page(
                    out_key,
                    mission_id,
                    chunk_index,
                    title,
                    lines,
                    type_key=forced_type_key,
                    source_debug=source_ref("TextTable", bucket_token, {"entries": len(lines), "bucket": bucket}),
                    summary_rows=summary_rows,
                    tags=["wiki", "collection", "table_texttable", "source_streaming", f"group_{bucket_token}", "text"],
                    search_parts=[bucket, title, " ".join(line["id"] for line in lines[:50])],
                )
        skipped_rows = len(excluded & {str(row_id) for row_id in text_table})
        print(
            f"Writing {total_pages} text-table collection pages for {total_rows} entries "
            f"({skipped_rows} referenced rows skipped)..."
        )
    print(f"Writing {len(skill_patches)} skill patch reference pages...")
    for skill_id, row in sorted(skill_patches.items()):
        if not isinstance(row, dict):
            continue
        bundles = [bundle for bundle in (row.get("SkillPatchDataBundle") or []) if isinstance(bundle, dict)]
        if not bundles:
            continue
        title = next(
            (
                brace_text(t((bundle.get("skillName") or {}).get("id")))
                for bundle in bundles
                if brace_text(t((bundle.get("skillName") or {}).get("id")))
            ),
            skill_id,
        )
        summary_rows: list[dict] = []
        level_count = len([bundle for bundle in bundles if int(bundle.get("level") or 0) > 0])
        if level_count:
            summary_rows.append({"text": f"Levels: {level_count}"})
        icon_id = next((str(bundle.get("iconId") or "") for bundle in bundles if str(bundle.get("iconId") or "")), "")
        if icon_id:
            summary_rows.append({"text": f"Icon: {icon_id}"})
        tag_id = next((str(bundle.get("tagId") or "") for bundle in bundles if str(bundle.get("tagId") or "")), "")
        if tag_id:
            summary_rows.append({"text": f"Tag: {tag_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for bundle in sorted(bundles, key=lambda item: (int(item.get("level") or 0), str(item.get("skillId") or skill_id))):
            level = int(bundle.get("level") or 0)
            level_hint = f"Level {level}" if level else ""
            description = t((bundle.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{skill_id}_desc_{level}",
                description,
                hint=level_hint,
                debug={
                    **source_ref(
                        "SkillPatchTable.SkillPatchDataBundle",
                        skill_id,
                        pick_fields(bundle, "coolDown", "description", "iconId", "level", "skillId", "skillName", "subDescList", "subDescNameList", "tagId"),
                        nodeId=level,
                    ),
                    "fields": {
                        "title": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "skillName", bundle.get("skillName")),
                        "text": text_trace("SkillPatchTable.SkillPatchDataBundle", skill_id, "description", bundle.get("description")),
                    },
                } if description else None,
            )
            raw_sub_names = bundle.get("subDescNameList") or []
            raw_sub_values = bundle.get("subDescList") or []
            for idx, raw_name in enumerate(raw_sub_names, start=1):
                label = t((raw_name or {}).get("id"))
                if not label:
                    continue
                value = str(raw_sub_values[idx - 1] or "").strip() if idx - 1 < len(raw_sub_values) else ""
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{skill_id}_sub_{level}_{idx}",
                    label,
                    hint=" ".join(part for part in [level_hint, value] if part),
                    debug={
                        **source_ref(
                            "SkillPatchTable.SkillPatchDataBundle",
                            skill_id,
                            pick_fields(bundle, "level", "skillId", "subDescList", "subDescNameList"),
                            nodeId=level,
                            nodeIndex=idx - 1,
                        ),
                        "fields": {
                            "text": text_trace(
                                "SkillPatchTable.SkillPatchDataBundle",
                                skill_id,
                                f"subDescNameList[{idx - 1}]",
                                raw_name,
                            ),
                        },
                    },
                )
        if title == skill_id and not lines:
            continue
        write_reference_page(
            f"wiki_skill_{skill_id}",
            "SkillPatchTable",
            0,
            title,
            lines,
            source_debug=source_ref("SkillPatchTable", skill_id, pick_fields(row, "SkillPatchDataBundle")),
            summary_rows=summary_rows,
            tags=["wiki", "skillPatch", "table_skillpatchtable"],
            search_parts=[skill_id, title, tag_id],
        )
    print(f"Writing {len(char_growth)} character growth reference pages...")
    for char_id, row in sorted(char_growth.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or character_page_title(char_id)
        extra_mission_names.setdefault(char_id, title)
        summary_rows: list[dict] = []
        if row.get("rarity") is not None:
            summary_rows.append({"text": f"Rarity: {row['rarity']}"})
        if profession := str(row.get("profession") or ""):
            summary_rows.append({"text": f"Profession: {profession}"})
        if weapon_type := str(row.get("weaponType") or ""):
            summary_rows.append({"text": f"Weapon type: {weapon_type}"})
        if default_weapon_id := str(row.get("defaultWeaponId") or ""):
            summary_rows.append({"text": f"Default weapon: {default_weapon_id}"})
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("charBreakCostMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: (int((item[1] or {}).get("breakStage") or 0), item[0]),
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("description") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.charBreakCostMap",
                        char_id,
                        pick_fields(node, "breakStage", "charId", "description", "equipTierLimit", "name", "nodeId", "nodeType", "requiredItem"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.charBreakCostMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.charBreakCostMap", char_id, "description", node.get("description")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("skillGroupMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            node_name = brace_text(t((node.get("name") or {}).get("id")))
            node_desc = t((node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.skillGroupMap",
                        char_id,
                        pick_fields(node, "desc", "name", "skillId", "skillType", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.skillGroupMap", char_id, "name", node.get("name")),
                        "text": text_trace("CharGrowthTable.skillGroupMap", char_id, "desc", node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        for node_id, node in sorted(
            ((node_id, node) for node_id, node in (row.get("talentNodeMap") or {}).items() if isinstance(node, dict)),
            key=lambda item: item[0],
        ):
            attr_node = node.get("attributeNodeInfo") if isinstance(node.get("attributeNodeInfo"), dict) else {}
            node_name = brace_text(t((attr_node.get("title") or {}).get("id")))
            node_desc = t((attr_node.get("desc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{char_id}_{node_id}",
                node_desc or node_name,
                hint=node_name if node_desc and node_name else "",
                debug={
                    **source_ref(
                        "CharGrowthTable.talentNodeMap",
                        char_id,
                        pick_fields(node, "attributeNodeInfo", "nodeId", "nodeType", "preNodeId", "requiredItem", "unlockLevel"),
                        nodeId=node_id,
                    ),
                    "fields": {
                        "title": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.title", attr_node.get("title")),
                        "text": text_trace("CharGrowthTable.talentNodeMap", char_id, "attributeNodeInfo.desc", attr_node.get("desc")),
                    },
                } if (node_desc or node_name) else None,
            )
        if title == char_id and not lines:
            continue
        write_reference_page(
            f"wiki_growth_{char_id}",
            char_id,
            0,
            title,
            lines,
            source_debug=source_ref(
                "CharGrowthTable",
                char_id,
                pick_fields(row, "charId", "charBreakCostMap", "defaultWeaponId", "name", "profession", "rarity", "skillGroupMap", "talentNodeMap", "weaponType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "character", "growth", "table_chargrowthtable"],
            search_parts=[char_id, title, str(row.get("profession") or ""), str(row.get("weaponType") or "")],
            actors=[char_id.split("_", 2)[-1]] if char_id.startswith("chr_") else [],
        )
    print(f"Writing {len(game_mechanics)} game mechanic reference pages...")
    for mechanic_id, row in sorted(game_mechanics.items()):
        if not isinstance(row, dict):
            continue
        game_category = str(row.get("gameCategory") or "misc")
        mission_id = f"wiki_game_mechanic_{game_category}"
        title = brace_text(t((row.get("gameName") or {}).get("id"))) or mechanic_id
        desc = t((row.get("desc") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            mechanic_id,
            desc,
            debug={
                **source_ref(
                    "GameMechanicTable",
                    mechanic_id,
                    pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
                ),
                "fields": {
                    "title": text_trace("GameMechanicTable", mechanic_id, "gameName", row.get("gameName")),
                    "text": text_trace("GameMechanicTable", mechanic_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        if title == mechanic_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("difficulty") is not None:
            summary_rows.append({"text": f"Difficulty: {row['difficulty']}"})
        if row.get("costStamina") is not None:
            summary_rows.append({"text": f"Stamina: {row['costStamina']}"})
        write_reference_page(
            f"wiki_mechanic_{mechanic_id}",
            mission_id,
            int(row.get("difficulty") or 0),
            title,
            lines,
            source_debug=source_ref(
                "GameMechanicTable",
                mechanic_id,
                pick_fields(row, "conditionIds", "costStamina", "desc", "difficulty", "gameCategory", "gameMechanicsId", "gameName", "rewardId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "gameMechanic", game_category, "table_gamemechanictable"],
            search_parts=[mechanic_id, game_category, title, desc],
        )
    print(f"Writing {len(loading_tips)} loading-tip reference pages...")
    for tip_id, row in sorted(loading_tips.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("tipsTitle") or {}).get("id"))) or tip_id
        text = t((row.get("text") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            tip_id,
            text,
            debug={
                **source_ref(
                    "LoadingTipsTable",
                    tip_id,
                    pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
                ),
                "fields": {
                    "title": text_trace("LoadingTipsTable", tip_id, "tipsTitle", row.get("tipsTitle")),
                    "text": text_trace("LoadingTipsTable", tip_id, "text", row.get("text")),
                },
            } if text else None,
        )
        if title == tip_id and not lines:
            continue
        summary_rows: list[dict] = []
        if unlock_mission := str(row.get("unlockMissionId") or ""):
            summary_rows.append({"text": f"Unlock mission: {unlock_mission}"})
        if row.get("typeTag") is not None:
            summary_rows.append({"text": f"Type: {row['typeTag']}"})
        write_reference_page(
            f"wiki_tip_{tip_id}",
            "LoadingTipsTable",
            int(row.get("typeTag") or 0),
            title,
            lines,
            kind="table_loadingtipstable",
            type_key="table_loadingtipstable",
            source_debug=source_ref(
                "LoadingTipsTable",
                tip_id,
                pick_fields(row, "key", "mapTag", "text", "tipsTitle", "typeTag", "unlockMissionId"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "table_loadingtipstable"],
            search_parts=[tip_id, title, text, str(row.get("unlockMissionId") or "")],
        )
    print(f"Writing {len(error_codes)} error-code reference pages...")
    for code, row in sorted(error_codes.items(), key=lambda item: int(item[0]) if re.fullmatch(r"-?\d+", str(item[0])) else 0):
        if not isinstance(row, dict):
            continue
        text = t((row.get("text") or {}).get("id"))
        if not text:
            continue
        write_reference_page(
            f"wiki_error_{code}",
            "ErrorCodeTable",
            int(code) if re.fullmatch(r"-?\d+", str(code)) else 0,
            str(code),
            [{
                "id": str(code),
                "text": text,
                "_debug": {
                    **source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
                    "fields": {
                        "text": text_trace("ErrorCodeTable", str(code), "text", row.get("text")),
                    },
                },
            }],
            source_debug=source_ref("ErrorCodeTable", str(code), pick_fields(row, "text")),
            tags=["wiki", "errorCode", "table_errorcodetable"],
            search_parts=[str(code), text],
        )
    achievement_group_names: dict[str, str] = {}
    achievement_group_category_ids: dict[str, str] = {}
    achievement_category_names: dict[str, str] = {}
    for category_id, category_row in sorted(
        achievement_types.items(),
        key=lambda item: (int((item[1] or {}).get("categoryPriority") or 0), item[0]),
    ):
        if not isinstance(category_row, dict):
            continue
        category_name = brace_text(t((category_row.get("categoryName") or {}).get("id"))) or category_id
        achievement_category_names[category_id] = category_name
        for group_row in (category_row.get("achievementGroupData") or []):
            if not isinstance(group_row, dict):
                continue
            group_id = str(group_row.get("groupId") or "")
            if not group_id:
                continue
            group_name = brace_text(t((group_row.get("groupName") or {}).get("id"))) or category_name
            achievement_group_names[group_id] = group_name
            achievement_group_category_ids[group_id] = category_id
    def achievement_group_meta(group_id: str) -> tuple[str, str, str]:
        category_id = achievement_group_category_ids.get(group_id, "")
        category_name = achievement_category_names.get(category_id, category_id)
        group_name = achievement_group_names.get(group_id) or category_name or group_id
        return group_name, category_id, category_name
    print(f"Writing {len(achievements)} achievement reference pages...")
    for achieve_id, row in sorted(
        achievements.items(),
        key=lambda item: (str((item[1] or {}).get("groupId") or ""), int((item[1] or {}).get("order") or 0), item[0]),
    ):
        if not isinstance(row, dict):
            continue
        group_id = str(row.get("groupId") or "misc")
        group_name, category_id, category_name = achievement_group_meta(group_id)
        mission_id = f"wiki_achievement_{group_id}"
        extra_mission_names.setdefault(mission_id, group_name)
        title = brace_text(t((row.get("name") or {}).get("id"))) or achieve_id
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        desc = t((row.get("desc") or {}).get("id"))
        append_reference_line(
            lines,
            seen_texts,
            f"{achieve_id}_desc",
            desc,
            hint="Description" if desc else "",
            debug={
                **source_ref("AchievementTable", achieve_id, pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order")),
                "fields": {
                    "title": text_trace("AchievementTable", achieve_id, "name", row.get("name")),
                    "text": text_trace("AchievementTable", achieve_id, "desc", row.get("desc")),
                },
            } if desc else None,
        )
        level_infos = row.get("levelInfos") or {}
        for level_key, level_row in sorted(
            ((level_key, level_row) for level_key, level_row in level_infos.items() if isinstance(level_row, dict)),
            key=lambda item: int(item[0]) if re.fullmatch(r"\d+", str(item[0])) else 0,
        ):
            complete_desc = t((level_row.get("completeDesc") or {}).get("id"))
            append_reference_line(
                lines,
                seen_texts,
                f"{achieve_id}_complete_{level_key}",
                complete_desc,
                hint=f"Level {level_key} completion" if complete_desc else "",
                debug={
                    **source_ref(
                        "AchievementTable.levelInfos",
                        achieve_id,
                        pick_fields(level_row, "achieveLevel", "completeDesc", "conditions"),
                        nodeId=level_key,
                    ),
                    "fields": {
                        "text": text_trace("AchievementTable.levelInfos", achieve_id, "completeDesc", level_row.get("completeDesc")),
                    },
                } if complete_desc else None,
            )
            for idx, condition in enumerate((level_row.get("conditions") or []), start=1):
                if not isinstance(condition, dict):
                    continue
                condition_desc = t((condition.get("desc") or {}).get("id"))
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{achieve_id}_condition_{level_key}_{idx}",
                    condition_desc,
                    hint=f"Level {level_key} condition {idx}" if condition_desc else "",
                    debug={
                        **source_ref(
                            "AchievementTable.levelInfos.conditions",
                            achieve_id,
                            pick_fields(condition, "conditionId", "desc", "progressToCompare"),
                            nodeId=f"{level_key}:{idx}",
                        ),
                        "fields": {
                            "text": text_trace("AchievementTable.levelInfos.conditions", achieve_id, "desc", condition.get("desc")),
                        },
                    } if condition_desc else None,
                )
        if title == achieve_id and not lines:
            continue
        write_reference_page(
            f"wiki_achievement_{achieve_id}",
            mission_id,
            int(row.get("order") or 0),
            title,
            lines,
            source_debug=source_ref(
                "AchievementTable",
                achieve_id,
                pick_fields(row, "achieveId", "desc", "groupId", "levelInfos", "name", "order"),
            ),
            debug_extra={
                "achievementGroup": {
                    "groupId": group_id,
                    "groupName": group_name,
                    "categoryId": category_id,
                    "categoryName": category_name,
                }
            },
            summary_rows=[{"text": f"Levels: {len(level_infos)}"}] if level_infos else None,
            tags=["wiki", "achievement", group_id, "table_achievementtable"],
            search_parts=[achieve_id, group_id, group_name, category_id, category_name, title, desc],
        )
    print(f"Writing {len(sns_chats)} SNS chat reference pages...")
    for chat_id, row in sorted(sns_chats.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or chat_id
        desc = t((row.get("desc") or {}).get("id"))
        tag_label = brace_text(t((row.get("tagLabel") or {}).get("id")))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_desc",
            desc,
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
                ),
                "fields": {
                    "title": text_trace("SNSChatTable", chat_id, "name", row.get("name")),
                    "text": text_trace("SNSChatTable", chat_id, "desc", row.get("desc")),
                    "tag": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if desc else None,
        )
        append_reference_line(
            lines,
            seen_texts,
            f"{chat_id}_tag",
            tag_label,
            hint="Tag" if tag_label else "",
            debug={
                **source_ref(
                    "SNSChatTable",
                    chat_id,
                    pick_fields(row, "chatId", "name", "tagLabel", "tagType"),
                ),
                "fields": {
                    "text": text_trace("SNSChatTable", chat_id, "tagLabel", row.get("tagLabel")),
                },
            } if tag_label else None,
        )
        if title == chat_id and not lines:
            continue
        summary_rows: list[dict] = []
        if row.get("chatType") is not None:
            summary_rows.append({"text": f"Chat type: {row['chatType']}"})
        if owner := str(row.get("owner") or ""):
            summary_rows.append({"text": f"Owner: {owner}"})
        if row.get("memberRawNum") is not None:
            summary_rows.append({"text": f"Members: {row['memberRawNum']}"})
        write_reference_page(
            f"wiki_chat_{chat_id}",
            "SNSChatTable",
            int(row.get("chatType") or 0),
            title,
            lines,
            type_key="other",
            source_debug=source_ref(
                "SNSChatTable",
                chat_id,
                pick_fields(row, "chatId", "chatType", "desc", "memberRawNum", "name", "owner", "tagLabel", "tagType"),
            ),
            summary_rows=summary_rows,
            tags=["wiki", "snsChat", "table_snschattable"],
            search_parts=[chat_id, title, desc, tag_label, str(row.get("owner") or "")],
        )
    print(f"Writing {len(enemy_ability_desc)} enemy ability reference pages...")
    for ability_id, row in sorted(enemy_ability_desc.items()):
        if not isinstance(row, dict):
            continue
        title = brace_text(t((row.get("name") or {}).get("id"))) or ability_id
        desc = t((row.get("description") or {}).get("id"))
        lines: list[dict] = []
        seen_texts: set[tuple[str, str, str]] = set()
        append_reference_line(
            lines,
            seen_texts,
            ability_id,
            desc,
            debug={
                **source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
                "fields": {
                    "title": text_trace("EnemyAbilityDescTable", ability_id, "name", row.get("name")),
                    "text": text_trace("EnemyAbilityDescTable", ability_id, "description", row.get("description")),
                },
            } if desc else None,
        )
        if title == ability_id and not lines:
            continue
        write_reference_page(
            f"wiki_enemyability_{ability_id}",
            "EnemyAbilityDescTable",
            0,
            title,
            lines,
            source_debug=source_ref("EnemyAbilityDescTable", ability_id, pick_fields(row, "abilityId", "description", "name")),
            tags=["wiki", "enemyAbility", "table_enemyabilitydesctable"],
            search_parts=[ability_id, title, desc],
        )
    training_death_tips = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingDeathTips.json",
        "StreamingAssets/Table/TrainingDeathTips.json",
    )
    training_type_info = load_optional_table_json(
        STREAMING_TABLE_DIR,
        "TrainingTypeInfoTable.json",
        "StreamingAssets/Table/TrainingTypeInfoTable.json",
    )
    if isinstance(training_death_tips, dict) or isinstance(training_type_info, dict):
        training_death_tips = training_death_tips if isinstance(training_death_tips, dict) else {}
        training_type_info = training_type_info if isinstance(training_type_info, dict) else {}
        training_keys = sorted(
            set(training_death_tips) | set(training_type_info),
            key=lambda key: (
                int((training_type_info.get(key) or {}).get("priority") or 9999)
                if isinstance(training_type_info.get(key), dict)
                else 9999,
                str(key),
            ),
        )
        for row_index, row_id in enumerate(training_keys, start=1):
            tip_row = training_death_tips.get(row_id)
            info_row = training_type_info.get(row_id)
            tip_row = tip_row if isinstance(tip_row, dict) else {}
            info_row = info_row if isinstance(info_row, dict) else {}
            title = (
                brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
                or row_id
            )
            lines: list[dict] = []
            seen_texts: set[tuple[str, str, str]] = set()
            tip_contents = tip_row.get("tipContents") or []
            if isinstance(tip_contents, list):
                for idx, tip_ref in enumerate(tip_contents, start=1):
                    text = t((tip_ref or {}).get("id"))
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_tip_{idx}",
                        text,
                        hint=f"Tip {idx}",
                        debug={
                            **source_ref(
                                "TrainingDeathTips",
                                row_id,
                                {"path": f"$.tipContents[{idx-1}]"},
                                nodeId=idx,
                                tableSource="StreamingAssets/Table",
                            ),
                            "fields": {
                                "text": text_trace(
                                    "TrainingDeathTips",
                                    row_id,
                                    f"$.tipContents[{idx-1}]",
                                    tip_ref,
                                ),
                            },
                        } if text else None,
                    )
            label_text = brace_text(t((info_row.get("progressBarLabel") or {}).get("id")))
            if not lines and label_text:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_label",
                    label_text,
                    hint="Type Label",
                    debug={
                        **source_ref(
                            "TrainingTypeInfoTable",
                            row_id,
                            {"path": "$.progressBarLabel"},
                            tableSource="StreamingAssets/Table",
                        ),
                        "fields": {
                            "text": text_trace(
                                "TrainingTypeInfoTable",
                                row_id,
                                "$.progressBarLabel",
                                info_row.get("progressBarLabel"),
                            ),
                        },
                    },
                )
            if not title and not lines:
                continue
            summary_rows = [
                {"text": "Table: TrainingDeathTips / TrainingTypeInfoTable"},
                {"text": f"Row: {row_id}"},
            ]
            if label_text and label_text != title:
                summary_rows.append({"text": f"Label: {label_text}"})
            if info_row.get("priority") is not None:
                summary_rows.append({"text": f"Priority: {info_row['priority']}"})
            if info_row.get("trainingThresholdFactor") is not None:
                summary_rows.append({"text": f"Threshold Factor: {info_row['trainingThresholdFactor']}"})
            source_debug = source_ref(
                "TrainingDeathTips",
                row_id,
                {"table": "TrainingDeathTips / TrainingTypeInfoTable"},
                tableSource="StreamingAssets/Table",
            )
            debug_extra = {
                "mergedSources": [
                    source_ref(
                        "TrainingDeathTips",
                        row_id,
                        pick_fields(tip_row, "tipContents"),
                        tableSource="StreamingAssets/Table",
                    ),
                    source_ref(
                        "TrainingTypeInfoTable",
                        row_id,
                        pick_fields(info_row, "priority", "progressBarLabel", "trainingThresholdFactor", "trainingType"),
                        tableSource="StreamingAssets/Table",
                    ),
                ],
            }
            write_reference_page(
                f"wiki_trainingtip_{collection_slug(row_id)}",
                "TrainingDeathTips",
                int(info_row.get("priority") or row_index),
                title,
                lines,
                kind="table_trainingdeathtips",
                type_key="other",
                source_debug=source_debug,
                summary_rows=summary_rows,
                tags=[
                    "wiki",
                    "table_trainingdeathtips",
                    "table_trainingtypeinfotable",
                    "group_training_death_tips",
                ],
                search_parts=[
                    "TrainingDeathTips",
                    "TrainingTypeInfoTable",
                    row_id,
                    title,
                    label_text,
                ],
                debug_extra=debug_extra,
            )
    collection_omit_tables = {
        "AchievementTable.json",
        "AchievementTypeTable.json",
        "AIBarkText.json",
        "BlocDataTable.json",
        "CheckInRewardTable.json",
        "DialogOptionTable.json",
        "DialogSummaryTable.json",
        "DialogTextTable.json",
        "GamepadImplicitSettingItemTable.json",
        "GamepadSettingItemTable.json",
        "GamepadSettingOptionTable.json",
        "GameSystemConfigTable.json",
        "GiftpackCashShopIdTable.json",
        I18N_HOTFIX_TABLE,
        "MissionExtraInfoTable.json",
        "MoneyConfigTable.json",
        "MoneyConsumeTable.json",
        "MoneyExchangeTable.json",
        "MoneyGainTable.json",
        "MoneyRecordTable.json",
        "PrtsCategory.json",
        "PrtsDocument.json",
        "PrtsInvestigate.json",
        "PrtsInvestigateCategory.json",
        "PrtsMultimedia.json",
        "PrtsRecord.json",
        "QualitySubSettingOptionTable.json",
        "QualitySubSettingTable.json",
        "ReportTable.json",
        "SceneCollectableItemTable.json",
        "ShareChannelTable.json",
        "SNSDialogTopicTable.json",
        "SettingTabTable.json",
        "TowerDefenseGroupTable.json",
        "TrainingDeathTips.json",
        "TrainingTypeInfoTable.json",
        "WeaponBasicTable.json",
    }
    collection_omit_prefixes = (
        "Attribute",
        "CompositeAttributeShow",
        "SocialBuilding",
    )
    collection_skip_tables = {
        "DialogTextTable.json",
        "SNSDialogTable.json",
        "SNSDialogOptionTable.json",
        "RadioTable.json",
        "RemoteCommonTable.json",
        "EnvTalkTable.json",
        "ResponsiveDialog.json",
        "MailSenderTable.json",
        "MailTemplateTable.json",
        "PrtsAllItem.json",
        "PrtsFirstLv.json",
        "PrtsPage.json",
        "PrtsNote.json",
        "WikiCategoryTable.json",
        "WikiGroupTable.json",
        "WikiEntryDataTable.json",
        "WikiTutorialPageTable.json",
        "WikiTutorialPageByEntryTable.json",
        "WikiCraftJumpTable.json",
        "WikiDefaultCraftTable.json",
        "MissionAreaTable.json",
        "NpcProxyTable.json",
        "NpcProxyExDataTable.json",
        "AtmosphericNpcClusterDataTable.json",
        "SkillPatchTable.json",
        "GameMechanicTable.json",
        "DungeonCharTutorialStepTable.json",
        "LoadingTipsTable.json",
        "ErrorCodeTable.json",
        "SNSChatTable.json",
        "EnemyAbilityDescTable.json",
        "TextTable.json",
    }
    collection_preloaded_tables: dict[str, dict] = {
        "AchievementTable.json": achievements,
        "AIBarkText.json": ai_bark_text,
        "AudioDialog.json": audio_dialog,
        "CharGrowthTable.json": char_growth,
        "CharacterTable.json": character_rows,
        "DialogOptionTable.json": dlg_opts,
        "DungeonTable.json": dungeons,
        "EnemyDisplayInfoTable.json": enemy_display_info,
        "EnemyTemplateDisplayInfoTable.json": enemy_template_display,
        "ItemTable.json": item_rows,
        "MissionExtraInfoTable.json": mission_extra_info,
        "NpcTable.json": npc_rows,
        "NpcTemplateGroupTable.json": npc_templates,
        "ResponsiveDialog.json": responsive_dialog,
        "RichContentTable.json": rich_content,
        "WeaponBasicTable.json": weapon_basic,
    }
    collection_table_cache: dict[tuple[str, str], dict] = {
        ("streaming", table_name): payload
        for table_name, payload in collection_preloaded_tables.items()
    }

    def collection_is_redundant_support_table(table_name: str) -> bool:
        tokens = set(collection_table_name_tokens(table_name))
        return bool({"tag", "title", "label"} & tokens)
    def collection_table_payload(table_source: str, table_name: str) -> dict:
        cache_key = (table_source, table_name)
        if cache_key in collection_table_cache:
            return collection_table_cache[cache_key]
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        payload = load_optional_table_json(
            table_dir,
            table_name,
            f"{collection_source_label(table_source)}/{table_name}",
        )
        collection_table_cache[cache_key] = payload if isinstance(payload, dict) else {}
        return collection_table_cache[cache_key]

    def resolve_reference_raw_i18n(raw_value, *, preferred_source: str = "streaming"):
        if isinstance(raw_value, dict):
            is_i18n_text = "id" in raw_value and "text" in raw_value
            resolved_text = t(raw_value.get("id"), preferred_source=preferred_source) if is_i18n_text else ""
            out = {}
            for key, value in raw_value.items():
                if is_i18n_text and key == "text" and resolved_text:
                    out[key] = resolved_text
                else:
                    out[key] = resolve_reference_raw_i18n(value, preferred_source=preferred_source)
            return out
        if isinstance(raw_value, list):
            return [resolve_reference_raw_i18n(value, preferred_source=preferred_source) for value in raw_value]
        return raw_value

    def write_raw_reference_bundle() -> dict:
        reference_dir.mkdir(parents=True, exist_ok=True)
        generated = int(time.time())
        table_index: list[dict] = []
        base_reference_rows: dict[str, list[dict]] = {}
        base_reference_files: dict[str, str] = {}
        base_reference_hashes: dict[str, str] = {}
        total_rows = 0
        total_texts = 0
        total_bytes = 0
        def reference_payload_hash(payload: dict) -> str:
            text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            return _reference_hashlib.sha256(text.encode("utf-8")).hexdigest()
        for table_source, table_dir in (
            ("streaming", STREAMING_TABLE_DIR),
            ("persistent", PERSISTENT_TABLE_DIR),
        ):
            if not table_dir.exists():
                continue
            source_out_dir = reference_dir / table_source
            source_out_dir.mkdir(parents=True, exist_ok=True)
            for table_path in sorted(table_dir.glob("*.json")):
                table_name = table_path.name
                if table_name.startswith("I18nTextTable_") or table_name == I18N_HOTFIX_TABLE:
                    continue
                payload = collection_table_payload(table_source, table_name)
                if not isinstance(payload, dict) or not payload:
                    continue
                row_payloads: list[dict] = []
                raw_rows: dict[str, object] = {}
                table_texts = 0
                for row_index, (row_id, row) in enumerate(
                    sorted(payload.items(), key=lambda item: str(item[0])),
                    start=1,
                ):
                    row_key = str(row_id)
                    text_nodes = collect_reference_text_nodes(
                        table_name,
                        row_key,
                        row,
                        preferred_source=table_source,
                    )
                    if not text_nodes:
                        continue
                    texts = reference_row_texts(text_nodes)
                    table_texts += len(texts)
                    bucket = collection_bucket(
                        table_name,
                        row_key,
                        row if isinstance(row, dict) else None,
                    )
                    row_payload = {
                        "id": row_key,
                        "title": collection_row_title(
                            table_name,
                            row_key,
                            text_nodes,
                            preferred_source=table_source,
                        ),
                        "bucket": bucket,
                        "order": collection_scene_value(
                            row if isinstance(row, dict) else None,
                            row_index,
                        ),
                        "texts": texts,
                    }
                    row_payloads.append(row_payload)
                    raw_rows[row_key] = resolve_reference_raw_i18n(
                        row,
                        preferred_source=table_source,
                    )
                if not row_payloads:
                    continue
                rel_file = f"{table_source}/{table_path.stem}.json"
                out_payload = {
                    "generated": generated,
                    "language": language_code,
                    "source": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "rows": row_payloads,
                    "rawRows": raw_rows,
                }
                storage = "full"
                base_file = ""
                overlay_rows = 0
                removed_rows = 0
                if table_source == "persistent" and table_name in base_reference_rows:
                    base_rows = base_reference_rows.get(table_name) or []
                    base_file = base_reference_files.get(table_name) or ""
                    base_hash = base_reference_hashes.get(table_name) or ""
                    base_by_id = {str(row.get("id") or ""): row for row in base_rows}
                    current_by_id = {str(row.get("id") or ""): row for row in row_payloads}
                    removed_ids = sorted(row_id for row_id in base_by_id if row_id not in current_by_id)
                    changed_rows = [
                        row for row in row_payloads
                        if base_by_id.get(str(row.get("id") or "")) != row
                    ]
                    changed_raw_rows = {
                        str(row.get("id") or ""): raw_rows.get(str(row.get("id") or ""))
                        for row in changed_rows
                        if str(row.get("id") or "") in raw_rows
                    }
                    overlay_rows = len(changed_rows)
                    removed_rows = len(removed_ids)
                    if not changed_rows and not removed_ids and base_file:
                        rel_file = base_file
                        storage = "shared"
                        file_bytes = 0
                        content_hash = base_hash
                    else:
                        rel_file = f"overlays/{table_source}/{table_path.stem}.json"
                        out_payload = {
                            "generated": generated,
                            "language": language_code,
                            "source": collection_source_label(table_source),
                            "table": table_name,
                            "label": collection_display_name(table_path.stem),
                            "baseFile": base_file,
                            "rowOrder": [str(row.get("id") or "") for row in row_payloads],
                            "removedRows": removed_ids,
                            "rows": changed_rows,
                            "rawRows": changed_raw_rows,
                        }
                        content_hash = reference_payload_hash(out_payload)
                        out_path = write_reference_payload(rel_file, out_payload)
                        file_bytes = out_path.stat().st_size
                        storage = "overlay"
                else:
                    content_hash = reference_payload_hash(out_payload)
                    out_path = write_reference_payload(rel_file, out_payload)
                    file_bytes = out_path.stat().st_size
                    if table_source == "streaming":
                        base_reference_rows[table_name] = row_payloads
                        base_reference_files[table_name] = rel_file
                        base_reference_hashes[table_name] = content_hash
                total_bytes += file_bytes
                total_rows += len(row_payloads)
                total_texts += table_texts
                table_row = {
                    "source": table_source,
                    "sourceLabel": collection_source_label(table_source),
                    "table": table_name,
                    "label": collection_display_name(table_path.stem),
                    "file": rel_file,
                    "rows": len(row_payloads),
                    "texts": table_texts,
                    "bytes": file_bytes,
                    "storage": storage,
                    "hash": content_hash,
                }
                if base_file:
                    table_row["baseFile"] = base_file
                if overlay_rows:
                    table_row["overlayRows"] = overlay_rows
                if removed_rows:
                    table_row["removedRows"] = removed_rows
                table_index.append(table_row)
        table_index.sort(key=lambda row: (row["source"], row["label"], row["table"]))
        index_payload = {
            "generated": generated,
            "language": language_code,
            "tables": table_index,
            "stats": {
                "tables": len(table_index),
                "rows": total_rows,
                "texts": total_texts,
                "bytes": total_bytes,
            },
        }
        write_reference_payload("index.json", index_payload)
        print(
            f"Raw reference bundle written: {len(table_index)} tables; "
            f"{total_rows} rows; {total_texts} localized text node(s)"
        )
        return index_payload["stats"]
    ai_bark_reference_cache: dict[str, dict[str, dict[str, str]]] = {}
    def collection_ai_bark_refs(table_source: str) -> dict[str, dict[str, str]]:
        if table_source in ai_bark_reference_cache:
            return ai_bark_reference_cache[table_source]
        refs: dict[str, dict[str, str]] = {}
        responsive_payload = collection_table_payload(table_source, "ResponsiveDialog.json")
        for set_id, top_row in sorted(responsive_payload.items(), key=lambda item: str(item[0])):
            if not isinstance(top_row, dict):
                continue
            speakers = top_row.get("speakers") or {}
            if not isinstance(speakers, dict):
                continue
            for speaker_id, speaker_row in sorted(speakers.items()):
                if not isinstance(speaker_row, dict):
                    continue
                actor_id = speaker_actor_id(str(speaker_id))
                speaker_name = speaker_display_name(str(speaker_id)) or actor_id or str(speaker_id)
                triggers = speaker_row.get("triggers") or {}
                if not isinstance(triggers, dict):
                    continue
                for trigger_key, trigger_row in sorted(triggers.items()):
                    if not isinstance(trigger_row, dict):
                        continue
                    for response_id in (trigger_row.get("response") or []):
                        row_id = str(response_id)
                        current = refs.get(row_id)
                        if current and current.get("source") == "ResponsiveDialog":
                            continue
                        refs[row_id] = {
                            "actorId": actor_id,
                            "speakerId": str(speaker_id),
                            "speakerName": speaker_name,
                            "source": "ResponsiveDialog",
                            "setId": str(set_id),
                            "triggerKey": str(trigger_key),
                        }
        audio_payload = collection_table_payload(table_source, "AudioDialog.json")
        for row_id, audio_row in sorted(audio_payload.items(), key=lambda item: str(item[0])):
            if not isinstance(audio_row, dict):
                continue
            row_key = str(row_id)
            audio_path = str(audio_row.get("path") or "")
            speaker_id = str(audio_row.get("speakerChannel") or "")
            actor_id = speaker_actor_id(speaker_id)
            speaker_name = speaker_display_name(speaker_id) or actor_id or speaker_id
            current = refs.get(row_key)
            if current:
                if audio_path:
                    current["audioPath"] = audio_path
                if speaker_id and not current.get("speakerId"):
                    current["speakerId"] = speaker_id
                if actor_id and not current.get("actorId"):
                    current["actorId"] = actor_id
                if speaker_name and not current.get("speakerName"):
                    current["speakerName"] = speaker_name
                continue
            if not actor_id:
                continue
            refs[row_key] = {
                "actorId": actor_id,
                "speakerId": speaker_id,
                "speakerName": speaker_name,
                "source": "AudioDialog",
                "audioPath": audio_path,
            }
        ai_bark_reference_cache[table_source] = refs
        return refs
    def rich_content_row_for_source(content_id: str, table_source: str) -> dict:
        content_key = str(content_id or "").strip()
        if not content_key:
            return {}
        payload = collection_table_payload(table_source, "RichContentTable.json")
        row = payload.get(content_key) if isinstance(payload, dict) else None
        if not isinstance(row, dict) and table_source != "streaming":
            row = rich_content.get(content_key)
        return row if isinstance(row, dict) else {}
    def rich_content_title_text_for_source(content_id: str, table_source: str) -> str:
        row = rich_content_row_for_source(content_id, table_source)
        return t((row.get("title") or {}).get("id"), preferred_source=table_source) if row else ""
    def rich_content_lines_for_source(content_id: str, table_source: str) -> list[dict]:
        row = rich_content_row_for_source(content_id, table_source)
        if not row:
            return []
        out: list[dict] = []
        for idx, item in enumerate(row.get("contentList") or [], start=1):
            if not isinstance(item, dict):
                continue
            content = item.get("content") or {}
            text = t(content.get("id"), preferred_source=table_source)
            out.append({
                "id": f"{content_id}_{idx}",
                "text": text,
                "_debug": {
                    **source_ref(
                        "RichContentTable.contentList",
                        str(content_id),
                        pick_fields(item, "content"),
                        nodeId=idx,
                        tableSource=collection_source_label(table_source),
                    ),
                    "fields": {
                        "text": text_trace(
                            "RichContentTable",
                            str(content_id),
                            "content",
                            content,
                            preferred_source=table_source,
                        ),
                    },
                },
            })
        return out
    def reading_content_refs(table_name: str, row_id: str, row: dict | None, *, table_source: str) -> list[dict]:
        if not isinstance(row, dict):
            return []
        refs: list[dict] = []
        if table_name == "PrtsReading.json":
            items = row.get("list") or {}
            if not isinstance(items, dict):
                return []
            sorted_items = sorted(
                ((node_id, node) for node_id, node in items.items() if isinstance(node, dict)),
                key=lambda item: (int((item[1] or {}).get("order") or 0), str(item[0])),
            )
            for node_id, node in sorted_items:
                content_id = str(node.get("contentId") or "").strip()
                if not content_id:
                    continue
                name = brace_text(t((node.get("name") or {}).get("id"), preferred_source=table_source))
                subtitle = brace_text(t((node.get("subtitle") or {}).get("id"), preferred_source=table_source))
                refs.append({
                    "contentId": content_id,
                    "label": name or subtitle or content_id,
                    "subtitle": subtitle,
                    "path": f"$.list.{node_id}.contentId",
                    "nodeId": node_id,
                    "source": pick_fields(node, "contentId", "name", "order", "subtitle", "uniqId"),
                })
        elif table_name == "ReadingPopUpTable.json":
            content_id = str(row.get("contentId") or "").strip()
            if content_id:
                refs.append({
                    "contentId": content_id,
                    "label": brace_text(t((row.get("title") or {}).get("id"), preferred_source=table_source)) or content_id,
                    "path": "$.contentId",
                    "nodeId": 1,
                    "source": pick_fields(row, "bgType", "contentId", "iconType", "id", "title"),
                })
        return refs
    def append_linked_reading_content_lines(
        table_name: str,
        row_id: str,
        row: dict | None,
        *,
        table_source: str,
        lines: list[dict],
        seen_texts: set[tuple[str, str, str]],
    ) -> tuple[list[dict], str]:
        linked_refs: list[dict] = []
        preview_text = ""
        for ref_index, ref in enumerate(
            reading_content_refs(table_name, row_id, row, table_source=table_source),
            start=1,
        ):
            content_id = str(ref.get("contentId") or "").strip()
            if not content_id:
                continue
            label = str(ref.get("label") or content_id)
            linked_from = source_ref(
                table_name.removesuffix(".json"),
                row_id,
                {
                    "path": ref.get("path") or "$.contentId",
                    "contentId": content_id,
                    **(ref.get("source") or {}),
                },
                nodeId=ref.get("nodeId"),
                tableSource=collection_source_label(table_source),
            )
            rich_title = rich_content_title_text_for_source(content_id, table_source)
            rich_lines = rich_content_lines_for_source(content_id, table_source)
            if rich_title and rich_title != label:
                append_reference_line(
                    lines,
                    seen_texts,
                    f"{row_id}_linked_{ref_index}_title",
                    rich_title,
                    hint=f"{label} / Title",
                    debug={
                        **source_ref(
                            "RichContentTable",
                            content_id,
                            {"title": (rich_content_row_for_source(content_id, table_source).get("title") or {})},
                            tableSource=collection_source_label(table_source),
                        ),
                        "linkedFrom": linked_from,
                        "fields": {
                            "text": text_trace(
                                "RichContentTable",
                                content_id,
                                "title",
                                (rich_content_row_for_source(content_id, table_source).get("title") or {}),
                                preferred_source=table_source,
                            ),
                        },
                    },
                )
                preview_text = preview_text or rich_title
            if rich_lines:
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RichContentTable",
                    "lineCount": len(rich_lines),
                    "label": label,
                })
                for content_index, content_line in enumerate(rich_lines, start=1):
                    text = str(content_line.get("text") or "")
                    debug = dict(content_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=rich_title or label,
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text
                continue
            radio_row = radio_row_lookup.get(content_id)
            if radio_row:
                radio_lines = [line for line in (radio_row.get("lines") or []) if isinstance(line, dict)]
                linked_refs.append({
                    "contentId": content_id,
                    "source": "RadioTable",
                    "lineCount": len(radio_lines),
                    "label": label,
                })
                for content_index, radio_line in enumerate(radio_lines, start=1):
                    text = str(radio_line.get("text") or "")
                    debug = dict(radio_line.get("_debug") or {})
                    debug["linkedFrom"] = linked_from
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_id}_linked_{ref_index}_{content_index}",
                        text,
                        hint=label,
                        actor=str(radio_line.get("actor") or ""),
                        aid=str(radio_line.get("aid") or ""),
                        debug=debug,
                    )
                    if text:
                        preview_text = preview_text or text
        return linked_refs, preview_text
    def write_generic_collection_pages(
        table_source: str,
        *,
        dedupe_against_streaming: bool = False,
    ) -> tuple[int, int]:
        table_dir = STREAMING_TABLE_DIR if table_source == "streaming" else PERSISTENT_TABLE_DIR
        if not table_dir.exists():
            return (0, 0)
        generic_collection_paths = [
            path
            for path in sorted(table_dir.glob("*.json"))
            if not path.name.startswith("I18nTextTable_")
            and path.name not in collection_omit_tables
            and not path.name.startswith(collection_omit_prefixes)
            and not collection_is_redundant_support_table(path.name)
            and (table_source != "streaming" or path.name not in collection_skip_tables)
        ]
        label = "generic" if table_source == "streaming" else "supplemental persistent"
        print(
            f"Writing {label} collection pages from {len(generic_collection_paths)} tables..."
        )
        generic_collection_pages = 0
        generic_collection_tables = 0
        for table_path in generic_collection_paths:
            table_name = table_path.name
            payload = collection_table_payload(table_source, table_name)
            if not isinstance(payload, dict) or not payload:
                continue
            table_pages = 0
            table_label = collection_display_name(table_path.stem)
            streaming_payload = (
                collection_table_payload("streaming", table_name)
                if dedupe_against_streaming
                else {}
            )
            for row_index, (row_id, row) in enumerate(sorted(payload.items(), key=lambda item: str(item[0])), start=1):
                row_key = str(row_id)
                if table_name == "RichContentTable.json" and row_key in prts_content_ids:
                    continue
                forced_kind = None
                text_nodes = collect_reference_text_nodes(
                    table_name,
                    row_key,
                    row,
                    preferred_source=table_source,
                )
                if not text_nodes:
                    continue
                if (
                    table_name == "RichContentTable.json"
                    and text_sequence_fingerprint(text_nodes) in wiki_text_fingerprints
                ):
                    continue
                variant = False
                if dedupe_against_streaming:
                    streaming_row = streaming_payload.get(row_key) if isinstance(streaming_payload, dict) else None
                    if streaming_row is not None:
                        streaming_nodes = collect_reference_text_nodes(
                            table_name,
                            row_key,
                            streaming_row,
                            preferred_source="streaming",
                        )
                        if collection_text_fingerprint(streaming_nodes) == collection_text_fingerprint(text_nodes):
                            continue
                        variant = bool(streaming_nodes)
                bucket = collection_bucket(table_name, row_key, row if isinstance(row, dict) else None)
                bucket_token = collection_bucket_token(bucket)
                story_ref = collection_reading_story_ref(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                ) or collection_story_ref_from_bucket(bucket)
                if story_ref:
                    mission_id, forced_scene_value, forced_type_key = story_ref
                    if not forced_scene_value:
                        forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    extra_mission_names.setdefault(mission_id, collection_display_name(mission_id))
                else:
                    mission_id = (
                        f"wiki_collection_{collection_slug(table_source)}_"
                        f"{collection_slug(table_path.stem)}_{bucket_token}"
                    )
                    forced_scene_value = collection_scene_value(row if isinstance(row, dict) else None, row_index)
                    forced_type_key = forced_kind
                title = collection_row_title(
                    table_name,
                    row_key,
                    text_nodes,
                    preferred_source=table_source,
                )
                lines: list[dict] = []
                seen_texts: set[tuple[str, str, str]] = set()
                for node_index, node in enumerate(text_nodes, start=1):
                    hint = node.get("hint") or collection_display_name(node.get("field") or "text")
                    append_reference_line(
                        lines,
                        seen_texts,
                        f"{row_key}_{node_index}",
                        node.get("text") or "",
                        hint=hint,
                        debug={
                            **source_ref(
                                table_path.stem,
                                row_key,
                                {
                                    "path": node.get("path") or "$",
                                },
                                nodeId=node_index,
                                tableSource=collection_source_label(table_source),
                            ),
                            "fields": {
                                "text": text_trace(
                                    table_path.stem,
                                    row_key,
                                    str(node.get("path") or "$"),
                                    node.get("raw"),
                                    preferred_source=table_source,
                                ),
                            },
                        },
                    )
                linked_content_refs, linked_preview_text = append_linked_reading_content_lines(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    lines=lines,
                    seen_texts=seen_texts,
                )
                if not lines:
                    continue
                out_key = (
                    f"wiki_collection_{collection_slug(table_source)}_"
                    f"{collection_slug(table_path.stem)}_{row_key}"
                )
                summary_rows = collection_summary_rows(
                    table_name,
                    row_key,
                    row if isinstance(row, dict) else None,
                    bucket,
                    table_source=table_source,
                    variant=variant,
                )
                debug_extra = {}
                if linked_content_refs:
                    total_linked_lines = sum(int(ref.get("lineCount") or 0) for ref in linked_content_refs)
                    summary_rows.append({
                        "text": f"Linked content: {len(linked_content_refs)} ref(s), {total_linked_lines} line(s)",
                    })
                    debug_extra["linkedContent"] = linked_content_refs
                search_parts = [
                    table_label,
                    row_key,
                    bucket,
                    table_source,
                ]
                if isinstance(row, dict):
                    for field in ("groupId", "categoryId", "type", "gameCategory", "charId", "profession", "weaponType", "owner"):
                        value = row.get(field)
                        if is_present(value):
                            search_parts.append(str(value))
                page_tags = collection_tags(
                    table_name,
                    row_key,
                    bucket,
                    row if isinstance(row, dict) else None,
                    table_source=table_source,
                    variant=variant,
                )
                write_reference_page(
                    out_key,
                    mission_id,
                    forced_scene_value,
                    title,
                    lines,
                    kind=forced_kind,
                    type_key=forced_type_key,
                    source_debug=source_ref(
                        table_path.stem,
                        row_key,
                        {"table": table_name},
                        tableSource=collection_source_label(table_source),
                        variantOf="StreamingAssets/Table" if variant else None,
                    ),
                    summary_rows=summary_rows,
                    tags=page_tags,
                    search_parts=search_parts,
                    preview_text=linked_preview_text or None,
                    debug_extra=debug_extra or None,
                )
                table_pages += 1
                generic_collection_pages += 1
            if table_pages:
                generic_collection_tables += 1
                print(f"  collection {table_source} {table_name}: {table_pages} pages")
        return generic_collection_pages, generic_collection_tables
    if include_reference_in_story_index:
        generic_collection_pages, generic_collection_tables = write_generic_collection_pages("streaming")
        persistent_collection_pages, persistent_collection_tables = write_generic_collection_pages(
            "persistent",
            dedupe_against_streaming=True,
        )
        print(
            f"Generic collection pages written: {generic_collection_pages + persistent_collection_pages} "
            f"across {generic_collection_tables + persistent_collection_tables} tables"
        )
    else:
        print("Skipping generic table collection pages for lean story profile.")
    reference_stats: dict = {}
    if reuse_reference:
        reference_stats = load_reused_reference_stats(reference_dir, language_code)
    elif write_reference:
        reference_stats = write_raw_reference_bundle()
    print(f"Writing {len(mail_templates)} mail conversations...")
    for template_id, row in sorted(mail_templates.items()):
        if not isinstance(row, dict):
            continue
        sender_id = str(row.get("senderId") or "system")
        sender_row = mail_senders.get(sender_id) if isinstance(mail_senders.get(sender_id), dict) else {}
        sender_name = (
            brace_text(t((sender_row.get("senderName") or {}).get("id")))
            or speaker_display_name(sender_id)
            or sender_id
        )
        title = brace_text(t((row.get("title") or {}).get("id"))) or template_id
        body = t((row.get("mailContent") or {}).get("id"))
        out_key = f"mail_{template_id}"
        if sender_name:
            extra_mission_names[sender_id] = sender_name
        summary: list[dict] = []
        if row.get("rewardId"):
            summary.append({"text": f"Reward: {row['rewardId']}"})
        if row.get("duration") is not None:
            summary.append({"text": f"Duration: {row['duration']}"})
        if row.get("type") is not None:
            summary.append({"text": f"Type: {row['type']}"})
        lines = [{
            "id": template_id,
            "aid": sender_id,
            "actor": sender_name,
            "text": body,
            "_debug": {
                **source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
                "fields": {
                    "title": text_trace("MailTemplateTable", template_id, "title", row.get("title")),
                    "text": text_trace("MailTemplateTable", template_id, "mailContent", row.get("mailContent")),
                },
            },
        }]
        payload = {
            "key": out_key,
            "kind": "mail",
            "mission": sender_id,
            "scene": 0,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "MailTemplateTable",
                    template_id,
                    pick_fields(row, "duration", "mailContent", "rewardId", "senderId", "templateId", "title", "type"),
                ),
            },
        }
        if summary:
            payload["summary"] = summary
        if sender_row:
            payload["_debug"]["sender"] = source_ref(
                "MailSenderTable",
                sender_id,
                pick_fields(sender_row, "id", "senderIcon", "senderName"),
            )
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "mail",
            "m": sender_id,
            "s": 0,
            "t": "mail",
            "a": 0,
            "title": title,
            "c": [sender_id] if sender_id else [],
            "n": len(lines),
            "p": preview(body or title),
            "tags": ["mail"],
        }
        search_text = " ".join(part for part in [
            template_id,
            sender_id,
            sender_name,
            title,
            body,
            str(row.get("rewardId") or ""),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    embedded_prts_notes_by_entry: dict[str, list[dict]] = defaultdict(list)
    embedded_prts_note_ids: set[str] = set()
    for note_id, note_meta in sorted(prts_note_metadata.items()):
        note_key = str(note_id or "").strip()
        if not note_key.startswith("hint_research"):
            continue
        note_row = prts_notes.get(note_key)
        if not isinstance(note_row, dict):
            continue
        linked_entry_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        if not linked_entry_ids:
            continue
        note_text = t((note_row.get("desc") or {}).get("id"))
        if not note_text:
            continue
        embedded_prts_note_ids.add(note_key)
        embedded_note = {
            "id": note_key,
            "title": str(note_meta.get("title") or note_key),
            "text": note_text,
            "researchId": str(note_meta.get("researchId") or ""),
            "index": int(note_meta.get("index") or 0),
        }
        for linked_entry_id in linked_entry_ids:
            linked_key = str(linked_entry_id or "").strip()
            if not linked_key:
                continue
            embedded_prts_notes_by_entry[linked_key].append(dict(embedded_note))
    def resolve_prts_payload(content_id: str) -> tuple[list[dict], list[dict], dict]:
        lines = rich_content_lines(content_id)
        summary_rows: list[dict] = []
        debug_extra: dict = {}
        if rich_row := rich_content.get(content_id):
            rich_title = rich_content_title_text(content_id)
            if rich_title:
                summary_rows.append({"text": f"Content: {rich_title}"})
            debug_extra["content"] = source_ref(
                "RichContentTable",
                content_id,
                pick_fields(rich_row, "title", "contentList"),
            )
        elif radio_row := radio_row_lookup.get(content_id):
            lines = list(radio_row.get("lines") or [])
            summary_rows.append({"text": f"Linked radio: {content_id}"})
        else:
            summary_rows.append({"text": f"Content ref: {content_id}"})
        return lines, summary_rows, debug_extra

    def prts_row_attachment_aliases(
        row_id: str,
        content_id: str,
        first_lv_id: str,
        first_lv_row: dict,
    ) -> set[str]:
        aliases: set[str] = set()
        for value in (row_id, content_id, first_lv_id, first_lv_row.get("icon")):
            aliases.update(prts_attachment_aliases(str(value or "")))
        return aliases
    prts_attachment_story_refs: dict[str, tuple[str, int, str]] = {}
    for sns_id, sns_entry in sns_groups.items():
        match = SNS_RE.match(sns_id)
        if not match:
            continue
        mission_id = match.group(1)
        scene_value = int(match.group(2))
        type_key, _act = parse_mission(mission_id)
        if type_key not in MISSION_STORY_TYPES:
            continue
        story_ref = (mission_id, scene_value, type_key)
        cdata = sns_entry.get("dialogContentData") or {}
        if not isinstance(cdata, dict):
            continue
        for node in cdata.values():
            if not isinstance(node, dict):
                continue
            values: list[str] = []
            content_param = node.get("contentParam")
            if isinstance(content_param, list):
                values.extend(str(value) for value in content_param if str(value))
            elif is_present(content_param):
                values.append(str(content_param))
            content_params = node.get("contentParams")
            if isinstance(content_params, list):
                values.extend(str(value) for value in content_params if str(value))
            elif is_present(content_params):
                values.append(str(content_params))
            for value in values:
                for alias in prts_attachment_aliases(value):
                    prts_attachment_story_refs.setdefault(alias, story_ref)
    standalone_prts_note_count = sum(
        1
        for note_id, row in prts_notes.items()
        if isinstance(row, dict) and str(note_id) not in embedded_prts_note_ids
    )
    print(f"Writing {len(prts_all_items) + standalone_prts_note_count} PRTS entries...")
    for row_id, row in sorted(prts_all_items.items(), key=lambda item: (
        str(item[1].get("firstLvId") or ""),
        int(item[1].get("order") or 0),
        item[0],
    )):
        if not isinstance(row, dict):
            continue
        content_id = str(row.get("contentId") or "")
        first_lv_id = str(row.get("firstLvId") or row.get("type") or "prts")
        first_lv_row = prts_first_lv.get(first_lv_id) if isinstance(prts_first_lv.get(first_lv_id), dict) else {}
        category_id = str(first_lv_row.get("categoryId") or row.get("type") or "prts")
        page_row = prts_page.get(category_id) if isinstance(prts_page.get(category_id), dict) else {}
        mission_label = brace_text(t((first_lv_row.get("name") or {}).get("id"))) or first_lv_id
        if mission_label:
            extra_mission_names[first_lv_id] = mission_label
        story_ref = collection_story_ref_from_identifiers(
            content_id,
            row_id,
            first_lv_id,
        )
        if not story_ref:
            for alias in prts_row_attachment_aliases(row_id, content_id, first_lv_id, first_lv_row):
                story_ref = prts_attachment_story_refs.get(alias)
                if story_ref:
                    break
        if not story_ref:
            story_ref = collection_map_ref_from_identifiers(content_id, row_id, first_lv_id)
        entry_mission_id = first_lv_id
        entry_scene = int(row.get("order") or 0)
        entry_type = "prts"
        if story_ref:
            entry_mission_id, story_scene, entry_type = story_ref
            entry_scene = story_scene or entry_scene
            extra_mission_names.setdefault(entry_mission_id, collection_display_name(entry_mission_id))
        title = (
            brace_text(t((row.get("name") or {}).get("id")))
            or rich_content_title_text(content_id)
            or row_id
        )
        subtitle = brace_text(t((first_lv_row.get("subName") or {}).get("id")))
        desc = t((row.get("desc") or {}).get("id"))
        lines, summary_rows, debug_extra = resolve_prts_payload(content_id)
        page_label = brace_text(t((page_row.get("name") or {}).get("id"))) or category_id
        if page_label:
            summary_rows.insert(0, {"text": f"Page: {page_label}"})
        if subtitle:
            summary_rows.append({"text": f"Section: {subtitle}"})
        if desc:
            summary_rows.append({"text": desc})
        linked_research_rows = prts_investigate_metadata_by_unlock_prts.get(str(row_id)) or []
        if linked_research_rows:
            for research_row in linked_research_rows:
                research_title = str(research_row.get("title") or "").strip()
                research_desc = str(research_row.get("desc") or "").strip()
                if research_title:
                    summary_rows.append({"text": f"Research: {research_title}"})
                if research_desc:
                    summary_rows.append({"text": research_desc})
            debug_extra["linkedResearch"] = [
                {
                    "researchId": str(research_row.get("researchId") or ""),
                    "title": str(research_row.get("title") or ""),
                    "desc": str(research_row.get("desc") or ""),
                }
                for research_row in linked_research_rows
            ]
        linked_notes = embedded_prts_notes_by_entry.get(str(row_id)) or []
        if linked_notes:
            summary_rows.append({"text": f"Archive notes: {len(linked_notes)}"})
            seen_note_lines: set[tuple[str, str, str]] = set()
            for line in lines:
                normalized = re.sub(r"\s+", " ", str(line.get("text") or "")).strip()
                if not normalized:
                    continue
                seen_note_lines.add((str(line.get("hint") or ""), str(line.get("actor") or ""), normalized))
            linked_note_debug: list[dict] = []
            for note in linked_notes:
                note_id = str(note.get("id") or "")
                note_row = prts_notes.get(note_id) if isinstance(prts_notes.get(note_id), dict) else {}
                note_title = str(note.get("title") or note_id or "Archive Note")
                append_reference_line(
                    lines,
                    seen_note_lines,
                    note_id or row_id,
                    str(note.get("text") or ""),
                    hint=note_title,
                    debug={
                        **source_ref(
                            "PrtsNote",
                            note_id,
                            {
                                "linkedEntry": row_id,
                                "researchId": str(note.get("researchId") or ""),
                            },
                        ),
                        "fields": {
                            "text": text_trace("PrtsNote", note_id, "desc", note_row.get("desc")),
                        },
                    },
                )
                linked_note_debug.append({
                    "noteId": note_id,
                    "title": note_title,
                    "researchId": str(note.get("researchId") or ""),
                    "index": int(note.get("index") or 0),
                })
            if linked_note_debug:
                debug_extra["linkedNotes"] = linked_note_debug
        payload = {
            "key": row_id,
            "kind": "prts",
            "mission": entry_mission_id,
            "scene": entry_scene,
            "title": title,
            "lines": lines,
            "_debug": {
                "source": source_ref(
                    "PrtsAllItem",
                    row_id,
                    pick_fields(row, "contentId", "desc", "firstLvId", "id", "name", "order", "type"),
                ),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        if first_lv_row:
            payload["_debug"]["firstLevel"] = source_ref(
                "PrtsFirstLv",
                first_lv_id,
                pick_fields(first_lv_row, "categoryId", "firstLvId", "icon", "itemIds", "name", "order", "subName"),
            )
        if page_row:
            payload["_debug"]["page"] = source_ref(
                "PrtsPage",
                category_id,
                pick_fields(page_row, "icon", "name", "pageType"),
            )
        payload["_debug"].update(debug_extra)
        write_conv_payload(row_id, payload)
        entry = {
            "k": row_id,
            "d": "prts",
            "m": entry_mission_id,
            "s": entry_scene,
            "t": entry_type,
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), title)),
            "tags": [str(row.get("type") or "prts"), category_id],
        }
        search_text = " ".join(part for part in [
            row_id,
            content_id,
            first_lv_id,
            category_id,
            page_label,
            mission_label,
            subtitle,
            title,
            desc,
            " ".join(line.get("text") or "" for line in lines),
        ] if part)
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    for note_id, row in sorted(prts_notes.items()):
        if not isinstance(row, dict):
            continue
        if str(note_id) in embedded_prts_note_ids:
            continue
        text = t((row.get("desc") or {}).get("id"))
        note_meta = prts_note_metadata.get(note_id) or {}
        note_title = str(note_meta.get("title") or note_id)
        note_category = str(note_meta.get("category") or "")
        note_collection_ids = [
            str(value)
            for value in (note_meta.get("collectionIds") or [])
            if str(value)
        ]
        summary_rows: list[dict] = []
        if note_category:
            summary_rows.append({"text": f"Category: {prts_category_display_name(note_category)}"})
        if note_collection_ids:
            preview_ids = ", ".join(note_collection_ids[:3])
            if len(note_collection_ids) > 3:
                preview_ids += ", ..."
            summary_rows.append({"text": f"Linked entries: {preview_ids}"})
        payload = {
            "key": note_id,
            "kind": "prts",
            "mission": "PrtsNote",
            "scene": 0,
            "title": note_title,
            "lines": [{
                "id": note_id,
                "text": text,
                "_debug": {
                    **source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
                    "fields": {
                        "text": text_trace("PrtsNote", note_id, "desc", row.get("desc")),
                    },
                },
            }],
            "_debug": {
                "source": source_ref("PrtsNote", note_id, pick_fields(row, "desc", "id")),
            },
        }
        if summary_rows:
            payload["summary"] = summary_rows
        write_conv_payload(note_id, payload)
        note_tags = ["note"]
        if note_category:
            note_tags.extend([note_category, f"category_{collection_slug(note_category)}"])
        entry = {
            "k": note_id,
            "d": "prts",
            "m": "PrtsNote",
            "s": 0,
            "t": "prts",
            "a": 0,
            "title": note_title,
            "c": [],
            "n": 1,
            "p": preview(text or note_title),
            "tags": note_tags,
        }
        search_parts = [note_id, note_title, note_category, prts_category_display_name(note_category)]
        if text:
            search_parts.append(text)
        if note_collection_ids:
            search_parts.extend(note_collection_ids)
        entry["x"] = " ".join(part for part in search_parts if part)
        index_entries.append(entry)


    responsive_refs = collection_ai_bark_refs("streaming")
    responsive_people: dict[str, dict] = {}
    for response_id, bark_row in sorted(ai_bark_text.items(), key=lambda item: str(item[0])):
        if not isinstance(bark_row, dict):
            continue
        response_key = str(response_id)
        ref = responsive_refs.get(response_key) or {}
        speaker_id = str(ref.get("speakerId") or "")
        actor_id = str(ref.get("actorId") or speaker_actor_id(speaker_id) or "")
        person_key = actor_id or speaker_id or response_key
        display_name = (
            str(ref.get("speakerName") or "")
            or speaker_display_name(speaker_id)
            or speaker_display_name(actor_id)
            or actor_id
            or speaker_id
            or person_key
        )
        group = responsive_people.setdefault(
            person_key,
            {
                "displayName": display_name,
                "actorId": actor_id,
                "speakerIds": set(),
                "setIds": set(),
                "triggerKeys": set(),
                "responseIds": [],
                "audioOnlyResponseIds": set(),
                "audioPaths": set(),
                "linesByText": {},
            },
        )
        if display_name and (not group.get("displayName") or group["displayName"] == person_key):
            group["displayName"] = display_name
        if actor_id and not group.get("actorId"):
            group["actorId"] = actor_id
        if speaker_id:
            group["speakerIds"].add(speaker_id)
        if ref.get("setId"):
            group["setIds"].add(str(ref["setId"]))
        if ref.get("triggerKey"):
            group["triggerKeys"].add(str(ref["triggerKey"]))
        if ref.get("audioPath"):
            group["audioPaths"].add(str(ref["audioPath"]))
        group["responseIds"].append(response_key)
        bark_text = t((bark_row.get("barkText") or {}).get("id"))
        normalized_text = re.sub(r"\s+", " ", str(bark_text or "")).strip()
        if not normalized_text:
            if ref.get("audioPath"):
                group["audioOnlyResponseIds"].add(response_key)
            continue
        set_id = str(ref.get("setId") or "")
        set_sort = int(set_id) if set_id.lstrip("-").isdigit() else 10**9
        trigger_key = str(ref.get("triggerKey") or "")
        source_payload = {
            "responseId": response_key,
            "speakerId": speaker_id,
            "actorId": actor_id,
            "setId": set_id,
            "triggerKey": trigger_key,
            "audioPath": str(ref.get("audioPath") or ""),
            "source": str(ref.get("source") or ""),
        }
        line_info = group["linesByText"].get(normalized_text)
        if line_info is None:
            line_info = {
                "id": response_key,
                "text": bark_text,
                "speakerIds": set([speaker_id]) if speaker_id else set(),
                "setIds": set([set_id]) if set_id else set(),
                "triggerKeys": set([trigger_key]) if trigger_key else set(),
                "responseIds": [response_key],
                "audioPaths": set([str(ref.get("audioPath") or "")]) if ref.get("audioPath") else set(),
                "sourceRefs": [source_payload],
                "fieldTrace": text_trace("AIBarkText", response_key, "barkText", bark_row.get("barkText")),
                "sortKey": (set_sort, trigger_key or "~", response_key),
            }
            group["linesByText"][normalized_text] = line_info
        else:
            if speaker_id:
                line_info["speakerIds"].add(speaker_id)
            if set_id:
                line_info["setIds"].add(set_id)
            if trigger_key:
                line_info["triggerKeys"].add(trigger_key)
            if ref.get("audioPath"):
                line_info["audioPaths"].add(str(ref["audioPath"]))
            line_info["responseIds"].append(response_key)
            line_info["sourceRefs"].append(source_payload)
            line_info["sortKey"] = min(line_info["sortKey"], (set_sort, trigger_key or "~", response_key))
    print(f"Writing {len(responsive_people)} responsive conversations...")
    for person_key, group in sorted(
        responsive_people.items(),
        key=lambda item: ((item[1].get("displayName") or item[0]).lower(), item[0]),
    ):
        display_name = str(group.get("displayName") or person_key)
        actor_id = str(group.get("actorId") or person_key)
        mission_id = actor_id or person_key
        if display_name:
            extra_mission_names[mission_id] = display_name
        lines: list[dict] = []
        for line_info in sorted(group["linesByText"].values(), key=lambda item: item["sortKey"]):
            trigger_keys = sorted(line_info["triggerKeys"])
            set_ids = responsive_sort_values(line_info["setIds"])
            hint_bits: list[str] = []
            if trigger_keys:
                hint_bits.append(f"Triggers: {responsive_preview_values(trigger_keys)}")
            if set_ids:
                hint_bits.append(f"Sets: {responsive_preview_values(set_ids)}")
            if not trigger_keys and line_info["audioPaths"]:
                hint_bits.append("Audio fallback")
            if len(line_info["responseIds"]) > 1:
                hint_bits.append(f"Responses: {len(line_info['responseIds'])}")
            audio_paths = sorted(line_info["audioPaths"])
            line = {
                "id": line_info["id"],
                "aid": actor_id,
                "actor": display_name,
                "text": line_info["text"],
                "_debug": {
                    "source": {
                        "table": "AIBarkText",
                        "actorId": actor_id,
                        "speakerIds": sorted(line_info["speakerIds"]),
                        "setIds": set_ids,
                        "triggerKeys": trigger_keys,
                        "responseIds": responsive_sort_values(line_info["responseIds"]),
                        "audioPaths": audio_paths,
                        "refs": line_info["sourceRefs"],
                    },
                    "fields": {
                        "text": line_info["fieldTrace"],
                    },
                },
            }
            if audio_paths:
                line["audioPaths"] = audio_paths
                if len(audio_paths) == 1:
                    line["audioPath"] = audio_paths[0]
            if hint_bits:
                line["hint"] = " | ".join(hint_bits)
            lines.append(line)
        duplicate_count = max(0, len(group["responseIds"]) - len(lines))
        summary_rows = [
            {"text": f"Speaker: {display_name}"},
            {"text": f"Actor ID: {actor_id}"},
            {"text": f"Unique lines: {len(lines)}"},
            {"text": f"Source bark rows: {len(group['responseIds'])}"},
        ]
        if duplicate_count:
            summary_rows.append({"text": f"Duplicate bark rows merged: {duplicate_count}"})
        if group["audioOnlyResponseIds"]:
            summary_rows.append({"text": f"Audio fallback rows: {len(group['audioOnlyResponseIds'])}"})
        summary_rows.extend(
            responsive_summary_rows("Speaker IDs", sorted(group["speakerIds"]), chunk_size=6)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger sets", responsive_sort_values(group["setIds"]), chunk_size=12)
        )
        summary_rows.extend(
            responsive_summary_rows("Trigger keys", sorted(group["triggerKeys"]), chunk_size=8)
        )
        out_key = f"responsive_{person_key}"
        payload = {
            "key": out_key,
            "kind": "responsive",
            "mission": mission_id,
            "scene": 0,
            "title": display_name,
            "lines": lines,
            "summary": summary_rows,
            "_debug": {
                "source": {
                    "table": "AIBarkText",
                    "personKey": person_key,
                    "actorId": actor_id,
                    "speakerIds": sorted(group["speakerIds"]),
                    "setIds": responsive_sort_values(group["setIds"]),
                    "triggerKeys": sorted(group["triggerKeys"]),
                    "responseIds": responsive_sort_values(group["responseIds"]),
                    "audioOnlyResponseIds": responsive_sort_values(group["audioOnlyResponseIds"]),
                    "audioPaths": sorted(group["audioPaths"]),
                },
            },
        }
        write_conv_payload(out_key, payload)
        entry = {
            "k": out_key,
            "d": "responsive",
            "m": mission_id,
            "s": 0,
            "t": "responsive",
            "a": 0,
            "title": payload["title"],
            "c": [actor_id],
            "n": len(lines),
            "p": preview(next((line.get("text") or "" for line in lines if line.get("text")), payload["title"])),
            "tags": ["responsive"],
        }
        search_text = " ".join(
            part
            for part in [
                person_key,
                actor_id,
                display_name,
                " ".join(sorted(group["speakerIds"])),
                " ".join(responsive_sort_values(group["setIds"])),
                " ".join(sorted(group["triggerKeys"])),
                " ".join(line.get("hint") or "" for line in lines),
                " ".join(line.get("text") or "" for line in lines),
            ]
            if part
        )
        if search_text:
            entry["x"] = search_text
        index_entries.append(entry)
    # Emit unmatched dialog ids (utility/spaceship/etc.) as a single bucket per prefix.
    if misc:
        misc_groups: dict[str, list[tuple[str, dict]]] = defaultdict(list)
        for did, e in misc:
            # Group on the substring up to the last underscore-then-digits.
            key = re.sub(r"_\d+(_\d+)?$", "", did) or "_misc"
            misc_groups[key].append((did, e))
        print(f"Writing {len(misc_groups)} misc dialog buckets...")
        for key, items in misc_groups.items():
            items.sort(key=lambda x: x[0])
            lines = []
            actors: set[str] = set()
            for did, e in items:
                actor_id = e.get("actorNameId") or ""
                text = t(e.get("dialogText", {}).get("id"))
                if actor_id:
                    actors.add(actor_id)
                lines.append({
                    "id": did,
                    "aid": actor_id,
                    "actor": t(e.get("actorName", {}).get("id")),
                    "text": text,
                    "hint": t(e.get("hint", {}).get("id")),
                    "audio": e.get("audioOverride") or "",
                    "emo": e.get("emotionType", 0),
                    "_debug": {
                        **source_ref(
                            "DialogTextTable",
                            did,
                            pick_fields(
                                e,
                                "actorNameId",
                                "actorName",
                                "dialogText",
                                "hint",
                                "audioOverride",
                                "emotionType",
                            ),
                        ),
                        "fields": {
                            "actor": text_trace("DialogTextTable", did, "actorName", e.get("actorName")),
                            "text": text_trace("DialogTextTable", did, "dialogText", e.get("dialogText")),
                            "hint": text_trace("DialogTextTable", did, "hint", e.get("hint")),
                        },
                    },
                })
            out_key = f"misc_{key}"
            type_, act, mission, scene = slot_misc(key)
            original_line_ids = [line.get("id") or "" for line in lines]
            ordered_line_ids, line_order_debug = resolve_scene_line_order(
                key,
                original_line_ids,
            )
            if ordered_line_ids:
                line_order_index = {line_id: idx for idx, line_id in enumerate(ordered_line_ids)}
                lines = [
                    line
                    for _idx, line in sorted(
                        enumerate(lines),
                        key=lambda item: (
                            line_order_index.get(item[1].get("id") or "", len(ordered_line_ids) + item[0]),
                            item[0],
                        ),
                    )
                ]
            prev_text = next((line.get("text") or "" for line in lines if line.get("text")), "")
            payload = {
                "key": out_key, "kind": "dlg",
                "mission": mission, "scene": scene,
                "lines": lines,
                "_debug": {
                    "title": mission_name_trace(mission),
                },
            }
            if line_order_debug:
                payload["_debug"]["lineOrder"] = line_order_debug
            if out_key in summary_by_key:
                payload["summary"] = summary_by_key[out_key]
            if out_key in options_by_key:
                packed_options = pack_options(options_by_key[out_key], lines, key)
                payload["optionGroups"] = packed_options["groups"]
                if packed_options["warnings"]:
                    payload["warnings"] = packed_options["warnings"]
            line_graph = build_dialog_tree_line_graph_payload(
                key,
                [line.get("id") or "" for line in lines],
            )
            if line_graph:
                payload["lineGraph"] = line_graph
            graph_fragments = build_dialog_tree_fragment_payload(key)
            if graph_fragments:
                payload["graphFragments"] = graph_fragments
            scene_graph_links = build_dialog_tree_scene_link_payload(key)
            if scene_graph_links:
                payload["sceneGraphLinks"] = scene_graph_links
                scene_graph_links_by_key[out_key] = scene_graph_links
            attach_runtime_registry_debug(payload)
            attach_timeline_action_evidence(
                payload,
                key,
                original_line_ids,
                [line.get("id") or "" for line in lines],
            )
            attach_scene_order_warning(payload)
            attach_timeline_timestamp_regression_warning(payload)
            story_issue_codes = dialog_story_issue_codes(payload)
            option_issue_targets = dialog_option_issue_targets(payload)
            recovery_methods = dialog_recovery_methods(payload)
            write_conv_payload(out_key, payload)
            entry = {
                "k": out_key, "d": "dlg", "m": mission, "s": scene,
                "t": type_, "a": act, "c": sorted(actors),
                "n": len(lines), "p": preview(prev_text),
            }
            if (tags := entry_tags(out_key, mission)):
                entry["tags"] = tags
            entry["x"] = merge_search_text(
                indexed_line_haystack(lines, "text", "actor", "aid", "hint"),
                extras_text(out_key),
            )
            entry["x"] = merge_search_text(
                entry.get("x", ""),
                mission_context_text(mission),
            )
            entry["x"] = merge_search_text(entry.get("x", ""), graph_fragments_text(graph_fragments))
            entry["x"] = merge_search_text(entry.get("x", ""), scene_links_text(scene_graph_links))
            if graph_fragments:
                tags = entry.setdefault("tags", [])
                if "graphFragment" not in tags:
                    tags.append("graphFragment")
            if scene_graph_links:
                tags = entry.setdefault("tags", [])
                if "sceneGraph" not in tags:
                    tags.append("sceneGraph")
            if story_issue_codes:
                entry["storyIssues"] = story_issue_codes
            if option_issue_targets:
                entry["optionIssueTargets"] = option_issue_targets
            if recovery_methods:
                entry["recoveryMethods"] = recovery_methods
            if not entry["x"]:
                entry.pop("x")
            index_entries.append(entry)

    def mark_duplicate_sim_operator_entries() -> None:
        archive_text_by_actor: dict[str, str] = {}
        for entry in index_entries:
            if entry.get("d") != "table_charactertable":
                continue
            actor_ids = [str(actor_id or "").lower() for actor_id in (entry.get("c") or []) if actor_id]
            actor_id = actor_ids[0] if actor_ids else ""
            if not actor_id:
                continue
            conv_path = conv_dir / f"{entry.get('k')}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if not line_texts:
                continue
            archive_text_by_actor[actor_id] = "\n".join([
                archive_text_by_actor.get(actor_id, ""),
                *line_texts,
            ]).strip()
        for entry in index_entries:
            key = str(entry.get("k") or "")
            if not (key.startswith("misc_sim_") or key.startswith("env_greetEnvTalk_")):
                continue
            actor_id = sim_duplicate_actor_from_key(key)
            archive_blob = archive_text_by_actor.get(actor_id, "")
            if not actor_id or not archive_blob:
                continue
            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            line_texts = normalized_duplicate_line_texts(payload)
            if line_texts and all(text in archive_blob for text in line_texts):
                entry["omitSimDuplicate"] = True
    mark_duplicate_sim_operator_entries()
    for mission in {entry["m"] for entry in index_entries if entry.get("m")}:
        mission_name(mission)
    if include_reference_in_story_index:
        write_texttable_collection_pages(collect_exported_texttable_row_ids())
    def merge_conv_hint_search_text(entry: dict) -> None:
        key = str(entry.get("k") or "")
        if not key:
            return
        hint_text = conv_hint_search_text_by_key.get(key, "")
        if hint_text:
            entry["x"] = merge_search_text(entry.get("x", ""), hint_text)
            if not entry["x"]:
                entry.pop("x", None)
    for entry in index_entries:
        merge_conv_hint_search_text(entry)


    def story_source_link_report_rows(keys: set[str]) -> list[dict]:
        rows: list[dict] = []
        for key in sorted(keys):
            links = story_source_links.get(key) or []
            source_counts = Counter(str(link.get("source") or "") for link in links)
            rows.append({
                "key": key,
                "kind": str((links[0] if links else {}).get("kind") or ""),
                "references": len(links),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(link.get("file") or "")
                    for link in links
                    if link.get("file")
                )[:8],
            })
        return rows
    def render_story_source_link_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Story Source Links ({language_code})",
            "",
            "## Summary",
            "",
            f"- Source-link keys: `{summary.get('sourceLinkKeys', 0)}`",
            f"- Source references: `{summary.get('sourceReferences', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached references: `{summary.get('attachedReferences', 0)}`",
            f"- Referenced but missing in WebUI: `{summary.get('referencedMissingKeys', 0)}`",
            f"- Story entries without source links: `{summary.get('storyEntriesWithoutSourceLinks', 0)}`",
            "",
            "## Missing Referenced Keys",
            "",
        ]
        for row in (report.get("referencedMissing") or [])[:80]:
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('references')}` refs)")
        if not report.get("referencedMissing"):
            lines.append("- None")
        lines.extend(["", "## Story Entries Without Source Links", ""])
        for row in (report.get("storyEntriesWithoutSourceLinks") or [])[:80]:
            label = row.get("mission") or ""
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}{', ' + label if label else ''})")
        if not report.get("storyEntriesWithoutSourceLinks"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)
    def attach_story_source_links_to_outputs() -> dict:
        if not story_source_links:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }
        def resolve_source_link_key(source_key: str) -> str:
            if source_key in available_keys:
                return source_key
            if source_key.startswith("dlg_"):
                misc_key = f"misc_{source_key}"
                if misc_key in available_keys:
                    return misc_key
                match = re.match(r"^(dlg_.+_\d+)d\d+$", source_key)
                if match and match.group(1) in available_keys:
                    return match.group(1)
            if source_key.startswith("cutscene_") and source_key.endswith("_start"):
                base_key = source_key.removesuffix("_start")
                if base_key in available_keys:
                    return base_key
            return ""
        resolved_source_links: dict[str, list[dict]] = defaultdict(list)
        unresolved_source_keys: set[str] = set()
        for source_key, links in story_source_links.items():
            resolved_key = resolve_source_link_key(source_key)
            if not resolved_key:
                unresolved_source_keys.add(source_key)
                continue
            for link in links:
                resolved_link = dict(link)
                if source_key != resolved_key:
                    resolved_link["sourceKey"] = source_key
                resolved_source_links[resolved_key].append(resolved_link)
        def unique_story_source_link_mission(links: list[dict]) -> str:
            missions: set[str] = set()
            for link in links:
                mission_id = str(link.get("mission") or "").strip()
                if not mission_id:
                    source = link.get("source") if isinstance(link.get("source"), dict) else {}
                    mission_id = str(source.get("mission") or "").strip()
                if not mission_id:
                    continue
                type_key, _act = parse_mission(mission_id)
                if type_key in MISSION_STORY_TYPES:
                    missions.add(mission_id)
            return next(iter(missions)) if len(missions) == 1 else ""
        attached_keys: set[str] = set()
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            links = resolved_source_links.get(key) or []
            if not links:
                continue
            attached_keys.add(key)
            attached_refs += len(links)
            compact_links = [compact_story_source_link(link) for link in links[:12]]
            omitted = max(0, len(links) - len(compact_links))
            entry["src"] = story_source_link_index_summary(links)
            entry["x"] = merge_search_text(entry.get("x", ""), story_source_link_search_text(links))
            if entry.get("d") == "sns":
                story_mission = unique_story_source_link_mission(links)
                if story_mission and story_mission != entry.get("m"):
                    entry["storyMission"] = story_mission
            tags = entry.setdefault("tags", [])
            if "sourceLinked" not in tags:
                tags.append("sourceLinked")
            conv_path = conv_dir / f"{key}.json"
            if not conv_path.exists():
                continue
            try:
                payload = json.loads(conv_path.read_text(encoding="utf-8"))
            except Exception:
                continue
            payload["sourceLinks"] = compact_links
            if omitted:
                payload["sourceLinksOmitted"] = omitted
            debug = payload.setdefault("_debug", {})
            debug["sourceLinks"] = {
                "source": {
                    "index": repo_rel(STORY_SOURCE_LINKS_PATH),
                    "key": key,
                    "count": len(links),
                    "shown": len(compact_links),
                    "omitted": omitted,
                },
            }
            write_json(conv_path, payload)
            remember_written(conv_path, written_conv_paths)
        referenced_missing = unresolved_source_keys
        source_link_candidate_kinds = set(MISSION_SCENE_ENTRY_KINDS) | {"env", "misc"}
        story_entries_without_links = [
            {
                "key": str(entry.get("k") or ""),
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
            }
            for entry in index_entries
            if entry.get("k")
            and entry.get("d") in source_link_candidate_kinds
            and entry.get("k") not in resolved_source_links
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "sourceIndex": repo_rel(STORY_SOURCE_LINKS_PATH),
            "summary": {
                "sourceLinkKeys": len(story_source_links),
                "sourceReferences": sum(len(rows) for rows in story_source_links.values()),
                "attachedKeys": len(attached_keys),
                "attachedReferences": attached_refs,
                "referencedMissingKeys": len(referenced_missing),
                "storyEntriesWithoutSourceLinks": len(story_entries_without_links),
            },
            "referencedMissing": sorted(
                story_source_link_report_rows(referenced_missing),
                key=lambda row: (-int(row.get("references") or 0), row.get("key") or ""),
            )[:300],
            "storyEntriesWithoutSourceLinks": story_entries_without_links[:500],
        }
        report_json = REPORTS_DIR / f"story_source_links_{language_code}.json"
        report_md = REPORTS_DIR / f"story_source_links_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        write_json(report_json, report, indent=2, compact=False)
        report_md.write_text(render_story_source_link_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": repo_rel(report_json),
            "markdown": repo_rel(report_md),
        }
        return report
    story_source_link_report = attach_story_source_links_to_outputs()


    def render_narrative_video_report_md(report: dict) -> str:
        summary = report.get("summary") or {}
        lines = [
            f"# Narrative Videos ({language_code})",
            "",
            "## Summary",
            "",
            f"- Scanned video files: `{summary.get('scannedVideos', 0)}`",
            f"- Attached WebUI keys: `{summary.get('attachedKeys', 0)}`",
            f"- Attached video refs: `{summary.get('attachedVideos', 0)}`",
            f"- Timeline-backed evidence rows: `{summary.get('authoritativeEvidenceRows', 0)}`",
            f"- Standalone video files: `{summary.get('standaloneVideoKeys', 0)}`",
            f"- Standalone video refs: `{summary.get('standaloneVideoRefs', 0)}`",
            f"- Manual inline attach refs: `{summary.get('manualAttachedInlineVideos', 0)}`",
            f"- Suppressed inline video refs: `{summary.get('suppressedInlineVideos', 0)}`",
            f"- Unresolved video refs: `{summary.get('unresolvedVideos', 0)}`",
            "",
            "## Attached Keys",
            "",
        ]
        for row in (report.get("attached") or [])[:120]:
            names = ", ".join((row.get("files") or [])[:4])
            lines.append(f"- `{row.get('key')}` ({row.get('kind')}, `{row.get('videos')}` refs): {names}")
        if not report.get("attached"):
            lines.append("- None")
        lines.extend(["", "## Standalone Videos", ""])
        for row in (report.get("standalone") or [])[:120]:
            names = ", ".join((row.get("files") or [])[:4])
            lines.append(f"- `{row.get('key')}` ({row.get('mission')}, `{row.get('videos')}` refs): {names}")
        if not report.get("standalone"):
            lines.append("- None")
        lines.extend(["", "## Unresolved Videos", ""])
        for row in (report.get("unresolved") or [])[:120]:
            candidates = ", ".join(f"`{candidate}`" for candidate in (row.get("keyCandidates") or [])[:4])
            lines.append(f"- `{row.get('name')}` ({row.get('kind')}) -> {candidates}")
        if not report.get("unresolved"):
            lines.append("- None")
        lines.extend(["", "## Manual Inline Attachments", ""])
        for row in (report.get("manualAttachedInline") or [])[:120]:
            note = f" ({row.get('note')})" if row.get("note") else ""
            lines.append(f"- `{row.get('name')}` -> `{row.get('targetKey')}`{note}")
        if not report.get("manualAttachedInline"):
            lines.append("- None")
        lines.extend(["", "## Suppressed Inline Attachments", ""])
        for row in (report.get("suppressedInline") or [])[:120]:
            note = f" ({row.get('note')})" if row.get("note") else ""
            lines.append(f"- `{row.get('name')}` -> `{row.get('targetKey')}`{note}")
        if not report.get("suppressedInline"):
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)
    def attach_narrative_videos_to_outputs() -> dict:
        if not narrative_video_assets:
            return {}
        available_keys = {
            str(entry.get("k") or "")
            for entry in index_entries
            if entry.get("k")
        }
        def resolve_video_key(ref: dict) -> str:
            authoritative_keys = list(ref.get("authoritativeKeys") or [])
            candidate_list = list(ref.get("keyCandidates") or [])
            if str(ref.get("kind") or "") == "remotecomm":
                for candidate in candidate_list:
                    owner_key = remotecomm_video_owner_by_stem.get(str(candidate or "").lower())
                    if owner_key in available_keys:
                        return owner_key
            if authoritative_keys:
                for candidate in authoritative_keys:
                    candidate = str(candidate or "")
                    if candidate in available_keys:
                        return candidate
                return ""
            for candidate in candidate_list:
                candidate = str(candidate or "")
                if candidate.startswith(("dlg_", "misc_dlg_")):
                    continue
                if candidate in available_keys:
                    return candidate
            for candidate in candidate_list:
                owner_key = remotecomm_video_owner_by_stem.get(str(candidate or "").lower())
                if owner_key in available_keys:
                    return owner_key
            return ""
        def video_override_for(
            rules_by_key: dict[str, list[dict]],
            target_key: str,
            ref: dict,
            *,
            require_stem: bool = False,
        ) -> dict:
            if not target_key:
                return {}
            rules = rules_by_key.get(target_key) or []
            if not rules:
                return {}
            ref_stems = {
                normalized
                for normalized in (
                    _normalize_video_override_stem(ref.get("stem")),
                    _normalize_video_override_stem(ref.get("baseStem")),
                    _normalize_video_override_stem(ref.get("name")),
                )
                if normalized
            }
            for rule in rules:
                rule_stems = set(rule.get("stems") or [])
                if require_stem and not rule_stems:
                    continue
                if rule_stems and not (rule_stems & ref_stems):
                    continue
                return {
                    "source": repo_rel(rule.get("source") or _NARRATIVE_VIDEO_OVERRIDES_PATH),
                    "targetKey": target_key,
                    "stems": sorted(rule_stems),
                    "note": str(rule.get("note") or ""),
                }
            return {}
        def suppression_override_for(resolved_key: str, ref: dict) -> dict:
            return video_override_for(narrative_video_suppress_overrides, resolved_key, ref)
        def manual_attachment_override_for(ref: dict) -> dict:
            for target_key in sorted(narrative_video_attach_overrides):
                if target_key not in available_keys:
                    continue
                override = video_override_for(
                    narrative_video_attach_overrides,
                    target_key,
                    ref,
                    require_stem=True,
                )
                if override:
                    return override
            return {}
        resolved_videos: dict[str, list[dict]] = defaultdict(list)
        standalone_videos: dict[str, list[dict]] = defaultdict(list)
        unresolved_videos: list[dict] = []
        suppressed_inline_videos: list[dict] = []
        manual_attached_inline_videos: list[dict] = []
        # Index entry kind for each WebUI key. Authoritative bindings are used
        # both for inline placement and for keeping standalone video rows near
        # their bound story entry in Story sort.
        entry_kind_by_key: dict[str, str] = {
            str(entry.get("k") or ""): str(entry.get("d") or "")
            for entry in index_entries
            if entry.get("k")
        }
        def standalone_video_key(ref: dict) -> str:
            stem = str(ref.get("baseStem") or ref.get("stem") or ref.get("name") or "").strip()
            stem = re.sub(r"\.[^.]+$", "", stem, flags=re.IGNORECASE)
            stem = re.sub(r"[^A-Za-z0-9_]+", "_", stem).strip("_").lower()
            return f"video_{stem or 'unknown'}"
        def natural_name_key(value: object) -> tuple:
            return tuple(
                (1, int(part)) if part.isdigit() else (0, part.lower())
                for part in re.split(r"(\d+)", str(value or ""))
            )
        def video_ref_sort_name(ref: dict) -> str:
            return str(ref.get("name") or ref.get("baseStem") or ref.get("stem") or "").strip()
        def video_ref_base_name(ref: dict) -> str:
            return str(ref.get("baseStem") or ref.get("stem") or ref.get("name") or "").strip()
        def video_ref_stem(ref: dict) -> str:
            stem = video_ref_base_name(ref)
            stem = re.sub(r"\.[^.]+$", "", stem, flags=re.IGNORECASE)
            return stem.lower()
        def narrative_video_name_sort_key(ref: dict) -> tuple:
            return (
                natural_name_key(video_ref_sort_name(ref)),
                natural_name_key(video_ref_base_name(ref)),
                narrative_video_sort_key(ref),
            )
        def timeline_clip_start(ref: dict) -> float | None:
            binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
            starts: list[float] = []
            for clip in binding.get("clips") or []:
                if not isinstance(clip, dict):
                    continue
                start = clip.get("start")
                if isinstance(start, (int, float)):
                    starts.append(float(start))
            return min(starts) if starts else None
        def remotecomm_timeline_order(key: str) -> dict[str, tuple]:
            order: dict[str, tuple] = {}
            for index, segment in enumerate(remotecomm_video_timeline_by_key.get(key) or []):
                stem = str(segment.get("videoStem") or "").strip().lower()
                if not stem or stem in order:
                    continue
                start = segment.get("startTime")
                start_key = float(start) if isinstance(start, (int, float)) else float(index)
                order[stem] = (index, start_key)
            return order
        def sort_refs_for_story_file(key: str, refs: list[dict]) -> list[dict]:
            remote_order = remotecomm_timeline_order(key)
            clip_timeline_present = any(timeline_clip_start(ref) is not None for ref in refs)
            if remote_order or clip_timeline_present:
                return sorted(
                    refs,
                    key=lambda ref: (
                        0,
                        remote_order[video_ref_stem(ref)],
                        narrative_video_name_sort_key(ref),
                    )
                    if video_ref_stem(ref) in remote_order
                    else (
                        1,
                        timeline_clip_start(ref),
                        narrative_video_name_sort_key(ref),
                    )
                    if timeline_clip_start(ref) is not None
                    else (
                        2,
                        narrative_video_name_sort_key(ref),
                    ),
                )
            return sorted(refs, key=narrative_video_name_sort_key)
        def note_attached_video_in_summary(payload: dict) -> None:
            summary = payload.get("summary")
            if not isinstance(summary, list):
                return
            stale_note = "Text-only candidate: no matching AnimeStudio cutscene asset, source link, or narrative video was found."
            refreshed_note = (
                "Text-only candidate: no matching AnimeStudio cutscene asset or source link was found; "
                "narrative video is attached separately."
            )
            for row in summary:
                if isinstance(row, dict) and row.get("text") == stale_note:
                    row["text"] = refreshed_note
        def strip_video_gender_prefix(stem: str) -> tuple[str, str]:
            match = re.match(r"^(?P<gender>f|m|fm)_(?P<rest>cs_video_.+)$", stem or "", flags=re.IGNORECASE)
            if not match:
                return "", stem or ""
            return match.group("gender").lower(), match.group("rest")
        def video_scene_hint(refs: list[dict]) -> str:
            for ref in refs:
                override = ref.get("_videoAttachmentAttachOverride")
                if not isinstance(override, dict):
                    continue
                target = str(override.get("targetKey") or ref.get("_resolvedKey") or "").strip()
                if target:
                    return strip_video_scene_prefix(target)
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                scene = str(binding.get("scene") or "").strip()
                if scene and not binding.get("isHint"):
                    return strip_video_scene_prefix(scene)
            for ref in refs:
                _gender, base = strip_video_gender_prefix(str(ref.get("baseStem") or ref.get("stem") or ""))
                for prefix in ("cs_video_dlg_", "cs_video_cutscene_", "cs_video_remotecomm_", "cs_video_"):
                    if base.startswith(prefix):
                        return strip_video_scene_prefix(base[len(prefix):])
                if base:
                    return strip_video_scene_prefix(base)
            return ""
        def strip_video_scene_prefix(scene: str) -> str:
            value = str(scene or "")
            for prefix in ("dlg_", "cutscene_", "remotecomm_", "radio_", "black_"):
                if value.startswith(prefix):
                    return value[len(prefix):]
            return value
        def video_mission_scene(refs: list[dict]) -> tuple[str, int]:
            scene_hint = video_scene_hint(refs)
            match = re.match(
                r"^(?P<mission>[a-z]+\d+m\d+(?:d\d+)?)(?:_(?P<scene>\d+).*)?$",
                scene_hint,
                flags=re.IGNORECASE,
            )
            if not match:
                return (scene_hint.split("_", 1)[0].lower() if scene_hint else "video", 0)
            return match.group("mission").lower(), int(match.group("scene") or 0)
        def video_title(refs: list[dict]) -> str:
            base_names = _unique_preserve(
                str(ref.get("baseStem") or ref.get("stem") or "")
                for ref in refs
                if ref.get("baseStem") or ref.get("stem")
            )
            if base_names:
                return base_names[0]
            names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
            return names[0] if names else "Narrative video"
        def video_text_candidate_rows(video_stem: str) -> list[dict]:
            prefix = f"{video_stem}_"
            rows: list[tuple[tuple[int, int, str], dict]] = []
            for row_id, text_entry in text_table.items():
                row_key = str(row_id or "")
                if not row_key.startswith(prefix):
                    continue
                suffix = row_key[len(prefix):]
                match = re.fullmatch(r"(?P<line>\d+)(?P<sub>d\d+)?(?:_[fm])?", suffix, flags=re.IGNORECASE)
                if not match:
                    continue
                sub = match.group("sub") or ""
                sub_order = int(sub[1:]) if sub else -1
                text = t(text_entry.get("id") if isinstance(text_entry, dict) else text_entry)
                line = {
                    "id": row_key,
                    "cid": f"{match.group('line')}{sub}",
                    "text": text,
                    "_debug": {
                        **source_ref(
                            "TextTable",
                            row_key,
                            pick_fields(text_entry, "id", "text") if isinstance(text_entry, dict) else {"value": text_entry},
                            videoStem=video_stem,
                            evidence="name-matched-video-text-candidate",
                        ),
                        "fields": {
                            "text": text_trace("TextTable", row_key, "id", text_entry),
                        },
                    },
                }
                if sub:
                    line["sub"] = sub
                rows.append(((int(match.group("line")), sub_order, row_key), line))
            return [line for _sort_key, line in sorted(rows, key=lambda item: item[0])]
        for ref in narrative_video_assets:
            original_resolved_key = resolve_video_key(ref)
            suppress_override = suppression_override_for(original_resolved_key, ref)
            attach_override = {} if suppress_override else manual_attachment_override_for(ref)
            resolved_key = (
                ""
                if suppress_override
                else str(attach_override.get("targetKey") or original_resolved_key or "")
            )
            resolved_kind = (
                entry_kind_by_key.get(resolved_key, "")
                if resolved_key
                else ""
            )
            # Rule: a video is always emitted as a standalone `video_*` bundle.
            # When story-key resolution maps it to another file, it also embeds
            # there. Timeline-backed refs render at their authored positions.
            standalone_ref = dict(ref)
            standalone_ref["_resolvedKey"] = resolved_key
            standalone_ref["_resolvedKind"] = resolved_kind
            if suppress_override:
                standalone_ref["_suppressedResolvedKey"] = original_resolved_key
                standalone_ref["_videoAttachmentOverride"] = suppress_override
            if attach_override:
                standalone_ref["_videoAttachmentAttachOverride"] = attach_override
            should_embed_inline = bool(resolved_key)
            if should_embed_inline:
                resolved_ref = dict(ref)
                resolved_ref["resolvedKey"] = resolved_key
                if attach_override:
                    resolved_ref["attachmentOverride"] = attach_override
                resolved_videos[resolved_key].append(resolved_ref)
            standalone_videos[standalone_video_key(ref)].append(standalone_ref)
            if suppress_override:
                suppressed_inline_videos.append(standalone_ref)
            elif attach_override:
                manual_attached_inline_videos.append(standalone_ref)
            elif not resolved_key:
                unresolved_videos.append(ref)
        authoritative_evidence: list[dict] = []
        def timeline_video_evidence_rows(key: str, refs: list[dict]) -> list[dict]:
            rows: list[dict] = []
            seen: set[tuple[str, str, str]] = set()
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                if not binding or binding.get("isHint"):
                    continue
                source_kinds = set(binding.get("sourceKinds") or [])
                if "timelinePlayable" not in source_kinds:
                    continue
                evidence_sources = [
                    source for source in (binding.get("evidence") or [])
                    if isinstance(source, dict) and source.get("kind") == "timelinePlayable"
                ]
                clips = [
                    clip for clip in (binding.get("clips") or [])
                    if isinstance(clip, dict)
                ]
                evidence_key = (
                    str(binding.get("fmvId") or ref.get("stem") or ""),
                    str(ref.get("rel") or ""),
                    key,
                )
                if evidence_key in seen:
                    continue
                seen.add(evidence_key)
                rows.append({
                    "webuiKey": key,
                    "webuiFile": f"data/lang/{language_code}/conv/{key}.json",
                    "video": {
                        "name": str(ref.get("name") or ""),
                        "rel": str(ref.get("rel") or ""),
                        "source": str(ref.get("source") or ""),
                        "format": str(ref.get("format") or ""),
                        "size": int(ref.get("size") or 0),
                    },
                    "binding": {
                        "fmvId": str(binding.get("fmvId") or ref.get("stem") or ""),
                        "scene": str(binding.get("scene") or ""),
                        "mission": str(binding.get("mission") or ""),
                        "sourceKinds": sorted(source_kinds),
                    },
                    "evidence": {
                        "method": "timelinePlayable",
                        "why": (
                            "Timeline FMV clip references a BeyondFMVPlayableAsset; "
                            "that playable's fmvId selects this narrative video."
                        ),
                        "sources": evidence_sources,
                        "clips": clips[:8],
                    },
                })
            return rows
        def standalone_binding_summary(refs: list[dict]) -> tuple[str, str]:
            for ref in refs:
                override = ref.get("_videoAttachmentOverride")
                if not isinstance(override, dict):
                    continue
                target = str(override.get("targetKey") or ref.get("_suppressedResolvedKey") or "")
                target_note = f" to `{target}`" if target else ""
                return (
                    f"Attachment status: manual override suppresses inline attachment{target_note}; kept standalone in WebUI",
                    "standaloneVideoManualOverrideSuppressedInline",
                )
            for ref in refs:
                override = ref.get("_videoAttachmentAttachOverride")
                if not isinstance(override, dict):
                    continue
                target = str(override.get("targetKey") or ref.get("_resolvedKey") or "")
                if not target:
                    continue
                resolved_kind = str(ref.get("_resolvedKind") or "")
                label = {
                    "cutscene": "cutscene",
                    "dlg": "dialog",
                    "remotecomm": "remotecomm",
                }.get(resolved_kind, "story file")
                return (
                    f"Attachment status: manual override attaches inline to {label} `{target}`; kept standalone in WebUI",
                    "standaloneVideoManualOverrideAttachedInline",
                )
            for ref in refs:
                binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                if not binding or binding.get("isHint"):
                    continue
                scene = str(binding.get("scene") or "")
                if not scene:
                    continue
                resolved_kind = str(ref.get("_resolvedKind") or "")
                resolved_key = str(ref.get("_resolvedKey") or "")
                if resolved_kind == "cutscene":
                    label, target = "cutscene", resolved_key or scene
                elif resolved_kind == "dlg":
                    label, target = "dialog", resolved_key or scene
                elif resolved_kind == "remotecomm":
                    label, target = "remotecomm", resolved_key or scene
                elif scene.startswith("cutscene_"):
                    label, target = "cutscene", scene
                elif scene.startswith("dlg_"):
                    label, target = "dialog", scene
                elif scene.startswith("remotecomm_"):
                    label, target = "remotecomm", scene
                else:
                    label, target = "scene", scene
                attached_note = " (also embedded inline)" if resolved_kind else ""
                return (
                    f"Attachment status: timeline-bound to {label} `{target}`{attached_note}; kept standalone in WebUI",
                    "standaloneVideoBoundButKeptSeparate",
                )
            resolved_key = next(
                (
                    str(ref.get("_resolvedKey") or "")
                    for ref in refs
                    if ref.get("_resolvedKey")
                ),
                "",
            )
            resolved_kind = next(
                (
                    str(ref.get("_resolvedKind") or "")
                    for ref in refs
                    if ref.get("_resolvedKind")
                ),
                "",
            )
            if resolved_key:
                label = {
                    "cutscene": "cutscene",
                    "dlg": "dialog",
                    "remotecomm": "remotecomm",
                }.get(resolved_kind, "story file")
                return (
                    f"Attachment status: filename-mapped to {label} `{resolved_key}` (also embedded inline); kept standalone in WebUI",
                    "standaloneVideoFilenameMapped",
                )
            return (
                "Attachment status: no non-name binding found for a dialog or cutscene",
                "standaloneVideoNoAuthoritativeStoryBinding",
            )
        def emit_standalone_video_outputs() -> list[dict]:
            entries: list[dict] = []
            for key, raw_refs in sorted(standalone_videos.items()):
                refs = sorted(raw_refs, key=narrative_video_name_sort_key)
                if not refs:
                    continue
                compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
                omitted = max(0, len(refs) - len(compact_refs))
                mission, scene = video_mission_scene(refs)
                type_, act = parse_mission(mission)
                title = video_title(refs)
                names = _unique_preserve(str(ref.get("name") or "") for ref in refs if ref.get("name"))
                source_counts = Counter(str(ref.get("source") or "") for ref in refs)
                format_counts = Counter(str(ref.get("format") or "") for ref in refs)
                attachment_text, attachment_reason = standalone_binding_summary(refs)
                attached_story_key = next(
                    (
                        str(ref.get("_resolvedKey") or "")
                        for ref in refs
                        if ref.get("_resolvedKey")
                    ),
                    "",
                )
                text_candidates = video_text_candidate_rows(title)
                # `title` is the asset baseStem (e.g. cs_video_e0m0_3); the game
                # ships no localized title for FMVs. Keep it as a search hint
                # and as the lead summary label, but don't expose it as a
                # `title` field 鈥?that would mislead the WebUI into treating
                # the stem as a human-readable name. cutscene/dlg/radio bundles
                # also omit the field.
                #
                # We do NOT promote `cs_video_<scene>_NN` TextTable rows to
                # playable lines. They share a name with the FMV, but no
                # decoded subtitle track carries those keys. Keep them as
                # explicit candidates so the evidence level stays visible.
                summary_rows = [
                    {"text": f"Standalone narrative video: {title}"},
                    {"text": f"Mission: {mission}"},
                    {"text": f"Files: {len(refs)} exported variant(s)"},
                    {"text": attachment_text},
                ]
                if text_candidates:
                    candidate_preview = " / ".join(
                        str(row.get("text") or "")
                        for row in text_candidates[:4]
                        if row.get("text")
                    )
                    summary_rows.append({
                        "text": (
                            "Name-matched TextTable candidates: "
                            + (candidate_preview or f"{len(text_candidates)} row(s)")
                        ),
                    })
                    summary_rows.append({
                        "text": "Video text note: these rows share the FMV stem but are not tied by a decoded subtitle track.",
                    })
                payload = {
                    "key": key,
                    "kind": "video",
                    "mission": mission,
                    "scene": scene,
                    "lines": [],
                    "summary": summary_rows,
                    "narrativeVideos": compact_refs,
                    "_debug": {
                        "title": mission_name_trace(mission),
                        "narrativeVideos": {
                            "source": {
                                "key": key,
                                "count": len(refs),
                                "shown": len(compact_refs),
                                "omitted": omitted,
                                "reason": attachment_reason,
                            },
                        },
                    },
                }
                if text_candidates:
                    payload["videoTextCandidates"] = text_candidates[:16]
                if omitted:
                    payload["narrativeVideosOmitted"] = omitted
                write_conv_payload(key, payload)
                entry = {
                    "k": key,
                    "d": "video",
                    "m": mission,
                    "s": scene,
                    "t": type_ if type_ != "?" else "other",
                    "a": act,
                    "c": [],
                    "n": 0,
                    "p": preview(", ".join(names) or title),
                    "tags": ["narrativeVideo"],
                    "vid": narrative_video_index_summary(refs),
                    "x": merge_search_text(
                        " ".join([
                            key,
                            title,
                            mission,
                            " ".join(names),
                            " ".join(str(ref.get("rel") or "") for ref in refs),
                            " ".join(str(ref.get("stem") or "") for ref in refs),
                        ]),
                        mission_context_text(mission),
                    ),
                }
                if attached_story_key:
                    entry["attachTo"] = attached_story_key
                entry["videoSources"] = {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                }
                entry["videoFormats"] = {
                    fmt: format_counts[fmt]
                    for fmt in sorted(format_counts)
                    if fmt
                }
                if not entry["x"]:
                    entry.pop("x", None)
                entries.append(entry)
            return entries
        attached_rows: list[dict] = []
        attached_refs = 0
        for entry in index_entries:
            key = str(entry.get("k") or "")
            refs = sort_refs_for_story_file(key, resolved_videos.get(key) or [])
            if not refs:
                continue
            attached_refs += len(refs)
            authoritative_evidence.extend(timeline_video_evidence_rows(key, refs))
            compact_refs = [compact_narrative_video_ref(ref) for ref in refs[:16]]
            omitted = max(0, len(refs) - len(compact_refs))
            entry["vid"] = narrative_video_index_summary(refs)
            entry["x"] = merge_search_text(entry.get("x", ""), narrative_video_search_text(refs))
            tags = entry.setdefault("tags", [])
            if "narrativeVideo" not in tags:
                tags.append("narrativeVideo")
            conv_media_tags_by_key[key].add("mediaVideo")
            conv_path = conv_dir / f"{key}.json"
            if conv_path.exists():
                try:
                    payload = json.loads(conv_path.read_text(encoding="utf-8"))
                except Exception:
                    payload = None
                if isinstance(payload, dict):
                    payload["narrativeVideos"] = compact_refs
                    note_attached_video_in_summary(payload)
                    if omitted:
                        payload["narrativeVideosOmitted"] = omitted
                    if isinstance(payload.get("cutscene"), dict):
                        payload["cutscene"]["videoRefs"] = compact_refs
                    clip_starts: list[float] = []
                    if str(entry.get("d") or "") in ("cutscene", "remotecomm"):
                        for ref in refs:
                            binding = ref.get("binding") if isinstance(ref.get("binding"), dict) else {}
                            for clip in binding.get("clips") or []:
                                if not isinstance(clip, dict):
                                    continue
                                start = clip.get("start")
                                if isinstance(start, (int, float)):
                                    clip_starts.append(float(start))
                    debug = payload.setdefault("_debug", {})
                    debug["narrativeVideos"] = {
                        "source": {
                            "key": key,
                            "count": len(refs),
                            "shown": len(compact_refs),
                            "omitted": omitted,
                            **(
                                {"timelineAlignedWith": key}
                                if clip_starts
                                else {}
                            ),
                        },
                    }
                    unplaced_video_stems = sorted({
                        str(ref.get("baseStem") or ref.get("stem") or ref.get("name") or "")
                        for ref in refs
                        if not any(
                            isinstance(clip, dict) and isinstance(clip.get("start"), (int, float))
                            for clip in (((ref.get("binding") or {}).get("clips")) or [])
                        )
                    })
                    if unplaced_video_stems and str(entry.get("d") or "") in ("cutscene", "remotecomm"):
                        unplaced_video_stems = []
                    if unplaced_video_stems:
                        existing_warnings = [
                            warning for warning in (payload.get("warnings") or [])
                            if isinstance(warning, dict)
                            and warning.get("code") != "narrativeVideoUnplaced"
                        ]
                        existing_warnings.append({
                            "code": "narrativeVideoUnplaced",
                            "status": "missing",
                            "videoStems": unplaced_video_stems,
                            "videoCount": len(unplaced_video_stems),
                        })
                        payload["warnings"] = existing_warnings
                    expected_remotecomm_video_stems = remotecomm_expected_video_stems_by_key.get(key, [])
                    if expected_remotecomm_video_stems and str(entry.get("d") or "") == "remotecomm":
                        present_video_stems = {
                            str(ref.get("baseStem") or ref.get("stem") or "").strip().lower()
                            for ref in refs
                            if ref.get("baseStem") or ref.get("stem")
                        }
                        missing_video_stems = [
                            stem for stem in expected_remotecomm_video_stems
                            if stem.lower() not in present_video_stems
                        ]
                        existing_warnings = [
                            warning for warning in (payload.get("warnings") or [])
                            if isinstance(warning, dict)
                            and warning.get("code") != "remotecommNarrativeVideoMissing"
                        ]
                        if missing_video_stems:
                            existing_warnings.append({
                                "code": "remotecommNarrativeVideoMissing",
                                "status": "missing",
                                "videoStems": missing_video_stems,
                                "videoCount": len(missing_video_stems),
                                "evidence": "RemoteCommonTable middleId video lookup",
                            })
                        if existing_warnings:
                            payload["warnings"] = existing_warnings
                        else:
                            payload.pop("warnings", None)
                    write_json(conv_path, payload)
                    remember_written(conv_path, written_conv_paths)
            source_counts = Counter(str(ref.get("source") or "") for ref in refs)
            attached_rows.append({
                "key": key,
                "kind": str(entry.get("d") or ""),
                "mission": str(entry.get("m") or ""),
                "videos": len(refs),
                "sources": {
                    source: source_counts[source]
                    for source in sorted(source_counts)
                    if source
                },
                "files": _unique_preserve(
                    str(ref.get("name") or "")
                    for ref in refs
                    if ref.get("name")
                )[:12],
            })
        standalone_entries = emit_standalone_video_outputs()
        for entry in standalone_entries:
            index_entries.append(entry)
            conv_media_tags_by_key[str(entry.get("k") or "")].add("mediaVideo")
        unresolved_rows = [
            {
                "name": str(ref.get("name") or ""),
                "kind": str(ref.get("kind") or ""),
                "rel": str(ref.get("rel") or ""),
                "keyCandidates": list(ref.get("keyCandidates") or []),
            }
            for ref in unresolved_videos
        ]
        report = {
            "generated": int(time.time()),
            "language": language_code,
            "summary": {
                "scannedVideos": len(narrative_video_assets),
                "attachedKeys": len(attached_rows),
                "attachedVideos": attached_refs,
                "manualAttachedInlineVideos": len(manual_attached_inline_videos),
                "suppressedInlineVideos": len(suppressed_inline_videos),
                "authoritativeEvidenceRows": len(authoritative_evidence),
                "standaloneVideoKeys": len(standalone_entries),
                "standaloneVideoRefs": sum(len(rows) for rows in standalone_videos.values()),
                "unresolvedVideos": len(unresolved_videos),
                "cutsceneVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "cutscene"),
                "remotecommVideoFiles": sum(1 for ref in narrative_video_assets if ref.get("kind") == "remotecomm"),
            },
            "attached": sorted(
                attached_rows,
                key=lambda row: (-int(row.get("videos") or 0), row.get("key") or ""),
            )[:500],
            "standalone": [
                {
                    "key": str(entry.get("k") or ""),
                    "mission": str(entry.get("m") or ""),
                    "videos": int((entry.get("vid") or {}).get("n") or 0),
                    "files": list((entry.get("vid") or {}).get("files") or []),
                }
                for entry in standalone_entries[:500]
            ],
            "unresolved": unresolved_rows[:500],
            "manualAttachedInline": [
                {
                    "name": str(ref.get("name") or ""),
                    "targetKey": str((ref.get("_videoAttachmentAttachOverride") or {}).get("targetKey") or ""),
                    "stems": list((ref.get("_videoAttachmentAttachOverride") or {}).get("stems") or []),
                    "note": str((ref.get("_videoAttachmentAttachOverride") or {}).get("note") or ""),
                    "source": str((ref.get("_videoAttachmentAttachOverride") or {}).get("source") or ""),
                }
                for ref in manual_attached_inline_videos[:500]
            ],
            "suppressedInline": [
                {
                    "name": str(ref.get("name") or ""),
                    "targetKey": str(
                        ((ref.get("_videoAttachmentOverride") or {}).get("targetKey"))
                        or ref.get("_suppressedResolvedKey")
                        or ""
                    ),
                    "stems": list((ref.get("_videoAttachmentOverride") or {}).get("stems") or []),
                    "note": str((ref.get("_videoAttachmentOverride") or {}).get("note") or ""),
                    "source": str((ref.get("_videoAttachmentOverride") or {}).get("source") or ""),
                }
                for ref in suppressed_inline_videos[:500]
            ],
        }
        report_json = REPORTS_DIR / f"narrative_videos_{language_code}.json"
        report_md = REPORTS_DIR / f"narrative_videos_{language_code}.md"
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        evidence_payload = {
            "generated": report["generated"],
            "language": language_code,
            "summary": {
                "rows": len(authoritative_evidence),
                "webuiKeys": len({row.get("webuiKey") for row in authoritative_evidence}),
                "method": "timelinePlayable",
            },
            "rows": sorted(
                authoritative_evidence,
                key=lambda row: (
                    str(row.get("webuiKey") or ""),
                    str(((row.get("binding") or {}).get("fmvId")) or ""),
                    str(((row.get("video") or {}).get("rel")) or ""),
                ),
            ),
        }
        evidence_path = out_dir / "narrative_video_evidence.json"
        write_json(evidence_path, evidence_payload)
        write_json(report_json, report, indent=2, compact=False)
        report_md.write_text(render_narrative_video_report_md(report), encoding="utf-8")
        report["report"] = {
            "json": repo_rel(report_json),
            "markdown": repo_rel(report_md),
            "evidence": repo_rel(evidence_path),
        }
        return report
    narrative_video_report = attach_narrative_videos_to_outputs()
    def normalize_index_entry_defaults(entry: dict) -> None:
        type_key = str(entry.get("t") or "").strip()
        if not type_key or type_key in {"?", "x"}:
            entry["t"] = "other"
        raw_tags = list(entry.get("tags") or [])
        raw_tags.extend(sorted(conv_media_tags_by_key.get(str(entry.get("k") or ""), set())))
        tags = []
        for raw_tag in raw_tags:
            tag = str(raw_tag or "").strip()
            if tag and tag not in tags:
                tags.append(tag)
        entry["tags"] = tags or ["other"]
    for entry in index_entries:
        normalize_index_entry_defaults(entry)
    # Sort index by type, act, mission, scene
    index_entries.sort(key=lambda e: (e["d"], e["t"], e["a"], e["m"], e["s"]))
    mission_names = {
        mission: name
        for mission in sorted({e["m"] for e in index_entries if e.get("m")})
        if (name := mission_name(mission))
    }
    present_missions = {e["m"] for e in index_entries if e.get("m")}
    for mission, name in sorted(extra_mission_names.items()):
        if mission in present_missions and name:
            mission_names.setdefault(mission, name)
    def env_entry_search_text(env_entry: dict) -> str:
        parts: list[str] = []
        if env_entry.get("id"):
            parts.append(str(env_entry["id"]))
        if env_entry.get("lines"):
            parts.append(indexed_line_haystack(env_entry["lines"], "text", "actor", "aid", "emoji"))
        npc = env_entry.get("npc") or {}
        for field in ("npcId", "name", "title", "dialogSelector"):
            value = npc.get(field)
            if value:
                parts.append(str(value))
        return " ".join(part for part in parts if part)
    index_entry_by_key = {
        entry["k"]: entry
        for entry in index_entries
        if entry.get("k")
    }
    scene_bindings_by_mission: dict[str, dict[str, dict]] = defaultdict(dict)
    for mission, refs in mission_level_refs.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in SCENE_BINDING_TARGET_KINDS
        }
        if not scene_targets:
            continue
        processed_chain_levels: set[str] = set()
        for ref in refs:
            level_id = ref.get("levelId") or ""
            if not level_id:
                continue
            leveldata_path = ROOT / ref["file"]
            named_entries = _load_leveldata_named_entries(leveldata_path)
            if any(LT_BINDING_RE.match(entry["text"]) for entry in named_entries):
                levelscript_info = _load_levelscript_binding_data(level_id)
                binding_groups = _build_level_binding_groups(
                    named_entries,
                    levelscript_info["uidPayloads"],
                    dialog_scene_out_key,
                    mission,
                )
                for group in binding_groups:
                    group_scene_keys = {
                        payload["sceneKey"]
                        for row in group["rows"]
                        for payload in row.get("payloads") or []
                        if payload.get("sceneKey")
                    }
                    for scene_key in sorted(group_scene_keys & scene_targets):
                        scene_entry = scene_bindings_by_mission[mission].setdefault(
                            scene_key,
                            {"groups": [], "chains": []},
                        )
                        scene_entry["groups"].append({
                            "label": group["label"],
                            "levelId": level_id,
                            "hostType": ref.get("hostType") or "",
                            "levelKind": ref.get("kind") or "",
                            "levelDataFile": ref["file"],
                            "rows": group["rows"],
                            "_debug": {
                                "source": {
                                    "file": ref["file"],
                                    "levelId": level_id,
                                    "hostType": ref.get("hostType") or "",
                                    "kind": ref.get("kind") or "",
                                },
                            },
                        })
            if level_id in processed_chain_levels:
                continue
            processed_chain_levels.add(level_id)
            level_chain_map = _build_levelscript_scene_chain_map(level_id, dialog_scene_out_key, mission)
            for scene_key, chains in level_chain_map.items():
                if scene_key not in scene_targets:
                    continue
                scene_entry = scene_bindings_by_mission[mission].setdefault(
                    scene_key,
                    {"groups": [], "chains": []},
                )
                scene_entry["chains"].extend(chains)
    for mission, scene_map in scene_bindings_by_mission.items():
        for scene_key, scene_entry in scene_map.items():
            scene_entry["groups"].sort(
                key=lambda group: (
                    group.get("levelId") or "",
                    group.get("label") or "",
                    group.get("levelDataFile") or "",
                )
            )
            scene_entry["chains"].sort(
                key=lambda chain: (
                    chain.get("levelId") or "",
                    chain.get("file") or "",
                    (chain.get("steps") or [{}])[0].get("localId", 0),
                )
            )
            index_entry = index_entry_by_key.get(scene_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                _scene_binding_search_text(scene_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "levelBinding" not in tags:
                tags.append("levelBinding")
    scene_env_talks_by_mission: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for mission, env_entries in story_env_entries_by_mission.items():
        scene_targets = {
            entry["k"]
            for entry in index_entries
            if entry.get("m") == mission and entry.get("d") in ("dlg", "misc")
        }
        if not scene_targets:
            continue
        scene_tracking: dict[str, dict[str, set[str]]] = defaultdict(
            lambda: {"levels": set(), "proxies": set()}
        )
        if flow := load_mission_flow(mission):
            for quest in flow.get("quests") or []:
                quest_targets: list[str] = []
                for dialog_id in quest.get("dialogs") or []:
                    out_key = dialog_scene_out_key(dialog_id)
                    if out_key and out_key in scene_targets and out_key not in quest_targets:
                        quest_targets.append(out_key)
                if not quest_targets:
                    continue
                quest_levels = {
                    hint["scene"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("scene")
                }
                quest_proxies = {
                    hint["npcProxyId"]
                    for hint in (quest.get("tracking") or [])
                    if hint.get("npcProxyId")
                }
                for out_key in quest_targets:
                    scene_tracking[out_key]["levels"].update(quest_levels)
                    scene_tracking[out_key]["proxies"].update(quest_proxies)
        only_scene_target = next(iter(scene_targets)) if len(scene_targets) == 1 else ""
        for env_entry in env_entries:
            hints = env_entry.pop("_attachHints", None) or {}
            env_levels = set(hints.get("levels") or [])
            env_proxies = set(hints.get("proxies") or [])
            proxy_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_proxies and env_proxies & tracking["proxies"]
            }
            level_hits = {
                out_key
                for out_key, tracking in scene_tracking.items()
                if env_levels and env_levels & tracking["levels"]
            }
            target_key = ""
            binding_source: dict = {}
            if len(proxy_hits) == 1:
                target_key = next(iter(proxy_hits))
                binding_source = {
                    "mode": "npcProxyId",
                    "targetKey": target_key,
                    "matchedProxyIds": sorted(
                        env_proxies & scene_tracking[target_key]["proxies"]
                    ),
                    "candidateSceneKeys": sorted(proxy_hits),
                }
            elif not proxy_hits and len(level_hits) == 1:
                target_key = next(iter(level_hits))
                binding_source = {
                    "mode": "sceneLevel",
                    "targetKey": target_key,
                    "matchedLevels": sorted(
                        env_levels & scene_tracking[target_key]["levels"]
                    ),
                    "candidateSceneKeys": sorted(level_hits),
                }
            elif not proxy_hits and not level_hits and only_scene_target:
                target_key = only_scene_target
                binding_source = {
                    "mode": "onlySceneInMission",
                    "targetKey": target_key,
                }
            if not target_key:
                continue
            env_entry["_debug"]["sceneBinding"] = {"source": binding_source}
            scene_env_talks_by_mission[mission][target_key].append(env_entry)
            if env_index_entry := index_entry_by_key.get(env_entry.get("key") or ""):
                env_index_entry["attachTo"] = target_key
            index_entry = index_entry_by_key.get(target_key)
            if not index_entry:
                continue
            index_entry["x"] = merge_search_text(
                index_entry.get("x", ""),
                env_entry_search_text(env_entry),
            )
            tags = index_entry.setdefault("tags", [])
            if "envTalk" not in tags:
                tags.append("envTalk")
    mission_extras_payload: dict[str, dict] = {}
    for mission in sorted(
        set(scene_env_talks_by_mission)
        | set(scene_bindings_by_mission)
        | set(mission_note_by_mission)
        | set(mission_level_refs)
    ):
        extra: dict[str, list[dict]] = {}
        if mission in mission_note_by_mission:
            extra["notes"] = mission_note_by_mission[mission]
        if mission in mission_level_refs:
            extra["levelRefs"] = mission_level_refs[mission]
        if mission in scene_bindings_by_mission:
            extra["sceneBindings"] = {
                out_key: scene_bindings_by_mission[mission][out_key]
                for out_key in sorted(scene_bindings_by_mission[mission])
            }
        if mission in scene_env_talks_by_mission:
            extra["sceneEnvTalk"] = {
                out_key: scene_env_talks_by_mission[mission][out_key]
                for out_key in sorted(scene_env_talks_by_mission[mission])
            }
        mission_extras_payload[mission] = extra
    # Mission flow graphs from MissionRuntimeAsset. Story-gated dialog
    # ordering + choice-branches live here; pure-env ambient scenes do not.
    scene_keys_by_mission: dict[str, set[str]] = defaultdict(set)
    story_kind_by_key: dict[str, str] = {}
    story_owner_by_key: dict[str, str] = {}
    for entry in index_entries:
        story_key = str(entry.get("k") or "")
        if story_key:
            entry_kind = str(entry.get("d") or "story")
            story_kind_by_key[story_key] = (
                "dialog" if entry_kind == "dlg" else entry_kind
            )
            story_owner_by_key[story_key] = str(entry.get("m") or "")
        if entry.get("d") in MISSION_SCENE_ENTRY_KINDS:
            scene_keys_by_mission[entry["m"]].add(entry["k"])
    present_index_missions = sorted({e["m"] for e in index_entries if e.get("m")})
    mission_runtime_ids: list[str] = []
    mission_runtime_paths: list[Path] = []
    mission_variant_ids_by_parent: dict[str, list[str]] = defaultdict(list)
    for path in sorted(MRA_DIR.glob("*.json")):
        stem = path.stem
        if stem.endswith("_meta"):
            continue
        mission_runtime_ids.append(stem)
        mission_runtime_paths.append(path)
        parent_mission = re.sub(r"d\d+$", "", stem)
        if parent_mission != stem and parent_mission in scene_keys_by_mission:
            mission_variant_ids_by_parent[parent_mission].append(stem)
    mission_flow_missions = sorted(set(present_index_missions) | set(mission_runtime_ids))
    all_available_scene_keys = set().union(*scene_keys_by_mission.values())
    all_story_entry_keys = set(story_kind_by_key)
    def resolve_scene_ref_out_key(raw_ref: str, available_scene_keys: set[str]) -> str:
        if not raw_ref:
            return ""
        for candidate in _unique_preserve([
            str(raw_ref or "").strip(),
            *_scene_ref_alias_candidates(raw_ref),
        ]):
            if not candidate:
                continue
            if candidate in available_scene_keys:
                return candidate
            if out_key := dialog_scene_out_key(candidate):
                if out_key in available_scene_keys:
                    return out_key
            if canonical_cutscene := _canonical_cutscene_key(candidate):
                if canonical_cutscene in available_scene_keys:
                    return canonical_cutscene
        return ""
    def quest_area_scene_refs(quest: dict, available_scene_keys: set[str]) -> list[str]:
        refs: list[str] = []
        for raw_ref in _quest_area_story_refs(quest):
            resolved = resolve_scene_ref_out_key(raw_ref, available_scene_keys)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs
    def quest_leveldata_scene_refs(quest: dict, available_scene_keys: set[str]) -> list[str]:
        refs: list[str] = []
        for row in quest.get("levelDataStoryRefs") or []:
            raw_ref = row.get("storyRef") if isinstance(row, dict) else row
            resolved = resolve_scene_ref_out_key(raw_ref or "", available_scene_keys)
            if resolved and resolved not in refs:
                refs.append(resolved)
        return refs
    def flow_has_available_scene_ref(flow: dict | None, available_scene_keys: set[str]) -> bool:
        if not flow or not available_scene_keys:
            return False
        for quest in flow.get("quests") or []:
            for field_name in ("dialogs", "cutscenes", "remotecomms", "radios", "failStoryRefs"):
                for raw_ref in quest.get(field_name) or []:
                    if resolve_scene_ref_out_key(raw_ref, available_scene_keys):
                        return True
            if quest_area_scene_refs(quest, available_scene_keys):
                return True
            if quest_leveldata_scene_refs(quest, available_scene_keys):
                return True
            for proxy_ref in quest.get("proxyDialogs") or []:
                raw_ref = (
                    proxy_ref.get("dialogId")
                    if isinstance(proxy_ref, dict)
                    else proxy_ref
                )
                if resolve_scene_ref_out_key(raw_ref or "", available_scene_keys):
                    return True
        return False
    def mission_graph_flow(mission: str, flow: dict | None) -> dict | None:
        """Return the flow used only for scene-graph ordering.
        Some playable mission variants (`c16m4d5`, `e10m4d5`, etc.) carry
        MissionRuntime quest refs for parent story keys. The parent mission is
        where those story files live in the WebUI, so fold matching variant
        quests into the graph pass only when their refs resolve to actual
        parent nodes.
        """
        available = scene_keys_by_mission.get(mission, set())
        if not available:
            return flow
        variant_quests: list[dict] = []
        variant_missions: list[str] = []
        for variant_mission in mission_variant_ids_by_parent.get(mission) or []:
            variant_flow = load_mission_flow(variant_mission)
            if not flow_has_available_scene_ref(variant_flow, available):
                continue
            variant_missions.append(variant_mission)
            for quest in (variant_flow or {}).get("quests") or []:
                variant_quest = copy.deepcopy(quest)
                variant_quest["variantMission"] = variant_mission
                variant_quests.append(variant_quest)
        if not variant_quests:
            return flow
        graph_flow = copy.deepcopy(flow or {"quests": []})
        graph_flow["quests"] = [
            *list(graph_flow.get("quests") or []),
            *variant_quests,
        ]
        graph_flow["variantMissionIds"] = variant_missions
        return graph_flow

    def build_mission_scene_pins(
        flow: dict | None,
        available_scene_keys: set[str],
    ) -> dict[str, list[dict]]:
        if not flow or not available_scene_keys:
            return {}
        scene_rows: dict[str, dict[tuple, dict]] = defaultdict(dict)
        for quest in flow.get("quests") or []:
            # Prefer stronger authored/runtime scene refs for spatial pinning.
            # Radios are only used when a quest has no dialog/cutscene/remotecomm target.
            primary_scene_refs = _unique_preserve([
                *(
                    resolved
                    for dialog_id in (quest.get("dialogs") or [])
                    if (resolved := resolve_scene_ref_out_key(dialog_id, available_scene_keys))
                ),
                *(
                    resolved
                    for cutscene_id in (quest.get("cutscenes") or [])
                    if (resolved := resolve_scene_ref_out_key(cutscene_id, available_scene_keys))
                ),
                *(
                    resolved
                    for remote_id in (quest.get("remotecomms") or [])
                    if (resolved := resolve_scene_ref_out_key(remote_id, available_scene_keys))
                ),
            ])
            radio_scene_refs = _unique_preserve([
                resolved
                for radio_id in (quest.get("radios") or [])
                if (resolved := resolve_scene_ref_out_key(radio_id, available_scene_keys))
            ])
            area_scene_refs = quest_area_scene_refs(quest, available_scene_keys)
            scene_refs = primary_scene_refs or radio_scene_refs or area_scene_refs
            if len(scene_refs) != 1:
                continue
            scene_key = scene_refs[0]
            for pin in quest.get("pins") or []:
                position = pin.get("position") or {}
                key = (
                    pin.get("scene") or "",
                    pin.get("sourceType") or "",
                    pin.get("trackingType") or "",
                    pin.get("missionAreaId") or "",
                    pin.get("npcProxyId") or "",
                    round(float(position.get("x", 0.0)), 3),
                    round(float(position.get("y", 0.0)), 3),
                    round(float(position.get("z", 0.0)), 3),
                )
                row = scene_rows[scene_key].get(key)
                if row is None:
                    row = {
                        "scene": pin.get("scene") or "",
                        "sourceType": pin.get("sourceType") or "",
                        "trackingType": pin.get("trackingType") or "",
                        "position": {
                            "x": float(position.get("x", 0.0)),
                            "y": float(position.get("y", 0.0)),
                            "z": float(position.get("z", 0.0)),
                        },
                        "questIds": [],
                        "flowIndices": [],
                    }
                    if pin.get("missionAreaId"):
                        row["missionAreaId"] = pin["missionAreaId"]
                    if pin.get("npcProxyId"):
                        row["npcProxyId"] = pin["npcProxyId"]
                    if pin.get("radius") is not None:
                        row["radius"] = pin["radius"]
                    if pin.get("routePointCount") is not None:
                        row["routePointCount"] = pin["routePointCount"]
                    scene_rows[scene_key][key] = row
                quest_id = quest.get("id") or ""
                if quest_id and quest_id not in row["questIds"]:
                    row["questIds"].append(quest_id)
                flow_index = quest.get("flowIndex")
                if flow_index is not None and flow_index not in row["flowIndices"]:
                    row["flowIndices"].append(flow_index)
        return {
            scene_key: sorted(
                rows.values(),
                key=lambda row: (
                    min(row.get("flowIndices") or [10**9]),
                    row.get("scene") or "",
                    row.get("sourceType") or "",
                    row["position"]["x"],
                    row["position"]["z"],
                ),
            )
            for scene_key, rows in sorted(scene_rows.items())
            if rows
        }
    def build_mission_scene_graph(mission: str, flow: dict | None) -> dict | None:
        available = scene_keys_by_mission.get(mission, set())
        ui_nodes: set[str] = set()
        chain_nodes: set[str] = set()
        chain_sequences: list[dict] = []
        scene_chain_sequences: list[dict] = []
        story_call_items_by_file: dict[tuple[str, str], list[tuple[int, int, str]]] = defaultdict(list)
        seen_story_call_items: set[tuple[str, str, int, int, str]] = set()
        hash_terminal_contexts: list[dict] = []
        seen_hash_terminal_contexts: set[tuple] = set()
        call_server_callback_contexts: list[dict] = []
        seen_call_server_callback_contexts: set[tuple] = set()
        if flow:
            for quest in flow.get("quests") or []:
                for hint in quest.get("tracking") or []:
                    jump_id = hint.get("jumpId") or ""
                    if jump_id:
                        ui_nodes.add(f"ui:{jump_id}")
        seen_chain_signatures: set[tuple[str, tuple[str, ...]]] = set()
        def compact_levelscript_step(step: dict, node_key: str, payload_text: str) -> dict:
            source_info = (step.get("_debug") or {}).get("source") or {}
            row = {
                "nodeKey": node_key,
                "payloadText": payload_text,
                "localId": step.get("localId"),
                "nextId": step.get("nextId"),
            }
            compact_source = {
                key: source_info.get(key)
                for key in ("layout", "code", "kind", "uid", "start")
                if source_info.get(key) not in (None, "", [], {})
            }
            if compact_source:
                row["source"] = compact_source
            return {
                key: value
                for key, value in row.items()
                if value not in (None, "", [], {})
            }
        for scene_entry in (scene_bindings_by_mission.get(mission) or {}).values():
            for chain in scene_entry.get("chains") or []:
                sequence: list[str] = []
                sequence_steps: list[dict] = []
                for step in chain.get("steps") or []:
                    source_info = (step.get("_debug") or {}).get("source") or {}
                    start = source_info.get("start")
                    if not isinstance(start, int):
                        start = 10**9
                    for payload_index, payload in enumerate(step.get("payloads") or []):
                        raw_text = str(payload.get("text") or "")
                        node_key = str(
                            resolve_scene_ref_out_key(raw_text, available)
                            or payload.get("nodeKey")
                            or _scene_graph_runtime_payload_key(
                                raw_text,
                                mission,
                                dialog_scene_out_key,
                            )
                        )
                        if not node_key:
                            continue
                        file_ref = chain.get("file") or ""
                        level_id = chain.get("levelId") or ""
                        if is_call_server_self_uid_callback(node_key, step):
                            source_step = compact_levelscript_step(step, node_key, raw_text)
                            source_info = source_step.get("source") or {}
                            callback_signature = (
                                file_ref,
                                level_id,
                                str(source_info.get("uid") or "").casefold(),
                                node_key.casefold(),
                            )
                            if callback_signature not in seen_call_server_callback_contexts:
                                seen_call_server_callback_contexts.add(callback_signature)
                                preceding_scene_key = next(
                                    (
                                        key
                                        for key in reversed(sequence)
                                        if _is_story_scene_graph_kind(
                                            _scene_graph_node_kind(key, available)
                                        )
                                    ),
                                    "",
                                )
                                callback = {
                                    "kind": "levelscriptCallServerSelfUidCallback",
                                    "file": file_ref,
                                    "levelId": level_id,
                                    "callbackLabel": node_key,
                                    "recordUid": source_info.get("uid") or "",
                                    "identityRole": "self_uid_callback_label",
                                    "storyNode": False,
                                    "missionOwnershipEvidence": False,
                                    "orderEvidence": False,
                                    "sourceStep": source_step,
                                }
                                if preceding_scene_key:
                                    callback["precedingSceneKey"] = preceding_scene_key
                                call_server_callback_contexts.append(callback)
                            continue
                        if file_ref and _is_story_scene_graph_key(node_key, available):
                            signature = (file_ref, level_id, start, payload_index, node_key)
                            if signature not in seen_story_call_items:
                                seen_story_call_items.add(signature)
                                story_call_items_by_file[(file_ref, level_id)].append(
                                    (start, payload_index, node_key)
                                )
                        if not sequence or sequence[-1] != node_key:
                            sequence.append(node_key)
                            sequence_steps.append(
                                compact_levelscript_step(step, node_key, raw_text)
                            )
                if not sequence:
                    continue
                signature = (chain.get("file") or "", tuple(sequence))
                if signature in seen_chain_signatures:
                    continue
                seen_chain_signatures.add(signature)
                chain_nodes.update(sequence)
                scene_sequence = _compact_scene_graph_sequence(sequence, available)
                if scene_sequence:
                    scene_chain_sequences.append({
                        "file": chain.get("file") or "",
                        "levelId": chain.get("levelId") or "",
                        "sequence": scene_sequence,
                    })
                if len(sequence) < 2:
                    continue
                chain_sequences.append({
                    "file": chain.get("file") or "",
                    "levelId": chain.get("levelId") or "",
                    "sequence": sequence,
                })
                for pos, (src, dst) in enumerate(zip(sequence, sequence[1:])):
                    src_kind = _scene_graph_node_kind(src, available)
                    dst_kind = _scene_graph_node_kind(dst, available)
                    if src_kind == "levelscriptHash" and _is_story_scene_graph_kind(dst_kind):
                        scene_key = dst
                        hash_key = src
                        direction = "hash->story"
                    elif _is_story_scene_graph_kind(src_kind) and dst_kind == "levelscriptHash":
                        scene_key = src
                        hash_key = dst
                        direction = "story->hash"
                    else:
                        continue
                    file_ref = chain.get("file") or ""
                    level_id = chain.get("levelId") or ""
                    terminal_signature = (
                        file_ref,
                        level_id,
                        scene_key,
                        hash_key,
                        direction,
                        pos,
                    )
                    if terminal_signature in seen_hash_terminal_contexts:
                        continue
                    seen_hash_terminal_contexts.add(terminal_signature)
                    hash_terminal_contexts.append({
                        "kind": "levelscriptHashTerminal",
                        "file": file_ref,
                        "levelId": level_id,
                        "sceneKey": scene_key,
                        "hash": hash_key,
                        "direction": direction,
                        "sourceStep": sequence_steps[pos] if pos < len(sequence_steps) else {},
                        "hashStep": sequence_steps[pos + 1] if pos + 1 < len(sequence_steps) else {},
                    })
        story_call_contexts: list[dict] = []
        for (file_ref, level_id), items in sorted(story_call_items_by_file.items()):
            sequence: list[str] = []
            for _, __, node_key in sorted(items):
                if not sequence or sequence[-1] != node_key:
                    sequence.append(node_key)
            if sequence:
                story_call_contexts.append({
                    "kind": "levelscriptFileStoryCallOrder",
                    "file": file_ref,
                    "levelId": level_id,
                    "sequence": sequence,
                })
        all_nodes = set(available) | ui_nodes | chain_nodes
        if not all_nodes:
            return None
        mission_entries = [entry for entry in index_entries if entry.get("m") == mission]
        scene_file_order = build_mission_scene_file_order(
            mission_entries,
            flow,
        )
        mission_runtime_order_map = {
            str(key): int(value)
            for key, value in (scene_file_order.get("orderMap") or {}).items()
            if str(key)
        }
        fallback_order_map = infer_mission_dialog_order(
            mission,
            mission_entries,
            flow,
            mission_level_refs.get(mission),
        )
        order_map = dict(mission_runtime_order_map)
        fallback_base = (max(order_map.values()) + 1000) if order_map else 0
        for key, value in fallback_order_map.items():
            order_map.setdefault(key, fallback_base + value)
        node_entries = sorted(
            (entry for entry in mission_entries if entry.get("k") in available),
            key=lambda entry: (
                order_map.get(entry["k"], 10**9),
                entry.get("s", 10**9),
                entry.get("k") or "",
            ),
        )
        mission_entry_by_key = {
            entry["k"]: entry
            for entry in node_entries
            if entry.get("k")
        }
        edges_by_key: dict[tuple[str, str, str], dict] = {}
        def ensure_edge(src: str, dst: str, kind: str) -> dict | None:
            if not src or not dst or src == dst:
                return None
            if src not in all_nodes or dst not in all_nodes:
                return None
            edge = edges_by_key.get((src, dst, kind))
            if edge is None:
                edge = {"from": src, "to": dst, "kind": kind}
                edges_by_key[(src, dst, kind)] = edge
            return edge
        for source_edge in scene_file_order.get("edges") or []:
            edge = ensure_edge(
                source_edge.get("from") or "",
                source_edge.get("to") or "",
                source_edge.get("kind") or "questPrev",
            )
            if not edge:
                continue
            edge["source"] = source_edge.get("source") or scene_file_order.get("source")
            for quest_id in source_edge.get("questIds") or []:
                refs = edge.setdefault("questIds", [])
                if quest_id and quest_id not in refs:
                    refs.append(quest_id)
        if flow:
            quest_by_id = {
                quest.get("id") or "": quest
                for quest in flow.get("quests") or []
                if quest.get("id")
            }
            quest_scene_refs: dict[str, list[str]] = {}
            quest_scene_meta: dict[str, dict] = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })
            quest_leveldata_refs: dict[str, list[str]] = {}
            def gather_upstream_scene_refs(quest_id: str, seen: set[str] | None = None) -> list[str]:
                if not quest_id:
                    return []
                if seen is None:
                    seen = set()
                if quest_id in seen:
                    return []
                seen.add(quest_id)
                scene_refs = quest_scene_refs.get(quest_id, [])
                if scene_refs:
                    return scene_refs
                out: list[str] = []
                for prev_id in (quest_by_id.get(quest_id) or {}).get("prev") or []:
                    for scene_ref in gather_upstream_scene_refs(prev_id, seen):
                        if scene_ref not in out:
                            out.append(scene_ref)
                return out
            script_scene_ref_cache: dict[tuple[str, str], list[str]] = {}
            def normalized_script_ids(values) -> list[str]:
                out: list[str] = []
                for value in values or []:
                    script_id = value
                    if isinstance(value, dict):
                        script_id = value.get("scriptId") or value.get("value")
                        if isinstance(script_id, dict):
                            script_id = script_id.get("scriptId")
                    if script_id is None:
                        continue
                    script_id_text = str(script_id)
                    if script_id_text and script_id_text not in out:
                        out.append(script_id_text)
                return out
            def levelscript_scene_refs_for_script(level_id: str, script_id) -> list[str]:
                if not level_id or script_id is None:
                    return []
                script_stem = str(script_id)
                cache_key = (level_id, script_stem)
                if cache_key in script_scene_ref_cache:
                    return script_scene_ref_cache[cache_key]
                hits: list[tuple[int, int, str]] = []
                for file_info in _load_levelscript_binding_data(level_id).get("files") or []:
                    if Path(file_info.get("file") or "").stem != script_stem:
                        continue
                    for record in file_info.get("records") or []:
                        record_start = int(record.get("start") or 0)
                        for hit in record.get("strings") or []:
                            scene_ref = resolve_scene_ref_out_key(hit.get("text") or "", available)
                            if not scene_ref:
                                continue
                            hits.append((
                                record_start,
                                int(hit.get("offset") or record_start),
                                scene_ref,
                            ))
                refs = _unique_preserve([scene_ref for _, __, scene_ref in sorted(hits)])
                script_scene_ref_cache[cache_key] = refs
                return refs
            def quest_condition_script_scene_refs(quest: dict) -> list[str]:
                refs: list[str] = []
                default_scene_ids = list(quest.get("scenes") or [])
                for anchor in quest.get("objectiveAnchors") or []:
                    anchor_scene_ids = list(anchor.get("sceneIds") or default_scene_ids)
                    for script_id in normalized_script_ids(anchor.get("scriptIds")):
                        for scene_id in anchor_scene_ids:
                            for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                                if scene_ref not in refs:
                                    refs.append(scene_ref)
                    for leaf in anchor.get("conditionLeaves") or []:
                        leaf_scene_ids = list(leaf.get("sceneIds") or anchor_scene_ids)
                        for script_id in normalized_script_ids(leaf.get("scriptIds")):
                            for scene_id in leaf_scene_ids:
                                for scene_ref in levelscript_scene_refs_for_script(scene_id, script_id):
                                    if scene_ref not in refs:
                                        refs.append(scene_ref)
                return refs
            def quest_field_scene_refs(quest: dict, field_name: str) -> list[str]:
                refs: list[str] = []
                for raw_ref in quest.get(field_name) or []:
                    resolved = resolve_scene_ref_out_key(raw_ref, available)
                    if resolved and resolved not in refs:
                        refs.append(resolved)
                return refs
            def add_leveldata_edge_meta(edge: dict, quest: dict, scene_refs: list[str]) -> None:
                quest_id = quest.get("id") or ""
                refs = edge.setdefault("questIds", [])
                if quest_id and quest_id not in refs:
                    refs.append(quest_id)
                scene_ref_set = set(scene_refs)
                for row in quest.get("levelDataStoryRefs") or []:
                    if not isinstance(row, dict):
                        continue
                    resolved = resolve_scene_ref_out_key(row.get("storyRef") or "", available)
                    if scene_ref_set and resolved not in scene_ref_set:
                        continue
                    file_ref = row.get("file") or ""
                    if file_ref:
                        source_files = edge.setdefault("sourceFiles", [])
                        if file_ref not in source_files:
                            source_files.append(file_ref)
                    level_id = row.get("levelId") or ""
                    if level_id:
                        level_ids = edge.setdefault("levelIds", [])
                        if level_id not in level_ids:
                            level_ids.append(level_id)
                    entity = row.get("entity") or ""
                    if entity:
                        entities = edge.setdefault("entities", [])
                        if entity not in entities:
                            entities.append(entity)
                    for field in row.get("fields") or []:
                        fields = edge.setdefault("fields", [])
                        if field and field not in fields:
                            fields.append(field)
            for quest in flow.get("quests") or []:
                proxy_dialog_refs: list[str] = []
                for proxy_ref in quest.get("proxyDialogs") or []:
                    raw_ref = (
                        proxy_ref.get("dialogId")
                        if isinstance(proxy_ref, dict)
                        else proxy_ref
                    )
                    resolved = resolve_scene_ref_out_key(raw_ref or "", available)
                    if resolved and resolved not in proxy_dialog_refs:
                        proxy_dialog_refs.append(resolved)
                scene_refs = _unique_preserve([
                    *quest_condition_script_scene_refs(quest),
                    *quest_field_scene_refs(quest, "dialogs"),
                    *proxy_dialog_refs,
                    *quest_field_scene_refs(quest, "cutscenes"),
                    *quest_field_scene_refs(quest, "remotecomms"),
                    *quest_field_scene_refs(quest, "radios"),
                    *quest_area_scene_refs(quest, available),
                ])
                quest_id = quest.get("id") or ""
                flow_index = quest.get("flowIndex", 0)
                leveldata_scene_refs = quest_leveldata_scene_refs(quest, available)
                if leveldata_scene_refs:
                    quest_leveldata_refs[quest_id] = leveldata_scene_refs
                if scene_refs:
                    quest_scene_refs[quest_id] = scene_refs
                    first_scene = scene_refs[0]
                    meta = quest_scene_meta[first_scene]
                    if quest_id and quest_id not in meta["questIds"]:
                        meta["questIds"].append(quest_id)
                    if isinstance(flow_index, int | float) and flow_index not in meta["flowIndices"]:
                        meta["flowIndices"].append(int(flow_index))
                    if quest_id and not (quest.get("prev") or []) and quest_id not in meta["rootQuestIds"]:
                        meta["rootQuestIds"].append(quest_id)
                for src, dst in zip(scene_refs, scene_refs[1:]):
                        if edge := ensure_edge(src, dst, "questSequence"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
                if leveldata_scene_refs:
                    sources = scene_refs[:]
                    if not sources:
                        for prev_id in quest.get("prev") or []:
                            for scene_ref in gather_upstream_scene_refs(prev_id):
                                if scene_ref not in sources:
                                    sources.append(scene_ref)
                    if sources:
                        src = _unique_preserve(sources)[-1]
                        if edge := ensure_edge(src, leveldata_scene_refs[0], "levelDataQuestRef"):
                            add_leveldata_edge_meta(edge, quest, leveldata_scene_refs[:1])
                    for src, dst in zip(leveldata_scene_refs, leveldata_scene_refs[1:]):
                        if edge := ensure_edge(src, dst, "levelDataQuestRef"):
                            add_leveldata_edge_meta(edge, quest, [src, dst])
                jump_nodes = [
                    f"ui:{hint.get('jumpId')}"
                    for hint in (quest.get("tracking") or [])
                    if hint.get("jumpId")
                ]
                sources = scene_refs[:]
                if not sources:
                    for prev_id in quest.get("prev") or []:
                        for scene_ref in gather_upstream_scene_refs(prev_id):
                            if scene_ref not in sources:
                                sources.append(scene_ref)
                    for jump_node in jump_nodes:
                        for src in _unique_preserve(sources):
                            if edge := ensure_edge(src, jump_node, "uiJump"):
                                refs = edge.setdefault("questIds", [])
                                if quest_id and quest_id not in refs:
                                    refs.append(quest_id)
            children_by_prev: dict[str, list[str]] = defaultdict(list)
            for quest in flow.get("quests") or []:
                child_id = quest.get("id") or ""
                for prev_id in quest.get("prev") or []:
                    if prev_id and child_id:
                        children_by_prev[prev_id].append(child_id)
            for quest in flow.get("quests") or []:
                quest_id = quest.get("id") or ""
                leveldata_scene_refs = quest_leveldata_refs.get(quest_id) or []
                if not leveldata_scene_refs:
                    continue
                for child_id in children_by_prev.get(quest_id) or []:
                    child_targets = (
                        quest_scene_refs.get(child_id)
                        or quest_leveldata_refs.get(child_id)
                        or []
                    )
                    if not child_targets:
                        continue
                    if edge := ensure_edge(
                        leveldata_scene_refs[-1],
                        child_targets[0],
                        "levelDataQuestRef",
                    ):
                        add_leveldata_edge_meta(edge, quest, leveldata_scene_refs[-1:])
            for quest in flow.get("quests") or []:
                quest_id = quest.get("id") or ""
                scene_refs = quest_scene_refs.get(quest_id, [])
                if not scene_refs:
                    continue
                first_scene = scene_refs[0]
                for prev_id in quest.get("prev") or []:
                    for prev_scene in gather_upstream_scene_refs(prev_id):
                        if edge := ensure_edge(prev_scene, first_scene, "questPrev"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
                            if prev_id and prev_id not in refs:
                                refs.append(prev_id)
                fail_scene_refs = _unique_preserve([
                    resolved
                    for raw_ref in (quest.get("failStoryRefs") or [])
                    if (resolved := resolve_scene_ref_out_key(raw_ref, available))
                ])
                guard_sources = scene_refs[-1:] or _unique_preserve([
                    upstream
                    for prev_id in quest.get("prev") or []
                    for upstream in gather_upstream_scene_refs(prev_id)
                ])
                for guard_src in guard_sources:
                    for fail_scene in fail_scene_refs:
                        if edge := ensure_edge(guard_src, fail_scene, "questFailGuard"):
                            refs = edge.setdefault("questIds", [])
                            if quest_id and quest_id not in refs:
                                refs.append(quest_id)
        else:
            quest_scene_meta = defaultdict(lambda: {
                "questIds": [],
                "rootQuestIds": [],
                "flowIndices": [],
            })
        for scene_key, links in scene_graph_links_by_key.items():
            if scene_key not in available:
                continue
            for link in links:
                source_key = link.get("sourceKey") or ""
                for opt in link.get("options") or []:
                    option_id = opt.get("optionId") or ""
                    if first_scene := opt.get("firstSceneKey"):
                        if first_scene != scene_key:
                            if edge := ensure_edge(scene_key, first_scene, "authoredDirect"):
                                if option_id:
                                    edge.setdefault("optionIds", [])
                                    if option_id not in edge["optionIds"]:
                                        edge["optionIds"].append(option_id)
                                if source_key:
                                    edge.setdefault("sourceKeys", [])
                                    if source_key not in edge["sourceKeys"]:
                                        edge["sourceKeys"].append(source_key)
                    for submenu_scene in opt.get("submenuSceneKeys") or []:
                        if submenu_scene == scene_key or submenu_scene == opt.get("firstSceneKey"):
                            continue
                        if edge := ensure_edge(scene_key, submenu_scene, "authoredMenu"):
                            if option_id:
                                edge.setdefault("optionIds", [])
                                if option_id not in edge["optionIds"]:
                                    edge["optionIds"].append(option_id)
                            if source_key:
                                edge.setdefault("sourceKeys", [])
                                if source_key not in edge["sourceKeys"]:
                                    edge["sourceKeys"].append(source_key)
        for chain in chain_sequences:
            sequence = chain.get("sequence") or []
            for src, dst in zip(sequence, sequence[1:]):
                if edge := ensure_edge(src, dst, "levelscriptChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)
        chain_start_meta: dict[str, dict] = defaultdict(lambda: {
            "sourceFiles": [],
            "levelIds": [],
            "positions": [],
        })
        for chain in scene_chain_sequences:
            sequence = chain.get("sequence") or []
            if sequence:
                first_scene = sequence[0]
                meta = chain_start_meta[first_scene]
                file_ref = chain.get("file") or ""
                if file_ref and file_ref not in meta["sourceFiles"]:
                    meta["sourceFiles"].append(file_ref)
                level_id = chain.get("levelId") or ""
                if level_id and level_id not in meta["levelIds"]:
                    meta["levelIds"].append(level_id)
                meta["positions"].append(0)
            for pos, (src, dst) in enumerate(zip(sequence, sequence[1:])):
                if edge := ensure_edge(src, dst, "levelscriptSceneChain"):
                    file_ref = chain.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    level_id = chain.get("levelId") or ""
                    if level_id:
                        refs = edge.setdefault("levelIds", [])
                        if level_id not in refs:
                            refs.append(level_id)
                    edge.setdefault("positions", [])
                    if pos not in edge["positions"]:
                        edge["positions"].append(pos)
        # Levelscript file-order edges (weak ordering hints).
        # File-order tokens within a single SerializeReference dump usually
        # track authored event flow even when the records aren't UID-linked,
        # so we mine every level the mission actually touches 鈥?including
        # levels that share a LevelData host file with another mission
        # (mission_level_refs misses these because it keys off filename).
        flow_level_ids: list[str] = []
        if re.match(r"^map\d+_lv\d+$", mission or "", re.I):
            flow_level_ids.append(mission)
        for candidate in [(flow or {}).get("level")] + [
            scene_id
            for quest in ((flow or {}).get("quests") or [])
            for scene_id in (quest.get("scenes") or [])
        ] + [ref.get("levelId") for ref in (mission_level_refs.get(mission) or [])] + [
            ref.get("levelId") for ref in (mission_leveldata_host_refs.get(mission) or [])
        ]:
            if candidate and candidate not in flow_level_ids:
                flow_level_ids.append(candidate)
        for level_id in flow_level_ids:
            for pair in _build_levelscript_dialog_exit_scene_pairs(
                level_id, dialog_scene_out_key, mission
            ):
                src = pair.get("src") or ""
                dst = pair.get("dst") or ""
                if src not in available or dst not in available:
                    continue
                if edge := ensure_edge(src, dst, "levelscriptDialogExit"):
                    file_ref = pair.get("file") or ""
                    if file_ref:
                        refs = edge.setdefault("sourceFiles", [])
                        if file_ref not in refs:
                            refs.append(file_ref)
                    pair_level_id = pair.get("levelId") or ""
                    if pair_level_id:
                        refs = edge.setdefault("levelIds", [])
                        if pair_level_id not in refs:
                            refs.append(pair_level_id)
                    edge["event"] = pair.get("event") or "LevelEvent_OnDialogExit"
                    edge["sourceScript"] = pair.get("sourceScript") or ""
                    edge["headerLocalId"] = pair.get("headerLocalId")
                    edge["targetLocalId"] = pair.get("targetLocalId")
                    position = pair.get("position")
                    if isinstance(position, int):
                        positions = edge.setdefault("positions", [])
                        if position not in positions:
                            positions.append(position)
            for file_seq in _build_levelscript_file_order_scene_sequences(
                level_id, dialog_scene_out_key, mission
            ):
                filtered = [k for k in file_seq["sequence"] if k in available]
                if len(filtered) < 2:
                    continue
                for pos, (src, dst) in enumerate(zip(filtered, filtered[1:])):
                    if edge := ensure_edge(src, dst, "levelscriptFileOrder"):
                        file_ref = file_seq.get("file") or ""
                        if file_ref:
                            refs = edge.setdefault("sourceFiles", [])
                            if file_ref not in refs:
                                refs.append(file_ref)
                        seq_level_id = file_seq.get("levelId") or ""
                        if seq_level_id:
                            refs = edge.setdefault("levelIds", [])
                            if seq_level_id not in refs:
                                refs.append(seq_level_id)
                        edge.setdefault("positions", [])
                        if pos not in edge["positions"]:
                            edge["positions"].append(pos)
            for pair in _build_levelscript_cross_file_scene_pairs(
                level_id, dialog_scene_out_key, mission
            ):
                src = pair.get("src") or ""
                dst = pair.get("dst") or ""
                if src not in available or dst not in available:
                    continue
                if edge := ensure_edge(src, dst, "levelscriptCrossFileOrder"):
                    for key in ("fromFile", "toFile"):
                        file_ref = pair.get(key) or ""
                        if file_ref:
                            refs = edge.setdefault("sourceFiles", [])
                            if file_ref not in refs:
                                refs.append(file_ref)
                    pair_level_id = pair.get("levelId") or ""
                    if pair_level_id:
                        refs = edge.setdefault("levelIds", [])
                        if pair_level_id not in refs:
                            refs.append(pair_level_id)
                    stems = edge.setdefault("fileStems", [])
                    stem_pair = [pair.get("fromStem"), pair.get("toStem")]
                    if stem_pair not in stems:
                        stems.append(stem_pair)
        # PRTS collection rows expose authored page order inside a single
        # reading/collection item. Treat that as weak ordering only, and only
        # when each ordered slot maps to exactly one story node.
        prts_buckets: dict[str, dict[int, list[tuple[str, str]]]] = defaultdict(lambda: defaultdict(list))
        for row_id, row in prts_all_items.items():
            if not isinstance(row, dict):
                continue
            first_lv_id = str(row.get("firstLvId") or "")
            order = row.get("order")
            content_id = str(row.get("contentId") or "")
            if not first_lv_id or not isinstance(order, int) or not content_id.startswith("text_"):
                continue
            suffix = content_id[len("text_"):]
            candidates = [
                key
                for key in (
                    f"dlg_{suffix}",
                    f"black_{suffix}",
                    f"misc_dlg_{suffix}",
                )
                if key in available
            ]
            if len(candidates) != 1:
                continue
            prts_buckets[first_lv_id][order].append((candidates[0], str(row_id)))
        for first_lv_id, order_map_by_bucket in prts_buckets.items():
            ordered_slots = [
                (order, rows[0])
                for order, rows in sorted(order_map_by_bucket.items())
                if len(rows) == 1
            ]
            if len(ordered_slots) < 2:
                continue
            for pos, ((_, (src, src_row)), (__, (dst, dst_row))) in enumerate(zip(ordered_slots, ordered_slots[1:])):
                if edge := ensure_edge(src, dst, "prtsCollectionOrder"):
                    edge["firstLvId"] = first_lv_id
                    refs = edge.setdefault("prtsRows", [])
                    for row_ref in (src_row, dst_row):
                        if row_ref and row_ref not in refs:
                            refs.append(row_ref)
                    edge.setdefault("positions", [])
                    if pos not in edge["positions"]:
                        edge["positions"].append(pos)
        # Radio-continuation edges (authored continueAfterDialog/Radio flags
        # combined with LevelScript file-offset adjacency, audited offline by
        # scripts/story_recovery/build_radio_continuation_audit.py). Silent
        # no-op when the audit report has not been generated yet.
        radio_cont_candidates = _load_radio_continuation_candidates_by_mission(
            str(_RADIO_CONTINUATION_REPORT_PATH)
        ).get(mission) or []
        for cand in radio_cont_candidates:
            predecessor = cand.get("predecessor") or ""
            radio = cand.get("radio") or ""
            if not predecessor or not radio:
                continue
            if predecessor not in available or radio not in available:
                continue
            if predecessor == radio:
                continue
            edge = ensure_edge(predecessor, radio, "radioContinuation")
            if not edge:
                continue
            file_ref = cand.get("file") or ""
            if file_ref:
                refs = edge.setdefault("sourceFiles", [])
                if file_ref not in refs:
                    refs.append(file_ref)
            level_id = cand.get("levelId") or ""
            if level_id:
                refs = edge.setdefault("levelIds", [])
                if level_id not in refs:
                    refs.append(level_id)
            match = cand.get("match") or ""
            if match:
                kinds = edge.setdefault("continuationKinds", [])
                if match not in kinds:
                    kinds.append(match)
        graph_order_map = _refine_scene_graph_order(
            all_nodes,
            list(edges_by_key.values()),
            order_map,
            available,
        )
        chained_node_keys: set[str] = {
            k
            for edge in edges_by_key.values()
            for k in (edge.get("from") or "", edge.get("to") or "")
            if k
        }
        mission_runtime_ordered_keys = set(mission_runtime_order_map)
        strong_order_edge_kinds = {
            "questSequence",
            "questPrev",
            "questFailGuard",
            "authoredDirect",
            "authoredMenu",
            "levelscriptSceneChain",
            "levelscriptDialogExit",
            # Authored continueAfterDialog/Radio flag combined with a
            # LevelScript file-offset adjacency is stronger than file-order
            # alone because the flag asserts the radio is meant to follow the
            # preceding dialog/radio.
            "radioContinuation",
        }
        weak_order_edge_kinds = {
            "levelscriptFileOrder",
            "levelscriptCrossFileOrder",
            "levelDataQuestRef",
            "prtsCollectionOrder",
        }
        strong_ordered_keys = set(mission_runtime_ordered_keys)
        weak_ordered_keys: set[str] = set()
        for edge in edges_by_key.values():
            kind = edge.get("kind") or ""
            if kind in strong_order_edge_kinds:
                target = strong_ordered_keys
            elif kind in weak_order_edge_kinds:
                target = weak_ordered_keys
            else:
                continue
            for node_key in (edge.get("from") or "", edge.get("to") or ""):
                if node_key:
                    target.add(node_key)
        def order_strength(node_key: str) -> str:
            if node_key in strong_ordered_keys:
                return "strong"
            if node_key in weak_ordered_keys:
                return "weak"
            return "unknown"
        nodes = [
            {
                "key": node_key,
                "kind": (
                    (mission_entry_by_key.get(node_key) or {}).get("d")
                    or _scene_graph_node_kind(node_key, available)
                ),
                "order": graph_order_map.get(node_key, -1),
                **(
                    {"orderSource": "MissionRuntimeAsset.questDic[*].prevQuestIdList"}
                    if node_key in mission_runtime_ordered_keys
                    else {}
                ),
                "orderStrength": order_strength(node_key),
                **(
                    {"orderConfirmed": False}
                    if node_key not in chained_node_keys and node_key not in mission_runtime_ordered_keys
                    else {}
                ),
            }
            for node_key in sorted(
                all_nodes,
                key=lambda key: (
                    graph_order_map.get(key, 10**9),
                    order_map.get(key, 10**9),
                    _scene_graph_node_kind(key, available),
                    key,
                ),
            )
        ]
        edges = sorted(
            edges_by_key.values(),
            key=lambda edge: (
                graph_order_map.get(edge["from"], 10**9),
                graph_order_map.get(edge["to"], 10**9),
                edge.get("kind") or "",
                edge["from"],
                edge["to"],
            ),
        )
        scene_entry = _detect_scene_graph_entries(
            nodes,
            edges,
            dict(quest_scene_meta),
            dict(chain_start_meta),
            order_map,
            graph_order_map,
            available,
        )
        payload = {"nodes": nodes, "edges": edges}
        if scene_entry:
            payload.update(scene_entry)
        if story_call_contexts:
            payload["levelscriptStoryCallContexts"] = story_call_contexts
        if hash_terminal_contexts:
            payload["levelscriptHashTerminals"] = hash_terminal_contexts
        if call_server_callback_contexts:
            payload["levelscriptCallServerCallbacks"] = call_server_callback_contexts
        if scene_file_order:
            payload["sceneFileOrder"] = {
                key: value
                for key, value in scene_file_order.items()
                if key != "orderMap"
            }
        return payload

    mission_flows_payload: dict[str, dict] = {}
    mission_scene_graphs: dict[str, dict] = {}
    for mission in mission_flow_missions:
        flow = load_mission_flow(mission)
        localized_flow = localize_mission_flow(flow)
        graph_flow = mission_graph_flow(mission, flow)
        scene_graph = build_mission_scene_graph(mission, graph_flow)
        if not localized_flow and not scene_graph:
            continue
        payload = {"quests": (localized_flow or {}).get("quests") or []}
        if (localized_flow or {}).get("missionDescription"):
            payload["missionDescription"] = localized_flow["missionDescription"]
        if localized_flow:
            available = scene_keys_by_mission.get(mission, set())
            mission_story_connections = quest_attached_story_connections(
                {
                    "storyConnections": localized_flow.get("missionStoryConnections") or [],
                },
                all_story_entry_keys,
            )
            if mission_story_connections:
                payload["missionStoryConnections"] = mission_story_connections
            referenced: set[str] = set()
            for q in localized_flow["quests"]:
                # A MissionRuntime can author a direct reference to a Story file
                # owned by another mission (ambient/map dialog is the common
                # case), so normalize direct refs against the language corpus.
                runtime_actions = quest_attached_dialog_tree_runtime_actions(
                    q,
                    all_available_scene_keys,
                    dialog_tree_open_ui_actions_by_key,
                )
                if runtime_actions:
                    q["runtimeActions"] = runtime_actions
                else:
                    q.pop("runtimeActions", None)
                story_connections = quest_attached_story_connections(q, all_available_scene_keys)
                if story_connections:
                    q["storyConnections"] = story_connections
                else:
                    q.pop("storyConnections", None)
                story_files = quest_attached_story_files(q, all_available_scene_keys, story_connections)
                if story_files:
                    q["storyFiles"] = story_files
                else:
                    q.pop("storyFiles", None)
                referenced.update(
                    row.get("key")
                    for row in story_connections
                    if row.get("key") in available
                )
                referenced.update(quest_area_scene_refs(q, available))
                referenced.update(quest_leveldata_scene_refs(q, available))
            unlinked = sorted(available - referenced)
            if localized_flow.get("level"):
                payload["level"] = localized_flow["level"]
            if unlinked:
                payload["unlinked"] = unlinked
            map_pins = build_mission_map_pins(localized_flow)
            if map_pins:
                payload["mapPins"] = map_pins
            scene_pins = build_mission_scene_pins(localized_flow, available)
            if scene_pins:
                payload["scenePins"] = scene_pins
        if scene_graph:
            payload["sceneGraph"] = scene_graph
            if graph_flow and graph_flow.get("variantMissionIds"):
                payload["sceneGraphVariantMissions"] = graph_flow["variantMissionIds"]
            mission_scene_graphs[mission] = scene_graph
        mission_flows_payload[mission] = payload

    # NpcProxyEx rows with an explicit MissionRuntime id establish mission
    # context even when no quest tracks that NPC. Keep this on the mission
    # shell; the stricter exact-(mission, proxy)-to-one-quest join is emitted
    # separately by mission_flow.py.
    npc_proxy_ex_rows = npc_proxy_ex.get("data") or {}
    if isinstance(npc_proxy_ex_rows, dict):
        for proxy_id, proxy_rows in npc_proxy_ex_rows.items():
            for proxy_row in proxy_rows or []:
                if not isinstance(proxy_row, dict):
                    continue
                target_mission = str(proxy_row.get("missionId") or "")
                flow_payload = mission_flows_payload.get(target_mission)
                if not target_mission or flow_payload is None:
                    continue
                story_key = resolve_scene_ref_out_key(
                    str(proxy_row.get("dialogId") or ""),
                    all_story_entry_keys,
                )
                if not story_key:
                    continue
                connection = {
                    "key": story_key,
                    "kind": story_kind_by_key.get(story_key, "dialog"),
                    "relation": "npc_proxy_ex_mission_context",
                    "direction": "context",
                    "phase": "context",
                    "confidence": "direct_mission_scope",
                    "source": "NpcProxyExDataTable.data[*].missionId + dialogId",
                    "npcProxyId": str(proxy_id or ""),
                    "npcProxyMissionId": target_mission,
                    "questTriggerStatus": (
                        "mission_scoped_proxy_dialog_configuration_not_"
                        "mission_or_quest_activation"
                    ),
                    "selectionOrderStatus": (
                        "one_based_active_row_selection_only_no_cross_row_"
                        "chronology"
                    ),
                    "executionSide": "client",
                    "networkRole": (
                        "server_selected_proxy_state_then_local_interaction_"
                        "dialog"
                    ),
                    "serverExchange": True,
                    "clientRequest": False,
                    "expectedClientReply": False,
                    "upstreamServerStateSources": [
                        "SC_NPC_ENTER_MAP_RESYNC",
                        "SC_NPC_ACTIVE_CHANGE_NTF",
                    ],
                    "serverFields": [
                        "proxyNumId",
                        "metaKvs",
                        "activeCondIndex",
                    ],
                    "serverEvidenceStatus": (
                        "the server supplies proxy state and a one-based "
                        "activeCondIndex, not mission, quest, dialog, or "
                        "relative Story order"
                    ),
                    "nativeConsumers": [{
                        "method": (
                            "NpcInteractComponent."
                            "_TryGetNpcProxyInteractDialogId"
                        ),
                        "token": "0x06011381",
                        "address": "0x183564080",
                    }, {
                        "method": "NpcProxy._IsMissionConflict",
                        "token": "0x060131f4",
                        "address": "0x18706ac74",
                    }],
                    "nativeMappingId": (
                        "npc-proxy-dialog-selection-native-v1"
                    ),
                    "gameAssemblySha256": (
                        "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2"
                        "B983FB9D45677D80FFCE"
                    ),
                }
                story_owner = story_owner_by_key.get(story_key) or ""
                if story_owner:
                    connection["storyOwnerMission"] = story_owner
                connections = flow_payload.setdefault("missionStoryConnections", [])
                signature = (
                    story_key,
                    connection["relation"],
                    connection["npcProxyId"],
                    target_mission,
                )
                if any((
                    str(existing.get("key") or ""),
                    str(existing.get("relation") or ""),
                    str(existing.get("npcProxyId") or ""),
                    str(existing.get("npcProxyMissionId") or ""),
                ) == signature for existing in connections if isinstance(existing, dict)):
                    continue
                connections.append(connection)

    # FocusModeInstanceTable authors an explicit mission id beside the radio
    # played when focus-mode interaction is locked. This is direct mission
    # scope, but not a quest transition or a generic radio-play action.
    focus_mode_payload = load_json_path(
        FOCUS_MODE_INSTANCE_TABLE_PATH,
        "FocusModeInstanceTable.json",
    ) if FOCUS_MODE_INSTANCE_TABLE_PATH.is_file() else {}
    focus_mode_rows = focus_mode_payload.get("dataTable") or {}
    if isinstance(focus_mode_rows, dict):
        for row_id, focus_row in focus_mode_rows.items():
            if not isinstance(focus_row, dict):
                continue
            target_mission = str(focus_row.get("missionId") or "").strip()
            flow_payload = mission_flows_payload.get(target_mission)
            if not target_mission or flow_payload is None:
                continue
            story_key = resolve_scene_ref_out_key(
                str(focus_row.get("radioIdInteractLocked") or ""),
                all_story_entry_keys,
            )
            if not story_key:
                continue
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "radio"),
                "relation": "focus_mode_interact_locked_radio",
                "direction": "context",
                "phase": "interact_locked",
                "confidence": "direct_mission_scope",
                "source": (
                    "FocusModeInstanceTable.dataTable[*].missionId + "
                    "radioIdInteractLocked"
                ),
                "focusModeId": str(focus_row.get("id") or row_id or ""),
                "focusModeMissionId": target_mission,
                "focusModeField": "radioIdInteractLocked",
                "subDataParentId": focus_row.get("subDataParentId"),
            }
            story_owner = story_owner_by_key.get(story_key) or ""
            if story_owner:
                connection["storyOwnerMission"] = story_owner
            connections = flow_payload.setdefault("missionStoryConnections", [])
            signature = (
                story_key,
                connection["relation"],
                connection["focusModeId"],
                target_mission,
            )
            if any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("focusModeId") or ""),
                str(existing.get("focusModeMissionId") or ""),
            ) == signature for existing in connections if isinstance(existing, dict)):
                continue
            connections.append(connection)

    # SNSDialogTable can author the mission relationship three times in one
    # row: the root relatedMissionId, a type-12 content node linkMissionId,
    # and the same mission id in contentParam. Require all three original-data
    # fields to agree before attaching the SNS conversation to a mission shell.
    # This is an authored navigation/context link, not a server-return edge.
    if isinstance(sns, dict):
        for sns_row_id, sns_row in sns.items():
            if not isinstance(sns_row, dict):
                continue
            target_mission = str(sns_row.get("relatedMissionId") or "").strip()
            flow_payload = mission_flows_payload.get(target_mission)
            if not target_mission or flow_payload is None:
                continue
            story_key = resolve_scene_ref_out_key(
                str(sns_row.get("dialogId") or sns_row_id or ""),
                all_story_entry_keys,
            )
            if not story_key:
                continue
            linked_content_ids: list[str] = []
            content_rows = sns_row.get("dialogContentData") or {}
            if not isinstance(content_rows, dict):
                continue
            for content_row_id, content_row in content_rows.items():
                if not isinstance(content_row, dict):
                    continue
                try:
                    content_type = int(content_row.get("contentType"))
                except (TypeError, ValueError):
                    continue
                link_mission = str(content_row.get("linkMissionId") or "").strip()
                content_params = {
                    str(value or "").strip()
                    for value in content_row.get("contentParam") or []
                    if str(value or "").strip()
                }
                if (
                    content_type == 12
                    and link_mission == target_mission
                    and target_mission in content_params
                ):
                    linked_content_ids.append(str(
                        content_row.get("contentId")
                        if content_row.get("contentId") is not None
                        else content_row_id
                    ))
            if not linked_content_ids:
                continue
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "sns"),
                "relation": "sns_authored_mission_link",
                "direction": "context",
                "phase": "mission_link",
                "confidence": "authored_direct",
                "source": (
                    "SNSDialogTable.relatedMissionId + "
                    "dialogContentData[*].linkMissionId + contentParam"
                ),
                "snsDialogId": str(sns_row.get("dialogId") or sns_row_id or ""),
                "snsMissionId": target_mission,
                "snsContentIds": sorted(set(linked_content_ids)),
                "snsContentType": 12,
            }
            story_owner = story_owner_by_key.get(story_key) or ""
            if story_owner:
                connection["storyOwnerMission"] = story_owner
            connections = flow_payload.setdefault("missionStoryConnections", [])
            signature = (
                story_key,
                connection["relation"],
                target_mission,
                tuple(connection["snsContentIds"]),
            )
            if any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("snsMissionId") or ""),
                tuple(str(value) for value in existing.get("snsContentIds") or []),
            ) == signature for existing in connections if isinstance(existing, dict)):
                continue
            connections.append(connection)

    # Recovered Unity Timeline assets can embed black-screen text playables
    # inside a dialog Actor root.  Collect the exact containment edges here;
    # mission scope is added later only when original LevelData uniquely hosts
    # the typed LevelScript action that starts the parent dialog.
    unresolved_black_timeline_attachments: dict[str, list[dict]] = defaultdict(list)
    black_timeline_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for attachment in recover_black_timeline_attachments():
        if not isinstance(attachment, dict):
            continue
        black_key = str(attachment.get("key") or "")
        dialog_key = str(attachment.get("dialogKey") or "")
        if black_key not in all_story_entry_keys:
            continue
        if not dialog_key:
            unresolved_black_timeline_attachments[black_key].append(attachment)
            continue
        black_timeline_groups[(black_key, dialog_key)].append(attachment)

    # Native NarrativeBlackScreen actions serialize exact TextTable line ids,
    # not a conversation key. Resolve those ids through the already emitted
    # black conversations and require every id in an action to name the same
    # Story file. Native Execute calls GameAction.ShowNarrativeBlackScreen, so
    # this is client presentation/playback evidence; without a separate quest
    # event it belongs on the mission shell and is never a server exchange.
    black_line_story_keys: dict[str, set[str]] = defaultdict(set)
    for black_key, bucket in black_groups.items():
        for _order, text_id, _text_entry in bucket.get("items") or []:
            if text_id:
                black_line_story_keys[str(text_id)].add(str(black_key))
    unique_black_line_owner = {
        text_id: next(iter(story_keys))
        for text_id, story_keys in black_line_story_keys.items()
        if len(story_keys) == 1
    }
    # DialogTree TextAssets serialize narrative-mask actions as ParadoxNotion
    # typed JSON.  Resolve only exact LangKey ids from the two concrete action
    # classes proved by the current native binary; literal/custom text is never
    # used as a filename or content-based join.
    dialog_tree_narrative_groups: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for occurrence in recover_dialog_tree_narrative_mask_actions():
        if not isinstance(occurrence, dict):
            continue
        text_id = str(occurrence.get("textId") or "")
        black_key = unique_black_line_owner.get(text_id) or ""
        dialog_key = str(occurrence.get("dialogKey") or "")
        if not black_key or black_key not in all_story_entry_keys or not dialog_key:
            continue
        dialog_tree_narrative_groups[(black_key, dialog_key)].append(occurrence)
    # DialogLeftSubtitleActionData uses four fixed LangKey slots and is
    # rendered by the local dialog UI. Feed its exact containment through the
    # same frozen parent-scope/veto machinery, while retaining a distinct
    # relation so it cannot be mistaken for black-screen or audio playback.
    for occurrence in recover_dialog_tree_left_subtitle_actions():
        if not isinstance(occurrence, dict):
            continue
        text_id = str(occurrence.get("textId") or "")
        black_key = unique_black_line_owner.get(text_id) or ""
        dialog_key = str(occurrence.get("dialogKey") or "")
        if not black_key or black_key not in all_story_entry_keys or not dialog_key:
            continue
        dialog_tree_narrative_groups[(black_key, dialog_key)].append(occurrence)
    # A registered DialogTree can directly play a trunk line or next dialog
    # belonging to a different emitted Story file. These are exact
    # current-binary playback carriers anchored by directed ancestry to the
    # current dialog's trunk, not filename-prefix or weak-component inference.
    # Mission/quest scope is resolved later from a frozen parent-evidence index
    # so a newly attached child can never become a transitive parent.
    dialog_tree_story_playback_groups: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)
    for occurrence in recover_dialog_tree_story_playback_carriers(
        dialog_id_registry,
        all_story_entry_keys,
    ):
        if not isinstance(occurrence, dict):
            continue
        story_key = str(occurrence.get("storyKey") or "")
        dialog_key = str(occurrence.get("dialogKey") or "")
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or not dialog_key
            or story_key == dialog_key
        ):
            continue
        dialog_tree_story_playback_groups[(story_key, dialog_key)].append(occurrence)
    raw_mission_flows_for_dialog_tree = {
        mission_id: load_mission_flow(mission_id)
        for mission_id in mission_flows_payload
    }
    dialog_tree_completion_parent_quests = (
        collect_dialog_tree_completion_parent_quests(
            raw_mission_flows_for_dialog_tree,
            set(dialog_id_registry),
        )
    )
    dialog_tree_prime_story_playback_groups: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)
    prime_occurrences = (
        recover_dialog_tree_prime_reachable_story_playback_carriers(
            dialog_id_registry,
            all_story_entry_keys,
            {str(text_id) for text_id in dialogs},
            set(dialog_tree_completion_parent_quests),
        )
        if dialog_tree_completion_parent_quests
        else []
    )
    for occurrence in prime_occurrences:
        if not isinstance(occurrence, dict):
            continue
        story_key = str(occurrence.get("storyKey") or "")
        dialog_key = str(occurrence.get("dialogKey") or "")
        pair = (story_key, dialog_key)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or not dialog_key
            or story_key == dialog_key
            or pair in dialog_tree_story_playback_groups
        ):
            continue
        dialog_tree_prime_story_playback_groups[pair].append(occurrence)
    native_black_action_index = build_levelscript_native_black_action_index(
        unique_black_line_owner
    )
    suppressed_native_fmv_pairs = {
        (str(target_key), str(stem).lower())
        for target_key, rules in narrative_video_suppress_overrides.items()
        for rule in rules
        for stem in rule.get("stems") or []
    }
    native_story_playback_index = filter_native_story_playback_index(
        build_levelscript_native_story_playback_index(),
        all_story_entry_keys,
        suppressed_native_fmv_pairs,
    )
    native_non_fmv_story_playback_index = filter_non_fmv_story_playback_index(
        native_story_playback_index
    )
    battle_signal_producer_index = build_battle_signal_producer_index()
    mission_timeline_recovery_payload = build_mission_timeline_recovery_report(
        mission_scene_graphs,
        mission_flows=mission_flows_payload,
    )
    mission_timelines_by_mission = {
        mission.get("mission") or "": mission
        for mission in mission_timeline_recovery_payload.get("missions") or []
        if mission.get("mission")
    }

    recovered_attachment_types = {
        "scriptCondition": (
            "levelscript_condition_scope",
            "scoped_script",
            "LevelScript referenced by this quest condition",
        ),
        "variantMissionRuntime": (
            "variant_runtime_attachment",
            "scoped_variant",
            "variant MissionRuntime quest attachment",
        ),
    }
    quest_targets: dict[str, tuple[str, dict]] = {}
    recovered_black_timeline_keys = {
        black_key
        for black_key, _dialog_key in black_timeline_groups
    }
    recovered_dialog_tree_narrative_keys = {
        black_key
        for black_key, _dialog_key in dialog_tree_narrative_groups
    }

    for owner_mission, flow_payload in mission_flows_payload.items():
        for quest in flow_payload.get("quests") or []:
            if isinstance(quest, dict) and quest.get("id"):
                quest_targets[str(quest["id"])] = (owner_mission, quest)

    pending_dialog_tree_quest_state_dependencies = (
        recover_dialog_tree_quest_state_dependencies(dialog_id_registry)
    )
    for mission, timeline_recovery in mission_timelines_by_mission.items():
        available = scene_keys_by_mission.get(mission, set())
        for placement in (timeline_recovery.get("scenePlacement") or {}).values():
            if not isinstance(placement, dict):
                continue
            raw_scene_key = str(placement.get("sceneKey") or "")
            local_scene_key = resolve_scene_ref_out_key(
                raw_scene_key,
                available,
            )
            for attachment in placement.get("questAttachSources") or []:
                if not isinstance(attachment, dict):
                    continue
                attachment_source = str(attachment.get("source") or "")
                # Script conditions can deliberately invoke a Story file
                # owned by a different mission (and can target reading-text
                # rows). Resolve those exact authored references against the
                # complete language corpus; variant-runtime recovery remains
                # restricted to the owning mission's scene set.
                scene_key = local_scene_key
                if not scene_key and attachment_source == "scriptCondition":
                    scene_key = resolve_scene_ref_out_key(
                        raw_scene_key,
                        all_story_entry_keys,
                    )
                if not scene_key:
                    continue
                if attachment_source == "scriptCondition":
                    # A recovered scene placement can span neighboring
                    # LevelScripts. When current-build typed playback exists,
                    # an exact mismatch is negative evidence: do not claim
                    # that a quest condition observing script B scopes a
                    # dialog whose native playback is in script A.
                    native_parent_occurrences = list(
                        native_story_playback_index.get(scene_key) or []
                    )
                    if native_parent_occurrences:
                        attachment_pair = (
                            str(attachment.get("mapId") or ""),
                            str(attachment.get("scriptId") or ""),
                        )
                        native_pairs = {
                            (
                                str(row.get("levelId") or ""),
                                str(row.get("scriptId") or ""),
                            )
                            for row in native_parent_occurrences
                            if row.get("levelId") and row.get("scriptId")
                        }
                        if attachment_pair not in native_pairs:
                            continue
                quest_target = quest_targets.get(str(attachment.get("questId") or ""))
                attachment_type = recovered_attachment_types.get(attachment_source)
                if not quest_target or not attachment_type:
                    continue
                _, quest = quest_target
                relation, confidence, source_label = attachment_type
                connection = {
                    "key": scene_key,
                    "kind": story_kind_by_key.get(
                        scene_key,
                        str(placement.get("kind") or "story"),
                    ),
                    "relation": relation,
                    "direction": "context",
                    "phase": "context",
                    "confidence": confidence,
                    "source": source_label,
                }
                for field_name in ("mapId", "scriptId", "variantMission", "npcProxyId"):
                    if attachment.get(field_name) not in (None, ""):
                        connection[field_name] = attachment[field_name]
                if attachment.get("key") not in (None, ""):
                    connection["conditionKey"] = attachment["key"]
                if attachment.get("kind") not in (None, ""):
                    connection["attachmentKind"] = attachment["kind"]
                connections = quest.setdefault("storyConnections", [])
                signature = (
                    scene_key,
                    relation,
                    str(connection.get("mapId") or ""),
                    str(connection.get("scriptId") or ""),
                    str(connection.get("conditionKey") or ""),
                    str(connection.get("variantMission") or ""),
                    str(connection.get("attachmentKind") or ""),
                    str(connection.get("npcProxyId") or ""),
                )
                if any((
                    existing.get("key"),
                    existing.get("relation"),
                    str(existing.get("mapId") or ""),
                    str(existing.get("scriptId") or ""),
                    str(existing.get("conditionKey") or ""),
                    str(existing.get("variantMission") or ""),
                    str(existing.get("attachmentKind") or ""),
                    str(existing.get("npcProxyId") or ""),
                ) == signature for existing in connections if isinstance(existing, dict)):
                    continue
                connections.append(connection)

    # Promote only an immediate authored Story-graph neighbor when the other
    # endpoint is already attached to exactly one quest. This is intentionally
    # non-transitive: it captures explicit DialogTree routes and LevelScript
    # next-id chains without flooding an entire component from one seed.
    attached_quests_by_story_key: dict[str, set[str]] = defaultdict(set)
    for flow_payload in mission_flows_payload.values():
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for row in quest.get("storyConnections") or []:
                if not isinstance(row, dict):
                    continue
                story_key = str(row.get("key") or "")
                if story_key in all_available_scene_keys:
                    attached_quests_by_story_key[story_key].add(quest_id)

    graph_neighbor_candidates: dict[str, list[dict]] = defaultdict(list)
    promotable_graph_edge_kinds = {"authoredDirect", "levelscriptSceneChain"}
    for graph_mission, flow_payload in mission_flows_payload.items():
        scene_graph = flow_payload.get("sceneGraph") or {}
        for edge in scene_graph.get("edges") or []:
            if not isinstance(edge, dict) or edge.get("kind") not in promotable_graph_edge_kinds:
                continue
            source_key = str(edge.get("from") or "")
            target_key = str(edge.get("to") or "")
            if source_key not in all_available_scene_keys or target_key not in all_available_scene_keys:
                continue
            for unattached_key, anchor_key in ((source_key, target_key), (target_key, source_key)):
                if attached_quests_by_story_key.get(unattached_key):
                    continue
                anchor_quests = attached_quests_by_story_key.get(anchor_key) or set()
                if len(anchor_quests) != 1:
                    continue
                quest_id = next(iter(anchor_quests))
                quest_target = quest_targets.get(quest_id)
                if not quest_target or quest_target[0] != graph_mission:
                    continue
                graph_neighbor_candidates[unattached_key].append({
                    "questId": quest_id,
                    "anchor": anchor_key,
                    "edgeKind": edge.get("kind"),
                    "sourceFiles": list(edge.get("sourceFiles") or []),
                    "levelIds": list(edge.get("levelIds") or []),
                    "sourceKeys": list(edge.get("sourceKeys") or []),
                    "optionIds": list(edge.get("optionIds") or []),
                })

    for story_key, candidates in sorted(graph_neighbor_candidates.items()):
        candidate_quest_ids = {
            str(candidate.get("questId") or "")
            for candidate in candidates
            if candidate.get("questId")
        }
        if len(candidate_quest_ids) != 1:
            continue
        quest_id = next(iter(candidate_quest_ids))
        quest_target = quest_targets.get(quest_id)
        if not quest_target:
            continue
        _, quest = quest_target
        edge_kinds = sorted({
            str(candidate.get("edgeKind") or "")
            for candidate in candidates
            if candidate.get("edgeKind")
        })
        is_authored_branch = "authoredDirect" in edge_kinds
        relation = (
            "story_graph_branch" if is_authored_branch
            else "levelscript_story_sequence"
        )
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": relation,
            "direction": "context",
            "phase": "context",
            "confidence": (
                "scoped_authored" if is_authored_branch
                else "scoped_sequence"
            ),
            "source": (
                "authored DialogTree route from uniquely quest-anchored Story file"
                if is_authored_branch
                else "LevelScript next-id Story chain from uniquely quest-anchored Story file"
            ),
            "anchors": sorted({
                str(candidate.get("anchor") or "")
                for candidate in candidates
                if candidate.get("anchor")
            }),
            "edgeKinds": edge_kinds,
        }
        for output_field in ("sourceFiles", "levelIds", "sourceKeys", "optionIds"):
            values = sorted({
                str(value)
                for candidate in candidates
                for value in candidate.get(output_field) or []
                if value not in (None, "")
            })
            if values:
                connection[output_field] = values
        quest.setdefault("storyConnections", []).append(connection)

    # A Story id in an actionList record proves only that the LevelScript can
    # reference it. Promote that id to mission-shell context only when a
    # separate original-data edge uniquely scopes the exact containing script
    # to a MissionRuntime: either an exact mission/quest string in the script
    # or a typed MissionRuntime condition checking that script. The scoped
    # mission can differ from the Story key's naming owner because authored
    # dungeon/encounter missions intentionally reuse parent-mission Story ids.
    preexisting_attached_story_keys_by_mission: dict[str, set[str]] = defaultdict(set)
    for attached_mission, flow_payload in mission_flows_payload.items():
        preexisting_attached_story_keys_by_mission[attached_mission].update(
            str(row.get("key") or "")
            for row in flow_payload.get("missionStoryConnections") or []
            if isinstance(row, dict) and row.get("key")
        )
        preexisting_attached_story_keys_by_mission[attached_mission].update(
            str(row.get("key") or "")
            for quest in flow_payload.get("quests") or []
            for row in quest.get("storyConnections") or []
            if isinstance(row, dict) and row.get("key")
        )
    mission_runtime_id_set = set(mission_runtime_ids)
    quest_owner_candidates: dict[str, set[str]] = defaultdict(set)
    for owner_mission, flow_payload in mission_flows_payload.items():
        for quest in flow_payload.get("quests") or []:
            quest_id = str(quest.get("id") or "")
            if quest_id:
                quest_owner_candidates[quest_id].add(str(owner_mission))
    quest_owner_by_id = {
        quest_id: next(iter(owner_missions))
        for quest_id, owner_missions in quest_owner_candidates.items()
        if len(owner_missions) == 1
    }

    # Patrol checkpoint listeners carry no mission or quest id themselves.
    # Bind them only after the complete original-data chain agrees: exact
    # receiver-to-playback control path, typed BriefData alias -> world entity,
    # same-script NpcPatrolStart(alias, patrolId), framed NpcPatrolData point,
    # and same-scene EntityTrackingInfo rows whose mission union is unique.
    # Multiple candidate quests remain display evidence and never become
    # activation, playback, completion, or ownership claims.
    for context in build_npc_patrol_checkpoint_mission_contexts(
        native_non_fmv_story_playback_index,
        mission_flows_payload,
    ):
        target_mission = str(context.get("missionId") or "")
        story_key = str(context.get("storyKey") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not isinstance(flow_payload, dict)
            or not story_key
            or story_key not in all_story_entry_keys
        ):
            continue
        occurrences = list(context.get("occurrences") or [])
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "radio"),
            "relation": "mission_tracked_npc_patrol_entity_context",
            "direction": "context",
            "phase": "local_npc_patrol_checkpoint",
            "confidence": "native_exact_mission_navigation_context",
            "evidenceTier": "derived_exact_foreign_key",
            "source": (
                "exact current-build patrol checkpoint receiver -> Story path + "
                "typed same-script LevelData property/world-entity/patrol data + "
                "NpcPatrolStart producer + one-mission MissionRuntime "
                "EntityTrackingInfo union"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "questTriggerStatus": (
                "mission_navigation_context_not_unique_quest_activation_"
                "playback_or_completion"
            ),
            "executionSide": "client",
            "networkRole": "local_npc_patrol_runtime_event",
            "transport": "local-npc-patrol-runtime-event",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "serverEvidenceStatus": (
                "NpcPatrolStart and checkpoint dispatch are local gameplay "
                "events; no request, server push, or reply is serialized by "
                "this route"
            ),
            "worldEntityId": context.get("worldEntityId"),
            "candidateQuestIds": context.get("candidateQuestIds") or [],
            "trackingRows": context.get("trackingRows") or [],
            "occurrenceCount": len(occurrences),
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in occurrences
                if row.get("scriptId")
            }),
            "npcEntityPropertyPaths": sorted({
                str(row.get("npcEntityPropertyPath") or "")
                for row in occurrences
                if row.get("npcEntityPropertyPath")
            }),
            "patrolIds": sorted({
                int(row["patrolId"])
                for row in occurrences
                if isinstance(row.get("patrolId"), int)
            }),
            "checkpointIndices": sorted({
                int(row["checkpointIndex"])
                for row in occurrences
                if isinstance(row.get("checkpointIndex"), int)
            }),
            "nativeActions": sorted({
                str(row.get("nativeAction") or "")
                for row in occurrences
                if row.get("nativeAction")
            }),
            "sourceFiles": context.get("sourceFiles") or [],
            "patrolEvidence": occurrences,
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # A residual Leader-trigger listener serializes only its local trigger slot.
    # Attach mission context only when the exact containing LevelScript has a
    # fully decoded BriefData world-entity reference whose same-scene typed
    # EntityTrackingInfo consumers all belong to one MissionRuntime.  The
    # trigger volume is decoded independently and must be local
    # (waitSrvRes=false). Multiple quest trackers remain candidate navigation
    # evidence; none becomes activation, playback, completion, or ownership.
    for context in build_mission_tracked_world_entity_levelscript_contexts(
        native_non_fmv_story_playback_index,
        mission_flows_payload,
    ):
        target_mission = str(context.get("missionId") or "")
        story_key = str(context.get("storyKey") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not isinstance(flow_payload, dict)
            or not story_key
            or story_key not in all_story_entry_keys
            or story_key
            in preexisting_attached_story_keys_by_mission.get(target_mission, set())
        ):
            continue
        occurrences = list(context.get("occurrences") or [])
        world_entity_ids = list(context.get("worldEntityIds") or [])
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "radio"),
            "relation": "mission_tracked_world_entity_levelscript_context",
            "direction": "context",
            "phase": "local_leader_trigger_world_entity_context",
            "confidence": "native_exact_mission_navigation_context",
            "evidenceTier": "derived_exact_foreign_key",
            "source": (
                "exact current-build Leader trigger receiver -> Story path + "
                "decoded local trigger volume + typed same-script LevelData "
                "BriefData world-entity refs + one-mission MissionRuntime "
                "EntityTrackingInfo union"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "questTriggerStatus": (
                "shared_script_world_entity_tracking_context_not_trigger_gate"
            ),
            "executionSide": "client",
            "networkRole": "local_authored_trigger_volume_event",
            "transport": "local-authored-trigger-volume-event",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "expectedReturn": "none",
            "serverEvidenceStatus": (
                "the selected Leader volume has waitSrvRes=false; no mission "
                "or quest id, client request, server push, reply, or expected "
                "return is serialized by this playback route"
            ),
            "worldEntityIds": world_entity_ids,
            "worldEntityId": (
                world_entity_ids[0] if len(world_entity_ids) == 1 else ""
            ),
            "candidateQuestIds": context.get("candidateQuestIds") or [],
            "trackingRows": context.get("trackingRows") or [],
            "occurrenceCount": len(occurrences),
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in occurrences
                if row.get("scriptId")
            }, key=int),
            "triggerSlotIds": sorted({
                int(row["triggerSlotId"])
                for row in occurrences
                if isinstance(row.get("triggerSlotId"), int)
                and not isinstance(row.get("triggerSlotId"), bool)
            }),
            "nativeActions": sorted({
                str(row.get("nativeAction") or "")
                for row in occurrences
                if row.get("nativeAction")
            }),
            "sourceFiles": context.get("sourceFiles") or [],
            "worldEntityLevelScriptEvidence": occurrences,
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # StageChanged receivers are local client events, but the current native
    # runtime reaches them from SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE. Recover a
    # mission shell only through the same exact typed world-entity join used
    # above, additionally allowing the LevelScript global id itself to be the
    # uniquely registered tracked entity. This does not prove which quest (or
    # any client request) caused the server to push the stage.
    for context in build_mission_tracked_world_entity_levelscript_contexts(
        native_non_fmv_story_playback_index,
        mission_flows_payload,
        receiver_family="stage",
    ):
        target_mission = str(context.get("missionId") or "")
        story_key = str(context.get("storyKey") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not isinstance(flow_payload, dict)
            or not story_key
            or story_key not in all_story_entry_keys
            or story_key
            in preexisting_attached_story_keys_by_mission.get(target_mission, set())
        ):
            continue
        occurrences = list(context.get("occurrences") or [])
        preloads = list(context.get("preloadOccurrences") or [])
        world_entity_ids = list(context.get("worldEntityIds") or [])
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "radio"),
            "relation": "mission_tracked_world_entity_levelscript_stage_context",
            "direction": "context",
            "phase": "server_synced_levelscript_stage",
            "confidence": "native_exact_mission_navigation_context",
            "evidenceTier": "derived_exact_foreign_key",
            "source": (
                "exact current-build StageChanged receiver -> Story path + "
                "typed same-script LevelData/world-entity resolution + "
                "one-mission MissionRuntime EntityTrackingInfo union + "
                "native server stage-push handler chain"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "questTriggerStatus": (
                "shared_script_world_entity_tracking_context_not_stage_writer"
            ),
            "executionSide": "server_synced_client_runtime_playback",
            "networkRole": "server_to_client_stage_push_then_local_event",
            "transport": "server-stage-push-to-local-level-script-event",
            "serverExchange": True,
            "clientRequest": False,
            "expectedClientReply": False,
            "expectedReturn": "none",
            "serverMessage": "SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE",
            "serverFields": ["sceneNumId", "scriptId", "stage"],
            "serverEvidenceStatus": (
                "the server pushes scriptId/stage and the client dispatches "
                "OnScriptStageChanged; no paired client stage request, mission "
                "id, quest id, reply, or proof that a candidate quest wrote "
                "the stage exists in this route"
            ),
            "nativeConsumers": [
                {
                    "method": "_Handle_SyncLevelScriptStage",
                    "address": "0x1873867cc",
                },
                {
                    "method": "ServerSyncLevelScriptStage",
                    "address": "0x186f95310",
                },
                {
                    "method": "UpdateStage",
                    "address": "0x186fad930",
                },
                {
                    "method": "OnScriptStageChanged",
                    "address": "0x186fab7dc",
                },
            ],
            "worldEntityIds": world_entity_ids,
            "worldEntityId": (
                world_entity_ids[0] if len(world_entity_ids) == 1 else ""
            ),
            "candidateQuestIds": context.get("candidateQuestIds") or [],
            "trackingRows": context.get("trackingRows") or [],
            "occurrenceCount": len(occurrences),
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in occurrences
                if row.get("scriptId")
            }, key=int),
            "stageFilters": sorted({
                int(row["stageFilter"])
                for row in occurrences
                if isinstance(row.get("stageFilter"), int)
                and not isinstance(row.get("stageFilter"), bool)
            }),
            "nativeActions": sorted({
                str(row.get("nativeAction") or "")
                for row in occurrences
                if row.get("nativeAction")
            }),
            "worldEntityResolutionModes": sorted({
                str(resolution.get("resolutionMode") or "")
                for row in occurrences
                for resolution in row.get("entityResolutions") or []
                if resolution.get("resolutionMode")
            }),
            "levelDataEntityPropertyNames": sorted({
                str(resolution.get("propertyName") or "")
                for row in occurrences
                for resolution in row.get("entityResolutions") or []
                if resolution.get("propertyName")
            }),
            "sourceFiles": context.get("sourceFiles") or [],
            "worldEntityLevelScriptEvidence": occurrences,
            "preloadOccurrences": preloads,
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    def original_table_source_files(*names: str) -> list[str]:
        return sorted({
            repo_rel(path)
            for name in names
            for path in (
                STREAMING_TABLE_DIR / name,
                PERSISTENT_TABLE_DIR / name,
            )
            if path.is_file()
        })

    # DomainDepot is a system-authored mission shell rather than a quest-authored
    # dialog sequence.  The feature constant names f1m25 directly; the two
    # delivery tables provide the exact NPC/target/Dialog foreign-key chain.
    # Hold these exact system-shell carriers until every stronger quest/native
    # attachment family has materialized.  The late global-connectedness gate
    # prevents the six already-proven f1m33 delivery dialogs from being
    # duplicated under f1m25 while retaining the 24 otherwise-unlinked rows.
    pending_original_system_story_connections: list[
        tuple[str, str, dict]
    ] = []
    for carrier in build_domain_depot_story_connections(
        domain_depot_const,
        domain_depot_dialogs,
        domain_depot_targets,
        mission_runtime_id_set,
    ):
        target_mission = str(carrier.get("missionId") or "")
        story_key = str(carrier.get("key") or "")
        nominal_story_owner = story_owner_by_key.get(story_key) or ""
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            # Scope reduction only: a different existing Story group prevents
            # this system-shell fallback from manufacturing a cross-owner
            # placement. It is never used to create positive evidence.
            or (
                nominal_story_owner
                and nominal_story_owner != target_mission
            )
            or not isinstance(flow_payload, dict)
        ):
            continue
        connection = {
            **carrier,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "domain_depot_delivery_dialog",
            "direction": "context",
            "phase": str(carrier.get("dialogPhase") or "delivery_dialog"),
            "confidence": "typed_original_data_plus_native_runtime_consumer",
            "evidenceTier": "direct",
            "source": (
                "DomainDepotConst.depotDeliverMissionId and exact "
                "DialogTable[npcProxyId] -> DeliverTargetTable.targetId join; "
                "native delivery response handling installs the dialog override"
            ),
            "sourceFiles": original_table_source_files(
                "DomainDepotConst.json",
                "DomainDepotDeliverTargetDialogTable.json",
                "DomainDepotDeliverTargetTable.json",
            ),
            "storyOwnerMission": nominal_story_owner,
            "questTriggerStatus": (
                "exact_system_mission_shell_without_quest_identity"
            ),
            "executionSide": "client_and_server",
            "networkRole": "server_response_installs_delivery_dialog",
            "serverExchange": True,
            "clientRequest": True,
            "expectedClientReply": True,
            "serverMessage": (
                "CS_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_REQ -> "
                "SC_DOMAIN_DEPOT_RECV_PACKAGE_FOR_DELIVER_RSP; dialog finish -> "
                "CS_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_REQ"
            ),
            "serverFields": ["deliverInstId"],
            "expectedReturn": (
                "SC_DOMAIN_DEPOT_SEND_PACKAGE_FOR_DELIVER_RSP"
                "{deliverInstId,rewardValue,extraCreditCount}"
            ),
            "serverEvidenceStatus": (
                "native _HandleDomainDepotRecvPackageForDeliverRsp calls "
                "_AddDialogInDelivering; _OnTargetDialogFinish sends the "
                "package-delivery completion request"
            ),
            "nativeConsumers": [
                {
                    "method": "GetDeliverStaticDataForMissionWrapper",
                    "address": "0x187300b08",
                },
                {
                    "method": "_AddDialogInDelivering",
                    "address": "0x18730238c",
                },
                {
                    "method": "_OnTargetDialogFinish",
                    "address": "0x187305764",
                },
            ],
            "nativeMappingId": "domain-depot-delivery-dialog-tables-native-v1",
        }
        pending_original_system_story_connections.append((
            target_mission,
            story_key,
            connection,
        ))

    # SkipChapterTable co-authors the MissionRuntime id, dialog id, activity id,
    # and protocol configuration id in one typed original-data row.
    for carrier in build_skip_chapter_story_connections(
        skip_chapter_rows,
        mission_runtime_id_set,
    ):
        target_mission = str(carrier.get("missionId") or "")
        story_key = str(carrier.get("key") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or not isinstance(flow_payload, dict)
        ):
            continue
        connection = {
            **carrier,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "skip_chapter_bound_dialog",
            "direction": "context",
            "phase": "chapter_skip",
            "confidence": "typed_original_data_plus_native_protocol_sender",
            "evidenceTier": "direct",
            "source": (
                "one SkipChapterTable row directly co-carries missionId, "
                "bindDlgId, bindActivityId, and skipChapterConfigId"
            ),
            "sourceFiles": original_table_source_files("SkipChapterTable.json"),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "questTriggerStatus": (
                "exact_system_mission_shell_without_quest_identity"
            ),
            "executionSide": "client_and_server",
            "networkRole": "client_skip_chapter_request",
            "serverExchange": True,
            "clientRequest": True,
            "expectedClientReply": True,
            "serverMessage": "CS_DO_SKIP_CHAPTER",
            "serverFields": ["SkipChapterConfigId"],
            "expectedReturn": "SC_DO_SKIP_CHAPTER{SkipChapterConfigId}",
            "serverEvidenceStatus": (
                "ActivitySystem.SendDoSkipChapter constructs and sends the "
                "typed request; _HandleDoSkipChapter consumes the matching response"
            ),
            "nativeConsumers": [
                {
                    "method": "ActivitySystem.SendDoSkipChapter",
                    "address": "0x1872cd7d0",
                    "token": "0x06003dab",
                },
                {
                    "method": "ActivitySystem._HandleDoSkipChapter",
                    "address": "0x1872cf2b8",
                    "token": "0x06003dbd",
                },
            ],
            "nativeMappingId": "skip-chapter-table-native-protocol-v1",
        }
        pending_original_system_story_connections.append((
            target_mission,
            story_key,
            connection,
        ))

    # FactoryBuildingPanelLock is intentionally dependency-only.  Native
    # CheckBuildingLock reads the two authored quest states and returns the
    # radio id for local playback; it does not establish a Story owner and it
    # does not send a packet on this path.
    for carrier in build_factory_lock_story_dependencies(
        factory_building_panel_locks,
        quest_targets,
    ):
        target_mission = str(carrier.get("missionId") or "")
        story_key = str(carrier.get("key") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or not isinstance(flow_payload, dict)
        ):
            continue
        quest_gate_roles = list(carrier.get("questGateRoles") or [])
        dependency = {
            **carrier,
            "kind": story_kind_by_key.get(story_key, "radio"),
            "relation": "factory_panel_lock_quest_state_dependency",
            "direction": "dependency",
            "phase": "factory_building_lock_check",
            "confidence": "typed_original_data_plus_native_quest_state_consumer",
            "evidenceTier": "direct",
            "source": (
                "FactoryBuildingPanelLock row co-carries radioId and exact quest "
                "state boundaries; native FactoryUtil.CheckBuildingLock reads "
                "those quest ids and returns the radio id"
            ),
            "sourceFiles": original_table_source_files(
                "FactoryBuildingPanelLock.json"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "missionStateId": target_mission,
            "missionStateGateRoles": [
                str(row.get("field") or "")
                for row in quest_gate_roles
                if row.get("field")
            ],
            "missionStateGatePredicates": [
                f"FactoryBuildingPanelLock.{row.get('field')} = {row.get('questId')}"
                for row in quest_gate_roles
                if row.get("field") and row.get("questId")
            ],
            "questTriggerStatus": "exact_quest_state_dependency_without_ownership",
            "storyBinding": False,
            "ownership": False,
            "dependencyOnly": True,
            "executionSide": "client",
            "networkRole": "reads_synchronized_local_quest_state",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "upstreamServerStateSources": [
                "SC_SYNC_ALL_MISSION",
                "SC_QUEST_STATE_UPDATE",
            ],
            "upstreamServerStateRole": (
                "independent server pushes populate the local MissionSystem "
                "quest cache; checking the factory lock sends no request"
            ),
            "serverEvidenceStatus": (
                "FactoryUtil.CheckBuildingLock calls MissionSystem.GetQuestState "
                "twice and writes out radioId; no direct request/reply belongs "
                "to this local presentation path"
            ),
            "nativeConsumer": {
                "method": "FactoryUtil.CheckBuildingLock",
                "address": "0x18747ec68",
                "token": "0x060063eb",
            },
            "nativeMappingId": "factory-panel-lock-quest-radio-native-v1",
        }
        dependencies = flow_payload.setdefault(
            "missionStateStoryDependencies",
            [],
        )
        signature = (
            story_key,
            str(dependency.get("relation") or ""),
            str(dependency.get("factoryBuildingId") or ""),
            int(dependency.get("conditionIndex") or 0),
            target_mission,
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("factoryBuildingId") or ""),
            int(existing.get("conditionIndex") or 0),
            str(existing.get("missionStateId") or ""),
        ) == signature for existing in dependencies if isinstance(existing, dict)):
            dependencies.append(dependency)

    allowed_script_condition_types = {
        "CheckLevelScriptPropertyBool",
        "CheckLevelScriptPropertyInt",
        "CheckLevelScriptStage",
        "CheckLevelScriptStageReachMax",
        "CheckLevelScriptTaskFinished",
        "CheckScriptMonsterKilled",
    }
    script_condition_bindings: dict[tuple[str, str], list[dict]] = defaultdict(list)
    interactive_condition_script_bindings: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)
    world_entity_condition_groups: list[dict] = []
    world_entity_condition_refs: list[dict] = []
    for mission_runtime_path in mission_runtime_paths:
        try:
            mission_runtime_raw = load_json_path(
                mission_runtime_path,
                mission_runtime_path.name,
            )
        except (OSError, json.JSONDecodeError):
            continue
        condition_mission = str(
            mission_runtime_raw.get("missionId") or mission_runtime_path.stem
        ).strip()
        if condition_mission not in mission_runtime_id_set:
            continue
        condition_source_file = repo_rel(mission_runtime_path)
        world_entity_condition_groups.extend({
            **condition,
            "missionId": condition_mission,
            "sourceFile": condition_source_file,
        } for condition in decode_mission_world_entity_condition_groups(
            mission_runtime_raw
        ))
        world_entity_condition_refs.extend({
            **condition,
            "missionId": condition_mission,
            "sourceFile": condition_source_file,
        } for condition in decode_mission_world_entity_condition_refs(
            mission_runtime_raw
        ))
        for condition in decode_mission_script_conditions(mission_runtime_raw):
            type_name = str(condition.get("type") or "").split(",", 1)[0]
            short_type = type_name.rsplit(".", 1)[-1]
            if short_type not in allowed_script_condition_types:
                continue
            map_id = str(condition.get("mapId") or "").strip()
            script_id = str(condition.get("scriptId") or "").strip()
            if not map_id or not script_id:
                continue
            script_condition_bindings[(map_id, script_id)].append({
                "missionId": condition_mission,
                "questId": str(condition.get("questId") or ""),
                "conditionType": short_type,
                "conditionKey": str(condition.get("key") or ""),
                "conditionValue": condition.get("value"),
                "sourceFile": condition_source_file,
            })
        for condition in decode_mission_interactive_script_entity_conditions(
            mission_runtime_raw
        ):
            resolution = resolve_interactive_condition_script_entity(condition)
            if resolution.get("status") != "unique":
                continue
            map_id = str(resolution.get("levelId") or "")
            script_id = str(resolution.get("scriptId") or "")
            if not map_id or not script_id:
                continue
            interactive_condition_script_bindings[(map_id, script_id)].append({
                "missionId": condition_mission,
                "questId": str(condition.get("questId") or ""),
                "conditionType": "InteractiveCheckInt",
                "conditionKey": str(condition.get("key") or ""),
                "conditionValue": condition.get("compareValue"),
                "conditionComparer": condition.get("comparer"),
                "entityLogicId": resolution.get("logicId"),
                "entitySlotId": resolution.get("entitySlotId"),
                "entityType": resolution.get("entityType"),
                "entityDetailId": str(resolution.get("entityDetailId") or ""),
                "registryIndex": resolution.get("registryIndex"),
                "sourceFile": condition_source_file,
                "registrySourceFile": str(
                    resolution.get("registrySourceFile") or ""
                ),
                "levelScriptSourceFile": str(
                    resolution.get("levelScriptSourceFile") or ""
                ),
            })

    action_story_occurrences = build_levelscript_action_story_occurrences()

    # ON_SPAWNER_COMPLETE carries an exact uint64 SpawnerPtr from the server
    # completion push into the local LevelEvent.  A current SpawnerConfig can
    # then provide authored mission context when that id is globally unique and
    # its embedded entity identifiers agree on one exact MissionRuntime id.
    # This is mission context only; the server push itself is not quest-scoped.
    spawner_config_mission_index = build_spawner_config_mission_index(
        mission_runtime_id_set
    )
    for story_key, occurrences in sorted(
        native_non_fmv_story_playback_index.items()
    ):
        if story_key not in all_story_entry_keys:
            continue
        candidates: list[dict] = []
        candidate_missions: set[str] = set()
        for occurrence in occurrences:
            occurrence_level = str(occurrence.get("levelId") or "")
            for owner in occurrence.get("nativeEventOwners") or []:
                event_detail = owner.get("eventDetail") or {}
                if event_detail.get("type") != "LevelEvent_OnSpawnerComplete":
                    continue
                spawner_id = event_detail.get("spawnerFilterId")
                if not isinstance(spawner_id, int):
                    continue
                resolution = spawner_config_mission_index.get(spawner_id) or {}
                if resolution.get("status") != "unique":
                    continue
                configs = list(resolution.get("configs") or [])
                mission_ids = list(resolution.get("missionIds") or [])
                if (
                    len(configs) != 1
                    or len(mission_ids) != 1
                    or str(configs[0].get("levelId") or "") != occurrence_level
                ):
                    continue
                target_mission = str(mission_ids[0])
                candidate_missions.add(target_mission)
                candidates.append({
                    "missionId": target_mission,
                    "spawnerId": spawner_id,
                    "config": configs[0],
                    "occurrence": occurrence,
                    "eventOwner": owner,
                })
        if not candidates or len(candidate_missions) != 1:
            continue
        target_mission = next(iter(candidate_missions))
        if (
            target_mission not in mission_flows_payload
            or story_key in preexisting_attached_story_keys_by_mission[target_mission]
        ):
            continue
        source_files = sorted({
            str(candidate["occurrence"].get("sourceFile") or "")
            for candidate in candidates
        } | {
            str(candidate["config"].get("sourceFile") or "")
            for candidate in candidates
        } | {
            repo_rel(MRA_DIR / f"{target_mission}.json")
        } - {""})
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "spawner_config_authored_mission_context",
            "direction": "context",
            "phase": "server_completion_push",
            "confidence": "native_exact_authored_config_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "exact current-build OnSpawnerComplete SpawnerPtr + unique same-level "
                "original SpawnerConfig id + one exact MissionRuntime id embedded in "
                "authored config identifiers; mission context only, not quest ownership"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "spawnerConfigMissionId": target_mission,
            "questTriggerStatus": "server_push_not_quest_scoped",
            "executionSide": "client",
            "networkRole": "server_to_client_push_then_local_event",
            "serverExchange": True,
            "serverMessage": "SC_SCENE_MONSTER_SPAWNER_COMPLETE",
            "serverFields": ["sceneNumId", "spawnerId"],
            "clientRequest": False,
            "expectedClientReply": False,
            "spawnerIds": sorted({
                candidate["spawnerId"] for candidate in candidates
            }),
            "levelIds": sorted({
                str(candidate["occurrence"].get("levelId") or "")
                for candidate in candidates
                if candidate["occurrence"].get("levelId")
            }),
            "scriptIds": sorted({
                str(candidate["occurrence"].get("scriptId") or "")
                for candidate in candidates
                if candidate["occurrence"].get("scriptId")
            }),
            "authoredSpawnerTokens": sorted({
                str(token)
                for candidate in candidates
                for token in candidate["config"].get("authoredTokens") or []
                if token
            }),
            "sourceFiles": source_files,
            "nativeControlPathCount": len(candidates),
            "spawnerConfigEvidence": candidates,
        }
        mission_flows_payload[target_mission].setdefault(
            "missionStoryConnections", []
        ).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # A dynamic OnEntityHpChanged list can still be resolved without naming
    # guesses when one exact OnSpawnerEntitySpawn header feeds it through one
    # exact ListAddValueEntityPtr action in the same LevelScript.  Reuse the
    # same fail-closed SpawnerConfig mission index as the completion path, but
    # keep this edge local and mission-level: HP dispatch itself sends no RPC
    # and the current MissionRuntime objectives do not identify one quest.
    for story_key, occurrences in sorted(
        native_non_fmv_story_playback_index.items()
    ):
        if story_key not in all_story_entry_keys:
            continue
        candidates: list[dict] = []
        candidate_missions: set[str] = set()
        for occurrence in occurrences:
            occurrence_level = str(occurrence.get("levelId") or "")
            for owner in occurrence.get("nativeEventOwners") or []:
                hp_context = resolve_dynamic_hp_spawner_context(occurrence, owner)
                if hp_context.get("status") != "exact":
                    continue
                spawner_id = hp_context.get("spawnerId")
                if not isinstance(spawner_id, int):
                    continue
                resolution = spawner_config_mission_index.get(spawner_id) or {}
                configs = list(resolution.get("configs") or [])
                mission_ids = list(resolution.get("missionIds") or [])
                if (
                    resolution.get("status") != "unique"
                    or len(configs) != 1
                    or len(mission_ids) != 1
                    or str(configs[0].get("levelId") or "") != occurrence_level
                ):
                    continue
                target_mission = str(mission_ids[0])
                candidate_missions.add(target_mission)
                candidates.append({
                    "missionId": target_mission,
                    "spawnerId": spawner_id,
                    "config": configs[0],
                    "occurrence": occurrence,
                    "eventOwner": owner,
                    "hpSpawnerContext": hp_context,
                })
        if not candidates or len(candidate_missions) != 1:
            continue
        target_mission = next(iter(candidate_missions))
        if (
            target_mission not in mission_flows_payload
            or story_key in preexisting_attached_story_keys_by_mission[target_mission]
        ):
            continue
        source_files = sorted({
            str(candidate["occurrence"].get("sourceFile") or "")
            for candidate in candidates
        } | {
            str(candidate["config"].get("sourceFile") or "")
            for candidate in candidates
        } | {
            repo_rel(MRA_DIR / f"{target_mission}.json")
        } - {""})
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "hp_spawner_config_authored_mission_context",
            "direction": "context",
            "phase": "local_hp_threshold",
            "confidence": "native_exact_authored_config_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "exact current-build OnSpawnerEntitySpawn -> ListAddValueEntityPtr "
                "-> OnEntityHpChanged list -> Story path + unique same-level original "
                "SpawnerConfig id + one exact MissionRuntime id embedded in authored "
                "config identifiers; mission context only, not quest ownership"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "spawnerConfigMissionId": target_mission,
            "questTriggerStatus": "mission_context_only_quest_unresolved",
            "executionSide": "client",
            "networkRole": "local_runtime_event",
            "serverExchange": False,
            "clientRequest": False,
            "expectedServerReply": False,
            "spawnerIds": sorted({
                candidate["spawnerId"] for candidate in candidates
            }),
            "spawnerGroupKeys": sorted({
                str(candidate["hpSpawnerContext"].get("groupKey") or "")
                for candidate in candidates
                if candidate["hpSpawnerContext"].get("groupKey")
            }),
            "hpRatios": sorted({
                candidate["hpSpawnerContext"].get("hpRatio")
                for candidate in candidates
                if candidate["hpSpawnerContext"].get("hpRatio") is not None
            }),
            "entityListPaths": sorted({
                str(candidate["hpSpawnerContext"].get("entityListPath") or "")
                for candidate in candidates
                if candidate["hpSpawnerContext"].get("entityListPath")
            }),
            "levelIds": sorted({
                str(candidate["occurrence"].get("levelId") or "")
                for candidate in candidates
                if candidate["occurrence"].get("levelId")
            }),
            "scriptIds": sorted({
                str(candidate["occurrence"].get("scriptId") or "")
                for candidate in candidates
                if candidate["occurrence"].get("scriptId")
            }),
            "authoredSpawnerTokens": sorted({
                str(token)
                for candidate in candidates
                for token in candidate["config"].get("authoredTokens") or []
                if token
            }),
            "sourceFiles": source_files,
            "nativeControlPathCount": len(candidates),
            "hpSpawnerConfigEvidence": candidates,
        }
        mission_flows_payload[target_mission].setdefault(
            "missionStoryConnections", []
        ).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # EntityTrackingInfo is resolved by the client from a local script/slot to
    # one WorldEntityRegistry entry. Two deliberately narrow joins are useful
    # for Story recovery:
    #
    # * an exact ``interactives[slot].properties[type_id]`` value identifies
    #   the Story configured on the tracked entity;
    # * a typed action with an exact event-to-action control path in the same
    #   resolved script establishes tracked-script context, but not a bridge
    #   from the tracked slot to that event.
    #
    # Both remain context edges. Neither claims quest playback, chronology, a
    # completion callback, or a server exchange.
    native_playback_by_script: dict[tuple[str, str], list[tuple[str, dict]]] = (
        defaultdict(list)
    )
    native_property_playback_by_level_local: dict[
        tuple[str, int], list[tuple[str, dict]]
    ] = defaultdict(list)
    for raw_story_key, rows in native_non_fmv_story_playback_index.items():
        story_key = resolve_scene_ref_out_key(raw_story_key, all_story_entry_keys)
        if not story_key:
            continue
        for row in rows:
            if not row.get("nativeEventOwners"):
                continue
            pair = (
                str(row.get("levelId") or ""),
                str(row.get("scriptId") or ""),
            )
            if all(pair):
                native_playback_by_script[pair].append((story_key, row))
                # Index the exact serialized target once.  Iterating every
                # event-owned playback in a level for every tracking hint is
                # quadratic on the full corpus and can add many minutes to a
                # lean Story build.  The matcher below still repeats all
                # schema, registry-uniqueness, and global-id checks before a
                # relation is accepted.
                for owner in row.get("nativeEventOwners") or []:
                    if (
                        not isinstance(owner, dict)
                        or owner.get("status") != "exact_serialized_control_path"
                        or owner.get("headerName")
                        != "EntityEvent_OnSavePropertyChanged"
                    ):
                        continue
                    detail = owner.get("eventDetail") or {}
                    target = detail.get("targetEntity") or {}
                    target_global_logic_id = target.get("logicId")
                    if (
                        detail.get("type")
                        != "EntityEvent_OnSavePropertyChanged"
                        or not isinstance(target_global_logic_id, int)
                        or isinstance(target_global_logic_id, bool)
                        or target_global_logic_id <= 0
                    ):
                        continue
                    native_property_playback_by_level_local[
                        (pair[0], target_global_logic_id % GLOBAL_SCRIPT_ID_SCALE)
                    ].append((story_key, row))

    # Nested multi-description tracking is a real runtime tracking source, but
    # it may only create mission context when every independent typed
    # MissionRuntime reference to the resolved script agrees on one mission.
    # This union deliberately includes direct script conditions, interactive
    # registry conditions, normal tracking, and the nested runtime wrappers.
    tracking_owner_missions_by_pair: dict[tuple[str, str], set[str]] = (
        defaultdict(set)
    )
    for pair, references in script_condition_bindings.items():
        tracking_owner_missions_by_pair[pair].update(
            str(reference.get("missionId") or "")
            for reference in references
            if reference.get("missionId")
        )
    for pair, references in interactive_condition_script_bindings.items():
        tracking_owner_missions_by_pair[pair].update(
            str(reference.get("missionId") or "")
            for reference in references
            if reference.get("missionId")
        )
    for owner_mission, owner_flow in mission_flows_payload.items():
        for owner_quest in owner_flow.get("quests") or []:
            for owner_hint in owner_quest.get("tracking") or []:
                owner_resolution = resolve_entity_tracking_script(owner_hint)
                if owner_resolution.get("status") != "unique":
                    continue
                owner_pair = (
                    str(owner_resolution.get("levelId") or ""),
                    str(owner_resolution.get("scriptId") or ""),
                )
                if all(owner_pair):
                    tracking_owner_missions_by_pair[owner_pair].add(owner_mission)

    world_interactive_dialog_contexts_by_tracking: dict[tuple, list[dict]] = (
        defaultdict(list)
    )
    for context in build_entity_tracking_world_interactive_dialog_contexts(
        set(all_story_entry_keys),
        set(mission_flows_payload),
    ):
        world_interactive_dialog_contexts_by_tracking[
            (
                str(context.get("missionId") or ""),
                str(context.get("questId") or ""),
                str(context.get("levelId") or ""),
                context.get("entityLogicId"),
            )
        ].append(context)

    entity_tracking_relations = {
        "entity_tracking_interactive_story_target",
        "entity_tracking_native_playback_context",
        "entity_tracking_native_event_playback_context",
        "entity_tracking_native_property_playback_context",
        "entity_tracking_world_interactive_dialog_context",
    }
    for tracking_mission, flow_payload in mission_flows_payload.items():
        mission_runtime_source = repo_rel(MRA_DIR / f"{tracking_mission}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for hint in quest.get("tracking") or []:
                if (
                    str(hint.get("type") or "") == "EntityTrackingInfo"
                    and hint.get("trackScriptEntity") is False
                ):
                    world_dialog_contexts = (
                        world_interactive_dialog_contexts_by_tracking.get(
                            (
                                tracking_mission,
                                quest_id,
                                str(hint.get("scene") or ""),
                                hint.get("entityLogicId"),
                            )
                        )
                        or []
                    )
                    if len(world_dialog_contexts) == 1:
                        context = world_dialog_contexts[0]
                        story_key = str(context.get("storyKey") or "")
                        source_files = sorted({
                            str(context.get("missionRuntimeSourceFile") or ""),
                            str(context.get("levelDataSourceFile") or ""),
                            str(context.get("levelDataVerifiedMirrorFile") or ""),
                            str(context.get("worldEntityRegistrySourceFile") or ""),
                            str(context.get("interactiveTableSourceFile") or ""),
                            str(context.get("interactiveTableVerifiedMirrorFile") or ""),
                            str(context.get("interactiveTemplateSourceFile") or ""),
                            str(context.get("interactiveTemplateVerifiedMirrorFile") or ""),
                        } - {""})
                        quest.setdefault("storyConnections", []).append({
                            "key": story_key,
                            "kind": story_kind_by_key.get(story_key, "story"),
                            "relation": (
                                "entity_tracking_world_interactive_dialog_context"
                            ),
                            "direction": "context",
                            "phase": "tracked_entity_narrative_dialog",
                            "confidence": "native_exact_quest_context",
                            "evidenceTier": "native_direct",
                            "source": (
                                "typed MissionRuntime EntityTrackingInfo uniquely targets "
                                "one WorldEntityRegistry identity; the same-scene counted "
                                "LevelInteractiveData record co-carries the exact mission "
                                "state and Dialog Story id in componentProperties[94], "
                                "and InteractiveTable resolves the mirrored "
                                "int_narrative_common template; navigation/configuration "
                                "context only, with no ownership, quest playback, quest "
                                "completion, chronology, or server exchange claimed"
                            ),
                            "storyOwnerMission": (
                                story_owner_by_key.get(story_key) or ""
                            ),
                            "trackingMissionId": tracking_mission,
                            "candidateQuestIds": [quest_id],
                            "questTriggerStatus": (
                                "exact_tracked_world_entity_context"
                            ),
                            "ownership": False,
                            "questPlayback": False,
                            "questCompletion": False,
                            "executionSide": "client",
                            "networkRole": (
                                "local_navigation_and_dialog_configuration"
                            ),
                            "serverExchange": False,
                            "clientRequest": False,
                            "expectedClientReply": False,
                            "levelIds": [str(context.get("levelId") or "")],
                            "entityLogicIds": [
                                str(context.get("worldEntityGlobalLogicId") or "")
                            ],
                            "trackedLocalEntityLogicIds": [
                                str(context.get("entityLogicId") or "")
                            ],
                            "entityDetailIds": [
                                str(context.get("entityDetailId") or "")
                            ],
                            "entityTemplateIds": [
                                str(context.get("entityTemplateId") or "")
                            ],
                            "propertyKeys": [
                                "FX_CHANGE_MISSION_ID",
                                "TYPE",
                                "TYPE_ID",
                            ],
                            "narrativeType": context.get("narrativeType"),
                            "narrativeTypeName": str(
                                context.get("narrativeTypeName") or ""
                            ),
                            "trackingObjectiveIndex": hint.get("objectiveIndex"),
                            "trackingIndex": hint.get("trackingIndex"),
                            "sourceFiles": source_files,
                            "trackedEntityEvidence": [context],
                        })
                        preexisting_attached_story_keys_by_mission[
                            tracking_mission
                        ].add(story_key)
                    entity_targets: list[tuple[str, dict, dict]] = []
                    local_logic_id = hint.get("entityLogicId")
                    if not isinstance(local_logic_id, int) or isinstance(
                        local_logic_id, bool
                    ):
                        local_logic_id = 0
                    for story_key, playback in native_property_playback_by_level_local.get(
                        (
                            str(hint.get("scene") or ""),
                            local_logic_id,
                        ),
                        [],
                    ):
                        for match in match_entity_tracking_native_entity_event_context(
                            playback,
                            hint,
                        ):
                            entity_targets.append((story_key, playback, match))
                    target_story_keys = {
                        story_key for story_key, _playback, _match in entity_targets
                    }
                    target_logic_ids = {
                        match.get("targetGlobalLogicId")
                        for _story_key, _playback, match in entity_targets
                    }
                    if len(target_story_keys) == 1 and len(target_logic_ids) == 1:
                        story_key = next(iter(target_story_keys))
                        source_files = sorted({
                            mission_runtime_source,
                            *[
                                str(playback.get("sourceFile") or "")
                                for _key, playback, _match in entity_targets
                            ],
                            *[
                                str(match.get("registrySourceFile") or "")
                                for _key, _playback, match in entity_targets
                            ],
                        } - {""})
                        match_rows = [match for _key, _playback, match in entity_targets]
                        event_owners = [
                            match.get("eventOwner")
                            for match in match_rows
                            if match.get("eventOwner")
                        ]
                        quest.setdefault("storyConnections", []).append({
                            "key": story_key,
                            "kind": story_kind_by_key.get(story_key, "story"),
                            "relation": "entity_tracking_native_property_playback_context",
                            "direction": "context",
                            "phase": "tracking",
                            "confidence": "native_exact_tracked_entity_property_context",
                            "evidenceTier": "native_exact_context",
                            "source": (
                                "typed MissionRuntime EntityTrackingInfo targets the same "
                                "uniquely resolved entity as an exact local "
                                "SavePropertyChanged listener whose serialized control path "
                                "reaches the Story action; navigation/entity context only; "
                                "no quest gate, chronology, completion callback, or "
                                "server-return edge is claimed"
                            ),
                            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
                            "trackingMissionId": tracking_mission,
                            "candidateQuestIds": [quest_id],
                            "questTriggerStatus": (
                                "tracked_entity_property_context_not_quest_playback"
                            ),
                            "executionSide": "client",
                            "networkRole": (
                                "local_navigation_and_property_event_context"
                            ),
                            "serverExchange": False,
                            "serverEvidenceStatus": (
                                "objective_server_placeholder_payload_unavailable"
                            ),
                            "levelIds": [str(hint.get("scene") or "")],
                            "scriptIds": sorted({
                                str(playback.get("scriptId") or "")
                                for _key, playback, _match in entity_targets
                                if playback.get("scriptId")
                            }),
                            "entityLogicIds": [str(next(iter(target_logic_ids)))],
                            "trackedLocalEntityLogicIds": [
                                str(hint.get("entityLogicId") or "")
                            ],
                            "propertyKeys": sorted({
                                str(match.get("propertyKey") or "")
                                for match in match_rows
                                if match.get("propertyKey")
                            }),
                            "nativeEventNames": sorted({
                                str(owner.get("headerName") or "")
                                for owner in event_owners
                                if owner.get("headerName")
                            }),
                            "nativeControlPathCount": len(event_owners),
                            "nativeEventOwners": event_owners,
                            "objectiveConditionTypes": sorted({
                                str(condition_type)
                                for anchor in quest.get("objectiveAnchors") or []
                                for condition_type in anchor.get("conditionTypes") or []
                                if condition_type
                            }),
                            "trackingObjectiveIndex": hint.get("objectiveIndex"),
                            "trackingIndex": hint.get("trackingIndex"),
                            "sourceFiles": source_files,
                            "trackedEntityEvidence": match_rows,
                        })
                        preexisting_attached_story_keys_by_mission[
                            tracking_mission
                        ].add(story_key)
                resolution = resolve_entity_tracking_script(hint)
                if resolution.get("status") != "unique":
                    continue
                pair = (
                    str(resolution.get("levelId") or ""),
                    str(resolution.get("scriptId") or ""),
                )
                if (
                    hint.get("trackingListSource")
                    == "multiDescTrackingInfoList.actualList"
                    and tracking_owner_missions_by_pair.get(pair)
                    != {tracking_mission}
                ):
                    continue
                targets: list[tuple[str, dict, dict]] = []
                for target in extract_tracked_interactive_story_targets(resolution):
                    story_key = resolve_scene_ref_out_key(
                        str(target.get("storyKey") or ""),
                        all_story_entry_keys,
                    )
                    if story_key:
                        targets.append((story_key, target, {}))
                for story_key, playback in native_playback_by_script.get(pair) or []:
                    targets.append((story_key, {}, playback))

                for story_key, interactive, playback in targets:
                    is_interactive = bool(interactive)
                    relation = (
                        "entity_tracking_interactive_story_target"
                        if is_interactive
                        else "entity_tracking_native_playback_context"
                    )
                    event_owners = list(playback.get("nativeEventOwners") or [])
                    event_slots = sorted({
                        str(slot_id)
                        for owner in event_owners
                        for slot_id in owner.get("triggerSlotIds") or []
                    })
                    tracked_slot = str(resolution.get("entitySlotId") or "")
                    slot_bridge_status = ""
                    if playback:
                        slot_bridge_status = (
                            "same_slot_still_context_only"
                            if tracked_slot and tracked_slot in event_slots
                            else "different_event_and_tracked_slots"
                            if event_slots
                            else "event_has_no_decoded_slot_bridge"
                        )
                    connection = {
                        "key": story_key,
                        "kind": story_kind_by_key.get(story_key, "story"),
                        "relation": relation,
                        "direction": "context",
                        "phase": "tracking",
                        "confidence": (
                            "native_exact_tracked_interactive_property"
                            if is_interactive
                            else "native_exact_tracked_script_context"
                        ),
                        "evidenceTier": "native_exact_context",
                        "source": (
                            "typed MissionRuntime EntityTrackingInfo + native global-script-id "
                            "resolution + exact aligned WorldEntityRegistry script/slot entry + "
                            "exact tracked interactive type_id property; navigation target "
                            "context only, not a quest playback or completion edge"
                            if is_interactive
                            else
                            "typed MissionRuntime EntityTrackingInfo + native global-script-id "
                            "resolution + exact aligned WorldEntityRegistry script/slot entry + "
                            "typed Story action reached by an exact serialized control path in "
                            "the same LevelScript; no tracked-slot-to-event bridge is claimed"
                        ),
                        "storyOwnerMission": story_owner_by_key.get(story_key) or "",
                        "trackingMissionId": tracking_mission,
                        "candidateQuestIds": [quest_id],
                        "questTriggerStatus": (
                            "navigation_target_configured_story_not_playback"
                            if is_interactive
                            else "navigation_target_script_context_not_playback"
                        ),
                        "executionSide": "client",
                        "networkRole": "local_navigation_context",
                        "clientNavigationOnly": True,
                        "serverExchange": False,
                        "levelIds": [pair[0]],
                        "scriptIds": [pair[1]],
                        "localScriptIds": [str(resolution.get("localScriptId") or "")],
                        "entitySlotIds": [tracked_slot],
                        "entityLogicIds": [
                            str(hint.get("entityLogicId"))
                            if hint.get("entityLogicId") is not None
                            else ""
                        ],
                        "entityDetailIds": [
                            str(resolution.get("entityDetailId") or "")
                        ],
                        "registryIndices": [resolution.get("registryIndex")],
                        "registrySourceFiles": [
                            str(resolution.get("registrySourceFile") or "")
                        ],
                        "sourceFiles": sorted({
                            mission_runtime_source,
                            str(resolution.get("levelScriptSourceFile") or ""),
                            str(resolution.get("registrySourceFile") or ""),
                        } - {""}),
                        "trackingObjectiveIndex": hint.get("objectiveIndex"),
                        "trackingIndex": hint.get("trackingIndex"),
                        "trackingListSource": hint.get("trackingListSource"),
                        "multiDescriptionIndex": hint.get(
                            "multiDescriptionIndex"
                        ),
                        "actualListIndex": hint.get("actualListIndex"),
                    }
                    if is_interactive:
                        connection.update({
                            "interactivePropertyKey": interactive.get("propertyKey"),
                            "interactiveEntryOffset": interactive.get(
                                "interactiveEntryOffset"
                            ),
                            "interactivePropertyOffset": interactive.get(
                                "propertyOffset"
                            ),
                            "interactiveStoryOffset": interactive.get("storyOffset"),
                            "entityTemplateIds": [
                                str(interactive.get("entityTemplateId") or "")
                            ],
                            "entityTemplatePaths": [
                                str(interactive.get("entityTemplatePath") or "")
                            ],
                            "interactiveTableSourceFiles": sorted({
                                str(interactive.get("interactiveTableSourceFile") or ""),
                                str(
                                    interactive.get(
                                        "interactiveTableVerifiedMirrorFile"
                                    )
                                    or ""
                                ),
                            } - {""}),
                        })
                        connection["sourceFiles"] = sorted({
                            *connection.get("sourceFiles", []),
                            *connection.get("interactiveTableSourceFiles", []),
                        })
                    else:
                        connection.update({
                            "nativeAction": str(playback.get("actionName") or ""),
                            "opcode": (
                                f"{playback.get('actionCode')}/{playback.get('actionKind')}"
                            ),
                            "nativeEventOwnerStatus": playback.get(
                                "nativeEventOwnerStatus"
                            ),
                            "nativeEventNames": sorted({
                                str(owner.get("headerName") or "")
                                for owner in event_owners
                                if owner.get("headerName")
                            }),
                            "triggerSlotIds": event_slots,
                            "trackedSlotBridgeStatus": slot_bridge_status,
                            "nativeControlPathCount": len(event_owners),
                            "nativeEventOwners": event_owners,
                        })
                    connections = quest.setdefault("storyConnections", [])
                    signature = (
                        story_key,
                        relation,
                        pair[0],
                        pair[1],
                        tracked_slot,
                    )
                    if any((
                        str(existing.get("key") or ""),
                        str(existing.get("relation") or ""),
                        str((existing.get("levelIds") or [""])[0]),
                        str((existing.get("scriptIds") or [""])[0]),
                        str((existing.get("entitySlotIds") or [""])[0]),
                    ) == signature for existing in connections if isinstance(existing, dict)):
                        continue
                    connections.append(connection)

                for native_event in build_entity_tracking_native_event_story_context(
                    resolution,
                    native_non_fmv_story_playback_index,
                ):
                    story_key = resolve_scene_ref_out_key(
                        str(native_event.get("storyKey") or ""),
                        all_story_entry_keys,
                    )
                    if not story_key:
                        continue
                    relation = "entity_tracking_native_event_playback_context"
                    producer_script = str(
                        native_event.get("producerScriptId") or ""
                    )
                    tracked_slot = str(
                        native_event.get("trackedEntitySlotId") or ""
                    )
                    connections = quest.setdefault("storyConnections", [])
                    signature = (
                        story_key,
                        relation,
                        producer_script,
                        tracked_slot,
                        str(native_event.get("raisedEventKey") or ""),
                    )
                    if any((
                        str(existing.get("key") or ""),
                        str(existing.get("relation") or ""),
                        str((existing.get("producerScriptIds") or [""])[0]),
                        str((existing.get("entitySlotIds") or [""])[0]),
                        str(existing.get("raisedEventKey") or ""),
                    ) == signature for existing in connections if isinstance(existing, dict)):
                        continue
                    source_files = sorted({
                        mission_runtime_source,
                        str(resolution.get("registrySourceFile") or ""),
                        str(native_event.get("producerSourceFile") or ""),
                        *[
                            str(value or "")
                            for value in native_event.get("listenerSourceFiles") or []
                        ],
                    } - {""})
                    connections.append({
                        "key": story_key,
                        "kind": story_kind_by_key.get(story_key, "story"),
                        "relation": relation,
                        "direction": "context",
                        "phase": "tracking_native_event",
                        "confidence": "native_exact_tracked_entity_event_playback_context",
                        "evidenceTier": "native_exact_context",
                        "source": (
                            "typed MissionRuntime EntityTrackingInfo + exact registry "
                            "script/slot + TravelPoleBegin entity output compared to that "
                            "same ScriptEntityPtr slot + typed IfElse true branch + "
                            "RaiseCustomLevelEvent + unique same-level custom-event Story "
                            "listener; playback context only because the objective uses an "
                            "opaque server placeholder"
                        ),
                        "storyOwnerMission": story_owner_by_key.get(story_key) or "",
                        "trackingMissionId": tracking_mission,
                        "candidateQuestIds": [quest_id],
                        "questTriggerStatus": (
                            "exact_tracked_entity_event_playback_context_opaque_objective_completion"
                        ),
                        "executionSide": "client",
                        "networkRole": "local_tracked_entity_event_context",
                        "serverExchange": False,
                        "serverEvidenceStatus": "objective_server_placeholder_payload_unavailable",
                        "levelIds": [str(native_event.get("levelId") or "")],
                        "producerScriptIds": [producer_script],
                        "listenerScriptIds": list(
                            native_event.get("listenerScriptIds") or []
                        ),
                        "entitySlotIds": [tracked_slot],
                        "entityLogicIds": [str(hint.get("entityLogicId") or 0)],
                        "entityDetailIds": [
                            str(resolution.get("entityDetailId") or "")
                        ],
                        "registryIndices": [resolution.get("registryIndex")],
                        "trackedSlotBridgeStatus": "exact_entity_compare_event_bridge",
                        "producerEventName": str(
                            native_event.get("producerHeaderName") or ""
                        ),
                        "producerHeaderLocalId": native_event.get(
                            "producerHeaderLocalId"
                        ),
                        "raiseActionLocalId": native_event.get(
                            "raiseActionLocalId"
                        ),
                        "raisedEventKey": str(
                            native_event.get("raisedEventKey") or ""
                        ),
                        "entityCompareBridge": native_event.get(
                            "entityCompareBridge"
                        ),
                        "producerControlPath": native_event.get(
                            "producerControlPath"
                        ),
                        "listenerEventOwners": native_event.get(
                            "listenerEventOwners"
                        ) or [],
                        "objectiveConditionTypes": sorted({
                            str(condition_type)
                            for anchor in quest.get("objectiveAnchors") or []
                            for condition_type in anchor.get("conditionTypes") or []
                            if condition_type
                        }),
                        "sourceFiles": source_files,
                    })
                    preexisting_attached_story_keys_by_mission[
                        tracking_mission
                    ].add(story_key)

    # MissionArea ids are level-scoped in the native table.  When the exact
    # level-specific MissionArea shape is byte-for-byte equivalent (within
    # JSON/f32 round-trip precision) to the Leader trigger-volume slot whose
    # serialized event/control path reaches a Story action, retain that shared
    # trigger geometry as quest context.  This is deliberately not promoted to
    # a quest-state gate or server-return edge: entering the volume is a local
    # playback trigger, while MissionRuntime merely configures the same area as
    # the quest's navigation/objective target.
    native_leader_playback_by_level: dict[
        str,
        list[tuple[str, dict]],
    ] = defaultdict(list)
    for raw_story_key, rows in (
        list(native_non_fmv_story_playback_index.items())
        + list(native_black_action_index.items())
    ):
        story_key = resolve_scene_ref_out_key(raw_story_key, all_story_entry_keys)
        if not story_key:
            continue
        for occurrence in rows:
            event_owners = occurrence.get("nativeEventOwners") or []
            if not any(
                isinstance(owner, dict)
                and owner.get("status") == "exact_serialized_control_path"
                and owner.get("headerName")
                == "ScriptEvent_OnLeaderEnterTriggerVolume"
                for owner in event_owners
            ):
                continue
            level_id = str(occurrence.get("levelId") or "")
            if level_id:
                native_leader_playback_by_level[level_id].append(
                    (story_key, occurrence)
                )

    for tracking_mission, flow_payload in mission_flows_payload.items():
        mission_runtime_source = repo_rel(MRA_DIR / f"{tracking_mission}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            connections = quest.setdefault("storyConnections", [])
            existing_story_keys = {
                str(row.get("key") or "")
                for row in connections
                if isinstance(row, dict) and row.get("key")
            }
            for tracking in quest.get("tracking") or []:
                if not isinstance(tracking, dict):
                    continue
                level_id = str(tracking.get("scene") or "")
                if not level_id:
                    continue
                for story_key, occurrence in (
                    native_leader_playback_by_level.get(level_id) or []
                ):
                    if story_key in existing_story_keys:
                        continue
                    matches = match_mission_area_leader_trigger_context(
                        occurrence,
                        tracking,
                    )
                    if len(matches) != 1:
                        continue
                    match = matches[0]
                    connection = {
                        "key": story_key,
                        "kind": story_kind_by_key.get(story_key, "story"),
                        "relation": "mission_area_trigger_volume_story_context",
                        "direction": "context",
                        "phase": "tracking",
                        "confidence": "native_exact_area_trigger_geometry_context",
                        "evidenceTier": "native_exact_context",
                        "source": (
                            "typed MissionRuntime MissionAreaTrackingInfo + exact "
                            "LevelBasicInfoTable.idNum-selected MissionAreaTable row + "
                            "identical current-build Leader trigger-volume geometry on "
                            "the exact serialized event-to-Story control path; shared "
                            "trigger context only, not a quest-state playback gate"
                        ),
                        "storyOwnerMission": story_owner_by_key.get(story_key) or "",
                        "trackingMissionId": tracking_mission,
                        "candidateQuestIds": [quest_id],
                        "questTriggerStatus": (
                            "same_authored_trigger_geometry_context_not_quest_gate"
                        ),
                        "executionSide": "client",
                        "networkRole": "local_trigger_context",
                        "serverExchange": False,
                        "levelIds": [str(match.get("levelId") or "")],
                        "levelNums": [str(match.get("levelNum") or "")],
                        "scriptIds": [str(match.get("scriptId") or "")],
                        "triggerSlotIds": [str(match.get("triggerSlotId") or "")],
                        "triggerVolumeType": str(
                            match.get("triggerVolumeType") or ""
                        ),
                        "triggerVolumeOffset": match.get("triggerVolumeOffset"),
                        "triggerShapeOffset": match.get("triggerShapeOffset"),
                        "triggerShape": match.get("triggerShape"),
                        "missionAreaIds": [
                            str(match.get("missionAreaId") or "")
                        ],
                        "missionAreaShape": match.get("missionAreaShape"),
                        "subDataParentIds": [
                            str(match.get("subDataParentId") or "")
                        ],
                        "sourceFiles": sorted({
                            mission_runtime_source,
                            str(match.get("sourceFile") or ""),
                            str(match.get("missionAreaSourceFile") or ""),
                            str(match.get("levelBasicInfoSourceFile") or ""),
                        } - {""}),
                        "trackingObjectiveIndex": tracking.get("objectiveIndex"),
                        "trackingIndex": tracking.get("trackingIndex"),
                        "nativeEventOwners": match.get("nativeEventOwners") or [],
                    }
                    signature = (
                        story_key,
                        connection["relation"],
                        connection["scriptIds"][0],
                        connection["triggerSlotIds"][0],
                        connection["missionAreaIds"][0],
                    )
                    if any((
                        str(existing.get("key") or ""),
                        str(existing.get("relation") or ""),
                        str((existing.get("scriptIds") or [""])[0]),
                        str((existing.get("triggerSlotIds") or [""])[0]),
                        str((existing.get("missionAreaIds") or [""])[0]),
                    ) == signature for existing in connections if isinstance(existing, dict)):
                        continue
                    connections.append(connection)
                    existing_story_keys.add(story_key)
                    preexisting_attached_story_keys_by_mission[
                        tracking_mission
                    ].add(story_key)

    # PosTrackingInfo is weaker than MissionAreaTrackingInfo because it has no
    # shape dimensions.  Still, an exact scene + event-selected trigger slot +
    # trigger-shape-center match is useful mission context. Collect every
    # current MissionRuntime candidate first and promote only when all matches
    # for a Story key agree on one mission. This prevents popular coordinates
    # or shared trigger assets from fanning out ownership.
    pos_trigger_candidates: dict[str, list[dict]] = defaultdict(list)
    for tracking_mission, flow_payload in mission_flows_payload.items():
        mission_runtime_source = repo_rel(MRA_DIR / f"{tracking_mission}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for tracking in quest.get("tracking") or []:
                if (
                    not isinstance(tracking, dict)
                    or tracking.get("type") != "PosTrackingInfo"
                    or tracking.get("sourceType") != "trackingPos"
                ):
                    continue
                level_id = str(tracking.get("scene") or "")
                for story_key, occurrence in (
                    native_leader_playback_by_level.get(level_id) or []
                ):
                    matches = match_pos_tracking_leader_trigger_context(
                        occurrence,
                        tracking,
                    )
                    if len(matches) != 1:
                        continue
                    pos_trigger_candidates[story_key].append({
                        "missionId": tracking_mission,
                        "questId": quest_id,
                        "missionRuntimeSource": mission_runtime_source,
                        "tracking": tracking,
                        "occurrence": occurrence,
                        "match": matches[0],
                    })

    for story_key, candidates in sorted(pos_trigger_candidates.items()):
        candidate_missions = {
            str(row.get("missionId") or "") for row in candidates
        }
        candidate_missions.discard("")
        if len(candidate_missions) != 1:
            continue
        target_mission = next(iter(candidate_missions))
        flow_payload = mission_flows_payload.get(target_mission)
        if (
            flow_payload is None
            or story_key
            in preexisting_attached_story_keys_by_mission[target_mission]
        ):
            continue
        occurrences = [row["occurrence"] for row in candidates]
        matches = [row["match"] for row in candidates]
        owners = [
            owner
            for match in matches
            for owner in match.get("nativeEventOwners") or []
        ]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "pos_tracking_trigger_center_story_context",
            "direction": "context",
            "phase": "tracking",
            "confidence": "native_exact_unique_mission_trigger_center_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "typed MissionRuntime PosTrackingInfo + identical scene and "
                "position to one current-build Leader trigger-volume shape "
                "selected by the exact serialized trigger-slot event-to-Story "
                "control path; all original-data candidates agree on one "
                "mission, but this is navigation/playback context rather than "
                "a quest-state gate"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "trackingMissionId": target_mission,
            "candidateQuestIds": sorted({
                str(row.get("questId") or "")
                for row in candidates
                if row.get("questId")
            }),
            "questTriggerStatus": (
                "same_authored_trigger_center_context_not_quest_gate"
            ),
            "executionSide": "client",
            "networkRole": "local_trigger_context",
            "serverExchange": False,
            "serverEvidenceStatus": "local_trigger_no_server_payload",
            "levelIds": sorted({
                str(match.get("levelId") or "") for match in matches
            } - {""}),
            "scriptIds": sorted({
                str(match.get("scriptId") or "") for match in matches
            } - {""}),
            "triggerSlotIds": sorted({
                str(match.get("triggerSlotId") or "") for match in matches
            } - {""}),
            "triggerVolumeType": "Leader",
            "triggerShapes": [match.get("triggerShape") for match in matches],
            "trackingPositions": [
                match.get("trackingPosition") for match in matches
            ],
            "nativeActions": sorted({
                str(row.get("actionName") or "")
                for row in occurrences
                if row.get("actionName")
            }),
            "nativeEventNames": sorted({
                str(owner.get("headerName") or "")
                for owner in owners
                if owner.get("headerName")
            }),
            "nativeEventOwners": owners,
            "sourceFiles": sorted({
                *[
                    str(row.get("missionRuntimeSource") or "")
                    for row in candidates
                ],
                *[str(match.get("sourceFile") or "") for match in matches],
            } - {""}),
            "trackingRows": [
                {
                    "questId": row.get("questId"),
                    "objectiveIndex": row["tracking"].get("objectiveIndex"),
                    "trackingIndex": row["tracking"].get("trackingIndex"),
                    "position": row["tracking"].get("position"),
                }
                for row in candidates
            ],
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # Two additional native event consumers can scope playback to a mission
    # shell without selecting a quest:
    #
    # * MissionEvent_OnClientGlobalVarChanged carries one exact variable key;
    #   require that key to occur in CheckClientGlobalVar objectives from one
    #   MissionRuntime only. Multiple quests may observe the same key.
    # * WaitForNpcProxyReady on the exact event-to-playback path carries one or
    #   more proxy ids; require every MissionRuntime-tracked match on that path
    #   to agree on one mission. Untracked readiness waits do not add owners.
    #
    # Both are local playback context. Neither recovers a server payload,
    # response, quest-state transition, or unique quest trigger.
    client_global_var_consumers: dict[str, list[dict]] = defaultdict(list)
    npc_tracking_consumers: dict[str, list[dict]] = defaultdict(list)
    for consumer_mission, flow_payload in mission_flows_payload.items():
        mission_runtime_source = repo_rel(MRA_DIR / f"{consumer_mission}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            for anchor in quest.get("objectiveAnchors") or []:
                if not isinstance(anchor, dict):
                    continue
                for leaf in anchor.get("conditionLeaves") or []:
                    if not isinstance(leaf, dict) or leaf.get("type") != "CheckClientGlobalVar":
                        continue
                    for key in leaf.get("keys") or []:
                        key_text = str(key or "").strip()
                        if key_text:
                            client_global_var_consumers[key_text].append({
                                "missionId": consumer_mission,
                                "questId": quest_id,
                                "objectiveIndex": anchor.get("index"),
                                "sourceFile": mission_runtime_source,
                            })
            for tracking in quest.get("tracking") or []:
                if not isinstance(tracking, dict) or tracking.get("type") != "NpcProxyTrackingInfo":
                    continue
                proxy_id = str(tracking.get("npcProxyId") or "").strip()
                if proxy_id:
                    npc_tracking_consumers[proxy_id].append({
                        "type": str(tracking.get("type") or ""),
                        "missionId": consumer_mission,
                        "questId": quest_id,
                        "scene": str(tracking.get("scene") or ""),
                        "objectiveIndex": tracking.get("objectiveIndex"),
                        "trackingIndex": tracking.get("trackingIndex"),
                        "useFilterCondition": tracking.get(
                            "useFilterCondition"
                        ),
                        "trackingVisibilityFilter": copy.deepcopy(
                            tracking.get("trackingVisibilityFilter")
                        ),
                        "sourceFile": mission_runtime_source,
                    })

    npc_proxy_lazy_destroy_contexts = (
        build_npc_proxy_lazy_destroy_dialog_contexts(
            npc_tracking_consumers,
            npc_proxy_rows,
            set(all_story_entry_keys),
        )
    )
    for context in npc_proxy_lazy_destroy_contexts:
        target_mission = str(context.get("missionId") or "")
        quest_id = str(context.get("questId") or "")
        story_key = str(context.get("storyKey") or "")
        quest_target = quest_targets.get(quest_id)
        if (
            not target_mission
            or not story_key
            or not quest_target
            or str(quest_target[0] or "") != target_mission
            or not isinstance(quest_target[1], dict)
        ):
            continue
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "npc_proxy_lazy_destroy_dialog_context",
            "direction": "context",
            "phase": "server_proxy_deactivation",
            "confidence": "native_exact_quest_navigation_context",
            "evidenceTier": "derived_exact_quest",
            "source": (
                "one typed same-scene MissionRuntime NpcProxyTrackingInfo + "
                "exact NpcProxyTable lazyDestroy=true and "
                "lazyDestroyOverrideDialogId + installed "
                "NpcProxy.OnDeActive -> NpcProxyMgr.ApplyLazyDestroyData -> "
                "NpcManager.AddOverrideInteractDialogId native call chain"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "npcProxyId": context.get("npcProxyId"),
            "levelIds": [context.get("levelId")],
            "dialogId": context.get("dialogId"),
            "questTriggerStatus": (
                "tracked_proxy_navigation_and_dialog_configuration_context_"
                "not_quest_deactivation_or_playback"
            ),
            "storyBinding": True,
            "ownership": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "executionSide": "client",
            "networkRole": (
                "server_proxy_state_then_local_lazy_destroy_dialog_override"
            ),
            "serverExchange": True,
            "clientRequest": False,
            "expectedClientReply": False,
            "upstreamServerStateSources": [
                "SC_NPC_ENTER_MAP_RESYNC",
                "SC_NPC_ACTIVE_CHANGE_NTF",
            ],
            "serverFields": ["proxyNumId", "metaKvs", "activeCondIndex"],
            "serverEvidenceStatus": (
                "server state identifies the proxy and active condition, not "
                "the mission, quest, or dialog; the exact authored proxy row "
                "supplies the local override dialog"
            ),
            "sourceFiles": sorted({
                str((context.get("trackingConsumer") or {}).get("sourceFile") or ""),
                repo_rel(NPC_PROXY_TABLE_PATH),
            } - {""}),
            "npcProxyTableRow": context.get("npcProxyTableRow"),
            "nativeConsumers": [{
                "method": "NpcProxyTrackingInfo.GetTargetPos",
                "token": "0x06004ca6",
                "address": "0x18384f850",
            }, {
                "method": "NpcProxy.OnDeActive",
                "token": "0x060131f3",
                "address": "0x187069e7c",
            }, {
                "method": "NpcProxyMgr.ApplyLazyDestroyData",
                "token": "0x0601324f",
                "address": "0x187065af4",
            }, {
                "method": "NpcManager.AddOverrideInteractDialogId",
                "token": "0x060131cf",
                "address": "0x18705f854",
            }],
            "nativeMappingId": (
                "npc-proxy-lazy-destroy-dialog-context-native-v1"
            ),
        }
        quest = quest_target[1]
        connections = quest.setdefault("storyConnections", [])
        signature = (
            story_key,
            connection["relation"],
            str(connection.get("npcProxyId") or ""),
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("npcProxyId") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    world_entity_registry_path = (
        GAMEPLAY_CONFIG_DIR / "WorldEntityRegistry.json"
    )
    world_entity_registry = (
        load_json_path(
            world_entity_registry_path,
            "WorldEntityRegistry.json",
        )
        if world_entity_registry_path.is_file()
        else {}
    )
    npc_proxy_dialog_navigation_contexts = (
        build_npc_proxy_tracking_dialog_navigation_contexts(
            npc_tracking_consumers,
            npc_proxy_rows,
            npc_proxy_ex,
            world_entity_registry,
            dialog_id_registry,
            dialog_tree_story_playback_groups,
        )
    )
    for context in npc_proxy_dialog_navigation_contexts:
        target_mission = str(context.get("missionId") or "")
        quest_id = str(context.get("questId") or "")
        quest_target = quest_targets.get(quest_id)
        if (
            not quest_target
            or str(quest_target[0] or "") != target_mission
        ):
            continue
        quest = quest_target[1]
        parent_story_key = str(context.get("parentStoryKey") or "")
        if not isinstance(quest, dict) or not parent_story_key:
            continue
        connection = {
            "key": parent_story_key,
            "kind": story_kind_by_key.get(parent_story_key, "dialog"),
            "relation": "npc_proxy_tracking_dialog_navigation_context",
            "direction": "context",
            "phase": "tracking",
            "confidence": "native_exact_quest_navigation_context",
            "evidenceTier": "derived_exact_quest",
            "source": (
                "one typed same-scene MissionRuntime NpcProxyTrackingInfo + "
                "exact NpcProxyTable/WorldEntityRegistry identity + one "
                "missionless NpcProxyEx dialog + registered parent DialogTree "
                "with a typed next-dialog carrier"
            ),
            "storyOwnerMission": (
                story_owner_by_key.get(parent_story_key) or ""
            ),
            "npcProxyId": context.get("npcProxyId"),
            "levelIds": [context.get("levelId")],
            "childStoryKeys": list(context.get("childStoryKeys") or []),
            "trackingVisibilityFilter": context.get(
                "trackingVisibilityFilter"
            ),
            "trackingVisibilityRole": (
                "navigation_marker_visibility_only_not_dialog_activation"
            ),
            "questTriggerStatus": (
                "tracked_proxy_navigation_context_not_quest_playback"
            ),
            "storyBinding": True,
            "ownership": False,
            "questPlayback": False,
            "questCompletion": False,
            "possibleAuthoredRoute": True,
            "executionSide": "client",
            "networkRole": "local_tracked_npc_navigation_context",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "serverEvidenceStatus": (
                "NpcProxyTrackingInfo reads AOI position only; an independent "
                "server push selects activeCondIndex and carries no mission, "
                "quest, or dialog id"
            ),
            "sourceFiles": sorted({
                str((context.get("trackingConsumer") or {}).get("sourceFile") or ""),
                repo_rel(NPC_PROXY_TABLE_PATH),
                repo_rel(NPC_PROXY_EX_PATH),
                repo_rel(world_entity_registry_path),
                *[
                    str(occurrence.get("sourceFile") or "")
                    for route in context.get("dialogTreeChildRoutes") or []
                    for occurrence in route.get("occurrences") or []
                    if isinstance(occurrence, dict)
                ],
            } - {""}),
            "npcProxyTableRow": context.get("npcProxyTableRow"),
            "npcProxyRegistryRow": context.get("npcProxyRegistryRow"),
            "npcProxyExRows": context.get("npcProxyExRows"),
            "dialogTreeChildRoutes": context.get("dialogTreeChildRoutes"),
            "nativeConsumers": [{
                "method": "NpcProxyTrackingInfo.GetTargetPos",
                "token": "0x06004ca6",
                "address": "0x18384f850",
            }, {
                "method": "NpcInteractComponent._TryGetNpcProxyInteractDialogId",
                "token": "0x06011381",
                "address": "0x183564080",
            }, {
                "method": "DialogTreeDialogNode.DoExecute",
                "token": "0x06003b6e",
                "address": "0x1872a3770",
            }],
            "nativeMappingId": (
                "npc-proxy-tracking-dialog-navigation-context-native-v1"
            ),
        }
        connections = quest.setdefault("storyConnections", [])
        signature = (
            parent_story_key,
            connection["relation"],
            str(connection.get("npcProxyId") or ""),
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("npcProxyId") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(
            parent_story_key
        )

    mission_event_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    npc_wait_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    npc_target_groups: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for raw_story_key, occurrences in (
        list(native_non_fmv_story_playback_index.items())
        + list(native_black_action_index.items())
    ):
        story_key = resolve_scene_ref_out_key(raw_story_key, all_story_entry_keys)
        if not story_key:
            continue
        for occurrence in occurrences:
            npc_target = match_play3d_npc_tracking_context(
                story_key,
                occurrence,
                npc_tracking_consumers,
            )
            if npc_target:
                target_mission = str(npc_target.get("missionId") or "")
                proxy_id = str(npc_target.get("npcProxyId") or "")
                npc_target_groups[(
                    story_key,
                    target_mission,
                    proxy_id,
                )].append({
                    "occurrence": occurrence,
                    "consumers": list(npc_target.get("consumers") or []),
                })
            for owner in occurrence.get("nativeEventOwners") or []:
                if not isinstance(owner, dict):
                    continue
                if owner.get("headerName") == "MissionEvent_OnClientGlobalVarChanged":
                    literals = [
                        str(value)
                        for value in owner.get("headerTexts") or []
                        if value and not str(value).startswith("$")
                    ]
                    if len(literals) != 1:
                        continue
                    variable_key = literals[0]
                    consumers = client_global_var_consumers.get(variable_key) or []
                    missions = {str(row.get("missionId") or "") for row in consumers}
                    missions.discard("")
                    if len(missions) == 1:
                        mission_event_groups[(
                            story_key,
                            next(iter(missions)),
                            variable_key,
                        )].append({
                            "occurrence": occurrence,
                            "owner": owner,
                            "consumers": consumers,
                        })

                tracked_waits: list[tuple[str, list[dict]]] = []
                for step in owner.get("path") or []:
                    if not isinstance(step, dict) or step.get("actionName") != "WaitForNpcProxyReady":
                        continue
                    for value in step.get("texts") or []:
                        proxy_id = str(value or "").strip()
                        consumers = npc_tracking_consumers.get(proxy_id) or []
                        if consumers:
                            tracked_waits.append((proxy_id, consumers))
                wait_missions = {
                    str(row.get("missionId") or "")
                    for _proxy_id, consumers in tracked_waits
                    for row in consumers
                    if row.get("missionId")
                }
                if tracked_waits and len(wait_missions) == 1:
                    target_mission = next(iter(wait_missions))
                    for proxy_id, consumers in tracked_waits:
                        npc_wait_groups[(story_key, target_mission, proxy_id)].append({
                            "occurrence": occurrence,
                            "owner": owner,
                            "consumers": consumers,
                        })

    for (story_key, target_mission, variable_key), evidence_rows in sorted(
        mission_event_groups.items()
    ):
        flow_payload = mission_flows_payload.get(target_mission)
        if flow_payload is None:
            continue
        consumers = [
            row
            for evidence in evidence_rows
            for row in evidence.get("consumers") or []
        ]
        occurrences = [row["occurrence"] for row in evidence_rows]
        owners = [row["owner"] for row in evidence_rows]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "mission_global_var_native_playback_context",
            "direction": "context",
            "phase": "mission_event",
            "confidence": "native_exact_unique_mission_global_var_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "exact MissionEvent_OnClientGlobalVarChanged key on a serialized "
                "event-to-Story control path + the same CheckClientGlobalVar key "
                "used by one MissionRuntime only; mission shell context, not a "
                "unique quest trigger or decoded server exchange"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "missionGlobalVarKey": variable_key,
            "candidateQuestIds": sorted({
                str(row.get("questId") or "") for row in consumers if row.get("questId")
            }),
            "questTriggerStatus": "shared_client_global_var_mission_context_not_quest_trigger",
            "executionSide": "client",
            "networkRole": "local_mission_event_context",
            "serverExchange": False,
            "serverEvidenceStatus": "no_request_or_response_payload_decoded",
            "levelIds": sorted({str(row.get("levelId") or "") for row in occurrences if row.get("levelId")}),
            "scriptIds": sorted({str(row.get("scriptId") or "") for row in occurrences if row.get("scriptId")}),
            "nativeActions": sorted({str(row.get("actionName") or "") for row in occurrences if row.get("actionName")}),
            "nativeEventNames": ["MissionEvent_OnClientGlobalVarChanged"],
            "nativeControlPathStatuses": sorted({str(row.get("status") or "") for row in owners if row.get("status")}),
            "nativeEventOwners": owners,
            "sourceFiles": sorted({
                *[str(row.get("sourceFile") or "") for row in occurrences],
                *[str(row.get("sourceFile") or "") for row in consumers],
            } - {""}),
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    for (story_key, target_mission, proxy_id), evidence_rows in sorted(
        npc_wait_groups.items()
    ):
        flow_payload = mission_flows_payload.get(target_mission)
        if flow_payload is None:
            continue
        consumers = [
            row
            for evidence in evidence_rows
            for row in evidence.get("consumers") or []
        ]
        occurrences = [row["occurrence"] for row in evidence_rows]
        owners = [row["owner"] for row in evidence_rows]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "npc_proxy_wait_native_playback_context",
            "direction": "context",
            "phase": "npc_ready",
            "confidence": "native_exact_unique_mission_npc_wait_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "typed WaitForNpcProxyReady on the exact serialized event-to-Story "
                "control path + the same NpcProxyTrackingInfo id used by one "
                "MissionRuntime only; mission shell context, not a unique quest "
                "trigger or decoded server exchange"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "npcProxyId": proxy_id,
            "candidateQuestIds": sorted({
                str(row.get("questId") or "") for row in consumers if row.get("questId")
            }),
            "questTriggerStatus": "shared_tracked_npc_readiness_context_not_quest_trigger",
            "executionSide": "client",
            "networkRole": "local_npc_ready_context",
            "serverExchange": False,
            "serverEvidenceStatus": "no_request_or_response_payload_decoded",
            "levelIds": sorted({str(row.get("levelId") or "") for row in occurrences if row.get("levelId")}),
            "scriptIds": sorted({str(row.get("scriptId") or "") for row in occurrences if row.get("scriptId")}),
            "nativeActions": sorted({str(row.get("actionName") or "") for row in occurrences if row.get("actionName")}),
            "nativeEventNames": sorted({str(row.get("headerName") or "") for row in owners if row.get("headerName")}),
            "nativeControlPathStatuses": sorted({str(row.get("status") or "") for row in owners if row.get("status")}),
            "nativeEventOwners": owners,
            "sourceFiles": sorted({
                *[str(row.get("sourceFile") or "") for row in occurrences],
                *[str(row.get("sourceFile") or "") for row in consumers],
            } - {""}),
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    for (story_key, target_mission, proxy_id), evidence_rows in sorted(
        npc_target_groups.items()
    ):
        flow_payload = mission_flows_payload.get(target_mission)
        if flow_payload is None:
            continue
        consumers = [
            row
            for evidence in evidence_rows
            for row in evidence.get("consumers") or []
        ]
        occurrences = [row["occurrence"] for row in evidence_rows]
        owners = [
            owner
            for occurrence in occurrences
            for owner in occurrence.get("nativeEventOwners") or []
            if isinstance(owner, dict)
        ]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "npc_proxy_target_native_playback_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_unique_mission_npc_playback_target",
            "evidenceTier": "native_exact_context",
            "source": (
                "exact current-build Play3DRadio 12-field payload with "
                "radioId equal to this Story key, useNpcProxy=true, and one "
                "npcProxyId + the same typed NpcProxyTrackingInfo id and scene "
                "used by one MissionRuntime only; mission playback-target "
                "context, not a quest trigger or decoded server exchange"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "npcProxyId": proxy_id,
            "candidateQuestIds": sorted({
                str(row.get("questId") or "")
                for row in consumers
                if row.get("questId")
            }),
            "questTriggerStatus": (
                "same_tracked_npc_is_play3d_emitter_not_quest_trigger"
            ),
            "executionSide": "client",
            "networkRole": "local_npc_playback_target_context",
            "serverExchange": False,
            "serverEvidenceStatus": "local_playback_target_no_server_payload",
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in occurrences
                if row.get("scriptId")
            }),
            "nativeActions": ["Play3DRadio"],
            "nativeEventNames": sorted({
                str(row.get("headerName") or "")
                for row in owners
                if row.get("headerName")
            }),
            "nativeControlPathStatuses": sorted({
                str(row.get("status") or "")
                for row in owners
                if row.get("status")
            }),
            "nativeEventOwners": owners,
            "play3DRadioPayloads": [
                row.get("play3DRadio")
                for row in occurrences
                if row.get("play3DRadio")
            ],
            "sourceFiles": sorted({
                *[str(row.get("sourceFile") or "") for row in occurrences],
                *[str(row.get("sourceFile") or "") for row in consumers],
            } - {""}),
        }
        connections = flow_payload.setdefault("missionStoryConnections", [])
        signature = (story_key, connection["relation"], proxy_id)
        if any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("npcProxyId") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            continue
        connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    native_script_pairs = {
        (
            str(row.get("levelId") or ""),
            str(row.get("scriptId") or ""),
        )
        for rows in native_story_playback_index.values()
        for row in rows
        if row.get("levelId") and row.get("scriptId")
    }
    native_script_pairs.update({
        (
            str(row.get("levelId") or ""),
            str(row.get("scriptId") or ""),
        )
        for rows in native_black_action_index.values()
        for row in rows
        if row.get("levelId") and row.get("scriptId")
    })
    radio_trigger_zone_contexts = (
        build_level_function_area_radio_trigger_story_contexts(
            set(all_story_entry_keys),
            mission_runtime_id_set,
        )
    )
    for context in radio_trigger_zone_contexts:
        route_story_key = resolve_scene_ref_out_key(
            str(context.get("radioId") or ""),
            all_story_entry_keys,
        )
        if not route_story_key:
            continue
        for target_mission in context.get("missionStateIds") or []:
            target_mission = str(target_mission or "")
            if target_mission not in mission_runtime_id_set:
                continue
            gate_roles = list(
                (context.get("missionStateRolesById") or {}).get(target_mission)
                or []
            )
            dependency = {
                "key": route_story_key,
                "kind": story_kind_by_key.get(route_story_key, "radio"),
                "relation": "radio_trigger_zone_mission_state_dependency",
                "direction": "dependency",
                "phase": "mission_state_trigger_zone",
                "confidence": "native_exact_level_function_area_radio_trigger",
                "source": (
                    "one exact installed-build LevelData RadioTriggerZoneData "
                    "row co-carries this radioId and the named mission-state "
                    "field; native OnEnter evaluates those fields before "
                    "calling GameAction.PlayRadio"
                ),
                "storyOwnerMission": story_owner_by_key.get(route_story_key) or "",
                "missionStateId": target_mission,
                "missionStateGateRoles": gate_roles,
                "missionStateGatePredicates": [
                    f"RadioTriggerZoneData.{role} = {target_mission}"
                    for role in gate_roles
                ],
                "questTriggerStatus": (
                    "exact_level_function_area_radio_trigger_state_context_"
                    "without_quest_identity"
                ),
                "storyBinding": False,
                "ownership": False,
                "dependencyOnly": True,
                "executionSide": "client",
                "networkRole": "reads_synchronized_local_mission_state",
                "serverExchange": False,
                "clientRequest": False,
                "expectedClientReply": False,
                "upstreamServerStateSources": [
                    "SC_SYNC_ALL_MISSION",
                    "SC_MISSION_STATE_UPDATE",
                ],
                "upstreamServerStateRole": (
                    "independent server pushes populate the local MissionSystem "
                    "cache; entering this zone sends no mission-state request"
                ),
                "serverEvidenceStatus": (
                    "RadioTriggerZoneHandler.OnEnter reads the local mission "
                    "cache and calls GameAction.PlayRadio; no direct request "
                    "or reply belongs to this playback"
                ),
                "nativeMappingId": (
                    "level-function-area-radio-trigger-zone-tag-9-v1d4"
                ),
                "nativeConsumer": context.get("nativeConsumer"),
                "levelIds": [str(context.get("levelId") or "")],
                "sourceFiles": [str(context.get("sourceFile") or "")],
                "sourcePath": context.get("sourcePath"),
                "recordOffset": context.get("recordOffset"),
                "recordEndOffset": context.get("recordEndOffset"),
                "unionTag": context.get("unionTag"),
                "serializedMemberCount": context.get("serializedMemberCount"),
                "specificDataListCount": context.get("specificDataListCount"),
                "radioTriggerId": context.get("triggerId"),
                "useRadioTriggerOnce": context.get("useRadioTriggerOnce"),
                "prtsId": context.get("prtsId"),
                "missionStateRolesById": context.get("missionStateRolesById"),
            }
            dependencies = mission_flows_payload[target_mission].setdefault(
                "missionStateStoryDependencies",
                [],
            )
            dependency_signature = (
                route_story_key,
                dependency["relation"],
                target_mission,
                str(dependency.get("radioTriggerId") or ""),
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
                str(existing.get("radioTriggerId") or ""),
            ) == dependency_signature for existing in dependencies if isinstance(existing, dict)):
                dependencies.append(dependency)

            connection = {
                **dependency,
                "relation": "radio_trigger_zone_mission_state_playback_context",
                "direction": "context",
                "confidence": "native_exact_serialized_co_carrier",
                "evidenceTier": "direct",
                "storyBinding": True,
                "dependencyOnly": False,
            }
            connections = mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            )
            connection_signature = (
                route_story_key,
                connection["relation"],
                target_mission,
                str(connection.get("radioTriggerId") or ""),
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
                str(existing.get("radioTriggerId") or ""),
            ) == connection_signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(
                route_story_key
            )
    airwall_radio_contexts = build_leveldata_airwall_mission_radio_contexts(
        set(all_story_entry_keys),
        mission_runtime_id_set,
        quest_owner_by_id,
    )
    for context in airwall_radio_contexts:
        route_story_key = resolve_scene_ref_out_key(
            str(context.get("radioId") or ""),
            all_story_entry_keys,
        )
        if not route_story_key:
            continue
        all_state_checks = list(context.get("missionStateChecks") or [])
        has_quest_checks = any(
            check.get("isQuest") is True
            for check in all_state_checks
        )
        for target_mission in context.get("missionStateIds") or []:
            target_mission = str(target_mission or "")
            if target_mission not in mission_runtime_id_set:
                continue
            target_checks = [
                check
                for check in all_state_checks
                if str(check.get("targetMissionId") or "") == target_mission
            ]
            if not target_checks:
                continue
            dependency = {
                "key": route_story_key,
                "kind": story_kind_by_key.get(route_story_key, "radio"),
                "relation": "airwall_mission_state_radio_dependency",
                "direction": "dependency",
                "phase": "airwall_mission_state_gate",
                "confidence": "native_exact_leveldata_airwall_state_carrier",
                "source": (
                    "one exact installed-build LevelData AirWallGroup row "
                    "co-carries typed MissionCheckData predicates and this "
                    "pushBackRadioId; native AirWallManager listeners update "
                    "the wall state and the pushback callback calls "
                    "GameAction.PlayRadio"
                ),
                "storyOwnerMission": (
                    story_owner_by_key.get(route_story_key) or ""
                ),
                "missionStateId": target_mission,
                "missionStateIds": list(context.get("missionStateIds") or []),
                "missionStateChecks": all_state_checks,
                "targetMissionStateChecks": target_checks,
                "riseCombination": context.get("riseCombination"),
                "downCombination": context.get("downCombination"),
                "questTriggerStatus": (
                    "exact_airwall_state_gated_pushback_playback_context_"
                    "not_mission_transition_trigger_or_story_ownership"
                ),
                "storyBinding": False,
                "ownership": False,
                "dependencyOnly": True,
                "questActivation": False,
                "questPlayback": False,
                "questCompletion": False,
                "executionSide": "client",
                "networkRole": "reads_synchronized_local_mission_and_quest_state",
                "serverExchange": False,
                "clientRequest": False,
                "expectedClientReply": False,
                "upstreamServerStateSources": [
                    "SC_SYNC_ALL_MISSION",
                    "SC_MISSION_STATE_UPDATE",
                    *(
                        ["SC_QUEST_STATE_UPDATE"]
                        if has_quest_checks
                        else []
                    ),
                ],
                "upstreamServerStateRole": (
                    "independent server pushes populate local MissionSystem "
                    "and QuestSystem state; AirWall state changes and "
                    "pushback playback send no mission-state query"
                ),
                "serverEvidenceStatus": (
                    "AirWallManager listens to local synchronized mission and "
                    "quest state; a later local wall pushback invokes the "
                    "radio callback"
                ),
                "nativeMappingId": (
                    "leveldata-airwall-mission-radio-memorypack-v1d4"
                ),
                "nativeConsumer": context.get("nativeConsumer"),
                "levelIds": [str(context.get("levelId") or "")],
                "sourceFiles": [str(context.get("sourceFile") or "")],
                "sourcePath": context.get("sourcePath"),
                "recordOffset": context.get("recordOffset"),
                "recordEndOffset": context.get("recordEndOffset"),
                "serializedMemberCount": context.get(
                    "serializedMemberCount"
                ),
                "airWallGroupId": context.get("groupId"),
                "airWallScriptId": context.get("scriptId"),
                "airWallSlotId": context.get("slotId"),
                "airWallDefaultOn": context.get("defaultOn"),
            }
            dependencies = mission_flows_payload[target_mission].setdefault(
                "missionStateStoryDependencies",
                [],
            )
            dependency_signature = (
                route_story_key,
                dependency["relation"],
                target_mission,
                str(dependency.get("sourcePath") or ""),
                int(dependency.get("recordOffset") or 0),
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
                str(existing.get("sourcePath") or ""),
                int(existing.get("recordOffset") or 0),
            ) == dependency_signature for existing in dependencies if isinstance(existing, dict)):
                dependencies.append(dependency)

            connection = {
                **dependency,
                "relation": "airwall_mission_state_radio_playback_context",
                "direction": "context",
                "confidence": "native_exact_serialized_co_carrier",
                "evidenceTier": "direct",
                "storyBinding": True,
                "dependencyOnly": False,
            }
            connections = mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            )
            connection_signature = (
                route_story_key,
                connection["relation"],
                target_mission,
                str(connection.get("sourcePath") or ""),
                int(connection.get("recordOffset") or 0),
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
                str(existing.get("sourcePath") or ""),
                int(existing.get("recordOffset") or 0),
            ) == connection_signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(
                route_story_key
            )
    narrative_interactive_contexts = (
        build_level_interactive_narrative_mission_story_contexts(
            set(all_story_entry_keys),
            mission_runtime_id_set,
        )
    )
    for context in narrative_interactive_contexts:
        route_story_key = resolve_scene_ref_out_key(
            str(context.get("storyKey") or ""),
            all_story_entry_keys,
        )
        target_mission = str(context.get("missionStateId") or "")
        if not route_story_key or target_mission not in mission_runtime_id_set:
            continue
        dependency = {
            "key": route_story_key,
            "kind": story_kind_by_key.get(route_story_key, "radio"),
            "relation": "narrative_interactive_mission_state_dependency",
            "direction": "dependency",
            "phase": "interactive_narrative_mission_state_fx",
            "confidence": "native_exact_same_entity_param_map",
            "source": (
                "one exact counted LevelInteractiveData record co-carries "
                "canonical FX_CHANGE_MISSION_ID and TYPE_ID ParamValue entries; "
                "ReadingPopUpTable resolves TYPE_ID to this Story file and the "
                "native NarrativeComponent reads mission state and starts "
                "radio/dialog playback"
            ),
            "storyOwnerMission": story_owner_by_key.get(route_story_key) or "",
            "missionStateId": target_mission,
            "missionStateGateRoles": ["FX_CHANGE_MISSION_ID"],
            "missionStateGatePredicates": [
                f"Beyond.PropertyKeys.FX_CHANGE_MISSION_ID = {target_mission}",
            ],
            "questTriggerStatus": (
                "exact_same_entity_narrative_mission_state_context_"
                "without_quest_identity"
            ),
            "storyBinding": False,
            "ownership": False,
            "dependencyOnly": True,
            "executionSide": "client",
            "networkRole": "local_narrative_mission_state_context",
            "serverExchange": False,
            "upstreamServerStateSources": [
                "SC_SYNC_ALL_MISSION",
                "SC_MISSION_STATE_UPDATE",
            ],
            "upstreamServerStateRole": (
                "independent server pushes populate the MissionSystem cache; "
                "the mission-state FX gate itself sends no request"
            ),
            "serverEvidenceStatus": (
                "ClientCollectNarrative is local; _CollectNarrative can call "
                "a separate _RequestInteract path, but no exact protocol "
                "message/reply is attributed to this mission-state edge"
            ),
            "nativeMappingId": (
                "level-interactive-narrative-param-map-v1d4"
            ),
            "nativeConsumer": context.get("nativeConsumer"),
            "levelIds": [str(context.get("levelId") or "")],
            "sourceFiles": [str(context.get("sourceFile") or "")],
            "sourcePath": context.get("sourcePath"),
            "recordOffset": context.get("recordOffset"),
            "recordEndOffset": context.get("recordEndOffset"),
            "serializedMemberCount": context.get("serializedMemberCount"),
            "interactiveListCount": context.get("interactiveListCount"),
            "interactiveListCountOffset": context.get("interactiveListCountOffset"),
            "interactiveRecordIndex": context.get("recordIndex"),
            "interactiveParamMapOffset": context.get("paramMapOffset"),
            "interactiveParamMapEndOffset": context.get("paramMapEndOffset"),
            "interactiveParamMapEntryCount": context.get("paramMapEntryCount"),
            "propertyKeys": context.get("propertyKeys"),
            "propertyKeyTokens": context.get("propertyKeyTokens"),
            "propertyEntryOffsets": context.get("propertyEntryOffsets"),
            "readingPopupId": context.get("readingPopupId"),
            "entityDetailIds": [str(context.get("entityDetailId") or "")],
            "entityTemplateIds": [str(context.get("entityTemplateId") or "")],
            "entityTemplatePaths": [str(context.get("entityTemplatePath") or "")],
            "interactiveTableSourceFile": context.get("interactiveTableSourceFile"),
            "interactiveTableVerifiedMirrorFile": context.get(
                "interactiveTableVerifiedMirrorFile"
            ),
            "readingPopupTableSourceFile": context.get(
                "readingPopupTableSourceFile"
            ),
        }
        dependencies = mission_flows_payload[target_mission].setdefault(
            "missionStateStoryDependencies",
            [],
        )
        signature = (
            route_story_key,
            dependency["relation"],
            target_mission,
            int(dependency.get("recordOffset") or 0),
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("missionStateId") or ""),
            int(existing.get("recordOffset") or 0),
        ) == signature for existing in dependencies if isinstance(existing, dict)):
            dependencies.append(dependency)

        connection = {
            **dependency,
            "relation": "narrative_interactive_mission_state_playback_context",
            "direction": "context",
            "confidence": "native_exact_serialized_co_carrier",
            "evidenceTier": "direct",
            "storyBinding": True,
            "dependencyOnly": False,
        }
        connections = mission_flows_payload[target_mission].setdefault(
            "missionStoryConnections",
            [],
        )
        connection_signature = (
            route_story_key,
            connection["relation"],
            target_mission,
            int(connection.get("recordOffset") or 0),
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("missionStateId") or ""),
            int(existing.get("recordOffset") or 0),
        ) == connection_signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(
            route_story_key
        )
    native_event_playback_index: dict[str, list[dict]] = defaultdict(list)
    for playback_index in (
        native_non_fmv_story_playback_index,
        native_black_action_index,
    ):
        for story_key, occurrences in playback_index.items():
            native_event_playback_index[story_key].extend(occurrences)
    task_mission_state_dependencies = (
        build_levelscript_task_mission_state_story_dependencies(
            dict(native_event_playback_index),
        )
    )
    for route in task_mission_state_dependencies:
        route_story_key = resolve_scene_ref_out_key(
            str(route.get("storyKey") or ""),
            all_story_entry_keys,
        )
        target_mission = str(route.get("missionId") or "")
        if (
            not route_story_key
            or target_mission not in mission_runtime_id_set
            or target_mission not in mission_flows_payload
        ):
            continue
        dependency = {
            "key": route_story_key,
            "kind": story_kind_by_key.get(route_story_key, "story"),
            "relation": "levelscript_task_mission_state_dependency",
            "direction": "dependency",
            "phase": "levelscript_task_condition",
            "confidence": "native_exact_same_script_task_dependency",
            "evidenceTier": "native_dependency_only",
            "source": (
                "the same original LevelScript contains this exact Story "
                "playback action and a structurally decoded taskMap "
                "CheckMissionState condition; the task is not on the "
                "playback action's serialized control path"
            ),
            "storyOwnerMission": story_owner_by_key.get(route_story_key) or "",
            "missionStateId": target_mission,
            "missionStateGateRoles": ["task_condition"],
            "missionStateGatePredicates": [str(route.get("predicate") or "")],
            "questTriggerStatus": (
                "exact_same_script_task_dependency_without_control_path"
            ),
            "storyBinding": False,
            "ownership": False,
            "dependencyOnly": True,
            "sameScriptOnly": True,
            "controlPathLinked": False,
            "executionSide": "client",
            "networkRole": "reads_synchronized_local_mission_state",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "upstreamServerStateSources": [
                "SC_SYNC_ALL_MISSION",
                "SC_MISSION_STATE_UPDATE",
            ],
            "upstreamServerStateRole": (
                "independent server pushes populate the local MissionSystem "
                "cache; evaluating this task condition sends no request"
            ),
            "serverEvidenceStatus": (
                "CheckMissionState reads the synchronized local mission-state "
                "cache; no direct request or expected return belongs to this "
                "same-script dependency"
            ),
            "nativeMappingId": route.get("nativeMappingId"),
            "levelIds": [str(route.get("levelId") or "")],
            "scriptIds": [str(route.get("scriptId") or "")],
            "sourceFiles": [str(route.get("sourceFile") or "")],
            "nativeActions": [str(route.get("storyAction") or "")],
            "taskKey": str(route.get("taskKey") or ""),
            "conditionKey": str(route.get("conditionKey") or ""),
            "taskEntryOffset": route.get("taskEntryOffset"),
            "taskEntryOffsetHex": str(route.get("taskEntryOffsetHex") or ""),
            "conditionOffset": route.get("conditionOffset"),
            "conditionOffsetHex": str(route.get("conditionOffsetHex") or ""),
            "missionStateTaskCondition": route,
        }
        dependencies = mission_flows_payload[target_mission].setdefault(
            "missionStateStoryDependencies",
            [],
        )
        signature = (
            route_story_key,
            dependency["relation"],
            target_mission,
            dependency["taskKey"],
            dependency["conditionKey"],
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("missionStateId") or ""),
            str(existing.get("taskKey") or ""),
            str(existing.get("conditionKey") or ""),
        ) == signature for existing in dependencies if isinstance(existing, dict)):
            dependencies.append(dependency)
    mission_state_story_routes = build_levelscript_mission_state_story_routes(
        dict(native_event_playback_index),
    )
    mission_state_story_routes_by_story: dict[str, list[dict]] = defaultdict(list)
    for route in mission_state_story_routes:
        route_story_key = resolve_scene_ref_out_key(
            str(route.get("storyKey") or ""),
            all_story_entry_keys,
        )
        if not route_story_key:
            continue
        mission_state_story_routes_by_story[route_story_key].append(route)
        for target_mission in route.get("gateMissionIds") or []:
            target_mission = str(target_mission or "")
            if target_mission not in mission_runtime_id_set:
                continue
            relevant_paths: list[dict] = []
            for gate_path in route.get("gatePaths") or []:
                relevant_gates = [
                    gate
                    for gate in gate_path.get("missionStateGates") or []
                    if str(gate.get("missionId") or "") == target_mission
                ]
                if relevant_gates:
                    relevant_paths.append({
                        **gate_path,
                        "missionStateGates": relevant_gates,
                    })
            if not relevant_paths:
                continue
            dependency = {
                "key": route_story_key,
                "kind": story_kind_by_key.get(route_story_key, "story"),
                "relation": "mission_state_getter_native_dependency",
                "direction": "dependency",
                "phase": "mission_state_branch",
                "confidence": "native_exact_mission_state_gate",
                "source": (
                    "exact IfElse control path to this Story action; the "
                    "condition is CompareMissionState over GetMissionState "
                    "with a constant original-data mission id and exact "
                    "installed-build native-fallback comparer/state enums"
                ),
                "storyOwnerMission": story_owner_by_key.get(route_story_key) or "",
                "missionStateId": target_mission,
                "missionStateGateRoles": sorted({
                    str(gate.get("selectedStateRelation") or "state_predicate")
                    for path in relevant_paths
                    for gate in path.get("missionStateGates") or []
                }),
                "missionStateGatePredicates": sorted({
                    (
                        f"{gate.get('missionId')} "
                        f"{gate.get('comparerName')} "
                        f"{gate.get('expectedStateName')} -> "
                        f"{gate.get('selectedBranch')} branch"
                    )
                    for path in relevant_paths
                    for gate in path.get("missionStateGates") or []
                }),
                "questTriggerStatus": (
                    "exact_mission_state_gate_without_quest_identity"
                ),
                "storyBinding": False,
                "ownership": False,
                "dependencyOnly": True,
                "executionSide": "client",
                "networkRole": "reads_synchronized_local_mission_state",
                "serverExchange": False,
                "clientRequest": False,
                "expectedClientReply": False,
                "upstreamServerStateSources": [
                    "SC_SYNC_ALL_MISSION",
                    "SC_MISSION_STATE_UPDATE",
                ],
                "upstreamServerStateRole": (
                    "independent server pushes populate the local MissionSystem "
                    "cache; neither is a direct reply to this Story gate"
                ),
                "serverEvidenceStatus": (
                    "GetMissionState.GetResult reads the local player "
                    "MissionSystem cache; this getter and comparison send no "
                    "request and expect no direct response"
                ),
                "nativeMappingId": route.get("nativeMappingId"),
                "nativeFallbackCaveat": (
                    "IFix dispatch can replace native method bodies; retain "
                    "the serialized gate even if a future patch changes "
                    "runtime evaluation semantics"
                ),
                "nativeActions": sorted({
                    str(path.get("storyAction") or "")
                    for path in relevant_paths
                    if path.get("storyAction")
                }),
                "nativeEventNames": sorted({
                    str(path.get("headerName") or "")
                    for path in relevant_paths
                    if path.get("headerName")
                }),
                "levelIds": sorted({
                    str(path.get("levelId") or "")
                    for path in relevant_paths
                    if path.get("levelId")
                }),
                "scriptIds": sorted({
                    str(path.get("scriptId") or "")
                    for path in relevant_paths
                    if path.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(path.get("sourceFile") or "")
                    for path in relevant_paths
                    if path.get("sourceFile")
                }),
                "missionStateGatePaths": relevant_paths,
            }
            dependencies = mission_flows_payload[target_mission].setdefault(
                "missionStateStoryDependencies",
                [],
            )
            signature = (
                route_story_key,
                dependency["relation"],
                target_mission,
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
            ) == signature for existing in dependencies if isinstance(existing, dict)):
                dependencies.append(dependency)

            # Only one state predicate in the current corpus proves an active
            # mission shell narrowly enough to count as a Story attachment:
            # Equal(Processing) with the true branch selected, and no second
            # mission predicate on the path. Broad ``!= Completed`` and
            # completed/post-mission predicates remain dependency-only.
            processing_context = is_exact_processing_mission_state_story_context(
                route,
                target_mission,
            )
            if not processing_context:
                continue
            connection = {
                **dependency,
                "relation": "mission_state_processing_native_playback_context",
                "direction": "context",
                "phase": "mission_processing",
                "confidence": "native_exact_active_mission_context",
                "evidenceTier": "derived_exact_shell",
                "source": (
                    "exact native IfElse true branch plays this Story action "
                    "only while GetMissionState for the named mission equals "
                    "MissionState.Processing; mission shell context, not quest "
                    "causality or Story ownership"
                ),
                "storyBinding": True,
                "ownership": False,
                "dependencyOnly": False,
            }
            connections = mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            )
            connection_signature = (
                route_story_key,
                connection["relation"],
                target_mission,
            )
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("missionStateId") or ""),
            ) == connection_signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(
                route_story_key
            )
    travel_pole_custom_event_routes = (
        build_levelscript_travel_pole_custom_event_story_routes(
            dict(native_event_playback_index),
        )
    )
    custom_event_story_producer_routes = (
        build_levelscript_custom_event_story_producer_routes(
            dict(native_event_playback_index),
        )
    )
    custom_event_story_producer_routes_by_story: dict[str, list[dict]] = (
        defaultdict(list)
    )
    for producer_route in custom_event_story_producer_routes:
        producer_story_key = str(producer_route.get("storyKey") or "")
        if producer_story_key:
            custom_event_story_producer_routes_by_story[producer_story_key].append(
                producer_route
            )
    normalized_native_playback_index: dict[str, list[dict]] = defaultdict(list)
    for raw_story_key, occurrences in native_event_playback_index.items():
        normalized_story_key = resolve_scene_ref_out_key(
            raw_story_key,
            all_story_entry_keys,
        )
        if normalized_story_key:
            normalized_native_playback_index[normalized_story_key].extend(
                occurrences or []
            )
    normalized_custom_event_routes: list[dict] = []
    for producer_route in custom_event_story_producer_routes:
        normalized_story_key = resolve_scene_ref_out_key(
            str(producer_route.get("storyKey") or ""),
            all_story_entry_keys,
        )
        if normalized_story_key:
            normalized_custom_event_routes.append({
                **producer_route,
                "storyKey": normalized_story_key,
            })
    for context in build_quest_progress_locked_interactive_story_contexts(
        dict(normalized_native_playback_index),
        normalized_custom_event_routes,
        mission_runtime_id_set,
    ):
        target_mission = str(context.get("missionId") or "")
        quest_id = str(context.get("questId") or "")
        story_key = str(context.get("storyKey") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        target_quest = next((
            quest
            for quest in (flow_payload or {}).get("quests") or []
            if isinstance(quest, dict) and str(quest.get("id") or "") == quest_id
        ), None)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or not isinstance(target_quest, dict)
        ):
            continue
        source_files = sorted({
            str(record.get("missionRuntimeSourceFile") or "")
            for record in context.get("levelDataRecords") or []
        } | {
            str(record.get("levelDataSourceFile") or "")
            for record in context.get("levelDataRecords") or []
        } | {
            str(record.get("levelDataVerifiedMirrorFile") or "")
            for record in context.get("levelDataRecords") or []
        } | {
            str(record.get("worldEntityRegistrySourceFile") or "")
            for record in context.get("levelDataRecords") or []
        } | {
            str(route.get("playbackSourceFile") or "")
            for route in context.get("entityRoutes") or []
        } - {""})
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "quest_progress_locked_interactive_playback_context",
            "direction": "context",
            "phase": "quest_progress_lock",
            "confidence": "native_exact_quest_progress_locked_interactive_context",
            "evidenceTier": "native_exact_context",
            "source": (
                "every exact native playback occurrence is rooted directly, or "
                "through an exact literal custom-event producer, at a constant "
                "InteractiveStateChanged world entity; its byte-identical counted "
                "LevelInteractiveData record has a complete "
                "SimpleConditionCheckQuestState Equal Completed progress lock, the "
                "registry type/detail matches, and the quest resolves uniquely in "
                "MissionRuntime; this proves local quest-state-gated interactive "
                "context only, not Story ownership or quest activation/playback/"
                "completion causality"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "candidateQuestIds": [quest_id],
            "questTriggerStatus": (
                "quest_completed_state_gates_interactive_progress_lock_not_"
                "playback_activation"
            ),
            "storyBinding": True,
            "ownership": False,
            "questActivation": False,
            "questActivationCausality": False,
            "questPlayback": False,
            "questCompletion": False,
            "executionSide": "client",
            "networkRole": (
                "reads_synchronized_local_quest_state_and_dispatches_local_entity_event"
            ),
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "levelIds": list(context.get("levelIds") or []),
            "entityLogicIds": list(context.get("entityLogicIds") or []),
            "progressLockCondition": str(
                context.get("progressLockCondition") or ""
            ),
            "compareOperator": str(context.get("compareOperator") or ""),
            "compareTarget": str(context.get("compareTarget") or ""),
            "nativeOccurrenceCount": context.get("occurrenceCount"),
            "nativeRouteCount": context.get("routeCount"),
            "sourceFiles": source_files,
            "questProgressLockEvidence": context,
        }
        connections = target_quest.setdefault("storyConnections", [])
        connection_signature = (
            story_key,
            connection["relation"],
            quest_id,
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str((existing.get("candidateQuestIds") or [""])[0] or ""),
        ) == connection_signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)
    manual_guide_group_story_routes = (
        build_levelscript_manual_guide_group_story_routes(
            dict(native_event_playback_index),
        )
    )
    authoritative_scope_script_pairs = set(native_script_pairs)
    authoritative_scope_script_pairs.update({
        (
            str(route.get("levelId") or ""),
            str(route.get("producerScriptId") or ""),
        )
        for route in travel_pole_custom_event_routes
        if route.get("levelId") and route.get("producerScriptId")
    })
    native_script_pairs.update({
        (
            str(route.get("levelId") or ""),
            str(route.get("producerScriptId") or ""),
        )
        for route in manual_guide_group_story_routes
        if route.get("levelId") and route.get("producerScriptId")
    })
    leveldata_script_hosts = build_leveldata_mission_script_host_index(
        native_script_pairs,
        mission_runtime_id_set,
    )
    mission_area_leveldata_script_hosts = (
        build_leveldata_mission_area_script_host_index(native_script_pairs)
    )
    npc_proxy_segment_script_hosts = build_npc_proxy_segment_script_host_index(
        native_script_pairs,
        npc_tracking_consumers,
    )

    # A typed MissionRuntime NPC tracking row and NpcProxyEx mission owner can
    # identify the WorldEntityRegistry segment that contains a playback
    # LevelScript.  The registry's dictionary key and repeated
    # segmentIdGlobal must both equal that exact same-scene LevelScript id.
    # This is authored segment/mission-shell context only: navigation does not
    # prove that the quest, NPC, or server activates the script.  Files with a
    # stronger attachment anywhere are deliberately left untouched, and every
    # resolved occurrence must agree on one mission before a new attachment is
    # emitted.
    npc_proxy_segment_candidates: dict[str, list[dict]] = defaultdict(list)
    for raw_story_key, occurrences in native_event_playback_index.items():
        story_key = resolve_scene_ref_out_key(
            raw_story_key,
            all_story_entry_keys,
        )
        if not story_key:
            continue
        for occurrence in occurrences:
            pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            host = npc_proxy_segment_script_hosts.get(pair)
            npc_proxy_segment_candidates[story_key].append({
                "occurrence": occurrence,
                "host": host,
            })

    # Promotion is deliberately deferred until all stronger native and
    # original-data connection families below have populated the flow. The
    # final selector runs immediately before DialogTree parent inheritance.
    pending_npc_proxy_segment_connections: list[tuple[str, str, dict]] = []
    for story_key, evidence_rows in sorted(npc_proxy_segment_candidates.items()):
        # A normalized Story output can have several authored dlg/misc aliases
        # or native occurrences. Every one must resolve through the exact same
        # segment rule; accepting only the matching subset would let a weak
        # shell edge bypass stronger/conflicting evidence elsewhere.
        if not evidence_rows or any(not row.get("host") for row in evidence_rows):
            continue
        hosts = [row["host"] for row in evidence_rows]
        if any(str(host.get("status") or "") != "unique" for host in hosts):
            continue
        host_missions = {
            str(mission_id or "")
            for host in hosts
            for mission_id in host.get("hostMissionIds") or []
        }
        host_missions.discard("")
        if len(host_missions) != 1:
            continue
        target_mission = next(iter(host_missions))
        flow_payload = mission_flows_payload.get(target_mission)
        if flow_payload is None:
            continue
        occurrences = [row["occurrence"] for row in evidence_rows]
        host_rows = [
            row
            for host in hosts
            for row in host.get("hosts") or []
            if isinstance(row, dict)
        ]
        tracking_consumers = [
            row
            for host in host_rows
            for row in host.get("trackingConsumers") or []
            if isinstance(row, dict)
        ]
        registry_rows = [
            host.get("registryRow")
            for host in host_rows
            if isinstance(host.get("registryRow"), dict)
        ]
        proxy_ex_rows = [
            row
            for host in host_rows
            for row in host.get("npcProxyExRows") or []
            if isinstance(row, dict)
        ]
        native_event_owners = [
            owner
            for occurrence in occurrences
            for owner in occurrence.get("nativeEventOwners") or []
            if isinstance(owner, dict)
        ]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "npc_proxy_segment_levelscript_mission_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_npc_proxy_segment_shell",
            "evidenceTier": "derived_exact_shell",
            "source": (
                "typed same-scene MissionRuntime NpcProxyTrackingInfo + "
                "matching NpcProxyEx mission owner + WorldEntityRegistry "
                "NpcProxyBriefInfo whose dictionary key and segmentIdGlobal "
                "equal the exact Story playback LevelScript global id; "
                "authored segment shell only, not quest/NPC activation"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "npcProxyIds": sorted({
                str(row.get("proxyId") or "")
                for row in host_rows
                if row.get("proxyId")
            }),
            "segmentIdsGlobal": sorted({
                str(row.get("segmentIdGlobal") or "")
                for row in host_rows
                if row.get("segmentIdGlobal")
            }),
            "candidateQuestIds": sorted({
                str(row.get("questId") or "")
                for row in tracking_consumers
                if row.get("questId")
            }),
            "questTriggerStatus": (
                "same_authored_npc_proxy_segment_not_quest_playback"
            ),
            "executionSide": "client",
            "networkRole": "local_authored_segment_context",
            "serverExchange": False,
            "serverEvidenceStatus": (
                "tracking_and_segment_identity_only_no_request_or_response"
            ),
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in occurrences
                if row.get("scriptId")
            }),
            "nativeActions": sorted({
                str(row.get("actionName") or "")
                for row in occurrences
                if row.get("actionName")
            }),
            "nativeEventNames": sorted({
                str(owner.get("headerName") or "")
                for owner in native_event_owners
                if owner.get("headerName")
            }),
            "nativeEventOwners": native_event_owners,
            "npcProxyTrackingRows": tracking_consumers,
            "npcProxyRegistryRows": registry_rows,
            "npcProxyExRows": proxy_ex_rows,
            "sourceFiles": sorted({
                *[
                    str(row.get("sourceFile") or "")
                    for row in occurrences
                ],
                *[
                    str(row.get("sourceFile") or "")
                    for row in tracking_consumers
                ],
                *[
                    str(row.get("sourceFile") or "")
                    for row in registry_rows
                ],
                *[
                    str(row.get("sourceFile") or "")
                    for row in proxy_ex_rows
                ],
            } - {""}),
        }
        pending_npc_proxy_segment_connections.append((
            target_mission,
            story_key,
            connection,
        ))

    # The current native guide implementation distinguishes manual guide
    # groups from server-owned guide completion.  ManuallyStartGuideGroup calls
    # _TryAddProcessingClientOnlyGuideGroup; _CompleteCurGuideGroup handles
    # that branch locally and skips CS_COMPLETE_GUIDE_GROUP.  Attach the exact
    # completion playback only to a producer script with one validated,
    # mission-named LevelData host.  This remains mission-shell context, never
    # a quest trigger or a server request/response edge.
    for guide_route in select_leveldata_native_event_story_context(
        manual_guide_group_story_routes,
        leveldata_script_hosts,
        preexisting_attached_story_keys_by_mission,
    ):
        story_key = resolve_scene_ref_out_key(
            str(guide_route.get("storyKey") or ""),
            all_story_entry_keys,
        )
        target_mission = str(guide_route.get("missionId") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if not story_key or not target_mission or flow_payload is None:
            continue
        shell_hosts = list(guide_route.get("levelDataHosts") or [])
        source_files = sorted({
            str(guide_route.get("producerSourceFile") or ""),
            *[
                str(value or "")
                for value in guide_route.get("listenerSourceFiles") or []
            ],
            *[
                str(host.get("levelDataFile") or "")
                for host in shell_hosts
            ],
        } - {""})
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "mission_shell_manual_guide_completion_playback_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_client_only_guide_completion_shell",
            "evidenceTier": "derived_exact_shell",
            "source": (
                "exact current-build ManuallyStartGuideGroup action literal + "
                "exact OnGuideGroupComplete Story listener literal + one "
                "validated mission-named LevelData member-22 producer host; "
                "the native client-only completion branch skips the guide "
                "completion request"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "levelDataHostMissionId": target_mission,
            "questTriggerStatus": (
                "manual_guide_group_shell_context_not_quest_playback"
            ),
            "executionSide": "client",
            "networkRole": "local_client_only_guide_group_context",
            "serverExchange": False,
            "serverEvidenceStatus": (
                "client_only_manual_guide_branch_skips_cs_complete_guide_group"
            ),
            "guideGroupId": str(guide_route.get("guideGroupId") or ""),
            "nativeAction": "ManuallyStartGuideGroup",
            "opcode": "0x0304/0x09",
            "producerScriptIds": [
                str(guide_route.get("producerScriptId") or "")
            ],
            "producerActionLocalId": guide_route.get(
                "producerActionLocalId"
            ),
            "listenerLevelIds": list(
                guide_route.get("listenerLevelIds") or []
            ),
            "listenerScriptIds": list(
                guide_route.get("listenerScriptIds") or []
            ),
            "listenerEventOwners": list(
                guide_route.get("listenerEventOwners") or []
            ),
            "levelIds": sorted({
                str(guide_route.get("levelId") or ""),
                *[
                    str(value or "")
                    for value in guide_route.get("listenerLevelIds") or []
                ],
            } - {""}),
            "levelDataFiles": sorted({
                str(host.get("levelDataFile") or "")
                for host in shell_hosts
                if host.get("levelDataFile")
            }),
            "sourceFiles": source_files,
        }
        flow_payload.setdefault("missionStoryConnections", []).append(
            connection
        )
        preexisting_attached_story_keys_by_mission[target_mission].add(
            story_key
        )
    authoritative_script_scope_references: dict[
        tuple[str, str],
        list[dict],
    ] = defaultdict(list)
    for pair, references in script_condition_bindings.items():
        for reference in references:
            authoritative_script_scope_references[pair].append({
                **reference,
                "scopeKind": "typed_mission_runtime_script_condition",
            })
    for pair, references in interactive_condition_script_bindings.items():
        for reference in references:
            authoritative_script_scope_references[pair].append({
                **reference,
                "scriptId": pair[1],
                "scopeKind": (
                    "typed_interactive_condition_registry_script_entity"
                ),
            })
    for tracking_mission, flow_payload in mission_flows_payload.items():
        mission_runtime_source = repo_rel(MRA_DIR / f"{tracking_mission}.json")
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            for hint in quest.get("tracking") or []:
                resolution = resolve_entity_tracking_script(hint)
                if resolution.get("status") != "unique":
                    continue
                pair = (
                    str(resolution.get("levelId") or ""),
                    str(resolution.get("scriptId") or ""),
                )
                if not all(pair):
                    continue
                if (
                    hint.get("trackingListSource")
                    == "multiDescTrackingInfoList.actualList"
                    and tracking_owner_missions_by_pair.get(pair)
                    != {tracking_mission}
                ):
                    continue
                authoritative_script_scope_references[pair].append({
                    "missionId": tracking_mission,
                    "questId": str(quest.get("id") or ""),
                    "scopeKind": "typed_entity_tracking_registry_script",
                    "entitySlotId": resolution.get("entitySlotId"),
                    "registryIndex": resolution.get("registryIndex"),
                    "sourceFile": mission_runtime_source,
                    "registrySourceFile": str(
                        resolution.get("registrySourceFile") or ""
                    ),
                    "trackingListSource": hint.get("trackingListSource"),
                    "trackingObjectiveIndex": hint.get("objectiveIndex"),
                    "multiDescriptionIndex": hint.get("multiDescriptionIndex"),
                    "actualListIndex": hint.get("actualListIndex"),
                })
    authoritative_scope_leveldata_script_hosts = (
        build_leveldata_authoritative_scope_script_host_index(
            authoritative_scope_script_pairs,
            mission_runtime_id_set,
            authoritative_script_scope_references,
        )
    )
    shared_leveldata_hosts_by_story: dict[str, list[dict]] = defaultdict(list)

    # A producer-only LevelScript can share one complete validated LevelData
    # shell with authoritative MissionRuntime anchors even when the playback
    # listener lives in a different LevelData asset.  Attach only the exact
    # typed TravelPole -> EntityCompare -> RaiseCustomLevelEvent -> unique
    # same-level custom-event Story routes selected by the fail-closed helper.
    # Stronger direct/tracked attachments, including PLAY_SEQ_1, were inserted
    # above and are deliberately skipped here.
    for native_event in select_leveldata_native_event_story_context(
        travel_pole_custom_event_routes,
        authoritative_scope_leveldata_script_hosts,
        preexisting_attached_story_keys_by_mission,
    ):
        story_key = resolve_scene_ref_out_key(
            str(native_event.get("storyKey") or ""),
            all_story_entry_keys,
        )
        target_mission = str(native_event.get("missionId") or "")
        flow_payload = mission_flows_payload.get(target_mission)
        if not story_key or not target_mission or flow_payload is None:
            continue
        shell_hosts = list(native_event.get("levelDataHosts") or [])
        authoritative_references = [
            reference
            for host in shell_hosts
            for reference in host.get("authoritativeReferences") or []
        ]
        entity_compare = (
            (native_event.get("entityCompareBridge") or {}).get(
                "entityCompare"
            )
            or {}
        )
        script_entity = entity_compare.get("scriptEntity") or {}
        source_files = sorted({
            str(native_event.get("producerSourceFile") or ""),
            *[
                str(value or "")
                for value in native_event.get("listenerSourceFiles") or []
            ],
            *[
                str(host.get("levelDataFile") or "")
                for host in shell_hosts
            ],
            *[
                str(reference.get("sourceFile") or "")
                for reference in authoritative_references
            ],
        } - {""})
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "authoritative_scope_native_event_playback_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_validated_leveldata_shell_event_route",
            "evidenceTier": "derived_exact_shell",
            "source": (
                "exact TravelPoleBegin entity output compared to one slot-backed "
                "ScriptEntityPtr + typed IfElse path + RaiseCustomLevelEvent "
                "literal + unique same-level LevelEvent_OnCustomEvent Story "
                "listener; the producer script's complete validated LevelData "
                "member-22 dictionary has one authoritative mission union"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "levelDataHostMissionId": target_mission,
            "questTriggerStatus": (
                "producer_shell_custom_event_context_not_quest_playback"
            ),
            "executionSide": "client",
            "networkRole": "local_asset_shell_custom_event_context",
            "serverExchange": False,
            "serverEvidenceStatus": "local_native_event_route_no_server_payload",
            "levelIds": [str(native_event.get("levelId") or "")],
            "producerScriptIds": [
                str(native_event.get("producerScriptId") or "")
            ],
            "listenerScriptIds": list(
                native_event.get("listenerScriptIds") or []
            ),
            "entitySlotIds": [str(script_entity.get("slotId"))]
            if isinstance(script_entity.get("slotId"), int)
            else [],
            "entityLogicIds": [str(script_entity.get("logicId"))]
            if isinstance(script_entity.get("logicId"), int)
            else [],
            "trackedSlotBridgeStatus": "exact_entity_compare_event_bridge",
            "producerEventName": str(
                native_event.get("producerHeaderName") or ""
            ),
            "producerHeaderLocalId": native_event.get(
                "producerHeaderLocalId"
            ),
            "nativeAction": "RaiseCustomLevelEvent",
            "opcode": "0x037e/0x0a",
            "raiseActionLocalId": native_event.get("raiseActionLocalId"),
            "raisedEventKey": str(native_event.get("raisedEventKey") or ""),
            "entityCompareBridge": native_event.get("entityCompareBridge"),
            "producerControlPath": native_event.get("producerControlPath"),
            "listenerEventOwners": native_event.get("listenerEventOwners") or [],
            "levelDataFiles": sorted({
                str(host.get("levelDataFile") or "")
                for host in shell_hosts
                if host.get("levelDataFile")
            }),
            "levelDataDictionaryEntryCounts": sorted({
                int(host.get("dictionaryEntryCount"))
                for host in shell_hosts
                if isinstance(host.get("dictionaryEntryCount"), int)
            }),
            "authoritativeScopeKinds": sorted({
                str(reference.get("scopeKind") or "")
                for reference in authoritative_references
                if reference.get("scopeKind")
            }),
            "anchorQuestIds": sorted({
                str(reference.get("questId") or "")
                for reference in authoritative_references
                if reference.get("questId")
            }),
            "anchorScriptIds": sorted({
                str(reference.get("scriptId") or "")
                for reference in authoritative_references
                if reference.get("scriptId")
            }),
            "authoritativeScopeReferences": authoritative_references,
            "sourceFiles": source_files,
        }
        flow_payload.setdefault("missionStoryConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    def missionish_ref_target(raw_ref: object) -> str:
        text = str(raw_ref or "").strip()
        if text in mission_runtime_id_set:
            return text
        if "_q#" in text:
            mission_id = text.split("_q#", 1)[0]
            if mission_id in mission_runtime_id_set:
                return mission_id
        return ""

    for story_key, occurrences in sorted(action_story_occurrences.items()):
        if story_key not in all_story_entry_keys:
            continue
        if any(
            occurrence.get("recordClass") == "play_fmv"
            for occurrence in occurrences
        ):
            # FMV mission placement is handled only by the exact native
            # LevelData joins below, after all occurrences pass the one-shell
            # completeness check. The generic string/script scope must never
            # promote a favorable subset of an ambiguous FMV family.
            continue
        story_owner = story_owner_by_key.get(story_key) or ""
        scoped_occurrences_by_mission: dict[str, list[dict]] = defaultdict(list)
        for occurrence in occurrences:
            record_story_owners = {
                story_owner_by_key.get(str(record_key) or "") or ""
                for record_key in occurrence.get("allStoryKeysInRecord") or []
                if str(record_key or "") in all_story_entry_keys
            }
            record_story_owners.discard("")
            if len(record_story_owners) > 1:
                continue
            explicit_evidence: list[dict] = []
            explicit_missions: set[str] = set()
            for missionish_ref in occurrence.get("sourceMissionishRefs") or []:
                target_mission = missionish_ref_target(missionish_ref.get("text"))
                if not target_mission:
                    continue
                explicit_missions.add(target_mission)
                explicit_evidence.append({
                    "missionId": target_mission,
                    "rawRef": str(missionish_ref.get("text") or ""),
                    "offset": missionish_ref.get("offset"),
                    "encoding": str(missionish_ref.get("encoding") or ""),
                })
            condition_evidence = list(script_condition_bindings.get((
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )) or [])
            condition_missions = {
                str(row.get("missionId") or "")
                for row in condition_evidence
                if row.get("missionId")
            }
            scoped_missions = explicit_missions | condition_missions
            if len(scoped_missions) != 1:
                continue
            target_mission = next(iter(scoped_missions))
            if target_mission not in mission_flows_payload:
                continue
            scoped_occurrence = dict(occurrence)
            if explicit_evidence:
                scoped_occurrence["explicitMissionRefs"] = explicit_evidence
            if condition_evidence:
                scoped_occurrence["missionConditions"] = condition_evidence
            scoped_occurrence["scopeEvidenceKinds"] = [
                label
                for label, rows in (
                    ("script_contains_mission_or_quest_ref", explicit_evidence),
                    ("mission_condition_checks_script", condition_evidence),
                )
                if rows
            ]
            scoped_occurrences_by_mission[target_mission].append(scoped_occurrence)
        all_occurrence_count = len(occurrences)
        for target_mission, scoped_occurrences in sorted(
            scoped_occurrences_by_mission.items()
        ):
            if story_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "story"),
                "relation": "levelscript_mission_context",
                "direction": "context",
                "phase": "context",
                "confidence": "scoped_script",
                "source": (
                    "decoded actionList payload contains this exact Story id; the containing "
                    "LevelScript is separately and uniquely scoped to this MissionRuntime"
                ),
                "storyOwnerMission": story_owner,
                "levelScriptMissionId": target_mission,
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": all_occurrence_count,
                "hasUnscopedOrOtherMissionOccurrences": (
                    len(scoped_occurrences) < all_occurrence_count
                ),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "scopeEvidenceKinds": sorted({
                    str(kind)
                    for row in scoped_occurrences
                    for kind in row.get("scopeEvidenceKinds") or []
                    if kind
                }),
                "levelScriptOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    def native_black_control_summary(occurrences: list[dict]) -> dict:
        control_paths = [
            path
            for occurrence in occurrences
            for path in occurrence.get("nativeEventOwners") or []
            if isinstance(path, dict)
        ]
        if not control_paths:
            return {}
        return {
            "nativeEventOwnerStatus": "exact_serialized_control_path",
            "nativeEventNames": sorted({
                str(path.get("headerName") or "")
                for path in control_paths
                if path.get("headerName")
            }),
            "nativeEventOpcodes": sorted({
                str(path.get("headerOpcode") or "")
                for path in control_paths
                if path.get("headerOpcode")
            }),
            "nativeEventTags": sorted({
                str(path.get("headerUnionTag") or "")
                for path in control_paths
                if path.get("headerUnionTag")
            }),
            "nativeEventTexts": sorted({
                str(text)
                for path in control_paths
                for text in path.get("headerTexts") or []
                if text
            }),
            "nativeEventSummaries": sorted({
                str((path.get("eventDetail") or {}).get("summary") or "")
                for path in control_paths
                if (path.get("eventDetail") or {}).get("summary")
            }),
            "triggerSlotIds": sorted({
                str(slot_id)
                for path in control_paths
                for slot_id in path.get("triggerSlotIds") or []
            }),
            "nativeControlPathCount": len(control_paths),
            "nativeActionTags": sorted({
                str(occurrence.get("unionTag") or "")
                for occurrence in occurrences
                if occurrence.get("unionTag")
            }),
        }

    # Native black-screen actions serialize TextTable line ids and therefore
    # are not present in ``action_story_occurrences``. Apply the same exact
    # MissionRuntime script-condition / explicit-script-reference scope used
    # above instead of leaving those typed actions out of quest and mission
    # context. A Story filename or a shared LevelData shell is never used as
    # an owner here.
    for black_key, occurrences in sorted(native_black_action_index.items()):
        if black_key not in all_story_entry_keys:
            continue
        story_owner = story_owner_by_key.get(black_key) or ""
        scoped_occurrences_by_mission: dict[str, list[dict]] = defaultdict(list)
        for occurrence in occurrences:
            explicit_evidence: list[dict] = []
            explicit_missions: set[str] = set()
            for missionish_ref in occurrence.get("sourceMissionishRefs") or []:
                target_mission = missionish_ref_target(missionish_ref.get("text"))
                if not target_mission:
                    continue
                explicit_missions.add(target_mission)
                explicit_evidence.append({
                    "missionId": target_mission,
                    "rawRef": str(missionish_ref.get("text") or ""),
                    "offset": missionish_ref.get("offset"),
                    "encoding": str(missionish_ref.get("encoding") or ""),
                })
            condition_evidence = list(script_condition_bindings.get((
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )) or [])
            condition_missions = {
                str(row.get("missionId") or "")
                for row in condition_evidence
                if row.get("missionId")
            }
            scoped_missions = explicit_missions | condition_missions
            if len(scoped_missions) != 1:
                continue
            target_mission = next(iter(scoped_missions))
            if target_mission not in mission_flows_payload:
                continue
            scoped_occurrence = dict(occurrence)
            if explicit_evidence:
                scoped_occurrence["explicitMissionRefs"] = explicit_evidence
            if condition_evidence:
                scoped_occurrence["missionConditions"] = condition_evidence
            scoped_occurrence["scopeEvidenceKinds"] = [
                label
                for label, rows in (
                    ("script_contains_mission_or_quest_ref", explicit_evidence),
                    ("mission_condition_checks_script", condition_evidence),
                )
                if rows
            ]
            scoped_occurrences_by_mission[target_mission].append(scoped_occurrence)

            # A MissionRuntime condition names the exact quest that observes
            # this LevelScript. Preserve that authored quest scope as well as
            # the broader mission-shell connection emitted below.
            for condition_row in condition_evidence:
                quest_id = str(condition_row.get("questId") or "")
                quest_target = quest_targets.get(quest_id)
                if not quest_target or quest_target[0] != target_mission:
                    continue
                _quest_mission, quest = quest_target
                quest_connection = {
                    "key": black_key,
                    "kind": story_kind_by_key.get(black_key, "black"),
                    "relation": "levelscript_condition_scope",
                    "direction": "context",
                    "phase": "runtime_playback",
                    "confidence": "scoped_script",
                    "source": (
                        "typed current-build NarrativeBlackScreen action in the "
                        "exact LevelScript referenced by this quest condition"
                    ),
                    "mapId": str(occurrence.get("levelId") or ""),
                    "scriptId": str(occurrence.get("scriptId") or ""),
                    "conditionKey": str(condition_row.get("conditionKey") or ""),
                    "conditionType": str(condition_row.get("conditionType") or ""),
                    "executionSide": "client",
                    "networkRole": "local_presentation",
                    "nativeAction": str(occurrence.get("actionName") or ""),
                    "opcode": (
                        f"{occurrence.get('actionCode')}/{occurrence.get('actionKind')}"
                    ),
                    "textIds": list(occurrence.get("lineIds") or []),
                }
                connections = quest.setdefault("storyConnections", [])
                signature = (
                    black_key,
                    quest_connection["relation"],
                    quest_connection["mapId"],
                    quest_connection["scriptId"],
                    quest_connection["conditionKey"],
                )
                if any((
                    str(existing.get("key") or ""),
                    str(existing.get("relation") or ""),
                    str(existing.get("mapId") or ""),
                    str(existing.get("scriptId") or ""),
                    str(existing.get("conditionKey") or ""),
                ) == signature for existing in connections if isinstance(existing, dict)):
                    continue
                connections.append(quest_connection)

        for target_mission, scoped_occurrences in sorted(
            scoped_occurrences_by_mission.items()
        ):
            if black_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            connection = {
                "key": black_key,
                "kind": story_kind_by_key.get(black_key, "black"),
                "relation": "levelscript_native_black_action",
                "direction": "context",
                "phase": "runtime_playback",
                "confidence": "scoped_script",
                "source": (
                    "current-build NarrativeBlackScreen formatter + exact TextTable "
                    "line id + client ShowNarrativeBlackScreen Execute; the containing "
                    "LevelScript is separately and uniquely scoped to this MissionRuntime"
                ),
                "storyOwnerMission": story_owner,
                "levelScriptMissionId": target_mission,
                "executionSide": "client",
                "networkRole": "local_presentation",
                "questTriggerStatus": "condition_scoped",
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                **native_black_control_summary(scoped_occurrences),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "textIds": sorted({
                    str(line_id)
                    for row in scoped_occurrences
                    for line_id in row.get("lineIds") or []
                    if line_id
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "scopeEvidenceKinds": sorted({
                    str(kind)
                    for row in scoped_occurrences
                    for kind in row.get("scopeEvidenceKinds") or []
                    if kind
                }),
                "nativeBlackActionOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    # The strongest broad mission-shell join available in the installed data:
    # a typed current-build Story playback record belongs to a numeric
    # LevelScript file, and a mission-named LevelData file in the same level
    # contains that id in its fully validated member-22 BriefData dictionary.
    # This is asset-shell context, not logical quest ownership; quest placement
    # is never inferred from byte proximity.
    def leveldata_scoped_occurrences(
        occurrences: list[dict],
    ) -> tuple[dict[str, list[dict]], list[dict]]:
        return classify_leveldata_mission_shell_occurrences(
            occurrences,
            leveldata_script_hosts,
            set(mission_flows_payload),
        )

    for story_key, occurrences in sorted(native_story_playback_index.items()):
        scoped_by_mission, shared_hosts = leveldata_scoped_occurrences(occurrences)
        if shared_hosts:
            shared_leveldata_hosts_by_story[story_key].extend(shared_hosts)
        if not native_fmv_scope_is_complete(
            occurrences,
            scoped_by_mission,
            shared_hosts,
        ):
            continue
        if story_key not in all_story_entry_keys:
            continue
        story_owner = story_owner_by_key.get(story_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            if story_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "story"),
                "relation": "leveldata_levelscript_mission_context",
                "direction": "context",
                "phase": "context",
                "confidence": "native_exact_host",
                "source": (
                    "current-build typed playback action + exact same-level numeric "
                    "LevelScript id in a validated LevelData member-22 "
                    "LevelScriptBriefData dictionary entry; mission-named asset-shell "
                    "context only"
                ),
                "storyOwnerMission": story_owner,
                "levelDataHostMissionId": target_mission,
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "hasUnscopedOrOtherMissionOccurrences": (
                    len(scoped_occurrences) < len(occurrences)
                ),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for row in scoped_occurrences
                    for host in row.get("levelDataHosts") or []
                    if host.get("levelDataFile")
                }),
                "levelScriptOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # Black-screen actions store TextTable line ids rather than conversation
    # ids.  Their native formatter/Execute proof establishes client playback;
    # the validated LevelData BriefData host supplies asset-shell context.
    for black_key, occurrences in sorted(native_black_action_index.items()):
        scoped_by_mission, shared_hosts = leveldata_scoped_occurrences(occurrences)
        if shared_hosts:
            shared_leveldata_hosts_by_story[black_key].extend(shared_hosts)
        if black_key not in all_story_entry_keys:
            continue
        story_owner = story_owner_by_key.get(black_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            if black_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            connection = {
                "key": black_key,
                "kind": story_kind_by_key.get(black_key, "black"),
                "relation": "levelscript_native_black_action",
                "direction": "context",
                "phase": "runtime_playback",
                "confidence": "native_exact_host",
                "source": (
                    "current-build NarrativeBlackScreen formatter + exact TextTable "
                    "line id + client ShowNarrativeBlackScreen Execute + exact "
                    "same-level validated Mission LevelData BriefData host"
                ),
                "storyOwnerMission": story_owner,
                "levelDataHostMissionId": target_mission,
                "executionSide": "client",
                "networkRole": "local_presentation",
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                **native_black_control_summary(scoped_occurrences),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "textIds": sorted({
                    str(line_id)
                    for row in scoped_occurrences
                    for line_id in row.get("lineIds") or []
                    if line_id
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for row in scoped_occurrences
                    for host in row.get("levelDataHosts") or []
                    if host.get("levelDataFile")
                }),
                "nativeMappingId": str(
                    scoped_occurrences[0].get("nativeMappingId") or ""
                ),
                "nativeBlackActionOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    def mission_area_leveldata_scoped_occurrences(
        occurrences: list[dict],
    ) -> tuple[dict[str, list[dict]], list[dict]]:
        scoped: dict[str, list[dict]] = defaultdict(list)
        shared: list[dict] = []
        for occurrence in occurrences:
            pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            host_evidence = mission_area_leveldata_script_hosts.get(pair)
            if not host_evidence:
                continue
            if host_evidence.get("status") != "unique":
                shared.append(host_evidence)
                continue
            host_missions = list(host_evidence.get("hostMissionIds") or [])
            if len(host_missions) != 1:
                continue
            target_mission = str(host_missions[0] or "")
            if target_mission not in mission_flows_payload:
                continue
            enriched = dict(occurrence)
            enriched["missionAreaLevelDataHosts"] = list(
                host_evidence.get("hosts") or []
            )
            enriched["scopeEvidenceKinds"] = [
                "typed_mission_area_subdata_parent_matches_validated_leveldata_root"
            ]
            scoped[target_mission].append(enriched)
        return scoped, shared

    # Some broad LevelData filenames carry no MissionRuntime identifier. The
    # original data still supplies an exact asset-shell join when a typed
    # MissionAreaTrackingInfo id resolves through MissionAreaTable's
    # subDataParentId to a root BriefData key in that same fully validated
    # member-22 dictionary. Every authored root in the file must agree on one
    # mission; shared files remain debug-only ambiguity evidence.
    for story_key, occurrences in sorted(native_story_playback_index.items()):
        scoped_by_mission, shared_hosts = mission_area_leveldata_scoped_occurrences(
            occurrences
        )
        if shared_hosts:
            shared_leveldata_hosts_by_story[story_key].extend(shared_hosts)
        if not native_fmv_scope_is_complete(
            occurrences,
            scoped_by_mission,
            shared_hosts,
        ):
            continue
        if story_key not in all_story_entry_keys:
            continue
        story_owner = story_owner_by_key.get(story_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            if story_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            area_hosts = [
                host
                for row in scoped_occurrences
                for host in row.get("missionAreaLevelDataHosts") or []
            ]
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "story"),
                "relation": "mission_area_leveldata_mission_context",
                "direction": "context",
                "phase": "context",
                "confidence": "native_exact_area_root_host",
                "source": (
                    "typed MissionRuntime MissionAreaTrackingInfo.missionAreaId + "
                    "exact MissionAreaTable.subDataParentId + identical root key "
                    "in the same validated LevelData member-22 dictionary; "
                    "asset-shell context only"
                ),
                "storyOwnerMission": story_owner,
                "missionAreaHostMissionId": target_mission,
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "hasUnscopedOrOtherMissionOccurrences": (
                    len(scoped_occurrences) < len(occurrences)
                ),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                **native_black_control_summary(scoped_occurrences),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for host in area_hosts
                    if host.get("levelDataFile")
                }),
                "missionAreaIds": sorted({
                    str(reference.get("missionAreaId") or "")
                    for host in area_hosts
                    for reference in host.get("missionAreaReferences") or []
                    if reference.get("missionAreaId")
                }),
                "subDataParentIds": sorted({
                    str(root_id)
                    for host in area_hosts
                    for root_id in host.get("rootScriptIds") or []
                    if root_id
                }),
                "missionAreaSourceFiles": sorted({
                    str(reference.get("sourceFile") or "")
                    for host in area_hosts
                    for reference in host.get("missionAreaReferences") or []
                    if reference.get("sourceFile")
                }),
                "levelScriptOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    for black_key, occurrences in sorted(native_black_action_index.items()):
        scoped_by_mission, shared_hosts = mission_area_leveldata_scoped_occurrences(
            occurrences
        )
        if shared_hosts:
            shared_leveldata_hosts_by_story[black_key].extend(shared_hosts)
        if black_key not in all_story_entry_keys:
            continue
        story_owner = story_owner_by_key.get(black_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            if black_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            area_hosts = [
                host
                for row in scoped_occurrences
                for host in row.get("missionAreaLevelDataHosts") or []
            ]
            connection = {
                "key": black_key,
                "kind": story_kind_by_key.get(black_key, "black"),
                "relation": "mission_area_leveldata_mission_context",
                "direction": "context",
                "phase": "runtime_playback",
                "confidence": "native_exact_area_root_host",
                "source": (
                    "current-build NarrativeBlackScreen action + exact line id + "
                    "typed MissionAreaTrackingInfo/MissionAreaTable sub-data parent "
                    "root in the same validated LevelData member-22 dictionary"
                ),
                "storyOwnerMission": story_owner,
                "missionAreaHostMissionId": target_mission,
                "executionSide": "client",
                "networkRole": "local_presentation",
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "textIds": sorted({
                    str(line_id)
                    for row in scoped_occurrences
                    for line_id in row.get("lineIds") or []
                    if line_id
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for host in area_hosts
                    if host.get("levelDataFile")
                }),
                "missionAreaIds": sorted({
                    str(reference.get("missionAreaId") or "")
                    for host in area_hosts
                    for reference in host.get("missionAreaReferences") or []
                    if reference.get("missionAreaId")
                }),
                "subDataParentIds": sorted({
                    str(root_id)
                    for host in area_hosts
                    for root_id in host.get("rootScriptIds") or []
                    if root_id
                }),
                "missionAreaSourceFiles": sorted({
                    str(reference.get("sourceFile") or "")
                    for host in area_hosts
                    for reference in host.get("missionAreaReferences") or []
                    if reference.get("sourceFile")
                }),
                "nativeBlackActionOccurrences": scoped_occurrences,
            }
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    def authoritative_scope_leveldata_occurrences(
        occurrences: list[dict],
    ) -> tuple[dict[str, list[dict]], list[dict]]:
        scoped: dict[str, list[dict]] = defaultdict(list)
        shared: list[dict] = []
        for occurrence in occurrences:
            pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            host_evidence = authoritative_scope_leveldata_script_hosts.get(pair)
            if not host_evidence:
                continue
            if host_evidence.get("status") != "unique":
                shared.append({
                    **host_evidence,
                    "scopeMode": "authoritative_scope_validated_leveldata_shell",
                })
                continue
            host_missions = list(host_evidence.get("hostMissionIds") or [])
            if len(host_missions) != 1:
                continue
            target_mission = str(host_missions[0] or "")
            if target_mission not in mission_flows_payload:
                continue
            enriched = dict(occurrence)
            enriched["authoritativeScopeLevelDataHosts"] = list(
                host_evidence.get("hosts") or []
            )
            enriched["scopeEvidenceKinds"] = [
                "authoritative_reference_in_same_validated_leveldata_dictionary"
            ]
            scoped[target_mission].append(enriched)
        return scoped, shared

    # A condition/tracked script can be a sibling of the playback script in
    # one complete, validated LevelData member-22 dictionary.  Union every
    # authoritative mission reference in that dictionary and require exactly
    # one mission before attaching the playback file to that mission shell.
    # The anchor quest remains evidence only: sibling containment does not
    # prove which quest starts playback or create chronology.
    for story_key, occurrences in sorted({
        **native_story_playback_index,
        **native_black_action_index,
    }.items()):
        if story_key not in all_story_entry_keys:
            continue
        scoped_by_mission, shared_hosts = (
            authoritative_scope_leveldata_occurrences(occurrences)
        )
        if shared_hosts:
            shared_leveldata_hosts_by_story[story_key].extend(shared_hosts)
        if not native_fmv_scope_is_complete(
            occurrences,
            scoped_by_mission,
            shared_hosts,
        ):
            continue
        story_owner = story_owner_by_key.get(story_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            if story_key in preexisting_attached_story_keys_by_mission[target_mission]:
                continue
            shell_hosts = [
                host
                for occurrence in scoped_occurrences
                for host in occurrence.get(
                    "authoritativeScopeLevelDataHosts",
                    [],
                )
            ]
            authoritative_references = [
                reference
                for host in shell_hosts
                for reference in host.get("authoritativeReferences") or []
            ]
            connection = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "story"),
                "relation": "authoritative_scope_leveldata_mission_context",
                "direction": "context",
                "phase": "runtime_playback",
                "confidence": "native_exact_validated_leveldata_shell",
                "evidenceTier": "derived_exact_shell",
                "source": (
                    "typed MissionRuntime script condition, exact EntityTracking "
                    "registry script, typed InteractiveCheckInt logic id resolved "
                    "as one current-build registry script entity, typed MissionArea "
                    "parent root, or exact mission-named LevelData host scopes the "
                    "complete validated member-22 dictionary to one mission; this "
                    "typed playback script is a sibling entry in that same asset "
                    "shell, not a quest trigger"
                ),
                "storyOwnerMission": story_owner,
                "levelDataHostMissionId": target_mission,
                "questTriggerStatus": "sibling_script_shell_context_not_playback",
                "executionSide": "client",
                "networkRole": "local_asset_shell_context",
                "serverExchange": False,
                "occurrenceCount": len(scoped_occurrences),
                "allOccurrenceCount": len(occurrences),
                "hasUnscopedOrOtherMissionOccurrences": (
                    len(scoped_occurrences) < len(occurrences)
                ),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in scoped_occurrences
                    if row.get("actionName")
                }),
                **native_black_control_summary(scoped_occurrences),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in scoped_occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in scoped_occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in scoped_occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in scoped_occurrences
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for host in shell_hosts
                    if host.get("levelDataFile")
                }),
                "levelDataDictionaryEntryCounts": sorted({
                    int(host.get("dictionaryEntryCount"))
                    for host in shell_hosts
                    if isinstance(host.get("dictionaryEntryCount"), int)
                }),
                "authoritativeScopeKinds": sorted({
                    str(reference.get("scopeKind") or "")
                    for reference in authoritative_references
                    if reference.get("scopeKind")
                }),
                "anchorQuestIds": sorted({
                    str(reference.get("questId") or "")
                    for reference in authoritative_references
                    if reference.get("questId")
                }),
                "anchorScriptIds": sorted({
                    str(reference.get("scriptId") or "")
                    for reference in authoritative_references
                    if reference.get("scriptId")
                }),
                "authoritativeScopeReferences": authoritative_references,
                "levelScriptOccurrences": scoped_occurrences,
            }
            text_ids = sorted({
                str(line_id)
                for row in scoped_occurrences
                for line_id in row.get("lineIds") or []
                if line_id
            })
            if text_ids:
                connection["textIds"] = text_ids
            mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            ).append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # Timeline containment receives mission scope through the parent dialog's
    # typed native playback and exact LevelData host.  This also supports
    # runtime-registered parent dialogs with no emitted ordinary text lines.
    for (black_key, dialog_key), attachment_rows in sorted(black_timeline_groups.items()):
        parent_occurrences = list(native_story_playback_index.get(dialog_key) or [])
        scoped_by_mission, shared_hosts = leveldata_scoped_occurrences(parent_occurrences)
        if shared_hosts:
            shared_leveldata_hosts_by_story[black_key].extend({
                **row,
                "parentStoryKey": dialog_key,
            } for row in shared_hosts)
        story_owner = story_owner_by_key.get(black_key) or ""
        for target_mission, scoped_occurrences in sorted(scoped_by_mission.items()):
            connection = {
                "key": black_key,
                "kind": story_kind_by_key.get(black_key, "black"),
                "relation": "timeline_dialog_contains_black",
                "direction": "context",
                "phase": "timeline_contained",
                "confidence": "native_exact_host",
                "source": (
                    "serialized black playable/track/Actor containment + exact "
                    "DialogIdTable timeline owner + typed parent-dialog playback + "
                    "exact same-level validated Mission LevelData BriefData host"
                ),
                "storyOwnerMission": story_owner,
                "levelDataHostMissionId": target_mission,
                "parentStoryKey": dialog_key,
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(attachment_rows),
                "textIds": sorted({
                    str(row.get("textId") or "")
                    for row in attachment_rows
                    if row.get("textId")
                }),
                "timelines": sorted({
                    str(row.get("timeline") or "")
                    for row in attachment_rows
                    if row.get("timeline")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in attachment_rows
                    if row.get("sourceFile")
                }),
                "levelDataFiles": sorted({
                    str(host.get("levelDataFile") or "")
                    for row in scoped_occurrences
                    for host in row.get("levelDataHosts") or []
                    if host.get("levelDataFile")
                }),
                "assetPaths": sorted({
                    str(row.get("assetPath") or "")
                    for row in attachment_rows
                    if row.get("assetPath")
                }),
                "trackPaths": sorted({
                    str(row.get("trackPath") or "")
                    for row in attachment_rows
                    if row.get("trackPath")
                }),
                "rootPaths": sorted({
                    str(row.get("rootPath") or "")
                    for row in attachment_rows
                    if row.get("rootPath")
                }),
                "timelineAttachments": attachment_rows,
                "parentDialogNativeOccurrences": scoped_occurrences,
            }
            connections = mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            )
            signature = (black_key, connection["relation"], dialog_key)
            if any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("parentStoryKey") or ""),
            ) == signature for existing in connections if isinstance(existing, dict)):
                continue
            connections.append(connection)
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    # Apply exact system-feature carriers only after every stronger attachment
    # family.  This is a positive typed/native relation, but still mission-shell
    # context rather than quest placement, and it must never duplicate a Story
    # file already attached elsewhere.
    attach_unconnected_mission_shell_fallbacks(
        mission_flows_payload,
        preexisting_attached_story_keys_by_mission,
        pending_original_system_story_connections,
    )

    # Apply the NPC-proxy segment fallback only now, after every stronger
    # native/original-data family above has materialized its mission and quest
    # connections. This keeps it available to the DialogTree parent pass below
    # while preventing a broad asset-segment relation from duplicating or
    # suppressing direct bindings discovered later in the build sequence.
    attach_unconnected_mission_shell_fallbacks(
        mission_flows_payload,
        preexisting_attached_story_keys_by_mission,
        pending_npc_proxy_segment_connections,
    )

    # A black playable can inherit mission-shell context from its exact parent
    # dialog even when that dialog's LevelScript lives in a broad level shell.
    # Restrict this to direct original-data parent relations and require one
    # unique mission; quest placement remains unresolved when the parent is
    # attached to more than one quest.
    direct_parent_context_relations = {
        "leveldata_levelscript_mission_context",
        "mission_area_leveldata_mission_context",
        "levelscript_mission_context",
        "mission_accept_dialog",
        "npc_proxy_ex_mission_context",
        "mission_global_var_native_playback_context",
        "npc_proxy_wait_native_playback_context",
        "npc_proxy_target_native_playback_context",
        "npc_proxy_segment_levelscript_mission_context",
        "mission_state_processing_native_playback_context",
    }
    direct_parent_contexts: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for context_mission, flow_payload in mission_flows_payload.items():
        for row in flow_payload.get("missionStoryConnections") or []:
            if not isinstance(row, dict):
                continue
            parent_key = str(row.get("key") or "")
            relation = str(row.get("relation") or "")
            if parent_key and relation in direct_parent_context_relations:
                direct_parent_contexts[parent_key][context_mission].append(row)
        # EntityTracking relations live inside the exact quest that authored
        # the tracking hint, but are still context-only. Expose their owning
        # mission here so nested DialogTree narrative actions may inherit one
        # unambiguous mission shell without turning navigation into playback.
        for quest in flow_payload.get("quests") or []:
            for row in quest.get("storyConnections") or []:
                if not isinstance(row, dict):
                    continue
                parent_key = str(row.get("key") or "")
                relation = str(row.get("relation") or "")
                if parent_key and relation in entity_tracking_relations:
                    direct_parent_contexts[parent_key][context_mission].append(row)

    # DialogTree nesting can use the exact typed MissionArea/position context
    # of its parent dialog as a veto/agreement signal. Keep this in a dedicated
    # index: the older Timeline inheritance rule deliberately has a narrower
    # accepted relation set and must not change as a side effect.
    dialog_tree_parent_contexts: dict[str, dict[str, list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for parent_key, contexts_by_mission in direct_parent_contexts.items():
        for context_mission, rows in contexts_by_mission.items():
            dialog_tree_parent_contexts[parent_key][context_mission].extend(rows)
    dialog_tree_extra_parent_relations = {
        "mission_area_trigger_volume_story_context",
        "pos_tracking_trigger_center_story_context",
    }
    for context_mission, flow_payload in mission_flows_payload.items():
        connection_lists = [flow_payload.get("missionStoryConnections") or []]
        connection_lists.extend(
            quest.get("storyConnections") or []
            for quest in flow_payload.get("quests") or []
            if isinstance(quest, dict)
        )
        for connections in connection_lists:
            for row in connections:
                if not isinstance(row, dict):
                    continue
                parent_key = str(row.get("key") or "")
                relation = str(row.get("relation") or "")
                if parent_key and relation in dialog_tree_extra_parent_relations:
                    dialog_tree_parent_contexts[parent_key][context_mission].append(row)

    # A typed narrative-mask action is part of its exact parent DialogTree.
    # Propagate it to a quest only when the parent itself has one unique direct
    # original-data quest placement.  Derived one-hop graph/LevelScript routes
    # and OCR/manual/gameplay ordering are intentionally excluded.
    direct_parent_quest_relations = {
        "client_action_start",
        "client_action_succeed",
        "entity_tracking_world_interactive_dialog_context",
        "failure_condition",
        "levelscript_quest_completed_action",
        "objective_condition",
    }
    derived_parent_quest_relations = {
        "levelscript_condition_scope",
        "levelscript_story_sequence",
        "entity_tracking_interactive_story_target",
        # Exact recovered variant-MissionRuntime placement is context-only.
        # Multiple such quests may select their one shared mission shell, but
        # can never choose a favorable quest for an inherited carrier.
        "variant_runtime_attachment",
    }
    direct_parent_quests: dict[str, dict[tuple[str, str], list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    derived_parent_quests: dict[str, dict[tuple[str, str], list[dict]]] = defaultdict(
        lambda: defaultdict(list)
    )
    dialog_tree_carrier_context_quests: dict[
        str,
        dict[tuple[str, str], list[dict]],
    ] = defaultdict(lambda: defaultdict(list))
    dialog_tree_carrier_context_quest_relations = {
        # Exact NpcProxyEx dialog plus the quest's typed tracking proxy. This
        # is quest context rather than proof that the quest launches playback.
        "npc_proxy_ex_attachment",
        # One exact typed tracking row resolves through the same-scene proxy
        # tables/registry to a registered interaction parent and typed
        # next-dialog child. Navigation/configuration only, never activation.
        "npc_proxy_tracking_dialog_navigation_context",
        # The exact tracked proxy is configured with a lazy-destroy dialog;
        # native OnDeActive applies that id as an NPC interaction override.
        # This remains configuration context, not quest-trigger causality.
        "npc_proxy_lazy_destroy_dialog_context",
    }
    quest_by_mission_and_id: dict[tuple[str, str], dict] = {}
    for context_mission, flow_payload in mission_flows_payload.items():
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict) or not quest.get("id"):
                continue
            quest_id = str(quest["id"])
            quest_by_mission_and_id[(context_mission, quest_id)] = quest
            for row in quest.get("storyConnections") or []:
                if not isinstance(row, dict):
                    continue
                parent_key = str(row.get("key") or "")
                relation = str(row.get("relation") or "")
                if parent_key and relation in direct_parent_quest_relations:
                    direct_parent_quests[parent_key][(context_mission, quest_id)].append(row)
                elif parent_key and relation in derived_parent_quest_relations:
                    derived_parent_quests[parent_key][(context_mission, quest_id)].append(row)
                elif parent_key and relation in dialog_tree_carrier_context_quest_relations:
                    dialog_tree_carrier_context_quests[parent_key][
                        (context_mission, quest_id)
                    ].append(row)

    def dialog_tree_story_playback_connection(
        story_key: str,
        dialog_key: str,
        occurrence_rows: list[dict],
        *,
        scope: dict,
        parent_scope_key: str,
    ) -> dict:
        carrier_quest_state_context = scope.get("carrierQuestStateContext")
        quest_evidence = str(scope.get("questEvidence") or "none")
        scope_kind = str(scope.get("scopeKind") or "mission")
        if carrier_quest_state_context:
            confidence = "native_exact_cross_story_quest_state_context"
            evidence_tier = "native_exact_context"
            quest_trigger_status = (
                "exact_multi_quest_branch_dependency_not_unique_trigger"
            )
        elif scope_kind == "quest" and quest_evidence == "direct":
            confidence = "native_exact_parent_quest"
            evidence_tier = "native_direct"
            quest_trigger_status = "exact_parent_quest_context_not_independent_trigger"
        elif scope_kind == "quest":
            confidence = "native_derived_exact_parent_quest"
            evidence_tier = "derived_exact_quest"
            quest_trigger_status = "exact_parent_quest_context_not_playback_trigger"
        elif quest_evidence == "derived" and not scope.get("missionContextRows"):
            confidence = "native_derived_exact_parent_shell"
            evidence_tier = "derived_exact_shell"
            quest_trigger_status = "unresolved_derived_exact_mission_shell"
        else:
            confidence = "native_exact_parent_mission_context"
            evidence_tier = "native_direct_mission_context"
            quest_trigger_status = "unresolved_parent_has_no_unique_quest"
        scope_rows = [
            *list(scope.get("questRows") or []),
            *list(scope.get("missionContextRows") or []),
        ]
        carrier_kinds = sorted({
            str(row.get("carrierKind") or "")
            for row in occurrence_rows
            if row.get("carrierKind")
        })
        has_trunk_carrier = "trunk" in carrier_kinds
        has_dialog_carrier = "dialog" in carrier_kinds
        native_consumers = []
        if has_trunk_carrier:
            native_consumers.extend([
                {
                    "method": "DTTrunkNodeData.get_trunkId",
                    "token": "0x06003977",
                    "address": "0x187292f78",
                },
                {
                    "method": "DialogPlayTrunkActionData.get_trunkId",
                    "token": "0x06003945",
                    "address": "0x18729799c",
                },
                {
                    "method": "DialogTreeTrunkNode.DoExecute",
                    "token": "0x06003bb4",
                    "address": "0x1872a74b4",
                },
                {
                    "method": "DialogTreeTrunkNode.FindTrunkIdForReplacement",
                    "token": "0x06003bb3",
                    "address": "0x1872a76f8",
                },
                {
                    "method": "DialogTreeTrunkNode._DoPlayTrunk",
                    "token": "0x06003bb6",
                    "address": "0x1872a80b8",
                },
                {
                    "method": "DialogPlayTrunkActionData.SetOverrideTrunkId",
                    "token": "0x06003955",
                    "address": "0x187297578",
                },
                {
                    "method": "DialogManager.PlayTrunkNode",
                    "token": "0x0600f785",
                    "address": "0x186e16cc8",
                },
            ])
        if has_dialog_carrier:
            native_consumers.extend([
                {
                    "method": "DialogTreeDialogNode.DoExecute",
                    "token": "0x06003b6e",
                    "address": "0x1872a3770",
                },
                {
                    "method": "DialogManager.PlayNextDialog",
                    "token": "0x0600f78e",
                    "address": "0x186e168e8",
                },
            ])
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "dialog_tree_reachable_story_playback",
            "direction": "context",
            "phase": "dialog_tree_story_playback",
            "confidence": confidence,
            "evidenceTier": evidence_tier,
            "source": (
                "registered installed-game DialogTree TextAsset contains an exact "
                "typed playback carrier in the directed ancestor/descendant "
                "closure of a current-parent trunk; the current binary executes "
                "that carrier locally, while registered parent scope comes from "
                "separate original mission data"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "parentStoryKey": dialog_key,
            "questTriggerStatus": quest_trigger_status,
            "storyBinding": True,
            "ownership": False,
            "possibleAuthoredRoute": True,
            "certainty": "authored_reachable",
            "carrierKinds": carrier_kinds,
            "executionSide": "client",
            "networkRole": "local_dialog_tree_story_playback",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "serverEvidenceStatus": (
                "the recovered typed carrier paths end in local DialogManager "
                "playback and contain no network request"
            ),
            "occurrenceCount": len(occurrence_rows),
            "trunkIds": sorted({
                str(row.get("trunkId") or "")
                for row in occurrence_rows
                if row.get("trunkId")
            }),
            "dialogIds": sorted({
                str(row.get("dialogId") or "")
                for row in occurrence_rows
                if row.get("dialogId")
            }),
            "sourceFiles": sorted({
                str(row.get("sourceFile") or "")
                for row in occurrence_rows
                if row.get("sourceFile")
            }),
            "sourcePathIds": sorted({
                str(row.get("sourcePathId") or "")
                for row in occurrence_rows
                if row.get("sourcePathId")
            }),
            "parentScopeRelations": sorted({
                str(row.get("relation") or "")
                for row in scope_rows
                if isinstance(row, dict) and row.get("relation")
            }),
            "dialogTreeStoryPlaybackCarriers": occurrence_rows,
            "runtimeReplacementPossible": has_trunk_carrier,
            "runtimeReplacementNote": (
                "authored trunk ids may be replaced at runtime through "
                "FindTrunkIdForReplacement/SetOverrideTrunkId"
                if has_trunk_carrier
                else ""
            ),
            "nativeConsumers": native_consumers,
            "nativeMappingId": "dialog-tree-reachable-story-playback-native-v1",
        }
        if carrier_quest_state_context:
            connection.update({
                "source": (
                    "registered installed-game DialogTree contains exact typed "
                    "cross-Story playback carriers behind an all-leaf "
                    "CheckQuestState/CombineCondition gate that dominates every "
                    "serialized root-to-carrier path; all quest ids resolve to "
                    "one MissionRuntime"
                ),
                "dependencyOnly": True,
                "carrierQuestStateContext": carrier_quest_state_context,
                "missionStateGateRoles": ["DialogTree CheckQuestState"],
                "missionStateGatePredicates": [
                    (
                        f"{row.get('conditionPath')}._questId="
                        f"{row.get('questId')}; _comparer="
                        f"{row.get('comparer')}; _targetQuestState="
                        f"{row.get('targetQuestState')}"
                    )
                    for context in carrier_quest_state_context.get(
                        "questStateBranchContexts"
                    ) or []
                    for row in context.get("conditions") or []
                    if isinstance(row, dict)
                ],
                "upstreamServerStateSources": [
                    "SC_SYNC_ALL_MISSION",
                    "SC_QUEST_STATE_UPDATE",
                ],
                "nativeMappingId": (
                    "dialog-tree-cross-story-quest-state-carrier-native-v1"
                ),
            })
        npc_navigation_contexts = [
            row
            for row in scope_rows
            if isinstance(row, dict)
            and row.get("relation")
            == "npc_proxy_tracking_dialog_navigation_context"
        ]
        if npc_navigation_contexts:
            connection.update({
                "questTriggerStatus": (
                    "tracked_proxy_navigation_context_not_quest_playback"
                ),
                "npcProxyTrackingDialogContexts": npc_navigation_contexts,
                "questPlayback": False,
                "questCompletion": False,
                "trackingVisibilityRole": (
                    "navigation_marker_visibility_only_not_dialog_activation"
                ),
            })
        if parent_scope_key != dialog_key:
            connection["parentStoryOutKey"] = parent_scope_key
        candidate_quest_ids = list(scope.get("candidateQuestIds") or [])
        if candidate_quest_ids:
            connection["candidateQuestIds"] = candidate_quest_ids
        return connection

    # Freeze all accepted parent indexes above this point. The new connection
    # relation is intentionally absent from those sets, making inheritance
    # one-hop and non-transitive.
    attached_before_dialog_tree_playback = collect_globally_attached_story_keys(
        mission_flows_payload,
        preexisting_attached_story_keys_by_mission,
    )
    pending_dialog_tree_playback_groups = {
        pair: rows
        for pair, rows in dialog_tree_story_playback_groups.items()
        if pair[0] not in attached_before_dialog_tree_playback
    }
    scoped_dialog_tree_playback_pairs: set[tuple[str, str]] = set()
    unresolved_dialog_tree_playback_scopes: dict[tuple[str, str], dict] = {}
    strict_dialog_tree_mission_relations = {
        "mission_accept_dialog",
        "npc_proxy_ex_mission_context",
    }
    for (story_key, dialog_key), occurrence_rows in sorted(
        pending_dialog_tree_playback_groups.items()
    ):
        parent_scope_key = (
            resolve_scene_ref_out_key(dialog_key, all_story_entry_keys)
            or dialog_key
        )
        parent_direct_quests = direct_parent_quests.get(parent_scope_key) or {}
        parent_native_pairs = {
            (
                str(row.get("levelId") or ""),
                str(row.get("scriptId") or ""),
            )
            for row in native_story_playback_index.get(parent_scope_key) or []
            if row.get("levelId") and row.get("scriptId")
        }
        validated_derived_quests = {
            target: [
                row
                for row in rows
                if str(row.get("relation") or "") != "levelscript_condition_scope"
                or (
                    str(row.get("mapId") or ""),
                    str(row.get("scriptId") or ""),
                ) in parent_native_pairs
            ]
            for target, rows in (derived_parent_quests.get(parent_scope_key) or {}).items()
        }
        validated_derived_quests = {
            target: rows
            for target, rows in validated_derived_quests.items()
            if rows
        }
        for target, rows in (
            dialog_tree_carrier_context_quests.get(parent_scope_key) or {}
        ).items():
            validated_derived_quests.setdefault(target, []).extend(rows)
        strict_parent_contexts = {
            mission: [
                row
                for row in rows
                if str(row.get("relation") or "")
                in strict_dialog_tree_mission_relations
            ]
            for mission, rows in (
                direct_parent_contexts.get(parent_scope_key) or {}
            ).items()
        }
        strict_parent_contexts = {
            mission: rows
            for mission, rows in strict_parent_contexts.items()
            if rows
        }
        scope = select_cross_story_quest_state_carrier_scope(
            occurrence_rows,
            quest_targets,
        )
        if not scope.get("scopeKind"):
            scope = select_dialog_tree_story_carrier_scope(
                parent_direct_quests,
                validated_derived_quests,
                strict_parent_contexts,
            )
        if not scope.get("scopeKind"):
            unresolved_dialog_tree_playback_scopes[(story_key, dialog_key)] = scope
            continue
        target_mission = str(scope.get("missionId") or "")
        target_flow = mission_flows_payload.get(target_mission)
        if not isinstance(target_flow, dict):
            unresolved_dialog_tree_playback_scopes[(story_key, dialog_key)] = {
                **scope,
                "status": "missing_target_mission_flow",
            }
            continue
        connection = dialog_tree_story_playback_connection(
            story_key,
            dialog_key,
            occurrence_rows,
            scope=scope,
            parent_scope_key=parent_scope_key,
        )
        if scope.get("scopeKind") == "quest":
            target = (target_mission, str(scope.get("questId") or ""))
            quest = quest_by_mission_and_id.get(target)
            if not isinstance(quest, dict):
                unresolved_dialog_tree_playback_scopes[(story_key, dialog_key)] = {
                    **scope,
                    "status": "missing_target_quest",
                }
                continue
            connections = quest.setdefault("storyConnections", [])
        else:
            connections = target_flow.setdefault("missionStoryConnections", [])
        signature = (story_key, connection["relation"], dialog_key)
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("parentStoryKey") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        scoped_dialog_tree_playback_pairs.add((story_key, dialog_key))
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)

    # A fresh native DialogTree run enters serialized nodes[0] when no current
    # node exists. Keep this weaker containment tier separate from the exact
    # current-parent-trunk carrier above: MissionRuntime merely observes the
    # registered parent dialog's completion and does not prove that the quest
    # starts either the parent or child playback.
    attached_after_anchored_dialog_tree = collect_globally_attached_story_keys(
        mission_flows_payload,
        preexisting_attached_story_keys_by_mission,
    )
    unique_prime_parent_groups = unique_dialog_tree_prime_parent_groups(
        dialog_tree_prime_story_playback_groups
    )
    for story_key, (dialog_key, occurrence_rows) in sorted(
        unique_prime_parent_groups.items()
    ):
        if story_key in attached_after_anchored_dialog_tree:
            continue
        parent_completion_quests = (
            dialog_tree_completion_parent_quests.get(dialog_key) or {}
        )
        scope = select_dialog_tree_story_carrier_scope(
            parent_completion_quests,
            {},
            {},
        )
        if not scope.get("scopeKind"):
            continue
        target_mission = str(scope.get("missionId") or "")
        target_flow = mission_flows_payload.get(target_mission)
        if not isinstance(target_flow, dict):
            continue
        scope_rows = [
            row
            for rows in parent_completion_quests.values()
            for row in rows
            if isinstance(row, dict)
        ]
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "dialog_tree_prime_reachable_story_playback_dependency",
            "direction": "context",
            "phase": "dialog_tree_prime_reachable_story_playback",
            "confidence": (
                "native_exact_prime_reachable_parent_quest_dependency"
                if scope.get("scopeKind") == "quest"
                else "native_exact_prime_reachable_parent_mission_dependency"
            ),
            "evidenceTier": "native_exact_context",
            "source": (
                "registered current-game DialogTree; native fresh start falls "
                "back to serialized allNodes[0], and a directed typed connection "
                "path reaches this exact Story playback carrier; MissionRuntime "
                "only observes the parent dialog's CheckTalkOptionFinish and does "
                "not prove quest playback, activation, completion, or Story ownership"
            ),
            "storyBinding": True,
            "ownership": False,
            "dependencyOnly": True,
            "possibleAuthoredRoute": True,
            "certainty": "authored_prime_reachable",
            "questActivation": False,
            "questPlayback": False,
            "questCompletion": False,
            "questTriggerStatus": (
                "exact_parent_dialog_completion_context_not_quest_playback_trigger"
            ),
            "parentStoryKey": dialog_key,
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "executionSide": "client",
            "networkRole": "local_dialog_tree_story_playback",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "serverEvidenceStatus": (
                "parent completion is read from synchronized mission state; the "
                "prime-to-carrier route itself sends no request and expects no reply"
            ),
            "occurrenceCount": len(occurrence_rows),
            "parentScopeRelations": sorted({
                str(row.get("relation") or "")
                for row in scope_rows
                if row.get("relation")
            }),
            "objectiveConditionTypes": sorted({
                str(row.get("conditionType") or "")
                for row in scope_rows
                if row.get("conditionType")
            }),
            "finishIds": sorted({
                int(row.get("finishId"))
                for row in scope_rows
                if isinstance(row.get("finishId"), int)
                and not isinstance(row.get("finishId"), bool)
            }),
            "primeNodeIds": sorted({
                str(row.get("primeNodeId") or "")
                for row in occurrence_rows
                if row.get("primeNodeId")
            }),
            "primeNodeIndexes": sorted({
                int(row.get("primeNodeIndex"))
                for row in occurrence_rows
                if isinstance(row.get("primeNodeIndex"), int)
            }),
            "trunkIds": sorted({
                str(row.get("trunkId") or "")
                for row in occurrence_rows
                if row.get("trunkId")
            }),
            "dialogIds": sorted({
                str(row.get("dialogId") or "")
                for row in occurrence_rows
                if row.get("dialogId")
            }),
            "sourceFiles": sorted({
                str(row.get("sourceFile") or "")
                for row in occurrence_rows
                if row.get("sourceFile")
            }),
            "sourcePathIds": sorted({
                str(row.get("sourcePathId") or "")
                for row in occurrence_rows
                if row.get("sourcePathId")
            }),
            "dialogTreePrimeStoryPlaybackCarriers": occurrence_rows,
            "parentCompletionConditions": scope_rows,
            "nativeEntryMethods": [
                {"method": "DialogTreeController.StartDialog", "token": "0x06003a9b", "va": "0x1872a3454"},
                {"method": "DialogTreeController.StartDialogue()", "token": "0x06003a92", "va": "0x1872a35a8"},
                {"method": "DialogTreeController.StartDialogue(instigator,callback)", "token": "0x06003a96", "va": "0x1872a3604"},
                {"method": "NodeCanvas.Framework.Graph.StartGraph", "token": "0x06001120", "va": "0x18306edb0"},
                {"method": "NodeCanvas.Framework.Graph.get_primeNode", "token": "0x06001109", "va": "0x18306d980"},
                {"method": "DialogTree.get_requiresPrimeNode", "token": "0x06003a63", "va": "0x1872ac6a4"},
                {"method": "DialogTree.OnGraphStarted", "token": "0x06003a77", "va": "0x1872a969c"},
                {"method": "DialogTree.EnterNode", "token": "0x06003a75", "va": "0x1872a8ed4"},
            ],
            "nativeMappingId": (
                "dialog-tree-prime-reachable-completion-dependency-native-v1"
            ),
        }
        candidate_quest_ids = list(scope.get("candidateQuestIds") or [])
        if candidate_quest_ids:
            connection["candidateQuestIds"] = candidate_quest_ids
        if scope.get("scopeKind") == "quest":
            target = (target_mission, str(scope.get("questId") or ""))
            quest = quest_by_mission_and_id.get(target)
            if not isinstance(quest, dict):
                continue
            connections = quest.setdefault("storyConnections", [])
        else:
            connections = target_flow.setdefault("missionStoryConnections", [])
        signature = (story_key, connection["relation"], dialog_key)
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("parentStoryKey") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(story_key)
        attached_after_anchored_dialog_tree.add(story_key)

    # Preserve exact but unscoped carriers as a recovery frontier. They remain
    # unlinked and never count as a mission/quest binding.
    unresolved_playback_rows_by_story: dict[str, list[dict]] = defaultdict(list)
    for pair, occurrence_rows in pending_dialog_tree_playback_groups.items():
        if pair in scoped_dialog_tree_playback_pairs:
            continue
        story_key, dialog_key = pair
        unresolved_playback_rows_by_story[story_key].append({
            "parentStoryKey": dialog_key,
            "scope": unresolved_dialog_tree_playback_scopes.get(pair) or {
                "status": "unresolved_parent_scope",
            },
            "occurrences": occurrence_rows,
        })
    for story_key, parent_rows in sorted(unresolved_playback_rows_by_story.items()):
        owner_mission = story_owner_by_key.get(story_key) or ""
        owner_flow = mission_flows_payload.get(owner_mission)
        if not isinstance(owner_flow, dict):
            continue
        occurrences = [
            occurrence
            for parent_row in parent_rows
            for occurrence in parent_row["occurrences"]
        ]
        owner_flow.setdefault(
            "unresolvedDialogTreeStoryPlaybackCarriers",
            [],
        ).append({
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "dialog_tree_reachable_story_playback_unscoped",
            "direction": "context",
            "phase": "dialog_tree_story_playback",
            "confidence": "native_exact_playback_unscoped",
            "evidenceTier": "native_playback_without_mission_scope",
            "source": (
                "registered DialogTree has an exact anchored Story playback carrier, "
                "but original mission data does not select one accepted parent scope"
            ),
            "storyBinding": False,
            "ownership": False,
            "possibleAuthoredRoute": True,
            "executionSide": "client",
            "serverExchange": False,
            "parentStoryKeys": sorted({
                str(row.get("parentStoryKey") or "")
                for row in parent_rows
                if row.get("parentStoryKey")
            }),
            "parentScopes": [row["scope"] for row in parent_rows],
            "occurrenceCount": len(occurrences),
            "trunkIds": sorted({
                str(row.get("trunkId") or "")
                for row in occurrences
                if row.get("trunkId")
            }),
            "dialogIds": sorted({
                str(row.get("dialogId") or "")
                for row in occurrences
                if row.get("dialogId")
            }),
            "sourceFiles": sorted({
                str(row.get("sourceFile") or "")
                for row in occurrences
                if row.get("sourceFile")
            }),
            "dialogTreeStoryPlaybackCarriers": occurrences,
        })

    def dialog_tree_narrative_connection(
        black_key: str,
        dialog_key: str,
        occurrence_rows: list[dict],
        *,
        confidence: str,
        quest_trigger_status: str,
        evidence_tier: str,
    ) -> dict:
        left_subtitle_only = bool(occurrence_rows) and all(
            str(row.get("actionKind") or "") == "left_subtitle"
            for row in occurrence_rows
        )
        connection = {
            "key": black_key,
            "kind": story_kind_by_key.get(black_key, "black"),
            "relation": (
                "dialog_tree_left_subtitle_action"
                if left_subtitle_only
                else "dialog_tree_narrative_action"
            ),
            "direction": "context",
            "phase": (
                "dialog_left_subtitle"
                if left_subtitle_only
                else "dialog_narrative_mask"
            ),
            "confidence": confidence,
            "source": (
                (
                    "installed-game DialogTree TextAsset m_Script + exact native "
                    "DialogLeftSubtitleActionData text1..text4 LangKey fields + "
                    "separately classified original-data parent dialog scope"
                )
                if left_subtitle_only
                else (
                    "installed-game DialogTree TextAsset m_Script + exact native "
                    "DialogNarrativeMaskActionData/"
                    "DialogComplexNarrativeMaskActionData type and LangKey field + "
                    "separately classified original-data parent dialog scope"
                )
            ),
            "storyOwnerMission": story_owner_by_key.get(black_key) or "",
            "parentStoryKey": dialog_key,
            "questTriggerStatus": quest_trigger_status,
            "evidenceTier": evidence_tier,
            "clientPresentationOnly": True,
            "executionSide": "client",
            "networkRole": (
                "local_dialog_ui_left_subtitle"
                if left_subtitle_only
                else "local_dialog_narrative_presentation"
            ),
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "occurrenceCount": len(occurrence_rows),
            "textIds": sorted({
                str(row.get("textId") or "")
                for row in occurrence_rows
                if row.get("textId")
            }),
            "actionKinds": sorted({
                str(row.get("actionKind") or "")
                for row in occurrence_rows
                if row.get("actionKind")
            }),
            "actionTypes": sorted({
                str(row.get("actionType") or "")
                for row in occurrence_rows
                if row.get("actionType")
            }),
            "actionPaths": sorted({
                str(row.get("actionPath") or "")
                for row in occurrence_rows
                if row.get("actionPath")
            }),
            "sourceFiles": sorted({
                str(row.get("sourceFile") or "")
                for row in occurrence_rows
                if row.get("sourceFile")
            }),
            "sourcePathIds": sorted({
                str(row.get("sourcePathId") or "")
                for row in occurrence_rows
                if row.get("sourcePathId")
            }),
        }
        if left_subtitle_only:
            connection["textFields"] = sorted({
                str(row.get("textField") or "")
                for row in occurrence_rows
                if row.get("textField")
            })
            connection["dialogTreeLeftSubtitleActions"] = occurrence_rows
            connection["nativeConsumers"] = [
                {
                    "method": "DialogLeftSubtitleAction.OnPlay",
                    "token": "0x0600f682",
                    "address": "0x186e37bc8",
                },
                {
                    "method": "LangKey.GetText",
                    "token": "0x0600047e",
                    "address": "0x183036af0",
                },
                {
                    "method": "UILeftSubtitle.SetLeftSubTitle",
                    "token": "0x06000751",
                    "address": "0x18b0de1f4",
                },
            ]
            connection["serverEvidenceStatus"] = (
                "DialogLeftSubtitleAction.OnPlay sends a local global UI event; "
                "the shipped dialog Lua resolves each nonempty LangKey and the "
                "native subtitle widget renders it without a network request"
            )
        else:
            connection["dialogTreeNarrativeActions"] = occurrence_rows
            placement_statuses = sorted({
                str(row.get("dialogTreeConnectionPlacementStatus") or "")
                for row in occurrence_rows
                if row.get("dialogTreeConnectionPlacementStatus")
            })
            connection["dialogTreeConnectionPlacementStatuses"] = (
                placement_statuses
            )
            connection["embeddedAfterLineIds"] = sorted({
                str(line_id)
                for row in occurrence_rows
                for line_id in row.get("embeddedAfterLineIds") or []
                if line_id
            })
            connection["embeddedBeforeLineIds"] = sorted({
                str(line_id)
                for row in occurrence_rows
                for line_id in row.get("embeddedBeforeLineIds") or []
                if line_id
            })
            exact_embedded_placement = bool(occurrence_rows) and all(
                str(row.get("dialogTreeConnectionPlacementStatus") or "")
                == "exact_unique_adjacent_parent_trunks"
                and str(row.get("dialogKey") or "") == dialog_key
                and bool(row.get("embeddedAfterLineIds"))
                and bool(row.get("embeddedBeforeLineIds"))
                for row in occurrence_rows
            )
            connection["embeddedLinePlacementStatus"] = (
                "exact_complete_connection_neighbors"
                if exact_embedded_placement
                else "not_exact_complete_connection_neighbors"
            )
            connection["nativeMappingId"] = (
                "dialog-tree-narrative-mask-connection-native-v1"
            )
            connection["orderBoundary"] = (
                "the serialized DialogTree connections place the nested text "
                "between parent line nodes; because the parent Story file has "
                "content on both sides, this is line-level containment and "
                "does not establish a Story-file edge"
            )
        return connection

    dialog_tree_parents_by_black: dict[str, set[str]] = defaultdict(set)
    for black_key, dialog_key in dialog_tree_narrative_groups:
        dialog_tree_parents_by_black[black_key].add(dialog_key)

    scoped_dialog_tree_parent_pairs: set[tuple[str, str]] = set()
    for (black_key, dialog_key), occurrence_rows in sorted(
        dialog_tree_narrative_groups.items()
    ):
        # Runtime/Mission data uses emitted Story keys. Sub-scene DialogTree
        # ids such as `dlg_e7m2_1d5` are emitted as
        # `misc_dlg_e7m2_1d5`; normalize through the same exact Story-key
        # resolver used by MissionRuntime references before looking up scope.
        parent_scope_key = (
            resolve_scene_ref_out_key(dialog_key, all_story_entry_keys)
            or dialog_key
        )
        parent_quests = direct_parent_quests.get(parent_scope_key) or {}
        if len(parent_quests) == 1:
            target = next(iter(parent_quests))
            target_mission, _quest_id = target
            quest = quest_by_mission_and_id[target]
            connection = dialog_tree_narrative_connection(
                black_key,
                dialog_key,
                occurrence_rows,
                confidence="native_exact_parent_quest",
                quest_trigger_status="exact_unique_parent_quest",
                evidence_tier="native_direct",
            )
            if parent_scope_key != dialog_key:
                connection["parentStoryOutKey"] = parent_scope_key
            parent_rows = parent_quests[target]
            connection["parentScopeRelations"] = sorted({
                str(row.get("relation") or "")
                for row in parent_rows
                if row.get("relation")
            })
            connections = quest.setdefault("storyConnections", [])
            signature = (black_key, connection["relation"], dialog_key)
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("parentStoryKey") or ""),
            ) == signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            scoped_dialog_tree_parent_pairs.add((black_key, dialog_key))
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)
            continue

        # The installed data also exposes exact multi-hop quest routes. Keep
        # these visibly weaker than a direct MissionRuntime lifecycle field,
        # but do not discard them merely because the same black Story file is
        # authored in another parent dialog.
        parent_native_pairs = {
            (
                str(row.get("levelId") or ""),
                str(row.get("scriptId") or ""),
            )
            for row in native_story_playback_index.get(parent_scope_key) or []
            if row.get("levelId") and row.get("scriptId")
        }
        parent_derived_quests = {
            target: [
                row
                for row in rows
                if str(row.get("relation") or "") != "levelscript_condition_scope"
                or (
                    str(row.get("mapId") or ""),
                    str(row.get("scriptId") or ""),
                ) in parent_native_pairs
            ]
            for target, rows in (derived_parent_quests.get(parent_scope_key) or {}).items()
        }
        parent_derived_quests = {
            target: rows
            for target, rows in parent_derived_quests.items()
            if rows
        }
        if not parent_quests and len(parent_derived_quests) == 1:
            target = next(iter(parent_derived_quests))
            target_mission, _quest_id = target
            quest = quest_by_mission_and_id[target]
            connection = dialog_tree_narrative_connection(
                black_key,
                dialog_key,
                occurrence_rows,
                confidence="native_derived_exact_parent_quest",
                quest_trigger_status="exact_parent_quest_context_not_playback",
                evidence_tier="derived_exact_quest",
            )
            if parent_scope_key != dialog_key:
                connection["parentStoryOutKey"] = parent_scope_key
            parent_rows = parent_derived_quests[target]
            connection["parentScopeRelations"] = sorted({
                str(row.get("relation") or "")
                for row in parent_rows
                if row.get("relation")
            })
            connections = quest.setdefault("storyConnections", [])
            signature = (black_key, connection["relation"], dialog_key)
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("parentStoryKey") or ""),
            ) == signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            scoped_dialog_tree_parent_pairs.add((black_key, dialog_key))
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)
            continue

        # A nested narrative action may inherit the exact parent dialog's
        # independently validated LevelData mission shell. This closes the
        # containment chain without pretending that a local trigger/context
        # row proves one quest or that a Story filename proves ownership.
        # Native playback stores the authored DialogId (`dlg_*`), while a
        # sub-scene can be emitted as `misc_dlg_*` in Story. Consult both exact
        # aliases and deduplicate the same serialized action occurrence.
        parent_native_occurrences = collect_native_story_occurrences(
            native_story_playback_index,
            parent_scope_key,
            dialog_key,
        )
        parent_union_contexts = (
            dialog_tree_parent_contexts.get(parent_scope_key) or {}
        )
        parent_area_shells, shared_parent_area_shells = (
            mission_area_leveldata_scoped_occurrences(
                parent_native_occurrences
            )
        )
        target_mission, typed_parent_contexts = (
            select_unique_typed_mission_area_parent_mission(
                parent_area_shells,
                shared_parent_area_shells,
                len(parent_native_occurrences),
                parent_union_contexts,
            )
        )
        typed_mission_area_scope = bool(target_mission)
        if typed_mission_area_scope:
            parent_shells = parent_area_shells
            parent_scope_contexts = typed_parent_contexts
            parent_host_row_key = "missionAreaLevelDataHosts"
            parent_scope_relation = "mission_area_leveldata_mission_context"
        else:
            parent_shells, shared_parent_shells = leveldata_scoped_occurrences(
                parent_native_occurrences
            )
            target_mission = select_unique_original_parent_mission(
                parent_shells,
                shared_parent_shells,
                len(parent_native_occurrences),
                parent_union_contexts,
            )
            parent_scope_contexts = parent_union_contexts
            parent_host_row_key = "levelDataHosts"
            parent_scope_relation = "leveldata_levelscript_mission_context"
        if not parent_quests and target_mission:
            parent_occurrences = parent_shells[target_mission]
            connection = dialog_tree_narrative_connection(
                black_key,
                dialog_key,
                occurrence_rows,
                confidence=(
                    "native_derived_exact_parent_mission_area_shell"
                    if typed_mission_area_scope
                    else "native_derived_exact_parent_shell"
                ),
                quest_trigger_status="unresolved_derived_exact_mission_shell",
                evidence_tier="derived_exact_shell",
            )
            if parent_scope_key != dialog_key:
                connection["parentStoryOutKey"] = parent_scope_key
            context_rows = list(parent_scope_contexts.get(target_mission) or [])
            connection["parentScopeRelations"] = sorted({
                parent_scope_relation,
                *(
                    str(row.get("relation") or "")
                    for row in context_rows
                    if row.get("relation")
                ),
            })
            if typed_mission_area_scope:
                connection["missionAreaHostMissionId"] = target_mission
                connection["scopeEvidenceKinds"] = [
                    "typed_mission_area_subdata_parent_matches_validated_leveldata_root"
                ]
            else:
                connection["levelDataHostMissionId"] = target_mission
            connection["parentDialogNativeOccurrences"] = parent_occurrences
            connection["levelDataFiles"] = sorted({
                str(host.get("levelDataFile") or "")
                for row in parent_occurrences
                for host in row.get(parent_host_row_key) or []
                if host.get("levelDataFile")
            })
            connections = mission_flows_payload[target_mission].setdefault(
                "missionStoryConnections",
                [],
            )
            signature = (black_key, connection["relation"], dialog_key)
            if not any((
                str(existing.get("key") or ""),
                str(existing.get("relation") or ""),
                str(existing.get("parentStoryKey") or ""),
            ) == signature for existing in connections if isinstance(existing, dict)):
                connections.append(connection)
            scoped_dialog_tree_parent_pairs.add((black_key, dialog_key))
            preexisting_attached_story_keys_by_mission[target_mission].add(black_key)
            continue

        parent_mission_contexts = direct_parent_contexts.get(parent_scope_key) or {}
        direct_mission_relations = {
            "mission_accept_dialog",
            "npc_proxy_ex_mission_context",
        }
        strict_mission_contexts = {
            mission: [
                row
                for row in rows
                if str(row.get("relation") or "") in direct_mission_relations
            ]
            for mission, rows in parent_mission_contexts.items()
        }
        strict_mission_contexts = {
            mission: rows
            for mission, rows in strict_mission_contexts.items()
            if rows
        }
        candidate_missions = set(strict_mission_contexts)
        candidate_missions.update(mission for mission, _quest_id in parent_quests)
        evidence_tier = "native_direct_mission_context"
        confidence = "native_exact_parent_context"
        quest_trigger_status = "unresolved_parent_has_no_unique_quest"
        selected_parent_contexts = strict_mission_contexts
        if not candidate_missions:
            # Exact typed LevelScript playback plus a validated same-level
            # LevelData mission host is useful mission-shell context, but it is
            # a multi-hop asset chain rather than a direct lifecycle reference.
            # Keep it visibly weaker and never use it for quest placement.
            selected_parent_contexts = {
                mission: rows
                for mission, rows in parent_mission_contexts.items()
                if rows
            }
            candidate_missions = set(selected_parent_contexts)
            evidence_tier = "derived_exact_shell"
            confidence = "native_derived_exact_parent_shell"
            quest_trigger_status = "unresolved_derived_exact_mission_shell"
        if len(candidate_missions) != 1:
            continue
        target_mission = next(iter(candidate_missions))
        context_rows = list(
            selected_parent_contexts.get(target_mission) or []
        )
        for (quest_mission, _quest_id), rows in parent_quests.items():
            if quest_mission == target_mission:
                context_rows.extend(rows)
        connection = dialog_tree_narrative_connection(
            black_key,
            dialog_key,
            occurrence_rows,
            confidence=confidence,
            quest_trigger_status=quest_trigger_status,
            evidence_tier=evidence_tier,
        )
        if parent_scope_key != dialog_key:
            connection["parentStoryOutKey"] = parent_scope_key
        connection["parentScopeRelations"] = sorted({
            str(row.get("relation") or "")
            for row in context_rows
            if row.get("relation")
        })
        candidate_quest_ids = sorted({
            str(quest_id)
            for row in context_rows
            for quest_id in row.get("candidateQuestIds") or []
            if quest_id
        })
        if candidate_quest_ids:
            connection["candidateQuestIds"] = candidate_quest_ids
        connections = mission_flows_payload[target_mission].setdefault(
            "missionStoryConnections",
            [],
        )
        signature = (black_key, connection["relation"], dialog_key)
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("relation") or ""),
            str(existing.get("parentStoryKey") or ""),
        ) == signature for existing in connections if isinstance(existing, dict)):
            connections.append(connection)
        scoped_dialog_tree_parent_pairs.add((black_key, dialog_key))
        preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    for (black_key, dialog_key), attachment_rows in sorted(black_timeline_groups.items()):
        parent_contexts = direct_parent_contexts.get(dialog_key) or {}
        if len(parent_contexts) != 1:
            continue
        target_mission = next(iter(parent_contexts))
        if black_key in preexisting_attached_story_keys_by_mission[target_mission]:
            continue
        context_rows = parent_contexts[target_mission]
        connection = {
            "key": black_key,
            "kind": story_kind_by_key.get(black_key, "black"),
            "relation": "timeline_dialog_contains_black",
            "direction": "context",
            "phase": "timeline_contained",
            "confidence": "native_exact_parent_context",
            "source": (
                "serialized black playable/track/Actor containment + exact "
                "DialogIdTable timeline owner + unique direct original-data "
                "mission context of the parent dialog"
            ),
            "storyOwnerMission": story_owner_by_key.get(black_key) or "",
            "parentStoryKey": dialog_key,
            "questTriggerStatus": "unresolved_parent_has_no_unique_quest",
            "occurrenceCount": len(attachment_rows),
            "parentScopeRelations": sorted({
                str(row.get("relation") or "")
                for row in context_rows
                if row.get("relation")
            }),
            "textIds": sorted({
                str(row.get("textId") or "")
                for row in attachment_rows
                if row.get("textId")
            }),
            "timelines": sorted({
                str(row.get("timeline") or "")
                for row in attachment_rows
                if row.get("timeline")
            }),
            "sourceFiles": sorted({
                str(row.get("sourceFile") or "")
                for row in attachment_rows
                if row.get("sourceFile")
            }),
            "assetPaths": sorted({
                str(row.get("assetPath") or "")
                for row in attachment_rows
                if row.get("assetPath")
            }),
            "trackPaths": sorted({
                str(row.get("trackPath") or "")
                for row in attachment_rows
                if row.get("trackPath")
            }),
            "rootPaths": sorted({
                str(row.get("rootPath") or "")
                for row in attachment_rows
                if row.get("rootPath")
            }),
            "timelineAttachments": attachment_rows,
        }
        mission_flows_payload[target_mission].setdefault(
            "missionStoryConnections",
            [],
        ).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(black_key)

    # These residual native listeners carry no mission selector in their event
    # payloads. Recover quest context only when an independent,
    # typed original-data foreign-key chain closes that gap:
    # MissionRuntime condition EntityPtrs -> the exact same current-build
    # LevelScriptBriefData.refWorldEntity set -> the exact LevelScript whose
    # whitelisted exact native control path reaches this Story action.
    # Every entity must be unique to both one quest and one script across the
    # complete supplied corpora.  This proves shared authored entity context,
    # not that the quest or server activates the local trigger volume.
    world_entity_occurrences_by_story: dict[str, list[dict]] = defaultdict(list)
    world_entity_script_pairs: set[tuple[str, str]] = set()
    all_world_entity_action_occurrences_by_story: dict[
        str,
        list[dict],
    ] = defaultdict(list)
    all_world_entity_action_signatures_by_story: dict[str, set[tuple]] = (
        defaultdict(set)
    )
    for raw_story_key, occurrences in native_event_playback_index.items():
        story_key = resolve_scene_ref_out_key(
            raw_story_key,
            all_story_entry_keys,
        )
        if not story_key:
            continue
        for occurrence in occurrences:
            all_signature = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
                str(occurrence.get("sourceFile") or ""),
                occurrence.get("recordOffset"),
                str(occurrence.get("actionName") or ""),
            )
            if (
                all_signature
                not in all_world_entity_action_signatures_by_story[story_key]
            ):
                all_world_entity_action_signatures_by_story[story_key].add(
                    all_signature
                )
                all_world_entity_action_occurrences_by_story[story_key].append(
                    occurrence
                )
            matching_owner_rows = [
                {
                    "owner": owner,
                    "eventFamily": event_family,
                }
                for owner in occurrence.get("nativeEventOwners") or []
                if (event_family := classify_world_entity_story_receiver_owner(
                    owner
                ))
            ]
            pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            event_families = {
                row["eventFamily"] for row in matching_owner_rows
            }
            if (
                not matching_owner_rows
                or len(event_families) != 1
                or not all(pair)
            ):
                continue
            world_entity_occurrences_by_story[story_key].append({
                "occurrence": occurrence,
                "eventOwners": [row["owner"] for row in matching_owner_rows],
                "eventFamily": next(iter(event_families)),
            })
            world_entity_script_pairs.add(pair)

    receiver_world_entity_context = (
        build_leveldata_world_entity_quest_script_context(
            world_entity_script_pairs,
            world_entity_condition_groups,
            world_entity_condition_refs,
        )
    )
    globally_attached_before_world_entity = collect_globally_attached_story_keys(
        mission_flows_payload,
        preexisting_attached_story_keys_by_mission,
    )
    for story_key, occurrence_rows in sorted(
        world_entity_occurrences_by_story.items()
    ):
        resolved_rows: list[dict] = []
        for occurrence_row in occurrence_rows:
            occurrence = occurrence_row["occurrence"]
            pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            host = receiver_world_entity_context.get(pair) or {}
            candidates = list(host.get("candidates") or [])
            if host.get("status") != "unique" or len(candidates) != 1:
                continue
            resolved_rows.append({
                **occurrence_row,
                "context": candidates[0],
            })
        # Do not select a favorable subset when the same Story key has another
        # leader-trigger occurrence whose entity context remains unresolved.
        if len(resolved_rows) != len(occurrence_rows):
            continue
        mission_quest_pairs = {
            (
                str(row["context"].get("missionId") or ""),
                str(row["context"].get("questId") or ""),
            )
            for row in resolved_rows
        }
        if len(mission_quest_pairs) != 1:
            continue
        event_families = {
            str(row.get("eventFamily") or "")
            for row in resolved_rows
            if row.get("eventFamily")
        }
        if len(event_families) != 1:
            continue
        event_family = next(iter(event_families))
        resolved_pairs = {
            (
                str(row["occurrence"].get("levelId") or ""),
                str(row["occurrence"].get("scriptId") or ""),
            )
            for row in resolved_rows
        }
        if len(resolved_pairs) != 1:
            continue
        resolved_pair = next(iter(resolved_pairs))
        selected_signatures = {
            (
                str(row["occurrence"].get("levelId") or ""),
                str(row["occurrence"].get("scriptId") or ""),
                str(row["occurrence"].get("sourceFile") or ""),
                row["occurrence"].get("recordOffset"),
                str(row["occurrence"].get("actionName") or ""),
            )
            for row in resolved_rows
        }
        preload_occurrences: list[dict] = []
        invalid_unselected_occurrence = False
        for occurrence in all_world_entity_action_occurrences_by_story.get(
            story_key
        ) or []:
            occurrence_pair = (
                str(occurrence.get("levelId") or ""),
                str(occurrence.get("scriptId") or ""),
            )
            occurrence_signature = (
                occurrence_pair[0],
                occurrence_pair[1],
                str(occurrence.get("sourceFile") or ""),
                occurrence.get("recordOffset"),
                str(occurrence.get("actionName") or ""),
            )
            if occurrence_pair != resolved_pair:
                invalid_unselected_occurrence = True
                break
            if occurrence_signature in selected_signatures:
                continue
            if (
                occurrence.get("recordClass") == "preload_cutscene"
                and occurrence.get("actionName") == "PreloadCutsceneAction"
                and occurrence.get("nativeMappingId")
                == (
                    "gameassembly-2026-07-11-cr-0x18b9217d0-"
                    "actionbase-0x0000-0x0520"
                )
            ):
                preload_occurrences.append(occurrence)
                continue
            invalid_unselected_occurrence = True
            break
        if invalid_unselected_occurrence:
            continue
        target_mission, target_quest_id = next(iter(mission_quest_pairs))
        quest_target = quest_targets.get(target_quest_id)
        if (
            not target_mission
            or not target_quest_id
            or quest_target is None
            or quest_target[0] != target_mission
            or story_key in globally_attached_before_world_entity
        ):
            continue
        _quest_mission, quest = quest_target
        unique_contexts: dict[tuple[str, str, str], dict] = {}
        for row in resolved_rows:
            context = row["context"]
            unique_contexts.setdefault((
                str(context.get("levelId") or ""),
                str(context.get("scriptId") or ""),
                str((context.get("conditionGroup") or {}).get(
                    "groupType"
                ) or ""),
            ), context)
        contexts = list(unique_contexts.values())
        native_occurrences = [row["occurrence"] for row in resolved_rows]
        native_event_owners = [
            owner
            for row in resolved_rows
            for owner in row.get("eventOwners") or []
        ]
        leveldata_hosts = [
            host
            for context in contexts
            for host in context.get("levelDataHosts") or []
        ]
        condition_groups = [
            context.get("conditionGroup")
            for context in contexts
            if isinstance(context.get("conditionGroup"), dict)
        ]
        condition_refs = [
            ref
            for context in contexts
            for ref in context.get("conditionRefs") or []
        ]
        entity_resolutions = [
            resolution
            for context in contexts
            for resolution in context.get("entityScriptResolutions") or []
        ]
        registry_briefs = [
            brief
            for context in contexts
            for brief in context.get("worldEntityRegistryBriefs") or []
        ]
        registry_sources = {
            str(context.get("worldEntityRegistrySourceFile") or "")
            for context in contexts
            if context.get("worldEntityRegistrySourceFile")
        }
        stage_filters = sorted({
            int((owner.get("eventDetail") or {}).get("newStageFilter"))
            for owner in native_event_owners
            if isinstance(
                (owner.get("eventDetail") or {}).get("newStageFilter"),
                int,
            )
            and not isinstance(
                (owner.get("eventDetail") or {}).get("newStageFilter"),
                bool,
            )
        })
        if event_family == "ScriptEvent_OnScriptStageChanged":
            boundary = {
                "executionSide": "server_synced_client_runtime_playback",
                "networkRole": "server_to_client_stage_push_then_local_event",
                "serverExchange": True,
                "serverEvidenceStatus": (
                    "one_way_stage_push_without_mission_or_quest_identity; "
                    "condition_to_stage_causality_unproven"
                ),
                "serverMessage": "SC_SCENE_LEVEL_SCRIPT_STAGE_CHANGE",
                "serverFields": ["sceneNumId", "scriptId", "stage"],
                "clientRequest": False,
                "expectedClientReply": False,
                "expectedReturn": "none",
            }
        elif event_family == "EntityEvent_OnInteractiveStateChanged":
            boundary = {
                "executionSide": "local_entity_property_event_playback",
                "networkRole": "local_entity_property_event",
                "serverExchange": False,
                "serverEvidenceStatus": (
                    "no_packet_join_in_this_event_to_playback_path; "
                    "condition_to_property_event_causality_unproven"
                ),
            }
        else:
            boundary = {
                "executionSide": "local_trigger_volume_playback",
                "networkRole": "local_authored_trigger_volume_event",
                "serverExchange": False,
                "serverEvidenceStatus": (
                    "no_packet_or_server_activation_join_in_this_evidence_chain"
                ),
            }
        connection = {
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "story"),
            "relation": "leveldata_world_entity_quest_playback_context",
            "direction": "context",
            "phase": "runtime_playback",
            "confidence": "native_exact_world_entity_foreign_key",
            "evidenceTier": "derived_exact_foreign_key",
            "source": (
                "typed MissionRuntime WorldEntity condition group + exact "
                "same-level LevelScriptBriefData.refWorldEntity foreign keys "
                "+ exact whitelisted current-build receiver control "
                "path to this Story action; shared authored entity context "
                "only, not quest/server activation causality"
            ),
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "levelDataHostMissionId": target_mission,
            "questId": target_quest_id,
            "questTriggerStatus": (
                "shared_authored_world_entities_not_activation_proof"
            ),
            **boundary,
            "levelIds": sorted({
                str(row.get("levelId") or "")
                for row in native_occurrences
                if row.get("levelId")
            }),
            "scriptIds": sorted({
                str(row.get("scriptId") or "")
                for row in native_occurrences
                if row.get("scriptId")
            }, key=int),
            "entityLogicIds": sorted({
                str(entity_id)
                for context in contexts
                for entity_id in context.get("entityLogicIds") or []
            }, key=int),
            "entityDetailIds": sorted({
                str(brief.get("detailId") or "")
                for brief in registry_briefs
                if brief.get("detailId")
            }),
            "entityTypes": sorted({
                int(brief.get("entityType"))
                for brief in registry_briefs
                if isinstance(brief.get("entityType"), int)
                and not isinstance(brief.get("entityType"), bool)
            }),
            "conditionGroupTypes": sorted({
                str(group.get("groupType") or "")
                for group in condition_groups
                if group.get("groupType")
            }),
            "nativeActions": sorted({
                str(row.get("actionName") or "")
                for row in native_occurrences
                if row.get("actionName")
            }),
            "nativeEventNames": [event_family],
            "stageFilters": stage_filters,
            "triggerSlotIds": sorted({
                str(slot_id)
                for owner in native_event_owners
                for slot_id in owner.get("triggerSlotIds") or []
            }, key=int),
            "sourceFiles": sorted({
                *[
                    str(row.get("sourceFile") or "")
                    for row in native_occurrences
                ],
                *[
                    str(group.get("sourceFile") or "")
                    for group in condition_groups
                ],
                *[
                    str(host.get("levelDataFile") or "")
                    for host in leveldata_hosts
                ],
                *registry_sources,
            } - {""}),
            "missionRuntimeConditionGroups": condition_groups,
            "missionRuntimeConditionRefs": condition_refs,
            "worldEntityScriptResolutions": entity_resolutions,
            "worldEntityRegistryBriefs": registry_briefs,
            "levelDataHosts": leveldata_hosts,
            "nativeEventOwners": native_event_owners,
            "nativeOccurrences": native_occurrences,
            "preloadOccurrences": preload_occurrences,
        }
        quest.setdefault("storyConnections", []).append(connection)
        preexisting_attached_story_keys_by_mission[target_mission].add(
            story_key
        )
        globally_attached_before_world_entity.add(story_key)

    globally_attached_story_keys = {
        str(row.get("key") or "")
        for flow_payload in mission_flows_payload.values()
        for row in flow_payload.get("missionStoryConnections") or []
        if isinstance(row, dict) and str(row.get("key") or "") in all_story_entry_keys
    }
    globally_attached_story_keys.update(
        str(row.get("key") or "")
        for flow_payload in mission_flows_payload.values()
        for quest in flow_payload.get("quests") or []
        for row in quest.get("storyConnections") or []
        if isinstance(row, dict) and str(row.get("key") or "") in all_story_entry_keys
    )

    # Retain quest-state routing evidence only for Story files that stronger
    # original-data/native attachment families have not already explained.
    # This keeps the dependency layer focused on recovery gaps while preserving
    # its non-owning status: a branch condition explains route selection, not
    # which quest launched the registered dialog root.
    for carrier in pending_dialog_tree_quest_state_dependencies:
        story_key = str(carrier.get("dialogKey") or "")
        quest_id = str(carrier.get("questId") or "")
        quest_target = quest_targets.get(quest_id)
        if (
            not story_key
            or story_key not in all_story_entry_keys
            or story_key in globally_attached_story_keys
            or not quest_target
        ):
            continue
        target_mission, _quest = quest_target
        flow_payload = mission_flows_payload.get(target_mission)
        if not isinstance(flow_payload, dict):
            continue
        condition_rows = [
            row
            for row in carrier.get("conditions") or []
            if isinstance(row, dict)
        ]
        dependency = {
            **carrier,
            "key": story_key,
            "kind": story_kind_by_key.get(story_key, "dialog"),
            "relation": "dialog_tree_quest_state_dependency",
            "direction": "dependency",
            "phase": "dialog_branch_selection",
            "confidence": "typed_original_data_plus_native_quest_state_consumer",
            "evidenceTier": "direct",
            "source": (
                "typed DialogTree If/Branch condition co-carries the exact "
                "quest id and state comparator on an authored connection path "
                "to the registered dialog's current trunk"
            ),
            "sourceFiles": [str(carrier.get("sourceFile") or "")],
            "storyOwnerMission": story_owner_by_key.get(story_key) or "",
            "missionStateId": target_mission,
            "missionStateGateRoles": ["DialogTree CheckQuestState"],
            "missionStateGatePredicates": [
                (
                    f"{row.get('conditionPath')}._questId={quest_id}; "
                    f"_comparer={row.get('comparer')}; "
                    f"_targetQuestState={row.get('targetQuestState')}"
                )
                for row in condition_rows
            ],
            "questTriggerStatus": "exact_quest_state_dependency_without_ownership",
            "storyBinding": False,
            "ownership": False,
            "dependencyOnly": True,
            "executionSide": "client",
            "networkRole": "reads_synchronized_local_quest_state",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "upstreamServerStateSources": [
                "SC_SYNC_ALL_MISSION",
                "SC_QUEST_STATE_UPDATE",
            ],
            "upstreamServerStateRole": (
                "independent server pushes populate the local MissionSystem "
                "quest cache; evaluating the DialogTree condition sends no request"
            ),
            "serverEvidenceStatus": (
                "CheckQuestState.OnActivate reads MissionSystem.GetQuestState and "
                "TableUtils.DoCompare; _OnQuestStateChange observes later local cache "
                "updates, while If/Branch selects the authored outgoing connection"
            ),
            "nativeConsumers": [
                {
                    "method": "CheckQuestState.OnActivate",
                    "address": "0x18400f840",
                    "token": "0x060045c5",
                },
                {
                    "method": "CheckQuestState._OnQuestStateChange",
                    "address": "0x1873418f0",
                    "token": "0x060045c6",
                },
                {
                    "method": (
                        "DialogTreeIfNode._TrySelectIfBranch"
                        if carrier.get("nodeType")
                        == "Beyond.Gameplay.DialogTreeIfNode"
                        else "DialogTreeBranchNode._TrySelectBranch"
                    ),
                    "address": (
                        "0x1872a5280"
                        if carrier.get("nodeType")
                        == "Beyond.Gameplay.DialogTreeIfNode"
                        else "0x1872a1d0c"
                    ),
                    "token": (
                        "0x06003be4"
                        if carrier.get("nodeType")
                        == "Beyond.Gameplay.DialogTreeIfNode"
                        else "0x06003bd4"
                    ),
                },
            ],
            "nativeMappingId": "dialog-tree-check-quest-state-native-v1",
        }
        dependencies = flow_payload.setdefault(
            "missionStateStoryDependencies",
            [],
        )
        signature = (
            story_key,
            quest_id,
            str(dependency.get("sourceFile") or ""),
            str(dependency.get("nodeId") or ""),
        )
        if not any((
            str(existing.get("key") or ""),
            str(existing.get("questId") or ""),
            str(existing.get("sourceFile") or ""),
            str(existing.get("nodeId") or ""),
        ) == signature for existing in dependencies if isinstance(existing, dict)):
            dependencies.append(dependency)

    scoped_dialog_tree_parents_by_black: dict[str, set[str]] = defaultdict(set)
    for black_key, dialog_key in scoped_dialog_tree_parent_pairs:
        scoped_dialog_tree_parents_by_black[black_key].add(dialog_key)
    for flow_payload in mission_flows_payload.values():
        connection_lists = [flow_payload.get("missionStoryConnections") or []]
        connection_lists.extend(
            quest.get("storyConnections") or []
            for quest in flow_payload.get("quests") or []
            if isinstance(quest, dict)
        )
        for connections in connection_lists:
            for connection in connections:
                if not isinstance(connection, dict):
                    continue
                if connection.get("relation") not in {
                    "dialog_tree_narrative_action",
                    "dialog_tree_left_subtitle_action",
                }:
                    continue
                black_key = str(connection.get("key") or "")
                all_parents = sorted(
                    dialog_tree_parents_by_black.get(black_key) or set()
                )
                unscoped_parents = sorted(
                    set(all_parents)
                    - scoped_dialog_tree_parents_by_black.get(black_key, set())
                )
                connection["allParentStoryKeys"] = all_parents
                if unscoped_parents:
                    connection["unscopedParentStoryKeys"] = unscoped_parents
                    connection["scopeCompleteness"] = "partial"
                else:
                    connection["scopeCompleteness"] = "complete"

    # Keep every residual exact DialogTree containment visible after scoping.
    # A black Story file can be authored in multiple parent dialogs; one exact
    # parent use may be connected while another remains unresolved. Only files
    # with no connected parent stay in `unlinked`, while partial files retain
    # an explicit unresolved-use row for binary recovery follow-up.
    dialog_tree_occurrences_by_black: dict[str, list[dict]] = defaultdict(list)
    for (black_key, dialog_key), occurrence_rows in dialog_tree_narrative_groups.items():
        if (black_key, dialog_key) in scoped_dialog_tree_parent_pairs:
            continue
        dialog_tree_occurrences_by_black[black_key].extend(occurrence_rows)
    for black_key, occurrence_rows in sorted(dialog_tree_occurrences_by_black.items()):
        owner_mission = story_owner_by_key.get(black_key) or ""
        owner_flow = mission_flows_payload.get(owner_mission)
        if owner_flow is None:
            continue
        parent_story_keys = sorted({
            str(occurrence.get("dialogKey") or "")
            for occurrence in occurrence_rows
            if occurrence.get("dialogKey")
        })
        all_parent_story_keys = sorted(
            dialog_tree_parents_by_black.get(black_key) or set()
        )
        partially_scoped = black_key in globally_attached_story_keys
        parent_status = (
            "partially_scoped_parent_uses"
            if partially_scoped
            else "ambiguous_multiple_parent_dialogs"
            if len(parent_story_keys) > 1
            else "unique_parent_scope_unresolved"
        )
        left_subtitle_only = bool(occurrence_rows) and all(
            str(occurrence.get("actionKind") or "") == "left_subtitle"
            for occurrence in occurrence_rows
        )
        row = {
            "key": black_key,
            "kind": story_kind_by_key.get(black_key, "black"),
            "relation": (
                "dialog_tree_left_subtitle_action_unscoped"
                if left_subtitle_only
                else "dialog_tree_narrative_action_unscoped"
            ),
            "direction": "context",
            "phase": (
                "dialog_left_subtitle"
                if left_subtitle_only
                else "dialog_narrative_mask"
            ),
            "confidence": "native_exact_containment_unscoped",
            "evidenceTier": "native_containment_only",
            "source": (
                "installed-game DialogTree TextAsset contains exact typed "
                + (
                    "DialogLeftSubtitleActionData LangKeys"
                    if left_subtitle_only
                    else "narrative-action black LangKeys"
                )
                + ", but parent dialog ownership does not prove one accepted scope"
            ),
            "storyOwnerMission": owner_mission,
            "parentStoryKeys": parent_story_keys,
            "allParentStoryKeys": all_parent_story_keys,
            "parentStatus": parent_status,
            "questTriggerStatus": "unresolved",
            "partiallyScoped": partially_scoped,
            "clientPresentationOnly": True,
            "executionSide": "client",
            "serverExchange": False,
            "clientRequest": False,
            "expectedClientReply": False,
            "occurrenceCount": len(occurrence_rows),
            "textIds": sorted({
                str(occurrence.get("textId") or "")
                for occurrence in occurrence_rows
                if occurrence.get("textId")
            }),
            "actionKinds": sorted({
                str(occurrence.get("actionKind") or "")
                for occurrence in occurrence_rows
                if occurrence.get("actionKind")
            }),
            "actionTypes": sorted({
                str(occurrence.get("actionType") or "")
                for occurrence in occurrence_rows
                if occurrence.get("actionType")
            }),
            "actionPaths": sorted({
                str(occurrence.get("actionPath") or "")
                for occurrence in occurrence_rows
                if occurrence.get("actionPath")
            }),
            "sourceFiles": sorted({
                str(occurrence.get("sourceFile") or "")
                for occurrence in occurrence_rows
                if occurrence.get("sourceFile")
            }),
            "sourcePathIds": sorted({
                str(occurrence.get("sourcePathId") or "")
                for occurrence in occurrence_rows
                if occurrence.get("sourcePathId")
            }),
        }
        if left_subtitle_only:
            row["textFields"] = sorted({
                str(occurrence.get("textField") or "")
                for occurrence in occurrence_rows
                if occurrence.get("textField")
            })
            row["dialogTreeLeftSubtitleActions"] = occurrence_rows
        else:
            row["dialogTreeNarrativeActions"] = occurrence_rows
        if len(parent_story_keys) == 1:
            row["parentStoryKey"] = parent_story_keys[0]
        unresolved_field = (
            "unresolvedDialogTreeLeftSubtitleActions"
            if left_subtitle_only
            else "unresolvedDialogTreeNarrativeActions"
        )
        unlinked_field = (
            "unlinkedDialogTreeLeftSubtitleActions"
            if left_subtitle_only
            else "unlinkedDialogTreeNarrativeActions"
        )
        owner_flow.setdefault(unresolved_field, []).append(row)
        if not partially_scoped:
            owner_flow.setdefault(unlinked_field, []).append(row)

    for owner_mission, flow_payload in mission_flows_payload.items():
        owner_available = scene_keys_by_mission.get(owner_mission, set())
        for quest in flow_payload.get("quests") or []:
            if not isinstance(quest, dict):
                continue
            quest_available = set(owner_available)
            quest_available.update(
                str(row.get("key") or "")
                for row in quest.get("storyConnections") or []
                if isinstance(row, dict)
                and str(row.get("key") or "") in all_story_entry_keys
            )
            connections = quest_attached_story_connections(quest, quest_available)
            if connections:
                quest["storyConnections"] = connections
            else:
                quest.pop("storyConnections", None)
            story_files = quest_attached_story_files(quest, quest_available, connections)
            if story_files:
                quest["storyFiles"] = story_files
            else:
                quest.pop("storyFiles", None)
        unlinked = sorted(owner_available - globally_attached_story_keys)
        if unlinked:
            flow_payload["unlinked"] = unlinked
        else:
            flow_payload.pop("unlinked", None)
        native_unscoped_rows: list[dict] = []
        for story_key in unlinked:
            occurrences = list(native_story_playback_index.get(story_key) or [])
            native_relation = "native_story_playback_unscoped"
            if not occurrences:
                occurrences = list(native_black_action_index.get(story_key) or [])
                native_relation = "native_black_playback_unscoped"
            if not occurrences:
                continue
            native_unscoped_row = {
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "story"),
                "relation": native_relation,
                "direction": "context",
                "phase": "runtime_playback",
                "confidence": "native_typed_direct_unscoped",
                "source": (
                    "exact tagged Story id in an actionList record whose current-build "
                    "ActionBase formatter is a playback action; mission/quest trigger unresolved"
                ),
                "storyOwnerMission": owner_mission,
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(occurrences),
                "nativeActions": sorted({
                    str(row.get("actionName") or "")
                    for row in occurrences
                    if row.get("actionName")
                }),
                **native_black_control_summary(occurrences),
                "opcodes": sorted({
                    f"{row.get('actionCode')}/{row.get('actionKind')}"
                    for row in occurrences
                    if row.get("actionCode") and row.get("actionKind")
                }),
                "levelIds": sorted({
                    str(row.get("levelId") or "")
                    for row in occurrences
                    if row.get("levelId")
                }),
                "scriptIds": sorted({
                    str(row.get("scriptId") or "")
                    for row in occurrences
                    if row.get("scriptId")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in occurrences
                    if row.get("sourceFile")
                }),
                "nativeMappingId": str(
                    occurrences[0].get("nativeMappingId") or ""
                ),
                "occurrences": occurrences,
            }
            producer_routes = list(
                custom_event_story_producer_routes_by_story.get(story_key) or []
            )
            if producer_routes:
                native_unscoped_row.update({
                    "nativeEventProducerStatus": "exact_serialized_local_producer",
                    "producerScriptIds": sorted({
                        str(route.get("producerScriptId") or "")
                        for route in producer_routes
                        if route.get("producerScriptId")
                    }),
                    "listenerScriptIds": sorted({
                        str(script_id)
                        for route in producer_routes
                        for script_id in route.get("listenerScriptIds") or []
                        if script_id
                    }),
                    "raisedEventKeys": sorted({
                        str(route.get("raisedEventKey") or "")
                        for route in producer_routes
                        if route.get("raisedEventKey")
                    }),
                    "producerActions": sorted({
                        str(route.get("producerAction") or "")
                        for route in producer_routes
                        if route.get("producerAction")
                    }),
                    "producerReceiverModes": sorted({
                        str(route.get("receiverMode") or "")
                        for route in producer_routes
                        if route.get("receiverMode")
                    }),
                    "producerSourceFiles": sorted({
                        str(route.get("producerSourceFile") or "")
                        for route in producer_routes
                        if route.get("producerSourceFile")
                    }),
                    "nativeEventProducerRoutes": producer_routes,
                    "executionSide": "client",
                    "networkRole": "local_levelscript_event_dispatch",
                    "serverExchange": False,
                    "clientRequest": False,
                    "expectedClientReply": False,
                    "serverEvidenceStatus": (
                        "local_raise_custom_event_has_no_serialized_"
                        "mission_or_server_identity"
                    ),
                })
            battle_signal_routes = match_battle_signal_story_producers(
                story_key,
                occurrences,
                battle_signal_producer_index,
            )
            if battle_signal_routes:
                native_unscoped_row.update({
                    "nativeEventProducerStatus": (
                        "exact_ability_battle_signal_local_producer"
                    ),
                    "producerAssetIds": sorted({
                        str(route.get("producerAssetId") or "")
                        for route in battle_signal_routes
                        if route.get("producerAssetId")
                    }),
                    "producerDomains": sorted({
                        str(route.get("producerDomain") or "")
                        for route in battle_signal_routes
                        if route.get("producerDomain")
                    }),
                    "producerActions": ["SendBattleSignalToLevel"],
                    "producerSignals": sorted({
                        str(route.get("receiverSignalId") or "")
                        for route in battle_signal_routes
                        if route.get("receiverSignalId")
                    }),
                    "producerValues": sorted({
                        str((route.get("doubleValue") or {}).get("value"))
                        for route in battle_signal_routes
                        if (route.get("doubleValue") or {}).get("value")
                        is not None
                    }),
                    "producerSourceFiles": sorted({
                        str(route.get("producerSourceFile") or "")
                        for route in battle_signal_routes
                        if route.get("producerSourceFile")
                    }),
                    "nativeEventProducerRoutes": battle_signal_routes,
                    "executionSide": "client",
                    "networkRole": "local_ability_battle_signal_dispatch",
                    "serverExchange": False,
                    "clientRequest": False,
                    "expectedClientReply": False,
                    "serverEvidenceStatus": (
                        "local_battle_signal_has_no_serialized_"
                        "mission_or_server_identity"
                    ),
                })
            mission_state_routes = list(
                mission_state_story_routes_by_story.get(story_key) or []
            )
            if mission_state_routes:
                native_unscoped_row.update({
                    "missionStateGateStatus": (
                        "exact_native_gate_without_generated_mission_attachment"
                    ),
                    "missionStateGateMissionIds": sorted({
                        str(mission_id)
                        for route in mission_state_routes
                        for mission_id in route.get("gateMissionIds") or []
                        if mission_id
                    }),
                    "missionStateGateRoutes": mission_state_routes,
                    "executionSide": "client",
                    "networkRole": "reads_synchronized_local_mission_state",
                    "serverExchange": False,
                    "clientRequest": False,
                    "expectedClientReply": False,
                })
            shared_hosts = shared_leveldata_hosts_by_story.get(story_key) or []
            if shared_hosts:
                native_unscoped_row["sharedLevelDataHosts"] = shared_hosts
                native_unscoped_row["levelDataHostStatus"] = "shared"
            native_unscoped_rows.append(native_unscoped_row)
        if native_unscoped_rows:
            flow_payload["unlinkedNativePlayback"] = native_unscoped_rows
        else:
            flow_payload.pop("unlinkedNativePlayback", None)
        unresolved_timeline_rows: list[dict] = []
        for story_key in unlinked:
            attachments = unresolved_black_timeline_attachments.get(story_key) or []
            if not attachments:
                continue
            unresolved_timeline_rows.append({
                "key": story_key,
                "kind": story_kind_by_key.get(story_key, "black"),
                "relation": "timeline_black_root_unresolved",
                "direction": "context",
                "phase": "timeline_contained",
                "confidence": "authored_root_unscoped",
                "source": (
                    "serialized black-screen text playable and owning Timeline Actor root; "
                    "no exact recovered root-to-dialog mapping"
                ),
                "storyOwnerMission": owner_mission,
                "questTriggerStatus": "unresolved",
                "occurrenceCount": len(attachments),
                "textIds": sorted({
                    str(row.get("textId") or "")
                    for row in attachments
                    if row.get("textId")
                }),
                "timelines": sorted({
                    str(row.get("timeline") or "")
                    for row in attachments
                    if row.get("timeline")
                }),
                "sourceFiles": sorted({
                    str(row.get("sourceFile") or "")
                    for row in attachments
                    if row.get("sourceFile")
                }),
                "attachments": attachments,
            })
        if unresolved_timeline_rows:
            flow_payload["unlinkedTimelineContainment"] = unresolved_timeline_rows
        else:
            flow_payload.pop("unlinkedTimelineContainment", None)
        definition_only_black_rows: list[dict] = []
        for story_key in unlinked:
            if story_kind_by_key.get(story_key) != "black":
                continue
            if native_story_playback_index.get(story_key):
                continue
            if native_black_action_index.get(story_key):
                continue
            if unresolved_black_timeline_attachments.get(story_key):
                continue
            if story_key in recovered_black_timeline_keys:
                continue
            if story_key in recovered_dialog_tree_narrative_keys:
                continue
            definition_only_black_rows.append({
                "key": story_key,
                "kind": "black",
                "relation": "original_text_definition_without_consumer",
                "direction": "context",
                "phase": "definition_only",
                "confidence": "current_build_no_consumer",
                "source": (
                    "original TextTable definition exists, but no current-build "
                    "LevelScript black-screen playback action, typed DialogTree "
                    "narrative-mask action, or serialized Timeline black-text "
                    "playable references it"
                ),
                "nominalStoryGroup": owner_mission,
                "consumerSearchStatus": (
                    "no_current_original_game_consumer_recovered"
                ),
                "searchedConsumerKinds": [
                    "LevelScript ActionBase black-screen playback actions",
                    "DialogTree narrative-mask actions",
                    "Timeline subtitle and center-text playables",
                ],
                "bindingStatus": "definition_only_unlinked",
                "serverEvidenceStatus": (
                    "no_runtime_consumer_or_network_edge_recovered"
                ),
            })
        if definition_only_black_rows:
            flow_payload["unlinkedDefinitionOnly"] = definition_only_black_rows
        else:
            flow_payload.pop("unlinkedDefinitionOnly", None)
    mission_timeline_json = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.json"
    mission_timeline_md = REPORTS_DIR / f"mission_timeline_recovery_{language_code}.md"
    write_mission_timeline_recovery_json(
        mission_timeline_json,
        mission_timeline_recovery_payload,
    )
    mission_timeline_md.parent.mkdir(parents=True, exist_ok=True)
    mission_timeline_md.write_text(
        render_mission_timeline_markdown(mission_timeline_recovery_payload),
        encoding="utf-8",
    )
    mission_timeline_report = {
        "json": repo_rel(mission_timeline_json),
        "markdown": repo_rel(mission_timeline_md),
        "summary": mission_timeline_recovery_payload["summary"],
        "evidencePolicy": MISSION_TIMELINE_EVIDENCE_POLICY,
    }

    mission_data_files: dict[str, str] = {}
    mission_data_bytes = 0
    mission_data_missions = sorted(
        set(mission_extras_payload)
        | set(mission_flows_payload)
        | set(mission_timelines_by_mission)
    )
    story_order_overrides = _load_story_order_overrides(str(_STORY_ORDER_OVERRIDES_PATH))
    if mission_data_missions:
        mission_dir.mkdir(parents=True, exist_ok=True)
        used_mission_filenames: set[str] = set()
        for mission in mission_data_missions:
            filename = safe_mission_data_filename(mission, used_mission_filenames)
            rel_file = f"mission/{filename}"
            payload = {"mission": mission}
            if mission in mission_extras_payload:
                payload["extras"] = mission_extras_payload[mission]
            if mission in mission_flows_payload:
                payload["flow"] = mission_flows_payload[mission]
            if mission in mission_timelines_by_mission:
                timeline_recovery = mission_timelines_by_mission[mission]
                # Additive: per-scene static order confidence + phase, reusing the
                # resolution that yields the order-compare report's keyInfo.
                timeline_recovery["sceneOrderInfo"] = build_mission_scene_order_info(
                    mission_flows_payload.get(mission),
                    timeline_recovery.get("questSpatialTrack"),
                    timeline_recovery.get("quests"),
                    timeline_recovery.get("scenePlacement"),
                    build_mission_scene_order_candidate_kinds(
                        index_entries,
                        mission,
                        story_order_overrides.get(mission),
                    ),
                )
                payload["timelineRecovery"] = timeline_recovery
            out_path = write_mission_payload(rel_file, payload)
            mission_data_files[mission] = rel_file
            mission_data_bytes += out_path.stat().st_size
    def emit_webui_secret_notice() -> None:
        if language_code != "CN":
            return

        out_key = "black_webui_secret_notice"
        title = "Open-source notice"
        mission = "webui_secret"
        lines = [
            {
                "id": f"{out_key}_001",
                "text": "You found a small system notice in the corner.",
            },
            {
                "id": f"{out_key}_002",
                "text": (
                    "This WebUI code is free and open source: "
                    "Variante/endfield_research_kit "
                    "(https://github.com/Variante/endfield_research_kit). "
                    "No one should obtain this WebUI or its code through paid access."
                ),
            },
            {
                "id": f"{out_key}_003",
                "text": (
                    "Text, images, audio, video, models, and related content shown here "
                    "come from unpacked and organized Endfield game data. Rights to game "
                    "content belong to Hypergryph and the relevant rights holders. This "
                    "project is for research, organization, and browsing only."
                ),
            },
        ]
        payload = {
            "key": out_key,
            "kind": "black",
            "mission": mission,
            "scene": "notice",
            "title": title,
            "lines": lines,
            "_debug": {
                "source": {
                    "table": "WebUI synthetic notice",
                    "rowId": out_key,
                    "note": (
                        "Manual WebUI-only open-source and copyright notice "
                        "requested by the maintainer."
                    ),
                },
            },
        }
        write_conv_payload(out_key, payload)

        index_entries[:] = [entry for entry in index_entries if entry.get("k") != out_key]
        index_entries.append({
            "k": out_key,
            "d": "black",
            "m": mission,
            "s": 0,
            "t": "other",
            "a": 0,
            "title": title,
            "c": [],
            "n": len(lines),
            "p": preview(lines[0]["text"]),
            "tags": ["other", "webui"],
            "x": merge_search_text(
                merge_search_text(title, indexed_line_haystack(lines, "text")),
                "copyright open source free WebUI Variante endfield_research_kit GitHub Hypergryph Endfield",
            ),
        })

    emit_webui_secret_notice()
    generated = int(time.time())
    search_entries: list[dict] = []
    for entry in index_entries:
        search_text = str(entry.pop("x", "") or "").strip()
        if search_text:
            search_entries.append({
                "k": str(entry.get("k") or ""),
                "x": search_text,
            })
    write_json(out_dir / "actors.json", {
        "generated": generated,
        "language": language_code,
        "actorNames": actor_names,
    })
    write_json(out_dir / "missions.json", {
        "generated": generated,
        "language": language_code,
        "missionNames": mission_names,
    })
    write_json(out_dir / "search.json", {
        "generated": generated,
        "language": language_code,
        "entries": search_entries,
    })
    index_payload = {
        "generated": generated,
        "profile": profile,
        "actors": "actors.json",
        "missions": "missions.json",
        "search": "search.json",
        "entries": index_entries,
    }
    if write_reference and reference_stats:
        index_payload["reference"] = {
            "index": "reference/index.json",
            "stats": reference_stats,
            "reused": bool(reuse_reference),
        }
    if mission_data_files:
        index_payload["missionData"] = {
            "files": mission_data_files,
            "missions": len(mission_data_files),
            "bytes": mission_data_bytes,
        }
    index_payload["missionTimelineRecovery"] = mission_timeline_report
    if story_source_link_report:
        index_payload["storySourceLinks"] = {
            "sourceIndex": story_source_link_report.get("sourceIndex"),
            "summary": story_source_link_report.get("summary"),
            "report": story_source_link_report.get("report"),
        }
    if narrative_video_report:
        index_payload["narrativeVideos"] = {
            "summary": narrative_video_report.get("summary"),
            "report": narrative_video_report.get("report"),
        }
    if include_reference_in_story_index:
        index_payload["missionExtras"] = mission_extras_payload
        index_payload["missionFlows"] = mission_flows_payload
    write_json(out_dir / "index.json", index_payload)
    cleanup_stale_json(conv_dir, written_conv_paths)
    cleanup_stale_json(mission_dir, written_mission_paths)
    if write_reference and not reuse_reference:
        cleanup_stale_json(reference_dir, written_reference_paths)
    total_size = sum(p.stat().st_size for p in conv_dir.glob("*.json"))
    conv_count = len(list(conv_dir.glob("*.json")))
    index_path = out_dir / "index.json"
    mission_report_files = {
        mission: repo_rel(out_dir / rel_file)
        for mission, rel_file in mission_data_files.items()
    }
    scene_placement_index = shared_build_scene_placement_index_from_timelines(
        mission_timelines_by_mission,
        mission_files=mission_report_files,
    )
    scene_order_rows = shared_collect_scene_order_gap_rows_from_payloads(
        ROOT,
        sorted(scene_order_gap_sources.values(), key=lambda item: item[0].name),
        scene_placement_index=scene_placement_index,
        dialog_id_registry=dialog_id_registry,
    )
    scene_order_report = shared_write_scene_order_gap_reports(
        ROOT,
        REPORTS_DIR,
        language_code,
        conv_dir,
        rows=scene_order_rows,
    )
    inferred_anchor_report = shared_write_inferred_option_anchors_report(
        REPORTS_DIR,
        language_code,
        conv_dir,
        rows=list(inferred_option_anchor_rows_by_key.values()),
    )
    print(f"\n[{language_code}] Done in {time.time()-t0:.1f}s")
    print(f"  profile:       {profile}")
    print(f"  conversations: {len(index_entries)}")
    print(f"  actors:        {len(actor_names)}")
    print(f"  conv data:     {total_size/1024/1024:.1f} MB across {conv_count} files")
    if mission_data_files:
        print(f"  mission data:  {mission_data_bytes/1024/1024:.1f} MB across {len(mission_data_files)} files")
    print(
        "  mission timelines: "
        f"{mission_timeline_recovery_payload['summary']['missionCount']} missions, "
        f"{mission_timeline_recovery_payload['summary']['questCount']} quests"
    )
    if story_source_link_report:
        source_summary = story_source_link_report.get("summary") or {}
        print(
            "  source links:  "
            f"{source_summary.get('attachedKeys', 0)} keys, "
            f"{source_summary.get('attachedReferences', 0)} refs attached"
        )
    if narrative_video_report:
        video_summary = narrative_video_report.get("summary") or {}
        print(
            "  narrative vid: "
            f"{video_summary.get('attachedKeys', 0)} keys, "
            f"{video_summary.get('attachedVideos', 0)} refs attached"
        )
    if reference_stats:
        print(f"  reference:     {reference_stats.get('bytes', 0)/1024/1024:.1f} MB across {reference_stats.get('tables', 0)} tables")
    print(f"  index:         {index_path.stat().st_size/1024:.1f} KB")
    return {
        "language": language_code,
        "profile": profile,
        "conversations": len(index_entries),
        "actors": len(actor_names),
        "convBytes": total_size,
        "convFiles": conv_count,
        "missionDataBytes": mission_data_bytes,
        "missionDataFiles": len(mission_data_files),
        "missionTimelineRecoveryReport": mission_timeline_report["markdown"],
        "missionTimelineRecoveryData": mission_timeline_report["json"],
        "missionTimelineRecoveryMissions": mission_timeline_recovery_payload["summary"]["missionCount"],
        "missionTimelineRecoveryUnresolved": mission_timeline_recovery_payload["summary"].get("unresolvedByKind", {}),
        "referenceBytes": int(reference_stats.get("bytes", 0)) if reference_stats else 0,
        "referenceTables": int(reference_stats.get("tables", 0)) if reference_stats else 0,
        "referenceRows": int(reference_stats.get("rows", 0)) if reference_stats else 0,
        "referenceReused": bool(reuse_reference),
        "indexBytes": index_path.stat().st_size,
        "sceneOrderGapReport": repo_rel(scene_order_report["markdown"]),
        "sceneOrderGapData": repo_rel(scene_order_report["json"]),
        "sceneOrderGapCount": scene_order_report["summary"]["totalFlaggedScenes"],
        "inferredOptionAnchorsReport": repo_rel(inferred_anchor_report["markdown"]),
        "inferredOptionAnchorsData": repo_rel(inferred_anchor_report["json"]),
        "inferredOptionAnchorsScenes": inferred_anchor_report["summary"]["totalScenes"],
        "inferredOptionAnchorsGroups": inferred_anchor_report["summary"]["totalInferredGroups"],
        "narrativeVideoReport": str((narrative_video_report.get("report") or {}).get("markdown") or ""),
        "narrativeVideoData": str((narrative_video_report.get("report") or {}).get("json") or ""),
        "narrativeVideoKeys": int((narrative_video_report.get("summary") or {}).get("attachedKeys", 0)),
        "narrativeVideoRefs": int((narrative_video_report.get("summary") or {}).get("attachedVideos", 0)),
    }

__all__ = [name for name in globals() if not name.startswith("__")]





