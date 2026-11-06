"""NameMountPointDef's selected managed16 adapter and own MC2 wrapper.

The named value owns one enum, padding and a reference lane at eight. Its
compiled adapter happens to use the established mask byte programs; nominal
layout, registration, getter and concrete wrapper are proved independently.
No mask type, live provider choice or serialized padding is carried over.
"""
import json,struct

TYPE='Beyond.Gameplay.View.NameMountPointDef'


def need(check,condition):
    if not condition:raise ValueError('interactiveMountTransfer.'+check)


def derive(image,pins,*,array_source=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import animation_mask_sources as paths
    from scripts.game_data.memorypack import generated_action_sources as actions,pointer_param as pointer
    from scripts.game_data.memorypack import interactive_value_wrapper_sources as wrappers
    from scripts.game_data.memorypack import primitive_param,event_args_paths,scalar_param_native as scalar
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.buff_ptr_sources import _definition,_adapter_context
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    child=wrappers.derive(image,pins,wrapper,*actions._prepare(image,pins));layout=child['layout']
    need('own-proved-managed16-layout',layout['typeName']==TYPE and layout['managedBytes']==16
        and layout['referenceLaneOffsets']==[8]and layout['wireGrammarAdmitted']is False)
    pair=derive_pair(image,TYPE,wrapper.name);face,=pair['composition']['interfaces']
    forward=pointer.registered_pair(image,pair,wrapper,label='interactiveMountTransfer.pair')
    need('same-own-GetValue16',face['getValueMethodIndex']==layout['proofs']['GetValue']['method'][0])
    section=md.sections['interfaceOffsets'];td=md.types[wrapper.type_definition];at=section.offset+td.interface_offsets_start*8
    offsets=list(struct.iter_unpack('<ii',md.buf[at:at+td.interface_offsets_count*8]))
    ordinal=offsets.index((face['interfaceTypeIndex'],face['interfaceOffset']))
    canonical=ge.resolve(_definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','Deserialize').index,[TYPE,'object'],[])
    nonnull=ge.resolve(_definition(image,'Beyond.MemoryPack.GenericMemoryPackFormatter`2','DeserializeNotNull').index,[TYPE,'object'],[])
    body=pointer.owned(image,canonical['pointer']);converted=pointer.owned(image,nonnull['pointer'])
    s=dict(adapter=body['pointer'],notNull=converted['pointer'],
        readNull=_body_target(body,'test al, al',before=True),
        typeHandle=_body_target(body,'test rax, rax',before=True),
        creationTest=_body_target(body,'mov rcx, rax'),
        activate=_body_target(body,'mov rcx, [rcx+0x58]'))
    need('actual-nonnull-call-target',s['notNull']==_body_target(body,'mov r9, [r9+0x18]'))
    s.update(resolve=_body_target(converted,'mov rcx, [rdi+0x20]'),
        wrapperProvider=_body_target(converted,'mov rcx, [rcx+0x20]'),
        ordinaryDispatch=_body_target(converted,'mov rdx, rax'),
        context=_body_target(converted,'mov edx, 0x8'),
        conversion=_body_target(converted,'mov r9, rbx'),
        barrier=_body_target(converted,'movups [rsi], xmm0'))
    conversion=pointer.owned(image,s['conversion']);s['prepare']=_body_target(conversion,'mov rbx, r8')
    programs=[paths.adapter_program(body['regions'],body['pointer'],s,**kw)for kw in(
        dict(null=True),dict(create=False),dict(create=True))]
    converted_programs=[paths.not_null_program(converted['regions'],converted['pointer'],s,zero=zero)for zero in(False,True)]
    conversion_program=paths.conversion_program(conversion['regions'],conversion['pointer'],s['prepare'],ordinal=ordinal)
    invoked=pointer.owned(image,s['ordinaryDispatch'])
    invocation=deserialize_slot(invoked['regions'],invoked['pointer'],prepare=s['prepare'],callback=base+child['formatterSource']['method'][3])
    read_null=pointer.owned(image,s['readNull'])
    null_symbols=dict(peek=_body_target(read_null,'test al, al',before=True),
        objectHeader=_body_target(read_null,'mov rcx, rbx'))
    null_programs=[paths.null_program(read_null['regions'],read_null['pointer'],null_symbols,null=n)for n in(False,True)]
    offsets=scalar.reader_offsets(image,'interactiveMountTransfer');peek=pointer.owned(image,null_symbols['peek'])
    peek_program=event_args_paths.peek(peek['regions'],peek['pointer'],offsets)
    header=vector_recorder(image)(null_symbols['objectHeader']-base);primitive_param.object_header_source(image,header,offsets)
    context,context_proof=_adapter_context(image,ge)
    need('same-named-type-handle',s['typeHandle']==base+pair['registration']['helperMethods']['typeFromHandle'][3])
    dispatcher=None
    if array_source is not None:
        need('own-proved-typed-array-source',array_source.get('nativeInputs')==pins
            and array_source.get('typeName')==TYPE+'[]'and array_source.get('actualSourceProved')is True
            and array_source.get('elementManagedBytes')==16 and array_source.get('elementGrammarAdmitted')is False)
        target=array_source['proof']['programs'][-1]['symbols']['dispatch'];dispatch=pointer.owned(image,target)
        dispatcher=dict(windows=dispatch['windows'],programs=[paths.adapter_program(dispatch['regions'],target,s,inline=True,**kw)
            for kw in(dict(null=True),dict(create=False),dict(create=True))])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.interactive-mount-transfer-source.v1',nativeInputs=pins,
        typeName=TYPE,wrapperName=wrapper.name,managedBytes=16,referenceLaneOffsets=[8],
        actualSourceProved=True,wireGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(layout=layout,wrapperSource=child,registeredPair=pair,pairForwarder=forward,
            canonicalRegistration=canonical,nonnullRegistration=nonnull,interfaceOrdinal=ordinal,
            adapterContext=context,adapterContextProof=context_proof,programs=programs,
            convertedPrograms=converted_programs,conversionProgram=conversion_program,wrapperInvocation=invocation,
            nullPrograms=null_programs,peek=peek_program,header=header,arrayDispatcher=dispatcher,
            symbolRvas={k:v-base for k,v in s.items()},sourceWindows=dict(adapter=body['windows'],nonnull=converted['windows'],
                conversion=conversion['windows'],invocation=invoked['windows'],readNull=read_null['windows'],peek=peek['windows'])),
        evidenceBoundary=dict(exact='Own nominal MC2 fields, complete managed16 adapter FF/create/reuse and wrapper conversion, actual slot5 and interface/GetValue, enum/padding/reference layout.',
            conditional='Ready coherent selected closed adapter and wrapper callbacks, normal compatible helpers and getter results; disabled collector, valid disjoint buffered input/output. '+__doc__,
            unresolved=['live formatter/provider selection','enclosing parent and complete byte grammar','runtime mounting behavior']))))
