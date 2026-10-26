"""PrimaryAttr named selector's non-Main/non-Sub positive-zero return."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_selector_rows(parts,offsets,enum_ids,patch_pointer):
    _require(len(parts)==5,'primary-selector-parts',5,len(parts))
    _require(all(type(n) is int and 0<=n<128 for n in offsets.values()),'primary-selector-offsets','positive typed disp8',offsets)
    _require(all(type(n) is int and -128<=n<128 for n in enum_ids.values()) and enum_ids['Main']!=enum_ids['Sub'],
             'primary-selector-enum-domain','distinct signed imm8 enum IDs',enum_ids)
    cmp_field=lambda offset,value:'837e'+bytes([offset,value&255]).hex()
    forms=[['488bc4','48895808','48896810','48897018','57','4881ec80000000','ready-byte',
            '498be9','0f2970e8','498bd8','0f2978d8','488bfa','488bf1','ready-selected'],
           ['33d2','patch-id','patch-call','84c0','patch-excluded',cmp_field(offsets['source'],0),'480f45fb',
            cmp_field(offsets['type'],enum_ids['Main']),'not-main-selected'],
           [cmp_field(offsets['type'],enum_ids['Sub']),'not-sub-selected'],
           ['0f57c0','66480f7ec0','footer-jump'],
           ['0f28742470','4c8d9c2480000000','498b5b10','498b6b18','498b7320','0f287c2460','498be3','5f','c3']]
    edges={};ranges=[];patch=None
    for rows,expected in zip(parts,forms):
        _require(len(rows)==len(expected),'primary-selector-row-count',len(expected),len(rows));start=int(rows[0]['va'],16);at=start
        for row,form in zip(rows,expected):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'primary-selector-contiguity',hex(at),row['va'])
            if form=='ready-byte':
                _require(len(raw)==7 and raw[:2]==b'\x80\x3d' and raw[-1]==0,'primary-selector-ready-byte','complete RIP CMP byte0',raw.hex())
            elif form=='patch-id':_require(len(raw)==5 and raw[0]==0xb9,'primary-selector-patch-id','MOV ECX imm32',raw.hex())
            elif form=='patch-call':
                _require(len(raw)==5 and raw[0]==0xe8,'primary-selector-patch-call','direct CALL',raw.hex())
                patch=relative_branch_target(raw,at,source='primarySelector');_require(patch==patch_pointer,'primary-selector-patch-target',patch_pointer,patch)
            elif form in ('ready-selected','not-main-selected','footer-jump'):
                opcode=0xeb if form=='footer-jump' else 0x75
                _require(len(raw)==2 and raw[0]==opcode,'primary-selector-short-edge',hex(opcode),raw.hex());edges[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
            elif form in ('patch-excluded','not-sub-selected'):
                _require(len(raw)==6 and raw[:2]==bytes.fromhex('0f85'),'primary-selector-near-edge','JNE near',raw.hex());edges[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
            else:_require(raw==bytes.fromhex(form),'primary-selector-instruction',form,raw.hex())
            at+=len(raw)
        ranges.append((start,at))
    _require([edges[k] for k in ('ready-selected','not-main-selected','not-sub-selected','footer-jump')]==[a for a,b in ranges[1:]],
             'primary-selector-selected-edges',[a for a,b in ranges[1:]],[edges[k] for k in ('ready-selected','not-main-selected','not-sub-selected','footer-jump')])
    _require(all(not a<=edges['patch-excluded']<b for a,b in ranges),'primary-selector-patch-excluded','outside selected spans',edges['patch-excluded'])
    _require(all(b<=c or d<=a for n,(a,b) in enumerate(ranges) for c,d in ranges[n+1:]),'primary-selector-separated-spans','nonoverlapping selected ranges',ranges)
    return {'selectedSpans':[[hex(a),hex(b)] for a,b in ranges],'selectedByteCount':sum(b-a for a,b in ranges),
            'actualEdges':edges,'actualPatchCall':hex(patch),'selectedPrimaryTypeEnumIds':enum_ids,
            'returnLow64Bits':'0000000000000000','zeroingInstruction':'XORPS XMM0,XMM0 then MOVQ RAX,XMM0',
            'frameDeltaBytes':136,'normalRetStackDeltaBytes':8,'actorSelectionUsedByResult':False,
            'fullOtherPathsProved':False,'livePrimaryTypeOrFinalValueObserved':False}


def check_primary_selector(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','primary-selector-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],'primary-selector-owner',spec['baseType'],selected.parent(spec['type']))
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    owner,method=consumer_proof['symbol'].rsplit('.',1);ref=index.body(owner,method)
    records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(ref.symbol,ref.pointer)]
    named=methods(body.symbol,body.pointer);_require(bool(named),'primary-selector-definition','ordinary instance Evaluate',body.symbol)
    for m in named:
        _require(not m.flags&0x10 and len(index.metadata.parameters_for(m))==7,'primary-selector-signature','ordinary instance seven arguments',m.flags)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'primarySelector.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),records)
        for name,typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,typ,'primarySelector.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'primarySelector.'+name)
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name)==('register',register),'primary-selector-register',[name,register],index.parameter_location(body.pointer,body.symbol,name))
    offsets={};td=index.types[spec['type']]
    for key,qualified,typ in (('source',spec['sourceField'],spec['sourceEnum']),('type',spec['selectorField'],spec['selectorEnum'])):
        owner,actual,offset=selected.field(qualified)
        _require((owner,actual)==(spec['type'],typ),'primary-selector-field-owner',[spec['type'],typ],[owner,actual])
        fields=[f for f in index.metadata.fields_for(td) if index.metadata.string(f.name_index)==qualified.split('::',1)[1]]
        _require(len(fields)==1,'primary-selector-enum-field',1,len(fields))
        require_ordinary_int32_enum(selected,fields[0].type_index,typ,'primarySelector.'+key);offsets[key]=offset
    enum_ids={name:index.enum_member_id(spec['selectorEnum'],name) for name in ('Main','Sub')}
    def read(at,size,sizes):return partition(index.pe.bytes_at_va(at,size),at,sizes)
    entry=read(body.pointer,52,(3,4,4,4,1,7,7,3,4,3,4,3,3,2))
    def target(row,opcode):
        raw=bytes.fromhex(row['bytes']);va=int(row['va'],16)
        _require(raw[:len(opcode)]==opcode,'primary-selector-target-encoding',opcode.hex(),raw.hex())
        return va+len(raw)+int.from_bytes(raw[len(opcode):],'little',signed=True)
    patch_va=target(entry[-1],b'\x75');patch=read(patch_va,34,(2,5,5,2,6,4,4,4,2))
    sub_va=target(patch[-1],b'\x75');sub=read(sub_va,10,(4,6))
    zero_va=target(sub[-1],bytes.fromhex('0f85'));zero=read(zero_va,10,(3,5,2))
    footer_va=target(zero[-1],b'\xeb');footer=read(footer_va,35,(5,8,4,4,4,5,3,1,1))
    patch_pointer=relative_branch_target(bytes.fromhex(patch[2]['bytes']),int(patch[2]['va'],16),source='primarySelector')
    _check_named_provider(index,patch_pointer,spec['patchMethod'],['int'],'bool',is_static=True)
    parts=[entry,patch,sub,zero,footer]
    proof=check_selector_rows(parts,offsets,enum_ids,patch_pointer)
    _require(body.pointer in index.extents,'primary-selector-entry-pdata','actual selected named entry pdata start',hex(body.pointer))
    ranges=check_physical_coverage(index.extents,parts)
    for part in parts:
        raw=b''.join(bytes.fromhex(row['bytes']) for row in part);start=int(part[0]['va'],16)
        _require(index.pe.bytes_at_va(start,len(raw))==raw,'primary-selector-raw-partition','complete selected raw partition',hex(start))
    return {**proof,'symbol':body.symbol,'claim':'primaryAttributeTypeNeitherMainNorSubPositiveZeroResult',
            'selectedPhysicalPdataRanges':ranges,'managedSelectedUnwindFamilyProved':False,
            'typedSelectorField':spec['selectorField'],
            'boundary':'Complete selected entry-to-RET takes the anonymous readiness byte nonzero, ordinary false patch result, and the typed PrimaryAttrCalculationType Int32 field unequal to both freshly selected native Main and Sub enum IDs. This path never dereferences the selected actor, accesses nullable fields or invokes attribute/scale providers: XORPS XMM0 followed by MOVQ sets the returned low64 bits to positive-zero Double in the concrete CalcResult return, through the full frame and XMM6/XMM7 restoring RET. Ordinary receiver/inputs/source and selector enum storage, actual raw branch links and complete per-instruction unique physical range coverage are checked. Source-field compare and exact CMOV bytes are part of the path but their actor choice is unused by this result; no Main/Sub nullable helper identity or layout follows. Valid this-field/static/frame/save/return storage, original code unchanged, normal Win64 patch return/nonvolatile saved-state preservation remain conditions. No other subtype/type/patch/initializer paths, whole RAX representation beyond the selected low64 MOVQ, live selector value, final damage/Poise or shared managed unwind family is inferred.'}
