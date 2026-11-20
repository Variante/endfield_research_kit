"""Project admitted Center pairs and payload checks without asynchronous joins.

Recorded addresses establish equality at sampled endpoints. Event adjacency,
constructor history and equal bytes do not prove uninterrupted object lifetime.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
from scripts.game_data.battle_input_request_links import project_request_links, _fields
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.battle-center-observations.v3'
PREFIX='battle.Center.'
MAX_BYTES=256*1024**2


def need(ok,message):
    if not ok:raise ValueError('battleCenter: '+message)


def _snapshot(event):
    fields=[f for f in event['fields'] if f['label']=='inputSnapshot']
    if not fields:return None
    need(len(fields)==1,'duplicate input snapshot')
    f=fields[0]
    if f.get('state')!=1:return None
    raw=bytes.fromhex(f['rawHex'])
    need(f.get('byteCount')==len(raw)==88,'input snapshot must cover complete 88-byte value')
    return dict(address=f['raw64'],rawHex=raw.hex(),allZero=not any(raw))


def _native(inspection,proof,schema,status,rules):
    need(proof.get('schema')==schema and proof.get('status')==status and not proof.get('failures'),
         'matching successful native audit required: '+schema)
    for name,role in [('GameAssembly.dll','gameAssembly'),('global-metadata.dat','metadata')]:
        need(proof['nativeInputs'][name].lower()==inspection['sourceContext']['nativeInputs'][role]['sha256'].lower(),
             'native input mismatch: '+name)
    need(all(proof['rules'].get(k)is True for k in rules),'required native rules missing')


def project(inspection,writer,fsm,lifecycle,dispatch):
    need(inspection.get('sourceContext',{}).get('recipeName')=='battle-center-fsm','Center recipe admission required')
    # Recheck normal pairs and all parent enclosures; do not trust the separately
    # serialized ancestors array, or infer absent descendants as rejection.
    project_request_links(inspection)
    _native(inspection,writer,'endfield.skill-input-blackboard-native-audit.v1','validated-conditional-writer',
            ('originalPathOnly',))
    _native(inspection,fsm,'endfield.skill-center-fsm-native-audit.v1','validated-conditional-fragments',
            ('castResultIsOriginalSourceOrNull','secondCastResultUnused','nullAiComPreservesOldFields'))
    _native(inspection,lifecycle,'endfield.skill-center-lifecycle-native-audit.v1','validated-conditional-lifecycle',
            ('stopAndClearDisposeBeforeZero88','blackboardClearAllOriginalNoOp'))
    _native(inspection,dispatch,'endfield.skill-center-dispatch-native-audit.v9','validated-conditional-fragments',
            ('conditionFallbackForwardsStoredTargetAndMethodInfo','conditionFallbackRequiresThreeTargetMismatches'))
    fallback=[r for r in dispatch['callSites'] if r.get('role')=='conditionDelegateFallback']
    need(len(fallback)==1,'one proved condition fallback callsite required')
    fallback=fallback[0]
    need(fallback['callHex']=='ffd0' and fallback['callKind']=='indirect'
         and type(fallback['returnRva'])is int and fallback['returnRva']==fallback['callRva']+2,
         'condition fallback must be the proved indirect call return')
    obs=inspection['observations'];byid={(o['threadId'],o['invocationId']):o for o in obs}
    by_enter={o['enter']['sequence']:o for o in obs}
    def ancestors(o):
        parent=o['enter'].get('parentInvocationId',0);result=[]
        while parent:
            a=byid[o['threadId'],parent];result.append(a);parent=a['enter'].get('parentInvocationId',0)
        return result
    def ref(o):
        return dict(threadId=o['threadId'],invocationId=o['invocationId'],hook=o['hook'],
            entrySequence=o['enter']['sequence'],returnSequence=o['exit']['sequence'],
            receiverPointer=o['enter']['rawArgs'][0],callerReturnRva=o['enter'].get('callerGameAssemblyRva'))
    getters=collections.defaultdict(list);children=collections.defaultdict(list)
    for o in obs:
        for a in ancestors(o):children[a['threadId'],a['invocationId']].append(o)
        if o['hook']==PREFIX+'GetBlackboard':
            parent=byid.get((o['threadId'],o['enter'].get('parentInvocationId')))
            need(parent is not None and parent['hook']==PREFIX+'ToSkill','getter needs direct recorded ToSkill parent')
            getters[parent['threadId'],parent['invocationId']].append(o)
    sites=writer['callSites'];get_roles={sites['getter1Return']:'first',sites['getter2Return']:'second'}
    need(len(get_roles)==2,'distinct getter callsites required')
    admissions=[];entries=[];constructors=[];resets=[];cases=[];origins={};condition_calls=[]
    for o in obs:
        if o['hook']==PREFIX+'ToSkill':
            matched=o['enter'].get('callerGameAssemblyRva')==fallback['returnRva']
            mask=o['enter'].get('argsReadMask',0)
            need(type(mask)is int and 0<=mask<256,'ordinary argument-read mask required')
            method_observed=matched and bool(mask&2)
            method_pointer=o['enter']['rawArgs'][1] if method_observed else None
            if method_observed:
                need(type(method_pointer)is int and 0<=method_pointer<2**64,'recorded MethodInfo pointer bits required')
            condition_calls.append(dict(**ref(o),returned=o['booleanReturn'],
                route='condition-delegate-fallback' if matched else 'unclassified-caller',
                directCallsiteMatched=matched,transitionIdentityObserved=False,
                checkerIdentityObserved=False,selectionResultObserved=False,
                methodInfoArgumentObserved=method_observed,methodInfoPointer=method_pointer,
                methodInfoContentsObserved=False,methodInfoLifetimeProved=False))
            gs=getters[o['threadId'],o['invocationId']]
            if not gs and not o.get('booleanReturn'):continue
            rows=[]
            for g in sorted(gs,key=lambda x:x['enter']['sequence']):
                role=get_roles.get(g['enter'].get('callerGameAssemblyRva'))
                need(role is not None,'unclassified getter callsite')
                rows.append(dict(**ref(g),role=role,returnedPointer=g['exit']['returnValue'],
                    methodInfoPointer=g['enter']['rawArgs'][1],sameMachineArgument=g['enter']['rawArgs'][0]==o['enter']['rawArgs'][0]))
            next_event=by_enter.get(o['exit']['sequence']+1)
            adjacent=None
            if next_event and next_event['hook']==PREFIX+'OnEnter' and next_event['threadId']==o['threadId']:
                bb=_fields(next_event['enter']).get('blackboardIdentity')
                adjacent=dict(**ref(next_event),sampledBlackboardPointer=bb,
                    getterResultEqualities=[g['returnedPointer']==bb for g in rows],causalDeliveryProved=False)
            admissions.append(dict(**ref(o),returned=o['booleanReturn'],getters=rows,
                twoOrderedGetterResults=[g['role']for g in rows]==['first','second'],
                immediatelyFollowingObservedEntry=adjacent,runtimeContextContentsObserved=False))
        elif o['hook']==PREFIX+'OnEnter':
            descendants=children[o['threadId'],o['invocationId']]
            casts=[]
            for d in descendants:
                if d['hook']!=PREFIX+'DoCast':continue
                b,x=_fields(d['enter']),_fields(d['exit'])
                before=[a for a in children[d['threadId'],d['invocationId']] if a['hook']=='battle.Ability.BeforeCast']
                casts.append(dict(**ref(d),sameStateReceiver=d['enter']['rawArgs'][0]==o['enter']['rawArgs'][0],
                    before=b,after=x,inputBefore=_snapshot(d['enter']),inputAfter=_snapshot(d['exit']),
                    beforeCastDescendants=[dict(**ref(a),fields=_fields(a['enter']))for a in before],
                    tryCastBooleanObserved=False))
            entries.append(dict(**ref(o),fromStateIdBits32=o['enter']['rawArgs'][1]&0xffffffff,
                before=_fields(o['enter']),after=_fields(o['exit']),inputBefore=_snapshot(o['enter']),
                inputAfter=_snapshot(o['exit']),doCastDescendants=casts,synchronousEnclosureObserved=True))
        elif o['hook']==PREFIX+'StateInit':
            args=o['enter']['rawArgs'];before=_fields(o['enter']);after=_fields(o['exit'])
            source=args[2];stored=after.get('blackboardIdentity');ai=args[3]
            constructors.append(dict(**ref(o),stateIdBits32=args[1]&0xffffffff,sourceBlackboardPointer=source,
                suppliedAiPointer=ai,before=before,after=after,storedSourceEquality=source==stored))
            # Only the observed null-AI branch supplies all needed operands.
            if ai==0 and stored in (0,source) and before.get('aiIdentity')==after.get('aiIdentity') and before.get('entityIdentity')==after.get('entityIdentity'):
                token=lambda value:None if value==0 else str(value)
                effects=[dict(op='cast-request',ordinal=1,targetType='CenterBlackboard',sourceToken=token(source),resultToken=token(stored)),
                    dict(op='write',stateToken=str(args[0]),field='m_blackboard',valueToken=token(stored)),
                    dict(op='cast-request',ordinal=2,targetType='CenterBlackboard',sourceToken=token(source),resultUnused=True),
                    dict(op='write-barrier-request',stateToken=str(args[0]),field='m_blackboard')]
                case=dict(id='observed-init-'+str(o['invocationId']),operation='center-state-init-after-base',
                    inputs=dict(state_token=str(args[0]),source_blackboard_token=token(source),first_cast_result_token=token(stored),ai_component_token=None,entity_read_token=None),
                    expected=_result(effects))
                cases.append(case);origins[case['id']]=dict(kind='recorded-operands-conditional-original-path',observation=ref(o),helperEffectsObserved=False)
        elif o['hook']in(PREFIX+'BlackboardStop',PREFIX+'BlackboardClear'):
            before,after=_snapshot(o['enter']),_snapshot(o['exit']);name=o['hook'].removeprefix(PREFIX+'Blackboard')
            resets.append(dict(**ref(o),operation=name,before=before,after=after,
                sameStorageAddress=bool(before and after and before['address']==after['address'])))
            if before and after and before['address']==after['address']:
                bb=str(o['enter']['rawArgs'][0]);effects=[dict(op='dispose-request',blackboardToken=bb,field='skillInputData'),
                    dict(op='zero-bytes',blackboardToken=bb,field='skillInputData',byteCount=88)]
                case=dict(id='observed-reset-'+str(o['invocationId']),operation='center-reset-input-bytes',
                    inputs=dict(blackboard_token=bb,operation=name,input_before_hex=before['rawHex']),
                    expected=dict(_result(effects),inputAfterHex=after['rawHex']))
                cases.append(case);origins[case['id']]=dict(kind='recorded-payload-endpoints-conditional-original-path',observation=ref(o),disposeEffectObserved=False)
    all_before=[o for o in obs if o['hook']=='battle.Ability.BeforeCast']
    for e in entries:
        e['priorConstructorEndpointMatches']=[]
        for c in constructors:
            if c['receiverPointer']==e['receiverPointer'] and c['returnSequence']<e['entrySequence']:
                changes={key:dict(constructorReturn=c['after'][key],onEnter=e['before'][key])
                    for key in ('blackboardIdentity','aiIdentity','entityIdentity')
                    if key in c['after'] and key in e['before'] and c['after'][key]!=e['before'][key]}
                e['priorConstructorEndpointMatches'].append(dict(invocationId=c['invocationId'],
                    changedFields=changes,sameLiveInstanceProved=False,interveningWriterIdentified=False))
    enclosed=sum(len(c['beforeCastDescendants'])for e in entries for c in e['doCastDescendants'])
    counts=dict(observations=len(obs),toSkillTrue=sum(o.get('booleanReturn')is True for o in obs if o['hook']==PREFIX+'ToSkill'),
        toSkillFalse=sum(o.get('booleanReturn')is False for o in obs if o['hook']==PREFIX+'ToSkill'),
        getterPairs=sum(map(len,getters.values())),onEnter=len(entries),doCast=sum(len(e['doCastDescendants'])for e in entries),
        beforeCastWithinDoCast=enclosed,beforeCastOutsideDoCast=len(all_before)-enclosed,constructors=len(constructors),
        refreshPairs=sum(o['hook']==PREFIX+'RefreshData'for o in obs),resets=len(resets),
        nonzeroResetInputs=sum(r['before']is not None and not r['before']['allZero']for r in resets),
        zeroResetOutputs=sum(r['after']is not None and r['after']['allZero']for r in resets),regressionCases=len(cases))
    counts.update(toSkillConditionFallback=sum(r['directCallsiteMatched']for r in condition_calls),
        toSkillUnclassifiedCaller=sum(not r['directCallsiteMatched']for r in condition_calls),
        conditionMethodInfoArguments=sum(r['methodInfoArgumentObserved']for r in condition_calls),
        distinctConditionMethodInfoPointers=len({r['methodInfoPointer']for r in condition_calls if r['methodInfoArgumentObserved']}))
    return dict(schema=SCHEMA,status='observed-conditional-endpoints',counts=counts,admissions=admissions,
        conditionCalls=condition_calls,entries=entries,constructors=constructors,resets=resets,cases=cases,caseOrigins=origins,
        runtimeReady=False,completeFieldWriterHistoryProved=False,crossFrameDeliveryProved=False,
        boundary='Normal paired observations and explicit synchronous enclosure. Equal sampled pointers/bytes or adjacent observed events do not prove causal delivery, class contents, uninterrupted lifetime, successful cast or a hit.')


def _result(effects):
    return dict(outcome='normal-return',returned=None,effects=effects,runtimeOwnershipProved=False,
                crossFrameDeliveryProved=False,actualNewSkillStartProved=False)


def inspect(inspection_path,writer_path,fsm_path,lifecycle_path,dispatch_path):
    saved=[]
    for path in map(Path,(inspection_path,writer_path,fsm_path,lifecycle_path,dispatch_path)):
        need(path.stat().st_size<=MAX_BYTES,'source byte budget exceeded')
        with path.open('rb')as stream:raw=stream.read(MAX_BYTES+1)
        need(len(raw)<=MAX_BYTES,'source grew beyond budget');saved.append((path,raw))
    result=project(*(json.loads(raw)for _,raw in saved))
    for p,raw in saved:
        need(p.stat().st_size<=MAX_BYTES,'source grew at bookend')
        with p.open('rb')as stream:after=stream.read(MAX_BYTES+1)
        need(after==raw,'source changed during projection')
    result['sources']=[dict(path=str(p.resolve()),sha256=hashlib.sha256(raw).hexdigest())for p,raw in saved]
    return result


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('inspection','writer-evidence','fsm-evidence','lifecycle-evidence','dispatch-evidence','output','cases-output'):
        parser.add_argument('--'+name,type=Path,required=True)
    a=parser.parse_args(argv);inputs=[a.inspection,a.writer_evidence,a.fsm_evidence,a.lifecycle_evidence,a.dispatch_evidence]
    for p in (a.output,a.cases_output):need(p.resolve().is_relative_to(REPO_ROOT/'reports')and p.resolve()not in [x.resolve()for x in inputs],'distinct reports output required')
    need(a.output.resolve()!=a.cases_output.resolve(),'output paths must differ')
    result=inspect(*inputs)
    cases=dict(schema='endfield.conditional-timing-cases.v1',cases=result.pop('cases'),caseOrigins=result.pop('caseOrigins'),sources=result['sources'],
        conditions=dict(original_path='Observed endpoint operands projected through the reviewed original constructor/reset paths; IFix selection and helper effects remain premises.',
            operand_binding='Same-call retained constructor arguments/fields and exact 88-byte reset endpoints; coherent snapshot/receiver is required.',
            delta_and_sample_sources='No elapsed-time reconstruction. Constructor null-AI preserves fields; reset before/after bytes are independent observed values.',
            precision='Exact reference tokens and bytes. Dispose normal completion and no interfering write between reset and sampled return are conditions.'),
        boundary=result['boundary'])
    for path,value in [(a.output,result),(a.cases_output,cases)]:
        path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],counts=result['counts'])))


if __name__=='__main__':main()
