"""Explicit remaining Story leaves; no collection or enclosing-owner admission."""
import json

PLANS={
 'Beyond.Gameplay.LevelDataBlackboxBasic':(('disableSwitchMode','bool','bool-byte'),('domainGrade','int','scalar32'),
  ('enterFactoryModeOnSceneLoaded','bool','bool-byte'),('lockLogisticConveyor','bool','bool-byte'),
  ('lockLogisticConveyorBridge','bool','bool-byte'),('lockLogisticConveyorConverger','bool','bool-byte'),
  ('lockLogisticConveyorSplitter','bool','bool-byte'),('lockLogisticConveyorValve','bool','bool-byte'),
  ('lockLogisticPipe','bool','bool-byte'),('lockLogisticPipeConnector','bool','bool-byte'),
  ('lockLogisticPipeConverger','bool','bool-byte'),('lockLogisticPipeSplitter','bool','bool-byte'),('lockLogisticPipeValve','bool','bool-byte')),
 'Beyond.Gameplay.LevelDataBlackBoxCompleteCondition':(('cannotCompleteWhenBlockedNodeExist','bool','bool-byte'),
  ('cannotCompleteWhenDanglingConveyorExist','bool','bool-byte'),('cannotCompleteWhenOutOfPowerExist','bool','bool-byte'),
  ('cannotCompleteWhenPowerGenLessThanPowerCost','bool','bool-byte')),
 'Beyond.Gameplay.LevelDataBlackBoxTaskConfig':(('levelScriptId','ulong','scalar64-bits'),('taskId','string','byte-payload')),
 'Beyond.Gameplay.LevelDataBlackBoxIntroEffectConfig':(('delay','float','float32-bits'),('introEffectName','string','byte-payload'),
  ('loopEffectName','string','byte-payload'),('position','UnityEngine.Vector3','unity-vector3-raw12')),
 'Beyond.Gameplay.LevelDataBlackboxGeneralAbilityEntry':(('abilityType','Beyond.GEnums.GeneralAbilityType','scalar32'),
  ('customState','Beyond.Gameplay.GeneralAbilitySystem+AbilityState','scalar32')),
 'Beyond.Gameplay.InventoryItemBundle':(('count','int','scalar32'),('id','string','byte-payload')),
 'Beyond.Gameplay.InventoryItemBundleWithInfinite':(('count','int','scalar32'),('id','string','byte-payload'),('infinite','bool','bool-byte')),
 'Beyond.Gameplay.Rectangle2D':(('eulerAngle','UnityEngine.Vector3','unity-vector3-raw12'),('worldPos','UnityEngine.Vector3','unity-vector3-raw12'),
  ('xSize','float','float32-bits'),('ySize','float','float32-bits')),
 'Beyond.Gameplay.PredefinedParamComponent_Cache':(('lockManualInOut','bool','bool-byte'),),
 'Beyond.Gameplay.PredefinedParamComponent_EnvGenWithActivator':(('lockEnvFromItemId','string','byte-payload'),),
 'Beyond.Gameplay.PredefinedParamComponent_PowerDiffuser':(('disablePowerPole','bool','bool-byte'),),
 'Beyond.Gameplay.PredefinedParamComponent_PowerGate':(('toInstKey','string','byte-payload'),('toScene','string','byte-payload')),
 'Beyond.Gameplay.PredefinedParamComponent_PowerPole':(('disablePowerDiffuser','bool','bool-byte'),),
 'Beyond.Gameplay.PredefinedParamComponent_PowerPort':(('target','ulong','scalar64-bits'),),
 'Beyond.Gameplay.PredefinedParamComponent_Selector':(('currentSelectedItemId','string','byte-payload'),('lockSelectedItemId','bool','bool-byte')),
 'Beyond.Gameplay.PredefinedParamComponent_SewageTreatPlantExport':(('groupId','string','byte-payload'),),
 'Beyond.Gameplay.PredefinedParamComponent_SewageTreatPlantImport':(('groupId','string','byte-payload'),),
 'Beyond.Gameplay.PredefinedParamComponent_TravelPole':(('lockAutoTravelTargetSetting','bool','bool-byte'),('nextInstKey','string','byte-payload')),
 'Beyond.Gameplay.PredefinedParamComponent_Valve':(('enableItemPass','bool','bool-byte'),('isItemCountLocked','bool','bool-byte'),
  ('isItemLimited','bool','bool-byte'),('isItemLocked','bool','bool-byte'),('isItemPassLocked','bool','bool-byte'),
  ('isSpeedLimited','bool','bool-byte'),('isSpeedLimitedLocked','bool','bool-byte'),('isSpeedLimitedTechUnlock','bool','bool-byte'),
  ('itemCount','int','scalar32'),('limitSpeed','int','scalar32'),('limitSpeedLocked','bool','bool-byte'),('passItemId','string','byte-payload')),
 'Beyond.Gameplay.InventorySystem+ItemInstData':(('expireTs','long','scalar64-bits'),('instId','ulong','scalar64-bits'),
  ('isNew','bool','bool-byte'),('itemFlag','Proto.ITEM_FLAG','scalar32'),('templateId','string','byte-payload')),
 'Beyond.Gameplay.CommonItemBundle':(('count','int','scalar32'),('id','string','byte-payload')),
 'Beyond.Gameplay.SocialBuildingConfig':(('like','int','scalar32'),('ownerId','int','scalar32')),
 'Beyond.Gameplay.HUBSelectorPort':(('currentSelectedItemId','string','byte-payload'),('index','int','scalar32'),('lockSelectedItemId','bool','bool-byte')),
 'Beyond.Gameplay.AI.EnemyCommonPlayTemplate+BornSeqAnimItem':(('animId','string','byte-payload'),('repeat','bool','bool-byte'),
  ('repeatDuration','float','float32-bits'),('rootMotion','bool','bool-byte'),('speed','float','float32-bits')),
 'Beyond.Gameplay.SpawnerBlackboardKVPair':(('key','string','byte-payload'),('useString','bool','bool-byte'),
  ('valueFloat','float','float32-bits'),('valueString','string','byte-payload')),
}


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or source.get('wrappedType')!=name or not isinstance(program,dict)
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (i,n,k,'byte-payload'if k=='byte-payload'else None)for i,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=(['byte-payload']if any(k=='byte-payload'for n,t,k in plan)else[])
  or program.get('childBindings')!=[]):raise ValueError('storyLeafRecord.exact-finite-program:'+str(name))


def derive(image,pins,*,type_names=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 need=lambda k,e,a:scalar.need('storyLeafRecord',k,e,a)
 _publication_gate(image,pins);names=list(PLANS)if type_names is None else type_names
 need('explicit-finite-selection',True,isinstance(names,list)and bool(names)and all(type(n)is str and n in PLANS for n in names)and len(names)==len(set(names)))
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in names}
 need('exact-own-wrapper-set',set(names),set(wrappers));ctx=NativeReferenceContext(image);base=image.pe.image_base
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in names]);records={};caps={}
 for name,row in zip(names,generated['owners'],strict=True):
  source=require_complete(row,validator='storyLeafRecord',type_name=name)
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={})
  bind_program(name,source,program,pending);enums={}
  for member,declared,kind in PLANS[name]:
   if kind!='scalar32'or declared=='int':continue
   need('own-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   need('own-32bit-enum:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-original-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('whole-owned-original-output:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  pooled={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
   for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  caps[name]=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,nullAdmitted=True,
   positiveAdmitted=True,ordinaryAdapterAdmitted=True,finiteFloatProfile=True,profileAdmitted=True,
   actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
   parentFieldAdmitted=False,wholeOwnerAdmitted=False)
  from scripts.game_data.codecs.leveldata.current_leaf_record import validate
  validate(name,caps[name]);records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pooled)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-leaf-record-components.v1',status='validated-conditional-finite-leaf-records',
  nativeInputs=pins,records=records,capabilities=caps,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Only explicitly named complete ordinary wrapper sources, all new/existing/FF frames, concrete canonical adapters/GetValue, nominal enum backings, unchanged primitive/vector stores and independently checked pooled targets.',
   conditional='Matching ready callbacks, coherent original/cache/context, normal provider/allocation/helper/collector effects and stable disjoint nonwrapping buffered input. Spatial/scalar float projection is finite.',
   unresolved=['enclosing field and collection source/callback/count joins','runtime selection or behavior','whole owner physical EOF/public source receipt']))))
