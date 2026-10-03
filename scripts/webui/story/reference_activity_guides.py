"""Readable, source-preserving guides for authored achievement/activity rows.

These projections describe stored targets and rewards, never current player
progress, server availability, or inferred condition semantics. Nested record
boundaries and their source paths survive the projection. References are exact
lookups through the same resolver as the Text page's structured fields.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from scripts.webui.story.reference_structured_fields import (
    MISSION_SOURCE,
    ReferenceResolver,
    quest_mission_id,
    table_stem,
)


GUIDE_TABLES = frozenset({
    "AchievementTable", "AchievementTypeTable", "AchievementStatisticTable",
    "ActivityTable", "ActivityAchievementDataTable",
    "ActivityConditionalMultiStageTable", "ActivityConditionalMultiStageStageToActivityTable",
    "ActivityConditionalMultiStageConditionTable", "ActivityConditionalMultiStageCompleteConditionTable",
    "ActivityConditionalMultiStageTaskConfigTable", "ActivityConditionalMultiStageTaskCompleteConditionTable",
    "ActivityConditionalMultiStageMilestoneTable", "ActivityLevelRewardsTable",
    "ActivityWeeklyTaskTable", "ActivityWeeklyTaskMileStoneTable",
    "ActivityGameEntranceSeriesTable", "ActivityGameEntranceSeriesAchieveTable",
    "ActivityGameEntranceGameTable", "ActivityDungeonTable", "RewardTable", "TimeRangeTable",
})


@dataclass
class ActivityGuideResolver:
    references: ReferenceResolver
    row_data: Callable[[str, str], Any]
    text: Callable[[Any], str]


def _value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, list):
        return ", ".join(_value(item) for item in value)
    return "" if value is None else str(value)


def _records(value: Any):
    if isinstance(value, dict):
        return ((str(key), record) for key, record in value.items() if isinstance(record, dict))
    if isinstance(value, list):
        return ((str(index), record) for index, record in enumerate(value) if isinstance(record, dict))
    return ()


def activity_reference_guide(
    table_name: str, row_key: str, row: Any, resolver: ActivityGuideResolver,
) -> dict[str, Any] | None:
    """Project one supported row; return None for generic/empty row shapes."""
    stem = table_stem(table_name)
    if stem not in GUIDE_TABLES or not isinstance(row, dict):
        return None
    sections: list[dict[str, Any]] = []

    def section(label: str, label_zh: str, path: str = "", title: str = "") -> list[dict]:
        fields: list[dict] = []
        sections.append({"label": label, "labelZh": label_zh, "path": path, "title": title, "fields": fields})
        return fields

    def add(fields: list[dict], field: str, label: str, zh: str, value: Any,
            table: str = "", *, row_id: str = "", technical: bool = False):
        if value in (None, "", [], {}):
            return
        entry = {"field": field, "label": label, "labelZh": zh, "value": _value(value)}
        if technical:
            entry["technical"] = True
        if table:
            key = row_id or _value(value)
            resolved, name = resolver.references.resolve(table, key)
            entry.update(ref={"table": table, "row": key}, resolved=resolved)
            if name:
                entry["name"] = name
        fields.append(entry)

    def text(fields: list[dict], field: str, label: str, zh: str, value: Any):
        add(fields, field, label, zh, resolver.text(value))

    def conditions(value: Any, path: str, label: str, zh: str):
        for key, condition in _records(value):
            base = f"{path}.{key}"
            fields = section(label, zh, base, resolver.text(condition.get("desc")))
            add(fields, f"{base}.conditionId", "Condition", "条件", condition.get("conditionId"), technical=True)
            add(fields, f"{base}.progressToCompare", "Target", "目标值", condition.get("progressToCompare"))
            text(fields, f"{base}.tips", "Hint", "提示", condition.get("tips"))
            add(fields, f"{base}.jumpId", "Go to", "跳转目标", condition.get("jumpId"), "SystemJumpTable")
            for name, title, title_zh in (
                ("conditionType", "Condition type code", "条件类型代码"),
                ("compareOperator", "Comparison code", "比较方式代码"),
            ):
                add(fields, f"{base}.{name}", title, title_zh, condition.get(name), technical=True)
            # Typed parameter views are stored representations, not decoded
            # predicates. Do not turn a string into a mission/stage ownership.
            for index, parameter in _records(condition.get("parameters")):
                for name in ("valueStringList", "valueIntList", "valueFloatList", "valueBoolList"):
                    number = str(int(index) + 1) if index.isdigit() else index
                    add(fields, f"{base}.parameters.{index}.{name}", f"Parameter {number} · {name}",
                        f"参数 {number} · {name}", parameter.get(name), technical=True)

    def reward(fields: list[dict], path: str, reward_id: Any):
        if not isinstance(reward_id, str) or not reward_id:
            return
        add(fields, path, "Reward", "奖励", reward_id, "RewardTable")
        if resolver.references.resolve("RewardTable", reward_id)[0]:
            record = resolver.row_data("RewardTable", reward_id)
            if isinstance(record, dict):
                reward_items(fields, record, f"RewardTable/{reward_id}")

    def reward_items(fields: list[dict], record: dict, path: str):
        prefix = f"{path}." if path else ""
        for key, bundle in _records(record.get("itemBundles")):
            before = len(fields)
            add(fields, f"{prefix}itemBundles.{key}.id", "Fixed reward item", "固定奖励物品", bundle.get("id"), "ItemTable")
            if len(fields) > before and "count" in bundle:
                fields[-1]["quantity"] = bundle["count"]
        random_bundles = record.get("probItemBundles")
        if isinstance(random_bundles, list) and random_bundles:
            add(fields, f"{prefix}probItemBundles", "Random reward entries (not guaranteed)", "随机奖励条目（不保证获得）", len(random_bundles))

    def common(fields: list[dict], record: dict, path: str = ""):
        prefix = f"{path}." if path else ""
        for name, label, zh, target in (
            ("activityId", "Activity", "活动", "ActivityTable"),
            ("achieveId", "Achievement", "成就", "AchievementTable"),
            ("achievementId", "Achievement", "成就", "AchievementTable"),
            ("missionId", "Mission", "任务", MISSION_SOURCE),
            ("timeId", "Configured time range", "配置时间范围", "TimeRangeTable"),
            ("unlockTimeId", "Configured unlock time", "配置解锁时间", "TimeRangeTable"),
            ("displayTimeId", "Configured display time", "配置展示时间", "TimeRangeTable"),
            ("jumpId", "Go to", "跳转目标", "SystemJumpTable"),
            ("gameId", "Dungeon", "关卡", "DungeonTable"),
        ):
            add(fields, prefix + name, label, zh, record.get(name), target)
        for name, label, zh in (
            ("score", "Score", "分数"), ("progressToCompare", "Target", "目标值"),
            ("displayFactor", "Display factor", "展示倍率"),
            ("sortId", "Display order", "显示顺序"), ("timeOffset", "Stored time offset", "配置时间偏移"),
        ):
            add(fields, prefix + name, label, zh, record.get(name))
        reward(fields, prefix + "rewardId", record.get("rewardId"))

    if stem == "AchievementTable":
        fields = section("Achievement", "成就")
        text(fields, "desc", "Description", "说明", row.get("desc"))
        for name, label, zh in (
            ("groupId", "Group", "分组"), ("initLevel", "Initial tier", "初始等级"),
            ("canBeUpgraded", "Supports tier upgrades", "支持升级"),
            ("canBePlated", "Supports plating", "支持镀层"),
        ):
            add(fields, name, label, zh, row.get(name))
        common(fields, row)
        for key, level in _records(row.get("levelInfos")):
            path = f"levelInfos.{key}"
            fields = section("Achievement tier", "成就等级", path)
            add(fields, f"{path}.achieveLevel", "Tier", "等级", level.get("achieveLevel", key))
            text(fields, f"{path}.completeDesc", "Completion description", "完成说明", level.get("completeDesc"))
            conditions(level.get("conditions"), f"{path}.conditions", "Tier requirement", "等级要求")
        conditions(row.get("plateConditions"), "plateConditions", "Plating requirement", "镀层要求")
    elif stem == "AchievementTypeTable":
        fields = section("Achievement category", "成就类别")
        text(fields, "categoryName", "Category", "类别", row.get("categoryName"))
        add(fields, "noObtainCanView", "Visible before obtaining", "获得前可见", row.get("noObtainCanView"))
        for key, group in _records(row.get("achievementGroupData")):
            fields = section("Achievement group", "成就分组", f"achievementGroupData.{key}", resolver.text(group.get("groupName")))
            add(fields, f"achievementGroupData.{key}.groupId", "Group", "分组", group.get("groupId"))
    elif stem == "AchievementStatisticTable":
        fields = section("Achievement statistics", "成就统计")
        add(fields, "maxStatVal", "Maximum statistic value", "统计值上限", row.get("maxStatVal"))
        for key, item in _records(row.get("achieveList")):
            fields = section("Achievement contribution", "成就计数", f"achieveList.{key}")
            common(fields, item, f"achieveList.{key}")
            add(fields, f"achieveList.{key}.statVal", "Statistic value", "统计值", item.get("statVal"))
    elif stem == "ActivityTable":
        fields = section("Activity configuration", "活动配置")
        text(fields, "desc", "Description", "说明", row.get("desc"))
        common(fields, row)
        for target, label, zh in (
            ("ActivityConditionalMultiStageTable", "Activity stages", "活动阶段"),
            ("ActivityDungeonTable", "Activity dungeons", "活动关卡"),
        ):
            record = resolver.row_data(target, row_key)
            if isinstance(record, dict) and record.get("activityId") == row.get("id") == row_key:
                add(fields, "id", label, zh, row_key, target)
        for name, label, zh in (
            ("introMissionQuestId", "Introduction quest", "引导任务"),
            ("endMissionQuestId", "Ending quest", "结束任务"),
        ):
            value = row.get(name)
            add(fields, name, label, zh, value, MISSION_SOURCE, row_id=quest_mission_id(value or ""))
        conditions(row.get("conditions"), "conditions", "Activity prerequisite", "活动前置条件")
    elif stem in {"ActivityConditionalMultiStageConditionTable", "ActivityConditionalMultiStageCompleteConditionTable"}:
        conditions(row.get("conditionList"), "conditionList", "Stage condition", "阶段条件")
    elif stem == "ActivityConditionalMultiStageTaskCompleteConditionTable":
        conditions([row], "$row", "Task completion condition", "任务完成条件")
    elif stem in {"ActivityConditionalMultiStageTable", "ActivityLevelRewardsTable"}:
        fields = section("Activity", "活动")
        common(fields, row)
        for key, stage in _records(row.get("stageList")):
            path = f"stageList.{key}"
            fields = section("Activity stage", "活动阶段", path, resolver.text(stage.get("name")))
            add(fields, f"{path}.stageId", "Stage", "阶段", stage.get("stageStrId") or stage.get("stageId", key))
            text(fields, f"{path}.desc", "Description", "说明", stage.get("desc"))
            common(fields, stage, path)
            conditions(stage.get("conditions"), f"{path}.conditions", "Stage prerequisite", "阶段前置条件")
            # These side tables are explicitly keyed by their stageId. Show
            # only an exact existing row with a matching stored stageId.
            for target, label, zh in (
                ("ActivityConditionalMultiStageConditionTable", "Stage prerequisites", "阶段前置条件"),
                ("ActivityConditionalMultiStageCompleteConditionTable", "Stage completion requirements", "阶段完成要求"),
            ):
                stage_id = stage.get("stageId")
                condition_row = resolver.row_data(target, str(stage_id or ""))
                entries = condition_row.get("conditionList", []) if isinstance(condition_row, dict) else []
                if entries and all(isinstance(entry, dict) and entry.get("stageId") == stage_id for entry in entries):
                    add(fields, f"{path}.stageId", label, zh, stage_id, target)
    elif stem == "ActivityConditionalMultiStageTaskConfigTable":
        for key, task in _records(row.get("TaskConfigMap")):
            path = f"TaskConfigMap.{key}"
            fields = section("Activity task", "活动任务", path, resolver.text(task.get("desc")))
            add(fields, f"{path}.taskId", "Task", "任务", task.get("taskId", key))
            common(fields, task, path)
            for name, label, zh in (
                ("completeConditionId", "Completion condition", "完成条件"),
                ("unlockConditionId", "Unlock condition ID (unresolved target)", "解锁条件 ID（未解析目标）"),
            ):
                target = "ActivityConditionalMultiStageTaskCompleteConditionTable" if name == "completeConditionId" else ""
                for value in task.get(name) or []:
                    add(fields, f"{path}.{name}", label, zh, value, target)
    elif stem in {"ActivityConditionalMultiStageMilestoneTable", "ActivityWeeklyTaskMileStoneTable"}:
        for key, milestone in _records(row.get("mileStones")):
            path = f"mileStones.{key}"
            fields = section("Reward milestone", "奖励里程碑", path)
            add(fields, f"{path}.milestoneId", "Milestone", "里程碑", milestone.get("milestoneId", key))
            common(fields, milestone, path)
    elif stem == "ActivityGameEntranceSeriesTable":
        for key, series in _records(row.get("seriesMap")):
            path = f"seriesMap.{key}"
            fields = section("Activity series", "活动系列", path, resolver.text(series.get("name")))
            add(fields, path, "Series games", "系列关卡", key, "ActivityGameEntranceGameTable")
            common(fields, series, path)
    elif stem in {"ActivityGameEntranceGameTable", "ActivityDungeonTable"}:
        name = "gameList" if stem == "ActivityGameEntranceGameTable" else "gameMap"
        for key, game in _records(row.get(name)):
            path = f"{name}.{key}"
            fields = section("Activity dungeon", "活动关卡", path)
            common(fields, game, path)
            for field, label, zh in (
                ("gameUnlockStage", "Unlock stage", "解锁阶段"),
                ("gameCloseStage", "Closing stage", "关闭阶段"),
            ):
                add(fields, f"{path}.{field}", label, zh, game.get(field), "ActivityConditionalMultiStageStageToActivityTable")
    elif stem == "RewardTable":
        fields = section("Reward breakdown", "奖励明细")
        reward_items(fields, row, "")
    elif stem == "TimeRangeTable":
        for key, time_range in _records(row.get("timeRangeList")):
            path = f"timeRangeList.{key}"
            fields = section("Authored time range", "配置时间范围", path)
            for name, label, zh in (("openTime", "Opening time", "开始时间"), ("closeTime", "Closing time", "结束时间")):
                add(fields, f"{path}.{name}", label, zh, time_range.get(name))
    else:
        fields = section("Activity configuration", "活动配置")
        text(fields, "desc", "Description", "说明", row.get("desc"))
        common(fields, row)
    sections = [entry for entry in sections if entry["fields"] or entry["title"]]
    if not sections:
        return None
    kind = "achievement" if stem.startswith("Achievement") else "reward" if stem == "RewardTable" else "activity"
    return {"kind": kind, "evidenceBoundary": "storedConfiguration", "sections": sections}
