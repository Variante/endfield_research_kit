"""Exact Param<Vector3> reference arrays, independent of Param<List<Vector3>>.

ReadArray's reciprocal contexts and stride-eight slot loop supply no element
wire size. The independently derived four-field Vector3 Param supplies its
own raw12 constant and canonical callback. Ready compatible provider/callback,
typed fresh allocation, disabled collector and coherent buffered input remain
conditions. No runtime vector evaluation or enclosing owner is admitted.
"""
import json

SCHEMA='endfield.levelscript-vector3-param-array-components.v1'
SOURCE_SCHEMA='endfield.levelscript-vector3-param-array-source.v1'
CAPABILITY='story-actionmap-vector3-param-array'
WIRE='actionmap-param-array'
VALUE='UnityEngine.Vector3'
ELEMENT='Beyond.Gameplay.Actions.Param`1<'+VALUE+'>'
TYPE=ELEMENT+'[]'
PARENT='Beyond.Gameplay.Actions.ListMakeVector3'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_ListMakeVector3ForMemoryPack'


def need(check, condition):
    if not condition:raise ValueError('vectorParamArray.'+check)


def norm(value):return json.loads(json.dumps(value))


def require_carrier(carrier):
    raw=bytes.fromhex(carrier.get('declaredTypeRecordHex','')) if isinstance(carrier,dict) else b''
    definition=bytes.fromhex(carrier.get('definitionTypeRecordHex','')) if isinstance(carrier,dict) else b''
    need('exact-closed-reference-Param-carrier', isinstance(carrier,dict)
        and carrier.get('type')==ELEMENT and type(carrier.get('bytes')) is int and carrier['bytes']==8
        and type(carrier.get('definitionTypeIndex')) is int and carrier.get('argumentTypes')==[VALUE]
        and len(raw)==len(definition)==16 and raw[10:12]==b'\x15\x00' and definition[10:12]==b'\x12\x00')


def derive_source(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import validate_typed_usage_context,validate_generic_contexts,derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.buff_ptr_sources import _call
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reader
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.skill_reference_array_sources import array_program,provider_program,induction
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    need('exact-count-domain',type(count_limit)is int and count_limit==4096)
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    need('literal-positive-source-target',type(call_target)is int and call_target>base)
    validate_typed_usage_context(image,typed_request,label='vectorParamArray.actual')
    bound=bind_typed_read(image,typed_request,method_name='ReadArray',argument=ELEMENT,kind=21,reference=True)
    carrier=closed_generic_reference_pointer_extent(ctx,bound['argumentPointer']);require_carrier(carrier)
    need('own-Param-definition',carrier['definitionTypeIndex']==ctx.index.types['Beyond.Gameplay.Actions.Param`1'].index)
    array=pointer.owned(image,call_target)
    helpers={name:_call(array,offset)for name,offset in dict(arrayAllocate=247,provider=373,prepare=435).items()}
    offsets=scalar.reader_offsets(image,'vectorParamArray')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[array_program(array['regions'],call_target,offsets,helpers,count=n,count_limit=3)for n in(-1,0,1,2,3)]
    loop=induction(programs,count_limit=count_limit)
    reader=_reader(image,pins)
    contexts=ContextSymbols(image);first=contexts.context(typed_request['methodSpec'][0],is_method=True)
    second=contexts.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label='vectorParamArray.overloads')
    context=validate_read_array_context(image,[first,second],typed_request,GenericEntries(image),bound['argumentPointer'],
        reader['valueContext']['formatterDeserializeDefinition'],fail=lambda k,e,a:need(k,e==a))
    need('same-owned-GetFormatter-definition',reader['valueContext']['providerMethodDefinition']==second['entries'][3]['methodSpec'][0])
    provider=pointer.owned(image,helpers['provider'])
    ps={name:_call(provider,offset)for name,offset in dict(classFromType=88,hash=145,compare=238,backend=376,indexedType=393,assignable=409).items()}
    provider_proof=provider_program(provider['regions'],provider['pointer'],ps)
    need('same-Param-provider-and-cache',(reader['program']['providerClassCell'],reader['program']['cacheCell'])==
        (provider_proof['providerClassCell'],provider_proof['cache']['cacheGlobalCell']))
    usages=[]
    for program in programs:
        at=program['providerUsageInstruction']
        if at is None:continue
        usage=derive_typed_usage_context(image,at-base,label='vectorParamArray.provider')
        need('same-actual-provider-class',(usage['tag'],usage['typeName'])==(1,'MemoryPack.MemoryPackFormatterProvider')
            and usage['usageCellRva']+base==provider_proof['providerClassCell'])
        usages.append(usage)
    collector=_load('model_view_state_controller_native.json',pins)
    barrier=_barrier(image,base+collector['collector']['entryRva'])
    need('same-disabled-collector',all(p['collectorFlag']==base+barrier['result']['disabledFlagRva']for p in programs))
    _publication_gate(image,pins)
    return norm(dict(schema=SOURCE_SCHEMA,status='validated-conditional-vector-Param-array-source',nativeInputs=pins,
        elementType=ELEMENT,elementValueType=False,closedArrayType=TYPE,typedRequest=typed_request,
        arrayReaderMethodDefinition=typed_request['methodSpec'][0],arrayReaderTargetRva=call_target-base,
        countLimit=count_limit,elementGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(imageBase=base,closedCarrier=carrier,sourceWindows=array['windows'],
            sourceRegions=[(a,b.hex().upper())for a,b in array['regions']],readerOffsets=offsets,
            helperRvas={k:v-base for k,v in helpers.items()},programs=programs,induction=loop,
            contexts=[first,second],arrayContext=context,referenceReader=reader,
            providerWindows=provider['windows'],providerRegions=[(a,b.hex().upper())for a,b in provider['regions']],
            providerProgram=provider_proof,providerHelperRvas={k:v-base for k,v in ps.items()},actualProviderUsages=usages,barrier=barrier)))


def validate_source(source,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.skill_reference_array_sources import array_program,provider_program,induction
    need('exact-owned-array-source',type(source)is dict and source.get('schema')==SOURCE_SCHEMA
        and source.get('status')=='validated-conditional-vector-Param-array-source' and source.get('nativeInputs')==pins
        and source.get('elementType')==ELEMENT and source.get('closedArrayType')==TYPE
        and source.get('elementValueType')is False and type(source.get('countLimit'))is int and source['countLimit']==4096
        and all(source.get(k)is False for k in('elementGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    p=source['proof'];base=p['imageBase'];need('literal-image-base',type(base)is int and base>0)
    require_carrier(p['closedCarrier']);usage=source['typedRequest']
    need('actual-ReadArray-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadArray',[],[ELEMENT])
        and usage['methodSpec'][0]==source['arrayReaderMethodDefinition']
        and type(source.get('arrayReaderTargetRva'))is int and source['arrayReaderTargetRva']>0)
    body=regions(p['sourceWindows'],[[a-base,h]for a,h in p['sourceRegions']],base,'vector-Param-array')
    provider=regions(p['providerWindows'],[[a-base,h]for a,h in p['providerRegions']],base,'vector-Param-array-provider')
    symbols={k:base+v for k,v in p['helperRvas'].items()}
    paths=[array_program(body,base+source['arrayReaderTargetRva'],p['readerOffsets'],symbols,count=n,count_limit=3)for n in(-1,0,1,2,3)]
    need('complete-array-and-provider-source-replay',norm(paths)==p['programs'] and norm(induction(paths,count_limit=4096))==p['induction']
        and norm(provider_program(provider,symbols['provider'],{k:base+v for k,v in p['providerHelperRvas'].items()}))==p['providerProgram'])
    reader=p['referenceReader'];ctx=p['arrayContext']
    need('same-independent-reference-provider-context',ctx.get('readArrayOverloadsReciprocallyJoined')is True
        and ctx.get('emptyArrayTypeProviderAndDeserializeOwned')is True and ctx.get('formatterSlot')==5
        and ctx.get('unmanagedSlotExecuted')is False and ctx.get('returnOverloadDefinition')==source['arrayReaderMethodDefinition']
        and p['contexts'][0]['definition']==source['arrayReaderMethodDefinition']
        and p['contexts'][1]['entries'][3]['methodSpec'][0]==reader['valueContext']['providerMethodDefinition']
        and(reader['program']['providerClassCell'],reader['program']['cacheCell'])==
            (p['providerProgram']['providerClassCell'],p['providerProgram']['cache']['cacheGlobalCell']))
    need('same-disabled-collector-and-actual-provider',all(path['collectorFlag']==base+p['barrier']['result']['disabledFlagRva']for path in paths)
        and p['actualProviderUsages'] and all((u.get('tag'),u.get('typeName'),base+u.get('usageCellRva',-base))==
            (1,'MemoryPack.MemoryPackFormatterProvider',p['providerProgram']['providerClassCell'])for u in p['actualProviderUsages']))
    return base


def _capability(child,source):
    from scripts.game_data.codecs.levelscript.current_vector_param_array import SCHEMA as CAP_SCHEMA,validate
    cap=dict(schema=CAP_SCHEMA,elementType=ELEMENT,closedArrayType=TYPE,countLimit=4096,countWireBytes=4,nullCount=-1,
        freshArrayRequired=True,elementReferenceKind=21,referenceSlotBytes=8,elementWireBytes=None,elementCapability=child,
        readerMethodDefinition=source['arrayReaderMethodDefinition'],sourceTargetRva=source['arrayReaderTargetRva'],
        canonicalCallbackTargetRva=child['canonicalCallbackTargetRva'],elementGrammarAdmitted=True,positiveCountsAdmitted=True,
        actualElementCallbackEqualsProvedParamRequired=True,actualProviderEqualsProvedProviderRequired=True,
        liveFormatterSelectionObserved=False,runtimeValueEvaluationProved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    validate(cap);return cap


def derive(image,pins,*,typed_request,call_target,count_limit=4096):
    from scripts.game_data.memorypack.levelscript_condition_param_sources import derive_many,CAP_PREFIX
    source=derive_source(image,pins,typed_request=typed_request,call_target=call_target,count_limit=count_limit)
    children=derive_many(image,pins,[VALUE]);key=CAP_PREFIX+ELEMENT
    owners=[o for o in children['owners']if o.get('status')=='validated-conditional-Param-child'and o.get('typeName')==ELEMENT]
    need('one-independent-vector-Param-child',len(owners)==1 and children['capabilities'].get(key)==owners[0]['capability'])
    carrier=owners[0]['proof']['closedCarrier'];selected=source['proof']['closedCarrier']
    need('same-independent-closed-Param-carrier',all(carrier[k]==selected[k]for k in('type','bytes','definitionTypeIndex','argumentTypes','definitionTypeRecordHex'))
        and children['referenceReader']==source['proof']['referenceReader'])
    cap=_capability(owners[0]['capability'],source)
    return norm(dict(schema=SCHEMA,status='validated-conditional-vector-Param-array',nativeInputs=pins,
        capabilities={CAPABILITY:cap},proof=dict(source=source,ParamSource=children),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,sourceReceiptAuthority=False,currentVfsCorpus=False))


def validate_component(component,pins,capability=CAPABILITY):
    from scripts.game_data.memorypack.levelscript_condition_param_sources import CAP_PREFIX
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
    from scripts.game_data.codecs.levelscript.current_vector_param_array import validate
    need('own-array-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-vector-Param-array'and capability==CAPABILITY
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    p=component['proof'];validate_source(p['source'],pins)
    children=p['ParamSource'];child=_validate_capability(children,CAP_PREFIX+ELEMENT)
    need('same-child-build',children.get('nativeInputs')==pins and children['referenceReader']==p['source']['proof']['referenceReader'])
    expected=_capability(child,p['source']);cap=component['capabilities'][capability];validate(cap)
    need('exact-array-capability-projection',cap==expected)
    owners=[o for o in children['owners']if o.get('typeName')==ELEMENT]
    need('one-complete-canonical-element',len(owners)==1 and owners[0].get('status')=='validated-conditional-Param-child'
        and owners[0].get('capability')==child and all(owners[0]['proof']['closedCarrier'][k]==p['source']['proof']['closedCarrier'][k]
            for k in('type','bytes','definitionTypeIndex','argumentTypes','definitionTypeRecordHex')))
    return cap


def derive_member(image,pins,parent_source,member_index=7):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    need('exact-parent-source-selector',parent_source.get('nativeInputs')==pins and parent_source.get('wrapperName')==WRAPPER
        and parent_source.get('wrappedType')==PARENT and parent_source.get('completeSelectedCallerAdmitted')is True
        and type(member_index)is int and member_index==7)
    read=parent_source['orderedSourceReads'][member_index]
    need('exact-array-field',read['fieldName']=='_list'and read['declaredType']==TYPE)
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='vectorParamArray.parent')
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-parent-E8',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'])
    image.check_instruction_windows([read['instruction']],label='vectorParamArray.actual-parent')
    return derive(image,pins,typed_request=usage,call_target=image.pe.image_base+read['sourceTargetRva'])


def derive_parent(image,pins):
    from scripts.game_data.memorypack import generated_reader_sources
    batch=generated_reader_sources.derive_many(image,pins,[WRAPPER]);owner,=batch['owners']
    need('complete-own-array-parent',owner.get('status')=='complete-reader-source-proved')
    return derive_member(image,pins,owner['proof'])


def bind_member(source,scope,read,pins,usage,component,capability):
    cap=validate_component(component,pins,capability);actual=component['proof']['source'];index=read['memberIndex']
    need('exact-parent-and-owned-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('wrapperName')==WRAPPER and source.get('wrappedType')==PARENT
        and source.get('completeSelectedCallerAdmitted')is True and source.get('sourceScope')==scope
        and type(index)is int and index==7 and read.get('fieldName')=='_list'and read.get('declaredType')==TYPE
        and read.get('kind')=='reference:'+TYPE and read.get('mode')=='typed-Param-reference-array'
        and source['orderedSourceReads'][index]==scope['events'][index]==read
        and scope.get('arraySources',{}).get(str(index))==actual and actual['typedRequest']==usage
        and read.get('sourceTargetRva')==cap['sourceTargetRva'])
    context=read['context'];raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('same-actual-constructed-ReadArray-context',len(raw)==16 and raw[10:12]==b'\x15\x00'
        and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'),context.get('typeKind'))==
            ('MemoryPack.MemoryPackReader','ReadArray',ELEMENT,'rdx',21)
        and tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec')))
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('exact-actual-array-E8',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==cap['sourceTargetRva'])
    rich=scope['richProgram'];flows=[p for p in rich['sources']if p.get('memberIndex')==index]
    stores=[p for p in rich['fieldStores']if p.get('memberIndex')==index];setter=source['setters'][index]
    need('whole-array-RAX-to-own-named-setter',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
        and stores[0].get('instruction')in scope['selectedProgram'] and scope['richSetters'][index]==setter
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==8
        and setter.get('method',[None,None,None])[2]=='set____list__' and setter.get('codeWindows'))
    at,h=stores[0]['instruction'];raw=bytes.fromhex(h)
    need('actual-named-setter-call',len(raw)==5 and raw[0]in(232,233)
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
    paths=source['programs']
    need('all-four-complete-array-parent-frames',len(paths)==4
        and{(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(n,f)for n in(False,True)for f in(False,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    return dict(fieldName='_list',typeName=TYPE,capability=CAPABILITY,readerMethodDefinition=cap['readerMethodDefinition'],
        sourceTargetRva=cap['sourceTargetRva'],sourceReferenceKind=21,referenceOutputBytes=8,
        elementType=ELEMENT,closedCarrierProved=True,actualCallbackEqualsProvedChildRequired=True,
        parentArgumentLocalStoreFrameRequired=True,parentFieldAdmitted=False)
