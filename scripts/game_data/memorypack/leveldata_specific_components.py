"""Finite current spaceship grammar under explicit erased-dictionary conditions."""
import json
from scripts.game_data.memorypack.leveldata_specific_transport_sources import TYPE,CHILD
from scripts.game_data.memorypack import leveldata_ship_dictionary_sources as cabins
from scripts.game_data.memorypack import leveldata_ship_u64_dictionary_sources as machines
from scripts.game_data.memorypack import leveldata_vector_tuple_list_sources as tuples

CAP='story-level-specific'
CABIN_CAP='story-ship-cabin-dictionary'
MACHINE_CAP='story-ship-uint64-dictionary'
ULONG_CAP='story-ship-uint64-list'
ULONGS='System.Collections.Generic.List`1<ulong>'
CABINS='System.Collections.Generic.Dictionary`2<string,'+cabins.CABIN+'>'
LIMIT=4096
PLAN=(('cabinSlotInfoLut',CABINS,'ship-cabin-dictionary'),('growBoxSceneObjectId',ULONGS,'uint64-list'),
 ('manufacturingRoomMachine',machines.TYPE,'ship-uint64-dictionary'),('showcaseRootPos','UnityEngine.Vector3','unity-vector3-raw12'),
 ('showcaseSlotBindAPList',ULONGS,'uint64-list'),('showcaseSlotLocalPosInfoList',tuples.LIST,'vector3-pair-list'),
 ('spawnPos','UnityEngine.Vector3','unity-vector3-raw12'),('spawnRot','UnityEngine.Vector3','unity-vector3-raw12'))
OPERATIONS={'ship-cabin-dictionary':CABIN_CAP,'ship-uint64-dictionary':MACHINE_CAP,'uint64-list':ULONG_CAP,'vector3-pair-list':tuples.LIST_CAP}


def validate_ulong(cap):
 if (not isinstance(cap,dict)or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(ULONGS,'ulong',[-1,LIMIT])
  or any(type(cap.get(k))is not int or cap[k]!=v for k,v in dict(countLimit=LIMIT,headerBytes=4,elementWireBytes=8,elementRawBits=64).items())
  or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','rawBitsPreserved','initiallyNullOutputRequired','actualCallbackEqualsProvedChildRequired'))
  or any(cap.get(k)is not False for k in('runtimeProviderSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted'))):
  raise ValueError('storyLevelSpecific.exact-UInt64-list-profile')


def validate_child(capability,caps):
 from scripts.game_data.codecs.leveldata import current_ship_dictionary,current_vector_tuple
 if capability==CABIN_CAP:current_ship_dictionary.validate_cabin(caps.get(capability))
 elif capability==MACHINE_CAP:current_ship_dictionary.validate_uint64(caps.get(capability))
 elif capability==ULONG_CAP:validate_ulong(caps.get(capability))
 elif capability==tuples.LIST_CAP:current_vector_tuple.validate_list(caps.get(capability),caps.get(tuples.VALUE_CAP))
 else:raise ValueError('storyLevelSpecific.closed-collection-capability')


def bind_collection(pins,join,child,capability):
 expected={CABIN_CAP:CABINS,MACHINE_CAP:machines.TYPE,ULONG_CAP:ULONGS,tuples.LIST_CAP:tuples.LIST}
 cap=child.get('capabilities',{}).get(capability,{});usage=join.get('typedRequest',{});typename=expected.get(capability)
 spec=usage.get('methodSpec')
 if (typename is None or child.get('nativeInputs')!=pins or join.get('typeName')!=typename
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[typename]
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or type(join.get('sourceTargetRva'))is not int or join['sourceTargetRva']<=0
  or type(cap.get('packableReaderMethodDefinition'))is not int or type(cap.get('packableReaderTargetRva'))is not int
  or(cap['packableReaderMethodDefinition'],cap['packableReaderTargetRva'])!=(spec[0],join['sourceTargetRva'])):
  raise ValueError('storyLevelSpecific.exact-collection-parent')
 validate_child(capability,child['capabilities'])
 result=dict(fieldName=join['fieldName'],typeName=typename,capability=capability,countLimit=LIMIT,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],actualCallbackEqualsProvedChildRequired=True)
 if capability in(CABIN_CAP,MACHINE_CAP):
  result.update({key:cap[key]for key in('sourceWitnessClassArguments','closedPointerEquivalenceProved',
   'actualCallbackEqualsSourceWitnessRequired','actualClosedContextAndSourceBodyCompatibilityRequired',
   'typedConstructorAndHelperCompatibilityRequired','normalNonthrowingInsertRequired','runtimeProviderSelectionObserved')})
 return result


def bind_program(source,program,pending):
 if (pending or source.get('wrappedType')!=CHILD or not isinstance(program,dict)
  or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
  or type(program.get('memberCount'))is not int or program['memberCount']!=len(PLAN)
  or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
  or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
   (index,n,k,OPERATIONS.get(k))for index,(n,t,k)in enumerate(PLAN)]
  or program.get('requiredCapabilities')!=sorted(OPERATIONS.values())
  or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
   (n,t,OPERATIONS[k])for n,t,k in PLAN if k in OPERATIONS]):raise ValueError('storyLevelSpecific.exact-eight-member-program')


def bind_parent(pins,field,read,usage,reader,base):
 spec=usage.get('methodSpec')
 if (field.get('name')!='specificData'or field.get('typeName')!=TYPE or read.get('fieldName')!='specificData'
  or(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))!=(6,'MemoryPack.MemoryPackReader','ReadValue',[],[TYPE])
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or spec[0]!=reader.get('referenceReaderMethodDefinition')
  or type(read.get('sourceTarget'))is not int or read['sourceTarget']!=base+reader.get('referenceReaderTargetRva',-1)):
  raise ValueError('storyLevelSpecific.exact-current-host-ReadValue-parent')
 return dict(ownerType='Beyond.Gameplay.LevelData',fieldName='specificData',typeName=TYPE,capability=CAP,
  readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=read['sourceTarget']-base,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import generated_reader_sources,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.leveldata_specific_transport_sources import derive as derive_transport
 from scripts.game_data.memorypack.levelscript_collection_sources import derive_ulong_list_component
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
 need=lambda k,e,a:scalar.need('storyLevelSpecificComponents',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==CHILD]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('exact-eight-field-order',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 requests={};collections={};children={};caps={};proofs={}
 for read in source['orderedSourceReads']:
  index=read['memberIndex'];kind=PLAN[index][2]
  if kind not in OPERATIONS:continue
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyLevelSpecific.actualChild')
  target=base+read['sourceTargetRva'];key=OPERATIONS[kind];extra={}
  if key==CABIN_CAP:proof=cabins.derive_cabin(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
  elif key==MACHINE_CAP:proof=machines.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
  elif key==tuples.LIST_CAP:
   proof=tuples.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capabilities'][key];extra={tuples.VALUE_CAP:proof['capabilities'][tuples.VALUE_CAP]}
  else:
   proof=derive_ulong_list_component(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
   cap={k:proof[k]for k in('typeName','elementType','packableReaderMethodDefinition','packableReaderTargetRva','countLimit','countRange',
    'nullable','positiveCountsAdmitted','headerBytes','elementWireBytes','elementRawBits','rawBitsPreserved',
    'initiallyNullOutputRequired','actualCallbackEqualsProvedChildRequired','runtimeProviderSelectionObserved','parentFieldAdmitted','wholeOwnerAdmitted')}
  requests[index]=usage;collections[read['declaredType']]=(key,kind,key)
  children[index]=dict(nativeInputs=pins,capabilities={key:cap,**extra});proofs[read['fieldName']]=proof
  if key in caps:need('same-independent-list-profile:'+key,caps[key],cap)
  caps[key]=cap;caps.update(extra)
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=CHILD,value4={},
  typed_requests=requests,collections=collections,collection_children=children,collection_binder=bind_collection)
 bind_program(source,program,pending)
 transport=derive_transport(image,pins)
 need('same-selected-wrapper',(wrapper.name,CHILD),(transport['childWrapperName'],transport['childTypeName']))
 life=source['lifecycle'];coherent=life.get('coherentGetter',{});construction=source.get('constructedGetterJoin',{})
 need('actual-base-holder',(TYPE,16),tuple(life['baseHolder'][1:]));need('coherent-cache-base-holder',life['baseHolder'],coherent.get('baseHolder'))
 need('same-full-reference-cache-return',True,coherent.get('coherentNonNullSamePointerReturn'))
 need('base-holder-constructed-before-reader',True,16 in construction.get('constructedReferenceOffsets',[]))
 need('no-inherited-cache-alias-assumed',False,construction.get('inheritedCacheCoherenceAssumed'))
 need('same-inherited-holder',(TYPE,16),(transport['derivedHolder']['declaredType'],transport['derivedHolder']['offset']))
 need('actual-concrete-slot5',wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter',life['concreteFormatter']['method'][1])
 reader=reference_reader_abi(image,pins)
 field,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']=='specificData')
 usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyLevelSpecific.host')
 binding=bind_typed_read(image,usage,method_name='ReadValue',argument=TYPE,kind=18,reference=True)
 parent=bind_parent(pins,field,read,usage,reader,base)
 cap=dict(typeName=TYPE,childTypeName=CHILD,wrapperName=wrapper.name,memberCount=8,program=program,childCapabilities=caps,
  admittedRouteTags=[0],nullAdmitted=True,positiveAdmitted=True,wrapperNullAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,
  concreteOriginalAdapterUsed=False,finiteFloatProfile=True,countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True,
  sourceWitnessClassArguments={key:caps[key]['sourceWitnessClassArguments']for key in(CABIN_CAP,MACHINE_CAP)},
  closedPointerEquivalenceProved=False,actualDictionaryCallbacksEqualSourceWitnessRequired=True,
  actualDictionaryClosedContextAndSourceBodyCompatibilityRequired=True,typedDictionaryConstructorAndHelperCompatibilityRequired=True,
  normalNonthrowingDictionaryInsertRequired=True,storedMapSemanticsAdmitted=False,runtimeProviderSelectionObserved=False,
  parentBinding=parent,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
 from scripts.game_data.codecs.leveldata.current_specific import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-level-specific-components.v1',status='validated-conditional-current-spaceship-profile',nativeInputs=pins,
  source=source,compiled=program,children=proofs,transport=transport,referenceReader=reader,
  parent=dict(declaration=field,source=read,typedRequest=usage,typedBinding=binding,binding=parent),capability=cap,
  wholeUnionAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False,
  evidenceBoundary=dict(exact='Fresh complete SpaceShipSpecificData8 source/store/lifecycle/frame, finite independently proved dictionaries/UInt64 lists/raw24 tuple list, tag0/FF union and actual LevelData.specificData ReadValue nominal/context/E8 to current base canonical adapter/inherited GetValue conversion.',
   conditional='Both string-key dictionary callbacks must equal their independently registered object-key source witnesses with compatible actual closed contexts/receiver/helpers. Exact pooled-string/Cabin/UInt64 callbacks, typed constructors/provider/context/Initialize/TryInsert effects, normal nonthrowing insertion and stable buffered disjoint nonwrapping storage remain required. Stored-map semantics and live provider/callback/context selection are unobserved.',
   unresolved=['runtime dictionary/provider/callback/context selection and stored map behavior','actual whole LevelData/LevelScript owner physical EOF and public source receipts']))))
