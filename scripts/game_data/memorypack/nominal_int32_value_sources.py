"""Named one-Int32 values with an actual typed raw4/EAX source.

An independently current ordinary value declaration and reciprocal Reader
ReadUnmanaged MVAR request supply nominal identity. Complete actual and closed
registered source programs supply four consumed bytes and unchanged EAX bits;
their pointers are compared explicitly, never equated by width or name.
Wrapper framing, enclosing setter/frame and runtime meaning remain separate.
"""
import struct

LABEL='nominalInt32Value'

def need(k,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+k+':'+str(detail)[:650])

def int32_rdi_program(regions,entry,offsets):
    """Own the complete RDI Reader/EBX payload buffered program and full frame."""
    from scripts.game_data.memorypack.modelview_sources import audio_id_source
    keys=('currentPtr','bufferLength','advancedCount','consumed')
    need('literal-current-reader-offsets',set(offsets)==set(keys)and all(type(offsets[k])is int and 0<=offsets[k]<128 for k in keys))
    program=audio_id_source(regions,entry,offsets);selected=program['selectedBytes']
    code={a+i:b for a,raw in regions for i,b in enumerate(raw)}
    guards=[at+6+int.from_bytes(bytes(code[at+2+i]for i in range(4)),'little',signed=True)for at,h in selected if h in('0f8c','0f88')]
    end=max(at+len(bytes.fromhex(h))for at,h in selected)
    need('guards-leave-warm-program-and-stay-owned',len(guards)==2 and all(not entry<=target<end and any(a<=target<a+len(raw)for a,raw in regions)for target in guards))
    return dict(selectedBytes=selected,wireBytes=4,resultRegister='eax',sourceBytes=4,
        readerRegister='rdi',payloadRegister='ebx',fourCursorUpdatesProved=True,rawInt32BitsUnchanged=True,
        guardTargets=guards,entryRspRestored=True,nonvolatilesRestored=['rbx','rsi','rdi'],normalReturn=True)

def _buffered_source(image,target,offsets):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_primitive_sources as primitive,generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.modelview_sources import audio_id_source
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    try:return primitive.derive(image,target,'int32',offsets)
    except ValueError as initial:
        body=members._body(image,target)
        advanced=None
        try:program=int32_rdi_program(body['regions'],target,offsets)
        except ValueError as exact:
            # The independent registered body may call Advance(4). Authenticate
            # both complete source programs and the actual callee, with no alias.
            record=vector_recorder(image)(target-image.pe.image_base,fragments=True)
            need('registered-Advance-profile-call',len(record['instructions'])==19 and bytes.fromhex(record['instructions'][13][1])[:1]==b'\xe8')
            at,raw=record['instructions'][13];advance=image.pe.image_base+at+5+int.from_bytes(bytes.fromhex(raw)[1:],'little',signed=True)
            advanced=vector_recorder(image)(advance-image.pe.image_base,fragments=True);record['advance']=advanced
            scalar.int32_advanced_source(image,record,offsets)
            selected=NativeReferenceContext(image);md=image.metadata
            methods=[m for m in md.methods_for(selected.index.types['MemoryPack.MemoryPackReader'])if md.string(m.name_index)=='Advance'and m.parameter_count==1 and not m.flags&16]
            need('one-current-named-Advance-ABI',len(methods)==1);method=methods[0];parameters=list(md.parameters_for(method))
            need('current-Advance-formals',selected.is_value_type('MemoryPack.MemoryPackReader')and
                (selected.type_name(method.return_type),[selected.type_name(p.type_index)for p in parameters],method.generic_container_index)==('void',['int'],-1))
            scalar.ordinary(image,selected.type_pointer(method.return_type),1,LABEL+'.Advance.return')
            scalar.ordinary(image,selected.type_pointer(parameters[0].type_index),8,LABEL+'.Advance.count')
            program=audio_id_source(body['regions'],target,offsets,registered=True,advance=advance)
            program.update(resultRegister='eax',rawInt32BitsUnchanged=True,fourCursorUpdatesProved=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'])
            advanced=dict(source=advanced,namedAdvanceMethod=[method.index,image.type_name(method.declaring_type),'Advance',image.method_pointer_va(method)-image.pe.image_base],
                actualTargetRva=advance-image.pe.image_base,actualManagedEntryIdentityClaimed=False)
        return dict(kind='int32',targetRva=target-image.pe.image_base,family=body['family'],codeWindows=body['windows'],
            profile='reader-rdi-payload-ebx'+('-Advance4'if advanced else''),sourceProgram=program,advance=advanced,wireBytes=4,resultRegister='eax',
            completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True,
            conditional='Enough contiguous disjoint buffered input and coherent Reader; refill/error paths remain unadmitted.')

def bind(context,source_target,proof,*,base):
    need('literal-actual-source-target',type(source_target)is int and source_target>0 and type(base)is int)
    need('literal-current-identities',type(context.get('typeDefinition'))is int and context['typeDefinition']>=0
        and isinstance(context.get('methodSpec'),(list,tuple))and len(context['methodSpec'])==3
        and type(context['methodSpec'][0])is int and context['methodSpec'][0]>=0
        and type(proof.get('typeDefinition'))is int and type(proof.get('readerMethodDefinition'))is int
        and type(proof.get('targetRva'))is int)
    need('actual-request-and-source',context.get('methodOwner')=='MemoryPack.MemoryPackReader'and context.get('methodName')=='ReadUnmanaged'
        and context.get('register')=='rdx'and type(context.get('typeKind'))is int and context['typeKind']==17
        and proof.get('schema')=='endfield.nominal-int32-value-source.v1'and proof.get('status')=='validated'
        and proof.get('typeName')==context.get('fullTypeName')and proof.get('typeDefinition')==context.get('typeDefinition')
        and proof.get('readMethod')=='ReadUnmanaged'and proof.get('readerMethodDefinition')==context.get('methodSpec',[None])[0]
        and type(proof.get('wireBytes'))is int and proof['wireBytes']==4 and proof.get('managedBytes')==4
        and proof.get('targetRva')==source_target-base and proof.get('resultRegister')=='eax'
        and proof.get('completeBufferedProgram')is True and proof.get('entryRspRestored')is True and proof.get('nonvolatilesRestored')is True)
    return dict(typeName=proof['typeName'],typeDefinition=proof['typeDefinition'],readerMethodDefinition=proof['readerMethodDefinition'],targetRva=proof['targetRva'],wireBytes=4,resultRegister='eax')

def derive(image,pins,*,context,source_target):
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_primitive_sources as primitive,scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    usage=derive_typed_usage_context(image,context['instructionRva'],label=LABEL)
    name=context['fullTypeName'];td=ctx.index.types[name]
    need('exact-actual-typed-request',usage['tag']==6 and(usage['typeName'],usage['methodName'],usage['classArguments'],usage['methodArguments'])==
        ('MemoryPack.MemoryPackReader','ReadUnmanaged',[],[name])and usage['instructionHex']==context['instructionHex']and usage['methodSpec']==context['methodSpec'])
    need('current-nongeneric-nonenum-value',ctx.is_value_type(name)and not ctx.is_enum(name)and td.generic_container_index<0 and td.index==context['typeDefinition'])
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    raw=image.pe.bytes_at_va(argument.type_pointer_va,16)
    scalar.ordinary(image,argument.type_pointer_va,17,LABEL+'.argument')
    need('same-current-closed-ordinary-type',raw.hex().upper()==context['argumentRawHex'].upper()and int.from_bytes(raw[:8],'little')==td.index)
    fields=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
    need('one-current-nonstatic-Int32-field',len(fields)==1)
    field=fields[0];fact=ctx.field(name+'::'+md.string(field.name_index))
    need('exact-current-Int32-field',fact==(name,'int',16));scalar.ordinary(image,ctx.type_pointer(field.type_index),8,LABEL+'.field')
    need('current-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
    need('current-managed4-layout',(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4))==(20,4))
    method=md.methods[usage['methodSpec'][0]];section=md.sections['genericContainers'];at=section.offset+method.generic_container_index*16
    need('owned-Reader-return-MVAR',method.generic_container_index>=0 and section.offset<=at<=section.offset+section.size-16 and not method.flags&16 and method.parameter_count==0 and usage['methodSpec'][1]==-1)
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    identity=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source=LABEL)
    returned=image.pe.bytes_at_va(ctx.type_pointer(method.return_type),16)
    need('reciprocal-own-sole-MVAR-return',(owner,count,is_method)==(method.index,1,1)and identity['methodIndex']==method.index and identity['ordinal']==0
        and returned[10:12]==bytes((30,0))and int.from_bytes(returned[:8],'little')==start)
    canonical=GenericEntries(image).resolve(method.index,[],[name]);offsets=scalar.reader_offsets(image,LABEL)
    actual=_buffered_source(image,source_target,offsets)
    registered=actual if canonical['pointer']==source_target else _buffered_source(image,canonical['pointer'],offsets)
    _publication_gate(image,pins)
    result=json.loads(json.dumps(dict(schema='endfield.nominal-int32-value-source.v1',status='validated',nativeInputs=pins,typeName=name,typeDefinition=td.index,
        readMethod='ReadUnmanaged',readerMethodDefinition=method.index,targetRva=source_target-base,wireBytes=4,managedBytes=4,resultRegister='eax',
        completeBufferedProgram=True,entryRspRestored=True,nonvolatilesRestored=True,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(typedRequest=usage,argumentRawHex=raw.hex().upper(),returnTypeRawHex=returned.hex().upper(),genericParameterOwner=identity,
            fieldName=md.string(field.name_index),field=fact,closedRegistration=canonical,actualPointerEqualsRegistered=canonical['pointer']==source_target,
            pointerAliasInferred=False,actualSource=actual,registeredSource=registered),
        evidenceBoundary=dict(exact='Fresh one-Int32 nominal value/field declaration, reciprocal ReadUnmanaged MVAR and exact closed registration, independently complete actual/canonical four-byte cursor and EAX return source programs.',
            conditional=__doc__+' Ready coherent requested closed MethodInfo, enough contiguous disjoint buffered input, normal Win64 invocation. Managed4 is checked independently and does not choose the wire program.',
            structuralOnly='Stored signed Int32 bits with current nominal type ownership; no runtime domain meaning.',
            unresolved=['enclosing source-to-setter/frame/owner','wrapper formatter framing','refill/error paths','runtime meaning']))))
    bind(context,source_target,result,base=base);return result
