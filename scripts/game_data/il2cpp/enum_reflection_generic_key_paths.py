"""Count1 nominal argument transfers in native reflection type construction.

The named static RuntimeType.MakeGenericType entry's exact E9 selects this
current owned family. Its complete instruction partition and control graph
are checked. On the four finite selected count1 paths, the source copies the
actual argument Type object's carrier payload into an owned aligned buffer,
passes that unchanged buffer/count to the independently proved argument
interner, and builds the generic-class key from the actual open type carrier
plus that returned instantiation. The other two key words are explicitly zero.
The existing-key and freshly allocated-key paths remain distinct; the latter
requests one zeroed32 block and passes that exact key to its actual insertion.
The selected new-key path requests class creation; the selected existing-key
path reads its cached class. Both forward the resulting class's byval carrier
to the actual reflection-object helper and return its result unchanged.

Only count1 has the explicit dynamic-stack geometry/normal-frame certificate;
the whole control graph grants no other arity's frame/semantics claim. Normal
stack probing and Win64 helpers, valid coherent Type/array payloads, mutex and
interner/key-cache state, disjoint zeroed allocation and stable opaque effects
remain conditions. The actual generic-class lookup/insertion/class creation,
virtual managed caller, reflection result identity, inflated MethodInfo/RGCTX
and concrete enum formatter callback are not inferred from these transfers.
No scalar width, enum list grammar, parent or whole owner is admitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-reflection-generic-key-paths.v1'
LABEL='enumReflectionGenericKeyPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _release(g,*,owned,owner,depth,mutex):
    need('same-selected-mutex-depth',g.relative('8b05')==depth)
    g.take('85c0');g.branch('7e',False,1);g.take('83f801');g.branch('75',owned,1)
    release=None
    if owned:
        g.take('ffc8');need('same-recursive-depth-store',g.relative('8905')==depth)
    else:
        need('same-owner-clear',g.relative('4c892d')==owner)
        need('same-depth-clear',g.relative('44892d')==depth)
        need('same-actual-mutex-address',g.relative('488d0d')==mutex);release=g.relative('e8');g.jump('eb',1)
    return release


def program(regions,entry,*,owns_mutex,missing_key):
    need('literal-current-generic-key-path',type(owns_mutex)is bool and type(missing_key)is bool)
    g=BytesPath(regions,entry);g.take('4055','4154','4155','4156','4157','4881ec90000000','488d6c2430',
        '48899d98000000','4889b5a0000000','4889bda8000000','488bda','4c8b6110','b201','498bcc')
    class_helper=g.relative('e8');g.take('4c8bf8','8b7318','8bce','48c1e103','488d410f','483bc1');g.branch('77',True,1)
    g.take('4883e0f0');probe=g.relative('e8');g.take('482be0','488d7c2430','85f6');g.branch('74',False,1)
    g.take('488bd7','482bdf','4c8bc6','0f1f8000000000');loop=g.at
    g.take('488b441a20','488b4810','48890a','488d5208','4983e801')
    need('same-argument-copy-backedge',g.relative('75',1)==loop)
    # Count is exactly one: the actual count-down branch falls through.
    g.take('8bd6','488bcf');intern=g.relative('e8')
    g.take('4c8bf0','4983c720','0f57c0','f30f7f4548','4c897d38','48894540')
    mutex=g.relative('488d05');g.take('48898590000000');thread=g.relative('ff15')
    g.take('488bd8');owner=g.relative('488b0d');g.take('483bc1');g.branch('74',owns_mutex,1)
    if owns_mutex:depth=g.relative('ff05')
    else:
        g.take('b9ffffffff');semaphore=g.relative('f00fc10d');g.take('85c9');g.branch('7f',True,1)
        need('same-actual-new-mutex-owner',g.relative('48891d')==owner)
        depth=g.relative('c705')+4;g.take('01000000');g.jump('eb',1)
    g.take('4533ed','44896d00','488d4538','48894508','4c8d4500','488d5518');lookup=g.relative('e8')
    capacity=g.relative('4c8b05');g.take('49c1e004');slots=g.relative('4c0305')
    g.take('c644242001','4d8bc8','488d4d00');iterator=g.relative('e8')
    g.take('488b5d20','483b5d08');g.branch('74',missing_key,1)
    allocation=None
    if missing_key:
        g.take('ba01000000','41b820000000');allocator=g.relative('488b0d');allocate=g.relative('e8')
        g.take('488bd8','4c8938','4c897008','44896d00','48894508','4c8d4500','488d5518');insert=g.relative('e8')
        stats=g.relative('f048ff05')
        allocation=dict(allocatorContextCell=allocator,allocationTarget=allocate,count=1,elementBytes=32,
            unchangedOpenTypeStoredAt=0,unchangedArgumentInstantiationStoredAt=8,
            remainingKeyWordsZeroRequired=True,nonnullDisjointZeroed32AllocationRequired=True,
            insertionTarget=insert,insertionR8='address of actual tag-zero pair with unchanged allocated key pointer',
            allocationCountCell=stats)
    else:g.take('488b5b08')
    release=_release(g,owned=owns_mutex,owner=owner,depth=depth,mutex=mutex)
    if not missing_key:g.jump('eb',1)
    g.take('488b4318','4885c0');g.branch('75',not missing_key,1)
    create=None
    if missing_key:
        g.take('b201','488bcb');create=g.relative('e8');g.take('4885c0');g.branch('74',False,1)
    g.take('488d4820');reflection=g.relative('e8')
    g.take('488b9d98000000','488bb5a0000000','488bbda8000000','488d6560',
        '415f','415e','415d','415c','5d','c3')
    result=dict(selectedBytes=g.seen,entry=entry,ownsMutex=owns_mutex,missingKey=missing_key,inputArgumentCount=1,
        originalTypeObjectPayloadOffset=16,arrayCountOffset=24,arrayElementsOffset=32,argumentTypePayloadOffset=16,
        actualClassHelper=class_helper,actualStackProbe=probe,actualArgumentInterner=intern,
        argumentInternerInputs=dict(rcx='owned count1 argument buffer',edx='unchanged actual array count1'),
        argumentBufferValue='unchanged actual argument Type payload',genericKeyBytes=32,
        genericKeyWords=['actual open class return +32','unchanged actual argument-interner return',0,0],
        primitiveNormalizerCalledOnArgumentPath=False,actualThreadIatCell=thread,mutexAddress=mutex,
        mutexOwnerCell=owner,mutexDepthCell=depth,actualReleaseTarget=release,actualLookupTarget=lookup,
        actualIteratorHelper=iterator,keyTableCapacityCell=capacity,keyTableSlotsCell=slots,
        lookupInsertionAndKeyIdentityProved=False,allocation=allocation,actualClassCreationTarget=create,
        cachedClassOffset=24,actualReflectionObjectTarget=reflection,returnedReflectionResultUnchanged=True,
        selectedClassResultMustBeNonnull=True,selectedCount1NormalFrameProved=True,
        count1DynamicAllocationBytes=16,count1ArgumentBufferBytes=8,count1ArgumentBufferAlignment=16,
        entryRspBeforeDynamicAllocation=-184,entryRspAtNormalCallsAfterProbe=-200,frameRbpFromEntryRsp=-136,
        selectedReturnRspFromRbp=96,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        normalAbiPreservingProbeAndHelpersRequired=True,otherAritiesFramesProved=False,
        genericClassAndReflectionObjectIdentityProved=False)
    if not owns_mutex:result['positiveOldSemaphoreWordRequired']=True;result['semaphoreCell']=semaphore
    else:result['incomingRecursiveDepthMustBePositiveAndBelowSignedMax']=True
    return result


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_runtime_type_receiver_paths import derive as receiver_source
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.consumer_control import build_consumer_control_graph
    from scripts.game_data.memorypack.pointer_param import owned
    from scripts.game_data.levelscript_two_routes_native import _window
    _publication_gate(image,pins);prior=receiver_source(image,pins,**arguments);ctx=NativeReferenceContext(image);md=image.metadata
    methods=[m for m in md.methods_for(ctx.index.types['System.RuntimeType'])if md.string(m.name_index)=='MakeGenericType'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['System.Type','System.Type[]']]
    need('one-current-exact-static-reflection-entry',len(methods)==1);method,=methods
    need('actual-static-Type-return',method.flags&0x10 and ctx.type_name(method.return_type)=='System.Type')
    entry=image.method_pointer_va(method);raw=image.pe.bytes_at_va(entry,5);g=BytesPath([(entry,raw)],entry);target=g.relative('e9')
    body=owned(image,target);rows=[]
    for at,data in body['regions']:rows+=checked_rows(decode(image.mapper,data,at),data,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));graph=build_consumer_control_graph(rows,entry=target,
        owned_ranges=[(a,a+len(data))for a,data in body['regions']])
    need('all-current-owned-native-reflection-code-reachable',not graph['nonEntryInstructions'])
    graph['edges']={a:sorted(v)for a,v in graph['edges'].items()}
    paths=[program(body['regions'],target,owns_mutex=owner,missing_key=missing)for owner in(False,True)for missing in(False,True)]
    interner=prior['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['selectedHit']['entryPrefix']['selectedBytes'][0][0]
    class_helper=prior['proof']['typeFromHandlePaths']['empty-new']['classHelperTarget']
    selection=prior['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']
    probe=selection['proof']['normalizer']['actualCalls']['probe']
    for p in paths:
        need('same-independent-actual-argument-interner-class-helper-and-probe',p['actualArgumentInterner']==interner
            and p['actualClassHelper']==class_helper and p['actualStackProbe']==probe)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(receiverSource=prior,namedStaticMethod=[method.index,'System.RuntimeType','MakeGenericType'],
            namedEntryWindow=_window(image,entry,entry+5,'Exact selected named static entry E9; no unwind extent claim'),
            nativeReflectionWindows=body['windows'],nativeReflectionControlGraph=graph,count1Programs=paths),
        unchangedNominalArgumentAndGenericKeyTransfersProved=True,allAritiesNormalFramesProved=False,
        actualConstructedClassOrClosedMethodInfoIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current named native reflection source partition/control graph and four explicit count1 argument/key/cache/class-result/return programs with actual independent interner/class helper identities.',
            conditional=__doc__,structuralOnly='Nominal argument carriers and generic-class key construction.',
            unresolved=['managed virtual caller and actual nominal Type payload identity','generic-class key lookup/insertion/class creation/reflection result',
                'other arities and opaque alias/cache/history effects','inflated MethodInfo/RGCTX and concrete enum callback','wire/parent/EOF']))))
