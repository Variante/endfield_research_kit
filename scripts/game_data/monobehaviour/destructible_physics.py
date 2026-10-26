"""Stored DestructiblePhysicsMono header and physicsSettings prefix.

Only this prefix is decoded. The caller must authenticate the named MonoScript
through its serialized external slot; the following effects/curve tail remains
opaque. No live activation or actor attachment is inferred from these items.
"""
from scripts.game_data.unity_scene import _Reader


def read_physics_prefix(data: bytes) -> dict:
    reader = _Reader(data)
    out = dict(gameObject=reader.pointer('m_GameObject'))
    out['enabled'], = reader.unpack('B','m_Enabled'); reader.align()
    out['script'] = reader.pointer('m_Script')
    length, = reader.unpack('i','m_Name.length')
    out['name'] = reader.take(length,'m_Name').decode('utf-8'); reader.align()
    values = reader.vector(4,'physicsSettings')
    out['settings'] = dict(zip(('density','linearDrag','angularDrag','gravity'),values))
    count, = reader.unpack('i','physicsSettings.physicsItems.count')
    # Every item requires PPtr, renderer count and forceMultiplier, at minimum.
    if not 0 <= count <= (len(data)-reader.offset)//20:
        raise ValueError('physicsItems count cannot fit remaining prefix')
    out['items'] = []
    for i in range(count):
        field = f'physicsItems[{i}]'
        out['items'].append(dict(collider=reader.pointer(field+'.cld'),
            renderers=reader.pointers(field+'.correspondingRenderers'),
            forceMultiplier=reader.vector(1,field+'.forceMultiplier')[0]))
    out.update(prefixBytes=reader.offset,opaqueTailBytes=len(data)-reader.offset)
    return out
