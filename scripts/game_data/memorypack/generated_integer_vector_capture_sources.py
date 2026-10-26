"""Exact inline twelve-byte integer-vector capture before actual Advance(12).

This byte program interprets no floating values. Its literal guard, low-eight
stack spill and high-four EBP capture establish twelve unchanged source bytes.
Nominal Int32 axis layout, actual Advance effects, field/local transfer and
complete caller frames are independent gates; no typed frontdoor is invented.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='UnityEngine.Vector3Int'


def need(key,condition):
    if not condition:raise ValueError('generatedIntegerVectorCapture.'+key)


def program(regions,entry,offsets,*,reader='rbx',output='rdi',path_factory=None):
    need('literal-reader-output',(reader,output)==('rbx','rdi'))
    need('callable-path-factory',path_factory is None or callable(path_factory))
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-distinct-small-reader-offsets',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    rem,cur=(bytes((offsets[k],)).hex()for k in('bufferLength','currentPtr'))
    g.take('837b'+rem+'0c');wrapper=g.at
    wrapper_register='rdi'if bytes(g.bytes.get(g.at+i,0)for i in range(3))==bytes.fromhex('488b3f')else'rsi'
    g.take('488b3f'if wrapper_register=='rdi'else'488b37');g.branch('0f8c',False)
    pointer=g.at;g.take('488b43'+cur,'ba0c000000','488bcb')
    low=g.at;g.take('f20f1000');high=g.at
    high_register='rsi'if bytes(g.bytes.get(g.at+i,0)for i in range(3))==bytes.fromhex('8b7008')else'rbp'
    need('finite-wrapper-and-high-capture-profile',(wrapper_register,high_register)in(('rsi','rbp'),('rdi','rsi')))
    g.take('8b7008'if high_register=='rsi'else'8b6808');spill=g.at;g.take('f20f11442430')
    call=g.at;target=g.relative('e8')
    return dict(selectedBytes=g.seen,guardInstructionVa=entry,sourcePointerInstructionVa=pointer,
        sourcePointerRegister='rax',wireBytes=12,
        capturedSourceSlices=[dict(register='xmm0',sourceOffset=0,bytes=8,loadInstructionVa=low,kind='sse'),
            dict(register=high_register,sourceOffset=8,bytes=4,loadInstructionVa=high,kind='integer')],
        sourceLocalValues=[dict(displacement=48,bytes=8,sourceOffset=0,register='xmm0',storeInstructionVa=spill)],
        wrapperLoad=dict(instructionVa=wrapper,register=wrapper_register,outputRegister=output),remainingRegister=None,
        readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=call,advanceTargetVa=target,
        actualReaderArgument='rbx',actualSignedCountArgument=12,independentAdvanceSourceRequired=True,
        completeSourceBitsCaptured=True,completeLowEightSpilledBeforeAdvance=True,
        preservedCaptureRegistersRequired=[high_register],managedLayoutUsedForWidth=False,
        nominalIntegerLayoutProved=False,typedReadUnmanagedClaimed=False,fieldTransferProved=False,callerFrameProved=False,
        condition='At least twelve contiguous buffered bytes and disjoint stable Reader/input/output/frame. Complete raw bits are captured before the actual Advance call. Own Int32 axis layout and source/local/field/frame composition remain mandatory; SSE moves provide no floating interpretation.')


def field_program(regions,entry,*,field_offset):
    """Exact captured stack8/EBP4 to a direct holder16 named Int3 field."""
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    need('literal-disp8-field',type(field_offset)is int and 16<=field_offset<=119)
    g=BytesPath(regions,entry);g.take('4885f6');wrapper_null=_nonnull(g)
    g.take('488b4610','4885c0');original_null=_nonnull(g)
    g.take('f20f10442430','488bcb');low=g.at;g.take('f20f1140'+bytes((field_offset,)).hex())
    high=g.at;g.take('8968'+bytes((field_offset+8,)).hex())
    return dict(selectedBytes=g.seen,fieldOffset=field_offset,baseHolderOffset=16,
        sourceLocalDisplacement=48,sourceSlices=[[0,8],[8,4]],storedBytes=12,
        fieldStores=[dict(instructionVa=low,sourceOffset=0,bytes=8),dict(instructionVa=high,sourceOffset=8,bytes=4)],
        ownedNullExits=[wrapper_null,original_null],completeSourceBitsStoredUnchanged=True,
        referencesStored=False,barrierRequired=False,callerFrameProved=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    """Own ordinary Int3 layout plus exact direct hidden-pointer8+4 setter."""
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_vector_member_sources import base_vector_setter_program
    from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-ordinary-Int3-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    need('direct-current-parent-holder16',ctx.field(wrapper.name+'::__instance')==(wrapper.name,wrapper.wrapped_type,16))
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'integerVectorCapture.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);pointer=ctx.type_pointer(parameter.type_index)
    nominal=dict(derive_layout(image,type_pointer=pointer),typeDefinition=ctx.index.types[TYPE].index)
    need('independent-current-Int32-axes',nominal['typeName']==TYPE and nominal['managedBytes']==12
        and nominal['fieldCount']==3 and nominal['referenceLaneOffsets']==nominal['paddingByteRanges']==[]
        and[(f['name'],f['declaredType'],f['managedOffset'],f['rawKind'])for f in nominal['fields']]==
            [('m_X','int',0,8),('m_Y','int',4,8),('m_Z','int',8,8)])
    raw=image.pe.bytes_at_va(pointer,16);body=members._body(image,image.method_pointer_va(method))
    program=base_vector_setter_program(body['regions'],body['pointer'],holder=16,field=offset,width=12)
    owned={a+i:b for a,h in body['regions']for i,b in enumerate(h)};null=program['ownedNullExit']
    program['ownedNullExit']=dict(null,bytes=bytes(owned[null['instructionVa']+i]for i in range(6)).hex().upper())
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=12,
        nominalValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',
        program=program,getter=None,incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def derive(image,pins,*,wrapper_name,field_name):
    """Fresh source/local/field slice; complete parent framing stays separate."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as advance
    from scripts.game_data.memorypack.leveldata_integer_vector_layout import derive_layout
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    wrapper=_selected_wrapper(image,wrapper_name);need('reference-parent',not wrapper.wrapped_is_value_type)
    selected=[m for m in wrapper.members if m.declared_type=='UnityEngine.Vector3Int']
    need('one-explicit-current-Int3-member',len(selected)==1 and selected[0].name==field_name)
    original=ctx.index.types[wrapper.wrapped_type]
    field,=[f for f in md.fields_for(original)if md.string(f.name_index)==field_name]
    scalar.ordinary(image,ctx.type_pointer(field.type_index),17,'integerVectorCapture.field')
    nominal=derive_layout(image,type_pointer=ctx.type_pointer(field.type_index))
    need('own-Int32-axes-layout',nominal['typeName']=='UnityEngine.Vector3Int'and nominal['managedBytes']==12)
    slot=ctx.field(wrapper.wrapped_type+'::'+field_name)
    need('own-current-named-field',slot[:2]==(wrapper.wrapped_type,'UnityEngine.Vector3Int'))
    need('same-parent-holder16',ctx.field(wrapper.name+'::__instance')==(wrapper.name,wrapper.wrapped_type,16))
    mm=pointer.methods(image,wrapper);body=pointer.owned(image,image.method_pointer_va(mm['Deserialize']))
    offsets=scalar.reader_offsets(image,'integerVectorCapture');prefix=bytes((0x83,0x7b,offsets['bufferLength'],12,0x48,0x8b,0x37))
    positions=[];joined={a+i:b for a,raw in body['regions']for i,b in enumerate(raw)}
    for row in body['rows']:
        at=int(row['va'],16)
        if bytes(joined.get(at+i,0)for i in range(len(prefix)))==prefix:positions.append(at)
    need('one-literal-current-source-capture',len(positions)==1)
    source=program(body['regions'],positions[0],offsets)
    helper=advance(image,pins,target=source['advanceTargetVa'],offsets=offsets)
    field_flow=field_program(body['regions'],source['advanceCallInstructionVa']+5,field_offset=slot[2])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.generated-integer-vector-capture-source.v1',nativeInputs=pins,
        status='proved-current-Int3-capture-and-field-slice-requires-full-parent',typeName='UnityEngine.Vector3Int',
        wrapperName=wrapper.name,fieldName=field_name,fieldOffset=slot[2],wireBytes=12,layout=nominal,
        sourceProgram=source,advanceSource=helper,fieldProgram=field_flow,sourceWindows=body['windows'],
        completeSourceBitsStoredUnchanged=True,typedReadUnmanagedClaimed=False,wholeParentAdmitted=False,
        callerFrameProved=False,childGrammarAdmitted=False)))
