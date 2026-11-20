"""Compare independently read cache names with recorded admission arguments.

Same-command candidates are retained without inventing an unrecorded _ToSkill
invocation, frame number, stable request lifetime or later cast association.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
from scripts.game_data.battle_input_request_links import project_request_links, _fields

SCHEMA = 'endfield.battle-input-handoff.v1'


def need(ok, message):
    if not ok:
        raise ValueError('battleInputHandoff: '+message)


def project_handoff(inspection, transfer, *, max_candidates=200000):
    links = project_request_links(inspection)
    need(type(max_candidates) is int and max_candidates > 0, 'invalid candidate budget')
    need(transfer.get('schema') == 'endfield.skill-request-transfer-native-audit.v1' and
         transfer.get('status') == 'validated-conditional-carriers' and
         not transfer.get('failures'), 'validated conditional transfer audit required')
    native = inspection['sourceContext']['nativeInputs']
    for name, role in (('GameAssembly.dll', 'gameAssembly'), ('global-metadata.dat', 'metadata')):
        need(transfer['nativeInputs'][name].lower() == native[role]['sha256'].lower(), 'native input mismatch')
    rules = transfer['rules']
    need(all(rules.get(k) is True for k in ('originalPathOnly', 'secondSkillIdReadRequired',
        'nameCarrierContinuityProved', 'viewTargetArgumentBindingProved',
        'normalWin64CalleeSavedRegistersRequired', 'coherentLocalStackRequired')) and
        all(rules.get(k) is False for k in ('firstLookupOutputForwardedToAdmission',
        'pendingDeliveryProved', 'actualCastProved')), 'unsupported transfer rules')
    sites = transfer['callSites']
    selected = [sites[k] for k in ('firstGetterReturnRva', 'secondGetterReturnRva', 'canCastReturnRva')]
    need(all(type(x) is int and x > 0 for x in selected) and len(set(selected)) == 3, 'distinct exact caller sites required')
    byid = {(o['threadId'], o['invocationId']): o for o in inspection['observations']}
    def command(o):
        parent = o['enter'].get('parentInvocationId', 0)
        while parent:
            ancestor = byid[o['threadId'], parent]
            if ancestor['hook'] == 'battle.Command.OnExecute':
                return parent
            parent = ancestor['enter'].get('parentInvocationId', 0)
        return None
    getters = []
    for row in links['getterLinks']:
        o = byid[row['threadId'], row['invocationId']]
        getters.append(dict(**row, callerReturnRva=o['enter'].get('callerGameAssemblyRva')))
    admissions = []
    for o in inspection['observations']:
        if o['hook'] != 'battle.AbilitySystem.CanCastById':
            continue
        e = o['enter']; fields = _fields(e)
        need(type(o.get('booleanReturn')) is bool, 'exact admission Boolean required')
        admissions.append(dict(invocationId=o['invocationId'], threadId=o['threadId'],
            commandInvocationId=command(o), entrySequence=e['sequence'], returnSequence=o['exit']['sequence'],
            callerReturnRva=e.get('callerGameAssemblyRva'), receiverPointer=e['rawArgs'][0],
            skillIdPointer=e['rawArgs'][1], skillId=fields.get('skillId'),
            returned=o['booleanReturn'], actualNewSkillStartProved=False))
    first_index = collections.defaultdict(list)
    admission_index = collections.defaultdict(list)
    for g in getters:
        if g['callerReturnRva'] == sites['firstGetterReturnRva'] and g['commandInvocationId'] is not None:
            first_index[(g['threadId'],g['commandInvocationId'],g['controllerPointer'])].append(g)
    for a in admissions:
        if a['callerReturnRva'] == sites['canCastReturnRva'] and a['commandInvocationId'] is not None:
            admission_index[(a['threadId'],a['commandInvocationId'])].append(a)
    pairs = []; used = 0
    for second in getters:
        if second['callerReturnRva'] != sites['secondGetterReturnRva']:
            continue
        cmd = second['commandInvocationId']
        firsts = [g for g in first_index.get((second['threadId'],cmd,second['controllerPointer']),[])
            if g['returnSequence'] < second['entrySequence']]
        matches = [a for a in admission_index.get((second['threadId'],cmd),[])
            if second['returnSequence'] < a['entrySequence']]
        used += len(firsts) + len(matches)
        need(used <= max_candidates, 'candidate budget exceeded')
        pairs.append(dict(secondGetterInvocationId=second['invocationId'], threadId=second['threadId'],
            commandInvocationId=cmd, secondReturnedPointer=second['returnedPointer'],
            firstGetterCandidates=[dict(invocationId=g['invocationId'], returnedPointer=g['returnedPointer'],
                equalNamePointerObserved=g['returnedPointer'] == second['returnedPointer']) for g in firsts],
            admissionCandidates=[dict(**a, secondNameArgumentEqualityObserved=a['skillIdPointer'] == second['returnedPointer']) for a in matches],
            sameToSkillInvocationProved=False, controllerToAbilityOwnershipProved=False,
            requestIdentityProved=False, crossFrameDeliveryProved=False))
    return dict(schema=SCHEMA, status='observed-conditional-handoff-candidates',
        counts=dict(firstGetterCalls=sum(g['callerReturnRva'] == sites['firstGetterReturnRva'] for g in getters),
            secondGetterCalls=len(pairs), allAdmissions=len(admissions),
            selectedToSkillAdmissions=sum(a['callerReturnRva'] == sites['canCastReturnRva'] for a in admissions),
            secondReadsWithOneFirstAndOneEqualAdmission=sum(len(p['firstGetterCandidates']) == 1 and
                len(p['admissionCandidates']) == 1 and p['admissionCandidates'][0]['secondNameArgumentEqualityObserved'] for p in pairs),
            otherAdmissionCallers=dict(collections.Counter(str(a['callerReturnRva']) for a in admissions
                if a['callerReturnRva'] != sites['canCastReturnRva']))),
        readAdmissionCandidates=pairs, admissionObservations=admissions,
        nativeValidationPerformed=False, runtimeReady=False, fullCrossFrameDeliveryProved=False,
        boundary='Same-command caller/argument observations under separately validated conditional native carriers. '
                 'No closest-time matching, hidden _ToSkill invocation, pending record, frame identity or cast success is invented.')


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('inspection', 'transfer-evidence', 'output'):
        p.add_argument('--'+key, type=Path, required=True)
    a = p.parse_args(argv)
    from scripts.repo_paths import REPO_ROOT
    inputs = [a.inspection, a.transfer_evidence]
    need(a.output.resolve().is_relative_to(REPO_ROOT/'reports') and
         a.output.resolve() not in [p.resolve() for p in inputs], 'output must be a distinct reports path')
    saved = []
    for path in inputs:
        need(path.stat().st_size <= 256*1024**2, 'input byte budget exceeded')
        raw = path.read_bytes(); need(len(raw) <= 256*1024**2, 'input grew beyond byte budget')
        saved.append((path, raw))
    result = project_handoff(*(json.loads(raw) for _,raw in saved))
    need(all(path.read_bytes() == raw for path,raw in saved), 'source changed during projection')
    result['sources'] = [dict(path=str(path.resolve()),sha256=hashlib.sha256(raw).hexdigest()) for path,raw in saved]
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(result['counts']))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
