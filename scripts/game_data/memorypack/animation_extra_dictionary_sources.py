"""Finite nominal static-out dictionary sources below Animation ExtraData.

Each actual R8 MethodInfo and E8 body is independently bound. Source paths
prove framing and full key/reference transfers; key formatter semantics,
concrete children, parent fields and runtime provider selection stay separate.
"""
import json

OWNER='Beyond.SerializeFieldDictionary`2'
PREFIX='Beyond.Gameplay.View.Animation.'
DOMAINS={
    ('Beyond.Gameplay.Core.CharHurtAnim',PREFIX+'CharacterAnimExtraData+CharHurtAnimConfig'):('enum4-reference',4),
    ('string',PREFIX+'CharacterAnimExtraData+CharMoveAdditiveAnimConfig'):('string-reference',8),
    ('string','string'):('string-reference',8),
    ('Beyond.Gameplay.Core.EnemyHurtAnim',PREFIX+'EnemyAnimExtraData+EnemyHurtAnimEntry'):('enum4-reference',4),
    ('Beyond.Gameplay.Core.EnemyHurtShakeIntensity',PREFIX+'EnemyAnimExtraData+EnemyHurtShakeIntensityConfig'):('enum1-value8',1),
}
TYPES={OWNER+'<'+key+','+value+'>':(key,value)for key,value in DOMAINS}
LABEL='animationExtraDictionarySource'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def request_shape(usage):
    arguments=usage.get('classArguments',[]);key=tuple(arguments)if isinstance(arguments,(list,tuple))else()
    raw=bytes.fromhex(usage.get('instructionHex',''));spec=usage.get('methodSpec')
    need('finite-actual-R8-class-only-request',key in DOMAINS and usage.get('tag')==6
        and(usage.get('typeName'),usage.get('methodName'),usage.get('methodArguments'))==(OWNER,'DeserializeV2',[])
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')and type(usage.get('instructionRva'))is int
        and usage['instructionRva']>=0 and isinstance(spec,(list,tuple))and len(spec)==3
        and all(type(n)is int for n in spec)and spec[0]>=0 and spec[1]>=0 and spec[2]==-1)
    return key


def request_context(image,instruction_rva):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    usage=derive_typed_usage_context(image,instruction_rva,label=LABEL);key,value=request_shape(usage)
    ctx=NativeReferenceContext(image);md=image.metadata;owner=ctx.index.types[OWNER]
    args=image.instantiations.resolve(usage['methodSpec'][1]).arguments;need('two-actual-class-arguments',len(args)==2)
    facts=[]
    for name,arg in zip((key,value),args,strict=True):
        kind=14 if name=='string'else 17 if name==key or DOMAINS[(key,value)][0]=='enum1-value8'else 18
        scalar.ordinary(image,arg.type_pointer_va,kind,LABEL+'.argument',reference=kind in(14,18))
        raw=image.pe.bytes_at_va(arg.type_pointer_va,16)
        need('actual-own-nominal-carrier',raw[10:12]==bytes((kind,0 if kind in(14,18)else 128))
            and(kind==14 or int.from_bytes(raw[:8],'little')==ctx.index.types[name].index))
        fact=dict(typeName=name,typeKind=kind,rawTypeRecordHex=raw.hex().upper(),
            typeDefinition=None if kind==14 else ctx.index.types[name].index)
        if kind==17 and name==key:
            width=DOMAINS[(key,value)][1];expected='int'if width==4 else'byte'
            fields=[f for f in md.fields_for(ctx.index.types[name])if not ctx.field_attributes(f.type_index)&16]
            need('own-exact-enum-backing',ctx.is_enum(name)and len(fields)==1
                and md.string(fields[0].name_index)=='value__'and ctx.type_name(fields[0].type_index)==expected)
            scalar.ordinary(image,ctx.type_pointer(fields[0].type_index),8 if width==4 else 5,LABEL+'.enumBacking')
            fact.update(enumBackingType=expected,enumBackingBytes=width,
                enumBackingRawTypeHex=image.pe.bytes_at_va(ctx.type_pointer(fields[0].type_index),16).hex().upper())
        elif kind==17:
            fields=[f for f in md.fields_for(ctx.index.types[name])if not ctx.field_attributes(f.type_index)&16]
            need('own-value8-two-Singles',ctx.is_value_type(name)and len(fields)==2
                and[(md.string(f.name_index),ctx.type_name(f.type_index))for f in fields]==
                    [('animationSpeed','float'),('animationWeight','float')])
            for f in fields:scalar.ordinary(image,ctx.type_pointer(f.type_index),12,LABEL+'.value8Field')
            layout=[(md.string(f.name_index),*ctx.field(name+'::'+md.string(f.name_index))[1:])for f in fields]
            need('own-value8-field-offsets',layout==[('animationSpeed','float',16),('animationWeight','float',20)])
            td=ctx.index.types[name];need('own-value8-size-table-index',0<=td.index<image.registration['typeDefinitionsSizesCount'])
            at=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+td.index*8)
            need('own-value8-size-table-row',(image.pe.u32_at_va(at),image.pe.u32_at_va(at+4))==(24,8))
            fact.update(valueCarrierBytes=8,fields=layout,referenceLaneOffsets=[],paddingByteRanges=[])
        facts.append(fact)
    method=md.methods[usage['methodSpec'][0]];parameters=list(md.parameters_for(method))
    need('own-static-void-two',method.declaring_type==owner.index and bool(method.flags&16)
        and ctx.type_name(method.return_type)=='void'and method.parameter_count==len(parameters)==2)
    reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
    need('actual-Reader-and-reference-out-byref',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==bytes((17,32))and output[10:12]==bytes((21,32)))
    opened=ContextSymbols(image).type(ctx.type_pointer(parameters[1].type_index))
    need('output-owned-class-VARs',opened['definition']['name']==OWNER
        and[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in opened['classArguments']]==[(owner.index,0),(owner.index,1)])
    typename=OWNER+'<'+key+','+value+'>'
    return dict(instructionRva=usage['instructionRva'],instructionHex=usage['instructionHex'],
        methodSpecIndex=usage['methodSpecIndex'],methodSpec=usage['methodSpec'],methodOwner=OWNER,
        methodName='DeserializeV2',fullTypeName=typename,register='r8',
        contextMode='owned-static-out-animation-extra-dictionary',typeKind=21,typeDefinition=owner.index,
        typedRequest=usage,resultAbi='void-byref-reference8',readerParameterRawHex=reader.hex().upper(),
        outputParameterRawHex=output.hex().upper(),arguments=facts)


def validate_event(event,setter):
    context=event.get('context',{});binding=event.get('staticOutSourceBinding',{});u=context.get('typedRequest',{})
    key,value=request_shape(u);typename=OWNER+'<'+key+','+value+'>'
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-static-reference-event',event.get('kind')=='reference:'+typename and event.get('declaredType')==typename
        and event.get('mode')=='typed-static-out-reference'and event.get('resultAbi')=='out-reference-local'
        and event.get('actualSourceProved')is True and event.get('referenceBytes')==setter.get('storedBytes')==8
        and context.get('contextMode')=='owned-static-out-animation-extra-dictionary'
        and context.get('fullTypeName')==typename and context.get('register')=='r8'
        and context.get('resultAbi')=='void-byref-reference8'and len(raw)==16 and raw[10]==21 and not raw[11]&128)
    need('same-actual-static-source-binding',binding==dict(typeName=typename,sourceTargetRva=event.get('sourceTargetRva'),
        readerMethodDefinition=context['methodSpec'][0],context=context,resultAbi='void-byref-reference8',
        referenceBytes=8,actualSourceProved=True))
    return context


def caller_program(regions,usage,source_target,*,base):
    """The exact actual R8/out-address/Reader/E8 fragment, without a frame grant."""
    from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
    request_shape(usage);g=BytesPath(regions,base+usage['instructionRva']);g.take(usage['instructionHex'])
    prefix=bytes(g.bytes.get(g.at+i,-1)for i in range(3))
    if prefix==bytes.fromhex('488d54'):
        g.take('488d5424');displacement=g.read(1)[0]
        need('finite-RSP-output-home',displacement in(32,40,104));address=dict(baseRegister='rsp',displacement=displacement)
    else:
        g.take('488d55');displacement=int.from_bytes(g.read(1),'little',signed=True)
        need('finite-RBP-output-home',displacement in(56,-16,-8));address=dict(baseRegister='rbp',displacement=displacement)
    g.take('488bcf');call=g.at;g.call(source_target)
    return dict(selectedBytes=g.seen,sourceInstruction=[call-base,'e8'+(source_target-call-5).to_bytes(4,'little',signed=True).hex()],
        sourceTargetRva=source_target-base,methodInfoRegister='r8',readerRegister='rdi',outputAddress=address,
        referenceBytes=8,zeroOutputAndReaderOriginRequired=True,parentFieldAdmitted=False,enclosingFrameAdmitted=False)


def parent_source(image,usage,source_target):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer
    from scripts.game_data.memorypack.animation_extra_parent_sources import PARENT_FIELDS
    ctx=NativeReferenceContext(image);base=image.pe.image_base;typename=OWNER+'<'+','.join(request_shape(usage))+'>'
    wrappers={w.wrapped_type:w for w in image.memorypack_wrappers.values()};found=[]
    for name,fields in PARENT_FIELDS.items():
        indices=[i for i,t in fields.items()if t==typename]
        if not indices:continue
        wrapper=wrappers[name];method=pointer.methods(image,wrapper)['Deserialize'];body=pointer.owned(image,image.method_pointer_va(method))
        if not any(w['startRva']<=usage['instructionRva']<w['endRva']for w in body['windows']):continue
        need('one-own-declared-dictionary-field',len(indices)==1);index=indices[0];member=wrapper.members[index]
        need('same-actual-nominal-member',member.declared_type==typename)
        current=name;lineage=[];declared=[]
        for _ in range(32):
            if not current or current in lineage:break
            lineage.append(current)
            if current not in ctx.index.types:
                need('only-terminal-object-alias',current=='object');break
            definition=ctx.index.types[current]
            fields=[f for f in image.metadata.fields_for(definition)if image.metadata.string(f.name_index)==member.name
                and not ctx.field_attributes(f.type_index)&16]
            if fields:declared.append((current,fields))
            current=ctx.parent(current)
        need('one-actual-inherited-field-declaration',len(declared)==1 and len(declared[0][1])==1)
        owner=declared[0][0];original=ctx.field(owner+'::'+member.name)
        need('same-own-original-field',original[:2]==(owner,typename)and type(original[2])is int and original[2]>=16)
        found.append(dict(typeName=name,wrapperName=wrapper.name,memberIndex=index,fieldName=member.name,
            originalField=list(original),originalFieldLineage=lineage,method=[method.index,wrapper.name,'Deserialize',body['pointer']-base],
            windows=body['windows'],regions=[[at-base,raw.hex()]for at,raw in body['regions']],
            program=caller_program(body['regions'],usage,source_target,base=base),actualTypedCallProved=True,
            zeroLocalProved=False,parentFieldAdmitted=False,enclosingFrameAdmitted=False))
    need('one-owned-actual-parent-call',len(found)==1)
    return found[0]


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack import animation_extra_dictionary_programs as paths
    from scripts.game_data.memorypack import animation_custom_dictionary_programs as string_paths
    from scripts.game_data.memorypack.animation_custom_dictionary_sources import context_slots
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins);base=image.pe.image_base
    need('literal-actual-E8-target',type(source_target)is int and source_target>base)
    fresh=request_context(image,context['instructionRva'])
    need('same-independent-own-context',json.loads(json.dumps(fresh))==json.loads(json.dumps(context)))
    parent=parent_source(image,fresh['typedRequest'],source_target)
    key,value=request_shape(fresh['typedRequest']);profile,width=DOMAINS[(key,value)]
    actual=pointer.owned(image,source_target);offsets=scalar.reader_offsets(image,LABEL)
    if profile=='string-reference':
        symbols=string_paths.symbols(actual['regions'],'reference-Montage')
        programs=[string_paths.montage_program(actual['regions'],source_target,offsets,symbols,count=n)for n in(-1,0,1,2,3)]
        from scripts.game_data.memorypack.counted_loop_sources import prove_induction
        induction=prove_induction(programs[1:],initial='448bef',increment='41ffc5',comparison='443bac2490000000',
            counter='r13d',saved_count='signed Int32 stack144',max_count=4096,mode_key='newDictionary',
            backedge_sites=programs[2]['backedgeSites'])
        header=None
    else:
        symbols=paths.symbols(actual['regions'],key_bytes=width)
        programs=[paths.program(actual['regions'],source_target,offsets,symbols,count=n,key_bytes=width)for n in(-1,0,1,2,3)]
        induction=paths.induction(programs,key_bytes=width)
        header=primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base,fragments=True),offsets)
    typed=context_slots(image)
    helpers={}
    for name,target in symbols.items():
        if name not in('constructor','keyProvider','valueProvider','keyDispatch','valueDispatch','insert'):continue
        owned=pointer.owned(image,target)
        helpers[name]=dict(targetRva=target-base,windows=owned['windows'],
            regions=[[at-base,raw.hex()]for at,raw in owned['regions']])
    result=dict(schema='endfield.animation-extra-dictionary-source.v1',status='validated-conditional-static-out-source',
        nativeInputs=dict(pins),typeName=context['fullTypeName'],keyType=key,valueType=value,profile=profile,
        context=context,sourceTargetRva=source_target-base,readerMethodDefinition=context['methodSpec'][0],
        resultAbi='void-byref-reference8',referenceBytes=8,keyOutputBytes=width,valueOutputBytes=8,
        valueStorageKind='value8'if profile=='enum1-value8'else'reference8',
        objectMarkerBytes=1,countHeaderBytes=4,initiallyNullOutputRequired=True,existingOutputClearProved=False,
        proof=dict(windows=actual['windows'],regions=[[at-base,raw.hex()]for at,raw in actual['regions']],
            programs=programs,countInduction=induction,readerOffsets=offsets,
            symbolRvas={name:target-base for name,target in symbols.items()},genericClassSlots=typed,
            helpers=helpers,objectHeader=header,barrier=_barrier(image,symbols['barrier']),actualParent=parent),
        keyGrammarAdmitted=False,referenceChildGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        condition='Fresh initially-null output; exact current nominal MethodInfo and actual E8 source, initialized class/helper state, sufficient buffered input, stable disjoint storage and normal compatible helpers. Key callback, reference value grammar, constructor/insertion semantics and live provider selection remain independent.')
    _publication_gate(image,pins)
    return json.loads(json.dumps(result))
