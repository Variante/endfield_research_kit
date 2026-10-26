"""Conditional current Unity AnimationCurve new/existing/FF source component.

This is UnityEngine.AnimationCurve with seven-word Keyframe28 storage, distinct
from Beyond's value curves and their managed ABI. Complete own custom formatter
paths copy wrap words and signed nullable key count, allocate typed fresh key
arrays/curve objects, store the named Internal_Create result in m_Ptr and pass
the original wrap/key arguments to exact named icall-resolution caches. The
existing-output path and FF clear are independently proved. Normal matching
provider/slot5/icall callbacks and helper ABI, coherent metadata/caches, disabled
collector, compatible allocations and buffered disjoint storage are conditions.
Callback execution, interpolation/evaluation, cold/refill/error parity, runtime
provider/inflation choice and enclosing owner/physical EOF remain unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.skill_root_child_bindings import need

SCHEMA='endfield.skill-animation-curve-sources.v1'
TYPE='UnityEngine.AnimationCurve'
CAPABILITY='skill-animation-curve'
ICALLS={
 'create':('Internal_Create','UnityEngine.AnimationCurve::Internal_Create(UnityEngine.Keyframe[])',True,'nint',['UnityEngine.Keyframe[]']),
 'wrap0':('set_preWrapMode','UnityEngine.AnimationCurve::set_preWrapMode(UnityEngine.WrapMode)',False,'void',['UnityEngine.WrapMode']),
 'wrap1':('set_postWrapMode','UnityEngine.AnimationCurve::set_postWrapMode(UnityEngine.WrapMode)',False,'void',['UnityEngine.WrapMode']),
 'keys':('SetKeys','UnityEngine.AnimationCurve::SetKeys(UnityEngine.Keyframe[])',False,'void',['UnityEngine.Keyframe[]']),
}


def cache_binding(regions,entry,*,cache_cell,argument_entry,resolver_nonnull_guard=False):
    """Full cold literal/resolver/store path rejoins the actual argument setup."""
    need('curve-literal-resolver-guard',True,type(resolver_nonnull_guard)is bool)
    g=BytesPath(regions,entry);literal=g.relative('488d0d');resolver=g.relative('e8')
    if resolver_nonnull_guard:g.take('4885c0');g.branch('75',True,1)
    need('curve-icall-cache-store',cache_cell,g.relative('488905'))
    if g.bytes.get(g.at)==235:g.jump('eb',1)
    else:g.jump('e9')
    need('curve-icall-exact-argument-join',argument_entry,g.at)
    return dict(selectedBytes=g.seen,literalVa=literal,resolverTargetVa=resolver,
        cacheCellVa=cache_cell,argumentEntryVa=argument_entry,normalResolverReturnRequired=True,
        selectedResolverNonNullGuardProved=resolver_nonnull_guard)


def count_induction(programs,*,count_limit):
    """Induct on the source-owned R13 count and independent R12 array guard."""
    need('curve-literal-bounded-count',True,type(count_limit)is int and 2<=count_limit<=10000)
    need('curve-finite-complete-witnesses',[0,1,2],sorted(p['keyCountWitness']for p in programs))
    by={p['keyCountWitness']:p for p in programs}
    need('curve-same-nonnull-callback-source',True,all(p.get('null')is False and p.get('memberCount')==3
        and p.get('keyWireBytes')==28 for p in programs))
    rows=[(a,h.lower())for a,h in by[1]['selectedBytes']];loop=by[1]['loopEntry']
    indices=[i for i,(at,h)in enumerate(rows)if at==loop];need('curve-one-source-loop-entry',1,len(indices));begin=indices[0]
    edges=[]
    for i,(at,h)in enumerate(rows[:-1]):
        if h!='0f8c':continue
        operand_at,operand=rows[i+1];raw=bytes.fromhex(operand)
        if len(raw)==4 and operand_at==at+2 and at+6+int.from_bytes(raw,'little',signed=True)==loop:edges.append(i+1)
    need('curve-one-signed-loop-backedge',1,len(edges));end=edges[0]
    prefix,body,suffix=rows[:begin],rows[begin:end+1],rows[end+1:]
    need('curve-complete-tail-callback-frame',True,bool(prefix)and bool(body)and bool(suffix)and suffix[-1][1]=='48ffe0')
    need('curve-identical-two-iteration-program',prefix+body*2+suffix,[(a,h.lower())for a,h in by[2]['selectedBytes']])
    need('curve-exact-two-counters',True,sum(h=='41ffc4'for a,h in body)==1
        and sum(h=='49ffc5'for a,h in body)==1 and body[-3][1]=='4c3b6c2430'
        and sum(h=='48897c2430'for a,h in prefix)==1 and sum(h=='33f6'for a,h in prefix)==1
        and sum(h=='448be6'for a,h in prefix)==1 and sum(h=='4c8bee'for a,h in prefix)==1)
    need('curve-complete-key-source-and-destination-step',True,sum(h=='4983c71c'for a,h in body)==1
        and sum(h=='488343501c'for a,h in body)==1 and sum(h=='837b301c'for a,h in body)==1)
    return dict(schema='endfield.unity-curve-key-induction.v1',countLimit=count_limit,positiveCountRange=[1,count_limit],
        loopEntry=loop,body=body,witnessCounts=[0,1,2],countCounter='r13',arrayIndexCounter='r12d',savedSignedCount='entry RSP+48',
        byteIdenticalStepProved=True,noCounterOverflow=count_limit<2**31-1,
        invariant='At entry i=R13=R12D, 0<=i<count; the independently source-proved body consumes exactly28 bytes, stores the seven owned Keyframe words, advances the destination28 and increments both counters once. Signed R13 comparison repeats iff i+1<count. Count is sign-extended Int32, saved once; bounded positive count prevents counter overflow.',
        condition='The complete source walker proves every selected operation, initialization, guard, unchanged saved count, frame and tail callback argument. Normal exact typed allocation, per-step buffered source, compatible arrays, noninterference and callback ABI are required; growth/refill/error and runtime callbacks gain no admission.')


def resolver_roles(bindings):
    """Distinct guarded create lookup and common normal setter resolver."""
    need('curve-exact-four-callback-roles',set(ICALLS),set(bindings))
    regular={bindings[role]['resolverTargetVa']for role in('wrap0','wrap1','keys')}
    need('curve-three-standard-icall-resolvers',1,len(regular));standard=next(iter(regular))
    create=bindings['create']['resolverTargetVa']
    need('curve-distinct-guarded-create-resolver',True,type(create)is int and type(standard)is int and create!=standard)
    need('curve-exact-resolver-null-guard-shapes',True,all(bindings[role].get('selectedResolverNonNullGuardProved')is(role=='create')for role in ICALLS))
    return dict(guardedCreateLookupTargetVa=create,standardSetterResolverTargetVa=standard,
        pointerAliasClaimed=False,resolverLookupEffectsProved=False)


def derive(image,pins,*,count_limit=10000):
    """Fresh own callback/nominal/actual Reader joins without a wrapper alias."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context,_vtable
    from scripts.game_data.il2cpp.formatter_value_paths import deserialize_slot
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import animation_curve_source as existing,modelview_curve_sources as fresh
    from scripts.game_data.memorypack import scalar_param_native as scalar
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_reader_abi
    from scripts.game_data.memorypack.skill_shared_sequence_sources import _fast_barrier
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base
    old=existing.derive(image,pins);method=md.methods[old['sourceMethod'][0]]
    need('curve-custom-formatter-nominal-base','MemoryPack.MemoryPackFormatter`1<'+TYPE+'>',ctx.parent(old['sourceMethod'][1]))
    need('curve-own-custom-slot-ABI',(False,'void',2,5),(bool(method.flags&16),ctx.type_name(method.return_type),method.parameter_count,method.slot))
    _vtable(image,method.declaring_type,5,method.index,'skillAnimationCurve')
    for parameter,typename,kind in zip(md.parameters_for(method),('MemoryPack.MemoryPackReader',TYPE),(17,18),strict=True):
        raw=image.pe.bytes_at_va(ctx.type_pointer(parameter.type_index),16)
        need('curve-own-formatter-byrefs',(typename,bytes((kind,32))),(ctx.type_name(parameter.type_index),raw[10:12]))
    body=owned(image,base+old['sourceMethod'][3]);rows=body['rows']
    def before_move(text):
        calls={control_transfer(row)['target']for i,row in enumerate(rows[:-1])if bytes.fromhex(row['bytes'])[:1]==b'\xe8'
            and rows[i+1]['text']==text}
        need('curve-one-allocator-before:'+text,1,len(calls));return next(iter(calls))
    symbols=dict(allocate=before_move('mov rbx, rax'),arrayAllocate=before_move('mov rbp, rax'),barrier=base+old['nullBarrierTargetRva'])
    programs=[fresh.unity_curve(body['regions'],body['pointer'],old['readerOffsets'],symbols,null=null,keys=count)
        for null,count in((True,0),(False,-1),(False,0),(False,1),(False,2))]
    positive=programs[-1];certificate=count_induction(programs[2:],count_limit=count_limit)
    typed={name:derive_typed_usage_context(image,at-base,label='skillAnimationCurve.allocation')for name,at in positive['allocations'].items()}
    for role,usage in typed.items():
        need('curve-exact-typed-allocation',(1,'UnityEngine.Keyframe[]'if role=='keyArrayUsage'else TYPE),(usage['tag'],usage['typeName']))
    need('curve-exact-owned-native-pointer',(TYPE,'nint',16),ctx.field(TYPE+'::m_Ptr'))
    fd,=[f for f in md.fields_for(ctx.index.types[TYPE])if md.string(f.name_index)=='m_Ptr']
    scalar.ordinary(image,ctx.type_pointer(fd.type_index),24,'skillAnimationCurve.m_Ptr')
    bindings={};callee_abis={}
    for role,(name,literal,static,result,parameters)in ICALLS.items():
        cell=positive['cells'][role];loads=[]
        for i,row in enumerate(rows[:-2]):
            raw=bytes.fromhex(row['bytes'])
            if len(raw)!=7 or raw[:3]!=b'\x48\x8b\x05' or existing.rip_target(row)!=cell:continue
            need('curve-icall-cache-test',b'\x48\x85\xc0',bytes.fromhex(rows[i+1]['bytes']))
            edge=control_transfer(rows[i+2]);need('curve-icall-cache-null-edge',('conditional',4),(edge['kind'],edge['conditionCode']))
            loads.append((edge['target'],int(rows[i+2]['va'],16)+len(bytes.fromhex(rows[i+2]['bytes']))))
        need('curve-one-exact-icall-cache:'+role,1,len(loads));entry,join=loads[0]
        binding=cache_binding(body['regions'],entry,cache_cell=cell,argument_entry=join,resolver_nonnull_guard=role=='create')
        need('curve-exact-icall-name:'+role,literal,image.pe.c_string_at_va(binding['literalVa']));bindings[role]=binding
        chosen,=[m for m in md.methods_for(ctx.index.types[TYPE])if md.string(m.name_index)==name
            and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==parameters]
        need('curve-named-icall-formal-ABI:'+role,(static,result),(bool(chosen.flags&16),ctx.type_name(chosen.return_type)))
        need('curve-nongeneric-named-icall',True,chosen.generic_container_index<0)
        signature=[chosen.return_type,*[p.type_index for p in md.parameters_for(chosen)]]
        kinds={'void':(1,False),'nint':(24,False),'UnityEngine.WrapMode':(17,False),'UnityEngine.Keyframe[]':(29,True)}
        for ordinal,(index,typename)in enumerate(zip(signature,[result,*parameters],strict=True)):
            kind,reference=kinds[typename]
            scalar.ordinary(image,ctx.type_pointer(index),kind,'skillAnimationCurve.'+role+'.formal'+str(ordinal),reference=reference)
        callee_abis[role]=dict(methodDefinition=chosen.index,ownerType=TYPE,methodName=name,static=static,returnType=result,parameterTypes=parameters,
            signatureTypeRecordHex=[image.pe.bytes_at_va(ctx.type_pointer(index),16).hex().upper()for index in signature])
    resolvers=resolver_roles(bindings)
    resolver_windows={str(target-base):owned(image,target)['windows']for target in
        (resolvers['guardedCreateLookupTargetVa'],resolvers['standardSetterResolverTargetVa'])}
    reader=reference_reader_abi(image,pins);dispatch=owned(image,reader['referenceClones']['dispatchTarget'])
    prepare,={control_transfer(r)['target']for r in dispatch['rows']if bytes.fromhex(r['bytes'])[:1]==b'\xe8'
        and int(r['va'],16)<dispatch['pointer']+80}
    transfer=deserialize_slot(dispatch['regions'],dispatch['pointer'],prepare=prepare,callback=body['pointer'])
    barrier_windows,barrier_proof,_=_fast_barrier(image,symbols['barrier'])
    cap=dict(typeName=TYPE,formatterTypeName=old['sourceMethod'][1],memberCount=3,nullAdmitted=True,nullable=True,
        nullMarker=255,wholeGrammarAdmitted=True,ordinaryOriginalReadValueAdmitted=True,
        ownConcreteFactorySemanticsProved=True,customFormatterWritesOriginalDirectly=True,
        keyframeTypeName='UnityEngine.Keyframe',keyframeBytes=28,keyframeFields=old['keyframeFields'],
        collectionCounts=[-1,0],countLimit=count_limit,positiveCountsAdmitted=True,keyLoopInductionProved=True,
        **{key:reader[key]for key in('referenceReaderMethodDefinition','referenceReaderTargetRva')},
        callbackSelectionConditional=True,wholeSkillDataAdmitted=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='validated-conditional-unity-animation-curve',nativeInputs=pins,
        capabilities={CAPABILITY:cap},requiredExternalCapabilities=[],proof=dict(existingOutput=old,newOutputPrograms=programs,
            countInduction=certificate,typedAllocations=typed,icallBindings=bindings,icallFormalABIs=callee_abis,
            resolverRoles=resolvers,resolverWindows=resolver_windows,
            dispatchWindows=dispatch['windows'],dispatchTransfer=transfer,referenceReaders=reader,
            barrierWindows=barrier_windows,barrierProof=barrier_proof),wholeSkillDataAdmitted=False,
        evidenceBoundary=dict(exact='Own selected Unity custom formatter complete existing/new/FF output programs, Keyframe28 layout and bounded count induction, named typed allocations/native pointer store, exact icall caches/formal ABIs and actual ordinary reference Reader/slot5 transfer.',
            conditional=__doc__,direct='Wrap/key arguments reach exact named callback-resolution caches; callbacks are not executed.',
            structuralOnly='Stored Unity curve words.',unresolved=['runtime formatter/provider/icall selection and execution','curve evaluation/interpolation','normal allocation/import/helper effects','cold/refill/error paths','enclosing owner/physical EOF']))))
