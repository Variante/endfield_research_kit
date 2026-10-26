"""Current receiver allocator partition and conditional fast-block header path.

All current allocator instructions, including real counter read/modify/writes
and non-writing prefetch hints, have a complete partition, CFG and normal
frame proof. The selected ordinary non-generic, reference-containing class
path takes an already available small-block allocation from its actual size
class table. Both allocator-mode branches are independently checked. It writes
the unchanged incoming class into that same block's header, preserves the
block through selected disabled optional hooks and returns it unchanged after
the actual final class helper. Its argument is independently bound to the
TypeFromHandle cold path's freshly loaded RuntimeType class cell.

This is conditional on coherent initialized class/layout/size-class tables,
a nonnull disjoint free block, sufficient storage, matching class flag and
descriptor predicates, disabled selected optional hooks and compatible normal
helper effects preserving header/storage. Other allocator paths are fully
checked for source/control but their allocation semantics remain unadmitted.
Actual startup/cache contents, allocator execution, initialized RuntimeType
identity, virtual slots, MethodInfo/RGCTX and concrete enum callbacks remain
separate. No wire, parent or whole owner is admitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-receiver-allocator-paths.v1'
LABEL='enumReceiverAllocatorPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def fast_block_program(regions,entry,*,image_base,mode_one):
    need('literal-allocator-mode',type(mode_one)is bool)
    g=BytesPath(regions,entry);g.take('4053','57','4883ec58','488bf9');layout=g.relative('e8')
    g.take('48837f6000');g.branch('74',True,1)
    g.take('f6873801000020');g.branch('0f85',True)
    g.take('48837f0800','4889742450','8bb7f8000000');g.branch('0f84',False)
    mode_cell=g.relative('833d')+1;g.take('01','4c896c2440','4c89742438','4c897c2430');g.branch('75',not mode_one,1)
    table=g.relative('4c8b35');class_number=g.relative('448b3d')
    if mode_one:g.jump('eb',1)
    need('same-selected-image-base-role',g.relative('4c8d2d')==image_base)
    g.take('4881fe00080000');g.branch('0f87',False)
    hook=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    g.take('498b8cf5');size_table=int.from_bytes(g.read(4),'little',signed=True)
    g.take('498b1cce','4885db');g.branch('0f85',True)
    g.take('488b03','498904ce','48c1e104');counter=g.relative('48010d')
    need('same-optional-hook-cell-after-removal',g.relative('833d')+1==hook)
    g.take('00','48893b');g.branch('74',True,1)
    card=g.relative('833d')+1;g.take('00');g.branch('74',True,1)
    allocation_count=g.relative('f048ff05')
    g.take('4c8b7c2430','4c8b742438','4c8b6c2440');g.jump('eb',1)
    g.take('488b742450','f6873901000002');g.branch('74',True,1)
    trace=g.relative('f605')+1;g.take('80');g.branch('74',True,1)
    g.take('488bcf');final=g.relative('e8');g.take('488bc3','4883c458','5f','5b','c3')
    return dict(selectedBytes=g.seen,entry=entry,modeOne=mode_one,allocatorModeCell=mode_cell,
        allocatorModeMustEqualOne=mode_one,actualClassLayoutTarget=layout,actualFinalClassTarget=final,
        freeBlockTableCell=table,classNumberCell=class_number,sizeClassIndexTableRelativeOffset=size_table,
        sizeClassIndexScale=8,freeBlockPointerScale=8,instanceSizeClassOffset=248,instanceSizeAtMost2048Required=True,
        genericClassOffset=96,genericClassMustBeNull=True,classFlagsOffset=312,referenceFlagMask=32,
        referenceFlagMustBeSet=True,descriptorClassOffset=8,descriptorMustBeNonnull=True,
        optionalHookCell=hook,optionalCardCell=card,optionalTraceCell=trace,
        selectedOptionalHookAndCardWordsMustBeZero=True,selectedTraceBit128MustBeZero=True,
        selectedFinalizerFlagByteOffset=313,selectedFinalizerFlagBit2MustBeZero=True,
        freeListHeadUpdatedToPreviousBlockHeader=True,headerOffset=0,
        unchangedIncomingClassStoredInReturnedBlock=True,returnedBlock='unchanged selected free block rbx',
        byteCounterCell=counter,byteCounterAddend='actual selected size-class index multiplied by16',
        allocationCountCell=allocation_count,allocationCountIncrement=1,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rdi','rsi','r13','r14','r15'],normalReturn=True,
        helperClassAndHeaderAliasPreservationRequired=True,actualRuntimeClassOrAllocatorExecutionProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_runtime_type_receiver_paths import derive as receiver_source
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=receiver_source(image,pins,**arguments)
    cold=prior['proof']['typeFromHandlePaths']['empty-new'];body=owned(image,cold['allocationTarget']);rows=[]
    for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));graph,padding=complete_program(body['regions'],rows,body['pointer'])
    paths=[fast_block_program(body['regions'],body['pointer'],image_base=image.pe.image_base,mode_one=mode)for mode in(True,False)]
    need('same-actual-class-header-and-return-with-both-mode-tables',
        all(p['unchangedIncomingClassStoredInReturnedBlock']for p in paths)
        and paths[0]['allocatorModeCell']==paths[1]['allocatorModeCell']
        and paths[0]['actualFinalClassTarget']==paths[1]['actualFinalClassTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(receiverSource=prior,actualAllocatorEntry=body['pointer'],allocatorWindows=body['windows'],
            allocatorCfg=graph,allocatorPadding=padding,fastBlockPaths=paths,
            actualIncomingClassCell=cold['runtimeTypeClassCell']),
        selectedUnchangedClassHeaderAndReferenceReturnProved=True,allAllocatorPathsSemanticallyAdmitted=False,
        initializedRuntimeTypeClassIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete current allocator partition/CFG/normal frames and both actual selected small free-block/header/return paths, bound to TypeFromHandle cold allocator call.',
            conditional=__doc__,structuralOnly='Native allocated object header, free-block table and counter transfers.',
            unresolved=['class/layout/size/free-block tables and opaque helper alias effects','other allocator allocation paths and actual execution',
                'initialized RuntimeType receiver/virtual slots/MethodInfo/RGCTX','concrete enum callback','wire/parent/EOF']))))
