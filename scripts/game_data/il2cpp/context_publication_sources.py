"""Prove selected interface-array and ordinary method-pair publication programs.

These are conditional physical writes from the current complete setup CFG.
Runtime metadata/class identity, child return meaning, allocation capacity,
concurrent visibility and execution are deliberately separate open claims.
"""
from __future__ import annotations
import struct
from .class_creation_control import _prefix, _dominators
from .class_dispatch_sources import (
    metadata_dispatch_count_columns, prove_creation_dispatch_sources,
    _preserved, _overlaps,
)
from .context_setup_control import _rows, _graph, _frame, _load_byte, _cmp_zero, _origins
from .field_setup_control import _graph as creation_graph, _frames
from .integer_widths import decode_word_zero_extension
from .memory_moves import decode_memory_move
from .owned_partition import BranchGrammar, rip_load
from .relation_import_control import _memory

LABEL = 'contextPublicationSources'


def metadata_publication_columns(catalog, metadata):
    columns = metadata_dispatch_count_columns(catalog, metadata)
    section = metadata.sections['typeDefinitions']; stride = columns['recordBytes']
    if not 0 <= section.offset <= len(metadata.buf)-section.size:
        raise ValueError(LABEL+'.stored-type-section-boundary')
    for name, width in (('vtableMethods',4),('interfaceOffsets',8)):
        selected = metadata.sections[name]
        if selected.size < 0 or selected.size % width or not 0 <= selected.offset <= len(metadata.buf)-selected.size:
            raise ValueError(LABEL+'.stored-table-section-boundary:'+name)
    layout = None
    for ordinal, td in enumerate(metadata.types):
        start = section.offset+ordinal*stride
        prefix = catalog.parse_type_reference_prefix(metadata.buf, start, stride)
        tail = catalog.parse_type_layout_tail(metadata.buf, prefix[-1], stride)
        selected = {'vtableStartDwordOffset': prefix[-1]-start+4+6*4,
            'interfaceOffsetsStartDwordOffset': prefix[-1]-start+4+7*4}
        if layout is not None and selected != layout:
            raise ValueError(LABEL+'.metadata-start-offset-drift')
        layout = selected
        values = tuple(struct.unpack_from('<i', metadata.buf, start+selected[k])[0]
            for k in ('vtableStartDwordOffset', 'interfaceOffsetsStartDwordOffset'))
        if values != (tail[1][6], tail[1][7]) or values != (td.vtable_start, td.interface_offsets_start):
            raise ValueError(LABEL+'.named-metadata-range-start')
        for key, first, count, width in (
            ('vtableMethods', td.vtable_start, td.vtable_count, 4),
            ('interfaceOffsets', td.interface_offsets_start, td.interface_offsets_count, 8)):
            selected_section = metadata.sections[key]
            if selected_section.size % width or count and not 0 <= first <= selected_section.size//width-count:
                raise ValueError(LABEL+'.stored-metadata-range:'+key)
    header = {}
    for name in ('vtableMethods', 'interfaceOffsets'):
        at = 8+list(metadata.sections).index(name)*8
        value = struct.unpack_from('<i', metadata.buf, at)[0]
        selected_section = metadata.sections[name]
        if value != selected_section.offset or not 0 <= value < 1 << 31:
            raise ValueError(LABEL+'.signed-header-offset:'+name)
        header[name] = {'offsetField': at, 'storedOffset': value,
            'storedBytes': selected_section.size,
            'recordBytes': 4 if name == 'vtableMethods' else 8}
    return {**columns, **layout, 'headerSections': header,
        'allStoredTypeRangeStartsAndBoundsChecked': True,
        'actualRuntimeHeaderBaseOrRecordIdentityProved': False}


def _move(g, direction, register, size, receiver, offset=0, index=None, scale=1):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_memory_move(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw): g.fail('memory-encoding', 'complete GP move', row)
    f = decoded[0]['memoryOperation']; a = f['address']
    if (f['direction'], f['register'], f['memoryBytes'], a['base'], a['index'], a['scale'],
        a['displacement'], a['ripRelative'], a['addressBits']) != (
        direction, register, size, receiver, index, scale, offset, False, 64):
        g.fail('memory-operands', (direction, register, size, receiver, index, scale, offset), f)
    return row


def _word(g, destination, *, receiver=None, offset=0, source=None):
    row = g.row(); raw = bytes.fromhex(row['bytes'])
    decoded = decode_word_zero_extension(raw, 0, int(row['va'], 16))
    if decoded is None or decoded[1] != len(raw): g.fail('unsigned-word-encoding', 'complete MOVZX word', row)
    f = decoded[0]['wordZeroExtensionOperation']; a = f['sourceAddress'] or {}
    if (f['destinationRegister'], f['destinationBits'], f['sourceRegister'], f['sourceBits'],
        f['memoryReadBytes'], a.get('base'), a.get('index'), a.get('displacement')) != (
        destination, 32, source, 16, 0 if source else 2, receiver, None, None if source else offset):
        g.fail('unsigned-word-operands', (destination, receiver, offset, source), f)
    return row


def prove_creation_publication_sources(rows, base, creation, layout, columns):
    inherited = prove_creation_dispatch_sources(rows, base, creation,
        layout['selfPointer'], layout['interfaceCount'], columns)
    f = creation['function']; edges, _, stores = creation_graph(rows, base, f)
    _frames(rows, edges, base, f); allocation = _prefix(rows, base, creation, f)
    dom = _dominators(edges, base+f['entryRva']); by_at = {int(r['va'],16): i for i,r in enumerate(rows)}
    found = {}
    for name, offset, size, register in (
        ('metadataRecordPointer', layout['metadataRecordPointer'], 8, 'rdi'),
        ('vtableCount', layout['vtableCount'], 2, 'ax')):
        candidates = _overlaps(stores, {'rax', 'rbx'}, offset, size)
        if len(candidates) != 1: raise ValueError(LABEL+'.unique-creation-source-store:'+name)
        at = base+candidates[0]; n = by_at[at]
        g = BranchGrammar(rows[n:n+1], label=LABEL+'.creation.'+name)
        _move(g, 'store', register, size, 'rbx', offset); g.finish()
        if name == 'vtableCount':
            load = rows[n-1]; load_at = int(load['va'],16)
            if load_at+len(bytes.fromhex(load['bytes'])) != at: raise ValueError(LABEL+'.adjacent-count-source')
            g = BranchGrammar([load], label=LABEL+'.creationCount')
            _word(g, 'eax', receiver='rdi', offset=columns['vtableCountWordOffset']); g.finish()
            if load_at not in dom[at]: raise ValueError(LABEL+'.count-source-dominance')
        else: load_at = at
        bound = base+f['sourceAllocationPrefix']['window']['endRva']
        _preserved(rows, bound, at, {'rdi', 'rbx'})
        if allocation not in dom[load_at] or any(at not in dom[base+r] for r in f['returnRvas']):
            raise ValueError(LABEL+'.creation-source-normal-return-dominance')
        found[name] = {'storeRva': at-base, 'allocationByteOffset': offset,
            'source': 'saved current metadata record pointer RDI' if name == 'metadataRecordPointer' else 'current named metadata vtable_count WORD',
            **({'loadRva': load_at-base, 'sourceRecordWordOffset': columns['vtableCountWordOffset']} if name == 'vtableCount' else {}),
            'directStoreUnique': True, 'dominatesEveryNormalLocalReturn': True,
            'unchangedByChildrenAliasesOrConcurrentWritesProved': False}
    return {'inheritedDispatchSources': inherited, **found,
        'actualRuntimeMetadataClassOrPreparedPointerIdentityProved': False}


def _fragment(rows, base, declaration, edges, label):
    a, b = (base+declaration[k] for k in ('startRva', 'endRva'))
    selected = [r for r in rows if a <= int(r['va'],16) < b]
    if not selected or int(selected[0]['va'],16) != a or int(selected[-1]['va'],16)+len(bytes.fromhex(selected[-1]['bytes'])) != b:
        raise ValueError(LABEL+'.fragment-boundary:'+label)
    starts = {int(r['va'],16) for r in selected}
    entries={base+r for r in declaration.get('entryRvas',[declaration['startRva']])}
    if a not in entries or not entries <= starts:
        raise ValueError(LABEL+'.fragment-entry-boundary:'+label)
    if any(target not in entries for at, targets in edges.items() if at not in starts for target in targets & starts):
        raise ValueError(LABEL+'.external-entry-into-fragment-interior:'+label)
    return BranchGrammar(selected, label=LABEL+'.'+label)


def _labels(g, base, spec):
    g.labels.update({k: base+v for k,v in spec.items()})


def _lea(g, register, receiver, offset=0, *, absolute=None):
    from .integer_addressing import decode_lea_address
    row=g.row();raw=bytes.fromhex(row['bytes'])
    decoded=decode_lea_address(raw,0,int(row['va'],16))
    if decoded is None or decoded[1]!=len(raw):g.fail('lea-encoding','complete LEA',row)
    f=decoded[0]['addressOperation']
    if (f['destination'],f['destinationBits'])!=(register,64):g.fail('lea-destination',register,f)
    if absolute is not None:
        valid=f['ripRelative'] and f.get('absoluteAddress')==absolute
    else:valid=not f['ripRelative'] and (f['base'],f['index'],f['displacement'],f['addressBits'])==(receiver,None,offset,64)
    if not valid:g.fail('lea-address',(receiver,offset,absolute),f)
    return row


def _pair_target(g, c, counter, *, value='rcx', index='rax'):
    l=c['layout'];_word(g,'eax' if index=='rax' else 'ecx',source=counter)
    g.take(f'add {index}, 0x{l["pairBias"]:x}',f'add {index}, {index}')
    return _move(g,'store',value,8,'rdi',index=index,scale=8)


def _linked_methods(g, base, c, function):
    p=c['program'];l=c['layout'];m=p['linkedMethods'];calls=p['calls'];glob=p['globals']
    home=function['addressHandoff']['currentHomeOffset'];bp_home=function['addressHandoff']['saveRbpOffset']
    _memory(g,'load','rbx',8,base='rsp',displacement=home)
    g.take(f'cmp word [r14+0x{l["vtableCount"]:x}], si');g.branch('jbe','linkedRestore')
    g.take('mov rdx, rbx');_memory(g,'store','rbp',8,base='rsp',displacement=bp_home)
    g.take('mov rcx, r14');recursive=g.call(base+p['entryRva'])
    _word(g,'eax',receiver='r14',offset=l['vtableCount']);_word(g,'ebp',source='si')
    count_store=_move(g,'store','ax',2,'rdi',l['vtableCount'])
    g.take(f'cmp si, word [r14+0x{l["vtableCount"]:x}]');g.branch('jae','afterLinkedMethods')
    for reg,key in (('r15','fallbackTargetAddressRva'),('r13','fallbackSecondWordAddressRva')):
        _lea(g,reg,None,absolute=base+glob[key])
    g.take('nop');g.mark('linkedMethodLoop')
    _move(g,'load','rax',8,'r14',l['metadataRecordPointer']);_word(g,'ecx',source='bp')
    _move(g,'load','edx',4,'rax',c['metadataColumns']['vtableStartDwordOffset'])
    rip_load(g,'rax',base+glob['headerPointerCellRva']);g.take('add edx, ecx',
        f'movsxd rcx, dword [rax+0x{c["metadataColumns"]["headerSections"]["vtableMethods"]["offsetField"]:x}]',
        f'add rcx, qword [rip => 0x{base+glob["metadataBaseCellRva"]:x}]')
    _move(g,'load','ecx',4,'rcx',index='rdx',scale=4);lookup=g.call(base+calls['methodLookup'])
    g.take('mov rbx, rax','test rax, rax');g.branch('je','publishLinkedMethod')
    g.take(f'cmp [rax+0x{m["methodClassPointer"]:x}], rsi');g.branch('je','publishLinkedMethod')
    g.take(f'test byte [rax+0x{p["methodFlagByte"]:x}], 0x{p["methodAlternateMask"]:x}');g.branch('je','afterCarrierInflation')
    _move(g,'load','rcx',8,'rax',m['methodCarrierPointer']);_lea(g,'rdx','r12',p['inflationContextOffset'])
    inflate=g.call(base+calls['methodCarrierInflate']);g.take('xor edx, edx','mov rcx, rax')
    carrier=g.call(base+calls['methodCarrierLookup']);g.take('mov rbx, rax','test rax, rax');g.branch('je','publishLinkedMethod')
    g.mark('afterCarrierInflation');g.take(f'cmp [rbx+0x{m["methodClassPointer"]:x}], rsi');g.branch('je','publishLinkedMethod')
    _move(g,'load','rax',8,'rbx',m['methodClassPointer'])
    g.take(f'test byte [rax+0x{m["classTupleFlagByte"]:x}], 0x{m["classTupleFlagMask"]:x}');g.branch('je','publishLinkedMethod')
    _move(g,'load','rax',8,'r12',p['inflationContextOffset']);_lea(g,'rcx','rsp',m['tupleHomeOffset'])
    g.take('mov dl, 0x1');_memory(g,'store','rax',8,base='rsp',displacement=m['tupleHomeOffset']+8)
    _memory(g,'store','rbx',8,base='rsp',displacement=m['tupleHomeOffset'])
    _memory(g,'store','rsi',8,base='rsp',displacement=m['tupleHomeOffset']+16)
    tuple_lookup=g.call(base+calls['methodCarrierLookup']);g.take('mov rbx, rax')
    g.mark('publishLinkedMethod');_word(g,'eax',source='bp');g.take('add rax, rax')
    second_word=_move(g,'store','rbx',8,'rdi',l['pairBias']*l['pairStride']+8,index='rax',scale=8)
    g.take('test rbx, rbx');g.branch('je','nullLinkedMethod')
    g.take(f'cmp [rbx+0x{m["methodClassPointer"]:x}], rsi');g.branch('je','linkedTargetSelection')
    g.take(f'cmp [rbx+0x{m["methodClassPointer"]:x}], rdi');g.branch('je','linkedTargetSelection')
    g.take('cmp [rbx], rsi');g.branch('je','linkedTargetSelection')
    _move(g,'load','rax',8,'rbx',m['methodClassPointer'])
    g.take(f'test byte [rax+0x{m["classPrepareFlagByte"]:x}], 0x{m["classPrepareFlagMask"]:x}');g.branch('jne','linkedPrepareCandidate')
    for ordinal,kind in enumerate(m['classPrepareKinds']):
        g.take(f'cmp byte [rax+0x{m["classKindByte"]:x}], 0x{kind:x}')
        g.branch('je' if ordinal==0 else 'jne','linkedPrepareCandidate' if ordinal==0 else 'linkedTargetSelection')
    g.mark('linkedPrepareCandidate');g.take(f'cmp [rax+0x{l["linkedPointer"]:x}], rsi');g.branch('je','linkedTargetSelection')
    g.take(f'test byte [rax+0x{m["classPreparedFlagByte"]:x}], 0x{m["classPreparedFlagMask"]:x}');g.branch('jne','linkedTargetSelection')
    _memory(g,'load','rdx',8,base='rsp',displacement=home);g.take('mov rcx, rax')
    address_call=g.call(base+calls['incomingAddress'])
    g.mark('linkedTargetSelection');_load_byte(g,'eax','rbx',p['methodFlagByte'])
    g.take(f'and al, 0x{p["methodAlternateMask"]:x}',f'cmp [rbx+0x{p["methodDirectTargetOffset"]:x}], rsi');g.branch('je','missingLinkedTarget')
    g.take('test al, al');g.branch('je','directLinkedTarget')
    g.take(f'cmp [rip+0x{base+glob["alternateTargetGateCellRva"]-(int(g.rows[g.cursor]["va"],16)+len(bytes.fromhex(g.rows[g.cursor]["bytes"]))):x} => 0x{base+glob["alternateTargetGateCellRva"]:x}], rsi');g.branch('je','directLinkedTarget')
    targets=[]
    for label,offset in ((None,p['methodAlternateTargetOffset']),('directLinkedTarget',p['methodDirectTargetOffset'])):
        if label:g.mark(label)
        _move(g,'load','rcx',8,'rbx',offset);targets.append(_pair_target(g,c,'bp'));g.branch('jmp','incrementLinkedMethod')
    g.mark('missingLinkedTarget');g.take('test al, al');g.branch('je','fallbackLinkedTarget')
    g.take(f'test byte [rbx+0x{p["methodFlagByte"]:x}], 0x{m["methodMissingTargetExcludedMask"]:x}');g.branch('jne','fallbackLinkedTarget')
    _move(g,'load','rax',8,'rbx',m['methodCarrierPointer'])
    g.take(f'cmp [rax+0x{m["carrierExclusionPointer"]:x}], rsi');g.branch('jne','fallbackLinkedTarget')
    g.take('mov rcx, rbx');missing_call=g.call(base+calls['missingMethodTarget'])
    targets.append(_pair_target(g,c,'bp',value='rax',index='rcx'));g.branch('jmp','incrementLinkedMethod')
    g.mark('nullLinkedMethod');_word(g,'eax',source='bp');g.take('add rax, rax')
    _move(g,'store','r13',8,'rdi',l['pairBias']*l['pairStride']+8,index='rax',scale=8)
    g.mark('fallbackLinkedTarget');targets.append(_pair_target(g,c,'bp',value='r15'))
    g.mark('incrementLinkedMethod');g.take('inc bp',f'cmp bp, word [r14+0x{l["vtableCount"]:x}]');g.branch('jb','linkedMethodLoop')
    g.mark('afterLinkedMethods');g.take(f'cmp dword [rdi+0x{l["selectorDword"]:x}], {m["selectorSentinel"]:#x}')
    _memory(g,'load','rbp',8,base='rsp',displacement=bp_home);g.branch('jne','linkedRestore')
    _move(g,'load','rax',8,'rdi',l['linkedPointer']);_move(g,'load','rbx',8,'rax',m['selectorLinkedArgumentOffset'])
    g.take('mov rcx, rbx');repair_first=g.call(base+calls['selectorRepairFirst'])
    g.take('test rax, rax');g.branch('je','linkedRestore');g.take('cmp rax, rbx');g.branch('je','linkedRestore')
    _lea(g,'rcx','r14',m['selectorRepairContextOffset']);g.take('mov rdx, rax')
    repair_second=g.call(base+calls['selectorRepairSecond']);g.take('test rax, rax');g.branch('je','linkedRestore')
    _move(g,'load','rax',8,'rax',m['selectorRepairNestedPointer']);g.take('test rax, rax');g.branch('je','linkedRestore')
    _move(g,'load','eax',4,'rax',l['selectorDword']);selector_store=_move(g,'store','eax',4,'rdi',l['selectorDword'])
    g.mark('linkedRestore')
    for reg,off in p['linkedSavedHomes'].items():_memory(g,'load',reg,8,base='rsp',displacement=off)
    g.finish()
    return {'recursiveCallRva':int(recursive['va'],16)-base,'freshSourceVtableCountStoreRva':int(count_store['va'],16)-base,
        'methodLookupCallRva':int(lookup['va'],16)-base,'carrierInflationCallRva':int(inflate['va'],16)-base,
        'carrierLookupCallRvas':[int(r['va'],16)-base for r in (carrier,tuple_lookup)],
        'stackTupleBytes':24,'stackTupleSources':['saved candidate QWORD','fresh linked-context QWORD','zero QWORD'],
        'tupleLookupFlagIsLowDlOnly':True,'upperRdxValueForTupleCallProved':False,
        'freshCandidateSecondWordStoreRva':int(second_word['va'],16)-base,
        'incomingAddressCallRva':int(address_call['va'],16)-base,
        'targetQwordStoreRvas':[int(r['va'],16)-base for r in targets],
        'missingTargetHelperCallRva':int(missing_call['va'],16)-base,
        'allCandidateRewriteTargetAndFallbackBranchesChecked':True,
        'counterBits':16,'maximumNormalLoopIterations':65535,'counterWrapOnContinuingPathExcluded':True,
        'selectorRepair':{'initialSentinel':m['selectorSentinel'],'allocationDwordByteOffset':l['selectorDword'],
            'helperCallRvas':[int(r['va'],16)-base for r in (repair_first,repair_second)],
            'storeRva':int(selector_store['va'],16)-base,'nestedPointerByteOffset':m['selectorRepairNestedPointer'],
            'actualConditionalPostCreationSelectorWriteProved':True,'runtimeSelectorOrNestedClassIdentityProved':False},
        'childReturnIdentitiesEffectsOrTerminationProved':False,'actualStorageCapacityOrVisibilityProved':False}


def _special(g, base, c):
    p=c['program'];l=c['layout'];s=p['special'];calls=p['calls']
    _move(g,'load','rcx',8,'rcx',s['receiverSourcePointer']);incoming=g.call(base+calls['incomingAddress'])
    _move(g,'load','rbx',8,'rdi',s['receiverSourcePointer']);g.take('mov rcx, rbx')
    lookup=g.call(base+calls['specialLookup']);_lea(g,'rcx','rbx',s['sourceTypeAddressOffset'])
    stored=_move(g,'store','rax',8,'rdi',s['receiverLookupResult']);g.take('test rcx, rcx');g.branch('je','sourceSpecialFlag')
    for kind in s['directSetKinds']:
        g.take(f'cmp byte [rcx+0x{s["sourceTypeKindByte"]:x}], 0x{kind:x}');g.branch('je','setSpecialBit')
    g.take(f'cmp byte [rcx+0x{s["sourceTypeKindByte"]:x}], 0x{s["queryKind"]:x}');g.branch('jne','sourceSpecialFlag')
    _move(g,'load','rcx',8,'rcx');query=g.call(base+calls['linkedLookup'])
    _move(g,'load','ecx',4,'rax',s['queryDwordOffset']);g.take(f'shr ecx, 0x{s["queryShift"]:x}','test cl, cl');g.branch('je','setSpecialBit')
    g.mark('sourceSpecialFlag');g.take(f'test byte [rbx+0x{s["flagByte"]:x}], 0x{s["flagMask"]:x}');g.branch('jne','setSpecialBit')
    g.mark('clearSpecialBit');g.take('xor cl, cl');g.branch('jmp','mergeSpecialBit')
    g.mark('setSpecialBit');g.take(f'mov cl, 0x{s["flagMask"]:x}')
    g.mark('mergeSpecialBit');_load_byte(g,'eax','rdi',s['flagByte'])
    g.take(f'and al, 0x{255^s["flagMask"]:x}','or al, cl','mov rcx, rdi')
    flag_store=_move(g,'store','al',1,'rdi',s['flagByte']);first=g.call(base+calls['specialFirst'])
    g.take('mov rcx, rdi');second=g.call(base+calls['specialSecond']);g.branch('jmp','flagUpdate');g.finish()
    return {'incomingAddressCallRva':int(incoming['va'],16)-base,
        'initialPointerAndPostHelperPointerEqualityProved':False,
        'lookupCallRva':int(lookup['va'],16)-base,'freshLookupResultQwordStoreRva':int(stored['va'],16)-base,
        'storedQwordByteOffset':s['receiverLookupResult'],'typeQueryCallRva':int(query['va'],16)-base,
        'typeAddressAdditionWrapsModulo64':True,'directSetKinds':s['directSetKinds'],'queryKind':s['queryKind'],
        'queryPredicate':'direct kind or selected query result DWORD high bit clear selects set; other paths mirror the fresh source flag bit',
        'flagByteOffset':s['flagByte'],'flagMask':s['flagMask'],'flagStoreRva':int(flag_store['va'],16)-base,
        'selectedFlagBitReplacedAndOtherBitsPreserved':True,
        'postFlagChildCallRvas':[int(r['va'],16)-base for r in (first,second)],
        'postFlagChildReceiverIsOriginalRdiProved':True,
        'incomingSlotContentsOrChildEffectsAndIdentitiesProved':False}


def _interface_record(g, base, c, *, linked):
    p=c['program']; l=c['layout']; col=c['metadataColumns']; glob=p['globals']; calls=p['calls']
    receiver='r14' if linked else 'rdi'
    _move(g,'load','rax',8,receiver,l['metadataRecordPointer'])
    _word(g,'r8d',source='bx')
    g.take(f'add r8d, dword [rax+0x{col["interfaceOffsetsStartDwordOffset"]:x}]')
    rip_load(g,'rax',base+glob['headerPointerCellRva'])
    g.take(f'movsxd r9, dword [rax+0x{col["headerSections"]["interfaceOffsets"]["offsetField"]:x}]',
        f'add r9, qword [rip => 0x{base+glob["metadataBaseCellRva"]:x}]', 'movsxd rax, r8d',
        'movsxd rcx, dword [r9+rax*8]', f'cmp ecx, {p["interfaceNullIndex"]:#x}')
    g.branch('jne','registeredInterface');g.take('mov rcx, rsi');g.branch('jmp','interfaceArgument')
    g.mark('registeredInterface');rip_load(g,'rax',base+glob['registrationCellRva'])
    g.take('mov rdx, rcx');_move(g,'load','rcx',8,'rax',p['registrationTypesOffset'])
    _move(g,'load','rcx',8,'rcx',index='rdx',scale=8)
    g.mark('interfaceArgument');g.take('movsxd rax, r8d');_word(g,'edx',source='bx')
    g.take('add rdx, rdx');_move(g,'load','r8d',4,'r9',4,index='rax',scale=8)
    _move(g,'load','rax',8,'rdi',l['interfaceArray'])
    offset_store=_move(g,'store','r8d',4,'rax',l['recordOffsetDword'],index='rdx',scale=8)
    if linked:
        g.take('xor r8d, r8d',f'lea rdx, [r12+0x{p["inflationContextOffset"]:x}]')
        g.call(base+calls['inflate'])
        g.take('mov rcx, rax')
    g.take(f'mov dl, 0x{p["typeLookupFlag"]:x}'); lookup=g.call(base+calls['typeLookup'])
    _move(g,'load','rcx',8,'rdi',l['interfaceArray']);_word(g,'edx',source='bx')
    g.take('inc bx','add rdx, rdx');pointer_store=_move(g,'store','rax',8,'rcx',index='rdx',scale=8)
    g.take(f'cmp bx, word [{receiver}+0x{l["interfaceCount"]:x}]');g.branch('jb','interfaceLoop')
    return {'offsetDwordStoreRva':int(offset_store['va'],16)-base,
        'freshTypeLookupReturnQwordStoreRva':int(pointer_store['va'],16)-base,
        'typeLookupCallRva':int(lookup['va'],16)-base,
        'recordBytes':l['recordStride'], 'offsetDwordByteOffset':l['recordOffsetDword'],
        'sourceRecordIndexExpression':'sign_extend_64((zero_extend_32(BX) + fresh stored interface_offsets_start DWORD) modulo 2^32)',
        'counterBits':16,'continuationPredicate':'unsigned incremented BX < fresh count WORD',
        'maximumNormalLoopIterations':65535,'counterWrapOnContinuingPathExcluded':True,
        'registeredTypeOrClassReturnIdentityProved':False,'requestedCapacitySufficesForFreshLoopCountsProved':False}


def validate_context_publication_program(index, context, c):
    base=index.pe.image_base;p=c['program'];l=c['layout']
    f=next(f for f in context['functions'] if f['role']=='second')
    if f['entryRva']!=p['entryRva'] or l['recordStride']!=16 or l['recordOffsetDword']!=8 or l['pairBias']!=20 or l['pairStride']!=16:
        raise ValueError(LABEL+'.selected-program-or-geometry')
    rows=_rows(index,f); ranges=[(w['startRva'],w['endRva']) for w in f['ownedWindows']]
    edges,complete=_graph(rows,base,f,ranges,{f['entryRva']});_frame(rows,edges,base,f)
    required={'prefix','selector','linkedArray','ordinary','flags','linkedMethods','special','restore'}
    if set(p['windows'])!=required:raise ValueError(LABEL+'.complete-semantic-fragment-set')
    linked_rows=[r for r in rows if base+p['windows']['linkedMethods']['startRva']<=int(r['va'],16)<base+p['windows']['linkedMethods']['endRva']]
    expected_labels={name:p['windows'][role]['startRva'] for name,role in (
        ('restore','restore'),('ordinarySelector','selector'),('ordinary','ordinary'),
        ('linkedArrayDone','linkedMethods'),('flagUpdate','flags'))}
    if len(linked_rows)<2:raise ValueError(LABEL+'.linked-method-entry-inventory')
    expected_labels['linkedArraySkip']=int(linked_rows[1]['va'],16)-base
    if p['labels']!=expected_labels:raise ValueError(LABEL+'.actual-semantic-fragment-label-joins')
    for name,w in p['windows'].items():
        expected=[w['startRva']]+([expected_labels['linkedArraySkip']] if name=='linkedMethods' else [])
        if w.get('entryRvas',[w['startRva']])!=expected:
            raise ValueError(LABEL+'.unproved-semantic-fragment-entry:'+name)
    covered=[int(r['va'],16) for w in p['windows'].values() for r in rows
        if base+w['startRva']<=int(r['va'],16)<base+w['endRva']]
    if sorted(covered)!=[int(r['va'],16) for r in rows]:
        raise ValueError(LABEL+'.complete-semantic-fragment-partition')
    restore_pop = base+f['addressHandoff']['restoreRva']+4
    if next(r for r in rows if int(r['va'],16)==restore_pop)['text'] != 'pop rdi':
        raise ValueError(LABEL+'.receiver-restore-pop')
    preserved_rows=[r for r in rows if int(r['va'],16)!=restore_pop]
    _preserved(preserved_rows,base+p['windows']['prefix']['endRva'],base+p['windows']['ordinary']['endRva'],{'rdi'})
    g=_fragment(rows,base,p['windows']['prefix'],edges,'prefix');_labels(g,base,p['labels'])
    _memory(g,'store','rdx',8,base='rsp',displacement=f['addressHandoff']['entryHomeOffset'])
    g.take('push rbx','push rdi',f'sub rsp, 0x{f["addressHandoff"]["frameBytes"]:x}')
    _load_byte(g,'eax','rcx',f['addressHandoff']['flagByte'])
    g.take('mov rbx, rdx','mov rdi, rcx',f'test al, 0x{f["addressHandoff"]["readyMask"]:x}');g.branch('jne','restore')
    g.take(f'test byte [rcx+0x{f["addressHandoff"]["blockedFlagByte"]:x}], 0x{f["addressHandoff"]["blockedMask"]:x}');g.branch('jne','restore')
    _cmp_zero(g,'rcx',l['linkedPointer'])
    for reg,off in p['savedHomes'].items():_memory(g,'store',reg,8,base='rsp',displacement=off)
    g.branch('je','ordinarySelector');g.finish()
    g=_fragment(rows,base,p['windows']['selector'],edges,'ordinarySelector');_labels(g,base,p['labels'])
    g.take(f'cmp byte [rcx+0x{l["specialByte"]:x}], 0x0');g.branch('je','ordinary');g.finish()
    g=_fragment(rows,base,p['windows']['linkedArray'],edges,'linkedArray');_labels(g,base,p['labels'])
    _move(g,'load','rcx',8,'rcx',l['linkedPointer'])
    for reg,off in p['linkedSavedHomes'].items():_memory(g,'store',reg,8,base='rsp',displacement=off)
    g.call(base+p['calls']['linkedLookup']);_move(g,'load','r12',8,'rdi',l['linkedPointer'])
    g.take('xor esi, esi','mov r14, rax',f'cmp word [rax+0x{l["interfaceCount"]:x}], si');g.branch('jbe','linkedArraySkip')
    g.take(f'cmp [rdi+0x{l["interfaceArray"]:x}], rsi');g.branch('jne','linkedArraySkip')
    _word(g,'ecx',receiver='rax',offset=l['interfaceCount']);g.take('mov r8d, 0x10')
    _move(g,'store','cx',2,'rdi',l['interfaceCount']);_word(g,'edx',receiver='rax',offset=l['interfaceCount'])
    rip_load(g,'rcx',base+p['globals']['allocatorContextCellRva']);g.call(base+p['calls']['allocation'])
    linked_publication=_move(g,'store','rax',8,'rdi',l['interfaceArray']);_word(g,'ebx',source='si')
    g.take(f'cmp si, word [r14+0x{l["interfaceCount"]:x}]');g.branch('jae','linkedArrayDone');g.take('nop')
    g.mark('interfaceLoop');linked=_interface_record(g,base,c,linked=True);g.finish()
    g=_fragment(rows,base,p['windows']['ordinary'],edges,'ordinary');_labels(g,base,p['labels'])
    g.take('xor esi, esi',f'cmp word [rcx+0x{l["interfaceCount"]:x}], si');g.branch('jbe','afterInterfaceArray')
    g.take(f'cmp [rcx+0x{l["interfaceArray"]:x}], rsi');g.branch('jne','afterInterfaceArray')
    _word(g,'edx',receiver='rcx',offset=l['interfaceCount']);g.take('mov r8d, 0x10')
    rip_load(g,'rcx',base+p['globals']['allocatorContextCellRva']);g.call(base+p['calls']['allocation'])
    _word(g,'ebx',source='si');ordinary_publication=_move(g,'store','rax',8,'rdi',l['interfaceArray'])
    g.take(f'cmp si, word [rdi+0x{l["interfaceCount"]:x}]');g.branch('jae','afterInterfaceArray');g.take('nop')
    g.mark('interfaceLoop');ordinary=_interface_record(g,base,c,linked=False)
    g.mark('afterInterfaceArray');g.take(f'cmp word [rdi+0x{l["vtableCount"]:x}], si');g.branch('jbe','flagUpdate')
    for reg,key in (('r15','fallbackTargetAddressRva'),('r13','fallbackSecondWordAddressRva')):
        g.take(f'lea {reg}, [rip+0x{(base+p["globals"][key]-(int(g.rows[g.cursor]["va"],16)+len(bytes.fromhex(g.rows[g.cursor]["bytes"])))):x} => 0x{base+p["globals"][key]:x}]')
    g.mark('methodLoop');_move(g,'load','rax',8,'rdi',l['metadataRecordPointer']);_word(g,'ecx',source='si')
    _move(g,'load','edx',4,'rax',c['metadataColumns']['vtableStartDwordOffset'])
    rip_load(g,'rax',base+p['globals']['headerPointerCellRva']);g.take('add edx, ecx',
        f'movsxd rcx, dword [rax+0x{c["metadataColumns"]["headerSections"]["vtableMethods"]["offsetField"]:x}]',
        f'add rcx, qword [rip => 0x{base+p["globals"]["metadataBaseCellRva"]:x}]')
    _move(g,'load','ecx',4,'rcx',index='rdx',scale=4);g.call(base+p['calls']['methodLookup'])
    _word(g,'ecx',source='si');g.take('add rcx, rcx')
    second_word=_move(g,'store','rax',8,'rdi',l['pairBias']*l['pairStride']+8,index='rcx',scale=8)
    g.take('test rax, rax');g.branch('je','nullMethod');_cmp_zero(g,'rax',p['methodDirectTargetOffset']);g.branch('je','fallbackTarget')
    g.take(f'test byte [rax+0x{p["methodFlagByte"]:x}], 0x{p["methodAlternateMask"]:x}');g.branch('je','directTarget')
    g.take(f'cmp qword [rip => 0x{base+p["globals"]["alternateTargetGateCellRva"]:x}], 0x0');g.branch('je','directTarget')
    target_stores=[]
    for label,source in ((None,p['methodAlternateTargetOffset']),('directTarget',p['methodDirectTargetOffset'])):
        if label:g.mark(label)
        _move(g,'load','rcx',8,'rax',source);_word(g,'eax',source='si')
        g.take(f'add rax, 0x{l["pairBias"]:x}','add rax, rax')
        target_stores.append(_move(g,'store','rcx',8,'rdi',index='rax',scale=8));g.branch('jmp','incrementMethod')
    g.mark('nullMethod');_word(g,'eax',source='si');g.take('add rax, rax')
    null_word=_move(g,'store','r13',8,'rdi',l['pairBias']*l['pairStride']+8,index='rax',scale=8)
    g.mark('fallbackTarget');_word(g,'eax',source='si');g.take(f'add rax, 0x{l["pairBias"]:x}','add rax, rax')
    target_stores.append(_move(g,'store','r15',8,'rdi',index='rax',scale=8))
    g.mark('incrementMethod');g.take('inc si',f'cmp si, word [rdi+0x{l["vtableCount"]:x}]');g.branch('jb','methodLoop');g.branch('jmp','flagUpdate');g.finish()
    g=_fragment(rows,base,p['windows']['flags'],edges,'flags')
    _load_byte(g,'eax','rdi',f['addressHandoff']['flagByte']);g.take('nop')
    _memory(g,'load','r15',8,base='rsp',displacement=p['savedHomes']['r15'])
    g.take(f'or al, 0x{f["addressHandoff"]["readyMask"]:x}')
    for reg in ('r13','rsi'):_memory(g,'load',reg,8,base='rsp',displacement=p['savedHomes'][reg])
    _move(g,'store','al',1,'rdi',f['addressHandoff']['flagByte'])
    g.take(f'or [rdi+0x{f["addressHandoff"]["blockedFlagByte"]:x}], 0x{f["addressHandoff"]["blockedMask"]:x}');g.finish()
    g=_fragment(rows,base,p['windows']['linkedMethods'],edges,'linkedMethods');_labels(g,base,p['labels'])
    linked_methods=_linked_methods(g,base,c,f)
    g=_fragment(rows,base,p['windows']['special'],edges,'special');_labels(g,base,p['labels'])
    special=_special(g,base,c)
    g=_fragment(rows,base,p['windows']['restore'],edges,'restore')
    g.take(f'add rsp, 0x{f["addressHandoff"]["frameBytes"]:x}','pop rdi','pop rbx','ret');g.finish()
    helper_calls=[row['siteRva'] for row in f['directCalls'] if row['targetRva']==p['calls']['incomingAddress']]
    recursive_calls=[row['siteRva'] for row in f['directCalls'] if row['targetRva']==f['entryRva']]
    addresses=_origins(rows,edges,base,{**f,'incomingAddressCallRvas':sorted(helper_calls+recursive_calls)})
    if len(helper_calls)!=2 or len(recursive_calls)!=1 or len(addresses)!=3:
        raise ValueError(LABEL+'.complete-incoming-address-call-inventory')
    for key, result, publication in (('linkedArray',linked,linked_publication),('ordinaryArray',ordinary,ordinary_publication)):
        result['freshAllocationReturnPointerPublicationRva']=int(publication['va'],16)-base
    return {'completeSecondSetupCfgChecked':True,'checkedInstructions':complete['checkedInstructions'],
        'selectedPrefixAndOrdinarySelectorChecked':True,'linkedArray':linked,'ordinaryArray':ordinary,
        'ordinaryCompletionFreshReadyFlagAndBlockedMaskOrChecked':True,
        'ordinaryMethodPairs':{'freshMethodLookupReturnSecondWordStoreRva':int(second_word['va'],16)-base,
            'nullMethodSubstituteSecondWordStoreRva':int(null_word['va'],16)-base,
            'targetQwordStoreRvas':[int(r['va'],16)-base for r in target_stores],
            'pairAddressFormula':'receiver + (zero_extend_64(SI) + bias) * 16',
            'pairBias':l['pairBias'],'counterBits':16,'maximumNormalLoopIterations':65535,
            'counterWrapOnContinuingPathExcluded':True,
            'freshLookupReturnAndTargetFieldsOrFallbackAddressesChecked':True,
            'methodLookupOrTargetCallableIdentityProved':False},
        'allocationArguments':{'countBits':16,'strideBytes':16,'normalAllocationOutcomeOrCapacityProved':False},
        'ordinaryBranchConditions':'initial ready/blocked masks clear, linked pointer zero, special byte zero; readable/writable stable compatible storage and normal ABI child returns',
        'linkedMethodPairs':linked_methods,'specialBranch':special,
        'allIncomingAddressHandoffs':addresses,
        'completeSecondPhysicalFieldArgumentAndPublicationProgramProved':True,
        'allOwnedInstructionsHaveExactlyOneCheckedSemanticFragment':True,
        'lookupInflationAndSpecialChildrenIdentitiesEffectsAndTerminationProved':False,
        'runtimePreparedReceiverMetadataInterfaceOrPairIdentityProved':False,
        'actualExecutionOrConcurrentPublicationProved':False,'wholeRootAdmitted':False}
