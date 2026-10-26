"""Actual warm handle-to-RuntimeType cache effects for selected ordinary kinds.

Cache contents and canonical live class/Type identities remain conditions.
The returned pointer transfer and all selected non-import callees are replayed.
Cold construction, insertion, allocation and collisions are separate paths.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp import enum_argument_key_paths as value_keys
from scripts.game_data.memorypack import formatter_provider_success_sources as handles
from scripts.game_data.memorypack import leveldata_patrol_value_hash_programs as classes
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_helper_sources as packets
from scripts.game_data.memorypack import leveldata_patrol_checkpoint_callee_sources as source

SCHEMA='endfield.story-patrol-runtime-type-cache-sources.v1'
TYPES={'int':('System.Int32',8),'string':('System.String',14),
    'UnityEngine.Vector3':('UnityEngine.Vector3',17),'Beyond.Gameplay.Core.EntityPtr':('Beyond.Gameplay.Core.EntityPtr',17)}


def need(check,condition):
    if not condition:raise ValueError('patrolRuntimeTypeCache.'+check)


def norm(v):return json.loads(json.dumps(v))


def same(a,b):return json.dumps(a,sort_keys=True,separators=(',',':'))==json.dumps(b,sort_keys=True,separators=(',',':'))


def _requirements():
    return dict(ownNominalTypeAndInitializedHandleDataRequired=True,selectedClassCellsOrRecordCacheRequiredNonnull=True,
        ownClassByvalMatchesSelectedNominalKindByrefAndDataRequired=True,SystemTypeClassRequiredInitialized=True,
        reflectionCacheRequiredNonempty=True,deletedCountRequiredZero=True,capacityRequiredPositivePowerOfTwo=True,
        maskRequiredCapacityMinusOne=True,firstProbeRequiredOccupiedTagZero=True,sentinelRequiredNonzero=True,
        actualKeyComparisonRequiredZero=True,valueIndexRequiredInBounds=True,returnedRuntimeTypeRequiredNonnull=True,
        returnedRuntimeTypeIdentityRequiredCanonicalForSelectedClass=True,
        mutexImportsRequiredNormalAbiAndExclusiveStableStorage=True,interveningAliasMutationForbidden=True,
        runtimeCacheOrClassContentsObserved=False)


def primitive_class(regions,entry,*,kind):
    need('primitive-selected-kind',kind in (8,14));g=BytesPath(regions,entry)
    g.take('4053','4883ec20','0fbe410a');base=g.relative('4c8d05')
    g.take('488bd9','83f80f');g.branch('7c',True,1)
    g.take('ffc8','3dfe000000');g.branch('77',False,1)
    g.take('4863c8','410fb68408');byte_table=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('418b8c80');table=base+int.from_bytes(g.read(4),'little',signed=True)
    g.take('4903c8','ffe1');g.at=byte_table+kind-1;index=g.read(1)[0]
    g.at=table+4*index;target=base+int.from_bytes(g.read(4),'little',signed=True);g.at=target
    cell=g.relative('488b05')
    if g.bytes[g.at]==0xeb:g.jump('eb',1)
    elif g.bytes[g.at]==0xe9:g.jump('e9')
    g.take('4885c0');g.branch('75',True,1);g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,typeKind=kind,byteTable=byte_table,jumpTable=table,
        selectedByteIndex=kind-1,selectedWordIndex=index,selectedTargetVa=target,cachedClassCellVa=cell,
        result='same nonnull selected primitive class-cell value',normalCalls=0,nonframeWrites=0,
        classCellIdentityObserved=False,entryRspRestored=True,restoredNonvolatiles=['rbx'])


def primitive_hash(regions,entry,*,kind):
    need('primitive-hash-kind',kind in (8,14));g=BytesPath(regions,entry)
    g.take('4053','4883ec20','480fbe410a','8b5908','4869d0');prime=int.from_bytes(g.read(4),'little',signed=True)
    need('positive-hash-polynomial',0<prime<1<<31)
    g.take('0fb6410a','48c1eb1d','83e301','4803da')
    for value,opcode in ((18,'75'),(17,'74'),(21,'74'),(29,'74'),(15,'74')):
        g.take('3c'+bytes((value,)).hex());g.branch(opcode,value==18,1)
    g.take('488bc3','4883c420','5b','c3')
    return dict(selectedBytes=g.seen,typeKind=kind,prime=prime,byrefDwordBit=29,
        result='kind * prime + raw byref bit modulo2^64',typeDataOrAddressRead=False,
        normalCalls=0,entryRspRestored=True,restoredNonvolatiles=['rbx'])


def primitive_equals(regions,entry,*,kind,image_base):
    need('primitive-equality-kind',kind in (8,14));g=BytesPath(regions,entry)
    g.take('4883ec28','4c8bda','48895c2430');need('same-image-base',g.relative('488d15')==image_base)
    g.take('4c8bd1','66660f1f840000000000','410fb6430a','4138420a');g.branch('0f85',False)
    g.take('418b4308','418b4a08','c1e81d','c1e91d','83e001','83e101','3bc8');g.branch('0f85',False)
    g.take('410fbe420a','83c0f1','83f80f');g.branch('0f87',True)
    g.take('33c0','488b5c2430','4883c428','c3')
    return dict(selectedBytes=g.seen,inputKinds=[kind,kind],sameRawByrefRequired=True,
        result=0,typeDataOrAddressCompared=False,normalCalls=0,entryRspRestored=True,restoredNonvolatiles=['rbx'])


def _programs(p):
    b=p['imageBase'];s=p['sources'];r=lambda n:packets.regions(s[n],b);e=lambda n:b+s[n]['entryRva']
    h=handles.type_from_handle(r('handle'),e('handle'),{n:e(n)for n in ('classFromType','hash','compare')})
    return dict(handle=h,primitiveClasses={str(k):primitive_class(r('classFromType'),e('classFromType'),kind=k)for k in (8,14)},
        primitiveHash={str(k):primitive_hash(r('hash'),e('hash'),kind=k)for k in (8,14)},
        primitiveEquals={str(k):primitive_equals(r('compare'),e('compare'),kind=k,image_base=b)for k in (8,14)},
        valueClass=classes.class_from_type(r('classFromType'),e('classFromType')),
        ordinaryClass=classes.ordinary_class(r('ordinaryClass'),e('ordinaryClass')),
        definitionClass=classes.definition_class(r('definitionClass'),e('definitionClass')),
        valueHash=value_keys.hash_program(r('hash'),e('hash')),
        valueEquals=value_keys.compare_program(r('compare'),e('compare'),image_base=b,equal=True))


def compose(proof,pins):
    p=norm(proof);p['programs']=norm(_programs(p));p['requirements']=_requirements()
    v=norm(dict(schema=SCHEMA,status='validated-conditional-warm-runtime-type-cache',nativeInputs=pins,proof=p,
        selectedWarmTypeFromHandleEffectsProved=True,selectedOrdinaryAndStringCalleesProved=True,
        coldCacheOrAllocationEffectsProved=False,canonicalRuntimeTypeIdentityObserved=False,
        runtimeInvocationObserved=False,playbackProved=False,
        conditions=['Same valid selected Type handle, actual metadata/runtime class cells and indexed cached classes; own current byval kind/byref/data agree with the admitted ordinary nominal.',
            'Initialized System.Type class, nonempty coherent reflection cache, deleted count0, valid power-of-two mask/capacity, non-sentinel first occupied tag0, key comparator zero, valid value index and nonnull canonical matching RuntimeType entry.',
            'Mutex imports have normal ABI and hold stable exclusive cache storage; no alias mutation, cold creation, collision, allocation, insertion or runtime identity observation is granted.']))
    validate(v,pins);return v


def derive(image,pins,*,entry):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack.leveldata_patrol_checkpoint_storage_sources import _fixed_prefix
    _publication_gate(image,pins);b=image.pe.image_base;s={'handle':source._body(image,entry)}
    calls=source._calls(s['handle'],b)
    for role,i in (('classFromType',0),('hash',1),('compare',2)):s[role]=source._body(image,calls[i][1])
    # Both switch tables reside in the actual owned function packets. Their
    # words/bytes are replayed directly rather than inferred from code order.
    c=classes.class_from_type(packets.regions(s['classFromType'],b),b+s['classFromType']['entryRva'])
    s['ordinaryClass']=_fixed_prefix(image,c['ordinaryClassTargetVa'],19)
    c=classes.ordinary_class(packets.regions(s['ordinaryClass'],b),b+s['ordinaryClass']['entryRva'])
    head=_fixed_prefix(image,c['classDefinitionCall']['targetVa'],232)
    g=BytesPath(packets.regions(head,b),b+head['entryRva'])
    g.relative('488b05');g.take('486390a0000000','48b865210b59c84216b2','482bca');g.relative('482b0d')
    g.take('48f7e9','4803d1','48c1fa06','488bca','48c1e93f','4803ca');tail=g.relative('e9')
    # The selected resolver is inside this exact existing direct-source span.
    # Do not append an overlapping unwind packet to the same authenticated bytes.
    need('owned-direct-definition-resolver',tail in g.bytes)
    s['definitionClass']=head
    ctx=NativeReferenceContext(image);nom={}
    for name,(declared,kind)in TYPES.items():
        td=ctx.index.types[declared];ptr=ctx.type_pointer(td.byval_type_index)
        nom[name]=dict(name=declared,typeDefinition=td.index,byvalTypeIndex=td.byval_type_index,
            registeredTypePointerVa=ptr,rawTypeHex=image.pe.bytes_at_va(ptr,16).hex().upper(),kind=kind)
    v=compose(dict(imageBase=b,sources=s,nominalTypes=nom),pins);_publication_gate(image,pins);return v


def validate(v,pins):
    need('schema-native',v.get('schema')==SCHEMA and v.get('status')=='validated-conditional-warm-runtime-type-cache'and v.get('nativeInputs')==pins)
    p=v['proof'];need('finite-children',set(p['sources'])=={'handle','classFromType','hash','compare','ordinaryClass','definitionClass'})
    for s in p['sources'].values():packets.verify_packet(s)
    g=_programs(p);need('exact-program-replay',same(g,p['programs']))
    need('explicit-warm-selected-state',p['requirements']==_requirements())
    need('same-ordinary-class-tail',g['valueClass']['ordinaryClassTargetVa']==p['imageBase']+p['sources']['ordinaryClass']['entryRva']
        and g['ordinaryClass']['classDefinitionCall']['targetVa']==p['imageBase']+p['sources']['definitionClass']['entryRva'])
    need('exact-nominal-domain',set(p['nominalTypes'])==set(TYPES))
    for name,(declared,kind)in TYPES.items():
        n=p['nominalTypes'][name];raw=bytes.fromhex(n['rawTypeHex'])
        need('registered-ordinary-kind-'+name,n['name']==declared and n['kind']==kind and len(raw)==16 and raw[10:12]==bytes((kind,0 if kind==14 else 128))
            and all(type(n[k])is int and n[k]>=0 for k in ('typeDefinition','byvalTypeIndex','registeredTypePointerVa')))
    need('conditional-only',all(v.get(k)is True for k in('selectedWarmTypeFromHandleEffectsProved','selectedOrdinaryAndStringCalleesProved'))
        and all(v.get(k)is False for k in('coldCacheOrAllocationEffectsProved','canonicalRuntimeTypeIdentityObserved','runtimeInvocationObserved','playbackProved')))
    return v
