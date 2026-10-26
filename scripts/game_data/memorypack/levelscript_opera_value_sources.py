"""OperaSegment MC2 wrapper sources; array callback and Original adapter separate."""
import hashlib,json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.levelscript_opera_array_sources import TYPE,ENUM,PARAMETERS,layout as original_layout

SCHEMA='endfield.story-opera-value-wrapper.v1'


def need(key,condition):
 if not condition:raise ValueError('storyOperaValue.'+key)


def value_leaf_program(regions,entry,*,getter=False):
 need('literal-leaf-mode',type(getter)is bool);g=BytesPath(regions,entry)
 if getter:g.take('0f104210','488bc1','0f1101','c3')
 else:g.take('0f57c0','0f114110','c3')
 return dict(selectedBytes=g.seen,managedBytes=16,wholePayloadCopiedUnchanged=getter,
  wholePayloadZeroed=not getter,sameHiddenOutputReturnedInRax=getter,
  entryFrameUnchanged=True,normalReturn=True,physicalExtentProved=False,wireGrammarAdmitted=False)


def record_program(regions,entry,*,symbols=None,new=False,ff=False):
 need('literal-path-modes',type(new)is bool and type(ff)is bool)
 need('literal-symbol-domain',symbols is None or type(symbols)is dict)
 g=BytesPath(regions,entry);roles={};reads=[];allocation=None
 def call(role):
  site=g.at;target=g.relative('e8');need('same-role-target:'+role,role not in roles or roles[role]==target)
  if symbols is not None:need('independent-role-target:'+role,symbols.get(role)==target)
  roles[role]=target;return site
 g.take('48895c2410','4889742418','57','4883ec20');flag=g.relative('803d')+1
 g.take('00','488bda','488bf9');g.branch('75',True,1)
 g.take('488d542430','c644243000','488bcf');header=call('header');g.take('84c0');g.branch('0f84',ff)
 if ff:g.take('488bcb','48c70300000000');call('barrier')
 else:
  g.take('48833b00');g.branch('75',not new,1)
  if new:
   allocation=dict(instructionVa=g.at,classCellVa=g.relative('488b0d'));call('allocate')
   g.take('4885c0');g.branch('74',False,1)
   g.take('0f57c0','488bcb','0f114010','488903');call('barrier')
  g.take('807c243002');g.branch('75',False,1)
  context=dict(instructionVa=g.at,cellVa=g.relative('488b15'));g.take('488bcf','488b33');site=call('enum')
  g.take('4885f6');g.branch('74',False,1);g.take('894610')
  reads.append(dict(fieldName='operaType',declaredType=ENUM,sourceCallVa=site,typedUsage=context,fieldOffset=16,storedBytes=4))
  g.take('488bcf');context=dict(instructionVa=g.at,cellVa=g.relative('488b15'));g.take('488b1b');site=call('array')
  g.take('4885db');g.branch('74',False,1);g.take('4533c0','488bd0','488bcb');setter=call('arraySetter')
  reads.append(dict(fieldName='parameters',declaredType=PARAMETERS,sourceCallVa=site,typedUsage=context,setterCallVa=setter,fieldOffset=24,storedBytes=8))
  g.jump('eb',1)
 g.take('488b5c2438','488b742440','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,symbolTargets=roles,newWrapper=new,wrapperFF=ff,initializedFlagVa=flag,
  headerCallVa=header,typedAllocation=allocation,orderedReads=reads,managedBytes=16,memberCount=None if ff else 2,
  wrapperReferenceClearedBytes=8 if ff else 0,newWrapperZeroedBytes=16 if new and not ff else 0,
  paddingBytesTouchedByPositiveMembers=False,wrapperFFDefaultOriginalAdmitted=False,
  frame=dict(entryRspDelta=-40,callShadowRspRange=[0,32],headerEntryHome=[8,9],
   savedEntryHomes=dict(rbx=[16,24],rsi=[24,32],rdi=[-8,0]),entryRspRestored=True,
   allNonvolatilesRestored=True,fullSelectedFrameProved=True),
  normalReturn=True,canonicalOriginalAdmitted=False,parametersElementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive_record(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
 from scripts.game_data.memorypack import unmanaged_enum_member_sources,skill_reference_array_sources
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 from scripts.game_data.memorypack.vector_layout import vector_recorder
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 need('own-MC2-member-order',[(m.name,m.declared_type)for m in wrapper.members]==[('operaType',ENUM),('parameters',PARAMETERS)])
 nominal=original_layout(image,ctx);need('direct-inline-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,TYPE,16))
 td=md.types[wrapper.type_definition];at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 need('complete-wrapper-storage',image.pe.u32_at_va(at)==32)
 methods=pointer.methods(image,wrapper);reader=methods['Deserialize'];primitive_param.reader_abi(image,ctx,reader,wrapper)
 body=pointer.owned(image,image.method_pointer_va(reader));first=record_program(body['regions'],body['pointer'],new=True)
 symbols=first['symbolTargets'];programs=[first]+[record_program(body['regions'],body['pointer'],symbols=symbols,new=n,ff=f)
  for n,f in((False,False),(True,True),(False,True))]
 allocation=derive_typed_usage_context(image,first['typedAllocation']['instructionVa']-base,label='storyOperaValue.allocation')
 need('exact-owned-wrapper-allocation',(allocation['tag'],allocation['typeName'])==(1,wrapper.name)
  and base+allocation['usageCellRva']==first['typedAllocation']['classCellVa'])
 leaves={}
 for role,getter in(('.ctor',False),('CreateInstance',False),('GetValue',True)):
  method=methods[role];scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,(TYPE,17,False)if getter else('void',1,False),[],'storyOperaValue.'+role)
  target=image.method_pointer_va(method);raw=image.pe.bytes_at_va(target,16);program=value_leaf_program([(target,raw)],target,getter=getter)
  length=sum(len(bytes.fromhex(h))for a,h in program['selectedBytes']);raw=raw[:length]
  leaves[role]=dict(method=[method.index,wrapper.name,role,target-base],program=program,
   sourceRegions=[[target,raw.hex().upper()]],window=dict(startRva=target-base,endRva=target-base+length,sha256=hashlib.sha256(raw).hexdigest().upper()))
 request_sources={}
 for read in first['orderedReads']:
  usage=derive_typed_usage_context(image,read['typedUsage']['instructionVa']-base,label='storyOperaValue.member')
  need('same-current-MethodInfo-cell',base+usage['usageCellRva']==read['typedUsage']['cellVa'])
  site=read['sourceCallVa'];instruction=[site-base,image.pe.bytes_at_va(site,5).hex().upper()]
  if read['fieldName']=='operaType':
   child=unmanaged_enum_member_sources.derive(image,pins,typed_request=usage,source_target=symbols['enum'],enum_type=ENUM,source_instruction=instruction)
  else:child=skill_reference_array_sources.derive(image,pins,typed_request=usage,call_target=symbols['array'],element_type=PARAMETERS[:-2],count_limit=4096)
  request_sources[read['fieldName']]=dict(typedRequest=usage,sourceInstruction=instruction,source=child)
 member,=[m for m in wrapper.members if m.name=='parameters'];method=md.methods[member.method_index]
 scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(PARAMETERS,29,True)],'storyOperaValue.arraySetter')
 target=image.method_pointer_va(method);need('same-current-named-array-setter',target==symbols['arraySetter'])
 raw=image.pe.bytes_at_va(target,13);g=BytesPath([(target,raw)],target);g.take('48895118','4883c118');need('same-field-barrier',g.relative('e9')==symbols['barrier'])
 setter=dict(method=[method.index,wrapper.name,md.string(method.name_index),target-base],selectedBytes=g.seen,
  sourceRegions=[[target,raw.hex().upper()]],window=dict(startRva=target-base,endRva=target-base+13,sha256=hashlib.sha256(raw).hexdigest().upper()),
  fieldOffset=24,storedBytes=8,selectedBarrierFieldOffset=24,completeIncomingReferenceStoredUnchanged=True,entryFrameUnchanged=True,physicalExtentProved=False)
 offsets=scalar.reader_offsets(image,'storyOperaValue');header=vector_recorder(image)(symbols['header']-base)
 primitive_param.object_header_source(image,header,offsets);barrier,barrier_program,_=_fast_barrier(image,symbols['barrier'])
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-opera-value-wrapper',nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,
  layout=nominal,managedBytes=16,readerMethod=[reader.index,wrapper.name,'Deserialize',body['pointer']-base],
  sourceWindows=body['windows'],sourceRegions=[[a,h.hex().upper()]for a,h in body['regions']],programs=programs,
  leaves=leaves,allocation=allocation,memberSources=request_sources,arraySetter=setter,headerSource=header,
  symbolRvas={r:t-base for r,t in symbols.items()},barrier=dict(source=barrier,program=barrier_program),
  canonicalOriginalAdmitted=False,parametersElementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own inline16 MC2/FF/new/reused wrapper/source/store/frame, raw enum32 and actual typed ParamKeyValue reference-array source/count/context, whole16 zero/getter leaves.',
   conditional='Initialized metadata, compatible disjoint output/Reader/frame, sufficient buffered input, normal typed allocation and child/provider/callback ABI and disabled collector.',
   unresolved=['ParamKeyValue element callback/grammar join','canonical Original adapter/default/GetValue interface','actual parent array callback/local/store/frame','whole Module/physical EOF/publication']))))
