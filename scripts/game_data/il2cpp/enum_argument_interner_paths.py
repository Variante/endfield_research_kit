"""Conditional count-one generic-argument interner hit and return.

The actual initialized-table path hashes the unchanged input argument, tests
an occupied slot with count one, compares that input argument with the slot's
argument through the independently proved kind17 comparator, and returns the
same slot's instantiation pointer after restoring the full frame. The initial
slot, table layout and all raw branch conditions are explicit. No comparison
call is inferred from a matching target alone.

This selected hit path does not establish that a live table contains a given
registration, that a probe terminates, or that insertion/initialization made a
particular static instantiation canonical. Compatible normal mutex calls and
stable disjoint input/table storage remain conditions. Equal type contents do
not by themselves select a concrete formatter, MethodInfo, or wire grammar.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath
from scripts.game_data.il2cpp.enum_argument_key_paths import interner_hash_prefix

SCHEMA='endfield.enum-argument-interner-paths.v1'
LABEL='enumArgumentInternerPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def hit_program(regions,entry):
    prefix=interner_hash_prefix(regions,entry)
    g=BytesPath(regions,entry);g.seen=list(prefix['selectedBytes'])
    at,raw=g.seen[-1];g.at=at+len(bytes.fromhex(raw))
    g.take('4869ff');prime=int.from_bytes(g.read(4),'little',signed=True)
    need('positive-slot-polynomial-prime',0<prime<1<<31)
    g.take('4803f8','49ffc0','4c3bc3');g.branch('72',False,1)
    g.take('4923fb','4c8be3');slots=g.relative('4c8b2d')
    g.take('0f1f840000000000');probe=g.at
    g.take('488bc7','4803c0');sentinel=g.relative('488b0d')
    g.take('413b4cc500');g.branch('75',True,1)
    # RIP points past the trailing imm8 as well as opcode/displacement.
    probe_condition=g.relative('48833d')+1;g.take('00');g.branch('76',True,1)
    need('same-count-zero-cell-as-entry-condition',probe_condition==prefix['tableBeginCell'])
    g.take('488bc7','4803c0','41837cc50000');g.branch('75',False,1)
    g.take('498b4cc508','3b19');g.branch('75',False,1)
    g.take('33f6','4d85e4');g.branch('74',False,1)
    g.take('488b5c2428','4c8b7108','4c2bf3','0f1f440000')
    compare_loop=g.at;g.take('498b141e','488b0b');compare_site=g.at;compare=g.relative('e8')
    g.take('85c0');g.branch('75',False,1)
    g.take('48ffc6','4883c308','493bf4');back=g.relative('72',1)
    need('same-counted-comparison-backedge',back==compare_loop)
    g.take('4883ffff');g.branch('75',True,1)
    g.take('48c1e704','4903fd','8bac24a8000000');capacity=g.relative('4c8b15')
    need('same-capacity-cell-at-return',capacity==prefix['capacityCell'])
    g.take('49c1e204','4d03d5','493bfa');g.branch('74',False,1)
    g.take('488b5f08');mutex=g.relative('488b0d')
    need('same-selected-mutex-cell',mutex==prefix['mutexCell'])
    unlock=g.relative('ff15');g.take('90');g.jump('e9')
    g.take('488bc3','4883c458','415f','415e','415d','415c','5f','5e','5d','5b','c3')
    return dict(selectedBytes=g.seen,entryPrefix=prefix,hashTarget=prefix['hashTarget'],slotHashPrime=prime,
        slotHash='(1 * slotHashPrime + argumentHash) & (capacity -1)',slotsCell=slots,sentinelCell=sentinel,
        countZeroCell=probe_condition,countZeroCellMustBeZero=True,initialSlotTagMustDifferFromSentinel=True,
        candidateSlotTag=0,candidateInstantiationCount=1,inputCount=1,slotBytes=16,slotInstantiationOffset=8,
        instantiationCountOffset=0,instantiationArgumentsOffset=8,argumentPointerStride=8,
        probeSite=probe,compareLoop=compare_loop,compareSite=compare_site,compareTarget=compare,
        compareArguments=dict(rcx='unchanged input buffer[0]',rdx='candidate instantiation arguments[0]'),
        comparatorZeroRequired=True,comparisonOrdinal=0,selectedCandidateIndexMustNotBeMinusOne=True,
        selectedSlotMustDifferFromCapacityEnd=True,returnedCandidateInstantiationUnchanged=True,
        unlockIatCell=unlock,normalCallHomeAndAlignmentProved=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
        probeTerminationProved=False,tablePopulationOrCanonicalPointerIdentityProved=False)


def derive(image,pins,**key_arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_placeholder_type_copy import derive as placeholder_source
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins)
    placeholder=placeholder_source(image,pins,**key_arguments);keys=placeholder['proof']['argumentKeySource']
    normal=keys['proof']['normalizerSelection']['proof']['normalizer'];entry=normal['actualCalls']['internArguments']
    body=owned(image,entry);source=hit_program(body['regions'],entry)
    need('fresh-entry-to-actual-hash-call',source['hashTarget']==keys['proof']['hashCallerPrefix']['hashTarget'])
    need('fresh-actual-comparison-call-not-target-alias',any(row['instructionVa']==source['compareSite']
        and row['targetVa']==source['compareTarget']for row in keys['proof']['rawCompareCallCandidates']))
    compared=keys['proof']['comparePrograms'][0]
    need('independent-same-kind-byref-data-comparator',compared['inputKinds']==[17,17]
        and compared['sameRawByrefBitRequired']is True and compared['dataEqualitySelectsZero']is True
        and compared['returnedEax']==0 and compared['typeRecordPointerIdentityCompared']is False
        and compared['entryRspRestored']is True and compared['opaqueCalls']==0)
    # Both independently owned child programs leave every live counted-loop
    # nonvolatile and the hash loop's R8/R10/R11 unchanged. The literal paths
    # contain no further helper call that could silently clobber those values.
    need('literal-owned-hash-and-compare-programs',bool(keys['proof']['hashProgram']['selectedBytes'])
        and keys['proof']['hashProgram']['opaqueCalls']==0 and compared['opaqueCalls']==0)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(placeholderTypeSource=placeholder,internerWindows=body['windows'],selectedHit=source),
        actualComparisonCallerControlAndArgumentsProved=True,countOneHitReturnsSameInstantiationConditional=True,
        initializedInternerResultIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete selected initialized-table/count1 hit path, actual occupied-slot/count/argument comparator call and full returned candidate/frame; independently selected kind17 hash/comparison programs.',
            conditional=__doc__,structuralOnly='Native generic argument keys and instantiation table.',
            unresolved=['lookup/class cache initialization and opaque aliases','probe/insertion/registered-instantiation population and canonical pointer identity',
                'actual nominal provider/formatter/MethodInfo callback selection','wire framing/parent/EOF']))))
