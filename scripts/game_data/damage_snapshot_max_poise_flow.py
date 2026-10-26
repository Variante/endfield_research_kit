"""Named MaxPoise attribute request, normal narrowing and setter input carry."""
from scripts.game_data.damage_snapshot_cache_flow import _require


def check_reference_definition(selected, type_index, name, owner_index, role):
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type
    proof=require_ordinary_type(selected,type_index,name,role,reference_kind=0x12)
    raw=selected.image.pe.bytes_at_va(selected.type_pointer(type_index),16)
    _require(len(raw)==16 and int.from_bytes(raw[:8],'little')==owner_index,
             'max-poise-reference-definition',[role,owner_index],[role,raw.hex()])
    return {**proof,'concreteDefinitionIndex':owner_index}


def check_source_rows(rows, pointer, attributes_offset, enum_id, provider_pointer):
    from scripts.game_data.il2cpp.context import relative_branch_target
    _require(len(rows)==45,'max-poise-row-count',45,len(rows))
    raw=[bytes.fromhex(x['bytes']) for x in rows];at=pointer
    for row,b in zip(rows,raw):
        _require(int(row['va'],16)==at,'max-poise-contiguous',hex(at),row['va']);at+=len(b)
    _require(type(attributes_offset) is int and 0<=attributes_offset<2**31,
             'max-poise-attributes-displacement','nonnegative disp32',attributes_offset)
    exact={0:'4053',1:'4883ec20',2:'488bd9',4:'83b9e000000000',6:'488b81b8000000',7:'488b10',8:'4885d2',
        12:'83b9e000000000',14:'488b81b8000000',15:'488b10',16:'4885d2',
        20:'488b83'+attributes_offset.to_bytes(4,'little').hex(),21:'4885c0',23:'4533c0',
        24:'ba'+enum_id.to_bytes(4,'little',signed=True).hex(),25:'488bc8',27:'f20f5ac0',
        28:'4883c420',29:'5b',30:'c3',37:'4883ba3077000000',40:'4883b90070000000',44:'cc'}
    for n,form in exact.items():_require(raw[n].hex()==form,'max-poise-instruction',[n,form],[n,raw[n].hex()])
    for n in (3,32,35):_require(len(raw[n])==7 and raw[n][:3]==bytes.fromhex('488b0d'),'max-poise-static-load','complete RIP qword load',raw[n].hex())
    for n in (10,18):_require(len(raw[n])==7 and raw[n][:3]==bytes.fromhex('817a18'),'max-poise-signed-threshold','complete anonymous signed DWORD compare',raw[n].hex())
    for n in (26,31,34,43):_require(len(raw[n])==5 and raw[n][0]==0xe8,'max-poise-call','complete E8',raw[n].hex())
    target=relative_branch_target(raw[26],int(rows[26]['va'],16),source='maxPoiseProvider')
    _require(target==provider_pointer,'max-poise-provider-target',hex(provider_pointer),hex(target))
    edges={}
    for n,op,dest in ((5,b'\x74',31),(9,b'\x0f\x84',43),(11,b'\x0f\x8f',None),
        (13,b'\x74',34),(17,b'\x74',43),(19,b'\x0f\x8f',None),(22,b'\x74',43),
        (33,b'\xeb',6),(36,b'\xeb',14),(38,b'\x74',12),(39,b'\xe9',None),(41,b'\x74',20),(42,b'\xe9',None)):
        b=raw[n];width=4 if len(op)==2 or op==b'\xe9' else 1
        _require(len(b)==len(op)+width and b[:len(op)]==op,'max-poise-branch-encoding',[n,op.hex()],b.hex())
        destination=int(rows[n]['va'],16)+len(b)+int.from_bytes(b[len(op):],'little',signed=True)
        _require(destination==int(rows[dest]['va'],16) if dest is not None else not pointer<=destination<at,
                 'max-poise-branch-target',dest,hex(destination));edges[str(n)]=hex(destination)
    return {'selectedEntryExtent':[hex(pointer),hex(at)],'selectedNormalReturnSpan':[hex(pointer),rows[31]['va']],
        'selectedInstructionIndices':list(range(31)),'actualEdges':edges,'actualProviderEntry':hex(target),
        'anonymousSignedThresholds':[int.from_bytes(raw[n][3:],'little',signed=True) for n in (10,18)],
        'frameDeltaBytes':40,'normalRetStackDeltaBytes':8,'actualEnumInt32':enum_id,
        'operationOrder':'typed attributes reference -> native enum Int32 request -> normal ordinary Double XMM0.low64 -> CVTSD2SS -> Single XMM0.low32 -> full RBX/frame RET',
        'ordinaryFalseIsPatchedCallProved':False,'allSourceValueProductionOrCachedPathsProved':False,
        'liveMaxPoiseObserved':False,'allOtherGetterPathsProved':False}


def check_setter_carry(rows, getter_pointer, opaque_pointer):
    from scripts.game_data.il2cpp.context import relative_branch_target
    _require(len(rows)==12,'max-poise-setter-carry-count',12,len(rows))
    forms=('33d2','488bcb','getter','488b0d','0f28f0','83b9e000000000','ready-edge','4c8b0d','0f28d6','0f57c9','0f28c7','opaque')
    start=int(rows[0]['va'],16);at=start;excluded=None
    for row,form in zip(rows,forms):
        b=bytes.fromhex(row['bytes']);_require(int(row['va'],16)==at,'max-poise-setter-carry-contiguous',hex(at),row['va'])
        if form in ('getter','opaque'):
            _require(len(b)==5 and b[0]==0xe8,'max-poise-setter-carry-call','complete E8',b.hex())
            target=relative_branch_target(b,at,source='maxPoiseSetterCarry')
            _require(target==(getter_pointer if form=='getter' else opaque_pointer),'max-poise-setter-carry-target',form,hex(target))
        elif form=='ready-edge':
            _require(len(b)==2 and b[0]==0x74,'max-poise-setter-carry-ready','JE excluded initializer',b.hex())
            excluded=at+2+int.from_bytes(b[1:],'little',signed=True)
        elif form in ('488b0d','4c8b0d'):
            _require(len(b)==7 and b[:3].hex()==form,'max-poise-setter-carry-rip',form,b.hex())
        else:_require(b.hex()==form,'max-poise-setter-carry-instruction',form,b.hex())
        at+=len(b)
    _require(excluded is not None and not start<=excluded<at,'max-poise-setter-carry-excluded','outside carry span',excluded)
    return {'selectedCallerRequestSpan':[hex(start),hex(at)],'getterEntry':hex(getter_pointer),'actualOpaqueRequestEntry':hex(opaque_pointer),
        'forwarding':'normal get_maxPoise Single XMM0.low32 -> MOVAPS XMM6 -> MOVAPS XMM2 -> actual anonymous request input carrier',
        'candidateQEqualsGetterSourceProved':False,'opaqueUpperBoundOrClampSemanticsProved':False}


def check_max_poise(index, setter_proof, spec):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.context import relative_branch_target
    from scripts.game_data.il2cpp.protocol import native_enum_members
    from scripts.game_data.damage_snapshot_abi import require_ordinary_type,require_ordinary_int32_enum
    from scripts.game_data.damage_snapshot_primary_attr_flow import partition
    from scripts.game_data.damage_snapshot_atk_scale_flow import check_physical_coverage
    selected=NativeReferenceContext(index.image,index=index);body=index.body(spec['type'],spec['method'])
    owner=index.types[spec['type']];attrs=index.types[spec['attributesType']];enum=index.types[spec['attributeEnum']]
    receiver=check_reference_definition(selected,owner.byval_type_index,spec['type'],owner.index,'maxPoise.receiver')
    getter_defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(body.pointer,())
        if f"{n.get('type')}.{n.get('method')}"==body.symbol]
    _require(bool(getter_defs),'max-poise-getter-definition','fresh named getter',body.symbol)
    for m in getter_defs:
        _require(m.declaring_type==owner.index and not m.flags&0x10 and len(index.metadata.parameters_for(m))==0,
                 'max-poise-getter-concrete-owner',[owner.index,'ordinary instance zero parameters'],m.declaring_type)
        require_ordinary_type(selected,m.return_type,'float','maxPoise.getter.return')
    field_owner,field_type,offset=selected.field(spec['attributesField'])
    _require((field_owner,field_type)==(spec['type'],spec['attributesType']),'max-poise-field-owner',
             [spec['type'],spec['attributesType']],[field_owner,field_type])
    fields=[f for f in index.metadata.fields_for(owner) if index.metadata.string(f.name_index)==spec['attributesField'].split('::',1)[1]]
    _require(len(fields)==1,'max-poise-field-count',1,len(fields))
    attributes=check_reference_definition(selected,fields[0].type_index,spec['attributesType'],attrs.index,'maxPoise.attributes')
    _require(body.size==spec['entryExtentBytes'],'max-poise-entry-extent',spec['entryExtentBytes'],body.size)
    rows=partition(index.pe.bytes_at_va(body.pointer,body.size),body.pointer,spec['entryInstructionLengths'])
    pointer=relative_branch_target(bytes.fromhex(rows[26]['bytes']),int(rows[26]['va'],16),source='maxPoiseGetValue')
    provider_defs=[index.metadata.methods[n['methodIndex']] for n in index.names_by_pointer.get(pointer,())
        if f"{n.get('type')}.{n.get('method')}"==spec['providerMethod']]
    _require(bool(provider_defs),'max-poise-provider-definition','fresh direct named Attributes.GetValue',hex(pointer))
    for m in provider_defs:
        params=list(index.metadata.parameters_for(m))
        _require(m.declaring_type==attrs.index and not m.flags&0x10 and len(params)==1,
                 'max-poise-provider-concrete-owner',[attrs.index,'instance single enum parameter'],m.declaring_type)
        require_ordinary_int32_enum(selected,params[0].type_index,spec['attributeEnum'],'maxPoise.enumFormal')
        record=index.pe.bytes_at_va(selected.type_pointer(params[0].type_index),16)
        _require(len(record)==16 and int.from_bytes(record[:8],'little')==enum.index,
                 'max-poise-enum-concrete-definition',enum.index,record.hex())
        require_ordinary_type(selected,m.return_type,'double','maxPoise.provider.return')
        parameter=index.metadata.string(params[0].name_index)
        _require(index.parameter_location(pointer,spec['providerMethod'],parameter)==('register','rdx'),
                 'max-poise-enum-argument-slot','rdx low32',index.parameter_location(pointer,spec['providerMethod'],parameter))
    members=native_enum_members(index.metadata,index.enum_defaults,index.pe,index.image.registration,spec['attributeEnum'])
    ids=[m['id'] for m in members if m['name']==spec['attributeMember']]
    _require(len(ids)==1,'max-poise-native-enum-member',1,len(ids))
    proof=check_source_rows(rows,body.pointer,offset,ids[0],pointer)
    source={**proof,'symbol':body.symbol,'claim':'maxPoiseTypedAttributeRequestDoubleToSingleNormalReturn',
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[rows]),
        'typedAttributesField':spec['attributesField'],'nativeAttributeAliases':[m for m in members if m['id']==ids[0]],
        'receiverDefinition':receiver,'attributesDefinition':attributes,'providerConcreteDefinitionIndex':attrs.index,'enumConcreteDefinitionIndex':enum.index,
        'boundary':'Complete selected named getter entry-to-RET with anonymous dual static readiness/carrier/null/signed-threshold guards and nonnull typed m_attributes. Same selected-image receiver/field/provider concrete class indices and enum definition, ordinary Int32 enum and Double/Single ABI, actual direct provider target, native MaxPoise ID/all same-ID aliases, CVTSD2SS and full frame/RBX return are checked. No ordinary false IsPatched call is inferred from anonymous guards. Attributes.GetValue internals, cached/recompute path selection and actual Double value remain open; it is a typed named request and normal-return precision boundary. Original code unchanged, valid compatible receiver/attributes/class/frame/return storage, normal Win64 callee/saved-state/storage noninterference and actual floating environment/normal conversion are conditions. No live attribute value, runtime invocation/subtype, other initializer/diversion/throw paths or applied/displayed amount is recovered.'}
    _require(setter_proof.get('claim') in ('poiseSetterSelectedPostCallCarrierTypedLocalWrite','poiseSetterSelectedPostCallCarrierNoLocalWrite'),
             'max-poise-fresh-setter','fresh setter normal path witness',setter_proof.get('claim'))
    _require(setter_proof['actualCalls']['maxPoise']==hex(body.pointer),'max-poise-same-getter-entry',hex(body.pointer),setter_proof['actualCalls']['maxPoise'])
    caller=index.body(spec['callerType'],spec['callerMethod']);at=caller.pointer+spec['callerRequestOffset']
    _require(setter_proof['symbol']==caller.symbol and int(setter_proof['selectedEntryExtent'][0],16)==caller.pointer,
             'max-poise-same-setter-body','fresh same named setter entry',setter_proof.get('symbol'))
    request=partition(index.pe.bytes_at_va(at,spec['callerRequestBytes']),at,spec['callerRequestLengths'])
    carry=check_setter_carry(request,body.pointer,int(setter_proof['actualCalls']['opaqueCandidate'],16))
    return [source,{**carry,'symbol':caller.symbol,'claim':'maxPoiseSingleNormalResultToSetterOpaqueRequestCarrier',
        'selectedPhysicalPdataRanges':check_physical_coverage(index.extents,[request]),
        'sourceNormalReturnClaim':source['claim'],'setterNormalReturnClaim':setter_proof['claim'],
        'boundary':'Fresh complete getter normal Single XMM0.low32 source is connected to the same actual named call in a fresh complete selected setter path, then MOVAPS retains it in XMM6 and transfers low32 into XMM2 for the actual anonymous request. Anonymous readiness nonzero excludes the initializer call; source/caller concrete identity, target and register/control transfers are checked independently. Normal getter and Win64 saved-state/frame/storage preservation, compatible receiver/context/value carriers and actual source floating conversion conditions remain. Other SIMD lanes have no asserted typed meaning. Anonymous helper managed prototype and upper-bound/Clamp/min/max semantics are not proved, and its post-call candidate q is not identified with this input value. No actual live MaxPoise or applied/displayed result follows.'}]
