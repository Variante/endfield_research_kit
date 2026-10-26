"""Compose admitted render components with complete physical source directories.

PPtrs select their own file's ordered external table, then a unique physical
CAB/object in the admitted directory selection. CABMap is a location hint for
additional extraction, never the ownership witness. Runtime selection, world
instances and effective material/shader behavior remain separate.
"""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path

from scripts.common import write_json,sha256_file
from scripts.game_data import unity_scene_corpus as scenes,unity_render_corpus as renderers,unity_source_directory_corpus as sources
from scripts.game_data.cabmap import ROOT_MAPS,parse_cabmap
from scripts.game_data.cooked_collision_corpus import _path_key
from scripts.game_data.unity_scene import scene_identity,read_scene_object,trace_component
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.stored-render-resource-joins.v1'


def directory_key(row):
    return scene_identity(dict(sourceOriginalPath=row['sourceOriginalPath'],sourceOffset=row['sourceOffset'],sourceFile=row['sourceFile'],pathId=0))[:3]


def resolve_pointer(owner,pointer,directories,objects,expected_class):
    file_id,pid=pointer;pid&=((1<<64)-1)
    result=dict(fileId=file_id,pathId=str(pid))
    if not pid:return dict(result,status='null')
    source=directories.get(owner[:3])
    if source is None:raise ValueError('resource pointer owner lacks an admitted physical directory')
    if file_id==0:target_file=owner[:3]
    elif file_id>0:
        slots=source['directory']['externals']
        if file_id>len(slots):raise ValueError(f'resource pointer file slot {file_id} exceeds referring table of {len(slots)}')
        slot=slots[file_id-1];cab=slot['fileName']
        result.update(expectedCab=cab,externalPath=slot['path'],externalMetadataOffset=slot['metadataOffset'],
                      referringMetadataSha256=source['metadataSha256'])
        candidates=[key for key in directories if key[2]==cab]
        if len(candidates)!=1:
            return dict(result,status='external_directory_unavailable' if not candidates else 'external_physical_target_ambiguous')
        target_file=candidates[0]
    else:raise ValueError('negative resource pointer file slot')
    candidates=[r for r in directories[target_file]['directory']['objects'] if r['pathId']&((1<<64)-1)==pid]
    if not candidates:return dict(result,status='target_absent_from_complete_directory')
    if len(candidates)!=1:raise ValueError('duplicate resource target in complete directory')
    info=candidates[0]
    if expected_class is not None and info['classId']!=expected_class:raise ValueError(f'resource pointer target class differs: expected={expected_class}; actual={info["classId"]}; CAB={target_file[2]}; PathID={pid}')
    identity=dict(sourceOriginalPath=target_file[0],sourceOffset=target_file[1],sourceFile=target_file[2],pathId=pid)
    target=objects.get((*target_file,pid))
    if target is None:return dict(result,status='exact_directory_target_body_unselected',target=dict(identity=identity,classId=info['classId']))
    return dict(result,status='exact_selected_target_identity',target=target)


def _pointer(value):return value['m_FileID'],value['m_PathID']


def join_resources(scene,render_report,source_reports,decoded_bodies):
    directories={};objects={}
    for report in source_reports:
        if report.get('schema')!=sources.SCHEMA or report.get('status')!='complete' or report.get('failures'):
            raise ValueError('render resource source directory was not admitted')
        for row in report['directories']:
            key=directory_key(row)
            if key in directories and directories[key]['metadataSha256']!=row['metadataSha256']:raise ValueError('conflicting physical source metadata')
            directories[key]=row
        for row in report['objects']:
            key=scene_identity(row['identity'])
            if key in objects and objects[key]['rawSha256']!=row['rawSha256']:raise ValueError('conflicting physical source object bytes')
            objects[key]=row
    roots={tuple(r['trace']['chain'][-1]['gameObject']) for r in scene['colliders'] if r.get('prefabAssets')}
    selected=[r for r in render_report['renderers'] if tuple(r['trace']['chain'][-1]['gameObject']) in roots]
    rows=[];missing=set();material_rows={};mesh_rows={}
    for row in selected:
        renderer_key=scene_identity(row['renderer']['identity']);source=objects.get(renderer_key)
        if source is None or source['rawSha256']!=row['renderer']['rawSha256']:raise ValueError('render resource source differs from admitted renderer')
        body=decoded_bodies[renderer_key];filter_source=row['meshFilter']
        if filter_source:
            filter_key=scene_identity(filter_source['identity']);target=objects.get(filter_key)
            if target is None or target['rawSha256']!=filter_source['rawSha256']:raise ValueError('render resource source differs from admitted MeshFilter')
            mesh=resolve_pointer(filter_key,_pointer(decoded_bodies[filter_key]['m_Mesh']),directories,objects,43)
        else:mesh=dict(status='mesh_filter_unavailable')
        materials=[resolve_pointer(renderer_key,_pointer(p),directories,objects,21) for p in body['m_Materials']]
        for reference in [mesh,*materials]:
            if reference['status']=='external_directory_unavailable':missing.add(reference['expectedCab'])
            if reference['status']=='exact_selected_target_identity':
                target=reference['target'];key=scene_identity(target['identity'])
                if target['classId']==43:mesh_rows[key]=target
                elif target['classId']==21:material_rows[key]=target
        rows.append(dict(row,mesh=mesh,materials=materials))
    material_details=[]
    for key,row in sorted(material_rows.items()):
        body=decoded_bodies[key]
        shader=resolve_pointer(key,_pointer(body['m_Shader']),directories,objects,48)
        textures=[]
        for env in body['m_SavedProperties']['m_TexEnvs']:
            value=env['Value'];reference=resolve_pointer(key,_pointer(value['m_Texture']),directories,objects,None)
            textures.append(dict(property=env['Key'],reference=reference,scale=value['m_Scale'],offset=value['m_Offset'],uvSet=value['m_UVSetIndex']))
        material_details.append(dict(source=row,shader=shader,textures=textures,
            validKeywords=body['m_ValidKeywords'],invalidKeywords=body['m_InvalidKeywords'],
            customRenderQueue=body['m_CustomRenderQueue'],doubleSidedGI=body['m_DoubleSidedGI']))
    # LOD memberships come from actual stored group PPtrs, not _lodN names.
    bodies={scene_identity(r['identity']):dict(read_scene_object(r['type'],Path(r['rawPath']).read_bytes()),kind=r['type'])
            for r in scene['rawSources'] if r['type'] in ('GameObject','Transform')}
    groups=[];selected_renderers={scene_identity(r['renderer']['identity']) for r in rows}
    for key,source in objects.items():
        if source['classId']!=205:continue
        body=decoded_bodies[key];bodies[key]=dict(kind='LODGroup',gameObject=_pointer(body['m_GameObject']))
        trace=trace_component(key,bodies);root=tuple(trace['chain'][-1]['gameObject'])
        if root not in roots:continue
        levels=[]
        for ordinal,level in enumerate(body['m_LODs']):
            members=[];unavailable=[]
            for member in level['renderers']:
                ref=resolve_pointer(key,_pointer(member['renderer']),directories,objects,None)
                if ref['status']=='exact_selected_target_identity':
                    target_key=scene_identity(ref['target']['identity'])
                    if target_key in selected_renderers:
                        owner=next(r for r in rows if scene_identity(r['renderer']['identity'])==target_key)
                        if tuple(owner['trace']['chain'][-1]['gameObject'])!=root:raise ValueError('LODGroup/renderer physical prefab roots differ')
                        members.append(ref['target']['identity'])
                    else:unavailable.append(dict(status='outside_admitted_mesh_renderer_scope',reference=ref))
                else:unavailable.append(ref)
            levels.append(dict(ordinal=ordinal,screenRelativeHeight=level['screenRelativeHeight'],fadeTransitionWidth=level['fadeTransitionWidth'],renderers=members,unavailableMembers=unavailable))
        if any(level['renderers'] for level in levels):groups.append(dict(source=source,trace=trace,enabled=body['m_Enabled'],levels=levels))
    return dict(schema=SCHEMA,status='complete',failures=[],renderers=rows,materials=material_details,meshes=list(mesh_rows.values()),lodGroups=groups,
        missingCabs=sorted(missing),counts=dict(renderers=len(rows),materials=len(material_details),meshes=len(mesh_rows),lodGroups=len(groups),
            resolvedMeshReferences=sum(r['mesh']['status']=='exact_selected_target_identity' for r in rows),
            resolvedMaterialSlots=sum(p['status']=='exact_selected_target_identity' for r in rows for p in r['materials'])),
        meshStatuses=dict(Counter(r['mesh']['status'] for r in rows)),materialStatuses=dict(Counter(p['status'] for r in rows for p in r['materials'])),
        evidenceBoundary='Exact stored render-to-Mesh/material PPtrs through the referring complete external table and unique physical directory/object in the admitted source selection; material properties and LOD membership are stored definitions. CABMap only locates additional extraction candidates. Effective runtime loading, LOD selection, shader variants, deformation, world placement and draw participation remain unresolved.')


def locate_cabs(cabs,scene,*,cabmap_dir):
    candidates={cab:[] for cab in cabs};inputs=[]
    for root,name in ROOT_MAPS.items():
        path=cabmap_dir/name;raw=path.read_bytes();base,entries=parse_cabmap(raw)
        inputs.append(dict(path=str(path.resolve()),sha256=sha256_file(path)))
        for entry in entries:
            if entry.cab in candidates:candidates[entry.cab].append(dict(Source=str((Path(base)/entry.path).resolve()),Offset=entry.offset,Cab=entry.cab))
    wanted={(_path_key(r['Source']),r['Offset']) for values in candidates.values() for r in values};active=set()
    with gzip.open(REPO_ROOT/scene['provenance']['outerLedger'],'rt',encoding='utf-8') as source:
        for line in source:
            row=json.loads(line)
            if row.get('recordType')=='file' and row.get('status')=='verified' and row.get('boundaryStatus')=='boundary_verified' and row.get('physicalChunkPath'):
                key=(_path_key(row['physicalChunkPath']),row['offset'])
                if key in wanted:active.add(key)
    selection=[];gaps=[]
    for cab,values in candidates.items():
        filtered={(_path_key(r['Source']),r['Offset']):r for r in values if (_path_key(r['Source']),r['Offset']) in active}
        if len(filtered)==1:selection.append(next(iter(filtered.values())))
        else:gaps.append(dict(cab=cab,status='locator_missing_active_span' if not filtered else 'locator_ambiguous_active_spans',candidates=list(filtered.values())))
    return sorted(selection,key=lambda r:(r['Source'],r['Offset'],r['Cab'])),gaps,inputs


def audit(scene_receipt,render_receipt,source_receipts):
    scene=scenes.validate_receipt(scene_receipt.resolve());render=renderers.validate_receipt(render_receipt.resolve(),scene)
    admissions=[];decoded={}
    for path in source_receipts:
        report,bodies=sources.validate_receipt(path,scene);admissions.append(report)
        for key,body in bodies.items():
            if key in decoded and decoded[key]!=body:raise ValueError('conflicting independently decoded resource bodies')
            decoded[key]=body
    result=join_resources(scene,render,admissions,decoded)
    scenes.check_receipt_snapshot(scene);scenes.check_receipt_snapshot(render)
    for report in admissions:scenes.check_receipt_snapshot(report)
    return result,scene,render,admissions,decoded


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-receipt',type=Path,required=True);parser.add_argument('--render-receipt',type=Path,required=True)
    parser.add_argument('--source-receipt',type=Path,action='append',required=True)
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/assets/render_resources_current.json')
    parser.add_argument('--dependency-selection',type=Path,default=REPO_ROOT/'reports/assets/render_resource_dependency_selection.json')
    parser.add_argument('--cabmap-dir',type=Path,default=REPO_ROOT/'export_full/meta/cab_map')
    parser.add_argument('--collect-dependencies',action='store_true',help='Collect located Mesh/material CAB dependencies as a separate static source receipt, then recompute joins.')
    parser.add_argument('--dependency-receipt',type=Path,default=REPO_ROOT/'reports/assets/source_directories_dependencies_current.json')
    parser.add_argument('--collect-material-resources',action='store_true',help='Collect shader/texture target directories after Mesh/material ownership is resolved.')
    parser.add_argument('--material-resource-receipt',type=Path,default=REPO_ROOT/'reports/assets/source_directories_material_resources_current.json')
    args=parser.parse_args(argv)
    if any(not p.resolve().is_relative_to((REPO_ROOT/'reports').resolve()) for p in (args.output_json,args.dependency_selection,args.dependency_receipt,args.material_resource_receipt)):
        parser.error('generated resource audits/selections belong under reports/')
    try:
        result,scene,render,admissions,decoded=audit(args.scene_receipt,args.render_receipt,args.source_receipt)
        selection,gaps,inputs=locate_cabs(result['missingCabs'],scene,cabmap_dir=args.cabmap_dir)
        write_json(args.dependency_selection,selection)
        if args.collect_dependencies and selection:
            print('Collecting located resource CABs:',len(selection),flush=True)
            fresh=sources.collect(args.scene_receipt,work_root=REPO_ROOT/'tmp/animestudio/source_directories',
                                  selection=selection,classes=(21,43,142),admitted_scene=scene)
            write_json(args.dependency_receipt,fresh)
            admission,bodies=sources.validate_receipt(args.dependency_receipt.resolve(),scene)
            admissions.append(admission);decoded.update(bodies);args.source_receipt.append(args.dependency_receipt)
            result=join_resources(scene,render,admissions,decoded)
            scenes.check_receipt_snapshot(scene);scenes.check_receipt_snapshot(render)
            for report in admissions:scenes.check_receipt_snapshot(report)
        if args.collect_material_resources:
            refs=[m['shader'] for m in result['materials']]+[t['reference'] for m in result['materials'] for t in m['textures']]
            missing={p['expectedCab'] for p in refs if p['status']=='external_directory_unavailable'}
            material_selection,material_gaps,material_inputs=locate_cabs(missing,scene,cabmap_dir=args.cabmap_dir)
            material_selection.extend(dict(Source=p['target']['identity']['sourceOriginalPath'],Offset=p['target']['identity']['sourceOffset'],
                Cab=p['target']['identity']['sourceFile']) for p in refs if p['status']=='exact_directory_target_body_unselected')
            material_selection=list({(_path_key(r['Source']),r['Offset'],r['Cab']):r for r in material_selection}.values())
            if material_selection:
                print('Collecting shader/texture resource CABs:',len(material_selection),flush=True)
                fresh=sources.collect(args.scene_receipt,work_root=REPO_ROOT/'tmp/animestudio/source_directories',selection=material_selection,
                    classes=(28,48,89),admitted_scene=scene)
                write_json(args.material_resource_receipt,fresh)
                admission,bodies=sources.validate_receipt(args.material_resource_receipt.resolve(),scene)
                admissions.append(admission);decoded.update(bodies);args.source_receipt.append(args.material_resource_receipt)
                result=join_resources(scene,render,admissions,decoded)
                for report in admissions:scenes.check_receipt_snapshot(report)
            result['materialLocatorGaps']=material_gaps;result['materialLocatorInputs']=material_inputs
        result.update(locatorGaps=gaps,locatorInputs=inputs,dependencySelection=str(args.dependency_selection),
            receipts=dict(scene=str(args.scene_receipt.resolve()),render=str(args.render_receipt.resolve()),sources=[str(p.resolve()) for p in args.source_receipt]))
        write_json(args.output_json,result)
        print('Stored render resources:',result['counts'],'missing target CABs:',len(result['missingCabs']),'located:',len(selection),'locator gaps:',len(gaps),flush=True)
        return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as error:
        print('Stored render resource gate failed:',str(error)[:1600],flush=True);return 1


if __name__=='__main__':
    if not __package__:raise SystemExit('Run as python -m scripts.game_data.unity_render_resources')
    raise SystemExit(main())
