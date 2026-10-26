"""Own the nominal three-reference BlackboardVector3 and concrete lifecycle.

The three stored children are independently proved BlackboardDouble records.
Managed Vector3 naming never supplies twelve raw bytes. The existing wire
declaration, current complete concrete caller, own getter/factory/reference
adapter and every actual nominal child request are joined on one image.
Runtime evaluation and provider/default selection remain unobserved.
"""
import json
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

from scripts.game_data.memorypack.skill_root_child_bindings import need,bind_read_value,reference_reader_abi

TYPE='Beyond.Blackboard+BlackboardVector3'
CHILD='Beyond.Blackboard+BlackboardDouble'
CAPABILITY='skill-blackboard-vector3'
DECLARATIONS=tuple((name,CHILD,'reference')for name in('x','y','z'))


def reader_program(regions,entry,offsets,*,new=False,null=False,formatter=False):
    need('vector-literal-reader-path',True,all(type(value)is bool for value in(new,null,formatter)))
    g=BytesPath(regions,entry);calls=[];usages=[];allocation=None;collectors=[]
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408'if formatter else'48895c2410','48896c2418','4889742420','57','4883ec20');ready=flag(g)
    formatter_class=None
    if formatter:
        g.take('498bf8','488bda');g.branch('75',True,1)
        at=g.at;cell=g.relative('488b0d');formatter_class=dict(instruction=at,cell=cell)
        g.take('83b9e000000000');g.branch('75',True,1);flag(g);g.branch('75',True,1)
    else:g.take('488bfa','488bd9');g.branch('75',True,1)
    g.take('837b'+rem+'01');g.branch('7d',True,1)
    g.take('488b43'+cur,'0fb628','8b73'+rem,'83ee01');g.branch('79',True,1)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'8973'+rem,'4080fdff');g.branch('0f84',null)
    if null:
        g.take('488bcf','48c70700000000');barrier=g.relative('e8')
    else:
        barrier=None;g.take('48833f00');g.branch('75',not new,1)
        if new:
            at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8');g.take('488bf0','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');constructor=g.relative('e8');g.take('488bcf','488937');barrier=g.relative('e8')
            allocation=dict(instruction=at,cell=cell,allocate=allocate,constructor=constructor)
        g.take('4080fd03');g.branch('0f85',False)
        bitmap=None
        for index,name in enumerate(('x','y','z')):
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell,fieldName=name))
            g.take('488bcb','488b37'if index<2 else'488b3f');call=g.at;target=g.relative('e8')
            calls.append(dict(fieldName=name,instruction=call,target=target))
            g.take('4885f6'if index<2 else'4885ff');g.branch('0f84',False)
            g.take('4c8b4610'if index<2 else'4c8b4710','4d85c0');g.branch('0f84',False)
            collectors.append(flag(g,'833d'))
            if not index:bitmap=g.relative('488d2d')
            g.take('498940'+bytes((16+8*index,)).hex());g.branch('74',True,1)
        if bytes(g.bytes.get(g.at+i,0)for i in range(1))==b'\xeb':g.jump('eb',1)
        need('same-vector-disabled-collector',1,len(set(collectors)))
    g.take('488b5c2430'if formatter else'488b5c2438','488b6c2440','488b742448','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,newWrapper=new,ff=null,memberCount=None if null else 3,
        metadataReadyFlag=ready,wrapperAllocation=allocation,childUsages=usages,childCalls=calls,
        formatter=formatter,formatterClassUsage=formatter_class,
        barrierTarget=barrier,disabledCollector=collectors[0]if collectors else None,
        ownHolderOffset=16,childReferenceOffsets=[16,24,32],normalReturn=True,entryRspRestored=True,
        directWireBytes=1,childGrammarsAdmitted=False)


def wrapper_constructor_program(regions,entry):
    """Complete inline vector+three Double allocations under disabled collector."""
    g=BytesPath(regions,entry);classes=[];allocations=[];collectors=[]
    def usage():
        at=g.at;cell=g.relative('488b0d');classes.append(dict(instruction=at,cell=cell))
    def allocate():usage();allocations.append(g.relative('e8'))
    g.take('4053','56','4883ec28');ready=flag(g);g.take('488bf1');g.branch('75',True,1)
    allocate();g.take('488bd8','4885c0');g.branch('0f84',False)
    usage();g.take('48897c2448');allocations.append(g.relative('e8'));g.take('488bf8','4885c0');g.branch('0f84',False)
    usage();g.take('48896c2440','4c89742420','83b9e000000000');g.branch('75',True,1)
    g.take('4533f6','48897b10');collectors.append(g.relative('443935'));bitmap=g.relative('488d2d')
    g.take('44897714');g.branch('74',True,1)
    for index in(1,2):
        allocate();g.take('488bf8','4885c0');g.branch('0f84',False)
        usage();g.take('4439b1e0000000');g.branch('75',True,1)
        if index==1:
            collectors.append(g.relative('443935'));g.take('44897714','48897b18');g.branch('74',True,1)
        else:
            collectors.append(g.relative('8b05'));g.take('44897714','48897b20','85c0');g.branch('74',True,1)
    for index in range(3):
        g.take('488b4b'+bytes((16+8*index,)).hex(),'4885c9');g.branch('74'if index==2 else'0f84',False,1 if index==2 else 4)
        g.take('44897114')
    g.take('48895e10','85c0');g.branch('74',True,1)
    g.take('488b6c2440','4c8b742420','488b7c2448','4883c428','5e','5b','c3')
    need('one-vector-typed-allocator',1,len(set(allocations)));need('same-vector-constructor-disabled-collector',1,len(set(collectors)))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,classUsages=classes,allocate=allocations[0],
        disabledCollector=collectors[0],bitmap=bitmap,vectorChildOffsets=[16,24,32],childSingleValueOffset=20,
        freshTypedVectorAndThreeDoubleObjects=True,threeSingleDefaultsZero=True,
        wrapperHolderOffset=16,normalReturn=True,entryRspRestored=True,wireBytes=0)


def original_constructor_program(regions,entry):
    """Own .ctor(float,float,float), including saved SIMD arguments and return."""
    g=BytesPath(regions,entry);classes=[];allocations=[];collectors=[]
    def usage():
        at=g.at;cell=g.relative('488b0d');classes.append(dict(instruction=at,cell=cell))
    g.take('48895c2418','57','4883ec50','0f29742440','488bd9');usage()
    g.take('0f28f3','0f297c2430','0f28fa','440f29442420','440f28c1');allocations.append(g.relative('e8'))
    g.take('488bf8','4885c0');g.branch('0f84',False);usage();g.take('4889742468','83b9e000000000');g.branch('75',True,1)
    collectors.append(flag(g,'833d'));bitmap=g.relative('488d35');g.take('c7471400000000','48897b10');g.branch('74',True,1)
    for index in(1,2):
        usage();allocations.append(g.relative('e8'));g.take('488bf8','4885c0');g.branch('0f84',False)
        usage();g.take('83b9e000000000');g.branch('75',True,1)
        collectors.append(flag(g,'833d'));g.take('c7471400000000','48897b'+bytes((16+8*index,)).hex());g.branch('74',True,1)
    g.take('488b4310','4885c0');g.branch('74',False,1);g.take('f3440f114014','488b4318','4885c0');g.branch('74',False,1)
    g.take('f30f117814','488b4320','4885c0');g.branch('74',False,1)
    g.take('488b742468','488b5c2470','0f287c2430','440f28442420','f30f117014','0f28742440','4883c450','5f','c3')
    need('same-original-vector-allocator',1,len(set(allocations)));need('same-original-vector-disabled-collector',1,len(set(collectors)))
    return dict(selectedBytes=g.seen,classUsages=classes,allocate=allocations[0],disabledCollector=collectors[0],bitmap=bitmap,
        incomingSinglesStoredUnchanged=['xmm1 via xmm8','xmm2 via xmm7','xmm3 via xmm6'],
        restoredSimdNonvolatiles=['xmm6','xmm7','xmm8'],normalReturn=True,entryRspRestored=True,wireBytes=0)


def factory_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec30');ready=flag(g);g.take('488bf9');g.branch('75',True,1)
    at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8');g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('0f57db','48c744242000000000','0f57d2','0f57c9','488bcb');constructor=g.relative('e8')
    g.take('488d4f10','48895f10','488b5c2440','4883c430','5f');barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,originalClassUsage=dict(instruction=at,cell=cell),
        allocate=allocate,constructor=constructor,zeroSingleArguments=['xmm1','xmm2','xmm3'],
        zeroUnusedMethodInfoArgument=True,holderOffset=16,barrier=barrier,normalReturnViaBarrier=True,entryRspRestored=True,wireBytes=0)


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack import skill_blackboard_double_sources,buff_blackboard_vector3_native as warm
    _publication_gate(image,pins)
    reviewed=json.loads(warm.CONTRACT_PATH.read_bytes());need('vector-native-inputs',pins,reviewed['nativeInputs'])
    actual=warm.derive(image,pins,reviewed);need('same-current-vector-wire-declaration',reviewed,actual)
    need('exact-vector-wire-fields',dict(nullHeader=255,memberCount=3,
        members=[dict(name=name,kind='blackboard-double')for name in('x','y','z')]),actual['wireLayout'])
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('actual-vector-reference-fields',[(name,CHILD)for name in('x','y','z')],[(m.name,m.declared_type)for m in wrapper.members])
    need('own-wrapper-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
    for index,name in enumerate(('x','y','z')):need('own-vector-field:'+name,(TYPE,CHILD,16+8*index),ctx.field(TYPE+'::'+name))
    mm=methods(image,wrapper);bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in('.ctor','CreateInstance','Deserialize')}
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    for name in('.ctor','CreateInstance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,False)if name=='GetValue'else('void',1,False),[], 'blackboardVector3.'+name)
    constructor=wrapper_constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'])
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'])
    om,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='.ctor'
        and [ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['float']*3]
    scalar.owned_method_abi(image,ctx,om.index,om.declaring_type,('void',1,False),[('float',12,False)]*3,'blackboardVector3.originalConstructor')
    need('actual-named-float3-constructor',image.method_pointer_va(om),factory['constructor'])
    bodies['originalConstructor']=owned(image,factory['constructor']);original=original_constructor_program(bodies['originalConstructor']['regions'],bodies['originalConstructor']['pointer'])
    need('same-owned-vector-allocator',constructor['allocate'],factory['allocate']);need('same-owned-child-allocator',constructor['allocate'],original['allocate'])
    programs=[reader_program(bodies['Deserialize']['regions'],bodies['Deserialize']['pointer'],actual['proof']['readerOffsets'],**path)
        for path in({},{'new':True},{'null':True})]
    need('actual-wrapper-constructor',bodies['.ctor']['pointer'],programs[1]['wrapperAllocation']['constructor'])
    need('same-selected-wrapper-allocator',constructor['allocate'],programs[1]['wrapperAllocation']['allocate'])
    barrier_windows,barrier_proof,_=_fast_barrier(image,factory['barrier'])
    for program in programs:
        if program['barrierTarget']is not None:need('same-vector-barrier',factory['barrier'],program['barrierTarget'])
    for program in(constructor,original,*programs[:2]):need('same-actual-vector-disabled-collector',base+barrier_proof['disabledFlagRva'],program['disabledCollector'])
    double=skill_blackboard_double_sources.derive(image,pins);typed=[]
    def class_usage(usage,typename):
        row=derive_typed_usage_context(image,usage['instruction']-base,label='blackboardVector3.class')
        need('exact-vector-owned-class',(1,typename),(row['tag'],row['typeName']));typed.append(row)
    bbbase=skill_blackboard_double_sources.BASE
    for usage,name in zip(constructor['classUsages'],(TYPE,CHILD,bbbase,CHILD,bbbase,CHILD,bbbase),strict=True):class_usage(usage,name)
    for usage,name in zip(original['classUsages'],(CHILD,bbbase)*3,strict=True):class_usage(usage,name)
    class_usage(factory['originalClassUsage'],TYPE);class_usage(programs[1]['wrapperAllocation'],wrapper.name)
    bindings=[]
    for usage,call in zip(programs[0]['childUsages'],programs[0]['childCalls'],strict=True):
        request=derive_typed_usage_context(image,usage['instruction']-base,label='blackboardVector3.child')
        bindings.append(bind_read_value(pins,dict(fieldName=call['fieldName'],typeName=CHILD,typedRequest=request,
            sourceTargetRva=call['target']-base),double,'skill-blackboard-double'))
    need('same-positive-vector-child-calls',programs[0]['childCalls'],programs[1]['childCalls'])
    pair=derive_pair(image,TYPE,wrapper.name)
    def prove_formatter(selected,selected_pair,selected_wrapper):
        need('same-selected-vector-formatter',(TYPE,wrapper.name),(selected_wrapper.wrapped_type,selected_wrapper.name))
        method=selected_pair['composition']['methods'][1];body=owned(selected,base+method[3])
        paths=[reader_program(body['regions'],body['pointer'],actual['proof']['readerOffsets'],formatter=True,**path)
            for path in({},{'new':True},{'null':True})]
        child_bindings=[]
        for program in paths:
            class_usage(program['formatterClassUsage'],wrapper.name)
            if program['wrapperAllocation']:
                class_usage(program['wrapperAllocation'],wrapper.name)
                need('same-formatter-wrapper-constructor',bodies['.ctor']['pointer'],program['wrapperAllocation']['constructor'])
                need('same-formatter-allocator',constructor['allocate'],program['wrapperAllocation']['allocate'])
            if program['barrierTarget']is not None:need('same-formatter-barrier',factory['barrier'],program['barrierTarget'])
            if program['disabledCollector']is not None:need('same-formatter-disabled-collector',base+barrier_proof['disabledFlagRva'],program['disabledCollector'])
            for usage,call in zip(program['childUsages'],program['childCalls'],strict=True):
                request=derive_typed_usage_context(selected,usage['instruction']-base,label='blackboardVector3.formatterChild')
                child_bindings.append(bind_read_value(pins,dict(fieldName=call['fieldName'],typeName=CHILD,typedRequest=request,
                    sourceTargetRva=call['target']-base),double,'skill-blackboard-double'))
        return dict(kind='complete-inline-BlackboardVector3-formatter',method=method,sourceWindows=body['windows'],
            programs=paths,childBindings=child_bindings,directStaticReaderCallExecuted=False,
            pointerEqualityToStaticReaderProved=False,ownNominalGrammarProved=True)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_formatter)
    need('same-own-vector-getter',getter['entryRva'],adapter['getterMethod'][3])
    abi=reference_reader_abi(image,pins)
    for key in('referenceReaderMethodDefinition','referenceReaderTargetRva'):
        need('same-selected-vector-reader:'+key,actual[key],abi[key])
    cap=dict(typeName=TYPE,wrapperName=wrapper.name,memberCount=3,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        orderedReads=[dict(fieldName=name,kind='record',childCapability='skill-blackboard-double')for name in('x','y','z')],
        **{key:abi[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        fixedWireBytes=None,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-vector3-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-vector3',capabilities={CAPABILITY:cap},
        proof=dict(warm=actual,readerPrograms=programs,constructor=constructor,originalConstructor=original,factory=factory,
            getter=getter,pair=pair,adapter=adapter,referenceAbi=abi,blackboardDouble=double,childBindings=bindings,
            sourceWindows={name:body['windows']for name,body in bodies.items()},typedClassUsages=typed,
            barrierWindows=barrier_windows,barrierProof=barrier_proof),
        evidenceBoundary=dict(exact='Current complete own MC3/new/FF concrete reader, holder/getter/factory/reference adapter and three actual typed child calls, each joined to concrete BlackboardDouble grammar and lifecycle.',
            conditional=__doc__+' Ready nominal callbacks, coherent contexts, normal helper effects and typed allocation, disabled collector and buffered disjoint storage.',
            structuralOnly='Stored vector blackboard configuration.',unresolved=['runtime evaluation/provider selection','enclosing owners/physical EOF']))))
