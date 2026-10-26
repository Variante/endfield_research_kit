"""Bounded current Enemy30 with separately authenticated nominal subtrees."""
import json
from scripts.game_data.memorypack import leveldata_enemy_nested_sources as nested
from scripts.game_data.memorypack import leveldata_enemy_dictionary_sources as dictionary
from scripts.game_data.memorypack import leveldata_string_array_sources as strings
from scripts.game_data.memorypack import leveldata_nullable_float_sources as nullable

TYPE='Beyond.Gameplay.LevelEnemyData'
AI='Beyond.Gameplay.AI.Config.EnemyAIOverrideAttr'
CAP='story-enemy-record'
AI_CAP='story-enemy-ai-override'
BUFF_LIST='System.Collections.Generic.List`1<'+nested.BUFF+'>'
BUFF_CAP='story-enemy-spawn-buff-list'
LIMIT=4096
NODE_LIMIT=16384
FIELD='enemies'
PLAN=(('aoiRadiusType','Beyond.Gameplay.Core.AoiRadiusEnum','scalar32'),('belongLevelScriptId','ulong','scalar64-bits'),
 ('createState','Beyond.Gameplay.Core.CreateState','scalar32'),('dependencyGroupId','ulong','scalar64-bits'),
 ('entityDataIdKey','string','byte-payload'),('entityType','Beyond.Gameplay.Core.ObjectType','scalar32'),
 ('forceLoad','bool','bool-byte'),('keepCrossMap','bool','bool-byte'),('levelLogicId','ulong','scalar64-bits'),
 ('overrideSendDieEvent','bool','bool-byte'),('position','UnityEngine.Vector3','unity-vector3-raw12'),
 ('rotation','UnityEngine.Vector3','unity-vector3-raw12'),('scale','UnityEngine.Vector3','unity-vector3-raw12'),('sendDieEvent','bool','bool-byte'),
 ('aiBlackboard',dictionary.TYPE,'enemy-empty-dictionary'),('bornBehaviorData',nested.BORN,'enemy-born-behavior'),
 ('bornTemplateId','string','byte-payload'),('buffs',BUFF_LIST,'enemy-spawn-buff-list'),
 ('enemyDefaultActionType','Beyond.Gameplay.AI.EnemyDefaultActionType','scalar32'),('enemyGroupId','int','scalar32'),
 ('enemyPatrolId','ulong','scalar64-bits'),('extraDelayToRecycleTime',nullable.TYPE,'nullable-single-raw8'),
 ('idleBreakAnimations',strings.ARRAY,'pooled-string-array'),('isDangerousEnemy','bool','bool-byte'),('level','int','scalar32'),
 ('overrideAIAttrData',AI,'enemy-ai-override'),('overrideAIConfig','string','byte-payload'),('overrideIdleBreak','bool','bool-byte'),
 ('patrolCfgType','Beyond.Gameplay.Core.EnemyPatrolCfgType','scalar32'),('respawnable','bool','bool-byte'))
OPERATIONS={'byte-payload':'byte-payload','enemy-empty-dictionary':dictionary.CAP,'enemy-born-behavior':nested.KEYS[nested.BORN],
 'enemy-spawn-buff-list':BUFF_CAP,'pooled-string-array':strings.CAP,'enemy-ai-override':AI_CAP}


def bind_program(source,program,pending):
 if (pending or not isinstance(program,dict)or source.get('wrappedType')!=TYPE
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
  or type(program.get('memberCount'))is not int or program['memberCount']!=30
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (j,n,k,OPERATIONS.get(k))for j,(n,t,k)in enumerate(PLAN)]
  or program.get('requiredCapabilities')!=sorted(set(OPERATIONS.values()))
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,OPERATIONS[k])for n,t,k in PLAN if k in('enemy-empty-dictionary','enemy-born-behavior','enemy-spawn-buff-list','pooled-string-array','enemy-ai-override')]):
  raise ValueError('storyEnemy.exact-bounded-thirty-member-program')


def bind_reference(pins,parent,child,key):
 expected={nested.KEYS[nested.BORN]:nested.BORN,AI_CAP:AI};name=expected.get(key)
 cap=child.get('capabilities',{}).get(key,{});usage=parent.get('typedRequest',{})
 if(name is None or child.get('nativeInputs')!=pins or cap.get('typeName')!=name or parent.get('typeName')!=name
  or any(cap.get(k)is not True for k in('profileAdmitted','ordinaryAdapterAdmitted','actualCallbackEqualsProvedChildRequired'))
  or cap.get('wholeGrammarAdmitted')is not False or cap.get('liveFormatterSelectionObserved')is not False
  or usage.get('methodName')!='ReadValue'or usage.get('methodArguments')!=[name]
  or not isinstance(usage.get('methodSpec'),(tuple,list))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or type(cap.get('referenceReaderMethodDefinition'))is not int or type(cap.get('referenceReaderTargetRva'))is not int
  or(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva'])!=(usage['methodSpec'][0],parent['sourceTargetRva'])):
  raise ValueError('storyEnemy.exact-nominal-reference-parent:'+str(key))
 return dict(fieldName=parent['fieldName'],typeName=name,capability=key,readerMethodDefinition=usage['methodSpec'][0],
  sourceTargetRva=parent['sourceTargetRva'],actualCallbackEqualsProvedChildRequired=True)


def bind_collection(pins,parent,child,key):
 cap=child.get('capabilities',{}).get(key,{});usage=parent.get('typedRequest',{})
 if(child.get('nativeInputs')!=pins or key not in(dictionary.CAP,BUFF_CAP)
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[parent.get('typeName')]
  or not isinstance(usage.get('methodSpec'),(list,tuple))or not usage['methodSpec']
  or type(usage['methodSpec'][0])is not int or usage['methodSpec'][0]<0
  or type(parent.get('sourceTargetRva'))is not int or parent['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(usage['methodSpec'][0],parent['sourceTargetRva'])):
  raise ValueError('storyEnemy.exact-collection-parent:'+str(key))
 if key==dictionary.CAP:
  from scripts.game_data.codecs.leveldata.current_enemy_dictionary import validate
  validate(cap)
  if parent.get('typeName')!=dictionary.TYPE:raise ValueError('storyEnemy.exact-empty-dictionary-type')
  return dict(fieldName=parent['fieldName'],typeName=dictionary.TYPE,capability=key,
   readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=parent['sourceTargetRva'],allowedCounts=[-1,0],countLimit=0,
   sourceWitnessClassArguments=['object','object'],closedPointerEquivalenceProved=False,
   actualCallbackEqualsCanonicalRequired=True,typedConstructorAndHelperCompatibilityRequired=True,
   actualCallbackSelectionObserved=False,providerFactorySelectionObserved=False,positiveObjectValuesAdmitted=False)
 if (parent.get('typeName')!=BUFF_LIST or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(BUFF_LIST,nested.BUFF,[-1,LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4).items())
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','finiteElementProfileAdmitted',
   'initiallyNullListRequired','actualCallbackEqualsProvedChildRequired'))or cap.get('elementWireBytes')is not None
  or cap.get('runtimeProviderSelectionObserved')is not False):raise ValueError('storyEnemy.exact-spawn-buff-list')
 return dict(fieldName=parent['fieldName'],typeName=BUFF_LIST,capability=key,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=parent['sourceTargetRva'],
  actualCallbackEqualsProvedChildRequired=True,initiallyNullListRequired=True)


def derive_owned_adapter(image,pins,source,wrapper):
 """Join the fresh cached getter program to its exact registered family.

 Family ownership supplies provenance only. The independently derived source
 owns the coherent return and the two compatible refresh programs.
 """
 from scripts.game_data.memorypack import scalar_param_native as scalar
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 need=lambda k,e,a:scalar.need('storyEnemy',k,e,a)
 need('owned-getter-nominal',TYPE,source.get('wrappedType'))
 getter=source['lifecycle']['GetValue'];owned=getter['ownedCoherentGetter']
 need('same-source-getter',getter['method'],owned['method'])
 need('coherent-whole-reference-return',True,owned.get('coherentNonNullSamePointerReturn'))
 need('coherent-program-whole-reference',True,owned['program'].get('fullSameReferenceReturned'))
 need('compatible-refresh-admitted',True,owned.get('refreshAdmitted'))
 paths=owned['compatibleRefresh']['programs']
 need('exact-compatible-refresh-paths',['empty','different'],[p['path']for p in paths])
 for path in paths:
  need('same-reference-refresh:'+path['path'],True,path['program'].get('sameBaseReferenceCachedAndReturned'))
 pair=derive_pair(image,TYPE,owned_getter_family=True)
 entry=pair['getterEntryProof']
 need('metadata-owned-getter-family','owned-getter-family',entry['kind'])
 need('same-pair-getter',getter['method'],entry['entryMethod'])
 need('same-fresh-getter-family',owned['family'],json.loads(json.dumps(entry['family'])))
 adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-owned-Original-getter',getter['method'],adapter['getterMethod'])
 need('same-concrete-callback',source['lifecycle']['concreteFormatter']['method'][0],
  pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 return pair,adapter


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar,pooled_source_helper
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_ordinary_leaf_sources import derive as ordinary
 from scripts.game_data.memorypack.leveldata_source_refusal import require_complete
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 need=lambda k,e,a:scalar.need('storyEnemy',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base;ctx=NativeReferenceContext(image)
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 row,=generated_reader_sources.derive_many(image,pins,[wrapper.name])['owners'];source=require_complete(row,validator='storyEnemy',type_name=TYPE)
 need('exact-thirty-current-fields',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 born=nested.derive(image,pins);ai=ordinary(image,pins,type_names=[AI]);abi=reference_reader_abi(image,pins)
 children={nested.KEYS[nested.BORN]:born['capabilities'][nested.BORN],nested.KEYS[nested.BUFF]:born['capabilities'][nested.BUFF],
  AI_CAP:dict(ai['capabilities'][AI],referenceReaderMethodDefinition=abi['referenceReaderMethodDefinition'],referenceReaderTargetRva=abi['referenceReaderTargetRva'])}
 requests={};collections={};components={};references={};reference_children={};arrays={};array_children={};proofs={}
 for read in source['orderedSourceReads']:
  index=read['memberIndex'];member,declared,kind=PLAN[index]
  if kind not in OPERATIONS or kind=='byte-payload':continue
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyEnemy.actualChild');requests[index]=usage;target=base+read['sourceTargetRva'];key=OPERATIONS[kind]
  if kind in('enemy-born-behavior','enemy-ai-override'):
   references[declared]=(key,kind,key);reference_children[declared]=dict(nativeInputs=pins,capabilities={key:children[key]});continue
  if kind=='pooled-string-array':
   proof=strings.derive(image,pins,typed_request=usage,call_target=target);children[key]=proof['capability']
   arrays[declared]=(key,kind,key);array_children[index]=dict(nativeInputs=pins,capabilities={key:proof['capability']},source=proof)
  elif kind=='enemy-empty-dictionary':
   proof=dictionary.derive(image,pins,typed_request=usage,call_target=target);children[key]=proof['capabilities'][key]
   collections[declared]=(key,kind,key);components[index]=proof
  else:
   proof=reference_list(image,pins,typed_request=usage,call_target=target,element_type=nested.BUFF,count_limit=LIMIT)
   cap=dict(typeName=BUFF_LIST,elementType=nested.BUFF,countRange=[-1,LIMIT],countLimit=LIMIT,headerBytes=4,elementWireBytes=None,
    nullable=True,positiveCountsAdmitted=True,finiteElementProfileAdmitted=True,initiallyNullListRequired=True,
    actualCallbackEqualsProvedChildRequired=True,runtimeProviderSelectionObserved=False,
    packableReaderMethodDefinition=usage['methodSpec'][0],packableReaderTargetRva=proof['witnessComponent']['callTargetRva'])
   children[key]=cap;collections[declared]=(key,kind,key);components[index]=dict(nativeInputs=pins,capabilities={key:cap})
  proofs[member]=proof
 # The source VM already re-proves this exact constructed child. Retain its
 # wire capability alongside the pure compiler's full region/program replay.
 actual_nullable=source['sourceScope']['constructedValueSources']['21']['proof']['nativeSource']
 need('same-selected-Nullable-source',pins,actual_nullable['nativeInputs']);children[nullable.CAP]=actual_nullable['capability']
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},typed_requests=requests,
  collections=collections,collection_children=components,collection_binder=bind_collection,
  references=references,reference_children=reference_children,reference_binder=bind_reference,
  arrays=arrays,array_children=array_children,array_binder=strings.bind_array)
 bind_program(source,program,pending);enums={}
 for member,declared,kind in PLAN:
  if kind!='scalar32'or declared=='int':continue
  need('nominal-enum:'+declared,'System.Enum',ctx.parent(declared));field=ctx.field(declared+'::value__')
  need('exact-32bit-enum:'+declared,True,field[1]in('int','uint'));enums[member]=dict(typeName=declared,backing=field[1],field=list(field))
 pair,adapter=derive_owned_adapter(image,pins,source,wrapper)
 pooled={r['fieldName']:pooled_source_helper.validate_on_image(image,base+r['sourceTargetRva'],pins)for r in source['orderedSourceReads']if r['kind']=='byte-payload'}
 declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==FIELD)
 need('exact-actual-host-type','System.Collections.Generic.List`1<'+TYPE+'>',declaration['typeName'])
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyEnemy.actualHost')
 listing=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
 binding=dict(ownerType='Beyond.Gameplay.LevelData',fieldName=FIELD,typeName=declaration['typeName'],capability=CAP,countLimit=LIMIT,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=listing['witnessComponent']['callTargetRva'],actualCallbackEqualsProvedChildRequired=True)
 cap=dict(typeName=TYPE,memberCount=30,program=program,enumBackings=enums,childCapabilities=children,nodeLimit=NODE_LIMIT,parentBinding=binding,
  nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,ordinaryAdapterAdmitted=True,finiteFloatProfile=True,
  coherentOriginalCacheRequired=True,compatibleRefreshOnly=True,coldInitializationObserved=False,
  actualCallbackEqualsProvedChildRequired=True,wholeGrammarAdmitted=False,liveFormatterSelectionObserved=False,
  aiBlackboardAllowedCounts=[-1,0],positiveObjectValuesAdmitted=False,
  nullableSourceBinding=dict(fieldName='extraDelayToRecycleTime',typeName=nullable.TYPE,capability=nullable.CAP,
   readerMethodDefinition=source['orderedSourceReads'][21]['context']['methodSpec'][0],
   sourceTargetRva=source['orderedSourceReads'][21]['sourceTargetRva']))
 from scripts.game_data.codecs.leveldata.current_enemy import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-enemy-components.v1',status='validated-conditional-enemy-empty-blackboard-profile',nativeInputs=pins,
  capability=cap,record=dict(source=source,compiled=program,pair=pair,adapter=adapter,enums=enums,pooled=pooled,children=proofs),
  nested=born,aiOverride=ai,referenceABI=abi,parent=dict(declaration=declaration,source=read,typedRequest=usage,collection=listing,binding=binding),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
   exact='Own thirty-field complete Enemy reader/Original getter/canonical adapter/all4 frames, typed nominal current child sources/compiled joins and actual LevelData list parent.',
   conditional='aiBlackboard only null/new-empty under separately retained erased dictionary callback/constructor/provider conditions; initially-null count-sized child lists/arrays with matching ready callbacks/contexts and normal compatible helpers. Finite scalar/spatial floats and resource budgets bound the projection; Nullable preserves all eight raw bits/bytes.',
   unresolved=['positive arbitrary-object dictionary entries and runtime callback/constructor/provider selection','runtime Enemy creation/behavior','whole host physical EOF/public source receipt']))))
