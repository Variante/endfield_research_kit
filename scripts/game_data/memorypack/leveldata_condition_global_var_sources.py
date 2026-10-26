"""Finite tag9 condition leaf and separately selected current union transfer.

This owner does not evaluate global variables or promote any historical inline
reader. Concrete source/lifecycle/adapter and the union case join separately.
"""
import json

TYPE='Beyond.Gameplay.SimpleConditionCheckGlobalVar'
BASE='Beyond.Gameplay.ConditionRuntimeBase'
TAG=9
CAP_SCHEMA='endfield.story-condition-runtime-global-var-capability.v1'
CAP='story-condition-runtime'
PLAN=(('compareOperator','Beyond.GEnums.CompareOperator','scalar32'),('compareTarget','int','scalar32'),
 ('globalVarName','string','byte-payload'))


def bind_program(source,program,pending):
 if(pending or source.get('wrappedType')!=TYPE or not isinstance(program,dict)
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
  or type(program.get('memberCount'))is not int or program['memberCount']!=3
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,t,k)in enumerate(PLAN)]
  or program.get('requiredCapabilities')!=['byte-payload']or program.get('childBindings')!=[]):
  raise ValueError('storyConditionGlobalVar.exact-finite-source')


def derive_leaf(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 need=lambda k,e,a:scalar.need('storyConditionGlobalVar',k,e,a)
 _publication_gate(image,pins);ctx=NativeReferenceContext(image);base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 row=generated_reader_sources.derive_many(image,pins,[wrapper.name])['owners'][0]
 source=require_complete(row,validator='storyConditionGlobalVar',type_name=TYPE)
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={})
 bind_program(source,program,pending)
 pair=derive_pair(image,TYPE,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
 need('full-original-output',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
 need('same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
 need('same-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 enum_type=PLAN[0][1];need('own-operator-enum','System.Enum',ctx.parent(enum_type));enum=ctx.field(enum_type+'::value__')
 need('exact-word-backed-operator',True,enum[1]in('int','uint'))
 pooled_read,=[r for r in source['orderedSourceReads']if r['fieldName']=='globalVarName']
 pooled=pooled_source_helper.validate_on_image(image,base+pooled_read['sourceTargetRva'],pins)
 cap=dict(typeName=TYPE,memberCount=3,program=program,
  enumBacking=dict(typeName=enum_type,backing=enum[1],field=list(enum)),signedCompareTargetBits=32,
  nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=True,
  actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
 from scripts.game_data.codecs.leveldata.current_condition_global_var import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-global-var-leaf.v1',status='validated-conditional-current-leaf',
  nativeInputs=pins,typeName=TYPE,capability=cap,source=source,pair=pair,adapter=adapter,pooled=pooled,
  unionSelectionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Only this nominal current three-member reader/lifecycle/getter/adapter, own CompareOperator backing, signed Int32 target and actual pooled-string source.',
   conditional='Ready matching callbacks/contexts and coherent wrapper/original/cache, normal helper effects and buffered disjoint storage.',
   unresolved=['current union selection and inherited conversion','actual enclosing parent','runtime global-variable lookup/listening/evaluation','whole owner/physical EOF']))))


def derive_transport(image,pins):
 """Extend a freshly re-proved base transport with exactly the actual tag9."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import _vtable,derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import pointer_param as pointer,reference_adapter_sources,scalar_param_native as scalar
 from scripts.game_data.memorypack.current_reference_union_sources import _lineage
 from scripts.game_data.memorypack.leveldata_condition_runtime_sources import derive_transport as derive_base
 from scripts.game_data.memorypack.skill_action_union_sources import original_lineage
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 from scripts.game_data.memorypack.skill_selector_union_sources import finder_program,closed_packable_thunk_program
 from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
 need=lambda k,e,a:scalar.need('storyConditionGlobalVarTransport',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
 common=derive_base(image,pins);switch=common['switch'];entry=int(switch['dispatcherVa'],16)
 body=pointer.owned(image,entry);need('same-actual-owned-dispatcher',common['ownedWindows'],body['windows'])
 parent,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==BASE]
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 selected,=[r for r in switch['entries']if r['tag']==TAG]
 need('exact-current-tag9-child',wrapper.name,selected['wrapperName'])
 need('direct-indexed-table-case',selected['targetVa'],selected['bodyVa']);at=int(selected['bodyVa'],16);table=int(switch['tableVa'],16)
 first=common['programs'][0];first_at=int(switch['entries'][first['tag']]['bodyVa'],16)
 cast_raw=image.pe.bytes_at_va(first_at+10,5);need('fresh-base-cast-E8',b'\xe8',cast_raw[:1])
 cast=first_at+15+int.from_bytes(cast_raw[1:],'little',signed=True)
 packable=common['referencePackable']['source']['selectedBytes'][0][0]
 symbols=dict(imageBase=base,header=first['source']['headerTarget'],packable=packable,cast=cast,barrier=first['source']['barrierTarget'])
 thunk=None
 if image.pe.bytes_at_va(at+23,3)!=bytes.fromhex('488b15'):
  raw=image.pe.bytes_at_va(at+23,5);need('actual-child-closed-thunk-E8',b'\xe8',raw[:1]);actual=at+28+int.from_bytes(raw[1:],'little',signed=True)
  thunk=closed_packable_thunk_program(image.pe.bytes_at_va(actual,12),actual,packable);symbols['closedPackable']=actual
 program=finder_program(body['regions'],entry,symbols,tag=TAG,count=50,table=table,selected=at)
 context=program['childUsage']['instruction']if program['childUsage']is not None else thunk['contextInstruction']
 usage=derive_typed_usage_context(image,context-base,label='storyConditionGlobalVarTransport.child')
 typed=bind_typed_read(image,usage,method_name='ReadPackable',argument=wrapper.name,kind=18,reference=True)
 need('owned-packable-definition',common['referencePackable']['packableContext']['packableDefinition'],typed['methodDefinition'])
 cast_usage=derive_typed_usage_context(image,program['castUsage']['instruction']-base,label='storyConditionGlobalVarTransport.cast')
 need('actual-selected-cast',(1,wrapper.name),(cast_usage['tag'],cast_usage['typeName']))
 word=image.pe.u32_at_va(table+4*TAG);need('exact-current-table-word',at,base+word)
 holder=_wrapper_holder(ctx,image,wrapper);need('same-inherited-original-holder',(BASE,16),(holder['declaredType'],holder['offset']))
 face,=common['pair']['composition']['interfaces'];td=md.types[wrapper.type_definition];section=md.sections['interfaceOffsets']
 start=section.offset+td.interface_offsets_start*8
 import struct
 faces=list(struct.iter_unpack('<ii',md.buf[start:start+td.interface_offsets_count*8]))
 joined=[(ordinal,offset)for ordinal,(index,offset)in enumerate(faces)if index==face['interfaceTypeIndex']]
 need('one-owned-inherited-interface',1,len(joined));ordinal,offset=joined[0]
 getter=pointer.methods(image,parent)['GetValue'];getter_entry=image.method_pointer_va(getter)
 _vtable(image,wrapper.type_definition,offset,getter.index,'storyConditionGlobalVarTransport.getter')
 conversion_entry=base+common['adapter']['canonicalRoutes']['symbolRvas']['conversion'];conversion=pointer.owned(image,conversion_entry)
 converted=reference_adapter_sources.conversion(conversion['regions'],conversion_entry,
  base+common['adapter']['canonicalRoutes']['conversionPrepareRva'],getter_entry,ordinal=ordinal)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-global-var-transport.v1',
  status='validated-conditional-tag9-transport',nativeInputs=pins,typeName=BASE,tag=TAG,wrappedType=TYPE,wrapperName=wrapper.name,
  currentBase=common,source=program,typedRequest=usage,typedArgument=typed,closedPackableThunk=thunk,nullableCast=cast_usage,
  tableEntry=dict(rva=table+4*TAG-base,rawHex=word.to_bytes(4,'little').hex().upper(),unsignedTargetRva=word),
  originalLineage=original_lineage(image,ctx,wrapper,BASE),wrapperLineage=_lineage(ctx,md,wrapper.name,parent.name),
  inheritedConversion=dict(interfaceOrdinal=ordinal,interfaceOffset=offset,interfaceTypeIndex=face['interfaceTypeIndex'],
   baseGetValueMethod=getter.index,holder=holder,conversion=converted),
  concreteChildGrammarAdmitted=False,wholeUnionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  liveFormatterSelectionObserved=False)))


def derive(image,pins):
 """Fresh same-image leaf and selected route, without widening the full union."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.scalar_param_native import need
 _publication_gate(image,pins);transport=derive_transport(image,pins);leaf=derive_leaf(image,pins)
 need('storyConditionGlobalVar','same-current-wrapper',(transport['wrapperName'],TYPE),
  (leaf['source']['wrapperName'],leaf['source']['wrappedType']))
 need('storyConditionGlobalVar','same-concrete-callback',leaf['pair']['composition']['interfaces'][0]['formatterDeserializeMethodIndex'],
  leaf['source']['lifecycle']['concreteFormatter']['method'][0])
 route=dict(tag=TAG,typeName=TYPE,wrapperName=transport['wrapperName'],wrapperNullAdmitted=True,
  capability=leaf['capability'],actualWrapperCallbackEqualsProvedConcreteRequired=True)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-global-var-component.v1',
  status='validated-conditional-tag9-component',nativeInputs=pins,transport=transport,leaf=leaf,route=route,
  wholeUnionAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))


def derive_opt_in(image,pins):
 """A separate finite five-route scope; the default four-route owner is intact."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.leveldata_condition_components import derive as derive_base
 from scripts.game_data.memorypack.scalar_param_native import need
 _publication_gate(image,pins);extension=derive(image,pins);original=derive_base(image,pins)
 need('storyConditionGlobalVar','same-fresh-base-transport',original['transport'],extension['transport']['currentBase'])
 base=original['capability']
 cap=dict(schema=CAP_SCHEMA,capability=CAP,typeName=BASE,baseCapability=base,tag9Route=extension['route'],
  admittedRouteTags=[0,9,12,13,18],countLimit=base['countLimit'],nodeLimit=base['nodeLimit'],depthLimit=base['depthLimit'],
  referenceReaderMethodDefinition=base['referenceReaderMethodDefinition'],referenceReaderTargetRva=base['referenceReaderTargetRva'],
  profileAdmitted=True,nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=False,
  actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
 from scripts.game_data.codecs.leveldata.current_condition_global_var import validate_union
 validate_union(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-condition-global-var-opt-in-components.v1',
  status='validated-conditional-five-route-condition-opt-in',nativeInputs=pins,capability=cap,base=original,extension=extension,
  defaultConditionOwnerChanged=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))


def bind_reference(pins,join,child,capability):
 """Only the actual Dock filter parent selects this explicit opt-in scope."""
 from scripts.game_data.codecs.leveldata.current_condition_global_var import validate_union
 cap=child.get('capabilities',{}).get(capability,{});usage=join.get('typedRequest',{})
 if(capability!=CAP or child.get('nativeInputs')!=pins or join.get('typeName')!=BASE or join.get('fieldName')!='filterCondition'
  or(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))!=
   (6,'MemoryPack.MemoryPackReader','ReadValue',[],[BASE])
  or not isinstance(usage.get('methodSpec'),(list,tuple))or len(usage['methodSpec'])!=3
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or(cap.get('referenceReaderMethodDefinition'),cap.get('referenceReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyConditionGlobalVar.exact-opt-in-Dock-reference-parent')
 validate_union(cap)
 return dict(fieldName=join['fieldName'],typeName=BASE,capability=CAP,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=join['sourceTargetRva'],admittedRouteTags=list(cap['admittedRouteTags']),conditionCapabilitySchema=CAP_SCHEMA,
  profileAdmitted=True,wholeGrammarAdmitted=False,actualCallbackEqualsProvedChildRequired=True)
