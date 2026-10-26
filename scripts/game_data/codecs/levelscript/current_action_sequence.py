"""Current sequential map framing through authenticated reviewed node readers.

Every action, getter and header uses ActionMap with the selected StringPool.
The owner must still reach physical EOF. Positive blackboards require their
own current contract; unsupported children remain bounded refusals.
"""

from __future__ import annotations


from scripts.game_data.codecs.levelscript import action_map as levelscript_action_map


from scripts.game_data.codecs.levelscript.param_graph import ParamGraphDecodeError,decode_param_blackboard


from scripts.game_data.codecs.levelscript.framing_common import LevelScriptTopLevelFramingError


from scripts.game_data.codecs.levelscript.primitives import i32 as _i32


from scripts.game_data.codecs.levelscript.sequential_owner import _frame_levelscript_sequential_owner


from scripts.game_data import levelscript_union_tags as union_tags




from typing import Any


def _preload_cutscene_layout(member_count: int = 17) -> dict[str, Any]:
    """Require the name-keyed v5 layout and selected-build union gate.

    The generated reader inserts option controls among the older preload
    fields. Reading the former twelve-member body would lose the cursor.
    """
    validator = "levelscriptPreloadCutscene"
    audit = union_tags.union_tags_audit()

    def refuse(gate: str, expected: Any, actual: Any) -> None:
        error = LevelScriptTopLevelFramingError(
            f"validator={validator},gate={gate},action=PreloadCutsceneAction,"
            f"expected={expected},actual={actual},memberCount={member_count},"
            f"source={levelscript_action_map.CONTRACT_PATH}"
        )
        error.diagnostics = {
            "validator": validator, "gate": gate, "action": "PreloadCutsceneAction",
            "expected": expected, "actual": actual, "memberCount": member_count,
            "source": str(levelscript_action_map.CONTRACT_PATH),
        }
        raise error

    if audit.get("status") != "validated":
        refuse("installed-native-inputs", "validated", audit.get("status"))
    pair = union_tags.pair("ActionBase", "PreloadCutsceneAction")
    if not isinstance(pair[0], int) or pair[1] != 17:
        refuse("catalog-member-count", 17, pair[1:] if not isinstance(pair[0], int) else pair[1])
    if member_count != 17:
        refuse("serialized-member-count", 17, member_count)
    try:
        layouts = levelscript_action_map._contract()["layouts"]
    except (ValueError, KeyError, OSError) as error:
        refuse("reviewed-layout-contract", levelscript_action_map.LAYOUT_SCHEMA, str(error)[:240])
    rows = [row for row in layouts if row.get("family") == "ActionBase"
            and union_tags.short_name(row.get("wrapperName", "")) == "PreloadCutsceneAction"]
    if len(rows) != 1:
        refuse("reviewed-layout-row", 1, len(rows))
    row = rows[0]
    if row.get("memberCount") != 17 or len(row.get("fields", [])) != 17:
        refuse("reviewed-member-count", 17,
               [row.get("memberCount"), len(row.get("fields", []))])
    return row


def _read_reviewed_map_node(
    data: bytes, cursor: int, family: str, original_error: ValueError | None = None, *, strings: Any = None, game_root=None, null_list_params=None,
) -> tuple[dict[str, Any], int]:
    try:
        return levelscript_action_map.decode_reviewed_node(data, cursor, family, strings=strings,game_root=game_root,null_list_params=null_list_params)
    except levelscript_action_map.ActionMapCodecError as error:
        if getattr(error, "diagnostics", {}).get("validator") == "levelscriptPreloadCutscene":
            refusal = LevelScriptTopLevelFramingError(
                f"reviewed {family} at offset={cursor}: {error}"
            )
            refusal.diagnostics = error.diagnostics
            raise refusal from error
        raise LevelScriptTopLevelFramingError(
            f"{str(original_error)+'; ' if original_error is not None else ''}reviewed {family} at offset={cursor}: {error}"
        ) from error


def frame_levelscript_current_action_sequence_leader_enter(
    data: bytes,
    *, strings: Any = None, game_root=None, null_list_params=None, npc_decoder=None,
) -> dict[str, Any]:
    """Close selected current sequences, including reviewed shared union layouts."""
    if len(data) < 7 or data[:3] != b"\x1c\x02\x03":
        raise LevelScriptTopLevelFramingError("selected action map root/member mismatch")
    action_count = _i32(data, 3)
    if action_count is None or not 0 <= action_count <= 4096:
        raise LevelScriptTopLevelFramingError("invalid selected actionList count")
    cursor = 7
    actions = []
    for _index in range(action_count):
        action,cursor=_read_reviewed_map_node(data,cursor,'ActionBase',strings=strings,game_root=game_root,null_list_params=null_list_params)
        actions.append(action)
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated getterList count")
    getter_count = _i32(data, cursor)
    if getter_count is None or getter_count < 0 or getter_count > 4096:
        raise LevelScriptTopLevelFramingError(
            f"invalid selected getterList count={getter_count}"
        )
    cursor += 4
    getters = []
    for _index in range(getter_count):
        getter,cursor=_read_reviewed_map_node(data,cursor,'GetterBase',strings=strings,game_root=game_root,null_list_params=null_list_params)
        getters.append(getter)
    if cursor + 4 > len(data):
        raise LevelScriptTopLevelFramingError("truncated headerList count")
    header_count = _i32(data, cursor)
    if header_count is None or not 0 <= header_count <= 4096:
        raise LevelScriptTopLevelFramingError(
            "invalid selected headerList count: "
            f"actual={header_count}"
        )
    cursor += 4
    headers = []
    for _index in range(header_count):
        header,cursor=_read_reviewed_map_node(data,cursor,'ActionHeader',strings=strings,game_root=game_root,null_list_params=null_list_params)
        headers.append(header)
    try:
        blackboard, action_map_end = decode_param_blackboard(data,cursor,strings=strings,game_root=game_root)
    except ParamGraphDecodeError as error:
        raise LevelScriptTopLevelFramingError(str(error)) from error
    action_map = {
        "startOffset": 1,
        "endOffset": action_map_end,
        "serializedMemberCount": 2,
        "completeAsset": True,
        "dataMap": {
            "startOffset": 2,
            "endOffset": cursor,
            "serializedMemberCount": 3,
            "actionListCount": action_count,
            "getterListCount": getter_count,
            "headerListCount": header_count,
            "actionList": actions,
            "getterList": getters,
            "headerList": headers,
        },
        "paramBlackboard": blackboard,
    }
    return _frame_levelscript_sequential_owner(
        data,
        action_map=action_map,
        owner_offset=action_map_end,
        action_map_boundary="selected current action/getter/header sequence",
        partial_status="exact_named_current_action_sequence_owner_prefix",
        strings=strings,game_root=game_root,npc_decoder=npc_decoder,
    )
