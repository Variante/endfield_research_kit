"""Shared table-name and table-join rules for exported ``game/Table`` rows.

Several pages project the same authored tables. The rules here are the single
place that decides which tables count as activity tables and how a RewardTable
row's fixed ``itemBundles`` reach ItemTable, so the Assets, Story and Updates
builders cannot drift apart. Both rules are name/field based over authored
rows; they establish no ownership beyond the exact table name or ``id`` join.
"""
from __future__ import annotations

from collections.abc import Iterator


def is_activity_table(stem: str) -> bool:
    """Return whether a ``game/Table`` stem belongs to the Activities page.

    Every ``Activity``-prefixed table plus ``CheckInRewardTable``, compared
    case-insensitively on the stem (no ``.json`` suffix).
    """
    lower = stem.lower()
    return lower.startswith("activity") or lower == "checkinrewardtable"


def is_activity_browse_table(stem: str) -> bool:
    """Return whether the Activities page browses this table's rows.

    The narrower set on top of :func:`is_activity_table`: ``Activity*Table``
    stems plus ``CheckInRewardTable``. Supporting Activity tables without the
    ``Table`` suffix (constants, id maps, state enums) still count as activity
    data for Updates but are not row-browsed, so no media is projected for them.
    """
    return is_activity_table(stem) and (stem.endswith("Table") or stem.lower() == "checkinrewardtable")


def iter_reward_bundles(reward: object) -> Iterator[tuple[int, dict, str]]:
    """Yield ``(index, bundle, item_id)`` for a RewardTable row's fixed bundles.

    Only ``itemBundles`` are followed (``probItemBundles`` are random and stay
    with the caller). Bundles that are not objects or carry no ``id`` are
    skipped; ``index`` is the bundle's position in the authored list.
    """
    if not isinstance(reward, dict):
        return
    bundles = reward.get("itemBundles")
    if not isinstance(bundles, list):
        return
    for index, bundle in enumerate(bundles):
        if isinstance(bundle, dict) and bundle.get("id"):
            yield index, bundle, str(bundle["id"])
