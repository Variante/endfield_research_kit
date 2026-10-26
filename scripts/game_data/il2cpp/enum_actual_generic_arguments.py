"""Actual provider GetGenericArguments count1 inline/canonical transfers.

The provider's selected helper is not treated as the named virtual method:
its source compares the actual receiver slot callback against that exact
metadata-owned body, then executes its own inlined argument loop. Both full
owned source families have independent instruction/CFG/frame checks. On the
explicit constructed-class/count1/collector-disabled paths, each reads the
actual class.generic key, then that key's class-instantiation/count/vector,
requests the actual reflection helper for the unchanged argument carrier and
writes that unchanged helper result to element0 of its actual fresh array.
Both return the same array they filled. The source helper's other explicit
external/virtual tails remain conditional and grant no alternate semantics.

These transfers require a coherent incoming constructed class, its actual
key/class-instantiation, one stable argument, initialized matching virtual
selection, valid disjoint normally returning array allocation/reflection
helpers and a zero collector flag. Neither class/Type payload identity nor
allocation, cache or alias effects are inferred. Actual initialized nominal
MethodInfo/RGCTX/callback and concrete enum wire/list/parent remain unresolved.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-actual-generic-arguments.v1'
LABEL='enumActualGenericArguments'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def inline_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2418','55','56','57','4154','4156','4883ec20',
        '0fb7d9','488bfa','488b0a');prepare=g.relative('e8')
    g.take('488b07','488d4b14','4803c9','4c8b04c8','488b54c808')
    canonical=g.relative('488d05');g.take('4c3bc0');g.branch('0f85',False)
    g.take('488b4f10','b201');class_helper=g.relative('e8');array_class=g.relative('488b0d')
    g.take('488bf0','f6803801000010');g.branch('0f84',True)
    g.take('4883786000');g.branch('0f84',False)
    g.take('488b4060','488b7008','8b16');allocate=g.relative('e8')
    g.take('33db','488be8','391e');g.branch('0f86',False)
    collector_table=g.relative('4c8d25');g.take('0f1f440000');loop=g.at
    g.take('488b4e08','488d7d20','8bc3','488d3cc7','8bc3','488b0cc1');reflection=g.relative('e8')
    collector=g.relative('833d')+1;g.take('00','488907');g.branch('74',True,1)
    g.take('ffc3','3b1e');need('same-count1-inline-argument-loop',g.relative('72',1)==loop)
    g.jump('eb',1);g.take('4885ed');g.branch('75',True,1)
    g.take('488bc5','488b5c2460','4883c420','415e','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,actualClassPreparation=prepare,comparedCanonicalTarget=canonical,
        actualClassHelper=class_helper,arrayElementClassCell=array_class,actualArrayAllocator=allocate,
        actualReflectionHelper=reflection,collectorFlagCell=collector,collectorTable=collector_table,
        collectorFlagMustBeZero=True,inputVirtualSlotMustBe=63,callbackMustEqualComparedCanonical=True,
        callbackOffset='320 + actual slot63 *16',methodInfoOffset='328 + actual slot63 *16',
        inputTypePayloadOffset=16,classGenericKeyOffset=96,keyClassInstantiationOffset=8,
        instantiationCountOffset=0,instantiationArgumentsOffset=8,argumentCarrierTransferredUnchanged=True,
        selectedCount=1,arrayElementsOffset=32,storedReflectionResultUnchanged=True,
        freshArrayResultReturnedUnchanged=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r14'],
        actualInputClassContextAndTypePayloadIdentityProved=False)


def canonical_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','55','56','57','4154','4155','4156','4157','4883ec20',
        '488b4910','b201');class_helper=g.relative('e8');array_class=g.relative('488b0d')
    g.take('4c8be8','f6803801000010');g.branch('0f84',True)
    g.take('4883786000');g.branch('0f84',False)
    g.take('488b4060','488b6808','8b5500');allocate=g.relative('e8')
    g.take('33ff','488bf0','397d00');g.branch('0f86',False)
    collector_table=g.relative('4c8d35');g.take('0f1f4000','0f1f840000000000');loop=g.at
    g.take('488b4d08','8bc7','4883c004','488d1cc6','8bc7','488b0cc1');reflection=g.relative('e8')
    collector=g.relative('833d')+1;g.take('00','488903');g.branch('74',True,1)
    g.take('ffc7','3b7d00');need('same-count1-canonical-argument-loop',g.relative('72',1)==loop)
    g.jump('eb',1);g.take('4885f6');g.branch('75',True,1)
    g.take('488b5c2468','488bc6','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,actualClassHelper=class_helper,arrayElementClassCell=array_class,
        actualArrayAllocator=allocate,actualReflectionHelper=reflection,collectorFlagCell=collector,
        collectorTable=collector_table,collectorFlagMustBeZero=True,inputTypePayloadOffset=16,
        classGenericKeyOffset=96,keyClassInstantiationOffset=8,instantiationCountOffset=0,instantiationArgumentsOffset=8,
        argumentCarrierTransferredUnchanged=True,selectedCount=1,arrayElementsOffset=32,
        storedReflectionResultUnchanged=True,freshArrayResultReturnedUnchanged=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        actualInputClassContextAndTypePayloadIdentityProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_constructed_class_paths import derive as constructed_source,_json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.consumer_control import check_consumer_control
    from scripts.game_data.il2cpp.initializer_control import control_transfer
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import _vtable
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=constructed_source(image,pins,**arguments)
    managed=prior['proof']['managedArgumentSource'];dispatch=managed['proof']['virtualDispatchSource']
    helper=owned(image,dispatch['proof']['selectedProviderPath']['actualCalls']['genericArguments'])
    actual=inline_program(helper['regions'],helper['pointer']);ctx=NativeReferenceContext(image);md=image.metadata
    methods=[m for m in md.methods_for(ctx.index.types['System.RuntimeType'])if md.string(m.name_index)=='GetGenericArguments'
        and m.slot==63 and not md.parameters_for(m)]
    need('one-exact-GetGenericArguments-override',len(methods)==1);method,=methods
    need('actual-instance-Type-array-return',not method.flags&0x10 and ctx.type_name(method.return_type)=='System.Type[]')
    _vtable(image,method.declaring_type,63,method.index,LABEL)
    need('same-actual-compared-canonical-body',actual['comparedCanonicalTarget']==image.method_pointer_va(method))
    named=owned(image,actual['comparedCanonicalTarget']);canonical=canonical_program(named['regions'],named['pointer'])
    graphs={}
    for role,body in(('actual',helper),('canonical',named)):
        rows=[]
        for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
        rows.sort(key=lambda r:int(r['va'],16))
        if role=='canonical':graph,padding=complete_program(body['regions'],rows,body['pointer']);graphs[role]=dict(control=graph,padding=padding)
        else:
            by={int(r['va'],16):r for r in rows};tails={}
            for at,row in by.items():
                if bytes.fromhex(row['bytes'])==bytes.fromhex('49ffe0'):tails[at]=dict(register='r8');continue
                flow=control_transfer(row)
                if flow['kind']=='jump'and flow['target']not in by:tails[at]=dict(target=flow['target'])
            need('exact-two-current-argument-helper-external-tails',len(tails)==2 and sum('target'in t for t in tails.values())==1)
            graphs[role]=check_consumer_control(rows,entry=body['pointer'],owned_ranges=[(a,a+len(raw))for a,raw in body['regions']],tail_exits=tails)
    cold=managed['proof']['nativeGenericKeySource']['proof']['receiverSource']['proof']['typeFromHandlePaths']['empty-new']
    reflection_entry=prior['proof']['selectedReflectionPaths'][0]['entry']
    for p in(actual,canonical):
        need('same-independent-class-and-reflection-helpers',p['actualClassHelper']==cold['classHelperTarget']and p['actualReflectionHelper']==reflection_entry)
    need('same-inline-canonical-allocation-class-collector-and-source-roles',all(actual[k]==canonical[k]for k in(
        'arrayElementClassCell','actualArrayAllocator','collectorFlagCell','collectorTable','classGenericKeyOffset',
        'keyClassInstantiationOffset','instantiationCountOffset','instantiationArgumentsOffset')))
    need('same-independent-actual-class-preparation',actual['actualClassPreparation']==dispatch['proof']['makeGenericType']['classPreparationTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(constructedSource=prior,namedMethod=[method.index,'System.RuntimeType','GetGenericArguments'],
            actualHelperWindows=helper['windows'],canonicalWindows=named['windows'],controlGraphs=graphs,
            actualInlineCount1Program=actual,canonicalCount1Program=canonical),
        actualAndCanonicalCount1CarrierArrayTransfersProved=True,actualNominalContextOrTypePayloadIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Independent complete actual helper and named method sources/control/frames, actual callback comparison, two count1 class/key/vector/reflection/array-store/return paths and shared helper/cell joins.',
            conditional=__doc__,structuralOnly='Actual source generic argument carrier and Type-array transport.',
            unresolved=['actual incoming nominal class/key/Type payload and allocation/cache effects',
                'closed MethodInfo/RGCTX and concrete enum callback','wire/list/parent/EOF'])),default=_json_set))
