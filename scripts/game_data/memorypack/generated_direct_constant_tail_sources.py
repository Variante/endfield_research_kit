"""Exact direct-holder factory with early address and multiple DWORD defaults.

The caller independently binds the typed allocation and each current declared
field. This profile owns the initialized selected constructor/factory bytes,
all literal stores, whole fresh holder and restored barrier tail. It grants no
child wire grammar or claim that the named Original constructor was invoked.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath


def need(key,condition):
    if not condition:raise ValueError('generatedDirectConstantTail.'+key)


def _literal_defaults(g):
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    head=lifecycle._peek(g,3)
    if head==bytes.fromhex('66c740'):
        at=g.at;g.take('66c740');offset=g.read(1)[0];value=g.read(2)
        need('packed-pair-of-literal-boolean-bytes',16<=offset<127 and all(b in(0,1)for b in value))
        return [dict(instructionVa=at,offset=offset+i,bytes=1,constantHex=bytes((b,)).hex().upper(),
            sourceStoreBytes=2,sourceStoreOffset=offset,sourceByteIndex=i,requiresBooleanByteField=True)for i,b in enumerate(value)]
    if head[:2]==bytes.fromhex('c780'):
        at=g.at;g.take('c780');offset=int.from_bytes(g.read(4),'little',signed=True);value=g.read(4)
        need('positive-owned-disp32-DWORD-field',128<=offset<2**31-4)
        return [dict(instructionVa=at,offset=offset,bytes=4,constantHex=value.hex().upper(),displacementBytes=4)]
    need('literal-byte-or-DWORD',head[:2]in(bytes.fromhex('c740'),bytes.fromhex('c640')))
    return [lifecycle._direct_constant(g,1 if head[:2]==bytes.fromhex('c640')else 4)]


def program(regions,entry,symbols):
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle
    need('actual-allocator-and-barrier',all(type(symbols.get(k))is int and symbols[k]>0 for k in('allocate','barrier')))
    g=BytesPath(regions,entry);g.take('4053','4883ec20')
    metadata=lifecycle._direct_flag(g,'803d');g.take('488bd9');lifecycle._initialized(g)
    allocation=lifecycle._direct_allocation(g,symbols['allocate']);g.take('4885c0');lifecycle._nonnull(g)
    leading=lifecycle._peek(g,2)in(bytes.fromhex('c740'),bytes.fromhex('c640'))or lifecycle._peek(g,1)==b'\xb9'
    stores=[];ecx=None;register_stores=0;steps=0
    if leading:
        while lifecycle._peek(g,4)!=bytes.fromhex('488d4b10'):
            steps+=1;need('bounded-leading-scalar-defaults',steps<=32)
            if lifecycle._peek(g,1)==b'\xb9':
                need('one-consumed-constant-register',ecx is None)
                g.take('b9');ecx=g.read(4);continue
            if lifecycle._peek(g,2)==bytes.fromhex('8948'):
                need('whole-known-ECX-before-holder-address',ecx is not None)
                at=g.at;g.take('8948');offset=g.read(1)[0]
                need('positive-direct-ECX-field',16<=offset<128)
                stores.append(dict(instructionVa=at,offset=offset,bytes=4,constantHex=ecx.hex().upper()));register_stores+=1
            else:
                stores.extend(_literal_defaults(g))
        need('nonempty-consumed-leading-defaults',bool(stores)and(ecx is None or register_stores>0))
    g.take('488d4b10')
    while lifecycle._peek(g,2)in(bytes.fromhex('c740'),bytes.fromhex('c640'),bytes.fromhex('c780'))or lifecycle._peek(g,3)==bytes.fromhex('66c740'):
        need('bounded-current-DWORD-defaults',len(stores)<32)
        literals=_literal_defaults(g)
        need('mixed-defaults-only-after-leading-DWORD',leading or len(literals)==1 and literals[0]['bytes']==4)
        stores.extend(literals)
    need('at-least-two-distinct-defaults',2<=len(stores)<=32 and len({p for s in stores for p in range(s['offset'],s['offset']+s['bytes'])})==sum(s['bytes']for s in stores))
    g.take('48894310','4883c420','5b')
    need('same-actual-restored-barrier-tail',g.relative('e9')==symbols['barrier'])
    return dict(selectedBytes=g.seen,metadata=metadata,allocation=allocation,constantFields=stores,
        holderOffset=16,sameAllocatedOriginalStored=True,baseHolderOffset=16,typedCacheOffset=None,
        allocationTarget=symbols['allocate'],inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],
        originalConstructorInvoked=False,normalReturnViaBarrier=True,entryRspRestored=True,allNonvolatilesRestored=True,
        factoryProfile='direct-leading-scalar-holder-address-packed-defaults.v1'if any(s.get('sourceStoreBytes')==2 or s.get('displacementBytes')==4 for s in stores)
            else'direct-leading-scalar-holder-address-mixed-defaults.v1'if leading else'direct-early-holder-address-multiple-DWORD-defaults.v1',childGrammarAdmitted=False)
