"""Generic provider's lazy method context uses its original method key.

The exact registered placeholder GetFormatter<T> body is independently owned;
its complete source/CFG/frame and cold successful path are checked without
equating that registration to a concrete enum. Its unchanged MethodInfo is
passed to the actual lazy initializer when context+56 remains null. Under the
explicit same-thread recursive lock, the initializer reads MethodInfo.key+64,
uses that key's original definition class image/token and address of its actual
class/method-instantiation pair, calls the separately proved RGCTX initializer,
and stores its unchanged output in that same MethodInfo+56. Warm and cold
initializer paths release one recursion level and return the same MethodInfo.

The provider's two static method slots are independently exact reciprocal MVAR0
and MemoryPackFormatter<MVAR0>, with the actual method token's sorted-module
search replayed. Source MVAR substitution indexes the actual method-inst vector;
it is distinct from the class-generic ListFormatter/Deserialize context.
The provider passes context slot0's carrier through TypeFromHandle/backend and
checks the returned object against context slot1's actual class before returning
it unchanged. Actual backend/reflection/cache effects remain separate.

Coherent initialized original key/definition/context/class/module, bounded
method-instantiation, successful normal helpers/cast, stable disjoint storage
and recursive lock state are conditions. No live nominal callback or concrete
enum/list/parent grammar follows from placeholder code or these source transfers.
"""
import json

from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

SCHEMA='endfield.enum-method-rgctx-paths.v1'
LABEL='enumMethodRgctxPaths'


def need(check,condition):
    if not condition:raise ValueError(LABEL+'.'+check)


def provider_program(regions,entry):
    g=BytesPath(regions,entry);g.take('48895c2408','4889742410','57','4883ec20','4883793800','488bf9')
    g.branch('75',False,1);provider_usage=g.relative('488d0d');metadata=g.relative('e8')
    type_usage=g.relative('488d0d');need('same-two-metadata-initializers',g.relative('e8')==metadata)
    g.take('48837f3800');g.branch('75',False,1)
    g.take('488bcf');initialize=g.relative('e8');g.take('488b5f38')
    type_class=g.relative('488b0d');g.take('488b1b');ready=g.relative('e8')
    g.take('33d2','488bcb');handle=g.relative('e8')
    provider_class=g.relative('488b0d');g.take('488bd8');need('same-provider-ready-helper',g.relative('e8')==ready)
    g.take('488bcb');backend=g.relative('e8');g.take('488b4f38','488bd8','488b4908');expected=g.relative('e8')
    g.take('488bd0','488bcb');cast=g.relative('e8');g.take('4885c0');g.branch('0f85',True)
    g.take('488b5c2430','488b742438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,providerTypeUsageCell=provider_usage,typeTypeUsageCell=type_usage,
        actualMetadataInitializer=metadata,actualMethodContextInitializer=initialize,methodInfoContextOffset=56,
        actualTypeClassCell=type_class,actualProviderClassCell=provider_class,actualReadyHelper=ready,
        actualTypeFromHandle=handle,actualBackend=backend,actualExpectedClassResolver=expected,actualCast=cast,
        sameOriginalMethodInfoPreserved=True,requestedTypeCarrierContextSlot=0,expectedFormatterClassContextSlot=1,
        backendTypeArgument='actual TypeFromHandle result for unchanged own context slot0 carrier',
        expectedClassArgument='unchanged own context slot1',successfulNonnullCastRequired=True,
        actualCompatibleBackendResultReturnedUnchanged=True,entryRspRestored=True,normalReturn=True,
        nonvolatilesRestored=['rbx','rsi','rdi'],actualBackendReceiverOrCallbackProved=False)


def initializer_program(regions,entry,*,cold):
    need('literal-initializer-context-path',type(cold)is bool)
    g=BytesPath(regions,entry);g.take('48895c2410','57','4883ec20','488bd9')
    mutex=g.relative('488d05');g.take('4889442430');thread=g.relative('ff15');g.take('488bf8')
    owner=g.relative('488b15');g.take('483bc2');g.branch('74',True,1);depth=g.relative('ff05')
    g.take('48837b3800');g.branch('74',cold,1)
    context=None
    if cold:
        g.take('488b4340','4c8d4008','488b10','488b4a20','4c8d4c2430','8b5248','488b09')
        context=g.relative('e8');g.take('48894338')
    else:g.jump('eb',1)
    g.take('488b4c2430','83795000');g.branch('7e',False,1)
    g.take('83795001');g.branch('75',True,1);g.take('ff4950')
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,entry=entry,cold=cold,mutexAddress=mutex,currentThreadIatCell=thread,
        ownerCell=owner,recursiveDepthCell=depth,currentThreadAlreadyOwnsMutexRequired=True,
        positiveBoundedRecursiveDepthRequired=True,methodInfoKeyOffset=64,methodInfoContextOffset=56,
        keyOriginalDefinitionOffset=0,keyContextPairOffset=8,definitionClassOffset=32,definitionTokenOffset=72,
        classImageOffset=0,actualRgctxInitializer=context,
        arguments=dict(rcx='actual original definition.class.image',edx='actual original definition token',
            r8='address of actual original key.class/method-inst pair',r9='address of same current owned mutex local')if cold else None,
        returnedContextStoredUnchangedInSameMethodInfo=cold,returnsSameIncomingMethodInfo=True,
        oneRecursiveLevelReleased=True,entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'])


def derive(image,pins,**arguments):
    from scripts.game_data.il2cpp.enum_source_variants import select
    variant=select(arguments.get("enum_variant"))
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.enum_rgctx_helper_paths import derive as helper_source,search_program
    from scripts.game_data.il2cpp.enum_constructed_class_paths import _json_set
    from scripts.game_data.il2cpp.enum_reflection_dispatch_paths import decode
    from scripts.game_data.il2cpp.enum_instantiation_seed_paths import complete_program
    from scripts.game_data.il2cpp.owned_partition import checked_rows
    from scripts.game_data.il2cpp.rgctx_symbols import ContextSymbols
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack.pointer_param import owned
    _publication_gate(image,pins);prior=helper_source(image,pins,**arguments);ctx=NativeReferenceContext(image);md=image.metadata
    owner=ctx.index.types['MemoryPack.MemoryPackFormatterProvider']
    methods=[m for m in md.methods_for(owner)if md.string(m.name_index)=='GetFormatter'and m.generic_container_index>=0
        and m.flags&16 and not md.parameters_for(m)]
    need('one-exact-static-generic-provider-definition',len(methods)==1);method,=methods
    entry=GenericEntries(image).resolve(method.index,[],[variant['placeholderType']]);body=owned(image,entry['pointer'])
    provider=provider_program(body['regions'],body['pointer']);initializer=owned(image,provider['actualMethodContextInitializer'])
    programs=[initializer_program(initializer['regions'],initializer['pointer'],cold=c)for c in(False,True)];graphs={}
    for role,source in(('provider',body),('initializer',initializer)):
        rows=[]
        for at,raw in source['regions']:rows+=checked_rows(decode(image.mapper,raw,at),raw,LABEL)
        rows.sort(key=lambda row:int(row['va'],16));graph,padding=complete_program(source['regions'],rows,source['pointer'])
        graphs[role]=dict(windows=source['windows'],control=graph,padding=padding)
    class_context=prior['proof']['classContextSource'];actual=class_context['proof']['selectedPrefix']['entry']
    need('same-independent-actual-rgctx-initializer',programs[1]['actualRgctxInitializer']==actual)
    need('same-metadata-type-and-provider-usage-cells',provider['typeTypeUsageCell']==provider['actualTypeClassCell']
        and provider['providerTypeUsageCell']==provider['actualProviderClassCell'])
    context=ContextSymbols(image).context(method.index,is_method=True)
    need('exact-own-provider-method-context-two-slots',context['count']==2 and[e['kind']for e in context['entries']]==[1,2])
    first,second=context['entries'];variable=first['type'];parameter=variable.get('parameterOwner',{})
    need('actual-own-reciprocal-MVAR0',bytes.fromhex(variable['rawHex'])[10:12]==bytes.fromhex('1e00')
        and parameter.get('methodIndex')==method.index and parameter['ordinal']==0
        and int.from_bytes(bytes.fromhex(parameter['parameterRawHex'])[12:14],'little')==0)
    need('second-slot-is-own-formatter-of-same-MVAR',second['type']['definition']['name']=='MemoryPack.MemoryPackFormatter`1'
        and second['type']['classArguments']==[variable]and ctx.type_name(method.return_type)==second['typeName'])
    source=owned(image,class_context['proof']['selectedPrefix']['actualRangeSearch']);module=image.modules[context['image']]
    count=image.pe.u32_at_va(module+64);need('bounded-actual-method-range-directory',0<count<=1_000_000)
    table=image.pe.u64_at_va(module+72);raw=image.pe.bytes_at_va(table,count*12)
    tokens=[int.from_bytes(raw[i:i+4],'little')for i in range(0,len(raw),12)]
    search=search_program(source['regions'],source['pointer'],tokens=tokens,token=context['token']);at=search['selectedRangeIndex']*12
    need('same-native-method-context-search-and-static-range',
        (int.from_bytes(raw[at+4:at+8],'little',signed=True),int.from_bytes(raw[at+8:at+12],'little',signed=True))==(context['start'],context['count']))
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema=SCHEMA,status='proved-current-source-only',nativeInputs=pins,
        proof=dict(rgctxHelperSource=prior,providerMethod=[method.index,'MemoryPack.MemoryPackFormatterProvider','GetFormatter'],
            placeholderProviderRegistration=entry,completeFamilies=graphs,selectedColdProvider=provider,
            selectedInitializerPrograms=programs,staticMethodContext=context,actualMethodTokenSearch=search),
        originalMethodKeyToActualLazyContextTransfersProved=True,actualNominalProviderReceiverOrCallbackIdentityProved=False,
        concreteEnumCallbackSelected=False,wireGrammarAdmitted=False,wholeOwnerAdmitted=False,
        evidenceBoundary=dict(exact='Own generic provider registration/complete body, complete actual lazy initializer, selected recursive warm/cold source paths and exact MVAR method context/token search.',
            conditional=__doc__,structuralOnly='Generic method context transport distinct from class RGCTX.',
            unresolved=['actual initialized original MethodInfo key/context and opaque helper/cache effects',
                'provider/reflection constructed receiver and slot5 binding','concrete enum/list/parent/EOF'])),default=_json_set))
