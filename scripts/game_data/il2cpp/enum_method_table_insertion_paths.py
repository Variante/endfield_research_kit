"""Actual method-key table first-empty insertion and equal-key duplicate.

The selected initialized, adequately reserved, no-deleted-slot paths hash the
unchanged method/class-inst/method-inst key, use all three exact pointer
comparisons for a duplicate, and either publish the unchanged tag/key/triple
or retain the existing equal entry. The output records the same table,
selected slot, capacity end and literal inserted flag; all normal frame and
nonvolatile restoration is included. The selected source contains no calls.

The independently selected normalized pointer lookup uses the same actual
table storage, key offsets, hash inputs and multiplier. This establishes a
source relationship, not that arbitrary runtime input is the seeded key.
Reservation/resize/collision induction, full table history, descriptors and
interned-pointer identity, startup execution and actual provider/MethodInfo
callback selection remain unresolved. No enum wire grammar is admitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-method-table-insertion-paths.v1'
LABEL='enumMethodTableInsertionPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,*,duplicate=False):
    need('literal-insertion-path',type(duplicate)is bool);g=BytesPath(regions,entry)
    g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157','4881ecb0000000',
        '498bf0','488bfa');marker=g.relative('803d')+1;g.take('00');g.branch('0f85',False)
    occupied=g.relative('488b1d');g.take('4883fbfe');g.branch('0f83',False)
    table=g.relative('488d0d');capacity=g.relative('4c8b25');g.take('4983fc04');g.branch('0f82',False)
    g.take('488d4301');threshold=g.relative('483b05');g.branch('0f87',False)
    g.take('4533d2','4d8d7424ff','488b5608','488b02','8b4848','488b4208','48c1e803','4803c8')
    g.take('4c69c9');prime=int.from_bytes(g.read(4),'little',signed=True);need('positive-polynomial-prime',0<prime<1<<31)
    g.take('488b4210','48c1e803','4c03c8','49c7c5ffffffff','4c8bc2')
    slots=g.relative('4c8b1d');sentinel=g.relative('488b2d');deleted=g.relative('4c8b3d')
    g.take('4d23ce','4b8d0449','413b2cc3');g.branch('0f84',not duplicate)
    compared=False
    if duplicate:
        g.take('4d85ff');g.branch('0f85',False)
        g.take('4b8d0c49','418b04cb','3906');g.branch('0f84',True)
        g.take('833e00');g.branch('75',False,1)
        g.take('498b54cb08','488b02','493900');g.branch('0f85',False)
        g.take('488b4208','49394008');g.branch('75',False,1)
        g.take('488b4210','49394010');g.branch('75',False,1)
        g.take('b001','84c0');g.branch('0f84',False)
        g.take('49c7c5ffffffff','4d3bcd');g.branch('0f84',False);g.jump('e9')
        need('same-table-existing-output',g.relative('488d05')==table)
        g.take('4889442420','4b8d0449','498d0cc3','48894c2428','4b8d0464','498d0cc3','48894c2430','32c0');g.jump('e9')
        compared=True
    else:
        g.take('85ed');g.branch('75',True,1)
        g.take('4983fdff');g.branch('75',False,1)
        g.take('4d8be9','488bc3','492bc7','48b9aaaaaaaaaaaaaa0a','483bc1');g.branch('0f83',False)
        g.take('4d85ff');g.branch('0f85',False)
        g.take('48ffc3');need('same-occupied-count-store',g.relative('48891d')==occupied)
        g.take('4a8d0c6d00000000','4903cd','8b06','418904cb','488b4608','498944cb08','488b4610','498944cb10')
        need('same-table-new-output',g.relative('488d05')==table)
        g.take('4889442420','4a8d046d00000000','4903c5');need('same-slots-new-output',g.relative('488b15')==slots)
        g.take('488d04c2','4889442428');need('same-capacity-new-output',g.relative('488b05')==capacity)
        g.take('488d0c40','488d04ca','4889442430','b001')
    g.take('0f10442420','0f1107','f20f104c2430','f20f114f10','884718','488bc7','4c8d9c24b0000000',
        '498b5b30','498b6b38','498b7340','498be3','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,duplicate=duplicate,markerCell=marker,markerByteMustBeZero=True,
        occupiedCountCell=occupied,tableAddress=table,capacityCell=capacity,capacityAtLeastFourRequired=True,
        capacityThresholdCell=threshold,capacityThresholdSufficientRequired=True,slotsCell=slots,
        sentinelCell=sentinel,sentinelMustBeNonzero=True,deletedCountCell=deleted,deletedCountMustBeZero=True,
        slotBytes=24,slotTagOffset=0,slotKeyOffset=8,slotTripleOffset=16,hashMethodPointeeDwordOffset=72,
        hashPointerShift=3,hashPrime=prime,hashPointerKeyOffsets=[8,16],comparedKeyQwordOffsets=[0,8,16]if compared else[],
        inputPairTagMustBeZero=True,everyDuplicateKeyPointerCompared=compared,
        unchangedIncomingTagKeyAndTriplePublished=not duplicate,equalExistingEntryNotOverwritten=duplicate,
        outputOffsets=dict(table=0,current=8,end=16,insertedByte=24),insertedFlag=0 if duplicate else 1,
        outputAndReturnAreOriginalRdx=True,opaqueCalls=0,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],normalReturn=True,
        arbitraryProbeOrResizeAndWholeTableHistoryProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_method_table_seed_paths import derive as seed_source
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import _complete_family
    _publication_gate(image,pins);prior=seed_source(image,pins,**arguments)
    target=prior['proof']['selectedSeedProgram']['insertionTarget']
    body,rows,cfg,padding=_complete_family(image,target)
    programs=[program(body['regions'],target,duplicate=flag)for flag in(False,True)]
    selection=prior['proof']['argumentSeedSource']['proof']['methodSelectionSource']['proof']['selectedNormalizedHit']
    need('same-insertion-and-normalized-selection-slots-and-capacity',all(
        p['slotsCell']==selection['slotsCell']and p['capacityCell']==selection['capacityCell']
        and p['slotBytes']==selection['slotBytes']and p['comparedKeyQwordOffsets']in([],selection['keyQwordOffsets'])for p in programs))
    # The exact selected lookup byte grammar independently checks the same
    # literal hash multiplier, pointee token offset and both pointer shifts.
    need('same-explicit-key-storage-layout',programs[0]['slotKeyOffset']==selection['slotKeyPointerOffset']
        and programs[0]['slotTripleOffset']==selection['slotValuePointerOffset'])
    multipliers=[int.from_bytes(bytes.fromhex(raw)[3:],'little',signed=True)for at,raw in selection['selectedBytes']
        if raw.startswith('4c69c9')and len(bytes.fromhex(raw))==7]
    need('same-actual-insertion-and-both-selection-hash-multipliers',len(multipliers)==2
        and all(p['hashPrime']==prime for p in programs for prime in multipliers))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(methodTableSeedSource=prior,insertionWindows=body['windows'],insertionCfg=cfg,
            insertionPadding=padding,selectedInsertionPrograms=programs),
        actualSelectedKeyTripleInsertionAndEqualKeyRetentionProved=True,initializedMethodKeyTableIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Full current insertion byte partition/CFG and selected call-free first-empty/new and equal-pointer-key/duplicate transfers and output/full frames, joined to actual seed and pointer lookup.',
            conditional=__doc__,structuralOnly='Runtime generic method-key to native index-triple table.',
            unresolved=['reservation/resize/collision induction and complete initialized table history',
                'method descriptor and canonical instantiation pointer identity','actual provider/MethodInfo/callback selection',
                'startup execution and opaque aliases','wire/parent/EOF']))))
