"""Join fresh typed pooled FMV owners to current verified Video names.

Requires the current v2 LevelScript family receipt, including complete reader,
StringPool, selected raw chunks and logical export joins. Every operation
replays its selected owners; saved positive schema/native results are not cached.
The output is conditional source/name evidence and never unused-cutscene safety.
"""
import argparse,gzip,hashlib,json
from pathlib import Path
from scripts.common import check_installed_native_inputs,write_report_json
from scripts.game_data.levelscript_fmv_video_native import validate,CONTRACT_PATH,SCHEMA
from scripts.game_data.levelscript_corpus import verify_family_receipt,DEFAULT_OUTPUT,_guard_output
from scripts.game_data.levelscript_binary import frame_levelscript_named
from scripts.game_data.levelscript_null_list_param_native import current_null_list_params
from scripts.game_data.levelscript_source_receipts import SourceReader
from scripts.game_data.codecs.levelscript import fmv
from scripts.game_data.memorypack.corpus_gate import _fingerprint,_chunk_selection_snapshot,_chunk_fingerprints
from scripts.repo_paths import REPO_ROOT

REPORT_SCHEMA='endfield.levelscript-fmv-video-join.v2'
DEFAULT_REPORT=REPO_ROOT/'reports/story/recovery/current_levelscript_fmv_video_join.json'

def _require(ok,check,source,**detail):
 if not ok:
  error=ValueError(check+':'+str(source)+':'+json.dumps(detail,sort_keys=True)[:1400]);error.diagnostic=dict(validator='levelscript_fmv_video_corpus',check=check,source=str(source),**detail);raise error

def _video_rows(path,input_set,wanted):
 found={}
 with gzip.open(path,'rt',encoding='utf-8')as stream:
  for line in stream:
   r=json.loads(line);name=r.get('virtualPath')
   if r.get('recordType')!='file'or name not in wanted:continue
   _require(name not in found,'duplicate-video-path',name)
   _require((r.get('blockName'),r.get('status'),r.get('boundaryStatus'),r.get('inputSetSha256'))==('Video','verified','boundary_verified',input_set),'video-ledger-row',name,actual={k:r.get(k)for k in('blockName','status','boundaryStatus','inputSetSha256')})
   _require(r.get('fileNameHashDeclaredHex')==r.get('fileNameHashRecomputedHex')and r.get('declaredFileDataMd5LittleEndianHex')==r.get('recomputedFileDataMd5'),'video-ledger-hash-joins',name)
   found[name]=r
 return found

def _video_bytes(row):
 path=Path(row['physicalChunkPath']);at,n=row['offset'],row['length'];_require(row.get('encrypted')is False and type(at)is int and type(n)is int and 0<=at and 0<n<=path.stat().st_size-at,'video-raw-slice',row['virtualPath'])
 with path.open('rb')as stream:stream.seek(at);raw=stream.read(n)
 actual=hashlib.md5(raw).hexdigest().upper();_require(len(raw)==n and actual==row['recomputedFileDataMd5'].upper(),'current-video-data-md5',row['virtualPath'],expected=row['recomputedFileDataMd5'],actual=actual)
 return dict(path=row['virtualPath'],length=n,dataMd5=actual,fileNameHash=row['fileNameHashRecomputedHex'],physicalChunkPath=str(path),physicalChunkSource=row['physicalChunkSource'])

def audit(*,expected_input_set_sha256,expected_family_receipt_sha256,family_receipt_path=DEFAULT_OUTPUT,export_root=REPO_ROOT/'export_full',game_root=None,sources=None,contract_path=CONTRACT_PATH):
 gate=validate(game_root=game_root,contract_path=contract_path);_require(gate.get('status')=='validated','native-name-programs',contract_path,actual=gate)
 export_root=Path(export_root);receipt_path=Path(family_receipt_path)
 def receipt():return verify_family_receipt(receipt_path,expected_sha256=expected_family_receipt_sha256,expected_input_set_sha256=expected_input_set_sha256,export_root=export_root)
 before=receipt();_require((before.get('format'),before.get('schemaVersion'))==('endfield-levelscript-current-corpus-v2',2),'current-pooled-family-receipt-required',receipt_path)
 pins=gate['nativeInputs'];pair=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=Path(game_root).parent/'GameAssembly.dll'if game_root is not None else None,metadata=Path(game_root)/'il2cpp_data/Metadata/global-metadata.dat'if game_root is not None else None);_require(pair.status=='validated','selected-native-inputs',game_root,actual=pair.status,detail=pair.detail);selected_root=Path(pair.metadata).parents[2]
 provenance=before['provenance'];outer=json.loads(Path(provenance['outer']['path']).read_bytes());_require(all(Path(outer[k]).resolve()==(selected_root/folder).resolve()for k,folder in(('primaryAssets','Persistent'),('fallbackAssets','StreamingAssets'))),'selected-native-vfs-roots',selected_root)
 source=SourceReader(dict(status='complete',provenance=dict(levelscriptReaderInputs=provenance['readerInputs'],levelscriptStringPoolInputs=provenance['levelscriptStringPoolInputs'])),export_root/'game/Json',pins,game_root=selected_root)
 universe={r['exportRelativePath']:r for r in before['rows']if r['family']=='LevelScriptData'};selected=sorted(universe)if sources is None else sorted(set(sources));_require(bool(selected)and all(p in universe for p in selected),'selected-owner-source-set',receipt_path,selected=selected[:8],unknown=sorted(set(selected)-set(universe))[:8])
 projected=[];failures=[];files={};owners=0
 with current_null_list_params(game_root=selected_root,strings=source.strings)as null_list_params:
  for path in selected:
   file=source.root/path;data=file.read_bytes();digest=hashlib.sha256(data).hexdigest().upper();logical=universe[path];_require([len(data),digest]==[logical['length'],logical['logicalSha256']],'owner-logical-byte-join',path,expected={k:logical[k]for k in('length','logicalSha256')},actual=dict(length=len(data),sha256=digest));files[file]=data
   try:
    frame=frame_levelscript_named(data,source=path,strings=source.strings,game_root=selected_root,null_list_params=null_list_params);out=fmv.project_owner(data,frame,source=path,strings=source.strings);owners+=1
    for row in out['rows']:row['nameCandidates']=fmv.name_candidates(row['projection']['fmvId'],gate['layout']);projected.append(row)
    failures.extend(dict(source=path,**r)for r in out['diagnostics'])
   except(ValueError,KeyError,IndexError,TypeError)as error:failures.append(dict(source=path,check='fresh-typed-owner-or-name-refused',sourceSha256=digest,detail=str(error)[:1200]))
 wanted={n['path']for r in projected for n in r['nameCandidates']};videos=_video_rows(Path(provenance['ledger']['path']),before['inputSetSha256'],wanted);video_rows=list(videos.values());resolution=_chunk_selection_snapshot(video_rows,outer);chunks=_chunk_fingerprints(video_rows);verified={name:_video_bytes(r)for name,r in videos.items()}
 for row in projected:
  row['videoFiles']=[dict(verified[n['path']],selection=n)for n in row['nameCandidates']if n['path']in verified];row['nativeMappingId']=SCHEMA;row['evidenceBoundary']='conditional'
  if not row['videoFiles']:failures.append(dict(source=row['source'],actionStart=row['actionStart'],check='no-current-video-file-for-proved-conditional-candidates'))
 source.check();_require(all(p.read_bytes()==raw for p,raw in files.items()),'owner-source-bookend',source.root);_require(chunks==_chunk_fingerprints(video_rows)and resolution==_chunk_selection_snapshot(video_rows,outer),'video-physical-bookend',provenance['ledger']['path']);_require(before==receipt(),'family-receipt-bookend',receipt_path)
 return dict(schema=REPORT_SCHEMA,status='partial'if failures else'validated',inputSetSha256=before['inputSetSha256'],nativeInputs=pins,evidenceBoundary='conditional',conditions=gate['conditions'],familyReceipt=_fingerprint(receipt_path),exportRoot=export_root.resolve().as_posix(),sources=selected,coverage=dict(sourceUniverse=len(universe),sourcesSelected=len(selected),ownersClosed=owners,allSourcesSelected=set(selected)==set(universe),allOwnersClosed=owners==len(selected),unusedCutsceneSafe=False,unresolved='Other source/consumer families and live selection remain independent; this conditional name join never clears unused-cutscene safety.'),readerInputs=source.reader_inputs,stringPoolInputs=source.pool_inputs,videoChunkFingerprints=chunks,videoChunkResolution=resolution,diagnostics=failures,rows=projected)

def replay_report(report_path=DEFAULT_REPORT,*,export_root=REPO_ROOT/'export_full',game_root=None):
 """Use a saved report only as a source selection; freshly replay every gate."""
 path=Path(report_path);raw=path.read_bytes();saved=json.loads(raw);_require(saved.get('schema')==REPORT_SCHEMA and saved.get('exportRoot')==Path(export_root).resolve().as_posix(),'current-FMV-report-source-plan',path)
 current=audit(expected_input_set_sha256=saved['inputSetSha256'],expected_family_receipt_sha256=saved['familyReceipt']['sha256'],family_receipt_path=Path(saved['familyReceipt']['path']),export_root=export_root,game_root=game_root,sources=saved['sources']);_require(path.read_bytes()==raw,'FMV-source-plan-bookend',path);return current

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--expected-input-set-sha256',required=True);parser.add_argument('--expected-family-receipt-sha256',required=True)
 for name,default in(('family-receipt',DEFAULT_OUTPUT),('export-root',REPO_ROOT/'export_full'),('game-root',None),('contract',CONTRACT_PATH),('report',DEFAULT_REPORT)):parser.add_argument('--'+name,type=Path,default=default)
 parser.add_argument('--source',action='append');args=parser.parse_args()
 family=json.loads(args.family_receipt.read_bytes());provenance=family['provenance'];protected=[Path(__file__),args.contract,args.family_receipt,args.export_root,*([args.game_root]if args.game_root is not None else[])]
 protected.extend(Path(provenance[k]['path'])for k in('outer','ledger'))
 protected.extend(Path(r['path'])for k in('sourceFingerprints','buildFingerprints','selectedChunkFingerprints','nativeInputs','streamToolFingerprints')for r in provenance.get(k,[]))
 protected.extend(args.export_root/'game/Json'/r['exportRelativePath']for r in family['rows'])
 protected.extend(Path(r['path'])for r in provenance['levelscriptStringPoolInputs']['files'])
 _guard_output(args.report,protected)
 try:result=audit(expected_input_set_sha256=args.expected_input_set_sha256,expected_family_receipt_sha256=args.expected_family_receipt_sha256,family_receipt_path=args.family_receipt,export_root=args.export_root,game_root=args.game_root,sources=args.source,contract_path=args.contract)
 except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError)as error:result=dict(schema=REPORT_SCHEMA,status='failed',diagnostic=getattr(error,'diagnostic',dict(check='load-or-shape',detail=str(error)[:1400])))
 write_report_json(args.report,result);print('levelscript_fmv_video_corpus: '+result['status']+': '+str(result.get('coverage',result.get('diagnostic')))[:1600]);return 0 if result['status']=='validated'else 1

if __name__=='__main__':raise SystemExit(main())
