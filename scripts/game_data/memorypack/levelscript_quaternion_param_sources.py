"""Complete selected Quaternion Param caller, factories and hidden16 transfer.

The exact source profile owns no generic heap layout. Compiled setter offsets
are proved individually; the closed raw16 helper owns the constant's nominal
layout and actual internal MethodSpec. Ordinary Param adaptation is separate.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

TYPE='Beyond.Gameplay.Actions.Param`1<UnityEngine.Quaternion>'
VALUE='UnityEngine.Quaternion'


def need(check,condition,detail=None):
    if not condition:raise ValueError('quaternionParam.'+check+(':'+str(detail)[:1600]if detail is not None else''))


def reader_program(regions,entry,*,existing,null):
    need('literal-four-path-selection',type(existing)is bool and type(null)is bool)
    g=BytesPath(regions,entry);calls={}
    def call(name):
        at=g.at;target=g.relative('e8');calls[name]=dict(instructionVa=at,targetVa=target);return target
    g.take('48895c2410','4889742418','57','4883ec30');flag=g.relative('803d')+1
    g.take('00','488bda','488bf1');g.branch('75',True,1)
    g.take('488d542440','c644244000','488bce');call('header');g.take('84c0');g.branch('0f84',null)
    allocation=None
    if null:
        g.take('488bcb','48c70300000000');call('nullBarrier')
    else:
        g.take('48833b00');g.branch('75',existing,1)
        if not existing:
            at=g.at;cell=g.relative('488b0d');allocator=call('allocateWrapper')
            allocation=dict(instructionVa=at,cellVa=cell,allocatorTargetVa=allocator)
            g.take('488bf8','4885c0');g.branch('0f84',False)
            g.take('33d2','488bc8');allocation['constructorVa']=call('wrapperConstructor')
            g.take('488bcb','48893b');call('outputBarrier')
        g.take('807c244004');g.branch('0f85',False)
        g.take('488b3b','488d4c2420','488bd6');call('constValue')
        g.take('4885ff');g.branch('74',False,1)
        g.take('0f1000','4533c0','488d542420','488bcf','f30f7f442420');call('setConstValue')
        for name in('idRef','paramSource'):
            g.take('488b3b','488bce');call(name);g.take('4885ff');g.branch('74',False,1)
            g.take('4533c0','8bd0','488bcf');call('set'+name[0].upper()+name[1:])
        g.take('488b1b','488bce');call('path');g.take('4885db');g.branch('74',False,1)
        g.take('4533c0','488bd0','488bcb');call('setPath');g.jump('eb',1)
    g.take('488b5c2448','488b742450','4883c430','5f','c3')
    return dict(selectedBytes=g.seen,existing=existing,null=null,initializedFlagCellVa=flag,calls=calls,
        wrapperAllocation=allocation,memberCount=None if null else 4,
        orderedFields=[]if null else['constValue','idRef','paramSource','path'],
        hiddenOutputRspOffset=32,hiddenOutputBytes=16,returnedRaxMustEqualHiddenOutput=not null,
        complete16SelfCopyBeforeSetter=not null,constantSetterArgument=None if null else 'rdx=RSP32',
        headerLocalRspOffset=64,frameBytes=56,entryRspRestored=True,allNonvolatilesRestored=True,
        savedEntryHomes=dict(rbx=[16,24],rsi=[24,32]),pushedNonvolatiles=['rdi'],
        nullOutputBytes=8 if null else 0,normalReturn=True,initializedMetadataRequired=True,
        compatibleCallsRequired=True,childGrammarAdmitted=False,wholeOwnerAdmitted=False)


def factory_program(regions,entry,*,id_ref_offset):
    need('compiled-idRef-slot',type(id_ref_offset)is int and 16<=id_ref_offset<128)
    g=BytesPath(regions,entry);g.take('4053','4883ec20');flag=g.relative('803d')+1
    g.take('00','488bd9');g.branch('75',True,1)
    at=g.at;cell=g.relative('488b0d');allocator=g.relative('e8')
    g.take('4885c0');g.branch('75',True,1)
    g.take('c740'+bytes((id_ref_offset,)).hex()+'ffffffff','488d4b10','48894310','4883c420','5b')
    barrier=g.relative('e9')
    return dict(selectedBytes=g.seen,initializedFlagCellVa=flag,allocationInstructionVa=at,
        allocationCellVa=cell,allocatorTargetVa=allocator,barrierTargetVa=barrier,
        defaultIdRefOffset=id_ref_offset,defaultIdRef=-1,wholeReferenceStoreBytes=8,holderOffset=16,
        originalConstructorCalled=False,entryRspRestored=True,allNonvolatilesRestored=True,
        normalTypedZeroInitializedAllocationRequired=True,normalReturn=True)


def setter_program(regions,entry,*,field):
    need('finite-named-setter',field in('constValue','idRef','paramSource','path'))
    g=BytesPath(regions,entry);g.take('4883ec28','488b4910'if field=='path'else'488b4110',
        '4885c9'if field=='path'else'4885c0');g.branch('75',True,1)
    if field=='constValue':
        g.take('0f1002','0f1140');slot=g.read(1)[0];g.take('4883c428','c3');barrier=None;width=16
    elif field=='path':
        g.take('488951');slot=g.read(1)[0];g.take('4883c1'+bytes((slot,)).hex(),'4883c428')
        barrier=g.relative('e9');width=8
    else:
        g.take('8950');slot=g.read(1)[0];g.take('4883c428','c3');barrier=None;width=4
    need('bounded-compiled-field-slot',16<=slot<=127-width+1)
    return dict(selectedBytes=g.seen,fieldName=field,compiledFieldOffset=slot,storedBytes=width,
        barrierTargetVa=barrier,sourceBitsStoredUnchanged=True,entryRspRestored=True,normalReturn=True)


def derive_parent(image,pins):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext,closed_generic_reference_pointer_extent
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack import pointer_param as pointer,primitive_param as primitive,scalar_param_native as scalar,pooled_source_helper
    from scripts.game_data.memorypack import leveldata_quaternion_forwarder_sources as child
    from scripts.game_data.memorypack.wrapper_members import derive_from_image
    from scripts.game_data.memorypack.levelscript_script_task_param_sources import _record
    from scripts.game_data.memorypack.levelscript_condition_param_sources import _reference_join
    _publication_gate(image,pins);base=image.pe.image_base;ctx=NativeReferenceContext(image)
    wrapper,=[w for w in derive_from_image(image).values()if w.wrapped_type==TYPE]
    need('own-four-Param-members',[(m.name,m.declared_type)for m in wrapper.members]==
        [('constValue',VALUE),('idRef','int'),('paramSource','int'),('path','string')])
    need('own-wrapper-holder',ctx.field(wrapper.name+'::__instance')==(wrapper.name,TYPE,16))
    methods=pointer.methods(image,wrapper);bodies={};records={};setters={}
    for name in('.ctor','CreateInstance','Deserialize',*('set___'+m.name+'__'for m in wrapper.members)):
        method=methods[name];target=image.method_pointer_va(method)
        bodies[name]=pointer.owned(image,target);records[name]=_record(image,target,method.index)
        if name=='Deserialize':primitive.reader_abi(image,ctx,method,wrapper)
        else:
            field=name[6:-2]if name.startswith('set___')else None
            spec={'constValue':(VALUE,17,False),'idRef':('int',8,False),'paramSource':('int',8,False),'path':('string',14,True)}
            scalar.owned_method_abi(image,ctx,method.index,wrapper.type_definition,('void',1,False),
                [spec[field]]if field else[],'quaternionParam')
            if field:setters[field]=setter_program(bodies[name]['regions'],target,field=field)
    occupied=[i for p in setters.values()for i in range(p['compiledFieldOffset'],p['compiledFieldOffset']+p['storedBytes'])]
    need('all-compiled-fields-disjoint',len(occupied)==32 and len(set(occupied))==32)
    body=bodies['Deserialize'];programs=[reader_program(body['regions'],body['pointer'],existing=e,null=n)for e in(False,True)for n in(False,True)]
    positive=programs[0];calls=positive['calls'];existing=programs[2]
    need('same-both-positive-source-callees',all(existing['calls'].get(k)==v for k,v in calls.items()if k not in('allocateWrapper','wrapperConstructor','outputBarrier')))
    for field in setters:
        role='set'+field[0].upper()+field[1:]
        need('same-actual-named-setter:'+field,calls[role]['targetVa']==base+records['set___'+field+'__']['pointerRva'])
    factories={};allocations={}
    reference=_reference_join(image,pins,VALUE)
    for name in('.ctor','CreateInstance'):
        body_=bodies[name];program=factory_program(body_['regions'],body_['pointer'],id_ref_offset=setters['idRef']['compiledFieldOffset'])
        usage=derive_typed_usage_context(image,program['allocationInstructionVa']-base,label='quaternionParam.Original')
        need('own-typed-Original-allocation',usage.get('tag')==1 and type(usage['tag'])is int and usage.get('typeName')==TYPE)
        pointer_=ctx.type_pointer(usage['typeIndex']);carrier=closed_generic_reference_pointer_extent(ctx,pointer_)
        need('same-closed-Original-carrier',carrier['type']==TYPE and carrier['argumentTypes']==[VALUE]
            and carrier['bytes']==8 and carrier['definitionTypeIndex']==reference['closedCarrier']['definitionTypeIndex'])
        raw=bytes.fromhex(carrier['declaredTypeRecordHex']);expected=bytes.fromhex(reference['closedCarrier']['declaredTypeRecordHex'])
        need('same-actual-GenericClass-pointer-and-carrier-markers',len(raw)==len(expected)==16
            and raw[:8]==expected[:8]and raw[10:12]==expected[10:12]==bytes((21,0)))
        factories[name]=program;allocations[name]=dict(usage=usage,carrier=carrier)
    allocation=positive['wrapperAllocation'];usage=derive_typed_usage_context(image,allocation['instructionVa']-base,label='quaternionParam.wrapper')
    need('own-typed-wrapper-allocation',usage.get('tag')==1 and usage.get('typeName')==wrapper.name
        and allocation['constructorVa']==base+records['.ctor']['pointerRva'])
    need('same-both-Original-type-cells',len({row['usage']['usageCellRva']for row in allocations.values()})==1)
    need('same-typed-allocator',all(p['allocatorTargetVa']==allocation['allocatorTargetVa']for p in factories.values()))
    barrier=setters['path']['barrierTargetVa']
    need('same-collector-reference-barrier',all(p['barrierTargetVa']==barrier for p in factories.values())
        and all(p['calls']['nullBarrier']['targetVa']==barrier for p in programs if p['null'])
        and calls['outputBarrier']['targetVa']==barrier)
    from scripts.game_data.memorypack.skill_passive_map_sources import _barrier
    collector=_barrier(image,barrier)
    offsets=scalar.reader_offsets(image,'quaternionParam');header=_record(image,calls['header']['targetVa']);primitive.object_header_source(image,header,offsets)
    need('same-two-int32-readers',calls['idRef']['targetVa']==calls['paramSource']['targetVa'])
    integer=_record(image,calls['idRef']['targetVa']);scalar.integer_source(image,integer,offsets,'quaternionParam.integer')
    pooled=pooled_source_helper.validate_on_image(image,calls['path']['targetVa'],pins)
    constant=child.derive(image,pins,source_target=calls['constValue']['targetVa'])
    forward=constant['proof']['forwarderProgram']
    need('complete-hidden16-constant-return',constant['wireBytes']==16 and constant['typeName']==VALUE
        and all(forward.get(k)is True for k in('sameIncomingOutputRcx','sameIncomingReaderRdx','sameOutputReturnedInRax','fullFrameAndNonvolatilesRestored')))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(nativeInputs=pins,typeName=TYPE,wrapperName=wrapper.name,programs=programs,
        factories=factories,allocationSources=allocations,wrapperAllocation=usage,ownedMethods=records,setters=setters,
        constantSource=constant,headerSource=header,integerSource=integer,pooledSource=pooled,canonicalReference=reference,
        collector=collector,
        fourPathSourceProved=True,wholeOwnerAdmitted=False,runtimeEvaluationAdmitted=False)))
