"""Read one packed ECS collider definition, independently of live actor ownership.

This is the byte-array format consumed by the ECS decoder, not a cooked PhysX
mesh. Mesh slots refer to the caller's ordered mesh list. Native authentication
is owned by ecs_collision_native; raw projections do not assert live selection.

Evidence and admission boundary
-------------------------------
The stored projection is structuralOnly until ecs_collision_native authenticates
its selected header, primitive/mesh/multi/terrain cases and descriptor strides.
Bounded counts, ordered mesh-list consistency and exact EOF are defensive reader
gates, stronger than the native decoder's own bounds checks. Disabled ordinary
attachments still consume their record and mesh slot. Complex meshes use a
separate flag profile without the ordinary bit-zero attachment gate. Anonymous
words, capsule dimension lanes and unknown flag bits retain raw values.

decode_prefix derives a self-sized definition from authenticated kind/counts,
then applies the strict reader to that exact slice. Trailing bytes stay opaque;
a clipped definition is unavailable even if its header is complete. An unbound
decoder argument supplies neither length units nor file/resource ownership, and
a prefix projection cannot replace an owned definition or missing mesh-ID span.
"""
from __future__ import annotations

import struct


def decode_prefix(payload: bytes, *, layout: dict, kinds: dict, limits: dict, mesh_count: int) -> dict:
    """Project one schema-sized prefix without assigning units to a caller.

    The strict definition reader still sees exact EOF. Captured trailing bytes
    are opaque and do not acquire ownership, framing or a buffer-length claim.
    """
    if not isinstance(payload,bytes) or len(payload)>limits['maxBytes']:
        raise ValueError('ecs-collision:prefix payload type/size')
    header=layout['header']
    if len(payload)<header['bytes']:raise ValueError(f'ecs-collision:prefix header truncated:expected>={header["bytes"]},actual={len(payload)}')
    number=struct.unpack_from('<h',payload,header['kind'])[0];kind=kinds.get(str(number))
    if kind is None:raise ValueError('ecs-collision:unsupported prefix kind:'+str(number))
    if kind=='multi':
        m=layout['multi']
        if len(payload)<m['bytes']:raise ValueError('ecs-collision:prefix multi header truncated')
        counts={name:struct.unpack_from('<i',payload,offset)[0] for name,offset in m['countOffsets'].items()}
        if any(n<0 or n>limits['maxRecords'] for n in counts.values()) or sum(counts.values())>limits['maxRecords']:
            raise ValueError('ecs-collision:prefix multi count bound')
        extent=m['bytes']+sum(n*m['strides'][name] for name,n in counts.items())
    else:extent=layout['singleBytes'][kind]
    if not 0<extent<=limits['maxBytes'] or extent>len(payload):
        raise ValueError(f'ecs-collision:prefix extent unavailable:expected={extent},captured={len(payload)},maximum={limits["maxBytes"]}')
    projection=decode(payload[:extent],layout=layout,kinds=kinds,limits=limits,mesh_count=mesh_count)
    return dict(projection=projection,consumedBytes=extent,capturedBytes=len(payload),opaqueTrailingBytes=len(payload)-extent,
        boundary='structuralOnly: complete schema-sized captured prefix; caller length units, allocation extent, trailing bytes, source selection and runtime ownership remain unresolved')


def decode(payload: bytes, *, layout: dict, kinds: dict, limits: dict, mesh_count: int) -> dict:
    def require(ok, detail):
        if not ok:
            raise ValueError('ecs-collision:' + detail)

    require(isinstance(payload, bytes) and len(payload) <= limits['maxBytes'], 'payload type/size')
    require(isinstance(mesh_count, int) and 0 <= mesh_count <= limits['maxRecords'], 'mesh count bound')
    if not payload:
        return dict(status='empty_definition', bytes=0, records=[], meshSlotsUsed=[])
    header = layout['header']
    require(len(payload) >= header['bytes'], f"header truncated:expected>={header['bytes']},actual={len(payload)}")

    def read(fmt, at):
        size = struct.calcsize('<' + fmt)
        require(0 <= at <= len(payload)-size, f'read outside payload:offset={at},bytes={size},actual={len(payload)}')
        return struct.unpack_from('<' + fmt, payload, at)

    kind_number = read('h', header['kind'])[0]
    require(str(kind_number) in kinds, 'unsupported kind:' + str(kind_number))
    kind = kinds[str(kind_number)]
    result = dict(status='decoded_definition', bytes=len(payload), kind=kind, kindValue=kind_number,
                  position=list(read('3f', header['position'])), rotation=list(read('4f', header['rotation'])),
                  reserved=read('H', header['reserved'])[0], layer=read('I', header['layer'])[0],
                  tag=read('i', header['tag'])[0], records=[], meshSlotsUsed=[],
                  boundary='structuralOnly: exact stored framing and ordered mesh slots; live attachments, shape ordinal and source selection remain separate')
    cursor = header['bytes']

    def record(group, start, size, *, single=False, mesh_slot=None):
        require(start+size <= len(payload), f'{group} record truncated:offset={start},bytes={size},actual={len(payload)}')
        r = dict(kind=group, offset=start, bytes=size, rawHex=payload[start:start+size].hex())
        if not single and group not in ('sphere', 'complexMesh'):
            r.update(position=list(read('3f', start)), rotation=list(read('4f', start+12)))
        elif not single and group == 'sphere':
            r['position'] = list(read('3f', start))
        # These offsets are stable per-record wire layouts, not native addresses.
        if group == 'box':
            gameplay, tag_config, flags, dims = (12,16,20,0) if single else (28,32,36,40)
            r['halfExtents'] = list(read('3f', start+dims))
        elif group == 'capsule':
            gameplay, tag_config, flags = (8,12,16) if single else (28,32,36)
            dimensions = 0 if single else 40
            r['dimensions'] = list(read('2f',start+dimensions))
        elif group == 'sphere':
            gameplay, tag_config, flags, radius = (4,8,12,0) if single else (12,16,20,24)
            r['radius'] = read('f',start+radius)[0]
        elif group == 'complexMesh':
            gameplay, tag_config, flags = 0,4,8
            r['scale'] = list(read('3f',start+12))
        elif group in ('triangleMesh', 'convexMesh', 'mesh'):
            gameplay, tag_config, flags, scale = (16,20,24,0) if single else (28,32,36,44)
            r.update(scale=list(read('3f',start+scale)),meshWord=read('I',start+(12 if single else 40))[0])
        elif group == 'terrain':
            gameplay, tag_config, flags = 0,4,8
            r['scale'] = list(read('3f',start+12))
        else:
            raise ValueError('ecs-collision:unsupported record:' + group)
        bits = read('I', start+flags)[0]
        complex_mesh=group == 'complexMesh'
        r.update(gameplayOptionsWord=read('I',start+gameplay)[0],tagConfigWord=read('I',start+tag_config)[0],
                 flagWord=bits,attachmentGate=None if complex_mesh else bool(bits&1),
                 secondaryFlag=None if complex_mesh else bool(bits&2),surfaceTypeByte=(bits>>(1 if complex_mesh else 2))&255)
        at = layout['extraWord']['single' if single else 'multi'].get(group)
        if at is not None:
            require(0 <= at <= size-4, 'anonymous word outside record:' + group)
            r['anonymousWord'] = read('I', start+at)[0]
        if complex_mesh:r['attachmentGateStatus']='packed-bit-zero-not-tested; mesh validation and allocation remain conditional'
        if mesh_slot is not None:
            r['meshSlot'] = mesh_slot
            result['meshSlotsUsed'].append(mesh_slot)
        result['records'].append(r)

    if kind == 'multi':
        multi = layout['multi']
        require(len(payload) >= multi['bytes'], 'multi header truncated')
        counts = {group:read('i',offset)[0] for group,offset in multi['countOffsets'].items()}
        require(all(0 <= n <= limits['maxRecords'] for n in counts.values()) and sum(counts.values()) <= limits['maxRecords'], 'multi count bound')
        require(counts['complexMesh'] <= 1, 'unsupported complex mesh count:' + str(counts['complexMesh']))
        expected_meshes = counts['complexMesh']+counts['triangleMesh']+counts['convexMesh']
        require(mesh_count == expected_meshes, f'multi mesh count:expected={expected_meshes},actual={mesh_count}')
        expected_bytes = multi['bytes']+sum(counts[k]*multi['strides'][k] for k in counts)
        require(len(payload) == expected_bytes, f'multi EOF:expected={expected_bytes},actual={len(payload)}')
        result['counts'] = counts
        cursor, slot = multi['bytes'], 0
        for group in ('complexMesh','box','capsule','sphere','triangleMesh','convexMesh'):
            for _ in range(counts[group]):
                mesh_group = group in ('complexMesh','triangleMesh','convexMesh')
                record(group,cursor,multi['strides'][group],mesh_slot=slot if mesh_group else None)
                cursor += multi['strides'][group]
                slot += int(mesh_group)
    else:
        expected_bytes = layout['singleBytes'][kind]
        require(len(payload) == expected_bytes, f'{kind} EOF:expected={expected_bytes},actual={len(payload)}')
        if kind == 'mesh':
            require(mesh_count == 1, f'single mesh count:expected=1,actual={mesh_count}')
        record(kind,cursor,expected_bytes-cursor,single=True,mesh_slot=0 if kind=='mesh' else None)
        cursor = expected_bytes
    require(cursor == len(payload), 'unconsumed bytes')
    return result


def annotate_parameters(projection: dict, enums: dict) -> dict:
    """Attach only authenticated enum labels; preserve aliases and unknown bits."""
    options=enums['Beyond.Gameplay.Core.ColliderOptions']['members']
    surfaces=enums['UnityEngine.ColliderSurfaceType']['members']
    known=0
    for member in options:known |= member['value']&0xffffffff
    for record in projection['records']:
        word=record['gameplayOptionsWord']
        record['gameplayOptionNames']=[member['name'] for member in options
            if (mask:=member['value']&0xffffffff) != 0 and word&mask == mask]
        record['unknownGameplayOptionBits']=word&(~known)&0xffffffff
        record['surfaceTypeNames']=[member['name'] for member in surfaces if member['value'] == record['surfaceTypeByte']]
    projection['parameterEvidenceBoundary']='direct covered native parameter/userdata forwarding and selected enum defaults; default-decoder stored interpretation, not runtime activation or option reads'
    return projection


def main(argv=None):
    import argparse
    import hashlib
    import json
    from pathlib import Path
    from scripts.game_data.ecs_collision_native import load
    from scripts.game_data.corpus_common import atomic_write_text
    from scripts.repo_paths import REPO_ROOT

    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--payload',type=Path,required=True)
    parser.add_argument('--mesh-count',type=int,required=True)
    parser.add_argument('--game-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/runtime_capture/collision/ecs-definition.json')
    args=parser.parse_args(argv)
    output=args.output.resolve()
    if not any(output.is_relative_to(REPO_ROOT/name) for name in ('reports','scratch','tmp')):
        raise ValueError('ecs-collision:generated output must be under reports/, scratch/ or tmp/')
    root=args.game_root.resolve()
    if root.name=='Endfield_Data':root=root.parent
    contract,gate=load(gameassembly=root/'GameAssembly.dll',metadata=root/'Endfield_Data/il2cpp_data/Metadata/global-metadata.dat',unityplayer=root/'UnityPlayer.dll')
    report=dict(schema='endfield.ecs-collision-projection.v2',status=gate['status'],nativeGate=gate,payload=str(args.payload.resolve()),projection=None,diagnostics=[])
    if contract is not None:
        try:
            payload=args.payload.read_bytes()
            report.update(projection=decode(payload,layout=contract['layout'],kinds=contract['kinds'],limits=contract['limits'],mesh_count=args.mesh_count),
                          payloadSha256=hashlib.sha256(payload).hexdigest(),status='validated')
            annotate_parameters(report['projection'],contract['enums'])
            if args.payload.read_bytes()!=payload:raise ValueError('ecs-collision:payload changed during projection')
        except (OSError,ValueError,KeyError,struct.error) as error:
            report.update(status='failed',projection=None,diagnostics=[dict(check='ecs_definition_framing',source=str(args.payload),detail=str(error)[:1200])])
    atomic_write_text(output,json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],records=len((report['projection'] or {}).get('records',[])),detail=gate.get('detail',''),diagnostics=report['diagnostics'] or gate['diagnostics'],output=str(output))))
    return 0 if report['status']=='validated' else 1


if __name__=='__main__':raise SystemExit(main())
