"""Exact count1 managed reflection argument-copy and native-call path.

The selected RuntimeType.MakeGenericType(Type[]) override has its complete
owned instruction partition, control flow and normal frames checked. On the
explicit warm, successful count1 path it allocates the named RuntimeType[],
checks the actual supplied argument, writes that unchanged object into the
new array and forwards that same array with the unchanged open Type receiver
to the named static MakeGenericType entry. That entry's independently owned
native count1 source forwards each actual Type payload to the argument
interner without primitive normalization. The returned Type is returned
unchanged after the actual ready-class and nonnull checks.

Compatible coherent Type objects, count1 input/generic-parameter arrays,
nonnull disjoint correctly typed allocation, successful actual class/type
predicates, warm classes and normally returning validation/barrier helpers
with stable disjoint data are conditions. The virtual receiver's live slot,
actual Type payload identity, allocation/validation opaque effects, generic
class/cache/MethodInfo/RGCTX identity and formatter callback remain unproved.
Other paths are fully partitioned, not admitted by this finite path. No enum
wire width, list, parent or whole owner is admitted.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-managed-generic-arguments.v1'
LABEL='enumManagedGenericArguments'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry):
    g=BytesPath(regions,entry)
    g.take('48895c2408','55','56','57','4154','4155','4156','4157','4883ec20',
        '488bda','488be9','4885d2');g.branch('0f84',False)
    g.take('8b5218');array_site=g.at;array_cell=g.relative('488b0d');allocate=g.relative('e8')
    g.take('b935000000','488bd5','488bf0');is_definition=g.relative('e8')
    g.take('84c0');g.branch('0f84',False)
    g.take('b93f000000','488bd5');parameters=g.relative('e8')
    g.take('4885c0');g.branch('0f84',False)
    g.take('8b4b18','394818');g.branch('0f85',False)
    g.take('4533ed','4c8d7620','488bc3','418bfd','482bc6','4889442478');loop=g.at
    g.take('3b7b18');g.branch('0f8d',False);g.branch('0f83',False)
    type_site=g.at;type_cell=g.relative('488b0d')
    g.take('4d8b3c06','4439a9e0000000');g.branch('0f84',False)
    g.take('4d85ff');g.branch('0f84',False)
    runtime_site=g.at;runtime_cell=g.relative('488b15');g.take('498b0f');is_runtime=g.relative('e8')
    g.take('84c0');g.branch('0f84',False)
    g.take('4d8be7');same_runtime_site=g.at;need('same-actual-runtime-class',g.relative('488b0d')==runtime_cell)
    g.take('4439a9e0000000');g.branch('0f84',False)
    g.take('4d85e4');g.branch('0f84',False)
    g.take('4885f6');g.branch('0f84',False)
    g.take('488b06','4d8b3c24','498bd7','488b4040','488bc8','4889442468');assignable=g.relative('e8')
    g.take('84c0');g.branch('0f84',False)
    g.take('3b7e18');g.branch('0f83',False)
    g.take('4863c7','4883c004','4d8926','488d0cc6');barrier=g.relative('e8')
    g.take('488b442478','ffc7','4983c608')
    need('same-selected-count1-copy-backedge',g.relative('e9')==loop);g.at=loop
    g.take('3b7b18');g.branch('0f8d',True)
    g.take('b201','488bcd');open_class=g.relative('e8')
    same_array_site=g.at;need('same-actual-RuntimeType-array-class',g.relative('488b3d')==array_cell)
    g.take('488bd8','4885c0');g.branch('74',False,1)
    g.take('4c8b30','488bcf','498bd6');same_assignable=g.relative('e8')
    need('same-actual-array-assignability-predicate',same_assignable==assignable)
    g.take('84c0');g.branch('74',False,1)
    g.take('4c8beb');third_runtime_site=g.at;need('same-actual-runtime-validation-class',g.relative('488b0d')==runtime_cell)
    g.take('83b9e000000000');g.branch('0f84',False)
    g.take('4533c0','498bd5','488bce');validate=g.relative('e8')
    g.take('488bd6','488bcd');call=g.at;native=g.relative('e8')
    same_type_site=g.at;need('same-actual-result-Type-class',g.relative('488b0d')==type_cell)
    g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('4885db');g.branch('0f84',False)
    g.take('488bc3','488b5c2460','4883c420','415f','415e','415d','415c','5f','5e','5d','c3')
    return dict(selectedBytes=g.seen,entry=entry,inputArgumentCount=1,arrayCountOffset=24,arrayElementsOffset=32,
        typeClassUsageInstruction=type_site,runtimeTypeUsageInstruction=runtime_site,
        repeatedRuntimeTypeUsageInstructions=[same_runtime_site,third_runtime_site],resultTypeUsageInstruction=same_type_site,
        runtimeTypeArrayUsageInstruction=array_site,repeatedRuntimeTypeArrayUsageInstruction=same_array_site,
        runtimeTypeArrayClassCell=array_cell,typeClassCell=type_cell,runtimeTypeClassCell=runtime_cell,
        allocationTarget=allocate,allocationEdx='unchanged incoming Type[] count1',
        genericDefinitionPredicate=dict(target=is_definition,slot=53,receiver='unchanged incoming Type receiver'),
        genericParametersRequest=dict(target=parameters,slot=63,receiver='unchanged incoming Type receiver'),
        actualRuntimeTypePredicate=is_runtime,actualAssignablePredicate=assignable,actualReferenceBarrier=barrier,
        copiedArrayElement='unchanged actual incoming Type[] element0',freshArrayElementStoreOffset=32,
        actualOpenClassRequest=open_class,actualValidationTarget=validate,
        validationArguments=dict(rcx='same fresh RuntimeType[]',rdx='actual successful open-class array result',r8=0),
        actualNativeCall=call,actualNativeTarget=native,
        nativeArguments=dict(rcx='unchanged incoming open Type receiver',rdx='same fresh count1 RuntimeType[]'),
        actualNativeResultReturnedUnchanged=True,entryRspAfterPrologue=-88,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rbp','rsi','rdi','r12','r13','r14','r15'],
        normalReturn=True,count1ArrayAndGenericParameterCountRequired=True,
        freshDisjointRuntimeTypeArrayAllocationRequired=True,selectedTypeAndAssignablePredicatesMustSucceed=True,
        classesInitializedRequired=True,normalDisjointValidationAndBarrierHelpersRequired=True,
        opaqueHelperAndActualTypePayloadIdentityProved=False)


def derive(image,pins,**arguments):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_reflection_generic_key_paths import derive as key_source
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import derive as dispatch_source,decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=key_source(image,pins,**arguments);dispatch=dispatch_source(image,pins,**arguments)
    selected,=[r for r in dispatch['proof']['selectedSlotMethods']if r['method'][1]=='System.RuntimeType']
    method=image.metadata.methods[selected['method'][0]];body=owned(image,image.method_pointer_va(method));rows=[]
    for at,data in body['regions']:rows+=checked_rows(decode(image.mapper,data,at),data,LABEL)
    rows.sort(key=lambda r:int(r['va'],16));graph,padding=complete_program(body['regions'],rows,body['pointer'])
    path=program(body['regions'],body['pointer']);provider=dispatch['proof']['selectedProviderPath']['actualCalls']
    need('same-independent-generic-predicates-and-argument-request',path['genericDefinitionPredicate']['target']==provider['isGenericType']
        and path['genericParametersRequest']['target']==provider['genericArguments'])
    actual=image.metadata.methods[prior['proof']['namedStaticMethod'][0]]
    static_entry=image.method_pointer_va(actual);static_body=prior['proof']['count1Programs'][0]['entry']
    need('same-independent-named-static-native-body',path['actualNativeTarget']==static_body
        and static_entry==image.pe.image_base+prior['proof']['namedEntryWindow']['startRva'])
    ctx=NativeReferenceContext(image);md=image.metadata;base=image.pe.image_base;usages={}
    for key,name in(('typeClassUsageInstruction','System.Type'),('resultTypeUsageInstruction','System.Type'),
            ('runtimeTypeUsageInstruction','System.RuntimeType'),('runtimeTypeArrayUsageInstruction','System.RuntimeType[]'),
            ('repeatedRuntimeTypeArrayUsageInstruction','System.RuntimeType[]')):
        usage=derive_typed_usage_context(image,path[key]-base,label=LABEL)
        need('actual-selected-nominal-usage:'+key,usage.get('tag')==1 and usage.get('typeName')==name)
        usages[key]=usage
    validations=[m for m in md.methods_for(ctx.index.types['System.RuntimeType'])if md.string(m.name_index)=='SanityCheckGenericArguments'
        and[ctx.type_name(p.type_index)for p in md.parameters_for(m)]==['System.RuntimeType[]','System.RuntimeType[]']]
    need('one-exact-named-generic-validation',len(validations)==1);validation,=validations
    validation_abi=dict(static=bool(validation.flags&0x10),result=ctx.type_name(validation.return_type),
        metadataEntry=image.method_pointer_va(validation),actualCallTarget=path['actualValidationTarget'])
    need('same-actual-generic-validation-entry:'+str(validation_abi),validation_abi['static']
        and validation_abi['result']=='void'and validation_abi['metadataEntry']==validation_abi['actualCallTarget'])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(nativeGenericKeySource=prior,virtualDispatchSource=dispatch,managedMethod=selected['method'],
            managedWindows=body['windows'],managedCfg=graph,managedPadding=padding,count1Program=path,typedUsages=usages,
            validationMethod=[validation.index,'System.RuntimeType','SanityCheckGenericArguments'],
            staticCallBinding=dict(actualDirectCallTarget=path['actualNativeTarget'],namedStaticEntry=static_entry,
                independentlyOwnedNativeBody=static_body,actualCallEntersOwnedBodyDirectly=True,
                namedEntryHasIndependentlyProvedE9ToSameBody=True,
                namedEntryPointerEqualsActualCallTarget=static_entry==path['actualNativeTarget'])),
        exactManagedCount1NominalArgumentTransferProved=True,actualClosedTypeAndMethodInfoIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Complete selected managed override source partition/CFG/frames, exact count1 copy/typed usages and named static native call.',
            conditional=__doc__,structuralOnly='Actual count1 Type-object array and payload transport.',
            unresolved=['actual receiver slot and Type payload identity','allocator/validation/barrier and cache effects',
                'generic-class/MethodInfo/RGCTX identity and concrete enum callback','wire/parent/EOF']))))
