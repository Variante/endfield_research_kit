"""Prove IFix's unequal-Type Ldvirtftn resolver from selected native evidence.

The parent owns the native input/Execute gate and external-row producer. Stored
MethodSpec contexts, cache arguments and search control flow are authenticated
here; no runtime cache contents, reflection result or generic sharing decision
is interpreted. Normal-return rules can cache and later consume a null value.

The outer cache uses the original receiver Type and the inner cache uses the
declared MethodInfo's GetBaseDefinition. A hit consumes the stored reference,
including null, without searching. On a miss, GetMember uses the base name,
Method kind and Instance/Public/NonPublic flags; the first returned candidate
with an equal base definition wins. Otherwise the search advances through
BaseType and caches null on exhaustion. DeclaredOnly is absent, so this does
not prove the nearest declared override or the runtime member enumeration order.
"""
from __future__ import annotations

import hashlib
from typing import Any

from scripts.game_data.ifix_vm_basic_rules import resolve_dispatch_entry
from scripts.game_data.il2cpp.context import (
    generic_method_candidates, rip_qword_load_target, unresolved_usage_index, usage_method_spec,
)
from scripts.game_data.il2cpp.protocol import enum_members, field_defaults, runtime_type_name


class VirtualDispatchRuleError(ValueError):
    """An unequal-Type rule lacks its selected native/context witness."""


_INNER_TYPE = 'System.Collections.Generic.Dictionary`2<System.Reflection.MethodInfo,System.Reflection.MethodInfo>'
_DICTIONARY_ROLES = {
    'outerTry': ('TryGetValue', ['System.Type', _INNER_TYPE], ['key', 'value']),
    'innerCtor': ('.ctor', ['System.Reflection.MethodInfo', 'System.Reflection.MethodInfo'], []),
    'outerSet': ('set_Item', ['System.Type', _INNER_TYPE], ['key', 'value']),
    'innerTry': ('TryGetValue', ['System.Reflection.MethodInfo', 'System.Reflection.MethodInfo'], ['key', 'value']),
    'innerSet': ('set_Item', ['System.Reflection.MethodInfo', 'System.Reflection.MethodInfo'], ['key', 'value']),
}
_VIRTUAL_ROLES = {
    'name': ('System.Reflection.MemberInfo', 'get_Name', [], 'string'),
    'baseDefinition': ('System.Reflection.MethodInfo', 'GetBaseDefinition', [], 'System.Reflection.MethodInfo'),
    'members': ('System.Type', 'GetMember', ['string', 'System.Reflection.MemberTypes', 'System.Reflection.BindingFlags'], 'System.Reflection.MemberInfo[]'),
    'baseType': ('System.Type', 'get_BaseType', [], 'System.Type'),
}
_HELPER_REFS = {
    'runtimeTypeGet': 'functionPointerRules.helpers.objectGetType',
    'typeTest': 'functionPointerRules.helpers.typeTest',
    'arrayFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'virtualInvoke': 'newobjSelector.virtualInvokeHelper',
    'typeEquality': 'newobjSelector.pointerEquality',
    'zeroRegister': 'basicOpcodeRules.sharedWindows.zeroRegister',
}
_HELPERS = ('nameInvoke', 'baseDefinitionInvoke', 'memberInvoke', 'methodEquality',
            'methodInequality', 'typeInequality', 'incrementInt32', 'tryGetValueBody',
            'dictionaryCtorBody', 'dictionarySetBody', 'allocationHelper')
_WINDOWS = ('normalizationAndOuterCache', 'innerCacheLookup', 'hierarchyMembers',
            'candidateLoop', 'hierarchyAdvanceAndCacheStore')
_CALLS = {
    'runtimeTypeGet': 'runtimeTypeGet', 'declaredTypeTest': 'typeTest', 'declaredBaseTypeTest': 'typeTest',
    'declaredBaseDefinition': 'baseDefinitionInvoke', 'outerTry': 'outerTry',
    'allocateInner': 'allocationHelper', 'innerCtor': 'innerCtor', 'outerSet': 'outerSet', 'innerTry': 'innerTry',
    'hierarchyTypeNonNull': 'typeInequality', 'methodName': 'nameInvoke', 'members': 'memberInvoke',
    'candidateFetch': 'arrayFetch', 'candidateTypeTest': 'typeTest', 'candidateBaseDefinition': 'baseDefinitionInvoke',
    'baseDefinitionEquality': 'methodEquality', 'incrementCandidate': 'incrementInt32',
    'selectedNonNull': 'methodInequality', 'baseType': 'virtualInvoke', 'innerSet': 'innerSet',
}
_FLOW = {
    'sameTypeBypass': ('jne', 'declaredStore'), 'outerHit': ('jne', 'innerCacheLookup'),
    'innerHit': ('jne', 'resolvedStore'), 'typeExhausted': ('je', 'cacheStore'),
    'candidateArrayExhausted': ('jge', 'selectedReload'), 'candidateMatch': ('jne', 'candidateStore'),
    'nextCandidate': ('jump', 'candidateLoop'), 'matchedCandidateJoin': ('jump', 'selectedCheck'),
    'selectedNonNull': ('jne', 'cacheStore'), 'nextBaseType': ('jump', 'hierarchyMembers'),
}
_WITNESSES = {
    'runtimeTypeArguments': '33d2488bce', 'runtimeTypeResult': '4c8bf8',
    'declaredBaseSlot': 'b9', 'declaredBaseArgument': '488bd0', 'baseDefinitionResult': '4c8bf0',
    'selectedNullInitialize': '4c89ac2480000000', 'outerCacheField': '488b5f',
    'outerTryArguments': '4c8d8424a0000000498bd7488bcb', 'outerTryBoolean': '413ac5',
    'innerAllocationResult': '488bd8', 'innerConstructArgument': '488bcb',
    'innerStoreLocal': '48899c24a0000000', 'outerCacheReload': '488b7f',
    'outerSetArguments': '4c8bc3498bd7488bcf', 'innerCacheLoad': '488b9c24a0000000',
    'innerTryArguments': '4c8d842480000000498bd6488bcb', 'innerTryBoolean': '413ac5',
    'typeNonNullArguments': '4533c033d2498bcf', 'typeNonNullBoolean': '413ac5',
    'methodTypeAndNameSlot': 'bf', 'nameArguments': '8bcf498bd6',
    'memberSlot': '8d4f', 'bindingFlags': 'c7442420', 'memberArguments': '448bcf4c8bc3498bd7',
    'memberArrayAndCounter': '488bf8418bf5', 'candidateArrayBounds': '3b7718',
    'candidateFetchArguments': '4863d6488bcf', 'candidateTypeTestArgument': '488bc8',
    'candidateResult': '488bd8', 'candidateBaseSlot': 'b9', 'candidateBaseArgument': '488bd3',
    'baseEqualityArguments': '4533c0498bd6488bc8', 'baseEqualityBoolean': '413ac5',
    'incrementArguments': 'ba010000008bce', 'candidateCounterCommit': '8bf0',
    'candidateStore': '48899c2480000000', 'selectedReload': '488b9c2480000000',
    'selectedNullCompareArguments': '4533c033d2488bcb', 'selectedBoolean': '413ac5',
    'baseTypeSlot': 'b9', 'baseTypeArgument': '498bd7', 'nextTypeCommit': '4c8bf8',
    'cacheStoreReferences': '488b9c24a0000000488bbc2480000000',
    'innerSetArguments': '4c8bc7498bd6488bcb',
}
_METHOD_CALL_IDENTITIES = {
    'methodEquality': ('System.Reflection.MethodInfo', 'op_Equality'),
    'methodInequality': ('System.Reflection.MethodInfo', 'op_Inequality'),
    'typeInequality': ('System.Type', 'op_Inequality'),
}
_LOOKUP_WITNESSES = {
    'outArgumentSaved': '498bd8', 'indexAndHitSplit': '4863f085c07907',
    'missOutNull': '33c0488903', 'hitOutReference': '488b44cf30488903', 'hitBoolean': 'b001',
}


def _rva(value: str | int) -> int:
    return int(value, 0) if isinstance(value, str) else int(value)


def _named(rows: list[dict[str, Any]], expected: Any, label: str) -> dict[str, dict[str, Any]]:
    mapped = {row.get('name'): row for row in rows}
    if len(mapped) != len(rows) or set(mapped) != set(expected):
        raise VirtualDispatchRuleError(f'virtual-dispatch.{label}: missing/duplicate/unknown declarations')
    return mapped


def _ref(contract: dict[str, Any], path: str) -> dict[str, Any]:
    row: Any = contract
    for key in path.split('.'):
        if isinstance(row, list):
            found = [item for item in row if item.get('name', item.get('opcode', item.get('role'))) == key]
            if len(found) != 1:
                raise VirtualDispatchRuleError(f'virtual-dispatch: ambiguous/missing reference {path}')
            row = found[0]
        elif isinstance(row, dict) and key in row:
            row = row[key]
        else:
            raise VirtualDispatchRuleError(f'virtual-dispatch: missing reference {path}')
    if not isinstance(row, dict):
        raise VirtualDispatchRuleError(f'virtual-dispatch: invalid reference {path}')
    return row


def _slice(body: bytes, base: int, site: int, count: int, label: str) -> bytes:
    at = site - base
    if count < 1 or not 0 <= at <= len(body) - count:
        raise VirtualDispatchRuleError(f'virtual-dispatch.{label}: outside Execute body rva={site:#x} bytes={count}')
    return body[at:at + count]


def _hash(raw: bytes, row: dict[str, Any], label: str) -> None:
    actual = hashlib.sha256(raw).hexdigest().upper()
    if actual != str(row['sha256']).upper():
        raise VirtualDispatchRuleError(f"virtual-dispatch.{label}: mismatched expectedSha256={row['sha256']} actualSha256={actual}")


def _edge(body: bytes, base: int, row: dict[str, Any], target: int, label: str) -> None:
    site, kind = _rva(row['rva']), row['kind']
    byte = _slice(body, base, site, 1, label)[0]
    short = {'jump': 0xeb, 'je': 0x74, 'jne': 0x75, 'jge': 0x7d}.get(kind)
    if short is not None and byte == short:
        raw = _slice(body, base, site, 2, label)
        actual = site + 2 + int.from_bytes(raw[1:], 'little', signed=True)
    else:
        prefix = {'call': b'\xe8', 'jump': b'\xe9', 'je': b'\x0f\x84', 'jne': b'\x0f\x85', 'jge': b'\x0f\x8d'}[kind]
        raw = _slice(body, base, site, len(prefix) + 4, label)
        actual = site + len(raw) + int.from_bytes(raw[len(prefix):], 'little', signed=True) if raw.startswith(prefix) else None
    if actual != target:
        raise VirtualDispatchRuleError(f'virtual-dispatch.{label}: edge target/shape expected={target:#x} actual={actual}')


def _shape(spec: dict[str, Any]) -> None:
    if (spec.get('schema') != 'endfield.ifix-vm-virtual-dispatch-rules.v1'
            or spec.get('opcode') != 'Ldvirtftn' or spec.get('evidenceBoundary') != 'conditional'
            or spec.get('executionBoundary') != 'unobserved'
            or spec.get('selectedWhen') != 'receiver-runtime-Type-differs-from-declared-DeclaringType'
            or spec.get('cacheKey') != 'original-receiver-runtime-Type/declared-MethodInfo-GetBaseDefinition'
            or spec.get('nullResult') != 'cache-and-store-null-on-search-exhaustion'
            or spec.get('searchOrder') != 'first-returned-matching-candidate-then-BaseType'
            or spec.get('runtimeResultBoundary') != 'unobserved'
            or spec.get('storedContextBoundary') != 'exact-MethodSpec-and-class-instantiation; runtime-sharing-unobserved'
            or spec.get('helperRefs') != _HELPER_REFS):
        raise VirtualDispatchRuleError('virtual-dispatch: unsupported schema/rule/boundary/reference')
    _named(spec.get('windows', []), _WINDOWS, 'windows')
    _named(spec.get('helpers', []), _HELPERS, 'helpers')
    _named(spec.get('virtualMethods', []), _VIRTUAL_ROLES, 'virtualMethods')
    _named(spec.get('dictionaryContexts', []), _DICTIONARY_ROLES, 'dictionaryContexts')
    _named(spec.get('witnesses', []), _WITNESSES, 'witnesses')
    _named(spec.get('calls', []), _CALLS, 'calls')
    _named(spec.get('branches', []), _FLOW, 'branches')


def _runtime_type(image: Any, index: int) -> str:
    pointer = image.pe.u64_at_va(_rva(image.registration['types']) + index * 8)
    return runtime_type_name(image.pe, image.metadata, pointer)


def _method(image: Any, row: dict[str, Any], *, pointer: bool, label: str) -> Any:
    identity = [row['methodIndex'], row['type'], row['method']]
    if pointer:
        identity.append(_rva(row['rva']))
    index = image.validate_method_row(identity, label='virtual-dispatch.' + label)
    method = image.metadata.methods[index]
    params = image.metadata.parameters_for(method)
    if (method.token != _rva(row['token']) or method.parameter_count != row['parameterCount']
            or [image.metadata.string(p.name_index) for p in params] != row['parameterNames']):
        raise VirtualDispatchRuleError(f'virtual-dispatch.{label}: metadata token/parameters differ')
    return method


def validate_virtual_dispatch_rules(
    image: Any, spec: dict[str, Any], body: bytes, body_rva: int,
    opcode_ids: dict[str, int], contract: dict[str, Any], extents: dict[int, int],
) -> dict[str, Any]:
    """Authenticate cache/search/null rules; concrete runtime outcomes stay open."""
    _shape(spec)
    expected_refs = {'producerRef': 'functionPointerRules.rules.Ldvirtftn',
                     'methodInfoTypeRef': 'delegateConstruction.methodInfoType',
                     'cacheFieldRef': 'functionPointerRules.runtimeFields.IFix.Core.VirtualMachine.overrideCache'}
    # Type names contain dots, so the owning field is reached explicitly below.
    if any(spec.get(key) != value for key, value in expected_refs.items()):
        raise VirtualDispatchRuleError('virtual-dispatch: unsupported producer/type/cache references')
    producer = _ref(contract, spec['producerRef'])
    if spec['opcodeId'] != opcode_ids.get('Ldvirtftn') or producer['opcodeId'] != spec['opcodeId']:
        raise VirtualDispatchRuleError('virtual-dispatch: opcode ID differs')
    entry = resolve_dispatch_entry(body, body_rva, _rva(contract['basicOpcodeRules']['dispatchStartRva']), spec['opcodeId'])
    if entry != _rva(producer['entryRva']):
        raise VirtualDispatchRuleError('virtual-dispatch: selected producer entry differs')
    p_windows = _named(producer['windows'], ('receiverAndWholeOperand', 'runtimeTypeOwnerComparison',
                         'unequalTypeResolver', 'resolvedObjectSlotStore', 'declaredObjectSlotStore'), 'parent producer windows')
    for row in p_windows.values():
        _hash(_slice(body, body_rva, _rva(row['rva']), row['byteCount'], row['name']), row, 'parent.' + row['name'])
    windows = _named(spec['windows'], _WINDOWS, 'windows')
    previous = _rva(p_windows['unequalTypeResolver']['rva'])
    for name in _WINDOWS:
        row = windows[name]
        if _rva(row['rva']) != previous:
            raise VirtualDispatchRuleError('virtual-dispatch: resolver windows are not contiguous')
        _hash(_slice(body, body_rva, previous, row['byteCount'], name), row, name)
        previous += row['byteCount']
    if previous != _rva(p_windows['resolvedObjectSlotStore']['rva']):
        raise VirtualDispatchRuleError('virtual-dispatch: search does not join the reviewed result store')
    targets = {name: _rva(row['rva']) for name, row in windows.items()}
    targets.update({'resolvedStore': _rva(p_windows['resolvedObjectSlotStore']['rva']),
                    'declaredStore': _rva(p_windows['declaredObjectSlotStore']['rva'])})
    for name, path in _HELPER_REFS.items():
        row = _ref(contract, path)
        site, size = _rva(row.get('windowRva', row['rva'])), row['byteCount']
        raw = (_slice(body, body_rva, site, size, path) if name == 'zeroRegister'
               else image.pe.bytes_at_va(image.pe.image_base + site, size))
        _hash(raw, row, path)
        targets[name] = _rva(row['rva'])
    if _slice(body, body_rva, targets['zeroRegister'], 3, 'zeroRegister') != bytes.fromhex('4533ed'):
        raise VirtualDispatchRuleError('virtual-dispatch: selected null/false register differs')
    helpers = _named(spec['helpers'], _HELPERS, 'helpers')
    for name, row in helpers.items():
        pointer, count = image.pe.image_base + _rva(row['rva']), row['byteCount']
        if count < 1 or (row['extentBoundary'] == 'pdata-exact' and extents.get(pointer) != pointer + count):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: native extent differs')
        if row['extentBoundary'] not in ('pdata-exact', 'explicit-reviewed-window'):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported extent declaration')
        raw = image.pe.bytes_at_va(pointer, count)
        _hash(raw, row, name)
        targets[name] = _rva(row['rva'])
        if name == 'typeInequality' and raw != bytes.fromhex('483bca0f95c0c3'):
            raise VirtualDispatchRuleError('virtual-dispatch: Type null comparison is not pointer inequality')
        if name == 'incrementInt32' and raw != bytes.fromhex('8d0411c3'):
            raise VirtualDispatchRuleError('virtual-dispatch: candidate increment helper differs')
        if name == 'methodInequality' and raw[:35] != bytes.fromhex('4883ec28488bc1483bca74134885c974054885d2750d32c034014883c428c3b001ebf5'):
            raise VirtualDispatchRuleError('virtual-dispatch: MethodInfo inequality null path differs')
        if name == 'nameInvoke' and raw[24:42] != bytes.fromhex('488d4b1448c1e10448030f488b01488b5108'):
            raise VirtualDispatchRuleError('virtual-dispatch: Name helper vtable slot program differs')
        if name == 'baseDefinitionInvoke' and raw[42:60] != bytes.fromhex('488d431448c1e0044803074c8b00488b5008'):
            raise VirtualDispatchRuleError('virtual-dispatch: base-definition helper vtable slot program differs')
        if name in _METHOD_CALL_IDENTITIES:
            if (row['type'], row['method']) != _METHOD_CALL_IDENTITIES[name]:
                raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported operator identity')
            method = _method(image, row, pointer=True, label=name)
            if method.parameter_count != 2 or _runtime_type(image, method.return_type) != 'bool':
                raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: operator signature differs')
    virtuals = _named(spec['virtualMethods'], _VIRTUAL_ROLES, 'virtualMethods')
    for name, row in virtuals.items():
        owner, method_name, parameter_types, return_type = _VIRTUAL_ROLES[name]
        if (row['type'], row['method'], row['parameterTypes'], row['returnType']) != (owner, method_name, parameter_types, return_type):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported virtual signature')
        method = _method(image, row, pointer=False, label=name)
        if (method.slot != row['virtualSlot'] or [_runtime_type(image, p.type_index) for p in image.metadata.parameters_for(method)] != parameter_types
                or _runtime_type(image, method.return_type) != return_type):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: virtual slot/types differ')
    member_helper = image.pe.bytes_at_va(image.pe.image_base + _rva(helpers['memberInvoke']['rva']), helpers['memberInvoke']['byteCount'])
    table_offset = (virtuals['members']['virtualSlot'] + 20) * 16
    if (member_helper[49:63] != b'\x4c\x8b\x90' + table_offset.to_bytes(4, 'little')
            + b'\x48\x8b\x80' + (table_offset + 8).to_bytes(4, 'little')
            or member_helper[-3:] != bytes.fromhex('49ffe2')):
        raise VirtualDispatchRuleError('virtual-dispatch: GetMember helper vtable selection/tail differs')
    defaults = field_defaults(image.metadata)
    members = {r['name']: r['id'] for r in enum_members(image.metadata, defaults, 'System.Reflection.MemberTypes')}
    flags = {r['name']: r['id'] for r in enum_members(image.metadata, defaults, 'System.Reflection.BindingFlags')}
    declared_enums = spec['reflectionSelection']
    if (declared_enums.get('memberType') != {'name': 'Method', 'id': members.get('Method')}
            or declared_enums.get('bindingMembers') != {name: flags.get(name) for name in ('Instance', 'Public', 'NonPublic')}
            or declared_enums.get('excludedBindingMembers') != {'DeclaredOnly': flags.get('DeclaredOnly')}
            or type(flags.get('DeclaredOnly')) is not int
            or any(type(flags.get(name)) is not int for name in ('Instance', 'Public', 'NonPublic'))):
        raise VirtualDispatchRuleError('virtual-dispatch: reflection enum members differ')
    binding_mask = flags['Instance'] | flags['Public'] | flags['NonPublic']
    if declared_enums.get('bindingMask') != binding_mask or binding_mask & flags['DeclaredOnly']:
        raise VirtualDispatchRuleError('virtual-dispatch: reflection binding mask differs')
    cache_field = contract['functionPointerRules']['runtimeFields']['IFix.Core.VirtualMachine']['overrideCache']
    if cache_field['type'] != 'System.Collections.Generic.Dictionary`2<System.Type,' + _INNER_TYPE + '>':
        raise VirtualDispatchRuleError('virtual-dispatch: inherited override cache field type differs')
    dynamic = {
        'declaredBaseSlot': virtuals['baseDefinition']['virtualSlot'].to_bytes(4, 'little'),
        'candidateBaseSlot': virtuals['baseDefinition']['virtualSlot'].to_bytes(4, 'little'),
        'baseTypeSlot': virtuals['baseType']['virtualSlot'].to_bytes(4, 'little'),
        'methodTypeAndNameSlot': members['Method'].to_bytes(4, 'little'),
        'bindingFlags': binding_mask.to_bytes(4, 'little'),
        'outerCacheField': bytes([cache_field['offset']]), 'outerCacheReload': bytes([cache_field['offset']]),
    }
    delta = virtuals['members']['virtualSlot'] - virtuals['name']['virtualSlot']
    if members['Method'] != virtuals['name']['virtualSlot'] or not 0 <= delta <= 127:
        raise VirtualDispatchRuleError('virtual-dispatch: coupled Name/GetMember slot program differs')
    dynamic['memberSlot'] = bytes([delta])
    witnesses = _named(spec['witnesses'], _WITNESSES, 'witnesses')
    for name, expected_hex in _WITNESSES.items():
        expected = bytes.fromhex(expected_hex) + dynamic.get(name, b'')
        raw = _slice(body, body_rva, _rva(witnesses[name]['rva']), len(expected), name)
        if raw != expected:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported witness shape')
        targets[name] = _rva(witnesses[name]['rva'])
    targets['cacheStore'] = targets['cacheStoreReferences']
    targets['selectedCheck'] = targets['selectedNullCompareArguments']
    contexts = _named(spec['dictionaryContexts'], _DICTIONARY_ROLES, 'dictionaryContexts')
    reg, pe = image.registration, image.pe
    records_va = _rva(reg['methodSpecs'])
    records = pe.bytes_at_va(records_va, reg['methodSpecsCount'] * 12)
    contexts_checked = []
    for name, row in contexts.items():
        method_name, arguments, parameter_names = _DICTIONARY_ROLES[name]
        if row['classArgumentTypeNames'] != arguments or row['method']['method'] != method_name:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported dictionary method/context')
        method = _method(image, row['method'], pointer=False, label=name)
        if row['method']['type'] != 'System.Collections.Generic.Dictionary`2' or row['method']['parameterNames'] != parameter_names:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: dictionary metadata identity differs')
        thunk = row['thunk']
        raw = pe.bytes_at_va(pe.image_base + _rva(thunk['rva']), 12)
        _hash(raw, thunk, name + '.thunk')
        prefix = bytes.fromhex('488b15') if name == 'innerCtor' else bytes.fromhex('4c8b0d')
        if raw[:3] != prefix or raw[7] != 0xe9:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported context thunk shape')
        cell = rip_qword_load_target(raw[:7], pe.image_base + _rva(thunk['rva']), source='virtual-dispatch.' + name)
        inline = _slice(body, body_rva, _rva(row['inlineLoadRva']), 7, name + '.inline')
        if inline[:3] != prefix or rip_qword_load_target(inline, pe.image_base + _rva(row['inlineLoadRva']), source='virtual-dispatch.' + name) != cell:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: inline/thunk context cell differs')
        usage = usage_method_spec(pe.bytes_at_va(cell, 8), records, len(image.metadata.methods), reg['genericInstsCount'],
                                  source='virtual-dispatch.' + name, usage_offset=cell, records_offset=records_va)
        expected = row['usage']
        keys = ('index', 'rawHex', 'definition', 'classInstantiationIndex', 'methodInstantiationIndex', 'usageRawHex')
        if (any(usage[key] != expected[key] for key in keys) or cell != pe.image_base + _rva(expected['cellRva'])
                or usage['definition'] != row['method']['methodIndex'] or usage['methodInstantiationIndex'] != -1):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: stored MethodSpec differs')
        actual_arguments = [runtime_type_name(pe, image.metadata, a.type_pointer_va)
                            for a in image.instantiations.resolve(usage['classInstantiationIndex']).arguments]
        if actual_arguments != arguments:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: class argument order/types differ actual={actual_arguments}')
        target = _rva(thunk['rva']) + 12 + int.from_bytes(raw[8:], 'little', signed=True)
        expected_body = ('tryGetValueBody' if name in ('outerTry', 'innerTry') else
                         'dictionaryCtorBody' if name == 'innerCtor' else 'dictionarySetBody')
        if target != _rva(thunk['tailTargetRva']) or target != targets[expected_body]:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: shared-body tail target differs')
        targets[name] = _rva(thunk['rva'])
        contexts_checked.append({'name': name, 'storedMethodSpecIndex': usage['index'], 'classArguments': actual_arguments,
                                 'tailTargetRva': hex(target), 'evidenceBoundary': 'exact', 'runtimeSharingBoundary': 'unobserved'})
    type_loads = _named(spec['typeLoads'], ('declaredTypeTest', 'declaredBaseTypeTest', 'candidateTypeTest', 'innerAllocation'), 'typeLoads')
    for name, row in type_loads.items():
        declared_type = _ref(contract, spec['methodInfoTypeRef']) if name != 'innerAllocation' else spec['innerDictionaryType']
        raw = _slice(body, body_rva, _rva(row['rva']), 7, name)
        expected_prefix = bytes.fromhex('488b0d') if name == 'innerAllocation' else bytes.fromhex('488b15')
        cell = rip_qword_load_target(raw, pe.image_base + _rva(row['rva']), source='virtual-dispatch.' + name)
        if raw[:3] != expected_prefix or cell != pe.image_base + _rva(declared_type['cellRva']):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: type-cell load differs')
        raw_usage = pe.bytes_at_va(cell, 8)
        index = unresolved_usage_index(raw_usage, reg['typesCount'], tag=1, source='virtual-dispatch.' + name, offset=cell)
        expected_type = _INNER_TYPE if name == 'innerAllocation' else 'System.Reflection.MethodInfo'
        if (int.from_bytes(raw_usage, 'little') != _rva(declared_type['encodedWord'])
                or index != declared_type['registeredTypeIndex'] or declared_type['typeName'] != expected_type
                or _runtime_type(image, index) != expected_type):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: stored type differs')
    calls = _named(spec['calls'], _CALLS, 'calls')
    for name, target_name in _CALLS.items():
        row = calls[name]
        if row['kind'] != 'call' or row['target'] != target_name:
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported call declaration')
        _edge(body, body_rva, row, targets[target_name], name)
    for name, (kind, target_name) in _FLOW.items():
        row = _named(spec['branches'], _FLOW, 'branches')[name]
        if (row['kind'], row['target']) != (kind, target_name):
            raise VirtualDispatchRuleError(f'virtual-dispatch.{name}: unsupported branch declaration')
        _edge(body, body_rva, row, targets[target_name], name)
    lookup = helpers['tryGetValueBody']
    lookup_bytes = pe.bytes_at_va(pe.image_base + _rva(lookup['rva']), lookup['byteCount'])
    if set(spec['tryGetValueWitnesses']) != set(_LOOKUP_WITNESSES):
        raise VirtualDispatchRuleError('virtual-dispatch.TryGetValue: missing/unknown witnesses')
    for name, shape in _LOOKUP_WITNESSES.items():
        offset = spec['tryGetValueWitnesses'][name]
        if lookup_bytes[offset:offset + len(bytes.fromhex(shape))] != bytes.fromhex(shape):
            raise VirtualDispatchRuleError(f'virtual-dispatch.TryGetValue.{name}: unsupported out/result witness')
    lookup_edges = _named(spec['tryGetValueEdges'], ('missReturn', 'hitWithoutBarrier'), 'TryGetValue.edges')
    for name, row in lookup_edges.items():
        at = row['offset']
        raw = lookup_bytes[at:at + 2]
        expected_opcode = {'missReturn': 0xeb, 'hitWithoutBarrier': 0x74}[name]
        target_offset = at + 2 + int.from_bytes(raw[1:], 'little', signed=True) if len(raw) == 2 and raw[0] == expected_opcode else None
        if target_offset != row['targetOffset']:
            raise VirtualDispatchRuleError(f'virtual-dispatch.TryGetValue.{name}: result branch differs')
    if (lookup_edges['missReturn']['targetOffset'] != spec['tryGetValueWitnesses']['hitBoolean'] + 2
            or lookup_edges['hitWithoutBarrier']['targetOffset'] != spec['tryGetValueWitnesses']['hitBoolean']):
        raise VirtualDispatchRuleError('virtual-dispatch.TryGetValue: null miss and reference hit do not join their reviewed returns')
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    table_va = _rva(reg['genericMethodTable'])
    generic_rows = generic_method_candidates(pe.bytes_at_va(table_va, reg['genericMethodTableCount'] * 16),
        reg['genericMethodTableCount'], reg['methodSpecsCount'], {r['usage']['index'] for r in contexts.values()},
        code['genericMethodPointersCount'], code['invokerPointersCount'], source='virtual-dispatch.GenericMethod', offset=table_va)
    candidates = [{'methodSpecIndex': r['methodSpecIndex'], 'tableIndex': r['tableIndex'],
                   'pointerRva': hex(pe.u64_at_va(_rva(code['genericMethodPointers']) + r['indices'][0] * 8) - pe.image_base)}
                  for r in generic_rows]
    return {'status': 'validated_conditional_virtual_dispatch_rules', 'opcode': 'Ldvirtftn',
            'storedContexts': contexts_checked, 'genericMethodCandidates': candidates,
            'genericCandidateBoundary': 'stored-candidates-only; no-runtime-sharing-selection' if candidates else 'no-direct-table-rows-for-selected-stored-MethodSpecs',
            'cacheKey': spec['cacheKey'], 'nullResult': spec['nullResult'], 'searchOrder': spec['searchOrder'],
            'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved',
            'unresolved': ['runtime-Type-and-receiver-compatibility', 'dictionary-comparer/cache-contents-and-hit-miss',
                           'reflected-member-order-and-base-definition-results', 'runtime-generic-sharing-and-class-initialization',
                           'helper-exceptions-and-normal-return', 'concrete-selected-MethodInfo-or-null', 'delegate-binding-and-invocation']}


def project_virtual_dispatch_rules(decoded: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Describe authored Ldvirtftn alternatives without choosing a runtime method."""
    _shape(spec)
    rows = []
    for method in decoded['methods']:
        for instruction in method['instructions']:
            if instruction['name'] != 'Ldvirtftn':
                continue
            if instruction['opcode'] != spec['opcodeId']:
                raise VirtualDispatchRuleError('virtual-dispatch projection: opcode/name mismatch')
            rows.append({'vmMethodIndex': method['index'], 'instructionIndex': instruction['index'], 'offset': instruction['offset'],
                         'opcode': 'Ldvirtftn', 'selectedWhen': spec['selectedWhen'], 'cacheKey': spec['cacheKey'],
                         'conditionalResolution': {'outerMiss': 'allocate-inner-dictionary-and-cache-under-original-runtime-Type',
                             'innerHit': 'skip-reflection-and-store-cached-reference-including-null',
                             'innerMiss': 'enumerate-GetMember(base-definition-Name,Method,Instance|Public|NonPublic)',
                             'candidateMatch': 'first-returned-candidate-with-MethodInfo.op_Equality(GetBaseDefinition(),declared-base-definition)',
                             'noCandidate': 'advance-through-BaseType-until-null',
                             'searchExhausted': 'cache-null-under-original-runtime-Type-and-base-definition; store-null-Object-reference'},
                         'searchOrderBoundary': 'GetMember-may-include-inherited-members; nearest-declared-override-unproved',
                         'runtimeType': None, 'cacheHit': None, 'runtimeMethodInfo': None,
                         'evidenceBoundary': 'conditional', 'executionBoundary': 'unobserved'})
    return rows
