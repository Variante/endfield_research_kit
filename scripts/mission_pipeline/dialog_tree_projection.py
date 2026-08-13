"""Publish hash-verified DialogTree definitions to exact quest observers."""
from __future__ import annotations

import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    path.write_text(encoded + "\n", encoding="utf-8", newline="\n")


def _repo_path(path: Path) -> str:
    path = path.resolve()
    return (
        path.relative_to(ROOT).as_posix()
        if path.is_relative_to(ROOT)
        else path.as_posix()
    )


def _natural_quest_key(value: str) -> tuple[str, int, str]:
    mission, marker, suffix = str(value).partition("_q#")
    try:
        number = int(suffix) if marker else 10**9
    except ValueError:
        number = 10**9
    return mission, number, suffix


def publish_quest_dialog_tree_definitions(
    index: dict[str, Any],
    output_root: Path,
    story_data_root: Path,
    language: str,
) -> dict[str, Any]:
    """Attach hash-verified DialogTree definitions to exact quest observers.

    MissionRuntime ``CheckTalkOptionFinish`` and
    ``CheckRepeatableTalkFinish`` prove that a quest observes a DialogTree
    root. The recovered TextAsset proves that root's internal graph; it does
    not prove which client action starts the dialog or add cross-file
    chronology.
    """
    sidecar_root = story_data_root / language.upper() / "mission"
    unique_story_keys: set[str] = set()
    placements = 0
    missions = 0
    quests = 0
    if not sidecar_root.is_dir():
        result = {
            "schema": "missionPipelineDialogTreeDefinitions.v1",
            "published": {
                "missions": 0,
                "quests": 0,
                "placements": 0,
                "uniqueStoryKeys": 0,
            },
        }
        index["dialogTreeDefinitions"] = result
        return result

    for summary in index.get("missions") or []:
        if not isinstance(summary, dict):
            continue
        mission_id = str(summary.get("id") or "")
        sidecar_path = sidecar_root / f"{mission_id}.json"
        mission_path = output_root / str(summary.get("file") or "")
        if not sidecar_path.is_file() or not mission_path.is_file():
            continue
        sidecar = _read_json(sidecar_path)
        timeline_recovery = (
            sidecar.get("timelineRecovery")
            if isinstance(sidecar, dict)
            else None
        )
        raw_definitions = (
            timeline_recovery.get("sceneDialogTreeEvidence")
            if isinstance(timeline_recovery, dict)
            else None
        )
        if not isinstance(raw_definitions, dict) or not raw_definitions:
            continue

        definitions: dict[str, dict[str, Any]] = {}
        for scene_key, raw in raw_definitions.items():
            if not isinstance(raw, dict):
                raise ValueError(
                    f"DialogTree evidence is not an object: {sidecar_path} {scene_key}"
                )
            source_file = str(raw.get("sourceFile") or "")
            source_sha256 = str(raw.get("sourceSha256") or "").upper()
            if (
                str(raw.get("sceneKey") or "") != str(scene_key)
                or raw.get("assetType") != "Beyond.Gameplay.DialogTree"
                or raw.get("evidenceKind") != "exact_dialog_tree_definition"
                or not re.fullmatch(r"[0-9A-F]{64}", source_sha256)
                or not source_file
            ):
                raise ValueError(
                    f"DialogTree evidence failed shape validation: "
                    f"{sidecar_path} {scene_key}"
                )
            source_path = (ROOT / source_file).resolve()
            if not source_path.is_relative_to(ROOT) or not source_path.is_file():
                raise ValueError(
                    f"DialogTree evidence source is missing/outside repo: "
                    f"{sidecar_path} {scene_key} {source_file}"
                )
            actual_sha256 = hashlib.sha256(source_path.read_bytes()).hexdigest().upper()
            if actual_sha256 != source_sha256:
                raise ValueError(
                    f"DialogTree evidence source hash mismatch: {sidecar_path} "
                    f"{scene_key} expected={source_sha256} actual={actual_sha256}"
                )
            definitions[str(scene_key)] = raw

        payload = _read_json(mission_path)
        if not isinstance(payload, dict):
            continue
        mission_placements = 0
        mission_quests: set[str] = set()
        mission_observed_dialogs: set[str] = set()
        for node in payload.get("nodes") or []:
            if not isinstance(node, dict):
                continue
            observers_by_dialog: dict[str, list[dict[str, Any]]] = defaultdict(list)

            def collect_observers(
                condition: Any,
                relation: str,
                objective_index: int | None = None,
            ) -> None:
                if isinstance(condition, list):
                    for child in condition:
                        collect_observers(child, relation, objective_index)
                    return
                if not isinstance(condition, dict):
                    return
                condition_type = str(condition.get("type") or "")
                facts = condition.get("facts")
                if (
                    condition_type in {
                        "CheckTalkOptionFinish",
                        "CheckRepeatableTalkFinish",
                    }
                    and isinstance(facts, dict)
                    and facts.get("dialogId")
                ):
                    dialog_id = str(facts["dialogId"])
                    observer = {
                        "relation": relation,
                        "conditionType": condition_type,
                    }
                    if objective_index is not None:
                        observer["objectiveIndex"] = objective_index
                    if "finishId" in facts:
                        observer["finishId"] = facts["finishId"]
                    if observer not in observers_by_dialog[dialog_id]:
                        observers_by_dialog[dialog_id].append(observer)
                for value in condition.values():
                    if isinstance(value, (dict, list)):
                        collect_observers(value, relation, objective_index)

            for objective in node.get("objectives") or []:
                if isinstance(objective, dict):
                    collect_observers(
                        objective.get("condition"),
                        "objective_condition",
                        objective.get("index"),
                    )
            collect_observers(node.get("failedCondition"), "failed_condition")
            observed_dialogs = set(observers_by_dialog)
            mission_observed_dialogs.update(observed_dialogs)
            rows = [
                {
                    **definitions[dialog_id],
                    "missionObservers": observers_by_dialog[dialog_id],
                }
                for dialog_id in sorted(observed_dialogs, key=_natural_quest_key)
                if dialog_id in definitions
            ]
            if not rows:
                continue
            node["dialogTreeDefinitions"] = rows
            mission_placements += len(rows)
            mission_quests.add(str(node.get("id") or ""))
            unique_story_keys.update(
                str(row.get("sceneKey") or "") for row in rows
            )
        unplaced = sorted(
            set(definitions) - mission_observed_dialogs,
            key=_natural_quest_key,
        )
        if unplaced:
            raise ValueError(
                "DialogTree definitions have no supported MissionRuntime "
                f"observer: mission={mission_id} source={sidecar_path} "
                f"expected={unplaced[:8]} "
                f"actual={sorted(mission_observed_dialogs, key=_natural_quest_key)[:16]}"
            )
        if not mission_placements:
            continue
        summary["dialogTreeDefinitionCount"] = mission_placements
        summary["dialogTreeDefinitionQuestCount"] = len(mission_quests)
        _write_json(mission_path, payload)
        placements += mission_placements
        quests += len(mission_quests)
        missions += 1

    result = {
        "schema": "missionPipelineDialogTreeDefinitions.v1",
        "evidencePolicy": (
            "Exact MissionRuntime CheckTalkOptionFinish or "
            "CheckRepeatableTalkFinish observer plus a typed, hash-verified "
            "current-game DialogTree TextAsset. Definition/internal branch "
            "evidence only; no activation or cross-file order promotion."
        ),
        "sourceRoot": _repo_path(sidecar_root),
        "published": {
            "missions": missions,
            "quests": quests,
            "placements": placements,
            "uniqueStoryKeys": len(unique_story_keys),
        },
    }
    index["dialogTreeDefinitions"] = result
    _write_json(output_root / "index.json", index)
    return result
