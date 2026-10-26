"""Authenticate IFix's conditional chain-field traversal and outward writeback.

mGet selects fieldInfos[fieldIds[layer]] before reading the parent recursively.
A null FieldInfo selects newFieldInfos.get_Item; for a nonzero layer, that
dictionary getter is also obtained before recursion. The recursive call keeps
the original root, isArray flag and both tables and uses layer minus one. The
selected getter then receives the returned parent. Only layer zero consults
isArray: true casts the root twice and requests Array.GetValue(int); false
requests the reflected or new-field getter on the root.

mSet captures the reflected row before mGet reads the parent at layer minus
one. It then requests the reflected or new-field setter on that parent with
the current replacement. Its tail recursion is a native loop: decrement the
layer, replace the current replacement with the returned parent, and preserve
the original root, field IDs, tables and isArray flag. This explicitly requests
outward writeback, including for boxed parent objects. At layer zero it sets
the root's selected field, or requests Array.SetValue(object,int) when isArray.
The Int32 layer and field IDs are checked with unsigned array bounds tests.

The reflected getter calls the named FieldInfo.GetValue virtual slot. Its
receiver dispatcher passes its class to an opaque helper, loads the code and hidden MethodInfo
from the slot pair, compares two image-qualified registered MethodDef targets,
and otherwise jumps to that code with receiver, owner and hidden MethodInfo.
The first fast path reads owner+0x30 after a null guard. The second reads the
receiver's +0x18 word and tail-calls an opaque runtime field-read helper. Those
are conditional dispatcher recipes; neither target comparison proves that a
runtime FieldInfo selected an implementation. Full finite programs guard every
instruction and branch in mGet, mSet and this dispatcher. Addresses, hashes and
selected usage cells belong to reviewed JSON, not this algorithm module.

Successful reflection, cast and dictionary outcomes, exact generic sharing,
runtime storage contents and alias mutation remain unobserved. Interpretation
requires valid stable input arrays and normal nonmutating helper returns. The
native initialization guard is authenticated but static-state initialization
and concurrent runtime behavior are not observed. New-field storage and the
runtime field-read helper are separate semantic joins.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_delegate_rules import _method as _parent_method
from scripts.game_data.ifix_vm_reference_update_rules import (
    _ref, _rva, _hash, _expect, _type, _usage, _dictionary_target, _field_equal_program,
)


class ChainFieldRuleError(ValueError):
    """The chain recipe lacks its selected native witness."""


_METHOD_REFS = {n: 'referenceUpdateRules.methods.' + n for n in
                ('chainSet', 'fieldEqual', 'fieldSet', 'newFieldSet', 'arraySet')}
_HELPER_REFS = {n: 'referenceUpdateRules.helpers.' + n for n in
                ('typeInitialize', 'cast', 'dictionaryItem', 'boundsFailure', 'nullFailure')}
_USAGE_REFS = {'dictionary': 'referenceUpdateRules.usageCells.instanceDictionary',
               'arrayType': 'referenceUpdateRules.usageCells.arrayType'}
_METHODS = {
    'chainGet': ('IFix.Core.EvaluationStackOperation', 'mGet', ['bool', 'object', 'int', 'int[]',
        'System.Reflection.FieldInfo[]', 'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>'], 'object', True),
    'chainSet': ('IFix.Core.EvaluationStackOperation', 'mSet', ['bool', 'object', 'object', 'int', 'int[]',
        'System.Reflection.FieldInfo[]', 'System.Collections.Generic.Dictionary`2<int,IFix.Core.NewFieldInfo>'], 'void', True),
    'fieldEqual': ('System.Reflection.FieldInfo', 'op_Equality', ['System.Reflection.FieldInfo', 'System.Reflection.FieldInfo'], 'bool', True),
    'fieldSet': ('System.Reflection.FieldInfo', 'SetValue', ['object', 'object'], 'void', False),
    'newFieldSet': ('IFix.Core.NewFieldInfo', 'SetValue', ['object', 'object'], 'void', False),
    'newFieldGet': ('IFix.Core.NewFieldInfo', 'GetValue', ['object'], 'object', False),
    'arraySet': ('System.Array', 'SetValue', ['object', 'int'], 'void', False),
    'arrayGet': ('System.Array', 'GetValue', ['int'], 'object', False),
    'fieldGet': ('System.Reflection.FieldInfo', 'GetValue', ['object'], 'object', False),
    'jsonKey': ('Newtonsoft.Json.Serialization.JsonPropertyCollection', 'GetKeyForItem', ['Newtonsoft.Json.Serialization.JsonProperty'], 'string', False),
    'runtimeField': ('System.Reflection.RuntimeFieldInfo', 'UnsafeGetValue', ['object'], 'object', False),
}
_FAST_IMAGES = {'jsonKey': 'Newtonsoft.Json.dll', 'runtimeField': 'mscorlib.dll'}
_CLAIMS = {
    'schema': 'endfield.ifix-vm-chain-field-rules.v1', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
    'getterRecipe': 'select-field-or-new-field-before-recursive-parent-read;layer-zero-array-only-when-isArray',
    'setterRecipe': 'capture-field-row;read-parent-at-layer-minus-one;set-child;writeback-parent-outward-until-layer-zero',
    'aliasBoundary': 'stable-valid-tables-and-nonmutating-normal-helper-returns;actual-aliases-values-and-helper-mutation-unobserved',
    'dispatcherBoundary': 'conditional-class-slot-target-and-hidden-MethodInfo;runtime-FieldInfo-implementation-unobserved',
    'dictionaryBoundary': 'stored-typed-context-registered-MethodDef-family-runtime-sharing-unresolved',
}


def _need(ok: bool, detail: str) -> None:
    if not ok:
        raise ChainFieldRuleError('chainField.' + detail)


def _named(rows: list[dict], names: Any, label: str) -> dict[str, dict]:
    result = {row.get('name'): row for row in rows}
    _need(len(result) == len(rows) and set(result) == set(names), label + ': missing/duplicate/unknown declarations')
    return result


def _identity(image: Any, row: dict, role: str, extents: dict[int, int]) -> tuple[int, bytes]:
    owner, name, params, returned, static = _METHODS[role]; md = image.metadata
    _need((row.get('type'), row.get('method'), row.get('parameterCount')) == (owner, name, len(params))
          and row.get('parameterTypes') == params, role + ': declared identity differs')
    selected = [m for t in md.types if md.type_full_name(t) == owner for m in md.methods_for(t)
                if md.string(m.name_index) == name and m.parameter_count == len(params)
                and [_type(image, p.type_index) for p in md.parameters_for(m)] == params]
    _need(len(selected) == 1, role + ': expected one named overload'); method = selected[0]
    _need(_type(image, method.return_type) == returned and bool(method.flags & 0x10) == static
          and method.generic_container_index == -1 and method.token == _rva(row['token']), role + ': return/static/generic/token differs')
    _need('returnType' not in row or row['returnType'] == returned, role + ': declared return type differs')
    if role == 'fieldGet':
        _need(row.get('returnType') == returned and row.get('slot') == method.slot == 27
              and method.flags & 0x40 and method.flags & 0x400 and image.method_pointer_va(method) == 0,
              'fieldGet: abstract virtual slot differs')
        return 0, b''
    if role in _FAST_IMAGES:
        image_name = md.string(md.images[image.owners[method.declaring_type]].name_index)
        _need(image_name == row.get('image') == _FAST_IMAGES[role], role + ': image-qualified identity differs')
        rva = image.method_pointer_va(method) - image.pe.image_base
        _need(rva == _rva(row['rva']), role + ': registered MethodDef pointer differs')
        return rva, b''
    rva = _parent_method(image, row, extents)
    return rva, image.pe.bytes_at_va(image.pe.image_base + rva, row['bodyBytes'])


_GET_BLOCKS = {
    'entry': ('488bc4488958084889681048897018488978204154415641574883ec40', ('rip', '803d', 'flag', '00'), '498bf14963e8488bfa448ae1', ('jne8', 'select'), ('rip', '488d0d', 'dictionary', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'arrayType', ''), ('call', 'typeInitialize'), ('rip', 'c605', 'flag', '01')),
    'select': ('4885f6', ('je', 'nullExit'), '3b6e18', ('jae', 'boundsExit'), '48635cae2085ed', ('je', 'base'), '4c8bb424800000004d85f6', ('je', 'nullExit'), '413b5e18', ('jae', 'boundsExit'), '4d8b7cde204533c0498bcf33d2', ('call', 'fieldEqual'), '84c0', ('jne8', 'recursiveNew')),
    'recursiveReflected': ('488b842488000000448d45ff4883642430004c8bce4889442428488bd7418acc4c89742420', ('call', 'chainGet'), '4d85ff', ('je', 'nullExit'), '4c8bc0498bd7', ('jmp', 'reflectedGet')),
    'recursiveNew': ('4c8bbc24880000004d85ff', ('je', 'nullExit'), ('rip', '4c8b05', 'dictionary', ''), '8bd3498bcf', ('call', 'dictionaryItem'), '488364243000448d45ff4c897c24284c8bce488bd74c89742420418acc488bd8', ('call', 'chainGet'), '4885db', ('je', 'nullExit'), '488bd0488bcb', ('jmp', 'newGet')),
    'base': ('4584e4', ('jne', 'baseArray'), '488b8c24800000004885c9', ('je', 'nullExit'), '3b5918', ('jae', 'boundsExit'), '488b74d9204533c0488bce33d2', ('call', 'fieldEqual'), '84c0', ('jne8', 'baseNew'), '4885f6', ('je', 'nullExit'), '4c8bc7488bd6'),
    'reflectedGet': ('b91b000000', ('call', 'fieldGetDispatch')),
    'return': ('488b5c2460488b6c2468488b742470488b7c24784883c440415f415e415cc3',),
    'baseNew': ('488b8c24880000004885c9', ('je8', 'nullExit'), ('rip', '4c8b05', 'dictionary', ''), '8bd3', ('call', 'dictionaryItem'), '4885c0', ('je8', 'nullExit'), '488bd7488bc8'),
    'newGet': ('4533c0', ('call', 'newFieldGet'), ('jmp8', 'return')),
    'baseArray': (('rip', '488b15', 'arrayType', ''), '488bcf', ('call', 'cast'), '4885c0', ('je8', 'nullExit'), ('rip', '488b15', 'arrayType', ''), '488bcf', ('call', 'cast'), '488bc84533c08bd3', ('call', 'arrayGet'), ('jmp', 'return')),
    'boundsExit': (('call', 'boundsFailure'), 'cc'),
    'nullExit': (('call', 'nullFailure'), 'cc'),
}

_SET_BLOCKS = {
    'entry': ('488bc44889581048896818488970208848085741544155415641574883ec404c8bbc24a0000000418be9488bbc2498000000', '498bf04c8ba424900000004c8bf2'),
    'loop': (('rip', '803d', 'flag', '00'), ('jne8', 'select'), ('rip', '488d0d', 'dictionary', ''), ('call', 'typeInitialize'), ('rip', '488d0d', 'arrayType', ''), ('call', 'typeInitialize'), '8a4c2470', ('rip', 'c605', 'flag', '01')),
    'select': ('4d85e4', ('je', 'nullExit'), '413b6c2418', ('jae', 'boundsExit'), '4863c549635c842085ed', ('je', 'base'), '4885ff', ('je', 'nullExit'), '3b5f18', ('jae', 'boundsExit'), '488b44df20448d45ff4883642430004d8bcc4c897c2428498bd6488984249000000048897c2420', ('call', 'chainGet'), '488b8c24900000004533c033d24c8be8', ('call', 'fieldEqual'), '84c0', ('jne8', 'recursiveNew')),
    'recursiveReflected': ('488b8424900000004885c0', ('je', 'nullExit'), '4533c94c8bc6498bd5488bc8', ('call', 'fieldSet'), ('jmp8', 'writeback')),
    'recursiveNew': ('4d85ff', ('je', 'nullExit'), ('rip', '4c8b05', 'dictionary', ''), '8bd3498bcf', ('call', 'dictionaryItem'), '4885c0', ('je', 'nullExit'), '4533c94c8bc6498bd5488bc8', ('call', 'newFieldSet')),
    'writeback': ('8a4c2470ffcd498bf5', ('jmp', 'loop')),
    'base': ('84c9', ('jne', 'baseArray'), '4885ff', ('je', 'nullExit'), '3b5f18', ('jae', 'boundsExit'), '488b7cdf204533c0488bcf33d2', ('call', 'fieldEqual'), '84c0', ('jne8', 'baseNew'), '4885ff', ('je', 'nullExit'), '4533c94c8bc6498bd6488bcf', ('call', 'fieldSet')),
    'return': ('4c8d5c2440498b5b38498b6b40498b7348498be3415f415e415d415c5fc3',),
    'baseNew': ('4d85ff', ('je8', 'nullExit'), ('rip', '4c8b05', 'dictionary', ''), '8bd3498bcf', ('call', 'dictionaryItem'), '4885c0', ('je8', 'nullExit'), '4533c94c8bc6498bd6488bc8', ('call', 'newFieldSet'), ('jmp8', 'return')),
    'baseArray': (('rip', '488b15', 'arrayType', ''), '498bce', ('call', 'cast'), '4885c0', ('je8', 'nullExit'), ('rip', '488b15', 'arrayType', ''), '498bce', ('call', 'cast'), '488bc84533c9448bc3488bd6', ('call', 'arraySet'), ('jmp', 'return')),
    'boundsExit': (('call', 'boundsFailure'), 'cc'),
    'nullExit': (('call', 'nullFailure'), 'cc'),
}

_NEAR = {'je': '0f84', 'jne': '0f85', 'jae': '0f83', 'jmp': 'e9'}
_SHORT = {'je8': 0x74, 'jne8': 0x75, 'jmp8': 0xeb}


def _program(base: int, blocks: dict, targets: dict[str, int], cells: dict[str, int], flag: int) -> tuple[bytes, dict[str, int]]:
    p = _Program(base); near = []; slots = dict(cells, flag=flag)
    for label, tokens in blocks.items():
        p.mark(label)
        for token in tokens:
            if isinstance(token, str): p.add(token); continue
            kind, *args = token
            if kind == 'call': p.call(targets[args[0]])
            elif kind == 'rip': p.rip(args[0], slots[args[1]], bytes.fromhex(args[2]))
            elif kind in _SHORT: p.branch(_SHORT[kind], args[0])
            elif kind in _NEAR:
                p.add(_NEAR[kind]); near.append((len(p.raw), args[0])); p.add(bytes(4))
            else: _need(False, 'unknown finite program token')
    for at, label in near: p.raw[at:at + 4] = (p.labels[label] - at - 4).to_bytes(4, 'little', signed=True)
    return p.finish(), {name: base + at for name, at in p.labels.items()}


def _dispatcher_program(base: int, targets: dict[str, int]) -> bytes:
    p = _Program(base)
    p.add('48895c24084889742410574883ec200fb7d9498bf0488b0a488bfa'); p.call(targets['classPrepare'])
    p.add('488d4b1448c1e10448030f488b014c8b4108'); p.rip('488d0d', targets['jsonKey'])
    p.add('483bc1'); p.branch(0x74, 'jsonKey'); p.rip('488d0d', targets['runtimeField'])
    p.add('488bd6483bc1'); p.branch(0x74, 'runtimeField')
    restore = '488b5c2430488b7424384883c4205f'
    p.add('488bcf' + restore + '48ffe0')
    p.mark('jsonKey'); p.add('4885f6'); p.branch(0x74, 'nullExit'); p.add('488b4630' + restore + 'c3')
    p.mark('runtimeField'); p.add('488b4f18' + restore)
    p.add('e9'); p.add((targets['fieldRead'] - base - len(p.raw) - 4).to_bytes(4, 'little', signed=True))
    p.mark('nullExit'); p.call(targets['nullFailure']); p.add('cc')
    return p.finish()


def validate_chain_field_rules(image: Any, spec: dict, contract: dict, extents: dict[int, int]) -> dict:
    """Validate a gated image; the root validates inherited prerequisite groups."""
    _need(all(spec.get(k) == v for k, v in _CLAIMS.items()) and spec.get('methodRefs') == _METHOD_REFS
          and spec.get('helperRefs') == _HELPER_REFS and spec.get('usageRefs') == _USAGE_REFS,
          'unsupported schema/reference/boundary')
    methods = _named(spec['methods'], ('chainGet', 'newFieldGet', 'arrayGet'), 'methods'); targets = {}; bodies = {}
    for name in set(_METHODS) - set(_FAST_IMAGES):
        row = spec['fieldGet'] if name == 'fieldGet' else _ref(contract, _METHOD_REFS[name]) if name in _METHOD_REFS else methods[name]
        targets[name], bodies[name] = _identity(image, row, name, extents)
    for name, row in _named(spec['fastPointerMethods'], _FAST_IMAGES, 'fast pointers').items():
        # The fast comparisons identify registered MethodDefs, not runtime selection.
        row = dict(row); row.setdefault('parameterCount', len(row['parameterTypes']))
        targets[name], _ = _identity(image, row, name, extents)
    helpers = _named(spec['helpers'], ('fieldGetDispatch', 'classPrepare', 'fieldRead'), 'helpers')
    for name, row in {**helpers, **{n: _ref(contract, ref) for n, ref in _HELPER_REFS.items()}}.items():
        targets[name] = _rva(row['rva']); size = row['byteCount']
        _need(type(size) is int and 0 < size <= 65536, name + ': invalid window length')
        if name in ('fieldGetDispatch', 'fieldRead'):
            _need(extents.get(image.pe.image_base + targets[name]) == image.pe.image_base + targets[name] + size,
                  name + ': exact helper extent differs')
        _hash(image.pe.bytes_at_va(image.pe.image_base + targets[name], size), row, name)
    _need(spec.get('dispatcherEdges') == {'classPrepareRva': hex(targets['classPrepare']), 'fieldReadRva': hex(targets['fieldRead'])},
          'dispatcher: edge declarations differ')
    cells = {}; definition = None
    for name, path in _USAGE_REFS.items():
        row = _ref(contract, path); cells[name] = _rva(row['cellRva']); selected = _usage(image, row)
        if name == 'dictionary': definition = selected
    _need(definition is not None, 'dictionary: stored context absent')
    _dictionary_target(image, definition, targets['dictionaryItem'])
    _expect(bodies['fieldEqual'], _field_equal_program(targets['fieldEqual'],
        _rva(contract['referenceUpdateRules']['nonnullFieldEqualityHelperRva'])), 'chainField.fieldEqual.null-selection')
    _need(set(spec['initialization']) == {'chainGet', 'chainSet'}, 'initialization: declaration set differs')
    labels = {}
    for name, blocks in [('chainGet', _GET_BLOCKS), ('chainSet', _SET_BLOCKS)]:
        _need(set(spec['initialization'][name]) == {'flagRva'}, 'initialization: unknown declarations')
        program, labels[name] = _program(targets[name], blocks, targets, cells, _rva(spec['initialization'][name]['flagRva']))
        _expect(bodies[name], program, 'chainField.' + name + '.full-finite-arguments-and-control')
    _expect(image.pe.bytes_at_va(image.pe.image_base + targets['fieldGetDispatch'], helpers['fieldGetDispatch']['byteCount']),
            _dispatcher_program(targets['fieldGetDispatch'], targets), 'chainField.fieldGetDispatch.full-finite-slot-and-targets')
    return {'status': 'validated_conditional_chain_field_recipe', 'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
        'getterRecipe': spec['getterRecipe'], 'setterRecipe': spec['setterRecipe'], 'aliasBoundary': spec['aliasBoundary'],
        'dispatcherBoundary': spec['dispatcherBoundary'], 'entryRvas': {n: {k: hex(v) for k, v in rows.items()} for n, rows in labels.items()},
        'unresolved': ['runtime-input-storage-and-aliases', 'helper-mutation-and-concurrency', 'reflection-and-cast-success',
            'dictionary-results-and-exact-generic-sharing', 'runtime-FieldInfo-implementation', 'runtime-class-and-field-read-helpers',
            'new-field-storage-callee-outcomes', 'actual-execution']}


def validate_selected_chain_field_rules(contract: dict, *, gameassembly: Path, metadata: Path, spec: dict | None = None) -> dict:
    """Fail closed before opening anything except the explicit selected pair."""
    if gameassembly is None or metadata is None:
        return {'status': 'missing', 'evidenceBoundary': 'unresolved', 'detail': 'explicit GameAssembly and metadata paths are required'}
    inputs = contract['nativeInputs']
    _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')), 'nativeInputs: selected hashes required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
                                        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated': return {'status': gate.status, 'evidenceBoundary': 'unresolved', 'detail': gate.detail}
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.chainFields')
    return validate_chain_field_rules(image, contract['chainFieldRules'] if spec is None else spec, contract,
                                     image.mapper.pdata_function_extents(image.pe))
