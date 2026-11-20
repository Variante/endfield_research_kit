"""Classify recorded request readers and retain bounded Skill/Ability identity joins.

Native audit receipts are explicit inputs, matched to the admitted capture's
native hashes. They are reused evidence, not a new native validation. This ledger
never promotes an earlier equal pointer into a delivered request or a lifetime.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
from scripts.game_data.battle_input_request_links import project_request_links, _fields

SCHEMA = 'endfield.battle-input-delivery.v1'


def need(ok, message):
    if not ok:
        raise ValueError('battleInputDelivery: ' + message)


def _bindings(proof, key):
    rows = proof['callerBindings']
    result = {r[key]: r for r in rows}
    need(len(result) == len(rows), 'duplicate native caller binding')
    return result


def _assignment_cases():
    # Explicit portable operands and independent expected writes. None of these
    # counter/input values was recorded by the battle-input session.
    cases = []
    for name, supplied, origin, cost, source, first, second, expected_id, expected_origin, expected_cost, next_counter in (
        ('supplied', 9, 44, 0x3f800000, None, None, None, 9, 44, 0x3f800000, None),
        ('supplied-raw-bits', 2, 0, 0x7fc01234, None, None, None, 2, 0, 0x7fc01234, None),
        ('generated', 0, None, None, 80, 7, 7, 7, 80, 0, 8),
        ('counter-wrap', 0, None, None, 80, 0xffffffff, 0xffffffff, 0xffffffff, 80, 0, 0),
        ('counter-zero', 0, None, None, 80, 0, 0, 0, 80, 0, 1),
        ('distinct-counter-reads', 0, None, None, 80, 7, 10, 7, 80, 0, 11)):
        cases.append(dict(id='assignment-'+name, operation='assign-skill-cast-info',
            inputs=dict(input_id=supplied, input_origin=origin, input_cost_bits=cost,
                        source_skill=source, counter=first, counter_for_increment=second),
            expected=dict(skillCastId=expected_id, castOriginSkill=expected_origin,
                costBits=expected_cost, counterWriteRequested=supplied == 0,
                nextCounter=next_counter, globallyUniqueCastIdProved=False, requestDeliveryProved=False)))
    return cases


def project_delivery(inspection, delivery, identity, *, max_identity_candidates=200000):
    need(type(max_identity_candidates) is int and max_identity_candidates > 0, 'invalid identity candidate budget')
    links = project_request_links(inspection)  # Admission, normal pairs and full enclosure checks.
    files = inspection['sourceContext']['nativeInputs']
    for proof, schema in ((delivery, 'endfield.skill-request-delivery-native-audit.v1'),
                          (identity, 'endfield.skill-cast-identity-native-audit.v1')):
        need(proof.get('schema') == schema and
             proof.get('status') == 'validated-conditional-fragments', 'matching conditional native audit required')
        need(not proof.get('failures'), 'native audit failures present')
        for name, role in (('GameAssembly.dll', 'gameAssembly'), ('global-metadata.dat', 'metadata')):
            need(proof['nativeInputs'][name].lower() == files[role]['sha256'].lower(), 'native input mismatch')
    need(all(delivery['rules'].get(k) is True for k in ('originalPathOnly',
             'getterResultForwardedAsSkillId', 'lookupOutParameterByref', 'lookupFalseReturnsFalse')) and
         delivery['rules'].get('actualCastProved') is False, 'unsupported delivery rules')
    need(identity['rules'].get('originalPathOnly') is True and
         identity['rules'].get('abilityInitStoresSourceSkill') is True and
         identity['rules'].get('counterIndependentlyReloadedForIncrement') is True and
         identity['rules'].get('zeroInputIdReadsCounterThenRequestsWrappingIncrement') is True and
         identity['rules'].get('requestDeliveryProved') is False and
         identity['rules'].get('nonzeroInputIdCopiesIdOriginAndCostBits') is True and
         identity['rules'].get('zeroInputOriginUsesSourceSkill') is True and
         type(identity['rules'].get('zeroInputCostBits')) is int and
         identity['rules']['zeroInputCostBits'] == 0 and
         type(identity['rules'].get('counterBits')) is int and
         identity['rules']['counterBits'] == 32, 'unsupported identity rules')
    callers = _bindings(delivery, 'returnRva')
    cast_callers = _bindings(identity, 'role')
    obs = {(o['threadId'], o['invocationId']): o for o in inspection['observations']}
    readers = []
    for g in links['getterLinks']:
        event = obs[g['threadId'], g['invocationId']]['enter']
        site = callers.get(event.get('callerGameAssemblyRva'))
        readers.append(dict(**g, callerBinding=site, callerClassified=site is not None,
            category=site['category'] if site else 'unclassified',
            getterToLookupArgumentFragmentProved=bool(site and site['ownerRole'] == 'owner'
                and site['targetRole'] == 'getter'),
            lookupResultObserved=False, actualExecutionProved=False))
    inits = []
    init_index = collections.defaultdict(list)
    cases = []
    for o in inspection['observations']:
        if o['hook'] != 'battle.Ability.Init':
            continue
        before, after = _fields(o['enter']), _fields(o['exit'])
        ability, skill = o['enter']['rawArgs'][:2]
        need(type(ability) is int and 0 < ability < 2**64 and
             type(skill) is int and 0 < skill < 2**64, 'exact nonnull Init arguments required')
        need(all(type(fields.get(key)) is int for fields,key in
            ((before,'abilityIdentity'),(after,'abilityIdentity'),
             (before,'skillIdentityFromArgument'),(after,'skillIdentity'))) and
             before.get('abilityIdentity') == after.get('abilityIdentity') == ability and
             before.get('skillIdentityFromArgument') == skill and
             after.get('skillIdentity') == skill, 'Init source argument/receiver binding differs')
        need(type(after.get('abilityInstanceUid')) is int and
             0 <= after['abilityInstanceUid'] < 2**32, 'exact Init UID required')
        site = cast_callers['abilityInit']
        classified = o['enter'].get('callerGameAssemblyRva') == site['returnRva']
        row = dict(invocationId=o['invocationId'], threadId=o['threadId'],
            entrySequence=o['enter']['sequence'], returnSequence=o['exit']['sequence'],
            abilityIdentity=ability, abilityInstanceUid=after['abilityInstanceUid'],
            sourceSkill=skill, sourceArgumentStoreObserved=True,
            callerBinding=site if classified else None, lifetimeContinuityProved=False)
        inits.append(row)
        init_index[(row['threadId'], ability, row['abilityInstanceUid'], skill)].append(row)
        # The argument-to-field observation is independent of its upstream caller.
        cases.append(dict(id='init-'+str(o['threadId'])+'-'+str(o['invocationId']),
            operation='ability-init-source-binding', inputs=dict(source_skill=skill),
            expected=dict(sourceSkill=after['skillIdentity'], ownershipLifetimeProved=False,
                          castOccurrenceCreatedProved=False)))
    casts = []
    groups = collections.defaultdict(list)
    candidate_count = 0
    stable_keys = ('abilityIdentity', 'abilityInstanceUid', 'skillIdentity',
                   'skillCastId', 'castOriginSkillIdentity')
    for b in links['beforeCastLinks']:
        o = obs[b['threadId'], b['invocationId']]
        before, after = _fields(o['enter']), _fields(o['exit'])
        need(all(k in before and k in after and type(before[k]) is int and type(after[k]) is int for k in stable_keys),
             'exact BeforeCast identities required')
        need(all(before[k] == after[k] for k in stable_keys), 'BeforeCast identity changed within pair')
        need(before['abilityIdentity'] == o['enter']['rawArgs'][0], 'BeforeCast receiver differs')
        for key in stable_keys:
            bits = 32 if key in ('skillCastId', 'abilityInstanceUid') else 64
            need(0 <= before[key] < 2**bits, 'BeforeCast identity carrier out of range')
        site = cast_callers['beforeCast']
        classified = o['enter'].get('callerGameAssemblyRva') == site['returnRva']
        candidates = [i for i in init_index[(b['threadId'], before['abilityIdentity'],
            before['abilityInstanceUid'], before['skillIdentity'])]
            if i['returnSequence'] < b['entrySequence']]
        candidate_count += len(candidates)
        need(candidate_count <= max_identity_candidates, 'identity candidate budget exceeded')
        row = dict(**b, occurrenceKey=[b['threadId'], b['invocationId']],
            callerBinding=site if classified else None,
            earlierInitSnapshotCandidates=[i['invocationId'] for i in candidates],
            observedSourceOriginEqual=before['skillIdentity'] == before['castOriginSkillIdentity'],
            lifetimeContinuityProved=False, assignInputBranchObserved=False,
            crossFrameRequestDeliveryProved=False)
        casts.append(row)
        groups[(before['abilityIdentity'], before['abilityInstanceUid'], before['skillIdentity'])].append(row)
    repeated = []
    for (ability, uid, skill), rows in groups.items():
        ids = sorted({r['abilitySnapshot']['skillCastId'] for r in rows})
        if len(ids) > 1:
            repeated.append(dict(abilityIdentity=ability, abilityInstanceUid=uid,
                sourceSkill=skill, observedCastIds=ids,
                observationKeys=[r['occurrenceKey'] for r in rows], lifetimeContinuityProved=False))
    counts = dict(getters=len(readers), getterCategories=dict(collections.Counter(r['category'] for r in readers)),
        directGetterToLookupFragments=sum(r['getterToLookupArgumentFragmentProved'] for r in readers),
        abilityInit=len(inits), initWithKnownCaller=sum(r['callerBinding'] is not None for r in inits),
        beforeCast=len(casts), beforeCastWithKnownCaller=sum(r['callerBinding'] is not None for r in casts),
        beforeCastWithEarlierInitSnapshot=sum(bool(r['earlierInitSnapshotCandidates']) for r in casts),
        beforeCastWithoutCommand=sum(r['commandInvocationId'] is None for r in casts),
        repeatedAbilityTupleWithDifferentCastIds=len(repeated))
    ledger = dict(schema=SCHEMA, status='observed-conditional-links', counts=counts,
        inputAdmissionInherited=True, nativeValidationPerformed=False, getterLinks=readers,
        initBindings=inits, beforeCastLinks=casts, repeatedAbilityTuples=repeated,
        fullCrossFrameDeliveryProved=False, runtimeReady=False,
        gaps=['Getter lookup output, selected pending record and its delivery were not observed together.',
              'Sequence order and separate commands are not frame IDs or authenticated intervening write continuity.',
              'BeforeCast caller identifies the TryCastSkill tail, not its unrecorded upstream caller.',
              'Earlier equal pointer/UID/source snapshots are candidates; no allocation lifetime is inferred.',
              'Cast IDs and source-origin equality do not reveal AssignSkillCastInfo inputs or counter branch.'])
    origins = {c['id']: 'observed-init-argument-and-return-field' for c in cases}
    fixtures = _assignment_cases()
    origins.update({c['id']: 'portable-native-rule-fixture-not-recorded' for c in fixtures})
    case_doc = dict(schema='endfield.conditional-timing-cases.v1', conditions=dict(
        original_path='Selected original Init store and AssignSkillCastInfo paths, normal returns and native carrier continuity premises; other method effects are outside this projection.',
        operand_binding='Init cases use admitted receiver/argument/returned field records. Assignment cases are explicit portable fixtures, including independent counter reads, not recorded operands.',
        delta_and_sample_sources='No timing delta; exact UInt64 reference carriers at observed boundaries only.',
        precision='Opaque integer references, UInt32 wrapping increment and unchanged cost bits; no lifetime, delivery or unique occurrence inference.'),
        cases=cases+fixtures, caseOrigins=origins,
        boundary='Observed argument-to-field cases and separately labelled portable identity fixtures; not full input replay.')
    return ledger, case_doc


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('inspection', 'delivery-evidence', 'identity-evidence', 'output', 'cases-output'):
        p.add_argument('--'+name, type=Path, required=True)
    a = p.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    inputs = [a.inspection, a.delivery_evidence, a.identity_evidence]
    outputs = [a.output, a.cases_output]
    need(len({x.resolve() for x in outputs}) == 2 and
         all(x.resolve().is_relative_to(REPO_ROOT/'reports') and
             x.resolve() not in [i.resolve() for i in inputs] for x in outputs),
         'distinct reports outputs must not replace inputs')
    sources = []
    docs = []
    for path in inputs:
        need(path.stat().st_size <= 256*1024**2, 'input byte budget exceeded')
        raw = path.read_bytes()
        need(len(raw) <= 256*1024**2, 'input grew beyond budget')
        sources.append((path, raw))
        docs.append(json.loads(raw))
    results = project_delivery(*docs)
    need(all(path.read_bytes() == raw for path, raw in sources), 'inputs changed during projection')
    refs = [dict(path=str(path.resolve()), sha256=hashlib.sha256(raw).hexdigest()) for path, raw in sources]
    for path, result in zip(outputs, results):
        result['sources'] = refs
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(results[0]['counts']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
