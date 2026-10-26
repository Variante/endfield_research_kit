"""Project admitted stored render components beside exact collision owners."""
from __future__ import annotations

from collections import Counter

from scripts.game_data.unity_render_corpus import SCHEMA as CORPUS_SCHEMA
from scripts.game_data.unity_render_resources import SCHEMA as RESOURCE_SCHEMA
from scripts.webui.assets.collision_runtime import object_key, variant_key
from scripts.webui.assets.collision_prefabs import _root_key

SCHEMA='endfield.assets-collision-renderers.v3'


def _identity(value):
    key=object_key(value)
    return {**value,'pathId':str(key[1]),'sourceOffset':str(value['sourceOffset'])}


def _pointer(reference):
    result={k:v for k,v in reference.items() if k!='target'}
    if 'target' in reference:
        target=reference['target']
        result['target']=dict(identity=_identity(target['identity']),**{k:target[k] for k in ('rawSha256','name','classId','surface','asset','storedTextures') if k in target})
    return result


def project_renderers(entries,scenes,report,*,assemblies=None):
    if report.get('schema') not in (CORPUS_SCHEMA,RESOURCE_SCHEMA) or report.get('status')!='complete' or report.get('failures'):
        raise ValueError('stored renderer corpus was not admitted')
    variants={variant_key(e['cl']):e for e in entries if 'cl' in e}
    if len(variants)!=sum('cl' in e for e in entries):
        raise ValueError('duplicate collision variant in renderer projection')
    groups={};seen={};unlinked=set();memberships={}
    for group in report.get('lodGroups',[]):
        for level in group['levels']:
            for identity in level['renderers']:
                memberships.setdefault(object_key(identity),[]).append(dict(groupIdentity=_identity(group['source']['identity']),
                    ordinal=level['ordinal'],screenRelativeHeight=level['screenRelativeHeight'],groupEnabled=group['enabled']))
    for scene in scenes:
        for row in scene['colliders']:
            if row['status']!='exact_serialized_collider_link' or not row.get('prefabAssets'):
                continue
            if len(row['geometry'])!=1:raise ValueError('renderer projection needs one selected cooked buffer')
            item=row['geometry'][0];mesh=row['mesh']
            key=(*object_key(mesh['identity']),item['kind'],mesh['rawSha256'],item['sha256'])
            if key not in variants:continue
            root=_root_key(row['trace']);paths={p['path'] for p in row['prefabAssets']}
            group=groups.setdefault(root,dict(paths=set(),variants=set(),records=[]))
            group['paths'].update(paths);group['variants'].add(key)
    for row in report['renderers']:
        identity=object_key(row['renderer']['identity']);root=_root_key(row['trace'])
        if identity in seen:
            if seen[identity]!=row:raise ValueError('conflicting stored renderer observations')
            continue
        seen[identity]=row;group=groups.get(root)
        if group is None or not row['prefabPaths']:
            unlinked.add(identity);continue
        if not set(row['prefabPaths']).issubset(group['paths']):
            raise ValueError('renderer declared prefab paths differ from admitted collision root')
        group['records'].append(dict(identity=_identity(row['renderer']['identity']),
            rawSha256=row['renderer']['rawSha256'],
            meshFilter=dict(identity=_identity(row['meshFilter']['identity']),rawSha256=row['meshFilter']['rawSha256']) if row['meshFilter'] else None,
            hierarchy=[dict(name=n['name'],active=n['active']) for n in reversed(row['trace']['chain'])],
            enabled=row['enabled'],mesh=_pointer(row['mesh']),materials=[_pointer(p) for p in row['materials']],staticBatch=row['staticBatch'],
            lodMemberships=memberships.get(identity,[]),
            additionalVertexStreams=_pointer(row['additionalVertexStreams']),enlightenVertexStream=_pointer(row['enlightenVertexStream'])))
    assembly_rows={object_key(dict(sourceOriginalPath=k[0],sourceOffset=k[1],sourceFile=k[2],pathId=k[3])):v
                   for k,v in (assemblies or {}).items()}
    links={};all_records=[]
    for root,group in sorted(groups.items()):
        if not group['records']:continue
        all_records.extend(group['records'])
        descriptor=dict(prefabPaths=sorted(group['paths']),rootIdentity=dict(sourceFile=root[0],pathId=str(root[1]),
            sourceOriginalPath=root[2],sourceOffset=str(root[3])),records=group['records'],
            renderAssemblies=assembly_rows.get(root,[]))
        for key in group['variants']:links.setdefault(key,[]).append(descriptor)
    for entry in entries:
        if 'cl' in entry:entry['cl'].pop('renderers',None)
    for key,rows in links.items():variants[key]['cl']['renderers']=dict(schema=SCHEMA,prefabs=rows)
    return dict(schema=SCHEMA,status='validated',counts=dict(linkedVariants=len(links),
        prefabRoots=sum(bool(g['records']) for g in groups.values()),rendererBindings=len(all_records),
        materialSlots=sum(len(r['materials']) for r in all_records),unlinkedRenderers=len(unlinked)),
        meshStatuses=dict(Counter(r['mesh']['status'] for r in all_records)),
        materialStatuses=dict(Counter(p['status'] for r in all_records for p in r['materials'])),
        evidenceBoundary=report['evidenceBoundary'])
