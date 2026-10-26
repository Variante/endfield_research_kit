"""Exact Impact/SuperArmor dropdown Int32 blackboard descendants.

These two nominal Originals inherit the actual BlackboardCustomWithDropdownIntValue
and BlackboardInt chain, ending at the selected int/int generic base. Their
MC4 source is pooled key4, normalized bool1, Int32 value4, custom-value bool1.
The wrapper's original holder16, inherited cache24, dropdown cache32 and own
cache40 are distinct. Fresh construction writes holder16 and cache40; the
dropdown setter independently refreshes cache32 before its bool32 field store.
No stale inherited cache is equated with the new original. The base int/int
field/constructor source is freshly composed rather than resolving a constructed
name through an unrelated TypeDef. Matching normal canonical callbacks,
initialized coherent compatible originals, typed zeroed allocation, disabled
collector and disjoint buffered storage remain conditions. Evaluation, live
provider selection, cold/refill/error paths and enclosing owners are unresolved.
"""
import hashlib
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPES={
    'Beyond.Gameplay.Core.BlackboardImpactValue':'skill-blackboard-impact-value',
    'Beyond.Gameplay.Core.BlackboardSuperArmorValue':'skill-blackboard-super-armor-value',
}
DROPDOWN='Beyond.Blackboard+BlackboardCustomWithDropdownIntValue'
DROPDOWN_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardCustomWithDropdownIntValueForMemoryPack'
BASE='Beyond.Blackboard+BlackboardParamBase`2<int,int>'
BASE_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardParamBase_int_int_ForMemoryPack'
INT='Beyond.Blackboard+BlackboardInt'
INT_WRAPPER='Beyond.MemoryPack.Beyond_Blackboard_BlackboardIntForMemoryPack'
ORDER=(('blackboardKey','pooled-string','byte-payload'),('useBlackboardKey','bool',None),
    ('value','int32',None),('useCustomValue','bool',None))


def base_constructor_program(regions,entry,target):
    """Actual dropdown wrapper constructor restores its frame then tails base."""
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1)
    at=g.at;cell=g.relative('488b0d');g.take('83b9e000000000');g.branch('74',False,1)
    g.take('33d2','488bcb','4883c420','5b')
    need('dropdown-named-base-constructor-tail',target,g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,baseClassUsage=dict(instruction=at,cell=cell),
        exactBaseConstructorTargetVa=target,sameReceiverRcx=True,normalReturnViaBase=True,entryRspRestored=True)


def constructor_program(regions,entry,s):
    """Own cache40 construction, retaining distinct inherited caches."""
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('0f84',False);at=g.at;cell=g.relative('488b0d')
    g.take('83b9e000000000');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['baseConstructor'])
    alloc_at=g.at;alloc_cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bf8','4885c0');g.branch('0f84',False)
    g.take('4533c0','33d2','488bc8');g.call(s['originalIntConstructor'])
    g.take('4533c0','488bd7','488bcb');g.call(s['instanceSetter'])
    g.take('488b7b10');first=g.at;concrete=g.relative('488b15');g.take('488bcf');g.call(s['strictCast'])
    g.take('48894328','488bcf');second=g.at;need('dropdown-same-constructor-class',concrete,g.relative('488b15'));g.call(s['strictCast'])
    g.take('488d4b28','488b5c2430','4883c420','5f')
    need('dropdown-constructor-disabled-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,baseClassUsage=dict(instruction=at,cell=cell),
        allocationUsage=dict(instruction=alloc_at,cell=alloc_cell),
        concreteClassUsages=[dict(instruction=first,cell=concrete),dict(instruction=second,cell=concrete)],
        originalConstructorInt32Argument=0,originalHolderOffset=16,typedCacheOffset=40,
        ownCacheAndBaseHolderReceiveSameOriginal=True,inheritedCachesEquated=False,
        normalReturnViaBarrier=True,entryRspRestored=True)


def factory_program(regions,entry,s):
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20');ready=flag(g)
    g.take('488bf9');g.branch('75',True,1);at=g.at;cell=g.relative('488b0d');g.call(s['allocate'])
    g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('4533c0','33d2','488bcb');g.call(s['originalIntConstructor'])
    g.take('4533c0','488bd3','488bcf');g.call(s['instanceSetter'])
    g.take('488b5f10');first=g.at;concrete=g.relative('488b15');g.take('488bcb');g.call(s['strictCast'])
    g.take('48894728','488bcb');second=g.at;need('dropdown-same-factory-class',concrete,g.relative('488b15'));g.call(s['strictCast'])
    g.take('488d4f28','488b5c2430','4883c420','5f');need('dropdown-factory-disabled-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,allocationUsage=dict(instruction=at,cell=cell),
        concreteClassUsages=[dict(instruction=first,cell=concrete),dict(instruction=second,cell=concrete)],
        originalConstructorInt32Argument=0,originalHolderOffset=16,typedCacheOffset=40,
        ownCacheAndBaseHolderReceiveSameOriginal=True,inheritedCachesEquated=False,
        normalReturnViaBarrier=True,entryRspRestored=True)


def instance_setter_program(regions,entry,barrier):
    g=BytesPath(regions,entry);g.take('4883ec28','4c8bd1','48895128','4883c128','4c8bca');g.call(barrier)
    g.take('498d4a10','4d894a10','4883c428');need('dropdown-setter-same-barrier',barrier,g.relative('e9'))
    return dict(selectedBytes=g.seen,originalHolderOffset=16,typedCacheOffset=40,
        wholeIncomingRdxStoredUnchanged=True,requiredPreservedAcrossDisabledBarrier=['r9','r10'],
        normalReturnViaBarrier=True,entryRspRestored=True,inheritedCachesEquated=False)


def dropdown_getter_program(regions,entry,predicate,barrier,*,cache='coherent',original_null=False,compatible=True):
    """Own actual inverse cache32 branch and inline class predicate paths."""
    need('dropdown-cache32-path',True,cache in('coherent','empty','stale')
        and type(original_null)is bool and type(compatible)is bool and not(cache=='coherent'and original_null))
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1);g.take('48837b2000');g.branch('0f85',cache!='empty')
    if cache!='empty':
        g.take('488b4310','48394320');g.branch('0f84',cache=='coherent')
        if cache=='stale':g.jump('e9')
    usages=[]
    if cache!='coherent':
        g.take('48897c2430','488b7b10','4885ff');g.branch('74',original_null,1)
        if original_null:
            g.take('33c0','48894320');g.jump('eb',1)
        else:
            at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
            g.take('488b0f');g.call(predicate);g.take('84c0');g.branch('74',not compatible,1)
            if compatible:g.take('488bc7')
            else:g.take('33c0');g.jump('eb',1)
            g.take('48894320');at=g.at;again=g.relative('488b15');usages.append(dict(instruction=at,cell=again))
            need('dropdown-cache32-same-class-cell',cell,again);g.take('488b0f');g.call(predicate)
        g.take('488d4b20');g.call(barrier);g.take('488b7c2430')
    g.take('488b4320','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheState=cache,originalNull=original_null,
        compatible=compatible,originalHolderOffset=16,typedCacheOffset=32,concreteClassUsages=usages,
        returnedReference='same nonnull original'if cache=='coherent'or not original_null and compatible else'null',
        entryRspRestored=True,normalReturn=True,wireBytes=0)


def own_getter_program(regions,entry,cast,barrier,*,cache='coherent'):
    """Exact cache40 nullable-cast refresh, independent of the cache32 shape."""
    need('dropdown-cache40-path',True,cache in('coherent','empty','stale'))
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1);g.take('48837b2800');g.branch('0f84',cache=='empty')
    if cache!='empty':g.take('488b4310','48394328');g.branch('0f85',cache=='stale')
    usages=[]
    if cache!='coherent':
        at=g.at;cell=g.relative('488b15');usages.append(dict(instruction=at,cell=cell))
        g.take('48897c2430','488b7b10','488bcf');g.call(cast);g.take('48894328','488bcf')
        at=g.at;again=g.relative('488b15');usages.append(dict(instruction=at,cell=again))
        need('dropdown-cache40-same-class-cell',cell,again);g.call(cast)
        g.take('488d4b28');g.call(barrier);g.take('488b7c2430');g.jump('e9')
    g.take('488b4328','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,cacheState=cache,originalHolderOffset=16,
        typedCacheOffset=40,concreteClassUsages=usages,returnedReference='same compatible nullable original',
        entryRspRestored=True,normalReturn=True,wireBytes=0)


def prehook_program(regions,entry):
    """Actual initialized nonnull own-cache prehook, before any header read."""
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g)
    g.take('488bd9');g.branch('74',False,1);g.take('48837b2800');g.branch('0f84',False)
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,ownNonNullCacheRequired=True,
        typedCacheOffset=40,originalHolderUnchanged=True,noReaderArgument=True,serializedFieldWrites=0,
        entryRspRestored=True,normalReturn=True,wireBytes=0)


def _closed_setters(image,pins,wrapper,wrappers,base_source,barrier,cache):
    """Exact selected generic fields, using the freshly proved same closed base."""
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import generated_member_sources as members,scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    need('dropdown-closed-int-base',BASE,base_source['proof']['closedBase']['name'])
    slots=base_source['proof']['warm']['proof']['typedStores']['fieldOffsets']
    need('dropdown-int-base-source-slots',dict(blackboardKey=24,useBlackboardKey=16,value=20),slots)
    proofs=[]
    for member,(name,kind,_)in zip(wrapper.members,ORDER,strict=True):
        need('dropdown-exact-ordered-member',name,member.name)
        if name=='useCustomValue':
            from scripts.game_data.memorypack.skill_root_buff_input_sources import getter_setter_program
            from scripts.game_data.memorypack.pointer_param import methods
            from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
            need('dropdown-own-bool-field',(DROPDOWN,'bool',32),ctx.field(DROPDOWN+'::useCustomValue'))
            need('dropdown-own-bool-setter-owner',DROPDOWN_WRAPPER,member.declaring_wrapper)
            mm=methods(image,wrappers[DROPDOWN_WRAPPER]);method=md.methods[member.method_index]
            scalar.owned_method_abi(image,ctx,method.index,wrappers[DROPDOWN_WRAPPER].type_definition,
                ('void',1,False),[('bool',2,False)],'dropdown.useCustomValueSetter')
            getter=mm['get___instance'];scalar.owned_method_abi(image,ctx,getter.index,wrappers[DROPDOWN_WRAPPER].type_definition,
                (DROPDOWN,18,True),[],'dropdown.cache32Getter')
            getter_body=members._body(image,image.method_pointer_va(getter));body=members._body(image,image.method_pointer_va(method))
            predicate=base+base_source['proof']['sourceWindows']['assignable'][0]['startRva']
            programs=[dropdown_getter_program(getter_body['regions'],getter_body['pointer'],predicate,base+barrier,**path)
                for path in({},dict(cache='empty'),dict(cache='stale'),dict(cache='empty',original_null=True),dict(cache='empty',compatible=False))]
            typed=[]
            for program in programs:
                for site in program['concreteClassUsages']:
                    usage=derive_typed_usage_context(image,site['instruction']-base,label='dropdown.cache32Class')
                    need('dropdown-exact-cache32-class',(1,DROPDOWN),(usage['tag'],usage['typeName']));typed.append(usage)
            getter_proof=dict(method=[getter.index,DROPDOWN_WRAPPER,'get___instance',getter_body['pointer']-base],
                family=getter_body['family'],codeWindows=getter_body['windows'],programs=programs,typedClassUsages=typed,
                baseHolder=(BASE_WRAPPER,BASE,16),typedCache=(DROPDOWN_WRAPPER,DROPDOWN,32),refreshAdmitted=True,
                coherentNonNullSamePointerReturn=True,ownedClassPredicate=base_source['proof']['classPredicate'])
            program=getter_setter_program(body['regions'],body['pointer'],dict(getter=getter_body['pointer']),kind='bool',field_offset=32)
            proof=dict(method=[method.index,DROPDOWN_WRAPPER,md.string(method.name_index),body['pointer']-base],member=member.row(),
                targetField=DROPDOWN+'::useCustomValue',fieldOffset=32,storedBytes=1,profile='cached-getter-setter',getter=getter_proof,
                sourceFamily=body['family'],codeWindows=body['windows'],program=program,
                incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False)
            proofs.append(proof);continue
        need('dropdown-actual-generic-setter-owner',BASE_WRAPPER,member.declaring_wrapper)
        typename,raw_kind,width,mode={'blackboardKey':('string',14,8,'reference-return'),
            'useBlackboardKey':('bool',2,1,'normalized-byte-return'),'value':('int',8,4,'int32-return')}[name]
        need('dropdown-actual-closed-member-type',typename,member.declared_type)
        method=md.methods[member.method_index]
        scalar.owned_method_abi(image,ctx,method.index,wrappers[BASE_WRAPPER].type_definition,
            ('void',1,False),[(typename,raw_kind,raw_kind==14)],'dropdown.closedSetter')
        body=members._body(image,image.method_pointer_va(method))
        program=members.base_setter_program(body['rows'],holder=16,field=slots[name],mode=mode,barrier=base+barrier)
        parameter,=md.parameters_for(method)
        proofs.append(dict(method=[method.index,BASE_WRAPPER,md.string(method.name_index),body['pointer']-base],member=member.row(),
            targetField=BASE+'::'+name,fieldOffset=slots[name],storedBytes=width,profile='direct-base-holder-setter',getter=None,
            sourceFamily=body['family'],codeWindows=body['windows'],program=program,
            parameterTypeRecordHex=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16).hex().upper(),
            exactClosedBaseFieldSource=base_source['proof']['warm']['proof']['typedStores'],
            selectedClosedValueParameter=base_source['proof']['baseValueParameter']if name=='value'else None,
            incomingValueStoredUnchanged=True,childGrammarAdmitted=False,factoryAdmitted=False))
    return proofs


def _derive_one(image,pins,type_name,base_source,targets,barrier,disabled_flag):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import generated_action_sources as actions,generated_member_sources as members
    from scripts.game_data.memorypack import generated_header_sources as headers,generated_reader_sources as readers,generated_lifecycle_sources as lifecycle
    from scripts.game_data.memorypack import buff_ec_profiles_native as ec,scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    wrappers={w.name:w for w in image.memorypack_wrappers.values()};wrapper,=[w for w in wrappers.values()if w.wrapped_type==type_name]
    need('dropdown-exact-current-original-parent',DROPDOWN,ctx.parent(type_name))
    need('dropdown-exact-original-parent-chain',(INT,BASE),(ctx.parent(DROPDOWN),ctx.parent(INT)))
    need('dropdown-exact-wrapper-chain',(DROPDOWN_WRAPPER,INT_WRAPPER,BASE_WRAPPER),
        (ctx.parent(wrapper.name),ctx.parent(DROPDOWN_WRAPPER),ctx.parent(INT_WRAPPER)))
    need('dropdown-original-has-no-own-instance-fields',[],[f.index for f in md.fields_for(ctx.index.types[type_name])
        if not ctx.field_attributes(f.type_index)&16])
    need('dropdown-owned-custom-bool',(DROPDOWN,'bool',32),ctx.field(DROPDOWN+'::useCustomValue'))
    for owner,field,typename,offset in((wrapper.name,'__realInstance',type_name,40),
            (DROPDOWN_WRAPPER,'__realInstance',DROPDOWN,32),(INT_WRAPPER,'__realInstance',INT,24),(BASE_WRAPPER,'___instance',BASE,16)):
        need('dropdown-distinct-owned-holder',(owner,typename,offset),ctx.field(owner+'::'+field))
        fd,=[f for f in md.fields_for(ctx.index.types[owner])if md.string(f.name_index)==field]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),21 if owner==BASE_WRAPPER else 18,'dropdown.'+field,reference=True)
    fd,=[f for f in md.fields_for(ctx.index.types[DROPDOWN])if md.string(f.name_index)=='useCustomValue']
    scalar.ordinary(image,ctx.type_pointer(fd.type_index),2,'dropdown.useCustomValue')
    mm=methods(image,wrapper);entry=image.method_pointer_va(mm['Deserialize'])
    family,windows,rows=ec.family(image,entry-base)
    body=dict(pointer=entry,family=family,windows=windows,rows=rows,
        regions=[(base+w['startRva'],image.window_bytes(w))for w in windows])
    need('dropdown-complete-owned-reader-instruction-partition',False,any(r['text'].startswith('db ')for r in body['rows']))
    primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    for name in('.ctor','CreateInstance','OnDeserialized','get___instance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,
            (type_name,18,True)if name in('GetValue','get___instance')else('void',1,False),[],'dropdown.'+name)
    scalar.owned_method_abi(image,ctx,mm['set___instance'].index,wrapper.type_definition,
        ('void',1,False),[(type_name,18,True)],'dropdown.instanceSetter')
    cache={};fields=_closed_setters(image,pins,wrapper,wrappers,base_source,barrier,cache)
    claim,enums=actions._claim(image,wrapper);need('dropdown-MC4-count',4,len(claim['members']))
    offsets=ec.source_offsets(image)
    header,start=headers.derive(image,body['rows'],body['pointer'],4,offsets,barrier,disabled_flag=disabled_flag)
    reader=header['readerRegister'];path,choices=ec.fast_path(body['rows'],start,reader,offsets,terminal_target=base+barrier)
    contexts,skipped=actions._contexts(image,body['rows']);actual_targets=dict(targets)
    actual_targets['_memberPrimitive']=actions._primitive_sources(image,claim,path,reader,actual_targets,offsets,contexts=contexts,pins=pins)
    events,requirements=actions._events(image,claim,path,contexts,reader,actual_targets)
    need('dropdown-exact-source-return-order',['byte-payload','byte','scalar32','byte'],[r['kind']for r in events])
    transfers=members.call_transfers(body['rows'],events,[base+p['method'][3]for p in fields],base,
        normal_path=path,reader=reader,output=header['outputRegister'],setter_proofs=fields,barrier=base+barrier)
    call_sites={base+event['instruction'][0]for event in events}
    for transfer in transfers:
        call_sites.update(base+site[0]for site in transfer.get('actualCalls',[transfer['setterCall']]if 'setterCall'in transfer else[]))
    need('dropdown-complete-normal-source-setter-call-set',call_sites,
        {ec.va(row)for row in path if control_transfer(row)['kind']in('call','indirectCall','registerCall')})
    scope=dict(schema='endfield.generated-action-source-scope.v1',nativeInputs=pins,wrapperName=wrapper.name,wrappedType=type_name,
        memberCount=4,method=[mm['Deserialize'].index,wrapper.name,'Deserialize',body['pointer']-base],
        family=body['family'],codeWindows=body['windows'],headerProof=header,events=events,childRequirements=requirements,
        primitiveSources={str(i):p for i,p in actual_targets['_memberPrimitive'].items()},setterTransfers=transfers,
        selectedProgram=[ec.site(r,base)for r in path],sourceScopeAdmitted=True,wholeWrapperAdmitted=False,positiveGrammarAdmitted=False)
    bodies={name:owned(image,image.method_pointer_va(mm[name]))for name in('.ctor','CreateInstance','set___instance','get___instance','OnDeserialized')}
    coherent=members._coherent_getter(image,ctx,wrapper,mm['get___instance'],cache,barrier=base+barrier)
    need('dropdown-own-getter-cache',40,coherent['typedCache'][2])
    cast=base+base_source['proof']['sourceWindows']['cast'][0]['startRva']
    own_getters=[own_getter_program(bodies['get___instance']['regions'],bodies['get___instance']['pointer'],cast,base+barrier,cache=state)
        for state in('coherent','empty','stale')]
    strict,={control_transfer(row)['target']for i,row in enumerate(bodies['CreateInstance']['rows'][:-1])
        if ec.raw(row)[:1]==b'\xe8'and bodies['CreateInstance']['rows'][i+1]['text']=='mov [rdi+0x28], rax'}
    symbols=dict(barrier=base+barrier,strictCast=strict,instanceSetter=bodies['set___instance']['pointer'],
        allocate=base_source['proof']['constructor']['allocate'],originalIntConstructor=base_source['proof']['factory']['originalConstructor'])
    need('dropdown-same-independent-strict-cast',base_source['proof']['sourceWindows']['strictCast'][0]['startRva'],strict-base)
    need('dropdown-disabled-barrier-preserves-instance-registers',True,base_source['proof']['selectedDisabledBarrierPreservesR9R10']is True
        and base_source['proof']['barrierWindows']['codeWindows'][0]['startRva']==barrier)
    base_mm=methods(image,wrappers[DROPDOWN_WRAPPER]);base_body=owned(image,image.method_pointer_va(base_mm['.ctor']))
    int_ctor=image.method_pointer_va(methods(image,wrappers[INT_WRAPPER])['.ctor'])
    base_constructor=base_constructor_program(base_body['regions'],base_body['pointer'],int_ctor)
    symbols['baseConstructor']=base_body['pointer']
    constructor=constructor_program(bodies['.ctor']['regions'],bodies['.ctor']['pointer'],symbols)
    factory=factory_program(bodies['CreateInstance']['regions'],bodies['CreateInstance']['pointer'],symbols)
    setter=instance_setter_program(bodies['set___instance']['regions'],bodies['set___instance']['pointer'],base+barrier)
    hook=prehook_program(bodies['OnDeserialized']['regions'],bodies['OnDeserialized']['pointer'])
    typed=[]
    def usage(site,typename):
        actual=derive_typed_usage_context(image,site['instruction']-base,label='dropdown.class')
        need('dropdown-exact-typed-class',(1,typename),(actual['tag'],actual['typeName']));typed.append(actual)
    usage(base_constructor['baseClassUsage'],INT_WRAPPER);usage(constructor['baseClassUsage'],DROPDOWN_WRAPPER)
    for p in(constructor,factory):
        usage(p['allocationUsage'],type_name)
        for site in p['concreteClassUsages']:usage(site,type_name)
    for program in own_getters:
        for site in program['concreteClassUsages']:usage(site,type_name)
    positive=readers.positive_program(body['rows'],scope,base);programs=[]
    for existing,ff in((False,False),(True,False),(False,True),(True,True)):
        selected=readers.prefix_program(body['rows'],body['pointer'],header,base=base,prehook=bodies['OnDeserialized']['pointer'],
            constructor=bodies['.ctor']['pointer'],allocate=symbols['allocate'],barrier=base+barrier,existing=existing,ff=ff)
        full=selected.pop('selectedRows')+([]if ff else positive)
        frame=readers.frame_program(full,header_local=header.get('headerLocalDisplacement'),base=base,tail_barrier=base+barrier if ff else None)
        programs.append(dict(**selected,frame=frame,selectedProgram=[ec.site(r,base)for r in full]))
    pair=derive_pair(image,type_name,wrapper.name);adapter=derive_adapter(image,pins,pair,wrapper)
    pointer=image.method_pointer_va(mm['GetValue']);raw=image.pe.bytes_at_va(pointer,7)
    need('dropdown-own-GetValue-thunk',b'\x33\xd2\xe9',raw[:3])
    need('dropdown-own-GetValue-target',bodies['get___instance']['pointer'],pointer+7+int.from_bytes(raw[3:],'little',signed=True))
    need('dropdown-same-adapter-owned-getter',pointer-base,adapter['getterMethod'][3])
    need('dropdown-same-adapter-owned-reader',scope['method'],adapter['pairForwarder']['readerMethod'])
    reader_abi=reference_reader_abi(image,pins);bw,bp,_=_fast_barrier(image,base+barrier)
    cap=dict(typeName=type_name,wrapperName=wrapper.name,memberCount=4,nullable=True,nullMarker=255,nullAdmitted=True,
        wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,ownConcreteGetterSemanticsProved=True,
        ownConcreteFactorySemanticsProved=True,orderedReads=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in ORDER],
        positiveWireBytes=11,nullWireBytes=1,**{k:reader_abi[k]for k in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    return dict(capability=cap,proof=dict(baseSource=base_source,scope=scope,setters=fields,programs=programs,
        coherentGetter=coherent,ownGetterPrograms=own_getters,constructor=constructor,factory=factory,instanceSetter=setter,prehook=hook,
        baseConstructor=base_constructor,baseConstructorWindows=base_body['windows'],sourceWindows={k:v['windows']for k,v in bodies.items()},
        typedClassUsages=typed,pair=pair,adapter=adapter,referenceReaders=reader_abi,barrierWindows=bw,barrierProof=bp,
        getterEntryWindow=dict(startRva=pointer-base,endRva=pointer-base+7,sha256=hashlib.sha256(raw).hexdigest().upper(),
            boundary='exact seven-byte owned GetValue tail; named getter body independently proved')))


def derive(image,pins,*,type_names=None):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.memorypack.skill_blackboard_int_sources import derive as base_source
    from scripts.game_data.memorypack.generated_action_sources import _prepare
    _publication_gate(image,pins);names=sorted(TYPES)if type_names is None else list(type_names)
    need('dropdown-finite-distinct-types',True,0<len(names)<=2 and len(names)==len(set(names))and set(names)<=set(TYPES))
    actual=base_source(image,pins);targets,barrier,disabled=_prepare(image,pins)
    records={name:_derive_one(image,pins,name,actual,targets,barrier,disabled)for name in names}
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-dropdown-blackboard-sources.v1',status='validated-conditional-dropdown-blackboards',
        nativeInputs=pins,capabilities={TYPES[n]:r['capability']for n,r in records.items()},requiredExternalCapabilities=['byte-payload'],
        records=records,wholeSkillDataAdmitted=False,evidenceBoundary=dict(exact='Distinct selected dropdown Original/wrapper ancestry, int/int base source, MC4 new/existing/FF complete frames, all named fields/setters, cache32 refresh versus cache40 construction/GetValue, ordinary canonical adapters and Reader identity.',
            conditional=__doc__,structuralOnly='Stored key, selector flags and Int32 value.',
            unresolved=['runtime blackboard evaluation/provider/callback choice','noncoherent own-cache prehook','cold/refill/error paths','enclosing owners/physical EOF']))))
