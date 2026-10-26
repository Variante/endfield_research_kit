"""Summarize saved numeric Buff calls and explicit synchronous query paths.

Reuse a completed paired inspection. Source tables supply candidate comparisons,
never live node ownership or a substitute for missing initialization returns.
"""
from __future__ import annotations
import argparse
from collections import Counter,defaultdict
import json
import struct
from pathlib import Path

from . import mission_trace_inspect as trace
from .buff_runtime_paired_inspect import floating_return
from .buff_runtime_trace_inspect import fingerprint,checked_pin
from .mission_trace_invocations import Invocations
from scripts.repo_paths import REPO_ROOT

NUMERIC = {'buff.ActionBlackboard.GetDouble':'double',
           'buff.ActionBlackboard.GetFloatInput':'float',
           'buff.ActionBlackboard.GetFloatKey':'float',
           'buff.HealPackData.GetFinalHealValue':'double',
           'buff.BattleFormula.CalculateHeal':'double',
           'buff.AbilitySystem.get_hp':'double','buff.AbilitySystem.get_maxHp':'double'}
NUMERIC['buff.Modifier.GetFinalDelta']='double'
LOOKUP='buff.Blackboard.TryGetFloat'
LOOKUPS={LOOKUP:('outputFloat','floatBits','float'),
         'buff.Blackboard.TryGetDoubleKey':('outputDouble','floatBits','double')}
WRITES={'buff.Blackboard._AssignInternal','buff.Blackboard._AssignDynamicInternal','buff.Blackboard.AssignDouble','buff.Blackboard.AssignString'}
MERGES={'buff.Blackboard.AssignList','buff.Blackboard.AddRange','buff.Blackboard.AssignDynamicList','buff.ActionBlackboard.AssignList'}
APPLICATIONS={'buff.Modifier.Apply','buff.AbilitySystem.ApplyModifier','buff.AbilitySystem._DoApplyModifier'}
EFFECT='buff.SkillUtil._CalculatePotentialTalentEffect'
BOUNDARY=('Explicit saved invocation enclosure and raw values only. Entry-only '
          'initialization calls do not provide completed intervals. A source-table '
          'agreement, pointer equality or numeric agreement does not establish '
          'serialized-node selection, an intermediate writer or final HP mutation.')


def fields(row):
    return {f['label']:f.get('value') for f in row['fields']}


def classify_healing_snapshots(result, audit):
    """Label only native-gated copy sites with an observed false snapshot guard.

    Actor ownership is not inferred from these labels: the saved attribute
    receiver and UID must separately agree with same-action actor records.
    """
    if audit.get('status') != 'validated':
        return
    spec=audit.get('interpretation',{}).get('attributeSnapshots')
    if not spec:
        return
    sites={r['returnRva']:r for r in spec['copies']}
    for snapshot in result['healingAttributeSnapshots']:
        guards=[r for r in snapshot['patchChecks'] if
            r['entry']['fields'].get('patchId')==spec['guardPatchId'] and
            r['entry']['parentInvocationId']==snapshot['entry']['invocationId']]
        if len(guards)!=1 or guards[0]['returned'] is not False:
            snapshot['copyClassification']='unresolved-snapshot-patch-selection'
            continue
        snapshot['copyClassification']='conditional-native-copy-sites'
        for read in snapshot['attributeReads']:
            site=sites.get(read['entry']['callerReturnRva'])
            if site:
                read['compiledSnapshotSide']=site['side']
                read['snapshotArrayField']=site['arrayField']
                uid=read['entry']['fields'].get('attributesInstanceUid')
                read['attributeReceiverUidUnchanged']=(
                    type(uid) is int and uid >= 0 and uid==
                    read['returnFields'].get('attributesInstanceUid'))


def healing_native_roles(profile, gameassembly, metadata):
    from scripts.common import check_installed_native_inputs
    from .buff_healing_settlement_native import load_healing_settlement
    pins=profile['files']
    gate=check_installed_native_inputs(pins['gameAssembly']['sha256'],pins['metadata']['sha256'],
                                       gameassembly=gameassembly,metadata=metadata)
    trace.require(gate.validated,'Buff healing roles: native '+gate.status+': '+gate.detail)
    return load_healing_settlement(gameassembly=gate.gameassembly,metadata=gate.metadata)


def brief(row):
    return {'sequence':row['sequence'],'hook':row['hook'],
            'invocationId':row['invocationId'],'parentInvocationId':row['parentInvocationId'],
            'receiverBits':row['rawArgs'][0],'callerReturnRva':row['callerGameAssemblyRva'],
            'fields':fields(row)}


def summarize(events,hooks,enums=None):
    validator=Invocations();stacks=defaultdict(list);opened={};groups={};init=Counter()
    values=defaultdict(Counter);lookups=Counter();lookup_sites=Counter();rounding=Counter();heals=[];hp=[]
    caller_counts=Counter();entries=Counter();unscoped=0;ability_init={};action_paths={};resets=Counter()
    write_requests=[];effects=[];hp_events=[];notifications=[]
    merges=[];applications=[];patches=[];packets=[]
    healing_actions=[];reset_intervals=[]
    attribute_snapshots=[];event_interest=[];event_dispatch=[];event_queues=[]
    conditions=[];creation_intervals=[];ability_source_intervals=[];helper_inputs=[]
    def nearest(stack,predicate):
        return next((opened[i] for i in reversed(stack) if predicate(opened[i]['entry']['hook'])),None)
    for row in events:
        hook=hooks[row['hookIndex']]
        trace.require(row['hook']==hook['name'],'Buff values: hook binding')
        validator.observe({**row,'args':row['rawArgs']},hook)
        stack=stacks[row['threadId']];phase=row['phase'];name=row['hook'];ident=row['invocationId']
        if phase in ('entry','enter'):entries[name]+=1;caller_counts[(name,row['callerGameAssemblyRva'])]+=1
        if phase=='entry' and name=='buff.Ability.Init':
            ability_init[row['rawArgs'][0]]=brief(row)
        if phase in ('entry','enter') and name.startswith('buff.SkillUtil.'):
            key=json.dumps({'hook':name,'callerReturnRva':row['callerGameAssemblyRva'],'fields':fields(row)},sort_keys=True)
            init[key]+=1
            trace.require(len(init)<=65536,'Buff values: initialization grouping budget')
        if phase=='entry':
            if name=='buff.ActionBlackboardExtensions.GetDoubleValueOrDefault':
                trace.require(len(helper_inputs)<65536,'Buff values: helper input budget')
                comparison=nearest(stack,lambda h:h=='buff.CompareFloat.ExecuteInternal')
                helper_inputs.append({'entry':brief(row),
                    'comparisonInvocationId':comparison['entry']['invocationId'] if comparison else None,
                    'helperReturnObserved':False,'defaultScalarInputObserved':False,
                    'boundary':'Transparent helper entry fields only; generic success, XMM2 default and numeric return are not observed.'})
            if name.startswith('buff.HealDetail.'):
                trace.require(len(packets)<65536,'Buff values: protocol snapshot budget')
                packets.append({'entry':brief(row),'phase':'entry-only','boundary':'Protocol object fields at a named property-access boundary; no whole-message codec boundary, transport direction, pointer lifetime or acknowledgement.'})
            if name=='buff.AbilitySystem.SetHpInternal':
                trace.require(len(hp_events)<65536,'Buff values: HP entry budget')
                action=nearest(stack,lambda h:h in {'buff.HealAction.ExecuteInternal','buff.AbilityAction.Execute'})
                event={'entry':brief(row),'actionInvocationId':action['entry']['invocationId'] if action else None}
                hp_events.append(event)
                if action:action['hpEntries'].append(event)
            continue
        if phase=='enter':
            if name=='buff.SequenceAction.ExecuteInstant':
                queue=nearest(stack,lambda h:h=='buff.ActionContainer.ExecuteInstant')
                if queue:
                    trace.require(len(queue['sequenceEntries'])<65536,'Buff values: event sequence budget')
                    queue['sequenceEntries'].append({**brief(row),
                        'directContainerParent':row['parentInvocationId']==queue['entry']['invocationId']})
            context=nearest(stack,lambda h:h=='buff.Buff._ExecuteBuffAction')
            action=nearest(stack,lambda h:h=='buff.AbilityAction.Execute')
            environment=fields(action['entry']).get('entryEnvironment') if action else fields(row).get('entryEnvironment')
            opened[ident]={'entry':row,'queries':[],'children':[],
                'actionQueries':[],'abilityInitCandidate':ability_init.get(environment),
                'effectQueries':[],'writeRequests':[],'hpEntries':[],
                'nestedWrites':[],'patchChecks':[],
                'healStages':[],'mergeCalls':[],
                'sourceTransfers':[], 'attributeReads':[], 'eventQueues':[], 'sequenceEntries':[],
                'buff':brief(context['entry']) if context else None,
                'ancestors':[brief(opened[i]['entry']) for i in stack] if name in {LOOKUP,'buff.HealPackData.GetFinalHealValue','buff.CheckHp.ExecuteInternal'} else []}
            stack.append(ident);continue
        current=opened.pop(ident);stack.pop();entry=current['entry'];normal=phase=='return'
        if not normal:continue
        if name in LOOKUPS:
            output_label,bits_label,storage=LOOKUPS[name]
            f=fields(row);out=next(f for f in row['fields'] if f['label']==output_label)
            query={'key':f['key'],'succeeded':bool(row['returnValue']),
                'valueBits':out.get(bits_label),'value':f[output_label],'storage':storage,
                'blackboardReceiverBits':entry['rawArgs'][0],'invocationId':ident,
                'entrySequence':entry['sequence'],'returnSequence':row['sequence'],
                'callerReturnRva':entry['callerGameAssemblyRva']}
            lookups[json.dumps({k:query[k] for k in ('key','succeeded','valueBits','value','storage')},sort_keys=True)]+=1
            lookup_sites[json.dumps({k:query[k] for k in ('key','succeeded','valueBits','value','storage','callerReturnRva')},sort_keys=True)]+=1
            ancestor=nearest(stack,lambda h:h in NUMERIC)
            if ancestor:ancestor['queries'].append(query)
            else:unscoped+=1
            action=nearest(stack,lambda h:h=='buff.AbilityAction.Execute')
            if action:action['actionQueries'].append(query)
            effect=nearest(stack,lambda h:h==EFFECT)
            if effect:effect['effectQueries'].append(query)
        if name in NUMERIC:
            numeric=floating_return(NUMERIC[name],row['returnValue'])
            values[name][json.dumps(numeric,sort_keys=True)]+=1
            signature={'hook':name,'buffIdAtAncestorEntry':(current['buff'] or {}).get('fields',{}).get('entryDataId'),
                'skillIdAtEarlierObservedInit':(current['abilityInitCandidate'] or {}).get('fields',{}).get('suppliedSkillDataId'),
                'key':fields(entry).get('key'),'return':numeric,
                'expressionFields':{k:v for k,v in fields(entry).items() if k.startswith('expression')},
                'queries':[{k:q[k] for k in ('key','succeeded','valueBits','value')} for q in current['queries']]}
            key=json.dumps(signature,sort_keys=True)
            trace.require(len(groups)<65536 or key in groups,'Buff values: numeric grouping budget')
            group=groups.setdefault(key,{**signature,'calls':0,'examples':[]});group['calls']+=1
            if len(group['examples'])<2:group['examples'].append({'entry':brief(entry),'queries':current['queries']})
            ancestor=nearest(stack,lambda h:h in NUMERIC or h=='buff.AbilityAction.Execute')
            if ancestor:ancestor['children'].append({'hook':name,'return':numeric,'rawReturn':row['returnValue'],
                'invocationId':ident,'args':entry['rawArgs'][:2]})
            if name=='buff.ActionBlackboard.GetFloatInput':
                doubles=[c for c in current['children'] if c['hook']=='buff.ActionBlackboard.GetDouble']
                if len(doubles)==1 and doubles[0]['args']==entry['rawArgs'][:2] and doubles[0]['return']['class']=='finite':
                    try:expected=int.from_bytes(struct.pack('<f',doubles[0]['return']['value']),'little')
                    except OverflowError:rounding['finite-outside-single-range']+=1
                    else:rounding['nearest-even-bit-match' if expected==row['returnValue'] else 'different-bits']+=1
                else:rounding['no-unique-same-input-double-child']+=1
            if name in {'buff.HealPackData.GetFinalHealValue','buff.BattleFormula.CalculateHeal'}:
                enclosing=nearest(stack,lambda h:h=='buff.AbilityAction.Execute')
                heals.append({'entry':brief(entry),'return':numeric,'returnFields':fields(row),
                    'abilityInitCandidate':current['abilityInitCandidate'],
                    'ancestors':current['ancestors'],'precedingObservedNumericSiblings':(enclosing or {}).get('children',[])[:-1],
                    'boundary':BOUNDARY})
        if name in WRITES:
            trace.require(len(write_requests)<65536,'Buff values: write request budget')
            effect=nearest(stack,lambda h:h==EFFECT)
            request={'entry':brief(entry),'returnFields':fields(row),
                'returnedDynamicAcceptance':bool(row['returnValue']) if name.endswith('_AssignDynamicInternal') else None,
                'effectInvocationId':effect['entry']['invocationId'] if effect else None,
                'boundary':'Recorded write request and normal completion; void does not prove destination contents. Only explicitly enclosed named IFix checks observe patch decisions.'}
            write_requests.append(request)
            if effect:effect['writeRequests'].append(request)
            merge=nearest(stack,lambda h:h in MERGES)
            if merge:merge['nestedWrites'].append(request)
        if name in MERGES:
            trace.require(len(merges)<65536,'Buff values: merge interval budget')
            parent=nearest(stack,lambda h:h in MERGES or h=='buff.Skill.AssignSourceBlackboard' or h==EFFECT)
            observed_merge={'entry':brief(entry),'returnFields':fields(row),'submittedItems':current['nestedWrites'],
                'sourceListArgumentBits':entry['rawArgs'][1],
                'ownerInvocationId':parent['entry']['invocationId'] if parent else None,
                'patchChecks':current['patchChecks'],
                'boundary':'Completed merge/append interval and reached per-item submissions. Empty append, inlined mutations and unobserved items prevent a whole collection snapshot claim.'}
            merges.append(observed_merge)
            reset=nearest(stack,lambda h:h in {'buff.Skill.AssignSourceBlackboard','buff.Skill._OnCreate'})
            if reset:reset['mergeCalls'].append({'entry':observed_merge['entry'],
                'sourceListArgumentBits':observed_merge['sourceListArgumentBits'],
                'ownerInvocationId':observed_merge['ownerInvocationId']})
        if name=='buff.IFix.IsPatched':
            trace.require(len(patches)<131072,'Buff values: patch observation budget')
            observed={'entry':brief(entry),'returned':bool(row['returnValue'])}
            patches.append(observed)
            if stack:opened[stack[-1]]['patchChecks'].append(observed)
        if name=='buff.Attributes.GetValue':
            snapshot=nearest(stack,lambda h:h=='buff.HealPackData._DumpAttributes')
            if snapshot:
                trace.require(len(snapshot['attributeReads'])<4096,'Buff values: attribute snapshot budget')
                snapshot['attributeReads'].append({'entry':brief(entry),'returnFields':fields(row),
                    'returnSequence':row['sequence'],'floatingReturn':floating_return('double',row['returnValue'])})
        if name=='buff.HealPackData._DumpAttributes':
            trace.require(len(attribute_snapshots)<65536,'Buff values: snapshot interval budget')
            owner=nearest(stack,lambda h:h=='buff.HealAction.ExecuteInternal')
            attribute_snapshots.append({'entry':brief(entry),'returnFields':fields(row),
                'returnSequence':row['sequence'],'actionInvocationId':owner['entry']['invocationId'] if owner else None,
                'attributeReads':current['attributeReads'],'patchChecks':current['patchChecks'],
                'boundary':'Completed snapshot/getter enclosures; side/array transfer requires separately gated native callsite proof. Missing reads are not zero attribute values.'})
        if name=='buff.AbilitySystem.NeedTriggerEvent':
            trace.require(len(event_interest)<65536,'Buff values: event interest budget')
            owner=nearest(stack,lambda h:h=='buff.AbilitySystem._OnHealed')
            event_interest.append({'entry':brief(entry),'returnFields':fields(row),'returned':bool(row['returnValue']),
                'notificationInvocationId':owner['entry']['invocationId'] if owner else None,
                'boundary':'Observed interest result, not listener execution or delivery.'})
        if name=='buff.ActionContainer.ExecuteInstant':
            trace.require(len(event_queues)<65536,'Buff values: event queue budget')
            owner=nearest(stack,lambda h:h=='buff.AbilitySystem.TriggerEvent')
            observed={'entry':brief(entry),'returnFields':fields(row),'returnSequence':row['sequence'],
                'dispatchInvocationId':owner['entry']['invocationId'] if owner else None,
                'sequenceEntries':current['sequenceEntries'],
                'boundary':'Reached action-container interval and explicit synchronous sequence entries. An empty interval proves no recorded sequence entry, not absent generic delegate subscribers.'}
            event_queues.append(observed)
            if owner:owner['eventQueues'].append(observed)
        if name=='buff.AbilitySystem.TriggerEvent':
            trace.require(len(event_dispatch)<65536,'Buff values: event dispatch budget')
            owner=nearest(stack,lambda h:h=='buff.AbilitySystem._OnHealed')
            event_dispatch.append({'entry':brief(entry),'returnFields':fields(row),'returnSequence':row['sequence'],
                'notificationInvocationId':owner['entry']['invocationId'] if owner else None,
                'actionQueues':current['eventQueues'],'patchChecks':current['patchChecks'],
                'boundary':'Completed named dispatch, event/context identities and action-container descendants. Generic delegates, pointer lifetime and listener effects remain separate.'})
        if name in APPLICATIONS:
            trace.require(len(applications)<65536,'Buff values: application interval budget')
            signed=row['returnValue'] if row['returnValue']<2**31 else row['returnValue']-2**32
            definition=(enums or {}).get(hook['returnType'],{})
            applications.append({'entry':brief(entry),'returnFields':fields(row),'resultBits':row['returnValue'],
                'resultValue':signed,'resultNames':[m['name'] for m in definition.get('members',[]) if m['value']==signed],
                'patchChecks':current['patchChecks'],
                'boundary':'Recorded named application result and sequential fields. Target/delta type and explicit enclosures must be inspected; the result alone does not prove server acceptance.'})
        if name.startswith('buff.HealDetail.'):
            trace.require(len(packets)<65536,'Buff values: protocol snapshot budget')
            packets.append({'entry':brief(entry),'returnFields':fields(row),'phase':'completed-pair',
                'boundary':'Named property-access snapshots; no whole-message codec boundary. Object equality does not prove lifetime or packet origin/direction.'})
        if name==EFFECT:
            trace.require(len(effects)<65536,'Buff values: effect interval budget')
            effects.append({'entry':brief(entry),'queries':current['effectQueries'],
                'writeRequests':current['writeRequests'],'returnedNormally':True,
                'boundary':'Explicit effect interval, not proof that every candidate activeCondition passed.'})
        if name=='buff.AbilitySystem._OnHealed':
            trace.require(len(notifications)<65536,'Buff values: notification budget')
            action=nearest(stack,lambda h:h in {'buff.HealAction.ExecuteInternal','buff.AbilityAction.Execute'})
            target=entry['rawArgs'][0]
            prior=[e for e in (action or {}).get('hpEntries',[]) if e['entry']['receiverBits']==target]
            notifications.append({'entry':brief(entry),'returnFields':fields(row),
                'actionInvocationId':action['entry']['invocationId'] if action else None,
                'precedingSameReceiverHpEntries':prior,
                'boundary':'Stored HP and realDelta at notification; only explicit same-action/same-receiver earlier entries are associated. No timestamp join, pointer lifetime or server acceptance.'})
        if name=='buff.CheckHp.ExecuteInternal':
            hp.append({'entry':brief(entry),'returned':bool(row['returnValue']),
                'abilityInitCandidate':current['abilityInitCandidate'],
                'numericChildren':current['children'],'ancestors':current['ancestors']})
        if name in {'buff.CompareFloat.ExecuteInternal','buff.CheckEntityNum.ExecuteInternal'}:
            trace.require(len(conditions)<65536,'Buff values: condition budget')
            conditions.append({'entry':brief(entry),'returned':bool(row['returnValue']),
                'returnFields':fields(row),'abilityInitCandidate':current['abilityInitCandidate'],
                'boundary':'Named condition result and input snapshots under recorded enclosure; stored-node selection and complete target count remain separate.'})
        if name=='buff.Ability.AssignSourceBlackboard':
            trace.require(len(ability_source_intervals)<65536,'Buff values: Ability source interval budget')
            observed={'entry':brief(entry),'returnFields':fields(row),
                'boundary':'Captured source/extra arguments and dynamic-baseline identity; no list enumeration or pointer lifetime.'}
            ability_source_intervals.append(observed)
            owner=nearest(stack,lambda h:h in {'buff.Skill.AssignSourceBlackboard','buff.Skill._OnCreate'})
            if owner:owner['sourceTransfers'].append(observed)
        if name=='buff.Skill._OnCreate':
            trace.require(len(creation_intervals)<65536,'Buff values: Skill creation interval budget')
            creation_intervals.append({'entry':brief(entry),'returnFields':fields(row),
                'mergeCalls':sorted(current['mergeCalls'],key=lambda r:r['entry']['sequence']),
                'sourceTransfers':current['sourceTransfers'],
                'boundary':'Same creation interval inputs and source-list submissions; incoming extra transfer is compared by recorded argument bits, not a lifetime assertion.'})
        if name=='buff.Skill.AssignSourceBlackboard':
            before=fields(entry);after=fields(row)
            signature={'extraArgumentNull':before.get('extraBlackboardIdentity')==0,
                'onCreateIdentityUnchanged':before.get('onCreateBlackboardIdentity')==after.get('onCreateBlackboardIdentity'),
                'actionBlackboardIdentityUnchanged':before.get('actionBlackboardIdentity')==after.get('actionBlackboardIdentity'),
                'contentsOrSpecificWritesProved':False}
            resets[json.dumps(signature,sort_keys=True)]+=1
            trace.require(len(reset_intervals)<65536,'Buff values: source reset interval budget')
            reset_intervals.append({'entry':brief(entry),'returnFields':after,
                'mergeCalls':sorted(current['mergeCalls'],key=lambda r:r['entry']['sequence']),
                'sourceTransfers':current['sourceTransfers'],
                'boundary':'Explicit reset descendants in entry order and raw source-list arguments; opaque lists are not enumerated and contents are not inferred.'})
        healing_action=nearest(stack,lambda h:h=='buff.HealAction.ExecuteInternal')
        if healing_action and (name in NUMERIC or name in APPLICATIONS or name=='buff.AbilitySystem._OnHealed'):
            trace.require(len(healing_action['healStages'])<65536,'Buff values: healing stage budget')
            healing_action['healStages'].append({'entry':brief(entry),'returnFields':fields(row),
                'returnSequence':row['sequence'],'rawReturn':row['returnValue'],
                'floatingReturn':floating_return(NUMERIC[name],row['returnValue']) if name in NUMERIC else None})
        if name=='buff.HealAction.ExecuteInternal':
            trace.require(len(healing_actions)<65536,'Buff values: healing action budget')
            healing_actions.append({'entry':brief(entry),'returned':bool(row['returnValue']),
                'abilityInitCandidate':current['abilityInitCandidate'],
                'stages':sorted(current['healStages'],key=lambda r:r['entry']['sequence']),
                'hpEntries':current['hpEntries'],
                'boundary':'Completed same-thread HealAction descendants only. Outside property-access calls are kept separate; pointer equality is not a lifetime or server acknowledgement.'})
        # Numeric reads enclosed by a condition are retained independently of
        # the broader action enclosure; never bind them merely by timestamp.
        if name in NUMERIC:
            condition=nearest(stack,lambda h:h=='buff.CheckHp.ExecuteInternal')
            if condition:condition['children'].append({'hook':name,'return':numeric,'invocationId':ident})
        if name=='buff.AbilityAction.Execute' and current['actionQueries']:
            receivers={};path=[]
            for q in current['actionQueries']:
                receivers.setdefault(q['blackboardReceiverBits'],len(receivers))
                path.append({**{k:q[k] for k in ('key','succeeded','value','valueBits')},'receiverOrdinal':receivers[q['blackboardReceiverBits']]})
            signature={'queries':path,'skillIdAtEarlierObservedInit':(current['abilityInitCandidate'] or {}).get('fields',{}).get('suppliedSkillDataId')}
            key=json.dumps(signature,sort_keys=True);trace.require(len(action_paths)<65536 or key in action_paths,'Buff values: action-query grouping budget')
            group=action_paths.setdefault(key,{**signature,'calls':0,'examples':[]});group['calls']+=1
            if len(group['examples'])<2:group['examples'].append({'entry':brief(entry),'queries':current['actionQueries'],'numericChildren':current['children']})
    complete=validator.finish(True)
    coverage={'expressionFieldCalls':sum(g['calls'] for g in groups.values() if
              {'expressionUsesKey','expressionKey','expressionLiteral'} <= set(g['expressionFields'])),
        'completedEffectIntervals':len(effects),'writeRequests':len(write_requests),
        'effectEnclosedWriteRequests':sum(r['effectInvocationId'] is not None for r in write_requests),
        'outerFormulaReturns':sum(h['entry']['hook']=='buff.BattleFormula.CalculateHeal' for h in heals),
        'hpWriteEntries':len(hp_events),'healingNotifications':len(notifications),
        'notificationsWithSameActionReceiverHpEntry':sum(bool(n['precedingSameReceiverHpEntries']) for n in notifications)}
    coverage.update(mergeIntervals=len(merges),applicationResults=len(applications),
                    namedPatchDecisions=len(patches),protocolSnapshots=len(packets))
    coverage.update(attributeSnapshotIntervals=len(attribute_snapshots),
        attributeSnapshotReads=sum(len(r['attributeReads']) for r in attribute_snapshots),
        healingEventInterest=len(event_interest),healingEventDispatch=len(event_dispatch),
        healingEventQueues=len(event_queues),
        healingEventSequenceEntries=sum(len(r['sequenceEntries']) for r in event_queues))
    return {'boundary':BOUNDARY,'invocations':complete,'hookEntries':dict(entries),
        'numericReturnValues':{h:[{**json.loads(k),'calls':n} for k,n in c.most_common()] for h,c in values.items()},
        'lookupValues':[{**json.loads(k),'calls':n} for k,n in lookups.most_common()],
        'lookupSites':[{**json.loads(k),'calls':n} for k,n in lookup_sites.most_common()],
        'lookupsWithoutNumericAncestor':unscoped,'floatFromDoubleChecks':dict(rounding),
        'numericPaths':sorted(groups.values(),key=lambda r:-r['calls']),
        'actionQueryPaths':sorted(action_paths.values(),key=lambda r:-r['calls']),
        'initialization':[{**json.loads(k),'calls':n} for k,n in init.items()],
        'healing':heals,'hpConditions':hp,
        'modifierEffects':effects,'blackboardWriteRequests':write_requests,
        'hpWriteEntries':hp_events,'healingNotifications':notifications,
        'blackboardMergeIntervals':merges,'modifierApplications':applications,
        'namedPatchDecisions':patches,'healingProtocolSnapshots':packets,
        'healingActionIntervals':healing_actions,'sourceResetIntervals':reset_intervals,
        'conditionResults':conditions,'skillCreationIntervals':creation_intervals,
        'abilitySourceIntervals':ability_source_intervals,'expressionHelperInputs':helper_inputs,
        'healingAttributeSnapshots':attribute_snapshots,'healingEventInterest':event_interest,
        'healingEventDispatch':event_dispatch,'healingEventQueues':event_queues,
        'resolutionCoverage':coverage,
        'sourceResetSnapshots':[{**json.loads(k),'calls':n} for k,n in resets.items()],
        'callers':[{'hook':h,'returnRva':r,'calls':n} for (h,r),n in caller_counts.items() if h in NUMERIC or h in LOOKUPS or h.startswith('buff.SkillUtil.')]}


def inspect_values(analysis_dir,output,*,gameassembly=None,metadata=None):
    trace.require(not output.exists(),'Buff values: output must be new')
    analysis=trace.read_object(analysis_dir/'buff-paired-analysis.json',32*1024**2)
    trace.require(analysis.get('recordedPairTransportComplete') is True,'Buff values: complete recorded pairs required')
    pins=[fingerprint(analysis_dir/'buff-paired-analysis.json'),*analysis['inputs']]
    for pin in pins:checked_pin(pin)
    profile_path=next(Path(p['path']) for p in pins if Path(p['path']).name=='mission-trace-build-manifest.json')
    decoded=next(Path(p['path']) for p in pins if Path(p['path']).name=='decoded.events.jsonl')
    profile=trace.read_object(profile_path,32*1024**2)
    def events():
        with decoded.open('rb') as stream:
            for n,line in enumerate(stream,1):
                trace.require(n<=trace.Limits().rows and len(line)<=trace.Limits().output_line_bytes and line.endswith(b'\n'),'Buff values: line/row budget')
                yield trace.parse_json(line,'Buff numeric row')
    result={'schema':'endfield.buff-runtime-numeric-observations.v4','inputs':pins,
        'session':analysis['session'],'nativeInputs':profile['files'],'nativeValidationReproved':False,
        **summarize(events(),profile['missionTraceHooks'],profile.get('enumDefinitions',{}))}
    trace.require((gameassembly is None)==(metadata is None),'Buff values: both native input paths required')
    if gameassembly is not None:
        if any(h['name']=='buff.HealPackData._DumpAttributes' for h in profile['missionTraceHooks']):
            result['compiledHealingRoles']=healing_native_roles(profile,gameassembly,metadata)
            classify_healing_snapshots(result,result['compiledHealingRoles'])
        result['compiledQueryRoles']=query_roles(profile,gameassembly,metadata)
        counts=Counter();roles=result['compiledQueryRoles']['returnRvaRoles']
        for row in result['lookupSites']:
            row['compiledQueryRole']=roles.get(row['callerReturnRva'],'unmapped-caller') if row['storage']=='float' else 'double-query-unmapped'
            counts[(row['compiledQueryRole'],row['succeeded'])]+=row['calls']
        result['compiledQueryRoleCounts']=[{'role':r,'succeeded':s,'calls':n} for (r,s),n in counts.items()]
    for pin in pins:checked_pin(pin)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_bytes((json.dumps(result,ensure_ascii=True,allow_nan=False,indent=2)+'\n').encode())
    return result


def query_roles(profile,gameassembly,metadata):
    """Recheck the affected complete query program for recorded caller joins."""
    from scripts.common import check_installed_native_inputs
    from .il2cpp.native_image import open_native_image
    from .il2cpp.body_claims import BodyIndex,_named_direct_call
    from .il2cpp.blackboard_query_flow import prove_float_query_order
    gate=check_installed_native_inputs(profile['files']['gameAssembly']['sha256'],profile['files']['metadata']['sha256'],
        gameassembly=gameassembly,metadata=metadata)
    trace.require(gate.validated,'Buff numeric query roles: native '+gate.status+': '+gate.detail)
    image=open_native_image(gate.gameassembly,gate.metadata);index=BodyIndex(image)
    body=index.body('Beyond.ActionBlackboard','TryGetFloat')
    proof=prove_float_query_order(index,body)
    calls=[row for row in body.rows if _named_direct_call(index,row,'Beyond.Blackboard.TryGetFloat') is not None]
    trace.require(len(calls)==2,'Buff numeric query roles: expected two checked query sites')
    roles={int(row['va'],16)+len(bytes.fromhex(row['bytes']))-image.pe.image_base:role
        for row,role in zip(calls,['direct-query','entity-fallback-query'])}
    after=check_installed_native_inputs(gate.gameassembly_sha256,gate.metadata_sha256,gameassembly=gate.gameassembly,metadata=gate.metadata)
    trace.require(after.validated,'Buff numeric query roles: native inputs changed')
    return {'nativeInputs':profile['files'],'proof':proof,'returnRvaRoles':roles,
        'boundary':'Recorded caller RVAs agree with the selected complete compiled query program. Loaded-image bytes and uninstrumented query invocation identity remain separate.'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis-dir',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--gameassembly',type=Path);parser.add_argument('--metadata',type=Path)
    args=parser.parse_args(argv)
    if not any(args.output.resolve().is_relative_to(REPO_ROOT/r) for r in ('reports','scratch','tmp')):parser.error('--output must be under an ignored output root')
    try:result=inspect_values(args.analysis_dir,args.output,gameassembly=args.gameassembly,metadata=args.metadata)
    except (trace.InspectionError,OSError,ValueError,KeyError,TypeError) as exc:
        print('[buff_runtime_values_inspect] failed: '+str(exc));return 1
    print(json.dumps({'numericPathGroups':len(result['numericPaths']),'healingReturns':len(result['healing']),
        'floatFromDoubleChecks':result['floatFromDoubleChecks'],'resolutionCoverage':result['resolutionCoverage']}));return 0


if __name__=='__main__':raise SystemExit(main())
