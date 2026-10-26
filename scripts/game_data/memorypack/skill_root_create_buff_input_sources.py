"""CreateBuffActionInput MC5 with distinct original and inherited typed caches.

The actual source prepares own cache32 before its header, calls the inherited
BuffInput cache24 getter for the first three stored fields, then uses its own
typed setters for pooled buffIdKey and Boolean readIdFromBlackboard. The fresh
constructor first runs the BuffInput constructor, then installs the selected
Create original in holder16/cache32; inherited cache24 is never equated to it.
Own and inherited getter refresh/cast semantics, exact metadata lineage, named
field transfers and complete selected MC5/FF/new returns are separate proofs.
Matching normal typed allocations, coherent ready closed contexts, buffered
disjoint storage and noninterfering helper/barrier effects remain conditional.
Runtime provider selection, the positive AssignPair collection join and enclosing
union/root/EOF are not inferred from this caller component.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_assign_pair_sources import branch,need

VALUE='Beyond.Gameplay.Core.CreateBuffActionInput'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffActionInputForMemoryPack'
BASE='Beyond.Gameplay.Core.BuffInput'
BASE_WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_BuffInputForMemoryPack'
LIST='System.Collections.Generic.List`1<Beyond.Blackboard+AssignPair>'


def reader_program(regions,entry,offsets,slots,s,*,new=False,null=False,prepare_empty=False,original_null=False):
    need('literal-create-reader-paths',True,all(type(x)is bool for x in(new,null,prepare_empty,original_null)))
    need('compatible-create-reader-paths',True,not(new and(prepare_empty or original_null))and not(original_null and not(prepare_empty and null)))
    g=BytesPath(regions,entry);cur,rem,adv,used=(bytes((offsets[n],)).hex()for n in('currentPtr','bufferLength','advancedCount','consumed'))
    g.take('48895c2408','48896c2410','4889742418','57','4883ec20');ready=flag(g)
    g.take('488bf2','488bd9');g.branch('0f84',False)
    g.take('488b2e','4885ed');g.branch('74',new,1)
    classes=[];prepare_flag=None
    if not new:
        prepare_flag=flag(g);g.branch('0f84',False)
        g.take('48837d2000');g.branch('0f84',prepare_empty)
        if prepare_empty:
            g.take('48837d1000');g.branch('0f84',original_null)
            if not original_null:
                g.take('488b7d10');at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
                g.take('488bcf');g.call(s['cast']);g.take('48894520','488bcf')
                at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell));g.call(s['cast'])
                g.take('488d4d20');g.call(s['barrier']);g.take('90');g.jump('e9')
                need('same-inline-Create-class',classes[0]['cell'],classes[1]['cell'])
    g.take('837b'+rem+'01');g.branch('0f8c',False)
    g.take('488b43'+cur,'0fb638','8b6b'+rem,'83ed01');g.branch('0f88',False)
    g.take('48ff43'+cur,'ff43'+adv,'ff43'+used,'896b'+rem,'4080ffff');g.branch('0f84',null)
    allocation=None;events=[]
    if null:
        g.take('488bce','48c70600000000');g.call(s['barrier']);g.jump('eb',1)
    else:
        g.take('48833e00');g.branch('0f84',new)
        if new:
            at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488be8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');g.call(s['constructor'])
            g.take('488bce','48892e');g.call(s['barrier']);g.take('90');g.jump('e9')
            allocation=dict(instruction=at,cell=cell)
        g.take('4080ff05');g.branch('0f85',False)
        g.take('488b3e','488bcb');at=g.at;g.call(s['boolean']);g.take('0fb6e8','4885ff');branch(g,'0f84','74',False)
        g.take('33d2','488bcf');g.call(s['baseGetter']);g.take('4885c0');branch(g,'0f84','74',False)
        g.take('408868'+bytes((slots['assignBlackboard'],)).hex())
        events.append(dict(fieldName='assignBlackboard',kind='bool',sourceCall=at,sourceTarget=s['boolean'],inheritedGetter=s['baseGetter']))
        g.take('488bcb');at=g.at;cell=g.relative('488b15');context=dict(instruction=at,cell=cell)
        g.take('488b3e');at=g.at;g.call(s['list']);g.take('488be8','4885ff');branch(g,'0f84','74',False)
        g.take('33d2','488bcf');g.call(s['baseGetter']);g.take('4885c0');branch(g,'0f84','74',False)
        slot=bytes((slots['assignItems'],)).hex();g.take('488d48'+slot,'488968'+slot);g.call(s['barrier'])
        events.append(dict(fieldName='assignItems',kind='list',sourceCall=at,sourceTarget=s['list'],typedContext=context,inheritedGetter=s['baseGetter']))
        g.take('488b3e','488bcb');at=g.at;g.call(s['pool']);g.take('488be8','4885ff');branch(g,'0f84','74',False)
        g.take('33d2','488bcf');g.call(s['baseGetter']);g.take('4885c0');branch(g,'0f84','74',False)
        slot=bytes((slots['buffId'],)).hex();g.take('488d48'+slot,'488968'+slot);g.call(s['barrier'])
        events.append(dict(fieldName='buffId',kind='pooled-string',sourceCall=at,sourceTarget=s['pool'],inheritedGetter=s['baseGetter']))
        for field,role,kind in(('buffIdKey','setKey','pooled-string'),('readIdFromBlackboard','setFlag','bool')):
            g.take('488b3e','488bcb');at=g.at;g.call(s['pool']if kind=='pooled-string'else s['boolean'])
            g.take('4885ff');branch(g,'0f84','74',False);g.take('4533c0','488bd0'if kind=='pooled-string'else'0fb6d0','488bcf')
            setter=g.at;g.call(s[role]);events.append(dict(fieldName=field,kind=kind,sourceCall=at,
                sourceTarget=s['pool']if kind=='pooled-string'else s['boolean'],setterCall=setter,setterTarget=s[role]))
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,prepareReadyFlag=prepare_flag,newWrapper=new,ff=null,
        prepareCacheEmpty=prepare_empty,prepareOriginalNull=original_null,
        originalHolderOffset=16,ownCacheOffset=32,inheritedCacheOffset=24,inheritedCachesNotEquated=True,
        inlineClassUsages=classes,newAllocationUsage=allocation,orderedFields=events,
        memberCount=None if null else 5,normalReturn=True,entryRspRestored=True,childGrammarsAdmitted=False)


def original_initializer_program(regions,entry,s):
    """Actual optimized original initializer; no named-entry equality assumed."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','56','4883ec20','488bf1')
    at=g.at;cell=g.relative('488b0d');allocation=dict(instruction=at,cell=cell)
    g.call(s['allocate']);g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('48897c2430','33d2');at=g.at;cell=g.relative('488b3d');constructor=dict(instruction=at,cell=cell)
    g.take('488b4f20','488b89c0000000');g.call(s['context'])
    g.take('83b8e000000000');g.branch('74',False,1)
    g.take('488b4f20','33d2','488b89c0000000');g.call(s['context'])
    g.take('488b88b8000000','488b01','488d4b10','48894310');g.call(s['barrier'])
    g.take('488d4e20','48895e20','488b7c2430','488b5c2438','4883c420','5e')
    need('actual-initializer-barrier-tail',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,listAllocationUsage=allocation,listConstructorUsage=constructor,
        original='same incoming rcx preserved rsi',originalListFieldOffset=32,
        listItemsOffset=16,listContextSlot=0,normalReturnViaBarrier=True,
        classAndOtherOriginalFieldsUnchanged=True,wireBytes=0,
        condition='Normal typed zeroed List<AssignPair> allocation and initialized owned List class/static empty array; compatible context/barrier helpers and valid disjoint original/list/frame. This initializer is independently selected from its actual caller E8, never equated to a metadata constructor pointer.')


def inline_cached_setter_program(regions,entry,s,*,kind,field_offset,cache='coherent'):
    """Own setters inline their cache32 getter while preserving incoming RSI."""
    need('exact-inline-setter-kind',True,kind in('reference','bool'))
    need('exact-inline-setter-cache',True,cache in('coherent','empty','stale'))
    need('bounded-inline-setter-slot',True,type(field_offset)is int and 16<=field_offset<128)
    g=BytesPath(regions,entry);g.take('4056','4883ec20');ready=flag(g)
    g.take('488bf2'if kind=='reference'else'0fb6f2','48895c2430','488bd9');g.branch('74',False,1)
    g.take('48837b2000');g.branch('0f84',cache=='empty')
    if cache!='empty':g.take('488b4310','48394320');g.branch('0f85',cache=='stale')
    classes=[]
    if cache!='coherent':
        at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
        g.take('48897c2438','488b7b10','488bcf');g.call(s['cast']);g.take('48894320','488bcf')
        at=g.at;cell=g.relative('488b15');classes.append(dict(instruction=at,cell=cell))
        g.call(s['cast']);g.take('488d4b20');g.call(s['barrier']);g.take('488b7c2438');g.jump('e9')
        need('same-inline-setter-class',classes[0]['cell'],classes[1]['cell'])
    g.take('488b4b20'if kind=='reference'else'488b4320','488b5c2430',
        '4885c9'if kind=='reference'else'4885c0');g.branch('74',False,1)
    slot=bytes((field_offset,)).hex()
    if kind=='reference':
        g.take('488971'+slot,'4883c1'+slot,'4883c420','5e')
        need('inline-reference-setter-barrier',s['barrier'],g.relative('e9'))
    else:g.take('408870'+slot,'4883c420','5e','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,kind=kind,fieldOffset=field_offset,
        cacheState=cache,originalHolderOffset=16,ownCacheOffset=32,concreteClassUsages=classes,
        preservedInput='complete incoming RDX'if kind=='reference'else'incoming DL unchanged',
        storedBytes=8 if kind=='reference'else 1,inheritedCache24Unchanged=True,
        normalReturn=True,entryRspRestored=True,wireBytes=0)


def derive(image,pins):
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.skill_root_buff_input_sources import (
        derive_buff_input,derived_cached_getter_program,typed_cached_constructor_program)
    from scripts.game_data.memorypack.skill_shared_sequence_sources import selected_inputs,_selected_wrapper
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.pointer_param import methods,owned,registered_pair
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param,buff_ec_profiles_native as ec
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.wrapper_members import INSTANCE_FIELD_NAMES
    selected_inputs(pins);base=image.pe.image_base;md=image.metadata;ctx=NativeReferenceContext(image)
    inherited=derive_buff_input(image,pins);wrapper=_selected_wrapper(image,WRAPPER)
    need('actual-original-base',BASE,ctx.parent(VALUE));need('actual-wrapper-base',BASE_WRAPPER,ctx.parent(WRAPPER))
    need('exact-MC5-members',[('assignBlackboard','bool'),('assignItems',LIST),('buffId','string'),('buffIdKey','string'),('readIdFromBlackboard','bool')],
        [(m.name,m.declared_type)for m in wrapper.members])
    own=[f for f in md.fields_for(md.types[wrapper.type_definition])if md.string(f.name_index)in INSTANCE_FIELD_NAMES and not ctx.field_attributes(f.type_index)&16]
    need('unique-owned-Create-cache',1,len(own));fd=own[0]
    need('own-Create-cache',(WRAPPER,VALUE,32),ctx.field(WRAPPER+'::'+md.string(fd.name_index)))
    scalar.ordinary(image,ctx.type_pointer(fd.type_index),18,'createBuffInput.cache',reference=True)
    pair=derive_pair(image,VALUE,WRAPPER,owned_getter_family=True);forward=registered_pair(image,pair,wrapper,label='createBuffInput.registered')
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    for name in('get___instance','GetValue'):
        scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,(VALUE,18,False),[],'createBuffInput.'+name)
    for name in('.ctor',):scalar.owned_method_abi(image,ctx,mm[name].index,wrapper.type_definition,('void',1,False),[],'createBuffInput.'+name)
    s={k:base+v for k,v in inherited['symbolRvas'].items()}
    s['baseGetter']=s['getter'];s['baseConstructor']=s['constructor']
    s.update({k:image.method_pointer_va(mm[n])for k,n in dict(getter='get___instance',constructor='.ctor',setKey='set___buffIdKey__',setFlag='set___readIdFromBlackboard__').items()})
    ctor,=[m for m in md.methods_for(ctx.index.types[VALUE])if md.string(m.name_index)=='.ctor'and m.parameter_count==0]
    scalar.owned_method_abi(image,ctx,ctor.index,ctor.declaring_type,('void',1,False),[],'createBuffInput.originalConstructor')
    named_constructor=image.method_pointer_va(ctor)
    bodies={role:owned(image,target)for role,target in s.items()if role in('getter','constructor','setKey','setFlag')}
    bodies['reader']=owned(image,image.method_pointer_va(mm['Deserialize']))
    def call(body,offset):
        row,=[r for r in body['rows']if int(r['va'],16)==body['pointer']+offset]
        raw=bytes.fromhex(row['bytes']);need('selected-create-E8',(5,232),(len(raw),raw[0]));return control_transfer(row)['target']
    s['originalConstructor']=call(bodies['constructor'],90)
    thunk=bytes.fromhex('33D2E9')+(s['originalConstructor']-(named_constructor+7)).to_bytes(4,'little',signed=True)
    need('named-original-constructor-exact-zero-context-tail',thunk,image.pe.bytes_at_va(named_constructor,7))
    constructor_thunk=dict(methodIndex=ctor.index,entryRva=named_constructor-base,bytesHex=thunk.hex().upper(),
        actualTargetRva=s['originalConstructor']-base,rdxIsZeroAtBothCallers=True,physicalExtentProved=False)
    bodies['originalInitializer']=owned(image,s['originalConstructor'])
    s['context']=call(bodies['originalInitializer'],58)
    need('same-default-list-class-context-helper',s['context'],call(bodies['originalInitializer'],85))
    original_initializer=original_initializer_program(bodies['originalInitializer']['regions'],s['originalConstructor'],s)
    s['list']=call(bodies['reader'],202)
    for offset,role in((149,'boolean'),(257,'pool'),(304,'pool'),(334,'boolean'),(171,'baseGetter'),(224,'baseGetter'),(275,'baseGetter')):
        need('exact-inherited-source:'+role,s[role],call(bodies['reader'],offset))
    offsets=scalar.reader_offsets(image,'createBuffInput');slots={n:ctx.field(BASE+'::'+n)[2]for n in('assignBlackboard','assignItems','buffId')}
    programs=[reader_program(bodies['reader']['regions'],bodies['reader']['pointer'],offsets,slots,s,**path)for path in(
        {},dict(new=True),dict(null=True),dict(new=True,null=True),dict(prepare_empty=True),dict(prepare_empty=True,null=True),
        dict(prepare_empty=True,original_null=True,null=True))]
    getters=[derived_cached_getter_program(bodies['getter']['regions'],s['getter'],s,cache=cache)for cache in('coherent','empty','stale')]
    own_value=owned(image,image.method_pointer_va(mm['GetValue']))
    own_value_programs=[derived_cached_getter_program(own_value['regions'],own_value['pointer'],s,cache=cache)for cache in('coherent','empty','stale')]
    constructor=typed_cached_constructor_program(bodies['constructor']['regions'],s['constructor'],s,cache_offset=32,base_constructor=True)
    classes=[]
    for p in programs+getters+own_value_programs+[constructor]:
        for u in p.get('inlineClassUsages',[])+p.get('concreteClassUsages',[]):
            usage=derive_typed_usage_context(image,u['instruction']-base,label='createBuffInput.concreteClass')
            need('exact-Create-class',(1,VALUE),(usage['tag'],usage['typeName']));classes.append(usage)
    original=derive_typed_usage_context(image,constructor['originalClassUsage']['instruction']-base,label='createBuffInput.originalClass')
    need('exact-Create-allocation',(1,VALUE),(original['tag'],original['typeName']))
    base_class=derive_typed_usage_context(image,constructor['baseClassUsage']['instruction']-base,label='createBuffInput.baseClass')
    need('exact-base-wrapper-constructor-class',(1,BASE_WRAPPER),(base_class['tag'],base_class['typeName']))
    allocation=derive_typed_usage_context(image,programs[1]['newAllocationUsage']['instruction']-base,label='createBuffInput.wrapperAllocation')
    need('exact-Create-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    setters={}
    for name,role,kind,raw_kind,slot in(('buffIdKey','setKey','reference',14,48),('readIdFromBlackboard','setFlag','bool',2,40)):
        field=ctx.field(VALUE+'::'+name);need('exact-own-Create-field',(VALUE,'string'if kind=='reference'else'bool',slot),field)
        method=mm['set___'+name+'__']
        scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),[(field[1],raw_kind,False)],'createBuffInput.setter')
        fd,=[f for f in md.fields_for(ctx.index.types[VALUE])if md.string(f.name_index)==name]
        scalar.ordinary(image,ctx.type_pointer(fd.type_index),raw_kind,'createBuffInput.field',reference=kind=='reference')
        setters[name]=[inline_cached_setter_program(bodies[role]['regions'],s[role],s,kind=kind,field_offset=slot,cache=cache)
            for cache in('coherent','empty','stale')]
        for program in setters[name]:
            for u in program['concreteClassUsages']:
                selected_class=derive_typed_usage_context(image,u['instruction']-base,label='createBuffInput.setterClass')
                need('exact-inline-setter-Create-class',(1,VALUE),(selected_class['tag'],selected_class['typeName']))
                classes.append(selected_class)
    usage=derive_typed_usage_context(image,programs[0]['orderedFields'][1]['typedContext']['instruction']-base,label='createBuffInput.assignItems')
    bind_typed_read(image,usage,method_name='ReadPackable',argument=LIST,kind=21,reference=True)
    clones=ec.clone_facts(image,pins);need('actual-list-reference-clone',clones['ReadPackable']['targetRva'],s['list']-base)
    from scripts.game_data.memorypack.skill_value_list_context import derive as derive_list_context
    list_context,_=derive_list_context(image,pins,typed_request=usage,call_target=s['list'],element_type='Beyond.Blackboard+AssignPair')
    list_allocation=derive_typed_usage_context(image,original_initializer['listAllocationUsage']['instruction']-base,label='createBuffInput.defaultList')
    need('exact-default-list-type',(1,LIST),(list_allocation['tag'],list_allocation['typeName']))
    scalar.ordinary(image,ctx.type_pointer(list_allocation['typeIndex']),21,'createBuffInput.defaultList',reference=True)
    list_constructor=derive_typed_usage_context(image,original_initializer['listConstructorUsage']['instruction']-base,label='createBuffInput.defaultListConstructor')
    need('exact-default-list-constructor',('System.Collections.Generic.List`1','.ctor',['Beyond.Blackboard+AssignPair'],[]),
        tuple(list_constructor[k]for k in('typeName','methodName','classArguments','methodArguments')))
    lm=md.methods[list_constructor['methodSpec'][0]]
    need('default-list-constructor-ABI',(False,'void',0),(bool(lm.flags&16),ctx.type_name(lm.return_type),lm.parameter_count))
    return json.loads(json.dumps(dict(schema='endfield.skill-root-create-buff-input-source.v1',nativeInputs=pins,
        status='proved-MC5-caller-requires-assign-pair-list',typeName=VALUE,wrapperName=WRAPPER,
        registeredPair=pair,forwarding=forward,programs=programs,constructorProgram=constructor,
        getterPrograms=getters,getValuePrograms=own_value_programs,getValueWindows=own_value['windows'],setterPrograms=setters,
        originalConstructorThunk=constructor_thunk,originalInitializerProgram=original_initializer,
        originalInitializerListContext=list_context,defaultListAllocationUsage=list_allocation,defaultListConstructorUsage=list_constructor,
        ownCacheField=dict(fieldName=md.string(own[0].name_index),offset=32),inheritedBuffInput=inherited,
        concreteClassUsages=classes,originalAllocationUsage=original,wrapperAllocationUsage=allocation,baseClassUsage=base_class,
        sourceWindows={k:b['windows']for k,b in bodies.items()},symbolRvas={k:v-base for k,v in s.items()},
        requiredChildJoins=[dict(fieldName='assignItems',typeName=LIST,typedRequest=usage,sourceTargetRva=s['list']-base)],
        wholeRecordAdmitted=False,wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='CreateBuffActionInput MC5/FF/new reader, pre-header own-cache32 refresh, exact inherited cache24 getter flow and named original stores, own getter/constructor/setter semantics and full selected normal returns.',
            conditional=__doc__,structuralOnly='Stored authored buff/blackboard configuration.',
            unresolved=['positive AssignPair list join','abstract union/parent callback and framing','runtime selection','whole root/physical EOF']))))
