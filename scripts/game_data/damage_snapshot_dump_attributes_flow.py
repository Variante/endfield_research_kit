"""Complete selected two-loop attribute-array production and normal return."""

from scripts.game_data.damage_snapshot_cache_flow import _require


def check_dump_rows(rows, offsets, anon, layout, expected_targets):
    _require(len(rows)==119,'dump-row-count',119,len(rows))
    raw = [bytes.fromhex(r['bytes']) for r in rows]
    start = int(rows[0]['va'], 16)
    at = start
    for row, b in zip(rows, raw):
        _require(int(row['va'],16)==at,'dump-contiguous-row',hex(at),row['va'])
        at += len(b)
    _require(at-start==560,'dump-body-bytes',560,at-start)
    exact = {0: '48895c2408', 1: '48896c2410', 2: '4889742418', 3: '48897c2420', 4: '4156', 5: '4883ec20', 6: '488be9', 7: '33d2', 10: '84c0', 15: '33ff', 16: '4c8bf0', 17: '4885c0', 19: '8bdf', 24: '3b18', 31: '488b10', 32: '4885d2', 37: '4885c0', 39: '4533c0', 40: '8bd3', 41: '488bc8', 43: '4885f6', 47: '4863c3', 48: 'ffc3', 54: '488bf0', 55: '4885c0', 61: '3b38', 68: '488b10', 69: '4885d2', 74: '4885c0', 76: '4533c0', 77: '8bd7', 78: '488bc8', 80: '4885db', 84: '4863c7', 85: 'ffc7', 88: '488b5c2430', 89: '488b6c2438', 90: '488b742440', 91: '488b7c2448', 92: '4883c420', 93: '415e', 94: 'c3', 95: '488bc8', 102: '488bc8', 116: 'cc', 118: 'cc'}
    def d8(value):
        _require(type(value) is int and 0<=value<128,'dump-attributes-disp8','nonnegative signed byte',value)
        return bytes((value,)).hex()
    def d32(value):
        _require(type(value) is int and 0<=value<2**31,'dump-attributes-disp32','nonnegative signed DWORD',value)
        return value.to_bytes(4,'little').hex()
    _require(layout['strideBytes']==8 and type(layout['strideBytes']) is int,'dump-attributes-double-stride',8,layout['strideBytes'])
    exact.update({13:'488d4d'+d8(offsets['firstLock']),21:'39b8'+d32(anon['readyDword']),23:'488b80'+d32(anon['payloadPointer']),
        27:'488b75'+d8(offsets['attackerArray']),28:'39b9'+d32(anon['readyDword']),30:'488b81'+d32(anon['payloadPointer']),
        34:'817a'+d8(anon['opaqueCountDword'])+d32(anon['opaqueSignedLimit']),36:'498b86'+d32(offsets['actorAttributes']),
        45:'3b5e'+d8(layout['countDwordOffset']),49:'f20f1144c6'+d8(layout['payloadOffset']),52:'488d4d'+d8(offsets['secondLock']),
        58:'83b8'+d32(anon['readyDword'])+'00',60:'488b80'+d32(anon['payloadPointer']),64:'488b9d'+d32(offsets['defenderArray']),
        65:'83b9'+d32(anon['readyDword'])+'00',67:'488b81'+d32(anon['payloadPointer']),
        71:'817a'+d8(anon['opaqueCountDword'])+d32(anon['opaqueSignedLimit']),73:'488b86'+d32(offsets['actorAttributes']),
        82:'3b7b'+d8(layout['countDwordOffset']),86:'f20f1144c3'+d8(layout['payloadOffset']),
        109:'4839b9'+d32(anon['coldContinuationPointer']),112:'4883b9'+d32(anon['coldContinuationPointer'])+'00'})
    for n, b in exact.items():
        _require(raw[n].hex()==b,'dump-instruction',[n,b],[n,raw[n].hex()])
    _require(len(raw[8])==5 and raw[8][0]==0xb9,'dump-patch-id','complete MOV ECX imm32',raw[8].hex())
    rip = {12: '488b15', 20: '488b05', 26: '488b0d', 51: '488b15', 57: '488b05', 63: '488b0d', 97: '488b05', 100: '488b0d', 104: '488b05', 107: '488b0d'}
    for n, op in rip.items():
        _require(len(raw[n])==7 and raw[n][:3].hex()==op,'dump-rip-load',[n,op,7],raw[n].hex())
    branches = ((11, '0f85', None), (18, '0f84', 51), (22, '0f84', 95), (25, '7d', 51), (29, '0f84', 99), (33, '0f84', 117), (35, '0f8f', None), (38, '0f84', 117), (44, '0f84', 117), (46, '0f83', 115), (50, 'e9', 20), (56, '0f84', 88), (59, '0f84', 102), (62, '7d', 88), (66, '0f84', 106), (70, '0f84', 117), (72, '0f8f', None), (75, '0f84', 117), (81, '0f84', 117), (83, '0f83', 115), (87, 'e9', 57), (98, 'e9', 23), (101, 'e9', 30), (105, 'e9', 60), (108, 'e9', 67), (110, '0f84', 36), (111, 'e9', None), (113, '0f84', 73), (114, 'e9', None))
    edges={}
    for n, op, dest in branches:
        op = bytes.fromhex(op)
        b = raw[n]
        _require(b[:len(op)]==op,'dump-branch-opcode',[n,op.hex()],b.hex())
        _require(len(b)==len(op)+(4 if len(op)==2 or op==b'\xe9' else 1),'dump-branch-length',[n,len(op)+(4 if len(op)==2 or op==b'\xe9' else 1)],len(b))
        target = int(rows[n]['va'], 16) + len(b) + int.from_bytes(b[len(op):], 'little', signed=True)
        _require(target==int(rows[dest]['va'],16) if dest is not None else not start<=target<at,'dump-branch-target',[n,None if dest is None else rows[dest]['va']],hex(target))
        edges[str(n)]=hex(target)
    calls = {}
    for n in (9, 14, 42, 53, 79, 96, 99, 103, 106, 115, 117):
        b = raw[n]
        _require(len(b)==5 and b[0]==0xe8,'dump-call-encoding',[n,'complete E8'],b.hex())
        calls[n] = int(rows[n]['va'], 16) + 5 + int.from_bytes(b[1:], 'little', signed=True)
    _require(calls[14]==calls[53] and calls[42]==calls[79],'dump-phase-call-targets','same physical Lock and same named GetValue',[hex(calls[n]) for n in (14,53,42,79)])
    covered = set(exact) | set(rip) | {8} | {n for n, _, _ in branches} | set(calls)
    _require(covered==set(range(119)),'dump-complete-grammar','all119 rows independently classified',sorted(set(range(119))-covered))

    def riptarget(n):
        return int(rows[n]['va'], 16) + 7 + int.from_bytes(raw[n][3:], 'little', signed=True)
    _require(len(set(riptarget(n) for n in (12, 51)))==1,'dump-lock-context','same complete RIP slot',[hex(riptarget(n)) for n in (12, 51)])
    _require(len(set(riptarget(n) for n in (20, 57, 97, 104)))==1,'dump-anonymous-bound-context','same complete RIP slot',[hex(riptarget(n)) for n in (20, 57, 97, 104)])
    _require(len(set(riptarget(n) for n in (26, 63, 100, 107)))==1,'dump-anonymous-actor-context','same complete RIP slot',[hex(riptarget(n)) for n in (26, 63, 100, 107)])
    for n,target in expected_targets.items():
        _require(calls[n]==target,'dump-attributes-actual-call-target',[n,hex(target)],hex(calls[n]))
    return {'completeEntryExtent':[hex(start),hex(at)],'completeInstructionCount':119,'full119rowsClassified':True,
        'all29branchTargetsChecked':True,'actualEdges':edges,'actualCalls':{str(n):hex(t) for n,t in calls.items()},
        'samePhysicalLockAndGetterAcrossPhases':True,'sameAnonymousBoundStaticRootSlot':True,
        'selectedEntryIndices':list(range(20)),'attackerGuardIndices':list(range(20,26)),
        'attackerIterationIndices':list(range(26,51)),'defenderSetupIndices':list(range(51,57)),
        'defenderGuardIndices':list(range(57,63)),'defenderIterationIndices':list(range(63,88)),
        'fullNormalFooterIndices':list(range(88,95)),'frameDeltaBytes':40,'normalRetPopBytes':8,
        'recurrence':'EDI0; EBX0; first GetValue(EDX=oldEBX) -> normalDouble -> MOVSXD oldEBX -> INC EBX32 -> sameoldindex8B store; second GetValue(EDX=oldEDI) analogously -> full normal void RET',
        'stableAnonymousBoundRequired':True,'coherentTimeSnapshotProved':False,'typedLockReturnProved':False}

def check_dump_attributes(index, selector_proof, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import runtime_type_name
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_pointer,require_ordinary_value_type,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_max_poise_flow import check_reference_definition
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    selected=NativeReferenceContext(index.image,index=index);owner=index.types[spec['type']];actor=index.types[spec['actorType']];attrs=index.types[spec['attributesType']]
    body=index.body(spec['type'],spec['method'])
    receiver=require_ordinary_value_type(selected,owner.byval_type_index,spec['type'],'dump.receiver')
    record=index.pe.bytes_at_va(selected.type_pointer(owner.byval_type_index),16)
    _require(int.from_bytes(record[:8],'little')==owner.index,'dump-pack-concrete-owner',owner.index,record.hex())
    defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(body.pointer,()) if f"{n.get('type')}.{n.get('method')}"==body.symbol]
    _require(bool(defs),'dump-entry-definition',body.symbol,defs)
    for m in defs:
        _require(m.declaring_type==owner.index and not m.flags&16 and not index.metadata.parameters_for(m),'dump-entry-prototype','same concrete instance owner zero arguments',m.declaring_type)
        require_ordinary_type(selected,m.return_type,'void','dump.return')
    _require(body.size==spec['entryExtentBytes'],'dump-entry-extent',spec['entryExtentBytes'],body.size)
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    targets={n:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='dumpRequest') for n in (9,42)}
    _check_named_provider(index,targets[9],spec['patchMethod'],['int'],'bool',is_static=True)
    offsets={};field_abis={};lock_declarations=[]
    for key,fieldname in (('firstLock',spec['firstLockStorageField']),('secondLock',spec['secondLockStorageField']),('attackerArray',spec['attackerArrayField']),('defenderArray',spec['defenderArrayField'])):
        fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==fieldname]
        _require(len(fields)==1,'dump-pack-field-count',[fieldname,1],len(fields))
        fo,ft,offset=selected.field(spec['type']+'::'+fieldname)
        _require(fo==spec['type'],'dump-pack-field-owner',spec['type'],fo);offsets[key]=offset-spec['conditionalValueHeaderBytes']
        if key.endswith('Array'):
            abi=require_ordinary_type(selected,fields[0].type_index,'double[]','dump.'+key,reference_kind=0x1d)
            raw=index.pe.bytes_at_va(selected.type_pointer(fields[0].type_index),16);element=int.from_bytes(raw[:8],'little')
            field_abis[key]={**abi,'element':require_ordinary_pointer(selected,element,runtime_type_name(index.pe,index.metadata,element),'double','dump.'+key+'.element')}
        else:
            raw=index.pe.bytes_at_va(selected.type_pointer(fields[0].type_index),16)
            _require(ft==spec['lockStorageDeclarationType'] and len(raw)==16 and raw[10]==0x15 and raw[11]&0x7f==0 and selected.is_value_type(ft),
                     'dump-lock-storage-declaration','declared ordinary generic value storage, no typed Lock ABI',[ft,raw.hex()])
            lock_declarations.append({'field':spec['type']+'::'+fieldname,'declaredType':ft,'viewTier':'structuralOnly','genericLockReturnIdentityProved':False})
    actor_abi=check_reference_definition(selected,actor.byval_type_index,spec['actorType'],actor.index,'dump.compatibleActorDeclaration')
    fo,ft,offsets['actorAttributes']=selected.field(spec['actorAttributesField'])
    _require((fo,ft)==(spec['actorType'],spec['attributesType']),'dump-actor-field-owner',[spec['actorType'],spec['attributesType']],[fo,ft])
    af=[f for f in index.metadata.fields_for(actor) if index.metadata.string(f.name_index)==spec['actorAttributesField'].split('::',1)[1]]
    _require(len(af)==1,'dump-actor-field-count',1,len(af))
    attributes_abi=check_reference_definition(selected,af[0].type_index,spec['attributesType'],attrs.index,'dump.currentAttributes')
    providers=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(targets[42],()) if f"{n.get('type')}.{n.get('method')}"==spec['providerMethod']]
    _require(bool(providers),'dump-provider-identity',spec['providerMethod'],hex(targets[42]))
    for m in providers:
        args=list(index.metadata.parameters_for(m))
        _require(m.declaring_type==attrs.index and not m.flags&16 and len(args)==1,'dump-provider-prototype','same concrete Attributes instance, one enum argument',m.declaring_type)
        require_ordinary_int32_enum(selected,args[0].type_index,spec['attributeEnum'],'dump.attributeIndex')
        enum_record=index.pe.bytes_at_va(selected.type_pointer(args[0].type_index),16)
        _require(int.from_bytes(enum_record[:8],'little')==index.types[spec['attributeEnum']].index,'dump-enum-concrete-owner',index.types[spec['attributeEnum']].index,enum_record.hex())
        require_ordinary_type(selected,m.return_type,'double','dump.provider.return')
        name=index.metadata.string(args[0].name_index)
        _require(index.parameter_location(targets[42],spec['providerMethod'],name)==('register','rdx'),'dump-enum-slot','RDX low32',name)
    proof=check_dump_rows(rows,offsets,spec['anonymousProgram'],spec['conditionalArrayLayout'],targets)
    selector=index.body(spec['type'],spec['selectorMethod'])
    _require(selector_proof.get('claim')=='damageTypeSelectedAttackerDoubleArraySlotNormalReturn'
             and selector_proof['symbol']==selector.symbol and selector_proof['receiverABI']['type']==spec['type']
             and int(selector_proof['selectedEntryExtent'][0],16)==selector.pointer
             and selector_proof['conditionalValueHeaderBytes']==spec['conditionalValueHeaderBytes']
             and selector_proof['conditionalArrayLayout']==spec['conditionalArrayLayout']
             and not selector_proof['producerIndexMapProved'],'dump-fresh-selector','same freshly proved compatible selector, prior producer gap retained',selector_proof.get('symbol'))
    return {**proof,'symbol':body.symbol,'claim':'dumpAttributesTwoOrderedEnumDoubleArrayLoopsNormalReturn',
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows]),'receiverABI':receiver,'arrayFieldABIs':field_abis,
        'actorDeclarationABI':actor_abi,'attributesDeclarationABI':attributes_abi,'lockStorageDeclarations':lock_declarations,
        'providerConcreteDefinitionIndex':attrs.index,'attributeEnumConcreteDefinitionIndex':index.types[spec['attributeEnum']].index,
        'conditionalValueHeaderBytes':spec['conditionalValueHeaderBytes'],'conditionalArrayLayout':spec['conditionalArrayLayout'],
        'conditionalSelectorJoin':{'freshSelectorClaim':selector_proof['claim'],'nativeCaseAnnotations':selector_proof['nativeCaseAnnotations'],
            'tier':'conditional','conditions':spec['selectorJoinConditions'],'actualInvocationOrCallingOrderProved':False},
        'providerInternalValuesOrCoherentSnapshotProved':False,'anonymousBoundValueOrSourceProved':False,'boundary':spec['evidenceBoundary']}
