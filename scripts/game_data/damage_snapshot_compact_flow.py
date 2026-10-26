"""Conditional compact-cache recurrence derived from separately checked paths."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.damage_snapshot_iteration_flow import conditional_iteration_step


def compact_step(index,bound,count,*,snapshot,simple):
    step=conditional_iteration_step(index,bound)
    _require(type(count) is int and 0<=count<=index,'snapshot-compact-count-range','0 <= cache count <= source counter',[count,index])
    _require(type(snapshot) is bool and type(simple) is bool,'snapshot-compact-flags','explicit Boolean selection',[snapshot,simple])
    _require(not snapshot or simple,'snapshot-compact-selected-path','skip or snapshot/simple fast path',[snapshot,simple])
    append=snapshot and simple
    return {**step,'oldCacheCount':count,'nextCacheCount':count+int(append),'appendedRawIndex':count if append else None,
            'cacheIndexEqualsSourceCounter':count==index if append else None,'producerConsumerIndexJoinProved':False}


def writer_disjoint_conditions(cache_base,array_base,action_cache_slot,old_count,slots):
    _require(type(old_count) is int and 0<=old_count<=0x7fffffff,'snapshot-compact-old-index','nonnegative Int32',old_count)
    _require(all(type(v) is int for v in (cache_base,array_base,action_cache_slot)) and
             all(type(slots.get(k)) is int and slots[k]>=0 for k in ('counterDword','countDword','arrayReference','arrayPayload')),
             'snapshot-compact-address-inputs','explicit integer bases and anonymous slots',[cache_base,array_base,action_cache_slot,slots])
    raw_ranges={'counterDword':(cache_base+slots['counterDword'],4),
                'countDword':(cache_base+slots['countDword'],4),
                'arrayReference':(cache_base+slots['arrayReference'],8),
                'actionCacheSlot':(action_cache_slot,8),
                'payloadStore':(array_base+slots['arrayPayload']+old_count*8,8)}
    valid=all(type(a) is int and 0<=a and a+n<=1<<64 for a,n in raw_ranges.values())
    def disjoint(a,b):
        x,n=raw_ranges[a];y,m=raw_ranges[b];return valid and (x+n<=y or y+m<=x)
    # The counter write precedes count+1; the payload write follows it.
    count_retained=disjoint('payloadStore','countDword')
    carrier_ref_retained=all(disjoint(w,'arrayReference') for w in ('counterDword','countDword','payloadStore'))
    action_ref_retained=all(disjoint(w,'actionCacheSlot') for w in ('counterDword','countDword','payloadStore'))
    return {'actualRanges':{k:{'address':a,'widthBytes':n} for k,(a,n) in raw_ranges.items()},
            'validNonwrappingRanges':valid,'postPayloadCountUpdateRetained':count_retained,
            'carrierArrayReferenceRetained':carrier_ref_retained,'actionCachePointerRetained':action_ref_retained,
            'selectedWriterPreservationConditionsHold':count_retained and carrier_ref_retained and action_ref_retained}


def check_compact_connections(clear,writer,append,skip,iteration):
    expected=((clear,'snapshotIncomingThisCacheReset'),(writer,'snapshotCompiledHelperRawStore'),
              (append,'snapshotSimpleValueToAppendRequest'),(skip,'snapshotFlagSkipAppendContinuation'),
              (iteration,'snapshotZeroCounterPositiveBoundIterationConnections'))
    _require(all(p.get('claim')==c for p,c in expected),'snapshot-compact-dependencies','fresh separate native path proofs',[p.get('claim') for p,_ in expected])
    _require(clear['symbol']==append['symbol']==skip['symbol']==iteration['symbol'],'snapshot-compact-same-producer','same selected body',[p['symbol'] for p in (clear,append,skip,iteration)])
    _require(clear['cacheField']==writer['cacheField']==append['cacheField'],'snapshot-compact-cache-field','same selected action cache',[p['cacheField'] for p in (clear,writer,append)])
    _require(writer['helperEntry']==append['compiledAppendTarget'] and writer['requestCall']==append['appendCall'],
             'snapshot-compact-actual-call-join','same physical selected helper request',[writer['helperEntry'],append['compiledAppendTarget']])
    _require(skip['iterationContinuation']==append['continuation'] and iteration['firstCounterValue']==0,
             'snapshot-compact-counter-joins','same increment and zero initialization',[skip['iterationContinuation'],append['continuation'],iteration['firstCounterValue']])
    _require(clear['resetWidthBytes']==4 and [w['widthBytes'] for w in writer['selectedWrites']]==[4,4,8],
             'snapshot-compact-write-widths','reset32, counter32/count32/payload64',[clear['resetWidthBytes'],writer['selectedWrites']])
    return {'claim':'snapshotConditionalCompactCacheRecurrence','evidenceBoundary':'conditional',
            'anonymousSlots':dict(writer['anonymousSlots']),'cacheField':clear['cacheField'],
            'initialSourceCounter':0,'initialRawCacheCount':0,
            'skipTransition':'sourceCounter+1, rawCacheCount unchanged',
            'selectedSimpleTransition':'sourceCounter+1, rawCacheCount+1; raw payload index is old rawCacheCount',
            'conditionalRelation':'raw cache count equals number of selected simple snapshot appends so far; any earlier skip makes current append raw index less than source counter',
            'compiledTargetIsRegisteredAddEntry':writer['compiledTargetIsRegisteredAddEntry'],
            'actualConsumerIncomingIndexObserved':False,'producerConsumerIndexJoinProved':False,
            'requiredConditions':['same valid unchanged action/cache/array identities and live generic ABI/class parity',
                'normal Win64 returning providers and selected physical fast helper with nonnegative Int32 capacities',
                'all non-helper/local/interim/provider/external writes leave cache count, array reference and action cache slot unchanged',
                'actual payload eight-byte write range is disjoint from receiver count four-byte range',
                'all actual helper writes are disjoint from action cache slot and carrier array-reference ranges',
                'positive Int32 loop bound and every selected skip/simple/unit guard; excluded/non-simple/slow paths invalidate recurrence'],
            'boundary':'This is a conditional recurrence composed from fresh checked reset, skip, selected loop and actual helper paths. No live storage disjointness, count/order/index values or whole producer execution is observed. Anonymous slots do not become managed List fields; physical and registered Add remain distinct, and actual consumer-index equality stays open.'}


def check_snapshot_compact(index,clear,writer,append,skip,iteration,spec):
    body=index.body(spec['type'],spec['method'])
    proof=check_compact_connections(clear,writer,append,skip,iteration)
    _require(body.symbol==clear['symbol'],'snapshot-compact-selected-body','selected producer',body.symbol)
    return {**proof,'symbol':body.symbol}
