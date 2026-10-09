"""Byte identities and affine tail proofs for selected forward vector loops.

The consumer proves original control flow/counter updates. Here an aligned
temporal loop block has a distinct byte-token proof; its tail is proved for an
arbitrary already-copied prefix P with original length P + remaining.
"""
from __future__ import annotations
import copy
from .byte_copy_programs import prove_byte_copy_moves


def _fail(label,check,expected,actual):
    raise ValueError(f'{label}.{check}: expected={str(expected)[:256]} actual={str(actual)[:384]}')


def prove_aligned_loop_payload(operations,*,width,chunk,label='aligned-copy-loop'):
    if width not in (16,32) or type(chunk) is not int or chunk<=0 or chunk%width:
        _fail(label,'block-shape','positive whole-vector chunk',(width,chunk))
    normalized=[]
    for op in operations:
        address=op.get('address',{});direction=op.get('direction');d=address.get('displacement')
        if (op.get('memoryBytes')!=width or op.get('registerBits')!=width*8 or op.get('registerBitOffset')!=0
                or op.get('backingRegister') not in {f'vector{i}' for i in range(1,5)}
                or op.get('valueExtension') is not None or op.get('nonTemporalHint') is not False
                or address.get('base')!=('rdx' if direction=='load' else 'rcx') or address.get('index') is not None
                or address.get('addressBits')!=64 or address.get('ripRelative') is not False):
            _fail(label,'loop-move','selected temporal vector transfer preserving cached head/tail',op)
        expected_alignment=1 if direction=='load' else width
        if type(d) is not int or d%width or op.get('requiredAlignmentBytes')!=expected_alignment:
            _fail(label,'aligned-address','whole-vector offset and proved aligned destination base',op)
        # Under aligned destination and a whole-vector displacement, an aligned
        # temporal store transfers the identical bytes of an unaligned store.
        row=copy.deepcopy(op);row['requiredAlignmentBytes']=1;normalized.append(row)
    proof=prove_byte_copy_moves(normalized,length=chunk,pointers={'rdx':'source','rcx':'destination'},label=label)
    return {'chunkBytes':chunk,'widthBytes':width,'allChunkBytesEqualInitialSourceProved':True,
        'sourceAndDestinationRangesInChunkProved':True,'forwardSafeOverlapProved':True,
        'cachedHeadAndLastVectorsPreserved':True,'destinationAlignmentPreservedByChunk':True,
        'alignmentSelection':'incoming destination is aligned to vector width; chunk and each store offset are multiples of that width',
        'byteProof':proof,'runtimeExecutionObserved':False}


def prove_rebased_vector_tail(operations,*,width,chunk,remaining,label='rebased-copy-tail'):
    if width not in (16,32) or type(chunk) is not int or chunk<width or chunk%width or type(remaining) is not int or not 0<=remaining<=chunk:
        _fail(label,'tail-domain','bounded remaining length and whole-vector chunk',(width,chunk,remaining))
    rounded=(remaining+width-1)&-width
    # Tokens are affine positions (coefficient of P, constant), with P the
    # current source/destination displacement from their original bases.
    registers={'vector0':[(0,i) for i in range(width)],
        'vector5':[(1,remaining-width+i) for i in range(width)]}
    covered=set();previous_store_end=0;head_written=False;loads=stores=0
    for op in operations:
        a=op.get('address',{});base=a.get('base');index=a.get('index');d=a.get('displacement');direction=op.get('direction')
        if (op.get('memoryBytes')!=width or op.get('registerBits')!=width*8 or op.get('registerBitOffset')!=0
                or not op.get('backingRegister','').startswith('vector') or op.get('valueExtension') is not None
                or op.get('requiredAlignmentBytes')!=1 or op.get('nonTemporalHint') is not False
                or op.get('writesFlags') is not False or a.get('addressBits')!=64 or a.get('ripRelative') is not False
                or type(d) is not int or index not in (None,'r8','r9') or a.get('scale')!=1):
            _fail(label,'tail-move','exact unaligned vector transfer over selected affine addresses',op)
        start=d+(remaining if index=='r8' else rounded if index=='r9' else 0)
        backing=op['backingRegister']
        if direction=='load':
            if base!='rdx' or not 0<=start<=start+width<=remaining:
                _fail(label,'tail-source-range',f'within remaining [0,{remaining})',(base,start,start+width))
            if head_written or start<previous_store_end:
                _fail(label,'tail-future-source-safety','earlier relative destination ends at/below next source start',(start,previous_store_end,head_written))
            if backing in ('vector0','vector5'):
                _fail(label,'cached-vector-preservation','scratch register leaves saved head and last unchanged',backing)
            registers[backing]=[(1,i) for i in range(start,start+width)];loads+=1
        elif direction=='store':
            if base=='rax':
                if index is not None or start!=0:_fail(label,'original-head-address','original destination plus zero',a)
                expected=[(0,i) for i in range(width)];head_written=True
            elif base=='rcx':
                if not (0<=start<=start+width<=remaining or start==remaining-width and start+width==remaining and remaining>0):
                    _fail(label,'tail-destination-range','within remainder or the saved original last vector',(start,start+width))
                expected=[(1,i) for i in range(start,start+width)]
                covered.update(range(max(0,start),min(remaining,start+width)))
                previous_store_end=max(previous_store_end,start+width)
            else:_fail(label,'tail-destination','current or original destination',base)
            if registers.get(backing)!=expected:
                _fail(label,'affine-byte-identity',expected,registers.get(backing))
            if op.get('upperRegisterEffect')!='preserved':_fail(label,'store-register','unchanged source vector',op)
            stores+=1
        else:_fail(label,'tail-direction','load or store',direction)
    if covered!=set(range(remaining)) or not head_written:
        _fail(label,'complete-tail-and-prefix-coverage',{'remaining':remaining,'headWritten':True},
            {'covered':len(covered),'headWritten':head_written,'firstMissing':next((i for i in range(remaining) if i not in covered),None)})
    return {'remainingBytes':remaining,'roundedBytes':rounded,'tableIndex':rounded//width,
        'allRemainderBytesEqualInitialSourceProved':True,'savedOriginalHeadStoredProved':True,
        'forwardSafeOverlapProved':True,'loads':loads,'stores':stores,
        'symbolicSelection':'original length L=P+remaining > chunk; P=alignmentAdvance+k*chunk, 1<=alignmentAdvance<=width; prior interval [alignmentAdvance,P) is already copied and cached head [0,width) and last [L-width,L) retain original source bytes',
        'coverageProof':'head covers [0,alignmentAdvance); prior loops cover [alignmentAdvance,P); affine tail identities cover [P,L). Each new source read is at/above P and every prior destination endpoint, or destination is disjoint above source endpoint.',
        'runtimeExecutionObserved':False}


def evaluate_forward_alignment(*,length,source,destination,width,chunk):
    values=(length,source,destination)
    if any(type(v) is not int or not 0<=v<1<<64 for v in values) or width not in (16,32) or type(chunk) is not int or chunk<width or chunk%width:
        return {'status':'refused','reason':'operand domain'}
    if length<=chunk or source+length>=1<<64 or destination+length>=1<<64:
        return {'status':'refused','reason':'large-path or pointer-endpoint selection'}
    advance=width-(destination&(width-1));remaining=length-advance
    loops=0 if remaining<=chunk else remaining//chunk
    tail=remaining-loops*chunk
    return {'status':'selected','alignmentAdvance':advance,'alignedDestination':destination+advance,
        'alignedSource':source+advance,'remainingAfterAlignment':remaining,'loopCount':loops,'tailBytes':tail,
        'finalDisplacement':advance+loops*chunk,'runtimeExecutionObserved':False}
