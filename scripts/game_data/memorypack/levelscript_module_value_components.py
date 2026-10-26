"""Finite Module value/collection grammar joined to independent source owners.

Pure composition checks nominal source relationships. Native derive must still
freshly obtain every input on its one selected image. No enclosing Module,
root dictionary or physical EOF authority follows from these child profiles.
"""
import json

from scripts.game_data.memorypack import levelscript_module_value_transfer_programs as values

SCHEMA='endfield.story-module-value-components.v1'
VALUE_SCHEMA='endfield.story-module-value-capability.v1'
LIST_SCHEMA='endfield.story-module-value-list-capability.v1'
ARRAY_SCHEMA='endfield.story-module-opera-array-capability.v1'
PARAM_SCHEMA='endfield.story-module-param-array-capability.v1'
VALUE_CAPS={values.EFFECT:'story-module-effect-info',values.AIRWALL:'story-module-air-wall-ptr',values.OPERA:'story-module-opera-segment'}
LIST_CAPS={name:key+'-list'for name,key in VALUE_CAPS.items()if name!=values.OPERA}
OPERA_ARRAY='story-module-opera-segment-array'
PARAM_ARRAY='story-module-param-key-value-array'
PKV='Beyond.Gameplay.ParamKeyValue'
VALUE_ORDER={values.EFFECT:[['delayToHide','float'],['effectKey','string'],['eulerAngles','UnityEngine.Vector3'],['position','UnityEngine.Vector3'],['scale','UnityEngine.Vector3']],
 values.AIRWALL:[['logicId','ulong'],['slotId','uint'],['useSlotId','bool']],values.OPERA:[['operaType','Beyond.Gameplay.EncounterData+OperaType'],['parameters',PKV+'[]']]}
LAYOUTS={values.EFFECT:([['effectKey','string',16],['delayToHide','float',24],['position','UnityEngine.Vector3',28],['eulerAngles','UnityEngine.Vector3',40],['scale','UnityEngine.Vector3',52]],[0],[]),
 values.AIRWALL:([['useSlotId','bool',16],['logicId','ulong',24],['slotId','uint',32]],[],[[1,8],[20,24]]),
 values.OPERA:([['operaType','Beyond.Gameplay.EncounterData+OperaType',16],['parameters',PKV+'[]',24]],[8],[[4,8]])}


def need(key,condition):
 if not condition:raise ValueError('storyModuleValues.'+key)


def verify_value_programs(source):
 """Replay full owned windows and selected canonical/wrapper programs."""
 from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
 from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
 from scripts.game_data.memorypack import levelscript_module_value_wrapper_sources as inline
 from scripts.game_data.memorypack import levelscript_opera_value_sources as opera
 name=source['typeName'];p=source['proof'];base=p['registrations']['adapter']['pointer']-source['canonicalCallbackTargetRva']
 need('same-owned-selected-image-base',type(base)is int and base>=2**32)
 raw={role:regions(p['sourceWindows'][role],[[at-base,h]for at,h in rows],base,'Module-value-'+role)
  for role,rows in p['sourceRegions'].items()}
 symbols={k:base+v for k,v in p['symbolRvas'].items()};programs=p['programs'];norm=lambda v:json.loads(json.dumps(v))
 adapter=p['registrations']['adapter']['pointer'];nonnull=p['registrations']['nonnull']['pointer']
 parsed=dict(adapter=[values.adapter_program(raw['adapter'],adapter,type_name=name,symbols=symbols,**mode)
  for mode in({},dict(create=False),dict(null=True))],
  nonnull=[values.nonnull_program(raw['nonnull'],nonnull,type_name=name,symbols=symbols,wrapper_null=n)for n in(False,True)],
  conversion=values.conversion_program(raw['conversion'],symbols['conversion'],type_name=name,prepare=symbols['prepare'],ordinal=p['interfaceOrdinal']),
  readNull=[values.null_program(raw['readNull'],symbols['readNull'],symbols=symbols,null=n,near=name==values.AIRWALL)for n in(False,True)])
 need('all-owned-canonical-programs',norm(parsed)==programs and symbols['nonnull']==nonnull)
 face,=p['pair']['composition']['interfaces']
 callback,=[m for m in p['pair']['composition']['methods']if m[0]==face['formatterDeserializeMethodIndex']]
 invocation=deserialize_slot(raw['wrapperInvoke'],symbols['wrapperInvoke'],prepare=symbols['prepare'],callback=base+callback[3])
 need('same-owned-wrapper-slot-five-ABI',norm(invocation)==p['wrapperInvocation'])
 record=source['record'];own=regions(record['sourceWindows'],[[at-base,h]for at,h in record['sourceRegions']],base,'Module-value-wrapper')
 rs={k:base+v for k,v in record['symbolRvas'].items()};entry=base+record['readerMethod'][3]
 fn=opera.record_program if name==values.OPERA else inline.reader_program;arguments={}if name==values.OPERA else dict(type_name=name)
 paths=[fn(own,entry,symbols=rs,new=n,ff=f,**arguments)for n,f in((True,False),(False,False),(True,True),(False,True))]
 need('all-four-owned-wrapper-programs',norm(paths)==record['programs'])
 if name!=values.OPERA:
  frames=[inline.frame_program(own,entry,type_name=name,symbols=rs,new=n,ff=f)for n,f in((True,False),(False,False),(True,True),(False,True))]
  need('all-owned-value-wrapper-frames',norm(frames)==record['frames'])
 for role,leaf in record['leaves'].items():
  code=regions([leaf['window']],[[at-base,h]for at,h in leaf['sourceRegions']],base,'Module-value-'+role)
  result=(opera.value_leaf_program(code,base+leaf['method'][3],getter=role=='GetValue')if name==values.OPERA else
   inline.value_leaf_program(code,base+leaf['method'][3],type_name=name,mode='getter'if role=='GetValue'else'default'))
  need('same-owned-whole-value-leaf:'+role,norm(result)==leaf['program'])
 return base


def value_capability(source,pins,*,parameters=None):
 name=source.get('typeName');need('finite-selected-canonical-source',name in VALUE_CAPS
  and source.get('schema')=='endfield.story-module-value-transfer.v1'and source.get('status')=='validated-conditional-module-value-transfer'
  and source.get('nativeInputs')==pins and source.get('managedBytes')==values.WIDTHS[name]
  and type(source.get('canonicalCallbackTargetRva'))is int and source['canonicalCallbackTargetRva']>0
  and all(source.get(k)is True for k in('canonicalCallbackAdmitted','wrapperSourceAdmitted','actualCallbackEqualsCanonicalRequired'))
  and all(source.get(k)is False for k in('liveFormatterSelectionObserved','elementGrammarAdmitted','parentFieldAdmitted','containerAdmitted','wholeOwnerAdmitted')))
 verify_value_programs(source)
 fields,refs,padding=LAYOUTS[name];layout=source.get('layout',{})
 need('exact-own-field-layout',layout.get('typeName')==name and layout.get('managedBytes')==values.WIDTHS[name]
  and layout.get('fields')==fields and layout.get('referenceLaneOffsets')==refs and layout.get('paddingByteRanges')==padding
  and layout.get('paddingRangesAreStartEnd')is True)
 record=source['record'];order=VALUE_ORDER[name];paths=record.get('programs',[])
 need('all-four-wrapper-source-paths',len(paths)==4 and{(p.get('newWrapper'),p.get('wrapperFF'))for p in paths}=={(n,f)for n in(False,True)for f in(False,True)}
  and all(p.get('normalReturn')is True and p.get('managedBytes')==values.WIDTHS[name]for p in paths)
  and all([[r['fieldName'],r.get('declaredType',dict((k,v)for k,v in order).get(r['fieldName']))]for r in p['orderedReads']]==order for p in paths if not p['wrapperFF']))
 proof=source['proof'];canonical=proof['programs']
 need('canonical-full-default-and-getter-copy',len(canonical['adapter'])==3 and len(canonical['nonnull'])==2
  and any(p.get('defaultZeroOutputBytes')==values.WIDTHS[name]and p.get('canonicalFF')is True for p in canonical['adapter'])
  and any(p.get('wholeGetterCopiedBytes')==values.WIDTHS[name]and p.get('wrapperNull')is False for p in canonical['nonnull'])
  and any(p.get('defaultZeroBytes')==values.WIDTHS[name]and p.get('wrapperNull')is True for p in canonical['nonnull'])
  and sum(n for _,n in canonical['conversion']['copiedSlices'])==values.WIDTHS[name]
  and canonical['conversion'].get('interfaceFallbackAdmitted')is False)
 if name==values.OPERA:
  need('separate-positive-ParamKeyValue-array-grammar',isinstance(parameters,dict)and parameters.get('schema')==PARAM_SCHEMA
   and parameters.get('capability')==PARAM_ARRAY and parameters.get('typeName')==PKV+'[]'and parameters.get('positiveCountsAdmitted')is True)
 else:need('no-unowned-parameter-child',parameters is None)
 return dict(schema=VALUE_SCHEMA,capability=VALUE_CAPS[name],typeName=name,originalTypeDefinition=layout['typeDefinition'],managedBytes=values.WIDTHS[name],memberCount=len(order),
  serializedOrder=order,canonicalFFWireBytes=1,canonicalFFDefaultManagedBytes=values.WIDTHS[name],
  referenceLaneOffsets=refs,paddingByteRanges=padding,paddingRangesAreStartEnd=True,
  canonicalCallbackTargetRva=source['canonicalCallbackTargetRva'],canonicalOriginalAdapterAdmitted=True,
  actualCallbackEqualsCanonicalRequired=True,profileAdmitted=True,rawIeeeBitsPreserved=True,
  positiveWireBytes=14 if name==values.AIRWALL else 45 if name==values.EFFECT else None,
  booleanNormalization='any-nonzero-byte-to-one'if name==values.AIRWALL else None,
  parametersCapability=parameters,liveFormatterSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def list_capability(source,value,pins):
 name=source.get('elementType')
 need('exact-fresh-list-source',name in LIST_CAPS and source.get('schema')=='endfield.story-module-value-list-source.v1'
  and source.get('status')=='validated-conditional-module-value-list-source'and source.get('nativeInputs')==pins
  and source.get('typeName')=='System.Collections.Generic.List`1<'+name+'>'
  and(source.get('countLimit'),source.get('countRange'),source.get('headerBytes'),source.get('managedElementBytes'),source.get('elementWireBytes'))==
   (4096,[-1,4096],4,values.WIDTHS[name],None)
  and all(source.get(k)is True for k in('initiallyNullListRequired','actualCallbackEqualsCanonicalRequired','positiveCountsAdmitted','wholeManagedValueStored'))
  and all(source.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted','liveFormatterSelectionObserved'))
  and value.get('schema')==VALUE_SCHEMA and value.get('typeName')==name and value.get('capability')==VALUE_CAPS[name]
  and source.get('elementCanonicalCallbackTargetRva')==value.get('canonicalCallbackTargetRva'))
 need('complete-count-induction-and-owned-value',source['proof']['induction']['maxCount']==4096
  and source['proof']['value']['typeName']==name and source['proof']['value']['canonicalCallbackTargetRva']==value['canonicalCallbackTargetRva'])
 return dict(schema=LIST_SCHEMA,capability=LIST_CAPS[name],typeName=source['typeName'],elementType=name,elementCapability=value,
  countLimit=4096,countRange=[-1,4096],headerBytes=4,managedElementBytes=values.WIDTHS[name],elementWireBytes=None,
  packableReaderMethodDefinition=source['typedRequest']['methodSpec'][0],packableReaderTargetRva=source['callTargetRva'],
  initiallyNullListRequired=True,actualCallbackEqualsCanonicalRequired=True,positiveCountsAdmitted=True,
  completeManagedValueStored=True,profileAdmitted=True,growthAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def parameter_array_capability(opera,param_graph,pins):
 member=opera['record']['memberSources']['parameters'];array=member['source'];key=param_graph.get('keyValue',{})
 need('separate-complete-pooled-Param-graph',param_graph.get('nativeInputs')==pins
  and param_graph.get('admittedTypes')==[PKV,'Beyond.Gameplay.ParamValue','Beyond.Gameplay.ParamValueAtom']
  and(param_graph.get('stringEncoding'),param_graph.get('nullIndex'),param_graph.get('emptyIndex'),param_graph.get('parserArrayCountLimit'))==
   ('int32-pool-index',-2,-1,16384)and param_graph.get('wholeOwnerAdmitted')is False and param_graph.get('runtimeSelectionObserved')is False
  and key.get('typeName')==PKV and key.get('adapter',{}).get('pairForwarder',{}).get('getterReturnedReferenceSemanticsProved')is True)
 need('actual-owned-Param-reference-array',array.get('schema')=='endfield.skill-reference-array-component.v1'
  and array.get('status')=='validated-conditional-reference-array-component'and array.get('nativeInputs')==pins
  and(array.get('elementType'),array.get('elementValueType'),array.get('closedArrayType'),array.get('countLimit'))==(PKV,False,PKV+'[]',4096)
  and array.get('positiveCountsAdmitted')is True and array.get('elementGrammarAdmitted')is False
  and array.get('typedRequest')==member['typedRequest']and array['induction']['maxCount']==4096)
 return dict(schema=PARAM_SCHEMA,capability=PARAM_ARRAY,typeName=PKV+'[]',elementType=PKV,countLimit=4096,
  nestedAtomCountLimit=16384,nodeLimit=16384,elementLimit=16384,positiveCountsAdmitted=True,
  stringEncoding='int32-pool-index',nullIndex=-2,emptyIndex=-1,memberCounts=dict(keyValue=2,value=2,atom=2),
  atomFFOutput='zero64-and-null-string',actualCallbackEqualsCanonicalRequired=True,
  arrayReaderMethodDefinition=array['arrayReaderMethodDefinition'],arrayReaderTargetRva=array['arrayReaderTargetRva'],
  profileAdmitted=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def opera_array_capability(source,value,pins):
 need('exact-Opera-value-array',source.get('schema')=='endfield.story-opera-value-array-source.v1'
  and source.get('status')=='validated-conditional-opera-value-array'and source.get('nativeInputs')==pins
  and(source.get('elementType'),source.get('elementValueType'),source.get('closedArrayType'),source.get('elementManagedBytes'),source.get('elementWireBytes'))==
   (values.OPERA,True,values.OPERA+'[]',16,None)
  and source.get('countLimit')==4096 and source.get('countRange')==[-1,4096]
  and all(source.get(k)is True for k in('positiveCountsAdmitted','initiallyNullArrayRequired','actualSourceProved'))
  and all(source.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted'))
  and value.get('schema')==VALUE_SCHEMA and value.get('typeName')==values.OPERA and value.get('parametersCapability',{}).get('schema')==PARAM_SCHEMA)
 return dict(schema=ARRAY_SCHEMA,capability=OPERA_ARRAY,typeName=values.OPERA+'[]',elementType=values.OPERA,elementCapability=value,
  countLimit=4096,countRange=[-1,4096],headerBytes=4,managedElementBytes=16,elementWireBytes=None,
  arrayReaderMethodDefinition=source['arrayReaderMethodDefinition'],arrayReaderTargetRva=source['arrayReaderTargetRva'],
  initiallyNullArrayRequired=True,actualCallbackEqualsCanonicalRequired=True,positiveCountsAdmitted=True,
  profileAdmitted=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def compose(value_sources,list_sources,opera_arrays,param_graph,pins):
 """Pure child-only joins; fresh native authentication belongs to derive."""
 from scripts.game_data.codecs.levelscript import current_module_values as codec
 need('exact-three-owned-values',isinstance(value_sources,dict)and set(value_sources)==set(VALUE_CAPS))
 need('exact-two-owned-value-lists',isinstance(list_sources,dict)and set(list_sources)==set(LIST_CAPS))
 need('actual-Intro-and-Tail-value-array-sources',isinstance(opera_arrays,dict)
  and set(opera_arrays)=={'Beyond.Gameplay.EncounterData+IntroPart','Beyond.Gameplay.EncounterData+TailPart'})
 parameters=parameter_array_capability(value_sources[values.OPERA],param_graph,pins)
 caps={PARAM_ARRAY:parameters}
 for name,proof in value_sources.items():
  cap=value_capability(proof,pins,parameters=parameters if name==values.OPERA else None);codec.validate_value(cap);caps[VALUE_CAPS[name]]=cap
 for name,proof in list_sources.items():
  need('same-operation-list-value-proof',proof['proof']['value']==value_sources[name])
  cap=list_capability(proof,caps[VALUE_CAPS[name]],pins);codec.validate_list(cap);caps[LIST_CAPS[name]]=cap
 selected=[]
 for parent,proof in opera_arrays.items():
  cap=opera_array_capability(proof,caps[VALUE_CAPS[values.OPERA]],pins);codec.validate_array(cap);selected.append(cap)
 need('same-complete-Opera-array-profile',selected[0]==selected[1]);caps[OPERA_ARRAY]=selected[0]
 return dict(schema=SCHEMA,status='validated-conditional-module-values',nativeInputs=dict(pins),capabilities=caps,
  proof=dict(values=value_sources,lists=list_sources,operaArrays=opera_arrays,paramGraph=param_graph),
  parentFieldAdmitted=False,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False,
  evidenceBoundary=dict(exact='Three distinct canonical Module value grammars/default outputs, two positive value lists and Opera value-array/Param reference-array graph with their independent selected native sources.',
   conditional='All source-owner conditions, actual selected callbacks equal the owned canonical children, initially null collection outputs, coherent ready contexts/provider/helper ABI, disabled collector and disjoint stable storage. Pooled strings require the owning operation matching StringPool.',
   unresolved=['actual enclosing Module local/field/frame and fresh-output joins','runtime selection/behavior','whole Module/root dictionary/physical EOF/publication']))


def derive(image,pins,*,list_requests,opera_requests):
 """Fresh same-image child composition from explicit actual parent requests."""
 from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
 from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
 from scripts.game_data.memorypack import levelscript_module_value_list_sources as lists
 from scripts.game_data.memorypack import levelscript_module_value_transfer_sources as transfer
 from scripts.game_data.memorypack import levelscript_opera_array_sources as arrays,levelscript_param_graph_sources as params
 _publication_gate(image,pins);base=image.pe.image_base
 need('finite-explicit-list-requests',isinstance(list_requests,dict)and set(list_requests)==set(LIST_CAPS))
 need('finite-explicit-Opera-requests',isinstance(opera_requests,dict)
  and set(opera_requests)=={'Beyond.Gameplay.EncounterData+IntroPart','Beyond.Gameplay.EncounterData+TailPart'})
 def actual(request,method,argument):
  need('literal-parent-request',isinstance(request,dict)and isinstance(request.get('typed_request'),dict)
   and type(request.get('call_target'))is int and request['call_target']>base)
  usage=request['typed_request'];fresh=derive_typed_usage_context(image,usage['instructionRva'],label='storyModuleValues.actualParent')
  need('fresh-exact-parent-MethodInfo',fresh==usage and(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
   (6,'MemoryPack.MemoryPackReader',method,[],[argument]))
  instruction=request.get('source_instruction');need('literal-actual-call-site',isinstance(instruction,(list,tuple))and len(instruction)==2
   and type(instruction[0])is int and isinstance(instruction[1],str))
  raw=bytes.fromhex(instruction[1]);need('same-actual-E8-target',len(raw)==5 and raw[0]==232
   and base+instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==request['call_target'])
  image.check_instruction_windows([instruction],label='storyModuleValues.actualParentE8');return usage,request['call_target']
 list_sources={}
 for name,request in list_requests.items():
  usage,target=actual(request,'ReadPackable','System.Collections.Generic.List`1<'+name+'>')
  list_sources[name]=lists.derive(image,pins,typed_request=usage,call_target=target,element_type=name)
 value_sources={name:proof['proof']['value']for name,proof in list_sources.items()}
 value_sources[values.OPERA]=transfer.derive(image,pins,type_name=values.OPERA)
 opera_arrays={}
 for parent,request in opera_requests.items():
  usage,target=actual(request,'ReadArray',values.OPERA)
  opera_arrays[parent]=arrays.derive(image,pins,typed_request=usage,call_target=target)
 graph=params.derive(image,pins);result=compose(value_sources,list_sources,opera_arrays,graph,pins)
 result['actualRequests']=dict(lists=list_requests,operaArrays=opera_requests)
 _publication_gate(image,pins);return result
