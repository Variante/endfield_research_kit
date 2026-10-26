"""Actual fallback SerializeReferenceDictionary source, without child grammar."""
import json,struct
from scripts.game_data.memorypack import animation_fallback_dictionary_programs as paths

SCHEMA='endfield.animation-fallback-reference-dictionary-source.v1'
OWNER='Beyond.SerializeReferenceDictionary`2'
PARENT='Beyond.Gameplay.View.Animation.AnimationMontageSetSo'
VALUE='Beyond.Montage.AnimMontageData'
TYPE=OWNER+'<string,'+VALUE+'>'


def need(key,condition):
    if not condition:raise ValueError('animationFallbackDictionarySource.'+key)


def normalized(v):return json.loads(json.dumps(v))


def request_shape(usage):
    raw=bytes.fromhex(usage.get('instructionHex',''));spec=usage.get('methodSpec',[])
    need('exact-owned-R8-static-request',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
        usage.get('classArguments'),usage.get('methodArguments'))==(6,OWNER,'DeserializeV2',['string',VALUE],[])
        and len(raw)==7 and raw[:3]==bytes.fromhex('4c8b05')and len(spec)==3
        and all(type(n)is int for n in spec)and spec[0]>=0 and spec[1]>=0 and spec[2]==-1)


def request_context(image,usage):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import scalar_param_native as scalar
    request_shape(usage)
    fresh=derive_typed_usage_context(image,usage['instructionRva'],label='fallbackDictionary.actual')
    need('same-fresh-request',normalized(fresh)==normalized(usage))
    ctx=NativeReferenceContext(image);md=image.metadata;td=ctx.index.types[OWNER]
    arguments=image.instantiations.resolve(usage['methodSpec'][1]).arguments
    need('two-own-closed-class-arguments',len(arguments)==2);facts=[]
    for name,kind,arg in zip(('string',VALUE),(14,18),arguments,strict=True):
        scalar.ordinary(image,arg.type_pointer_va,kind,'fallbackDictionary.argument',reference=True)
        raw=image.pe.bytes_at_va(arg.type_pointer_va,16)
        need('own-reference-argument',raw[10:12]==bytes((kind,0))and(kind==14 or
            int.from_bytes(raw[:8],'little')==ctx.index.types[name].index and not ctx.is_value_type(name)))
        facts.append(dict(typeName=name,typeKind=kind,rawTypeRecordHex=raw.hex().upper(),
            typeDefinition=None if kind==14 else ctx.index.types[name].index))
    method=md.methods[usage['methodSpec'][0]];parameters=list(md.parameters_for(method))
    need('own-static-void-two-parameter-ABI',method.declaring_type==td.index and method.flags&16
        and md.string(method.name_index)=='DeserializeV2'and ctx.type_name(method.return_type)=='void'
        and method.parameter_count==len(parameters)==2)
    reader=image.pe.bytes_at_va(ctx.type_pointer(parameters[0].type_index),16)
    output=image.pe.bytes_at_va(ctx.type_pointer(parameters[1].type_index),16)
    opened=ContextSymbols(image).type(ctx.type_pointer(parameters[1].type_index))
    need('own-Reader-and-constructed-reference-out',ctx.type_name(parameters[0].type_index)=='MemoryPack.MemoryPackReader'
        and reader[10:12]==bytes((17,32))and output[10:12]==bytes((21,32))
        and opened['definition']['name']==OWNER
        and[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in opened['classArguments']]==[(td.index,0),(td.index,1)])
    slots=ContextSymbols(image).context(td.index,slots=[29,30,31,32,37]);entries={e['relativeSlot']:e for e in slots['entries']}
    allocated=entries[29]['type'];need('own-allocated-class',allocated['definition']['name']==OWNER)
    def variables(args,ordinals):
        need('exact-own-class-VARs',[(a['parameterOwner'].get('typeIndex'),a['parameterOwner'].get('ordinal'))for a in args]==[(td.index,n)for n in ordinals])
    variables(allocated['classArguments'],[0,1])
    for slot,owner,name,role,ordinals in((30,OWNER,'.ctor','classArguments',[0,1]),
        (31,'MemoryPack.MemoryPackFormatterProvider','GetFormatter','methodArguments',[0]),
        (32,'MemoryPack.MemoryPackFormatterProvider','GetFormatter','methodArguments',[1]),
        (37,OWNER,'set_Item','classArguments',[0,1])):
        entry=entries[slot];need('exact-static-context-slot:'+str(slot),(entry['typeName'],entry['methodName'])==(owner,name))
        variables(entry[role],ordinals)
    return dict(typeName=TYPE,typeDefinition=td.index,typedRequest=usage,arguments=facts,contextSlots=slots,
        readerParameterRawHex=reader.hex().upper(),outputParameterRawHex=output.hex().upper(),outputType=opened,
        resultAbi='void-byref-reference8',methodInfoRegister='r8')


def count_context(image,instruction):
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.context import method_parameter_owner
    from scripts.game_data.memorypack import scalar_param_native as scalar
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    usage=derive_typed_usage_context(image,instruction-base,label='fallbackDictionary.count')
    need('actual-Int32-byref-ReadUnmanaged-context',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),
        usage.get('classArguments'),usage.get('methodArguments'))==(6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['int'])
        and bytes.fromhex(usage['instructionHex'])[:3]==bytes.fromhex('4c8b05'))
    method=md.methods[usage['methodSpec'][0]];parameter,=md.parameters_for(method)
    raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16);section=md.sections['genericContainers']
    need('own-generic-instance-void-one-out-method',method.declaring_type==ctx.index.types['MemoryPack.MemoryPackReader'].index
        and not method.flags&16 and method.generic_container_index>=0 and ctx.type_name(method.return_type)=='void')
    at=section.offset+method.generic_container_index*16
    owner,count,is_method,start=struct.unpack_from('<iiii',md.buf,at)
    reciprocal=method_parameter_owner(md.buf,start,[m.generic_container_index for m in md.methods],source='fallbackDictionary.count')
    need('same-owned-byref-MVAR-zero',(owner,count,is_method)==(method.index,1,1)
        and reciprocal.get('methodIndex')==method.index and reciprocal.get('ordinal')==0
        and raw[10:12]==bytes((30,32))and int.from_bytes(raw[:8],'little')==start)
    argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
    scalar.ordinary(image,argument.type_pointer_va,8,'fallbackDictionary.countArgument')
    return dict(typedRequest=usage,parameterRawTypeHex=raw.hex().upper(),parameterOwner=reciprocal,
        argumentRawTypeHex=image.pe.bytes_at_va(argument.type_pointer_va,16).hex().upper(),resultAbi='void-byref-output-rdx',
        wireWidthFromLiteralSourceRequired=True,methodInfoNotReadBySelectedSource=True)


def verify_source(actual,pins):
    from scripts.game_data.memorypack.animation_custom_dictionary_callbacks import regions
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    need('same-independent-static-reference-dictionary-source',actual.get('schema')==SCHEMA
        and actual.get('status')=='validated-conditional-fallback-reference-dictionary-source'
        and actual.get('nativeInputs')==pins and(actual.get('typeName'),actual.get('keyType'),actual.get('valueType'))==(TYPE,'string',VALUE)
        and actual.get('actualSourceProved')is True and actual.get('referenceBytes')==8
        and actual.get('initiallyNullOutputRequired')is True
        and all(actual.get(k)is False for k in('callbackGrammarAdmitted','parentFieldAdmitted','wholeOwnerAdmitted')))
    proof=actual['proof'];context=proof['context'];request_shape(context['typedRequest'])
    need('own-class-and-byref-ABI',context.get('typeName')==TYPE and context.get('methodInfoRegister')=='r8'
        and context.get('resultAbi')=='void-byref-reference8'
        and context['typedRequest']['methodSpec'][0]==actual.get('staticReaderMethodDefinition')
        and bytes.fromhex(context.get('readerParameterRawHex',''))[10:12]==bytes((17,32))
        and bytes.fromhex(context.get('outputParameterRawHex',''))[10:12]==bytes((21,32)))
    base=proof['programs'][0]['selectedBytes'][0][0]-actual['sourceTargetRva']
    raw=regions(proof['sourceWindows'],proof['sourceRegions'],base,'fallback-reference-dictionary')
    replay=[paths.program(raw,base+actual['sourceTargetRva'],count=n)for n in(-1,0,1,2,3)]
    need('whole-own-static-byte-programs',normalized(replay)==proof['programs'])
    symbols={}
    for row in replay:
        for key,target in row['symbols'].items():need('same-selected-helper:'+key,key not in symbols or symbols[key]==target);symbols[key]=target
    need('all-actual-helper-identities',{k:v-base for k,v in symbols.items()}==proof.get('symbolRvas'))
    induction=prove_induction(replay[1:],initial='458bef',increment='41ffc5',comparison='443b6de0',counter='r13d',saved_count='RBP-32',
        max_count=proof['induction']['maxCount'],mode_key='newDictionary',backedge_sites=replay[-1]['backedgeSites'])
    need('same-bounded-loop-induction',normalized(induction)==proof['induction']and induction['maxCount']<=4096)
    count=proof['countContext'];usage=count['typedRequest'];formal=bytes.fromhex(count.get('parameterRawTypeHex',''))
    need('independent-Int32-output-ABI',(usage.get('tag'),usage.get('typeName'),usage.get('methodName'),usage.get('classArguments'),usage.get('methodArguments'))==
        (6,'MemoryPack.MemoryPackReader','ReadUnmanaged',[],['int'])
        and len(formal)==16 and formal[10:12]==bytes((30,32))
        and count.get('parameterOwner',{}).get('methodIndex')==usage['methodSpec'][0]
        and count['parameterOwner'].get('ordinal')==0 and count.get('resultAbi')=='void-byref-output-rdx')
    argument=bytes.fromhex(count.get('argumentRawTypeHex',''))
    need('same-actual-Int32-value-carrier:'+argument.hex(),len(argument)==16 and argument[10:12]==bytes((8,128)))
    for role,parse in(('count',lambda raw,entry:paths.count_program(raw,entry,proof['readerOffsets'])),('insert',paths.insertion_program)):
        helper=proof['helpers'][role];owned=regions(helper['windows'],helper['regions'],base,'fallback-'+role)
        checked=parse(owned,base+helper['targetRva']);expected=proof['countProgram'if role=='count'else'insertionProgram']
        need('same-full-helper-program:'+role,helper['targetRva']==proof['symbolRvas'][role]and normalized(checked)==expected)
    parent=proof['parent'];owned=regions(parent['windows'],parent['regions'],base,'fallback-parent')
    data={a+i:b for a,h in owned for i,b in enumerate(h)};usage=context['typedRequest'];at=base+usage['instructionRva']
    need('actual-typed-parent-call',parent.get('typeName')==PARENT and parent.get('typedRequest')==usage
        and bytes(data.get(at+i,0)for i in range(7))==bytes.fromhex(usage['instructionHex'])
        and bytes(data.get(at+7+i,0)for i in range(8))==bytes.fromhex('488d542448488bce'))
    call=bytes(data.get(at+15+i,0)for i in range(5))
    need('same-actual-E8',call[:1]==b'\xe8'and at+20+int.from_bytes(call[1:],'little',signed=True)==base+actual['sourceTargetRva']
        and parent.get('sourceInstruction')==[at+15-base,call.hex().upper()])
    return base


def derive(image,pins,*,typed_request,source_target,count_limit=4096):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    context=request_context(image,typed_request);need('finite-positive-count-limit',type(count_limit)is int and 3<=count_limit<=4096)
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==PARENT]
    need('exact-actual-fallback-member',[(m.name,m.declared_type)for m in wrapper.members]==
        [('_montages',TYPE),('_npcMontages','System.Collections.Generic.List`1<Beyond.Gameplay.Core.GameplayTag>')])
    parent=pointer.owned(image,image.method_pointer_va(pointer.methods(image,wrapper)['Deserialize']))
    at=base+typed_request['instructionRva'];bytes_={a+i:b for a,raw in parent['regions']for i,b in enumerate(raw)}
    need('actual-parent-R8-E8-fragment',bytes(bytes_.get(at+i,0)for i in range(7))==bytes.fromhex(typed_request['instructionHex'])
        and bytes(bytes_.get(at+7+i,0)for i in range(8))==bytes.fromhex('488d542448488bce'))
    raw=bytes(bytes_[at+15+i]for i in range(5))
    need('same-actual-static-source-E8',raw[:1]==b'\xe8'and at+20+int.from_bytes(raw[1:],'little',signed=True)==source_target)
    body=pointer.owned(image,source_target);programs=[paths.program(body['regions'],source_target,count=n)for n in(-1,0,1,2,3)]
    symbols={}
    for p in programs:
        for name,target in p['symbols'].items():need('coherent-own-helper:'+name,name not in symbols or symbols[name]==target);symbols[name]=target
    induction=prove_induction(programs[1:],initial='458bef',increment='41ffc5',comparison='443b6de0',counter='r13d',saved_count='RBP-32',
        max_count=count_limit,mode_key='newDictionary',backedge_sites=programs[-1]['backedgeSites'])
    offsets=scalar.reader_offsets(image,'fallbackDictionary');count=count_context(image,programs[-1]['countContextInstructionVa'])
    header=primitive_param.object_header_source(image,vector_recorder(image)(symbols['objectHeader']-base,fragments=True),offsets)
    helpers={name:pointer.owned(image,symbols[name])for name in('count','dispatch','insert','constructor','provider')}
    count_program=paths.count_program(helpers['count']['regions'],symbols['count'],offsets)
    insertion=paths.insertion_program(helpers['insert']['regions'],symbols['insert'])
    provider=derive_typed_usage_context(image,programs[-1]['providerClassInstructionVa']-base,label='fallbackDictionary.provider')
    need('own-formatter-provider-class',(provider.get('tag'),provider.get('typeName'))==(1,'MemoryPack.MemoryPackFormatterProvider'))
    result=normalized(dict(schema=SCHEMA,status='validated-conditional-fallback-reference-dictionary-source',nativeInputs=pins,
        typeName=TYPE,keyType='string',valueType=VALUE,sourceTargetRva=source_target-base,
        staticReaderMethodDefinition=typed_request['methodSpec'][0],actualSourceProved=True,referenceBytes=8,
        initiallyNullOutputRequired=True,callbackGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(context=context,countContext=count,readerOffsets=offsets,programs=programs,induction=induction,
            sourceWindows=body['windows'],sourceRegions=[[a-base,h.hex().upper()]for a,h in body['regions']],
            symbolRvas={k:v-base for k,v in symbols.items()},header=header,barrier=_barrier(image,symbols['barrier']),
            countProgram=count_program,insertionProgram=insertion,providerClass=provider,
            helpers={k:dict(targetRva=v['pointer']-base,windows=v['windows'],regions=[[a-base,h.hex().upper()]for a,h in v['regions']])for k,v in helpers.items()},
            parent=dict(typeName=PARENT,wrapperName=wrapper.name,windows=parent['windows'],regions=[[a-base,h.hex().upper()]for a,h in parent['regions']],
                sourceInstruction=[at+15-base,raw.hex().upper()],typedRequest=typed_request)),
        evidenceBoundary=dict(exact='Actual own reference-dictionary class context, FF/new paths, raw byref Int32 count, separate slot5 key/value reference locals, unchanged underlying setter arguments and bounded R13 loop.',
            conditional='Ready coherent closed contexts and providers, successful normal typed allocation/constructor/insertion, matching actual callbacks and stable disjoint storage. Serialized duplicate entries are preserved; final mutable dictionary effects and runtime selection remain unproved.')))
    verify_source(result,pins);_publication_gate(image,pins);return result
