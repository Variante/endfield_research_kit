"""Finite constructor carrier flow into the selected Skill registration block.

This closes the previously explicit intermediate RSI/RBX preservation premise.
Normal Win64 helper returns remain required; heap lifetime and helper effects
are not inferred from register preservation.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
from pathlib import Path

from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.blackboard_vector_transfers import decode_blackboard_vectors
from scripts.game_data.skill_center_fsm_native import _validate as validate_fsm, SCHEMA as FSM_SCHEMA
from scripts.game_data.skill_request_transfer_native import _branch
from scripts.game_data.skill_timing_runtime_native import _require

SCHEMA = 'endfield.skill-center-construction-flow-native-contract.v1'
AUDIT_SCHEMA = 'endfield.skill-center-construction-flow-native-audit.v1'
CONTRACT_PATH = CONTRACTS_DIR / 'skill_center_construction_flow_native.json'


def _walk(rows, *, start, finish, exceptional):
    by = {int(row['va'],16):row for row in rows}
    _require(len(by)==len(rows), 'construction-unique-nodes', 'distinct instructions', len(rows))
    protected = {'rbx','ebx','bx','bl','bh','rsi','esi','si','sil','rsp','esp','sp','spl'}
    allowed = {'mov','lea','test','xor','nop','call','jcc','je','jne','jmp'}
    reached=set(); todo=[start]; edges=[]; calls=[]; terminals=set()
    while todo:
        at=todo.pop()
        if at in (finish,exceptional):
            terminals.add(at); continue
        if at in reached: continue
        _require(at in by, 'construction-branch-target', 'owned instruction or declared exit', at)
        reached.add(at); row=by[at]; raw=bytes.fromhex(row['bytes']); op=row['text'].split()[0]
        _require(op in allowed, 'construction-supported-instruction', sorted(allowed), row)
        register=(row.get('write') or {}).get('register')
        _require(register not in protected, 'construction-saved-carrier-write', 'preserved RSI/RBX/RSP', row)
        if op in ('mov','lea','xor') and not row.get('write') and not row.get('memoryOperation'):
            # Reviewed immediate memory stores have no register output. Refuse
            # a decoder result that silently omits a register destination.
            _require((len(raw)==7 and raw[:2]==b'\xc6\x05') or
                     (len(raw)==7 and raw[:2]==b'\xc7\x40'),
                     'construction-unmodelled-write', 'selected immediate memory store', row)
        if op=='call':
            _require(len(raw)==5 and raw[0]==0xe8, 'construction-direct-call', 'Win64 direct normal-return call', row)
            calls.append(dict(site=at,target=at+5+struct.unpack('<i',raw[1:])[0]))
        target=_branch(raw,at)
        if op in ('jcc','je','jne','jmp'):
            _require(target is not None, 'construction-decoded-branch', 'direct bounded branch', row)
        successors=[at+len(raw)] if target is None else (
            [target] if raw[0] in (0xe9,0xeb) else [at+len(raw),target])
        for nxt in successors:
            edges.append((at,nxt));todo.append(nxt)
    _require(reached==set(by), 'construction-complete-reachability', 'all selected nodes', sorted(set(by)-reached))
    _require(finish in terminals and exceptional in terminals, 'construction-exits', 'normal target and exceptional exit', sorted(terminals))
    # Ensure there is no hidden closed loop in the finite projection.
    can_finish=set(terminals)
    while True:
        added={a for a,b in edges if b in can_finish}-can_finish
        if not added:break
        can_finish.update(added)
    _require(reached<=can_finish, 'construction-exit-reachability', 'each node can reach a declared exit', sorted(reached-can_finish))
    return dict(decodedInstructions=len(rows),directCalls=sorted(calls,key=lambda x:x['site']),
                cfgEdges=sorted(edges),normalTargetReachable=True)


def _validate(image,c,dependency):
    validate_fsm(image,dependency)
    spans={r['id']:r for r in dependency['spans']}
    method=next(r['identity'] for r in dependency['methods'] if r['id']=='machine')
    _require(c['owner']==method, 'construction-owner', 'authenticated Center machine constructor', c['owner'])
    image.validate_method_row(c['owner'],label='centerConstructionFlow')
    start=spans['machineCapture']['rva']+len(bytes.fromhex(spans['machineCapture']['hex']))-6
    finish=spans['skillRegister']['rva']; exceptional=dependency['operands']['machineNullRva']
    _require((c['startRva'],c['finishRva'],c['exceptionalExitRva'])==(start,finish,exceptional),
             'construction-dependency-joins', 'captured entry branch to Skill block', c)
    windows=c['codeWindows']; image.check_windows(windows,label='centerConstructionFlow')
    _require(len(windows)==4 and {w['role'] for w in windows}=={'entryToNull','priorStates','entitySetup','nullExit'},
             'construction-window-coverage', 'four distinct reviewed ranges', windows)
    family=image.unwind_index.family(method[3]); rows=[]
    for w in windows:
        raw=bytes.fromhex(w['hex'])
        owned_until=w['startRva']
        for lo,hi in sorted(a['runtimeTriple'][:2] for a in family['ranges']):
            if lo<=owned_until<hi:owned_until=min(hi,w['endRva'])
        _require(len(raw)==w['endRva']-w['startRva'] and
                 image.pe.bytes_at_va(image.pe.image_base+w['startRva'],len(raw))==raw and
                 owned_until==w['endRva'],
                 'construction-owned-bytes', 'actual bytes in constructor unwind family', w['role'])
        if w['role']=='nullExit':
            _require(w['startRva']==exceptional and len(raw)==6 and raw[0]==0xe8 and raw[-1]==0xcc,
                     'construction-exceptional-exit', 'opaque helper then INT3', w)
            continue
        decoded=decode_blackboard_vectors(image.mapper,raw,image.pe.image_base+w['startRva'])
        _require(b''.join(bytes.fromhex(r['bytes']) for r in decoded)==raw,
                 'construction-decoder-coverage', 'complete selected bytes', w['role'])
        rows.extend(decoded)
    flow=_walk(rows,start=image.pe.image_base+start,finish=image.pe.image_base+finish,
               exceptional=image.pe.image_base+exceptional)
    # Reports use RVAs; the finite walker itself also accepts portable VA fixtures.
    flow['cfgEdges']=[[a-image.pe.image_base,b-image.pe.image_base] for a,b in flow['cfgEdges']]
    flow['directCalls']=[{k:v-image.pe.image_base for k,v in row.items()} for row in flow['directCalls']]
    return flow


def load_skill_center_construction_flow(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path)
    audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',nativeInputs={},rules={},failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerConstructionFlow')
        _require(c['dependency']=='skill_center_fsm_native.json','construction-dependency-name','FSM contract',c['dependency'])
        dep_path=CONTRACTS_DIR/c['dependency']
        dep,dep_digest=read_reviewed_contract(dep_path,schema=FSM_SCHEMA,status='reviewed',label='centerConstructionFlow')
        pins=c['nativeInputs'];_require(pins==dep['nativeInputs'],'construction-input-match',pins,dep['nativeInputs'])
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        flow=_validate(open_native_image(gate.gameassembly,gate.metadata),c,dep)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
        _require(after.status=='validated' and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest and
                 hashlib.sha256(dep_path.read_bytes()).hexdigest().upper()==dep_digest,
                 'construction-bookends','unchanged native inputs and declarations',after.status)
        audit.update(status='validated-conditional-carriers',nativeInputs=pins,flow=flow,
            rules=dict(machineAndBlackboardCarriersPreservedToSkillBlock=True,
                       metadataInitializationBranchCovered=True,entitySetupBranchCovered=True,
                       priorStateConstructionBranchesCovered=True,normalWin64CallsRequired=True,
                       helperHeapEffectsProved=False,actualRegistrationProved=False,lifetimeProved=False),
            evidenceBoundary=c['evidenceBoundary'])
    except (OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError) as error:
        audit.update(status='validation_failed',nativeInputs={},rules={},failures=[dict(check=str(error)[:1400])])
    return audit


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('gameassembly','metadata','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    from scripts.repo_paths import REPO_ROOT
    _require(any(args.output.resolve().is_relative_to(REPO_ROOT/root) for root in ('reports','scratch','tmp')),
             'construction-output-root','ignored output root',str(args.output))
    audit=load_skill_center_construction_flow(gameassembly=args.gameassembly,metadata=args.metadata)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=audit['status'],failures=audit['failures'])))
    return 0 if audit['status']=='validated-conditional-carriers' else 1


if __name__=='__main__':raise SystemExit(main())
