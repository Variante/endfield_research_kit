"""Authenticate bounded request-consumption and ordinary cast-dispatch facts.

The request tick and normal-attack entry are separate paths. In particular this
gate does not claim a cached request has an authenticated caller to TryCastSkill.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, native_validation_failure
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.memorypack.pooled_source_helper import check_unity_input

SCHEMA = 'endfield.skill-cast-dispatch-native-contract.v1'
LABEL = 'skillCastDispatch'
CONTRACT_PATH = CONTRACTS_DIR / 'skill_cast_dispatch_native.json'
METHODS = {'tick': ('ComboController', 'Tick'), 'allow': ('ComboController', '_AllowNextSkill'),
    'normalAttack': ('AbilitySystem', 'TryCastNormalAttack'), 'doCast': ('Skill', 'DoCast'),
    'tryCast': ('AbilitySystem', 'TryCastSkill'), 'nextId': ('ComboController', 'get_nextSkillId'),
    'hasRequest': ('ComboController', 'get_hasNextSkillRequest'), 'firstAttack': ('AbilitySystem', 'get_firstAttack')}
BLOCKS = {'tickRegisters', 'tickZero', 'tickAllow', 'changeHandleTick', 'tickDelta', 'tickExpiry', 'tickClear', 'tickDispose', 'normalDispatch', 'firstSelection',
    'hasRequestRead', 'nextIdRead', 'allowOriginal', 'allowOption', 'interruptAndTarget',
    'switchAndCurrent', 'prepareSelected', 'inlineReset', 'inlineCallbacks', 'trySuccess',
    'tryFailure', 'doCastDurationReset', 'doCastReset', 'doCastExclusiveCallback', 'doCastTimelineStart'}
CALL_ROLES = {
    'tickAllow': [('AbilitySystem+ComboController','_AllowNextSkill')],
    'changeHandleTick': [('AbilitySystem+ChangeSkillHandle','Tick')],
    'tickDispose': [('TargetHandle','Dispose')],
    'normalDispatch': [('AbilitySystem','get_firstAttack'),('AbilitySystem','get_firstAttack'),('AbilitySystem','TryCastSkill')],
    'allowOriginal': [('AbilitySystem','CheckCanInterruptCurSkill')],
    'interruptAndTarget': [('AbilitySystem','CheckCanInterruptCurSkill'),('Skill','CanCastToTarget')],
    'switchAndCurrent': [('Skill+SwitchToAddBuffProcessor','TrySwitchToAddBuff'),('Skill','Interrupt')],
    'prepareSelected': [('Ability','AssignSkillCastInfo'),('Skill','SaveTarget'),('Skill','get_targetHandle'),('AbilitySystem','BeforeCastStart')],
    'inlineReset': [('timer','Reset'),('Skill','get_cooldown'),('multiTimer','ResetOne')],
    'doCastReset': [('multiTimer','ResetOne')],
    'doCastTimelineStart': [('TimelineActionProcessor','CastStart')],
}


def need(check, condition):
    if not condition:
        raise ValueError(LABEL + '.' + check)


def _same_json(actual, expected):
    """JSON value equality without Python's bool/int equivalence."""
    if type(actual) is not type(expected):
        return False
    if isinstance(expected, dict):
        return actual.keys() == expected.keys() and all(_same_json(actual[key], value) for key,value in expected.items())
    if isinstance(expected, list):
        return len(actual) == len(expected) and all(_same_json(left,right) for left,right in zip(actual,expected))
    return actual == expected


def remaining_request_time(remaining_time, all_scaled_time, expiry_threshold):
    """Selected scalar float32 subtraction and Tick's ordered keep predicate.

    This does not model iFix overrides, external mutation or a cast attempt.
    Unordered comparisons (NaN) and results <= the selected constant expire.
    """
    def f32(value):
        try:
            return struct.unpack('<f', struct.pack('<f', value))[0]
        except OverflowError:
            return float('-inf') if value < 0 else float('inf')
    result = f32(f32(remaining_time) - f32(all_scaled_time))
    return result, result > f32(expiry_threshold)


def _scope(fact):
    need('schema-status', fact.get('schema') == SCHEMA and fact.get('status') == 'reviewed')
    rules = fact['rules']
    expected = dict(originalPathOnly=True, tickDispatchesSkill=False, requestToDispatchCallerJoinProved=False,
        firstAttackUsesRequest=False, doCastReturnType='void', tryCastTrueIncludesSwitchToBuff=True,
        expiryComparison='subtractFloat32ThenKeepOnlyIfOrderedGreaterThanSelectedThreshold', tickDeltaParameter='allScaledTime',
        changeHandleDeltaParameter='timeManagerDeltaTime', clearOrder=['disposeRetainedInputTarget', 'zeroWholeNullableRequest'],
        requestExposure='hasValueAndStoredAllowBit', ordinaryTransition=['isCastingSkillStartTrue',
        'interruptPriorSkillUnlessAlreadyForced', 'storeSelectedCurSkill', 'saveTarget', 'beforeCastStart',
        'castStateInitialization', 'isCastingSkillStartFalse', 'returnTrue'])
    need('rules', _same_json(rules, expected))
    need('method-coverage', set(fact['methods']) == set(METHODS))
    need('block-coverage', set(fact['blocks']) == BLOCKS)
    need('fact-coverage', [row['id'] for row in fact['facts']] == ['tickRefreshAndExpiry', 'requestExposure',
        'normalAttackSelection', 'ordinaryTryCastTransition', 'standaloneDoCastWrites'])
    need('fact-boundaries', all(row['evidence'] == 'conditional' and row['description'] for row in fact['facts'])
        and all(fact['evidenceBoundary'].get(key) for key in ('exact', 'conditional', 'unresolved')))


def _validate_blocks(image, fact):
    """Check complete family ownership and gap-free reviewed instruction spans."""
    base = image.pe.image_base
    owned = {}
    for role, method in fact['methods'].items():
        identity = method['identity']
        suffix, name = METHODS[role]
        owner = 'Beyond.Gameplay.Core.' + ('AbilitySystem+ComboController' if suffix == 'ComboController' else suffix)
        need('method-role', identity[1:3] == [owner, name])
        image.validate_method_row(identity, label=LABEL)
        actual = image.metadata.methods[identity[0]]
        context = NativeReferenceContext(image)
        need('method-return', context.type_name(actual.return_type) == method['returnType'])
        need('method-parameters', [dict(name=image.metadata.string(row.name_index), type=context.type_name(row.type_index))
             for row in image.metadata.parameters_for(actual)] == method['parameters'])
        ranges = sorted(tuple(row['runtimeTriple'][:2]) for row in image.unwind_index.family(identity[3])['ranges'])
        declared = sorted((row['startRva'], row['endRva']) for row in fact['codeWindows'] if row['owner'] == role)
        need('complete-method-family', ranges == declared and bool(ranges))
        owned[role] = ranges
    need('window-owner', all(row['owner'] in owned for row in fact['codeWindows']))
    image.check_windows(fact['codeWindows'], label=LABEL)
    instruction_map = {}
    for role, block in fact['blocks'].items():
        need('block-owner', block['owner'] in owned)
        start, end = block['startRva'], block['endRva']
        need('block-owned-range', start < end and any(a <= start < end <= b for a, b in owned[block['owner']]))
        at = start
        for row in block['instructions']:
            raw = bytes.fromhex(row['hex'])
            need('block-contiguous-instructions', row['rva'] == at and 0 < len(raw) <= 15)
            need('instruction-bytes', image.pe.bytes_at_va(base + at, len(raw)) == raw)
            if at in instruction_map:
                need('overlapping-instruction', instruction_map[at] == raw)
            instruction_map[at] = raw
            at += len(raw)
        need('block-complete-end', at == end)
    return instruction_map


def _semantics(fact):
    """Finite opcode witnesses for the reviewed control/data operations.

    Addresses are declarations; none is a build constant in this algorithm.
    Full surrounding family hashes guard all intervening control paths.
    """
    blocks = {key: [bytes.fromhex(row['hex']) for row in value['instructions']]
              for key, value in fact['blocks'].items()}
    def contains(key, *hexes):
        sequence = [bytes.fromhex(value) for value in hexes]
        need('opcode-' + key, sum(blocks[key][at:at + len(sequence)] == sequence
             for at in range(len(blocks[key]) - len(sequence) + 1)) == 1)
    # These finite encodings also bind the actual receiver registers throughout
    # each contiguous span; review strings never participate in validation.
    contains('tickDelta', 'f3410f5cc0', '44884dcc', '0f114de8', '488945d0')
    contains('tickExpiry', '0f2ffe')
    need('ordered-positive-retention', blocks['tickExpiry'][-1][:2] == b'\x0f\x82')
    expiry = fact['blocks']['tickExpiry']['instructions'][-1]
    need('expiry-branch-to-retain', expiry['rva'] + 6 + struct.unpack_from('<i',bytes.fromhex(expiry['hex']),2)[0]
        == fact['blocks']['tickClear']['endRva'])
    contains('tickRegisters', '440f28c1')
    contains('tickRegisters', '440f28ca')
    contains('changeHandleTick', '4533c0', '410f28c9', '488bcb')
    need('zero-whole-request', blocks['tickClear'] == [bytes.fromhex(x) for x in
        ['0f57c0','0f114738','0f114748','0f114758','0f114768','0f114778','0f118788000000','0f118798000000','0f1187a8000000']])
    contains('hasRequestRead', '80793800')
    contains('hasRequestRead', '488b4148', '48c1e820')
    contains('firstSelection', '83b8d800000000')
    contains('firstSelection', 'ffc3', '3bde')
    contains('normalDispatch', '488b90f0000000')
    contains('allowOriginal', '488bd0', '4885c0')
    contains('allowOriginal', '807b3800')
    contains('allowOriginal', '807b5800')
    contains('allowOriginal', '660f73db04', '660f7ed8', '84c0')
    contains('allowOption', '48c1e820')
    contains('switchAndCurrent', '84c0')
    contains('switchAndCurrent', '41c685a002000001')
    contains('switchAndCurrent', '4989bdd8030000')
    contains('inlineReset', '884760', '89b7b0000000', '6689b7b4000000', '89b788000000', '6689b78c000000', '40887761', '48895f58')
    contains('inlineCallbacks', '488b4558', '48894768')
    contains('trySuccess', '41c685a002000000', 'b001')
    need('false-return', blocks['tryFailure'] == [b'\x32\xc0'])
    need('duration-reset', blocks['doCastDurationReset'] == [bytes.fromhex(x) for x in ['8b4110','894114','897918']])
    contains('doCastReset', '884660')
    contains('doCastReset', '89beb0000000', '6689beb4000000', '89be88000000', '6689be8c000000', '40887e61', '4c897e58')
    need('exclusive-callback', blocks['doCastExclusiveCallback'] == [bytes.fromhex('4c896668')])


def _validate(image, fact):
    _scope(fact)
    instructions = _validate_blocks(image, fact)
    _semantics(fact)
    context = NativeReferenceContext(image)
    fields = {}
    for row in fact['fields']:
        key = row['owner'] + '::' + row['name']
        need('field-unique', key not in fields)
        need('typed-field', tuple(context.field(key)) == (row['owner'], row['typeName'], row['offset']))
        fields[key] = row
    # Bind selected opcode displacements to their independently typed fields.
    selected = [('AbilitySystem','m_skills','firstSelection','488b8f',4),
        ('AbilitySystem','m_activeSkillMap','allowOriginal','488b89',4),
        ('AbilitySystem','m_isCastingSkillStart','switchAndCurrent','41c685',4),
        ('AbilitySystem','<curSkill>k__BackingField','switchAndCurrent','4989bd',4),
        ('AbilitySystem+ComboController','m_nextSkillRequest','hasRequestRead','8079',1),
        ('Skill','m_skillId','normalDispatch','488b90',4),
        ('Skill','<skillType>k__BackingField','firstSelection','83b8',4),
        ('Skill','m_finishCode','inlineReset','89b7',4),
        ('Skill','m_appliedCost','inlineReset','8847',1),
        ('Skill','m_onCastEndCallbackOnce','inlineReset','48895f',1),
        ('Skill','m_onExclusiveCallbackOnce','inlineCallbacks','488947',1)]
    # These are finite opcode/receiver forms, not duplicated layout numbers:
    # each displacement is decoded from the checked instruction and compared
    # against the independently authenticated metadata field.
    for owner,name,block,prefix_hex,width in selected:
        prefix=bytes.fromhex(prefix_hex)
        offset=fields['Beyond.Gameplay.Core.'+owner+'::'+name]['offset']
        candidates=[bytes.fromhex(row['hex'])for row in fact['blocks'][block]['instructions']]
        expected_uses=2 if owner=='AbilitySystem'and name=='m_skills'else 1
        need('opcode-field-displacement',sum(raw.startswith(prefix) and len(raw)>=len(prefix)+width
            and int.from_bytes(raw[len(prefix):len(prefix)+width],'little',signed=True)==offset
            for raw in candidates)==expected_uses)
    seen = set()
    for row in fact['calls']:
        site = row['siteRva']; raw = instructions.get(site, b'')
        need('call-unique', site not in seen); seen.add(site)
        block = fact['blocks'][row['block']]
        need('call-block-membership', any(ins['rva'] == site for ins in block['instructions']))
        need('actual-direct-call-target', len(raw) == 5 and raw[0] == 0xe8
             and site + 5 + struct.unpack_from('<i', raw, 1)[0] == row['target'][3])
        image.validate_method_row(row['target'], label=LABEL + '.callee')
        method = image.metadata.methods[row['target'][0]]
        need('callee-signature', context.type_name(method.return_type) == row['returnType']
             and [context.type_name(value.type_index) for value in image.metadata.parameters_for(method)] == row['parameterTypes'])
    required = {'_AllowNextSkill','Dispose','get_firstAttack','TryCastSkill','CheckCanInterruptCurSkill',
        'CanCastToTarget','TrySwitchToAddBuff','Interrupt','AssignSkillCastInfo','SaveTarget','get_targetHandle',
        'BeforeCastStart','Reset','get_cooldown','ResetOne','CastStart','Tick'}
    need('named-call-coverage', {row['target'][2] for row in fact['calls']} == required)
    actual_calls = {}
    for row in fact['calls']:
        actual_calls.setdefault(row['block'], []).append((row['target'][1],row['target'][2]))
    expected_calls = {block: [('Beyond.Gameplay.PeriodicTimer' if owner == 'timer' else
        'Beyond.Gameplay.MultiPeriodicTimer' if owner == 'multiTimer' else 'Beyond.Gameplay.Core.'+owner,name)
        for owner,name in rows] for block,rows in CALL_ROLES.items()}
    need('ordered-call-roles', actual_calls == expected_calls)
    zero = fact['blocks']['tickZero']['instructions'][0]
    raw = bytes.fromhex(zero['hex'])
    need('zero-constant-load', len(raw) == 8 and raw[:4] == b'\xf3\x0f\x10\x3d')
    address = image.pe.image_base + zero['rva'] + 8 + struct.unpack_from('<i',raw,4)[0]
    threshold = fact['tickExpiryThreshold']
    need('threshold-scope', threshold['loadBlock'] == 'tickZero' and threshold['comparison'] == 'orderedGreaterThan')
    bits = bytes.fromhex(threshold['bitsHex'])
    need('expiry-threshold-constant', len(bits) == 4 and image.pe.bytes_at_va(address,4) == bits)
    value = struct.unpack('<f',bits)[0]
    need('finite-positive-expiry-threshold', 0 < value < float('inf'))
    for row in fact['typedRequests']:
        actual = derive_typed_usage_context(image, row['instructionRva'], label=LABEL)
        need('typed-request', actual == row['expected'])
    need('typed-request-coverage', [(row['owner'],row['expected']['typeName'],row['expected']['methodName'])
        for row in fact['typedRequests']] == [('allow','System.Collections.Generic.CollectionExtensions','GetValueOrDefault'),
        ('firstAttack','Beyond.CollectionExtensions','SafeCount'),('firstAttack','System.Collections.Generic.List`1','get_Item')])
    return dict(schema='endfield.skill-cast-dispatch-native-audit.v1', status='validated',
        nativeInputs=fact['nativeInputs'], rules=fact['rules'], facts=fact['facts'],
        evidenceBoundary=fact['evidenceBoundary'], tickExpiryThreshold=dict(threshold, value=value), requestToDispatchCallerJoinProved=False,
        runtimeExecutionProved=False, methodCount=len(fact['methods']), codeWindowCount=len(fact['codeWindows']))


def validate_current_native_contract(*, gameassembly, metadata, contract_path=CONTRACT_PATH):
    path = Path(contract_path)
    try:
        raw = path.read_bytes(); fact = json.loads(raw); _scope(fact); pins = fact['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=Path(gameassembly), metadata=Path(metadata))
        if gate.status != 'validated':
            return dict(status=gate.status, detail=gate.detail, requestToDispatchCallerJoinProved=False)
        if failure := check_unity_input(gate.gameassembly, pins):
            return failure
        result = _validate(open_native_image(gate.gameassembly, gate.metadata), fact)
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
            gameassembly=gate.gameassembly, metadata=gate.metadata)
        if after.status != 'validated':
            return dict(status=after.status, detail=after.detail, requestToDispatchCallerJoinProved=False)
        if failure := check_unity_input(gate.gameassembly, pins):
            return failure
        need('contract-bookend', raw == path.read_bytes())
        return result
    except (ValueError, KeyError, IndexError, TypeError, OSError, RuntimeError) as error:
        return native_validation_failure(error, label=LABEL, source_path=path)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--contract', type=Path, default=CONTRACT_PATH)
    parser.add_argument('--output', type=Path, default=REPO_ROOT/'reports/game_data/skill_cast_dispatch_native.json')
    args = parser.parse_args(argv)
    if not args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()):
        parser.error('--output must be below reports/')
    result = validate_current_native_contract(gameassembly=args.gameassembly, metadata=args.metadata, contract_path=args.contract)
    if result.get('status') == 'validated':
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result.get('status') == 'validated' else 2


if __name__ == '__main__':
    raise SystemExit(main())
