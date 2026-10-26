"""Selected PrimaryAttr Double-to-Single rounding, scale and low-lane return."""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def partition(raw,start,sizes):
    _require(len(raw)==sum(sizes),'primary-raw-size',sum(sizes),len(raw))
    result=[];off=0
    for size in sizes:
        result.append({'va':hex(start+off),'bytes':raw[off:off+size].hex()});off+=size
    return result


def check_primary_rows(parts,offsets,providers,server_stack):
    _require(len(parts)==4,'primary-selected-parts',4,len(parts))
    _require(all(type(v) is int and 0<=v<128 for v in offsets.values()),'primary-fields','positive typed disp8',offsets)
    _require(type(server_stack) is int and 0<=server_stack+136<2**31,'primary-server-stack','bounded ordinary frame argument',server_stack)
    forms=[['attribute-call','807e'+bytes([offsets['applyScale']]).hex()+'00','0f57f6','default-float','f20f5af0','no-scale-excluded',
            '488b4e'+bytes([offsets['scale']]).hex(),'4533c0','488bd5','scale-call','0f28f8','f30f59f0',
            '488b9c24'+(server_stack+136).to_bytes(4,'little').hex(),'4885db','null-server-selected'],
           ['0f5ac6','result-jump'],['66480f7ec0','footer-jump'],
           ['0f28742470','4c8d9c2480000000','498b5b10','498b6b18','498b7320','0f287c2460','498be3','5f','c3']]
    edges={};calls={};ranges=[]
    for rows,expected in zip(parts,forms):
        _require(len(rows)==len(expected),'primary-instruction-count',len(expected),len(rows))
        start=int(rows[0]['va'],16);at=start
        for row,form in zip(rows,expected):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'primary-contiguity',hex(at),row['va'])
            if form.endswith('-call'):
                _require(len(raw)==5 and raw[0]==0xe8,'primary-call','direct CALL',raw.hex())
                target=relative_branch_target(raw,at,source='primaryAttrNumeric')
                _require(target==providers[form],'primary-provider',providers[form],target);calls[form]=hex(target)
            elif form=='default-float':
                _require(len(raw)==8 and raw[:4]==bytes.fromhex('f30f103d'),'primary-default-float','complete RIP MOVSS',raw.hex())
            elif form in ('no-scale-excluded','null-server-selected','result-jump','footer-jump'):
                opcode=0x74 if form in ('no-scale-excluded','null-server-selected') else 0xeb
                _require(len(raw)==2 and raw[0]==opcode,'primary-edge',hex(opcode),raw.hex())
                edges[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
            else:_require(raw==bytes.fromhex(form),'primary-instruction',form,raw.hex())
            at+=len(raw)
        ranges.append((start,at))
    _require(edges['no-scale-excluded']==int(parts[0][12]['va'],16),
             'primary-no-scale-branch','actual server load skipping selected scale instructions',edges['no-scale-excluded'])
    _require(edges['null-server-selected']==ranges[1][0] and edges['result-jump']==ranges[2][0] and edges['footer-jump']==ranges[3][0],
             'primary-selected-edges',[r[0] for r in ranges[1:]],[edges[k] for k in ('null-server-selected','result-jump','footer-jump')])
    _require(all(end<=other_start or other_end<=start for n,(start,end) in enumerate(ranges) for other_start,other_end in ranges[n+1:]),
             'primary-separated-parts','nonoverlapping selected spans',ranges)
    return {'selectedSpans':[[hex(a),hex(b)] for a,b in ranges],'selectedByteCount':sum(b-a for a,b in ranges),
            'actualCalls':calls,'actualEdges':edges,'frameDeltaBytes':136,'normalRetStackDeltaBytes':8,
            'floatingOperationOrder':'GetAttribute ordinary Double normal XMM0.low64 -> CVTSD2SS XMM6.low32; Single getter scale -> MULSS XMM6.low32; CVTPS2PD XMM0,XMM6 selected low lane -> MOVQ RAX',
            'packedUpperLaneMeaningProved':False,'entryToFragmentDataflowProved':False,'liveFinalValueObserved':False}


def check_primary_attr(index,consumer_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_value_type,require_ordinary_double_array,require_ordinary_field,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_forward_flow import _parameter
    from scripts.game_data.damage_snapshot_multiply_formula_flow import check_result_records
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(consumer_proof.get('claim')=='snapshotCacheIndexToReturn','primary-result-witness','fresh concrete CalcResult consumer',consumer_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    _require(not selected.is_value_type(spec['type']) and selected.parent(spec['type'])==spec['baseType'],
             'primary-owner',spec['baseType'],selected.parent(spec['type']))
    def methods(symbol,pointer):
        return [index.metadata.methods[r['methodIndex']] for r in index.names_by_pointer.get(pointer,()) if f"{r.get('type')}.{r.get('method')}"==symbol]
    owner,method=consumer_proof['symbol'].rsplit('.',1);ref=index.body(owner,method)
    records=[index.pe.bytes_at_va(selected.type_pointer(m.return_type),16) for m in methods(ref.symbol,ref.pointer)]
    named=methods(body.symbol,body.pointer);_require(bool(named),'primary-named-method','ordinary instance Evaluate',body.symbol)
    for m in named:
        _require(not m.flags&0x10 and len(index.metadata.parameters_for(m))==7,'primary-signature','instance seven arguments',m.flags)
        require_ordinary_value_type(selected,m.return_type,spec['returnType'],'primary.result')
        check_result_records(index.pe.bytes_at_va(selected.type_pointer(m.return_type),16),records)
        for name,typ in spec['referenceParameters'].items():
            require_ordinary_type(selected,_parameter(selected,m,name).type_index,typ,'primary.'+name,reference_kind=0x12)
        for name in ('attackerOverrideAttributes','defenderOverrideAttributes'):
            require_ordinary_double_array(selected,_parameter(selected,m,name).type_index,'primary.'+name)
    offsets={}
    for key,qualified,typ in (('scale',spec['scaleField'],spec['scalarParameterType']),('applyScale',spec['applyScaleField'],'bool')):
        owner,actual,offset=selected.field(qualified)
        _require((owner,actual)==(spec['type'],typ),'primary-field-owner',[spec['type'],typ],[owner,actual])
        require_ordinary_field(selected,qualified,typ,'primary.'+key);offsets[key]=offset
    stack=index.parameter_location(body.pointer,body.symbol,'argsForServer')
    _require(stack[0]=='stack' and type(stack[1]) is int,'primary-server-location','named ordinary stack argument',stack)
    candidates=[]
    for row in body.rows:
        raw=bytes.fromhex(row['bytes'])
        if len(raw)==5 and raw[0]==0xe8:
            pointer=relative_branch_target(raw,int(row['va'],16),source='primaryAttrEntry')
            if methods(spec['attributeGetter'],pointer):candidates.append((int(row['va'],16),pointer))
    _require(len(candidates)==1,'primary-attribute-call-unique',1,len(candidates))
    start,attribute=candidates[0];attribute_methods=methods(spec['attributeGetter'],attribute)
    for m in attribute_methods:
        arguments=index.metadata.parameters_for(m)
        _require(not m.flags&0x10 and len(arguments)==3,'primary-attribute-signature','instance three arguments',m.flags)
        require_ordinary_type(selected,m.return_type,'double','primary.attribute.return')
        require_ordinary_type(selected,arguments[0].type_index,spec['referenceParameters']['attacker'],'primary.attribute.source',reference_kind=0x12)
        require_ordinary_int32_enum(selected,arguments[1].type_index,spec['attributeEnum'],'primary.attribute.enum')
        require_ordinary_double_array(selected,arguments[2].type_index,'primary.attribute.array')
    for name,register in (('this','rcx'),('attrSource','rdx'),('attributeType','r8'),('attrArray','r9')):
        _require(index.parameter_location(attribute,spec['attributeGetter'],name)==('register',register),
                 'primary-attribute-abi',[name,register],index.parameter_location(attribute,spec['attributeGetter'],name))
    first=partition(index.pe.bytes_at_va(start,61),start,(5,4,3,8,4,2,4,3,3,5,3,4,8,3,2))
    edge=bytes.fromhex(first[-1]['bytes']);edge_va=int(first[-1]['va'],16)
    _require(edge[:1]==b'\x74','primary-server-edge','actual JE null server',edge.hex())
    widen_va=edge_va+2+int.from_bytes(edge[1:],'little',signed=True)
    widen=partition(index.pe.bytes_at_va(widen_va,5),widen_va,(3,2))
    result_va=widen_va+5+int.from_bytes(bytes.fromhex(widen[-1]['bytes'])[1:],'little',signed=True)
    result=partition(index.pe.bytes_at_va(result_va,7),result_va,(5,2))
    footer_va=result_va+7+int.from_bytes(bytes.fromhex(result[-1]['bytes'])[1:],'little',signed=True)
    footer=partition(index.pe.bytes_at_va(footer_va,35),footer_va,(5,8,4,4,4,5,3,1,1))
    scale=relative_branch_target(bytes.fromhex(first[9]['bytes']),int(first[9]['va'],16),source='primaryScale')
    _check_named_provider(index,scale,spec['scalarGetter'],[spec['scalarParameterType'],spec['referenceParameters']['blackboard']],'float',is_static=True)
    proof=check_primary_rows([first,widen,result,footer],offsets,{'attribute-call':attribute,'scale-call':scale},stack[1])
    end=index.extents.get(body.pointer)
    _require(end==footer_va+35 and all(body.pointer<=int(a,16)<int(b,16)<=end for a,b in proof['selectedSpans']),
             'primary-physical-span','all fragments and full RET within actual named entry pdata extent',end)
    # This independent entry witness establishes save offsets only. The gap to
    # the numerical fragment remains an explicit continuity condition.
    entry_forms=['488bc4','48895808','48896810','48897018','57','4881ec80000000',
                 'ready-byte','498be9','0f2970e8','498bd8','0f2978d8','488bfa','488bf1']
    rows=body.rows[:13];_require(len(rows)==13,'primary-entry-save-rows',13,len(rows));at=body.pointer
    for row,form in zip(rows,entry_forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'primary-entry-contiguity',hex(at),row['va'])
        if form=='ready-byte':_require(len(raw)==7 and raw[:2]==b'\x80\x3d' and raw[-1]==0,'primary-entry-ready','complete RIP CMP byte0',raw.hex())
        else:_require(raw==bytes.fromhex(form),'primary-entry-save',form,raw.hex())
        at+=len(raw)
    entry=b''.join(bytes.fromhex(r['bytes']) for r in rows)
    _require(index.pe.bytes_at_va(body.pointer,len(entry))==entry,'primary-entry-raw','independent exact entry save witness',len(entry))
    for name,register in (('this','rcx'),('attacker','rdx'),('defender','r8'),('blackboard','r9')):
        _require(index.parameter_location(body.pointer,body.symbol,name)==('register',register),'primary-entry-register',[name,register],index.parameter_location(body.pointer,body.symbol,name))
    return {**proof,'symbol':body.symbol,'claim':'primaryAttributeDoubleRoundedSingleScaleThenPackedLowLaneResult',
            'entrySavedFrameWitnessBytes':len(entry),'typedFields':[spec['applyScaleField'],spec['scaleField']],
            'boundary':'A unique actual named ordinary Double GetAttribute call anchors this local consumer. Its normal result is rounded to Single by CVTSD2SS before a nonzero typed applyScale Bool selects named ordinary Single getter and MULSS. Null server selects CVTPS2PD (packed two-lane conversion); only its low Double lane is returned through MOVQ and the complete common saved-state RET. A separate exact entry save witness establishes the compatible frame size and save/restore offsets, not complete entry-to-fragment control or dataflow. At fragment entry RSI must still be compatible this and RBP incoming blackboard; actual attribute-call arguments and live contexts must be valid, saved frame/storage continuous and unmodified, and normal Win64 callees preserve nonvolatile SIMD/register state. Prefragment actor/enum/nullable selection and instruction paths are open. No upper packed lane meaning, getter internals, FP environment observations, code modification, runtime subtype invocation or final live output is inferred; MXCSR and normal completion remain conditions.'}
