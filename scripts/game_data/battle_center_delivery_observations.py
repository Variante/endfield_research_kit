"""Bounded synchronous equality observations for the Center delivery profile.

No nearest-time matching, runtime closed-type inference, lifetime inference or
cross-frame causality is performed. The admitted inspection owns ABI/transport
validation; this projection rechecks pair enclosure and preserves ambiguity.
"""
from __future__ import annotations
import argparse
import collections
import hashlib
import json
from pathlib import Path
from scripts.game_data.battle_input_request_links import project_request_links, _fields
from scripts.repo_paths import REPO_ROOT

SCHEMA='endfield.battle-center-delivery-observations.v3'
MAX_BYTES=256*1024**2
MAX_INPUT_BYTES=1024**3
D='battle.Delivery.'
C='battle.Center.'


def need(ok,detail):
    if not ok:raise ValueError('centerDelivery: '+detail)


def argument(event,index):
    mask=event.get('argsReadMask',0)
    need(type(mask)is int and 0<=mask<256,'invalid argument read mask')
    if not mask & (1<<index):return None
    value=event['rawArgs'][index]
    need(type(value)is int and 0<=value<2**64,'invalid observed argument bits')
    return value


def raw(event,label,count):
    rows=[f for f in event.get('fields',[])if f['label']==label]
    need(len(rows)<=1,'duplicate raw field '+label)
    if not rows or type(rows[0].get('state'))is not int or rows[0]['state']!=1:return None
    f=rows[0]
    need(f.get('stateName','exact')=='exact','inconsistent raw state')
    value=bytes.fromhex(f['rawHex'])
    need(f.get('byteCount')==len(value)==count,'wrong raw width '+label)
    return value


def words(event,label,count=1):
    value=raw(event,label,count*8)
    return None if value is None else [int.from_bytes(value[i:i+8],'little')for i in range(0,len(value),8)]


def project(inspection,*,max_depth=64,max_links=200000):
    need(inspection.get('sourceContext',{}).get('recipeName')=='battle-center-delivery','delivery recipe required')
    need(type(max_depth)is int and type(max_links)is int and 0<max_depth<=64 and 0<max_links<=200000,'invalid delivery budgets')
    observations=inspection['observations']
    need(isinstance(observations,list)and 0<len(observations)<=50000,'observation budget exceeded')
    stacks=collections.defaultdict(list)
    for event in sorted((e for o in observations for e in (o['enter'],o['exit'])),key=lambda e:e['sequence']):
        stack=stacks[event['threadId']]
        if event['phase']=='enter':
            need(event.get('parentInvocationId',0)==(stack[-1]if stack else 0),'parent is not the active paired ancestor')
            need(len(stack)<max_depth,'paired nesting budget exceeded')
            stack.append(event['invocationId'])
        else:
            need(bool(stack)and stack.pop()==event['invocationId'],'paired intervals are not nested')
    request_links=project_request_links(inspection)
    byid={(o['threadId'],o['invocationId']):o for o in observations}
    children=collections.defaultdict(list)
    selectors=collections.defaultdict(list);links=0
    def reserve():
        nonlocal links
        links+=1;need(links<=max_links,'delivery link budget exceeded')
    def key(o):return o['threadId'],o['invocationId']
    def parent(o):return byid.get((o['threadId'],o['enter'].get('parentInvocationId',0)))
    def nearest(o,hook):
        a=parent(o)
        while a is not None:
            if a['hook']==hook:return a
            a=parent(a)
        return None
    def ref(o):return dict(threadId=o['threadId'],invocationId=o['invocationId'],hook=o['hook'],
        entrySequence=o['enter']['sequence'],returnSequence=o['exit']['sequence'],
        receiverPointer=argument(o['enter'],0),callerReturnRva=o['enter'].get('callerGameAssemblyRva'))
    for o in observations:
        a=parent(o)
        while a is not None:
            reserve();children[key(a)].append(o);a=parent(a)
        if o['hook']==D+'Select':
            tick=parent(o)
            need(tick is not None and tick['hook']==D+'Tick','selector needs direct recorded Tick parent')
            value=o['exit'].get('returnValue')
            need(type(value)is int and 0<=value<2**64,'selector requires raw reference return')
            reserve();selectors[key(tick),value].append(o)
    transits=[];conditions=[];descriptors=[];settlements=[];damage_calls=[];timing=[];lifecycles=[];state_entries=[]
    def ancestor_ref(o,hook):
        found=nearest(o,hook)
        return None if found is None else ref(found)
    def cast_children(entry):
        return [ref(c)|dict(beforeCastDescendants=[ref(b)for b in children[key(c)]
            if b['hook']=='battle.Ability.BeforeCast' and nearest(b,C+'DoCast') is c])
            for c in children[key(entry)]if c['hook']==C+'DoCast' and nearest(c,C+'OnEnter') is entry]
    for o in sorted(observations,key=lambda r:r['enter']['sequence']):
        if o['hook']in ('buff.AbilitySystem.ApplyModifier','buff.AbilitySystem._DoApplyModifier'):
            settlements.append(ref(o)|dict(before=_fields(o['enter']),after=_fields(o['exit']),
                returnedBits=o['exit'].get('returnValue'),
                damageProcessAncestor=ancestor_ref(o,'damage.Action.ProcessDamage'),
                damageActionAncestor=ancestor_ref(o,'damage.Action.ExecuteInternal'),
                outerApplyModifierAncestor=ancestor_ref(o,'buff.AbilitySystem.ApplyModifier'),
                uniqueSkillOwnershipProved=False))
        elif o['hook']in ('damage.Action.ExecuteInternal','damage.Action.ProcessDamage'):
            damage_calls.append(ref(o)|dict(before=_fields(o['enter']),after=_fields(o['exit']),
                recordedBindingCandidate=o.get('bindingCandidate'),
                sameCallBeforeCastAncestor=ancestor_ref(o,'battle.Ability.BeforeCast'),
                asyncSkillToHitOwnershipProved=False))
        elif o['hook']in ('battle.Skill.Init','battle.Skill.Release','battle.Ability.Init','battle.Ability.Release',
                          'battle.Action.AssignData','battle.Action.ReAssign'):
            lifecycles.append(ref(o)|dict(before=_fields(o['enter']),after=_fields(o['exit']),
                uninterruptedLifetimeProved=False))
        elif o['hook'].startswith('battle.Time.'):
            timing.append(ref(o)|dict(entryFields=o['enter']['fields'],returnFields=o['exit']['fields'],
                rawArguments=o['enter']['rawArgs'],argumentReadMask=o['enter'].get('argsReadMask',0),
                observationClocks={phase:{name:event[name]for name in ('qpc','qpcFrequency','tickNs')if name in event}
                    for phase,event in [('entry',o['enter']),('return',o['exit'])]},
                returnedBits=o['exit'].get('returnValue'),
                damageProcessAncestor=ancestor_ref(o,'damage.Action.ProcessDamage'),
                centerTickAncestor=ancestor_ref(o,D+'Tick'),
                fullClockOrControlRecoveryProved=False))
        if o['hook']==C+'OnEnter':
            command=nearest(o,'battle.Command.OnExecute');bb=_fields(o['enter']).get('blackboardIdentity')
            admissions=[]
            if command is not None:
                for p in children[key(command)]:
                    if p['hook']!=C+'ToSkill' or nearest(p,'battle.Command.OnExecute') is not command:
                        continue
                    if p['exit']['sequence']>=o['enter']['sequence'] or p.get('booleanReturn')is not True:continue
                    reserve()
                    getters=[ref(g)|dict(returnedPointer=g['exit'].get('returnValue'),
                        equalsSampledStateBlackboard=bb not in (None,0)and g['exit'].get('returnValue')==bb)
                        for g in children[key(p)]if g['hook']==C+'GetBlackboard' and parent(g) is p]
                    admissions.append(ref(p)|dict(getters=sorted(getters,key=lambda g:g['entrySequence']),
                        causalTransferProved=False))
            state_entries.append(ref(o)|dict(directRecordedParent=None if parent(o)is None else ref(parent(o)),
                commandAncestor=None if command is None else ref(command),
                commandType=None if command is None else _fields(command['enter']).get('cmdType'),
                tickAncestor=ancestor_ref(o,D+'Tick'),transitAncestor=ancestor_ref(o,D+'Transit'),
                blackboardPointer=bb,earlierSuccessfulToSkillCandidates=admissions,
                doCastDescendants=cast_children(o),crossFrameDeliveryProved=False))
        if o['hook']==D+'Transit':
            tick=parent(o)
            need(tick is not None and tick['hook']==D+'Tick','executor needs direct recorded Tick parent')
            pointer=argument(o['enter'],0)
            candidates=[]
            for s in selectors.get((key(tick),pointer),[])if pointer not in (None,0)else []:
                if s['exit']['sequence']>=o['enter']['sequence']:continue
                reserve();candidates.append(ref(s)|dict(returnedPointer=pointer))
            endpoints=words(o['enter'],'transitionFromTo',2)
            before=words(o['enter'],'currentSlot');after=words(o['exit'],'currentSlot')
            entries=[]
            for e in children[key(o)]:
                if e['hook']!=C+'OnEnter' or nearest(e,D+'Transit') is not o:continue
                state=argument(e['enter'],0)
                entries.append(ref(e)|dict(
                    equalsSampledToState=bool(endpoints and endpoints[1]!=0 and state==endpoints[1]),
                    equalsReturnedCurrentSlot=bool(after and after[0]!=0 and state==after[0]),
                    blackboardPointer=_fields(e['enter']).get('blackboardIdentity'),
                    doCastDescendants=cast_children(e)))
            transits.append(ref(o)|dict(tick=ref(tick),selectorCandidates=candidates,
                uniqueSelectorPointerMatch=len(candidates)==1,transitionFromTo=endpoints,
                currentSlotAddress=argument(o['enter'],1),currentSlotBefore=before,currentSlotAfter=after,
                entries=entries,beforeCastDescendants=[ref(b)for b in children[key(o)]
                    if b['hook']=='battle.Ability.BeforeCast' and nearest(b,D+'Transit') is o],
                synchronousEnclosureObserved=True,liveClosedCenterTypeProved=False,
                crossFrameDeliveryProved=False,lifetimeContinuityProved=False))
        elif o['hook']==D+'Condition':
            recorded_parent=parent(o)
            need(recorded_parent is not None,'scoped condition needs a recorded paired ancestor')
            selector=recorded_parent if recorded_parent['hook']==D+'Select'else None
            tick=nearest(o,D+'Tick')
            calls=[p for p in children[key(o)]if p['hook']==C+'ToSkill' and nearest(p,D+'Condition') is o]
            value=o['exit'].get('returnValue')
            need(type(value)is int and 0<=value<2**64,'condition requires raw return bits')
            conditions.append(ref(o)|dict(selector=None if selector is None else ref(selector),
                tick=None if tick is None else ref(tick),directRecordedParent=ref(recorded_parent),
                commandAncestor=ancestor_ref(o,'battle.Command.OnExecute'),
                selectorInvocationObserved=selector is not None,
                returnedLow8=value&255,
                checkerPointer=words(o['enter'],'transitionChecker'),
                checkerDispatch=words(o['enter'],'checkerDispatch',7),
                toSkillDescendants=[ref(p)|dict(
                    sameMachineAsTick=None if tick is None else argument(p['enter'],0) not in (None,0) and
                        argument(p['enter'],0)==argument(tick['enter'],0),
                    methodInfoPointer=argument(p['enter'],1))for p in calls]))
        if o['hook']==C+'ToSkill':
            code=words(o['enter'],'methodCodePair',2);flags=raw(o['enter'],'methodFlags',13)
            descriptors.append(ref(o)|dict(methodInfoPointer=argument(o['enter'],1),codePair=code,
                returned=o.get('booleanReturn'),
                tokenAndFlagsHex=None if flags is None else flags.hex(),
                descriptorBytesObserved=code is not None and flags is not None,
                initializedLifetimeProved=False))
    return dict(schema=SCHEMA,status='observed-synchronous-equalities',transits=transits,
        conditions=conditions,descriptors=descriptors,settlements=settlements,damageCalls=damage_calls,
        timingSamples=timing,lifecycleSamples=lifecycles,stateEntries=state_entries,
        inputRequestCounts=request_links['counts'],
        coverage=dict(settlementPairs=len(settlements),damageCallPairs=len(damage_calls),
            timingPairs=len(timing),lifecyclePairs=len(lifecycles),
            settlementsWithinDamageProcess=sum(s['damageProcessAncestor']is not None for s in settlements)),
        counts=dict(normalPairs=len(observations),transits=len(transits),conditions=len(conditions),
            uniqueSelectorPointerMatches=sum(t['uniqueSelectorPointerMatch']for t in transits),
            ambiguousSelectorPointerMatches=sum(len(t['selectorCandidates'])>1 for t in transits),
            enteredSampledToStates=sum(e['equalsSampledToState']for t in transits for e in t['entries']),
            descriptorByteSamples=sum(d['descriptorBytesObserved']for d in descriptors),
            conditionsWithoutRecordedSelector=sum(not c['selectorInvocationObserved']for c in conditions),
            stateEntries=len(state_entries),commandOwnedStateEntries=sum(e['commandAncestor']is not None for e in state_entries)),
        evidenceBoundary=dict(direct='Recorded normal pair enclosure and sampled byte/pointer equalities only.',
            unresolved='Cross-frame request identity, live closed types, atomicity, all intervening writers and lifetime.'),
        fullInputExecutionChainProved=False)


def inspect(path,*,max_input_bytes=MAX_BYTES):
    need(type(max_input_bytes)is int and 0<max_input_bytes<=MAX_INPUT_BYTES,'invalid input byte budget')
    path=Path(path);need(path.stat().st_size<=max_input_bytes,'inspection too large; explicit --max-input-bytes may be required')
    with path.open('rb')as source:data=source.read(max_input_bytes+1)
    need(len(data)<=max_input_bytes,'inspection too large')
    result=project(json.loads(data))
    with path.open('rb')as source:need(source.read(max_input_bytes+1)==data,'inspection source changed')
    result['source']=dict(path=str(path.resolve()),sha256=hashlib.sha256(data).hexdigest())
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--inspection',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--max-input-bytes',type=int,default=MAX_BYTES,help='explicit bounded inspection size, maximum 1 GiB')
    a=p.parse_args(argv)
    if not any(a.output.resolve().is_relative_to(REPO_ROOT/r)for r in ('reports','scratch','tmp')):
        p.error('output must be in reports/scratch/tmp')
    if a.output.resolve()==a.inspection.resolve():p.error('output must not replace inspection')
    try:result=inspect(a.inspection,max_input_bytes=a.max_input_bytes)
    except (OSError,ValueError,KeyError,TypeError,IndexError)as error:
        print(json.dumps(dict(status='blocked',diagnostics=[str(error)[:1200]])));return 1
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=result['status'],counts=result['counts'])));return 0


if __name__=='__main__':raise SystemExit(main())
