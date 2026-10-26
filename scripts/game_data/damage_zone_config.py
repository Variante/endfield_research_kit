"""Project an explicitly selected exported damage-zone definition.

This reads a serialized-TypeTree MonoBehaviour, preserving source identity.
It does not assert that this object is the live DataManager configuration.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from scripts.game_data.unity_store import UnityObjectStore

ROUTES = ('damageTypeDamageIncreaseZoneName', 'igniteDamageIncreaseZoneName',
          'skillTypeDamageIncreaseZoneName', 'damageToBrokenUnitIncreaseZoneName',
          'damageEnhancedZoneName', 'damageVulnerableZoneName')


def project_zone_config(document):
    meta = document.get('$animestudio', {})
    if document.get('m_Name') != 'DamageScaleProcessorConfig' or meta.get('typeTreeSource') != 'serializedType':
        raise ValueError('damage-zone definition requires the named serialized TypeTree')
    paths = set(meta.get('typeTreeFieldPaths', []))
    needed = {'allZones.Array.data.' + name + ':' + kind for name, kind in (
        ('name', 'string'), ('isMultiplyZone', 'UInt8'), ('mergeAttackerAndDefender', 'UInt8'),
        ('isDamageTypeZone', 'UInt8'), ('serverIndex', 'int'))}
    needed.update(name + ':string' for name in ROUTES)
    if not needed <= paths:
        raise ValueError('damage-zone TypeTree does not name every required field')
    raw_zones = document.get('allZones')
    if not isinstance(raw_zones, list) or len(raw_zones) > 1024:
        raise ValueError('damage-zone list is absent or exceeds the projection bound')
    zones = []
    for ordinal, row in enumerate(raw_zones):
        if not isinstance(row, dict) or not isinstance(row.get('name'), str):
            raise ValueError(f'damage-zone name missing at index {ordinal}')
        flags = {name: row.get(name) for name in ('isMultiplyZone', 'mergeAttackerAndDefender', 'isDamageTypeZone')}
        if any(type(value) not in (int, bool) or value not in (0, 1) for value in flags.values()):
            raise ValueError(f'damage-zone Boolean differs at index {ordinal}')
        if type(row.get('serverIndex')) is not int:
            raise ValueError(f'damage-zone serverIndex differs at index {ordinal}')
        zones.append({'index': ordinal, 'name': row['name'], **{k: bool(v) for k, v in flags.items()},
                      'serverIndex': row['serverIndex']})
    names = [row['name'] for row in zones]
    if len(set(names)) != len(names):
        raise ValueError('duplicate zone names make this named projection ambiguous')
    routes = {}
    for name in ROUTES:
        value = document.get(name)
        if not isinstance(value, str):
            raise ValueError(f'damage-zone route is not a string: {name}')
        routes[name] = {'name': value, 'index': names.index(value) if value in names else None}
    return {'zones': zones, 'routes': routes, 'sourceObject': {
        k: meta.get(k) for k in ('pathId', 'sourceFile', 'sourceOriginalPath', 'sourceOffset', 'rawDataSha256')},
        'liveConfigSelected': False, 'boundary': 'Stored named definition; use native rules separately. This is not observed runtime configuration selection.'}


def load_zone_config(export_root: Path, *, name: str | None = None):
    """The caller authenticates export freshness before consuming this projection."""
    store = UnityObjectStore.for_export(export_root)
    candidates = [store.row('MonoBehaviour', name)] if name else store.rows_by_object_name('MonoBehaviour', 'DamageScaleProcessorConfig')
    if len(candidates) != 1 or candidates[0] is None:
        raise ValueError('select one unambiguous DamageScaleProcessorConfig document')
    row = candidates[0]
    raw = store.read_bytes('MonoBehaviour', row.name)
    if len(raw) != row.size or hashlib.sha256(raw).hexdigest().lower() != row.sha256.lower():
        raise ValueError('damage-zone exported document changed during selection')
    result = project_zone_config(json.loads(raw))
    return {**result, 'exportDocument': row.ref, 'exportSha256': row.sha256}
