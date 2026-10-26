"""Admit stored render components within a selected prefab scene receipt.

Stored renderer/filter ownership and material slot order are exact. External
slots may reuse witnesses from the same admitted physical serialized file;
unwitnessed slots remain unresolved. Resource bodies outside the original
scene scope and runtime draw/appearance are not claimed by this supplement.


Evidence and admission boundary
-------------------------------
Exact admission uses the shared supplement producer/source/census gates and
reviewed field paths plus an independent EOF reader. Renderer and MeshFilter
must share a reciprocal GameObject and a complete chain to the declared physical
prefab root; a missing filter is a gap. Dedicated JSON lacks PPtr witnesses and
omits the final Enlighten stream, whose raw tail remains authoritative. An
external slot may reuse a checked MeshCollider witness only from that same
physical file, with raw pointer, CAB/path and source hashes checked. Missing
witnesses, excluded bodies and ambiguous CABs remain distinct. Other Renderer
classes are outside scope; exact Mesh identity alone is not render geometry.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from scripts.common import write_json
from scripts.game_data import unity_scene_corpus as scenes, unity_scene_supplement as supplement
from scripts.game_data.unity_render import layouts, read_render_object, check_typed
from scripts.game_data.unity_scene import local_target, scene_identity, read_scene_object, trace_component
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.selected-unity-render-corpus.v1'
TYPES = ('MeshFilter','MeshRenderer','AssetBundle')


def _slot_witnesses(scene):
    """A slot belongs to its physical file, regardless of which component uses it."""
    slots = {}
    for row in scene['rawSources']:
        if row['type']!='MeshCollider':
            continue
        key=scene_identity(row['identity']);raw=Path(row['rawPath']).read_bytes()
        typed=Path(row['jsonPath']).read_bytes()
        if (hashlib.sha256(raw).hexdigest()!=row['rawSha256']
                or hashlib.sha256(typed).hexdigest().upper()!=row['jsonSha256'].upper()):
            raise ValueError(f"renderer external-slot witness changed: {row['jsonPath']}")
        document=json.loads(typed);meta=document['$animestudio'];body=read_scene_object('MeshCollider',raw)
        if scene_identity(meta)!=key:
            raise ValueError('renderer external-slot witness physical identity differs')
        scenes._check_typed(body,document,'MeshCollider')
        pointer=body['mesh']
        if not pointer[0] or not pointer[1]:
            continue
        # This validates the referring raw pointer and the ordered external
        # slot's CAB/path witness even when the target CAB isn't selected.
        scenes._external_mesh_target(key,pointer,meta,{})
        witness=next(r for r in meta['pptrReferences'] if r['path']=='$.m_Mesh')
        cab=witness['expectedTargetSourceFile'];slot=(*key[:3],pointer[0])
        if slot in slots and slots[slot]['cab']!=cab:
            raise ValueError('conflicting physical serialized external-slot witnesses')
        identity=row['identity']
        slots[slot]=dict(cab=cab,identity={**identity,'pathId':str(key[3]),'sourceOffset':str(key[1])},
                         rawSha256=row['rawSha256'])
    return slots


def pointer_reference(key, pointer, sources, slots, expected_type):
    result=dict(fileId=pointer[0],pathId=str(pointer[1]&((1<<64)-1)))
    if not pointer[1]:
        return dict(result,status='null')
    if pointer[0]==0:
        target=local_target(key,pointer)
    else:
        witness=slots.get((*key[:3],pointer[0]))
        if witness is None:
            return dict(result,status='external_slot_unwitnessed')
        result.update(expectedCab=witness['cab'],slotWitness=witness)
        locations={k[:3] for k in sources if k[2]==witness['cab']}
        if len(locations)>1:
            return dict(result,status='external_physical_target_ambiguous')
        if not locations:
            return dict(result,status='external_target_outside_selection')
        target=(*next(iter(locations)),pointer[1]&((1<<64)-1))
    row=sources.get(target)
    if row is None:
        return dict(result,status='target_body_outside_selection')
    if row['type']!=expected_type:
        raise ValueError(f'renderer {expected_type} PPtr selects admitted {row["type"]} object')
    identity=row['identity']
    return dict(result,status='exact_selected_target_identity',
                target=dict(identity={**identity,'pathId':str(target[3]),'sourceOffset':str(target[1])},
                            rawSha256=row['rawSha256'],name=row.get('name','')))


def inspect_exports(run,scene):
    sources,documents,bodies,prefab_roots=supplement.inspect_sources(run,scene,TYPES)
    reviewed=layouts();counts=Counter();filters={}
    for key,source in sources.items():
        kind=source['type']
        if kind=='AssetBundle':continue
        doc,raw=documents[key];meta=doc['$animestudio'];layout=reviewed[kind]
        if (meta['classId']!=layout['classId'] or meta.get('typeTreeSource')!='serializedType'
                or meta.get('typeTreeFieldPaths')!=layout['fieldPaths']):
            raise ValueError(f"{kind} serialized layout differs: {source['jsonPath']}")
        try:
            body=read_render_object(kind,raw);check_typed(body,doc,kind)
            bodies[key]=dict(body,gameObject=body['m_GameObject'],kind=kind)
            counts[kind]+=1
            if kind=='MeshFilter':
                trace=trace_component(key,bodies)
                filters[key]=dict(source=source,body=body,trace=trace)
            else:
                counts['omittedEnlightenFields']+=('m_EnlightenVertexStream' not in doc)
                counts['nonNullEnlightenStreams']+=bool(body['m_EnlightenVertexStream'][1])
        except (ValueError,KeyError,TypeError,OverflowError) as error:
            raise ValueError(f"renderer body/hierarchy gate: source={source['jsonPath']}; {error}") from error
    known={scene_identity(r['identity']):r for r in scene['rawSources']}
    known.update(sources);slots=_slot_witnesses(scene);rows=[]
    for key,source in sorted(sources.items()):
        if source['type']!='MeshRenderer':continue
        body=bodies[key]
        try:
            trace=trace_component(key,bodies);game_key=tuple(trace['gameObject'])
            matched=[local_target(game_key,p) for p in bodies[game_key]['components']
                     if local_target(game_key,p) in filters]
            if len(matched)>1:
                raise ValueError('renderer GameObject declares multiple available MeshFilters')
            filter_row=filters.get(matched[0]) if matched else None
            if filter_row and tuple(filter_row['trace']['gameObject'])!=game_key:
                raise ValueError('renderer/MeshFilter GameObject backlinks differ')
            mesh=(pointer_reference(matched[0],filter_row['body']['m_Mesh'],known,slots,'Mesh')
                  if filter_row else dict(status='mesh_filter_unavailable'))
            materials=[pointer_reference(key,p,known,slots,'Material') for p in body['m_Materials']]
            paths=sorted(prefab_roots.get(tuple(trace['chain'][-1]['gameObject']),[]))
            rows.append(dict(renderer=source,meshFilter=filter_row['source'] if filter_row else None,
                trace=trace,prefabPaths=paths,enabled=body['m_Enabled'],mesh=mesh,materials=materials,
                staticBatch=body['m_StaticBatchInfo'],
                additionalVertexStreams=pointer_reference(key,body['m_AdditionalVertexStreams'],known,slots,'Mesh'),
                enlightenVertexStream=pointer_reference(key,body['m_EnlightenVertexStream'],known,slots,'Mesh')))
            counts['prefabLinkedRenderers']+=bool(paths)
            counts['renderersWithoutMeshFilter']+=filter_row is None
            counts['materialSlots']+=len(materials)
        except (ValueError,KeyError,TypeError) as error:
            raise ValueError(f"renderer ownership gate: source={source['jsonPath']}; {error}") from error
    return dict(schema=SCHEMA,status='complete',failures=[],renderers=rows,rawSources=list(sources.values()),
                counts=dict(counts),meshStatuses=dict(Counter(r['mesh']['status'] for r in rows)),
                materialStatuses=dict(Counter(p['status'] for r in rows for p in r['materials'])),
                evidenceBoundary='Exact selected raw/typed renderer and MeshFilter fields, reciprocal GameObject/TRS hierarchy, declared physical prefab roots and ordered stored material PPtrs. External slots reuse only authenticated witnesses from the same physical serialized file. A selected target identity is not decoded render geometry or material appearance. Unwitnessed/excluded resource bodies, other renderer classes, live activation, world placement, draw participation and shader selection remain unresolved.')


def collect(scene_receipt,*,work_root):
    return supplement.collect(scene_receipt,work_root=work_root,prefix='renderers-',types=TYPES,inspect=inspect_exports)


def validate_receipt(path,scene):
    return supplement.validate_receipt(path,scene,schema=SCHEMA,types=TYPES,inspect=inspect_exports)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-receipt',type=Path,required=True)
    parser.add_argument('--work-root',type=Path,default=REPO_ROOT/'tmp/animestudio/collision_renderers')
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/assets/collision_renderers_current.json')
    args=parser.parse_args(argv)
    if not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('generated receipts belong under reports/')
    try:
        report=collect(args.scene_receipt,work_root=args.work_root);write_json(args.output_json,report)
        print('Stored render component corpus:',report['status'],report['counts'])
        print('Mesh references:',report['meshStatuses'],'Material references:',report['materialStatuses'])
        return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as error:
        print('Stored render component corpus failed:',str(error)[:1600]);return 1


if __name__=='__main__':
    if not __package__:raise SystemExit('Run as python -m scripts.game_data.unity_render_corpus')
    raise SystemExit(main())
