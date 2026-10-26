"""Authenticate the named cast-info callee without selecting a caller class."""
from pathlib import Path
import hashlib
from scripts.common import check_installed_native_inputs
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.body_claims import BodyIndex, check_claim
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.consumer_control import check_consumer_control
from scripts.game_data.il2cpp.skill_cast_fill_program import check_skill_cast_fill_program
from scripts.game_data.memorypack.core import CONTRACTS_DIR
from scripts.game_data.memorypack.buff_selector_validator_identity_consumer import _rows, _method
from scripts.game_data.memorypack import buff_selector_marker_surface as selected_build

CONTRACT_PATH = CONTRACTS_DIR / 'buff_skill_cast_fill_claims.json'
LABEL = 'buffSkillCastFill'


def _validate_image(image, contract):
    index = BodyIndex(image)
    selected = NativeReferenceContext(image, index=index)
    spec = contract['consumer']
    body = index.body(spec['type'], spec['method'])
    method = _method(image, index, body.pointer, body.symbol)
    parameters = [selected.type_name(p.type_index) for p in image.metadata.parameters_for(method)]
    if (bool(method.flags & 0x10) != spec['isStatic'] or parameters != spec['parameterTypes']
            or selected.type_name(method.return_type) != spec['returnType']):
        raise ValueError(LABEL + '.method-signature')
    if (selected.is_value_type(spec['type']) or not selected.is_value_type(spec['returnType'])
            or selected.is_enum(spec['returnType'])):
        raise ValueError(LABEL + '.receiver-reference-return-value-types')
    fields = []
    for declaration in contract['fields']:
        owner, type_name, offset = selected.field(declaration['field'])
        if owner != spec['type'] or type_name != declaration['type']:
            raise ValueError(LABEL + '.declared-field:' + declaration['field'])
        fields.append({'role': declaration['role'], 'field': declaration['field'], 'owner': owner, 'type': type_name, 'offset': offset})
    for claim in contract['bodyClaims']:
        failure = check_claim(index, body, claim)
        if failure:
            raise ValueError(LABEL + '.body-claim:' + str(claim) + ':' + failure)
    rows, ranges = _rows(index, body)
    control = check_consumer_control(rows, entry=body.pointer, owned_ranges=ranges)
    layout, _ = read_reviewed_contract(CONTRACTS_DIR / contract['returnLayoutContract'],
        schema='endfield.buff-selector-validator-identity-claims.v1', status='reviewed', label=LABEL + '.layout')
    info = layout['castInfo']
    if info['type'] != spec['returnType'] or info['boxedObjectHeaderBytes'] != 16 or info['copiedValueBytes'] != 24:
        raise ValueError(LABEL + '.returned-value-shape')
    members = []
    roles = {'skillCastId': 'skillCastId', 'originSkill': 'originSkill', 'nonReturnedAtbCost': 'cost'}
    for member in info['members']:
        owner, type_name, offset = selected.field(info['type'] + '::' + member['name'])
        if owner != info['type'] or type_name != member['type'] or offset - info['boxedObjectHeaderBytes'] != member['inlineOffset']:
            raise ValueError(LABEL + '.returned-member-layout:' + member['name'])
        members.append({'role': roles[member['name']], 'name': member['name'], 'type': type_name,
                        'boxedOffset': offset, 'inlineOffset': member['inlineOffset']})
    if {m['role']: m['type'] for m in members} != {f['role']: f['type'] for f in fields}:
        raise ValueError(LABEL + '.source-return-member-types')
    td = index.types[info['type']]
    if not 0 <= td.index < int(image.registration['typeDefinitionsSizesCount']):
        raise ValueError(LABEL + '.returned-size-index')
    pointer = image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'], 16) + td.index * 8)
    if not pointer:
        raise ValueError(LABEL + '.returned-size-row-missing')
    size_row = image.pe.bytes_at_va(pointer, 16)
    if len(size_row) != 16 or int.from_bytes(size_row[:4], 'little') != info['boxedObjectHeaderBytes'] + info['copiedValueBytes']:
        raise ValueError(LABEL + '.returned-boxed-size')
    calls = {}
    for role, name in (('isPatched', 'IFix.WrappersManagerImpl.IsPatched'),
                       ('getPatch', 'IFix.WrappersManagerImpl.GetPatch'),
                       ('patchWrapper', 'IFix.ILFixDynamicMethodWrapper.__Gen_Wrap_1583')):
        matches = [int(r['text'][5:], 16) for r in rows if r['text'].startswith('call 0x')
                   and name in index.names_of(int(r['text'][5:], 16))]
        if len(matches) != 1:
            raise ValueError(LABEL + '.unique-named-call:' + role)
        calls[role] = matches[0]
    traps = [i for i, row in enumerate(rows) if row['text'] == 'int3']
    if len(traps) != 1 or traps[0] == 0 or not rows[traps[0] - 1]['text'].startswith('call 0x'):
        raise ValueError(LABEL + '.trap-helper-call')
    calls['trapHelper'] = int(rows[traps[0] - 1]['text'][5:], 16)
    flow = check_skill_cast_fill_program(rows, entry=body.pointer, owned_ranges=ranges,
        mapper=image.mapper, specification=contract['returnFlow'],
        source_fields={f['role']: f['offset'] for f in fields}, calls=calls,
        inline_offsets={m['role']: m['inlineOffset'] for m in members}, copied_value_bytes=info['copiedValueBytes'])
    return {'methodIndex': method.index, 'symbol': body.symbol,
        'returnType': spec['returnType'], 'parameterTypes': parameters,
        'fields': fields, 'claimsChecked': len(contract['bodyClaims']),
        'control': {k: v for k, v in control.items() if k not in ('edges', 'frames')},
        'returnMembers': members, 'selectedBoxedSizeBytes': int.from_bytes(size_row[:4], 'little'), 'memberFlow': flow,
        'callerEnvironmentSelected': False, 'returnMemberFlowProved': False,
        'unpatchedReturnMemberFlowProved': True}


def validate_current_native_contract(*, gameassembly: Path | None = None, metadata: Path | None = None):
    contract, _ = read_reviewed_contract(CONTRACT_PATH,
        schema='endfield.buff-skill-cast-fill-claims.v2', status='reviewed', label=LABEL)
    selected = selected_build._contract()
    pins = selected['nativeInputs']
    gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gameassembly, metadata=metadata)
    if gate.status != 'validated':
        return {'status': gate.status, 'detail': gate.detail, 'nativeInputs': pins,
                'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    unity = gate.gameassembly.parent / 'UnityPlayer.dll'
    def unity_matches():
        return unity.is_file() and hashlib.sha256(unity.read_bytes()).hexdigest().upper() == pins['UnityPlayer.dll']
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
                'detail': 'UnityPlayer.dll missing or mismatched', 'nativeInputs': pins,
                'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    image = open_native_image(gate.gameassembly, gate.metadata)
    proof = _validate_image(image, contract)
    after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
        gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        return {'status': after.status, 'detail': after.detail, 'nativeInputs': pins,
                'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    if not unity_matches():
        return {'status': 'mismatched' if unity.is_file() else 'missing',
                'detail': 'UnityPlayer.dll changed during validation', 'nativeInputs': pins,
                'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
    return {'status': 'validated', 'nativeInputs': pins, 'proof': proof,
        'evidenceBoundary': contract['evidenceBoundary'],
        'runtimeExecutionKnown': False, 'wholeRootAdmitted': False}
