"""Own pooled Param<List<GameplayTag>> with generated MC1/default tag elements.

The actual Param's ReadPackable context and call bind the independent selected
tag-list source. The canonical outer reference adapter is proved separately.
The raw4 unmanaged tag-array grammar supplies no evidence to this list.
"""
import json

VALUE='Beyond.Gameplay.Core.GameplayTag'
LIST='System.Collections.Generic.List`1<'+VALUE+'>'
TYPE='Beyond.Gameplay.Actions.Param`1<'+LIST+'>'
SCHEMA='endfield.levelscript-gameplay-tag-list-param-components.v1'
CAPABILITY='story-actionmap-gameplay-tag-list-param'
LIMIT=4096


def need(check,condition):
    if not condition:raise ValueError('gameplayTagListParam.'+check)


def _bind_action_parent(image,pins,cap):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.memorypack import generated_reader_sources
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    wrapper='Beyond.MemoryPack.Beyond_Gameplay_Actions_ListGetValueGameplayTagForMemoryPack'
    source=generated_reader_sources.derive(image,pins,wrapper)
    read,=[r for r in source['orderedSourceReads']if r['fieldName']=='_list']
    need('own-action-parent-nominal',source['wrapperName']==wrapper and read['declaredType']==TYPE)
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='gameplayTagListParam.actualParent')
    bound=bind_typed_read(image,usage,method_name='ReadValue',argument=TYPE,kind=21,reference=True)
    carrier=closed_generic_reference_pointer_extent(NativeReferenceContext(image),bound['argumentPointer'])
    need('own-action-parent-closed-carrier',carrier['type']==TYPE and carrier['argumentTypes']==[LIST]and carrier['bytes']==8)
    need('own-action-parent-reader-source',bound['methodDefinition']==cap['readerMethodDefinition']
        and read['sourceTargetRva']==cap['sourceTargetRva'])
    site,encoded=read['instruction'];raw=bytes.fromhex(encoded)
    need('own-action-parent-source-E8',len(raw)==5 and raw[0]==232
        and site+5+int.from_bytes(raw[1:],'little',signed=True)==cap['sourceTargetRva'])
    image.check_instruction_windows([read['instruction']],label='gameplayTagListParam.actualParentCall')
    return dict(source=source,read=read,typedRequest=usage,typedBinding=bound,closedCarrier=carrier)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_profile
    from scripts.game_data.memorypack.reference_param import derive_reference_parameter
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader,_reference_join
    from scripts.game_data.memorypack import skill_gameplay_tag_lists as listing
    from scripts.game_data.codecs.levelscript.current_gameplay_tag_list_param import validate
    _publication_gate(image,pins);base=image.pe.image_base
    profile=derive_profile(image,LIST,integer_slots=None)
    parent,*_=derive_reference_parameter(image,pins,profile,LIST,reader_method='ReadPackable')
    usage=parent['typedRead'];rows=parent['parent']['instructions']
    need('same-own-actual-closed-Param-list-request',usage['methodArguments']==[LIST])
    sites=[i for i,row in enumerate(rows)if row==[usage['instructionRva'],usage['instructionHex']]]
    need('one-own-list-context-site',len(sites)==1)
    calls=[row for row in rows[sites[0]+1:]if bytes.fromhex(row[1])[:1]==b'\xe8']
    need('own-actual-list-source-call',bool(calls))
    site,encoded=calls[0];raw=bytes.fromhex(encoded)
    need('own-exact-list-source-E8',len(raw)==5 and raw[0]==232)
    target=base+site+5+int.from_bytes(raw[1:],'little',signed=True)
    image.check_instruction_windows([calls[0]],label='gameplayTagListParam.actualConstantCall')
    child=listing.derive(image,pins,typed_request=usage,call_target=target,count_limit=LIMIT)
    collection=child['capabilities']['skill-root-gameplay-tag-value-list']
    element=child['capabilities']['skill-root-gameplay-tag']
    need('own-generated-MC1-default4-elements',collection['closedListType']==LIST
        and collection['elementType']==VALUE and collection['elementValueType']is True
        and collection['positiveCountsAdmitted']is True and collection['countLimit']==LIMIT
        and collection['elementCapability']=='skill-root-gameplay-tag'
        and element['memberCount']==1 and element['positiveWireBytes']==5
        and element['nullWireBytes']==1 and element['nullReturnsDefaultValue']is True
        and element['rawUnmanagedTagGrammarUsed']is False)
    need('same-actual-Param-list-reader',collection['packableReaderMethodDefinition']==usage['methodSpec'][0]
        and collection['packableReaderTargetRva']==target-base
        and child['proof']['context']['typedRequest']==usage)
    reference=_reference_join(image,pins,LIST);reader=_reader(image,pins)
    need('same-own-whole-Param-reference-getter',parent['ownedMethods']['GetValue']['pointerRva']==reference['getter']['entryRva'])
    cap=dict(schema='endfield.levelscript-gameplay-tag-list-param-capability.v1',typeName=TYPE,valueType=LIST,
        memberCount=4,fieldOrder=['constValue','idRef','paramSource','path'],pathEncoding='int32-pool-index',
        countLimit=LIMIT,countRange=[-1,LIMIT],headerBytes=4,elementType=VALUE,
        elementWireKind='generated-MC1-int32-or-FF-default4',elementMemberCount=1,
        positiveElementWireBytes=5,defaultElementWireBytes=1,defaultElementValue=0,
        outerNullReference=True,positiveCountsAdmitted=True,exactOwnNominalsProved=True,
        actualParamAndListAndElementCallbacksRequired=True,liveFormatterSelectionObserved=False,
        runtimeTagResolutionProved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        readerMethodDefinition=reader['readerMethodDefinition'],sourceTargetRva=reader['sourceTargetRva'],
        canonicalParamCallbackTargetRva=reference['adapter']['callbackBinding']['canonicalTargetRva'])
    validate(cap);action_parent=_bind_action_parent(image,pins,cap);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,status='validated-conditional-Param-child',
        capabilities={CAPABILITY:cap},proof=dict(parent=parent,parentProfile=profile,collection=child,reference=reference,reader=reader,actionParent=action_parent),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
