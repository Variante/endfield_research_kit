"""Actual optimized Byte-key provider clone; no nominal callback selection."""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='enumByteProviderPrograms'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def program(regions,entry,*,cold_context=False,cold_type=False,cold_provider=False):
    need('literal-selected-paths',all(type(x)is bool for x in(cold_context,cold_type,cold_provider)))
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',cold_context,1)
    provider_usage=type_usage=metadata=initialize=None
    if cold_context:
        provider_usage=g.relative('488d0d');metadata=g.relative('e8')
        type_usage=g.relative('488d0d');need('same-metadata-helper',g.relative('e8')==metadata)
        g.take('48837f3800');g.branch('0f85',False)
        g.take('488bcf');initialize=g.relative('e8');g.jump('e9')
    type_class=g.relative('488b0d');g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',cold_type)
    type_ready=None
    if cold_type:type_ready=g.relative('e8');g.jump('e9')
    g.take('33d2','488bcb');handle=g.relative('e8')
    provider_class=g.relative('488b0d');g.take('488bd8','83b9e000000000');g.branch('74',cold_provider,1)
    provider_ready=None
    if cold_provider:provider_ready=g.relative('e8');g.jump('eb',1)
    g.take('488bcb');backend=g.relative('e8')
    g.take('488b4f38','ba01000000','488bd8');expected=g.relative('e8')
    g.take('488bd0','488bcb');cast=g.relative('e8');g.take('4885c0');g.branch('0f84',False)
    g.take('488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,coldContext=cold_context,coldType=cold_type,coldProvider=cold_provider,
        providerTypeUsageCell=provider_usage,typeTypeUsageCell=type_usage,actualMetadataInitializer=metadata,
        actualMethodContextInitializer=initialize,actualTypeClassCell=type_class,actualProviderClassCell=provider_class,
        actualTypeReadyHelper=type_ready,actualProviderReadyHelper=provider_ready,
        actualTypeFromHandle=handle,actualBackend=backend,actualExpectedClassResolver=expected,actualCast=cast,
        methodInfoContextOffset=56,requestedTypeCarrierContextSlot=0,expectedFormatterClassContextSlot=1,
        expectedClassResolverSlotArgument=1,sameOriginalMethodInfoPreserved=True,
        backendTypeArgument='actual TypeFromHandle result for unchanged own context slot0',
        successfulNonnullCastRequired=True,actualCompatibleBackendResultReturnedUnchanged=True,
        entryRspRestored=True,normalReturn=True,nonvolatilesRestored=['rbx','rdi'],
        actualNominalCallbackOrMethodInfoSelectionProved=False)


def register_program(regions,entry,*,cold_context=False,cold_type=False,cold_provider=False):
    """Byte formatter Register source passes original Type/ref to owned setter."""
    need('literal-register-paths',all(type(x)is bool for x in(cold_context,cold_type,cold_provider)))
    g=BytesPath(regions,entry)
    g.take('48895c2408','4889742410','57','4883ec20','48837a3800','488bda','488bf1');g.branch('74',cold_context,1)
    usages=[];metadata=initialize=None
    if cold_context:
        for _ in range(3):
            usages.append(g.relative('488d0d'));target=g.relative('e8')
            need('same-register-metadata-helper',metadata in(None,target));metadata=target
        g.take('48837b3800');g.branch('0f85',False)
        g.take('488bcb');initialize=g.relative('e8');g.jump('e9')
    provider=g.relative('488b05');g.take('83b8e000000000');g.branch('0f84',cold_provider)
    provider_ready=None
    if cold_provider:
        g.take('488bc8');provider_ready=g.relative('e8')
        need('same-provider-cell-after-ready',g.relative('488b05')==provider);g.jump('e9')
    system_type=g.relative('488b0d');g.take('488b80b8000000','488b5b38','83b9e000000000','488b7818','488b1b')
    g.branch('0f84',cold_type);type_ready=None
    if cold_type:type_ready=g.relative('e8');g.jump('e9')
    g.take('33d2','488bcb');handle=g.relative('e8')
    g.take('4885ff');g.branch('74',False,1)
    method_site=g.at;method_cell=g.relative('4c8b0d')
    g.take('4c8bc6','488bd0','488bcf','488b5c2430','488b742438','4883c420','5f')
    tail=g.at;setter=g.relative('e9')
    return dict(selectedBytes=g.seen,entry=entry,coldContext=cold_context,coldType=cold_type,coldProvider=cold_provider,
        metadataUsageCells=usages,actualMetadataInitializer=metadata,actualMethodContextInitializer=initialize,
        providerClassCell=provider,systemTypeClassCell=system_type,actualProviderReadyHelper=provider_ready,
        actualTypeReadyHelper=type_ready,actualTypeFromHandle=handle,
        dictionaryMethodUsageInstruction=method_site,dictionaryMethodInfoCell=method_cell,actualDictionarySetter=setter,
        dictionarySetterTailInstruction=tail,methodInfoContextOffset=56,nominalCarrierMethodContextSlot=0,
        registryStaticFieldsOffset=184,registryDictionaryFieldOffset=24,
        setterArguments=dict(rcx='actual provider staticFields.registry dictionary',
            rdx='System.Type converted from unchanged Register MethodInfo context slot0',
            r8='unchanged incoming formatter reference',r9='actual closed registry setter MethodInfo'),
        entryRspRestoredBeforeTail=True,nonvolatilesRestoredBeforeTail=['rbx','rsi','rdi'],
        sameIncomingFormatterReferencePassedUnchanged=True,actualDictionarySetterSourceRequired=True,
        registryPublicationOrCallbackSelectionProved=False)
