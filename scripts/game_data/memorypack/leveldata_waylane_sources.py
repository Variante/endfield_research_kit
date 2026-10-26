"""Exact WayLane value16 wrapper; uint-array and list grammars are separate.

The owned payload is Int32 at0, padding at4..7 and uint-array reference at8.
The declared member order is array then Int32. Wrapper FF clears the wrapper
reference; only an independently proved canonical value adapter can supply a
default original. No collection counts or serialized width follow from16.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.AI.WayLane'


def record_program(regions,entry,offsets,s,*,null=False,new=False):
 if type(null)is not bool or type(new)is not bool or null and new:raise ValueError('storyWayLane.literal-wrapper-path')
 g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
 g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
 g.take('488bfa','488bd9');g.branch('0f84',False)
 g.take('837b'+rem+'01');g.branch('0f8c',False)
 g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
 g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('74',null,1)
 allocation=None;usage=None;array_site=None
 if null:
  g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
 else:
  g.take('48833f00');g.branch('0f84',new)
  if new:
   allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
   g.take('0f57c0','488bcf','0f114010','488907');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('4080fe02');g.branch('0f85',False)
  usage=dict(instruction=g.at,cell=g.relative('488b35'));g.take('488b2f','48837e3800');g.branch('0f84',False)
  g.take('488b5638','488bcb','488b12');array_site=g.at;g.call(s['array']);g.take('4885ed');g.branch('74',False,1)
  g.take('488d4d18','48894518');g.call(s['barrier']);g.take('488b3f','488bcb');g.call(s['int32'])
  g.take('4885ff');g.branch('74',False,1);g.take('894710')
 g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperNull=null,newWrapper=None if null else new,
  typedAllocation=allocation,arrayUsage=usage,arraySourceCall=array_site,arrayTarget=None if null else s['array'],
  nestedMethodInfoArgument=None if null else dict(frontdoorContextOffset=56,dangerousMethodSlot=0,argumentRegister='rdx'),
  managedBytes=16,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]],wrapperHeaderBytes=1,
  wrapperReferenceClearedBytes=8 if null else 0,newWrapperZeroedBytes=16 if new else 0,
  sourceFieldOffsets=[]if null else[24,16],sameReaderAndOutput=True,normalReturn=True,entryRspRestored=True,
  originalDefaultFromWrapperFFAdmitted=False,childGrammarAdmitted=False,positiveCollectionAdmitted=False)


def derive_record(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_unmanaged_array_context import derive_uint32
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 from scripts.game_data.memorypack.pooled_nominal_key_sources import lang_getter
 need=lambda k,e,a:scalar.need('storyWayLane',k,e,a)
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 need('nominal-nongeneric-value',True,ctx.is_value_type(TYPE)and ctx.index.types[TYPE].generic_container_index<0)
 need('member-order',[('laneDir','uint[]'),('totalLane','int')],[(m.name,m.declared_type)for m in wrapper.members])
 need('owned-inline-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
 need('own-fields',[(TYPE,'int',16),(TYPE,'uint[]',24)],[ctx.field(TYPE+'::'+n)for n in('totalLane','laneDir')])
 td=ctx.index.types[TYPE];scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'storyWayLane.original')
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('boxed-size32',32,image.pe.u32_at_va(size))
 fields=[]
 for field in md.fields_for(td):
  if ctx.field_attributes(field.type_index)&16:continue
  name=md.string(field.name_index);raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16);declared=ctx.type_name(field.type_index)
  scalar.ordinary(image,ctx.type_pointer(field.type_index),29 if name=='laneDir'else 8,'storyWayLane.field',reference=name=='laneDir')
  if name=='laneDir':need('array-owned-UInt32-element',b'\x09\x80',image.pe.bytes_at_va(int.from_bytes(raw[:8],'little'),16)[10:12])
  fields.append(dict(name=name,typeName=declared,field=list(ctx.field(TYPE+'::'+name)),rawTypeHex=raw.hex()))
 methods=pointer.methods(image,wrapper);method=methods['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
 body=pointer.owned(image,image.method_pointer_va(method));offsets=scalar.reader_offsets(image,'storyWayLane')
 symbols=dict(array=_body_target(body,'test rbp, rbp',before=True),int32=_body_target(body,'test rdi, rdi',before=True),
  barrier=_body_target(body,'mov [rdi], 0x0'),allocate=_body_target(body,'test rax, rax',before=True))
 programs=[record_program(body['regions'],body['pointer'],offsets,symbols,**mode)for mode in(dict(null=True),dict(new=True),dict())]
 usage=derive_typed_usage_context(image,programs[2]['arrayUsage']['instruction']-base,label='storyWayLane.uintArray')
 context=derive_uint32(image,usage)
 allocation=programs[1]['typedAllocation'];allocation_usage=derive_typed_usage_context(image,allocation['instruction']-base,label='storyWayLane.allocation')
 need('typed-wrapper-allocation',(1,wrapper.name),(allocation_usage['tag'],allocation_usage['typeName']))
 pair=derive_pair(image,TYPE,wrapper.name);registration=pointer.registered_pair(image,pair,wrapper,label='storyWayLane.registeredPair')
 scalar.owned_method_abi(image,ctx,methods['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'storyWayLane.getter')
 getter_entry=image.method_pointer_va(methods['GetValue']);getter=lang_getter([(getter_entry,image.pe.bytes_at_va(getter_entry,16))],getter_entry)
 constructors={role:pointer.leaf(image,image.method_pointer_va(methods[role]),['0F57C0','0F114110','C3'])for role in('.ctor','CreateInstance')}
 integer=vector_recorder(image)(symbols['int32']-base);scalar.integer_source(image,integer,offsets,'storyWayLane.int32',width=4)
 barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-waylane-record-source.v1',status='validated-current-value-wrapper-source',nativeInputs=pins,
  typeName=TYPE,wrapperName=wrapper.name,managedBytes=16,referenceLaneOffsets=[8],paddingByteRanges=[[4,8]],fields=fields,
  readerMethod=[method.index,wrapper.name,'Deserialize',body['pointer']-base],
  sourceWindows=body['windows'],programs=programs,arrayContext=context,arrayTypedRequest=usage,typedAllocation=allocation_usage,
  pair=pair,registration=registration,getter=getter,constructors=constructors,integerSource=integer,
  barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={key:target-base for key,target in symbols.items()},
  childGrammarAdmitted=False,positiveCollectionAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own WayLane value16/padding/reference layout, full FF/new/reuse wrapper source and Reader/header/field transfers, exact nested Dangerous<uint> MethodInfo argument flow, own constructors/getter/current eager pair and Int32 source.',
   conditional='Ready coherent typed contexts, disjoint buffered Reader/wrapper/field/frame storage, exact matching wrapper callback and normal compatible typed allocation/barrier effects. Uint array grammar and canonical original transfer are independently required.',
   unresolved=['UInt32 array source/counts','canonical original value16 adapter/dispatch','positive WayLane list loop/Add','actual WayPoint/host parents','runtime selection','whole owner/physical EOF']))))


def prove_array_source(image,pins,*,typed_request,call_target):
 """Fresh exact parent ABI/MethodInfo join for the distinct optimized helper."""
 from scripts.game_data.memorypack import scalar_param_native as scalar
 need=lambda k,e,a:scalar.need('storyWayLaneArraySource',k,e,a)
 record=derive_record(image,pins);base=image.pe.image_base
 need('same-selected-inputs',pins,record['nativeInputs']);need('same-fresh-actual-request',typed_request,record['arrayTypedRequest'])
 expected=base+record['symbolRvas']['array'];need('actual-owned-E8-target',expected,call_target)
 program=record['programs'][2]
 need('same-selected-caller-target',call_target,program['arrayTarget'])
 need('exact-nested-MethodInfo-flow',dict(frontdoorContextOffset=56,dangerousMethodSlot=0,argumentRegister='rdx'),program['nestedMethodInfoArgument'])
 context=record['arrayContext'];first,danger=context['contexts'][:2]
 need('same-frontdoor-definition',typed_request['methodSpec'][0],first['definition'])
 need('same-nested-Dangerous-definition',danger['definition'],first['entries'][0]['methodSpec'][0])
 return dict(typeName='uint[]',readerMethodDefinition=first['definition'],dangerousMethodDefinition=danger['definition'],
  sourceTargetRva=call_target-base,sourceCallRva=program['arraySourceCall']-base,
  readerRegister='rcx',methodInfoRegister='rdx',resultRegister='rax',nestedDangerousMethodInfoProved=True,
  completeCallerSourceProved=True,actualE8Proved=True,proof=record)
