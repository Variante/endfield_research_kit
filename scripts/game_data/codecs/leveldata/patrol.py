"""Exact current-wrapper codecs for authored LevelData NPC patrols.

- ``npcPatrol`` (internal pooled codec via ``npc_patrol_decoder``): the generated ten-field
  ``NpcPatrolData`` owner, three-field points and positive
  ``PatrolSubAction`` lists. The action codec follows all 26 generated
  members, including the four-field ``Beyond.Blackboard.DataPair`` order
  (``isDynamic``, ``key``, ``valueDouble``, ``valueStr``). Its polymorphic
  ``subActionData`` admits only null, tag-0 three-field
  ``PatrolSubActionEnvTalkData`` and tag-1 one-field
  ``PatrolSubPlayAudioData``; the latter stores ``AudioId._id`` as an
  signed 32-bit value in the native-gated NPC Patrol profile; the separate
  PatrolData stored-layout lane remains independently bounded.
- ``patrols`` (``decode_patrol_list``): the authored patrol grammar also
  used by Spawner routes. ``PatrolData`` has 39 stored members, beginning
  with the action list and ending with ``worldOffset``; each
  ``PatrolAction`` has four members (``actionType``, position, subactions,
  subpositions) and reuses the same ``PatrolSubActionData`` union routes.

Unknown tags, changed member counts and malformed nested values fail
closed. Exact stored layout; it does not prove runtime traversal or audio
playback.
"""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import (
    read_bool,
    read_count,
    read_f32,
    read_f64,
    read_i32,
    read_string,
    read_u32,
)


PATROL_SUB_ACTION_TYPE_NAMES = {
    0: "None",
    1: "Wait",
    2: "TurnTo",
    3: "PlayAnimation",
    4: "Rest",
    5: "PlayEnvTalk",
    6: "PlayRadio",
    7: "EventToLevel",
    8: "ConfigMovement",
    9: "PlayRadioInRange",
    10: "PlayRadioAtTime",
    11: "PlayAudio",
    12: "EnemyPatrolEvent",
}


def _read_vector3(data: bytes, offset: int) -> tuple[list[float], int] | None:
    values: list[float] = []
    for _ in range(3):
        decoded = read_f32(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        values.append(value)
    return values, offset


def _read_fields(
    data: bytes,
    offset: int,
    readers: tuple[tuple[str, Callable[[bytes, int], tuple[Any, int] | None]], ...],
) -> tuple[dict[str, Any], int] | None:
    values: dict[str, Any] = {}
    for name, reader in readers:
        decoded = reader(data, offset)
        if decoded is None:
            return None
        values[name], offset = decoded
    return values, offset


def _read_blackboard_pairs(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    """Read ``List<Beyond.Blackboard.DataPair>`` in generated member order."""

    start = offset
    count_decoded = read_count(data, offset, max_count=256)
    if count_decoded is None:
        return None
    count, offset = count_decoded
    rows: list[dict[str, Any]] = []
    for index in range(max(0, count)):
        row_start = offset
        if offset >= len(data) or data[offset] != 4:
            return None
        offset += 1
        decoded = _read_fields(data, offset, (
            ("isDynamic", read_bool),
            ("key", read_string),
            ("valueDouble", read_f64),
            ("valueStr", read_string),
        ))
        if decoded is None:
            return None
        values, offset = decoded
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": offset,
            "memberCount": 4,
            **values,
        })
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _read_sub_action_data(data: bytes, offset: int) -> tuple[dict[str, Any] | None, int] | None:
    """Read the current two-route ``PatrolSubActionData`` MemoryPack union."""

    start = offset
    if offset >= len(data):
        return None
    tag = data[offset]
    offset += 1
    if tag == 0xFF:
        return None, offset
    if tag == 0:
        if offset >= len(data) or data[offset] != 3:
            return None
        offset += 1
        decoded = _read_fields(data, offset, (
            ("envTalkId", read_string),
            ("npcId", read_string),
            ("overrideNpc", read_bool),
        ))
        if decoded is None:
            return None
        values, offset = decoded
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 3,
            "typeName": "PatrolSubActionEnvTalkData",
            **values,
        }, offset
    if tag == 1:
        if offset >= len(data) or data[offset] != 1:
            return None
        offset += 1
        audio_id = read_u32(data, offset)
        if audio_id is None:
            return None
        audio_id_value, offset = audio_id
        return {
            "startOffset": start,
            "endOffset": offset,
            "unionTag": tag,
            "memberCount": 1,
            "typeName": "PatrolSubPlayAudioData",
            "audioEventId": audio_id_value,
        }, offset
    return None


def _read_patrol_sub_action(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 26:
        return None
    offset += 1
    decoded = _read_fields(data, offset, (
        ("actionEndTypeRaw", read_i32),
        ("animKeyTagId", read_i32),
        ("animMaskTypeRaw", read_i32),
        ("animName", read_string),
        ("configMovementStyle", read_bool),
        ("configSnap", read_bool),
        ("duration", read_f32),
    ))
    if decoded is None:
        return None
    values, offset = decoded
    pairs = _read_blackboard_pairs(data, offset)
    if pairs is None:
        return None
    values["eventBBDataPairs"], offset = pairs
    decoded = _read_fields(data, offset, (
        ("eventKey", read_string),
        ("eventToLevelTypeRaw", read_i32),
        ("ignoreAnimDis", read_f32),
        ("movementStyleRaw", read_i32),
        ("npcPlayAnimationTimeEndForceToIdle", read_bool),
        ("overrideSpeed", read_bool),
        ("overrideSpeedValue", read_f32),
        ("radioId", read_string),
        ("radioWaitTime", read_f32),
        ("radius", read_f32),
        ("repeatAnim", read_bool),
        ("rootMotion", read_bool),
        ("rotationOffset", read_f32),
        ("rotationY", read_f32),
        ("snapToGroundRaw", read_i32),
    ))
    if decoded is None:
        return None
    trailing, offset = decoded
    values.update(trailing)
    sub_action_data = _read_sub_action_data(data, offset)
    if sub_action_data is None:
        return None
    values["subActionData"], offset = sub_action_data
    decoded = _read_fields(data, offset, (
        ("typeRaw", read_i32),
        ("waitTime", read_f32),
    ))
    if decoded is None:
        return None
    trailing, offset = decoded
    values.update(trailing)
    type_raw = values["typeRaw"]
    values["typeName"] = PATROL_SUB_ACTION_TYPE_NAMES.get(type_raw, "")
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 26,
        **values,
    }, offset


def _read_vector3_list(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, offset = decoded
    rows: list[list[float]] = []
    for _ in range(max(0, count)):
        value = _read_vector3(data, offset)
        if value is None:
            return None
        point, offset = value
        rows.append(point)
    return {
        "startOffset": start,
        "endOffset": offset,
        "count": count,
        "value": None if count == -1 else rows,
    }, offset


def _read_patrol_action(data: bytes, offset: int) -> tuple[dict[str, Any], int] | None:
    start = offset
    if offset >= len(data) or data[offset] != 4:
        return None
    offset += 1
    action_type = read_i32(data, offset)
    if action_type is None:
        return None
    action_type_value, offset = action_type
    position = _read_vector3(data, offset)
    if position is None:
        return None
    position_value, offset = position
    subactions_start = offset
    subaction_count_decoded = read_count(data, offset, max_count=100_000)
    if subaction_count_decoded is None:
        return None
    subaction_count, offset = subaction_count_decoded
    subactions: list[dict[str, Any]] = []
    for _ in range(max(0, subaction_count)):
        decoded = _read_patrol_sub_action(data, offset)
        if decoded is None:
            return None
        value, offset = decoded
        subactions.append(value)
    subactions_end = offset
    subpositions = _read_vector3_list(data, offset)
    if subpositions is None:
        return None
    subpositions_value, offset = subpositions
    return {
        "startOffset": start,
        "endOffset": offset,
        "memberCount": 4,
        "actionTypeRaw": action_type_value,
        "position": position_value,
        "subActions": {
            "startOffset": subactions_start,
            "endOffset": subactions_end,
            "count": subaction_count,
            "value": None if subaction_count == -1 else subactions,
        },
        "subPositions": subpositions_value,
    }, offset


def decode_patrol_list(data: bytes, offset: int) -> dict[str, Any] | None:
    """Decode the generated ``List<PatrolData>`` used by LevelData."""

    start = offset
    decoded = read_count(data, offset, max_count=100_000)
    if decoded is None:
        return None
    count, cursor = decoded
    rows: list[dict[str, Any]] = []
    for index in range(max(0, count)):
        row_start = cursor
        if cursor >= len(data) or data[cursor] != 39:
            return None
        cursor += 1
        actions_start = cursor
        action_count_decoded = read_count(data, cursor, max_count=100_000)
        if action_count_decoded is None:
            return None
        action_count, cursor = action_count_decoded
        actions: list[dict[str, Any]] = []
        for _ in range(max(0, action_count)):
            action = _read_patrol_action(data, cursor)
            if action is None:
                return None
            action_value, cursor = action
            actions.append(action_value)
        actions_end = cursor
        values_decoded = _read_fields(data, cursor, (
            ("addBornPositionAsCheckpoint", read_bool),
            ("bornMoveStyleRaw", read_i32),
            ("bornOverrideSpeed", read_f32),
            ("bornPositionWaitDuration", read_f32),
            ("changePlayerMoveStyle", read_bool),
            ("coolDownBetweenWalkAndStop", read_f32),
            ("enableBornAction", read_bool),
            ("enableBornSpeedOverride", read_bool),
            ("forbidNpcInteract", read_bool),
            ("forcePlayerMoveStyleRaw", read_i32),
            ("id", read_i32),
            ("inLocalSpace", read_bool),
            ("isLimitPlayerActionWhenGaitLimit", read_bool),
            ("isStopDistance", read_bool),
            ("isUseCatmull", read_bool),
            ("limitPlayerActionTypeRaw", read_i32),
            ("loopRaw", read_i32),
            ("motionEnterDis", read_f32),
            ("motionTypeRaw", read_i32),
            ("moveStyleWithoutLeadRaw", read_i32),
            ("pauseActionWhenPatrolDisabled", read_bool),
            ("playerChangeLimitDelayTime", read_f32),
            ("runAheadRadius", read_f32),
            ("runBehindRadius", read_f32),
            ("snapRaw", read_i32),
            ("sprintAheadRadius", read_f32),
            ("sprintBehindRadius", read_f32),
            ("stop2WalkBufferTime", read_f32),
            ("stopWalkInplace", read_bool),
            ("turnCheck", read_bool),
            ("turnCheckAngle", read_f32),
            ("turnCheckDis", read_f32),
            ("turnCheckTime", read_f32),
            ("turnRadio", read_f32),
            ("usePatrolPointEnterGaitAsLimitGait", read_bool),
            ("useWorldOffset", read_bool),
            ("waitDistance", read_f32),
        ))
        if values_decoded is None:
            return None
        values, cursor = values_decoded
        world_offset = _read_vector3(data, cursor)
        if world_offset is None:
            return None
        world_offset_value, cursor = world_offset
        rows.append({
            "indexInCollection": index,
            "startOffset": row_start,
            "endOffset": cursor,
            "memberCount": 39,
            "actions": {
                "startOffset": actions_start,
                "endOffset": actions_end,
                "count": action_count,
                "value": None if action_count == -1 else actions,
            },
            **values,
            "worldOffset": world_offset_value,
        })
    return {
        "startOffset": start,
        "endOffset": cursor,
        "count": count,
        "value": None if count == -1 else rows,
        "rows": rows,
        "evidenceBoundary": (
            "exact current generated PatrolData member-39 and PatrolAction member-4 "
            "wrappers; nested PatrolSubActionData retains its maintained union gate"
        ),
        "fieldOrderSource": "current generated MemoryPack wrappers",
    }


class NpcPatrolFramingError(ValueError):
    def __init__(self, gate, field, offset, expected=None, actual=None):
        self.diagnostic = dict(validator="leveldataNpcPatrol", gate=gate, field=field,
                               offset=offset, expected=expected, actual=actual)
        super().__init__(f"npcPatrol.{gate}: field={field} offset={offset} "
                         f"expected={str(expected)[:250]} actual={str(actual)[:350]}")


def _decode_current_patrol(data, offset, *, strings, layout, root_record=None, node_budget=None):
    """Shared finite pooled evaluator; callers independently authenticate parents."""
    import math
    import struct
    from scripts.game_data.string_pool import resolve_string_pool_index

    def scalar(fmt, field):
        nonlocal offset
        size = struct.calcsize("<" + fmt)
        if not 0 <= offset <= len(data) - size:
            raise NpcPatrolFramingError("truncated", field, offset, size, len(data) - offset)
        value = struct.unpack_from("<" + fmt, data, offset)[0]
        offset += size
        if fmt == "f" and not math.isfinite(value):
            raise NpcPatrolFramingError("nonfinite", field, offset - size, "finite", str(value))
        return value

    def collection(element, field, *, empty=False):
        start = offset
        count = scalar("i", field + ".count")
        limit = 0 if empty else layout["countLimit"]
        if not -1 <= count <= limit:
            raise NpcPatrolFramingError("collection-elements-unproved" if empty else "count-unproved",
                                        field, start, [-1, limit], count)
        if node_budget is not None and count>node_budget[0]:
            raise NpcPatrolFramingError('node-limit',field,start)
        rows = [record(element, f"{field}[{i}]") for i in range(max(0, count))]
        for index, row in enumerate(rows):
            if row is not None:
                row["indexInCollection"] = index
        return dict(startOffset=start, endOffset=offset, count=count,
                    value=None if count == -1 else rows, rows=rows)

    def data_pair_collection(field):
        nonlocal offset
        child=layout.get('dataPairCapability',{})
        cap=layout.get('dataPairListCapability',{})
        name='Beyond.Blackboard+DataPair'
        plan=[dict(fieldName=f,kind=k)for f,k in (
            ('isDynamic','bool'),('key','pooled-string'),('valueDouble','double-bits'),('valueStr','pooled-string'))]
        if child.get('nullReturnsDefaultValue')is not True or (child.get('typeName'),child.get('memberCount'),child.get('managedBytes'),
                child.get('nullMarker'),child.get('nullReturnsDefaultValue'),child.get('orderedReads'))!=(name,4,32,255,True,plan):
            raise NpcPatrolFramingError('DataPair-child-unproved',field,offset)
        if cap.get('positiveCountsAdmitted')is not True or cap.get('elementGrammarAdmitted')is not True or (cap.get('closedListType'),cap.get('countLimit'),cap.get('positiveCountsAdmitted'),
                cap.get('elementGrammarAdmitted'),cap.get('managedElementBytes'))!=(
                'System.Collections.Generic.List`1<'+name+'>',4096,True,True,32):
            raise NpcPatrolFramingError('DataPair-list-unproved',field,offset)
        start=offset;count=scalar('i',field+'.count')
        if type(count)is not int or not -1<=count<=4096:
            raise NpcPatrolFramingError('count-unproved',field,start,[-1,4096],count)
        if node_budget is not None:
            if count>node_budget[0]:raise NpcPatrolFramingError('node-limit',field,start)
            node_budget[0]-=max(count,0)
        rows=[]
        for index in range(max(0,count)):
            at=offset;marker=scalar('B',field+'.memberCount')
            if marker==255:
                values=dict(isDynamic=False,key=None,valueDouble=0.0,valueDoubleBits='0000000000000000',valueStr=None,
                    defaultValue=True)
            elif marker==4:
                dynamic=scalar('B',field+'.isDynamic')
                key=resolve_string_pool_index(scalar('i',field+'.key'),strings,field+'.key')
                raw_at=offset;value=scalar('d',field+'.valueDouble')
                text=resolve_string_pool_index(scalar('i',field+'.valueStr'),strings,field+'.valueStr')
                values=dict(isDynamic=bool(dynamic),key=key,valueDouble=value if math.isfinite(value)else None,
                    valueDoubleBits=bytes(data[raw_at:raw_at+8]).hex(),valueStr=text,defaultValue=False)
            else:
                raise NpcPatrolFramingError('member-count',field,at,[4,255],marker)
            rows.append(dict(startOffset=at,endOffset=offset,indexInCollection=index,memberCount=marker,
                recordType=name,**values))
        return dict(startOffset=start,endOffset=offset,count=count,value=None if count==-1 else rows,rows=rows)

    def record(name, field, *, nullable=True):
        start = offset
        if node_budget is not None:
            if node_budget[0]<=0:raise NpcPatrolFramingError('node-limit',field,start)
            node_budget[0]-=1
        marker = scalar("B", field + ".memberCount")
        if nullable and marker == 255:
            return None
        fields = layout["records"][name]
        if marker != len(fields):
            raise NpcPatrolFramingError("member-count", field, start, len(fields), marker)
        values, spans, enum_names = {}, {}, {}
        for row in fields:
            key, wire, at = row["name"], row["wire"], offset
            path = field + "." + key
            if wire in ("i32", "f32", "bool"):
                value = scalar({"i32": "i", "f32": "f", "bool": "B"}[wire], path)
                if wire == "bool":
                    value = bool(value)
            elif wire == "pool":
                value = resolve_string_pool_index(scalar("i", path), strings, path)
            elif wire == "vector3":
                value = [scalar("f", path + "." + axis) for axis in ("x", "y", "z")]
            elif wire in ("list", "empty-list"):
                value = collection(row["element"], path, empty=wire == "empty-list")
            elif wire == 'data-pair-list':
                value = data_pair_collection(path)
            elif wire == "union":
                tag = scalar("B", path + ".unionTag")
                if tag == 255:
                    value = None
                elif str(tag) in layout["union"]:
                    value = record(layout["union"][str(tag)], path, nullable=False)
                    value["unionTag"] = tag
                else:
                    raise NpcPatrolFramingError("union-tag-unproved", path, at, [0, 1, 255], tag)
            else:
                raise NpcPatrolFramingError("wire-unproved", path, at, None, wire)
            values[key], spans[key] = value, [at, offset]
            enum = next((e for e in layout["enums"] if (e["parent"], e["field"]) == (name, key)), None)
            if enum:
                enum_names[key] = enum["values"].get(str(value))
        return dict(startOffset=start, endOffset=offset, memberCount=marker,
                    recordType=name, fieldRanges=spans, enumNames=enum_names, **values)

    if root_record is not None:
        value=record(root_record,'patrolSubAction');return value,offset
    return collection(layout["root"], "npcPatrol")


def _decode_npc_patrol_list(data,offset,*,strings,layout):
    """Current NPC list frontdoor, selected by its lexical native operation."""
    return _decode_current_patrol(data,offset,strings=strings,layout=layout)


def _decode_pooled_patrol_sub_action(data,offset,*,strings,layout,node_budget):
    """Read an already authenticated SubAction child without fabricating a list."""
    if (not isinstance(node_budget,list)or len(node_budget)!=1 or type(node_budget[0])is not int
            or node_budget[0]<=0):raise NpcPatrolFramingError('node-limit','patrolSubAction',offset)
    return _decode_current_patrol(data,offset,strings=strings,layout=layout,
        root_record='Beyond.Gameplay.Core.PatrolSubAction',node_budget=node_budget)
