"""Load the reviewed DynamicScene-to-Story context for Mission Pipeline.

The adjacent artifact is a compact, current-build projection of the decoded
DynamicStreaming mission-control roots and their exact LevelScript decoration
action joins.  It intentionally exposes context only: matching authored ids
and shared local control flow do not prove mission ownership or Story order.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

if __package__ == "story_builder":
    from common import (
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
elif __package__ == "scripts.story_builder":
    from scripts.common import (
        NATIVE_EVIDENCE_MISMATCHED,
        NATIVE_EVIDENCE_VALIDATED,
        check_installed_native_inputs,
    )
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.dynamic_scene")


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = "dynamicSceneStoryContext.v1"
AUDIT_SCHEMA = "dynamicSceneStoryContextValidation.v1"
DEFAULT_ARTIFACT = Path(__file__).with_name("dynamic_scene.json")
DEFAULT_EXPORT_ROOT = ROOT / "export_full"
DEFAULT_EXPORT_SUMMARY = ROOT / "reports" / "export" / "export_full_summary.json"

GAMEASSEMBLY_SHA256 = (
    "0C5573679BC6DEC2D068A14335466DB7CCF20AF9BAE2B983FB9D45677D80FFCE"
)
METADATA_SHA256 = (
    "90C58E26E87C7227A85DDA3FEDF6CE5ED0B06DC1F76E0ABBE75AB20750ADF97E"
)
DYNAMIC_STREAM_SHA256 = (
    "1702E7F78D19E43F30208BC8A5CE1CAEDC16994DA9A7360FEFDD5F404E900320"
)
SOURCE_FINGERPRINTS = {
    "StreamingAssets": "20438582CCC8B862ED6E3092648C967D1601D7E10B20367471FF72918ADB8E14",
    "Persistent": "6DC0C8C55BFE8AC4D9506604E2D4733D9C0E470BD1CBEDBCA41B6DEDF12E3DCA",
}
EXPECTED_COUNTS = {
    "candidateRoots": 72,
    "storyOccurrences": 218,
    "exactTargetBridgeRoots": 1,
    "sharedControlPathStoryOccurrences": 1,
    "exactLocalTriggerVolumeContexts": 1,
    "triggerVolumeForeignKeyBridges": 0,
}
CLASSIFICATION = "exact_cross_reference_not_runtime_owner"
LOCAL_BRIDGE_CLASSIFICATION = (
    "exact_dynamic_scene_target_and_shared_levelscript_control_path"
)
TRIGGER_CONTEXT_STATUS = (
    "exact_local_levelscript_trigger_volume_without_foreign_identity"
)
TRIGGER_SCHEMA_MAPPING_ID = (
    "current-global-metadata-levelscript-trigger-volume-data-fields"
)


def _source_file(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _read_json(path: Path) -> tuple[dict[str, Any], bytes, str | None]:
    try:
        raw = path.read_bytes()
        payload = json.loads(raw.decode("utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        return {}, b"", str(error)[:400]
    if not isinstance(payload, dict):
        return {}, raw, f"expected object, found {type(payload).__name__}"
    return payload, raw, None


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def _resolved_export_source(export_root: Path, relative: str) -> Path | None:
    candidate = (export_root / relative).resolve()
    try:
        candidate.relative_to(export_root.resolve())
    except ValueError:
        return None
    return candidate


def _validate_context_rows(
    context: Any,
    source_paths: set[str],
    reject: Any,
) -> None:
    if not isinstance(context, dict):
        reject("context_object", {"type": "object"}, type(context).__name__)
        return
    exact_gates = (
        ("classification", CLASSIFICATION, context.get("classification")),
        ("direct_bridge", False, context.get("directBridgeFound")),
        ("mission_activation_bridge", False, context.get("missionActivationBridgeFound")),
        ("mission_graph_action", "none", context.get("missionGraphAction")),
        ("counts", EXPECTED_COUNTS, context.get("counts")),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    rows = context.get("rows")
    if not isinstance(rows, list):
        reject("rows_list", {"type": "array"}, type(rows).__name__)
        return
    if len(rows) != EXPECTED_COUNTS["candidateRoots"]:
        reject("row_count", EXPECTED_COUNTS["candidateRoots"], len(rows))

    occurrence_count = 0
    bridge_count = 0
    shared_story_count = 0
    trigger_context_count = 0
    seen_row_keys: set[tuple[str, str, str]] = set()
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            reject(f"row_{index}_object", {"type": "object"}, type(row).__name__)
            continue
        logic_id = str(row.get("logicId") or "")
        scene = str(row.get("scene") or "")
        dynamic_source = str(row.get("dynamicSourceFile") or "")
        key = (scene, logic_id, dynamic_source)
        if not scene or not logic_id.isdigit() or not dynamic_source.endswith(".bytes"):
            reject(
                f"row_{index}_identity",
                {"scene": "nonempty", "logicId": "digits", "dynamicSourceFile": "*.bytes"},
                {"scene": scene, "logicId": logic_id, "dynamicSourceFile": dynamic_source},
            )
        if key in seen_row_keys:
            reject(f"row_{index}_unique", {"unique": True}, key)
        seen_row_keys.add(key)
        for field, expected in (
            ("scriptId", logic_id),
            ("classification", CLASSIFICATION),
            ("missionOwnerStatus", "unresolved"),
            ("storyBinding", False),
            ("orderEvidence", False),
            ("missionGraphAction", "none"),
        ):
            if row.get(field) != expected:
                reject(f"row_{index}_{field}", expected, row.get(field))

        conditions = row.get("conditions")
        if not isinstance(conditions, list) or not conditions:
            reject(f"row_{index}_conditions", {"nonemptyArray": True}, conditions)

        occurrences = row.get("storyOccurrences")
        if not isinstance(occurrences, list) or not occurrences:
            reject(f"row_{index}_occurrences", {"nonemptyArray": True}, occurrences)
            occurrences = []
        occurrence_count += len(occurrences)
        occurrence_keys: set[str] = set()
        for occurrence_index, occurrence in enumerate(occurrences):
            if not isinstance(occurrence, dict):
                reject(
                    f"row_{index}_occurrence_{occurrence_index}",
                    {"type": "object"},
                    type(occurrence).__name__,
                )
                continue
            story_key = str(occurrence.get("storyKey") or "")
            source_file = str(occurrence.get("sourceFile") or "")
            occurrence_keys.add(story_key)
            if (
                not story_key
                or str(occurrence.get("scriptId") or "") != logic_id
                or source_file not in source_paths
            ):
                reject(
                    f"row_{index}_occurrence_{occurrence_index}_identity",
                    {"storyKey": "nonempty", "scriptId": logic_id, "sourceFile": "hashed"},
                    occurrence,
                )

        bridge = row.get("localContextBridge")
        if bridge is None:
            continue
        bridge_count += 1
        if not isinstance(bridge, dict):
            reject(f"row_{index}_bridge_object", {"type": "object"}, type(bridge).__name__)
            continue
        for field, expected in (
            ("classification", LOCAL_BRIDGE_CLASSIFICATION),
            ("missionOwnerStatus", "unresolved"),
            ("storyBinding", False),
            ("orderEvidence", False),
            ("missionGraphAction", "none"),
        ):
            if bridge.get(field) != expected:
                reject(f"row_{index}_bridge_{field}", expected, bridge.get(field))
        shared_keys = bridge.get("sharedStoryKeys") or []
        if not isinstance(shared_keys, list) or not set(shared_keys).issubset(occurrence_keys):
            reject(
                f"row_{index}_bridge_story_keys",
                {"subsetOfOccurrenceKeys": sorted(occurrence_keys)},
                shared_keys,
            )
        shared_story_count += len(shared_keys)
        actions = bridge.get("exactTargetActions")
        if not isinstance(actions, list) or not actions:
            reject(f"row_{index}_bridge_actions", {"nonemptyArray": True}, actions)
            continue
        for action_index, action in enumerate(actions):
            if not isinstance(action, dict):
                reject(
                    f"row_{index}_action_{action_index}",
                    {"type": "object"},
                    type(action).__name__,
                )
                continue
            if (
                action.get("actionName")
                not in {"ShowSceneDecorationNew", "ShowSceneDecorationWithHandle"}
                or action.get("serializedMemberCount") != 10
                or str(action.get("targetDynamicEntityLogicId") or "") != logic_id
                or str(action.get("sourceFile") or "") not in source_paths
            ):
                reject(
                    f"row_{index}_action_{action_index}_identity",
                    {
                        "actionName": ["ShowSceneDecorationNew", "ShowSceneDecorationWithHandle"],
                        "serializedMemberCount": 10,
                        "targetDynamicEntityLogicId": logic_id,
                        "sourceFile": "hashed",
                    },
                    action,
                )
            trigger = action.get("localTriggerVolumeContext")
            if trigger is None:
                continue
            trigger_context_count += 1
            if (
                not isinstance(trigger, dict)
                or trigger.get("status") != TRIGGER_CONTEXT_STATUS
                or trigger.get("schemaMappingId") != TRIGGER_SCHEMA_MAPPING_ID
                or trigger.get("foreignKeyBridgeFound") is not False
                or trigger.get("missionGraphAction") != "none"
            ):
                reject(
                    f"row_{index}_action_{action_index}_trigger_context",
                    {
                        "status": TRIGGER_CONTEXT_STATUS,
                        "schemaMappingId": TRIGGER_SCHEMA_MAPPING_ID,
                        "foreignKeyBridgeFound": False,
                        "missionGraphAction": "none",
                    },
                    trigger,
                )

    actual_counts = {
        "candidateRoots": len(rows),
        "storyOccurrences": occurrence_count,
        "exactTargetBridgeRoots": bridge_count,
        "sharedControlPathStoryOccurrences": shared_story_count,
        "exactLocalTriggerVolumeContexts": trigger_context_count,
        "triggerVolumeForeignKeyBridges": 0,
    }
    if actual_counts != EXPECTED_COUNTS:
        reject("recomputed_counts", EXPECTED_COUNTS, actual_counts)


def validate_dynamic_scene_context(
    artifact_path: Path = DEFAULT_ARTIFACT,
    *,
    export_root: Path = DEFAULT_EXPORT_ROOT,
    export_summary_path: Path = DEFAULT_EXPORT_SUMMARY,
    gameassembly: Path | None = None,
    metadata: Path | None = None,
) -> dict[str, Any]:
    """Return context plus deterministic validation diagnostics.

    Any drift removes ``dynamicSceneContext`` from the result.  Mission
    Pipeline can therefore omit this optional evidence without promoting stale
    or partly validated rows.
    """

    artifact_path = Path(artifact_path)
    export_root = Path(export_root)
    failures: list[dict[str, Any]] = []
    source_file = _source_file(artifact_path)

    def reject(gate: str, expected: Any, actual: Any, source: str = source_file) -> None:
        failures.append({
            "validator": "dynamicSceneStoryContext",
            "gate": gate,
            "sourceFile": source,
            "expected": expected,
            "actual": actual,
        })

    artifact, raw, error = _read_json(artifact_path)
    if error:
        reject("read_valid_artifact", {"readableJsonObject": True}, error)
    sources = artifact.get("sources") if isinstance(artifact.get("sources"), dict) else {}
    exact_gates = (
        ("schema", SCHEMA, artifact.get("schema")),
        ("status", "validated", artifact.get("status")),
        ("gameassembly_sha256", GAMEASSEMBLY_SHA256, str(sources.get("gameAssemblySha256") or "").upper()),
        ("metadata_sha256", METADATA_SHA256, str(sources.get("globalMetadataSha256") or "").upper()),
        ("dynamic_stream_sha256", DYNAMIC_STREAM_SHA256, str(sources.get("dynamicStreamingStreamSha256") or "").upper()),
        ("source_fingerprints", SOURCE_FINGERPRINTS, {
            str(key): str(value).upper()
            for key, value in (sources.get("installedSourceFingerprints") or {}).items()
        }),
    )
    for gate, expected, actual in exact_gates:
        if actual != expected:
            reject(gate, expected, actual)

    native = check_installed_native_inputs(
        GAMEASSEMBLY_SHA256,
        METADATA_SHA256,
        gameassembly=gameassembly,
        metadata=metadata,
    )
    if native.status != NATIVE_EVIDENCE_VALIDATED:
        reject(
            "installed_native_inputs",
            {"status": NATIVE_EVIDENCE_VALIDATED},
            {"status": native.status, "detail": native.detail},
        )

    summary, _summary_raw, summary_error = _read_json(Path(export_summary_path))
    if summary_error:
        reject(
            "read_export_summary",
            {"readableJsonObject": True},
            summary_error,
            _source_file(Path(export_summary_path)),
        )
    summary_fingerprints = {
        source: str(((summary.get("source_sizes") or {}).get(source) or {}).get("fingerprint") or "").upper()
        for source in SOURCE_FINGERPRINTS
    }
    if summary_fingerprints != SOURCE_FINGERPRINTS:
        reject(
            "export_source_fingerprints",
            SOURCE_FINGERPRINTS,
            summary_fingerprints,
            _source_file(Path(export_summary_path)),
        )

    source_rows = sources.get("levelScriptFiles")
    source_paths: set[str] = set()
    if not isinstance(source_rows, list):
        reject("levelscript_sources", {"type": "array"}, type(source_rows).__name__)
        source_rows = []
    seen_sources: set[str] = set()
    for index, row in enumerate(source_rows):
        if not isinstance(row, dict):
            reject(f"levelscript_source_{index}", {"type": "object"}, type(row).__name__)
            continue
        relative = str(row.get("path") or "")
        expected_sha = str(row.get("sha256") or "").upper()
        if not relative or relative in seen_sources:
            reject(f"levelscript_source_{index}_unique_path", {"uniqueNonempty": True}, relative)
            continue
        seen_sources.add(relative)
        source_paths.add(f"export_full/{relative}")
        resolved = _resolved_export_source(export_root, relative)
        if resolved is None or not resolved.is_file():
            reject(
                f"levelscript_source_{index}_exists",
                {"pathWithinExportRoot": relative, "isFile": True},
                str(resolved) if resolved is not None else "outside-export-root",
            )
            continue
        actual_sha = _sha256(resolved)
        if actual_sha != expected_sha:
            reject(
                f"levelscript_source_{index}_sha256",
                expected_sha,
                actual_sha,
                _source_file(resolved),
            )
    if len(source_paths) != EXPECTED_COUNTS["candidateRoots"]:
        reject("levelscript_source_count", EXPECTED_COUNTS["candidateRoots"], len(source_paths))

    context = artifact.get("context")
    _validate_context_rows(context, source_paths, reject)
    status = NATIVE_EVIDENCE_VALIDATED
    if failures:
        status = (
            native.status
            if native.status != NATIVE_EVIDENCE_VALIDATED
            else NATIVE_EVIDENCE_MISMATCHED
        )
    return {
        "schema": AUDIT_SCHEMA,
        "status": status,
        "sourceFile": source_file,
        "sourceSha256": hashlib.sha256(raw).hexdigest().upper() if raw else "",
        "dynamicSceneContext": context if not failures else None,
        "validationFailures": failures,
        "usesOcrOrManualOrder": False,
    }


def load_dynamic_scene_context(
    artifact_path: Path = DEFAULT_ARTIFACT,
    **validation_paths: Any,
) -> dict[str, Any] | None:
    """Load the exact non-owning context, or fail closed on any drift."""

    return validate_dynamic_scene_context(
        artifact_path,
        **validation_paths,
    ).get("dynamicSceneContext")


__all__ = [
    "AUDIT_SCHEMA",
    "DEFAULT_ARTIFACT",
    "EXPECTED_COUNTS",
    "SCHEMA",
    "load_dynamic_scene_context",
    "validate_dynamic_scene_context",
]
