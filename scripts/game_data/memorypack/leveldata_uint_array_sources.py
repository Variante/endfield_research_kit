"""Exact current UInt32 bulk-array source, bounded independently to64 values.

The nominal ReadUnmanagedArray context and its actual Dangerous helper are
distinct joins. The four-byte multiplier, payload guard, exact bounded copy
and all Reader updates establish raw UInt32 elements without a callback or a
GameplayTag/Int32 width substitution. Ready coherent typed contexts, matching
normal allocation/static-empty-array effects and disjoint buffered storage
remain conditions. The parent must prove its nested MethodInfo argument flow.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='uint[]'
CAP='story-uint32-array'
LIMIT=64


def array_program(regions,entry,offsets,s,*,count):
 if type(count)is not int or not -1<=count<=LIMIT:raise ValueError('storyUIntArray.count-profile')
 g=BytesPath(regions,entry);cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
 g.take('48895c2410','48896c2418','4889742420','57','4883ec20','48837a3800','488bea','488bd9');g.branch('0f84',False)
 g.take('837b'+rem+'04');g.branch('0f8c',False)
 g.take('488b43'+cur,'8b38','8b73'+rem,'83c6fc');g.branch('0f88',False)
 g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','8973'+rem,'486343'+used,'488b53'+total,'482bd0','4863c7','483bd0');g.branch('0f8c',False)
 g.take('83ffff');g.branch('0f84',count==-1)
 if count==-1:g.take('33c0');g.jump('eb',1)
 else:
  g.take('85ff');g.branch('0f84',count==0)
  if count==0:
   g.take('488b4d38','488b09');g.call(s['empty']);g.take('90');g.jump('e9')
  else:
   g.take('4c89742430','8d34bd00000000','3b73'+rem);g.branch('0f8f',False)
   g.take('488b4538','4c8b7008','49837e3800');g.branch('0f84',False)
   g.take('498b4e38','33d2');g.call(s['context']);g.take('488bd7','488bc8');g.call(s['arrayAllocate'])
   g.take('488b5538','488bc8','4c8bf0','488b5210');g.call(s['dataReference'])
   g.take('488b53'+cur,'488bc8','448bc6');g.call(s['copy']);g.take('85f6');g.branch('74',False,1)
   g.take('8b7b'+rem,'2bfe');g.branch('0f88',False)
   g.take('0173'+adv,'4863c6','480143'+cur,'0173'+used,'897b'+rem,'498bc6','4c8b742430')
 g.take('488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,elementWireBytes=4,payloadBytes=max(count,0)*4,
  rawBitsPreserved=True,actualReader='incoming RCX preserved RBX',actualMethodInfo='incoming RDX preserved RBP',
  elementCallbackUsed=False,allocationCountPassedUnchanged=count>0,sameReaderCounters=True,normalReturn=True,entryRspRestored=True)


def empty_program(regions,entry,context):
 g=BytesPath(regions,entry);g.take('4053','4883ec20','4883793800','488bd9');g.branch('74',False,1)
 g.take('488b4b38','33d2');g.call(context);g.take('83b8e000000000');g.branch('74',False,1)
 g.take('488b4b38','33d2');g.call(context)
 g.take('488b80b8000000','488b00','4883c420','5b','c3')
 return dict(selectedBytes=g.seen,contextSlot=0,normalReturn=True,entryRspRestored=True,
  result='unchanged owned EmptyArray<uint> static reference',runtimeObjectIdentityObserved=False)


def bind_actual_source(image,context,binding,*,base,call_target):
 """Bind a freshly executed owning prover to this exact context and E8."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 need=lambda k,e,a:scalar.need('storyUIntArray',k,e,a)
 need('fresh-owning-source-result',True,isinstance(binding,dict))
 for key,value in dict(typeName=TYPE,readerMethodDefinition=context['contexts'][0]['definition'],
  dangerousMethodDefinition=context['contexts'][1]['definition'],sourceTargetRva=call_target-base,
  readerRegister='rcx',methodInfoRegister='rdx',resultRegister='rax',nestedDangerousMethodInfoProved=True,
  completeCallerSourceProved=True,actualE8Proved=True).items():
  need('actual-source-identity:'+key,value,binding.get(key))
  if type(value)is int:need('literal-actual-source-identity:'+key,int,type(binding.get(key)))
  if type(value)is bool:need('literal-actual-source-identity:'+key,bool,type(binding.get(key)))
 site=binding.get('sourceCallRva');need('literal-actual-source-call',True,type(site)is int and site>0)
 raw=image.pe.bytes_at_va(base+site,5);need('actual-owned-call-size',5,len(raw));need('actual-owned-call-E8',232,raw[0])
 need('actual-owned-call-target',call_target,base+site+5+int.from_bytes(raw[1:],'little',signed=True))
 return binding


def derive(image,pins,*,typed_request,call_target,actual_source_prover=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.pointer_param import owned
 from scripts.game_data.memorypack.skill_unmanaged_array_context import derive_uint32
 from scripts.game_data.memorypack.skill_gameplay_tag_array_sources import data_reference_program
 from scripts.game_data.memory_copy_bounded_native import validate_components as copy_source
 need=lambda k,e,a:scalar.need('storyUIntArray',k,e,a)
 _publication_gate(image,pins);need('callable-owning-source-prover',True,actual_source_prover is None or callable(actual_source_prover))
 base=image.pe.image_base;ctx=NativeReferenceContext(image)
 context=derive_uint32(image,typed_request);danger=context['contexts'][1]['definition']
 registration=GenericEntries(image).resolve(danger,[],['uint'])
 canonical_match=registration['pointer']==call_target;actual_source=None
 if actual_source_prover is not None:
  actual_source=bind_actual_source(image,context,actual_source_prover(image,pins,typed_request=typed_request,call_target=call_target),base=base,call_target=call_target)
 elif not canonical_match:need('exact-closed-Dangerous-source',registration['pointer'],call_target)
 body=owned(image,call_target);calls=[row for row in body['rows']if bytes.fromhex(row['bytes'])[:1]==b'\xe8']
 need('four-complete-hot-helper-calls',True,len(calls)>=4)
 symbols={key:control_transfer(row)['target']for key,row in zip(('context','arrayAllocate','dataReference','copy'),calls[:4],strict=True)}
 empty,=[control_transfer(row)['target']for index,row in enumerate(body['rows'])if index and bytes.fromhex(row['bytes'])[:1]==b'\xe8'and body['rows'][index-1]['text']=='mov rcx, [rcx]']
 symbols['empty']=empty;offsets=scalar.reader_offsets(image,'storyUIntArray');offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
 paths=[array_program(body['regions'],call_target,offsets,symbols,count=count)for count in range(-1,LIMIT+1)]
 data=owned(image,symbols['dataReference']);data_program=data_reference_program(data['regions'],symbols['dataReference'])
 empty_body=owned(image,empty);empty_proof=empty_program(empty_body['regions'],empty,symbols['context'])
 copy_path=CONTRACTS_DIR/'memory_copy_bounded_native.json';copy_raw=copy_path.read_bytes();declaration=json.loads(copy_raw)
 need('copy-selected-inputs',pins,declaration['nativeInputs']);need('actual-bounded-copy-source',base+declaration['entryRva'],symbols['copy'])
 copy=copy_source(image,declaration);need('copy-complete-payload-bound',True,copy['maxBytes']>=LIMIT*4)
 _publication_gate(image,pins);need('copy-source-bookend',copy_raw,copy_path.read_bytes())
 cap=dict(typeName=TYPE,elementType='uint',elementValueType=True,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,
  positiveCountsAdmitted=True,headerBytes=4,elementWireBytes=4,rawBitsPreserved=True,elementCallbackUsed=False,
  arrayReaderMethodDefinition=typed_request['methodSpec'][0],dangerousMethodDefinition=danger,dangerousTargetRva=call_target-base,
  nestedDangerousMethodInfoRequired=True,normalTypedAllocationRequired=True,actualRuntimeSelectionObserved=False,
  canonicalEntryPointerMatched=canonical_match,closedPointerEquivalenceProved=canonical_match,
  actualSourceAuthentication='fresh-owning-caller'if actual_source is not None else'exact-registered-entry',
  actualOwningSourceJoinProved=actual_source is not None,
  wholeGrammarAdmitted=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 return json.loads(json.dumps(dict(schema='endfield.story-uint32-array-source.v1',status='validated-conditional-uint32-array-source',nativeInputs=pins,
  capability=cap,proof=dict(context=context,registration=registration,actualSourceJoin=actual_source,
   canonicalEntryPointerMatched=canonical_match,closedPointerEquivalenceProved=canonical_match,programs=paths,sourceWindows=body['windows'],
   dataReference=data_program,dataReferenceWindows=data['windows'],empty=empty_proof,emptyWindows=empty_body['windows'],
   copy=copy,symbolRvas={key:target-base for key,target in symbols.items()}),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Fresh exact primitive UInt32 context and closed Dangerous body, complete signed null/empty/positive1..64 programs, raw4 multiplier/payload/copy/Reader updates and current typed data-reference/static-empty helper programs.',
   conditional=__doc__,unresolved=['actual enclosing nested MethodInfo/field flow','counts above64','runtime typed allocation/context selection','whole owner/physical EOF']))))
