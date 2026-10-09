"""Prove complete selected backward-overlap copying with pipeline completion.

The actual common dispatch edge, full original program, cached-vector values,
descending chunk induction and every bounded tail are checked. Live stride,
reference/allocation conditions and observed effects remain separate.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.backward_copy_instructions import decode_backward_copy_instructions
from scripts.game_data.il2cpp.backward_copy_programs import prove_backward_cache_alignment,prove_pipelined_backward_chunk,prove_backward_tail
from scripts.game_data import buff_effect_line_center_copy_rep_native as rep_owner

SCHEMA='endfield.buff-effect-line-center-copy-backward-native-contract.v1'
LABEL='buffEffectLineCenterCopyBackward'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_copy_backward_native.json'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _program(rows):
    g=ProgramGrammar(rows,label=LABEL+'.program')
    def memory(text):
        row=g.take(text)
        if row.get('memoryOperation') is None:g.fail('exact-memory-transfer','structured original memory operand',row)
        return row['memoryOperation']
    def exact(text,raw_hex):
        row=g.take(text)
        if bytes.fromhex(row['bytes'])!=bytes.fromhex(raw_hex):g.fail('exact-qword-or-control-encoding',raw_hex,row)
        return row
    def vector(text):
        row=g.take(text)
        if row.get('vectorRegisterOperation') is None:g.fail('exact-vector-transfer','structured original register transfer',row)
        return row['vectorRegisterOperation']
    def nop():
        row=g.take('nop')
        if row.get('paddingOperation')!={'readsMemory':False,'writesFlags':False}:g.fail('padding','no memory/flag change',row)

    head=memory('movups xmm2, [rdx]')
    for text,destination,source in (('sub rdx, rcx','rdx','rcx'),('add rcx, r8','rcx','r8')):
        row=g.take(text);op=row.get('integerOperation',{})
        if (op.get('bits'),op.get('destination'),op.get('source'))!=(64,destination,source):g.fail('source-delta-endpoint-width','qword arithmetic',row)
    last=memory('movups xmm0, [rcx+rdx*1-0x10]')
    exact('sub rcx, 0x10','4883E910');exact('sub r8, 0x10','4983E810')
    row=g.take('test cl, 0xf');test=row.get('byteTestOperation',{})
    if (test.get('backingRegister'),test.get('bitOffset'),test.get('bits'),test.get('mask'),test.get('writesRegister'),test.get('writesMemory'))!=('rcx',0,8,15,False,False):
        g.fail('alignment-low-byte-predicate','unchanged CL & 15',row)
    g.branch('je','aligned')
    exact('mov r9, rcx','4C8BC9');exact('and rcx, -0x10','4883E1F0')
    saved_last=vector('movups xmm1, xmm0');aligned_load=memory('movups xmm0, [rcx+rdx*1]')
    unaligned_store=memory('movups [r9], xmm1')
    exact('mov r8, rcx','4C8BC1');row=g.take('sub r8, rax')
    if row.get('integerOperation',{}).get('bits')!=64:g.fail('prefix-distance-width',64,row)
    g.mark('aligned');exact('mov r9, r8','4D8BC8');exact('shr r9, 0x7','49C1E907');g.branch('je','small-tail')
    initial_store=memory('movaps [rcx], xmm0');g.branch('jmp','chunk-body');nop()
    g.mark('repeat-header')
    repeat_stores=[memory('movaps [rcx+0x10], xmm0'),memory('movaps [rcx], xmm1')]
    g.mark('chunk-body');steps=[memory('movups xmm0, [rcx+rdx*1-0x10]'),memory('movups xmm1, [rcx+rdx*1-0x20]')]
    exact('sub rcx, 0x80','4881E980000000');steps.append({'kind':'pointer-retreat','bytes':128})
    for text in ('movaps [rcx+0x70], xmm0','movaps [rcx+0x60], xmm1',
            'movups xmm0, [rcx+rdx*1+0x50]','movups xmm1, [rcx+rdx*1+0x40]'):
        steps.append(memory(text))
    exact('dec r9','49FFC9')
    for text in ('movaps [rcx+0x50], xmm0','movaps [rcx+0x40], xmm1',
            'movups xmm0, [rcx+rdx*1+0x30]','movups xmm1, [rcx+rdx*1+0x20]',
            'movaps [rcx+0x30], xmm0','movaps [rcx+0x20], xmm1',
            'movups xmm0, [rcx+rdx*1+0x10]','movups xmm1, [rcx+rdx*1]'):
        steps.append(memory(text))
    g.branch('jne','repeat-header')
    exit_store=memory('movaps [rcx+0x10], xmm0');exact('and r8, 0x7f','4983E07F')
    exit_copy=vector('movaps xmm0, xmm1');g.mark('small-tail')
    exact('mov r9, r8','4D8BC8');exact('shr r9, 0x4','49C1E904');g.branch('je','final-tail');nop()
    g.mark('small-loop');tail_steps=[memory('movups [rcx], xmm0')]
    exact('sub rcx, 0x10','4883E910');tail_steps.append({'kind':'pointer-retreat','bytes':16})
    tail_steps.append(memory('movups xmm0, [rcx+rdx*1]'));exact('dec r9','49FFC9');g.branch('jne','small-loop')
    g.mark('final-tail');exact('and r8, 0xf','4983E00F');g.branch('je','final-current')
    head_store=memory('movups [rax], xmm2');g.mark('final-current');final_store=memory('movups [rcx], xmm0');exact('ret','C3');g.finish()

    alignment=prove_backward_cache_alignment(head,last,saved_last,aligned_load,unaligned_store,initial_store,label=LABEL+'.alignmentValues')
    chunk=prove_pipelined_backward_chunk(steps,repeat_stores,exit_store,exit_copy,label=LABEL+'.chunkValues')
    tails=[prove_backward_tail(tail_steps,head_store,final_store,remaining=r,label=LABEL+'.tailValues') for r in range(128)]
    return {'completeOriginalBackwardProgramChecked':True,'alignment':alignment,'chunk':chunk,
        'tail':{'allReachableRemaindersProved':True,'finiteRemaindersProved':len(tails),'proofs':tails},
        'counterAndPointerInductionProved':True,
        'induction':'Let L=N-16-a, a=(D+N-16)&15 and initial aligned P=D+L. For k=L>>7>0 the initial cached-current store completes [P,D+N). At each chunk body P is aligned and at least 128 above D; source-minus-destination remains fixed, every source byte in [P-128,P) is loaded in descending order, upper six vectors are stored, and the lowest two are cached. A repeat header stores those two at the new P and P+16, completing the suffix before the next body. The original qword counter decrements once and JNE repeats exactly k bodies without underflow. On the last body the exit writes the upper pending vector and forwards the lowest into vector0; P=D+(L&127), its vector is cached, and [P+16,D+N) is complete. k=0 directly establishes that same tail invariant from alignment caches. The qword tail counter (L&127)>>4 gives at most seven descending vector iterations; every later source end is at/below preceding destination starts under D>S. At final h=L&15, the cached original head is stored iff h!=0, then the cached current vector at D+h is stored; all bytes are covered with agreeing overlap values.',
        'returnsOriginalDestinationWithoutChangingParentNonvolatileRegistersProved':True,'runtimeExecutionObserved':False}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if contract.get('scope')!='conditional-complete-backward-overlap-copy' or set(contract.get('blocks',{}))!={'backward'}:
        _fail('contract-shape','one complete owned backward program',contract.get('scope'))
    return contract


def _validate_image(image,contract):
    parent=rep_owner._contract();base=image.pe.image_base
    if parent['nativeInputs']!=contract['nativeInputs']:_fail('same-parent-build',parent['nativeInputs'],contract['nativeInputs'])
    rep=rep_owner._validate_image(image,parent)
    bulk=rep_owner.argument_owner._contract()['programs']['bulk'];window=contract['blocks']['backward']
    if (bulk['entryRva']!=contract['bulkEntryRva'] or not any(w['startRva']<=window['startRva']<window['endRva']<=w['endRva'] for w in bulk['windows'])):
        _fail('owned-called-bulk-program',bulk,window)
    if rep['common']['backwardOverlapEdge']['target']!=base+window['startRva']:
        _fail('actual-backward-entry-edge',base+window['startRva'],rep['common']['backwardOverlapEdge'])
    program=_program(decode_backward_copy_instructions(image.mapper,image.window_bytes(window),base+window['startRva']))
    return {'sameImageArgumentAndDispatchProofRevalidated':True,'actualBackwardOverlapEntryJoinProved':True,
        'program':program,'conditionalCompleteBackwardByteCopyProved':True,'conditionalArbitraryBackwardLoopCountProved':True,
        'backwardCopySelection':'actual common branch with N>32 and source<destination<source+N, non-wrapping endpoints; supported legacy vector state, valid stable compatible ordinary memory, no concurrent overwrite, source-minus-destination modulo qword arithmetic, sixteen-byte aligned current destination and the parent same-element/normal-return/frame/bitset conditions',
        'runtimeOverlapSelectionProved':False,'runtimeStrideProved':False,'allocationFreshnessProved':False,
        'sourceTemporaryNonaliasingLifetimeProved':False,'bulkCopyImplementationProved':False,
        'existingValuesPreservedAcrossResizeProved':False,'runtimeExecutionObserved':False}


def validate_current_native_contract(*,gameassembly:Path|None=None,metadata:Path|None=None):
    contract=_contract();pins=contract['nativeInputs']
    gate=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gameassembly,metadata=metadata)
    if gate.status!='validated':return {'status':gate.status,'detail':gate.detail,'nativeInputs':pins}
    unity=Path(gate.gameassembly).parent/'UnityPlayer.dll'
    def matches():
        if not unity.is_file():return False
        with unity.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest().upper()==pins['UnityPlayer.dll']
    if not matches():return {'status':'mismatched','detail':'Selected UnityPlayer missing or different','nativeInputs':pins}
    result=_validate_image(open_native_image(gate.gameassembly,gate.metadata),contract)
    after=check_installed_native_inputs(pins['GameAssembly.dll'],pins['global-metadata.dat'],gameassembly=gate.gameassembly,metadata=gate.metadata)
    if after.status!='validated' or not matches():return {'status':'mismatched','detail':'Selected native inputs changed during backward copy proof','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
