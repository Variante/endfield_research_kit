"""Publish validated staged Animator repairs without rebuilding other Assets data."""
from __future__ import annotations

import argparse,hashlib,json,os,time
from collections import Counter
from pathlib import Path
from scripts.common import rel_path,sha256_file,write_json,path_id_export_base_stem
from scripts.game_data.extraction.animestudio.repair_models import SCHEMA
from scripts.game_data.extraction.export_full_from_game import build_animestudio_object_index_cli_provenance
from scripts.game_data.extraction.unity_dependencies import builtin_inputs
from scripts.game_data.extraction.verify_export_freshness import Requirements,verify
from scripts.game_data.fbx_normalize import normalize_fbx,fbx_content_fingerprints,FBX_CONTENT_SCHEMA,FBX_VARIANT_SCHEMA
from scripts.game_data.unity_store import UnityObjectStore,UnityObjectStoreWriter
from scripts.source_paths import ExportLayout
from scripts.webui.assets.fbx_root import read_fbx_root_names_from_bytes


def atomic_json(path,payload):
    temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')),encoding='utf8')
    os.replace(temporary,path)


def update_index(payload,prepared,incomplete):
    """Keep unrelated entries and sidecar headers byte-equivalent as values."""
    by_ref={entry['r']:entry for entry in payload['entries']}
    for row in prepared:
        reference='Unity/Animator/'+row['output'];entry=by_ref.get(reference)
        if entry is None:
            entry=dict(k='model',r=reference);payload['entries'].append(entry);by_ref[reference]=entry
        entry.update(s=row['size'],h=row['normalizedSha256'],pid=f"{row['sourceCase']['PathID']&((1<<64)-1):016X}")
        container=row['sourceCase'].get('Container')
        if container and not entry.get('c'):entry['c']=container
        entry.pop('fr',None)
        if len(row['roots'])==1 and row['roots'][0]!=(path_id_export_base_stem(Path(row['output']).stem) or Path(row['output']).stem):entry['fr']=row['roots'][0]
        entry.pop('mr',None);entry.pop('d',None);entry.pop('fc',None);entry.pop('fv',None)
        if row['fc']:entry.update(fc=row['fc'],fv=row['fv'])
    for reference,recovery in incomplete.items():
        if reference in by_ref:by_ref[reference].update(h=recovery['h'],mr=recovery)
    counts=Counter(entry.get('fc') for entry in payload['entries'] if entry.get('fc'))
    for entry in payload['entries']:
        if entry.get('fc') and counts[entry['fc']]<2:entry.pop('fc',None);entry.pop('fv',None)
    kind_counts=Counter(entry['k'] for entry in payload['entries'])
    payload['counts'].update(total=len(payload['entries']),**kind_counts)
    payload.update(generated=int(time.time()),fbxContentSchema=FBX_CONTENT_SCHEMA,fbxVariantSchema=FBX_VARIANT_SCHEMA)


def check_source_snapshot(receipt,game_root):
    for source in receipt['physicalInputs']:
        path=Path(source['path']);stat=path.stat()
        if not path.resolve().is_relative_to(game_root.resolve()) or (stat.st_size,stat.st_mtime_ns)!=(source['bytes'],source['mtimeNs']):
            raise ValueError('physical repair source snapshot changed')


def publish(*,root,export_root,asset_dir,stage_report,cli,game_root,work):
    receipt=json.loads(stage_report.read_bytes())
    if receipt.get('schema')!=SCHEMA or not receipt.get('complete'):raise ValueError('incomplete or unsupported repair receipt')
    if build_animestudio_object_index_cli_provenance(cli)!=receipt['cli']:raise ValueError('repair decoder closure differs')
    if builtin_inputs(game_root)!=receipt['auxiliaryInputs']:raise ValueError('repair Unity resources differ')
    if verify(game_root=game_root,output_root=export_root,requirements=Requirements(unity=('Animator',),asset_map=True)):
        raise ValueError('repair source freshness failed')
    check_source_snapshot(receipt,game_root)
    index_path=asset_dir/'index.json';before=index_path.read_bytes();payload=json.loads(before)
    if payload.get('root')!=rel_path(export_root,root) or payload.get('mode')=='webui':raise ValueError('repair publication requires selected broad index')
    layout=ExportLayout(export_root);provenance_path=layout.extraction_provenance_path;provenance_before=provenance_path.read_bytes()
    provenance=json.loads(provenance_before)
    animator=(provenance.get('unity') or {}).get('Animator')
    if not isinstance(animator,dict):raise ValueError('explicit Animator provenance is required for resource dependency publication')
    animator['auxiliaryInputs']=receipt['auxiliaryInputs']
    work.mkdir(parents=True,exist_ok=True);normalized=work/'normalized';normalized.mkdir(exist_ok=True)
    store=UnityObjectStore.for_export(export_root);prepared=[];incomplete={};backups={};new_count=0;changed=0
    names=set();indexed={row['r']:row for row in payload['entries']}
    for ordinal,case in enumerate(receipt['cases']):
        name=case['output']
        if Path(name).name!=name or not name.endswith('.fbx') or name in names:raise ValueError('unsafe or duplicate repair output')
        names.add(name)
        baseline=case['baseline']
        if baseline['name'] not in (name,name+'.empty.json'):raise ValueError('repair baseline does not name the selected model or its empty marker')
        old=store.row('Animator',baseline['name'])
        if old is None or old.sha256!=baseline['sha256']:raise ValueError(f'canonical repair baseline changed: {name}')
        reference='Unity/Animator/'+name
        if baseline['name']==name:
            entry=indexed.get(reference)
            if entry is None or entry.get('s')!=old.size or (entry.get('h') and entry['h']!=old.sha256):
                raise ValueError(f'published repair baseline changed: {name}')
        elif reference in indexed or store.row('Animator',name) is not None:
            raise ValueError(f'recovered model already exists: {name}')
        if case['status']!='validated':
            if case['status'] not in ('not_exported','geometry_count_differs'):raise ValueError(f'unknown repair status: {case["status"]}')
            if baseline['name']==name:
                with store.open_document('Animator',name) as stream:
                    from scripts.game_data.fbx_inventory import read_inventory
                    actual=read_inventory(stream,old.size)['geometryInstances']
                incomplete[reference]=dict(status='incomplete_geometry',h=old.sha256,expected=case['expectedGeometryInstances'],exported=actual)
            continue
        source=Path(case['path']);manifest=Path(case['exportManifest'])
        if sha256_file(source)!=case['sha256'] or sha256_file(manifest)!=case['exportManifestSha256']:
            raise ValueError(f'staged repair artifact differs: {name}')
        data=normalize_fbx(source.read_bytes());digest=hashlib.sha256(data).hexdigest()
        stem=path_id_export_base_stem(Path(name).stem) or Path(name).stem
        fc,fv=fbx_content_fingerprints(data,stem)
        if not fc or not fv:raise ValueError(f'repaired FBX comparison framing failed: {name}')
        path=normalized/name;path.write_bytes(data)
        roots=read_fbx_root_names_from_bytes(data)
        prepared.append(dict(output=name,path=str(path),normalizedSha256=digest,size=len(data),fc=fc,fv=fv,roots=roots,
            sourceCase=case['sourceCase'],baseline=baseline))
        if baseline['name']!=name:new_count+=1
        if old.sha256!=digest or old.name!=name:
            backups[old.name]=old;changed+=1
        if (ordinal+1)%100==0:print(f'Validated repair publication {ordinal+1}/{len(receipt["cases"])}',flush=True)
    if index_path.read_bytes()!=before:raise ValueError('Assets index changed during repair preparation')
    # Back up every affected stored document and both publication headers before
    # changing canonical rows. The snapshot is a normal deduplicated Unity store.
    backup_path=work/'before-Unity.sqlite'
    if backup_path.exists():raise ValueError('repair backup already exists; choose a fresh work directory')
    with UnityObjectStoreWriter(backup_path,jobs=1) as backup:
        for name,row in backups.items():
            data=store.read_bytes('Animator',name)
            if hashlib.sha256(data).hexdigest()!=row.sha256:raise ValueError(f'backup source differs: {name}')
            backup.put('Animator',name,data,mtime_ns=row.mtime_ns)
    (work/'before-index.json').write_bytes(before)
    (work/'before-provenance.json').write_bytes(provenance_before)
    update_index(payload,prepared,incomplete)
    write_json(work/'prepared.json',prepared)
    if index_path.read_bytes()!=before or provenance_path.read_bytes()!=provenance_before:
        raise ValueError('publication headers changed during preparation')
    check_source_snapshot(receipt,game_root)
    store.close()
    writer=UnityObjectStoreWriter(layout.unity_store_path,jobs=1)
    try:
        for row in prepared:
            writer.put('Animator',row['output'],Path(row['path']).read_bytes(),mtime_ns=time.time_ns())
            if row['baseline']['name']!=row['output']:writer.delete('Animator',[row['baseline']['name']])
    except Exception:
        writer.connection.rollback();raise
    finally:writer.close()
    if index_path.read_bytes()!=before or provenance_path.read_bytes()!=provenance_before:
        raise ValueError('publication headers changed concurrently; stored repairs are backed up; re-index against the current publication')
    atomic_json(provenance_path,provenance);atomic_json(index_path,payload)
    report=dict(schema='endfield.assets-fbx-repair-publication.v1',validated=len(prepared),changed=changed,newModels=new_count,
        incomplete=incomplete,backup=str(backup_path),stageReceiptSha256=sha256_file(stage_report),
        entries=[dict(output=r['output'],sha256=r['normalizedSha256'],size=r['size']) for r in prepared])
    write_json(work/'publication.json',report);return report


def main():
    parser=argparse.ArgumentParser(description=__doc__.splitlines()[0])
    for flag in ('root','export-root','asset-dir','stage-report','cli','game-root','work'):parser.add_argument('--'+flag,type=Path,required=True)
    parser.add_argument('--report',type=Path,help='Optional generated publication receipt under reports/')
    args=parser.parse_args();result=publish(root=args.root,export_root=args.export_root,asset_dir=args.asset_dir,
        stage_report=args.stage_report,cli=args.cli,game_root=args.game_root,work=args.work)
    if args.report:write_json(args.report,result)
    print(json.dumps({k:v for k,v in result.items() if k!='entries'},ensure_ascii=False),flush=True)

if __name__=='__main__':
    if not __package__:raise SystemExit('Run as python -m scripts.webui.assets.fbx_repair')
    main()
