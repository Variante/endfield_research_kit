"""Publish neutral stored render meshes/material metadata and LOD assemblies."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import tempfile
import shutil

from scripts.common import rel_path,write_json
from scripts.common import sha256_file
from scripts.game_data.unity_scene import scene_identity
from scripts.game_data.unity_mesh import read_surface
from scripts.game_data import unity_texture_decode
from scripts.webui.assets.collision_prefabs import transform_surface

SOURCE='StoredRender'
SCHEMA='endfield.assets-stored-render.v2'
BOUNDARY='Selected stored render meshes and mathematical root/descendant TRS, with stored LOD membership. Neutral preview: material appearance, runtime LOD selection, vertex-stream overrides, animation and world placement are not reconstructed.'


def _name(key):return hashlib.sha256(json.dumps(key,separators=(',',':')).encode()).hexdigest()


def _public(value):
    if isinstance(value,dict):
        return {k:(str(v&((1<<64)-1)) if k in ('pathId','m_PathID') and isinstance(v,int) else str(v) if k=='sourceOffset' else _public(v)) for k,v in value.items()}
    if isinstance(value,list):return [_public(v) for v in value]
    return value


def _obj(path,parts):
    offset=uv_offset=normal_offset=faces_count=0
    with path.open('w',encoding='utf-8',newline='\n') as stream:
        stream.write('# '+BOUNDARY+'\n')
        for name,surface,vertices,submeshes in parts:
            stream.write('o '+name+'\n')
            for row in vertices:stream.write('v '+' '.join(format(v,'.17g') for v in row)+'\n')
            uv=surface['uv0'];normals=surface['normals'] if vertices is surface['vertices'] else None
            # Assemblies use generated viewer normals rather than incorrectly
            # transforming source normals under nonuniform stored TRS.
            for row in uv or []:stream.write('vt '+' '.join(format(v,'.17g') for v in row)+'\n')
            for row in normals or []:stream.write('vn '+' '.join(format(v,'.17g') for v in row)+'\n')
            for sub in submeshes:
                stream.write(f'g {name}_submesh_{sub["slot"]}\n')
                for face in sub['faces']:
                    refs=[]
                    for i in face:
                        vertex=i+offset+1
                        refs.append(f'{vertex}/{i+uv_offset+1}/{i+normal_offset+1}' if uv and normals else
                                    f'{vertex}/{i+uv_offset+1}' if uv else f'{vertex}//{i+normal_offset+1}' if normals else str(vertex))
                    stream.write('f '+' '.join(refs)+'\n');faces_count+=1
            offset+=len(vertices);uv_offset+=len(uv or []);normal_offset+=len(normals or [])
    return dict(rel=f'{SOURCE}/{path.name}',sha256=hashlib.sha256(path.read_bytes()).hexdigest(),vertexCount=offset,triangleCount=faces_count)


def publish(report,bodies,*,root,asset_dir,cli=None):
    destination=asset_dir/'stored_render';destination.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix='selection-',dir=destination.resolve()));surfaces={};mesh_assets={};material_assets={}
    textures={}
    for material in report['materials']:
        for value in material['textures']:
            reference=value['reference'];target=reference.get('target')
            if reference['status']=='exact_selected_target_identity' and target['classId']==28:
                textures[scene_identity(target['identity'])]=target
    texture_evidence=dict(schema=unity_texture_decode.SCHEMA,status='missing',decoded=0,unavailable=0)
    if textures:
        try:
            if cli is None:raise ValueError('stored texture decode requires the admitted parent CLI')
            decoded=unity_texture_decode.decode_textures(list(textures.values()),bodies,cli=cli,work_root=root/'tmp/animestudio/texture_previews')
            for value in decoded['textures']:
                target=textures[scene_identity(value['source']['identity'])];name='texture_'+unity_texture_decode.texture_key(target['identity'])+'.png'
                shutil.copyfile(value['pngPath'],stage/name)
                if sha256_file(stage/name).lower()!=value['pngSha256']:raise ValueError('copied texture PNG hash differs')
                target['preview']=dict(rel=f'{SOURCE}/{name}',sha256=value['pngSha256'],**value['descriptor'],
                    payloadSha256=value['payloadSha256'],topMipSha256=value['topMipSha256'])
            texture_evidence.update(status=decoded['status'],decoded=len(decoded['textures']),unavailable=len(decoded['unavailable']),evidenceBoundary=decoded['evidenceBoundary'])
            write_json(root/'reports/assets/stored_texture_preview_current.json',decoded)
        except (ValueError,OSError,KeyError,TypeError,OverflowError) as error:
            for target in textures.values():target.pop('preview',None)
            texture_evidence.update(status='unavailable',diagnostic=str(error)[:1200])
    for row in report['meshes']:
        key=scene_identity(row['identity'])
        resource=row.get('resource');stream=Path(row['rawPath']).parent/resource['file'] if resource and resource['status']=='exact_owner_archive_span' else None
        try:surface=read_surface(bodies[key],stream.read_bytes() if stream else None)
        except ValueError:continue # source audit retains the scoped diagnostic
        surfaces[key]=surface;descriptor=_obj(stage/('mesh_'+_name(key)+'.obj'),[(row['name'],surface,surface['vertices'],surface['submeshes'])])
        descriptor.update(schema=SCHEMA,submeshCount=len(surface['submeshes']),hasUV0=surface['uv0'] is not None,hasUV1=surface['uv1'] is not None)
        mesh_assets[key]=descriptor;row['asset']=descriptor
    for detail in report['materials']:
        row=detail['source'];key=scene_identity(row['identity']);name='material_'+_name(key)+'.json'
        # The complete stored document retains sampler UV-set indices and
        # fields omitted by dedicated Material JSON. No runtime shader claim.
        row['storedTextures']=[dict(property=t['property'],scale=t['scale'],offset=t['offset'],uvSet=t['uvSet'],
            reference={k:v for k,v in t['reference'].items() if k!='target'},
            **(dict(target=dict(identity=_public(t['reference']['target']['identity']),name=t['reference']['target']['name'],
                        classId=t['reference']['target']['classId'],rawSha256=t['reference']['target']['rawSha256'],
                        preview=t['reference']['target'].get('preview'))) if 'target' in t['reference'] else {})) for t in detail['textures']]
        write_json(stage/name,dict(schema='endfield.assets-stored-material.v2',identity=_public(row['identity']),rawSha256=row['rawSha256'],
            storedProperties=_public(bodies[key]),shader=_public(detail['shader']),textures=_public(detail['textures']),evidenceBoundary=report['evidenceBoundary']))
        descriptor=dict(rel=f'{SOURCE}/{name}',name=row['name'],sha256=hashlib.sha256((stage/name).read_bytes()).hexdigest())
        material_assets[key]=descriptor;row['asset']=descriptor
    # Resolve-pointer targets share the source rows, so mesh/material asset
    # links are attached only after every source was independently admitted.
    by_root=defaultdict(list);lods=defaultdict(list)
    for row in report['renderers']:by_root[tuple(row['trace']['chain'][-1]['gameObject'])].append(row)
    for group in report['lodGroups']:lods[tuple(group['trace']['chain'][-1]['gameObject'])].append(group)
    assemblies={};counts=dict(meshes=len(mesh_assets),materials=len(material_assets),assemblies=0,selectedMissing=0)
    for key,rows in sorted(by_root.items()):
        groups=lods[key];grouped={scene_identity(i) for g in groups for level in g['levels'] for i in level['renderers']}
        ordinals=range(max(len(g['levels']) for g in groups)) if groups else [None]
        descriptors=[]
        for ordinal in ordinals:
            chosen=set()
            if ordinal is not None:
                # A preview choice, never an assertion of camera-selected LOD.
                for group in groups:
                    if ordinal<len(group['levels']):chosen.update(scene_identity(i) for i in group['levels'][ordinal]['renderers'])
            selected=[r for r in rows if scene_identity(r['renderer']['identity']) not in grouped or scene_identity(r['renderer']['identity']) in chosen]
            parts=[];missing=0;disabled=inactive=overrides=0
            for row in selected:
                mesh=row['mesh'];mesh_key=scene_identity(mesh['target']['identity']) if mesh['status']=='exact_selected_target_identity' else None
                surface=surfaces.get(mesh_key)
                if surface is None or row['staticBatch']['subMeshCount']:
                    missing+=1;continue
                matrix=row['trace']['composedLocalMatrix'];flattened=[face for s in surface['submeshes'] for face in s['faces']]
                vertices,faces=transform_surface(surface['vertices'],flattened,matrix);submeshes=[];at=0
                for sub in surface['submeshes']:
                    count=len(sub['faces']);submeshes.append(dict(slot=sub['slot'],faces=faces[at:at+count]));at+=count
                renderer_key=scene_identity(row['renderer']['identity']);parts.append((f'renderer_{renderer_key[2]}_{renderer_key[3]:016X}',surface,vertices,submeshes))
                disabled+=not row['enabled'];inactive+=not all(n['active'] for n in row['trace']['chain'])
                overrides+=row['additionalVertexStreams'].get('status')!='null' or row['enlightenVertexStream'].get('status')!='null'
            counts['selectedMissing']+=missing
            if not parts:continue
            descriptor=_obj(stage/f'prefab_{_name(key)}_lod{ordinal if ordinal is not None else "none"}.obj',parts)
            descriptor.update(schema=SCHEMA,lodOrdinal=ordinal,rendererCount=len(parts),selectedMissingCount=missing,
                storedDisabledCount=disabled,storedInactiveCount=inactive,unappliedVertexStreamCount=overrides)
            descriptors.append(descriptor);counts['assemblies']+=1
        assemblies[key]=descriptors
    return dict(schema=SCHEMA,status='validated',sourceRoot=rel_path(stage,root),counts=counts,texturePreviews=texture_evidence,evidenceBoundary=BOUNDARY),assemblies
