"""Compare paired Buff observations with saved, previously admitted source spans.

This is candidate concordance, not proof of runtime file or node selection.
The selected frozen family receipt is reused; no corpus gate is rerun here.
"""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path

from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.buff_runtime_trace_inspect import checked_pin, fingerprint
from scripts.game_data.memorypack.core import read_memorypack_utf8_string
from scripts.game_data.mission_trace_invocations import Invocations

BUFF_EVENT = 'buff.Buff._ExecuteBuffAction'
CONTEXT_FIELDS = ('entryStoredBuffId', 'entryDataId', 'entryInstanceUid', 'entryClientInstId')
BOUNDARY = ('Previously admitted stored spans and explicit synchronous call enclosures '
    'agree on the compared fields only. A unique candidate does not prove live file '
    'loading, serialized-node selection, allocation lifetime, resolved targets or effects.')


def field_map(row):
    values = {field['label']: field for field in row['fields']}
    trace.require(len(values) == len(row['fields']), 'Buff candidates: duplicate field labels')
    return values


def same_snapshot(a, b):
    return (a is not None and b is not None and a['state'] in (1, 4) and
        b['state'] == a['state'] and a.get('raw64') == b.get('raw64') and a.get('text') == b.get('text'))


def observed_contexts(events, hooks):
    """Delay a consumer until its enclosing Buff event's return is observed."""
    invocations = Invocations()
    stacks, pending, opened = {}, {}, {}
    for row in events:
        hook = hooks[row['hookIndex']]
        trace.require(row['hook'] == hook['name'], 'Buff candidates: hook binding')
        invocations.observe({**row, 'args': row['rawArgs']}, hook)
        stack = stacks.setdefault(row['threadId'], [])
        phase, identity = row['phase'], row['invocationId']
        if phase == 'enter':
            ancestor = next((item for item in reversed(stack) if item['hook'] == BUFF_EVENT), None)
            opened[identity] = (row, ancestor)
            stack.append(row)
        elif phase in ('return', 'unwind'):
            entry, ancestor = opened.pop(identity)
            stack.pop()
            if hook['name'].endswith('.ExecuteInternal'):
                item = {'entry': entry, 'returned': row, 'context': ancestor,
                    'contextStableAtReturn': False, 'consumerStableAtReturn': phase == 'return'}
                if ancestor is None:
                    yield item
                else:
                    pending.setdefault(ancestor['invocationId'], []).append(item)
            if row['hook'] == BUFF_EVENT:
                before, after = field_map(entry), field_map(row)
                stable = phase == 'return' and all(same_snapshot(before.get(k), after.get(k)) for k in CONTEXT_FIELDS)
                for item in pending.pop(identity, []):
                    item['contextStableAtReturn'] = stable
                    yield item
    invocations.finish(True)
    trace.require(not pending and not opened, 'Buff candidates: unclosed context')


def route_catalog(validation, wanted_types, pins):
    """Read type/tag declarations actually consumed by the frozen family gate."""
    scope = validation.get('contractReadScope', {})
    trace.require(scope.get('probeObserved') is True and scope.get('failureLatched') is False and
        scope.get('observedInputFailures') == 0, 'Buff candidates: frozen contract scope failed')
    routes = {}
    for pin in scope.get('consumedPins', []):
        path = Path(pin['path'])
        if not path.name.startswith('buff_') or not path.name.endswith('_native.json'):
            continue
        contract = trace.read_object(path, 32 * 1024**2)
        records, dispatch = contract.get('records'), contract.get('actionDispatch')
        if not isinstance(records, dict) or not isinstance(dispatch, dict):
            continue
        selected = {key: value for key, value in records.items()
            if value.get('runtimeTypeName') in wanted_types}
        if not selected:
            continue
        actual_pin = checked_pin(pin)
        trace.require(contract.get('status') == 'exact-current-build' and
            contract.get('nativeInputs') == validation['nativeInputs'],
            'Buff candidates: frozen route native input differs: ' + path.name)
        pins.append(actual_pin)
        for tag, key in dispatch.items():
            if key not in selected:
                continue
            tag = int(tag)
            declaration = {'type': selected[key]['runtimeTypeName'], 'contract': path.name}
            trace.require(tag not in routes or routes[tag]['type'] == declaration['type'],
                'Buff candidates: conflicting frozen action route')
            routes[tag] = declaration
    return routes


def source_nodes(receipt, data, source_id, routes=None):
    """Visit only the Buff event maps in a complete, byte-matched root receipt."""
    trace.require(receipt.get('wholeSchemaExact') is True and receipt.get('rootMemberCount') == 30 and
        receipt.get('headerRange') == [0, 1] and data[:1] == b'\x1e' and
        receipt.get('bytesConsumed') == receipt.get('physicalEof') == len(data),
        'Buff candidates: incomplete root receipt')
    root_fields = receipt['fields']
    trace.require(len(root_fields) == 30, 'Buff candidates: root field count')
    cursor = 1
    for index, field in enumerate(root_fields):
        trace.require(field['index'] == index and field['start'] == cursor and
            cursor <= field['end'] <= len(data), 'Buff candidates: root field partition')
        cursor = field['end']
    trace.require(cursor == len(data), 'Buff candidates: root EOF')
    identity = next(field for field in root_fields if field['name'] == 'id')
    text, end, error = read_memorypack_utf8_string(data, identity['start'])
    trace.require(not error and end == identity['end'] and text == identity['value'] == source_id,
        'Buff candidates: root/source ID differs')
    trace.require(text.encode('utf-8') == data[identity['start'] + 4:end],
        'Buff candidates: invalid source ID encoding')
    result, seen = [], set()

    def visit(value, path, event, depth=0):
        trace.require(depth <= 128, 'Buff candidates: receipt nesting budget')
        if isinstance(value, dict):
            names = value.get('namedFields') or value.get('namedMembers') or (
                value.get('parent', {}).get('namedFields', []) if isinstance(value.get('parent'), dict) else [])
            declaration = (routes or {}).get(value.get('tag'))
            type_name = value.get('typeName') or (declaration or {}).get('type')
            if type_name and 'tag' in value and any(
                    field.get('fieldName', field.get('name')) == 'serverActionIndex' for field in names):
                trace.require(declaration is None or declaration['type'] == type_name,
                    'Buff candidates: receipt/frozen dispatch type differs')
                key = (type_name, value['start'], value['end'])
                trace.require(0 <= key[1] < key[2] <= len(data), 'Buff candidates: action span')
                if key not in seen:
                    seen.add(key)
                    trace.require(len(result) < 10000 and len({f.get('fieldName', f.get('name')) for f in names}) == len(names),
                        'Buff candidates: action budget or duplicate fields')
                    result.append({'type': key[0], 'tag': value['tag'], 'start': key[1], 'end': key[2],
                        'path': path, 'event': event,
                        'typeEvidence': 'receipt typeName' if value.get('typeName') else declaration['contract'],
                        'fields': {f.get('fieldName', f.get('name')): f for f in names}})
            for name, item in value.items():
                if isinstance(item, (dict, list)):
                    visit(item, path + '/' + name, event, depth + 1)
        elif isinstance(value, list):
            for index, item in enumerate(value):
                visit(item, path + '/' + str(index), event, depth + 1)

    event_field = next(field for field in root_fields if field['name'] == 'buffEventAction')
    child = event_field.get('child') or {}
    for index, mapping in enumerate(child.get('maps', [])):
        event = next(field for field in mapping['namedFields'] if field['name'] == 'buffEvent')
        raw = data[event['start']:event['end']]
        trace.require(len(raw) == 4 and raw.hex().lower() == event['rawHex'].lower(),
            'Buff candidates: stored event span differs')
        visit(mapping, f'buffEventAction/maps/{index}', int.from_bytes(raw, 'little'))
    return result


def compare_node(node, data, entry, returned, hook):
    """Compare declared scalar/string fields; preserve unsupported fields explicitly."""
    before, after = field_map(entry), field_map(returned)
    compared, unchecked = [], []
    for descriptor in hook['fields']:
        if descriptor.get('role') != 'storedConfiguration':
            continue
        label = descriptor['label']
        a, b = before.get(label), after.get(label)
        if not same_snapshot(a, b):
            return None
        path = descriptor.get('fieldPath') or []
        trace.require(path and '::' in path[-1]['field'], 'Buff candidates: missing stored field path')
        name = path[-1]['field'].rsplit('::', 1)[1]
        field = node['fields'].get(name)
        if field is None or field.get('declaredType') != descriptor['type']:
            unchecked.append(label)
            continue
        start, end = field['start'], field['end']
        trace.require(node['start'] <= start <= end <= node['end'], 'Buff candidates: field outside action')
        raw = data[start:end]
        if descriptor['kind'] in (2, 5):
            width = 1 if descriptor['kind'] == 5 else 4
            if a['state'] != 1 or len(raw) != width or descriptor.get('valueBits') != width * 8:
                return None
            if 'rawHex' in field:
                trace.require(raw.hex().lower() == field['rawHex'].lower(),
                    f'Buff candidates: stored scalar {name} at {start}:{end} differs')
            if int.from_bytes(raw, 'little') != (a['raw64'] & ((1 << (width * 8)) - 1)):
                return None
        elif descriptor['kind'] == 3:
            text, consumed, error = read_memorypack_utf8_string(data[:end], start)
            if error or consumed != end:
                unchecked.append(label)
                continue
            # The shared primitive replaces malformed UTF-8; no replacement is admitted here.
            if text is not None and text.encode('utf-8') != raw[4:]:
                return None
            if (a['state'] == 4 and text is not None) or (a['state'] == 1 and text != a.get('text')):
                return None
        else:
            unchecked.append(label)
            continue
        compared.append({'label': label, 'sourceField': name, 'sourceRange': [start, end]})
    if not any(item['sourceField'] == 'serverActionIndex' for item in compared):
        return None
    return {'sourceNode': {k: node[k] for k in ('type', 'tag', 'start', 'end', 'path', 'event', 'typeEvidence') if k in node},
        'comparedFields': compared, 'uncheckedFields': unchecked,
        'runtimeNodeSelectionExact': False}


def validate_family_binding(profile, validation):
    trace.require(validation.get('status') == 'current-validated-native-cache' and
        validation.get('completeFamilySourceGateSatisfied') is True,
        'Buff candidates: completed frozen family validation required')
    for key, native in (('gameAssembly', 'GameAssembly.dll'), ('metadata', 'global-metadata.dat')):
        expected = validation.get('nativeInputs', {}).get(native)
        captured = profile.get('files', {}).get(key, {}).get('sha256')
        trace.require(isinstance(expected, str) and len(expected) == 64 and isinstance(captured, str) and
            captured.lower() == expected.lower(), 'Buff candidates: captured/family native input differs: ' + key)


def inspect_candidates(analysis_dir, validation_path, output_dir):
    analysis_dir, output_dir = analysis_dir.resolve(), output_dir.resolve()
    trace.require(any(output_dir.is_relative_to((trace.REPO_ROOT / folder).resolve())
        for folder in ('reports', 'scratch', 'tmp')), 'Buff candidates: output must be ignored')
    analysis_path = analysis_dir / 'buff-paired-analysis.json'
    analysis = trace.read_object(analysis_path, 32 * 1024**2)
    session = Path(analysis['session']).resolve()
    trace.require(not output_dir.is_relative_to(session) and not session.is_relative_to(output_dir) and
        not output_dir.is_relative_to(analysis_dir) and not analysis_dir.is_relative_to(output_dir),
        'Buff candidates: output must be separate from session and passing analysis')
    trace.require(not output_dir.exists() or output_dir.is_dir() and not any(output_dir.iterdir()),
        'Buff candidates: output must be new or empty')
    trace.require(analysis['status'] == 'locally-analyzed-recorded-pairs' and
        analysis.get('recordedPairTransportComplete') is True, 'Buff candidates: complete paired analysis required')
    pins = [fingerprint(analysis_path), fingerprint(validation_path)]
    bound = {Path(item['path']).name: checked_pin(item) for item in analysis['inputs']}
    pins.extend(bound.values())
    profile = trace.read_object(Path(bound['mission-trace-build-manifest.json']['path']), 32 * 1024**2)
    validation = trace.read_object(validation_path, 64 * 1024**2)
    validate_family_binding(profile, validation)
    wanted_types = {field['type'] for hook in profile['missionTraceHooks'] for field in hook['fields']
        if field['label'] == 'entryStoredDataIdentity'}
    routes = route_catalog(validation, wanted_types, pins)
    family_pin = checked_pin(validation['familyReport'])
    pins.append(family_pin)
    family = trace.read_object(Path(family_pin['path']), 1024**3)
    trace.require(family.get('status') == 'complete' and len(family['files']) <= 4096,
        'Buff candidates: incomplete or oversized family')
    sources = {Path(row['identity']['fileName']).stem: row for row in family['files']}
    trace.require(len(sources) == len(family['files']), 'Buff candidates: duplicate family source IDs')
    cache, results, counts = {}, {}, Counter()
    decoded = Path(bound['decoded.events.jsonl']['path'])
    def events():
        with decoded.open('rb') as stream:
            count = 0
            while line := stream.readline(trace.Limits().output_line_bytes + 1):
                count += 1
                trace.require(count <= trace.Limits().rows and line.endswith(b'\n') and
                    len(line) <= trace.Limits().output_line_bytes, 'Buff candidates: event budget')
                yield trace.parse_json(line, 'Buff candidate event')
            trace.require(count == analysis['invocations']['entered'] * 2 +
                sum(row['rows'] for row in analysis['hookPhases'] if row['phase'] == 'entry'),
                'Buff candidates: decoded row count')

    for observation in observed_contexts(events(), profile['missionTraceHooks']):
        entry, returned, context = (observation[k] for k in ('entry', 'returned', 'context'))
        hook = profile['missionTraceHooks'][entry['hookIndex']]
        fields = field_map(entry)
        context_values = field_map(context) if context else {}
        source_id = context_values.get('entryDataId', {}).get('value')
        state, candidates = 'no-stable-buff-context', []
        event = context_values.get('suppliedBuffEvent', {}).get('value')
        if (observation['consumerStableAtReturn'] and observation['contextStableAtReturn'] and source_id and
                context_values['entryStoredBuffId']['value'] == source_id):
            if source_id not in cache:
                row = sources.get(source_id)
                archive = trace.safe_path(session, 'source-files/export_full/game/Json/BuffData/' + source_id + '.json')
                if row is None or row.get('wholeSchemaExact') is not True or 'rootSharedEventReceipt' not in row:
                    cache[source_id] = None
                else:
                    source_pin = fingerprint(archive)
                    trace.require(source_pin['sha256'].lower() == row['logicalSha256'].lower() and
                        source_pin['bytes'] == row['identity']['length'], 'Buff candidates: archived/family bytes differ: ' + source_id)
                    pins.append(source_pin)
                    data = trace.read_bytes(archive, 32 * 1024**2)
                    cache[source_id] = (data, source_nodes(row['rootSharedEventReceipt'], data, source_id, routes))
            stored = cache[source_id]
            state = 'no-exact-shared-event-receipt'
            identity_spec = next((field for field in hook['fields'] if field['label'] == 'entryStoredDataIdentity'), None)
            if stored is not None and identity_spec is not None:
                data, nodes = stored
                data_identity = fields['entryStoredDataIdentity']
                if data_identity['state'] == 1 and data_identity['raw64'] and same_snapshot(
                        data_identity, field_map(returned).get('entryStoredDataIdentity')):
                    eligible = [node for node in nodes if node['type'] == identity_spec['type'] and node['event'] == event]
                    for node in eligible:
                        candidate = compare_node(node, data, entry, returned, hook)
                        if candidate:
                            candidates.append(candidate)
                    state = ('one-stored-candidate' if len(candidates) == 1 else
                        'multiple-stored-candidates' if candidates else
                        'no-compared-field-match' if eligible else 'type-event-not-in-stored-node-index')
                else:
                    state = 'unstable-or-null-action-data'
            elif stored is not None:
                state = 'action-data-not-observed'
        signature = {'hook': hook['name'], 'buffId': source_id, 'event': event, 'matchState': state,
            'entryConfiguration': [{k: field[k] for k in ('label', 'type', 'state', 'raw64', 'text') if k in field}
                for field in entry['fields'] if any(spec['label'] == field['label'] and
                    spec.get('role') == 'storedConfiguration' for spec in hook['fields'])],
            'candidates': candidates}
        key = json.dumps(signature, sort_keys=True)
        trace.require(len(results) <= 65536, 'Buff candidates: grouping budget')
        group = results.setdefault(key, {**signature, 'calls': 0, 'returnedTrue': 0, 'returnedFalse': 0, 'examples': []})
        group['calls'] += 1
        group['returnedTrue' if returned['returnValue'] == 1 else 'returnedFalse'] += 1
        if len(group['examples']) < 3:
            group['examples'].append({'invocationId': entry['invocationId'], 'entrySequence': entry['sequence'],
                'returnSequence': returned['sequence'], 'buffEventInvocationId': context['invocationId'] if context else None,
                'dataIdentityBits': fields.get('entryStoredDataIdentity', {}).get('raw64')})
        counts[state] += 1
    trace.require(pins == [fingerprint(Path(pin['path'])) for pin in pins], 'Buff candidates: inputs changed during join')
    report = {'schema': 'endfield.buff-runtime-source-candidates.v1', 'status': 'compared-stored-candidates',
        'session': str(session), 'inputs': pins, 'summary': dict(counts),
        'groups': sorted(results.values(), key=lambda row: (-row['calls'], row['hook'])),
        'nativeValidationReproved': False, 'frozenStoredReceiptsReused': True,
        'runtimeNodeSelectionExact': False, 'wholeRootGainsClaimed': 0, 'boundary': BOUNDARY}
    output_dir.mkdir(parents=True)
    (output_dir / 'source-candidates.json').write_text(json.dumps(report, ensure_ascii=True, indent=2) + '\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-dir', type=Path, required=True)
    parser.add_argument('--family-validation', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_candidates(args.analysis_dir, args.family_validation, args.output_dir)
    except (trace.InspectionError, OSError, KeyError, ValueError, TypeError) as exc:
        print('[buff_runtime_source_candidates] failed: ' + str(exc)); return 1
    print(json.dumps(report['summary'])); return 0


if __name__ == '__main__':
    raise SystemExit(main())
