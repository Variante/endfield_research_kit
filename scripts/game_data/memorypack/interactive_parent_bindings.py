"""Complete generated Interactive parent transfers, without child admission.

Only freshly derived complete callers can use this join. Ordinary RAX
references have two explicit profiles: a source-to-named-setter call, or the
owned rich program's complete reference store. Static out parameters and
hidden managed values have different owners and never enter this path.
"""


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveParent.'+check+':'+str(detail)[:900])


def source_scope(source,pins):
    need('complete-own-current-source',source.get('schema')=='endfield.generated-concrete-reader-source.v1'
        and source.get('nativeInputs')==pins and source.get('completeSelectedCallerAdmitted')is True
        and source.get('childGrammarAdmitted')is False and source.get('wholeOwnerAdmitted')is False)
    scope=source.get('sourceScope',{});reads=source.get('orderedSourceReads',[])
    need('same-native-reader-and-ordered-fields',scope.get('nativeInputs')==pins
        and scope.get('wrappedType')==source.get('wrappedType')
        and scope.get('wrapperName')==source.get('wrapperName')
        and source.get('method')==scope.get('method')==source.get('lifecycle',{}).get('readerMethod')
        and scope.get('sourceScopeAdmitted')is True and scope.get('events')==reads
        and type(scope.get('memberCount'))is int and len(reads)==scope['memberCount']
        and [r.get('memberIndex')for r in reads]==list(range(len(reads)))
        and len(source.get('setters',[]))==len(reads))
    paths=source.get('programs',[])
    need('four-owned-complete-frames',len(paths)==4
        and all(type(p.get('existing'))is bool and type(p.get('wrapperNull'))is bool
            and p.get('frame',{}).get('entryRspRestored')is True
            and p.get('frame',{}).get('allWin64IntegerNonvolatilesRestored')is True for p in paths)
        and {(p['existing'],p['wrapperNull'])for p in paths}=={(False,False),(False,True),(True,False),(True,True)})
    return scope


def _call(instruction,target):
    need('literal-E8',isinstance(instruction,(list,tuple))and len(instruction)==2
        and type(instruction[0])is int and type(instruction[1])is str)
    raw=bytes.fromhex(instruction[1])
    need('exact-E8-target',len(raw)==5 and raw[0]==232
        and instruction[0]+5+int.from_bytes(raw[1:],'little',signed=True)==target)


def bind_reference_result(source,read,pins):
    return _bind_reference_result(source,read,pins,value_array=False)


def bind_value_array_result(source,read,pins):
    """Only the root's two independently owned value-element arrays."""
    fields={3:('bornTag','Beyond.Gameplay.Core.GameplayTag[]'),
        17:('mountPoints','Beyond.Gameplay.View.NameMountPointDef[]')}
    index=read.get('memberIndex')
    need('finite-own-value-array-field',source.get('wrappedType')=='Beyond.Gameplay.InteractiveTemplateData'
        and index in fields and(read.get('fieldName'),read.get('declaredType'))==fields[index]
        and read.get('context',{}).get('methodName')==('ReadUnmanagedArray'if index==3 else'ReadArray')
        and read.get('context',{}).get('typeKind')==17)
    return _bind_reference_result(source,read,pins,value_array=True)


def _bind_reference_result(source,read,pins,*,value_array):
    """Prove the whole returned reference reaches its own named field."""
    from scripts.game_data.memorypack.generated_inline_record_components import _coverage
    scope=source_scope(source,pins);index=read.get('memberIndex')
    need('own-actual-reference-member',type(index)is int and 0<=index<len(scope['events'])
        and scope['events'][index]==read and read.get('kind')=='reference:'+read.get('declaredType','')
        and read.get('mode')not in('typed-static-out-reference','typed-hidden-value')
        and read.get('resultAbi','rax')=='rax')
    context=read.get('context')or{}
    need('own-typed-returning-reference-request',context.get('fullTypeName')in
        (read['declaredType'],read['declaredType'][:-2]if read['declaredType'].endswith('[]')else read['declaredType'])
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')in(('ReadArray','ReadUnmanagedArray')if value_array else('ReadValue','ReadPackable','ReadArray'))
        and context.get('register')=='rdx'and context.get('typeKind')in((17,)if value_array else(14,18,21)))
    _call(read['instruction'],read['sourceTargetRva'])
    setter=source['setters'][index]
    need('same-owned-named-setter',setter.get('member',{}).get('name')==read['fieldName']
        and setter['member'].get('declaredType')==read['declaredType']
        and setter.get('incomingValueStoredUnchanged')is True and setter.get('storedBytes')==8
        and type(setter.get('fieldOffset'))is int)
    selected=scope.get('selectedProgram',[])
    need('source-call-in-complete-program',read['instruction']in selected)
    rich=scope.get('richProgram')
    if rich is not None:
        flows=[r for r in rich.get('sources',[])if r.get('memberIndex')==index]
        stores=[r for r in rich.get('fieldStores',[])if r.get('memberIndex')==index]
        need('whole-rich-reference-flow',rich.get('completeSelectedNormalProgram')is True
            and rich.get('selectedProgram')==selected
            and flows==[dict(memberIndex=index,instruction=read['instruction'],resultAbi='rax')]
            and _coverage(stores,8,'sourceOffset','storedBytes')
            and all(s.get('instruction')in selected for s in stores))
        instructions=[s['instruction']for s in stores];profile='owned-rich-reference-store'
    else:
        transfer,=[r for r in scope.get('setterTransfers',[])if r.get('memberIndex')==index]
        need('same-return-and-named-destination',transfer.get('sourceCall')==read['instruction']
            and transfer.get('returnAbi')=='rax'and transfer.get('setterTargetRva')==setter['method'][3]
            and transfer.get('wrapperLoad')in selected)
        if 'transferProgram'in transfer:
            from scripts.game_data.memorypack.generated_member_sources import _store_encoding
            field=setter['fieldOffset'];instructions=transfer['transferProgram'];store=transfer.get('store')
            need('owned-direct-holder-inline-reference',transfer.get('profile')=='direct-holder-inline-store'
                and transfer.get('normalWholeSourceValueStoredUnchanged')is True
                and transfer.get('fieldOffset')==field and transfer.get('storedBytes')==8
                and transfer.get('fieldGetter')is None and transfer.get('sourceReturnSaved')is None
                and setter.get('getter')is None and setter.get('profile')=='direct-base-holder-setter'
                and setter.get('program',{}).get('holderOffset')==16
                and bool(instructions)and store in instructions
                and bytes.fromhex(store[1])==_store_encoding('rcx','rax',field,8))
            start=selected.index(read['instruction'])+1
            need('complete-inline-source-to-store-instruction-range',selected[start:start+len(instructions)]==instructions)
            calls=transfer.get('actualCalls',[]);tail=transfer.get('referenceBarrierTail')
            need('complete-inline-reference-barrier-handoff',
                (bool(calls)and calls[-1]==instructions[-1]or tail==instructions[-1])
                and all(call in instructions for call in calls)
                and setter.get('program',{}).get('normalReturnViaBarrier')is True)
            profile='owned-direct-holder-inline-reference'
        else:
            need('whole-RAX-to-RDX-reference-transfer',transfer.get('transfer',[None,None])[1]=='488BD0'
                and transfer['transfer']in selected and transfer.get('setterCall')in selected)
            _call(transfer['setterCall'],setter['method'][3])
            instructions=[transfer['transfer'],transfer['setterCall']];profile='owned-reference-setter-call'
    for path in source['programs']:
        if path['wrapperNull']:continue
        need('same-source-and-transfer-in-both-positive-paths',read['instruction']in path['selectedProgram']
            and all(i in path['selectedProgram']for i in instructions))
    return dict(typeName=read['declaredType'],fieldName=read['fieldName'],memberIndex=index,
        sourceInstruction=read['instruction'],sourceTargetRva=read['sourceTargetRva'],
        sourceContext=context,referenceBytes=8,wholeReferenceStored=True,transferProfile=profile,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def fresh_request(image,read):
    """Authenticate the actual caller's MethodInfo instruction and E8."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    c=read.get('context')or{}
    need('literal-owned-context',type(c.get('instructionRva'))is int)
    usage=derive_typed_usage_context(image,c['instructionRva'],label='interactiveParent.actualRequest')
    need('same-actual-closed-MethodInfo',usage.get('methodSpec')==c.get('methodSpec')
        and usage.get('instructionHex')==c.get('instructionHex'))
    _call(read['instruction'],read['sourceTargetRva'])
    image.check_instruction_windows([read['instruction']],label='interactiveParent.actualE8')
    return usage
