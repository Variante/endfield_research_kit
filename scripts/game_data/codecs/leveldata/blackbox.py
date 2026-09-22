"""Exact current-wrapper codec for ``LevelDataBlackbox``."""

from __future__ import annotations

from typing import Any, Callable

from .memorypack import read_bool, read_count, read_f32, read_i32, read_string, read_u64


class LevelDataBlackboxCodecError(ValueError):
    pass


def _need(value: Any, field: str) -> Any:
    if value is None:
        raise LevelDataBlackboxCodecError(f"{field}:truncated-or-invalid")
    return value


def _marker(data: bytes, offset: int, field: str, expected: int) -> int:
    if offset >= len(data):
        raise LevelDataBlackboxCodecError(f"{field}:truncated-marker")
    actual = data[offset]
    if actual != expected:
        raise LevelDataBlackboxCodecError(
            f"{field}.memberCount:expected={expected} actual={actual}"
        )
    return offset + 1


def _nullable_object(
    data: bytes, offset: int, field: str, expected: int,
    body: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[Any, int]:
    if offset >= len(data):
        raise LevelDataBlackboxCodecError(f"{field}:truncated-marker")
    if data[offset] == 0xFF:
        return None, offset + 1
    cursor = _marker(data, offset, field, expected)
    return body(data, cursor, field)


def _count(data: bytes, offset: int, field: str, maximum: int = 100_000) -> tuple[int, int]:
    return _need(read_count(data, offset, max_count=maximum), field)


def _string_list(data: bytes, offset: int, field: str) -> tuple[list[str] | None, int]:
    count, cursor = _count(data, offset, field)
    if count == -1:
        return None, cursor
    values: list[str] = []
    for index in range(count):
        value, cursor = _need(
            read_string(data, cursor, max_length=16_384), f"{field}[{index}]"
        )
        if value is None:
            raise LevelDataBlackboxCodecError(f"{field}[{index}]:null")
        values.append(value)
    return values, cursor


def _i32_list(data: bytes, offset: int, field: str) -> tuple[list[int] | None, int]:
    count, cursor = _count(data, offset, field)
    if count == -1:
        return None, cursor
    values: list[int] = []
    for index in range(count):
        value, cursor = _need(read_i32(data, cursor), f"{field}[{index}]")
        values.append(value)
    return values, cursor


def _basic(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    names = (
        "disableSwitchMode", "domainGrade", "enterFactoryModeOnSceneLoaded",
        "lockLogisticConveyor", "lockLogisticConveyorBridge",
        "lockLogisticConveyorConverger", "lockLogisticConveyorSplitter",
        "lockLogisticConveyorValve", "lockLogisticPipe",
        "lockLogisticPipeConnector", "lockLogisticPipeConverger",
        "lockLogisticPipeSplitter", "lockLogisticPipeValve",
    )
    values: dict[str, Any] = {"memberCount": 13}
    cursor = offset
    for name in names:
        reader = read_i32 if name == "domainGrade" else read_bool
        values[name], cursor = _need(reader(data, cursor), f"{field}.{name}")
    return values, cursor


def _one_string_list(data: bytes, offset: int, field: str, name: str) -> tuple[dict[str, Any], int]:
    values, cursor = _string_list(data, offset, f"{field}.{name}")
    return {"memberCount": 1, name: values}, cursor


def _complete(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    values: dict[str, Any] = {"memberCount": 4}
    cursor = offset
    for name in (
        "cannotCompleteWhenBlockedNodeExist",
        "cannotCompleteWhenDanglingConveyorExist",
        "cannotCompleteWhenOutOfPowerExist",
        "cannotCompleteWhenPowerGenLessThanPowerCost",
    ):
        values[name], cursor = _need(read_bool(data, cursor), f"{field}.{name}")
    return values, cursor


def _discard(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    forbid, cursor = _need(read_bool(data, offset), field + ".forbidAllItemDiscard")
    items, cursor = _string_list(data, cursor, field + ".forbidItems")
    return {"memberCount": 2, "forbidAllItemDiscard": forbid, "forbidItems": items}, cursor


def _task(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    level_script_id, cursor = _need(read_u64(data, offset), field + ".levelScriptId")
    task_id, cursor = _need(read_string(data, cursor, max_length=4096), field + ".taskId")
    if task_id is None:
        raise LevelDataBlackboxCodecError(f"{field}.taskId:null")
    return {"memberCount": 2, "levelScriptId": str(level_script_id), "taskId": task_id}, cursor


def _fail_task(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    cursor = _marker(data, offset, field + ".failInfo", 1)
    fail_info, cursor = _need(
        read_string(data, cursor, max_length=16_384), field + ".failInfo.value"
    )
    level_script_id, cursor = _need(read_u64(data, cursor), field + ".levelScriptId")
    task_id, cursor = _need(read_string(data, cursor, max_length=4096), field + ".taskId")
    if fail_info is None or task_id is None:
        raise LevelDataBlackboxCodecError(f"{field}:null-string")
    return {"memberCount": 3, "failInfo": {"memberCount": 1, "value": fail_info},
            "levelScriptId": str(level_script_id), "taskId": task_id}, cursor


def _object_list(
    data: bytes, offset: int, field: str, marker: int,
    body: Callable[[bytes, int, str], tuple[Any, int]],
) -> tuple[list[Any] | None, int]:
    count, cursor = _count(data, offset, field)
    if count == -1:
        return None, cursor
    rows = []
    for index in range(count):
        cursor = _marker(data, cursor, f"{field}[{index}]", marker)
        row, cursor = body(data, cursor, f"{field}[{index}]")
        rows.append(row)
    return rows, cursor


def _general_ability(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    def entry(raw: bytes, cursor: int, item_field: str) -> tuple[dict[str, int], int]:
        ability_type, cursor = _need(read_i32(raw, cursor), item_field + ".abilityType")
        custom_state, cursor = _need(read_i32(raw, cursor), item_field + ".customState")
        return {"memberCount": 2, "abilityType": ability_type, "customState": custom_state}, cursor
    rows, cursor = _object_list(data, offset, field + ".customAbilityStates", 2, entry)
    return {"memberCount": 1, "customAbilityStates": rows}, cursor


def _intro(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    delay, cursor = _need(read_f32(data, offset), field + ".delay")
    intro, cursor = _need(read_string(data, cursor, max_length=4096), field + ".introEffectName")
    loop, cursor = _need(read_string(data, cursor, max_length=4096), field + ".loopEffectName")
    position = []
    for axis in "xyz":
        value, cursor = _need(read_f32(data, cursor), f"{field}.position.{axis}")
        position.append(value)
    return {"memberCount": 4, "delay": delay, "introEffectName": intro,
            "loopEffectName": loop, "position": position}, cursor


def _inventory(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    def bundle(raw: bytes, cursor: int, item_field: str) -> tuple[dict[str, Any], int]:
        count, cursor = _need(read_i32(raw, cursor), item_field + ".count")
        item_id, cursor = _need(read_string(raw, cursor, max_length=4096), item_field + ".id")
        return {"memberCount": 2, "count": count, "id": item_id}, cursor
    def infinite_bundle(raw: bytes, cursor: int, item_field: str) -> tuple[dict[str, Any], int]:
        count, cursor = _need(read_i32(raw, cursor), item_field + ".count")
        item_id, cursor = _need(read_string(raw, cursor, max_length=4096), item_field + ".id")
        infinite, cursor = _need(read_bool(raw, cursor), item_field + ".infinite")
        return {"memberCount": 3, "count": count, "id": item_id, "infinite": infinite}, cursor
    bag, cursor = _object_list(data, offset, field + ".bagContent", 2, bundle)
    slots, cursor = _need(read_i32(data, cursor), field + ".bagSlotCount")
    depot, cursor = _object_list(data, cursor, field + ".depotContent", 3, infinite_bundle)
    locked, cursor = _need(read_bool(data, cursor), field + ".depotManualInOutLocked")
    return {"memberCount": 4, "bagContent": bag, "bagSlotCount": slots,
            "depotContent": depot, "depotManualInOutLocked": locked}, cursor


def _item_bundle(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    count, cursor = _need(read_i32(data, offset), field + ".count")
    item_id, cursor = _need(read_string(data, cursor, max_length=4096), field + ".id")
    return {"memberCount": 2, "count": count, "id": item_id}, cursor


def _predefined_component(
    data: bytes, offset: int, field: str, component: str,
) -> tuple[dict[str, Any], int]:
    values: dict[str, Any]
    cursor = offset
    if component == "cache":
        value, cursor = _need(read_bool(data, cursor), field + ".lockManualInOut")
        values = {"memberCount": 1, "lockManualInOut": value}
    elif component == "common":
        values = {"memberCount": 9}
        for name in (
            "disable", "forbidDelete", "forbidMove", "initialDoNotPlace",
            "initialHide", "isSocialBuilding", "needRepair",
        ):
            values[name], cursor = _need(read_bool(data, cursor), f"{field}.{name}")
        values["repairNeedItem"], cursor = _object_list(
            data, cursor, field + ".repairNeedItem", 2, _item_bundle
        )

        def social_body(raw: bytes, at: int, nested: str) -> tuple[dict[str, Any], int]:
            like, at = _need(read_i32(raw, at), nested + ".like")
            owner_id, at = _need(read_i32(raw, at), nested + ".ownerId")
            return {"memberCount": 2, "like": like, "ownerId": owner_id}, at

        values["socialBuildingConfig"], cursor = _nullable_object(
            data, cursor, field + ".socialBuildingConfig", 2, social_body
        )
    elif component == "envGenWithActivator":
        value, cursor = _need(read_string(data, cursor, max_length=4096), field + ".lockEnvFromItemId")
        values = {"memberCount": 1, "lockEnvFromItemId": value}
    elif component == "fluidContainer":
        infinite, cursor = _need(read_bool(data, cursor), field + ".itemInfinite")
        locked, cursor = _need(read_bool(data, cursor), field + ".lockManualInout")
        bundle, cursor = _nullable_object(
            data, cursor, field + ".prePlacedItem", 2, _item_bundle
        )
        values = {"memberCount": 3, "itemInfinite": infinite,
                  "lockManualInout": locked, "prePlacedItem": bundle}
    elif component == "fluidReaction":
        unlock, cursor = _need(read_bool(data, cursor), field + ".preFinalCacheUnlock")
        formulas, cursor = _string_list(data, cursor, field + ".visibleFormulas")
        values = {"memberCount": 2, "preFinalCacheUnlock": unlock,
                  "visibleFormulas": formulas}
    elif component == "gridBox":
        content, cursor = _object_list(data, cursor, field + ".content", 2, _item_bundle)
        default, cursor = _need(read_bool(data, cursor), field + ".defaultStorageMode")
        transfer, cursor = _need(read_bool(data, cursor), field + ".enableAutoTransfer")
        locked, cursor = _need(read_bool(data, cursor), field + ".lockManualInOut")
        values = {"memberCount": 4, "content": content, "defaultStorageMode": default,
                  "enableAutoTransfer": transfer, "lockManualInOut": locked}
    elif component == "hub":
        generate, cursor = _need(read_i32(data, cursor), field + ".powerGenerate")
        saved, cursor = _need(read_i32(data, cursor), field + ".powerSaveAmount")

        def selector_port(raw: bytes, at: int, nested: str) -> tuple[dict[str, Any], int]:
            item_id, at = _need(read_string(raw, at, max_length=4096), nested + ".currentSelectedItemId")
            index, at = _need(read_i32(raw, at), nested + ".index")
            locked, at = _need(read_bool(raw, at), nested + ".lockSelectedItemId")
            return {"memberCount": 3, "currentSelectedItemId": item_id,
                    "index": index, "lockSelectedItemId": locked}, at

        selectors, cursor = _object_list(data, cursor, field + ".selectors", 3, selector_port)
        values = {"memberCount": 3, "powerGenerate": generate,
                  "powerSaveAmount": saved, "selectors": selectors}
    elif component == "miner":
        items, cursor = _string_list(data, cursor, field + ".forbiddenMineItems")
        values = {"memberCount": 1, "forbiddenMineItems": items}
    elif component == "powerDiffuser":
        value, cursor = _need(read_bool(data, cursor), field + ".disablePowerPole")
        values = {"memberCount": 1, "disablePowerPole": value}
    elif component == "powerGate":
        inst, cursor = _need(read_string(data, cursor, max_length=4096), field + ".toInstKey")
        scene, cursor = _need(read_string(data, cursor, max_length=4096), field + ".toScene")
        values = {"memberCount": 2, "toInstKey": inst, "toScene": scene}
    elif component == "powerPole":
        value, cursor = _need(read_bool(data, cursor), field + ".disablePowerDiffuser")
        values = {"memberCount": 1, "disablePowerDiffuser": value}
    elif component == "powerPort":
        value, cursor = _need(read_u64(data, cursor), field + ".target")
        values = {"memberCount": 1, "target": str(value)}
    elif component == "producer":
        values = {"memberCount": 8}
        values["enableModeSwitch"], cursor = _need(read_bool(data, cursor), field + ".enableModeSwitch")
        values["forbidLiquidMode"], cursor = _need(read_bool(data, cursor), field + ".forbidLiquidMode")
        values["limitedFormulaIds"], cursor = _string_list(data, cursor, field + ".limitedFormulaIds")
        for name in ("lockFormulaId", "modeCustom0", "modeCustom1"):
            values[name], cursor = _need(read_string(data, cursor, max_length=4096), f"{field}.{name}")
        values["modeUseCustom"], cursor = _need(read_bool(data, cursor), field + ".modeUseCustom")
        values["useMode"], cursor = _need(read_string(data, cursor, max_length=4096), field + ".useMode")
    elif component == "selector":
        item_id, cursor = _need(read_string(data, cursor, max_length=4096), field + ".currentSelectedItemId")
        locked, cursor = _need(read_bool(data, cursor), field + ".lockSelectedItemId")
        values = {"memberCount": 2, "currentSelectedItemId": item_id,
                  "lockSelectedItemId": locked}
    elif component in ("sewageTreatPlantExport", "sewageTreatPlantImport"):
        group_id, cursor = _need(read_string(data, cursor, max_length=4096), field + ".groupId")
        values = {"memberCount": 1, "groupId": group_id}
    elif component == "sign":
        contents, cursor = _i32_list(data, cursor, field + ".contents")
        values = {"memberCount": 1, "contents": contents}
    elif component == "travelPole":
        locked, cursor = _need(read_bool(data, cursor), field + ".lockAutoTravelTargetSetting")
        next_key, cursor = _need(read_string(data, cursor, max_length=4096), field + ".nextInstKey")
        values = {"memberCount": 2, "lockAutoTravelTargetSetting": locked,
                  "nextInstKey": next_key}
    elif component == "udPipe":
        node, cursor = _need(read_string(data, cursor, max_length=4096), field + ".connUdPipeNode")
        container, cursor = _nullable_object(
            data, cursor, field + ".container", 3,
            lambda d, o, f: _predefined_component(d, o, f, "fluidContainer"),
        )
        values = {"memberCount": 2, "connUdPipeNode": node, "container": container}
    elif component == "valve":
        values = {"memberCount": 12}
        for name in (
            "enableItemPass", "isItemCountLocked", "isItemLimited", "isItemLocked",
            "isItemPassLocked", "isSpeedLimited", "isSpeedLimitedLocked",
            "isSpeedLimitedTechUnlock",
        ):
            values[name], cursor = _need(read_bool(data, cursor), f"{field}.{name}")
        values["itemCount"], cursor = _need(read_i32(data, cursor), field + ".itemCount")
        values["limitSpeed"], cursor = _need(read_i32(data, cursor), field + ".limitSpeed")
        values["limitSpeedLocked"], cursor = _need(read_bool(data, cursor), field + ".limitSpeedLocked")
        values["passItemId"], cursor = _need(read_string(data, cursor, max_length=4096), field + ".passItemId")
    else:
        raise LevelDataBlackboxCodecError(f"{field}:unknown-component={component}")
    return values, cursor


_PREDEFINED_COMPONENTS: tuple[tuple[str, int], ...] = (
    ("cache", 1), ("common", 9), ("envGenWithActivator", 1),
    ("fluidContainer", 3), ("fluidReaction", 2), ("gridBox", 4),
    ("hub", 3), ("miner", 1), ("powerDiffuser", 1), ("powerGate", 2),
    ("powerPole", 1), ("powerPort", 1), ("producer", 8), ("selector", 2),
    ("sewageTreatPlantExport", 1), ("sewageTreatPlantImport", 1), ("sign", 1),
    ("travelPole", 2), ("udPipe", 2), ("valve", 12),
)


def decode_predefined_param_at(
    data: bytes, offset: int, field: str = "predefinedParam",
) -> tuple[dict[str, Any], int]:
    """Decode the generated 20-member ``PredefinedParam`` wrapper."""
    values: dict[str, Any] = {"memberCount": 20}
    cursor = offset
    for component, member_count in _PREDEFINED_COMPONENTS:
        values[component], cursor = _nullable_object(
            data, cursor, f"{field}.{component}", member_count,
            lambda d, o, f, name=component: _predefined_component(d, o, f, name),
        )
    return values, cursor


def _predefined_template(data: bytes, offset: int, field: str) -> tuple[dict[str, Any], int]:
    param, cursor = _nullable_object(
        data, offset, field + ".predefinedParam", 20, decode_predefined_param_at
    )
    template_id, cursor = _need(
        read_string(data, cursor, max_length=4096), field + ".templateId"
    )
    return {"memberCount": 2, "predefinedParam": param, "templateId": template_id}, cursor


def decode_leveldata_blackbox(data: bytes, offset: int) -> tuple[dict[str, Any], int]:
    """Decode the current 15-member wrapper or raise at the exact bad member."""
    start = offset
    cursor = _marker(data, offset, "blackbox", 15)
    fields: dict[str, Any] = {}
    fields["basic"], cursor = _nullable_object(data, cursor, "blackbox.basic", 13, _basic)
    for name, attr in (
        ("buildingCraft", "limitedBuildingCraftIds"),
    ):
        fields[name], cursor = _nullable_object(
            data, cursor, f"blackbox.{name}", 1,
            lambda d, o, f, a=attr: _one_string_list(d, o, f, a),
        )
    fields["completeCondition"], cursor = _nullable_object(
        data, cursor, "blackbox.completeCondition", 4, _complete
    )
    fields["discardItem"], cursor = _nullable_object(
        data, cursor, "blackbox.discardItem", 2, _discard
    )
    fields["equipCraft"], cursor = _nullable_object(
        data, cursor, "blackbox.equipCraft", 1,
        lambda d, o, f: _one_string_list(d, o, f, "limitedEquipCraftIds"),
    )
    fields["extraTask"], cursor = _object_list(data, cursor, "blackbox.extraTask", 2, _task)
    fields["failTask"], cursor = _object_list(
        data, cursor, "blackbox.failTask", 3, _fail_task
    )
    fields["generalAbility"], cursor = _nullable_object(
        data, cursor, "blackbox.generalAbility", 1, _general_ability
    )
    fields["introEffect"], cursor = _nullable_object(
        data, cursor, "blackbox.introEffect", 4, _intro
    )
    fields["inventory"], cursor = _nullable_object(
        data, cursor, "blackbox.inventory", 4, _inventory
    )
    fields["mainTask"], cursor = _object_list(data, cursor, "blackbox.mainTask", 2, _task)
    fields["manualCraft"], cursor = _nullable_object(
        data, cursor, "blackbox.manualCraft", 1,
        lambda d, o, f: _one_string_list(d, o, f, "limitedManualCraftIds"),
    )
    fields["predefinedTemplates"], cursor = _object_list(
        data, cursor, "blackbox.predefinedTemplates", 2, _predefined_template
    )
    fields["presetBluePrints"], cursor = _nullable_object(
        data, cursor, "blackbox.presetBluePrints", 1,
        lambda d, o, f: _one_string_list(d, o, f, "presetBpKey"),
    )
    fields["statistics"], cursor = _nullable_object(
        data, cursor, "blackbox.statistics", 1,
        lambda d, o, f: _one_string_list(d, o, f, "limitedStatisticItemIds"),
    )
    return {"startOffset": start, "endOffset": cursor, "memberCount": 15,
            "fields": fields}, cursor
