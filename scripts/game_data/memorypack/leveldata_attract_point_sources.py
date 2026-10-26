"""Finite current attract-point record; stored fields do not prove AI behavior."""
import json
from scripts.game_data.memorypack.leveldata_extended_record_sources import STRINGS,STRING_CAP,bind_strings

TYPE='Beyond.Gameplay.AI.AttractPointInEditorData'
CAP='story-attract-point'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
ULONGS='System.Collections.Generic.List`1<ulong>'
ULONG_CAP='story-attract-uint64-list'
LIMIT=4096
PLAN=(('actionEndType','Beyond.Gameplay.AI.ActionEndType','scalar32'),('actionType','Beyond.Gameplay.AI.ActionType','scalar32'),
 ('activeLookAt','bool','bool-byte'),('animMaskType','Beyond.NPC.Animation.ENPCAnimationAvatarMaskType','scalar32'),
 ('animNameTag','Beyond.Gameplay.Core.GameplayTag','gameplay-tag32'),('animVirtualTag','Beyond.Gameplay.Core.GameplayTag','gameplay-tag32'),
 ('attractObjectType','Beyond.Gameplay.AI.AttractObjectType','scalar32'),('chairCheckDistance','float','float32-bits'),('chairID','ulong','scalar64-bits'),
 ('cooldownFinishAction','Beyond.Gameplay.AI.AttractCooldownFinishAction','scalar32'),('cooldownTime','float','float32-bits'),
 ('enableAtInit','bool','bool-byte'),('enableCooldown','bool','bool-byte'),('enableSyncGroup','bool','bool-byte'),
 ('envTalkString','string','byte-payload'),('groupId','int','scalar32'),('groupIndex','int','scalar32'),('isPoiPoint','bool','bool-byte'),('level','int','scalar32'),
 ('linkedAttractPoints',ULONGS,'uint64-list'),('linkedWayPoints',ULONGS,'uint64-list'),('mainId','ulong','scalar64-bits'),
 ('movementStyleType','Beyond.Gameplay.AbilityUnsafe.ENPCAbilityMovementStyleType','scalar32'),('moveToMethod','Beyond.Gameplay.AI.MoveToMethod','scalar32'),
 ('ownerRoomId','string','byte-payload'),('position','UnityEngine.Vector3','unity-vector3-raw12'),('restaurantPointType','Beyond.Gameplay.AI.RestaurantPointType','scalar32'),
 ('rotation','UnityEngine.Quaternion','unity-quaternion-raw16'),('searchName','string','byte-payload'),('spaceshipBehaviorType','Beyond.GEnums.AttractBehaviourType','scalar32'),
 ('spaceshipDetailAnimType','string','byte-payload'),('spaceshipGeneralAnimType','Beyond.GEnums.AttractGeneralAnimType','scalar32'),
 ('spaceshipTag',STRINGS,'pooled-string-list'),('startDelay','float','float32-bits'),('syncGroupId','int','scalar32'),('useEmoji','bool','bool-byte'),
 ('uuid','ulong','scalar64-bits'),('waitTime','float','float32-bits'),('wayLineHash','int','scalar32'),('wayPointEndUuid','ulong','scalar64-bits'),
 ('wayPointRate','float','float32-bits'),('wayPointStartUuid','ulong','scalar64-bits'))
OPERATIONS={'byte-payload':'byte-payload','uint64-list':ULONG_CAP,'pooled-string-list':STRING_CAP}


def bind_program(source,program,pending):
 if (pending or source.get('wrappedType')!=TYPE or not isinstance(program,dict)
   or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
   or type(program.get('memberCount'))is not int or program['memberCount']!=len(PLAN)
   or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
   or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
    (index,n,k,OPERATIONS.get(k))for index,(n,t,k)in enumerate(PLAN)]
   or program.get('requiredCapabilities')!=sorted({OPERATIONS[k]for n,t,k in PLAN if k in OPERATIONS})
   or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
    (n,t,OPERATIONS[k])for n,t,k in PLAN if k in('uint64-list','pooled-string-list')]):raise ValueError('storyAttract.exact-finite-program')


def bind_collection(pins,join,child,capability):
 if capability==STRING_CAP:return bind_strings(pins,join,child,capability)
 cap=child.get('capabilities',{}).get(capability,{});usage=join['typedRequest']
 if(capability!=ULONG_CAP or child.get('nativeInputs')!=pins or join['typeName']!=ULONGS
   or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(ULONGS,'ulong',[-1,LIMIT])
   or type(cap.get('countLimit'))is not int or cap['countLimit']!=LIMIT
   or type(cap.get('elementWireBytes'))is not int or cap['elementWireBytes']!=8
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved','initiallyNullOutputRequired','actualCallbackEqualsProvedChildRequired'))
   or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[ULONGS]
   or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyAttract.exact-UInt64-list-parent')
 return dict(fieldName=join['fieldName'],typeName=ULONGS,capability=ULONG_CAP,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar,buff_gameplay_tag_native
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 need=lambda k,e,a:scalar.need('storyAttract',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('complete-nominal-field-order',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 tag=buff_gameplay_tag_native.validate_on_image(image,pins);need('independent-current-GameplayTag','validated',tag.get('status'))
 strings=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
 need('independent-pooled-string-element',(5,4,8),(strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
 typed={};collections={};children={};child_caps={};proofs={}
 for read in source['orderedSourceReads']:
  index=read['memberIndex'];kind=PLAN[index][2]
  if kind not in('uint64-list','pooled-string-list'):continue
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyAttract.actualChild');typed[index]=usage
  key=OPERATIONS[kind];target=base+read['sourceTargetRva']
  if kind=='uint64-list':
   proof=derive_ulong_list_component(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
   cap={k:v for k,v in proof.items()if k not in('proof','typedRequest','typedBinding','closedCarrier','evidenceBoundary')}
  else:
   proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type='string',count_limit=LIMIT)
   cap=dict(closedListType=STRINGS,elementType='string',elementValueType=False,nullable=True,positiveCountsAdmitted=True,
    elementGrammarAdmitted=True,countLimit=LIMIT,actualCallbackEqualsPooledStringRequired=True,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
  if key in child_caps:need('same-independent-collection-capability:'+key,child_caps[key],cap)
  collections[read['declaredType']]=(key,kind,key);children[index]=dict(nativeInputs=pins,capabilities={key:cap});child_caps[key]=cap;proofs[read['fieldName']]=proof
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,
  value4={'Beyond.Gameplay.Core.GameplayTag':tag},typed_requests=typed,collections=collections,collection_children=children,collection_binder=bind_collection)
 bind_program(source,program,pending)
 pools={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
 enums={}
 for field,declared,kind in PLAN:
  if kind!='scalar32'or declared=='int':continue
  need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
  need('separate-exact-Int32-backing:'+declared,(declared,'int',16),value);enums[field]=dict(typeName=declared,backing='int',field=list(value))
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
 need('same-owned-concrete-callback',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 need('full-owned-original-reference',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='npcAttractPointData')
 need('exact-host-attract-list',LIST,declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyAttract.host')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='npcAttractPointData',typeName=LIST,capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=TYPE,memberCount=len(PLAN),program=program,enumBackings=enums,childCapabilities=child_caps,parentBinding=binding,
  nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
  ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False)
 from scripts.game_data.codecs.leveldata.current_attract_point import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-attract-point-components.v1',status='validated-finite-current-attract-point-profile',nativeInputs=pins,
  capability=cap,source=source,pair=pair,adapter=adapter,pooled=pools,enumBackings=enums,children=proofs,gameplayTag=tag,pooledStringElements=strings,
  parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Complete AttractPoint42 generated source/lifecycle/ordinary adapter, exact finite primitive/vector/quaternion/GameplayTag/pool program, independently current UInt64/string lists and actual host parent.',
   conditional='Ready compatible actual callbacks/providers, coherent original/cache, initially null count-sized lists, buffered disjoint nonwrapping storage and normal helper effects. Finite float/count profile remains separate.',
   unresolved=['AI activation/behavior and runtime provider selection','whole owner/physical EOF']))))
