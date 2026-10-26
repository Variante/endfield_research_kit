"""Finite primitive Param children for current condition record composition.

The concrete four-field wrapper, whole-reference GetValue, exact closed
reference carrier, eager adapter pair and reference ReadValue source are each
proved freshly. A Param spelling alone supplies none of them. The outer
constructed-reference request/store/frame and recursive owner stay separate.
"""
import json

LABEL='storyConditionParam'
SCHEMA='endfield.story-condition-param-sources.v1'
PREFIX='Beyond.Gameplay.Actions.Param`1<'
CAP_PREFIX='story-condition-param:'
PRIMITIVES={
 'bool':('bool','bool-byte',1),'int':('int','i32',4),'string':('string','pool',4),
 'float':('float','single-raw4',4),'uint':('uint','u32',4),'ulong':('ulong','u64',8),
 'UnityEngine.Vector2':('vector2','vector2-raw8',8),
 'UnityEngine.Vector3':('vector3','vector3-raw12',12),
}


def need(key,condition):
 if not condition:raise ValueError(LABEL+'.'+key)


def _reader(image,pins):
 from scripts.game_data.contracts import CONTRACTS_DIR
 from scripts.game_data.il2cpp.formatter_composition import validate_generic_contexts
 from scripts.game_data.il2cpp.generic_entries import GenericEntries
 from scripts.game_data.memorypack import modelview_reference_sources,pointer_param as pointer
 from scripts.game_data.memorypack.packable_reference_sources import validate_packable_context
 from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
 fact=json.loads((CONTRACTS_DIR/'npc_runtime_native.json').read_bytes())['readValue']
 dependency=json.loads((CONTRACTS_DIR/'leveldata_npc_patrol_native.json').read_bytes())
 routes=dependency['declarations']['adapters']['referenceRoutes']
 need('same-reviewed-reader-build',fact['nativeInputs']==dependency['nativeInputs']==pins)
 base=image.pe.image_base;body=pointer.owned(image,base+fact['entryRva'])
 need('complete-owned-reference-reader',body['windows']==fact['ownedWindows'])
 validate_generic_contexts(image,fact['contexts'],label=LABEL+'.ReadValue')
 def fail(key,expected,actual):raise ValueError(LABEL+'.'+key+':expected='+str(expected)[:300]+':actual='+str(actual)[:300])
 entries=GenericEntries(image)
 value=validate_read_value_context(image,fact['contexts'][1],fact['contexts'][2],entries,fail=fail)
 packable=validate_packable_context(image,fact['contexts'][0],value['readerMethodDefinition'],entries,fail=fail)
 program=modelview_reference_sources.read_value(body['regions'],body['pointer'],{k:base+v for k,v in routes['symbolRvas'].items()})
 return dict(readerMethodDefinition=value['readerMethodDefinition'],sourceTargetRva=fact['entryRva'],
  valueContext=value,packableContext=packable,program=program,windows=body['windows'],
  sourceRegions=[(a,b.hex().upper())for a,b in body['regions']],pointerEquivalenceClaimed=False)


def _reference_join(image,pins,value_type,*,forwarder_prover=None):
 """Fresh carrier/getter/adapter only; this supplies no constant grammar."""
 need('callable-Param-forwarder-prover',forwarder_prover is None or callable(forwarder_prover))
 from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_extent
 from scripts.game_data.memorypack import pointer_param as pointer
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 type_name=PREFIX+value_type+'>'
 wrappers=[w for w in derive_from_image(image).values()if w.wrapped_type==type_name]
 need('one-exact-Param-wrapper',len(wrappers)==1);wrapper=wrappers[0];ctx=NativeReferenceContext(image)
 getter=pointer.methods(image,wrapper)['GetValue'];carrier=closed_generic_reference_extent(ctx,getter.return_type)
 need('same-closed-reference-Param-carrier',carrier['type']==type_name and carrier['argumentTypes']==[value_type]
  and carrier['definitionTypeIndex']==ctx.index.types[PREFIX[:-1]].index)
 pair=derive_pair(image,type_name,wrapper.name)
 adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=forwarder_prover)
 getter_source=pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3'])
 return dict(getterMethodDefinition=getter.index,closedCarrier=carrier,adapter=adapter,getter=getter_source)


def _capability(value_type,wire,width,reader,adapter):
 return dict(typeName=PREFIX+value_type+'>',valueType=value_type,memberCount=4,
  fieldOrder=['constValue','idRef','paramSource','path'],constantWireKind=wire,constantWireBytes=width,
  idRefWireKind='i32',paramSourceWireKind='i32',pathEncoding='int32-pool-index',
  positiveWireBytes=1+width+4+4+4,nullWireBytes=1,nullOutput='reference-null',
  nullAdmitted=True,positiveAdmitted=True,wholeGrammarAdmitted=True,
  sourceReferenceKind=21,referenceOutputBytes=8,closedCarrierProved=True,
  readerMethodDefinition=reader['readerMethodDefinition'],sourceTargetRva=reader['sourceTargetRva'],
  actualCallbackEqualsProvedChildRequired=True,liveFormatterSelectionObserved=False,
  canonicalCallbackTargetRva=adapter['callbackBinding']['canonicalTargetRva'])


def _derive_primitive(image,pins,value_type,reader):
 from scripts.game_data.memorypack import primitive_param
 from scripts.game_data.codecs.levelscript.current_condition_param import validate
 need('finite-primitive-domain',value_type in PRIMITIVES)
 primitive,wire,width=PRIMITIVES[value_type];type_name=PREFIX+value_type+'>'
 source=primitive_param.derive_parameter(image,pins,primitive)
 reference=_reference_join(image,pins,value_type)
 need('same-owned-whole-reference-getter',source['parameter']['methods']['GetValue']['methodIndex']==reference['getterMethodDefinition'])
 capability=_capability(value_type,wire,width,reader,reference['adapter'])
 validate(capability)
 return dict(typeName=type_name,valueType=value_type,capability=capability,
  proof=dict(wrapperSource=source,**{k:v for k,v in reference.items()if k!='getterMethodDefinition'}),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def derive_many(image,pins,value_types):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 need('literal-distinct-finite-request',isinstance(value_types,(list,tuple))and 1<=len(value_types)<=len(PRIMITIVES)
  and all(type(n)is str and n in PRIMITIVES for n in value_types)and len(set(value_types))==len(value_types))
 _publication_gate(image,pins);reader=_reader(image,pins);owners=[];capabilities={}
 for value in value_types:
  try:
   child=_derive_primitive(image,pins,value,reader);capabilities[CAP_PREFIX+child['typeName']]=child['capability']
   owners.append(dict(status='validated-conditional-Param-child',**child))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   owners.append(dict(status='pendingReview',typeName=PREFIX+value+'>',valueType=value,reason=str(error)[:1800],
    diagnostic=dict(validator=LABEL,errorType=type(error).__name__,failedGate=str(error).split(':',1)[0],
     expected='exact concrete Param source, closed reference carrier, whole-reference getter and canonical adapter',actual=str(error)[:1200]),
    parentFieldAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,referenceReader=reader,owners=owners,
  capabilities=capabilities,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
