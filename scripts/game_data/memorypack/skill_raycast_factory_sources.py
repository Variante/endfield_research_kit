"""Finite RayCast zero-vector/default construction with a typed hidden helper.

Original and wrapper constructors explicitly zero named Vector3 fields and
store captured scalar constants. CreateInstance uses the independently owned
Vector3.get_zero reachable leaf, whose twelve output bytes are zero and whose
unchanged RDX preserves the live fresh Original across each call. Every complete
8+4 copy targets its own named current field; scalar bits must match the owned
Original constructor. None of these defaults supplies wire framing. Ready
metadata, normal typed zeroed allocation, disabled collector and disjoint stable
Original/wrapper/frame storage remain conditions. Helper/runtime selection and
enclosing action/root/EOF remain unresolved; physical leaf extent is unclaimed.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag
from scripts.game_data.memorypack.skill_root_child_bindings import need

PREFIX='Beyond.Gameplay.Core.RayCastEffectAction+'
PLANS={
 PREFIX+'CurveRayData':dict(constants=('sourcePosType',),vectors=('startPosOffset','endPosOffset'),
    original=('c:sourcePosType','z2','z0','v:startPosOffset','z0','v:endPosOffset'),
    wrapper=('c:sourcePosType','z2','z0','v:startPosOffset','z0','holder','v:endPosOffset'),
    factory=('scratch','a:sourcePosType','v:startPosOffset','scratch','v:endPosOffset','holder')),
 PREFIX+'MountPointRayData':dict(constants=(),vectors=('startPosOffset',),
    original=('z2','z0','v:startPosOffset'),wrapper=('z2','z0','holder','v:startPosOffset'),
    factory=('scratch','v:startPosOffset','holder')),
 PREFIX+'PointToPointRayData':dict(constants=('sourcePosType','targetPosType','groundCheckDistance'),vectors=('startPosOffset','endPosOffset'),
    original=('c:sourcePosType','z2','z0','c:targetPosType','v:startPosOffset','z0','c:groundCheckDistance','v:endPosOffset'),
    wrapper=('c:sourcePosType','z2','z0','c:targetPosType','v:startPosOffset','c:groundCheckDistance','holder','z0','v:endPosOffset'),
    factory=('scratch','a:sourcePosType','v:startPosOffset','scratch','d:targetPosType','v:endPosOffset','holder','d:groundCheckDistance')),
 PREFIX+'RaycastData':dict(constants=('rayDirectionType','angleVelocity'),vectors=('startAngleOffset',),
    original=('c:rayDirectionType','z2','z0','c:angleVelocity','v:startAngleOffset'),
    wrapper=('c:rayDirectionType','z2','c:angleVelocity','holder','z0','v:startAngleOffset'),
    factory=('scratch','a:rayDirectionType','v:startAngleOffset','holder','d:angleVelocity')),
}


def _offset(slots,name,*,vector=False):
    value=slots[name];need('raycast-factory-positive-disp8',True,type(value)is int and 16<=value and value+(8 if vector else 0)<128)
    return bytes((value,)).hex()


def zero_program(data,entry):
    g=BytesPath([(entry,data)],entry)
    g.take('0f57d2','0f57c0','0f14c2','f20f1101','f30f115108','488bc1','c3')
    return dict(selectedBytes=g.seen,programBytes=g.at-entry,zeroOutputBytes=12,outputSlices=[[0,8],[8,4]],
        sameOutputRcxReturnedInRax=True,originalRdxUnchanged=True,stackAndNonvolatilesUnchanged=True,
        hiddenOutputRegister='rcx',normalReturn=True,physicalExtentProved=False)


def _inline_defaults(g,plan,slots,role):
    constants=[];vectors=[];zero2=False;zero0=False;holder=False
    for op in plan[role]:
        if op=='z2':g.take('0f57d2');zero2=True
        elif op=='z0':g.take('0f57c0');zero0=True
        elif op=='holder':g.take('488d4b10');holder=True
        elif op.startswith('c:'):
            name=op[2:];at=g.at;g.take(('c741'if role=='original'else'c740')+_offset(slots,name));bits=g.read(4).hex().upper()
            constants.append(dict(fieldName=name,instructionVa=at,offset=slots[name],bytes=4,constantHex=bits))
        else:
            need('raycast-explicit-vector-operation',True,op.startswith('v:')and zero2 and zero0);name=op[2:];at=g.at
            g.take('0f14c2',('f20f1141'if role=='original'else'f20f1140')+_offset(slots,name,vector=True),
                ('f30f1151'if role=='original'else'f30f1150')+bytes((slots[name]+8,)).hex())
            vectors.append(dict(fieldName=name,instructionVa=at,offset=slots[name],bytes=12,zeroBits=True,storeSlices=[[0,8],[8,4]]))
    need('raycast-complete-default-scope',(list(plan['constants']),list(plan['vectors'])),
        ([r['fieldName']for r in constants],[r['fieldName']for r in vectors]))
    return constants,vectors,holder


def original_program(data,entry,name,slots):
    need('raycast-finite-default-plan',True,name in PLANS);g=BytesPath([(entry,data)],entry)
    constants,vectors,holder=_inline_defaults(g,PLANS[name],slots,'original');need('raycast-original-no-wrapper-holder',False,holder);g.take('c3')
    return dict(selectedBytes=g.seen,programBytes=g.at-entry,constantFields=constants,zeroVectorFields=vectors,
        sameOriginalRcx=True,normalReturn=True,stackAndNonvolatilesUnchanged=True,callFree=True,physicalExtentProved=False,wireBytes=0)


def wrapper_program(regions,entry,name,slots,s):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _initialized,_nonnull
    need('raycast-finite-default-plan',True,name in PLANS);g=BytesPath(regions,entry)
    g.take('4053','4883ec20');ready=flag(g,prefix='803d');g.take('488bd9');_initialized(g)
    at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('4885c0');_nonnull(g)
    constants,vectors,holder=_inline_defaults(g,PLANS[name],slots,'wrapper');need('raycast-one-prepared-holder',True,holder)
    g.take('48894310','4883c420','5b');need('raycast-wrapper-restored-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadata=ready,allocation=dict(site=at,cell=cell),allocationTarget=s['allocate'],
        constantFields=constants,zeroVectorFields=vectors,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,
        entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,wireBytes=0)


def factory_program(regions,entry,name,slots,s):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _initialized,_nonnull
    need('raycast-finite-default-plan',True,name in PLANS);g=BytesPath(regions,entry)
    g.take('4053','4883ec30');ready=flag(g,prefix='803d');g.take('488bd9');_initialized(g)
    at=g.at;cell=g.relative('488b0d');g.call(s['allocate']);g.take('488bd0','4885c0');_nonnull(g)
    constants=[];vectors=[];scratch=False;holder=False
    for op in PLANS[name]['factory']:
        if op=='scratch':g.take('488d4c2420');scratch=True
        elif op=='holder':g.take('488d4b10');holder=True
        elif op[:2]in('a:','d:'):
            field=op[2:];site=g.at;g.take(('c740'if op[0]=='a'else'c742')+_offset(slots,field));bits=g.read(4).hex().upper()
            constants.append(dict(fieldName=field,instructionVa=site,offset=slots[field],bytes=4,constantHex=bits))
        else:
            need('raycast-owned-zero-helper-output-local',True,op.startswith('v:')and scratch);field=op[2:];site=g.at;g.call(s['zero'])
            g.take('8b4808','f20f1000','f20f1142'+_offset(slots,field,vector=True),'894a'+bytes((slots[field]+8,)).hex())
            vectors.append(dict(fieldName=field,helperCallVa=site,helperTarget=s['zero'],offset=slots[field],bytes=12,
                sameOwnedOutputLocalCopied=True,outputLocal=32,originalRegister='rdx',storeSlices=[[0,8],[8,4]]));scratch=False
    need('raycast-one-factory-holder',True,holder and not scratch)
    need('raycast-factory-complete-default-scope',(list(PLANS[name]['constants']),list(PLANS[name]['vectors'])),
        ([r['fieldName']for r in constants],[r['fieldName']for r in vectors]))
    g.take('48895310','4883c430','5b');need('raycast-factory-restored-barrier',s['barrier'],g.relative('e9'))
    return dict(selectedBytes=g.seen,metadata=ready,allocation=dict(site=at,cell=cell),allocationTarget=s['allocate'],
        constantFields=constants,zeroVectorFields=vectors,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,
        ownedHelperRdxPreservationRequired=True,entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True,wireBytes=0)


def bind_defaults(original,program):
    expected={r['fieldName']:(r['offset'],r['bytes'],r['constantHex'])for r in original['constantFields']}
    actual={r['fieldName']:(r['offset'],r['bytes'],r['constantHex'])for r in program['constantFields']}
    need('raycast-exact-constructor-default-bits',expected,actual)
    need('raycast-exact-constructor-vector-fields',
        [(r['fieldName'],r['offset'],r['bytes'],r['storeSlices'])for r in original['zeroVectorFields']],
        [(r['fieldName'],r['offset'],r['bytes'],r['storeSlices'])for r in program['zeroVectorFields']])
    intervals=[set(range(r['offset'],r['offset']+r['bytes']))for r in original['constantFields']+original['zeroVectorFields']]
    need('raycast-disjoint-owned-default-fields',True,all(not a&b for i,a in enumerate(intervals)for b in intervals[i+1:]))


def prove(image,ctx,wrapper,body,symbols,original_ctor):
    if wrapper.wrapped_type not in PLANS:return NotImplemented
    from scripts.game_data.memorypack.skill_raycast_record_sources import RECORDS
    if wrapper.name!=RECORDS[wrapper.wrapped_type]['wrapperName']:return NotImplemented
    from scripts.game_data.memorypack import generated_member_sources as members,generated_lifecycle_sources as life,generated_vector_member_sources as vector,scalar_param_native as scalar
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    name=wrapper.wrapped_type;md=image.metadata;base=image.pe.image_base;td=ctx.index.types[name];plan=PLANS[name]
    need('raycast-named-owned-original-ctor',True,original_ctor is not None and original_ctor.declaring_type==td.index
        and md.string(original_ctor.name_index)=='.ctor'and original_ctor.parameter_count==0 and original_ctor.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,original_ctor.index,td.index,('void',1,False),[],'raycastFactory.originalCtor')
    fields={key:ctx.field(name+'::'+key)for key in(*plan['constants'],*plan['vectors'])};slots={key:row[2]for key,row in fields.items()}
    for key in plan['vectors']:
        need('raycast-exact-default-vector-field',('UnityEngine.Vector3',slots[key]),fields[key][1:])
        field,=[f for f in md.fields_for(td)if md.string(f.name_index)==key]
        scalar.ordinary(image,ctx.type_pointer(field.type_index),17,'raycastFactory.vectorField')
    layout=vector.layout(image,ctx,'UnityEngine.Vector3')
    zero_td=ctx.index.types['UnityEngine.Vector3'];zero,=[m for m in md.methods_for(zero_td)if md.string(m.name_index)=='get_zero']
    need('raycast-exact-static-zero-value-ABI',True,bool(zero.flags&16)and zero.parameter_count==0 and zero.generic_container_index<0
        and ctx.type_name(zero.return_type)=='UnityEngine.Vector3')
    scalar.ordinary(image,ctx.type_pointer(zero.return_type),17,'raycastFactory.zeroReturn');zero_at=image.method_pointer_va(zero)
    zero_source=zero_program(image.pe.bytes_at_va(zero_at,128),zero_at)
    zero_proof=dict(method=life._method_row(image,zero),program=zero_source,layout=layout,
        codeWindow=_window(image,zero_at,zero_at+zero_source['programBytes'],'complete reachable zero-vector helper entry; physical extent unproved'))
    original_at=image.method_pointer_va(original_ctor);data=image.pe.bytes_at_va(original_at,128)
    original=original_program(data,original_at,name,slots)
    constants=[life._bind_factory_constant(image,ctx,name,row)for row in original['constantFields']]
    constructor=dict(method=life._method_row(image,original_ctor),program=original,constantFieldBindings=constants,
        vectorFieldBindings={key:fields[key]for key in plan['vectors']},vectorLayout=layout,
        codeWindows=[_window(image,original_at,original_at+original['programBytes'],'complete reachable call-free scalar/zero-vector original constructor; physical extent unproved')])
    method,=[m for m in md.methods_for(md.types[wrapper.type_definition])if image.method_pointer_va(m)==body['pointer']
        and md.string(m.name_index)in('.ctor','CreateInstance')]
    role=md.string(method.name_index);s=dict(symbols,zero=zero_at)
    program=(wrapper_program if role=='.ctor'else factory_program)(body['regions'],body['pointer'],name,slots,s)
    bind_defaults(original,program)
    barrier_windows,barrier,_=_fast_barrier(image,symbols['barrier'])
    need('raycast-exact-disabled-collector',symbols['disabled'],base+barrier['disabledFlagRva'])
    return dict(program=program,originalConstructor=constructor,proof=dict(typeName=name,wrapperName=wrapper.name,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalConstructor=constructor,
        actualZeroHelper=zero_proof,barrierWindows=barrier_windows,barrierProgram=barrier,
        freshZeroedAllocationRequired=True,constructorDefaultsSupplyWireFraming=False,condition=__doc__))
