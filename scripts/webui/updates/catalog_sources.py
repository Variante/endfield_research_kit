"""Bounded authored sources for the Combat stages and Activities catalogs."""
from __future__ import annotations

from scripts.webui.gameplay.battle_stages import COMBAT_CATEGORIES, REWARD_FIELDS
from scripts.webui.gameplay.battle_activities import activity_links
from scripts.webui.story.reference_activity_guides import (
    ActivityGuideResolver, GUIDE_TABLES, activity_reference_guide,
)
from scripts.webui.story.reference_structured_fields import ReferenceResolver


class Sources:
    def __init__(self, tables):
        self.tables = tables
        self.rows = {}

    def add(self, table, key, fields=None):
        key = str(key or '')
        row = self.tables.get(table, {}).get(key)
        if isinstance(row, dict):
            source = f'{table}/{key}'
            self.rows[source] = row if fields is None else {
                **self.rows.get(source, {}), **{field: row[field] for field in fields if field in row}}
        return row if isinstance(row, dict) else {}

    def reward(self, key):
        row = self.add('RewardTable', key)
        for bundle in row.get('itemBundles') or []:
            self.add('ItemTable', bundle.get('id'), ('name', 'iconId', 'rarity'))


def stage_source_records(tables):
    records = {}
    activities = activity_links(tables, lambda _: '')
    for key, row in tables.get('DungeonTable', {}).items():
        if not isinstance(row, dict) or row.get('dungeonCategory') not in COMBAT_CATEGORIES:
            continue
        sources = Sources(tables)
        sources.add('DungeonTable', key)
        sources.add('DungeonSeriesTable', row.get('dungeonSeriesId'), ('name', 'desc', 'sortId'))
        sources.add('DungeonTypeTable', row.get('dungeonCategory'), ('enemyInfoTitle',))
        raid = sources.add('DungeonRaidTable', key)
        if raid.get('RelatedLevel') != key:
            sources.add('DungeonTable', raid.get('RelatedLevel'), ('dungeonName',))
        sources.add('SeasonTowerDungeonTable', key, ('specialBuffDesc',))
        for field in REWARD_FIELDS:
            sources.reward(row.get(field))
        for enemy_id in row.get('enemyIds') or []:
            enemy = sources.add('EnemyTable', enemy_id, ('templateId', 'attrModifiers', 'bornBuffs'))
            sources.add('EnemyDisplayInfoTable', enemy_id, ('name',))
            sources.add('EnemyTemplateDisplayInfoTable', enemy.get('templateId'), ('name',))
        for activity in activities.get(key, []):
            sources.add('ActivityTable', activity['id'], ('name',))
            receipt = activity['source']
            table, identity = receipt['table'], receipt['row']
            raw = tables[table][identity]
            path = receipt['field'].split('.')
            # Keep only this dungeon's slot in multi-game activity records.
            # Sparse list positions preserve the original source field paths.
            if len(path) >= 3:
                container, slot = path[:2]
                value = raw[container]
                if isinstance(value, list):
                    selected = [None] * (int(slot) + 1)
                    selected[int(slot)] = value[int(slot)]
                else:
                    selected = {slot: value[slot]}
                source = f'{table}/{identity}'
                previous = sources.rows.get(source, {}).get(container)
                if isinstance(previous, dict):
                    selected = {**previous, **selected}
                elif isinstance(previous, list):
                    selected += [None] * max(0, len(previous) - len(selected))
                    selected = [item if item is not None else previous[i] if i < len(previous) else None
                                for i, item in enumerate(selected)]
                sources.rows[source] = {container: selected}
            else:
                sources.add(table, identity, ('activityId', 'dungeonId'))
        records[f'stage:{key}'] = sources.rows
    return records


ACTIVITY_RELATED_TABLES = (
    'CheckInRewardTable', 'ActivityConditionalMultiStageTable',
    'ActivityConditionalMultiStageTaskConfigTable', 'ActivityConditionalMultiStageMilestoneTable',
    'ActivityWeeklyTaskMileStoneTable',
)


def activity_source_records(tables):
    """Follow the same guide references and related-reward slots as Activities.

    Item, dungeon and parent-activity links are terminal labels, so a condition
    string or reward item can never import another activity's configuration.
    """
    records = {}
    for key, row in tables.get('ActivityTable', {}).items():
        if not isinstance(row, dict):
            continue
        sources = Sources(tables)
        sources.add('ActivityTable', key)
        pending = [('ActivityTable', key)]
        for table in ACTIVITY_RELATED_TABLES:
            related = tables.get(table, {}).get(key)
            if not isinstance(related, dict):
                continue
            if table == 'CheckInRewardTable':
                days = related.get('stageList') or []
                if not days or not all(isinstance(day, dict) and day.get('activityId') == key for day in days):
                    continue
            if table == 'ActivityConditionalMultiStageTable' and related.get('activityId') != key:
                continue
            pending.append((table, key))
        for tag in row.get('tagIds') or []:
            sources.add('ActivityTagTable', tag, ('name',))
        seen = set()
        resolver = ActivityGuideResolver(
            ReferenceResolver(lambda table, identity: identity in tables.get(table, {})),
            lambda table, identity: tables.get(table, {}).get(identity),
            lambda value: str(value.get('id') or value.get('text') or '') if isinstance(value, dict) else str(value or ''))
        while pending:
            table, identity = pending.pop()
            if (table, identity) in seen:
                continue
            seen.add((table, identity))
            owned = sources.add(table, identity)
            guide = activity_reference_guide(table, identity, owned, resolver) or {}
            for section in guide.get('sections', []):
                for field in section['fields']:
                    ref = field.get('ref') or {}
                    target, target_id = ref.get('table'), ref.get('row')
                    if target == 'RewardTable':
                        sources.reward(target_id)
                    elif target in GUIDE_TABLES and target != 'ActivityTable':
                        pending.append((target, target_id))
                    elif target in {'ActivityTable', 'ItemTable', 'DungeonTable', 'SystemJumpTable',
                                    'CharacterTable', 'WeaponBasicTable'}:
                        # A backlink to the root must not widen a terminal label.
                        if f'{target}/{target_id}' not in sources.rows:
                            sources.add(target, target_id, ('name', 'dungeonName', 'iconId', 'rarity'))
                        if target == 'WeaponBasicTable':
                            sources.add('ItemTable', target_id, ('name', 'iconId', 'rarity'))
                    # Supply text/submission data are inlined by the guide and
                    # preserve their exact table/row in each emitted field path.
                    path = field['field']
                    for inline in ('ActivitySubmitFoodTable', 'SubmitItem'):
                        if path.startswith(inline + '/'):
                            sources.add(inline, path.split('/', 1)[1].split('.', 1)[0])
                    if path.startswith('SystemJumpTable/'):
                        sources.add('SystemJumpTable', path.split('/', 1)[1].split('.', 1)[0],
                                    ('id', 'phaseId', 'phaseArgs'))
        records[f'ActivityTable/{key}'] = sources.rows
    return records
