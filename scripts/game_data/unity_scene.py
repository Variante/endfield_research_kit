"""Bounded Endfield Unity scene-object bodies and local collider joins.

These are stored GameObject, Transform, MeshCollider, BoxCollider and Rigidbody bodies, not runtime
instances. Callers authenticate the serialized identity/raw bytes separately.
External PPtrs remain unresolved; a matching name or bare PathID never joins.
"""
from __future__ import annotations

import math
import struct

BOX_TYPE_TREE_FIELDS = (
    'm_GameObject:PPtr<GameObject>', 'm_GameObject.m_FileID:int', 'm_GameObject.m_PathID:SInt64',
    'm_ColliderOptions:int', 'm_TagConfig:int', 'm_Material:PPtr<PhysicMaterial>',
    'm_Material.m_FileID:int', 'm_Material.m_PathID:SInt64', 'm_SurfaceType:UInt8',
    'm_IsTrigger:bool', 'm_Enabled:bool', 'm_EnableDither:bool', 'm_Size:Vector3f',
    'm_Size.x:float', 'm_Size.y:float', 'm_Size.z:float', 'm_Center:Vector3f',
    'm_Center.x:float', 'm_Center.y:float', 'm_Center.z:float',
)


class _Reader:
    def __init__(self, data: bytes):
        self.data, self.offset = data, 0

    def take(self, size: int, field: str) -> bytes:
        if size < 0 or self.offset + size > len(self.data):
            raise ValueError(f"{field}: truncated at {self.offset}, need {size}, length {len(self.data)}")
        out = self.data[self.offset:self.offset+size]; self.offset += size
        return out

    def unpack(self, fmt: str, field: str):
        return struct.unpack('<'+fmt, self.take(struct.calcsize('<'+fmt), field))

    def pointer(self, field: str) -> tuple[int, int]:
        file_id, path_id = self.unpack('iq', field)
        if file_id < 0:
            raise ValueError(f"{field}: negative file ID {file_id}")
        return file_id, path_id

    def boolean(self, field: str) -> bool:
        value, = self.unpack('B', field)
        if value > 1:
            raise ValueError(f"{field}: invalid bool {value}")
        return bool(value)

    def pointers(self, field: str) -> list[tuple[int, int]]:
        count, = self.unpack('i', field+'.count')
        if not 0 <= count <= (len(self.data)-self.offset)//12:
            raise ValueError(f"{field}: count {count} cannot fit remaining bytes")
        return [self.pointer(f'{field}[{i}]') for i in range(count)]

    def vector(self, size: int, field: str) -> tuple[float, ...]:
        values = self.unpack('f'*size, field)
        if not all(math.isfinite(value) for value in values):
            raise ValueError(f"{field}: non-finite vector")
        return values

    def align(self):
        self.take((-self.offset) & 3, 'alignment')

    def finish(self):
        if self.offset != len(self.data):
            raise ValueError(f"scene object: trailing bytes at {self.offset}/{len(self.data)}")


def read_scene_object(kind: str, data: bytes) -> dict:
    """Read the observed player layouts through EOF, rejecting other shapes."""
    reader = _Reader(data)
    if kind in ('MeshCollider', 'BoxCollider'):
        out = dict(gameObject=reader.pointer('m_GameObject'))
        out['colliderOptions'], out['tagConfig'] = reader.unpack('ii', 'options')
        out['material'] = reader.pointer('m_Material')
        out['surfaceType'], = reader.unpack('B', 'm_SurfaceType')
        for key in ('isTrigger', 'enabled', 'enableDither'):
            out[key] = reader.boolean(key)
        if kind == 'MeshCollider':
            out['convex'] = reader.boolean('convex')
            reader.align()
            out['cookingOptions'], = reader.unpack('i', 'm_CookingOptions')
            out['mesh'] = reader.pointer('m_Mesh')
        else:
            reader.align()
            out['size'] = reader.vector(3, 'm_Size')
            out['center'] = reader.vector(3, 'm_Center')
    elif kind == 'Transform':
        out = dict(gameObject=reader.pointer('m_GameObject'), rotation=reader.vector(4, 'm_LocalRotation'),
                   position=reader.vector(3, 'm_LocalPosition'), scale=reader.vector(3, 'm_LocalScale'))
        norm = sum(value*value for value in out['rotation'])
        if abs(norm-1) > 1e-4:
            raise ValueError(f"m_LocalRotation: quaternion norm squared {norm} differs from 1")
        out['children'] = reader.pointers('m_Children')
        out['father'] = reader.pointer('m_Father')
    elif kind == 'GameObject':
        out = dict(components=reader.pointers('m_Component'))
        out['layer'], = reader.unpack('I', 'm_Layer')
        length, = reader.unpack('i', 'm_Name.length')
        out['name'] = reader.take(length, 'm_Name').decode('utf-8')
        reader.align()
        out['tag'], out['artTag'] = reader.unpack('BB', 'm_Tag/m_ArtTag')
        out['active'] = reader.boolean('m_IsActive')
    elif kind == 'Rigidbody':
        out = dict(gameObject=reader.pointer('m_GameObject'))
        out['mass'], out['drag'], out['angularDrag'] = reader.vector(3, 'mass/drag')
        out['useGravity'] = reader.boolean('m_UseGravity')
        out['isKinematic'] = reader.boolean('m_IsKinematic')
        out['interpolate'], = reader.unpack('B', 'm_Interpolate')
        reader.align()
        out['constraints'], out['collisionDetection'] = reader.unpack('ii', 'constraints/collisionDetection')
    else:
        raise ValueError(f"unsupported scene object kind: {kind}")
    reader.finish()
    return out


def scene_identity(metadata: dict) -> tuple:
    """Exact physical serialized identity; signed/unsigned PathID normalize."""
    return (metadata['sourceOriginalPath'].replace('\\', '/').casefold(), metadata['sourceOffset'],
            metadata['sourceFile'], metadata['pathId'] & ((1 << 64)-1))


def local_target(identity: tuple, pointer: tuple[int, int]) -> tuple | None:
    return (*identity[:3], pointer[1] & ((1 << 64)-1)) if pointer[0] == 0 and pointer[1] else None


def _multiply(a, b):
    return tuple(sum(a[r*4+k]*b[k*4+c] for k in range(4)) for r in range(4) for c in range(4))


def _local_matrix(transform):
    x, y, z, w = transform['rotation']; sx, sy, sz = transform['scale']; px, py, pz = transform['position']
    return ((1-2*(y*y+z*z))*sx, 2*(x*y-z*w)*sy, 2*(x*z+y*w)*sz, px,
            2*(x*y+z*w)*sx, (1-2*(x*x+z*z))*sy, 2*(y*z-x*w)*sz, py,
            2*(x*z-y*w)*sx, 2*(y*z+x*w)*sy, (1-2*(x*x+y*y))*sz, pz,
            0., 0., 0., 1.)


def trace_component(identity: tuple, objects: dict[tuple, dict], *, max_depth: int = 256) -> dict:
    """Verify component backlinks and every local parent/child edge.

    ``objects`` contains authenticated raw scene bodies with ``kind``. The
    resulting matrix composes their stored TRS chain; it is not a live instance
    transform. Missing/external parents and cycles never return a partial matrix.
    """
    collider = objects[identity]
    game_key = local_target(identity, collider['gameObject'])
    game = objects.get(game_key)
    if not game or game['kind'] != 'GameObject':
        raise ValueError('component GameObject is external or unavailable')
    if sum(local_target(game_key, pointer) == identity for pointer in game['components']) != 1:
        raise ValueError(f"GameObject must declare its {collider['kind']} component exactly once")
    candidates = [(key, objects[key]) for pointer in game['components']
                  if (key := local_target(game_key, pointer)) in objects and objects[key]['kind'] == 'Transform']
    if len(candidates) != 1:
        raise ValueError(f'GameObject has {len(candidates)} available Transform components')
    key, transform = candidates[0]
    chain, seen = [], set()
    while True:
        if key in seen or len(chain) >= max_depth:
            raise ValueError('Transform parent cycle or depth limit')
        seen.add(key)
        owner_key = local_target(key, transform['gameObject']); owner = objects.get(owner_key)
        if not owner or owner['kind'] != 'GameObject':
            raise ValueError('Transform GameObject is external or unavailable')
        if not any(local_target(owner_key, pointer) == key for pointer in owner['components']):
            raise ValueError('GameObject does not declare its Transform component')
        if not chain and owner_key != game_key:
            raise ValueError(f"{collider['kind']} and Transform GameObject backlinks differ")
        chain.append(dict(identity=key, gameObject=owner_key, name=owner['name'], active=owner['active'],
                          position=transform['position'], rotation=transform['rotation'], scale=transform['scale']))
        father = transform['father']
        if not father[1]:
            break
        parent_key = local_target(key, father); parent = objects.get(parent_key)
        if not parent or parent['kind'] != 'Transform':
            raise ValueError('Transform parent is external or unavailable')
        if not any(local_target(parent_key, pointer) == key for pointer in parent['children']):
            raise ValueError('Transform parent does not declare its child')
        key, transform = parent_key, parent
    matrix = (1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.)
    for node in reversed(chain):
        matrix = _multiply(matrix, _local_matrix(node))
        if not all(math.isfinite(value) for value in matrix):
            raise ValueError('Transform composition produced a non-finite matrix')
    return dict(gameObject=game_key, chain=chain, composedLocalMatrix=matrix)


def trace_collider(identity: tuple, objects: dict[tuple, dict], *, max_depth: int = 256) -> dict:
    """Verify a supported Collider's stored component/hierarchy and shape fields."""
    collider = objects[identity]
    if collider['kind'] not in ('MeshCollider', 'BoxCollider'):
        raise ValueError('collider identity does not name a supported Collider')
    common = dict(trace_component(identity, objects, max_depth=max_depth), enabled=collider['enabled'])
    if collider['kind'] == 'BoxCollider':
        return dict(common, size=collider['size'], center=collider['center'], isTrigger=collider['isTrigger'])
    return dict(common, mesh=local_target(identity, collider['mesh']),
                meshPointerStatus='null' if not collider['mesh'][1] else 'local' if collider['mesh'][0] == 0 else 'external_unresolved',
                convex=collider['convex'])


def trace_rigidbody(identity: tuple, objects: dict[tuple, dict]) -> dict:
    """Join a stored Rigidbody to reciprocal colliders on its own GameObject.

    Child colliders, runtime actor attachment, activation, awake state and
    scene/filter participation require separate evidence. Kinematic bodies
    stay dormant here even if a compiled consumer can later activate them.
    """
    body = objects[identity]
    if body['kind'] != 'Rigidbody':
        raise ValueError('body identity does not name a Rigidbody')
    game_key = local_target(identity,body['gameObject']); game = objects.get(game_key)
    if not game or game['kind'] != 'GameObject':
        raise ValueError('Rigidbody GameObject is external or unavailable')
    components = [local_target(game_key,p) for p in game['components']]
    if components.count(identity) != 1:
        raise ValueError('GameObject must declare its Rigidbody exactly once')
    attached = []
    for key in components:
        collider = objects.get(key,{})
        if collider.get('kind') != 'MeshCollider':continue
        if local_target(key,collider['gameObject']) != game_key:
            raise ValueError('Rigidbody/MeshCollider GameObject backlinks differ')
        trace = trace_collider(key,objects)
        attached.append(dict(identity=key,trace=trace,
            storedPhysicalShape=collider['enabled'] and not collider['isTrigger'] and collider['convex']
                and all(node['active'] for node in trace['chain'])))
    candidate = body['mass'] > 0 and body['constraints'] == 0 and any(c['storedPhysicalShape'] for c in attached)
    return dict(identity=identity,gameObject=game_key,name=game['name'],layer=game['layer'],
        body=body,colliders=attached,storedSolverCandidate=candidate,
        storedMode='kinematic' if body['isKinematic'] else 'dynamic',
        runtimeSolverEligibility='unresolved',
        evidenceBoundary='exact stored reciprocal components/TRS; conditional candidate after activation; '
            'unresolved live attachment, awake body, scene policy, pair flags and solver participation')
