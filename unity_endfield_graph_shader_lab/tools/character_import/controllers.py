"""Exact UI AnimatorController evidence used by character manifests."""

from __future__ import annotations

import json
import zlib
from functools import lru_cache
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = PROJECT_ROOT.parent
CONTROLLER_ROOTS = (
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "StreamingAssets"
    / "json_by_type"
    / "AnimatorController",
    REPO_ROOT
    / "export_full"
    / "recovered"
    / "AnimeStudio-cli"
    / "Persistent"
    / "json_by_type"
    / "AnimatorController",
)


def _crc32(value: str) -> int:
    return zlib.crc32(value.encode("utf-8")) & 0xFFFFFFFF


@lru_cache(maxsize=1)
def _controller_documents() -> tuple[dict[str, dict[str, Any]], dict[int, dict[str, Any]]]:
    by_name: dict[str, dict[str, Any]] = {}
    by_path_id: dict[int, dict[str, Any]] = {}
    # Scan the installed baseline first and the Persistent patch overlay last,
    # matching Unity's current-data precedence for newly shipped controllers.
    for root in CONTROLLER_ROOTS:
        if not root.is_dir():
            continue
        for path in root.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            data["_source_json"] = str(path.resolve())
            name = str(data.get("m_Name") or "")
            if name:
                by_name[name.casefold()] = data
            path_id = int((data.get("$animestudio") or {}).get("pathId") or 0)
            if path_id:
                by_path_id[path_id] = data
    return by_name, by_path_id


def _names(document: dict[str, Any]) -> dict[int, str]:
    return {_crc32(str(item)): str(item) for item in document.get("m_TOSData") or []}


def _states(document: dict[str, Any]) -> list[dict[str, Any]]:
    machines = ((document.get("m_Controller") or {}).get("m_StateMachineArray") or [])
    if len(machines) != 1:
        raise RuntimeError(
            f"{document.get('m_Name')}: expected one UI state machine, found {len(machines)}"
        )
    return [item["data"] for item in machines[0]["data"]["m_StateConstantArray"]]


def _state_clip_path_id(document: dict[str, Any], state: dict[str, Any]) -> int:
    trees = state.get("m_BlendTreeConstantArray") or []
    nodes = trees[0]["data"].get("m_NodeArray") or [] if trees else []
    if not nodes:
        return 0
    index = int(nodes[0]["data"].get("m_ClipID") or 0)
    clips = document.get("m_AnimationClips") or []
    if index < 0 or index >= len(clips):
        return 0
    return int(clips[index].get("m_PathID") or 0)


def _state_records(document: dict[str, Any]) -> list[dict[str, Any]]:
    names = _names(document)
    records: list[dict[str, Any]] = []
    for index, state in enumerate(_states(document)):
        records.append(
            {
                "index": index,
                "name": names.get(int(state.get("m_NameID") or 0), ""),
                "path": names.get(int(state.get("m_PathID") or 0), ""),
                "path_hash": int(state.get("m_PathID") or 0),
                "clip_path_id": _state_clip_path_id(document, state),
                "loop": bool(state.get("m_Loop")),
                "state": state,
            }
        )
    return records


def _overview_clip_path_ids(document: dict[str, Any]) -> tuple[int, int] | None:
    """Return the serialized main Overview start/idle clip PPtrs.

    The controller filename is not a stable identity across exports: Unity's
    generated AnimatorController filename includes the build-local object id.
    The two clip PPtrs are stable evidence in the current controller document,
    so use them as the identity for the main UI handoff instead.
    """

    records = _state_records(document)
    by_path = {str(item["path"]): item for item in records}
    entrance = by_path.get("Overview.FromOveview")
    settled = by_path.get("Overview.OverviewIdle")
    if entrance is None or settled is None:
        return None
    start_path_id = int(entrance.get("clip_path_id") or 0)
    loop_path_id = int(settled.get("clip_path_id") or 0)
    if not start_path_id or not loop_path_id or start_path_id == loop_path_id:
        return None
    return start_path_id, loop_path_id


def _resolve_main_overview_document(character: dict[str, Any]) -> dict[str, Any] | None:
    """Resolve a current controller by its selected body clip PathIDs.

    ``m_Name`` is retained as a preference, not as the identity.  This lets a
    refreshed export resolve a controller whose numeric filename changed while
    refusing to guess when the selected clip pair is missing or ambiguous.
    """

    by_name, _ = _controller_documents()
    character_id = str(character.get("character_id") or "")
    preferred = by_name.get(f"{character_id}_controller".casefold())
    selected_ids = {
        int(item.get("PathID") or 0)
        for item in (character.get("ui_animation") or {}).get("selected_entries") or []
        if int(item.get("PathID") or 0)
    }

    documents: dict[str, dict[str, Any]] = {}
    for document in by_name.values():
        source = str(document.get("_source_json") or "")
        documents[source or f"{id(document)}"] = document

    matches: list[dict[str, Any]] = []
    for document in documents.values():
        try:
            pair = _overview_clip_path_ids(document)
        except (KeyError, IndexError, TypeError, ValueError, RuntimeError):
            # A malformed unrelated controller must not become a substitute
            # candidate.  The named candidate is checked strictly below.
            continue
        if pair is not None and set(pair).issubset(selected_ids):
            matches.append(document)

    if preferred is not None:
        try:
            preferred_pair = _overview_clip_path_ids(preferred)
        except (KeyError, IndexError, TypeError, ValueError, RuntimeError) as exc:
            raise RuntimeError(
                f"{character_id}: preferred UI controller is malformed"
            ) from exc
        if any(document is preferred for document in matches):
            return preferred
        if preferred_pair is not None:
            raise RuntimeError(
                f"{character_id}: current UI controller Overview clip PathIDs are "
                "outside the selected body UI set"
            )

    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        names = ", ".join(sorted(str(item.get("m_Name") or "") for item in matches))
        raise RuntimeError(
            f"{character_id}: selected Overview clip PathIDs match multiple UI controllers: {names}"
        )
    return None


def _controller_source_owns_prefab(
    document: dict[str, Any],
    character_id: str,
    prefab_name: str,
) -> bool:
    """Require the exported controller container to name this exact deco owner."""

    normalized = str((document.get("$animestudio") or {}).get("container") or "")
    normalized = normalized.replace("\\", "/").casefold().rstrip("/")
    prefab = str(prefab_name or "").casefold()
    character = str(character_id or "").casefold()
    if not prefab or not character or not prefab.startswith(f"{character}_deco_"):
        return False
    return normalized.endswith(
        f"/prefabs/uimodels/decoitems/{prefab}_controller.controller"
    )


def resolve_private_widget_controller(
    character_id: str,
    prefab_name: str,
    controller_path_id: int,
    required_clip_path_ids: set[int],
) -> dict[str, Any] | None:
    """Resolve a private widget controller from current PPtrs and clip ownership.

    The Animator PPtr is the preferred current-build owner edge.  If that PPtr
    is unavailable after an export refresh, the exact source container plus the
    selected state clip PathID set can recover it without consulting the old
    controller filename.  A resolved PPtr that fails either gate is rejected
    rather than replaced by a similarly shaped controller.
    """

    by_name, by_path_id = _controller_documents()
    required = {int(path_id) for path_id in required_clip_path_ids if int(path_id)}
    if not required:
        return None

    documents: dict[str, dict[str, Any]] = {}
    for document in by_name.values():
        source = str(document.get("_source_json") or "")
        documents[source or f"{id(document)}"] = document

    def matches(document: dict[str, Any]) -> bool:
        if not _controller_source_owns_prefab(document, character_id, prefab_name):
            return False
        state_clip_path_ids = {
            int(item.get("clip_path_id") or 0)
            for item in _state_records(document)
            if int(item.get("clip_path_id") or 0)
        }
        return required.issubset(state_clip_path_ids)

    pptr_document = by_path_id.get(int(controller_path_id or 0))
    if pptr_document is not None:
        return pptr_document if matches(pptr_document) else None

    candidates: list[dict[str, Any]] = []
    for document in documents.values():
        try:
            if matches(document):
                candidates.append(document)
        except (KeyError, IndexError, TypeError, ValueError, RuntimeError):
            continue
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        names = ", ".join(sorted(str(item.get("m_Name") or "") for item in candidates))
        raise RuntimeError(
            f"{character_id}/{prefab_name}: private widget clip set matches "
            f"multiple controllers: {names}"
        )
    return None


def recover_main_overview_controller(character: dict[str, Any]) -> dict[str, Any]:
    """Recover the exact controller entrance and start-to-idle transition."""

    character_id = str(character.get("character_id") or "")
    document = _resolve_main_overview_document(character)
    if document is None:
        return {}

    records = _state_records(document)
    entrance = next((item for item in records if item["path"] == "Overview.FromOveview"), None)
    settled = next((item for item in records if item["path"] == "Overview.OverviewIdle"), None)
    if entrance is None or settled is None:
        raise RuntimeError(f"{character_id}: controller lacks the canonical Overview states")

    transitions = entrance["state"].get("m_TransitionConstantArray") or []
    if len(transitions) != 1:
        raise RuntimeError(f"{character_id}: Overview.FromOveview has {len(transitions)} transitions")
    transition = transitions[0]["data"]

    machine = document["m_Controller"]["m_StateMachineArray"][0]["data"]
    entries = [
        item["data"]
        for item in machine.get("m_AnyStateTransitionConstantArray") or []
        if int(item["data"].get("m_DestinationState") or -1) == int(entrance["index"])
    ]
    if len(entries) != 1:
        raise RuntimeError(f"{character_id}: expected one AnyState Overview entrance, found {len(entries)}")
    entry = entries[0]

    selected = {
        int(item.get("PathID") or 0): str(item.get("Name") or "")
        for item in (character.get("ui_animation") or {}).get("selected_entries") or []
    }
    entrance_clip = selected.get(int(entrance["clip_path_id"]), "")
    settled_clip = selected.get(int(settled["clip_path_id"]), "")
    if not entrance_clip or not settled_clip:
        raise RuntimeError(
            f"{character_id}: controller Overview clips are outside the selected body UI set"
        )

    return {
        "controller_name": str(document.get("m_Name") or ""),
        "source_json": str(document.get("_source_json") or ""),
        "start_clip": entrance_clip,
        "loop_clip": settled_clip,
        "entry_normalized_offset": float(entry.get("m_TransitionOffset") or 0.0),
        "exit_normalized_time": float(transition.get("m_ExitTime") or 0.0),
        "transition_duration": float(transition.get("m_TransitionDuration") or 0.0),
        "transition_duration_fixed": bool(transition.get("m_HasFixedDuration")),
        "destination_normalized_offset": float(transition.get("m_TransitionOffset") or 0.0),
        "interruption_source": int(transition.get("m_InterruptionSource") or 0),
        "ordered_interruption": bool(transition.get("m_OrderedInterruption")),
        "blend_root_motion": bool(transition.get("m_EnableBlendRootMotion")),
        "entry_transition_conditions": [
            {
                "mode": int(condition["data"].get("m_ConditionMode") or 0),
                "parameter": _names(document).get(
                    int(condition["data"].get("m_EventID") or 0), ""
                ),
                "threshold": float(condition["data"].get("m_EventThreshold") or 0.0),
            }
            for condition in entry.get("m_ConditionConstantArray") or []
        ],
    }


def recover_controller_proven_widget_states(
    character: dict[str, Any],
    widget_clips: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Join body and private-deco clips by exact controller state path."""

    character_id = str(character.get("character_id") or "")
    main = _resolve_main_overview_document(character)
    if main is None:
        return []
    body_names = {
        int(item.get("PathID") or 0): str(item.get("Name") or "")
        for item in (character.get("ui_animation") or {}).get("selected_entries") or []
    }
    widget_by_id = {
        int(item.get("PathID") or 0): str(item.get("Name") or "")
        for item in (character.get("ui_animation") or {}).get("selected_companion_widget_entries") or []
    }
    imported = {
        (
            str(item.get("source_controller_clip_name") or item.get("name") or ""),
            str(item.get("widget_prefab") or ""),
        ): item
        for item in widget_clips
    }

    prefab_controllers: dict[str, dict[str, Any]] = {}
    hierarchy_root = Path(str((character.get("work_paths") or {}).get("widget_hierarchy") or ""))
    animator_root = hierarchy_root / "Animator"
    if animator_root.is_dir():
        for path in animator_root.glob("*.json"):
            animator = json.loads(path.read_text(encoding="utf-8"))
            prefab = str((animator.get("m_GameObject") or {}).get("Name") or animator.get("Name") or "")
            controller_id = int((animator.get("m_Controller") or {}).get("m_PathID") or 0)
            controller = _controller_documents()[1].get(controller_id)
            if prefab and controller is not None:
                prefab_controllers[prefab] = controller

    companions_by_state: dict[str, list[dict[str, Any]]] = {}
    for prefab, controller in prefab_controllers.items():
        for record in _state_records(controller):
            clip_name = widget_by_id.get(int(record["clip_path_id"]), "")
            clip = imported.get((clip_name, prefab))
            if clip is None:
                continue
            companions_by_state.setdefault(str(record["path"]), []).append(
                {"clip": clip, "loop": bool(record["loop"]), "controller": controller}
            )

    recovered: list[dict[str, Any]] = []
    for record in _state_records(main):
        body_clip = body_names.get(int(record["clip_path_id"]), "")
        companions = companions_by_state.get(str(record["path"])) or []
        if not body_clip or not companions:
            continue
        companion_clips = [item["clip"] for item in companions]
        recovered.append(
            {
                "label": f"{record['path']} / controller-proven body + UI item widget",
                "base_clip": body_clip,
                "source": "original_main_and_private_deco_animator_controllers",
                "confidence": "source_proven",
                "note": "exact matching original AnimatorController state path and clip PPtrs",
                "evidence_clips": [body_clip, *[str(item["name"]) for item in companion_clips]],
                "visible_props": sorted({str(item["widget_prop_path"]) for item in companion_clips}),
                "layers": [
                    {
                        "clip": str(item["clip"]["name"]),
                        "layer": index + 1,
                        "blend_mode": "blend",
                        "weight": 1.0,
                        "role": "ui_item_widget",
                        "controller_loop": bool(item["loop"]),
                        "controller_name": str(item["controller"].get("m_Name") or ""),
                    }
                    for index, item in enumerate(companions)
                ],
                "controller_state": {
                    "path": str(record["path"]),
                    "loop": bool(record["loop"]),
                },
            }
        )
    return recovered
