"""Emit per-mission story order for the WebUI.

For every mission with a `MissionRuntimeAsset/<mission>.json` plus meta:

1. **Quest DAG** is topologically sorted from
   `questDic[*].prevQuestIdList`.
2. **Opcode table** classifies LevelScript records by their `(code, kind)`
   pair into PlayCutscene / PlayLevelSeq / PlayRadio / SetQuestState.
   The table was derived from string-payload frequency on `indie_dg002`
   (see `scratch/opcode_audit.py`); 100% of records in each row carry
   one kind of string, so the inference is direct from the binary.
3. **Script ↔ quest bindings** come from two original-data signals, in
   decreasing strength:
     (a) `MissionRuntimeAsset/*.json` quest objectives with
         `CheckLevelScriptProperty*._scriptId.constValue.scriptId` —
         the named script must run before the quest can advance.
     (b) Cross-script `uint64` references embedded in each LevelScript
         binary — undirected edges; bindings BFS-propagate from (a).
4. Scripts are emitted in quest-DAG order. Within a script, play
   payloads are walked in on-disk byte order.

Output: `webui/data/assets/story_order.json`
"""
from __future__ import annotations
import argparse
import json
import re
import struct
import sys
from collections import defaultdict, deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from story_builder.level_bindings import (  # noqa: E402
    LEVELSCRIPT_OPCODE_TABLE,
    _build_uid_record_chains,
    _load_levelscript_binding_data,
    classify_levelscript_record,
    collect_leveltimeline_markers,
)
from story_builder.levelscript_binary import (  # noqa: E402
    decode_levelscript_binary_file,
    decode_levelscript_record_payload,
    decode_script_pointer_payload,
    levelscript_action_map_membership,
)

DATA_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MISSION_ASSET_ROOT = DATA_ROOT / "MissionRuntimeAsset"
LEVELSCRIPT_ROOT = DATA_ROOT / "LevelScriptData"
LEVELDATA_ROOT = DATA_ROOT / "LevelData"
WEBUI_CONV_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
WEBUI_MISSION_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
OUTPUT_PATH = ROOT / "webui" / "data" / "assets" / "story_order.json"
OBSERVED_ORDER_HINTS_PATH = ROOT / "scripts" / "story_recovery" / "manual_observed_order_hints.json"

MISSION_ID_RE = re.compile(r"^[a-z][a-z0-9]*m[0-9]+(?:d[0-9]+)?$")

# The opcode table itself lives in `story_builder.level_bindings` as
# `LEVELSCRIPT_OPCODE_TABLE` so scene_graph and other builders can reuse it.
OPCODE_TABLE = LEVELSCRIPT_OPCODE_TABLE
CONTROL_RECORD_CLASSES = {
    (0x0455, 0x0A): "script-id-pointer-ref",
    (0x045D, 0x0A): "script-id-pointer-ref",
    (0x0101, 0x24): "control-state-script-ref",
}


def repo_rel(path: Path | str) -> str:
    raw_path = Path(path)
    try:
        return raw_path.resolve().relative_to(ROOT.resolve()).as_posix()
    except (OSError, ValueError):
        return raw_path.as_posix()


def payload_to_entry_key(text: str, mission_id: str) -> str | None:
    """Map a tagged ASCII payload to the WebUI conv-entry key, or None
    if it does not correspond to a user-facing story unit."""
    if not isinstance(text, str):
        return None
    # `cs_<mission>_<N>` is the asset stem for `cutscene_<mission>_<N>`.
    m = re.match(r"^cs_(" + re.escape(mission_id) + r")_(\d+)(?:[_.].*)?$", text)
    if m:
        return f"cutscene_{m.group(1)}_{m.group(2)}"
    if text.startswith(f"cutscene_{mission_id}_"):
        return text.split("/", 1)[0]
    if text.startswith(f"radio_{mission_id}_"):
        return text
    if text.startswith(f"dlg_{mission_id}_"):
        return f"misc_{text}"
    return None


def list_conv_keys_for_mission(mission_id: str) -> list[str]:
    if not WEBUI_CONV_ROOT.is_dir():
        return []
    out: list[str] = []
    token_re = re.compile(rf"(^|_){re.escape(mission_id)}(_|$)")
    for path in sorted(WEBUI_CONV_ROOT.iterdir()):
        if path.is_file() and path.suffix == ".json" and token_re.search(path.stem):
            out.append(path.stem)
    return out


def bound_video_scene_for_conv_key(conv_key: str, mission_id: str) -> str | None:
    """Return an explicit timeline-playable story binding for a video entry."""
    path = WEBUI_CONV_ROOT / f"{conv_key}.json"
    if not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if payload.get("kind") != "video":
        return None

    scenes: set[str] = set()
    for row in payload.get("narrativeVideos") or []:
        if not isinstance(row, dict):
            continue
        binding = row.get("binding")
        if not isinstance(binding, dict):
            debug = row.get("_debug") if isinstance(row.get("_debug"), dict) else {}
            source = debug.get("source") if isinstance(debug.get("source"), dict) else {}
            binding = source.get("binding") if isinstance(source, dict) else None
        if not isinstance(binding, dict) or binding.get("isHint"):
            continue
        source_kinds = {str(value or "") for value in binding.get("sourceKinds") or [] if value}
        if "timelinePlayable" not in source_kinds:
            continue
        scene = str(binding.get("scene") or "")
        if scene.startswith(f"cutscene_{mission_id}_") or scene.startswith(f"radio_{mission_id}_"):
            scenes.add(scene)
    if len(scenes) == 1:
        return next(iter(scenes))
    return None


def load_observed_order_hint(mission_id: str) -> dict:
    """Load human-observed gameplay order hints for calibration-only missions."""
    if not OBSERVED_ORDER_HINTS_PATH.is_file():
        return {}
    try:
        payload = json.loads(OBSERVED_ORDER_HINTS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    hint = payload.get(mission_id)
    return hint if isinstance(hint, dict) else {}


def apply_observed_order_hint(
    mission_id: str,
    ordered: list[str],
    entry_details: list[dict],
) -> tuple[list[str], list[dict]]:
    """Apply partial gameplay-observed order while keeping recovered evidence.

    These hints are intentionally labelled as calibration evidence, not firm
    original-data recovery. They let us compare the static-data recovery surface
    against a real playthrough without losing the previous inferred evidence.
    """
    hint = load_observed_order_hint(mission_id)
    hint_order = [
        str(key or "")
        for key in hint.get("order") or []
        if str(key or "")
    ]
    if len(hint_order) < 2:
        return ordered, entry_details

    present_order_keys = set(ordered)
    seen_hint: set[str] = set()
    observed_keys: list[str] = []
    for key in hint_order:
        if key in seen_hint or key not in present_order_keys:
            continue
        seen_hint.add(key)
        observed_keys.append(key)
    if len(observed_keys) < 2:
        return ordered, entry_details

    details_by_key = {
        str(entry.get("key") or ""): entry
        for entry in entry_details
        if entry.get("key")
    }
    source = str(hint.get("source") or "observed-gameplay")
    note = str(hint.get("note") or "Gameplay-observed order calibration.")
    alignments = hint.get("evidenceAlignments")
    alignments_by_key = alignments if isinstance(alignments, dict) else {}
    for index, key in enumerate(observed_keys):
        entry = details_by_key.get(key)
        if not entry:
            continue
        recovered_evidence = entry.get("evidence") or ""
        recovered_rank = entry.get("rank")
        entry.setdefault("recoveredEvidenceBeforeObserved", entry.get("evidence") or "")
        entry.setdefault("recoveredPhaseBeforeObserved", entry.get("phase"))
        entry.setdefault("recoveredRankBeforeObserved", entry.get("rank"))
        entry["observedOrderIndex"] = index
        entry["observedOrderSource"] = source
        entry["observedOrderNote"] = note

        alignment = alignments_by_key.get(key)
        if isinstance(alignment, dict):
            status = str(alignment.get("status") or "partial")
            evidence = str(alignment.get("evidence") or "observed-gameplay-calibration")
            entry["observedEvidenceAlignmentStatus"] = status
            entry["observedEvidenceAlignment"] = str(alignment.get("kind") or evidence)
            alignment_note = str(alignment.get("note") or "")
            if alignment_note:
                entry["observedEvidenceAlignmentNote"] = alignment_note
            source_refs = [
                str(value)
                for value in alignment.get("sourceRefs") or []
                if str(value)
            ]
            if source_refs:
                entry["observedEvidenceAlignmentSourceRefs"] = source_refs[:6]
            try:
                entry["rank"] = int(alignment.get("rank"))
            except (TypeError, ValueError):
                entry["rank"] = 6
            entry["evidence"] = evidence
            entry["observedEvidenceGap"] = status in {"gap", "unresolved"}
            continue

        try:
            old_rank = int(recovered_rank)
        except (TypeError, ValueError):
            old_rank = 99
        if recovered_evidence and old_rank <= 2:
            entry["observedEvidenceAlignmentStatus"] = "source-backed"
            entry["observedEvidenceAlignment"] = recovered_evidence
            entry["observedEvidenceAlignmentNote"] = (
                "The observed row keeps direct decoded source evidence; the "
                "calibration changes relative placement, not the row identity."
            )
            entry["evidence"] = f"observed-compatible:{recovered_evidence}"
            entry["rank"] = 4
            entry["observedEvidenceGap"] = False
        elif recovered_evidence and recovered_evidence != "webui-conv-fallback":
            entry["observedEvidenceAlignmentStatus"] = "partial"
            entry["observedEvidenceAlignment"] = recovered_evidence
            entry["observedEvidenceAlignmentNote"] = (
                "The observed row has decoded/static evidence, but that "
                "evidence does not by itself prove the observed relative order."
            )
            entry["evidence"] = "observed-gameplay-calibration"
            entry["rank"] = 6
            entry["observedEvidenceGap"] = False
        else:
            entry["observedEvidenceAlignmentStatus"] = "gap"
            entry["observedEvidenceAlignment"] = "unresolved-static-source"
            entry["observedEvidenceAlignmentNote"] = (
                "No decoded MissionRuntime, LevelData, or LevelScript order "
                "source currently explains this observed placement."
            )
            entry["evidence"] = "observed-gameplay-calibration"
            entry["rank"] = 6
            entry["observedEvidenceGap"] = True

    observed_set = set(observed_keys)
    new_order = [
        *observed_keys,
        *[key for key in ordered if key not in observed_set],
    ]
    new_details = [
        details_by_key[key]
        for key in new_order
        if key in details_by_key
    ]
    return new_order, new_details


def quest_topo_order(quest_dic: dict) -> list[str]:
    prev = {qid: list(q.get("prevQuestIdList") or []) for qid, q in quest_dic.items()}
    placed: list[str] = []
    placed_set: set[str] = set()
    pending = set(quest_dic)
    while pending:
        progress = False
        for qid in sorted(pending):
            if all((p in placed_set) or (p not in quest_dic) for p in prev[qid]):
                placed.append(qid)
                placed_set.add(qid)
                pending.discard(qid)
                progress = True
        if not progress:
            placed.extend(sorted(pending))
            break
    return placed


def walk_property_check_script_ids(quest: dict, qid: str, out: dict[int, str]) -> None:
    def visit(obj):
        if isinstance(obj, dict):
            t = obj.get("$type", "")
            if "CheckLevelScriptProperty" in t:
                cv = (obj.get("_scriptId") or {}).get("constValue") or {}
                sid = cv.get("scriptId")
                if isinstance(sid, int):
                    # Don't overwrite — earliest quest wins (mission DAG order).
                    out.setdefault(sid, qid)
            for v in obj.values():
                visit(v)
        elif isinstance(obj, list):
            for it in obj:
                visit(it)
    visit(quest)


def walk_property_check_conditions(quest: dict, qid: str, out: list[dict]) -> None:
    def visit(obj):
        if isinstance(obj, dict):
            type_name = str(obj.get("$type", ""))
            script_id = ((obj.get("_scriptId") or {}).get("constValue") or {}).get("scriptId")
            if "CheckLevelScriptProperty" in type_name and isinstance(script_id, int):
                key = ((obj.get("_key") or {}).get("constValue") or "")
                out.append({
                    "questId": qid,
                    "scriptId": str(script_id),
                    "key": str(key or ""),
                    "type": type_name,
                })
            for value in obj.values():
                visit(value)
        elif isinstance(obj, list):
            for item in obj:
                visit(item)
    visit(quest)


def _script_id_sort_key(stem: str):
    try:
        return (0, int(stem))
    except ValueError:
        return (1, stem)


# Parses an authored content number out of a WebUI entry key. The designer
# numbering is the strongest within-phase ordering signal we have:
#   radio_<m>_1d5      -> 1.5
#   radio_<m>_2d8      -> 2.8
#   misc_dlg_<m>_0d9   -> 0.9
#   cutscene_<m>_3     -> 3.0
#   radio_<m>_16_1     -> 16.001  (variant under radio_16)
# Returns +inf for keys with no parseable suffix (named cutscenes like
# `cutscene_<m>_lookingatpatriot`, env entries, etc.).
_CONTENT_NUM_RE = re.compile(r"_(\d+)(?:d(\d+))?(?:_(\d+))?$")
_LEVELSEQ_NUM_RE = re.compile(r"^levelseq_([a-z0-9]+m[0-9]+(?:d[0-9]+)?)_(\d+)(?:_|$)")
_ORDINAL_NAME_RE = re.compile(r"_(\d+)(?:st|nd|rd|th)([A-Z][a-z]+)")


def parse_content_number(text: str) -> float:
    """Extract a designer-authored ordering float from a payload key."""
    if not isinstance(text, str) or not text:
        return float("inf")
    m = _CONTENT_NUM_RE.search(text)
    if not m:
        return float("inf")
    base = int(m.group(1))
    frac = 0.0
    if m.group(2) is not None:
        sub = m.group(2)
        frac = int(sub) / (10 ** len(sub))
    elif m.group(3) is not None:
        # `_N` variant suffix; keep it adjacent to its parent at +N/1000.
        frac = int(m.group(3)) / 1000.0
    return float(base) + frac


def script_min_content_number(payload_keys: list[str]) -> float:
    """Minimum authored content number across a script's payloads —
    radios and cutscenes are numbered in narrative order so this maps
    cleanly onto a story-position float. Dialog entries (misc_dlg_*,
    dlg_*) are skipped: their `0dN` naming uses a different scale and
    would falsely promote `misc_dlg_<m>_0d5` (value 0.5) above
    `radio_<m>_1` (value 1.0)."""
    best = float("inf")
    for key in payload_keys:
        if key.startswith(("misc_dlg_", "dlg_", "env_", "sns_", "black_")):
            continue
        n = parse_content_number(key)
        if n < best:
            best = n
    return best


def parse_levelseq_number(text: str, mission_id: str) -> float | None:
    """Return an authored numeric levelseq index from a LevelScript payload.

    `levelseq_<mission>_001` style strings are binary payloads from the
    original game data. They are a stronger cross-file phase anchor than radio
    or cutscene filename suffixes, which can be local to a subsystem.
    """
    if not isinstance(text, str):
        return None
    match = _LEVELSEQ_NUM_RE.match(text)
    if not match or match.group(1) != mission_id:
        return None
    try:
        return float(int(match.group(2)))
    except ValueError:
        return None


def source_script_id_from_file(source_file: str) -> str:
    text = str(source_file or "").replace("\\", "/")
    if "/LevelScriptData/" not in text:
        return ""
    stem = text.rsplit("/", 1)[-1]
    return stem[:-5] if stem.endswith(".json") else stem


def mission_level_ids(mission_id: str, primary_level_id: str) -> list[str]:
    """Return the main mission level plus secondary original-data level refs.

    Some mission bundles include scene bindings recovered from sub-mission
    LevelData on another level. Those are still original game data and should
    be visible to the story-order scan, but the MissionRuntime meta only names
    the primary level.
    """
    out: list[str] = []

    def add(level_id: str) -> None:
        level_id = str(level_id or "")
        if level_id and level_id not in out:
            out.append(level_id)

    add(primary_level_id)
    path = WEBUI_MISSION_ROOT / f"{mission_id}.json"
    if not path.is_file():
        return out
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    for ref in ((payload.get("extras") or {}).get("levelRefs") or []):
        if isinstance(ref, dict):
            add(ref.get("levelId") or "")
    return out


def mission_leveldata_files(mission_id: str, primary_level_id: str) -> set[str]:
    """Return LevelData files that belong to this mission's source surface.

    Primary mission levels keep the existing broad scan because e0m0-style
    story beats can live in sibling sub-LevelData files. Secondary levels are
    restricted to explicit mission bundle refs so unrelated missions on that
    level do not leak marker diagnostics into this mission.
    """
    out: set[str] = set()
    primary_dir = LEVELDATA_ROOT / str(primary_level_id or "")
    if primary_dir.is_dir():
        for path in primary_dir.glob("*.json"):
            out.add(repo_rel(path))

    path = WEBUI_MISSION_ROOT / f"{mission_id}.json"
    if not path.is_file():
        return out
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return out
    for ref in ((payload.get("extras") or {}).get("levelRefs") or []):
        if isinstance(ref, dict) and ref.get("file"):
            out.add(str(ref["file"]).replace("\\", "/"))
    return out


def ordinal_name_hint(text: str) -> tuple[str, int, str] | None:
    """Extract authored ordinal labels such as `1stZipline` / `2ndZipline`.

    These labels are weaker than quest/property and levelseq anchors, but they
    are still literal strings from LevelScript payloads. They are useful for
    keeping later named variants near an already anchored first occurrence.
    """
    match = _ORDINAL_NAME_RE.search(str(text or ""))
    if not match:
        return None
    try:
        ordinal = int(match.group(1))
    except ValueError:
        return None
    token = f"{match.group(1)}{match.group(0).split(match.group(1), 1)[1]}"
    return match.group(2).lower(), ordinal, token


def load_timeline_event_hints(mission_id: str, quest_idx: dict[str, int]) -> dict[tuple[str, str], dict]:
    """Load per-scene/per-script hints from the generated mission bundle.

    These hints are derived from decoded original data by
    `mission_recovery.py`. They are used only after direct quest/property and
    levelseq evidence; filtering by the same LevelScript id avoids applying a
    chunk-level hint from one script to an unrelated occurrence of the same
    scene key. Spatial proximity candidates are deliberately excluded here:
    they are map/location diagnostics, not playback-order anchors.
    """
    path = WEBUI_MISSION_ROOT / f"{mission_id}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    timeline = payload.get("timelineRecovery") or {}
    scene_placement = timeline.get("scenePlacement") or {}
    hints: dict[tuple[str, str], dict] = {}

    def put(scene_key: str, script_id: str, hint: dict) -> None:
        if not scene_key or not script_id:
            return
        key = (scene_key, script_id)
        current = hints.get(key)
        candidate_key = (
            int(hint.get("priority", 99)),
            float(hint.get("distanceXZ", 10**9)),
            float(hint.get("questOrder", 10**9)),
        )
        current_key = (
            int(current.get("priority", 99)),
            float(current.get("distanceXZ", 10**9)),
            float(current.get("questOrder", 10**9)),
        ) if current else None
        if current is None or candidate_key < current_key:
            hints[key] = hint

    for scene_key, row in scene_placement.items():
        for source in row.get("questAttachSources") or []:
            if not isinstance(source, dict):
                continue
            quest_id = str(source.get("questId") or "")
            script_id = str(source.get("scriptId") or "")
            if quest_id not in quest_idx:
                continue
            put(scene_key, script_id, {
                "questId": quest_id,
                "questOrder": float(quest_idx[quest_id]),
                "source": source.get("source") or "questAttach",
                "priority": 0,
            })
    return hints


def rounded_float(value, digits: int = 3) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return round(number, digits)


def compact_vector3(value: object) -> dict[str, float] | None:
    if not isinstance(value, dict):
        return None
    out: dict[str, float] = {}
    for axis in ("x", "y", "z"):
        number = rounded_float(value.get(axis))
        if number is not None:
            out[axis] = number
    return out or None


def compact_spatial_candidate(candidate: dict) -> dict:
    pin = candidate.get("pin") if isinstance(candidate.get("pin"), dict) else {}
    out: dict[str, object] = {}
    for key in (
        "source",
        "strength",
        "questId",
        "flowIndex",
        "questOrder",
        "levelId",
        "mapId",
        "scriptId",
    ):
        value = candidate.get(key)
        if value not in (None, "", [], {}):
            out[key] = value
    offset = candidate.get("offset")
    if offset is not None:
        try:
            out["offset"] = int(offset)
        except (TypeError, ValueError):
            pass
    for key in ("distanceXZ", "distance3d", "yDelta"):
        value = rounded_float(candidate.get(key))
        if value is not None:
            out[key] = value
    position = compact_vector3(candidate.get("position"))
    if position:
        out["position"] = position
    if pin:
        for source_key, out_key in (
            ("label", "pinLabel"),
            ("missionAreaId", "pinMissionAreaId"),
            ("trackingType", "pinTrackingType"),
            ("sourceType", "pinSourceType"),
            ("mapId", "pinMapId"),
        ):
            value = pin.get(source_key)
            if value not in (None, "", [], {}):
                out[out_key] = value
        pin_position = compact_vector3(pin.get("position"))
        if pin_position:
            out["pinPosition"] = pin_position
    return out


def load_spatial_candidates(mission_id: str) -> dict[str, list[dict]]:
    """Load compact map-position candidates from mission timeline recovery.

    The candidates compare decoded LevelScript vector literals with recovered
    quest/map pins. They are location evidence, not standalone scene-to-scene
    order proof. The sorter can use coherent direct same-script candidates only
    to override a weak suffix fallback for an otherwise raw-ordered script
    cluster.
    """
    path = WEBUI_MISSION_ROOT / f"{mission_id}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scene_placement = ((payload.get("timelineRecovery") or {}).get("scenePlacement") or {})
    out: dict[str, list[dict]] = {}
    for scene_key, row in scene_placement.items():
        if not isinstance(row, dict):
            continue
        candidates = [
            compact_spatial_candidate(candidate)
            for candidate in row.get("spatialQuestCandidates") or []
            if isinstance(candidate, dict)
        ]
        candidates = [candidate for candidate in candidates if candidate.get("questId")]
        if not candidates:
            continue
        candidates.sort(key=lambda candidate: (
            float(candidate.get("questOrder", 10**9)),
            float(candidate.get("distanceXZ", 10**9)),
            _script_id_sort_key(str(candidate.get("scriptId") or "")),
            int(candidate.get("offset") or 0),
        ))
        out[str(scene_key)] = candidates
    return out


def spatial_evidence_for_entry(spatial_by_key: dict[str, list[dict]], scene_key: str, stem: str) -> dict:
    candidates = spatial_by_key.get(scene_key) or []
    if not candidates:
        return {}
    script_id = str(stem or "").rsplit("/", 1)[-1]
    direct = [candidate for candidate in candidates if str(candidate.get("scriptId") or "") == script_id]
    related = [candidate for candidate in candidates if str(candidate.get("scriptId") or "") != script_id]
    out: dict[str, object] = {
        "spatialCandidateCount": len(candidates),
        "spatialNote": (
            "Map-position proximity compares decoded LevelScript vectors with "
            "quest pins; it supports location/quest vicinity and only overrides "
            "weak suffix order for coherent same-script raw-order clusters."
        ),
    }
    if direct:
        out["spatialQuestCandidates"] = direct[:4]
    if related:
        out["spatialRelatedQuestCandidates"] = related[:4]
    return out


def _compact_leveltimeline_story_marker(marker: dict, occurrence: dict, endpoint: str) -> dict:
    relations: list[str] = []
    for pair in marker.get("resolvedPairs") or []:
        relation = str(pair.get("relation") or "")
        if relation and relation not in relations:
            relations.append(relation)
    out = {
        "marker": marker.get("marker") or "",
        "kind": marker.get("kind") or "",
        "endpoint": endpoint,
        "status": marker.get("status") or "",
        "levelId": marker.get("levelId") or "",
        "levelDataFile": marker.get("file") or "",
        "levelDataOffset": marker.get("textOffset"),
        "markerKey": marker.get("markerKey"),
        "sourceUid": marker.get("sourceUid") or "",
        "targetUid": marker.get("targetUid") or "",
        "sourceScript": occurrence.get("sourceScript") or "",
        "recordStart": occurrence.get("recordStart"),
        "recordClass": occurrence.get("recordClass") or "",
        "recordStrings": list(occurrence.get("recordStrings") or [])[:6],
        "recordPlainStrings": list(occurrence.get("recordPlainStrings") or [])[:6],
    }
    if relations:
        out["relations"] = relations[:4]
    return {key: value for key, value in out.items() if value not in (None, "", [], {})}


def build_leveltimeline_marker_event_map(
    markers: list[dict],
    mission_id: str,
) -> dict[tuple[str, str], list[dict]]:
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    seen: set[tuple] = set()
    for marker in markers:
        if marker.get("kind") != "p":
            continue
        if marker.get("status") not in {"same-record", "same-script"}:
            continue
        for endpoint, occurrences in (
            ("source", marker.get("sourceOccurrences") or []),
            ("target", marker.get("targetOccurrences") or []),
        ):
            for occurrence in occurrences:
                script_id = str(occurrence.get("sourceScript") or "")
                if not script_id:
                    continue
                for payload in occurrence.get("recordStrings") or []:
                    scene_key = payload_to_entry_key(str(payload or ""), mission_id)
                    if not scene_key:
                        continue
                    dedupe_key = (
                        scene_key,
                        script_id,
                        marker.get("marker") or "",
                        occurrence.get("recordStart"),
                    )
                    if dedupe_key in seen:
                        continue
                    seen.add(dedupe_key)
                    out[(scene_key, script_id)].append(
                        _compact_leveltimeline_story_marker(marker, occurrence, endpoint)
                    )
    for rows in out.values():
        rows.sort(key=lambda row: (
            str(row.get("levelDataFile") or ""),
            int(row.get("levelDataOffset") or 0),
            str(row.get("endpoint") or ""),
            int(row.get("recordStart") or 0),
        ))
    return out


def compact_scene_edge(edge: dict) -> dict:
    out: dict[str, object] = {}
    for key in ("direction", "neighbor", "kind"):
        value = edge.get(key)
        if value not in (None, "", [], {}):
            out[key] = value
    source_files = [str(value or "") for value in edge.get("sourceFiles") or [] if value]
    if source_files:
        out["sourceFiles"] = source_files[:4]
        scripts: list[str] = []
        for source_file in source_files:
            script = source_script_id_from_file(source_file)
            if script and script not in scripts:
                scripts.append(script)
        if scripts:
            out["sourceScripts"] = scripts[:4]
    level_ids = [str(value or "") for value in edge.get("levelIds") or [] if value]
    if level_ids:
        out["levelIds"] = level_ids[:4]
    positions = [value for value in edge.get("positions") or [] if isinstance(value, int)]
    if positions:
        out["positions"] = positions[:8]
    return out


def load_scene_placement_evidence(mission_id: str) -> dict[str, dict]:
    """Load compact source-backed scene-edge diagnostics from mission recovery."""
    path = WEBUI_MISSION_ROOT / f"{mission_id}.json"
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    scene_placement = ((payload.get("timelineRecovery") or {}).get("scenePlacement") or {})
    out: dict[str, dict] = {}
    for scene_key, row in scene_placement.items():
        if not isinstance(row, dict):
            continue
        item: dict[str, object] = {}
        if row.get("chunkId"):
            item["sceneChunkId"] = row.get("chunkId")
        evidence_kinds = [str(value or "") for value in row.get("evidenceKinds") or [] if value]
        if evidence_kinds:
            item["sceneEvidenceKinds"] = evidence_kinds[:8]
        quest_ids = [str(value or "") for value in row.get("questIds") or [] if value]
        if quest_ids:
            item["sceneQuestIds"] = quest_ids[:8]
        incoming = [
            compact_scene_edge(edge)
            for edge in row.get("incomingEdges") or []
            if isinstance(edge, dict)
        ]
        outgoing = [
            compact_scene_edge(edge)
            for edge in row.get("outgoingEdges") or []
            if isinstance(edge, dict)
        ]
        incoming = [edge for edge in incoming if edge.get("neighbor")]
        outgoing = [edge for edge in outgoing if edge.get("neighbor")]
        if incoming:
            item["sceneIncomingEdges"] = incoming[:4]
        if outgoing:
            item["sceneOutgoingEdges"] = outgoing[:4]
        if item:
            item["scenePlacementNote"] = (
                "Mission timeline scene-edge diagnostics are original-data "
                "evidence. Same-script scene-chain edges can promote only "
                "weak suffix fallback groups; same-script file-order edges "
                "can reorder only local ties."
            )
            out[str(scene_key)] = item
    return out


def apply_scene_file_order_constraints(
    events: list[dict],
    scene_placement_by_key: dict[str, dict],
    terminal_branch_evidence_by_event: dict[tuple[str, str], list[dict]] | None = None,
) -> list[dict]:
    """Stably reorder local ties to satisfy direct same-script binary edges."""
    if len(events) < 2:
        return events
    event_by_key = {str(event.get("key") or ""): event for event in events if event.get("key")}
    initial_order = {key: index for index, key in enumerate(event_by_key)}
    edges: dict[str, set[str]] = defaultdict(set)
    incoming_count: dict[str, int] = {key: 0 for key in event_by_key}

    for source_key in event_by_key:
        placement = scene_placement_by_key.get(source_key) or {}
        for edge in placement.get("sceneOutgoingEdges") or []:
            if not isinstance(edge, dict):
                continue
            if edge.get("kind") != "levelscriptFileOrder":
                continue
            target_key = str(edge.get("neighbor") or "")
            if target_key not in event_by_key or target_key == source_key:
                continue
            source_event = event_by_key[source_key]
            target_event = event_by_key[target_key]
            source_stem = str(source_event.get("fileStem") or "")
            target_stem = str(target_event.get("fileStem") or "")
            edge_scripts = {str(value or "") for value in edge.get("sourceScripts") or [] if value}
            if not source_stem or source_stem != target_stem:
                continue
            if edge_scripts and source_stem not in edge_scripts:
                continue
            if source_event.get("_constraintPhase") != target_event.get("_constraintPhase"):
                continue
            if source_event.get("_constraintRank") != target_event.get("_constraintRank"):
                continue
            if target_key in edges[source_key]:
                continue
            edges[source_key].add(target_key)
            incoming_count[target_key] += 1

    terminal_memberships: dict[tuple[str, tuple[object, ...]], set[tuple[int, int]]] = defaultdict(set)
    terminal_rows: list[tuple[str, dict, tuple[object, ...]]] = []
    for source_key, event in event_by_key.items():
        source_stem = str(event.get("fileStem") or "")
        if not source_stem:
            continue
        for row in (terminal_branch_evidence_by_event or {}).get((source_key, source_stem)) or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("sourceScript") or "") != source_stem:
                continue
            visit_order = row.get("visitOrder")
            target_offset = row.get("targetOffset")
            terminal_offset = row.get("terminalOffset")
            terminal_local_id = row.get("terminalLocalId")
            branch_index = row.get("branchIndex")
            branch_root_local_id = row.get("branchRootLocalId")
            if not all(
                isinstance(value, int)
                for value in (
                    visit_order,
                    terminal_offset,
                    terminal_local_id,
                    branch_index,
                    branch_root_local_id,
                )
            ):
                continue
            # Branch root 0 is overloaded in the serialized data: sometimes it
            # is a real local action id, sometimes it is an empty/sentinel path.
            # Keep promotion to nonzero roots until that ambiguity is decoded.
            if branch_root_local_id <= 0:
                continue
            if not isinstance(target_offset, int):
                target_offset = 0
            terminal_key = (
                source_stem,
                terminal_offset,
                terminal_local_id,
            )
            terminal_memberships[(source_key, terminal_key)].add(
                (branch_index, branch_root_local_id)
            )
            terminal_rows.append((source_key, row, terminal_key))

    terminal_groups: dict[tuple[object, ...], dict[str, tuple[int, int]]] = defaultdict(dict)
    for source_key, row, terminal_key in terminal_rows:
        memberships = terminal_memberships.get((source_key, terminal_key)) or set()
        if len(memberships) != 1:
            continue
        event = event_by_key[source_key]
        source_stem, terminal_offset, terminal_local_id = terminal_key
        visit_order = row["visitOrder"]
        target_offset = row.get("targetOffset")
        branch_index = row["branchIndex"]
        branch_root_local_id = row["branchRootLocalId"]
        if not isinstance(target_offset, int):
            target_offset = 0
        group_key = (
            source_stem,
            terminal_offset,
            terminal_local_id,
            branch_index,
            branch_root_local_id,
            event.get("_constraintPhase"),
            event.get("_constraintRank"),
        )
        current = terminal_groups[group_key].get(source_key)
        candidate = (visit_order, target_offset)
        if current is None or candidate < current:
            terminal_groups[group_key][source_key] = candidate

    for grouped in terminal_groups.values():
        if len(grouped) < 2:
            continue
        ordered = sorted(
            grouped.items(),
            key=lambda item: (item[1][0], item[1][1], initial_order.get(item[0], 10**9)),
        )
        for (source_key, source_order), (target_key, target_order) in zip(ordered, ordered[1:]):
            if source_order == target_order:
                continue
            if target_key in edges[source_key]:
                continue
            edges[source_key].add(target_key)
            incoming_count[target_key] += 1

    if not any(edges.values()):
        return events

    ready = sorted(
        [key for key, count in incoming_count.items() if count == 0],
        key=lambda key: initial_order[key],
    )
    ordered_keys: list[str] = []
    while ready:
        key = ready.pop(0)
        ordered_keys.append(key)
        for target_key in sorted(edges.get(key) or (), key=lambda item: initial_order[item]):
            incoming_count[target_key] -= 1
            if incoming_count[target_key] == 0:
                ready.append(target_key)
                ready.sort(key=lambda item: initial_order[item])

    if len(ordered_keys) != len(event_by_key):
        # Do not invent cycle-breaking semantics.
        return events
    return [event_by_key[key] for key in ordered_keys]


def extract_cross_script_refs(level_id: str) -> dict[str, set[int]]:
    """Per script stem, return the set of *other* script IDs whose
    8-byte little-endian id literal appears in the binary."""
    level_dir = LEVELSCRIPT_ROOT / level_id
    if not level_dir.is_dir():
        return {}
    stems = [p.stem for p in level_dir.glob("*.json") if p.stem.isdigit()]
    script_ids = {int(s) for s in stems}
    out: dict[str, set[int]] = {}
    for stem in stems:
        self_id = int(stem)
        try:
            raw = (level_dir / f"{stem}.json").read_bytes()
        except OSError:
            continue
        found: set[int] = set()
        for target_id in sorted(script_ids):
            if target_id == self_id or target_id < 8000000000:
                continue
            needle = struct.pack("<Q", target_id)
            if raw.find(needle) >= 0:
                found.add(target_id)
        if found:
            out[stem] = found
    return out


def leveldata_script_refs(files_by_stem: dict[str, dict]) -> dict[str, dict]:
    """Return first LevelData file/offset plus neighbors for each script.

    This is diagnostic UI metadata. LevelData byte order is original decoded
    data, but it is not promoted into playback chronology by this builder.
    """
    key_by_level_script = {
        (str(file_info.get("levelId") or ""), str(file_info.get("sourceScript") or file_info.get("fileStem") or "")): stem
        for stem, file_info in files_by_stem.items()
    }
    ids_by_level: dict[str, set[int]] = defaultdict(set)
    for level_id, script_id in key_by_level_script:
        if script_id.isdigit():
            ids_by_level[level_id].add(int(script_id))

    out: dict[str, dict] = {}
    for level_id, script_ids in sorted(ids_by_level.items()):
        leveldata_dir = LEVELDATA_ROOT / level_id
        if not leveldata_dir.is_dir() or not script_ids:
            continue
        for path in sorted(leveldata_dir.glob("*.json")):
            try:
                raw = path.read_bytes()
            except OSError:
                continue
            hits: list[tuple[int, str, str]] = []
            for script_id in sorted(script_ids):
                needle = struct.pack("<Q", script_id)
                start = 0
                while True:
                    offset = raw.find(needle, start)
                    if offset < 0:
                        break
                    start = offset + 1
                    stem = key_by_level_script.get((level_id, str(script_id)))
                    if stem:
                        hits.append((offset, str(script_id), stem))
            if not hits:
                continue
            hits.sort(key=lambda item: item[0])
            sequence: list[tuple[int, str, str]] = []
            seen_scripts: set[str] = set()
            for offset, script_id, stem in hits:
                if stem in seen_scripts:
                    continue
                seen_scripts.add(stem)
                sequence.append((offset, script_id, stem))
            for index, (offset, script_id, stem) in enumerate(sequence):
                if stem in out:
                    continue
                prev_scripts = [item[1] for item in sequence[max(0, index - 2):index]]
                next_scripts = [item[1] for item in sequence[index + 1:index + 3]]
                out[stem] = {
                    "levelDataFile": repo_rel(path),
                    "levelDataOffset": offset,
                    "levelDataPrevScripts": prev_scripts,
                    "levelDataNextScripts": next_scripts,
                    "levelDataNote": "LevelData byte order/grouping only; not promoted as a playback edge.",
                }
    return out


def levelscript_binary_refs(files_by_stem: dict[str, dict]) -> dict[str, dict]:
    """Return compact binary field diagnostics for WebUI story-order entries."""
    out: dict[str, dict] = {}
    for stem, file_info in files_by_stem.items():
        source_script = str(file_info.get("sourceScript") or file_info.get("fileStem") or "")
        if not source_script.isdigit():
            continue
        rel_file = str(file_info.get("file") or "")
        if not rel_file:
            continue
        summary = decode_levelscript_binary_file(ROOT / rel_file, source_script)
        if not summary:
            continue
        out[stem] = {
            "binaryMemberCount": summary.get("serializedMemberCount"),
            "binaryExpectedMemberCount": summary.get("expectedMemberCount"),
            "binaryScriptIdVerified": bool(summary.get("scriptIdVerified")),
            "binaryScriptIdOffset": summary.get("probableScriptIdOffsetHex") or "",
            "binaryScriptIdOccurrenceCount": summary.get("scriptIdOccurrenceCount"),
            "binaryStartShapeList": summary.get("startShapeListStatus") or "",
            "binaryStartShapeListCount": summary.get("startShapeListCount"),
            "binaryStartType": summary.get("startTypeName") or "",
            "binaryStartTypeRaw": summary.get("startTypeRaw"),
            "binaryTaskMap": summary.get("taskMapStatus") or "",
            "binaryTaskMapCount": summary.get("taskMapCount"),
            "binaryTriggerVolumes": summary.get("triggerVolumesStatus") or "",
            "binaryTriggerVolumesCount": summary.get("triggerVolumesCount"),
            "binaryNote": summary.get("note") or "",
        }
    return out


def cross_ref_record_for_offset(records: list[dict], offset: int, data_len: int) -> dict | None:
    for index, record in enumerate(records):
        next_start = int(records[index + 1]["start"]) if index + 1 < len(records) else data_len
        payload_start = int(record.get("payloadStart", record.get("start", 0)))
        if payload_start <= offset < next_start:
            return record
    for index, record in enumerate(records):
        next_start = int(records[index + 1]["start"]) if index + 1 < len(records) else data_len
        start = int(record.get("start", 0))
        if start <= offset < next_start:
            return record
    return None


def semantic_record_class(record: dict | None) -> str:
    if not record:
        return ""
    base = classify_levelscript_record(record)
    if base:
        return base
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return CONTROL_RECORD_CLASSES.get((code, kind), "")
    return ""


def record_offset_relation(record: dict | None, offset: int) -> str:
    if not record:
        return "unmatched"
    start = int(record.get("start") or 0)
    payload_start = int(record.get("payloadStart", start) or start)
    if offset < start:
        return "before-record"
    if offset < payload_start:
        return "pre-payload"
    return "payload"


def levelscript_cross_ref_diagnostics(files_by_stem: dict[str, dict]) -> dict[str, dict]:
    """Return compact cross-script diagnostics for WebUI tooltips.

    These are original binary references, but they are intentionally not used
    for sorting because most target-record opcodes are still not decoded into
    directed start/end semantics.
    """
    ids_by_level: dict[str, set[int]] = defaultdict(set)
    stem_by_level_script: dict[tuple[str, str], str] = {}
    for stem, file_info in files_by_stem.items():
        level_id = str(file_info.get("levelId") or "")
        source_script = str(file_info.get("sourceScript") or file_info.get("fileStem") or "")
        if level_id and source_script.isdigit():
            ids_by_level[level_id].add(int(source_script))
            stem_by_level_script.setdefault((level_id, source_script), stem)

    outgoing: dict[str, list[dict]] = defaultdict(list)
    incoming: dict[str, list[dict]] = defaultdict(list)
    for stem, file_info in files_by_stem.items():
        level_id = str(file_info.get("levelId") or "")
        source_script = str(file_info.get("sourceScript") or file_info.get("fileStem") or "")
        if not level_id or not source_script.isdigit():
            continue
        rel_file = str(file_info.get("file") or "")
        if not rel_file:
            continue
        try:
            raw = (ROOT / rel_file).read_bytes()
        except OSError:
            continue
        source_id = int(source_script)
        records = list(file_info.get("records") or [])
        for target_id in sorted(ids_by_level.get(level_id) or []):
            if target_id == source_id:
                continue
            needle = struct.pack("<Q", target_id)
            start = 0
            while True:
                offset = raw.find(needle, start)
                if offset < 0:
                    break
                start = offset + 1
                record = cross_ref_record_for_offset(records, offset, len(raw))
                code = record.get("code") if record else None
                kind = record.get("kind") if record else None
                row = {
                    "levelId": level_id,
                    "sourceScript": source_script,
                    "targetScript": str(target_id),
                    "offset": offset,
                    "record": f"0x{int(code):04x}/0x{int(kind):02x}" if isinstance(code, int) and isinstance(kind, int) else "",
                    "class": semantic_record_class(record),
                    "relation": record_offset_relation(record, offset),
                }
                row.update(decode_script_pointer_payload(raw, record, target_offset=offset))
                outgoing[stem].append(row)
                target_stem = stem_by_level_script.get((level_id, str(target_id)))
                if target_stem:
                    incoming[target_stem].append(row)

    out: dict[str, dict] = {}
    for stem in files_by_stem:
        def distinct_refs(rows: list[dict], script_key: str) -> list[dict]:
            compact: list[dict] = []
            seen: set[tuple[str, str, str, str, str]] = set()
            for row in sorted(
                rows,
                key=lambda item: (_script_id_sort_key(item.get(script_key) or ""), int(item.get("offset") or 0)),
            ):
                key = (
                    str(row.get("sourceScript") or ""),
                    str(row.get("targetScript") or ""),
                    str(row.get("record") or ""),
                    str(row.get("class") or ""),
                    str(row.get("relation") or ""),
                    str(row.get("pointerScript") or ""),
                    str(row.get("pointerFlag") if row.get("pointerFlag") is not None else ""),
                )
                if key in seen:
                    continue
                seen.add(key)
                compact.append(row)
            return compact[:6]

        out_refs = distinct_refs(outgoing.get(stem, []), "targetScript")
        in_refs = distinct_refs(incoming.get(stem, []), "sourceScript")
        if not out_refs and not in_refs:
            continue
        out[stem] = {
            "binaryOutgoingScriptRefs": out_refs[:8],
            "binaryIncomingScriptRefs": in_refs[:8],
            "binaryScriptRefNote": "Cross-script uint64 refs are binary control evidence only; not promoted as playback edges.",
        }
    return out


def levelseq_numbers_for_script(file_info: dict, mission_id: str) -> list[tuple[int, float, str]]:
    out: list[tuple[int, float, str]] = []
    for hit in file_info.get("stringHits") or []:
        seq = parse_levelseq_number(hit.get("text"), mission_id)
        if seq is not None:
            out.append((int(hit.get("offset") or 0), seq, hit.get("text") or ""))
    return sorted(out)


def nearest_levelseq_number(levelseqs: list[tuple[int, float, str]], offset: int) -> tuple[float | None, str]:
    if not levelseqs:
        return None, ""
    prior = [item for item in levelseqs if item[0] <= offset]
    if prior:
        _, seq, text = prior[-1]
        return seq, text
    _, seq, text = levelseqs[0]
    return seq, text


def record_for_offset(file_info: dict, offset: int) -> dict | None:
    records = file_info.get("records") or []
    if not records:
        return None
    for idx, record in enumerate(records):
        next_start = records[idx + 1]["start"] if idx + 1 < len(records) else 10**18
        if record.get("payloadStart", record.get("start", 0)) <= offset < next_start:
            return record
    return None


def next_start_by_record_start(records: list[dict], data_len: int) -> dict[int, int | None]:
    starts: dict[int, int | None] = {}
    sorted_records = sorted(records, key=lambda row: int(row.get("start") or 0))
    for index, record in enumerate(sorted_records):
        start = int(record.get("start") or 0)
        starts[start] = (
            int(sorted_records[index + 1].get("start") or data_len)
            if index + 1 < len(sorted_records)
            else None
        )
    return starts


def script_payload_events_in_order(file_info: dict, mission_id: str) -> list[dict]:
    """Return user-facing story payload events in byte-offset order.

    UID `nextId` chains are still decoded by the shared loader, but for
    cross-file story ordering the safest primitive is the serialized payload
    position inside the original LevelScript blob. The event carries nearby
    record and levelseq context so the sorter can prefer stronger anchors.
    """
    seen: set[str] = set()
    out: list[dict] = []
    levelseqs = levelseq_numbers_for_script(file_info, mission_id)
    for hit in sorted(file_info.get("stringHits") or [], key=lambda item: item["offset"]):
        key = payload_to_entry_key(hit.get("text"), mission_id)
        if not key or key in seen:
            continue
        seen.add(key)
        offset = int(hit.get("offset") or 0)
        record = record_for_offset(file_info, offset)
        seq, seq_text = nearest_levelseq_number(levelseqs, offset)
        out.append({
            "key": key,
            "payload": hit.get("text") or "",
            "offset": offset,
            "fileStem": file_info.get("fileStem") or "",
            "file": file_info.get("file") or "",
            "recordStart": record.get("start") if record else None,
            "recordClass": classify_levelscript_record(record or {}),
            "recordCode": record.get("code") if record else None,
            "recordKind": record.get("kind") if record else None,
            "levelseq": seq,
            "levelseqText": seq_text,
        })
    return out


def script_payload_keys_in_order(file_info: dict, mission_id: str) -> list[str]:
    return [event["key"] for event in script_payload_events_in_order(file_info, mission_id)]


def build_terminal_branch_event_evidence(
    files_by_stem: dict[str, dict],
    mission_id: str,
    property_conditions_by_script: dict[str, list[dict]],
) -> dict[tuple[str, str], list[dict]]:
    """Map concrete story events reached by `0x0bed/0x00` branch refs.

    The branch record itself is not a user-facing scene. Its tail local ids are
    followed through split-list refs, nested branches, and `nextId` links; only
    reached play/story payload records are exposed here.
    """
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for stem, file_info in files_by_stem.items():
        records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
        if not records:
            continue
        file_path = Path(str(file_info.get("file") or ""))
        if not file_path.is_absolute():
            file_path = ROOT / file_path
        try:
            data = file_path.read_bytes()
        except OSError:
            continue

        next_by_start = next_start_by_record_start(records, len(data))
        by_local_id: dict[int, list[dict]] = defaultdict(list)
        for record in records:
            local_id = record.get("localId")
            if isinstance(local_id, int):
                by_local_id[local_id].append(record)

        events_by_record_start: dict[int, list[dict]] = defaultdict(list)
        for hit in sorted(file_info.get("stringHits") or [], key=lambda item: int(item.get("offset") or 0)):
            key = payload_to_entry_key(str(hit.get("text") or ""), mission_id)
            if not key:
                continue
            offset = int(hit.get("offset") or 0)
            record = record_for_offset(file_info, offset)
            if not record:
                continue
            events_by_record_start[int(record.get("start") or 0)].append({
                "key": key,
                "payload": hit.get("text") or "",
                "offset": offset,
                "recordStart": int(record.get("start") or 0),
                "recordClass": classify_levelscript_record(record or {}),
                "localId": record.get("localId"),
            })

        source_script = str(file_info.get("sourceScript") or stem)
        conditions = property_conditions_by_script.get(stem) or property_conditions_by_script.get(source_script) or []
        for record in records:
            if (record.get("code"), record.get("kind")) != (0x0BED, 0x00):
                continue
            start = int(record.get("start") or 0)
            decoded = decode_levelscript_record_payload(data, record, next_start=next_by_start.get(start))
            branch_refs = [
                int(ref)
                for ref in decoded.get("branchLocalRefs") or []
                if isinstance(ref, int)
            ]
            if not branch_refs:
                continue
            property_keys = [str(value) for value in decoded.get("propertyKeys") or [] if value]
            matching_conditions = [
                condition
                for condition in conditions
                if str(condition.get("key") or "") in property_keys
            ]

            seen_starts: set[int] = set()
            queue = deque(
                (ref, branch_index, ref, 0)
                for branch_index, ref in enumerate(branch_refs)
            )
            visit_order = 0
            while queue and visit_order < 96:
                local_id, branch_index, root_local_id, depth = queue.popleft()
                targets = by_local_id.get(local_id) or []
                for target in targets[:4]:
                    target_start = int(target.get("start") or 0)
                    if target_start in seen_starts:
                        continue
                    seen_starts.add(target_start)
                    visit_order += 1
                    target_decoded = decode_levelscript_record_payload(
                        data,
                        target,
                        next_start=next_by_start.get(target_start),
                    )
                    for event in events_by_record_start.get(target_start) or []:
                        evidence = {
                            "source": "levelscriptTerminalBranch",
                            "propertyKeys": property_keys,
                            "terminalLocalId": record.get("localId"),
                            "terminalOffset": start,
                            "terminalOffsetHex": f"0x{start:x}",
                            "branchLocalRefs": branch_refs,
                            "branchIndex": branch_index,
                            "branchRootLocalId": root_local_id,
                            "targetLocalId": target.get("localId"),
                            "targetOffset": target_start,
                            "targetOffsetHex": f"0x{target_start:x}",
                            "targetClass": classify_levelscript_record(target or {}),
                            "depth": depth,
                            "visitOrder": visit_order,
                            "sourceScript": source_script,
                        }
                        if matching_conditions:
                            evidence["questIds"] = sorted({
                                str(condition.get("questId") or "")
                                for condition in matching_conditions
                                if condition.get("questId")
                            })
                            evidence["conditionTypes"] = sorted({
                                str(condition.get("type") or "")
                                for condition in matching_conditions
                                if condition.get("type")
                            })
                        out[(event["key"], stem)].append({
                            key: value
                            for key, value in evidence.items()
                            if value not in ("", None, [], {})
                        })
                    if depth >= 8:
                        continue
                    next_id = target.get("nextId")
                    if isinstance(next_id, int) and next_id >= 0:
                        queue.append((next_id, branch_index, root_local_id, depth + 1))
                    for ref in target_decoded.get("localRecordRefs") or []:
                        if isinstance(ref, int):
                            queue.append((ref, branch_index, root_local_id, depth + 1))
                    for ref in target_decoded.get("branchLocalRefs") or []:
                        if isinstance(ref, int):
                            queue.append((ref, branch_index, root_local_id, depth + 1))

    for rows in out.values():
        rows.sort(key=lambda row: (
            int(row.get("terminalOffset") or 0),
            int(row.get("branchIndex") or 0),
            int(row.get("visitOrder") or 0),
            int(row.get("targetOffset") or 0),
        ))
    return out


def build_header_event_evidence(
    files_by_stem: dict[str, dict],
    mission_id: str,
) -> dict[tuple[str, str], list[dict]]:
    """Map story/play records reached from decoded headerList event starts.

    This is evidence surfacing only. `ActionHeader.nextId` gives a direct
    event-to-action edge, but runtime event conditions still decide when the
    header fires, so this function does not promote cross-scene order.
    """
    out: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for stem, file_info in files_by_stem.items():
        records = sorted(file_info.get("records") or [], key=lambda row: int(row.get("start") or 0))
        if not records:
            continue
        file_path = Path(str(file_info.get("file") or ""))
        if not file_path.is_absolute():
            file_path = ROOT / file_path
        try:
            data = file_path.read_bytes()
        except OSError:
            continue

        action_map, membership = levelscript_action_map_membership(data, records)
        if action_map.get("status") != "present":
            continue
        next_by_start = next_start_by_record_start(records, len(data))

        action_buckets: dict[int, list[dict]] = defaultdict(list)
        for record in records:
            local_id = record.get("localId")
            role = str(membership.get(int(record.get("start") or 0)) or "")
            if isinstance(local_id, int) and role.startswith("actionList"):
                action_buckets[local_id].append(record)
        action_by_local = {
            local_id: bucket[0]
            for local_id, bucket in action_buckets.items()
            if len(bucket) == 1
        }

        events_by_record_start: dict[int, list[dict]] = defaultdict(list)
        for hit in sorted(file_info.get("stringHits") or [], key=lambda item: int(item.get("offset") or 0)):
            key = payload_to_entry_key(str(hit.get("text") or ""), mission_id)
            if not key:
                continue
            offset = int(hit.get("offset") or 0)
            record = record_for_offset(file_info, offset)
            if not record:
                continue
            events_by_record_start[int(record.get("start") or 0)].append({
                "key": key,
                "payload": hit.get("text") or "",
                "offset": offset,
                "recordStart": int(record.get("start") or 0),
                "recordClass": classify_levelscript_record(record or {}),
                "localId": record.get("localId"),
            })

        source_script = str(file_info.get("sourceScript") or stem)
        for header in records:
            header_start = int(header.get("start") or 0)
            action_map_role = str(membership.get(header_start) or "")
            if not action_map_role.startswith("headerList"):
                continue
            decoded_header = decode_levelscript_record_payload(
                data,
                header,
                next_start=next_by_start.get(header_start),
                action_map_role=action_map_role,
            )
            action_header = decoded_header.get("actionHeader")
            if not isinstance(action_header, dict):
                continue
            target_local_id = action_header.get("nextId")
            if not isinstance(target_local_id, int) or target_local_id < 0:
                continue
            current = action_by_local.get(target_local_id)
            if current is None:
                continue
            seen_starts: set[int] = set()
            depth = 0
            visit_order = 0
            while current is not None and depth < 32:
                target_start = int(current.get("start") or 0)
                if target_start in seen_starts:
                    break
                seen_starts.add(target_start)
                visit_order += 1
                for event in events_by_record_start.get(target_start) or []:
                    evidence = {
                        "source": "levelscriptHeaderActionChain",
                        "headerLocalId": header.get("localId"),
                        "headerOffset": header_start,
                        "headerOffsetHex": f"0x{header_start:x}",
                        "headerOpcode": f"0x{int(header.get('code') or 0):04x}/0x{int(header.get('kind') or 0):02x}",
                        "headerEventText": [str(text) for text in header.get("texts") or [] if text][:6],
                        "targetLocalId": current.get("localId"),
                        "targetOffset": target_start,
                        "targetOffsetHex": f"0x{target_start:x}",
                        "targetClass": classify_levelscript_record(current or {}),
                        "depth": depth,
                        "visitOrder": visit_order,
                        "sourceScript": source_script,
                    }
                    out[(event["key"], stem)].append({
                        key: value
                        for key, value in evidence.items()
                        if value not in ("", None, [], {})
                    })
                next_id = current.get("nextId")
                if not isinstance(next_id, int) or next_id < 0:
                    break
                current = action_by_local.get(next_id)
                depth += 1

    for rows in out.values():
        rows.sort(key=lambda row: (
            int(row.get("headerOffset") or 0),
            int(row.get("visitOrder") or 0),
            int(row.get("targetOffset") or 0),
        ))
    return out


def build_mission_order(mission_id: str) -> dict | None:
    mission_path = MISSION_ASSET_ROOT / f"{mission_id}.json"
    meta_path = MISSION_ASSET_ROOT / f"{mission_id}_meta.json"
    if not mission_path.is_file() or not meta_path.is_file():
        return None
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    level_id = (
        (meta.get("acceptMode") or {}).get("levelId")
        or meta.get("levelId")
        or ""
    )
    if not level_id:
        return None
    level_ids = mission_level_ids(mission_id, level_id)

    mission = json.loads(mission_path.read_text(encoding="utf-8"))
    quest_dic = mission.get("questDic") or {}
    if not quest_dic:
        return None
    quest_order = quest_topo_order(quest_dic)
    quest_idx = {qid: i for i, qid in enumerate(quest_order)}

    # ---- Signal A: direct script↔quest binding via property checks. ----
    direct_script_to_quest: dict[int, str] = {}
    property_conditions: list[dict] = []
    # Track for each quest the order it first names a script — preserves the
    # quest's authoring order across multiple property checks.
    for qid in quest_order:
        walk_property_check_script_ids(quest_dic[qid], qid, direct_script_to_quest)
        walk_property_check_conditions(quest_dic[qid], qid, property_conditions)

    # ---- Load every binary on every source-backed level for this mission. ----
    files_by_stem: dict[str, dict] = {}
    for source_level_id in level_ids:
        info = _load_levelscript_binding_data(source_level_id)
        for file_info in info["files"]:
            stem = str(file_info.get("fileStem") or "")
            if not stem:
                continue
            key = stem
            if key in files_by_stem:
                key = f"{source_level_id}/{stem}"
            enriched = dict(file_info)
            enriched["fileStem"] = key
            enriched["sourceScript"] = stem
            enriched["levelId"] = source_level_id
            files_by_stem[key] = enriched
    leveldata_refs_by_stem = leveldata_script_refs(files_by_stem)
    binary_refs_by_stem = levelscript_binary_refs(files_by_stem)
    cross_refs_by_stem = levelscript_cross_ref_diagnostics(files_by_stem)
    leveltimeline_markers = collect_leveltimeline_markers(
        level_ids,
        leveldata_files=mission_leveldata_files(mission_id, level_id),
    )
    leveltimeline_markers_by_event = build_leveltimeline_marker_event_map(
        leveltimeline_markers,
        mission_id,
    )

    # Per-script play payload events.
    script_events: dict[str, list[dict]] = {}
    script_payloads: dict[str, list[str]] = {}
    for stem, fi in files_by_stem.items():
        events = script_payload_events_in_order(fi, mission_id)
        if events:
            script_events[stem] = events
            script_payloads[stem] = [event["key"] for event in events]

    if not script_payloads:
        return None

    # ---- Direct script ↔ quest bindings only (Signal A). ----
    # Direction-less cross-script uint64 refs (Signal B) are not used to
    # *create* bindings — that over-attributed scripts whose only role is
    # observing another script's property. Bound scripts instead act as
    # interpolation anchors for unbound scripts: an unbound script with a
    # numerically-nearby script id picks up its neighbour's quest phase.
    payload_stems = set(script_payloads)
    xrefs: dict[str, set[int]] = defaultdict(set)
    for source_level_id in level_ids:
        for stem, refs in extract_cross_script_refs(source_level_id).items():
            xrefs[stem].update(refs)

    # ---- Signal C: mission-start scripts. ----
    # A script that (a) has no quest binding, (b) references the master
    # controller and nothing else, and (c) is not referenced by any
    # other play script, is fired by the engine's mission-accept hook.
    # Drop it to phase = -1 so it sorts before all quest-bound content.
    # Identify the master as the script with the most quest strings
    # (already computed below for Signal A2). Re-use that detection here.
    quest_re_for_master = re.compile(rf"^{re.escape(mission_id)}_q#")
    quest_hits_count: dict[str, int] = {}
    for stem, fi in files_by_stem.items():
        n = sum(1 for h in fi["stringHits"] if quest_re_for_master.match(h["text"]))
        if n:
            quest_hits_count[stem] = n
    master_stem_for_start = (
        max(quest_hits_count, key=quest_hits_count.get) if quest_hits_count else None
    )

    referenced_by: dict[str, set[str]] = defaultdict(set)
    for src, tgts in xrefs.items():
        for tgt in tgts:
            referenced_by[str(tgt)].add(src)

    mission_start_scripts: set[str] = set()
    if master_stem_for_start:
        for stem in payload_stems:
            outgoing = {str(t) for t in xrefs.get(stem, ())}
            if outgoing != {master_stem_for_start}:
                continue
            # Nothing else points at this script either.
            if referenced_by.get(stem):
                continue
            mission_start_scripts.add(stem)

    script_to_quest: dict[str, str] = {}
    for sid, qid in direct_script_to_quest.items():
        stem = str(sid)
        if stem in payload_stems:
            script_to_quest[stem] = qid

    # ---- Signal A2: scripts that embed <mission>_q#N as a tagged string. ----
    # The master controller carries the whole quest table; any other script
    # mentioning a quest id is either (a) gated by that quest, or
    # (b) *advances* the mission to that quest after its play records fire.
    # Distinguish by byte-offset position:
    #   - if the quest reference is in the late portion of the binary AND
    #     the script has play-records earlier, treat it as an "advance-to"
    #     call. The play records happen during quest_idx - 1.
    #   - otherwise treat the quest reference as a gating condition that
    #     fires during the named quest.
    # Identify the master by quest-string count.
    quest_re = re.compile(rf"^{re.escape(mission_id)}_q#")
    quest_hits_per_script: dict[str, list[tuple[int, str]]] = {}
    for stem, fi in files_by_stem.items():
        hits = [(h["offset"], h["text"]) for h in fi["stringHits"] if quest_re.match(h["text"])]
        if hits:
            quest_hits_per_script[stem] = hits
    master_stem = (
        max(quest_hits_per_script, key=lambda s: len(quest_hits_per_script[s]))
        if quest_hits_per_script
        else None
    )

    PLAY_KINDS = {"play_levelseq", "play_cutscene", "play_radio", "play_dialog"}
    for stem, hits in quest_hits_per_script.items():
        if stem == master_stem or stem not in payload_stems:
            continue
        present = [(off, q) for off, q in hits if q in quest_dic]
        if not present:
            continue
        present.sort()
        earliest_off, earliest_q = present[0]

        # Look for play-records in the same script and find their min offset.
        fi = files_by_stem[stem]
        play_offsets: list[int] = []
        for rec in fi.get("records") or []:
            kind_class = OPCODE_TABLE.get((rec.get("code"), rec.get("kind")))
            if kind_class in PLAY_KINDS:
                play_offsets.append(rec["start"])
        if not play_offsets:
            play_offsets = [h["offset"] for h in fi.get("stringHits") or []
                            if payload_to_entry_key(h["text"], mission_id)]

        # Keep the referenced quest as the script-level anchor. Event-level
        # ordering below still sees whether play payloads are before/after the
        # marker; subtracting a whole quest here over-promotes scripts like
        # e0m0/8700020028 that carry a late q#10 marker.
        script_to_quest.setdefault(stem, earliest_q)

    timeline_hints = load_timeline_event_hints(mission_id, quest_idx)
    spatial_candidates_by_key = load_spatial_candidates(mission_id)
    scene_placement_by_key = load_scene_placement_evidence(mission_id)

    # Some late gameplay clusters have coherent source-script spatial evidence,
    # while filename/content suffixes place the whole script much too early
    # (for example cutscene_e0m0_3/4/5 in the q#11 final-area cluster). Use the
    # script's raw payload order at the shared spatial quest cluster only when
    # direct same-script candidates agree and the suffix would otherwise be
    # several quest phases earlier.
    script_spatial_raw_order_phase: dict[str, tuple[float, str]] = {}
    for stem, payload_keys in script_payloads.items():
        direct_candidates: list[dict] = []
        payloads_with_direct_candidate: set[str] = set()
        for payload_key in payload_keys:
            for candidate in spatial_candidates_by_key.get(payload_key) or []:
                if str(candidate.get("scriptId") or "") == stem and isinstance(candidate.get("questOrder"), (int, float)):
                    direct_candidates.append(candidate)
                    payloads_with_direct_candidate.add(payload_key)
        if not direct_candidates:
            continue
        if len(payloads_with_direct_candidate) < min(2, len(payload_keys)):
            continue
        quest_orders = {float(candidate["questOrder"]) for candidate in direct_candidates}
        if len(quest_orders) != 1:
            continue
        content_numbers = [
            parse_content_number(payload_key)
            for payload_key in payload_keys
        ]
        content_numbers = [value for value in content_numbers if value != float("inf")]
        if not content_numbers:
            continue
        spatial_phase = next(iter(quest_orders))
        if spatial_phase - min(content_numbers) < 3.0:
            continue
        quest_ids = sorted({str(candidate.get("questId") or "") for candidate in direct_candidates if candidate.get("questId")})
        evidence = "script-spatial-raw-order"
        if quest_ids:
            evidence += f":{quest_ids[0]}"
        script_spatial_raw_order_phase[stem] = (spatial_phase, evidence)

    def crossfile_spatial_phase_for_event(event: dict) -> tuple[float, str] | None:
        """Use predecessor-script spatial support to correct weak late suffixes.

        Cross-file LevelScript order is not generally chronological: e0m0 has
        known counterexamples where adjacent script ids span unrelated quest
        beats. This helper only applies when a scene has an incoming recovered
        cross-file edge, the spatial candidate belongs to the predecessor
        script named by that edge, and a numeric levelseq/content suffix would
        otherwise place the event several phases later.
        """
        key = str(event.get("key") or "")
        stem = str(event.get("fileStem") or "")
        if not key or not stem:
            return None
        placement = scene_placement_by_key.get(key) or {}
        predecessor_scripts: set[str] = set()
        for edge in placement.get("sceneIncomingEdges") or []:
            if not isinstance(edge, dict) or edge.get("kind") != "levelscriptCrossFileOrder":
                continue
            for script_id in edge.get("sourceScripts") or []:
                script_text = str(script_id or "")
                if script_text and script_text != stem:
                    predecessor_scripts.add(script_text)
        if not predecessor_scripts:
            return None

        candidates = [
            candidate
            for candidate in spatial_candidates_by_key.get(key) or []
            if (
                str(candidate.get("scriptId") or "") in predecessor_scripts
                and isinstance(candidate.get("questOrder"), (int, float))
            )
        ]
        if not candidates:
            return None
        quest_orders = {float(candidate["questOrder"]) for candidate in candidates}
        if len(quest_orders) != 1:
            return None
        spatial_phase = next(iter(quest_orders))

        # Keep this limited to numeric levelseq over-anchoring. Generic
        # content suffix rows need a separate audit before cross-file spatial
        # proximity is allowed to move them.
        if not isinstance(event.get("levelseq"), (int, float)):
            return None
        authored_phase = float(event["levelseq"])
        if authored_phase - spatial_phase < 3.0:
            return None

        quest_ids = sorted({
            str(candidate.get("questId") or "")
            for candidate in candidates
            if candidate.get("questId")
        })
        evidence = "crossfile-spatial-order"
        if quest_ids:
            evidence += f":{quest_ids[0]}"
        return (spatial_phase, evidence)

    property_conditions_by_script: dict[str, list[dict]] = defaultdict(list)
    for condition in property_conditions:
        script_id = str(condition.get("scriptId") or "")
        if script_id:
            property_conditions_by_script[script_id].append(condition)
    terminal_branch_evidence_by_event = build_terminal_branch_event_evidence(
        files_by_stem,
        mission_id,
        property_conditions_by_script,
    )
    header_event_evidence_by_event = build_header_event_evidence(
        files_by_stem,
        mission_id,
    )

    property_offsets: dict[tuple[str, str], list[int]] = defaultdict(list)
    for stem, file_info in files_by_stem.items():
        for hit in [
            *list(file_info.get("stringHits") or []),
            *list(file_info.get("plainStringHits") or []),
        ]:
            text = str(hit.get("text") or "")
            if text:
                property_offsets[(stem, text)].append(int(hit.get("offset") or 0))
    for bucket in property_offsets.values():
        bucket.sort()

    levelseq_alias_phase: dict[str, float] = {}
    for file_info in files_by_stem.values():
        numeric = levelseq_numbers_for_script(file_info, mission_id)
        if not numeric:
            continue
        for hit in file_info.get("stringHits") or []:
            text = str(hit.get("text") or "")
            if not text.startswith(f"levelseq_{mission_id}_"):
                continue
            if parse_levelseq_number(text, mission_id) is not None:
                continue
            seq, _seq_text = nearest_levelseq_number(numeric, int(hit.get("offset") or 0))
            if seq is not None:
                levelseq_alias_phase[text] = min(float(seq), levelseq_alias_phase.get(text, float("inf")))

    script_levelseq_alias_phase: dict[str, float] = {}
    for stem, file_info in files_by_stem.items():
        if levelseq_numbers_for_script(file_info, mission_id):
            continue
        phases = [
            levelseq_alias_phase[str(hit.get("text") or "")]
            for hit in file_info.get("stringHits") or []
            if str(hit.get("text") or "") in levelseq_alias_phase
        ]
        if phases:
            script_levelseq_alias_phase[stem] = min(phases)

    script_timeline_hints: dict[str, dict] = {}
    for (_scene_key, stem), hint in timeline_hints.items():
        current = script_timeline_hints.get(stem)
        candidate_key = (
            int(hint.get("priority", 99)),
            float(hint.get("distanceXZ", 10**9)),
            float(hint.get("questOrder", 10**9)),
        )
        current_key = (
            int(current.get("priority", 99)),
            float(current.get("distanceXZ", 10**9)),
            float(current.get("questOrder", 10**9)),
        ) if current else None
        if current is None or candidate_key < current_key:
            script_timeline_hints[stem] = hint

    def leveltimeline_marker_phase_for_event(event: dict) -> tuple[float, int, str] | None:
        key = str(event.get("key") or "")
        stem = str(event.get("fileStem") or "")
        markers = leveltimeline_markers_by_event.get((key, stem)) or []
        if not markers:
            return None
        marker_text = str(markers[0].get("marker") or "")
        evidence = "leveltimeline-marker"
        if marker_text:
            evidence += f":{marker_text}"

        if isinstance(event.get("levelseq"), (int, float)):
            return (float(event["levelseq"]), 2, evidence)
        if stem in mission_start_scripts:
            return (-1.0, 2, evidence)
        if stem in script_to_quest:
            return (float(quest_idx[script_to_quest[stem]]), 2, evidence)

        hint = timeline_hints.get((key, stem))
        if hint and isinstance(hint.get("questOrder"), (int, float)):
            return (float(hint["questOrder"]), 3, evidence)
        script_hint = script_timeline_hints.get(stem)
        if script_hint and isinstance(script_hint.get("questOrder"), (int, float)):
            return (float(script_hint["questOrder"]), 4, evidence)
        return None

    # Phase assignment per script:
    #   mission-start scripts -> -1   (sort before everything else)
    #   quest-bound scripts   -> quest_idx[bound_q]   (real anchor)
    #   unbound with numbered radio/cutscene -> min content number
    #   unbound, dialog-only / unnamed       -> interpolate between
    #     bound anchors by script id (the only signal left).
    #
    # Script id is a poor proxy for story position when content names
    # are numeric (8700040001 plays radio_<m>_1d5 yet sits high in the
    # id range), but it remains useful for dialog-only scripts whose
    # content has no narrative number to anchor on.
    anchors: list[tuple[int, float]] = []
    for stem, qid in script_to_quest.items():
        try:
            anchors.append((int(stem), float(quest_idx[qid])))
        except ValueError:
            continue
    anchors.sort()
    int_stems = [int(s) for s in payload_stems if s.isdigit()]

    def interpolate_script_id(sid_int: int) -> float:
        if not anchors:
            if int_stems and max(int_stems) > min(int_stems):
                frac = (sid_int - min(int_stems)) / (max(int_stems) - min(int_stems))
                return frac * max(0, len(quest_order) - 1)
            return 0.0
        if sid_int <= anchors[0][0]:
            return anchors[0][1]
        if sid_int >= anchors[-1][0]:
            return anchors[-1][1]
        for i in range(len(anchors) - 1):
            lo_id, lo_phase = anchors[i]
            hi_id, hi_phase = anchors[i + 1]
            if lo_id <= sid_int <= hi_id:
                if hi_id == lo_id:
                    return lo_phase
                t = (sid_int - lo_id) / (hi_id - lo_id)
                return lo_phase + t * (hi_phase - lo_phase)
        return anchors[-1][1]

    def event_phase(event: dict) -> tuple[float, int, str]:
        if isinstance(event.get("overridePhase"), (int, float)) and isinstance(event.get("overrideRank"), int):
            return (
                float(event["overridePhase"]),
                int(event["overrideRank"]),
                str(event.get("overrideEvidence") or "override"),
            )
        stem = str(event.get("fileStem") or "")
        offset = int(event.get("offset") or 0)
        key = str(event.get("key") or "")

        terminal_branch_rows = terminal_branch_evidence_by_event.get((key, stem)) or []
        terminal_branch_quest_candidates: list[tuple[float, int, str]] = []
        for row in terminal_branch_rows:
            for quest_id in row.get("questIds") or []:
                quest_text = str(quest_id or "")
                if quest_text not in quest_idx:
                    continue
                property_key = (row.get("propertyKeys") or [""])[0]
                terminal_branch_quest_candidates.append((
                    float(quest_idx[quest_text]),
                    0,
                    f"terminal-branch:{quest_text}:{property_key}",
                ))
        if terminal_branch_quest_candidates:
            return min(terminal_branch_quest_candidates)

        best_property: tuple[float, int, str] | None = None
        for condition in property_conditions_by_script.get(stem) or []:
            quest_id = str(condition.get("questId") or "")
            if quest_id not in quest_idx:
                continue
            phase = float(quest_idx[quest_id])
            key = str(condition.get("key") or "")
            offsets = property_offsets.get((stem, key)) or []
            if offsets and offset < offsets[0]:
                phase = max(-0.5, phase - 0.25)
            candidate = (phase, 0, f"property:{quest_id}:{key}")
            if best_property is None or candidate < best_property:
                best_property = candidate
        if best_property is not None:
            return best_property

        file_info = files_by_stem.get(stem) or {}
        quest_hits = [
            (off, qid)
            for off, qid in quest_hits_per_script.get(stem, [])
            if qid in quest_idx and record_for_offset(file_info, int(off)) is not None
        ]
        if quest_hits:
            quest_hits.sort(key=lambda item: (abs(item[0] - offset), item[0]))
            _, quest_id = quest_hits[0]
            return (float(quest_idx[quest_id]), 1, f"quest-record-string:{quest_id}")

        leveltimeline_phase = leveltimeline_marker_phase_for_event(event)
        if leveltimeline_phase is not None:
            return leveltimeline_phase

        crossfile_spatial_phase = crossfile_spatial_phase_for_event(event)
        if crossfile_spatial_phase is not None:
            phase, evidence = crossfile_spatial_phase
            return (float(phase), 2, evidence)

        if isinstance(event.get("levelseq"), (int, float)):
            return (float(event["levelseq"]), 2, f"levelseq:{event.get('levelseqText') or ''}")

        if stem in script_levelseq_alias_phase:
            return (float(script_levelseq_alias_phase[stem]), 3, "levelseq-alias")

        hint = timeline_hints.get((str(event.get("key") or ""), stem))
        if hint and isinstance(hint.get("questOrder"), (int, float)):
            priority = int(hint.get("priority", 2))
            return (
                float(hint["questOrder"]),
                4 + priority,
                f"{hint.get('source') or 'timeline'}:{hint.get('questId') or ''}",
            )

        script_hint = script_timeline_hints.get(stem)
        if script_hint and isinstance(script_hint.get("questOrder"), (int, float)):
            priority = int(script_hint.get("priority", 2))
            return (
                float(script_hint["questOrder"]),
                7 + priority,
                f"script-{script_hint.get('source') or 'timeline'}:{script_hint.get('questId') or ''}",
            )

        if stem in mission_start_scripts:
            return (-1.0, 10, "mission-start")

        if stem in script_to_quest:
            return (float(quest_idx[script_to_quest[stem]]), 11, f"script-anchor:{script_to_quest[stem]}")

        content_n = parse_content_number(str(event.get("key") or ""))
        if content_n != float("inf") and stem in script_spatial_raw_order_phase:
            phase, evidence = script_spatial_raw_order_phase[stem]
            return (float(phase), 11, evidence)
        if content_n != float("inf"):
            return (float(content_n), 12, "content-suffix-fallback")

        try:
            sid_int = int(stem)
        except ValueError:
            return (float(len(quest_order)) + 1000.0, 19, "fallback")
        return (interpolate_script_id(sid_int), 18, "script-id-interpolation")

    # Within the same phase bucket, sort by the minimum authored content
    # number across each script's payloads, then by script id. This stops
    # `radio_<m>_1d5` from being out-sorted by `radio_<m>_2*` just because
    # its host script has a higher script id.
    ordered: list[str] = []
    entry_details: list[dict] = []
    seen: set[str] = set()
    all_events = [
        event
        for events in script_events.values()
        for event in events
    ]
    conv_keys = list_conv_keys_for_mission(mission_id)
    ordinal_groups: dict[str, list[tuple[int, str, dict]]] = defaultdict(list)
    for event in all_events:
        hint = ordinal_name_hint(str(event.get("key") or event.get("payload") or ""))
        if hint:
            group, ordinal, token = hint
            ordinal_groups[group].append((ordinal, token, event))
    for rows in ordinal_groups.values():
        anchors: list[tuple[int, float, int, str]] = []
        for ordinal, token, event in rows:
            if ordinal != 1:
                continue
            phase, rank, _reason = event_phase(event)
            if rank <= 6:
                anchors.append((rank, phase, ordinal, token))
        if not anchors:
            continue
        base_rank, base_phase, base_ordinal, base_token = min(anchors)
        for ordinal, token, event in rows:
            if ordinal <= base_ordinal:
                continue
            _phase, rank, _reason = event_phase(event)
            if rank <= 6:
                continue
            event["overridePhase"] = base_phase + ((ordinal - base_ordinal) * 0.25)
            event["overrideRank"] = 7
            event["overrideEvidence"] = f"ordinal-name:{base_token}->{token}"

    def event_sort_key(event: dict):
        phase, rank, _reason = event_phase(event)
        stem = str(event.get("fileStem") or "")
        try:
            sid_int = int(stem)
        except ValueError:
            sid_int = 0
        content_n = parse_content_number(str(event.get("key") or ""))
        return (phase, rank, sid_int, int(event.get("offset") or 0), content_n, str(event.get("key") or ""))

    def event_choice_key(event: dict):
        phase, rank, _reason = event_phase(event)
        stem = str(event.get("fileStem") or "")
        try:
            sid_int = int(stem)
        except ValueError:
            sid_int = 0
        fallback_bucket = 1 if rank >= 12 else 0
        return (fallback_bucket, phase, rank, sid_int, int(event.get("offset") or 0), str(event.get("key") or ""))

    def apply_scene_chain_overrides() -> None:
        """Keep recovered same-script scene chains together when all inputs are weak."""
        selected_by_key: dict[str, dict] = {}
        for event in all_events:
            key = str(event.get("key") or "")
            if not key:
                continue
            current = selected_by_key.get(key)
            if current is None or event_choice_key(event) < event_choice_key(current):
                selected_by_key[key] = event

        phases: dict[str, tuple[float, int, str]] = {}
        weak_keys: set[str] = set()
        for key, event in selected_by_key.items():
            phase, rank, reason = event_phase(event)
            phases[key] = (phase, rank, reason)
            if rank >= 12 and reason == "content-suffix-fallback":
                weak_keys.add(key)
        if len(weak_keys) < 2:
            return

        edges: dict[str, set[str]] = defaultdict(set)
        chunks_by_key: dict[str, str] = {}
        for source_key in weak_keys:
            source_event = selected_by_key[source_key]
            source_stem = str(source_event.get("fileStem") or "")
            placement = scene_placement_by_key.get(source_key) or {}
            if "sourceBackedSceneSequence" not in (placement.get("sceneEvidenceKinds") or []):
                continue
            source_chunk = str(placement.get("sceneChunkId") or "")
            if source_chunk:
                chunks_by_key[source_key] = source_chunk
            for edge in placement.get("sceneOutgoingEdges") or []:
                if not isinstance(edge, dict) or edge.get("kind") != "levelscriptSceneChain":
                    continue
                target_key = str(edge.get("neighbor") or "")
                if target_key not in weak_keys:
                    continue
                target_event = selected_by_key[target_key]
                if str(target_event.get("fileStem") or "") != source_stem:
                    continue
                target_placement = scene_placement_by_key.get(target_key) or {}
                target_chunk = str(target_placement.get("sceneChunkId") or "")
                if source_chunk and target_chunk and source_chunk != target_chunk:
                    continue
                if target_chunk:
                    chunks_by_key[target_key] = target_chunk
                edges[source_key].add(target_key)

        if not any(edges.values()):
            return

        neighbors: dict[str, set[str]] = defaultdict(set)
        for source_key, targets in edges.items():
            for target_key in targets:
                neighbors[source_key].add(target_key)
                neighbors[target_key].add(source_key)

        visited: set[str] = set()
        for root in sorted(neighbors):
            if root in visited:
                continue
            stack = [root]
            component: set[str] = set()
            while stack:
                key = stack.pop()
                if key in component:
                    continue
                component.add(key)
                stack.extend(sorted(neighbors.get(key) or ()))
            visited.update(component)
            if len(component) < 2:
                continue

            incoming = {key: 0 for key in component}
            component_edges = {
                key: {target for target in edges.get(key, set()) if target in component}
                for key in component
            }
            for targets in component_edges.values():
                for target in targets:
                    incoming[target] += 1

            ready = sorted(
                [key for key, count in incoming.items() if count == 0],
                key=lambda key: event_choice_key(selected_by_key[key]),
            )
            ordered_keys: list[str] = []
            while ready:
                key = ready.pop(0)
                ordered_keys.append(key)
                for target in sorted(
                    component_edges.get(key) or (),
                    key=lambda item: event_choice_key(selected_by_key[item]),
                ):
                    incoming[target] -= 1
                    if incoming[target] == 0:
                        ready.append(target)
                        ready.sort(key=lambda item: event_choice_key(selected_by_key[item]))
            if len(ordered_keys) != len(component):
                continue

            base_phase = min(phases[key][0] for key in component)
            chunk_ids = sorted({
                chunks_by_key.get(key, "")
                for key in component
                if chunks_by_key.get(key, "")
            })
            evidence = "levelscript-scene-chain"
            if chunk_ids:
                evidence += f":{chunk_ids[0]}"
            for index, key in enumerate(ordered_keys):
                event = selected_by_key[key]
                event["overridePhase"] = round(base_phase + (index * 0.01), 3)
                event["overrideRank"] = 8
                event["overrideEvidence"] = evidence

    apply_scene_chain_overrides()

    selected_events: dict[str, dict] = {}
    for event in all_events:
        key = str(event.get("key") or "")
        if not key:
            continue
        current = selected_events.get(key)
        if current is None or event_choice_key(event) < event_choice_key(current):
            selected_events[key] = event

    sorted_events = sorted(selected_events.values(), key=event_sort_key)
    for event in sorted_events:
        phase, rank, _reason = event_phase(event)
        event["_constraintPhase"] = round(float(phase), 3)
        event["_constraintRank"] = int(rank)
    sorted_events = apply_scene_file_order_constraints(
        sorted_events,
        scene_placement_by_key,
        terminal_branch_evidence_by_event,
    )

    for event in sorted_events:
        key = str(event.get("key") or "")
        if not key or key in seen:
            continue
        phase, rank, reason = event_phase(event)
        ordered.append(key)
        seen.add(key)
        entry_details.append({
            "key": key,
            "phase": round(float(phase), 3),
            "rank": rank,
            "evidence": reason,
            "sourceFile": event.get("file") or "",
            "sourceScript": event.get("fileStem") or "",
            "offset": event.get("offset"),
            "recordClass": event.get("recordClass") or "",
            "levelseq": event.get("levelseqText") or "",
            **(
                {
                    "levelTimelineMarkerEdges": leveltimeline_markers_by_event.get(
                        (key, str(event.get("fileStem") or ""))
                    )[:6],
                    "levelTimelineMarkerNote": (
                        "Resolved lt:p LevelTimeline marker from LevelData to "
                        "LevelScript UID records. lt:mp partners are retained "
                        "in audits as metadata until their runtime semantics "
                        "are decoded."
                    ),
                }
                if leveltimeline_markers_by_event.get((key, str(event.get("fileStem") or "")))
                else {}
            ),
            **(leveldata_refs_by_stem.get(str(event.get("fileStem") or "")) or {}),
            **(binary_refs_by_stem.get(str(event.get("fileStem") or "")) or {}),
            **(cross_refs_by_stem.get(str(event.get("fileStem") or "")) or {}),
            **(scene_placement_by_key.get(key) or {}),
            **(
                {
                    "terminalBranchEvidence": terminal_branch_evidence_by_event.get(
                        (key, str(event.get("fileStem") or ""))
                    )[:6],
                    "terminalBranchNote": (
                        "0x0bed/0x00 compact terminal branch refs were walked "
                        "through local LevelScript action ids to this concrete "
                        "story/play record; this is branch evidence, not generic setter proof."
                    ),
                }
                if terminal_branch_evidence_by_event.get((key, str(event.get("fileStem") or "")))
                else {}
            ),
            **(
                {
                    "headerEventEvidence": header_event_evidence_by_event.get(
                        (key, str(event.get("fileStem") or ""))
                    )[:6],
                    "headerEventNote": (
                        "Decoded headerList ActionHeader.nextId reaches this "
                        "story/play record through an actionList chain. This "
                        "identifies the triggering event path, but runtime "
                        "conditions still control chronology."
                    ),
                }
                if header_event_evidence_by_event.get((key, str(event.get("fileStem") or "")))
                else {}
            ),
            **spatial_evidence_for_entry(
                spatial_candidates_by_key,
                key,
                str(event.get("fileStem") or ""),
            ),
        })

    # Append WebUI entries the binary scan never named. Explicit timeline-bound
    # standalone videos stay distinct, but inherit adjacency from their bound
    # story key instead of drifting to the end as generic fallbacks.
    for stem in conv_keys:
        if stem not in seen:
            bound_scene = bound_video_scene_for_conv_key(stem, mission_id)
            if bound_scene and bound_scene in seen and bound_scene in ordered:
                insert_at = ordered.index(bound_scene) + 1
                while insert_at < len(ordered) and str(ordered[insert_at]).startswith("video_"):
                    insert_at += 1
                bound_entry = next(
                    (entry for entry in entry_details if entry.get("key") == bound_scene),
                    {},
                )
                bound_rank = bound_entry.get("rank")
                rank = int(bound_rank) + 1 if isinstance(bound_rank, int) else 98
                ordered.insert(insert_at, stem)
                seen.add(stem)
                entry_details.insert(insert_at, {
                    "key": stem,
                    "phase": bound_entry.get("phase"),
                    "rank": rank,
                    "evidence": f"timeline-video-binding:{bound_scene}",
                    "videoBindingScene": bound_scene,
                    "videoBindingNote": (
                        "Standalone video entry with explicit AnimeStudio "
                        "timelinePlayable binding to this story key; kept as "
                        "its own WebUI row but ordered next to the bound scene."
                    ),
                })
                continue
            ordered.append(stem)
            seen.add(stem)
            entry_details.append({
                "key": stem,
                "phase": None,
                "rank": 99,
                "evidence": "webui-conv-fallback",
            })

    # Unbound `video_cs_video_*` entries are video-table rows, not aliases for
    # `cutscene_*` story keys. Filename similarity is not an order signal.

    ordered, entry_details = apply_observed_order_hint(
        mission_id,
        ordered,
        entry_details,
    )

    if not ordered:
        return None
    return {"level": level_id, "levels": level_ids, "order": ordered, "entries": entry_details}


def all_mission_ids() -> list[str]:
    if not MISSION_ASSET_ROOT.is_dir():
        return []
    out: set[str] = set()
    for path in MISSION_ASSET_ROOT.iterdir():
        if not path.is_file() or path.suffix != ".json":
            continue
        stem = path.stem[:-5] if path.stem.endswith("_meta") else path.stem
        if MISSION_ID_RE.match(stem):
            out.add(stem)
    return sorted(out)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--missions", nargs="*")
    args = parser.parse_args()

    mission_ids = args.missions or all_mission_ids()
    missions_payload: dict[str, dict] = {}
    for mid in mission_ids:
        result = build_mission_order(mid)
        if result and result.get("order"):
            missions_payload[mid] = {
                "level": result["level"],
                "levels": result.get("levels") or [result["level"]],
                "order": result["order"],
                "entries": result.get("entries") or [],
            }

    payload = {
        "method": (
            "Per-mission story order derived from original/decodeable game "
            "data. Event phases use MissionRuntime quest/property anchors "
            "(including plain length-prefixed LevelScript property keys), "
            "LevelScript quest strings that attach to decoded records, numeric levelseq "
            "payloads, resolved LevelData LevelTimeline lt:p markers that "
            "point at concrete LevelScript UID records, secondary LevelData "
            "level refs from mission bundles, mission-start scripts, weak "
            "authored ordinal-name hints, and "
            "same-script mission timeline condition hints from decoded mission "
            "bundles. Entries also carry decoded LevelData file/offset and "
            "neighbor-script diagnostics for original-data grouping; those "
            "diagnostics are visible in the WebUI but are not promoted as "
            "playback edges. Entries with source scripts also carry compact "
            "binary cross-script reference diagnostics; these are shown as "
            "control evidence and are not sorting inputs. Entries also expose "
            "compact map-position diagnostics from decoded LevelScript vectors "
            "matched against quest pins; those support spatial/quest vicinity "
            "and can override weak suffix fallback only when direct same-script "
            "candidates agree for a raw-ordered source-script cluster. Compact "
            "mission timeline scene-edge diagnostics are exposed beside entries "
            "so same-script scene-chain edges can keep weak suffix fallback "
            "groups together, while same-script file-order edges can be checked "
            "without opening the full mission bundle. Direct same-script "
            "file-order and nonzero terminal-branch path edges are applied as "
            "stable local ordering constraints. A "
            "constrained cross-file rule may also "
            "correct numeric levelseq over-anchoring when an incoming "
            "cross-file edge and predecessor-script spatial candidate agree. Story "
            "cutscenes and narrative video entries remain distinct; explicit "
            "timelinePlayable video bindings inherit adjacency from their bound "
            "story keys, but matching video names are not coupled to cutscene "
            "story keys. Mission-specific gameplay-observed calibration hints "
            "may reorder listed entries as non-firm `observed-gameplay-calibration` "
            "rows while preserving the previous recovered evidence fields. When a story "
            "key appears in multiple scripts, the earliest non-fallback "
            "occurrence is chosen before final sorting. Filename/content "
            "suffixes are only weak fallbacks."
        ),
        "missions": missions_payload,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    total = sum(len(m["order"]) for m in missions_payload.values())
    print(f"Wrote {args.output} - {len(missions_payload)} missions, {total} ordered entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
