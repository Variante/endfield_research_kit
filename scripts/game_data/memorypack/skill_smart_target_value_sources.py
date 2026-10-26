"""Own SmartTargetSelectSetting managed40 and MC4 wrapper source.

The complete hidden getter copies sixteen plus sixteen plus eight bytes, with
three independently laid out reference lanes and two padding ranges. The wire
record instead delegates BuffFindSettings, a BuffId list and Query around one
ordinary Int32-backed enum. Its wrapper FF clears a reference, not an Original
default40. Each delegated child, canonical value adapter, actual parent source
and whole field/frame remain independent gates. No historical parser, managed
width, native marshal size or similarly sized value supplies wire grammar.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

TYPE='Beyond.Gameplay.Core.SmartTargetSelectSetting'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_SmartTargetSelectSettingForMemoryPack'
FIND='Beyond.Gameplay.Core.BuffFindSettings'
BUFF_IDS='System.Collections.Generic.List`1<Beyond.Gameplay.Core.BuffId>'
ENUM='Beyond.Gameplay.SmartTargetSelectStrategy'
QUERY='Beyond.Gameplay.Core.GameplayTagQuery'
MEMBERS=(('smartTargetBuffFindSettings',FIND),('smartTargetBuffIds',BUFF_IDS),
    ('smartTargetSelectStrategy',ENUM),('smartTargetTagQuery',QUERY))
CAPABILITY='skill-smart-target-select-setting'
ORDER=[dict(fieldName=n,kind=k,childCapability=c)for n,k,c in(
    (MEMBERS[0][0],'record','skill-root-buff-find-settings'),
    (MEMBERS[1][0],'value-list','skill-root-buff-id-list'),
    (MEMBERS[2][0],'enum32',None),(MEMBERS[3][0],'record','skill-root-gameplay-tag-query'))]


def getter_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f104210','488bc1','0f104a20','0f1101',
        'f20f104230','0f114910','f20f114120','c3')
    return dict(selectedBytes=g.seen,managedBytes=40,wrapperOffset=16,hiddenOutputRegister='rcx',
        wrapperRegister='rdx',sameHiddenOutputReturnedInRax=True,sourceSlices=[[0,16],[16,16],[32,8]],
        referenceLaneOffsets=[8,24,32],normalReturn=True,entryRspRestored=True)


def default_program(regions,entry):
    g=BytesPath(regions,entry);g.take('0f57c0','33c0','0f114110','0f114120','48894130','c3')
    return dict(selectedBytes=g.seen,managedBytes=40,wrapperOffset=16,zeroByteRanges=[[0,40]],
        normalReturn=True,entryRspRestored=True)


def wrapper_program(regions,entry,*,new=False,null=False):
    need('smart-target-literal-wrapper-path',True,type(new)is bool and type(null)is bool and not(new and null))
    g=BytesPath(regions,entry);g.take('48895c2418','57','4883ec30');ready=flag(g)
    g.take('488bda','488bf9');g.branch('0f84',False);calls={};sites={};usages={}
    def call(role):
        at=g.at;target=g.relative('e8')
        if role in calls:need('smart-target-same-actual-helper:'+role,calls[role],target)
        calls[role]=target;sites.setdefault(role,[]).append(at)
    def usage(role,opcode):
        at=g.at;cell=g.relative(opcode);usages[role]=dict(instruction=at,cell=cell)
    g.take('488d542440','c644244000','488bcf');call('header');g.take('84c0');g.branch('0f84',null)
    if null:
        g.take('488bcb','48c70300000000');call('barrier');g.take('90');g.jump('e9')
    else:
        g.take('4889742448','48833b00');g.branch('0f84',new)
        if new:
            usage('allocation','488b0d');call('allocate');g.take('4885c0');g.branch('0f84',False)
            g.take('33c9','0f57c0','0f114010','0f114020','48894830','488bcb','488903')
            call('barrier');g.take('90');g.jump('e9')
        g.take('0fb6742440','4080fe04');g.branch('0f85',False)
        usage('find','488b15');g.take('488bcf','488b33');call('find');g.take('4885f6');g.branch('0f84',False)
        g.take('488d4e30','48894630');call('barrier')
        usage('buffIds','488b15');g.take('488bcf','488b33');call('buffIds');g.take('4885f6');g.branch('74',False,1)
        g.take('488d4e18','48894618');call('barrier')
        usage('enum','488b15');g.take('488bcf','488b33');call('enum');g.take('4885f6');g.branch('74',False,1)
        g.take('894610','488d4c2420');usage('query','4c8b05');g.take('488bd7','488b1b');call('query')
        g.take('4885db');g.branch('74',False,1);g.take('0f10442420','488d4b28','0f114320');call('barrier')
        g.take('488b742448')
    g.take('488b5c2450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,newWrapper=new,wrapperFF=null,
        actualCalls=calls,callSites=sites,usages=usages,memberCount=None if null else 4,
        wrapperReferenceCleared=null,originalDefaultValueAdmitted=False,managedBytes=40,
        wholeQuery16StoredUnchanged=not null,queryReferenceLaneBarrierOffset=40 if not null else None,
        entryRspRestored=True,allIntegerNonvolatilesRestored=True,normalReturn=True,
        wireOrder=[]if null else ORDER)


def layout(image,ctx):
    """Fresh own nominal managed40/nested Query layout, without wire admission."""
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper
    from scripts.game_data.memorypack.skill_root_value_sources import value_layout
    from scripts.game_data.memorypack.generated_managed_value_sources import layout as managed_layout
    wrapper=_selected_wrapper(image,WRAPPER);need('smart-target-own-original',TYPE,wrapper.wrapped_type)
    need('smart-target-complete-members',list(MEMBERS),[(m.name,m.declared_type)for m in wrapper.members])
    td=ctx.index.types[TYPE];need('smart-target-plain-value',('System.ValueType',-1),(ctx.parent(TYPE),td.generic_container_index))
    # The nested Query is separately declared and laid out; its reference lane
    # and padding cannot be inferred from its managed size alone.
    query_layout=managed_layout(image,ctx,QUERY)
    need('smart-target-exact-nested-Query-layout',(16,[8],[[4,4]]),tuple(query_layout[k]for k in
        ('managedBytes','referenceLaneOffsets','paddingByteRanges')))
    result=value_layout(image,ctx,TYPE,wrapper,managed_bytes=40,fields={
        MEMBERS[0][0]:(FIND,18,8),MEMBERS[1][0]:(BUFF_IDS,21,8),MEMBERS[2][0]:(ENUM,17,4),MEMBERS[3][0]:(QUERY,17,16)})
    need('smart-target-exact-reordered-fields',{MEMBERS[0][0]:(32,48,8),MEMBERS[1][0]:(8,24,8),
        MEMBERS[2][0]:(0,16,4),MEMBERS[3][0]:(16,32,16)},
        {n:tuple(f[k]for k in('unboxedOffset','wrapperOffset','bytes'))for n,f in result['fields'].items()})
    result.update(referenceLaneOffsets=[8,24,32],paddingByteRanges=[[4,8],[20,24]],nestedQueryLayout=query_layout)
    return result


def derive_wrapper(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import scalar_param_native as scalar,primitive_param
    from scripts.game_data.memorypack.pointer_param import methods,owned,leaf,registered_pair
    from scripts.game_data.memorypack.reference_param_profile import derive_pair
    from scripts.game_data.memorypack.skill_root_prefix_sources import bind_typed_read
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _selected_wrapper,_fast_barrier
    from scripts.game_data.memorypack.vector_layout import vector_recorder
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    wrapper=_selected_wrapper(image,WRAPPER);nominal_layout=layout(image,ctx)
    mm=methods(image,wrapper);primitive_param.reader_abi(image,ctx,mm['Deserialize'],wrapper)
    scalar.owned_method_abi(image,ctx,mm['GetValue'].index,wrapper.type_definition,(TYPE,17,False),[],'smartTarget.GetValue')
    getter=leaf(image,image.method_pointer_va(mm['GetValue']),['0F104210','488BC1','0F104A20','0F1101','F20F104230','0F114910','F20F114120','C3'])
    getter_semantics=getter_program([(base+a,bytes.fromhex(h))for a,h in getter['instructions']],image.method_pointer_va(mm['GetValue']))
    defaults={}
    for role in('.ctor','CreateInstance'):
        scalar.owned_method_abi(image,ctx,mm[role].index,wrapper.type_definition,('void',1,False),[],'smartTarget.'+role)
        defaults[role]=leaf(image,image.method_pointer_va(mm[role]),['0F57C0','33C0','0F114110','0F114120','48894130','C3'])
    body=owned(image,image.method_pointer_va(mm['Deserialize']))
    paths=[wrapper_program(body['regions'],body['pointer'],**choice)for choice in({},{'new':True},{'null':True})]
    symbols={}
    for path in paths:
        for role,target in path['actualCalls'].items():
            if role in symbols:need('smart-target-identical-path-helper:'+role,symbols[role],target)
            symbols[role]=target
    requests={role:derive_typed_usage_context(image,row['instruction']-base,label='smartTarget.'+role)
        for role,row in paths[0]['usages'].items()}
    typed={}
    for role,typ,method,kind,reference in(('find',FIND,'ReadValue',18,True),('buffIds',BUFF_IDS,'ReadPackable',21,True),
            ('enum',ENUM,'ReadUnmanaged',17,False),('query',QUERY,'ReadValue',17,False)):
        typed[role]=bind_typed_read(image,requests[role],method_name=method,argument=typ,kind=kind,reference=reference)
    enum=ctx.index.types[ENUM];enum_fields=[f for f in md.fields_for(enum)if not ctx.field_attributes(f.type_index)&16]
    need('smart-target-actual-enum-backing',1,len(enum_fields));backing,=enum_fields
    need('smart-target-enum-backing-name','value__',md.string(backing.name_index));scalar.ordinary(image,ctx.type_pointer(backing.type_index),8,'smartTarget.enumInt32')
    allocation=derive_typed_usage_context(image,paths[1]['usages']['allocation']['instruction']-base,label='smartTarget.allocation')
    need('smart-target-own-wrapper-allocation',(1,WRAPPER),(allocation['tag'],allocation['typeName']))
    offsets=scalar.reader_offsets(image,'smartTarget');record=vector_recorder(image)
    header=record(symbols['header']-base);primitive_param.object_header_source(image,header,offsets)
    integer=record(symbols['enum']-base);scalar.integer_source(image,integer,offsets,'smartTarget.enumInt32')
    barrier,barrier_program,_=_fast_barrier(image,symbols['barrier'])
    pair=derive_pair(image,TYPE,WRAPPER);forwarding=registered_pair(image,pair,wrapper,label='smartTarget.pair')
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.skill-smart-target-wrapper-source.v1',
        status='proved-smart-target-wrapper-requires-value-and-child-joins',nativeInputs=pins,typeName=TYPE,wrapperName=WRAPPER,
        layout=nominal_layout,registeredPair=pair,forwarding=forwarding,getter=getter,getterProgram=getter_semantics,defaults=defaults,
        sourceWindows=body['windows'],programs=paths,requests=requests,typedArguments=typed,allocationUsage=allocation,
        headerSource=header,integerSource=integer,barrierWindows=barrier,barrierProgram=barrier_program,
        symbolRvas={k:v-base for k,v in symbols.items()},wireOrder=ORDER,
        originalDefaultValueAdmitted=False,childGrammarAdmitted=False,parentFieldAdmitted=False,wholeOwnerAdmitted=False)))
