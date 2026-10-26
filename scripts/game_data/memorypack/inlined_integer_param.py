"""Initialized enum source and allocation paths, including independent mark loops."""
from scripts.game_data.memorypack.pooled_inline_sources import _Path
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.initializer_control import control_transfer
import hashlib
from scripts.game_data.levelscript_family_regenerate import Build
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.zero_wrapper_programs import _flag
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack import primitive_param as primitive, scalar_param_native as scalar, pooled_source_helper

def exact(g, text, encoded):
    row = g.row()
    if row['text'] != text or bytes.fromhex(row['bytes']) != bytes.fromhex(encoded):
        raise ValueError('targetEnum.operand-width-or-instruction:' + str(row)[:400])

def entry(rows, base):
    g = ProgramGrammar(rows, label='targetEnum.entry')
    g.take('mov rax, rsp', 'mov [rax+0x20], rbx', 'push rbp', 'push rsi', 'push rdi', 'push r14', 'push r15', 'sub rsp, 0x60')
    flag = _flag(g)
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    at = int(row['va'], 16)
    if len(raw) != 7 or raw[:3] != b'L\x8d=' or at + 7 + int.from_bytes(raw[3:], 'little', signed=True) != base:
        raise ValueError('targetEnum.image-base-origin')
    g.take('mov r14, rdx', 'mov rbx, rcx')
    edge = g.branch('jne')
    g.finish()
    return dict(initializationFlag=flag, initializedTarget=edge['target'], reader='entry RCX -> RBX', holder='entry RDX -> R14', imageBaseRegister='R15', entryRspSavedRbxOffset=32)

def flag(g):
    row = g.row()
    raw = bytes.fromhex(row['bytes'])
    if len(raw) != 7 or raw[:2] != b'\x83=' or raw[-1] != 0:
        raise ValueError('targetEnum.mark-flag')
    return int(row['va'], 16) + 7 + int.from_bytes(raw[2:6], 'little', signed=True)

def bitmap(g, role, field_offset=0):
    register = 'r14' if role == 'null' else 'r8'
    if role == 'null':
        g.take('shr r14, 0xc')
    elif role == 'wrapper':
        g.take('mov r8, r14')
    elif role == 'path':
        g.take('add r8, ' + hex(field_offset))
    elif role == 'constructor':
        g.take('lea r8, [rsi+0x10]', 'shr r8, 0xc')
    else:
        raise ValueError('targetEnum.bitmap-role')
    address = g.row()
    raw = bytes.fromhex(address['bytes'])
    prefix = b'H\x8d\x95' if role == 'constructor' else b'I\x8d\x97'
    if len(raw) != 7 or raw[:3] != prefix:
        raise ValueError('targetEnum.bitmap-base')
    rva = int.from_bytes(raw[3:], 'little', signed=True)
    if role not in ('null', 'constructor'):
        g.take('shr r8, 0xc')
    g.take('and ' + ('r14d' if register == 'r14' else 'r8d') + ', 0x1fffff', 'mov eax, ' + ('r14d' if register == 'r14' else 'r8d'), 'shr rax, 0x6', 'and ' + ('r14d' if register == 'r14' else 'r8d') + ', 0x3f', 'lea rdx, [rdx+rax*8]', 'prefetch [rdx]')
    while g.rows[g.at]['text'] == 'nop':
        g.take('nop')
    loop = g.at
    g.take('mov rax, [rdx]', 'mov rcx, rax')
    exact(g, 'bts rcx, ' + register, '4c0fabf1' if register == 'r14' else '4c0fabc1')
    exact(g, 'lock cmpxchg [rdx], rcx', 'f0480fb10a')
    edge = g.rows[g.at]
    g.branch(5, False)
    if control_transfer(edge)['target'] != loop:
        raise ValueError('targetEnum.bitmap-retry-edge')
    return dict(bitmapRva=rva, maxQwordIndex=32767, bitmapBytes=262144, retryTarget=loop, loopInvariant='Each retry only reloads/updates the same bitmap qword and RAX/RCX/flags. Reader, frame, field value and caller aliases are untouched; normal completion may take any finite retries.')

def source(rows, start, *, slots, allocated=False, path_mark=False, wrapper_mark=False, null=False):
    if set(slots) != {'constValue', 'idRef', 'paramSource', 'path'} or any((type(n) is not int or not 16 <= n <= 127 for n in slots.values())):
        raise ValueError('targetEnum.profile-slots')
    g = _Path(rows)
    g.at = start
    calls = {}
    stores = {}
    marks = []
    flags = []

    def call(name):
        row = g.row()
        flow = control_transfer(row)
        if flow['kind'] != 'call' or not row['text'].startswith('call 0x'):
            raise ValueError('targetEnum.direct-source:' + name)
        calls[name] = dict(site=int(row['va'], 16), target=flow['target'])

    def nonnull(register):
        g.take('test ' + register + ', ' + register)
        g.branch(4, False)
    exact(g, 'cmp [rbx+0x30], 0x1', '837b3001')
    g.branch(13, True)
    g.take('mov rax, [rbx+0x50]')
    exact(g, 'movzx esi, [rax]', '0fb630')
    g.take('mov edi, [rbx+0x30]', 'sub edi, 0x1')
    g.branch(9, True)
    for text, encoded in (('inc [rbx+0x50]', '48ff4350'), ('inc [rbx+0x40]', 'ff4340'), ('inc [rbx+0x44]', 'ff4344')):
        exact(g, text, encoded)
    g.take('mov [rbx+0x30], edi')
    exact(g, 'cmp sil, -0x1', '4080feff')
    g.branch(4, null)
    allocation = None
    if null:
        flags.append(flag(g))
        exact(g, 'mov [r14], 0x0', '49c70600000000')
        g.branch(4, not path_mark)
        if path_mark:
            marks.append(bitmap(g, 'null'))
    else:
        exact(g, 'cmp [r14], 0x0', '49833e00')
        g.branch(5, not allocated)
        if allocated:
            allocation = g.row()
            raw = bytes.fromhex(allocation['bytes'])
            if len(raw) != 7 or raw[:3] != b'H\x8b\r':
                raise ValueError('targetEnum.wrapper-allocation-context')
            call('allocateWrapper')
            g.take('mov rdi, rax')
            nonnull('rax')
            g.take('xor edx, edx', 'mov rcx, rax')
            call('constructor')
            flags.append(flag(g))
            exact(g, 'mov [r14], rdi', '49893e')
            g.branch(4, not wrapper_mark)
            if wrapper_mark:
                marks.append(bitmap(g, 'wrapper'))
        exact(g, 'cmp sil, 0x4', '4080fe04')
        g.branch(5, False)
        exact(g, 'cmp [rbx+0x30], 0x4', '837b3004')
        g.take('mov rdi, [r14]')
        g.branch(13, True)
        g.take('mov rax, [rbx+0x50]')
        exact(g, 'mov ebp, [rax]', '8b28')
        g.take('mov esi, [rbx+0x30]', 'add esi, -0x4')
        g.branch(9, True)
        for text, encoded in (('add [rbx+0x50], 0x4', '4883435004'), ('add [rbx+0x40], 0x4', '83434004'), ('add [rbx+0x44], 0x4', '83434404')):
            exact(g, text, encoded)
        g.take('mov [rbx+0x30], esi')
        nonnull('rdi')
        g.take('mov rax, [rdi+0x10]')
        nonnull('rax')
        stores['constValue'] = g.at
        exact(g, f'mov [rax+{slots['constValue']:#x}], ebp', '8968' + bytes((slots['constValue'],)).hex())
        for name in ('idRef', 'paramSource'):
            g.take('mov rcx, rbx', 'mov rdi, [r14]')
            call(name)
            nonnull('rdi')
            g.take('mov rcx, [rdi+0x10]')
            nonnull('rcx')
            stores[name] = g.at
            exact(g, f'mov [rcx+{slots[name]:#x}], eax', '8941' + bytes((slots[name],)).hex())
        g.take('mov rcx, rbx', 'mov rdi, [r14]')
        call('path')
        nonnull('rdi')
        g.take('mov r8, [rdi+0x10]')
        nonnull('r8')
        flags.append(flag(g))
        stores['path'] = g.at
        exact(g, f'mov [r8+{slots['path']:#x}], rax', '498940' + bytes((slots['path'],)).hex())
        g.branch(4, not path_mark)
        if path_mark:
            marks.append(bitmap(g, 'path', slots['path']))
            g.jump()
    g.take('mov rbx, [rsp+0xa8]', 'add rsp, 0x60', 'pop r15', 'pop r14', 'pop rdi', 'pop rsi', 'pop rbp', 'ret')
    return dict(selectedInstructions=g.seen, calls=calls, stores=stores, wireBytes=1 if null else 17, markFlags=flags, markLoops=marks, allocationLoad=allocation, nullOutput=null, allocated=allocated, pathMark=path_mark, wrapperMark=wrapper_mark)

def constructor(entry_rows, rows, start, base, *, id_ref_slot, active):
    prefix = ProgramGrammar(entry_rows, label='targetEnum.constructorEntry')
    prefix.take('push rbp', 'push rsi', 'sub rsp, 0x58')
    initialized = _flag(prefix)
    row = prefix.row()
    raw = bytes.fromhex(row['bytes'])
    at = int(row['va'], 16)
    if len(raw) != 7 or raw[:3] != b'H\x8d-' or at + 7 + int.from_bytes(raw[3:], 'little', signed=True) != base:
        raise ValueError('targetEnum.constructor-image-base')
    prefix.take('mov rsi, rcx')
    edge = prefix.branch('jne')
    prefix.finish()
    if edge['target'] != start:
        raise ValueError('targetEnum.constructor-initialized-edge')
    g = _Path(rows)
    g.at = start
    allocation = g.row()
    raw = bytes.fromhex(allocation['bytes'])
    if len(raw) != 7 or raw[:3] != b'H\x8b\r':
        raise ValueError('targetEnum.parameter-allocation-context')
    call = g.row()
    flow = control_transfer(call)
    if flow['kind'] != 'call':
        raise ValueError('targetEnum.parameter-allocator')
    g.take('test rax, rax')
    g.branch(4, False)
    cell = flag(g)
    exact(g, f'mov [rax+{id_ref_slot:#x}], 0xffffffff', 'c740' + bytes((id_ref_slot,)).hex() + 'ffffffff')
    exact(g, 'mov [rsi+0x10], rax', '48894610')
    g.branch(4, not active)
    mark = bitmap(g, 'constructor') if active else None
    g.take('add rsp, 0x58', 'pop rsi', 'pop rbp', 'ret')
    return dict(initializationFlag=initialized, allocationLoad=allocation, allocator=flow['target'], markFlag=cell, markLoop=mark, selectedInstructions=g.seen, allocatedField='declared Param instance in wrapper+16', idRefDefault=-1)

def derive(image, inputs, value_type):
    """Fresh selected-image proof; reuses parsed native indexes, never claim results."""
    pins = inputs
    build = Build(image, pins)
    ctx = NativeReferenceContext(image)
    base = image.pe.image_base
    value = value_type
    wrapped = 'Beyond.Gameplay.Actions.Param`1<' + value + '>'
    wrapper, = [w for w in build.wrappers.values() if w.wrapped_type == wrapped]
    scalar.need('inlinedIntegerParam', "check:[(m.name, m.declared_type) for m in wrapper.members] == [('constValue', value), ('idRef', 'int'), ('paramSource', 'int'), ('path', 'string')]", [('constValue', value), ('idRef', 'int'), ('paramSource', 'int'), ('path', 'string')], [(m.name, m.declared_type) for m in wrapper.members])
    scalar.need('inlinedIntegerParam', "check:wrapper.members[0].kind == 'enum' and wrapper.members[0].underlying_kind == 'scalar32' and (wrapper.members[0].width == 4)", True, bool(wrapper.members[0].kind == 'enum' and wrapper.members[0].underlying_kind == 'scalar32' and (wrapper.members[0].width == 4)))
    scalar.need('inlinedIntegerParam', "check:ctx.field(value + '::value__')[1] == 'int' and ctx.field(wrapper.name + '::__instance') == (wrapper.name, wrapped, 16)", True, bool(ctx.field(value + '::value__')[1] == 'int' and ctx.field(wrapper.name + '::__instance') == (wrapper.name, wrapped, 16)))
    methods = {image.metadata.string(m.name_index): m for m in image.metadata.methods_for(image.metadata.types[wrapper.type_definition])}

    def native(name):
        method = methods[name]
        pointer = image.method_pointer_va(method)
        ranges = sorted((tuple(p['runtimeTriple'][:2]) for p in image.unwind_index.family(pointer - base)['ranges']))
        scalar.need('inlinedIntegerParam', 'check:ranges[0][0] == pointer - base and all((a[1] == b[0] for a, b in zip(ranges, ranges[1:])))', True, bool(ranges[0][0] == pointer - base and all((a[1] == b[0] for a, b in zip(ranges, ranges[1:])))))
        rows = build.body._decode(pointer, base + ranges[-1][1] - pointer)
        windows = [dict(startRva=a, endRva=b, sha256=hashlib.sha256(image.pe.bytes_at_va(base + a, b - a)).hexdigest().upper()) for a, b in ranges]
        return (method, pointer, ranges, rows, windows)
    slots = {}
    setters = {}
    mark_flag = None
    for field in ('constValue', 'idRef', 'paramSource', 'path'):
        method, pointer, ranges, rows, windows = native('set___' + field + '__')
        kind = value if field == 'constValue' else 'string' if field == 'path' else 'int'
        scalar.owned_method_abi(image, ctx, method.index, wrapper.type_definition, ('void', 1, False), [(kind, 17 if field == 'constValue' else 14 if field == 'path' else 8, field == 'path')], 'targetEnum.setter')
        if field == 'path':
            slot = bytes.fromhex(rows[5]['bytes'])[-1]
            g = _Path(rows)
            g.take('sub rsp, 0x28', 'mov r8, [rcx+0x10]', 'test r8, r8')
            g.branch(4, False)
            flag = g.row()
            raw = bytes.fromhex(flag['bytes'])
            scalar.need('inlinedIntegerParam', "check:len(raw) == 7 and raw[:2] == b'\\x83=' and (raw[-1] == 0)", True, bool(len(raw) == 7 and raw[:2] == b'\x83=' and (raw[-1] == 0)))
            mark_flag = int(flag['va'], 16) + 7 + int.from_bytes(raw[2:6], 'little', signed=True)
            exact(g, f'mov [r8+{slot:#x}], rdx', '498950' + bytes((slot,)).hex())
            g.branch(4, True)
            g.take('add rsp, 0x28', 'ret')
        else:
            slot = bytes.fromhex(rows[4]['bytes'])[-1]
            g = ProgramGrammar(rows, label='targetEnum.integerSetter')
            g.take('sub rsp, 0x28', 'mov rax, [rcx+0x10]', 'test rax, rax')
            g.branch('je', 'null')
            actual = g.take(f'mov [rax+{slot:#x}], edx')
            scalar.need('inlinedIntegerParam', "check:bytes.fromhex(actual['bytes']) == b'\\x89P' + bytes((slot,))", b'\x89P' + bytes((slot,)), bytes.fromhex(actual['bytes']))
            g.take('add rsp, 0x28', 'ret')
            g.mark('null')
            g.pattern('call 0x[0-9a-f]+')
            g.take('int3')
            g.finish()
        slots[field] = slot
        setters[field] = dict(methodIndex=method.index, codeWindows=windows, selectedInstructions=getattr(g, 'seen', None))
    occupied = [n for field, width in (('constValue', 4), ('idRef', 4), ('paramSource', 4), ('path', 8)) for n in range(slots[field], slots[field] + width)]
    scalar.need('inlinedIntegerParam', 'check:len(set(occupied)) == 20 and all((16 <= n < 128 for n in occupied))', True, bool(len(set(occupied)) == 20 and all((16 <= n < 128 for n in occupied))))
    method, pointer, ranges, allrows, windows = native('Deserialize')
    primitive.reader_abi(image, ctx, method, wrapper)
    first = build.body._decode(pointer, ranges[0][1] - ranges[0][0])
    ingress = entry(first, base)
    hot = ingress['initializedTarget']
    rows = build.body._decode(hot, base + ranges[-1][1] - hot)
    variants = []
    for allocated in (False, True):
        for path_mark in (False, True):
            for wrapper_mark in (False, True) if allocated else (False,):
                result = source(rows, hot, slots=slots, allocated=allocated, path_mark=path_mark, wrapper_mark=wrapper_mark)
                variants.append(result)
    for active in (False, True):
        variants.append(source(rows, hot, slots=slots, null=True, path_mark=active))
    positive = variants[0]
    null = variants[-2]
    scalar.need('inlinedIntegerParam', "check:{cell for result in variants for cell in result['markFlags']} == {mark_flag}", {mark_flag}, {cell for result in variants for cell in result['markFlags']})
    constructors = []
    for name in ('.ctor', 'CreateInstance'):
        m, p, r, _, w = native(name)
        prefix = build.body._decode(p, r[0][1] - r[0][0])
        edge = control_transfer(prefix[-1])
        start = edge['target']
        hot_rows = build.body._decode(start, base + r[-1][1] - start)
        scalar.owned_method_abi(image, ctx, m.index, wrapper.type_definition, ('void', 1, False), [], 'targetEnum.' + name)
        for active in (False, True):
            result = constructor(prefix, hot_rows, start, base, id_ref_slot=slots['idRef'], active=active)
            usage = derive_typed_usage_context(image, int(result['allocationLoad']['va'], 16) - base, label='targetEnum.parameterAllocation')
            scalar.need('inlinedIntegerParam', "check:usage['tag'] == 1 and usage['typeName'] == wrapped and (result['markFlag'] == mark_flag)", True, bool(usage['tag'] == 1 and usage['typeName'] == wrapped and (result['markFlag'] == mark_flag)))
            constructors.append(dict(name=name, methodIndex=m.index, ownedWindows=w, allocationContext=usage, program=result))
    for result in variants:
        if result['allocated']:
            usage = derive_typed_usage_context(image, int(result['allocationLoad']['va'], 16) - base, label='targetEnum.wrapperAllocation')
            scalar.need('inlinedIntegerParam', "check:usage['tag'] == 1 and usage['typeName'] == wrapper.name and (result['calls']['constructor']['target'] == image.method_pointer_va(methods['.ctor']))", True, bool(usage['tag'] == 1 and usage['typeName'] == wrapper.name and (result['calls']['constructor']['target'] == image.method_pointer_va(methods['.ctor']))))
            scalar.need('inlinedIntegerParam', "check:result['calls']['allocateWrapper']['target'] == constructors[0]['program']['allocator']", constructors[0]['program']['allocator'], result['calls']['allocateWrapper']['target'])
    loops = [loop for r in variants for loop in r['markLoops']] + [r['program']['markLoop'] for r in constructors if r['program']['markLoop']]
    bitmap_rva, = {loop['bitmapRva'] for loop in loops}
    sections = [s for s in image.pe.sections if s['characteristics'] & 2147483648 and s['virtualAddress'] <= bitmap_rva and (bitmap_rva + 262144 <= s['virtualAddress'] + s['virtualSize'])]
    scalar.need('inlinedIntegerParam', 'check:len(sections) == 1', 1, len(sections))
    scalar.need('inlinedIntegerParam', "check:positive['calls']['idRef']['target'] == positive['calls']['paramSource']['target']", positive['calls']['paramSource']['target'], positive['calls']['idRef']['target'])
    offsets = scalar.reader_offsets(image, 'targetEnum')
    scalar.need('inlinedIntegerParam', 'check:offsets == dict(currentPtr=80, bufferLength=48, advancedCount=64, consumed=68)', dict(currentPtr=80, bufferLength=48, advancedCount=64, consumed=68), offsets)
    target = positive['calls']['idRef']['target']
    end = build.body.extents[target]
    raw = image.pe.bytes_at_va(target, end - target)
    decoded = build.body._decode(target, end - target)
    integer = dict(window=dict(startRva=target - base, endRva=end - base, sha256=hashlib.sha256(raw).hexdigest().upper()), instructions=[[int(r['va'], 16) - base, bytes.fromhex(r['bytes']).hex().upper()] for r in decoded])
    scalar.integer_source(image, integer, offsets, 'targetEnum.integer')
    pooled = pooled_source_helper.validate_on_image(image, positive['calls']['path']['target'], pins)
    scalar.need('inlinedIntegerParam', "check:pooled['wireEncoding'] == 'int32-pool-index'", 'int32-pool-index', pooled['wireEncoding'])
    getter = methods['GetValue']
    pointer = image.method_pointer_va(getter)
    raw = image.pe.bytes_at_va(pointer, 5)
    rows = build.body._decode(pointer, 5)
    scalar.owned_method_abi(image, ctx, getter.index, wrapper.type_definition, (wrapped, 21, True), [], 'inlinedIntegerParam.getter')
    scalar.program(image, [[int(r['va'], 16) - base, bytes.fromhex(r['bytes']).hex().upper()] for r in rows], [b'H\x8bA\x10', b'\xc3'], 'inlinedIntegerParam.getter')
    getter_proof = dict(methodIndex=getter.index, pointerRva=pointer - base, bytes=raw.hex().upper(), field='declared wrapper::__instance', fieldOffset=16, returnedBits=64)
    for row in constructors:
        scalar.ordinary(image, ctx.type_pointer(row['allocationContext']['typeIndex']), 21, 'inlinedIntegerParam.allocatedParameter', reference=True)
    return dict(schema='endfield.memorypack-inlined-int32-enum-param-proof.v1', wrappedType=wrapped, wrapperName=wrapper.name, memberCount=4, rawSize=4, pathEncoding='int32-pool-index', ownedWindows=windows, ingress=ingress, ownedSetterSlots=slots, setters=setters, sourcePaths=variants, constructors=constructors, getter=getter_proof, bitmapSection=sections[0], int32Source=integer, pooledSource=pooled, evidenceBoundary=dict(direct='Typed Int32-backed enum and owned setter slots; initialized buffered header/count, raw constant, two Int32 binding reads, pooled path, FF output, fresh wrapper/parameter construction, pointer getter and both bitmap-mark branches.', conditional='Initialized metadata flags; valid disjoint source/reader/output/frame/heap/bitmap, sufficient contiguous input and nonoverflowing counters, matching coherent StringPool, compatible normal ABI-preserving allocation and helpers; atomic retry loops complete normally. Runtime metadata inflation and provider/holder selection are not observed.', unresolved=['cold metadata initialization and refill paths', 'live generic provider/cache selection', 'enclosing action/source/corpus admission and camera execution']))
