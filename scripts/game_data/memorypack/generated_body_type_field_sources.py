"""Exact BodyTypeDef32 named setter/local source, with both reference lanes.

The setter copies two complete16-byte slices and tails through one explicit
barrier at lane8. The second native reference lane24 remains in the nominal
layout and copied bits; no second barrier is invented. Disabled collector,
normal compatible helpers, typed nonnull holder and disjoint stable storage
are conditions. This owns no MC3 wire grammar or enclosing frame.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import body_type_value_sources as value

TYPE=value.TYPE
SLICES=[[0,16],[16,16]]


def need(check,condition):
    if not condition:raise ValueError('generatedBodyTypeField.'+check)


def setter_program(regions,entry,*,field,barrier):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('owned-literal-field-and-barrier',type(field)is int and 16<=field<2**31-32 and type(barrier)is int and barrier>0)
    g=BytesPath(regions,entry);g.take('4883ec28','488b4910','4885c9');null=_nonnull(g)
    g.take('0f1002','0f104a10',_displacement('0f1141',field),_displacement('0f1149',field+16))
    g.take('4883c1'+bytes((field+8,)).hex()if field+8<128 else'4881c1'+(field+8).to_bytes(4,'little').hex())
    g.take('4883c428');need('same-tail-barrier',g.relative('e9')==barrier)
    null_at=null['nullTargetVa'];raw=bytes(g.bytes[null_at+i]for i in range(6))
    need('bounded-null-helper-then-trap',raw[0]==232 and raw[-1]==204)
    return dict(selectedBytes=g.seen,holderOffset=16,sourceSlices=SLICES,storedBytes=32,managedBytes=32,
        referenceLaneOffsets=[8,24],explicitBarrierLaneOffsets=[8],barrierReferenceLaneOffset=8,
        barrierTarget=barrier,nullBranch=dict(null,bytes=raw.hex().upper()),
        wholeInputBitsStoredUnchanged=True,completeSourceBitsStoredUnchanged=True,disabledCollectorRequired=True,
        entryRspRestored=True,normalFrameAndReturn=True,normalReturnViaBarrier=True)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    _publication_gate(image,pins)
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('own-nominal-reference-parent',member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type))
    nominal=value.layout(image,ctx);holder=direct_holder(image,ctx,wrapper)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,
        ('void',1,False),[(TYPE,17,False)],'generatedBodyTypeField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    program=setter_program(body['regions'],body['pointer'],field=offset,barrier=image.pe.image_base+barrier)
    _publication_gate(image,pins)
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=32,
        managedValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',
        program=program,getter=None,directHolder=holder,ordinarySourceRows=body['rows'],
        ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    layout=setter.get('managedValueLayout',{});program=setter.get('program',{});context=event.get('context')
    parameter=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-managed32-source-and-setter',event.get('kind')=='managed:'+TYPE
        and event.get('declaredType')==layout.get('typeName')==TYPE and event.get('mode')=='typed-managed-value'
        and event.get('actualSourceProved')is True and event.get('resultAbi')=='hidden-local'and'wireBytes'not in event
        and event.get('managedBytes')==layout.get('managedBytes')==setter.get('storedBytes')==32
        and event.get('referenceLaneOffsets')==layout.get('referenceLaneOffsets')==[8,24]
        and layout.get('paddingByteRanges')==[[1,7],[20,4]]and type(layout.get('typeDefinition'))is int
        and len(parameter)==16 and parameter[10:12]==bytes((17,128))
        and int.from_bytes(parameter[:8],'little')==layout['typeDefinition']
        and program.get('sourceSlices')==SLICES and program.get('explicitBarrierLaneOffsets')==[8]
        and program.get('referenceLaneOffsets')==[8,24]and all(program.get(k)is True for k in
            ('wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged','disabledCollectorRequired',
             'entryRspRestored','normalFrameAndReturn','normalReturnViaBarrier')))
    if event.get('sourceContextMode')=='owned-closed-forwarder':
        from scripts.game_data.memorypack.body_type_closed_value_sources import verify
        actual=event.get('bodyTypeClosedForwarderSource',{})
        verify(actual,actual.get('nativeInputs'))
        need('actual-own-closed-BodyType-source',context is None and actual.get('sourceTargetRva')==event.get('sourceTargetRva')
            and actual.get('proof',{}).get('nominal')==layout)
    else:
        need('actual-own-ReadValue-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
            and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17
            and context.get('typeDefinition')==layout['typeDefinition']and event.get('sourceContextMode')is None)
    return True


def read_source(image,pins,*,context,source_target):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    need('own-ordinary-context',isinstance(context,dict)and context.get('fullTypeName')==TYPE and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadValue'and context.get('register')=='r8'and context.get('typeKind')==17)
    usage=derive_typed_usage_context(image,context['instructionRva'],label='generatedBodyTypeField.ReadValue')
    need('same-actual-context',usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    result=value.derive(image,pins,typed_request=usage,source_target=source_target)
    need('same-nominal-current-source',result['nativeInputs']==pins and result['typeName']==TYPE and result['managedBytes']==32
        and result['resultAbi']=='hidden-local'and result['actualSourceProved']is True
        and result['sourceTargetRva']==source_target-image.pe.image_base and result['readerMethodDefinition']==context['methodSpec'][0]
        and result['proof']['nominal']['typeDefinition']==context['typeDefinition']and result['wireGrammarAdmitted']is False)
    return result


def require_setter(setter):
    """Replay the complete retained setter bytes, including its bounded null edge."""
    import hashlib,json
    method=setter.get('method',[]);program=setter.get('program',{});selected=program.get('selectedBytes',[])
    need('owned-method-and-byte-path',len(method)==4 and all(type(method[i])is int for i in(0,3))
        and selected and type(selected[0][0])is int and method[3]>=0)
    base=selected[0][0]-method[3];rows=setter.get('ordinarySourceRegions',[]);windows=setter.get('codeWindows',[])
    regions=[(base+a,bytes.fromhex(h))for a,h in rows]
    need('complete-unique-setter-regions',len(rows)==len(windows)>0 and len({a for a,h in rows})==len(rows))
    by_start={base+w['startRva']:w for w in windows}
    for start,raw in regions:
        window=by_start.get(start,{})
        need('current-whole-native-window-bytes',window.get('endRva',0)-window.get('startRva',0)==len(raw)
            and hashlib.sha256(raw).hexdigest().upper()==window.get('sha256','').upper())
    family=setter.get('sourceFamily',{})
    need('complete-owned-setter-family',family.get('schema')=='endfield.amd64-unwind-chain-family.v1'
        and family.get('selectedPrimaryRva')==method[3]
        and sorted(tuple(r['runtimeTriple'][:2])for r in family.get('ranges',[]))
            ==sorted((w['startRva'],w['endRva'])for w in windows))
    actual=setter_program(regions,base+method[3],field=setter['fieldOffset'],barrier=program['barrierTarget'])
    need('full-setter-program-replayed',json.loads(json.dumps(actual))==program)
    return actual
