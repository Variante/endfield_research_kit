"""Named Double value times widened Single scale on a selected return path."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_definite_rows(rows,cold,pointer,offsets,providers,server_stack):
    _require(all(type(v) is int and 0 <= v < 128 for v in offsets.values()),
             'definite-field-offsets','positive typed disp8',offsets)
    _require(type(server_stack) is int and 0 <= server_stack+120 < 2**31,
             'definite-server-frame','bounded ordinary stack argument',server_stack)
    forms=['48895c2408','48896c2410','4889742418','57','4883ec70','488bea',
           '0f29742460','488bd9','0f297c2450','33d2','patch-id','498bf9','498bf0',
           'patch-call','84c0','patch-excluded','488b4b'+bytes([offsets['value']]).hex(),
           '4533c0','488bd7','value-call','807b'+bytes([offsets['applyScale']]).hex()+'00',
           '0f28f0','default-float','scale-edge','488b9c24'+(server_stack+120).to_bytes(4,'little').hex(),
           '4885db','server-excluded','66480f7ef0','0f28742460','4c8d5c2470',
           '498b5b10','498b6b18','498b7320','0f287c2450','498be3','5f','c3']
    _require(len(rows)==len(forms),'definite-rows',len(forms),len(rows))
    at=pointer;edges={};calls={};branch=None;resume=None
    for n,(row,form) in enumerate(zip(rows,forms)):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'definite-contiguity',hex(at),row['va'])
        if form.endswith('-call'):
            _require(len(raw)==5 and raw[0]==0xe8,'definite-call','direct CALL',raw.hex())
            target=relative_branch_target(raw,at,source='definiteValue')
            _require(target==providers[form],'definite-provider',providers[form],target);calls[form]=hex(target)
        elif form=='patch-id':
            _require(len(raw)==5 and raw[0]==0xb9,'definite-patch-id','MOV ECX imm32',raw.hex())
        elif form=='default-float':
            _require(len(raw)==8 and raw[:4]==bytes.fromhex('f30f103d'),'definite-default-float','complete RIP MOVSS XMM7',raw.hex())
        elif form in ('patch-excluded','scale-edge','server-excluded'):
            _require(len(raw)==6 and raw[:2]==bytes.fromhex('0f85'),'definite-edge','JNE near',raw.hex())
            target=at+6+int.from_bytes(raw[2:],'little',signed=True)
            if form=='scale-edge':branch=target;resume=at+6
            else:edges[form]=target
        else:_require(raw==bytes.fromhex(form),'definite-instruction',form,raw.hex())
        at+=len(raw)
    tail=['488b4b'+bytes([offsets['scale']]).hex(),'4533c0','488bd7','scale-call',
          '0f57c9','0f28f8','f30f5ac8','f20f59f1','resume-jump']
    _require(len(cold)==len(tail),'definite-cold-rows',len(tail),len(cold));cold_at=branch
    for row,form in zip(cold,tail):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==cold_at,'definite-cold-contiguity',hex(cold_at),row['va'])
        if form=='scale-call':
            _require(len(raw)==5 and raw[0]==0xe8,'definite-scale-call','direct CALL',raw.hex())
            target=relative_branch_target(raw,cold_at,source='definiteScale')
            _require(target==providers[form],'definite-scale-provider',providers[form],target);calls[form]=hex(target)
        elif form=='resume-jump':
            _require(len(raw)==5 and raw[0]==0xe9 and cold_at+5+int.from_bytes(raw[1:],'little',signed=True)==resume,
                     'definite-resume-edge','JMP actual main server load',raw.hex())
        else:_require(raw==bytes.fromhex(form),'definite-cold-instruction',form,raw.hex())
        cold_at+=len(raw)
    _require(all(not pointer<=v<at and not branch<=v<cold_at for v in edges.values()),'definite-excluded-edges','outside both selected physical spans',edges)
    _require(not pointer<=branch<at,'definite-cold-separated','actual nonoverlapping physical branch span',branch)
    return {'entryEnd':at,'coldStart':branch,'coldEnd':cold_at,'resumeVA':resume,
            'actualCalls':calls,'excludedTargets':edges,'frameDeltaBytes':120,'normalRetStackDeltaBytes':8,
            'floatingOperationOrder':'named GetDoubleValue(value) XMM0.low64 -> XMM6; nonzero applyScale selects named Single getter(valueScale); CVTSS2SD XMM1 then MULSD XMM6,XMM1; MOVQ result to RAX',
            'managedUnwindFamilyProved':False,'fullOtherPathsProved':False,'liveFinalValueObserved':False}


def check_definite_value(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_field
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','definite-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],
             'definite-owner',spec['baseType'],selected.parent(spec['type']))
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    owner,method=consumer_proof['symbol'].rsplit('.',1);reference=index.body(owner,method)
    records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(reference.symbol,reference.pointer)]
    named=methods(body.symbol,body.pointer);_require(bool(named),'definite-named-method','named ordinary instance Evaluate',body.symbol)
    for m in named:
        _require(not m.flags&0x10 and len(index.metadata.parameters_for(m))==7,'definite-signature','instance seven arguments',m.flags)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'definite.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),records)
        for name,typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,typ,'definite.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'definite.'+name)
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name)==('register',register),
                 'definite-input-register',[name,register],index.parameter_location(body.pointer,body.symbol,name))
    stack=index.parameter_location(body.pointer,body.symbol,'argsForServer')
    _require(stack[0]=='stack' and type(stack[1]) is int,'definite-server-stack','ordinary named stack argument',stack)
    offsets={}
    for key,qualified,typ in (('value',spec['valueField'],spec['scalarParameterType']),('scale',spec['scaleField'],spec['scalarParameterType']),('applyScale',spec['applyScaleField'],'bool')):
        owner,actual,offset=selected.field(qualified)
        _require((owner,actual)==(spec['type'],typ),'definite-field-owner',[spec['type'],typ],[owner,actual])
        require_ordinary_field(selected,qualified,typ,'definite.'+key);offsets[key]=offset
    rows=body.rows;_require(len(rows)==37,'definite-complete-main-rows',37,len(rows))
    providers={name:relative_branch_target(bytes.fromhex(rows[n]['bytes']),int(rows[n]['va'],16),source='definiteValue') for name,n in (('patch-call',13),('value-call',19))}
    edge=bytes.fromhex(rows[23]['bytes']);edge_va=int(rows[23]['va'],16)
    _require(len(edge)==6 and edge[:2]==bytes.fromhex('0f85'),'definite-cold-edge','actual JNE',edge.hex())
    cold_va=edge_va+6+int.from_bytes(edge[2:],'little',signed=True)
    raw=index.pe.bytes_at_va(cold_va,34)
    sizes=(4,3,3,5,3,3,4,4,5);cold=[];at=cold_va;offset=0
    for size in sizes:
        cold.append({'va':hex(at),'bytes':raw[offset:offset+size].hex()});at+=size;offset+=size
    providers['scale-call']=relative_branch_target(bytes.fromhex(cold[3]['bytes']),int(cold[3]['va'],16),source='definiteScale')
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    parameters=[spec['scalarParameterType'],spec['referenceParameters']['blackboard']]
    _check_named_provider(index,providers['value-call'],spec['doubleGetter'],parameters,'double',is_static=True)
    _check_named_provider(index,providers['scale-call'],spec['scalarGetter'],parameters,'float',is_static=True)
    proof=check_definite_rows(rows,cold,body.pointer,offsets,providers,stack[1])
    _require(index.extents.get(body.pointer)==proof['entryEnd'],'definite-main-physical-extent','full RET ends actual entry pdata extent',proof['entryEnd'])
    _require(cold_va in index.extents and proof['coldEnd']<=index.extents[cold_va],
             'definite-cold-physical-extent','complete branch-linked cold bytes in actual pdata range',hex(cold_va))
    main=b''.join(bytes.fromhex(r['bytes']) for r in rows)
    _require(index.pe.bytes_at_va(body.pointer,len(main))==main,'definite-raw-main','complete main raw partition',len(main))
    return {**proof,'symbol':body.symbol,'claim':'definiteValueNamedDoubleTimesWidenedSingleScaleToResult',
            'typedFields':[spec['valueField'],spec['applyScaleField'],spec['scaleField']],
            'boundary':'Actual named ordinary GetDoubleValue requests this.value and blackboard; applyScale Bool byte nonzero selects the actual branch-linked cold range requesting named ordinary Single getter with this.valueScale. CVTSS2SD widens the Single before MULSD multiplies the retained Double, and a direct jump resumes the main server-null guard and full restoring CalcResult RET. Concrete selected-image return owner and ordinary reference/Double-array inputs are checked. Actual physical pdata ranges and branch links do not prove shared managed unwind ownership. Valid receiver/field/server/frame storage, normal Win64 calls preserving this/blackboard/nonvolatile XMM6 and saved frame, body immutability, actual floating MXCSR rounding/DAZ/FTZ/exception environment and normal completion remain conditions. Default XMM7 literal is overwritten on this selected scale path and supplies no product operand. Other patch/no-scale/server paths, getter internals, runtime subtype selection and final live output remain open.'}
