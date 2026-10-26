"""Independently prove the compared-entry helper's two unpatched inline paths.

Pointer equality does not establish the receiver's concrete runtime type.
Typed Definite fields remain a compatible field-view condition.
"""
from scripts.game_data.damage_snapshot_cache_flow import _require
from scripts.game_data.il2cpp.context import relative_branch_target


def check_inline_rows(main,cold,pointer,offsets,providers,function_offset,info_offset,comparison_pointer,scaled):
    _require(type(scaled) is bool,'calculation-inline-mode','explicit bool',scaled)
    _require(all(type(v) is int and 0<=v<128 for v in offsets.values()),'calculation-inline-field-offsets','typed positive disp8',offsets)
    _require(all(type(v) is int and 0<=v<2**31 for v in (function_offset,info_offset)),
             'calculation-inline-carrier-offsets','bounded positive disp32',[function_offset,info_offset])
    dword=lambda n:n.to_bytes(4,'little').hex();byte=lambda n:bytes([n]).hex()
    forms=['48895c2408','4889742410','57','4883ec70','488b0a','498bf9','0f29742460','498bf0','0f297c2450','488bda',
           'opaque-call','488b03','4c8b90'+dword(function_offset),'488b88'+dword(info_offset),'comparison-address','4c3bd0','unequal-excluded',
           '33d2','patch-id','patch-call','84c0','patch-excluded','488bbc24a0000000','4533c0',
           '488b4b'+byte(offsets['value']),'488bd7','value-call','807b'+byte(offsets['applyScale'])+'00',
           '0f28f0','unused-default-single','scale-edge','488b9c24c0000000','4885db','server-excluded',
           '0f28c6','0f28742460','4c8d5c2470','498b5b10','66480f7ec0','498b7318','0f287c2450','498be3','5f','c3']
    _require(len(main)==len(forms),'calculation-inline-main-count',len(forms),len(main))
    at=pointer;edges={};calls={};scale_resume=None
    for row,form in zip(main,forms):
        raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'calculation-inline-contiguity',hex(at),row['va'])
        if form.endswith('-call'):
            _require(len(raw)==5 and raw[0]==0xe8,'calculation-inline-call','direct CALL',raw.hex())
            target=relative_branch_target(raw,at,source='calculationInline');calls[form]=hex(target)
            if form!='opaque-call':_require(target==providers[form],'calculation-inline-provider',providers[form],target)
        elif form=='comparison-address':
            _require(len(raw)==7 and raw[:3]==bytes.fromhex('488d05'),'calculation-inline-comparison-lea','complete RIP LEA',raw.hex())
            actual=at+7+int.from_bytes(raw[3:],'little',signed=True)
            _require(actual==comparison_pointer,'calculation-inline-named-comparison',comparison_pointer,actual)
        elif form=='patch-id':_require(len(raw)==5 and raw[0]==0xb9,'calculation-inline-patch-id','MOV ECX imm32',raw.hex())
        elif form=='unused-default-single':_require(len(raw)==8 and raw[:4]==bytes.fromhex('f30f103d'),'calculation-inline-unused-literal','complete RIP MOVSS XMM7',raw.hex())
        elif form=='unequal-excluded':
            _require(len(raw)==2 and raw[0]==0x75,'calculation-inline-compare-edge','JNE short',raw.hex());edges[form]=at+2+int.from_bytes(raw[1:],'little',signed=True)
        elif form in ('patch-excluded','scale-edge','server-excluded'):
            _require(len(raw)==6 and raw[:2]==bytes.fromhex('0f85'),'calculation-inline-near-edge','JNE near',raw.hex());edges[form]=at+6+int.from_bytes(raw[2:],'little',signed=True)
            if form=='scale-edge':scale_resume=at+6
        else:_require(raw==bytes.fromhex(form),'calculation-inline-instruction',form,raw.hex())
        at+=len(raw)
    cold_end=None
    if scaled:
        tail=['488b4b'+byte(offsets['scale']),'4533c0','488bd7','scale-call','0f57c9','0f28f8','f30f5ac8','f20f59f1','resume-jump']
        _require(len(cold)==len(tail),'calculation-inline-cold-count',len(tail),len(cold));cold_at=edges['scale-edge']
        for row,form in zip(cold,tail):
            raw=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==cold_at,'calculation-inline-cold-contiguity',hex(cold_at),row['va'])
            if form=='scale-call':
                _require(len(raw)==5 and raw[0]==0xe8,'calculation-inline-scale-call','direct CALL',raw.hex())
                target=relative_branch_target(raw,cold_at,source='calculationInlineScale')
                _require(target==providers[form],'calculation-inline-scale-provider',providers[form],target);calls[form]=hex(target)
            elif form=='resume-jump':
                _require(len(raw)==5 and raw[0]==0xe9 and cold_at+5+int.from_bytes(raw[1:],'little',signed=True)==scale_resume,
                         'calculation-inline-resume-edge','direct JMP actual helper server load',raw.hex())
            else:_require(raw==bytes.fromhex(form),'calculation-inline-cold-instruction',form,raw.hex())
            cold_at+=len(raw)
        cold_end=cold_at
        _require(at<=edges['scale-edge'] or cold_end<=pointer,'calculation-inline-separated-cold','nonoverlapping actual cold span',[pointer,at,edges['scale-edge'],cold_end])
    else:_require(not cold,'calculation-inline-no-scale-cold','no selected cold fragment',cold)
    excluded=[v for k,v in edges.items() if k!='scale-edge' or not scaled]
    _require(all(not pointer<=v<at and (cold_end is None or not edges['scale-edge']<=v<cold_end) for v in excluded),
             'calculation-inline-excluded-edges','outside selected spans',edges)
    return {'selectedMainSpan':[hex(pointer),hex(at)],'selectedColdSpan':[hex(edges['scale-edge']),hex(cold_end)] if cold_end is not None else None,
            'selectedByteCount':at-pointer+(cold_end-edges['scale-edge'] if cold_end is not None else 0),
            'actualEdges':edges,'actualCalls':calls,'comparisonEntry':hex(comparison_pointer),
            'frameDeltaBytes':120,'normalRetStackDeltaBytes':8,'actualApplyScaleCondition':'nonzero selected' if scaled else 'zero selected',
            'floatingOperationOrder':'Double getter low64 -> XMM6; Single scale getter -> CVTSS2SD XMM1; MULSD XMM6,XMM1; XMM6 -> XMM0 -> RAX' if scaled else 'Double getter low64 -> XMM6 -> XMM0 -> RAX unchanged; no rounding or multiply',
            'unusedDefaultSingleSuppliesResultOperand':False,'receiverConcreteTypeProved':False,'runtimeSubtypeObserved':False,
            'separateDefiniteBodyUsedAsInlineProof':False,'otherPatchOrServerPathsProved':False}


def check_calculation_inline(index,dispatch_proof,spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_field
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    _require(dispatch_proof.get('claim')=='calculationIndirectCallbackAndNamedDefiniteEntrySelection',
             'calculation-inline-fresh-dispatch','fresh actual callback/entry-comparison witness',dispatch_proof.get('claim'))
    selected=NativeReferenceContext(index.image,index=index)
    comparison=index.body(spec['type'],spec['method'])
    _require(int(dispatch_proof['comparisonEntry'],16)==comparison.pointer
             and comparison.symbol in dispatch_proof['ordinaryNamedPrototypeDeclarations'],
             'calculation-inline-same-named-comparison','fresh same ordinary prototype and selected named entry',comparison.symbol)
    offsets={}
    for key,qualified,typ in (('value',spec['valueField'],spec['scalarParameterType']),
                              ('applyScale',spec['applyScaleField'],'bool'),('scale',spec['scaleField'],spec['scalarParameterType'])):
        owner,actual,offset=selected.field(qualified)
        _require((owner,actual)==(spec['type'],typ),'calculation-inline-compatible-field-declaration',[spec['type'],typ],[owner,actual])
        require_ordinary_field(selected,qualified,typ,'calculationInline.'+key);offsets[key]=offset
    pointer=int(dispatch_proof['selectedSpans'][0][0],16)
    main_sizes=(5,5,1,4,3,3,5,3,5,3,5,3,7,7,7,3,2,2,5,5,2,6,8,3,4,3,5,4,3,8,6,8,3,6,3,5,5,4,5,4,5,3,1,1)
    main=partition(index.pe.bytes_at_va(pointer,188),pointer,main_sizes)
    providers={name:relative_branch_target(bytes.fromhex(main[n]['bytes']),int(main[n]['va'],16),source='calculationInlineProvider')
               for name,n in (('patch-call',19),('value-call',26))}
    _check_named_provider(index,providers['patch-call'],spec['patchMethod'],['int'],'bool',is_static=True)
    _check_named_provider(index,providers['value-call'],spec['doubleGetter'],[spec['scalarParameterType'],spec['blackboardType']],'double',is_static=True)
    edge=bytes.fromhex(main[30]['bytes']);edge_va=int(main[30]['va'],16)
    _require(len(edge)==6 and edge[:2]==bytes.fromhex('0f85'),'calculation-inline-scale-target','actual JNE near',edge.hex())
    cold_va=edge_va+6+int.from_bytes(edge[2:],'little',signed=True)
    cold=partition(index.pe.bytes_at_va(cold_va,34),cold_va,(4,3,3,5,3,3,4,4,5))
    providers['scale-call']=relative_branch_target(bytes.fromhex(cold[3]['bytes']),int(cold[3]['va'],16),source='calculationInlineScaleProvider')
    _check_named_provider(index,providers['scale-call'],spec['scalarGetter'],[spec['scalarParameterType'],spec['blackboardType']],'float',is_static=True)
    function_offset=dispatch_proof['actualFunctionCarrierDisplacement'];info_offset=dispatch_proof['actualInfoCarrierDisplacement']
    result=[]
    for scaled in (False,True):
        selected_cold=cold if scaled else []
        proof=check_inline_rows(main,selected_cold,pointer,offsets,providers,function_offset,info_offset,comparison.pointer,scaled)
        ranges=check_physical_coverage(index.extents,[main]+([cold] if scaled else []))
        for part in [main]+([cold] if scaled else []):
            raw=b''.join(bytes.fromhex(row['bytes']) for row in part);start=int(part[0]['va'],16)
            _require(index.pe.bytes_at_va(start,len(raw))==raw,'calculation-inline-raw-partition','complete independently selected raw bytes',hex(start))
        result.append({**proof,'symbol':dispatch_proof['symbol'],
            'claim':'calculationDefiniteEntryEqualScaledDoubleTimesWidenedSingleResult' if scaled else 'calculationDefiniteEntryEqualNoScaleDoubleBitsReturn',
            'selectedPhysicalPdataRanges':ranges,'compatibleFieldViewDeclaration':spec['type'],
            'typedFieldNames':[spec['valueField'],spec['applyScaleField']]+([spec['scaleField']] if scaled else []),
            'declaredRuntimeCarrierLayout':dispatch_proof['declaredRuntimeCarrierLayout'],
            'runtimeLayoutObserved':False,'managedSelectedUnwindFamilyProved':False,
            'evidenceTiers':{'exact':'independent helper inline control, actual normal getter low64 transfer/precision and full restoring RET',
                'direct':'actual comparison equals selected named DefiniteValue.Evaluate entry; actual named ordinary getters',
                'conditional':'typed field view requires compatible Definite receiver layout; pointer equality does not prove receiver type; runtime class/prototype/parity and normal preservation remain conditions'},
            'boundary':'The helper inline body is independently read and checked: equal selected named entry pointer, false ordinary patch result, selected actual applyScale byte and null incoming server reference reach complete helper frame/XMM6/XMM7 restore and RET. No-scale copies the named ordinary Double getter normal low64 unchanged; scaled requests the independent named Single getter, widens with CVTSS2SD then multiplies retained Double with MULSD before the same actual return. Typed value/applyScale/valueScale declarations require a compatible DefiniteValue field view; equality of a function pointer is not proof of the receiver runtime type. The fresh dispatch witness supplies the actual helper/compared entry and ordinary prototype only; the separate Definite method body is not used to prove this inline source, control or arithmetic. Original code and relevant storage unchanged, valid field/blackboard/frame/static storage, normal Win64 pre-dispatch/patch/getter saved-state preservation, compatible runtime class/prototype/parity and normal completion remain conditions; scaled arithmetic additionally depends on actual MXCSR rounding/DAZ/FTZ/exception environment. Default Single load is not a result operand on either selected path. Other patch/server paths, getter internals, helper managed identity, live values/subtype or final damage/Poise are not inferred.'})
    return result
