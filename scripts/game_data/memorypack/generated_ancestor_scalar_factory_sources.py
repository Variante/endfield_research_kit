"""Cached factories with an owned ancestor call and early EBX defaults.

Every exact BYTE/WORD/DWORD store must equal independently proved Original
constructor defaults. The actual typed allocation, ancestor constructor,
holder setter and repeated same-class casts remain independent native joins.
The EBX constant is preserved across ordinary Win64 calls, then its entry
home is restored before the disabled barrier tail. No wire grammar follows.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

PROFILE='ancestor-called-early-ebx-mixed-defaults.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('generatedAncestorScalarFactory.'+check+':'+str(detail)[:700])


def program(regions,entry,barrier,*,ctor,base_slot,cache_slot,initializers,base_ctor=None):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _direct_flag,_initialized,_nonnull,_peek
    need('literal-owned-factory-role',type(ctor)is bool and type(base_slot)is int and type(cache_slot)is int
        and 16<=base_slot<cache_slot<128 and(type(base_ctor)is int and base_ctor>0 if ctor else base_ctor is None))
    need('finite-independent-scalar-defaults',isinstance(initializers,list)and 0<len(initializers)<=32)
    expected={};occupied=set()
    for store in initializers:
        offset,width,bits=store.get('offset'),store.get('bytes'),store.get('constantHex')
        need('exact-current-default-declaration',type(offset)is int and 16<=offset<2**31 and type(width)is int and width in(1,2,4)
            and isinstance(bits,str)and len(bytes.fromhex(bits))==width)
        span=set(range(offset,offset+width));need('disjoint-current-defaults',not occupied&span);occupied.update(span)
        expected[offset,width]=bytes.fromhex(bits)
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20')
    flag=_direct_flag(g,'803d');g.take('488bf9','bb');ebx=g.read(4);_initialized(g)
    ancestor=None;ready=None
    if ctor:
        at=g.at;cell=g.relative('488b0d');ancestor=dict(site=at,cell=cell)
        if _peek(g,2)==bytes.fromhex('83b9'):g.take('83b9e000000000');_initialized(g)
        else:ready=g.relative('e8')
        g.take('33d2','488bcf');g.call(base_ctor)
    at=g.at;cell=g.relative('488b0d');allocation=dict(site=at,cell=cell);allocate=g.relative('e8')
    g.take('4885c0');_nonnull(g);arguments=set();stores=[];steps=0
    while expected or arguments!={'rdx','rcx','r8'}:
        steps+=1;need('bounded-complete-default-argument-program',steps<=64)
        at=g.at;prefix=_peek(g,3)
        if prefix==bytes.fromhex('4533c0'):
            g.take('4533c0');need('one-zero-MethodInfo','r8'not in arguments);arguments.add('r8');continue
        if prefix==bytes.fromhex('488bd0'):
            g.take('488bd0');need('one-whole-allocation-argument','rdx'not in arguments);arguments.add('rdx');continue
        if prefix==bytes.fromhex('488bcf'):
            g.take('488bcf');need('one-preserved-wrapper-argument','rcx'not in arguments);arguments.add('rcx');continue
        if prefix[0]in(0x88,0x89)and prefix[1]in(0x58,0x98):
            width=1 if prefix[0]==0x88 else 4;g.take(prefix[:2].hex())
            offset=int.from_bytes(g.read(1 if prefix[1]==0x58 else 4),'little',signed=True);bits=ebx[:width]
        else:
            width=2 if prefix[0]==0x66 else 1 if prefix[0]==0xc6 else 4
            if width==2:g.take('66')
            g.take('c6'if width==1 else'c7');modrm=g.read(1)[0]
            need('same-allocated-Original-immediate-store',modrm in(0x40,0x80))
            offset=int.from_bytes(g.read(1 if modrm==0x40 else 4),'little',signed=True);bits=g.read(width)
        key=offset,width;need('same-current-Original-default-bits',key in expected and bits==expected[key],
            dict(actual=[offset,width,bits.hex()],remaining=[[o,w,b.hex()]for(o,w),b in expected.items()]))
        stores.append(dict(instructionVa=at,offset=offset,bytes=width,constantHex=bits.hex().upper()));del expected[key]
    setter=g.relative('e8');b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g.take('488b5f'+b)
    classes=[];casts=[]
    for index in range(2):
        at=g.at;cell=g.relative('488b15');classes.append(dict(site=at,cell=cell))
        if index==0:g.take('488bcb')
        casts.append(g.relative('e8'))
        if index==0:g.take('488947'+c,'488bcb')
    need('same-allocated-nominal-class-and-actual-cast',len(set(casts))==1 and all(r['cell']==allocation['cell']for r in classes))
    g.take('488d4f'+c,'488b5c2430','4883c420','5f');need('same-restored-barrier-tail',g.relative('e9')==barrier)
    result=dict(selectedBytes=g.seen,factoryProfile=PROFILE,initializedFlag=flag,constructor=ctor,allocation=allocation,
        allocationTarget=allocate,baseClassUsage=ancestor,baseReady=ready,instanceSetter=setter,strictCast=casts[0],
        classUsages=classes,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,originalConstructorCalled=False,
        originalConstructorTarget=None,originalConstructorEffectsProved=False,inlinedOriginalInitializers=initializers,
        registerDefaultStores=stores,defaultConstantRegister='ebx',normalReturnViaBarrier=True,entryRspRestored=True,
        nonvolatileRegistersRestored=['rbx','rdi'],condition=__doc__)
    if ctor:result['baseConstructorTarget']=base_ctor
    return result
