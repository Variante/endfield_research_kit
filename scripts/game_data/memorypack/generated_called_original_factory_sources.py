"""Exact cached wrapper ctor invoking owned ancestor and Original ctors."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition,detail=None):
    if not condition:raise ValueError('generatedCalledOriginalFactory.'+key+':'+str(detail)[:700])


def r9_initialized_factory(regions,entry,barrier,*,ctor,base_ctor,base_slot,cache_slot,initializers):
    """Exact RAX/R9 holder publications with independent Original defaults.

    Its owner must separately prove every Original constructor store.
    Disabled no-effect barriers preserve the volatile R9 allocation witness.
    """
    from scripts.game_data.memorypack import generated_lifecycle_sources as life
    need('finite-called-base-initialized-original',type(ctor)is bool and type(barrier)is int and barrier>0
        and(base_ctor is None or ctor and type(base_ctor)is int and base_ctor>0)
        and 16<=base_slot<cache_slot<128)
    from scripts.game_data.memorypack.generated_condition_factory_sources import _defaults
    expected=_defaults(initializers)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex()
    g=BytesPath(regions,entry);rbx=life._peek(g,2)==bytes.fromhex('4053')
    g.take('4053'if rbx else'4057','4883ec20');flag=life._direct_flag(g,'803d')
    g.take('488bd9'if rbx else'488bf9');life._initialized(g);ancestor=None
    if ctor:
        site=g.at;ancestor=dict(site=site,cell=g.relative('488b0d'));g.take('83b9e000000000');life._initialized(g)
        if base_ctor is not None:g.take('33d2','488bcb'if rbx else'488bcf');g.call(base_ctor)
    site=g.at;allocation=dict(site=site,cell=g.relative('488b0d'));allocator=g.relative('e8')
    g.take('4c8bc8','4885c0');life._nonnull(g)
    first=None;address=saved=stored=False;stores=[]
    while expected or not(address and saved and stored):
        if life._peek(g,4)==bytes.fromhex(('488d4b'if rbx else'488d4f')+c):
            need('one-cache-address',not address);first=g.at;g.take(('488d4b'if rbx else'488d4f')+c);address=True
        elif life._peek(g,5)==bytes.fromhex('48897c2430'if rbx else'48895c2430'):
            need('one-base-reference-register-home',not saved);g.take('48897c2430'if rbx else'48895c2430');saved=True
        elif life._peek(g,4)==bytes.fromhex(('488943'if rbx else'488947')+c):
            need('one-whole-cache-store',not stored);g.take(('488943'if rbx else'488947')+c);stored=True
        else:
            matches=[]
            for(offset,width),raw in expected.items():
                h=('66'if width==2 else'')+('c6'if width==1 else'c7')+('40'if offset<128 else'80')
                h+=offset.to_bytes(1 if offset<128 else 4,'little',signed=True).hex()+raw.hex()
                if life._peek(g,len(bytes.fromhex(h)))==bytes.fromhex(h):matches.append((offset,width,h))
            need('one-independently-proved-Original-default',len(matches)==1)
            offset,width,h=matches[0];at=g.at;g.take(h)
            stores.append(dict(instructionVa=at,offset=offset,bytes=width,constantHex=expected.pop((offset,width)).hex().upper()))
    g.call(barrier)
    second=g.at;g.take(('488d4b'if rbx else'488d4f')+b,('4c894b'if rbx else'4c894f')+b);g.call(barrier)
    g.take(('488b7b'if rbx else'488b5f')+b);usages=[];casts=[]
    for i in range(2):
        site=g.at;usages.append(dict(site=site,cell=g.relative('488b15')))
        if not i:g.take('488bcf'if rbx else'488bcb')
        casts.append(g.relative('e8'))
        if not i:g.take(('488943'if rbx else'488947')+c,'488bcf'if rbx else'488bcb')
    need('same-exact-Original-class-and-casts',len(set(casts))==1
         and all(u['cell']==allocation['cell']for u in usages))
    g.take(('488d4b'if rbx else'488d4f')+c,'488b7c2430'if rbx else'488b5c2430','4883c420','5b'if rbx else'5f')
    need('restored-frame-barrier-tail',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=ctor,
        allocation=allocation,allocationTarget=allocator,baseClassUsage=ancestor,baseReady=None,
        baseConstructorTarget=base_ctor,instanceSetter=None,strictCast=casts[0],classUsages=usages,
        inlineHolderWrites=[dict(offset=slot,bytes=8,sameAllocatedReference=True,programStart=start)
            for slot,start in((cache_slot,first),(base_slot,second))],
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,
        originalConstructorTarget=None,originalConstructorEffectsProved=False,inlinedOriginalInitializers=initializers,
        actualDefaultStores=stores,independentOriginalConstructorDefaultsRequired=True,disabledBarrierPreservesR9Required=True,
        normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
        condition=__doc__+' The actual called ancestor, every Original default, allocated nominal and compatible casts require independent selected-image joins.')


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
    original_context=None
    if lifecycle._peek(g,3)==bytes.fromhex('488b15'):
        at=g.at;original_context=dict(site=at,cell=g.relative('488b15'))
    else:g.take('33d2')
    g.take('488bc8');g.call(original_ctor)
    inline_writes=None
    if lifecycle._peek(g,4)==bytes.fromhex('488d4b'+c):
        inline_writes=[];setter=None
        for slot in(cache_slot,base_slot):
            d=bytes((slot,)).hex();start=g.at;g.take('488d4b'+d,'48897b'+d);g.call(barrier)
            inline_writes.append(dict(offset=slot,bytes=8,sameAllocatedReference=True,programStart=start))
    else:
        g.take('4533c0','488bd7','488bcb');setter=g.relative('e8')
    g.take('488b7b'+b)
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
                inlineHolderWrites=inline_writes,strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
                originalConstructorCalled=True,originalConstructorTarget=original_ctor,originalConstructorEffectsProved=False,
                **(dict(originalConstructorContext=original_context)if original_context is not None else{}),
                normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
                condition='Initialized own ancestor metadata, two independently owned current constructor calls on the exact wrapper/fresh Original, unchanged whole reference passed to its owned holder setter, same nominal casts and restored tail; runtime invocation and child framing are separate.')
