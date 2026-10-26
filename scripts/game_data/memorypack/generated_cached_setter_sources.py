"""Exact larger-frame initialized coherent generated setter programs.

Only the current selected warm path is admitted. Metadata initialization,
cache refresh, incompatible classes and null exits remain independent; no
table or neighboring body is claimed from its address or method name.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL = 'generatedCachedSetter'


def need(check, condition, detail=None):
    if not condition:
        raise ValueError(LABEL + '.' + check + ':' + str(detail)[:500])


def _equal(g, equal):
    first = g.bytes.get(g.at)
    pair = bytes(g.bytes.get(g.at + i, 0) for i in range(2))
    if first in (0x74, 0x75):
        g.branch(format(first, '02x'), equal if first == 0x74 else not equal, 1)
    else:
        need('literal-equality-predicate', pair in (b'\x0f\x84', b'\x0f\x85'))
        g.branch(pair.hex(), equal if pair[-1] == 0x84 else not equal)


def program(regions, entry, *, field, mode, base_slot, cache_slot, image_base,
            path_factory=None):
    """Full literal large-frame same-pointer byte/DWORD setter and return."""
    need('literal-field-cache-domain', type(field) is int and 16 <= field < 1 << 31 and
         type(base_slot) is int and type(cache_slot) is int and
         16 <= base_slot < cache_slot < 128 and type(image_base) is int)
    need('callable-only-path-factory', path_factory is None or callable(path_factory))
    need('explicit-value-mode', mode in ('normalized-byte-return', 'int32-return'))
    g = (path_factory or BytesPath)(regions, entry)
    rbp = bytes(g.bytes.get(g.at + i, 0) for i in range(2)) == b'\x40\x55'
    if rbp:
        g.take('4055', '4883ec50', '48895c2468',
               '0fb6ea' if mode == 'normalized-byte-return' else '8bea',
               '4889742470', '488bf1', '48897c2448', '33ff')
        flag = g.relative('40383d')
    else:
        need('rbx-mode', mode == 'int32-return')
        g.take('4053', '4883ec50', '48896c2468', '8bda', '4889742470',
               '488be9', '33f6', '48897c2448')
        flag = g.relative('403835')
    g.take('4c89742440')
    need('current-image-base-lea', g.relative('4c8d35') == image_base)
    _equal(g, False)
    b = bytes((base_slot,)).hex(); c = bytes((cache_slot,)).hex()
    # EDI/ESI was zeroed before the flag check and no intervening instruction
    # can overwrite its full register. Both qword comparisons prove identity.
    g.take(('48397e' if rbp else '483975') + c); _equal(g, False)
    g.take(('488b46' if rbp else '488b45') + b,
           ('483946' if rbp else '483945') + c); _equal(g, True)
    g.take(('488b46' if rbp else '488b45') + c, '4c8b742440', '488b7c2448', '488b742470',
           '488b5c2468' if rbp else '488b6c2468', '4885c0')
    _equal(g, False)
    prefix = ('408868' if field < 128 else '4088a8') if mode == 'normalized-byte-return' else \
             ('8968' if field < 128 else '89a8') if rbp else \
             ('8958' if field < 128 else '8998')
    g.take(prefix + field.to_bytes(1 if field < 128 else 4, 'little', signed=True).hex(),
           '4883c450', '5d' if rbp else '5b', 'c3')
    return dict(selectedBytes=g.seen, initializedFlag=flag,
        initializedFlagCompare='actual byte memory compared with zeroed DIL' if rbp else 'actual byte memory compared with zeroed SIL', fieldOffset=field,
        baseSlot=base_slot, cacheSlot=cache_slot, storedBytes=1 if mode == 'normalized-byte-return' else 4,
        incomingRegister='dl' if mode == 'normalized-byte-return' else 'edx',
        savedValueRegister='ebp' if rbp else 'ebx', originalRegister='rax',
        savedHomes=dict(rbp=-8, rbx=16, rsi=24, rdi=-16, r14=-24) if rbp else dict(rbx=-8, rbp=16, rsi=24, rdi=-16, r14=-24),
        selectedFrameBytes=88, entryRspRestored=True,
        nonvolatilesRestored=True, nonvolatileRegistersRestored=['rbp', 'rbx', 'rsi', 'rdi', 'r14'],
        normalIncomingValueStoredUnchanged=True, refreshAdmitted=False,
        metadataInitializationAdmitted=False, normalReturnViaBarrier=False,
        condition='Ready exact metadata flag, equal nonnull compatible current base/cache references, valid disjoint frame and named field. Every incoming declared byte/DWORD bit is retained through the saved low register and stored unchanged; boolean normalization must already be proved at the actual source. Cold initialization, empty/different cache and null exits are not admitted.')


def int32_program(regions, entry, *, field, base_slot, cache_slot, image_base, path_factory=None):
    return program(regions, entry, field=field, mode='int32-return', base_slot=base_slot,
                   cache_slot=cache_slot, image_base=image_base, path_factory=path_factory)
