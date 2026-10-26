"""Named final-attack Double result on a complete selected normal-return path."""
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_final_rows(rows, field_offset, damage_offset, excluded_damage, timing, calls):
    _require(len(rows)==42,'final-attack-row-count',42,len(rows))
    raw=[bytes.fromhex(r['bytes']) for r in rows];start=int(rows[0]['va'],16);at=start
    for row,b in zip(rows,raw):
        _require(int(row['va'],16)==at,'final-attack-contiguous',hex(at),row['va']);at+=len(b)
    _require(at-start==163,'final-attack-body-bytes',163,at-start)
    _require(all(type(n) is int and 0<=n<128 for n in (field_offset,damage_offset)),
             'final-attack-field-displacement','nonnegative signed disp8',[field_offset,damage_offset])
    _require(all(type(n) is int and 0<=n<128 for n in (excluded_damage,timing)),
             'final-attack-enum-immediate','nonnegative signed imm8',[excluded_damage,timing])
    exact={0:'4053',1:'4883ec30',2:'488bd9',3:'0f29742420',5:'33d2',7:'84c0',
        9:'837b'+bytes((damage_offset,excluded_damage)).hex(),12:'83b9e000000000',14:'4533c0',
        15:'33d2',16:'488bcb',18:'33d2',19:'488bcb',22:'0f28f0',23:'488b88b8000000',
        24:'488b4118',25:'4885c0',27:'488b8018040000',28:'4885c0',30:'80781000',
        32:'f20f5973'+bytes((field_offset,)).hex(),33:'0f28c6',34:'0f28742420',
        35:'4883c430',36:'5b',37:'c3',41:'cc'}
    _require(timing==0,'final-attack-timing-zero-encoding',0,timing)
    for n,b in exact.items():_require(raw[n].hex()==b,'final-attack-instruction',[n,b],[n,raw[n].hex()])
    _require(len(raw[4])==5 and raw[4][0]==0xb9,'final-attack-patch-id','complete MOV ECX imm32',raw[4].hex())
    for n,op in ((11,'488b0d'),(21,'488b05')):
        _require(len(raw[n])==7 and raw[n][:3].hex()==op,'final-attack-anonymous-rip-load',[n,op],raw[n].hex())
    from scripts.game_data.il2cpp.context import relative_branch_target
    targets={}
    for n in (6,17,20,38,40):
        b=raw[n];_require(len(b)==5 and b[0]==0xe8,'final-attack-call-encoding',[n,'complete E8'],b.hex())
        targets[str(n)]=relative_branch_target(b,int(rows[n]['va'],16),source='finalAttack')
    for n,target in calls.items():_require(targets[str(n)]==target,'final-attack-direct-target',[n,hex(target)],hex(targets[str(n)]))
    edges={}
    for n,op,dest in ((8,b'\x0f\x85',None),(10,b'\x0f\x84',None),(13,b'\x74',38),(26,b'\x74',40),(29,b'\x74',40),(31,b'\x0f\x85',None),(39,b'\xeb',14)):
        b=raw[n];width=4 if len(op)==2 else 1
        _require(len(b)==len(op)+width and b[:len(op)]==op,'final-attack-branch-encoding',[n,op.hex()],b.hex())
        target=int(rows[n]['va'],16)+len(b)+int.from_bytes(b[len(op):],'little',signed=True)
        _require(target==int(rows[dest]['va'],16) if dest is not None else not start<=target<at,
                 'final-attack-branch-target',[n,None if dest is None else rows[dest]['va']],hex(target));edges[str(n)]=hex(target)
    return {'selectedEntryExtent':[hex(start),hex(at)],'selectedInstructionIndices':list(range(38)),
        'actualCalls':{n:hex(t) for n,t in targets.items()},'actualEdges':edges,'frameDeltaBytes':56,
        'xmm6SavedEntryRelativeBytes':-24,'normalRetPopBytes':8,
        'operationOrder':'ordinary AfterCalculation modifier request -> same fresh fold normal Double -> retain low64 XMM6 -> post-two-call raw calcResult lowDouble load -> MULSD(scale,loadedValue) -> XMM0.low64 -> full XMM6/RBX/frame RET'}


def check_final_attack(index, fold_proof, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import native_enum_members
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.damage_snapshot_abi import require_ordinary_value_type,require_ordinary_int32_enum,require_ordinary_type
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method']);owner=index.types[spec['type']]
    def concrete_value(type_index,name,role):
        abi=require_ordinary_value_type(selected,type_index,name,role)
        raw=index.pe.bytes_at_va(selected.type_pointer(type_index),16)
        _require(int.from_bytes(raw[:8],'little')==index.types[name].index,'final-attack-concrete-value-owner',[role,index.types[name].index],raw.hex())
        return abi
    receiver=concrete_value(owner.byval_type_index,spec['type'],'finalAttack.receiver')
    defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(body.pointer,()) if f"{n.get('type')}.{n.get('method')}"==body.symbol]
    _require(bool(defs),'final-attack-entry-definition',body.symbol,defs)
    for m in defs:
        _require(m.declaring_type==owner.index and not m.flags&16 and not index.metadata.parameters_for(m),'final-attack-entry-prototype','same concrete instance zero-arg owner',m.declaring_type)
        require_ordinary_type(selected,m.return_type,'double','finalAttack.return')
    _require(body.size==spec['entryExtentBytes'],'final-attack-extent',spec['entryExtentBytes'],body.size)
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    targets={n:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='finalAttackRequest') for n in (6,17,20)}
    _check_named_provider(index,targets[6],spec['patchMethod'],['int'],'bool',is_static=True)
    field_proofs={};offsets={};enum_ids={};aliases={}
    for key,fieldname,typename,member in (('result',spec['resultField'],spec['resultType'],None),('damage',spec['damageField'],spec['damageEnum'],spec['excludedDamageMember'])):
        fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==fieldname]
        _require(len(fields)==1,'final-attack-field-count',[fieldname,1],len(fields))
        q=spec['type']+'::'+fieldname;fo,ft,offset=selected.field(q)
        _require((fo,ft)==(spec['type'],typename),'final-attack-field-owner',[spec['type'],typename],[fo,ft])
        field_proofs[key]=concrete_value(fields[0].type_index,typename,'finalAttack.'+key)
        offsets[key]=offset-spec['conditionalValueHeaderBytes']
        if member:
            require_ordinary_int32_enum(selected,fields[0].type_index,typename,'finalAttack.damage')
            members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,typename)
            ids=[x['id'] for x in members if x['name']==member];_require(len(ids)==1,'final-attack-enum-member',member,ids)
            enum_ids[key]=ids[0];aliases[key]=[x for x in members if x['id']==ids[0]]
    result_owner=index.types[spec['resultType']]
    instance_fields=[f for f in index.metadata.fields_for(result_owner) if not selected.field_attributes(f.type_index)&16]
    _require(len(instance_fields)==1,'final-attack-result-storage-count','sole Double field',len(instance_fields))
    rf=instance_fields[0];require_ordinary_type(selected,rf.type_index,'double','finalAttack.result.value')
    _require(selected.field(spec['resultType']+'::'+index.metadata.string(rf.name_index))==(spec['resultType'],'double',spec['conditionalValueHeaderBytes']),
             'final-attack-conditional-low-double-view','sole Double at declared boxed-header displacement',selected.field(spec['resultType']+'::'+index.metadata.string(rf.name_index)))
    modifiers=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(targets[17],()) if f"{n.get('type')}.{n.get('method')}"==spec['modifierMethod']]
    _require(bool(modifiers),'final-attack-modifier-definition',spec['modifierMethod'],hex(targets[17]))
    for m in modifiers:
        args=list(index.metadata.parameters_for(m))
        _require(m.declaring_type==owner.index and not m.flags&16 and len(args)==1,'final-attack-modifier-prototype','same concrete instance owner, one timing enum',m.declaring_type)
        require_ordinary_type(selected,m.return_type,'void','finalAttack.modifier.return')
        require_ordinary_int32_enum(selected,args[0].type_index,spec['timingEnum'],'finalAttack.timing')
        concrete_value(args[0].type_index,spec['timingEnum'],'finalAttack.timing.owner')
        name=index.metadata.string(args[0].name_index)
        _require(index.parameter_location(targets[17],spec['modifierMethod'],name)==('register','rdx'),'final-attack-timing-slot','rdx low32',name)
    members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,spec['timingEnum'])
    ids=[x['id'] for x in members if x['name']==spec['timingMember']];_require(len(ids)==1,'final-attack-timing-member',spec['timingMember'],ids)
    aliases['timing']=[x for x in members if x['id']==ids[0]]
    fold=index.body(spec['type'],spec['foldMethod'])
    _require(fold_proof.get('claim')=='damageScalePositiveOrderedDoubleFoldNormalReturn' and fold_proof['symbol']==fold.symbol
             and fold_proof['providerConcreteDefinitionIndex']==owner.index
             and int(fold_proof['selectedPhysicalPdataRanges'][0][0],16)==fold.pointer,
             'final-attack-fresh-fold','same fresh named concrete-owner entry',fold_proof.get('symbol'))
    _require(targets[20]==fold.pointer,'final-attack-same-fold-target',hex(fold.pointer),hex(targets[20]))
    proof=check_final_rows(rows,offsets['result'],offsets['damage'],enum_ids['damage'],ids[0],targets)
    return {**proof,'symbol':body.symbol,'claim':'finalAttackAfterCalculationFoldTimesPostCallValueNormalResult',
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows]),'receiverABI':receiver,'fieldABIs':field_proofs,
        'nativeEnumAliases':aliases,'freshFoldClaims':['damageScaleEmptySignedBoundSeedNormalReturn',fold_proof['claim']],
        'fieldViewTier':'conditional','rawInstructionTier':'exact','conditionalValueHeaderBytes':spec['conditionalValueHeaderBytes'],
        'boundary':spec['evidenceBoundary']}
