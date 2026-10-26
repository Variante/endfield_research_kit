"""Own BlackboardVector2 MC2/FF source and its two BlackboardDouble children.

The two stored references have variable wire sizes. No managed Vector2 width
or BlackboardVector3 source supplies their grammar. Own constructors, typed
allocations, complete source-to-setter transfers and reference adapter must
join on one selected image. Ready contexts, normal helpers, disabled collector
and buffered disjoint storage remain conditions; runtime evaluation is open.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need,bind_read_value,reference_reader_abi

TYPE='Beyond.Blackboard+BlackboardVector2'
CHILD='Beyond.Blackboard+BlackboardDouble'
CAPABILITY='skill-blackboard-vector2'


def factory_program(regions,entry,*,wrapper_constructor=False):
    need('literal-vector2-constructor-path',True,type(wrapper_constructor)is bool)
    g=BytesPath(regions,entry)
    g.take('48895c2408','57','4883ec20');ready=flag(g);g.take('488bf9')
    g.branch('74'if wrapper_constructor else'75',not wrapper_constructor,1)
    at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8')
    g.take('488bd8','4885c0');g.branch('74'if wrapper_constructor else'75',not wrapper_constructor,1)
    g.take('4533c9','0f57d2','0f57c9','488bc8'if wrapper_constructor else'488bcb')
    constructor=g.relative('e8')
    g.take('488d4f10','48895f10','488b5c2430','4883c420','5f');barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,originalClassUsage=dict(instruction=at,cell=cell),
        allocate=allocate,constructor=constructor,zeroSingleArguments=['xmm1','xmm2'],zeroMethodInfoArgument=True,
        holderOffset=16,normalReturnViaBarrier=True,entryRspRestored=True,barrier=barrier,wireBytes=0)


def original_constructor_program(regions,entry):
    g=BytesPath(regions,entry);classes=[];allocations=[];barriers=[]
    def usage():
        at=g.at;cell=g.relative('488b0d');classes.append(dict(instruction=at,cell=cell))
    g.take('48895c2408','4889742410','57','4883ec40','0f29742430','488bd9');usage()
    g.take('0f28f2','0f297c2420','0f28f9');allocations.append(g.relative('e8'))
    g.take('488bf8','4885c0');g.branch('0f84',False);usage();g.take('83b9e000000000');g.branch('0f84',False)
    g.take('33f6','48897b10','488d4b10','897714');barriers.append(g.relative('e8'))
    usage();allocations.append(g.relative('e8'));g.take('488bf8','4885c0');g.branch('74',False,1)
    usage();g.take('39b1e0000000');g.branch('74',False,1)
    g.take('897714','488d4b18','48897b18');barriers.append(g.relative('e8'))
    g.take('4c8b4b10','4d85c9');g.branch('74',False,1)
    g.take('f3410f117914','488b4318','4885c0');g.branch('74',False,1)
    g.take('488b5c2450','488b742458','0f287c2420','f30f117014','0f28742430','4883c440','5f','c3')
    need('one-vector2-child-allocator',1,len(set(allocations)));need('one-vector2-child-barrier',1,len(set(barriers)))
    return dict(selectedBytes=g.seen,classUsages=classes,allocate=allocations[0],barrier=barriers[0],
        incomingSinglesStoredUnchanged=['xmm1 via xmm7','xmm2 via xmm6'],restoredSimdNonvolatiles=['xmm6','xmm7'],
        twoFreshTypedDoubleChildren=True,zeroedSingleOffsets=[20,20],childReferenceOffsets=[16,24],
        normalReturn=True,entryRspRestored=True,wireBytes=0)


def reader_program(regions,entry,offsets,*,new=False,null=False):
    need('literal-vector2-reader-path',True,type(new)is bool and type(null)is bool)
    g=BytesPath(regions,entry);calls=[];usages=[];setters=[];allocation=None;barrier=None
    cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb630','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080feff');g.branch('74',null,1)
    if null:
        g.take('488bcf','48c70700000000');barrier=g.relative('e8');g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');allocate=g.relative('e8');g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');constructor=g.relative('e8');g.take('488bcf','48892f');barrier=g.relative('e8');g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell,allocate=allocate,constructor=constructor)
        g.take('4080fe02');g.branch('0f85',False)
        for index,name in enumerate(('x','y')):
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell,fieldName=name))
            g.take('488bcb','488b37'if index==0 else'488b3f');at=g.at;target=g.relative('e8')
            calls.append(dict(fieldName=name,instruction=at,target=target))
            g.take('4885f6'if index==0 else'4885ff');g.branch('74',False,1)
            g.take('4533c0','488bd0','488bce'if index==0 else'488bcf');at=g.at;target=g.relative('e8')
            setters.append(dict(fieldName=name,instruction=at,target=target,unchangedReferenceResult=True))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,ff=null,
        memberCount=None if null else 2,childUsages=usages,childCalls=calls,setterCalls=setters,
        wrapperAllocation=allocation,barrierTarget=barrier,directWireBytes=1,
        childGrammarsAdmitted=False,normalReturn=True,entryRspRestored=True)


def setter_program(regions,entry,*,field):
    need('finite-vector2-field-slot',True,type(field)is int and field in(16,24))
    g=BytesPath(regions,entry);slot=bytes((field,)).hex()
    g.take('4883ec28','488b4910','4885c9');g.branch('74',False,1)
    g.take('488951'+slot,'4883c1'+slot,'4883c428');barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,originalHolderOffset=16,fieldOffset=field,
        incomingReferenceStoredUnchanged=True,normalReturnViaBarrier=True,entryRspRestored=True,barrier=barrier,wireBytes=0)


def formatter_program(regions,entry):
    """Own exact ready generated forwarder with restored Win64 frame."""
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('498bd8','488bfa');g.branch('74',False,1)
    at=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('4533c0','488bd3','488bcf','488b5c2430','4883c420','5f');target=g.relative('e9')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,wrapperClassUsage=dict(instruction=at,cell=cell),
        target=target,readerArgument='RDX preserved RDI to RCX',outputArgument='R8 preserved RBX to RDX',
        methodInfoZeroed=True,normalReturnViaStaticReader=True,entryRspRestored=True)


def derive_wrapper(image,pins):
    """Fresh concrete wrapper source; deliberately grants no ordinary adapter."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack import skill_blackboard_double_sources,scalar_param_native as scalar
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.wrapped_type==TYPE]
    need('exact-vector2-generated-fields',[(name,CHILD)for name in('x','y')],[(m.name,m.declared_type)for m in wrapper.members])
    need('own-vector2-wrapper-holder',(wrapper.name,TYPE,16),ctx.field(wrapper.name+'::__instance'))
    for index,name in enumerate(('x','y')):need('own-vector2-field:'+name,(TYPE,CHILD,16+8*index),ctx.field(TYPE+'::'+name))
    mm=methods(image,wrapper);bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in('.ctor','CreateInstance','Deserialize')}
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
    for name in('.ctor','CreateInstance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (TYPE,18,True)if name=='GetValue'else('void',1,False),[],'blackboardVector2.'+name)
    constructor=factory_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],wrapper_constructor=True)
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'])
    need('same-vector2-allocator',constructor['allocate'],factory['allocate'])
    need('same-vector2-float-constructor',constructor['constructor'],factory['constructor'])
    need('same-vector2-barrier',constructor['barrier'],factory['barrier'])
    original_method,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)=='.ctor'
        and [ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['float']*2]
    scalar.owned_method_abi(image,ctx,original_method.index,original_method.declaring_type,('void',1,False),
        [('float',12,False)]*2,'blackboardVector2.originalConstructor')
    need('actual-named-vector2-float2-constructor',image.method_pointer_va(original_method),factory['constructor'])
    bodies['originalConstructor']=owned(image,factory['constructor'])
    original=original_constructor_program(bodies['originalConstructor']['regions'],factory['constructor'])
    need('same-vector2-child-allocator',factory['allocate'],original['allocate'])
    need('same-vector2-child-barrier',factory['barrier'],original['barrier'])
    offsets=scalar.reader_offsets(image,'blackboardVector2')
    programs=[reader_program(bodies['Deserialize']['regions'],bodies['Deserialize']['pointer'],offsets,**path)
        for path in({},{'new':True},{'null':True})]
    need('own-vector2-constructor-target',bodies['.ctor']['pointer'],programs[1]['wrapperAllocation']['constructor'])
    need('same-vector2-new-allocator',factory['allocate'],programs[1]['wrapperAllocation']['allocate'])
    for program in programs:
        if program['barrierTarget']is not None:need('same-vector2-reader-barrier',factory['barrier'],program['barrierTarget'])
    typed=[]
    def class_usage(usage,typename):
        row=derive_typed_usage_context(image,usage['instruction']-base,label='blackboardVector2.class')
        need('exact-vector2-owned-class',(1,typename),(row['tag'],row['typeName']));typed.append(row)
    class_usage(constructor['originalClassUsage'],TYPE);class_usage(factory['originalClassUsage'],TYPE)
    class_usage(programs[1]['wrapperAllocation'],wrapper.name)
    for usage,name in zip(original['classUsages'],(CHILD,skill_blackboard_double_sources.BASE)*2,strict=True):class_usage(usage,name)
    child=skill_blackboard_double_sources.derive(image,pins);bindings=[];setters=[]
    for index,(member,usage,call,setter_call)in enumerate(zip(wrapper.members,programs[0]['childUsages'],programs[0]['childCalls'],programs[0]['setterCalls'],strict=True)):
        request=derive_typed_usage_context(image,usage['instruction']-base,label='blackboardVector2.child')
        bindings.append(bind_read_value(pins,dict(fieldName=member.name,typeName=CHILD,typedRequest=request,
            sourceTargetRva=call['target']-base),child,'skill-blackboard-double'))
        method=md.methods[member.method_index];pointer=image.method_pointer_va(method)
        scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(CHILD,18,True)],'blackboardVector2.setter')
        need('actual-named-vector2-setter',pointer,setter_call['target']);body=owned(image,pointer)
        proof=setter_program(body['regions'],pointer,field=16+8*index)
        need('same-vector2-setter-barrier',factory['barrier'],proof['barrier'])
        setters.append(dict(method=[method.index,wrapper.name,md.string(method.name_index),pointer-base],program=proof,sourceWindows=body['windows']))
    for key in('childCalls','setterCalls'):need('same-vector2-positive-paths:'+key,programs[0][key],programs[1][key])
    formatter_name=wrapper.name+'+'+wrapper.name.rsplit('.',1)[-1]+'Formatter'
    formatter_method,=[m for m in md.methods_for(image.named_types[formatter_name])if md.string(m.name_index)=='Deserialize']
    body=owned(image,image.method_pointer_va(formatter_method));forwarder=formatter_program(body['regions'],body['pointer'])
    need('own-vector2-static-formatter-tail',bodies['Deserialize']['pointer'],forwarder['target'])
    class_usage(forwarder['wrapperClassUsage'],wrapper.name)
    barrier_windows,barrier_proof,_=_fast_barrier(image,factory['barrier']);_publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-vector2-wrapper-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-vector2-wrapper',typeName=TYPE,wrapperName=wrapper.name,
        memberCount=2,ordinaryOriginalReadValueAdmitted=False,wholeSkillDataAdmitted=False,
        proof=dict(readerOffsets=offsets,readerPrograms=programs,constructor=constructor,factory=factory,
            originalConstructor=original,getter=getter,setters=setters,childBindings=bindings,blackboardDouble=child,
            formatter=dict(method=[formatter_method.index,formatter_name,'Deserialize',body['pointer']-base],program=forwarder,sourceWindows=body['windows']),
            sourceWindows={name:body['windows']for name,body in bodies.items()},typedClassUsages=typed,
            barrierWindows=barrier_windows,barrierProof=barrier_proof),
        evidenceBoundary=dict(exact='Complete own current MC2/new/FF wrapper caller, exact named setter transfers, own holder16/getter/float2 factory, typed constructors and two independently complete Double children.',
            conditional=__doc__,structuralOnly='Stored vector blackboard configuration.',
            unresolved=['ordinary Original formatter registration/adapter','runtime evaluation/provider selection','enclosing owners/physical EOF']))))


def derive(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    wrapper_source=derive_wrapper(image,pins);base=image.pe.image_base
    wrapper,=[w for w in image.memorypack_wrappers.values()if w.name==wrapper_source['wrapperName']]
    pair=derive_pair(image,TYPE,wrapper.name)
    def prove_forwarder(selected,selected_pair,selected_wrapper):
        from scripts.game_data.memorypack.pointer_param import owned,methods
        method=selected_pair['composition']['methods'][1];body=owned(selected,base+method[3])
        proof=formatter_program(body['regions'],body['pointer'])
        need('same-fresh-static-reader',selected.method_pointer_va(methods(selected,selected_wrapper)['Deserialize']),proof['target'])
        return dict(method=method,program=proof,sourceWindows=body['windows'],directStaticReaderTailExecuted=True)
    adapter=derive_adapter(image,pins,pair,wrapper,forwarder_prover=prove_forwarder)
    need('same-own-vector2-getter',wrapper_source['proof']['getter']['entryRva'],adapter['getterMethod'][3])
    abi=reference_reader_abi(image,pins)
    cap=dict(typeName=TYPE,wrapperName=wrapper.name,memberCount=2,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        orderedReads=[dict(fieldName=name,kind='record',childCapability='skill-blackboard-double')for name in('x','y')],
        **{key:abi[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        ownConcreteGetterSemanticsProved=True,ownConcreteFactorySemanticsProved=True,
        fixedWireBytes=None,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-blackboard-vector2-sources.v1',nativeInputs=pins,
        status='validated-conditional-blackboard-vector2',capabilities={CAPABILITY:cap},
        proof=dict(wrapper=wrapper_source,pair=pair,adapter=adapter,referenceAbi=abi,
            blackboardDouble=wrapper_source['proof']['blackboardDouble']),
        evidenceBoundary=dict(exact='Own complete current MC2/new/FF wrapper source, two Double children, holder/getter/factory/setters, actual alternative eager registration and canonical ordinary reference adapter.',
            conditional=__doc__+' Exact inline adapter constructor base slot12 and System.Type/provider classes initialized; matching live canonical callbacks/contexts remain conditions.',
            structuralOnly='Stored vector blackboard configuration.',unresolved=['runtime evaluation/provider selection','enclosing owners/physical EOF']))))
