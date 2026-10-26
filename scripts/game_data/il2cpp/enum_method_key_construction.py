"""Actual MethodSpec dependencies and conditional method-key construction.

The exact selected definition resolver uses the incoming method index for its
cache and metadata-record selection, obtains the declaring class, invokes its
actual method setup, selects the ordinal relative to that class's recorded
method start, and publishes the unchanged resulting MethodInfo pointer. Its
separate hot path reads the same cache index. Descriptor creation and method
setup remain explicit opaque conditions, rather than static pointer aliases.

The selected same-thread recursive-lock paths preserve all three incoming key
arguments. A selected lookup hit returns the existing key pointer. A selected
miss requests one 24-byte allocation, writes the unchanged method/class-inst/
method-inst pointers at offsets0/8/16 and supplies that exact key to its actual
insertion call. Both paths release one recursion level and restore the full
frame. Lookup/insertion, allocator success, coherent recursion/cache state,
startup execution and actual MemoryPack callback selection remain unresolved.
These source programs grant no enum wire, collection or whole-owner grammar.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-method-key-construction.v1'
LABEL='enumMethodKeyConstruction'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def definition_program(regions,entry,*,cold=True):
    need('literal-definition-cache-path',type(cold)is bool);g=BytesPath(regions,entry)
    g.take('4053','4883ec20','4863d9');cache=g.relative('488b0d')
    g.take('48833cd900');g.branch('74',cold,1)
    fields={}
    if cold:
        header=g.relative('488b05');g.take('4c8bc3');metadata=g.relative('488b0d')
        g.take('49c1e005','48897c2430','48635030','4803ca','418b4c0804')
        class_resolver=g.relative('e8');g.take('488bc8','488bf8');setup=g.relative('e8')
        g.take('488b4768','8bcb','2b4824','488b8798000000','488b7c2430','4863c9','488b0cc8')
        need('same-definition-cache-publication',g.relative('488b05')==cache)
        g.take('48890cd8');need('same-definition-cache-return',g.relative('488b05')==cache)
        g.take('488b04d8')
        fields=dict(metadataHeaderCell=header,metadataBaseCell=metadata,methodSectionHeaderOffset=48,
            methodRecordBytes=32,declaringTypeIndexOffset=4,classResolverTarget=class_resolver,
            methodSetupTarget=setup,setupReceiver='unchanged actual class-resolver result',
            classMetadataRecordOffset=104,classMethodStartOffset=36,classMethodsPointerOffset=152,
            selectedOrdinal='incoming method index minus actual class metadata methodStart',
            unchangedSelectedMethodInfoStoredAtSameIndex=True,coherentNormalSetupMethodsRequired=True)
    else:g.take('488b04d9')
    g.take('4883c420','5b','c3')
    return dict(selectedBytes=g.seen,cold=cold,cacheCell=cache,cachePointerStride=8,
        validMethodIndexAndClassOrdinalRequired=True,cacheAndOpaqueAliasesMustRemainCoherent=True,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rdi']if cold else['rbx'],normalReturn=True,**fields)


def key_program(regions,entry,*,miss=False):
    need('literal-key-lookup-path',type(miss)is bool);g=BytesPath(regions,entry)
    g.take('488bc4','48895810','48896818','48897020','57','4156','4157','4883ec70',
        '498bf8','488bf2','488be9','488948a8','488950b0','4c8940b8')
    mutex=g.relative('4c8d3d');g.take('4c897808');current_thread=g.relative('ff15');g.take('488bd8')
    owner=g.relative('4c8b0d');g.take('493bc1');g.branch('74',True,1);depth=g.relative('ff05')
    g.take('4533f6','4489742420','488d442430','4889442428','4c8d442420','488d542448')
    lookup_site=g.at;lookup=g.relative('e8');capacity=g.relative('488b05');g.take('48c1e004')
    slots=g.relative('480305');g.take('488b5c2450','483bd8');g.branch('74',miss,1)
    allocation=None
    if miss:
        g.take('ba01000000','41b818000000');allocator=g.relative('488b0d');allocate=g.relative('e8')
        g.take('488bd8','488928','48897008','48897810','4489742420','4889442428',
            '4c8d442420','488d542448');insert_site=g.at;insert=g.relative('e8');g.take('90')
        allocation=dict(allocatorCell=allocator,actualAllocationTarget=allocate,rdxCount=1,r8ElementBytes=24,
            normalNonNullDisjointWritable24BytesRequired=True,keyFieldOffsets=[0,8,16],
            keyFieldValues=['unchanged incoming method pointer','unchanged incoming class-inst pointer',
                'unchanged incoming method-inst pointer'],insertionCall=insert_site,insertionTarget=insert,
            insertionPairTag=0,insertionPairKey='unchanged allocated key pointer',
            insertionAndAllocationSemanticsProved=False)
    else:g.take('488b5b08');g.jump('eb',1)
    need('same-recursive-lock-depth-reload',g.relative('8b15')==depth)
    g.take('85d2');g.branch('7e',False,1);g.take('83fa01');g.branch('75',True,1)
    g.take('ffca');need('same-recursive-depth-release',g.relative('8915')==depth)
    g.take('488bc3','4c8d5c2470','498b5b28','498b6b30','498b7338','498be3','415f','415e','5f','c3')
    return dict(selectedBytes=g.seen,miss=miss,mutexAddress=mutex,currentThreadIatCell=current_thread,
        ownerCell=owner,depthCell=depth,currentThreadAlreadyOwnsMutexRequired=True,
        entryDepthAtLeastOneAndNoOverflowRequired=True,oneRecursionLevelReleased=True,
        inputKeyQwordOffsets=[0,8,16],lookupPairTag=0,lookupPairKey='address of exact incoming three pointer locals',
        lookupCall=lookup_site,lookupTarget=lookup,capacityCell=capacity,slotsCell=slots,slotBytes=16,
        selectedLookupMustReturnEnd=miss,returnedKey='unchanged allocated key'if miss else'existing selected slot +8 key pointer',
        allocation=allocation,entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r14','r15'],
        normalReturn=True,lookupInsertionAndKeyCanonicalIdentityProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_method_table_seed_paths import derive as seed_source
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import _complete_family
    _publication_gate(image,pins);prior=seed_source(image,pins,**arguments)
    cold=prior['proof']['keyResolverPrograms'][1]
    definition,rows,graph,padding=_complete_family(image,cold['methodDefinitionTarget'])
    definitions=[definition_program(definition['regions'],definition['pointer'],cold=flag)for flag in(False,True)]
    key,rows,key_graph,key_padding=_complete_family(image,cold['keyConstructorTarget'])
    keys=[key_program(key['regions'],key['pointer'],miss=flag)for flag in(False,True)]
    selection=prior['proof']['argumentSeedSource']['proof']['methodSelectionSource']
    lookup=selection['proof']['primitiveNormalizerSource']['proof']['nameAndInternerSource']
    class_entry=lookup['proof']['recordClassPaths'][0]['selectedBytes'][0][0]
    need('same-independently-proved-record-class-resolver',definitions[1]['classResolverTarget']==class_entry)
    # Exact direct targets are structural dependencies. The parent programs
    # prove their argument/result transfers, never opaque callee semantics.
    dependencies={}
    for role,target in dict(methodSetup=definitions[1]['methodSetupTarget'],lookup=keys[0]['lookupTarget'],
            insertion=keys[1]['allocation']['insertionTarget'],allocation=keys[1]['allocation']['actualAllocationTarget']).items():
        dependencies[role]=dict(entry=target,semanticsProved=False)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(methodTableSeedSource=prior,definitionWindows=definition['windows'],definitionCfg=graph,
            definitionPadding=padding,definitionPrograms=definitions,keyWindows=key['windows'],keyCfg=key_graph,
            keyPadding=key_padding,keyPrograms=keys,dependencies=dependencies),
        actualMethodDefinitionAndKeyFieldTransfersProved=True,initializedMethodKeyTableIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete selected MethodInfo cache and same-thread recursive method-key hit/miss source transfers, owned byte partitions/CFGs/frames and actual dependency entries.',
            conditional=__doc__,structuralOnly='Runtime method descriptors and three-pointer generic method keys.',
            unresolved=['method setup and descriptor/cache coherence','allocator and key-table lookup/insertion semantics',
                'startup initialized tables and opaque aliases','actual MemoryPack receiver/MethodInfo/callback','wire/parent/EOF']))))
