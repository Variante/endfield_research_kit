"""Current Patrol consumer entry programs, with no execution/playback claim.

The simple radio handler and event-key getter are independently joined to
their nominal fields, signatures and actual call targets. Controller lookup,
conversion, action dispatch and checkpoint production/filtering remain
separate obligations; these two entry facts do not establish those joins.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
ACTION='Beyond.Gameplay.Core.PatrolSubAction'
HEADER='Beyond.Gameplay.Actions.LevelEvent.OnNpcPatrolCheckpointReach'
EVENT='Beyond.Gameplay.Core.GameLevelEvent'


def radio_program(regions,entry,*,radio_offset,ready_call,play_call):
    if type(radio_offset)is not int or not 16<=radio_offset<128:
        raise ValueError('patrolConsumer.radio-owned-reference-field')
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec30');ready=flag(g)
    g.take('498bf8','488bda','488bf1');g.branch('75',True,1)
    root=g.relative('488b05');g.take('488b4838','4885c9');g.branch('74',True,1)
    g.take('4885db');g.branch('75',True,1)
    typed_class=dict(instruction=g.at,cell=g.relative('488b0d'))
    g.take('488b5b'+bytes((radio_offset,)).hex());g.call(ready_call)
    g.take('4533c9','48c744242000000000','4183c8ff','b201','488bcb');g.call(play_call)
    g.take('b001','488b5c2440','488b742448','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,metadataReadyFlag=ready,optionalCallbackRootCell=root,
        typedClass=typed_class,radioFieldOffset=radio_offset,
        radioIdTransfer='incoming RDX action -> saved RBX -> same qword field -> saved RBX across normal class-ready helper -> PlayRadio.RCX',
        requestArguments=dict(fromBegin=True,index=-1,noFlushAfterLoading=False,implicitMethodInfo=None),
        normalReturn=True,returnBool=True,runtimeInvocationObserved=False,playbackProved=False,
        condition='Initialized metadata and stable nonnull optional-callback root with absent selected receiver; compatible nonnull nominal action, normal class-ready and PlayRadio call ABI and disjoint source storage. Exact entry source only; action dispatch, live invocation and playback remain unproved.')


def event_key_program(regions,entry,key):
    if type(key)is not int or not 0<=key<2**32:raise ValueError('patrolConsumer.enum-value')
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8bc9','488b4830','4885c9');g.branch('74',True,1)
    g.take('b8'+key.to_bytes(4,'little').hex(),'4883c428','c3')
    return dict(selectedBytes=g.seen,optionalCallbackRootCell=root,result=key,
        normalReturn=True,runtimeInvocationObserved=False,
        condition='Stable nonnull optional-callback root with absent selected receiver. Exact getter source and independently checked nominal enum return ABI; no runtime registration/dispatch/invocation follows.')


def derive(image,pins):
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.protocol import native_enum_members
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    _publication_gate(image,pins)
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda k,e,a:scalar.need('patrolConsumer',k,e,a)
    def method(owner,name,arity):
        m,=[m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and m.parameter_count==arity]
        return m
    radio=method(CONTROLLER,'_PlayRadioSubAction',1)
    scalar.owned_method_abi(image,ctx,radio.index,radio.declaring_type,('bool',2,False),[(ACTION,18,True)],'patrolConsumer.radio')
    radio_field=ctx.field(ACTION+'::radioId')
    need('nominal-radio-field',(ACTION,'string'),radio_field[:2])
    field,=[f for f in md.fields_for(ctx.index.types[ACTION])if md.string(f.name_index)=='radioId']
    scalar.ordinary(image,ctx.type_pointer(field.type_index),14,'patrolConsumer.radioId',reference=True)
    body=owned(image,image.method_pointer_va(radio))
    calls=[control_transfer(r)['target']for r in body['rows']if len(bytes.fromhex(r['bytes']))==5 and bytes.fromhex(r['bytes'])[0]==0xe8]
    need('radio-owned-helper-calls',True,len(calls)>=3)
    request=method('Beyond.Gameplay.Actions.GameAction','PlayRadio',4)
    need('request-static-void-arity',(True,'void',4),
        (bool(request.flags&16),ctx.type_name(request.return_type),request.parameter_count))
    scalar.ordinary(image,ctx.type_pointer(request.return_type),1,'patrolConsumer.PlayRadio.void')
    expected=[('radioId','string',14,True),('fromBegin','bool',2,False),
        ('index','int',8,False),('noFlushAfterLoading','bool',2,False)]
    for parameter,(name,type_name,kind,reference)in zip(md.parameters_for(request),expected,strict=True):
        need('request-owned-parameter',(name,type_name),(md.string(parameter.name_index),ctx.type_name(parameter.type_index)))
        scalar.ordinary(image,ctx.type_pointer(parameter.type_index),kind,'patrolConsumer.PlayRadio.'+name,reference=reference)
    need('actual-PlayRadio-target',image.method_pointer_va(request),calls[-1])
    program=radio_program(body['regions'],body['pointer'],radio_offset=radio_field[2],ready_call=calls[-2],play_call=calls[-1])
    usage=derive_typed_usage_context(image,program['typedClass']['instruction']-base,label='patrolConsumer.GameActionClass')
    need('exact-ready-class',(1,'Beyond.Gameplay.Actions.GameAction'),(usage['tag'],usage['typeName']))
    key_method=method(HEADER,'get_eventKey',0)
    scalar.owned_method_abi(image,ctx,key_method.index,key_method.declaring_type,(EVENT,17,False),[],'patrolConsumer.eventKey')
    need('enum-return-parent','System.Enum',ctx.parent(EVENT))
    need('enum-backing',(EVENT,'uint',16),ctx.field(EVENT+'::value__'))
    getter=owned(image,image.method_pointer_va(key_method))
    values=[int.from_bytes(raw[1:],'little')for r in getter['rows']
        if len(raw:=bytes.fromhex(r['bytes']))==5 and raw[0]==0xb8]
    need('one-exact-return-literal',1,len(values));key=values[0]
    enum=native_enum_members(md,image.body_index.enum_defaults,image.pe,image.registration,EVENT)
    members=[row for row in enum if row['id']==key]
    need('return-literal-is-owned-enum',True,bool(members))
    key_program=event_key_program(getter['regions'],getter['pointer'],key)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,radio=dict(
        method=[radio.index,CONTROLLER,'_PlayRadioSubAction',body['pointer']-base],
        sourceWindows=body['windows'],program=program,field=radio_field,readyClass=usage,
        requestMethod=[request.index,'Beyond.Gameplay.Actions.GameAction','PlayRadio',image.method_pointer_va(request)-base]),
        eventKey=dict(method=[key_method.index,HEADER,'get_eventKey',getter['pointer']-base],
            sourceWindows=getter['windows'],program=key_program,enumType=EVENT,enumMembers=members),
        actionDispatchProved=False,checkpointProducerProved=False,checkpointFilterProved=False,
        wholeOwnerAdmitted=False,runtimeInvocationObserved=False,playbackProved=False)))
