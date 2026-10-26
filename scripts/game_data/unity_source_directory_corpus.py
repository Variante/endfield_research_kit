"""Admit complete selected Unity directories and declared raw object bodies.

An admitted scene supplies the current VFS/CLI gate. Additional physical Bundle
spans require the same selected ledger and current chunk hashes. A separate
sidecar extracts metadata, generic JSON/raw bodies and owner-archive spans;
independent readers recheck metadata EOF, body EOF/JSON and exact object census.
Saved derived directory/resource rows never authorize a join.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tempfile

from scripts.common import sha256_file,write_json
from scripts.game_data import unity_scene_corpus as scenes
from scripts.game_data.cooked_collision_corpus import _selected_ledger,_digest,_decoder_closure,_path_key
from scripts.game_data.extraction.animestudio.source_directory import build_helper,extract
from scripts.game_data.unity_serialized_directory import read_directory
from scripts.game_data.unity_type_tree import decode_object,check_json
from scripts.game_data.unity_mesh import decode_mesh,read_surface
from scripts.game_data.unity_scene import scene_identity
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.selected-unity-source-directory-corpus.v1'
DEFAULT_CLASSES=(21,23,33,43,142,205)


def source_selection(scene):
    return [dict(Source=r['identity']['sourceOriginalPath'],Offset=r['identity']['sourceOffset'],Cab=r['identity']['sourceFile'])
            for r in scene['rawSources'] if r['type']=='AssetBundle']


def admit_sources(scene,selection,*,root=REPO_ROOT):
    if not selection or len({(_path_key(r['Source']),r['Offset'],r['Cab']) for r in selection})!=len(selection):
        raise ValueError('directory selection is empty or contains duplicate source/CAB identities')
    for r in selection:
        if not re.fullmatch(r'CAB-[0-9a-fA-F]{32}(?:\.sharedAssets)?',r['Cab']) or type(r['Offset'])!=int or r['Offset']<0:
            raise ValueError('directory selection CAB/offset is unsupported')
    summary=Path(scene['provenance']['outerSummaryPath']);ledger=root/scene['provenance']['outerLedger']
    filtered=[dict(Source=r['Source'],Offset=r['Offset'],Type='AssetBundle',PathID=0) for r in selection]
    _,_,_,chunks=_selected_ledger(summary,ledger,filtered,scene['inputSetSha256'])
    previous={_path_key(r['path']):r for r in scene['extraction']['physicalInputs']};physical=[]
    scenes.check_receipt_snapshot(scene)
    for key,row in sorted(chunks.items()):
        path=Path(row['physicalChunkPath']);stat=path.stat()
        if key in previous:
            record=previous[key]
            if (stat.st_size!=record['length'] or stat.st_mtime_ns!=record['mtimeNs']
                    or record['md5']!=row['recomputedContentMd5']):
                raise ValueError(f'directory source differs from admitted scene chunk: {path}')
            digest=record['md5']
        else:
            digest=_digest(path,'md5')
        if stat.st_size!=row['actualPhysicalLength'] or digest!=row['recomputedContentMd5']:
            raise ValueError(f'directory physical source hash/length gate: source={path}; expected={row["actualPhysicalLength"]}/{row["recomputedContentMd5"]}; actual={stat.st_size}/{digest}')
        physical.append(dict(path=str(path),length=stat.st_size,mtimeNs=stat.st_mtime_ns,md5=digest))
    scenes.check_receipt_snapshot(scene);return physical


def inspect_exports(data_root,selection,classes,*,known_sources=()):
    manifest_path=data_root/'directory.json';manifest=json.loads(manifest_path.read_bytes())
    if manifest['schema']!='endfield.serialized-directory-extraction.v1':raise ValueError('unsupported directory sidecar schema')
    wanted={(_path_key(r['Source']),r['Offset'],r['Cab']) for r in selection}
    spans={k[:2] for k in wanted};seen=set();files={manifest_path.resolve()};directories=[];objects=[];decoded={};counts=Counter()
    known={scene_identity(r['identity']):r for r in known_sources}
    for row in manifest['directories']:
        key=(_path_key(row['source']),row['offset'],row['cab'])
        if key[:2] not in spans or key in seen:raise ValueError('directory sidecar source/CAB scope differs or duplicates a physical file')
        seen.add(key)
        meta_path=data_root/row['metadata']
        if not re.fullmatch(r'[0-9a-f]{64}\.metadata\.bin',row['metadata']):raise ValueError('directory metadata filename is unsupported')
        raw_meta=meta_path.read_bytes();files.add(meta_path.resolve())
        if hashlib.sha256(raw_meta).hexdigest()!=row['metadataSha256']:raise ValueError(f'directory metadata hash differs: {meta_path}')
        directory=read_directory(raw_meta,file_length=row['fileLength']);catalog={o['pathId']&((1<<64)-1):o for o in directory['objects']}
        if len(catalog)!=row['objectCount'] or [e['path'] for e in directory['externals']]!=row['externals']:
            raise ValueError(f'directory parsed census/external slots differ: {meta_path}')
        directory_source=dict(sourceOriginalPath=row['source'],sourceOffset=row['offset'],sourceFile=row['cab'],
            metadataPath=str(meta_path),metadataSha256=row['metadataSha256'],fileLength=row['fileLength'],directory=directory)
        directories.append(directory_source);found=set()
        for item in row['objects']:
            pid=item['pathId']&((1<<64)-1);info=catalog.get(pid)
            if (info is None or pid in found or item['classId'] not in classes or info['classId']!=item['classId']
                    or info['byteStart']!=item['byteStart'] or info['byteSize']!=item['byteSize']):
                raise ValueError(f'directory object class/span/census differs: source={meta_path}; PathID={pid}')
            found.add(pid);stem=item['stem']
            if not re.fullmatch(r'[0-9a-f]{64}_p[0-9A-F]{16}',stem):raise ValueError('directory object filename is unsupported')
            if stem!=row['metadata'].removesuffix('.metadata.bin')+f'_p{pid:016X}':
                raise ValueError('directory object filename differs from physical file/PathID')
            raw_path=data_root/(stem+'.dat');json_path=data_root/(stem+'.json');raw=raw_path.read_bytes();typed=json.loads(json_path.read_bytes())
            files.update((raw_path.resolve(),json_path.resolve()))
            if (len(raw)!=info['byteSize'] or hashlib.sha256(raw).hexdigest()!=item['rawSha256']
                    or sha256_file(json_path).lower()!=item['jsonSha256']):
                raise ValueError(f'directory body byte/hash gate: source={raw_path}; expectedBytes={info["byteSize"]}; actualBytes={len(raw)}')
            nodes=directory['types'][info['typeIndex']]['nodes']
            try:
                body=(decode_mesh if info['classId']==43 else decode_object)(nodes,raw);check_json(body,typed)
            except (ValueError,KeyError,TypeError,OverflowError) as error:
                raise ValueError(f'directory body EOF/JSON gate: source={raw_path}; classId={info["classId"]}; {error}') from error
            identity=dict(sourceOriginalPath=row['source'],sourceOffset=row['offset'],sourceFile=row['cab'],pathId=item['pathId'])
            object_key=scene_identity(identity);old=known.get(object_key)
            if old and old['rawSha256']!=item['rawSha256']:raise ValueError(f'directory body differs from admitted source object: {raw_path}')
            resource=item['resource'];stream=None
            if resource:
                descriptor=body['m_StreamData']
                if any(resource[f]!=descriptor[f] for f in ('path','offset','size')):raise ValueError('directory resource descriptor differs from independent body')
                if resource['status']=='exact_owner_archive_span':
                    if (resource['path']!=f'archive:/{row["cab"]}/{row["cab"]}.resS' or resource['offset']<0
                            or resource['offset']+resource['size']>resource['archiveStreamLength']
                            or resource['file']!=stem+'.stream.bin'):raise ValueError('directory resource is not an exact owner archive span')
                    path=data_root/resource['file'];stream=path.read_bytes();files.add(path.resolve())
                    if len(stream)!=resource['size'] or hashlib.sha256(stream).hexdigest()!=resource['sha256']:
                        raise ValueError(f'directory resource length/hash differs: {path}')
                elif resource['status'] not in ('empty','outside_owner_archive'):
                    raise ValueError('unsupported directory resource status')
                elif resource['status']=='empty' and resource['size']!=0:
                    raise ValueError('empty directory resource has nonzero length')
            elif body.get('m_StreamData',{}).get('size',0):
                raise ValueError('directory body has an unrecorded resource descriptor')
            record=dict(identity=identity,classId=info['classId'],byteStart=info['byteStart'],byteSize=info['byteSize'],
                rawPath=str(raw_path),jsonPath=str(json_path),rawSha256=item['rawSha256'],jsonSha256=item['jsonSha256'],
                name=body.get('m_Name',''),resource=resource)
            if info['classId']==43:
                try:
                    surface=read_surface(body,stream)
                    record['surface']=dict(status='complete',vertexCount=surface['vertexCount'],triangleCount=surface['triangleCount'],
                        submeshCount=len(surface['submeshes']),hasUV0=surface['uv0'] is not None,hasUV1=surface['uv1'] is not None)
                except ValueError as error:
                    record['surface']=dict(status='unavailable',diagnostic=str(error)[:800])
                counts['renderSurfaces']+=record['surface']['status']=='complete'
            decoded[object_key]=body;objects.append(record);counts[str(info['classId'])]+=1
        expected={pid for pid,info in catalog.items() if info['classId'] in classes}
        if found!=expected:raise ValueError(f'directory declared-class body census differs: {meta_path}; expected={len(expected)}; actual={len(found)}')
    if not wanted.issubset(seen):raise ValueError('selected physical CABs are missing from directory sidecar')
    if files!={p.resolve() for p in data_root.iterdir() if p.is_file()}:raise ValueError('directory artifact file census differs')
    for key,row in known.items():
        physical=(_path_key(row['identity']['sourceOriginalPath']),key[1],key[2])
        if physical not in seen:continue
        source=next(d for d in directories if (_path_key(d['sourceOriginalPath']),d['sourceOffset'],d['sourceFile'])==physical)
        candidates=[o for o in source['directory']['objects'] if o['pathId']&((1<<64)-1)==key[3]]
        meta=json.loads(Path(row['jsonPath']).read_bytes())['$animestudio']
        if (len(candidates)!=1 or candidates[0]['byteSize']!=row['byteSize'] or candidates[0]['classId']!=meta['classId']):
            raise ValueError('admitted source object class/span differs from complete serialized directory')
    return dict(schema=SCHEMA,status='complete',failures=[],directories=directories,objects=objects,
                counts=dict(counts,directories=len(directories),declaredObjects=sum(len(d['directory']['objects']) for d in directories)),
                evidenceBoundary='Complete selected serialized header/metadata directories and ordered external slots, authenticated physical VFS spans, independently decoded declared-class raw/JSON bodies through EOF and exact owner-archive resource ranges. Object identity and stored render buffers do not establish runtime resolver selection, activation, world placement, draw participation or material appearance.'),decoded,files


def collect(scene_receipt,*,work_root,selection=None,classes=DEFAULT_CLASSES,admitted_scene=None):
    scene_receipt=scene_receipt.resolve();scene=admitted_scene or scenes.validate_receipt(scene_receipt)
    if (scene.get('schema')!='endfield.selected-unity-scene-corpus.v4' or scene.get('status')!='complete'
            or scene.get('failures') or str(scene_receipt) not in scene['currentInputSnapshots']):
        raise ValueError('source collection requires its currently admitted complete parent scene')
    scenes.check_receipt_snapshot(scene)
    selection=selection or source_selection(scene);physical=admit_sources(scene,selection)
    work_root.mkdir(parents=True,exist_ok=True);run=Path(tempfile.mkdtemp(prefix='directories-',dir=work_root.resolve()))
    path=run/'selection.json';write_json(path,selection);cli=Path(scene['extraction']['command'][0])
    helper=build_helper(cli,run/'helper');extraction=extract(helper,cli,path,run/'data',classes)
    write_json(run/'producer.json',dict(inputSetSha256=scene['inputSetSha256'],sceneReceipt=str(scene_receipt),sceneReceiptSha256=sha256_file(scene_receipt),
        selection=dict(path=str(path),sha256=sha256_file(path),classes=sorted(classes)),
        extraction=dict(**extraction,logSha256=sha256_file(Path(extraction['log'])),helper=helper,physicalInputs=physical,
                        decoderOutputClosure=scene['extraction']['decoderOutputClosure'])))
    report,_,_=inspect_exports(run/'data',selection,classes,known_sources=scene['rawSources'])
    report.update(inputSetSha256=scene['inputSetSha256'],sceneReceipt=str(scene_receipt),sceneReceiptSha256=sha256_file(scene_receipt),
        selection=dict(path=str(path),sha256=sha256_file(path),classes=sorted(classes)),
        extraction=dict(**extraction,logSha256=sha256_file(Path(extraction['log'])),helper=helper,physicalInputs=physical,
                        decoderOutputClosure=scene['extraction']['decoderOutputClosure']))
    scenes.check_receipt_snapshot(scene)
    for row in physical:
        stat=Path(row['path']).stat()
        if (stat.st_size,stat.st_mtime_ns)!=(row['length'],row['mtimeNs']):raise ValueError('directory physical source changed during collection')
    return report


def validate_receipt(path,scene,*,root=REPO_ROOT):
    original=path.read_bytes();saved=json.loads(original)
    if (saved.get('schema')!=SCHEMA or saved.get('status')!='complete' or saved.get('failures')
            or saved['inputSetSha256']!=scene['inputSetSha256'] or saved['sceneReceipt'] not in scene['currentInputSnapshots']
            or sha256_file(Path(saved['sceneReceipt']))!=saved['sceneReceiptSha256']):raise ValueError('source directory receipt/base scene admission differs')
    selection_path=Path(saved['selection']['path']);selection=json.loads(selection_path.read_bytes());classes=saved['selection']['classes']
    if sha256_file(selection_path)!=saved['selection']['sha256']:raise ValueError('source directory selection hash differs')
    physical=admit_sources(scene,selection,root=root)
    if physical!=saved['extraction']['physicalInputs']:raise ValueError('source directory physical source receipt differs')
    extraction=saved['extraction'];helper=extraction['helper'];cli=Path(scene['extraction']['command'][0]);log=Path(extraction['log'])
    run=selection_path.parent;data_root=run/'data'
    expected=[helper['sdk'],helper['binary'],str(cli.parent.resolve()),str(selection_path.resolve()),str(data_root.resolve()),','.join(map(str,sorted(classes)))]
    if (extraction['command']!=expected or log!=run/'data.log' or log.stat().st_size or sha256_file(log)!=extraction['logSha256']
            or _decoder_closure(Path(helper['binary']))!=helper['closure']
            or _decoder_closure(cli)!=extraction['decoderOutputClosure']
            or extraction['decoderOutputClosure']!=scene['extraction']['decoderOutputClosure']):raise ValueError('source directory producer/command/log/CLI gate differs')
    paths={path.resolve(),selection_path,log}
    paths.update(p for p in data_root.iterdir() if p.is_file());paths.update(Path(r['path']) for r in physical)
    paths.update(p for p in Path(helper['binary']).parent.rglob('*') if p.is_file())
    snapshots={str(p):(p.stat().st_size,p.stat().st_mtime_ns) for p in paths}
    current,decoded,_=inspect_exports(data_root,selection,classes,known_sources=scene['rawSources'])
    if current['objects']!=saved['objects'] or path.read_bytes()!=original:raise ValueError('source directory object receipts or receipt changed')
    scenes.check_receipt_snapshot(scene);current['currentInputSnapshots']=snapshots;scenes.check_receipt_snapshot(current)
    current['inputSetSha256']=scene['inputSetSha256'];return current,decoded


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scene-receipt',type=Path,required=True)
    parser.add_argument('--selection',type=Path)
    parser.add_argument('--work-root',type=Path,default=REPO_ROOT/'tmp/animestudio/source_directories')
    parser.add_argument('--output-json',type=Path,default=REPO_ROOT/'reports/assets/source_directories_current.json')
    args=parser.parse_args(argv)
    if not args.output_json.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('generated receipts belong under reports/')
    try:
        report=collect(args.scene_receipt,work_root=args.work_root,selection=json.loads(args.selection.read_bytes()) if args.selection else None)
        write_json(args.output_json,report);print('Selected source directories:',report['status'],report['counts'],flush=True);return 0
    except (OSError,ValueError,KeyError,TypeError,OverflowError) as error:
        print('Selected source directory gate failed:',str(error)[:1600],flush=True);return 1


if __name__=='__main__':
    if not __package__:raise SystemExit('Run as python -m scripts.game_data.unity_source_directory_corpus')
    raise SystemExit(main())
