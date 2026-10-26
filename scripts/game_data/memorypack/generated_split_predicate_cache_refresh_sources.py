"""Exact split comparison and inline-predicate reference cache refresh.

Typed parent/cache declarations and the selected class predicate remain the
caller's independent obligations. This program proves both compatible refresh
paths, full pointer stores and the complete integer register/stack return.
It does not admit a cold metadata path or infer a live predicate outcome.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def program(regions,entry,*,base_slot,cache_slot,predicate,barrier,refresh):
    if not(type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128
            and refresh in('empty','different')and type(predicate)is int and predicate>0
            and type(barrier)is int and barrier>0):
        raise ValueError('generatedSplitPredicateCacheRefresh.scope')
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex()
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('74',False,1)
    g.take('48837b'+c+'00');g.branch('75',refresh=='different',1)
    if refresh=='different':
        g.take('488b43'+b,'483943'+c);g.branch('74',False,1);g.jump('eb',1)
    g.take('48897c2430','488b7b'+b,'4885ff');g.branch('74',False,1)
    first=g.relative('488b15');g.take('488b0f');g.call(predicate)
    g.take('84c0');g.branch('74',False,1)
    g.take('488bc7','488943'+c)
    second=g.relative('488b15');g.take('488b0f');g.call(predicate)
    g.take('488d4b'+c);g.call(barrier)
    g.take('488b7c2430','488b43'+c,'4883c420','5b','c3')
    if first!=second:raise ValueError('generatedSplitPredicateCacheRefresh.same-owned-class')
    return dict(selectedBytes=g.seen,initializedFlag=flag,baseSlot=base_slot,cacheSlot=cache_slot,
        predicateClassCell=first,refresh=refresh,sameBaseReferenceCachedAndReturned=True,
        normalReturn=True,entryRspRestored=True,allNonvolatilesRestored=True,
        condition='Initialized typed wrapper, selected empty/different cache and compatible nonnull base; '
            'the exact selected class predicate returns true normally on the first test, both predicate '
            'calls preserve disjoint wrapper/frame storage and Win64 nonvolatiles, and the disabled '
            'reference barrier preserves the same ABI. Live predicate outcomes remain conditional.')
