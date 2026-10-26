"""Own positive FactoryHide record and exact FCNode list/parent source joins."""
import json
TYPE='Beyond.Gameplay.LevelFunctionAreaData+FunctionAreaFactoryHideDesc'
PARENT='Beyond.Gameplay.LevelFunctionAreaData+FunctionAreaBaseData'
ENUM='Beyond.GEnums.FCNodeType'
LIST='System.Collections.Generic.List`1<'+ENUM+'>'
CAP='story-function-area-factory-hide'
LIST_CAP='skill-enum-list:'+ENUM
ELEMENT_CAP='skill-enum-callback:'+ENUM
LIMIT=4096
PLAN=(('hideAllBuildingUI','bool','bool-byte'),('hideFacBuilding','bool','bool-byte'),('hideFacBuildingAll','bool','bool-byte'),
 ('hideFacFence','bool','bool-byte'),('hideSocialFac','bool','bool-byte'),
 ('hideSocialFacOwner','Beyond.Gameplay.Factory.SocialFragment+EOwner','scalar32'),('showFacBuildingTypes',LIST,'factory-hide-enum-list'))


def bind_enums(pins,join,child,key):
 from scripts.game_data.memorypack.skill_enum_list_codec import require_capability
 cap=child.get('capabilities',{}).get(key,{})
 require_capability(cap,child.get('capabilities',{}).get(ELEMENT_CAP,{}),name=ENUM);usage=join.get('typedRequest',{})
 if(key!=LIST_CAP or child.get('nativeInputs')!=pins or cap.get('nativeInputs')!=pins
  or join.get('typeName')!=LIST or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[LIST]
  or not isinstance(usage.get('methodSpec'),(list,tuple))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or type(join.get('sourceTargetRva'))is not int
  or(usage['methodSpec'][0],join['sourceTargetRva'])!=(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])):
  raise ValueError('factoryHide.exact-own-enum-list-parent')
 return dict(fieldName=join['fieldName'],typeName=LIST,capability=LIST_CAP,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  actualNominalEnumCallbackRequired=True,runtimeFormatterSelectionObserved=False)


def bind_parent(pins,join,child,key):
 from scripts.game_data.codecs.leveldata.current_factory_hide import validate
 cap=child.get('capabilities',{}).get(key,{});validate(cap);usage=join.get('typedRequest',{})
 if(key!=CAP or child.get('nativeInputs')!=pins or join.get('typeName')!=TYPE or join.get('fieldName')!='factoryHideDesc'
  or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[TYPE]
  or not isinstance(usage.get('methodSpec'),(list,tuple))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or type(join.get('sourceTargetRva'))is not int
  or(usage['methodSpec'][0],join['sourceTargetRva'])!=(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])):
  raise ValueError('factoryHide.exact-ordinary-parent')
 return dict(fieldName='factoryHideDesc',typeName=TYPE,capability=CAP,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=join['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def bind_program(source,program,pending):
 if(pending or not isinstance(program,dict)or source.get('wrappedType')!=TYPE
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
  or type(program.get('memberCount'))is not int or program['memberCount']!=7
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,LIST_CAP if k=='factory-hide-enum-list'else None)for j,(n,t,k)in enumerate(PLAN)]
  or program.get('requiredCapabilities')!=[LIST_CAP]
  or[(b.get('fieldName'),b.get('typeName'),b.get('capability'))for b in program.get('childBindings',[])]!=[
   ('showFacBuildingTypes',LIST,LIST_CAP)]):raise ValueError('factoryHide.exact-seven-member-program')


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,enum_list_native_sources as enums,scalar_param_native as scalar
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 need=lambda k,e,a:scalar.need('factoryHide',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in(TYPE,PARENT)}
 need('exact-own-and-parent-wrappers',{TYPE,PARENT},set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in(TYPE,PARENT)])
 source,parent=[require_complete(row,validator='factoryHide',type_name=name)for name,row in zip((TYPE,PARENT),generated['owners'],strict=True)]
 need('exact-own-declarations',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 enum_source=enums.derive(image,pins);read=source['orderedSourceReads'][6]
 usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='factoryHide.actualEnumParent')
 enum_binding=enums.bind_request(image,pins,enum_source,typed_request=usage,call_target=base+read['sourceTargetRva'],enum_type=ENUM)
 component=dict(nativeInputs=pins,capabilities={k:enum_source['capabilities'][k]for k in(LIST_CAP,ELEMENT_CAP)})
 program,pending=compile_member_program(source,pins,wrapper_name=wrappers[TYPE].name,type_name=TYPE,value4={},typed_requests={6:usage},
  collections={LIST:(LIST_CAP,'factory-hide-enum-list',LIST_CAP)},collection_children={6:component},collection_binder=bind_enums)
 bind_program(source,program,pending)
 field=ctx.field(PLAN[5][1]+'::value__');need('own-Owner-enum','System.Enum',ctx.parent(PLAN[5][1]));need('own-Owner-backing',True,field[1]in('int','uint'))
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrappers[TYPE])
 need('whole-owned-original-output',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
 need('same-owned-getter',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
 need('same-owned-concrete-callback',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 abi=reference_reader_abi(image,pins)
 cap=dict(typeName=TYPE,memberCount=7,program=program,enumBacking=dict(typeName=PLAN[5][1],backing=field[1],field=list(field)),
  enumList=component['capabilities'][LIST_CAP],enumCallback=component['capabilities'][ELEMENT_CAP],countLimit=LIMIT,
  nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,ordinaryAdapterAdmitted=True,
  wholeGrammarAdmitted=False,actualCallbackEqualsProvedChildRequired=True,actualNominalEnumCallbackRequired=True,
  runtimeFormatterSelectionObserved=False,referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])
 actual,=[r for r in parent['orderedSourceReads']if r['fieldName']=='factoryHideDesc']
 need('exact-actual-parent-child',TYPE,actual['declaredType'])
 parent_usage=derive_typed_usage_context(image,actual['context']['instructionRva'],label='factoryHide.actualOrdinaryParent')
 cap['parentBinding']=dict(ownerType=PARENT,fieldName='factoryHideDesc',typeName=TYPE,capability=CAP,
  readerMethodDefinition=parent_usage['methodSpec'][0],sourceTargetRva=actual['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)
 binding=bind_parent(pins,dict(fieldName='factoryHideDesc',typeName=TYPE,typedRequest=parent_usage,sourceTargetRva=actual['sourceTargetRva']),
  dict(nativeInputs=pins,capabilities={CAP:cap}),CAP)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-factory-hide-components.v1',status='validated-conditional-factory-hide-profile',nativeInputs=pins,capability=cap,
  source=source,compiled=program,pair=pair,adapter=adapter,enumSource=enum_source,enumParent=enum_binding,
  parent=dict(source=parent,read=actual,typedRequest=parent_usage,binding=dict(binding,ownerType=PARENT)),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own complete ordinary seven-member caller/lifecycle/adapter/frame, nominal Owner enum, independently selected FCNode callback/list source and actual BaseData parent.',
   conditional='Initialized coherent nominal formatter/class/MethodInfo/registry/cache contexts, matching original callbacks and normally returning helpers, disabled barriers and disjoint buffered storage. Collection resource bound restricts the independent enum-list induction.',
   unresolved=['runtime replacements/provider selection and effective factory visibility','whole BaseData/LevelData grammar, EOF and public owner receipts']))))
