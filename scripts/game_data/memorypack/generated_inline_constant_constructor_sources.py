"""Finite inline construction with independently owned Original defaults.

This source profile does not invoke the named Original constructor. It joins
the same literal field defaults to the caller's fresh allocation, both holders,
two compatible class predicates and whole wrapper output. The outer caller
still owns its full frame, while collector-enabled and initialization paths
remain outside this selected fragment.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

LABEL='generatedInlineConstantConstructor'
PULL_TYPE='Beyond.Gameplay.Core.PullAction+Data'
DISABLE_TYPE='Beyond.Gameplay.Core.DisableNormalSkillWithUI+Data'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,*,initialized_flag,base_slot,cache_slot,allocator,predicate,disabled,constant_stores,
            wrapper='rdi',output='r14',original_type=PULL_TYPE):
    from scripts.game_data.memorypack.generated_inline_constructor_sources import _edge,_nonnull
    need('one-literal-register-and-holder-profile',(wrapper,output,base_slot,cache_slot)==('rdi','r14',16,24))
    need('independently-owned-roles',all(type(v)is int and v>0 for v in(initialized_flag,allocator,predicate,disabled)))
    need('finite-nominal-inline-default-profile',original_type in(PULL_TYPE,DISABLE_TYPE))
    field_roles=([('stopTolerance','float',4),('finishPullByAction','bool',1),('isEnable','bool',1)]if original_type==PULL_TYPE
        else[('autoFinishByAction','bool',1),('isEnable','bool',1)])
    need('finite-named-original-defaults',type(constant_stores)is list and len(constant_stores)==len(field_roles))
    roles=[]
    for store,(name,typ,width)in zip(constant_stores,field_roles,strict=True):
        fields=store.get('fields',[]);raw=bytes.fromhex(store.get('constantHex',''))
        need('same-owned-original-field-default',len(fields)==1 and(fields[0].get('name'),fields[0].get('typeName'),fields[0].get('bytes'))==(name,typ,width)
            and type(store.get('offset'))is int and 16<=store['offset']<128 and fields[0].get('offset')==store['offset']
            and store.get('bytes')==width and len(raw)==width and type(fields[0].get('owner'))is str)
        roles.append((store['offset'],width,raw.hex()))
    need('distinct-current-default-field-ranges',len({p for offset,width,_ in roles for p in range(offset,offset+width)})==sum(width for _,_,width in field_roles))
    g=BytesPath(regions,entry)
    need('same-current-own-metadata-cell',flag(g,prefix='803d')==initialized_flag);_edge(g,zero=False)
    at=g.at;ancestor_cell=g.relative('488b0d');ancestor=dict(instructionVa=at,cellVa=ancestor_cell)
    g.take('83b9e000000000');_edge(g,zero=False)
    at=g.at;allocation_cell=g.relative('488b0d');allocation=dict(instructionVa=at,cellVa=allocation_cell)
    g.call(allocator);g.take('4c8bc8','4885c0');null=_nonnull(g)
    collectors=[];stores=[];defaults=[]
    def collect():
        at=g.at;need('same-independently-disabled-DWORD-collector',flag(g,prefix='833d')==disabled);collectors.append(at)
    def store(raw,role,offset,source):
        at=g.at;g.take(raw);stores.append(dict(instructionVa=at,role=role,offset=offset,bytes=8,sourceRegister=source,sameAllocatedReference=True))
    collect()
    for offset,width,raw in roles:
        at=g.at;g.take(('c740'if width==4 else'c640')+bytes((offset,)).hex()+raw)
        defaults.append(dict(instructionVa=at,offset=offset,bytes=width,constantHex=raw.upper()))
    store('48894718','wrapper-holder',24,'rax');_edge(g,zero=True)
    collect();store('4c894f10','wrapper-holder',16,'r9');_edge(g,zero=True)
    g.take('488b5f10');at=g.at;cell=g.relative('488b35');classes=[dict(instructionVa=at,cellVa=cell)]
    g.take('4885db');_edge(g,zero=False)
    predicates=[]
    def compatible():
        g.take('488b0b','488bd6');predicates.append(g.at);g.call(predicate);g.take('84c0');_edge(g,zero=False)
    compatible();store('48895f18','typed-cache-after-compatible-predicate',24,'rbx')
    at=g.at;cell2=g.relative('488b35');classes.append(dict(instructionVa=at,cellVa=cell2))
    need('both-exact-current-Original-class-cells',cell==cell2==allocation_cell)
    compatible();g.jump('e9');collect();_edge(g,zero=True)
    collect();store('49893e','parent-output',0,'rdi');_edge(g,zero=True)
    return dict(selectedBytes=g.seen,selectedEnd=g.at,initializedFlag=initialized_flag,
        allocation=allocation,ancestorClass=ancestor,classUsages=classes,allocatorTarget=allocator,
        predicateTarget=predicate,predicateSites=predicates,baseHolderOffset=16,typedCacheOffset=24,
        wrapperRegister=wrapper,outputRegister=output,originalRegister='rbx',holderWrites=stores,
        defaultFieldStores=defaults,collectorComparisons=collectors,ownedNullExit=null,
        originalConstructorCalled=False,sameIndependentlyOwnedOriginalDefaults=True,
        completeSelectedConstructionFragment=True,sameFreshOriginalInBothHolders=True,sameFreshWrapperInOutput=True,
        callerFrameProved=False,childGrammarAdmitted=False,metadataInitializationAdmitted=False,enabledCollectorAdmitted=False,
        condition='Exact initialized nominal classes, successful fresh allocation and compatible class predicates, independently current collector zero. The '+('three'if original_type==PULL_TYPE else'two')+' literal default writes equal the independently proved named Original constructor; this caller does not invoke that entry. Outer frame and field grammar remain separate.')
