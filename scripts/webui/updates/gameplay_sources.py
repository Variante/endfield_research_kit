"""Typed, bounded source ownership for Gameplay entity comparisons.

A string matching a table key is not a foreign key. Shared definitions follow
only the joins used by the entity page; related item labels are terminal views.
In particular, costs, recommended weapons and set members cannot crawl back
into other entities or through factory recipes.
"""
from __future__ import annotations

from typing import Any, Iterator

from scripts.webui.gameplay.gems import collect_gem_entries
from scripts.webui.updates.catalog_sources import stage_source_records

PRIMARY_TABLES = {
    'character': 'CharacterTable', 'weapon': 'WeaponBasicTable',
    'equipment': 'EquipTable', 'enemy': 'EnemyTable', 'item': 'UseItemTable',
    'gem': 'WorldEnergyPointGroupTable',
    'stage': 'DungeonTable',
}
OWNER_TABLES = {
    'character': ('CharacterTable', 'CharGrowthTable', 'CharacterPotentialTable', 'SpaceshipCharSkillTable'),
    'weapon': ('WeaponBasicTable', 'ItemTable'),
    'equipment': ('EquipTable', 'ItemTable'),
    'enemy': ('EnemyTable', 'EnemyDisplayInfoTable'),
    'item': ('UseItemTable', 'ItemTable', 'UsableItemChestTable', 'RecoverApItemTable'),
}
# Each target is declared by the owning field, never by an unrestricted key
# lookup across tables. Nested fields retain the same declared role.
JOINS = {
    'CharacterTable': {'charTypeId': ('CharTypeTable',), 'profession': ('CharProfessionTable',)},
    'CharGrowthTable': {'skillIdList': ('SkillPatchTable',), 'talentEffectId': ('PotentialTalentEffectTable',),
                       'nodeId': ('CharBreakNodeTable',)},
    'CharacterPotentialTable': {'potentialEffectId': ('PotentialTalentEffectTable',)},
    'PotentialTalentEffectTable': {'skillId': ('SkillPatchTable',)},
    'SpaceshipCharSkillTable': {'skillId': ('SpaceshipSkillTable',)},
    'WeaponBasicTable': {
        'levelTemplateId': ('WeaponUpgradeTemplateTable', 'WeaponUpgradeTemplateSumTable'),
        'breakthroughTemplateId': ('WeaponBreakThroughTemplateTable',),
        'talentTemplateId': ('WeaponTalentTemplateTable',),
        'weaponSkillList': ('SkillPatchTable',), 'weaponPotentialSkill': ('SkillPatchTable',)},
    'EquipTable': {'domainId': ('DomainDataTable',)},
    'EquipSuitTable': {'skillID': ('SkillPatchTable',)},
    'EquipFormulaTable': {'level': ('EquipFormulaChainTable',), 'packId': ('EquipPackTable',),
                          'unlockKey': ('ShopChannelDevelopmentTable',)},
    'EnemyTable': {'attrTemplateId': ('EnemyAttributeTemplateTable',),
                   'templateId': ('EnemyTemplateDisplayInfoTable', 'WikiEnemyDropTable')},
    'EnemyDisplayInfoTable': {'abilityDescIds': ('EnemyAbilityDescTable',)},
    'EnemyTemplateDisplayInfoTable': {'abilityDescIds': ('EnemyAbilityDescTable',),
                                     'tags': ('EnemyTagTable',), 'distributionIds': ('DistributionInfoTable',),
                                     'displayType': ('DisplayEnemyTypeTable',)},
    'DistributionInfoTable': {'jumpId': ('SystemJumpTable',)},
    'UseItemTable': {'skillId': ('SkillPatchTable',), 'rewardId': ('RewardTable',)},
    'UsableItemChestTable': {'rewardId': ('RewardTable',)},
}
ITEM_FIELDS = {
    'CharacterTable': ('defaultWeaponId',), 'CharGrowthTable': ('defaultWeaponId',),
    'CharacterPotentialTable': ('firstItemId', 'itemIds', 'unlockCardTopicItem', 'unlockCharPictureItemList'),
    'WeaponBasicTable': ('potentialUpItemList',), 'WikiEnemyDropTable': ('dropItemIds',),
    'UsableItemChestTable': ('randomChestItemIds', 'fixedChestItemIds'),
    'EquipFormulaTable': ('costItemId', 'costGoldId'),
    'EquipFormulaChainTable': ('costItemId', 'costGoldId'),
}
ITEM_LISTS = ('requiredItem', 'itemBundle', 'requiredItems', 'itemList')
ITEM_LABEL_FIELDS = ('name', 'iconId', 'rarity')
# Equipment displays labels from these shared catalogs, not their regional
# development levels, shop inventories, pack configuration or sibling members.
EQUIPMENT_SOURCE_FIELDS = {
    'DomainDataTable': ('domainName', 'name', 'storageName'),
    'EquipSuitTable': ('list',),
    'EquipPackTable': ('name',),
    'ShopChannelDevelopmentTable': ('channelName', 'name'),
}


def gem_source_records(tables: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Use the page's pool/stage joins without importing compatible weapons."""
    entries, _ = collect_gem_entries({name + '.json': rows for name, rows in tables.items()}, [], lambda _: '')
    records = {}
    for entry in entries:
        key = entry['id']
        sources = {f'WorldEnergyPointGroupTable/{key}': tables['WorldEnergyPointGroupTable'][key]}

        def add(table, identity, fields=None):
            row = tables.get(table, {}).get(identity)
            if isinstance(row, dict):
                sources[f'{table}/{identity}'] = row if fields is None else {
                    name: row[name] for name in fields if name in row}

        for pool in entry['termPools']:
            for term in pool:
                add('GemTable', term['id'], ('tagName', 'termType'))
        for stage in entry['stages']:
            add('WorldEnergyPointTable', stage['id'])
            mechanic = tables.get('GameMechanicTable', {}).get(stage['id']) or {}
            if mechanic.get('gameGroupId') == key:
                add('GameMechanicTable', stage['id'])
            add('LevelDescTable', stage['levelId'], ('showName',))
        if entry['domain']['id']:
            add('DomainDataTable', entry['domain']['id'], ('domainName', 'sortId'))
        records[f'gem:{key}'] = sources
    return records


def _scalars(value: Any) -> Iterator[str]:
    if isinstance(value, list):
        for child in value:
            yield from _scalars(child)
    elif isinstance(value, (str, int)) and not isinstance(value, bool) and str(value):
        yield str(value)


def _fields(value: Any, names) -> Iterator[tuple[str, Any]]:
    if isinstance(value, dict):
        if 'id' in value and set(value) <= {'id', 'text'}:
            return
        for name, child in value.items():
            if name in names:
                yield name, child
            yield from _fields(child, names)
    elif isinstance(value, list):
        for child in value:
            yield from _fields(child, names)


def entity_source_records(tables: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Return each entity's own rows and explicitly joined shared definitions."""
    records = {}
    # Match equipment_suit_lookup/formula_by_equip in the page builder: the
    # last explicitly named membership/outcome wins. The membership list is a
    # selector, not part of every member's effect definition.
    suit_rows = {}
    for key, row in tables.get('EquipSuitTable', {}).items():
        if isinstance(row, dict):
            for item in row.get('equipList') or []:
                suit_rows[str(item)] = key
    formulas = {}
    for key, row in tables.get('EquipFormulaTable', {}).items():
        if isinstance(row, dict):
            formulas[str(row.get('outcomeEquipId') or '')] = key

    for kind, primary in PRIMARY_TABLES.items():
        if kind == 'gem':
            records.update(gem_source_records(tables))
            continue
        if kind == 'stage':
            records.update(stage_source_records(tables))
            continue
        for identity in tables.get(primary, {}):
            sources = {}
            pending = [(table, str(identity)) for table in OWNER_TABLES[kind]]
            if kind == 'equipment':
                if str(identity) in suit_rows:
                    pending.append(('EquipSuitTable', suit_rows[str(identity)]))
                if str(identity) in formulas:
                    pending.append(('EquipFormulaTable', formulas[str(identity)]))
            seen = set()

            def item_label(key):
                source = f'ItemTable/{key}'
                row = tables.get('ItemTable', {}).get(key)
                if isinstance(row, dict) and source not in sources:
                    sources[source] = {name: row[name] for name in ITEM_LABEL_FIELDS if name in row}

            while pending:
                table, key = pending.pop()
                if (table, key) in seen:
                    continue
                seen.add((table, key))
                row = tables.get(table, {}).get(key)
                if row is None:
                    continue
                if kind == 'equipment' and table in EQUIPMENT_SOURCE_FIELDS and isinstance(row, dict):
                    row = {field: row[field] for field in EQUIPMENT_SOURCE_FIELDS[table] if field in row}
                sources[f'{table}/{key}'] = row
                for field, value in _fields(row, JOINS.get(table, {})):
                    for target in JOINS[table][field]:
                        for ref in _scalars(value):
                            pending.append((target, ref))
                # Leaf item labels have no outgoing edges, including when an
                # item happens to carry an entity ID or a production recipe.
                for _, value in _fields(row, ITEM_FIELDS.get(table, ())):
                    for ref in _scalars(value):
                        item_label(ref)
                for _, items in _fields(row, ITEM_LISTS):
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict):
                                item_label(str(item.get('id') or ''))
            records[f'{kind}:{identity}'] = sources
    return records
