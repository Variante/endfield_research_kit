"""Own current Core Patrol39/Action4; authored NPC and runtime conversion stay distinct."""
import copy
import json

ROOT='Beyond.Gameplay.Core.PatrolData'
ACTION='Beyond.Gameplay.Core.PatrolAction'
SUBACTION='Beyond.Gameplay.Core.PatrolSubAction'
ENV='Beyond.Gameplay.Core.PatrolSubActionEnvTalkData'
AUDIO='Beyond.Gameplay.Core.PatrolSubPlayAudioData'
VECTOR='UnityEngine.Vector3'
CAP='story-core-patrol'
LIMIT=4096
NODE_LIMIT=32768
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
PLANS={
 ACTION:(('actionType','Beyond.Gameplay.Core.PatrolActionType','scalar32'),('position',VECTOR,'unity-vector3-raw12'),
  ('subActions',LIST(SUBACTION),'core-patrol-reference-list'),('subPositions',LIST(VECTOR),'core-patrol-vector3-list')),
 ROOT:(('actions',LIST(ACTION),'core-patrol-reference-list'),('addBornPositionAsCheckpoint','bool','bool-byte'),
  ('bornMoveStyle','Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType','scalar32'),('bornOverrideSpeed','float','float32-bits'),
  ('bornPositionWaitDuration','float','float32-bits'),('changePlayerMoveStyle','bool','bool-byte'),('coolDownBetweenWalkAndStop','float','float32-bits'),
  ('enableBornAction','bool','bool-byte'),('enableBornSpeedOverride','bool','bool-byte'),('forbidNpcInteract','bool','bool-byte'),
  ('forcePlayerMoveStyle','Beyond.Gameplay.Core.MovementComponent+GroundedMoveGait','scalar32'),('id','int','scalar32'),
  ('inLocalSpace','bool','bool-byte'),('isLimitPlayerActionWhenGaitLimit','bool','bool-byte'),('isStopDistance','bool','bool-byte'),('isUseCatmull','bool','bool-byte'),
  ('limitPlayerActionType','Beyond.Gameplay.Core.PlayerController+InputActionType','scalar32'),('loop','Beyond.Gameplay.Core.PatrolLoopType','scalar32'),
  ('motionEnterDis','float','float32-bits'),('motionType','Beyond.Gameplay.Core.MotionType','scalar32'),
  ('moveStyleWithoutLead','Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType','scalar32'),('pauseActionWhenPatrolDisabled','bool','bool-byte'),
  ('playerChangeLimitDelayTime','float','float32-bits'),('runAheadRadius','float','float32-bits'),('runBehindRadius','float','float32-bits'),
  ('snap','Beyond.Gameplay.Core.SnapToGround','scalar32'),('sprintAheadRadius','float','float32-bits'),('sprintBehindRadius','float','float32-bits'),
  ('stop2WalkBufferTime','float','float32-bits'),('stopWalkInplace','bool','bool-byte'),('turnCheck','bool','bool-byte'),
  ('turnCheckAngle','float','float32-bits'),('turnCheckDis','float','float32-bits'),('turnCheckTime','float','float32-bits'),('turnRadio','float','float32-bits'),
  ('usePatrolPointEnterGaitAsLimitGait','bool','bool-byte'),('useWorldOffset','bool','bool-byte'),('waitDistance','float','float32-bits'),
  ('worldOffset',VECTOR,'unity-vector3-raw12')),
}
COLLECTIONS={LIST(SUBACTION):(SUBACTION,'core-patrol-reference-list'),LIST(ACTION):(ACTION,'core-patrol-reference-list'),
 LIST(VECTOR):(VECTOR,'core-patrol-vector3-list')}
SUB_PLANS={
 SUBACTION:(('actionEndType','i32',None),('animKeyTag','i32',None),('animMaskType','i32',None),('animName','pool',None),
  ('configMovementStyle','bool',None),('configSnap','bool',None),('duration','f32',None),('eventBBDataPairs','data-pair-list','Beyond.Blackboard+DataPair'),
  ('eventKey','pool',None),('eventToLevelType','i32',None),('ignoreAnimDis','f32',None),('movementStyle','i32',None),
  ('npcPlayAnimationTimeEndForceToIdle','bool',None),('overrideSpeed','bool',None),('overrideSpeedValue','f32',None),('radioId','pool',None),
  ('radioWaitTime','f32',None),('radius','f32',None),('repeatAnim','bool',None),('rootMotion','bool',None),('rotationOffset','f32',None),
  ('rotationY','f32',None),('snapToGround','i32',None),('subActionData','union',None),('type','i32',None),('waitTime','f32',None)),
 ENV:(('envTalkId','pool',None),('npcId','pool',None),('overrideNpc','bool',None)),AUDIO:(('audioEventId','i32',None),),
}


def list_key(name):
 if name not in COLLECTIONS:raise ValueError('corePatrol.unknown-list')
 return 'story-core-patrol-list:'+name


def subaction_layout(layout):
 """Narrow an independently freshly proved NPC component to its shared child."""
 result=copy.deepcopy(layout);result['root']=SUBACTION
 result['records']={n:result['records'][n]for n in SUB_PLANS}
 result['enums']=[r for r in result['enums']if r['parent']in SUB_PLANS]
 validate_subaction_layout(result);return result


def validate_subaction_layout(layout):
 if(not isinstance(layout,dict)or layout.get('root')!=SUBACTION or type(layout.get('countLimit'))is not int
  or layout['countLimit']!=LIMIT or set(layout.get('records',{}))!=set(SUB_PLANS)
  or layout.get('union')!={'0':ENV,'1':AUDIO}):raise ValueError('corePatrol.exact-shared-subaction-layout')
 for name,plan in SUB_PLANS.items():
  if[(r.get('name'),r.get('wire'),r.get('element'))for r in layout['records'][name]]!=list(plan):
   raise ValueError('corePatrol.exact-shared-subaction-order')
 child=layout.get('dataPairCapability',{});collection=layout.get('dataPairListCapability',{})
 if(child.get('nullReturnsDefaultValue')is not True or(child.get('typeName'),child.get('memberCount'),child.get('managedBytes'),
  child.get('positiveWireBytes'),child.get('nullWireBytes'),child.get('nullMarker'))!=('Beyond.Blackboard+DataPair',4,32,18,1,255)
  or child.get('orderedReads')!=[dict(fieldName=f,kind=k)for f,k in(('isDynamic','bool'),('key','pooled-string'),('valueDouble','double-bits'),('valueStr','pooled-string'))]
  or(collection.get('closedListType'),collection.get('countLimit'),collection.get('managedElementBytes'))!=(LIST('Beyond.Blackboard+DataPair'),LIMIT,32)
  or collection.get('positiveCountsAdmitted')is not True or collection.get('elementGrammarAdmitted')is not True):
  raise ValueError('corePatrol.exact-shared-DataPair-child')


def bind_collection(pins,join,child,key):
 declared=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(declared not in COLLECTIONS or key!=list_key(declared)or child.get('nativeInputs')!=pins
  or cap.get('typeName')!=declared or(cap.get('elementType'),cap.get('wireKind'))!=COLLECTIONS[declared]
  or cap.get('countRange')!=[-1,LIMIT]or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
  or type(cap.get('headerBytes'))is not int or cap['headerBytes']!=4
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted',
   'initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
  or cap.get('runtimeFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[declared]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('corePatrol.exact-collection-parent')
 if declared==LIST(VECTOR)and(cap.get('elementWireBytes'),cap.get('managedElementBytes'),cap.get('elementRecordHeaderBytes'))!=(12,12,0):
  raise ValueError('corePatrol.exact-Vector3-child')
 return dict(fieldName=join['fieldName'],typeName=declared,capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 child=lambda t:list_key(t)if t in COLLECTIONS else None
 if(plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,child(t))for j,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({child(t)for n,t,k in plan if child(t)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,child(t))for n,t,k in plan if t in COLLECTIONS]):raise ValueError('corePatrol.exact-finite-program:'+str(name))


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,leveldata_patrol_component_sources,leveldata_vector3_list_sources
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 need=lambda k,e,a:scalar.need('corePatrol',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('exact-two-own-wrappers',set(PLANS),set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
 sources={n:require_complete(row,validator='corePatrol',type_name=n)for n,row in zip(PLANS,generated['owners'],strict=True)}
 shared=leveldata_patrol_component_sources.derive(image,pins,host);layout=subaction_layout(shared['layout'])
 records={};caps={};collections={}
 for name,plan in PLANS.items():
  source=sources[name];need('exact-own-declarations:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};selectors={};components={};proofs={}
  for read,(member,declared,kind)in zip(source['orderedSourceReads'],plan,strict=True):
   if declared not in COLLECTIONS:continue
   element,_=COLLECTIONS[declared]
   if element==ACTION:need('independently-complete-Action4',True,ACTION in caps)
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='corePatrol.actualChild')
   target=base+read['sourceTargetRva'];key=list_key(declared)
   proof=(leveldata_vector3_list_sources.derive(image,pins,typed_request=usage,call_target=target)if element==VECTOR else
    reference_list(image,pins,typed_request=usage,call_target=target,element_type=element,count_limit=LIMIT))
   cap=dict(typeName=declared,elementType=element,wireKind=kind,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
    nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,initiallyNullListRequired=True,
    actualCallbackEqualsProvedChildRequired=True,runtimeFormatterSelectionObserved=False,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=target-base)
   if element==VECTOR:
    actual=proof['capability'];need('same-Vector3-method-target',(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva']),
     (actual['packableReaderMethodDefinition'],actual['packableReaderTargetRva']))
    cap.update(elementWireBytes=actual['elementWireBytes'],managedElementBytes=actual['managedElementBytes'],elementRecordHeaderBytes=actual['elementRecordHeaderBytes'])
   else:need('same-reference-method-target',(usage,target-base),(proof['witnessComponent']['typedRequest'],proof['witnessComponent']['callTargetRva']))
   collections[key]=cap;requests[read['memberIndex']]=usage;selectors[declared]=(key,kind,key)
   components[read['memberIndex']]=dict(nativeInputs=pins,capabilities={key:cap});proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=selectors,collection_children=components,collection_binder=bind_collection)
  bind_program(name,source,program,pending);enums={}
  for member,declared,kind in plan:
   if kind!='scalar32'or declared=='int':continue
   need('own-nominal-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   need('own-enum-backing:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('whole-owned-Original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-own-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-own-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  caps[name]=dict(typeName=name,memberCount=len(plan),program=program,enumBackings=enums,nullAdmitted=True,positiveAdmitted=True,
   ordinaryAdapterAdmitted=True,profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,runtimeFormatterSelectionObserved=False)
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,collections=proofs)
 field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='patrols')
 need('exact-current-Core-host-list',LIST(ROOT),field['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='corePatrol.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=ROOT,count_limit=LIMIT)
 need('same-actual-host-list-source',(usage,read['sourceTarget']-base),(listing['witnessComponent']['typedRequest'],listing['witnessComponent']['callTargetRva']))
 parent=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='patrols',typeName=LIST(ROOT),capability=CAP,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTarget']-base,initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=ROOT,capability=CAP,records=caps,collections=collections,subActionLayout=layout,parentBinding=parent,countLimit=LIMIT,nodeLimit=NODE_LIMIT,
  profileAdmitted=True,finiteFloatProfile=True,actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,
  wholeGrammarAdmitted=False,controllerConversionProved=False,actionDispatchProved=False,checkpointProducerProved=False,runtimeFormatterSelectionObserved=False)
 from scripts.game_data.codecs.leveldata.current_core_patrol import validate
 cap=json.loads(json.dumps(cap));validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-core-patrol-components.v1',status='validated-conditional-core-patrol-records',nativeInputs=pins,
  capability=cap,records=records,sharedSubAction=shared,parent=dict(field=field,source=read,typedRequest=usage,collection=listing,binding=parent),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own complete CorePatrol39 and CoreAction4 readers/lifecycle/adapters/enums, independently current SubAction26/union2/DataPair32 children, Vector3 list and each actual list/host call.',
   conditional='Matching original callbacks, coherent ready classes/contexts/holders, initially-null count-sized lists, normally returning allocation/collector/helpers and stable disjoint buffered storage. Finite float/count/node limits bound this projection.',
   unresolved=['NPC-to-Core conversion and actual controller lookup','action dispatch, checkpoint producer/filter and playback','runtime formatter/provider selection','complete owner physical EOF and public current receipts']))))
