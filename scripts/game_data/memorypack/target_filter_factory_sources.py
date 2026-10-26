"""Exact current TargetFilter defaults and complete direct-holder factories.

The wrapper inlines the same two Boolean and two enum defaults as the owned
Original constructor. Each stored byte is joined to a current named field;
zeroed allocation supplies the other defaults. This optional callable proves
construction and the restored holder16/barrier tail only. It grants no wire
grammar, callback selection or runtime allocation observation.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.memorypack.pooled_string_list_sources import flag

TYPE='Beyond.Gameplay.Core.TargetFilter'
WRAPPER='Beyond.MemoryPack.Beyond_Gameplay_Core_TargetFilterForMemoryPack'
DEFAULTS=((16,2,'0101'),(20,4,'01000000'),(32,4,'FFFFFFFF'))

def need(key,condition,detail=None):
    if not condition:raise ValueError('targetFilterFactory.'+key+':'+str(detail)[:800])

def factory_program(regions,entry,symbols):
    """Both initialized entry shapes, with exact full return and store bits."""
    g=BytesPath(regions,entry);g.take('4053','4883ec20');ready=flag(g,prefix='803d');g.take('488bd9')
    if g.bytes.get(g.at)==0x74:g.branch('74',False,1)
    else:g.branch('75',True,1)
    site=g.at;cell=g.relative('488b0d');g.call(symbols['allocate']);g.take('4885c0')
    if g.bytes.get(g.at)==0x74:g.branch('74',False,1)
    else:g.branch('75',True,1)
    stores=[]
    for raw,offset,width,value in [('66c740100101',16,2,'0101'),('c7401401000000',20,4,'01000000'),('c74020ffffffff',32,4,'FFFFFFFF')]:
        if len(stores)==1:g.take('488d4b10')
        at=g.at;g.take(raw);stores.append(dict(instructionVa=at,offset=offset,bytes=width,constantHex=value))
    g.take('48894310','4883c420','5b');need('same-disabled-barrier',g.relative('e9')==symbols['barrier'])
    return dict(selectedBytes=g.seen,initializedFlag=ready,allocation=dict(site=site,cell=cell),allocationTarget=symbols['allocate'],
        constantFields=stores,baseHolderOffset=16,typedCacheOffset=None,
        inlineHolderWrites=[dict(offset=16,bytes=8,sameAllocatedReference=True)],sameAllocatedOriginalStored=True,
        originalConstructorInvoked=False,entryRspRestored=True,allNonvolatilesRestored=True,normalReturnViaBarrier=True)

def bind_defaults(constructor,program):
    """No byte of a packed word may borrow the width of an adjacent field."""
    leaf=constructor.get('reachableLeaf',{})
    actual=lambda stores:tuple((s['offset'],s['bytes'],s['constantHex'].upper())for s in stores)
    need('complete-independent-Original-leaf',constructor.get('completeReachableEntryProgramProved')is True and
        constructor.get('physicalFunctionExtentProved')is False and leaf.get('tailTargetVa')is None)
    need('same-exact-Original-and-inline-defaults',actual(leaf.get('stores',[]))==actual(program['constantFields'])==DEFAULTS)
    stores=constructor.get('constantFieldStores',[]);need('all-default-store-bindings',len(stores)==3)
    expected=[[(TYPE,'bool',16,1),(TYPE,'bool',17,1)],[(TYPE,'Beyond.Gameplay.Core.FactionTarget',20,4)],[(TYPE,'Beyond.Gameplay.Core.ObjectType',32,4)]]
    joined=[]
    for store,wanted in zip(stores,expected,strict=True):
        fields=store['fields'];facts=[(f['owner'],f['typeName'],f['offset'],f['bytes'])for f in fields]
        need('exact-current-named-default-fields',facts==wanted and all(type(f.get('name'))is str and f['name']for f in fields),facts)
        joined.append(dict(offset=store['offset'],bytes=store['bytes'],constantHex=store['constantHex'],fields=fields))
    return joined

def prove(image,ctx,wrapper,body,symbols,original_ctor):
    """Callable-only finite lifecycle hook; unrelated owners stay strict."""
    if(wrapper.wrapped_type,wrapper.name)!=(TYPE,WRAPPER):return NotImplemented
    from scripts.game_data.memorypack import generated_lifecycle_sources as lifecycle,scalar_param_native as scalar
    md=image.metadata;td=ctx.index.types[TYPE]
    need('one-owned-nongeneric-Original-constructor',original_ctor is not None and original_ctor.declaring_type==td.index and
        md.string(original_ctor.name_index)=='.ctor'and original_ctor.generic_container_index<0)
    scalar.owned_method_abi(image,ctx,original_ctor.index,td.index,('void',1,False),[],'targetFilterFactory.originalCtor')
    constructor=lifecycle._original_constructor(image,ctx,original_ctor,TYPE)
    program=factory_program(body['regions'],body['pointer'],symbols);fields=bind_defaults(constructor,program)
    return dict(program=program,originalConstructor=constructor,proof=dict(typeName=TYPE,wrapperName=WRAPPER,
        completeSelectedFactoryAdmitted=True,childGrammarAdmitted=False,originalConstructor=constructor,
        defaultFieldBindings=fields,zeroedFreshAllocationRequired=True,serializedFramingInferred=False,
        condition='Initialized current metadata; exact typed fresh zeroed allocation, same whole Original reference in sole holder16, disabled independently proved barrier, stable disjoint storage and normal helpers. Complete selected constructor/default bits and restored frame are proved; live construction and child wire grammar are not observed.'))
