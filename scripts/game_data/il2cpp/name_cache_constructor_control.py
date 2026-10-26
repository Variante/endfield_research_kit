"""Complete cache-constructor defaults under explicit valid-storage conditions.

Allocation success and live execution are not inferred. The selected threshold
products are exact binary32 exponent shifts, so no host float rounding is used.
"""
from __future__ import annotations
from fractions import Fraction
from .integer_addressing import _address, _prefix, _required
from .integer_effects import decode_immediate_memory_store
from .word_immediate_stores import decode_word_immediate_store
from .scalar_conversions import decode_scalar_signed_conversion
from .type_data_initialization_control import _complete
from .method_carrier_resolution import _memory
from .name_cache_marker_iterator_control import _SplitGrammar, _initializer

LABEL = 'nameCacheConstructorControl'


def exact_scaled_single(bits, capacity):
    """Positive normal binary32 times an exactly representable power of two."""
    if type(bits) is not int or not 0 < bits < 1 << 31:
        raise ValueError(LABEL + '.positive-normal-single-domain')
    exponent = (bits >> 23) & 255
    if not 1 <= exponent <= 254:
        raise ValueError(LABEL + '.positive-normal-single-domain')
    if type(capacity) is not int or not 0 < capacity <= 1 << 24 or capacity & (capacity - 1):
        raise ValueError(LABEL + '.exact-capacity-domain')
    shift = capacity.bit_length() - 1
    if exponent + shift > 254:
        raise ValueError(LABEL + '.scaled-single-overflow')
    significand = (1 << 23) | (bits & ((1 << 23) - 1))
    power = exponent - 127 - 23 + shift
    value = Fraction(significand << power, 1) if power >= 0 else Fraction(significand, 1 << -power)
    return {'resultBits': bits + (shift << 23), 'numerator': value.numerator,
            'denominator': value.denominator, 'truncatedInteger': value.numerator // value.denominator,
            'allMxcsrRoundingModesHaveSameProduct': True}


def _immediate(g, bits, base, displacement, value):
    row = g.row(); raw = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    parsed = decode_word_immediate_store(raw, 0, at) if bits == 16 else decode_immediate_memory_store(raw, 0, at)
    f = parsed[0]['immediateMemoryStoreOperation'] if parsed and parsed[1] == len(raw) else {}
    a = f.get('destinationAddress', {})
    if (f.get('bits'), f.get('immediateWord'), a.get('base'), a.get('index'),
        a.get('displacement'), a.get('ripRelative')) != (bits, value, base, None, displacement, False):
        g.fail('immediate-field-store', (bits, base, displacement, value), row)


def _single(g, opcode, destination, *, source=None, memory_base=None, displacement=0, absolute=None):
    row = g.row(); raw = bytes.fromhex(row['bytes']); at_va = int(row['va'], 16)
    if raw[:1] != b'\xf3': g.fail('single-prefix', 'F3', row)
    at, rex = _prefix(raw, 1)
    if rex & 8 or raw[at:at + 2] != bytes((0x0f, opcode)): g.fail('single-opcode', opcode, row)
    at += 2; modrm = _required(raw, at, 1, 0, LABEL + '.single')[0]; at += 1
    register = ((modrm >> 3) & 7) | ((rex & 4) << 1)
    if register != destination: g.fail('single-destination', destination, row)
    if source is not None:
        if modrm >> 6 != 3 or ((modrm & 7) | ((rex & 1) << 3)) != source: g.fail('single-source', source, row)
    else:
        if modrm >> 6 == 3: g.fail('single-memory', 'memory operand', row)
        a, at = _address(raw, at, modrm, rex, 0, LABEL + '.single')
        if absolute is None:
            if (a['base'], a['index'], a['displacement'], a['ripRelative']) != (memory_base, None, displacement, False):
                g.fail('single-memory', (memory_base, displacement), row)
        elif not a['ripRelative'] or at_va + at + a['displacement'] != absolute:
            g.fail('single-global', absolute, row)
    if at != len(raw): g.fail('single-span', at, row)


def _conversion(g, operation, destination, source):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    parsed = decode_scalar_signed_conversion(raw, 0, int(row['va'], 16))
    f = parsed[0]['scalarSignedConversionOperation'] if parsed and parsed[1] == len(raw) else {}
    if (f.get('operation'), f.get('destinationRegister'), f.get('sourceRegister'), f.get('signedIntegerBits')) != (operation, destination, source, 64):
        g.fail('signed-single-conversion', (operation, destination, source, 64), row)


def _negative(g, label):
    row = g.row(); b = bytes.fromhex(row['bytes']); at = int(row['va'], 16)
    if len(b) != 2 or b[0] != 0x78: g.fail('signed-negative-branch', 'JS rel8', row)
    g.edges.append((at + 2 + int.from_bytes(b[1:], 'little', signed=True), label, row))


def _base(rows, c, image_base):
    l, d = c['layout'], c['defaults']; g = _SplitGrammar(rows, label=LABEL + '.base')
    g.take('mov rdx, rcx', 'xorps xmm0, xmm0', 'xor ecx, ecx')
    for field in ('upperThreshold', 'lowerThreshold'): _memory(g, 'store', 'rcx', 8, 'rdx', l[field])
    _memory(g, 'store', 'cx', 2, 'rdx', l['flags']); _memory(g, 'store', 'cl', 1, 'rdx', l['flags'] + 2)
    _memory(g, 'store', 'ecx', 4, 'rdx', l['generation'])
    for field in ('upperFactor', 'lowerFactor'): _immediate(g, 32, 'rdx', l[field], d[field + 'Bits'])
    _memory(g, 'load', 'eax', 1, 'r9', 0); _memory(g, 'store', 'al', 1, 'rdx', l['copiedByte'])
    _memory(g, 'store', 'ecx', 4, 'rdx', l['removedHeader'])
    for field in ('removedNamespace', 'removedName'): _memory(g, 'store', 'rcx', 8, 'rdx', l[field])
    _immediate(g, 64, 'rdx', l['capacity'], d['capacity'])
    for field in ('removedCount', 'usedCount'): _memory(g, 'store', 'rcx', 8, 'rdx', l[field])
    _memory(g, 'store', 'ecx', 4, 'rdx', l['freeHeader'])
    for field in ('freeNamespace', 'freeName', 'freeRecord'): _memory(g, 'store', 'rcx', 8, 'rdx', l[field])
    _memory(g, 'load', 'r8', 8, 'rdx', l['capacity']); _memory(g, 'store', 'rcx', 8, 'rdx', l['nodes'])
    g.take('test r8, r8'); _negative(g, 'upperUnsigned')
    g.mark('upperConvert'); _conversion(g, 'cvtsi2ss', 'xmm0', 'r8')
    g.mark('upperMultiply'); _single(g, 0x59, 0, memory_base='rdx', displacement=l['upperFactor'])
    g.take('xor ecx, ecx', 'mov r9, 0x8000000000000000')
    _single(g, 0x10, 1, absolute=image_base + c['thresholdConstant']['rva'])
    g.take('comiss xmm0, xmm1'); g.branch('jb', 'upperTruncate')
    _single(g, 0x5c, 0, source=1); g.take('comiss xmm0, xmm1'); g.branch('jae', 'upperTruncate')
    g.take('mov rcx, r9'); g.mark('upperTruncate'); _conversion(g, 'cvttss2si', 'rax', 'xmm0')
    g.take('xorps xmm0, xmm0', 'add rax, rcx'); _memory(g, 'store', 'rax', 8, 'rdx', l['upperThreshold'])
    g.take('test r8, r8'); _negative(g, 'lowerUnsigned')
    g.mark('lowerConvert'); _conversion(g, 'cvtsi2ss', 'xmm0', 'r8')
    g.mark('lowerMultiply'); _single(g, 0x59, 0, memory_base='rdx', displacement=l['lowerFactor'])
    g.take('xor ecx, ecx', 'comiss xmm0, xmm1'); g.branch('jb', 'lowerTruncate')
    _single(g, 0x5c, 0, source=1); g.take('comiss xmm0, xmm1'); g.branch('jae', 'lowerTruncate')
    g.take('mov rcx, r9'); g.mark('lowerTruncate'); _conversion(g, 'cvttss2si', 'rax', 'xmm0')
    g.take(f'mov byte [rdx+0x{l["flags"]:x}], 0x0', 'add rax, rcx')
    _memory(g, 'store', 'rax', 8, 'rdx', l['lowerThreshold']); g.take('mov rax, rdx', 'ret')
    g.mark('upperUnsigned'); g.take('mov rax, r8', 'mov rcx, r8', 'shr rcx, 0x1', 'and eax, 0x1', 'or rcx, rax')
    _conversion(g, 'cvtsi2ss', 'xmm0', 'rcx'); _single(g, 0x58, 0, source=0); g.branch('jmp', 'upperMultiply')
    g.mark('lowerUnsigned'); g.take('mov rax, r8', 'and r8d, 0x1', 'shr rax, 0x1', 'or rax, r8')
    _conversion(g, 'cvtsi2ss', 'xmm0', 'rax'); _single(g, 0x58, 0, source=0); g.branch('jmp', 'lowerMultiply'); g.finish()


def _constructor(rows, c, image_base):
    l, d, calls = c['layout'], c['defaults'], c['externalCalls']; g = _SplitGrammar(rows, label=LABEL + '.constructor')
    _memory(g, 'store', 'rcx', 8, 'rsp', 8)
    g.take('push rbx', 'sub rsp, 0xc0', 'mov rbx, rcx', 'lea r9, [rsp+0xd8]')
    g.call(image_base + c['functions']['baseInitializer']['entryRva']); g.take('nop', f'cmp qword [rbx+0x{l["removedCount"]:x}], 0x0')
    g.branch('jne', 'cold')
    g.mark('markers'); _immediate(g, 16, 'rbx', l['flags'] + 1, d['markerFlagsWord'])
    _immediate(g, 32, 'rbx', l['removedHeader'], d['removedHeader']); g.take('xor eax, eax')
    for field in ('removedNamespace', 'removedName'): _memory(g, 'store', 'rax', 8, 'rbx', l[field])
    g.take('xorps xmm0, xmm0'); _immediate(g, 32, 'rbx', l['freeHeader'], d['freeHeader'])
    _memory(g, 'store', 'xmm0', 16, 'rbx', l['freeNamespace']); _memory(g, 'store', 'rax', 8, 'rbx', l['freeRecord'])
    _memory(g, 'load', 'rcx', 8, 'rbx', l['capacity']); g.take('shl rcx, 0x5'); g.call(image_base + calls['allocator'])
    _memory(g, 'store', 'rax', 8, 'rbx', l['nodes']); _memory(g, 'load', 'r8', 8, 'rbx', l['capacity'])
    g.take('shl r8, 0x5', 'add r8, rax', 'mov rdx, rax', 'mov rcx, rbx')
    g.call(image_base + c['functions']['nodeInitializer']['entryRva'])
    g.take('nop', 'mov rax, rbx', 'add rsp, 0xc0', 'pop rbx', 'ret')
    g.mark('cold'); g.take(f'mov r8d, 0x{d["capacity"]:x}', 'mov rdx, rbx', 'lea rcx, [rsp+0x40]')
    g.call(image_base + calls['rehash']); g.take('lea rdx, [rsp+0x40]', 'mov rcx, rbx'); g.call(image_base + calls['swap'])
    g.take('nop', 'mov rcx, [rsp+0xb8]', 'test rcx, rcx'); g.branch('je', 'coldReturn')
    g.call(image_base + calls['free']); g.take('nop'); g.mark('coldReturn'); g.branch('jmp', 'markers'); g.finish()


def validate_name_cache_constructor(programs, constant_raw, *, image_base, contract):
    c = contract
    if set(programs) != {'constructor', 'baseInitializer', 'nodeInitializer'} or set(c['functions']) != set(programs):
        raise ValueError(LABEL + '.function-membership')
    l, d = c['layout'], c['defaults']
    if (l['flags'], l['removedCount'], l['usedCount'], l['capacity'], l['freeHeader'], l['nodes']) != (24, 64, 72, 80, 88, 120):
        raise ValueError(LABEL + '.selected-cache-layout')
    if constant_raw != bytes.fromhex(c['thresholdConstant']['rawHex']) or int.from_bytes(constant_raw, 'little') != 0x5f000000:
        raise ValueError(LABEL + '.threshold-constant-not-two-to-63')
    graphs = {role: _complete(rows, image_base + c['functions'][role]['entryRva']) for role, rows in programs.items()}
    for role in ('baseInitializer', 'nodeInitializer'):
        if graphs[role]['calls'] or graphs[role]['traps']: raise ValueError(LABEL + '.closed-child:' + role)
    _base(programs['baseInitializer'], c, image_base)
    _constructor(programs['constructor'], c, image_base)
    _initializer(programs['nodeInitializer'], {
        'cacheFreeHeader': l['freeHeader'], 'cacheFreeStrings': l['freeNamespace'],
        'cacheFreeRecord': l['freeRecord'], 'nodeHeader': 0, 'nodeNamespace': 8,
        'nodeRecord': 24, 'nodeBytes': 32})
    upper, lower = (exact_scaled_single(d[k + 'Bits'], d['capacity']) for k in ('upperFactor', 'lowerFactor'))
    for p in (upper, lower):
        if Fraction(p['numerator'], p['denominator']) >= 1 << 63: raise ValueError(LABEL + '.signed-threshold-range')
    if d['freeHeader'] == 0 or d['removedHeader'] == 0 or d['freeHeader'] == d['removedHeader']:
        raise ValueError(LABEL + '.distinct-nonzero-markers')
    return {'status': 'complete-conditional-constructor-defaults-proved',
        'codeInstructions': sum(len(rows) for rows in programs.values()),
        'baseCapacity': d['capacity'], 'upperThreshold': upper, 'lowerThreshold': lower,
        'baseRemovedAndUsedCountsZeroProved': True,
        'baseNormalReturnPreservesReceiverAndNonvolatileRegistersProved': True,
        'constructorColdRehashUnselectedUnderBasePostconditionsProved': True,
        'defaultMarkersHaveDistinctNonzeroHeadersProved': True,
        'defaultMarkerStringsAndAuxiliaryZeroProved': True,
        'allocatorRequestedBytes': 32 * d['capacity'],
        'conditionalReturnedStorageInitializedAsFreeNodesProved': True,
        'nodeCopiedBytes': 28, 'nodePaddingBytesUnconstrained': 4,
        'copiedStackByteValueKnown': False, 'wholeCacheBytesInitialized': False,
        'allocatorSuccessObserved': False, 'allocatorNoninterferenceProved': False,
        'capacitySufficientForFuturePopulationProved': False,
        'duplicateInsertionHistoryProved': False, 'lookupReturnedSystemInt32ClassProved': False,
        'wholeRootAdmitted': False, 'runtimeExecutionKnown': False,
        'conditions': c['conditionalDomain']}
