"""Authenticate non-temporal store coverage and exact following-store fence.

Return-time visibility, subsequent read consumption and general resize
preservation remain explicit joins. No current execution is observed.
"""
from __future__ import annotations
import copy
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.non_temporal_copy import project_loop_store_values,prove_tail_store_values,prove_store_fence
from scripts.game_data import buff_effect_line_center_copy_loops_native as loop_owner

SCHEMA='endfield.buff-effect-line-center-copy-non-temporal-native-contract.v1'
LABEL='buffEffectLineCenterCopyNonTemporal'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_copy_non_temporal_native.json'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _payload(rows):
    g=ProgramGrammar(rows,label=LABEL+'.tailPayload');moves=[]
    while g.cursor<len(rows) and rows[g.cursor].get('memoryOperation') is not None:moves.append(g.row()['memoryOperation'])
    fence=g.take('sfence');proof=prove_store_fence(bytes.fromhex(fence['bytes']),label=LABEL+'.fence')
    cleanup=g.take('vzeroupper')
    state=cleanup.get('vectorStateOperation',{})
    if (bytes.fromhex(cleanup['bytes'])!=b'\xc5\xf8\x77' or state.get('preservesLow128Bits') is not True
            or state.get('zerosBits128Through255') is not True or state.get('writesMemory') is not False
            or state.get('writesFlags') is not False or state.get('registerNumbers')!=list(range(16))):
        g.fail('cleanup-after-writes','complete selected VZEROUPPER',cleanup)
    ret=g.take('ret');g.finish()
    if bytes.fromhex(ret['bytes'])!=b'\xc3':g.fail('plain-complete-return','C3',ret)
    return {'moves':moves,'fence':proof,'completeOriginalFenceCleanupReturnProved':True}


def _loop(rows,*,width,chunk):
    normalized=copy.deepcopy(rows);ops=[]
    for row in normalized:
        if row.get('memoryOperation') is None:break
        ops.append(row['memoryOperation'])
    projected,values=project_loop_store_values(ops,width=width,chunk=chunk,label=LABEL+'.loopValues')
    for row,op in zip(normalized,projected):row['memoryOperation']=op
    induction=loop_owner._loop(normalized,width=width,chunk=chunk)
    return {'completeOriginalLoopAndCounterGuardProved':True,'storeValues':values,
        'counterInduction':induction,'conditionalArbitraryLoopStoreCoverageProved':True,
        'copyReturnVisibilityProved':False}


def _tails(rows,*,width,chunk,table,image_base):
    # This tail has a different complete payload grammar: a store fence is
    # mandatory. Preserve its original contiguous inventory and reuse only
    # the existing independently checked table-load operand proof.
    g=ProgramGrammar(rows,label=LABEL+'.tailHeader')
    lea=g.take(f'lea r9, [r8+0x{width-1:x}]')
    if lea.get('addressOperation',{}).get('destinationBits')!=64:g.fail('rounding-width',64,lea)
    mask=g.take(f'and r9, -0x{width:x}');raw=bytes.fromhex(mask['bytes'])
    if len(raw)!=4 or raw[:3]!=b'\x49\x83\xe1' or int.from_bytes(raw[3:],'little',signed=True)!=-width:
        g.fail('rounding-mask','qword AND with signed negative width',mask)
    transfer=g.take('mov r11, r9');shift=g.take(f'shr r11, 0x{width.bit_length()-1:x}')
    if bytes.fromhex(transfer['bytes'])!=b'\x4d\x8b\xd9' or bytes.fromhex(shift['bytes'])!=bytes((0x49,0xc1,0xeb,width.bit_length()-1)):
        g.fail('rounding-index-width','qword transfer and logical right shift',{'transfer':transfer,'shift':shift})
    loop_owner.small_owner._table_load(g,destination='r11',index='r11',table=table)
    addition=g.take('add r11, r10')
    if addition.get('integerOperation',{}).get('bits')!=64:g.fail('table-target-width',64,addition)
    g.take('jmp r11');g.finish(prefix=True)
    payload_rows=rows[g.cursor:];_payload(payload_rows)
    tail={'payloadRows':payload_rows,'payloadInstructionIndices':{int(row['va'],16):i for i,row in enumerate(payload_rows)}}
    if chunk%width or len(table['entries'])!=chunk//width+1:_fail('tail-table-bound',chunk//width+1,len(table['entries']))
    proofs=[]
    # The checked loop always executes once and exits with remaining < chunk.
    for remaining in range(chunk):
        rounded=(remaining+width-1)&-width;index=rounded//width;target=image_base+table['entries'][index]
        if target not in tail['payloadInstructionIndices']:_fail('actual-tail-target',sorted(tail['payloadInstructionIndices']),target)
        payload=_payload(tail['payloadRows'][tail['payloadInstructionIndices'][target]:])
        values=prove_tail_store_values(payload['moves'],width=width,chunk=chunk,remaining=remaining,label=LABEL+'.tailValues')
        proofs.append({'remaining':remaining,'index':index,'nonTemporalStores':values['alignedNonTemporalStores'],
            'savedTemporalStores':values['savedTemporalStores'],'fence':payload['fence']})
    return {'allReachableRemainderStoreValuesProved':True,'finiteRemaindersProved':len(proofs),
        'remainingMinimum':0,'remainingMaximum':chunk-1,'proofs':proofs,
        'everyReachableTailHasFenceThenCleanupThenPlainReturnProved':True,
        'zeroRemainderStillStoresOriginalHeadProved':True}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if contract.get('scope')!='conditional-non-temporal-store-values-and-following-store-order' or set(contract.get('blocks',{}))!={'loop','tail','fence'}:
        _fail('contract-shape','complete non-temporal loop, tail and selected fence',contract.get('scope'))
    return contract


def _validate_image(image,contract):
    parent=loop_owner._contract();base=image.pe.image_base
    if parent['nativeInputs']!=contract['nativeInputs']:_fail('same-parent-build',parent['nativeInputs'],contract['nativeInputs'])
    prior=loop_owner._validate_image(image,parent)
    bulk=loop_owner.small_owner.rep_owner.argument_owner._contract()['programs']['bulk']
    if contract['bulkEntryRva']!=bulk['entryRva']:_fail('actual-bulk-entry',bulk['entryRva'],contract['bulkEntryRva'])
    blocks=contract['blocks']
    for window in blocks.values():
        if not any(w['startRva']<=window['startRva']<window['endRva']<=w['endRva'] for w in bulk['windows']):
            _fail('owned-program-window',bulk['windows'],window)
    if (blocks['loop']['startRva']!=parent['highNonTemporalEntryRva']
            or blocks['loop']['endRva']!=blocks['tail']['startRva']
            or not blocks['tail']['startRva']<blocks['fence']['startRva']<blocks['fence']['endRva']<blocks['tail']['endRva']
            or prior['paths']['high']['alignment']['nonTemporalEntryEdge']['target']!=base+blocks['loop']['startRva']):
        _fail('complete-non-temporal-entry-and-tail-joins','actual parent unsigned edge, loop fallthrough and owned fence',blocks)
    width=prior['paths']['high']['widthBytes'];chunk=prior['paths']['high']['chunkBytes']
    if parent['selectionConstants']['highNonTemporalThreshold']<chunk:_fail('first-loop-count-guard','threshold >= chunk',parent['selectionConstants'])
    loop_rows=decode_memory_move_instructions(image.mapper,image.window_bytes(blocks['loop']),base+blocks['loop']['startRva'])
    loop=_loop(loop_rows,width=width,chunk=chunk)
    raw=image.window_bytes(blocks['tail']);start=blocks['fence']['startRva']-blocks['tail']['startRva'];end=blocks['fence']['endRva']-blocks['tail']['startRva']
    fence=prove_store_fence(raw[start:end],label=LABEL+'.ownedFence')
    tail_rows=decode_memory_move_instructions(image.mapper,raw[:start],base+blocks['tail']['startRva'])
    tail_rows.append({'va':hex(base+blocks['fence']['startRva']),'bytes':raw[start:end].hex(' '),'text':'sfence','storeFenceOperation':fence})
    tail_rows+=decode_memory_move_instructions(image.mapper,raw[end:],base+blocks['fence']['endRva'])
    table=contract['table'];image.check_windows([table],label=LABEL,gate='non-temporal-table')
    table_raw=image.window_bytes(table)
    if len(table_raw)%4 or [int.from_bytes(table_raw[i:i+4],'little') for i in range(0,len(table_raw),4)]!=table['entries']:
        _fail('raw-table-entries',table['entries'],table_raw.hex())
    if any(base+rva>=1<<64 for rva in table['entries']):_fail('table-target-no-wrap','valid loaded image',table['entries'])
    tails=_tails(tail_rows,width=width,chunk=chunk,table=table,image_base=base)
    return {'temporalAndParentProofRevalidated':True,'loop':loop,'tails':tails,'fence':fence,
        'conditionalNonTemporalStoreByteCoverageProved':True,
        'conditionalArbitraryNonTemporalLoopStoreCoverageProved':True,
        'conditionalPrecedingPayloadStoresOrderedBeforeFollowingStoresProved':True,
        'conditionalCopiedBytesAfterAllCheckedStoresVisibleProved':True,
        'conditionalStoreCoverageSelection':'all parent forward-safe/compatible same-element and normal-return selections; actual runtime stride equals independently checked Vector3 width; high aligned non-temporal branch selected; valid stable writable non-wrapping compatible ordinary memory and supported vector/fence state; no interfering payload/frame/bitset writes. The original head, loop chunks and rebased tail all write their corresponding initial source bytes, including any overlapping cached writes.',
        'allPayloadStoresGloballyVisibleAtReturnProved':False,'subsequentLoadOrderingProved':False,
        'postFenceParentPublicationStoreJoinProved':False,'nonTemporalCopyImplementationProved':False,
        'backwardCopyImplementationProved':False,'runtimeStrideProved':False,'runtimeModeOrCPUSelectionProved':False,
        'bulkCopyImplementationProved':False,'existingValuesPreservedAcrossResizeProved':False,'runtimeExecutionObserved':False}


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
    if after.status!='validated' or not matches():return {'status':'mismatched','detail':'Selected native inputs changed during non-temporal proof','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
