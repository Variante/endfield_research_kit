"""Exact finite Enemy born-animation and spawn-buff subtrees; parent is separate."""
import json

from scripts.game_data.memorypack.leveldata_extended_record_sources import STRINGS,STRING_CAP,bind_strings

BORN='Beyond.Gameplay.AI.EnemyCommonPlayTemplate+BornBehaviorData'
SEQ='Beyond.Gameplay.AI.EnemyCommonPlayTemplate+BornSeqAnimItem'
BUFF='Beyond.Gameplay.SpawnerBuffInst'
KV='Beyond.Gameplay.SpawnerBlackboardKVPair'
LIMIT=4096
NODE_LIMIT=16384
KEYS={BORN:'story-enemy-born-behavior',BUFF:'story-enemy-spawn-buff'}
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
LISTS={LIST(SEQ):SEQ,LIST(KV):KV}
def list_key(name):return 'story-enemy-reference-list:'+name
def leaf_key(name):return 'story-enemy-leaf:'+name
PLANS={
 BORN:(('bornCanInterrupt','bool','bool-byte'),('canInterruptTime','float','float32-bits'),('desc','string','byte-payload'),
  ('enterAnimId','string','byte-payload'),('enterAnimSpeed','float','float32-bits'),('enterBuffId','string','byte-payload'),
  ('enterMode','Beyond.Gameplay.AI.EnemyCommonPlayTemplate+PlayMode','scalar32'),('enterRepeat','bool','bool-byte'),
  ('enterRootMotion','bool','bool-byte'),('enterSeqAnimList',LIST(SEQ),'enemy-reference-list'),('enterSkillId','string','byte-payload'),
  ('exitAnimId','string','byte-payload'),('exitAnimSpeed','float','float32-bits'),('exitBuffId','string','byte-payload'),
  ('exitMode','Beyond.Gameplay.AI.EnemyCommonPlayTemplate+PlayMode','scalar32'),('exitRootMotion','bool','bool-byte'),
  ('exitSkillId','string','byte-payload'),('randomExitAnimId','bool','bool-byte'),('randomExitAnimIds',STRINGS,'pooled-string-list')),
 BUFF:(('blackboard',LIST(KV),'enemy-reference-list'),('buffId','string','byte-payload'))}


def operation(kind,declared):
 if kind=='byte-payload':return 'byte-payload'
 if kind=='pooled-string-list':return STRING_CAP
 if kind=='enemy-reference-list'and declared in LISTS:return list_key(LISTS[declared])
 return None


def bind_program(name,source,program,pending):
 plan=PLANS.get(name)
 if(plan is None or pending or not isinstance(program,dict)or source.get('wrappedType')!=name
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in plan]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(plan)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,operation(k,t))for j,(n,t,k)in enumerate(plan)]
  or program.get('requiredCapabilities')!=sorted({operation(k,t)for n,t,k in plan if operation(k,t)is not None})
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,operation(k,t))for n,t,k in plan if k in('enemy-reference-list','pooled-string-list')]):
  raise ValueError('storyEnemyNested.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,key):
 if key==STRING_CAP:return bind_strings(pins,join,child,key)
 declared=join.get('typeName');element=LISTS.get(declared);cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(element is None or key!=list_key(element)or child.get('nativeInputs')!=pins
  or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(declared,element,[-1,LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','finiteElementProfileAdmitted','initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
  or cap.get('elementWireBytes')is not None or cap.get('runtimeProviderSelectionObserved')is not False
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[declared]
  or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyEnemyNested.exact-reference-list-parent:'+str(key))
 return dict(fieldName=join['fieldName'],typeName=declared,capability=key,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper,leveldata_leaf_record_sources
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.pooled_string_list_sources import validate_string_components
 from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 check=lambda k,e,a:scalar.need('storyEnemyNested',k,e,a)
 _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 leaves=leveldata_leaf_record_sources.derive(image,pins,type_names=[SEQ,KV]);abi=reference_reader_abi(image,pins)
 strings=validate_string_components(image,_load('levelscript_pooled_string_list_native.json',pins))
 check('independent-pooled-string-callback',(5,4,8),(strings['stringFormatterSlot'],strings['wireBytes'],strings['managedReferenceBytes']))
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 check('two-exact-current-wrappers',set(PLANS),set(wrappers));generated=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
 records={};caps={}
 for name,row in zip(PLANS,generated['owners'],strict=True):
  source=require_complete(row,validator='storyEnemyNested',type_name=name)
  check('exact-declared-order:'+name,[(n,t)for n,t,k in PLANS[name]],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  requests={};collections={};components={};children={};proofs={}
  for read in source['orderedSourceReads']:
   j=read['memberIndex'];member,declared,kind=PLANS[name][j]
   if kind not in('enemy-reference-list','pooled-string-list'):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyEnemyNested.actualParent');requests[j]=usage
   element='string'if kind=='pooled-string-list'else LISTS[declared]
   proof=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=element,count_limit=LIMIT)
   if kind=='pooled-string-list':
    key=STRING_CAP;cap=dict(closedListType=STRINGS,elementType='string',elementValueType=False,nullable=True,positiveCountsAdmitted=True,
     elementGrammarAdmitted=True,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,initiallyNullListRequired=True,actualCallbackEqualsPooledStringRequired=True,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
   else:
    key=list_key(element);children[leaf_key(element)]=leaves['capabilities'][element]
    cap=dict(typeName=declared,elementType=element,countRange=[-1,LIMIT],countLimit=LIMIT,headerBytes=4,elementWireBytes=None,
     nullable=True,positiveCountsAdmitted=True,finiteElementProfileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
     initiallyNullListRequired=True,runtimeProviderSelectionObserved=False,
     packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
   collections[declared]=(key,kind,key);components[j]=dict(nativeInputs=pins,capabilities={key:cap});children[key]=cap;proofs[member]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},typed_requests=requests,
   collections=collections,collection_children=components,collection_binder=bind_collection)
  bind_program(name,source,program,pending);enums={}
  for member,declared,kind in PLANS[name]:
   if kind!='scalar32':continue
   check('own-nominal-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
   check('own-32bit-enum:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  check('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  check('same-concrete-callback:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  check('whole-owned-Original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  cap=dict(typeName=name,memberCount=len(PLANS[name]),program=program,enumBackings=enums,childCapabilities=children,nodeLimit=NODE_LIMIT,
   nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,finiteFloatProfile=True,ordinaryAdapterAdmitted=True,
   actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
   referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'],
   parentFieldAdmitted=False,wholeOwnerAdmitted=False)
  from scripts.game_data.codecs.leveldata.current_enemy_nested import validate
  validate(name,cap);caps[name]=cap;records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,enums=enums,children=proofs)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-enemy-nested-components.v1',status='validated-conditional-enemy-nested-records',nativeInputs=pins,
  records=records,capabilities=caps,leafRecords=leaves,pooledStringElements=strings,referenceABI=abi,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Own BornBehavior19/SpawnerBuffInst2 complete ordinary sources/frames/adapters, distinct Seq5/KV4 children, exact nominal PlayMode/pool sources and independent reference/string lists.',
   conditional='Initially null count-sized lists, initialized matching contexts/callbacks, coherent caches and normal compatible provider/allocation/collector/helper effects. Finite floats/counts/node budget are projection bounds.',
   unresolved=['actual enclosing Enemy fields/collections/host','arbitrary object dictionary values','runtime behavior/provider selection','whole owner physical EOF/publication']))))
