"""Positive Predefine/PowerGate and SafeZone/Box graphs, separate from empty gates."""
import json

SAFE='Beyond.Gameplay.LevelSafeZoneData'
BOX=SAFE+'+Box'
PREDEFINE='Beyond.Gameplay.LevelFactoryPredefineData'
POWER=PREDEFINE+'+PowerGate'
LIST=lambda n:'System.Collections.Generic.List`1<'+n+'>'
LIMIT=4096
NODE_LIMIT=16384
FIELDS={'safeZone':SAFE,'factoryPredefineData':PREDEFINE}
CHILDREN={SAFE:BOX,PREDEFINE:POWER}
CAPS={SAFE:'story-safe-zone-positive',PREDEFINE:'story-factory-predefine-positive'}
PLANS={BOX:(('center','UnityEngine.Vector3','unity-vector3-raw12'),('extents','UnityEngine.Vector3','unity-vector3-raw12'),
 ('rotation','UnityEngine.Vector3','unity-vector3-raw12')),
 POWER:(('instKey','string','byte-payload'),('outLinkDirection','UnityEngine.Vector3','unity-vector3-raw12'),
  ('outLinkLength','float','float32-bits'),('toInstKey','string','byte-payload'),('toScene','string','byte-payload')),
 SAFE:(('boxes',LIST(BOX),'auxiliary-record-list'),),PREDEFINE:(('powerGates',LIST(POWER),'auxiliary-record-list'),)}
LISTS={LIST(child):child for child in CHILDREN.values()}


def list_key(name):
 if name not in LISTS:raise ValueError('auxiliaryContainer.unknown-list')
 return 'story-auxiliary-record-list:'+name


def operation(declared,kind):
 return list_key(declared)if kind=='auxiliary-record-list'else'byte-payload'if kind=='byte-payload'else None


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
   (n,t,operation(t,k))for n,t,k in plan if k=='auxiliary-record-list']):
  raise ValueError('auxiliaryContainer.exact-finite-program:'+str(name))


def bind_collection(pins,join,child,key):
 name=join.get('typeName');cap=child.get('capabilities',{}).get(key,{});usage=join.get('typedRequest',{})
 if(name not in LISTS or key!=list_key(name)or child.get('nativeInputs')!=pins
  or(cap.get('typeName'),cap.get('elementType'))!=(name,LISTS[name])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or cap.get('countRange')!=[-1,LIMIT]or cap.get('wholeGrammarAdmitted')is not False
  or cap.get('liveFormatterSelectionObserved')is not False
  or any(cap.get(k)is not True for k in('profileAdmitted','elementGrammarAdmitted','initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[name]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('readerMethodDefinition'))is not int or type(cap.get('sourceTargetRva'))is not int
  or(cap['readerMethodDefinition'],cap['sourceTargetRva'])!=(usage['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('auxiliaryContainer.exact-list-parent')
 return dict(fieldName=join['fieldName'],typeName=name,capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 need=lambda k,e,a:scalar.need('auxiliaryContainer',k,e,a)
 _publication_gate(image,pins);need('same-selected-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('four-exact-current-wrappers',set(PLANS),set(wrappers))
 result=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in PLANS])
 sources={n:require_complete(r,validator='auxiliaryContainer',type_name=n)for n,r in zip(PLANS,result['owners'],strict=True)}
 for n in PLANS:compile_member_program(sources[n],pins,wrapper_name=wrappers[n].name,type_name=n,value4={})
 abi=reference_reader_abi(image,pins);records={};record_caps={};caps={};parents={}
 for name,plan in PLANS.items():
  source=sources[name];requests={};collections={};components={};collection_proofs={};list_caps={}
  need('exact-own-declarations:'+name,[(n,t)for n,t,k in plan],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
  for read in source['orderedSourceReads']:
   declared=read['declaredType']
   if declared not in LISTS:continue
   child=LISTS[declared];need('own-complete-element',True,child in record_caps)
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='auxiliaryContainer.actualList')
   proof=reference_list(image,pins,typed_request=usage,call_target=base+read['sourceTargetRva'],element_type=child,count_limit=LIMIT)
   key=list_key(declared);cap=dict(typeName=declared,elementType=child,countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,
    profileAdmitted=True,wholeGrammarAdmitted=False,elementGrammarAdmitted=True,initiallyNullListRequired=True,
    actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
    readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=proof['witnessComponent']['callTargetRva'])
   requests[read['memberIndex']]=usage;collections[declared]=(key,'auxiliary-record-list',key)
   components[read['memberIndex']]=dict(nativeInputs=pins,capabilities={key:cap});list_caps[key]=cap;collection_proofs[read['fieldName']]=proof
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collections,collection_children=components,collection_binder=bind_collection)
  bind_program(name,source,program,pending)
  pair=derive_pair(image,name);adapter=derive_adapter(image,pins,pair,wrappers[name])
  need('same-owned-getter:'+name,source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
  need('whole-owned-original:'+name,True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
  need('same-concrete-slot5:'+name,source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  record_caps[name]=dict(typeName=name,memberCount=len(plan),program=program,nullAdmitted=True,positiveAdmitted=True,
   ordinaryAdapterAdmitted=True,profileAdmitted=True,actualCallbackEqualsProvedChildRequired=True,
   wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False)
  records[name]=dict(source=source,compiled=program,pair=pair,adapter=adapter,pooled=pooled,collections=collection_proofs)
  if name not in CHILDREN:continue
  field_name,=[field for field,root in FIELDS.items()if root==name]
  field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==field_name)
  need('exact-actual-root-type:'+field_name,name,field['typeName'])
  usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='auxiliaryContainer.actualHost')
  typed=bind_typed_read(image,usage,method_name='ReadValue',argument=name,kind=18,reference=True)
  need('exact-reference-source',(abi['referenceReaderMethodDefinition'],abi['referenceReaderTargetRva']),
   (usage['methodSpec'][0],read['sourceTarget']-base))
  binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=field_name,typeName=name,capability=CAPS[name],
   readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTarget']-base,actualCallbackEqualsProvedChildRequired=True)
  cap=dict(typeName=name,capability=CAPS[name],memberCount=1,records={n:record_caps[n]for n in(name,CHILDREN[name])},collections=list_caps,
   parentBinding=binding,countLimit=LIMIT,nodeLimit=NODE_LIMIT,profileAdmitted=True,wholeGrammarAdmitted=False,
   actualCallbackEqualsProvedChildRequired=True,coherentWrapperStorageRequired=True,initiallyNullListsRequired=True,
   finiteFloatProfile=True,liveFormatterSelectionObserved=False)
  from scripts.game_data.codecs.leveldata.current_auxiliary_container import validate
  validate(cap);caps[name]=cap;parents[field_name]=dict(declaration=field,source=read,typedRequest=usage,typedBinding=typed,binding=binding)
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-auxiliary-container-components.v1',status='validated-conditional-positive-auxiliary-containers',
  nativeInputs=pins,records=records,capabilities=caps,parents=parents,referenceABI=abi,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
  evidenceBoundary=dict(exact='Only the separate current SafeZone/Box and FactoryPredefine/PowerGate ordinary records, complete sources/lifecycle/adapters/frames, exact pooled/vector/Single fields, positive reference-list count/callback/Add sources and both own LevelData ReadValue parents.',
   conditional='Ready matching callbacks, coherent contexts/wrapper/original/cache and initially-null count-sized lists, normal compatible provider/allocation/helper/collector effects and buffered disjoint storage; finite floats and bounded resources define the projection.',
   unresolved=['runtime safe-zone or factory behavior','whole host/public owner/pool/physical EOF']))))
