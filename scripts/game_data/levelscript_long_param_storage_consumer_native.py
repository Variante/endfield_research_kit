"""Compose the selected stored Int64 constant with its named ordinary consumer."""
from __future__ import annotations

import argparse
import json
import os
import struct
import tempfile
from pathlib import Path

if __name__ == '__main__' and not __package__:
    raise SystemExit('Run with python -m scripts.game_data.levelscript_long_param_storage_consumer_native')

from scripts.common import check_installed_native_inputs
from scripts.game_data import levelscript_long_param_native as storage
from scripts.game_data import levelscript_long_param_value_native as consumer
from scripts.game_data import levelscript_param_types as types
from scripts.game_data import levelscript_param_value_bridge as bridge
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.body_claims import BodyIndex
from scripts.game_data.il2cpp.native_image import METADATA_HELPER_PATH, NATIVE_MAPPER_PATH, open_native_image
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.memorypack import utf8_source_helper
from scripts.game_data.memorypack.corpus_gate import _fingerprint, _guard_output_path, _parser_source_snapshots
from scripts.game_data.memorypack.scalar_param_native import need
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.levelscript-long-param-storage-consumer-native-claims.v2'
CONTRACT_PATH = CONTRACTS_DIR / 'levelscript_long_param_storage_consumer_native_claims.json'
DEPENDENCIES = {
    'storage': storage.CONTRACT_PATH,
    'consumer': consumer.CONTRACT_PATH,
    'utf8Source': utf8_source_helper.CONTRACT_PATH,
}
IDENTITY_CONDITIONS = [
    'same selected output-slot wrapper throughout field population, GetValue and consumer use',
    'same compatible holder throughout field population, GetValue and consumer use',
    'constant and selector storage unchanged except for the proved selected field writes',
]


def selected_constant_path(predicate, caller, slots, declarations):
    """Select one actual ready CONST path, after both owning programs passed."""
    label = 'longParamStorageConsumer.selection'
    need(label, 'constDeclaration', 0, declarations['PARAM_SOURCE_CONST']['value'])
    markers = [declarations[name]['value'] for name in ('PARAM_SOURCE_GETTER', 'PARAM_SERVER_GETTER')]
    consumer.predicate_program(predicate, slots, markers)
    # CONST differs from both comparisons: JNE reaches the second CMP, SETE
    # writes AL=0. The caller tests AL, so its idRef guard is bypassed.
    need(label, 'constOutsideGetterMarkers', True, 0 not in markers)
    for at, encoded in ((25, '84c0'), (35, '84c0'), (36, '488b442430'), (44, 'c3')):
        need(label, 'callerOpcode' + str(at), bytes.fromhex(encoded), bridge.raw(caller[at]))
    for at, opcode, target in ((10, b'\x75', 13), (15, b'\x74', 38),
                                (19, b'\x75', 21), (26, b'\x74', 29),
                                (37, b'\x75', 39)):
        need(label, 'callerDestination' + str(at), caller[target][0], bridge.target(caller[at], opcode))
    path = list(range(11)) + list(range(13, 20)) + list(range(21, 27)) + list(range(29, 38)) + list(range(39, 45))
    need(label, 'excludedIdRefAndFallback', False, any(n in path for n in (27, 28, 38)))
    need(label, 'selectedCalls', [24, 34], [n for n in path if bridge.raw(caller[n])[:1] == b'\xe8'])
    return {'predicatePath': [predicate[n][0] for n in (0, 1, 4, 5, 6)],
            'predicateResult': 'AL=0 for stored CONST',
            'callerPath': [caller[n][0] for n in path],
            'tryResult': 'full QWORD output followed by EAX=1',
            'return': 'RAX full64 current selected output',
            'idRefGuardReached': False, 'selectedReadyPathOnly': True}


def join_descriptor(parameter, row, wrapper_definition, parameter_definition, claims):
    """Cross-join facts already authenticated by the two owning validators."""
    label = 'longParamStorageConsumer.join'
    need(label, 'concreteWrapper', wrapper_definition, parameter['typeDefinition'])
    for entry in row['entries'].values():
        need(label, 'concreteParameter', parameter_definition, entry['parameterDefinition'])
    view = row['wrapperView']
    need(label, 'holderOffset', 16, view['holderOffset'])
    for name, index in view['methods'].items():
        need(label, 'sameMethod.' + name, index, parameter['methods'][name]['methodIndex'])
    need(label, 'sameGetterEntry', parameter['methods']['GetValue']['pointerRva'], view['windows'][0]['startRva'])
    fields = parameter['ownedFieldSlots']
    for name, slot in view['slots'].items():
        need(label, 'sameSlot.' + name, slot, fields[name])
    widths = {'constValue': 8, 'idRef': 4, 'paramSource': 4, 'path': 8}
    intervals = {name: [fields[name], fields[name] + width] for name, width in widths.items()}
    for name, interval in intervals.items():
        need(label, 'validSlot.' + name, True, type(interval[0]) is int and interval[0] >= 0)
        for other, target in intervals.items():
            if name < other:
                need(label, 'disjoint.' + name + '.' + other, True,
                     interval[1] <= target[0] or target[1] <= interval[0])
    need(label, 'storedReadOrder', list(widths), [r['name'] for r in parameter['orderedReads']])
    constant = row['provedClaims']['constant']
    need(label, 'constantWidth', 8, constant['outputBytes'])
    need(label, 'constantSourceMember', 'constValue', constant['sourceMember'])
    need(label, 'constantSelectorMember', 'paramSource', constant['selectorMember'])
    need(label, 'constantSelector', 'PARAM_SOURCE_CONST', constant['selectorDeclaration'])
    need(label, 'successByte', 1, constant['successfulBooleanBits'])
    proved = {'sameConcreteWrapperAndParameter': True,
              'sameGetterAndConstSourceSetters': True, 'constantBytes': widths['constValue'],
              'storedSelector': 'PARAM_SOURCE_CONST', 'selectedReadyConsumerPath': 'constant-output',
              'return': 'unchanged Int64 bits', 'identityConditions': IDENTITY_CONDITIONS,
              'runtimeReceiverOrProviderSelectionProved': False}
    need(label, 'evaluatedClaims', proved, claims)
    return {'wrapperDefinition': wrapper_definition, 'parameterDefinition': parameter_definition,
            'fieldIntervals': intervals, 'methodIdentities': view['methods'], 'provedClaims': proved}


def evaluate(image, declaration, stored, result):
    label = 'longParamStorageConsumer'
    need(label, 'storedCodec', 'Param<long>', stored['codecKind'])
    need(label, 'storedWidth', 8, stored['rawSize'])
    need(label, 'consumerRows', 1, len(result['rows']))
    row = result['rows'][0]
    spec = json.loads(consumer.CONTRACT_PATH.read_bytes())['methods']['wrapperView']
    context = NativeReferenceContext(image)
    wrapper = bridge.qualified_owner(image, spec)
    holder = [f for f in image.metadata.fields_for(wrapper) if image.metadata.string(f.name_index) == spec['holder']]
    need(label, 'holderCount', 1, len(holder))
    definition = types.param_reference(image, types.type_record(image, context, holder[0].type_index), 10)
    parameter = json.loads(storage.CONTRACT_PATH.read_bytes())['parameter']
    joined = join_descriptor(parameter, row, wrapper.index, definition, declaration['claims'])
    index = BodyIndex(image)
    predicate = bridge.decode_rows(index, image.pe.image_base + row['entries']['predicate']['pointerRva'], 17)
    begin, end = row['ownedRanges']['value'][:2]
    caller = bridge.decode_rows(index, image.pe.image_base + begin, end - begin)
    selection = selected_constant_path(predicate, caller, row['wrapperView']['slots'], row['declarations'])
    return {**joined, 'selection': selection, 'evidenceBoundary': declaration['evidenceBoundary'],
            'conditions': IDENTITY_CONDITIONS + [
                'selected default stored wrapper and buffered normal sources',
                'ordinary closed ABI and compatible selected MethodInfo/context',
                'selected initialized and ready branches, normal allocator/barrier/UTF8 callees',
                'all conditions retained by the independent storage and consumer proofs'],
            'positiveEnclosingOwnerAdmissionProved': False,
            'runtimeReceiverOrProviderSelectionProved': False}


def proof_sources(contract_path):
    paths = [contract_path, *DEPENDENCIES.values(), NATIVE_MAPPER_PATH, METADATA_HELPER_PATH,
             *[Path(r['path']) for r in _parser_source_snapshots(Path(__file__))]]
    return [_fingerprint(p) for p in sorted({p.resolve() for p in paths}, key=str)]


def validate_storage_consumer_claims(*, contract_path=CONTRACT_PATH, gameassembly=None, metadata=None):
    contract_path = Path(contract_path)
    try:
        raw = contract_path.read_bytes(); declaration = json.loads(raw)
        need('longParamStorageConsumer', 'schema', SCHEMA, declaration.get('schema'))
        need('longParamStorageConsumer', 'status', 'reviewed', declaration.get('status'))
        need('longParamStorageConsumer', 'dependencies', [{'role': k, 'path': p.name} for k, p in DEPENDENCIES.items()], declaration['dependencies'])
        if gameassembly is None or metadata is None:
            return {'status': 'missing', 'rows': [], 'detail': 'longParamStorageConsumer.explicitNativePair: both paths required'}
        pair = {'gameassembly': Path(gameassembly), 'metadata': Path(metadata)}
        paths = [pair['gameassembly'], pair['metadata'], pair['gameassembly'].parent / 'UnityPlayer.dll']
        if not all(p.is_file() for p in paths):
            return {'status': 'missing', 'rows': [], 'detail': 'longParamStorageConsumer.nativeInputs: selected GA/MD/Unity file missing'}
        native = [_fingerprint(p) for p in paths]; sources = proof_sources(contract_path)
        need('longParamStorageConsumer', 'parsedDeclarationUnchanged', raw, contract_path.read_bytes())
        before = check_installed_native_inputs(native[0]['sha256'], native[1]['sha256'], **pair)
        if before.status != 'validated':
            return {'status': before.status, 'rows': [], 'detail': before.detail}
        stored = storage.validate_long_param_native_contract(gameassembly=before.gameassembly, metadata=before.metadata)
        if stored['status'] != 'validated':
            return {'status': stored['status'], 'rows': [], 'detail': 'storage: ' + str(stored.get('detail', 'refused'))[:1300]}
        result = consumer.validate_long_param_value_claims(gameassembly=before.gameassembly, metadata=before.metadata)
        if result['status'] != 'validated':
            return {'status': result['status'], 'rows': [], 'detail': 'consumer: ' + str(result.get('detail', 'refused'))[:1300]}
        row = evaluate(open_native_image(before.gameassembly, before.metadata), declaration, stored, result)
        after = check_installed_native_inputs(native[0]['sha256'], native[1]['sha256'], **pair)
        if after.status != 'validated':
            return {'status': after.status, 'rows': [], 'detail': after.detail}
        need('longParamStorageConsumer', 'nativeUnchanged', native, [_fingerprint(p) for p in paths])
        need('longParamStorageConsumer', 'sourcesUnchanged', sources, proof_sources(contract_path))
        return {'schema': SCHEMA, 'status': 'validated', 'rows': [row], 'proofSources': sources,
                'nativeInputs': native, 'nativeBefore': before.status, 'nativeAfter': after.status}
    except (ValueError, KeyError, OSError, TypeError, IndexError, StopIteration, struct.error) as exc:
        return {'status': 'pendingReview', 'rows': [], 'source': str(contract_path), 'detail': str(exc)[:1500]}


def check_output(output, protected):
    root = (REPO_ROOT / 'reports').resolve()
    target = output.resolve()
    if not root.is_relative_to(REPO_ROOT.resolve()) or target == root or not target.is_relative_to(root):
        raise ValueError('longParamStorageConsumer.output: report must be under reports/')
    _guard_output_path(output, protected)
    if output.exists():
        need('longParamStorageConsumer.output', 'owner', SCHEMA, json.loads(output.read_bytes()).get('schema'))


def publish_result(output, result, contract_path, protected):
    inputs = protected + [Path(r['path']) for r in result['proofSources']]
    check_output(output, inputs)
    output.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.long-param-composition-', suffix='.tmp', dir=output.parent)
    staged = Path(temporary)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            json.dump(result, handle, indent=2)
            handle.write('\n')
        current_sources = proof_sources(contract_path)
        need('longParamStorageConsumer.publication', 'sourcesUnchanged', result['proofSources'], current_sources)
        need('longParamStorageConsumer.publication', 'nativeUnchanged', result['nativeInputs'],
             [_fingerprint(Path(r['path'])) for r in result['nativeInputs']])
        # Re-resolve after staging and the potentially slow freshness reads.
        inputs += [Path(r['path']) for r in current_sources]
        check_output(staged, inputs)
        check_output(output, inputs)
        os.replace(staged, output)
    finally:
        if staged.exists():
            staged.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--contract', type=Path, default=CONTRACT_PATH)
    parser.add_argument('--gameassembly', type=Path, required=True)
    parser.add_argument('--metadata', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    try:
        protected = [args.contract, args.gameassembly, args.metadata, args.gameassembly.parent / 'UnityPlayer.dll', *DEPENDENCIES.values()]
        if args.output is not None:
            check_output(args.output, protected)
        result = validate_storage_consumer_claims(contract_path=args.contract, gameassembly=args.gameassembly, metadata=args.metadata)
        if result['status'] == 'validated' and args.output is not None:
            publish_result(args.output, result, args.contract, protected)
    except (ValueError, KeyError, OSError, TypeError) as exc:
        result = {'status': 'pendingReview', 'rows': [], 'detail': str(exc)[:1500]}
    print(json.dumps({'status': result['status'], 'rows': len(result['rows']), **({'detail': result['detail']} if 'detail' in result else {})}))
    return 0 if result['status'] == 'validated' else 2


if __name__ == '__main__':
    raise SystemExit(main())
