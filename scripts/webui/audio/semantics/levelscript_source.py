"""Fresh current pooled owners for Audio; stored strings are not Event requests."""
import hashlib,json
from scripts.game_data.levelscript_null_list_param_native import current_null_list_params
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.serialization_roots_native import read_contract
from scripts.game_data.levelscript_corpus import DEFAULT_OUTPUT,verify_family_receipt
from scripts.game_data.levelscript_source_receipts import SourceReader
from scripts.game_data.levelscript_binary import frame_levelscript_named
from scripts.game_data.levelscript_union_tags import short_name
from scripts.game_data.codecs.levelscript.audio_actions import project_audio_bindings
from scripts.game_data.codecs.levelscript.typed_record_payload import project_record

COMMON=('dontLogWarning','ID','releaseWhenExecutionFinished','uid','scopeMask','useCurrentScope','useGraphScope','nextID')
def require(ok,check,source,**detail):
 if not ok:
  error=ValueError('audioLevelScriptSource.'+check+':'+str(source)+':'+json.dumps(detail,sort_keys=True)[:1300]);error.diagnostic=dict(validator='audioLevelScriptSource',check=check,source=str(source),**detail);raise error

def project_owner(data,frame,*,source,action_names):
 require(frame.get('schemaStatus')=='named_exact'and type(frame.get('bytesConsumed'))is int and frame['bytesConsumed']==len(data),'complete-named-eof-required',source,expected=dict(schemaStatus='named_exact',bytesConsumed=len(data)),actual={k:frame.get(k)for k in('schemaStatus','bytesConsumed','stopField')},readerRefusals=frame.get('readerRefusals',[])[:2])
 asset=frame.get('ranges',{}).get('actionMap',{})
 if asset.get('value','present')is None:return dict(targetCount=0,rows=[],stringListGetters={})
 mapping=asset.get('dataMap',{});actions=mapping.get('actionList',[]);getters=mapping.get('getterList',[])
 for name,values in(('actionList',actions),('getterList',getters)):
  require(type(mapping.get(name+'Count'))is int and mapping[name+'Count']==len(values),'complete-typed-list-required',source,list=name)
 rows=[];selected_getters={};duplicate_getters=set();count=0
 for family,nodes in(('ActionBase',actions),('GetterBase',getters)):
  for ordinal,node in enumerate(nodes):
   name=short_name(node['wrapperName'])
   if family=='ActionBase'and name not in action_names or family=='GetterBase'and name!='ListGetValueString':continue
   fields=node['fields'];spans=node.get('fieldRanges',{});common=8 if family=='ActionBase'else 7;common_name=list(fields)[common-1]if len(fields)>=common else None;start,end=node['sourceOffset'],node['endOffset']
   require(common_name in spans and type(start)is int and type(end)is int and 0<=start<spans[common_name][1]<=end<=len(data),'typed-node-boundary',source,action=name,start=start,end=end)
   record=dict(start=start,end=end,payloadStart=spans[common_name][1],localId=fields.get('ID'),uid=fields.get('uid'),unionTag=node['unionTag'],serializedMemberCount=node['memberCount'],family=family,typedNode=node,unionTagEncoding='current-typed-owner')
   if family=='GetterBase':
    detail=project_record(record).get('listGetValueString')
    if isinstance(detail,dict)and type(record['localId'])is int:
     local=record['localId']
     if local in selected_getters or local in duplicate_getters:duplicate_getters.add(local);selected_getters.pop(local,None)
     else:selected_getters[local]=dict(record=record,actionMapRole='getterList#'+str(ordinal+1),getter=detail)
    continue
   count+=1;require(tuple(fields)[:8]==COMMON and node['memberCount']==len(fields),'current-action-common-fields',source,action=name)
   own={}
   for field,value in list(fields.items())[8:]:
    kind=node.get('fieldTypes',{}).get(field,'');span=spans.get(field)
    require(kind.startswith(('Param<','ParamOutput<'))and isinstance(span,(list,tuple))and len(span)==2 and all(type(at)is int for at in span)and record['payloadStart']<=span[0]<span[1]<=end,'typed-audio-field',source,action=name,field=field,kind=kind,range=span)
    require(value is None or isinstance(value,dict),'typed-audio-param',source,action=name,field=field)
    if value is None:detail=dict(present=False,bindingKind='null')
    else:
     output=kind.startswith('ParamOutput<');require(output or type(value.get('paramSource'))is int,'typed-audio-param-source',source,action=name,field=field)
     detail=dict(value,present=True,bindingKind='output'if output else'constant'if value['paramSource']==0 else'dynamic')
    own[field]=dict(detail,sourceField='_'+field)
   audio=project_audio_bindings(name,own);audio['eventBindingCandidates']=audio.pop('eventBindings',[]);audio.update(requestConsumerStatus='current-native-consumer-unproved',propertySourceStatus='current-LevelData-owner-receipt-unproved',payloadShape='current-pooled-typed-owner-fields',nativeMappingId='current-owning-reader-typed-fields')
   rows.append(dict(record=record,actionMapRole='actionList#'+str(ordinal+1),audioAction=audio))
 return dict(targetCount=count,rows=rows,stringListGetters=selected_getters,topology=None,topologyDiagnostic=dict(validator='audioLevelScriptSource',check='current-native-topology-consumer-unproved',source=source))

class CurrentAudioSource:
 """One lexical operation; no saved native/schema success survives another enter."""
 def __init__(self,export_root,*,gameassembly,metadata,action_names,receipt_path=DEFAULT_OUTPUT):
  self.root=Path(export_root);self.receipt_path=Path(receipt_path);self.gameassembly=gameassembly;self.metadata=metadata;self.action_names=action_names;self.active=False;self.files={};self.closed=set()
 def receipt(self):return verify_family_receipt(self.receipt_path,expected_sha256=self.receipt_sha,expected_input_set_sha256=self.input_set,export_root=self.root)
 def __enter__(self):
  require(not self.active,'operation-already-active',self.root);self.files={};self.closed=set()
  require(self.gameassembly is not None and self.metadata is not None,'explicit-native-pair-required',self.root,expected='explicit GameAssembly.dll and global-metadata.dat',actual=dict(gameassembly=str(self.gameassembly),metadata=str(self.metadata)))
  self.pins=read_contract()['nativeInputs'];pair=check_installed_native_inputs(self.pins['GameAssembly.dll'],self.pins['global-metadata.dat'],gameassembly=self.gameassembly,metadata=self.metadata);require(pair.status=='validated','selected-native-inputs',self.root,actual=pair.status,detail=pair.detail);self.game_root=Path(pair.metadata).parents[2]
  self.receipt_raw=self.receipt_path.read_bytes();plan=json.loads(self.receipt_raw);self.receipt_sha=hashlib.sha256(self.receipt_raw).hexdigest().upper();self.input_set=plan['inputSetSha256'];self.before=self.receipt();require((self.before.get('format'),self.before.get('schemaVersion'))==('endfield-levelscript-current-corpus-v2',2),'current-pooled-family-receipt-required',self.receipt_path,expected=['endfield-levelscript-current-corpus-v2',2],actual=[self.before.get('format'),self.before.get('schemaVersion')])
  provenance=self.before['provenance'];outer=json.loads(Path(provenance['outer']['path']).read_bytes());require(all(Path(outer[key]).resolve()==(self.game_root/folder).resolve()for key,folder in(('primaryAssets','Persistent'),('fallbackAssets','StreamingAssets'))),'selected-native-vfs-roots',self.game_root)
  self.source=SourceReader(dict(status='complete',provenance=dict(levelscriptReaderInputs=provenance['readerInputs'],levelscriptStringPoolInputs=provenance['levelscriptStringPoolInputs'])),self.root/'game/Json',self.pins,game_root=self.game_root)
  self.universe={r['exportRelativePath']:r for r in self.before['rows']if r['family']=='LevelScriptData'};self.native_scope=current_null_list_params(game_root=self.game_root,strings=self.source.strings);self.null_list_params=self.native_scope.__enter__();self.active=True;return self
 def frame(self,path,data):
  require(self.active,'operation-not-active',path);file=Path(path).resolve();relative=file.relative_to(self.source.root.resolve()).as_posix();row=self.universe.get(relative);digest=hashlib.sha256(data).hexdigest().upper();require(row is not None and[len(data),digest]==[row['length'],row['logicalSha256']],'owner-logical-byte-join',path,expected=None if row is None else dict(length=row['length'],sha256=row['logicalSha256']),actual=dict(length=len(data),sha256=digest));require(self.files.setdefault(file,data)==data,'mixed-source-versions',path)
  frame=frame_levelscript_named(data,source=relative,strings=self.source.strings,game_root=self.game_root,null_list_params=self.null_list_params);require(frame.get('schemaStatus')=='named_exact'and type(frame.get('bytesConsumed'))is int and frame['bytesConsumed']==len(data),'complete-named-eof-required',relative,expected=dict(schemaStatus='named_exact',bytesConsumed=len(data)),actual={k:frame.get(k)for k in('schemaStatus','bytesConsumed','stopField')},readerRefusals=frame.get('readerRefusals',[])[:2]);self.closed.add(relative);return frame
 def decode(self,path,data):
  return project_owner(data,self.frame(path,data),source=Path(path).resolve().relative_to(self.source.root.resolve()).as_posix(),action_names=self.action_names)
 def audit(self):
  require(self.active,'operation-not-active',self.root)
  return dict(status='current-authenticated-known-action-profile',familyReceipt=dict(path=str(self.receipt_path),sha256=self.receipt_sha),sourceUniverse=len(self.universe),sourcesAttempted=len(self.files),ownersClosed=len(self.closed),allSourcesAttempted=len(self.files)==len(self.universe),allOwnersClosed=len(self.closed)==len(self.universe),audioActionAbsenceProved=False,requestConsumerStatus='current-native-consumer-unproved')
 def __exit__(self,*error):
  try:
   self.native_scope.__exit__(*error)
   self.source.check();require(all(path.read_bytes()==raw for path,raw in self.files.items()),'owner-source-bookend',self.source.root);require(self.receipt_raw==self.receipt_path.read_bytes()and self.before==self.receipt(),'family-receipt-bookend',self.receipt_path)
  finally:self.active=False
