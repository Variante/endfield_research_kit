"""Offline ordinary-entry context decoding and explicit damage Process association.

Projection does not authenticate a transport or a native contract. Missing calls
remain unknown; predicate entry snapshots are not native-load observations.
"""
from __future__ import annotations
import math
import struct
from scripts.game_data.mission_trace_invocations import Invocations

ABI = 'win64.entry_context.v1'
SCHEMA = 'endfield.damage-operand-inspection.v2'
PROCESS = 'damage.Action.ProcessDamage'
PACK = 'damage.Pack.GetFinalAttackValue'
GP_NAMES = ('rax','rcx','rdx','rbx','rsp','rbp','rsi','rdi','r8','r9','r10','r11','r12','r13','r14','r15')

class OperandInspectionError(ValueError):
    pass

def require(ok, message):
    if not ok:
        raise OperandInspectionError(message)

def uint(value, label, bits=64):
    require(type(value) is int and 0 <= value < 1 << bits, 'invalid '+label)
    return value

def decode_entry_context(row, hook):
    """Decode fixed architectural blobs; never apply named-method argument ABI."""
    require(hook.get('abiId') == ABI and row.get('schema') == 'endfieldCapture.entryContext.v1'
            and row.get('phase') == 'context', 'entry context schema/ABI mismatch')
    fields = row.get('fields')
    require(isinstance(fields,list) and len(fields)==2, 'entry context requires two fixed blobs')
    blobs=[]
    for field,size in zip(fields,(160,256)):
        require(isinstance(field,dict) and field.get('state')==1 and field.get('sourceAddress')==0 and field.get('value')==0
                and field.get('byteCount')==size,
                'entry context blob not exact architectural context')
        raw=field.get('rawHex')
        require(isinstance(raw,str) and len(raw)==size*2, 'entry context blob width')
        try:
            blob=bytes.fromhex(raw)
        except ValueError as exc:
            raise OperandInspectionError('invalid entry context hex') from exc
        require(len(blob)==size, 'entry context blob width')
        blobs.append(blob)
    gp=dict(zip(GP_NAMES,struct.unpack_from('<16Q',blobs[0])))
    flags,mxcsr,mode,mask,size,reserved=struct.unpack_from('<QIIQII',blobs[0],128)
    require(reserved==0 and mode in (1,2), 'invalid extended-state mode/reserved')
    require((mode==1 and size==512 and mask==0) or (mode==2 and 576<=size<=65536 and mask&3==3),
            'invalid extended-state storage/mask')
    rsp=uint(row.get('originalRsp'),'original RSP')
    require(rsp>0 and rsp==gp['rsp'] and rsp%16==8, 'ordinary entry original RSP mismatch')
    return dict(gp=gp,rflags=flags,mxcsr=mxcsr,xstateMode=mode,xstateMask=mask,xstateBytes=size,
                xmmRawHex=[blobs[1][n*16:(n+1)*16].hex() for n in range(16)])

def project_operand_contexts(paired_rows, contexts, hooks, *, health_hook, raw_hook, pack_offset=832, first_call_conditions=None):
    """Project admitted rows, keeping first scoped post-factor entry per Process.

    Context records carry decoded architecturalContext, explicit
    parentProcessInvocationId and the actual saved caller return address.
    Hook caller scopes must already be authenticated by transport admission.
    """
    entries,returns,owners,processes={}, {}, {}, {}
    pairs=Invocations()
    sequences=set()
    for row in paired_rows:
        seq=uint(row.get('sequence'),'paired sequence')
        require(seq>0 and seq not in sequences,'duplicate sequence')
        sequences.add(seq)
        index=uint(row.get('hookIndex'),'hookIndex',32)
        require(index<len(hooks),'hook index outside profile')
        hook=hooks[index]
        require(row.get('hook')==hook['name'],'paired hook mismatch')
        pairs.observe({**row,'args':row.get('rawArgs')},hook)
        key=(row['threadId'],row['invocationId'])
        if row['phase']=='enter':
            parent=(row['threadId'],row['parentInvocationId'])
            owner=key if row['hook']==PROCESS else owners.get(parent)
            owners[key]=owner;entries[key]={'sequence':seq}
            if key==owner:
                processes[key]=dict(processInvocationId=key[1],threadId=key[0],entrySequence=seq,
                    returnSequence=None,packs=[],factorObservations=[],defenderPoiseFactor=None,
                    healthPredicate={'state':'unobserved','entrySnapshot':None,'actualReturn':None},
                    usesRaw={'state':'unobserved','actualReturn':None})
            if owner is not None and row['hook']==PACK:
                args=row.get('rawArgs')
                require(isinstance(args,list) and bool(args),'missing Pack.this')
                processes[owner]['packs'].append(dict(invocationId=key[1],sequence=seq,address=uint(args[0],'Pack.this')))
            if owner is not None and row['hook']==health_hook:
                state=processes[owner]['healthPredicate']
                require(state['state']=='unobserved','multiple health predicates per Process')
                state.update(state='entry-observed',entrySnapshot=dict(sequence=seq,fields=row.get('fields',[]),
                    boundary='at-predicate-entry snapshot; not proof of native data load or getter route'))
        elif row['phase']=='return':
            returns[key]=seq
            owner=owners.get(key)
            if key in processes:processes[key]['returnSequence']=seq
            if owner is not None and row['hook'] in (health_hook,raw_hook):
                target=processes[owner]['healthPredicate' if row['hook']==health_hook else 'usesRaw']
                require(target['actualReturn'] is None,'duplicate operand return')
                require(row['returnValue'] in (0,1),'invalid actual bool return')
                target.update(state='observed',actualReturn=bool(row['returnValue']),returnSequence=seq,
                              invocationId=key[1])
    receipt=pairs.finish(True)
    for row in contexts:
        seq=uint(row.get('sequence'),'context sequence')
        require(seq>0 and seq not in sequences,'duplicate sequence')
        sequences.add(seq)
        thread=uint(row.get('threadId'),'threadId',32)
        owner=(thread,uint(row.get('parentProcessInvocationId'),'parent Process'))
        require(owner in processes,'context has no explicit Process')
        p=processes[owner]
        require(p['entrySequence']<seq<p['returnSequence'],'context outside active Process')
        parent=(thread,uint(row.get('parentInvocationId'),'parent invocation'))
        require(owners.get(parent)==owner and entries[parent]['sequence']<seq<returns.get(parent,0),
                'context explicit parent is not active in same Process')
        index=uint(row.get('hookIndex'),'context hookIndex',32)
        require(index<len(hooks) and hooks[index].get('abiId')==ABI,'context hook ABI differs')
        hook=hooks[index]
        require(row.get('hook')==hook['name'],'context hook differs')
        caller=uint(row.get('callerGameAssemblyRva'),'caller RVA',32)
        scope=hook.get('captureCallerReturnRvas')
        require(isinstance(scope,str) and caller in {int(v,16) for v in scope.split(',')},'context outside exact caller scope')
        arch=row.get('architecturalContext')
        require(isinstance(arch,dict) and isinstance(arch.get('gp'),dict),'context architectural decode missing')
        rsp=uint(arch['gp'].get('rsp'),'entry RSP')
        require(len(p['packs'])==1,'Process lacks unique own Pack')
        pack=p['packs'][0]
        require(pack['address']>0 and pack['address']==rsp+8+pack_offset and pack['sequence']<seq,
                'context local Pack differs from Process Pack.this')
        xmm=arch.get('xmmRawHex')
        require(isinstance(xmm,list) and len(xmm)==16 and isinstance(xmm[1],str) and len(xmm[1])==32,
                'missing full XMM1 context')
        bits=int.from_bytes(bytes.fromhex(xmm[1])[:8],'little')
        value=struct.unpack('<d',bits.to_bytes(8,'little'))[0]
        p['factorObservations'].append(dict(sequence=seq,hook=hook['name'],callerGameAssemblyRva=caller,
            originalRsp=rsp,localPackAddress=pack['address'],rawBits=bits,rawCarrierObserved=True,
            value=value if math.isfinite(value) else None,finite=math.isfinite(value)))
    for p in processes.values():
        if p['usesRaw']['state']=='observed':
            require(p['healthPredicate']['state']=='observed'
                    and p['healthPredicate']['returnSequence']<p['usesRaw']['returnSequence']
                    and p['healthPredicate']['actualReturn'] is False,
                    'UsesRaw contradicts missing/true prior health predicate return')
        p['factorObservations'].sort(key=lambda r:r['sequence'])
        if p['factorObservations']:
            require(isinstance(first_call_conditions,(list,tuple)) and bool(first_call_conditions)
                    and all(isinstance(v,str) and bool(v.strip()) for v in first_call_conditions),
                    'factor interpretation requires explicit first-call proof conditions')
            first=p['factorObservations'][0]
            raw=p['usesRaw']
            require(raw['state']=='observed' and raw['actualReturn'] is False
                    and raw['returnSequence']<first['sequence'],
                    'post-factor context contradicts missing/true UsesRaw return')
            p['defenderPoiseFactor']=dict(state='observed',**first,
                factorInterpretation='conditional',firstCallConditions=list(first_call_conditions),
                boundary='first admitted post-arithmetic call entry XMM1; conditional on authenticated finite first-call coverage')
        else:p['defenderPoiseFactor']={'state':'unobserved','value':None,'rawBits':None}
        p['boundary']='Predicate entry fields are snapshots; normal returns are actual bool results. No missing-site default, getter route, callback semantics or server authority inferred.'
    return dict(schema=SCHEMA,status='projected',transportAdmitted=False,processes=list(processes.values()),invocations=receipt)

def validate_entry_context_event(row, hook, hooks, invocations, module_base, module_size):
    """Check a context against the live *observed* paired stack without changing it."""
    require(isinstance(row.get('args'),list) and len(row['args'])==8
            and all(type(v) is int and v==0 for v in row['args'])
            and type(row.get('argsReadMask')) is int and row['argsReadMask']==0
            and row.get('returnValue') is None, 'context must not claim ordinary ABI arguments/return')
    thread=uint(row.get('threadId'),'context thread',32)
    stack=invocations.stacks.get(thread,[])
    require(bool(stack),'context lacks active paired scope')
    require(uint(row.get('depth'),'context depth',32)==len(stack)
            and uint(row.get('parentInvocationId'),'context parent')==stack[-1]['invocationId'],
            'context observed parent/depth differs')
    process=[p for p in stack if hooks[p['hookIndex']]['name']==PROCESS]
    require(bool(process),'context lacks active Process')
    process_id=process[-1]['invocationId']
    require(uint(row.get('parentProcessInvocationId'),'context Process')==process_id
            and uint(row.get('invocationId'),'context invocation')==process_id,
            'context Process identity differs from active ancestry')
    entry=uint(row.get('entryRva'),'context entry RVA',32)
    declared=int(hook['rva'],16) if isinstance(hook.get('rva'),str) else hook.get('rva')
    require(entry==declared,'context target entry RVA differs')
    address=uint(row.get('returnAddress'),'context saved return address')
    require(module_base<=address<module_base+module_size,'context saved return outside selected module')
    caller=address-module_base
    require(row.get('callerGameAssemblyRva')==caller,'context caller address/RVA differs')
    scope=hook.get('captureCallerReturnRvas')
    require(isinstance(scope,str) and caller in {int(v,16) for v in scope.split(',')},
            'context saved caller outside selected direct calls')
    return decode_entry_context(row,hook)

def validate_operand_profile(profile):
    """Authenticate retained operand declarations against the reviewed local contract.

    This is retained-source consistency, not a fresh native/build or backend proof.
    """
    import hashlib
    import json
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.damage_operand_capture_prepare import compile_operand_hooks
    contract_path=CONTRACTS_DIR/'damage_operand_capture_native.json'
    contract_raw=contract_path.read_bytes()
    contract=json.loads(contract_raw)
    recipe=json.loads((CONTRACTS_DIR/'damage_operand_capture.json').read_text(encoding='utf-8'))
    require(profile.get('recipeSchema')==recipe['schema'] and profile.get('operandRecipe')==recipe,
            'operand recipe declaration differs')
    proof=profile.get('operandNativeProof')
    require(isinstance(proof,dict) and proof.get('status')=='validated' and proof.get('failures')==[],
            'operand retained native receipt is not validated')
    require(proof.get('schema')==contract['schema'],
            'operand native schema differs: expected='+contract['schema']+' actual='+str(proof.get('schema')))
    current_digest=hashlib.sha256(contract_raw).hexdigest()
    require(isinstance(proof.get('contractSha256'),str) and proof['contractSha256'].lower()==current_digest,
            'operand native receipt contract changed: path='+str(contract_path)+
            ' expected='+current_digest+' actual='+str(proof.get('contractSha256'))[:128])
    require(proof.get('nativeInputs')==contract['nativeInputs'], 'operand native contract input pins differ')
    require(isinstance(profile.get('files'),dict),'operand files must be object')
    for role,key in [('gameAssembly','gameAssemblySha256'),('metadata','metadataSha256')]:
        require(isinstance(profile['files'].get(role),dict),'operand native input must be object')
        require(profile['files'][role].get('sha256')==proof['nativeInputs'][key],
                'operand profile/native input epoch differs')
    call_proof=proof.get('firstCallProof')
    require(isinstance(call_proof,dict) and call_proof.get('conditions')==contract['firstCallGraph']['conditions']
            and call_proof.get('factorUseDominatesFirstCallsInBoundedGraph') is True
            and call_proof.get('xmm1PreservedUntilFirstCall') is True
            and call_proof.get('exceptionResumePathsIncluded') is False,
            'operand first-call proof conditions/boundary differ')
    require(proof.get('sites')==contract['contextEntries']+contract['pairedEntries'],
            'operand complete native entry set differs')
    hooks=profile.get('missionTraceHooks')
    require(isinstance(hooks,list) and all(isinstance(h,dict) for h in hooks),'operand hooks must be object list')
    base=[h for h in hooks if not isinstance(h,dict) or 'operandEntryKey' not in h]
    extra=[h for h in hooks if isinstance(h,dict) and 'operandEntryKey' in h]
    from scripts.game_data.mission_trace_capture_prepare import read_recipe
    base_recipe=read_recipe(CONTRACTS_DIR/recipe['baseRecipe'])
    require(len(base)==len(base_recipe['hooks'])
            and [h.get('name') for h in base]==[h['name'] for h in base_recipe['hooks']],
            'operand inherited base hook set/order differs')
    expected=compile_operand_hooks(proof,recipe,base,contract)
    require(extra==expected and hooks==base+extra,'operand hook descriptor differs from reviewed compilation')
    return {h['name']:h for h in expected}

def inspect_operand_session(session, output_dir, *, local_files=False, limits=None):
    """Admit a retained targeted session and project its bounded decoded stream."""
    import json
    from pathlib import Path
    from scripts.game_data import mission_trace_inspect as trace
    from scripts.game_data.mission_trace_replay import fingerprint
    from scripts.repo_paths import REPO_ROOT
    limits=limits or trace.Limits()
    session,output_dir=Path(session).resolve(),Path(output_dir).resolve()
    require(output_dir.is_relative_to((REPO_ROOT/'reports').resolve()),'operand output must be under reports/')
    output_dir.mkdir(parents=True,exist_ok=True)
    destination=output_dir/'damage.operands.json'
    require(not destination.exists(),'operand output already exists')
    result=dict(schema=SCHEMA,status='blocked',transportAdmitted=False,processes=[],diagnostics=[])
    try:
        inspection=trace.inspect_session(session,output_dir/'trace',local_files=local_files,limits=limits)
        require(inspection.get('status')==('analyzed' if local_files else 'inspected'),'maintained transport inspection failed')
        facts=inspection.get('receiptFacts',{})
        require(facts.get('collectionBoundFailureMarkers')==[] and all(facts.get(k) is True for k in
            ('captureCompleteClaim','healthyClaim','allJournalRowsAccounted','strictTransitionReceiptsConsistent',
             'nativeInputHashesBoundToProfile')),'operand capture requires complete healthy accounted transport')
        artifacts,inventory=(trace.snapshot_local_inventory if local_files else trace.verify_inventory)(session,limits)
        require(inventory.get('inventorySha256')==inspection['inventory'].get('inventorySha256'),'operand inventory changed')
        profile,summary,hooks=trace.bindings(artifacts,limits)
        validate_operand_profile(profile)
        path=output_dir/'trace'/inspection['decodedOutput']
        pin=fingerprint(path,limits.output_bytes)
        contexts=[]
        def paired_rows():
            with path.open('rb') as source:
                for count,line in enumerate(source):
                    require(count<limits.rows and len(line)<=limits.output_line_bytes,'operand decoded row budget')
                    row=trace.parse_json(line,'operand decoded row')
                    if row.get('phase')=='context':contexts.append(row)
                    else:yield row
        result=project_operand_contexts(paired_rows(),contexts,hooks,
            health_hook='damage.Operand.healthPredicateEntry',raw_hook='damage.Operand.usesRawEntry',
            first_call_conditions=profile['operandNativeProof']['firstCallProof']['conditions'])
        require(bool(result['processes']),'no observed Process enclosure')
        require(fingerprint(path,limits.output_bytes)==pin,'operand decoded source changed')
        for artifact in artifacts.values():
            require(fingerprint(artifact['path'],limits.artifact_bytes)['sha256']==artifact['sha256'],
                    'operand retained source changed')
        result.update(status='observed',transportAdmitted=True,sourceContext=dict(sessionPath=str(session),
            inspection=inspection,decodedSource=dict(path=str(path),**pin),inventory=inventory,
            nativeInputs=profile['files'],operandNativeProof=profile['operandNativeProof'],
            nativeValidationReproved=False,backendValidationReproved=False))
    except (ValueError,OSError,KeyError,TypeError,RuntimeError) as exc:
        result=dict(schema=SCHEMA,status='blocked',transportAdmitted=False,processes=[],diagnostics=[dict(
            validator='damage_operand_inspect',failedCheck='transport_or_operand_association',
            sourcePath=str(session),detail=str(exc)[:2048])])
    destination.write_text(json.dumps(result,ensure_ascii=True,separators=(',',':'),allow_nan=False)+'\n',encoding='ascii')
    return result


def main(argv=None):
    import argparse
    from pathlib import Path
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',type=Path,required=True)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--local-files',action='store_true')
    args=parser.parse_args(argv)
    result=inspect_operand_session(args.session,args.output_dir,local_files=args.local_files)
    print('[damage_operand_inspect] '+result['status']+'; Processes='+str(len(result['processes'])))
    for diagnostic in result.get('diagnostics',[]):print(diagnostic['detail'])
    return 0 if result['status']=='observed' else 1


if __name__=='__main__':
    raise SystemExit(main())
