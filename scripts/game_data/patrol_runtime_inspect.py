"""Evaluate bounded Patrol observations after the strict recorder package gate.

The public entry always inspects the original package itself. Saved analysis or
native proof objects are never accepted in place of it. Observed synchronous
enclosure, physical field equality, callback selection and downstream playback
are separate results; missing operands remain named capture requirements.
"""
from __future__ import annotations

if __name__ == '__main__' and __spec__ is None:
    raise SystemExit('Run from repository root: python -m scripts.game_data.patrol_runtime_inspect')

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path

from scripts.game_data import mission_trace_inspect as transport
from scripts.game_data.mission_trace_invocations import Invocations
from scripts.game_data.patrol_runtime_capture_sources import SCHEMA as LAYOUT_SCHEMA, POINT, ACTION

SCHEMA = 'endfield.patrol-runtime-inspection.v1'
MAX_INVOCATIONS = 16384


class PatrolInspectionError(ValueError):
    pass


def need(check, condition):
    if not condition:
        raise PatrolInspectionError('patrol_runtime.' + check)


def _field(row, label, *, null=False):
    hits = [v for v in row['fields'] if v['label'] == label]
    need('unique-field:' + label, len(hits) == 1)
    value, = hits
    need('complete-field:' + label, value['state'] == 1 or null and value['state'] == 4)
    return value


def _pointer(row, label, *, null=False):
    value = _field(row, label, null=null)
    need('reference-identity:' + label, value.get('valueRepresentation') == 'referenceIdentity')
    result = value.get('rawPointer', 0) if value['state'] == 1 else 0
    need('nonnull-reference:' + label, type(result) is int and (result > 0 or null and result == 0))
    return result


def _raw(row, label):
    value = _field(row, label)
    need('opaque-raw-span:' + label, value.get('readMode') in {'rawBytes', 'dependentReferenceBytes', 'virtualCallbackPair'})
    data = bytes.fromhex(value['rawHex'])
    need('complete-opaque-span:' + label, len(data) == value['byteCount'] > 0)
    return value, data


def _value(row, label):
    value = _field(row, label)
    need('canonical-bool:' + label, value.get('type') != 'bool' or value.get('canonicalBool') is True)
    return value.get('value')


def _slice(raw, descriptor, qualified, size):
    cells = [c for c in descriptor['rawProof']['fields'] if c['field'] == qualified]
    need('unique-owned-field:' + qualified, len(cells) == 1)
    cell, = cells
    start = cell['offset'] - descriptor['rawProof']['offset']
    need('owned-field-span:' + qualified, type(size) is int and size > 0
         and cell['byteCount'] == size and 0 <= start <= len(raw) - size)
    return raw[start:start + size]


def _container(row, label):
    value = _field(row, label)
    need('stable-full-container:' + label, value.get('readMode') == 'boundedContainer'
         and value['countBefore'] == value['countAfter'] <= 8
         and value['versionBefore'] == value['versionAfter']
         and value['storageBefore'] == value['storageAfter']
         and value['capacityBefore'] == value['capacityAfter'] >= value['countBefore']
         and value['stride'] == 8 and value['failureCode'] == 0
         and len(bytes.fromhex(value['rawHex'])) == 8 * value['countBefore'])
    return value


def _conversion(initializer, converter, layouts):
    """One actual converter, then installed output in its enclosing Init return."""
    first, last = initializer['entry'], initializer['return']
    entered, returned = converter['entry'], converter['return']
    controller = _pointer(first, 'controller')
    need('same-controller-through-conversion', all(_pointer(r, 'controller') == controller
         for r in (last, entered, returned)))
    config = _pointer(entered, 'config')
    need('same-config-through-return', _pointer(returned, 'config') == config)
    output, data = _raw(returned, 'coreOutput')
    need('Core-reference-byref-output8', len(data) == 8
         and output.get('argumentRepresentation', {}).get('mode') == 'referenceByRef')
    core = int.from_bytes(data, 'little')
    need('same-installed-Core-reference', core > 0 and _pointer(last, 'installedCore') == core)
    before = _container(entered, 'configPoints')
    after = _container(returned, 'configPoints')
    need('same-Config-list-snapshot-before-and-after', all(before[k] == after[k] for k in
         ('containerAddress', 'storageBefore', 'countBefore', 'versionBefore', 'capacityBefore', 'rawHex')))
    actions = _container(last, 'coreActions')
    count = before['countBefore']
    need('same-ordered-point-action-count', count == actions['countBefore'])
    need('exact-Config-and-Core-container-source-roles', before['type'].endswith('<' + POINT + '>')
         and actions['type'].endswith('<' + ACTION + '>'))
    widths = layouts['pointTransfers']
    joins = []
    for index in range(count):
        point, raw_point = _raw(entered, 'point' + str(index))
        again, raw_again = _raw(returned, 'point' + str(index))
        action, raw_action = _raw(last, 'action' + str(index))
        need('stable-point-snapshot:' + str(index), point['raw64'] == again['raw64'] and raw_point == raw_again)
        need('same-index-source-descriptors:' + str(index), point['itemIndex'] == action['itemIndex'] == index
             and point['type'] == POINT and action['type'] == ACTION)
        for source_name, target_name, size in (
            ('position', 'position', widths['positionBytes']),
            ('enterGait', 'enterGait', widths['gaitBytes']),
            ('actions', 'subActions', widths['subActionsReferenceBytes'])):
            need('ordered-owned-transfer:' + str(index) + ':' + source_name,
                 _slice(raw_point, point, POINT + '::' + source_name, size) ==
                 _slice(raw_action, action, ACTION + '::' + target_name, size))
        joins.append(dict(index=index, pointAddress=point['raw64'], actionAddress=action['raw64'],
                          ownedPositionGaitAndSubActionReferenceEqual=True))
    return dict(initializerInvocation=first['invocationId'], converterInvocation=entered['invocationId'],
                threadId=first['threadId'], controller=controller, config=config, core=core,
                pointCount=count, orderedPointTransfers=joins, observedInstalledReferenceAndTransfers=True,
                boundary='Stable sampled before/after descriptors and same-process references; no unseen-write history, allocator identity or controller activation is inferred.')


_SCALARS = ('isStarted', 'isFinished', 'timer', 'executeTimeStamp', 'delayToNextTick',
            'delayToNextTickAllowDeltaTimeZero', 'ticking', 'ticked')


def _executor_state(row):
    value = {key: _value(row, key) for key in _SCALARS}
    for key in ('timer', 'executeTimeStamp'):
        need('finite-executor-Single:' + key, _field(row, key).get('floatClass') == 'finite')
    value['currentAction'] = _pointer(row, 'currentAction', null=True)
    return value


def _executor_transfer(invocation, layouts):
    entry, returned = invocation['entry'], invocation['return']
    executor = _pointer(entry, 'executor')
    need('same-executor-return', _pointer(returned, 'executor') == executor)
    uid = _value(entry, 'executorUid')
    need('same-tracked-nonzero-UID', type(uid) is int and uid > 0 and _value(returned, 'executorUid') == uid)
    need('actual-false-force-selected-input', _value(entry, 'force') is False)
    need('normal-successful-TryInvoke', returned['returnValue'] == 1)
    delay = _field(returned, 'outputDelay')
    need('outputDelay-exact-bool-byref', delay.get('argumentRepresentation', {}).get('mode') == 'scalarByRef'
         and delay.get('canonicalBool') is True and delay['value'] is False)
    actual = _executor_state(returned)
    expected = layouts['executorState']['tickInputState']
    need('successful-scalar-state-equals-fresh-source-domain',
         all((expected[k] == 0 and _field(returned, k).get('floatBits') == '0x00000000')
             if k in ('timer', 'executeTimeStamp') else type(actual[k]) is type(expected[k]) and actual[k] == expected[k]
             for k in _SCALARS)
         and actual['currentAction'] == 0 and expected['currentAction'] is None)
    incoming = _pointer(entry, 'incomingEvent')
    cached = _pointer(returned, 'cachedEvent')
    need('cached-event-distinct-from-unmodified-incoming', cached != incoming
         and _pointer(returned, 'incomingEvent') == incoming)
    return dict(invocationId=entry['invocationId'], threadId=entry['threadId'], executor=executor,
                executorUid=uid, incomingEvent=incoming, cachedEvent=cached, scalarPoststate=actual,
                selectedScalarTryInvokeOutputObserved=True, completeSelectedStateObserved=False,
                unresolved=['Cursor/result/iteration containers and typed event values require their own full source-bound descriptors; scalar agreement does not establish them.'])


def _callback_selection(invocation):
    role = 'actionEnter' if invocation['entry']['hook'] == 'patrol.actionEnter' else 'actionExecute'
    entry, returned = invocation['entry'], invocation['return']
    action = _pointer(entry, 'action')
    need('same-action-at-wrapper-return', _pointer(returned, 'action') == action)
    before, raw = _raw(entry, 'callback')
    after, raw_after = _raw(returned, 'callback')
    need('same-nonnull-observed-callback-pair', before.get('callbackRole') == after.get('callbackRole') == role
         and raw == raw_after and len(raw) == 16
         and int.from_bytes(raw[:8], 'little') > 0 and int.from_bytes(raw[8:], 'little') > 0)
    return dict(invocationId=entry['invocationId'], action=action, role=role,
                targetAddress=int.from_bytes(raw[:8], 'little'), methodInfoAddress=int.from_bytes(raw[8:], 'little'),
                wrapperReturnedNormally=True, wrapperReturn=returned['returnValue'],
                callbackSelectionObserved=True, actualCallbackEntryReturnObserved=False,
                actualAuthoredCallbackEffectsProved=False)


def _tick_transfer(invocation, completed, layouts):
    entry, returned = invocation['entry'], invocation['return']
    executor = _pointer(entry, 'executor'); uid = _value(entry, 'executorUid')
    need('tick-stable-tracked-executor', type(uid) is int and uid > 0
         and _pointer(returned, 'executor') == executor and _value(returned, 'executorUid') == uid)
    need('tick-selected-zero-Single-delta', _field(entry, 'deltaTime').get('floatBits') == '0x00000000')
    ancestor = entry['parentInvocationId']
    candidates = [v for v in completed.values() if v['entry']['hook'] == 'patrol.tryInvoke'
        and v['entry']['threadId'] == entry['threadId'] and v['entry']['parentInvocationId'] == ancestor
        and v['return']['sequence'] < entry['sequence'] and _pointer(v['entry'], 'executor') == executor
        and _value(v['entry'], 'executorUid') == uid]
    need('same-recorded-ancestor-single-successful-TryInvoke', ancestor > 0 and len(candidates) == 1)
    success = _executor_transfer(candidates[0], layouts)
    need('same-observed-TryInvoke-to-Tick-scalar-state', _executor_state(entry) == success['scalarPoststate'])
    actions = [v for v in completed.values() if v['entry']['parentInvocationId'] == entry['invocationId']
               and v['entry']['hook'] in ('patrol.actionEnter', 'patrol.actionExecute')]
    enters = [v for v in actions if v['entry']['hook'] == 'patrol.actionEnter']
    executes = [v for v in actions if v['entry']['hook'] == 'patrol.actionExecute']
    need('one-paired-Enter-and-DoExecute', len(enters) == len(executes) == 1)
    enter, execute = enters[0], executes[0]
    need('ordered-action-wrappers-return-true', enter['return']['sequence'] < execute['entry']['sequence']
         and enter['return']['returnValue'] == execute['return']['returnValue'] == 1)
    action = _pointer(enter['entry'], 'action')
    need('same-actual-action-wrapper-receiver', _pointer(execute['entry'], 'action') == action
         and _pointer(returned, 'currentAction') == action)
    storage, raw = _raw(execute['return'], 'actionResultStorage')
    owner = 'Beyond.Gameplay.Actions.ActionBase::'
    def bits(name, size):return _slice(raw, storage, owner + name, size)
    need('actual-action-result-next-and-delay-flags', bits('m_executeResult', 1) == b'\x01'
         and bits('m_finishThread', 1) == bits('m_delayToNextTick', 1) == bits('m_delayToNextTickAllowDeltaTimeZero', 1) == b'\x00'
         and int.from_bytes(bits('m_nextID', 4), 'little', signed=True) >= 0
         and int.from_bytes(bits('m_reservedID', 4), 'little', signed=True) == -1
         and bits('m_waitForExtraUidList', 8) == b'\x00' * 8)
    delay_bits = bits('m_delayToNext', 4); delay = struct.unpack('<f', delay_bits)[0]
    epsilon_source = layouts['executorTimer']['source']['regions']
    need('one-source-owned-Single-epsilon', len(epsilon_source) == 1 and len(bytes.fromhex(epsilon_source[0][1])) == 4)
    epsilon = struct.unpack('<f', bytes.fromhex(epsilon_source[0][1]))[0]
    need('actual-delay-greater-than-selected-source-epsilon', math.isfinite(epsilon) and epsilon > 0
         and math.isfinite(delay) and delay > epsilon)
    actual = _executor_state(returned); expected = layouts['executorState']['tickOutputState']
    need('same-scalar-Tick-return-state', all(actual[k] == expected[k] and type(actual[k]) is type(expected[k])
         for k in _SCALARS if k not in ('timer', 'executeTimeStamp'))
         and _field(returned, 'timer').get('floatBits') == '0x00000000'
         and _field(returned, 'executeTimeStamp').get('floatBits') == '0x' + delay_bits[::-1].hex())
    return dict(invocationId=entry['invocationId'], tryInvokeInvocation=success['invocationId'],
        recordedAncestorInvocation=ancestor, executor=executor, executorUid=uid, action=action,
        selectedScalarContinuationObserved=True, actionWrapperResultsObserved=True,
        completeSelectedStateObserved=False, actualAuthoredCallbackEffectsProved=False,
        unresolved=['Cursor, previous-result, iteration dictionary and extra-thread list logical contents and manager queue still require complete source-bound descriptors.'])


def _conversion_context(invocation, completed, layouts):
    """A missing causal enclosure is a semantic gap, not broken transport."""
    entry = invocation['entry']
    parent = completed.get(entry['parentInvocationId'])
    need('converter-recorded-immediate-Init-enclosure', parent is not None and parent['entry']['hook'] == 'patrol.init'
         and parent['entry']['threadId'] == entry['threadId'])
    siblings = [v for v in completed.values() if v['entry']['parentInvocationId'] == entry['parentInvocationId']
                and v['entry']['hook'] == entry['hook']]
    need('one-selected-converter-per-Init', len(siblings) == 1)
    return _conversion(parent, invocation, layouts)


def _evaluate(rows, hooks, layouts):
    """Private pure evaluator for already package-bound, decoded observations."""
    need('fresh-retained-layout-schema', layouts.get('schema') == LAYOUT_SCHEMA)
    tracker = Invocations(); active = {}; completed = {}; sequence = 0
    for row in rows:
        need('strict-sequence-order', type(row['sequence']) is int and row['sequence'] > sequence)
        sequence = row['sequence']
        index = row['hookIndex']; need('retained-hook-index', type(index) is int and 0 <= index < len(hooks))
        hook = hooks[index]; need('exact-retained-hook-name', row['hook'] == hook['name'] and row['hook'].startswith('patrol.'))
        record = dict(row, args=row['rawArgs'])
        receipt = tracker.observe(record, hook)
        identity = row['invocationId']
        if row['phase'] == 'enter':
            need('bounded-semantic-invocation-count', len(active) + len(completed) < MAX_INVOCATIONS)
            active[identity] = row
        elif receipt is not None:
            entered = active.pop(identity)
            need('normal-return-required', receipt['returnedNormally'])
            completed[identity] = dict(entry=entered, **{'return': row})
    pairing = tracker.finish(True)
    result = dict(pairing=pairing, conversions=[], executorTransfers=[], tickTransfers=[], callbackSelections=[], radioRequests=[],
                  checkpointCalls=[], notAdmitted=[], gaps=[])
    def assess(key, invocation, function, *args):
        try:
            result[key].append(function(*args))
        except PatrolInspectionError as exc:
            # A complete negative/other source path is still an observation.
            # It never becomes a successful witness for the selected domain.
            result['notAdmitted'].append(dict(invocationId=invocation['entry']['invocationId'],
                hook=invocation['entry']['hook'], selectedEffectAdmitted=False, gate=str(exc)[:2048]))
    for invocation in completed.values():
        entry = invocation['entry']; name = entry['hook']
        if name == 'patrol.convert':
            assess('conversions', invocation, _conversion_context, invocation, completed, layouts)
        elif name == 'patrol.tryInvoke':
            assess('executorTransfers', invocation, _executor_transfer, invocation, layouts)
        elif name == 'patrol.logicTick':
            assess('tickTransfers', invocation, _tick_transfer, invocation, completed, layouts)
        elif name in ('patrol.actionEnter', 'patrol.actionExecute'):
            assess('callbackSelections', invocation, _callback_selection, invocation)
        elif name in ('patrol.playRadio', 'patrol.stopRadio'):
            radio = _field(entry, 'radioId', null=True); again = _field(invocation['return'], 'radioId', null=True)
            need('unchanged-complete-radio-string', radio['state'] == again['state']
                 and radio.get('text') == again.get('text')
                 and (radio['state'] == 4 or isinstance(radio.get('text'), str)))
            result['radioRequests'].append(dict(invocationId=entry['invocationId'], threadId=entry['threadId'],
                operation=name, radioId=radio.get('text'), nonemptyRequestCandidate=bool(radio.get('text')),
                returnedNormally=True, downstreamAudioAssociated=False))
        elif name in ('patrol.checkpoint', 'patrol.checkpointFilter'):
            result['checkpointCalls'].append(dict(invocationId=entry['invocationId'], hook=name,
                returnedNormally=True, result=invocation['return']['returnValue'], fullSameReferenceEventChainObserved=False))
    for key, message in (
        ('conversions', 'No complete Config-to-installed-Core conversion observed.'),
        ('executorTransfers', 'No false-force tracked-executor successful output observed.'),
        ('tickTransfers', 'No same-recorded-ancestor coherent first Tick scalar continuation observed.'),
        ('callbackSelections', 'No source-bound live ActionBase callback pair observed.'),
        ('radioRequests', 'No paired Radio request observed.'),
        ('checkpointCalls', 'No paired checkpoint producer/filter observed.')):
        if not result[key]:result['gaps'].append(message)
    result['gaps'].extend([
        'Full checkpoint values/table/callback identity and complete executor containers/queue must be captured and joined before event-state completion.',
        'The observed virtual callback pair requires exact target/MethodInfo source review and actual callback entry/return evidence; base declaration is not live dispatch evidence.',
        'Radio requests require an explicit mission-to-typed-audio parent/identity bridge and exact playingID stop/completion evidence; timestamp proximity is insufficient.',
        'Controller/resource activation and handle/table/retain lifecycle require their bounded source-owned operands; installed Core equality alone does not prove activation.'
    ])
    result.update(runtimeVerificationComplete=False, playbackVerified=False, audibleOutputVerified=False,
                  nativeValidationReproved=False, engineGettersCalled=False)
    return result


def inspect_session(session, output_dir, *, local_files=False, limits=transport.Limits()):
    """Inspect originals and evaluate new output within one bounded file epoch."""
    session = Path(session).resolve(strict=True); output = Path(output_dir).resolve()
    need('ignored-output-root', any(output.is_relative_to((transport.REPO_ROOT / v).resolve()) for v in ('reports', 'scratch', 'tmp')))
    need('output-outside-original-package', not output.is_relative_to(session) and not session.is_relative_to(output))
    need('new-output-directory', not output.exists())
    snapshot = transport.snapshot_local_inventory if local_files else transport.verify_inventory
    artifacts, inventory = snapshot(session, limits)
    output.mkdir(parents=True)
    report = dict(schema=SCHEMA, status='failed', session=str(session), runtimeVerificationComplete=False,
                  playbackVerified=False, audibleOutputVerified=False, nativeValidationReproved=False,
                  legacyCaptureAdmission=False, inventoryOriginAuthenticated=False,
                  inputMode='current-local-files' if local_files else 'retained-hash-inventory',
                  inventory=inventory,
                  provenanceBoundary='Input hashes describe these reads and entry/exit equality; collector origin, native transactions and omitted runtime effects are not authenticated.')
    try:
        receipt = transport.inspect_session(session, output / 'transport', local_files=local_files, limits=limits)
        need('strict-complete-original-transport', receipt['status'] == ('analyzed' if local_files else 'inspected')
             and receipt['receiptFacts']['allJournalRowsAccounted'] is True)
        profile, summary, hooks = transport.bindings(artifacts, limits)
        need('complete-paired-provider', summary.get('complete') is True and summary.get('returnValuesObserved') is True)
        need('Patrol-profile-only', all(h['name'].startswith('patrol.') for h in hooks))
        layouts = profile.get('readLayouts'); need('source-owned-Patrol-layouts', isinstance(layouts, dict))
        decoded = output / 'transport' / 'decoded.events.jsonl'; digest = hashlib.sha256()
        def rows():
            with decoded.open('rb') as stream:
                for line in stream:
                    need('bounded-decoded-line', len(line) <= limits.output_line_bytes)
                    digest.update(line)
                    yield transport.parse_json(line, 'newly decoded Patrol event')
        report['observations'] = _evaluate(rows(), hooks, layouts)
        final_artifacts, final_inventory = snapshot(session, limits)
        need('all-original-package-inputs-unchanged', artifacts == final_artifacts and inventory == final_inventory)
        report.update(status='inspected-bounded-Patrol-observations', transportReceipt=receipt,
                      originalPackageEntryExitPassed=True, decodedInputs=dict(path=str(decoded), length=decoded.stat().st_size,
                      sha256=digest.hexdigest()), retainedProfileSha256=artifacts['private/mission-trace-build-manifest.json']['sha256'])
    except (ValueError, OSError, KeyError, TypeError) as exc:
        report['failure'] = str(exc)[:2048]
        (output / 'patrol-inspection.json').write_text(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='ascii')
        raise PatrolInspectionError(report['failure']) from exc
    (output / 'patrol-inspection.json').write_text(json.dumps(report, indent=2, ensure_ascii=True, allow_nan=False) + '\n', encoding='ascii')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', required=True, type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--local-files', action='store_true',
                        help='Analyze current collector path/size inventory with fresh local entry/exit hashes; no producer provenance or legacy admission.')
    args = parser.parse_args(argv)
    try:result = inspect_session(args.session, args.output_dir, local_files=args.local_files)
    except (PatrolInspectionError, transport.InspectionError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(result['status'] + '; runtime/playback verification remains incomplete; ' + str(args.output_dir))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
