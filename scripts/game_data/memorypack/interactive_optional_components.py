"""Variant's four exact closed managed Optionals and their parent transfers.

The native hidden16 return is a managed representation, never a wire width.
The independently derived Optional source owns MC2/FF, its named fields and
adapter/default conversion. Every populated nested array still needs its own
array/element proof; this join alone grants no enclosing grammar or EOF.
"""
from scripts.game_data.memorypack import interactive_parent_bindings as parent
from scripts.game_data.memorypack import interactive_value_layouts as layouts

TYPE='Beyond.Gameplay.Core.InteractiveTemplateVariant'
FIELDS={1:('bornTag','Beyond.Gameplay.Core.GameplayTag[]'),11:('modelId','string'),
        12:('mountPoints',layouts.MOUNT+'[]'),13:('relatedGuideTimestampGameVar','string[]')}


def need(check,condition):
    if not condition:raise ValueError('interactiveOptionalComponents.'+check)


def bind_member(source,read,pins):
    from scripts.game_data.memorypack.generated_inline_record_components import _coverage
    scope=parent.source_scope(source,pins);index=read.get('memberIndex');name=read.get('declaredType')
    need('four-exact-own-closed-Optionals',source.get('wrappedType')==TYPE and index in FIELDS
        and (read.get('fieldName'),name)==(FIELDS[index][0],layouts.OPTIONAL+FIELDS[index][1]+'>')
        and scope['events'][index]==read and read.get('kind')=='managed:'+name
        and read.get('mode')=='typed-managed-value'and read.get('resultAbi')=='hidden-local'
        and read.get('managedBytes')==16 and read.get('referenceLaneOffsets')==[8]
        and read.get('actualSourceProved')is True and 'wireBytes'not in read)
    child=scope.get('managedValueSources',{}).get(str(index),{});c=read.get('context',{})
    p=child.get('proof',{});layout=p.get('layout',{});closed=layout.get('nominal',{}).get('carrier',{})
    raw=bytes.fromhex(c.get('argumentRawHex',''));carrier=bytes.fromhex(closed.get('rawHex',''))
    need('same-independently-owned-closed-ReadValue-source',child.get('schema')=='endfield.interactive-managed-optional-read-source.v1'
        and child.get('nativeInputs')==pins and child.get('typeName')==name
        and child.get('managedBytes')==16 and child.get('referenceLaneOffsets')==[8]
        and child.get('resultAbi')=='hidden-local'and child.get('actualSourceProved')is True
        and child.get('wireGrammarAdmitted')is False and child.get('parentFieldAdmitted')is False
        and child.get('wholeOwnerAdmitted')is False and child.get('providerSelectionObserved')is False
        and child.get('readerMethodDefinition')==c.get('methodSpec',[None])[0]
        and child.get('sourceTargetRva')==read.get('sourceTargetRva'))
    need('actual-closed-value21-MVAR-context',len(raw)==len(carrier)==16
        and raw[10:12]==carrier[10:12]==bytes((21,128))and raw[:8]==carrier[:8]
        and(c.get('fullTypeName'),c.get('methodOwner'),c.get('methodName'),c.get('register'),c.get('typeKind'))
            ==(name,'MemoryPack.MemoryPackReader','ReadValue','r8',21)
        and(p.get('typedRequest',{}).get('instructionRva'),p['typedRequest'].get('instructionHex'),p['typedRequest'].get('methodSpec'))
            ==(c.get('instructionRva'),c.get('instructionHex'),c.get('methodSpec')))
    parent._call(read['instruction'],child['sourceTargetRva'])
    setter=source['setters'][index];program=setter.get('program',{})
    need('own-complete-managed-layout-and-setter',layout==setter.get('managedValueLayout')
        and layout.get('nativeInputs')==pins and layout.get('typeName')==name
        and layout.get('managedBytes')==16 and layout.get('referenceLaneOffsets')==[8]
        and layout.get('openGenericOffsetsUsed')is False and layout.get('wholeValueBitsAndPaddingPreserved')is True
        and setter.get('storedBytes')==16 and setter.get('incomingValueStoredUnchanged')is True
        and setter.get('member',{}).get('declaredType')==name
        and setter['member'].get('name')==read['fieldName']and setter.get('targetField')==TYPE+'::'+read['fieldName']
        and program.get('storedBytes')==program.get('managedBytes')==16
        and program.get('referenceLaneOffsets')==[8]and program.get('barrierReferenceLaneOffset')==8
        and program.get('wholeInputBitsStoredUnchanged')is True and program.get('disabledCollectorRequired')is True
        and program.get('entryRspRestored')is True
        and(program.get('normalReturn')is True or program.get('normalReturnViaBarrier')is True))
    rich=scope.get('richProgram',{});stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
    flows=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
    hidden=[r for r in rich.get('hiddenSourceLocals',[])if r.get('memberIndex')==index]
    need('whole-native-managed-value-and-padding-transfer',rich.get('completeSelectedNormalProgram')is True
        and rich.get('selectedProgram')==scope.get('selectedProgram')
        and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='hidden-local')]
        and _coverage(stores,16,'sourceOffset','storedBytes')
        and all(r.get('instruction')in rich['selectedProgram']for r in stores)
        and len(hidden)==1 and hidden[0].get('bytes')==16
        and hidden[0].get('sourceInstruction')==read['instruction'])
    for path in source['programs']:
        if path['wrapperNull']:continue
        life,=[r for r in path['frame'].get('hiddenSourceLocalLifetimes',[])if r.get('memberIndex')==index]
        need('both-complete-frames-own-this-exact-hidden-lifetime',
            all(life.get(k)==hidden[0].get(k)for k in('displacement','bytes','sourceInstruction'))
            and life.get('fieldStores')==stores and life.get('completeIndependentSourceFlowRequired')is True
            and read['instruction']in path['selectedProgram']
            and all(r['instruction']in path['selectedProgram']for r in stores))
    wrapper=p.get('wrapperSource',{})
    schema={1:'endfield.interactive-tag-optional-source.v1',12:'endfield.interactive-mount-optional-source.v1'}.get(
        index,'endfield.interactive-inline-value-wrapper-source.v1')
    need('own-independent-complete-wrapper-and-layout',wrapper.get('schema')==schema and wrapper.get('nativeInputs')==pins
        and wrapper.get('typeName')==name and wrapper.get('layout')==layout
        and wrapper.get('completeSelectedCallerAdmitted')is True and wrapper.get('childGrammarAdmitted')is False
        and wrapper.get('wholeOwnerAdmitted')is False)
    return dict(typeName=name,memberIndex=index,fieldName=read['fieldName'],managedBytes=16,
        referenceLaneOffsets=[8],sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva'],
        typedRequest=p['typedRequest'],wholeManagedValueAndPaddingStored=True,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)
