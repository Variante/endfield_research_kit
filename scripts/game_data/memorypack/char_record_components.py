"""Finite Char concrete record composition below union and container owners.

Complete selected source/lifecycle, per-field child proofs and the independent
ordinary adapter are separate gates. Unknown children emit no partial record
capability. No route, containing collection, runtime playback or public owner
is selected here.
"""
import json

SCHEMA='endfield.char-interact-record-components.v1'
CAP_PREFIX='char-interact-record:'
WIRE='char-interact-record'
PLANS={
    'Beyond.Gameplay.Core.CharInteractPerform.AddMultiTagsActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.AudioEventActData':20,
    'Beyond.Gameplay.Core.CharInteractPerform.BodyTypeActData':1,
    'Beyond.Gameplay.Core.CharInteractPerform.CameraAddControlStateActData':20,
    'Beyond.Gameplay.Core.CharInteractPerform.CameraBlendInActData':20,
    'Beyond.Gameplay.Core.CharInteractPerform.CameraBlendOutActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.CameraRemoveControlStateActData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.CharAnimActionData':31,
    'Beyond.Gameplay.Core.CharInteractPerform.CharCancelWetSquadActionData':15,
    'Beyond.Gameplay.Core.CharInteractPerform.CharFocusOnActionData':22,
    'Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformActor':13,
    'Beyond.Gameplay.Core.CharInteractPerform.CharJumpActionData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.CharLimbIKActionData':20,
    'Beyond.Gameplay.Core.CharInteractPerform.CharMeshGroupShowActData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.CharMoveToActionData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.CharNpcMontageActionData':25,
    'Beyond.Gameplay.Core.CharInteractPerform.CharRotateToActionData':23,
    'Beyond.Gameplay.Core.CharInteractPerform.CharSkMorphActionData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.CharSnapToActionData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.CharSnapToTmpObjectMountPointActData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.CharStopLimbIKActionData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.CharWeaponShowActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.CharWetSquadActionData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.DecoAnimActData':17,
    'Beyond.Gameplay.Core.CharInteractPerform.EffectPlayActData':26,
    'Beyond.Gameplay.Core.CharInteractPerform.EntityHideEffectSourceTagActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.EntityShowEffectSourceTagActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.GlobalHideEffectSourceTagActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.GlobalShowEffectSourceTagActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.HideCharPotentialEffectActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.HorseAnimDriverActData':30,
    'Beyond.Gameplay.Core.CharInteractPerform.HorsePelvisSnapActData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.InteractiveActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.LoopSubSpecialPerformEntry':3,
    'Beyond.Gameplay.Core.CharInteractPerform.LoopTimeCondition':2,
    'Beyond.Gameplay.Core.CharInteractPerform.NpcAIEventActionData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.NpcMontageActionData':19,
    'Beyond.Gameplay.Core.CharInteractPerform.NpcStopCurMontageActionData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.ObjectAnimActData':18,
    'Beyond.Gameplay.Core.CharInteractPerform.ObjectDetachAttachActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.ObjectShowActData':26,
    'Beyond.Gameplay.Core.CharInteractPerform.RemoveTagsByIdActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.SetWeakInterruptTypeActData':17,
    'Beyond.Gameplay.Core.CharInteractPerform.ShowMainUIActData':16,
    'Beyond.Gameplay.Core.CharInteractPerform.SubSpecialPerformEntryData':1,
    'Beyond.Gameplay.Core.CharInteractPerform.TeleportCharActionData':17,
    'Beyond.Gameplay.Core.CharInteractPerform.TempObjectAnimatorDriverBlackboardActData':16,
    'Beyond.NPC.Ability.NPCMontageBasicDesc':5,
}
VALUE_OPERATIONS={
 'Beyond.Gameplay.BodyTypeDef':('body-type-def-value','body-type-def-value','body-type-def-value'),
 'Beyond.Gameplay.View.Animation.AlphaBlend':('skill-alpha-blend','alpha-blend-value','skill-alpha-blend'),
 'Beyond.FAnimationCurve':('beyond-curve-value','beyond-curve-value','beyond-curve-value'),
}


def need(key,condition,detail=None):
 if not condition:raise ValueError('charRecordComponents.'+key+(':'+str(detail)[:1200]if detail is not None else''))


def key(type_name):
 need('finite-owned-record-type',type_name in PLANS)
 return CAP_PREFIX+type_name


def _merge(caps,requirements,component,pins):
 need('same-independent-child-native-inputs',component.get('nativeInputs')==pins)
 incoming=component.get('capabilities',{});external=component.get('requiredExternalCapabilities',[])
 need('literal-whole-child-capability-map',isinstance(incoming,dict)and all(type(n)is str and n and isinstance(c,dict)for n,c in incoming.items())
  and isinstance(external,(list,tuple))and all(type(n)is str and n for n in external))
 for name,cap in incoming.items():need('exact-shared-child-capability:'+name,name not in caps or caps[name]==cap)
 caps.update(incoming);requirements.update(external)


def _value_binder(source,scope,read,pins,usage,component,capability):
 from scripts.game_data.memorypack.animation_record_components import bind_value
 return bind_value(source,scope,read,pins,usage,component,capability)


def _requests(source,provided):
 scope=source['sourceScope'];requests=dict(provided or{})
 for read in source['orderedSourceReads']:
  i=read['memberIndex'];name=read['declaredType'];context=read.get('context')
  if i in requests:continue
  if read['kind'].startswith('managed:')and name in VALUE_OPERATIONS:
   actual=scope.get('managedValueSources',{}).get(str(i),{});requests[i]=actual.get('proof',{}).get('typedRequest',{})
  elif isinstance(context,dict):
   requests[i]=dict(instructionRva=context['instructionRva'],instructionHex=context['instructionHex'],
    methodSpec=context['methodSpec'],tag=6,typeName=context['methodOwner'],methodName=context['methodName'],
    classArguments=[],methodArguments=[context['fullTypeName']])
 return requests


def compose(source,pins,*,value_children=None,typed_requests=None,value4=None,
        reference_operations=None,reference_children=None,reference_binder=None,
        collection_operations=None,collection_children=None,collection_binder=None):
 from scripts.game_data.memorypack.generated_record_components import compile_member_program
 name=source.get('wrappedType');capability=key(name);count=PLANS[name];scope=source.get('sourceScope',{});reads=source.get('orderedSourceReads',[])
 need('complete-selected-current-record',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
  and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True
  and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False
  and len(reads)==scope.get('memberCount')==count)
 values=dict(value_children or{});refs=dict(reference_children or{});lists=dict(collection_children or{})
 reference_operations=dict(reference_operations or{});collection_operations=dict(collection_operations or{})
 need('per-member-independent-children',all(type(i)is int and 0<=i<count for group in(values,refs,lists)for i in group)
  and not(set(values)&set(refs)or set(values)&set(lists)or set(refs)&set(lists)))
 need('callable-domain-parent-join',reference_binder is None or callable(reference_binder))
 need('callable-domain-list-parent-join',collection_binder is None or callable(collection_binder))
 requests=_requests(source,typed_requests);value4=dict(value4 or{});value8={};operations={};selected_values={};grouped_refs={};missing4=[]
 for read in reads:
  i=read['memberIndex'];declared=read['declaredType'];kind=read['kind']
  if i in values:
   need('finite-exact-managed-value-selection',kind=='managed:'+declared and declared in VALUE_OPERATIONS)
   operations[declared]=VALUE_OPERATIONS[declared];selected_values[i]=values[i]
  if kind.startswith('value4:'):
   proof=scope.get('primitiveSources',{}).get(str(i),value4.get(declared))
   if proof is None:missing4.append(dict(memberIndex=i,fieldName=read['fieldName'],typeName=declared,kind=kind,reason='independent exact named raw4 source proof required'))
   else:value4[declared]=proof
  elif kind=='value8:UnityEngine.Vector2':value8.setdefault(declared,{})[str(i)]=scope['primitiveSources'][str(i)]
  if i in refs:
   need('explicit-reference-domain-operation',declared in reference_operations and callable(reference_binder))
   cap_name,wire,required=reference_operations[declared]
   need('same-nominal-independent-reference-child',refs[i].get('nativeInputs')==pins
    and refs[i].get('capabilities',{}).get(cap_name,{}).get('typeName')==declared
    and all(type(x)is str and x for x in(cap_name,wire,required)))
   if declared in grouped_refs:
    need('same-nominal-full-reference-capability',grouped_refs[declared]['capabilities'][cap_name]==refs[i]['capabilities'][cap_name])
   else:grouped_refs[declared]=refs[i]
  if i in lists:
   need('explicit-list-domain-operation',declared in collection_operations and callable(collection_binder)
    and lists[i].get('nativeInputs')==pins)
 need('only-used-reference-operations',set(reference_operations)<={r['declaredType']for r in reads})
 need('only-used-list-operations',set(collection_operations)<={r['declaredType']for r in reads})
 def adapted(group,callback,selected_pins,join,component,selected_cap):
  matches=[r for r in reads if(r['fieldName'],r['declaredType'])==(join.get('fieldName'),join.get('typeName'))]
  need('unique-domain-parent-field',len(matches)==1);read,=matches;i=read['memberIndex']
  need('same-parent-join-and-child',selected_pins==pins and i in group and join.get('typedRequest')==requests.get(i)
   and join.get('sourceTargetRva')==read.get('sourceTargetRva')
   and component.get('capabilities',{}).get(selected_cap)==group[i].get('capabilities',{}).get(selected_cap))
  binding=callback(source,scope,read,pins,requests[i],group[i],selected_cap)
  need('same-complete-actual-domain-binding',isinstance(binding,dict)
   and(binding.get('fieldName'),binding.get('typeName'),binding.get('capability'))==(read['fieldName'],read['declaredType'],selected_cap)
   and type(binding.get('readerMethodDefinition'))is int and binding['readerMethodDefinition']==requests[i].get('methodSpec',[None])[0]
   and type(binding.get('sourceTargetRva'))is int and binding['sourceTargetRva']==read['sourceTargetRva'])
  return binding
 def ref_bind(selected_pins,join,component,selected_cap):return adapted(refs,reference_binder,selected_pins,join,component,selected_cap)
 def list_bind(selected_pins,join,component,selected_cap):return adapted(lists,collection_binder,selected_pins,join,component,selected_cap)
 if missing4:return dict(schema=SCHEMA,status='pendingReview',nativeInputs=pins,typeName=name,capability=capability,pending=missing4,
  wholeGrammarAdmitted=False,ordinaryOriginalAdapterAdmitted=False,containingOwnerAdmitted=False,wholeOwnerAdmitted=False)
 compiled,pending=compile_member_program(source,pins,wrapper_name=source['wrapperName'],type_name=name,
  value4=value4,value8=value8,typed_requests=requests,typed_values=operations,value_children=selected_values,value_binder=_value_binder,
  references=reference_operations,reference_children=grouped_refs,reference_binder=ref_bind if refs else None,
  collections=collection_operations,collection_children=lists,collection_binder=list_bind if lists else None)
 if pending:return dict(schema=SCHEMA,status='pendingReview',nativeInputs=pins,typeName=name,capability=capability,pending=pending,
  wholeGrammarAdmitted=False,ordinaryOriginalAdapterAdmitted=False,containingOwnerAdmitted=False,wholeOwnerAdmitted=False)
 need('complete-exact-ordered-record',compiled['memberCount']==count and len(compiled['reads'])==count
  and [(r['memberIndex'],r['fieldName'])for r in compiled['reads']]==[(r['memberIndex'],r['fieldName'])for r in reads])
 cap=dict(typeName=name,wrapperName=source['wrapperName'],memberCount=count,orderedReads=compiled['reads'],nullable=True,nullMarker=255,
  wholeGrammarAdmitted=True,directWrapperGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=False,
  actualContainingRouteAdmitted=False,wholeOwnerAdmitted=False)
 caps={capability:cap};required=set(compiled['requiredCapabilities'])
 for component in list(values.values())+list(refs.values())+list(lists.values()):_merge(caps,required,component,pins)
 return dict(schema=SCHEMA,status='compiled-conditional-direct-wrapper-char-record',nativeInputs=pins,typeName=name,capability=capability,
  capabilities=caps,compiled=compiled,pending=[],requiredExternalCapabilities=sorted(required-set(caps)),
  ordinaryOriginalAdapterAdmitted=False,containingOwnerAdmitted=False,wholeOwnerAdmitted=False)


def _attribute(image,pins,source):
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 name=source.get('wrappedType');need('finite-retained-current-source',name in PLANS and source.get('nativeInputs')==pins
  and source.get('completeSelectedCallerAdmitted')is True and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
 wrappers=[w for w in derive_from_image(image).values()if w.wrapped_type==name and w.name==source.get('wrapperName')]
 need('one-current-nominal-wrapper',len(wrappers)==1);wrapper,=wrappers;method=source.get('method',[]);md=image.metadata
 need('literal-current-reader-identity',len(method)==4 and type(method[0])is int and 0<=method[0]<len(md.methods))
 actual=md.methods[method[0]]
 need('same-actual-reader-and-member-order',image.type_name(actual.declaring_type)==wrapper.name and md.string(actual.name_index)=='Deserialize'
  and actual.flags&16 and image.method_pointer_va(actual)==image.pe.image_base+method[3]and method[1:3]==[wrapper.name,'Deserialize']
  and len(wrapper.members)==PLANS[name]and[(m.name,m.declared_type)for m in wrapper.members]==[(r['fieldName'],r['declaredType'])for r in source['orderedSourceReads']])
 image.check_windows(source['codeWindows'],label='charRecordComponents.retained-source')
 return wrapper,dict(method=method,codeWindows=source['codeWindows'],freshMethodAndMemberAttribution=True,
  retainedCompleteSourceSemanticsReused=True,sourceProgramSemanticsReproved=False)


def _ordinary(image,pins,source,wrapper):
 from scripts.game_data.memorypack.reference_param_profile import derive_pair
 from scripts.game_data.memorypack.reference_object_sources import derive_adapter
 from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
 life=source['lifecycle'];owned=life.get('directHolderMode')is not True and'ownedCoherentGetter'in life['GetValue']
 pair=derive_pair(image,source['wrappedType'],wrapper.name,owned_getter_family=owned)
 adapter=derive_adapter(image,pins,pair,wrapper);reader=reference_reader_abi(image,pins)
 need('same-own-whole-reader-and-getter',adapter['getterMethod']==life['GetValue']['method']and adapter['pairForwarder']['readerMethod']==source['method'])
 face,=pair['composition']['interfaces'];definition=face['formatterDeserializeMethodIndex']
 formatter,=[m for m in pair['composition']['methods']if m[0]==definition];callback=adapter['callbackBinding']
 need('actual-own-wrapper-formatter-method',len(formatter)==4 and type(formatter[0])is int
  and image.method_pointer_va(image.metadata.methods[definition])==image.pe.image_base+formatter[3]
  and callback.get('actualCallbackEqualsCanonicalRequired')is True and callback.get('runtimeSelectionObserved')is False)
 identity=dict(ordinaryOriginalReadValueAdmitted=True,ordinaryOriginalCallbackAdmitted=True,valueStorageKind='reference8',
  ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
  callbackSelectionConditional=True,actualCallbackEqualsProvedChildRequired=True,sourceReferenceKind=18,referenceOutputBytes=8,
  originalTypeDefinition=image.named_types[source['wrappedType']].index,canonicalAdapterTargetRva=callback['canonicalTargetRva'],
  formatterDeserializeMethodDefinition=formatter[0],referenceReaderMethodDefinition=reader['referenceReaderMethodDefinition'],
  referenceReaderTargetRva=reader['referenceReaderTargetRva'])
 return identity,dict(pair=json.loads(json.dumps(pair)),adapter=adapter,referenceReaders=reader)


def validate_component(component,pins):
 need('whole-ordinary-Char-component',component.get('schema')==SCHEMA and component.get('status')=='validated-conditional-char-interact-record-components'
  and component.get('nativeInputs')==pins and component.get('pending')==[]and component.get('ordinaryOriginalAdapterAdmitted')is True
  and component.get('containingOwnerAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
 name=component.get('typeName');capability=key(name);caps=component.get('capabilities',{});cap=caps.get(capability,{})
 from scripts.game_data.memorypack.char_record_codec import require_capability
 require_capability(cap,ordinary=True)
 need('same-primary-record-program',component.get('capability')==capability and cap.get('orderedReads')==component.get('compiled',{}).get('reads')
  and component['compiled'].get('memberCount')==PLANS[name])
 proof=component.get('proof',{});source=proof.get('source',{});adapter=proof.get('adapter',{});refs=proof.get('referenceReaders',{})
 pair=proof.get('pair',{});registration=pair.get('registration',{});raw=bytes.fromhex(registration.get('key',{}).get('typeRawHex',''))
 checks=dict(
  source=source.get('nativeInputs')==pins and source.get('wrappedType')==name and source.get('wrapperName')==cap.get('wrapperName')and source.get('completeSelectedCallerAdmitted')is True,
  adapter=adapter.get('schema')=='endfield.reference-object-adapter-source.v1'and adapter.get('nativeInputs')==pins and adapter.get('typeName')==name and adapter.get('wrapperName')==cap['wrapperName'],
  pair=adapter.get('pair')==pair and registration.get('originalType')==name and registration.get('wrapperType')==cap['wrapperName'],
  nominalKey=len(raw)==16 and raw[10:12]==bytes((18,0))and int.from_bytes(raw[:8],'little')==cap['originalTypeDefinition'],
  getter=adapter.get('getterMethod')==source.get('lifecycle',{}).get('GetValue',{}).get('method'),
  reader=adapter.get('pairForwarder',{}).get('readerMethod')==source.get('method'),
  originalCallback=adapter.get('callbackBinding',{}).get('canonicalTargetRva')==cap['canonicalAdapterTargetRva'],
  wrapperCallback=len(pair.get('composition',{}).get('interfaces',[]))==1
   and pair['composition']['interfaces'][0].get('formatterDeserializeMethodIndex')==cap['formatterDeserializeMethodDefinition']
   and any(m[0]==cap['formatterDeserializeMethodDefinition']for m in pair['composition'].get('methods',[])if isinstance(m,list)and len(m)==4),
  referenceReader=(refs.get('referenceReaderMethodDefinition'),refs.get('referenceReaderTargetRva'))==(cap['referenceReaderMethodDefinition'],cap['referenceReaderTargetRva']))
 need('same-exact-original-reader-callback',all(checks.values()),checks)
 required=component.get('requiredExternalCapabilities',[])
 need('complete-external-capability-domain',isinstance(required,list)and required==sorted(set(required))and not set(required)&set(caps)
  and set(component['compiled'].get('requiredCapabilities',[]))<=set(caps)|set(required))
 need('same-complete-source-field-order',[(r.get('memberIndex'),r.get('fieldName'))for r in cap['orderedReads']]==
  [(r.get('memberIndex'),r.get('fieldName'))for r in source.get('orderedSourceReads',[])])
 expected={capability:cap};needed=set(component['compiled'].get('requiredCapabilities',[]))
 child_groups=proof.get('children',{})
 need('explicit-strong-child-groups',isinstance(child_groups,dict)and set(child_groups)<=
  {'value_children','reference_children','collection_children'})
 for group in child_groups.values():
  need('per-member-child-proof-map',isinstance(group,dict))
  for child in group.values():_merge(expected,needed,child,pins)
 need('all-and-only-complete-descendant-capabilities',caps==expected and required==sorted(needed-set(expected)))
 return dict(capability=capability,capabilities=caps,requiredExternalCapabilities=required)


def derive_selected(image,pins,*,sources,children=None):
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 need('finite-distinct-source-selection',isinstance(sources,dict)and bool(sources)and set(sources)<=set(PLANS)
  and set(children or{})<=set(sources))
 _publication_gate(image,pins);owners=[];caps={};required=set()
 for name,source in sources.items():
  try:
   wrapper,attribution=_attribute(image,pins,source);need('same-explicit-record-selection',source['wrappedType']==name)
   requests={}
   for read in source['orderedSourceReads']:
    context=read.get('context')
    if isinstance(context,dict):requests[read['memberIndex']]=derive_typed_usage_context(image,context['instructionRva'],label='charRecordComponents.actual')
   kwargs=dict((children or{}).get(name,{}));need('native-owner-owns-fresh-typed-requests','typed_requests'not in kwargs)
   named4={}
   for read in source['orderedSourceReads']:
    if read['kind'].startswith('value4:')and str(read['memberIndex'])not in source['sourceScope'].get('primitiveSources',{}):
     if read['declaredType']=='Beyond.Gameplay.Core.GameplayTag':
      from scripts.game_data.memorypack.buff_gameplay_tag_native import validate_on_image
     elif read['declaredType']=='UnityEngine.LayerMask':
      from scripts.game_data.memorypack.buff_layer_mask_native import validate_on_image
     else:continue
     named4[read['declaredType']]=validate_on_image(image,pins)
   need('native-owner-owns-fresh-named4-sources','value4'not in kwargs)
   record=compose(source,pins,typed_requests=requests,value4=named4,**kwargs)
   if record['pending']:owners.append(dict(typeName=name,status='pendingReview',proof=record));continue
   identity,ordinary=_ordinary(image,pins,source,wrapper)
   record['capabilities'][record['capability']]=dict(record['capabilities'][record['capability']],**identity)
   record.update(status='validated-conditional-char-interact-record-components',ordinaryOriginalAdapterAdmitted=True,
    proof=dict(source=source,sourceAttribution=attribution,children={k:v for k,v in kwargs.items()if k.endswith('_children')},**ordinary))
   validate_component(record,pins);_merge(caps,required,record,pins)
   owners.append(dict(typeName=name,status=record['status'],proof=record))
  except(ValueError,KeyError,IndexError,TypeError)as error:
   owners.append(dict(typeName=name,status='pendingReview',reason=str(error)[:1800],diagnostic=dict(validator='charRecordComponents',errorType=type(error).__name__),
    wholeGrammarAdmitted=False,containingOwnerAdmitted=False,wholeOwnerAdmitted=False))
 _publication_gate(image,pins)
 return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,owners=owners,capabilities=caps,
  requiredExternalCapabilities=sorted(required-set(caps)),containingOwnerAdmitted=False,wholeOwnerAdmitted=False)))


def derive_sources(image,pins,type_names=None,*,stage=None):
 """Fresh complete source map for the finite current Char record inventory.

 No retained report supplies admission. Any source hold aborts the result;
 callers can receive bounded per-owner progress through a callable stage.
 """
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.memorypack.wrapper_members import derive_from_image
 from scripts.game_data.memorypack.generated_reader_sources import derive
 selected=list(PLANS if type_names is None else type_names)
 need('finite-fresh-source-selection',bool(selected)and len(selected)==len(set(selected))and set(selected)<=set(PLANS)
  and(stage is None or callable(stage)))
 _publication_gate(image,pins);inventory=list(derive_from_image(image).values());sources={}
 for index,name in enumerate(selected):
  wrappers=[w for w in inventory if w.wrapped_type==name]
  need('one-current-source-wrapper:'+name,len(wrappers)==1 and len(wrappers[0].members)==PLANS[name])
  if stage is not None:stage(dict(stage='char-record-source',index=index,total=len(selected),typeName=name))
  try:
   source=derive(image,pins,wrappers[0].name);_attribute(image,pins,source)
   need('same-fresh-explicit-source-owner',source['wrappedType']==name)
  except(ValueError,KeyError,IndexError,TypeError)as error:
   raise ValueError('charRecordComponents.source-held:'+name+':'+str(error)[:1400])from error
  sources[name]=source
 _publication_gate(image,pins)
 if stage is not None:stage(dict(stage='char-record-source-complete',index=len(selected),total=len(selected)))
 return sources
