"""SelfRotateAction stored fields with independently owned UTF8/target/direction children."""
import hashlib
import json
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.context_audit_memorypack import buff_action_read_order
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_actions import Reader, SEQUENCE_RECURSION_LIMIT
from scripts.game_data.memorypack.action_dispatcher import load_action_routes
from scripts.game_data.memorypack import named_native_records as named
from scripts.game_data.memorypack import utf8_source_helper as strings
from scripts.game_data.memorypack import buff_direction_target_children as direction_children
from scripts.game_data.memorypack.getter_direct_action_sources import validate_getter_direct_outputs

LABEL = 'buffSelfRotateAction'
TAG = 324
CONTRACT_PATH = CONTRACTS_DIR/'buff_self_rotate_action_native.json'


def _contract():
    contract, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-self-rotate-action-native-contract.v1', status='exact-current-build', label=LABEL)
    if set(contract['records']) != {'selfRotateAction'} or contract['actionDispatch'] != {'324': 'selfRotateAction'}:
        raise ValueError(LABEL+'.contract-shape')
    record = contract['records']['selfRotateAction']
    if len(record['members']) != 18 or record['inheritedMemberCount'] != 4 or record['sourceReadOrder'] != 'member18':
        raise ValueError(LABEL+'.member-shape')
    for member in record['members']:
        if member['kind'] in contract['childTypes'] and (member['declaredType'] != contract['childTypes'][member['kind']]
                or member.get('sourceContextInstructionRva') is None):
            raise ValueError(LABEL+'.typed-child:'+member['fieldName'])
    return contract


def supported_tags(): return frozenset((TAG,))
def _members(c): return {k: [{'fieldName': m['fieldName'], 'kind': m['kind']} for m in r['members']] for k, r in c['records'].items()}


def _children(contract, children):
    for role in ('target', 'direction', 'directionTargets', 'sourceString'):
        child = children.get(role, {})
        if child.get('status') != 'validated' or child.get('nativeInputs') != contract['nativeInputs']:
            raise ValueError(LABEL+'.independent-child:'+role)
    string_contract = strings._contract()
    string_native = children['sourceString']
    if (string_native.get('sourceHelpers') != string_contract['sourceHelpers']
            or string_native.get('wireEncoding') != string_contract['wireEncoding']
            or contract['stringSourceContract'] != strings.CONTRACT_PATH.name):
        raise ValueError(LABEL+'.independent-string-source')
    if children['directionTargets'].get('targetMembers') != ['source', 'target']:
        raise ValueError(LABEL+'.direction-target-join')


def validate_current_native_contract(*, children, gameassembly: Path | None = None, metadata: Path | None = None):
    c = _contract(); pins = c['nativeInputs']
    def empty(status, detail): return {'status': status, 'detail': detail, 'nativeInputs': pins, 'recordMembers': {}, 'actionDispatch': {}}
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return empty(gate.status, gate.detail)
    unity = gate.gameassembly.parent/'UnityPlayer.dll'
    def matches(): return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not matches(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll missing or mismatched')
    _children(c, children)
    image = open_native_image(gate.gameassembly, gate.metadata)
    record = c['records']['selfRotateAction']; source_path = CONTRACTS_DIR/record['sourceContract']
    source = json.loads(source_path.read_bytes())
    buff_action_read_order(image.pe, image.metadata, image.registration, image.instantiations,
        image.modules, image.owners, source=str(gate.gameassembly), contract_path=source_path)
    source['codeWindows'].extend(c['sourceWindows'])
    def fail(check, expected, actual, **details):
        raise ValueError(LABEL+'.'+check+':'+json.dumps({'source': str(source_path), 'expected': str(expected)[:700], 'actual': str(actual)[:700]}))
    output = validate_getter_direct_outputs(image, source, record, source_string_helpers=children['sourceString']['sourceHelpers'], fail=fail)
    proved = named.validate_named_records(image, source, c['records'], label=LABEL, fail=fail)
    routes, audit = load_action_routes(gameassembly=gate.gameassembly, metadata=gate.metadata); route = routes.get(TAG)
    if (audit['status'] != 'validated' or route is None or route.status != 'resolved'
            or route.wrapper_name != record['wrapperTypeName']
            or list(route.member_order) != [m['fieldName'] for m in record['members']]
            or list(route.member_declared_types) != [m['declaredType'] for m in record['members']]):
        fail('current-route', record['wrapperTypeName'], None if route is None else route.row())
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'], gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated': return empty(after.status, after.detail)
    if not matches(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll changed during validation')
    return {'status': 'validated', 'nativeInputs': pins, 'recordMembers': proved,
        'actionDispatch': c['actionDispatch'], 'outputProof': output, 'runtimeExecutionKnown': False,
        'evidenceBoundary': c['evidenceBoundary']}


def decode_action(data, *, source, digest, start, end, tag, native_validation, target_decoder, depth=0):
    c = _contract(); children = native_validation.get('children', {}); audit = children.get('selfRotateAction', {})
    if (native_validation.get('status') != 'validated' or audit.get('status') != 'validated'
            or native_validation.get('nativeInputs') != c['nativeInputs'] or audit.get('nativeInputs') != c['nativeInputs']
            or audit.get('recordMembers') != _members(c) or audit.get('actionDispatch') != c['actionDispatch']
            or type(tag) is not int or tag != TAG or not isinstance(data, bytes) or not source
            or not isinstance(digest, str) or hashlib.sha256(data).hexdigest().upper() != digest.upper()
            or type(start) is not int or type(end) is not int or not 0 <= start < end <= len(data)):
        raise ValueError(LABEL+'.decode:native-source-or-span')
    if type(depth) is not int or not 0 <= depth <= SEQUENCE_RECURSION_LIMIT:
        raise ValueError(LABEL+'.decode:depth-limit')
    _children(c, children)
    reader = Reader(data, source, end); reader.pos = start
    if reader.nested_union_tag((TAG,), 'self-rotate-action') != TAG: raise ValueError(LABEL+'.physical-tag')
    fields = []; record = c['records']['selfRotateAction']; is_null = reader.peek() == 255
    if is_null: reader.take(1, 'null-self-rotate-wrapper')
    else:
        reader.header(len(record['members']))
        for member in record['members']:
            begin = reader.pos; kind = member['kind']; value = {}
            if kind in ('byte', 'scalar32', 'raw-float32'):
                value['rawHex'] = reader.take(1 if kind == 'byte' else 4, member['fieldName']).hex().upper()
            elif kind == 'byte-payload':
                reader.byte_payload()
                child = strings.decode_source_string(data, source=source, digest=digest,
                    start=begin, end=reader.pos, source_helper_rva=member['sourceCall']['targetRva'],
                    native_validation=children['sourceString'])
                value['child'] = {**child, 'recursiveStoredSchemaExact': child.get('wholeStoredSpanExact') is True}
            elif kind == 'target-profile':
                reader.target_profile(); span = {'start': begin, 'end': reader.pos, 'fieldName': member['fieldName']}
                value['child'] = ({**span, 'status': 'exact-null', 'recursiveStoredSchemaExact': True}
                    if data[begin:reader.pos] == b'\xff' else target_decoder(data, source, digest, span, children, depth=depth+1))
            elif kind == 'direction-profile':
                reader.direction_profile()
                value['child'] = direction_children.decode_direction(data, source=source, digest=digest,
                    start=begin, end=reader.pos, children=children, target_decoder=target_decoder, depth=depth+1)
            else: raise ValueError(LABEL+'.unsupported-kind:'+kind)
            if 'child' in value and (value['child'].get('recursiveStoredSchemaExact') is not True
                    or [value['child'].get('start'), value['child'].get('end')] != [begin, reader.pos]):
                raise ValueError(LABEL+'.child-span:'+member['fieldName'])
            fields.append({'fieldName': member['fieldName'], 'declaredType': member['declaredType'],
                'kind': kind, 'start': begin, 'end': reader.pos, **value})
    if reader.pos != end: raise ValueError(LABEL+'.required-action-end')
    return {'schema': 'endfield.buff-self-rotate-action-receipt.v1', 'source': source,
        'logicalSha256': digest.upper(), 'tag': tag, 'typeName': record['runtimeTypeName'],
        'start': start, 'end': end, 'namedFields': fields, 'isNull': is_null,
        'recursiveStoredSchemaExact': True, 'wholeBuffDataExact': False, 'runtimeExecutionKnown': False}
