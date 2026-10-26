"""Exact cached wrapper ctor invoking owned ancestor and Original ctors."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition,detail=None):
    if not condition:raise ValueError('generatedCalledOriginalFactory.'+key+':'+str(detail)[:700])


def program(regions,entry,barrier,*,base_ctor,original_ctor,base_slot,cache_slot):
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('independent-current-constructor-roles',all(type(p)is int and p>0 for p in(base_ctor,original_ctor,barrier))
         and 16<=base_slot<cache_slot<128)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex()
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20')
    flag=lifecycle._direct_flag(g,'803d');g.take('488bd9');lifecycle._initialized(g)
    site=g.at;ancestor=dict(site=site,cell=g.relative('488b0d'));g.take('83b9e000000000');lifecycle._initialized(g)
    g.take('33d2','488bcb');g.call(base_ctor)
    site=g.at;allocation=dict(site=site,cell=g.relative('488b0d'));allocator=g.relative('e8')
    g.take('488bf8','4885c0');lifecycle._nonnull(g)
    g.take('33d2','488bc8');g.call(original_ctor)
    g.take('4533c0','488bd7','488bcb');setter=g.relative('e8');g.take('488b7b'+b)
    usages,casts=[],[]
    for index in range(2):
        at=g.at;usages.append(dict(site=at,cell=g.relative('488b15')))
        if not index:g.take('488bcf')
        casts.append(g.relative('e8'))
        if not index:g.take('488943'+c,'488bcf')
    need('same-current-class-and-both-casts',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
    g.take('488d4b'+c,'488b5c2430','4883c420','5f');need('same-restored-barrier-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=True,allocation=allocation,allocationTarget=allocator,
                baseClassUsage=ancestor,baseReady=None,baseConstructorTarget=base_ctor,instanceSetter=setter,
                inlineHolderWrites=None,strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
                originalConstructorCalled=True,originalConstructorTarget=original_ctor,originalConstructorEffectsProved=False,
                normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
                condition='Initialized own ancestor metadata, two independently owned current constructor calls on the exact wrapper/fresh Original, unchanged whole reference passed to its owned holder setter, same nominal casts and restored tail; runtime invocation and child framing are separate.')
