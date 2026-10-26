"""Explicit constructed Nullable<Single> layout and whole-QWORD setters.

This value carrier is GENERICINST21 with its own HasValue/Single/padding layout.
It cannot borrow the ordinary kind17 managed-reference lane or an Int64 wire
grammar. The source Reader, serialization, parent entry and construction remain
independent; this component proves the current parameter/field and store only.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='System.Nullable`1<float>'
LABEL='generatedNullableValue'
def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:800])

def setter_program(regions,entry,*,field,base_slot,cache_slot,path_factory=None):
    from scripts.game_data.memorypack.generated_member_sources import _nonnull_edge,_displacement
    need('finite-distinct-owned-holders',type(field)is int and field>=16 and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    need('callable-only-selected-path',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry);g.take('4053','4883ec20')
    flag=g.relative('803d')+1;g.take('00','488bda','48897c2438','488bf9');_nonnull_edge(g)
    b=bytes((base_slot,)).hex();c=bytes((cache_slot,)).hex()
    g.take('48837f'+c+'00');_nonnull_edge(g);g.take('488b47'+b,'483947'+c)
    raw=bytes(g.bytes.get(g.at+i,0)for i in range(2))
    if raw[:1]==b'\x74':g.branch('74',True,1)
    elif raw[:1]==b'\x75':g.branch('75',False,1)
    elif raw==b'\x0f\x84':g.branch('0f84',True)
    else:g.branch('0f85',False)
    g.take('488b47'+c,'488b7c2438','4885c0');_nonnull_edge(g)
    g.take(_displacement('488958',field),'4883c420','5b','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag,fieldOffset=field,baseSlot=base_slot,cacheSlot=cache_slot,
        storedBytes=8,incomingRegister='rdx',preservedRegister='rbx',wholeInputBitsStoredUnchanged=True,paddingBitsPreserved=True,
        referenceLaneOffsets=[],entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],normalReturn=True,
        coherentCompatibleNonNullCacheRequired=True,refreshAdmitted=False,wireGrammarAdmitted=False)

def derive_setter(image,pins,member,wrappers,getter_cache):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.leveldata_nullable_float_sources import derive_layout
    _publication_gate(image,pins);need('only-reviewed-constructed-value',member.declared_type==TYPE)
    ctx,wrapper,_,target,offset,method=_setter_metadata(image,wrappers,member);md=image.metadata;base=image.pe.image_base
    need('ordinary-reference-parent',not ctx.is_value_type(wrapper.wrapped_type))
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,21,False)],LABEL+'.setter')
    need('nongeneric-current-setter',method.generic_container_index<0)
    parameter,=md.parameters_for(method);type_pointer=ctx.type_pointer(parameter.type_index);raw=image.pe.bytes_at_va(type_pointer,16)
    need('exact-value-carrier-flags',raw[10:12]==bytes((21,128)))
    nominal=derive_layout(image,type_pointer=type_pointer)
    owner,name=target.rsplit('::',1);field,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==name]
    field_layout=derive_layout(image,type_pointer=ctx.type_pointer(field.type_index))
    need('same-closed-parameter-and-named-field',nominal['typeName']==field_layout['typeName']==TYPE and
        nominal['selectedCarrier']['definition']==field_layout['selectedCarrier']['definition']and
        nominal['selectedCarrier']['classArguments']==field_layout['selectedCarrier']['classArguments'])
    need('independent-complete-managed-layout',nominal.get('concreteTypeKind')==21 and nominal.get('valueCarrier')is True
        and nominal.get('managedBytes')==8 and nominal.get('referenceLaneOffsets')==[]and nominal.get('paddingByteRanges')==[[1,3]]
        and nominal.get('hasValueByteOffset')==0 and nominal.get('singleBitsByteOffset')==4 and nominal.get('wireGrammarAdmitted')is False)
    getter=pointer.methods(image,wrapper).get('get___instance');need('owned-current-compatible-getter',getter is not None)
    coherent=members._coherent_getter(image,ctx,wrapper,getter,getter_cache)
    body=members._body(image,image.method_pointer_va(method))
    program=setter_program(body['regions'],body['pointer'],field=offset,base_slot=coherent['baseHolder'][2],cache_slot=coherent['typedCache'][2])
    proof=dict(nativeInputs=dict(pins),method=[method.index,wrapper.name,md.string(method.name_index),body['pointer']-base],member=member.row(),
        targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=8,constructedValueLayout=nominal,fieldValueLayout=field_layout,
        sourceFamily=body['family'],codeWindows=body['windows'],profile='inline-coherent-constructed-value-setter',program=program,getter=coherent,
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,parentFieldAdmitted=False,factoryAdmitted=False,
        evidenceBoundary='Fresh exact kind21 Nullable<Single> parameter and named Original field, independently owned generic-layout/direct-method witnesses, coherent nonnull compatible cache, whole input QWORD including padding and full restored setter frame. Reader/provider/wire, parent entry and construction remain separate.')
    _publication_gate(image,pins);return proof

def derive(image,pins,wrapper_name):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    _publication_gate(image,pins);inventory=list(image.memorypack_wrappers.values());wrappers={w.name:w for w in inventory}
    need('unique-current-inventory',len(wrappers)==len(inventory));wrapper=wrappers[wrapper_name]
    selected=[m for m in wrapper.members if m.declared_type==TYPE];need('one-or-more-owned-constructed-members',bool(selected))
    cache={};proofs=[derive_setter(image,pins,m,wrappers,cache)for m in selected]
    _publication_gate(image,pins);return dict(nativeInputs=dict(pins),wrapperName=wrapper_name,members=proofs,wholeOwnerAdmitted=False,wireGrammarAdmitted=False)

def read_source(image,pins,*,context,source_target):
    """Explicit constructed21 request; never an ordinary managed17 fallback."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.leveldata_nullable_float_sources import derive_read_value
    _publication_gate(image,pins)
    raw=bytes.fromhex(context.get('argumentRawHex',''))if isinstance(context,dict)else b''
    need('exact-constructed-value-ReadValue-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadValue'
        and context.get('typeKind')==21 and len(raw)==16 and raw[10:12]==bytes((21,128))and context.get('register')=='rdx')
    need('literal-actual-source-entry',type(source_target)is int and source_target>image.pe.image_base)
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL+'.ReadValue')
    need('same-exact-current-typed-request',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    native=derive_read_value(image,pins,typed_request=usage,source_target=source_target)
    cap=native.get('capability',{});layout=native.get('proof',{}).get('layout',{})
    need('independent-complete-current-Nullable-source',native.get('nativeInputs')==pins and native.get('typeName')==TYPE
        and native.get('status')=='validated-conditional-source'and cap.get('capability')=='story-nullable-single'
        and cap.get('typeName')==TYPE and cap.get('concreteTypeKind')==21 and cap.get('valueCarrier')is True and cap.get('managedBytes')==8
        and cap.get('sourceTargetRva')==source_target-image.pe.image_base and cap.get('readerMethodDefinition')==context['methodSpec'][0]
        and cap.get('resultAbi')=='rax-managed-value'and cap.get('paddingByteRanges')==[[1,3]]and cap.get('actualSourceProved')is True
        and cap.get('rawBitsPreserved')is True and cap.get('headerBytes')==0 and cap.get('wireBytes')==8
        and layout.get('hasValue')==0 and layout.get('single')==4 and layout.get('managedBytes')==8)
    result=dict(nativeInputs=dict(pins),typeName=TYPE,managedBytes=8,concreteTypeKind=21,valueCarrier=True,resultAbi='rax-managed-value',
        actualSourceProved=True,sourceTargetRva=cap['sourceTargetRva'],readerMethodDefinition=cap['readerMethodDefinition'],
        referenceLaneOffsets=[],paddingByteRanges=[[1,3]],proof=dict(typedRequest=usage,nativeSource=native),
        wireGrammarAdmitted=False,parentFieldAdmitted=False)
    _publication_gate(image,pins);return result
