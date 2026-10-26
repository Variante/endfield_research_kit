"""Fresh two nominal Char static dictionaries below the root field owner.

Exact UInt32/CLASS and String/CLASS MethodInfos, actual E8 bodies, null/zero/
positive count programs and local-to-insertion flow are proved here. Callback
grammars, native insertion outcome and complete Char root admission remain
separate. No enum or another dictionary's pointer is substituted for UInt32.
"""
import json

SCHEMA='endfield.char-perform-positive-dictionary-source.v1'
OWNER='Beyond.SerializeFieldDictionary`2'
PARENT='Beyond.Gameplay.Core.CharInteractPerform.CharInteractPerformRuntimeCfg'
DOMAINS={
    'bodyTypeActDataDict':(2,'uint','Beyond.Gameplay.Core.CharInteractPerform.BodyTypeActData'),
    'subPerformEntries':(25,'string','Beyond.Gameplay.Core.CharInteractPerform.SubSpecialPerformEntryData'),
}


def need(check,condition):
    if not condition:raise ValueError('charPositiveDictionarySource.'+check)


def normalized(value):return json.loads(json.dumps(value))


def request_context(image,usage,*,field):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    need('finite-field-selection',field in DOMAINS);index,key,value=DOMAINS[field]
    raw=bytes.fromhex(usage.get('instructionHex',''))
    need('literal-actual-R8-class-only-MethodInfo',tuple(usage.get(k)for k in
        ('tag','typeName','methodName','classArguments','methodArguments'))==(6,OWNER,'DeserializeV2',[key,value],[])
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')
        and len(usage.get('methodSpec',[]))==3 and usage['methodSpec'][1]>=0 and usage['methodSpec'][2]==-1)
    fresh=derive_typed_usage_context(image,usage['instructionRva'],label='charPositiveDictionarySource.actual')
    need('same-fresh-actual-request',fresh==usage);ctx=NativeReferenceContext(image);md=image.metadata
    arguments=image.instantiations.resolve(usage['methodSpec'][1]).arguments
    need('two-own-closed-class-arguments',len(arguments)==2);facts=[]
    for name,arg,kind in zip((key,value),arguments,(9 if key=='uint'else 14,18),strict=True):
        encoded=image.pe.bytes_at_va(arg.type_pointer_va,16)
        scalar.ordinary(image,arg.type_pointer_va,kind,'charPositiveDictionarySource.argument',reference=kind in(14,18))
        need('actual-nominal-type-carrier',encoded[10:12]==bytes((kind,128 if kind==9 else 0))
            and(kind in(9,14)or int.from_bytes(encoded[:8],'little')==ctx.index.types[name].index))
        facts.append(dict(typeName=name,typeKind=kind,rawTypeRecordHex=encoded.hex(),
            typeDefinition=ctx.index.types[name].index if kind==18 else None))
    method=md.methods[usage['methodSpec'][0]];parameters=list(md.parameters_for(method));definition=ctx.index.types[OWNER]
    need('own-static-reader-definition',method.declaring_type==definition.index and bool(method.flags&16)
        and ctx.type_name(method.return_type)=='void'and method.parameter_count==len(parameters)==2)
    reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
    carrier=ContextSymbols(image).type(ctx.type_pointer(parameters[1].type_index))
    need('owned-Reader-and-dictionary-output-byrefs',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==bytes((17,32))and output[10:12]==bytes((21,32))
        and carrier['definition']['name']==OWNER
        and[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in carrier['classArguments']]
            ==[(definition.index,0),(definition.index,1)])
    return dict(fieldName=field,memberIndex=index,typeName=OWNER+'<'+key+','+value+'>',keyType=key,valueType=value,
        typedRequest=usage,arguments=facts,readerParameterRawHex=reader.hex(),outputParameterRawHex=output.hex(),
        outputCarrier=carrier,resultAbi='void-byref-reference8',methodInfoRegister='r8')


def derive(image,pins,*,fields=tuple(DOMAINS),count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.animation_custom_dictionary_sources import context_slots
    from scripts.game_data.memorypack import char_perform_positive_dictionary_programs as paths
    from scripts.game_data.memorypack.char_perform_root_sources import root_existing
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    _publication_gate(image,pins);need('finite-distinct-fields',isinstance(fields,(tuple,list))and bool(fields)
        and len(fields)==len(set(fields))and set(fields)<=set(DOMAINS))
    need('bounded-count-domain',type(count_limit)is int and 3<=count_limit<=4096)
    path=CONTRACTS_DIR/'char_interact_perform_sparse_native.json';before=path.read_bytes();fact=json.loads(before)
    need('same-reviewed-root-source-build',fact.get('nativeInputs')==pins
        and fact.get('schema')=='endfield.char-interact-perform-sparse-native.v4'
        and fact.get('status')=='conditional-current-build-wire')
    profile=fact['profile'];base=image.pe.image_base;ctx=NativeReferenceContext(image)
    root_method=profile['programMethods']['rootReader'];root_body=pointer.owned(image,base+root_method[3])
    offsets=scalar.reader_offsets(image,'charPositiveDictionarySource');typed=context_slots(image);owners=[]
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
    need('same-own-root-wrapper-and-members',wrapper.name==profile['wrapper']
        and[(m.name,m.declared_type)for m in wrapper.members]==[(f['name'],f['type'])for f in profile['fieldPlan']]
        and ctx.field(wrapper.name+'::__instance')==(wrapper.name,PARENT,16)
        and ctx.is_value_type(PARENT)is False)
    image.validate_method_row(root_method,label='charPositiveDictionarySource.parent')
    primitive_param.reader_abi(image,ctx,image.metadata.methods[root_method[0]],wrapper)
    root=root_existing(root_body['regions'],root_body['pointer'],profile['fieldPlan'],offsets=offsets,source_targets={})
    for field in fields:
        index,key,value=DOMAINS[field];event=root['fields'][index];decl=profile['fieldPlan'][index]
        need('own-current-Char-root-field',profile['original']==PARENT and event['name']==decl['name']==field
            and event['mode']==decl['mode']=='out8'and len(event['contextCells'])==1)
        usage=derive_typed_usage_context(image,event['contextCells'][0]['instruction']-base,label='charPositiveDictionarySource.parent')
        context=request_context(image,usage,field=field);target=event['sourceTarget']
        need('same-own-field-and-actual-static-target',ctx.field(PARENT+'::'+field)==(PARENT,context['typeName'],decl['offset'])
            and decl['type']==context['typeName']and target==base+profile['dictionarySources'][field]['entryRva']
            and usage['methodSpec'][0]==profile['dictionarySources'][field]['definition'])
        call=image.pe.bytes_at_va(event['sourceCall'],5)
        need('actual-whole-parent-E8',call[0]==232 and event['sourceCall']+5+int.from_bytes(call[1:],'little',signed=True)==target)
        typename=derive_typed_usage_context(image,event['selectedStart']-base,
            label='charPositiveDictionarySource.closedClass')
        need('same-ready-closed-dictionary-class',typename.get('tag')==1 and typename.get('typeName')==context['typeName'])
        body=pointer.owned(image,target);model='uintDictionary'if key=='uint'else'referenceDictionary'
        old,= [c for c in profile['calls']if c['model']==model and c['kwargs']['null']is False]
        symbols=dict(old['args'][3]);symbols.update(paths.symbols(body['regions'],unsigned=key=='uint'))
        programs=[paths.program(body['regions'],target,offsets,symbols,count=n,unsigned=key=='uint')for n in(-1,0,1,2,3)]
        counted=paths.induction(programs,unsigned=key=='uint',count_limit=count_limit)
        header=None
        if key=='uint':
            primitive_param.object_header_source(image,vector_recorder(image)(symbols['header']-base,fragments=True),offsets)
            marker=pointer.owned(image,symbols['header']);header=dict(entryRva=symbols['header']-base,
                windows=marker['windows'],regions=[[at-base,raw.hex()]for at,raw in marker['regions']],
                program=paths.object_marker_program(marker['regions'],symbols['header'],offsets))
        helpers={}
        for role in('constructor','keyProvider','valueProvider','keyDispatch','valueDispatch','insert'):
            if role not in symbols:continue
            owned=pointer.owned(image,symbols[role]);helpers[role]=dict(entryRva=symbols[role]-base,windows=owned['windows'],
                regions=[[at-base,raw.hex()]for at,raw in owned['regions']],rows=owned['rows'])
        owners.append(dict(schema=SCHEMA,status='validated-conditional-char-positive-dictionary-source',nativeInputs=pins,
            fieldName=field,typeName=context['typeName'],keyType=key,valueType=value,sourceTargetRva=target-base,
            readerMethodDefinition=usage['methodSpec'][0],resultAbi='void-byref-reference8',
            initiallyNullOutputRequired=True,callbackGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
            proof=dict(context=context,readerOffsets=offsets,sourceWindows=body['windows'],
                sourceRegions=[[at-base,raw.hex()]for at,raw in body['regions']],programs=programs,induction=counted,
                symbolRvas={role:at-base for role,at in symbols.items()},classContext=typed,helpers=helpers,
                header=header,barrier=_barrier(image,symbols['barrier']),actualParent=dict(method=root_method,
                    rootWindows=root_body['windows'],rootRegions=[[at-base,raw.hex()]for at,raw in root_body['regions']],
                    program=root,fieldPlan=profile['fieldPlan'],context=usage,closedClass=typename,
                    sourceInstruction=[event['sourceCall']-base,call.hex()],fieldEvent=event,
                    existingRootSourceProved=True,newRootSourceAdmitted=False)),evidenceBoundary=__doc__))
    need('reviewed-source-bookend',path.read_bytes()==before);_publication_gate(image,pins)
    return normalized(dict(nativeInputs=pins,owners=owners,callbackGrammarAdmitted=False,wholeOwnerAdmitted=False))
