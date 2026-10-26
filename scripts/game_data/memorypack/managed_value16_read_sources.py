"""Typed managed16 Reader/provider transfer under an exact canonical callback.

The actual Reader and provider entries are proved independently; neither is
equated to a registered body. The fixed-slot dispatcher must compare the fresh
canonical adapter pointer and execute its complete matched path. Backend
selection, its successful compatible-class predicate and coherent closed
MethodInfos are explicit conditions, never observations of a runtime provider.
This component proves no byte grammar from the managed output size.
"""
from scripts.game_data.il2cpp.formatter_value_paths import BytesPath

LABEL='managedValue16Read'

def need(key,condition,detail=None):
    if not condition:raise ValueError(LABEL+'.'+key+':'+str(detail)[:700])

def provider_program(regions,entry,s):
    """Complete initialized compatible-backend success path with inline cast."""
    g=BytesPath(regions,entry)
    g.take('48895c2410','57','4883ec20','4883793800','488bf9');g.branch('74',False,1)
    type_site=g.at;type_cell=g.relative('488b0d')
    g.take('488b5f38','83b9e000000000','488b1b');g.branch('0f84',False)
    g.take('33d2','488bcb');g.call(s['typeHandle'])
    provider_site=g.at;provider_cell=g.relative('488b0d')
    g.take('488bd8','83b9e000000000');g.branch('74',False,1)
    g.take('488bcb');g.call(s['backend'])
    g.take('488b4f38','ba01000000','488bd8');g.call(s['indexed'])
    g.take('4885db');g.branch('0f84',False)
    g.take('488b0b','488bd0');g.call(s['assignable'])
    g.take('84c0');g.branch('0f84',False)
    g.take('488bc3','488b5c2438','4883c420','5f','c3')
    return dict(selectedBytes=g.seen,typeClassUsageSite=type_site,typeClassCell=type_cell,
        providerClassUsageSite=provider_site,providerClassCell=provider_cell,
        requestedTypeContextSlot=0,resultFormatterTypeContextSlot=1,
        sameRequestedTypePassedToBackend=True,sameNonNullBackendReferenceReturned=True,
        resultClassPredicatePassed=True,predicateOutcomeObserved=False,
        entryRspRestored=True,nonvolatilesRestored=['rbx','rdi'],normalReturn=True)

def derive(image,pins,*,typed_request,source_target,reference_lane,wrapper_name=None):
    """Re-derive the nominal adapter and bind the actual typed Reader source."""
    import json
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.formatter_composition import derive_typed_usage_context
    from scripts.game_data.il2cpp.generic_entries import GenericEntries
    from scripts.game_data.memorypack import pointer_param as pointer,buff_ptr_sources
    from scripts.game_data.memorypack.managed_value16_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_tag_query_transfer import adapter16_program
    _publication_gate(image,pins);base=image.pe.image_base
    need('one-exact-request-type',typed_request.get('methodArguments')and len(typed_request['methodArguments'])==1)
    adapter=derive_adapter(image,pins,type_name=typed_request['methodArguments'][0],wrapper_name=wrapper_name,reference_lane=reference_lane)
    need('same-current-adapter-inputs',adapter['nativeInputs']==pins)
    need('exact-canonical-adapter-kind',adapter['schema']=='endfield.managed-value16-adapter-source.v1'and
        adapter['status']=='proved-conditional-managed16-adapter'and adapter['managedBytes']==16 and
        adapter['canonicalCallbackAdmitted']is True and adapter['providerSelectionObserved']is False)
    for windows in adapter['proof']['sourceWindows'].values():image.check_windows(windows,label=LABEL+'.canonical')
    value=adapter['typeName'];typed=buff_ptr_sources._typed_context(image,typed_request,value,GenericEntries(image))
    sources={};s={k:base+v for k,v in adapter['proof']['symbolRvas'].items()}
    def own(role,target):sources[role]=pointer.owned(image,target);s[role]=target;return sources[role]
    read=own('read',source_target)
    own('provider',buff_ptr_sources._call(read,60));dispatch=own('dispatch',buff_ptr_sources._call(read,79))
    for offset,name in((52,'typeHandle'),(79,'backend'),(96,'indexed'),(116,'assignable')):
        actual=buff_ptr_sources._call(sources['provider'],offset)
        if name in s:need('same-canonical-helper.'+name,s[name]==actual)
        s[name]=actual
    actual_read=buff_ptr_sources.read16_program(read['regions'],source_target,s)
    actual_provider=provider_program(sources['provider']['regions'],s['provider'],s)
    need('same-actual-prepare',buff_ptr_sources._call(dispatch,37)==s['prepare'])
    dispatch_paths=[adapter16_program(dispatch['regions'],s['dispatch'],s,dispatch=True,**p)
        for p in({},{'create':False},{'null':True})]
    read_class=derive_typed_usage_context(image,source_target-base+37,label=LABEL+'.readerProviderClass')
    need('actual-reader-provider-class',(read_class['tag'],read_class['typeName'])==(1,'MemoryPack.MemoryPackFormatterProvider'))
    provider_classes=[]
    for key in('typeClassUsageSite','providerClassUsageSite'):
        provider_classes.append(derive_typed_usage_context(image,actual_provider[key]-base,label=LABEL+'.'+key))
    need('actual-provider-classes',[(u['tag'],u['typeName'])for u in provider_classes]==
        [(1,'System.Type'),(1,'MemoryPack.MemoryPackFormatterProvider')])
    _publication_gate(image,pins)
    return json.loads(json.dumps(dict(schema='endfield.managed-value16-read-source.v1',status='proved-conditional-typed-managed16-read',
        nativeInputs=pins,typeName=value,wrapperName=adapter['wrapperName'],managedBytes=16,
        readMethod='ReadValue',readerMethodDefinition=typed_request['methodSpec'][0],sourceTargetRva=source_target-base,
        actualSourceProved=True,resultAbi='hidden-local',providerSelectionObserved=False,wireGrammarAdmitted=False,
        proof=dict(typedRequest=typed_request,typedContext=typed,adapter=adapter,readerProgram=actual_read,providerProgram=actual_provider,
            dispatchPaths=dispatch_paths,readerProviderClass=read_class,providerClasses=provider_classes,
            actualSourceWindows={k:v['windows']for k,v in sources.items()},
            actualComparedCanonicalAdapterRva=s['adapter']-base,actualReaderRegisteredPointerEqualityInferred=False,
            selectedCallbackEqualsCanonicalIsCondition=True),
        evidenceBoundary=dict(exact='Fresh nominal ReadValue MVAR/provider context and actual full Reader, compatible-backend success and matched canonical dispatch FF/create/no-create source programs.',
            conditional=__doc__+' Initialized referenced classes, normal TypeFromHandle/backend/indexer/predicate effects, successful compatible nonnull backend result, matching canonical callback and coherent exact closed adapter MethodInfo, readable disjoint storage.',
            unresolved=['live provider/default/override/inflation selection','child wire grammar','enclosing field/framing','cold/refill/error paths','whole owner']))))
