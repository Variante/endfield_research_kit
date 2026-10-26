"""Finite current water-volume record with independent LangKey and Vector3 lists.

Actual compatible ready callbacks/provider contexts, initially null count-sized
lists, buffered disjoint storage and normal helper/barrier effects remain
conditions. This component grants no enclosing LevelData or physical EOF.
"""
TYPE='Beyond.Gameplay.LevelWaterVolumeData'
CAP='story-water-volume'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
LIMIT=4096
PARENT_FIELDS=('waterVolumes','riftVolumes')
from scripts.game_data.memorypack import leveldata_lang_key_components as language
from scripts.game_data.memorypack import leveldata_vector3_list_sources as vectors

PLAN=(('amountCurrent','int','scalar32'),('amountMax','int','scalar32'),
 ('fillEase','Beyond.Gameplay.Core.TweenManager+TweenEase','scalar32'),
 ('fillSpeed','float','float32-bits'),('flowDirection','float','float32-bits'),('flowSpeed','float','float32-bits'),
 ('heightMax','float','float32-bits'),('id','ulong','scalar64-bits'),('intContainedWater','bool','bool-byte'),
 ('isConnectNavMesh','bool','bool-byte'),('isInfinite','bool','bool-byte'),('isPrototype','bool','bool-byte'),
 ('isUseLunaConfig','bool','bool-byte'),('lunaConfigPathHash','long','scalar64-bits'),
 ('meshPathHash','long','scalar64-bits'),('navMeshEntityId','long','scalar64-bits'),
 ('obbCenter','UnityEngine.Vector3','unity-vector3-raw12'),('obbRotation','UnityEngine.Quaternion','unity-quaternion-raw16'),
 ('obbSize','UnityEngine.Vector3','unity-vector3-raw12'),('parentId','ulong','scalar64-bits'),
 ('pivot','UnityEngine.Vector3','unity-vector3-raw12'),('points',vectors.LIST,'vector3-list'),
 ('waterItemType','string','byte-payload'),('waterNameLangKey',language.TYPE,'lang-key'),
 ('waterStartAudio','string','byte-payload'),('waterStopAudio','string','byte-payload'))


def operation(kind):
 return {'lang-key':language.CAP,'vector3-list':vectors.CAP,'byte-payload':'byte-payload'}.get(kind)


def bind_program(source,program,pending):
 if (pending or source.get('wrappedType')!=TYPE or not isinstance(program,dict)
   or[(r.get('fieldName'),r.get('declaredType'))for r in source.get('orderedSourceReads',[])]!=[(n,t)for n,t,k in PLAN]
   or type(program.get('memberCount'))is not int or program['memberCount']!=len(PLAN)
   or any(type(r.get('memberIndex'))is not int for r in program.get('reads',[]))
   or[(r.get('memberIndex'),r.get('fieldName'),r.get('kind'),r.get('childCapability'))for r in program.get('reads',[])]!=[
    (i,n,k,operation(k))for i,(n,t,k)in enumerate(PLAN)]
   or program.get('requiredCapabilities')!=sorted({operation(k)for n,t,k in PLAN if operation(k)})
   or[(r.get('fieldName'),r.get('typeName'),r.get('capability'))for r in program.get('childBindings',[])]!=[
    (n,t,operation(k))for n,t,k in PLAN if k in('vector3-list','lang-key')]):
  raise ValueError('storyWater.exact-finite-program')


def bind_vectors(pins,join,child,capability):
 cap=child.get('capabilities',{}).get(capability,{})
 if (capability!=vectors.CAP or child.get('nativeInputs')!=pins or join['typeName']!=vectors.LIST
   or(cap.get('typeName'),cap.get('elementType'),cap.get('countRange'))!=(vectors.LIST,vectors.TYPE,[-1,LIMIT])
   or any(cap.get(k)is not True for k in('nullable','positiveCountsAdmitted','actualCallbackEqualsProvedChildRequired',
    'initiallyNullListRequired','rawBitsPreserved','finiteFloatProfile'))
   or any(type(cap.get(k))is not int or cap[k]!=v for k,v in(('countLimit',LIMIT),('elementWireBytes',12),('managedElementBytes',12)))
   or join['typedRequest'].get('methodName')!='ReadPackable'or join['typedRequest'].get('methodArguments')!=[vectors.LIST]
   or(cap.get('packableReaderMethodDefinition'),cap.get('packableReaderTargetRva'))!=(join['typedRequest']['methodSpec'][0],join['sourceTargetRva'])):
  raise ValueError('storyWater.exact-vector3-list-parent')
 return dict(fieldName=join['fieldName'],typeName=vectors.LIST,capability=vectors.CAP,
  readerMethodDefinition=cap['packableReaderMethodDefinition'],sourceTargetRva=cap['packableReaderTargetRva'],
  countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True)


def bind_host_parent(pins,declaration,read,usage,collection,base):
 name=declaration.get('name');witness=collection.get('witnessComponent',{});spec=usage.get('methodSpec')
 if (name not in PARENT_FIELDS or declaration.get('typeName')!=LIST or read.get('fieldName')!=name
  or collection.get('nativeInputs')!=pins or collection.get('elementType')!=TYPE
  or collection.get('status')!='validated-bounded-reference-list-induction'or collection.get('nullable')is not True
  or collection.get('countRange')!=[-1,LIMIT]or collection.get('freshListsAdmitted')is not True
  or collection.get('elementGrammarAdmitted')is not False
  or any(collection.get(k)is not False for k in('parentFieldAdmitted','wholeOwnerAdmitted'))
  or usage.get('methodName')!='ReadPackable'or usage.get('methodArguments')!=[LIST]
  or not isinstance(spec,(list,tuple))or not spec or type(spec[0])is not int or spec[0]<0
  or witness.get('typedRequest')!=usage or witness.get('elementType')!=TYPE
  or type(read.get('sourceTarget'))is not int or read['sourceTarget']!=base+witness.get('callTargetRva',-1)):
  raise ValueError('storyWater.exact-independent-host-parent')
 return dict(ownerType='Beyond.Gameplay.LevelData',fieldName=name,typeName=LIST,capability=CAP,
  readerMethodDefinition=spec[0],sourceTargetRva=witness['callTargetRva'],countLimit=LIMIT,actualCallbackEqualsProvedChildRequired=True)


def derive(image,pins,host):
 import json
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
 from scripts.game_data.memorypack import generated_reader_sources,pooled_source_helper,scalar_param_native as scalar
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 from scripts.game_data.memorypack.reference_list_induction_sources import derive as reference_list
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 need=lambda k,e,a:scalar.need('storyWater',k,e,a)
 _publication_gate(image,pins);need('same-current-host',pins,host['nativeInputs']);base=image.pe.image_base
 wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
 source=generated_reader_sources.derive(image,pins,wrapper.name)
 need('exact-ordered-fields',[(n,t)for n,t,k in PLAN],[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 typed={};children={};values={};child_proofs={};caps={}
 for read in source['orderedSourceReads']:
  field=read['fieldName'];index=read['memberIndex'];kind=PLAN[index][2]
  if kind not in('vector3-list','lang-key'):continue
  usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='storyWater.actualChild')
  typed[index]=usage;target=base+read['sourceTargetRva']
  if kind=='vector3-list':
   proof=vectors.derive(image,pins,typed_request=usage,call_target=target);cap=proof['capability']
   children[index]=dict(nativeInputs=pins,capabilities={vectors.CAP:cap});caps[vectors.CAP]=cap
  else:
   proof=language.derive(image,pins,typed_request=usage,source_target=target)
   values[index]=proof;caps[language.CAP]=proof['capabilities'][language.CAP]
  child_proofs[field]=proof
 program,pending=compile_member_program(source,pins,wrapper_name=wrapper.name,type_name=TYPE,value4={},typed_requests=typed,
  collections={vectors.LIST:(vectors.CAP,'vector3-list',vectors.CAP)},collection_children=children,collection_binder=bind_vectors,
  typed_values={language.TYPE:(language.CAP,'lang-key',language.CAP)},value_children=values,value_binder=language.bind_value)
 bind_program(source,program,pending)
 pair=derive_pair(image,TYPE);adapter=derive_adapter(image,pins,pair,wrapper)
 need('same-owned-GetValue',source['lifecycle']['GetValue']['method'],adapter['getterMethod'])
 need('same-owned-concrete-slot5',source['lifecycle']['concreteFormatter']['method'][0],pair['composition']['interfaces'][0]['formatterDeserializeMethodIndex'])
 need('full-owned-original-reference',True,source['lifecycle']['GetValue']['program'].get('fullReferenceOutput'))
 pools={read['fieldName']:pooled_source_helper.validate_on_image(image,base+read['sourceTargetRva'],pins)
  for read in source['orderedSourceReads']if read['kind']=='byte-payload'}
 ctx=NativeReferenceContext(image);enum_type=PLAN[2][1];need('nominal-TweenEase-parent','System.Enum',ctx.parent(enum_type))
 field=ctx.field(enum_type+'::value__');need('nominal-TweenEase32',True,field[1]in('int','uint'))
 enum=dict(typeName=enum_type,backing=field[1],field=list(field))
 parents={}
 for name in PARENT_FIELDS:
  declaration,read=next((f,r)for f,r in zip(host['fields'],host['program']['orderedReads'],strict=True)if f['name']==name)
  usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='storyWater.hostParent:'+name)
  collection=reference_list(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=TYPE,count_limit=LIMIT)
  binding=bind_host_parent(pins,declaration,read,usage,collection,base)
  parents[name]=dict(declaration=declaration,source=read,typedRequest=usage,collection=collection,binding=binding)
 binding=parents['waterVolumes']['binding']
 cap=dict(typeName=TYPE,memberCount=len(PLAN),program=program,enumBacking=enum,childCapabilities=caps,parentBinding=binding,
  nullAdmitted=True,positiveAdmitted=True,profileAdmitted=True,wholeGrammarAdmitted=False,finiteFloatProfile=True,
  ordinaryAdapterAdmitted=True,actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
  additionalParentBindings={'riftVolumes':parents['riftVolumes']['binding']})
 from scripts.game_data.codecs.leveldata.current_water import validate
 validate(cap);_publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema='endfield.story-water-volume-components.v2',status='validated-finite-current-water-profile',
  nativeInputs=pins,capability=cap,source=source,pair=pair,adapter=adapter,pooled=pools,children=child_proofs,
  parent=parents['waterVolumes'],additionalParents={'riftVolumes':parents['riftVolumes']},
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(exact='Complete current WaterVolume26 generated source/lifecycle/ordinary adapter/GetValue, finite primitive/vector/quaternion transfers, dedicated two-reference LangKey and exact Vector3 list/count/callback; waterVolumes and riftVolumes have independently current actual LevelData typed requests, E8 targets and list-source joins to this same nominal record.',
   conditional=__doc__,unresolved=['runtime provider/formatter selection','enclosing whole owner/physical EOF']))))
