"""Source-bound complete SubSpeed null/member-five stored records.

Default formatter bindings and buffered normal source paths are conditional.
Stored bytes do not establish live provider choice or accumulated object state.
"""
from __future__ import annotations

import argparse
import ast
import datetime
import hashlib
import json
import struct
from pathlib import Path
from typing import Any
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.corpus_gate import CensusGateError, _fingerprint, _package_import_closure
from scripts.game_data.memorypack.buff_actions import Reader
from scripts.game_data.memorypack import buff_move_to_subspeed_source as source_owner
from scripts.game_data.memorypack import buff_move_to_lifecycle as lifecycle
from scripts.game_data.memorypack import buff_move_to_original_adapters as adapters
from scripts.game_data.memorypack import buff_blackboard_double_data as doubles
from scripts.game_data.memorypack import buff_adding_cooldown as scalar
from scripts.game_data.memorypack import animation_curve as curves
from scripts.game_data.memorypack import utf8_source_helper as strings

LABEL = 'buffMoveToSubSpeed'
SCHEMA = 'endfield.buff-move-to-subspeed-stored-receipt.v1'
CONTRACT_PATH = source_owner.CONTRACT_PATH
FIELD_PROFILE = (('fixedSpeed', 'scalar-payload'), ('rootMotionAnimKey', 'byte-payload'),
                 ('rootMotionScale', 'scalar-payload'), ('speedCurve', 'curve'), ('speedType', 'scalar32'))
DOUBLE_TYPE = 'Beyond.Blackboard+BlackboardDouble'


def _fail(check: str, expected: Any, actual: Any) -> None:
    error = CensusGateError(f'{LABEL}.{check}', source=CONTRACT_PATH.as_posix(),
                           expected=str(expected)[:1500], actual=str(actual)[:1800])
    error.diagnostic.update(validator=LABEL, check=check)
    error.args = (json.dumps(error.diagnostic, sort_keys=True),)
    raise error


def _record() -> tuple[dict, dict]:
    c = source_owner._contract()
    record = c['records']['subSpeed']
    if tuple((m['fieldName'], m['kind']) for m in record['members']) != FIELD_PROFILE:
        _fail('source-field-profile', FIELD_PROFILE, record['members'])
    return c, record


def _proof_paths() -> set[Path]:
    """Collect source closure and recursively referenced reviewed declarations."""
    sources = set(_package_import_closure(Path(__file__))) | {Path(__file__), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH}
    pending = {CONTRACT_PATH}
    for path in sources:
        if path.suffix != '.py':
            continue
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                name = node.value
                if name.endswith('.json') and Path(name).name == name and (CONTRACTS_DIR / name).is_file():
                    pending.add(CONTRACTS_DIR / name)
    seen = set()
    def references(value):
        if isinstance(value, dict):
            for child in value.values():
                yield from references(child)
        elif isinstance(value, list):
            for child in value:
                yield from references(child)
        elif isinstance(value, str) and value.endswith('.json') and Path(value).name == value:
            target = CONTRACTS_DIR / value
            if target.is_file():
                yield target
    while pending:
        path = pending.pop()
        if path in seen:
            continue
        seen.add(path)
        pending.update(set(references(json.loads(path.read_bytes()))) - seen)
    return sources | seen


def _curve_native(image: Any, native_inputs: dict) -> dict:
    c = curves._contract()
    if c['nativeInputs'] != native_inputs:
        _fail('curve-build', native_inputs, c['nativeInputs'])
    source = json.loads((CONTRACTS_DIR / c['sourceContract']).read_bytes())
    if source.get('schemaVersion') != 1 or c['sourceMethod'] not in source['methodGroups'][0]['methods']:
        _fail('curve-source-owner', c['sourceMethod'], c['sourceContract'])
    curves._check_curve_copies(image, c)
    return {'status': 'validated', 'nativeInputs': native_inputs,
            **{k: c[k] for k in ('keyframeFields', 'storedMemberCount', 'keyframeBytes', 'evidenceBoundary')}}


def _compose(c: dict, record: dict, components: dict, curve_type: dict) -> dict:
    native = c['nativeInputs']
    for name in ('source', 'lifecycle', 'adapters', 'doubleData', 'curve', 'string'):
        value = components[name]
        if value.get('status') != 'validated' or value.get('nativeInputs') != native:
            _fail('component-build', {'component': name, 'nativeInputs': native}, value.get('status'))
    base = components['scalar']
    if (base.get('status') != 'validated' or base.get('sourceStoreValidated') is not True
            or base.get('selectedReadOrder') != ['blackboardKey', 'useBlackboardKey', 'value']):
        _fail('scalar-source-order', 'validated current three-member stored scalar source', base)
    expected = [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in record['members']]
    if components['source']['recordMembers'] != {'subSpeed': expected}:
        _fail('source-five-members', expected, components['source'].get('recordMembers'))
    header = components['lifecycle']['summary']['records']['subSpeed']['source']
    if (header['memberCount'] != len(record['members']) or not header['currentFieldProgramJoined']
            or not header['nullClearsWrapperReference'] or header['completeNullReturns'] != 1
            or header['completeNormalReturns'] != 2):
        _fail('complete-buffered-wrapper-returns', 'null and new/reused member-five complete returns', header)
    route = components['adapters']['summary']['records']['subSpeed']
    if (route['originalType'] != record['runtimeTypeName'] or route['wrapperType'] != record['wrapperTypeName']
            or not route['staticOriginalAdapterRegistrationProved']
            or not route['getterEntry']['directOutputFieldRead']
            or not route['typedInterfaceLookup']['completeCallerReturnProved']
            or not route['wrapperReaderRoute']['completeCallerFrameRestoredBeforeTail']):
        _fail('complete-default-adapter-route', 'same original/wrapper and concrete direct getter/source route', route)
    members = record['members']
    if ([m['declaredType'] for m in members[:4]] !=
            [DOUBLE_TYPE, 'string', DOUBLE_TYPE, curve_type['typeName']]):
        _fail('typed-child-grammar-join', 'two BlackboardDouble references, string and actual curve formatter type', members)
    if not all(components['doubleData']['sourceTransfer'].get(k) for k in
               ('sourceMatchesActualNamedSetterCells', 'normalBooleanNormalizationProved', 'rawFloat32CopyProved')):
        _fail('closed-double-wire-cells', 'current key/flag/raw Float32 cells', components['doubleData']['sourceTransfer'])
    string_call = members[1]['sourceCall']['targetRva']
    if string_call not in components['string']['sourceHelpers']:
        _fail('actual-string-child-helper', components['string']['sourceHelpers'], string_call)
    return {'memberNames': [m['fieldName'] for m in members],
            'memberKinds': [m['kind'] for m in members], 'declaredTypes': [m['declaredType'] for m in members],
            'stringHelperRva': string_call, 'acceptedStoredHeaders': [255, len(members)],
            'completeSelectedWrapperReturnsProved': True,
            'defaultOriginalWrapperAdapterRouteJoined': True,
            'storedChildGrammarBindingsProved': True,
            'actualSourceCallbackCursorEqualityProved': False,
            'actualProviderSelectionProved': False, 'finalAccumulatedInstanceStateProved': False}


def validate_current_native_contract(*, gameassembly: Path, metadata: Path) -> dict:
    c, record = _record()
    native = c['nativeInputs']
    pair = check_installed_native_inputs(native['GameAssembly.dll'], native['global-metadata.dat'],
                                         gameassembly=gameassembly, metadata=metadata)
    if pair.status != 'validated':
        return {'status': pair.status, 'detail': pair.detail, 'nativeInputs': native}
    unity = Path(pair.gameassembly).parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == native['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing', 'detail': 'UnityPlayer.dll differs', 'nativeInputs': native}
    paths = _proof_paths() | {Path(pair.gameassembly), Path(pair.metadata), unity}
    sources = [_fingerprint(p) for p in sorted(paths)]
    selected = {'gameassembly': pair.gameassembly, 'metadata': pair.metadata}
    components = {'source': source_owner.validate_current_native_contract(**selected),
                  'lifecycle': lifecycle.validate_current_native_contract(**selected),
                  'adapters': adapters.validate_current_native_contract(**selected),
                  'doubleData': doubles.validate_current_native_contract(**selected),
                  'scalar': scalar.validate_current_native_contract(**selected)}
    components['string'] = components['source'].get('physicalStringHelper', {})
    image = open_native_image(pair.gameassembly, pair.metadata)
    components['curve'] = _curve_native(image, native)
    summary = _compose(c, record, components, curves.formatter_curve_type(image))
    for row in sources:
        actual = _fingerprint(Path(row['path']))
        if actual != row:
            _fail('source-drift', row, actual)
    after = check_installed_native_inputs(native['GameAssembly.dll'], native['global-metadata.dat'],
                                          gameassembly=pair.gameassembly, metadata=pair.metadata)
    if after.status != 'validated' or not unity_matches():
        return {'status': after.status if after.status != 'validated' else 'mismatched',
                'detail': 'native inputs changed during SubSpeed composition', 'nativeInputs': native}
    return {'status': 'validated', 'nativeInputs': native, 'proofSources': sources,
            'summary': summary, 'components': components,
            'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False,
            'evidenceBoundary': {'exact': 'Current selected typed source order, null/member-five wrapper returns and default original/wrapper/child declaration joins.',
                'conditional': 'Initialized compatible contexts and default formatter selection, sufficient buffers, typed normal callee returns and selected disabled barriers.',
                'unresolved': 'Actual callback cursor equality, provider/vtable selection, allocation/curve effects, accumulated runtime state, other member variants and enclosing actions/roots.'}}


def _validate_decode(native: dict) -> tuple[dict, dict]:
    c, record = _record()
    s = native.get('summary', {})
    if (native.get('status') != 'validated' or native.get('nativeInputs') != c['nativeInputs']
            or not s.get('storedChildGrammarBindingsProved')
            or not s.get('completeSelectedWrapperReturnsProved')
            or not s.get('defaultOriginalWrapperAdapterRouteJoined')
            or s.get('memberNames') != [m['fieldName'] for m in record['members']]
            or s.get('memberKinds') != [m['kind'] for m in record['members']]
            or s.get('declaredTypes') != [m['declaredType'] for m in record['members']]
            or s.get('acceptedStoredHeaders') != [255, len(record['members'])]):
        _fail('decode-native-bindings', 'current fully composed SubSpeed source and stored child bindings', s)
    return c, record


def decode_subspeed_child(data: bytes, *, source: str, digest: str, start: int, end: int,
                          native_validation: dict) -> dict:
    c, record = _validate_decode(native_validation)
    if (not isinstance(data, bytes) or not source or not isinstance(digest, str)
            or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        _fail('decode-source-or-span', 'authenticated original bytes and bounded nonempty child span', [source, start, end])
    reader = Reader(data, source, end)
    reader.pos = start
    null = reader.peek() == 255
    fields = []
    if null:
        reader.take(1, 'null-subSpeed')
    else:
        reader.header(len(record['members']))
        components = native_validation['components']
        for member in record['members']:
            begin = reader.pos
            kind = member['kind']
            if kind == 'scalar-payload':
                reader.scalar_payload()
                child = doubles.decode_data(data, source=source, digest=digest, child_start=begin, child_end=reader.pos,
                    native_validation=components['doubleData'], scalar_native_validation=components['scalar'])
            elif kind == 'byte-payload':
                reader.byte_payload()
                child = strings.decode_source_string(data, source=source, digest=digest, start=begin, end=reader.pos,
                    source_helper_rva=native_validation['summary']['stringHelperRva'], native_validation=components['string'])
            elif kind == 'curve':
                reader.curve_profile()
                child = curves.decode_curve(data, source=source, digest=digest, start=begin, end=reader.pos,
                    native_validation=components['curve'])
            elif kind == 'scalar32':
                raw = reader.take(4, member['fieldName'])
                child = {'rawBitsHex': raw.hex().upper(), 'wireBytes': len(raw)}
            else:
                _fail('decode-member-kind', 'a proved current child kind', kind)
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                           'kind': kind, 'start': begin, 'end': reader.pos, 'child': child})
    if reader.pos != end:
        _fail('decode-complete-child-end', end, reader.pos)
    result = {'schema': SCHEMA, 'source': source, 'logicalSha256': digest.upper(),
              'start': start, 'end': end, 'null': null, 'headerBytes': 1,
              'memberCount': None if null else len(record['members']), 'namedFields': fields,
              'recursiveStoredSchemaExact': True, 'wholeStoredSpanExact': True,
              'defaultFormatterRouteConditional': True, 'actualSourceCallbackCursorEqualityProved': False,
              'finalAccumulatedInstanceStateProved': False, 'actualProviderSelectionProved': False,
              'wholeActionAdmitted': False, 'wholeRootAdmitted': False, 'runtimeExecutionKnown': False}
    if encode_subspeed_child(result) != data[start:end]:
        _fail('decode-named-reencode', 'exact original child bytes from named nested values', [start, end])
    result['namedFieldReencodeExact'] = True
    return result


def _encode_string(value: str | None) -> bytes:
    if value is None:
        return struct.pack('<i', -1)
    raw = value.encode('utf-8', 'strict')
    return struct.pack('<i', len(raw)) + raw


def _encode_word(raw_hex: str, field: str) -> bytes:
    try:
        raw = bytes.fromhex(raw_hex)
    except (TypeError, ValueError) as error:
        _fail('encode-word', 'exact four-byte raw word', {'field': field, 'error': str(error)})
    if len(raw) != 4:
        _fail('encode-word-width', {'field': field, 'bytes': 4}, len(raw))
    return raw


def encode_subspeed_child(receipt: dict) -> bytes:
    """Rebuild from named nested members, preserving raw Boolean/Float32 words."""
    if receipt.get('schema') != SCHEMA:
        _fail('encode-schema', SCHEMA, receipt.get('schema'))
    if receipt['null']:
        if receipt['namedFields'] or receipt['memberCount'] is not None:
            _fail('encode-null-fields', [], receipt['namedFields'])
        return b'\xff'
    fields = receipt['namedFields']
    if tuple((f['fieldName'], f['kind']) for f in fields) != FIELD_PROFILE or receipt['memberCount'] != len(fields):
        _fail('encode-field-order', FIELD_PROFILE, fields)
    output = bytearray((len(fields),))
    for field in fields:
        child = field['child']
        if field['kind'] == 'scalar-payload':
            if child['childNull']:
                output += b'\xff'
            else:
                members = child['fields']
                if [m['fieldName'] for m in members] != ['blackboardKey', 'useBlackboardKey', 'value']:
                    _fail('encode-double-order', 'key, raw flag and raw Float32 value', members)
                output += b'\x03' + _encode_string(members[0]['storedValue'])
                output += bytes((members[1]['wireRawByte'],)) + _encode_word(members[2]['rawBitsHex'], 'BlackboardDouble.value')
        elif field['kind'] == 'byte-payload':
            output += _encode_string(child['value'])
        elif field['kind'] == 'curve':
            if child['null']:
                output += b'\xff'
            else:
                members = child['namedFields']
                count = child['keyCount']
                if (type(count) is not int or count < -1
                        or [m['fieldName'] for m in members] != ['preWrapMode', 'postWrapMode', 'keys']
                        or len(members[2]['elements']) != max(0, count)):
                    _fail('encode-curve-count', 'two wrap words and exactly the declared nullable key count', count)
                output += b'\x03' + _encode_word(members[0]['rawHex'], 'preWrapMode') + _encode_word(members[1]['rawHex'], 'postWrapMode')
                output += struct.pack('<i', count)
                expected_fields = [m['fieldName'] for m in curves._contract()['keyframeFields']]
                for key in members[2]['elements']:
                    if [m['fieldName'] for m in key['namedFields']] != expected_fields:
                        _fail('encode-keyframe-order', expected_fields, key['namedFields'])
                    for member in key['namedFields']:
                        output += _encode_word(member['rawHex'], member['fieldName'])
        else:
            output += _encode_word(child['rawBitsHex'], field['fieldName'])
    return bytes(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    report = args.report.resolve()
    if not report.is_relative_to(Path(__file__).resolve().parents[3] / 'reports'):
        parser.error('--report must be inside reports')
    result = validate_current_native_contract(gameassembly=args.gameassembly, metadata=args.metadata)
    if result['status'] != 'validated':
        print(json.dumps({'status': result['status'], 'detail': result.get('detail'), 'reportPreserved': report.as_posix()}))
        raise SystemExit(1)
    result.update(schema='endfield.buff-move-to-subspeed-composition-validation.v1',
                  checkedAtUtc=datetime.datetime.now(datetime.timezone.utc).isoformat())
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': result['status'], 'storedMembers': len(result['summary']['memberNames']),
                      'proofSources': len(result['proofSources']), 'report': report.as_posix()}), flush=True)


if __name__ == '__main__':
    main()
