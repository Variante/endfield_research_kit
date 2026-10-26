"""Selected reference-list loop invariant over the maintained exact body model."""
from scripts.game_data.memorypack.pooled_string_list_sources import list_source


def reference_loop(regions,entry,offsets,symbols):
    proof=list_source(regions,entry,offsets,symbols,count=1,new=True,grow=False)
    selected=proof['selectedBytes'];starts=[a for a,b in selected if b=='48c744242000000000'];increments=[a for a,b in selected if b=='ffc6'];initial=[a for a,b in selected if b=='33f6']
    branches=[i for i,(_,b)in enumerate(selected)if b=='0f8c']
    if len(starts)!=2 or len(increments)!=1 or len(initial)!=1 or not branches:raise ValueError('modelViewList.loop-shape')
    i=branches[-1];site,prefix=selected[i];disp_at,disp=selected[i+1]
    if disp_at!=site+2 or len(bytes.fromhex(disp))!=4 or disp_at+4+int.from_bytes(bytes.fromhex(disp),'little',signed=True)!=starts[-1]:raise ValueError('modelViewList.backedge')
    if not initial[0]<starts[-1]<increments[0]<site:raise ValueError('modelViewList.counter-order')
    if selected[i-1][1]!='3b742468' or selected[i-2][1]!='ffc6':raise ValueError('modelViewList.saved-count')
    return dict(selectedBytes=selected,headerBytes=4,elementCallbackSites=proof['elementCallbackSites'],callbackAbi=proof['callbackAbi'],loopEntry=starts[-1],loopBackedge=site,counterRegister='esi',countSlot=104,referenceStride=8,normalReturn=True,induction='For signed N in1..Int32Max, initial ESI=0 and immutable saved N; one complete fixed body invokes one same-Reader/out callback, appends its fullref8, then increments ESI once and compares signed ESI<N. Normal iteration preserves ESI/count/Reader/output context, hence exactly N callbacks and list writes, and ESI=N at normal exit; no overflow before that exit.',condition='Fresh typed List<T> context and matching formatter slot, initially null output, normal initialized allocation/array helpers with capacity N, size0 and stable storage; disabled collector and no child/helper interference. All calls preserve nonvolatile RSI/R13/R14/R15 under ordinary Win64 ABI and caller stack locals are disjoint. Same selected no-growth Add path on each iteration. Constructor/storage/runtime/default/provider effects conditional; exact child wire grammars proved separately.')
