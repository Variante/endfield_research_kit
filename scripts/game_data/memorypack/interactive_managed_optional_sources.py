"""Typed closed Optional-reference hidden16 sources and Original field writes.

Only the four exact closed reference Optionals enter this owner. Their layout
comes from their own compiled accessors; actual ReadValue/provider, matched
canonical shared adapter branch and owned interface/GetValue are separate
native programs. The coherent selected MethodInfo represents the exact eager
Original/wrapper pair. Runtime provider/inflation selection and child wire
grammar remain separate; shared native code never supplies a closed layout.
"""
import json,struct
from scripts.game_data.memorypack import interactive_value_layouts as layouts

TYPES={layouts.OPTIONAL+t+'>'for t in layouts.REFERENCES}


def need(check,condition,detail=''):
    if not condition:raise ValueError('interactiveManagedOptional.'+check+':'+str(detail)[:900])


def derive_setter(image,pins,member,wrappers,barrier):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,generated_managed_value_sources as managed
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('finite-own-closed-value',member.declared_type in TYPES)
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-reference-parent',not ctx.is_value_type(wrapper.wrapped_type))
    layout=layouts.derive(image,pins,member.declared_type,barrier=image.pe.image_base+barrier)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    own=bytes.fromhex(layout['nominal']['carrier']['rawHex'])
    need('same-own-closed-value-carrier',raw[10:12]==own[10:12]==bytes((21,128))and raw[:8]==own[:8])
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
        [(member.declared_type,21,False)],'interactiveManagedOptional.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    holder_name,holder=field(wrapper.name,{'___instance','__instance','__realInstance'})
    need('actual-own-reference-holder',holder==(wrapper.name,wrapper.wrapped_type,16))
    declaration,=[f for f in image.metadata.fields_for(image.metadata.types[wrapper.type_definition])
        if wrapper.name+'::'+image.metadata.string(f.name_index)==holder_name]
    scalar.ordinary(image,ctx.type_pointer(declaration.type_index),18,'interactiveManagedOptional.holder',reference=True)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    if body['regions'][0][1].startswith(bytes.fromhex('48895c2410574883ec20')):
        from scripts.game_data.memorypack.interactive_managed_optional_programs import inline_setter
        from scripts.game_data.memorypack.generated_action_sources import _prepare
        _,current_barrier,disabled=_prepare(image,pins)
        need('same-own-prepared-barrier',current_barrier==barrier)
        program=inline_setter(body['regions'],body['pointer'],field=offset,disabled=image.pe.image_base+disabled)
    else:
        program=managed.setter_program(body['regions'],body['pointer'],field=offset,managed_bytes=16,
            reference_lane_offsets=[8],barrier=image.pe.image_base+barrier,holder=16)
    program['holderOffset']=16
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=16,
        sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',program=program,
        getter=None,managedValueLayout=layout,incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import generated_action_sources as actions,pointer_param as pointer,buff_ptr_sources as buff
    from scripts.game_data.memorypack import primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.read_value_reference_sources import validate_read_value_context
    from scripts.game_data.memorypack.interactive_managed_optional_programs import read,provider
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    name=context.get('fullTypeName');raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('finite-actual-hidden16-request',name in TYPES and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==21
        and len(raw)==16 and raw[10:12]==bytes((21,128))and type(source_target)is int and source_target>base)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='interactiveManagedOptional.ReadValue')
    need('same-current-actual-request',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex']
        and(usage['tag'],usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])
            ==(6,'MemoryPack.MemoryPackReader','ReadValue',[],[name]))
    validate_typed_usage_context(image,usage,label='interactiveManagedOptional.actualCaller')
    _,barrier,disabled=actions._prepare(image,pins);layout=layouts.derive(image,pins,name,barrier=base+barrier)
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,21,'interactiveManagedOptional.closed')
    carrier=ContextSymbols(image).type(argument.type_pointer_va);own=layout['nominal']['carrier']
    need('same-own-closed-layout-and-actual-MVAR',carrier['name']==name and carrier['definition']==own['definition']
        and bytes.fromhex(carrier['rawHex'])[:8]==bytes.fromhex(own['rawHex'])[:8]
        and carrier['classArguments']==own['classArguments'])
    symbols=ContextSymbols(image);formatter_method=buff._definition(image,'MemoryPack.MemoryPackFormatterProvider','GetFormatter')
    contexts=[symbols.context(usage['methodSpec'][0],is_method=True),symbols.context(formatter_method.index,is_method=True)]
    context_proof=validate_read_value_context(image,*contexts,ge,
        fail=lambda key,e,a:need('typed-context.'+key,e==a,(e,a)))
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==name]
    pair=derive_pair(image,name,wrapper.name);face,=pair['composition']['interfaces']
    section=md.sections['interfaceOffsets'];td=md.types[wrapper.type_definition];at=section.offset+td.interface_offsets_start*8
    table=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]))
    ordinal=table.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    need('same-own-proved-GetValue16',face['getValueMethodIndex']==layout['proofs']['GetValue']['method'][0])
    reader=pointer.owned(image,source_target)
    programs=[read(reader['regions'],source_target,ordinal=ordinal,**p)for p in(
        dict(ff=True),dict(create=False,wrapper_null=False),dict(create=True,wrapper_null=False),
        dict(create=False,wrapper_null=True),dict(create=True,wrapper_null=True))]
    helper_targets={}
    for p in programs:
        for key,target in p['helperTargets'].items():
            need('same-actual-helper-across-selected-paths',key not in helper_targets or helper_targets[key]==target)
            helper_targets[key]=target
        need('same-disabled-reference-lane-source',p['disabledCollectorFlagVa']is None or p['disabledCollectorFlagVa']==base+disabled)
    canonical_definition=buff._definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize')
    canonical=ge.resolve(canonical_definition.index,['Beyond.Optional`1<object>','object'],[])
    need('actual-compared-registered-canonical-shared-entry',all(p['comparedCanonicalTargetVa']==canonical['pointer']for p in programs))
    adapter_context,adapter_proof=buff._adapter_context(image,ge)
    provided=pointer.owned(image,helper_targets['provider']);provider_proof=provider(provided['regions'],provided['pointer'])
    classes=[]
    for site in provider_proof['classUsages']:
        classes.append(derive_typed_usage_context(image,site['instructionVa']-base,label='interactiveManagedOptional.providerClass'))
    need('actual-compatible-provider-class-roles',[(u.get('tag'),u.get('typeName'))for u in classes]
        ==[(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    read_classes=[]
    for site in programs[2]['classUsages']:
        read_classes.append(derive_typed_usage_context(image,site['instructionVa']-base,label='interactiveManagedOptional.readerClass'))
    need('actual-reader-class-roles',[(u.get('tag'),u.get('typeName'))for u in read_classes]
        ==[(1,'MemoryPack.MemoryPackFormatterProvider'),(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    if name==layouts.OPTIONAL+'Beyond.Gameplay.Core.GameplayTag[]>':
        from scripts.game_data.memorypack.interactive_tag_optional_sources import derive
    elif name==layouts.OPTIONAL+layouts.MOUNT+'[]>':
        from scripts.game_data.memorypack.interactive_mount_optional_sources import derive
    else:
        from scripts.game_data.memorypack.interactive_value_wrapper_sources import derive
    child=derive(image,pins,wrapper,*actions._prepare(image,pins))
    # _prepare returns (targets, barrier, disabled), exactly this owner's ABI.
    formatter=child['formatterSource'];invoke=pointer.owned(image,helper_targets['wrapperInvoke'])
    invocation=deserialize_slot(invoke['regions'],invoke['pointer'],prepare=helper_targets['prepare'],callback=base+formatter['method'][3])
    header=vector_recorder(image)(helper_targets['header']-base)
    primitive_param.object_header_source(image,header,scalar.reader_offsets(image,'interactiveManagedOptional.header'))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.interactive-managed-optional-read-source.v1',nativeInputs=pins,
        typeName=name,wrapperName=wrapper.name,managedBytes=16,resultAbi='hidden-local',referenceLaneOffsets=[8],
        readerMethodDefinition=usage['methodSpec'][0],sourceTargetRva=source_target-base,
        actualSourceProved=True,wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        providerSelectionObserved=False,proof=dict(typedRequest=usage,closedCarrier=carrier,layout=layout,
            readerProviderContexts=contexts,readerProviderContextProof=context_proof,registeredPair=pair,
            canonicalSharedEntry=canonical,adapterContext=adapter_context,adapterContextProof=adapter_proof,
            readerPrograms=programs,readerWindows=reader['windows'],providerProgram=provider_proof,
            providerWindows=provided['windows'],providerClasses=classes,readerClasses=read_classes,
            wrapperSource=child,wrapperInvocation=invocation,wrapperInvokeWindows=invoke['windows'],
            headerSource=header,interfaceOrdinal=ordinal),
        evidenceBoundary=dict(exact='Fresh closed value21 request/layout, eager exact wrapper pair, actual complete compatible provider and matched shared Optional hidden16 reader paths, own wrapper slot5 and GetValue/interface transfer.',
            conditional=__doc__+' Initialized coherent helper contexts, normal noninterfering type/backend/provider/allocation helpers, matching compatible callback/interface receiver, disjoint stable buffered storage and disabled collector.',
            unresolved=['live provider/default/override/inflation selection','independent child grammar admission','whole enclosing owner/physical EOF']))))
