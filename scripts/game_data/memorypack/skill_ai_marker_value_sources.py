"""Own EnemyCheckAIMarkerInfo raw8 source, separate from its wrapper grammar.

The exact ReadUnmanaged call consumes eight bytes, including representation
padding, and returns the unchanged QWORD. Its Boolean and GameplayTag layout
is an independent nominal check, not a width selector or Boolean normalization.
Actual and registered entries are checked separately, and actual Advance owns
the four Reader updates and preserved payload. Ready matching closed contexts,
buffered disjoint storage and normal Win64 calls remain conditions. Wrapper
framing, parent field/frame and effective runtime marker behavior are separate.
"""
import json
import struct

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.AI.EnemyCheckAIMarker+EnemyCheckAIMarkerInfo'
TAG='Beyond.Gameplay.Core.GameplayTag'
WIRE='ai-marker-raw8'
LABEL='skillAiMarkerValue'


def need(key,valid,detail=None):
    if not valid:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])


def layout(image,ctx):
    from scripts.game_data.memorypack import scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE];tag=ctx.index.types[TAG]
    need('own-ordinary-nongeneric-value',ctx.is_value_type(TYPE)and not ctx.is_enum(TYPE)
        and td.generic_container_index<0 and ctx.is_value_type(TAG)and not ctx.is_enum(TAG))
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    actual=[(md.string(f.name_index),*ctx.field(TYPE+'::'+md.string(f.name_index))[1:])for f in fields]
    need('own-bool-and-GameplayTag-fields',actual==[('invert','bool',16),('marker',TAG,20)],actual)
    scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),2,LABEL+'.Boolean')
    scalar.ordinary(image,ctx.type_pointer(fields[1].type_index),17,LABEL+'.GameplayTag')
    raw=image.pe.bytes_at_va(ctx.type_pointer(fields[1].type_index),16)
    need('same-actual-GameplayTag-declaration',int.from_bytes(raw[:8],'little')==tag.index)
    tag_fields=[f for f in md.fields_for(tag)if not ctx.field_attributes(f.type_index)&16]
    need('own-tag-one-Int32-field',len(tag_fields)==1
        and ctx.field(TAG+'::'+md.string(tag_fields[0].name_index))==(TAG,'int',16))
    scalar.ordinary(image,ctx.type_pointer(tag_fields[0].type_index),8,LABEL+'.GameplayTag.Int32')
    sizes=[]
    for definition,expected in((td,(24,8)),(tag,(20,4))):
        need('current-size-table-index',0<=definition.index<image.registration['typeDefinitionsSizesCount'])
        pointer=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
        actual_size=(image.pe.u32_at_va(pointer),image.pe.u32_at_va(pointer+4))
        need('independent-value-size',actual_size==expected,(definition.index,expected,actual_size));sizes.append(actual_size)
    return dict(typeName=TYPE,typeDefinition=td.index,managedBytes=8,boxedBytes=24,
        fields=[dict(name='invert',typeName='bool',managedOffset=0,bytes=1),
            dict(name='marker',typeName=TAG,typeDefinition=tag.index,managedOffset=4,bytes=4)],
        referenceLaneOffsets=[],paddingByteRanges=[[1,4]],wireReadAdmitted=False)


def source_program(regions,entry,offsets):
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('four-independent-Reader-offsets',set(offsets)>=set(keys)
        and len({offsets[key]for key in keys})==4
        and all(type(offsets[key])is int and 0<=offsets[key]<128 for key in keys))
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20',
        '8379'+bytes((offsets['bufferLength'],8)).hex(),'488bf9');g.branch('7d',True,1)
    pointer=g.at;g.take('488b5f'+bytes((offsets['currentPtr'],)).hex(),'ba08000000','488bcf')
    capture=g.at;g.take('488b1b');call=g.at;advance=g.relative('e8')
    g.take('488bc3','488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=8,resultRegister='rax',sourcePointerInstructionVa=pointer,
        captureInstructionVa=capture,sourcePointerRegister='rbx',payloadRegister='rbx',
        advanceCallInstructionVa=call,advanceTargetVa=advance,actualSignedCountArgument=8,
        sourceSlices=[[0,8]],returnSlices=[[0,8]],rawBitsIncludingPaddingUnchanged=True,
        boolNormalizationClaimed=False,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
        normalReturn=True,independentAdvanceSourceRequired=True,managedLayoutUsedForWidth=False)


def _source(image,pins,target,offsets):
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.generated_called_advance_sources import derive as derive_advance
    base=image.pe.image_base;family,windows,rows=ec.family(image,target-base)
    regions=[(base+w['startRva'],image.window_bytes(w))for w in windows]
    program=source_program(regions,target,offsets)
    advance=derive_advance(image,pins,target=program['advanceTargetVa'],offsets=offsets)
    need('own-eight-byte-payload-survives-actual-Advance',advance.get('completeAdvanceProgramProved')is True
        and advance.get('allFourReaderUpdatesProved')is True
        and advance['programs'][0].get('preservedCapturedRegister')=='rbx')
    return dict(targetRva=target-base,family=family,codeWindows=windows,
        sourceRegions=[[at,raw.hex().upper()]for at,raw in regions],program=program,advanceSource=advance,
        completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True)


def bind(context,source_target,proof,*,base):
    need('exact-actual-raw8-request',context.get('methodOwner')=='MemoryPack.MemoryPackReader'
        and context.get('methodName')=='ReadUnmanaged'and context.get('fullTypeName')==TYPE
        and context.get('register')=='rdx'and type(context.get('typeKind'))is int and context['typeKind']==17
        and proof.get('schema')=='endfield.skill-ai-marker-raw8-source.v1'and proof.get('status')=='validated'
        and proof.get('typeName')==TYPE and proof.get('typeDefinition')==context.get('typeDefinition')
        and proof.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
        and type(proof.get('targetRva'))is int and proof['targetRva']==source_target-base
        and proof.get('readMethod')=='ReadUnmanaged'and proof.get('wireBytes')==proof.get('managedBytes')==8
        and proof.get('resultRegister')=='rax'and proof.get('completeBufferedProgram')is True
        and proof.get('entryRspRestored')is True and proof.get('nonvolatilesRestored')is True)
    return dict(typeName=TYPE,typeDefinition=proof['typeDefinition'],wireBytes=8,resultRegister='rax',
        readerMethodDefinition=proof['readerMethodDefinition'],targetRva=proof['targetRva'])


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
    need('exact-owned-context-and-bytes',usage.get('tag')==6
        and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
            ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[TYPE])
        and usage['methodSpec']==context['methodSpec']and usage['instructionHex']==context['instructionHex'])
    nominal=layout(image,ctx);argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.argument')
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    need('same-current-nominal-argument',raw.hex().upper()==context['argumentRawHex'].upper()
        and int.from_bytes(raw[:8],'little')==context['typeDefinition']==nominal['typeDefinition'])
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers']
    at=section.offset+method.generic_container_index*16
    need('own-instance-zeroarg-MVAR-method',method.generic_container_index>=0
        and section.offset<=at<=section.offset+section.size-16 and not method.flags&16
        and method.parameter_count==0 and usage['methodSpec'][1]==-1)
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    identity=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source=LABEL)
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('reciprocal-sole-MVAR-result',(owner,count,is_method)==(method.index,1,1)
        and identity['methodIndex']==method.index and identity['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==start)
    canonical=GenericEntries(image).resolve(method.index,[],[TYPE])
    need('own-closed-registration-index',canonical['methodSpecIndex']==usage['methodSpecIndex'])
    offsets=scalar.reader_offsets(image,LABEL);actual=_source(image,pins,source_target,offsets)
    registered=actual if canonical['pointer']==source_target else _source(image,pins,canonical['pointer'],offsets)
    proof=json.loads(json.dumps(dict(schema='endfield.skill-ai-marker-raw8-source.v1',status='validated',nativeInputs=pins,
        typeName=TYPE,typeDefinition=nominal['typeDefinition'],managedBytes=8,wireBytes=8,resultRegister='rax',
        readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,
        completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=usage,layout=nominal,argumentRawHex=raw.hex().upper(),returnTypeRawHex=returned.hex().upper(),
            genericParameterOwner=identity,closedRegistration=canonical,actualPointerEqualsRegistered=canonical['pointer']==source_target,
            pointerAliasInferred=False,actualSource=actual,registeredSource=registered),
        evidenceBoundary=dict(exact='Own ordinary Boolean/GameplayTag value and padding, reciprocal ReadUnmanaged MVAR, exact closed registration, independently complete actual/canonical QWORD load/return and actual Advance8 effects.',
            conditional=__doc__,structuralOnly='Stored raw representation, including padding; no evaluated marker or Boolean normalization.',
            unresolved=['enclosing named setter/field/frame','wrapper framing','refill and runtime selection','whole owner/physical EOF']))))
    bind(context,source_target,proof,base=base);_publication_gate(image,pins);return proof
