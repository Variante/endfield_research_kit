"""Finite dedicated reference-domain source attribution for held catalogs.

Ordinary originals remain reference types. Their separately maintained exact
domain reader/lifecycle/adapter programs supply the source proof instead of
the generic reference-reader algorithm. Native attribution rederives the same
complete owner and checks full equality; no child or catalog is promoted.
"""
import hashlib,json


def need(check,condition,detail=None):
    if not condition:raise ValueError('catalogReferenceDomainSource.'+check+':'+str(detail)[:800])


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest().upper()


def _profile(schema):
    if schema=='endfield.skill-blackboard-double-sources.v1':
        from scripts.game_data.memorypack import skill_blackboard_double_sources as owner
        return owner,'validated-conditional-blackboard-double',owner.WRAPPER
    if schema=='endfield.skill-blackboard-int-sources.v1':
        from scripts.game_data.memorypack import skill_blackboard_int_sources as owner
        return owner,'validated-conditional-blackboard-int',owner.WRAPPER
    if schema=='endfield.skill-blackboard-vector3-sources.v1':
        from scripts.game_data.memorypack import skill_blackboard_vector3_sources as owner
        return owner,'validated-conditional-blackboard-vector3','Beyond.MemoryPack.Beyond_Blackboard_BlackboardVector3ForMemoryPack'
    if schema=='endfield.skill-blackboard-buff-id-sources.v1':
        from scripts.game_data.memorypack import skill_blackboard_buff_id_sources as owner
        return owner,'validated-conditional-blackboard-buff-id',owner.WRAPPER
    return None


def project(source,pins):
    profile=_profile(source.get('schema'))
    if profile is None:return NotImplemented
    owner,status,wrapper=profile;cap=source.get('capabilities',{}).get(owner.CAPABILITY,{})
    proof=source.get('proof',{});pair=proof.get('pair',{});programs=proof.get('readerPrograms',[])
    need('same-owned-nominal-and-build',source.get('nativeInputs')==pins and bool(pins)and source.get('status')==status
        and cap.get('typeName')==owner.TYPE and cap.get('wrapperName')==wrapper
        and cap.get('wholeGrammarAdmitted')is True and cap.get('ordinaryOriginalReadValueAdmitted')is True
        and cap.get('ownConcreteGetterSemanticsProved')is True and cap.get('ownConcreteFactorySemanticsProved')is True)
    need('complete-own-reader-paths',isinstance(programs,list)and len(programs)>=3
        and {(False,False),(True,False),(False,True)}<={(p.get('newWrapper'),p.get('ff'))for p in programs}
        and all(type(p.get('newWrapper'))is bool and type(p.get('ff'))is bool
            and p.get('selectedBytes')and p.get('entryRspRestored')is True
            and(p.get('normalReturn')is True or p.get('normalReturnViaBarrier')is True)for p in programs))
    for role in('constructor','factory'):
        program=proof.get(role,{})
        need('own-complete-lifecycle:'+role,bool(program.get('selectedBytes'))and program.get('entryRspRestored')is True
            and(program.get('normalReturn')is True or program.get('normalReturnViaBarrier')is True))
    registration=pair.get('registration',{})
    need('same-original-and-wrapper-registration',registration.get('originalType')==owner.TYPE and registration.get('wrapperType')==wrapper)
    methods=pair.get('composition',{}).get('methods',[])
    need('own-getter-and-concrete-formatter',isinstance(methods,list)and len(methods)==2
        and any(m[1:3]==[wrapper,'GetValue']for m in methods)
        and any(m[1].startswith(wrapper+'+')and m[2]=='Deserialize'for m in methods))
    reader=proof.get('warm',{}).get('readerMethod')or proof.get('adapter',{}).get('pairForwarder',{}).get('readerMethod')
    need('own-exact-static-reader',isinstance(reader,list)and len(reader)==4 and reader[1:3]==[wrapper,'Deserialize']
        and type(reader[0])is int and type(reader[3])is int and reader[0]>=0 and reader[3]>0)
    from scripts.game_data.memorypack.catalog_source_review import _source_windows
    windows=_source_windows(proof.get('sourceWindows',{}).get('Deserialize'))
    return dict(schema='endfield.catalog-dedicated-reference-source-projection.v1',nativeInputs=dict(pins),
        wrapperName=wrapper,wrappedType=owner.TYPE,maintainedOwner=owner.__name__,sourceMethods=[reader]+methods,codeWindows=windows,
        sourceKind='dedicated-reference-domain-source',originalIsValueType=False,genericReferenceReaderApplicable=True,
        genericReferenceReaderUsed=False,genericNotApplicableClaimed=False,
        completeSelectedSourceAdmitted=False,retainedSelectedSourceComplete=True,nativeAttributionProved=False,
        retainedSourceProofSha256=fingerprint(source),completeFreshOwnerReplayRequired=True,childGrammarFromSourceAdmitted=False,
        currentConsumerAdmitted=False,catalogAdmitted=False,historicalAttributionHoldCleared=False,
        conditions=['Own exact reference nominal, concrete wrapper reader, registered formatter and GetValue.',
            'Fresh compatible initialized metadata/cache/helpers, disabled collector and disjoint stable storage.',
            'Own selected new/existing/FF/lifecycle and adapter paths; runtime selection and child/consumer grammar remain separate.',
            'Every old catalog still requires its precise native semantic-role projection.'])


def derive(image,pins,*,retained_sources):
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    need('finite-distinct-owned-sources',isinstance(retained_sources,list)and 0<len(retained_sources)<=4
        and len({s.get('schema')for s in retained_sources})==len(retained_sources))
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);out=[]
    for source in retained_sources:
        row=project(source,pins);need('explicit-dedicated-reference-owner',row is not NotImplemented)
        owner,_,_=_profile(source['schema'])
        need('actual-original-is-reference',ctx.is_value_type(owner.TYPE)is False,owner.TYPE)
        fresh=owner.derive(image,pins)
        need('same-complete-current-reference-owner',fresh==source,dict(wrapperName=row['wrapperName'],
            retainedSha256=fingerprint(source),currentSha256=fingerprint(fresh)))
        out.append(dict(row,completeSelectedSourceAdmitted=True,nativeAttributionProved=True))
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=out,sourceCount=len(out),
        sourceProgramSemanticsReproved=True,currentConsumersAdmitted=False,catalogsActivated=0,historicalAttributionHoldsCleared=0,
        evidenceBoundary=__doc__)


def derive_current(image,pins,*,schemas):
    """Reprove a current owner, retaining its full new proof instead of an old cap.

    This mode makes no retained-proof-equality claim. It is useful when a prior
    report predates an explicit admission declaration; the current native
    program derivation, nominal gate and source windows must all succeed anew.
    """
    from scripts.game_data.buff_formatter_windows_regenerate import _publication_gate
    from scripts.game_data.il2cpp.reference_layouts import NativeReferenceContext
    need('finite-distinct-current-owner-schemas',isinstance(schemas,list)and 0<len(schemas)<=4
        and len(set(schemas))==len(schemas)and all(_profile(s)is not None for s in schemas))
    _publication_gate(image,pins);ctx=NativeReferenceContext(image);out=[];full=[]
    for schema in schemas:
        owner,_,_=_profile(schema)
        need('current-original-is-reference',ctx.is_value_type(owner.TYPE)is False,owner.TYPE)
        source=owner.derive(image,pins);row=project(source,pins)
        need('same-requested-current-source-schema',source.get('schema')==schema and row is not NotImplemented)
        out.append(dict(row,completeSelectedSourceAdmitted=True,nativeAttributionProved=True,
            currentSourceProofSha256=fingerprint(source),retainedSourceProofEqualityClaimed=False))
        full.append(source)
    _publication_gate(image,pins)
    return dict(schema='endfield.catalog-dedicated-source-attribution.v1',nativeInputs=dict(pins),sources=out,sourceCount=len(out),
        sourceProgramSemanticsReproved=True,fullCurrentOwnerSources=full,retainedProgramProofsReused=False,
        currentConsumersAdmitted=False,catalogsActivated=0,historicalAttributionHoldsCleared=0,evidenceBoundary=__doc__)
