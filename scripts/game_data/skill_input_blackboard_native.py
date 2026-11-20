"""Conditional typed blackboard writer after the selected CanCastSkill result."""
from __future__ import annotations
import argparse,hashlib,json,struct
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
from scripts.game_data.il2cpp.blackboard_vector_transfers import decode_blackboard_vectors
from scripts.game_data.il2cpp.context import generic_method_candidates
from scripts.game_data.skill_request_transfer_native import _branch
from scripts.game_data.skill_timing_runtime_native import _require,_validate_fields
from scripts.game_data.skill_ai_dispatch_native import _strict

CONTRACT_PATH=CONTRACTS_DIR/'skill_input_blackboard_native.json'
SCHEMA='endfield.skill-input-blackboard-native-contract.v1'
BB='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterBlackboard'
STATE='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterState'
OWNER='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine'
DATA='Beyond.Gameplay.Core.SkillCastInputData'


def _rules():
    return dict(originalPathOnly=True,canCastFalseSkipsBlackboardCallsAndWrites=True,firstGetterRequestsDispose=True,
        secondGetterIndependent=True,secondGetterNullCheckedAfterCopyFrom=True,copyResultBytes=88,
        typedDestination=BB+'::skillInputData',destinationTypePremiseRequired=True,normalWin64CallsRequired=True,
        coherentObjectsAndLocalMemoryRequired=True,originalCanCastBoolReturned=True,providedClosedGetterMethodInfoProved=True,
        compiledGetterClosedDeclarationProved=False,reviewedClosedGetterCandidateCount=0,blackboardGetterInstanceTypeProved=False,
        sameBlackboardInstanceProved=False,stateConsumerDeliveryProved=False,disposeIndirectEffectsProved=False,
        normalReturnedWriterPathOnly=True,viewSourceLocalsPremiseRequired=True,helperOrder=['get-blackboard-1','dispose-field-1','get-blackboard-2','copy-from-view',
            'require-destination-nonnull','store-field-2','write-barrier'],barrierEffectsProved=False)


def _declarations(image,c):
    ctx=NativeReferenceContext(image);md=image.metadata
    expected={'owner':(OWNER,'_ToSkill'),'copy':(DATA,'CopyFrom'),'dispose':(DATA,'Dispose')}
    _require(set(c['methods'])==set(expected),'bb-method-coverage',expected,c['methods'])
    for role,row in c['methods'].items():
        _require(tuple(row['identity'][1:3])==expected[role],'bb-method-nominal',expected[role],row)
        m=md.methods[image.validate_method_row(row['identity'],label='skillInputBlackboard')]
        actual=dict(returnType=ctx.type_name(m.return_type),parameters=[dict(name=md.string(p.name_index),type=ctx.type_name(p.type_index))for p in md.parameters_for(m)],slot=m.slot,isStatic=bool(m.flags&16))
        _require(_strict(actual,{k:row[k]for k in actual}),'bb-method-signature',row,actual)
    _validate_fields(image,[c['field']]);f=c['field']
    _require((f['type'],f['name'],f['valueType'],f['ordinaryKind'],f['static'])==(BB,'skillInputData',DATA,17,False),'bb-destination-field','named value field',f)
    size=c['typeSize'];td=image.named_types[DATA];ptr=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);raw=image.pe.bytes_at_va(ptr,16)
    _require(size['type']==DATA and raw.hex()==size['hex']and ctx.is_value_type(DATA)and int.from_bytes(raw[:4],'little')-c['operands']['boxedHeaderBytes']==c['operands']['fieldBytes']==88,'bb-input-extent','typed 88-byte input',size)


def _contexts(image,c):
    rows=c['contexts'];sites=c['sites'];expected_sites=[sites['getter1Call'],sites['getter2Call']]
    _require(len(rows)==2 and len({r['rva']for r in rows})==2,'bb-context-coverage','two distinct getter requests',rows)
    specs=set()
    for row,call in zip(rows,expected_sites):
        actual=derive_typed_usage_context(image,row['rva'],label='skillInputBlackboard')
        _require(_strict(actual,row['result'])and actual.get('typeName')=='Beyond.Gameplay.StateMachine`2'
            and actual.get('methodName')=='get_stateBlackboard'and actual.get('classArguments')==[STATE,BB]
            and actual.get('methodArguments')==[],'bb-provided-methodinfo','selected closed getter request',actual)
        raw=image.pe.bytes_at_va(image.pe.image_base+row['rva'],call+5-row['rva'])
        _require(raw[:3]==bytes.fromhex('488b15')and raw[7:10]==bytes.fromhex('488bce')and raw[10]==0xe8
            and len(raw)==15 and call+5+struct.unpack('<i',raw[11:])[0]==c['physicalGetterRva'],
            'bb-getter-request-call','RDX MethodInfo/RCX RSI -> selected physical call',raw.hex());specs.add(actual['methodSpecIndex'])
    reg=image.registration;code=image.mapper.code_registration_summary(image.pe,image.code_registration);table=int(reg['genericMethodTable'],16)
    candidates=generic_method_candidates(image.pe.bytes_at_va(table,reg['genericMethodTableCount']*16),reg['genericMethodTableCount'],reg['methodSpecsCount'],specs,
        code['genericMethodPointersCount'],code['invokerPointersCount'],source=str(image.gameassembly),offset=table)
    _require(len(candidates)==0,'bb-reviewed-closed-candidates','reviewed no closed entry; do not promote physical getter identity',candidates)


def _validate(image,c):
    _declarations(image,c);_contexts(image,c);windows={x['role']:x for x in c['codeWindows']}
    _require(set(windows)=={'writer','return'}and len(windows)==len(c['codeWindows']),'bb-window-coverage','writer/return',windows)
    image.check_windows(c['codeWindows'],label='skillInputBlackboard');family=image.unwind_index.family(c['methods']['owner']['identity'][3]);by={}
    for role,w in windows.items():
        raw=bytes.fromhex(w['hex']);cursor=w['startRva']
        for lo,hi in sorted(x['runtimeTriple'][:2]for x in family['ranges']):
            if lo<=cursor<hi:cursor=min(hi,w['endRva'])
        _require(len(raw)==w['endRva']-w['startRva']and image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(raw))==raw
            and cursor==w['endRva'],'bb-owned-window',role,w)
        rows=decode_blackboard_vectors(image.mapper,raw,image.pe.image_base+w['startRva'])
        _require(sum(len(bytes.fromhex(r['bytes']))for r in rows)==len(raw),'bb-decoder-complete',role,rows)
        for row in rows:by[int(row['va'],16)-image.pe.image_base]=row
    sites=c['sites'];flow=c['flow'];d=c['operands'];start=windows['writer']['startRva'];field=c['field']['offset']
    def raw(at):return bytes.fromhex(by[at]['bytes'])
    def sequence(at,parts):
        for part in parts:_require(raw(at)==part,'bb-exact-sequence','selected instruction',by[at]);at+=len(part)
        return at
    h=bytes.fromhex;pack=lambda value:struct.pack('<i',value)
    _require(raw(start)==h('0fb6f8')and raw(start+3)==h('84c0')and start+5==sites['canCastFalseBranch']
        and raw(sites['canCastFalseBranch'])[:2]==h('0f84')and _branch(raw(sites['canCastFalseBranch']),sites['canCastFalseBranch'])==sites['falseNode'],
        'bb-admission-bool-edge','capture EDI, test AL, false skips writer',sites)
    _require(raw(sites['falseNode'])==h('4032ff')and _branch(raw(sites['falseNode']+3),sites['falseNode']+3)==sites['returnCapture']
        and raw(sites['returnCapture'])==h('400fb6c7'),'bb-return-original-bool','false clears DIL; normal return captures DIL',sites)
    _require(sites['getter1Return']==sites['getter1Call']+5 and sites['getter2Return']==sites['getter2Call']+5
        and sites['disposeReturn']==sites['disposeCall']+5 and sites['copyReturn']==sites['copyCall']+5 and sites['barrierReturn']==sites['barrierCall']+5,
        'bb-call-return-sites','adjacent selected call returns',sites)
    _require(sites['disposeReturn']==c['contexts'][1]['rva']and sites['barrierReturn']==sites['returnCapture']
        and sites['bb2NullCheck']+9==sites['firstStore'],'bb-helper-stage-adjacency','dispose -> second getter; copy nullcheck -> store -> barrier -> return',sites)
    _require(raw(sites['copyViewLea'])==h('488d5424')+bytes([d['viewStack']])
        and raw(sites['copyOutputLea'])==h('488d4d')+d['copyOutRbp'].to_bytes(1,'little',signed=True),
        'bb-copy-buffer-arguments','explicit local input/output buffer addresses',sites)
    first=sequence(sites['getter1Return'],[h('4885c0')]);_require(raw(first)[:2]==h('0f84')and _branch(raw(first),first)==flow['exceptionalExitRva'],'bb-first-nonnull','opaque exceptional exit',by[first])
    _require(sequence(first+6,[h('488d48')+bytes([field]),h('33d2')])==sites['disposeCall'],'bb-dispose-destination','first result named field address',sites)
    _require(raw(sites['bb2Capture'])==h('488bd8')and sites['getter2Return']<sites['bb2Capture']<sites['copyCall']<sites['bb2NullCheck'],'bb-second-receiver-order','save getter2 before copy then check null',sites)
    _require(raw(sites['bb2NullCheck'])==h('4885db')and _branch(raw(sites['bb2NullCheck']+3),sites['bb2NullCheck']+3)==flow['exceptionalExitRva'],'bb-second-nonnull','opaque exit after CopyFrom',sites)
    end=sequence(sites['copyReturn'],[h('f20f106850'),h('0f1000'),h('0f104810'),h('0f105020'),h('0f105830'),h('0f106040')])
    _require(end==sites['bb2NullCheck'],'bb-copy-result-loads','all 88 result bytes loaded before nonnull check',end)
    end=sequence(sites['firstStore'],[h('0f1143')+bytes([field]),h('488d4b')+bytes([field]),h('0f114b')+bytes([field+16]),
        h('0f1153')+bytes([field+32]),h('0f115b')+bytes([field+48]),h('0f1163')+bytes([field+64]),h('f20f116b')+bytes([field+80])])
    _require(end==sites['barrierCall'],'bb-whole-value-store','88-byte named field then barrier request',end)
    calls={sites['getter1Call']:c['physicalGetterRva'],sites['disposeCall']:c['methods']['dispose']['identity'][3],sites['getter2Call']:c['physicalGetterRva'],sites['copyCall']:c['methods']['copy']['identity'][3],sites['barrierCall']:c['barrierRva']}
    edges={};allowed={'mov','movzx','movups','movaps','movsd','xor','lea','test','call','jcc','je','jne','jmp','pop','add','ret'}
    for at,r in by.items():
        b=raw(at);_require(r['text'].split()[0]in allowed,'bb-finite-instruction','supported exact instruction vocabulary',r)
        destination=_branch(b,at);n=at+len(b)
        edges[at]=[]if b[0]==0xc3 else [destination]if b[0]in (0xe9,0xeb)else[n,destination]if destination is not None else[n]
        if b[0]==0xe8:_require(at in calls and at+5+struct.unpack('<i',b[1:])[0]==calls[at],'bb-call-target',calls,r)
    def reach(begin,stop=None):
        todo=[begin];seen=set()
        while todo:
            at=todo.pop()
            if at in seen or at==stop or at==flow['exceptionalExitRva']:continue
            _require(at in by,'bb-control-target','owned instruction or exceptional exit',at);seen.add(at);todo.extend(edges[at])
        return seen
    false=reach(sites['falseNode']);_require(all((by[at].get('memoryOperation')or{}).get('direction')!='store'for at in false),'bb-false-no-field-store','no false-path memory store',false);_require(not(set(calls)&false),'bb-false-skips-helpers','no helper on false path',false)
    true=reach(start+11);returns={at for at in true if raw(at)[0]==0xc3};_require(len(returns)==1,'bb-normal-return','one selected normal return',returns)
    for at in calls:_require(at in true and not(returns&reach(start+11,at)),'bb-helper-order-dominance','each helper required before normal return',at)
    for at in true:
        r=by[at];register=(r.get('write')or{}).get('register')
        if sites['bb2Capture']<at<=sites['barrierCall']:_require(register not in ('rbx','ebx','bx','bl','bh'),'bb-destination-carrier','normal Win64 RBX preserved',r)
        if start<at<sites['returnCapture']:_require(register not in ('rdi','edi','di','dil'),'bb-predicate-carrier','normal Win64 RDI preserved',r)
        if sites['copyViewLea']<at<sites['copyCall']:_require(register not in ('rdx','edx','dx','dl','dh')and raw(at)[0]!=0xe8,'bb-copy-input-address-carrier','RDX local input reaches CopyFrom',r)
        if sites['copyOutputLea']<at<sites['copyCall']:_require(register not in ('rcx','ecx','cx','cl','ch')and raw(at)[0]!=0xe8,'bb-copy-output-address-carrier','RCX local output reaches CopyFrom',r)
        if sites['getter2Return']<=at<sites['bb2Capture']:_require(register not in ('rax','eax','ax','al','ah')and raw(at)[0]!=0xe8,'bb-getter-result-carrier','same RAX until RBX save',r)
        if at>=flow['epilogueRva']and at<windows['return']['endRva']:_require(register not in ('rax','eax','ax','al','ah'),'bb-return-bool-carrier','EAX reaches return',r)
    _require(_strict(c['rules'],_rules()),'bb-rules-boundary',_rules(),c['rules'])
    return dict(rules=_rules(),callSites=sites,providedBlackboardType=BB,closedGetterCandidates=0,decodedInstructions=len(by),evidenceBoundary=c['evidenceBoundary'])


def load_skill_input_blackboard(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);a=dict(schema='endfield.skill-input-blackboard-native-audit.v1',status='validation_failed',rules={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='skillInputBlackboard');pins=c['nativeInputs'];g=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);a.update(status=g.status,detail=g.detail)
        if g.status!='validated':return a
        result=_validate(open_native_image(g.gameassembly,g.metadata),c);after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'bb-bookends','unchanged selected inputs',after.status);a.update(result,status='validated-conditional-writer',nativeInputs=pins)
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:a.update(status='validation_failed',rules={},failures=[dict(check=str(e)[:1200],source=str(path))])
    return a


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly','metadata','output'):p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args();r=load_skill_input_blackboard(gameassembly=args.gameassembly,metadata=args.metadata)
    from scripts.repo_paths import REPO_ROOT
    _require(any(args.output.resolve().is_relative_to(REPO_ROOT/x)for x in ('reports','scratch','tmp')),'bb-output-root','ignored',args.output)
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r));return 0 if r['status']=='validated-conditional-writer'else 1


if __name__=='__main__':raise SystemExit(main())
