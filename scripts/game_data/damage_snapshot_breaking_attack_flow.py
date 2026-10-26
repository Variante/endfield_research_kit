"""Selected named BreakingAttack mixed-precision numerical consumer."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_breaking_rows(parts,offsets,providers,arguments,enum_ids):
    _require(len(parts)==4,'breaking-parts',4,len(parts))
    _require(all(type(x) is int and 0<=x<128 for x in offsets.values()),'breaking-field-offsets','typed positive disp8',offsets)
    _require(all(type(x) is int and 0<=x+152<2**31 for x in arguments.values()),'breaking-stack-arguments','bounded ordinary stack slots',arguments)
    dword=lambda n:n.to_bytes(4,'little').hex()
    forms=[['488bc4','48895808','48896810','48897018','57','4881ec90000000','ready-byte',
            '498bf9','0f2970e8','498bf0','0f2978d8','488bea','440f2940c8','488bd9','440f2948b8','ready-selected'],
           ['33d2','patch-id','patch-call','84c0','patch-excluded',
            '4c8b8c24'+dword(arguments['attackerOverrideAttributes']+152),'41b8'+dword(enum_ids['attacker']),
            '488364242000','488bd5','488bcb','attacker-call',
            '4c8b8c24'+dword(arguments['defenderOverrideAttributes']+152),'41b8'+dword(enum_ids['defender']),
            '488364242000','488bd6','488bcb','440f28c0','defender-call',
            '488b4b'+bytes([offsets['multiplier']]).hex(),'4533c0','488bd7','0f28f8','multiplier-call',
            '488b4b'+bytes([offsets['scale']]).hex(),'4533c0','488bd7','440f28c8','scale-call',
            '488b9c24'+dword(arguments['argsForServer']+152),'0f28f0','4885db','server-selected'],
           ['f2410f59f8','0f57c9','f3410f59f1','f20f5acf','f30f59f1','0f57c0','f30f5ac6','66480f7ec0','footer-jump'],
           ['0f287c2470','4c8d9c2490000000','498b5b10','498b6b18','498b7320','410f2873f0',
            '450f2843d0','450f284bc0','498be3','5f','c3']]
    edges={};calls={};ranges=[]
    for rows,expected in zip(parts,forms):
        _require(len(rows)==len(expected),'breaking-row-count',len(expected),len(rows))
        start=int(rows[0]['va'],16);at=start
        for row,form in zip(rows,expected):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'breaking-contiguity',hex(at),row['va'])
            if form.endswith('-call'):
                _require(len(raw)==5 and raw[0]==0xe8,'breaking-call','direct CALL',raw.hex())
                target=relative_branch_target(raw,at,source='breakingAttack')
                _require(target==providers[form],'breaking-provider',providers[form],target);calls[form]=hex(target)
            elif form=='ready-byte':
                _require(len(raw)==7 and raw[:2]==b'\x80\x3d' and raw[-1]==0,'breaking-ready-byte','complete RIP CMP byte0',raw.hex())
            elif form=='patch-id':
                _require(len(raw)==5 and raw[0]==0xb9,'breaking-patch-id','MOV ECX imm32',raw.hex())
            elif form in ('ready-selected','server-selected','footer-jump'):
                opcode={'ready-selected':0x75,'server-selected':0x74,'footer-jump':0xeb}[form]
                _require(len(raw)==2 and raw[0]==opcode,'breaking-edge',hex(opcode),raw.hex())
                edges[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
            elif form=='patch-excluded':
                _require(len(raw)==6 and raw[:2]==bytes.fromhex('0f85'),'breaking-patch-edge','JNE near',raw.hex())
                edges[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
            else:_require(raw==bytes.fromhex(form),'breaking-instruction',form,raw.hex())
            at+=len(raw)
        ranges.append((start,at))
    _require([edges[k] for k in ('ready-selected','server-selected','footer-jump')]==[a for a,b in ranges[1:]],
             'breaking-selected-links',[a for a,b in ranges[1:]],[edges[k] for k in ('ready-selected','server-selected','footer-jump')])
    _require(all(not a<=edges['patch-excluded']<b for a,b in ranges),'breaking-patch-exclusion','outside selected spans',edges['patch-excluded'])
    _require(all(b<=c or d<=a for n,(a,b) in enumerate(ranges) for c,d in ranges[n+1:]),'breaking-disjoint-spans','nonoverlapping selected spans',ranges)
    return {'selectedSpans':[[hex(a),hex(b)] for a,b in ranges],'selectedByteCount':sum(b-a for a,b in ranges),
            'actualCalls':calls,'actualEdges':edges,'actualAttributeEnumIds':enum_ids,'frameDeltaBytes':152,'normalRetStackDeltaBytes':8,
            'floatingOperationOrder':'MULSD defender attribute Double by attacker attribute Double; MULSS atkScale Single by multiplier Single; CVTSD2SS attribute product to Single; MULSS scale product by rounded attribute product; CVTSS2SD final Single to Double; MOVQ RAX',
            'providerInternalsOrLiveValuesProved':False,'fullOtherPathsProved':False}


def check_breaking_attack(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_field,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','breaking-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],'breaking-owner',spec['baseType'],selected.parent(spec['type']))
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    owner,method=consumer_proof['symbol'].rsplit('.',1);reference=index.body(owner,method)
    records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(reference.symbol,reference.pointer)]
    named=methods(body.symbol,body.pointer);_require(bool(named),'breaking-named-definition','ordinary instance Evaluate',body.symbol)
    for m in named:
        _require(not m.flags&0x10 and len(index.metadata.parameters_for(m))==7,'breaking-signature','instance seven arguments',m.flags)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'breaking.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),records)
        for name,typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,typ,'breaking.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'breaking.'+name)
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name)==('register',register),'breaking-input-register',[name,register],index.parameter_location(body.pointer,body.symbol,name))
    arguments={}
    for name in ('attackerOverrideAttributes','defenderOverrideAttributes','argsForServer'):
        location=index.parameter_location(body.pointer,body.symbol,name)
        _require(location[0]=='stack' and type(location[1]) is int,'breaking-stack-location','ordinary named stack argument',[name,location]);arguments[name]=location[1]
    offsets={}
    for key,qualified in (('multiplier',spec['multiplierField']),('scale',spec['scaleField'])):
        owner,typ,offset=selected.field(qualified)
        _require((owner,typ)==(spec['type'],spec['scalarParameterType']),'breaking-field-owner',[spec['type'],spec['scalarParameterType']],[owner,typ])
        require_ordinary_field(selected,qualified,typ,'breaking.'+key);offsets[key]=offset
    rows=body.rows;_require(len(rows)==109,'breaking-complete-body-rows',109,len(rows))
    parts=[rows[:16],rows[19:51],rows[67:76],rows[98:]]
    providers={name:relative_branch_target(bytes.fromhex(parts[1][n]['bytes']),int(parts[1][n]['va'],16),source='breakingProvider')
               for name,n in (('patch-call',2),('attacker-call',10),('defender-call',17),('multiplier-call',22),('scale-call',27))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    for key in ('multiplier-call','scale-call'):
        _check_named_provider(index,providers[key],spec['scalarGetter'],[spec['scalarParameterType'],spec['referenceParameters']['blackboard']],'float',is_static=True)
    _require(providers['attacker-call']==providers['defender-call'],'breaking-common-attribute-target','same actual named instance getter',providers)
    attribute=providers['attacker-call'];named_attribute=methods(spec['attributeGetter'],attribute)
    _require(bool(named_attribute),'breaking-attribute-name',spec['attributeGetter'],hex(attribute))
    for m in named_attribute:
        args=index.metadata.parameters_for(m)
        _require(not m.flags&0x10 and len(args)==3,'breaking-attribute-signature','ordinary instance three arguments',m.flags)
        require_ordinary_type(selected,m.return_type,'double','breaking.attribute.return')
        require_ordinary_type(selected,args[0].type_index,spec['referenceParameters']['attacker'],'breaking.attribute.source',reference_kind=0x12)
        require_ordinary_int32_enum(selected,args[1].type_index,spec['attributeEnum'],'breaking.attribute.enum')
        require_ordinary_double_array(selected,args[2].type_index,'breaking.attribute.array')
    for name,register in (('this','rcx'),('attrSource','rdx'),('attributeType','r8'),('attrArray','r9')):
        _require(index.parameter_location(attribute,spec['attributeGetter'],name)==('register',register),'breaking-attribute-abi',[name,register],index.parameter_location(attribute,spec['attributeGetter'],name))
    enum_ids={key:index.enum_member_id(spec['attributeEnum'],member) for key,member in spec['attributeMembers'].items()}
    _require(all(type(n) is int and 0<=n<2**31 for n in enum_ids.values()),'breaking-enum-domain','nonnegative ordinary Int32 enum immediates',enum_ids)
    proof=check_breaking_rows(parts,offsets,providers,arguments,enum_ids)
    end=index.extents.get(body.pointer)
    _require(end==int(proof['selectedSpans'][-1][1],16) and all(body.pointer<=int(a,16)<int(b,16)<=end for a,b in proof['selectedSpans']),
             'breaking-owned-physical-range','all selected bytes and RET within actual entry pdata extent',end)
    for part in parts:
        raw=b''.join(bytes.fromhex(row['bytes']) for row in part);start=int(part[0]['va'],16)
        _require(index.pe.bytes_at_va(start,len(raw))==raw,'breaking-raw-coverage','complete selected raw partition',hex(start))
    return {**proof,'symbol':body.symbol,'claim':'breakingAttackTypedAttributesAndSingleFactorsMixedPrecisionResult',
            'typedAttributeMembers':spec['attributeMembers'],'typedScalarFields':[spec['multiplierField'],spec['scaleField']],
            'boundary':'Complete selected entry-to-RET skips the anonymous metadata initializer on nonzero byte, takes false ordinary patch result and null ordinary server argument. Named ordinary GetAttribute requests incoming attacker/attacker override with selected native enum Atk and incoming defender/defender override with BreakingAttackDamageTakenScalar; immediate IDs are freshly joined to selected native enum members. Ordinary Single blackboard getters request typed multiplier and atkScale fields. Actual Double attribute product is rounded to Single, while atkScale times multiplier is already a Single product; a second Single multiply precedes Double widening and concrete CalcResult return. Register/frame and XMM6/7/8/9 save/restore, all direct selected edges, raw partitions and full RET are checked. This source/result arithmetic requires valid initialized objects/arrays/field/frame/static storage, original code unchanged, normal Win64 callees preserving nonvolatile registers/SIMD/saved state, actual MXCSR rounding/DAZ/FTZ/exception state and normal completion. Getter internals, actual live values, metadata initializer, patched/server paths, runtime subtype invocation and final damage remain open.'}
