"""Actual HandIKParams raw8 ReadUnmanaged, including stored Boolean/padding bits."""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Core.CharInteractPerform.HandIKParams'
SCHEMA='endfield.char-hand-ik-raw-source.v1'


def need(check,condition):
    if not condition:raise ValueError('charHandIK.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    td=ctx.index.types[TYPE];md=image.metadata
    need('own-ordinary-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[[md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:]]for f in fields]
    need('own-float-and-two-stored-Booleans',actual==[['blendTime','float',16],['usePosition','bool',20],['useRotation','bool',21]])
    for f,kind in zip(fields,(12,2,2),strict=True):scalar.ordinary(image,ctx.type_pointer(f.type_index),kind,'charHandIK.field')
    at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('own-boxed24-managed8',image.pe.u32_at_va(at)==24)
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,boxedBytes=24,managedBytes=8,
        marshaledNativeBytes=image.pe.u32_at_va(at+4),marshaledSizeUsedForManagedWidth=False,
        referenceLaneOffsets=[],paddingByteRanges=[[6,2]],paddingRangeEncoding='start,length',storedBooleanBytesNormalized=False)


def program(regions,entry,offsets):
    need('four-distinct-reader-fields',set(offsets)=={'currentPtr','bufferLength','advancedCount','consumed'}
        and all(type(v)is int and 0<=v<128 for v in offsets.values())and len(set(offsets.values()))==4)
    cur,rem=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength'))
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20','8379'+rem+'08','488bf9');g.branch('7d',True,1)
    g.take('488b5f'+cur,'ba08000000','488bcf','488b1b');site=g.at;advance=g.relative('e8')
    g.take('488bc3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,managedOutputBytes=8,resultRegister='rax',readerRegister='rcx',contextRegister='rdx',
        advanceTargetVa=advance,advanceInstructionVa=site,advanceCount=8,sameFullQwordReturned=True,
        storedBooleanBytesNormalized=False,paddingBitsCopied=True,wrapperFramingUsed=False,firstFFIsRawData=True,
        entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True,readerOffsets=dict(offsets))


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.memorypack import scalar_param_native as scalar,pointer_param as pointer
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    _publication_gate(image,pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    need('actual-own-typed-context',isinstance(context,dict)and tuple(context.get(k)for k in('methodOwner','methodName','fullTypeName','typeKind','register'))
        ==('MemoryPack.MemoryPackReader','ReadUnmanaged',TYPE,17,'rdx'))
    usage=derive_typed_usage_context(image,context['instructionRva'],label='charHandIK')
    need('same-actual-owned-MethodSpec',usage.get('methodSpec')==context['methodSpec']and usage.get('instructionHex')==context['instructionHex']
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and bytes.fromhex(usage['instructionHex'])[:3]==bytes.fromhex('488b15'))
    nominal=layout(image,ctx);argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,17,'charHandIK.argument');raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('same-nominal-carrier',raw[10:12]==bytes((17,128))and int.from_bytes(raw[:8],'little')==nominal['typeDefinition']==context['typeDefinition']
        and raw.hex().upper()==context['argumentRawHex'].upper())
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
    need('own-generic-noarg-instance-method',image.type_name(method.declaring_type)=='MemoryPack.MemoryPackReader'and md.string(method.name_index)=='ReadUnmanaged'
        and not method.flags&16 and method.parameter_count==0 and method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
    container=struct.unpack_from('<iiii',md.buf,at);parameter=method_parameter_owner(md.buf,container[3],[m.generic_container_index for m in md.methods],source='charHandIK')
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('own-reciprocal-return-MVAR',container[:3]==(method.index,1,1)and parameter['methodIndex']==method.index and parameter['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
    body=pointer.owned(image,source_target);offsets=scalar.reader_offsets(image,'charHandIK');selected=program(body['regions'],source_target,offsets)
    advance=derive_advance(image,pins,target=selected['advanceTargetVa'],offsets=offsets)
    _publication_gate(image,pins)
    result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated',nativeInputs=pins,typeName=TYPE,typeDefinition=nominal['typeDefinition'],
        readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,wireBytes=8,managedBytes=8,
        resultAbi='register-value',resultRegister='rax',contextRegister='rdx',referenceLaneOffsets=[],paddingByteRanges=[[6,2]],
        actualSourceProved=True,wrapperFramingUsed=False,firstFFIsRawData=True,wholeGrammarAdmitted=True,
        proof=dict(layout=nominal,typedRequest=usage,closedCarrierHex=raw.hex(),ownedMethodParameter=parameter,program=selected,
            readerOffsets=offsets,sourceWindows=body['windows'],sourceRegions=[[a-base,h.hex()]for a,h in body['regions']],advanceSource=advance),
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
    verify(result,pins);return result


def verify(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.generated_called_advance_components import verify_advance
    need('own-current-raw8',actual.get('schema')==SCHEMA and actual.get('status')=='validated'and actual.get('nativeInputs')==pins
        and actual.get('typeName')==TYPE and actual.get('wireBytes')==actual.get('managedBytes')==8
        and actual.get('readMethod')=='ReadUnmanaged'and actual.get('actualSourceProved')is True
        and actual.get('resultAbi')=='register-value'and actual.get('resultRegister')=='rax'and actual.get('contextRegister')=='rdx'
        and actual.get('wrapperFramingUsed')is False and actual.get('firstFFIsRawData')is True
        and actual.get('referenceLaneOffsets')==[]and actual.get('paddingByteRanges')==[[6,2]])
    p=actual['proof'];nominal=p['layout'];usage=p['typedRequest'];carrier=bytes.fromhex(p['closedCarrierHex'])
    need('own-full-nominal-layout-and-request',nominal.get('typeName')==TYPE and nominal.get('typeDefinition')==actual['typeDefinition']
        and nominal.get('fields')==[['blendTime','float',16],['usePosition','bool',20],['useRotation','bool',21]]
        and nominal.get('managedBytes')==8 and nominal.get('boxedBytes')==24 and nominal.get('referenceLaneOffsets')==[]
        and nominal.get('paddingByteRanges')==[[6,2]]and nominal.get('storedBooleanBytesNormalized')is False
        and len(carrier)==16 and carrier[10:12]==bytes((17,128))and int.from_bytes(carrier[:8],'little')==actual['typeDefinition']
        and tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and usage.get('methodSpec',[None])[0]==actual['readerMethodDefinition'])
    parameter=p['ownedMethodParameter'];encoded=bytes.fromhex(usage.get('instructionHex',''))
    need('same-owned-formal-and-RDX-usage',parameter.get('methodIndex')==actual['readerMethodDefinition']and parameter.get('ordinal')==0
        and len(encoded)==7 and encoded[:3]==bytes.fromhex('488b15'))
    base=p['program']['selectedBytes'][0][0]-actual['targetRva'];raw=regions(p['sourceWindows'],p['sourceRegions'],base,'charHandIK')
    need('whole-raw8-program',json.loads(json.dumps(program(raw,base+actual['targetRva'],p['readerOffsets'])))==p['program'])
    verify_advance(p['advanceSource'],p['program'],pins,base)
    return True
