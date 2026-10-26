"""Exact Actor direct-holder construction inside its generated reader.

The independent current lifecycle owns the nominal allocation and holder.
The independently decoded noarg Original constructor owns its one enum default.
This fragment proves that same default and reference publication in the actual
reader; it invokes no Original constructor and owns no caller frame or grammar.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActor'
ENUM='Beyond.Gameplay.CharInteractPerformEnums+ActorType'


def need(key,condition):
 if not condition:raise ValueError('charActorInline.'+key)


def program(regions,entry,*,initialized_flag,allocator,disabled,wrapper='rdi',output='rsi'):
 from scripts.game_data.memorypack.generated_inline_constructor_sources import _edge,_nonnull
 from scripts.game_data.memorypack.pooled_string_list_sources import flag
 need('finite-direct-holder-registers',(wrapper,output)==('rdi','rsi'))
 need('independently-owned-roles',all(type(v)is int and v>0 for v in(initialized_flag,allocator,disabled)))
 g=BytesPath(regions,entry)
 need('same-own-constructor-ready-flag',flag(g,prefix='803d')==initialized_flag);_edge(g,zero=False)
 at=g.at;cell=g.relative('488b0d');allocation=dict(instructionVa=at,cellVa=cell)
 g.call(allocator);g.take('4885c0');null=_nonnull(g)
 default=g.at;g.take('c7401000000000');holder=g.at;g.take('48894710')
 collector=g.at;need('same-current-disabled-collector',g.relative('8b05')==disabled)
 g.take('85c0');_edge(g,zero=True)
 publication=g.at;g.take('48893e','85c0');_edge(g,zero=True)
 return dict(selectedBytes=g.seen,selectedEnd=g.at,initializedFlag=initialized_flag,allocation=allocation,
  allocatorTarget=allocator,wrapperRegister=wrapper,outputRegister=output,baseHolderOffset=16,typedCacheOffset=None,
  defaultFieldStores=[dict(instructionVa=default,offset=16,bytes=4,constantHex='00000000')],
  holderWrites=[dict(instructionVa=holder,role='sole-wrapper-holder',offset=16,bytes=8,sameAllocatedReference=True),
   dict(instructionVa=publication,role='parent-output',offset=0,bytes=8,sameFreshWrapper=True)],
  collectorLoadVa=collector,disabledCollectorAddress=disabled,ownedNullExit=null,
  originalConstructorCalled=False,sameIndependentlyOwnedOriginalDefaults=True,sameFreshOriginalInOwnedHolder=True,
  sameFreshWrapperInOutput=True,completeSelectedConstructionFragment=True,directHolderOnly=True,
  callerFrameProved=False,childGrammarAdmitted=False,metadataInitializationAdmitted=False,enabledCollectorAdmitted=False,
  condition='The exact current Actor class is initialized and fresh allocation succeeds. Its sole direct holder receives the whole fresh Original after the independently owned ActorType zero default; collector is disabled and EAX stays zero through output publication. Caller frame, field grammar and live runtime effects remain separate.')


def derive_fragment(image,pins,*,wrapper,lifecycle,rows,entry,wrapper_register,output_register,barrier):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_member_sources as members,generated_lifecycle_sources as lives,pointer_param as pointer,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_vector_member_sources import selected_rows
 from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 need('exact-current-Actor-direct-lifecycle',wrapper.wrapped_type==TYPE and not wrapper.wrapped_is_value_type
  and lifecycle.get('wrapperName')==wrapper.name and lifecycle.get('wrappedType')==TYPE
  and lifecycle.get('typeDefinition')==wrapper.type_definition and lifecycle.get('directHolderMode')is True
  and lifecycle.get('typedCache')is None and tuple(lifecycle.get('baseHolder',[])[:2])==(wrapper.name,TYPE)
  and lifecycle['baseHolder'][2]==16)
 ctor=pointer.methods(image,wrapper)['.ctor'];factory,=[f for f in lifecycle['factories']if f['method']==lives._method_row(image,ctor)]
 fp=factory['program'];fields=factory.get('initialization',{}).get('constantFields',[])
 need('same-independently-owned-direct-factory',fp.get('baseHolderOffset')==16 and fp.get('typedCacheOffset')is None
  and fp.get('sameAllocatedOriginalStored')is True and fp.get('inlineHolderWrites')==[dict(offset=16,bytes=8,sameAllocatedReference=True)]
  and len(fields)==1 and list(fields[0].get('field',[]))==[TYPE,ENUM,16]
  and fields[0].get('bytes')==4 and fields[0].get('constantHex')=='00000000')
 original,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='.ctor'and m.parameter_count==0 and not m.flags&16]
 scalar.owned_method_abi(image,ctx,original.index,original.declaring_type,('void',1,False),[],'charActorInline.OriginalCtor')
 defaults=lives._original_constructor(image,ctx,original,TYPE,pins=pins);leaf=defaults.get('reachableLeaf',{})
 stores=defaults.get('constantFieldStores',[])
 need('complete-own-noarg-Original-default-entry',defaults.get('completeReachableEntryProgramProved')is True
  and all(leaf.get(k)is True for k in('normalReturn','callFree','stackUnchanged','allNonvolatileRegistersUnchanged'))
  and len(stores)==1 and stores[0].get('offset')==16 and stores[0].get('bytes')==4 and stores[0].get('constantHex')=='00000000'
  and len(stores[0].get('fields',[]))==1 and stores[0]['fields'][0].get('owner')==TYPE
  and stores[0]['fields'][0].get('typeName')==ENUM and stores[0]['fields'][0].get('offset')==16 and stores[0]['fields'][0].get('bytes')==4)
 collector=_barrier(image,barrier);disabled=base+collector['result']['disabledFlagRva']
 parsed=program([(members.ec.va(r),members.ec.raw(r))for r in rows],entry,
  initialized_flag=fp['metadata'],allocator=fp['allocationTarget'],disabled=disabled,wrapper=wrapper_register,output=output_register)
 usage=derive_typed_usage_context(image,parsed['allocation']['instructionVa']-base,label='charActorInline.OriginalAllocation')
 need('same-fresh-exact-Original-class',usage.get('tag')==1 and usage.get('typeName')==TYPE
  and tuple(factory.get('originalAllocation',{}).get(k)for k in('tag','typeName'))==(1,TYPE)
  and parsed['allocation']['cellVa']==fp.get('allocation',{}).get('cell'))
 # Usage sites differ between factory and caller; only their exact nominal
 # class result and allocation helper are shared, never their MethodInfo site.
 fields=lives._holder_fields(image,ctx,wrapper.name,[16],lives._class_ancestry(ctx,TYPE))
 need('same-only-owned-holder-field',len(fields)==1 and list(fields[0])==list(lifecycle['baseHolder']))
 selected=selected_rows(rows,parsed['selectedBytes']);_publication_gate(image,pins)
 return dict(schema='endfield.generated-inline-constructor-fragment.v1',nativeInputs=dict(pins),wrapperName=wrapper.name,wrappedType=TYPE,
  wrapperConstructorMethod=factory['method'],program=parsed,originalAllocation=usage,originalConstructor=defaults,
  ownedHolderFields=fields,directHolderOnly=True,collector=collector,selectedProgram=[members.ec.site(r,base)for r in selected],
  sameFreshWrapperInOutput=True,completeSelectedConstructionFragment=True,callerFrameProved=False,childGrammarAdmitted=False,wholeOwnerAdmitted=False)
