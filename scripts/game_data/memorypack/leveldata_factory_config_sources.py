"""Finite current Blackbox/Predefined graph; every parent remains an own join."""
import json
from scripts.game_data.memorypack import leveldata_leaf_record_sources as leaves

PREFIX='Beyond.Gameplay.'
BLACKBOX=PREFIX+'LevelDataBlackbox'
PREDEFINED=PREFIX+'PredefinedParam'
PREDEFINED_HOST=PREFIX+'LevelFactoryPredefinedParamData'
TEMPLATE=PREFIX+'PredefinedParamTemplate'
LANG='Beyond.LangKey'
LIMIT=4096
NODE_LIMIT=32768
CAP='story-factory-config-graph'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
LEAF_NAMES=tuple(PREFIX+n for n in(
 'LevelDataBlackboxBasic','LevelDataBlackBoxCompleteCondition','LevelDataBlackBoxTaskConfig',
 'LevelDataBlackBoxIntroEffectConfig','LevelDataBlackboxGeneralAbilityEntry','InventoryItemBundle',
 'InventoryItemBundleWithInfinite','CommonItemBundle','SocialBuildingConfig','HUBSelectorPort',
 'PredefinedParamComponent_Cache','PredefinedParamComponent_EnvGenWithActivator','PredefinedParamComponent_PowerDiffuser',
 'PredefinedParamComponent_PowerGate','PredefinedParamComponent_PowerPole','PredefinedParamComponent_PowerPort',
 'PredefinedParamComponent_Selector','PredefinedParamComponent_SewageTreatPlantExport','PredefinedParamComponent_SewageTreatPlantImport',
 'PredefinedParamComponent_TravelPole','PredefinedParamComponent_Valve'))
R=lambda n:PREFIX+n
REF=lambda field,name:(field,R(name),'factory-config-record')
SEQ=lambda field,name:(field,LIST(R(name)),'factory-config-record-list')
STRINGS=lambda field:(field,LIST('string'),'pooled-string-list')
PLANS={name:leaves.PLANS[name]for name in LEAF_NAMES}
PLANS.update({
 R('PredefinedParamComponent_Common'):(('disable','bool','bool-byte'),('forbidDelete','bool','bool-byte'),
  ('forbidMove','bool','bool-byte'),('initialDoNotPlace','bool','bool-byte'),('initialHide','bool','bool-byte'),
  ('isSocialBuilding','bool','bool-byte'),('needRepair','bool','bool-byte'),SEQ('repairNeedItem','CommonItemBundle'),REF('socialBuildingConfig','SocialBuildingConfig')),
 R('PredefinedParamComponent_FluidContainer'):(('itemInfinite','bool','bool-byte'),('lockManualInout','bool','bool-byte'),REF('prePlacedItem','CommonItemBundle')),
 R('PredefinedParamComponent_FluidReaction'):(('preFinalCacheUnlock','bool','bool-byte'),STRINGS('visibleFormulas')),
 R('PredefinedParamComponent_GridBox'):(SEQ('content','CommonItemBundle'),('defaultStorageMode','bool','bool-byte'),('enableAutoTransfer','bool','bool-byte'),('lockManualInOut','bool','bool-byte')),
 R('PredefinedParamComponent_Hub'):(('powerGenerate','int','scalar32'),('powerSaveAmount','int','scalar32'),SEQ('selectors','HUBSelectorPort')),
 R('PredefinedParamComponent_Miner'):(STRINGS('forbiddenMineItems'),),
 R('PredefinedParamComponent_Producer'):(('enableModeSwitch','bool','bool-byte'),('forbidLiquidMode','bool','bool-byte'),STRINGS('limitedFormulaIds'),
  ('lockFormulaId','string','byte-payload'),('modeCustom0','string','byte-payload'),('modeCustom1','string','byte-payload'),('modeUseCustom','bool','bool-byte'),('useMode','string','byte-payload')),
 R('PredefinedParamComponent_Sign'):(('contents',LIST('int'),'int32-list'),),
 R('PredefinedParamComponent_UdPipeLoaderUnloader'):(('connUdPipeNode','string','byte-payload'),REF('container','PredefinedParamComponent_FluidContainer')),
 PREDEFINED:tuple(REF(field,'PredefinedParamComponent_'+suffix)for field,suffix in(
  ('cache','Cache'),('common','Common'),('envGenWithActivator','EnvGenWithActivator'),('fluidContainer','FluidContainer'),
  ('fluidReaction','FluidReaction'),('gridBox','GridBox'),('hub','Hub'),('miner','Miner'),('powerDiffuser','PowerDiffuser'),
  ('powerGate','PowerGate'),('powerPole','PowerPole'),('powerPort','PowerPort'),('producer','Producer'),('selector','Selector'),
  ('sewageTreatPlantExport','SewageTreatPlantExport'),('sewageTreatPlantImport','SewageTreatPlantImport'),('sign','Sign'),
  ('travelPole','TravelPole'),('udPipe','UdPipeLoaderUnloader'),('valve','Valve'))),
 PREDEFINED_HOST:(('instKey','string','byte-payload'),REF('param','PredefinedParam')),
 TEMPLATE:(REF('predefinedParam','PredefinedParam'),('templateId','string','byte-payload')),
 R('LevelDataBlackBoxBuildingCraft'):(STRINGS('limitedBuildingCraftIds'),),
 R('LevelDataBlackboxDiscardItem'):(('forbidAllItemDiscard','bool','bool-byte'),STRINGS('forbidItems')),
 R('LevelDataBlackBoxEquipCraft'):(STRINGS('limitedEquipCraftIds'),),
 R('LevelDataBlackBoxFailTaskConfig'):(('failInfo',LANG,'lang-key'),('levelScriptId','ulong','scalar64-bits'),('taskId','string','byte-payload')),
 R('LevelDataBlackboxGeneralAbility'):(SEQ('customAbilityStates','LevelDataBlackboxGeneralAbilityEntry'),),
 R('InventoryContentInfo'):(SEQ('bagContent','InventoryItemBundle'),('bagSlotCount','int','scalar32'),
  SEQ('depotContent','InventoryItemBundleWithInfinite'),('depotManualInOutLocked','bool','bool-byte')),
 R('LevelDataBlackBoxManualCraft'):(STRINGS('limitedManualCraftIds'),),
 R('LevelDataBlackBoxBluePrint'):(STRINGS('presetBpKey'),),
 R('LevelDataBlackBoxStatistics'):(STRINGS('limitedStatisticItemIds'),),
 BLACKBOX:(REF('basic','LevelDataBlackboxBasic'),REF('buildingCraft','LevelDataBlackBoxBuildingCraft'),
  REF('completeCondition','LevelDataBlackBoxCompleteCondition'),REF('discardItem','LevelDataBlackboxDiscardItem'),
  REF('equipCraft','LevelDataBlackBoxEquipCraft'),SEQ('extraTask','LevelDataBlackBoxTaskConfig'),SEQ('failTask','LevelDataBlackBoxFailTaskConfig'),
  REF('generalAbility','LevelDataBlackboxGeneralAbility'),REF('introEffect','LevelDataBlackBoxIntroEffectConfig'),REF('inventory','InventoryContentInfo'),
  SEQ('mainTask','LevelDataBlackBoxTaskConfig'),REF('manualCraft','LevelDataBlackBoxManualCraft'),SEQ('predefinedTemplates','PredefinedParamTemplate'),
  REF('presetBluePrints','LevelDataBlackBoxBluePrint'),REF('statistics','LevelDataBlackBoxStatistics')),
})
COLLECTIONS={declared:('string'if kind=='pooled-string-list'else'int'if kind=='int32-list'else declared[len(LIST(''))-1:-1],kind)
 for plan in PLANS.values()for field,declared,kind in plan if kind in('pooled-string-list','int32-list','factory-config-record-list')}


def record_key(name):
 if name not in PLANS:raise ValueError('factoryConfig.unknown-record:'+str(name))
 return 'story-factory-config-record:'+name


def list_key(name):
 if name not in COLLECTIONS:raise ValueError('factoryConfig.unknown-list:'+str(name))
 return 'story-factory-config-list:'+name


def operation(declared,kind):
 if kind=='factory-config-record':return record_key(declared)
 if kind in('factory-config-record-list','pooled-string-list','int32-list'):return list_key(declared)
 if kind=='lang-key':return 'story-lang-key'
 return 'byte-payload'if kind=='byte-payload'else None


def ordered_types():
 result=[];pending=list(PLANS)
 while pending:
  ready=[name for name in pending if all(
   (declared if kind=='factory-config-record'else COLLECTIONS[declared][0])in result
   for field,declared,kind in PLANS[name]if kind in('factory-config-record','factory-config-record-list'))]
  if not ready:raise ValueError('factoryConfig.finite-acyclic-record-graph')
  result.extend(ready);pending=[n for n in pending if n not in ready]
 return result


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if(plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,operation(t,k))for j,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({operation(t,k)for n,t,k in plan if operation(t,k)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,operation(t,k))for n,t,k in plan if k in('factory-config-record','factory-config-record-list','pooled-string-list','int32-list','lang-key')]):
  raise ValueError('factoryConfig.exact-finite-program:'+str(name))


def bind_reference(pins,join,child,key):
 name=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(name not in PLANS or key!=record_key(name)or child.get('nativeInputs')!=pins or cap.get('typeName')!=name
  or any(cap.get(k)is not True for k in('profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[name]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
  or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('factoryConfig.exact-reference-parent:'+str(name))
 return dict(fieldName=join['fieldName'],typeName=name,capability=key,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=join['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def bind_collection(pins,join,child,key):
 declared=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(declared not in COLLECTIONS or key!=list_key(declared)or child.get('nativeInputs')!=pins
  or cap.get('typeName')!=declared or(cap.get('elementType'),cap.get('wireKind'))!=COLLECTIONS[declared]
  or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT or cap.get('countRange')!=[-1,LIMIT]
  or type(cap.get('headerBytes'))is not int or cap['headerBytes']!=4
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted','initiallyNullListRequired',
   'actualCallbackEqualsProvedChildRequired'))or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[declared]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('factoryConfig.exact-list-parent:'+str(declared))
 element,kind=COLLECTIONS[declared]
 if kind=='pooled-string-list'and cap.get('actualCallbackEqualsPooledStringRequired')is not True:
  raise ValueError('factoryConfig.exact-pooled-string-list-callback')
 binding=dict(fieldName=join['fieldName'],typeName=declared,capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
 if kind=='pooled-string-list':binding['actualCallbackEqualsPooledStringRequired']=True
 return binding


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack import leveldata_lang_key_components as language,leveldata_int_list_sources as integers
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 need=lambda k,e,a:scalar.need('factoryConfig',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 names=ordered_types();wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('exact-current-wrapper-set',set(PLANS),set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in names])
 # Check every source before the heavier canonical adapter compositions. A
 # known late factory/transfer refusal must not repeat all earlier adapters.
 sources={name:require_complete(row,validator='factoryConfig',type_name=name)for name,row in zip(names,generated['owners'],strict=True)}
 abi=reference_reader_abi(image,pins)
 string_source=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
 need('dedicated-pooled-string-wire',(5,4,8),(string_source['stringFormatterSlot'],string_source['wireBytes'],string_source['managedReferenceBytes']))
 records={};caps={};list_caps={};language_cap=None
 for name in names:
  source=sources[name];plan=PLANS[name]
  need('exact-declared-field-order:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  references={};reference_children={};collections={};collection_children={};requests={};values={};value_children={};proofs={}
  for read,(member,declared,kind)in zip(source['orderedSourceReads'],plan,strict=True):
   if kind not in('factory-config-record','factory-config-record-list','pooled-string-list','int32-list','lang-key'):continue
   index=read['memberIndex'];key=operation(declared,kind)
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='factoryConfig.actualChild');requests[index]=usage;target=base+read['sourceTargetRva']
   if kind=='factory-config-record':
    references[declared]=(key,kind,key);reference_children[declared]=dict(nativeInputs=pins,capabilities={key:caps[declared]});continue
   if kind=='lang-key':
    child=language.derive(image,pins,typed_request=usage,source_target=target)
    if language_cap is not None:need('same-LangKey-child',language_cap,child['capabilities'][language.CAP])
    language_cap=child['capabilities'][language.CAP];values[LANG]=(language.CAP,'lang-key',language.CAP);value_children[index]=child;proofs[member]=child;continue
   element,_=COLLECTIONS[declared]
   proof=(integers.derive(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)if kind=='int32-list'else
    reference_list(image,pins,typed_request=usage,call_target=target,element_type=element,count_limit=LIMIT))
   actual_target=proof['capability']['packableReaderTargetRva']if kind=='int32-list'else proof['witnessComponent']['callTargetRva']
   cap=dict(typeName=declared,elementType=element,wireKind=kind,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
    nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
    actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=actual_target)
   if kind=='pooled-string-list':cap['actualCallbackEqualsPooledStringRequired']=True
   if key in list_caps:need('same-independent-list-profile:'+declared,list_caps[key],cap)
   list_caps[key]=cap;collections[declared]=(key,kind,key);collection_children[index]=dict(nativeInputs=pins,capabilities={key:cap});proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},typed_requests=requests,
   references=references,reference_children=reference_children,reference_binder=bind_reference,
   collections=collections,collection_children=collection_children,collection_binder=bind_collection,
   typed_values=values,value_children=value_children,value_binder=language.bind_value if values else None)
  bind_program(name,source,program,pending);enums={}
  for member,declared,kind in plan:
   if kind!='scalar32'or declared=='int':continue
   need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   need('own-int32-enum:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('whole-owned-original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-owned-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  caps[name]=dict(typeName=name,memberCount=len(plan),program=program,enumBackings=enums,nullAdmitted=True,positiveAdmitted=True,
   profileAdmitted=True,ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,
   liveFormatterSelectionObserved=False,referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pooled,children=proofs)
 parents={}
 for field_name,name in(('blackbox',BLACKBOX),('predefinedParams',PREDEFINED_HOST)):
  field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field_name)
  usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='factoryConfig.actualHost')
  if field_name=='blackbox':
   binding=bind_reference(pins,dict(fieldName=field_name,typeName=field['typeName'],typedRequest=usage,sourceTargetRva=read['sourceTarget']-base),
    dict(nativeInputs=pins,capabilities={record_key(name):caps[name]}),record_key(name));listing=None
  else:
   need('exact-host-predefined-list',LIST(name),field['typeName'])
   listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=name,count_limit=LIMIT)
   binding=dict(fieldName=field_name,typeName=LIST(name),capability=CAP,countLimit=LIMIT,
    readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],
    initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
  parents[field_name]=dict(field=field,source=read,typedRequest=usage,collection=listing,binding=dict(binding,ownerType='Beyond.Gameplay.LevelData'))
 cap=dict(typeName=BLACKBOX,capability=CAP,records=caps,collections=list_caps,langKey=language_cap,countLimit=LIMIT,nodeLimit=NODE_LIMIT,
  parentBindings={n:r['binding']for n,r in parents.items()},profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,finiteFloatProfile=True)
 from scripts.game_data.codecs.leveldata.current_factory_config import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-factory-config-components.v1',status='validated-conditional-finite-factory-config-graph',
  nativeInputs=pins,capability=cap,records=records,parents=parents,pooledStrings=string_source,referenceABI=abi,
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Only the explicit acyclic Blackbox/Predefined records, each complete current ordinary source/lifecycle/adapter/frame, actual child parents, nominal enums, LangKey and Int32/pooled/reference lists, plus both exact LevelData parents.',
   conditional='Initialized coherent wrapper/original/cache storage and matching ready actual callbacks/contexts, initially-null count-sized lists, normal compatible helpers/provider/collector effects and disjoint buffered input; finite scalar/spatial floats and bounded resources define this projection.',
   unresolved=['runtime callback/provider selection or factory gameplay behavior','whole LevelData/Narrative physical EOF and public source receipts']))))
