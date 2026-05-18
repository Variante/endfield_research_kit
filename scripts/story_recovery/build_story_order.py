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
from functools import lru_cache
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

from story_builder.level_bindings import (  # noqa: E402
    LEVELSCRIPT_OPCODE_TABLE,
    _build_uid_record_chains,
    _load_levelscript_binding_data,
    classify_levelscript_record,
)

DATA_ROOT = ROOT / "export_full" / "structured" / "StreamingAssets" / "Data" / "Json"
MISSION_ASSET_ROOT = DATA_ROOT / "MissionRuntimeAsset"
LEVELSCRIPT_ROOT = DATA_ROOT / "LevelScriptData"
PERSISTENT_TABLE_ROOT = ROOT / "export_full" / "structured" / "Persistent" / "Table"
TEXT_TABLE_PATH = PERSISTENT_TABLE_ROOT / "TextTable.json"
I18N_TEXT_TABLE_CN_PATH = PERSISTENT_TABLE_ROOT / "I18nTextTable_CN.json"
WEBUI_CONV_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "conv"
WEBUI_MISSION_ROOT = ROOT / "webui" / "data" / "lang" / "CN" / "mission"
OUTPUT_PATH = ROOT / "webui" / "data" / "assets" / "story_order.json"

MISSION_ID_RE = re.compile(r"^[a-z][a-z0-9]*m[0-9]+(?:d[0-9]+)?$")

# The opcode table itself lives in `story_builder.level_bindings` as
# `LEVELSCRIPT_OPCODE_TABLE` so scene_graph and other builders can reuse it.
OPCODE_TABLE = LEVELSCRIPT_OPCODE_TABLE


def payload_to_entry_key(text: str, mission_id: str) -> str | None:
    """Map a tagged ASCII payload to the WebUI conv-entry key, or None
    if it does not correspond to a user-facing story unit."""
    if not isinstance(text, str):
        return None
    # Audio mask `au_special_cs_<mission>_<N>_*` plays alongside
    # `cutscene_<mission>_<N>`.
    m = re.match(r"^au_special_cs_(" + re.escape(mission_id) + r")_(\d+)(?:_|$)", text)
    if m:
        return f"cutscene_{m.group(1)}_{m.group(2)}"
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


@lru_cache(maxsize=1)
def _load_text_tables() -> tuple[dict, dict]:
    try:
        text_table = json.loads(TEXT_TABLE_PATH.read_text(encoding="utf-8"))
        cn_table = json.loads(I18N_TEXT_TABLE_CN_PATH.read_text(encoding="utf-8"))
    except OSError:
        return {}, {}
    return text_table, cn_table


@lru_cache(maxsize=None)
def decoded_time_zero_title_cards(mission_id: str) -> dict[str, str]:
    """Return cutscene keys whose original localized first row is 00:00:00.

    This is story text evidence, not a video-file binding. It handles the
    e0m0 opening title card while keeping later LevelScript replays separate.
    """
    text_table, cn_table = _load_text_tables()
    if not text_table or not cn_table:
        return {}

    out: dict[str, str] = {}
    prefix = f"cutscene_{mission_id}_"
    for row_id, row in text_table.items():
        if not isinstance(row_id, str) or not row_id.startswith(prefix) or not row_id.endswith("_01"):
            continue
        if not isinstance(row, dict) or "id" not in row:
            continue
        text = str(cn_table.get(str(row["id"])) or "")
        normalized = text.replace("\uff1a", ":")
        if "00:00:00" not in normalized:
            continue
        out[row_id[:-3]] = f"decoded-title-card-time-zero:{row_id}"
    return out


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
    scene key.
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
        for candidate in row.get("spatialQuestCandidates") or []:
            if not isinstance(candidate, dict):
                continue
            quest_id = str(candidate.get("questId") or "")
            script_id = str(candidate.get("scriptId") or "")
            if quest_id not in quest_idx:
                continue
            put(scene_key, script_id, {
                "questId": quest_id,
                "questOrder": float(quest_idx[quest_id]),
                "source": "levelscriptSpatialProximity",
                "priority": 2,
                "distanceXZ": float(candidate.get("distanceXZ", 10**9)),
            })
    return hints


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
        for off in range(len(raw) - 8):
            v = struct.unpack_from("<Q", raw, off)[0]
            if v in script_ids and v != self_id and v >= 8000000000:
                found.add(v)
        if found:
            out[stem] = found
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

    property_conditions_by_script: dict[str, list[dict]] = defaultdict(list)
    for condition in property_conditions:
        script_id = str(condition.get("scriptId") or "")
        if script_id:
            property_conditions_by_script[script_id].append(condition)

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
    for cutscene_key, evidence in decoded_time_zero_title_cards(mission_id).items():
        if cutscene_key not in conv_keys:
            continue
        all_events.append({
            "key": cutscene_key,
            "payload": cutscene_key,
            "offset": 0,
            "fileStem": "",
            "file": "export_full/structured/Persistent/Table/TextTable.json",
            "recordClass": "decoded_title_card",
            "levelseq": None,
            "levelseqText": "",
            "overridePhase": -2.0,
            "overrideRank": 0,
            "overrideEvidence": evidence,
        })

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
        return (rank, phase, sid_int, int(event.get("offset") or 0), str(event.get("key") or ""))

    selected_events: dict[str, dict] = {}
    for event in all_events:
        key = str(event.get("key") or "")
        if not key:
            continue
        current = selected_events.get(key)
        if current is None or event_choice_key(event) < event_choice_key(current):
            selected_events[key] = event

    for event in sorted(selected_events.values(), key=event_sort_key):
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
        })

    # Append WebUI entries the binary scan never named, in natural-name order.
    for stem in conv_keys:
        if stem not in seen:
            ordered.append(stem)
            seen.add(stem)
            entry_details.append({
                "key": stem,
                "phase": None,
                "rank": 99,
                "evidence": "webui-conv-fallback",
            })

    # `video_cs_video_*` entries are video-table rows, not aliases for
    # `cutscene_*` story keys. Filename similarity is not an order signal.

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
        "version": 7,
        "method": (
            "Per-mission story order derived from original/decodeable game "
            "data. Event phases use MissionRuntime quest/property anchors "
            "(including plain length-prefixed LevelScript property keys), "
            "decoded time-zero title-card text rows, LevelScript quest "
            "strings that attach to decoded records, numeric levelseq "
            "payloads, secondary LevelData level refs from mission bundles, "
            "mission-start scripts, weak authored ordinal-name hints, and "
            "same-script mission timeline/spatial hints from decoded mission "
            "bundles. Story "
            "cutscenes and narrative video entries remain distinct; matching "
            "video names are not coupled to cutscene story keys. When a story "
            "key appears in multiple scripts, the strongest occurrence is "
            "chosen before final sorting. Filename/content suffixes are only "
            "weak fallbacks."
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
