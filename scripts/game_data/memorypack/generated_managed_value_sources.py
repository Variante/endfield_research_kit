"""Named managed-value layouts and exact source-preserving field setters.

These are managed transfers, not fixed-width wire grammars. BuffId owns one
reference lane, LangKey owns two, and GameplayTagQuery owns padding plus an
array reference. Their actual Reader/provider and wire programs stay in each
nominal domain owner; none is admitted through another type's byte size.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedManagedValue'
NOMINALS={
    'Beyond.Gameplay.Core.BuffId':dict(bytes=8,fields=[('buffId','string',16,14)],references=[0],padding=[]),
    'Beyond.Gameplay.Core.GlobalBuffId':dict(bytes=8,fields=[('id','string',16,14)],references=[0],padding=[]),
    'Beyond.LangKey':dict(bytes=16,fields=[('key','string',16,14),('<rawText>k__BackingField','string',24,14)],references=[0,8],padding=[]),
    'Beyond.Gameplay.Core.GameplayTagQuery':dict(bytes=16,fields=[('queryType','Beyond.Gameplay.Core.GameplayTagQuery+QueryType',16,17),
        ('tags','Beyond.Gameplay.Core.GameplayTag[]',24,29)],references=[8],padding=[[4,4]]),
}


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def layout(image,ctx,type_name):
    """Current exact nominal field declarations and size-table row only."""
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('explicit-nominal-domain',type_name in NOMINALS);expected=NOMINALS[type_name];md=image.metadata
    td=ctx.index.types[type_name];need('nongeneric-value-definition',ctx.is_value_type(type_name)and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[]
    for field in fields:
        name=md.string(field.name_index);fact=ctx.field(type_name+'::'+name);raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
        actual.append((name,fact[1],fact[2],raw[10]))
        scalar.ordinary(image,ctx.type_pointer(field.type_index),raw[10],LABEL+'.field',reference=raw[10]in(14,29))
    need('exact-current-nominal-fields',actual==expected['fields'],actual)
    if type_name=='Beyond.Gameplay.Core.GameplayTagQuery':
        enum_name=expected['fields'][0][1];need('query-enum-declaration',ctx.is_enum(enum_name))
        enum=ctx.index.types[enum_name];backing=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
        need('query-enum-exact-int32-backing',enum.generic_container_index<0 and len(backing)==1 and
            md.string(backing[0].name_index)=='value__'and ctx.field(enum_name+'::value__')==(enum_name,'int',16))
        scalar.ordinary(image,ctx.type_pointer(backing[0].type_index),8,LABEL+'.queryEnum')
    need('current-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8);width=expected['bytes']
    need('current-nominal-managed-size',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(16+width,width))
    return dict(typeName=type_name,typeDefinition=td.index,fields=actual,managedBytes=width,
        referenceLaneOffsets=list(expected['references']),paddingByteRanges=expected['padding'],wireGrammarAdmitted=False)


def setter_program(regions,entry,*,field,managed_bytes,reference_lane_offsets,barrier,getter=None,holder=16):
    """Own complete ordinary getter/direct-holder, whole input store and tail."""
    from scripts.game_data.memorypack import generated_lifecycle_sources as life,generated_member_sources as members
    need('finite-managed-transfer',type(managed_bytes)is int and managed_bytes in(8,16)and
        type(reference_lane_offsets)is list and reference_lane_offsets in([0],[0,8],[8]))
    need('literal-field-holder-target',type(field)is int and field>=16 and type(holder)is int and 16<=holder<128 and
        type(barrier)is int and barrier>0 and(getter is None or type(getter)is int and getter>0))
    need('reference-lanes-inside-managed-value',all(type(offset)is int and offset+8<=managed_bytes for offset in reference_lane_offsets))
    g=BytesPath(regions,entry);lane=None
    if getter is not None:
        g.take('4053','4883ec20','488bda','33d2');g.call(getter);g.take('4885c0');life._nonnull(g)
        if managed_bytes==16:g.take('0f1003')
        site=g.at;cell_prefix=life._peek(g,3)
        need('managed-setter-field-address',cell_prefix in(bytes.fromhex('488d48'),bytes.fromhex('488d88')))
        width=1 if cell_prefix[-1]==0x48 else 4;g.take(cell_prefix.hex());address=int.from_bytes(g.read(width),'little',signed=True);lane=address-field
        need('actual-reference-lane-address',lane in reference_lane_offsets)
        g.take(members._displacement('488958',field)if managed_bytes==8 else members._displacement('0f1140',field))
        g.take('4883c420','5b');restored=['rbx'];source='rdx preserved rbx'
    else:
        g.take('4883ec28',members._displacement('488b49',holder),'4885c9');life._nonnull(g)
        if managed_bytes==16:g.take('0f1002',members._displacement('0f1141',field))
        else:g.take(members._displacement('488951',field))
        prefix=life._peek(g,3);need('direct-managed-field-address',prefix in(bytes.fromhex('4883c1'),bytes.fromhex('4881c1')))
        g.take(prefix.hex());address=int.from_bytes(g.read(1 if prefix[1]==0x83 else 4),'little',signed=True);lane=address-field
        need('direct-actual-reference-lane-address',lane in reference_lane_offsets)
        g.take('4883c428');restored=[];source='incoming rdx pointer'if managed_bytes==16 else'incoming rdx whole qword'
    need('same-disabled-tail-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,storedBytes=managed_bytes,managedBytes=managed_bytes,referenceLaneOffsets=reference_lane_offsets,
        barrierReferenceLaneOffset=lane,incomingValueSource=source,wholeInputBitsStoredUnchanged=True,
        disabledCollectorRequired=True,entryRspRestored=True,nonvolatileRegistersRestored=restored,normalReturnViaBarrier=True,
        condition='Exact current nominal managed fields/layout and ordinary setter ABI; compatible nonnull holder/getter, disjoint stable source/destination and disabled no-effect collector barrier. Full same input bits are stored; no wire width, child grammar or runtime callback selection is inferred.')


def _derive_setter(image,member,wrappers,barrier,getter_cache):
    """Current named metadata/ABI, own getter or direct holder, and full bytes."""
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member);base=image.pe.image_base;md=image.metadata
    need('ordinary-reference-parent',not ctx.is_value_type(wrapper.wrapped_type))
    nominal=layout(image,ctx,member.declared_type)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(member.declared_type,17,False)],LABEL+'.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=md.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method));getter=pointer.methods(image,wrapper).get('get___instance');getter_proof=None;proof=None;errors=[]
    arguments=dict(field=offset,managed_bytes=nominal['managedBytes'],reference_lane_offsets=nominal['referenceLaneOffsets'],barrier=base+barrier)
    if getter is not None:
        try:
            getter_proof=members._coherent_getter(image,ctx,wrapper,getter,getter_cache,barrier=base+barrier)
            proof=setter_program(body['regions'],body['pointer'],getter=image.method_pointer_va(getter),**arguments)
            profile='cached-getter-setter'
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error));getter_proof=None
    if proof is None:
        try:
            holder_name,holder=field(wrapper.name,{'___instance','__instance','__realInstance'})
            need('same-owned-direct-reference-holder',holder==(wrapper.name,wrapper.wrapped_type,16),holder)
            declared,=[f for f in md.fields_for(md.types[wrapper.type_definition])if wrapper.name+'::'+md.string(f.name_index)==holder_name]
            scalar.ordinary(image,ctx.type_pointer(declared.type_index),18,LABEL+'.holder',reference=True)
            proof=setter_program(body['regions'],body['pointer'],holder=holder[2],**arguments);proof['holderOffset']=holder[2]
            profile='direct-base-holder-setter'
        except(ValueError,KeyError,IndexError)as error:errors.append(str(error))
    need('complete-managed-setter',proof is not None,errors)
    return dict(method=[method.index,wrapper.name,md.string(method.name_index),body['pointer']-base],member=member.row(),targetField=target,
        fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=nominal['managedBytes'],managedValueLayout=nominal,
        sourceFamily=body['family'],codeWindows=body['windows'],profile=profile,program=proof,getter=getter_proof,
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False,
        evidenceBoundary='Fresh exact current named value layout/ordinary kind17 setter and destination field. Complete whole-input getter/direct-holder store/frame/tail under independently disabled collector; actual source Reader/provider, child wire grammar and parent entry/lifecycle remain separate.')


def derive_many(image,pins,wrapper_names):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.generated_action_sources import _prepare
    need('bounded-distinct-current-wrappers',type(wrapper_names)is list and 0<len(wrapper_names)<=64 and len(set(wrapper_names))==len(wrapper_names))
    _publication_gate(image,pins);_,barrier,_=_prepare(image,pins);inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory}
    need('unique-named-current-inventory',len(inventory)==len(wrappers));cache={};owners=[]
    for name in wrapper_names:
        selected=[m for m in wrappers[name].members if m.declared_type in NOMINALS];need('one-or-more-selected-nominal-members',bool(selected),name)
        members=[]
        for member in selected:
            try:members.append(dict(status='setter-source-proved',proof=_derive_setter(image,member,wrappers,barrier,cache)))
            except(ValueError,KeyError,IndexError,TypeError)as error:members.append(dict(status='pendingReview',member=member.row(),reason=str(error)[:1800]))
        owners.append(dict(wrapperName=name,members=members,wholeOwnerAdmitted=False))
    _publication_gate(image,pins)
    return dict(nativeInputs=pins,owners=owners,parentFieldAdmitted=False,wireGrammarAdmitted=False)


def read_source(image,pins,*,context,source_target):
    """Bind an actual current typed request to its separate nominal owner."""
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    raw=bytes.fromhex(context.get('argumentRawHex',''))if type(context)is dict else b''
    need('explicit-current-managed-context',type(context)is dict and context.get('fullTypeName')in NOMINALS and
        context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'and
        context.get('typeKind')==17 and len(raw)==16 and raw[11]==128)
    name=context['fullTypeName'];spec=NOMINALS[name]
    need('literal-actual-managed-source',type(source_target)is int and source_target>image.pe.image_base)
    need('actual-managed-context-register',context['register']==('rdx'if spec['bytes']==8 else'r8'))
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.ReadValue')
    need('same-raw-current-MethodSpec',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    if name=='Beyond.LangKey':
        from scripts.game_data.memorypack.leveldata_lang_key_value_sources import derive_read_value
        proof=derive_read_value(image,pins,typed_request=usage,source_target=source_target)
    elif name=='Beyond.Gameplay.Core.GlobalBuffId':
        from scripts.game_data.memorypack.skill_global_buff_id_sources import derive_read_value
        proof=derive_read_value(image,pins,typed_request=usage,source_target=source_target)
    else:
        from scripts.game_data.memorypack.skill_nominal_value_read_sources import derive
        proof=derive(image,pins,typed_request=usage,source_target=source_target)
    need('same-current-nominal-actual-source',proof['nativeInputs']==pins and proof['typeName']==name and proof['managedBytes']==spec['bytes']and
        proof['sourceTargetRva']==source_target-image.pe.image_base and proof['readerMethodDefinition']==context['methodSpec'][0]and
        proof['resultAbi']==('rax'if spec['bytes']==8 else'hidden-local')and proof['actualSourceProved']is True and proof['wireGrammarAdmitted']is False)
    return proof
