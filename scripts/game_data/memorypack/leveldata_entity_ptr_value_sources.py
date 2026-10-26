"""Actual EntityPtr hidden40 source and physical layout, without a Param parent.

The three serialized fields and runtime-only ObjectPtr<Entity> storage remain
distinct. The selected dedicated EntityPtr owner supplies its own canonical
MC3/FF/default40 programs; the actual enclosing parent still owns its hidden
local, complete field transfer, setter, barrier and frame. Provider selection,
cache coherence and runtime entity resolution are conditional or unobserved.
"""
import hashlib
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='Beyond.Gameplay.Core.EntityPtr'
OBJECT='Beyond.ObjectPtr`1<Beyond.Gameplay.Core.Entity>'
ENTITY='Beyond.Gameplay.Core.Entity'
LABEL='storyEntityPtrValueSource'


def need(check,expected,actual):scalar.need(LABEL,check,expected,actual)


def require_runtime_accessor_carrier(field,accessor):
 """The accessor must name the same closed carrier, without a GC-map claim."""
 keys=('definition','classInstantiationIndex','classArguments')
 need('accessor-own-closed-carrier',tuple(field[k]for k in keys),tuple(accessor.get(k)for k in keys))


def read_program(regions,entry,*,provider,dispatch):
 """Complete initialized warm provider-nonnull hidden40 caller path."""
 g=BytesPath(regions,entry)
 g.take('48895c2408','4889742410','57','4883ec20','4983783800','498bf8','488bf2','488bd9')
 g.branch('74',False,1)
 g.take('0f57c0','33c0','0f1103','0f114310','48894320');cell=g.relative('488b0d')
 g.take('3981e0000000');g.branch('74',False,1)
 g.take('488b4f38','488b09');g.call(provider);g.take('4885c0');g.branch('74',False,1)
 g.take('4c8bcb','4c8bc6','488bd0');g.call(dispatch)
 g.take('488bc3','488b5c2430','488b742438','4883c420','5f','c3')
 return dict(selectedBytes=g.seen,providerClassCell=cell,outputBytes=40,zeroedOutputBytes=40,
  readerRegister='incoming rdx',inputMethodInfoRegister='incoming r8',hiddenOutputRegister='incoming rcx',
  dispatchReaderRegister='r8',dispatchOutputRegister='r9',formatterRegister='rdx',providerContextSlot=0,
  sameIncomingReaderAndOutput=True,sameOutputReturnedInRax=True,normalReturn=True,
  selectedFrameBytes=40,entryRspRestored=True,allIntegerNonvolatilesRestored=True,
  savedEntryHomes=dict(rbx=[8,16],rsi=[16,24]),pushedNonvolatiles=['rdi'],
  actualMatchingCanonicalCallbackRequired=True,providerNonnullRequired=True,wireGrammarAdmitted=False)


def object_getter_program(regions,entry):
 """Original EntityPtr's own hidden16 runtime-field getter, not a wrapper."""
 g=BytesPath(regions,entry);g.take('0f104218','488bc1','0f1101','c3')
 return dict(selectedBytes=g.seen,receiverRegister='rdx',hiddenOutputRegister='rcx',fieldValueOffset=24,
  copiedBytes=16,sameOutputReturnedInRax=True,stackAndNonvolatilesUntouched=True,normalReturn=True,
  completeNormalLeafProved=True,physicalFunctionExtentProved=False,wireGrammarAdmitted=False)


def object_setter_program(regions,entry,barrier):
 """Own original field copy/tail; its GC/reference meaning remains a join."""
 g=BytesPath(regions,entry);g.take('0f1002','0f114118','4883c118')
 need('own-object-setter-barrier',barrier,g.relative('e9'))
 return dict(selectedBytes=g.seen,receiverRegister='rcx',sourcePointerRegister='rdx',fieldValueOffset=24,
  copiedBytes=16,selectedBarrierAddressOffset=24,normalTailReturn=True,stackAndNonvolatilesUntouched=True,
  completeNormalLeafProved=True,physicalFunctionExtentProved=False,referenceLaneSemanticsProved=False,wireGrammarAdmitted=False)


def whole_setter_program(regions,entry,barrier):
 """Dedicated EntityPtr wrapper's unchanged complete40 copy and barrier slot."""
 g=BytesPath(regions,entry)
 g.take('0f1002','0f104a10','0f114110','f20f104220','0f114920','f20f114130','4883c128')
 need('own-whole-value-setter-barrier',barrier,g.relative('e9'))
 return dict(selectedBytes=g.seen,managedBytes=40,inlineHolderOffset=16,copiedSlices=[[0,16],[16,16],[32,8]],
  selectedBarrierAddressOffset=40,selectedBarrierValueOffset=24,allSourceBitsPreserved=True,
  normalTailReturn=True,stackAndNonvolatilesUntouched=True,physicalFunctionExtentProved=False,
  referenceLaneSemanticsProved=False,wireGrammarAdmitted=False)


def derive_layout(image,*,type_pointer):
 """Own full storage/accessor bits; runtime ObjectPtr internals remain opaque."""
 from scripts.game_data.il2cpp.context import type_parameter_owner
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
 from scripts.game_data.memorypack import pointer_param as pointer
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
 ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;td=ctx.index.types[TYPE]
 scalar.ordinary(image,type_pointer,17,LABEL+'.EntityPtr')
 raw=image.pe.bytes_at_va(type_pointer,16)
 need('exact-value17-128',(td.index,b'\x11\x80'),(int.from_bytes(raw[:8],'little'),raw[10:12]))
 need('nominal-value',(True,False,'System.ValueType',-1),(ctx.is_value_type(TYPE),ctx.is_enum(TYPE),ctx.parent(TYPE),td.generic_container_index))
 fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
 expected=[('useSlotId','bool',16),('logicId','ulong',24),('slotId','uint',32),('<objectPtr>k__BackingField',OBJECT,40)]
 need('complete-physical-fields',expected,[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields])
 for f,kind in zip(fields,(2,11,9,21),strict=True):scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,LABEL+'.field')
 need('bounded-size-row',True,0<=td.index<image.registration['typeDefinitionsSizesCount'])
 size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*td.index)
 need('boxed-and-unknown-marshaling-size',(56,0xffffffff),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
 # Authenticate the actual runtime-only carrier and owned declarations. Its
 # closed runtime field offsets/GC map are deliberately not inferred from the
 # open generic definition, a same-sized pointer, or a generated wrapper.
 closed=ContextSymbols(image).type(ctx.type_pointer(fields[-1].type_index));definition=ctx.index.types['Beyond.ObjectPtr`1']
 need('exact-closed-runtime-object',(OBJECT,'Beyond.ObjectPtr`1'),(closed['name'],closed['definition']['name']))
 need('exact-closed-runtime-value21',b'\x15\x80',image.pe.bytes_at_va(ctx.type_pointer(fields[-1].type_index),16)[10:12])
 definition_raw=image.pe.bytes_at_va(closed['definition']['typePointerVa'],16)
 scalar.ordinary(image,closed['definition']['typePointerVa'],17,LABEL+'.ObjectPtrDefinition')
 need('exact-owned-generic-definition',definition.index,int.from_bytes(definition_raw[:8],'little'))
 argument,=closed['classArguments'];need('exact-Entity-argument',ENTITY,argument['name'])
 scalar.ordinary(image,argument['typePointerVa'],18,LABEL+'.Entity',reference=True)
 need('Entity-class',False,ctx.is_value_type(ENTITY))
 object_fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
 need('own-open-field-declarations',['obj','cachedUid'],[md.string(f.name_index)for f in object_fields])
 obj,uid=object_fields;var=image.pe.bytes_at_va(ctx.type_pointer(obj.type_index),16)
 scalar.ordinary(image,ctx.type_pointer(obj.type_index),19,LABEL+'.ownedT')
 parameter=type_parameter_owner(md.buf,int.from_bytes(var[:8],'little'),[t.generic_container_index for t in md.types],source=LABEL)
 need('reciprocal-owned-T',(definition.index,0),(parameter['typeIndex'],parameter['ordinal']))
 scalar.ordinary(image,ctx.type_pointer(uid.type_index),9,LABEL+'.cachedUid');need('own-UInt32-uid','uint',ctx.type_name(uid.type_index))
 originals={}
 for name,result,arguments in(('get_objectPtr',(OBJECT,21),[]),('set_objectPtr',('void',1),[(OBJECT,21)])):
  method,=[m for m in md.methods_for(td)if md.string(m.name_index)==name]
  need('own-value-accessor-ABI',(td.index,0,-1,len(arguments)),
   (method.declaring_type,method.flags&16,method.generic_container_index,method.parameter_count))
  parameters=list(md.parameters_for(method));need('own-value-accessor-parameters',len(arguments),len(parameters))
  declared=[method.return_type,*[p.type_index for p in parameters]];types=[]
  for index,(type_index,(type_name,kind))in enumerate(zip(declared,[result,*arguments],strict=True)):
   at=ctx.type_pointer(type_index);scalar.ordinary(image,at,kind,LABEL+'.originalAccessor')
   need('own-value-accessor-declared-type',type_name,ctx.type_name(type_index))
   declared=dict(typeName=type_name,rawTypeHex=image.pe.bytes_at_va(at,16).hex().upper())
   if type_name==OBJECT:
    need('own-constructed-value21',b'\x15\x80',image.pe.bytes_at_va(at,16)[10:12])
    selected=ContextSymbols(image).type(at);require_runtime_accessor_carrier(closed,selected);declared['closedCarrier']=selected
   types.append(declared)
  originals[name]=(method,dict(method=[method.index,TYPE,name],declaredTypes=types,receiverValueType=True))
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 need('own-inline-whole-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
 whole=pointer.methods(image,wrapper)['set____instance']
 scalar.owned_method_abi(image,ctx,whole.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],LABEL+'.wholeSetter')
 need('whole-value-parameter17',b'\x11\x80',image.pe.bytes_at_va(ctx.type_pointer(list(md.parameters_for(whole))[0].type_index),16)[10:12])
 def bounded(method,size,prover,*,tail=False):
  at=image.method_pointer_va(method);body=image.pe.bytes_at_va(at,size)
  target=at+size+int.from_bytes(body[-4:],'little',signed=True)if tail else None
  program=prover([(at,body)],at,target)if tail else prover([(at,body)],at)
  return dict(methodIndex=method.index,entryRva=at-base,
   sourceWindow=dict(startRva=at-base,endRva=at-base+size,sha256=hashlib.sha256(body).hexdigest().upper()),
   sourceRegions=[[at,body.hex().upper()]],program=program,physicalFunctionExtentProved=False),target
 getter,getter_abi=originals['get_objectPtr'];pointer.leaf(image,image.method_pointer_va(getter),['0F104218','488BC1','0F1101','C3'])
 hidden,_=bounded(getter,11,object_getter_program)
 setter,setter_abi=originals['set_objectPtr'];field_setter,target=bounded(setter,16,object_setter_program,tail=True)
 whole_setter,whole_target=bounded(whole,34,whole_setter_program,tail=True)
 need('same-selected-barrier-helper',target,whole_target)
 barrier,barrier_program,_=_fast_barrier(image,target)
 return json.loads(json.dumps(dict(typeName=TYPE,typeDefinition=td.index,managedBytes=40,
  knownPaddingByteRanges=[[1,8],[20,24]],opaqueRuntimeStorageRanges=[[24,40]],selectedBarrierValueOffsets=[24],
  runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,fields=[list(f)for f in expected],
  boxedBytes=56,marshaledNativeBytes=0xffffffff,unknownMarshalSizeUsedForManagedWidth=False,
  actualTypeRawHex=raw.hex().upper(),runtimeOnlyObjectPtr=dict(typeName=OBJECT,storageByteRange=[24,40],
   closedCarrier=closed,ownedParameter=parameter,getterAbi=getter_abi,setterAbi=setter_abi,
   getter=hidden,setter=field_setter,wholeWrapperSetter=whole_setter,barrierTargetRva=target-base,
   barrier=barrier,barrierProgram=barrier_program,selectedBarrierValueOffset=24,
   runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,
   openGenericOffsetsUsed=False,formatterOrWireGrammarAdmitted=False),
  wireGrammarAdmitted=False,providerOrRuntimeSelectionAdmitted=False)))


def derive_read_value(image,pins,*,typed_request,source_target):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data import levelscript_entity_ptr_param_native as native
 from scripts.game_data.levelscript_family_regenerate import Build
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context
 from scripts.game_data.il2cpp.initializer_control import control_transfer
 from scripts.game_data.il2cpp.rgctx_symbols import validate_claims
 from scripts.game_data.memorypack import entity_ptr_param,pointer_param as pointer
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 _publication_gate(image,pins);base=image.pe.image_base
 need('literal-actual-source-target',True,type(source_target)is int and source_target>base)
 path=native.DEFAULT_CONTRACT;before=path.read_bytes();fact=native._contract(path)
 need('dedicated-current-EntityPtr-owner',pins,fact['nativeInputs'])
 clone_path=CONTRACTS_DIR/'memorypack_reader_clones_native.json';clones_before=clone_path.read_bytes()
 validate_typed_usage_context(image,typed_request,label=LABEL+'.actualCaller')
 binding=bind_typed_read(image,typed_request,method_name='ReadValue',argument=TYPE,kind=17)
 layout=derive_layout(image,type_pointer=binding['argumentPointer'])
 actual=entity_ptr_param.derive(image,pins,fact['profile'])
 validate_claims(fact['proof'],actual,label=LABEL+'.dedicatedProof');validate_claims(actual,fact['proof'],label=LABEL+'.dedicatedDeclaration')
 need('exact-own-closed-reader-spec',actual['outer']['valueContext']['methodSpec'],list(typed_request['methodSpec']))
 # Force the complete reviewed hidden40 gate even if a name resolves here.
 Build(image,pins).prove_reader_clone_target(source_target,'MemoryPack.MemoryPackReader.ReadValue',result_abi='hidden-output-40')
 source=pointer.owned(image,source_target);calls=[control_transfer(r)['target']for r in source['rows']if control_transfer(r)['kind']=='call']
 need('warm-provider-dispatch-and-cold-helpers',True,len(calls)>=2)
 dispatch,= [r for r in fact['profile']['actualAdapter']['records']if r['role']=='actual-dispatch']
 need('actual-selected-EntityPtr-dispatch',base+dispatch['entryRva'],calls[1])
 program=read_program(source['regions'],source_target,provider=calls[0],dispatch=calls[1])
 need('complete-hidden40-source',40,program['outputBytes'])
 _publication_gate(image,pins);need('dedicated-contract-bookend',before,path.read_bytes());need('reviewed-reader-bookend',clones_before,clone_path.read_bytes())
 return json.loads(json.dumps(dict(schema='endfield.story-entity-ptr-value-source.v1',status='validated-conditional-source',
  nativeInputs=pins,typeName=TYPE,managedBytes=40,resultAbi='hidden-local',readerMethodDefinition=typed_request['methodSpec'][0],
  sourceTargetRva=source_target-base,actualSourceProved=True,knownPaddingByteRanges=layout['knownPaddingByteRanges'],
  opaqueRuntimeStorageRanges=layout['opaqueRuntimeStorageRanges'],selectedBarrierValueOffsets=layout['selectedBarrierValueOffsets'],
  runtimeReferenceLayoutAdmitted=False,completeRuntimePaddingMapAdmitted=False,
  positiveWireBytes=14,nullWireBytes=1,wireMemberCount=3,runtimeOnlyObjectPtr=True,rawBoolNormalization='nonzero',
  actualCallbackEqualsProvedChildRequired=True,coherentWrapperStorageRequired=True,wireGrammarAdmitted=False,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(typedRequest=typed_request,typedReadBinding=binding,
   layout=layout,actualProgram=program,actualWindows=source['windows'],actualSourceRegions=[[a,raw.hex().upper()]for a,raw in source['regions']],
   dedicatedContract=path.name,leaf=actual['leaf'],adapter=actual['adapter'],conversion=actual['conversion'],
   forwarders=[r for r in actual['forwarders']if r['originalType']==TYPE],slotTransfer=actual['slotTransfer'],
   adapterRegistration=actual['adapterRegistration']),evidenceBoundary=dict(
    exact='Actual nominal ReadValue<EntityPtr> MethodSpec and independently reviewed/replayed hidden40 source, own complete40 setter and runtime-field getter/setter bits, exact selected barrier address, dedicated MC3/FF/default40 and canonical selected transfer programs.',
    conditional=__doc__,unresolved=['actual enclosing hidden local/field/setter/frame','runtime formatter/provider/cache selection or Entity resolution','whole owner/physical EOF']))))
