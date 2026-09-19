from __future__ import annotations


def dialog_tree_story_playback_connection(
        story_key: str,
        dialog_key: str,
        occurrence_rows: list[dict],
        *,
        scope: dict,
        parent_scope_key: str,
        story_kind_by_key: dict[str, str],
        story_owner_by_key: dict[str, str],
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


def dialog_tree_narrative_connection(
        black_key: str,
        dialog_key: str,
        occurrence_rows: list[dict],
        *,
        confidence: str,
        quest_trigger_status: str,
        evidence_tier: str,
        story_kind_by_key: dict[str, str],
        story_owner_by_key: dict[str, str],
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


__all__ = [
    "dialog_tree_narrative_connection",
    "dialog_tree_story_playback_connection",
]
