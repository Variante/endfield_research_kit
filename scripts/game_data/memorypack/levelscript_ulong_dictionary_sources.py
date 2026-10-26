"""Current UInt64/reference dictionary count loop; children remain separate."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag


def dictionary_program(regions,entry,o,s,*,count=-1,same_comparer=False,induction_witness=False):
    if(type(count)is not int or type(induction_witness)is not bool
            or count not in((-1,0,1,2,3)if induction_witness else(-1,0,1,2))or type(same_comparer)is not bool):
        raise ValueError('levelScriptUlongDictionary.literal-profile')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68,'totalLength':24}:
        raise ValueError('levelScriptUlongDictionary.reader-layout')
    g=BytesPath(regions,entry);loops=[];loop=None;backedge=None
    g.take('4c89442418','53','55','56','57','4154','4155','4157','4883ec60','4533e4',
        '498bf1','837a3004','4d8bf8','488bda','4c89642438','488be9','4c89a424a8000000','4c89642430')
    g.branch('0f8c',False)
    g.take('488b4350','4c6328','8b7b30','83c7fc');g.branch('0f88',False)
    g.take('4883435004','83434004','83434404','897b30','48634344','488b4b18','482bc8','493bcd')
    g.branch('0f8c',False);g.take('4183fdff');g.branch('0f84',count==-1)
    if count==-1:
        g.take('498bcf','4d8927');g.call(s['barrier'])
    else:
        g.take('4c89b424a0000000','4d3927');g.branch('0f85',False)
        g.take('488b4e20','ba03000000','488b6d10','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b4e20','488b91c0000000','488b4a20','4c396120');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','4c8b7120','4585ed');g.branch('0f88',False)
        g.branch('0f8f',count>0)
        if count:
            g.take('498b4620','488b88c0000000','488b4108','4c396020');g.branch('0f84',False)
            g.take('498b4620','418bd5','488bcf','4c8b80c0000000','4d8b4008');g.call(s['initialize']);g.jump('e9')
        g.take('498b4620','488b88c0000000','488b4910');g.call(s['comparer'])
        g.take('483be8');g.branch('74',same_comparer,1)
        if not same_comparer:g.take('488d4f30','48896f30');g.call(s['barrier'])
        g.take('498bcf','49893f');g.call(s['barrier'])
        provider=dict(instruction=g.at,cell=g.relative('488b0d'))
        g.take('4439a1e0000000');g.branch('0f84',False)
        g.take('488b4620','488b88c0000000','488b4930');g.call(s['keyProvider'])
        g.take('488b4e20','4c8bf0','488b89c0000000','488b4938');g.call(s['valueProvider'])
        g.take('4889442440','488be8','4585ed');g.branch('7f',bool(count),1)
        if count:
            if g.relative('488d3d')!=s['keyCallback']:raise ValueError('levelScriptUlongDictionary.key-callback')
            g.take('90');loop=g.at
            for index in range(count):
                if g.at!=loop:raise ValueError('levelScriptUlongDictionary.same-loop-entry')
                before=len(g.seen)
                g.take('488b4620','488b88c0000000','488b4940','4883793800');g.branch('0f84',False)
                g.take('0f57c0','0f11442448','33c0','48898424a8000000','4889442430','4d85f6')
                g.branch('0f84',False)
                g.take('498b0e');g.call(s['prepare'])
                g.take('498b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
                g.take('837b3008');g.branch('0f8c',False)
                g.take('488b4350','488b00','48898424a8000000','8b7b30','83c7f8');g.branch('0f88',False)
                g.take('4883435008','83434008','83434408','897b30','4885ed');g.branch('0f84',False)
                g.take('b905000000','4c8d4c2430','4c8bc3','488bd5');g.call(s['valueDispatch'])
                g.take('498b2f','4c8bbc24a8000000','4c8b642430','4885ed');g.branch('0f84',False)
                g.take('488b4620','488b88c0000000','488b4148','4883782000');g.branch('0f84',False)
                g.take('488b4620','488b88c0000000','488b7948','488b4720','488b88c0000000',
                    '488b81c0000000','4883782000');g.branch('0f84',False)
                g.take('488b4720','4d8bc4','498bd7','488bcd','4c8b88c0000000','498b81c0000000',
                    '41b102','4889442420');g.call(s['tryInsert'])
                g.take('4c8b642438')
                if g.relative('488d3d')!=s['keyCallback']:raise ValueError('levelScriptUlongDictionary.repeated-key-callback')
                g.take('4c8bbc24b0000000','41ffc4','488b6c2440','4c89642438','453be5')
                backedge=g.at;g.branch('0f8c',index+1<count);loops.append(g.seen[before:])
            g.jump('e9')
        g.take('4c8bb424a0000000')
    g.take('4883c460','415f','415d','415c','5f','5e','5d','5b','c3')
    if count>=2 and any(body!=loops[0]for body in loops[1:]):raise ValueError('levelScriptUlongDictionary.identical-loop')
    return dict(selectedBytes=g.seen,countWitness=count,newDictionary=count!=-1,
        comparerMatchesDefault=None if count==-1 else same_comparer,headerBytes=4,keyWireBytes=8,
        valueWireBytes=None,loopBodies=loops,loopEntry=loop,loopBackEdge=backedge,
        keyBitsPreserved=64,valueOutputBytes=8,valueCallbackSlot=5,duplicateBehaviorArgument=2,
        savedCount='signed R13 from header, unchanged through exact loop',
        counter='R12 starts0, stored at RSP+56; restored/incremented after one value callback and TryInsert, compared signed with R13D',
        sameReader=True,entryFrameRestored=True,normalReturn=True,childGrammarAdmitted=False,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)


def brief_constructor_program(regions,entry,s):
    """Own the same newly allocated original across its normal constructor."""
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('74',False,1)
    allocation=dict(instruction=g.at,cell=g.relative('488b0d'));g.call(s['allocate'])
    g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('33d2','488bc8');g.call(s['originalConstructor'])
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f')
    if g.relative('e9')!=s['barrier']:raise ValueError('levelScriptBrief.constructor-barrier')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,typedAllocation=allocation,
        originalHolderOffset=16,sameAllocatedReferenceStored=True,normalReturnViaBarrier=True,
        condition='Initialized current wrapper constructor; selected typed zeroed original allocation, normal original constructor and source-disjoint disabled barrier effects. Original construction defaults are not a serialized grammar.')


def derive(image,pins,owners,leveldata):
    """Own exact current Brief/string/module dictionary parents and source."""
    import copy,json
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.memorypack import scalar_param_native as scalar,modelview_packable_sources,pooled_string_list_sources
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.levelscript_owner_sources import ROOT,BRIEF
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_context
    from scripts.game_data.memorypack.levelscript_collection_sources import ulong_formatter_program
    from scripts.game_data.memorypack.skill_cost_data_list_sources import _load
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    need=lambda k,e,a:scalar.need('levelScriptUlongDictionary',k,e,a)
    need('same-owner-pins',(pins,pins),(owners['nativeInputs'],leveldata['nativeInputs']))
    selected=[('Beyond.Gameplay.LevelData',leveldata,('levelScriptBriefDataDict','levelScriptDataPathDict')),
        (ROOT,owners['owners'][ROOT],('modules',))]
    parents=[]
    for original,owner,fields in selected:
        for field,read in zip(owner['fields'],owner['program']['orderedReads'],strict=True):
            if field['name']not in fields:continue
            usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='levelScriptUlongDictionary.parent')
            bind_typed_read(image,usage,method_name='ReadPackable',argument=field['typeName'],kind=21,reference=True)
            argument,=image.instantiations.resolve(usage['methodSpec'][2]).arguments
            carrier=ContextSymbols(image).type(argument.type_pointer_va)
            need('closed-dictionary-definition','System.Collections.Generic.Dictionary`2',carrier['definition']['name'])
            key,value=carrier['classArguments'];key_raw=bytes.fromhex(key['rawHex']);value_raw=bytes.fromhex(value['rawHex'])
            need('exact-UInt64-key',b'\x0b\x80',key_raw[10:12])
            if value['name']=='string':need('ordinary-string-value',b'\x0e\x00',value_raw[10:12])
            else:need('exact-reference-value',(b'\x12\x00',ctx.index.types[value['name']].index),
                (value_raw[10:12],int.from_bytes(value_raw[:8],'little')))
            parents.append(dict(owner=original,field=field,source=read,typedRequest=usage,closedCarrier=carrier))
    need('three-exact-parent-fields',{'levelScriptBriefDataDict','levelScriptDataPathDict','modules'},
        {p['field']['name']for p in parents});need('one-of-each-parent',3,len(parents))
    core=_load('npc_runtime_native.json',pins)['readPackable']
    generic=_load('leveldata_npc_patrol_native.json',pins)['declarations']
    routes=copy.deepcopy(generic['adapters']['referenceRoutes']);routes['wrappers']=[]
    reference=modelview_packable_sources.validate_components(image,pins,core,routes)
    for parent in parents:need('actual-reference-parent-source',base+core['entryRva'],parent['source']['sourceTarget'])
    td=ctx.index.types['MemoryPack.Formatters.DictionaryFormatter`2']
    method,=[m for m in md.methods_for(td)if md.string(m.name_index)=='Deserialize']
    entry=ge.resolve(method.index,['ulong','object'],[]);body=owned(image,entry['pointer'])
    context=ContextSymbols(image).context(td.index);context_proof=dictionary_context(image,context)
    need('formatter-slot-ABI',(False,5,2,'void'),
        (bool(method.flags&16),method.slot,method.parameter_count,ctx.type_name(method.return_type)))
    _vtable(image,td.index,5,method.index,'levelScriptUlongDictionary')
    reader,out=md.parameters_for(method);reader_raw=image.pe.bytes_at_va(ctx.type_pointer(reader.type_index),16)
    need('reader-byref',(b'\x11\x20',ctx.index.types['MemoryPack.MemoryPackReader'].index),
        (reader_raw[10:12],int.from_bytes(reader_raw[:8],'little')))
    slots={r['relativeSlot']:r for r in context['entries']}
    output=image.pe.bytes_at_va(ctx.type_pointer(out.type_index),16)
    declared=image.pe.bytes_at_va(ctx.type_pointer(slots[3]['index']),16)
    need('same-owned-dictionary-byref',(b'\x15\x20',declared[:8]),(output[10:12],output[:8]))
    element=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    key_method,=[m for m in md.methods_for(element)if md.string(m.name_index)=='Deserialize']
    key_entry=ge.resolve(key_method.index,['ulong'],[])
    s=dict(context=_body_target(body,'mov rcx, [rcx+0xc0]'),allocate=_body_target(body,'mov rcx, rax'),
        initialize=_body_target(body,'mov r8, [r8+0x8]'),comparer=_body_target(body,'mov rcx, [rcx+0x10]'),
        barrier=_body_target(body,'mov [r15], rdi'),keyProvider=_body_target(body,'mov rcx, [rcx+0x30]'),
        valueProvider=_body_target(body,'mov rcx, [rcx+0x38]'),prepare=_body_target(body,'mov rcx, [r14]'),
        valueDispatch=_body_target(body,'mov rdx, rbp'),tryInsert=_body_target(body,'mov r9b, 0x2'),
        keyCallback=key_entry['pointer'])
    offsets=scalar.reader_offsets(image,'levelScriptUlongDictionary')
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    programs=[dictionary_program(body['regions'],body['pointer'],offsets,s,count=n,same_comparer=c)
        for n in(-1,0,1,2)for c in(False,True)]
    key_source=owned(image,key_entry['pointer']);key_proof=ulong_formatter_program(key_source['regions'],key_source['pointer'],offsets)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==BRIEF]
    mm=methods(image,wrapper);pair=derive_pair(image,BRIEF);adapter=derive_adapter(image,pins,pair,wrapper)
    need('same-value-dispatch',base+adapter['canonicalRoutes']['symbolRvas']['dispatch'],s['valueDispatch'])
    current=owners['owners'][BRIEF];reader=mm['Deserialize']
    need('same-complete-Brief-reader',current['method'],[reader.index,wrapper.name,'Deserialize',image.method_pointer_va(reader)-base])
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    ctor=owned(image,image.method_pointer_va(mm['.ctor']))
    cs=dict(allocate=_body_target(ctor,'mov rbx, rax',before=True),
        originalConstructor=_body_target(ctor,'mov rcx, rax'),barrier=s['barrier'])
    constructor=brief_constructor_program(ctor['regions'],ctor['pointer'],cs)
    usage=derive_typed_usage_context(image,constructor['typedAllocation']['instruction']-base,label='levelScriptBrief.original-allocation')
    need('typed-Brief-original-allocation',(1,BRIEF),(usage['tag'],usage['typeName']))
    original_ctor,=[m for m in md.methods_for(ctx.index.types[BRIEF])
        if md.string(m.name_index)=='.ctor'and not m.parameter_count and image.method_pointer_va(m)==cs['originalConstructor']]
    scalar.owned_method_abi(image,ctx,original_ctor.index,original_ctor.declaring_type,('void',1,False),[],
        'levelScriptBrief.original-constructor')
    string_fact=_load('levelscript_pooled_string_list_native.json',pins)
    strings=pooled_string_list_sources.validate_string_components(image,string_fact)
    string_type=ctx.index.types['MemoryPack.BeyondStringFormatter']
    string_method,=[m for m in md.methods_for(string_type)if md.string(m.name_index)=='Deserialize']
    dispatch=owned(image,s['valueDispatch'])
    string_dispatch=deserialize_slot(dispatch['regions'],dispatch['pointer'],prepare=s['prepare'],
        callback=image.method_pointer_va(string_method))
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    capabilities={}
    for parent in parents:
        name=parent['field']['typeName'];value=parent['closedCarrier']['classArguments'][1]['name']
        admitted=value=='string'
        capabilities[name]=dict(countLimit=16384,headerBytes=4,keyWireBytes=8,
            valueType=value,valueWireBytes=4 if value=='string'else None,
            recordMemberCount=9 if value==BRIEF else None,nullRecordBytes=1 if value==BRIEF else None,
            counts='-1-or-nonnegative',wholeGrammarAdmitted=admitted,
            recordSourceAdmitted=value==BRIEF,elementGrammarAdmitted=admitted,
            requiredChildCapabilities=['System.Collections.Generic.List`1<ulong>',
                'System.Collections.Generic.List`1<Beyond.Gameplay.ParamKeyValue>',
                'System.Collections.Generic.Dictionary`2<int,string>']if value==BRIEF else[],
            wholeOwnerAdmitted=False)
    return json.loads(json.dumps(dict(nativeInputs=pins,parents=parents,registration=entry,
        context=context,contextProof=context_proof,referenceParentSource=reference,
        programs=programs,sourceWindows=body['windows'],symbolRvas={k:v-base for k,v in s.items()},
        keyRegistration=key_entry,keySourceWindows=key_source['windows'],keyProgram=key_proof,
        brief=dict(profile=pair,adapter=adapter,getter=getter,constructor=constructor,
            constructorWindows=ctor['windows'],typedAllocation=usage,originalConstructorDefinition=original_ctor.index,
            ownerSource=current,propertyGraphGrammarDelegated=True),pooledStringCallback=strings,
        pooledStringDispatch=string_dispatch,valueDispatchWindows=dispatch['windows'],
        barrier=dict(source=barrier,proof=barrier_proof),capabilities=capabilities,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
