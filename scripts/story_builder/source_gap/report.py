"""Publishing and Markdown rendering for the source Story gap queue."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .contracts import BUCKET_ORDER, SCORE_WEIGHTS
from common import (
    md_escape,
    safe_key,
    write_report_json,
    write_text_if_changed,
)


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Source-only Story Recovery Gap Queue",
        "",
        f"Generated: `{report['_generatedAt']}`",
        "",
        "This is a recovery-work queue, not a proposed Story order. Main-story (`e`)",
        "missions sort first. Every score contribution is preserved in the JSON.",
        "",
        "## Ranking Policy",
        "",
        "Bucket order: " + ", ".join(f"`{bucket}`" for bucket in BUCKET_ORDER) + ".",
        "",
        "Score weights: " + ", ".join(
            f"`{key}` x {weight}" for key, weight in SCORE_WEIGHTS.items()
        ) + ".",
        "",
        (
            "Current-build offline-exhaustion evidence: "
            f"`{safe_key((report.get('offlineExhaustionEvidence') or {}).get('status')) or 'unknown'}`. "
            "These rows are deferred from triage only; they create no graph edge "
            "and reopen when a hash or audit target set changes."
        ),
        (
            "Current-build quest-attachment diagnostic evidence: "
            f"`{safe_key((report.get('questAttachmentDiagnosticEvidence') or {}).get('status')) or 'unknown'}`. "
            "These rows close broad co-membership as non-owning only; they add "
            "no quest-to-Story or order edge."
        ),
        (
            "Current-build Story trigger manifest evidence: "
            f"`{safe_key((report.get('storyTriggerManifestEvidence') or {}).get('status')) or 'unknown'}`; "
            "exact playback closures remain non-ordering (`graphEffect=none`)."
        ),
        (
            "Project-authored Story provenance: "
            f"`{safe_key((report.get('projectAuthoredStoryEvidence') or {}).get('status')) or 'unknown'}`. "
            "These generated WebUI rows are explicitly excluded from original-game "
            "consumer and chronology recovery."
        ),
        (
            "Story trigger closure contract validation: "
            f"`{safe_key((report.get('storyTriggerClosureValidation') or {}).get('status')) or 'unknown'}`."
        ),
        "",
    ]
    for heading, status_key in (
        ("Story Trigger Manifest Validator Failures", "storyTriggerManifestEvidence"),
        ("Story Trigger Closure Validator Failures", "storyTriggerClosureValidation"),
        ("Project-authored Story Provenance Failures", "projectAuthoredStoryEvidence"),
    ):
        failures = (report.get(status_key) or {}).get("validationFailures") or []
        if not failures:
            continue
        lines.extend([
            f"## {heading}",
            "",
            "| mission | Story | gate | source | expected | actual |",
            "| --- | --- | --- | --- | --- | --- |",
        ])
        for failure in failures:
            source_paths = failure.get("sourcePaths") or [
                safe_key(failure.get("sourcePath"))
            ]
            lines.append(
                f"| `{md_escape(safe_key(failure.get('missionId')) or '-')}` | "
                f"`{md_escape(safe_key(failure.get('storyKey')) or '-')}` | "
                f"`{md_escape(safe_key(failure.get('gate')))}` | "
                f"`{md_escape('; '.join(filter(None, map(str, source_paths))))}` | "
                f"`{md_escape(json.dumps(failure.get('expected') or {}, ensure_ascii=False, sort_keys=True)[:500])}` | "
                f"`{md_escape(json.dumps(failure.get('actual') or {}, ensure_ascii=False, sort_keys=True)[:500])}` |"
            )
        lines.append("")
    offline_failures = (
        report.get("offlineExhaustionEvidence") or {}
    ).get("validationFailures") or []
    if offline_failures:
        lines.extend([
            "## Offline-Exhaustion Validator Failures",
            "",
            "| Story | gate | source | expected | actual |",
            "| --- | --- | --- | --- | --- |",
        ])
        for failure in offline_failures:
            expected = failure.get("expected") or {}
            actual = failure.get("actual") or {}
            source_paths = failure.get("sourcePaths") or []
            lines.append(
                f"| `{md_escape(safe_key(failure.get('storyKey')) or '-')}` | "
                f"`{md_escape(safe_key(failure.get('gate')))}` | "
                f"`{md_escape('; '.join(map(str, source_paths)))}` | "
                f"`{md_escape(json.dumps(expected, ensure_ascii=False, sort_keys=True)[:500])}` | "
                f"`{md_escape(json.dumps(actual, ensure_ascii=False, sort_keys=True)[:500])}` |"
            )
        lines.append("")
    diagnostic_failures = (
        report.get("questAttachmentDiagnosticEvidence") or {}
    ).get("validationFailureDetails") or []
    if diagnostic_failures:
        lines.extend([
            "## Quest-Attachment Validator Failures",
            "",
            "| quest | gate | source | expected condition | actual condition |",
            "| --- | --- | --- | --- | --- |",
        ])
        for failure in diagnostic_failures:
            expected = failure.get("expected") or {}
            actual = failure.get("actual") or {}
            lines.append(
                f"| `{md_escape(safe_key(failure.get('questId')))}` | "
                f"`{md_escape(safe_key(failure.get('gate')))}` | "
                f"`{md_escape(safe_key(failure.get('sourcePath')))}` | "
                f"`{md_escape(safe_key(expected.get('conditionType')))}` | "
                f"`{md_escape(safe_key(actual.get('conditionType')))}` |"
            )
        lines.append("")
    lines.extend([
        "## Bucket Summary",
        "",
        "| bucket | missions | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | actionable LS gaps | closed LS negatives | quest gaps (actionable / diagnostic-closed) | option gaps |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ])
    for row in report["summary"]["buckets"]:
        option_gaps = int(
            row.get("actionableNoExplicitOptionRouteGroups") or 0
        ) + int(
            row.get("actionableExcludedOptionEvidenceGroups") or 0
        )
        lines.append(
            f"| `{row['bucket']}` | {row.get('missions', 0)} | {row.get('score', 0)} | "
            f"{row.get('sceneCount', 0)} | {row.get('isolatedScenes', 0)} "
            f"({row.get('actionableCoreIsolatedScenes', 0)} / "
            f"{row.get('closedExactNativeIsolatedScenes', 0)} / "
            f"{row.get('closedExactRuntimeConfigIsolatedScenes', 0)} / "
            f"{row.get('closedDefinitionOnlyIsolatedScenes', 0)} / "
            f"{row.get('closedNonMissionContentIsolatedScenes', 0)} / "
            f"{row.get('deferredOfflineExhaustedIsolatedScenes', 0)}) | "
            f"{row.get('weakOnlyScenes', 0)} "
            f"({row.get('actionableWeakOnlyScenes', 0)} / "
            f"{row.get('closedExactNativeWeakOnlyScenes', 0)}) | "
            f"{row.get('sourceCycles', 0)} | "
            f"{row.get('untypedMultiSceneLevelscriptContexts', 0)} | "
            f"{row.get('closedNonPlaybackLevelscriptContexts', 0)} | "
            f"{row.get('questIdsWithoutStrictStoryAttachment', 0)} / "
            f"{row.get('closedQuestAttachmentDiagnostics', 0)} | "
            f"{option_gaps} |"
        )

    lines.extend([
        "",
        "## Ranked Missions",
        "",
        "| rank | mission | bucket rank | score | scenes | isolated (core: actionable / native-closed / runtime-config-closed / definition-closed / non-mission-closed / offline-exhausted) | weak-only (actionable / exact-closed) | cycles | LS gaps | quest gaps (actionable / diagnostic-closed) | option gaps | primary frontier |",
        "| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
    ])
    for row in report["missions"][:100]:
        metrics = row["metrics"]
        option_gaps = (
            metrics["actionableNoExplicitOptionRouteGroups"]
            + metrics["actionableExcludedOptionEvidenceGroups"]
        )
        lines.append(
            f"| {row['rank']} | `{md_escape(row['mission'])}` | {row['bucketRank']} | {row['score']} | "
            f"{metrics['sceneCount']} | {metrics['isolatedScenes']} "
            f"({metrics['actionableCoreIsolatedScenes']} / "
            f"{metrics['closedExactNativeIsolatedScenes']} / "
            f"{metrics['closedExactRuntimeConfigIsolatedScenes']} / "
            f"{metrics['closedDefinitionOnlyIsolatedScenes']} / "
            f"{metrics['closedNonMissionContentIsolatedScenes']} / "
            f"{metrics['deferredOfflineExhaustedIsolatedScenes']}) | "
            f"{metrics['weakOnlyScenes']} "
            f"({metrics['actionableWeakOnlyScenes']} / "
            f"{metrics['closedExactNativeWeakOnlyScenes']}) | "
            f"{metrics['sourceCycles']} | {metrics['untypedMultiSceneLevelscriptContexts']} | "
            f"{metrics['questIdsWithoutStrictStoryAttachment']} / "
            f"{metrics['closedQuestAttachmentDiagnostics']} | {option_gaps} | "
            f"`{row['primaryFrontier']}` |"
        )

    main_rows = [row for row in report["missions"] if row["bucket"] == "main"][:25]
    lines.extend([
        "",
        "## Main-story Frontier Detail",
        "",
    ])
    for row in main_rows:
        metrics = row["metrics"]
        lines.extend([
            f"### {row['bucketRank']}. `{md_escape(row['mission'])}`",
            "",
            f"Score `{row['score']}`; primary frontier `{row['primaryFrontier']}`. "
            f"Scenes `{metrics['sceneCount']}`, isolated `{metrics['isolatedScenes']}` "
            f"(`{metrics['actionableCoreIsolatedScenes']}` actionable core, "
            f"`{metrics['closedExactNativeIsolatedScenes']}` exact-native closed, "
            f"`{metrics['closedExactRuntimeConfigIsolatedScenes']}` "
            "exact runtime-config closed, "
            f"`{metrics['closedDefinitionOnlyIsolatedScenes']}` definition-only closed, "
            f"`{metrics['closedNonMissionContentIsolatedScenes']}` non-mission content closed, "
            f"`{metrics['deferredOfflineExhaustedIsolatedScenes']}` current-build offline-exhausted), "
            f"weak-only `{metrics['weakOnlyScenes']}` "
            f"(`{metrics['actionableWeakOnlyScenes']}` actionable, "
            f"`{metrics['closedExactNativeWeakOnlyScenes']}` exact-native closed), "
            f"cycles `{metrics['sourceCycles']}`.",
            "",
            f"Quest ids without strict Story attachment: "
            f"`{metrics['questIdsWithoutStrictStoryAttachment']}`; "
            f"closed non-owning diagnostic co-memberships: "
            f"`{metrics['closedQuestAttachmentDiagnostics']}`; untyped multi-scene "
            f"LevelScript contexts: `{metrics['untypedMultiSceneLevelscriptContexts']}`; "
            f"closed binary-negative contexts: "
            f"`{metrics['closedNonPlaybackLevelscriptContexts']}`; "
            f"actionable option gap groups: "
            f"`{metrics['actionableNoExplicitOptionRouteGroups'] + metrics['actionableExcludedOptionEvidenceGroups']}` "
            f"(`{metrics['deferredOfflineExhaustedOptionRouteGroups']}` "
            f"current-build offline-exhausted; "
            f"`{metrics['singleOptionNoExplicitRouteGroups']}` single-option "
            f"acknowledgements and `{metrics['closedExcludedOptionEvidenceGroups']}` "
            "shared/cosmetic exclusions are retained but not scored).",
            "",
        ])
        contexts = row.get("untypedMultiSceneLevelscriptContexts") or []
        if contexts:
            lines.append("Top untyped LevelScript contexts:")
            lines.append("")
            for context in contexts[:5]:
                scenes = ", ".join(f"`{md_escape(key)}`" for key in context["sceneKeys"])
                lines.append(f"- `{md_escape(context['sourceFile'])}`: {scenes}")
            lines.append("")
        closed_contexts = row.get("closedNonPlaybackLevelscriptContexts") or []
        if closed_contexts:
            lines.append("Closed binary-negative LevelScript contexts:")
            lines.append("")
            for context in closed_contexts[:5]:
                classifications = ", ".join(
                    f"`{md_escape(item['sceneKey'])}` "
                    f"({md_escape(item['status'])})"
                    for item in context.get("unresolvedBinaryClassifications") or []
                )
                lines.append(
                    f"- `{md_escape(context['sourceFile'])}`: {classifications}"
                )
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


@dataclass(frozen=True)
class GapReportPaths:
    json: Path
    markdown: Path


def report_paths(reports_dir: Path, language: str) -> GapReportPaths:
    language = str(language or "CN").upper()
    return GapReportPaths(
        json=reports_dir / f"source_story_gap_queue_{language}.json",
        markdown=reports_dir / f"source_story_gap_queue_{language}.md",
    )


def publish_gap_report(
    report: dict[str, Any],
    reports_dir: Path,
    language: str,
) -> GapReportPaths:
    """Publish the JSON and human-readable views from one report object."""
    paths = report_paths(reports_dir, language)
    write_report_json(paths.json, report)
    write_text_if_changed(paths.markdown, render_markdown(report))
    return paths
