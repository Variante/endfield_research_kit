"""Own CabinSlotInfo's padded value48 wrapper; container/adapter stay separate."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.CabinSlotInfo'
PLAN=(('boundSize','UnityEngine.Vector3',48),('logicId','ulong',16),
 ('position','UnityEngine.Vector3',24),('rotation','UnityEngine.Vector3',36))


def record_program(regions,entry,s,*,null=False,new=False):
 if type(null)is not bool or type(new)is not bool or null and new:raise ValueError('storyCabin.literal-wrapper-path')
 g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec30');ready=flag(g)
 g.take('488bda','488bf9');g.branch('0f84',False)
 g.take('488d542440','c644244000','488bcf');g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 allocation=None;contexts=[];calls=[]
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier']);g.take('90');g.jump('e9')
 else:
  g.take('4889742448','48833b00');g.branch('0f84',new)
  if new:
   allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate']);g.take('4885c0');g.branch('0f84',False)
   g.take('0f57c0','488bcb','0f114010','0f114020','0f114030','488903');g.call(s['barrier']);g.take('90');g.jump('e9')
  g.take('0fb6742440','4080fe04');g.branch('0f85',False)
  contexts.append(g.at);g.relative('4c8b05');g.take('488d4c2420','488b33','488bd7');calls.append(g.at);g.call(s['vector3'])
  g.take('4885f6');g.branch('0f84',False)
  g.take('f20f10442420','488bcf','8b442428','f20f114630','894638','488b33');g.call(s['uint64'])
  g.take('4885f6');g.branch('74',False,1);g.take('48894610','488d4c2420')
  contexts.append(g.at);g.relative('4c8b05');g.take('488bd7','488b33');calls.append(g.at);g.call(s['vector3'])
  g.take('4885f6');g.branch('74',False,1)
  g.take('f20f10442420','488d4c2420','8b442428','488bd7','f20f114618','894620')
  contexts.append(g.at);g.relative('4c8b05');g.take('488b1b');calls.append(g.at);g.call(s['vector3'])
  g.take('4885db');g.branch('74',False,1)
  g.take('f20f10442420','8b442428','488b742448','f20f114324','89432c')
 g.take('488b5c2450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperNull=null,newWrapper=None if null else new,
  typedAllocation=allocation,vectorContextInstructions=contexts,vectorSourceCalls=calls,
  wrapperHeaderBytes=1,wrapperReferenceClearedBytes=8 if null else 0,newWrapperZeroedBytes=48 if new else 0,
  managedBytes=48,paddingByteRanges=[[44,48]],referenceLaneOffsets=[],sourceFieldOffsets=[]if null else[48,16,24,36],
  fieldCopySlices=[]if null else[[48,8],[56,4],[16,8],[24,8],[32,4],[36,8],[44,4]],
  sourceOutputLocal=[32,44],sourceLocalReusedOnlyAfterPreviousFieldStored=True,normalReturn=True,entryRspRestored=True,
  frame=dict(entryRspDelta=-56,callShadow=[0,32],sourceLocal=[32,44],headerEntryHome=[8,9],
   savedRsiEntryHome=[16,24],savedRbxEntryHome=[24,32],pushedNonvolatiles=['rdi']),
  originalDefaultFromWrapperFFAdmitted=False,containerAdmitted=False)


def derive_record(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.vector_layout import vector_context,vector_recorder
 from scripts.game_data.memorypack.generated_vector3_source import program as vector_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 need=lambda k,e,a:scalar.need('storyCabin',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 need('exact-member-order',[(n,t)for n,t,o in PLAN],[(m.name,m.declared_type)for m in wrapper.members])
 td=ctx.index.types[TYPE];need('nominal-nongeneric-value',True,ctx.is_value_type(TYPE)and td.generic_container_index<0)
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'storyCabin.value')
 need('owned-inline-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
 need('boxed-size64',64,image.pe.u32_at_va(size));fields=[]
 actual=[]
 for f in md.fields_for(td):
  if ctx.field_attributes(f.type_index)&16:continue
  name=md.string(f.name_index);field=ctx.field(TYPE+'::'+name);actual.append((name,field[1],field[2]))
  scalar.ordinary(image,ctx.type_pointer(f.type_index),11 if field[1]=='ulong'else 17,'storyCabin.field')
  fields.append(dict(name=name,typeName=field[1],field=list(field),rawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(f.type_index),16).hex()))
 need('exact-owned-fields',sorted(PLAN),sorted(actual))
 methods=pointer.methods(image,wrapper);method=methods['Deserialize'];primitive_param.reader_abi(image,ctx,method,wrapper)
 body=pointer.owned(image,image.method_pointer_va(method));calls=[control_transfer(r)['target']for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8']
 need('normal-first-five-calls',True,len(calls)>=5);need('same-three-actual-Vector3-entries',[calls[1]]*3,[calls[1],calls[3],calls[4]])
 from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
 symbols=dict(header=calls[0],vector3=calls[1],uint64=calls[2],barrier=_body_target(body,'mov [rbx], rax'),
  allocate=_body_target(body,'test rax, rax',before=True))
 programs=[record_program(body['regions'],body['pointer'],symbols,**mode)for mode in(dict(null=True),dict(new=True),dict())]
 offsets=scalar.reader_offsets(image,'storyCabin');vectors=[]
 for site in programs[-1]['vectorContextInstructions']:
  usage=derive_typed_usage_context(image,site-base,label='storyCabin.actualVector3')
  need('actual-ReadUnmanaged-vector3',('MemoryPack.MemoryPackReader','ReadUnmanaged',['UnityEngine.Vector3']),
   (usage['typeName'],usage['methodName'],usage['methodArguments']))
  registration=vector_context(image,usage,3,label='storyCabin.Vector3');source=pointer.owned(image,symbols['vector3'])
  vectors.append(dict(typedRequest=usage,registration=registration,actualTargetRva=symbols['vector3']-base,
   actualProgram=vector_program(source['regions'],source['pointer'],offsets),actualWindows=source['windows'],pointerAliasClaimed=False))
 allocation=programs[1]['typedAllocation'];allocation_usage=derive_typed_usage_context(image,allocation['instruction']-base,label='storyCabin.allocation')
 need('typed-wrapper-allocation',(1,wrapper.name),(allocation_usage['tag'],allocation_usage['typeName']))
 pair=derive_pair(image,TYPE,wrapper.name);registration=pointer.registered_pair(image,pair,wrapper,label='storyCabin.registeredPair')
 scalar.owned_method_abi(image,ctx,methods['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'storyCabin.getter')
 getter=pointer.leaf(image,image.method_pointer_va(methods['GetValue']),['0F104210','488BC1','0F104A20','0F1101','0F104230','0F114910','0F114120','C3'])
 constructors={role:pointer.leaf(image,image.method_pointer_va(methods[role]),['0F57C0','0F114110','0F114120','0F114130','C3'])for role in('.ctor','CreateInstance')}
 recorder=vector_recorder(image);header=recorder(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
 integer=recorder(symbols['uint64']-base);scalar.integer_source(image,integer,offsets,'storyCabin.uint64',width=8)
 barrier,barrier_proof,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-cabin-value-wrapper.v1',status='validated-current-cabin-wrapper-source',nativeInputs=pins,
  typeName=TYPE,wrapperName=wrapper.name,managedBytes=48,referenceLaneOffsets=[],paddingByteRanges=[[44,48]],fields=fields,
  readerMethod=[method.index,wrapper.name,'Deserialize',body['pointer']-base],sourceWindows=body['windows'],programs=programs,
  pair=pair,registration=registration,getter=getter,constructors=constructors,vectorSources=vectors,uint64Source=integer,headerSource=header,
  typedAllocation=allocation_usage,barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={key:target-base for key,target in symbols.items()},
  canonicalOriginalAdapterAdmitted=False,containerAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own nominal CabinSlotInfo48 fields/no-reference/padding, full MC4/FF/new/existing generated wrapper source, three independently typed actual Vector3 sources and complete local8+4 transfers, UInt64 source, full48 getter/zeroing and registered concrete wrapper.',
   conditional='Ready coherent owned metadata and wrapper/context, sufficient contiguous disjoint input/output/frame, exact callback and normal allocation/barrier effects. Positive padding is not serialized.',
   unresolved=['canonical original value48 adapter/conversion','dictionary/list and enclosing fields','runtime selection','whole owner/physical EOF']))))
