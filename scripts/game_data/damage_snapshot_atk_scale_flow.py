"""Selected null-override AtkScale consumer of named attacker.get_atk."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_physical_coverage(extents,parts):
    ranges=set()
    for part in parts:
        for row in part:
            at=int(row['va'],16);end=at+len(bytes.fromhex(row['bytes']))
            matches=[(start,stop) for start,stop in extents.items() if start<=at<end<=stop]
            _require(len(matches)==1,'atk-scale-instruction-physical-range',
                     'unique actual pdata range covers complete selected instruction',[row['va'],end,matches])
            ranges.add(matches[0])
    return [[hex(start),hex(end)] for start,end in sorted(ranges)]


def check_atk_rows(parts,offset,providers,override_stack,server_stack):
    _require(len(parts)==3,'atk-scale-parts',3,len(parts))
    _require(type(offset) is int and 0<=offset<128,'atk-scale-field-offset','typed positive disp8',offset)
    _require(all(type(x) is int and 0<=x+120<2**31 for x in (override_stack,server_stack)),
             'atk-scale-stack-arguments','bounded ordinary stack slots',[override_stack,server_stack])
    dword=lambda x:x.to_bytes(4,'little').hex()
    forms=[['48895c2408','48896c2410','4889742418','57','4883ec70','ready-byte','498bd9','498bf0','488bea','488bf9','ready-excluded',
            '0f29742460','33d2','patch-id','0f297c2450','patch-call','84c0','patch-excluded',
            '488b8424'+dword(override_stack+120),'4885c0','null-override-selected'],
           ['4885ed','null-attacker-excluded','33d2','488bcd','attack-call','0f28f0','scalar-jump'],
           ['488b4f'+bytes([offset]).hex(),'4533c0','488bd3','scalar-call',
            '488b9c24'+dword(server_stack+120),'0f28f8','4885db','server-excluded',
            '0f57c0','f30f5ac7','f20f59c6','66480f7ec0','0f287c2450','4c8d5c2470',
            '498b5b10','498b6b18','498b7320','0f28742460','498be3','5f','c3']]
    edges={};calls={};ranges=[]
    for rows,expected in zip(parts,forms):
        _require(len(rows)==len(expected),'atk-scale-row-count',len(expected),len(rows));start=int(rows[0]['va'],16);at=start
        for row,form in zip(rows,expected):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'atk-scale-contiguity',hex(at),row['va'])
            if form.endswith('-call'):
                _require(len(raw)==5 and raw[0]==0xe8,'atk-scale-call','direct CALL',raw.hex())
                target=relative_branch_target(raw,at,source='atkScale')
                _require(target==providers[form],'atk-scale-provider',providers[form],target);calls[form]=hex(target)
            elif form=='ready-byte':
                _require(len(raw)==7 and raw[:2]==b'\x80\x3d' and raw[-1]==0,'atk-scale-ready-byte','complete RIP byte CMP0',raw.hex())
            elif form=='patch-id':_require(len(raw)==5 and raw[0]==0xb9,'atk-scale-patch-id','MOV ECX imm32',raw.hex())
            elif form=='scalar-jump':
                _require(len(raw)==5 and raw[0]==0xe9,'atk-scale-resume-jump','JMP near',raw.hex());edges[form]=at+5+int.from_bytes(raw[1:],'little',signed=True)
            elif form.endswith('-excluded') or form=='null-override-selected':
                opcode=bytes.fromhex('0f85') if form in ('patch-excluded','server-excluded') else bytes.fromhex('0f84')
                _require(len(raw)==6 and raw[:2]==opcode,'atk-scale-edge',opcode.hex(),raw.hex());edges[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
            else:_require(raw==bytes.fromhex(form),'atk-scale-instruction',form,raw.hex())
            at+=len(raw)
        ranges.append((start,at))
    _require(edges['null-override-selected']==ranges[1][0] and edges['scalar-jump']==ranges[2][0],
             'atk-scale-selected-links',[r[0] for r in ranges[1:]],[edges['null-override-selected'],edges['scalar-jump']])
    _require(all(not a<=target<b for key,target in edges.items() if key.endswith('-excluded') for a,b in ranges),
             'atk-scale-excluded-links','outside selected spans',edges)
    _require(all(b<=c or d<=a for n,(a,b) in enumerate(ranges) for c,d in ranges[n+1:]),'atk-scale-separated-spans','nonoverlapping selected spans',ranges)
    return {'selectedSpans':[[hex(a),hex(b)] for a,b in ranges],'selectedByteCount':sum(b-a for a,b in ranges),
            'actualCalls':calls,'actualEdges':edges,'frameDeltaBytes':120,'normalRetStackDeltaBytes':8,
            'floatingOperationOrder':'named incoming attacker.get_atk ordinary Double normal XMM0 -> XMM6; typed atkScale named Single getter -> XMM7; CVTSS2SD Single to Double then MULSD converted scale by retained attack -> MOVQ RAX',
            'managedColdUnwindFamilyProved':False,'nonnullOverrideArraySemanticsProved':False,'liveFinalValueObserved':False}


def check_atk_scale(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_field
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','atk-scale-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],'atk-scale-owner',spec['baseType'],selected.parent(spec['type']))
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    owner,method=consumer_proof['symbol'].rsplit('.',1);ref=index.body(owner,method)
    records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(ref.symbol,ref.pointer)]
    named=methods(body.symbol,body.pointer);_require(bool(named),'atk-scale-definition','ordinary instance Evaluate',body.symbol)
    for m in named:
        _require(not m.flags&0x10 and len(index.metadata.parameters_for(m))==7,'atk-scale-signature','ordinary instance seven arguments',m.flags)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'atkScale.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),records)
        for name,typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,typ,'atkScale.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'atkScale.'+name)
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name)==('register',register),'atk-scale-register',[name,register],index.parameter_location(body.pointer,body.symbol,name))
    arguments={}
    for name in ('attackerOverrideAttributes','argsForServer'):
        location=index.parameter_location(body.pointer,body.symbol,name)
        _require(location[0]=='stack' and type(location[1]) is int,'atk-scale-stack-location','ordinary named stack argument',[name,location]);arguments[name]=location[1]
    owner,typ,offset=selected.field(spec['scaleField'])
    _require((owner,typ)==(spec['type'],spec['scalarParameterType']),'atk-scale-field-owner',[spec['type'],spec['scalarParameterType']],[owner,typ])
    require_ordinary_field(selected,spec['scaleField'],typ,'atkScale.scale')
    rows=body.rows;_require(len(rows)==51,'atk-scale-complete-body-rows',51,len(rows));prefix=rows[:21];tail=rows[24:45]
    raw_edge=bytes.fromhex(prefix[-1]['bytes']);edge_va=int(prefix[-1]['va'],16)
    _require(len(raw_edge)==6 and raw_edge[:2]==bytes.fromhex('0f84'),'atk-scale-null-override-edge','JZ near',raw_edge.hex())
    cold_va=edge_va+6+int.from_bytes(raw_edge[2:],'little',signed=True)
    cold=partition(index.pe.bytes_at_va(cold_va,27),cold_va,(3,6,2,3,5,3,5))
    providers={name:relative_branch_target(bytes.fromhex(part[n]['bytes']),int(part[n]['va'],16),source='atkScaleProvider')
               for name,part,n in (('patch-call',prefix,15),('attack-call',cold,4),('scalar-call',tail,3))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    _check_named_provider(index,providers['attack-call'],spec['attackGetter'],[],'double',is_static=False)
    _require(spec['attackGetter'].rsplit('.',1)[0]==spec['referenceParameters']['attacker'],'atk-scale-attack-receiver-owner',spec['referenceParameters']['attacker'],spec['attackGetter'])
    _require(index.parameter_location(providers['attack-call'],spec['attackGetter'],'this')==('register','rcx'),
             'atk-scale-get-attack-receiver','ordinary instance this RCX',spec['attackGetter'])
    _check_named_provider(index,providers['scalar-call'],spec['scalarGetter'],[typ,spec['referenceParameters']['blackboard']],'float',is_static=True)
    proof=check_atk_rows([prefix,cold,tail],offset,providers,arguments['attackerOverrideAttributes'],arguments['argsForServer'])
    _require(body.pointer in index.extents,'atk-scale-primary-entry-range','actual selected named entry pdata start',hex(body.pointer))
    selected_ranges=check_physical_coverage(index.extents,(prefix,cold,tail))
    ranges=[(start,end) for start,end in index.extents.items() if start<=cold_va<cold_va+27<=end]
    _require(len(ranges)==1,'atk-scale-cold-physical-span','unique actual physical pdata range',ranges)
    for part in (prefix,cold,tail):
        start=int(part[0]['va'],16);raw=b''.join(bytes.fromhex(row['bytes']) for row in part)
        _require(index.pe.bytes_at_va(start,len(raw))==raw,'atk-scale-raw-partition','complete selected byte partition',hex(start))
    return {**proof,'symbol':body.symbol,'claim':'atkScaleNullOverrideNamedAttackDoubleTimesWidenedSingleResult',
            'selectedPhysicalPdataRanges':selected_ranges,'managedSelectedUnwindFamilyProved':False,
            'coldPhysicalPdataRange':[[hex(a),hex(b)] for a,b in ranges],
            'boundary':'Complete selected entry-to-RET takes nonzero anonymous readiness byte, false ordinary patch result, null ordinary attacker override, nonnull incoming attacker and null ordinary server argument. The actual branch-linked cold range requests named ordinary attacker.get_atk Double, retains it in XMM6 and rejoins the main typed atkScale Single getter request using incoming blackboard. CVTSS2SD precedes MULSD and concrete CalcResult low-half return through full saved-frame/XMM6/XMM7 RET. Ordinary input/field/getter/return owner ABI and exact raw branch links are checked. Every selected instruction has complete unique actual pdata coverage; entry-to-next-range fallthrough and explicit cold edges prove selected machine flow, not shared managed unwind ownership of any ranges. Valid initialized objects/field/frame/static storage, original code unchanged, normal Win64 nonvolatile/saved-state preservation and actual floating MXCSR with normal completion remain conditions. Nonnull override anonymous array slot meaning, initializer/patch/server/null-attacker paths, getter internals, live attack/scale values, runtime subtype invocation and final damage stay open.'}
