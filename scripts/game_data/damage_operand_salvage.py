"""Validate a retained damage-operand journal prefix without transport admission.

This reads saved files only. A paired local prefix is not a complete capture,
authenticated producer implementation, native-load observation, or numeric
factor admission. The complete transport inspector is deliberately unchanged.
"""
from __future__ import annotations
import argparse,hashlib,json,struct
from collections import Counter
from dataclasses import replace
from pathlib import Path
from scripts.game_data import mission_trace_inspect as trace
from scripts.game_data.mission_trace_invocations import Invocations,PAIRED_ABI
from scripts.game_data.mission_trace_replay import fingerprint
from scripts.game_data.damage_operand_inspect import (ABI,PROCESS,PACK,validate_operand_profile,
    validate_entry_context_event,project_operand_contexts)
from scripts.game_data.contracts import CONTRACTS_DIR

SCHEMA='endfield.damage-operand-salvaged-prefix.v1'
HEALTH='damage.Operand.healthPredicateEntry'
RAW='damage.Operand.usesRawEntry'
DEFAULT_LIMITS=replace(trace.Limits(),journal_bytes=64*1024**2,rows=100000,artifact_bytes=256*1024**2,
    package_bytes=512*1024**2,output_bytes=128*1024**2)
SOURCES=('session.json','private/mission-trace-build-manifest.json','private/mission-trace.activation',
    'private/runtime.conf','private/EndfieldCapture.dll','mission-trace/status.json','mission-trace/events.jsonl')


class SalvageError(ValueError):
    def __init__(self,check,expected,actual,**identity):
        self.diagnostic=dict(validator='damage_operand_salvage',failedCheck=check,expected=expected,actual=actual,**identity)
        super().__init__(check+': expected='+str(expected)[:300]+'; actual='+str(actual)[:500])


def _check(ok,check,expected,actual,**identity):
    if not ok:raise SalvageError(check,expected,actual,**identity)


def _unsigned(value,label,bits=64):
    _check(type(value)is int and 0<=value<1<<bits,'unsigned_'+label,'UInt'+str(bits),value)
    return value


def _field_rows(hook,row,enums):
    args=row['args'];mask=row['argsReadMask'];observed=row.get('fields');phase=row['phase']
    descriptors=[]if phase=='unwind'else hook['fields']
    _check(isinstance(observed,list)and len(observed)==len(descriptors),'event_field_count',len(descriptors),len(observed)if isinstance(observed,list)else type(observed).__name__)
    decoded=[]
    for descriptor,field in zip(descriptors,observed):
        _check(isinstance(field,dict),'event_field_object','object',type(field).__name__)
        _check(mask&(1<<descriptor['arg'])or field.get('state')==2,'event_field_unread_argument','readable argument or unreadable state',descriptor.get('label'))
        if descriptor['kind']==4 and field.get('state')==1:
            _check(field.get('value')==args[descriptor['arg']],'scalar_argument_binding',args[descriptor['arg']],field.get('value'))
        if descriptor['kind']==3 and descriptor['chain0']==4097 and field.get('state')==4:
            _check(args[descriptor['arg']]==0,'null_string_argument',0,args[descriptor['arg']])
        if descriptor['kind']in(6,7)and descriptor['chain0']==4097 and field.get('state')==1:
            _check(field.get('value')==args[descriptor['arg']]+descriptor['offset'],'direct_span_argument_source',args[descriptor['arg']]+descriptor['offset'],field.get('value'))
        value=trace.decode_field(descriptor,field,enums)
        if descriptor['kind']==9:trace.validate_returned_part_phase(row,value)
        if descriptor['kind']==10:_check(phase in('enter','return'),'selector_phase','entry/normal return',phase)
        decoded.append(value)
    trace.validate_bounded_relations(descriptors,decoded)
    return decoded


def _decode_prefix(lines,profile,status,hooks,limits):
    """Validate *all* newline-delimited rows; project only a closed leading scope."""
    stack=Invocations();paired=[];contexts=[];decoded=[];frontier=0;counts=Counter();field_states=Counter();last_qpc_by_thread={};tail=None;row_number=0
    base=_unsigned(status.get('moduleBase'),'moduleBase');image_size=_unsigned(status.get('moduleImageSize'),'moduleImageSize',32)
    _check(base>0 and image_size>0,'module_range','nonzero module base/size',(base,image_size))
    start_qpc=_unsigned(status.get('startQpc'),'startQpc');end_qpc=_unsigned(status.get('statusQpc'),'statusQpc')
    start_tick=_unsigned(status.get('startTickNs'),'startTickNs');end_tick=_unsigned(status.get('statusTickNs'),'statusTickNs')
    _check(end_qpc>=start_qpc and end_tick>=start_tick,'status_clock_bracket','ordered start/status clocks',(start_qpc,end_qpc,start_tick,end_tick))
    for line_number,line in enumerate(lines,1):
        _check(len(line)<=limits.input_line_bytes,'journal_line_budget',limits.input_line_bytes,len(line),line=line_number)
        if not line.endswith(b'\n'):
            _check(next(lines,None)is None,'unterminated_row_not_final','physical terminal tail','later data exists',line=line_number)
            tail=dict(line=line_number,bytes=len(line),sha256=hashlib.sha256(line).hexdigest(),reason='unterminated final row excluded; no row reconstructed')
            break
        _check(row_number<limits.rows,'journal_row_budget',limits.rows,row_number+1,line=line_number)
        try:
            row=trace.parse_json(line,'salvage journal row '+str(line_number))
            _check(isinstance(row,dict),'event_object','object',type(row).__name__)
            seq=_unsigned(row.get('sequence'),'sequence');_check(seq==row_number+1,'sequence_contiguous_file_order',row_number+1,seq)
            index=_unsigned(row.get('hookIndex'),'hookIndex',32);_check(index<len(hooks),'event_hook_index',len(hooks),index)
            hook=hooks[index];_check(row.get('hook')==hook['name'],'event_hook_name',hook['name'],row.get('hook'))
            thread=_unsigned(row.get('threadId'),'threadId',32);_check(thread>0,'event_thread','nonzero',thread)
            qpc=_unsigned(row.get('qpc'),'qpc');tick=_unsigned(row.get('tickNs'),'tickNs')
            _check(start_qpc<=qpc<=end_qpc and start_tick<=tick<=end_tick,'event_clock_bracket','within retained status bracket',(qpc,tick))
            _check(qpc>=last_qpc_by_thread.get(thread,0),'same_thread_qpc_order','nondecreasing',qpc);last_qpc_by_thread[thread]=qpc
            if hook.get('abiId')==ABI:
                _check(row.get('schema')=='endfieldCapture.entryContext.v1'and row.get('phase')=='context','context_schema_phase','entryContext/context',(row.get('schema'),row.get('phase')))
                _check(isinstance(row.get('fields'),list)and all(isinstance(field,dict)and all(type(field.get(k))is int for k in('state','sourceAddress','value','byteCount'))for field in row['fields']),'context_blob_scalar_types','architectural field tags/counts/zeroes must be integers',row.get('fields'))
                arch=validate_entry_context_event(row,hook,hooks,stack,base,image_size)
                value=dict(row,rawArgs=row['args'],architecturalContext=arch);contexts.append(value)
            else:
                _check(row.get('schema')=='endfieldCapture.missionTraceEntry.v3','paired_event_schema','missionTraceEntry.v3',row.get('schema'))
                abi=PAIRED_ABI.fullmatch(hook.get('abiId',''));_check(abi is not None,'paired_hook_abi','supported paired ABI',hook.get('abiId'))
                args=row.get('args');_check(isinstance(args,list)and len(args)==8,'event_arguments','eight raw UInt64 slots',args)
                for arg in args:_unsigned(arg,'argument')
                mask=_unsigned(row.get('argsReadMask'),'argsReadMask',8);_check(mask==(1<<int(abi[2]))-1,'paired_argument_mask',(1<<int(abi[2]))-1,mask)
                address=_unsigned(row.get('returnAddress'),'returnAddress');caller=address-base if base<=address<base+image_size else 0
                _check(type(row.get('callerGameAssemblyRva'))is int and row['callerGameAssemblyRva']==caller,'caller_address_rva',caller,row.get('callerGameAssemblyRva'))
                scope=hook.get('captureCallerReturnRvas')
                if scope:
                    expected={int(value,16)for value in scope.split(',')};_check(caller in expected,'paired_caller_scope',sorted(expected),caller)
                active=[entry for entry in stack.stacks.get(thread,[])if hooks[entry['hookIndex']]['name']==PROCESS]
                process_owner=row['invocationId']if row.get('phase')=='enter'and hook['name']==PROCESS else active[-1]['invocationId']if active else None
                stack.observe(row,hook)
                fields=_field_rows(hook,row,profile.get('enumDefinitions',{}));value=dict(row,rawArgs=args,fields=fields,nearestProcessInvocationId=process_owner);paired.append(value)
            decoded.append(value);counts[hook['name']]+=1;field_states.update(field.get('state')for field in row.get('fields',[])if isinstance(field,dict));row_number+=1
            if not any(stack.stacks.values()):frontier=row_number
        except (ValueError,KeyError,TypeError,IndexError)as error:
            if isinstance(error,SalvageError):error.diagnostic.update(line=line_number,sequence=row.get('sequence')if isinstance(locals().get('row'),dict)else None,hook=row.get('hook')if isinstance(locals().get('row'),dict)else None)
            else:raise SalvageError('event_validation','valid profile/ABI/stack/field record',str(error)[:1000],line=line_number,sequence=row.get('sequence')if isinstance(locals().get('row'),dict)else None,hook=row.get('hook')if isinstance(locals().get('row'),dict)else None)from error
            raise
    receipt=stack.finish(False)
    _check(receipt['unwound']==0,'unwound_prefix','no unwind in locally projected prefix',receipt)
    _check(frontier>0,'closed_leading_scope','nonempty prefix ending with every observed stack closed',receipt)
    prefix_paired=[r for r in paired if r['sequence']<=frontier];prefix_contexts=[r for r in contexts if r['sequence']<=frontier]
    proof=profile['operandNativeProof']['firstCallProof']
    sites=[site for site in profile['operandNativeProof']['sites']if site.get('type')=='entryContext']
    offsets={site.get('context',{}).get('localPackOffsetFromEntryRsp')for site in sites}
    _check(sites and len(offsets)==1 and all(site.get('context',{}).get('factorRegister')=='xmm1'
        and site['context'].get('factorBits')==64 for site in sites),
        'factor_context_pack_declaration','one authenticated XMM1 low64/RSP-local Pack relation',sites)
    local_pack_offset=next(iter(offsets));_check(type(local_pack_offset)is int and local_pack_offset>=struct.calcsize('<Q'),
        'factor_context_pack_offset','ordinary entry RSP offset including return address',local_pack_offset)
    projection=project_operand_contexts(prefix_paired,prefix_contexts,hooks,health_hook=HEALTH,raw_hook=RAW,
        pack_offset=local_pack_offset-struct.calcsize('<Q'),
        first_call_conditions=proof['conditions'])
    _check(bool(projection['processes']),'process_prefix','at least one locally closed Process',0)
    grouped_entries={}
    normal_returns={(r['threadId'],r['invocationId']):r for r in prefix_paired if r['phase']=='return'}
    for row in prefix_paired:
        if row['phase']=='enter':grouped_entries.setdefault((row['threadId'],row.get('nearestProcessInvocationId')),[]).append(row)
    for process in projection['processes']:
        process['localAssociationValidated']=True;process['transportAdmitted']=False
        process['healthPredicate']['state']='salvaged-prefix-return'if process['healthPredicate']['actualReturn']is not None else'salvaged-prefix-unobserved'
        process['usesRaw']['state']='salvaged-prefix-return'if process['usesRaw']['actualReturn']is not None else'salvaged-prefix-unobserved'
        factor=process['defenderPoiseFactor']
        factor.update(state='salvaged-prefix-carrier-candidate'if process['factorObservations']else'salvaged-prefix-unobserved',
            numericFactorAdmitted=False,completeDeliveryProved=False,backendImplementationProved=False,
            factorInterpretation='unadmitted-carrier-candidate-checkpoint-semantics-unproved',
            compiledCheckpointSemanticsProved=False,localDeliveryProved=False,
            boundary='Saved low64 XMM1 carrier candidate only. Raw prefix/checkpoint consistency alone does not prove compiled checkpoint semantics, local delivery, backend implementation or numeric factor admission.')
        entries=grouped_entries.get((process['threadId'],process['processInvocationId']),[])
        own=next(r for r in entries if r['invocationId']==process['processInvocationId']);health=[r for r in entries if r['hook']==HEALTH]
        snapshots={f['label']:f for f in own['fields']};groups={}
        for r in entries:
            if r['hook']=='buff.Attributes.GetValue':
                f={v['label']:v for v in r['fields']};uid=f.get('attributesInstanceUid',{}).get('value');key=(r['rawArgs'][0],uid)
                groups[key]=groups.get(key,0)+1
        modifiers=[r for r in entries if r['hook']=='buff.AbilitySystem.ApplyModifier']
        modifier=modifiers[0]if len(modifiers)==1 and (process['threadId'],modifiers[0]['invocationId'])in normal_returns else None
        modifier_fields={f['label']:f for f in modifier['fields']}if modifier else{}
        health_bindings=[]
        for event in health:
            hfields={f['label']:f for f in event['fields']};observed=hfields.get('defenderIdentity',{})
            _check(observed.get('state')==1 and observed.get('value')==event['rawArgs'][0],'health_receiver_snapshot_arg',event['rawArgs'][0],observed)
            health_bindings.append(dict(sequence=event['sequence'],receiverPointer=event['rawArgs'][0],receiverSnapshotEqualsArgument=True,
                dataPointerEntrySnapshot=hfields.get('defenderDataIdentity'),healthTypeEntrySnapshot=hfields.get('defenderHealthTypeSnapshot'),
                actualGetterLoadProved=False,processDefenderObjectIdentityProved=False,
                healthReceiverEqualsModifierReceiver=event['rawArgs'][0]==modifier['rawArgs'][0]if modifier else None,
                modifierBindingState='unique-normal-return-in-same-Process'if modifier else'unobserved-or-ambiguous',
                modifierInvocationId=modifier['invocationId']if modifier else None,
                modifierReceiverPointer=modifier['rawArgs'][0]if modifier else None,
                modifierTargetEntrySnapshots={k:modifier_fields.get(k)for k in('targetServerId','targetBattleInstanceId','targetEntityName','attributesIdentity','attributesInstanceUid')}))
        process['bindingBoundary']=dict(healthEntries=health_bindings,processRawInputTargetCarrier=own['rawArgs'][2],
            processEffectSourceAttributeEntrySnapshots={k:snapshots.get(k)for k in('effectSourceAttributesIdentity','effectSourceAttributesInstanceUid')},
            scopedAttributeReceiverUidSnapshots=[dict(pointer=k[0],uid=k[1],count=v)for k,v in sorted(groups.items())],
            packThisSource='unique same-Process Pack.GetFinalAttackValue entry and exact context RSP-relative local address',
            defenderPointerFromOpaqueInputTargetProved=False,attributeUidIsObjectLifetimeProof=False,
            boundary='Same-thread explicit Process enclosure and observed pointer/UID snapshots; opaque target conversion, live getter loads and object lifetime remain unproved.')
    return dict(processes=projection['processes'],invocations=receipt,prefixInvocations=projection['invocations'],
        validatedRows=row_number,projectedPrefixLastSequence=frontier,projectedRows=frontier,validatedContextRows=len(contexts),projectedContextRows=len(prefix_contexts),
        excludedValidatedSuffixRows=row_number-frontier,excludedUnterminatedTail=tail,hookCounts=dict(counts),
        lastEventQpc=decoded[-1]['qpc'],lastEventTickNs=decoded[-1]['tickNs'],maximumEventQpc=max(r['qpc']for r in decoded),maximumEventTickNs=max(r['tickNs']for r in decoded),decodedFieldStateCounts=dict(field_states),
        projectorStatusRetainedForDiagnostics=projection['status'],projectorObservedStateNotAdmitted=True)


def _retained_dependency_pins(profile,limits):
    """Bookend every JSON dependency read by the reused declaration binders."""
    from scripts.game_data.damage_runtime_branch_abi import CONTRACT as abi_contract
    pending=[CONTRACTS_DIR/'damage_operand_capture_native.json',CONTRACTS_DIR/'damage_operand_capture.json',
             CONTRACTS_DIR/profile['operandRecipe']['baseRecipe'],abi_contract]
    seen=set();pins=[]
    while pending:
        path=Path(pending.pop()).resolve()
        _check(path.is_relative_to(CONTRACTS_DIR.resolve())and path.parent==CONTRACTS_DIR.resolve()and path.suffix=='.json',
            'contract_dependency_path','reviewed sibling contract',str(path))
        if path in seen:continue
        _check(len(seen)<16,'contract_dependency_budget',16,len(seen)+1)
        seen.add(path);pin=fingerprint(path,limits.json_bytes);pins.append(pin)
        value=trace.parse_json(path.read_bytes(),'retained dependency '+path.name)
        ancestor=value.get('inheritsRecipe')
        if ancestor is not None:
            _check(isinstance(ancestor,str)and Path(ancestor).name==ancestor,'recipe_ancestor_path','sibling filename',ancestor)
            pending.append(CONTRACTS_DIR/ancestor)
    return pins


def _checkpoint_consistency(status,result,journal_bytes):
    checks=[]
    def compare(name,expected,actual):
        checks.append(dict(check=name,expected=expected,actual=actual,
            consistent=type(expected)is type(actual)and expected==actual))
    compare('journalBytes_vs_bytesWritten',journal_bytes,status.get('bytesWritten'))
    for key in('attempted','admitted','written'):compare('validatedRows_vs_'+key,result['validatedRows'],status.get(key))
    for key in('dropped','unrecorded','queueFullDrops','contentionDrops','pairingFailures'):compare('retained_zero_claim_'+key,0,status.get(key))
    for key,state in(('unreadableFields',2),('truncatedFields',3),('nullFields',4)):
        compare('decodedFieldStates_vs_'+key,result['decodedFieldStateCounts'].get(state,0),status.get(key))
    for hook in status.get('hooks',[]):
        compare('hookRows_vs_calls_'+str(hook.get('name')),result['hookCounts'].get(hook.get('name'),0),hook.get('calls'))
    ordered=(type(status.get('statusQpc'))is int and result['maximumEventQpc']<=status['statusQpc']
        and type(status.get('statusTickNs'))is int and result['maximumEventTickNs']<=status['statusTickNs'])
    checks.append(dict(check='events_not_after_status_checkpoint',expected=True,actual=ordered,consistent=ordered))
    return dict(status='consistent'if all(c['consistent']for c in checks)else'mismatched',checks=checks,
        maximumEventQpc=result['maximumEventQpc'],lastEventQpc=result['lastEventQpc'],statusQpc=status.get('statusQpc'),
        compiledCheckpointSemanticsProved=False,localDeliveryProved=False,
        boundary='Byte/row/clock/counter consistency only. Compiled publication order, counter monotonicity/no-reset epochs, unreadable accounting, and complete scoped hook enablement are not established here.')


def salvage_operand_session(session,output_dir,*,limits=DEFAULT_LIMITS):
    session=Path(session).resolve();output_dir=Path(output_dir).resolve()
    from scripts.repo_paths import REPO_ROOT
    _check(output_dir.is_relative_to((REPO_ROOT/'reports').resolve()),'output_scope','under reports/',str(output_dir))
    _check(not output_dir.is_relative_to(session)and not session.is_relative_to(output_dir),'output_separate','outside original session',str(output_dir))
    destination=output_dir/'damage.operands.salvaged-prefix.json';_check(not destination.exists(),'output_exists','new report',str(destination));output_dir.mkdir(parents=True,exist_ok=True)
    report=dict(schema=SCHEMA,status='blocked',transportAdmitted=False,runtimeCompletenessProved=False,numericOperandAdmission=False,
        backendImplementationProved=False,compiledCheckpointSemanticsProved=False,localDeliveryProved=False,nativeValidationReproved=False,producerOriginAuthenticated=False,processes=[],diagnostics=[])
    sources=[]
    try:
        artifacts={}
        for name in SOURCES:
            path=trace.safe_path(session,name);pin=fingerprint(path,limits.journal_bytes if name.endswith('events.jsonl')else limits.artifact_bytes);sources.append(pin)
            artifacts[name]=dict(path=path,bytes=pin['bytes'],sha256=pin['sha256'])
        _check(sum(p['bytes']for p in sources)<=limits.package_bytes,'source_package_budget',limits.package_bytes,sum(p['bytes']for p in sources))
        # Reuse declaration/activation/ABI binding with the retained status, never
        # write a summary or claim a completed transport receipt.
        adapter={**artifacts,'mission-trace/summary.json':artifacts['mission-trace/status.json']}
        retained_session=trace.bound_object(artifacts,'session.json',limits)
        dll=artifacts['private/EndfieldCapture.dll']
        _check(type(retained_session.get('runtimeBytes'))is int and retained_session['runtimeBytes']==dll['bytes']
            and retained_session.get('runtimeSha256')==dll['sha256'],'staged_dll_session_identity',
            dict(bytes=dll['bytes'],sha256=dll['sha256']),{k:retained_session.get(k)for k in('runtimeBytes','runtimeSha256')})
        retained_profile=trace.bound_object(artifacts,'private/mission-trace-build-manifest.json',limits)
        sources.extend(_retained_dependency_pins(retained_profile,limits))
        profile,status,hooks=trace.bindings(adapter,limits);validate_operand_profile(profile)
        _check(status.get('pairingFailures')==0 and type(status.get('pairingFailures'))is int,'status_pairing_failures',0,status.get('pairingFailures'))
        journal=artifacts['mission-trace/events.jsonl']['path']
        with journal.open('rb')as stream:
            def lines():
                while line:=stream.readline(limits.input_line_bytes+1):yield line
            result=_decode_prefix(lines(),profile,status,hooks,limits)
        for pin in sources:
            after=fingerprint(Path(pin['path']),max(limits.artifact_bytes,limits.journal_bytes,limits.json_bytes))
            _check(after==pin,'source_bookend',pin,after)
        report.update(result,status='salvaged-prefix',locallyPairedProcessCount=len(result['processes']),savedCarrierRowsRecovered=sum(len(p['factorObservations'])for p in result['processes']),admittedNumericRows=0,sources=sources,sessionPath=str(session),
            retainedStatusClaims={k:status.get(k)for k in('complete','stopped','quiescent','healthy','writeComplete','finalCountersStable','attempted','admitted','written','dropped','unrecorded','startQpc','statusQpc','startTickNs','statusTickNs','bytesWritten','unreadableFields','truncatedFields','nullFields','queueFullDrops','contentionDrops','pairingFailures')},
            checkpointConsistency=_checkpoint_consistency(status,result,artifacts['mission-trace/events.jsonl']['bytes']),
            profileActivationConsistencyValidated=True,stagedDllSessionIdentityConsistent=True,retainedNativeHashBindingsConsistent=True,
            statusUsedForDeclarationBindingOnly='mission-trace/status.json; no summary synthesized',
            boundary='All available complete rows validated; only explicitly closed leading local scopes projected. This is salvaged-prefix evidence, never complete transport, live native validation, backend implementation proof or numeric admission.')
    except (OSError,ValueError,KeyError,TypeError,IndexError,RuntimeError)as error:
        diagnostic=error.diagnostic if isinstance(error,SalvageError)else dict(validator='damage_operand_salvage',failedCheck='retained_source_or_profile_binding',detail=str(error)[:2000])
        diagnostic.update(sourcePath=str(session),sourcePins=sources);report.update(status='blocked',processes=[],diagnostics=[diagnostic])
    destination.write_text(json.dumps(report,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n',encoding='ascii')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--session',type=Path,required=True);parser.add_argument('--output-dir',type=Path,required=True)
    args=parser.parse_args(argv);result=salvage_operand_session(args.session,args.output_dir)
    print(json.dumps({k:result[k]for k in('status','transportAdmitted','runtimeCompletenessProved','numericOperandAdmission','diagnostics')},indent=2));return 0 if result['status']=='salvaged-prefix'else 1
if __name__=='__main__':raise SystemExit(main())
