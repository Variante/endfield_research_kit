#!/usr/bin/env python3
"""Build exact Story consumers embedded in factory guide runtime assets.

This audit is deliberately narrow.  It accepts only a fully typed
``GuideRuntimeAsset`` managed-reference action whose class is exactly
``FacSetInteractLockedState`` and whose ``radioId`` and factory instance key
are serialized in the same action.  It does not infer mission ownership or
Story order.

Outputs:

    reports/story/recovery/animestudio_story_guide_consumer_audit.json
    reports/story/recovery/animestudio_story_guide_consumer_audit.md
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import json
from pathlib import Path
import re
import sys
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = ROOT / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from common import (  # noqa: E402
    NativeEvidenceUnavailable,
    check_installed_native_inputs,
    md_escape,
    native_evidence_required,
    native_evidence_skip_message,
    read_json,
    safe_key,
    sha256_file,
    write_report_json,
    write_text_if_changed,
)
from export_full_from_game import (  # noqa: E402
    animestudio_object_index_dir,
    load_animestudio_object_index_summary,
)


SCHEMA = "animestudioStoryGuideConsumerAudit.v1"
DEFAULT_OUTPUT_ROOT = ROOT / "export_full"
DEFAULT_EXPORT_SUMMARY = ROOT / "reports" / "export" / "export_full_summary.json"
DEFAULT_REPORT_ROOT = ROOT / "reports" / "story" / "recovery"
DEFAULT_SOURCES = ("StreamingAssets",)

GUIDE_RUNTIME_ASSET = "Beyond.Gameplay.Actions.GuideRuntimeAsset"
ACTION_CLASS = "FacSetInteractLockedState"
ACTION_NAMESPACE = "Beyond.Gameplay.Actions"
ACTION_ASSEMBLY = "Gameplay.Beyond"
ACTION_LAYOUT = "Beyond.Gameplay.Actions.FacSetInteractLockedState"
RADIO_PATH_RE = re.compile(
    r"^\$\.references\.RefIds\[(?P<index>[0-9]+)\]\.data\.radioId\.value$"
)
OWNER_OR_RUNTIME_SEGMENTS = frozenset({
    "levelscriptid",
    "linkmissionid",
    "missionid",
    "questid",
    "relatedmissionid",
    "sceneid",
    "scenenumid",
    "scriptid",
})

# Current-build native evidence.  The audit refuses to publish classifications
# against another GameAssembly until this mapping is revalidated.
EXPECTED_GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
NATIVE_MAPPING_ID = (
    "gameassembly-2026-07-11-fac-set-interact-locked-state-execute-v1"
)


class AuditError(RuntimeError):
    pass


def _scalar_map(row: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for index, item in enumerate(row.get("scalars") or []):
        shape_valid = (
            isinstance(item, list)
            and len(item) == 3
            and isinstance(item[0], str)
            and item[1] in {"s", "i", "b"}
        )
        value_valid = bool(
            shape_valid
            and (
                (item[1] == "s" and isinstance(item[2], str))
                or (
                    item[1] == "i"
                    and isinstance(item[2], int)
                    and not isinstance(item[2], bool)
                )
                or (item[1] == "b" and isinstance(item[2], bool))
            )
        )
        if not value_valid:
            identity = row.get("object")
            identity = identity if isinstance(identity, dict) else {}
            raise AuditError(
                "malformed scalar row: "
                f"source={identity.get('source')!r} "
                f"serializedFile={identity.get('serializedFile')!r} "
                f"pathId={identity.get('pathId')!r} index={index}; "
                "expected [path, type, value] with "
                "s:string, i:integer, or b:boolean; "
                f"actual={item!r}"
            )
        values[item[0]] = item[2]
    return values


def _path_segments(path: str) -> set[str]:
    segments: set[str] = set()
    for segment in str(path or "").split("."):
        segment = re.sub(r"\[[0-9]+\]$", "", segment)
        normalized = re.sub(r"[^a-z0-9]", "", segment.lower())
        if normalized:
            segments.add(normalized)
    return segments


def _object_identity(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("object")
    if not isinstance(value, dict):
        raise AuditError("object-index row has no object identity")
    required = ("serializedFile", "source", "sourceOffset", "pathId")
    if any(value.get(field) is None for field in required):
        raise AuditError("object-index row has an incomplete object identity")
    return {field: value[field] for field in required}


def audit_object_row(row: dict[str, Any], source: str) -> list[dict[str, Any]]:
    """Return exact guide-radio action rows from one merged object record."""
    if row.get("recordType") != "object":
        return []
    scalars = _scalar_map(row)
    radio_paths = [
        (path, match)
        for path in scalars
        if (match := RADIO_PATH_RE.fullmatch(path))
        and safe_key(scalars[path])
    ]
    if not radio_paths:
        return []

    script = row.get("script") if isinstance(row.get("script"), dict) else {}
    asset_name = safe_key(row.get("name"))
    object_reasons: list[str] = []
    if safe_key(script.get("fullName")) != GUIDE_RUNTIME_ASSET:
        object_reasons.append("object_is_not_typed_guide_runtime_asset")
    if not asset_name.startswith("guide_blackbox_"):
        object_reasons.append("asset_is_not_named_blackbox_guide")
    owner_paths = sorted(
        path
        for path, value in scalars.items()
        if path.endswith(".value")
        and safe_key(value)
        and _path_segments(path) & OWNER_OR_RUNTIME_SEGMENTS
    )
    if owner_paths:
        object_reasons.append("same_object_has_owner_or_runtime_identifier")

    actions: list[dict[str, Any]] = []
    guide_level_ids = sorted({
        safe_key(value)
        for path, value in scalars.items()
        if path.endswith(".levelId.value") and safe_key(value)
    })
    for radio_path, match in radio_paths:
        ref_index = int(match.group("index"))
        prefix = f"$.references.RefIds[{ref_index}]"
        reasons = list(object_reasons)
        expected = {
            f"{prefix}.type.class": ACTION_CLASS,
            f"{prefix}.type.ns": ACTION_NAMESPACE,
            f"{prefix}.type.asm": ACTION_ASSEMBLY,
            f"{prefix}.data.layout": ACTION_LAYOUT,
        }
        for path, value in expected.items():
            if safe_key(scalars.get(path)) != value:
                reasons.append(f"typed_action_field_mismatch:{path}")
        instance_key = safe_key(scalars.get(f"{prefix}.data.instKey.value"))
        if not instance_key:
            reasons.append("factory_instance_key_missing")
        actions.append({
            "storyKey": safe_key(scalars[radio_path]),
            "assetName": asset_name,
            "assetType": safe_key(script.get("fullName")),
            "source": source,
            "object": _object_identity(row),
            "decodeStatus": safe_key(row.get("decodeStatus")) or "unknown",
            "scalarsTruncated": bool(row.get("scalarsTruncated")),
            "managedReferenceIndex": ref_index,
            "actionClass": safe_key(scalars.get(f"{prefix}.type.class")),
            "actionNamespace": safe_key(scalars.get(f"{prefix}.type.ns")),
            "actionAssembly": safe_key(scalars.get(f"{prefix}.type.asm")),
            "actionLayout": safe_key(scalars.get(f"{prefix}.data.layout")),
            "actionId": safe_key(
                scalars.get(f"{prefix}.data.actionBase.actionId.hex")
            ),
            "actionKey": safe_key(
                scalars.get(f"{prefix}.data.actionBase.key")
            ),
            "nextId": safe_key(
                scalars.get(f"{prefix}.data.actionBase.nextId.hex")
            ),
            "factoryInstanceKey": instance_key,
            "guideLevelIds": guide_level_ids,
            "radioField": radio_path,
            "ownerOrRuntimeIdentifierPaths": owner_paths,
            "accepted": not reasons,
            "rejectionReasons": reasons,
        })
    return actions


def iter_gzip_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, 1):
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise AuditError(f"{path}:{line_number}: row is not an object")
                yield value
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"{path}: cannot read merged object index: {exc}") from exc


def _source_fingerprint(
    export_summary: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    row = (export_summary.get("source_sizes") or {}).get(source)
    if not isinstance(row, dict):
        raise AuditError(f"export summary has no {source} source fingerprint")
    result = {
        "files": row.get("files"),
        "bytes": row.get("bytes"),
        "fingerprint": safe_key(row.get("fingerprint")).lower(),
    }
    if (
        isinstance(result["files"], bool)
        or not isinstance(result["files"], int)
        or isinstance(result["bytes"], bool)
        or not isinstance(result["bytes"], int)
        or len(result["fingerprint"]) != 64
    ):
        raise AuditError(f"export summary has an invalid {source} fingerprint")
    return result


def scan_source(
    output_root: Path,
    source: str,
    export_summary: dict[str, Any],
) -> dict[str, Any]:
    current_fingerprint = _source_fingerprint(export_summary, source)
    summary = load_animestudio_object_index_summary(
        output_root,
        source,
        expected_source_fingerprint=current_fingerprint,
    )
    if summary is None:
        raise AuditError(
            f"{source}: no current published object index; rerun an explicit "
            "installed-game export with --animestudio-object-index"
        )
    output = (summary.get("outputs") or {}).get("objects") or {}
    relative_name = safe_key(output.get("path"))
    if not relative_name or Path(relative_name).name != relative_name:
        raise AuditError(f"{source}: merged object-index path is invalid")
    index_dir = animestudio_object_index_dir(output_root, source)
    object_path = index_dir / relative_name
    actions: list[dict[str, Any]] = []
    object_count = 0
    for row in iter_gzip_jsonl(object_path):
        if row.get("recordType") != "object":
            continue
        object_count += 1
        actions.extend(audit_object_row(row, source))
    expected_objects = int((summary.get("counts") or {}).get("objects") or 0)
    if object_count != expected_objects:
        raise AuditError(
            f"{source}: parsed {object_count} objects, expected {expected_objects}"
        )
    return {
        "source": source,
        "summary": str(index_dir / "summary.json"),
        "objects": str(object_path),
        "stageSignatureSha256": (
            (summary.get("stageSignature") or {}).get("sha256")
        ),
        "sourceFingerprint": current_fingerprint,
        "objectCount": object_count,
        "actions": actions,
    }



def resolve_gameassembly(explicit_path: Path | None) -> Path | None:
    """Return an explicit binary, or ``None`` to let the shared gate resolve.

    The gate already considers the export summary's ``game_root`` alongside
    ENDFIELD_GAME_ROOT and endfield_paths.bat, so this keeps one precedence
    order for every recovery step.
    """
    return explicit_path.resolve() if explicit_path is not None else None


def build_report(
    output_root: Path,
    sources: Iterable[str],
    export_summary_path: Path,
    gameassembly: Path | None,
) -> dict[str, Any]:
    export_summary = read_json(export_summary_path, {})
    if not isinstance(export_summary, dict):
        raise AuditError(f"{export_summary_path}: invalid export summary")
    gameassembly_path = resolve_gameassembly(gameassembly)
    native = check_installed_native_inputs(
        EXPECTED_GAMEASSEMBLY_SHA256,
        gameassembly=gameassembly_path,
        require_metadata=False,
    )
    if not native.validated:
        raise NativeEvidenceUnavailable(native)
    gameassembly_sha256 = native.gameassembly_sha256.upper()

    source_rows = [
        scan_source(output_root, source, export_summary)
        for source in sources
    ]
    actions = [
        action
        for source_row in source_rows
        for action in source_row.pop("actions")
    ]
    accepted = [row for row in actions if row["accepted"]]
    rejected = [row for row in actions if not row["accepted"]]
    accepted_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    rejected_by_key: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in accepted:
        accepted_by_key[row["storyKey"]].append(row)
    for row in rejected:
        rejected_by_key[row["storyKey"]].append(row)

    classifications: list[dict[str, Any]] = []
    for story_key in sorted(accepted_by_key):
        rows = accepted_by_key[story_key]
        if rejected_by_key.get(story_key):
            continue
        classifications.append({
            "storyKey": story_key,
            "recoveryStatus":
                "closed_exact_guide_runtime_non_mission_content",
            "evidenceKind": "guide_runtime_asset",
            "contentClass": "factory_interaction_lock_guide_radio",
            "assetType": GUIDE_RUNTIME_ASSET,
            "consumerClass": f"{ACTION_NAMESPACE}.{ACTION_CLASS}",
            "assetCount": len({row["assetName"] for row in rows}),
            "actionCount": len(rows),
            "assetNames": sorted({row["assetName"] for row in rows}),
            "factoryInstanceKeys": sorted({
                row["factoryInstanceKey"] for row in rows
            }),
            "guideLevelIds": sorted({
                level_id
                for row in rows
                for level_id in row["guideLevelIds"]
            }),
            "nativeMappingId": NATIVE_MAPPING_ID,
            "nativeMethod": {
                "name":
                    "Beyond.Gameplay.Actions."
                    "FacSetInteractLockedState.Execute",
                "token": "0x06008a6d",
                "address": "0x187654fa0",
            },
            "nativeConsumer": {
                "lockedBranch":
                    "RemoteFactoryInteract.LockBuildingInteract("
                    "instanceKey, radioId, false)",
                "unlockedBranch":
                    "RemoteFactoryInteract.UnlockBuildingInteract("
                    "instanceKey, false)",
            },
            "orderBoundary": (
                "the guide action is non-mission factory tutorial content; "
                "action ids, next ids, asset names, and object order do not "
                "create mission ownership or cross-Story chronology"
            ),
        })

    counts = Counter({
        "sources": len(source_rows),
        "objectsScanned": sum(row["objectCount"] for row in source_rows),
        "matchingObjects": len({
            (
                row["source"],
                row["object"]["serializedFile"],
                row["object"]["pathId"],
            )
            for row in actions
        }),
        "matchingActions": len(actions),
        "acceptedActions": len(accepted),
        "rejectedActions": len(rejected),
        "classifiedStoryKeys": len(classifications),
    })
    actions.sort(key=lambda row: (
        row["storyKey"],
        row["assetName"],
        row["managedReferenceIndex"],
    ))
    rejected.sort(key=lambda row: (
        row["storyKey"],
        row["assetName"],
        row["managedReferenceIndex"],
    ))
    return {
        "_schema": SCHEMA,
        "exportSummary": str(export_summary_path),
        "sources": source_rows,
        "nativeEvidence": {
            "validated": True,
            "gameAssembly": str(gameassembly_path),
            "gameAssemblySha256": gameassembly_sha256,
            "mappingId": NATIVE_MAPPING_ID,
            "method": {
                "name":
                    "Beyond.Gameplay.Actions."
                    "FacSetInteractLockedState.Execute",
                "token": "0x06008a6d",
                "address": "0x187654fa0",
                "fieldOffsets": {
                    "_isLocked": "0xd0",
                    "_instKey": "0xd8",
                    "_radioId": "0xe0",
                },
                "lockedBranchTarget":
                    "RemoteFactoryInteract.LockBuildingInteract",
                "unlockedBranchTarget":
                    "RemoteFactoryInteract.UnlockBuildingInteract",
            },
        },
        "summary": dict(counts),
        "classifications": classifications,
        "actions": actions,
        "rejectedActions": rejected,
        "evidencePolicy": {
            "accepted": (
                "current source fingerprint and object-index signature; exact "
                "typed GuideRuntimeAsset; exact FacSetInteractLockedState "
                "managed reference; same-action radioId and factory instKey; "
                "blackbox guide asset; no same-object mission, quest, scene, "
                "LevelScript, or script identifier; current native Execute "
                "mapping"
            ),
            "notAccepted": (
                "filenames alone, Story-id prefixes, neighboring objects, "
                "PathID/address order, partial action identities, or any row "
                "that co-carries a mission/runtime owner"
            ),
            "promotionBoundary": (
                "classifies authored factory tutorial content out of the "
                "mission recovery queue; creates no mission owner or order edge"
            ),
        },
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# AnimeStudio Story Guide Consumer Audit",
        "",
        f"- Object rows scanned: `{summary['objectsScanned']}`",
        f"- Matching guide objects: `{summary['matchingObjects']}`",
        f"- Exact typed actions: `{summary['matchingActions']}`",
        f"- Classified Story keys: `{summary['classifiedStoryKeys']}`",
        (
            "- Native mapping: "
            f"`{report['nativeEvidence']['mappingId']}` against "
            f"`{report['nativeEvidence']['gameAssemblySha256']}`"
        ),
        "",
        "## Classifications",
        "",
    ]
    if not report["classifications"]:
        lines.append("_No Story keys met the strict guide-content policy._")
    else:
        lines.extend([
            "| Story | Assets | Actions | Consumer | Status |",
            "|---|---:|---:|---|---|",
        ])
        for row in report["classifications"]:
            lines.append(
                f"| `{md_escape(row['storyKey'])}` | {row['assetCount']} | "
                f"{row['actionCount']} | "
                f"`{md_escape(row['consumerClass'])}` | "
                f"`{md_escape(row['recoveryStatus'])}` |"
            )
    lines.extend([
        "",
        "## Evidence boundary",
        "",
        f"- Accepted: {report['evidencePolicy']['accepted']}.",
        f"- Rejected: {report['evidencePolicy']['notAccepted']}.",
        f"- Promotion: {report['evidencePolicy']['promotionBoundary']}.",
        "",
    ])
    return "\n".join(lines)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument(
        "--export-summary",
        type=Path,
        default=DEFAULT_EXPORT_SUMMARY,
    )
    parser.add_argument("--gameassembly", type=Path)
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        help="Published AnimeStudio source index to scan; repeat as needed.",
    )
    parser.add_argument("--report-root", type=Path, default=DEFAULT_REPORT_ROOT)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = build_report(
            args.output_root.resolve(),
            tuple(args.sources or DEFAULT_SOURCES),
            args.export_summary.resolve(),
            args.gameassembly,
        )
    except NativeEvidenceUnavailable as exc:
        required = native_evidence_required()
        print(
            native_evidence_skip_message(
                "animestudio-story-guide-consumer", exc.result, required=required
            ),
            file=sys.stderr,
        )
        return 1 if required else 0
    except (AuditError, ValueError) as exc:
        raise SystemExit(
            f"AnimeStudio Story guide consumer audit failed: {exc}"
        ) from exc
    json_path = (
        args.report_root / "animestudio_story_guide_consumer_audit.json"
    )
    markdown_path = (
        args.report_root / "animestudio_story_guide_consumer_audit.md"
    )
    write_report_json(json_path, report)
    write_text_if_changed(markdown_path, render_markdown(report))
    print(f"AnimeStudio Story guide audit: {markdown_path.relative_to(ROOT)}")
    print(f"AnimeStudio Story guide data: {json_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
