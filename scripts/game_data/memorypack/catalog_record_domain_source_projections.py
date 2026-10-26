"""Own selected BuffFindSettings and CreateBuffActionInput source projections.

Their maintained reference-domain sources prove the actual new/reuse/FF and
cache paths, constructor and getter used by those callers. No unused named
CreateInstance entry or four generic-reader variants are claimed. Ordinary
canonical adapter identity is joined independently. Child wire grammars,
current consumers and catalog activation remain separate.
"""
import hashlib,json

PROFILES={
    'endfield.skill-root-buff-find-source.v1':('Beyond.Gameplay.Core.BuffFindSettings',
        'Beyond.MemoryPack.Beyond_Gameplay_Core_BuffFindSettingsForMemoryPack','proved-record-caller-requires-child-joins'),
    'endfield.skill-root-create-buff-input-source.v1':('Beyond.Gameplay.Core.CreateBuffActionInput',
        'Beyond.MemoryPack.Beyond_Gameplay_Core_CreateBuffActionInputForMemoryPack','proved-MC5-caller-requires-assign-pair-list'),
}


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogRecordDomainSource.'+check+':'+str(detail)[:700])


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def project(source,ordinary,pins):
    profile=PROFILES.get(source.get('schema'))
    if profile is None:return NotImplemented
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    typename,wrapper,status=profile
    need('same-owned-reference-source',source.get('nativeInputs')==pins and bool(pins)and source.get('status')==status
        and source.get('typeName')==typename and source.get('wrapperName')==wrapper)
    pair=source.get('registeredPair',{});adapter=ordinary.get('adapter',{})
    need('same-canonical-ordinary-pair',adapter.get('nativeInputs')==pins and adapter.get('pair')==pair
        and(adapter.get('typeName'),adapter.get('wrapperName'))==(typename,wrapper)
        and(pair.get('registration',{}).get('originalType'),pair.get('registration',{}).get('wrapperType'))==(typename,wrapper))
    method=adapter.get('pairForwarder',{}).get('readerMethod',[]);methods=pair.get('composition',{}).get('methods',[])
    need('own-static-reader-and-GetValue',len(method)==4 and method[1:3]==[wrapper,'Deserialize']
        and type(method[0])is int and type(method[3])is int and method[3]>0 and len(methods)==2
        and adapter.get('getterMethod')in methods and adapter['getterMethod'][1:3]==[wrapper,'GetValue']
        and any(m[1].startswith(wrapper+'+')and m[2]=='Deserialize'for m in methods))
    programs=source.get('programs',[])
    expected=3 if typename.endswith('.BuffFindSettings')else 7
    need('complete-selected-domain-caller-programs',len(programs)==expected
        and {(False,False),(True,False),(False,True)}<={(p.get('newWrapper'),p.get('ff'))for p in programs}
        and all(type(p.get('newWrapper'))is bool and type(p.get('ff'))is bool and p.get('selectedBytes')
            and p.get('normalReturn')is True and p.get('entryRspRestored')is True for p in programs))
    constructor=source.get('constructor')if expected==3 else source.get('constructorProgram')
    need('selected-own-construction',isinstance(constructor,dict)and bool(constructor.get('selectedBytes'))
        and(constructor.get('normalReturn')is True or constructor.get('normalReturnViaBarrier')is True))
    if expected==3:
        need('own-direct-holder-getter',source.get('getter',{}).get('entryRva')==adapter['getterMethod'][3]
            and ordinary.get('ownConcreteGetterSemanticsProved')is True
            and ordinary.get('ownConcreteFactorySemanticsProved')is True)
        windows=_source_windows(source.get('sourceWindows'))
    else:
        for role in('getterPrograms','getValuePrograms'):
            getters=source.get(role,[])
            need('complete-distinct-cache32-getter:'+role,{p.get('cacheState')for p in getters}=={'coherent','empty','stale'}
                and all(p.get('typedCacheOffset')==32 and p.get('originalHolderOffset')==16
                    and p.get('selectedBytes')and p.get('normalReturn')is True
                    and [row[1].lower()for row in p['selectedBytes'][-3:]]==['4883c420','5b','c3']for p in getters))
        need('original-default-initializer',source.get('originalInitializerProgram',{}).get('normalReturnViaBarrier')is True
            and source.get('originalConstructorThunk',{}).get('rdxIsZeroAtBothCallers')is True)
        need('cache32-not-equated-with-inherited-cache24',all(p.get('inheritedCachesNotEquated')is True for p in programs))
        windows=_source_windows(source.get('sourceWindows',{}).get('reader'))
    return dict(schema='endfield.catalog-dedicated-reference-source-projection.v1',nativeInputs=dict(pins),
        wrapperName=wrapper,wrappedType=typename,maintainedOwner='scripts.game_data.memorypack.'+
            ('skill_root_buff_find_sources'if expected==3 else'skill_root_create_buff_input_sources'),
        sourceKind='dedicated-reference-domain-source',sourceMethods=[method]+methods,codeWindows=windows,
        originalIsValueType=False,genericReferenceReaderApplicable=True,genericReferenceReaderUsed=False,
        genericNotApplicableClaimed=False,retainedSelectedSourceComplete=True,selectedDomainProgramCount=expected,
        fourGenericReaderVariantsClaimed=False,unusedCreateInstanceEntryAdmitted=False,
        completeSelectedSourceAdmitted=False,nativeAttributionProved=False,childGrammarFromSourceAdmitted=False,
        currentConsumerAdmitted=False,catalogAdmitted=False,historicalAttributionHoldCleared=False,
        retainedSourceProofSha256=fingerprint(source),ordinarySourceProofSha256=fingerprint(ordinary),conditions=[
            'Exact selected own new/reuse/FF/cache programs, named field transfers and construction/getter paths.',
            'The same selected canonical ordinary reference adapter, exact GetValue and static-reader entry.',
            'Initialized compatible metadata/cache/provider contexts, normal helpers and typed allocations, disabled collector and stable disjoint buffered storage.',
            'Delegated children, runtime callback choice, current consumers and catalog semantic-role migration remain separate.'])


def derive_current(image,pins,*,schemas):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    from scripts.game_data.memorypack import skill_root_buff_find_sources as find,skill_root_create_buff_input_sources as create
    from scripts.game_data.memorypack.reference_object_sources import derive_adapter
    from scripts.game_data.memorypack.skill_root_child_bindings import reference_record_abi
    need('finite-distinct-owner-schemas',isinstance(schemas,list)and 0<len(schemas)<=2
        and len(set(schemas))==len(schemas)and set(schemas)<=set(PROFILES))
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);rows=[];full=[]
    for schema in schemas:
        typename,wrapper,_=PROFILES[schema];need('actual-reference-original',ctx.is_value_type(typename)is False)
        source=find.derive(image,pins)if typename==find.TYPE else create.derive(image,pins)
        if typename==find.TYPE:ordinary=reference_record_abi(image,pins,source)
        else:
            chosen,=[w for w in image.memorypack_wrappers.values()if w.name==wrapper]
            ordinary=dict(adapter=derive_adapter(image,pins,source['registeredPair'],chosen))
        row=project(source,ordinary,pins)
        rows.append(dict(row,completeSelectedSourceAdmitted=True,nativeAttributionProved=True,
            currentSourceProofSha256=fingerprint(source),retainedSourceProofEqualityClaimed=False))
        full.append(dict(source=source,ordinary=ordinary))
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=rows,
        fullCurrentOwnerSources=full,sourceCount=len(rows),sourceProgramSemanticsReproved=True,
        retainedProgramProofsReused=False,currentConsumersAdmitted=False,catalogsActivated=0,historicalAttributionHoldsCleared=0)
