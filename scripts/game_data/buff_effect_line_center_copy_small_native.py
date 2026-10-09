"""Prove selected small, snapshot and bounded vector bulk-copy programs.

All lengths in each native bound are covered by distinct symbolic source-byte
identities. Larger vector/backward paths, live stride/providers and general
resize preservation remain open; no execution outcome is inferred.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
from scripts.common import check_installed_native_inputs
from scripts.game_data.contracts import CONTRACTS_DIR
from scripts.game_data.il2cpp.native_image import open_native_image,read_reviewed_contract
from scripts.game_data.il2cpp.program_grammar import ProgramGrammar
from scripts.game_data.il2cpp.memory_moves import decode_memory_move_instructions
from scripts.game_data.il2cpp.byte_copy_programs import prove_byte_copy_moves
from scripts.game_data import buff_effect_line_center_copy_rep_native as rep_owner

SCHEMA='endfield.buff-effect-line-center-copy-small-native-contract.v1'
LABEL='buffEffectLineCenterCopySmall'
CONTRACT_PATH=CONTRACTS_DIR/'buff_effect_line_center_copy_small_native.json'


def _fail(check,expected,actual):
    raise ValueError(f'{LABEL}.{check}: source={CONTRACT_PATH.as_posix()} expected={str(expected)[:384]} actual={str(actual)[:512]}')


def _table_load(g,*,destination,index,table):
    row=g.row();op=row.get('memoryOperation',{});address=op.get('address',{})
    expected={'base':'r10','index':index,'scale':4,'displacement':table['startRva'],'ripRelative':False,'addressBits':64}
    if (op.get('direction')!='load' or op.get('register')!=destination+'d' or op.get('backingRegister')!=destination
            or op.get('registerBits')!=32 or op.get('registerBitOffset')!=0 or op.get('memoryBytes')!=4
            or op.get('upperRegisterEffect')!='zero upper 32 bits' or op.get('valueExtension') is not None
            or address!=expected or op.get('nonTemporalHint') is not False or op.get('writesFlags') is not False):
        g.fail('dispatch-dword-load',{'destination':destination,'address':expected},row)
    return row


def _small_dispatch(rows,*,small_limit,table,image_base):
    g=ProgramGrammar(rows,label=LABEL+'.smallDispatch')
    g.take('mov rax, rcx');origin=g.pattern(r'lea r10, \[rip[+-]0x[0-9a-f]+ => 0x[0-9a-f]+\]')
    if origin.get('addressOperation',{}).get('absoluteAddress')!=image_base:
        g.fail('image-base-origin',image_base,origin)
    g.take(f'cmp r8, 0x{small_limit:x}');large=g.branch('ja')
    padding=g.take('nop')
    if padding.get('paddingOperation',{}).get('readsMemory') is not False:g.fail('padding','no memory read',padding)
    load=_table_load(g,destination='r9',index='r8',table=table)
    addition=g.take('add r9, r10')
    if addition.get('integerOperation',{}).get('bits')!=64:g.fail('table-target-width',64,addition)
    g.take('jmp r9');g.finish()
    if len(table['entries'])!=small_limit+1:g.fail('small-index-bound',small_limit+1,len(table['entries']))
    return {'completeDispatchChecked':True,'selectedIndex':'incoming unsigned byte count',
        'indexMinimum':0,'indexMaximum':small_limit,'largeEntryEdge':large,'tableLoad':load}


def _payload(rows,*,label,cleanup_allowed=False):
    g=ProgramGrammar(rows,label=LABEL+'.'+label);moves=[];cleanup=False
    while g.cursor<len(g.rows):
        row=g.row()
        if row['text']=='ret':
            if bytes.fromhex(row['bytes'])!=b'\xc3':g.fail('plain-return','C3',row)
            g.finish();return {'moves':moves,'cleanupChecked':cleanup,'completeReturnChecked':True}
        if row['text']=='vzeroupper' and cleanup_allowed:
            effect=row.get('vectorStateOperation',{})
            if (cleanup or bytes.fromhex(row['bytes'])!=b'\xc5\xf8\x77'
                    or effect.get('registerNumbers')!=list(range(16)) or effect.get('preservesLow128Bits') is not True
                    or effect.get('zerosBits128Through255') is not True or effect.get('writesMemory') is not False
                    or effect.get('writesFlags') is not False):g.fail('vector-cleanup','checked low-lane-preserving cleanup',row)
            cleanup=True;continue
        op=row.get('memoryOperation')
        if not op or cleanup:g.fail('payload-program','exact memory moves then optional cleanup and plain RET',row)
        backing=op.get('backingRegister','')
        if op.get('direction')=='load' and (backing in ('rax','rsp','rbx','rbp','rsi','rdi','r12','r13','r14','r15')
                or backing.startswith('vector') and int(backing[6:])>=6):
            g.fail('held-register-preservation','return register and nonvolatile GP/low-vector registers untouched',row)
        moves.append(op)
    g.fail('program-end','complete plain return','end')


def _vector_prefix(rows,*,width,limit):
    g=ProgramGrammar(rows,label=LABEL+'.vectorPrefix');moves=[]
    for number,index,displacement in ((0,None,0),(5,'r8',-width)):
        row=g.row();op=row.get('memoryOperation',{})
        expected={'base':'rdx','index':index,'scale':1,'displacement':displacement,'ripRelative':False,'addressBits':64}
        if (op.get('direction')!='load' or op.get('backingRegister')!=f'vector{number}' or op.get('memoryBytes')!=width
                or op.get('registerBits')!=width*8 or op.get('registerBitOffset')!=0 or op.get('address')!=expected
                or op.get('valueExtension') is not None or op.get('requiredAlignmentBytes')!=1
                or op.get('nonTemporalHint') is not False or op.get('writesFlags') is not False):
            g.fail('saved-head-tail',{'width':width,'register':number,'address':expected},row)
        moves.append(op)
    comparison=g.take(f'cmp r8, 0x{limit:x}');raw=bytes.fromhex(comparison['bytes'])
    if len(raw)!=7 or raw[:3]!=b'\x49\x81\xf8' or int.from_bytes(raw[3:],'little',signed=True)!=limit:
        g.fail('vector-limit-width','qword comparison with current positive bound',comparison)
    tail=g.branch('jbe');g.finish()
    return {'moves':moves,'tailEntryEdge':tail,'completeSelectedPrefixChecked':True}


def _vector_tail(rows,*,width,table):
    g=ProgramGrammar(rows,label=LABEL+'.vectorTail')
    lea=g.take(f'lea r9, [r8+0x{width-1:x}]')
    if lea.get('addressOperation',{}).get('destinationBits')!=64:g.fail('rounding-width',64,lea)
    mask=g.take(f'and r9, -0x{width:x}');raw=bytes.fromhex(mask['bytes'])
    if len(raw)!=4 or raw[:3]!=b'\x49\x83\xe1' or int.from_bytes(raw[3:],'little',signed=True)!=-width:
        g.fail('rounding-mask','qword AND with signed negative width',mask)
    transfer=g.take('mov r11, r9');shift=g.take(f'shr r11, 0x{width.bit_length()-1:x}')
    if bytes.fromhex(transfer['bytes'])!=b'\x4d\x8b\xd9' or bytes.fromhex(shift['bytes'])!=bytes((0x49,0xc1,0xeb,width.bit_length()-1)):
        g.fail('rounding-index-width','qword transfer and logical right shift',{'transfer':transfer,'shift':shift})
    _table_load(g,destination='r11',index='r11',table=table)
    addition=g.take('add r11, r10')
    if addition.get('integerOperation',{}).get('bits')!=64:g.fail('table-target-width',64,addition)
    g.take('jmp r11');g.finish(prefix=True)
    payload=rows[g.cursor:];_payload(payload,label='allTailInstructions',cleanup_allowed=width==32)
    starts={int(row['va'],16):i for i,row in enumerate(payload)}
    return {'payloadRows':payload,'payloadInstructionIndices':starts,
        'indexEquation':f'((unsigned length + {width-1}) & -{width}) >> {width.bit_length()-1}',
        'roundingBits':64,'dispatchHeaderChecked':True}


def _prove_payload(moves,*,length,rounded=None,overlap='forward-safe',label):
    scalars={'r8':length}
    if rounded is not None:scalars['r9']=rounded
    return prove_byte_copy_moves(moves,length=length,pointers={'rdx':'source','rcx':'destination','rax':'destination'},
        scalars=scalars,overlap=overlap,label=LABEL+'.'+label)


def _prove_vector(rows_prefix,rows_tail,*,width,limit,medium_limit,table,image_base):
    prefix=_vector_prefix(rows_prefix,width=width,limit=limit);tail=_vector_tail(rows_tail,width=width,table=table)
    if width not in (16,32) or limit%width or limit//width+1!=len(table['entries']) or not medium_limit<limit:
        _fail('finite-vector-bound','positive native bound matching available width/table cases',(width,limit,medium_limit,len(table['entries'])))
    proofs=[];indices=set()
    for length in range(medium_limit+1,limit+1):
        rounded=(length+width-1)&-width;index=rounded//width
        if not 0<=index<len(table['entries']):_fail('vector-index-bound',len(table['entries']),index)
        target=image_base+table['entries'][index]
        if target not in tail['payloadInstructionIndices']:_fail('table-target-instruction-boundary',sorted(tail['payloadInstructionIndices']),target)
        selected=_payload(tail['payloadRows'][tail['payloadInstructionIndices'][target]:],label='selectedTail',cleanup_allowed=width==32)
        proof=_prove_payload(prefix['moves']+selected['moves'],length=length,rounded=rounded,label='vectorBytes')
        proofs.append({'length':length,'index':index,'rounded':rounded,'loads':proof['loads'],'stores':proof['stores']});indices.add(index)
    return {'completeSelectedPrefixAndTailsChecked':True,'tailEntryEdge':prefix['tailEntryEdge'],
        'widthBytes':width,'lengthMinimum':medium_limit+1,'lengthMaximum':limit,'finiteLengthsProved':len(proofs),
        'selectedIndices':sorted(indices),'indexEquation':tail['indexEquation'],'proofs':proofs,
        'allSelectedBytesEqualInitialSourceProved':True,'allSelectedPayloadRangesInBoundsProved':True,
        'forwardSafeOverlapProved':True,'actualModeOrCPUSelectionObserved':False}


def _contract():
    contract,_=read_reviewed_contract(CONTRACT_PATH,schema=SCHEMA,status='exact-current-build',label=LABEL)
    if (contract.get('scope')!='conditional-small-snapshot-and-bounded-vector-byte-copy'
            or set(contract.get('blocks',{}))!={'smallDispatch','snapshot','highPrefix','highTail','lowPrefix','lowTail'}
            or set(contract.get('tables',{}))!={'small','high','low'} or set(contract.get('vectors',{}))!={'high','low'}):
        _fail('contract-shape','selected blocks, three dispatch tables, small leaves and two vector bounds',contract.get('scope'))
    return contract


def _validate_image(image,contract):
    parent=rep_owner._contract();base=image.pe.image_base
    if parent['nativeInputs']!=contract['nativeInputs']:_fail('same-parent-build',parent['nativeInputs'],contract['nativeInputs'])
    rep=rep_owner._validate_image(image,parent)
    bulk=rep_owner.argument_owner._contract()['programs']['bulk']
    if contract['bulkEntryRva']!=bulk['entryRva']:_fail('actual-bulk-entry',bulk['entryRva'],contract['bulkEntryRva'])
    def owned(window):
        if not any(w['startRva']<=window['startRva']<window['endRva']<=w['endRva'] for w in bulk['windows']):
            _fail('owned-program-range',bulk['windows'],window)
    rows={}
    for role,window in contract['blocks'].items():
        owned(window);rows[role]=decode_memory_move_instructions(image.mapper,image.window_bytes(window),base+window['startRva'])
    tables=contract['tables']
    for role,table in tables.items():
        image.check_windows([table],label=LABEL,gate='dispatch-table')
        raw=image.window_bytes(table)
        if len(raw)%4 or [int.from_bytes(raw[i:i+4],'little') for i in range(0,len(raw),4)]!=table['entries']:
            _fail('raw-table-entries:'+role,table['entries'],raw.hex())
        if any(base+rva>=(1<<64) for rva in table['entries']):_fail('table-target-no-wrap','valid loaded image',table['entries'])
    constants=rep['selectionConstants'];small_limit=constants['smallLimit'];medium_limit=constants['mediumLimit']
    if not 0<=small_limit<medium_limit:_fail('size-order','small < medium',(small_limit,medium_limit))
    dispatch=_small_dispatch(rows['smallDispatch'],small_limit=small_limit,table=tables['small'],image_base=base)
    if (contract['blocks']['smallDispatch']['startRva']!=bulk['entryRva']
            or dispatch['largeEntryEdge']['target']!=base+parent['blocks']['medium']['startRva']
            or contract['blocks']['snapshot']['startRva']!=parent['blocks']['medium']['endRva']):
        _fail('small-and-snapshot-entry-joins','actual bulk/medium fallthrough entries',contract['blocks'])
    leaves=contract['smallLeaves']
    if len(leaves)!=len(tables['small']['entries']):_fail('small-leaf-count',len(tables['small']['entries']),len(leaves))
    small=[]
    for length,(window,target) in enumerate(zip(leaves,tables['small']['entries'])):
        owned(window)
        if window['startRva']!=target:_fail('actual-small-table-target',target,window)
        decoded=decode_memory_move_instructions(image.mapper,image.window_bytes(window),base+window['startRva'])
        payload=_payload(decoded,label='smallLeaf');proof=_prove_payload(payload['moves'],length=length,overlap='arbitrary',label='smallBytes')
        small.append({'length':length,'loads':proof['loads'],'stores':proof['stores'],'arbitraryOverlapSafe':proof['arbitraryOverlapSafe']})
    snapshot_payload=_payload(rows['snapshot'],label='snapshot')
    snapshot=[_prove_payload(snapshot_payload['moves'],length=n,overlap='arbitrary',label='snapshotBytes') for n in range(small_limit+1,medium_limit+1)]
    vectors={}
    for role in ('high','low'):
        declaration=contract['vectors'][role]
        vectors[role]=_prove_vector(rows[role+'Prefix'],rows[role+'Tail'],width=declaration['widthBytes'],limit=declaration['lengthMaximum'],
            medium_limit=medium_limit,table=tables[role],image_base=base)
        entry=rep['common']['highVectorEntryEdge']['target'] if role=='high' else rep['low']['lowVectorEntryEdge']['target']
        rep_minimum=constants['highRepMinimum'] if role=='high' else constants['lowRepMinimum']
        if (entry!=base+contract['blocks'][role+'Prefix']['startRva'] or declaration['lengthMaximum']>rep_minimum
                or vectors[role]['tailEntryEdge']['target']!=base+contract['blocks'][role+'Tail']['startRva']):
            _fail('bounded-vector-entry-joins','current vector entry below REP threshold and actual tail edge',role)
    common_maximum=min(vectors['high']['lengthMaximum'],vectors['low']['lengthMaximum'])
    return {'repAndArgumentProofRevalidated':True,'smallDispatch':dispatch,'small':small,
        'snapshot':{'lengthMinimum':small_limit+1,'lengthMaximum':medium_limit,'finiteLengthsProved':len(snapshot),
            'allSelectedBytesEqualInitialSourceProved':True,'arbitraryOverlapSafe':True},'vectors':vectors,
        'conditionalSmallSnapshotAndVectorByteCopyProved':True,'allModeForwardSafeLengthMaximum':common_maximum,
        'conditionalFortyEightByteCopyProved':medium_limit<48<=common_maximum,
        'conditionalOldPointPreservationViaSelectedSmallBulkPathsProved':True,
        'conditionalOldPointPreservationSelection':'parent same-element and normal-return selections; actual class stride equals independently checked Vector3 width; byte length selects a proved small/snapshot/bounded vector path; valid stable non-wrapping arrays, code and tables; supported instruction/CPU state; payloads disjoint from caller frame and optional bitset; successful optional bitset retry; vector overlap is forward-safe; selected new-array reference then checked append',
        'returnDestinationAndRequiredNonvolatilePreservationProved':True,'runtimeStrideProved':False,
        'runtimeModeOrCPUSelectionProved':False,'bulkCopyImplementationProved':False,
        'existingValuesPreservedAcrossResizeProved':False,'runtimeExecutionObserved':False,
        'directionFlagNotUsedBySelectedMovePrograms':True}


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
    if after.status!='validated' or not matches():return {'status':'mismatched','detail':'Selected native inputs changed during small copy validation','nativeInputs':pins}
    return {'status':'validated','nativeInputs':pins,**result,'evidenceBoundary':contract['evidenceBoundary']}
