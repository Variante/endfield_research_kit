"""Authenticate reviewed original Skill frame conversions on an explicit build.

The pinned windows record reviewed native semantics; this bounded validator
checks declarations, operand bindings and literals without a disassembler or
BodyIndex scan. It does not execute native code or prove iFix/live behavior.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp import protocol
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.repo_paths import REPO_ROOT

CONTRACT_PATH = CONTRACTS_DIR / 'skill_timing_runtime_native.json'
SCHEMA = 'endfield.skill-timing-runtime-native-contract.v2'
AUDIT_SCHEMA = 'endfield.skill-timing-runtime-native-audit.v2'
LABEL = 'skillTimingRuntime'


def _require(condition: bool, check: str, expected, actual) -> None:
    if not condition:
        raise ValueError(f'{check}: expected={str(expected)[:250]}; actual={str(actual)[:250]}')


def _validate_fields(image, fields: list[dict]) -> dict[str, dict]:
    result = {}
    context = NativeReferenceContext(image)
    for row in fields:
        owner = image.named_type_definitions.get(row['type'], ())
        _require(len(owner) == 1, 'field-owner', row['type'], len(owner))
        td = owner[0]
        declarations = [field for field in image.metadata.fields_for(td)
                        if image.metadata.string(field.name_index) == row['name']]
        _require(len(declarations) == 1, 'field-declaration', row['id'], len(declarations))
        actual_type = context.type_name(declarations[0].type_index)
        context.require_ordinary_kind(declarations[0].type_index, row['ordinaryKind'])
        _require(actual_type == row['valueType'], 'field-type', row['valueType'], actual_type)
        offsets = protocol.runtime_type_field_offsets(image.metadata, image.pe, image.registration, td.index)
        actual_offset = offsets.get(row['name'])
        _require(actual_offset == row['offset'], 'field-offset', row['offset'], actual_offset)
        _require(row['id'] not in result, 'duplicate-field', 'unique id', row['id'])
        result[row['id']] = row
    return result


def _validate(image, contract: dict) -> dict:
    methods = {}
    context = NativeReferenceContext(image)
    for row in contract['methods']:
        _require(row['id'] not in methods, 'duplicate-method', 'unique id', row['id'])
        method_index = image.validate_method_row(row['identity'], label=LABEL)
        method = image.metadata.methods[method_index]
        signature = {'returnType': context.type_name(method.return_type),
                     'parameterTypes': [context.type_name(p.type_index)
                                        for p in image.metadata.parameters_for(method)],
                     'isStatic': bool(method.flags & 0x10)}
        expected = {key: row[key] for key in signature}
        _require(signature == expected, 'method-signature', expected, signature)
        methods[row['id']] = row
    windows = contract['codeWindows']
    _require(len(windows) == len(methods) and {w['method'] for w in windows} == set(methods),
             'method-window-coverage', list(methods), [w['method'] for w in windows])
    for window in windows:
        _require(window['startRva'] == methods[window['method']]['identity'][3]
                 and window['endRva'] > window['startRva'], 'method-window-entry',
                 methods[window['method']]['identity'][3], window['startRva'])
    image.check_windows(windows, label=LABEL)
    fields = _validate_fields(image, contract['fields'])

    def read(rva, length):
        return image.pe.bytes_at_va(image.pe.image_base + rva, length)

    def instruction(row, rva_key='rva', hex_key='hex'):
        raw = bytes.fromhex(row[hex_key])
        matching = [w for w in windows if w['method'] == row['method']]
        _require(len(matching) == 1, 'operand-method', row['method'], len(matching))
        window = matching[0]
        rva = row[rva_key]
        _require(window['startRva'] <= rva and rva + len(raw) <= window['endRva'],
                 'operand-window', window['method'], rva)
        actual = read(rva, len(raw))
        _require(actual == raw, 'operand-bytes', raw.hex(), actual.hex())
        return raw

    for row in contract['fieldReads'] + contract['fieldStores']:
        raw = instruction(row)
        offset, size = row['displacementOffset'], row['displacementSize']
        _require(size in (1, 4) and 0 <= offset <= len(raw) - size,
                 'field-displacement-shape', 'bounded signed disp8/disp32', row)
        actual = int.from_bytes(raw[offset:offset + size], 'little', signed=True)
        _require(actual == fields[row['field']]['offset'], 'field-operand', fields[row['field']]['offset'], actual)
        if 'storedByte' in row:
            _require(raw[-1] == row['storedByte'] and fields[row['field']]['ordinaryKind'] == 2,
                     'flag-store', row['storedByte'], raw[-1])
    divisors = []
    for row in contract['float32Divisions']:
        raw = instruction(row, 'instructionRva', 'instructionHex')
        _require(len(raw) == 8 and raw[:3] == bytes.fromhex('f30f5e') and raw[3] & 0xc7 == 5,
                 'float32-division-opcode', 'DIVSS xmm,[RIP+disp32]', raw.hex())
        target = row['instructionRva'] + len(raw) + struct.unpack_from('<i', raw, 4)[0]
        _require(target == row['literalRva'], 'float32-literal-reference', row['literalRva'], target)
        value = read(target, 4)
        _require(value == bytes.fromhex(row['literalHex']), 'float32-literal-bytes', row['literalHex'], value.hex())
        number = struct.unpack('<f', value)[0]
        _require(number == row['float32'], 'float32-literal-value', row['float32'], number)
        divisors.append(number)
    rules = contract['rules']
    _require(divisors and all(value == rules['authoredFramesPerSecond'] for value in divisors),
             'authored-frame-divisor', rules['authoredFramesPerSecond'], divisors)
    _require(rules['originalPathOnly'] is True, 'original-path-boundary', True, rules)
    clamp = contract['durationClamp']
    raw = instruction(clamp)
    # The reviewed contiguous sequence is MOV EAX,imm32; CMP EBX,EAX; CMOVLE EBX,EAX.
    _require(len(raw) == 10 and raw[0] == 0xb8 and raw[5:] == bytes.fromhex('3bd80f4ed8'),
             'duration-clamp-opcode', 'signed maximum with immediate', raw.hex())
    minimum = struct.unpack_from('<i', raw, 1)[0]
    _require(minimum == rules['durationClampMinimumFrames'], 'duration-clamp-minimum',
             rules['durationClampMinimumFrames'], minimum)
    for row in contract['directCalls']:
        raw = instruction(row)
        _require(len(raw) == 5 and raw[0] == 0xe8, 'direct-call-opcode', 'E8 rel32', raw.hex())
        image.validate_method_row(row['target'], label=LABEL)
        target = row['rva'] + 5 + struct.unpack_from('<i', raw, 1)[0]
        _require(target == row['target'][3], 'direct-call-target', row['target'][3], target)
    for fact in contract['facts']:
        _require(fact['method'] in methods, 'fact-method', list(methods), fact['method'])
    cancel_rules = _validate_cancel_rules(contract, fields, instruction, read)
    return {'rules': dict(rules), 'conditionalCancelRules': cancel_rules}



def _validate_cancel_rules(contract, fields, instruction, read) -> dict:
    """Bind the reviewed getter control to typed timer/data/marker operands.

    The complete pinned primary windows own ordinary null/class-init control.
    These operand and branch checks prevent a rule from using an unrelated
    same-offset field, literal, return leaf or call result.
    """
    sources = contract['cancelSources']
    expected_names = {'timerReference': ('Beyond.Gameplay.Core.Skill', 'm_durationTimer', 18),
        'timerElapsed': ('Beyond.Gameplay.PeriodicTimer', 'm_passedTime', 12),
        'dataReference': ('Beyond.Gameplay.Core.Skill', 'm_data', 18),
        'exclusiveFrames': ('Beyond.Gameplay.Core.SkillData', 'exclusiveFrame', 8),
        'interruptMarker': ('Beyond.Gameplay.Core.Skill', 'm_markCanInterrupt', 2),
        'dashMarker': ('Beyond.Gameplay.Core.Skill', 'm_markCanDash', 2)}
    _require(set(sources) == set(expected_names), 'cancel-source-roles', list(expected_names), list(sources))
    bindings = {}
    for role, (owner, name, kind) in expected_names.items():
        field = fields[sources[role]]
        _require((field['type'], field['name'], field['ordinaryKind']) == (owner, name, kind),
                 'cancel-field-binding', (role, owner, name, kind), field)
        matching = [row for row in contract['fieldReads'] if row.get('cancelRole') == role]
        _require(len(matching) == 1 and matching[0]['field'] == sources[role],
                 'cancel-read-binding', (role, sources[role]), matching)
        _require(matching[0]['method'] == ('Skill.get_canDash' if role == 'dashMarker' else 'Skill.get_canInterrupt'),
                 'cancel-read-method', role, matching[0]['method'])
        bindings[role] = matching[0]
    _require(fields[sources['timerReference']]['valueType'] == fields[sources['timerElapsed']]['type']
             and fields[sources['dataReference']]['valueType'] == fields[sources['exclusiveFrames']]['type'],
             'cancel-reference-chain', 'typed timer/data reference to named child owner', sources)
    epsilons = contract['epsilonAdditions']
    _require(len(epsilons) == 1, 'cancel-epsilon-count', 1, len(epsilons))
    epsilon = epsilons[0]
    _require(epsilon['method'] == 'Skill.get_canInterrupt', 'cancel-epsilon-method', 'Skill.get_canInterrupt', epsilon['method'])
    raw = instruction(epsilon, 'rva', 'instructionHex')
    _require(len(raw) == 8 and raw[:4] == bytes.fromhex('f30f5835'),
             'cancel-epsilon-opcode', 'ADDSS xmm6,[RIP+disp32]', raw.hex())
    target = epsilon['rva'] + 8 + struct.unpack_from('<i', raw, 4)[0]
    _require(target == epsilon['literalRva'], 'cancel-epsilon-reference', epsilon['literalRva'], target)
    literal = read(target, 4)
    _require(literal == bytes.fromhex(epsilon['literalHex']), 'cancel-epsilon-bytes', epsilon['literalHex'], literal.hex())
    number = struct.unpack('<f', literal)[0]
    rules = contract['conditionalCancelRules']
    _require(number == epsilon['float32'] == rules['epsilonFloat32'] and literal.hex() == rules['epsilonHex'],
             'cancel-epsilon-value', (epsilon['float32'], epsilon['literalHex']), (number, rules))
    _require(rules['originalPathOnly'] is True and rules['getterOnly'] is True
             and rules['singlePrecision'] is True and rules['completePlayerCancelWindowProved'] is False
             and rules['comparison'] == 'strictGreaterThan', 'cancel-rule-boundary',
             'original Single getter predicate only, strict greater-than', rules)
    _require(rules['receiverChain'] == [sources['timerReference'], sources['timerElapsed']]
             and rules['exclusiveSourceChain'] == [sources['dataReference'], sources['exclusiveFrames']],
             'cancel-rule-source-chain', sources, rules)
    controls = contract['cancelControl']
    _require(len(controls) == 4 and len({row['role'] for row in controls}) == 4,
             'cancel-control-coverage', 'four distinct reviewed control blocks', controls)
    blocks = {row['role']: row for row in controls}
    raw_blocks = {role: instruction(row) for role, row in blocks.items()}
    compare = raw_blocks['thresholdCompare']
    _require(len(compare) == 10 and compare[:8] == bytes.fromhex('0f2ffe0f28742430') and compare[8] == 0x77,
             'cancel-compare-control', 'COMISS elapsed,threshold; restore; JA true', compare.hex())
    true_return = blocks['thresholdTrueReturn']
    branch_target = blocks['thresholdCompare']['rva'] + len(compare) + int.from_bytes(compare[9:], 'little', signed=True)
    _require(branch_target == true_return['rva'] and epsilon['rva'] + 8 == blocks['thresholdCompare']['rva'],
             'cancel-threshold-control-target', true_return['rva'], branch_target)
    _require(raw_blocks['thresholdTrueReturn'] == bytes.fromhex('0f287c2420b0014883c4405bc3'),
             'cancel-true-return', 'restore; return Boolean true', raw_blocks['thresholdTrueReturn'].hex())
    marker = raw_blocks['interruptMarkerReturn']
    marker_read = bindings['interruptMarker']
    _require(blocks['interruptMarkerReturn']['rva'] == marker_read['rva']
             and marker == bytes.fromhex(marker_read['hex']) + bytes.fromhex('0f287c24204883c4405bc3')
             and blocks['thresholdCompare']['rva'] + len(compare) == marker_read['rva'],
             'cancel-marker-return', 'fallthrough returns full named marker byte', marker.hex())
    dash = raw_blocks['dashFallback']
    dash_read = bindings['dashMarker']
    _require(len(dash) == 18 and dash[:6] == bytes.fromhex('84c0b0017506')
             and dash[6:12] == bytes.fromhex(dash_read['hex']) and dash[12:] == bytes.fromhex('4883c4205bc3')
             and blocks['dashFallback']['rva'] + 6 == dash_read['rva'],
             'cancel-dash-result', 'true call result returns true; false returns named dash marker', dash.hex())
    calls = [row for row in contract['directCalls'] if row['method'] == 'Skill.get_canDash']
    _require(len(calls) == 1 and calls[0]['target'][1:3] == ['Beyond.Gameplay.Core.Skill', 'get_canInterrupt']
             and calls[0]['rva'] + 5 == blocks['dashFallback']['rva'],
             'cancel-dash-call-result', 'owned named getter call immediately before result test', calls)
    return dict(rules)


def load_skill_timing_runtime(contract_path: Path = CONTRACT_PATH, *,
                              gameassembly: Path | None = None, metadata: Path | None = None) -> dict:
    path = Path(contract_path)
    audit = {'schema': AUDIT_SCHEMA, 'status': 'validation_failed', 'rows': [], 'rules': {},
             'nativeInputs': {}, 'conditionalCancelRules': {}, 'failures': [], 'contract': str(path)}
    try:
        contract, digest = read_reviewed_contract(path, schema=SCHEMA, status='reviewed', label=LABEL)
        audit.update(contractSha256=digest, evidenceBoundary=contract['evidenceBoundary'])
        pins = contract['nativeInputs']
        gate = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                             gameassembly=gameassembly, metadata=metadata)
        audit.update(status=gate.status, detail=gate.detail)
        if gate.status != 'validated':
            return audit
        image = open_native_image(gate.gameassembly, gate.metadata)
        validated = _validate(image, contract)
        rules = validated['rules']
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                              gameassembly=gate.gameassembly, metadata=gate.metadata)
        _require(after.status == 'validated', 'native-inputs-after', 'validated', after.detail)
        _require(hashlib.sha256(path.read_bytes()).hexdigest().upper() == digest,
                 'contract-after', 'unchanged during validation', 'contract changed')
        rows = []
        for fact in contract['facts']:
            row = dict(fact)
            if 'conversion' in fact:
                row['authoredFramesPerSecond'] = rules['authoredFramesPerSecond']
                if fact['id'] == 'duration':
                    row['durationClampMinimumFrames'] = rules['durationClampMinimumFrames']
            if fact['id'] in ('conditionalCanInterruptGetter', 'conditionalCanDashGetter'):
                row.update({key: validated['conditionalCancelRules'][key]
                            for key in ('epsilonFloat32', 'epsilonHex', 'originalPathOnly', 'getterOnly')})
            if fact['id'] == 'conditionalCanInterruptGetter':
                row['conditionalCancelRules'] = dict(validated['conditionalCancelRules'])
            elif fact['id'] == 'conditionalCanDashGetter':
                row['canDash'] = validated['conditionalCancelRules']['canDash']
            rows.append(row)
        audit.update(status='validated', detail='', rows=rows, rules=rules,
                     conditionalCancelRules=validated['conditionalCancelRules'],
                     nativeInputs={name: pins[name] for name in ('GameAssembly.dll', 'global-metadata.dat')})
    except (OSError, ValueError, KeyError, IndexError, TypeError, RuntimeError, struct.error) as error:
        audit.update(status='validation_failed', detail=str(error)[:800], rows=[], rules={}, conditionalCancelRules={}, nativeInputs={})
        audit['failures'].append({'validator': LABEL, 'check': str(error).split(':', 1)[0][:120],
                                  'source': str(path), 'detail': str(error)[:800]})
    return audit


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, default=CONTRACT_PATH)
    parser.add_argument('--gameassembly', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args(argv)
    if args.output and not any(args.output.resolve().is_relative_to(REPO_ROOT / root)
                               for root in ('reports', 'scratch', 'tmp')):
        parser.error('--output must be under reports/, scratch/ or tmp/')
    audit = load_skill_timing_runtime(args.contract, gameassembly=args.gameassembly, metadata=args.metadata)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: audit[key] for key in ('status', 'detail', 'rules', 'failures')}, indent=2))
    return 0 if audit['status'] == 'validated' else 1


if __name__ == '__main__':
    raise SystemExit(main())
