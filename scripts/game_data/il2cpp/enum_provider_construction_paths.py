"""Selected provider enum branch constructs a nominal reflected formatter.

The finite warm branch owns its actual input Type receiver, first-predicate
false and virtual IsEnum-slot true choices, source-selected open formatter
usage, count1 Type-array allocation/check/store, virtual MakeGenericType call,
actual constructed-Type argument to the instance factory and complete return.
Every method/helper/type identity is an independent composition obligation;
the byte program alone does not rename an open formatter or supply its ABI.

The enum fallback's DangerousUnmanagedFormatter request is distinct from an
ordinary UnmanagedFormatter constructor/Register<T> path. Exact nominal
constructor/Register MethodSpecs can exist without corresponding exact closed
native generic-method-table registrations. Their actual usage/caller, code
selection and callback must be joined; neither absence of a table row nor a
different formatter's placeholder program decides the nominal wire grammar.

Warm usage/classes, actual predicates and helper returns, disjoint correctly
typed allocation and array effects, actual virtual MethodInfo/receiver slots,
reflection construction and instance-factory effects remain conditions. No
nominal-to-placeholder callback, enum width/list grammar or owner admission
follows from a Type name or matching native pointer.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='enumProviderConstructionPaths'
SCHEMA='endfield.enum-provider-construction-paths.v1'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def enum_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','48896c2410','4889742418','57','4883ec20')
    warm=g.relative('803d')+1;g.take('00','8ada','488bf9','bd01000000');g.branch('75',True,1)
    g.take('4885ff');g.branch('0f84',False)
    g.take('33d2','488bcf');first=g.relative('e8');g.take('488bd7','84c0');g.branch('0f85',False)
    g.take('b95d000000');is_enum=g.relative('e8');g.take('84c0');g.branch('0f85',True)
    type_class_site=g.at;type_class=g.relative('488b0d');open_site=g.at;open_cell=g.relative('488b1d');ready=g.relative('e8')
    g.take('33d2','488bcb');handle=g.relative('e8')
    array_site=g.at;array_cell=g.relative('488b0d');g.take('488bd5','488bf0');allocate=g.relative('e8')
    g.take('488bd8','4885c0');g.jump('e9');g.branch('74',False,1)
    g.take('488bd7','488bcb');array_check=g.relative('e8')
    g.take('4c8bc7','33d2','488bcb');array_store=g.relative('e8')
    g.take('4885f6');g.branch('74',False,1)
    g.take('4c8bc3','488bd6','b9a8000000');make=g.relative('e8');g.take('488bd8')
    g.take('33d2','488bcb');instance=g.relative('e8');g.jump('e9')
    g.take('488b5c2430','488b6c2438','488b742440','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,warmUsageFlagCell=warm,warmUsageFlagMustBeNonzero=True,
        requestedType='unchanged incoming RCX saved in RDI',actualFirstPredicate=first,firstPredicateMustReturnZero=True,
        actualIsEnumVirtual=is_enum,isEnumVirtualSlot=93,isEnumMustReturnNonzero=True,
        actualTypeClassUsageInstruction=type_class_site,actualTypeClassCell=type_class,
        actualOpenFormatterUsageInstruction=open_site,actualOpenFormatterCell=open_cell,actualReadyHelper=ready,
        actualTypeFromHandle=handle,openTypeHandleMethodInfoIsNull=True,
        actualTypeArrayUsageInstruction=array_site,actualTypeArrayClassCell=array_cell,actualArrayAllocator=allocate,
        arrayCount=1,arrayCountArgumentRegister='rdx',actualArrayTypeCheck=array_check,actualArrayStore=array_store,
        arrayStoreArguments=dict(rcx='same nonnull fresh array',rdx=0,r8='unchanged original requested Type'),
        actualMakeGenericTypeVirtual=make,makeGenericTypeSlot=168,
        makeArguments=dict(rcx=168,rdx='actual open formatter Type returned by actual TypeFromHandle',r8='same count1 array'),
        actualInstanceFactory=instance,instanceFactoryArguments=dict(rcx='unchanged actual constructed Type',rdx=0),
        instanceFactoryResultReturnedUnchanged=True,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbx','rbp','rsi','rdi'],actualOpenTypeReceiverAndCallbackIdentityProved=False)
