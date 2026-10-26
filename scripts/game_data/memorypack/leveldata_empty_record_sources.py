"""Current LevelData container records with independently closed empty children.

The record sources and reference adapters are complete selected paths. Only
null/empty child lists are admitted here; positive elements remain separate.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

PLANS={
    'Beyond.Gameplay.LevelFactoryPredefineData':('powerGates',),
    'Beyond.Gameplay.LevelFunctionAreaData':('baseData','functionAreaConditions','ranges','specificDatas'),
    'Beyond.Gameplay.LevelSafeZoneData':('boxes',),
}
PARENTS={'factoryPredefineData':'Beyond.Gameplay.LevelFactoryPredefineData',
    'functionArea':'Beyond.Gameplay.LevelFunctionAreaData','safeZone':'Beyond.Gameplay.LevelSafeZoneData'}


def record_program(regions,entry,fields,o,s,*,null=False,new=False):
    """Prove the exact buffered source, owned stores and whole normal frame."""
    if type(null)is not bool or type(new)is not bool or len(fields)not in(1,4):
        raise ValueError('leveldataEmptyRecord.closed-literal-profile')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('leveldataEmptyRecord.reader-layout')
    if any(type(f['offset'])is not int or not 16<=f['offset']<128 for f in fields):
        raise ValueError('leveldataEmptyRecord.owned-field-offsets')
    one=len(fields)==1;g=BytesPath(regions,entry);reads=[];allocation=None
    peek=lambda n=2:bytes(g.bytes.get(g.at+i,0)for i in range(n)).hex()
    def edge(taken):
        if peek()=='0f84':g.branch('0f84',taken)
        else:g.branch('74',taken,1)
    def tail():
        g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
        if g.relative('e9')!=s['barrier']:raise ValueError('leveldataEmptyRecord.tail-barrier')
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    ready=flag(g);g.take('488bf2'if one else'488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb638'if one else'0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080ffff'if one else'4080feff');edge(null)
    if null:
        g.take('48c70600000000'if one else'48c70700000000','488bce'if one else'488bcf');g.jump('eb',1)
    else:
        g.take('48833e00'if one else'48833f00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
            g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bce'if one else'488bcf','48892e'if one else'48892f')
            g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take(('4080ff'if one else'4080fe')+bytes((len(fields),)).hex());g.branch('0f85',False)
        for index,field in enumerate(fields):
            final=index==len(fields)-1;setup=[];context=None
            expected={'488b15','488bcb','488b3e'if one else'488b3f'if final else'488b37'}
            while peek(3)in expected:
                prefix=peek(3)
                if prefix=='488b15':
                    if context is not None:raise ValueError('leveldataEmptyRecord.duplicate-context')
                    context=dict(instruction=g.at,cell=g.relative(prefix))
                else:g.take(prefix)
                setup.append(prefix)
            if len(setup)!=3 or set(setup)!=expected or context is None:
                raise ValueError('leveldataEmptyRecord.same-reader-holder-context')
            call=g.at;g.call(s['reference'])
            g.take('4885ff'if final else'4885f6');edge(False)
            g.take('488b4f10'if final else'488b4e10','4885c9');edge(False)
            slot=bytes((field['offset'],)).hex();g.take('488941'+slot,'4883c1'+slot)
            reads.append(dict(fieldName=field['name'],sourceCall=call,sourceTarget=s['reference'],
                typedUsage=context,storeOffset=field['offset']))
            if not final:g.call(s['barrier'])
    tail()
    return dict(selectedBytes=g.seen,initializedFlag=ready,headerBytes=1,
        serializedMemberCount=None if null else len(fields),nullWireBytes=1,
        null=null,newWrapper=None if null else new,typedAllocation=allocation,
        orderedReads=reads,normalTailReturn=True,entryFrameRestored=True,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,leveldata):
    """Reprove all nominal records, actual parents and each empty list source."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.levelscript_ulong_dictionary_sources import brief_constructor_program
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata;build=Build(image,pins)
    need=lambda k,e,a:scalar.need('leveldataEmptyRecord',k,e,a)
    need('same-LevelData-pins',pins,leveldata['nativeInputs']);records={};parents=[]
    offsets=scalar.reader_offsets(image,'leveldataEmptyRecord')
    for original,names in PLANS.items():
        wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==original]
        need('nominal-reference',False,ctx.is_value_type(original))
        need('ordered-members',list(names),[m.name for m in wrapper.members])
        need('wrapper-holder',(wrapper.name,original,16),ctx.field(wrapper.name+'::__instance'))
        fields=[]
        for member in wrapper.members:
            declaring=build.wrappers[member.declaring_wrapper].wrapped_type
            owner,declared,slot=ctx.field(declaring+'::'+member.name)
            need('exact-declared-field',member.declared_type,declared)
            need('reference-list-member',True,declared.startswith('System.Collections.Generic.List`1<')and declared.endswith('>'))
            fields.append(dict(name=member.name,typeName=declared,offset=slot))
        mm=methods(image,wrapper);body=owned(image,image.method_pointer_va(mm['Deserialize']))
        ctor=owned(image,image.method_pointer_va(mm['.ctor']))
        barrier=next(control_transfer(r)['target']for r in body['rows']
            if r['text'].startswith('jmp ')and int(r['va'],16)<body['pointer']+0x160)
        reference=_body_target(body,'mov rcx, rbx')
        build.prove_reader_clone_target(reference,'MemoryPack.MemoryPackReader.ReadPackable',result_abi='reference')
        symbols=dict(reference=reference,constructor=ctor['pointer'],barrier=barrier,
            allocate=_body_target(ctor,'mov rbx, rax',before=True),
            originalConstructor=_body_target(ctor,'mov rcx, rax'))
        constructor=brief_constructor_program(ctor['regions'],ctor['pointer'],symbols)
        programs=[record_program(body['regions'],body['pointer'],fields,offsets,symbols,**kw)
            for kw in(dict(null=True),dict(new=True),dict(new=False))]
        allocations=[]
        for label,allocation,type_name in(('wrapper',programs[1]['typedAllocation'],wrapper.name),
                ('original',constructor['typedAllocation'],original)):
            usage=derive_typed_usage_context(image,allocation['instruction']-base,label='leveldataEmptyRecord.'+label)
            need('typed-allocation:'+label,(1,type_name),(usage['tag'],usage['typeName']));allocations.append(usage)
        original_ctor,=[m for m in md.methods_for(ctx.index.types[original])
            if md.string(m.name_index)=='.ctor'and not m.parameter_count and image.method_pointer_va(m)==symbols['originalConstructor']]
        scalar.owned_method_abi(image,ctx,original_ctor.index,original_ctor.declaring_type,('void',1,False),[],
            'leveldataEmptyRecord.original-constructor')
        pair=derive_pair(image,original);adapter=derive_adapter(image,pins,pair,wrapper)
        getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
        lists=[]
        for field,read in zip(fields,programs[-1]['orderedReads'],strict=True):
            usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataEmptyRecord.list')
            child_type=field['typeName'][len('System.Collections.Generic.List`1<'):-1]
            component=derive_reference_list_component(image,pins,typed_request=usage,
                call_target=read['sourceTarget'],element_type=child_type,count_limit=0)
            lists.append(dict(field=field,source=read,typedRequest=usage,component=component,
                counts=[-1,0],elementGrammarAdmitted=False))
        barrier_source,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
        records[original]=dict(wrapperName=wrapper.name,fields=fields,
            method=[mm['Deserialize'].index,wrapper.name,'Deserialize',body['pointer']-base],
            sourceWindows=body['windows'],programs=programs,profile=pair,adapter=adapter,
            constructor=constructor,constructorWindows=ctor['windows'],getter=getter,typedAllocations=allocations,
            childLists=lists,barrier=dict(source=barrier_source,proof=barrier_proof),
            capability=dict(typeName=original,memberCount=len(fields),headerBytes=1,nullWireBytes=1,
                childListCounts=[-1,0],positiveChildElementsAdmitted=False,wholeOwnerAdmitted=False))
    for field,read in zip(leveldata['fields'],leveldata['program']['orderedReads'],strict=True):
        if field['name']not in PARENTS:continue
        need('exact-current-parent-type',PARENTS[field['name']],field['typeName'])
        usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='leveldataEmptyRecord.parent')
        bind_typed_read(image,usage,method_name='ReadValue',argument=field['typeName'],kind=18,reference=True)
        build.prove_reader_clone_target(read['sourceTarget'],'MemoryPack.MemoryPackReader.ReadValue',result_abi='reference')
        parents.append(dict(field=field,source=read,typedRequest=usage))
    need('all-three-parent-joins',set(PARENTS),{p['field']['name']for p in parents})
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,parents=parents,
        wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
