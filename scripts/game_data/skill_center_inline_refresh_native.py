"""Conditional local proof of CenterStateMachine's inlined state refresh.

The selected normal machine schedule is proved conditional on opaque helper results.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct
from scripts.common import check_installed_native_inputs
from scripts.repo_paths import REPO_ROOT
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image, read_reviewed_contract
from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext, validate_reference_ancestor_chain
from scripts.game_data.skill_timing_runtime_native import _require, _validate_fields
from scripts.game_data.skill_pending_storage_native import _match

SCHEMA='endfield.skill-center-inline-refresh-native-contract.v2'
AUDIT_SCHEMA='endfield.skill-center-inline-refresh-native-audit.v2'
CONTRACT_PATH=CONTRACTS_DIR/'skill_center_inline_refresh_native.json'
STATE='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateBase'
MACHINE='Beyond.Gameplay.AI.CharacterMainCtrlSystem+CenterStateMachine'
AI='Beyond.Gameplay.AI.CharacterAIComponent'
ENTITY='Beyond.Gameplay.Core.Entity'

def _rules():
    return dict(entryToFragmentsRequired=False,selectedNormalCfgProved=True,opaqueHelperResultsRequired=True,iteratorScheduleProved=True,machineReplacementEarlyReturn=True,perIterationMachineAiReload=True,secondTypePredicateCanNullState=True,aiWritePrecedesNullFailure=True,coldBytesCovered=True,exceptionCfgProved=False,dictionaryImplementationProved=False,inlineOriginalWritesAiAndEntity=True,
        inlineDoesNotCallBaseRefreshEntry=True,sameBaseReplacementCellAndSlots=True,
        aiBitmapBarrierPreservesStateAndAiCarriers=True,entityBitmapBarrierConsumesStateAfterFinalStore=True,sourceEntityFieldNamed=True,
        completeLoopCfgProved=True,captureWriterAttributed=False,lifetimeProved=False,
        blackboardIdentityProved=False,completeWriterCensusProved=False)

def _programs(c):
    spans={r['id']:r for r in c['spans']}; op=c['operands']; f={r['id']:r['offset']for r in c['fields']}
    _require(set(spans)=={'source','current','dispatch','aiStore','aiBarrier','entityStore','entityBarrier','baseDispatch','baseReplacement'},'inline-span-set','exact finite fragments',list(spans))
    h=bytes.fromhex;F=lambda k,w=1:('field',k,w);O=lambda k,w=4:('operand',k,w);R=lambda k,w=4:('relative',k,w)
    def check(key,parts):
        r=spans[key];_require(_match(bytes.fromhex(r['hex']),r['rva'],parts,f,op,op),'inline-fragment-'+key,'finite semantic byte grammar',r)
    check('source',[h('488b83'),F('entityAi',4),h('488946'),F('machineAi'),h('488d4e'),F('machineAi'),h('e8'),R('barrier'),h('48895e'),F('machineEntity'),h('488d4e'),F('machineEntity'),h('e8'),R('barrier')])
    check('current',[h('488b5c2450488b7e'),F('machineAi')])
    check('dispatch',[h('488b05'),R('typeInfoCell'),h('488b48'),O('dispatchOffset',1),h('4885c97423'),h('488b81'),O('functionOffset'),h('4885c07417'),h('4533c94c8bc7488bd3488b89'),O('contextOffset'),h('ffd0e9'),R('nextIteration')])
    _require(spans['dispatch']['rva']+len(bytes.fromhex(spans['dispatch']['hex']))==op['ordinary']==spans['aiStore']['rva'],'inline-dispatch-target','original reaches AI write',op['ordinary'])
    check('aiStore',[h('48897b'),F('ai')])
    # Closed bitmap loops contain no calls and no writes to RBX or RDI.
    # R14 bitmap carrier and valid bitmap memory are explicit entry premises.
    check('aiBarrier',[h('8b0d'),R('bitmapFlag'),h('85c974474c8d43'),F('ai'),h('49c1e80c4181e0ffff1f00418bc048c1e806498d14c64183e03f0f0d8af86e04000f1f00488b82f86e0400488bc84c0fabc1f0480fb18af86e040075e78b0d'),R('bitmapFlag')])
    check('entityStore',[h('4885ff0f84'),R('nullFailure'),h('488b47'),F('aiEntity'),h('488943'),F('entity')])
    check('entityBarrier',[h('85c90f84'),R('nextIteration'),h('4883c3'),F('entity'),h('48c1eb0c81e3ffff1f008bc348c1e806498d14c683e33f0f0d8af86e0400660f1f440000488b82f86e0400488bc8480fabd9f0480fb18af86e040075e7e9'),R('nextIteration')])
    # Entity barrier intentionally consumes RBX after the last state store;
    # RDI remains unchanged, and the next iteration reloads RBX.
    check('baseDispatch',[h('488b05'),R('typeInfoCell'),h('4c8bd14c8bda488b48'),O('dispatchOffset',1),h('4885c90f85'),R('baseReplacement')])
    check('baseReplacement',[h('488b81'),O('functionOffset'),h('4885c00f84'),R('baseOriginal'),h('488b89'),O('contextOffset'),h('4d8bc84d8bc3498bd2ffd0')])
    for left,right in [('aiStore','aiBarrier'),('aiBarrier','entityStore'),('entityStore','entityBarrier')]:
        _require(spans[left]['rva']+len(bytes.fromhex(spans[left]['hex']))==spans[right]['rva'],'inline-fragment-continuity',left,right)
    _flow_program(c)
    return _rules()

def _model():
    return dict(
        machineEntryArguments={'machine':'RCX -> RSI','entity':'RDX -> RBX','methodContext':'R8 -> RDI'},
        machineReplacement=['if replacement table and function present: opaque(context, machine, entity, methodContext)','return without original writes'],
        originalSetup=['null entity -> failure helper','read entity.charAI once; write machine.ai; opaque write barrier','write machine.entity = original entity; opaque write barrier','read machine collection field; null -> failure','opaque collection helper; null result -> failure','read result+0x10; store iterator collection; opaque stack barrier; null collection -> failure','iterator index=0, version=collection+0x2c, current=null'],
        iteration=['opaque MoveNext(iterator address, generic context); false -> normal return','read iterator current and independently reload machine.ai','null current or false first opaque type predicate -> failure helper','false second opaque type predicate -> state carrier null; true -> original current','if state replacement function exists: opaque(context,state,ai,null); next iteration','otherwise write state.ai = this iteration ai; run conditional bitmap loop','null ai -> failure after ai store; otherwise read ai.entity once and write state.entity','run conditional entity bitmap loop; next iteration'],
        normalUnreachableCleanup='cleanup landing bytes have no predecessor in selected ordinary CFG; exception routing unresolved',
        heapMutationBoundary='Opaque helpers and source write barriers may mutate heap; carrier preservation by Win64 ABI does not imply field or object lifetime stability.',
        dynamicRequired=['actual helper results and iterator currents','replacement effects and exceptions','object lifetime and capture writer attribution','heap changes across opaque calls'])

def _flow_program(c):
    """Finite instruction grammar; relative operands are data, edge topology is code."""
    flow=c['selectedFlow']; rows=flow['instructions']
    _require(flow['entry']==c['methods'][0]['identity'][3],'inline-flow-method-entry',c['methods'][0]['identity'][3],flow['entry'])
    grammar='48895c2408 4889742410 57 4156 4157 4883ec60 498bf8 488bda 488bf1 803d:4:00 75:1: 488d0d:4: e8:4: 488d0d:4: e8:4: 488d0d:4: e8:4: 488d0d:4: e8:4: 488d0d:4: e8:4: 488d0d:4: e8:4: c605:4:01 488b05:4: 488b4838 4885c9 74:1: 488b81c0c30000 4885c0 74:1: 4c8bcf 4c8bc3 488bd6 488b89c8c30000 ffd0 4c8d5c2460 498b5b20 498b7328 498be3 415f 415e 5f c3 0f57c0 33c0 0f11442440 4889442450 4885db 0f84:4: 488b8350010000 48894658 488d4e58 e8:4: 48895e60 488d4e60 e8:4: 488b5e28 4885db 0f84:4: 488b15:4: 488bcb e8:4: 4885c0 0f84:4: 488b5810 0f57c0 f30f7f442430 48895c2428 488d4c2428 e8:4: 4885db 0f84:4: 8b432c 89442434 4533ff 44897c2430 33c0 4889442438 0f10442428 0f11442440 f20f104c2438 f20f114c2450 4c897c2428 488d442440 4889442430 4c8d35:4: 0f1f00 488b15:4: 488d4c2440 e8:4: 84c0 0f84:4: 488b5c2450 488b7e58 4885db 0f84:4: 488b15:4: 488b0b e8:4: 84c0 0f84:4: 488b15:4: 488b0b e8:4: 84c0 490f44df 488b05:4: 488b4838 4885c9 74:1: 488b8130c10000 4885c0 74:1: 4533c9 4c8bc7 488bd3 488b8938c10000 ffd0 e9:4: 48897b40 8b0d:4: 85c9 74:1: 4c8d4340 49c1e80c 4181e0ffff1f00 418bc0 48c1e806 498d14c6 4183e03f 0f0d8af86e0400 0f1f00 488b82f86e0400 488bc8 4c0fabc1 f0480fb18af86e0400 75:1: 8b0d:4: 4885ff 0f84:4: 488b4750 48894348 85c9 0f84:4: 4883c348 48c1eb0c 81e3ffff1f00 8bc3 48c1e806 498d14c6 83e33f 0f0d8af86e0400 660f1f440000 488b82f86e0400 488bc8 480fabd9 f0480fb18af86e0400 75:1: e9:4: e9:4: 488b4c2428 4885c9 0f84:4: e8:4: cc e8:4: cc e8:4: cc e8:4: cc e8:4: 90 e8:4: e8:4: cc cc'.split()
    _require(len(rows)==len(grammar),'inline-flow-instruction-count',len(grammar),len(rows))
    cursor=flow['entry']; by_rva={r['rva']:i for i,r in enumerate(rows)}; actual_edges={}
    for i,(row,pattern) in enumerate(zip(rows,grammar)):
        raw=bytes.fromhex(row['hex'])
        _require(row['rva']==cursor,'inline-flow-contiguous',cursor,row['rva'])
        cursor+=len(raw)
        if ':' in pattern:
            left,width,right=pattern.split(':'); a=len(bytes.fromhex(left)); n=int(width)
            _require(len(raw)==a+n+len(bytes.fromhex(right)) and raw[:a]==bytes.fromhex(left) and raw[a+n:]==bytes.fromhex(right),'inline-flow-opcode-'+str(i),pattern,row)
            target=cursor+int.from_bytes(raw[a:a+n],'little',signed=True)
            _require(target==flow['references'][str(i)],'inline-flow-reference-'+str(i),flow['references'][str(i)],target)
            if i in {10: 24, 27: 44, 30: 44, 49: 166, 59: 168, 64: 170, 72: 172, 92: 160, 96: 175, 101: 175, 110: 120, 113: 120, 119: 88, 123: 139, 137: 133, 140: 174, 144: 88, 158: 154, 159: 88, 160: 36, 163: 36}:
                _require(target in by_rva,'inline-flow-internal-edge',target,row)
                actual_edges[i]=by_rva[target]
        else:
            _require(raw.hex()==pattern,'inline-flow-opcode-'+str(i),pattern,row)
    _require(cursor==flow['end'],'inline-flow-end',flow['end'],cursor)
    _require(actual_edges=={10: 24, 27: 44, 30: 44, 49: 166, 59: 168, 64: 170, 72: 172, 92: 160, 96: 175, 101: 175, 110: 120, 113: 120, 119: 88, 123: 139, 137: 133, 140: 174, 144: 88, 158: 154, 159: 88, 160: 36, 163: 36},'inline-flow-edge-topology',{10: 24, 27: 44, 30: 44, 49: 166, 59: 168, 64: 170, 72: 172, 92: 160, 96: 175, 101: 175, 110: 120, 113: 120, 119: 88, 123: 139, 137: 133, 140: 174, 144: 88, 158: 154, 159: 88, 160: 36, 163: 36},actual_edges)
    # Existing local write grammars must be slices of this complete schedule.
    body=b''.join(bytes.fromhex(r['hex'])for r in rows)
    anchors={'source': 50, 'current': 93, 'dispatch': 107, 'aiStore': 120, 'aiBarrier': 121, 'entityStore': 139, 'entityBarrier': 143}
    for span in c['spans']:
        if not span['id'].startswith('base'):
            _require(span['rva']==rows[anchors[span['id']]]['rva'],'inline-flow-carrier-join',span['id'],span['rva'])
            at=span['rva']-flow['entry']; raw=bytes.fromhex(span['hex'])
            _require(body[at:at+len(raw)]==raw,'inline-flow-fragment-join',span['id'],at)
    return body

def _validate(image,c):
    cx=NativeReferenceContext(image);_validate_fields(image,c['fields'])
    expected={'ai':(STATE,'m_aiCom',AI),'entity':(STATE,'m_entity',ENTITY),'aiEntity':('Beyond.Gameplay.Core.BaseComponent','<entity>k__BackingField',ENTITY),'entityAi':(ENTITY,'<charAICom>k__BackingField',AI),'machineAi':(MACHINE,'m_aiCom',AI),'machineEntity':(MACHINE,'m_entity',ENTITY)}
    _require({r['id']for r in c['fields']}==set(expected),'inline-field-set',list(expected),c['fields'])
    for r in c['fields']:_require((r['type'],r['name'],r['valueType'])==expected[r['id']],'inline-nominal-field',expected[r['id']],r)
    validate_reference_ancestor_chain(cx,AI,['Beyond.Gameplay.AI.AIComponent','Beyond.Gameplay.Core.TickComponent','Beyond.Gameplay.Core.BaseComponent'],'Beyond.Gameplay.Core.BaseComponent')
    _require(len(c['methods'])==2,'inline-method-count',2,len(c['methods']))
    resolved_entries=[]
    for row,owner in zip(c['methods'],[MACHINE,STATE]):
        _require(row['identity'][1:3]==[owner,'RefreshData'],'inline-method-role',owner,row)
        m=image.metadata.methods[image.validate_method_row(row['identity'],label='centerInlineRefresh')]
        resolved_entries.append(image.method_pointer_va(m)-image.pe.image_base)
        params=[dict(name=image.metadata.string(p.name_index),type=cx.type_name(p.type_index))for p in image.metadata.parameters_for(m)]
        _require(not m.flags&16 and cx.type_name(m.return_type)=='void'and params==row['parameters'],'inline-method-signature',row,params)
    _require(c['selectedFlow']['entry']==resolved_entries[0],'inline-flow-resolved-method-entry',resolved_entries[0],c['selectedFlow']['entry'])
    body=_flow_program(c)
    image.check_windows([c['flowWindow']],label='centerInlineRefreshFlow')
    w=c['flowWindow']; flow=c['selectedFlow']
    _require((w['startRva'],w['endRva'])==(flow['entry'],flow['end']) and image.pe.bytes_at_va(image.pe.image_base+flow['entry'],len(body))==body,'inline-flow-native-body','complete selected schedule',w)
    family=image.unwind_index.family(resolved_entries[0])
    _require(any(r['runtimeTriple'][0]<=flow['entry'] and flow['end']<=r['runtimeTriple'][1] for r in family['ranges']),'inline-flow-owned','selected body in machine unwind family',family)
    image.check_windows(c['codeWindows'],label='centerInlineRefresh')
    _require(len(c['codeWindows'])==len(c['spans']),'inline-window-count','one per span',c['codeWindows'])
    for r,w in zip(c['spans'],c['codeWindows']):
        raw=bytes.fromhex(r['hex']);_require((w['startRva'],w['endRva'])==(r['rva'],r['rva']+len(raw))and image.pe.bytes_at_va(image.pe.image_base+r['rva'],len(raw))==raw,'inline-span-native-bytes',r['id'],w)
    for r in c['spans']:
        owner=c['methods'][1 if r['id'].startswith('base')else 0]['identity'][3]
        _require(any(a['runtimeTriple'][0]<=r['rva']and r['rva']+len(bytes.fromhex(r['hex']))<=a['runtimeTriple'][1]for a in image.unwind_index.family(owner)['ranges']),'inline-span-owned',r['id'],owner)
    return _programs(c)

def load_skill_center_inline_refresh(*,gameassembly,metadata,contract_path=CONTRACT_PATH):
    path=Path(contract_path);audit=dict(schema=AUDIT_SCHEMA,status='validation_failed',rules={},rows=[],failures=[])
    try:
        c,digest=read_reviewed_contract(path,schema=SCHEMA,status='reviewed',label='centerInlineRefresh');pins=c['nativeInputs']
        gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata);audit.update(status=gate.status,detail=gate.detail)
        if gate.status!='validated':return audit
        rules=_validate(open_native_image(gate.gameassembly,gate.metadata),c)
        after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
        _require(after.status=='validated'and hashlib.sha256(path.read_bytes()).hexdigest().upper()==digest,'inline-input-bookends','unchanged declarations and native inputs',after.status)
        audit.update(status='validated-conditional-inline-refresh',detail='',nativeInputs=pins,evidenceBoundary=c['evidenceBoundary'],rules=rules,model=_model(),rows=[dict(id='centerMachineInlineRefresh',evidence='conditional',rules=rules)])
    except(OSError,ValueError,KeyError,IndexError,TypeError,RuntimeError,struct.error,OverflowError)as e:
        audit.update(status='validation_failed',detail=str(e)[:1600],rules={},rows=[],failures=[dict(check=str(e).split(':',1)[0],detail=str(e)[:1600])])
    return audit

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('gameassembly','metadata'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--output',type=Path,default=REPO_ROOT/'reports/game_data/skill_center_inline_refresh_native.json');a=p.parse_args(argv)
    _require(a.output.resolve().is_relative_to((REPO_ROOT/'reports').resolve()),'inline-output-root','reports/',a.output)
    r=load_skill_center_inline_refresh(gameassembly=a.gameassembly,metadata=a.metadata)
    if r['status']=='validated-conditional-inline-refresh':a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(r));return 0 if r['status']=='validated-conditional-inline-refresh'else 2
if __name__=='__main__':raise SystemExit(main())

