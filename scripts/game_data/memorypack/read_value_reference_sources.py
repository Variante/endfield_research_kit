"""Owned ReadValue and inlined reference-adapter paths through complete returns.

These proofs require compatible initialized runtime contexts, selected cache
and provider results, normal correctly typed calls, and the ordinary Win64
nonvolatile/stack ABI. They observe no runtime selection or global effects and
admit no child grammar, list or root. Physical entries are bound by call bytes,
independently of the names on supplied MethodInfos.
"""
from __future__ import annotations

import struct
from typing import Any, Callable

from scripts.game_data.il2cpp.context import method_parameter_owner, type_parameter_owner
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack.reference_conversion_sources import validate_program, _target


def validate_read_value_context(image: Any, reader: dict, provider: dict,
                                entries: Any, *, fail: Callable) -> dict:
    """Join authenticated Reader MVAR, provider and formatter slots/signatures."""
    selected = NativeReferenceContext(image)
    section = image.metadata.sections['genericContainers']
    containers = [m.generic_container_index for m in image.metadata.methods]

    def method_owner(row, owner_name, method_name, static):
        definition = row['definition']; m = image.metadata.methods[definition]
        at = section.offset + m.generic_container_index * 16
        if (not row['isMethod'] or image.type_name(m.declaring_type) != owner_name
                or image.metadata.string(m.name_index) != method_name
                or bool(m.flags & 0x10) != static or image.metadata.parameters_for(m)
                or m.generic_container_index < 0 or not section.offset <= at <= section.offset + section.size - 16):
            fail('read-value-method-owner', [owner_name, method_name, static], row)
        owner, count, is_method, start = struct.unpack_from('<iiii', image.metadata.buf, at)
        identity = method_parameter_owner(image.metadata.buf, start, containers, source='readValueReference')
        if (owner, count, is_method) != (definition, 1, 1) or identity['methodIndex'] != definition or identity['ordinal'] != 0:
            fail('read-value-owned-mvar', 'one reciprocal method parameter', identity)
        return m, start

    def payload(row, kind):
        raw = bytes.fromhex(row['rawHex'])
        if (len(raw) != 16 or row['kind'] != kind or int.from_bytes(raw[:4], 'little') != kind
                or image.pe.u32_at_va(int.from_bytes(raw[8:], 'little')) != row['index']):
            fail('read-value-context-payload', kind, row)

    def slots(row, kinds):
        if [r['relativeSlot'] for r in row['entries']] != list(range(len(kinds))):
            fail('read-value-context-slots', 'complete ordered unique slots', row)
        for item, kind in zip(row['entries'], kinds, strict=True): payload(item, kind)
        return row['entries']

    def parameter(pointer, start, *, kind=0x1e, byref=False):
        raw = image.pe.bytes_at_va(pointer, 16)
        if len(raw) != 16 or raw[10:12] != bytes((kind, 0x20 if byref else 0)) or int.from_bytes(raw[:8], 'little') != start:
            fail('read-value-parameter-identity', [start, kind, byref], raw.hex())
        return raw

    def argument(instance, start):
        args = image.instantiations.resolve(instance).arguments
        if len(args) != 1: fail('read-value-instance-arity', 1, len(args))
        return parameter(args[0].type_pointer_va, start)

    def formatter(pointer, start):
        raw = image.pe.bytes_at_va(pointer, 16)
        if len(raw) != 16 or raw[10:12] != b'\x15\x00':
            fail('read-value-formatter-type', 'undecorated reference instantiation', raw.hex())
        root_ptr, inst_ptr = struct.unpack('<QQ', image.pe.bytes_at_va(int.from_bytes(raw[:8], 'little'), 16))
        root = image.pe.bytes_at_va(root_ptr, 16)
        if root[10:12] != b'\x12\x00' or image.type_name(int.from_bytes(root[:8], 'little')) != 'MemoryPack.MemoryPackFormatter`1':
            fail('read-value-formatter-owner', 'MemoryPackFormatter reference class', root.hex())
        inst = image.instantiations.resolve_pointer(inst_ptr)
        argument(inst.index, start)
        return inst.index

    rm, rvar = method_owner(reader, 'MemoryPack.MemoryPackReader', 'ReadValue', False)
    pm, pvar = method_owner(provider, 'MemoryPack.MemoryPackFormatterProvider', 'GetFormatter', True)
    if not selected.is_value_type('MemoryPack.MemoryPackReader'):
        fail('read-value-reader-receiver', 'unboxed Reader value type', reader)
    parameter(selected.type_pointer(rm.return_type), rvar)
    rs = slots(reader, [3, 2, 3]); ps = slots(provider, [1, 2])
    parameter(selected.type_pointer(ps[0]['index']), pvar)
    formatter(selected.type_pointer(ps[1]['index']), pvar)
    if selected.type_pointer(pm.return_type) != selected.type_pointer(ps[1]['index']):
        fail('read-value-provider-result-signature', 'same owned formatter result', pm.return_type)
    get_spec = entries.specs[rs[0]['index']]; deserialize_spec = entries.specs[rs[2]['index']]
    if (list(get_spec) != rs[0]['methodSpec'] or get_spec[0] != provider['definition'] or get_spec[1] != -1
            or list(deserialize_spec) != rs[2]['methodSpec'] or deserialize_spec[2] != -1
            or deserialize_spec[1] != get_spec[2]):
        fail('read-value-provider-formatter-instance', 'same Reader MVAR instance and owned provider', [get_spec, deserialize_spec])
    argument(get_spec[2], rvar)
    if formatter(selected.type_pointer(rs[1]['index']), rvar) != get_spec[2]:
        fail('read-value-expected-formatter-instance', 'same exact Reader MVAR instance', rs[1])
    dm = image.metadata.methods[deserialize_spec[0]]; td = image.metadata.types[dm.declaring_type]
    params = image.metadata.parameters_for(dm)
    if (image.type_name(td.index) != 'MemoryPack.MemoryPackFormatter`1' or image.metadata.string(dm.name_index) != 'Deserialize'
            or dm.flags & 0x10 or dm.slot != 5 or selected.type_name(dm.return_type) != 'void'
            or len(params) != 2 or td.generic_container_index < 0):
        fail('read-value-deserialize-abi', 'instance void slot five with two byrefs', deserialize_spec)
    ca = section.offset + td.generic_container_index * 16
    if not section.offset <= ca <= section.offset + section.size - 16:
        fail('read-value-formatter-container-range', 'bounded generic container', ca)
    owner, count, is_method, start = struct.unpack_from('<iiii', image.metadata.buf, ca)
    identity = type_parameter_owner(image.metadata.buf, start, [t.generic_container_index for t in image.metadata.types], source='readValueReference')
    if (owner, count, is_method) != (td.index, 1, 0) or identity['typeIndex'] != td.index or identity['ordinal'] != 0:
        fail('read-value-formatter-var-owner', 'one reciprocal class parameter', identity)
    raw_reader = image.pe.bytes_at_va(selected.type_pointer(params[0].type_index), 16)
    if (raw_reader[10:12] != b'\x11\x20' or int.from_bytes(raw_reader[:8], 'little') != rm.declaring_type):
        fail('read-value-deserialize-reader-byref', 'same unboxed Reader byref', raw_reader.hex())
    parameter(selected.type_pointer(params[1].type_index), start, kind=0x13, byref=True)
    return {'readerMethodDefinition': rm.index, 'providerMethodDefinition': pm.index,
        'formatterDeserializeDefinition': dm.index, 'formatterSlot': 5,
        'ownedReaderParameterOrdinal': 0, 'providerKeyAndResultOwned': True,
        'runtimeInflationObserved': False}


OUTER = [
    '48895C2408','55','56','57','4154','4155','4156','4157','4883EC70','488BDA','4C8BF9','48837A3800',None,
    '48C744242000000000',None,'83B9E000000000',None,'488B4338','488B28','48837D3800',None,'488B5D38','488B1B',None,
    '83B9E000000000',None,'4885DB',None,'83B9E000000000',None,'B201','488BCB',None,'4C8D6820',None,'488B8B80000000',None,'90',
    '488B4340','49C7C0FFFFFFFF','4C898424C8000000','483B4338',None,'4533C9','4C898C24B8000000','4C8B7348','49FFCE','498BCD',None,
    '488BF8','4C898424C0000000','488B7368','448B6350','4923FE','488D0C7F','443B24CE',None,'48837B3800',None,
    '488D047F','833CC600',None,'488B54C608','498BCD',None,'85C0',None,'4883FFFF',None,'488D0C7F','488D14CE',
    '488B4348','488D0C40','488B4368','488D0CC8','483BD1',None,'488B4A10','488B4370','4C8B34C8','488B8B80000000',None,'90',None,
    '83B9E000000000',None,None,None,None,'83B9E000000000',None,'498BCE',None,'488BD8','488B4538','488B4008','F6803801000001',None,
    '4885DB',None,'488BD0','488B0B',None,'84C0',None,'B905000000','4C8D4C2420','4D8BC7','488BD3',None,
    '488B442420','488B9C24B0000000','4883C470','415F','415E','415D','415C','5F','5E','5D','C3']

INLINE_PREFIX = [
    '48895C2408','55','56','57','4154','4155','4156','4157','4881EC80000000','4D8BE9','4D8BF8','488BFA','0FB7D9','488B0A',None,
    '488D4314','48C1E004','480307','4C8B10','488B5808','48899C24D8000000',None,'4C3BD0',None,None,None,
    '41837F3001',None,'498B4750','8038FF',None]
INLINE_POSITIVE = INLINE_PREFIX + [
    '488B4320','488B98C0000000','488B5B50',None,'83B9E000000000',None,'4885DB',None,'83B9E000000000',None,'B201','488BCB',None,
    '488D5820','48899C24C8000000',None,'488B8F80000000',None,'90','488B4740','4533F6','49C7C1FFFFFFFF','4C898C24D0000000',
    '483B4738',None,'498BF6','4C8B4748','49FFC8','4C89442420','488BCB',None,'488BD8','4923D8','498BE9','4C8B6768','8B4750','488D0C5B',
    '413B04CC',None,'4C397738',None,'488D045B','453934C4',None,'498B54C408','488B8C24C8000000',None,'85C0',None,'4883FBFF',None,
    '488D0C5B','498D14CC','488B4748','488D0C40','488B4768','488D0CC8','483BD1',None,'488B4A10','488B4770','488B34C8','488B8F80000000',None,
    '90',None,'4885F6',None,'B942000000','488BD6',None,'488B9C24D8000000','A980000000',None,'488B4320','488B88C0000000','488B4958',None,
    '4C8BF0','488B4B20','488B91C0000000','488B5A18','4C89B424C8000000',None,None,None,'83B9E000000000',None,
    '488B4320','F6803801000001',None,'488B80C0000000','488B4820',None,'4885C0',None,'B905000000','4C8D8C24C8000000','4D8BC7','488BD0',None,
    '488BBC24C8000000','4885FF',None]
EPILOGUE = ['488B9C24C0000000','4881C480000000','415F','415E','415D','415C','5F','5E','5D','C3']


def _profile(image, proof, expected, branches, call_positions, rips, jumps, indirects, calls, *, fail):
    validate_program(image, proof, fail=fail, extra_opcodes={'A980000000': 'test eax, 0x80'})
    rows = proof['program']
    if len(rows) != len(expected): fail('read-value-profile-size', len(expected), len(rows))
    covered = set(branches) | set(call_positions) | set(rips) | set(jumps) | set(indirects)
    if covered != {n for n, v in enumerate(expected) if v is None}:
        fail('read-value-profile-coverage', 'each variable instruction independently constrained', sorted(covered))
    for n, (row, wanted) in enumerate(zip(rows, expected, strict=True)):
        if wanted is not None and row[1] != wanted:
            fail('read-value-owned-transfer', {'position': n, 'bytes': wanted}, row)
    for n, (opcode, taken) in branches.items():
        at, h = rows[n]; raw = bytes.fromhex(h); op = bytes.fromhex(opcode)
        if (len(raw) != (2 if len(op) == 1 else 6) or raw[:len(op)] != op
                or rows[n+1][0] != (_target(at, raw) if taken else at + len(raw))):
            fail('read-value-selected-guard', {'position': n, 'opcode': opcode, 'taken': taken}, rows[n:n+2])
    for n, name in call_positions.items():
        at, h = rows[n]; raw = bytes.fromhex(h)
        if len(raw) != 5 or raw[0] != 0xe8 or _target(at, raw) != calls[name]:
            fail('read-value-physical-call', {'position': n, 'name': name, 'target': calls[name]}, rows[n])
    for n, prefix in rips.items():
        raw = bytes.fromhex(rows[n][1]); op = bytes.fromhex(prefix)
        if len(raw) != 7 or raw[:len(op)] != op or op in (b'\x80\x3d', b'\x83\x3d') and raw[-1] != 0:
            fail('read-value-independent-rip', {'position': n, 'prefix': prefix}, rows[n])
    for n in jumps:
        raw = bytes.fromhex(rows[n][1])
        if not (len(raw) == 5 and raw[0] == 0xe9 or len(raw) == 2 and raw[0] == 0xeb):
            fail('read-value-direct-jump', 'complete owned jump', rows[n])
    for n in indirects:
        raw = bytes.fromhex(rows[n][1])
        if len(raw) != 6 or raw[:2] != b'\xff\x15':
            fail('read-value-global-indirect-call', 'actual RIP-relative indirect call', rows[n])
    return rows


def validate_read_value_transfer(image: Any, proof: dict, calls: dict, *, fail: Callable) -> dict:
    """Same entry Reader, zeroed local output and full output-to-RAX return."""
    branches = {n: (op, taken) for n, op, taken in (
        (12,'0F84',False),(16,'0F84',False),(20,'0F84',False),(25,'0F84',False),(27,'0F84',False),(29,'0F84',False),
        (42,'0F84',False),(56,'75',True),(58,'0F87',False),(61,'0F85',False),(66,'0F85',False),(68,'0F84',False),
        (76,'0F84',False),(85,'0F84',False),(87,'0F84',False),(90,'0F84',False),(97,'0F84',False),(99,'0F84',False),(104,'0F84',False))}
    _profile(image, proof, OUTER, branches,
        {32:'typeKey',48:'cacheHash',64:'cacheCompare',92:'formatterResult',102:'formatterClassPredicate',109:'formatterDispatch'},
        {n:'488B0D' for n in (14,23,83,88)} | {34:'488B1D',86:'803D'}, (), (36,81), calls, fail=fail)
    return {'entryRva': proof['program'][0][0], 'readerRegister': 'rcx', 'companionRegister': 'rdx',
        'savedReaderRegister': 'r15', 'localOutputFromEntryRsp': -136,
        'zeroInitializedOutputBits': 64, 'formatterSlot': 5, 'returnRegister': 'rax',
        'sameReaderForwarded': True, 'sameLocalOutputReturned': True,
        'directReaderFieldReads': 0, 'directReaderCursorStores': 0, 'completeReturnProved': True,
        'physicalBodyIdentityProved': False, 'runtimeSelectionObserved': False}


def validate_optimized_adapter_transfer(image: Any, proof: dict, calls: dict, offsets: dict,
                                        *, adapter_entry: int, mode: str, fail: Callable) -> dict:
    """First pointer match inlines the adapter, including its complete output."""
    if mode not in ('nonnull', 'nullWrapperOutput', 'ff'):
        fail('read-value-inline-mode', 'one complete selected output path', mode)
    if (set(offsets) != {'currentPtr','bufferLength','advancedCount','consumed'}
            or any(type(v) is not int or not 0 <= v < 128 for v in offsets.values()) or len(set(offsets.values())) != 4):
        fail('read-value-reader-layout', 'four distinct bounded Reader fields', offsets)
    prefix = list(INLINE_PREFIX)
    prefix[26] = f'41837F{offsets["bufferLength"]:02X}01'
    prefix[28] = f'498B47{offsets["currentPtr"]:02X}'
    branches = {23:('0F85',False),25:('75',True),27:('7D',True),30:('75',mode != 'ff')}
    cp = {14:'classPrepare'}; rips = {21:'488D05',24:'803D'}; jumps = []; indirects = []
    if mode == 'ff':
        expected = prefix + [f'41837F{offsets["bufferLength"]:02X}01',None,
            f'418B5F{offsets["bufferLength"]:02X}','83EB01',None,f'41895F{offsets["bufferLength"]:02X}',
            f'49FF47{offsets["currentPtr"]:02X}',f'41FF47{offsets["advancedCount"]:02X}',f'41FF47{offsets["consumed"]:02X}',
            '33C0','49894500',None] + EPILOGUE
        branches.update({32:('7D',True),35:('79',True)}); jumps = [42]
    else:
        expected = prefix + INLINE_POSITIVE[len(prefix):]
        branches.update({n:(op,take) for n,op,take in (
            (36,'75',True),(38,'0F84',False),(40,'75',True),(55,'75',True),(69,'75',True),(71,'76',True),
            (74,'75',False),(79,'74',True),(81,'74',False),(89,'74',False),(98,'0F84',False),(104,'77',False),
            (115,'75',True),(118,'75',True),(121,'75',True),(126,'0F84',False),(134,'0F84',mode=='nullWrapperOutput'))})
        cp.update({43:'typeKey',61:'cacheHash',77:'cacheCompare',101:'typeFlags',108:'activator',124:'wrapperGetFormatter',131:'formatterDispatch'})
        rips.update({34:'488B0D',46:'488B3D',114:'803D',116:'488B0D'}); jumps=[96]; indirects=[48,94]
        if mode == 'nullWrapperOutput':
            expected += ['33C0','49894500',None] + EPILOGUE; jumps += [137]
        else:
            expected += ['488B4320','F6803801000001',None,'488B80C0000000','488B4040','F6803801000001',None,
                '33C9','4C8BC7','488BD0',None,'49894500',None,None] + EPILOGUE
            branches.update({137:('75',True),141:('75',True),148:('0F84',True)})
            cp[145]='interfaceConversion'; rips[147]='833D'
    rows = _profile(image, proof, expected, branches, cp, rips, jumps, indirects, calls, fail=fail)
    at, h = rows[21]; raw = bytes.fromhex(h)
    actual = at + 7 + int.from_bytes(raw[3:], 'little', signed=True)
    if actual != adapter_entry:
        fail('read-value-first-optimized-pointer', 'same independently registered adapter entry', [adapter_entry,actual])
    return {'entryRva': rows[0][0], 'mode': mode, 'optimizedCase': 0, 'formatterSlot': 5,
        'sameReaderPreserved': True, 'sameOriginalOutputPreserved': True,
        'localWrapperFromEntryRsp': 16 if mode != 'ff' else None,
        'ownedAdapterMethodInfoFromEntryRsp': 32, 'runtimeReferenceBits': 64,
        'wireBytesConsumedDirectly': 1 if mode == 'ff' else 0,
        'readerCursorStoresDirectly': 4 if mode == 'ff' else 0,
        'callsActivatorConditionally': mode != 'ff', 'wrapperGetFormatterEffectsProved': False,
        'nullClearsOriginalOutput': mode in ('ff','nullWrapperOutput'),
        'typedInterfaceReturnStored': mode == 'nonnull', 'completeReturnProved': True,
        'runtimeSelectionObserved': False}
