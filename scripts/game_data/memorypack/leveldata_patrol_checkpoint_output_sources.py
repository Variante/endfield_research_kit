"""Checkpoint direct Int32 output request sources, without live setter effects.

The selected ordinary delegate program preserves the supplied Int32, receiver
and MethodInfo. Its actual target and property effect require live identity.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as helpers
from scripts.game_data.memorypack.pooled_string_list_sources import flag

SCHEMA='endfield.story-patrol-checkpoint-output-sources.v2'


def need(check,condition):
    if not condition:raise ValueError('patrolCheckpointOutput.'+check)


def predicate_program(regions,entry,*,direct):
    need('literal-predicate-selection',type(direct)is bool)
    g=BytesPath(regions,entry);g.take('83791000');g.branch('75',not direct,1)
    g.take('b001'if direct else'32c0','c3')
    return dict(selectedBytes=g.seen,discriminatorOffset=16,requiredDiscriminatorZero=direct,
        returnsLiteral=direct,entryRspAndNonvolatilesUntouched=True,memoryWrites=0)


def setter_program(regions,entry,*,invoke,bound=True,setter_present=True,label='null'):
    need('finite-setter-branch',type(bound)is bool and type(setter_present)is bool and label in('null','empty')
        and(bound or not setter_present))
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20');ready=flag(g)
    g.take('498bf8','8bf2','488bd9');g.branch('74',False,1)
    g.take('488b4720','488b88c0000000','488b01','4883782000');g.branch('0f84',False)
    g.take('807b6800');g.branch('0f84',not bound)
    if bound:g.take('48837b6000');g.branch('0f84',not setter_present)
    invoked=bound and setter_present
    if invoked:
        g.take('488b5b60','4885db');g.branch('74',False,1)
        g.take('488b4720','488b90c0000000','488b4228','4883782000');g.branch('0f84',False)
        g.take('488b4720','8bd6','488bcb','4c8b80c0000000','4d8b4028');g.call(invoke)
    else:
        g.take('488b4318','4885c0');g.branch('0f84',label=='null')
        if label=='empty':g.take('83781000');g.branch('0f86',True)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlagVa=ready,bound=bound,setterPresent=setter_present,label=label,
        bindingByteOffset=104,setterReferenceOffset=96,labelReferenceOffset=24,
        classContextOffset=192,classReadinessSlot=0,delegateInvokeContextSlot=5,
        delegateInvoked=invoked,delegateArguments=dict(rcx='same selected setter reference',
            edx='same incoming Int32 bits',r8='same declaring class context slot5')if invoked else None,
        noEffectCallsOnSelectedInertBranch=not invoked,entryRspRestored=True,frameBytes=40,callShadow=[0,32],
        restoredNonvolatiles=['rbx','rsi','rdi'],actualDelegateTargetOrEffectProved=False,
        condition='Ready metadata and stable own declaring class context; compatible nonnull ParamOutput<int>; chosen binding/setter/empty-label branch; normal Win64 delegate ABI. Nonempty logging paths and alternate class/setup paths are independent.')


def ordinary_delegate_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2420','57','4883ec30','488b4118','8bda','4c8b4128','488b7940')
    excluded=[g.relative('488d0d')];g.take('483bc1');g.branch('74',False,1)
    g.take('48896c2440');excluded.append(g.relative('488d0d'))
    g.take('4889742448','4c89742450','483bc1');g.branch('0f84',False)
    excluded.append(g.relative('488d0d'));g.take('483bc1');g.branch('0f84',False)
    g.take('488bcf','ffd0','488b742448','488b6c2440','4c8b742450','488b5c2458','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,excludedInlineTargets=excluded,
        invokePointerFieldOffset=24,methodInfoFieldOffset=40,targetReferenceFieldOffset=64,
        arguments=dict(rcx='same incoming delegate target reference',edx='same incoming Int32 bits',r8='same incoming delegate MethodInfo field'),
        indirectInvocationCount=1,entryRspRestored=True,frameBytes=56,callShadow=[0,32],
        restoredNonvolatiles=['rbx','rbp','rsi','rdi','r14'],actualCallbackIdentityObserved=False,
        condition='Compatible stable System.Action<int> delegate whose invoke pointer is distinct from all three explicit inlined callbacks; stable target/context and normal Win64 ABI. No callback target or effect is inferred from delegate shape.')


def _leaf_packet(image,at):
    import hashlib
    from scripts.game_data.il2cpp.closed_leaf_entry import decode_closed_leaf_entry
    decoded=decode_closed_leaf_entry(image.mapper,image.pe.bytes_at_va(at,128),at)
    raw=b''.join(bytes.fromhex(r['bytes'])for r in decoded['rows']);base=image.pe.image_base
    need('actual-closed-leaf-contiguous-bytes',image.pe.bytes_at_va(at,len(raw))==raw)
    return dict(entryRva=at-base,windows=[dict(startRva=at-base,endRva=at-base+len(raw),sha256=hashlib.sha256(raw).hexdigest().upper())],
        regions=[[at-base,raw.hex().upper()]],physicalFunctionExtentProved=False)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    _publication_gate(image,pins);parent=helpers.derive(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    symbols=parent['proof']['helpers']['outputId']['symbolRvas'];predicate=_leaf_packet(image,base+symbols['isDirect'])
    setter=helpers.packet(image,base+symbols['setDirect']);body=owned(image,base+setter['entryRva'])
    calls=helpers._calls([r for r in body['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'])
    invoke=next(target for offset,target in calls if offset==133);delegate=helpers.packet(image,invoke)
    class_owner=ctx.index.types['Beyond.Gameplay.Actions.ParamOutput`1']
    context=ContextSymbols(image).context(class_owner.index)
    slot=next(r for r in context['entries']if r['relativeSlot']==5)
    need('own-Action-Invoke-class-slot',(slot['kind'],slot.get('typeName'),slot.get('methodName'))==(3,'System.Action`1','Invoke'))
    actual_entries=GenericEntries(image).observe(slot['methodSpec'][0],['int'],[])
    p=ContextSymbols(image).context(class_owner.index,slots=[0,5])
    modes=[dict(bound=True,setter_present=True)]+[dict(bound=b,setter_present=False,label=l)for b in(False,True)for l in('null','empty')]
    result=dict(schema=SCHEMA,status='validated-conditional-direct-output-request-sources',nativeInputs=pins,
        proof=dict(imageBase=base,helperSource=parent,predicate=predicate,setter=setter,delegate=delegate,
            invokeTargetRva=invoke-base,declaringClassContext=p,invokeRegistrations=actual_entries,
            invokeCanonicalPointerEquivalenceProved=False,
            predicatePrograms=[predicate_program(helpers.regions(predicate,base),base+predicate['entryRva'],direct=v)for v in(False,True)],
            setterPrograms=[setter_program(helpers.regions(setter,base),base+setter['entryRva'],invoke=invoke,**mode)for mode in modes],
            ordinaryDelegateProgram=ordinary_delegate_program(helpers.regions(delegate,base),invoke)),
        directPredicateByteEffectsProved=True,selectedInertSetterReturnsAndBoundRequestSourcesProved=True,
        selectedOrdinaryDelegateArgumentsAndFrameProved=True,actualOutputPropertyEffectProved=False,
        checkpointFilterProved=False,runtimeInvocationObserved=False,playbackProved=False,
        evidenceBoundary=dict(exact='Own direct-output discriminator Bool, unbound/absent setter with null or empty label returns, complete bound setter request and ordinary delegate arguments/normal frame.',
            conditional='Own ready class context, selected binding/inert-label domain and exact non-inlined stable delegate invoke/target/MethodInfo; every helper returns normally.',
            unresolved=['Actual delegate target, property binding and storage effect require live identity','three explicit optimized delegate targets, nonempty logging and other output/Param modes are separate source alternatives','actual event invocation and playback']))
    result=json.loads(json.dumps(result));validate(result);_publication_gate(image,pins);return result


def validate(value):
    need('schema',value.get('schema')==SCHEMA);p=value['proof'];base=p['imageBase'];helpers.validate(p['helperSource'])
    for name in('predicate','setter','delegate'):helpers.verify_packet(p[name])
    symbols=p['helperSource']['proof']['helpers']['outputId']['symbolRvas']
    need('own-output-callee-entry-joins',p['predicate']['entryRva']==symbols['isDirect']and p['setter']['entryRva']==symbols['setDirect'])
    actual=[predicate_program(helpers.regions(p['predicate'],base),base+p['predicate']['entryRva'],direct=v)for v in(False,True)]
    need('complete-predicate-program-replay',json.loads(json.dumps(actual))==p['predicatePrograms'])
    modes=[dict(bound=True,setter_present=True)]+[dict(bound=b,setter_present=False,label=l)for b in(False,True)for l in('null','empty')]
    actual=[setter_program(helpers.regions(p['setter'],base),base+p['setter']['entryRva'],invoke=base+p['invokeTargetRva'],**mode)for mode in modes]
    need('complete-setter-program-replay',json.loads(json.dumps(actual))==p['setterPrograms'])
    need('own-delegate-target-join',p['delegate']['entryRva']==p['invokeTargetRva'])
    actual=ordinary_delegate_program(helpers.regions(p['delegate'],base),base+p['delegate']['entryRva'])
    need('complete-ordinary-delegate-replay',json.loads(json.dumps(actual))==p['ordinaryDelegateProgram'])
    need('selected-declaring-class-context',p['declaringClassContext'].get('typeName')=='Beyond.Gameplay.Actions.ParamOutput`1'
        and p['declaringClassContext'].get('isMethod')is False and p['declaringClassContext'].get('selectedSlots')==[0,5])
    context=p['declaringClassContext'];entries=context['entries']
    need('own-complete-selected-context-entries',len(entries)==2 and[r.get('relativeSlot')for r in entries]==[0,5])
    arguments=[]
    for row,owner,name in((entries[0],'Beyond.Gameplay.Actions.ParamOutput`1','get_variableBind'),(entries[1],'System.Action`1','Invoke')):
        need('own-class-slot-declaration-'+name,(row.get('kind'),row.get('typeName'),row.get('methodName'))==(3,owner,name)
            and row.get('methodArguments')==[] and len(row.get('classArguments',[]))==1)
        arg=row['classArguments'][0];raw=bytes.fromhex(arg.get('rawHex',''));identity=arg.get('parameterOwner',{})
        need('own-reciprocal-class-argument-'+name,len(raw)==16 and raw[10:12]==bytes((19,0))
            and identity.get('typeIndex')==context['definition']and identity.get('ordinal')==0
            and identity.get('typeName')==context['typeName']and identity.get('parameterIndex')==int.from_bytes(raw[:8],'little'))
        arguments.append(arg)
    need('same-actual-class-argument-and-no-pointer-alias',arguments[0]==arguments[1]
        and p.get('invokeCanonicalPointerEquivalenceProved')is False)
    need('source-only-flags',all(value.get(k)is True for k in('directPredicateByteEffectsProved',
        'selectedInertSetterReturnsAndBoundRequestSourcesProved','selectedOrdinaryDelegateArgumentsAndFrameProved'))
        and all(value.get(k)is False for k in('actualOutputPropertyEffectProved','checkpointFilterProved','runtimeInvocationObserved','playbackProved')))
    return value
