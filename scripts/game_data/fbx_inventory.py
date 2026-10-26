"""Bounded binary FBX object/geometry census, without inflating mesh arrays.

This proves the exported structure, not source renderer completeness or mesh
payload integrity. A source/PPtr audit must supply the expected renderer set.
"""
import struct

SCHEMA = 'endfield.fbx-structural-inventory.v1'


def read_inventory(stream, length):
    stream.seek(0)
    def take(size):
        data=stream.read(size)
        if len(data)!=size:raise ValueError('truncated FBX structural read')
        return data
    if length<27 or take(23)!=b'Kaydara FBX Binary  \x00\x1a\x00':
        raise ValueError('binary FBX header required')
    version,=struct.unpack('<I',take(4));header=struct.Struct('<QQQB' if version>=7500 else '<IIIB')

    def children(start,end):
        position=start
        while position+header.size<=end:
            stream.seek(position);node_end,count,props_len,name_len=header.unpack(take(header.size))
            if node_end==0:
                if count or props_len or name_len:raise ValueError('invalid FBX null record')
                return
            name=take(name_len);props_at=stream.tell()
            if not position+header.size<=props_at<=props_at+props_len<=node_end<=end:
                raise ValueError('FBX node bounds differ')
            yield name,props_at,count,props_len,node_end
            position=node_end
        if position!=end:raise ValueError('FBX child tail is truncated')

    def properties(at,count,size):
        if count>64 or size>1024*1024:raise ValueError('FBX identity property bound exceeded')
        stream.seek(at);end=at+size;values=[]
        scalar={'Y':('h',2),'C':('?',1),'I':('i',4),'F':('f',4),'D':('d',8),'L':('q',8)}
        for _ in range(count):
            if stream.tell()>=end:raise ValueError('FBX property count exceeds block')
            code=take(1).decode('ascii')
            if code in scalar:
                fmt,width=scalar[code];value,=struct.unpack('<'+fmt,take(width))
            elif code in ('S','R'):
                size_,=struct.unpack('<I',take(4))
                if size_>end-stream.tell():raise ValueError('FBX identity string exceeds block')
                data=take(size_);value=data.decode('utf8').split('\0',1)[0] if code=='S' else None
            elif code in 'fdlib':
                count_,encoding,stored=struct.unpack('<III',take(12))
                if encoding not in (0,1) or stored>end-stream.tell():raise ValueError('FBX array descriptor exceeds block')
                value={'count':count_,'encoding':encoding,'storedBytes':stored};stream.seek(stored,1)
            else:raise ValueError(f'unsupported FBX identity property {code}')
            values.append(value)
        if stream.tell()!=end:raise ValueError('FBX property block has unconsumed bytes')
        return values

    models={};geometries={};connections=[]
    for section,at,count,size,end in children(27,length):
        if section not in (b'Objects',b'Connections'):continue
        for name,child_at,child_count,child_size,child_end in children(at+size,end):
            if section==b'Connections':
                if name!=b'C':continue
                props=properties(child_at,child_count,child_size)
                if len(props)>=3 and props[0]=='OO':connections.append(props[1:3])
            elif name in (b'Model',b'Geometry'):
                props=properties(child_at,child_count,child_size)
                if len(props)!=3 or type(props[0])!=int or not all(isinstance(v,str) for v in props[1:]):
                    raise ValueError('FBX object identity differs')
                target=models if name==b'Model' else geometries
                if props[0] in target:raise ValueError('duplicate FBX object identity')
                row=dict(name=props[1],type=props[2]);target[props[0]]=row
                if name==b'Geometry' and props[2]=='Mesh':
                    for sub,sub_at,sub_count,sub_size,_ in children(child_at+child_size,child_end):
                        if sub not in (b'Vertices',b'PolygonVertexIndex'):continue
                        # Array payloads can be large; consume only their header.
                        stream.seek(sub_at);code=take(1);n,encoding,stored=struct.unpack('<III',take(12))
                        valid_code=code in (b'd',b'f') if sub==b'Vertices' else code==b'i'
                        if sub_count!=1 or sub_size!=13+stored or encoding not in (0,1) or not valid_code:
                            raise ValueError('FBX geometry array descriptor differs')
                        if sub==b'Vertices' and n%3:raise ValueError('FBX position count is not xyz')
                        row['vertices' if sub==b'Vertices' else 'polygonVertexIndices']=n//3 if sub==b'Vertices' else n
    owners_by_geometry={}
    for child,parent in connections:
        if child in geometries and parent in models:
            owners_by_geometry.setdefault(child,[]).append(parent)
    mesh_rows=[]
    for geometry_id,row in geometries.items():
        if row['type']!='Mesh':continue
        owners=owners_by_geometry.get(geometry_id,[])
        mesh_rows.append(dict(**row,models=[models[owner]['name'] for owner in owners]))
    attached={parent for child,parent in connections if child in geometries and geometries[child]['type']=='Mesh'}
    return dict(version=version,geometries=mesh_rows,geometryCount=len(mesh_rows),
                geometryInstances=sum(len(row['models']) for row in mesh_rows),
                models=list(models.values()),unattachedMeshModels=[row['name'] for key,row in models.items() if row['type']=='Mesh' and key not in attached])


def inventory_store(export_root, *, cache=None):
    """Reuse unchanged structural reads; this does not authenticate skipped arrays."""
    from scripts.game_data.unity_store import UnityObjectStore,UnityStoreError
    saved = {}
    if cache:
        if cache.get('schema') != SCHEMA or cache.get('errors'):
            raise ValueError('unsupported or failed FBX inventory cache')
        saved = {row['name']: row for row in cache['rows']}
    store = UnityObjectStore.for_export(export_root)
    rows = []; errors = []; reused = 0
    for row in store.rows('Animator', '*.fbx'):
        previous = saved.get(row.name)
        if previous and (previous['sha256'], previous['size']) == (row.sha256, row.size):
            rows.append(previous); reused += 1
            continue
        try:
            with store.open_document(row.type, row.name) as stream:
                inventory = read_inventory(stream, row.size)
            rows.append(dict(name=row.name, pathId=row.path_id, sha256=row.sha256, size=row.size, inventory=inventory))
        except (ValueError, OSError, UnityStoreError) as error:
            errors.append(dict(name=row.name, error=str(error)))
    return dict(schema=SCHEMA, rows=rows, errors=errors, reused=reused)


def main():
    import argparse
    import json
    from pathlib import Path
    from scripts.common import write_json
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--export-root', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cache', type=Path, help='Prior successful structural report; reuse only identical row hashes and sizes')
    args = parser.parse_args()
    cache = json.loads(args.cache.read_bytes()) if args.cache else None
    result = inventory_store(args.export_root, cache=cache)
    write_json(args.report, result)
    print(f'FBX inventory: rows={len(result["rows"])}; reused={result["reused"]}; errors={len(result["errors"])}')
    if result['errors']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
