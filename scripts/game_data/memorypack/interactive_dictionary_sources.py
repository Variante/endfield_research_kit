"""Finite Interactive static dictionaries; each actual source is proved separately."""
import json
OWNER='Beyond.SerializeFieldDictionary`2'
DOMAINS={('int','string'),('string','int'),('string','Beyond.Gameplay.Core.InteractiveTemplateVariant'),
         ('string','Beyond.Gameplay.ParamListForGraph'),('string','Beyond.Gameplay.SkillType'),
         ('Beyond.Gameplay.Core.AbilitySystem+ComboController+BattleCommandType','string'),
         ('string','Beyond.Gameplay.Core.AbilitySystemData+BakedMeshPointList'),
         ('Beyond.Gameplay.MountPoint','Beyond.Gameplay.BasicShapeData'),
         ('string','Beyond.Gameplay.Core.SkillCameraConfig')}
TYPES={OWNER+'<'+k+','+v+'>':(k,v)for k,v in DOMAINS}
MODE='owned-static-out-interactive-dictionary'
SCHEMA='endfield.interactive-dictionary-source.v2'
LABEL='interactiveDictionarySource'
def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)
def request_shape(usage):
    pair=tuple(usage.get('classArguments',[]));raw=bytes.fromhex(usage.get('instructionHex',''));spec=usage.get('methodSpec')
    need('finite-actual-R8-class-request',pair in DOMAINS and usage.get('tag')==6
        and(usage.get('typeName'),usage.get('methodName'),usage.get('methodArguments'))==(OWNER,'DeserializeV2',[])
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')and type(usage.get('instructionRva'))is int
        and isinstance(spec,(list,tuple))and len(spec)==3 and all(type(n)is int for n in spec)
        and spec[0]>=0 and spec[1]>=0 and spec[2]==-1)
    return pair

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
        kind=14 if name=='string'else 8 if name=='int'else 17 if ctx.is_enum(name)else 18
        scalar.ordinary(image,arg.type_pointer_va,kind,LABEL+'.argument',reference=kind in(14,18))
        raw=image.pe.bytes_at_va(arg.type_pointer_va,16)
        need('own-actual-nominal-carrier',raw[10:12]==bytes((kind,0 if kind in(14,18)else 128))
            and(kind in(8,14)or int.from_bytes(raw[:8],'little')==ctx.index.types[name].index))
        if kind==17:
            td=ctx.index.types[name];backing=[f for f in md.fields_for(td)if not ctx.field_attributes(f.type_index)&16]
            need('own-enum-exact-int32',td.generic_container_index<0 and len(backing)==1
                and md.string(backing[0].name_index)=='value__'and ctx.type_name(backing[0].type_index)=='int')
            scalar.ordinary(image,ctx.type_pointer(backing[0].type_index),8,LABEL+'.enumBacking')
        fact=dict(typeName=name,typeKind=kind,rawTypeRecordHex=raw.hex().upper(),
            typeDefinition=None if kind in(8,14)else ctx.index.types[name].index)
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
        contextMode='owned-static-out-interactive-dictionary',typeKind=21,typeDefinition=owner.index,
        typedRequest=usage,resultAbi='void-byref-reference8',readerParameterRawHex=reader.hex().upper(),
        outputParameterRawHex=output.hex().upper(),arguments=facts)


def validate_event(event,setter):
    context=event.get('context',{});binding=event.get('staticOutSourceBinding',{});u=context.get('typedRequest',{})
    key,value=request_shape(u);typename=OWNER+'<'+key+','+value+'>'
    raw=bytes.fromhex(setter.get('parameterTypeRecordHex',''))
    need('exact-own-static-reference-event',event.get('kind')=='reference:'+typename and event.get('declaredType')==typename
        and event.get('mode')=='typed-static-out-reference'and event.get('resultAbi')=='out-reference-local'
        and event.get('actualSourceProved')is True and event.get('referenceBytes')==setter.get('storedBytes')==8
        and context.get('contextMode')=='owned-static-out-interactive-dictionary'
        and context.get('fullTypeName')==typename and context.get('register')=='r8'
        and context.get('resultAbi')=='void-byref-reference8'and len(raw)==16 and raw[10]==21 and not raw[11]&128)
    need('same-actual-static-source-binding',binding==dict(typeName=typename,sourceTargetRva=event.get('sourceTargetRva'),
        readerMethodDefinition=context['methodSpec'][0],context=context,resultAbi='void-byref-reference8',
        referenceBytes=8,actualSourceProved=True))
    return context


def source_programs(regions,source_target,offsets,key,value):
    """Replay the one selected finite body without nominal or child admission."""
    from scripts.game_data.memorypack import interactive_dictionary_programs as paths
    from scripts.game_data.memorypack import animation_custom_dictionary_programs as reference_paths
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('finite-own-key-value-domain',(key,value)in DOMAINS)
    enum_pair=key in('Beyond.Gameplay.Core.AbilitySystem+ComboController+BattleCommandType','Beyond.Gameplay.MountPoint')or value=='Beyond.Gameplay.SkillType'
    if enum_pair:
        from scripts.game_data.memorypack import interactive_enum_dictionary_programs as enum_paths
        symbols=enum_paths.symbols(regions,enum_key=key!='string')
        programs=[enum_paths.program(regions,source_target,offsets,symbols,count=n,enum_key=key!='string')for n in(-1,0,1,2,3)]
        induction=enum_paths.induction(programs,enum_key=key!='string')
    elif value in('Beyond.Gameplay.Core.InteractiveTemplateVariant','Beyond.Gameplay.ParamListForGraph','Beyond.Gameplay.Core.AbilitySystemData+BakedMeshPointList','Beyond.Gameplay.Core.SkillCameraConfig'):
        symbols=reference_paths.symbols(regions,'reference-Montage')
        programs=[reference_paths.montage_program(regions,source_target,offsets,symbols,count=n)for n in(-1,0,1,2,3)]
        counter='r13d';initial='448bef';increment='41ffc5';comparison='443bac2490000000';saved='signed Int32 stack144'
    else:
        integer_key=key!='string'
        symbols=paths.symbols(regions,int_key=integer_key)
        programs=[paths.program(regions,source_target,offsets,symbols,count=n,int_key=integer_key)for n in(-1,0,1,2,3)]
        counter='eax';initial='4489bc2488000000';increment='ffc0';comparison='3b442420';saved='signed Int32 stack32; counter stack136'
    if not enum_pair:
        induction=prove_induction(programs[1:],initial=initial,increment=increment,comparison=comparison,
            counter=counter,saved_count=saved,max_count=4096,mode_key='newDictionary',backedge_sites=programs[2]['backedgeSites'])
    return symbols,programs,induction


def derive(image,pins,*,context,source_target):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar
    from scripts.game_data.memorypack.animation_custom_dictionary_sources import context_slots
    _publication_gate(image,pins)
    fresh=request_context(image,context['instructionRva'])
    need('same-fresh-context',json.loads(json.dumps(fresh))==json.loads(json.dumps(context)))
    key,value=request_shape(fresh['typedRequest']);actual=pointer.owned(image,source_target)
    offsets=scalar.reader_offsets(image,LABEL)
    symbols,programs,induction=source_programs(actual['regions'],source_target,offsets,key,value)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,nativeInputs=pins,
        typeName=fresh['fullTypeName'],context=fresh,resultAbi='void-byref-reference8',referenceBytes=8,
        sourceTargetRva=source_target-image.pe.image_base,readerMethodDefinition=fresh['methodSpec'][0],
        proof=dict(windows=actual['windows'],sourceRegions=[[a-image.pe.image_base,raw.hex().upper()]for a,raw in actual['regions']],
            symbolRvas={k:v-image.pe.image_base for k,v in symbols.items()},
            programs=programs,induction=induction,readerOffsets=offsets,
            genericClassSlots=context_slots(image)),keyGrammarAdmitted=False,valueGrammarAdmitted=False,
        parentFieldAdmitted=False,wholeOwnerAdmitted=False,initiallyNullOutputRequired=True,
        condition='Ready original providers, compatible canonical callbacks/helpers, disjoint buffered input/output and normal ABI. Parent, concrete children and runtime selection remain independent.')))
