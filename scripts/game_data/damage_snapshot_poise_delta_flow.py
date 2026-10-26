"""Complete selected raw Poise delta returns and an explicit-ref caller request."""
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_delta_rows(rows, pointer, layout, add_id):
    _require(len(rows) == 47, 'poise-delta-count', 47, len(rows))
    raw = [bytes.fromhex(row['bytes']) for row in rows]
    at = pointer
    for row, data in zip(rows, raw):
        _require(int(row['va'], 16) == at, 'poise-delta-contiguous', hex(at), row['va'])
        at += len(data)
    direction = layout['directionDisplacement']; magnitude = layout['magnitudeDisplacement']
    _require(layout['directionWidthBytes'] == 4 and layout['magnitudeWidthBytes'] == 8,
             'poise-delta-read-widths', 'DWORD direction and eight-byte Double operand', layout)
    _require(type(direction) is int and type(magnitude) is int and 0 <= direction < 128 and 0 <= magnitude < 128,
             'poise-delta-displacements', 'reviewed nonnegative disp8', layout)
    exact = {0:'4053',1:'4883ec30',2:'488bd9',4:'83b9e000000000',6:'488b81b8000000',
        7:'488b10',8:'4885d2',12:'837b'+bytes([direction]).hex()+'00',14:'0f29742420',
        16:'f20f1073'+bytes([magnitude]).hex(),17:'83b9e000000000',19:'0f57c0',20:'660f2fc6',
        22:'b8'+int(add_id).to_bytes(4,'little',signed=True).hex(),23:'b9ffffffff',
        24:'3943'+bytes([direction]).hex(),25:'0f45c1',26:'660f6ec0',27:'f30fe6c0',28:'f20f59c6',
        29:'0f28742420',30:'4883c430',31:'5b',32:'c3',33:'0f57f6',40:'4883b900a9000000',
        43:'0f57c0',46:'cc'}
    for n, form in exact.items():
        _require(raw[n].hex() == form, 'poise-delta-instruction', [n,form], [n,raw[n].hex()])
    for n in (3,15,36):
        _require(len(raw[n]) == 7 and raw[n][:3] == bytes.fromhex('488b0d'),
                 'poise-delta-static-load', 'complete RIP qword load', raw[n].hex())
    _require(len(raw[10]) == 7 and raw[10][:3] == bytes.fromhex('817a18'),
             'poise-delta-anonymous-threshold', 'complete signed DWORD immediate compare', raw[10].hex())
    for n in (35,38,45):
        _require(len(raw[n]) == 5 and raw[n][0] == 0xe8, 'poise-delta-excluded-call', 'complete E8', raw[n].hex())
    edges = {}
    def branch(n, opcode, destination=None):
        data = raw[n]; width = 1 if len(opcode) == 1 and opcode != b'\xe9' else 4
        _require(len(data) == len(opcode)+width and data[:len(opcode)] == opcode,
                 'poise-delta-branch-encoding', [n,opcode.hex(),width], data.hex())
        target = int(rows[n]['va'],16)+len(data)+int.from_bytes(data[len(opcode):],'little',signed=True)
        if destination is not None:
            _require(target == int(rows[destination]['va'],16), 'poise-delta-branch-target', destination, hex(target))
        else:
            _require(not pointer <= target < at, 'poise-delta-excluded-external', 'outside entry extent', hex(target))
        edges[str(n)] = hex(target)
    for n, op, dest in ((5,b'\x74',35),(9,b'\x0f\x84',45),(11,b'\x0f\x8f',None),
        (13,b'\x74',43),(18,b'\x74',38),(21,b'\x77',33),(34,b'\xeb',22),
        (37,b'\xe9',6),(39,b'\xeb',19),(41,b'\x74',12),(42,b'\xe9',None),(44,b'\xeb',30)):
        branch(n,op,dest)
    return {'selectedEntryExtent':[hex(pointer),hex(at)],'actualEdges':edges,
        'anonymousSignedThreshold':int.from_bytes(raw[10][3:],'little',signed=True),
        'frameDeltaBytes':56,'normalRetStackDeltaBytes':8,
        'rawDirectionDisplacement':direction,'rawMagnitudeDisplacement':magnitude,
        'returnedRegister':'xmm0.low64','floatingDirectionConversion':'CMOVNE EAX,ECX -> MOVD XMM0,EAX -> CVTDQ2PD XMM0,XMM0 low Double lane',
        'ordinaryFalseIFixCallProved':False,'allAlternatePathsProved':False}


def check_caller_rows(rows, getter_pointer):
    from scripts.game_data.il2cpp.context import relative_branch_target
    _require(len(rows) == 9, 'poise-delta-caller-count', 9, len(rows))
    at = int(rows[0]['va'],16); start = at; targets = {}
    forms = ('33d2','498bce','getter','0f57d2','f20f5ad0','f30f58d6','b95b000000','488bd7','opaque')
    for row, form in zip(rows,forms):
        data=bytes.fromhex(row['bytes'])
        _require(int(row['va'],16)==at,'poise-delta-caller-contiguous',hex(at),row['va'])
        if form in ('getter','opaque'):
            target=relative_branch_target(data,at,source='poiseDeltaCaller')
            _require(data[0]==0xe8,'poise-delta-caller-direct-call','E8',data.hex())
            if form=='getter':_require(target==getter_pointer,'poise-delta-caller-same-getter',hex(getter_pointer),hex(target))
            targets[form]=hex(target)
        else:_require(data.hex()==form,'poise-delta-caller-instruction',form,data.hex())
        at+=len(data)
    return {'selectedCallerSpan':[hex(start),hex(at)],'actualCalls':targets,
        'getterReceiverCarrier':'retained r14 -> rcx','operationOrder':'normal Double XMM0 -> CVTSD2SS XMM2 -> ADDSS XMM2,XMM6 -> actual opaque setter-helper request',
        'wholeCallerControlOrReturnProved':False,'runtimeVirtualAccessorTargetProved':False,'appliedPoiseProved':False}


def check_poise_delta(index, spec):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_field, require_ordinary_int32_enum, require_ordinary_type
    from scripts.game_data.damage_snapshot_append_flow import _check_named_provider
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.protocol import native_enum_members
    selected=NativeReferenceContext(index.image,index=index)
    body=index.body(spec['type'],spec['method']); owner=index.types[spec['type']]
    _require(selected.is_value_type(spec['type']), 'poise-delta-value-owner', 'selected value definition', spec['type'])
    _check_named_provider(index,body.pointer,body.symbol,[],'double',is_static=False)
    actual_fields={}
    for name,qualified,typ in (('direction',spec['directionField'],spec['directionEnum']),('magnitude',spec['valueField'],'double')):
        field_owner,field_type,offset=selected.field(qualified)
        _require((field_owner,field_type)==(spec['type'],typ),'poise-delta-field-owner',[spec['type'],typ],[field_owner,field_type])
        fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==qualified.split('::',1)[1]]
        _require(len(fields)==1,'poise-delta-field-count',1,len(fields))
        if name=='direction':require_ordinary_int32_enum(selected,fields[0].type_index,typ,'poiseDelta.direction')
        else:require_ordinary_field(selected,qualified,typ,'poiseDelta.magnitude')
        actual_fields[name]=offset
    adjustment=spec['conditionalTypedView']['boxedValueHeaderAdjustmentBytes']
    _require(spec['conditionalTypedView']['independentlyProved'] is False and type(adjustment) is int and adjustment>=0,
             'poise-delta-header-condition','explicit unproved reviewed nonnegative adjustment',spec['conditionalTypedView'])
    _require(actual_fields=={'direction':spec['rawNumericalLayout']['directionDisplacement']+adjustment,
        'magnitude':spec['rawNumericalLayout']['magnitudeDisplacement']+adjustment},
        'poise-delta-conditional-view-arithmetic','declared conditional adjustment matches fresh metadata',actual_fields)
    members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,spec['directionEnum'])
    additions=[m['id'] for m in members if m['name']==spec['selectedCompareMember']]
    _require(len(additions)==1 and additions[0]==1,'poise-delta-direction-coefficient','fresh named Add id equals actual positive integer multiplier one',additions)
    _require(body.size==spec['entryExtentBytes'],'poise-delta-entry-extent',spec['entryExtentBytes'],body.size)
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    proof=check_delta_rows(rows,body.pointer,spec['rawNumericalLayout'],additions[0])
    ranges=check_physical_coverage(index.extents,[rows])
    common={**proof,'symbol':body.symbol,'selectedPhysicalPdataRanges':ranges,
        'allDirectionEnumMembers':members,'boxedMetadataFieldOffsets':actual_fields,
        'boxedToRawStorageAdjustmentIndependentlyProved':False,'typedFieldViewTier':'conditional',
        'rawNumericalTier':'exact','runtimeDirectionOrValueObserved':False,
        'boundary':'Exact selected raw numerical/control/frame/normal XMM0 low-Double return. Named ordinary Double/Int32 enum declarations are independently checked; raw receiver storage is interpreted as those fields only under the declared compatible unboxed/header view assumption. Anonymous static readiness/carrier/null/signed-threshold predicates select the paths; no ordinary false IsPatched call is inferred. Valid original receiver/static/save/frame/return storage, original code unchanged and no interfering writes are conditions. COMISD predicates use actual flags; floating exceptions, DAZ/FTZ and rounding environment and normal execution remain conditions. No other initializer/diversion/throw paths, live field value, upper SIMD meaning or applied Poise is proved.'}
    result=[]
    for claim,indices,rule in (
        ('poiseModifierRawZeroDirectionPositiveZero',list(range(14))+[43,44,30,31,32], 'raw direction == 0: XORPS XMM0 returns positive-zero without reading magnitude or saving XMM6'),
        ('poiseModifierRawNonzeroDirectionRetainedMagnitude',list(range(33)), 'raw direction != 0 and COMISD JA not taken: retained raw Double magnitude multiplied by low Double direction +1 when raw direction == Add, -1 otherwise'),
        ('poiseModifierRawOrderedNegativeClearedMagnitude',list(range(22))+[33,34]+list(range(22,33)), 'raw direction != 0 and COMISD CF=0/ZF=0: XORPS XMM6 clears magnitude to +0 then applies direction multiplier; returned zero sign is not simplified')):
        result.append({**common,'claim':claim,'selectedInstructionIndices':indices,'numericalRule':rule})
    caller_spec=spec['callerBoundedRequest']; caller=index.body(caller_spec['type'],caller_spec['method'])
    _require(caller_spec['referenceTypeKind']==0x11 and caller_spec['referenceFlags']==0x20,
             'poise-delta-explicit-ref-kind', 'value kind with reference flag only, no pinned/ordinary marker', caller_spec)
    definitions=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(caller.pointer,())
        if f"{n.get('type')}.{n.get('method')}"==caller.symbol]
    _require(bool(definitions),'poise-delta-caller-definition','fresh named caller',caller.symbol)
    for method in definitions:
        params=list(index.metadata.parameters_for(method))
        _require(not method.flags&0x10 and len(params)==1 and index.metadata.string(params[0].name_index)==caller_spec['parameter'],
                 'poise-delta-caller-signature','instance one modifier parameter',method.flags)
        require_ordinary_type(selected,method.return_type,'void','poiseDelta.caller.return')
        pointer=selected.type_pointer(params[0].type_index); record=index.pe.bytes_at_va(pointer,16)
        _require(len(record)==16 and selected.type_name(params[0].type_index)==spec['type']
            and record[10]==caller_spec['referenceTypeKind'] and record[11]==caller_spec['referenceFlags']
            and int.from_bytes(record[:8],'little')==owner.index,
            'poise-delta-caller-explicit-ref-record','selected same concrete owner value record with exact reviewed reference flags',record.hex())
        _require(index.parameter_location(caller.pointer,caller.symbol,caller_spec['parameter'])==('register','rdx'),
                 'poise-delta-caller-ref-location','rdx',index.parameter_location(caller.pointer,caller.symbol,caller_spec['parameter']))
    size=caller_spec['requestBytes']; raw=index.pe.bytes_at_va(caller.pointer,caller.size)
    signature=bytes.fromhex('33d2498bce'); candidates=[n for n in range(len(raw)-size+1) if raw[n:n+5]==signature
        and raw[n+5]==0xe8 and caller.pointer+n+10+int.from_bytes(raw[n+6:n+10],'little',signed=True)==body.pointer
        and raw[n+10:n+21]==bytes.fromhex('0f57d2f20f5ad0f30f58d6')]
    _require(len(candidates)==1,'poise-delta-caller-selection','unique actual named-getter numerical request',candidates)
    at=caller.pointer+candidates[0]; request=partition(index.pe.bytes_at_va(at,size),at,(2,3,5,3,4,4,5,3,5))
    result.append({**check_caller_rows(request,body.pointer),'symbol':caller.symbol,'claim':'poiseModifierExplicitRefGetterToSingleSetterRequest',
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[request]),
        'selectedModifierReferenceFlags':caller_spec['referenceFlags'],'ordinaryByvalueModifierParameterProved':False,
        'boundary':'Direct bounded caller request to the freshly named ordinary Double getter, through CVTSD2SS then ADDSS and the actual opaque setter-helper request. Selected explicit-reference value record and same concrete Modifier definition are checked without stripping flags. R14 is assumed to retain valid incoming Modifier value storage at this fragment; full caller entry/control/frame continuity and prior XMM6 Single getter origin are not proved. Normal getter/callee ABI and saved-state/frame/storage noninterference, compatible reference ABI/storage and floating environment are conditions. Getter typed field view retains its independent header/storage condition. No concrete virtual getter/setter target, complete caller return, resulting entity state or applied Poise is inferred.'})
    return result
