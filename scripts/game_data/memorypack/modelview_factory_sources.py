"""Current wrapper reset/holder/cast paths; allocator and runtime predicates are conditional."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def create_instance(regions,entry,s,*,cache=None,constructor=False):
    if cache not in(None,24,32)or cache is not None and constructor:raise ValueError('modelViewFactory.scope')
    g=BytesPath(regions,entry);full=cache is not None or constructor
    g.take('48895c2408','57','4883ec20')if full else g.take('4053','4883ec20');g.relative('803d');g.take('00','488bf9'if full else'488bd9');g.branch('75',True,1);allocation=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    if constructor:g.take('488bd8')
    g.take('4885c0');g.branch('75',True,1)
    if constructor:g.take('33d2','488bcb');g.call(s['constructor'])
    if cache is not None:
        c=bytes((cache,)).hex();g.take('4533c0','488bd0','488bcf');g.call(s['setInstance']);g.take('488b5f10');first=g.relative('488b15');g.take('488bcb');g.call(s['cast']);g.take('488947'+c,'488bcb');second=g.relative('488b15');g.call(s['cast']);g.take('488d4f'+c)
        if cell!=first or cell!=second:raise ValueError('modelViewFactory.original-cast-identity')
    elif constructor:g.take('488d4f10','48895f10')
    else:g.take('488d4b10','48894310')
    g.take('488b5c2430')if full else None;g.take('4883c420','5f')if full else g.take('4883c420','5b')
    if g.relative('e9')!=s['barrier']:raise ValueError('modelViewFactory.barrier-tail')
    return dict(selectedBytes=g.seen,allocationInstruction=allocation,originalClassCell=cell,baseSlot=16,cacheSlot=cache,originalConstructor=constructor,normalReturnViaBarrier=True,condition='Initialized exact typed wrapper reset, normal nonnull original allocation and optional original ctor preserving nonvolatiles; matching owned setter and compatible cast return same full original. Exact reference writes and restored caller frame precede disabled barrier tail. Other inherited caches are not assumed coherent; runtime constructor/allocation/predicate/storage effects conditional.')


def dual_setter(regions,entry,barrier,*,cache):
    if cache not in(24,32):raise ValueError('modelViewFactory.setter-cache')
    c=bytes((cache,)).hex();g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','488951'+c,'4883c1'+c,'4c8bca');g.call(barrier);g.take('498d4a10','4d894a10','4883c428')
    if g.relative('e9')!=barrier:raise ValueError('modelViewFactory.setter-tail')
    return dict(selectedBytes=g.seen,baseSlot=16,cacheSlot=cache,sameFullReferenceStored=True,normalReturnViaBarrier=True,condition='Current owned typed wrapper fields and RDX full original reference, disjoint stable storage; separately proved disabled collector preserves live R9 value/R10 receiver across first barrier, normal tail effects. Other inherited caches remain separate.')


def checked_cast(regions,entry,assignable):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','488bfa','488bd9','4885c9');g.branch('74',False,1);g.take('488b09');g.call(assignable);g.take('84c0');g.branch('74',False,1);g.take('488bc3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,sameFullReferenceReturned=True,normalReturn=True,condition='Nonnull incoming RCX has coherent class; actual predicate on its class and incoming RDX expected class returns true with ordinary Win64 preservation. Predicate outcome, helper internals and runtime class resolution remain conditional.')


def cached_rbx(regions,entry,s,*,cache,refresh):
    if cache not in(24,32)or refresh not in('empty','different'):raise ValueError('modelViewFactory.getter-scope')
    c=bytes((cache,)).hex();g=BytesPath(regions,entry);g.take('4053','4883ec20');g.relative('803d');g.take('00','488bd9');g.branch('74',False,1);g.take('48837b'+c+'00');g.branch('74'if g.bytes.get(g.at)==0x74 else'0f84',refresh=='empty',1 if g.bytes.get(g.at)==0x74 else 4)
    if refresh=='different':g.take('488b4310','483943'+c);g.branch('75'if g.bytes.get(g.at)==0x75 else'0f85',True,1 if g.bytes.get(g.at)==0x75 else 4)
    first=g.relative('488b15');g.take('48897c2430','488b7b10','488bcf');g.call(s['cast']);g.take('488943'+c,'488bcf');second=g.relative('488b15');g.call(s['cast']);g.take('488d4b'+c);g.call(s['barrier']);g.take('488b7c2430');g.jump('eb',1)if g.bytes.get(g.at)==0xeb else g.jump('e9',4);g.take('488b43'+c,'4883c420','5b','c3')
    if first!=second:raise ValueError('modelViewFactory.getter-cast-context')
    return dict(selectedBytes=g.seen,baseSlot=16,cacheSlot=cache,castClassCell=first,refresh=refresh,normalReturn=True,sameBaseReferenceCachedAndReturned=True,condition='Initialized current typed wrapper with compatible nonnull base16, cache empty or unequal as selected; normally returning compatible cast preserves same input, disabled barrier/storage stable and noninterfering. Predicate/live/default selection conditional.')


def wrapper_constructor(regions,entry,s,*,cache=None,constructor=False,mode="rdi"):
    if cache not in(None,24,32)or cache is not None and constructor or mode not in('rbx','rdi','rdi-late'):raise ValueError('modelViewFactory.constructor-scope')
    g=BytesPath(regions,entry);short_cache=cache==32 and mode=='rbx';late_cache=cache==32 and mode!='rdi';full=cache==32 and not late_cache or constructor
    if full:g.take('48895c2408','57','4883ec20')
    elif cache==24 or mode=='rdi-late':g.take('4057','4883ec20')
    else:g.take('4053','4883ec20')
    g.relative('803d');g.take('00','488bf9'if full or cache==24 or mode=='rdi-late'else'488bd9')
    if g.bytes.get(g.at)==0x75:g.branch('75',True,1)
    else:g.branch('74',False,1)
    parent=None
    if cache:
        parent=g.at;g.relative('488b0d')
        if cache==32 and not late_cache:g.call(s['initializeParent'])
        else:
            g.take('83b9e000000000')
            if g.bytes.get(g.at)==0x75:g.branch('75',True,1)
            else:g.branch('0f84',False,4)
        if cache==32:g.take('33d2','488bcb'if short_cache else'488bcf');g.call(s['parentConstructor'])
    allocation=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    if constructor:g.take('488bd8')
    g.take('4885c0')
    if g.bytes.get(g.at)==0x75:g.branch('75',True,1)
    else:g.branch('74',False,1)
    if constructor:g.take('33d2','488bc8');g.call(s['constructor'])
    if cache:
        c=bytes((cache,)).hex();g.take('4533c0')
        if cache==24 or mode=='rdi-late':g.take('48895c2430')
        elif short_cache:g.take('48897c2430')
        g.take('488bd0','488bcb'if short_cache else'488bcf');g.call(s['setInstance']);g.take('488b7b10'if short_cache else'488b5f10');first=g.relative('488b15');g.take('488bcf'if short_cache else'488bcb');g.call(s['cast']);g.take(('488943'if short_cache else'488947')+c,'488bcf'if short_cache else'488bcb');second=g.relative('488b15');g.call(s['cast']);g.take(('488d4b'if short_cache else'488d4f')+c)
        if cell!=first or cell!=second:raise ValueError('modelViewFactory.constructor-original-casts')
    elif constructor:g.take('488d4f10','48895f10')
    else:g.take('488d4b10','48894310')
    if full or cache==24 or mode=='rdi-late':g.take('488b5c2430','4883c420','5f')
    else:
        if short_cache:g.take('488b7c2430')
        g.take('4883c420','5b')
    if g.relative('e9')!=s['barrier']:raise ValueError('modelViewFactory.constructor-barrier-tail')
    return dict(selectedBytes=g.seen,allocationInstruction=allocation,parentClassInstruction=parent,originalClassCell=cell,baseSlot=16,cacheSlot=cache,normalReturnViaBarrier=True,condition='Fresh typed wrapper under selected initialized metadata/class-ready conditions; exact parent constructor, normal original allocation and optional original constructor, owned dual setter and compatible same-object casts. Exact current full original reference is stored in base16 and own cache where present. Original constructor/runtime allocation/storage effects and inherited cache coherence remain separate conditions.')
