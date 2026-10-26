"""Stage selected Animator repairs, with geometry and source-scope receipts.

Does not publish exports or WebUI data. The selection names expected geometry
instance counts from a source-declaration audit, including duplicate-path cases.
"""
from __future__ import annotations

import argparse,hashlib,json,subprocess,time
from pathlib import Path
from scripts.common import sha256_file,write_json
from scripts.game_data.extraction.unity_dependencies import builtin_files,builtin_inputs
from scripts.game_data.extraction.unity_overlay import effective_chunk_slot_keys,chunk_slot_key
from scripts.game_data.extraction.verify_export_freshness import Requirements,verify
from scripts.game_data.extraction.export_full_from_game import build_animestudio_object_index_cli_provenance
from scripts.game_data.fbx_inventory import read_inventory

SCHEMA='endfield.animator-repair-stage.v1'


def stage(selection,*,cli,game_root,export_root,work,report):
    if selection.get('schema')!='endfield.animator-repair-selection.v1':raise ValueError('unsupported Animator repair selection')
    if verify(game_root=game_root,output_root=export_root,requirements=Requirements(unity=('Animator',),asset_map=True)):
        raise ValueError('Animator/map source freshness failed')
    effective=effective_chunk_slot_keys(export_root)
    if effective is None:raise ValueError('effective source bundle catalogue is missing')
    cases=selection['cases'];names=set();groups={}
    for case in cases:
        name=case['output'];source=case['sourceCase'];path=Path(source['Source']).resolve()
        if Path(name).name!=name or not name.endswith('.fbx') or name in names:raise ValueError('unsafe or duplicate FBX output')
        names.add(name)
        if (not path.is_relative_to(game_root.resolve()/source['layer']) or not path.is_file()
                or chunk_slot_key(str(path),source['Offset']) not in effective):raise ValueError(f'unselected source bundle: {path}')
        if type(case['expectedGeometryInstances'])!=int or case['expectedGeometryInstances']<=0:raise ValueError('positive expected geometry count required')
        groups.setdefault((source['layer'],str(path)),[]).append(case)
    work.mkdir(parents=True,exist_ok=True);cli_provenance=build_animestudio_object_index_cli_provenance(cli)
    auxiliary=builtin_inputs(game_root);results=[];physical=[]
    result=dict(schema=SCHEMA,complete=False,cli=cli_provenance,auxiliaryInputs=auxiliary,cases=results,physicalInputs=physical,
                selectionSha256=hashlib.sha256(json.dumps(selection,sort_keys=True).encode()).hexdigest())
    for ordinal,((layer,source),rows) in enumerate(sorted(groups.items())):
        path=Path(source);stat=path.stat();physical.append(dict(path=source,bytes=stat.st_size,mtimeNs=stat.st_mtime_ns,sha256=sha256_file(path)))
        group=work/f'{ordinal:03d}';group.mkdir(parents=True,exist_ok=True);output=group/'output';manifest=group/'export.jsonl'
        selected=group/'selection.json';write_json(selected,[case['sourceCase'] for case in rows])
        other='StreamingAssets' if layer=='Persistent' else 'Persistent'
        args=[str(cli.resolve()),source,str(output.resolve()),'--game','ArknightsEndfield','--types','Animator','--names','^$',
              '--filter_data',str(selected.resolve()),'--export_type','Convert','--group_assets','ByType','--map_op','CABMap,Load',
              '--map_name','endfield_'+layer.lower()+'_assets','--cab_map_dir',str((export_root/'meta/cab_map').resolve()),
              '--fallback_cab_map',str((export_root/'meta/cab_map'/f'endfield_{other.lower()}_assets.bin').resolve()),
              '--export_manifest_jsonl',str(manifest.resolve()),'--no_model_textures','--logger_flags','Warning','Error']
        dependencies=builtin_files(game_root)
        if dependencies:args.extend(['--dependency_files',*(str(p) for p in dependencies)])
        write_json(group/'command.json',args);started=time.monotonic()
        with (group/'export.log').open('wb') as log:proc=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT)
        if proc.returncode:raise ValueError(f'Animator repair CLI failed: {group}; exit={proc.returncode}')
        entries=[json.loads(line) for line in manifest.read_text('utf8').splitlines()]
        if not entries or entries[-1].get('kind')!='summary' or not entries[-1].get('complete'):
            raise ValueError(f'incomplete repair export manifest: {manifest}')
        for case in rows:
            name=case['output'];target=output/'Animator'/name;owner=case['sourceCase']
            claimed=[r for r in entries if r.get('kind')=='output' and r.get('output')=='Animator/'+name
                     and r['pathId']==owner['PathID'] and Path(r['source']).resolve()==path and r['sourceOffset']==owner['Offset']]
            if not claimed or not target.is_file():
                results.append(dict(**case,status='not_exported',group=str(group)));continue
            with target.open('rb') as stream:inventory=read_inventory(stream,target.stat().st_size)
            count=inventory['geometryInstances'];expected=case['expectedGeometryInstances']
            valid=(count==expected and all(g.get('vertices',0)>0 and g.get('polygonVertexIndices',0)>0 for g in inventory['geometries']))
            results.append(dict(**case,status='validated' if valid else 'geometry_count_differs',path=str(target.resolve()),
                sha256=sha256_file(target),size=target.stat().st_size,geometryInstances=count,inventory=inventory,
                exportManifest=str(manifest),exportManifestSha256=sha256_file(manifest)))
        if (path.stat().st_size,path.stat().st_mtime_ns)!=(stat.st_size,stat.st_mtime_ns):raise ValueError('physical source changed during repair')
        write_json(report,result)
        print(f'Repair group {ordinal+1}/{len(groups)}: {len(rows)} models, {time.monotonic()-started:.1f}s; validated={sum(r["status"]=="validated" for r in results)}',flush=True)
    if builtin_inputs(game_root)!=auxiliary or build_animestudio_object_index_cli_provenance(cli)!=cli_provenance:
        raise ValueError('decoder or built-in resources changed during repair')
    result['complete']=True;write_json(report,result);return result


def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ('selection','cli','game-root','export-root','work','report'):parser.add_argument('--'+flag,type=Path,required=True)
    args=parser.parse_args();stage(json.loads(args.selection.read_bytes()),cli=args.cli,game_root=args.game_root,
        export_root=args.export_root,work=args.work,report=args.report)

if __name__=='__main__':
    if not __package__:raise SystemExit('Run as python -m scripts.game_data.extraction.animestudio.repair_models')
    main()
