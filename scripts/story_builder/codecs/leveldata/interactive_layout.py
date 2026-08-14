"""Decode LevelInteractiveData list framing and final record boundaries.

Story/narrative admissibility stays with the caller-provided semantic parsers. This
module only locates counted records and validates exact serialized boundaries.
"""

from __future__ import annotations

from collections.abc import Callable

from .memorypack import read_count, read_i32, read_string


def level_interactive_data_list_frames(
    data: bytes,
    *,
    final_record_end_offset: int | None = None,
) -> list[dict]:
    """Locate fully counted LevelInteractiveData lists in one LevelData blob."""
    candidates: list[tuple[int, str]] = []
    for offset, value in enumerate(data):
        if value != 25 or offset + 29 > len(data):
            continue
        decoded = read_string(
            data,
            offset + 1 + (3 * 8),
            max_length=256,
        )
        if decoded is not None and decoded[0].startswith("int_"):
            candidates.append((offset, decoded[0]))
    frames: list[dict] = []
    for index, (offset, _entity_id) in enumerate(candidates):
        if offset < 4:
            continue
        count = int.from_bytes(data[offset - 4 : offset], "little", signed=True)
        if count <= 0 or count > 50_000 or index + count > len(candidates):
            continue
        record_starts = candidates[index : index + count]
        # A next typed record is required as an exact end boundary. The final
        # list item remains intentionally unparsed rather than borrowing the
        # unknown following LevelData member as a boundary.
        bounded_records = [
            {
                "recordIndex": record_index,
                "recordOffset": record_starts[record_index][0],
                "recordEndOffset": record_starts[record_index + 1][0],
                "entityDetailId": record_starts[record_index][1],
                "recordBoundarySource": "next_record",
            }
            for record_index in range(max(0, count - 1))
        ]
        if (
            isinstance(final_record_end_offset, int)
            and record_starts[-1][0] < final_record_end_offset <= len(data)
        ):
            bounded_records.append({
                "recordIndex": count - 1,
                "recordOffset": record_starts[-1][0],
                "recordEndOffset": final_record_end_offset,
                "entityDetailId": record_starts[-1][1],
                "recordBoundarySource": "leveldata_member21_start",
            })
        frames.append({
            "listCountOffset": offset - 4,
            "listCount": count,
            "finalRecordOffset": record_starts[-1][0],
            "records": bounded_records,
        })
    return frames


def parse_leveldata_interactive_narrative_records(
    data: bytes,
    *,
    final_record_end_offset: int | None = None,
    record_parser: Callable[..., dict | None],
) -> list[dict]:
    """Recover fully bounded narrative interactives in LevelData.

    Non-final records use the next typed list item. A caller may supply the
    exact start of top-level member 21 to bound the final record, but only after
    independently validating either the adjacent nonempty member-22 dictionary
    or the complete empty-script members 21-43 suffix.
    """
    if not data or data[0] != 43:
        return []
    rows: list[dict] = []
    seen_offsets: set[int] = set()
    for frame in level_interactive_data_list_frames(
        data,
        final_record_end_offset=final_record_end_offset,
    ):
        for boundary in frame.get("records") or []:
            offset = boundary.get("recordOffset")
            end_offset = boundary.get("recordEndOffset")
            if (
                not isinstance(offset, int)
                or not isinstance(end_offset, int)
                or offset in seen_offsets
            ):
                continue
            parsed = record_parser(
                data,
                offset,
                end_offset,
                allow_progress_lock=True,
            )
            if (
                parsed is None
                or parsed.get("recordEndOffset") != end_offset
            ):
                continue
            seen_offsets.add(offset)
            rows.append({
                **parsed,
                "recordIndex": boundary.get("recordIndex"),
                "interactiveListCount": frame.get("listCount"),
                "interactiveListCountOffset":
                    frame.get("listCountOffset"),
                "recordBoundarySource":
                    boundary.get("recordBoundarySource"),
            })
    return rows


def parse_leveldata_interactive_horn_dialog_records(
    data: bytes,
    *,
    final_record_end_offset: int | None = None,
    record_parser: Callable[..., dict | None],
) -> list[dict]:
    """Recover fully bounded ``int_horn.properties.dialog_id`` consumers."""
    if not data or data[0] != 43:
        return []
    rows: list[dict] = []
    seen_offsets: set[int] = set()
    for frame in level_interactive_data_list_frames(
        data,
        final_record_end_offset=final_record_end_offset,
    ):
        for boundary in frame.get("records") or []:
            offset = boundary.get("recordOffset")
            end_offset = boundary.get("recordEndOffset")
            if (
                not isinstance(offset, int)
                or not isinstance(end_offset, int)
                or offset in seen_offsets
            ):
                continue
            parsed = record_parser(
                data,
                offset,
                end_offset,
            )
            if parsed is None:
                continue
            seen_offsets.add(offset)
            rows.append({
                **parsed,
                "recordIndex": boundary.get("recordIndex"),
                "interactiveListCount": frame.get("listCount"),
                "interactiveListCountOffset": frame.get("listCountOffset"),
                "recordBoundarySource":
                    boundary.get("recordBoundarySource"),
            })
    return rows


def leveldata_interactive_final_record_boundary(
    data: bytes,
    candidate_script_ids: set[int],
    *,
    expected_level_id: str = "",
    brief_dictionary_parser: Callable[..., dict],
    narrative_record_parser: Callable[..., dict | None],
    horn_record_parser: Callable[..., dict | None],
) -> dict | None:
    """Validate the member-20/21/22 boundary used by a final interactive.

    Current ``LevelData/43`` member 20 is the interactive list and member 21 is
    the fixed-width ``levelIdNum`` integer. A nonempty member-22 BriefData
    dictionary or the complete empty-script members 21-43 suffix supplies an
    exact boundary without borrowing an unrelated byte pattern.
    """
    brief_rows = (
        brief_dictionary_parser(
            data,
            candidate_script_ids,
        )
        if candidate_script_ids
        else {}
    )
    count_offsets = {
        int(row["dictionaryCountOffset"])
        for row in brief_rows.values()
        if isinstance(row.get("dictionaryCountOffset"), int)
    }
    if len(count_offsets) == 1:
        dictionary_count_offset = next(iter(count_offsets))
        member21_offset = dictionary_count_offset - 4
        level_id_num_decoded = read_i32(data, member21_offset)
        if (
            member21_offset > 0
            and level_id_num_decoded is not None
            and level_id_num_decoded[1] == dictionary_count_offset
            and level_id_num_decoded[0] >= 0
        ):
            return {
                "recordEndOffset": member21_offset,
                "levelDataMember21Offset": member21_offset,
                "levelIdNum": level_id_num_decoded[0],
                "levelScriptBriefDictionaryCountOffset":
                    dictionary_count_offset,
                "levelScriptBriefDictionaryCount": len(brief_rows),
                "levelDataFinalBoundaryValidation":
                    "nonempty_levelscript_brief_dictionary",
            }

    # Environment-only LevelData can serialize no LevelScriptBriefData rows.
    # In the current 43-member schema, the complete member-21..43 suffix is
    # independently recognizable: levelIdNum; fourteen empty collections;
    # LevelSafeZoneData/1 with its zero value; exact sceneId; two empty
    # collections; null LevelSpecificData; and three empty collections at EOF.
    candidates: list[dict] = []
    for frame in level_interactive_data_list_frames(data):
        record_offset = frame.get("finalRecordOffset")
        if not isinstance(record_offset, int):
            continue
        parsed = narrative_record_parser(
            data,
            record_offset,
            len(data),
            allow_progress_lock=True,
        )
        if parsed is None:
            parsed = horn_record_parser(
                data,
                record_offset,
                len(data),
                require_end_limit=False,
            )
        if parsed is None:
            continue
        member21_offset = int(parsed["recordEndOffset"])
        cursor = member21_offset
        level_id_num_decoded = read_i32(data, cursor)
        if level_id_num_decoded is None or level_id_num_decoded[0] < 0:
            continue
        level_id_num, cursor = level_id_num_decoded
        collection_offsets: list[int] = []
        valid = True
        for _ in range(14):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or data[cursor : cursor + 5] != b"\x01\x00\x00\x00\x00":
            continue
        safe_zone_offset = cursor
        cursor += 5
        scene_decoded = read_string(
            data,
            cursor,
            max_length=256,
        )
        if scene_decoded is None:
            continue
        scene_id, cursor = scene_decoded
        if expected_level_id and scene_id != expected_level_id:
            continue
        for _ in range(2):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor >= len(data) or data[cursor] != 0xFF:
            continue
        specific_data_offset = cursor
        cursor += 1
        for _ in range(3):
            decoded = read_count(data, cursor, max_count=0)
            if decoded is None or decoded[0] != 0:
                valid = False
                break
            collection_offsets.append(cursor)
            _, cursor = decoded
        if not valid or cursor != len(data):
            continue
        candidates.append({
            "recordEndOffset": member21_offset,
            "levelDataMember21Offset": member21_offset,
            "levelIdNum": level_id_num,
            "levelScriptBriefDictionaryCountOffset":
                collection_offsets[0],
            "levelScriptBriefDictionaryCount": 0,
            "levelScriptDataPathDictionaryCountOffset":
                collection_offsets[1],
            "levelScriptDataPathDictionaryCount": 0,
            "levelDataSafeZoneOffset": safe_zone_offset,
            "levelDataSceneId": scene_id,
            "levelDataSpecificDataOffset": specific_data_offset,
            "levelDataEmptySuffixEndOffset": cursor,
            "levelDataFinalBoundaryValidation":
                "complete_empty_script_suffix_to_eof",
        })
    unique = {
        int(row["recordEndOffset"]): row
        for row in candidates
    }
    return next(iter(unique.values())) if len(unique) == 1 else None

