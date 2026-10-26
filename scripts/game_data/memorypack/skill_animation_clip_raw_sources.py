"""Exact AnimationClipAsyncInfo raw36, separate from its MC7 wrapper/ABI40.

The selected original has seven named fields, boxed extent52, marshaled native
extent40 and no references. The actual ReadUnmanaged helper independently
guards36, captures and stores16+16+4 bytes and advances the Reader by36. Boolean
bytes32/33 and padding34..36 remain unchanged. Neither marshaled alignment nor
the ordinary MC7 wrapper supplies this wire width, default or FF framing.

The source requires coherent selected nominal MethodInfo, sufficient contiguous
disjoint input/output/Reader storage, nonwrapping counters and normal compatible
Win64 helpers. Actual parent locals/setters/frames, refill/error paths, runtime
animation resolution and enclosing owner/physical EOF remain separate proofs.
"""
import hashlib
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Montage.AnimationClipAsyncInfo'
LABEL='animationClipRaw36'
SCHEMA='endfield.animation-clip-raw36-source.v1'
CAPABILITY='animation-clip-raw36'
FIELDS=(('montagePathHash','long',16),('length','float',24),('framerate','float',28),
    ('averageSpeed','UnityEngine.Vector3',32),('averageAngularSpeed','float',44),
    ('isHumanoid','bool',48),('isLooping','bool',49))
PADDING=[[34,36]]


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('plain-owned-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and ctx.parent(TYPE)=='System.ValueType'and td.generic_container_index<0)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('exact-seven-named-fields',actual==list(FIELDS))
    for field,(_,typename,_)in zip(fields,FIELDS,strict=True):
        scalar.ordinary(image,ctx.type_pointer(field.type_index),{'long':10,'float':12,'bool':2,'UnityEngine.Vector3':17}[typename],LABEL+'.field')
    vector=ctx.index.types['UnityEngine.Vector3'];vf=[f for f in md.fields_for(vector)if not ctx.field_attributes(f.type_index)&16]
    vectors=[(md.string(f.name_index),*ctx.field('UnityEngine.Vector3::'+md.string(f.name_index))[1:])for f in vf]
    need('own-inline-vector3-value',ctx.is_value_type('UnityEngine.Vector3')and not ctx.is_enum('UnityEngine.Vector3')
        and vector.generic_container_index<0 and ctx.parent('UnityEngine.Vector3')=='System.ValueType'
        and vectors==[(n,'float',16+4*i)for i,n in enumerate(('x','y','z'))])
    for field in vf:scalar.ordinary(image,ctx.type_pointer(field.type_index),12,LABEL+'.vector-lane')
    need('bounded-selected-size-rows',all(0<=t.index<image.registration['typeDefinitionsSizesCount']for t in(td,vector)))
    table=int(image.registration['typeDefinitionsSizes'],16)
    sizes=image.pe.u64_at_va(table+td.index*8);vs=image.pe.u64_at_va(table+vector.index*8)
    need('explicit-boxed52-and-distinct-native40',image.pe.u32_at_va(sizes)==52 and image.pe.u32_at_va(sizes+4)==40)
    need('own-vector3-size-row',image.pe.u32_at_va(vs)==28 and image.pe.u32_at_va(vs+4)==12)
    return dict(typeName=TYPE,typeDefinition=td.index,fields=actual,boxedBytes=52,managedPayloadBytes=36,
        marshaledNativeBytes=40,marshaledSizeUsedForWireWidth=False,referenceLaneOffsets=[],paddingByteRanges=PADDING,
        vector3=dict(typeDefinition=vector.index,fields=vectors,managedBytes=12),wireReadAdmitted=False)


def program(regions,entry,offsets,*,path_factory=None):
    need('callable-path-factory',path_factory is None or callable(path_factory))
    rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('48895c2408','57','4883ec20','837a'+rem+'24','488bda','488bf9');g.branch('0f8c',False)
    g.take('488b43'+cur,'ba24000000','488bcb','0f1000','0f104810','8b4020','0f1107','0f114f10','894720')
    call=g.at;advance=g.relative('e8');g.take('488b5c2430','488bc7','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=36,managedOutputBytes=36,hiddenOutputRegister='rcx',readerRegister='rdx',
        methodInfoRegister='r8',capturedSourceSlices=[[0,16],[16,16],[32,4]],storedOutputSlices=[[0,16],[16,16],[32,4]],
        advanceCallInstructionVa=call,advanceTargetVa=advance,actualAdvanceReader='rbx',actualSignedAdvanceCount=36,
        sameOutputReturnedInRax=True,fullFrameAndNonvolatilesRestored=True,normalReturn=True,
        independentAdvanceSourceRequired=True,boolBytesNormalized=False,paddingBytesCopied=True)


def _capture(g,entry,offsets):
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('distinct-owned-reader-slots',set(offsets)>=set(keys)and len({offsets[k]for k in keys})==4
        and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    rem=bytes((offsets['bufferLength'],)).hex();cur=bytes((offsets['currentPtr'],)).hex()
    g.take('837b'+rem+'24');wrapper=g.at;g.take('488b37');guard=g.at
    cold=guard+6+int.from_bytes(bytes(g.bytes.get(guard+i,0)for i in range(2,6)),'little',signed=True)
    g.branch('0f8c',False);pointer=g.at;g.take('488b43'+cur,'ba24000000','488bcb')
    low=g.at;g.take('0f1030');last=g.at;g.take('8b6820');high=g.at;g.take('0f107810')
    call=g.at;advance=g.relative('e8')
    need('refill-outside-capture',not entry<=cold<g.at)
    return dict(selectedBytes=g.seen,nextInstructionVa=g.at,guardInstructionVa=entry,refillTargetVa=cold,
        sourcePointerInstructionVa=pointer,sourcePointerRegister='rax',wireBytes=36,
        capturedSourceSlices=[dict(register='xmm6',sourceOffset=0,bytes=16,loadInstructionVa=low,kind='sse'),
            dict(register='rbp',sourceOffset=32,bytes=4,loadInstructionVa=last,kind='integer'),
            dict(register='xmm7',sourceOffset=16,bytes=16,loadInstructionVa=high,kind='sse')],
        sourceLocalValues=[],wrapperLoad=dict(instructionVa=wrapper,register='rsi',outputRegister='rdi'),remainingRegister=None,
        readerOffsets={k:offsets[k]for k in keys},advanceCallInstructionVa=call,advanceTargetVa=advance,
        actualReaderArgument='rbx',actualSignedCountArgument=36,independentAdvanceSourceRequired=True,
        completeSourceBitsCaptured=True,preservedCaptureRegistersRequired=['xmm6','rbp','xmm7'],
        managedLayoutUsedForWidth=False,typedReadUnmanagedClaimed=False,fieldTransferProved=False,callerFrameProved=False,
        boolBytesNormalized=False,paddingBytesCopied=True)


def capture_program(regions,entry,offsets,*,path_factory=None):
    """Literal buffered capture through Advance36; parent effects stay closed."""
    need('callable-capture-path',path_factory is None or callable(path_factory))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    return _capture(g,entry,offsets)


def inline_program(regions,entry,offsets,*,field,path_factory=None):
    """Own one actual buffered/cached-getter field segment, not its parent."""
    need('literal-inline-field',type(field)is int and 16<=field<(1<<31)-36)
    need('callable-inline-path',path_factory is None or callable(path_factory))
    from scripts.game_data.memorypack.generated_member_sources import _displacement
    g=(BytesPath if path_factory is None else path_factory)(regions,entry);capture=_capture(g,entry,offsets)
    g.take('4885f6');null=g.relative('0f84')
    g.take('33d2','488bce');getter_site=g.at;getter=g.relative('e8');g.take('4885c0')
    need('same-inline-null-guard',g.relative('0f84')==null)
    g.take(_displacement('0f11b0',field),'488bcb',_displacement('0f11b8',field+16),_displacement('89a8',field+32))
    need('inline-guards-outside-normal-segment',not entry<=capture['refillTargetVa']<g.at and not entry<=null<g.at)
    return dict(selectedBytes=g.seen,wireBytes=36,storedBytes=36,readerRegister='rbx',wrapperHolderRegister='rdi',
        capturedSourceSlices=[[0,16,'xmm6'],[32,4,'ebp'],[16,16,'xmm7']],
        storedOutputSlices=[[0,16,'xmm6'],[16,16,'xmm7'],[32,4,'ebp']],fieldOffset=field,
        advanceCallInstructionVa=capture['advanceCallInstructionVa'],advanceTargetVa=capture['advanceTargetVa'],actualSignedAdvanceCount=36,
        getterCallInstructionVa=getter_site,getterTargetVa=getter,originalResultRegister='rax',
        guardInstructionVa=entry,refillTargetVa=capture['refillTargetVa'],nullTargetVa=null,capturedAcrossCallsUnderWin64Preservation=True,
        completeSourceBitsStoredUnchanged=True,boolBytesNormalized=False,paddingBytesCopied=True,
        inputReaderAndHolderOriginsRequired=True,ownGetterSemanticsRequired=True,parentFrameRequired=True,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False)


def bind(context,source_target,proof,*,base):
    need('literal-nominal-source',type(base)is int and type(source_target)is int and source_target>base
        and type(context.get('typeDefinition'))is int and type(context.get('typeKind'))is int
        and isinstance(context.get('methodSpec'),(tuple,list))and len(context['methodSpec'])==3
        and type(context['methodSpec'][0])is int and type(proof.get('readerMethodDefinition'))is int
        and type(proof.get('targetRva'))is int)
    need('actual-closed-raw36-request',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('register')=='r8'
        and context.get('fullTypeName')==TYPE and context['typeKind']==17
        and proof.get('schema')==SCHEMA and proof.get('status')=='validated'and proof.get('typeName')==TYPE
        and proof.get('typeDefinition')==context['typeDefinition']and proof.get('readMethod')=='ReadUnmanaged'
        and proof['readerMethodDefinition']==context['methodSpec'][0]and proof['targetRva']==source_target-base
        and all(type(proof.get(k))is int and proof[k]==36 for k in('wireBytes','managedBytes'))
        and type(proof.get('nativeAbiBytes'))is int and proof['nativeAbiBytes']==40
        and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==PADDING
        and proof.get('resultAbi')=='hidden-local'and proof.get('contextRegister')=='r8'
        and all(proof.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','fullFrameAndNonvolatilesRestored'))
        and all(proof.get(k)is False for k in('pointerAliasClaimed','wrapperWireUsed','boolBytesNormalized')))
    return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],
        targetRva=proof['targetRva'],wireBytes=36,managedBytes=36,nativeAbiBytes=40,resultAbi='hidden-local')


def verify(proof,pins):
    """Replay retained source bytes; fresh native derivation remains separate."""
    from scripts.game_data.memorypack.generated_inline_record_components import _owned_setter_trace
    from scripts.game_data.memorypack.generated_called_advance_sources import advance_program
    own=proof.get('proof',{});actual=own.get('actualProgram',{});selected=actual.get('selectedBytes',[])
    need('same-selected-source-and-entry',proof.get('nativeInputs')==pins and bool(selected)and type(proof.get('targetRva'))is int)
    base=selected[0][0]-proof['targetRva'];nominal=own.get('nominalLayout',{});usage=own.get('typedRequest',{})
    context=dict(methodOwner=usage.get('typeName'),methodName=usage.get('methodName'),register='r8',fullTypeName=TYPE,
        typeKind=17,typeDefinition=nominal.get('typeDefinition'),methodSpec=usage.get('methodSpec'))
    bind(context,base+proof['targetRva'],proof,base=base)
    need('exact-retained-nominal-request',usage.get('tag')==6
        and tuple(usage.get(k)for k in('typeName','methodName','classArguments','methodArguments'))==
            ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and len(bytes.fromhex(usage.get('instructionHex','')))==7
        and bytes.fromhex(usage['instructionHex'])[:3]==bytes.fromhex('4c8b05'))
    need('exact-owned-layout-not-native-width',nominal.get('typeName')==TYPE and nominal.get('fields')==[list(r)for r in FIELDS]
        and nominal.get('boxedBytes')==52 and nominal.get('managedPayloadBytes')==36 and nominal.get('marshaledNativeBytes')==40
        and nominal.get('marshaledSizeUsedForWireWidth')is False and nominal.get('referenceLaneOffsets')==[]
        and nominal.get('paddingByteRanges')==PADDING
        and nominal.get('vector3',{}).get('fields')==[[n,'float',16+4*i]for i,n in enumerate(('x','y','z'))]
        and nominal['vector3'].get('managedBytes')==12 and type(nominal['vector3'].get('typeDefinition'))is int)
    normalize=lambda value:json.loads(json.dumps(value));offsets=own['readerOffsets']
    replay=program([(a,bytes.fromhex(h))for a,h in selected],base+proof['targetRva'],offsets,
        path_factory=lambda regions,entry:_owned_setter_trace(regions,entry,own.get('actualWindows',[]),base))
    need('complete-actual-raw36-replayed',normalize(replay)==actual)
    advance=own.get('advanceSource',{});windows=advance.get('codeWindows',[]);regions=advance.get('sourceRegions',[])
    need('independent-complete-Advance36',advance.get('nativeInputs')==pins and advance.get('targetRva',-base)+base==actual['advanceTargetVa']
        and advance.get('readerOffsets')==offsets and bool(windows)and len(windows)==len(regions)
        and len({a for a,h in regions})==len(regions)and advance.get('registeredMethodIdentityClaimed')is False
        and all(advance.get(k)is True for k in('completeAdvanceProgramProved','allFourReaderUpdatesProved',
            'entryRspRestored','allNonvolatilesRestored','zeroCountReturnsWithoutMutation')))
    for at,h in regions:
        raw=bytes.fromhex(h);matches=[w for w in windows if base+w.get('startRva',-base)==at and w.get('endRva',0)-w.get('startRva',0)==len(raw)]
        need('exact-Advance-owned-window',len(matches)==1 and hashlib.sha256(raw).hexdigest().upper()==matches[0].get('sha256'))
    replay=[advance_program([(a,bytes.fromhex(h))for a,h in regions],actual['advanceTargetVa'],offsets,zero=z)for z in(False,True)]
    need('both-independent-Advance-paths',normalize(replay)==advance.get('programs'))
    return base


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as advance_source
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    nominal=layout(image,ctx);usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
    need('fresh-exact-nominal-request',usage.get('tag')==6 and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
        ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])and usage['methodSpec']==context['methodSpec']
        and usage['instructionHex']==context['instructionHex']and nominal['typeDefinition']==context['typeDefinition']
        and len(bytes.fromhex(usage['instructionHex']))==7 and bytes.fromhex(usage['instructionHex'])[:3]==bytes.fromhex('4c8b05'))
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments;raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.closedArgument')
    need('own-closed-value17-record',raw.hex().upper()==context['argumentRawHex'].upper()
        and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
    need('own-instance-Reader-method',(image.type_name(method.declaring_type),md.string(method.name_index),method.flags&16,method.parameter_count)==
        ('MemoryPack.MemoryPackReader','ReadUnmanaged',0,0)and not list(md.parameters_for(method))
        and method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16)
    container=struct.unpack_from('<iiii',md.buf,at);returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    owner=method_parameter_owner(md.buf,container[3],[m.generic_container_index for m in md.methods],source=LABEL)
    need('reciprocal-sole-return-MVAR',container[:3]==(method.index,1,1)and owner['methodIndex']==method.index and owner['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
    registered=GenericEntries(image).resolve(method.index,[],[TYPE]);body=pointer.owned(image,source_target)
    offsets=scalar.reader_offsets(image,LABEL);actual=program(body['regions'],source_target,offsets)
    advance=advance_source(image,pins,target=actual['advanceTargetVa'],offsets=offsets)
    result=json.loads(json.dumps(dict(schema=SCHEMA,status='validated',nativeInputs=pins,typeName=TYPE,
        typeDefinition=nominal['typeDefinition'],readMethod='ReadUnmanaged',readerMethodDefinition=method.index,
        targetRva=source_target-base,wireBytes=36,managedBytes=36,nativeAbiBytes=40,resultAbi='hidden-local',
        hiddenOutputRegister='rcx',readerRegister='rdx',contextRegister='r8',referenceLaneOffsets=[],paddingByteRanges=PADDING,
        actualSourceProved=True,actualEqualsRegisteredPointer=registered['pointer']==source_target,pointerAliasClaimed=False,
        allFourReaderUpdatesProved=True,fullFrameAndNonvolatilesRestored=True,wrapperWireUsed=False,boolBytesNormalized=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,proof=dict(typedRequest=usage,nominalLayout=nominal,
            returnRawHex=returned.hex(),genericParameterOwner=owner,registration=registered,
            actualFamily=image.unwind_index.family(source_target-base),actualWindows=body['windows'],
            actualProgram=actual,readerOffsets=offsets,advanceSource=advance),evidenceBoundary=dict(
            exact='Own seven-field/no-reference nominal layout with boxed52/nativeABI40 separate from actual hidden36 split16+16+4 source and independent Advance36.',
            conditional=__doc__,structuralOnly='Stored clip hash, IEEE bits, raw Boolean and padding bytes.',
            unresolved=['actual parent local/setter/frame','refill/error paths','ordinary MC7/default/FF wrapper','runtime animation/owner/EOF']))))
    bind(context,source_target,result,base=base);verify(result,pins);_publication_gate(image,pins);return result
