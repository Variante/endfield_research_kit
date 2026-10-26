"""Finite Character/Enemy patrol records, separate from runtime patrol consumers."""
import json

CHAR='Beyond.Gameplay.AI.CharacterPatrolData'
ENEMY='Beyond.Gameplay.AI.EnemyPatrolData'
CHAR_POINT='Beyond.Gameplay.AI.CharPatrolPointData'
ENEMY_POINT='Beyond.Gameplay.AI.EnemyPatrolPointData'
CHAR_ACTION='Beyond.Gameplay.AI.CharPatrolPointAction'
ENEMY_ACTION='Beyond.Gameplay.AI.EnemyPatrolPointAction'
TAG='Beyond.Gameplay.Core.GameplayTag'
LIMIT=4096
NODE_LIMIT=16384
FIELDS={'charPatrol':CHAR,'enemyPatrol':ENEMY}


def list_type(name):return 'System.Collections.Generic.List`1<'+name+'>'
def record_key(name):return 'story-authored-patrol-record:'+name
def list_key(name):return 'story-authored-patrol-list:'+name


PLANS={
 CHAR_ACTION:(('actionEndType','Beyond.Gameplay.AI.CharPatrolPointActionEndType','scalar32'),
  ('angle','float','float32-bits'),('animName','string','byte-payload'),('autoBlendOut','bool','bool-byte'),
  ('blendInTime','float','float32-bits'),('blendOutTime','float','float32-bits'),('duration','float','float32-bits'),
  ('envTalkId','string','byte-payload'),('eventKey','string','byte-payload'),('fixedTimeOffset','float','float32-bits'),
  ('npcMontageTag',TAG,'gameplay-tag32'),('playRate','float','float32-bits'),('radioId','string','byte-payload'),
  ('repeatAnim','bool','bool-byte'),('rootMotion','bool','bool-byte'),('templateId','string','byte-payload'),
  ('type','Beyond.Gameplay.AI.CharPatrolPointActionType','scalar32'),('waitTime','float','float32-bits')),
 ENEMY_ACTION:(('actionEndType','Beyond.Gameplay.AI.EnemyPatrolPointActionEndType','scalar32'),('animName','string','byte-payload'),
  ('duration','float','float32-bits'),('eventKey','string','byte-payload'),('radioId','string','byte-payload'),
  ('repeatAnim','bool','bool-byte'),('rootMotion','bool','bool-byte'),('rotationY','float','float32-bits'),
  ('templateDesc','string','byte-payload'),('templateId','string','byte-payload'),('templateName','string','byte-payload'),
  ('type','Beyond.Gameplay.AI.EnemyPatrolPointActionType','scalar32'),('waitTime','float','float32-bits')),
 CHAR_POINT:(('actions',list_type(CHAR_ACTION),'authored-patrol-list'),
  ('patrolGait','Beyond.Gameplay.AI.CharPatrolPointGait','scalar32'),('position','UnityEngine.Vector3','unity-vector3-raw12')),
 ENEMY_POINT:(('actions',list_type(ENEMY_ACTION),'authored-patrol-list'),
  ('patrolGait','Beyond.Gameplay.AI.EnemyPatrolPointGait','scalar32'),('position','UnityEngine.Vector3','unity-vector3-raw12')),
 CHAR:(('charPatrolLoopType','Beyond.Gameplay.AI.CharPatrolLoopType','scalar32'),('patrolId','ulong','scalar64-bits'),
  ('points',list_type(CHAR_POINT),'authored-patrol-list')),
 ENEMY:(('enemyPatrolLoopType','Beyond.Gameplay.AI.EnemyPatrolLoopType','scalar32'),('patrolId','ulong','scalar64-bits'),
  ('points',list_type(ENEMY_POINT),'authored-patrol-list')),
}
CHILDREN={CHAR_POINT:CHAR_ACTION,ENEMY_POINT:ENEMY_ACTION,CHAR:CHAR_POINT,ENEMY:ENEMY_POINT}
LISTS={list_type(child):child for child in CHILDREN.values()}


def operation(kind,declared):
 if kind=='byte-payload':return 'byte-payload'
 if kind=='authored-patrol-list'and declared in LISTS:return list_key(LISTS[declared])
 return None


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if (plan is None or pending or source.get('wrappedType')!=name or not isinstance(program,dict)
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (i,n,k,operation(k,t))for i,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({operation(k,t)for n,t,k in plan if operation(k,t)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,operation(k,t))for n,t,k in plan if k=='authored-patrol-list']):
  raise ValueError('storyAuthoredPatrol.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,key):
 typename=join.get('typeName');element=LISTS.get(typename);cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 spec=usage.get('methodSpec')
 if (element is None or key!=list_key(element)or child.get('nativeInputs')!=pins
  or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(typename,element,[-1,LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','finiteElementProfileAdmitted',
   'actualCallbackEqualsProvedChildRequired','initiallyNullListRequired'))
  or cap.get('runtimeProviderSelectionObserved')is not False or cap.get('elementWireBytes')is not None
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(spec[0],join['sourceTargetRva'])):
  raise ValueError('storyAuthoredPatrol.exact-list-parent:'+str(key))
 return dict(fieldName=join['fieldName'],typeName=typename,capability=key,countLimit=LIMIT,
  readerMethodDefinition=spec[0],sourceTargetRva=join['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 """Fresh selected source, child/count/callback and actual host joins for six records."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar,buff_gameplay_tag_native
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 need=lambda k,e,a:scalar.need('storyAuthoredPatrol',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('six-explicit-wrappers',set(PLANS),set(wrappers))
 generated=generated_reader_sources.derive_many(image,pins,[wrappers[name].name for name in PLANS]);records={};caps={};parents={}
 tag=buff_gameplay_tag_native.validate_on_image(image,pins);need('independent-GameplayTag','validated',tag.get('status'))
 for name,row in zip(PLANS,generated['owners'],strict=True):
  source=require_complete(row,validator='storyAuthoredPatrol',type_name=name)
  need('exact-own-order:'+name,[(n,t)for n,t,k in PLANS[name]],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  typed={};collections={};components={};children={};proofs={}
  for read in source['orderedSourceReads']:
   index=read['memberIndex'];member,declared,kind=PLANS[name][index]
   if kind!='authored-patrol-list':continue
   element=LISTS[declared];need('independently-complete-child:'+element,True,element in caps)
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyAuthoredPatrol.child')
   proof=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=element,count_limit=LIMIT)
   key=list_key(element);cap=dict(typeName=declared,elementType=element,countRange=[-1,LIMIT],countLimit=LIMIT,headerBytes=4,
    elementWireBytes=None,nullable=True,positiveCountsAdmitted=True,finiteElementProfileAdmitted=True,
    actualCallbackEqualsProvedChildRequired=True,initiallyNullListRequired=True,runtimeProviderSelectionObserved=False,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
   typed[index]=usage;collections[declared]=(key,kind,key);components[index]=dict(nativeInputs=pins,capabilities={key:cap})
   children[key]=cap;children[record_key(element)]=caps[element];proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={TAG:tag},
   typed_requests=typed,collections=collections,collection_children=components,collection_binder=bind_collection)
  bind_program(name,source,program,pending)
  enums={}
  for member,declared,kind in PLANS[name]:
   if kind!='scalar32'or declared=='int':continue
   need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));value=ctx.field(declared+'::value__')
   need('actual-32bit-enum:'+declared,True,value[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=value[1],field=list(value))
  pooled={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
   for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-own-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  need('whole-owned-original-output:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  cap=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,childCapabilities=children,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,finiteFloatProfile=True,ordinaryAdapterAdmitted=True,
   gameplayTagSourceProved=name==CHAR_ACTION,actualCallbackEqualsProvedChildRequired=True,
   wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
  if name in FIELDS.values():
   field,=[field for field,original in FIELDS.items()if original==name]
   declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field)
   need('actual-host-list:'+field,list_type(name),declaration['typeName'])
   usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyAuthoredPatrol.host')
   listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=name,count_limit=LIMIT)
   cap['parentBinding']=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field,typeName=declaration['typeName'],capability=record_key(name),
    readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],countLimit=LIMIT,
    actualCallbackEqualsProvedChildRequired=True)
   parents[field]=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=cap['parentBinding'])
  from scripts.game_data.codecs.leveldata.current_authored_patrol import validate
  validate(name,cap);caps[name]=cap;records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pooled,children=proofs)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-authored-patrol-components.v1',status='validated-conditional-authored-patrol-records',
  nativeInputs=pins,records=records,capabilities=caps,parents=parents,gameplayTag=tag,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Six explicit ordinary Character/Enemy patrol/action/point wrapper sources, all new/existing/FF frames, concrete adapters/GetValue, nominal enums/GameplayTag/pooled strings and independently current list/count/callback/actual host joins.',
   conditional='Ready matching callbacks/coherent cache and contexts, initially null count-sized reference lists, normal allocation/collector/helper effects and stable disjoint nonwrapping buffered input. Finite floats/counts/node budgets are projection limits.',
   unresolved=['runtime provider/formatter selection','patrol controller conversion/activation, action dispatch, checkpoint or playback','whole owner physical EOF/public source receipts']))))
