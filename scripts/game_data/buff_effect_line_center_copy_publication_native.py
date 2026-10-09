"""Join checked non-temporal stores to actual list publication and old reads.

Publication visibility and stable compatible reader selection remain explicit
conditions. This does not assert a live array class, fresh allocation or read
ordering supplied by SFENCE.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.integer_registers import decode_integer_register_instructions
from scripts.game_data.il2cpp.sse_lanes import decode_lane_transfer_instructions
from scripts.game_data.il2cpp.scalar_memory_moves import decode_fragment_instruction,prove_indexed_value_fragments
from scripts.game_data import buff_effect_line_center_copy_non_temporal_native as nt_owner
from scripts.game_data import buff_effect_line_center_population_native as population_owner

point_owner=population_owner.point_owner
argument_owner=nt_owner.loop_owner.small_owner.rep_owner.argument_owner
SCHEMA='endfield.buff-effect-line-center-copy-publication-native-contract.v1'
LABEL='buffEffectLineCenterCopyPublication'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_copy_publication_native.json'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _move(row,*,direction,register,bits,base,displacement):
    op=decode_fragment_instruction(bytes.fromhex(row['bytes']),int(row['va'],16),label=LABEL)
    expected={'base':base,'index':None,'scale':1,'displacement':displacement,'ripRelative':False,'addressBits':64}
    if (op['direction']!=direction or op['backingRegister']!=register or op['registerBits']!=bits
            or op['memoryBytes']!=bits//8 or op['registerBitOffset']!=0 or op['address']!=expected
            or op['valueExtension'] is not None or op['requiredAlignmentBytes']!=1 or op['nonTemporalHint'] is not False):
        _fail('publication-move',{'direction':direction,'register':register,'bits':bits,'address':expected},op)
    return op


def _publication(rows,pointers):
    g=ProgramGrammar(rows,label=LABEL+'.publication')
    allocate=g.call(pointers['allocateArray']);count_test=g.take('cmp [rbx+0x18], 0x0')
    if bytes.fromhex(count_test['bytes'])!=bytes.fromhex('837B1800'):g.fail('old-count-compare-width','signed dword comparison with zero',count_test)
    saved=g.take('mov rdi, rax')
    if bytes.fromhex(saved['bytes'])!=b'\x48\x8b\xf8':g.fail('saved-allocation-reference-width','qword RAX to RDI',saved)
    skip=g.row();raw=bytes.fromhex(skip['bytes']);at=int(skip['va'],16)
    if len(raw)!=2 or raw[0]!=0x7e:g.fail('count-copy-selection','signed short JLE to actual publication store',skip)
    skip_target=at+2+int.from_bytes(raw[1:],'little',signed=True)
    if skip['text'] not in (f'jle 0x{skip_target:x}',f'jcc 0x{skip_target:x}'):g.fail('count-copy-branch-decoding',hex(skip_target),skip)
    count=g.take('mov ecx, [rbx+0x18]');_move(count,direction='load',register='rcx',bits=32,base='rbx',displacement=24)
    g.take('xor r9d, r9d')
    context=g.take('mov [rsp+0x28], 0x0')
    if bytes.fromhex(context['bytes'])!=bytes.fromhex('48C744242800000000'):g.fail('hidden-context-width','zero qword hidden context',context)
    destination=g.take('mov r8, rax')
    if bytes.fromhex(destination['bytes'])!=b'\x4c\x8b\xc0':g.fail('same-allocated-destination','qword RAX to R8',destination)
    length=g.take('mov [rsp+0x20], ecx');_move(length,direction='store',register='rcx',bits=32,base='rsp',displacement=32)
    g.take('xor edx, edx');source=g.take('mov rcx, [rbx+0x10]');_move(source,direction='load',register='rcx',bits=64,base='rbx',displacement=16)
    copy=g.call(pointers['arrayCopy']);store=g.take('mov [rbx+0x10], rdi')
    move=_move(store,direction='store',register='rdi',bits=64,base='rbx',displacement=16);g.finish()
    if skip_target!=int(store['va'],16) or int(copy['va'],16)+len(bytes.fromhex(copy['bytes']))!=int(store['va'],16):
        g.fail('actual-copy-return-publication-join','next original instruction is the publication store',{'copy':copy,'store':store,'skip':skip_target})
    return {'completeAllocationToPublicationBlockChecked':True,'allocatedReferencePassedAsCopyDestinationProved':True,
        'allocatedReferenceSavedInRDIProved':True,'copyReturnsImmediatelyToPublicationStoreProved':True,
        'allocatedReferenceStoredAfterCopyProved':True,'publicationSlotBytes':move['memoryBytes'],
        'listItemsSlot':move['address']['displacement'],'copyCall':copy,'publicationStore':store,'allocationCall':allocate,
        'positiveOldCountSelected':True,'allocationFreshnessProved':False,'runtimeExecutionObserved':False}


def _outer_preservation(rows,fast_pointer):
    # Complete original caller grammar includes all selected return paths.
    argument_owner._outer(rows,fast_pointer)
    save=next(row for row in rows if row['text']=='mov [rsp+0x10], rbx')
    restore=next(row for row in rows if row['text']=='mov rbx, [r11+0x38]')
    _move(save,direction='store',register='rbx',bits=64,base='rsp',displacement=16)
    _move(restore,direction='load',register='rbx',bits=64,base='r11',displacement=56)
    for text,raw_hex in (('sub rsp, 0x70','4883EC70'),('lea r11, [rsp+0x70]','4C8D5C2470'),('mov rsp, r11','498BE3')):
        row=next(row for row in rows if row['text']==text)
        if bytes.fromhex(row['bytes'])!=bytes.fromhex(raw_hex):_fail('return-frame-width',raw_hex,row)
    pushes=[row for row in rows if row['text'].startswith('push ')];pops=[row for row in rows if row['text'].startswith('pop ')]
    if [row['text'][5:] for row in pushes]!=list(reversed([row['text'][4:] for row in pops])):
        _fail('matched-return-stack','push/pop inverse',{'pushes':pushes,'pops':pops})
    for row in pushes+pops:
        raw=bytes.fromhex(row['bytes'])
        if not (len(raw)==1 and 0x50<=raw[0]<=0x5f or len(raw)==2 and raw[0]==0x41 and 0x50<=raw[1]<=0x5f):
            _fail('qword-push-pop','unprefixed default-address stack transfer',row)
    if 56-len(pushes)*8!=16:_fail('saved-list-reference-slot','same entry-stack address',len(pushes))
    if pushes[0]['text']!='push rdi' or pops[-1]['text']!='pop rdi':_fail('saved-allocation-register','first pushed and last restored RDI',(pushes,pops))
    return {'completeActualArrayCopyReturnFrameChecked':True,'allocatedRDIAndListRBXPreservedAcrossSelectedArrayCopyProved':True,
        'selection':'normal checked helper/bulk completion with required nonvolatile preservation; stable valid caller stack disjoint from payloads and optional bitset'}


def _reader(rows,pointers):
    proof=point_owner._list_get_item(rows,pointers)
    output=next(row for row in rows if row['text']=='mov r9, rcx')
    if bytes.fromhex(output['bytes'])!=bytes.fromhex('4C8BC9'):_fail('reader-output-reference-width','qword incoming RCX to R9',output)
    slot=next(row for row in rows if row['text']=='mov rax, [rdx+0x10]')
    _move(slot,direction='load',register='rax',bits=64,base='rdx',displacement=proof['listItemsOffset'])
    signed=next(row for row in rows if row['text']=='movsxd rcx, r8d')
    triple=next(row for row in rows if row['text']=='lea rdx, [rcx+rcx*2]')
    if bytes.fromhex(signed['bytes'])!=b'\x49\x63\xc8' or bytes.fromhex(triple['bytes'])!=b'\x48\x8d\x14\x49':
        _fail('element-index-arithmetic','qword signed index and three-times-index address',(signed,triple))
    first=next(i for i,row in enumerate(rows) if row['text']=='movsd xmm0, [rax+0x20+rdx*4]')
    fragments=[decode_fragment_instruction(bytes.fromhex(row['bytes']),int(row['va'],16),label=LABEL+'.reader') for row in rows[first:first+4]]
    values=prove_indexed_value_fragments(fragments,source_base='rax',source_index='rdx',index_scale=4,
        data_offset=proof['arrayDataOffset'],output_base='r9',output_bytes=proof['outputBytes'],label=LABEL+'.reader')
    return {**proof,'itemsReferenceLoad':slot,'indexedReadBytesProved':values,
        'elementReadEquation':'observed items reference + checked payload offset + checked twelve-byte element stride * selected nonnegative old index',
        'publicationVisibilityAtReadProved':False}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if contract.get('scope')!='conditional-non-temporal-publication-and-visible-old-point-read' or set(contract.get('joins',{}))!={'publicationStartRva','publicationEndRva'}:
        _fail('contract-shape','allocation-to-publication block in existing complete parent capacity program',contract.get('scope'))
    return contract


def _validate_image(image,contract):
    base=image.pe.image_base;nt_contract=nt_owner._contract();population_contract=population_owner._contract();point_contract=point_owner._contract()
    if any(parent['nativeInputs']!=contract['nativeInputs'] for parent in (nt_contract,population_contract,point_contract)):
        _fail('same-parent-build','identical selected native inputs',[parent['nativeInputs'] for parent in (nt_contract,population_contract,point_contract)])
    nt=nt_owner._validate_image(image,nt_contract)
    population=population_owner._validate_image(image,population_contract)
    pointers={role:base+rva for role,rva in population_contract['callTargets'].items()}
    primary=population_contract['programs']['setCapacity']['windows'][0]
    window={'startRva':contract['joins']['publicationStartRva'],'endRva':contract['joins']['publicationEndRva']}
    if not primary['startRva']<=window['startRva']<window['endRva']<=primary['endRva']:
        _fail('owned-publication-range',primary,window)
    publication=_publication(decode_integer_register_instructions(image.mapper,image.window_bytes(window),base+window['startRva']),pointers)
    if publication['copyCall']['va']!=population['setCapacity']['existingPositiveCountCopyCall']['va']:
        _fail('actual-parent-copy-call',population['setCapacity']['existingPositiveCountCopyCall'],publication['copyCall'])
    args=argument_owner._contract();outer=args['blocks']['outer']
    if (args['nativeInputs']!=contract['nativeInputs'] or outer['startRva']!=population_contract['callTargets']['arrayCopy']
            or outer['startRva']!=args['programs']['arrayCopy']['entryRva']):
        _fail('actual-array-copy-entry-join','same build and actual called Array.Copy entry',{'outer':outer,'args':args['nativeInputs']})
    frame=_outer_preservation(decode_integer_register_instructions(image.mapper,image.window_bytes(outer),base+outer['startRva']),base+args['programs']['fastHelper']['entryRva'])
    getter=point_contract['programs']['getItem']['windows'][0]
    reader=_reader(decode_lane_transfer_instructions(image.mapper,image.window_bytes(getter),base+getter['startRva']),
        {role:base+rva for role,rva in point_contract['callTargets'].items()})
    if publication['listItemsSlot']!=reader['listItemsOffset'] or reader['arrayElementStride']!=reader['outputBytes']:
        _fail('same-published-slot-and-read-stride','same compiled items slot and complete element width',{'publication':publication,'reader':reader})
    if not (nt['conditionalNonTemporalStoreByteCoverageProved'] and nt['conditionalPrecedingPayloadStoresOrderedBeforeFollowingStoresProved']
            and nt['conditionalCopiedBytesAfterAllCheckedStoresVisibleProved']):
        _fail('required-parent-store-and-fence-facts','all authenticated prerequisite claims',nt)
    return {'nonTemporalAndPopulationProofsRevalidatedOnSameImage':True,'publication':publication,'returnFrame':frame,'reader':reader,
        'postFenceParentPublicationStoreJoinProved':True,
        'conditionalPayloadStoresVisibleBeforeActualItemsPublicationStoreVisibleProved':True,
        'conditionalOldPointReadFromVisiblePublishedArrayProved':True,
        'conditionalOldPointReadSelection':'all selected parent same-element/high non-temporal/normal-return, memory/frame/bitset conditions; actual runtime class stride equals independently checked getter element width; allocation result is a valid compatible destination array; required register/stack preservation; same compatible list header and published items reference remain stable and do not alias source headers; publication store is globally visible before the selected getter payload read, whose input observes that reference; stable coherent compatible memory, no intervening overwrite, nonnegative old index below original count and current list/array bounds, valid disjoint output buffer',
        'allPayloadStoresGloballyVisibleAtReturnProved':False,'subsequentLoadOrderingSuppliedBySFENCEProved':False,
        'actualPublicationVisibilityAtReadProved':False,'runtimeStrideProved':False,'allocationFreshnessProved':False,
        'sourceTemporaryNonaliasingLifetimeProved':False,'nonTemporalCopyImplementationProved':False,
        'backwardCopyImplementationProved':False,'bulkCopyImplementationProved':False,
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
    if after.status!='validated' or not matches():return {'status':'mismatched','detail':'Selected native inputs changed during publication proof','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
