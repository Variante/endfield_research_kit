"""Same-command Center admission/BeforeCast/cleanup candidates, offline only.

The hidden _ToSkill, _DoCastSkill and TryCastSkill invocations were not hooked.
Sequence/enclosure and native caller-site observations do not manufacture those
invocations, a shared blackboard, a TryCast Boolean, or a cross-frame lifetime.
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path

from scripts.game_data.battle_input_request_links import project_request_links, _fields
from scripts.game_data.battle_input_handoff import project_handoff
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.battle-input-center-links.v1'
MAX_INPUT_BYTES=256*1024**2


def need(condition,message):
    if not condition:raise ValueError('battleInputCenterLinks: '+message)


def _sha(value):
    need(type(value)is str and len(value)==64 and all(c in '0123456789abcdefABCDEF'for c in value),'exact SHA256 required')
    return value.lower()


def _integer(value,*,zero=False):
    return type(value)is int and (0 if zero else 1)<=value<2**64


def _identity(value):
    need(type(value)is list and len(value)==4 and _integer(value[0],zero=True)and _integer(value[3])and all(type(value[i])is str and value[i]for i in(1,2)),'exact native method identity required')
    return value


def _consumer(inspection,audit):
    need(audit.get('schema')=='endfield.skill-blackboard-consumer-native-audit.v1'and audit.get('status')=='validated-conditional-fragments'and audit.get('failures')==[],'validated conditional consumer audit required')
    for name,role in [('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata')]:
        need(_sha(audit['nativeInputs'][name])==_sha(inspection['sourceContext']['nativeInputs'][role]['sha256']),'consumer native input mismatch: '+name)
    rules=audit['rules']
    need(type(rules)is dict,'consumer rules object required')
    for key in ('originalPathOnly','normalWin64HelperReturnRequired','directTryCastRouteProved','cleanupReloadsBlackboard','cleanupClearsSkillEndCallbackOnly','cleanupThenReloadsEntityThenAbility','clearRequestTailForwardsToComboClear'):
        need(rules.get(key)is True,'required consumer premise missing: '+key)
    for key in ('sameWriterConsumerLiveBlackboardProved','runtimeFSMSelectionProved','blackboardToPendingJoinProved','tryCastBoolUsedForCleanupBranch','currentSessionBlackboardIdentityProved'):
        need(rules.get(key)is False,'consumer boundary changed: '+key)
    bindings=audit['callerBindings'];need(type(bindings)is list and len(bindings)<=32 and all(type(r)is dict for r in bindings),'bounded consumer caller bindings required')
    selected={}
    for role in ('directTryCast','postCastClearRequest','clearRequestTailAlias'):
        rows=[r for r in bindings if r.get('role')==role];need(len(rows)==1,'unique consumer binding required: '+role);selected[role]=rows[0]
    direct,clear,tail=(selected[k]for k in ('directTryCast','postCastClearRequest','clearRequestTailAlias'))
    for row in selected.values():
        _identity(row['owner']);_identity(row['target']);need(_integer(row['siteRva']),'exact caller instruction RVA required')
    owner=['Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterSkillState','_DoCastSkill']
    need(direct['owner'][1:3]==owner and clear['owner']==direct['owner'],'same selected CenterSkillState consumer owner required')
    need(direct['target'][1:3]==['Beyond.Gameplay.Core.AbilitySystem','TryCastSkill'],'selected direct TryCast target required')
    need(clear['target'][1:3]==['Beyond.Gameplay.Core.AbilitySystem','ClearSkillRequest'],'selected ClearSkillRequest target required')
    need(tail['owner']==clear['target']and tail['target'][1:3]==['Beyond.Gameplay.Core.AbilitySystem+ComboController','ClearSkillRequest'],'Clear wrapper-to-observed Combo.Clear join required')
    for row in (direct,clear):
        need(_integer(row['returnRva'])and row['returnRva']==row['siteRva']+5 and row.get('tailForwardPreservesCallerReturn')is False,'ordinary direct-call return binding required')
    need(tail['returnRva']is None and tail.get('tailForwardPreservesCallerReturn')is True,'tail-forwarded caller return proof required')
    return selected


def project_center_links(inspection,transfer,consumer,*,max_observations=50000,max_candidates=200000):
    need(type(max_observations)is int and 0<max_observations<=50000 and type(max_candidates)is int and 0<max_candidates<=2000000,'invalid bounded observation/candidate budget')
    need(all(type(v)is dict for v in(inspection,transfer,consumer)),'JSON input objects required')
    context=inspection.get('sourceContext');need(type(context)is dict and type(context.get('inspection'))is dict and type(context['inspection'].get('receiptFacts'))is dict,'inspection source/receipt objects required')
    need(type(transfer.get('rules'))is dict,'transfer rules object required')
    for name,role in [('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata')]:
        need(_sha(transfer['nativeInputs'][name])==_sha(context['nativeInputs'][role]['sha256']),'transfer native input mismatch: '+name)
    observations=inspection.get('observations');need(type(observations)is list and 0<len(observations)<=max_observations,'bounded observation list required')
    for o in observations:
        need(type(o)is dict and type(o.get('enter'))is dict and type(o.get('exit'))is dict,'closed observation event objects required')
        need(_integer(o['enter'].get('parentInvocationId',0),zero=True),'exact parent invocation integer required')
    # Reuse the maintained complete/healthy/accounted receipt, normal-pair and
    # same-thread enclosure admission, then the native-bound handoff admission.
    request=project_request_links(inspection,max_observations=max_observations,max_candidate_links=max_candidates)
    handoff=project_handoff(inspection,transfer,max_candidates=max_candidates)
    bindings=_consumer(inspection,consumer)
    sites=dict(admissionReturnRva=transfer['callSites']['canCastReturnRva'],postCastClearReturnRva=bindings['postCastClearRequest']['returnRva'])
    need(all(_integer(value)for value in sites.values()),'exact selected caller sites required')
    byid={(o['threadId'],o['invocationId']):o for o in observations}
    def command(o):
        parent=o['enter'].get('parentInvocationId',0)
        while parent:
            a=byid[o['threadId'],parent]
            if a['hook']=='battle.Command.OnExecute':return parent
            parent=a['enter'].get('parentInvocationId',0)
        return None
    def base(o):
        e,x=o['enter'],o['exit'];need(_integer(e['rawArgs'][0],zero=True),'exact receiver pointer bits required')
        return dict(invocationId=o['invocationId'],threadId=o['threadId'],commandInvocationId=command(o),entrySequence=e['sequence'],returnSequence=x['sequence'],callerReturnRva=e.get('callerGameAssemblyRva'),receiverPointer=e['rawArgs'][0])
    before=[];clears=[]
    for o in observations:
        if o['hook']=='battle.Ability.BeforeCast':
            row=base(o);fields=_fields(o['enter'])
            for label in ('abilityIdentity','abilityInstanceUid','skillIdentity','skillCastId','castOriginSkillIdentity'):
                value=fields.get(label)
                need(value is None or _integer(value,zero=True),'exact BeforeCast identity bits required: '+label);row[label]=value
            before.append(row)
        elif o['hook']=='battle.Combo.Clear':clears.append(base(o))
    before.sort(key=lambda r:(r['entrySequence'],r['threadId'],r['invocationId']));clears.sort(key=lambda r:(r['entrySequence'],r['threadId'],r['invocationId']))
    before_index=collections.defaultdict(list);clear_index=collections.defaultdict(list)
    for r in before:
        if r['commandInvocationId']is not None:before_index[r['threadId'],r['commandInvocationId']].append(r)
    for r in clears:
        if r['commandInvocationId']is not None and r['callerReturnRva']==sites['postCastClearReturnRva']:clear_index[r['threadId'],r['commandInvocationId']].append(r)
    getters={(r['threadId'],r['invocationId']):r for r in request['getterLinks']};handoff_index=collections.defaultdict(list)
    for pair in handoff['readAdmissionCandidates']:
        for admission in pair['admissionCandidates']:
            g=getters[pair['threadId'],pair['secondGetterInvocationId']]
            handoff_index[pair['threadId'],admission['invocationId']].append(dict(secondGetterInvocationId=pair['secondGetterInvocationId'],controllerPointer=g['controllerPointer'],secondReturnedPointer=pair['secondReturnedPointer'],secondNameArgumentEqualityObserved=admission['secondNameArgumentEqualityObserved'],firstGetterCandidates=pair['firstGetterCandidates'],sameHiddenToSkillInvocationProved=False))
    used=0
    def charge(count):
        nonlocal used
        used+=count;need(used<=max_candidates,'candidate comparison/output budget exceeded')
    rows=[]
    admissions=[r for r in handoff['admissionObservations']if r['callerReturnRva']==sites['admissionReturnRva']]
    for admission in admissions:
        need(_integer(admission['receiverPointer'],zero=True)and _integer(admission['skillIdPointer'],zero=True),'exact admission pointer bits required')
        key=(admission['threadId'],admission['commandInvocationId']);has_command=admission['commandInvocationId']is not None
        possible_before=before_index.get(key,[])if has_command else[];possible_clear=clear_index.get(key,[])if has_command else[]
        charge(len(possible_before)+len(possible_clear))
        bmatches=[r for r in possible_before if admission['returnSequence']<r['entrySequence']]
        cmatches=[r for r in possible_clear if admission['returnSequence']<r['entrySequence']]
        hmatches=handoff_index.get((admission['threadId'],admission['invocationId']),[]);charge(len(hmatches))
        cast_candidates=[]
        for before_row in bmatches:
            charge(len(cmatches));cast_candidates.append(dict(**before_row,laterSelectedClearCandidates=[r for r in cmatches if before_row['returnSequence']<r['entrySequence']],sameHiddenDoCastInvocationProved=False,tryCastBooleanObserved=False,blackboardInstanceIdentityProved=False))
        rows.append(dict(admission=admission,sameCommandObserved=has_command,handoffCandidates=hmatches,beforeCastCandidates=cast_candidates,selectedClearCandidates=cmatches,sameHiddenToSkillInvocationProved=False,sameHiddenDoCastInvocationProved=False,requestToCastCausalityProved=False,blackboardInstanceIdentityProved=False,tryCastBooleanObserved=False,crossFrameDeliveryProved=False))
    counts=dict(selectedAdmissions=len(rows),selectedAdmissionsWithCommand=sum(r['sameCommandObserved']for r in rows),selectedAdmissionsReturnedTrue=sum(r['admission']['returned']is True for r in rows),allBeforeCastObservations=len(before),allComboClearObservations=len(clears),selectedPostCastClearObservations=sum(r['callerReturnRva']==sites['postCastClearReturnRva']for r in clears),admissionsWithBeforeCastCandidate=sum(bool(r['beforeCastCandidates'])for r in rows),admissionsWithSelectedClearCandidate=sum(bool(r['selectedClearCandidates'])for r in rows),beforeCastCandidateEdges=sum(len(r['beforeCastCandidates'])for r in rows),selectedClearCandidateEdges=sum(len(r['selectedClearCandidates'])for r in rows),beforeCastToClearCandidateEdges=sum(len(b['laterSelectedClearCandidates'])for r in rows for b in r['beforeCastCandidates']),admissionsWithMultipleBeforeCastCandidates=sum(len(r['beforeCastCandidates'])>1 for r in rows),admissionsWithMultipleClearCandidates=sum(len(r['selectedClearCandidates'])>1 for r in rows),candidateComparisonsAndOutputEdges=used)
    return dict(schema=SCHEMA,status='observed-same-command-center-candidates',counts=counts,selectedCallerSites=sites,consumerCallerBindings=bindings,admissionCandidateGroups=rows,inputAdmissionInherited=True,transportReproved=False,nativeValidationPerformed=False,runtimeReady=False,fullCrossFrameDeliveryProved=False,boundary='All same-thread, same-command, ordered candidates are retained. Native direct-call and tail-wrapper facts classify caller sites; they do not identify a hidden invocation, TryCast Boolean, shared blackboard instance, uninterrupted object lifetime or runtime request delivery. No nearest-time selection or absent-call rejection is used.')


def inspect_center_links(inspection_path,transfer_path,consumer_path,*,max_candidates=200000):
    saved=[]
    for role,path in [('inspection',inspection_path),('transferEvidence',transfer_path),('consumerEvidence',consumer_path)]:
        path=Path(path);need(path.stat().st_size<=MAX_INPUT_BYTES,'input byte budget exceeded: '+role)
        with path.open('rb')as stream:raw=stream.read(MAX_INPUT_BYTES+1)
        need(len(raw)<=MAX_INPUT_BYTES,'input grew beyond byte budget: '+role);saved.append((role,path,raw))
    result=project_center_links(*(json.loads(raw)for _,_,raw in saved),max_candidates=max_candidates)
    for role,path,raw in saved:
        need(path.stat().st_size<=MAX_INPUT_BYTES,'input grew at bookend: '+role)
        with path.open('rb')as stream:after=stream.read(MAX_INPUT_BYTES+1)
        need(after==raw,'source changed during projection: '+role)
    result['sourceInputs']=[dict(role=role,path=str(path.resolve()),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())for role,path,raw in saved]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('inspection','transfer-evidence','consumer-evidence','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--max-candidates',type=int,default=200000);args=parser.parse_args(argv)
    try:
        inputs=[args.inspection,args.transfer_evidence,args.consumer_evidence]
        need(args.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve())and args.output.resolve()not in[p.resolve()for p in inputs],'output must be a distinct reports path')
        result=inspect_center_links(*inputs,max_candidates=args.max_candidates)
    except(OSError,ValueError,KeyError,TypeError,IndexError)as error:
        print(json.dumps(dict(schema=SCHEMA,status='blocked',diagnostics=[str(error)[:1600]])));return 2
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(status=result['status'],counts=result['counts'])));return 0


if __name__=='__main__':raise SystemExit(main())
