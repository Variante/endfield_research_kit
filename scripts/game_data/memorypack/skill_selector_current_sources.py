"""Current selector source components, composed by exact nominal union owners.

Zero-member records still have their own ordinary object header; that header
is distinct from the outer selector union tag and from the canonical FF marker.
No metadata name, zero field count or historical tag alone grants admission.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='skillSelectorCurrentSources'
FAMILIES={name:'Beyond.MemoryPack.Beyond_Gameplay_Core_Selector_'+suffix+'_DataForMemoryPack'
    for name,suffix in(('SelectorFinder','Finder'),('SelectorValidator','Validator'),
        ('SelectorPostProcessor','PostProcessor'))}


def _peek(g,n=1):return bytes(g.bytes[g.at+i]for i in range(n))


def _equal_branch(g,taken):
    if _peek(g)==b'\x74':g.branch('74',taken,1)
    elif _peek(g,2)==b'\x0f\x84':g.branch('0f84',taken)
    else:raise ValueError(LABEL+'.branch:expected-equal')


def _initialized(g):
    if _peek(g)==b'\x75':g.branch('75',True,1)
    elif _peek(g)==b'\x74':g.branch('74',False,1)
    elif _peek(g,2)==b'\x0f\x84':g.branch('0f84',False)
    else:raise ValueError(LABEL+'.branch:expected-initialized-guard')


def zero_program(regions,entry,symbols,*,ff=False,allocated=False):
    """Complete initialized existing-wrapper zero-header/FF source and frame."""
    if type(ff)is not bool or type(allocated)is not bool or ff and allocated:raise ValueError(LABEL+'.zero:mode')
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20')
    flag=g.relative('803d');g.take('00','488bda','488bf9');_initialized(g)
    g.take('488b0b','c644243800','4885c9')
    if _peek(g,2)==b'\x0f\x85':
        g.branch('0f85',not allocated)
        if not allocated:
            g.take('33d2');g.call(symbols['prehook']);g.take('90');g.jump('e9')
    else:
        g.branch('74',allocated,1)
        if not allocated:g.take('33d2');g.call(symbols['prehook'])
    g.take('488d542438','488bcf');g.call(symbols['header'])
    g.take('84c0');_equal_branch(g,ff)
    allocation=None
    if ff:
        g.take('488bcb','48c70300000000');g.call(symbols['barrier'])
        if _peek(g)==b'\x90':g.take('90')
        if _peek(g)==b'\xe9':g.jump('e9')
        elif _peek(g)==b'\xeb':g.jump('eb',1)
    else:
        g.take('48833b00');g.branch('75',not allocated,1)
        if allocated:
            allocation=g.at;g.relative('488b0d');g.call(symbols['allocate'])
            g.take('488bf8','4885c0')
            if _peek(g)==b'\x75':g.branch('75',True,1);g.take('33d2','488bcf')
            else:g.branch('0f84'if _peek(g,2)==b'\x0f\x84'else'74',False,4 if _peek(g,2)==b'\x0f\x84'else 1);g.take('33d2','488bc8')
            g.call(symbols['constructor']);g.take('488bcb','48893b');g.call(symbols['barrier'])
        if _peek(g,2)==b'\x0f\xb6':g.take('0fb67c2438')
        else:g.take('408a7c2438')
        g.take('4084ff')
        if _peek(g)==b'\x74':g.branch('74',True,1)
        elif _peek(g)==b'\x75':g.branch('75',False,1)
        elif _peek(g,2)==b'\x0f\x85':g.branch('0f85',False)
        else:raise ValueError(LABEL+'.zero:header-zero-return-guard')
    g.take('488b5c2430','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag+1,wrapperNull=ff,
        positiveMemberCount=None if ff else 0,headerBytes=1,sameReader=True,
        prehookTarget=symbols['prehook'],headerTarget=symbols['header'],
        barrierTarget=symbols['barrier']if ff else None,normalReturn=True,
        allocated=allocated,allocationUsageSite=allocation,
        originalOutput='incoming RDX preserved in RBX',reader='incoming RCX preserved in RDI',
        restoredRegisters=['rbx','rdi'],entryRspRestored=True)


def inline_zero_program(regions,entry,offsets,symbols,*,ff=False,allocated=False):
    """Own inline byte header, all Reader counters, output clear and return."""
    if type(ff)is not bool or type(allocated)is not bool or ff and allocated:raise ValueError(LABEL+'.inlineZero:mode')
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in
        ('currentPtr','bufferLength','advancedCount','consumed'))
    g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    flag=g.relative('803d');g.take('00','488bfa','488bd9');_initialized(g)
    g.take('488b0f','4885c9');g.branch('0f85',not allocated)
    if not allocated:g.take('33d2');g.call(symbols['prehook']);g.take('90');g.jump('e9')
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff')
    g.branch('74',ff,1)
    allocation=None
    if ff:
        g.take('488bcf','48c70700000000');g.call(symbols['barrier']);g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('75',not allocated,1)
        if allocated:
            allocation=g.at;g.relative('488b0d');g.call(symbols['allocate'])
            g.take('488bd8','4885c0');g.branch('74',False,1)
            g.take('33d2','488bc8');g.call(symbols['constructor'])
            g.take('488bcf','48891f');g.call(symbols['barrier'])
        g.take('4084f6');g.branch('0f85',False)
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,initializedFlag=flag+1,wrapperNull=ff,
        positiveMemberCount=None if ff else 0,headerBytes=1,sameReader=True,
        readerEffects=dict(currentPtr=1,bufferLength=-1,advancedCount=1,consumed=1),
        prehookTarget=symbols['prehook'],headerTarget=None,
        barrierTarget=symbols['barrier']if ff else None,normalReturn=True,
        allocated=allocated,allocationUsageSite=allocation,
        originalOutput='incoming RDX preserved in RDI',reader='incoming RCX preserved in RBX',
        restoredRegisters=['rbx','rbp','rsi','rdi'],entryRspRestored=True)


def factory_program(regions,entry,barrier,*,ctor=False):
    """Current zero-field factory: allocate, base holder, exact typed cache."""
    if type(ctor)is not bool:raise ValueError(LABEL+'.factory:mode')
    g=BytesPath(regions,entry);delayed=_peek(g,2)==b'\x40\x57'
    if delayed:g.take('4057')
    else:g.take('48895c2408','57')
    g.take('4883ec20');flag=g.relative('803d')+1
    g.take('00','488bf9');_initialized(g)
    base_usage=base_ready=None
    if ctor:
        site=g.at;cell=g.relative('488b0d');base_usage=dict(site=site,cell=cell)
        if _peek(g,2)==b'\x83\xb9':
            g.take('83b9e000000000')
            if _peek(g)==b'\x75':g.branch('75',True,1)
            else:g.branch('0f84',False)
        else:base_ready=g.relative('e8')
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell)
    allocator=g.relative('e8');g.take('4885c0')
    if _peek(g)==b'\x75':g.branch('75',True,1)
    else:g.branch('74',False,1)
    g.take('4533c0')
    if delayed:g.take('48895c2430')
    g.take('488bd0','488bcf');setter=g.relative('e8')
    g.take('488b5f10');usages=[];casts=[]
    for i in range(2):
        site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell))
        if i==0:g.take('488bcb')
        casts.append(g.relative('e8'))
        if i==0:g.take('48894718','488bcb')
    if len(set(casts))!=1 or any(u['cell']!=allocation['cell']for u in usages):
        raise ValueError(LABEL+'.factory:typed-class-and-cast-identity')
    g.take('488d4f18','488b5c2430','4883c420','5f')
    if g.relative('e9')!=barrier:raise ValueError(LABEL+'.factory:barrier-target')
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=ctor,
        allocation=allocation,baseClassUsage=base_usage,baseReady=base_ready,
        allocationTarget=allocator,instanceSetter=setter,strictCast=casts[0],
        classUsages=usages,baseHolderOffset=16,typedCacheOffset=24,
        originalConstructorCalled=False,normalReturnViaBarrier=True,
        condition='Matching initialized classes, normal successful zeroed typed allocation and exact owned holder setter, compatible strict casts, disabled collector and disjoint valid wrapper storage. No original constructor/default behavior is inferred.')


def _calls(body):
    result=[]
    for index,row in enumerate(body['rows']):
        raw=bytes.fromhex(row['bytes']);site=int(row['va'],16)
        if len(raw)==5 and raw[0]==0xe8:
            result.append((index,site,site+5+int.from_bytes(raw[1:],'little',signed=True)))
    return result


def derive_zero_components(image,pins,*,wrapper_names=None):
    """Own zero-record components; union transfer remains a separate join."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.zero_wrapper_programs import prove_zero_wrapper_forwarder
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param,scalar_param_native as scalar
    from scripts.game_data.memorypack import module_structure_models as holders
    from scripts.game_data.memorypack.subgame_world_models import dual_holder
    from scripts.game_data.memorypack.reference_param_profile import _getter_windows
    from scripts.game_data.memorypack.modelview_reference_sources import get_value
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _wrapper_holder
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    from scripts.game_data.memorypack.union_dispatch import read_union_switch
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    need=lambda k,e,a:scalar.need(LABEL,k,e,a)
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrappers=derive_from_image(image);offsets=scalar.reader_offsets(image,LABEL)
    switches={family:read_union_switch(image,name,wrappers=wrappers)for family,name in FAMILIES.items()}
    by_name={w.name:w for w in wrappers.values()};components=[]
    requested=None if wrapper_names is None else set(wrapper_names)
    if requested is not None and (not requested or len(requested)!=len(wrapper_names)
            or any(not isinstance(name,str)for name in requested)):
        raise ValueError(LABEL+'.zero:explicit-distinct-wrapper-names-required')
    for family,switch in switches.items():
        for route in switch['entries']:
            wrapper=by_name[route['wrapperName']]
            if wrapper.members:continue
            if requested is not None and wrapper.name not in requested:continue
            mm=pointer.methods(image,wrapper)
            if 'Deserialize'not in mm:raise ValueError(LABEL+'.zero:no-static-reader:'+wrapper.name)
            original=wrapper.wrapped_type
            # The actual union caller requests ReadPackable<ConcreteWrapper>.
            # Its direct generated slot5 formatter does not use this concrete
            # Original's GenericMemoryPackFormatter registration. The base
            # union Original adapter/conversion is independently composed.
            formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
            formatter,=image.named_type_definitions[formatter_name]
            formatter_method,=[m for m in md.methods_for(formatter)if md.string(m.name_index)=='Deserialize']
            _vtable(image,formatter.index,5,formatter_method.index,LABEL)
            need('concrete-instance-slot5',(False,5,'void',2),
                (bool(formatter_method.flags&16),formatter_method.slot,ctx.type_name(formatter_method.return_type),formatter_method.parameter_count))
            scalar.ordinary(image,ctx.type_pointer(formatter_method.return_type),1,LABEL+'.formatterVoid')
            for parameter,type_name,kind in zip(md.parameters_for(formatter_method),('MemoryPack.MemoryPackReader',wrapper.name),(17,18),strict=True):
                raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
                need('concrete-formatter-byrefs',(type_name,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
            forward_source=pointer.owned(image,image.method_pointer_va(formatter_method));forward_calls=_calls(forward_source)
            forward_program=prove_zero_wrapper_forwarder(forward_source['rows'],
                dict(metadataInit=forward_calls[0][2],classInit=forward_calls[1][2]),image.method_pointer_va(mm['Deserialize']),label=LABEL+'.concreteForwarder')
            holder=_wrapper_holder(ctx,image,wrapper)
            need('zero-reference-holder',False,ctx.is_value_type(original))
            cache_fields=[ctx.field(wrapper.name+'::'+md.string(field.name_index))
                for field in md.fields_for(md.types[wrapper.type_definition])
                if not ctx.field_attributes(field.type_index)&16]
            need('zero-typed-cache',[(wrapper.name,original,24)],
                [field for field in cache_fields if field[2]==24])
            body=pointer.owned(image,image.method_pointer_va(mm['Deserialize']))
            primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
            calls=_calls(body);rows=body['rows'];entry=body['pointer']
            inline=image.pe.bytes_at_va(entry,10)==bytes.fromhex('48895c240848896c2410')
            header=None if inline else next(target for index,site,target in calls
                if site<entry+120 and bytes.fromhex(rows[index+1]['bytes'])==b'\x84\xc0')
            allocate=next(target for index,site,target in calls
                if bytes.fromhex(rows[index+1]['bytes'])in(b'\x48\x8b\xf8',b'\x48\x8b\xd8'))
            barrier=next(target for index,site,target in calls
                if bytes.fromhex(rows[index-1]['bytes'])in(bytes.fromhex('48c70300000000'),bytes.fromhex('48c70700000000')))
            symbols=dict(header=header,prehook=image.method_pointer_va(mm['OnDeserialized']),
                allocate=allocate,constructor=image.method_pointer_va(mm['.ctor']),barrier=barrier)
            programs=[]
            for mode in({},dict(ff=True),dict(allocated=True)):
                program=(inline_zero_program(body['regions'],entry,offsets,symbols,**mode)if inline
                    else zero_program(body['regions'],entry,symbols,**mode))
                if program['allocationUsageSite']is not None:
                    usage=derive_typed_usage_context(image,program['allocationUsageSite']-base,label=LABEL)
                    need('zero-wrapper-allocation',(1,wrapper.name),(usage['tag'],usage['typeName']))
                    program['wrapperAllocation']=usage
                programs.append(program)
            header_proof=None
            if header is not None:
                header_proof=vector_recorder(image)(header-base)
                primitive_param.object_header_source(image,header_proof,offsets)
            barrier_proof=_barrier(image,barrier)
            getter_windows,thunk=_getter_windows(image,md.types[wrapper.type_definition],mm['GetValue'])
            need('owned-concrete-getter-tail','owned-zero-context-getter-tail',thunk['kind'])
            scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,
                (original,18,True),[],LABEL+'.GetValue')
            getter_entry=base+thunk['targetMethod'][3]
            getter=pointer.owned(image,getter_entry)
            original_getter=mm['get___instance']
            need('own-named-getter',image.method_pointer_va(original_getter),getter_entry)
            scalar.owned_method_abi(image,ctx,original_getter.index,wrapper.type_definition,
                (original,18,True),[],LABEL+'.cachedGetter')
            get_program=holders.rolling_holder(getter['regions'],getter_entry,cast=0,barrier=0,cached=True,same=True)
            get_thunk=get_value([(base+thunk['entryMethod'][3],bytes.fromhex(thunk['instructionHex']))],
                base+thunk['entryMethod'][3],getter=getter_entry)
            hook=pointer.owned(image,symbols['prehook'])
            scalar.owned_method_abi(image,ctx,mm['OnDeserialized'].index,wrapper.type_definition,
                ('void',1,False),[],LABEL+'.prehook')
            hook_program=holders.rolling_owned_prehook(hook['regions'],hook['pointer'],{},cached=True)
            factories=[]
            for name in('.ctor','CreateInstance'):
                method=mm[name];source=pointer.owned(image,image.method_pointer_va(method))
                scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[],LABEL+'.factory')
                program=factory_program(source['regions'],source['pointer'],barrier,ctor=name=='.ctor')
                need('same-zero-allocator',allocate,program['allocationTarget'])
                usage=derive_typed_usage_context(image,program['allocation']['site']-base,label=LABEL)
                need('zero-original-allocation',(1,original),(usage['tag'],usage['typeName']))
                for declared in program['classUsages']:
                    typed=derive_typed_usage_context(image,declared['site']-base,label=LABEL)
                    need('zero-original-cast',(1,original),(typed['tag'],typed['typeName']))
                setters=[];owner=wrapper.name
                for _ in range(32):
                    if owner in(None,'object','System.Object'):break
                    for candidate in md.methods_for(ctx.index.types[owner]):
                        if md.string(candidate.name_index)=='set___instance'and image.method_pointer_va(candidate)==program['instanceSetter']:
                            setters.append(candidate)
                    owner=ctx.parent(owner)
                need('one-owned-holder-setter',1,len(setters));setter=setters[0]
                stored=pointer.owned(image,program['instanceSetter'])
                store_program=dual_holder(stored['regions'],stored['pointer'],barrier)
                cast=pointer.owned(image,program['strictCast'])
                predicates=[target for index,site,target in _calls(cast)
                    if bytes.fromhex(cast['rows'][index-1]['bytes'])==b'\x48\x8b\x09']
                need('one-owned-strict-cast-predicate',1,len(predicates));predicate=predicates[0]
                cast_program=holders.rolling_owned_strict_cast(cast['regions'],cast['pointer'],predicate)
                factories.append(dict(method=[method.index,wrapper.name,name,source['pointer']-base],
                    sourceWindows=source['windows'],program=program,originalAllocation=usage,
                    holderSetter=dict(method=[setter.index,image.type_name(setter.declaring_type),'set___instance',stored['pointer']-base],
                        windows=stored['windows'],program=store_program),
                    strictCast=dict(windows=cast['windows'],program=cast_program)))
            components.append(dict(family=family,tag=route['tag'],wrapperName=wrapper.name,wrappedType=original,
                memberCount=0,wrapperNullAdmitted=True,holder=holder,
                concreteFormatter=dict(method=[formatter_method.index,formatter_name,'Deserialize',forward_source['pointer']-base],
                    windows=forward_source['windows'],program=forward_program),
                originalRegistrationRequiredByThisCaller=False,
                readerWindows=body['windows'],programs=programs,header=header_proof,barrier=barrier_proof,
                coherentCachedGetter=dict(windows=getter['windows'],program=get_program,thunk=get_thunk,entryProof=thunk,entryWindows=getter_windows),
                coherentPrehook=dict(windows=hook['windows'],program=hook_program),factories=factories))
    if requested is not None:need('complete-explicit-zero-wrapper-scope',requested,{r['wrapperName']for r in components})
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(status='validated-zero-components',nativeInputs=pins,
        switches=switches,components=components,unionTransfersAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Complete current initialized zero-header/FF/new-wrapper programs, one-byte header source or inlined four-field cursor updates, exact original/cache/factory stores, and own concrete generated metadata slot5/forwarder into the same reader. ReadPackable<ConcreteWrapper> has no concrete Original adapter-registration dependency.',
            conditional='Matching concrete generated callbacks, initialized coherent typed contexts, normal compatible allocations/casts/helpers, collector disabled, existing nonnull coherent cache/base pointers or proved factories, buffered nonwrapping disjoint storage. Runtime provider/default choice unobserved.',
            unresolved=['union tag/typed generic caller transfer composition','base Original adapter/conversion join','nonzero selectors','live runtime selection','refill/malformed paths','whole enclosing owners']))))
