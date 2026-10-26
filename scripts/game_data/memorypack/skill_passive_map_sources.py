"""Current passive-map source programs and their independently typed array.

The ordinary AbilityActionMap is not an ability action union and its array
holds SequenceActionData references, not AbilityActionData references. Native
composition owns both distinctions; the caller's list/count proof cannot
supply a child grammar. Runtime callbacks and helper effects remain explicit
conditions, and no action execution/order is inferred from stored fields.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillPassiveMapSources'
ORIGINAL='Beyond.Gameplay.Core.AbilityActionMap'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_AbilityActionMapForMemoryPack'
ELEMENT='Beyond.Gameplay.Core.SequenceActionData'


def map_program(regions,entry,offsets,slots,*,ff=False):
    """Complete initialized existing-wrapper MC2 or FF, through tail barrier."""
    if type(ff)is not bool or set(slots)!={'abilityEvent','actions'}:
        raise ValueError(LABEL+'.map:scope')
    if any(type(n)is not int or not 16<=n<128 for n in slots.values()):
        raise ValueError(LABEL+'.map:field-offsets')
    if set(range(slots['abilityEvent'],slots['abilityEvent']+4))&set(range(slots['actions'],slots['actions']+8)):
        raise ValueError(LABEL+'.map:overlapping-fields')
    g=BytesPath(regions,entry)
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    flag=g.relative('803d');g.take('00','488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('74',ff,1)
    contexts=[];calls=[];failures=[]
    if ff:
        g.take('48c70700000000','488bcf');g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',False)
        g.take('4080fe02');g.branch('0f85',False)
        at=g.at;contexts.append(dict(instruction=at,cell=g.relative('488b15')))
        g.take('488bcb','488b37');at=g.at;calls.append(dict(instruction=at,target=g.relative('e8')))
        g.take('4885f6');failures.append(g.relative('74',1))
        g.take('488b4e10','4885c9');failures.append(g.relative('74',1))
        g.take('8941'+bytes((slots['abilityEvent'],)).hex(),'488bcb')
        at=g.at;contexts.append(dict(instruction=at,cell=g.relative('488b15')))
        g.take('488b3f');at=g.at;calls.append(dict(instruction=at,target=g.relative('e8')))
        g.take('4885ff');failures.append(g.relative('74',1))
        g.take('488b4f10','4885c9');failures.append(g.relative('74',1))
        g.take('488941'+bytes((slots['actions'],)).hex(),'4883c1'+bytes((slots['actions'],)).hex())
        if len(set(failures))!=1 or failures[0]not in g.bytes:
            raise ValueError(LABEL+'.map:null-failure-ownership')
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,initializedFlag=flag+1,memberCount=None if ff else 2,
        wrapperNull=ff,typedContexts=contexts,sourceCalls=calls,referenceBarrier=barrier,
        headerBytes=1,completeSelectedReturnViaBarrier=True,sameReaderAndOutput=True,
        sourceReader='incoming RCX preserved in RBX',wrapperOutput='incoming RDX preserved in RDI',
        savedRegistersRestored=['rbx','rbp','rsi','rdi'],entryRspRestored=True,
        positiveElementsAdmitted=False)


def sequence_array_program(regions,entry,offsets,symbols,*,count=1,count_limit=17):
    """Own actual ReadArray<Sequence> bytes, callback references and return.

    Count witnesses exercise the same repeated exact loop. Neither the output
    slot stride nor a declared element type supplies any serialized width.
    """
    if (type(count)is not int or type(count_limit)is not int
            or not 0<=count_limit<=17 or not -1<=count<=count_limit):
        raise ValueError(LABEL+'.array:count-scope')
    g=BytesPath(regions,entry)
    cur,rem,adv,used,total=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed','totalLength'))
    g.take('48895c2418','48896c2420','56','57','4156','4883ec20',
        '48837a3800','488bfa','488bd9');g.branch('75',True,1)
    g.take('488b4738','33f6','4889742440','488b38','48397738');g.branch('75',True,1)
    g.take('837b'+rem+'04');g.branch('7d',True,1)
    g.take('488b43'+cur,'8b28','448b73'+rem,'4183c6fc');g.branch('79',True,1)
    g.take('488343'+cur+'04','8343'+adv+'04','8343'+used+'04','448973'+rem,
        '486343'+used,'488b4b'+total,'482bc8','4863c5','483bc8');g.branch('0f8c',False)
    g.take('83fdff');g.branch('0f84',count==-1)
    collectors=[];callbacks=[];provider_usage=None
    if count==-1:
        collectors.append(g.relative('3935'));g.take('4889742440');g.branch('74',True,1)
    else:
        g.take('85ed');g.branch('0f84',count==0)
        if count==0:
            g.take('488b4738','488b5808','48397338');g.branch('75',True,1)
            g.take('488b4338','488b00','f6803801000001');g.branch('75',True,1)
            g.take('39b0e0000000');g.branch('75',True,1)
            g.take('488b4338','488b00','f6803801000001');g.branch('75',True,1)
            collectors.append(g.relative('3935'))
            g.take('488b80b8000000','488b08','48894c2440');g.branch('0f84',True)
        else:
            g.take('488b442440','4885c0');g.branch('74',True,1)
            g.take('488b4738','488b4010','f6803801000001');g.branch('75',True,1)
            g.take('488bd5','488bc8');g.call(symbols['arrayAllocate'])
            collectors.append(g.relative('3935'));g.take('4889442440');g.branch('74',True,1)
            provider_usage=g.at;provider_cell=g.relative('488b0d')
            g.take('39b1e0000000');g.branch('75',True,1)
            g.take('488b4f38','488b4918');g.call(symbols['provider'])
            g.take('4c8bf0','85ed');g.branch('0f8e',False)
            g.take('6666660f1f840000000000');loop=g.at
            for i in range(count):
                if g.at!=loop:raise ValueError(LABEL+'.array:loop-backedge')
                g.take('488b7c2440','4885ff');g.branch('0f84',False)
                g.take('4d85f6');g.branch('0f84',False)
                g.take('3b7718');g.branch('0f83',False)
                g.take('498b0e');g.call(symbols['prepare'])
                g.take('4d8b0e','488bd3','8bc6','498bce','4883c004','4c8d04c7',
                    '498b8190010000','4d8b8998010000')
                callbacks.append(g.at);g.take('ffd0','ffc6','3bf5');g.branch('7c',i+1<count,1)
            g.jump('e9')
    g.take('488b442440','488b5c2450','488b6c2458','4883c420','415e','5f','5e','c3')
    if len(set(collectors))!=1:raise ValueError(LABEL+'.array:collector-identity')
    return dict(selectedBytes=g.seen,countWitness=count,headerBytes=4,
        initializedReturnLocalBytes=8,returnedReference='unchanged complete local RSP+64 -> RAX',
        callbackSites=callbacks,callbackAbi=dict(receiver='r14',reader='same incoming Reader in RBX',
            output='fresh array+32+index*8',callbackClassOffset=400,methodInfoClassOffset=408),
        referenceSlotBytes=8,arrayLengthOffset=24,providerUsageInstruction=provider_usage,
        collectorFlag=collectors[0],completeSelectedReturn=True,
        nonvolatileRegistersRestored=['rbx','rbp','rsi','rdi','r14'],entryRspRestored=True,
        loopInvariant='Before iteration i: index=i, 0<=i<count, prior i callbacks completed exactly once on same Reader and distinct fresh array reference slots; increment and signed compare produce i+1 and return at count. Child source effects are separately composed.',
        elementGrammarAdmitted=False)


def _barrier(image,pointer):
    """Actual bounded jump thunks into the independently owned disabled leaf."""
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.levelscript_two_routes_native import _window
    base=image.pe.image_base;seen=set();thunks=[]
    while image.pe.bytes_at_va(pointer,1)==b'\xe9':
        if pointer in seen or len(seen)>=4:raise ValueError(LABEL+'.barrier:cycle-or-depth')
        seen.add(pointer);raw=image.pe.bytes_at_va(pointer,5)
        target=pointer+5+int.from_bytes(raw[1:],'little',signed=True)
        thunks.append(dict(instruction=[pointer-base,raw.hex().upper()],
            window=_window(image,pointer,pointer+5,'actual one-instruction barrier jump; full extent unclaimed'),targetRva=target-base))
        pointer=target
    proof,checked,_=_fast_barrier(image,pointer)
    return dict(actualEntryRva=(base+thunks[0]['instruction'][0]if thunks else pointer)-base,
        thunks=thunks,disabledLeaf=proof,result=checked)


def derive(image,pins):
    """Fresh nominal map/enum/array proof, separate from parent list framing."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned,methods
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_wrapper_holder
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_action_null_source import derive_reference_null
    from scripts.game_data.memorypack.array_reference_sources import validate_read_array_context
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);wrapper=_selected_wrapper(image,WRAPPER)
    enum='Beyond.Gameplay.Core.AbilitySystem+Event'
    need('mapOriginal',ORIGINAL,wrapper.wrapped_type)
    need('mapMemberOrder',[('abilityEvent',enum),('actions',ELEMENT+'[]')],
        [(m.name,m.declared_type)for m in wrapper.members])
    slots={name:ctx.field(ORIGINAL+'::'+name)[2]for name in('abilityEvent','actions')}
    method=methods(image,wrapper)['Deserialize'];entry=image.method_pointer_va(method)
    body=owned(image,entry);offsets=scalar.reader_offsets(image,LABEL)
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    positive=map_program(body['regions'],entry,offsets,slots)
    null=map_program(body['regions'],entry,offsets,slots,ff=True)
    need('mapSameBarrier',positive['referenceBarrier'],null['referenceBarrier'])
    usages=[derive_typed_usage_context(image,row['instruction']-base,label=LABEL)for row in positive['typedContexts']]
    enum_request=bind_typed_read(image,usages[0],method_name='ReadUnmanaged',argument=enum,kind=17)
    integer=vector_recorder(image)(positive['sourceCalls'][0]['target']-base)
    scalar.integer_source(image,integer,offsets,LABEL+'.event')
    enum_proof=Build(image,pins).derive_enum(dict(typeName=enum,backingType='System.Int32',width=4))
    need('mapArrayRequest',('MemoryPack.MemoryPackReader','ReadArray',[],[ELEMENT]),
        tuple(usages[1][k]for k in('typeName','methodName','classArguments','methodArguments')))
    field,=[f for f in image.metadata.fields_for(ctx.index.types[ORIGINAL])if image.metadata.string(f.name_index)=='actions']
    array_raw=image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)
    need('mapArraySZArray',b'\x1d\x00',array_raw[10:12])
    element_pointer=int.from_bytes(array_raw[:8],'little');element_raw=image.pe.bytes_at_va(element_pointer,16)
    need('mapArrayReferenceElement',(b'\x12\x00',ctx.index.types[ELEMENT].index),
        (element_raw[10:12],int.from_bytes(element_raw[:8],'little')))
    array_target=positive['sourceCalls'][1]['target'];array=owned(image,array_target)
    by={int(r['va'],16)-array_target:r for r in array['rows']}
    def call(offset):
        row=by[offset];raw=bytes.fromhex(row['bytes'])
        need('arrayActualCall',(5,b'\xe8'),(len(raw),raw[:1]))
        return array_target+offset+5+int.from_bytes(raw[1:],'little',signed=True)
    symbols=dict(arrayAllocate=call(247),provider=call(373),prepare=call(435))
    programs={str(n):sequence_array_program(array['regions'],array_target,offsets,symbols,count=n)for n in range(-1,18)}
    reference=derive_reference_null(image,pins,ELEMENT)
    symbols_ctx=ContextSymbols(image);first=symbols_ctx.context(usages[1]['methodSpec'][0],is_method=True)
    second=symbols_ctx.context(first['entries'][0]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[first,second],label=LABEL+'.array')
    array_context=validate_read_array_context(image,[first,second],usages[1],GenericEntries(image),element_pointer,
        reference['readerContextProof']['formatterDeserializeDefinition'],fail=need)
    barrier=_barrier(image,positive['referenceBarrier'])
    for program in programs.values():
        need('arraySameCollector',barrier['result']['disabledFlagRva']+base,program['collectorFlag'])
    pair=derive_pair(image,ORIGINAL,WRAPPER)
    null_reference=derive_reference_null(image,pins,ORIGINAL,WRAPPER)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-conditional-passive-map',nativeInputs=pins,
        capabilities={
            'AbilityActionMap':dict(nullAdmitted=True,wholeGrammarAdmitted=True,memberCount=2,
                eventType=enum,sequenceArrayCapability='passive-map-sequence-array'),
            'passive-map-sequence-array':dict(nullable=True,collectionCounts=list(range(-1,18)),
                elementType=ELEMENT,elementCapability='SequenceActionData',referenceSlotBytes=8)},
        proof=dict(wrapperName=WRAPPER,wrappedType=ORIGINAL,holder=_wrapper_holder(ctx,image,wrapper),
            readerMethod=[method.index,WRAPPER,'Deserialize',entry-base],sourceWindows=body['windows'],
            programs=dict(positive=positive,ff=null),typedReads=usages,enumRequest=enum_request,
            enumBacking=enum_proof,integerSource=integer,pair=pair,originalNullReference=null_reference,
            array=dict(sourceTargetRva=array_target-base,sourceWindows=array['windows'],
                ownedContexts=[first,second],ownedArrayContext=array_context,sequenceReference=reference,
                programs={k:programs[k]for k in('-1','0','1','2','17')},symbols={k:v-base for k,v in symbols.items()}),
            barrier=barrier),
        wholeSkillDataAdmitted=False,evidenceBoundary=dict(
            exact='Own initialized current MC2/FF map source, exact Event enum32, independently typed SequenceActionData reference-array source/count/slot5 callback/return and named field transfers. Parent passive-list framing and child Sequence/action grammar remain independently composed.',
            conditional='Existing coherent compatible map wrapper/original, buffered nonwrapping disjoint Reader/source/output/frame, initialized closed MethodInfos/owned class contexts, normal typed allocation/preparation/provider/barrier ABI and selected compatible child callbacks. Array allocation is fresh and typed; empty-array contexts are initialized, collector disabled. Live callback/provider selection is unobserved.',
            structuralOnly='Stored event/sequence configuration does not prove event delivery, execution or authored timing.',
            unresolved=['unsupported actions/descendants','live callback/provider selection','cold/refill/malformed paths','whole SkillData']))))
