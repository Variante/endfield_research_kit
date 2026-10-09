"""Prove conditional aligned temporal vector loops and rebased copy tails.

Complete original guards/counters establish the natural-number induction.
Non-temporal/backward alternatives, runtime providers and general resize
preservation remain separate; no loop execution is observed here.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
from scripts.game_data.il2cpp.aligned_copy_loops import prove_aligned_loop_payload,prove_rebased_vector_tail
from scripts.game_data import buff_effect_line_center_copy_small_native as small_owner

SCHEMA='endfield.buff-effect-line-center-copy-loops-native-contract.v1'
LABEL='buffEffectLineCenterCopyLoops'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_copy_loops_native.json'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _qword_immediate(g,text,prefix,operand):
    row=g.take(text);raw=bytes.fromhex(row['bytes'])
    if len(raw)!=7 or raw[:3]!=prefix or int.from_bytes(raw[3:],'little',signed=True)!=operand:
        g.fail('qword-immediate',{'prefix':prefix.hex(),'signedOperand':operand},row)
    return row


def _above_equal(g):
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    if len(raw)==2 and raw[0]==0x73:relative=raw[1:]
    elif len(raw)==6 and raw[:2]==b'\x0f\x83':relative=raw[2:]
    else:g.fail('unsigned-loop-predicate','JAE',row)
    target=at+len(raw)+int.from_bytes(relative,'little',signed=True)
    if row['text'] not in (f'jae 0x{target:x}',f'jcc 0x{target:x}'):g.fail('unsigned-loop-decoding',hex(target),row)
    return {**row,'target':target,'predicate':'jae'}


def _alignment(rows,*,width,chunk,non_temporal_threshold=None):
    g=ProgramGrammar(rows,label=LABEL+'.alignment')
    origin=g.take('mov r9, rcx');mask=g.take(f'and r9, 0x{width-1:x}');subtract=g.take(f'sub r9, 0x{width:x}')
    if (bytes.fromhex(origin['bytes'])!=b'\x4c\x8b\xc9'
            or bytes.fromhex(mask['bytes'])!=bytes((0x49,0x83,0xe1,width-1))
            or bytes.fromhex(subtract['bytes'])!=bytes((0x49,0x83,0xe9,width))):
        g.fail('alignment-width','qword destination residue minus complete vector width',{'origin':origin,'mask':mask,'subtract':subtract})
    for text in ('sub rcx, r9','sub rdx, r9','add r8, r9'):
        row=g.take(text)
        if row.get('integerOperation',{}).get('bits')!=64:g.fail('alignment-arithmetic-width',64,row)
    _qword_immediate(g,f'cmp r8, 0x{chunk:x}',b'\x49\x81\xf8',chunk);tail=g.branch('jbe')
    non_temporal=None
    if non_temporal_threshold is not None:
        _qword_immediate(g,f'cmp r8, 0x{non_temporal_threshold:x}',b'\x49\x81\xf8',non_temporal_threshold)
        non_temporal=g.branch('ja')
    g.finish()
    return {'completeAlignmentChecked':True,'tailEntryEdge':tail,'nonTemporalEntryEdge':non_temporal,
        'alignmentAdvanceEquation':f'a={width}-(originalDestination & {width-1}), 1<=a<={width}',
        'pointerAndCountEquations':'source += a; destination += a; length -= a; original destination in RAX remains unchanged',
        'alreadyAlignedDestinationAdvancesFullWidth':True,
        'conditionalDestinationAlignmentProved':True,'arithmeticBits':64}


def _padding(rows):
    g=ProgramGrammar(rows,label=LABEL+'.padding');row=g.take('nop');g.finish()
    if row.get('paddingOperation')!={'readsMemory':False,'writesFlags':False}:g.fail('padding-operation','no memory read or flags write',row)
    return {'completeFallthroughPaddingChecked':True}


def _loop(rows,*,width,chunk):
    g=ProgramGrammar(rows,label=LABEL+'.loop');moves=[]
    while g.cursor<len(rows) and rows[g.cursor].get('memoryOperation') is not None:moves.append(g.row()['memoryOperation'])
    block=prove_aligned_loop_payload(moves,width=width,chunk=chunk,label=LABEL+'.loopBytes')
    _qword_immediate(g,f'add rcx, 0x{chunk:x}',b'\x48\x81\xc1',chunk)
    _qword_immediate(g,f'add rdx, 0x{chunk:x}',b'\x48\x81\xc2',chunk)
    _qword_immediate(g,f'sub r8, 0x{chunk:x}',b'\x49\x81\xe8',chunk)
    _qword_immediate(g,f'cmp r8, 0x{chunk:x}',b'\x49\x81\xf8',chunk)
    again=_above_equal(g);g.finish()
    if again['target']!=int(rows[0]['va'],16):g.fail('complete-loop-back-edge',rows[0]['va'],again)
    return {'completeLoopBodyAndGuardChecked':True,'backEdge':again,'block':block,
        'counterBits':64,'loopGuard':'repeat while unsigned remaining >= complete chunk',
        'induction':'At loop j, pointers equal original bases + alignmentAdvance + j*chunk; remaining = originalLength - alignmentAdvance - j*chunk. The copied prefix [alignmentAdvance, alignmentAdvance+j*chunk) retains initial source bytes. A guard admitting at least one full chunk keeps accesses in bounds; one checked block preserves the byte invariant and cached head/last, then advances both pointers and strictly reduces remaining by chunk without underflow. Alignment is preserved by a whole-vector chunk. The unsigned post-update guard either repeats or exits below one chunk.',
        'conditionalArbitraryLoopCountProved':True,'runtimeLoopCountObserved':False}


def _tails(rows,*,width,chunk,table,image_base):
    tail=small_owner._vector_tail(rows,width=width,table=table)
    if chunk%width or len(table['entries'])!=chunk//width+1:_fail('tail-table-bound',chunk//width+1,len(table['entries']))
    proofs=[]
    for remaining in range(chunk+1):
        rounded=(remaining+width-1)&-width;index=rounded//width;target=image_base+table['entries'][index]
        if target not in tail['payloadInstructionIndices']:_fail('rebased-tail-target-boundary',sorted(tail['payloadInstructionIndices']),target)
        payload=small_owner._payload(tail['payloadRows'][tail['payloadInstructionIndices'][target]:],label='rebasedTail',cleanup_allowed=width==32)
        proof=prove_rebased_vector_tail(payload['moves'],width=width,chunk=chunk,remaining=remaining,label=LABEL+'.tailBytes')
        proofs.append({'remaining':remaining,'index':index,'loads':proof['loads'],'stores':proof['stores']})
    return {'everyRebasedRemainderProved':True,'remainingMinimum':0,'remainingMaximum':chunk,
        'finiteRemaindersProved':len(proofs),'proofs':proofs,'zeroRemainderOriginalHeadWriteProved':True,
        'coverage':'cached head covers skipped alignment prefix; checked loop chunks cover the middle; affine tail preserves every remaining initial-source byte, including original-endpoint saved last, before the complete original return'}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (contract.get('scope')!='conditional-large-aligned-temporal-vector-byte-copy'
            or set(contract.get('blocks',{}))!={'highAlignment','highPadding','highLoop','lowAlignment','lowPadding','lowLoop'}
            or set(contract.get('selectionConstants',{}))!={'highNonTemporalThreshold'}):
        _fail('contract-shape','two complete aligned temporal loop paths and high non-temporal alternative',contract.get('scope'))
    return contract


def _validate_image(image,contract):
    parent=small_owner._contract();base=image.pe.image_base
    if parent['nativeInputs']!=contract['nativeInputs']:_fail('same-parent-build',parent['nativeInputs'],contract['nativeInputs'])
    prior=small_owner._validate_image(image,parent)
    bulk=small_owner.rep_owner.argument_owner._contract()['programs']['bulk']
    if contract['bulkEntryRva']!=bulk['entryRva']:_fail('actual-bulk-entry',bulk['entryRva'],contract['bulkEntryRva'])
    def decode(window):
        if not any(w['startRva']<=window['startRva']<window['endRva']<=w['endRva'] for w in bulk['windows']):
            _fail('owned-loop-window',bulk['windows'],window)
        return decode_memory_move_instructions(image.mapper,image.window_bytes(window),base+window['startRva'])
    rows={role:decode(window) for role,window in contract['blocks'].items()};paths={}
    for role in ('high','low'):
        width=parent['vectors'][role]['widthBytes'];chunk=parent['vectors'][role]['lengthMaximum']
        threshold=contract['selectionConstants']['highNonTemporalThreshold'] if role=='high' else None
        alignment=_alignment(rows[role+'Alignment'],width=width,chunk=chunk,non_temporal_threshold=threshold)
        padding=_padding(rows[role+'Padding']);loop=_loop(rows[role+'Loop'],width=width,chunk=chunk)
        tail=_tails(decode(parent['blocks'][role+'Tail']),width=width,chunk=chunk,table=parent['tables'][role],image_base=base)
        blocks=contract['blocks']
        if (blocks[role+'Alignment']['startRva']!=parent['blocks'][role+'Prefix']['endRva']
                or blocks[role+'Alignment']['endRva']!=blocks[role+'Padding']['startRva']
                or blocks[role+'Padding']['endRva']!=blocks[role+'Loop']['startRva']
                or blocks[role+'Loop']['endRva']!=parent['blocks'][role+'Tail']['startRva']
                or alignment['tailEntryEdge']['target']!=base+parent['blocks'][role+'Tail']['startRva']):
            _fail('complete-alignment-loop-tail-joins','actual prefix fallthrough, checked padding, loop and shared tail',role)
        if role=='high':
            if threshold<chunk or alignment['nonTemporalEntryEdge']['target']!=base+contract['highNonTemporalEntryRva']:
                _fail('unselected-non-temporal-alternative','checked unsigned threshold edge',alignment)
        paths[role]={'widthBytes':width,'chunkBytes':chunk,'alignment':alignment,'padding':padding,'loop':loop,'tail':tail,
            'conditionalLargeTemporalByteCopyProved':True,'forwardSafeOverlapProved':True,
            'entrySelection':'parent vector path selected; original length above parent bounded vector limit; high path additionally has remainingAfterAlignment <= reviewed non-temporal threshold',
            'runtimeSelectionObserved':False}
    return {'smallAndParentProofRevalidated':True,'paths':paths,
        'conditionalLargeAlignedTemporalByteCopyProved':True,
        'conditionalArbitraryTemporalLoopCountProved':True,'conditionalOldPointPreservationViaTemporalLoopsProved':True,
        'conditionalOldPointPreservationSelection':'all parent compatible same-element and normal-return selections; class stride equals independently checked Vector3 width; temporal path selected; valid stable non-wrapping arrays/code/tables and supported vector state; original source bytes retained except own proved overlap-safe writes; caller frame and optional bitset disjoint from payloads; successful optional retry, checked new-array reference and append',
        'returnDestinationAndRequiredNonvolatilePreservationProved':True,
        'nonTemporalCopyImplementationProved':False,'backwardCopyImplementationProved':False,
        'runtimeStrideProved':False,'runtimeModeOrCPUSelectionProved':False,
        'bulkCopyImplementationProved':False,'existingValuesPreservedAcrossResizeProved':False,
        'runtimeExecutionObserved':False}


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
    if after.status!='validated' or not matches():return {'status':'mismatched','detail':'Selected native inputs changed during loop proof','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
