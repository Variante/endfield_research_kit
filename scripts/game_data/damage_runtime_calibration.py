"""Traceable calibration input candidates from an admitted damage report (no fitting)."""
from __future__ import annotations
import argparse
from collections import Counter
import json
import tempfile
from pathlib import Path
from scripts.game_data.damage_runtime_numerics import fields, value, identity
from scripts.game_data.mission_trace_replay import fingerprint

LIMIT = 4 * 1024**3
BOUNDARY = ('Explicit synchronous action/pack/dump invocation and typed getter caller sources only. '
            'Same-action modifiers are candidates, not independent hits or a proved pack-to-target join. '
            'Pointer/UID equality does not prove lifetime. No fitting, server authority or combat completeness.')


def compact(field):
    if not field:
        return None
    return {k: (value(field) if k == 'value' else field.get(k)) for k in ('value', 'raw64', 'stateName', 'floatBits', 'enumNames') if k in field}


def ref(row):
    return {k: row.get(k) for k in ('sequence', 'threadId', 'invocationId', 'parentInvocationId', 'callerGameAssemblyRva')}


def prepare(report):
    if report.get('schema') != 'endfield.damage-runtime-inspection.v1' or report.get('status') != 'observed':
        raise ValueError('requires observed maintained damage inspection')
    inv = report.get('invocations', {})
    if inv.get('openCount') != 0 or inv.get('unwound') != 0 or inv.get('entered') != inv.get('completed'):
        raise ValueError('requires complete paired invocation projection')
    samples, dumps, modifiers, action_mods = [], {}, [], {}
    for action in report['actions']:
        aid = (action['threadId'], action['invocationId'])
        rows = {r['sequence']: r for r in action['observations']}
        entries = {r['invocationId']: r for r in rows.values() if r['phase'] == 'enter'}
        returns = {r['invocationId']: r for r in rows.values() if r['phase'] == 'return'}
        mods = []
        for iid, enter in entries.items():
            returned = returns.get(iid)
            if enter['hook'] != 'buff.AbilitySystem.ApplyModifier':
                continue
            before, after = fields(enter), fields(returned or {})
            target = identity(enter)
            stable = target is not None and target == identity(returned or {})
            item = {'id': len(modifiers), 'entry': ref(enter), 'return': ref(returned) if returned else None,
                    'target': list(target) if stable else None, 'identityStable': stable,
                    'before': {k: compact(v) for k,v in before.items()},
                    'after': {k: compact(v) for k,v in after.items()},
                    'returnedNormally': (returned or {}).get('invocationReceipt', {}).get('returnedNormally') is True}
            modifiers.append(item)
            mods.append(item)
        action_mods[aid] = mods
        for iid, enter in entries.items():
            if enter['hook'] == 'damage.Pack.DumpAttributes':
                parent = entries.get(enter['parentInvocationId'], {})
                dumps[(aid[0], iid)] = {'id': f'{aid[0]}:{iid}', 'entry': ref(enter),
                    'actionInvocationId': aid[1], 'packPointer': enter.get('receiverIdentity', {}).get('rawPointer'),
                    'parentHook': parent.get('hook'), 'getterSources': {}, 'attributeRows': 0}
            if enter['hook'] != 'damage.Pack.GetFinalAttackValue':
                continue
            returned = returns.get(iid)
            fs = fields(enter)
            samples.append({'id': len(samples), 'action': {'threadId': aid[0], 'invocationId': aid[1]},
                'pack': {'entry': ref(enter), 'return': ref(returned) if returned else None,
                    'pointer': enter.get('receiverIdentity', {}).get('rawPointer'),
                    'baseValue': compact(fs.get('packBaseValue')), 'damageType': compact(fs.get('damageType')),
                    'damageMask': compact(fs.get('damageMask')), 'finalValue': {
                        'value': (returned or {}).get('decodedReturnValue'), 'raw64': (returned or {}).get('returnValue')},
                    'returnedNormally': (returned or {}).get('invocationReceipt', {}).get('returnedNormally') is True},
                'modifierCandidateIds': [m['id'] for m in mods], 'dumpIds': [],
                'efficiencyOfDefCandidates': [{'return': ref(r), 'value': r.get('decodedReturnValue'),
                    'raw64': r.get('returnValue'),
                    'returnedNormally': r.get('invocationReceipt', {}).get('returnedNormally') is True}
                    for r in returns.values() if r['hook'] == 'damage.Const.EfficiencyOfDef'],
                'targetAssociation': 'unresolved-pack-to-modifier-join', 'critical': None, 'blocked': None,
                'rngOutcome': None, 'sourceSkill': None})
    for sample in samples:
        for key, dump in dumps.items():
            if key[0] == sample['action']['threadId'] and dump['actionInvocationId'] == sample['action']['invocationId'] and dump['packPointer'] not in (None, 0) and dump['packPointer'] == sample['pack']['pointer']:
                sample['dumpIds'].append(dump['id'])
    return samples, dumps, modifiers, action_mods


def project_attributes(rows, destination, dumps, action_mods):
    count = 0
    for snapshot in rows:
        key = snapshot['threadId'], snapshot.get('dumpInvocationId')
        dump = dumps.get(key)
        if dump is None or dump['actionInvocationId'] != snapshot.get('actionInvocationId'):
            raise ValueError(f'attribute source has no explicit dump/action: {key}')
        uid = value(snapshot.get('attributesInstanceUid'))
        for vals in snapshot['values']:
            row = dict(zip(snapshot['columns'], vals))
            targets = {tuple(m['target']) for m in action_mods[(key[0], dump['actionInvocationId'])]
                       if uid is not None and row.get('thisRaw') not in (None, 0) and m['target'] is not None
                       and m['target'][3] == row.get('thisRaw') and m['target'][4] == uid}
            source = json.dumps([snapshot.get('callerGameAssemblyRva'), row.get('thisRaw'), uid])
            source_info = dump['getterSources'].setdefault(source, {'getterCallerRva': snapshot.get('callerGameAssemblyRva'),
                'attributesPointer': row.get('thisRaw'), 'attributesInstanceUid': uid,
                'targetCandidates': [list(t) for t in sorted(targets)],
                'targetAssociation': 'unique-same-action-identity-candidate' if len(targets) == 1 else 'unknown', 'rows': 0})
            source_info['rows'] += 1
            dump['attributeRows'] += 1
            result = {'dumpId': dump['id'], 'actionInvocationId': dump['actionInvocationId'],
                'threadId': key[0], 'getterCallerRva': snapshot.get('callerGameAssemblyRva'),
                'sequence': row.get('sequence'), 'invocationId': row.get('invocationId'),
                'parentInvocationId': row.get('parentInvocationId'), 'attributesPointer': row.get('thisRaw'),
                'attributesInstanceUid': uid, 'attributeType': row.get('attributeTypeRaw'),
                'attributeNames': (row.get('attributeTypeField') or {}).get('enumNames'),
                'value': row.get('decodedReturnValue'), 'raw64': row.get('returnValue')}
            destination.write(json.dumps(result, separators=(',', ':'), allow_nan=False)+'\n')
            count += 1
    return count


def run(source, output):
    from scripts.repo_paths import REPO_ROOT
    source, output = Path(source).resolve(), Path(output).resolve()
    root = (REPO_ROOT/'reports').resolve()
    if not source.is_relative_to(root) or not output.is_relative_to(root):
        raise ValueError('inspection input and output must be under reports/')
    before = fingerprint(source, LIMIT)
    report = json.loads(source.read_text(encoding='utf-8'))
    side = report['attributeSnapshotSource']
    sidepath = Path(side['path']).resolve()
    if not sidepath.is_relative_to(root):
        raise ValueError('attribute input must be under reports/')
    attr_output = output.with_suffix('.attributes.jsonl')
    if source in (output, attr_output) or sidepath in (output, attr_output):
        raise ValueError('outputs must not replace either input')
    side_before = fingerprint(sidepath, LIMIT)
    if any(side_before[k] != side[k] for k in ('bytes', 'sha256')):
        raise ValueError('attribute sidecar fingerprint differs')
    samples, dumps, modifiers, action_mods = prepare(report)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = []
    try:
        for destination in (attr_output, output):
            with tempfile.NamedTemporaryFile(dir=destination.parent, prefix=destination.name+'.', suffix='.tmp', delete=False) as handle:
                temporary.append(Path(handle.name))
        attr_temp, main_temp = temporary
        with sidepath.open(encoding='utf-8') as src, attr_temp.open('w', encoding='utf-8', newline='\n') as dest:
            count = project_attributes((json.loads(line) for line in src), dest, dumps, action_mods)
        if count != side['rows']:
            raise ValueError('attribute sidecar row count differs')
        after, side_after = fingerprint(source, LIMIT), fingerprint(sidepath, LIMIT)
        if before != after or side_before != side_after:
            raise ValueError('input changed during analysis')
        dump_list = list(dumps.values())
        for dump in dump_list:
            dump['getterSources'] = list(dump['getterSources'].values())
        result = {'schema': 'endfield.damage-runtime-calibration.v1', 'status': 'observed-candidates',
            'boundary': BOUNDARY, 'combatComplete': False, 'counts': {'actions': len(report['actions']),
            'samples': len(samples), 'outerModifiers': len(modifiers), 'dumps': len(dump_list), 'attributeRows': count,
            'getterSourceAssociations': dict(Counter(s['targetAssociation'] for d in dump_list for s in d['getterSources']))},
            'sources': {'before': {'inspection': before, 'attributes': side_before},
                        'after': {'inspection': after, 'attributes': side_after}, 'fingerprintsVerifiedBeforeAndAfter': True},
            'attributeValues': {**fingerprint(attr_temp, LIMIT), 'path': str(attr_output)}, 'samples': samples, 'dumps': dump_list, 'outerModifiers': modifiers}
        main_temp.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n', encoding='utf-8')
        attr_temp.replace(attr_output)
        main_temp.replace(output)
        return result
    finally:
        for path in temporary:
            path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inspection', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.inspection, args.output)['counts']))


if __name__ == '__main__':
    main()
