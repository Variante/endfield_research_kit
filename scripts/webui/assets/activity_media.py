"""Compact exact activity image references over the Assets scan.

Only authored asset fields, instructionId and RewardTable itemBundles joins
are followed. Names and ID prefixes never establish activity ownership.
"""
from __future__ import annotations

from pathlib import Path

from scripts.common import read_json
from scripts.webui.game_tables import is_activity_browse_table, iter_reward_bundles
from scripts.webui.assets.table_asset_owners import (
    is_asset_bearing_field, iter_string_leaves, normalized_asset_stem,
)


def build_activity_media_payload(entries: list[dict], table_dir: Path) -> dict:
    images: dict[str, list[dict]] = {}
    for entry in entries:
        if entry.get("k") == "image":
            images.setdefault(normalized_asset_stem(entry["r"]), []).append(entry)

    def read(stem: str) -> dict:
        payload = read_json(table_dir / f"{stem}.json", {})
        return payload if isinstance(payload, dict) else {}

    rewards, items, instructions = read("RewardTable"), read("ItemTable"), read("InstructionBook")
    rows = {}
    # Only the tables the Activities page browses; see is_activity_browse_table.
    paths = sorted(path for path in table_dir.glob("*.json") if is_activity_browse_table(path.stem))
    for path in paths:
        for row_id, row in read(path.stem).items():
            if not isinstance(row, dict):
                continue
            sources = [(path.stem, str(row_id), row)]
            instruction = row.get("instructionId")
            if isinstance(instruction, str) and isinstance(instructions.get(instruction), dict):
                sources.append(("InstructionBook", instruction, instructions[instruction]))
            # Reward references may be nested in stage/task records.
            for field, value in iter_string_leaves(row):
                if field.split(".")[-1].lower().endswith("rewardid") and value in rewards:
                    for _index, _bundle, item_id in iter_reward_bundles(rewards[value]):
                        if isinstance(items.get(item_id), dict):
                            sources.append(("ItemTable", item_id, items[item_id]))
            refs, seen = [], set()
            for table, source_row, source in sources:
                for field, token in iter_string_leaves(source):
                    if not is_asset_bearing_field(field):
                        continue
                    candidates = images.get(token, [])
                    # Sprite and Texture2D duplicates show the Sprite crop once;
                    # distinct Sprite identities remain separate alternatives.
                    sprites = [entry for entry in candidates if "/Sprite/" in entry["r"]]
                    for entry in sprites or candidates:
                        key = (table, source_row, field, entry["r"])
                        if key in seen:
                            continue
                        seen.add(key)
                        refs.append({"token": token, "rel": entry["r"], "table": table,
                                     "row": source_row, "field": field,
                                     "width": entry.get("iw"), "height": entry.get("ih")})
            if refs:
                rows[f"{path.stem}/{row_id}"] = refs
    return {"schema": "activity-media.v1", "evidenceBoundary": "direct",
            "evidence": "Exact authored asset field; instructionId or fixed reward item join",
            "rows": rows}
