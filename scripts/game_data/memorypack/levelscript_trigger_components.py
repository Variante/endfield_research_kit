"""Finite current TriggerVolume concrete children and exact root composition."""
import json

from scripts.game_data.memorypack import levelscript_trigger_union_sources as transport
from scripts.game_data.memorypack import uint_reference_dictionary_sources as dictionary

ROOT='Beyond.Gameplay.LevelScriptData'
TYPE=transport.TYPE
SHAPE='Beyond.Gameplay.LevelScriptTriggerVolumeShapeData'
ENUM='Beyond.Gameplay.KickableObjectType'
SHAPE_ENUM='Beyond.Gameplay.LevelScriptTriggerVolumeShapeType'
LIST=lambda name:'System.Collections.Generic.List`1<'+name+'>'
DICTIONARY='System.Collections.Generic.Dictionary`2<uint,'+TYPE+'>'
CHILDREN={0:TYPE+'ForKickableInteractive',1:TYPE+'ForLeader',2:TYPE+'ForTeam'}
CAP='story-trigger-volumes'
SHAPE_CAP='story-trigger-shape'
SHAPE_LIST_CAP='story-trigger-shape-list'
VECTOR_LIST_CAP='story-trigger-vector2-list'
ENUM_LIST_CAP='skill-enum-list:'+ENUM
ENUM_CAP='skill-enum-callback:'+ENUM
LIMIT=4096
NODE_LIMIT=16384
COMMON=(('enterCheckOnGround','bool','bool-byte'),('exitShapeStartIndex','int','scalar32'),
 ('isImportant','bool','bool-byte'),('shapeList',LIST(SHAPE),'trigger-shape-list'),('slotId','uint','scalar32'),
 ('triggerCountLimit','int','scalar32'),('triggerOnPole','bool','bool-byte'),('waitSrvRes','bool','bool-byte'))
PLANS={CHILDREN[0]:COMMON+(('filterByKickableType','bool','bool-byte'),('kickableTypeList',LIST(ENUM),'trigger-kickable-list')),
 CHILDREN[1]:COMMON,CHILDREN[2]:COMMON+(('targetTemplateId','string','byte-payload'),),
 SHAPE:(('polyLinePoints',LIST('UnityEngine.Vector2'),'trigger-vector2-list'),('position','UnityEngine.Vector3','unity-vector3-raw12'),
 ('radius','float','float32-bits'),('rotation','UnityEngine.Vector3','unity-vector3-raw12'),
 ('shapeType',SHAPE_ENUM,'scalar32'),('size','UnityEngine.Vector3','unity-vector3-raw12'))}
OPERATIONS={'trigger-shape-list':SHAPE_LIST_CAP,'trigger-vector2-list':VECTOR_LIST_CAP,
 'trigger-kickable-list':ENUM_LIST_CAP,'byte-payload':'byte-payload'}


def need(check,condition):
 if not condition:raise ValueError('storyTriggerComponents.'+check)


def bind_program(source,program,pending):
 name=source.get('wrappedType');plan=PLANS.get(name)
 need('exact-finite-concrete-program:'+str(name),plan is not None and not pending and isinstance(program,dict)
  and[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]==[(n,t)for n,t,k in plan]
  and type(program.get('memberCount'))is int and program['memberCount']==len(plan)
  and all(type(r.get('memberIndex'))is int for r in program.get('reads',[]))
  and[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program['reads']]==[
   (i,n,k,OPERATIONS.get(k))for i,(n,t,k)in enumerate(plan)]
  and program.get('requiredCapabilities')==sorted({OPERATIONS[k]for n,t,k in plan if k in OPERATIONS})
  and[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]==[
   (n,t,OPERATIONS[k])for n,t,k in plan if k in('trigger-shape-list','trigger-vector2-list','trigger-kickable-list')])


def bind_collection(pins,join,child,key):
 from scripts.game_data.codecs.leveldata.current_kickable_enum_list import require_capability
 usage=join.get('typedRequest',{});cap=child.get('capabilities',{}).get(key,{})
 expected={SHAPE_LIST_CAP:(LIST(SHAPE),SHAPE),VECTOR_LIST_CAP:(LIST('UnityEngine.Vector2'),'UnityEngine.Vector2'),ENUM_LIST_CAP:(LIST(ENUM),ENUM)}
 need('finite-exact-list-parent',key in expected and child.get('nativeInputs')==pins
  and usage.get('methodName')=='ReadPackable'and usage.get('methodArguments')==[expected[key][0]]
  and join.get('typeName')==expected[key][0]and isinstance(usage.get('methodSpec'),(list,tuple))and len(usage['methodSpec'])==3
  and type(usage['methodSpec'][0])is int and type(join.get('sourceTargetRva'))is int and join['sourceTargetRva']>0
  and(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))==(usage['methodSpec'][0],join['sourceTargetRva']))
 if key==ENUM_LIST_CAP:
  need('same-native-nominal-enum-list',cap.get('nativeInputs')==pins)
  require_capability(cap,child['capabilities'].get(ENUM_CAP,{}))
 else:
  need('own-selected-concrete-list',cap.get('typeName')==expected[key][0]and cap.get('elementType')==expected[key][1]
   and cap.get('elementCapability')==(SHAPE_CAP if key==SHAPE_LIST_CAP else'unity-vector2-raw8')
   and all(cap.get(k)is True for k in('nullable','positiveCountsAdmitted','elementGrammarAdmitted',
    'initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))
   and cap.get('wholeGrammarAdmitted')is False and cap.get('runtimeFormatterSelectionObserved')is False
   and type(cap.get('countLimit'))is int and cap['countLimit']==LIMIT
   and type(cap.get('headerBytes'))is int and cap['headerBytes']==4
   and cap.get('elementWireBytes','absent')==(None if key==SHAPE_LIST_CAP else 8))
 return dict(fieldName=join['fieldName'],typeName=expected[key][0],capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=join['sourceTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,
  actualNominalEnumCallbackRequired=key==ENUM_LIST_CAP)


def list_capability(key,usage,target):
 name,element,element_cap,width={SHAPE_LIST_CAP:(LIST(SHAPE),SHAPE,SHAPE_CAP,None),
  VECTOR_LIST_CAP:(LIST('UnityEngine.Vector2'),'UnityEngine.Vector2','unity-vector2-raw8',8)}[key]
 return dict(typeName=name,elementType=element,elementCapability=element_cap,elementWireBytes=width,
  headerBytes=4,countLimit=LIMIT,nullable=True,positiveCountsAdmitted=True,elementGrammarAdmitted=True,
  initiallyNullListRequired=True,actualCallbackEqualsProvedChildRequired=True,
  wholeGrammarAdmitted=False,runtimeFormatterSelectionObserved=False,
  packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=target)


def derive(image,pins,owners):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,enum_optin_native_sources as enums
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.leveldata_vector2_list_sources import derive_collection as vector_list
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 _publication_gate(image,pins)
 enum_source=enums.derive(image,pins,domain='story-kickable')
 need('reviewed-own-Kickable-enum-domain',enum_source.get('domain')=='story-kickable'
  and enum_source.get('defaultSkillDomainChanged')is False
  and enum_source.get('domainDeclaration')==dict(nominalEnums=[ENUM],collectionEnums=[ENUM],countLimit=LIMIT))
 base=image.pe.image_base;ctx=NativeReferenceContext(image)
 need('same-fresh-root-owners',owners.get('nativeInputs')==pins)
 union=transport.derive_transport(image,pins)
 need('exact-own-union-cases',[(r['tag'],r['wrappedType'])for r in union['programs']]==list(CHILDREN.items()))
 wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()if w.wrapped_type in PLANS}
 need('four-exact-own-concrete-wrappers',set(wrappers)==set(PLANS))
 names=[SHAPE,*CHILDREN.values()];results=generated_reader_sources.derive_many(image,pins,[wrappers[n].name for n in names])
 sources={name:require_complete(row,validator='storyTriggerComponents',type_name=name)for name,row in zip(names,results['owners'],strict=True)}
 records={};collections={};proofs={}
 for name in names:
  source=sources[name];requests={};components={};selected={};children={}
  for read in source['orderedSourceReads']:
   declared=read['declaredType'];index=read['memberIndex']
   if declared not in(LIST(SHAPE),LIST('UnityEngine.Vector2'),LIST(ENUM)):continue
   usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyTriggerComponents.actualList');requests[index]=usage
   target=base+read['sourceTargetRva']
   if declared==LIST(ENUM):
    proof=enums.bind_request(image,pins,enum_source,typed_request=usage,call_target=target,enum_type=ENUM)
    key=ENUM_LIST_CAP;cap=enum_source['capabilities'][key]
    component=dict(nativeInputs=pins,capabilities={key:cap,ENUM_CAP:enum_source['capabilities'][ENUM_CAP]})
   elif declared==LIST(SHAPE):
    proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type=SHAPE,count_limit=LIMIT)
    key=SHAPE_LIST_CAP;cap=list_capability(key,usage,proof['witnessComponent']['callTargetRva']);component=dict(nativeInputs=pins,capabilities={key:cap})
   else:
    proof=vector_list(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
    need('strict-Vector2-count-induction',proof['loopInduction']['nonnegativeCountRange']==[0,LIMIT]
     and proof['capability']['countLimit']==LIMIT)
    key=VECTOR_LIST_CAP;cap=list_capability(key,usage,proof['context']['callTargetRva']);component=dict(nativeInputs=pins,capabilities={key:cap})
   if key in collections:
    need('same-independently-derived-child-source:'+key,collections[key]==cap)
   collections[key]=cap;components[index]=component;children[read['fieldName']]=proof
   selected[declared]=key
  collection_map={t:(key,next(k for n,t2,k in PLANS[name]if t2==t),key)for t,key in selected.items()}
  program,pending=compile_member_program(source,pins,wrapper_name=wrappers[name].name,type_name=name,value4={},
   typed_requests=requests,collections=collection_map,collection_children=components,collection_binder=bind_collection)
  bind_program(source,program,pending)
  pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)
   for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
  backing=None;pair=adapter=None
  if name==SHAPE:
   need('nominal-shape-enum','System.Enum'==ctx.parent(SHAPE_ENUM));field=ctx.field(SHAPE_ENUM+'::value__')
   need('shape-enum-DWORD',field[1]in('int','uint'));backing=dict(typeName=SHAPE_ENUM,backing=field[1],field=list(field))
   pair=derive_pair(image,SHAPE);adapter=derive_adapter(image,pins,pair,wrappers[name])
   need('same-own-whole-Shape-getter',source['lifecycle']['GetValue']['program'].get('fullReferenceOutput')is True
    and source['lifecycle']['GetValue']['method']==adapter['getterMethod'])
  else:
   inherited,=[r for r in union['inheritedConversions']if r['wrapperName']==wrappers[name].name]
   need('same-selected-concrete-original-holder',inherited['holder']['offset']==16 and inherited['holder']['declaredType']==TYPE)
   pair=source['lifecycle']['concreteFormatter']
  records[name]=dict(typeName=name,memberCount=len(PLANS[name]),program=program,
   enumBacking=backing,unsignedFields=['slotId']if name!=SHAPE else[],nullAdmitted=True,positiveAdmitted=True,
   profileAdmitted=True,finiteSpatialFloatProfile=True,actualCallbackEqualsProvedChildRequired=True,
   wholeGrammarAdmitted=False,runtimeFormatterSelectionObserved=False)
  proofs[name]=dict(source=source,compiled=program,pooled=pooled,children=children,pair=pair,adapter=adapter)
 collections[ENUM_CAP]=enum_source['capabilities'][ENUM_CAP]
 root=owners['owners'][ROOT]
 field,read=next((f,r)for f,r in zip(root['fields'],root['program']['orderedReads'],strict=True)if f['name']=='triggerVolumes')
 need('actual-own-root-dictionary',field['typeName']==DICTIONARY and read['fieldName']=='triggerVolumes'and read['storeOffset']==field['offset'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyTriggerComponents.actualRoot')
 root_dictionary=dictionary.derive(image,pins,typed_request=usage,call_target=read['sourceTarget'],value_type=TYPE,count_limit=LIMIT)
 binding=dict(ownerType=ROOT,fieldName='triggerVolumes',typeName=DICTIONARY,elementType=TYPE,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=root_dictionary['callTargetRva'],fieldOffset=field['offset'],
  initiallyNullOutputRequired=True,actualCallbackEqualsCanonicalRequired=True,actualValueCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=DICTIONARY,capability=CAP,elementType=TYPE,admittedRouteTags=[0,1,2],caseTypes={str(k):v for k,v in CHILDREN.items()},
  records=records,collections=collections,dictionary=root_dictionary['capability'],parentBinding=binding,
  countLimit=LIMIT,nodeLimit=NODE_LIMIT,nullUnionMarker=255,reservedMarkersRefused=[251,252,253,254],canonicalTagEncoding=True,
  profileAdmitted=True,nullAdmitted=True,positiveAdmitted=True,ordinaryBaseAdapterAdmitted=True,
  initiallyNullOutputsRequired=True,actualCallbackEqualsCanonicalRequired=True,actualValueCallbackEqualsProvedChildRequired=True,
  wholeGrammarAdmitted=False,runtimeFormatterSelectionObserved=False,runtimeTriggerEvaluationProved=False)
 from scripts.game_data.codecs.levelscript.current_trigger_volumes import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.levelscript-trigger-components.v1',status='validated-conditional-current-trigger-volumes',
  nativeInputs=pins,capability=cap,transport=union,records=proofs,enumSource=enum_source,
  parent=dict(field=field,source=read,typedRequest=usage,collection=root_dictionary,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
