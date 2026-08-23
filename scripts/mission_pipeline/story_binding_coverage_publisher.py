"""Publish a projected Story binding coverage report as JSON and Markdown."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable


def publish_report(
    report: dict[str, Any],
    *,
    report_root: Path,
    language: str,
    kind_counts: dict[str, Any],
    lua_playback_evidence: dict[str, Any],
    root_playback_alias_rows: list[dict[str, Any]],
    native_playback_event_keys: dict[str, Any],
    missionless_nodes: list[dict[str, Any]],
    evidence_tier_counts: dict[str, Any],
    connected_keys_by_evidence_tier: dict[str, Any],
    definition_only_classification: dict[str, Any],
    tracked_proxy_topology_failures: list[dict[str, Any]],
    json_writer: Callable[[Path, Any], None],
) -> dict[str, Any]:
    report_root.mkdir(parents=True, exist_ok=True)
    stem = f"mission_pipeline_story_binding_coverage_{language}"
    json_writer(report_root / f"{stem}.json", report)
    counts = report["counts"]
    lines = [
        f"# Mission Pipeline Story Binding Coverage ({language})",
        "",
        report["policy"],
        "",
        "## Summary",
        "",
        f"- Pipeline missions: `{counts['pipelineMissions']}`",
        f"- Unique Story files: `{counts['uniqueStoryFiles']}`",
        f"- Connected unique Story files: `{counts['connectedUniqueStoryFiles']}`",
        f"- Connected cross-owner Story files admitted by exact pipeline edges: `{counts['connectedCrossOwnerStoryFiles']}`",
        f"- Unlinked unique Story files: `{counts['unlinkedUniqueStoryFiles']}`",
        f"- Connected mission placements: `{counts['connectedMissionPlacements']}`",
        f"- Connection evidence rows: `{counts['connectionEvidenceRows']}`",
        f"- Normalized Story trigger/context routes: `{counts['storyTriggerRoutes']}`",
        f"- Validated tracked-proxy candidate topology contexts: `{counts['trackedProxyCandidateTopologyContexts']}` across `{counts['trackedProxyCandidateTopologyRoutes']}` dialog routes",
        f"- Those intersecting authored fork/merge structure: `{counts['trackedProxyCandidateTopologyBranchContexts']}` (fork-spanning `{counts['trackedProxyCandidateTopologyForkSpanningContexts']}`, merge `{counts['trackedProxyCandidateTopologyMergeContexts']}`)",
        f"- Tracked-proxy topology validation failures: `{counts['trackedProxyCandidateTopologyFailures']}`",
        f"- Story files with at least one normalized route: `{counts['storyFilesWithTriggerRoutes']}`",
        f"- Unlinked Story files with a known trigger/context route: `{counts['unlinkedStoryFilesWithTriggerRoutes']}`",
        f"- Shipped-Lua Story playback calls scanned: `{counts['scannedLuaStoryPlaybackCalls']}`",
        f"- Lua playback calls admitted: `{counts['acceptedLuaPlaybackCalls']}`",
        f"- Exact-case Lua playback calls admitted: `{counts['acceptedLuaExactCasePlaybackCalls']}`",
        f"- Unique case-insensitive Lua playback associations admitted: `{counts['acceptedLuaUniqueCaseInsensitivePlaybackCalls']}`",
        f"- Case-mismatched Lua calls rejected by installed-binary proof: `{counts['rejectedLuaCaseMismatchCalls']}`",
        f"- Runtime Lua handle dispatcher branches: `{counts['runtimeLuaHandleDispatcherCalls']}` in `{counts['runtimeLuaHandleDispatcherFamilies']}` polymorphic queue family",
        f"- Unresolved authored Lua playback references: `{counts['unresolvedLuaAuthoredPlaybackCalls']}`",
        f"- Exact root playback alias rows: `{counts['rootPlaybackAliasRows']}`",
        f"- TimelineAsset Story files reached by those aliases: `{counts['rootPlaybackAliasFiles']}`",
        f"- Alias rows composed with an independently connected root playback route: `{counts['composedRootPlaybackAliasRows']}`",
        f"- Story files connected by that composition: `{counts['composedRootPlaybackAliasFiles']}`",
        f"- Non-owning mission-state dependency Story files: `{counts['missionStateDependencyStoryFiles']}`",
        f"- Dependency-only Story files whose nominal owner is outside the pipeline: `{counts['missionStateDependencyCrossOwnerStoryFiles']}`",
        f"- Non-owning mission-state dependency placements: `{counts['missionStateDependencyPlacements']}`",
        f"- Unlinked files with exact native playback: `{counts['unlinkedNativePlaybackFiles']}`",
        f"- Exact native playbacks without a named event owner: `{counts['unlinkedNativePlaybackWithoutNamedEvent']}`",
        f"- Unresolved serialized Timeline containment: `{counts['unresolvedTimelineContainmentFiles']}`",
        f"- Unresolved typed DialogTree narrative containment: `{counts['unresolvedDialogTreeNarrativeFiles']}`",
        f"- Unlinked typed DialogTree narrative files: `{counts['unlinkedDialogTreeNarrativeFiles']}`",
        f"- Unresolved typed DialogTree left-subtitle containment: `{counts['unresolvedDialogTreeLeftSubtitleFiles']}`",
        f"- Unlinked typed DialogTree left-subtitle files: `{counts['unlinkedDialogTreeLeftSubtitleFiles']}`",
        f"- Unresolved typed DialogTree Story playback carriers: `{counts['unresolvedDialogTreeStoryPlaybackFiles']}`",
        f"- Definition-only black-screen files with no current-build playback consumer: `{counts['unlinkedDefinitionOnlyFiles']}`",
        f"- Those with non-empty original audio metadata only: `{counts['unlinkedDefinitionOnlyAudioMetadataFiles']}`",
        f"- Those with explicit empty audio mappings (likely legacy definitions): `{counts['unlinkedDefinitionOnlyEmptyAudioLikelyLegacyFiles']}`",
        f"- Those with no original audio metadata row: `{counts['unlinkedDefinitionOnlyWithoutAudioMetadataFiles']}`",
        f"- Exact non-mission authored content (speaker radio continuation, character SNS topics, factory guides): `{counts['nonMissionContentFiles']}`",
        f"- Missionless SubGame runtime nodes with exact playback: `{counts['missionlessSubGameRows']}`",
        f"- Unique Story files attached to those missionless nodes: `{counts['missionlessSubGameStoryFiles']}`",
        f"- Missionless SubGame-to-Story placements: `{counts['missionlessSubGameStoryPlacements']}`",
        f"- Exact missionless native runtime receiver nodes: `{counts['missionlessNativeRuntimeRows']}`",
        f"- Unique Story files attached to exact runtime receivers: `{counts['missionlessNativeRuntimeStoryFiles']}`",
        f"- Exact runtime-receiver-to-Story placements: `{counts['missionlessNativeRuntimeStoryPlacements']}`",
        f"- Exact receiver playback gates: `{counts['missionlessNativeRuntimePlaybackGates']}`",
        f"- Story files controlled by those exact gates: `{counts['missionlessNativeRuntimePlaybackGateStoryFiles']}`",
        f"- Exact post-playback control graphs: `{counts['missionlessNativeRuntimePostPlaybackControls']}`",
        f"- Typed branch points in those graphs: `{counts['missionlessNativeRuntimePostPlaybackBranchPoints']}`",
        f"- Server handoffs with unresolved handler identity: `{counts['missionlessNativeRuntimePostPlaybackServerHandoffs']}`",
        f"- Post-playback ActionBase placements named by the complete binary formatter: `{counts['postPlaybackFormatterNamedActions']}` / `{counts['postPlaybackActionPlacements']}`",
        f"- Remaining action shapes outside ActionBase: `{counts['postPlaybackUnresolvedActionShapes']}`",
        f"- Typed post-playback LevelSequence action placements: `{counts['postPlaybackLevelSequenceActions']}`",
        f"- Unique serialized LevelSequence ids: `{counts['postPlaybackLevelSequenceIds']}`",
        f"- Exact internally validated original LevelSequence TextAssets: `{counts['postPlaybackLevelSequenceExactAssets']}`",
        f"- Unresolved serialized LevelSequence ids: `{counts['postPlaybackLevelSequenceUnresolvedIds']}`",
        f"- Typed variable setters after any native Story playback: `{counts['postPlaybackVariableSetters']}`",
        f"- Exact same-level/script/key Story listener matches: `{counts['postPlaybackVariableExactListenerMatches']}`",
        f"- Cross-Story matches eligible for a future execution-semantics bridge: `{counts['postPlaybackVariableCrossStoryListenerMatches']}`",
        f"- Connected files with another unresolved DialogTree parent use: `{counts['partiallyConnectedDialogTreeNarrativeFiles']}`",
        "",
        "## By kind",
        "",
        "| kind | total | connected | unlinked |",
        "| --- | ---: | ---: | ---: |",
    ]
    for kind, values in kind_counts.items():
        lines.append(f"| `{kind}` | {values['total']} | {values['connected']} | {values['unlinked']} |")
    lines.extend([
        "",
        "## Shipped-Lua playback census",
        "",
        f"Validator: `{lua_playback_evidence['validator']}` / "
        f"`{lua_playback_evidence['status']}`.",
        "",
        lua_playback_evidence["evidenceBoundary"],
        "",
        f"Audit: `{lua_playback_evidence['auditReport']}` "
        f"SHA-256 `{lua_playback_evidence['auditSha256']}`.",
    ])
    case_contract_status = lua_playback_evidence.get(
        "caseResolutionContract"
    ) or {}
    lines.append(
        "Case-resolution native contract: "
        f"`{case_contract_status.get('status') or 'not_required'}` "
        f"from `{case_contract_status.get('sourceFile') or '-'}`."
    )
    case_contract_failures = case_contract_status.get("validationFailures") or []
    if case_contract_failures:
        failure = case_contract_failures[0]
        lines.append(
            "- first case-resolution failure: "
            f"validator=`{failure.get('validator') or '-'}`, "
            f"gate=`{failure.get('gate') or '-'}`, "
            f"expected=`{failure.get('expected')!r}`, "
            f"actual=`{failure.get('actual')!r}`, "
            f"source=`{failure.get('sourceFile') or '-'}`"
        )
    for row in lua_playback_evidence["acceptedExactPlaybackCalls"]:
        lines.append(
            f"- admitted `{row['storyKey']}` from `{row['luaFile']}:{row['luaLine']}` "
            f"(source SHA-256 `{row['luaSourceSha256']}`)"
        )
    for row in lua_playback_evidence["rejectedCaseMismatchCalls"]:
        lines.append(
            f"- rejected literal `{row['luaLiteral']}` for `{row['storyKey']}` "
            f"via `{row['auditReport']}`"
        )
    if root_playback_alias_rows:
        lines.extend([
            "",
            "## Exact CutsceneRoot playback aliases",
            "",
            "These rows prove root-to-TimelineAsset playback, not mission "
            "ownership or relative Story order.",
            "",
            "| root Story key | played TimelineAsset Story key | native mapping |",
            "| --- | --- | --- |",
        ])
        for row in root_playback_alias_rows:
            lines.append(
                f"| `{row['rootStoryKey']}` | "
                f"`{row['playableAssetStoryKey']}` | "
                f"`{row['nativeMappingId']}` |"
            )
    if native_playback_event_keys:
        lines.extend([
            "",
            "## Unlinked exact-native playback event families",
            "",
            "One Story file can occur under more than one decoded native event family.",
            "",
            "| native event | unique unlinked Story files |",
            "| --- | ---: |",
        ])
        for event_name, keys in sorted(
            native_playback_event_keys.items(),
            key=lambda item: (-len(item[1]), item[0]),
        ):
            lines.append(f"| `{event_name}` | {len(keys)} |")
    if missionless_nodes:
        lines.extend([
            "",
            "## Missionless original-data SubGame playback nodes",
            "",
            "These are exact SubGame/script/playback attachments, not mission-owned Story bindings.",
            "",
            "| SubGame | bound script | task ids | exact Story files | non-owning cross-references |",
            "| --- | ---: | --- | --- | --- |",
        ])
        for node in missionless_nodes:
            story_keys = ", ".join(f"`{row['key']}`" for row in node["storyFiles"])
            task_ids = ", ".join(f"`{value}`" for value in node["mainTaskIds"]) or "-"
            associations = ", ".join(
                f"`{row['relation']} -> {row['targetId']}`"
                for row in node.get("associations") or []
            ) or "-"
            lines.append(
                f"| `{node['subGameId']}` | `{node['bindScriptId']}` | {task_ids} | "
                f"{story_keys} | {associations} |"
            )
    if evidence_tier_counts:
        lines.extend([
            "",
            "## Explicit evidence tiers",
            "",
            "| tier | evidence rows | unique Story files |",
            "| --- | ---: | ---: |",
        ])
        for tier, row_count in sorted(evidence_tier_counts.items()):
            lines.append(
                f"| `{tier}` | {row_count} | {len(connected_keys_by_evidence_tier[tier])} |"
            )
    definition_classes = definition_only_classification["keysByClassification"]
    if definition_classes:
        lines.extend([
            "",
            "## Definition-only negative consumer classification",
            "",
            definition_only_classification["policy"],
            "",
            "| classification | files |",
            "| --- | ---: |",
        ])
        for classification, keys in definition_classes.items():
            lines.append(f"| `{classification}` | {len(keys)} |")
    lines.extend([
        "",
        "The JSON report contains the complete unlinked inventory and unresolved native-evidence keys.",
        "",
    ])
    (report_root / f"{stem}.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    if tracked_proxy_topology_failures:
        first = tracked_proxy_topology_failures[0]
        raise RuntimeError(
            f"validator={first['validator']} gate={first['gate']} "
            f"mission={first['mission']} story={first['storyKey']} "
            f"expected={first['expected']!r} actual={first['actual']!r} "
            f"source={first['sourceFile']} "
            f"sourceHashes={first['sourceHashes']!r} "
            f"failures={len(tracked_proxy_topology_failures)}"
        )
    return report
