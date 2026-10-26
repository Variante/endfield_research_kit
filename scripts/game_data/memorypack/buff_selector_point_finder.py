"""PointFinder stored fields composed from independent Vector3 child spans.

Evidence and admission boundary:

PointFinder has a maintained named reader under
`buff_selector_point_finder_native.json`
and `buff_selector_point_finder.py`.
The current selector union route, source contexts and generated setter
transfers prove `positionOffset` and `rotationOffset` as two separate
BlackboardVector3 fields. Each vector owns an independent original byte
range and reuses the authenticated x/y/z scalar children; null vectors and
null scalar children remain distinct. Original finder spans also reparse
their enclosing direct SelectorData field, preserving the recorded tag,
subtype and exact field boundary. The maintained SelectorData composition
is also replayed on the same original parent ranges; its remaining two
lists are independently verified empty. Positive lists retain their own
separate evidence requirements. This is an `exact` stored component with
`conditional` composition: complete roots still require the full family
gate and independent original-root replay. Evaluated offsets, resulting
coordinates, selected points and runtime execution remain `unresolved`.
"""
from __future__ import annotations
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import buff_effect_vector_child_receipt as vectors
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError

LABEL = 'buffSelectorPoint'
TAG = 14
CONTRACT_PATH = CONTRACTS_DIR / 'buff_selector_point_finder_native.json'


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-selector-point-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(c.get('records', {})) != {'pointFinder'}
            or c['dispatcher'].get('unionTag') != TAG
            or c.get('sourceContract') != 'finder_0e_native.json'
            or [m['fieldName'] for m in c['records']['pointFinder']['members']] != ['positionOffset', 'rotationOffset']
            or any(m['kind'] != 'BlackboardVector3' or m['declaredType'] != vectors._contract()['vectorRuntimeTypeName']
                for m in c['records']['pointFinder']['members'])):
        raise ValueError(f'{LABEL}.contract:shape')
    return c


def _members(c: dict) -> dict:
    return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in r['members']]
            for k, r in c['records'].items()}


def _fail(check: str, expected: Any, actual: Any, **details: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
        expected=str(expected)[:1024], actual=str(actual)[:1024])
    error.diagnostic.update(validator=LABEL, nativeInputs=_contract()['nativeInputs'], **details)
    raise error


def validate_current_native_contract(*, selector_native: dict[str, Any], vector_native: dict[str, Any],
        gameassembly: Path | None = None, metadata: Path | None = None) -> dict[str, Any]:
    c = _contract(); expected = c['nativeInputs']
    gate = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': expected}
    for name, child in (('selector', selector_native), ('vectors', vector_native)):
        if (child.get('status') != 'validated' or any(child.get('nativeInputs', {}).get(k) != expected[k]
                for k in ('GameAssembly.dll', 'global-metadata.dat'))):
            _fail('shared-child', expected, {'name': name, 'status': child.get('status'), 'nativeInputs': child.get('nativeInputs')})
    unity = gate.gameassembly.parent / 'UnityPlayer.dll'
    if not unity.is_file() or hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll', expected['UnityPlayer.dll'], 'missing-or-mismatched')
    image = open_native_image(gate.gameassembly, gate.metadata)
    source_path = CONTRACTS_DIR / c['sourceContract']; source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations, image.modules,
        image.owners, source=str(gate.gameassembly), contract_path=source_path, native_image=image)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=_fail)
    dispatch = c['dispatcher']; route = image.validate_dispatcher(dispatch, label=LABEL)
    image.check_instruction_windows([dispatch['typeLoadInstruction']], label=LABEL)
    rva, raw_hex = dispatch['typeLoadInstruction']; raw = bytes.fromhex(raw_hex)
    if (raw[:3] != b'\x48\x8b\x15' or len(raw) != 7
            or image.pe.image_base + rva + 7 + struct.unpack_from('<i', raw, 3)[0] != route['usageCell']):
        _fail('route-type-load', route['usageCell'], dispatch['typeLoadInstruction'])
    registry = selector_native['_registry']; record = c['records']['pointFinder']
    finder = [m for m in registry.plans[selector_native['selectorDefinition']] if m.name == 'finderData' and m.kind == 'union']
    definition = record['wrapperTypeDefinition']
    if (len(finder) != 1 or registry.union_tag_maps.get(finder[0].ref, {}).get(TAG) != definition
            or registry.wrapped_names.get(definition) != record['runtimeTypeName']):
        _fail('selector-parent-route', record['runtimeTypeName'], definition)
    after = check_installed_native_inputs(expected['GameAssembly.dll'], expected['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': expected}
    if hashlib.sha256(unity.read_bytes()).hexdigest().upper() != expected['UnityPlayer.dll']:
        _fail('UnityPlayer.dll-after', expected['UnityPlayer.dll'], 'mismatched')
    return {'status': 'validated', 'nativeInputs': expected, 'unionTag': TAG,
        'recordMembers': proved, 'evidenceBoundary': c['evidenceBoundary']}


def decode_finder(data: bytes, *, source: str, digest: str, start: int, end: int,
        context: dict[str, Any]) -> dict[str, Any]:
    c = _contract(); proof = context.get('pointFinder', {})
    if (proof.get('status') != 'validated' or proof.get('nativeInputs') != c['nativeInputs']
            or proof.get('unionTag') != TAG or proof.get('recordMembers') != _members(c)
            or not isinstance(data, bytes) or not isinstance(source, str) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    vector = context.get('effectVectors', {})
    leaf = vector.get('scalarNative', {})
    if (vector.get('status') != 'validated' or vector.get('nativeInputs') != c['nativeInputs']
            or vector.get('vectorMemberNames') != ['x', 'y', 'z']
            or leaf.get('status') != 'validated' or leaf.get('sourceStoreValidated') is not True
            or leaf.get('selectedReadOrder') != scalar._contract()['selectedReadOrder']):
        raise ValueError(f'{LABEL}.decode:shared-vector-scalar-native')
    reader = Reader(data, source, end); reader.pos = start
    tag = reader.nested_union_tag((TAG,), 'point-finder'); fields = []
    if tag is None:
        status = 'exact-null-union'
    elif reader.peek() == 255:
        reader.take(1, 'null-finder-wrapper'); status = 'exact-null-wrapper'
    else:
        members = c['records']['pointFinder']['members']; reader.header(len(members))
        status = 'named-finder-exact-span'
        for member in members:
            at = reader.pos; reader.vector_payload()
            child = vectors.decode_blackboard_vector3_value(data, source=source, logical_sha256=digest,
                start=at, end=reader.pos, native_validation=vector)
            if child.get('wholeValueExact') is not True or child.get('recursiveStoredSchemaExact') is not True:
                raise ValueError(f'{LABEL}.decode:vector-child-incomplete')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                'kind': member['kind'], 'start': at, 'end': reader.pos, 'child': child})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:finder-end={reader.pos}; expected={end}')
    return {'source': source, 'logicalSha256': digest.upper(), 'start': start, 'end': end, 'tag': tag,
        'typeName': c['records']['pointFinder']['runtimeTypeName'], 'status': status,
        'namedFields': fields, 'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
