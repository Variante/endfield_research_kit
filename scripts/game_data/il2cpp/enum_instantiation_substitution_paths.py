"""Selected actual count1 instantiation substitution and interner return.

The complete actual helper has a checked instruction partition/control graph.
Its null path returns zero with the original frame. Its explicit count1 path
owns the aligned dynamic buffer/frame, passes each unchanged input carrier
and actual generic context/flag to the independently proved type substitution,
and places that actual result into the same buffer used by the hash/comparator.
The selected occupied/equal interner path checks count and argument contents,
then returns that actual slot's unchanged instantiation after unlocking.

Only count1 has a selected dynamic-frame certificate. Coherent bounded input
instantiation/context, ordinary stack probing/Win64 helpers, unchanged counted
loop registers, stable disjoint cache storage, the explicit first occupied
equal slot and comparison zero are conditions. No insertion, complete probe
termination, canonical static pointer, live RGCTX or callback identity follows.
Native count/pointer records do not specify any enum or collection wire width.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-instantiation-substitution-paths.v1'
LABEL='enumInstantiationSubstitutionPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def _prefix(regions,entry,*,nonnull):
    g=BytesPath(regions,entry);g.take('4055','56','57','4154','4155','4156','4157','4883ec50','488d6c2420',
        '48895d78','410fb6f0','4c8bf2','488bf9','4885c9');g.branch('75',nonnull,1)
    return g


def _restore(g):
    g.take('488b5d78','488d6530','415f','415e','415d','415c','5f','5e','5d','c3')


def null_program(regions,entry):
    g=_prefix(regions,entry,nonnull=False);g.take('33c0');g.jump('e9');_restore(g)
    return dict(selectedBytes=g.seen,entry=entry,inputInstantiationMustBeNull=True,returnsZero=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def hit_program(regions,entry):
    g=_prefix(regions,entry,nonnull=True);g.take('8b01','48c1e003','488d480f','483bc8');g.branch('77',True,1)
    g.take('4883e1f0','488bc1');probe=g.relative('e8');g.take('482be1','4c8d642420','33db','391f');g.branch('76',False,1)
    g.take('0f1f4000','66660f1f840000000000');loop=g.at
    g.take('488b4f08','440fb6c6','498bd6','488b0cd9');substitute_site=g.at;substitute=g.relative('e8')
    g.take('498904dc','48ffc3','8b07','483bd8');need('same-count1-substitution-loop',g.relative('72',1)==loop)
    g.take('448b2f','44896d70','44896d08','4c896510');mutex=g.relative('488d05');g.take('48898588000000')
    need('same-actual-lock-cell',g.relative('488b0d')==mutex);lock=g.relative('ff15');g.take('90')
    end=g.relative('488b05');begin=g.relative('483b05');g.branch('75',True,1)
    g.take('48c7858800000000000000');capacity=g.relative('4c8b1d');g.take('49ffcb','4c895d00','8b5d08','8bfb','4533c0','85db')
    g.branch('74',False,1);g.take('4c8b5510');hash_loop=g.at
    g.take('4b8b0cc2');hash_site=g.at;hashing=g.relative('e8');g.take('4869ff')
    prime=int.from_bytes(g.read(4),'little',signed=True);need('positive-actual-polynomial-prime',0<prime<1<<31)
    g.take('4803f8','49ffc0','4c3bc3');need('same-count1-hash-loop',g.relative('72',1)==hash_loop)
    g.take('4923fb','4c8beb');slots=g.relative('4c8b3d');g.take('6690','488bc7','4803c0')
    sentinel=g.relative('488b0d');g.take('413b0cc7');g.branch('75',True,1)
    need('same-zero-probe-condition-cell',g.relative('48833d')+1==begin);g.take('00');g.branch('76',True,1)
    g.take('488bc7','4803c0','41833cc700');g.branch('75',False,1)
    g.take('498b4cc708','3b19');g.branch('75',False,1)
    g.take('33f6','4d85ed');g.branch('74',False,1)
    g.take('488b5d10','4c8b7108','4c2bf3','660f1f840000000000');compare_loop=g.at
    g.take('498b141e','488b0b');compare_site=g.at;compare=g.relative('e8')
    g.take('85c0');g.branch('75',False,1)
    g.take('48ffc6','4883c308','493bf5');need('same-count1-compare-loop',g.relative('72',1)==compare_loop)
    g.take('4883ffff');g.branch('0f84',False);g.take('48c1e704','4903ff','448b6d70')
    need('same-selected-capacity-at-return',g.relative('4c8b15')==capacity)
    g.take('49c1e204','4d03d7','493bfa');g.branch('74',False,1)
    g.take('488b5f08');need('same-selected-unlock-cell',g.relative('488b0d')==mutex)
    unlock=g.relative('ff15');g.take('90');g.jump('e9');g.take('488bc3');_restore(g)
    return dict(selectedBytes=g.seen,entry=entry,inputArgumentCount=1,inputInstantiationVectorOffset=8,
        actualStackProbe=probe,actualTypeSubstitutionCall=substitute_site,actualTypeSubstitution=substitute,
        substitutionArguments=dict(rcx='unchanged input instantiation argument0',rdx='unchanged incoming generic context',
            r8d='zero-extended unchanged incoming R8B'),actualSubstitutionOutputStoredUnchanged=True,
        bufferStore='owned aligned count1 buffer[0]',internerBuffer='same actual substitution-output buffer',
        actualMutexCell=mutex,lockIatCell=lock,unlockIatCell=unlock,tableEndCell=end,tableBeginCell=begin,
        countZeroCellMustBeZero=True,capacityCell=capacity,slotsCell=slots,sentinelCell=sentinel,
        hashCall=hash_site,hashTarget=hashing,slotHashPrime=prime,slotHash='(1*slotHashPrime+actual substituted carrier hash)&(capacity-1)',
        compareCall=compare_site,compareTarget=compare,compareArguments=dict(rcx='same actual substitution-output buffer[0]',
            rdx='actual candidate instantiation argument0'),comparatorZeroRequired=True,candidateCountMustBeOne=True,
        candidateTagMustBeZeroAndDifferFromSentinel=True,selectedSlotMustNotBeCapacityEndOrMinusOne=True,
        returnedCandidateInstantiationUnchanged=True,count1DynamicAllocationBytes=16,count1BufferBytes=8,
        entryRspBeforeDynamicAllocation=-136,entryRspAtCallsAfterProbe=-152,frameRbpFromEntryRsp=-104,
        selectedReturnRspFromRbp=48,selectedBufferFromEntryRsp=-120,normalAbiPreservingProbeAndHelpersRequired=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        otherAritiesFramesProved=False,liveInternerOrCanonicalStaticPointerIdentityProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_type_substitution_paths import derive as type_source,constructed_program
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.consumer_control import build_consumer_control_graph
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=type_source(image,pins,**arguments)
    type_entry=prior['proof']['selectedKindPrograms'][0]['entry'];type_body=owned(image,type_entry)
    at=unique(type_body['regions'],bytes.fromhex('488b07488b48084885c97512'))
    g=BytesPath(type_body['regions'],at);g.take('488b07','488b4808','4885c9');g.branch('75',True,1);target=g.relative('e8')
    body=owned(image,target);rows=[]
    for start,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,start),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));graph=build_consumer_control_graph(rows,entry=target,
        owned_ranges=[(a,a+len(raw))for a,raw in body['regions']])
    need('complete-source-reachable-from-actual-entry',not graph['nonEntryInstructions'])
    hit=hit_program(body['regions'],target);null=null_program(body['regions'],target)
    need('same-independently-proved-actual-type-substitution',hit['actualTypeSubstitution']==type_entry)
    inflated=prior['proof']['inflatedMethodSource'];constructed=inflated['proof']['constructedClassSource']
    generic=[constructed_program(type_body['regions'],type_entry,image_base=image.pe.image_base,changed_key=k)for k in(False,True)]
    normal=constructed['proof']['managedArgumentSource']['proof']['nativeGenericKeySource']['proof']['receiverSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']
    projection=normal['proof']['classFieldSource']['proof']['typeDataFixup']['proof']['projection']
    from scripts.game_data.il2cpp.record_index_geometry import prove_record_index_geometry
    geometry=prove_record_index_geometry(multiplier=generic[0]['recordMultiplier'],shift=generic[0]['recordShift'],
        record_bytes=image.metadata.type_record_size,records=len(image.metadata.types))
    for p in generic:
        need('same-actual-generic-carrier-instantiation-and-class-key-helpers',p['actualInstantiationSubstitution']==target
            and p['actualGenericClassKeyConstructor']==inflated['proof']['selectedClassKeyPrograms'][0]['selectedBytes'][0][0])
        need('same-independent-generic-original-definition-record-projection',p['actualDefinitionClassResolver']==projection['tailTarget']
            and p['metadataHeaderCell']==projection['metadataHeaderCell']and p['metadataBaseCell']==projection['metadataBaseCell']
            and p['recordSectionHeaderOffset']==projection['headerOffsetField'])
    key=constructed['proof']['managedArgumentSource']['proof']['nativeGenericKeySource']['proof']['receiverSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['selectedHit']
    pairs=[('hashTarget','hashTarget'),('compareTarget','compareTarget'),('capacityCell','entryPrefix.capacityCell'),
        ('slotsCell','slotsCell'),('sentinelCell','sentinelCell'),('tableBeginCell','entryPrefix.tableBeginCell'),
        ('slotHashPrime','slotHashPrime'),('actualMutexCell','entryPrefix.mutexCell')]
    for left,right in pairs:
        actual=key
        for name in right.split('.'):actual=actual[name]
        need('same-independent-interner-'+left,hit[left]==actual)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(typeSubstitutionSource=prior,actualSourceWindows=body['windows'],completeControlGraph=graph,
            selectedCount1Hit=hit,nullInstantiation=null,selectedConstructedCarrierSubstitutions=generic,
            constructedDefinitionRecordGeometry=geometry),
        actualSubstitutedCarrierBufferAndConditionalInternerReturnProved=True,allAritiesNormalFramesProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete actual instantiation helper instruction/control partition and selected null/count1 substitution/hash/compare/return/frame paths with independent helper/cache joins.',
            conditional=__doc__,structuralOnly='Native instantiation/vector transport.',
            unresolved=['actual initialized nominal parameter/context and cache population/selection',
                'insertion/other probes and arities','complete initialized class RGCTX/callback','enum/list/parent/EOF'])),default=_json_set))
