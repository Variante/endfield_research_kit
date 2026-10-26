"""Finite ExtraData dictionary source replay and component joins.

Native source identity is separate from the nominal key callback and value
grammar. The containing record must independently bind the fresh out-local,
named setter and full enclosing frame.
"""
import json

from scripts.game_data.memorypack import animation_extra_dictionary_sources as source
from scripts.game_data.memorypack import animation_extra_dictionary_programs as paths
from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions

SCHEMA='endfield.animation-extra-dictionary-components.v1'
WIRE='animation-extra-static-dictionary'
CAPABILITIES=dict(zip(source.TYPES,(
    'animation-extra-char-hurt-dictionary','animation-extra-move-additive-dictionary',
    'animation-extra-override-perform-dictionary','animation-extra-enemy-hurt-dictionary',
    'animation-extra-enemy-shake-dictionary'),strict=True))


def need(check,condition):
    if not condition:raise ValueError('animationExtraDictionaryComponents.'+check)


def normalized(value):
    return json.loads(json.dumps(value))


def replay_source(actual,pins):
    """Reproduce all five source paths and the exact actual parent E8 slice."""
    typename=actual.get('typeName');need('finite-own-source',typename in source.TYPES)
    key,value=source.TYPES[typename];profile,key_bytes=source.DOMAINS[(key,value)]
    need('same-current-nominal-source',actual.get('schema')=='endfield.animation-extra-dictionary-source.v1'
        and actual.get('status')=='validated-conditional-static-out-source'and actual.get('nativeInputs')==pins
        and(actual.get('keyType'),actual.get('valueType'),actual.get('profile'))==(key,value,profile)
        and actual.get('resultAbi')=='void-byref-reference8'and actual.get('referenceBytes')==8
        and actual.get('keyOutputBytes')==key_bytes and actual.get('valueOutputBytes')==8
        and actual.get('valueStorageKind')==('value8'if profile=='enum1-value8'else'reference8')
        and actual.get('objectMarkerBytes')==1 and actual.get('countHeaderBytes')==4
        and actual.get('initiallyNullOutputRequired')is True and actual.get('existingOutputClearProved')is False
        and actual.get('keyGrammarAdmitted')is False and actual.get('referenceChildGrammarAdmitted')is False
        and actual.get('parentFieldAdmitted')is False and actual.get('wholeOwnerAdmitted')is False)
    context=actual.get('context',{});usage=context.get('typedRequest',{})
    need('same-actual-static-source-context',source.request_shape(usage)==(key,value)
        and context.get('contextMode')=='owned-static-out-animation-extra-dictionary'
        and context.get('fullTypeName')==typename and context.get('register')=='r8'
        and context.get('resultAbi')=='void-byref-reference8'
        and context.get('methodSpec')==usage.get('methodSpec')
        and actual.get('readerMethodDefinition')==usage['methodSpec'][0]
        and type(actual.get('sourceTargetRva'))is int and actual['sourceTargetRva']>0)
    p=actual['proof'];programs=p.get('programs',[])
    need('five-complete-source-programs',len(programs)==5 and programs[0].get('selectedBytes'))
    base=programs[0]['selectedBytes'][0][0]-actual['sourceTargetRva']
    need('explicit-selected-native-base',type(base)is int and base>=2**32)
    raw=regions(p['windows'],p['regions'],base,'extra-dictionary')
    if profile=='string-reference':
        from scripts.game_data.memorypack import animation_custom_dictionary_programs as string_paths
        from scripts.game_data.memorypack.counted_loop_sources import prove_induction
        symbols=string_paths.symbols(raw,'reference-Montage')
        checked=[string_paths.montage_program(raw,base+actual['sourceTargetRva'],p['readerOffsets'],symbols,count=n)
            for n in(-1,0,1,2,3)]
        counted=prove_induction(checked[1:],initial='448bef',increment='41ffc5',comparison='443bac2490000000',
            counter='r13d',saved_count='signed Int32 stack144',max_count=4096,mode_key='newDictionary',
            backedge_sites=checked[2]['backedgeSites'])
    else:
        symbols=paths.symbols(raw,key_bytes=key_bytes)
        checked=[paths.program(raw,base+actual['sourceTargetRva'],p['readerOffsets'],symbols,count=n,key_bytes=key_bytes)
            for n in(-1,0,1,2,3)]
        counted=paths.induction(checked,key_bytes=key_bytes)
    need('same-complete-byte-programs-and-induction',normalized(checked)==programs
        and normalized(counted)==p.get('countInduction')and{k:v-base for k,v in symbols.items()}==p.get('symbolRvas'))
    from scripts.game_data.memorypack.animation_extra_parent_sources import PARENT_FIELDS
    parent=p.get('actualParent',{});parent_type=parent.get('typeName');index=parent.get('memberIndex')
    need('exact-own-containing-declaration',parent_type in PARENT_FIELDS and type(index)is int
        and PARENT_FIELDS[parent_type].get(index)==typename and parent.get('actualTypedCallProved')is True
        and parent.get('zeroLocalProved')is False and parent.get('parentFieldAdmitted')is False
        and parent.get('enclosingFrameAdmitted')is False and parent.get('originalField',[None,None])[1]==typename
        and parent['originalField'][0]in parent.get('originalFieldLineage',[])
        and parent.get('originalFieldLineage',[None])[0]==parent_type)
    parent_raw=regions(parent['windows'],parent['regions'],base,'extra-dictionary-parent')
    need('same-exact-own-parent-call',normalized(source.caller_program(parent_raw,usage,
        base+actual['sourceTargetRva'],base=base))==parent.get('program'))
    need('same-selected-key-carrier',context.get('arguments',[{}])[0].get('typeName')==key
        and len(context.get('arguments',[]))==2 and context['arguments'][1].get('typeName')==value)
    if profile=='enum1-value8':
        selected=context['arguments'][1]
        need('independent-own-value8-layout',selected.get('typeKind')==17 and selected.get('valueCarrierBytes')==8
            and selected.get('fields')==[['animationSpeed','float',16],['animationWeight','float',20]]
            and selected.get('referenceLaneOffsets')==selected.get('paddingByteRanges')==[])
    return base


def key_capability(evidence,actual,pins):
    """Separate exact nominal enum selection from the actual source carrier."""
    key=actual['keyType']
    if key=='string':
        from scripts.game_data.memorypack.animation_custom_dictionary_components import replay_callback
        replay_callback(evidence,pins);need('own-string-key',evidence.get('typeName')=='string')
        return evidence
    if actual['profile']=='enum1-value8':
        from scripts.game_data.il2cpp import enum_byte_nominal_callbacks as nominal
        proof=evidence.get('proof',{})
        rebuilt=nominal.compose(pins,proof.get('originalContextSource',{}),proof.get('nominalRegistrySource',{}),
            proof.get('selectedCallbackSource',{}))
        cap=rebuilt['capability'];registry=proof['nominalRegistrySource']['proof']
        need('same-independent-original-byte-nominal-source',evidence==rebuilt
            and cap.get('typeName')==key and cap.get('typeDefinition')==actual['context']['arguments'][0]['typeDefinition']
            and cap.get('wireBytes')==1 and cap.get('underlyingType')=='byte'
            and registry.get('actualDictionaryRequest')==actual['context']['typedRequest']
            and cap.get('providerTargetRva')==actual['proof']['symbolRvas']['keyProvider']
            and cap.get('dispatchTargetRva')==actual['proof']['symbolRvas']['keyDispatch'])
        return dict(cap,callbackMethodDefinition=cap['formatterMethodDefinition'])
    cap=evidence.get('capability',{});binding=evidence.get('nominalBinding',{})
    need('separate-selected-int32-enum-source',actual['profile']=='enum4-reference'
        and evidence.get('nativeInputs')==pins and cap.get('nativeInputs')==pins
        and cap.get('schema')=='endfield.enum-nominal-callback-sources.v1'
        and cap.get('status')=='validated-conditional-callback'and cap.get('typeName')==key
        and cap.get('typeDefinition')==actual['context']['arguments'][0]['typeDefinition']
        and cap.get('wireBytes')==4 and cap.get('callbackSlot')==5
        and cap.get('readerByref')is True and cap.get('outputByref')is True
        and cap.get('actualRuntimeSelectionObserved')is False
        and cap.get('unconditionalCallbackSelectionProved')is False
        and cap.get('parentOrCollectionGrammarAdmitted')is False
        and len(cap.get('conditions',[]))==6 and all(isinstance(c,str)and c for c in cap['conditions'])
        and type(cap.get('formatterMethodDefinition'))is int and cap['formatterMethodDefinition']>0
        and type(cap.get('callbackTargetRva'))is int and cap['callbackTargetRva']>0)
    carrier=binding.get('carrier',{});raw=bytes.fromhex(carrier.get('rawHex',''))
    need('same-actual-static-key-carrier',binding.get('typeName')==key and binding.get('typeDefinition')==cap['typeDefinition']
        and binding.get('argumentIndex')==0 and binding.get('callbackCapability')==cap
        and binding.get('actualTypedRequest')==actual['context']['typedRequest']
        and binding.get('actualProviderMethodInfoAndDispatcherJoinRequired')is True
        and binding.get('actualRuntimeSelectionObserved')is False and binding.get('parentOrCollectionGrammarAdmitted')is False
        and carrier.get('name')==key and len(raw)==16 and raw[10:12]==b'\x11\x80'
        and int.from_bytes(raw[:8],'little')==cap['typeDefinition']
        and raw.hex().upper()==actual['context']['arguments'][0]['rawTypeRecordHex'])
    return dict(cap,callbackMethodDefinition=cap['formatterMethodDefinition'])


def dispatch_program(actual,role,callback,base,*,adapter=None):
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath,deserialize_slot
    helper=actual['proof']['helpers'].get(role,{})
    need('own-exact-dispatch-helper',role in('keyDispatch','valueDispatch')and helper.get('targetRva')==actual['proof']['symbolRvas'].get(role)
        and type(helper.get('targetRva'))is int)
    raw=regions(helper['windows'],helper['regions'],base,role)
    if actual['profile']=='enum1-value8':
        if role=='keyDispatch':
            from scripts.game_data.il2cpp.enum_byte_callback_sources import dispatch_program as byte_dispatch
            g=BytesPath(raw,base+helper['targetRva'])
            g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf9','498bd8','488bf2')
            prepare=g.relative('e8')
            programs=[byte_dispatch(raw,base+helper['targetRva'],prepare=prepare,callback=base+callback,**options)
                for options in ({},dict(refill=True),dict(indirect=True))]
            return normalized(dict(profile='own-byte-enum-dispatch',programs=programs,
                callbackTargetRva=callback,sourceTargetRva=helper['targetRva'],actualPointerAliasInferred=False))
        from scripts.game_data.memorypack import animation_enemy_shake_value_sources as shake
        from scripts.game_data.memorypack.pooled_global_buff_id_sources import adapter_program
        need('own-independent-value8-canonical-source',isinstance(adapter,dict)and adapter.get('schema')==shake.SCHEMA
            and adapter.get('nativeInputs')==actual['nativeInputs']and adapter.get('typeName')==actual['valueType']
            and adapter.get('ordinaryOriginalCallbackAdmitted')is True
            and adapter.get('ordinaryOriginalReadValueAdmitted')is False
            and adapter.get('proof',{}).get('symbolRvas',{}).get('adapter')==callback)
        symbols={k:base+v for k,v in adapter['proof']['symbolRvas'].items()}
        programs=[adapter_program(raw,base+helper['targetRva'],symbols,dispatch=True,**options)
            for options in ({},dict(create=False),dict(null=True))]
        return normalized(dict(profile='actual-inline-canonical-value8',programs=programs,
            callbackTargetRva=callback,sourceTargetRva=helper['targetRva'],actualPointerAliasInferred=False,
            callbackSelectionConditional=True,runtimeSelectionObserved=False))
    if role=='valueDispatch'and adapter is not None:
        from scripts.game_data.memorypack.reference_adapter_sources import dispatch
        binding=adapter.get('callbackBinding',{});routes=adapter.get('canonicalRoutes',{})
        need('own-independent-canonical-reference-adapter',adapter.get('schema')=='endfield.reference-object-adapter-source.v1'
            and adapter.get('nativeInputs')==actual['nativeInputs']and adapter.get('typeName')==actual['valueType']
            and binding.get('canonicalTargetRva')==callback and binding.get('actualCallbackEqualsCanonicalRequired')is True
            and binding.get('runtimeSelectionObserved')is False and routes.get('symbolRvas',{}).get('main')==callback)
        symbols={k:base+v for k,v in routes['symbolRvas'].items()}
        # Execute this actual E8 target's complete selected inline paths. The
        # child's canonical body supplies helper identities, never its bytes.
        programs=[dispatch(raw,base+helper['targetRva'],symbols,**options)for options in(
            {},dict(create=False),dict(wrapper_null=True),dict(create=False,wrapper_null=True),dict(null=True))]
        return normalized(dict(profile='actual-inline-canonical-reference',sourceTargetRva=helper['targetRva'],
            callbackTargetRva=callback,programs=programs,actualPointerAliasInferred=False,
            callbackSelectionConditional=True,runtimeSelectionObserved=False))
    # The complete helper owns the preparation call. Decode that E8 at the
    # exact selected prologue boundary, then replay the complete byte program.
    entry=base+helper['targetRva'];g=BytesPath(raw,entry)
    if role=='keyDispatch':
        need('own-int32-enum-dispatch',actual['profile']=='enum4-reference')
        g.take('48895c2408','4889742410','57','4883ec20','488b0a','498bf1','498bd8','488bfa')
        prepare=g.relative('e8')
        from scripts.game_data.memorypack.skill_gait_dictionary_callbacks import dispatch_program as enum_dispatch
        return normalized(enum_dispatch(raw,entry,actual['proof']['readerOffsets'],prepare=prepare,callback=base+callback,kind='enum'))
    need('own-reference-dispatch',actual['valueStorageKind']=='reference8')
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec70','4d8be9','4d8bf8','488bfa','0fb7d9','488b0a')
    prepare=g.relative('e8')
    return normalized(deserialize_slot(raw,entry,prepare=prepare,callback=base+callback))


def compose(pins,actual,key_evidence,value_component,*,key_dispatch=None,value_dispatch=None,
        pooled_capability=None,value_binder=None):
    """Join independently proved sources; source alone never grants a child."""
    base=replay_source(actual,pins);key=key_capability(key_evidence,actual,pins)
    if actual['keyType']=='string':need('direct-string-slot5-source',key_dispatch is None)
    else:need('same-complete-own-key-dispatch',key_dispatch==dispatch_program(actual,'keyDispatch',key['callbackTargetRva'],base))
    if actual['valueType']=='string':
        need('independent-current-pooled-string-value',value_component==key_evidence and isinstance(pooled_capability,dict)
            and pooled_capability.get('wholeGrammarAdmitted')is True and pooled_capability.get('encoding')=='int32-pool-index'
            and pooled_capability.get('wireBytes')==4 and pooled_capability.get('emptyIndex')==-1 and pooled_capability.get('nullIndex')==-2)
        children={'byte-payload':pooled_capability};primary='byte-payload';callback=key['callbackTargetRva'];required=['byte-payload']
    else:
        from scripts.game_data.memorypack.animation_extra_record_components import validate_component
        selected=validate_component(value_component,pins,value_binder=value_binder)
        children=selected['capabilities'];primary=selected['capability'];child=children[primary]
        byte_value=actual['profile']=='enum1-value8'
        need('own-complete-value-callback',child.get('typeName')==actual['valueType']
            and child.get('valueStorageKind')==('value8'if byte_value else'reference8')and child.get('wholeGrammarAdmitted')is True
            and child.get('ordinaryOriginalReadValueAdmitted')is (not byte_value)
            and(not byte_value or child.get('ordinaryOriginalCallbackAdmitted')is True)
            and child.get('originalTypeDefinition')==actual['context']['arguments'][1]['typeDefinition'])
        callback=child['canonicalAdapterTargetRva'];required=selected['requiredExternalCapabilities']
    if actual['profile']=='string-reference':need('direct-value-slot5-source',value_dispatch is None)
    else:need('same-complete-own-value-dispatch',value_dispatch==dispatch_program(actual,'valueDispatch',callback,base,
        adapter=value_component['proof']['source']if actual['profile']=='enum1-value8'else value_component['proof']['adapter']))
    required=sorted(set(required)|({'byte-payload'}if actual['keyType']=='string'or actual['valueType']=='string'else set()))
    cap=dict(typeName=actual['typeName'],keyType=actual['keyType'],valueType=actual['valueType'],valueStorageKind=actual['valueStorageKind'],
        staticReaderMethodDefinition=actual['readerMethodDefinition'],staticReaderTargetRva=actual['sourceTargetRva'],
        resultAbi='void-byref-reference8',referenceBytes=8,wholeGrammarAdmitted=True,staticOutReferenceAdmitted=True,
        ordinaryOriginalReadValueAdmitted=False,nullable=True,nullMarker=255,nullWireBytes=1,positiveMarkerDomain=[0,254],
        nativePositiveHeaderOneEnforced=False,countEncoding='signed-int32',countBytes=4,countLimit=actual['proof']['countInduction']['maxCount'],
        nodeLimit=16384,positiveCountsAdmitted=True,keyWireBytes=key['wireBytes'],keyCallback=key,valueCapability=primary,
        valueCallbackTargetRva=callback,requiredChildCapabilities=children,requiredExternalCapabilities=required,
        callbackSelectionConditional=True,initiallyNullOutputRequired=True,clearExistingDictionaryAdmitted=False,
        orderedEntriesPreserved=True,duplicateKeysPreserved=True,finalMutableDictionaryReconstructed=False,
        actualRuntimeSelectionObserved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        conditions=key['conditions']+[actual['condition'],__doc__])
    from scripts.game_data.memorypack.animation_extra_dictionary_codec import require_capability
    require_capability(cap,actual['typeName'])
    return dict(capabilities={**children,CAPABILITIES[actual['typeName']]:cap},requiredExternalCapabilities=required)


def validate_component(component,pins,*,value_binder=None):
    need('own-current-component',component.get('schema')==SCHEMA
        and component.get('status')=='validated-conditional-animation-extra-dictionary-components'
        and component.get('nativeInputs')==pins and component.get('parentFieldAdmitted')is False
        and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];rebuilt=compose(pins,p['source'],p['keyEvidence'],p['valueComponent'],key_dispatch=p['keyDispatch'],
        value_dispatch=p['valueDispatch'],pooled_capability=p.get('pooledCapability'),value_binder=value_binder)
    need('exact-complete-capabilities',rebuilt['capabilities']==component.get('capabilities')
        and rebuilt['requiredExternalCapabilities']==component.get('requiredExternalCapabilities'))
    return rebuilt


def _derive_on_children(image,pins,*,requests,children,pooled_capability=None,value_binder=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import animation_custom_dictionary_callbacks as callbacks,enum_optin_native_sources
    from scripts.game_data.il2cpp.enum_optin_callback_bindings import bind_dictionary_key
    _publication_gate(image,pins);need('finite-request-selection',isinstance(requests,dict)and bool(requests)and set(requests)<=set(source.TYPES))
    enum=None;string=None;owners=[];base=image.pe.image_base
    for typename,request in requests.items():
        context=source.request_context(image,request['typedRequest']['instructionRva'])
        need('same-actual-request',context['typedRequest']==request['typedRequest'])
        actual=source.derive(image,pins,context=context,source_target=request['sourceTarget'])
        if actual['keyType']=='string':
            if string is None:string=callbacks.derive_string(image,pins)
            evidence=string
        elif actual['profile']=='enum1-value8':
            from scripts.game_data.il2cpp.enum_byte_nominal_callbacks import derive as derive_byte
            symbols=actual['proof']['symbolRvas']
            evidence=derive_byte(image,pins,typed_request=request['typedRequest'],
                provider_target=base+symbols['keyProvider'],dispatch_target=base+symbols['keyDispatch'])
        else:
            if enum is None:enum=enum_optin_native_sources.derive(image,pins,domain='animation-extra-int32-keys')
            cap=enum['capabilities']['skill-enum-callback:'+actual['keyType']]
            evidence=dict(nativeInputs=pins,capability=cap,nominalSource=enum,
                nominalBinding=bind_dictionary_key(image,pins,cap,typed_request=request['typedRequest'],enum_type=actual['keyType']))
        key=key_capability(evidence,actual,pins)
        value=string if actual['valueType']=='string'else children[actual['valueType']]
        selected=None
        if actual['valueType']!='string':
            from scripts.game_data.memorypack.animation_extra_record_components import validate_component as record
            q=record(value,pins,value_binder=value_binder);selected=q['capabilities'][q['capability']]['canonicalAdapterTargetRva']
        kd=None if actual['keyType']=='string'else dispatch_program(actual,'keyDispatch',key['callbackTargetRva'],base)
        vd=None if actual['profile']=='string-reference'else dispatch_program(actual,'valueDispatch',selected,base,
            adapter=value['proof']['source']if actual['profile']=='enum1-value8'else value['proof']['adapter'])
        joined=compose(pins,actual,evidence,value,key_dispatch=kd,value_dispatch=vd,pooled_capability=pooled_capability,value_binder=value_binder)
        component=dict(schema=SCHEMA,status='validated-conditional-animation-extra-dictionary-components',nativeInputs=pins,
            typeName=typename,**joined,proof=dict(source=actual,keyEvidence=evidence,valueComponent=value,
                keyDispatch=kd,valueDispatch=vd,pooledCapability=pooled_capability),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
        validate_component(component,pins,value_binder=value_binder);owners.append(component)
    _publication_gate(image,pins);return normalized(dict(nativeInputs=pins,owners=owners))
