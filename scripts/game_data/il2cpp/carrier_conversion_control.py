"""Complete selected anonymous carrier dispatch, reads and tail arguments.

Exact (pinned bytes) conclusions, checked over the complete owned partition:

- the first table maps a byte selector to a DWORD target; the fallback table
  is a directly indexed DWORD;
- a signed input byte and a DWORD decrement limit which selector slots are
  reachable, so the stored array extent does not prove every index is
  selectable;
- forwarded argument widths are either a fixed DWORD, or a payload-derived
  unsigned byte plus a flag that sets only the low byte.

Original-call transfer prefixes without unwind records stay bounded
candidates: absence of unwind ownership is not absence of code. Carrier
meaning and runtime selection are not proved.
"""
from __future__ import annotations
from scripts.game_data.il2cpp.integer_decrement import decode_decrement_instructions
from scripts.game_data.il2cpp.memory_moves import decode_memory_move
from scripts.game_data.il2cpp.owned_partition import (
    BranchGrammar as _Grammar, check_byte_partition, checked_rows, owned_windows, rip_load as _rip_load, window_bytes)

_LABEL='carrierConversion'


def _partition(index,c):
    base=index.pe.image_base;owned,pieces,code=owned_windows(index,c,_LABEL)
    windows=[checked_rows(decode_decrement_instructions(index.mapper,raw,start),raw,_LABEL)
             for category,_w,start,raw in code if category=='codeWindows']
    if [t['kind'] for t in c['tables']]!=['firstTargets','firstSelectors','secondTargets']:
        raise ValueError('carrierConversion.table-kinds')
    first,selectors,second=c['tables']
    if (first['width'],selectors['width'],second['width'])!=(4,1,4):raise ValueError('carrierConversion.table-widths')
    if selectors['count']!=c['layout']['primaryIndexMax']+1 or second['count']!=c['layout']['secondaryIndexMax']+1:
        raise ValueError('carrierConversion.table-index-bounds')
    for t in c['tables']:
        if not 0<t['count']<=256 or len(t['values'])!=t['count'] or t['endRva']-t['startRva']!=t['count']*t['width']:
            raise ValueError('carrierConversion.table-counts')
        raw=window_bytes(index,base+t['startRva'],base+t['endRva'],t['sha256'],_LABEL)
        if raw!=b''.join(n.to_bytes(t['width'],'little') for n in t['values']):raise ValueError('carrierConversion.table-values:'+t['kind'])
        if t['width']==4 and len(t['targetLabels'])!=t['count']:raise ValueError('carrierConversion.target-label-count')
        pieces.append((base+t['startRva'],base+t['endRva'],t['kind']))
    if any(not isinstance(n,int) or not 0<=n<first['count'] for n in selectors['values']):
        raise ValueError('carrierConversion.selector-target-bound')
    check_byte_partition(owned,pieces,_LABEL)
    return windows


def _target_load(g,table,register,index_register):
    row=g.row();raw=bytes.fromhex(row['bytes']);decoded=decode_memory_move(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('target-load','complete indexed memory load',row)
    f=decoded[0]['memoryOperation'];a=f['address']
    if (f['direction'],f['register'],f['registerBits'],f['memoryBytes'],f['upperRegisterEffect'],a['base'],a['index'],a['scale'],a['displacement'])!=('load',register,32,4,'zero upper 32 bits','r8',index_register,4,table['startRva']):
        g.fail('target-load','checked DWORD target with scale four and zero extension',f)


def _indirect(g,register):
    row=g.take(f'jmp {register}')
    expected={'rax':b'\xff\xe0','rcx':b'\xff\xe1'}[register]
    if bytes.fromhex(row['bytes'])!=expected:g.fail('indirect-transfer','full selected register',row)


def _tail(g,target):
    g.take('add rsp, 0x20','pop rbx');row=g.branch('jmp')
    if row['target']!=target:g.fail('actual-tail-target',hex(target),row)


def _globals(g,group,base):
    for spec in group:
        g.mark(spec['label'])
        if g.labels[spec['label']]!=base+spec['entryRva']:g.fail('global-case-entry',spec['entryRva'],g.labels[spec['label']]-base)
        _rip_load(g,'rax',base+spec['globalCellRva']);g.branch('jmp','cachedResult')


def _guard_mapping(c):
    l=c['layout'];first,selectors,second=c['tables'];result=[]
    global_specs=[c['initialGlobal']]+[s for group in c['globalGroups'].values() for s in group]
    globals_={s['label']:s['globalCellRva'] for s in global_specs}
    for raw in range(256):
        signed=raw if raw<128 else raw-256;position=(signed-l['primaryTagBias'])&0xffffffff
        row={'rawByte':raw,'signedValue':signed}
        if l['primaryIntervalStart']<=signed<l['primaryIntervalEndExclusive']:
            row['firstRoute']='interval-to-fallback'
        elif position>l['primaryIndexMax']:row['firstRoute']='unsigned-guard-to-fallback'
        else:
            selected=selectors['values'][position];label=first['targetLabels'][selected]
            row.update(firstRoute='table',firstIndex=position,firstSelector=selected,firstTargetLabel=label,firstTargetRva=first['values'][selected])
            if label in globals_:row.update(globalCellRva=globals_[label],nonnullGlobalRoute='return-unchanged',nullGlobalRoute='fallback')
        if signed==l['fallbackDirectTag']:row['fallbackTargetLabel']='originalTail'
        else:
            secondary=(signed-l['secondaryTagBias'])&0xffffffff
            if secondary>l['secondaryIndexMax']:row['fallbackTargetLabel']='zeroResult'
            else:row.update(secondIndex=secondary,fallbackTargetLabel=second['targetLabels'][secondary],fallbackTargetRva=second['values'][secondary])
        result.append(row)
    return result


def validate_carrier_conversion_control(index,c):
    base=index.pe.image_base;l=c['layout'];calls=c['calls'];first,selectors,second=c['tables']
    if c['initialGlobal']['label']!='initialGlobal' or c['coldGlobal']['label']!='coldGlobal':
        raise ValueError('carrierConversion.global-label-shape')
    windows=_partition(index,c)
    if len(windows)!=2:raise ValueError('carrierConversion.code-window-count')
    primary,cold=windows;g=_Grammar(primary,label='carrierConversion.primary');s=_Grammar(cold,label='carrierConversion.cold')
    g.take('push rbx','sub rsp, 0x20',f'movsx eax, byte [rcx+0x{l["inputTagByte"]:x}]')
    row=g.row();raw=bytes.fromhex(row['bytes']);at=int(row['va'],16)
    target=at+7+int.from_bytes(raw[3:],'little',signed=True) if len(raw)==7 and raw[:3]==b'\x4c\x8d\x05' else None
    if target!=base:g.fail('table-image-base',hex(base),row)
    g.take('mov rbx, rcx',f'cmp eax, 0x{l["primaryIntervalStart"]:x}');g.branch('jl','firstTable')
    g.take(f'cmp eax, 0x{l["primaryIntervalEndExclusive"]:x}');g.branch('jl','fallbackTag')
    g.mark('firstTable');g.take('dec eax',f'cmp eax, 0x{l["primaryIndexMax"]:x}');g.branch('ja','fallbackTag');g.take('cdqe')
    if l['primaryTagBias']!=1:g.fail('decrement-bias',1,l['primaryTagBias'])
    g.take(f'movzx eax, byte [r8+rax*1+0x{selectors["startRva"]:x}]')
    _target_load(g,first,'ecx','rax');g.take('add rcx, r8');_indirect(g,'rcx')
    g.mark('initialGlobal');_rip_load(g,'rax',base+c['initialGlobal']['globalCellRva'])
    if g.labels['initialGlobal']!=base+c['initialGlobal']['entryRva']:g.fail('initial-global-entry',c['initialGlobal']['entryRva'],g.labels['initialGlobal']-base)
    g.mark('cachedResult');g.take('test rax, rax');g.branch('jne','returnFrame')
    g.mark('fallbackTag');g.take(f'movsx eax, byte [rbx+0x{l["inputTagByte"]:x}]',f'cmp eax, 0x{l["fallbackDirectTag"]:x}')
    g.branch('jne','secondTable');g.mark('originalTail');g.take('mov rcx, rbx');_tail(g,base+calls['originalTail'])
    g.mark('returnFrame');g.take('add rsp, 0x20','pop rbx','ret')
    g.mark('secondTable');g.take(f'sub eax, 0x{l["secondaryTagBias"]:x}',f'cmp eax, 0x{l["secondaryIndexMax"]:x}')
    g.branch('ja','zeroResult');g.take('movsxd rcx, eax');_target_load(g,second,'eax','rcx');g.take('add rax, r8');_indirect(g,'rax')
    g.mark('payloadTailA');g.take('mov rcx, [rbx]');_tail(g,base+calls['payloadTailA'])
    _globals(g,c['globalGroups']['early'],base)
    g.mark('recursiveFixedWrapper');g.take('mov rcx, [rbx]');g.call(base+calls['recursive'])
    g.take('xor r8d, r8d',f'mov edx, 0x{l["fixedWrapperDword"]:x}','mov rcx, rax');_tail(g,base+calls['wrapperTail'])
    if l['fixedWrapperFlagDword']!=0:g.fail('fixed-wrapper-flag',0,l['fixedWrapperFlagDword'])
    _globals(g,c['globalGroups']['middle'],base)
    g.mark('payloadTailB');g.take('mov rcx, [rbx]');_tail(g,base+calls['payloadTailB'])
    _globals(g,c['globalGroups']['late'],base)
    g.mark('payloadTailC');g.take('mov rcx, [rbx]');_tail(g,base+calls['payloadTailC'])
    _globals(g,c['globalGroups']['last'],base)
    g.mark('recursiveStoredWrapper');g.take('mov rcx, [rbx]','mov rcx, [rcx]');g.call(base+calls['recursive'])
    g.take('mov rcx, rax',f'mov r8b, 0x{l["storedWrapperFlagByte"]:x}','mov rax, [rbx]',f'movzx edx, byte [rax+0x{l["storedWrapperByte"]:x}]')
    _tail(g,base+calls['wrapperTail'])
    s.mark('coldGlobal');_rip_load(s,'rax',base+c['coldGlobal']['globalCellRva']);s.branch('jmp','returnFrame')
    if s.labels['coldGlobal']!=base+c['coldGlobal']['entryRva']:s.fail('cold-global-entry',c['coldGlobal']['entryRva'],s.labels['coldGlobal']-base)
    s.mark('zeroResult');s.take('xor eax, eax');s.branch('jmp','returnFrame')
    labels={**g.labels,**s.labels};starts={int(r['va'],16) for rows in windows for r in rows}
    if not set(labels.values())<=starts:raise ValueError('carrierConversion.label-instruction-boundary')
    g.labels.update(labels);s.labels.update(labels);g.finish();s.finish()
    for table in (first,second):
        for target,label in zip(table['values'],table['targetLabels']):
            if base+target not in starts or labels.get(label)!=base+target:
                raise ValueError(f'carrierConversion.table-target-boundary: target={target} label={label}')
    if calls['recursive']!=c['entryRva']:raise ValueError('carrierConversion.actual-recursive-target')
    for pointer in calls.values():
        target=base+pointer
        if any(base+w['startRva']<=target<base+w['endRva'] for w in c['ownedWindows']) and target not in starts:
            raise ValueError('carrierConversion.direct-target-boundary')
    return {'completeOwnedCarrierCodeAndDataPartitionChecked':True,'checkedInstructions':sum(map(len,windows)),
        'ownedBytes':sum(w['endRva']-w['startRva'] for w in c['ownedWindows']),
        'codeBytes':sum(w['endRva']-w['startRva'] for w in c['codeWindows']),
        'tableBytes':sum(t['endRva']-t['startRva'] for t in c['tables']),
        'paddingBytes':sum(w['endRva']-w['startRva'] for w in c['paddingWindows']),
        'defaultDwordDecrementAndSignedTagReadsProved':True,'allActualDirectRecursiveAndTableTargetsChecked':True,
        'noExecutableEdgeAdmitsTableOrPaddingBytes':True,'tagGuardAndConditionalRoutes':_guard_mapping(c),
        'nonnullGlobalReturnedUnchangedAndZeroGlobalFallsBackProved':True,
        'originalInputAndDereferencedPayloadTailArgumentsProved':True,
        'recursiveOriginalInputFlagBytePreservedBeforeSelfCall':True,
        'recursiveResultAndFixedDwordWrapperArgumentsProved':True,
        'recursiveResultAndStoredUnsignedByteWrapperArgumentsProved':True,
        'storedWrapperFlagSetsOnlyR8LowByte':True,'ownedBodyHasNoInlineGlobalOrPayloadWrites':True,
        'completeStackAndNonvolatileRestorationProved':True,
        'conditions':['valid compatible stable selected input, payload and globals with disjoint stack storage',
            'normal compatible recursive/tail child returns and nonvolatile preservation; recursive termination is not established'],
        'namedTypeClassMeaningProved':False,'liveGlobalInitializationOrValuesProved':False,
        'childAllocationConversionOrCacheEffectsProved':False,'recursiveTerminationProved':False,
        'opaqueRelationMeaningProved':False,'actualRuntimeTargetSelected':False,
        'actualArrayCallbackTargetProved':False,'callbackCursorEqualityProved':False,'positiveListAdmitted':False,'wholeRootAdmitted':False}
