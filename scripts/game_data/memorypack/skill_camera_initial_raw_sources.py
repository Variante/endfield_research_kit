"""Actual closed ReadUnmanaged<CameraControlStateInitialParam> raw24 source.

The original has four Boolean and three Single fields with padding. Its actual
reader copies all24 bytes, then calls an independently owned Advance(24). The
Boolean bytes and padding remain raw. The separate wrapper MC7 wire, value
adapter, default/FF behavior and runtime camera meaning are not substituted.
"""
import json
import hashlib
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.View.CameraControlStateInitialParam'
LABEL='cameraInitialRawSource'
FIELDS=(('applyHorizontalAngle','bool',16),('horizontalAngleRelativeToCharacter','bool',17),
    ('horizontalAngle','float',20),('applyVerticalValue','bool',24),('verticalValue','float',28),
    ('applyZoomScale','bool',32),('zoomScale','float',36))
PADDING=[[2,4],[9,12],[17,20]]


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('plain-owned-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('all-seven-ordinary-fields',actual==list(FIELDS))
    for field,(_,typename,offset)in zip(fields,FIELDS,strict=True):
        scalar.ordinary(image,ctx.type_pointer(field.type_index),2 if typename=='bool'else 12,LABEL+'.field')
    need('bounded-boxed-size-row',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('boxed24-layout',image.pe.u32_at_va(size)==40)
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,managedBytes=24,boxedBytes=40,
        referenceLaneOffsets=[],paddingByteRanges=PADDING,wireReadAdmitted=False,
        marshaledNativeBytes=image.pe.u32_at_va(size+4),marshaledSizeUsedForWidth=False)


def program(regions,entry,offsets,*,path_factory=None):
    need('callable-path-factory',path_factory is None or callable(path_factory))
    rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('48895c2408','57','4883ec20','837a'+rem+'18','488bda','488bf9');g.branch('0f8c',False)
    g.take('488b43'+cur,'ba18000000','488bcb','0f1000','f20f104810','0f1107','f20f114f10')
    call=g.at;advance=g.relative('e8')
    g.take('488b5c2430','488bc7','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=24,managedOutputBytes=24,
        hiddenOutputRegister='rcx',readerRegister='rdx',methodInfoRegister='r8',
        capturedSourceSlices=[[0,16],[16,8]],storedOutputSlices=[[0,16],[16,8]],
        advanceCallInstructionVa=call,advanceTargetVa=advance,actualAdvanceReader='rbx',actualSignedAdvanceCount=24,
        sameOutputReturnedInRax=True,fullFrameAndNonvolatilesRestored=True,normalReturn=True,
        independentAdvanceSourceRequired=True,boolBytesNormalized=False,paddingBytesCopied=True)


def bind(context,source_target,proof,*,base):
    need('literal-nominal-source',type(base)is int and type(source_target)is int and source_target>base
        and type(context.get('typeDefinition'))is int and type(context.get('typeKind'))is int
        and isinstance(context.get('methodSpec'),(tuple,list))and len(context['methodSpec'])==3
        and type(context['methodSpec'][0])is int and type(proof.get('readerMethodDefinition'))is int
        and type(proof.get('targetRva'))is int)
    need('actual-closed-raw24-request',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='r8'
        and context.get('fullTypeName')==TYPE and context['typeKind']==17
        and proof.get('schema')=='endfield.camera-initial-raw24-source.v1'and proof.get('status')=='validated'
        and proof.get('typeName')==TYPE and proof.get('typeDefinition')==context['typeDefinition']
        and proof.get('readMethod')=='ReadUnmanaged'and proof['readerMethodDefinition']==context['methodSpec'][0]
        and proof['targetRva']==source_target-base and proof.get('wireBytes')==proof.get('managedBytes')==24
        and type(proof.get('wireBytes'))is int and type(proof.get('managedBytes'))is int
        and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==PADDING
        and proof.get('resultAbi')=='hidden-local'and proof.get('contextRegister')=='r8'
        and proof.get('actualSourceProved')is True and proof.get('allFourReaderUpdatesProved')is True
        and proof.get('fullFrameAndNonvolatilesRestored')is True and proof.get('pointerAliasClaimed')is False
        and proof.get('wrapperWireUsed')is False and proof.get('boolBytesNormalized')is False)
    return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],
        targetRva=proof['targetRva'],wireBytes=24,managedBytes=24,resultAbi='hidden-local')


def verify(proof,pins):
    """Replay retained exact source bytes; fresh native derivation is separate."""
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    normalize=lambda value:json.loads(json.dumps(value))
    own=proof.get('proof',{});nested=own.get('nestedSource');program_=own.get('actualProgram',{})
    need('own-current-source-declaration',proof.get('nativeInputs')==pins and proof.get('status')=='validated'
        and proof.get('typeName')==TYPE and proof.get('wireBytes')==proof.get('managedBytes')==24
        and proof.get('actualSourceProved')is True and proof.get('pointerAliasClaimed')is False
        and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==PADDING
        and proof.get('wrapperWireUsed')is False and proof.get('boolBytesNormalized')is False)
    if nested is not None:
        need('own-explicit-closed-forwarder',proof.get('schema')=='endfield.camera-initial-raw24-forwarder.v1'
            and proof.get('contextMode')=='owned-closed-forwarder'and proof.get('contextRegister')is None
            and program_==nested.get('proof',{}).get('actualProgram')
            and proof.get('readerMethodDefinition')==nested.get('readerMethodDefinition')
            and proof.get('typeDefinition')==nested.get('typeDefinition')
            and own.get('typedRequest')==nested.get('proof',{}).get('typedRequest'))
        base=verify(nested,pins);forward=own['forwarderProgram'];selected=forward['selectedBytes']
        replay=forwarder_program([(a,bytes.fromhex(h))for a,h in selected],base+proof['targetRva'])
        need('whole-owned-forwarder-replayed',normalize(replay)==forward
            and forward['nestedTargetVa']==base+nested['targetRva']
            and own.get('actualFamily',{}).get('selectedPrimaryRva')==proof['targetRva']
            and forward['contextInstructionVa']-base==own['typedRequest']['instructionRva'])
        chunks=dict(selected);site=forward['contextInstructionVa']
        need('own-actual-internal-context-bytes',chunks.get(site)=='4c8b05'
            and(chunks[site]+chunks.get(site+3,'')).upper()==own['typedRequest'].get('instructionHex'))
        return base
    selected=program_.get('selectedBytes',[])
    need('literal-owned-source-entry',bool(selected)and type(proof.get('targetRva'))is int)
    base=selected[0][0]-proof['targetRva'];usage=own.get('typedRequest',{})
    nominal=own.get('nominalLayout',{});request=dict(methodOwner=usage.get('typeName'),methodName=usage.get('methodName'),
        register='r8',fullTypeName=TYPE,typeKind=17,typeDefinition=nominal.get('typeDefinition'),methodSpec=usage.get('methodSpec'))
    bind(request,base+proof['targetRva'],proof,base=base)
    need('exact-nominal-raw24-program',nominal.get('typeName')==TYPE and nominal.get('fields')==[list(r)for r in FIELDS]
        and nominal.get('managedBytes')==24 and nominal.get('boxedBytes')==40
        and nominal.get('referenceLaneOffsets')==[]and nominal.get('paddingByteRanges')==PADDING
        and nominal.get('marshaledSizeUsedForWidth')is False
        and(usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
            ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE]))
    offsets=own['readerOffsets']
    replay=program([(a,bytes.fromhex(h))for a,h in selected],base+proof['targetRva'],offsets,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,own.get('actualWindows',[]),base))
    need('complete-actual-raw24-replayed',normalize(replay)==program_)
    advance=own.get('advanceSource',{});windows=advance.get('codeWindows',[]);regions=advance.get('sourceRegions',[])
    need('own-complete-independent-Advance',advance.get('nativeInputs')==pins
        and advance.get('targetRva',-base)+base==program_['advanceTargetVa']
        and advance.get('readerOffsets')==offsets and bool(windows)and len(windows)==len(regions)
        and len({a for a,h in regions})==len(regions)
        and all(advance.get(k)is True for k in('completeAdvanceProgramProved','allFourReaderUpdatesProved',
            'entryRspRestored','allNonvolatilesRestored','zeroCountReturnsWithoutMutation'))
        and advance.get('registeredMethodIdentityClaimed')is False)
    for at,h in regions:
        raw=bytes.fromhex(h);matches=[w for w in windows if base+w.get('startRva',-base)==at and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('exact-independent-Advance-owned-bytes',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
    replay=[advance_program([(a,bytes.fromhex(h))for a,h in regions],program_['advanceTargetVa'],offsets,zero=z)for z in(False,True)]
    need('both-complete-Advance-paths-replayed',normalize(replay)==advance.get('programs'))
    return base


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL);nominal=layout(image,ctx)
    need('fresh-exact-typed-request',usage.get('tag')==6 and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
        ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])and usage['methodSpec']==context['methodSpec']
        and usage['instructionHex']==context['instructionHex']and nominal['typeDefinition']==context['typeDefinition'])
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.closedArgument')
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('own-ordinary-closed-type-record',raw.hex().upper()==context['argumentRawHex'].upper()
        and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
    need('owned-noarg-instance-Reader-method',(image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,method.parameter_count)==
        ('MemoryPack.MemoryPackReader','ReadUnmanaged',0,0)and not list(md.parameters_for(method))
        and method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
    container=struct.unpack_from('<iiii',md.buf,at)
    owner=method_parameter_owner(md.buf,container[3],[m.generic_container_index for m in md.methods],source=LABEL)
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('reciprocal-sole-return-MVAR',container[:3]==(method.index,1,1)and owner['methodIndex']==method.index and owner['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
    registered=GenericEntries(image).resolve(method.index,[],[TYPE]);body=pointer.owned(image,source_target)
    offsets=scalar.reader_offsets(image,LABEL);actual=program(body['regions'],source_target,offsets)
    advance=derive_advance(image,pins,target=actual['advanceTargetVa'],offsets=offsets)
    need('same-independent-owned-Advance',advance['targetRva']+base==actual['advanceTargetVa']
        and advance['completeAdvanceProgramProved']is True and advance['allFourReaderUpdatesProved']is True)
    result=json.loads(json.dumps(dict(schema='endfield.camera-initial-raw24-source.v1',status='validated',nativeInputs=pins,
        typeName=TYPE,typeDefinition=nominal['typeDefinition'],readMethod='ReadUnmanaged',readerMethodDefinition=method.index,
        targetRva=source_target-base,wireBytes=24,managedBytes=24,resultAbi='hidden-local',hiddenOutputRegister='rcx',
        readerRegister='rdx',contextRegister='r8',referenceLaneOffsets=[],paddingByteRanges=PADDING,
        actualSourceProved=True,actualEqualsRegisteredPointer=registered['pointer']==source_target,pointerAliasClaimed=False,
        allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,wrapperWireUsed=False,boolBytesNormalized=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(typedRequest=usage,nominalLayout=nominal,
            returnRawHex=returned.hex(),genericParameterOwner=owner,registration=registered,
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            actualProgram=actual,readerOffsets=offsets,advanceSource=advance),
        evidenceBoundary=dict(exact='Own nominal seven-field/padded managed24 and reciprocal actual ReadUnmanaged MVAR; complete actual hidden16+8 source and independent actual Advance24 with all Reader updates and complete frames.',
            conditional='Sufficient contiguous coherent buffered input, nonwrapping counters, disjoint output/Reader/input and compatible normal Win64 calls.',
            structuralOnly='Stored raw Boolean/Single/padding bytes; no runtime camera semantics.',
            unresolved=['refill/error paths','parent local/setter/full frame','separate wrapper MC7 wire/default/adapter','whole enclosing owner/physical EOF']))))
    bind(context,source_target,result,base=base);verify(result,pins);_publication_gate(image,pins);return result


def derive_forwarder(image,pins,*,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.generated_vector3_source import forwarder_program
    _publication_gate(image,pins);base=image.pe.image_base;body=pointer.owned(image,source_target)
    forward=forwarder_program(body['regions'],source_target);contexts=ec.contexts(image,body['rows'])
    need('sole-owned-closed-raw24-request',len(contexts)==1 and contexts[0]['instructionRva']+base==forward['contextInstructionVa'])
    nested=derive(image,pins,context=contexts[0],source_target=forward['nestedTargetVa'])
    result=json.loads(json.dumps(dict(schema='endfield.camera-initial-raw24-forwarder.v1',status='validated',nativeInputs=pins,
        typeName=TYPE,typeDefinition=nested['typeDefinition'],readMethod='ReadUnmanaged',readerMethodDefinition=nested['readerMethodDefinition'],
        targetRva=source_target-base,wireBytes=24,managedBytes=24,resultAbi='hidden-local',hiddenOutputRegister='rcx',
        readerRegister='rdx',contextRegister=None,contextMode='owned-closed-forwarder',referenceLaneOffsets=[],paddingByteRanges=PADDING,
        actualSourceProved=True,pointerAliasClaimed=False,allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,
        wrapperWireUsed=False,boolBytesNormalized=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(forwarderProgram=forward,typedRequest=nested['proof']['typedRequest'],
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            actualProgram=nested['proof']['actualProgram'],nestedSource=nested),
        evidenceBoundary=dict(exact='Own closed helper supplies exact internal ReadUnmanaged InitialParam request, unchanged Reader/output and complete normal return, then joins its independent raw24/Advance24 source.',
            conditional='Coherent closed MethodInfo and nested disjoint buffered input/normal call conditions.',
            unresolved=['parent transfer/frame','wrapper MC7/default/adapter','runtime meaning','whole owner/EOF']))))
    verify(result,pins);_publication_gate(image,pins);return result
