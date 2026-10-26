"""Finite EnemyGroup stored schema; native parent composition is separate."""
GROUP='Beyond.Gameplay.LevelEnemyGroupData'
SLOT='Beyond.Gameplay.EnemyGroupSlot'
ENTITY='Beyond.Gameplay.Core.EntityPtr'
LIST=lambda t:'System.Collections.Generic.List`1<'+t+'>'
CAP='story-enemy-group-positive'
ENTITY_CAP='story-entity-ptr-value'
SLOT_LIST_CAP='story-enemy-group-slot-list'
LIMIT=4096
NODE_LIMIT=16384
PLANS={
 SLOT:(('entityPtr',ENTITY,'entity-ptr-stored-value'),('leader','bool','bool-byte'),
  ('offset','UnityEngine.Vector2','vector2-raw8')),
 GROUP:(('count','int','scalar32'),('groupId','int','scalar32'),('lockLeaderSlot','bool','bool-byte'),
  ('patrolId','ulong','scalar64-bits'),('radius','float','float32-bits'),
  ('slot',LIST(SLOT),'enemy-group-slot-list'),('speed','float','float32-bits'),('templateId','string','byte-payload')),
}


def operation(kind):
 return {'entity-ptr-stored-value':ENTITY_CAP,'enemy-group-slot-list':SLOT_LIST_CAP,'byte-payload':'byte-payload'}.get(kind)


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if(plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (i,n,k,operation(k))for i,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({operation(k)for n,t,k in plan if operation(k)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,operation(k))for n,t,k in plan if k in('entity-ptr-stored-value','enemy-group-slot-list')]):
  raise ValueError('storyEnemyGroup.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,capability):
 cap=child.get('capabilities',{}).get(capability,{});usage=join.get('typedRequest',{})
 if(capability!=SLOT_LIST_CAP or child.get('nativeInputs')!=pins
  or(join.get('typeName'),cap.get('typeName'),cap.get('elementType'))!=(LIST(SLOT),LIST(SLOT),SLOT)
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or cap.get('countRange')!=[-1,LIMIT]or cap.get('wholeGrammarAdmitted')is not False
  or cap.get('liveFormatterSelectionObserved')is not False
  or any(cap.get(k)is not True for k in('profileAdmitted','elementGrammarAdmitted','initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[LIST(SLOT)]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('readerMethodDefinition'))is not int or type(cap.get('sourceTargetRva'))is not int
  or(cap['readerMethodDefinition'],cap['sourceTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyEnemyGroup.exact-slot-list-parent')
 return dict(fieldName=join['fieldName'],typeName=LIST(SLOT),capability=SLOT_LIST_CAP,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 """Fresh complete two-record graph, own Entity40 and both actual list parents."""
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
 from scripts.game_data.memorypack import leveldata_entity_ptr_components as entity
 from scripts.game_data.memorypack.leveldata_entity_ptr_value_bindings import bind as bind_entity
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 need=lambda key,expected,actual:scalar.need('storyEnemyGroup',key,expected,actual)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('exact-two-current-wrappers',set(PLANS),set(wrappers))
 selected=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in PLANS])
 sources={name:require_complete(row,validator='storyEnemyGroup',type_name=name)
  for name,row in zip(PLANS,selected['owners'],strict=True)}
 records={};record_caps={};entity_child=None;slot_cap=None
 for name,plan in PLANS.items():
  source=sources[name];need('exact-own-declarations:'+name,[(n,t)for n,t,k in plan],
   [(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};collection_children={};typed_values={};value_children={};proofs={}
  for read,(member,declared,kind)in zip(source['orderedSourceReads'],plan,strict=True):
   if kind not in('entity-ptr-stored-value','enemy-group-slot-list'):continue
   index=read['memberIndex'];usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyEnemyGroup.actualChild')
   requests[index]=usage;target=base+read['sourceTargetRva']
   if kind=='entity-ptr-stored-value':
    entity_child=entity.derive(image,pins,typed_request=usage,source_target=target)
    typed_values[declared]=(ENTITY_CAP,kind,ENTITY_CAP);value_children[index]=entity_child;proofs[member]=entity_child
   else:
    need('own-complete-Slot-element',True,SLOT in record_caps)
    listing=reference_list(image,pins,typed_request=usage,call_target=target,element_type=SLOT,count_limit=LIMIT)
    slot_cap=dict(typeName=LIST(SLOT),elementType=SLOT,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
     profileAdmitted=True,wholeGrammarAdmitted=False,elementGrammarAdmitted=True,initiallyNullListRequired=True,
     actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
     readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'])
    collections[declared]=(SLOT_LIST_CAP,kind,SLOT_LIST_CAP)
    collection_children[index]=dict(nativeInputs=pins,capabilities={SLOT_LIST_CAP:slot_cap});proofs[member]=listing
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   value8={'UnityEngine.Vector2':{str(r['memberIndex']):source['sourceScope']['primitiveSources'][str(r['memberIndex'])]
    for r in source['orderedSourceReads']if r['kind']=='value8:UnityEngine.Vector2'}},
   typed_requests=requests,typed_values=typed_values,value_children=value_children,value_binder=bind_entity,
   collections=collections,collection_children=collection_children,collection_binder=bind_collection)
  bind_program(name,source,program,pending);pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('full-reference-GetValue:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-owned-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
   for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  record_caps[name]=dict(typeName=name,memberCount=len(plan),program=program,nullAdmitted=True,positiveAdmitted=True,
   ordinaryAdapterAdmitted=True,profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
   wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,children=proofs)
 field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='enemyGroup')
 need('own-actual-host-list',LIST(GROUP),field['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyEnemyGroup.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=GROUP,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName='enemyGroup',typeName=LIST(GROUP),elementType=GROUP,
  capability=CAP,readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)
 need('fresh-Entity-and-slot-list-components',True,entity_child is not None and slot_cap is not None)
 cap=dict(typeName=LIST(GROUP),capability=CAP,records=record_caps,slotCollection=slot_cap,
  entityCapability=entity_child['capabilities'][ENTITY_CAP],parentBinding=binding,countLimit=LIMIT,nodeLimit=NODE_LIMIT,headerBytes=4,
  profileAdmitted=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  actualCallbackEqualsProvedChildRequired=True,initiallyNullListsRequired=True,coherentWrapperStorageRequired=True,
  finiteFloatProfile=True,canonicalBooleanProfile=True,runtimeEntityResolutionProved=False,runtimeReferenceLayoutAdmitted=False)
 from scripts.game_data.codecs.leveldata.current_enemy_group import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-enemy-group-components.v1',
  status='validated-conditional-positive-enemy-group',nativeInputs=pins,capability=cap,records=records,
  parent=dict(declaration=field,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own Group8/Slot3 complete readers/lifecycle/getters/ordinary adapters, dedicated EntityPtr40 source/opaque field transfer/selected barrier/all frames, separate float Vector2, pooled template and both actual reference-list parents/count/callback/Add sources.',
   conditional='Ready matching callbacks/contexts and coherent cache, initially-null count-sized lists, normal compatible helper/provider/collector effects and buffered disjoint storage. Finite floats, canonical ordinary bools and resource bounds define the projection.',
   unresolved=['runtime Entity resolution/reference layout or gameplay behavior','whole LevelData/Narrative/public owner/pool/physical EOF']))))
