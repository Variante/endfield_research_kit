"""Prove a selected anonymous resolver scan and its bounded table control.

The complete owned byte partition and original branch/operand grammar are
checked together. Carrier meaning, conversion results, live globals and
execution remain outside this conditional static proof.

Exact (pinned bytes) conclusions:

- each table transfer loads the image base, a zero-extended byte selector,
  then a zero-extended DWORD target indexed by four, and jumps to target+base;
- tags pass signed nested-byte interval checks, then a DWORD bias/subtraction
  and an unsigned upper-bound guard before any table read;
- the record counter is a word and the parameter counter a DWORD; neither
  can wrap within the checked guards;
- the pair address is a DWORD offset plus a UInt16 selector, sign-extended,
  biased and scaled;
- each index leaf returns 0 on a -1 sentinel, otherwise the sign-extended
  header offset + base + scaled index. Both leaves preserve the caller's
  reused volatile scan registers without assuming a calling convention, and
  no unwind extent is invented for them.

The exhaustive byte inventory of guarded routes does not prove that any
route executed.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_tag_dispatch import decode_tag_dispatch_instructions
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.owned_partition import (
    BranchGrammar as _Grammar, check_byte_partition, checked_rows, owned_windows, rip_load as _rip_load, window_bytes)

_LABEL='resolverScan'


def _raw(index,start,end,digest):
    return window_bytes(index,start,end,digest,_LABEL)


def _rows(index,start,end,digest):
    raw=_raw(index,start,end,digest)
    return checked_rows(decode_tag_dispatch_instructions(index.mapper,raw,start),raw,_LABEL)


def _partition(index,c):
    base=index.pe.image_base;owned,pieces,windows=owned_windows(index,c,_LABEL)
    if len(c['tables'])!=2:raise ValueError('resolverScan.table-count')
    for table in c['tables']:
        count=table['selectorCount'];target_count=table['targetCount'];selectors=table['selectors'];targets=table['targets']
        if count!=c['layout']['tableIndexMax']+1 or not 0<count<=256 or len(selectors)!=count or not 0<target_count<=256 or len(targets)!=target_count:
            raise ValueError('resolverScan.table-counts')
        if len(table['targetLabels'])!=target_count or any(not isinstance(n,int) or not 0<=n<target_count for n in selectors):
            raise ValueError('resolverScan.selector-target-bound')
        for kind,size,values,digest in (
            ('selector',count,bytes(selectors),table['selectorTableSha256']),
            ('target',target_count*4,b''.join(n.to_bytes(4,'little') for n in targets),table['targetTableSha256'])):
            start=base+table[kind+'TableRva'];raw=_raw(index,start,start+size,digest)
            if raw!=values:raise ValueError('resolverScan.table-values:'+kind)
            pieces.append((start,start+size,kind+'Table'))
    check_byte_partition(owned,pieces,_LABEL)
    return [checked_rows(decode_tag_dispatch_instructions(index.mapper,raw,start),raw,_LABEL)
            for category,_w,start,raw in windows if category=='codeWindows']


def _table_control(g,c,table,skip):
    base=c['_base'];l=c['layout']
    g.take(f'sub ecx, 0x{l["tableTagStart"]:x}',f'cmp ecx, 0x{l["tableIndexMax"]:x}')
    g.branch('ja',skip);g.take('movsxd rax, ecx')
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    target=at+7+int.from_bytes(raw[3:],'little',signed=True) if len(raw)==7 and raw[:3]==b'\x48\x8d\x3d' else None
    if target!=base:g.fail('table-image-base',hex(base),row)
    row=g.take(f'movzx eax, byte [rdi+rax*1+0x{table["selectorTableRva"]:x}]')
    f=row['byteMemoryZeroExtensionOperation'];a=f['sourceAddress']
    if (f['destinationRegister'],f['destinationBits'],f['memoryReadBytes'],f['zeroExtendsTo64'],a['base'],a['index'],a['scale'],a['displacement'])!=('eax',32,1,True,'rdi','rax',1,table['selectorTableRva']):
        g.fail('selector-load','zero-extending selected byte load',f)
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('target-load','complete target memory move',row)
    f=decoded[0]['memoryOperation'];a=f['address']
    if (f['direction'],f['register'],f['registerBits'],f['memoryBytes'],f['upperRegisterEffect'],a['base'],a['index'],a['scale'],a['displacement'])!=('load','ecx',32,4,'zero upper 32 bits','rdi','rax',4,table['targetTableRva']):
        g.fail('target-load','zero-extending selected dword load with scale four',f)
    g.take('add rcx, rdi');row=g.take('jmp rcx')
    if bytes.fromhex(row['bytes'])!=b'\xff\xe1':g.fail('table-indirect-transfer','full RCX indirect jump',row)


def _index_leaf(index,c,spec):
    base=index.pe.image_base
    rows=_rows(index,base+spec['entryRva'],base+spec['endRva'],spec['sha256'])
    g=_Grammar(rows,label='resolverScan.indexLeaf')
    g.take('cmp ecx, -0x1');g.branch('jne','indexed');g.take('xor eax, eax','ret')
    g.mark('indexed');_rip_load(g,'rax',base+c['globalCells']['leafHeader'])
    g.take(f'movsxd rdx, dword [rax+0x{spec["headerOffsetWord"]:x}]')
    g.take(f'add rdx, qword [rip => 0x{base+c["globalCells"]["leafBase"]:x}]',
           'movsxd rax, ecx',f'shl rax, 0x{spec["recordShift"]:x}','add rax, rdx','ret')
    g.finish()
    return {'entryRva':spec['entryRva'],'checkedInstructions':len(rows),'completeTwoReturnControlChecked':True,
        'preservedCallerRegisters':['r8','r9','r10'],'minusOneDwordSentinelReturnsFullZero':True,
        'conditionalAddress':'blobBase + signExtend32(headerOffsetWord) + (signExtend32(index) << recordShift), modulo 2^64',
        'liveHeaderBaseIdentityOrBoundsProved':False}


def _guard_mapping(c,table):
    l=c['layout'];mapping=[]
    for raw in range(256):
        signed=raw if raw<128 else raw-256
        position=(signed-l['tableTagStart'])&0xffffffff
        row={'rawByte':raw,'signedValue':signed}
        if l['directTagIntervalStart']<=signed<l['directTagIntervalEndExclusive']:row['route']='direct-skip'
        elif position>l['tableIndexMax']:row['route']='unsigned-guard-skip'
        else:
            selector=table['selectors'][position]
            row.update(route='table',index=position,selector=selector,targetRva=table['targets'][selector],targetLabel=table['targetLabels'][selector])
        mapping.append(row)
    return mapping


def validate_resolver_scan_control(index,c):
    base=index.pe.image_base;l=c['layout'];calls=c['calls'];globals_=c['globalCells']
    windows=_partition(index,c)
    if len(windows)!=2:raise ValueError('resolverScan.code-window-count')
    primary,cold=windows;g=_Grammar(primary,label='resolverScan.primary');s=_Grammar(cold,label='resolverScan.cold')
    g.take('mov [rsp+0x8], rbx','push rbp','push rsi','push rdi','push r12','push r13','push r14','push r15','sub rsp, 0x30',
        f'cmp qword [rdx+0x{l["parameterContext"]:x}], 0x0','mov r14, rdx','movzx r12d, r8w','mov rsi, rcx')
    g.branch('je','nullResult');g.take(f'mov rcx, [rcx+0x{l["prepareArgumentPointer"]:x}]');g.call(base+calls['prepare'])
    g.take('xor r10d, r10d','movzx ebp, r10w',f'cmp r10w, word [rsi+0x{l["recordCount"]:x}]');g.branch('jae','nullResult')
    g.mark('recordLoop');g.take('movzx ebx, bp',f'shl rbx, 0x{l["recordStrideShift"]:x}',
        f'add rbx, qword [rsi+0x{l["recordStorage"]:x}]','mov rax, [rbx]',f'mov r8, [rax+0x{l["parameterContext"]:x}]','test r8, r8')
    g.branch('je','nextRecord');g.take(f'mov r9, [r14+0x{l["parameterContext"]:x}]','mov rdx, [r8]','mov rax, [r9]','mov rcx, [rax]','cmp [rdx], rcx')
    g.branch('je','matchingRecord');g.mark('nextRecord');g.take('inc bp',f'cmp bp, word [rsi+0x{l["recordCount"]:x}]')
    g.branch('jb','recordLoop');g.branch('jmp','nullResult')
    g.mark('matchingRecord');g.take(f'mov rax, [r8+0x{l["carrierItems"]:x}]',f'mov r9, [r9+0x{l["carrierItems"]:x}]',
        'mov [rsp+0x88], rax',f'mov rax, [r14+0x{l["parameterContext"]:x}]','mov [rsp+0x20], r9',
        'mov rcx, [rax]','mov rcx, [rcx]',f'mov ecx, [rcx+0x{l["definitionContainerIndex"]:x}]')
    g.call(base+calls['firstIndexLeaf']);g.take('cmp dword [r9], 0x0','mov r8d, r10d','mov [rsp+0x28], rax','mov [rsp+0x78], r10d')
    g.branch('jbe','matchedAllParameters');g.mark('parameterLoop')
    g.take(f'mov ecx, [rax+0x{l["metadataParameterStart"]:x}]','add ecx, r8d');g.call(base+calls['secondIndexLeaf'])
    g.take(f'mov rcx, [r9+0x{l["carrierItems"]:x}]','mov dl, 0x1',f'movzx r13d, word [rax+0x{l["parameterAttributes"]:x}]',
        'mov eax, r8d','mov rcx, [rcx+rax*8]','lea rdi, [rax*8]');g.call(base+calls['typeCarrier'])
    g.take('mov r15, rax','mov dl, 0x1','mov rax, [rsp+0x88]',f'mov rcx, [rax+0x{l["carrierItems"]:x}]','mov rcx, [rdi+rcx*1]')
    g.call(base+calls['typeCarrier']);g.take('mov r11, rax','and r13d, 0x3');g.branch('jne','varianceFlags')
    g.mark('plainCompare');g.take('cmp r15, r11');g.branch('je','nextParameter')
    g.take(f'cmp byte [rsi+0x{l["normalizationPermissionByte"]:x}], 0x0');g.branch('je','specialClassGuard')
    g.mark('normalization');g.take(f'cmp byte [r15+0x{l["tagByte"]:x}], 0x{l["bypassOuterTags"][0]:x}')
    for register,key in (('r8','normalizationR8'),('r9','normalizationR9'),('r10','normalizationR10'),('rdx','normalizationRdx')):
        _rip_load(g,register,base+globals_[key])
    g.branch('je','secondTag');g.take(f'cmp byte [r15+0x{l["tagByte"]:x}], 0x{l["bypassOuterTags"][1]:x}');g.branch('je','secondTag')
    g.take(f'mov rax, [r15+0x{l["nestedTagCarrier"]:x}]',f'movsx ecx, byte [rax+0x{l["tagByte"]:x}]',
        f'cmp ecx, 0x{l["directTagIntervalStart"]:x}');g.branch('jl','firstTable')
    g.take(f'cmp ecx, 0x{l["directTagIntervalEndExclusive"]:x}');g.branch('jge','firstTable')
    g.mark('secondTag');g.take(f'cmp byte [r11+0x{l["tagByte"]:x}], 0x{l["bypassOuterTags"][0]:x}');g.branch('je','originalSecond')
    g.take(f'cmp byte [r11+0x{l["tagByte"]:x}], 0x{l["bypassOuterTags"][1]:x}');g.branch('je','originalSecond')
    g.take(f'mov rax, [r11+0x{l["nestedTagCarrier"]:x}]',f'movsx ecx, byte [rax+0x{l["tagByte"]:x}]',
        f'cmp ecx, 0x{l["directTagIntervalStart"]:x}');g.branch('jl','secondTable')
    g.take(f'cmp ecx, 0x{l["directTagIntervalEndExclusive"]:x}');g.branch('jge','secondTable')
    g.mark('originalSecond');g.take('mov rdx, r11');g.mark('compareNormalized');g.take('cmp r15, rdx');g.branch('je','nextParameter')
    g.mark('rejectParameter');g.take('xor r10d, r10d');g.branch('jmp','nextRecord')
    g.mark('varianceFlags');g.take(f'mov ecx, [r15+0x{l["carrierFlags"]:x}]','shr ecx, 0x1f','test cl, cl');g.branch('jne','plainCompare')
    g.take(f'mov ecx, [rax+0x{l["carrierFlags"]:x}]','shr ecx, 0x1f','test cl, cl');g.branch('jne','plainCompare')
    g.take('cmp r13d, 0x1');g.branch('jne','reverseRelation');g.take('mov rdx, r11','mov rcx, r15');g.call(base+calls['relationPredicate'])
    g.take('test al, al');g.branch('je','rejectParameter');g.branch('jmp','nextParameter')
    g.mark('reverseRelation');g.take('mov rdx, r15','mov rcx, r11');g.call(base+calls['relationPredicate'])
    g.take('test al, al');g.branch('je','rejectParameter');g.mark('nextParameter')
    g.take('mov r8d, [rsp+0x78]','mov r9, [rsp+0x20]','inc r8d','mov [rsp+0x78], r8d','cmp r8d, [r9]');g.branch('jb','parameterContinue')
    g.mark('matchedAllParameters');g.take('mov eax, r12d',f'add eax, dword [rbx+0x{l["recordOffsetWord"]:x}]','cdqe',
        f'add rax, 0x{l["pairBiasUnits"]:x}',f'shl rax, 0x{l["pairScaleShift"]:x}','add rax, rsi')
    g.mark('epilogue');g.take('mov rbx, [rsp+0x70]','add rsp, 0x30','pop r15','pop r14','pop r13','pop r12','pop rdi','pop rsi','pop rbp','ret')
    g.mark('specialClassGuard');_rip_load(g,'rax',base+globals_['specialClassRax'])
    g.take(f'cmp [rsi+0x{l["specialClassTagPointer"]:x}], rax');g.branch('jne','rejectParameter');g.branch('jmp','normalization')
    table_context={**c,'_base':base}
    g.mark('firstTable');_table_control(g,table_context,c['tables'][0],'secondTag')
    g.mark('secondTable');_table_control(g,table_context,c['tables'][1],'originalSecond')
    g.mark('normalizeSecondR9');g.take('mov rdx, r9');g.branch('jmp','compareNormalized')
    g.mark('normalizeFirstR9');g.take('mov r15, r9');g.branch('jmp','secondTag')
    for label,text,target in (('normalizeFirstRdx','mov r15, rdx','secondTag'),('normalizeFirstR10','mov r15, r10','secondTag'),
        ('normalizeFirstR8','mov r15, r8','secondTag'),('normalizeSecondR10','mov rdx, r10','compareNormalized'),
        ('normalizeSecondR8','mov rdx, r8','compareNormalized'),('parameterContinue','mov rax, [rsp+0x28]','parameterLoop'),
        ('nullResult','xor eax, eax','epilogue')):
        s.mark(label);s.take(text);s.branch('jmp',target)
    labels={**g.labels,**s.labels};starts={int(r['va'],16) for rows in windows for r in rows}
    if not set(labels.values())<=starts:raise ValueError('resolverScan.label-instruction-boundary')
    g.labels.update(labels);s.labels.update(labels);g.finish();s.finish()
    for pointer in calls.values():
        target=base+pointer
        if any(base+w['startRva']<=target<base+w['endRva'] for w in c['ownedWindows']) and target not in starts:
            raise ValueError(f'resolverScan.direct-call-target-boundary: target={pointer}')
    for table in c['tables']:
        for target,label in zip(table['targets'],table['targetLabels']):
            if base+target not in starts or labels.get(label)!=base+target:
                raise ValueError(f'resolverScan.table-target-boundary: target={target} label={label}')
    if [s['entryRva'] for s in c['indexLeaves']]!=[calls['firstIndexLeaf'],calls['secondIndexLeaf']]:
        raise ValueError('resolverScan.actual-index-leaf-targets')
    leaves=[_index_leaf(index,c,spec) for spec in c['indexLeaves']]
    return {'completeOwnedResolverCodeAndDataPartitionChecked':True,'checkedResolverInstructions':sum(map(len,windows)),
        'checkedIndexLeafInstructions':sum(s['checkedInstructions'] for s in leaves),
        'checkedInstructions':sum(map(len,windows))+sum(s['checkedInstructions'] for s in leaves),
        'ownedBytes':sum(w['endRva']-w['startRva'] for w in c['ownedWindows']),
        'codeBytes':sum(w['endRva']-w['startRva'] for w in c['codeWindows']),
        'tableBytes':sum(t['selectorCount']+4*t['targetCount'] for t in c['tables']),
        'paddingBytes':sum(w['endRva']-w['startRva'] for w in c['paddingWindows']),
        'signedByteTagsAndUnsignedWordRecordCountProved':True,'unsignedDwordParameterCountAndCounterProved':True,
        'allActualDirectAndIndirectTableTargetsChecked':True,'noExecutableEdgeAdmitsTableOrPaddingBytes':True,
        'twoLevelTableOperandsAndZeroExtensionsProved':True,'nestedTagGuardMapping':[_guard_mapping(c,t) for t in c['tables']],
        'indexLeaves':leaves,'actualIndexLeavesPreserveReusedVolatileScanRegisters':True,
        'conditionalPairAddress':'receiver + ((signExtend32((recordOffsetWord + UInt16(selector)) modulo 2^32) + pairBiasUnits) << pairScaleShift), modulo 2^64',
        'zeroResultOnMissingContextOrRecordExhaustionProved':True,'completeNonvolatileAndStackRestorationProved':True,
        'conditions':['valid compatible stable selected receiver, context, records, parameters, carriers, stack and global/header/base storage',
            'preparation, carrier conversion and opaque relation return normally with compatible results and nonvolatile preservation',
            'stable bounded UInt16 record count and UInt32 parameter count; arithmetic itself does not prove valid memory'],
        'namedRuntimeClassInterfaceAndSlotMeaningProved':False,'liveHeaderBaseIdentityOrBoundsProved':False,
        'childEffectsOrInitializationMeaningProved':False,'actualRuntimeTargetSelected':False,'liveCacheContentsProved':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
