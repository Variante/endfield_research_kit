"""Finite IntroPart PosRot24 named setters and literal inline event joins."""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import levelscript_posrot_capture_sources as value

TYPE=value.TYPE
SLICES=[[0,16],[16,8]]


def need(check,condition):
    if not condition:raise ValueError('generatedPosRotField.'+check)


def layout(image,ctx):
    return dict(value.layout(image,ctx),wireReadAdmitted=False)


def setter_program(regions,entry,*,field):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _nonnull
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    need('finite-named-field',type(field)is int and field in(48,72,96,120))
    g=BytesPath(regions,entry)
    g.take('4883ec28','488b4110','4885c0');null=_nonnull(g)
    g.take('0f1002','f20f104a10',_displacement('0f1180',field),
        _displacement('f20f1188',field+16),'4883c428','c3')
    null=dict(null,bytes=bytes(g.bytes[null['nullTargetVa']+i]for i in range(6)).hex().upper())
    return dict(selectedBytes=g.seen,holderOffset=16,managedBytes=24,storedBytes=24,fieldOffset=field,
        sourceSlices=SLICES,referenceLaneOffsets=[],paddingByteRanges=[],barrierCalls=[],ownedNullExit=null,
        sourceValuePointer='incoming rdx',holderRegister='rax',wholeInputBitsStoredUnchanged=True,
        completeSourceBitsStoredUnchanged=True,entryRspRestored=True,normalFrameAndReturn=True,
        nonvolatileRegistersRestored=[],childGrammarAdmitted=False)


def derive_setter(image,pins,member,wrappers,barrier,getter_cache):
    from scripts.game_data.il2cpp.reference_field_programs import _setter_metadata
    from scripts.game_data.memorypack import generated_member_sources as members,pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_alpha_blend_field_sources import direct_holder
    ctx,wrapper,field,target,offset,method=_setter_metadata(image,wrappers,member)
    need('exact-four-IntroPart-fields',wrapper.wrapped_type==value.PARENT and member.name in value.FIELDS
        and member.declared_type==TYPE and not ctx.is_value_type(wrapper.wrapped_type)
        and offset==48+24*value.FIELDS.index(member.name))
    nominal=layout(image,ctx);holder=direct_holder(image,ctx,wrapper)
    scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(TYPE,17,False)],'generatedPosRotField.setter')
    need('nongeneric-owned-setter',method.generic_container_index<0)
    parameter,=image.metadata.parameters_for(method);raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
    body=members._body(image,image.method_pointer_va(method),pins=pins)
    program=setter_program(body['regions'],body['pointer'],field=offset)
    getter=pointer.methods(image,wrapper)['GetValue']
    scalar.owned_method_abi(image,ctx,getter.index,wrapper.type_definition,(wrapper.wrapped_type,18,False),[],'generatedPosRotField.directGetValue')
    direct_getter=dict(method=[getter.index,wrapper.name,'GetValue',image.method_pointer_va(getter)-image.pe.image_base],
        program=pointer.leaf(image,image.method_pointer_va(getter),['488B4110','C3']))
    return dict(method=[method.index,wrapper.name,image.metadata.string(method.name_index),body['pointer']-image.pe.image_base],
        member=member.row(),targetField=target,fieldOffset=offset,parameterTypeRecordHex=raw.hex().upper(),storedBytes=24,
        nominalValueLayout=nominal,sourceFamily=body['family'],codeWindows=body['windows'],profile='direct-base-holder-setter',
        sourceProfile='direct-posrot24-setter',program=program,getter=None,directHolder=holder,directGetValue=direct_getter,
        ordinarySourceRows=body['rows'],ordinarySourceRegions=[[a-image.pe.image_base,h.hex().upper()]for a,h in body['regions']],
        incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)


def validate_event(event,setter):
    nominal=setter.get('nominalValueLayout',{});program=setter.get('program',{});raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-inline-nominal-and-named-setter',event.get('fieldName')in value.FIELDS
        and event.get('kind')=='value24:'+TYPE and event.get('declaredType')==nominal.get('typeName')==TYPE
        and event.get('mode')=='buffered-called-advance-posrot24'and event.get('context')is None
        and event.get('wireBytes')==nominal.get('managedBytes')==setter.get('storedBytes')==24
        and nominal.get('referenceLaneOffsets')==nominal.get('paddingByteRanges')==[]
        and nominal.get('rawFieldOrder')==['position','eulerAngles']and nominal.get('wireReadAdmitted')is False
        and event.get('inlineNominalLayout')==nominal and type(nominal.get('typeDefinition'))is int
        and len(raw)==16 and raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']
        and setter.get('profile')=='direct-base-holder-setter'and setter.get('sourceProfile')=='direct-posrot24-setter'
        and setter.get('fieldOffset')==48+24*value.FIELDS.index(event['fieldName'])
        and program.get('holderOffset')==16 and program.get('sourceSlices')==SLICES
        and program.get('barrierCalls')==[]and program.get('referenceLaneOffsets')==program.get('paddingByteRanges')==[]
        and all(program.get(k)is True for k in('wholeInputBitsStoredUnchanged','completeSourceBitsStoredUnchanged','entryRspRestored','normalFrameAndReturn'))
        and event.get('actualSourceProved')is True)
    capture=event.get('inlineSourceProgram',{})
    need('own-XMM6-XMM7-raw24-capture',capture.get('wireBytes')==capture.get('actualSignedCountArgument')==24
        and capture.get('actualReaderArgument')=='rbx'and capture.get('wrapperLoad',{}).get('outputRegister')=='rdi'
        and capture.get('preservedCaptureRegistersRequired')==['xmm6','xmm7']
        and[(s.get('register'),s.get('sourceOffset'),s.get('bytes'))for s in capture.get('capturedSourceSlices',[])]==[('xmm6',0,16),('xmm7',16,8)]
        and capture.get('sourceLocalValues')==[]and capture.get('typedReadUnmanagedClaimed')is False
        and capture.get('managedLayoutUsedForWidth')is False and capture.get('completeSourceBitsCaptured')is True)
    return nominal


def require_setter(setter,*,base):
    from scripts.game_data.memorypack.leveldata_tracking_raw_sources import _owned_regions
    need('owned-full-setter-regions',type(base)is int and setter.get('sourceProfile')=='direct-posrot24-setter')
    regions=_owned_regions([[base+a,h]for a,h in setter['ordinarySourceRegions']],setter['codeWindows'],base=base,label='posrot-setter')
    replay=setter_program(regions,base+setter['method'][3],field=setter['fieldOffset'])
    need('same-full-setter-byte-program',json.loads(json.dumps(replay))==json.loads(json.dumps(setter['program'])))
    return True
