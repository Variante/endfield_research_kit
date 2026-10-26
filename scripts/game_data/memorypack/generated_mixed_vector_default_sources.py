"""One current scalar default and broadcast Vector3 in cached factories.

The scalar store is an exact DWORD at a positive disp32. Its field identity
and bits must be joined to the independent current Original constructor.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedMixedVectorDefaultSource'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _scalar(g,receiver):
    at=g.at;g.take({'rcx':'c781','rax':'c780'}[receiver])
    offset=int.from_bytes(g.read(4),'little',signed=True)
    need('positive-owned-disp32-DWORD',128<=offset<2**31)
    value=g.read(4)
    return dict(instructionVa=at,offset=offset,bytes=4,constantHex=value.hex().upper())


def _vector(g,receiver):
    suffix={'rcx':'41','rax':'40'}[receiver]
    g.take('f20f11'+suffix);offset=int.from_bytes(g.read(1),'little',signed=True)
    g.take('f30f11'+{'rcx':'51','rax':'50'}[receiver]);last=int.from_bytes(g.read(1),'little',signed=True)
    need('whole-contiguous-Vector3',16<=offset<=119 and last==offset+8)
    return offset


def leaf_program(data,entry):
    need('bounded-owned-Original-entry',type(data)is bytes and 0<len(data)<=128 and type(entry)is int)
    g=BytesPath([(entry,data)],entry);site=g.at;constant=g.relative('f30f1015');scalar=_scalar(g,'rcx')
    g.take('0f28c2','0f14c2');field=_vector(g,'rcx');g.take('c3')
    need('disjoint-scalar-and-vector',scalar['offset']>=field+12)
    return dict(selectedBytes=g.seen,programBytes=g.at-entry,constantInstructionVa=site,constantAddress=constant,
        fieldOffset=field,managedFieldBytes=12,sourceSingleLanes=[0,0,0],storedFieldSlices=[[0,8],[8,4]],
        scalarDefaultInitialization=scalar,everySingleBitPreserved=True,callFree=True,normalReturn=True,
        sameReceiverRcx=True,stackUnchanged=True,
        integerRegistersPreserved=['rcx','rdx','r8','r9','rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        volatileVectorWrites=['xmm0','xmm2'],physicalFunctionExtentProved=False)


def program(regions,entry,barrier,*,ctor,base_slot,cache_slot,base_ctor=None):
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('finite-current-holder-domain',type(ctor)is bool and 16<=base_slot<cache_slot<128)
    need('independent-base-constructor',not ctor or type(base_ctor)is int and base_ctor>0)
    b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g=BytesPath(regions,entry)
    if ctor:g.take('4057','4883ec20')
    else:g.take('48895c2408','57','4883ec30')
    flag=lifecycle._direct_flag(g,'803d');g.take('488bf9');lifecycle._initialized(g)
    ancestor=None
    if ctor:
        at=g.at;ancestor=dict(site=at,cell=g.relative('488b0d'));g.take('83b9e000000000');lifecycle._initialized(g)
        g.take('33d2','488bcf');g.call(base_ctor)
    at=g.at;allocation=dict(site=at,cell=g.relative('488b0d'));allocator=g.relative('e8')
    g.take('488bd0','4885c0');lifecycle._nonnull(g)
    if ctor:
        constant=g.relative('f30f1015');g.take('48895c2430');scalar=_scalar(g,'rax')
        g.take('0f28c2','4533c0','0f14c2','488bcf');field=_vector(g,'rax')
        vector=dict(mode='inline-broadcast-Single',constantAddress=constant,fieldOffset=field,
            bytes=12,storedSlices=[[0,8],[8,4]],everySingleBitPreserved=True)
    else:
        g.take('488d4c2420');scalar=_scalar(g,'rax');site=g.at;helper=g.relative('e8')
        g.take('4533c0','8b4808','f20f1000','f20f1142');field=int.from_bytes(g.read(1),'little',signed=True)
        g.take('894a');last=int.from_bytes(g.read(1),'little',signed=True)
        need('whole-helper-Vector3',16<=field<=119 and last==field+8);g.take('488bcf')
        vector=dict(mode='owned-hidden-Vector3-helper',helperTarget=helper,helperCallVa=site,outputLocal=32,
            allocatedOriginalRegister='rdx',fieldOffset=field,bytes=12,storedSlices=[[0,8],[8,4]],everySingleBitPreserved=True)
    need('disjoint-scalar-and-vector',scalar['offset']>=field+12)
    setter=g.relative('e8');g.take('488b5f'+b);usages=[];casts=[]
    for index in range(2):
        at=g.at;usages.append(dict(site=at,cell=g.relative('488b15')))
        if not index:g.take('488bcb')
        casts.append(g.relative('e8'))
        if not index:g.take('488947'+c,'488bcb')
    need('same-current-allocation-and-both-casts',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
    g.take('488d4f'+c,'488b5c2430'if ctor else'488b5c2440','4883c420'if ctor else'4883c430','5f')
    need('same-restored-tail-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,initializedFlag=flag,constructor=ctor,allocation=allocation,
        allocationTarget=allocator,baseClassUsage=ancestor,baseReady=None,baseConstructorTarget=base_ctor if ctor else None,
        instanceSetter=setter,inlineHolderWrites=None,strictCast=casts[0],classUsages=usages,
        baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,
        originalConstructorTarget=None,originalConstructorEffectsProved=False,normalReturnViaBarrier=True,
        vectorDefaultInitialization=vector,scalarDefaultInitialization=scalar,
        factoryProfile='cached-one-disp32-DWORD-and-broadcast-Vector3.v1',
        entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'])
