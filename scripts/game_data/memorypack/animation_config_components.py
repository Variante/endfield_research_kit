"""AnimationConfig MC15 with independently owned finite child grammars.

Every actual typed call and whole named field transfer is joined to its own
child. Positive fallback sets and repeated mask lists have distinct source,
callback, allocation and frame proofs. This is stored syntax under the declared
normal native selection conditions, without runtime animation/provider claims.
"""
import json

SCHEMA='endfield.animation-config-components.v2'
CAPABILITY='animation-config-current'
MASKS='animation-config-bone-weight-masks-positive'
TAGS='skill-root-gameplay-tag-value-list'


def need(check,condition):
    if not condition:raise ValueError('animationConfigComponents.'+check)


def normalized(v):return json.loads(json.dumps(v))


def validate_custom(component,pins):
    from scripts.game_data.memorypack import animation_custom_dictionary_components as owner
    need('all-three-own-custom-dictionaries',component.get('schema')==owner.SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-animation-custom-dictionaries')
    proof=component['proof'];caps={};required=set()
    need('only-three-static-domains',set(proof['dictionaries'])==set(owner.CAPABILITIES))
    for domain,row in proof['dictionaries'].items():
        key=proof['integerCallback']if domain=='timeRefCurves'else proof['stringCallback']
        value=proof['montage']if domain=='montages'else proof['curve']
        replay=owner.compose(pins,row['source'],key,value,key_dispatch=row['keyDispatch'])
        for name,cap in replay['capabilities'].items():
            need('coherent-custom-child',name not in caps or caps[name]==cap);caps[name]=cap
        required.update(replay['requiredExternalCapabilities'])
    need('exact-custom-source-composition',caps==component.get('capabilities')
        and sorted(required)==component.get('requiredExternalCapabilities'))
    return dict(capabilities=caps,requiredExternalCapabilities=sorted(required))


def compose(root,pins,*,extra,custom,unity,tags,fallback,masks,reference_readers):
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.memorypack import animation_config_root_sources as source
    from scripts.game_data.memorypack import animation_extra_union_components as extra_owner
    from scripts.game_data.memorypack import animation_custom_dictionary_components as custom_owner
    from scripts.game_data.memorypack import animation_int_curve_dictionary_components as unity_owner
    from scripts.game_data.memorypack import animation_fallback_set_components as fallback_owner
    from scripts.game_data.memorypack import animation_mask_positive_components as mask_owner
    from scripts.game_data.memorypack import skill_gameplay_tag_lists as tag_owner
    base=source.verify(root,pins);extra_owner.validate_component(extra,pins)
    custom_caps=validate_custom(custom,pins)
    need('own-ordinary-int-UnityCurve-dictionary',unity.get('schema')==unity_owner.SCHEMA and unity.get('nativeInputs')==pins
        and unity.get('status')=='validated-conditional-int-UnityCurve-dictionary')
    unity_caps=unity_owner.compose(pins,unity['proof']['source'],unity['proof']['curve'])
    need('same-complete-int-UnityCurve-dictionary',all(unity.get(k)==v for k,v in unity_caps.items()))
    fallback_caps=fallback_owner.validate_component(fallback,pins)
    mask_caps=mask_owner.validate_component(masks,pins)
    requests=root['requests'];bindings=[fallback_owner.bind_root(root,pins,fallback),mask_owner.bind_root(root,pins,masks)]
    need('exact-Extra-ordinary-ReadValue-field',requests[5]['typeName']==extra_owner.source.TYPE
        and requests[5]['typedRequest']['methodSpec'][0]==reference_readers['referenceReaderMethodDefinition']
        and requests[5]['sourceTargetRva']==reference_readers['referenceReaderTargetRva'])
    bindings.append(dict(memberIndex=5,capability=extra_owner.CAPABILITY,ordinaryReferenceReaderJoined=True))
    for domain,index in(('montages',6),('syncGroupCurves',11),('timeRefCurves',12)):
        actual=custom['proof']['dictionaries'][domain]['source'];request=requests[index]
        cap=custom_caps['capabilities'][custom_owner.CAPABILITIES[domain]]
        need('exact-static-dictionary-call-zero-local-field:'+domain,
            actual['proof']['request']['typedRequest']==request['typedRequest']
            and actual['typeName']==request['typeName'] and actual['sourceTargetRva']==request['sourceTargetRva']
            and cap['staticReaderMethodDefinition']==request['typedRequest']['methodSpec'][0]
            and request.get('initiallyNullOutputProved')is True
            and request['outLocal'].get('resetImmediatelyBeforeCurrentCall')is True
            and cap.get('initiallyNullOutputRequired')is True)
        bindings.append(dict(memberIndex=index,capability=custom_owner.CAPABILITIES[domain],
            ownFreshZeroLocalNamedFieldAndBothFramesProved=True))
    uc=unity_caps['capabilities'][unity_owner.CAPABILITY];ur=unity['proof']['source']['proof']['typedRequest']
    need('exact-int-UnityCurve-returned-reference-field',requests[10]['typedRequest']==ur
        and uc['typeName']==requests[10]['typeName']and uc['packableReaderTargetRva']==requests[10]['sourceTargetRva']
        and uc['packableReaderMethodDefinition']==ur['methodSpec'][0])
    bindings.append(dict(memberIndex=10,capability=unity_owner.CAPABILITY,wholeReturnedReferenceToNamedSetter=True))
    tc=tags.get('capabilities',{}).get(TAGS,{});te=tags.get('capabilities',{}).get('skill-root-gameplay-tag',{})
    need('exact-own-generated-GameplayTag-list-source',tags.get('schema')=='endfield.skill-gameplay-tag-list-components.v1'
        and tags.get('nativeInputs')==pins and tags.get('status')=='validated-conditional-components'
        and tc.get('closedListType')==requests[7]['typeName']==tag_owner.LIST
        and tc.get('elementCapability')=='skill-root-gameplay-tag'and tc.get('elementGrammarAdmitted')is True
        and tc.get('positiveCountsAdmitted')is True and tc.get('collectionCounts')==[-1,0]
        and tc.get('countLimit')==4096 and tc.get('elementValueType')is True
        and tc.get('packableReaderMethodDefinition')==requests[7]['typedRequest']['methodSpec'][0]
        and tc.get('packableReaderTargetRva')==requests[7]['sourceTargetRva']
        and te.get('memberCount')==1 and te.get('positiveWireBytes')==5 and te.get('nullWireBytes')==1
        and te.get('nullReturnsDefaultValue')is True and te.get('rawUnmanagedTagGrammarUsed')is False)
    context=tags['proof']['context'];need('same-actual-GameplayTag-list-request',context.get('typedRequest')==requests[7]['typedRequest'])
    bindings.append(dict(memberIndex=7,capability=TAGS,generatedMC1Elements=True,wholeReturnedReferenceToNamedSetter=True))
    fact=json.loads((CONTRACTS_DIR/'animation_masks_native.json').read_bytes());mask=root['firstFiveProfile']
    need('independent-current-mask-and-hash-source',fact.get('nativeInputs')==pins
        and fact.get('supportedCounts')==mask.get('supportedCounts')==[-1,0,1]
        and mask.get('entryRuntimeBytes')==16 and mask.get('entryWireBytes')==13
        and requests[3]['sourceTargetRva']==fact['profile']['rootReads'][3]
        and all(requests[index]['sourceTargetRva']==fact['profile']['symbols']['hash']for index in(1,2,4,8,9)))
    caps={};required=set()
    for selected in(extra,custom_caps,unity_caps,tags,fallback_caps,mask_caps):
        for name,cap in selected['capabilities'].items():
            need('coherent-independent-child:'+name,name not in caps or caps[name]==cap);caps[name]=cap
        required.update(selected.get('requiredExternalCapabilities',[]))
    caps[CAPABILITY]=dict(typeName=source.TYPE,wrapperName=root['wrapperName'],memberCount=15,
        orderedFieldNames=list(source.FIELDS),wholeGrammarAdmitted=True,allFifteenFieldsAdmitted=True,
        wholeNamedFieldAndBothPositiveFramesProved=True,rootNullMarkerAdmitted=False,
        fallbackPositiveAdmitted=True,maskCountLimit=4096,nodeLimit=16384,physicalEOFRequired=True,
        primitivePathBytes=8,boolBytes=1,runtimeAnimationProved=False,
        requiredChildCapabilities=[fallback_owner.CAPABILITY,MASKS,extra_owner.CAPABILITY,TAGS,unity_owner.CAPABILITY,
            *custom_owner.CAPABILITIES.values()])
    required.add('byte-payload');need('all-child-fields-bound',sorted(b['memberIndex']for b in bindings)==[0,3,5,6,7,10,11,12])
    return normalized(dict(schema=SCHEMA,status='validated-conditional-animation-config-components',nativeInputs=pins,
        capability=CAPABILITY,capabilities=caps,requiredExternalCapabilities=sorted(required-set(caps)),
        bindings=sorted(bindings,key=lambda b:b['memberIndex']),proof=dict(root=root,extra=extra,custom=custom,unity=unity,
            tags=tags,fallback=fallback,masks=masks,referenceReaders=reference_readers),wholeOwnerGrammarAdmitted=True,
        publicDecoderActivated=False,runtimeAnimationProved=False,evidenceBoundary=__doc__))


def validate_component(component,pins):
    need('own-complete-root-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins)
    p=component['proof'];checked=compose(p['root'],pins,extra=p['extra'],custom=p['custom'],unity=p['unity'],
        tags=p['tags'],fallback=p['fallback'],masks=p['masks'],reference_readers=p['referenceReaders'])
    need('same-all-fifteen-independent-field-joins',checked==component)
    return dict(capability=CAPABILITY,capabilities=checked['capabilities'],requiredExternalCapabilities=checked['requiredExternalCapabilities'])


def derive(image,pins,*,extra,custom,unity):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import animation_config_root_sources as source,animation_fallback_set_components as fallback_owner
    from scripts.game_data.memorypack import animation_mask_positive_components as mask_owner
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as tags
    _publication_gate(image,pins);root=source.derive(image,pins);base=image.pe.image_base
    def selected(index):
        r=root['requests'][index];return r['typedRequest'],base+r['sourceTargetRva']
    usage,target=selected(7);tag=tags(image,pins,typed_request=usage,call_target=target,count_limit=4096)
    usage,target=selected(0);fallback=fallback_owner.derive(image,pins,typed_request=usage,source_target=target,
        montage=custom['proof']['montage'],tags=tag)
    masks=mask_owner.derive(image,pins,root=root)
    result=compose(root,pins,extra=extra,custom=custom,unity=unity,tags=tag,fallback=fallback,masks=masks,reference_readers=reference_reader_abi(image,pins))
    _publication_gate(image,pins);return result


def derive_current(image,pins,*,pooled_capability):
    """Fresh complete source graph; generated reports are never inputs."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import animation_config_root_sources as roots
    from scripts.game_data.memorypack import animation_extra_graph_sources as extras
    from scripts.game_data.memorypack import animation_custom_dictionary_components as dictionaries
    from scripts.game_data.memorypack import animation_int_curve_dictionary_components as ordinary
    from scripts.game_data.memorypack import animation_fallback_set_components as fallback_owner
    from scripts.game_data.memorypack import animation_mask_positive_components as mask_owner
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_gameplay_tag_lists import derive as tag_list
    _publication_gate(image,pins);base=image.pe.image_base;root=roots.derive(image,pins)
    extra=extras.derive(image,pins,pooled_capability=pooled_capability)
    char,=[r for r in extra['proof']['records']if r['typeName'].endswith('.CharacterAnimExtraData')]
    hurt=char['proof']['valueChildren']['16']['proof']['valueComponent']
    curve=hurt['proof']['valueChildren']['0']['proof']['value']['proof']['typedSource']
    requests={domain:dict(typedRequest=root['requests'][index]['typedRequest'],
        sourceTarget=base+root['requests'][index]['sourceTargetRva'])
        for domain,index in(('montages',6),('syncGroupCurves',11),('timeRefCurves',12))}
    custom=dictionaries.derive(image,pins,requests=requests,
        curve_request=curve['proof']['typedRequest'],curve_source_target=base+curve['sourceTargetRva'])
    request=root['requests'][10]
    unity=ordinary.derive(image,pins,typed_request=request['typedRequest'],call_target=base+request['sourceTargetRva'])
    request=root['requests'][7]
    tags=tag_list(image,pins,typed_request=request['typedRequest'],call_target=base+request['sourceTargetRva'],count_limit=4096)
    request=root['requests'][0]
    fallback=fallback_owner.derive(image,pins,typed_request=request['typedRequest'],source_target=base+request['sourceTargetRva'],
        montage=custom['proof']['montage'],tags=tags)
    masks=mask_owner.derive(image,pins,root=root)
    result=compose(root,pins,extra=extra,custom=custom,unity=unity,tags=tags,fallback=fallback,masks=masks,
        reference_readers=reference_reader_abi(image,pins))
    _publication_gate(image,pins);return result
