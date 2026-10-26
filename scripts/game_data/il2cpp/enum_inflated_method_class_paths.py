"""Original nominal class/context versus shared code in MethodInfo creation.

The complete current inflated lookup and constructor families have independent
owned instruction/CFG/normal-frame checks. The selected empty lookup transfers
the unchanged actual key and false copy-key flag to its actual constructor.
The constructor's explicit recursive-lock/both-cache-miss/two-parameter path
retains the original definition and class-instantiation. Its actual class-key
helper receives the original definition class's byval carrier and unchanged
class-instantiation, then either its cached class or the separately proved
class-creation return supplies MethodInfo.class. That class is stored before
the independent pointer resolver receives the original method definition and
address of the original class/method-instantiation pair. Its actual output
words supply the code/adjustor/invoker fields. Pointer lookup normalization
does not substitute a placeholder class into that earlier explicit store.

The class-key helper's complete source and selected recursive hit/new paths
retain both actual input key words, including on the exact one32 allocation;
the other key words require zeroed disjoint allocation. Conditional cache hits
do not infer canonical pointer equality. Correct incoming definition/key,
coherent recursive mutex/cache and allocation/substitution/parameter/helper
effects remain conditions. Later constructor/class initialization, live
MethodInfo/RGCTX contents and actual MemoryPack callback are not admitted.
No concrete enum/list/wire/parent/whole owner follows from these source joins.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-inflated-method-class-paths.v1'
LABEL='enumInflatedMethodClassPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def lookup_empty_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4154','4155','4156','4157',
        '4883ec20','0fb6ea','488bf9','4885c9');g.branch('0f84',False)
    mutex=g.relative('488b0d');lock=g.relative('ff15');occupied=g.relative('4c8b0d');capacity=g.relative('488b35')
    slots=g.relative('4c8b05');end_state=g.relative('4c390d');g.branch('0f84',True)
    g.take('488d0476','498d1cc0');g.jump('e9')
    g.take('488d0476','498d0cc0','483bd9');g.branch('0f85',False)
    need('same-empty-lookup-mutex-release',g.relative('488b0d')==mutex);unlock=g.relative('ff15');g.take('90','488b07')
    excluded=[g.relative('488d0d'),g.relative('4c8d05')]
    g.take('483bc1');g.branch('0f84',False);g.take('493bc0');g.branch('0f84',False)
    g.take('400fb6d5','488bcf');call=g.at;constructor=g.relative('e8')
    g.take('488b5c2450','488b6c2458','488b742460','4883c420','415f','415e','415d','415c','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,mutexCell=mutex,lockIatCell=lock,unlockIatCell=unlock,
        occupiedCell=occupied,capacityCell=capacity,slotsCell=slots,endStateCell=end_state,
        excludedDefinitionAddresses=excluded,actualConstructorCall=call,actualConstructor=constructor,
        constructorArguments=dict(rcx='unchanged incoming method key',edx='unchanged zero-extended incoming DL'),
        incomingDlMustBeZero=True,selectedTableMustBeEmpty=True,originalDefinitionMustDifferFromExcludedSentinels=True,
        actualConstructorResultReturnedUnchanged=True,entryRspRestored=True,allNonvolatilesRestored=True)


def class_key_program(regions,entry,*,miss):
    need('literal-current-class-key-path',type(miss)is bool)
    g=BytesPath(regions,entry);g.take('488bc4','48895810','48896818','56','57','4156','4881ec90000000',
        '488bfa','488bf1','0f57c0','f30f7f40d0','488948c0','488950c8')
    mutex=g.relative('4c8d35');g.take('4c897008');thread=g.relative('ff15');g.take('488bd8')
    owner=g.relative('4c8b05');g.take('493bc0');g.branch('74',True,1);depth=g.relative('ff05')
    g.take('33ed','896c2430','488d442468','4889442438','4c8d442430','488d542448');lookup=g.relative('e8')
    capacity=g.relative('4c8b05');g.take('49c1e004');slots=g.relative('4c0305')
    g.take('c644242001','4d8bc8','488d4c2430');iterator=g.relative('e8')
    g.take('488b5c2450','483b5c2438');g.branch('74',miss,1)
    allocate=None;insert=None
    if miss:
        g.take('ba01000000','41b820000000');allocator=g.relative('488b0d');allocate=g.relative('e8')
        g.take('488bd8','488930','48897808','896c2430','4889442438','4c8d442430','488d542448');insert=g.relative('e8')
        stats=g.relative('f048ff05')
    else:g.take('488b5b08');g.jump('eb',1)
    need('same-class-key-recursive-depth',g.relative('8b15')==depth)
    g.take('85d2');g.branch('7e',False,1);g.take('83fa01');g.branch('75',True,1)
    g.take('ffca');need('same-class-key-recursive-release',g.relative('8915')==depth)
    g.take('488bc3','4c8d9c2490000000','498b5b28','498b6b30','498be3','415e','5f','5e','c3')
    result=dict(selectedBytes=g.seen,entry=entry,miss=miss,mutexAddress=mutex,threadIatCell=thread,ownerCell=owner,depthCell=depth,
        actualLookup=lookup,actualIterator=iterator,capacityCell=capacity,slotsCell=slots,
        actualAllocation=allocate,actualInsertion=insert,incomingClassCarrierAndInstantiationUnchanged=True,
        selectedKeyWords=['unchanged incoming RCX type carrier','unchanged incoming RDX class instantiation',0,0],
        recursiveOwnerPositiveDepthAndBoundedIncrementRequired=True,entryRspRestored=True,allNonvolatilesRestored=True,
        initializedKeyCanonicalIdentityProved=False)
    if miss:result['allocation']=dict(contextCell=allocator,count=1,bytes=32,zeroedDisjointAllocationRequired=True,statsCell=stats)
    return result


def constructor_program(regions,entry,*,class_cached):
    need('literal-current-constructor-class-cache-path',type(class_cached)is bool)
    g=BytesPath(regions,entry);g.take('48895c2410','55','56','57','4154','4155','4156','4157','488bec','4883ec60',
        '0fb6fa','4c8bf9');mutex=g.relative('488d05');g.take('48894540');thread=g.relative('ff15')
    g.take('488bd8');owner=g.relative('4c8b05');g.take('48c7c6ffffffff','493bc0');g.branch('74',True,1)
    depth=g.relative('ff05');g.take('4533f6','448975c0','4c897dc8','4c8d4550','488d55c0')
    first_cache=g.relative('488d0d');first_lookup=g.relative('e8');g.take('84c0');g.branch('0f85',False)
    g.take('448975c0','4c897dc8','4c8d4550','488d55c0')
    second_cache=g.relative('488d0d');second_lookup=g.relative('e8');need('same-two-cache-lookup-helper',first_lookup==second_lookup)
    g.take('84c0');g.branch('0f85',False)
    g.take('4084ff');g.branch('74',True,1)
    definition_origin=g.at;g.take('4d8b2f','498b5d20','4d397708');g.branch('74',False,1)
    g.take('488d4b20','498b5708');class_key=g.relative('e8')
    g.take('488b5818','4885db');g.branch('75',class_cached,1)
    create=None
    if not class_cached:
        g.take('b201','488bc8');create=g.relative('e8');g.take('488bd8','4885c0');g.branch('75',True,1)
    g.take('b860000000','41b858000000');options=g.relative('4c3935');g.take('440f45c0','ba01000000')
    allocator=g.relative('488b0d');allocate=g.relative('e8');g.take('48894550','448975c0','4c897dc8','4c8d4550','488d55c0')
    need('same-in-progress-cache-before-allocation-publication',g.relative('488d0d')==second_cache)
    insert=g.relative('e8');g.take('488b7d50');class_store=g.at;g.take('48895f20',
        '410fb7454c','6689474c','410fb7454e','6689474e','410fb74550','66894750','498b4518','48894718',
        '0fb64754','24fe','0c02','884754','418b4548','894748','498d5708','41b001','498b4d28')
    inflate=g.relative('e8');g.take('48894728','410fb64553','884753','450fb66553','498b4530','48894558',
        '418bd4','41b808000000');need('same-actual-parameter-allocator-context',g.relative('488b0d')==allocator)
    parameters=g.relative('e8');need('same-actual-allocator-target',parameters==allocate)
    g.take('488945c0','4584e4');g.branch('74',False,1)
    g.take('4c8bf0','488b7d58','482bf8');loop=g.at
    for index in range(2):
        g.take('41b001','498d5708','4a8b0c37');need('same-actual-parameter-type-inflater',g.relative('e8')==inflate)
        g.take('498906','4d8d7608','4983ec01');back=g.relative('75',1);need('same-two-parameter-loop-backedge',back==loop)
        if index==0:g.at=back
    g.take('488b7d50','48c7c6ffffffff','488b45c0','4533f6','48894730');random=g.relative('e8')
    g.take('448bc0','b881808080','41f7e8','4103d0','c1fa07','8bca','c1e91f','03d1','4102d0',
        '325752','80e201','305752','4c897f40','49837f1000');g.branch('75',False,1)
    g.take('41f6455401');g.branch('74',True,1)
    g.take('48837b6000');g.branch('75',True,1)
    g.take('498b4538','48894738','4d8d4708','498bd5','488d4de0');pointer_call=g.at;pointers=g.relative('e8')
    g.take('0f1008','0f105010','0f1155c0','f30f7e4008','66480fd64708','66480f7ec8','488907','4885c0')
    g.branch('74',False,1);g.take('66480fd65710');end=g.at
    return dict(selectedBytes=g.seen,entry=entry,end=end,classCached=class_cached,mutexAddress=mutex,threadIatCell=thread,
        ownerCell=owner,depthCell=depth,firstCache=first_cache,secondCache=second_cache,actualCacheLookup=first_lookup,
        actualCacheInsertion=insert,definitionOrigin=definition_origin,actualClassKeyConstructor=class_key,
        classKeyArguments=dict(rcx='original MethodInfo.class byval carrier at+32',rdx='unchanged original key.class-inst'),
        actualClassCreation=create,selectedClassMustBeNonnull=True,actualAllocator=allocate,allocatorContextCell=allocator,
        methodInfoBytesWhenOptionsCellZero=88,alternateOptionsMethodInfoBytes=96,optionsCell=options,optionsCellMustBeZero=True,
        classStore=class_store,methodInfoClassOffset=32,methodInfoClassValue='actual original nominal class from original class-inst key',
        originalDefinitionRegister='r13',originalKeyRegister='r15',methodInfoRegister='rdi',
        actualTypeSubstitution=inflate,selectedParameterCount=2,parameterPointerStride=8,
        originalDefinitionTokenOffset=72,methodInfoTokenOffset=72,originalKeyStoredAtMethodInfoOffset=64,
        originalMethodContextCopiedToMethodInfoOffset=56,actualRandomizationHelper=random,
        actualPointerResolverCall=pointer_call,actualPointerResolver=pointers,
        pointerResolverArguments=dict(rcx='owned stack output',rdx='unchanged original MethodInfo definition',
            r8='address of unchanged original key.class-inst/method-inst pair'),
        pointerOutputFieldOffsets=[0,8,16],sourcePointerOutputOffsets=[0,8,16],selectedPrimaryMustBeNonnull=True,
        originalClassStoredBeforeIndependentPointerResolution=True,completeConstructorReturnOrLiveContextProved=False,
        recursiveLockAndTwoCacheMissesRequired=True,originalCopyKeyFlagMustBeZero=True,
        selectedDefinitionNonGenericMethodAndActualTwoParametersRequired=True,
        normalDisjointAllocationLookupInsertionSubstitutionAndRandomHelpersRequired=True)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_encoded_method_paths import derive as encoded_source
    from scripts.game_data.il2cpp.enum_constructed_class_paths import derive as class_source,_json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=encoded_source(image,pins,**arguments)
    constructed_arguments={k:arguments[k]for k in('enum_requests','normalizer_entry','publication_entry','fixup_arguments')}
    if 'enum_variant'in arguments:constructed_arguments['enum_variant']=arguments['enum_variant']
    constructed=class_source(image,pins,**constructed_arguments)
    entry,=[p['tailTarget']for p in prior['proof']['encodedResolverPaths']if p['tag']==6]
    lookup=owned(image,entry);selected_lookup=lookup_empty_program(lookup['regions'],entry)
    constructor=owned(image,selected_lookup['actualConstructor'])
    programs=[constructor_program(constructor['regions'],constructor['pointer'],class_cached=c)for c in(False,True)]
    need('same-independent-actual-constructed-class-owner',programs[0]['actualClassCreation']==constructed['proof']['selectedClassCachePath']['entry'])
    method_key=prior['proof']['descriptorSource']['proof']['methodKeySource']
    selection=method_key['proof']['methodTableSeedSource']['proof']['argumentSeedSource']['proof']['methodSelectionSource']
    need('same-independent-actual-method-pointer-resolver',all(p['actualPointerResolver']==selection['proof']['selectedNormalizedHit']['selectedBytes'][0][0]for p in programs))
    definitions=[]
    for registered in selection['proof']['selectedPlaceholderRegistrations']:
        method=image.metadata.methods[registered['methodDefinition']]
        need('actual-placeholder-definition-has-selected-two-parameter-slot5-ABI',method.parameter_count==2
            and method.slot==5 and not method.flags&0x10 and image.metadata.string(method.name_index)=='Deserialize')
        definitions.append(dict(formatterType=registered['formatterType'],methodDefinition=method.index,
            actualToken=method.token,declaringType=method.declaring_type,parameterCount=method.parameter_count,
            actualIncomingDescriptorIdentityProved=False))
    key=owned(image,programs[0]['actualClassKeyConstructor']);key_paths=[class_key_program(key['regions'],key['pointer'],miss=m)for m in(False,True)]
    independent=constructed['proof']['managedArgumentSource']['proof']['nativeGenericKeySource']['proof']['count1Programs'][1]
    need('same-actual-class-key-cache-lookup-insertion-and-iterator',key_paths[1]['actualLookup']==independent['actualLookupTarget']
        and key_paths[1]['actualIterator']==independent['actualIteratorHelper']
        and key_paths[1]['actualInsertion']==independent['allocation']['insertionTarget']
        and key_paths[1]['capacityCell']==independent['keyTableCapacityCell']and key_paths[1]['slotsCell']==independent['keyTableSlotsCell'])
    graphs={}
    for role,body in(('lookup',lookup),('constructor',constructor),('classKey',key)):
        rows=[]
        for at,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
        rows.sort(key=lambda r:int(r['va'],16));graph,padding=complete_program(body['regions'],rows,body['pointer'])
        graphs[role]=dict(control=graph,padding=padding,windows=body['windows'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(encodedSource=prior,constructedClassSource=constructed,completeFamilies=graphs,
            selectedEmptyLookup=selected_lookup,selectedConstructorPrograms=programs,selectedClassKeyPrograms=key_paths,
            intendedPlaceholderDefinitions=definitions),
        originalClassInstantiationAndSeparateCodeProjectionTransfersProved=True,
        actualInitializedMethodInfoClassOrRgctxIdentityProved=False,concreteEnumCallbackSelected=False,
        wireGrammarAdmitted=False,wholeOwnerAdmitted=False,evidenceBoundary=dict(
            exact='Complete selected inflated lookup/constructor/class-key source partitions/CFGs/frames, empty lookup and two explicit two-parameter constructor prefixes through original-class and pointer-word stores, fresh independent code/class/cache helper joins.',
            conditional=__doc__,structuralOnly='Original nominal class/context and separately selected native code fields.',
            unresolved=['later complete constructor/class context initialization and opaque/alias/cache effects',
                'actual nominal MethodInfo/RGCTX and receiver callback','wire/list/parent/EOF'])),default=_json_set))
