"""Exact split comparison and fallthrough compatible-reference cache refresh.

Own declarations select the base/cache slots. The source selects its two class
uses and actual cast/barrier calls; compatible class predicates, disabled
collector and normal helper ABI remain conditions. No cold metadata path,
child grammar or constructor is supplied by this program.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,*,base_slot,cache_slot,cast,barrier,refresh):
    if not(type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128
            and refresh in('empty','different')and type(cast)is int and type(barrier)is int):
        raise ValueError('generatedSplitCacheRefresh.scope')
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('74',False,1)
    b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex();g.take('48837b'+c+'00')
    g.branch('0f85',refresh=='different')
    if refresh=='different':
        g.take('488b43'+b,'483943'+c);g.branch('0f84',False);g.jump('e9')
    first=g.relative('488b15');g.take('48897c2430','488b7b'+b,'488bcf');g.call(cast)
    g.take('488943'+c,'488bcf');second=g.relative('488b15');g.call(cast)
    g.take('488d4b'+c);g.call(barrier);g.take('488b7c2430','488b43'+c,'4883c420','5b','c3')
    if first!=second:raise ValueError('generatedSplitCacheRefresh.same-owned-cast-class')
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        castClassCell=first,refresh=refresh,sameBaseReferenceCachedAndReturned=True,
        normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
        condition='Initialized own typed wrapper with compatible nonnull base and selected empty/different cache; actual compatible cast returns the unchanged full base pointer, normal disabled barrier preserves Win64 nonvolatiles and disjoint storage. Class predicates and live provider selection remain conditional.')


def short_backward_program(regions,entry,*,base_slot,cache_slot,cast,barrier,refresh):
    """Short backward return beyond the legacy base16/cache24-or32 owner."""
    if not(type(base_slot)is int and type(cache_slot)is int and base_slot==16 and 32<cache_slot<128
            and refresh in('empty','different')and type(cast)is int and cast>0
            and type(barrier)is int and barrier>0):
        raise ValueError('generatedSplitCacheRefresh.short-backward-scope')
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex()
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('74',False,1)
    g.take('48837b'+c+'00');g.branch('74',refresh=='empty',1)
    if refresh=='different':
        g.take('488b43'+b,'483943'+c);g.branch('75',True,1)
    first=g.relative('488b15');g.take('48897c2430','488b7b'+b,'488bcf');g.call(cast)
    g.take('488943'+c,'488bcf');second=g.relative('488b15');g.call(cast)
    g.take('488d4b'+c);g.call(barrier);g.take('488b7c2430');g.jump('eb',1)
    g.take('488b43'+c,'4883c420','5b','c3')
    if first!=second:raise ValueError('generatedSplitCacheRefresh.same-owned-cast-class')
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        castClassCell=first,refresh=refresh,sameBaseReferenceCachedAndReturned=True,
        normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
        condition='Initialized own typed wrapper with compatible nonnull base and selected empty/different cache; '
            'actual compatible cast returns the unchanged full base pointer, normal disabled barrier preserves '
            'Win64 nonvolatiles and disjoint storage. Class predicates and live provider selection remain conditional.')


def initialized_short_backward_program(regions,entry,*,base_slot,cache_slot,cast,barrier,refresh):
    """Cache40 with a taken initialized JNE and an owned backward return."""
    if not(type(base_slot)is int and type(cache_slot)is int and(base_slot,cache_slot)==(16,40)
            and refresh in('empty','different')and type(cast)is int and cast>0
            and type(barrier)is int and barrier>0):
        raise ValueError('generatedSplitCacheRefresh.initialized-short-backward-scope')
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('75',True,1)
    g.take('48837b2800');g.branch('74',refresh=='empty',1)
    if refresh=='different':
        g.take('488b4310','48394328');g.branch('75',True,1)
    first=g.relative('488b15');g.take('48897c2430','488b7b10','488bcf');g.call(cast)
    g.take('48894328','488bcf');second=g.relative('488b15');g.call(cast)
    g.take('488d4b28');g.call(barrier);g.take('488b7c2430');g.jump('eb',1)
    g.take('488b4328','4883c420','5b','c3')
    if first!=second:raise ValueError('generatedSplitCacheRefresh.same-owned-cast-class')
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        castClassCell=first,refresh=refresh,sameBaseReferenceCachedAndReturned=True,
        normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
        condition='Initialized own cache40 wrapper with compatible nonnull base and selected empty/different cache; '
            'actual compatible cast returns the unchanged full base pointer, normal disabled barrier preserves '
            'Win64 nonvolatiles and disjoint storage. Class predicates and live provider selection remain conditional.')
