"""Finite current Vector3 list source; parent and whole-owner joins stay separate.

Ready compatible closed list/provider contexts and the exact independently
registered Vector3 callback are conditions. The selected list starts null;
normal typed count-sized allocation and ordinary helper effects provide empty
storage with enough capacity. Only buffered disjoint nonwrapping storage and
the exact no-growth normal paths are admitted. Live selection is unobserved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack import scalar_param_native as scalar

TYPE='UnityEngine.Vector3'
LIST='System.Collections.Generic.List`1<'+TYPE+'>'
CAP='story-vector3-list'
LIMIT=4096


def need(key,expected,actual):scalar.need('storyVector3List',key,expected,actual)


def list_program(regions,entry,s,offsets,*,count):
    need('literal-count-witness',True,type(count)is int and count in(-1,0,1,2,3))
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry);provider=callback=loop=backedge=None
    g.take('4053','55','4154','4157','4883ec48','488bda','33c0','4533e4',
        '4889442420','488bcb','4489642478','488d542478','89442428','498be9','4d8bf8')
    g.call(s['header']);g.take('84c0');g.branch('0f84',count==-1)
    if count==-1:
        g.take('498bcf','4d8927');g.call(s['barrier'])
    else:
        g.take('4c89ac2488000000','4889742470','4889bc2480000000','4c89742440',
            '448b6c2478','4d3927');g.branch('0f85',False)
        g.take('488b4d20','33d2','488b89c0000000');g.call(s['context'])
        g.take('488bc8');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
        g.take('488b4d20','488b91c0000000','488b4a08','4c396120');g.branch('0f84',False)
        g.take('488b4520','418bd5','488bcf','4c8b80c0000000','4d8b4008');g.call(s['constructor'])
        g.take('498bcf','49893f');g.call(s['barrier']);provider=g.relative('488b0d')
        g.take('4439a1e0000000');g.branch('0f84',False)
        g.take('488b4520','488b88c0000000','488b4918');g.call(s['provider'])
        g.take('488bf0','4585ed');g.branch('0f8e',count==0)
        if count:
            callback=g.relative('488d3d');need('selected-exact-callback',s['callback'],callback)
            g.take('0f1f4000','660f1f840000000000');loop=g.at
            for index in range(count):
                need('same-loop-head',loop,g.at)
                g.take('33c0','4889442420','89442428','4885f6');g.branch('0f84',False)
                g.take('488b0e');g.call(s['prepare'])
                g.take('488b06','4c8b9090010000','4c8b8898010000','4c3bd7');g.branch('0f85',False)
                g.take('837b'+rem+'0c');g.branch('0f8c',False)
                g.take('488b43'+cur,'f20f1000','f20f11442420','8b4008','89442428','8b7b'+rem,'83c7f4')
                g.branch('0f88',False)
                g.take('488343'+cur+'0c','8343'+adv+'0c','8343'+used+'0c','897b'+rem,
                    '498b3f','f20f10442420','448b742428','f20f11442478','4885ff');g.branch('0f84',False)
                g.take('488b4520','488b88c0000000','488b4130','4883782000');g.branch('0f84',False)
                g.take('488b4520','488d542430','488bcf','f20f11442430','4489742438',
                    '4c8b80c0000000','4d8b4030');g.call(s['add'])
                g.take('41ffc4');need('same-reloaded-callback',callback,g.relative('488d3d'))
                g.take('453be5');backedge=g.at;g.branch('0f8c',index+1<count)
        g.take('488b742470','488bbc2480000000','4c8b742440','4c8bac2488000000')
    g.take('4883c448','415f','415c','5d','5b','c3')
    return dict(selectedBytes=g.seen,countWitness=count,newList=True,loopHead=loop,backedge=backedge,
        providerClassCell=provider,selectedCallback=callback,headerBytes=4,elementWireBytes=12,
        managedElementBytes=12,capturedSourceSlices=[[0,8],[8,4]],storedArgumentSlices=[[0,8],[8,4]],
        headerCountHomeEntryOffset=16,elementCountRegister='r13d',counterRegister='r12d',
        completeFrameAndNonvolatilesRestored=True,normalReturn=True,
        countInvariant='R12D starts zero; R13D is the immutable signed header count. One exact raw12 read and same full12 Add precede the sole increment and signed backedge. The positive branch returns at R12D=count without overflow under the finite bound.',
        stackHomesDisjoint=True,initiallyNullListRequired=True,elementCallbacksInvoked=0,elementReads=max(count,0))


def callback_program(regions,entry,offsets):
    cur,rem,adv,used=(bytes((offsets[k],)).hex()for k in('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20','837a'+rem+'0c','498bf8','488bda');g.branch('0f8c',False)
    g.take('488b4a'+cur,'f20f1001','8b4108','f20f1107','894708','8b7b'+rem,'83c7f4');g.branch('0f88',False)
    g.take('488343'+cur+'0c','8343'+adv+'0c','8343'+used+'0c','897b'+rem,
        '488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,wireBytes=12,outputBytes=12,rawSourceSlices=[[0,8],[8,4]],
        readerRegister='incoming rdx',outputRegister='incoming r8',normalReturn=True,completeFrameRestored=True)


def add_program(regions,entry):
    """Actual optimized helper, independently of the registered generic body."""
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec30','ff411c','498bf0','4c8b4910',
        '488bfa','48634118','488bd9','4d85c9');g.branch('0f84',False)
    g.take('413b4118');g.branch('73',False,1)
    g.take('8d4801','894b18','413b4118');g.branch('0f83',False)
    g.take('f20f1002','488d0440','498d0c81','8b4208','f20f114120','894128',
        '488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,arrayStrideBytes=12,rawStores=[[0,8],[8,4]],sizeIncrement=1,
        incomingValueRegister='rdx-pointer',normalReturn=True,completeFrameRestored=True,
        canonicalPointerEquivalenceClaimed=False,capacityGreaterThanInitialSizeRequired=True)


def canonical_add_program(regions,entry,array_set):
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec30','ff411c','488bd9','488b4910',
        '498bf8','488bf2','4c634318','4885c9');g.branch('75',True,1)
    g.take('443b4118');g.branch('72',True,1)
    g.take('f20f1002','418d4001','894318','8b4208','498bd0','4c8d442420','f20f11442420','89442428')
    g.call(array_set);g.take('488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,rawArgumentSlices=[[0,8],[8,4]],sizeIncrement=1,arrayIndex='old size',
        incomingValueRegister='rdx-pointer',normalReturn=True,completeFrameRestored=True,
        capacityGreaterThanInitialSizeRequired=True)


def array_set_program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('4883ec28','3b5118');g.branch('73',False,1)
    g.take('f2410f1000','488d0452','488d0c81','418b4008','f20f114120','894128','4883c428','c3')
    return dict(selectedBytes=g.seen,arrayStrideBytes=12,rawStores=[[0,8],[8,4]],
        arrayRegister='incoming rcx',indexRegister='incoming edx',valueRegister='incoming r8-pointer',
        normalReturn=True,completeFrameRestored=True,indexInsideArrayRequired=True)


def derive(image,pins,*,typed_request,call_target):
    """Fresh exact caller/closed source; no enclosing field admission."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.contracts import CONTRACTS_DIR
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,validate_generic_contexts
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.memorypack import float_list_sources,lang_key_list_sources,numeric_list_sources,pooled_global_buff_id_sources
    from scripts.game_data.memorypack.counted_loop_sources import prove_induction
    from scripts.game_data.memorypack.levelscript_interactive_sources import dictionary_header_program,key_provider_program
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.skill_value_list_context import derive as list_context
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;ge=GenericEntries(image)
    context,body=list_context(image,pins,typed_request=typed_request,call_target=call_target,element_type=TYPE)
    definition=ctx.index.types[TYPE]
    need('nominal-nongeneric-value',(True,False,'System.ValueType',-1),
        (ctx.is_value_type(TYPE),ctx.is_enum(TYPE),ctx.parent(TYPE),definition.generic_container_index))
    fields=[f for f in md.fields_for(definition)if not ctx.field_attributes(f.type_index)&16]
    layout=[list(ctx.field(TYPE+'::'+md.string(f.name_index)))[1:]for f in fields]
    need('complete-three-Single-layout',[['float',16],['float',20],['float',24]],layout)
    need('complete-three-nominal-field-names',['x','y','z'],[md.string(f.name_index)for f in fields])
    for field in fields:need('ordinary-Single-field',bytes.fromhex('0c80'),image.pe.bytes_at_va(ctx.type_pointer(field.type_index),16)[10:12])
    need('bounded-type-size-slot',True,0<=definition.index<image.registration['typeDefinitionsSizesCount'])
    size=image.pe.u64_at_va(int(image.registration['typeDefinitionsSizes'],16)+8*definition.index)
    need('boxed-and-native-size',(28,12),(image.pe.u32_at_va(size),image.pe.u32_at_va(size+4)))
    callback_td=ctx.index.types['MemoryPack.Formatters.UnmanagedFormatter`1']
    callback_method,=[m for m in md.methods_for(callback_td)if md.string(m.name_index)=='Deserialize']
    registration=json.loads(json.dumps(ge.resolve(callback_method.index,[TYPE],[])));element=owned(image,registration['pointer'])
    need('same-exact-closed-element',context['registration']['classInstantiation']['arguments'],registration['classInstantiation']['arguments'])
    slots={r['relativeSlot']:r for r in context['context']['entries']}
    s={role:_body_target(body,text,before=before)for role,text,before in(
        ('header','test al, al',True),('context','mov rcx, [rcx+0xc0]',False),('allocate','mov rcx, rax',False),
        ('constructor','mov r8, [r8+0x8]',False),('barrier','mov [r15], rdi',False),
        ('provider','mov rcx, [rcx+0x18]',False),('prepare','mov rcx, [rsi]',False),('add','mov r8, [r8+0x30]',False))}
    s['callback']=element['pointer'];offsets=scalar.reader_offsets(image,'storyVector3List')
    programs=[list_program(body['regions'],body['pointer'],s,offsets,count=n)for n in(-1,0,1,2,3)]
    induction=prove_induction(programs,initial='4533e4',increment='41ffc4',comparison='453be5',
        counter='r12d',saved_count='r13d',max_count=LIMIT)
    sources={name:owned(image,s[name])for name in('header','constructor','provider','add')}
    callback=callback_program(element['regions'],element['pointer'],offsets)
    actual_add=add_program(sources['add']['regions'],s['add'])
    list_method,=[m for m in md.methods_for(ctx.index.types['MemoryPack.Formatters.ListFormatter`1'])if md.string(m.name_index)=='Deserialize']
    definitions=dict(list=list_method.index,callback=callback_method.index,
        capacity=slots[1]['methodSpec'][0],Clear=slots[2]['methodSpec'][0],Add=slots[6]['methodSpec'][0])
    abis=float_list_sources._method_abis(image,ctx,definitions,context['context'])
    ctor_registration=ge.resolve(definitions['capacity'],[TYPE],[])
    need('actual-closed-capacity-constructor',ctor_registration['pointer'],s['constructor'])
    canonical_registration=ge.resolve(definitions['Add'],[TYPE],[]);canonical_add=owned(image,canonical_registration['pointer'])
    rows=canonical_add['rows'];array_target,=[control_transfer(r)['target']for i,r in enumerate(rows)
        if bytes.fromhex(r['bytes'])[:1]==b'\xe8'and i and rows[i-1]['text']=='mov [rsp+0x28], eax']
    array_body=owned(image,array_target)
    canonical_program=canonical_add_program(canonical_add['regions'],canonical_add['pointer'],array_target)
    array_program=array_set_program(array_body['regions'],array_target)
    ctor=sources['constructor'];cs=dict(context=s['context'],barrier=s['barrier'],arrayAllocate=_body_target(ctor,'mov rcx, rax'))
    constructors=[float_list_sources.capacity_program(ctor['regions'],ctor['pointer'],cs,positive=p)for p in(False,True)]
    offsets['totalLength']=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
    header=dictionary_header_program(sources['header']['regions'],s['header'],offsets)
    pc=ContextSymbols(image).context(slots[3]['methodSpec'][0],is_method=True)
    validate_generic_contexts(image,[pc],label='storyVector3List.provider');pcs={r['relativeSlot']:r for r in pc['entries']}
    need('provider-context-slots',[0,1],sorted(pcs));pm=md.methods[pc['definition']]
    need('provider-nominal-static-ABI',('MemoryPack.MemoryPackFormatterProvider','GetFormatter',True,0),
        (image.type_name(pm.declaring_type),md.string(pm.name_index),bool(pm.flags&16),pm.parameter_count))
    need('provider-owned-return',ctx.type_pointer(pm.return_type),ctx.type_pointer(pcs[1]['index']))
    need('provider-owned-formatter-result','MemoryPack.MemoryPackFormatter`1',pcs[1]['type']['definition']['name'])
    for child in(pcs[0]['type'],pcs[1]['type']['classArguments'][0]):
        need('provider-owned-MVAR',(pm.index,0),(child['parameterOwner']['methodIndex'],child['parameterOwner']['ordinal']))
    provider=sources['provider'];calls=[control_transfer(r)['target']for r in provider['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'][:4]
    need('four-provider-normal-calls',4,len(calls));ps=dict(zip(('typeFromHandle','backend','type','assignable'),calls,strict=True))
    provider_program=key_provider_program(provider['regions'],provider['pointer'],dict(typeHandle=ps['typeFromHandle'],
        keyBackend=ps['backend'],context=ps['type'],cast=ps['assignable']))
    cast=owned(image,ps['assignable']);predicate=_body_target(cast,'mov rcx, [rcx]')
    cast_program=pooled_global_buff_id_sources.successful_cast(cast['regions'],cast['pointer'],predicate)
    need('same-indexed-provider-context',s['context'],ps['type'])
    dep_path=CONTRACTS_DIR/'levelscript_int_list_native.json';dep_raw=dep_path.read_bytes();dep=json.loads(dep_raw)
    need('generic-provider-build',pins,dep['nativeInputs']);backend=owned(image,ps['backend'])
    backend_target=base+dep['bodies']['providerBackend']['entryRva']
    backend_program=numeric_list_sources.uint_backend_forward_program(backend['regions'],backend['pointer'],backend_target)
    factory=lang_key_list_sources.generic_provider_factory(image,pins,dict(backend=backend_target,context=s['context']),need)
    usages=[]
    for owner,cell,name in((body,programs[1]['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (provider,provider_program['typeClassCell'],'System.Type'),(provider,provider_program['providerClassCell'],'MemoryPack.MemoryPackFormatterProvider'),
        (backend,backend_program['providerOwnerCell'],'MemoryPack.MemoryPackFormatterProvider')):
        row,=[r for r in owner['rows']if len(bytes.fromhex(r['bytes']))==7 and bytes.fromhex(r['bytes'])[:3]==b'\x48\x8b\x0d'
            and int(r['va'],16)+7+int.from_bytes(bytes.fromhex(r['bytes'])[3:],'little',signed=True)==cell]
        usage=derive_typed_usage_context(image,int(row['va'],16)-base,label='storyVector3List.namedCell')
        need('actual-named-provider-cell',(1,name),(usage['tag'],usage['typeName']));usages.append(usage)
    need('same-Type-key-provider-class',factory['providerClassCell'],programs[1]['providerClassCell'])
    need('same-backend-provider-class',factory['providerClassCell'],backend_program['providerOwnerCell'])
    barrier,barrier_proof,_=_fast_barrier(image,s['barrier'])
    need('dependency-bookend',dep_raw,dep_path.read_bytes());_publication_gate(image,pins)
    cap=dict(typeName=LIST,elementType=TYPE,capability=CAP,countLimit=LIMIT,countRange=[-1,LIMIT],nullable=True,
        positiveCountsAdmitted=True,headerBytes=4,elementWireBytes=12,managedElementBytes=12,
        elementRecordHeaderBytes=0,rawBitsPreserved=True,finiteFloatProfile=True,initiallyNullListRequired=True,
        packableReaderMethodDefinition=typed_request['methodSpec'][0],packableReaderTargetRva=call_target-base,
        wholeGrammarAdmitted=True,actualCallbackEqualsProvedChildRequired=True,runtimeProviderSelectionObserved=False)
    return json.loads(json.dumps(dict(schema='endfield.story-vector3-list-component.v1',status='validated-conditional-vector3-list',nativeInputs=pins,
        capability=cap,parentFieldAdmitted=False,wholeOwnerAdmitted=False,
        proof=dict(context=context,layout=layout,callbackRegistration=registration,callback=callback,listPrograms=programs,
            induction=induction,actualAdd=actual_add,canonicalAddRegistration=canonical_registration,canonicalAdd=canonical_program,
            arraySet=array_program,methodAbis=abis,constructorRegistration=ctor_registration,constructors=constructors,
            header=header,providerContext=pc,provider=provider_program,successfulCast=cast_program,backend=backend_program,factory=factory,classUsages=usages,
            barrier=dict(source=barrier,proof=barrier_proof),symbolRvas={k:v-base for k,v in s.items()},
            sourceWindows=dict(list=body['windows'],callback=element['windows'],canonicalAdd=canonical_add['windows'],
                arraySet=array_body['windows'],backend=backend['windows'],cast=cast['windows'],**{k:v['windows']for k,v in sources.items()})),
        evidenceBoundary=dict(exact='Fresh actual reference caller/closed list context, exact nominal Vector3 layout and registration, separate complete raw12 callback/list/actual Add/canonical Add/array store/header/capacity/provider programs and finite count induction.',
            conditional=__doc__,unresolved=['actual enclosing field/local/store','cold/refill/growth and existing lists',
                'runtime provider/default/override selection','whole owner/physical EOF']))))
