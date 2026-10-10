"""Project authored mission completion rewards for the Story summary."""

from __future__ import annotations

from collections.abc import Callable

from scripts.webui.game_tables import iter_reward_bundles


def mission_completion_reward_search_text(reward: dict | None) -> str:
    """Index configured reward names and IDs without loading mission details."""
    if not reward:
        return ""
    parts = [reward.get("rewardId")]
    for item in reward.get("items") or []:
        parts.extend((item.get("id"), item.get("name")))
    return "\n".join(str(part) for part in parts if part)


def project_mission_completion_reward(
    mission_id: str,
    flow: dict | None,
    rewards: dict,
    items: dict,
    *,
    translate: Callable[[object], str],
    source_file: str,
) -> dict | None:
    """Use only the mission-level rewardId, never quest rewards or name guesses."""
    reward_id = (flow or {}).get("rewardId")
    if not isinstance(reward_id, str) or not reward_id:
        return None
    reward = rewards.get(reward_id)
    result = {
        "rewardId": reward_id,
        "status": "resolved" if isinstance(reward, dict) else "missing",
        "items": [],
        "hasRandomRewards": False,
        "_debug": {
            "source": {
                "file": source_file,
                "missionId": mission_id,
                "field": "rewardId",
                "value": reward_id,
            },
            "reward": {"table": "RewardTable", "rowId": reward_id},
        },
    }
    if not isinstance(reward, dict):
        return result
    result["hasRandomRewards"] = bool(reward.get("probItemBundles"))
    for index, bundle, item_id in iter_reward_bundles(reward):
        item = items.get(item_id) or {}
        name = item.get("name") or {}
        label = (translate(name.get("id")) or name.get("text")) if isinstance(name, dict) else ""
        entry = {
            "id": item_id,
            "name": label or item_id,
            "_debug": {
                "table": "RewardTable",
                "rowId": reward_id,
                "field": f"itemBundles[{index}]",
                "source": bundle,
                "item": {"table": "ItemTable", "rowId": item_id, "name": name},
            },
        }
        count = bundle.get("count")
        if isinstance(count, (int, float)) and not isinstance(count, bool):
            entry["count"] = count
        icon_id = item.get("iconId")
        if isinstance(icon_id, str) and icon_id:
            entry["iconId"] = icon_id
            entry["_debug"]["item"]["iconId"] = icon_id
        result["items"].append(entry)
    return result
