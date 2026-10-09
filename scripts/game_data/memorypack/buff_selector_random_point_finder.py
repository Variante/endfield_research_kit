"""Named RandomPointFinder operands with reviewed recursive blackboard joins.

The selected finder route and source/destination reads prove storage. Vector2
contains two BlackboardDouble children. Flags, enum bits and blackboard bytes
stay raw; no coordinates, random choice or navigation result is evaluated.
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

LABEL = 'buffSelectorRandomPoint'
TAG = 16
CONTRACT_PATH = CONTRACTS_DIR / 'buff_selector_random_point_finder_native.json'


def _contract() -> dict[str, Any]:
    c, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-selector-random-point-native-contract.v1', status='exact-current-build', label=LABEL)
    if (set(c.get('records', {})) != {'randomPoint', 'blackboardVector2'}
            or c['dispatcher'].get('unionTag') != TAG
            or c.get('sourceContract') != 'finder_10_native.json'
            or [m['fieldName'] for m in c['records']['randomPoint']['members']] !=
                ['angle', 'extent2D', 'localPlaneRotationEulers', 'minRadius', 'pointNum', 'radius', 'shape', 'snapToNavMesh', 'useExtraJitter']
            or [m['fieldName'] for m in c['records']['blackboardVector2']['members']] != ['x', 'y']
            or any(m['declaredType'] != scalar._contract()['rootContextType']
                for m in c['records']['blackboardVector2']['members'])):
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
        image.owners, source=str(gate.gameassembly), contract_path=source_path)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=_fail)
    dispatch = c['dispatcher']; route = image.validate_dispatcher(dispatch, label=LABEL)
    image.check_instruction_windows([dispatch['typeLoadInstruction']], label=LABEL)
    rva, raw_hex = dispatch['typeLoadInstruction']; raw = bytes.fromhex(raw_hex)
    if (raw[:3] != b'\x48\x8b\x15' or len(raw) != 7
            or image.pe.image_base + rva + 7 + struct.unpack_from('<i', raw, 3)[0] != route['usageCell']):
        _fail('route-type-load', route['usageCell'], dispatch['typeLoadInstruction'])
    registry = selector_native['_registry']; record = c['records']['randomPoint']
    finder = [m for m in registry.plans[selector_native['selectorDefinition']] if m.name == 'finderData' and m.kind == 'union']
    definition = record['wrapperTypeDefinition']
    if (len(finder) != 1 or registry.union_tag_maps.get(finder[0].ref, {}).get(TAG) != definition
            or registry.wrapped_names.get(definition) != record['runtimeTypeName']):
        _fail('selector-parent-route', record['runtimeTypeName'], definition)
    joins = {m['fieldName']: m['declaredType'] for m in record['members']}
    if (joins['extent2D'] != c['records']['blackboardVector2']['runtimeTypeName']
            or joins['localPlaneRotationEulers'] != vectors._contract()['vectorRuntimeTypeName']
            or any(joins[k] != scalar._contract()['rootContextType'] for k in ('angle','minRadius','pointNum','radius'))):
        _fail('typed-blackboard-children', 'independently admitted scalar/vector children', joins)
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
    c = _contract(); proof = context.get('randomPointFinder', {})
    if (proof.get('status') != 'validated' or proof.get('nativeInputs') != c['nativeInputs']
            or proof.get('unionTag') != TAG or proof.get('recordMembers') != _members(c)
            or not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(f'{LABEL}.decode:native-source-or-span')
    for key in ('effectVectors',):
        if (context.get(key, {}).get('status') != 'validated'
                or any(context[key].get('nativeInputs', {}).get(k) != c['nativeInputs'][k]
                    for k in ('GameAssembly.dll','global-metadata.dat'))):
            raise ValueError(f'{LABEL}.decode:shared-child-inputs')
    leaf = context['effectVectors'].get('scalarNative', {})
    if (leaf.get('status') != 'validated' or leaf.get('sourceStoreValidated') is not True
            or leaf.get('selectedReadOrder') != scalar._contract()['selectedReadOrder']):
        raise ValueError(f'{LABEL}.decode:scalar-native-not-validated')
    reader = Reader(data, source, end); reader.pos = start
    args = dict(source=source, logical_sha256=digest)

    def scalar_child(a: int, b: int) -> dict:
        value = scalar.decode_adding_cooldown(data, a, b, native_validation=context['effectVectors']['scalarNative'])
        if value.get('wholeValueExact') is not True:
            raise ValueError(f'{LABEL}.decode:scalar-not-exact')
        return value

    def vector2() -> dict:
        a = reader.pos; fields = []
        if reader.peek() == 255:
            reader.take(1, 'null-vector2'); status = 'exact-null'
        else:
            reader.header(2); status = 'named-vector2-exact-span'
            for member in c['records']['blackboardVector2']['members']:
                at = reader.pos; reader.scalar_payload()
                fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                    'start': at, 'end': reader.pos, 'child': scalar_child(at, reader.pos)})
        return {'start': a, 'end': reader.pos, 'status': status, 'namedFields': fields,
            'recursiveStoredSchemaExact': True}

    tag = reader.nested_union_tag((TAG,), 'random-point-finder'); fields = []
    if tag is None:
        status = 'exact-null-union'
    elif reader.peek() == 255:
        reader.take(1, 'null-finder-wrapper'); status = 'exact-null-wrapper'
    else:
        members = c['records']['randomPoint']['members']; reader.header(len(members))
        status = 'named-finder-exact-span'
        for member in members:
            at = reader.pos; kind = member['kind']; value = {}
            if kind == 'BlackboardDouble':
                reader.scalar_payload(); value['child'] = scalar_child(at, reader.pos)
            elif kind == 'BlackboardVector2':
                value['child'] = vector2()
            elif kind == 'BlackboardVector3':
                reader.vector_payload()
                value['child'] = vectors.decode_blackboard_vector3_value(data, **args, start=at,
                    end=reader.pos, native_validation=context['effectVectors'])
            elif kind in ('byte','scalar32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, member['fieldName']).hex().upper()
            else:
                raise ValueError(f'{LABEL}.decode:unsupported-kind={kind}')
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'], 'kind': kind,
                'start': at, 'end': reader.pos, **value})
    if reader.pos != end:
        raise ValueError(f'{LABEL}.decode:finder-end={reader.pos}; expected={end}')
    return {'source': source, 'logicalSha256': digest.upper(), 'start': start, 'end': end, 'tag': tag,
        'typeName': c['records']['randomPoint']['runtimeTypeName'],
        'status': status, 'namedFields': fields, 'recursiveStoredSchemaExact': True, 'runtimeMeaningExact': False}
