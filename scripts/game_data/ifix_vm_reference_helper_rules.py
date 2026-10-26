"""Authenticate the complete small reference-array and cast programs offline.

The array helpers compare unsigned EDX with the stored array length, then use
the full RDX in their effective address. This is a low-32-bit guard, not proof
that an arbitrary 64-bit index is valid. A successful fetch reads one selected
element; a successful store writes its incoming R8/R8D. Failure requests the
already cataloged bounds helper and reaches INT3 if that request returns.

The managed store writes the object element before its optional native bitmap
update. A stored flag selects that update; the element address determines one
bit, and a locked compare/exchange loop retries until the selected word update
succeeds. The bitmap and flag are anonymous native globals. Their runtime
values, storage validity, concurrency, policy and loop completion stay open.

The cast wrapper returns null for a null object. Otherwise it requests the
cataloged class probe with the object's class and incoming target class, then
returns the original object when AL is nonzero, or null when AL is zero. Probe
success, mutation and type compatibility are not established by the wrapper.
The existing typeTest row is authenticated as an alias of the canonical cast
row; no second native callee catalog is introduced.

Programs reuse existing helper identities and add complete-body declarations
in a separate reviewed group. The explicit selected input gate and exact pdata
extents precede all native effects. This is not runtime execution or an array,
reflection, GC or object-identity emulator. Native anchors stay in JSON.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import NativeImage
from scripts.game_data.ifix_vm_delegate_bridge_rules import _Program
from scripts.game_data.ifix_vm_reference_address_rules import _ref, _rva, _hash, _expect


class ReferenceHelperRuleError(ValueError):
    """A small reference helper exceeds its selected bytes or declared boundary."""


_PROGRAM_REFS = {
    'managedFetch': 'initobjTypeOperand.consumerRowFetchHelper',
    'managedStore': 'constrainedTypeOperand.stackEffect.managedStackStoreHelper',
    'anonymousInfoFetch': 'functionPointerRules.helpers.anonymousInfoFetch',
    'int32Fetch': 'functionPointerRules.helpers.int32ArrayFetch',
    'int32Store': 'referenceAddressRules.helpers.int32ArrayStore',
    'cast': 'referenceUpdateRules.helpers.cast',
}
_HELPER_REFS = {
    'boundsFailure': 'referenceUpdateRules.helpers.boundsFailure',
    'classProbe': 'anonymousLoaderRules.helpers.classProbe',
}
_EFFECTS = {
    'managedFetch': 'return-qword-at-array+32+full64-index*8',
    'managedStore': 'write-R8-at-array+32+full64-index*8-before-optional-bitmap-update',
    'anonymousInfoFetch': 'return-qword-at-array+32+full64-index*8',
    'int32Fetch': 'return-zero-extended-dword-at-array+32+full64-index*4',
    'int32Store': 'write-R8D-at-array+32+full64-index*4',
    'cast': 'null-input-or-original-object-if-classProbe-AL-nonzero-else-null',
}
_CLAIMS = {
    'schema': 'endfield.ifix-vm-reference-helper-rules.v1',
    'evidenceBoundary': 'conditional',
    'executionBoundary': 'unobserved',
    'helperRefs': _HELPER_REFS,
    'castAliasRef': 'functionPointerRules.helpers.typeTest',
    'boundsGuard': 'unsigned-low32-index-below-stored-length-at-offset24',
    'addressIndex': 'full64-RDX-without-local-normalization',
    'arrayBoundary': 'valid-storage-and-compatible-full64-index-required',
    'failureBoundary': 'boundsFailure-request-then-INT3-if-returned',
    'bitmapBoundary': 'anonymous-native-storage-flag-and-CAS-completion-unobserved',
    'castBoundary': 'classProbe-result-and-mutation-unobserved',
    'effects': _EFFECTS,
}


def _need(ok: bool, detail: str) -> None:
    if not ok:
        raise ReferenceHelperRuleError('reference-helper.' + detail)


def _address(value: Any, role: str) -> int:
    _need(type(value) in (str, int), 'address is not an integer/hex string: ' + role)
    try:
        result = _rva(value)
    except (TypeError, ValueError):
        raise ReferenceHelperRuleError('reference-helper.invalid address: ' + role) from None
    _need(result >= 0, 'negative address: ' + role)
    return result


def _mapped_span(image: Any, at: int, size: int, role: str) -> None:
    matches = [s for s in image.pe.sections
               if type(s.get('virtualAddress')) is int and type(s.get('virtualSize')) is int
               and type(s.get('rawSize')) is int and s['virtualAddress'] <= at
               and at + size <= s['virtualAddress'] + max(s['virtualSize'], s['rawSize'])]
    _need(len(matches) == 1, 'native global mapped span missing/ambiguous: ' + role)


def _claims(spec: dict[str, Any]) -> None:
    _need(isinstance(spec, dict) and all(type(spec.get(k)) is type(v) and spec.get(k) == v
                                      for k, v in _CLAIMS.items()), 'unsupported schema/reference/boundary')
    _need(set(spec.get('programs', {})) == set(_PROGRAM_REFS), 'complete program catalog differs')
    _need(set(spec.get('nativeGlobals', {})) == {'flag', 'bitmap'}, 'anonymous global catalog differs')
    for role, kind in [('flag', 'anonymous-native-Int32-flag'), ('bitmap', 'anonymous-native-qword-bitmap')]:
        row = spec['nativeGlobals'][role]
        _need(set(row) == {'rva', 'identity'} and row.get('identity') == kind,
              'anonymous global declaration differs: ' + role)


def _array_program(role: str, at: int, bounds: int, globals_: dict[str, int]) -> bytes:
    p = _Program(at)
    p.add('4883ec283b5118')
    if role == 'anonymousInfoFetch':
        p.branch(0x72, 'access'); p.call(bounds); p.add('cc'); p.mark('access')
        p.add('488b44d1204883c428c3')
        return p.finish()
    p.branch(0x73, 'failure')
    if role == 'managedStore':
        p.rip('833d', globals_['flag'], b'\x00')
        p.add('4c8944d120'); p.branch(0x74, 'return')
        p.add('4883c2044c8d04d149c1e80c'); p.rip('488d0d', globals_['bitmap'])
        p.add('4181e0ffff1f00418bc048c1e8064183e03f488d14c10f0d0a'
              '0f1f4000660f1f840000000000')
        p.mark('retry'); p.add('488b02488bc84c0fabc1f0480fb10a'); p.branch(0x75, 'retry')
        p.mark('return'); p.add('4883c428c3')
    else:
        p.add({'managedFetch': '488b44d120', 'int32Fetch': '8b449120',
               'int32Store': '4489449120'}[role]); p.add('4883c428c3')
    p.mark('failure'); p.call(bounds); p.add('cc')
    return p.finish()


def _cast_program(at: int, probe: int) -> bytes:
    p = _Program(at)
    p.add('40534883ec20488bd94885c9'); p.branch(0x74, 'null')
    p.add('488b09'); p.call(probe)
    p.add('33c984c0480f44d9488bc34883c4205bc3')
    p.mark('null'); p.add('33c04883c4205bc3')
    return p.finish()


def validate_reference_helper_rules(image: Any, spec: dict[str, Any], contract: dict[str, Any],
                                    extents: dict[int, int]) -> dict[str, Any]:
    """Prove full finite programs on the caller's explicitly gated NativeImage."""
    _claims(spec)
    targets = {}
    for role, path in _HELPER_REFS.items():
        row = _ref(contract, path); at = _address(row['rva'], role); count = row['byteCount']
        _need(type(count) is int and 0 < count <= 4096, 'inherited helper extent differs: ' + role)
        _hash(image.pe.bytes_at_va(image.pe.image_base + at, count), row, role); targets[role] = at
    globals_ = {role: _address(row['rva'], role) for role, row in spec['nativeGlobals'].items()}
    _need(globals_['flag'] % 4 == 0 and globals_['bitmap'] % 8 == 0,
          'anonymous native globals are not aligned')
    # The selected globals can lie in a virtual-only section tail. Authenticate
    # mapped section containment without inventing on-disk or runtime contents.
    _mapped_span(image, globals_['flag'], 4, 'flag')
    _mapped_span(image, globals_['bitmap'], (1 << 21) // 8, 'bitmap')
    complete = []
    for role, path in _PROGRAM_REFS.items():
        row = spec['programs'][role]
        _need(set(row) == {'helperRef', 'bodyBytes', 'bodySha256'} and row.get('helperRef') == path,
              'canonical complete program reference differs: ' + role)
        size = row['bodyBytes']; _need(type(size) is int and 0 < size <= 4096, 'program size differs: ' + role)
        inherited = _ref(contract, path); at = _address(inherited['rva'], role); start = image.pe.image_base + at
        prefix_size = inherited['byteCount']
        _need(type(prefix_size) is int and 0 < prefix_size <= size, 'inherited prefix exceeds program: ' + role)
        _need(extents.get(start) == start + size, 'exact pdata program extent differs: ' + role)
        raw = image.pe.bytes_at_va(start, size)
        _hash(raw[:prefix_size], inherited, role + '.inherited')
        _need(isinstance(row['bodySha256'], str)
              and hashlib.sha256(raw).hexdigest().upper() == row['bodySha256'].upper(),
              'complete program hash differs: ' + role)
        expected = (_cast_program(at, targets['classProbe']) if role == 'cast' else
                    _array_program(role, at, targets['boundsFailure'], globals_))
        _expect(raw, expected, 'reference-helper.' + role)
        if role == 'cast':
            alias = _ref(contract, spec['castAliasRef'])
            _need(_address(alias['rva'], 'typeTest.alias') == at and type(alias['byteCount']) is int
                  and alias['byteCount'] == size, 'typeTest is not the complete canonical cast alias')
            _hash(raw, alias, 'typeTest.alias')
        complete.append(role)
    return dict(status='validated_conditional_reference_helper_rules', completePrograms=complete,
                canonicalCastRef=_PROGRAM_REFS['cast'], castAliasRef=spec['castAliasRef'],
                effects=dict(_EFFECTS), boundsGuard=spec['boundsGuard'], addressIndex=spec['addressIndex'],
                bitmapEffect='flag-nonzero:atomic-OR-selected-element-address-page-bit-with-retry',
                evidenceBoundary='conditional', executionBoundary='unobserved',
                unresolved=['runtime-array-storage-and-full64-index-compatibility', 'anonymous-flag-and-bitmap-values',
                            'CAS-contention-and-completion', 'classProbe-result-and-mutation',
                            'boundsFailure-outcome', 'actual-execution'])


def project_reference_helper_rules(spec: dict[str, Any]) -> dict[str, Any]:
    """Expose formulas without selecting live addresses, flags, bounds or objects."""
    _claims(spec)
    return dict(helperRefs=dict(_PROGRAM_REFS), effects=dict(_EFFECTS), castAliasRef=spec['castAliasRef'],
                guard='uint32(RDX)<uint32(*(array+24))',
                qwordAddress='array+32+RDX*8 (wrapping UInt64 address arithmetic)',
                dwordAddress='array+32+RDX*4 (wrapping UInt64 address arithmetic)',
                addressBoundary=spec['arrayBoundary'], bitmapFlag='*(anonymous-flag)!=0',
                bitmapWord='bitmap+8*(((elementAddress>>12)&0x1fffff)>>6)',
                bitmapBit='((elementAddress>>12)&0x1fffff)&63',
                bitmapBoundary=spec['bitmapBoundary'], castBoundary=spec['castBoundary'],
                evidenceBoundary='conditional', executionBoundary='unobserved')


def validate_selected_reference_helper_rules(contract: dict[str, Any], *, gameassembly: Path,
                                              metadata: Path, spec: dict[str, Any] | None = None) -> dict[str, Any]:
    """Fail closed on absent or mismatched explicit inputs before opening them."""
    if gameassembly is None or metadata is None:
        return dict(status='missing', evidenceBoundary='unresolved',
                    detail='explicit GameAssembly and metadata paths are required')
    inputs = contract['nativeInputs']
    _need(bool(inputs.get('gameAssemblySha256')) and bool(inputs.get('globalMetadataSha256')),
          'selected input hashes are required')
    gate = check_installed_native_inputs(inputs['gameAssemblySha256'], inputs['globalMetadataSha256'],
                                        gameassembly=Path(gameassembly), metadata=Path(metadata))
    if gate.status != 'validated':
        return dict(status=gate.status, evidenceBoundary='unresolved', detail=gate.detail)
    image = NativeImage(gate.gameassembly, gate.metadata, label='ifix.referenceHelpers')
    return validate_reference_helper_rules(image, contract['referenceHelperRules'] if spec is None else spec,
                                          contract, image.mapper.pdata_function_extents(image.pe))
