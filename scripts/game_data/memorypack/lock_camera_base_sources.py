"""Selected actual LockCamera generic-base constructor effects.

No open generic field offset or registered closed-entry identity is used by
this byte program. Its field offsets are observed effects only. A caller must
independently join the actual closed MethodInfo, named accessors and nominal
child constructors before using these effects as a complete record source.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='lockCameraBaseSource'
DEFINITION='Beyond.Gameplay.Core.LockCameraAimBaseAction`1+LockCameraAimBaseActionData'
DERIVED_TYPES=('Beyond.Gameplay.Core.LockCameraAimAction+LockCameraAimActionData',
    'Beyond.Gameplay.Core.LockCameraMultiAimAction+LockCameraMultiAimActionData')


def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:600])


def _constant(g):
    at=g.at;head=bytes(g.bytes.get(at+i,0)for i in range(2))
    need('literal-owned-receiver-default',head in(bytes.fromhex('c743'),bytes.fromhex('c783'),bytes.fromhex('c643')))
    g.take(head.hex());offset=int.from_bytes(g.read(4 if head==bytes.fromhex('c783')else 1),'little',signed=True)
    width=1 if head==bytes.fromhex('c643')else 4;value=g.read(width)
    need('positive-effect-offset',16<=offset<2**31)
    return dict(instructionVa=at,offset=offset,bytes=width,constantHex=value.hex().upper())


def _address(g,operation):
    at=g.at;head=bytes(g.bytes.get(at+i,0)for i in range(3))
    forms=(bytes.fromhex('488d4b'),bytes.fromhex('488d8b'))if operation=='address'else(bytes.fromhex('48897b'),bytes.fromhex('4889bb'))
    need('same-whole-owned-receiver-address',head in forms)
    g.take(head.hex());offset=int.from_bytes(g.read(1 if head==forms[0]else 4),'little',signed=True)
    need('positive-reference-effect-offset',16<=offset<2**31)
    return at,offset


def constructor_program(regions,entry,*,allocator,blackboard_constructor,barrier):
    """Own normal frame/default writes and all five typed allocation effects."""
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    need('literal-current-helpers',all(type(n)is int and n>0 for n in(allocator,blackboard_constructor,barrier)))
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30')
    flag=g.relative('803d')+1;g.take('00','488bd9');g.branch('0f84',False)
    constants=[_constant(g)for _ in range(5)];allocations=[];constant_cell=None
    for ordinal in range(5):
        at=g.at;cell=g.relative('488b0d')
        if ordinal==0:g.take('0f29742420')
        call=g.at;g.call(allocator);g.take('488bf8','4885c0');null=_nonnull(g)
        if ordinal==0:constant_cell=g.relative('f30f1035')
        g.take('4533c0','0f28ce','488bc8');ctor_call=g.at;g.call(blackboard_constructor)
        address,offset=_address(g,'address');store,stored_offset=_address(g,'store')
        need('same-whole-reference-and-barrier-field',offset==stored_offset)
        g.call(barrier)
        allocations.append(dict(classInstructionVa=at,classCellVa=cell,allocationCallVa=call,
            constructorCallVa=ctor_call,referenceAddressVa=address,referenceStoreVa=store,offset=offset,
            storedBytes=8,sourceRegister='rdi',sameAllocatedReferenceStored=True,ownedNullExit=null))
        if ordinal in(1,2,3):constants.append(_constant(g))
    g.take('0f28742420');constants.extend(_constant(g)for _ in range(6))
    g.take('488b5c2440','4883c430','5f','c3')
    ranges=[set(range(s['offset'],s['offset']+s['bytes']))for s in constants]
    ranges+=[set(range(s['offset'],s['offset']+8))for s in allocations]
    need('each-observed-write-has-disjoint-destination',sum(map(len,ranges))==len(set().union(*ranges)))
    need('one-current-child-allocation-class',len({a['classCellVa']for a in allocations})==1)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constantStores=constants,referenceAllocations=allocations,
        floatingArgumentCellVa=constant_cell,childConstructorFloatArgumentRegister='xmm1',
        allocatorTarget=allocator,childConstructorTarget=blackboard_constructor,barrierTarget=barrier,
        sameWholeReceiverInRbx=True,allReferenceArgumentsUseSameCurrentFloatBits=True,
        incomingMethodInfoRead=False,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi','xmm6'],
        normalReturn=True,metadataInitializationAdmitted=False,registeredClosedEntryIdentityClaimed=False,
        openGenericFieldOffsetsUsed=False,closedFieldOwnershipAdmitted=False,childGrammarAdmitted=False,
        wholeOwnerAdmitted=False,
        condition='Selected initialized constructor path, normal successful allocations and named child constructor calls, independently disabled barriers. Every recorded destination is an actual compiled store effect; closed nominal field ownership and child constructor semantics remain separate. Incoming RDX MethodInfo is never read by this selected program, and no registered closed method pointer equality is inferred.')


def derive_accessors(image,pins,*,type_name):
    """Fresh declaration/carrier/getter joins for actual named accessor effects.

    The returned offset source is the complete compiled property implementation,
    never an offset or size from the open definition. Full reader/lifecycle,
    construction and wire admission remain explicit independent obligations.
    """
    import json
    import re
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.reference_field_programs import prove_cached_field_setter
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_cached_initial24_sources import program as initial_setter
    from scripts.game_data.memorypack.skill_camera_initial_raw_sources import layout as initial_layout
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins);need('finite-concrete-derived-type',type_name in DERIVED_TYPES)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==type_name]
    own=ctx.index.types[type_name];parent=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(own.parent_index))
    need('same-closed-reference-parent',parent['definitionTypeIndex']==ctx.index.types[DEFINITION].index
        and parent['argumentTypes']==[type_name]and parent['bytes']==8)
    base_wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==ctx.parent(wrapper.name)]
    need('same-actual-closed-wrapper-parent',base_wrapper.wrapped_type==parent['type']and not base_wrapper.wrapped_is_value_type)
    cache=ctx.field(base_wrapper.name+'::__realInstance')
    need('exact-current-closed-cache-holder',cache==(base_wrapper.name,parent['type'],24))
    holder_fields=[f for f in md.fields_for(md.types[base_wrapper.type_definition])if md.string(f.name_index)=='__realInstance']
    need('one-current-closed-holder-declaration',len(holder_fields)==1)
    holder_carrier=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(holder_fields[0].type_index))
    need('same-fresh-closed-holder-carrier',holder_carrier['type']==parent['type']and
        holder_carrier['definitionTypeRecordHex']==parent['definitionTypeRecordHex']and holder_carrier['argumentTypes']==[type_name])
    base_holders=[];ancestor=ctx.parent(base_wrapper.name);visited=set()
    while ancestor not in('','object','System.Object'):
        need('bounded-owned-wrapper-ancestry',ancestor not in visited and len(visited)<16);visited.add(ancestor)
        for field in md.fields_for(ctx.index.types[ancestor]):
            name=md.string(field.name_index)
            if name in('___instance','__instance')and not ctx.field_attributes(field.type_index)&16:
                scalar.ordinary(image,ctx.type_pointer(field.type_index),18,LABEL+'.baseHolder',reference=True)
                base_holders.append(ctx.field(ancestor+'::'+name))
        ancestor=ctx.parent(ancestor)
    need('one-actual-closed-base-holder',len(base_holders)==1 and base_holders[0][2]==16
        and base_holders[0][1]==ctx.parent(DEFINITION))
    getter=pointer.methods(image,base_wrapper)['get___instance']
    scalar.owned_method_abi(image,ctx,getter.index,base_wrapper.type_definition,(parent['type'],21,True),[],LABEL+'.closedGetter')
    returned=closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(getter.return_type))
    need('same-fresh-closed-getter-return',returned==parent)
    body=members._body(image,image.method_pointer_va(getter),pins=pins)
    warm_programs=[]
    for mode in('rbx','rdi'):
        try:warm_programs.append(members.coherent_getter_program(body['regions'],body['pointer'],base_slot=16,cache_slot=24,mode=mode))
        except(ValueError,KeyError,IndexError):pass
    need('one-current-closed-coherent-getter',len(warm_programs)==1)
    warm=warm_programs[0]
    barrier_targets=[members.control_transfer(r)['target']for i,r in enumerate(body['rows'])if i and
        body['rows'][i-1]['text']in('lea rcx, [rbx+0x18]','lea rcx, [rdi+0x18]')and members.control_transfer(r)['kind']=='call']
    need('one-current-reference-barrier',len(barrier_targets)==1);barrier=barrier_targets[0]
    collector=_barrier(image,barrier)
    refresh=members._getter_refresh(image,body,base_slot=16,cache_slot=24,original=parent['type'],barrier=barrier)
    need('both-refresh-class-records-equal-closed-carrier',all(
        u.get('typeRawHex')==parent['declaredTypeRecordHex']for p in refresh['programs']for u in p['classUsages']))
    selected=[m for m in wrapper.members if m.declaring_wrapper==base_wrapper.name]
    definition=md.types[parent['definitionTypeIndex']]
    fields={md.string(f.name_index):f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16}
    need('all-closed-base-declarations-have-one-current-accessor',len(fields)==len(selected)==36 and
        {m.name for m in selected}==set(fields))
    records=[];occupied=set()
    for member in selected:
        field=fields[member.name];declared=ctx.type_name(field.type_index)
        need('same-unmodified-nonvariable-field-declaration',declared==member.declared_type and
            not any(marker in declared for marker in('VAR[','MVAR[','<generic-','<unresolved')))
        method=md.methods[member.method_index];parameter,=md.parameters_for(method)
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);kind=raw[10]
        reference=kind in(14,18,20,29)or kind==21 and not raw[11]&128
        scalar.owned_method_abi(image,ctx,method.index,base_wrapper.type_definition,('void',1,False),
            [(declared,kind,reference)],LABEL+'.closedProperty')
        need('nongeneric-own-property-method',method.generic_container_index<0)
        scalar.ordinary(image,ctx.type_pointer(field.type_index),kind,LABEL+'.closedDeclaration',reference=reference)
        native=members._body(image,image.method_pointer_va(method),pins=pins);rows=native['rows']
        if declared=='Beyond.Gameplay.View.CameraControlStateInitialParam':
            candidates=[int(m[1],16)for r in rows if(m:=re.fullmatch(r'movups \[rax\+0x([0-9a-f]+)\], xmm0',r['text']))]
            need('one-observed-Initial24-effect-offset',len(candidates)==1)
            offset=candidates[0];program=initial_setter(native['regions'],native['pointer'],getter=body['pointer'],field=offset)
            width=24;mode='owned-initial-value-pointer24';value_layout=initial_layout(image,ctx)
        else:
            candidates=[int(m[1],16)for r in rows if(m:=re.fullmatch(r'(?:mov|movss) \[rax\+0x([0-9a-f]+)\], (?:bl|ebx|rbx|xmm6)',r['text']))]
            need('one-observed-property-effect-offset',len(candidates)==1,(member.name,candidates));offset=candidates[0]
            if kind==2:mode='normalized-byte-return';width=1
            elif kind==12:mode='single-return';width=4
            elif kind==8:mode='int32-return';width=4
            elif kind==17:
                need('owned-int32-enum-property',ctx.is_enum(declared))
                td=ctx.index.types[declared];backing,=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
                need('own-enum-int32-backing',md.string(backing.name_index)=='value__'and ctx.type_name(backing.type_index)=='int')
                scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,LABEL+'.closedEnumBacking')
                mode='int32-return';width=4
            else:
                need('finite-reference-property',reference)
                if kind==21:closed_generic_reference_pointer_extent(ctx,ctx.type_pointer(parameter.type_index))
                mode='reference-return';width=8
            calls=[members.control_transfer(r)['target']for r in rows if members.control_transfer(r)['kind']=='call']
            nulls=[n for n in calls if n!=body['pointer']]
            need('same-actual-getter-and-owned-null-exit',calls.count(body['pointer'])==1 and len(nulls)==1)
            symbols=dict(getter=body['pointer'],nullThrow=nulls[0])
            if reference:symbols['barrier']=barrier
            program=prove_cached_field_setter(rows,field_offset=offset,mode=mode,symbols=symbols)
            value_layout=None
        span=set(range(offset,offset+width));need('closed-property-effects-disjoint',offset>=16 and not occupied&span)
        occupied|=span
        records.append(dict(member=member.row(),declaredField=dict(ownerDefinition=DEFINITION,name=member.name,typeName=declared,
                typeRecordHex=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16).hex().upper()),
            method=[method.index,base_wrapper.name,md.string(method.name_index),native['pointer']-base],
            actualEffectOffset=offset,storedBytes=width,parameterTypeRecordHex=raw.hex().upper(),mode=mode,
            family=native['family'],codeWindows=native['windows'],program=program,
            nominalValueLayout=value_layout,openGenericFieldOffsetUsed=False,
            offsetSource='complete actual named compiled property; open declaration offset unused'))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.lock-camera-closed-accessor-effects.v1',
        status='validated-conditional-closed-accessor-effects',nativeInputs=pins,typeName=type_name,wrapperName=wrapper.name,
        closedParent=parent,closedCacheHolder=cache,baseHolder=base_holders[0],baseWrapperName=base_wrapper.name,holderCarrier=holder_carrier,
        getter=dict(method=[getter.index,base_wrapper.name,'get___instance',body['pointer']-base],
            family=body['family'],codeWindows=body['windows'],warmProgram=warm,compatibleRefresh=refresh),
        disabledCollector=collector,accessors=records,all36NamedAccessorEffectsProved=True,
        nativeClosedMetadataFieldOffsetsAdmitted=False,openGenericFieldOffsetsUsed=False,
        closedInstanceSizeAdmitted=False,constructorsAdmitted=False,readerAdmitted=False,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False),default=lambda v:v.hex()if isinstance(v,bytes)else sorted(v)))
