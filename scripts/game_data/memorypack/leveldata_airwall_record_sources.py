"""Current AirWallGroup/AirWallCheckData complete buffered reference sources.

Every nested reference/list is an explicit child obligation. The programs do
not admit Mission checks, geometry, collection elements or runtime activation.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

GROUP='Beyond.Gameplay.AirWallGroup'
CHECK='Beyond.Gameplay.AirWallCheckData'
PLANS={
 GROUP:(('bounds','Beyond.Gameplay.ThreeDimRange','ReadValue'),
  ('checkData',CHECK,'ReadValue'),('defaultOn','bool','bool'),('groupId','ulong','uint64'),
  ('polyLineWalls','System.Collections.Generic.List`1<Beyond.Gameplay.PolyLineWall>','ReadPackable'),
  ('pushBackRadioId','string','pool'),('scriptId','ulong','uint64'),('slotId','uint','uint32')),
 CHECK:(('checkType','int','int32'),('missionData','Beyond.Gameplay.MissionTotalCheckData','ReadValue')),
}


def record_program(regions,entry,original,fields,o,s,*,null=False,new=False):
    if original not in PLANS or type(null)is not bool or type(new)is not bool:
        raise ValueError('airwallRecord.closed-profile')
    if [(f['name'],f['typeName'],f['kind'])for f in fields]!=list(PLANS[original]):
        raise ValueError('airwallRecord.nominal-plan')
    if o!={'currentPtr':80,'bufferLength':48,'advancedCount':64,'consumed':68}:
        raise ValueError('airwallRecord.reader-layout')
    if any(type(f['offset'])is not int or not 16<=f['offset']<128 for f in fields):
        raise ValueError('airwallRecord.owned-field-offset')
    g=BytesPath(regions,entry);reads=[];allocation=None;final_ref=original==CHECK
    peek=lambda n=2:bytes(g.bytes.get(g.at+i,0)for i in range(n)).hex()
    def edge(taken):
        if peek()=='0f84':g.branch('0f84',taken)
        else:g.branch('74',taken,1)
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    ready=flag(g);g.take('488bfa','488bd9');g.branch('0f84',False)
    g.take('837b3001');g.branch('0f8c',False)
    g.take('488b4350','0fb630','8b6b30','83ed01');g.branch('0f88',False)
    g.take('48ff4350','ff4340','ff4344','896b30','4080feff');edge(null)
    if null:
        if final_ref:g.take('48c70700000000','488bcf');g.jump('eb',1)
        else:g.take('488bcf','48c70700000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('48833f00');g.branch('0f84',new)
        if new:
            allocation=dict(instruction=g.at,cell=g.relative('488b0d'))
            g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bcf','48892f');g.call(s['barrier']);g.take('90');g.jump('e9')
        g.take('4080fe'+bytes((len(fields),)).hex());g.branch('0f85',False)
        for index,field in enumerate(fields):
            final=index==len(fields)-1;kind=field['kind'];reference=kind in('ReadValue','ReadPackable','pool')
            expected={'488bcb','488b3f'if final else'488b37'}
            if kind in('ReadValue','ReadPackable'):expected.add('488b15')
            setup=[];context=None
            while peek(3)in expected:
                prefix=peek(3)
                if prefix=='488b15':
                    if context is not None:raise ValueError('airwallRecord.duplicate-context')
                    context=dict(instruction=g.at,cell=g.relative(prefix))
                else:g.take(prefix)
                setup.append(prefix)
            if len(setup)!=len(expected)or set(setup)!=expected:
                raise ValueError('airwallRecord.same-reader-holder-context')
            call=g.at;g.call(s[kind]);g.take('4885ff'if final else'4885f6');edge(False)
            g.take('488b4f10'if final else'488b4e10','4885c9');edge(False)
            slot=bytes((field['offset'],)).hex()
            g.take(('488941'if reference or kind=='uint64'else'8841'if kind=='bool'else'8941')+slot)
            if reference:
                g.take('4883c1'+slot)
                if not final:g.call(s['barrier'])
            reads.append(dict(fieldName=field['name'],kind=kind,sourceCall=call,
                sourceTarget=s[kind],typedUsage=context,storeOffset=field['offset']))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f')
    if final_ref:
        if g.relative('e9')!=s['barrier']:raise ValueError('airwallRecord.tail-barrier')
    else:g.take('c3')
    return dict(selectedBytes=g.seen,initializedFlag=ready,null=null,newWrapper=None if null else new,
        typedAllocation=allocation,headerBytes=1,memberCount=None if null else len(fields),
        nullWireBytes=1,orderedReads=reads,normalReturn=True,entryFrameRestored=True,
        childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def derive(image,pins,leveldata):
    """Own closed record/caller/collection sources without granting children."""
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.levelscript_family_regenerate import Build
    from scripts.game_data.memorypack import scalar_param_native as scalar,pooled_source_helper
    from scripts.game_data.memorypack.pointer_param import owned,methods,leaf
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    from scripts.game_data.memorypack.levelscript_param_graph_sources import _body_target
    from scripts.game_data.memorypack.levelscript_spawner_sources import constructor_program
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_cost_data_list_sources import derive_reference_list_component
    from scripts.game_data.memorypack.levelscript_collection_sources import reference_list_induction
    base=image.pe.image_base;ctx=NativeReferenceContext(image);build=Build(image,pins)
    need=lambda k,e,a:scalar.need('airwallRecord',k,e,a)
    need('same-current-LevelData-pins',pins,leveldata['nativeInputs'])
    offsets=scalar.reader_offsets(image,'airwallRecord');records={};primitives={}
    for original,plan in PLANS.items():
        wrapper,=[w for w in build.wrappers.values()if w.wrapped_type==original]
        need('members',[(n,t)for n,t,_ in plan],[(m.name,m.declared_type)for m in wrapper.members])
        need('reference-original',False,ctx.is_value_type(original))
        need('owned-wrapper-holder',(wrapper.name,original,16),ctx.field(wrapper.name+'::__instance'))
        fields=[dict(name=n,typeName=t,kind=k,offset=ctx.field(original+'::'+n)[2])for n,t,k in plan]
        need('nominal-fields',[(original,t)for _,t,_ in plan],[ctx.field(original+'::'+n)[:2]for n,_,_ in plan])
        mm=methods(image,wrapper);body=owned(image,image.method_pointer_va(mm['Deserialize']))
        ctor=owned(image,image.method_pointer_va(mm['.ctor']))
        symbols=dict(constructor=ctor['pointer'],allocate=_body_target(ctor,'test rax, rax',before=True),
            barrier=next(control_transfer(r)['target']for r in ctor['rows']if control_transfer(r)['kind']=='jump'))
        for field in fields:
            slot=hex(field['offset']);kind=field['kind']
            instruction='mov [rcx+'+slot+'], '+('rax'if kind in('ReadValue','ReadPackable','pool','uint64')else'al'if kind=='bool'else'eax')
            target=_body_target(body,instruction,before=True)
            if kind in symbols:need('one-target-per-source-role',symbols[kind],target)
            symbols[kind]=target
        programs=[record_program(body['regions'],body['pointer'],original,fields,offsets,symbols,**kw)
            for kw in(dict(null=True),dict(new=True),dict(new=False))]
        constructor=constructor_program(ctor['regions'],ctor['pointer'],symbols)
        allocations=[]
        for role,allocation,type_name in(('wrapper',programs[1]['typedAllocation'],wrapper.name),
                ('original',constructor['typedAllocation'],original)):
            usage=derive_typed_usage_context(image,allocation['instruction']-base,label='airwallRecord.'+role)
            need('typed-allocation:'+role,(1,type_name),(usage['tag'],usage['typeName']));allocations.append(usage)
        pair=derive_pair(image,original);adapter=derive_adapter(image,pins,pair,wrapper)
        getter=leaf(image,image.method_pointer_va(mm['GetValue']),['488B4110','C3'])
        children=[]
        for field,read in zip(fields,programs[-1]['orderedReads'],strict=True):
            if field['kind']in('ReadValue','ReadPackable'):
                usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='airwallRecord.child')
                kind=21 if field['kind']=='ReadPackable'else 18
                bind_typed_read(image,usage,method_name=field['kind'],argument=field['typeName'],kind=kind,reference=True)
                build.prove_reader_clone_target(read['sourceTarget'],'MemoryPack.MemoryPackReader.'+field['kind'],result_abi='reference')
                children.append(dict(field=field,source=read,typedRequest=usage))
            elif field['kind']=='pool':
                primitives['pool']=pooled_source_helper.validate_on_image(image,read['sourceTarget'],pins)
            else:
                native=vector_recorder(image)(read['sourceTarget']-base)
                checked=scalar.boolean_source(image,native,offsets,'airwallRecord.bool')if field['kind']=='bool'else scalar.integer_source(
                    image,native,offsets,'airwallRecord.'+field['kind'],width=8 if field['kind']=='uint64'else 4)
                primitives[field['kind']]=dict(source=native,proof=checked)
        barrier,checked,_=_fast_barrier(image,symbols['barrier'])
        records[original]=dict(wrapperName=wrapper.name,fields=fields,
            method=[mm['Deserialize'].index,wrapper.name,'Deserialize',body['pointer']-base],
            sourceWindows=body['windows'],programs=programs,constructor=constructor,
            constructorWindows=ctor['windows'],typedAllocations=allocations,getter=getter,
            profile=pair,adapter=adapter,children=children,
            barrier=dict(source=barrier,proof=checked),symbolRvas={k:v-base for k,v in symbols.items()})
    parents=[];collection_sources=[]
    for owner,fields,reads in(('Beyond.Gameplay.LevelData',leveldata['fields'],leveldata['program']['orderedReads']),
            (GROUP,records[GROUP]['fields'],records[GROUP]['programs'][-1]['orderedReads'])):
        for field,read in zip(fields,reads,strict=True):
            if field['name']not in('airWalls','polyLineWalls'):continue
            element=GROUP if field['name']=='airWalls'else'Beyond.Gameplay.PolyLineWall'
            usage=derive_typed_usage_context(image,read['typedUsage']['instruction']-base,label='airwallRecord.listParent')
            component=derive_reference_list_component(image,pins,typed_request=usage,call_target=read['sourceTarget'],element_type=element,count_limit=2)
            body=owned(image,component['entry']['pointer'])
            total=ctx.field('MemoryPack.MemoryPackReader::totalLength')[2]-16
            induction=reference_list_induction(body['regions'],body['pointer'],dict(offsets,totalLength=total),
                {k:base+v for k,v in component['symbols'].items()})
            parents.append(dict(owner=owner,field=field,source=read,typedRequest=usage))
            collection_sources.append(dict(typeName=field['typeName'],component=component,positiveCountInduction=induction,
                countLimit=4096,elementGrammarAdmitted=False))
    need('both-distinct-list-parents',{'airWalls','polyLineWalls'},{p['field']['name']for p in parents})
    return json.loads(json.dumps(dict(nativeInputs=pins,records=records,primitiveSources=primitives,
        parents=parents,collections=collection_sources,wholeOwnerAdmitted=False,liveFormatterSelectionObserved=False)))
