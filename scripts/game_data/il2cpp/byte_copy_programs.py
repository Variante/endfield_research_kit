"""Symbolically prove bounded straight-line memory-copy payload programs.

Every byte is a distinct initial-source token. This is a program proof over
decoded operands, not an execution or a sampled byte comparison. Address
providers, branch selection, original instruction spans and returns are the
consumer's responsibility.
"""
from __future__ import annotations


def prove_byte_copy_moves(operations, *, length, pointers, scalars=None, overlap='forward-safe', label='byte-copy'):
    def fail(check, expected, actual):
        raise ValueError(f'{label}.{check}: expected={str(expected)[:256]} actual={str(actual)[:384]}')
    if type(length) is not int or length < 0 or overlap not in ('forward-safe','arbitrary'):
        fail('selection-domain','nonnegative byte count and explicit overlap selection',(length,overlap))
    scalars = dict(scalars or {}); registers = {}; clobbered = set(); covered = set()
    previous_store_end = None; has_store = False; all_reads_first = True; loads = stores = 0
    ranges = []
    for number, operation in enumerate(operations):
        direction = operation.get('direction'); address = operation.get('address', {})
        base = address.get('base'); index = address.get('index'); size = operation.get('memoryBytes')
        if (direction not in ('load','store') or type(size) is not int or size <= 0
                or address.get('addressBits') != 64 or address.get('ripRelative') is not False
                or base not in pointers or base in clobbered or operation.get('writesFlags') is not False):
            fail('memory-operand', 'selected unchanged pointer, default address width and exact move', {'instruction':number,'operation':operation})
        start = address.get('displacement')
        if type(start) is not int: fail('displacement','signed integer',start)
        if index is not None:
            if index not in scalars or index in clobbered or address.get('scale') != 1:
                fail('scalar-index','unchanged selected scalar with scale one',address)
            start += scalars[index]
        if not 0 <= start <= start+size <= length:
            fail('payload-range',f'within [0,{length})',(start,start+size))
        if pointers[base] != ('source' if direction=='load' else 'destination'):
            fail('payload-role',direction,pointers[base])
        if operation.get('requiredAlignmentBytes') != 1 or operation.get('nonTemporalHint') is not False:
            fail('move-selection','unaligned temporal memory move',operation)
        backing = operation.get('backingRegister'); bits = operation.get('registerBits'); bit_offset = operation.get('registerBitOffset')
        if (not isinstance(backing,str) or type(bits) is not int or bits not in (8,16,32,64,128,256)
                or type(bit_offset) is not int or bit_offset not in (0,8) or bits%8 or bit_offset%8):
            fail('register-width','supported byte-addressable register range',operation)
        width = bits//8; register_at = bit_offset//8
        total = 32 if backing.startswith('vector') else 8
        if register_at+width > total: fail('register-range',total,(register_at,width))
        value = registers.setdefault(backing,[('unknown',backing,i) for i in range(total)])
        if direction=='load':
            if has_store:
                all_reads_first=False
                if overlap=='arbitrary' or previous_store_end > start:
                    fail('future-source-safety','all earlier destination ends at/below next source start',{'priorStoreEnd':previous_store_end,'sourceStart':start,'overlap':overlap})
            if size > width: fail('load-width','memory width no larger than register write',operation)
            extension = operation.get('valueExtension')
            if size < width and extension != 'zero': fail('load-extension','proved zero extension',operation)
            if extension not in (None,'zero'): fail('load-extension','none or zero',extension)
            payload = [('source',i) for i in range(start,start+size)]
            value[register_at:register_at+width] = payload+[('constant',0)]*(width-size)
            upper = operation.get('upperRegisterEffect')
            if not isinstance(upper,str):fail('upper-register','explicit decoded register effect',upper)
            if bits==32 and not backing.startswith('vector'):
                if upper != 'zero upper 32 bits': fail('upper-register','zero upper 32 bits',upper)
                value[4:8]=[('constant',0)]*4
            elif bits==64 and not backing.startswith('vector'):
                if upper != 'replaced full register': fail('upper-register','full register replacement',upper)
            elif not backing.startswith('vector') and upper != 'preserved':
                fail('upper-register','partial register preserves remaining bytes',upper)
            elif backing.startswith('vector') and upper.startswith('zero bits above'):
                value[width:]=[('constant',0)]*(total-width)
            elif backing.startswith('vector') and upper != 'preserved':
                fail('upper-register','preserved or proved vector upper zeroing',upper)
            clobbered.add(backing);loads+=1
        else:
            if size > width or operation.get('valueExtension') is not None or operation.get('upperRegisterEffect') != 'preserved':
                fail('store-register','unchanged source register with sufficient captured bytes',operation)
            actual=value[register_at:register_at+size];expected=[('source',i) for i in range(start,start+size)]
            if actual != expected:fail('stored-source-byte-identity',expected,actual)
            covered.update(range(start,start+size));has_store=True;stores+=1
            previous_store_end=max(previous_store_end or 0,start+size)
        ranges.append({'direction':direction,'start':start,'end':start+size,'backingRegister':backing})
    if covered != set(range(length)):
        fail('complete-byte-coverage',length,{'covered':len(covered),'firstMissing':next((i for i in range(length) if i not in covered),None)})
    return {'byteCount':length,'allBytesEqualInitialSourceProved':True,'payloadRangesInBoundsProved':True,
        'allReadsPrecedeStores':all_reads_first,'arbitraryOverlapSafe':all_reads_first,
        'forwardSafeOverlapProved':True,'loads':loads,'stores':stores,'ranges':ranges,
        'proof': 'Distinct symbolic initial-source byte identities; every store has the matching destination offset and the complete byte range is covered. For interleaved loads, all previous relative destination endpoints are at/below the next relative source start, so destination <= source cannot overwrite an unread byte; destination >= source+length is disjoint.',
        'runtimeExecutionObserved':False}
