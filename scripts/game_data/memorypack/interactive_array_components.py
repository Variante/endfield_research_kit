"""The four root arrays keep their own element and native source identities.

GameplayTag is a proved raw4 bulk copy, components are reference callbacks,
NameMountPointDef is an independent managed16/headered-value conversion, and
STRING14 uses pooled indices. No managed stride is reused as a wire width.
This joins source and parent only; selected component bodies remain separate.
"""
from scripts.game_data.memorypack import interactive_parent_bindings as parent

TYPE='Beyond.Gameplay.InteractiveTemplateData'
FIELDS={3:('bornTag','Beyond.Gameplay.Core.GameplayTag[]'),
        4:('componentList','Beyond.Gameplay.BaseComponentData[]'),
        17:('mountPoints','Beyond.Gameplay.View.NameMountPointDef[]'),
        20:('relatedGuideTimestampGameVar','string[]')}


def need(check,condition):
    if not condition:raise ValueError('interactiveArrays.'+check)


def bind_member(source,read,pins):
    scope=parent.source_scope(source,pins);index=read.get('memberIndex');name=read.get('declaredType')
    need('four-own-root-array-fields',source.get('wrappedType')==TYPE and index in FIELDS
        and(read.get('fieldName'),name)==FIELDS[index]and scope['events'][index]==read)
    transfer=(parent.bind_value_array_result if index in(3,17)else parent.bind_reference_result)(source,read,pins)
    actual=scope.get('arraySources',{}).get(str(index),{});context=read.get('context',{})
    need('own-independent-current-array-source',actual.get('nativeInputs')==pins)
    if index==3:
        need('own-raw-GameplayTag-bulk-copy',actual.get('schema')=='endfield.skill-gameplay-tag-array-source.v1'
            and actual.get('status')=='validated-conditional-components')
        cap=actual.get('capabilities',{}).get('skill-root-gameplay-tag-array',{})
        need('raw-four-byte-tags-and-independent-copy-bound',cap.get('closedArrayType')==name
            and cap.get('elementType')==name[:-2]and cap.get('elementWireBytes')==4
            and cap.get('bulkCopyProved')is True and cap.get('countLimit')==64
            and cap.get('elementGrammarAdmitted')is True
            and actual['capabilities'].get('skill-root-gameplay-tag-raw4',{}).get('wholeGrammarAdmitted')is True)
        usage=actual['proof']['context']['typedRequest'];operation='raw-GameplayTag-array';limit=64
    elif index==4:
        cap=actual;usage=actual.get('typedRequest',{});operation='component-reference-array';limit=4096
        need('own-component-reference-array',actual.get('schema')=='endfield.skill-reference-array-component.v1'
            and actual.get('status')=='validated-conditional-reference-array-component'
            and actual.get('closedArrayType')==name and actual.get('elementType')==name[:-2]
            and actual.get('elementValueType')is False and actual.get('elementGrammarAdmitted')is False
            and actual.get('positiveCountsAdmitted')is True and actual.get('nullable')is True
            and type(actual.get('countLimit'))is int and actual['countLimit']>=limit)
    elif index==17:
        cap=actual;usage=actual.get('typedRequest',{});operation='mount-point-value-array';limit=4096
        need('own-managed-mount-point-array',actual.get('schema')=='endfield.interactive-mount-point-array-source.v1'
            and actual.get('typeName')==name and actual.get('elementType')==name[:-2]
            and actual.get('elementManagedBytes')==16 and actual.get('elementWireBytes')is None
            and actual.get('elementValueType')is True and actual.get('actualSourceProved')is True
            and actual.get('elementGrammarAdmitted')is False and actual.get('resultAbi')=='rax'
            and actual.get('countRange')==[-1,limit]and actual.get('initiallyNullArrayRequired')is True)
    else:
        cap=actual.get('capability',{});usage=actual.get('proof',{}).get('typedRequest',{})
        operation='pooled-string-array';limit=4096
        need('own-pooled-STRING14-array',actual.get('schema')=='endfield.story-pooled-string-array-component.v1'
            and cap.get('typeName')==name and cap.get('elementType')=='string'and cap.get('elementRawKind')==14
            and cap.get('elementWireBytes')==4 and cap.get('managedElementBytes')==8
            and cap.get('wholeGrammarAdmitted')is True and cap.get('elementGrammarAdmitted')is True
            and cap.get('countRange')==[-1,limit]and cap.get('initiallyNullArrayRequired')is True)
    need('same-actual-own-ReadArray-request',tuple(usage.get(k)for k in
        ('tag','typeName','methodName','classArguments','methodArguments'))==
            (6,'MemoryPack.MemoryPackReader','ReadUnmanagedArray'if index==3 else'ReadArray',[],[name[:-2]])
        and(usage.get('instructionRva'),usage.get('instructionHex'),usage.get('methodSpec'))==
            (context.get('instructionRva'),context.get('instructionHex'),context.get('methodSpec'))
        and cap.get('arrayReaderMethodDefinition')==usage['methodSpec'][0]
        and cap.get('arrayReaderTargetRva')==read.get('sourceTargetRva'))
    need('literal-native-reader-and-count-bounds',type(cap.get('arrayReaderMethodDefinition'))is int
        and type(cap.get('arrayReaderTargetRva'))is int and type(cap.get('countLimit'))is int
        and cap['countLimit']>=limit)
    return dict(transfer,operation=operation,countRange=[-1,limit],elementType=name[:-2],
        typedRequest=usage,elementGrammarAdmitted=index in(3,20),parentFieldAdmitted=False,wholeOwnerAdmitted=False)
