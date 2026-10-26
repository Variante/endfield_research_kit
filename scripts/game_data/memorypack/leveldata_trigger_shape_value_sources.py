"""Own TriggerShapeData's managed44 wrapper; outer value transfers stay separate.

The serialized MC5 order differs from physical field order. Exact fields,
ordinary Vector3 child source and the enum's closed ReadUnmanaged request are
joined independently; neither managed44 nor a type name supplies wire framing.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Core.TriggerShapeData'
ENUM='Beyond.Gameplay.Core.TriggerShape'
VECTOR='UnityEngine.Vector3'
FIELDS=(('type',ENUM,16),('position',VECTOR,20),('eulerAngles',VECTOR,32),('size',VECTOR,44),('radius','float',56))
ORDER=(('eulerAngles',VECTOR),('position',VECTOR),('radius','float'),('size',VECTOR),('type',ENUM))


def record_program(regions,entry,s,*,null=False,new=False):
 if type(null)is not bool or type(new)is not bool or null and new:
  raise ValueError('storyTriggerShape.literal-wrapper-path')
 g=BytesPath(regions,entry);g.take('48895c2410','4889742418','57','4883ec30');ready=flag(g)
 g.take('488bda','488bf9');g.branch('75',True,1)
 g.take('488d542440','c644244000','488bcf');header=g.at;g.call(s['header']);g.take('84c0');g.branch('0f84',null)
 allocation=None;enum=None;calls={}
 if null:
  g.take('488bcb','48c70300000000');g.call(s['barrier'])
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
   g.take('4885c0');g.branch('0f84',False)
   g.take('33c9','0f57c0','0f114010','0f114020','48894830','894838','488bcb','488903');g.call(s['barrier'])
  g.take('807c244005');g.branch('0f85',False)
  g.take('488b33','488d4c2420','488bd7');calls['eulerAngles']=g.at;g.call(s['vector'])
  g.take('488bc8','4885f6');g.branch('0f84',False)
  g.take('f20f1001','488bd7','8b4008','488d4c2420','f20f114620','894628','488b33')
  calls['position']=g.at;g.call(s['vector']);g.take('488bc8','4885f6');g.branch('74',False,1)
  g.take('f20f1001','488bcf','8b4008','f20f114614','89461c','488b33')
  calls['radius']=g.at;g.call(s['single']);g.take('4885f6');g.branch('74',False,1)
  g.take('f30f114638','488d4c2420','488b33','488bd7');calls['size']=g.at;g.call(s['vector'])
  g.take('488bc8','4885f6');g.branch('74',False,1)
  g.take('f20f1001','488bcf','8b4008','f20f11462c','894634')
  enum=dict(instruction=g.at,cell=g.relative('488b15'));g.take('488b1b');calls['type']=g.at;g.call(s['enum'])
  g.take('4885db');g.branch('74',False,1);g.take('894310');g.jump('eb',1)
 g.take('488b5c2448','488b742450','4883c430','5f','c3')
 return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperNull=null,newWrapper=None if null else new,
  typedAllocation=allocation,enumContext=enum,headerCall=header,memberCalls=calls,
  wireMemberCount=5,positiveWireBytes=45,wrapperHeaderBytes=1,wrapperNullWireBytes=1,
  inlineHolderManagedBytes=44,newWrapperZeroedBytes=44 if new else 0,clearedWrapperReferenceBytes=8 if null else 0,
  completeFieldCopies=[]if null else[['eulerAngles',32,12],['position',20,12],['radius',56,4],['size',44,12],['type',16,4]],
  readerRegister='rdi',wrapperOutputRegister='rbx',valueSourceOutputLocal=None if null else[32,44],
  frame=dict(entryRspDelta=-56,callShadow=[0,32],headerOutputEntryHome=[8,9],
   sourceOutputLocal=[32,44],savedEntryHomes=dict(rbx=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi']),
  entryRspRestored=True,allNonvolatilesRestored=True,normalReturn=True,
  canonicalOriginalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  condition='Initialized ready metadata, enough stable contiguous buffered input, disjoint wrapper/output/frame/Reader storage, '
   'compatible nonnull wrapper after fresh allocation or reuse, exact normal child/header/allocation effects and disabled collector. '
   'Wrapper FF clears only its reference; default original value output, canonical adapter/provider and outer parent transfer remain unproved.')


def derive_record(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar,generated_vector3_source,unmanaged_enum_member_sources
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 need=lambda k,e,a:scalar.need('storyTriggerShape',k,e,a)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE];td=ctx.index.types[TYPE]
 need('exact-nominal-value',(True,False,'System.ValueType',-1),(ctx.is_value_type(TYPE),ctx.is_enum(TYPE),ctx.parent(TYPE),td.generic_container_index))
 scalar.ordinary(image,ctx.type_pointer(td.byval_type_index),17,'storyTriggerShape.value')
 need('exact-ordered-fields',list(ORDER),[(m.name,m.declared_type)for m in wrapper.members])
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 actual=sorted([(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields],key=lambda x:x[2])
 need('complete-physical-layout',list(FIELDS),actual)
 for field in fields:scalar.ordinary(image,ctx.type_pointer(field.type_index),12 if ctx.type_name(field.type_index)=='float'else 17,'storyTriggerShape.field')
 need('holder-inline-value',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
 need('bounded-size-index',True,0<=td.index<image.registration['typeDefinitionsSizesCount'])
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 need('boxed-managed-sizes',(60,44),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
 methods=pointer.methods(image,wrapper);reader=methods['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper)
 body=pointer.owned(image,image.method_pointer_va(reader))
 def call(offset):
  site=body['pointer']+offset;row,=[r for r in body['rows']if int(r['va'],16)==site];raw=bytes.fromhex(row['bytes'])
  need('owned-E8-site:'+str(offset),(5,0xe8),(len(raw),raw[0]));return site+5+int.from_bytes(raw[1:],'little',signed=True)
 symbols=dict(header=call(110),allocate=call(136),barrier=call(176),vector=call(203),single=call(280),enum=call(347))
 need('same-vector-source-sites',(symbols['vector'],symbols['vector']),(call(246),call(306)))
 need('same-FF-barrier',symbols['barrier'],call(426))
 paths=[record_program(body['regions'],body['pointer'],symbols,**mode)for mode in(dict(null=True),dict(new=True),dict())]
 allocation=derive_typed_usage_context(image,paths[1]['typedAllocation']['instruction']-base,label='storyTriggerShape.wrapper')
 need('actual-owned-wrapper-allocation',(1,wrapper.name),(allocation['tag'],allocation['typeName']))
 enum=derive_typed_usage_context(image,paths[1]['enumContext']['instruction']-base,label='storyTriggerShape.enum')
 enum_call=paths[1]['memberCalls']['type']
 enum_source=unmanaged_enum_member_sources.derive(image,pins,typed_request=enum,source_target=symbols['enum'],enum_type=ENUM,
  source_instruction=[enum_call-base,image.pe.bytes_at_va(enum_call,5).hex().upper()])
 record=vector_recorder(image);offsets=scalar.reader_offsets(image,'storyTriggerShape')
 header=record(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
 single=record(symbols['single']-base);primitive_param.single_source(image,single,offsets)
 vector=generated_vector3_source.derive_forwarder(image,pins,source_target=symbols['vector'])
 getter=methods['GetValue'];scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(TYPE,17,False),[],'storyTriggerShape.getter')
 get=pointer.leaf(image,image.method_pointer_va(getter),['0F104210','8B4238','0F104A20','0F1101','F20F104230','0F114910','F20F114120','894128','488BC1','C3'])
 constructors={}
 for name in('.ctor','CreateInstance'):
  m=methods[name];scalar.owned_method_abi(image,ctx,m.index,wrapper.type_definition,('void',1,False),[],'storyTriggerShape.'+name)
  constructors[name]=pointer.leaf(image,image.method_pointer_va(m),['0F57C0','33C0','0F114110','0F114120','48894130','894138','C3'])
 barrier,barrier_program,_=_fast_barrier(image,symbols['barrier']);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-trigger-shape-value-wrapper.v1',status='validated-conditional-trigger-shape-wrapper',
  nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,managedBytes=44,referenceLaneOffsets=[],paddingByteRanges=[],
  fields=actual,orderedMembers=[list(r)for r in ORDER],sourceWindows=body['windows'],programs=paths,
  getter=get,constructors=constructors,allocation=allocation,headerSource=header,singleSource=single,vectorSource=vector,
  enumSource=enum_source,
  barrier=dict(source=barrier,program=barrier_program),symbolRvas={k:v-base for k,v in symbols.items()},
  canonicalOriginalAdapterAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own managed44 layout with no references/padding, complete MC5/FF/new/reused wrapper and zero44 constructors, hidden44 getter, independently current Vector3 closed source and Single/raw enum32 Reader programs.',
   conditional=paths[0]['condition'],unresolved=['own canonical original adapter/default44/provider/interface/getter transfer','actual MissionArea value parent/local/store/full frame','container callbacks/counts','whole owner and physical EOF/publication']))))
