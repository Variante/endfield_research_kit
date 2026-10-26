"""Selected null/empty string-list Param joins; no positive Param admission."""
import json
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.memorypack import pooled_string_list_sources as shared,scalar_param_native as scalar
CONTRACT_PATH=CONTRACTS_DIR/'levelscript_pooled_string_list_native.json'


def derive(image,pins,parent):
 raw=CONTRACT_PATH.read_bytes();fact=json.loads(raw);need=lambda k,e,a:scalar.need('stringListParam',k,e,a)
 need('current-shared-inputs',pins,fact['nativeInputs']);need('dependency-shape',('endfield.levelscript-pooled-string-list-native.v1','exact-current-build','List<string>','conditional'),tuple(fact[k] for k in ('schema','status','codecKind','evidenceBoundary')))
 shared.validate_components(image,fact);clears=clear_proofs(image,fact)
 literal=fact['parent']['selectedPlan'];typed=parent['typedRead'];need('actual-typed-reader',('MemoryPack.MemoryPackReader','ReadPackable',[],['System.Collections.Generic.List`1<string>']),tuple(typed[k] for k in ('typeName','methodName','classArguments','methodArguments')))
 for key in ('usageCellRva','usageRawHex','tag','methodSpecIndex','methodSpec','typeName','methodName','classArguments','methodArguments'):need('same-closed-read.'+key,literal['typedContext'][key],typed[key])
 at,code=parent['parent']['instructions'][22];code=bytes.fromhex(code);need('own-direct-read',b'\xe8',code[:1]);target=at+5+int.from_bytes(code[1:],'little',signed=True);need('same-actual-reader-target',literal['targetRva'],target)
 base=image.pe.image_base;program,=[r for r in fact['programs'] if r['role']=='list'];regions=[(base+w['startRva'],image.window_bytes(w)) for w in program['windows']];offsets=scalar.reader_offsets(image,'stringListParam');from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 offsets['totalLength']=NativeReferenceContext(image).field('MemoryPack.MemoryPackReader::totalLength')[2]-16;symbols={k:base+v for k,v in fact['listSymbols'].items()};selected=[shared.list_source(regions,base+program['entryRva'],offsets,symbols,count=-1)]+[shared.list_source(regions,base+program['entryRva'],offsets,symbols,count=0,new=new) for new in (False,True)]
 need('no-elements',[[],[],[]],[p['elementCallbackSites'] for p in selected])
 if raw!=CONTRACT_PATH.read_bytes():raise ValueError('stringListParam.dependency-changed')
 return dict(dependency=CONTRACT_PATH.name,typedParamRead=typed,literalRead=literal['typedContext'],sameActualReaderTargetRva=target,selectedPrograms=selected,clearProofs=clears,collectionCounts=[-1,0],wireCountBytes=4,elementCallbacks=0,boundary='Conditional current reference-shared ListFormatter<string> with matching owned instantiated MethodInfo contexts and current open List factory; independently typed Param uses the identical closed ReadPackable MethodSpec and native source as the reviewed literal caller. Initialized coherent provider/contexts, fresh zeroed allocation/static empty array and normal provider/disabled collector are explicit conditions. Existing-list source requires its prior count zero; both actual and registered Clear complete this selected return with matching zero-count/version effects. Positive prior-size Clear paths remain unproved. Null avoids provider; zero calls provider but its result is unused. No positive Param lists, live default/provider/cache/inflation/initializer execution, arbitrary generics or whole owners admitted.')


def empty_clear(regions,entry,*,registered):
 from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
 if type(registered)is not bool:raise ValueError('stringListParam.clear-profile')
 g=BytesPath(regions,entry);g.take('4057','4883ec30','8b7918','33d2','ff411c','895118','85ff');g.branch('0f8e',True) if registered else g.branch('7f',False,1);g.take('4883c430','5f','c3')
 return dict(selectedBytes=g.seen,previousCount=0,storedCount=0,countSlot=24,versionSlot=28,itemsUntouched=True,normalReturn=True,condition='Valid typed matching reference-shared List with prior count exactly zero; complete ordinary return, no helper or element/array access. Positive prior size is outside this source profile.')


def clear_proofs(image,fact):
 import hashlib
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 base=image.pe.image_base;ctx=NativeReferenceContext(image);slot,=[r for r in fact['contexts'][0]['entries'] if r['relativeSlot']==2];entry=GenericEntries(image).resolve(slot['methodSpec'][0],['object'],[]);method=image.metadata.methods[slot['methodSpec'][0]]
 scalar.need('stringListParam','clear-declaration',('System.Collections.Generic.List`1','Clear',False,0,'void'),(image.type_name(method.declaring_type),image.metadata.string(method.name_index),bool(method.flags&16),method.parameter_count,ctx.type_name(method.return_type)));result={}
 for role,pointer in (('actual',base+fact['listSymbols']['clear']),('registered',entry['pointer'])):
  windows=[];regions=[]
  for part in image.unwind_index.family(pointer-base)['ranges']:
   a,b=part['runtimeTriple'][:2];raw=image.pe.bytes_at_va(base+a,b-a);windows.append(dict(startRva=a,endRva=b,sha256=hashlib.sha256(raw).hexdigest().upper()));regions.append((base+a,raw))
  result[role]=dict(entryRva=pointer-base,windows=windows,source=empty_clear(regions,pointer,registered=role=='registered'))
 result['canonicalRegistration']=entry;return result
