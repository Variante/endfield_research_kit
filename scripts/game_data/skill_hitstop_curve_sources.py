"""Offline HitStop field and exported keyed-curve evidence, without library admission.

This reader consumes a completed Skill intake receipt. It does not re-run the
native derivation, select a DataManager configuration object, evaluate a Unity
curve or infer runtime hit-stop delivery. Names bind only inside one explicitly
selected exported dictionary document.
"""
from __future__ import annotations
import copy
import argparse
import math
import hashlib
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs
from scripts.game_data.string_pool import StringPool
from scripts.game_data.levelscript_reader_inputs import snapshot_string_pool_inputs
from scripts.game_data.memorypack.skill_timeline_current_sequence import encoded_tag
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.unity_store import UnityObjectStore
from scripts.game_data.extraction.unity_overlay import iter_asset_map_rows

SCHEMA='endfield.skill-hitstop-curve-sources.v1'
TYPE='Beyond.Gameplay.Core.HitStopAction+Data'


def need(check,condition):
    if not condition:raise ValueError('skillHitStopCurveSources.'+check)


def check_selected_native(contract,*,gameassembly,metadata):
    """Optional fresh selected-byte gate; does not derive or admit a library."""
    pins=contract['nativeInputs']
    return check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],
        gameassembly=Path(gameassembly),metadata=Path(metadata))


def extract_fields(export_root,receipt,summary,consumer_contract):
    """Bind pool/curve records to accepted route-owned byte ranges only."""
    root=Path(export_root).resolve()
    need('complete-receipt',receipt.get('status')=='stored-complete'and receipt.get('nativeOperationExitPassed')is True)
    need('consumer-contract-identity',consumer_contract.get('schema')=='endfield.skill-action-timing-consumers-native-contract.v1'
        and consumer_contract.get('status')=='reviewed')
    pins=receipt['native']['nativeInputs']
    need('recorded-consumer-build',all(pins.get(key)==value for key,value in consumer_contract['nativeInputs'].items()))
    need('recorded-timing-audit',receipt.get('timingNativeAudit',{}).get('status')=='validated')
    by_id={row['identifier']:row for row in receipt['skills']};out=[]
    need('distinct-skill-sources',len(by_id)==len(receipt['skills']))
    need('distinct-summary-sources',len({row['identifier']for row in summary['skills']})==len(summary['skills']))
    pool_before=snapshot_string_pool_inputs(root/'game/Json')
    pool=StringPool(root/'game/Json/StringPool');used_pages=set();source_bytes={}
    for selected in summary['skills']:
        skill=by_id[selected['identifier']];source=skill['source']
        need('complete-skill',skill.get('status')=='stored-complete'and skill.get('nativeOperationExitPassed')is True
            and skill['decoded'].get('wholeSkillDataExact')is True)
        path=root/'game/Json/SkillData'/(skill['identifier']+'.json')
        need('source-path',Path(source['path']).resolve()==path)
        raw=path.read_bytes();source_bytes[path]=raw;need('source-content',len(raw)==source['size']and hashlib.sha256(raw).hexdigest()==source['sha256'])
        need('summary-source',selected['source']==source)
        routes=[r for r in skill['routePrograms']if r.get('wrappedType')==TYPE and r.get('family')=='AbilityActionData']
        need('one-owned-route',len(routes)==1)
        named=[(r['fieldName'],r['kind'])for r in routes[0]['reads']]
        need('owned-curve-read-order',named[6:9]==[('curveKey','byte-payload'),('directCurve','curve-profile'),('duration','float32-bits')])
        records=skill['decoded']['records'];ranges=skill['decoded']['byteRanges'];seen_actions=set()
        for action in selected['actions']:
            if action.get('role')!='hit-stop-declaration':continue
            need('owned-action-type',action.get('typeName')==TYPE and action.get('wrapperNull')is False)
            a,z=action['start'],action['end']
            need('action-range',type(a)is int and type(z)is int and 0<=a<z<=len(raw))
            need('distinct-action-source',(a,z)not in seen_actions);seen_actions.add((a,z))
            unions=[r for r in records if r.get('kind')=='union'and r.get('start')==a and r.get('end')==z]
            need('one-owned-union-record',len(unions)==1)
            tag=routes[0]['tag'];tag_bytes=encoded_tag(tag);tag_end=a+len(tag_bytes)
            need('action-union-tag',unions[0].get('tag')==tag and raw[a:tag_end]==tag_bytes
                and('tag'not in action or type(action['tag'])is int and action['tag']==tag))
            need('action-member-header',raw[tag_end]==routes[0]['memberCount'])
            need('union-tag-range',{'start':a,'end':tag_end,'kind':'union-tag'}in ranges)
            need('union-header-range',{'start':tag_end,'end':tag_end+1,'kind':'member-header'}in ranges)
            curves=[r for r in records if r.get('kind')=='unity-animation-curve'and a<=r['start']<r['end']<=z]
            need('one-direct-curve-record',len(curves)==1);curve=curves[0];start=curve['start']
            keys=[r for r in records if r.get('kind')=='anonymous-byte-payload'and r['start']==start-4 and r['end']==start]
            need('one-adjacent-owned-pool-record',len(keys)==1);key=keys[0]
            need('attacker-to-curve-key-boundary',any(r.get('kind')=='anonymous-target-profile'and a<=r['start']and r['end']==key['start']for r in records))
            index=struct.unpack_from('<i',raw,key['start'])[0]
            need('pool-record-value',index==key['poolIndex']);text=pool.resolve(index)
            if index>=0:used_pages.add(index//pool.page_size)
            # The present admitted five-Skill input has only empty direct curves.
            # A future nonempty source must use the maintained Keyframe codec;
            # this focused reader refuses rather than inventing its wire shape.
            need('empty-direct-curve-record',curve['keyCount']==0 and curve['end']-start==13 and raw[start]==3)
            pre,post,count=struct.unpack_from('<iii',raw,start+1)
            need('curve-byte-count',count==0)
            for offset,kind in ((start+1,'UnityEngine.AnimationCurve.preWrapMode'),(start+5,'UnityEngine.AnimationCurve.postWrapMode')):
                need('curve-field-range',any(r=={'start':offset,'end':offset+4,'kind':kind}for r in ranges))
            durations=[f for f in action['fields']if f['fieldName']=='duration']
            direct=[f for f in action['fields']if f['fieldName']=='useDirectCurve']
            need('following-owned-duration',len(durations)==1 and durations[0].get('kind')=='float32-bits'
                and type(durations[0].get('start'))is int and type(durations[0].get('end'))is int
                and durations[0]['start']==curve['end']and durations[0]['end']==curve['end']+4)
            duration_start=durations[0]['start'];duration_end=durations[0]['end']
            need('duration-owned-range',{'start':duration_start,'end':duration_end,'kind':TYPE+'.duration.float32-bits'}in ranges)
            duration_bits=raw[duration_start:duration_end].hex();duration_value=struct.unpack_from('<f',raw,duration_start)[0]
            need('duration-summary-bits',durations[0].get('value')=={'bitsHex':duration_bits})
            if 'storedFloat32Value'in durations[0]:
                supplied=durations[0]['storedFloat32Value']
                need('duration-summary-float',type(supplied)in(int,float)and math.isfinite(supplied)
                    and math.isfinite(duration_value)and supplied==duration_value)
            need('owned-direct-switch',len(direct)==1 and direct[0].get('kind')=='bool-byte'
                and type(direct[0].get('start'))is int and direct[0]['start']==z-1 and direct[0].get('end')==z
                and raw[z-1]in(0,1)and type(direct[0].get('value'))is bool
                and direct[0]['value']==bool(raw[z-1]))
            need('direct-switch-owned-range',{'start':z-1,'end':z,'kind':TYPE+'.useDirectCurve.bool-byte'}in ranges)
            duration=dict(start=duration_start,end=duration_end,kind='float32-bits',bitsHex=duration_bits,
                value=duration_value if math.isfinite(duration_value)else None,
                floatClass='finite'if math.isfinite(duration_value)else('nan'if math.isnan(duration_value)else'infinity'))
            out.append(dict(identifier=skill['identifier'],actionStart=a,actionEnd=z,tag=tag,
                curveKey=dict(start=key['start'],end=start,poolIndex=index,value=text),
                directCurve=dict(start=start,end=curve['end'],keyCount=0,preWrapMode=pre,postWrapMode=post),
                useDirectCurve=direct[0]['value'],source=copy.deepcopy(source),duration=duration))
    pages=[]
    for page in sorted(used_pages):
        path=(pool.root/('StringPool'+str(page)+'.byte')).resolve()
        selected=[row for row in pool_before['files']if row['path']==path.as_posix()]
        need('used-pool-page-in-entry-snapshot',len(selected)==1)
        pages.append(copy.deepcopy(selected[0]))
    need('pool-source-bookend',pool_before==snapshot_string_pool_inputs(root/'game/Json'))
    for path,expected in source_bytes.items():need('skill-source-bookend',expected==path.read_bytes())
    return dict(schema=SCHEMA,fields=out,stringPoolPages=pages,stringPoolInputs=pool_before,recordedNativeInputs=copy.deepcopy(pins),
        nativeAdmissionGranted=False,selectedLibraryProved=False,runtimeExecutionProved=False,
        sourceBoundary='Skill bytes match completed intake hashes. Pool names are resolved from the explicitly selected export pages whose current hashes are retained; the receipt contains no saved pool-page hashes for an independent historical pool join.')


def _store_identity(export_root):
    store_path=Path(export_root).resolve()/'game/Unity.sqlite';result=[]
    for path in (store_path,Path(str(store_path)+'-wal'),Path(str(store_path)+'-journal')):
        if path.is_file():
            stat=path.stat();result.append((path.as_posix(),stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns))
    return result


def _asset_map_paths(export_root):
    root=Path(export_root)
    return sorted(path for layer in ('StreamingAssets','Persistent')
        for path in (root/'meta'/layer/'asset_map').glob('*.json'))


def _asset_map_inputs(export_root):
    result=[]
    for path in _asset_map_paths(export_root):
        digest=hashlib.sha256();length=0
        with path.open('rb')as stream:
            for block in iter(lambda:stream.read(1<<20),b''):
                length+=len(block);digest.update(block)
        result.append(dict(path=path.resolve().as_posix(),length=length,sha256=digest.hexdigest()))
    return result


def _asset_map_bindings(export_root,header):
    before=_asset_map_inputs(export_root);bindings=[]
    original=header.get('sourceOriginalPath');offset=header.get('sourceOffset');path_id=header['pathId']
    def normalized(path):return path.replace('\\','/').casefold()
    for source in before:
        for row in iter_asset_map_rows(Path(source['path'])):
            if(row.get('Type')!='MonoBehaviour'or type(row.get('PathID'))is not int or row['PathID']!=path_id):continue
            if(type(original)is not str or type(row.get('Source'))is not str or normalized(row['Source'])!=normalized(original)):continue
            if type(offset)is not int or type(row.get('Offset'))is not int or row['Offset']!=offset:continue
            need('asset-map-container',type(row.get('Container'))is str and bool(row['Container']))
            bindings.append(dict(assetMap=source['path'],entry=copy.deepcopy(row),
                objectSourceFile=header['sourceFile'],join='Exact physical source path + source offset + PathID + MonoBehaviour type'))
    need('asset-map-bookend',before==_asset_map_inputs(export_root))
    return before,bindings


def read_exported_curve_library(export_root,object_name,keys):
    """Exact keyed rows in one exported object; never promotes its selection."""
    root=Path(export_root).resolve()
    before=_store_identity(root);store=UnityObjectStore.for_export(root);rows=store.rows_by_object_name('MonoBehaviour',object_name)
    need('one-explicit-exported-object',len(rows)==1);row=rows[0]
    raw=store.read_bytes('MonoBehaviour',row.name)
    need('stored-document-hash',hashlib.sha256(raw).hexdigest()==row.sha256)
    value=json.loads(raw);header=value['$animestudio']
    need('object-identity',(header['pathId'],header['sourceFile'])==(row.path_id,row.source_file))
    dictionary=value['hitSopSettings'];names=dictionary['_keyData'];values=dictionary['_valueData']
    need('parallel-dictionary-vectors',type(names)is list and type(values)is list and len(names)==len(values)
        and all(type(key)is str for key in names)and len(names)==len(set(names)))
    selected=[]
    for key in keys:
        need('requested-key-present',key in names);index=names.index(key);curve=values[index]['timeScaleCurve']
        need('curve-shape',set(curve)=={'m_Curve','m_PreInfinity','m_PostInfinity','m_RotationOrder'}and type(curve['m_Curve'])is list)
        selected.append(dict(key=key,index=index,curve=copy.deepcopy(curve)))
    map_inputs,map_bindings=_asset_map_bindings(root,header)
    need('library-object-bookend',rows==store.rows_by_object_name('MonoBehaviour',object_name)
        and raw==store.read_bytes('MonoBehaviour',row.name))
    need('library-store-bookend',before==_store_identity(root))
    return dict(logicalPath='game/Unity/MonoBehaviour/'+row.name,pathId=row.path_id,sourceFile=row.source_file,
        documentSha256=row.sha256,serializedRawSha256=header['rawDataSha256'],curves=selected,storeInputs=before,
        assetMapInputs=map_inputs,assetMapBindings=map_bindings,
        assetMapBindingStatus='exact-exported-object-map-join'if map_bindings else'unresolved',
        selectedLibraryProved=False,nativeAdmissionGranted=False,
        evidenceBoundary='Exact serialized dictionary/curve rows in the explicit exported object. Runtime DataManager-selected asset identity, selection and Unity curve evaluation are not granted by this read.')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--intake',type=Path,required=True)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--export-root',type=Path,required=True)
    parser.add_argument('--library-object',required=True)
    parser.add_argument('--consumer-contract',type=Path,default=CONTRACTS_DIR/'skill_action_timing_consumers_native.json')
    parser.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_hitstop_curve_sources.json')
    args=parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):parser.error('--output must be below reports/')
    paths=(args.intake,args.summary,args.consumer_contract)
    before={path:path.read_bytes()for path in paths}
    receipt,summary,contract=(json.loads(before[path])for path in paths)
    result=extract_fields(args.export_root,receipt,summary,contract)
    keys=sorted({row['curveKey']['value']for row in result['fields']})
    need('literal-library-keys',all(type(key)is str and key for key in keys))
    result['libraryCandidate']=read_exported_curve_library(args.export_root,args.library_object,keys)
    for path,raw in before.items():need('report-or-contract-bookend',raw==path.read_bytes())
    # Final cross-reader bookends also catch changes during the later library
    # read; the individual readers already protect their own read intervals.
    need('pool-operation-bookend',result['stringPoolInputs']==snapshot_string_pool_inputs(args.export_root/'game/Json'))
    for source in {row['source']['path']:row['source']for row in result['fields']}.values():
        current=Path(source['path']).read_bytes()
        need('skill-operation-bookend',len(current)==source['size']and hashlib.sha256(current).hexdigest()==source['sha256'])
    need('library-operation-bookend',result['libraryCandidate']['storeInputs']==_store_identity(args.export_root))
    need('asset-map-operation-bookend',result['libraryCandidate']['assetMapInputs']==_asset_map_inputs(args.export_root))
    result['inputs']=[dict(path=path.resolve().as_posix(),sha256=hashlib.sha256(raw).hexdigest())for path,raw in before.items()]
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps(dict(status='structural-source-candidates',actions=len(result['fields']),
        curves=len(result['libraryCandidate']['curves']),selectedLibraryProved=False,nativeAdmissionGranted=False)))
    return 0


if __name__=='__main__':raise SystemExit(main())
