"""Nominal unmanaged QWORDs, with independent layout and source programs.

The actual native body proves eight consumed/returned bytes. A selected
ordinary value layout must separately occupy those bytes, and the reciprocal
closed ReadUnmanaged registration is checked without inferring pointer aliases.
"""
import json
import struct

from scripts.game_data.memorypack.unmanaged_qword_source import called_advance_qword_program,inline_qword_program

LABEL='nominalQwordValue'


def need(check,condition,detail=''):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def layout(image,name):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.stored_value_layouts import StoredValueLayouts
    ctx=NativeReferenceContext(image);td=ctx.index.types[name]
    need('ordinary-nongeneric-value',ctx.is_value_type(name)and not ctx.is_enum(name)
         and td.generic_container_index<0,name)
    result=StoredValueLayouts(image).layout(name,8)
    return dict(result,typeDefinition=td.index,managedBytes=8,referenceLaneOffsets=[])


def source(image,pins,target,offsets):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack import generated_primitive_sources as primitives
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    try:
        direct=primitives.derive(image,target,'int64',offsets)
    except ValueError as direct_error:
        direct=None;direct_detail=str(direct_error)
    if direct is not None:
        need('direct-QWORD-source-width',direct.get('wireBytes')==8)
        return dict(direct,completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True)
    base=image.pe.image_base;family,windows,_rows=ec.family(image,target-base)
    regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
    if image.pe.bytes_at_va(target,10)==bytes.fromhex('48895c24084889742410'):
        program=inline_qword_program(regions,target,offsets)
        return dict(targetRva=target-base,family=family,codeWindows=windows,program=program,
            completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True)
    try:program=called_advance_qword_program(regions,target,offsets)
    except ValueError as error:
        raise ValueError(LABEL+'.no-complete-QWORD-source:'+str(dict(targetRva=target-base,
            prefix=image.pe.bytes_at_va(target,64).hex(),direct=direct_detail,calledAdvance=str(error))))from error
    advance=derive_advance(image,pins,target=program['advanceTargetVa'],offsets=offsets)
    need('independent-four-Reader-updates-and-preserved-bits',advance.get('completeAdvanceProgramProved')is True
        and advance.get('allFourReaderUpdatesProved')is True
        and advance['programs'][0].get('preservedCapturedRegister')=='rbx')
    return dict(targetRva=target-base,family=family,codeWindows=windows,program=program,
        advanceSource=advance,completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True)


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
    name=context.get('fullTypeName')
    need('actual-ordinary-ReadUnmanaged-context',usage.get('tag')==6
        and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
            ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name])
        and usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    nominal=layout(image,name);argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.argument')
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('actual-nominal-value-carrier',raw.hex().upper()==context['argumentRawHex'].upper()
        and int.from_bytes(raw[:8],'little')==context['typeDefinition']==nominal['typeDefinition'])
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers']
    at=section.offset+method.generic_container_index*16
    need('instance-zeroarg-MVAR-method',method.generic_container_index>=0
        and section.offset<=at<=section.offset+section.size-16 and not method.flags&16
        and method.parameter_count==0 and usage['methodSpec'][1]==-1)
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    identity=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source=LABEL)
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('reciprocal-sole-MVAR-result',(owner,count,is_method)==(method.index,1,1)
        and identity['methodIndex']==method.index and identity['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==start)
    canonical=GenericEntries(image).resolve(method.index,[],[name])
    need('exact-closed-registration-index',canonical['methodSpecIndex']==usage['methodSpecIndex'])
    offsets=scalar.reader_offsets(image,LABEL);actual=source(image,pins,source_target,offsets)
    registered=actual if canonical['pointer']==source_target else source(image,pins,canonical['pointer'],offsets)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.nominal-qword-value-source.v1',status='validated',
        nativeInputs=pins,typeName=name,typeDefinition=nominal['typeDefinition'],wireBytes=8,resultRegister='rax',
        readerMethodDefinition=method.index,targetRva=source_target-base,completeBufferedProgram=True,
        entryRspRestored=True,nonvolatilesRestored=True,
        proof=dict(typedRequest=usage,layout=nominal,argumentRawHex=raw.hex().upper(),returnTypeRawHex=returned.hex().upper(),
            genericParameterOwner=identity,closedRegistration=canonical,actualPointerEqualsRegistered=canonical['pointer']==source_target,
            pointerAliasInferred=False,actualSource=actual,registeredSource=registered))))
