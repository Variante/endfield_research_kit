"""Build the production index of authored LevelScript manual-control targets."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
import struct
from typing import Any

if __package__ == "story_builder":
    from common import ROOT, rel_path
elif __package__ == "scripts.story_builder":
    from ..common import ROOT, rel_path
else:  # pragma: no cover - direct file execution is intentionally unsupported
    raise ImportError("import this module as scripts.story_builder.levelscript_manual_control")

from .context import LEVELSCRIPT_DIR
from .level_bindings import _load_levelscript_binding_data
from .levelscript_binary import (
    decode_levelscript_action_map_header,
    decode_levelscript_record_payload,
)


MANUAL_CONTROL_MAPPING_ID = "levelscript-actionbase-manual-control-opcodes-v1"
MANUAL_OPCODES = {
    (0x0308, 0x0A): ("manual-start", "ManualStartLevelScript"),
    (0x0302, 0x0A): ("manual-end", "ManualEndLevelScript"),
}
EXPECTED_EVENT_OPCODES = {
    "manual-start": (0x12BE, 0x00),
    "manual-end": (0x12C0, 0x00),
}
EVIDENCE_BOUNDARY = (
    "Serialized manual-control operands and exact ActionHeader.nextId links can "
    "identify literal targets or a binary-validated current-context self target. "
    "They do not establish mission ownership, server-side activation, event "
    "firing, playback ownership, or Story order."
)


def _text(value: Any) -> str:
    return str(value if value is not None else "").strip()


def _opcode(record: dict[str, Any]) -> str:
    code = record.get("code")
    kind = record.get("kind")
    if isinstance(code, int) and isinstance(kind, int):
        return f"0x{code:04x}/0x{kind:02x}"
    return ""


def _record_texts(
    record: dict[str, Any],
    decoded: dict[str, Any] | None = None,
) -> list[str]:
    texts: list[str] = []
    for field in (decoded or {}).get("taggedFields") or []:
        if not isinstance(field, dict) or field.get("type") != "string":
            continue
        value = _text(field.get("value"))
        if value and value not in texts:
            texts.append(value)
    for field_name in ("strings", "plainStrings"):
        for item in record.get(field_name) or []:
            value = item.get("text") if isinstance(item, dict) else item
            if isinstance(value, str) and value and value not in texts:
                texts.append(value)
    return texts


def _payload_window(
    data: bytes,
    record: dict[str, Any],
    next_start: int | None,
) -> bytes:
    start = int(record.get("payloadStart", record.get("start", 0)) or 0)
    if start < 0 or start >= len(data):
        return b""
    if next_start is None or next_start <= start or next_start > len(data):
        next_start = min(len(data), start + 160)
    return data[start:next_start]


def _script_id_bytes(
    level_ids: set[str],
    levelscript_root: Path,
) -> dict[str, list[tuple[str, bytes, bytes]]]:
    result: dict[str, list[tuple[str, bytes, bytes]]] = {}
    for level_id in level_ids:
        candidates: list[tuple[str, bytes, bytes]] = []
        for path in (levelscript_root / level_id).glob("*.json"):
            if not path.stem.isdigit():
                continue
            value = int(path.stem)
            candidates.append(
                (
                    path.stem,
                    struct.pack("<I", value & 0xFFFFFFFF),
                    struct.pack("<Q", value),
                )
            )
        result[level_id] = candidates
    return result


def _literal_targets(
    *,
    source_level_id: str,
    texts: list[str],
    payload: bytes,
    level_ids: set[str],
    script_ids: dict[str, list[tuple[str, bytes, bytes]]],
) -> list[tuple[str, str]]:
    text_levels = [text for text in texts if text in level_ids]
    search_levels = text_levels or [source_level_id]
    targets: list[tuple[str, str]] = []
    for level_id in search_levels:
        for script_id, raw_u32, raw_u64 in script_ids.get(level_id) or []:
            target = (level_id, script_id)
            if (
                script_id in texts
                or raw_u32 in payload[:160]
                or raw_u64 in payload[:160]
            ) and target not in targets:
                targets.append(target)
                if len(targets) >= 12:
                    return targets
    return targets


def _adjacent_record(
    *,
    data: bytes,
    records: list[dict[str, Any]],
    starts: list[int],
    by_local: dict[int, int],
    local_id: int | None,
) -> dict[str, Any]:
    if local_id is None or local_id not in by_local:
        return {}
    index = by_local[local_id]
    record = records[index]
    next_start = starts[index + 1] if index + 1 < len(starts) else None
    decoded = decode_levelscript_record_payload(data, record, next_start=next_start)
    return {
        "localId": record.get("localId"),
        "opcode": _opcode(record),
        "hint": decoded.get("label") or "",
        "nextId": record.get("nextId"),
        "texts": _record_texts(record, decoded)[:8],
    }


def _self_contract_operands(
    contract: dict[str, Any] | None,
) -> dict[str, Any] | None:
    contract = contract or {}
    operands = contract.get("serializedOperandContract") or {}
    if (
        (contract.get("validation") or {}).get("status") == "validated"
        and _text(contract.get("classification"))
        == "current_context_manual_start_self_target"
        and (contract.get("discoveryPattern") or {}).get(
            "serializedObjectInputs"
        )
        == []
        and operands.get("levelIdParamSource") is not None
        and operands.get("scriptIdParamSource") is not None
    ):
        return {
            "levelId": operands["levelIdParamSource"],
            "scriptId": operands["scriptIdParamSource"],
        }
    return None


@dataclass(frozen=True)
class ManualControlIndex:
    """Typed production result; JSON rows remain a presentation concern."""

    targets: dict[tuple[str, str], list[dict[str, Any]]]
    summary: dict[str, Any]
    validation: dict[str, Any]
    source_root: str
    mapping_id: str = MANUAL_CONTROL_MAPPING_ID
    evidence_boundary: str = EVIDENCE_BOUNDARY


def build_manual_control_index(
    *,
    levelscript_root: Path = LEVELSCRIPT_DIR,
    self_control_contract: dict[str, Any] | None = None,
) -> ManualControlIndex:
    """Scan LevelScriptData once and return only production control edges."""
    if not levelscript_root.is_dir():
        return ManualControlIndex(
            targets={},
            summary={"rows": 0},
            validation={
                "status": "validation_failed",
                "gate": "levelscript_root_exists",
                "source": rel_path(levelscript_root),
            },
            source_root=rel_path(levelscript_root),
        )

    level_ids = {path.name for path in levelscript_root.iterdir() if path.is_dir()}
    script_ids = _script_id_bytes(level_ids, levelscript_root)
    expected_self_operands = _self_contract_operands(self_control_contract)
    targets: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    counts: Counter[str] = Counter()
    payload_shapes: Counter[str] = Counter()
    unreadable_files: list[str] = []

    for level_id in sorted(level_ids):
        binding = _load_levelscript_binding_data(level_id, levelscript_root)
        for file_info in binding.get("files") or []:
            file_path = Path(_text(file_info.get("file")))
            if not file_path.is_absolute():
                file_path = ROOT / file_path
            try:
                data = file_path.read_bytes()
            except OSError:
                unreadable_files.append(rel_path(file_path))
                continue
            records = sorted(
                file_info.get("records") or [],
                key=lambda row: int(row.get("start") or 0),
            )
            if not records:
                continue
            starts = [int(record.get("start") or 0) for record in records]
            by_local = {
                int(record["localId"]): index
                for index, record in enumerate(records)
                if isinstance(record.get("localId"), int)
            }
            action_map = decode_levelscript_action_map_header(data)
            action_count = (
                int(action_map["recordCount"])
                if action_map.get("status") == "present"
                and isinstance(action_map.get("recordCount"), int)
                else None
            )
            source_script_id = file_path.stem

            for index, record in enumerate(records):
                role_action = MANUAL_OPCODES.get(
                    (record.get("code"), record.get("kind"))
                )
                if not role_action:
                    continue
                role, action = role_action
                next_start = starts[index + 1] if index + 1 < len(starts) else None
                decoded = decode_levelscript_record_payload(
                    data,
                    record,
                    next_start=next_start,
                )
                manual_control = decoded.get("manualControl") or {}
                payload_shapes[_text(manual_control.get("payloadShape")) or "unknown"] += 1
                counts["rows"] += 1
                counts[role] += 1
                local_id = record.get("localId")
                expected_event = EXPECTED_EVENT_OPCODES[role]
                linked_candidates: list[dict[str, Any]] = []
                for candidate_index, candidate in enumerate(records):
                    if (candidate.get("code"), candidate.get("kind")) != expected_event:
                        continue
                    candidate_next = (
                        starts[candidate_index + 1]
                        if candidate_index + 1 < len(starts)
                        else None
                    )
                    candidate_decoded = decode_levelscript_record_payload(
                        data,
                        candidate,
                        next_start=candidate_next,
                    )
                    candidate_next_id = (
                        candidate_decoded.get("actionHeader") or {}
                    ).get("nextId")
                    if not isinstance(candidate_next_id, int):
                        candidate_next_id = candidate.get("nextId")
                    if candidate_next_id == local_id:
                        linked_candidates.append(candidate)
                activation_pair = len(linked_candidates) == 1
                linked_event = (
                    _adjacent_record(
                        data=data,
                        records=records,
                        starts=starts,
                        by_local=by_local,
                        local_id=linked_candidates[0].get("localId"),
                    )
                    if activation_pair
                    else {}
                )
                if activation_pair:
                    counts["activationPairs"] += 1

                parameter_sources = manual_control.get("parameterSources") or {}
                if (
                    expected_self_operands is not None
                    and action == "ManualStartLevelScript"
                    and activation_pair
                    and parameter_sources == expected_self_operands
                ):
                    targets[(level_id, source_script_id)].append(
                        {
                            "sourceLevelId": level_id,
                            "sourceScriptId": source_script_id,
                            "localId": local_id,
                            "action": action,
                            "selfTarget": True,
                            "targetResolution": "current_context_self",
                            "parameterSources": parameter_sources,
                            "headerLinkedEvent": linked_event,
                            "sourceFile": rel_path(file_path),
                        }
                    )
                    counts["validatedSelfTargets"] += 1

                literal_targets = _literal_targets(
                    source_level_id=level_id,
                    texts=_record_texts(record, decoded),
                    payload=_payload_window(data, record, next_start),
                    level_ids=level_ids,
                    script_ids=script_ids,
                )
                if literal_targets:
                    counts["literalTargetRows"] += 1
                for target_level_id, target_script_id in literal_targets:
                    targets[(target_level_id, target_script_id)].append(
                        {
                            "sourceLevelId": level_id,
                            "sourceScriptId": source_script_id,
                            "localId": local_id,
                            "action": action,
                            "selfTarget": (
                                level_id == target_level_id
                                and source_script_id == target_script_id
                            ),
                            "targetResolution": "literal_serialized_identity",
                            "sourceFile": rel_path(file_path),
                        }
                    )

    ordered_targets = {
        key: sorted(
            rows,
            key=lambda row: (
                row["sourceLevelId"],
                row["sourceScriptId"],
                int(row.get("localId") or -1),
                row["targetResolution"],
            ),
        )
        for key, rows in sorted(targets.items())
    }
    return ManualControlIndex(
        targets=ordered_targets,
        summary={
            "rows": counts["rows"],
            "manualStartRows": counts["manual-start"],
            "manualEndRows": counts["manual-end"],
            "activationPairs": counts["activationPairs"],
            "literalTargetRows": counts["literalTargetRows"],
            "validatedSelfTargets": counts["validatedSelfTargets"],
            "targetIdentityCount": len(ordered_targets),
            "payloadShapes": dict(sorted(payload_shapes.items())),
        },
        validation={
            "status": "validated" if not unreadable_files else "validation_failed",
            "gate": "all_indexed_levelscript_files_readable",
            "unreadableFiles": unreadable_files[:20],
        },
        source_root=rel_path(levelscript_root),
    )
