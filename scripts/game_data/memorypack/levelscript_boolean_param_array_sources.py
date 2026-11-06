"""The two independently owned boolean-list getters' Param<bool> arrays."""
import json
from scripts.game_data.memorypack import levelscript_vector_param_array_sources as array_source

SCHEMA='endfield.levelscript-boolean-param-array-components.v1'
CAPABILITY='story-actionmap-boolean-param-array'
WIRE='actionmap-param-array'
ELEMENT='Beyond.Gameplay.Actions.Param`1<bool>'
TYPE=ELEMENT+'[]'
PARENT='Beyond.Gameplay.Actions.BoolGetterMultiAnd'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Actions_BoolGetterMultiAndForMemoryPack'
OWNERS={PARENT:WRAPPER,
    'Beyond.Gameplay.Actions.BoolGetterMultOr':'Beyond.MemoryPack.Beyond_Gameplay_Actions_BoolGetterMultOrForMemoryPack'}


def need(check,condition):
    if not condition:raise ValueError('booleanParamArray.'+check)


def capability(child,source):
    from scripts.game_data.codecs.levelscript.current_boolean_param_array import SCHEMA as CAP_SCHEMA,validate
    cap=dict(schema=CAP_SCHEMA,elementType=ELEMENT,closedArrayType=TYPE,countLimit=4096,countWireBytes=4,nullCount=-1,
        freshArrayRequired=True,elementReferenceKind=21,referenceSlotBytes=8,elementWireBytes=None,elementCapability=child,
        readerMethodDefinition=source['arrayReaderMethodDefinition'],sourceTargetRva=source['arrayReaderTargetRva'],
        canonicalCallbackTargetRva=child['canonicalCallbackTargetRva'],elementGrammarAdmitted=True,positiveCountsAdmitted=True,
        actualElementCallbackEqualsProvedParamRequired=True,actualProviderEqualsProvedProviderRequired=True,
        liveFormatterSelectionObserved=False,runtimeValueEvaluationProved=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)
    return validate(cap)


def validate_component(component,pins,selected=CAPABILITY):
    from scripts.game_data.memorypack.levelscript_condition_param_bindings import _validate_capability
    from scripts.game_data.memorypack.levelscript_condition_param_sources import CAP_PREFIX
    need('own-exact-component',component.get('schema')==SCHEMA and component.get('nativeInputs')==pins
        and component.get('status')=='validated-conditional-boolean-Param-array'and selected==CAPABILITY
        and component.get('parentFieldAdmitted')is False and component.get('wholeOwnerAdmitted')is False)
    proof=component['proof'];source=proof['source'];array_source.validate_source(source,pins)
    need('own-Boolean-source',source.get('schema')==array_source.BOOL_SOURCE_SCHEMA and source.get('elementType')==ELEMENT)
    children=proof['ParamSource'];child=_validate_capability(children,CAP_PREFIX+ELEMENT)
    need('same-independent-native-reader',children.get('nativeInputs')==pins
        and children.get('referenceReader')==source['proof']['referenceReader'])
    owners=[r for r in children['owners']if r.get('typeName')==ELEMENT]
    need('one-complete-own-Boolean-child',len(owners)==1 and owners[0].get('status')=='validated-conditional-Param-child'
        and owners[0].get('capability')==child and all(owners[0]['proof']['closedCarrier'][k]==source['proof']['closedCarrier'][k]
            for k in('type','bytes','definitionTypeIndex','argumentTypes','definitionTypeRecordHex')))
    expected=capability(child,source);need('exact-capability-projection',component.get('capabilities')=={CAPABILITY:expected})
    return expected


def derive_member(image,pins,parent_source,member_index=7):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.levelscript_condition_param_sources import derive_many,CAP_PREFIX
    need('own-source-and-finite-field',parent_source.get('nativeInputs')==pins and parent_source.get('wrappedType')in OWNERS
        and parent_source.get('wrapperName')==OWNERS[parent_source['wrappedType']] and parent_source.get('completeSelectedCallerAdmitted')is True
        and type(member_index)is int and member_index==7)
    read=parent_source['orderedSourceReads'][member_index]
    need('own-Boolean-array-field',(read['fieldName'],read['declaredType'])==('_list',TYPE))
    usage=derive_typed_usage_context(image,read['context']['instructionRva'],label='booleanParamArray.actualCaller')
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-owned-E8',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==read['sourceTargetRva'])
    image.check_instruction_windows([read['instruction']],label='booleanParamArray.actualCaller')
    source=parent_source['sourceScope']['arraySources'][str(member_index)]
    array_source.validate_source(source,pins)
    need('same-fresh-actual-array-request',source.get('typedRequest')==usage and source.get('arrayReaderTargetRva')==read['sourceTargetRva'])
    children=derive_many(image,pins,['bool']);child=children['capabilities'][CAP_PREFIX+ELEMENT]
    result=dict(schema=SCHEMA,status='validated-conditional-boolean-Param-array',nativeInputs=pins,
        capabilities={CAPABILITY:capability(child,source)},proof=dict(source=source,ParamSource=children),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,sourceReceiptAuthority=False,currentVfsCorpus=False)
    result=json.loads(json.dumps(result));validate_component(result,pins);return result


def bind_member(owner,scope,read,pins,usage,component,selected):
    cap=validate_component(component,pins,selected);actual=component['proof']['source'];index=read['memberIndex']
    need('own-complete-parent-and-source',owner.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and owner.get('nativeInputs')==pins and owner.get('wrappedType')in OWNERS
        and owner.get('wrapperName')==OWNERS[owner['wrappedType']]
        and owner.get('completeSelectedCallerAdmitted')is True and owner.get('sourceScope')==scope
        and type(index)is int and index==7 and read.get('fieldName')=='_list'and read.get('declaredType')==TYPE
        and read.get('kind')=='reference:'+TYPE and read.get('mode')=='typed-Param-reference-array'
        and owner['orderedSourceReads'][index]==scope['events'][index]==read
        and scope.get('arraySources',{}).get(str(index))==actual and actual['typedRequest']==usage
        and read.get('sourceTargetRva')==cap['sourceTargetRva'])
    context=read['context'];raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('own-closed-Boolean-ReadArray-context',len(raw)==16 and raw[10:12]==bytes((21,0))
        and(context.get('methodOwner'),context.get('methodName'),context.get('fullTypeName'),context.get('register'),context.get('typeKind'))==
            ('MemoryPack.MemoryPackReader','ReadArray',ELEMENT,'rdx',21)
        and tuple(context.get(k)for k in('instructionRva','instructionHex','methodSpec'))==tuple(usage.get(k)for k in('instructionRva','instructionHex','methodSpec')))
    at,h=read['instruction'];raw=bytes.fromhex(h)
    need('actual-owned-array-E8',len(raw)==5 and raw[0]==232 and at+5+int.from_bytes(raw[1:],'little',signed=True)==cap['sourceTargetRva'])
    rich=scope['richProgram'];flows=[r for r in rich['sources']if r.get('memberIndex')==index]
    stores=[r for r in rich['fieldStores']if r.get('memberIndex')==index];setter=owner['setters'][index]
    need('whole-owned-reference-to-named-setter',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
        and len(stores)==1 and(stores[0].get('sourceOffset'),stores[0].get('storedBytes'))==(0,8)
        and stores[0].get('instruction')in scope['selectedProgram']and scope['richSetters'][index]==setter
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==8
        and setter.get('method',[None,None,None])[2]=='set____list__'and setter.get('codeWindows'))
    at,h=stores[0]['instruction'];raw=bytes.fromhex(h)
    need('actual-named-setter-call',len(raw)==5 and raw[0]in(232,233)
        and at+5+int.from_bytes(raw[1:],'little',signed=True)==setter['method'][3])
    paths=owner['programs']
    need('all-four-complete-parent-frames',len(paths)==4
        and {(p.get('existing'),p.get('wrapperNull'))for p in paths}=={(n,f)for n in(False,True)for f in(False,True)}
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True and p['frame'].get('allWin64IntegerNonvolatilesRestored')is True for p in paths))
    return dict(fieldName='_list',typeName=TYPE,capability=CAPABILITY,readerMethodDefinition=cap['readerMethodDefinition'],
        sourceTargetRva=cap['sourceTargetRva'],sourceReferenceKind=21,referenceOutputBytes=8,
        elementType=ELEMENT,closedCarrierProved=True,actualCallbackEqualsProvedChildRequired=True,
        parentArgumentLocalStoreFrameRequired=True,parentFieldAdmitted=False)
