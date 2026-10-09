"""Isolated forward BuffData root replay for one CreateBuff ability action.

This route is deliberately narrower than the Buff corpus. It reads the original
logical bytes from the root header through physical EOF and refuses every
positive recursive collection except one certified CreateBuff action and the
separately reviewed DataPair list. The canonical corpus integrates and
independently replays the receipt (see below).

It accepts only a sole ``CreateBuffAction`` in ``abilityEventAction``, an
empty ``buffEventAction``, and the already supported other root children,
and composes the CreateBuff input, ``BlackboardDouble``, ``TargetSettings``,
recursive ``DirectionSettings`` and ``SelectorData`` children,
and ``BuffIconDurationSourceSetting`` child receipts. The complete shared
action proof supplies these children to both root paths; this adapter keeps
its independent sole-action, input-cardinality and root-field restrictions.
It reads the original
logical bytes through all thirty root members, checks the stored ``id``
against the source stem and reaches physical EOF. ``buff_corpus`` integrates
this receipt per accepted row, and ``scripts.game_data.jsondata_corpus``
re-checks the installed native build, source SHA and the entire receipt
before classifying the row as schema decoded. Assignment execution, decoded
string parity, duration selection and gameplay effects remain unobserved.
"""
from __future__ import annotations
from scripts.game_data.memorypack import buff_recursive_actions

import hashlib
import struct
from pathlib import PurePosixPath
from typing import Any

from scripts.game_data.memorypack import (
    buff_adding_cooldown,
    buff_create_buff_action_receipt as create,
    buff_datapair_native,
    buff_dispel_config, buff_icon_config,
    buff_stacking_compact_native,
    buff_timeline_empty_native,
)
from scripts.game_data.memorypack.buff import (
    read_buff_blackboard_float_raw_field_bounded,
    read_buff_blackboard_int_field, read_buff_bool_field,
    read_buff_memorypack_utf8_string_strict_bounded,
)
from scripts.game_data.memorypack.buff_actions import event_prefix, root_continuation
from scripts.game_data.memorypack.buff_root_no_positive_native import (
    _contract as _root_contract,
    validate_current_native_contract as validate_root_native,
)


SCHEMA = "endfield.buff-root-single-create-action-receipt.v1"
LABEL = "buffRootSingleCreateAction"


def validate_current_native_contract(*, recursive_validation: dict[str, Any] | None = None) -> dict[str, Any]:
    """Use the shared complete action proof, retaining this root's own gates.

    Corpus orchestration supplies its already validated recursive context.
    Standalone callers build that same context once, so a new nested owner
    cannot be silently omitted by an older, separately maintained child list.
    """
    root = validate_root_native()
    if root.get("status") != "validated":
        raise ValueError(f"{LABEL}.native:root-{root.get('status')}")
    recursive = (buff_recursive_actions.validate_current_native_contract()
                 if recursive_validation is None else recursive_validation)
    if (recursive.get("status") != "validated"
            or recursive.get("nativeInputs") != root["nativeInputs"]):
        raise ValueError(f"{LABEL}.native:recursive-actions-status-or-build")
    action_children = recursive.get("children", {})
    required = ("create", "iconDuration", "createInput", "blackboard", "target",
                "direction", "selector", "characterTeamFinder", "directionTargets",
                "selectorGeometry", "selectorPostprocessors")
    for name in required:
        if action_children.get(name, {}).get("status") != "validated":
            raise ValueError(f"{LABEL}.native:recursive-actions-child={name}")
    children = {
        "addingCooldown": buff_adding_cooldown.validate_current_native_contract(),
        "blackboardDataPairs": buff_datapair_native.validate_current_native_contract(),
        "dispelConfig": buff_dispel_config.validate_current_native_contract(),
        "iconConfig": buff_icon_config.validate_current_native_contract(),
        "stackingSettings": buff_stacking_compact_native.validate_current_native_contract(),
        "timelineActions": buff_timeline_empty_native.validate_current_native_contract(),
    }
    children.update(action_children)
    for name, child in children.items():
        if child.get("status") != "validated":
            raise ValueError(f"{LABEL}.native:{name}-{child.get('status')}")
        child_inputs = child.get("nativeInputs")
        if child_inputs is not None and any(
            child_inputs.get(file) != root["nativeInputs"][file]
            for file in ("GameAssembly.dll", "global-metadata.dat")
        ):
            raise ValueError(f"{LABEL}.native:{name}-build-drift")
    return {"status": "validated", "nativeInputs": root["nativeInputs"],
            "root": root, "children": children}


def _decode_single_create_action(
    data: bytes, source: str, digest: str, start: int, end: int,
    native: dict[str, Any],
) -> dict[str, Any]:
    action = buff_recursive_actions.decode_create_action(data, source, digest, start, end, native)
    inputs = action["inputList"]
    if (inputs.get("count") != 1 or len(inputs.get("inputs") or []) != 1
            or inputs["inputs"][0].get("status") != "named-five-member-exact-span"):
        raise ValueError(f"{LABEL}.action:input-list-not-single-exact")
    return action


def decode_single_create_action_root(
    data: bytes, *, source: str, expected_sha256: str,
    native_validation: dict[str, Any],
) -> dict[str, Any]:
    """Replay one selected 30-field root on original bytes, with no anchor."""
    if (native_validation.get("status") != "validated"
            or native_validation.get("root", {}).get("status") != "validated"):
        raise ValueError(f"{LABEL}:native-not-validated")
    if (not isinstance(data, bytes) or not data
            or not isinstance(source, str)
            or source.split("/")[:3] != ["Data", "Json", "BuffData"]
            or len(source.split("/")) != 4 or not source.endswith(".json")
            or not isinstance(expected_sha256, str)
            or hashlib.sha256(data).hexdigest().upper() != expected_sha256.upper()):
        raise ValueError(f"{LABEL}:source-or-sha256")
    contract = _root_contract()
    root_names = [row["name"] for row in contract["fields"]]
    if len(root_names) != 30 or data[0] != contract["rootMemberCount"]:
        raise ValueError(f"{LABEL}:root-header-or-contract")
    children = native_validation["children"]
    fields: list[dict[str, Any]] = []

    def add(index: int, start: int, end: int, **detail: Any) -> None:
        if (len(fields) != index or start != (1 if index == 0 else fields[-1]["end"])
                or type(end) is not int or not start < end <= len(data)):
            raise ValueError(f"{LABEL}.field[{index}]:noncontiguous")
        fields.append({"index": index, "name": root_names[index],
                       "start": start, "end": end, **detail})

    def null_or_empty(index: int, cursor: int) -> int:
        if cursor + 4 > len(data):
            raise ValueError(f"{LABEL}.field[{index}]:truncated-count")
        count = struct.unpack_from("<i", data, cursor)[0]
        if count not in (-1, 0):
            raise ValueError(f"{LABEL}.field[{index}]:positive-count={count}")
        add(index, cursor, cursor + 4, count=count)
        return cursor + 4

    first = event_prefix(data, source=source, limit=len(data))
    first_fields = first.get("namedFields") or []
    if (first.get("status") != "supported-prefix"
            or len(first_fields) != 1
            or first_fields[0].get("name") != "abilityEventAction"
            or first_fields[0].get("start") != 1
            or struct.unpack_from("<i", data, 1)[0] != 1):
        raise ValueError(f"{LABEL}.abilityEventAction:unsupported-prefix")
    field_end = first_fields[0]["end"]
    action_spans = [row for row in first.get("completedRecords", [])
                    if row.get("kind") == "union"
                    and 1 <= row.get("start", -1) < field_end]
    if (len(action_spans) != 1 or action_spans[0].get("tag") != create.TAG
            or not action_spans[0]["start"] < action_spans[0]["end"] < field_end):
        raise ValueError(f"{LABEL}.abilityEventAction:not-sole-create")
    action = _decode_single_create_action(
        data, source, expected_sha256.upper(), action_spans[0]["start"],
        action_spans[0]["end"], native_validation,
    )
    add(0, 1, field_end, count=1, actionRange=[action_spans[0]["start"],
                                               action_spans[0]["end"]],
        action=action)
    continuation = root_continuation(
        data, source=source, start=field_end, limit=len(data),
    )
    next_fields = continuation.get("namedFields") or []
    if (continuation.get("status") != "supported-prefix"
            or len(next_fields) != 5
            or [row.get("name") for row in next_fields] != root_names[1:6]):
        raise ValueError(f"{LABEL}.rootContinuation:unsupported-prefix")
    for row in next_fields:
        index = row["index"]
        start, end = row["start"], row["end"]
        if index == 1:
            child = buff_adding_cooldown.decode_adding_cooldown(
                data, start, end, native_validation=children["addingCooldown"],
            )
            add(index, start, end, child=child)
        elif index == 2:
            if end - start < 4:
                raise ValueError(f"{LABEL}.applyTags:truncated")
            count = struct.unpack_from("<i", data, start)[0]
            if count < -1 or count > 4096 or end - start != 4 + max(0, count) * 4:
                raise ValueError(f"{LABEL}.applyTags:count={count}")
            add(index, start, end, count=count)
        elif index == 3:
            if (end - start != 6 or data[start] != 2
                    or struct.unpack_from("<i", data, start + 1)[0] not in (-1, 0)):
                raise ValueError(f"{LABEL}.attributeModifier:nonempty")
            add(index, start, end, arrayCount=struct.unpack_from("<i", data, start + 1)[0])
        elif index == 4:
            child = buff_datapair_native.decode_datapair_list(
                data, start, end,
                native_validation=children["blackboardDataPairs"],
                require_end=False,
            )
            if child.get("consumedEnd") != end or child.get("wholeListExact") is not True:
                raise ValueError(f"{LABEL}.blackboard:child-end")
            add(index, start, end, count=child["count"], child=child)
        elif index == 5:
            if end - start != 4 or struct.unpack_from("<i", data, start)[0] not in (-1, 0):
                raise ValueError(f"{LABEL}.buffEventAction:nonempty")
            add(index, start, end, count=struct.unpack_from("<i", data, start)[0])
    cursor = continuation["consumedEnd"]
    cursor = null_or_empty(6, cursor)
    start = cursor
    child = buff_dispel_config.decode_dispel_config(
        data, start, start + 8, native_validation=children["dispelConfig"],
    )
    cursor = start + 8
    add(7, start, cursor, child=child)
    start = cursor
    value, cursor = read_buff_blackboard_float_raw_field_bounded(
        data, start, len(data), root_names[8],
    )
    child = buff_adding_cooldown.decode_adding_cooldown(
        data, start, cursor, native_validation=children["addingCooldown"],
    )
    add(8, start, cursor, value=value, child=child)
    start = cursor
    value, cursor = read_buff_bool_field(data, start, root_names[9])
    add(9, start, cursor, value=value)
    cursor = null_or_empty(10, cursor)
    for index in (11, 12):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, root_names[index])
        add(index, start, cursor, value=value)
    cursor = null_or_empty(13, cursor)
    start = cursor
    child = buff_icon_config.decode_icon_config(data, start, len(data), require_limit_end=False)
    cursor = child["consumedEnd"]
    add(14, start, cursor, child=child)
    start = cursor
    buff_id, cursor = read_buff_memorypack_utf8_string_strict_bounded(
        data, start, len(data), "id", max_length=512,
    )
    if buff_id != PurePosixPath(source).stem:
        raise ValueError(f"{LABEL}.id:source-name-mismatch={buff_id!r}")
    add(15, start, cursor, value=buff_id)
    cursor = null_or_empty(16, cursor)
    for index in (17, 18):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, root_names[index])
        add(index, start, cursor, value=value)
    start = cursor
    if start >= len(data):
        raise ValueError(f"{LABEL}.lifeType:truncated")
    cursor += 1
    add(19, start, cursor, rawByte=data[start])
    start = cursor
    value, cursor = read_buff_blackboard_int_field(data, start, root_names[20])
    add(20, start, cursor, value=value)
    start = cursor
    value, cursor = read_buff_bool_field(data, start, root_names[21])
    add(21, start, cursor, value=value)
    cursor = null_or_empty(22, cursor)
    cursor = null_or_empty(23, cursor)
    start = cursor
    child = buff_stacking_compact_native.decode_stacking_settings_compact(
        data, start, native_validation=children["stackingSettings"],
    )
    if child.get("stackEffectsCount") != 0:
        raise ValueError(f"{LABEL}.stackingSettings:positive-stack-effects")
    cursor = child["consumedEnd"]
    add(24, start, cursor, child=child)
    start = cursor
    if start + 4 > len(data):
        raise ValueError(f"{LABEL}.tagsAfterTriggerExtendBuffAction:truncated")
    count = struct.unpack_from("<i", data, start)[0]
    if count < -1 or count > 4096 or start + 4 + max(0, count) * 4 > len(data):
        raise ValueError(f"{LABEL}.tagsAfterTriggerExtendBuffAction:count={count}")
    cursor = start + 4 + max(0, count) * 4
    add(25, start, cursor, count=count)
    start = cursor
    child = buff_timeline_empty_native.decode_empty_timeline_suffix(
        data, start, native_validation=children["timelineActions"],
    )
    cursor = child["consumedEnd"]
    add(26, start, cursor, child=child)
    start = cursor
    value, cursor = read_buff_blackboard_float_raw_field_bounded(
        data, start, len(data), root_names[27],
    )
    named_child = buff_adding_cooldown.decode_adding_cooldown(
        data, start, cursor, native_validation=children["addingCooldown"],
    )
    add(27, start, cursor, value=value, child=named_child)
    for index in (28, 29):
        start = cursor
        value, cursor = read_buff_bool_field(data, start, root_names[index])
        add(index, start, cursor, value=value)
    if (cursor != len(data) or cursor != child.get("followingEnd")
            or len(fields) != 30 or fields[-1]["end"] != len(data)):
        raise ValueError(f"{LABEL}.physical-eof:cursor={cursor}; length={len(data)}")
    return {"schema": SCHEMA, "status": "named-exact-full-proposal",
            "source": source, "logicalSha256": expected_sha256.upper(),
            "wholeSchemaExact": True, "rootMemberCount": 30,
            "headerRange": [0, 1], "fields": fields,
            "bytesConsumed": cursor, "physicalEof": len(data),
            "nativeStatus": "validated",
            "evidenceBoundary": (
                "Selected root and action readers, source-hash-checked original "
                "bytes, one CreateBuff action with directly named nested children, "
                "thirty contiguous root fields, source id equality, and physical "
                "EOF. Live formatter provider choice and gameplay effects remain "
                "separate from stored schema."
            )}
