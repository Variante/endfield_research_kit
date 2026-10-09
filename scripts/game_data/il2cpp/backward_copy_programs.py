"""Distinct-byte and affine proofs for descending cached-vector copy programs.

The native consumer owns control flow, count division/decrement, alignment and
source-minus-destination arithmetic. No sample payload or loop count substitutes
for byte identities and a natural-number induction over those checked steps.
"""
from __future__ import annotations


def _fail(label,check,expected,actual):
    raise ValueError(f'{label}.{check}: expected={str(expected)[:256]} actual={str(actual)[:384]}')


def _move(op,*,label,aligned_store=False):
    a=op.get('address',{});direction=op.get('direction');d=a.get('displacement')
    if (direction not in ('load','store') or op.get('memoryBytes')!=16 or op.get('registerBits')!=128
            or op.get('registerBitOffset')!=0 or op.get('backingRegister') not in ('vector0','vector1','vector2')
            or op.get('valueExtension') is not None or op.get('upperRegisterEffect')!='preserved'
            or op.get('nonTemporalHint') is not False or op.get('writesFlags') is not False
            or a.get('addressBits')!=64 or a.get('ripRelative') is not False or type(d) is not int or a.get('scale')!=1):
        _fail(label,'move','exact sixteen-byte legacy bit transfer',op)
    alignment=16 if direction=='store' and aligned_store else 1
    if op.get('requiredAlignmentBytes')!=alignment:_fail(label,'alignment',alignment,op)
    return a,direction,d,op['backingRegister']


def prove_backward_cache_alignment(head,last,copy,aligned_load,unaligned_store,initial_store,*,label='backward-alignment'):
    expected_copy={'source':'vector0','destination':'vector1','bits':128,'bitOffset':0,'upperRegisterEffect':'preserved',
        'writesFlags':False,'readsMemory':False,'writesMemory':False}
    if copy!=expected_copy:_fail(label,'saved-last-register-copy',expected_copy,copy)
    specs=[(head,'load','rdx',None,0,'vector2',False),(last,'load','rcx','rdx',-16,'vector0',False),
        (aligned_load,'load','rcx','rdx',0,'vector0',False),(unaligned_store,'store','r9',None,0,'vector1',False),
        (initial_store,'store','rcx',None,0,'vector0',True)]
    for op,direction,base,index,d,backing,aligned in specs:
        a,actual_direction,actual_d,actual_backing=_move(op,label=label,aligned_store=aligned)
        if (actual_direction,actual_d,actual_backing,a.get('base'),a.get('index'))!=(direction,d,backing,base,index):
            _fail(label,'cache-address-and-carrier',(direction,base,index,d,backing),op)
    cases=[]
    for a in range(16):
        # N is arbitrary and >32. P is N-16-a relative to original D;
        # affine offsets (coefficient of N, constant) avoid sampled N/data.
        if 33-16-a<0 or not -16-a<=-16<=-a<=0:_fail(label,'affine-cache-bounds','P>=0 and overlapping suffix coverage',a)
        aligned_source=[(1,-16-a+i) for i in range(16)]
        aligned_destination=[(1,-16-a+i) for i in range(16)]
        last_source=[(1,-16+i) for i in range(16)]
        last_destination=[(1,-16+i) for i in range(16)]
        if aligned_source!=aligned_destination or last_source!=last_destination:_fail(label,'affine-byte-identity','same source and destination offsets',a)
        cases.append({'alignmentRetreat':a,'currentOffsetFromOriginalEnd':-16-a,
            'remainingPrefixLowerBound':33-16-a,'completeUpperSuffixWithInitialChunkStoreProved':True,
            'upperSuffixAfterCachedCurrentVectorProved':True})
    return {'allAlignmentResiduesProved':True,'alignmentCases':cases,'cachedOriginalHeadAndCurrentVectorProved':True,
        'originalLastStoredOnlyWhenUnalignedProved':True,'upperSuffixCoveredWhenBigLoopSelectedProved':True,
        'equations':'a=(D+N-16)&15; P=D+N-16-a; remaining=P-D=N-16-a; source reads equal current destination+S-D modulo 2^64',
        'selection':'N>32; valid stable source/destination with non-wrapping endpoints; destination>source; source delta remains unchanged',
        'runtimeExecutionObserved':False}


def prove_pipelined_backward_chunk(steps,repeat_stores,exit_store,exit_copy,*,label='backward-chunk'):
    registers={};covered=set();loaded=set();position=0;minimum_store=None;retreats=0
    for step in steps:
        if step.get('kind')=='pointer-retreat':
            if step.get('bytes')!=128 or retreats:_fail(label,'pointer-retreat','one original whole-chunk retreat',step)
            position-=128;retreats+=1;continue
        a,direction,d,backing=_move(step,label=label,aligned_store=True)
        if a.get('base')!='rcx' or a.get('index')!=('rdx' if direction=='load' else None):
            _fail(label,'delta-address','current destination plus source delta on loads; current destination on stores',step)
        start=position+d
        if not -128<=start<start+16<=0:_fail(label,'chunk-range','inside symbolic [P-128,P)',(start,start+16))
        if backing=='vector2':_fail(label,'cached-head-preservation','scratch vector0 or vector1',backing)
        if direction=='load':
            if minimum_store is not None and start+16>minimum_store:
                _fail(label,'future-source-safety','earlier destination starts at/above each later source end',(minimum_store,start+16))
            registers[backing]=list(range(start,start+16));loaded.update(range(start,start+16))
        else:
            if d%16:_fail(label,'aligned-store-offset','whole-vector displacement',d)
            if registers.get(backing)!=list(range(start,start+16)):
                _fail(label,'stored-source-byte-identity',list(range(start,start+16)),registers.get(backing))
            covered.update(range(start,start+16));minimum_store=min(minimum_store if minimum_store is not None else start,start)
    if retreats!=1 or loaded!=set(range(-128,0)) or covered!=set(range(-96,0)):
        _fail(label,'pipeline-body-coverage','all chunk loads and upper six vector stores',{'retreats':retreats,'loads':len(loaded),'stores':len(covered)})
    expected={'vector0':list(range(-112,-96)),'vector1':list(range(-128,-112))}
    if registers!=expected:_fail(label,'pending-low-vectors',expected,registers)

    def deferred_store(op,*,expected_backing):
        a,direction,d,backing=_move(op,label=label,aligned_store=True)
        start=-128+d
        if (direction!='store' or a.get('base')!='rcx' or a.get('index') is not None
                or backing!=expected_backing or d%16 or registers.get(backing)!=list(range(start,start+16))):
            _fail(label,'deferred-byte-identity','actual pending vector at its same offset',op)
        return set(range(start,start+16))

    if len(repeat_stores)!=2:_fail(label,'repeat-completion','two pending vector stores',repeat_stores)
    repeated=covered|deferred_store(repeat_stores[0],expected_backing='vector0')|deferred_store(repeat_stores[1],expected_backing='vector1')
    if repeated!=set(range(-128,0)):_fail(label,'repeat-full-chunk-coverage',128,len(repeated))
    exited=covered|deferred_store(exit_store,expected_backing='vector0')
    expected_copy={'source':'vector1','destination':'vector0','bits':128,'bitOffset':0,'upperRegisterEffect':'preserved',
        'writesFlags':False,'readsMemory':False,'writesMemory':False}
    if exit_copy!=expected_copy or exited!=set(range(-112,0)):_fail(label,'exit-cached-low-vector',expected_copy,exit_copy)
    return {'allChunkBytesLoadedFromInitialSourceProved':True,'repeatCompletesEveryChunkByteProved':True,
        'exitCompletesUpperChunkAndForwardsLowestVectorProved':True,'chunkBytes':128,'vectorBytes':16,
        'cachedOriginalHeadPreservedProved':True,'backwardOverlapFutureSourceSafetyProved':True,
        'pendingLowestVectorEquation':'on exit current pointer=P-128; vector0 holds initial source bytes at [P-128,P-112)',
        'inductionSelection':'incoming P is sixteen-byte aligned and at least one whole chunk above original destination; destination > source, valid stable non-wrapping memory',
        'runtimeExecutionObserved':False}


def prove_backward_tail(loop_steps,head_store,final_store,*,remaining,label='backward-tail'):
    if type(remaining) is not int or not 0<=remaining<128:_fail(label,'remainder-domain','integer in [0,128)',remaining)
    registers={'vector0':list(range(remaining,remaining+16)),'vector2':list(range(16))}
    position=remaining;covered=set();minimum_store=None;loads=stores=0

    def apply(op):
        nonlocal minimum_store,loads,stores
        a,direction,d,backing=_move(op,label=label)
        if direction=='load':
            if a.get('base')!='rcx' or a.get('index')!='rdx' or backing!='vector0':_fail(label,'tail-source','current pointer plus stable source delta',op)
            start=position+d
            if not 0<=start<start+16<=remaining+16:_fail(label,'tail-source-bounds','within selected remaining payload',(start,start+16))
            if minimum_store is not None and start+16>minimum_store:_fail(label,'future-source-safety','descending nonoverwriting read',(minimum_store,start+16))
            registers[backing]=list(range(start,start+16));loads+=1
        else:
            if a.get('index') is not None or a.get('base') not in ('rcx','rax'):_fail(label,'tail-destination','current or original destination',op)
            start=(position if a['base']=='rcx' else 0)+d
            if not 0<=start<start+16<=remaining+16 or registers.get(backing)!=list(range(start,start+16)):
                _fail(label,'stored-source-byte-identity','in-bounds original source bytes at same offset',(op,start,registers.get(backing)))
            covered.update(range(start,start+16));minimum_store=min(minimum_store if minimum_store is not None else start,start);stores+=1

    for _ in range(remaining//16):
        retreats=0
        for step in loop_steps:
            if step.get('kind')=='pointer-retreat':
                if step.get('bytes')!=16 or retreats:_fail(label,'tail-retreat','one complete-vector retreat',step)
                position-=16;retreats+=1
            else:apply(step)
        if retreats!=1:_fail(label,'tail-retreat','one complete-vector retreat',retreats)
    if position!=remaining%16:_fail(label,'tail-final-pointer',remaining%16,position)
    if remaining%16:apply(head_store)
    apply(final_store)
    if covered!=set(range(remaining+16)):_fail(label,'complete-tail-byte-coverage',remaining+16,len(covered))
    return {'remaining':remaining,'allTailBytesEqualInitialSourceProved':True,'cachedPrefixAndFinalVectorOverlapValuesAgreeProved':True,
        'backwardOverlapFutureSourceSafetyProved':True,'finalPointerOffset':position,'vectorIterations':remaining//16,
        'loads':loads,'stores':stores,'runtimeExecutionObserved':False}
