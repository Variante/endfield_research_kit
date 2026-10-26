"""Complete selected simple normal Float-times-Double program."""
import struct
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target

def check_formula_rows(rows,pointer,offsets,program,providers):
    pack_slot=offsets['packEntryStack']+136;scale=offsets['unitScale'];snap=offsets['snapshot'];simple=offsets['simple'];outscale=offsets['packScale'];attrs=offsets['packAttributes']
    byte=lambda n:bytes([n]);dword=lambda n:struct.pack('<i',n)
    _require(all(type(v) is int and 0<=v<128 for v in (scale,snap,simple,outscale,attrs)),'normal-formula-field-domain','bounded positive typed disp8',offsets)
    forms=[b'\x48\x89\x5c\x24\x08',b'\x48\x89\x6c\x24\x10',b'\x48\x89\x74\x24\x18',b'\x48\x89\x7c\x24\x20',b'\x41\x54',b'\x41\x56',b'\x41\x57',b'\x48\x83\xec\x70',
      b'\x48\x8b\xbc\x24'+dword(pack_slot),b'\x4c\x8b\xf2',b'\x48\x8b\xf1',b'\x0f\x29\x74\x24\x60',b'\x33\xd2',b'\x0f\x29\x7c\x24\x50','patch-id',b'\x49\x8b\xd9',b'\x49\x8b\xe8','patch-call',b'\x84\xc0','patch-excluded',
      b'\x48\x85\xdb','null-unit',b'\x38\x43'+byte(snap),'snapshot-excluded',b'\x38\x43'+byte(simple),'complex-excluded',
      b'\x48\x8b\x5b'+byte(scale),b'\x33\xd2',b'\x48\x8b\xce','blackboard-call',b'\x45\x33\xc0',b'\x48\x8b\xd0',b'\x48\x8b\xcb','scalar-call',
      b'\x48\x8b\x47'+byte(attrs),b'\x0f\x28\xf8',b'\xf3\x0f\x11\x7f'+byte(outscale),b'\x48\x85\xc0','null-array',
      b'\x83\x78'+byte(program['arrayLengthDword'])+b'\x02','short-array','class-carrier',
      b'\xf2\x0f\x10\x70'+byte(program['arrayReadDisp8']),b'\x83\xb9'+dword(program['anonymousClassDwordDisp32'])+b'\x00','class-init-excluded',
      'anonymous-root',b'\x0f\x57\xc0',b'\xf3\x0f\x5a\xc7',b'\x48\x8b\x88'+dword(program['anonymousRootPointerDisp32']),b'\xf2\x0f\x59\xc6',
      b'\x48\x8b\x41'+byte(program['anonymousChildPointerDisp8']),b'\x0f\x28\xf0',b'\x48\x85\xc0','null-child',b'\x48\x8b\x80'+dword(program['anonymousDebugPointerDisp32']),b'\x48\x85\xc0','null-debug',
      b'\x80\x78'+byte(program['anonymousDebugByteDisp8'])+b'\x00','debug-excluded',
      b'\x66\x48\x0f\x7e\xf0',b'\x0f\x28\x74\x24\x60',b'\x4c\x8d\x5c\x24\x70',b'\x49\x8b\x5b\x20',b'\x49\x8b\x6b\x28',b'\x49\x8b\x73\x30',b'\x49\x8b\x7b\x38',b'\x0f\x28\x7c\x24\x50',b'\x49\x8b\xe3',b'\x41\x5f',b'\x41\x5e',b'\x41\x5c',b'\xc3']
    _require(len(rows)>=len(forms),'normal-formula-complete-rows',len(forms),len(rows));at=pointer;excluded={};calls={};return_entry=None
    for row,form in zip(rows,forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'normal-formula-contiguity',hex(at),row['va'])
        if isinstance(form,bytes):_require(raw==form,'normal-formula-instruction',form.hex(),raw.hex())
        elif form=='patch-id':_require(len(raw)==5 and raw[0]==0xb9,'normal-formula-patch-id','MOV ECX imm32',raw.hex())
        elif form.endswith('-call'):
            _require(len(raw)==5 and raw[0]==0xe8,'normal-formula-call','direct CALL',raw.hex());target=relative_branch_target(raw,at,source='normalSimpleFormula')
            _require(target==providers[form],'normal-formula-provider-identity',[form,hex(providers[form])],hex(target));calls[form]=hex(target)
        elif form in ('class-carrier','anonymous-root'):
            wanted=b'\x48\x8b\x0d' if form=='class-carrier' else b'\x48\x8b\x05'
            _require(len(raw)==7 and raw[:3]==wanted,'normal-formula-anonymous-rip-load',form,raw.hex())
        else:
            opcode=b'\x0f\x86' if form=='short-array' else b'\x0f\x85' if form in ('patch-excluded','snapshot-excluded','debug-excluded') else b'\x0f\x84'
            _require(len(raw)==6 and raw[:2]==opcode,'normal-formula-selected-edge',[form,opcode.hex()],raw.hex());excluded[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
        if raw==b'\x66\x48\x0f\x7e\xf0':return_entry=at
        at+=len(raw)
    _require(all(not pointer<=target<at for target in excluded.values()),'normal-formula-excluded-targets','outside complete selected return trace',excluded)
    return {'selectedInstructionCount':len(forms),'selectedEnd':at,'commonReturnEntry':return_entry,'excludedTargets':excluded,'calls':calls,
            'actualArrayReadDisplacement':program['arrayReadDisp8'],'arrayReadWidthBytes':8,'arrayReadAddress':'anonymous carrier RAX + actualArrayReadDisplacement','arrayIndexMeaningProved':False,
            'floatingSequence':'ordinary Float provider XMM0 -> XMM7; low32 Float store; anonymous array carrier + reviewed byte displacement low64 -> XMM6; CVTSS2SD(XMM7.low32) then MULSD with XMM6.low64 -> XMM6 -> RAX.low64 -> CalcResult',
            'finalDamageOrLiveProviderValuesProved':False,'floatingEnvironmentObserved':False}


def check_normal_formula(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_process_flow import require_reference_proxy
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_field,require_ordinary_value_type,require_ordinary_double_array
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','normal-formula-fresh-result-layout','fresh normal CalcResult consumer',consumer_proof.get('claim'))
    body=index.body(spec['type'],spec['method']);selected=NativeReferenceContext(index.image,index=index)
    _require(body.symbol==consumer_proof['symbol'],'normal-formula-same-normal-body',consumer_proof['symbol'],body.symbol)
    methods=[index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(body.pointer,()) if f"{r.get('type')}.{r.get('method')}"==body.symbol]
    _require(bool(methods) and all(not m.flags&0x10 for m in methods),'normal-formula-instance-definition','ordinary named instance normal method',body.symbol)
    for method in methods:
        require_ordinary_type(selected,_parameter(selected,method,'damageUnit').type_index,spec['unitType'],'normal.formula.unit',reference_kind=0x12)
        pack=_parameter(selected,method,'damagePackData');raw=index.pe.bytes_at_va(selected.type_pointer(pack.type_index),16)
        require_reference_proxy(raw,selected.type_name(pack.type_index),spec['packType'],0x11,'normal.formula.packRef')
        require_ordinary_value_type(selected,method.return_type,spec['returnType'],'normal.formula.result')
    _require(selected.is_value_type(spec['packType']),'normal-formula-pack-owner','selected value owner',spec['packType'])
    _require(not selected.is_value_type(spec['type']) and index.parameter_location(body.pointer,body.symbol,'this')==('register','rcx') and index.parameter_location(body.pointer,body.symbol,'damageUnit')==('register','r9'),
             'normal-formula-reference-registers','ordinary this RCX/unit R9',body.symbol)
    location=index.parameter_location(body.pointer,body.symbol,'damagePackData')
    _require(location[0]=='stack' and type(location[1]) is int,'normal-formula-pack-stack','explicit reference proxy stack offset',location)
    header=spec['unboxedHeaderBytes'];_require(header==16,'normal-formula-value-header','reviewed Win64 boxed header adjustment',header)
    offsets={'packEntryStack':location[1]}
    for key,qualified,typ,owner in (('snapshot',spec['snapshotField'],'bool',spec['unitType']),('simple',spec['simpleField'],'bool',spec['unitType']),
                                   ('packScale',spec['packScaleField'],'float',spec['packType'])):
        actual_owner,actual_type,offset=selected.field(qualified)
        _require((actual_owner,actual_type)==(owner,typ),'normal-formula-field-owner',[owner,typ],[actual_owner,actual_type])
        require_ordinary_field(selected,qualified,typ,'normal.formula.'+key)
        offsets[key]=offset-header if owner==spec['packType'] else offset
    owner,scale_type,offset=selected.field(spec['scaleField'])
    _require(owner==spec['unitType'],'normal-formula-scale-owner',spec['unitType'],owner)
    require_ordinary_field(selected,spec['scaleField'],scale_type,'normal.formula.scaleParameter');offsets['unitScale']=offset
    owner,array_type,offset=selected.field(spec['packAttributesField'])
    _require((owner,array_type)==(spec['packType'],'double[]'),'normal-formula-array-owner',[spec['packType'],'double[]'],[owner,array_type])
    td=index.types[owner];field_name=spec['packAttributesField'].split('::',1)[1]
    fields=[f for f in index.metadata.fields_for(td) if index.metadata.string(f.name_index)==field_name]
    _require(len(fields)==1,'normal-formula-array-field-unique',1,len(fields));field=fields[0]
    require_ordinary_double_array(selected,field.type_index,'normal.formula.array')
    offsets['packAttributes']=offset-header
    ancestor=spec['blackboardGetter'].rsplit('.',1)[0];chain=[];current=spec['type']
    while current!=ancestor and len(chain)<8:
        parent=selected.parent(current)
        _require(parent and parent not in chain and not selected.is_value_type(current),'normal-formula-blackboard-ancestor',ancestor,[current,parent]);chain.append(parent);current=parent
    _require(current==ancestor,'normal-formula-blackboard-ancestor',ancestor,chain)
    rows=body.rows;_require(len(rows)>=34,'normal-formula-provider-rows',34,len(rows))
    providers={name:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='normalFormulaProvider') for name,n in (('patch-call',17),('blackboard-call',29),('scalar-call',33))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    _check_named_provider(index,providers['blackboard-call'],spec['blackboardGetter'],[],'Beyond.ActionBlackboard',is_static=False)
    _check_named_provider(index,providers['scalar-call'],spec['scalarGetter'],[scale_type,'Beyond.ActionBlackboard'],'float',is_static=True)
    proof=check_formula_rows(rows,body.pointer,offsets,spec['anonymousProgram'],providers)
    _require(proof['commonReturnEntry']==int(consumer_proof['returnEntry'],16),'normal-formula-common-result-return',consumer_proof['returnEntry'],hex(proof['commonReturnEntry']))
    _require(body.pointer in index.extents and proof['selectedEnd']<=index.extents[body.pointer],'normal-formula-owned-selected-span','complete entry-to-RET within exact owner',hex(proof['selectedEnd']))
    actual=b''.join(bytes.fromhex(r['bytes']) for r in rows[:proof['selectedInstructionCount']])
    _require(actual==index.pe.bytes_at_va(body.pointer,proof['selectedEnd']-body.pointer),'normal-formula-raw-coverage','complete raw selected byte partition',len(actual))
    return {**proof,'symbol':body.symbol,'claim':'snapshotNormalSimpleFloatScaleTimesDoubleCarrierToResult',
            'packAttributesUnboxedOffset':offsets['packAttributes'],'typedPackFields':[spec['packScaleField'],spec['packAttributesField']],'checkedValueOwner':spec['packType'],'metadataReceiverAncestorChain':chain,
            'boundary':'The complete selected false-IFix/nonnull-unit/zero-snapshot/nonzero-simple branch requests the named ordinary Float scalar getter, stores its low32 value in the typed explicit value-ref pack atkScale field and reads low64 from an anonymous array carrier slot reached through the typed Double[] attackerAttributes field. Ordinary Unit input/CalcResult return, explicit value ref, selected value owner, boxed-to-unboxed header adjustment, array/Double element ABI and metadata receiver ancestry are separately checked. All selected guards and excluded direct targets, CVTSS2SD/MULSD and full common restoring RET are checked. The formula is the actual Float-to-Double conversion then Double multiply; floating MXCSR/exception/DAZ/rounding state and live provider values are not observed. Array index interpretation requires separately compatible payload offset/element stride/runtime layout; the exact byte displacement and width do not infer an element number. Anonymous array layout/slot meaning, valid initialized provider/receiver/static/frame/array storage, normal Win64 returns and noninterference remain conditions. No attribute-enum identity for the slot, final damage, full other branches, runtime-class parity or snapshot compact-index equality is inferred.'}
