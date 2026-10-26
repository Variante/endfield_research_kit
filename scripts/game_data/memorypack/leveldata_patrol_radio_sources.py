"""Current Patrol radio scheduling and the selected delayed request source.

These complete selected entry programs join authored fields to owned controller
storage and, on the delayed due path, the actual PlayRadio call. They do not
prove that a controller is instantiated/ticked or that a request plays audio.
Optional replacement callbacks and collector-enabled paths stay conditional.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

CONTROLLER='Beyond.Gameplay.AI.NewNpcAIPatrolController'
ACTION='Beyond.Gameplay.Core.PatrolSubAction'
INFO='Beyond.Gameplay.AI.RadioInfo'


def displacement(value,width):
    if type(value)is not int or not 0<=value<2**(width*8-1):
        raise ValueError('patrolRadio.owned-field-displacement')
    return value.to_bytes(width,'little').hex()


def disabled_barrier_program(regions,entry):
    g=BytesPath(regions,entry);cell=flag(g,'833d');g.take('4c8bc1');g.branch('74',True,1);g.take('c3')
    return dict(selectedBytes=g.seen,disabledCollectorFlag=cell,preservedRegisters=['rax','rdx','r9','r10','r11'],
        selectedCalls=0,selectedMemoryWrites=0,runtimeCollectorStateObserved=False)


def schedule_program(regions,entry,fields,barrier,*,mode):
    if mode not in('time','range'):raise ValueError('patrolRadio.closed-schedule-mode')
    d=lambda name:displacement(fields[name],4)
    a=lambda name:displacement(fields[name],1)
    g=BytesPath(regions,entry);g.take('4883ec28');root=g.relative('488b05')
    g.take('4c8bd1','4c8bda','488b4838','4885c9');g.branch('74',True,1)
    if mode=='time':g.take('498d8a'+d('radioId'))
    g.take('4d85db');g.branch('75',True,1)
    g.take('488b42'+a('actionRadioId'))
    if mode=='time':g.take('488901')
    else:g.take('498d8a'+d('radioId'),'498982'+d('radioId'))
    g.call(barrier);g.take('458b4b'+a('actionWait'if mode=='time'else'actionRadius'),'b001')
    if mode=='time':
        g.take('45898a'+d('wait'),'41c782'+d('elapsed')+'00000000','41c682'+d('enabled')+'01')
    else:
        g.take('418b8a'+d('actionIndex'),'ffc1','45898a'+d('radius'),'41898a'+d('radioIndex'))
    g.take('4883c428','c3')
    return dict(selectedBytes=g.seen,mode=mode,optionalCallbackRootCell=root,
        radioIdUnchangedTransfer=True,returnBool=True,normalReturn=True,
        implicitMethodInfo=None,runtimeInvocationObserved=False,playbackProved=False,
        scheduling='copy nominal radioId and radioWaitTime; zero elapsed; enable one delayed check'if mode=='time'else
            'copy nominal radioId and radius; save current action index plus one with Int32 bits',
        condition='Stable nonnull compatible controller/action and optional callback root with absent receiver; selected collector-disabled leaf preserves volatile source registers. Only these initialized source paths are admitted.')


def delayed_program(regions,entry,fields,*,play_call,due):
    if type(due)is not bool:raise ValueError('patrolRadio.literal-due-path')
    d=lambda name:displacement(fields[name],4)
    g=BytesPath(regions,entry);g.take('4053','4883ec30');root=g.relative('488b05')
    g.take('488bd9','488b4838','4885c9');g.branch('0f85',False)
    g.take('488b83'+d('radioId'),'4885c0');g.branch('74',False,1)
    g.take('83781000');g.branch('0f87',True)
    g.take('83bb'+d('state')+'00');g.branch('75',False,1)
    g.take('80bb'+d('enabled')+'00');g.branch('74',False,1)
    g.take('f30f588b'+d('elapsed'),'f30f118b'+d('elapsed'));g.jump('eb',1)
    g.take('f30f1083'+d('elapsed'),'0f2f83'+d('wait'));g.branch('0f86',not due)
    typed=None
    if due:
        g.take('80bb'+d('enabled')+'00');g.branch('0f84',False)
        typed=dict(instruction=g.at,cell=g.relative('488b0d'))
        g.take('48897c2440','488bf8','83b9e000000000');g.branch('75',True,1)
        g.take('4533c9','48c744242000000000','41b8ffffffff','b201','488bcf');g.call(play_call)
        g.take('488b7c2440','c683'+d('enabled')+'00','c783'+d('elapsed')+'00000000');g.jump('e9')
    g.take('4883c430','5b','c3')
    return dict(selectedBytes=g.seen,optionalCallbackRootCell=root,due=due,readyClass=typed,
        requestArguments=dict(fromBegin=True,index=-1,noFlushAfterLoading=False,implicitMethodInfo=None)if due else None,
        requestCount=int(due),normalReturn=True,runtimeInvocationObserved=False,playbackProved=False,
        condition='Stable initialized nonnull controller and optional callback root with absent receiver; owned radio string nonempty, nominal PatrolState zero, needCheck true, buffered elapsed+delta is compared to wait with selected ordered result. Due path assumes ready class and normal PlayRadio ABI. No ticking, dispatch or playback is observed.')


def derive(image,pins):
    import json
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.protocol import native_enum_members
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack import scalar_param_native as scalar
    base=image.pe.image_base;ctx=NativeReferenceContext(image);md=image.metadata
    need=lambda k,e,a:scalar.need('patrolRadio',k,e,a)
    def method(owner,name,arity):
        return next(m for m in md.methods_for(ctx.index.types[owner])if md.string(m.name_index)==name and m.parameter_count==arity)
    def field(owner,name,kind):
        value=ctx.field(owner+'::'+name);need('nominal-field:'+owner+'::'+name,(owner,kind),value[:2]);return value[2]
    info=field(CONTROLLER,'m_radioInfo',INFO)
    need('owned-RadioInfo-value',True,ctx.is_value_type(INFO))
    shared=dict(radioId=info+field(INFO,'radioId','string')-16,wait=info+field(INFO,'radioWaitTime','float')-16,
        elapsed=info+field(INFO,'npcStopTime','float')-16,enabled=info+field(INFO,'needCheck','bool')-16,
        actionRadioId=field(ACTION,'radioId','string'),actionWait=field(ACTION,'radioWaitTime','float'),
        actionRadius=field(ACTION,'radius','float'),state=field(CONTROLLER,'m_state',CONTROLLER+'+PatrolState'))
    range_fields=dict(shared,radioId=field(CONTROLLER,'m_radioInRange','string'),
        radius=field(CONTROLLER,'m_range','float'),actionIndex=field(CONTROLLER,'m_actionIdx','int'),
        radioIndex=field(CONTROLLER,'m_radioActionIdx','int'))
    bodies={};schedules={};barriers={}
    for name,mode,fields in(('_PlayRadioAtTimeSubAction','time',shared),('_PlayRadioInRangeSubAction','range',range_fields)):
        m=method(CONTROLLER,name,1)
        scalar.owned_method_abi(image,ctx,m.index,m.declaring_type,('bool',2,False),[(ACTION,18,True)],'patrolRadio.schedule')
        body=owned(image,image.method_pointer_va(m));bodies[name]=body
        calls=[control_transfer(r)['target']for r in body['rows']if len(raw:=bytes.fromhex(r['bytes']))==5 and raw[0]==0xe8]
        # The only selected call is the actual field-store collector leaf; the
        # other direct call is owned by the excluded null-argument throw path.
        target=calls[-1];prefix=image.pe.bytes_at_va(target,12)
        need('disabled-barrier-short-edge',b'\x74',prefix[10:11])
        leaf=target+12+int.from_bytes(prefix[11:12],'little',signed=True)
        barrier=disabled_barrier_program([(target,prefix),(leaf,image.pe.bytes_at_va(leaf,1))],target)
        barriers[name]=dict(entryRva=target-base,proof=barrier)
        schedules[mode]=dict(method=[m.index,CONTROLLER,name,body['pointer']-base],windows=body['windows'],
            fields=fields,program=schedule_program(body['regions'],body['pointer'],fields,target,mode=mode))
    request=method('Beyond.Gameplay.Actions.GameAction','PlayRadio',4)
    need('actual-static-request-ABI',(True,'void',['string','bool','int','bool']),
        (bool(request.flags&16),ctx.type_name(request.return_type),[ctx.type_name(p.type_index)for p in md.parameters_for(request)]))
    scalar.ordinary(image,ctx.type_pointer(request.return_type),1,'patrolRadio.request.void')
    for p,(kind,reference)in zip(md.parameters_for(request),((14,True),(2,False),(8,False),(2,False)),strict=True):
        scalar.ordinary(image,ctx.type_pointer(p.type_index),kind,'patrolRadio.request.parameter',reference=reference)
    updater=method(CONTROLLER,'_PlayRadioAfterTime',1)
    scalar.owned_method_abi(image,ctx,updater.index,updater.declaring_type,('void',1,False),[('float',12,False)],'patrolRadio.delayed')
    body=owned(image,image.method_pointer_va(updater));programs=[delayed_program(body['regions'],body['pointer'],shared,
        play_call=image.method_pointer_va(request),due=due)for due in(False,True)]
    usage=derive_typed_usage_context(image,programs[1]['readyClass']['instruction']-base,label='patrolRadio.readyClass')
    need('exact-ready-class',(1,'Beyond.Gameplay.Actions.GameAction'),(usage['tag'],usage['typeName']))
    state_type=CONTROLLER+'+PatrolState'
    need('state-enum','System.Enum',ctx.parent(state_type))
    need('state-int32-backing',(state_type,'int',16),ctx.field(state_type+'::value__'))
    states=native_enum_members(md,image.body_index.enum_defaults,image.pe,image.registration,state_type)
    need('selected-state-member',True,any(r['id']==0 for r in states))
    return json.loads(json.dumps(dict(nativeInputs=pins,schedules=schedules,barriers=barriers,
        delayed=dict(method=[updater.index,CONTROLLER,'_PlayRadioAfterTime',body['pointer']-base],windows=body['windows'],
            fields=shared,programs=programs,readyClass=usage,request=[request.index,'Beyond.Gameplay.Actions.GameAction','PlayRadio',image.method_pointer_va(request)-base],states=states),
        rangeTriggerProved=False,actionDispatchProved=False,wholeOwnerAdmitted=False,
        runtimeInvocationObserved=False,playbackProved=False)))
