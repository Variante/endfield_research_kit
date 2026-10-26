"""Finite DamageType jump table and selected attacker-array Double returns."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_table_pe(pe, operand, width):
    """Whole raw-backed RVA table; executable readable sections are admitted."""
    _require(type(width) is int and 0<width<=256,'damage-table-width','bounded positive byte count',width)
    b=pe.buf
    def read(fmt,at):
        size=struct.calcsize(fmt)
        _require(0<=at<=len(b)-size,'damage-table-pe-range',[fmt,size],at)
        return struct.unpack_from(fmt,b,at)[0]
    coff=read('<I',60)+4;opt=coff+20;size=read('<H',coff+16)
    _require(read('<H',opt)==0x20b and size>=160,'damage-table-pe-header','PE32+ with relocation directory',size)
    rva=operand-pe.image_base;matches=[]
    for n in range(read('<H',coff+2)):
        off=opt+size+40*n;va=read('<I',off+12);raw=read('<I',off+16)
        if va<=rva and rva+width<=va+raw:matches.append((off,read('<I',off+36)))
    _require(len(matches)==1,'damage-table-complete-raw-section','one complete raw-backed table section',matches)
    flags=matches[0][1]
    _require(flags&0x40000000 and not flags&0x80000000,'damage-table-section-flags','readable nonwritable; executable allowed',hex(flags))
    rr,rs=read('<I',opt+152),read('<I',opt+156)
    if rs:
        sections=[s for s in pe.sections if s['virtualAddress']<=rr and rr+rs<=s['virtualAddress']+s['rawSize']]
        _require(len(sections)==1,'damage-table-relocation-directory','complete unique raw-backed directory',[rr,rs])
        s=sections[0];at=s['rawPointer']+rr-s['virtualAddress'];end=at+rs
        while at<end:
            page,block=read('<I',at),read('<I',at+4)
            _require(block>=8 and block%2==0 and at+block<=end,'damage-table-relocation-block','complete bounded even block',[at,block,end])
            for cursor in range(at+8,at+block,2):
                item=read('<H',cursor);kind=item>>12
                _require(kind in (0,1,2,3,10),'damage-table-relocation-kind','admitted ABSOLUTE/HIGH/LOW/HIGHLOW/DIR64',kind)
                address=page+(item&4095);span={0:0,1:2,2:2,3:4,10:8}[kind]
                _require(not kind or not(address<rva+width and address+span>rva),'damage-table-relocation-overlap','none across complete table',[kind,hex(address),span])
            at+=block
    return {'completeRawBytes':width,'sectionCharacteristics':hex(flags),'baseRelocationOverlapProvedAbsent':True,
        'originalRuntimeTableUnmodified':'conditional','observedLiveProtection':False}


def check_selector_rows(rows, data, image_base, damage_offset, array_offset, cases, excluded_ids, layout):
    _require(len(rows)==65 and len(data)==32,'damage-selector-partition-shape',[65,32],[len(rows),len(data)])
    _require(all(type(x) is int and 0<=x<8 for x in [*cases,*excluded_ids]),'damage-selector-case-id','ordinary integer IDs0..7',[list(cases),excluded_ids])
    _require(all(type(x) is int and 0<=x<128 for x in cases.values()),'damage-selector-index-immediate','nonnegative signed imm8',list(cases.values()))
    _require(type(layout.get('payloadOffset')) is int and 0<=layout['payloadOffset']<=2**31-1
             and type(layout.get('strideBytes')) is int and layout['strideBytes']==8 and all(layout['payloadOffset']+8*x<=2**31-1 for x in cases.values()),
             'damage-selector-double-address-layout','declared nonnegative signed disp32 payload and eight-byte Double stride',layout)
    raw=[bytes.fromhex(r['bytes']) for r in rows];start=int(rows[0]['va'],16);at=start
    for row,b in zip(rows,raw):
        _require(int(row['va'],16)==at,'damage-selector-contiguous',hex(at),row['va']);at+=len(b)
    _require(at-start==228,'damage-selector-code-bytes',228,at-start)
    _require(all(type(x) is int and 0<=x<128 for x in (damage_offset,array_offset,layout['countDwordOffset'])),
             'damage-selector-disp8','nonnegative signed disp8',[damage_offset,array_offset,layout])
    exact={0:'4053',1:'4883ec20',2:'488bd9',3:'33d2',6:'84c0',8:'486343'+bytes((damage_offset,)).hex(),9:'83f807',13:'4803ca',14:'ffe1',61:'cc',63:'cc',64:'6690'}
    for n,b in exact.items():_require(raw[n].hex()==b,'damage-selector-instruction',[n,b],[n,raw[n].hex()])
    _require(len(raw[4])==5 and raw[4][0]==0xb9,'damage-selector-patch-id','MOV ECX imm32',raw[4].hex())
    for n in (5,60,62):_require(len(raw[n])==5 and raw[n][0]==0xe8,'damage-selector-call','complete E8',[n,raw[n].hex()])
    _require(len(raw[11])==7 and raw[11][:3]==bytes.fromhex('488d15'),'damage-selector-image-base-lea','complete RIP LEA RDX',raw[11].hex())
    base=int(rows[11]['va'],16)+7+int.from_bytes(raw[11][3:],'little',signed=True)
    _require(base==image_base,'damage-selector-lea-base',hex(image_base),hex(base))
    _require(len(raw[12])==7 and raw[12][:3]==bytes.fromhex('8b8c82'),'damage-selector-table-sib','MOV ECX [RDX+RAX*4+disp32]',raw[12].hex())
    table=base+int.from_bytes(raw[12][3:],'little',signed=True)
    _require(table==at,'damage-selector-table-base','immediately following complete code partition',[hex(table),hex(at)])
    rvas=[int.from_bytes(data[n:n+4],'little') for n in range(0,32,4)]
    _require(0<=image_base<=2**64-1-max(rvas),'damage-selector-target-no-wrap','UInt64 imagebase + UInt32 RVAs',[image_base,max(rvas)])
    targets=[base+x for x in rvas];byva={int(r['va'],16):n for n,r in enumerate(rows)}
    edges={}
    def edge(n,op,dest):
        b=raw[n];width=4 if len(op)==2 else 1
        _require(len(b)==len(op)+width and b[:len(op)]==op,'damage-selector-branch-encoding',[n,op.hex()],b.hex())
        target=int(rows[n]['va'],16)+len(b)+int.from_bytes(b[len(op):],'little',signed=True)
        _require(target==int(rows[dest]['va'],16) if dest is not None else not start<=target<at+32,
                 'damage-selector-branch-target',[n,dest],hex(target));edges[str(n)]=hex(target)
    edge(7,b'\x0f\x85',None);edge(10,b'\x0f\x87',None)
    _require(set(cases)|set(excluded_ids)==set(range(8)) and not set(cases)&set(excluded_ids),
             'damage-selector-complete-eight-cases','five normal and three explicit excluded IDs',[cases,excluded_ids])
    _require(len(cases)==5 and len(excluded_ids)==3,'damage-selector-case-count',[5,3],[len(cases),len(excluded_ids)])
    leaves=[]
    for damage_id,index in sorted(cases.items()):
        target=targets[damage_id]
        _require(target in byva,'damage-selector-normal-table-target','actual instruction boundary',hex(target));n=byva[target]
        _require(n in (15,24,33,42,51),'damage-selector-normal-leaf','one complete normal leaf',n)
        expected={n:'488b43'+bytes((array_offset,)).hex(),n+1:'4885c0',n+3:'8378'+bytes((layout['countDwordOffset'],index)).hex(),n+5:'f20f1080'+(layout['payloadOffset']+layout['strideBytes']*index).to_bytes(4,'little',signed=True).hex(),n+6:'4883c420',n+7:'5b',n+8:'c3'}
        _require(type(index) is int and 0<=index<128,'damage-selector-index-immediate','nonnegative imm8',index)
        for k,b in expected.items():_require(raw[k].hex()==b,'damage-selector-leaf-instruction',[k,b],[k,raw[k].hex()])
        edge(n+2,b'\x0f\x84' if n==15 else b'\x74',62)
        edge(n+4,b'\x0f\x86' if n==15 else b'\x76',60)
        leaves.append({'damageId':damage_id,'rawArrayIndex':index,'loadDisplacementBytes':layout['payloadOffset']+layout['strideBytes']*index,
            'selectedInstructionIndices':list(range(15))+list(range(n,n+9)),'normalRetPopBytes':8})
    _require({byva[targets[k]] for k in cases}=={15,24,33,42,51},'damage-selector-all-leaves-covered','all five complete leaf bodies',cases)
    for k in excluded_ids:_require(not start<=targets[k]<at+32,'damage-selector-cold-target-excluded','outside code/table partition',[k,hex(targets[k])])
    return {'selectedEntryExtent':[hex(start),hex(at+32)],'codePartitionBytes':228,'tableDataBytes':32,'tableOperand':hex(table),
        'actualTableTargets':[hex(x) for x in targets],'normalCases':leaves,'excludedColdDamageIds':excluded_ids,'actualEdges':edges,
        'frameDeltaBytes':40,'normalResult':'selected raw eight-byte payload MOVSD -> XMM0.low64 -> add RSP32 -> pop RBX -> RET',
        'signedNegativeOrAboveSevenIdsExcluded':True,'allUnselectedColdPathsProved':False}

def check_damage_type_selector(index, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import runtime_type_name,native_enum_members
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_pointer,require_ordinary_value_type,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.il2cpp.context import relative_branch_target
    selected=NativeReferenceContext(index.image,index=index);owner=index.types[spec['type']];body=index.body(spec['type'],spec['method'])
    def concrete_value(type_index,name,role):
        abi=require_ordinary_value_type(selected,type_index,name,role)
        raw=index.pe.bytes_at_va(selected.type_pointer(type_index),16)
        _require(int.from_bytes(raw[:8],'little')==index.types[name].index,'damage-selector-concrete-owner',[role,index.types[name].index],raw.hex())
        return abi
    receiver=concrete_value(owner.byval_type_index,spec['type'],'damageSelector.receiver')
    defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(body.pointer,()) if f"{n.get('type')}.{n.get('method')}"==body.symbol]
    _require(bool(defs),'damage-selector-definition',body.symbol,defs)
    for m in defs:
        _require(m.declaring_type==owner.index and not m.flags&16 and not index.metadata.parameters_for(m),'damage-selector-prototype','same concrete instance owner zero arguments',m.declaring_type)
        require_ordinary_type(selected,m.return_type,'double','damageSelector.return')
    _require(body.size==spec['entryExtentBytes'],'damage-selector-entry-extent',spec['entryExtentBytes'],body.size)
    blob=index.pe.bytes_at_va(body.pointer,body.size);rows=partition(blob[:spec['codeBytes']],body.pointer,spec['codeInstructionLengths']);data=blob[spec['codeBytes']:]
    target=relative_branch_target(bytes.fromhex(rows[5]['bytes']),int(rows[5]['va'],16),source='damageSelectorPatch')
    _check_named_provider(index,target,spec['patchMethod'],['int'],'bool',is_static=True)
    offsets={};abis={}
    for key,fieldname,typename in (('damage',spec['damageField'],spec['damageEnum']),('array',spec['arrayField'],'double[]')):
        fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==fieldname]
        _require(len(fields)==1,'damage-selector-field-count',[fieldname,1],len(fields))
        fo,ft,offset=selected.field(spec['type']+'::'+fieldname)
        _require((fo,ft)==(spec['type'],typename),'damage-selector-field-owner',[spec['type'],typename],[fo,ft])
        offsets[key]=offset-spec['conditionalValueHeaderBytes']
        if key=='damage':
            abis[key]=concrete_value(fields[0].type_index,typename,'damageSelector.damage')
            require_ordinary_int32_enum(selected,fields[0].type_index,typename,'damageSelector.damage')
        else:
            raw=index.pe.bytes_at_va(selected.type_pointer(fields[0].type_index),16)
            _require(len(raw)==16 and raw[10]==0x1d and raw[11]==0,'damage-selector-array-ordinary','ordinary SZARRAY reference, no byref/pinned/value marker',raw.hex())
            element=int.from_bytes(raw[:8],'little')
            abis[key]={'nativeKind':'0x1d','flags':'0x0','element':require_ordinary_pointer(selected,element,runtime_type_name(index.pe,index.metadata,element),'double','damageSelector.array.element')}
    damage_members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,spec['damageEnum'])
    annotation_members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,spec['attributeEnumAnnotation'])
    def member_id(members,name):
        ids=[x['id'] for x in members if x['name']==name]
        _require(len(ids)==1,'damage-selector-native-member',name,ids)
        return ids[0]
    cases={};annotations=[]
    for item in spec['normalCases']:
        damage_id=member_id(damage_members,item['damageMember']);physical_index=member_id(annotation_members,item['numericAnnotationMember'])
        _require(damage_id not in cases,'damage-selector-duplicate-normal-case','unique native damage ID',damage_id)
        cases[damage_id]=physical_index
        annotations.append({'damageId':damage_id,'damageAliases':[x for x in damage_members if x['id']==damage_id],
            'rawArrayIndex':physical_index,'attributeTypeSameIdAliases':[x for x in annotation_members if x['id']==physical_index],
            'attributeValueInterpretationTier':'conditional numeric annotation; producer index map unproved'})
    excluded=[member_id(damage_members,name) for name in spec['excludedDamageMembers']]
    proof=check_selector_rows(rows,data,index.pe.image_base,offsets['damage'],offsets['array'],cases,excluded,spec['conditionalArrayLayout'])
    pe=check_table_pe(index.pe,int(proof['tableOperand'],16),len(data))
    table_row={'va':proof['tableOperand'],'bytes':data.hex()}
    return {**proof,'symbol':body.symbol,'claim':'damageTypeSelectedAttackerDoubleArraySlotNormalReturn','receiverABI':receiver,'fieldABIs':abis,
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows,[table_row]]),'tablePe':pe,'originalTableBytes':data.hex(),
        'nativeCaseAnnotations':annotations,'typedFieldViewTier':'conditional','rawInstructionAndTableTier':'exact',
        'conditionalValueHeaderBytes':spec['conditionalValueHeaderBytes'],'conditionalArrayLayout':spec['conditionalArrayLayout'],
        'producerIndexMapProved':False,'liveAttributeValuesObserved':False,'boundary':spec['evidenceBoundary']}
