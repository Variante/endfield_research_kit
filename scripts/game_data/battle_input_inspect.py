"""Project retained combat input call pairs without inventing async ownership.

Game action callbacks are not an OS input log. Boolean checks, queue mutation,
execution and damage processing remain separate observations. This module never
labels an absent child call as rejection or a void return as acceptance.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.mission_trace_capture_prepare import read_recipe
from scripts.game_data.mission_trace_invocations import Invocations, PAIRED_ABI
from scripts.game_data.mission_trace_replay import fingerprint
from scripts.repo_paths import REPO_ROOT

SCHEMA = 'endfield.battle-input-inspection.v1'
RECIPE = CONTRACTS_DIR / 'battle_input_capture.json'
RECIPES = {'battle-input': RECIPE, 'battle-center-fsm': CONTRACTS_DIR / 'battle_center_capture.json',
           'battle-center-delivery': CONTRACTS_DIR / 'battle_center_delivery_capture.json'}
BOUNDARY = ('Observed game callbacks and explicit same-thread call ancestry. '
            'Cross-tick pointer associations are candidates, not lifetime or request ownership proofs. '
            'No physical-key completeness, absent-call rejection, or successful-hit inference.')


def _values(row):
    return {f['label']: f.get('value') for f in row.get('fields', [])
            if f.get('state') == 1 or f.get('stateName') == 'exact'}


def project_rows(rows, hooks, recipe, *, source_context=None, read_layouts=None):
    """Consume already decoded rows. Session admission belongs to inspect_session."""
    specs = {h['name']: h for h in recipe['hooks']}
    trace.require(len(specs) == len(hooks) and set(specs) == {h['name'] for h in hooks},
                  'battle input hook selection differs')
    pairs, active, observations = Invocations(), {}, []
    abilities, actions, skills = {}, {}, {}
    last_sequence = 0
    for row in rows:
        trace.require(type(row.get('sequence')) is int and row['sequence'] > last_sequence,
                      'battle input sequence must increase')
        last_sequence = row['sequence']
        index = trace.integer(row.get('hookIndex'), 'hookIndex', len(hooks)-1)
        hook = hooks[index]
        trace.require(row.get('hook') == hook['name'] and PAIRED_ABI.fullmatch(hook['abiId']),
                      'battle input requires selected named paired hook')
        pairs.observe({**row, 'args': row.get('rawArgs')}, hook)
        role = specs[hook['name']].get('projectionRole', 'observation')
        key = (row['threadId'], row['invocationId'])
        this = row['rawArgs'][0]
        values = _values(row)
        if row['phase'] == 'enter':
            parent = active.get((row['threadId'], row['parentInvocationId']))
            ancestors = ([] if parent is None else parent['ancestors'] +
                         [dict(invocationId=parent['invocationId'], role=parent['role'], hook=parent['hook'])])
            observation = dict(hook=hook['name'], role=role, threadId=row['threadId'],
                               invocationId=row['invocationId'], ancestors=ancestors,
                               enter=row, exit=None, outcome='unresolved',
                               inputOwnership='synchronous-ancestor-only' if any(
                                   a['role'] in ('input', 'command') for a in ancestors) else 'unresolved')
            if role in ('ability-init', 'ability-release'):
                abilities.pop(this, None)
            if role in ('skill-init', 'skill-release'):
                skills.pop(this, None)
                abilities = {pointer: value for pointer, value in abilities.items()
                             if value.get('skillIdentity') != this}
            if role == 'ability-beforecast' and values.get('skillIdentity'):
                abilities[this] = dict(sequence=row['sequence'], invocationId=row['invocationId'],
                    observedAt='preparation-entry', **{**values, 'abilityIdentity':this})
            if role in ('action-bind', 'action-rebind'):
                actions.pop(this, None)
            if role in ('damage-action', 'damage-process'):
                environment = values.get('environmentIdentity')
                binding = actions.get(this)
                if binding and environment == binding['environmentIdentity']:
                    ability = abilities.get(environment)
                    observation['bindingCandidate'] = dict(actionBinding=binding,
                        abilityBinding=ability, skillBinding=skills.get(ability.get('skillIdentity')) if ability else None,
                        requestInvocationId=None,
                        lifetimeContinuityProved=False, castOccurrenceUnique=False)
                else:
                    observation['bindingCandidate'] = None
            active[key] = observation
            observations.append(observation)
        else:
            observation = active.pop(key)
            observation['exit'] = row
            if row['phase'] == 'unwind':
                observation['outcome'] = 'unwound'
                continue
            abi = PAIRED_ABI.fullmatch(hook['abiId'])
            if abi[1] == 'bool':
                observation['booleanReturn'] = bool(row['returnValue'])
                observation['outcome'] = role + ('-returned-true' if row['returnValue'] else '-returned-false')
            else:
                observation['outcome'] = 'returned-normally'
            observation['entrySnapshots'] = _values(observation['enter'])
            observation['exitSnapshots'] = values
            if role == 'skill-init':
                skills[this] = dict(sequence=row['sequence'], invocationId=row['invocationId'],
                                    **{**values, 'skillIdentity':this})
            if read_layouts is not None:
                from scripts.game_data.battle_input_capture_sources import REQUEST, decode_request
                source = read_layouts['values'][REQUEST]
                snapshots = {}
                for phase, event in (('before', observation['enter']), ('after', row)):
                    for field in event.get('fields', []):
                        if field.get('label') == 'requestSnapshot':
                            snapshots[phase] = (decode_request(bytes.fromhex(field['rawHex']), source)
                                                if field.get('state') == 1 else None)
                if snapshots:
                    observation['cacheSnapshots'] = snapshots
                    observation['cacheObservation'] = ('request-present-after-return' if
                        snapshots.get('after', {}) and snapshots['after'].get('present') else
                        'request-absent-after-return' if snapshots.get('after') is not None else 'unreadable')
            if role in ('ability-init','ability-beforecast') and values.get('skillIdentity'):
                abilities[this] = dict(sequence=row['sequence'], invocationId=row['invocationId'],
                                       observedAt=role+'-return',
                                       **{**values, 'abilityIdentity': this})
            elif role in ('action-bind', 'action-rebind') and values.get('environmentIdentity'):
                actions[this] = dict(sequence=row['sequence'], invocationId=row['invocationId'],
                                     **{**values, 'actionIdentity': this})
            elif role == 'ability-cast-info' and this in abilities:
                abilities[this] = {**abilities[this], **values, 'castInfoSequence': row['sequence']}
    receipt = pairs.finish(True)
    return dict(schema=SCHEMA, status='projected', sourceContext=source_context or {},
                boundary=BOUNDARY, physicalInputComplete=False, fullInputExecutionChainProved=False,
                invocations=receipt, observations=observations, diagnostics=[])


def inspect_session(session: Path, output_dir: Path, *, local_files=False, limits=trace.Limits(), recipe_name='battle-input'):
    output_dir = output_dir.resolve()
    trace.require(output_dir.is_relative_to((REPO_ROOT / 'reports').resolve()),
                  'battle input output must be below reports/')
    output_dir.mkdir(parents=True, exist_ok=True)
    destination = output_dir / 'battle-input.inspection.json'
    trace.require(not destination.exists(), 'battle input output already exists')
    report = dict(schema=SCHEMA, status='blocked', boundary=BOUNDARY, observations=[], diagnostics=[])
    try:
        trace.require(recipe_name in RECIPES, 'unknown reviewed battle recipe')
        recipe_path = RECIPES[recipe_name]
        recipe_bytes = recipe_path.read_bytes()
        inspected = trace.inspect_session(session, output_dir / 'trace', local_files=local_files, limits=limits)
        trace.require(inspected.get('status') == ('analyzed' if local_files else 'inspected'),
                      'battle input requires passing maintained inspection')
        facts = inspected.get('receiptFacts', {})
        trace.require(facts.get('collectionBoundFailureMarkers') == [] and all(facts.get(k) is True for k in
            ('captureCompleteClaim', 'healthyClaim', 'allJournalRowsAccounted',
             'strictTransitionReceiptsConsistent', 'nativeInputHashesBoundToProfile')),
            'battle input requires healthy complete accounted receipt and bound native inputs')
        artifacts, inventory = (trace.snapshot_local_inventory if local_files else trace.verify_inventory)(session.resolve(), limits)
        trace.require(inventory.get('inventorySha256') == inspected['inventory'].get('inventorySha256'),
                      'battle input inventory changed')
        profile, summary, hooks = trace.bindings(artifacts, limits)
        if recipe_name=='battle-center-delivery':
            from scripts.game_data.battle_center_delivery_capture_abi import validate_retained_profile
            validate_retained_profile(profile)
        recipe = read_recipe(recipe_path)
        specs = {h['name']: h for h in recipe['hooks']}
        for hook in hooks:
            spec = specs.get(hook['name'])
            trace.require(spec is not None and hook['symbol'] == spec['type']+'.'+spec['method'] and
                          hook['parameters'] == spec['parameters'] and hook['returnType'] == spec['returnType'] and
                          [f['label'] for f in hook['fields']] == [f['label'] for f in spec['fields']],
                          'battle input retained declaration differs from reviewed recipe')
        decoded = output_dir / 'trace' / inspected['decodedOutput']
        pin = fingerprint(decoded, limits.output_bytes)
        def rows():
            with decoded.open('rb') as source:
                for count, line in enumerate(source):
                    trace.require(count < limits.rows and len(line) <= limits.output_line_bytes,
                                  'battle input decoded row budget exceeded')
                    yield trace.parse_json(line, 'battle input decoded row')
        report = project_rows(rows(), hooks, recipe, read_layouts=profile.get('battleReadLayouts'), source_context=dict(
            sessionPath=str(session.resolve()), inspection=inspected, inventory=inventory,
            nativeInputs=profile['files'], receipt=summary, decodedSource={**pin, 'path':str(decoded)},
            nativeValidationReproved=False, recipeName=recipe_name))
        trace.require(recipe_path.read_bytes() == recipe_bytes, 'reviewed battle recipe changed')
        trace.require(fingerprint(decoded, limits.output_bytes) == pin, 'battle input decoded source changed')
        for artifact in artifacts.values():
            trace.require(fingerprint(artifact['path'], limits.artifact_bytes)['sha256'] == artifact['sha256'],
                          'battle input retained source changed')
        report['status'] = 'observed'
    except (ValueError, OSError, KeyError, TypeError, IndexError) as exc:
        report = dict(schema=SCHEMA, status='blocked', boundary=BOUNDARY, observations=[],
                      diagnostics=[dict(validator='battle_input_inspect', failedCheck='admission_or_projection',
                                        sourcePath=str(session.resolve()), detail=str(exc)[:2048])])
    with destination.open('x', encoding='utf-8') as target:
        json.dump(report, target, ensure_ascii=False, separators=(',', ':'), allow_nan=False)
        target.write('\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--local-files', action='store_true')
    parser.add_argument('--recipe', choices=tuple(RECIPES), default='battle-input')
    args = parser.parse_args(argv)
    result = inspect_session(args.session, args.output_dir, local_files=args.local_files, recipe_name=args.recipe)
    print('[battle_input_inspect]', result['status'], 'observations='+str(len(result['observations'])))
    for diagnostic in result['diagnostics']:
        print(diagnostic['detail'])
    return 0 if result['status'] == 'observed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
