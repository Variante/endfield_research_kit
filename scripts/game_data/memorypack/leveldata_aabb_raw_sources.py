"""Actual ReadUnmanaged<AABB> hidden16 source, separate from its MC2 wrapper.

The Node field calls this raw source directly. Its warmed path captures all
sixteen bytes, stores them unchanged and invokes its own Advance with length16.
The actual Advance independently proves the four Reader updates. No AABB
formatter, wrapper header, default marker or registered-body alias is inferred.
"""
import json,struct
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.AABB'
SCHEMA='endfield.leveldata-AABB-raw-source.v2'


def need(check,condition):
    if not condition:raise ValueError('polylineAabbRaw.'+check)


def program(regions,entry,offsets,*,advance=None,path_factory=None):
    need('callable-only-path-factory',path_factory is None or callable(path_factory))
    need('literal-advance-target',advance is None or type(advance)is int and advance>0)
    cur,remaining=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength'))
    g=(BytesPath if path_factory is None else path_factory)(regions,entry)
    g.take('48895c2408','57','4883ec20','837a'+remaining+'10','488bda','488bf9');g.branch('7d',True,1)
    g.take('488b43'+cur,'ba10000000','488bcb','0f1000','0f1107');call_at=g.at;actual=g.relative('e8')
    need('actual-owned-Advance',advance is None or advance==actual)
    g.take('488b5c2430','488bc7','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,advanceCallVa=call_at,advanceTargetVa=actual,advanceLength=16,
        wireBytes=16,managedOutputBytes=16,capturedSourceSlices=[[0,16]],storedOutputSlices=[[0,16]],
        hiddenOutputRegister='rcx',readerRegister='rdx',methodInfoRegister='r8',sameOutputReturnedInRax=True,
        sourcePayloadStoredBeforeAdvance=True,sameReaderPassedToAdvance=True,
        fullFrameAndNonvolatilesRestored=True,normalReturn=True,refillPathAdmitted=False)


def bind(context,source_target,proof,*,base):
    raw=bytes.fromhex(context.get('argumentRawHex',''))
    need('exact-own-actual-raw16-identity',type(source_target)is int and type(base)is int and source_target>base
        and context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
        and context.get('register')=='r8'and context.get('fullTypeName')==TYPE and context.get('typeKind')==17
        and type(context.get('typeDefinition'))is int and len(raw)==16 and raw[10:12]==bytes((17,128))
        and int.from_bytes(raw[:8],'little')==context['typeDefinition']
        and proof.get('schema')==SCHEMA and proof.get('status')=='validated'and proof.get('typeName')==TYPE
        and proof.get('typeDefinition')==context['typeDefinition']and proof.get('readMethod')=='ReadUnmanaged'
        and proof.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
        and proof.get('targetRva')==source_target-base
        and type(proof.get('wireBytes'))is int and proof.get('wireBytes')==proof.get('managedBytes')==16
        and proof.get('referenceLaneOffsets')==[]and proof.get('paddingByteRanges')==[]
        and proof.get('resultAbi')=='hidden-local'and proof.get('contextRegister')=='r8'
        and all(proof.get(k)is True for k in('actualSourceProved','allFourReaderUpdatesProved','fullFrameAndNonvolatilesRestored'))
        and proof.get('pointerAliasClaimed')is False)
    return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],
        targetRva=proof['targetRva'],wireBytes=16,managedBytes=16,resultAbi='hidden-local')


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    from scripts.game_data.memorypack.leveldata_aabb_value_sources import layout
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need('literal-actual-context',isinstance(context,dict)and context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('fullTypeName')==TYPE
        and context.get('typeKind')==17 and context.get('register')=='r8')
    usage=derive_typed_usage_context(image,context['instructionRva'],label='polylineAabbRaw.actual')
    need('same-fresh-nominal-ReadUnmanaged',tuple(usage.get(k)for k in('tag','typeName','methodName','classArguments','methodArguments'))
        ==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    nominal=layout(image,ctx);need('same-nominal-definition',nominal['typeDefinition']==context['typeDefinition'])
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    scalar.ordinary(image,argument.type_pointer_va,17,'polylineAabbRaw.closedAABB')
    need('same-actual-closed-carrier',raw.hex().upper()==context.get('argumentRawHex','').upper()
        and int.from_bytes(raw[:8],'little')==nominal['typeDefinition'])
    method=md.methods[usage['methodSpec'][0]]
    need('own-noarg-instance-ReadUnmanaged',image.type_name(method.declaring_type)=='MemoryPack.MemoryPackReader'
        and md.string(method.name_index)=='ReadUnmanaged'and not method.flags&16 and method.parameter_count==0
        and list(md.parameters_for(method))==[]and method.generic_container_index>=0)
    section=md.sections['genericContainers'];at=section.offset+16*method.generic_container_index
    need('bounded-method-container',section.offset<=at<=section.offset+section.size-16)
    container=struct.unpack_from('<iiii',md.buf,at)
    need('one-owned-method-MVAR',container[:3]==(method.index,1,1))
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('exact-owned-return-MVAR',returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==container[3])
    registered=GenericEntries(image).resolve(method.index,[],[TYPE])
    need('same-registered-MethodSpec',registered['methodSpecIndex']==usage['methodSpecIndex'])
    body=owned(image,source_target);offsets=scalar.reader_offsets(image,'polylineAabbRaw')
    actual=program(body['regions'],source_target,offsets)
    advance=derive_advance(image,pins,target=actual['advanceTargetVa'],offsets=offsets)
    result=dict(schema=SCHEMA,status='validated',nativeInputs=pins,typeName=TYPE,typeDefinition=nominal['typeDefinition'],
        readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,
        wireBytes=16,managedBytes=16,resultAbi='hidden-local',hiddenOutputRegister='rcx',readerRegister='rdx',contextRegister='r8',
        referenceLaneOffsets=[],paddingByteRanges=[],actualSourceProved=True,allFourReaderUpdatesProved=True,
        fullFrameAndNonvolatilesRestored=True,actualEqualsRegisteredPointer=source_target==registered['pointer'],pointerAliasClaimed=False,
        wholeOwnerAdmitted=False,proof=dict(typedRequest=usage,registration=registered,nominalLayout=nominal,
            methodContainer=container,returnRawHex=returned.hex().upper(),actualProgram=actual,advanceSource=advance,
            actualWindows=body['windows'],actualFamily=image.unwind_index.family(source_target-base),
            actualRegions=[[a-base,b.hex().upper()]for a,b in body['regions']],readerOffsets=offsets),
        evidenceBoundary=dict(exact='Own current AABB/Vector2 declarations, actual closed ReadUnmanaged return-MVAR request, warmed full raw16 capture/store/return/frame and actual Advance16 four-Reader-field updates.',
            conditional=__doc__+' Sufficient coherent buffered input, nonwrapping counters, stable disjoint source/hidden-output/frame and normal compatible Advance.',
            unresolved=['refill/error paths','Node local/setter/full caller transfer','whole Polyline grammar and EOF','runtime geometry meaning']))
    bind(context,source_target,result,base=base);_publication_gate(image,pins)
    return json.loads(json.dumps(result))
