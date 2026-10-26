"""Authenticate the selected anonymous-storey outer count/allocation programs.

The typed BinaryReader allocation/constructor request stores the reader local.
The later selected count window conditionally reads that stable receiver. Its
m_isMemoryStream byte selects an inline MemoryStream path or a buffered path.
The latter requests Stream.Read(byte[],int,int) at virtual slot 34 with offset
equal to the signed accumulated count and count=4-total, repeats while total<4,
and transfers out on a zero result. Other read results remain unobserved; this
does not assert progress or exactly four bytes consumed for arbitrary callees.

The MemoryStream path requests a class probe twice, conditionally retains the
stream pointer, checks _isOpen and stores wrapping Int32 _position+4 before its
signed _length test. Four separately bounded buffer bytes at old position are
combined. Both hot paths assemble a little-endian 32-bit bit pattern, forward
it in EDX (zero-extended), request AnonymousStoreyInfo[] allocation, and retain
the result for the separately authenticated record loop. There is no caller
nonnegative-count check. The record loop's ordinary exit is the next loader
section; neither that section nor VM publication is asserted here.

Finite caller grammars and the Stream query prefix establish requests only.
Cold transfers have authenticated entry bytes and unresolved semantics; some
may rejoin normal paths. Reader-to-count control flow, runtime implementations,
class-probe results, stable storage, allocation, exceptions and execution stay
conditional. Interface reflection length/order still prevents nonzero raw
anonymousStoreyInfos framing. Native anchors belong solely in contract rows.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.context import unresolved_usage_index
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _slice, _hash, _expect, _type, _identity
from scripts.game_data.ifix_vm_object_opcode_rules import _carrier as _ordinary_carrier


class AnonymousLoaderRuleError(ValueError):
    """A selected outer-count declaration lacks its reviewed native witness."""


def _need(ok: bool, detail: str) -> None:
    if not ok: raise AnonymousLoaderRuleError('anonymous-loader.' + detail)


def _claims(spec: dict) -> None:
    _need(all(type(spec.get(k)) is type(v) and spec.get(k) == v for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    for key, expected in [('blocks', _PROGRAMS), ('coldTransfers', _COLD), ('methods', {'readerCtor'}), ('virtualMethods', {'streamRead'}), ('helpers', {'streamReadRequest', 'classProbe'}), ('usageCells', _CELLS), ('fieldLayouts', _FIELDS)]:
        _need(set(spec.get(key, {})) == set(expected), 'catalog set differs: ' + key)


def _carrier(image: Any, pointer: int, name: str) -> None:
    if name == 'IFix.Core.PatchManager+PatchKind':
        raw = image.pe.bytes_at_va(pointer, 16); _need(len(raw) == 16 and raw[10] == 0x11 and not raw[11] & 0x20, 'PatchKind carrier differs')
    else: _ordinary_carrier(image, pointer, name)


def _method(image: Any, row: dict, identity: tuple, role: str, extents: dict[int, int], virtual_slot: int | None = None) -> int:
    _need(type(row.get('parameterCount')) is int, 'method count differs: ' + role)
    for key, value in [('returnTypeName', identity[3]), ('static', identity[4]), ('generic', False)]:
        if virtual_slot is not None or key in row: _need(type(row.get(key)) is type(value) and row.get(key) == value, 'method declaration differs: ' + role + '.' + key)
    if virtual_slot is not None: _need(type(row.get('virtualSlot')) is int and row['virtualSlot'] == virtual_slot, 'virtual slot declaration differs')
    md = image.metadata; ownername, name, params, returned, static = identity
    matches = [m for t in md.types if md.type_full_name(t) == ownername for m in md.methods_for(t) if md.string(m.name_index) == name and m.parameter_count == len(params) and [_type(image, p.type_index) for p in md.parameters_for(m)] == params]
    _need(len(matches) == 1, 'named overload differs: ' + role); method = matches[0]
    for index, typ in [(p.type_index, typ) for p, typ in zip(md.parameters_for(method), params)] + [(method.return_type, returned)]: _carrier(image, image.pe.u64_at_va(_rva(image.registration['types']) + index * 8), typ)
    return _identity(image, row, identity, role, extents, virtual_slot=virtual_slot)


def _layouts(image: Any, spec: dict) -> None:
    md = image.metadata
    for ownername, fields in _FIELDS.items():
        row = spec['fieldLayouts'][ownername]; _need(set(row) == set(fields), 'field declaration set differs: ' + ownername)
        owners = [t for t in md.types if md.type_full_name(t) == ownername]
        _need(len(owners) == 1 and not owners[0].bitfield & 1, 'reference owner differs: ' + ownername)
        owner = owners[0]; offsets = runtime_type_field_offsets(md, image.pe, image.registration, owner.index); definitions = {md.string(f.name_index): f for f in md.fields_for(owner)}
        for name, (typ, offset) in fields.items():
            declared = row[name]; f = definitions.get(name)
            _need(type(declared.get('offset')) is int and declared == dict(type=typ, offset=offset) and f is not None and offsets.get(name) == offset and _type(image, f.type_index) == typ, 'named field differs: ' + ownername + '.' + name)
            pointer = image.pe.u64_at_va(_rva(image.registration['types']) + f.type_index * 8); raw = image.pe.bytes_at_va(pointer, 16)
            _need(not int.from_bytes(raw[8:10], 'little') & 0x10, 'static field differs: ' + name); _carrier(image, pointer, typ)


def _cells(image: Any, spec: dict) -> dict[str, int]:
    result = {}
    for name, typ in _CELLS.items():
        row = spec['usageCells'][name]; at = _rva(row['cellRva']); raw = image.pe.bytes_at_va(image.pe.image_base + at, 8)
        _need(type(row.get('usageTag')) is int and row['usageTag'] == 1 and row.get('identity') == typ and raw == bytes.fromhex(row['rawHex']), 'stored usage differs: ' + name)
        index = unresolved_usage_index(raw, image.registration['typesCount'], tag=1, source='anonymous-loader.' + name, offset=at)
        _need(type(row.get('registeredTypeIndex')) is int and row['registeredTypeIndex'] == index and _type(image, index) == typ, 'named class differs: ' + name)
        pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
        _carrier(image, pointer, typ); _need(image.pe.bytes_at_va(pointer, 16) == bytes.fromhex(row['rawTypeHex']), 'raw type declaration differs: ' + name); result[name] = at
    return result


def _program(tokens: tuple, at: int, targets: dict[str, int], cells: dict[str, int]) -> bytes:
    p = _Program(at)
    for token in tokens:
        if isinstance(token, str): p.add(token); continue
        kind, *args = token
        if kind == 'call': p.call(targets[args[0]])
        elif kind == 'rip': p.rip(args[0], cells[args[1]])
        elif kind == 'branch':
            prefix = bytes.fromhex(args[0]); width = 1 if len(prefix) == 1 and prefix != b'\xe9' else 4
            p.add(prefix + (targets[args[1]] - (at + len(p.raw) + len(prefix) + width)).to_bytes(width, 'little', signed=True))
        else: _need(False, 'unknown finite token')
    return p.finish()


def validate_anonymous_loader_rules(image: Any, spec: dict, loader: bytes, loader_rva: int, contract: dict, extents: dict[int, int]) -> dict:
    """Authenticate outer count hot paths in the parent's selected loader body."""
    _claims(spec); _layouts(image, spec); targets = {}
    targets['readerCtor'] = _method(image, spec['methods']['readerCtor'], _METHODS['readerCtor'], 'readerCtor', extents)
    _method(image, spec['virtualMethods']['streamRead'], _METHODS['streamRead'], 'streamRead', extents, virtual_slot=34)
    for role, path in _CLAIMS['helperRefs'].items():
        row = _ref(contract, path); at = _rva(row['rva']); count = row['byteCount']
        _need(type(count) is int and 0 < count <= 4096, 'helper extent differs: ' + role); _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    for role, row in spec['helpers'].items():
        at = _rva(row['rva']); count = row['byteCount']; _need(type(count) is int and 0 < count <= 4096, 'owned helper extent differs: ' + role)
        _need(row.get('effectBoundary') == ('selected-vtable-prefix-runtime-dispatch-unobserved' if role == 'streamReadRequest' else 'opaque-callee-request-only'), 'helper outcome promoted: ' + role)
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    prefix = _program(('48895c241048896c2418565741564883ec300fb7d9418bf1488b0a498be8488bfa', ('call', 'classPrepare'), '488d431448c1e0044803074c8b10488b4808'), targets['streamReadRequest'], targets, {})
    _need(spec['helpers']['streamReadRequest']['byteCount'] == len(prefix), 'Stream prefix length differs')
    _expect(image.pe.bytes_at_va(image.pe.image_base + targets['streamReadRequest'], len(prefix)), prefix, 'Stream request prefix')
    for name, row in spec['coldTransfers'].items():
        at = _rva(row['rva']); count = row['byteCount']; _need(type(count) is int and 0 < count <= 32 and row.get('effectBoundary') == 'unresolved-cold-transfer', 'cold boundary differs: ' + name)
        _hash(_slice(loader, loader_rva, at, count, name), row, name); targets[name] = at
    record = _ref(contract, _CLAIMS['recordLoopRef']); targets['recordLoop'] = _rva(record['rva'])
    _hash(_slice(loader, loader_rva, targets['recordLoop'], record['byteCount'], 'recordLoop'), record, 'recordLoop')
    targets.update({name: _rva(row['rva']) for name, row in spec['blocks'].items()}); cells = _cells(image, spec)
    for name, row in spec['blocks'].items():
        at = targets[name]; count = row['byteCount']; _need(type(count) is int and 0 < count <= 4096, 'block extent differs: ' + name)
        raw = _slice(loader, loader_rva, at, count, name); _hash(raw, row, name); _expect(raw, _program(_PROGRAMS[name], at, targets, cells), name)
        _need(row.get('next') == _NEXT[name], 'continuation differs: ' + name)
        if _NEXT[name] is not None and name != 'readerProducer': _need(at + count == targets[_NEXT[name]], 'noncontiguous fallthrough: ' + name)
    _need(targets['bufferBytes'] + spec['blocks']['bufferBytes']['byteCount'] == targets['memoryCount'], 'hot count window gap')
    return dict(status='validated_conditional_anonymous_loader_rules', finiteBlockCount=len(_PROGRAMS), coldTransferCount=len(_COLD), projection=project_anonymous_loader_rules(spec), evidenceBoundary='conditional', executionBoundary='unobserved')


def project_anonymous_loader_rules(spec: dict) -> dict:
    """Expose the count request while preserving raw framing/runtime boundaries."""
    _claims(spec)
    return {key: spec[key] for key in _CLAIMS if key not in ('helperRefs', 'recordLoopRef')}


def validate_selected_anonymous_loader_rules(contract: dict, *, gameassembly: Path | None, metadata: Path | None, spec: dict | None = None) -> dict:
    if gameassembly is None or metadata is None: return dict(status='missing', detail='explicit native paths required', projection=None)
    inputs = contract['nativeInputs']; _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'native hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'], gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return dict(status=gate.status, detail=gate.detail, projection=None)
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.anonymous-loader'); extents = image.mapper.pdata_function_extents(image.pe)
    at = _method(image, contract['loader'], _LOADER, 'LoadInternal', extents); loader = image.pe.bytes_at_va(image.pe.image_base + at, contract['loader']['bodyBytes'])
    return validate_anonymous_loader_rules(image, contract['anonymousLoaderRules'] if spec is None else spec, loader, at, contract, extents)


_CLAIMS = dict(schema='endfield.ifix-vm-anonymous-loader-rules.v1', evidenceBoundary='conditional', executionBoundary='unobserved',
    scope='anonymousStoreyInfos-outer-count-and-allocation-hot-paths', countByteOrder='four-byte-little-endian-bit-pattern',
    bufferedRecipe='Stream.Read-slot-34(buffer,total,4-total);zero:unresolved-transfer;repeat-while-signed-total-less-than-four',
    memoryRecipe='class-probe-twice;conditional-pointer;isOpen;wrapping-position-plus-four-store-before-signed-length-check;four-bounded-bytes',
    allocationRecipe='MOV-EDX-count-zero-extends-32-bit-bit-pattern;AnonymousStoreyInfo-array-request;retain-local;record-loop',
    countBoundary='no-caller-nonnegative-count-gate;allocation-capacity-defaults-and-results-unobserved',
    receiverBoundary='typed-BinaryReader-allocation-and-constructor-request;producer-to-count-control-flow-and-live-receiver-unobserved',
    virtualBoundary='Stream.Read-virtual-slot-and-pointer-MethodInfo-prefix;concrete-runtime-dispatch-and-read-results-unobserved',
    storageBoundary='valid-stable-reader-stream-arrays-and-local-storage;normal-helper-returns-and-class-probe-consistency-required',
    coldBoundary='authenticated-target-entry-bytes-only;transfer-semantics-and-rejoins-unresolved',
    framingBoundary='outer-count-program-proved;interface-reflection-length-and-order-still-required;nonzero-raw-anonymousStoreyInfos-framing-refused',
    publicationBoundary='record-loop-owned-by-anonymousStoreyRules;next-loader-section-and-VM-publication-unresolved',
    helperRefs=dict(allocateObject='stackReferenceRules.nullObjectHelper', allocateArray='objectConversionRules.helpers.arrayAllocate', classPrepare='chainFieldRules.helpers.classPrepare'),
    recordLoopRef='anonymousStoreyRules.programs.loaderRecord')
_METHODS = dict(readerCtor=('System.IO.BinaryReader', '.ctor', ['System.IO.Stream'], 'void', False), streamRead=('System.IO.Stream', 'Read', ['byte[]', 'int', 'int'], 'int', False))
_LOADER = ('IFix.Core.PatchManager', 'LoadInternal', ['System.IO.Stream', 'bool', 'IFix.Core.PatchManager+PatchKind'], 'IFix.Core.VirtualMachine', True)
_FIELDS = {'System.IO.BinaryReader': {'m_stream': ('System.IO.Stream', 16), 'm_buffer': ('byte[]', 24), 'm_isMemoryStream': ('bool', 69)}, 'System.IO.MemoryStream': {'_buffer': ('byte[]', 40), '_position': ('int', 52), '_length': ('int', 56), '_isOpen': ('bool', 67)}}
_CELLS = dict(readerType='System.IO.BinaryReader', memoryType='System.IO.MemoryStream', infoArrayType='IFix.Core.AnonymousStoreyInfo[]')


_PROGRAMS = {'readerProducer': (('rip', '488b0d', 'readerType'),
                    ('call', 'allocateObject'),
                    '488bd84885c0',
                    ('branch', '0f84', 'cold00'),
                    '4533c0488bd6488bc8',
                    ('call', 'readerCtor'),
                    '48895c2440'),
 'countEntry': ('488b7c24404885ff',
                ('branch', '0f84', 'cold01'),
                '807f4500',
                ('branch', '0f85', 'memoryCount'),
                '48837f1800',
                ('branch', '74', 'bufferStart'),
                '488b47184885c0',
                ('branch', '0f84', 'cold02'),
                '83781804',
                ('branch', '0f8c', 'cold03')),
 'bufferStart': ('33db48395f10', ('branch', '0f84', 'cold04'), '660f1f840000000000'),
 'bufferLoop': ('488b57104885d2',
                ('branch', '0f84', 'cold05'),
                'b8040000002bc3b92200000089442420448bcb4c8b4718',
                ('call', 'streamReadRequest'),
                '85c0',
                ('branch', '0f84', 'cold06'),
                '03d883fb04',
                ('branch', '7c', 'bufferLoop')),
 'bufferBytes': ('488b47184885c0',
                 ('branch', '0f84', 'cold07'),
                 '83781800',
                 ('branch', '0f86', 'cold08'),
                 '440fb648204885c0',
                 ('branch', '0f84', 'cold09'),
                 '83781801',
                 ('branch', '0f86', 'cold10'),
                 '440fb640214885c0',
                 ('branch', '0f84', 'cold11'),
                 '83781802',
                 ('branch', '0f86', 'cold12'),
                 '0fb650224885c0',
                 ('branch', '0f84', 'cold13'),
                 '83781803',
                 ('branch', '0f86', 'cold14'),
                 '0fb64823c1e1080bcac1e108410bc8c1e108410bc9',
                 ('branch', 'e9', 'allocateInfoArray')),
 'memoryCount': ('48837f1000',
                 ('branch', '0f84', 'cold15'),
                 '488b5f104885db',
                 ('branch', '0f84', 'cold16'),
                 ('rip', '488b15', 'memoryType'),
                 '488b0b',
                 ('call', 'classProbe'),
                 '84c0',
                 ('branch', '0f84', 'cold16'),
                 ('rip', '488b15', 'memoryType'),
                 '488b0b',
                 ('call', 'classProbe'),
                 '33c984c0480f45cb80794300',
                 ('branch', '0f84', 'cold17'),
                 '8b513483c2048951343b5138',
                 ('branch', '0f8f', 'cold18'),
                 '4c8b41284d85c0',
                 ('branch', '0f84', 'cold19'),
                 '8d42fc4c63c8453b4818',
                 ('branch', '0f83', 'cold20'),
                 '430fb65c01204d85c0',
                 ('branch', '0f84', 'cold21'),
                 '8d42fd4c63c8453b4818',
                 ('branch', '0f83', 'cold22'),
                 '470fb65c01204d85c0',
                 ('branch', '0f84', 'cold23'),
                 '8d42fe4c63c8453b4818',
                 ('branch', '0f83', 'cold24'),
                 '470fb65401204d85c0',
                 ('branch', '0f84', 'cold25'),
                 '8d42ff4863c8413b4818',
                 ('branch', '0f83', 'cold26'),
                 '420fb64c0120c1e108410bcac1e108410bcbc1e1080bcb'),
 'allocateInfoArray': ('8bd1',
                       ('rip', '488b0d', 'infoArrayType'),
                       ('call', 'allocateArray'),
                       '4c8bf84889442450')}
_NEXT = {'readerProducer': 'unobserved-reader-to-count-join', 'countEntry': 'bufferStart', 'bufferStart': 'bufferLoop', 'bufferLoop': 'bufferBytes', 'bufferBytes': None, 'memoryCount': 'allocateInfoArray', 'allocateInfoArray': 'recordLoop'}
_COLD = {'cold05', 'cold13', 'cold17', 'cold12', 'cold11', 'cold26', 'cold14', 'cold24', 'cold15', 'cold20', 'cold16', 'cold18', 'cold19', 'cold06', 'cold09', 'cold10', 'cold25', 'cold08', 'cold23', 'cold02', 'cold01', 'cold03', 'cold07', 'cold00', 'cold04', 'cold21', 'cold22'}
