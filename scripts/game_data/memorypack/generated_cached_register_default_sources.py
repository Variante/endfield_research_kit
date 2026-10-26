"""Exact cached factories with post-allocation ECX scalar default reuse.

The complete initialized constructor/CreateInstance path retains one typed
Original allocation in RAX while literal ECX defaults and immediate BYTE/WORD/
DWORD stores interleave with the holder-setter arguments. Every actual store
must equal a separate freshly proved Original-constructor field default. RCX
receiver setup invalidates its former ECX constant; no register or field width
is inferred. The owned setter, both exact same-type casts and restored tail
retain the existing lifecycle's independent nominal/source proofs. No Original
constructor invocation, callback choice or serialized framing is admitted.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='generatedCachedRegisterDefaults'
PROFILE='cached-post-allocation-ecx-mixed-defaults.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+check+':'+str(detail)[:700])


def program(regions,entry,barrier,*,ctor,base_slot,cache_slot,initializers):
    from scripts.game_data.memorypack.generated_lifecycle_sources import _direct_flag,_initialized,_nonnull,_peek
    need('literal-owned-role',type(ctor)is bool and type(base_slot)is int and type(cache_slot)is int and 16<=base_slot<cache_slot<128)
    need('finite-current-defaults',type(initializers)is list and 0<len(initializers)<=32)
    expected={};occupied=set()
    for store in initializers:
        width=store.get('bytes');offset=store.get('offset');bits=store.get('constantHex')
        need('literal-default-declaration',type(width)is int and width in(1,2,4)and type(offset)is int and 16<=offset<2**31
            and type(bits)is str and len(bits)==width*2)
        value=bytes.fromhex(bits);span=set(range(offset,offset+width))
        need('distinct-disjoint-current-defaults',not occupied&span);occupied.update(span);expected[(offset,width)]=value
    g=BytesPath(regions,entry);g.take('48895c2408','57','4883ec20')
    flag=_direct_flag(g,'803d');g.take('488bf9');_initialized(g)
    ancestor=None;ready=None
    if ctor:
        site=g.at;cell=g.relative('488b0d');ancestor=dict(site=site,cell=cell);ready=g.relative('e8')
    site=g.at;cell=g.relative('488b0d');allocation=dict(site=site,cell=cell);allocate=g.relative('e8')
    g.take('4885c0');_nonnull(g)
    # This distinguishes the profile from the established immediate-only and
    # pre-prologue EBX scalar factory programs.
    g.take('b9');ecx=g.read(4);loads=1;register_stores=0;arguments=set();stores=[];steps=0
    while expected or arguments!={'rdx','rcx','r8'}:
        steps+=1;need('bounded-constant-and-argument-program',steps<=64)
        prefix=_peek(g,3);at=g.at
        if prefix[:1]==b'\xb9':g.take('b9');ecx=g.read(4);loads+=1;arguments.discard('rcx');continue
        if prefix==bytes.fromhex('4533c0'):
            g.take('4533c0');need('one-zero-MethodInfo','r8'not in arguments);arguments.add('r8');continue
        if prefix==bytes.fromhex('488bd0'):
            g.take('488bd0');need('one-unchanged-allocation-argument','rdx'not in arguments);arguments.add('rdx');continue
        if prefix==bytes.fromhex('488bcf'):
            g.take('488bcf');need('one-wrapper-receiver','rcx'not in arguments);arguments.add('rcx');ecx=None;continue
        if prefix[:2]in(bytes.fromhex('8948'),bytes.fromhex('8988')):
            modrm=prefix[1];g.take('89'+format(modrm,'02x'));offset=int.from_bytes(g.read(1 if modrm==0x48 else 4),'little',signed=True)
            need('same-current-live-ECX-constant',ecx is not None);width=4;value=ecx;register_stores+=1
        else:
            width=2 if prefix[:1]==b'\x66'else 1 if prefix[:1]==b'\xc6'else 4
            if width==2:g.take('66')
            opcode='c6'if width==1 else'c7';g.take(opcode);modrm=g.read(1)[0]
            need('only-immediate-store-to-same-allocation',modrm in(0x40,0x80))
            offset=int.from_bytes(g.read(1 if modrm==0x40 else 4),'little',signed=True);value=g.read(width)
        key=(offset,width)
        need('same-current-Original-default-bits',key in expected and value==expected[key],(key,value.hex(),[(k,v.hex())for k,v in expected.items()]))
        stores.append(dict(instructionVa=at,offset=offset,bytes=width,constantHex=value.hex().upper()));del expected[key]
    need('actual-post-allocation-register-reuse',loads>=1 and register_stores>=1)
    setter=g.relative('e8');b,c=bytes((base_slot,)).hex(),bytes((cache_slot,)).hex();g.take('488b5f'+b)
    usages=[];casts=[]
    for i in range(2):
        site=g.at;cell=g.relative('488b15');usages.append(dict(site=site,cell=cell))
        if i==0:g.take('488bcb')
        casts.append(g.relative('e8'))
        if i==0:g.take('488947'+c,'488bcb')
    need('same-current-Original-cast-twice',len(set(casts))==1 and all(u['cell']==allocation['cell']for u in usages))
    g.take('488d4f'+c,'488b5c2430','4883c420','5f');need('same-restored-tail-barrier',g.relative('e9')==barrier)
    return dict(selectedBytes=g.seen,factoryProfile=PROFILE,initializedFlag=flag,constructor=ctor,
        allocation=allocation,allocationTarget=allocate,baseClassUsage=ancestor,baseReady=ready,instanceSetter=setter,
        inlineHolderWrites=None,strictCast=casts[0],classUsages=usages,baseHolderOffset=base_slot,typedCacheOffset=cache_slot,
        originalConstructorCalled=False,originalConstructorTarget=None,originalConstructorEffectsProved=False,
        inlinedOriginalInitializers=initializers,registerDefaultStores=stores,defaultConstantRegister='ecx',
        normalReturnViaBarrier=True,entryRspRestored=True,nonvolatileRegistersRestored=['rbx','rdi'],
        condition=__doc__+' Fresh independently proved constructor defaults and actual typed allocator/ancestor/setter/casts; compatible normal helpers and disabled collector.')
