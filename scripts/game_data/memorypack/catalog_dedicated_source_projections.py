"""Finite dedicated wrapper-source projections for held catalog review.

Own source derivations remain authoritative. A projection neither supplies a
generic reference reader for a value original nor admits its child wire,
current consumer, enclosing route or reviewed catalog. Native attribution
rederives the same owner and requires the complete retained proof to agree.
"""
import hashlib
import json

SCHEMA='endfield.catalog-dedicated-source-projection.v1'


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogDedicatedSource.'+check+':'+str(detail)[:800])


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def _difference(expected,actual,path=()):
    if type(expected)is not type(actual):return dict(path=list(path),expectedType=type(expected).__name__,actualType=type(actual).__name__)
    if isinstance(expected,dict):
        if set(expected)!=set(actual):return dict(path=list(path),missingKeys=sorted(set(expected)-set(actual)),extraKeys=sorted(set(actual)-set(expected)))
        for key in sorted(expected):
            if expected[key]!=actual[key]:return _difference(expected[key],actual[key],path+(key,))
    elif isinstance(expected,list):
        if len(expected)!=len(actual):return dict(path=list(path),expectedLength=len(expected),actualLength=len(actual))
        for index,(left,right)in enumerate(zip(expected,actual)):
            if left!=right:return _difference(left,right,path+(index,))
    elif expected!=actual:return dict(path=list(path),expected=str(expected)[:140],actual=str(actual)[:140])
    return None


def _profile(schema):
    if schema=='endfield.impulse-envelope-wrapper-source.v1':
        from scripts.game_data.memorypack import skill_impulse_envelope_sources as owner
        return owner,'proved-envelope-wrapper-source-requires-value-and-curve-joins',32
    if schema=='endfield.skill-smart-target-wrapper-source.v1':
        from scripts.game_data.memorypack import skill_smart_target_value_sources as owner
        return owner,'proved-smart-target-wrapper-requires-value-and-child-joins',40
    if schema=='endfield.skill-root-assign-pair-source.v1':
        from scripts.game_data.memorypack import skill_root_assign_pair_sources as owner
        return owner,'proved-wrapper-source-requires-value40-adapter',40
    if schema=='endfield.skill-root-buff-id-source.v1':
        from scripts.game_data.memorypack import skill_root_buff_id_sources as owner
        return owner,'proved-wrapper-source-requires-value8-adapter',8
    if schema=='endfield.skill-gameplay-tag-value-source.v1':
        from scripts.game_data.memorypack import skill_gameplay_tag_value_sources as owner
        return owner,'proved-wrapper-source-requires-value4-adapter',4
    if schema=='endfield.skill-root-tag-query-source.v1':
        from scripts.game_data.memorypack import skill_root_tag_query_sources as owner
        return owner,'proved-wrapper-source-requires-array-and-value16-adapter',16
    return None


def project(source,pins):
    """Project only the complete finite source shapes owned above.

    This pure result is retained evidence awaiting native attribution. It is
    useful to the catalog reviewer only with its independent native result;
    it never authenticates the installed image or clears an old hold itself.
    """
    profile=_profile(source.get('schema'))
    if profile is None:return NotImplemented
    owner,status,width=profile;typ=getattr(owner,'TYPE',None)or owner.VALUE
    legacy=source['schema']in('endfield.skill-root-assign-pair-source.v1','endfield.skill-root-buff-id-source.v1',
        'endfield.skill-gameplay-tag-value-source.v1','endfield.skill-root-tag-query-source.v1')
    ff_key='ff'if legacy else'wrapperFF'
    need('same-native-owned-schema-and-nominal',source.get('nativeInputs')==pins and bool(pins)
        and source.get('status')==status and source.get('typeName')==typ
        and source.get('wrapperName')==owner.WRAPPER)
    layout=source.get('layout',{});programs=source.get('programs',[])
    need('own-managed-layout-and-holder',layout.get('typeName')==typ and layout.get('managedBytes')==width
        and layout.get('holder')==[owner.WRAPPER,typ,16])
    need('complete-explicit-source-paths',isinstance(programs,list)and len(programs)==3
        and all(type(p.get('newWrapper'))is bool and type(p.get(ff_key))is bool for p in programs)
        and{(p['newWrapper'],p[ff_key])for p in programs}=={(False,False),(True,False),(False,True)}
        and all((p.get('normalReturn')is True or legacy and p.get('normalReturnViaBarrier')is True)
            and(legacy or p.get('entryRspRestored')is True and p.get('allIntegerNonvolatilesRestored')is True)
            and isinstance(p.get('selectedBytes'),list)
            and p['selectedBytes'] for p in programs))
    new=next(p for p in programs if p['newWrapper']);null=next(p for p in programs if p[ff_key])
    if legacy:
        need('own-legacy-wrapper-and-default-boundaries',all(p.get('managedBytes')==width
            and p.get('originalDefaultValueAdmitted')is False for p in programs)
            and isinstance(source.get('getter'),dict)and source['getter'].get('instructions')
            and source.get('positiveCollectionAdmitted')is False)
    elif width==32:
        need('actual-wrapper-allocation-zero-and-FF-clear',new.get('newWrapperZeroedBytes')==width
            and null.get('wrapperReferenceCleared')is True and null.get('sourceHeaderBytes')==1
            and all(p.get('originalDefaultAdmitted')is False for p in programs))
    else:
        need('own-Smart-source-and-original-default-boundary',null.get('wrapperReferenceCleared')is True
            and all(p.get('managedBytes')==40 and p.get('originalDefaultValueAdmitted')is False for p in programs)
            and source.get('headerSource',{}).get('instructions'))
    forwarding=source.get('forwarding',{});forward=forwarding.get('forwarding',{})
    reader=forwarding.get('readerMethod',[]);pair=source.get('registeredPair',{})
    need('complete-own-registered-forwarder',len(reader)==4 and reader[1:3]==[owner.WRAPPER,'Deserialize']
        and type(reader[0])is int and type(reader[3])is int and reader[0]>=0 and reader[3]>0
        and forward.get('completeOriginalForwarderChecked')is True
        and forward.get('conditionalReaderAndOutputForwardingProved')is True
        and forward.get('runtimeFormatterProviderSelectionProved')is False)
    registration=pair.get('registration',{});composition=pair.get('composition',{})
    need('same-original-wrapper-registration',registration.get('originalType')==typ
        and registration.get('wrapperType')==owner.WRAPPER)
    methods=composition.get('methods',[]);getters=[m for m in methods if len(m)==4 and m[1:3]==[owner.WRAPPER,'GetValue']]
    need('own-exact-getter-and-formatter-methods',len(getters)==1 and len(methods)==2
        and any(m[1].startswith(owner.WRAPPER+'+')and m[2]=='Deserialize'for m in methods))
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    windows=_source_windows(source.get('sourceWindows'))
    need('source-child-and-parent-boundaries-preserved',source.get('wholeOwnerAdmitted')is False
        and(source.get('childGrammarAdmitted',False)is False and source.get('parentFieldAdmitted',False)is False
            if legacy else source.get('childGrammarAdmitted')is False and source.get('parentFieldAdmitted')is False
                and source.get('originalDefaultValueAdmitted')is False))
    fingerprint=_fingerprint(source)
    return dict(schema=SCHEMA,nativeInputs=dict(pins),wrapperName=owner.WRAPPER,wrappedType=typ,
        maintainedOwner=owner.__name__,sourceMethods=[reader]+methods,codeWindows=windows,
        sourceKind='dedicated-value-original-wrapper-source',completeSelectedSourceAdmitted=False,
        retainedSelectedSourceComplete=True,
        genericReferenceReaderApplicable=False,childGrammarFromSourceAdmitted=False,
        selectedWrapperPaths=[[False,False],[True,False],[False,True]],
        canonicalFFBeforeNewOrExistingSelection=True,managedBytes=width,rawManagedWidthIsWireWidth=False,
        boundedGetterRetained=True,defaultsOutsideSelectedReaderAdmitted=False,getterPhysicalExtentFromProjectionAdmitted=False,
        retainedSourceProofSha256=fingerprint,nativeAttributionProved=False,currentConsumerAdmitted=False,
        completeFreshOwnerReplayRequired=True,
        catalogAdmitted=False,historicalAttributionHoldCleared=False,
        conditions=['Own exact registered wrapper/formatter and conditional original forwarder.',
            'Initialized normal helpers, buffered disjoint storage and disabled collector.',
            'FF clears only the wrapper reference; original default/value adapter and child grammar remain separate.',
            'Current semantic consumer and native catalog role projection remain independently required.'])


def derive(image,pins,*,retained_sources):
    """Freshly rederive only each requested dedicated source owner."""
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    need('finite-distinct-owned-proofs',isinstance(retained_sources,list)and 0<len(retained_sources)<=6
        and len({s.get('wrapperName')for s in retained_sources})==len(retained_sources))
    _publication_gate(image,pins);rows=[]
    for source in retained_sources:
        projected=project(source,pins)
        need('explicit-dedicated-source-owner',projected is not NotImplemented,source.get('schema'))
        owner,_,_=_profile(source['schema']);derive_source=getattr(owner,'derive_wrapper',None)or owner.derive
        fresh=derive_source(image,pins)
        need('same-complete-current-owned-source',fresh==source,dict(wrapperName=source['wrapperName'],
            retainedSha256=_fingerprint(source),currentSha256=_fingerprint(fresh),firstDifference=_difference(source,fresh)))
        rows.append(dict(projected,nativeAttributionProved=True,completeSelectedSourceAdmitted=True))
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=rows,
        sourceCount=len(rows),sourceProgramSemanticsReproved=True,currentConsumersAdmitted=False,
        catalogsActivated=0,historicalAttributionHoldsCleared=0,evidenceBoundary=__doc__)
