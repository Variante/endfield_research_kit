"""Cached constructors with two exact inline compatible-class checks.

Current allocation, Original constructor, both holder declarations and each
typed class usage must be joined by the caller. The successful class predicate
and normal helper effects are conditions; no runtime outcome is observed.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

def need(k,condition):
    if not condition:raise ValueError('generatedInlineCastFactory.'+k)

def constructor_program(regions,entry,barrier,*,original_ctor,base_slot,cache_slot):
    from scripts.game_data.memorypack import generated_lifecycle_sources as life
    need('explicit-current-constructor-and-holder-slots',(original_ctor is None or type(original_ctor)is int and original_ctor>0)and 16<=base_slot<cache_slot<128)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    if bytes(g.bytes.get(entry+i,0)for i in range(2))==b'\x40\x53':
        need('r9-constructor-does-not-invoke-original',original_ctor is None)
        return r9_holder_constructor_program(regions,entry,barrier,base_slot=base_slot,cache_slot=cache_slot)
    g.take('48895c2410','57','4883ec20');flag=life._direct_flag(g,'803d');g.take('488bd9');life._initialized(g)
    site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);g.take('83b9e000000000');life._initialized(g)
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocator=g.relative('e8')
    g.take('488bf8','4885c0');life._nonnull(g)
    initialization=None
    if original_ctor is not None:
        g.take('33d2','4889742430','488bc8');g.call(original_ctor)
    else:
        fields=[];at=g.at;g.take('c740');offset=g.read(1)[0];constant=g.read(4).hex().upper()
        need('positive-original-disp8-field',16<=offset<128)
        fields.append(dict(instructionVa=at,object='original',offset=offset,bytes=4,constantHex=constant))
        site=g.at;cell=g.relative('488b0d');child=dict(site=site,cell=cell);g.call(allocator);g.take('4885c0');life._nonnull(g)
        at=g.at;g.take('c640');offset=g.read(1)[0];constant=g.read(1).hex().upper()
        need('positive-child-disp8-field',16<=offset<128)
        fields.append(dict(instructionVa=at,object='child',offset=offset,bytes=1,constantHex=constant))
        g.take('488d4f');reference=g.read(1)[0];g.take('488947');need('same-complete-child-reference-field',g.read(1)[0]==reference)
        need('positive-child-reference-disp8-field',16<=reference<128)
        g.take('4889742430');g.call(barrier)
        at=g.at;g.take('c647');offset=g.read(1)[0];constant=g.read(1).hex().upper()
        need('positive-original-byte-disp8-field',16<=offset<128)
        fields.append(dict(instructionVa=at,object='original',offset=offset,bytes=1,constantHex=constant))
        initialization=dict(childAllocation=child,childReferenceOffset=reference,constantFields=fields,
            sameCompleteChildReferenceStored=True,originalRdiPreserved=True,originalConstructorInvoked=False)
    writes=[]
    for slot in(cache_slot,base_slot):
        d=bytes((slot,)).hex();at=g.at;g.take('488d4b'+d,'48897b'+d);g.call(barrier)
        writes.append(dict(offset=slot,bytes=8,sameAllocatedReference=True,programStart=at))
    g.take('488b7b'+b);usages=[];predicates=[];calls=[]
    site=g.at;cell=g.relative('488b35');usages.append(dict(site=site,cell=cell))
    g.take('4885ff');life._nonnull(g)
    for i in range(2):
        if i:
            site=g.at;cell=g.relative('488b35');usages.append(dict(site=site,cell=cell))
        g.take('488b0f','488bd6');at=g.at;predicates.append(g.relative('e8'));calls.append(at)
        g.take('84c0');life._nonnull(g)
        if not i:g.take('48897b'+c)
    need('same-current-class-and-predicate',len(set(predicates))==1 and all(u['cell']==allocation['cell']for u in usages))
    g.take('488d4b'+c,'488b742430','488b5c2438','4883c420','5f');need('same-restored-tail-barrier',g.relative('e9')==barrier)
    result=dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocator,
        baseClassUsage=ancestor,baseReady=None,instanceSetter=None,inlineHolderWrites=writes,
        strictCast=None,inlineStrictCasts=dict(predicateTarget=predicates[0],predicateCalls=calls,
            sameBaseReferenceCached=True,successfulPredicateConditional=True,runtimePredicateOutcomeObserved=False,
            referenceRegister='rdi',classRegister='rsi',entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi']),
        classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        originalConstructorCalled=original_ctor is not None,originalConstructorTarget=original_ctor,originalConstructorEffectsProved=False,
        normalReturnViaBarrier=True,
        condition=__doc__+' The normal nonnull typed allocation remains preserved through the independently owned Original constructor and disabled barriers. Each inline predicate compares that allocation class with the same current nominal Original class; the successful branch retains the entire same reference. Exact full frame and tail are owned.')
    if initialization is not None:
        result['inlinedNestedInitialization']=initialization
        result['condition']=__doc__+' Fresh exact Original and child allocations, independently current named scalar/child field declarations and selected disabled barriers. The child reference and each literal scalar store are owned explicitly; no Original or child constructor is invoked. Both same-class successful predicates and the full restored tail are owned.'
    return result


def r9_holder_constructor_program(regions,entry,barrier,*,base_slot,cache_slot):
    """Same freshly allocated reference in RAX/R9 across disabled barriers.

    The caller must prove both nominal holder fields and the actual barrier's
    disabled path. Its no-effect return preserves volatile R9; the general
    Win64 nonvolatile rule alone does not establish this transfer.
    """
    from scripts.game_data.memorypack import generated_lifecycle_sources as life
    need('r9-literal-holder-domain',type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    g.take('4053','4883ec20');flag=life._direct_flag(g,'803d');g.take('488bd9');life._initialized(g);ancestors=[]
    for _ in range(4):
        if life._peek(g,2)==b'\x80\x3d':life._direct_flag(g,'803d');life._initialized(g)
        site=g.at;cell=g.relative('488b0d');usage=dict(site=site,cell=cell)
        if life._peek(g,2)==b'\x83\xb9':
            g.take('83b9e000000000');life._initialized(g);ancestors.append(usage)
        else:
            allocation=usage;allocator=g.relative('e8');break
    else:raise ValueError('generatedInlineCastFactory.r9-bounded-current-ancestors')
    need('r9-own-ancestor-initialization',bool(ancestors))
    g.take('4c8bc8','4885c0');life._nonnull(g)
    g.take('4889742430');first=g.at;g.take('488d4b'+c,'48897c2438','488943'+c);g.call(barrier)
    second=g.at;g.take('488d4b'+b,'4c894b'+b);g.call(barrier)
    g.take('488b7b'+b);classes=[];predicates=[];calls=[]
    site=g.at;cell=g.relative('488b35');classes.append(dict(site=site,cell=cell))
    g.take('4885ff');life._nonnull(g)
    for i in range(2):
        if i:
            site=g.at;cell=g.relative('488b35');classes.append(dict(site=site,cell=cell))
        g.take('488b0f','488bd6');calls.append(g.at);predicates.append(g.relative('e8'));g.take('84c0');life._nonnull(g)
        if not i:g.take('48897b'+c)
    need('r9-same-current-class-and-predicate',len(set(predicates))==1 and all(u['cell']==allocation['cell']for u in classes))
    g.take('488d4b'+c,'488b742430','488b7c2438','4883c420','5b');need('r9-same-restored-tail-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocator,
        ancestorClassUsages=ancestors,baseClassUsage=None,baseReady=None,instanceSetter=None,
        inlineHolderWrites=[dict(offset=cache_slot,bytes=8,sameAllocatedReference=True,programStart=first),dict(offset=base_slot,bytes=8,sameAllocatedReference=True,programStart=second)],
        strictCast=None,inlineStrictCasts=dict(predicateTarget=predicates[0],predicateCalls=calls,sameBaseReferenceCached=True,
            successfulPredicateConditional=True,runtimePredicateOutcomeObserved=False,referenceRegister='rdi',classRegister='rsi',
            entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi']),classUsages=classes,
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,originalConstructorTarget=None,
        originalConstructorEffectsProved=False,disabledBarrierPreservesR9Required=True,normalReturnViaBarrier=True,
        condition=__doc__+' Exact typed normal allocation and disabled no-effect barriers preserve the entire same RAX/R9 reference across both holder writes. No Original constructor is called; initialized ancestor metadata, successful compatible-class predicates and full restored frame remain explicit conditions.')


def literal_class_factory_program(regions,entry,barrier,*,ctor,original_ctor,base_slot,cache_slot):
    """Actual holder setter followed by two literal nominal class equalities."""
    from scripts.game_data.memorypack import generated_lifecycle_sources as life
    need('literal-class-explicit-current-roles',type(ctor)is bool and type(original_ctor)is int and original_ctor>0 and
        type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20');flag=life._direct_flag(g,'803d');g.take('488bd9');life._initialized(g);ancestor=None
    if ctor:
        site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);g.take('83b9e000000000');life._initialized(g)
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocator=g.relative('e8')
    g.take('488bf8','4885c0');life._nonnull(g);g.take('33d2');receiver=life._peek(g,3)
    need('literal-original-receiver',receiver in(bytes.fromhex('488bc8'),bytes.fromhex('488bcf')));g.take(receiver.hex());g.call(original_ctor)
    g.take('4533c0','488bd7','488bcb');setter=g.relative('e8');g.take('488b4b'+b);classes=[];comparisons=[]
    site=g.at;cell=g.relative('488b15');classes.append(dict(site=site,cell=cell));g.take('4885c9');life._nonnull(g)
    comparisons.append(g.at);g.take('483911');g.branch('75',False,1)
    if ctor:g.take('48894b'+c)
    else:
        g.take('488bc1','488943'+c)
    site=g.at;cell=g.relative('488b15');classes.append(dict(site=site,cell=cell))
    if not ctor:g.take('4885c9');life._nonnull(g)
    comparisons.append(g.at);g.take('483911')
    if ctor:g.branch('75',False,1)
    else:g.branch('74',True,1)
    need('literal-same-allocated-class',all(u['cell']==allocation['cell']for u in classes))
    g.take('488d4b'+c,'488b5c2430','4883c420','5f');need('literal-restored-tail-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=ctor,allocation=allocation,allocationTarget=allocator,
        baseClassUsage=ancestor,baseReady=None,instanceSetter=setter,strictCast=None,
        inlineStrictCasts=dict(predicateMode='literal-class-equality',comparisonSites=comparisons,sameBaseReferenceCached=True,
            successfulPredicateConditional=True,runtimePredicateOutcomeObserved=False,referenceRegister='rcx',classRegister='rdx',
            entryRspRestored=True,nonvolatilesRestored=['rbx','rdi']),classUsages=classes,
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=True,originalConstructorTarget=original_ctor,
        originalConstructorEffectsProved=False,normalReturnViaBarrier=True,
        condition='Initialized current nominal classes, exact allocation/Original constructor and independently owned holder setter. Both literal class-pointer equalities select the same whole nonnull base reference, with complete frame restoration and disabled tail barrier. No external compatible-class predicate or runtime class observation is claimed.')

def bind_initialization(image,ctx,wrapper,program):
    """Fresh nominal child allocation and each exact current constant field."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,scalar_param_native as scalar
    record=program['inlinedNestedInitialization'];base=image.pe.image_base;md=image.metadata
    child=derive_typed_usage_context(image,record['childAllocation']['site']-base,label='generatedInlineCastFactory.child')
    need('current-reference-child-allocation',child['tag']==1 and not ctx.is_value_type(child['typeName']))
    fields=[]
    for owner in life._class_ancestry(ctx,wrapper.wrapped_type):
        for field in md.fields_for(ctx.index.types[owner]):
            if ctx.field_attributes(field.type_index)&16:continue
            fact=ctx.field(owner+'::'+md.string(field.name_index))
            if fact[2]!=record['childReferenceOffset']:continue
            need('same-current-nominal-child-field',fact[1]==child['typeName'])
            scalar.ordinary(image,ctx.type_pointer(field.type_index),18,'generatedInlineCastFactory.childField',reference=True);fields.append(fact)
    need('one-current-child-reference-field',len(fields)==1)
    constants=[life._bind_factory_constant(image,ctx,child['typeName']if s['object']=='child'else wrapper.wrapped_type,s)for s in record['constantFields']]
    return dict(childAllocation=child,childReferenceField=fields[0],constantFields=constants,sourceProgram=record,
        originalConstructorInvoked=False,childConstructorInvoked=False,childWireGrammarAdmitted=False)
