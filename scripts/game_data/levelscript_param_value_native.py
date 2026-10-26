"""Authenticate selected Int32 Param evaluation and conditional constant transfer."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_param_value_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.corpus_common import atomic_write_text
from scripts.game_data.il2cpp.context import generic_method_candidates, method_parameter_owner, method_spec_record
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image
from scripts.game_data.il2cpp.protocol import runtime_type_field_offsets
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data import levelscript_param_types as param_types
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_output_path, _parser_source_snapshots
from scripts.game_data.memorypack.scalar_param_native import need, owned_method_abi, program, program_extent
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-param-value-native.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_param_value_native.json'


def _raw(row):
    return bytes.fromhex(row[1])


def _target(row, prefix):
    raw = _raw(row)
    need('paramValue.branch', 'prefix', prefix, raw[:len(prefix)])
    size = 1 if len(prefix) == 1 and prefix != b'\xe8' else 4
    need('paramValue.branch', 'size', len(prefix) + size, len(raw))
    return row[0] + len(raw) + int.from_bytes(raw[len(prefix):], 'little', signed=True)


def _shape(rows, forms, label):
    need(label, 'instructionCount', len(forms), len(rows))
    for n, (row, form) in enumerate(zip(rows, forms)):
        need(label, 'rvaType', int, type(row[0]))
        if form is not None:
            need(label, f'opcode[{n}]', bytes.fromhex(form), _raw(row))
        if n:
            need(label, f'contiguous[{n}]', rows[n - 1][0] + len(_raw(rows[n - 1])), row[0])


def check_getter_predicate(rows):
    """Both signed-marker equality paths return AL=1; every other DWORD returns 0."""
    _shape(rows, ['837910ff', None, '837910fe', None, '32c0', 'c3', 'b001', 'c3'], 'paramValue.predicate')
    for at in (1, 3):
        need('paramValue.predicate', 'trueDestination', rows[6][0], _target(rows[at], b'\x74'))
    return {'selectedBytes': 18, 'normalPaths': 3, 'trueSelectorBits': ['FFFFFFFF', 'FFFFFFFE'],
            'return': 'ordinary Boolean AL low8', 'storesOrCalls': 0}


def check_value_return(rows, predicate_rva, try_rva):
    forms = ['48895c2410', '48896c2418', '4889742420', '57', '4883ec20',
             '4983793800', '498bd9', '410fb6f0', '8bea', '488bf9', None,
             'c744243000000000', '4885ff', None, '488b4338', '488b5008',
             '48837a2000', None, '488b5338', '488bcf', '488b5208', None,
             '84c0', None, '488b4338', '488d542430', '440fb6c6', '488bcf',
             '4c8b4810', None, '84c0', None, '8b442430', '488b5c2438',
             '488b6c2440', '488b742448', '4883c420', '5f', 'c3', '488bcb',
             None, None, '837f24ff', None, '8bc5', None, 'ff12', None]
    _shape(rows, forms, 'paramValue.caller')
    need('paramValue.caller', 'size', 165, rows[-1][0] + len(_raw(rows[-1])) - rows[0][0])
    edges = {10: (b'\x74', 39), 13: (b'\x74', 44), 17: (b'\x74', 46),
             23: (b'\x75', 42), 31: (b'\x74', 44), 41: (b'\xeb', 11),
             43: (b'\x75', 24), 45: (b'\xeb', 33), 47: (b'\xeb', 18)}
    for at, (opcode, destination) in edges.items():
        need('paramValue.caller', f'destination[{at}]', rows[destination][0], _target(rows[at], opcode))
    need('paramValue.caller', 'actualPredicateCall', predicate_rva, _target(rows[21], b'\xe8'))
    need('paramValue.caller', 'actualTryCall', try_rva, _target(rows[29], b'\xe8'))
    _target(rows[40], b'\xe8')  # Unselected initializer stays opaque.
    paths = []

    def walk(n, path):
        if n in path or len(path) >= 48:
            raise ValueError('paramValue.caller.ownedCFG: cycle or oversized path')
        path = path + [n]
        if n == 38:
            paths.append(path)
        elif n in edges:
            opcode, destination = edges[n]
            if opcode == b'\xeb':
                walk(destination, path)
            else:
                if n not in (10, 17):
                    walk(destination, path)
                walk(n + 1, path)
        else:
            walk(n + 1, path)

    walk(0, [])
    need('paramValue.caller', 'normalPaths', 6, len(paths))
    for path in paths:
        need('paramValue.caller', 'retainedFrame', True,
             all(n in path for n in (0, 1, 2, 3, 4, 8, 9, 11, 33, 34, 35, 36, 37, 38)))
        need('paramValue.caller', 'oneResultSource', True, (32 in path) != (44 in path))
    constant_paths = [path for path in paths if 32 in path and 42 not in path]
    need('paramValue.caller', 'constantPathCount', 1, len(constant_paths))
    return {'normalPaths': 6, 'fallbackPaths': sum(44 in path for path in paths),
            'outputPaths': sum(32 in path for path in paths), 'constantPath': constant_paths[0],
            'localOutputOffset': 48, 'frameDelta': 40, 'return': 'ordinary Int32 EAX bits',
            'initializerAndReadyCallsProved': False}


def check_try_constant(rows):
    forms = ['48895c2418', '4889542410', '56', '57', '4154', '4156', '4157',
             '4881ecd0000000', '498bf9', '450fb6f0', '488bf2', '488bd9',
             '4983793800', None, '33c0', '4889842418010000', '4889842400010000',
             '0f57c0', '0f118424a0000000', '0f118424b0000000', '48898424c0000000',
             '4885db', None, '488b4738', '488b4808', '4883792000', None,
             '837b1000', None, '8b4320', '8906', 'b001', '488b9c2410010000',
             '4881c4d0000000', '415f', '415e', '415c', '5f', '5e', 'c3']
    _shape(rows, forms, 'paramValue.tryConstant')
    end = rows[-1][0] + 1
    need('paramValue.tryConstant', 'size', 159, end - rows[0][0])
    for at, opcode in ((13, b'\x74'), (22, b'\x0f\x84'), (26, b'\x0f\x84'), (28, b'\x0f\x85')):
        target = _target(rows[at], opcode)
        if rows[0][0] <= target < end:
            raise ValueError(f'paramValue.tryConstant.unselectedDestination[{at}]: target falls inside selected prefix')
    return {'selectedBytes': 159, 'normalPaths': 1, 'sourceSlot': 32, 'selectorSlot': 16,
            'frameDelta': 248, 'output': 'same source DWORD bits through original RDX',
            'return': 'AL=1 after output write', 'opaqueCallsOnSelectedPath': 0,
            'otherSelectorBehaviorProved': False}


def check_wrapper_bridge(methods, holder_offset, slots):
    getter = methods['GetValue']['instructions']
    _shape(getter, ['488b41' + bytes((holder_offset,)).hex(), 'c3'], 'paramValue.wrapperGetter')
    for name in ('constValue', 'idRef', 'paramSource'):
        rows = methods['set___' + name + '__']['instructions']
        _shape(rows, ['4883ec28', '488b41' + bytes((holder_offset,)).hex(), '4885c0', None,
                      None, 'cc', '8950' + bytes((slots[name],)).hex(), '4883c428', 'c3'],
               'paramValue.wrapperSetter.' + name)
        need('paramValue.wrapperSetter', 'nonnullDestination', rows[6][0], _target(rows[3], b'\x75'))
        _target(rows[4], b'\xe8')  # Null throw request is outside the selected path.
    need('paramValue.wrapper', 'consumerSlots', {'paramSource': 16, 'constValue': 32, 'idRef': 36}, slots)
    return {'holderOffset': holder_offset, 'slots': slots,
            'boundary': 'Generated typed wrapper setter/read view; compatible runtime receiver remains conditional.'}


def _selected_generic(image, declaration, role, context):
    image.validate_method_row(declaration['definition'], label='paramValue.' + role)
    method = image.metadata.methods[declaration['definition'][0]]
    reg, pe = image.registration, image.pe
    spec_index = declaration['methodSpecIndex']
    if type(spec_index) is not int or not 0 <= spec_index < reg['methodSpecsCount']:
        raise ValueError(f'paramValue.{role}.methodSpecIndex: outside selected table')
    spec_base = int(reg['methodSpecs'], 16)
    spec = method_spec_record(pe.bytes_at_va(spec_base + spec_index * 12, 12), len(image.metadata.methods),
                              reg['genericInstsCount'], source='paramValue.' + role, offset=spec_base + spec_index * 12)
    need('paramValue.' + role, 'methodSpec', declaration['methodSpec'], list(spec))
    need('paramValue.' + role, 'methodDefinition', method.index, spec[0])
    predicate = role == 'getterPredicate'
    need('paramValue.' + role, 'staticFlag', not predicate, bool(method.flags & 16))
    need('paramValue.' + role, 'emptyOtherInstantiation', -1, spec[2 if predicate else 1])
    arguments = image.instantiations.resolve(spec[1 if predicate else 2]).arguments
    need('paramValue.' + role, 'closedArgumentCount', 1, len(arguments))
    param_types.ordinary(pe.bytes_at_va(arguments[0].type_pointer_va, 16), 8, 'paramValue.closedInt32')
    params = image.metadata.parameters_for(method)
    param_types.ordinary(param_types.type_record(image, context, method.return_type), 2 if role != 'value' else 0x1e, 'paramValue.return')
    if predicate:
        need('paramValue.predicate', 'parameters', 0, len(params))
        definition = method.declaring_type
        need('paramValue.predicate', 'owner', param_types.PARAM_TYPE, image.type_name(definition))
    else:
        need('paramValue.' + role, 'parameters', 3, len(params))
        formal_raw = param_types.type_record(image, context, method.return_type if role == 'value' else params[1].type_index)
        param_types.ordinary(formal_raw, 0x1e, 'paramValue.formal', byref=role == 'tryConstant')
        formal = int.from_bytes(formal_raw[:8], 'little')
        owner = method_parameter_owner(image.metadata.buf, formal,
                                       [m.generic_container_index for m in image.metadata.methods], source='paramValue.formal')
        need('paramValue.formal', 'owner', method.index, owner['methodIndex'])
        need('paramValue.formal', 'ordinal', 0, owner['ordinal'])
        need('paramValue.formal', 'arity', 1, struct.unpack_from('<i', bytes.fromhex(owner['containerRawHex']), 4)[0])
        definition = param_types.param_reference(image, param_types.type_record(image, context, params[0].type_index), 0x1e, formal)
        if role == 'value':
            default_raw = param_types.type_record(image, context, params[1].type_index)
            param_types.ordinary(default_raw, 0x1e, 'paramValue.default')
            need('paramValue.default', 'sameFormal', formal, int.from_bytes(default_raw[:8], 'little'))
        param_types.ordinary(param_types.type_record(image, context, params[2].type_index), 2, 'paramValue.flag')
    code = image.mapper.code_registration_summary(pe, image.code_registration)
    table_base = int(reg['genericMethodTable'], 16)
    candidates = generic_method_candidates(pe.bytes_at_va(table_base, reg['genericMethodTableCount'] * 16),
                                           reg['genericMethodTableCount'], reg['methodSpecsCount'], {spec_index},
                                           code['genericMethodPointersCount'], code['invokerPointersCount'],
                                           source='paramValue.' + role, offset=table_base)
    need('paramValue.' + role, 'registrationCandidates', 1, len(candidates))
    pointer = pe.u64_at_va(int(code['genericMethodPointers'], 16) + candidates[0]['indices'][0] * 8)
    need('paramValue.' + role, 'registeredEntry', pe.image_base + declaration['window']['startRva'], pointer)
    return {'methodIndex': method.index, 'methodSpecIndex': spec_index, 'pointerRva': pointer - pe.image_base,
            'parameterDefinition': definition, 'exclusiveManagedBodyOrRuntimeMethodInfoProved': False}


def validate(image, contract):
    context = NativeReferenceContext(image)
    entries = contract['entries']
    need('paramValue', 'roles', {'value', 'getterPredicate', 'tryConstant'}, set(entries))
    selected = {role: _selected_generic(image, declaration, role, context) for role, declaration in entries.items()}
    need('paramValue', 'sameParameterDefinition', 1, len({row['parameterDefinition'] for row in selected.values()}))
    wrapper = contract['wrapper']
    owners = [td for td in image.metadata.types if image.type_name(td.index) == wrapper['type']]
    need('paramValue.wrapper', 'owners', 1, len(owners))
    owner = owners[0]
    need('paramValue.wrapper', 'nongenericOwner', -1, owner.generic_container_index)
    fields = [f for f in image.metadata.fields_for(owner) if image.metadata.string(f.name_index) == wrapper['holder']]
    need('paramValue.wrapper', 'holderFields', 1, len(fields))
    holder = fields[0]
    holder_raw = param_types.type_record(image, context, holder.type_index)
    need('paramValue.wrapper', 'instanceHolder', 0, int.from_bytes(holder_raw[8:10], 'little') & 16)
    definition = param_types.param_reference(image, holder_raw, 8)
    need('paramValue.wrapper', 'sameParameterDefinition', selected['value']['parameterDefinition'], definition)
    need('paramValue.wrapper', 'holderOffset', wrapper['holderOffset'],
         runtime_type_field_offsets(image.metadata, image.pe, image.registration, owner.index)[wrapper['holder']])
    bridge_methods = wrapper['methods']
    need('paramValue.wrapper', 'bridgeMethods', {'GetValue', 'set___constValue__', 'set___idRef__', 'set___paramSource__'}, set(bridge_methods))
    for name, record in bridge_methods.items():
        image.validate_method_row(record['definition'], label='paramValue.wrapper.' + name)
        method = image.metadata.methods[record['definition'][0]]
        pointer = image.method_pointer_va(method)
        need('paramValue.wrapper', 'sameOwner', owner.index, method.declaring_type)
        need('paramValue.wrapper', 'registeredPointer', image.pe.image_base + record['window']['startRva'], pointer)
        result, arguments = ((wrapper['wrappedType'], 21, True), []) if name == 'GetValue' else (('void', 1, False), [('int', 8, False)])
        owned_method_abi(image, context, method.index, owner.index, result, arguments, 'paramValue.wrapper.' + name)
        if name == 'GetValue':
            need('paramValue.wrapper', 'sameClosedReturn', definition, param_types.param_reference(image, param_types.type_record(image, context, method.return_type), 8))
    for declaration in [*entries.values(), *bridge_methods.values()]:
        image.check_windows([declaration['window']], label='paramValue')
        program_extent(declaration['instructions'], declaration['window'], 'paramValue')
        program(image, declaration['instructions'], [None] * len(declaration['instructions']), 'paramValue')
    predicate = check_getter_predicate(entries['getterPredicate']['instructions'])
    caller = check_value_return(entries['value']['instructions'], selected['getterPredicate']['pointerRva'], selected['tryConstant']['pointerRva'])
    constant = check_try_constant(entries['tryConstant']['instructions'])
    bridge = check_wrapper_bridge(bridge_methods, wrapper['holderOffset'], wrapper['slots'])
    return {'selectedEntries': selected, 'getterPredicate': predicate, 'caller': caller, 'constantTransfer': constant,
            'generatedWrapperView': bridge, 'evidenceBoundary': contract['evidenceBoundary'],
            'conditions': ['compatible same non-null parameter reference and stable selected storage',
                           'each anonymous context/descriptor takes initialized and ready branches',
                           'ordinary closed call ABI and retained frame/local conditions',
                           'readable objects and nonaliasing writable caller output slot'],
            'storedCodecIntegrationProved': False, 'runtimeProviderSelectionProved': False}


def validate_param_value_native_contract(*, contract_path=CONTRACT_PATH, gameassembly=None, metadata=None):
    """Explicit pair, source/native gates before and after; failures always empty rows."""
    contract_path = Path(contract_path)
    try:
        raw = contract_path.read_bytes()
        contract = json.loads(raw)
        need('paramValue', 'schema', SCHEMA, contract.get('schema'))
        need('paramValue', 'status', 'reviewed-conditional-current-build', contract.get('status'))
        pins = contract['nativeInputs']
        need('paramValue', 'nativePinScope', {'GameAssembly.dll', 'global-metadata.dat'}, set(pins))
        if gameassembly is None or metadata is None:
            return {'status': 'missing', 'detail': 'paramValue.explicitNativePair: both selected paths required', 'rows': []}
        paths = [Path(__file__), contract_path, NATIVE_MAPPER_PATH, METADATA_HELPER_PATH]
        paths += [Path(row['path']) for row in _parser_source_snapshots(Path(__file__))]
        sources = [_fingerprint(path) for path in sorted({path.resolve() for path in paths}, key=str)]
        before = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                              gameassembly=Path(gameassembly), metadata=Path(metadata))
        if before.status != 'validated':
            return {'status': before.status, 'detail': before.detail, 'rows': []}
        result = validate(open_native_image(before.gameassembly, before.metadata), contract)
        after = check_installed_native_inputs(pins['GameAssembly.dll'], pins['global-metadata.dat'],
                                             gameassembly=before.gameassembly, metadata=before.metadata)
        if after.status != 'validated':
            return {'status': after.status, 'detail': after.detail, 'rows': []}
        need('paramValue', 'sourceUnchanged', sources, [_fingerprint(Path(row['path'])) for row in sources])
        need('paramValue', 'declarationUnchanged', raw, contract_path.read_bytes())
        return {'schema': SCHEMA, 'status': 'validated', 'rows': [result], 'nativeInputs': pins,
                'proofSources': sources, 'nativeBefore': before.status, 'nativeAfter': after.status}
    except (ValueError, KeyError, OSError, IndexError, TypeError, struct.error) as exc:
        return {'status': 'unresolved', 'detail': str(exc)[:1500], 'source': str(contract_path), 'rows': []}


def _check_output(output, protected):
    if not output.resolve().is_relative_to((REPO_ROOT / 'reports').resolve()):
        raise ValueError('paramValue.output: generated report must be under reports/')
    _guard_output_path(output, protected)
    if output.exists():
        need('paramValue.output', 'existingReportSchema', SCHEMA, json.loads(output.read_bytes()).get('schema'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, default=CONTRACT_PATH)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.output is not None:
        try:
            _check_output(args.output, [args.contract, args.gameassembly, args.metadata])
        except (ValueError, OSError, json.JSONDecodeError) as exc:
            print(json.dumps({'status': 'unresolved', 'detail': str(exc)[:1500], 'rows': []}))
            return 2
    result = validate_param_value_native_contract(contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata)
    if args.output is not None and result['status'] == 'validated':
        try:
            _check_output(args.output, [args.contract, args.gameassembly, args.metadata,
                                       *[Path(row['path']) for row in result['proofSources']]])
            need('paramValue.publication', 'sourcesUnchanged', result['proofSources'],
                 [_fingerprint(Path(row['path'])) for row in result['proofSources']])
            atomic_write_text(args.output, json.dumps(result, indent=2) + '\n')
        except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
            result = {'status': 'unresolved', 'detail': str(exc)[:1500], 'rows': []}
    print(json.dumps({'status': result['status'], 'rows': len(result['rows']),
                      **({'detail': result['detail']} if 'detail' in result else {})}, indent=2))
    return 0 if result['status'] == 'validated' else 2


if __name__ == '__main__':
    raise SystemExit(main())
