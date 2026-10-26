"""Exact R15-wrapper/RSI-output construction and loaded collector guards.

An outer fresh graph proof must establish zero RBX at the initial metadata
comparison. The named lifecycle separately owns allocation, Original ctor,
strict casts, holder types and disabled collector. This component proves their
actual inline sequence and whole fresh references, never the outer frame.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.generated_inline_constructor_sources import _edge,_nonnull

LABEL='generatedR15InlineConstructor'


def need(key,condition):
    if not condition:raise ValueError(LABEL+'.'+key)


def program(regions,entry,*,initialized_flag,base_slot,cache_slot,allocator,original_constructor,strict_cast,disabled,
            wrapper='r15',output='rsi'):
    need('one-literal-register-and-holder-profile',(wrapper,output,base_slot,cache_slot)in(
        ('r15','rsi',16,24),('r15','r14',16,24)))
    need('actual-independent-roles',all(type(v)is int and v>0 for v in
        (initialized_flag,allocator,original_constructor,strict_cast,disabled)))
    g=BytesPath(regions,entry)
    need('same-own-constructor-metadata-cell',g.relative('381d')==initialized_flag);_edge(g,zero=False)
    at=g.at;ancestor_cell=g.relative('488b0d');ancestor=dict(instructionVa=at,cellVa=ancestor_cell)
    g.take('83b9e000000000');_edge(g,zero=False)
    at=g.at;allocation_cell=g.relative('488b0d');allocation=dict(instructionVa=at,cellVa=allocation_cell)
    g.call(allocator);g.take('488bd8','4885c0');null=_nonnull(g)
    g.take('33d2','488bc8');constructor_call=g.at;g.call(original_constructor)
    collectors=[];stores=[]
    def load_collector():
        at=g.at;need('same-current-loaded-DWORD-collector',g.relative('8b05')==disabled);collectors.append(at)
    def store(raw,role,offset):
        at=g.at;g.take(raw);stores.append(dict(instructionVa=at,role=role,offset=offset,bytes=8,sameAllocatedReference=True))
    load_collector()
    store('49895f18','wrapper-holder',24);g.take('85c0');_edge(g,zero=True)
    store('49895f10','wrapper-holder',16);g.take('85c0');_edge(g,zero=True)
    g.take('498b5f10');at=g.at;cell=g.relative('488b15');classes=[dict(instructionVa=at,cellVa=cell)]
    g.take('488bcb');casts=[g.at];g.call(strict_cast)
    store('49894718','typed-cache-after-compatible-cast',24)
    g.take('488bcb');at=g.at;cell2=g.relative('488b15');classes.append(dict(instructionVa=at,cellVa=cell2))
    casts.append(g.at);g.call(strict_cast)
    need('both-current-Original-class-cells',cell==cell2==allocation_cell)
    load_collector();g.take('85c0');_edge(g,zero=True)
    store('4d893e'if output=='r14'else'4c893e','parent-output',0);g.take('85c0');_edge(g,zero=True)
    return dict(selectedBytes=g.seen,selectedEnd=g.at,initializedFlag=initialized_flag,
        allocation=allocation,ancestorClass=ancestor,classUsages=classes,allocatorTarget=allocator,
        originalConstructorTarget=original_constructor,constructorCallVa=constructor_call,
        strictCastTarget=strict_cast,strictCastSites=casts,baseHolderOffset=16,typedCacheOffset=24,
        wrapperRegister=wrapper,outputRegister=output,originalRegister='rbx',holderWrites=stores,
        collectorLoads=collectors,loadedCollectorRegister='eax',entryZeroRegisterRequired='rbx',
        ownedNullExit=null,completeSelectedConstructionFragment=True,sameFreshOriginalInBothHolders=True,
        sameFreshWrapperInOutput=True,callerFrameProved=False,childGrammarAdmitted=False,
        metadataInitializationAdmitted=False,enabledCollectorAdmitted=False,
        condition='The independently complete entry graph proves incoming RBX zero at the metadata CMP. Exact initialized classes, normal nominal allocation/Original ctor and compatible strict casts, disjoint storage and independently disabled collector. Loaded EAX remains unchanged through the paired stores/TEST guards; outer full frame and field grammar stay separate.')
