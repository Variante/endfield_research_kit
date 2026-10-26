"""Authenticate the action-source helper and its named caller composition."""
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import Body, BodyIndex
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_reference_origins import check_reference_origins
from scripts.game_data.il2cpp.initializer_control import control_transfer
from scripts.game_data.il2cpp.skill_cast_action_source_program import check_action_source_helper, check_action_source_caller
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build
from scripts.game_data.memorypack import buff_selector_validator_identity_consumer as identity
from scripts.game_data.memorypack import buff_skill_cast_fill_consumer as fill

CONTRACT_PATH = CONTRACTS_DIR / 'buff_skill_cast_action_source_claims.json'
LABEL = 'buffSkillCastActionSource'


def _validate_image(image, contract):
    caller_contract, _ = read_reviewed_contract(CONTRACTS_DIR / contract['callerIdentityContract'],
        schema='endfield.buff-selector-validator-identity-claims.v1', status='reviewed', label=LABEL + '.caller')
    fill_contract, _ = read_reviewed_contract(CONTRACTS_DIR / contract['fillConsumerContract'],
        schema='endfield.buff-skill-cast-fill-claims.v2', status='reviewed', label=LABEL + '.fill')
    caller_proof = identity._validate_image(image, caller_contract)
    fill_proof = fill._validate_image(image, fill_contract)
    if not fill_proof['unpatchedReturnMemberFlowProved']:
        raise ValueError(LABEL + '.fresh-fill-proof-required')
    index = BodyIndex(image); selected = NativeReferenceContext(image, index=index)
    spec = caller_contract['consumer']
    caller = index.body(spec['type'], spec['method'])
    caller_rows, caller_ranges = identity._rows(index, caller)
    method = identity._method(image, index, caller.pointer, caller.symbol)
    parameter = spec['actionParameter']
    params = [p for p in image.metadata.parameters_for(method) if image.metadata.string(p.name_index) == parameter['name']]
    if len(params) != 1 or selected.type_name(params[0].type_index) != parameter['type']:
        raise ValueError(LABEL + '.action-parameter-type')
    location = index.parameter_location(caller.pointer, caller.symbol, parameter['name'])
    if location[0] != 'stack': raise ValueError(LABEL + '.incoming-action-location')
    origins = check_reference_origins(caller_rows, entry=caller.pointer, owned_ranges=caller_ranges,
        incoming_registers={}, incoming_stack_slots={location[1]: 'parameter:abilityAction'},
        selected_call_returns={})['registerOrigins']
    def call_indices(name):
        return [i for i, r in enumerate(caller_rows) if r['text'].startswith('call 0x')
                and name in index.names_of(int(r['text'][5:], 16))]
    fallback_calls = call_indices(caller_contract['calls']['skillCastId']['method'])
    clear_calls = call_indices(caller_contract['calls']['clear']['method'])
    if len(fallback_calls) != 1 or len(clear_calls) != 1:
        raise ValueError(LABEL + '.named-caller-projections')
    fallback_start = int(caller_rows[fallback_calls[0] - 6]['va'], 16)
    fallback_rejoin_site = int(caller_rows[fallback_calls[0] + 2]['va'], 16)
    clear_start = int(caller_rows[clear_calls[0] - 7]['va'], 16)
    action_tests = [i for i, r in enumerate(caller_rows) if r['text'] == 'test rdx, rdx'
                    and i+1 < len(caller_rows) and control_transfer(caller_rows[i+1]).get('target') == fallback_start]
    if len(action_tests) != 1: raise ValueError(LABEL + '.unique-action-test')
    action_index = action_tests[0]; action_test_site = int(caller_rows[action_index]['va'], 16)
    if origins[action_test_site]['rdx'] != ['parameter:abilityAction']:
        raise ValueError(LABEL + '.incoming-action-reference-origin')
    call = caller_rows[action_index + 3]
    if not call['text'].startswith('call 0x'): raise ValueError(LABEL + '.actual-helper-call')
    helper_pointer = int(call['text'][5:], 16)
    helper = Body('<action-source-helper>', helper_pointer, index._extent(helper_pointer), '', [])
    helper.rows = index._decode(helper.pointer, helper.size)
    helper_rows, helper_ranges = identity._rows(index, helper)
    field = contract['actionEnvironment']
    owner, type_name, offset = selected.field(field['field'])
    if owner != parameter['type'] or type_name != field['type'] or selected.is_value_type(owner):
        raise ValueError(LABEL + '.action-environment-field')
    calls = {}
    for role, name in contract['namedCalls'].items():
        matches = [int(r['text'][5:], 16) for r in helper_rows if r['text'].startswith('call 0x')
                   and name in index.names_of(int(r['text'][5:], 16))]
        if len(matches) != 1: raise ValueError(LABEL + '.unique-helper-call:' + role)
        calls[role] = matches[0]
    fill_body = index.body(fill_contract['consumer']['type'], fill_contract['consumer']['method'])
    if calls['fill'] != fill_body.pointer: raise ValueError(LABEL + '.actual-fill-child-pointer')
    traps = [i for i, row in enumerate(helper_rows) if row['text'] == 'int3']
    if len(traps) != 2 or any(i == 0 or not helper_rows[i-1]['text'].startswith('call 0x') for i in traps):
        raise ValueError(LABEL + '.two-checked-trap-call-sites')
    trap_targets = {int(helper_rows[i-1]['text'][5:], 16) for i in traps}
    if len(trap_targets) != 1: raise ValueError(LABEL + '.shared-trap-helper-target')
    calls['trapHelper'] = next(iter(trap_targets))
    remainder = [int(r['text'][5:], 16) for r in helper_rows if r['text'].startswith('call 0x')
                 and int(r['text'][5:], 16) not in set(calls.values())]
    if len(remainder) != 1: raise ValueError(LABEL + '.one-opaque-fallback-call')
    calls['fallbackHelper'] = remainder[0]
    helper_proof = check_action_source_helper(helper_rows, entry=helper.pointer, owned_ranges=helper_ranges,
        mapper=image.mapper, contract=contract, environment_offset=offset, calls=calls)
    projection = check_action_source_caller(caller_rows, entry=caller.pointer, owned_ranges=caller_ranges,
        mapper=image.mapper, action_test_site=action_test_site, helper_pointer=helper_pointer,
        fallback_start=fallback_start, fallback_rejoin_site=fallback_rejoin_site, clear_start=clear_start)
    return {'callerMethodIndex': method.index, 'helperPointer': helper_pointer,
        'actionEnvironment': {'field': field['field'], 'type': type_name, 'offset': offset},
        'freshCallerIdentityProof': caller_proof, 'freshFillConsumerProof': fill_proof,
        'helper': helper_proof, 'callerProjection': projection,
        'zeroHelperCasesSelectCallerClearPath': True, 'clearExecutionKnown': False,
        'selectedEnvironmentClassKnown': False, 'runtimeExecutionKnown': False}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-skill-cast-action-source-claims.v1', status='reviewed', label=LABEL)
    pins = selected_build._contract()['nativeInputs']
    def empty(status, detail):
        return {'status': status, 'detail': detail, 'nativeInputs': pins,
                'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated': return empty(gate.status, gate.detail)
    unity = gate.gameassembly.parent / 'UnityPlayer.dll'
    def matched():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not matched(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll missing or mismatched')
    proof = _validate_image(open_native_image(gate.gameassembly, gate.metadata), contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated': return empty(after.status, after.detail)
    if not matched(): return empty('mismatched' if unity.is_file() else 'missing', 'UnityPlayer.dll changed during validation')
    return {'status': 'validated', 'nativeInputs': pins, 'proof': proof,
            'evidenceBoundary': contract['evidenceBoundary'], 'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
