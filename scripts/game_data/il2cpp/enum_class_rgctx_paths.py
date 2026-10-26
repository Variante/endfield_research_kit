"""Actual class RGCTX slot construction preserves nominal generic context.

The complete selected initializer family has independent instruction/control/
normal-frame checks. Its explicit positive-range/spare-arena prefix binds the
actual token search, static definition vector, zeroed output and count. Kind2
passes the registered actual type carrier plus unchanged incoming context to
type substitution, then its actual class resolver. Kind3 resolves the actual
static MethodSpec key, substitutes both instantiations with that same context,
and constructs/looks up the exact three-word key before the actual inflated
MethodInfo call. Distinct selected recursive-lock hit/miss paths are retained.
All selected slots join the same sixteen-byte definition/eight-byte output
counter suffix and original output return; native sizes are not wire widths.

The independently read ListFormatter and UnmanagedFormatter static contexts
bind each actual slot to reciprocal VAR0 ownership. The separate metadata
parameter fixup uses sixteen-byte GenericParameter records and the resolver's
ordinal WORD at twelve, never a type name/width alias. The native caller
supplies actual class image/token and generic-key context, then stores the
returned vector in that same class's RGCTX field.

Initialized parameter payloads/class image/token/context, the actual selected
token-search result, stable range/metadata/arena/cache state, disjoint zeroing/
allocation, bounded depth and normal helper effects remain conditions. The
source programs do not observe initialized live slots or admit a formatter
callback, concrete enum/list grammar, enclosing owner or physical EOF.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-class-rgctx-paths.v1'
LABEL='enumClassRgctxPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def caller_program(regions,entry):
    g=BytesPath(regions,entry);g.take('4c8b4360','4983c008','4c8d4d40','8b9318010000','488b0b')
    call=g.at;target=g.relative('e8');g.take('488983c0000000')
    return dict(selectedBytes=g.seen,entry=entry,actualInitializerCall=call,actualInitializer=target,
        arguments=dict(rcx='actual class.image +0',edx='actual class.token +280',r8='address of actual genericKey.class/method-inst +8',
            r9='address of current owned mutex local'),genericKeyClassOffset=96,returnedRgctxStoredAtSameClassOffset=192,
        unchangedInitializerOutputStored=True,wholeCallerReturnOrInputIdentityProved=False)


def prefix_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2410','4c894c2420','55','56','57','4154','4155','4156','4157',
        '4881ecc0000000','4d8be8','488bd9','488b4138','83784000');g.branch('0f84',False)
    g.take('33c0','4889442444','89542440','488b4138','448b4040','488b5048')
    compare=g.relative('488d05');g.take('4889442420','41b90c000000','488d4c2440');search=g.relative('e8')
    g.take('4885c0');g.branch('0f84',False)
    g.take('8b6808','48637004','48c1e604','488b4338','48037058','85ed');g.branch('0f84',False)
    g.take('4c63e5');arena=g.relative('4c8b35')
    g.take('4e8d3ce500000000','498b06','488b4808','488b7910','4c397f20');g.branch('0f83',True)
    g.take('488b4f10','498d140f','48895710','4c297f20','4e8d04e500000000','33d2');zero=g.relative('e8')
    g.take('4889842400010000','85ed');g.branch('0f8e',False)
    g.take('4c8bf8','4c8d7608','4c8be5','0f1f4000','0f1f840000000000')
    return dict(selectedBytes=g.seen,entry=entry,loopEntry=g.at,actualRangeComparator=compare,actualRangeSearch=search,
        imageModuleOffset=56,moduleRangeCountOffset=64,moduleRangeVectorOffset=72,moduleDefinitionVectorOffset=88,
        searchKeyTokenOffset=0,searchKeyZeroQwordOffset=4,rangeBytes=12,rangeStartOffset=4,rangeCountOffset=8,
        definitionBytes=16,definitionPayloadOffset=8,outputSlotBytes=8,actualArenaCell=arena,actualZeroHelper=zero,
        selectedRangeCountPositiveAndAtMostSignedMaxRequired=True,spareArenaBytesMustCoverCountTimesEight=True,
        actualZeroReturnsSameDestAndClearsDisjointOutputRequired=True,genericContextRegister='r13',
        definitionPayloadRegister='r14',remainingCountRegister='r12',outputSlotRegister='r15',
        originalOutputSavedAtRsp=256,wholeRangeSearchOrArenaSemanticsProved=False)


def _slot(regions,entry,*,kind):
    need('finite-literal-rgctx-kind',type(kind)is int and kind in(1,2,3))
    g=BytesPath(regions,entry);g.take('418b4ef8','83f903');g.branch('0f84',kind==3)
    if kind!=3:
        g.take('83e901');g.branch('0f84',kind==1)
        if kind==2:g.take('83e901');g.branch('0f84',True)
    return g


def _suffix(g):
    store=g.at;g.take('498907');suffix=g.at
    g.take('4983c610','4983c708','4983ec01');back=g.relative('0f85')
    g.take('488b842400010000');g.jump('eb',1)
    g.take('488b9c2408010000','4881c4c0000000','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(slotStore=store,suffix=suffix,loopEntry=back,definitionStride=16,outputStride=8,remainingStep=-1,
        selectedFinalSlotMustHaveRemainingOne=True,originalOutputReturnedUnchanged=True,entryRspRestored=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'])


def type_slot_program(regions,entry,*,kind):
    need('literal-type-or-class-slot',type(kind)is int and kind in(1,2));g=_slot(regions,entry,kind=kind)
    g.take('498b06','486308','83f9ff');g.branch('75',True,1)
    g.take('488bd1');registration=g.relative('488b05');g.take('488b4838','488b0cd1','41b001','498bd5')
    substitute=g.relative('e8');class_helper=None
    if kind==2:g.take('488bc8','b201');class_helper=g.relative('e8')
    g.jump('e9');suffix=_suffix(g);need('same-type-slot-counted-backedge',suffix['loopEntry']==entry)
    return dict(selectedBytes=g.seen,entry=entry,kind=kind,registrationCell=registration,typePointersOffset=56,
        typePointerStride=8,actualTypeSubstitution=substitute,actualClassHelper=class_helper,
        substitutionArguments=dict(rcx='unchanged registered type pointer selected by actual definition payload index',
            rdx='unchanged initializer generic context',r8b=1),definitionIndexMustNotBeMinusOne=True,
        actualResultStoredUnchanged=True,**suffix)


def method_slot_program(regions,entry,*,miss):
    need('literal-method-key-cache-selection',type(miss)is bool);g=_slot(regions,entry,kind=3)
    g.take('498b0e','8b09');spec=g.relative('e8');g.take('488bd8','41b001','498bd5','488b4808')
    substitute=g.relative('e8');g.take('488bf8','41b001','498bd5','488b4b10')
    need('same-class-and-method-instantiation-substitution',g.relative('e8')==substitute)
    g.take('488bf0');options=g.relative('48833d')+1;g.take('00');g.branch('75',False,1)
    g.take('488bcf');depth=g.relative('e8');limit=g.relative('8b15');g.take('3bc2');g.branch('7f',False,1)
    g.take('488bce');need('same-second-depth-helper',g.relative('e8')==depth)
    g.take('3bc2');g.branch('7e',True,1)
    g.take('488b2b','48896c2478','4889bc2480000000','4889b42488000000')
    mutex=g.relative('488d05');g.take('4889842498000000');thread=g.relative('ff15');g.take('488bd8')
    owner=g.relative('488b0d');g.take('483bc1');g.branch('74',True,1);recursion=g.relative('ff05')
    g.take('33c0','89442450','488d442478','4889442458','4c8d442450','488d9424a0000000');lookup=g.relative('e8')
    capacity=g.relative('488b05');g.take('48c1e004');slots=g.relative('480305')
    g.take('488b9c24a8000000','483bd8');g.branch('74',miss,1)
    allocation=None
    if miss:
        g.take('ba01000000','41b818000000');allocator=g.relative('488b0d');allocate=g.relative('e8')
        g.take('488bd8','488928','48897808','48897010','33ff','897c2430','4889442438',
            '4c8d442430','488d9424a0000000');insert=g.relative('e8');g.take('90')
        allocation=dict(contextCell=allocator,target=allocate,count=1,bytes=24,insertion=insert,
            fieldOffsets=[0,8,16],fieldValues=['unchanged actual original MethodSpec definition',
                'actual class-instantiation substitution result','actual method-instantiation substitution result'],
            disjointNonnullAllocationAndOrdinaryInsertionRequired=True)
        need('same-new-key-recursive-depth-reload',g.relative('8b05')==recursion)
        g.take('85c0');g.branch('7e',False,1);g.take('83f801');g.branch('75',True,1)
        g.take('ffc8');need('same-new-key-recursive-depth-release',g.relative('8905')==recursion)
    else:
        g.take('488b5b08');need('same-key-hit-recursive-depth-reload',g.relative('8b05')==recursion)
        g.take('85c0');g.branch('7e',False,1);g.take('83f801');g.branch('75',True,1)
        g.take('ffc8');need('same-key-hit-recursive-depth-release',g.relative('8905')==recursion);g.jump('eb',1)
    g.take('33d2','488bcb');inflate=g.relative('e8');suffix=_suffix(g)
    need('same-method-slot-counted-backedge',suffix['loopEntry']==entry)
    return dict(selectedBytes=g.seen,entry=entry,kind=3,missingKey=miss,actualMethodSpecResolver=spec,
        actualInstantiationSubstitution=substitute,optionsCell=options,optionsCellMustBeZero=True,
        actualDepthHelper=depth,depthLimitCell=limit,bothActualDepthResultsMustNotExceedSignedLimit=True,
        depthHelperMustPreserveEdxForSecondComparison=True,mutexAddress=mutex,currentThreadIatCell=thread,
        ownerCell=owner,recursiveDepthCell=recursion,recursiveOwnerPositiveDepthAndNoOverflowRequired=True,
        actualKeyLookup=lookup,capacityCell=capacity,slotsCell=slots,allocation=allocation,
        actualInflatedMethodInfo=inflate,inflateArguments=dict(rcx='actual selected or allocated three-word method key',edx=0),
        actualMethodInfoOutputStoredUnchanged=True,**suffix)


def parameter_fixup_program(regions,entry,*,null_index=False):
    need('literal-parameter-fixup-path',type(null_index)is bool)
    g=BytesPath(regions,entry);g.take('486311','4c8bc1','83faff');g.branch('75',not null_index,1)
    if null_index:g.take('48c70100000000','c3');return dict(selectedBytes=g.seen,nullIndex=True,storedZero=True,entryRspUnchanged=True)
    header=g.relative('488b05');g.take('48c1e204','48634868');loaded=g.relative('48030d');g.take('4803d1','498910','c3')
    return dict(selectedBytes=g.seen,nullIndex=False,headerCell=header,metadataBaseCell=loaded,sectionHeaderOffset=104,
        parameterRecordBytes=16,signedInputIndex=True,sameInputPayloadQwordOverwritten=True,entryRspUnchanged=True,
        fullUnwindExtentProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_instantiation_substitution_paths import derive as instantiation_source
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.enum_class_field_paths import unique
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.levelscript_two_routes_native import _window
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=instantiation_source(image,pins,**arguments)
    inflated=prior['proof']['typeSubstitutionSource']['proof']['inflatedMethodSource']
    constructor=owned(image,inflated['proof']['selectedEmptyLookup']['actualConstructor'])
    at=unique(constructor['regions'],bytes.fromhex('4c8b43604983c0084c8d4d408b9318010000488b0be8'))
    caller=caller_program(constructor['regions'],at);body=owned(image,caller['actualInitializer']);rows=[]
    for start,raw in body['regions']:rows+=checked_rows(decode(image.mapper,raw,start),raw,LABEL)
    rows.sort(key=lambda row:int(row['va'],16));graph,padding=complete_program(body['regions'],rows,body['pointer'])
    prefix=prefix_program(body['regions'],body['pointer']);loop=prefix['loopEntry']
    types=[type_slot_program(body['regions'],loop,kind=k)for k in(1,2)]
    methods=[method_slot_program(body['regions'],loop,miss=m)for m in(False,True)]
    type_entry=prior['proof']['typeSubstitutionSource']['proof']['selectedKindPrograms'][0]['entry']
    need('same-independently-proved-type-substitution',all(p['actualTypeSubstitution']==type_entry for p in types))
    need('same-independently-proved-instantiation-substitution',all(p['actualInstantiationSubstitution']==prior['proof']['selectedCount1Hit']['entry']for p in methods))
    key=inflated['proof']['encodedSource']['proof']['descriptorSource']['proof']['methodKeySource']
    spec=key['proof']['methodTableSeedSource']['proof']['keyResolverPrograms'][0]['selectedBytes'][0][0]
    need('same-actual-MethodSpec-and-inflated-resolvers',all(p['actualMethodSpecResolver']==spec
        and p['actualInflatedMethodInfo']==inflated['proof']['selectedEmptyLookup']['entry']for p in methods))
    independent=key['proof']['keyPrograms'][1]
    need('same-independent-method-key-cache-fields-and-helpers',all(methods[1][left]==independent[right]for left,right in(
        ('actualKeyLookup','lookupTarget'),('capacityCell','capacityCell'),('slotsCell','slotsCell'),
        ('mutexAddress','mutexAddress'),('ownerCell','ownerCell'),('recursiveDepthCell','depthCell'))))
    need('same-independent-method-key-insertion',methods[1]['allocation']['insertion']==independent['allocation']['insertionTarget'])
    normal=inflated['proof']['constructedClassSource']['proof']['managedArgumentSource']['proof']['nativeGenericKeySource']['proof']['receiverSource']['proof']['nameAndInternerSource']['proof']['internerSource']['proof']['placeholderTypeSource']['proof']['argumentKeySource']['proof']['normalizerSelection']
    fixup=normal['proof']['classFieldSource']['proof']['typeDataFixup'];fp=fixup['proof']['typeLoop']
    selectors=bytes.fromhex(fp['selectorHex']);need('actual-VAR-and-MVAR-select-parameter-fixup',selectors[18]==selectors[29]==1)
    alt=fp['alternateCallSelectedBytes'];g=BytesPath([(a,bytes.fromhex(v))for a,v in alt],alt[0][0]);parameter=g.relative('e8')
    observed=[(parameter,image.pe.bytes_at_va(parameter,64))];parameter_paths=[parameter_fixup_program(observed,parameter,null_index=z)for z in(False,True)]
    parameter_proof=parameter_paths[0];md=image.metadata
    need('same-metadata-generic-parameter-section',list(md.sections).index('genericParameters')==12
        and parameter_proof['sectionHeaderOffset']==8+12*8 and md.sections['genericParameters'].size%16==0)
    need('same-independent-loaded-metadata-cells',parameter_proof['headerCell']==fixup['proof']['fixup']['metadataHeaderCell']
        and parameter_proof['metadataBaseCell']==fixup['proof']['fixup']['metadataBaseCell'])
    symbols=ContextSymbols(image);ctx=NativeReferenceContext(image);contexts={}
    for name in('MemoryPack.Formatters.ListFormatter`1','MemoryPack.Formatters.UnmanagedFormatter`1'):
        td=ctx.index.types[name];context=symbols.context(td.index)
        list_formatter=name=='MemoryPack.Formatters.ListFormatter`1'
        expected=[2,3,3,3,2,3,3,3,2]if list_formatter else[3,2]
        need('exact-static-formatter-slot-kinds',context['count']==len(expected)
            and[e['kind']for e in context['entries']]==expected)
        names=[e['methodName']for e in context['entries']if e['kind']==3]
        need('exact-static-formatter-method-roles',names==(['.ctor','Clear','GetFormatter','Deserialize','Add','.ctor']if list_formatter else['.ctor']))
        variables=[]
        def check_atom(value):
            if isinstance(value,dict):
                if 'parameterOwner'in value:
                    owner=value['parameterOwner'];need('actual-static-VAR-reciprocal-formatter-owner',
                        bytes.fromhex(value['rawHex'])[10]==19 and owner.get('typeIndex')==td.index and owner['ordinal']==0)
                    need('same-native-resolver-ordinal-WORD-at12',int.from_bytes(bytes.fromhex(owner['parameterRawHex'])[12:14],'little')==0)
                    variables.append(dict(typePointerVa=value['typePointerVa'],parameterOwner=owner))
                for child in value.values():check_atom(child)
            elif isinstance(value,list):
                for child in value:check_atom(child)
        check_atom(context);need('actual-static-context-has-owned-VAR0',bool(variables))
        contexts[name]=dict(typeDefinition=td.index,context=context,ownedVar0Occurrences=variables)
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(instantiationSource=prior,actualCaller=caller,actualWindows=body['windows'],completeControl=graph,padding=padding,
            selectedPrefix=prefix,selectedTypeSlots=types,selectedMethodSlots=methods,staticFormatterContexts=contexts,
            parameterFixupPrograms=parameter_paths,parameterFixupWindow=_window(image,parameter,parameter_paths[0]['selectedBytes'][-1][0]+len(bytes.fromhex(parameter_paths[0]['selectedBytes'][-1][1])),
                'Exact selected frameless parameter-fixup program; no unwind extent claim')),
        actualClassRgctxSlotSourceTransfersProved=True,actualInitializedRgctxOrCallbackIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete current initializer partition/CFG/frame, caller class/context store, selected prefix/type/method slots and current reciprocal formatter contexts/parameter fixer.',
            conditional=__doc__,structuralOnly='Native runtime context construction.',
            unresolved=['actual initialized class/image/token/context and selected search/helper/cache effects',
                'nominal callback/provider binding','concrete enum/list/parent/EOF'])),default=_json_set))
