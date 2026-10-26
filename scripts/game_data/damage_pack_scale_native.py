"""Authenticate the reviewed damage-pack scale composition on selected inputs.

The algorithm is a conditional disassembly interpretation. Authenticated bytes
and metadata are not a whole-CFG proof, a final HP result or live execution.
"""
from __future__ import annotations

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run python -m scripts.game_data.damage_pack_scale_native')

import argparse
import hashlib
import json
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.protocol import field_defaults, native_enum_members
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.enum64_defaults import native_enum64_members
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.context import method_spec_usage_index, method_spec_record
from scripts.game_data.il2cpp.protocol import runtime_type_name

CONTRACT = CONTRACTS_DIR / 'damage_pack_scale_native.json'
SCHEMA = 'endfield.damage-pack-scale-native-contract.v3'


def validate_method_context(image, row):
    """Check a caller's stored MethodSpec identity, without granting live dispatch."""
    cell = image.pe.image_base + row['usageRva']
    raw = image.pe.bytes_at_va(cell, 8)
    si = method_spec_usage_index(raw, image.registration['methodSpecsCount'],
                                source=str(image.gameassembly), offset=cell)
    at = int(image.registration['methodSpecs'], 16) + si * 12
    record = image.pe.bytes_at_va(at, 12)
    mi, ci, method_inst = method_spec_record(record, len(image.metadata.methods),
        image.registration['genericInstsCount'], source=str(image.gameassembly), offset=at)
    method = image.metadata.methods[mi]
    arguments = []
    for inst_index in (ci, method_inst):
        inst = image.instantiations.resolve(inst_index)
        arguments.append([runtime_type_name(image.pe, image.metadata, a.type_pointer_va)
                          for a in inst.arguments])
    actual = {'usageHex': raw.hex(), 'methodSpecIndex': si, 'recordHex': record.hex(),
              'definition': [mi, image.metadata.type_full_name(image.metadata.types[method.declaring_type]),
                             image.metadata.string(method.name_index)],
              'classArguments': arguments[0], 'methodArguments': arguments[1]}
    expected = {key: row[key] for key in actual}
    return expected, actual


def validate_windows(image, contract):
    failures = []

    def check(name, expected, actual):
        if expected != actual:
            failures.append({'check': name, 'expected': expected, 'actual': actual})

    for name, row in contract['methods'].items():
        try:
            image.validate_method_row([*row[:3], int(row[3], 16)], label=name)
        except (ValueError, RuntimeError, KeyError, IndexError) as exc:
            failures.append({'check': name + ':method', 'expected': row, 'actual': str(exc)})
    for window in contract['codeWindows']:
        raw = image.pe.bytes_at_va(image.pe.image_base + window['rva'], window['byteCount'])
        check(window['name'] + ':bytes', window['sha256'], hashlib.sha256(raw).hexdigest())
    literal = contract['literal']
    raw = image.pe.bytes_at_va(image.pe.image_base + literal['rva'], len(bytes.fromhex(literal['bytesHex'])))
    check('scale-initializer:bytes', literal['bytesHex'], raw.hex())
    context = NativeReferenceContext(image)
    for row in contract.get('methodContexts', []):
        expected, actual = validate_method_context(image, row)
        check(row['name'] + ':method-context', expected, actual)
    for name, signature in contract['methodSignatures'].items():
        method = image.metadata.methods[contract['methods'][name][0]]
        actual = {'returnType': context.type_name(method.return_type),
                  'parameters': [[image.metadata.string(p.name_index), context.type_name(p.type_index)]
                                 for p in image.metadata.parameters_for(method)], 'slot': method.slot}
        check(name + ':signature', signature, actual)
    for owner in contract['valueTypeOwners']:
        check(owner + ':value-type', True, context.is_value_type(owner))
    for field in contract['fields']:
        name = field['owner'] + '::' + field['name']
        if field.get('static'):
            owner = context.index.types[field['owner']]
            members = [f for f in image.metadata.fields_for(owner)
                       if image.metadata.string(f.name_index) == field['name']]
            check(name + ':field-count', 1, len(members))
            if len(members) != 1: continue
            member = members[0]
            check(name + ':static', True, bool(context.field_attributes(member.type_index) & 0x10))
            offsets = runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)
            actual = (field['owner'], context.type_name(member.type_index), offsets[field['name']])
        else:
            actual = context.field(name)
        check(name + ':layout', (field['owner'], field['type'], field['metadataOffset']), actual)
    for literal in contract['literals']:
        expected = bytes.fromhex(literal['bytesHex'])
        actual = image.pe.bytes_at_va(image.pe.image_base + literal['rva'], len(expected))
        check(f"literal:{literal['rva']}", expected.hex(), actual.hex())
    defaults = field_defaults(image.metadata)
    for owner, profile in contract['enumMembers'].items():
        if profile['width'] == 64:
            rows = native_enum64_members(image.metadata, defaults, image.pe, image.registration, owner)
        elif profile['width'] == 32:
            rows = native_enum_members(image.metadata, defaults, image.pe, image.registration, owner)
        else:
            raise ValueError(f'unsupported enum width: {owner}:{profile["width"]}')
        members = {r['name']: r['id'] for r in rows}
        for name, expected in profile['members'].items():
            check(owner + '.' + name, expected, members.get(name))
    special = contract['specialDamageType']
    members = native_enum_members(image.metadata, field_defaults(image.metadata), image.pe,
                                  image.registration, special['type'])
    check('special-damage-type', special['value'], {r['name']: r['id'] for r in members}.get(special['member']))
    return failures


def load_damage_pack_scale(*, gameassembly=None, metadata=None):
    contract, _ = read_reviewed_contract(CONTRACT, schema=SCHEMA, status='reviewed', label='damagePackScale')
    pins = contract['nativeInputs']
    gate = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
                                         gameassembly=gameassembly, metadata=metadata)
    result = {'schema': 'endfield.damage-pack-scale-native-audit.v3', 'status': gate.status,
              'detail': gate.detail, 'contract': CONTRACT.as_posix(), 'nativeInputs': pins,
              'failures': [], 'interpretation': {}, 'rules': {}, 'evidenceBoundary': contract['evidenceBoundary'],
              'liveExecutionObserved': False, 'finalHpLossProved': False}
    if gate.status != 'validated': return result
    try:
        failures = validate_windows(open_native_image(gate.gameassembly, gate.metadata), contract)
    except (ValueError, RuntimeError, KeyError, IndexError) as exc:
        failures = [{'check': 'native-validation', 'actual': str(exc)}]
    after = check_installed_native_inputs(pins['gameAssemblySha256'], pins['metadataSha256'],
                                          gameassembly=gate.gameassembly, metadata=gate.metadata)
    if after.status != 'validated':
        result.update(status=after.status, detail=after.detail)
        failures.append({'check': 'native-inputs-after', 'expected': pins, 'actual': after.detail})
    elif failures:
        result.update(status='pendingReview', detail=f'{len(failures)} failed check(s)')
    else:
        result['interpretation'] = contract['interpretation']
        result['rules'] = contract['rules']
    result['failures'] = [{**row, 'validator': 'damagePackScale', 'source': CONTRACT.as_posix(),
                           'nativeInputs': pins} for row in failures]
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--gameassembly', type=Path)
    parser.add_argument('--metadata', type=Path)
    parser.add_argument('--export-root', type=Path, help='Optionally project a fresh stored damage-zone definition.')
    parser.add_argument('--game-root', type=Path, help='Required with --export-root: installed Endfield_Data root.')
    parser.add_argument('--zone-config', help='Optional explicit MonoBehaviour document name within Unity.sqlite.')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.zone_config is not None and args.export_root is None:
        parser.error('--zone-config requires --export-root')
    if args.export_root is not None and args.game_root is None:
        parser.error('--export-root requires --game-root for freshness validation')
    from scripts.repo_paths import REPO_ROOT
    target = args.output.resolve()
    if not any(target.is_relative_to(REPO_ROOT / root) for root in ('reports', 'scratch', 'tmp')):
        parser.error('--output must be under reports/, scratch/ or tmp/')
    result = load_damage_pack_scale(gameassembly=args.gameassembly, metadata=args.metadata)
    if result['status'] in ('missing', 'mismatched'):
        print(f"damagePackScale: {result['status']}: {result['detail']}; report left untouched")
        return 1
    if args.export_root is not None and result['status'] == 'validated':
        from scripts.game_data.extraction.verify_export_freshness import build_report, Requirements, DEFAULT_SUMMARY
        from scripts.game_data.damage_zone_config import load_zone_config
        freshness = build_report(game_root=args.game_root, output_root=args.export_root,
                                 summary_path=DEFAULT_SUMMARY, sources=None,
                                 requirements=Requirements(unity=('MonoBehaviour',)))
        result['exportFreshness'] = freshness
        if not freshness.get('fresh'):
            result.update(status='pendingReview', detail='damage-zone export freshness failed',
                          interpretation={}, rules={})
            result['failures'].append({'validator': 'damagePackScale', 'check': 'export-freshness',
                'source': str(args.export_root), 'expected': 'fresh complete MonoBehaviour publication',
                'actual': {k: freshness.get(k) for k in ('error', 'missingOutputs', 'staleOutputs')}})
        else:
            try:
                result['storedZoneConfig'] = load_zone_config(args.export_root, name=args.zone_config)
            except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
                result.update(status='pendingReview', detail=str(exc), interpretation={}, rules={})
                result['failures'].append({'validator': 'damagePackScale', 'check': 'stored-zone-config',
                                          'source': str(args.export_root), 'actual': str(exc)})
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'detail', 'failures')}, ensure_ascii=False))
    return 0 if result['status'] == 'validated' else 1


if __name__ == '__main__':
    raise SystemExit(main())
