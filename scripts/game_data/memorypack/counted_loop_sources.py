"""Induction certificates for already strict, complete counted-source programs.

This helper does not identify a source or grant an element grammar. The caller's
exact byte parser owns every instruction/register effect and child/ABI join.
Here fresh one/two/three-iteration executions must expose one identical loop
body with the same signed back edge, initialization and increment. The bounded
nonnegative count then prevents signed counter overflow under the caller's
explicit capacity, buffered-source and normal ABI conditions.
"""


def prove_induction(programs,*,initial,increment,comparison,counter,saved_count,max_count=10000,mode_key='newList',backedge_sites=None):
    if (type(max_count)is not int or not 3<=max_count<=10000
            or counter not in('ebx','esi','edi','ebp','r12d','r13d','r14d','r15d')or not isinstance(saved_count,str)or not saved_count
            or type(mode_key)is not str or mode_key not in('newList','newDictionary','newArray')):
        raise ValueError('countedLoop.invalid-induction-domain')
    # BytesPath records instruction operands as separate chunks. A one-byte
    # displacement can itself equal a short-branch opcode. An exact source
    # parser may therefore select its actual backedge sites explicitly; this
    # narrows discovery and never bypasses opcode, operand, target or induction.
    if backedge_sites is not None and(not isinstance(backedge_sites,(list,tuple))or len(backedge_sites)!=1
            or any(type(at)is not int or at<0 for at in backedge_sites)):
        raise ValueError('countedLoop.invalid-explicit-backedge-sites')
    if any(mode_key not in p for p in programs):raise ValueError('countedLoop.missing-mode:'+mode_key)
    modes=sorted({p[mode_key]for p in programs});proofs=[]
    if not modes or any(type(m)is not bool for m in modes):raise ValueError('countedLoop.invalid-modes')
    for new in modes:
        selected={};zero=None
        for count in(0,1,2,3):
            rows=[p['selectedBytes']for p in programs if p[mode_key]==new and p['countWitness']==count]
            if len(rows)!=1:raise ValueError('countedLoop.one-complete-program-per-witness')
            selected[count]=[(a,h.lower())for a,h in rows[0]]
            if count==0:
                zero=next(p for p in programs if p[mode_key]==new and p['countWitness']==0)
        callbacks=(zero.get('elementCallbacks',zero.get('elementReads'))if zero is not None else None)
        if callbacks is None and zero is not None and 'elementCallbackSites'in zero:
            callbacks=len(zero['elementCallbackSites'])
        if callbacks!=0 or not selected[0]or selected[0][-1][1]!='c3':
            raise ValueError('countedLoop.zero-path-no-callback-complete-return')
        rows=selected[1];indices={a:i for i,(a,_)in enumerate(rows)}
        if len(indices)!=len(rows):raise ValueError('countedLoop.single-iteration-unique-instructions')
        edges=[]
        for i,(at,h)in enumerate(rows):
            if backedge_sites is not None and at not in backedge_sites:continue
            raw=bytes.fromhex(h)
            width=4 if raw==b'\x0f\x8c'else 1 if raw==b'\x7c'else None
            if width is None or i+1>=len(rows):continue
            operand_at,operand=rows[i+1];operand=bytes.fromhex(operand)
            if operand_at!=at+len(raw)or len(operand)!=width:
                raise ValueError('countedLoop.complete-backedge-operand')
            delta=int.from_bytes(operand,'little',signed=True);end=at+len(raw)+width
            target=end+delta
            if target in indices and indices[target]<i:edges.append((indices[target],i+1,target))
        if len(edges)!=1:raise ValueError('countedLoop.unique-signed-backedge')
        begin,end,target=edges[0];prefix,body,suffix=rows[:begin],rows[begin:end+1],rows[end+1:]
        if not prefix or not body or not suffix:raise ValueError('countedLoop.complete-loop-scope')
        if suffix[-1][1]!='c3':raise ValueError('countedLoop.positive-complete-return')
        if sum(h==initial for _,h in prefix)!=1 or any(h==initial for _,h in body):
            raise ValueError('countedLoop.counter-initialization')
        if sum(h==increment for _,h in body)!=1 or body[-3][1]!=comparison:
            raise ValueError('countedLoop.counter-increment-or-comparison')
        for count in(2,3):
            if selected[count]!=prefix+body*count+suffix:
                raise ValueError('countedLoop.byte-identical-induction-body')
        proofs.append({mode_key:new,**dict(counter=counter,savedCount=saved_count,
            loopEntry=target,incrementSite=next(a for a,h in body if h==increment),
            compareSite=body[-3][0],backedge=[body[-2][0],body[-2][1]+body[-1][1]],body=body,
            positiveWitnesses=[1,2,3],zeroProgramHasCompleteReturn=True)})
    result=dict(schema={'newList':'endfield.counted-loop-induction.v1','newDictionary':'endfield.counted-dictionary-loop-induction.v1',
        'newArray':'endfield.counted-array-loop-induction.v1'}[mode_key],
        maxCount=max_count,nonnegativeCountRange=[0,max_count],
        pathProofs=proofs,invariant='At loop entry counter=i, 0<=i<count; one successful element/store increments exactly once. Signed comparison returns to identical body iff i+1<count. Counter and saved count remain unchanged by children under their proved Win64 nonvolatile/frame ABI.',
        noSignedCounterOverflow=max_count<2**31-1,
        condition='The calling strict source parser proves every selected body operation and counter/count ownership. Independently proved child sources and normal ABI/capacity/buffer/disjoint effects hold for each iteration; cold failures, growth and live callback choice acquire no admission.')
    if mode_key in('newDictionary','newArray'):result['modeKey']=mode_key
    if backedge_sites is not None:result['explicitActualBackedgeSites']=list(backedge_sites)
    return result
